"""World mode (see docs/world-mode.md): a player's saves, and what a save has: its time, place, coins, the cards
opened from its packs and the deck built from them.

A new save starts with packs of a set the player chooses (only sets big enough to fill packs, MIN_SET_CARDS) and the
specialty packs staff set (WorldSettings), and nothing else: every card in its deck comes from those, as in a
challenge. The pack opening, the specialty packs and the deck rules are the challenges' (weiss.packs, weiss.buffs,
weiss.challenge); a save has the fields they read (pool, packs, rewards, last_opening, sets).
"""
import random
import re
import secrets
from collections import Counter
from types import SimpleNamespace

from django.db import transaction
from django.urls import reverse

from . import buffs, challenge, chatter, packs, quests
from .lists import CLIMAX_COUNT, COPY_LIMIT, DECK_SIZE, climax_problem, is_climax, unlimited, unplayable
from .models import (Card, CardList, CardListEntry, CpuProfile, CpuSchedule, GameRoom, GiftItem, WorldPlace, WorldSave, WorldSettings,
                     default_ranks)

MIN_SET_CARDS = 100  # cards a set needs in its packs to start a save with
MAX_DECKS = 10  # a save's decks: all built from the same cards it's opened, one of them equipped for duels
DECK_NAME = 100  # characters in a deck's name
START_PACKS = 20  # until staff set them (WorldSettings)
START_MONEY = 1000


def settings():
    return WorldSettings.current()


def start_packs():
    found = settings()
    return found.start_packs if found else START_PACKS


def start_money():
    found = settings()
    return found.start_money if found else START_MONEY


def loadout():
    """The specialty packs a new save starts with: [buff id, ...] (only those a challenge's loadout can have)."""
    found = settings()
    chosen = found.loadout if found else {}
    return [buff for buff in challenge.LOADOUT_BUFFS for _ in range(int(chosen.get(buff, 0)))]


def offered_sets():
    """[{"id", "name", "cards"}] a new save can start with: the sets with MIN_SET_CARDS cards in packs, newest first."""
    return [entry for entry in packs.pack_sets() if entry["cards"] >= MIN_SET_CARDS]


def saves_of(user):
    """{slot: save} for each of a player's slots, None where it's empty."""
    found = {save.slot: save for save in WorldSave.objects.filter(user=user).select_related("deck")}
    return {slot: found.get(slot) for slot in WorldSave.SLOTS}


def save_in(user, slot):
    return WorldSave.objects.filter(user=user, slot=slot).select_related("deck").first()


def changed(save, *fields):
    """Save these fields, and the version that says something changed. Whatever changed, the quests under way are
    checked again (a card opened, a rank reached, a flag set can each finish an objective)."""
    if quests.advance(save):
        fields = (*fields, "quests")
    save.version += 1
    save.save(update_fields=list(dict.fromkeys([*fields, "version", "played"])))


def start(user, slot, expansion_id, rng=random):
    """A new save in an empty slot: its packs and specialty packs to open, its coins, and an empty deck. Raises
    ValueError saying why it can't."""
    if slot not in WorldSave.SLOTS:
        raise ValueError("There's no such slot.")
    chosen = next((entry for entry in offered_sets() if entry["id"] == expansion_id), None)
    if not chosen:
        raise ValueError(f"Choose a set with at least {MIN_SET_CARDS} cards in its packs.")
    with transaction.atomic():
        if WorldSave.objects.select_for_update().filter(user=user, slot=slot).exists():
            raise ValueError(f"Slot {slot} has a save already.")
        save = WorldSave.objects.create(
            user=user, slot=slot, expansion_id=expansion_id, set_name=chosen["name"], packs=start_packs(), money=start_money(),
            seed=rng.randrange(1, 2 ** 31),
            rewards=[{"key": secrets.token_hex(6), "buff": buff, "source": "Starting loadout"} for buff in loadout()],
        )
        save.deck = CardList.objects.create(user=user, name="Deck 1", world_save=save)
        save.save(update_fields=["deck"])
    return save


def open_packs(save, count, rng=random):
    """Open some of the save's packs, of its set, into its pool. Returns what the pack opening page shows; raises
    ValueError saying why it can't."""
    if not 1 <= count <= save.packs:
        raise ValueError(f"You have {save.packs} pack{'s' if save.packs != 1 else ''} to open.")
    pool = packs.Pool.for_set(save.expansion_id)
    opened = packs.open_packs(pool, count, rng)
    for pack in opened:
        for pull in pack:
            buffs.add_to_pool(save, pull.card.pk, 1)
    save.packs -= count
    save.opened += count
    save.last_opening = {**packs.opening(pool, opened), "set_id": save.expansion_id}
    changed(save, "pool", "packs", "opened", "last_opening")
    return save.last_opening


def claim(save, key, data, rng=random):
    """Claim a specialty pack (or climax pick) with what the player chose (`data`, as posted), as a challenge does.
    Returns True if a pack was opened (to be shown being opened); raises ValueError saying what's wrong."""
    reward = buffs.reward_of(save, key)
    if not reward:
        raise ValueError("That's been claimed already.")
    buff = buffs.BUFFS.get(reward["buff"])
    opened = False
    if buff and buff.claim == "pack":
        pool, expansion_id = buffs.reward_pack(save, buff, data)
        pack = packs.open_pack(pool, rng, packs.BOOSTED_PACK if buff.pack == "lucky" else packs.PACK)
        for pull in pack:
            buffs.add_to_pool(save, pull.card.pk, 1)
        save.last_opening = {**packs.opening(pool, [pack]), "set_id": expansion_id}
        opened = True
    elif buff and buff.claim == "climax":
        pk = buffs.number(data, "card")
        if pk not in {card.pk for card in buffs.climax_choices(save)}:
            raise ValueError("Choose one of the climaxes.")
        buffs.add_to_pool(save, pk, buffs.CLIMAX_COPIES)
    else:
        raise ValueError("That can't be claimed here.")
    save.rewards = [r for r in save.rewards if r["key"] != key]
    changed(save, "pool", "rewards", "last_opening")
    return opened


# ---------------------------------------------------------------- Decks

def decks(save):
    """The save's decks, the equipped one first, then the most recently changed."""
    found = list(save.decks.order_by("-updated", "-pk"))
    return sorted(found, key=lambda deck: deck.pk != save.deck_id)


def deck_in(save, pk):
    """One of the save's decks, or None."""
    return save.decks.filter(pk=pk).first() if str(pk).isdigit() else None


def deck_name(name, save, but=None):
    """A deck's name as given, tidied; raises ValueError if it's empty or another of the save's decks has it."""
    name = " ".join(str(name or "").split())[:DECK_NAME]
    if not name:
        raise ValueError("Give the deck a name.")
    if save.decks.exclude(pk=but.pk if but else None).filter(name__iexact=name).exists():
        raise ValueError(f"You have a deck called “{name}” already.")
    return name


def new_deck(save, name, copy_from=None):
    """Another deck for the save, empty or a copy of one of its decks. Raises ValueError saying why it can't."""
    if save.decks.count() >= MAX_DECKS:
        raise ValueError(f"A save can have {MAX_DECKS} decks: delete one first.")
    deck = CardList.objects.create(user=save.user, name=deck_name(name, save), world_save=save)
    if copy_from:
        CardListEntry.objects.bulk_create(CardListEntry(card_list=deck, card_id=e.card_id, quantity=e.quantity) for e in copy_from.entries.all())
    if not save.deck_id:
        save.deck = deck
        changed(save, "deck")
    return deck


def rename_deck(save, deck, name):
    deck.name = deck_name(name, save, but=deck)
    deck.save(update_fields=["name", "updated"])


def equip(save, deck):
    """Duel with this deck from now on."""
    save.deck = deck
    changed(save, "deck")


def delete_deck(save, deck):
    """Delete one of the save's decks; if it was the equipped one, the next most recent is equipped instead. A save
    keeps at least one deck."""
    if save.decks.count() <= 1:
        raise ValueError("A save keeps at least one deck: empty it instead.")
    was_equipped = deck.pk == save.deck_id
    deck.delete()
    if was_equipped:
        save.deck = save.decks.order_by("-updated", "-pk").first()
        changed(save, "deck")


def deck_pool(save, deck=None):
    """[(card, copies opened, copies in the deck)], in the order a deck lists them: for the equipped deck, or another
    of the save's. Every deck builds from the same cards, so a card can be in several at once."""
    deck = deck or save.deck
    in_deck = dict(deck.entries.values_list("card_id", "quantity")) if deck else {}
    cards = Card.objects.filter(pk__in=[int(pk) for pk in save.pool]).order_by("level", "card_type", "serial_number")
    return [(card, save.pool[str(card.pk)], in_deck.get(card.pk, 0)) for card in cards]


def save_deck(save, copies, deck=None):
    """Make the deck (the equipped one, or another of the save's) exactly these {card id: copies}. Returns what's wrong with them (nothing is saved then), or None.
    Only cards opened, as many copies as opened; at most DECK_SIZE cards and CLIMAX_COUNT climaxes. The rules' 4 copies
    of a card are only warned about while building (the deck builder shows them); duelling checks them (deck_problem)."""
    copies = {int(pk): int(n) for pk, n in copies.items() if int(n) > 0}
    if any(n > save.pool.get(str(pk), 0) for pk, n in copies.items()):
        return "A deck can only have the cards you've opened, as many copies as you opened."
    if sum(copies.values()) > DECK_SIZE:
        return f"A deck has at most {DECK_SIZE} cards."
    cards = Card.objects.in_bulk(copies)
    climaxes = sum(n for pk, n in copies.items() if pk in cards and is_climax(cards[pk]))
    if climaxes > CLIMAX_COUNT:
        return climax_problem(climaxes, CLIMAX_COUNT)
    deck = deck or save.deck
    with transaction.atomic():
        deck.entries.all().delete()
        CardListEntry.objects.bulk_create(CardListEntry(card_list=deck, card_id=pk, quantity=n) for pk, n in copies.items())
        deck.save(update_fields=["updated"])
    changed(save)
    return None


def deck_problem(save, deck=None):
    """What stops a deck (the equipped one, unless another's given) duelling as it is, or None: a full DECK_SIZE
    cards, its climaxes, and no more than COPY_LIMIT of a card by name (unless the card says any number)."""
    deck = deck or save.deck
    if not deck:
        return "No deck is equipped."
    entries = list(deck.entries.select_related("card"))
    total = sum(entry.quantity for entry in entries)
    if total != DECK_SIZE:
        return f"A deck needs {DECK_SIZE} cards; yours has {total}."
    by_name, free = {}, set()
    for entry in entries:
        by_name[entry.card.name] = by_name.get(entry.card.name, 0) + entry.quantity
        if unlimited(entry.card):
            free.add(entry.card.name)
    over = sorted(name for name, n in by_name.items() if n > COPY_LIMIT and name not in free)
    if over:
        return f"A deck can have at most {COPY_LIMIT} copies of a card, not of {', '.join(over)}."
    return unplayable(deck)


def pool_shortfall(save):
    """If the save's cards can't make a legal deck even with every pack opened and claimed, what's missing; else None.
    Counts at most COPY_LIMIT of a card by name, and CLIMAX_COUNT climaxes."""
    if save.packs or save.rewards:
        return None  # there's more to come
    cards = Card.objects.in_bulk([int(pk) for pk in save.pool])
    climaxes, others = 0, {}
    for pk, n in save.pool.items():
        card = cards.get(int(pk))
        if not card:
            continue
        if is_climax(card):
            climaxes += n
        else:
            others[card.name] = others.get(card.name, 0) + (n if unlimited(card) else min(n, COPY_LIMIT))
    usable = min(climaxes, CLIMAX_COUNT) + min(sum(others.values()), DECK_SIZE - CLIMAX_COUNT)
    if climaxes < CLIMAX_COUNT:
        return f"Your cards have {climaxes} climax{'es' if climaxes != 1 else ''}, and a deck needs {CLIMAX_COUNT}."
    if usable < DECK_SIZE:
        return f"Your cards make at most {usable} of a deck's {DECK_SIZE} (counting {COPY_LIMIT} copies of a card)."
    return None


def step(save):
    """Where the save is on its way into the world: "packs" (some to open or claim), "deck" (the equipped one to
    build), or "ready"."""
    if save.packs or save.rewards:
        return "packs"
    if deck_problem(save):
        return "deck"
    return "ready"


# ---------------------------------------------------------------- Places and time

def places(save):
    """The places this save can go, in map order: those open from the start, and those whose flag it has."""
    return [place for place in WorldPlace.objects.all() if not place.unlock_flag or has_flag(save, place.unlock_flag)]


def place_of(save, known=None):
    """Where the save is: its place, or the first on the map if it hasn't one (a new save) or can't be there now."""
    known = known if known is not None else places(save)
    return next((place for place in known if place.key == save.place), known[0] if known else None)


THIS_TIME = ("this morning", "this afternoon", "this evening", "tonight")  # "You've spent this morning here"


def this_time(save):
    return THIS_TIME[save.turn % len(WorldSave.TIMES)]


def engaged(save):
    """Whether the player has spent this time of day with someone where they are (talked, given a gift, a quest, a
    duel): they stay till it passes. The shop doesn't count."""
    return save.today.get("engaged") == save.turn


def engage(save):
    save.today["engaged"] = save.turn


def test_mode(save):
    """Staff testing: time can be passed whenever (the staff Wait) and travel is free, so schedules and quests can be
    checked quickly. Off, staff play by the same rules as everyone."""
    return bool(save.flags.get("test_mode")) and save.user.is_staff


def set_test_mode(save, on):
    if not save.user.is_staff:
        raise ValueError("Test mode is for staff.")
    save.flags["test_mode"] = bool(on)
    changed(save, "flags")


def choosing(save):
    """Whether time has just passed and the player hasn't yet chosen where to spend the new time of day (the map, which
    has to be answered: staying where they are is a choice too). Nobody can be talked to or duelled till then."""
    return save.flags.get("choose") == save.turn and not test_mode(save)


def time_passed(save):
    """A new time of day (waited, or a duel's over): a new day clears what was done today, visits are checked, and
    the player chooses where to go next."""
    save.turn += 1
    if save.turn % len(WorldSave.TIMES) == 0:
        save.today = {}
    save.flags["choose"] = save.turn
    quests.arrived(save)


def anyone_out(save):
    return bool(whereabouts(save))


def can_wait(save):
    """(whether time can be passed now, why not): once the player's spent the time with someone, or if there's nobody
    in town to spend it with. Not while a duel's under way."""
    if live_duel(save):
        return False, "You're in a duel: finish it first."
    if engaged(save) or not anyone_out(save):
        return True, ""
    return False, "Spend this time with someone first: talk, give a gift or duel. Or travel to find someone."


def travel(save, key):
    """Go to a place (or stay where the player is, answering the map after time passes): free, until the player
    spends the time with someone (engaged), and then not until it passes. Raises ValueError if they can't go there."""
    place = next((place for place in places(save) if place.key == key), None)
    if not place:
        raise ValueError("You can't go there.")
    if engaged(save) and place.key != save.place and not test_mode(save):
        raise ValueError(f"You've spent {this_time(save)} here: pass time before you go somewhere else.")
    chose = save.flags.pop("choose", None) is not None
    if place.key != save.place:
        save.place = place.key
        quests.arrived(save)
        changed(save, "place", "quests", "flags")
    elif chose:
        changed(save, "flags")
    return place


def wait(save, staff=False):
    """Let time pass to the next part of the day; after night comes a new day, and what was done today is forgotten.
    Only once the time's been spent with someone (can_wait), and not while a duel's under way; `staff`: the test
    mode's Wait, any time."""
    allowed, why = can_wait(save)
    if staff and test_mode(save):
        allowed, why = (False, "You're in a duel: finish it first.") if live_duel(save) else (True, "")
    if not allowed:
        raise ValueError(why)
    time_passed(save)
    changed(save, "turn", "today", "quests", "flags")


# ---------------------------------------------------------------- Who's where (see CpuSchedule)

MAX_PER_PLACE = 2  # CPUs at one place at once
MAX_ON_STAGE = 10  # CPUs out in the whole town at once
MIN_ON_STAGE = 6  # the fewest a time of day draws, when there are CPUs enough
SEEN_AGAIN = 0.35  # how much less likely a CPU is to turn up again, for each time it's been out already that day


def haunts():
    """{cpu id: [its haunts]} for every CPU that can duel (finalized, with a deck)."""
    by_cpu = {}
    for rule in CpuSchedule.objects.filter(cpu__finalized=True, cpu__deck__isnull=False).select_related("place").order_by("cpu_id", "pk"):
        by_cpu.setdefault(rule.cpu_id, []).append(rule)
    return by_cpu


def day_cast(save, day, by_cpu=None):
    """[{cpu id: the haunt it's at} for each time of day 0 to 3]: who's out on this day (counting from 0), drawn fresh
    for each save and day from the seed, so a reload never moves anyone. For each time, CPUs whose haunts fit the
    weekday and time are shuffled, the heavier first and those out already today less likely, and placed until the
    time's draw (MIN_ON_STAGE to MAX_ON_STAGE) is out, never more than MAX_PER_PLACE at a place. A once-a-day haunt is
    used once at most. Rank-gated haunts are drawn like the rest (whereabouts leaves those out), so getting to know one
    CPU never moves another."""
    by_cpu = haunts() if by_cpu is None else by_cpu
    rng = random.Random(f"{save.seed}:{day}:cast")
    weekday = day % 7
    seen, used_once, plan = Counter(), set(), []
    for time in range(len(WorldSave.TIMES)):
        options = {}
        for cpu_id in sorted(by_cpu):
            fits = [rule for rule in by_cpu[cpu_id] if weekday in rule.days and time in rule.times and rule.pk not in used_once]
            if fits:
                options[cpu_id] = fits
        wanted = min(rng.randint(MIN_ON_STAGE, MAX_ON_STAGE), len(options))
        # A weighted shuffle (each a random key, raised to 1 / its weight): the heaviest tend to come first.
        order = sorted(((rng.random() ** (1 / max(sum(rule.weight for rule in fits) * SEEN_AGAIN ** seen[cpu_id], 0.01)), cpu_id)
                        for cpu_id, fits in options.items()), reverse=True)
        filled, cast = Counter(), {}
        for _, cpu_id in order:
            if len(cast) >= wanted:
                break
            free = [rule for rule in options[cpu_id] if filled[rule.place_id] < MAX_PER_PLACE]
            if not free:
                continue
            rule = rng.choices(free, weights=[max(rule.weight, 1) for rule in free])[0]
            cast[cpu_id] = rule
            filled[rule.place_id] += 1
            seen[cpu_id] += 1
            if rule.once_per_day:
                used_once.add(rule.pk)
        plan.append(cast)
    return plan


def whereabouts(save, turn=None):
    """{cpu id: the haunt it's at} now (or at this turn): the day's draw (day_cast), less any CPU there by a haunt the
    player doesn't know it well enough for yet, and any a quest sent away."""
    turn = save.turn if turn is None else turn
    cast = day_cast(save, turn // len(WorldSave.TIMES))[turn % len(WorldSave.TIMES)]
    away = quests.gone(save)  # sent away for good by a quest's ending: the day's draw keeps their place empty
    return {cpu_id: rule for cpu_id, rule in cast.items()
            if cpu_id not in away and (not rule.min_rank or rank_of(save, cpu_id) >= rule.min_rank)}


def starter_rules(cpu_id, places, usage, villain=False, secluded=()):
    """First haunts for one CPU, as CpuSchedule fields, rolled from the CPU so they're the same every time. Most CPUs
    get a home most weekdays, a weekend spot and somewhere to wander, each at whichever of `places` (keys) has the
    fewest haunts so far (`usage`, updated here), so CPUs spread across the town. A villain keeps to the `secluded`
    places, mostly at evening and night, and turns up somewhere busy by day only once the player's a friend."""
    rng = random.Random(cpu_id * 7919)

    def pick(among, but=()):
        choices = [key for key in among if key not in but] or list(among)
        least = min(usage.get(key, 0) for key in choices)
        key = rng.choice([key for key in choices if usage.get(key, 0) == least])
        usage[key] = usage.get(key, 0) + 1
        return key

    if villain and secluded:
        lair = pick(secluded)
        prowl = pick(secluded, (lair,))
        daytime = pick([key for key in places if key not in secluded] or places)
        return [
            {"place": lair, "days": sorted(rng.sample(range(7), 5)), "times": [2, 3], "weight": 70},
            {"place": prowl, "days": sorted(rng.sample(range(7), 3)), "times": [3], "weight": 50},
            {"place": daytime, "days": sorted(rng.sample(range(7), 3)), "times": [rng.choice((0, 1))], "weight": 30, "min_rank": 2},
        ]
    open_places = [key for key in places if key not in secluded] or list(places)
    home = pick(open_places)
    weekend = pick(open_places, (home,))
    wander = pick(places, (home, weekend))
    return [
        {"place": home, "days": [0, 1, 2, 3, 4], "times": sorted(rng.sample(range(4), 2)), "weight": 60},
        {"place": weekend, "days": [5, 6], "times": sorted(rng.sample(range(4), rng.randint(1, 2))), "weight": 50},
        {"place": wander, "days": sorted(rng.sample(range(7), 3)), "times": [rng.randrange(4)], "weight": 30},
    ]


def starter_schedules(cpus=None):
    """First haunts (starter_rules) for each CPU that can duel and has none, or for these CPUs; staff edit them from
    there. Returns how many CPUs got some."""
    places = {place.key: place for place in WorldPlace.objects.filter(shop=False)}
    if not places:
        return 0
    secluded = sorted(key for key, place in places.items() if place.secluded)
    usage = {}
    for rule in CpuSchedule.objects.select_related("place"):
        usage[rule.place.key] = usage.get(rule.place.key, 0) + 1
    found = CpuProfile.objects.filter(finalized=True, deck__isnull=False, schedule__isnull=True).order_by("pk")
    if cpus is not None:
        found = found.filter(pk__in=[cpu.pk for cpu in cpus])
    made = 0
    for cpu in found:
        for rule in starter_rules(cpu.pk, sorted(places), usage, villain=cpu.temperament == "villain", secluded=secluded):
            CpuSchedule.objects.create(cpu=cpu, **{**rule, "place": places[rule["place"]]})
        made += 1
    return made


def present(save, place_key=None, found=None):
    """[(cpu, rule)] at a place (the save's, unless another's given) now, by name. `found` is whereabouts(save), if
    it's been worked out already."""
    place_key = place_key or (place_of(save).key if place_of(save) else "")
    found = whereabouts(save) if found is None else found
    here = {cpu_id: rule for cpu_id, rule in found.items() if rule.place.key == place_key}
    cpus = CpuProfile.objects.filter(pk__in=here).select_related("image", "intro_image", "player_win_image", "player_lose_image").order_by("name")
    return [(cpu, here[cpu.pk]) for cpu in cpus]


def cpu_portraits(cpu):
    """How a CPU's drawn standing in a place: its uploaded pictures (pleased and dismayed being the ones shown when the
    player loses and wins), or else the card its circle picture is cut from."""
    if cpu.image_id:
        return {"kind": "art", "main": cpu.screen_url("main"), "pleased": cpu.screen_url("lose"), "dismayed": cpu.screen_url("win")}
    if cpu.avatar:
        image = reverse("weiss:card_image", args=[cpu.avatar_card_id])
        return {"kind": "card", "main": image, "pleased": image, "dismayed": image}
    return {"kind": "none"}


# ---------------------------------------------------------------- Duels

STAKE_PRIZE = 2  # a high-stakes win pays its entry fee back this many times over


def payouts():
    found = settings()
    return (found.win_payout, found.first_win_bonus) if found else (200, 100)


def live_duel(save):
    """The save's duel that's under way (a game not yet over), or None: time can't move on until it's done."""
    for room in GameRoom.objects.filter(world_save=save, status=GameRoom.Status.PLAYING).order_by("-pk")[:3]:
        if not room.state.get("game_over"):
            return room
    return None


def start_duel(save, cpu_id, high_stakes=False):
    """A duel with a CPU that's here now, with the equipped deck: a game against it, made with play.seat_cpu. A
    high-stakes one's entry fee is taken now and isn't given back. Raises ValueError saying why it can't."""
    from .play import seat_cpu  # weiss.play uses this module

    if live_duel(save):
        raise ValueError("Finish the duel you're in first.")
    if choosing(save):
        raise ValueError("Time has moved on: choose where to go first.")
    if (problem := deck_problem(save)):
        raise ValueError(f"Your equipped deck can't duel yet: {problem[0].lower()}{problem[1:]}")
    found = next(((cpu, rule) for cpu, rule in present(save) if str(cpu.pk) == str(cpu_id)), None)
    if not found:
        raise ValueError("They aren't here now.")
    cpu, rule = found
    offered = offered_stake(save, cpu.pk)
    fee = (offered or stake_with(save, cpu.pk, rule)) if high_stakes else 0
    if high_stakes and not fee:
        raise ValueError(f"{cpu.name} isn't playing for stakes here.")
    if GameRoom.objects.filter(host=save.user).count() >= GameRoom.MAX_OPEN_ROOMS:
        raise ValueError(f"You have {GameRoom.MAX_OPEN_ROOMS} game rooms open: delete an old one under Play first.")
    if fee > save.money:
        raise ValueError(f"The entry fee is {fee} coins, and you have {save.money}.")
    save.money -= fee
    room = GameRoom(host=save.user, host_deck=save.deck, status=GameRoom.Status.PLAYING, world_save=save, world_stake=fee)
    seat_cpu(room, cpu)
    room.save()
    quests.duel_started(save, room)
    engage(save)
    changed(save, "money", "quests", "today")
    return room


def game_finished(room, over):
    """A world duel's game is over (`over`, its game_over): a win pays (the duel's payout, the day's first win's bonus
    and a high-stakes prize), and win or lose, the time slot's used up. What happened waits on the save
    (flags["last_duel"]) for the town to say. Once per game."""
    with transaction.atomic():
        save = WorldSave.objects.select_for_update().filter(pk=room.world_save_id).first()
        if not save or (save.flags.get("last_duel") or {}).get("room") == room.pk:
            return
        won = over["winner"] == str(room.host_id)
        payout, bonus = payouts()
        first = won and not save.today.get("won")
        coins = (payout + (bonus if first else 0) + room.world_stake * STAKE_PRIZE) if won else 0
        save.money += coins
        if won:
            save.today["won"] = True
        save.today.setdefault("duelled", []).append(room.cpu_profile_id)
        cpu = CpuProfile.objects.filter(pk=room.cpu_profile_id).first()
        points = gain(cpu, WIN_POINTS if won else LOSS_POINTS) if cpu else 0
        before, after = add_points(save, cpu.pk, points) if cpu else (0, 0)
        rewards = [text for text, _ in reward_ranks(save, cpu, after)] if cpu and after > before else []
        rank_line, scene = "", ""
        if cpu and after > before:  # what reaching the rank plays: its line in the result, or its scene to watch
            found = chatter.pick(cpu, "rank_up", after)
            if found and found[2]:
                save.flags["scene"] = {"scene": found[2].pk, "cpu": cpu.pk}
                scene = reverse("weiss:world_scene", args=[save.slot])
            elif found:
                rank_line = next((filler(save, cpu)(step["text"]) for step in found[1]["steps"] if step["do"] == "say"), "")
        save.flags["last_duel"] = {"room": room.pk, "cpu": room.cpu_name, "cpu_id": room.cpu_profile_id, "won": won, "coins": coins,
                                   "first": first, "stake": room.world_stake, "seen": False, "points": points,
                                   "rank_up": rank_names()[after] if after > before else "", "rank_line": rank_line, "scene": scene,
                                   "rewards": rewards,
                                   # When it started, for the town's time-passing to go from.
                                   "before": {"time": save.turn % len(WorldSave.TIMES), "label": f"{save.weekday} {save.time_of_day.lower()}",
                                              "day": save.day}}
        quests.duel_finished(save, room, won)
        time_passed(save)
        changed(save, "money", "today", "flags", "turn", "relations", "pool", "gifts", "last_opening", "quests")


def duel_result(save):
    """The last duel's result, if the player hasn't seen it in the town yet: marked seen now."""
    result = save.flags.get("last_duel")
    if not result or result.get("seen"):
        return None
    result["seen"] = True
    save.save(update_fields=["flags"])
    cpu = CpuProfile.objects.filter(pk=result.get("cpu_id")).first()
    if cpu:
        result["line"] = chatter.first_line(cpu, "after_win" if result["won"] else "after_loss", rank_of(save, cpu.pk), filler(save, cpu))
    return result


# ---------------------------------------------------------------- The card shop

SHOP_SETS = 4  # sets on the shelves each day: the save's own, and others


def pack_price():
    found = settings()
    return found.pack_price if found else 300


def shop_stock(save):
    """[{"id", "name"}] the shop sells today: the save's set always, and others that change each day (from the seed)."""
    others = [entry for entry in offered_sets() if entry["id"] != save.expansion_id]
    rng = random.Random(f"{save.seed}:{save.turn // 4}:shop")
    picked = rng.sample(others, min(SHOP_SETS - 1, len(others)))
    return [{"id": save.expansion_id, "name": save.set_name}] + [{"id": e["id"], "name": e["name"]} for e in picked]


SHOP_SPECIALS = ("lucky_pack", "climax_pack", "level_pack", "color_pack")  # specialty packs the counter sells (weiss.buffs)
SHOP_CARDS = 10  # single cards on offer each day: rares and better, from the day's sets
SPECIALTY_PRICE = 600  # until staff set the prices (WorldSettings)
CARD_PRICE = 3000


def specialty_price():
    found = settings()
    return found.specialty_price if found else SPECIALTY_PRICE


def card_price():
    found = settings()
    return found.card_price if found else CARD_PRICE


def set_cover(expansion_id):
    """A set's cover card, as the set list has it: the lowest number of its main print run (so a promo packed into the
    set isn't its cover). None for a set with no cards."""
    serials = dict(Card.objects.filter(expansion_id=expansion_id).values_list("serial_number", "pk"))
    if not serials:
        return None
    main = Counter(serial.split("-", 1)[0] for serial in serials).most_common(1)[0][0]
    return serials[min(serial for serial in serials if serial.split("-", 1)[0] == main)]


def shop_cards(save):
    """The single cards on offer today: SHOP_CARDS of the rares and better (packs.grade_of 1 up) of the day's sets,
    picked from the seed, rarest first."""
    stocked = [entry["id"] for entry in shop_stock(save)]
    cards = [card for card in Card.objects.filter(expansion_id__in=stocked).order_by("serial_number")
             if packs.rarity_of(card) not in packs.NOT_IN_PACKS and packs.grade_of(packs.rarity_of(card)) >= 1]
    rng = random.Random(f"{save.seed}:{save.turn // 4}:cards")
    picked = rng.sample(cards, min(SHOP_CARDS, len(cards)))
    return sorted(picked, key=lambda card: (-packs.grade_of(packs.rarity_of(card)), card.serial_number))


def buy_card(save, card_id):
    """Buy one of the day's single cards: a copy goes in the save's cards. One of each a day. Raises ValueError."""
    here = place_of(save)
    if not here or not here.shop:
        raise ValueError("You need to be at the card shop.")
    card = next((card for card in shop_cards(save) if str(card.pk) == str(card_id)), None)
    if not card:
        raise ValueError("The shop doesn't have that card today.")
    if card.pk in save.today.get("bought_cards", []):
        raise ValueError(f"You've bought today's {card.name} already.")
    price = card_price()
    if price > save.money:
        raise ValueError(f"{card.name} costs {price} coins, and you have {save.money}.")
    save.money -= price
    buffs.add_to_pool(save, card.pk, 1)
    save.today.setdefault("bought_cards", []).append(card.pk)
    changed(save, "money", "pool", "today")
    return card


def buy_specialty(save, buff_id, data, rng=random):
    """Buy a specialty pack (SHOP_SPECIALS) of one of the day's sets, with its level or color as chosen (`data`, as
    posted), and open it into the save's cards. Raises ValueError saying why it can't."""
    here = place_of(save)
    if not here or not here.shop:
        raise ValueError("You need to be at the card shop.")
    if buff_id not in SHOP_SPECIALS:
        raise ValueError("The shop doesn't sell that.")
    buff = buffs.BUFFS[buff_id]
    price = specialty_price()
    if price > save.money:
        raise ValueError(f"A {buff.name.lower()} costs {price} coins, and you have {save.money}.")
    # weiss.buffs builds the pack, from the sets it's told this "run" has: the day's shelves.
    pool, expansion_id = buffs.reward_pack(SimpleNamespace(sets=[entry["id"] for entry in shop_stock(save)]), buff, data)
    pack = packs.open_pack(pool, rng, packs.BOOSTED_PACK if buff.pack == "lucky" else packs.PACK)
    for pull in pack:
        buffs.add_to_pool(save, pull.card.pk, 1)
    save.money -= price
    save.last_opening = {**packs.opening(pool, [pack]), "set_id": expansion_id, "bought": True}
    changed(save, "money", "pool", "last_opening")
    return save.last_opening


def shop(save):
    """The card shop's counter as the town shows it: today's sets (with their covers), the specialty packs, and the
    single cards (with their pictures, and whether they're bought today)."""
    stock = shop_stock(save)
    bought = set(save.today.get("bought_cards", []))
    cover = lambda expansion_id: (pk := set_cover(expansion_id)) and reverse("weiss:card_image", args=[pk])
    return {
        "price": pack_price(), "specialty_price": specialty_price(), "card_price": card_price(),
        "stock": [{**entry, "cover": cover(entry["id"])} for entry in stock],
        "specials": [{"key": key, "name": buffs.BUFFS[key].name, "about": buffs.BUFFS[key].description,
                      "asks": buffs.BUFFS[key].pack if buffs.BUFFS[key].pack in ("level", "color") else ""} for key in SHOP_SPECIALS],
        "levels": list(buffs.LEVELS), "colors": list(buffs.COLORS),
        "gifts": inventory(save),
        "cards": [{"id": card.pk, "name": card.name, "rarity": packs.rarity_of(card), "set": card.expansion,
                   "image": reverse("weiss:card_image", args=[card.pk]), "url": reverse("weiss:card", args=[card.pk]), "popup": reverse("weiss:card_popup", args=[card.pk]),
                   "sold": card.pk in bought} for card in shop_cards(save)],
    }


def buy_packs(save, expansion_id, count, rng=random):
    """Buy packs at the shop (where the save is) and open them into its cards. Raises ValueError saying why it can't."""
    here = place_of(save)
    if not here or not here.shop:
        raise ValueError("You need to be at the card shop.")
    if expansion_id not in {entry["id"] for entry in shop_stock(save)}:
        raise ValueError("The shop doesn't have that set today.")
    if not 1 <= count <= 10:
        raise ValueError("Buy 1 to 10 packs at a time.")
    cost = pack_price() * count
    if cost > save.money:
        raise ValueError(f"{count} pack{'s' if count != 1 else ''} cost {cost} coins, and you have {save.money}.")
    pool = packs.Pool.for_set(expansion_id)
    if not pool:
        raise ValueError("That set has no packs.")
    opened = packs.open_packs(pool, count, rng)
    for pack in opened:
        for pull in pack:
            buffs.add_to_pool(save, pull.card.pk, 1)
    save.money -= cost
    save.last_opening = {**packs.opening(pool, opened), "set_id": expansion_id, "bought": True}
    changed(save, "pool", "money", "last_opening")
    return save.last_opening


# ---------------------------------------------------------------- Friendship (save.relations)

TALK_POINTS = 3  # the first talk of the day with someone
WIN_POINTS = 6
LOSS_POINTS = 2
GIFT_POINTS = {"loved": 12, "liked": 6, "neutral": 2, "disliked": -4}
GIFTS_PER_DAY = 1  # gifts to each CPU a day
GAIN = {"warm": 1.5, "friendly": 1.25, "neutral": 1.0, "aloof": 0.75, "villain": 0.6}  # by temperament: talk, gifts and duels
MAX_GIFTS = 99  # of each item held
RESERVED_FLAGS = {"last_duel", "set", "scene", "choose", "test_mode"}
TALK_FIELDS = ("relations", "today", "flags", "money", "gifts", "pool", "last_opening", "quests")  # what talking can change


def ranks():
    """[{name, points}] from the first rank, as staff set them (sorted, the first at 0 points)."""
    found = settings()
    rows = [row for row in (found.ranks if found else default_ranks()) if isinstance(row, dict) and row.get("name")]
    rows = sorted(rows, key=lambda row: int(row.get("points") or 0)) or default_ranks()
    return [{"name": str(row["name"]), "points": 0 if i == 0 else int(row.get("points") or 0)} for i, row in enumerate(rows)]


def rank_names():
    return [row["name"] for row in ranks()]


def relation(save, cpu_id):
    """How things stand with a CPU: {points, talked (the day), gifted (the day)}, made if new."""
    return save.relations.setdefault(str(cpu_id), {"points": 0})


def rank_for(points):
    return max(i for i, row in enumerate(ranks()) if points >= row["points"])


def rank_of(save, cpu_id):
    """The rank with a CPU: by points, but never past a gate quest that isn't done (quests.cap)."""
    rank = rank_for(save.relations.get(str(cpu_id), {}).get("points", 0))
    held = quests.cap(save, cpu_id)
    return rank if held is None else min(rank, held)


def gain(cpu, n):
    """The points a talk, gift or duel brings with this CPU (`cpu`, or its id): more for a warm one, fewer for an aloof
    one or a villain. Losing points isn't softened or sharpened, nor are a script's own."""
    if n <= 0:
        return n
    temperament = cpu.temperament if hasattr(cpu, "temperament") else \
        CpuProfile.objects.filter(pk=cpu).values_list("temperament", flat=True).first()
    return max(1, round(n * GAIN.get(temperament, 1.0)))


def add_points(save, cpu_id, n):
    """Change how much a CPU likes the player (never below 0): (rank before, rank after)."""
    rel = relation(save, cpu_id)
    before = rank_of(save, cpu_id)
    rel["points"] = max(0, rel["points"] + n)
    return before, rank_of(save, cpu_id)


def standing(save, cpu_id):
    """A CPU's friendship as the town shows it: rank (number and name), ranks there are, points, points the next rank
    takes (None at the top), and whether they've been talked to and given a gift today."""
    rel = save.relations.get(str(cpu_id), {})
    points, rows = rel.get("points", 0), ranks()
    rank = rank_of(save, cpu_id)
    found = {"rank": rank, "name": rows[rank]["name"], "ranks": len(rows), "points": points,
             "next": rows[rank + 1]["points"] if rank + 1 < len(rows) else None,
             "talked": rel.get("talked") == save.day, "gifted": rel.get("gifted") == save.day,
             "next_rewards": rewards_for(rank + 1) if rank + 1 < len(rows) else []}
    gate = quests.gate_quest(save, cpu_id)
    if gate and found["next"] is not None:  # the next rank waits for a quest: say which, and how it stands
        found["gate"] = {"title": gate.title, "status": quests.status(save, gate.key) or ("offered" if quests.offerable(save, gate) else ""),
                         "ready": points >= found["next"]}
    return found


def has_flag(save, name):
    return name in save.flags.get("set", []) or bool(save.flags.get(name))


def filler(save, cpu):
    """Fills in a line's {player}, {name} and {rank}."""
    values = {"player": save.user.username, "name": cpu.name}

    def fill(text):
        values["rank"] = rank_names()[rank_of(save, cpu.pk)]
        return re.sub(r"\{(player|name|rank)\}", lambda m: values[m[1]], text)
    return fill


class Talk:
    """What a chatter script does to the save, for chatter.play: points, coins and gifts (once a day for each line, so
    talking again can't farm them), flags, and the events the box shows for them."""

    def __init__(self, save, cpu, key):
        self.save, self.cpu, self.key = save, cpu, key
        self.fill = filler(save, cpu)
        self.ranked_up = None  # the rank reached, if one was

    def once(self, at):
        done = self.save.today.setdefault("paid", [])
        mark = f"{self.cpu.pk}:{self.key}:{at}"
        if mark in done:
            return False
        done.append(mark)
        return True

    def rank(self):
        return rank_of(self.save, self.cpu.pk)

    def flag(self, name):
        return has_flag(self.save, name)

    def set_flag(self, name, on):
        if name in RESERVED_FLAGS:
            return
        held = [flag for flag in self.save.flags.get("set", []) if flag != name]
        self.save.flags["set"] = held + [name] if on else held

    def points(self, n, at=None):
        if at is not None and not self.once(at):
            return []
        before, after = add_points(self.save, self.cpu.pk, n)
        if after > before:
            self.ranked_up = after
        events = [{"points": n, "relation": standing(self.save, self.cpu.pk), "rank_up": rank_names()[after] if after > before else ""}]
        return events + [{"reward": text, **({"link": link} if link else {})} for text, link in reward_ranks(self.save, self.cpu, after)]

    def money(self, n, at):
        if not self.once(at):
            return []
        self.save.money += n
        return [{"money": n}]

    def gift(self, key, at):
        item = GiftItem.objects.filter(key=key).first()
        if not item or not self.once(at):
            return []
        self.save.gifts[key] = min(self.save.gifts.get(key, 0) + 1, MAX_GIFTS)
        return [{"gift": item.name, "icon": item.icon}]


# ---------------------------------------------------------------- What reaching a rank brings

# By rank reached (1 the first after Stranger): what it gives. Cards come from the CPU's own deck: "signature" a rare
# from its lower levels, "ace" its highest-level card, "anchors" the cards its deck is built around (with its climax).
# Packs are opened from the CPU's own set straight away. "stakes" lets the player duel it for that fee wherever it is.
# Every rank reached also counts for card sleeves ("world_rank").
RANK_REWARDS = {
    1: [("coins", 200), ("gift", "loved")],
    2: [("cards", "signature"), ("pack", "climax_pack")],
    3: [("pack", "color_pack"), ("coins", 400)],
    4: [("stakes", 500), ("cards", "ace")],
    5: [("cards", "anchors"), ("pack", "lucky_pack"), ("coins", 1000)],
}
REWARD_COPIES = 2


def deck_cards(cpu):
    """[(card, copies)] in the CPU's deck."""
    if not cpu.deck_id:
        return []
    return [(entry.card, entry.quantity) for entry in CardListEntry.objects.filter(card_list_id=cpu.deck_id).select_related("card")]


def signature_cards(cpu, which):
    """The cards of the CPU's deck a reward gives: [card]."""
    cards = deck_cards(cpu)
    if not cards:
        return []
    anchors = set((cpu.deck.express or {}).get("anchors", ())) if cpu.deck_id else set()
    climaxes = [(card, n) for card, n in cards if is_climax(card)]
    characters = [card for card, _ in cards if not is_climax(card) and card.pk not in anchors]
    grade = lambda card: packs.grade_of(packs.rarity_of(card))
    if which == "anchors":
        chosen = [card for card, _ in cards if card.pk in anchors]
        if not chosen:  # a deck express didn't build: its cx combo cards
            from . import abilities
            chosen = [card for card, _ in cards if not is_climax(card) and abilities.has_combo(card.description)][:2]
        top_climax = max(climaxes, key=lambda pair: (pair[1], pair[0].serial_number), default=None)
        return chosen + ([top_climax[0]] if top_climax else [])
    if which == "ace":
        pool = sorted(characters, key=lambda card: (-(card.level or 0), -grade(card), card.serial_number))
        return pool[:1]
    pool = sorted([card for card in characters if (card.level or 0) <= 2] or characters,
                  key=lambda card: (-grade(card), -(card.level or 0), card.serial_number))
    return pool[:1]


def cpu_set(cpu):
    """The set most of the CPU's deck comes from, and its main color: (expansion id, color), or (None, None)."""
    cards = deck_cards(cpu)
    sets, colors = Counter(), Counter()
    for card, n in cards:
        if card.expansion_id:
            sets[card.expansion_id] += n
        if card.color and not is_climax(card):
            colors[card.color] += n
    return (sets.most_common(1)[0][0] if sets else None), (colors.most_common(1)[0][0] if colors else None)


def give_reward(save, cpu, kind, what, rng=random):
    """Give one reward: (what it says, a link to see it or ""), or None if there's nothing to give."""
    if kind == "coins":
        save.money += what
        return f"{what:,} coins", ""
    if kind == "gift":
        loved = set((cpu.gift_tastes or {}).get("loves", []))
        items = list(GiftItem.objects.filter(staff_only=False))  # never the staff token
        item = next((item for item in items if loved & set(item.tags or [])), None) or (rng.choice(items) if items else None)
        if not item:
            return None
        save.gifts[item.key] = min(save.gifts.get(item.key, 0) + 1, MAX_GIFTS)
        return f"{item.icon} {item.name}".strip(), ""
    if kind == "cards":
        cards = signature_cards(cpu, what)
        for card in cards:
            buffs.add_to_pool(save, card.pk, REWARD_COPIES)
        return (f"{', '.join(card.name for card in cards)} ×{REWARD_COPIES}", "") if cards else None
    if kind == "pack":
        expansion_id, color = cpu_set(cpu)
        if not expansion_id:
            return None
        buff = buffs.BUFFS[what]
        try:
            pool, _ = buffs.reward_pack(SimpleNamespace(sets=[expansion_id]), buff, {"set": str(expansion_id), "color": color or ""})
        except ValueError:
            pool = packs.Pool.for_set(expansion_id)  # their set has no cards like that: a plain pack of it
            if not pool:
                return None
        pack = packs.open_pack(pool, rng, packs.BOOSTED_PACK if buff.pack == "lucky" else packs.PACK)
        for pull in pack:
            buffs.add_to_pool(save, pull.card.pk, 1)
        reward_opening(save, pool, pack, expansion_id)
        return f"A {buff.name.lower()} of {pool.set_name}", reverse("weiss:world_opened", args=[save.slot])
    if kind == "stakes":
        relation(save, cpu.pk)["stakes"] = what
        return f"High-stakes duels with {cpu.name}, for {what:,} coins", ""
    return None


def reward_opening(save, pool, pack, expansion_id):
    """A pack a reward opened, for the reveal: every pack given in one go (a quest's, then its rank's) is revealed
    together, so "See the cards" shows them all, not only the last."""
    opened = packs.opening(pool, [pack])
    if getattr(save, "_rewards_opened", False) and save.last_opening.get("packs"):
        merged = save.last_opening
        merged["packs"] += opened["packs"]
        if merged.get("set") != opened["set"]:
            merged["set"] = "your rewards"
    else:
        save.last_opening = {**opened, "set_id": expansion_id, "bought": True}
        save._rewards_opened = True


def reward_ranks(save, cpu, rank):
    """Give what every rank up to this one brings that this save hasn't had from this CPU yet: [(text, link)]. Each
    rank's rewards come once, whatever brought the rank; the sleeves' world_rank progress is counted too."""
    rel = relation(save, cpu.pk)
    given = []
    for reached in range(rel.get("rewarded", 0) + 1, rank + 1):
        for kind, what in RANK_REWARDS.get(reached, []):
            if (found := give_reward(save, cpu, kind, what)):
                given.append(found)
        rel["rewarded"] = reached
    if rank > 0:
        from . import sleeves
        sleeves.record(save.user_id, bests={"world_rank": rank, f"world_rank:{cpu.pk}": rank})
    return given


def rewards_for(rank):
    """What reaching a rank brings, as the town tells the player before they get there."""
    words = {"coins": lambda n: f"{n:,} coins", "gift": lambda _: "a gift", "pack": lambda b: f"a {buffs.BUFFS[b].name.lower()}",
             "stakes": lambda n: "high-stakes duels", "cards": lambda which: {"signature": "a signature card", "ace": "their ace card",
                                                                               "anchors": "their key cards"}[which]}
    return [words[kind](what) for kind, what in RANK_REWARDS.get(rank, [])]


def stake_with(save, cpu_id, rule=None):
    """The entry fee for a high-stakes duel with this CPU now: its haunt's, or the one earned with it, whichever's more."""
    return max(rule.stake if rule else 0, save.relations.get(str(cpu_id), {}).get("stakes", 0))


def someone_here(save, cpu_id):
    """The CPU (here now) the player's acting on. Raises ValueError if they aren't, or if the player has yet to choose
    where to spend this time of day."""
    if choosing(save):
        raise ValueError("Time has moved on: choose where to go first.")
    cpu = next((cpu for cpu, _ in present(save) if str(cpu.pk) == str(cpu_id)), None)
    if not cpu:
        raise ValueError("They aren't here now.")
    return cpu


def offered_stake(save, cpu_id):
    """The entry fee a CPU offered in talk today ("fight stake …"), or 0."""
    talk = save.today.get("talk") or {}
    return talk.get("stake", 0) if talk.get("cpu") == cpu_id else 0


def converse(save, cpu, context, after=()):
    """Start one of a CPU's lines for this context, and run it till it needs the player. `after` are events to show
    once it's said (the points a talk or gift brought). What the town gets: {"talk": {...}} (see carry_on)."""
    found = chatter.pick(cpu, context, rank_of(save, cpu.pk))
    key, compiled, _ = found if found else ("default:none", {"labels": {}, "steps": []}, None)
    save.today["talk"] = {"cpu": cpu.pk, "chatter": key, "at": None, "stake": offered_stake(save, cpu.pk)}
    return carry_on(save, cpu, compiled, 0, list(after))


def carry_on(save, cpu, compiled, start, after=()):
    talk = save.today["talk"]
    world = Talk(save, cpu, talk["chatter"])
    events, waiting = chatter.play(compiled, start, world)
    if waiting is None and talk.get("then"):  # a quest's script is said: what it was leading to
        more, waiting = quest_then(save, cpu, talk.pop("then"))
        after = [*after, *more]
    if waiting is None or "fight" in waiting or "quest_offer" in waiting or "endings" in waiting:
        events += after
        after = []
    talk["at"] = waiting["choice"] if waiting and "choice" in waiting else None
    talk["after"] = after  # shown when a choice's answer is done
    if waiting and "fight" in waiting:
        talk["stake"] = waiting["fight"]
    reached = world.ranked_up or talk.pop("rank_up", None)
    if reached is not None:
        if waiting and "choice" in waiting:
            talk["rank_up"] = reached  # after the conversation
        else:
            events += rank_up(save, cpu, reached)
    changed(save, *TALK_FIELDS)
    return {"talk": {"cpu": cpu.pk, "events": events, "waiting": waiting, "relation": standing(save, cpu.pk)}}


def rank_up(save, cpu, rank):
    """What reaching a rank plays: its rank_up line (with what it does), or a full scene (an event the town goes to)."""
    found = chatter.pick(cpu, "rank_up", rank)
    if not found:
        return []
    key, compiled, scene = found
    if scene:
        save.flags["scene"] = {"scene": scene.pk, "cpu": cpu.pk}
        return [{"scene": reverse("weiss:world_scene", args=[save.slot])}]
    events, _ = chatter.play(compiled, 0, Talk(save, cpu, key))  # said through: a rank-up line's choices aren't offered
    return events


def talk(save, cpu_id):
    """Talk to someone here: the day's first talk with them brings points."""
    cpu = someone_here(save, cpu_id)
    rel = relation(save, cpu.pk)
    if rel.get("talked_turn") == save.turn:
        raise ValueError(f"You've talked with {cpu.name} {this_time(save)} already.")
    rel["talked_turn"] = save.turn
    engage(save)
    cold = quests.estranged(save, cpu.pk)  # a choice closed this friendship: they say so (their own lines, or the built-in)
    if rel.get("talked") == save.day:
        return converse(save, cpu, "estranged" if cold else "again")
    rel["talked"] = save.day
    world = Talk(save, cpu, "talk")
    gained = world.points(gain(cpu, TALK_POINTS))
    found = converse(save, cpu, "estranged" if cold else "greet", gained)
    if world.ranked_up is not None:
        save.today["talk"]["rank_up"] = world.ranked_up
        if found["talk"]["waiting"] is None or "fight" in found["talk"]["waiting"]:
            found["talk"]["events"] += rank_up(save, cpu, save.today["talk"].pop("rank_up"))
            changed(save, *TALK_FIELDS)
    return found


def answer(save, cpu_id, option):
    """The player answers the choice they're on: the talk carries on."""
    cpu = someone_here(save, cpu_id)
    talk = save.today.get("talk") or {}
    key = talk.get("chatter", "")
    load = quests.script_for if key.startswith("quest:") else chatter.load
    compiled = load(key) if talk.get("cpu") == cpu.pk and talk.get("at") is not None else None
    if not compiled:
        raise ValueError("That conversation's over; talk to them again.")
    world = Talk(save, cpu, talk["chatter"])
    start = chatter.after_choice(compiled, talk["at"], option, world)
    return carry_on(save, cpu, compiled, start, talk.get("after", []))


# ---------------------------------------------------------------- Quests in the talk box (see weiss.quests)

def quest_script(save, cpu, key, part, then, after=()):
    """Play one of a quest's scripts in the talk box ("offer", "talk:<objective>" or "end:<ending>"), and when it's
    said, do `then` (quest_then). A quest with no script for it goes straight on."""
    save.today["talk"] = {"cpu": cpu.pk, "chatter": f"quest:{key}:{part}", "at": None, "stake": offered_stake(save, cpu.pk), "then": then}
    compiled = quests.script_for(f"quest:{key}:{part}") or {"labels": {}, "steps": []}
    return carry_on(save, cpu, compiled, 0, list(after))


def quest_then(save, cpu, then):
    """What a quest script leads to once it's said: (events, what the box waits for next)."""
    if then["do"] == "offer":
        quest = quests.quests(save).get(then["quest"])
        if quest and quests.offerable(save, quest):
            return [], {"quest_offer": quests.offer_panel(save, quest)}
        return [], None
    if then["do"] == "talked":
        return quests.talked(save, cpu, then["quest"], then["objective"]), None
    return [], None


def quest_act(save, cpu_id, act, key, data):
    """Something the player does about a quest with someone here: hear its offer, take it, talk about it, hand a card
    over, or choose how it ends. What the town gets: {"talk": {...}}, as converse."""
    cpu = someone_here(save, cpu_id)
    quest = quests.find_quest(save, key)
    engage(save)
    if act == "offer":
        if quest.giver_id != cpu.pk or not quests.offerable(save, quest):
            raise ValueError(f"{cpu.name} isn't offering that now.")
        return quest_script(save, cpu, key, "offer", {"do": "offer", "quest": key})
    if act == "accept":
        events = quests.accept(save, cpu, key)
        changed(save, *TALK_FIELDS)
        return {"talk": {"cpu": cpu.pk, "events": events, "waiting": None, "relation": standing(save, cpu.pk)}}
    if act == "talk":
        objective = data.get("objective", "")
        found = next((item for item in quests.actions(save, cpu)["talks"] if item["quest"] == key and item["objective"] == objective), None)
        if not found:
            raise ValueError("There's nothing to talk about there now.")
        return quest_script(save, cpu, key, f"talk:{objective}", {"do": "talked", "quest": key, "objective": objective})
    if act == "hand":
        events = quests.hand_over(save, cpu, key, data.get("objective", ""))
        changed(save, *TALK_FIELDS)
        return {"talk": {"cpu": cpu.pk, "events": events, "waiting": None, "relation": standing(save, cpu.pk)}}
    if act == "settle":
        panel = quests.settle_panel(save, cpu, key)
        if not panel["endings"]:
            raise ValueError(f"This isn't one to finish with {cpu.name}.")
        return {"talk": {"cpu": cpu.pk, "events": [], "waiting": {"endings": panel}, "relation": standing(save, cpu.pk)}}
    if act == "choose":
        ending, events = quests.choose(save, cpu, key, data.get("ending", ""), data.get("confirm") == "1")
        # The ending's own script plays first; what it did (rewards, what closed, a rank reached) is shown after.
        return quest_script(save, cpu, key, f"end:{ending['key']}", {"do": "ended"}, after=events)
    raise ValueError("That can't be done here.")


# ---------------------------------------------------------------- Gifts

def taste(cpu, item):
    """How a CPU takes a gift: loved, liked, disliked or neutral, by its tags (a loved tag wins over a disliked one)."""
    tastes, tags = cpu.gift_tastes or {}, set(item.tags or [])
    for kind, answer in (("loves", "loved"), ("dislikes", "disliked"), ("likes", "liked")):
        if tags & set(tastes.get(kind, [])):
            return answer
    return "neutral"


def gift_items(save):
    """The gift items this player can see and buy: staff-only ones (staff testing) only for staff."""
    items = GiftItem.objects.all()
    return items if save.user.is_staff else items.filter(staff_only=False)


def inventory(save):
    """[{key, name, icon, about, price, have, staff}] for every gift item, as the shop and the talk box show them."""
    return [{"key": item.key, "name": item.name, "icon": item.icon, "about": item.about, "price": item.price,
             "have": save.gifts.get(item.key, 0), "staff": item.staff_only} for item in gift_items(save)]


def buy_gift(save, key):
    here = place_of(save)
    if not here or not here.shop:
        raise ValueError("You need to be at the card shop.")
    item = gift_items(save).filter(key=key).first()
    if not item:
        raise ValueError("The shop doesn't sell that.")
    if save.gifts.get(key, 0) >= MAX_GIFTS:
        raise ValueError(f"You can carry {MAX_GIFTS} of those at most.")
    if item.price > save.money:
        raise ValueError(f"{item.name} costs {item.price} coins, and you have {save.money}.")
    save.money -= item.price
    save.gifts[key] = save.gifts.get(key, 0) + 1
    changed(save, "money", "gifts")
    return item


def give(save, cpu_id, key):
    """Give someone here a gift: once a day each. Their points change by how they take it, and they say so."""
    cpu = someone_here(save, cpu_id)
    item = gift_items(save).filter(key=key).first()
    if not item or save.gifts.get(key, 0) < 1:
        raise ValueError("You don't have that to give.")
    if item.staff_only:  # a staff token: a rank at once, and it costs no time or daily gift
        save.gifts[key] -= 1
        if not save.gifts[key]:
            del save.gifts[key]
        changed(save, "gifts")
        return level_up(save, cpu)
    rel = relation(save, cpu.pk)
    if rel.get("gifted") == save.day:
        raise ValueError(f"You've given {cpu.name} something today already.")
    engage(save)
    save.gifts[key] -= 1
    if not save.gifts[key]:
        del save.gifts[key]
    rel["gifted"] = save.day
    quests.gift_given(save, cpu, item)
    reaction = taste(cpu, item)
    world = Talk(save, cpu, "gift")
    gained = world.points(gain(cpu, GIFT_POINTS[reaction]))
    found = converse(save, cpu, f"gift_{reaction}", gained)
    found["talk"]["events"].insert(0, {"gave": item.name, "icon": item.icon, "reaction": reaction})  # handed over, then their answer
    if world.ranked_up is not None:
        if found["talk"]["waiting"] is None or "fight" in found["talk"]["waiting"]:
            found["talk"]["events"] += rank_up(save, cpu, world.ranked_up)
            changed(save, *TALK_FIELDS)
        else:
            save.today["talk"]["rank_up"] = world.ranked_up
            changed(save, "today")
    return found


def level_up(save, cpu):
    """Staff testing: take someone up one friendship rank at once, by the points that rank needs. It plays what a rank
    reached by points plays (the rank-up line or scene, and the rank's rewards, once). A rank a quest holds back stays
    where it is, as points do; the badge says what it waits on."""
    rows = ranks()
    rank = rank_of(save, cpu.pk)
    if rank + 1 >= len(rows):
        raise ValueError(f"{cpu.name} is {rows[rank]['name']} already.")
    points = relation(save, cpu.pk)["points"]
    threshold = rows[rank + 1]["points"]
    gate = quests.gate_quest(save, cpu.pk)
    gated = gate is not None and gate.gate_rank == rank + 1
    # A gated rank stops one point short first, so the next press is the one that gives its quest (as points would).
    target = threshold - 1 if gated and points < threshold - 1 else threshold
    need = max(target - points, 0)
    if not need:  # the points are there: a gate quest is what holds the rank
        if gated:
            raise ValueError(f"The next rank waits on “{gate.title}”.")
        raise ValueError(f"{cpu.name} is already at that rank.")
    world = Talk(save, cpu, "staff")
    events = world.points(need)
    if world.ranked_up is not None:
        events += rank_up(save, cpu, world.ranked_up)
    changed(save, *TALK_FIELDS)
    return {"talk": {"cpu": cpu.pk, "events": events, "waiting": None, "relation": standing(save, cpu.pk)}}


def staff_level(save, cpu_id):
    """The talk box's staff button: raise someone here a rank. Staff in test mode only."""
    if not save.user.is_staff or not test_mode(save):
        raise ValueError("Raising a rank is for staff in test mode.")
    return level_up(save, someone_here(save, cpu_id))


TASTE_TAGS = ("sweet", "drink", "food", "spicy", "fancy", "cute", "cool", "flowers", "cards", "book", "music", "sporty", "game", "calm")


def starter_tastes(cpu_id):
    """Made-up gift tastes for a CPU, the same every time for the same CPU: a tag it loves, two or three it likes and
    one or two it dislikes."""
    rng = random.Random(cpu_id * 104729)
    tags = rng.sample(TASTE_TAGS, 6)
    likes = rng.randint(2, 3)
    return {"loves": tags[:1], "likes": tags[1:1 + likes], "dislikes": tags[1 + likes:1 + likes + rng.randint(1, 2)]}


def give_tastes(cpus=None):
    """Give each CPU (all, unless some are given) that has no gift tastes its starter ones. Returns how many."""
    count = 0
    for cpu in cpus if cpus is not None else CpuProfile.objects.all():
        if not cpu.gift_tastes:
            cpu.gift_tastes = starter_tastes(cpu.pk)
            cpu.save(update_fields=["gift_tastes"])
            count += 1
    return count


# ---------------------------------------------------------------- The town, as the page shows it

def greetings(save, cpu):
    """{"hello", "bye"}: what this CPU says when the player walks up and leaves, by how well they know each other
    (its own lines, or the built-in ones), the same all through a time of day. Cold, if a choice estranged them."""
    fill = filler(save, cpu)
    if quests.estranged(save, cpu.pk):
        own = chatter.first_line(cpu, "estranged", 0, fill, random.Random(f"{save.seed}:{save.turn}:{cpu.pk}:cold"))
        return {"hello": own or fill(chatter.COLD["hello"].split(": ", 1)[1]), "bye": fill(chatter.COLD["goodbye"].split(": ", 1)[1])}
    rank = rank_of(save, cpu.pk)
    said = {}
    for key, context in (("hello", "hello"), ("bye", "goodbye")):
        said[key] = chatter.first_line(cpu, context, rank, fill, random.Random(f"{save.seed}:{save.turn}:{cpu.pk}:{context}"))
    return said


def town_news(save):
    """What's happened to the save's quests since the page last heard (a duel won, somewhere reached): told once."""
    found = save.quests.pop("news", None)
    if found:
        save.save(update_fields=["quests"])
    return found or []


def town(save):
    """The town as the page shows it: when and where it is, the save's coins, who's here, the shop and the map."""
    known = places(save)
    here = place_of(save, known)
    time = save.turn % len(WorldSave.TIMES)
    duel = live_duel(save)
    found = whereabouts(save)
    people = present(save, here.key, found) if here else []
    # Who's where, for the map: each place's people by name, with their circle pictures.
    names = {cpu.pk: cpu for cpu in CpuProfile.objects.filter(pk__in=found).select_related("avatar_card").order_by("name")}
    by_place = {}
    for cpu in names.values():
        by_place.setdefault(found[cpu.pk].place.key, []).append({"name": cpu.name, "avatar": cpu.avatar})
    return {
        "version": save.version, "day": save.day, "weekday": save.weekday, "time": time, "time_name": save.time_of_day,
        "money": save.money,
        "place": {"key": here.key, "name": here.name, "backdrop": here.backdrop(time), "shop": here.shop} if here else None,
        "places": [{"key": p.key, "name": p.name, "backdrop": p.backdrop(time), "here": here is not None and p.key == here.key,
                    "who": by_place.get(p.key, [])} for p in known],
        "people": [{"id": cpu.pk, "name": cpu.name, "portraits": cpu_portraits(cpu), "stake": stake_with(save, cpu.pk, rule),
                    **greetings(save, cpu), "talked_now": save.relations.get(str(cpu.pk), {}).get("talked_turn") == save.turn,
                    "intro": chatter.first_line(cpu, "before_duel", rank_of(save, cpu.pk), filler(save, cpu)) or cpu.intro_text,
                    "duelled": cpu.pk in save.today.get("duelled", []), "relation": standing(save, cpu.pk),
                    "offer": offered_stake(save, cpu.pk), "quests": quests.actions(save, cpu)} for cpu, rule in people],
        "quests": {**quests.counts(save), "url": reverse("weiss:world_quests", args=[save.slot])},
        "news": town_news(save),
        "gifts": inventory(save),
        "shop": shop(save) if here and here.shop else None,
        "deck_ready": deck_problem(save) is None,
        # Spending the time: once the player's spent it with someone here, they stay till they pass it.
        "engaged": engaged(save) and not test_mode(save), "can_wait": can_wait(save)[0], "wait_why": can_wait(save)[1],
        "choose": choosing(save), "test_mode": test_mode(save), "staff": save.user.is_staff,
        "next_time": WorldSave.TIMES[(save.turn + 1) % len(WorldSave.TIMES)],
        "duel": {"url": reverse("weiss:play_room", args=[duel.pk]), "cpu": duel.cpu_name} if duel else None,
        # A scene still to watch (a rank-up's, a quest's): kept until it's seen, wherever the player went in between.
        "scene": scene_waiting(save),
    }


def scene_waiting(save):
    """{"url", "who"} for a scene the save has waiting to be watched, or None."""
    pending = save.flags.get("scene")
    if not pending:
        return None
    who = CpuProfile.objects.filter(pk=pending.get("cpu")).values_list("name", flat=True).first() if pending.get("cpu") else None
    return {"url": reverse("weiss:world_scene", args=[save.slot]), "who": who or ""}
