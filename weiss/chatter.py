"""World mode's chatter: what a CPU says in the town's talk box (the Chatter model), written in a compact form of the
scene language (weiss.scenes). The box has no stage, so there's no cast and no staging: the CPU being talked to is
`them`, with `player` and `narrator` as in a scene. What a script can do:

    them: Hello, {player}!         them (pleased): …   them (dismayed): …   (moods: CPU_MOODS)
    player: Hi!                    narrator: …
    choice What now?  /  - Option -> label (set flag)
    label x / goto x / end / set flag / unset flag / if flag goto x / if not flag goto x
    if rank >= 2 goto x            points +5           give money 100     give gift coffee
    fight                          fight stake 500     (offers a duel, a high-stakes one for that entry fee)

The script runs on the server (play), so its points, coins and stakes are only ever what it says. weiss.world decides
when each context plays and keeps what it changes.
"""
import random
import re

from . import scenes
from .models import Chatter, GiftItem

THEM = "them"
CPU_MOODS = ("main", "pleased", "dismayed")
CONTEXTS = dict(Chatter.CONTEXTS)
FIRST_LINE_ONLY = {"before_duel", "after_win", "after_loss", "hello", "goodbye"}  # shown as one line, outside a conversation
MAX_POINTS = 50  # one `points` line's most, either way
MAX_MONEY = 5000  # one `give money` line's most
MAX_STAKE = 100_000
RUNAWAY = 500  # steps in one go with nothing for the player to do: a goto loop

NAME = scenes.NAME
RANK_IF = re.compile(rf"if\s+rank\s*(?P<op>>=|<=|==|=|!=|>|<)\s*(?P<rank>\d+)\s+goto\s+(?P<label>{NAME})", re.I)
POINTS = re.compile(r"points\s+(?P<n>[+-]?\s*\d+)", re.I)
GIVE_MONEY = re.compile(r"give\s+(?:money|coins)\s+(?P<n>\d+)", re.I)
GIVE_GIFT = re.compile(r"give\s+gift\s+(?P<key>[\w-]+)", re.I)
FIGHT = re.compile(r"fight(?:\s+stake\s+(?P<stake>\d+))?", re.I)
OPTION_ACT = re.compile(rf"(?P<verb>set|unset)\s+(?P<what>{NAME})", re.I)
STAGED = re.compile(r"(?:background|screen|wait|offer|cast)\b", re.I)
OPS = {">=": int.__ge__, "<=": int.__le__, "==": int.__eq__, "=": int.__eq__, "!=": int.__ne__, ">": int.__gt__, "<": int.__lt__}

REFERENCE = [  # for staff, as scenes.REFERENCE: (what to write, what it does, what to insert when clicked)
    ("them: Hello, {player}!", "The CPU being talked to speaks. {player} is the player's name, {name} the CPU's, {rank} the "
     "player's rank with them. A click goes on to the next line.", "them: "),
    ("them (pleased): Really?", f"With a mood: {', '.join(CPU_MOODS)} (their pictures for when the player loses and wins).", "them (pleased): "),
    ("player: Hi!", "The player speaks.", "player: "),
    ("narrator: They wave.", "Words from nobody in particular.", "narrator: "),
    ("choice What do you say?", "Asks the player. The options follow, one a line.", "choice "),
    ("- Sure -> yes (set keen)", "An option, under a choice: “-> label” is optional, and so is “(set flag)” or “(unset flag)”.", "- "),
    ("if rank >= 2 goto close", "Goes to a label by the player's rank with them (0 the first); also >, <, <=, ==, !=.", "if rank >= 1 goto "),
    ("points +5", f"Changes how much they like the player (at most {MAX_POINTS} either way). Once a day for each line.", "points +"),
    ("give money 100", f"Gives the player coins (at most {MAX_MONEY:,}). Once a day for each line.", "give money "),
    ("give gift iced-coffee", "Gives the player a gift item, by its key. Once a day for each line.", "give gift "),
    ("fight", "Offers a duel: the player chooses Duel or Not now.", "fight"),
    ("fight stake 500", "Offers a high-stakes duel with that entry fee; a win pays it back twice.", "fight stake "),
    ("set met / unset met", "Remembers (or forgets) something for the save. A place opens when the save has its flag.", "set "),
    ("if met goto again", "Goes to a label if a flag is set (“if not met …” for the opposite).", "if  goto "),
    ("label again / goto again", "A place to go to, and going there.", "label "),
    ("end", "Ends the talk. The end of the script does too.", "end"),
    ("# a note", "Notes for you; the player never sees them.", "# "),
]


def compile_chatter(script, gifts=None):
    """({"labels": {label: step}, "steps": [...]}, [(line number, what's wrong)]), as scenes.compile_scene. gifts: the
    gift keys there are, to check "give gift" against (None to look in the database)."""
    labels, steps, errors, jumps = {}, [], [], []
    choice = None

    def close_choice():
        if choice is not None and not choice["options"]:
            errors.append((choice["line"], "A choice needs at least one option under it, written “- …”."))

    if len(script) > scenes.MAX_SCRIPT:
        return {"labels": {}, "steps": []}, [(1, f"A script can be at most {scenes.MAX_SCRIPT:,} characters.")]
    for number, raw in enumerate(script.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        step = {"line": number}
        problem = None
        if line.startswith("-"):
            match = scenes.OPTION.fullmatch(line)
            if choice is None:
                problem = "An option (“- …”) has to come straight after a choice, or another option."
            elif not match:
                problem = "Write an option as “- what the player says -> label”."
            else:
                option = {"text": match["text"], "goto": (match["label"] or "").lower() or None}
                for act in filter(None, (part.strip() for part in (match["acts"] or "").split(","))):
                    found = OPTION_ACT.fullmatch(act)
                    if found:
                        option[found["verb"].lower()] = found["what"].lower()
                    else:
                        problem = "After an option, write “(set flag)” or “(unset flag)”; for more, go to a label."
                if option["goto"]:
                    jumps.append((number, option["goto"]))
                choice["options"].append(option)
            if problem:
                errors.append((number, problem))
            continue
        close_choice()
        choice = None
        if match := scenes.LABEL.fullmatch(line):
            label = match["label"].lower()
            if label in labels:
                problem = f"There's already a label called “{label}”."
            labels[label] = len(steps)
        elif line.lower() == "end":
            step["do"] = "end"
        elif match := scenes.GOTO.fullmatch(line):
            step.update({"do": "goto", "label": match["label"].lower()})
            jumps.append((number, step["label"]))
        elif match := RANK_IF.fullmatch(line):
            step.update({"do": "if_rank", "op": match["op"], "rank": int(match["rank"]), "label": match["label"].lower()})
            jumps.append((number, step["label"]))
        elif match := scenes.IF.fullmatch(line):
            step.update({"do": "if", "flag": match["flag"].lower(), "not": bool(match["not"]), "label": match["label"].lower()})
            jumps.append((number, step["label"]))
        elif match := scenes.SET.fullmatch(line):
            step.update({"do": match["verb"].lower(), "flag": match["flag"].lower()})
        elif match := POINTS.fullmatch(line):
            n = int(match["n"].replace(" ", ""))
            if not n or abs(n) > MAX_POINTS:
                problem = f"Points go from -{MAX_POINTS} to +{MAX_POINTS}, and not 0."
            step.update({"do": "points", "n": n})
        elif match := GIVE_MONEY.fullmatch(line):
            n = int(match["n"])
            if not 1 <= n <= MAX_MONEY:
                problem = f"Give from 1 to {MAX_MONEY:,} coins."
            step.update({"do": "money", "n": n})
        elif match := GIVE_GIFT.fullmatch(line):
            key = match["key"].lower()
            keys = sorted(gifts) if gifts is not None else list(GiftItem.objects.values_list("key", flat=True))
            if key not in keys:
                problem = f"There's no gift called “{key}”." + (f" Gifts are {', '.join(keys)}." if keys else "")
            step.update({"do": "gift", "key": key})
        elif line.lower().startswith("give"):
            problem = "In chatter, write “give money 100” or “give gift <key>”: buffs are for challenge scenes."
        elif match := FIGHT.fullmatch(line):
            stake = int(match["stake"] or 0)
            if stake > MAX_STAKE:
                problem = f"A stake can be at most {MAX_STAKE:,} coins."
            step.update({"do": "fight", "stake": stake})
        elif line.lower().startswith("fight"):
            problem = "In chatter, “fight” offers a duel with the CPU you're talking to: write “fight”, or “fight stake 500”."
        elif match := scenes.CHOICE.fullmatch(line):
            step.update({"do": "choice", "prompt": (match["prompt"] or "").strip(), "options": []})
            choice = step
        elif match := scenes.SAY.fullmatch(line):
            who, mood = match["who"].lower(), (match["expression"] or "").lower()
            if who not in (THEM, scenes.PLAYER, scenes.NARRATOR):
                problem = f"In chatter, the speakers are {THEM} (the CPU you're talking to), player and narrator."
            elif mood and who == scenes.NARRATOR:
                problem = "The narrator has no face to show a mood with."
            elif mood and who == THEM and mood not in CPU_MOODS:
                problem = f"Their moods are {', '.join(CPU_MOODS)}."
            step.update({"do": "say", "who": who, "text": match["text"]})
            # The player has no face here, so a mood on their line is let through and dropped: scripts written while
            # they had a portrait still compile.
            if mood and who == THEM:
                step["mood"] = mood
        elif STAGED.match(line) or ((found := scenes.DIRECTION.fullmatch(line))
                                    and scenes.verb_of(found["verb"], scenes.DIRECTION_VERBS)):
            problem = "Chatter plays in the town's talk box, which has no stage: no cast, entrances, moves, backgrounds, " \
                      "screen effects, waits or offers. Show feelings with a mood: “them (pleased): …”."
        else:
            problem = "I don't understand this line. The reference lists what chatter can say."
        if problem:
            errors.append((number, problem))
        elif "do" in step:
            steps.append(step)
    close_choice()
    for number, label in jumps:
        if label not in labels:
            errors.append((number, f"There's no label called “{label}”."))
    if not steps and not errors:
        errors.append((1, "Nothing's said yet."))
    return {"labels": labels, "steps": steps}, sorted(errors)


# ---------------------------------------------------------------- Built-in lines: no CPU is ever silent

DEFAULTS = [  # (context, min rank, script)
    ("greet", 0, "them: Oh, hi. {player}, right?\nplayer: That's me.\nthem: You play Weiss? We should duel sometime."),
    ("greet", 0, "them: Hey. Here for a game, or just looking around?"),
    ("greet", 0, "them: Hm? Oh. Hello."),
    ("greet", 2, "them (pleased): {player}! Good timing, I was getting bored."),
    ("greet", 2, "them (pleased): Hey, you. Built anything new lately?\nchoice\n- Always.\n- I'm still tinkering.\nthem: Show me in a duel, then."),
    ("greet", 4, "them (pleased): There you are. I was hoping I'd run into you today."),
    ("again", 0, "them: Back again? I'm still here."),
    ("again", 0, "them: Something else?"),
    ("again", 2, "them (pleased): Can't stay away, huh?"),
    ("gift_loved", 0, "them (pleased): Wait, for me? This is exactly the kind of thing I love. Thank you!"),
    ("gift_liked", 0, "them (pleased): Oh, nice. Thanks, {player}."),
    ("gift_neutral", 0, "them: Huh. Thanks, I guess."),
    ("gift_disliked", 0, "them (dismayed): …Oh. Um. Thanks. I'll… find a use for it."),
    ("before_duel", 0, "them: Let's see what you've got."),
    ("before_duel", 3, "them (pleased): Don't hold back on my account."),
    ("after_win", 0, "them (dismayed): You got me that time. Next time won't be so easy."),
    ("after_loss", 0, "them (pleased): Good game. Come back when you've tuned that deck."),
    ("rank_up", 1, "them: You know, you're not bad to have around."),
    ("rank_up", 2, "them (pleased): I think I'd call us friends now, {player}."),
    ("rank_up", 3, "them (pleased): It's always better when you're here. Don't tell anyone I said that."),
    ("rank_up", 4, "them (pleased): I trust you, {player}. That's not something I say lightly."),
    ("rank_up", 5, "them (pleased): Whatever happens out there, I'm on your side. Best friends, okay?"),
    ("estranged", 0, "them (dismayed): …Oh. It's you."),
    ("estranged", 0, "them: I haven't forgotten what you did. If you want a duel, fine. Don't expect more."),
    ("estranged", 0, "them (dismayed): Say what you came to say, {player}."),
    # Walking up to someone, and leaving them: by how well they know the player.
    ("hello", 0, "them: Hm? Oh, hello."),
    ("hello", 0, "them: Can I help you?"),
    ("hello", 2, "them (pleased): Hey, {player}."),
    ("hello", 2, "them (pleased): Oh, it's you! Hi."),
    ("hello", 4, "them (pleased): {player}! I was hoping you'd stop by."),
    ("goodbye", 0, "them: See you around."),
    ("goodbye", 0, "them: Bye, then."),
    ("goodbye", 2, "them (pleased): Catch you later, {player}."),
    ("goodbye", 4, "them (pleased): Don't be a stranger, okay? See you soon."),
]
COLD = {"hello": "them (dismayed): …What do you want?", "goodbye": "them: Fine. Go."}  # someone a quest choice estranged


def candidates(cpu, context, rank):
    """[(key, weight, compiled, scene)] that could play: the CPU's own lines for this context and rank, or else those for
    any CPU, or else the built-in ones; only those of the highest min rank the player has reached (rank_up: exactly
    the rank reached). Lines with mistakes are left out, so a typo never stops the town."""
    fits = (lambda min_rank: min_rank == rank) if context == "rank_up" else (lambda min_rank: min_rank <= rank)
    for rows in (Chatter.objects.filter(cpu=cpu, context=context), Chatter.objects.filter(cpu=None, context=context)):
        found = []
        for row in rows:
            if not fits(row.min_rank):
                continue
            compiled, errors = compile_chatter(row.script) if row.script.strip() else ({"labels": {}, "steps": []}, [])
            if (not errors and compiled["steps"]) or row.scene_id:
                found.append((row.min_rank, (f"db:{row.pk}", row.weight, compiled, row.scene)))
        if found:
            return top(found)
    found = [(min_rank, (f"default:{i}", 1, compile_chatter(script)[0], None))
             for i, (where, min_rank, script) in enumerate(DEFAULTS) if where == context and fits(min_rank)]
    return top(found)


def top(found):
    best = max((min_rank for min_rank, _ in found), default=None)
    return [entry for min_rank, entry in found if min_rank == best]


def pick(cpu, context, rank, rng=random):
    """(key, compiled, scene) for one line that fits, picked by weight; None if there's none (only rank_up can have none)."""
    found = candidates(cpu, context, rank)
    if not found:
        return None
    key, _, compiled, scene = rng.choices(found, weights=[max(weight, 1) for _, weight, _, _ in found])[0]
    return key, compiled, scene


def load(key):
    """The compiled script a talk is playing (by pick's key), to carry on from a choice; None if it's gone."""
    kind, _, ref = key.partition(":")
    if kind == "db":
        row = Chatter.objects.filter(pk=int(ref)).first() if ref.isdigit() else None
        compiled, errors = compile_chatter(row.script) if row else (None, True)
        return None if errors else compiled
    if kind == "default" and ref.isdigit() and int(ref) < len(DEFAULTS):
        return compile_chatter(DEFAULTS[int(ref)][2])[0]
    return None


def first_line(cpu, context, rank, fill, rng=random):
    """The first thing said in a line for this context, as text (`fill` fills in {player} and the like), or ""."""
    found = pick(cpu, context, rank, rng)
    if not found:
        return ""
    return next((fill(step["text"]) for step in found[1]["steps"] if step["do"] == "say"), "")


def play(compiled, start, world):
    """Run the script from step `start` until it needs the player: (events, waiting). Events are what the box shows, in
    order: {"say", "who", "mood"}, and what `world` reports for points, coins and gifts. waiting is {"choice": step
    index, "prompt", "options"}, {"fight": stake} or None (it ended). `world` does what the script asks: rank(),
    flag(name), set_flag(name, on), points(n, at), money(n, at), gift(key, at) and fill(text); `at` is the step, for
    once-a-day."""
    steps, labels = compiled["steps"], compiled["labels"]
    events, at, ran = [], start, 0
    while 0 <= at < len(steps):
        ran += 1
        if ran > RUNAWAY:
            break
        step = steps[at]
        do = step["do"]
        at += 1
        if do == "end":
            break
        elif do == "goto":
            at = labels[step["label"]]
        elif do == "if":
            if bool(world.flag(step["flag"])) != step["not"]:
                at = labels[step["label"]]
        elif do == "if_rank":
            if OPS[step["op"]](world.rank(), step["rank"]):
                at = labels[step["label"]]
        elif do in ("set", "unset"):
            world.set_flag(step["flag"], do == "set")
        elif do == "say":
            events.append({"say": world.fill(step["text"]), "who": step["who"], "mood": step.get("mood", "")})
        elif do == "points":
            events.extend(world.points(step["n"], at - 1))
        elif do == "money":
            events.extend(world.money(step["n"], at - 1))
        elif do == "gift":
            events.extend(world.gift(step["key"], at - 1))
        elif do == "fight":
            return events, {"fight": step["stake"]}
        elif do == "choice":
            return events, {"choice": at - 1, "prompt": world.fill(step["prompt"]), "options": [world.fill(o["text"]) for o in step["options"]]}
    return events, None


def after_choice(compiled, at, option, world):
    """Where a choice (step `at`) goes when the player picks `option`, having done its set/unset: the next step.
    Raises ValueError for a choice or option that isn't there."""
    steps = compiled["steps"]
    if not (0 <= at < len(steps)) or steps[at]["do"] != "choice" or not (0 <= option < len(steps[at]["options"])):
        raise ValueError("That choice has gone; talk to them again.")
    picked = steps[at]["options"][option]
    for verb in ("set", "unset"):
        if picked.get(verb):
            world.set_flag(picked[verb], verb == "set")
    return compiled["labels"][picked["goto"]] if picked["goto"] else at + 1
