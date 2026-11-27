"""World mode's cast, a few at a time: who's in a save's town (WorldSave.roster).

A new save starts with a small cast (WorldSettings.start_cast, at least MIN_VILLAINS of them villains) and a few more
arrive each week (weekly_cast). CPUs a quest ties together (one's quest names another, locks another's, or needs
another's done) are one group, and a group always arrives together; otherwise the order's drawn from the save's seed.
The plan is made once and kept, as waves: {"start_week": the week wave 0 is in town, "waves": [[cpu ids], ...],
"known": every CPU the plan has placed}, so reloading never changes it. A CPU made after the plan was (finalized later)
joins the next week's wave.

Each newcomer's arrival plays a scene, if one's written (docs/world-arrivals-plan.md):
"World: Arrival, <newcomer> & <resident>" with someone already in town, else "World: Arrival, <newcomer>". Its choice
says whose side the player takes (an option's "(set side_<cast id>)") and may give a pack ("(give climax_pack)");
arrival_done pays it: friendship points with that character, and the pack or, if none, arrival coins.

The scene plays when the player meets the newcomer (meet, meet_here), one at a time, never in a run: a week's newcomers
used to play back to back as the week began, and that was disorienting ("Pacing change" in the plan). Until then they're
pending, in flags["arrivals"], and the town marks them as new.
"""
import random

from . import quests, scenes, world, world_calendar as calendar
from .models import CpuProfile, Quest, Scene, WorldSave

MIN_VILLAINS = 2
START_CAST, WEEKLY_CAST = 12, 4  # until staff set them (WorldSettings)
ARRIVAL_COINS, ARRIVAL_POINTS = 200, 8
ARRIVAL = "World: Arrival, "  # how arrival scenes are named
PACKS = ("lucky_pack", "climax_pack", "color_pack")  # what an arrival option can give ("(give …)")


def numbers():
    """(start cast, weekly arrivals, arrival coins, arrival points) as staff set them."""
    found = world.settings()
    if not found:
        return START_CAST, WEEKLY_CAST, ARRIVAL_COINS, ARRIVAL_POINTS
    return found.start_cast, found.weekly_cast, found.arrival_coins, found.arrival_points


def everyone():
    """The CPUs who can be in town: finalized, with a deck and haunts."""
    return sorted(world.haunts())


# ---------------------------------------------------------------- Planning the waves

def named_in(spec):
    """The CPU names a quest's spec mentions: objectives' cpus, against, cpu and to; endings' to and removes."""
    found = []
    for stage in spec.get("stages", []):
        for obj in stage.get("objectives", []):
            for field in ("cpus", "against"):
                found += obj.get(field) or []
            for field in ("cpu", "to"):
                if obj.get(field):
                    found.append(obj[field])
    for ending in spec.get("endings", []):
        if ending.get("to"):
            found.append(ending["to"])
        found += ending.get("removes") or []
    return found


def linked_groups(cpu_ids):
    """[[cpu ids]]: CPUs a quest ties together in one group (a quest naming another CPU, locking or needing another's
    quest), the rest alone. Sorted, so the same CPUs always make the same groups."""
    parent = {pk: pk for pk in cpu_ids}

    def root(pk):
        while parent[pk] != pk:
            parent[pk] = parent[parent[pk]]
            pk = parent[pk]
        return pk

    def join(a, b):
        if a in parent and b in parent:
            parent[root(a)] = root(b)

    names = {name.lower(): pk for pk, name in CpuProfile.objects.filter(pk__in=cpu_ids).values_list("pk", "name")}
    found = list(Quest.objects.all())
    givers = {quest.key: quest.giver_id for quest in found}
    for quest in found:
        if quest.giver_id not in parent:
            continue
        spec = quest.spec or {}
        for name in named_in(spec):
            join(quest.giver_id, names.get(str(name).lower()))
        others = [lock for ending in spec.get("endings", []) for lock in ending.get("locks") or []]
        others += (spec.get("requires") or {}).get("quests", [])
        for key in others:
            join(quest.giver_id, givers.get(key))
    groups = {}
    for pk in cpu_ids:
        groups.setdefault(root(pk), []).append(pk)
    return sorted(sorted(group) for group in groups.values())


def plan(save, cpu_ids, keep=()):
    """The waves: wave 0 holds those in `keep` (whom an existing save's player knows already), at least MIN_VILLAINS
    villains, then groups drawn at random until it has the starting cast; after that, a wave a week of about
    weekly_cast (a group is never split, so a wave can run over)."""
    start, weekly, _, _ = numbers()
    rng = random.Random(f"{save.seed}:roster")
    groups = linked_groups(cpu_ids)
    rng.shuffle(groups)
    villains = set(CpuProfile.objects.filter(pk__in=cpu_ids, temperament="villain").values_list("pk", flat=True))
    first = []

    def take(group):
        first.extend(group)
        groups.remove(group)

    for group in [group for group in groups if set(group) & set(keep)]:
        take(group)
    for group in [group for group in groups if set(group) & villains]:
        if len(set(first) & villains) >= MIN_VILLAINS:
            break
        take(group)
    for group in list(groups):
        if len(first) >= start:
            break
        take(group)
    waves, wave = [sorted(first)], []
    for group in groups:
        if wave and len(wave) + len(group) > weekly:
            waves.append(sorted(wave))
            wave = []
        wave += group
    if wave:
        waves.append(sorted(wave))
    return waves


def week_index(save, turn=None):
    """Which wave the save's town is up to at this turn (0: the starting cast's week)."""
    roster = save.roster or {}
    return calendar.week_of(save.turn if turn is None else turn) - roster.get("start_week", 0)


def ensure(save):
    """The save's roster, planned now if it hasn't one (a save made before the cast came a few at a time keeps
    everyone the player's already met in its first wave), and with any CPU made since placed in next week's wave.
    Saves it if it changed. A save that isn't stored (a staff grid's sample) has none: everyone's in town."""
    if not save.pk:
        return None
    roster = save.roster or {}
    cpus = everyone()
    if not cpus:
        return roster
    changed = False
    if not any(roster.get("waves") or []):  # no plan yet (or one made when nobody could be in town): plan now
        met = {int(pk) for pk, rel in (save.relations or {}).items() if rel.get("points")}
        met |= {quest.giver_id for key, quest in quests.quests(save).items() if quest.giver_id and key in quests.log(save)}
        roster = {"start_week": calendar.week_of(save.turn), "waves": plan(save, cpus, keep=met), "known": cpus}
        changed = True
    else:
        new = [pk for pk in cpus if pk not in set(roster.get("known", []))]
        if new:
            nxt = max(week_index(save) + 1, 1)
            while len(roster["waves"]) <= nxt:
                roster["waves"].append([])
            roster["waves"][nxt] = sorted(set(roster["waves"][nxt]) | set(new))
            roster["known"] = sorted(set(roster["known"]) | set(new))
            changed = True
    if changed:
        save.roster = roster
        save.save(update_fields=["roster"])
    return roster


def released(save, day=None):
    """The CPU ids in the save's town on this day (counting from 0; default today), or None if it has no roster
    (everyone's in town)."""
    roster = save.roster or {}
    if not any(roster.get("waves") or []):  # no plan, or nobody placed yet: everyone's in town
        return None
    index = week_index(save, (calendar.day_of(save.turn) if day is None else day) * len(WorldSave.TIMES))
    return {pk for wave in roster["waves"][:max(index, 0) + 1] for pk in wave}


def newcomers(save):
    """The CPUs who arrived this week (none in the starting week)."""
    roster = ensure(save) or {}
    index = week_index(save)
    return list(roster["waves"][index]) if roster and 1 <= index < len(roster.get("waves", [])) else []


# ---------------------------------------------------------------- Arrivals

def week_started(save):
    """A new week: this week's newcomers are in town and the town says who. Those with an arrival scene wait to be met
    (meet, meet_here): nothing plays by itself."""
    arrived = newcomers(save)
    if not arrived:
        return
    names = list(CpuProfile.objects.filter(pk__in=arrived).order_by("name").values_list("name", flat=True))
    quests.news(save, f"New in town this week: {quests.names(names)}.")
    scened = [cpu.pk for cpu in CpuProfile.objects.filter(pk__in=arrived) if arrival_scene(save, cpu)]
    waiting = [pk for pk in pending(save) if pk not in scened] + [pk for pk in arrived if pk in scened]
    if waiting:
        save.flags["arrivals"] = waiting


def arrival_scene(save, cpu):
    """The scene a newcomer's arrival plays: one with someone in town ("World: Arrival, <name> & <other>": someone
    already here, or a fellow newcomer, as those a quest ties together arrive in the same week; drawn for the save if
    there are several), else its own ("World: Arrival, <name>"), else None."""
    here = (released(save) or set()) - {cpu.pk}
    names = dict(CpuProfile.objects.filter(pk__in=here).values_list("name", "pk"))
    lower = {name.lower(): pk for name, pk in names.items()}
    paired = []
    for scene in Scene.objects.filter(name__istartswith=f"{ARRIVAL}{cpu.name} & "):
        resident = scene.name[len(f"{ARRIVAL}{cpu.name} & "):].strip().lower()
        if resident in lower:
            paired.append(scene)
    if paired:
        return random.Random(f"{save.seed}:{cpu.pk}:arrival").choice(sorted(paired, key=lambda scene: scene.pk))
    return Scene.objects.filter(name__iexact=f"{ARRIVAL}{cpu.name}").first()


def pending(save):
    """The newcomers whose arrival hasn't played yet (the town marks them as new)."""
    return [int(pk) for pk in save.flags.get("arrivals", [])]


def meet(save, cpu_id):
    """The player meets a newcomer whose arrival hasn't played: their arrival scene plays now (the town goes to it), if
    nothing else is waiting to be watched. Returns whether it did. A newcomer whose scene can't be played any more (no
    one it needs is in town) has simply arrived: they stop being new."""
    cpu_id = int(cpu_id)
    queue = pending(save)
    if cpu_id not in queue or save.flags.get("scene"):
        return False
    queue.remove(cpu_id)
    if queue:
        save.flags["arrivals"] = queue
    else:
        save.flags.pop("arrivals", None)
    cpu = CpuProfile.objects.filter(pk=cpu_id).first()
    scene = arrival_scene(save, cpu) if cpu else None
    if not scene:
        return False
    save.flags["scene"] = {"scene": scene.pk, "cpu": cpu.pk, "auto": True, "arrival": cpu.pk}
    return True


def meet_here(save):
    """The player's come to a place (or stayed there into a new time of day): one newcomer here whose arrival hasn't
    played is met, the first in the order they came. Others here wait to be talked to, or for the next time. Nothing
    plays if a scene's already waiting (a quest's visit, say): one scene at a time. Returns whether one did."""
    queue = pending(save)
    if not queue or save.flags.get("scene"):
        return False
    here = {cpu.pk for cpu, _ in world.present(save)}
    first = next((pk for pk in queue if pk in here), None)
    return meet(save, first) if first is not None else False


def arrival_done(save, chosen_flags, chosen_buffs):
    """An arrival scene's over: the side the player took (an option's "set side_<cast id>"; the newcomer, if none)
    gets friendship points, and its pack ("give …") or the arrival coins are given. Once. Returns {"rewards": [words],
    "link": a link to see a pack's cards or ""}."""
    pending = save.flags.get("scene") or {}
    if not pending.get("arrival"):
        raise ValueError("There's no arrival to finish.")
    scene = Scene.objects.filter(pk=pending["scene"]).first()
    newcomer = CpuProfile.objects.filter(pk=pending["arrival"]).first()
    cast = scenes.compile_scene(scene.script)[0]["cast"] if scene else {}
    sides = [cast[flag[len("side_"):]] for flag in chosen_flags if flag.startswith("side_") and flag[len("side_"):] in cast]
    side = sides[0] if sides else newcomer
    coins, points = numbers()[2:]
    words, link = [], ""
    if side:
        gained = world.gain(side, points)
        before, after = world.add_points(save, side.pk, gained)
        words.append(f"+{gained} ♥ with {side.name}")
        if after > before:
            words.append(f"You and {side.name} are now: {world.rank_names()[after]}")
            words += [text for text, _ in world.reward_ranks(save, side, after)]
    pack = next((buff for buff in chosen_buffs if buff in PACKS), None)
    given = world.give_reward(save, newcomer, "pack", pack) if pack and newcomer else None
    if given:
        words.append(given[0])
        link = given[1]
    elif coins:
        save.money += coins
        words.append(f"{coins:,} coins")
    save.flags.pop("scene", None)
    world.next_scene(save)
    world.changed(save, *world.TALK_FIELDS)
    return {"rewards": words, "link": link}



def bring(save, cpu_ids):
    """Bring these CPUs into town now, if they haven't arrived yet (a story chapter that needs them has begun): they
    move from a later wave into this week's. Returns those brought."""
    roster = save.roster or {}
    if not any(roster.get("waves") or []):
        return []
    here = released(save) or set()
    index = max(week_index(save), 0)
    while len(roster["waves"]) <= index:
        roster["waves"].append([])
    able = set(everyone())
    brought = []
    for pk in dict.fromkeys(cpu_ids):
        if pk in here or pk not in able:
            continue
        for wave in roster["waves"][index + 1:]:
            if pk in wave:
                wave.remove(pk)
        roster["waves"][index] = sorted(set(roster["waves"][index]) | {pk})
        roster["known"] = sorted(set(roster.get("known", [])) | {pk})
        brought.append(pk)
    if brought:
        save.roster = roster
        names = list(CpuProfile.objects.filter(pk__in=brought).order_by("name").values_list("name", flat=True))
        quests.news(save, f"{quests.names(names)} {'has' if len(names) == 1 else 'have'} come to town.")
    return brought
