"""Challenge mode: build a deck from packs, then fight through an arcade list with it.

A challenge starts with START_PACKS packs (NARRATIVE_START_PACKS for a narrative one). Opening them adds their cards to the challenge's pool, and its
deck can hold only what's in the pool (sealed: nothing else, so a deck can be short of 50 until more packs
come), but like any deck, it needs its 8 climaxes to fight (see deck_ready). Each win in its arcade run brings more (see win_reward); a loss ends the challenge. In a
free challenge the player picks any set for each pack, an arbitrary arcade list to fight; a narrative one
(NarrativeChallenge, set up by staff) fixes the list, and the sets its packs come from. An infinite one has no
list: a path of every CPU there is, floor after floor of two or three to choose from, laid ahead of the player as far
as PATH_AHEAD (see path_of), harder floor by floor (INFINITE_MODELS), for as long as the player wins, each win
bringing a random reward and no scenes. Some spaces on the path are events instead of fights: a random scene from
the ones staff have chosen (Scene.infinite_event), whose choices mostly give pacts (weiss.buffs), something for
something. Every boss_every floors the path narrows to a boss (see boss_floor): a CPU playing at its hardest, and
beating it brings BOSS_PACKS more packs, an augment to pick (weiss.augments) and a curse to take (weiss.curses), which
makes every CPU after it harder. In co-op the pair wear it down
together, every bit of damage either of their games deals it coming off one health bar (wear_boss).

A co-op challenge (weiss.coop) is an infinite one for two: each player has their own run here, with the pool and
path shared between them, so what changes those goes through coop.shared.

Stopping partway keeps the run where it is: the next fight starts with the CPU it stopped at. Resetting
starts again from nothing, deck and all. At the end, cleared or lost, the player keeps the deck (it joins
their lists) or discards it; until then it's kept out of their lists (CardList.challenge).
"""
import random

from django.db import transaction
from django.utils import timezone

from . import augments, coop, packs
from .lists import DECK_SIZE, climax_problem, is_climax, unlimited
from .models import ArcadeRun, Card, CardList, CardListEntry, ChallengeRun, ChallengeSettings, CpuProfile, GameRoom, Scene

START_PACKS = 20  # packs to open at the start of a free challenge
NARRATIVE_START_PACKS = 20  # ...and of a narrative one
WIN_PACKS = 3  # what a win in a free challenge brings
NARRATIVE_WIN_PACKS = 2  # ...and in a narrative one, with these rewards to claim besides (weiss.buffs)
NARRATIVE_WIN_REWARDS = ("color_pack",)
COOP = "coop"  # what starting a co-op challenge (weiss.coop) asks for: an infinite one, for two
STAFF_ONLY_KINDS = (ChallengeRun.Kind.FREE, ChallengeRun.Kind.NARRATIVE)  # still being tried out: only staff start these
INFINITE_NAME = "Infinite challenge"
INFINITE_WIN_PACKS = 2  # what a win in an infinite challenge brings, with one of these besides, at random: its prize,
INFINITE_PRIZES = ("climax_pack", "color_pack", "lucky_pack")  # which the Victory screen's slot machine lands on (play.js)
# How an infinite challenge's CPUs play, whatever their own model: (fights, the model or the models to pick from),
# in turn, then hard, from an aggression picked at random, for the rest.
INFINITE_MODELS = ((2, ("easy",)), (1, ("standard",)), (3, ("focused", "strategic")))
INFINITE_TIERS = ("Easy", "Standard", "Tough")  # what the path calls each of those, and "Hard" after
PATH_WIDTHS = (2, 3)  # how many CPUs a floor of the path offers, at random (fewer if there aren't that many)
PATH_AHEAD = 3  # floors of the path laid out past the one being fought
COLUMNS = 3  # the path's width: left, middle and right; each space leads only to those beside it (see links)
EVENT = "event"  # a space on the path that plays an event scene instead of a fight
FLASH_CHANCE = .15  # that a fight on the path (not a boss's) is a flash battle (see is_flash); until staff set it
EVENT_CHANCE = .6  # that a floor (after the first) has an event among its spaces, if there are event scenes; until staff set it (see event_chance)
INFINITE_START_PACKS = 20  # what an infinite challenge starts with, until staff set it (see infinite_start_packs)
LOADOUT_BUFFS = ("climax_pack", "level_pack", "color_pack", "lucky_pack", "wild_pack", "climax_pick")  # what staff can start it with besides
BOSS_EVERY = 5  # floors apart the path's bosses are, until staff set it (see boss_every)
BOSS_STOCK = 3  # cards in the stock a boss starts each game with
BOSS_PACKS = 3  # what beating a boss brings, besides a win's usual reward


def can_start(user, kind):
    """Whether this player can start (or join) a challenge of this kind: the infinite challenge, solo or co-op, is everyone's."""
    return user.is_staff or kind not in STAFF_ONLY_KINDS


def current(user):
    """This player's challenge, from starting it until they've kept or discarded its deck; or None."""
    run = ChallengeRun.objects.filter(user=user, finished__isnull=True).select_related("deck", "arcade_run", "scenario", "narrative", "coop").first()
    return coop.load(run)  # a co-op challenge's pool and path are the pair's


def start_packs(kind):
    """How many packs a challenge of this kind starts with."""
    if kind == ChallengeRun.Kind.INFINITE:
        return infinite_start_packs()
    return NARRATIVE_START_PACKS if kind == ChallengeRun.Kind.NARRATIVE else START_PACKS


def infinite_start_packs():
    """What staff set on the CPU tab, or INFINITE_START_PACKS if they never have."""
    settings = ChallengeSettings.current()
    return settings.start_packs if settings else INFINITE_START_PACKS


def loadout():
    """The specialty packs an infinite challenge starts with, to claim: [buff id, ...] (see LOADOUT_BUFFS)."""
    settings = ChallengeSettings.current()
    chosen = settings.loadout if settings else {}
    return [buff for buff in LOADOUT_BUFFS for _ in range(int(chosen.get(buff, 0)))]


def infinite_models():
    """INFINITE_MODELS with the floors each tier lasts as staff set them on the CPU tab."""
    settings = ChallengeSettings.current()
    floors = settings.tier_floors if settings and len(settings.tier_floors) == len(INFINITE_MODELS) else None
    return tuple((floors[i] if floors else count, models) for i, (count, models) in enumerate(INFINITE_MODELS))


def win_reward(kind):
    """(packs, rewards) that a win brings a challenge of this kind; "random" is any buff (weiss.buffs), "prize" one
    of the INFINITE_PRIZES."""
    if kind == ChallengeRun.Kind.NARRATIVE:
        return NARRATIVE_WIN_PACKS, NARRATIVE_WIN_REWARDS
    if kind == ChallengeRun.Kind.INFINITE:
        return INFINITE_WIN_PACKS, ("prize",)
    return WIN_PACKS, ()


def win_reward_text(kind):
    """What a win brings, for the player: "3 packs", "2 packs and a color pack"."""
    from .buffs import BUFFS  # weiss.buffs uses this module
    if kind == ChallengeRun.Kind.INFINITE:
        names = [BUFFS[prize].name.lower() for prize in INFINITE_PRIZES]
        return f"a pack and a {', '.join(names[:-1])} or {names[-1]}"
    count, rewards = win_reward(kind)
    parts = [f"{count} pack{'s' if count != 1 else ''}"] + [f"a {BUFFS[buff].name.lower()}" for buff in rewards]
    return " and ".join([", ".join(parts[:-1]), parts[-1]] if len(parts) > 1 else parts)


def boss_reward_text(run):
    """What beating a boss brings, for the player."""
    if run and run.coop_id:
        return f"{BOSS_PACKS} more packs on top of a win's reward, then a vs. battle with your partner, whose winner picks their augment and curse first"
    return f"an augment pick and {BOSS_PACKS} more packs on top of a win's reward, and a curse to take"


def boss_shown(run, floor):
    """What a page shows of the boss of this floor: {"reward"}, and in co-op how worn down it is ("health", "max",
    "down") and each player's share of the damage ("dealt": {user id: damage}; see coop.hit_boss)."""
    shown = {"reward": boss_reward_text(run)}
    if run.coop_id:
        boss = coop.boss_of(run.path, floor)
        shown.update(health=boss["health"], max=boss["max"], down=bool(boss.get("down")), dealt=dict(boss["dealt"]),
                     percent=round(boss["health"] / boss["max"] * 100) if boss["max"] else 0)
    return shown


def infinite(arcade_run):
    """Whether this arcade run is an infinite challenge's."""
    return bool(arcade_run and ChallengeRun.objects.filter(arcade_run=arcade_run, kind=ChallengeRun.Kind.INFINITE).exists())


def opponents():
    """The CPUs an infinite challenge draws from: every one players can fight."""
    return list(CpuProfile.objects.filter(finalized=True, deck__entries__isnull=False).distinct())


def column_x(column):
    """Where across the path a column sits, from 0 to 1."""
    return (column + .5) / COLUMNS


def links(here, ahead):
    """Which spaces of the next floor (`ahead`, by column) each space of a floor (`here`) leads to: only those beside
    it, straight up or one column over. So going left puts the right out of reach until a space in the middle has
    been through. A space with none beside it (a CPU taken off the path) leads to the nearest instead; an empty
    column leads nowhere."""
    filled = [c for c, node in enumerate(ahead) if node is not None]
    led = []
    for c, node in enumerate(here):
        near = [j for j in filled if abs(j - c) <= 1] if node is not None else []
        if node is not None and not near and filled:
            nearest = min(abs(j - c) for j in filled)
            near = [j for j in filled if abs(j - c) == nearest]
        led.append(near)
    return led


def event_chance():
    """The chance that a floor offers an event: what staff set on the CPU tab, or EVENT_CHANCE if they never have."""
    settings = ChallengeSettings.current()
    return settings.event_percent / 100 if settings else EVENT_CHANCE


def flash_chance():
    """The chance that a fight on the path is a flash battle: what staff set on the CPU tab, or FLASH_CHANCE."""
    settings = ChallengeSettings.current()
    return settings.flash_percent / 100 if settings else FLASH_CHANCE


def is_flash(path, f, node):
    """Whether the space in column `node` of floor `f` is a flash battle: both players start at level 2, with
    stock (see game.flash_start)."""
    return [f, node] in (path or {}).get("flash", [])


def flash_now(run):
    """Whether the fight this player's on is a flash battle: the space picked on their floor."""
    path, at = run.path or {}, floor_at(run)
    picks = path.get("picks", [])
    return at < len(picks) and is_flash(path, at, picks[at])


def boss_every(coop=False):
    """How many floors apart a solo (or co-op) challenge's bosses are, as staff set it on the CPU tab; 0 for none."""
    settings = ChallengeSettings.current()
    if not settings:
        return BOSS_EVERY
    return settings.coop_boss_every if coop else settings.boss_every


def bosses_and_others(found):
    """(the CPUs that can be bosses, those that can be fought on the other floors), from these: staff's bosses
    and the rest; with no bosses (or nothing but), any of them can be either."""
    bosses = [cpu.pk for cpu in found if cpu.boss]
    others = [cpu.pk for cpu in found if not cpu.boss]
    if not bosses or not others:
        return [cpu.pk for cpu in found], [cpu.pk for cpu in found]
    return bosses, others


def is_boss(path, f):
    """Whether floor `f` of a path is a boss's."""
    return f in (path or {}).get("bosses", [])


def boss_floor(bosses, met, rng):
    """A boss floor: one boss, in the middle, where every column leads; one not `met` on the path yet, if there's one left."""
    floor = [None] * COLUMNS
    floor[COLUMNS // 2] = rng.choice([pk for pk in bosses if pk not in met] or bosses)
    return floor


def new_floor(before, found, rng, events=False, chance=None):
    """A floor: COLUMNS columns, two or three of them filled (an empty one is a gap in the path), with CPUs all
    different and none from the floor before it if there are enough others; and with `events`, sometimes an event
    in place of one of them (`chance`, see event_chance). A floor of one is in the middle, where every column can reach it."""
    width = min(rng.choice(PATH_WIDTHS), len(found), COLUMNS)
    fresh = [pk for pk in found if pk not in before]
    nodes = rng.sample(fresh, min(width, len(fresh)))
    nodes += rng.sample([pk for pk in found if pk not in nodes], width - len(nodes))
    if events and rng.random() < (event_chance() if chance is None else chance):
        nodes.insert(rng.randrange(len(nodes) + 1), EVENT)
        if len(nodes) > min(max(PATH_WIDTHS), COLUMNS):
            nodes.remove(next(pk for pk in nodes if pk != EVENT))
    floor = [None] * COLUMNS
    for column, node in zip([COLUMNS // 2] if len(nodes) == 1 else sorted(rng.sample(range(COLUMNS), len(nodes))), nodes):
        floor[column] = node
    return floor


def on_grid(floors, picks):
    """Floors laid before the path had columns (a list of just the nodes) put into them, picks and all: one in the
    middle, two at the sides, three across."""
    for f, floor in enumerate(floors):
        if len(floor) != COLUMNS:
            columns = {1: [COLUMNS // 2], 2: [0, COLUMNS - 1]}.get(len(floor), list(range(len(floor))))
            floors[f] = [None] * COLUMNS
            for column, node in zip(columns, floor):
                floors[f][column] = node
            if f < len(picks) and picks[f] < len(columns):
                picks[f] = columns[picks[f]]


def floor_at(run):
    """The floor of the path an infinite challenge is on: the spaces it's been through, fights won and events. In
    co-op, this player's: one who's finished the floor is on the next while their partner plays it out."""
    if run.coop_id:
        return coop.floor_of(run.path, run.user_id)
    path = run.path or {}
    if "done" in path:
        return path["done"]
    return run.arcade_run.position if run.arcade_run_id else 0  # begun before events: a floor a win


def event_scenes():
    """The scenes an infinite challenge's events can play: those staff have chosen, without mistakes."""
    from .scenes import compile_scene  # weiss.scenes uses weiss.buffs, which uses this module
    return [scene for scene in Scene.objects.filter(infinite_event=True) if not compile_scene(scene.script)[1]]


@coop.sharing
def path_of(run, rng=random):
    """An infinite challenge's path, {"floors": [[CPU id, EVENT or None for each column], ...], "picks": [the column
    taken on each floor], "done": floors been through, "bosses": [the floors that are bosses'], "flash": [[floor, column]
    of each flash battle (see is_flash)]}, laid out PATH_AHEAD
    floors past the one it's on, plus anything else kept with it (the next fight's modifiers, an event under way).
    CPUs that can't be fought any more are taken off the floors still to come (one picked for a fight is let go too),
    and events if there are no event scenes; a floor left empty is laid again. Every boss_every floors is a boss's
    (see boss_floor), kept as one once it's laid. Saved if it changed."""
    path = {**(run.path or {}), "floors": [list(f) for f in (run.path or {}).get("floors", [])], "picks": list((run.path or {}).get("picks", []))}
    floors, picks = path["floors"], path["picks"]
    # In co-op the pair is on the floor both are on, and the path is laid ahead of whichever of them is further on.
    at = path["done"] = coop.pair_floor(run) if run.coop_id else floor_at(run)
    furthest = coop.furthest_floor(run) if run.coop_id else at
    if not floors and at:  # begun before there were paths: the fights so far, one CPU to a floor
        floors[:] = [[pk] for pk in run.arcade_run.order[:at]]
        picks[:] = [0] * at
    on_grid(floors, picks)
    events = bool(event_scenes())
    cpus = opponents()
    found = [cpu.pk for cpu in cpus]
    bosses, others = bosses_and_others(cpus)
    every = boss_every(coop=bool(run.coop_id))
    found_or_event = found + ([EVENT] if events else [])
    found_here = found_or_event if not path.get("event") else found_or_event + [EVENT]  # an event under way stays
    del picks[at + 1:]
    if len(picks) > at and floors[at][picks[at]] not in found_here and furthest == at:  # not once a co-op player's been through it
        del picks[at:]
    for f in range(at, len(floors)):
        floors[f] = [pk if pk in (found_here if f == at else found_or_event) else None for pk in floors[f]]
    first_empty = next((f for f in range(at, len(floors)) if not any(pk is not None for pk in floors[f])), len(floors))
    del floors[first_empty:]
    if path.get("flash"):
        path["flash"] = [space for space in path["flash"] if space[0] < first_empty]  # those floors are laid again
    flash = flash_chance()
    chance = event_chance() if events and len(floors) < furthest + 1 + PATH_AHEAD else 0
    while found and len(floors) < furthest + 1 + PATH_AHEAD:
        f = len(floors)
        if is_boss(path, f) or every and (f + 1) % every == 0:
            met = [floors[b][COLUMNS // 2] for b in path.get("bosses", []) if b < f]
            floors.append(boss_floor(bosses, met, rng))
            path["bosses"] = sorted({*path.get("bosses", []), f})
        else:
            floors.append(new_floor(floors[-1] if floors else [], others, rng, events=events and f > 0, chance=chance))
            if flash:
                spaces = [[f, c] for c, pk in enumerate(floors[f]) if pk not in (None, EVENT) and rng.random() < flash]
                if spaces:
                    path["flash"] = [*path.get("flash", []), *spaces]
    if path != run.path:
        run.path = path
        run.save(update_fields=["path"])
    return path


def choices(path, at):
    """The nodes of floor `at` that can be fought: the one picked, if it has been; else those the last pick leads to."""
    picks, floors = path["picks"], path["floors"]
    if at >= len(floors):
        return []
    if at < len(picks):
        return [picks[at]]
    if at == 0:
        return [c for c, node in enumerate(floors[0]) if node is not None]
    return links(floors[at - 1], floors[at])[picks[at - 1]]


@coop.sharing
def pick(run, node, rng=random):
    """Choose where an infinite challenge goes next: a node of the floor it's on that the path leads to. Returns
    that CPU's id (or EVENT), or None if it can't be chosen. A choice made stands until the fight's won or the
    event's over (or the CPU's gone). In co-op this is a vote, and it's None until both players have voted (see
    coop.vote), unless there's only one way on."""
    path = path_of(run)
    at = floor_at(run)
    if at < len(path["picks"]):
        node = path["picks"][at]
    elif node not in choices(path, at):
        return None
    elif run.coop_id and len(choices(path, at)) > 1 and (node := coop.vote(run, path, f"floor:{at}", node, rng)) is None:  # one way on: no vote
        run.path = path
        return None
    else:
        path["picks"].append(node)
        run.path = path
        run.save(update_fields=["path"])
    return path["floors"][at][node]


def tier(fight):
    """What the path calls how hard its floor number `fight` (from 0) is (see INFINITE_MODELS)."""
    for (count, _), name in zip(infinite_models(), INFINITE_TIERS):
        if fight < count:
            return name
        fight -= count
    return "Hard"


def defeated(run):
    """The CPUs an infinite challenge has beaten, in order, as ids."""
    path = run.path or {}
    taken = [path["floors"][f][node] for f, node in enumerate(path.get("picks", [])[:floor_at(run)])]
    return [pk for pk in taken if pk != EVENT]


@coop.sharing
def start_event(run, rng=random):
    """The event space just picked: a random event scene, one this challenge hasn't had if there's one left, settled
    now (buffs and all, see buffs.resolve) and kept with the path until it's over (see end_event). Returns its
    payload, or None if there are no event scenes any more (the space is passed by then)."""
    from .scenes import playable  # weiss.scenes uses weiss.buffs, which uses this module
    path = path_of(run)
    if path.get("event"):
        return path["event"]
    found = event_scenes()
    fresh = [scene for scene in found if scene.pk not in path.get("seen", [])] or found
    payload = next(iter(playable([rng.choice(fresh)], with_buffs=True, rng=rng, viewer=run.user) if fresh else []), None)
    if payload:
        path["event"] = payload
        path["seen"] = [*path.get("seen", []), int(payload["key"].split("-")[0])]
    else:
        path["done"] += 1
    run.path = path
    run.save(update_fields=["path"])
    return payload


@coop.sharing
def end_event(run, picks, rng=random):
    """The event scene's been played: what its choices gave (from the page: see buffs.given) goes on the challenge,
    and the path moves on a floor. Returns what happened, for the player (see buffs.grant). In co-op, it goes on
    both players' challenges, and both move on."""
    from .buffs import given, grant  # weiss.buffs uses this module
    path = path_of(run)
    payload = path.pop("event", None)
    if not payload:
        return []
    source = f"Event: {payload.get('title', '')}"
    if run.coop_id:
        # The pair played it together: what its choices gave (as they decided them) goes to both, and both move on.
        buffs = given(payload, coop.agreed(path, payload, picks))
        run.path = path
        coop.finish_floor(run, coop.players(run.coop))
        coop.for_partner(run, lambda other: grant(other, buffs, source, rng))
        return grant(run, buffs, source, rng)
    path["done"] += 1
    run.path = path
    return grant(run, given(payload, picks), source, rng)


def infinite_style(arcade_run, profile):
    """(model, aggression) a CPU plays an infinite challenge's fight with, by how far up the path it is (see
    INFINITE_MODELS); or at its hardest, after a blood pact. Random choices are settled by the run and floor, so a
    fight keeps them, reloads and all."""
    from .cpu import MAX_AGGRESSION, MIN_AGGRESSION  # weiss.cpu needs nothing from here; this keeps it that way
    run = of(arcade_run)
    fight = floor_at(run) if run else arcade_run.position
    if run and "blood_pact" in (run.path or {}).get("next", []):
        return "hard", MAX_AGGRESSION
    rng = random.Random(f"{arcade_run.pk}:{fight}")
    for count, models in infinite_models():
        if fight < count:
            return rng.choice(models), profile.aggression
        fight -= count
    return "hard", rng.randint(MIN_AGGRESSION, MAX_AGGRESSION)


def of(arcade_run):
    """The challenge in progress that this arcade run is fought for, if it's one."""
    run = ChallengeRun.objects.filter(arcade_run=arcade_run, status=ChallengeRun.Status.ACTIVE).select_related("coop").first() if arcade_run else None
    return coop.load(run)


def narrative(arcade_run):
    """Whether this arcade run is a narrative challenge's: its scenes do the talking, so the CPUs' own intro and
    end-of-fight lines are left out."""
    run = of(arcade_run)
    return bool(run and run.kind == ChallengeRun.Kind.NARRATIVE)


def deck_name(name):
    return f"{name} challenge"[:100]


def start(user, kind, scenario, narrative=None):
    """A new challenge: an empty deck and its packs to open (see start_packs), and an infinite one's loadout."""
    name = narrative.name if narrative else scenario.name if scenario else INFINITE_NAME
    with transaction.atomic():
        deck = CardList.objects.create(user=user, name=deck_name(name), challenge=True)
        run = ChallengeRun.objects.create(user=user, kind=kind, narrative=narrative, scenario=scenario, name=name, deck=deck,
                                          sets=list(narrative.sets) if narrative else [], packs=start_packs(kind))
        give_loadout(run)
        return run


def give_loadout(run):
    """An infinite challenge's specialty packs to start with, waiting on its page to be claimed."""
    if run.kind == ChallengeRun.Kind.INFINITE and (buffs := loadout()):
        from .buffs import grant  # weiss.buffs uses this module
        grant(run, buffs, "Starting loadout")


def allowed_sets(run):
    """[{"id", "name", "cards"}] that this challenge's packs can come from (see packs.pack_sets)."""
    sets = packs.pack_sets()
    return [entry for entry in sets if entry["id"] in run.sets] if run.sets else sets


@coop.sharing
def open_packs(run, expansion_id, count, rng=random):
    """Open some of the challenge's packs into its pool. Returns what the pack opening page shows, or raises
    ValueError saying why it can't."""
    if run.status != ChallengeRun.Status.ACTIVE:
        raise ValueError("This challenge is over.")
    if not 1 <= count <= run.packs:
        raise ValueError(f"You have {run.packs} pack{'s' if run.packs != 1 else ''} to open.")
    if expansion_id not in {entry["id"] for entry in allowed_sets(run)}:
        raise ValueError("This challenge's packs don't come from that set.")
    pool = packs.Pool.for_set(expansion_id)
    opened = packs.open_packs(pool, count, rng)
    for pack in opened:
        for pull in pack:
            run.pool[str(pull.card.pk)] = run.pool.get(str(pull.card.pk), 0) + 1
    run.packs -= count
    run.opened += count
    run.last_opening = {"set": pool.set_name, "set_id": expansion_id, "grades": packs.GRADE_NAMES,
                        "packs": [[pull.as_dict() for pull in pack] for pack in opened]}
    run.save(update_fields=["pool", "packs", "opened", "last_opening"])
    return run.last_opening


def pool_cards(run):
    """[(card, copies pulled, copies in the deck)], in the order a deck lists them. In co-op, copies pulled are the
    pool's less those in the partner's deck."""
    in_deck = dict(run.deck.entries.values_list("card_id", "quantity")) if run.deck else {}
    pool = coop.available(run)  # in co-op, the copies the partner's deck has aren't this player's to use
    cards = Card.objects.filter(pk__in=[int(pk) for pk in pool]).order_by("level", "card_type", "serial_number")
    return [(card, pool[str(card.pk)], in_deck.get(card.pk, 0)) for card in cards]


def deck_pool(run):
    """The pool for building the deck: [(card, copies this player can use, copies in their deck, copies in the
    partner's deck)], in the order a deck lists them. In co-op every card the pair has pulled is here, those the
    partner's deck has all of too, so both players always see the whole pool; solo, the partner's copies are 0."""
    in_deck = dict(run.deck.entries.values_list("card_id", "quantity")) if run.deck else {}
    theirs = coop.partner_copies(run)
    cards = Card.objects.filter(pk__in=[int(pk) for pk in run.pool]).order_by("level", "card_type", "serial_number")
    return [(card, run.pool[str(card.pk)] - theirs.get(card.pk, 0), in_deck.get(card.pk, 0), theirs.get(card.pk, 0)) for card in cards]


@coop.sharing
def save_deck(run, copies):
    """Make the deck exactly these {card id: copies}. Returns what's wrong with them (nothing is saved then), or None.
    In co-op, it can't have the copies the partner's deck has (both are checked under the same lock, see coop.shared).
    An infinite challenge's deck can be saved over DECK_SIZE cards while it's being built, but can't fight like that
    (see deck_ready)."""
    copies = {int(pk): int(n) for pk, n in copies.items() if int(n) > 0}
    pool = coop.available(run)
    for pk, n in copies.items():
        if n > pool.get(str(pk), 0):
            return ("Your partner's deck has those copies: they'll have to take them out first." if n <= run.pool.get(str(pk), 0)
                    else "A deck can only have the cards you've pulled from your packs.")
    if sum(copies.values()) > DECK_SIZE and run.kind != ChallengeRun.Kind.INFINITE:
        return f"A deck has at most {DECK_SIZE} cards."
    if problem := deck_rules_broken(run, copies):
        return problem
    with transaction.atomic():
        run.deck.entries.all().delete()
        CardListEntry.objects.bulk_create(CardListEntry(card_list=run.deck, card_id=pk, quantity=n) for pk, n in copies.items())
        run.deck.save(update_fields=["updated"])
    return None


def deck_rules_broken(run, copies):
    """What's wrong with a deck of these {card id: copies} as it's built, or None: more climaxes than a deck can have
    (CLIMAX_COUNT, or more with Climax Overload), or since Highlander was picked, more copies of a card than it
    allows (see weiss.augments). The rules' 4 copies of a card are only warned about (the deck builder shows them)."""
    cards = Card.objects.in_bulk(copies)
    climaxes = sum(n for pk, n in copies.items() if pk in cards and is_climax(cards[pk]))
    if climaxes > augments.climax_limit(run):
        return climax_problem(climaxes, augments.climax_limit(run))
    if not augments.has(run, "highlander"):
        return None
    by_name, free = {}, set()
    for pk, n in copies.items():
        if pk in cards:
            by_name[cards[pk].name] = by_name.get(cards[pk].name, 0) + n
            if unlimited(cards[pk]):
                free.add(cards[pk].name)
    most = augments.copy_limit(run)
    over = sorted(name for name, n in by_name.items() if n > most and name not in free)
    return f"Highlander: a deck can run at most {most} copies of a card, not {', '.join(over)}." if over else None


def deck_ready(run):
    """What stops this deck being fought with as it is, or None: more than DECK_SIZE cards (only an infinite deck can be
    saved like that, see save_deck), what deck_rules_broken says, or too few climaxes (a deck can be short of DECK_SIZE cards while the pool grows, but not of climaxes)."""
    if not run.deck:
        return None
    copies = dict(run.deck.entries.values_list("card_id", "quantity"))
    climaxes = sum(run.deck.entries.filter(card__card_type__iexact="climax").values_list("quantity", flat=True))
    total = sum(copies.values())
    problem = ((total > DECK_SIZE and run.kind == ChallengeRun.Kind.INFINITE and f"A deck has at most {DECK_SIZE} cards, and this one has {total}.")
               or deck_rules_broken(run, copies) or climax_problem(climaxes, augments.climax_limit(run)))
    return problem and f"{problem} Change your deck to fight on."


def fought(room):
    """What an infinite challenge's game that's just ended was (see play.stamp_floor): {"floor" it was dealt for,
    "boss": whether it was a boss's}."""
    return {"floor": room.state.get("floor"), "boss": bool(room.state.get("boss"))}


def fight_finished(arcade_run, won, cleared, rng=random, fought=None):
    """A fight in a challenge's run has ended (see arcade.game_finished): a win brings packs; a loss ends it.
    Beating a boss (`fought`, see above) brings BOSS_PACKS more. Returns the prize a win drew (an infinite
    challenge's), for the Victory screen to show being drawn; or None."""
    run = of(arcade_run)
    if not run:
        return None
    fought = fought or {}
    if run.coop_id:
        return coop_fight_finished(run, won, rng, fought)
    prize = None
    if won:
        from .buffs import AMBUSH_PACKS, fight_mods, grant, roll  # weiss.buffs uses this module
        count, rewards = win_reward(run.kind)
        run.packs += count
        if "ambush" in fight_mods(run):
            run.packs += AMBUSH_PACKS
        extra_packs, extra_rewards = augments.win_extras(run)
        run.packs += extra_packs
        if fought.get("boss"):
            beat_boss(run, rng)
        path = {**(run.path or {}), "next": []}  # the fight's modifiers are done with
        if run.kind == ChallengeRun.Kind.INFINITE:
            path["done"] = floor_at(run) + 1  # up a floor
        run.path = path
        drawn = []
        for buff in rewards:
            if buff == "prize":
                buff = prize = rng.choice(augments.prizes(run, INFINITE_PRIZES))
            elif buff == "random":
                buff = roll(1, rng)[0]
            drawn.append(buff)
        grant(run, drawn + extra_rewards, "Victory", rng)
        if cleared:
            run.status = ChallengeRun.Status.WON
    elif run.lives >= augments.loss_cost(run):  # a second chance (two, with Glass Cannon): the fight's there to try again
        run.lives -= augments.loss_cost(run)
    else:
        run.status = ChallengeRun.Status.LOST
        arcade_run.status, arcade_run.finished = ArcadeRun.Status.ABANDONED, timezone.now()
        arcade_run.save(update_fields=["status", "finished"])
    if won or run.status == ChallengeRun.Status.LOST:
        snapshot_deck(run)
    run.save(update_fields=["packs", "rewards", "status", "lives", "path", "deck_snapshot"])
    return prize


def beat_boss(run, rng=random):
    """A boss beaten: BOSS_PACKS more packs to open, an augment to pick (weiss.augments), and a curse to take
    (weiss.curses), before the next fight (curse_due). In co-op the augment and curse come from the pair's vs.
    battle instead (coop.start_duel)."""
    from .buffs import grant  # weiss.buffs uses this module
    run.packs += BOSS_PACKS
    if not run.coop_id:
        grant(run, ["augment", "curse"], "Boss", rng)


def curse_due(run):
    """What's wrong if this player has a curse still to take, which they must before their next fight; or None."""
    if run.coop_id and (problem := coop.duel_due(run)):
        return problem
    if any(reward["buff"] == "curse" for reward in run.rewards or []):
        return "Take your curse first: beating the boss means taking one before your next fight."
    return None


def coop_fight_finished(run, won, rng=random, fought=None):
    """fight_finished, for one player of a co-op challenge: win or lose, they're done with this floor (see
    coop.finish_floor). A win brings them packs and a prize, as in solo; a loss uses up one of their second chances,
    or else counts towards the pair's limit (see coop.lost_game). A boss's floor is done only once the boss is down,
    both players' games having worn it down together as they went (see wear_boss): then it's done for both, both
    have beaten it, and a game against it still going is won (play.wear_boss ends it). A win against a boss that
    isn't down (it couldn't refresh its deck) doesn't count, and nor does a game for a floor the player is done with."""
    from .buffs import AMBUSH_PACKS, fight_mods, grant  # weiss.buffs uses this module
    fought = fought or {}
    prize = None
    with coop.shared(run):
        floor = fought.get("floor")
        down = bool(fought.get("boss") and coop.boss_of(run.path, floor).get("down"))
        if floor is not None and floor != floor_at(run) and not down:
            return None  # a floor this player is done with
        if fought.get("boss") and won != down:
            return None  # a win against a boss with health left (it couldn't refresh its deck), or a loss once it was down
        if won:
            count, _ = win_reward(run.kind)
            extra_packs, extra_rewards = augments.win_extras(run)
            run.packs += count + extra_packs + (AMBUSH_PACKS if "ambush" in fight_mods(run) else 0)
            prize = rng.choice(augments.prizes(run, INFINITE_PRIZES))
            grant(run, [prize, *extra_rewards], "Victory", rng)
        if not fought.get("boss"):
            coop.finish_floor(run)
        cost = augments.loss_cost(run)  # two with Glass Cannon
        if not won and run.lives >= cost:
            run.lives -= cost
        elif not won and coop.lost_game(run, cost):
            return None  # that was the last loss: it's over for both (see coop.end)
        snapshot_deck(run)
        run.save(update_fields=["packs", "rewards", "lives", "path", "deck_snapshot"])
    return prize


def wear_boss(run, floor, dealt, rng=random):
    """This player's game against the co-op boss of `floor` has just dealt it this much damage (see play.wear_boss):
    off the pair's health bar for it, and if that empties it, it's down (coop_boss_down). Returns whether it's down,
    now or already (or this player is past its floor)."""
    with coop.shared(run):
        if floor != floor_at(run):
            return True
        if coop.boss_of(run.path, floor).get("down"):
            return True
        if not dealt or not coop.hit_boss(run, floor, dealt):
            return False
        coop_boss_down(run, rng)
        run.save(update_fields=["packs", "rewards"])
    return True


def boss_down(run, floor):
    """Whether the co-op boss of `floor` is down (or this player is past its floor), as the pair's path has it now."""
    return floor != floor_at(run) or bool(coop.boss_of(run.path, floor).get("down"))


def coop_boss_down(run, rng=random):
    """The pair's boss is down: its floor is done for both of them, and both have beaten it. Call within coop.shared."""
    run.path["boss"]["down"] = True
    coop.finish_floor(run, coop.players(run.coop))
    coop.start_duel(run, run.path["boss"]["floor"], rng)
    beat_boss(run, rng)

    def partner_beat_it(other):
        beat_boss(other, rng)
        other.save(update_fields=["packs", "rewards"])
    coop.for_partner(run, partner_beat_it)


def snapshot_deck(run):
    """Keep the deck as it is now with the run (not saved here), for the leaderboard: the deck itself can be
    discarded at the end, or changed."""
    if run.deck_id:
        run.deck_snapshot = deck_snapshot(run.deck)


def deck_snapshot(deck):
    """A deck's cards as [[card id, copies]], to keep after the deck itself is changed or goes."""
    return [[pk, n] for pk, n in deck.entries.order_by("card_id").values_list("card_id", "quantity")]


def leaderboard(limit=50):
    """The best infinite challenges, by their run's score (the wins' scores added up), the earliest first on a tie:
    those that have won at least once. Each has `defeated` and `floor` worked out."""
    runs = list(ChallengeRun.objects.filter(kind=ChallengeRun.Kind.INFINITE, coop__isnull=True, arcade_run__score__gt=0)
                .select_related("user", "arcade_run").order_by("-arcade_run__score", "arcade_run__started", "pk")[:limit])
    for run in runs:
        run.defeated_count = len(defeated(run))
        run.floor = floor_at(run) + 1
    return runs


def prize_shown(prize):
    """What the slot machine needs: its reel (the prizes there are) and which one it stops on."""
    from .buffs import BUFFS  # weiss.buffs uses this module
    return {"reel": [{"buff": buff, "name": BUFFS[buff].name} for buff in INFINITE_PRIZES],
            "won": INFINITE_PRIZES.index(prize), "packs": INFINITE_WIN_PACKS}


def stop_fighting(run):
    """Take down the room its run is being fought in, if there is one; the run stays where it is."""
    if run.arcade_run_id:
        GameRoom.objects.filter(arcade_run_id=run.arcade_run_id).delete()


def give_up(run, keep_room=False):
    """End an active challenge as lost, so the player can keep or discard its deck. (`keep_room`: its fight is left
    to finish, as a co-op partner's is when the other's loss ends the challenge.)"""
    if not keep_room:
        stop_fighting(run)
    if run.arcade_run and run.arcade_run.status == ArcadeRun.Status.ACTIVE:
        run.arcade_run.status, run.arcade_run.finished = ArcadeRun.Status.ABANDONED, timezone.now()
        run.arcade_run.save(update_fields=["status", "finished"])
    run.status = ChallengeRun.Status.LOST
    snapshot_deck(run)
    run.save(update_fields=["status", "deck_snapshot"])


def reset(run):
    """Start the challenge again from nothing: the old deck goes, and with it the pool and the run."""
    with transaction.atomic():
        give_up(run)
        if run.deck:
            run.deck.delete()
        run.deck = CardList.objects.create(user=run.user, name=deck_name(run.name), challenge=True)
        run.pool, run.packs, run.opened, run.last_opening, run.rewards, run.lives, run.path, run.curses = {}, start_packs(run.kind), 0, {}, [], 0, {}, []
        run.arcade_run, run.status, run.started = None, ChallengeRun.Status.ACTIVE, timezone.now()
        run.save()
        give_loadout(run)


def close(run, keep, name=""):
    """The player is done with it: keep the deck as one of their lists, under this name, or discard it.
    Returns what's wrong (nothing changes then), or None."""
    if keep and run.deck:
        if CardList.objects.players(run.user).count() >= CardList.MAX_LISTS_PER_USER:
            return f"You already have {CardList.MAX_LISTS_PER_USER} lists; delete one first, or discard this deck."
        run.deck.challenge = False
        run.deck.name = (name.strip() or run.deck.name)[:100]
        run.deck.save(update_fields=["challenge", "name", "updated"])
    with transaction.atomic():
        if run.status == ChallengeRun.Status.ACTIVE:
            give_up(run)
        if not keep and run.deck:
            run.deck.delete()
            run.deck = None
        run.finished = timezone.now()
        run.save(update_fields=["deck", "finished"])
    return None
