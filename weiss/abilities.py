"""Reads Weiss Schwarz card text into abilities the game can run (see the abilities section of game.py).

parse(text) gives a list of plain-JSON abilities, one per ability on the card:

    {"kind": "auto"|"act"|"cont"|"event"|"counter"|"backup", "text": the printed line,
     "when": [{"on": ...}, ...],  # auto: what triggers it
     "cond": [{"type": ...}, ...],  # what has to be true for it to trigger, or be activated, or apply
     "cost": [{"part": ...}, ...], "steps": [{"do": ...}, ...],  # what paying and resolving it does
     "effects": [{"target": ..., "power": n, "soul": n, "grant": [text, ...]}, ...],  # cont: what it gives
     "color_free": {"self": True} or {"filter": ...},  # cont: hand cards it lets skip the color rule
     "no_backup": True,  # cont: no Backups can be played during this card's battle
     "once": bool,  # 1/TURN
     "where": zone}  # where the card has to be, if not on the stage

The wording on cards is regular enough to read clause by clause. Anything this doesn't recognize
becomes a {"do": "manual"} step, which asks the player to do that part by hand: an effect is never
silently dropped. A condition it doesn't recognize counts as met (the player can still skip the ability).

Inside the parser, quoted text (card names, granted abilities) is masked as ⟦n⟧ first, so commas and
full stops inside quotes can't confuse the splitting into sentences and clauses.
"""
import logging
import re
from functools import lru_cache

log = logging.getLogger(__name__)

ZONE_WORDS = {"waiting room": "waiting", "clock": "clock", "hand": "hand", "level": "level", "memory": "memory",
              "stock": "stock", "deck": "deck"}
OPEN_BEFORE = ' \n([/"'  # a quote after one of these (and before a word) opens; any other closes


# --- Quotes, sentences and clauses -------------------------------------------------------------------

def is_opening(text, i):
    before = text[i - 1] if i else " "
    after = text[i + 1] if i + 1 < len(text) else " "
    return before in OPEN_BEFORE and after not in ' .,)'


def closing_quote(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '"':
            depth += 1 if is_opening(text, i) else -1
            if depth <= 0:
                return i
    return None


def mask(text):
    """(text with each top-level quote replaced by ⟦n⟧, the quotes' contents)."""
    quotes, out, i = [], [], 0
    while i < len(text):
        end = closing_quote(text, i) if text[i] == '"' else None
        if end is None:
            out.append(text[i])
            i += 1
        else:
            out.append(f"⟦{len(quotes)}⟧")
            quotes.append(text[i + 1:end].strip())
            i = end + 1
    return "".join(out), quotes


def unmask(text, quotes):
    return re.sub(r"⟦(\d+)⟧", lambda m: f'"{quotes[int(m[1])]}"', text)


# Older sets say the same things in other words. These put card text into the wording the rest of
# this module reads. They run on everything but card names (see canonical).
NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
FULL_WIDTH = str.maketrans({"［": "[", "］": "]", "（": "(", "）": ")", "／": "/", "　": " ", "“": '"', "”": '"', "’": "'"})
WORDING = [
    (r"\bCXCombo@\s*", "【CXCOMBO】 "),
    (r"\bBond/\s+", "Bond/"),
    (r"\b(event|climax) cards?\b(?! named)", r"\1"),
    (r"\bRest this card\b", "【REST】 this card"),
    (r"\bis placed in your climax area\b", "is placed on your climax area"),
    (r"\byour characters' trigger check\b", "your character's trigger check"),
    (r"\bbecomes 【REVERSE】 during battle\b", "becomes 【REVERSE】"),
    (r"\b(placed on (?:the|your) stage from your hand)(?: or your deck| by the 【\w+】 effect of ⟦\d+⟧| or by (?:a|an|the)(?: 【\w+】)? (?:⟦\d+⟧ )?effect(?: of ⟦\d+⟧)?)", r"\1"),
    (r"\bthis card was placed on the stage\b", "this card is placed on the stage"),
    (r"\b([Ff]or each [^,.]*?) revealed among them\b", r"\1 revealed among those cards"),
    (r"\bputs the top card of your opponent's deck\b", "puts the top card of their deck"),
    (r"\bchoose 1 card in your hand and put it\b", "choose 1 card in your hand, and put it"),
    (r"\bin any position on your stage\b", "in any position of your stage"),
    (r"\bon any position on your stage\b", "in any position of your stage"),
    (r"\b([Ii])f the number of your other (.+?) is (\d+) or (more|less)\b", r"\1f the number of other \2 you have is \3 or \4"),
    (r"\b([Ii])f the number of characters in your opponent's center stage is (\d+) or (less|more)\b", r"\1f your opponent's center stage has \2 or \3 characters"),
    (r"\b(choose (?:up to )?\d+ .+?) in your opponent's (back|center) stage with level higher than your opponent's level\b", r"\1 with level higher than your opponent's level in your opponent's \2 stage"),
    (r"\bperform the following effects(?: 1 time(?: each)?)? in any order\b", "perform the following effects 1 time in any order"),
    (r"(?<=your deck)(?:, and|\.) [Ss]huffle your deck(?=\])", " & Shuffle your deck"),
    (r"\b([Cc])hoose (\d+) other character\b", r"\1hoose \2 of your other characters"),
    (r"【(?:Reverse|reverse)】", "【REVERSE】"),
    (r"【(?:Rest|rest)】", "【REST】"),
    (r"【(?:Stand|stand)】", "【STAND】"),
    (r"REST@", "【REST】"),
    (r"(?<=[\w,.])(?=【(?:REVERSE|REST|STAND)】)", " "),
    (r"(?<=【(?:REVERSE)】)(?=\w)", " "),
    (r"(?<=【(?:REST)】)(?=\w)", " "),
    (r"(?<=【(?:STAND)】)(?=\w)", " "),
    (r"(?<=\d)(?=《)", " "),
    (r"(?<=[a-z])\?(?=[a-z])", " "),
    (r"【REST】 this card from 【STAND】", "【REST】 this card"),
    (r"\bis put on (your|the) climax area\b", r"is placed on your climax area"),
    (r"\bplaced on the climax area\b", "placed on your climax area"),
    (r"\bwhen this card attacks\b", "attacks"),
    (r"\bWhen another of your (.*?)characters? (becomes|is|attacks)", lambda m: f"When your other {m[1]}character {m[2]}"),
    (r"\buses? an 【ACT】 ability\b", lambda m: m[0].replace(" ability", "")),
    (r"\bplay an event card\b", "play an event"),
    (r"\bany other (【REST】 |【STAND】 )?characters\b", lambda m: f"another {m[1] or ''}character"),
    (r"\bon the bottom of your\b", "at the bottom of your"),
    (r"\bput that battle opponent\b", "put that character"),
    (r"\bthey get the following\b", "those characters get the following"),
    (r"\bthe following \d+ abilities\b", "the following abilities"),
    (r"\bgets \+(\d+) until\b", r"gets +\1 power until"),
    (r"\b(?:on|to) the stage position (?:that )?this card was (?:on|in)\b", "in the stage position that this card was in"),
    (r"\bput it on this card's stage position\b", "put it in the stage position that this card was in"),
    (r"\s+as the defending character\b", ""),
    (r"\b([Cc]hoose [^,.]*?) on your opponent's (center|back) stage\b", r"\1 in your opponent's \2 stage"),
    (r"\bfrom your hand to your waiting room\b", "from your hand into your waiting room"),
    (r"\b[Pp]ut an? (?=《)", "Put 1 "),
    (r"\bPut another (.*?)from your stage\b", r"Put 1 other \1from your stage"),
    (r"\b(?:Put|Return) (\d+) (.+?) (?:from|in) your waiting room (?:at|to) the bottom of your clock\b", r"Put \1 \2 from your waiting room to the bottom of your clock"),
    (r"\b(Return \d+ .+?) (?:in|from) your waiting room (?:in)?to your deck\b", r"\1 from your waiting room to your deck"),
    (r"\bPut (\d+) markers? (?:from )?underneath this card into your waiting room\b", r"Put \1 marker into your waiting room"),
    (r"\bPut a marker (?:from )?underneath this card into your waiting room\b", "Put 1 marker into your waiting room"),
    (r"(?i)\bthis ability activates up to (\d+) times? per turn\.?\s*", lambda m: f"{m[1]}/TURN@ "),
    (r"\bthe total level of cards\b", "the total level of the cards"),
    (r"\bthis card is (?:on|in) the (center|back) stage\b", r"this card is in your \1 stage"),
    (r"\bthe revealed card is\b", "that card is"),
    (r"\bif you reveal (\d+) or more cards\b", "if you revealed 1 or more cards"),
    (r"\bIf you reveal (\d+) or more cards\b", "If you revealed 1 or more cards"),
    (r"(?:^|(?<=\. ))Then, ", ""),
    (r"\bif your opponent has (\d+) or (less|more) characters? in their center stage\b", r"if your opponent's center stage has \1 or \2 characters"),
    (r"\b[Uu]ntil end of turn, (all of your [^,.⟦]*?) (get [^.⟦]+?)(\.?\s*(?:⟦|$))", r"\1 \2 until end of turn\3"),
    (r"\b[Uu]ntil the end of your opponent's next turn, (this card|that character) (gets [^.⟦]+?)(\.?\s*(?:⟦|$))", r"\1 \2 until the end of your opponent's next turn\3"),
    (r"\bput it (at the bottom of|into) your opponent's (deck|memory|clock|stock)\b", lambda m: f"put it {m[1]} their {m[2]}"),
    (r"\bChoose another (.*?)character\b", r"Choose 1 other \1character"),
    (r"\bchoose another (.*?)character\b", r"choose 1 other \1character"),
    (r"\bif you are level\b", "if your level is"),
    (r"\bIf you are level\b", "If your level is"),
    (r"\b([Cc]hoose (?:up to )?\d+ .+?) (in your (?:waiting room|hand|clock|memory|level)) (with ⟦\d+⟧ in (?:its|their) card names?)", r"\1 \3 \2"),
    (r"\bchooase\b", "choose"),
    (r"\bif your opponent has (\d+) or (less|more) characters in their center stage\b", r"if your opponent's center stage has \1 or \2 characters"),
    (r"\bif the number of characters in your opponent's center stage is (\d+) or (less|more)\b", r"if your opponent's center stage has \1 or \2 characters"),
    (r"\bif the number of your other (.+?) is (\d+) or (more|less)\b", r"if the number of other \1 you have is \2 or \3"),
    (r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", lambda m: NUMBER_WORDS[m[1].lower()]),
    (r"\bOne\b", "1"),
    (r"\bThis ability activates up to 1 times? per turn\.\s*", "1/TURN@ "),
    (r"\b(cards?|characters?) named (⟦\d+⟧)", r"\2"),
    (r"\b([Cc]hoose|[Pp]ut|[Rr]eturn|[Rr]eveal) an? (⟦\d+⟧)", r"\1 1 \2"),
    (r"\bif an? (⟦\d+⟧) is in your climax area", r"if \1 is in your climax area"),
    (r"\b[Ww]hen an? (⟦\d+⟧) is placed\b", r"When \1 is placed"),
    (r"\b([Cc])hoose 1 of the following effects and perform it\b", r"\1hoose 1 of the following effects, and perform it"),
    (r"\b([Cc]hoose) an? (?=《|level |other |red |blue |green |yellow |card|character|climax|event)", r"\1 1 "),
    (r"\b[Uu]ntil end of turn, (this card|that character) (gets [^.⟦]+?)(\.?\s*(?:⟦|$))", r"\1 \2 until end of turn\3"),
    (r"\bthat card gets\b", "that character gets"),
    (r"\buntil end of your opponent's next turn\b", "until the end of your opponent's next turn"),
    (r"\b(on|in) your (center|back) stage\b", r"in your \2 stage"),
    (r"\bFor each (.+?) revealed, ", r"For each \1 revealed among those cards, "),
    (r"\bput it on the top of your deck in any order\b", "put it on the top of your deck"),
    (r"\b([Ss])huffle your deck afterwards\b", r"\1huffle your deck"),
    (r"\bin your back stage\b(?=,? you may)", "in your back stage"),
    (r"\bthis card is on your\b", "this card is in your"),
    (r"\b(\d+) multiplied by (the number of .+?|that character's (?:level|soul)|your level|the level of .+?)(?=\.|$)", r"\2 ×\1"),
    (r"\bin the middle position of the center stage\b", "in the middle position of your center stage"),
    (r"\bthis power gets\b", "this card gets"),
    (r"\b([Cc]hoose|[Pp]ut|[Rr]eturn|for) an? (?=(?:level \d+ or (?:higher|lower) )?(?:other )?(?:《[^》]+》 )?(?:card|character|climax|event)\b)", r"\1 1 "),
    (r"\b(?:[Dd])raw a card\b", "draw 1 card"),
    (r"\bon stage\b", "on the stage"),
    (r"\bfrom hand\b", "from your hand"),
    (r"\bfrom the stage to the waiting room\b", "into your waiting room from the stage"),
    (r"\bbecomes 【REVERSE】 in battle\b", "becomes 【REVERSE】"),
    (r"\bon any position of\b", "in any position of"),
    (r"\bon the stage position that this card was on\b", "in the stage position that this card was in"),
    (r"\bput it on the top or the bottom of your deck\b", "put it on the top or at the bottom of your deck"),
    (r"\bhis or her\b", "their"),
    (r"\bin any order\b(?= on| at)", "in any order"),
    (r"\b[Rr]eveal (\d+) cards from the top of your deck, (?:and )?put them into your waiting room", r"flip over \1 cards from the top of your deck, and put them into your waiting room"),
    (r"\s+,", ","),
]


def canonical(text):
    """Card text in the wording this module reads, with card names left as they are. A quote holding an
    effect (it starts with a tag or ends a sentence) gets the same treatment; a name doesn't."""
    body, quotes = mask((text or "").translate(FULL_WIDTH))
    for pattern, replacement in WORDING:
        body = re.sub(pattern, replacement, body)
    return unmask(body, [canonical(q) if q.startswith("【") or q.endswith(".") or q.startswith("[") else q for q in quotes])


def ability_lines(text):
    """A card's text, one ability to a line. Some cards' abilities run together with no line between
    them: a new one starts where a tag follows the end of a sentence, a reminder or a quote. (A tag can
    also come mid-sentence, as in "uses an 【ACT】", and 【ACT】 【COUNTER】 is one ability.)"""
    lines = []
    for raw in re.sub(r"\n\s*(?=\")", " ", (text or "").translate(FULL_WIDTH)).split("\n"):
        body, quotes = mask(" ".join(raw.split()))
        lines += [unmask(part, quotes) for part in re.split(r"(?<=[.)⟧])\s*(?=【(?:AUTO|ACT|CONT|COUNTER)】)", body) if part]
    return lines


def without_reminders(text):
    return re.sub(r"\s*\([^()]*\)", "", text).strip()


def sentences(text):
    """Split at full stops, keeping "the following ability. ⟦1⟧ ⟦2⟧" together."""
    text = re.sub(r"((?:following (?:abilit\w+|effects?|actions?)|perform it|that ability)[^.⟦]*)\.\s+((?:⟦\d+⟧\s*)+)", r"\1 \2", text)
    text = re.sub(r"((?:following abilities), this card gets that ability[^.⟦]*)\.\s+((?:⟦\d+⟧\s*)+)", r"\1 \2", text)
    return [s.strip() for s in re.split(r"(?<=\.)\s+", text) if s.strip().rstrip(".")]


def clauses(sentence):
    return [c for c in (re.sub(r"^(?:and|then) ", "", part.strip().rstrip(".")) for part in sentence.split(", ")) if c]


# --- Card filters: "up to 2 level 1 or higher 《NIKKE》 characters", "an event or a 《NIKKE》 character" ---

ALT = re.compile(
    r"(?:an? )?(?P<other>other )?(?P<stand>【STAND】 )?(?P<rest>【REST】 )?(?P<color>(?:red|blue|green|yellow)\b\s*)?"
    r"(?:level (?P<level>\d+|X) _(?P<dir>higher|lower)\s*)?(?:cost (?P<cost>\d+) _(?P<costdir>higher|lower)\s*)?"
    r"(?:⟦(?P<name>\d+)⟧|《(?P<trait>[^》]+)》)?\s*(?P<type>characters?|climax(?:es)?|events?|cards?)?"
    r"(?: with ⟦(?P<inname>\d+)⟧ in (?:its|their) card names?)?"
    r"(?: with \[(?P<icon>\w+)\] in (?:its|their|the) trigger icons?)?"
    r"(?: with level equal to _lower than your level(?: \+(?P<plus>\d+))?)?")


def parse_filter(words, quotes):
    """A filter is {"any": [alternative, ...]} plus "other" and "stand" flags, or None if not understood."""
    words = re.sub(r" or (higher|lower)", r" _\1", words.strip())
    any_of, flags = [], {}
    if words.endswith(" without markers"):
        words = words.removesuffix(" without markers")
        flags["no_markers"] = True
    if words.endswith(" in battle"):
        words = words.removesuffix(" in battle")
        flags["in_battle"] = True
    if words.endswith(" with level higher than your opponent's level"):
        words = words.removesuffix(" with level higher than your opponent's level")
        flags["above_opponent_level"] = True
    match = re.fullmatch(r"(.*?)characters? with ⟦(\d+)⟧ or ⟦(\d+)⟧ in its card name", words)
    if match and not match[1]:  # either of two names
        names = [re.sub(r"\(.*?\)", "", quotes[int(g)]).strip() for g in match.groups()[1:]]
        return {"any": [{"type": "character", "in_name": name} for name in names]}
    for part in words.split(" or "):
        match = ALT.fullmatch(part.strip())
        if not match or not part.strip():
            return None
        alt = {}
        if match["other"]:
            flags["other"] = True
        if match["stand"]:
            flags["stand"] = True
        if match["rest"]:
            flags["rest"] = True
        if match["color"]:
            alt["color"] = match["color"].strip()
        if match["cost"]:
            alt["cost_min" if match["costdir"] == "higher" else "cost_max"] = int(match["cost"])
        if "with level equal to _lower than your level" in part:
            alt["level_plus"] = int(match["plus"] or 0)
        if match["level"]:
            key = "level_min" if match["dir"] == "higher" else "level_max"
            alt[key] = "X" if match["level"] == "X" else int(match["level"])
        if match["name"]:
            alt["name"] = quotes[int(match["name"])]
        if match["inname"]:
            alt["in_name"] = re.sub(r"\(.*?\)", "", quotes[int(match["inname"])]).strip()
        if match["trait"]:
            alt["trait"] = match["trait"]
        if match["icon"]:
            alt["icon"] = match["icon"]
        kind = (match["type"] or "").lower()
        for word, name in (("character", "character"), ("climax", "climax"), ("event", "event")):
            if kind.startswith(word):
                alt["type"] = name
        if not alt and not kind:
            return None
        any_of.append(alt)
    return carries_type_back({"any": any_of, **flags})


def carries_type_back(filter_):
    """In "event or 《NIKKE》 character" nothing needs doing; in "《A》 or 《B》 characters" the type is shared."""
    last = filter_["any"][-1].get("type")
    for alt in filter_["any"]:
        if last and ("trait" in alt or "color" in alt) and "type" not in alt:
            alt["type"] = last
    return filter_


def plain_name(name):
    """Card text writes names with straight quotes where the card itself may have curly ones."""
    return " ".join(re.sub(r"[“”„‟]", '"', name or "").replace("’", "'").split())


def plain_name_lines(text):
    """A card's text line by line, with its quotes straightened the same way as plain_name."""
    return [plain_name(line) for line in ability_lines(text)]


def matches_filter(filter_, details, x=None, my_level=0):
    """Whether a card's details fit a filter. Cards with no level (climaxes) count as level 0."""
    if not filter_:
        return True
    level = details.get("level") or 0
    kind = (details.get("card_type") or details.get("type") or "").lower()
    traits = details.get("traits") or ""
    name = plain_name(details.get("name"))
    icons = (details.get("trigger") or "").split()
    for alt in filter_["any"]:
        low, high = alt.get("level_min"), alt.get("level_max")
        if "type" in alt and alt["type"] != kind:
            continue
        if "name" in alt and plain_name(alt["name"]) != name:
            continue
        if "in_name" in alt and plain_name(alt["in_name"]).lower() not in name.lower():
            continue
        if "trait" in alt and alt["trait"] not in re.split(r"[・/]", traits):
            continue
        if "color" in alt and alt["color"] != (details.get("color") or "").lower():
            continue
        cost = details.get("cost") or 0
        if ("cost_min" in alt and cost < alt["cost_min"]) or ("cost_max" in alt and cost > alt["cost_max"]):
            continue
        if "icon" in alt and alt["icon"] not in icons:
            continue
        if low is not None and level < (x if low == "X" else low):
            continue
        if high is not None and level > (x if high == "X" else high):
            continue
        if "level_plus" in alt and level > my_level + alt["level_plus"]:
            continue
        return True
    return False


# --- Conditions: "if you have 2 or more other 《NIKKE》 characters" ---------------------------------------

def parse_condition(words, quotes):
    """One condition as {"type": ...}, or None if not understood."""
    text = re.sub(r"^(?:if|and) ", "", words.strip(), flags=re.I).rstrip(".")
    if re.fullmatch(r"during your turn", text, re.I):
        return {"type": "my_turn"}
    if re.fullmatch(r"during your opponent's turn", text, re.I):
        return {"type": "opp_turn"}
    if re.fullmatch(r"during the turn that this card is placed on the stage from your hand", text, re.I):
        return {"type": "played_this_turn"}
    match = re.fullmatch(r"the total level of the cards in your level is (\d+) or (higher|lower)", text, re.I)
    if match:
        return {"type": "total_level", "n": int(match[1]), "dir": match[2]}
    if re.fullmatch(r"during this card's battle", text, re.I):
        return {"type": "in_battle"}
    match = re.fullmatch(r"there is (a|no) character facing this card", text, re.I)
    if match:
        return {"type": "facing_exists", "absent": match[1].lower() == "no"}
    match = re.fullmatch(r"(?:this card's battle opponent|the character facing this card) is cost (\d+) or (higher|lower)", text, re.I)
    if match:
        return {"type": "facing_level", "stat": "cost", "n": int(match[1]), "dir": match[2]}
    match = re.fullmatch(r"the number of (.+?) you have is (\d+) or (more|less)", text, re.I)
    if match and (f := parse_filter(match[1], quotes)):
        return {"type": "have", "n": int(match[2]), "dir": match[3], "filter": carries_type_back(f)}
    match = re.fullmatch(r"your opponent's (center|back) stage has (\d+) or (more|less) characters?", text, re.I)
    if match:
        return {"type": "opp_stage_count", "zone": match[1].lower(), "n": int(match[2]), "dir": match[3]}
    if re.fullmatch(r"you revealed 1 or more cards", text, re.I):
        return {"type": "looked"}
    match = re.fullmatch(r"there is an? (.+?)(?: revealed)? among those cards", text, re.I)
    if match and (f := parse_filter(match[1], quotes)):
        return {"type": "among_has", "filter": f}
    match = re.fullmatch(r"you have an? (⟦\d+⟧) with 1 or more markers", text, re.I)
    if match:
        return {"type": "have_markers", "filter": parse_filter(match[1], quotes)}
    if re.fullmatch(r"the level of this card's battle opponent is higher than your opponent's level", text, re.I):
        return {"type": "that_above_opponent_level"}
    if re.fullmatch(r"the level of the card put into your waiting room by this effect is higher than your opponent's", text, re.I):
        return {"type": "milled_higher"}
    match = re.fullmatch(r"you chose (\d+) characters?", text, re.I)
    if match:
        return {"type": "chose", "n": int(match[1])}
    if re.fullmatch(r"all of the characters from among those cards have the same power", text, re.I):
        return {"type": "same_power"}
    if re.fullmatch(r"during your climax phase", text, re.I):
        return {"type": "phase", "phase": "climax"}
    match = re.fullmatch(r"your level is (\d+) or (higher|lower)", text, re.I)
    if match:
        return {"type": "my_level", "n": int(match[1]), "dir": match[2]}
    match = re.fullmatch(r"your (hand|waiting room|memory|clock|stock) has (\d+) or (more|less)(?: (.+?))?", text, re.I)
    if match:
        filter_ = parse_filter(re.sub(r"^cards?$", "card", match[4] or "card"), quotes)
        if filter_:
            return {"type": "zone_count", "zone": ZONE_WORDS[match[1].lower()], "n": int(match[2]), "dir": match[3], "filter": filter_}
    match = re.fullmatch(r"all of your characters are 《([^》]+)》", text, re.I)
    if match:
        return {"type": "all_trait", "trait": match[1]}
    match = re.fullmatch(r"you have (\d+) or (more|less) (.+?)", text, re.I)
    if match:
        filter_ = parse_filter(match[3], quotes)
        if filter_:
            return {"type": "have", "n": int(match[1]), "dir": match[2], "filter": carries_type_back(filter_)}
    match = re.fullmatch(r"you (do not )?have (another|an?) (.+?)( and (.+?))?( in your (?:center stage|back stage|level))?", text, re.I)
    if match:
        wanted = [parse_filter(w, quotes) for w in (match[3], match[5]) if w]
        if all(wanted):
            return {"type": "have_each", "filters": wanted, "other": match[2].lower() == "another",
                    "absent": bool(match[1]), "center": "center" in (match[6] or ""), "back": "back" in (match[6] or ""), "level": "level" in (match[6] or "")}
    match = re.fullmatch(r"you have (⟦\d+⟧)(?: and (⟦\d+⟧))?( in your center stage)?( with 1 or more markers)?", text, re.I)
    if match and not match[4]:
        wanted = [parse_filter(w, quotes) for w in (match[1], match[2]) if w]
        return {"type": "have_each", "filters": wanted, "other": False, "absent": False, "center": bool(match[3])}
    match = re.fullmatch(r"(⟦\d+⟧|a climax with \[\w+\] in (?:its|the) trigger icons?) is in your climax area", text, re.I)
    if match:
        words = re.sub(r"^a climax", "climax", match[1]).replace("the trigger", "its trigger")
        return {"type": "climax_is", "filter": parse_filter(words, quotes), "owner": "me"}
    match = re.fullmatch(r"there is a climax in your (opponent's )?climax area", text, re.I)
    if match:
        return {"type": "climax_is", "filter": None, "owner": "opp" if match[1] else "me"}
    match = re.fullmatch(r"this card is in your (center stage|back stage|waiting room|memory|level)", text, re.I)
    if match:
        return {"type": "self_in", "where": match[1].lower()}
    if re.fullmatch(r"this card is in the middle position of your center stage", text, re.I):
        return {"type": "self_in", "where": "middle"}
    if re.fullmatch(r"this card is 【STAND】", text, re.I):
        return {"type": "self_stand"}
    match = re.fullmatch(r"(⟦\d+⟧) is in your (memory|waiting room|level|clock)", text, re.I)
    if match:
        return {"type": "zone_count", "zone": ZONE_WORDS[match[2].lower()], "n": 1, "dir": "more", "filter": parse_filter(match[1], quotes)}
    match = re.fullmatch(r"there (?:are no markers|is a marker) underneath this card", text, re.I)
    if match:
        return {"type": "self_markers", "any": "is a marker" in text}
    match = re.fullmatch(r"you have (\d+) or (more|less) (.+?) in your (center|back) stage", text, re.I)
    if match and (f := parse_filter(match[3], quotes)):
        return {"type": "have", "n": int(match[1]), "dir": match[2], "filter": carries_type_back(f), "zone": match[4].lower()}
    match = re.fullmatch(r"during (your |your opponent's |the )(main phase|attack phase|encore step|climax phase)", text, re.I)
    if match:
        return {"type": "phase", "phase": match[2].split()[0].lower(), "whose": {"your ": "me", "your opponent's ": "opp"}.get(match[1].lower())}
    if re.fullmatch(r"this card is 【REST】", text, re.I):
        return {"type": "self_rest"}
    match = re.fullmatch(r"all of your characters are ((?:《[^》]+》(?: or )?)+)", text, re.I)
    if match:
        return {"type": "all_trait", "traits": re.findall(r"《([^》]+)》", match[1])}
    match = re.fullmatch(r"your opponent's (hand|waiting room|memory|clock|stock) has (\d+) or (more|less)(?: (.+?))?", text, re.I)
    if match and (f := parse_filter(re.sub(r"^cards?$", "card", match[4] or "card"), quotes)):
        return {"type": "zone_count", "owner": "opp", "zone": ZONE_WORDS[match[1].lower()], "n": int(match[2]), "dir": match[3], "filter": f}
    match = re.fullmatch(r"the number of cards in your (deck|hand|waiting room|stock|clock|memory) is (\d+) or (more|less)", text, re.I)
    if match:
        return {"type": "zone_count", "zone": ZONE_WORDS[match[1].lower()], "n": int(match[2]), "dir": match[3], "filter": None}
    if re.fullmatch(r"this card is the top card of your clock", text, re.I):
        return {"type": "self_clock_top"}
    match = re.fullmatch(r"your opponent has an? (.+?)", text, re.I)
    if match:
        filter_ = parse_filter(match[1], quotes)
        if filter_:
            return {"type": "opp_has", "filter": filter_}
    match = re.fullmatch(r"(?:this card's battle opponent|the character facing this card) is level (\d+)(?: or (higher|lower))?", text, re.I)
    if match:
        return {"type": "facing_level", "n": int(match[1]), "dir": match[2]}
    if re.fullmatch(r"you put 1 card into your hand", text, re.I):
        return {"type": "counted", "key": "hand"}
    if re.fullmatch(r"you put 1 card into your stock", text, re.I):
        return {"type": "counted", "key": "stock"}
    if re.fullmatch(r"you drew 1 card", text, re.I):
        return {"type": "counted", "key": "drew"}
    match = re.fullmatch(r"that card (is not|is|has|'s trigger icon is) (.+?)", text, re.I)
    if match:
        words = re.sub(r"\ban? ", "", match[2])
        if match[1].lower() != "is" and match[1].lower() != "is not":
            words = f"card with {words.removesuffix(' in its trigger icon')} in its trigger icon"
        filter_ = parse_filter(words, quotes)
        if filter_:
            return {"type": "revealed", "filter": filter_, "negate": match[1].lower() == "is not"}
    match = re.fullmatch(r"that card's trigger icon is (\[\w+\])", text, re.I)
    if match:
        return {"type": "revealed", "filter": parse_filter(f"card with {match[1]} in its trigger icon", quotes)}
    match = re.fullmatch(r"there are (\d+) or (less|more) markers underneath this card", text, re.I)
    if match:
        return {"type": "self_marker_count", "n": int(match[1]), "dir": match[2]}
    match = re.fullmatch(r"there is a card in your (memory|waiting room|clock|stock)", text, re.I)
    if match:
        return {"type": "zone_count", "zone": ZONE_WORDS[match[1].lower()], "n": 1, "dir": "more", "filter": None}
    match = re.fullmatch(r"your deck has (\d+) or (more|less) cards", text, re.I)
    if match:
        return {"type": "zone_count", "zone": "deck", "n": int(match[1]), "dir": match[2], "filter": None}
    match = re.fullmatch(r"you have (\d+) or (more|less) cards in your (memory|hand|waiting room|stock|clock)", text, re.I)
    if match:
        return {"type": "zone_count", "zone": ZONE_WORDS[match[3].lower()], "n": int(match[1]), "dir": match[2], "filter": None}
    match = re.fullmatch(r"the number of (.+?) in your (memory|hand|waiting room|stock|clock) is (\d+) or (more|less)", text, re.I)
    if match and (f := parse_filter(match[1], quotes)):
        return {"type": "zone_count", "zone": ZONE_WORDS[match[2].lower()], "n": int(match[3]), "dir": match[4], "filter": carries_type_back(f)}
    match = re.fullmatch(r"the number of (.+?) in your opponent's (memory|hand|waiting room|stock|clock) is (\d+) or (more|less)", text, re.I)
    if match and (f := parse_filter(match[1], quotes)):
        return {"type": "zone_count", "owner": "opp", "zone": ZONE_WORDS[match[2].lower()], "n": int(match[3]), "dir": match[4], "filter": carries_type_back(f)}
    match = re.fullmatch(r"your level is (\d+)", text, re.I)
    if match:
        return {"type": "my_level", "n": int(match[1]), "dir": None}
    match = re.fullmatch(r"(⟦\d+⟧) is among those cards", text, re.I)
    if match:
        return {"type": "among_has", "filter": parse_filter(match[1], quotes)}
    if re.fullmatch(r"there are no markers underneath that character", text, re.I):
        return {"type": "that_no_markers"}
    if re.fullmatch(r"there is no character facing this card or the character facing this card is 【REVERSE】", text, re.I):
        return {"type": "no_standing_facing"}
    if re.fullmatch(r"you paid the cost", text, re.I):
        return {"type": "always"}
    return None


# --- Costs: "[(1) Put 1 card from your hand into your waiting room & 【REST】 this card]" ------------------

def parse_cost(words, quotes):
    """The parts of a cost, or None if any part isn't understood. Each part knows how to be paid in game.py."""
    parts = []
    for raw in re.split(r"\s*&\s*|(?<=\))\s*(?=\S)", words.strip()):
        raw = raw.strip()
        if not raw:
            continue
        match = re.fullmatch(r"\(?(\d+)\)?", raw)
        if match:
            if int(match[1]):
                parts.append({"part": "stock", "n": int(match[1])})
            continue
        if re.fullmatch(r"【REST】 this card", raw):
            parts.append({"part": "self_rest"})
            continue
        match = re.fullmatch(r"Put this (【STAND】 )?card (?:from your hand )?(into your|at the bottom of your) (waiting room|clock|memory|deck|stock)", raw)
        if match:
            to = "deck_bottom" if match[2].startswith("at") else ZONE_WORDS[match[3]]
            parts.append({"part": "self_to", "to": to, "stand": bool(match[1])})
            continue
        match = re.fullmatch(r"Reveal (\d+) (.+?) in your hand", raw)
        if match and (filter_ := parse_filter(match[2], quotes)):
            parts.append({"part": "pick", "zone": "hand", "n": int(match[1]), "filter": filter_, "to": None})
            continue
        if raw == "Return this card to your hand":
            parts.append({"part": "self_to", "to": "hand", "stand": False})
            continue
        if raw == "Shuffle your deck":
            parts.append({"part": "shuffle"})
            continue
        if raw == "Put the top card of your stock into your clock":
            parts.append({"part": "stock_to_clock"})
            continue
        match = re.fullmatch(r"Put (\d+) marker into your waiting room", raw)
        if match:
            parts.append({"part": "markers", "n": int(match[1])})
            continue
        match = re.fullmatch(r"Put (\d+) (.+?) from your waiting room to the bottom of your clock", raw)
        if match and (filter_ := parse_filter(match[2], quotes)):
            parts.append({"part": "pick", "zone": "waiting", "n": int(match[1]), "filter": carries_type_back(filter_), "to": "clock_bottom"})
            continue
        match = re.fullmatch(r"Return (\d+) (.+?) from your waiting room to your deck", raw)
        if match and (filter_ := parse_filter(match[2], quotes)):
            parts.append({"part": "pick", "zone": "waiting", "n": int(match[1]), "filter": carries_type_back(filter_), "to": "deck"})
            continue
        match = re.fullmatch(r"Put (\d+) (.+?) from your memory into your waiting room", raw)
        if match and (filter_ := parse_filter(match[2], quotes)):
            parts.append({"part": "pick", "zone": "memory", "n": int(match[1]), "filter": carries_type_back(filter_), "to": "waiting"})
            continue
        if raw == "Put the top card of your deck into your clock" or raw == "Put 1 card from the top of your deck into your clock":
            parts.append({"part": "deck_to_clock"})
            continue
        match = re.fullmatch(r"Put (1 .+? and 1 .+?) from your hand into your (waiting room|memory)", raw)
        if match:
            for one in match[1].split(" and "):
                filter_ = parse_filter(one.removeprefix("1 "), quotes)
                if not filter_:
                    return None
                parts.append({"part": "pick", "zone": "hand", "n": 1, "filter": filter_, "to": ZONE_WORDS[match[2]]})
            continue
        match = re.fullmatch(r"Put (\d+) (.+?) from your (hand|stage|climax area|level) into your (waiting room|memory|clock|stock)", raw)
        if match:
            filter_ = parse_filter(match[2], quotes)
            if not filter_:
                return None
            zone = {"hand": "hand", "stage": "stage", "climax area": "climax", "level": "level"}[match[3]]
            parts.append({"part": "pick", "zone": zone, "n": int(match[1]), "filter": carries_type_back(filter_), "to": ZONE_WORDS[match[4]]})
            continue
        match = re.fullmatch(r"【REST】 (\d+) of your (.+?)", raw)
        if match:
            filter_ = parse_filter(match[2], quotes)
            if not filter_:
                return None
            parts.append({"part": "rest_chars", "n": int(match[1]), "filter": {"stand": True, **filter_}})
            continue
        return None
    return parts


# --- "X is equal to ..." ---------------------------------------------------------------------------------

def parse_x(words, quotes):
    words = words.rstrip(".")
    times = 1
    match = re.fullmatch(r"(.+?) ×(\d+)", words)
    if match:
        words, times = match[1], int(match[2])
    if words == "your level":
        return {"of": "my_level", "times": times}
    if words == "the level of the character you chose -1":
        return {"of": "chosen_level", "minus": 1, "times": times}
    match = re.fullmatch(r"the number of (.+?) (?:revealed )?among those cards", words)
    if match and (f := parse_filter(match[1], quotes)):
        return {"of": "flipped", "filter": carries_type_back(f), "times": times}
    tiers = re.findall(r"(\d+) if there are (\d+)(?: or (\d+)| or (less|more)) markers underneath this card", words)
    above = next((int(x) for x, _, _, how in tiers if how == "more"), None)
    if tiers and above is not None:  # [[most markers, X], ...], then X with more markers than any of those
        steps = [[int(upper or low), int(x)] for x, low, upper, how in tiers if how != "more"]
        return {"of": "marker_tiers", "tiers": steps, "above": above, "times": times}
    if words == "that character's level":
        return {"of": "target_level", "times": times}
    if words == "that character's soul":
        return {"of": "target_soul", "times": times}
    match = re.fullmatch(r"(?:the level of that card|that card's level)(?: \+(\d+))?", words)
    if match:
        return {"of": "flipped_level", "plus": int(match[1] or 0), "times": times}
    if words == "the number of your opponent's characters":
        return {"of": "opp_chars", "times": times}
    if words == "this card's soul":
        return {"of": "self_soul", "times": times}
    if words == "the level of that character":
        return {"of": "that_level", "times": times}
    match = re.fullmatch(r"the number of (other )?characters you have with (⟦\d+⟧) in its card name", words)
    if match and (f := parse_filter(f"characters with {match[2]} in its card name", quotes)):
        return {"of": "my_chars", "filter": {**f, **({"other": True} if match[1] else {})}, "times": times}
    if words == "the level of the revealed card":
        return {"of": "revealed_level", "times": times}
    match = re.fullmatch(r"the total level of (?:those cards|(?:the )?cards put into your waiting room by this effect)", words)
    if match:
        return {"of": "flipped_total", "times": times}
    match = re.fullmatch(r"the number of (?:(.+?) )?put into your waiting room by this effect(?: \+(\d+))?", words)
    if match and (f := parse_filter(match[1] or "cards", quotes)):
        return {"of": "flipped", "filter": carries_type_back(f), "plus": int(match[2] or 0), "times": times}
    match = re.fullmatch(r"the (?:total )?number of \[(\w+)\](?: in the)? trigger icons? (?:of those cards|revealed among those cards|among the cards revealed by this effect)", words)
    if match:
        return {"of": "flipped_icons", "icon": match[1], "times": times}
    match = re.fullmatch(r"the number of your (other )?(.+?)", words)
    if match and (f := parse_filter(match[2], quotes)):
        return {"of": "my_chars", "filter": {**carries_type_back(f), **({"other": True} if match[1] else {})}, "times": times}
    match = re.fullmatch(r"the number of cards in your (stock|hand|waiting room|memory|clock|level)", words)
    if match:
        return {"of": "zone", "zone": ZONE_WORDS[match[1]], "filter": None, "times": times}
    if words == "the number of markers underneath this card":
        return {"of": "markers", "times": times}
    if words == "the level of the character facing this card":
        return {"of": "facing_level", "times": times}
    if words == "the level of the revealed character":
        return {"of": "revealed_level", "times": times}
    match = re.fullmatch(r"the number of characters in your opponent's (center|back) stage", words)
    if match:
        return {"of": "opp_stage", "zone": match[1], "times": times}
    if words == "the number of characters your opponent has":
        return {"of": "opp_chars", "times": times}
    match = re.fullmatch(r"the number of (.+?) you have", words)
    if match:
        filter_ = parse_filter(match[1], quotes)
        if filter_:
            return {"of": "my_chars", "filter": filter_, "times": times}
    match = re.fullmatch(r"the number of (.+?) in your (waiting room|memory|clock|level|hand)", words)
    if match:
        filter_ = parse_filter(match[1], quotes)
        if filter_:
            return {"of": "zone", "zone": ZONE_WORDS[match[2]], "filter": filter_, "times": times}
    return None


# --- Effects ---------------------------------------------------------------------------------------------

def stat_change(words, quotes):
    """"+1500 power and +1 soul", plus any abilities given, as {"power", "soul", "x", "grant": [text]}, or None."""
    change = {"power": 0, "soul": 0, "grant": []}
    for token in re.findall(r"⟦(\d+)⟧", words):
        change["grant"].append(quotes[int(token)])
    words = re.sub(r"(?:and )?(?:the following abilit(?:y|ies)|\s*⟦\d+⟧)", " ", words)
    words = re.sub(r"\band\b", " ", words).strip()
    while words:
        match = re.match(r"([+-])(\d+|X) (power|soul|level)\s*", words)
        if not match:
            return None
        if match[2] == "X":
            change["x_stat"] = match[3]
        else:
            change[match[3]] = int(match[2]) * (1 if match[1] == "+" else -1)
        words = words[match.end():]
    return change


UNTIL = r"(?: until (?P<until>end of turn|the end of your opponent's next turn))?(?P<after>(?:\s*⟦\d+⟧)*)"
GETS = re.compile(r"(?P<who>that character|those characters|this card|all characters in your opponent's center stage|all of your (?P<all>.+?)) gets? (?P<what>.*?)" + UNTIL)
MOVE_IT = [
    (r"(?:return|put) (?:it|them) (?:in)?to your hand", "hand"), (r"put (?:it|them) into your stock", "stock"),
    (r"put (?:it|them) into your memory", "memory"), (r"put (?:it|them) into your clock", "clock"),
    (r"put (?:it|them) into your waiting room", "waiting"), (r"put (?:it|them) at the bottom of your deck", "deck_bottom"),
    (r"put (?:it|them) on the top of your deck", "deck"), (r"return (?:it|them) to your deck", "deck"),
    (r"put (?:it|them) into their waiting room", "waiting"), (r"return (?:it|them) to their hand", "hand"),
    (r"put (?:it|them) on the top of their deck", "deck"), (r"put (?:it|them) into your opponent's waiting room", "waiting"),
    (r"put (?:it|them) at the bottom of their deck", "deck_bottom"), (r"put (?:it|them) into their (?:memory)", "memory"),
    (r"put (?:it|them) into their stock", "stock"), (r"put (?:it|them) into their clock", "clock"),
    (r"return (?:it|them) to your opponent's deck", "deck"), (r"return (?:it|them) to your opponent's hand", "hand"),
]
DESTS = {"on the top of your deck": "deck", "on the top": "deck", "at the bottom of your deck": "deck_bottom", "at the bottom": "deck_bottom",
         "into your waiting room": "waiting", "into your stock": "stock", "into your hand": "hand"}


def step_manual(text, quotes):
    return {"do": "manual", "text": unmask(text, quotes)}


def clause_steps(clause, quotes, cost):
    """The steps for one clause, or None if it isn't understood."""
    text = re.sub(r"^you (?=draw|choose|deal)", "", clause[0].lower() + clause[1:])

    # Nothing to do: the cards never left.
    if re.fullmatch(r"put them on the top of (?:your|their) deck in the original order", text):
        return []
    if text == "put them at the bottom of your deck in any order":
        return [{"do": "rest", "to": "deck_bottom"}]

    # What the opponent does.
    match = re.fullmatch(r"put (?:the (top|bottom) card|(\d+) cards? from the (top|bottom)) of your opponent's stock into (?:their|your opponent's) waiting room", text)
    if match:
        return [{"do": "stock_card", "owner": "opp", "end": match[1] or match[3], "n": int(match[2] or 1)}]
    match = re.fullmatch(r"your opponent puts the top(?: (\d+))? cards? of their deck into their (clock|stock|waiting room)", text)
    if match:
        return [{"do": "top", "n": int(match[1] or 1), "owner": "opp", "to": ZONE_WORDS[match[2]]}]
    if text in ("return it to their deck", "return them to their deck"):
        return [{"do": "move_it", "to": "deck"}]
    if text == "put that character into their stock":
        return [{"do": "that_to", "to": "stock"}]
    if text == "put that character into your memory":
        return [{"do": "that_to", "to": "memory"}]
    match = re.fullmatch(r"put that character face (up|down) underneath this card as a marker", text)
    if match:
        return [{"do": "that_it"}, {"do": "marker", "face_down": match[1] == "down"}]
    if text == "your opponent returns all cards from their stock to their deck":
        return [{"do": "stock_to_deck", "owner": "opp"}]
    if text == "shuffles their deck":
        return [{"do": "shuffle", "owner": "opp"}]
    if text == "puts the same number of cards from the top of their deck into their stock":
        return [{"do": "top", "n_from": "stock_returned", "n": 0, "owner": "opp", "to": "stock"}]
    match = re.fullmatch(r"your opponent puts (\d+) cards from the top of their deck into their waiting room", text)
    if match:
        return [{"do": "top", "n": int(match[1]), "owner": "opp", "to": "waiting"}]
    match = re.fullmatch(r"your opponent chooses (\d+) (.+?) in their waiting room", text)
    if match and (f := parse_filter(match[2], quotes)):
        return [{"do": "choose", "zone": "waiting", "owner": "opp", "chooser": "opp", "filter": f, "max": int(match[1]),
                 "min": int(match[1]), "text": unmask(clause, quotes)}]
    if text == "returns all cards except that card from their waiting room to their deck":
        return [{"do": "waiting_to_deck", "owner": "opp", "except_it": True}]

    if text == "your opponent puts all of their stock into their waiting room":
        return [{"do": "stock_to_deck", "owner": "opp", "to": "waiting"}]
    if text == "returns all cards from their waiting room except that card to their deck":
        return [{"do": "waiting_to_deck", "owner": "opp", "except_it": True}]
    if re.fullmatch(r"your opponent puts that character from their memory (?:in|on) any position of their stage", text):
        return [{"do": "place", "opponent_places": True}]

    # Exchanging two cards' places.
    match = re.fullmatch(r"exchange them as 【(STAND|REST)】", text)
    if match:
        return [{"do": "swap_stage", "pos": match[1].lower()}]
    if text in ("exchange them", "exchanges them"):
        return [{"do": "exchange"}]
    match = re.fullmatch(r"choose 1 card in your (level|clock|memory) and 1 card in your waiting room", text)
    if match:
        return [{"do": "choose", "zone": ZONE_WORDS[match[1]], "filter": None, "max": 1, "min": 1, "text": f"Choose 1 card in your {match[1]}"},
                {"do": "choose", "zone": "waiting", "filter": None, "max": 1, "min": 1, "text": "Choose 1 card in your waiting room"}]

    # Moving around the stage.
    if text == "move it to an open position of your back stage":
        return [{"do": "place", "open": True, "zone": "back", "keep_pos": True}]
    match = re.fullmatch(r"move this card to (?:an|another) open position of your (center|back) stage", text)
    if match:
        return [{"do": "self_it"}, {"do": "place", "open": True, "zone": match[1], "keep_pos": True}]
    if text == "move this card to the open middle position of your center stage":
        return [{"do": "self_it"}, {"do": "place", "open": True, "only": "C2", "keep_pos": True}]
    if text == "move it to another open position of their center stage":
        return [{"do": "place", "open": True, "zone": "center", "keep_pos": True, "on_owner": True}]
    match = re.fullmatch(r"put (it|them|that character) in any position of your (center|back) stage(?: as (【REST】))?", text)
    if match:
        first = [{"do": "that_it"}] if match[1] == "that character" else []
        return first + [{"do": "place", "zone": match[2], "rest": bool(match[3])}]
    if text == "put it in any position of your stage as the defending character":
        return [{"do": "place", "rest": False}]
    if text == "this card's soul does not decrease by side attacking until end of turn":
        return [{"do": "status", "status": "no_side_loss", "target": "source_uid"}]
    if text == "that character cannot 【STAND】 during your opponent's next stand phase":
        return [{"do": "status", "status": "no_stand", "target": "it_first", "until": "next"}]
    if text == "【REST】 that character":
        return [{"do": "pos_that", "pos": "rest"}]
    if text == "put them into your stock in any order":
        return [{"do": "move_it", "to": "stock"}]
    match = re.fullmatch(r"choose (up to )?(\d+) characters? in battle", text)
    if match:
        return [{"do": "choose_battle", "max": int(match[2]), "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"choose (up to )?(\d+) character facing this card", text)
    if match:
        return [{"do": "choose_facing", "min": 0 if match[1] else 1}]
    match = re.fullmatch(r"put them (?:on|in) separate positions of your stage", text)
    if match:
        return [{"do": "place_each"}]
    match = re.fullmatch(r"put it in the stage position that this card was in as 【REST】", text)
    if match:
        return [{"do": "to_old_slot", "rest": True}]
    match = re.fullmatch(r"(your opponent|you) cannot use ⟦(\d+)⟧ until end of turn|until end of turn (your opponent|you) cannot use ⟦(\d+)⟧", text)
    if match and "Encore" in quotes[int(match[2] or match[4])]:
        return [{"do": "status_all", "status": "no_encore", "owner": "opp" if "opponent" in (match[1] or match[3]) else "me"}]
    if text == "choose 1 of the following abilities":
        return []
    match = re.fullmatch(r"this card gets that ability(?: until (end of turn|the end of your opponent's next turn))? ((?:⟦\d+⟧\s*)+)", text)
    if match:
        until = "next" if (match[1] or "").startswith("the end") else "turn"
        given = [quotes[int(t)] for t in re.findall(r"⟦(\d+)⟧", match[2])]
        return [{"do": "options", "options": [{"text": g, "steps": [{"do": "buff", "target": "self", "until": until, "power": 0, "soul": 0, "grant": [g]}]} for g in given]}]
    match = re.fullmatch(r"choose (\d+) (⟦\d+⟧) marker underneath this card", text)
    if match and (f := parse_filter(match[2], quotes)):
        return [{"do": "choose", "zone": "marker", "filter": f, "min": int(match[1]), "max": int(match[1]), "text": unmask(clause, quotes)}]
    if text == "put this card face up underneath that character as a marker":
        return [{"do": "that_it"}, {"do": "self_marker_on_it"}]
    if text == "choose this card":
        return []
    if text == "【REST】 them":
        return [{"do": "pos_it", "pos": "rest"}]
    match = re.fullmatch(r"【REST】 all of your other (.+?)", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"do": "rest_all", "filter": f}]
    match = re.fullmatch(r"deal (\d+) damage to your opponent (\d+) times", text)
    if match:
        return [{"do": "damage", "n": int(match[1])}] * int(match[2])
    if re.fullmatch(r"choose this card and (\d+) of your (.+?)", text) or re.fullmatch(r"choose (\d+) of your (.+?) and this card", text):
        match = re.fullmatch(r"choose (?:this card and )?(\d+) of your (.+?)(?: and this card)?", text)
        if f := parse_filter(match[2], quotes):
            return [{"do": "choose", "zone": "stage", "filter": {"other": True, **f}, "min": int(match[1]), "max": int(match[1]), "text": unmask(clause, quotes)}, {"do": "add_self_to_it"}]
    match = re.fullmatch(r"choose 1 card in your (level|clock|memory) and 1 (.+?) in your waiting room", text)
    if match and (f := parse_filter(match[2], quotes)):
        return [{"do": "choose", "zone": ZONE_WORDS[match[1]], "filter": None, "max": 1, "min": 1, "text": f"Choose 1 card in your {match[1]}"},
                {"do": "choose", "zone": "waiting", "filter": carries_type_back(f), "max": 1, "min": 1, "text": "Choose from your waiting room"}]
    if text == "move it to another open position of their stage":
        return [{"do": "place", "open": True, "keep_pos": True, "on_owner": True}]
    if text == "move this card to an open position of your center stage with a character facing this card":
        return [{"do": "self_it"}, {"do": "place", "open": True, "zone": "center", "facing": True, "keep_pos": True}]

    # Markers.
    match = re.fullmatch(r"choose (\d+) (.+?) in your hand or marker underneath this card", text)
    if match and (f := parse_filter(match[2], quotes)):
        return [{"do": "choose", "zone": "hand_or_marker", "filter": f, "max": int(match[1]), "min": int(match[1]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"put all of your (.+?) from your memory face up underneath this card in any order as markers", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"do": "memory_to_markers", "filter": f}]
    match = re.fullmatch(r"put that card face (up|down) underneath this card as a marker", text)
    if match:
        return [{"do": "marker", "face_down": match[1] == "down"}]
    match = re.fullmatch(r"put the top card of your deck (?:face (up|down) )?underneath this card as a marker", text)
    if match:
        return [{"do": "top_marker", "face_down": match[1] == "down"}]
    if text == "put this card face up underneath that character as a marker":
        return [{"do": "self_marker_on_it"}]

    # What a character can't do for a while.
    if text == "that character cannot become 【REVERSE】 until end of turn":
        return [{"do": "status", "status": "no_reverse", "target": "that"}]
    if re.fullmatch(r"that character cannot use ⟦\d+⟧ until end of turn", text):
        return [{"do": "status", "status": "no_encore", "target": "reversed"}]

    # Whose deck, how much, in what order.
    if text == "all players put the top card of their deck into their waiting room":
        return [{"do": "all_mill"}]
    match = re.fullmatch(r"put (\d+) cards from the top of your or your opponent's deck into the waiting room", text)
    if match:
        return [{"do": "which_deck", "n": int(match[1])}]
    match = re.fullmatch(r"deal either (\d+) or (\d+) damage to your opponent", text)
    if match:
        return [{"do": "damage_choice", "options": sorted((int(match[1]), int(match[2])), reverse=True)}]
    if text == "deal X damage to your opponent":
        return [{"do": "damage", "n": 0, "x_stat": "n"}]
    match = re.fullmatch(r"deal (\d+) damage X times to your opponent", text)
    if match:
        return [{"do": "damage_times", "n": int(match[1]), "x_stat": "times"}]
    match = re.fullmatch(r"reveal the top (\d+) cards of your deck", text)
    if match:
        return [{"do": "reveal_top_cards", "n": int(match[1])}]
    if text == "put the rest on the top of your deck in any order or into your waiting room":
        return [{"do": "rest_choice"}]
    if text == "choose the character with the lowest power from among those cards":
        return [{"do": "lowest_power"}]
    if text == "put all of the characters from among those cards into your opponent's waiting room":
        return [{"do": "move_it", "to": "waiting"}]
    match = re.fullmatch(r"perform the following effects 1 time in any order ((?:⟦\d+⟧\s*)+)", text)
    if match:
        options = [quotes[int(t)] for t in re.findall(r"⟦(\d+)⟧", match[1])]
        return [{"do": "any_order", "options": [{"text": o, "steps": parse_effect(o, cost)} for o in options]}]

    # Choosing cards.
    match = re.fullmatch(r"choose (up to )?(\d+) (.+?) (?:in|from) your (waiting room|clock|hand|level|memory)", text)
    if match and (f := parse_filter(match[3], quotes)):
        return [{"do": "choose", "zone": ZONE_WORDS[match[4]], "filter": carries_type_back(f), "max": int(match[2]),
                 "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"choose (up to )?(\d+) (.+?) in your opponent's (clock|waiting room|level|memory)", text)
    if match and (f := parse_filter(match[3], quotes)):
        return [{"do": "choose", "zone": ZONE_WORDS[match[4]], "owner": "opp", "filter": carries_type_back(f), "max": int(match[2]),
                 "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"choose (up to )?(\d+) (.+?) in your opponent's (center stage|back stage)", text)
    if match and (f := parse_filter(match[3], quotes)):
        return [{"do": "choose", "zone": match[4].split()[0], "owner": "opp", "filter": f, "max": int(match[2]),
                 "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"choose (up to )?(\d+) of your opponent's (.+?)", text)
    if match and (f := parse_filter(match[3], quotes)):
        return [{"do": "choose", "zone": "stage", "owner": "opp", "filter": f, "max": int(match[2]),
                 "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"choose (up to )?(\d+) of your (.+?)", text)
    if match and (f := parse_filter(match[3], quotes)):
        return [{"do": "choose", "zone": "stage", "filter": f, "max": int(match[2]),
                 "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"choose (up to )?(\d+) (.+?) in your (center|back) stage", text)
    if match and (f := parse_filter(match[3], quotes)):
        return [{"do": "choose", "zone": match[4], "filter": f, "max": int(match[2]), "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]
    match = re.fullmatch(r"choose (up to )?(\d+) (.+?) from among them", text)
    if match and (f := parse_filter(match[3], quotes)):
        return [{"do": "choose", "zone": "among", "filter": carries_type_back(f), "max": int(match[2]),
                 "min": 0 if match[1] else int(match[2]), "text": unmask(clause, quotes)}]

    # Where the chosen cards go.
    for pattern, to in MOVE_IT:
        if re.fullmatch(pattern, text):
            return [{"do": "move_it", "to": to}]
    match = re.fullmatch(r"(?:return it to your hand|put it (.+?)) or (?:put it )?(.+?)", text)
    if match:
        first = "into your hand" if text.startswith("return") else match[1]
        rest = re.split(r" or ", match[2])
        tails = [first, *rest]
        if len(tails) == 2 and tails[0] == "on the top" and tails[1].startswith("at the bottom"):
            tails = ["on the top", "at the bottom"]
        if all(t in DESTS for t in tails):
            return [{"do": "dest", "options": [DESTS[t] for t in tails]}]
    match = re.fullmatch(r"put it on the top or at the bottom of your deck(?: or into your waiting room)?", text)
    if match:
        return [{"do": "dest", "options": ["deck", "deck_bottom"] + (["waiting"] if "waiting" in text else [])}]
    match = re.fullmatch(r"put it on the top of your deck or into your waiting room", text)
    if match:
        return [{"do": "dest", "options": ["deck", "waiting"]}]
    match = re.fullmatch(r"put (?:it|them) in any position of your stage(?: as (【REST】))?", text)
    if match:
        return [{"do": "place", "rest": bool(match[1])}]
    match = re.fullmatch(r"put (?:it|them) face (up|down)(?: in any order)? underneath this card(?: in any order)? as (?:a )?markers?", text)
    if match:
        return [{"do": "marker", "face_down": match[1] == "down"}]
    if text == "put it in the stage position that this card was in":
        return [{"do": "to_old_slot"}]
    rest = {"into your waiting room": "waiting", "on the top of your deck": "deck", "at the bottom of your deck": "deck_bottom",
            "into your stock": "stock", "at the bottom of your stock": "stock", "into their waiting room": "waiting"}
    if text.startswith("put the rest ") and text.removeprefix("put the rest ") in rest:
        return [{"do": "rest", "to": rest[text.removeprefix("put the rest ")]}]
    if text == "return the rest to their deck":
        return [{"do": "rest", "to": "deck"}]
    if re.fullmatch(r"put (?:them|the rest) on the top of (?:your|their) deck in any order", text):
        return [{"do": "order_top"}]
    if re.fullmatch(r"reveal (?:it|them) to your opponent", text):
        return [{"do": "reveal_it"}]
    if text == "【STAND】 it":
        return [{"do": "pos_it", "pos": "stand"}]
    if text == "【REST】 it":
        return [{"do": "pos_it", "pos": "rest"}]
    if text == "【REVERSE】 that character":
        return [{"do": "pos_that", "pos": "reverse"}]

    # Power and soul.
    match = GETS.fullmatch(text)
    if match and (change := stat_change(match["what"] + (match["after"] or ""), quotes)) is not None:
        who = match["who"]
        target = {"that character": "it", "those characters": "it", "this card": "self",
                  "all characters in your opponent's center stage": "opp_center"}.get(who, "all")
        step = {"do": "buff", "target": target, "until": "next" if (match["until"] or "").startswith("the end") else "turn", **change}
        if target == "all":
            f = parse_filter(match["all"], quotes)
            if not f:
                return None
            step["filter"] = f
        return [step]

    # The deck, clock and hand.
    match = re.fullmatch(r"draw (up to )?(\d+) cards?", text)
    if match:
        return [{"do": "draw", "n": int(match[2]), "upto": bool(match[1])}]
    match = re.fullmatch(r"put the top(?: (\d+))? cards? of your (opponent's )?deck into (?:your|their) (waiting room|stock|clock)", text)
    if match:
        return [{"do": "top", "n": int(match[1] or 1), "owner": "opp" if match[2] else "me", "to": ZONE_WORDS[match[3]]}]
    match = re.fullmatch(r"put (\d+) cards? from the top of your deck into your (waiting room|stock|clock)", text)
    if match:
        return [{"do": "top", "n": int(match[1]), "owner": "me", "to": ZONE_WORDS[match[2]]}]
    match = re.fullmatch(r"put the bottom (\d+|X) cards? of your opponent's deck into their waiting room", text)
    if match:
        return [{"do": "top", "n": 0 if match[1] == "X" else int(match[1]), "owner": "opp", "to": "waiting", "bottom": True, **({"x_stat": "n"} if match[1] == "X" else {})}]
    match = re.fullmatch(r"put up to (\d+) cards? from the top of your deck into your (waiting room|stock|clock)", text)
    if match:
        return [{"do": "top", "n": int(match[1]), "upto": True, "owner": "me", "to": ZONE_WORDS[match[2]]}]
    match = re.fullmatch(r"put the (top|bottom) card of your (opponent's )?clock into (?:your|their) (waiting room|stock)", text)
    if match:
        return [{"do": "clock_card", "end": match[1], "owner": "opp" if match[2] else "me", "to": ZONE_WORDS[match[3]]}]
    match = re.fullmatch(r"put up to (\d+) cards? from the top of your clock into your (waiting room|stock)", text)
    if match:
        return [{"do": "clock_card", "end": "top", "owner": "me", "to": ZONE_WORDS[match[2]], "n": int(match[1]), "upto": True}]
    match = re.fullmatch(r"(?:look at|reveal) (?:(up to )?(\d+|X) cards? from the top|the top card) of your (opponent's )?deck", text)
    if match and not text.startswith("reveal the top"):
        return [{"do": "look", "n": 0 if match[2] == "X" else int(match[2] or 1), "upto": bool(match[1]), "owner": "opp" if match[3] else "me",
                 **({"x_stat": "n"} if match[2] == "X" else {})}]
    match = re.fullmatch(r"search your deck for up to (\d+) (.+?)", text)
    if match and (f := parse_filter(match[2], quotes)):
        return [{"do": "search", "max": int(match[1]), "filter": carries_type_back(f), "text": unmask(clause, quotes)}]
    if text == "shuffle your deck":
        return [{"do": "shuffle", "owner": "me"}]
    if text == "your opponent shuffles their deck":
        return [{"do": "shuffle", "owner": "opp"}]
    if text == "reveal the top card of your deck":
        return [{"do": "reveal_top"}]
    match = re.fullmatch(r"flip over (\d+) cards from the top of your deck", text)
    if match:
        return [{"do": "flip", "n": int(match[1])}]
    if text == "put them into your waiting room":
        return [{"do": "move_it", "to": "waiting"}]
    match = re.fullmatch(r"deal (\d+) damage to your opponent", text)
    if match:
        return [{"do": "damage", "n": int(match[1])}]
    if text == "【REST】 this card":
        return [{"do": "pos_self", "pos": "rest"}]
    if text == "【STAND】 this card":
        return [{"do": "pos_self", "pos": "stand"}]
    if text in ("return all cards in your waiting room to your deck", "return all cards from your waiting room to your deck"):
        return [{"do": "waiting_to_deck"}]

    # This card, and "that character" (the one the trigger was about).
    if text == "put this card at the bottom of your deck":
        return [{"do": "self_to", "to": "deck_bottom"}]
    if text == "put this card on the top of your deck":
        return [{"do": "self_to", "to": "deck"}]
    match = re.fullmatch(r"(?:return|put) this card (?:in)?to your (hand|stock|memory|waiting room|clock|level)", text)
    if match:
        return [{"do": "self_to", "to": ZONE_WORDS[match[1]]}]
    if text == "return this card to your hand or put it into your stock":
        return [{"do": "self_it"}, {"do": "dest", "options": ["hand", "stock"]}]
    if text == "put this card in an open position of your stage":
        return [{"do": "self_it"}, {"do": "place", "rest": False, "open": True}]
    if text == "return this card to its previous stage position as 【REST】":
        return [{"do": "to_old_slot", "self": True, "rest": True}]
    match = re.fullmatch(r"(?:return|put) that character (?:(?:in)?to your (hand)|into your opponent's (memory|clock|waiting room|stock|hand)|at the bottom of your opponent's (deck)|on the top of your opponent's (deck))", text)
    if match:
        to = "deck_bottom" if match[3] else "deck" if match[4] else ZONE_WORDS[match[1] or match[2]]
        return [{"do": "that_to", "to": to}]
    if text == "return that character to its previous stage position as 【REST】":
        return [{"do": "to_old_slot", "that": True, "rest": True}]

    # Choices between effects, and repeats.
    match = re.fullmatch(r"choose 1 of the following effects", text)
    if match:
        return []  # the "perform it" clause carries the options
    match = re.fullmatch(r"perform it ((?:⟦\d+⟧\s*)+)", text)
    if match:
        options = [quotes[int(t)] for t in re.findall(r"⟦(\d+)⟧", match[1])]
        return [{"do": "options", "options": [{"text": o, "steps": parse_effect(o, cost)} for o in options]}]
    match = re.fullmatch(r"perform the following (?:action|effect)(?: (\d+) times)? ⟦(\d+)⟧", text)
    if match:
        body = parse_effect(quotes[int(match[2])], cost)
        return body * int(match[1] or 1)
    if text == "perform the [standby] effect":
        return [{"do": "choose", "zone": "waiting", "filter": {"any": [{"type": "character", "level_plus": 1}]}, "max": 1, "min": 0,
                 "text": "You may choose 1 character with level equal to or lower than your level +1 in your waiting room"},
                {"do": "place", "rest": True}]
    if text == "during that attack":
        return []
    if text == "perform a trigger check 2 times on the trigger step":
        return [{"do": "double_check"}]
    return None


def has_manual(steps):
    for step in steps:
        if step["do"] == "manual":
            return True
        if has_manual(step.get("then", [])):
            return True
    return False


def parse_clauses(parts, quotes, cost):
    steps = []
    for i, part in enumerate(parts):
        match = re.fullmatch(r"[Aa]t the beginning of (your next|the next|the|your|your opponent's next) (draw phase|clock phase|main phase|climax phase|attack phase|encore step)", part)
        if match and i + 1 < len(parts):
            whose = {"your next": "me", "your": "me", "your opponent's next": "opp"}.get(match[1].lower(), "any")
            steps.append({"do": "delay", "phase": match[2].split()[0], "whose": whose, "then": parse_clauses(parts[i + 1:], quotes, cost)})
            return steps
        if re.fullmatch(r"[Aa]t the end of (?:the|your|this) turn", part) and i + 1 < len(parts):
            steps.append({"do": "delay", "phase": "end", "whose": "any", "then": parse_clauses(parts[i + 1:], quotes, cost)})
            return steps
        match = re.fullmatch(r"[Yy]ou may (.+)", part)
        if match:
            pays = match[1] == "pay the cost"
            then = parse_clauses(parts[i + 1:] if pays else [match[1], *parts[i + 1:]], quotes, cost)
            steps.append({"do": "may", "cost": cost if pays else [], "then": then,
                          "text": unmask(", ".join(parts[i:]), quotes)})
            return steps
        got = clause_steps(part, quotes, cost)
        if got is None:
            steps.append(step_manual(", ".join(parts[i:]), quotes))
            return steps
        steps += got
    return steps


def last_may(steps):
    for step in reversed(steps):
        if step["do"] == "may":
            return step
        if step.get("then"):
            found = last_may(step["then"])
            if found:
                return found
    return None


def set_x(steps, spec):
    """Fill in what X means in the steps before an "X is equal to" sentence."""
    for step in steps:
        if step.get("x_stat") or step["do"] == "choose":
            step["x"] = spec
        set_x(step.get("then", []), spec)
        for option in step.get("options", []):
            if isinstance(option, dict):
                set_x(option["steps"], spec)


def parse_effect(text, cost=None, masked=None):
    """Effect text (one or more sentences) as steps. `cost` is what "you may pay the cost" pays."""
    body, quotes = masked or mask(text)
    if body.startswith("[") and (end := closing_bracket(body)) > 0:
        cost = parse_cost(body[1:end], quotes)
        body = body[end + 1:].strip()
        if cost is None:
            return [step_manual(body, quotes)]
    body = without_reminders(body)
    steps = []
    for sentence in sentences(body):
        if has_manual(steps):  # what comes after a manual step depends on it, so it's by hand too
            steps.append(step_manual(sentence, quotes))
            continue
        plain = sentence.rstrip(".")
        if re.search(r"this card cannot be played from your hand", plain):
            continue
        match = re.match(r"If you do, (.*)", plain)
        if match:
            may = last_may(steps)
            if may:
                may["then"] += parse_clauses(clauses(match[1]), quotes, cost)
            else:
                steps.append(step_manual(sentence, quotes))
            continue
        match = re.match(r"X is equal to (.*)", plain)
        if match:
            spec = parse_x(match[1], quotes)
            if spec:
                set_x(steps, spec)
            else:
                steps = [step_manual(unmask(body, quotes), [])]
            continue
        if plain.startswith("If performed 2 times"):
            steps.append({"do": "double_check_pay"})
            continue
        match = re.match(r"For each (.+?) revealed among those cards, (.*)", plain)
        if match and (f := parse_filter(match[1], quotes)):
            steps.append({"do": "for_each", "filter": f, "then": parse_clauses(clauses(match[2]), quotes, cost)})
            continue
        if plain.startswith("If "):
            parts = clauses(plain)
            conds = []
            while parts and (cond := parse_condition(parts[0], quotes)):
                conds.append(cond)
                parts = parts[1:]
            if conds and parts:
                steps.append({"do": "if", "cond": conds, "then": parse_clauses(parts, quotes, cost)})
            else:
                steps.append(step_manual(sentence, quotes))
            continue
        steps += parse_clauses(clauses(plain), quotes, cost)
    return steps


# --- When an AUTO ability triggers -----------------------------------------------------------------------

def parse_when(words, quotes):
    """The trigger events in a "When ..." clause as a list, or None if not understood. "When this
    card attacks or becomes 【REVERSE】" is two triggers."""
    match = re.fullmatch(r"(when this card) (attacks|direct attacks|frontal attacks|is frontal attacked|becomes 【REVERSE】) or (attacks|is frontal attacked|becomes 【REVERSE】)", words.strip(), re.I)
    if match:
        first, second = parse_one_when(f"{match[1]} {match[2]}", quotes), parse_one_when(f"{match[1]} {match[3]}", quotes)
        return first + second if first and second else None
    return parse_one_when(words, quotes)


def parse_one_when(words, quotes):
    text = re.sub(r"^(?:when|at the beginning of|at the end of) ", "", words.strip(), flags=re.I)
    begin = words.lower().startswith("at the beginning")
    if begin:
        if text == "the encore step":
            return [{"on": "phase", "phase": "encore", "whose": "any"}]
        if text == "all players' attack phase":
            return [{"on": "phase", "phase": "attack", "whose": "any"}]
        match = re.fullmatch(r"your (opponent's )?(draw phase|clock phase|main phase|climax phase|attack phase|encore step|first turn)", text)
        if match:
            phase = "first_turn" if match[2] == "first turn" else match[2].split()[0]
            return [{"on": "phase", "phase": phase, "whose": "opp" if match[1] else "me"}]
        return None
    if words.lower().startswith("at the end of"):
        if text == "your turn":
            return [{"on": "phase", "phase": "end", "whose": "me"}]
        return [{"on": "attack_end"}] if text == "this card's attack" else None
    match = re.fullmatch(r"this card is placed on the stage from your hand or (deck|waiting room|memory)", text)
    if match:
        return [{"on": "play"}]
    if text == "this card is placed on the stage from your waiting room":
        return [{"on": "play"}]
    match = re.fullmatch(r"your other (.+?) or this card is placed on the stage from your hand", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "play"}, {"on": "play_other", "filter": carries_type_back(f)}]
    match = re.fullmatch(r"(your character's|this card's) trigger check reveals (.+?)", text)
    if match and (f := parse_filter(match[2], quotes)):
        return [{"on": "check_card", "any": match[1] == "your character's", "filter": f}]
    match = re.fullmatch(r"(?:your|an?) (climax(?: with \[\w+\] in (?:its|the) trigger icons?)?) is placed on your climax area", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "climax", "filter": f}]
    match = re.fullmatch(r"your (⟦\d+⟧) is put into your waiting room from the stage", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "leave_other", "filter": f}]
    if text == "your opponent levels up":
        return [{"on": "level_up", "whose": "opp"}]
    if text == "your character direct attacks":
        return [{"on": "other_attacks", "filter": None, "kind": "direct", "any": True}]
    match = re.fullmatch(r"your opponent uses ⟦\d+⟧", text)
    if match:
        return [{"on": "backup", "opponent": True}]
    if re.fullmatch(r"you use ⟦\d+⟧", text):
        return [{"on": "backup", "any_of_mine": True}]
    match = re.fullmatch(r"your other (.+?) attacks", text) or re.fullmatch(r"another of your (.+?) attacks", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "other_attacks", "filter": carries_type_back(f)}]
    match = re.fullmatch(r"your other (.+?) is put into your waiting room from the stage", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "leave_other", "filter": carries_type_back(f)}]
    match = re.fullmatch(r"your other (.+?) is placed on the stage from your hand", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "play_other", "filter": carries_type_back(f)}]
    match = re.fullmatch(r"this card or your other (.+?) is placed on the stage from your hand", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "play"}, {"on": "play_other", "filter": carries_type_back(f)}]
    match = re.fullmatch(r"your other (.*?)character's battle opponent becomes 【REVERSE】", text)
    if match and (f := parse_filter(match[1] + "character", quotes)):
        return [{"on": "other_battle_win", "filter": f}]
    if text == "your opponent's climax is placed on their climax area":
        return [{"on": "climax", "whose": "opp"}]
    if text == "you level up":
        return [{"on": "level_up"}]
    if text == "your climax is placed on your climax area":
        return [{"on": "climax"}]
    if text == "a climax is placed on your opponent's climax area":
        return [{"on": "climax", "whose": "opp"}]
    if text == "your character's trigger check reveals a climax":
        return [{"on": "any_check_climax"}]
    if text == "you use an 【ACT】":
        return [{"on": "my_act"}]
    if text == "you play an event":
        return [{"on": "my_event"}]
    if text == "this card is frontal attacked":
        return [{"on": "frontal_self"}]
    if text == "this card is side attacked":
        return [{"on": "frontal_self", "kind": "side"}]
    if text == "this card frontal attacks":
        return [{"on": "attack", "kind": "front"}]
    if text == "this card side attacks":
        return [{"on": "attack", "kind": "side"}]
    if text == "damage dealt by this card is not canceled":
        return [{"on": "no_cancel"}]
    match = re.fullmatch(r"the damage you received is (not )?canceled", text)
    if match:
        return [{"on": "received", "cancelled": not match[1]}]
    if re.fullmatch(r"this card is placed on (?:the|your) stage from your hand or attacks", text):
        return [{"on": "play"}, {"on": "attack"}]
    if re.fullmatch(r"this card is placed on the stage from your hand or put into your waiting room from the stage", text):
        return [{"on": "play"}, {"on": "leave"}]
    if re.fullmatch(r"this card is (?:played and )?placed on (?:the|your) stage from your hand(?: or by .+)?", text):
        return [{"on": "play"}]
    if text == "this card attacks":
        return [{"on": "attack"}]
    if text == "this card direct attacks":
        return [{"on": "attack", "kind": "direct"}]
    if text == "this card is put into your waiting room from the stage":
        return [{"on": "leave"}]
    if text == "this card becomes 【REVERSE】":
        return [{"on": "reverse_self"}]
    if text == "this card or this card's battle opponent becomes 【REVERSE】":
        return [{"on": "reverse_self"}, {"on": "reverse_opponent"}]
    match = re.fullmatch(r"this card's (?:level (\d+) or higher )?battle opponent becomes 【REVERSE】", text)
    if match:
        return [{"on": "reverse_opponent", **({"level_min": int(match[1])} if match[1] else {})}]
    match = re.fullmatch(r"your (other )?(.+?) becomes 【REVERSE】", text)
    if match and (f := parse_filter(match[2], quotes)):
        return [{"on": "reverse_other", "filter": f}]
    if text == "a climax is placed on your climax area":
        return [{"on": "climax"}]
    match = re.fullmatch(r"(⟦\d+⟧) is placed on your climax area", text)
    if match:
        return [{"on": "climax", "filter": parse_filter(match[1], quotes)}]
    if text == "this card is placed on your climax area from your hand":
        return [{"on": "climax_self"}]
    if text == "damage dealt by this card is canceled":
        return [{"on": "cancel"}]
    if re.fullmatch(r"you use this card's ⟦\d+⟧", text):
        return [{"on": "backup"}]
    if text == "your opponent uses an 【ACT】":
        return [{"on": "opp_act"}]
    if text == "this card's trigger check reveals a climax":
        return [{"on": "check_climax"}]
    if text == "your climax triggers":
        return [{"on": "climax_trigger"}]
    match = re.fullmatch(r"your (.+?) triggers", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "climax_trigger", "filter": f}]
    match = re.fullmatch(r"your other (.+?) is frontal attacked", text)
    if match and (f := parse_filter(match[1], quotes)):
        return [{"on": "frontal", "filter": f}]
    if text == "the character facing this card attacks":
        return [{"on": "facing_attacks"}]
    return None


# --- Whole abilities -------------------------------------------------------------------------------------

HEAD_WORDS = re.compile(r"^(?:(?:【CXCOMBO】|【CLOCK】)\s*|(?:\d/TURN@|Memory|Brainstorm|Assist|Experience|Alarm|Recollection|Change|Resonate|Backup|Accelerate|Inspire)\s+)")


def strip_head(body):
    """Take the keywords off the front of an ability. ({"once", "where"}, the rest)."""
    head = {"once": False, "where": None, "limit": 0}
    while True:
        match = HEAD_WORDS.match(body)
        if not match:
            return head, body
        word = match[0].strip()
        if word.endswith("/TURN@"):
            head["once"] = True
            head["limit"] = int(word[0])
        elif word == "Memory":
            head["where"] = "memory"
        elif word == "【CLOCK】":
            head["where"] = "clock"
        body = body[match.end():]


def closing_bracket(body):
    """Where the "[" at the front of a cost closes, since it can hold a "[gate]" of its own."""
    depth = 0
    for i, char in enumerate(body):
        depth += {"[": 1, "]": -1}.get(char, 0)
        if depth == 0:
            return i
    return -1


def take_cost(ability, body, quotes):
    """Read a "[cost]" off the front of an ability's body, if it has one. Returns the rest."""
    if not body.startswith("["):
        return body
    end = closing_bracket(body)
    if end < 0:  # never closed, so there's no telling what's cost and what's effect
        ability["manual_cost"] = True
        return body[1:].strip()
    ability["cost"] = parse_cost(body[1:end], quotes)
    if ability["cost"] is None:
        ability["cost"] = []
        ability["manual_cost"] = True
    return body[end + 1:].strip()


ENCORE_REMINDER = ("When this card is put into your waiting room from the stage, you may pay the cost. "
                   "If you do, return this card to its previous stage position as 【REST】")


def parse_auto(body, quotes, line, head):
    """An AUTO ability's body: optional [cost], then conditions, the trigger, conditions and the effect."""
    ability = {"kind": "auto", "text": line, "cost": [], "cond": [], "when": None, "steps": [], **head}
    shift = re.fullmatch(r"Shift, Level (\d+) \(At the beginning of your main phase, you may choose (?:an? |1 )?(.+?) in your hand and this card in your clock, and exchange them\)", body)
    if shift and (f := parse_filter(shift[2], quotes)):
        ability.update(where="clock", when=[{"on": "phase", "phase": "main", "whose": "me"}], cond=[{"type": "my_level", "n": int(shift[1]), "dir": "higher"}],
                       steps=[{"do": "may", "cost": [], "text": "Exchange this card with one in your hand?", "then": [
                           {"do": "self_it"}, {"do": "choose", "zone": "hand", "filter": f, "min": 1, "max": 1, "text": "Choose a card to exchange"}, {"do": "exchange"}]}])
        return ability
    sunder = re.fullmatch(r"Sunder/(⟦\d+⟧)\s*\[([^\]]*)\]\s*(?:\(.*\))?", body)
    if sunder:
        # At the end of its attack: a named marker takes the stage, and this card and its markers go underneath.
        cost = parse_cost(sunder[2], quotes)
        ability["when"] = [{"on": "attack_end"}]
        if cost is None:
            ability["steps"] = [step_manual(body, quotes)]
            return ability
        ability["cost"] = cost
        ability["steps"] = [{"do": "may", "cost": cost, "text": "Sunder?", "then": [
            {"do": "choose", "zone": "marker", "filter": parse_filter(sunder[1], quotes), "min": 1, "max": 1, "text": "Choose the marker to put on the stage"},
            {"do": "place", "rest": False}, {"do": "self_under_it"}]}]
        return ability
    match = re.fullmatch(r"(Encore|Bond/⟦\d+⟧(?:\s*⟦\d+⟧)*)\s*\[([^\]]*)\]\s*(?:\((.*)\))?", body)
    if match and (match[3] or match[1] == "Encore"):  # keywords with their rules written in the reminder text
        cost = parse_cost(match[2], quotes)
        reminder = match[3] or ENCORE_REMINDER  # an Encore given by another card leaves it out
        if match[1] == "Encore":
            ability["when"] = [{"on": "leave"}]
        else:
            ability["when"] = [{"on": "play"}]
        reminder = re.sub(r"^When [^,]*, ", "", reminder)
        if cost is None:
            ability["steps"] = [step_manual(reminder, quotes)]
            return ability
        ability["cost"] = cost
        ability["steps"] = parse_effect(reminder + ".", cost, (reminder + ".", quotes))
        return ability
    body = take_cost(ability, body, quotes)
    late, body = strip_head(body)  # keywords can come after the cost too
    ability["once"] = ability["once"] or late["once"]
    ability["limit"] = ability["limit"] or late["limit"]
    ability["where"] = ability["where"] or late["where"]
    plain = without_reminders(body)
    parts = plain.split(". ", 1)
    pieces = clauses(parts[0])
    while pieces and not re.match(r"(?:when|at the (?:beginning|end) of) ", pieces[0], re.I):
        cond = parse_condition(pieces[0], quotes)
        if not cond:
            return ability  # can't tell when it happens
        ability["cond"].append(cond)
        if cond["type"] == "self_in" and cond["where"] in ("memory", "waiting room", "level"):
            ability["where"] = ZONE_WORDS[cond["where"]]
        if cond["type"] == "self_clock_top":
            ability["where"] = "clock"
        pieces = pieces[1:]
    if not pieces:
        return ability
    ability["when"] = parse_when(pieces[0], quotes)
    if ability["when"] is None:
        return ability
    pieces = pieces[1:]
    while pieces and re.match(r"(?:and )?if ", pieces[0], re.I):
        cond = parse_condition(pieces[0], quotes)
        if not cond:
            break
        ability["cond"].append(cond)
        pieces = pieces[1:]
        while len(pieces) > 1 and (cond := parse_condition(pieces[0], quotes)):
            ability["cond"].append(cond)
            pieces = pieces[1:]
    rest = ", ".join(pieces) + (". " + parts[1] if len(parts) > 1 else "")
    ability["steps"] = parse_effect(rest, ability["cost"], (rest, quotes))
    return ability


def parse_act(body, quotes, line, head):
    ability = {"kind": "act", "text": line, "cost": [], "cond": [], "steps": [], **head}
    body = take_cost(ability, body, quotes)
    plain = without_reminders(body)
    match = re.match(r"If this card is in your waiting room, (.*)", plain)
    if match:
        ability["where"] = "waiting"
        plain = "If " + match[1]
    ability["steps"] = parse_effect(plain, ability["cost"], (plain, quotes))
    return ability


def parse_each(words, quotes):
    """What a CONT boost counts, from "+500 power for each ...". None if it isn't understood."""
    if words in ("marker underneath this card", "of the markers underneath this card"):
        return {"of": "markers", "times": 1}
    match = re.fullmatch(r"character in your opponent's (center|back) stage", words)
    if match:
        return {"of": "opp_stage", "zone": match[1], "times": 1}
    if words == "of your opponent's characters":
        return {"of": "opp_chars", "times": 1}
    match = re.fullmatch(r"(.+?) in your (level|memory|waiting room|clock|hand|stock)", words)
    if match and (f := parse_filter(match[1], quotes)):
        return {"of": "zone", "zone": ZONE_WORDS[match[2]], "filter": f, "times": 1}
    match = re.fullmatch(r"(?:of your )?(other )?(.+?)(?: in your (center|back) stage)?", words)
    if match and (f := parse_filter(match[2], quotes)):
        return {"of": "my_chars", "filter": {**f, **({"other": True} if match[1] else {})}, "stage_zone": match[3], "times": 1}
    return None


def parse_cont(body, quotes, line, head):
    """A CONT ability's stat changes and abilities given, as far as they're understood."""
    ability = {"kind": "cont", "text": line, "cond": [], "effects": [], **head}
    plain = without_reminders(body)
    match = re.fullmatch(r"During this card's battle, all players cannot play ⟦(\d+)⟧ from their hands\.?", plain)
    if match and quotes[int(match[1])] == "Backup":
        ability["no_backup"] = True
        return ability
    plain = re.sub(r"(following abilit\w+)\.\s+((?:⟦\d+⟧\s*)+)", r"\1 \2", plain)
    x_spec = None
    match = re.search(r"\.?\s*X is equal to (.*)$", plain)
    if match:
        x_spec = parse_x(match[1], quotes)
        plain = plain[:match.start()]
        if not x_spec:
            return ability
    pieces = clauses(plain)
    while len(pieces) > 1:
        cond = parse_condition(pieces[0], quotes)
        if not cond:
            break
        ability["cond"].append(cond)
        pieces = pieces[1:]
    if len(pieces) != 1:
        return ability
    text = pieces[0].rstrip(".")
    if re.fullmatch(r"this card can be played from your hand without fulfilling color requirements", text, re.I):
        ability["color_free"] = {"self": True}
        return ability
    match = re.fullmatch(r"(?:all of your|your) (.+?) gets? the following ability while in your hand\.?\s*⟦(\d+)⟧", text, re.I)
    if match and "without fulfilling color requirements" in quotes[int(match[2])]:
        f = parse_filter(match[1], quotes)
        if f:
            ability["color_free"] = {"filter": carries_type_back(f)}
        return ability
    if "while in your hand" in text or "in the trigger icon" in text:
        return ability
    match = re.fullmatch(r"(?P<who>[Tt]his card|[Tt]he character facing this card|[Aa]ll of your (?P<all>.+?)|[Yy]our (?P<one>.+?)) gets? (?P<what>.+?)"
                         r"(?: for each (?P<each>.+?))?", text)
    if not match:
        return ability
    what = match["what"]
    change = stat_change(what, quotes)
    if change is None:
        return ability
    who = match["all"] or match["one"]
    target = {"type": "facing"} if match["who"].lower().startswith("the character facing") else {"type": "self"}
    if who:
        front = " in front of this card" in who
        middle = " in the middle position of your center stage" in who
        words = who.replace(" in front of this card", "").replace(" in the middle position of your center stage", "")
        f = parse_filter(words, quotes)
        if not f:
            return ability
        target = {"type": "front" if front else "middle" if middle else "all", "filter": carries_type_back(f)}
    effect = {"target": target, **change}
    if x_spec:
        effect["x"] = x_spec
    if match["each"]:
        effect["per"] = parse_each(match["each"], quotes)
        if not effect["per"]:
            return ability
    ability["effects"].append(effect)
    return ability


def unreadable(kind, line):
    """An ability this module failed on: it has to be done by hand, like any other it can't read."""
    return {"kind": kind, "text": line, "cost": [], "cond": [], "when": None, "effects": [], "once": False, "where": None,
            "steps": [{"do": "manual", "text": line}]}


def parse_tagged(tag, body, quotes, line):
    head, body = strip_head(body)
    if tag == "AUTO":
        return parse_auto(body, quotes, line, head)
    if tag == "CONT":
        return parse_cont(body, quotes, line, head)
    if tag == "COUNTER":
        return {"kind": "counter", "text": line, "cost": [], "cond": [], **head, "steps": parse_effect(body, None, (body, quotes))}
    if body.startswith("【COUNTER】"):  # Backup: game.counter_play plays these from the hand
        return {"kind": "backup", "text": line, "cost": [], "cond": [], "steps": [], **head}
    return parse_act(body, quotes, line, head)


@lru_cache(maxsize=4096)
def parse_cached(text):
    """Card text comes from outside and new sets have new wording, so no line of it may ever stop a page or a game."""
    abilities = []
    event_lines = []
    for line in ability_lines(canonical(text)):
        if line.startswith("("):  # a trigger icon's reminder text
            continue
        body, quotes = mask(line)
        tag = re.match(r"【(AUTO|ACT|CONT|COUNTER)】\s*", body)
        if not tag:
            event_lines.append(line)
            continue
        try:
            abilities.append(parse_tagged(tag[1], body[tag.end():], quotes, line))
        except Exception:
            log.exception("Couldn't read card text: %s", line)
            abilities.append(unreadable(tag[1].lower(), line))
    if event_lines:  # An event's lines happen one after another when it's played.
        steps = []
        for line in event_lines:
            try:
                body, quotes = mask(line)
                _, body = strip_head(body)
                steps += parse_effect(body, None, (body, quotes))
            except Exception:
                log.exception("Couldn't read card text: %s", line)
                steps.append({"do": "manual", "text": line})
        abilities.append({"kind": "event", "text": " ".join(event_lines), "cost": [], "cond": [], "once": False,
                          "where": None, "steps": steps})
    return tuple(abilities)


def by_hand_parts(text):
    """What in a card's text the game can't carry out itself, as the words that would be shown for
    doing it by hand. Includes abilities the card gives to itself or others."""
    def in_steps(steps):
        for step in steps:
            if step["do"] == "manual":
                yield step["text"]
            for granted in step.get("grant", []):
                yield from by_hand_parts(granted)
            yield from in_steps(step.get("then", []))
            for option in step.get("options", []):
                if isinstance(option, dict):
                    yield from in_steps(option["steps"])

    parts = []
    for ability in parse(text):
        if ability.get("manual_cost") or (ability["kind"] == "auto" and not ability.get("when")):
            parts.append(ability["text"])
        parts += in_steps(ability.get("steps", []))
        for effect in ability.get("effects", []):
            for granted in effect.get("grant", []):
                parts += by_hand_parts(granted)
    return parts


def parse(text):
    """The abilities in a card's text. The result is shared: copy before changing it."""
    return parse_cached(text or "")
