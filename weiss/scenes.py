"""Visual novel scenes: pre-written dialogue between CPUs, with staging, animations and branching choices.

Staff write a scene as a short script, one thing per line (REFERENCE below lists them all; the editing page shows
it). `compile_scene` turns a script into steps for the player (static/weiss/scene.js) and reports mistakes by line
number, so a scene with mistakes can still be saved and worked on, but not played.

    cast rapi as Rapi
    label start
    rapi enters left with slide
    rapi: Commander, {player}! Over here!
    rapi bounces
    choice What do you say?
    - On my way. -> go
    - Not now. -> later

The player only needs the steps and the cast, so anything that shows a scene (the staff test page now, something
for players later) builds it with `scene_payload` and hands it to ScenePlayer.
"""
import random
import re
import secrets

from . import buffs
from .models import CpuProfile, PlayerProfile, Scene

MAX_SCRIPT = 50_000
NARRATOR = "narrator"
PLAYER = "player"  # whoever's playing: always in the cast, with their name and avatar
POSITIONS = ("far-left", "left", "center", "right", "far-right")
ENTRANCES = ("fade", "slide", "rise", "drop", "zoom", "pop")  # exits are the same, played backwards
ACTIONS = ("shake", "tremble", "bounce", "jump", "nod", "spin", "flip", "pulse", "flash", "sway", "glow", "wobble")
SCREEN_EFFECTS = ("shake", "flash", "black", "clear")
BACKGROUNDS = ("default", "dusk", "night", "dawn", "crimson", "ocean", "forest", "void",  # drawn in static/weiss/backdrops.js
               "city", "rooftop", "rain", "sakura", "shrine", "snow", "beach", "space", "ruins", "castle",
               "classroom", "cafe", "library", "arena", "cave", "desert", "lab")
EXPRESSIONS = tuple(CpuProfile.SCREENS)  # a CPU's pictures: main, intro, win (the player won) and lose (the player lost)

# What a script can say, for the editing page: (what to write, what it does, what to insert when clicked).
REFERENCE = [
    ("cast rapi as Rapi", "Brings in a CPU profile under a short name (or “as #12” by its number). Before anything else.", "cast name as "),
    ("label fight", "A place to go to. A scene starts at the top.", "label "),
    ("rapi enters left with slide", f"Puts them on stage. Places: {', '.join(POSITIONS)}; ways in: {', '.join(ENTRANCES)}. Both optional.", " enters center with fade"),
    ("rapi: Hello, {player}!", "They speak. {player} is the player's name. A click goes on to the next line.", ": "),
    ("rapi (win): Ugh…", f"Speaks with another picture: {', '.join(EXPRESSIONS)}.", " (win): "),
    ("narrator: Night falls.", "Words from nobody in particular.", "narrator: "),
    ("player: I'm ready.", "Whoever's playing speaks: their name, and their avatar beside the words. No cast line needed; "
     "they can take the stage too (“player enters left”), as their avatar.", "player: "),
    ("rapi shows lose", "Changes their picture without speaking.", " shows "),
    ("rapi moves right", "Walks them to another place.", " moves "),
    ("rapi turns around", "Mirrors their picture, to face the other way; again to turn back.", " turns around"),
    ("rapi dims / rapi brightens", "Puts them in shadow, or back in the light.", " dims"),
    ("rapi bounces", f"An animation: {', '.join(ACTIONS)}.", " bounces"),
    ("rapi exits right with fade", "Takes them off stage, optionally to one side and by any of the ways in.", " exits with fade"),
    ("choice What do you say?", "Asks the player. The options follow, one a line; each can go to a label, or carry on below.", "choice "),
    ("- Fight her -> fight", "An option, under a choice. “-> label” is optional; after it, “(set brave)” sets a flag and “(give lucky_pack)” a buff (both: “(set brave, give lucky_pack)”).", "- "),
    ("give lucky_pack", "In a challenge, gives the player a buff (or “give random”; “give pact” for a random pact, a buff with a price). "
     "It's theirs at the end of the scene, to use before the next fight.", "give "),
    ("fight anis", "Makes Anis the next fight in the run (the CPU must be in its arcade list, often as a branch). In a scene "
     "before a fight that hasn't started, it's the fight about to start. On an option: “(fight anis)”.", "fight "),
    ("offer 3: Take a gift", "In a challenge, the player picks one of 3 random buffs (“offer 2 pacts: …” for pacts; or of the ones named: "
     "“offer lucky_pack, climax_pack”).", "offer 3: "),
    ("set brave / unset brave", "Remembers (or forgets) something for later.", "set "),
    ("if brave goto boast", "Goes to a label if a flag is set (“if not brave …” for the opposite).", "if  goto "),
    ("goto fight", "Goes to a label.", "goto "),
    ("background night", f"Changes the backdrop: {', '.join(BACKGROUNDS)}.", "background "),
    ("screen shake", f"A whole-screen effect: {', '.join(SCREEN_EFFECTS)} (black fades out, clear fades back in).", "screen "),
    ("wait 1.5", "Pauses for that many seconds.", "wait 1"),
    ("end", "Ends the scene. The end of the script does too.", "end"),
    ("# a note", "Notes for you; the player never sees them.", "# "),
]

NAME = r"[A-Za-z_][\w-]*"
CAST = re.compile(rf"cast\s+(?P<id>{NAME})\s+as\s+(?P<who>.+)", re.I)
LABEL = re.compile(rf"label\s+(?P<label>{NAME})", re.I)
GOTO = re.compile(rf"goto\s+(?P<label>{NAME})", re.I)
IF = re.compile(rf"if\s+(?P<not>not\s+)?(?P<flag>{NAME})\s+goto\s+(?P<label>{NAME})", re.I)
SET = re.compile(rf"(?P<verb>set|unset)\s+(?P<flag>{NAME})", re.I)
WAIT = re.compile(r"wait\s+(?P<seconds>\d+(?:\.\d+)?)\s*s?", re.I)
BACKGROUND = re.compile(r"background\s+(?P<name>\S+)", re.I)
SCREEN = re.compile(r"screen\s+(?P<effect>\S+)", re.I)
CHOICE = re.compile(r"choice(?:\s*:?\s*(?P<prompt>.*))?", re.I)
OPTION = re.compile(rf"-\s*(?P<text>.+?)\s*(?:->\s*(?P<label>{NAME}))?\s*(?:\((?P<acts>[^()]*)\))?", re.I)
OPTION_ACT = re.compile(rf"(?P<verb>set|unset|give|fight)\s+(?P<what>{NAME})", re.I)
GIVE = re.compile(rf"give\s+(?P<buff>{NAME})", re.I)
FIGHT = re.compile(rf"fight\s+(?P<who>{NAME})", re.I)
OFFER = re.compile(r"offer\s+(?P<what>[^:]+?)\s*(?::\s*(?P<prompt>.*))?", re.I)
SAY = re.compile(rf"(?P<who>{NAME})\s*(?:\(\s*(?P<expression>\w+)\s*\))?\s*:\s*(?P<text>.*\S)")
DIRECTION = re.compile(rf"(?P<who>{NAME})\s+(?P<verb>[a-z]+)(?:\s+(?P<rest>.*))?", re.I)
ENTER = re.compile(rf"(?:(?:at|to)\s+)?(?P<at>[\w-]+)?\s*(?:with\s+(?P<how>\w+))?", re.I)


def verb_of(word, known):
    """'bounces' -> 'bounce', 'flashes' -> 'flash': a script reads better in the present tense."""
    word = word.lower()
    for cut in (0, 1, 2):
        stem = word[:len(word) - cut] if cut else word
        if stem in known:
            return stem
    return None


def find_cpu(who):
    """(the CPU profile a cast line names, or None and why not): by name, or by number as #12."""
    who = who.strip().strip('"“”').strip()
    if re.fullmatch(r"#\d+", who):
        profile = CpuProfile.objects.filter(pk=int(who[1:])).first()
        return (profile, None) if profile else (None, f"There's no CPU profile {who}.")
    found = list(CpuProfile.objects.filter(name__iexact=who)[:2])
    if len(found) == 1:
        return found[0], None
    if not found:
        return None, f"There's no CPU profile called “{who}”."
    return None, f"More than one CPU profile is called “{who}”: write #{found[0].pk} or #{found[1].pk} instead."


DIRECTION_VERBS = {"enter", "exit", "move", "show", "turn", "dim", "brighten", *ACTIONS}


def compile_scene(script, find=find_cpu):
    """(scene, errors): the scene as {"cast": {id: CpuProfile}, "labels": {label: step}, "steps": [...]}, and
    [(line number, what's wrong)]. Each step is a dict with "do" and the line it came from."""
    cast, labels, steps, errors = {}, {}, [], []
    jumps = []  # (line, label) for every goto, to check once all the labels are known
    choice = None  # the choice the following "- ..." lines are options of

    def close_choice():
        if choice is not None and not choice["options"]:
            errors.append((choice["line"], "A choice needs at least one option under it, written “- …”."))

    if len(script) > MAX_SCRIPT:
        return {"cast": {}, "labels": {}, "steps": []}, [(1, f"A script can be at most {MAX_SCRIPT:,} characters.")]
    for number, raw in enumerate(script.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        step = {"line": number}
        problem = None
        if line.startswith("-"):
            match = OPTION.fullmatch(line)
            if choice is None:
                problem = "An option (“- …”) has to come straight after a choice, or another option."
            elif not match:
                problem = "Write an option as “- what the player says -> label”."
            else:
                option = {"text": match["text"], "goto": match["label"]}
                for act in filter(None, (part.strip() for part in (match["acts"] or "").split(","))):
                    found = OPTION_ACT.fullmatch(act)
                    if not found:
                        problem = "After an option, write “(set flag)”, “(unset flag)”, “(give buff)” or “(fight cpu)”, with commas between."
                    elif found["verb"].lower() == "give" and found["what"].lower() not in (*buffs.BUFFS, buffs.RANDOM, buffs.PACT):
                        problem = buff_problem(found["what"])
                    elif found["verb"].lower() == "fight" and found["what"].lower() not in cast:
                        problem = fight_problem(found["what"])
                    else:
                        option[found["verb"].lower()] = found["what"].lower()
                if option["goto"]:
                    jumps.append((number, option["goto"]))
                choice["options"].append(option)
            if problem:
                errors.append((number, problem))
            continue
        close_choice()
        choice = None
        if match := CAST.fullmatch(line):
            name = match["id"].lower()
            if steps:
                problem = "Cast everyone at the top, before anything happens."
            elif name in (NARRATOR, PLAYER) or name in cast:
                problem = f"“{name}” is already taken."
            else:
                profile, problem = find(match["who"])
                if profile:
                    cast[name] = profile
        elif match := LABEL.fullmatch(line):
            label = match["label"].lower()
            if label in labels:
                problem = f"There's already a label called “{label}”."
            labels[label] = len(steps)
        elif line.lower() == "end":
            step["do"] = "end"
        elif match := GOTO.fullmatch(line):
            step.update({"do": "goto", "label": match["label"].lower()})
            jumps.append((number, step["label"]))
        elif match := IF.fullmatch(line):
            step.update({"do": "if", "flag": match["flag"].lower(), "not": bool(match["not"]), "label": match["label"].lower()})
            jumps.append((number, step["label"]))
        elif match := SET.fullmatch(line):
            step.update({"do": match["verb"].lower(), "flag": match["flag"].lower()})
        elif match := FIGHT.fullmatch(line):
            if match["who"].lower() not in cast:
                problem = fight_problem(match["who"])
            step.update({"do": "fight", "who": match["who"].lower()})
        elif match := GIVE.fullmatch(line):
            if match["buff"].lower() not in (*buffs.BUFFS, buffs.RANDOM, buffs.PACT):
                problem = buff_problem(match["buff"])
            step.update({"do": "give", "buff": match["buff"].lower()})
        elif match := OFFER.fullmatch(line):
            what = match["what"].strip().lower()
            step.update({"do": "offer", "prompt": (match["prompt"] or "").strip()})
            if count := re.fullmatch(r"(\d+)(?:\s+(?:buffs?|rewards?|(?P<pacts>pacts?)))?", what):
                step["count"] = max(int(count[1]), 1)
                if count["pacts"]:
                    step["pacts"] = True
            else:
                step["choices"] = [name.strip() for name in what.split(",")]
                problem = next((buff_problem(name) for name in step["choices"] if name not in buffs.BUFFS), None)
        elif match := WAIT.fullmatch(line):
            step.update({"do": "wait", "seconds": min(float(match["seconds"]), 30)})
        elif match := BACKGROUND.fullmatch(line):
            if match["name"].lower() not in BACKGROUNDS:
                problem = f"Backgrounds are {', '.join(BACKGROUNDS)}."
            step.update({"do": "background", "name": match["name"].lower()})
        elif match := SCREEN.fullmatch(line):
            if match["effect"].lower() not in SCREEN_EFFECTS:
                problem = f"Screen effects are {', '.join(SCREEN_EFFECTS)}."
            step.update({"do": "screen", "effect": match["effect"].lower()})
        elif match := CHOICE.fullmatch(line):
            step.update({"do": "choice", "prompt": (match["prompt"] or "").strip(), "options": []})
            choice = step
        elif match := SAY.fullmatch(line):
            who = match["who"].lower()
            if who not in (NARRATOR, PLAYER) and who not in cast:
                problem = f"Nobody's cast as “{who}”: add “cast {who} as …” at the top."
            elif match["expression"] and who == PLAYER:
                problem = "The player has just the one picture: their avatar."
            elif match["expression"] and match["expression"].lower() not in EXPRESSIONS:
                problem = f"Pictures are {', '.join(EXPRESSIONS)}."
            step.update({"do": "say", "who": None if who == NARRATOR else who, "text": match["text"]})
            if match["expression"]:
                step["expression"] = match["expression"].lower()
        elif (match := DIRECTION.fullmatch(line)) and match["who"].lower() in (*cast, PLAYER):
            step["who"] = match["who"].lower()
            problem = direction(step, match["verb"], (match["rest"] or "").strip())
        elif match and match["who"].lower() not in (*cast, PLAYER) and verb_of(match["verb"], DIRECTION_VERBS):
            problem = f"Nobody's cast as “{match['who'].lower()}”: add “cast {match['who'].lower()} as …” at the top."
        else:
            problem = "I don't understand this line. The reference lists what a line can say."
        if problem:
            errors.append((number, problem))
        elif "do" in step:
            steps.append(step)
    close_choice()
    for number, label in jumps:
        if label not in labels:
            errors.append((number, f"There's no label called “{label}”."))
    if not steps and not errors:
        errors.append((1, "Nothing happens in this scene yet."))
    return {"cast": cast, "labels": labels, "steps": steps}, sorted(errors)


def fight_problem(name):
    return f"Only a CPU in the cast can be fought: add “cast {name.lower()} as …” at the top."


def buff_problem(name):
    return f"There's no buff called “{name}”. Buffs are {', '.join(buffs.BUFFS)}, or random, or pact (a random pact)."


def direction(step, verb, rest):
    """Fill in a step for "<who> <verb> <rest>". Returns what's wrong with it, or None."""
    written, verb = verb, verb_of(verb, DIRECTION_VERBS)
    if verb in ("enter", "exit"):
        match = ENTER.fullmatch(rest)
        at, how = (match["at"], match["how"]) if match else (None, None)
        if not match:
            return f"Write it as “{step['who']} {verb}s left with fade”: the place and the way are both optional."
        if at and at.lower() not in (POSITIONS if verb == "enter" else ("left", "right")):
            return f"Places are {', '.join(POSITIONS)}." if verb == "enter" else "They can exit left or right (or just exit)."
        if how and how.lower() not in ENTRANCES:
            return f"Ways in and out are {', '.join(ENTRANCES)}."
        step.update({"do": verb, "at": (at or ("center" if verb == "enter" else "")).lower(), "how": (how or "fade").lower()})
    elif verb == "move":
        at = re.sub(r"^to\s+", "", rest, flags=re.I).lower()
        if at not in POSITIONS:
            return f"Places are {', '.join(POSITIONS)}."
        step.update({"do": "move", "at": at})
    elif verb == "show":
        if step["who"] == PLAYER:
            return "The player has just the one picture: their avatar."
        if rest.lower() not in EXPRESSIONS:
            return f"Pictures are {', '.join(EXPRESSIONS)}."
        step.update({"do": "show", "expression": rest.lower()})
    elif verb == "turn":
        if rest.lower() not in ("", "around"):
            return f"Write it as “{step['who']} turns around”."
        step.update({"do": "turn"})
    elif verb in ("dim", "brighten"):
        if rest:
            return f"“{verb}” takes nothing after it."
        step.update({"do": verb})
    elif verb in ACTIONS:
        if rest:
            return f"“{verb}” takes nothing after it."
        step.update({"do": "animate", "animation": verb})
    else:
        return f"I don't know how to make {step['who']} “{written}”. The reference lists what they can do."
    return None


def cast_name(profile):
    """A short name to cast a CPU as: the first word of its name, or cpu12 if that won't do."""
    word = re.sub(r"[^a-z0-9_]", "", (profile.name.split() or [""])[0].lower())[:16]
    return word if re.fullmatch(NAME, word) and word not in (NARRATOR, PLAYER) else f"cpu{profile.pk}"


def scene_list():
    """Every scene, with how many mistakes its script has, for the CPU creation tab."""
    found = list(Scene.objects.all())
    for scene in found:
        scene.errors = len(compile_scene(scene.script)[1])
    return found


def player_cast(viewer):
    """The player, for the cast: the name and avatar of whoever's watching (`viewer`, a user), or "You"."""
    profile = PlayerProfile.objects.filter(user=viewer).first() if viewer and viewer.pk else None
    return {"name": viewer.username if viewer else "You", "player": True, "images": {}, "avatar": profile.avatar if profile else None}


def scene_payload(scene, title="", key="", viewer=None):
    """What ScenePlayer needs, as JSON: the steps and labels, and for each of the cast their name, pictures and
    avatar, the player (`viewer`) among them. `key` tells one showing apart from another, for a page playing
    scenes one after another."""
    cast = {PLAYER: player_cast(viewer)}
    for name, profile in scene["cast"].items():
        images = {expression: profile.screen_url(expression) for expression in EXPRESSIONS}
        cast[name] = {"name": profile.name, "cpu": profile.pk, "images": {k: v for k, v in images.items() if v}, "avatar": profile.avatar}
    return {"key": key, "title": title, "cast": cast, "labels": scene["labels"], "steps": scene["steps"]}


def chosen_fight(payload, picks):
    """The CPU profile id a played scene picked to fight next, from what the page reports: [[step, option or None]],
    the last that's a fight, checked against the scene (as buffs.given does); or None."""
    chosen = None
    for pick in picks if isinstance(picks, list) else []:
        try:
            at, option = pick
            step = payload["steps"][int(at)]
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        who = None
        if step["do"] == "fight" and option is None:
            who = step.get("who")
        elif step["do"] == "choice" and isinstance(option, int) and 0 <= option < len(step["options"]):
            who = step["options"][option].get("fight")
        cpu = payload["cast"].get(who, {}).get("cpu") if who else None
        if cpu:
            chosen = cpu
    return chosen


def playable(found, with_buffs=False, rng=random, viewer=None):
    """Payloads for these Scene objects (None skipped), leaving out any whose script has mistakes: a run goes
    on without a scene rather than stopping for one being written. with_buffs: a challenge's, whose buffs
    count (see buffs.resolve). viewer: the player, who can be in the scene."""
    payloads = []
    for scene in found:
        if scene:
            compiled, errors = compile_scene(scene.script)
            if not errors:
                payload = scene_payload(compiled, scene.name, f"{scene.pk}-{secrets.token_hex(4)}", viewer)
                payloads.append(buffs.resolve(payload, with_buffs, rng))
    return payloads


def starter_script(profiles):
    """A new scene's script: a short example to change, using a real CPU's name if there is one."""
    who = profiles[0].name if profiles else "Name of a CPU"
    return f"""# Lines starting with # are notes for you. The reference beside the editor lists everything a line can say.
cast them as {who}

label start
background dusk
them enters center with rise
them: Hello, {{player}}.
them bounces
choice What do you say?
- Hello! -> friendly (set polite)
- ... -> quiet

label friendly
them (lose): Nice to meet you!
end

label quiet
them nods
them: Not much of a talker, huh?
end
"""
