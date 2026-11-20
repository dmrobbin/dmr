"""World mode's tutorial: the first time a player reaches the town, a guide walks them through it, one step at a time
(docs/world-tutorial-plan.md). Each step's lines (TutorialLine, the guide's dialogue) play in the talk box; then the
thing to press is highlighted until the player's done what the step asks, and nothing else can be done. It ends with
the first duel with the guide (on easy), and sets "tutorial_done" (the story's first quest waits on it).

The state is on the save: flags["tutorial"] = {"step", "said"} (a new save only; saves from before have none).
`allows` is asked by every town move, and refuses what the step doesn't allow; `did` is told when the player's done
something, and moves the tutorial on if it's what the step was waiting for.
"""
from . import chatter, world
from .models import CpuProfile, GiftItem, TutorialLine

STEPS = ("arrive", "approach", "talk", "gift", "map", "shop", "quests", "time", "deck", "minigame", "duel")
RESULT_LINES = ("minigame_win", "minigame_lose")  # the guide's answer to the game's result (by the player's), not steps
GUIDES = ("Aang", "Chisato Nishikigi", "Asuna Yuuki", "Erza Scarlet")  # until the story pack sets them
DONE_FLAG = "tutorial_done"

# For each step: its goal (title), the hint, what to highlight (data-tutorial names, in order) and what it waits for.
INFO = {
    "arrive": ("Ask someone where you are", "Click one of the people here to ask them.", ["person"], "approach"),
    "approach": ("Listen", "", [], None),
    "talk": ("Talk to {guide}", "Press Talk.", ["talk"], "talk"),
    "gift": ("Give {guide} a gift", "Press Give a gift, then choose the gift.", ["gift", "gift-item"], "gift"),
    "map": ("Go to the card shop", "Open the map and choose the card shop.", ["map", "place-shop"], "travel_shop"),
    "shop": ("Buy a pack", "Open the shop counter, add a pack to your basket, then check out.", ["shop", "add-pack", "checkout"], "buy_pack"),
    "quests": ("Look at your quests", "Press Quests to open your quest log.", ["quests"], "quests"),
    "time": ("Pass time", "Press Pass time, then choose where to go.", ["wait"], "time"),
    "deck": ("Make your deck legal", "Press Decks and build a legal deck: 50 cards, 8 climaxes, at most 4 of a card.", ["decks"], "deck"),
    "minigame": ("Play a game with {guide}", "Press Play a game, then choose one. {guide} will go easy on you.", ["minigame"], "minigame"),
    "duel": ("Duel {guide}", "Press Duel. {guide} will go easy on you.", ["duel"], "duel"),
}

# What the guide says until the story pack's TUTORIAL is imported: plain, so the tutorial always works.
DEFAULT_LINES = {
    "arrive": ["narrator: You've arrived somewhere you don't recognise. A few people are around.", "narrator: You decide to ask someone where you are."],
    "approach": ["player: Excuse me… where am I?", "them: You're new! It's like this for everyone when they first get here.",
                 "player: But where is here?", "them (pleased): Somewhere worth learning your way around. Come on, I'll show you."],
    "talk": ["them: People here like being talked to. Talk to someone every day and you'll get closer.", "them: Go on: press Talk."],
    "gift": ["them (pleased): Here, take this. Now give it back to me: it's how gifts work.",
             "them: Everyone loves, likes or dislikes different things. One gift a day each."],
    "map": ["them: The town has lots of places, and people are out at different ones at different times.",
            "them: Let's go to the card shop. Open the map."],
    "shop": ["them: This is where cards come from. Packs, specialty packs, single cards, and gifts.",
             "them: Add a pack to your basket, then check out."],
    "quests": ["them: When someone has something to ask you, there's a ! over them. Your quest log keeps track.", "them: Have a look: press Quests."],
    "time": ["them: There are four times of day. Talking or duelling with someone spends the time; then you pass it.",
             "them: Press Pass time."],
    "deck": ["them: Your decks are built only from cards you've opened. You can have several; the equipped one duels.",
             "them: Make yours legal: 50 cards, 8 climaxes. Press Decks."],
    "minigame": ["them: Want to play a game with me? Pick one and we'll have a little fun."],
    "minigame_win": ["them: Good game, {player}. Well played."],
    "minigame_lose": ["them: I won that one. Play again whenever you like."],
    "duel": ["them (pleased): Let's see what you've got. I'll go easy on you."],
}


# ---------------------------------------------------------------- State

def state(save):
    return (save.flags or {}).get("tutorial")


def active(save):
    return bool(state(save))


def step(save):
    found = state(save)
    return found["step"] if found else None


def start(save):
    """A new save begins in the tutorial."""
    save.flags["tutorial"] = {"step": STEPS[0], "said": False}


def guide(save):
    pk = save.flags.get("mentor")
    return CpuProfile.objects.filter(pk=pk).first() if pk else None


def guide_names():
    found = world.settings()
    return list(found.tutorial_guides) if found and found.tutorial_guides else list(GUIDES)


def candidates():
    """The CPUs a new player can ask to be their guide: those named (WorldSettings.tutorial_guides) who can be in town."""
    able = set(world.haunts())
    names = guide_names()
    found = {cpu.name.lower(): cpu for cpu in CpuProfile.objects.filter(pk__in=able)}
    return [found[name.lower()] for name in names if name.lower() in found]


def at(save, name):
    return STEPS.index(step(save)) >= STEPS.index(name) if active(save) else True


# ---------------------------------------------------------------- What it says

def lines(save, name):
    """The step's lines as the talk box plays them: [{"who", "say", "mood"}], the guide's own, or any guide's, or the
    built-in."""
    cpu = guide(save)
    row = (TutorialLine.objects.filter(step=name, cpu=cpu).first() if cpu else None) or \
        TutorialLine.objects.filter(step=name, cpu__isnull=True).first()
    script = row.script if row else "\n".join(DEFAULT_LINES[name])
    compiled, _ = chatter.compile_chatter(script)
    fill = world.filler(save, cpu) if cpu else (lambda text: text.replace("{player}", save.user.username))
    return [{"who": s["who"], "say": fill(s["text"]), **({"mood": s["mood"]} if s.get("mood") else {})}
            for s in compiled["steps"] if s["do"] == "say"]


def view(save):
    """The tutorial as the town shows it (docs/world-tutorial-plan.md), or None once it's over."""
    found = state(save)
    if not found:
        return None
    name = found["step"]
    cpu = guide(save)
    title, hint, highlight, _ = INFO[name]
    who = cpu.name if cpu else "Your guide"
    if name == "time" and world.choice_pending(save):  # the map's open: every place is an answer, staying too
        highlight = [f"place-{place.key}" for place in world.places(save)]
        hint = "Choose where to go next: anywhere's fine, staying too."
    return {"step": name, "title": title.format(guide=who), "hint": hint.format(guide=who), "highlight": highlight,
            "lines": [] if found.get("said") else [*(lines(save, found["reply"]) if found.get("reply") else []), *lines(save, name)],
            "guide": {"id": cpu.pk, "name": cpu.name} if cpu else None,
            "candidates": [c.pk for c in candidates()] if name == "arrive" else []}


STEP_PAGES = {"deck": ("save", "deck")}  # where a step's done, if not in the town


def banner(save, page=None):
    """For the pages outside the town (`page`: "reveal", "quests", "save" or "deck"): {"step", "guide", "title", "hint",
    "legal"}. On a page where the step isn't done (it's in the town), the hint sends the player back to their guide."""
    found = view(save)
    if not found:
        return None
    if page and page not in STEP_PAGES.get(found["step"], ()):
        who = (found["guide"] or {}).get("name", "Your guide")
        found = {**found, "hint": f"Head back to the town: {who} is waiting to show you what's next."}
    # legal: the equipped deck can duel (the deck step's pages highlight "Back to the town" once it is)
    return {key: found[key] for key in ("step", "title", "hint")} | {"guide": (found["guide"] or {}).get("name", ""),
                                                                      "legal": world.deck_problem(save) is None}


# ---------------------------------------------------------------- Moving on

def ready(save):
    """Whether the step's done already, without the player doing anything more (a deck that's legal)."""
    name = step(save)
    if name == "approach":
        return True
    if name == "deck":
        return world.deck_problem(save) is None
    return False


def advance(save):
    """On to the next step (its lines to play), or, after the duel, the end."""
    index = STEPS.index(step(save)) + 1
    if index >= len(STEPS):
        return finish(save)
    name = STEPS[index]
    save.flags["tutorial"] = {"step": name, "said": False}
    cpu = guide(save)
    if name == "gift" and cpu:  # the guide hands over something they love, to give back
        loved = set((cpu.gift_tastes or {}).get("loves", []))
        items = list(GiftItem.objects.filter(staff_only=False))
        item = next((item for item in items if loved & set(item.tags or [])), None) or (items[0] if items else None)
        if item:
            save.gifts[item.key] = save.gifts.get(item.key, 0) + 1
    if name == "shop" and save.money < world.pack_price():  # enough for a pack
        save.money = world.pack_price()


def finish(save):
    save.flags.pop("tutorial", None)
    save.flags["set"] = sorted(set(save.flags.get("set", [])) | {DONE_FLAG})


def said(save):
    """The step's lines have been played: if it's done already (or only had something to say), it moves on."""
    found = state(save)
    if not found:
        return
    found["said"] = True
    if ready(save):
        advance(save)


def did(save, action):
    """The player did something: if it's what the step was waiting for, the tutorial moves on."""
    if active(save) and INFO[step(save)][3] == action:
        advance(save)


def minigame_done(save, won):
    """The game in the minigame step is over, won by the player or not: the step's done, and the guide answers the
    result (its line plays before the next step's)."""
    if not active(save) or step(save) != "minigame":
        return
    advance(save)
    save.flags["tutorial"]["reply"] = "minigame_win" if won else "minigame_lose"


def refresh(save):
    """The town's being shown: a step that's done by itself (a deck made legal on its page) moves on. Returns whether
    anything changed."""
    found = state(save)
    if found and found.get("said") and ready(save):
        advance(save)
        return True
    return False


def approach(save, cpu_id):
    """In "arrive", the player asks a candidate where they are: that CPU becomes their guide."""
    if step(save) != "arrive":
        raise ValueError("You've a guide already.")
    cpu = next((c for c in candidates() if str(c.pk) == str(cpu_id)), None)
    if not cpu:
        raise ValueError("They can't help you right now: ask someone else.")
    save.flags["mentor"] = cpu.pk
    save.flags["set"] = sorted(set(save.flags.get("set", [])) | {"mentor_chosen"})
    save.__dict__.pop("_quests", None)
    world.roster.bring(save, [cpu.pk])
    advance(save)
    return cpu


def skip(save):
    """Staff testing: the tutorial ends now (the guide the first candidate, if none's chosen)."""
    if not save.user.is_staff or not world.test_mode(save):
        raise ValueError("Skipping the tutorial is for staff in test mode.")
    if not save.flags.get("mentor") and candidates():
        save.flags["mentor"] = candidates()[0].pk
        save.flags["set"] = sorted(set(save.flags.get("set", [])) | {"mentor_chosen"})
    finish(save)


# ---------------------------------------------------------------- What it allows

def allows(save, move, cpu=None, place=None):
    """Raises ValueError (saying what the guide's waiting for) if the tutorial doesn't allow this now. Moves: talk,
    give, duel (with `cpu`), travel (to `place`, a key), wait, shop, quest, board, tournament."""
    if not active(save):
        return
    name = step(save)
    cpu_obj = guide(save)
    waiting = f"{cpu_obj.name if cpu_obj else 'Your guide'} is waiting: {INFO[name][1].format(guide=cpu_obj.name if cpu_obj else 'your guide')}"
    if name == "arrive":
        waiting = "First, ask someone where you are: click one of the people here."
    is_guide = cpu is not None and cpu_obj is not None and getattr(cpu, "pk", cpu) == cpu_obj.pk
    if name == "minigame" and move != "minigame":  # until the game's played, nothing else is open
        raise ValueError(waiting)
    ok = {
        "minigame": is_guide and name == "minigame",
        "talk": is_guide and at(save, "talk"),
        "give": is_guide and at(save, "gift"),
        "duel": is_guide and name == "duel",
        "travel": place is not None and ((name == "map" and place == "shop") or at(save, "time")),
        "wait": name == "time",
        "shop": at(save, "shop"),
    }.get(move, False)
    if not ok:
        raise ValueError(waiting)


def cast(save):
    """{cpu id: place key} for who's in town while the tutorial's on: the candidates at the player's place in "arrive",
    then the guide, wherever the player is. None when it's over (everyone, as usual)."""
    if not active(save):
        return None
    here = world.place_of(save)
    key = here.key if here else "plaza"
    if step(save) == "arrive":
        return {cpu.pk: key for cpu in candidates()}
    cpu = guide(save)
    return {cpu.pk: key} if cpu else {}


def easy(save, cpu):
    """Whether this duel is the tutorial's (with the guide, on easy)."""
    return step(save) == "duel" and guide(save) is not None and guide(save).pk == cpu.pk

