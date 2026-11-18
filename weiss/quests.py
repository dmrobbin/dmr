"""World mode's quests (see docs/world-mode.md, "Quests"): stages of objectives, then a choice of endings.

A quest is a Quest row: its key, title, giver and the friendship rank it gates, and a spec (checked by `check`):

    {"key": "ember-and-rose", "title": "Ember and Rose", "giver": "Ruby Rose", "gates": 5,
     "about": "Ruby's mother's cloak has gone missing, and she thinks she knows who took it.",
     "offer": ["them: Can I ask you something? It's important.", "player: Sure."],
     "requires": {"quests": ["first-steps"], "flags": ["met_ruby"], "rank": 2},
     "stages": [{"text": "Find out who took it",
                 "objectives": [{"do": "defeat", "cpus": ["Cinder Fall"]}, {"do": "have_card", "card": "RWBY/WX03-001"}]}],
     "endings": [{"key": "return", "title": "Give it back to Ruby", "locks": ["ashes"], "rewards": [{"coins": 500}],
                  "script": ["them (pleased): You found it!"]},
                 {"key": "keep", "title": "Hand it to Cinder", "to": "Cinder Fall", "removes": ["Ruby Rose"],
                  "flags": ["sided_with_cinder"]}],
     "rewards": [{"coins": 300}, {"card": "RWBY/WX03-002", "copies": 2}], "hidden": false}

How it plays out on a save (save.quests["log"][key]):
- Offered: a CPU offers its quests when they're open (`offerable`). A gate quest opens once the player has the points
  for its rank: until it's done, the giver's rank waits one below (`cap`), however many points pile up.
- Active: its stages go in order; a stage is done when all its objectives are. Objectives that are a state (having a
  card, a rank, a flag) are checked whenever the save changes (`advance`, from world.changed); the rest are done as
  they happen (a duel, a gift, going somewhere, talking, handing a card over).
- Settling: every stage done, it waits for the player to choose an ending, by talking to whoever that ending's turned
  in to. Each ending says what it would close first (`fallout`): quests it locks, CPUs who leave town for good, and
  everything that needs them.
- Done, with its ending; or failed, closed by another quest's ending. There's no deadline and no giving up: a quest
  only fails when a choice closes it, and the player is told before they make it.
"""
import random
import re
from types import SimpleNamespace

from django.urls import reverse

from . import buffs, chatter, packs, world
from .lists import is_climax
from .models import Card, CpuProfile, GiftItem, Quest, Scene, WorldPlace

MAX_TEXT = 1000
MAX_STAGES = 12
MAX_OBJECTIVES = 8
MAX_ENDINGS = 6
MAX_COPIES = 50
NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,59}")
STATES = ("have_card", "collect", "rank", "flag")  # checked whenever the save changes
REWARDS = ("coins", "card", "pack", "gift", "flag")
PACKS = ("lucky_pack", "climax_pack", "level_pack", "color_pack")  # packs a quest can give (world.SHOP_SPECIALS), from the giver's set

OBJECTIVES = {  # do: (fields it can have, what it's for: the reference's words)
    "have_card": ({"card", "copies"}, "Have a card (any printing of its name) among the save's cards."),
    "collect": ({"count", "trait", "color", "set"}, "Have so many different cards with a trait, of a color or from a set (by its number)."),
    "combo": ({"card", "climax", "against", "count", "win"}, "Start a character's climax combo in a duel (with that climax, against those CPUs, "
              "that many times; `win`: only in a duel that's won)."),
    "defeat": ({"cpus"}, "Beat each of these CPUs in a duel."),
    "lose_to": ({"cpu"}, "Lose a duel to this CPU."),
    "win_with": ({"card", "against"}, "Win a duel having played this card."),
    "win_deck": ({"colors", "trait", "set", "max_rarity", "against"}, "Win a duel with a deck that keeps to these: only these colors, "
                 "a trait on every character, one set, no card rarer than max_rarity."),
    "stakes": ({"fee", "against"}, "Win a high-stakes duel with an entry fee of at least this."),
    "streak": ({"wins", "against"}, "Win so many duels in a row (a loss starts it again)."),
    "beat_different": ({"count", "temperament", "cpus"}, "Beat so many different CPUs (of a temperament, or among these)."),
    "visit": ({"place", "days", "times", "scene"}, "Be at a place (on these days, at these times); its scene plays there, so something happens."),
    "give_card": ({"card", "copies", "to"}, "Hand a card over to a CPU, for good: it leaves the save's cards and decks."),
    "give_gift": ({"gift", "to"}, "Give a CPU this gift."),
    "rank": ({"cpu", "rank"}, "Reach this friendship rank with a CPU."),
    "talk": ({"to", "script"}, "Talk to a CPU: its script plays (chatter, with choices that can set flags)."),
    "flag": ({"flag", "text"}, "Have a flag (a chatter choice or an ending sets them): say what it means in `text`."),
}
COMMON = {"do", "text"}
AT_TIME = ("in the morning", "at noon", "in the evening", "at night")  # "Go to the Beach at night"
NAMED_CPUS = {"cpus", "cpu", "against", "to"}  # fields that name CPUs


def joined(script):
    """A script as text: a file can write one as a list of lines."""
    return "\n".join(str(line) for line in script) if isinstance(script, list) else str(script or "")


# ---------------------------------------------------------------- Checking a quest

def known_context(extra_keys=(), loose=False):
    """What a quest can name, from the database: for check. loose: quests it requires or locks needn't exist yet
    (they're listed in .pending instead), so two quests that lock each other can be written one at a time."""
    return SimpleNamespace(
        loose=loose, pending=[],
        cpus={name.lower(): name for name in CpuProfile.objects.values_list("name", flat=True)},
        cards=lambda serial: Card.objects.filter(serial_number=serial).exists(),
        places={key for key in WorldPlace.objects.values_list("key", flat=True)},
        gifts={key for key in GiftItem.objects.values_list("key", flat=True)},
        scenes=lambda name: Scene.objects.filter(name__iexact=name).exists(),
        ranks=world.rank_names(),
        quests={*Quest.objects.values_list("key", flat=True), *extra_keys},
    )


def check(data, context=None, giver=None):
    """({key, title, giver (a name or None), gate_rank, spec}, [problems]) for a quest as written. `giver`: the CPU a
    pack entry gives it to (it needn't name one then). context: what it can name (known_context; offline, a namespace
    with cards None to skip checking them)."""
    context = context or known_context()
    problems = []
    if not isinstance(data, dict):
        return None, ["A quest is written as {\"key\": ..., \"title\": ..., \"stages\": [...], \"endings\": [...]}."]
    allowed = {"key", "title", "giver", "gates", "about", "offer", "requires", "stages", "endings", "rewards", "hidden"}
    if extra := sorted(set(data) - allowed):
        problems.append(f"No such fields as {', '.join(extra)}.")
    key = str(data.get("key") or "")
    if not NAME.fullmatch(key):
        problems.append("Its key is lowercase letters, numbers, - and _, at most 60.")
    title = str(data.get("title") or "").strip()
    if not title or len(title) > 100:
        problems.append("It needs a title, at most 100 characters.")
    where = f"“{title or key}”"

    def cpu_name(name, what):
        found = context.cpus.get(str(name or "").strip().lower())
        if not found:
            problems.append(f"{what}: there's no CPU called “{name}”.")
        return found or str(name or "")

    giver = giver or data.get("giver")
    giver = cpu_name(giver, f"{where} giver") if giver else None
    gate = data.get("gates")
    if gate is not None:
        if not giver:
            problems.append(f"{where}: only a quest with a giver can gate a friendship rank.")
        if not isinstance(gate, int) or not 1 <= gate < len(context.ranks):
            problems.append(f"{where}: gates is a rank from 1 to {len(context.ranks) - 1}.")
    about = str(data.get("about") or "").strip()
    if not about or len(about) > MAX_TEXT:
        problems.append(f"{where}: it needs an about (what the quest log says it is), at most {MAX_TEXT} characters.")

    def script(raw, what):
        text = joined(raw)
        if text.strip():
            problems.extend(f"{what}, line {at}: {error}" for at, error in chatter.compile_chatter(text, gifts=context.gifts)[1])
        return text

    offer = script(data.get("offer"), f"{where} offer")
    requires = data.get("requires") or {}
    if not isinstance(requires, dict) or set(requires) - {"quests", "flags", "rank"}:
        problems.append(f"{where} requires: write it as {{\"quests\": [...], \"flags\": [...], \"rank\": 2}}.")
        requires = {}
    def unknown_quest(other, what):
        """A quest key that isn't there: a problem, or (writing one quest at a time) one to write next."""
        if getattr(context, "loose", False) and NAME.fullmatch(str(other)):
            context.pending.append(f"{what} “{other}”, which isn't written yet: it does nothing until a quest has that key.")
        else:
            problems.append(f"{where} {what} a quest “{other}” that there isn't.")

    for needed in requires.get("quests", []):
        if needed not in context.quests and needed != key:
            unknown_quest(needed, "requires")
    for flag in requires.get("flags", []):
        if not NAME.fullmatch(str(flag)):
            problems.append(f"{where} requires: “{flag}” isn't a flag name (lowercase letters, numbers, - and _).")
    if "rank" in requires and (not giver or not isinstance(requires["rank"], int) or not 0 <= requires["rank"] < len(context.ranks)):
        problems.append(f"{where} requires: rank is the friendship rank with the giver it needs, 0 to {len(context.ranks) - 1}.")

    def objective(raw, at):
        if not isinstance(raw, dict) or raw.get("do") not in OBJECTIVES:
            said = f"there's no objective “{raw['do']}”" if isinstance(raw, dict) and raw.get("do") else "write it as {\"do\": ...}"
            problems.append(f"{at}: {said}; objectives are {', '.join(OBJECTIVES)}.")
            return None
        do = raw["do"]
        fields, _ = OBJECTIVES[do]
        if extra := sorted(set(raw) - fields - COMMON):
            problems.append(f"{at} ({do}): no such fields as {', '.join(extra)}.")
        obj = dict(raw)
        for field in NAMED_CPUS & set(raw):
            names = raw[field] if isinstance(raw[field], list) else [raw[field]]
            if field in ("cpus", "against") and (not isinstance(raw[field], list) or not raw[field]):
                problems.append(f"{at} ({do}): {field} is a list of CPU names.")
                continue
            found = [cpu_name(name, f"{at} ({do})") for name in names]
            obj[field] = found if isinstance(raw[field], list) else found[0]
        for field in ("card", "climax"):
            if field in raw or (field == "card" and do in ("have_card", "combo", "win_with", "give_card")):
                serial = str(raw.get(field) or "")
                if not serial:
                    problems.append(f"{at} ({do}): it needs a {field}, by serial number.")
                elif context.cards is not None and not context.cards(serial):
                    problems.append(f"{at} ({do}): there's no card {serial}.")

        def whole(field, low, high, default=None):
            value = raw.get(field, default)
            if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
                problems.append(f"{at} ({do}): {field} goes from {low} to {high}.")

        if do in ("have_card", "give_card"):
            whole("copies", 1, MAX_COPIES, 1)
        if do == "collect":
            whole("count", 1, 200)
            if not any(raw.get(f) for f in ("trait", "color", "set")):
                problems.append(f"{at} (collect): say what to collect: a trait, a color or a set.")
        if do == "combo":
            whole("count", 1, 20, 1)
        if do in ("defeat",) and "cpus" not in raw:
            problems.append(f"{at} (defeat): name the CPUs to beat in cpus.")
        if do == "lose_to" and "cpu" not in raw:
            problems.append(f"{at} (lose_to): name the CPU in cpu.")
        if do == "win_deck":
            if not any(raw.get(f) for f in ("colors", "trait", "set", "max_rarity")):
                problems.append(f"{at} (win_deck): give the deck a rule: colors, trait, set or max_rarity.")
            if "colors" in raw and (not isinstance(raw["colors"], list) or set(raw["colors"]) - set(buffs.COLORS)):
                problems.append(f"{at} (win_deck): colors is a list of {', '.join(buffs.COLORS)}.")
            if "max_rarity" in raw and raw["max_rarity"] not in packs.GRADES:
                problems.append(f"{at} (win_deck): max_rarity is a rarity such as C, U, R or RR.")
        if do == "collect" and "color" in raw and raw["color"] not in buffs.COLORS:
            problems.append(f"{at} (collect): color is one of {', '.join(buffs.COLORS)}.")
        if do in ("collect", "win_deck") and "set" in raw and not isinstance(raw["set"], int):
            problems.append(f"{at} ({do}): set is a set's number (its expansion id).")
        if do == "stakes":
            whole("fee", 1, 1_000_000)
        if do == "streak":
            whole("wins", 2, 20)
        if do == "beat_different":
            whole("count", 1, 100)
            if "temperament" in raw and raw["temperament"] not in world.GAIN:
                problems.append(f"{at} (beat_different): temperament is one of {', '.join(world.GAIN)}.")
        if do == "visit":
            if raw.get("place") not in context.places:
                problems.append(f"{at} (visit): there's no place “{raw.get('place')}”.")
            if "days" in raw and (not isinstance(raw["days"], list) or any(d not in range(7) for d in raw["days"])):
                problems.append(f"{at} (visit): days are a list of 0 (Monday) to 6 (Sunday).")
            if "times" in raw and (not isinstance(raw["times"], list) or any(t not in range(4) for t in raw["times"])):
                problems.append(f"{at} (visit): times are a list of 0 (morning) to 3 (night).")
            if not raw.get("scene"):
                problems.append(f"{at} (visit): name the scene that plays there (scene), so something happens when they arrive.")
            elif not context.scenes(str(raw["scene"])):
                problems.append(f"{at} (visit): there's no scene called “{raw['scene']}”.")
        if do in ("give_card", "give_gift", "talk") and "to" not in raw:
            problems.append(f"{at} ({do}): name who it's for in to.")
        if do == "give_gift" and raw.get("gift") not in context.gifts:
            problems.append(f"{at} (give_gift): there's no gift “{raw.get('gift')}”.")
        if do == "rank":
            if "cpu" not in raw:
                problems.append(f"{at} (rank): name the CPU in cpu.")
            whole("rank", 1, len(context.ranks) - 1)
        if do == "talk":
            if not joined(raw.get("script")).strip():
                problems.append(f"{at} (talk): it needs a script, what's said.")
            obj["script"] = script(raw.get("script"), f"{at} (talk)")
        if do == "flag":
            if not NAME.fullmatch(str(raw.get("flag") or "")):
                problems.append(f"{at} (flag): flag is a flag's name (lowercase letters, numbers, - and _).")
            if not str(raw.get("text") or "").strip():
                problems.append(f"{at} (flag): say what the player has to do in text; a flag's name means nothing to them.")
        if "text" in raw and (not isinstance(raw["text"], str) or len(raw["text"]) > 200):
            problems.append(f"{at} ({do}): text is at most 200 characters.")
        return obj

    stages = []
    raw_stages = data.get("stages")
    if not isinstance(raw_stages, list) or not 1 <= len(raw_stages) <= MAX_STAGES:
        problems.append(f"{where}: it needs 1 to {MAX_STAGES} stages.")
        raw_stages = []
    for n, stage in enumerate(raw_stages, 1):
        at = f"{where} stage {n}"
        if not isinstance(stage, dict) or set(stage) - {"text", "objectives"}:
            problems.append(f"{at}: write it as {{\"text\": ..., \"objectives\": [...]}}.")
            continue
        text = str(stage.get("text") or "").strip()
        if not text or len(text) > 200:
            problems.append(f"{at}: it needs a text (what the quest log calls this step), at most 200 characters.")
        objectives = stage.get("objectives")
        if not isinstance(objectives, list) or not 1 <= len(objectives) <= MAX_OBJECTIVES:
            problems.append(f"{at}: it needs 1 to {MAX_OBJECTIVES} objectives.")
            objectives = []
        stages.append({"text": text, "objectives": [o for i, raw in enumerate(objectives, 1) if (o := objective(raw, f"{at} objective {i}"))]})

    def rewards(raw, at):
        given = []
        if not isinstance(raw or [], list):
            problems.append(f"{at}: rewards are a list.")
            return given
        for i, reward in enumerate(raw or [], 1):
            kinds = set(reward) & set(REWARDS) if isinstance(reward, dict) else set()
            if len(kinds) != 1 or set(reward) - set(REWARDS) - {"copies", "text"}:
                problems.append(f"{at} reward {i}: write it as one of {{\"coins\": 500}}, {{\"card\": serial, \"copies\": 2}}, "
                                "{\"pack\": \"lucky_pack\"}, {\"gift\": key}, {\"flag\": name, \"text\": ...}.")
                continue
            kind = kinds.pop()
            what = reward[kind]
            if kind == "coins" and (not isinstance(what, int) or not 1 <= what <= 100_000):
                problems.append(f"{at} reward {i}: coins go from 1 to 100,000.")
            elif kind == "card" and context.cards is not None and not context.cards(str(what)):
                problems.append(f"{at} reward {i}: there's no card {what}.")
            elif kind == "pack" and what not in PACKS:
                problems.append(f"{at} reward {i}: a pack is one of {', '.join(PACKS)}.")
            elif kind == "gift" and what not in context.gifts:
                problems.append(f"{at} reward {i}: there's no gift “{what}”.")
            elif kind == "flag" and (not NAME.fullmatch(str(what)) or not str(reward.get("text") or "").strip()):
                problems.append(f"{at} reward {i}: a flag needs a name and a text saying what it means for the player.")
            if "copies" in reward and (kind != "card" or not isinstance(reward["copies"], int) or not 1 <= reward["copies"] <= MAX_COPIES):
                problems.append(f"{at} reward {i}: copies (1 to {MAX_COPIES}) go with a card.")
            given.append(dict(reward))
        return given

    endings, seen = [], set()
    raw_endings = data.get("endings")
    if not isinstance(raw_endings, list) or not 1 <= len(raw_endings) <= MAX_ENDINGS:
        problems.append(f"{where}: it needs 1 to {MAX_ENDINGS} endings (one, if there's no choice to make).")
        raw_endings = []
    ending_fields = {"key", "title", "about", "to", "requires", "locks", "removes", "flags", "rewards", "script"}
    for n, ending in enumerate(raw_endings, 1):
        at = f"{where} ending {n}"
        if not isinstance(ending, dict):
            problems.append(f"{at}: write it as {{\"key\": ..., \"title\": ...}}.")
            continue
        if extra := sorted(set(ending) - ending_fields):
            problems.append(f"{at}: no such fields as {', '.join(extra)}.")
        ekey = str(ending.get("key") or "")
        if not NAME.fullmatch(ekey) or ekey in seen:
            problems.append(f"{at}: each ending needs a key of its own (lowercase letters, numbers, - and _).")
        seen.add(ekey)
        etitle = str(ending.get("title") or "").strip()
        if not etitle or len(etitle) > 100:
            problems.append(f"{at}: it needs a title, what the player chooses, at most 100 characters.")
        to = ending.get("to") or giver
        if not to:
            problems.append(f"{at}: say who it's turned in to (to), since the quest has no giver.")
        else:
            to = cpu_name(to, at)
        locks = ending.get("locks") or []
        if not isinstance(locks, list) or key in locks:
            problems.append(f"{at}: locks is a list of other quests' keys.")
        else:
            for lock in locks:
                if lock not in context.quests:
                    if getattr(context, "loose", False) and NAME.fullmatch(str(lock)):
                        context.pending.append(f"“{etitle}” locks “{lock}”, which isn't written yet: it closes nothing until a quest has that key.")
                    else:
                        problems.append(f"{at}: locks “{lock}”, and there's no quest with that key.")
        removes = [cpu_name(name, f"{at} removes") for name in (ending.get("removes") or [])]
        flags = ending.get("flags") or []
        if any(not NAME.fullmatch(str(flag)) for flag in flags):
            problems.append(f"{at}: flags are names: lowercase letters, numbers, - and _.")
        needs = ending.get("requires") or []
        if not isinstance(needs, list) or len(needs) > MAX_OBJECTIVES:
            problems.append(f"{at}: requires is a list of at most {MAX_OBJECTIVES} objectives.")
            needs = []
        endings.append({**{k: v for k, v in ending.items() if k in ending_fields}, "key": ekey, "title": etitle,
                        "about": str(ending.get("about") or ""), "to": to, "locks": list(locks) if isinstance(locks, list) else [],
                        "removes": removes, "flags": list(flags),
                        "requires": [o for i, raw in enumerate(needs, 1) if (o := objective(raw, f"{at} requires {i}"))],
                        "rewards": rewards(ending.get("rewards"), at), "script": script(ending.get("script"), f"{at} script")})
    spec = {"about": about, "offer": offer, "requires": requires, "stages": stages, "endings": endings,
            "rewards": rewards(data.get("rewards"), where), "hidden": bool(data.get("hidden", False))}
    return {"key": key, "title": title, "giver": giver, "gate_rank": gate, "spec": spec}, problems


def as_file(quest):
    """A quest as it's written (check reads it back): for the staff editor and CPU files."""
    spec = quest.spec or {}
    lines = lambda text: text.split("\n") if text else []
    data = {"key": quest.key, "title": quest.title}
    if quest.giver_id:
        data["giver"] = quest.giver.name
    if quest.gate_rank:
        data["gates"] = quest.gate_rank
    data["about"] = spec.get("about", "")
    if spec.get("offer"):
        data["offer"] = lines(spec["offer"])
    if spec.get("requires"):
        data["requires"] = spec["requires"]
    data["stages"] = [{"text": stage["text"], "objectives": [{**o, "script": lines(o["script"])} if o.get("script") else o
                                                               for o in stage["objectives"]]} for stage in spec.get("stages", [])]
    data["endings"] = []
    for ending in spec.get("endings", []):
        written = {k: v for k, v in ending.items() if v not in ("", [], None)}
        if quest.giver_id and written.get("to") == quest.giver.name:
            written.pop("to")
        if ending.get("script"):
            written["script"] = lines(ending["script"])
        data["endings"].append(written)
    if spec.get("rewards"):
        data["rewards"] = spec["rewards"]
    if spec.get("hidden"):
        data["hidden"] = True
    return data


def save_quest(fields, order=None):
    """Make or update the Quest a checked quest (check's fields) describes."""
    giver = CpuProfile.objects.filter(name__iexact=fields["giver"]).first() if fields["giver"] else None
    quest, _ = Quest.objects.update_or_create(key=fields["key"], defaults={
        "title": fields["title"], "giver": giver, "gate_rank": fields["gate_rank"], "spec": fields["spec"],
        **({"order": order} if order is not None else {})})
    return quest


# ---------------------------------------------------------------- Names in a quest, found

class Lookup:
    """CPUs by name and cards by serial, found once for one request."""

    def __init__(self):
        self._cpus, self._cards, self._names = {}, {}, {}

    def cpu(self, name):
        key = str(name or "").lower()
        if key not in self._cpus:
            self._cpus[key] = CpuProfile.objects.filter(name__iexact=key).first() if key else None
        return self._cpus[key]

    def cpu_id(self, name):
        found = self.cpu(name)
        return found.pk if found else None

    def card(self, serial):
        if serial not in self._cards:
            self._cards[serial] = Card.objects.filter(serial_number=serial).first()
        return self._cards[serial]

    def printings(self, serial):
        """Every card with the same name as this one: a quest's card is any printing of it."""
        card = self.card(serial)
        if not card:
            return set()
        if card.name not in self._names:
            self._names[card.name] = set(Card.objects.filter(name=card.name).values_list("pk", flat=True))
        return self._names[card.name]

    def card_name(self, serial):
        card = self.card(serial)
        return card.name if card else serial


def lookup(save):
    if not hasattr(save, "_quest_lookup"):
        save._quest_lookup = Lookup()
    return save._quest_lookup


# ---------------------------------------------------------------- A save's quests

def quests(save):
    """{key: Quest}, every quest there is, found once per save object (a request)."""
    if not hasattr(save, "_quests"):
        save._quests = {quest.key: quest for quest in Quest.objects.select_related("giver")}
    return save._quests


def log(save):
    return save.quests.setdefault("log", {})


def status(save, key):
    """"" (not taken), "active", "settling" (every stage done, an ending to choose), "done" or "failed"."""
    return (save.quests.get("log", {}).get(key) or {}).get("status", "")


def gone(save):
    """CPUs an ending sent away for good: they're never seen in this save's town again."""
    return set(save.quests.get("gone", []))


def cap(save, cpu_id):
    """The highest rank this CPU's friendship can be now: one below its first gate quest that isn't done (none: no cap)."""
    gates = [quest.gate_rank for quest in quests(save).values()
             if quest.giver_id == int(cpu_id) and quest.gate_rank and status(save, quest.key) != "done"]
    return min(gates) - 1 if gates else None


def gate_quest(save, cpu_id):
    """The gate quest holding this CPU's friendship now, or None."""
    held = cap(save, cpu_id)
    if held is None:
        return None
    return next((quest for quest in quests(save).values()
                 if quest.giver_id == int(cpu_id) and quest.gate_rank == held + 1 and status(save, quest.key) != "done"), None)


def estranged(save, cpu_id):
    """Whether a choice has closed this CPU's friendship for good: a gate quest of theirs failed."""
    return any(quest.giver_id == int(cpu_id) and quest.gate_rank and status(save, quest.key) == "failed" for quest in quests(save).values())


def offerable(save, quest):
    """Whether the quest's giver would offer it now: not taken or closed, its giver here to stay, what it requires
    done, and for a gate quest, the points its rank takes with every earlier gate passed."""
    if quest.key in log(save) or not quest.giver_id or quest.giver_id in gone(save):
        return False
    requires = (quest.spec or {}).get("requires") or {}
    if any(status(save, key) != "done" for key in requires.get("quests", [])):
        return False
    if any(not world.has_flag(save, flag) for flag in requires.get("flags", [])):
        return False
    rank = world.rank_of(save, quest.giver_id)
    if rank < requires.get("rank", 0):
        return False
    if quest.gate_rank:
        points = save.relations.get(str(quest.giver_id), {}).get("points", 0)
        return rank == quest.gate_rank - 1 and world.rank_for(points) >= quest.gate_rank
    return True


def ending_of(quest, key):
    return next((ending for ending in (quest.spec or {}).get("endings", []) if ending["key"] == key), None)


def current(save, quest):
    """[(objective key, objective)] the quest is working on now: its stage's, or once it's settling, every ending's
    own requirements."""
    entry = log(save).get(quest.key) or {}
    spec = quest.spec or {}
    if entry.get("status") == "active":
        stage = entry.get("stage", 0)
        if stage < len(spec.get("stages", [])):
            return [(f"{stage}.{i}", o) for i, o in enumerate(spec["stages"][stage]["objectives"])]
    if entry.get("status") == "settling":
        return [(f"e.{e['key']}.{i}", o) for e in spec.get("endings", []) for i, o in enumerate(e.get("requires", []))]
    return []


def need(obj):
    """How many of something an objective counts to."""
    return {"defeat": len(obj.get("cpus", [])), "combo": obj.get("count", 1), "streak": obj.get("wins", 1),
            "beat_different": obj.get("count", 1), "have_card": obj.get("copies", 1), "give_card": 1,
            "collect": obj.get("count", 1), "rank": obj.get("rank", 1)}.get(obj["do"], 1)


def held(save, obj):
    """How many of a state objective the save has now."""
    found = lookup(save)
    do = obj["do"]
    if do == "have_card":
        return sum(save.pool.get(str(pk), 0) for pk in found.printings(obj["card"]))
    if do == "collect":
        cards = Card.objects.filter(pk__in=[int(pk) for pk, n in save.pool.items() if n > 0])
        if obj.get("set"):
            cards = cards.filter(expansion_id=obj["set"])
        if obj.get("color"):
            cards = cards.filter(color__iexact=obj["color"])
        names = {card.name for card in cards if not obj.get("trait") or has_trait(card, obj["trait"])}
        return len(names)
    if do == "rank":
        cpu_id = found.cpu_id(obj["cpu"])
        return world.rank_of(save, cpu_id) if cpu_id else 0
    if do == "flag":
        return int(world.has_flag(save, obj["flag"]))
    return 0


def has_trait(card, trait):
    return trait.lower() in {part.strip().lower() for part in (card.traits or "").split("・")}


def progress(save, quest, obj_key, obj):
    """(have, need) for one objective now."""
    entry = log(save).get(quest.key) or {}
    if obj_key in entry.get("done", []):
        return need(obj), need(obj)
    if obj["do"] in STATES:
        return min(held(save, obj), need(obj)), need(obj)
    value = entry.get("progress", {}).get(obj_key, 0)
    return (len(value) if isinstance(value, list) else value), need(obj)


def met(save, quest, obj_key, obj):
    have, wanted = progress(save, quest, obj_key, obj)
    return have >= wanted


def tick(save, quest, obj_key, value=None):
    """Count one more towards an objective (or add `value` to its list of different ones): True if that's news."""
    entry = log(save)[quest.key]
    found = entry.setdefault("progress", {})
    if value is None:
        found[obj_key] = found.get(obj_key, 0) + 1
        return True
    seen = found.setdefault(obj_key, [])
    if value in seen:
        return False
    seen.append(value)
    return True


def finish(save, quest, obj_key):
    """An objective done, for good."""
    entry = log(save)[quest.key]
    if obj_key not in entry.setdefault("done", []):
        entry["done"].append(obj_key)


def news(save, text, quest=None, link=None):
    save.quests.setdefault("news", []).append({"text": text, **({"quest": quest.title} if quest else {}), **({"link": link} if link else {})})


def advance(save):
    """Settle what's changed: state objectives met now, and stages done (the quest moves on, or waits for an ending).
    Returns whether the save's quests changed."""
    if not any(entry.get("status") == "active" for entry in save.quests.get("log", {}).values()):
        return False
    moved = False
    for quest in quests(save).values():
        entry = log(save).get(quest.key)
        while entry and entry.get("status") == "active":
            objectives = current(save, quest)
            if not objectives or not all(met(save, quest, key, obj) for key, obj in objectives):
                break
            for key, _ in objectives:
                finish(save, quest, key)
            stages = quest.spec.get("stages", [])
            entry["stage"] = entry.get("stage", 0) + 1
            moved = True
            if entry["stage"] >= len(stages):
                entry["status"] = "settling"
                news(save, f"Done: {stages[-1]['text']}. {settle_hint(save, quest)}", quest)
            else:
                news(save, f"Done: {stages[entry['stage'] - 1]['text']}. Next: {stages[entry['stage']]['text']}.", quest)
    return moved


def settle_hint(save, quest):
    """Who to see to finish a quest."""
    found = lookup(save)
    names = list(dict.fromkeys(ending["to"] for ending in quest.spec.get("endings", []) if found.cpu_id(ending["to"]) not in gone(save)))
    if not names:
        return ""
    if len(names) == 1:
        return f"Talk to {names[0]} to finish it."
    return f"Talk to {', '.join(names[:-1])} or {names[-1]} to choose how it ends."


# ---------------------------------------------------------------- What happens, as it happens

def against(save, obj, cpu):
    """Whether a duel with this CPU counts for an objective (any CPU, unless it names some)."""
    return not obj.get("against") or cpu.name.lower() in {name.lower() for name in obj["against"]}


def deck_keeps(save, obj, deck):
    """Whether a deck ({card id: copies}) keeps to a win_deck objective's rules."""
    cards = Card.objects.in_bulk([int(pk) for pk in deck])
    for card in cards.values():
        if obj.get("set") and card.expansion_id != obj["set"]:
            return False
        if is_climax(card):
            continue  # climaxes have no traits, and their colors follow the deck's
        if obj.get("colors") and card.color not in obj["colors"]:
            return False
        if obj.get("trait") and not has_trait(card, obj["trait"]):
            return False
    if obj.get("max_rarity"):
        limit = packs.grade_of(obj["max_rarity"])
        if any(packs.grade_of(packs.rarity_of(card)) > limit for card in cards.values()):
            return False
    return bool(cards)


def duel_finished(save, room, won):
    """A world duel's over: what it did for the quests under way (beating someone, a combo, a card played, a deck's
    rules, stakes, a run of wins)."""
    cpu = CpuProfile.objects.filter(pk=room.cpu_profile_id).first()
    snapshot = save.quests.pop("duel", None) or {}
    if not cpu:
        return
    records = (room.state.get("records") or {}).get(str(room.host_id), {})
    played = set(records.get("played", []))
    combos = [tuple(pair) for pair in records.get("combos", [])]
    deck = snapshot.get("deck") if snapshot.get("room") == room.pk else None
    found = lookup(save)
    for quest in quests(save).values():
        for key, obj in current(save, quest):
            if met(save, quest, key, obj):
                continue
            do = obj["do"]
            counted = False
            if do == "defeat" and won and cpu.name.lower() in {n.lower() for n in obj["cpus"]}:
                counted = tick(save, quest, key, cpu.name)
            elif do == "lose_to" and not won and cpu.name.lower() == obj["cpu"].lower():
                counted = tick(save, quest, key)
            elif do == "combo" and against(save, obj, cpu) and (won or not obj.get("win")):
                characters = found.printings(obj["card"])
                climaxes = found.printings(obj["climax"]) if obj.get("climax") else None
                if any(char in characters and (climaxes is None or climax in climaxes) for char, climax in combos):
                    counted = tick(save, quest, key)
            elif do == "win_with" and won and against(save, obj, cpu) and played & found.printings(obj["card"]):
                counted = tick(save, quest, key)
            elif do == "win_deck" and won and against(save, obj, cpu) and deck and deck_keeps(save, obj, deck):
                counted = tick(save, quest, key)
            elif do == "stakes" and won and against(save, obj, cpu) and room.world_stake >= obj["fee"]:
                counted = tick(save, quest, key)
            elif do == "streak" and against(save, obj, cpu):
                if won:
                    counted = tick(save, quest, key)
                elif log(save)[quest.key].get("progress", {}).get(key):
                    log(save)[quest.key]["progress"][key] = 0
                    news(save, f"Your run of wins is over: {describe(save, obj)} starts again.", quest)
            elif do == "beat_different" and won and (not obj.get("temperament") or cpu.temperament == obj["temperament"]) \
                    and (not obj.get("cpus") or cpu.name.lower() in {n.lower() for n in obj["cpus"]}):
                counted = tick(save, quest, key, cpu.name)
            if counted:
                have, wanted = progress(save, quest, key, obj)
                news(save, f"{describe(save, obj)}: {'done' if have >= wanted else f'{have}/{wanted}'}.", quest)
    advance(save)


def duel_started(save, room):
    """Keep the deck a duel's played with, as it was when it started: a deck rule is checked against that."""
    save.quests["duel"] = {"room": room.pk, "deck": dict((str(pk), n) for pk, n in room.host_deck.entries.values_list("card_id", "quantity"))
                           if room.host_deck_id else {}}


def gift_given(save, cpu, item):
    for quest in quests(save).values():
        for key, obj in current(save, quest):
            if obj["do"] == "give_gift" and obj["gift"] == item.key and obj["to"].lower() == cpu.name.lower() and not met(save, quest, key, obj):
                tick(save, quest, key)
                news(save, f"{describe(save, obj)}: done.", quest)
    advance(save)


def arrived(save):
    """The save is somewhere, at some time (it went there, or time moved on): visits done there."""
    place = world.place_of(save)
    if not place:
        return
    weekday, time = (save.turn // len(save.TIMES)) % 7, save.turn % len(save.TIMES)
    for quest in quests(save).values():
        for key, obj in current(save, quest):
            if obj["do"] != "visit" or obj["place"] != place.key or met(save, quest, key, obj):
                continue
            if ("days" in obj and weekday not in obj["days"]) or ("times" in obj and time not in obj["times"]):
                continue
            tick(save, quest, key)
            link = None
            scene = Scene.objects.filter(name__iexact=obj.get("scene") or "").first() if obj.get("scene") else None
            if scene and not save.flags.get("scene"):
                save.flags["scene"] = {"scene": scene.pk}
                link = reverse("weiss:world_scene", args=[save.slot])
            news(save, f"{describe(save, obj)}: done.", quest, link)
    advance(save)


# ---------------------------------------------------------------- Talking: offers, objectives and endings

def offers(save, cpu):
    return [quest for quest in quests(save).values() if quest.giver_id == cpu.pk and offerable(save, quest)]


def actions(save, cpu):
    """What the player can do about quests with this CPU now: {"offers", "talks", "hands", "settles"}."""
    found = lookup(save)
    talks, hands, settles = [], [], []
    for quest in quests(save).values():
        st = status(save, quest.key)
        if st == "active":
            for key, obj in current(save, quest):
                if obj["do"] in ("talk", "give_card") and obj["to"].lower() == cpu.name.lower() and not met(save, quest, key, obj):
                    item = {"quest": quest.key, "title": quest.title, "objective": key, "text": describe(save, obj)}
                    if obj["do"] == "talk":
                        talks.append(item)
                    else:
                        have = held(save, {"do": "have_card", "card": obj["card"]})
                        hands.append({**item, "card": found.card_name(obj["card"]), "copies": obj.get("copies", 1), "have": have})
        elif st == "settling" and any(ending["to"].lower() == cpu.name.lower() for ending in quest.spec.get("endings", [])):
            settles.append({"quest": quest.key, "title": quest.title})
    return {"offers": [{"quest": quest.key, "title": quest.title} for quest in offers(save, cpu)],
            "talks": talks, "hands": hands, "settles": settles}


def find_quest(save, key):
    quest = quests(save).get(key)
    if not quest:
        raise ValueError("That quest isn't there any more.")
    return quest


def objective_at(quest, key):
    """The objective with this key (stage.index, or e.ending.index)."""
    spec = quest.spec or {}
    try:
        if key.startswith("e."):
            _, ending, i = key.split(".")
            return ending_of(quest, ending)["requires"][int(i)]
        stage, i = key.split(".")
        return spec["stages"][int(stage)]["objectives"][int(i)]
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def script_for(key):
    """A quest script a talk is playing, by its talk key ("quest:<quest>:offer", ":talk:<objective>" or
    ":end:<ending>"), compiled; None if it's gone."""
    _, quest_key, part = key.split(":", 2)
    quest = Quest.objects.filter(key=quest_key).first()
    if not quest:
        return None
    if part == "offer":
        text = quest.spec.get("offer", "")
    elif part.startswith("talk:"):
        text = (objective_at(quest, part[5:]) or {}).get("script", "")
    elif part.startswith("end:"):
        text = (ending_of(quest, part[4:]) or {}).get("script", "")
    else:
        return None
    compiled, errors = chatter.compile_chatter(text) if text.strip() else ({"labels": {}, "steps": []}, [])
    return None if errors else compiled


def offer_panel(save, quest):
    """What the offer box shows: the quest, what it asks first, what it gives, and whether its ending is a choice."""
    spec = quest.spec
    endings = spec.get("endings", [])
    return {"quest": quest.key, "title": quest.title, "about": spec.get("about", ""), "giver": quest.giver.name if quest.giver else "",
            "first": spec["stages"][0]["text"] if spec.get("stages") else "",
            "objectives": [{"text": describe(save, obj), "card": objective_card(save, obj)} for obj in spec["stages"][0]["objectives"]]
            if spec.get("stages") else [],
            "stages": len(spec.get("stages", [])), "rewards": reward_words(save, quest),
            "choice": len(endings) > 1, "closes": any(e.get("locks") or e.get("removes") for e in endings),
            "gate": world.rank_names()[quest.gate_rank] if quest.gate_rank else ""}


def accept(save, cpu, key):
    quest = find_quest(save, key)
    if quest.giver_id != cpu.pk or not offerable(save, quest):
        raise ValueError(f"{cpu.name} isn't offering that now.")
    log(save)[key] = {"status": "active", "stage": 0, "since": save.turn, "progress": {}, "done": []}
    first = quest.spec["stages"][0]["text"]
    events = [{"quest": f"Quest taken: {quest.title}. First: {first}."}]
    advance(save)
    return events + taken_news(save)


def taken_news(save):
    """Quest news made in a talk, shown there instead of later."""
    found = save.quests.pop("news", [])
    return [{"quest": item["text"]} for item in found]


def talked(save, cpu, key, obj_key):
    quest = find_quest(save, key)
    obj = objective_at(quest, obj_key)
    if not obj or obj["do"] != "talk" or (obj_key, obj) not in current(save, quest) or met(save, quest, obj_key, obj):
        return []
    tick(save, quest, obj_key)
    advance(save)
    return [{"quest": f"{describe(save, obj)}: done."}] + taken_news(save)


def hand_over(save, cpu, key, obj_key):
    """Hand a card over for a give_card objective: the copies leave the save's cards, the commonest printings first,
    and any deck with more than are left loses them too. Returns the talk's events."""
    quest = find_quest(save, key)
    obj = objective_at(quest, obj_key)
    if not obj or obj["do"] != "give_card" or obj["to"].lower() != cpu.name.lower() or status(save, key) != "active" \
            or (obj_key, obj) not in current(save, quest) or met(save, quest, obj_key, obj):
        raise ValueError("There's nothing to hand over for that now.")
    found = lookup(save)
    copies = obj.get("copies", 1)
    printings = sorted((card for card in Card.objects.filter(pk__in=found.printings(obj["card"])) if save.pool.get(str(card.pk))),
                       key=lambda card: (packs.grade_of(packs.rarity_of(card)), card.serial_number))
    if sum(save.pool[str(card.pk)] for card in printings) < copies:
        raise ValueError(f"You need {copies} {found.card_name(obj['card'])} to hand over.")
    left = copies
    for card in printings:
        take = min(left, save.pool[str(card.pk)])
        save.pool[str(card.pk)] -= take
        if not save.pool[str(card.pk)]:
            del save.pool[str(card.pk)]
        left -= take
        if not left:
            break
    trimmed = []
    for deck in save.decks.all():
        for entry in deck.entries.filter(card_id__in=[card.pk for card in printings]):
            if entry.quantity > save.pool.get(str(entry.card_id), 0):
                entry.quantity = save.pool.get(str(entry.card_id), 0)
                entry.save(update_fields=["quantity"]) if entry.quantity else entry.delete()
                trimmed.append(deck.name)
    finish(save, quest, obj_key)
    advance(save)
    name = found.card_name(obj["card"])
    events = [{"quest": f"You hand {name}{f' ×{copies}' if copies > 1 else ''} to {cpu.name}."}]
    if trimmed:
        events.append({"quest": f"It's gone from {', '.join(sorted(set(trimmed)))} too: check {'it' if len(set(trimmed)) == 1 else 'them'} before your next duel."})
    return events + taken_news(save)


def fallout(save, quest, ending):
    """What choosing this ending would close for good, worked out as it would happen: {"quests": [{key, title, giver,
    why, held (the rank its giver stays at, for a gate quest)}], "leave": [CPU names]}. Quests close when an ending locks
    them, when their giver leaves, when they need a closed quest, or when what's left of them needs someone who's gone."""
    found = lookup(save)
    gone_ids = gone(save) | {cpu_id for name in ending.get("removes", []) if (cpu_id := found.cpu_id(name))}
    gone_names = {name.lower() for name in ending.get("removes", [])} | \
                 {cpu.name.lower() for cpu in CpuProfile.objects.filter(pk__in=gone(save))}
    closed = {}
    ranks = world.rank_names()
    changed = True
    while changed:
        changed = False
        for other in quests(save).values():
            if other.key == quest.key or other.key in closed or status(save, other.key) in ("done", "failed"):
                continue
            requires = (other.spec or {}).get("requires") or {}
            giver = other.giver.name if other.giver else ""
            why, reason = None, ""
            if other.key in ending.get("locks", []):
                why, reason = f"“{ending['title']}” closes it.", "locked"
            elif other.giver_id and other.giver_id in gone_ids:
                why, reason = f"{giver} leaves town.", "left"
            elif any(key in closed or status(save, key) == "failed" for key in requires.get("quests", [])):
                why, reason = "It needs a quest this closes.", "needs"
            elif (who := needs_gone(save, other, gone_names)):
                why, reason = f"It needs {who}, who leaves town.", "needs"
            if why:
                closed[other.key] = {"key": other.key, "title": other.title, "giver": giver, "why": why, "reason": reason,
                                     "held": ranks[other.gate_rank - 1] if other.gate_rank and other.giver_id not in gone_ids else ""}
                changed = True
    return {"quests": list(closed.values()), "leave": list(ending.get("removes", []))}


def needs_gone(save, quest, gone_names):
    """The name of someone gone that what's left of this quest can't do without, or None."""
    if not gone_names:
        return None
    entry = log(save).get(quest.key) or {}
    spec = quest.spec or {}
    stage = entry.get("stage", 0) if entry.get("status") == "active" else (len(spec.get("stages", [])) if entry.get("status") == "settling" else 0)
    left = [(f"{s}.{i}", o) for s in range(stage, len(spec.get("stages", []))) for i, o in enumerate(spec["stages"][s]["objectives"])]
    for key, obj in left:
        if key in entry.get("done", []):
            continue
        for field in ("cpu", "to"):
            if obj.get(field) and obj[field].lower() in gone_names:
                return obj[field]
        if obj["do"] == "defeat":
            beaten = {name.lower() for name in entry.get("progress", {}).get(key, [])}
            missing = [name for name in obj["cpus"] if name.lower() in gone_names and name.lower() not in beaten]
            if missing:
                return missing[0]
        if obj.get("against") and all(name.lower() in gone_names for name in obj["against"]):
            return obj["against"][0]
    endings = spec.get("endings", [])
    if endings and all(ending["to"].lower() in gone_names for ending in endings):
        return endings[0]["to"]
    return None


def settle_panel(save, cpu, key):
    """The endings the player can choose with this CPU: each with whether it's ready (its own requirements) and what
    it would close."""
    quest = find_quest(save, key)
    if status(save, key) != "settling":
        raise ValueError("That quest isn't ready to finish.")
    choices = []
    for ending in quest.spec.get("endings", []):
        if ending["to"].lower() != cpu.name.lower():
            continue
        needs = [(f"e.{ending['key']}.{i}", obj) for i, obj in enumerate(ending.get("requires", []))]
        missing = [describe(save, obj) for k, obj in needs if not met(save, quest, k, obj)]
        choices.append({"key": ending["key"], "title": ending["title"], "about": ending.get("about", ""), "missing": missing,
                        "fallout": fallout(save, quest, ending), "rewards": reward_words(save, quest, ending)})
    others = [ending["to"] for ending in quest.spec.get("endings", []) if ending["to"].lower() != cpu.name.lower()]
    return {"quest": key, "title": quest.title, "endings": choices, "elsewhere": list(dict.fromkeys(others))}


def choose(save, cpu, key, ending_key, confirmed):
    """Choose how a quest ends: its rewards, its flags, and everything it closes, for good. An ending that closes
    anything must be `confirmed` (the page asks first, saying what). Returns (the ending, events to show after its
    script)."""
    quest = find_quest(save, key)
    ending = ending_of(quest, ending_key)
    if status(save, key) != "settling" or not ending or ending["to"].lower() != cpu.name.lower():
        raise ValueError("That isn't a way this quest can end here.")
    for i, obj in enumerate(ending.get("requires", [])):
        if not met(save, quest, f"e.{ending_key}.{i}", obj):
            raise ValueError(f"Not yet: {describe(save, obj)}.")
    found = fallout(save, quest, ending)
    if (found["quests"] or found["leave"]) and not confirmed:
        raise ValueError("This ending closes other quests: choose it again to confirm.")
    before = world.rank_of(save, quest.giver_id) if quest.giver_id else 0
    entry = log(save)[key]
    entry.update(status="done", ending=ending_key, finished=save.turn)
    events = [{"quest": f"Quest complete: {quest.title}.", "done": True}]
    for text, link in give_rewards(save, quest, [*quest.spec.get("rewards", []), *ending.get("rewards", [])]):
        events.append({"reward": text, **({"link": link} if link else {})})
    held_flags = [flag for flag in save.flags.get("set", []) if flag not in ending.get("flags", [])]
    save.flags["set"] = held_flags + list(ending.get("flags", []))
    lookups = lookup(save)
    for name in ending.get("removes", []):
        cpu_id = lookups.cpu_id(name)
        if cpu_id and cpu_id not in gone(save):
            save.quests.setdefault("gone", []).append(cpu_id)
            events.append({"quest": f"{name} has left town for good."})
    for closed in found["quests"]:
        log(save)[closed["key"]] = {**(log(save).get(closed["key"]) or {}), "status": "failed",
                                    "closed_by": {"quest": key, "ending": ending_key}, "why": closed["why"], "reason": closed["reason"],
                                    "finished": save.turn}
        events.append({"quest": f"Closed: {closed['title']}" + (f" ({closed['giver']})" if closed["giver"] else "") + "."})
    advance(save)
    if quest.giver_id and quest.giver_id not in gone(save):
        after = world.rank_of(save, quest.giver_id)
        if after > before:
            giver = quest.giver
            events.append({"rank_reached": world.rank_names()[after], "who": giver.name, "relation": world.standing(save, giver.pk)})
            events += [{"reward": text, **({"link": link} if link else {})} for text, link in world.reward_ranks(save, giver, after)]
            if giver.pk == cpu.pk:
                events += world.rank_up(save, giver, after)
            else:
                found_line = chatter.pick(giver, "rank_up", after)
                if found_line and found_line[2]:
                    save.flags["scene"] = {"scene": found_line[2].pk, "cpu": giver.pk}
                    events.append({"scene": reverse("weiss:world_scene", args=[save.slot])})
    # Anything with a link to follow (a pack's cards) goes last, after what closed and the rank reached, so following
    # it misses nothing; a scene still to play waits in the town too (world.town's "scene").
    events += taken_news(save)
    linked = [event for event in events if event.get("link")]
    scene = [event for event in events if event.get("scene")]
    return ending, [event for event in events if event not in linked and event not in scene] + linked + scene


def give_rewards(save, quest, rewards):
    """Give a quest's rewards: [(what it says, a link or "")]."""
    given = []
    found = lookup(save)
    for reward in rewards:
        if "coins" in reward:
            save.money += reward["coins"]
            given.append((f"{reward['coins']:,} coins", ""))
        elif "card" in reward:
            card = found.card(reward["card"])
            if card:
                buffs.add_to_pool(save, card.pk, reward.get("copies", 1))
                given.append((f"{card.name} ×{reward.get('copies', 1)}", ""))
        elif "pack" in reward:
            if quest.giver_id and (made := world.give_reward(save, quest.giver, "pack", reward["pack"])):
                given.append(made)
            elif not quest.giver_id:
                pool = packs.Pool.for_set(save.expansion_id)
                if pool:
                    pack = packs.open_pack(pool, random, packs.BOOSTED_PACK if reward["pack"] == "lucky_pack" else packs.PACK)
                    for pull in pack:
                        buffs.add_to_pool(save, pull.card.pk, 1)
                    world.reward_opening(save, pool, pack, save.expansion_id)
                    given.append((f"A pack of {pool.set_name}", reverse("weiss:world_opened", args=[save.slot])))
        elif "gift" in reward:
            item = GiftItem.objects.filter(key=reward["gift"]).first()
            if item:
                save.gifts[item.key] = min(save.gifts.get(item.key, 0) + 1, world.MAX_GIFTS)
                given.append((f"{item.icon} {item.name}".strip(), ""))
        elif "flag" in reward:
            if reward["flag"] not in save.flags.get("set", []):
                save.flags["set"] = save.flags.get("set", []) + [reward["flag"]]
            given.append((reward.get("text") or "Something new", ""))
    return given


# ---------------------------------------------------------------- Words for the player

def reward_words(save, quest, ending=None):
    """What a quest (or one ending) gives, in words, or ["A surprise"] if it's hidden."""
    if (quest.spec or {}).get("hidden"):
        return ["A surprise"]
    return [reward_text(save, reward) for reward in [*([] if ending else quest.spec.get("rewards", [])), *((ending or {}).get("rewards", []))]]


def reward_text(save, reward):
    """One reward in words: "500 coins", "Crescent Rose ×2", "a lucky pack", or what a flag's text says."""
    if reward.get("text"):
        return reward["text"]
    if "coins" in reward:
        return f"{reward['coins']:,} coins"
    if "card" in reward:
        return f"{lookup(save).card_name(reward['card'])} ×{reward.get('copies', 1)}"
    if "pack" in reward:
        return f"a {buffs.BUFFS[reward['pack']].name.lower()}"
    if "gift" in reward:
        item = GiftItem.objects.filter(key=reward["gift"]).first()
        return f"{item.icon} {item.name}".strip() if item else "a gift"
    return "something new"


def names(items):
    items = list(items)
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}" if items else ""


CARD_OBJECTIVES = ("have_card", "give_card", "combo", "win_with")  # objectives about a card: shown with its facts


def card_facts(card):
    """What a player needs to find a card: its picture, colour, level, cost, type, rarity and set (any printing of its
    name counts, so this is the printing the quest names)."""
    return {"name": card.name, "serial": card.serial_number, "url": reverse("weiss:card", args=[card.pk]),
            "image": reverse("weiss:card_image", args=[card.pk]), "color": card.color or "", "level": card.level,
            "cost": card.cost, "type": card.card_type or "", "rarity": card.rarity or "", "set": card.expansion or ""}


def objective_card(save, obj):
    """The card facts an objective is about, or None."""
    if obj.get("do") not in CARD_OBJECTIVES or not obj.get("card"):
        return None
    card = lookup(save).card(obj["card"])
    return card_facts(card) if card else None


def describe(save, obj):
    """An objective in words, for the quest log and the talk box."""
    if obj.get("text"):
        return obj["text"]
    found = lookup(save)
    do = obj["do"]
    vs = f" against {names(obj['against']) if len(obj['against']) < 3 else 'one of ' + names(obj['against'])}" if obj.get("against") else ""
    card = found.card_name(obj["card"]) if obj.get("card") else ""
    if do == "have_card":
        return f"Have the card {card}" + (f" ×{obj['copies']}" if obj.get("copies", 1) > 1 else "")
    if do == "collect":
        what = " ".join(filter(None, [obj.get("color")]))
        source = f" with the trait {obj['trait']}" if obj.get("trait") else ""
        from_set = ""
        if obj.get("set"):
            set_name = Card.objects.filter(expansion_id=obj["set"]).values_list("expansion", flat=True).first() or f"set {obj['set']}"
            from_set = f" from {set_name}"
        return f"Collect {obj['count']} different {what + ' ' if what else ''}cards{source}{from_set}"
    if do == "combo":
        climax = f" with {found.card_name(obj['climax'])}" if obj.get("climax") else ""
        times = f" {obj['count']} times" if obj.get("count", 1) > 1 else ""
        lead = "Win a duel using" if obj.get("win") else "Pull off"
        return f"{lead} {card}'s climax combo{climax}{vs}{times}"
    if do == "defeat":
        return f"Beat {names(obj['cpus'])} in a duel" + ("" if len(obj["cpus"]) == 1 else ", each of them")
    if do == "lose_to":
        return f"Lose a duel to {obj['cpu']}"
    if do == "win_with":
        return f"Win a duel{vs} having played {card}"
    if do == "win_deck":
        rules = []
        if obj.get("colors"):
            rules.append(f"only {' and '.join(obj['colors'])} cards")
        if obj.get("trait"):
            rules.append(f"every character a {obj['trait']}")
        if obj.get("set"):
            rules.append("cards from one set")
        if obj.get("max_rarity"):
            rules.append(f"nothing rarer than {obj['max_rarity']}")
        return f"Win a duel{vs} with a deck of {', '.join(rules)}"
    if do == "stakes":
        return f"Win a high-stakes duel{vs} of {obj['fee']:,} coins or more"
    if do == "streak":
        return f"Win {obj['wins']} duels in a row{vs}"
    if do == "beat_different":
        who = "villains" if obj.get("temperament") == "villain" else f"{obj['temperament']} CPUs" if obj.get("temperament") else "opponents"
        among = f" among {names(obj['cpus'])}" if obj.get("cpus") else ""
        return f"Beat {obj['count']} different {who}{among}"
    if do == "visit":
        place = WorldPlace.objects.filter(key=obj["place"]).values_list("name", flat=True).first() or obj["place"]
        days = sorted(obj.get("days") or [])
        times = sorted(obj.get("times") or [])
        when = ""
        if days and len(days) < 7:
            when += " on " + " or ".join(save.DAYS[d] for d in days)
        if times and len(times) < 4:
            when += " " + " or ".join(AT_TIME[t] for t in times)
        return f"Go to the {place}{when}"
    if do == "give_card":
        return f"Give the card {card}" + (f" ×{obj['copies']}" if obj.get("copies", 1) > 1 else "") + f" to {obj['to']}"
    if do == "give_gift":
        item = GiftItem.objects.filter(key=obj["gift"]).first()
        return f"Give {obj['to']} {f'{item.icon} {item.name}'.strip() if item else obj['gift']}"
    if do == "rank":
        return f"Become {world.rank_names()[obj['rank']]} with {obj['cpu']}"
    if do == "talk":
        return f"Talk to {obj['to']}"
    return obj.get("flag", "")


def journal(save):
    """The quest log as its page shows it: {"offered", "active", "done", "failed"}, each a list of quests in words."""
    found = lookup(save)
    ranks = world.rank_names()
    sections = {"offered": [], "active": [], "done": [], "failed": []}
    for quest in quests(save).values():
        entry = log(save).get(quest.key)
        spec = quest.spec or {}
        giver = quest.giver if quest.giver_id else None
        base = {"key": quest.key, "title": quest.title, "about": spec.get("about", ""), "giver": giver.name if giver else "",
                "avatar": giver.avatar if giver else None, "gate": ranks[quest.gate_rank] if quest.gate_rank else ""}
        if not entry:
            if offerable(save, quest):
                sections["offered"].append({**base, "about": f"{giver.name} has something to ask you. Find them in town and talk to them."})
            continue
        st = entry["status"]
        if st in ("active", "settling"):
            stages = []
            for n, stage in enumerate(spec.get("stages", [])):
                if n > entry.get("stage", 0):
                    break
                objectives = []
                for i, obj in enumerate(stage["objectives"]):
                    have, wanted = progress(save, quest, f"{n}.{i}", obj)
                    objectives.append({"text": describe(save, obj), "card": objective_card(save, obj), "have": have, "need": wanted,
                                       "done": have >= wanted})
                stages.append({"text": stage["text"], "done": n < entry.get("stage", 0), "objectives": objectives})
            endings = []
            if st == "settling":
                for ending in spec.get("endings", []):
                    missing = [describe(save, obj) for i, obj in enumerate(ending.get("requires", []))
                               if not met(save, quest, f"e.{ending['key']}.{i}", obj)]
                    endings.append({"title": ending["title"], "to": ending["to"], "missing": missing,
                                    "away": found.cpu_id(ending["to"]) in gone(save)})
            sections["active"].append({**base, "settling": st == "settling", "stages": stages, "endings": endings,
                                       "rewards": reward_words(save, quest), "left": len(spec.get("stages", [])) - entry.get("stage", 0) - 1})
        elif st == "done":
            ending = ending_of(quest, entry.get("ending")) or {}
            sections["done"].append({**base, "ending": ending.get("title", ""), "ending_about": ending.get("about", "")})
        elif st == "failed":
            by = entry.get("closed_by") or {}
            closer = quests(save).get(by.get("quest"))
            chosen = ending_of(closer, by.get("ending")) if closer else None
            sections["failed"].append({**base, "why": "" if entry.get("reason") == "locked" else entry.get("why", ""), "by": closer.title if closer else "",
                                       "by_ending": chosen["title"] if chosen else "",
                                       "held": ranks[quest.gate_rank - 1] if quest.gate_rank else ""})
    return sections


def counts(save):
    """How many quests are under way, and how many are ready to finish, for the town's Quests button."""
    entries = save.quests.get("log", {}).values()
    return {"active": sum(entry.get("status") in ("active", "settling") for entry in entries),
            "ready": sum(entry.get("status") == "settling" for entry in entries)}
