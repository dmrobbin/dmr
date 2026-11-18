"""World mode (see docs/world-mode.md): a player's saves, and what a save has: its time, place, coins, the cards
opened from its packs and the deck built from them.

A new save starts with packs of a set the player chooses (only sets big enough to fill packs, MIN_SET_CARDS) and the
specialty packs staff set (WorldSettings), and nothing else: every card in its deck comes from those, as in a
challenge. The pack opening, the specialty packs and the deck rules are the challenges' (weiss.packs, weiss.buffs,
weiss.challenge); a save has the fields they read (pool, packs, rewards, last_opening, sets).
"""
import hashlib
import random
import re
import secrets
from collections import Counter
from types import SimpleNamespace

from django.db import transaction
from django.urls import reverse

from . import buffs, challenge, chatter, packs
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
    """Save these fields, and the version that says something changed."""
    save.version += 1
    save.save(update_fields=[*fields, "version", "played"])


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


def travel(save, key):
    """Go to a place: free, any time. Raises ValueError if the save can't go there."""
    place = next((place for place in places(save) if place.key == key), None)
    if not place:
        raise ValueError("You can't go there.")
    if place.key != save.place:
        save.place = place.key
        changed(save, "place")
    return place


def wait(save):
    """Let time pass to the next part of the day; after night comes a new day, and what was done today is forgotten.
    Not while a duel's under way: it takes up the time it's in."""
    if live_duel(save):
        raise ValueError("You're in a duel: finish it first.")
    save.turn += 1
    if save.turn % len(WorldSave.TIMES) == 0:
        save.today = {}
    changed(save, "turn", "today")


# ---------------------------------------------------------------- Who's where (see CpuSchedule)

def chance(*parts):
    """A number from 0 to 1 that's always the same for the same parts: who's where never changes on a reload."""
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2 ** 64


def where_rule(save, rules, turn=None):
    """The rule (of one CPU's, highest priority first) that puts it somewhere at this turn, or None. A rule holds on its
    days and times, if its roll comes up; a once-a-day rule holds at only one of its times each day."""
    turn = save.turn if turn is None else turn
    day, time = turn // 4, turn % 4
    for rule in rules:
        if day % 7 not in rule.days or time not in rule.times:
            continue
        if rule.once_per_day:
            times = sorted(rule.times)
            if times[int(chance(save.seed, rule.cpu_id, day, rule.pk, "once") * len(times))] != time:
                continue
        if chance(save.seed, rule.cpu_id, turn, rule.pk) * 100 < rule.chance:
            return rule
    return None


def whereabouts(save, turn=None):
    """{cpu id: the rule that puts it somewhere} at this turn, for every CPU that can duel (finalized, with a deck). A
    CPU is in one place at most: its first rule that holds."""
    by_cpu = {}
    for rule in CpuSchedule.objects.filter(cpu__finalized=True, cpu__deck__isnull=False).select_related("place").order_by("-priority", "pk"):
        by_cpu.setdefault(rule.cpu_id, []).append(rule)
    found = {}
    for cpu_id, rules in by_cpu.items():
        if (rule := where_rule(save, rules, turn)):
            found[cpu_id] = rule
    return found


def starter_rules(cpu_id, places, usage):
    """A first schedule for one CPU, as CpuSchedule fields: a home it's at most weekdays, a weekend spot and somewhere it
    wanders to now and then. Each goes to whichever of `places` (keys) has the fewest rules so far (`usage`, updated
    here), so CPUs spread across the town; the rest is rolled from the CPU, the same every time."""
    rng = random.Random(cpu_id * 7919)

    def pick(but=()):
        choices = [key for key in places if key not in but] or list(places)
        least = min(usage.get(key, 0) for key in choices)
        key = rng.choice([key for key in choices if usage.get(key, 0) == least])
        usage[key] = usage.get(key, 0) + 1
        return key

    home = pick()
    weekend = pick((home,))
    wander = pick((home, weekend))
    return [
        {"place": home, "days": [0, 1, 2, 3, 4], "times": sorted(rng.sample(range(4), 2)), "chance": 90, "priority": 1},
        {"place": weekend, "days": [5, 6], "times": sorted(rng.sample(range(4), rng.randint(1, 2))), "chance": 80, "priority": 1},
        {"place": wander, "days": sorted(rng.sample(range(7), 3)), "times": [rng.randrange(4)], "chance": 60, "priority": 0},
    ]


def starter_schedules(cpus=None):
    """A first schedule (starter_rules) for each CPU that can duel and has none, or for these CPUs; staff edit them
    from there. Returns how many CPUs got one."""
    places = {place.key: place for place in WorldPlace.objects.filter(shop=False)}
    if not places:
        return 0
    usage = {}
    for rule in CpuSchedule.objects.select_related("place"):
        usage[rule.place.key] = usage.get(rule.place.key, 0) + 1
    found = CpuProfile.objects.filter(finalized=True, deck__isnull=False, schedule__isnull=True).order_by("pk")
    if cpus is not None:
        found = found.filter(pk__in=[cpu.pk for cpu in cpus])
    made = 0
    for cpu in found:
        for rule in starter_rules(cpu.pk, sorted(places), usage):
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
    if (problem := deck_problem(save)):
        raise ValueError(f"Your equipped deck can't duel yet: {problem[0].lower()}{problem[1:]}")
    found = next(((cpu, rule) for cpu, rule in present(save) if str(cpu.pk) == str(cpu_id)), None)
    if not found:
        raise ValueError("They aren't here now.")
    cpu, rule = found
    offered = offered_stake(save, cpu.pk)
    fee = (offered or rule.stake) if high_stakes else 0
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
    changed(save, "money")
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
        before, after = add_points(save, room.cpu_profile_id, WIN_POINTS if won else LOSS_POINTS) if room.cpu_profile_id else (0, 0)
        save.flags["last_duel"] = {"room": room.pk, "cpu": room.cpu_name, "cpu_id": room.cpu_profile_id, "won": won, "coins": coins,
                                   "first": first, "stake": room.world_stake, "seen": False,
                                   "points": WIN_POINTS if won else LOSS_POINTS, "rank_up": rank_names()[after] if after > before else ""}
        save.turn += 1
        if save.turn % len(WorldSave.TIMES) == 0:
            save.today = {}
        changed(save, "money", "today", "flags", "turn", "relations")


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
MAX_GIFTS = 99  # of each item held
RESERVED_FLAGS = {"last_duel", "set", "scene"}


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
    return rank_for(save.relations.get(str(cpu_id), {}).get("points", 0))


def add_points(save, cpu_id, n):
    """Change how much a CPU likes the player (never below 0): (rank before, rank after)."""
    rel = relation(save, cpu_id)
    before = rank_for(rel["points"])
    rel["points"] = max(0, rel["points"] + n)
    return before, rank_for(rel["points"])


def standing(save, cpu_id):
    """A CPU's friendship as the town shows it: rank (number and name), ranks there are, points, points the next rank
    takes (None at the top), and whether they've been talked to and given a gift today."""
    rel = save.relations.get(str(cpu_id), {})
    points, rows = rel.get("points", 0), ranks()
    rank = rank_for(points)
    return {"rank": rank, "name": rows[rank]["name"], "ranks": len(rows), "points": points,
            "next": rows[rank + 1]["points"] if rank + 1 < len(rows) else None,
            "talked": rel.get("talked") == save.day, "gifted": rel.get("gifted") == save.day}


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
        return [{"points": n, "relation": standing(self.save, self.cpu.pk), "rank_up": rank_names()[after] if after > before else ""}]

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


def someone_here(save, cpu_id):
    """The CPU (here now) the player's acting on. Raises ValueError if they aren't."""
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
    if waiting is None or "fight" in waiting:
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
    changed(save, "relations", "today", "flags", "money", "gifts")
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
    if rel.get("talked") == save.day:
        return converse(save, cpu, "again")
    rel["talked"] = save.day
    world = Talk(save, cpu, "talk")
    gained = world.points(TALK_POINTS)
    found = converse(save, cpu, "greet", gained)
    if world.ranked_up is not None:
        save.today["talk"]["rank_up"] = world.ranked_up
        if found["talk"]["waiting"] is None or "fight" in found["talk"]["waiting"]:
            found["talk"]["events"] += rank_up(save, cpu, save.today["talk"].pop("rank_up"))
            changed(save, "flags", "relations", "today", "money", "gifts")
    return found


def answer(save, cpu_id, option):
    """The player answers the choice they're on: the talk carries on."""
    cpu = someone_here(save, cpu_id)
    talk = save.today.get("talk") or {}
    compiled = chatter.load(talk.get("chatter", "")) if talk.get("cpu") == cpu.pk and talk.get("at") is not None else None
    if not compiled:
        raise ValueError("That conversation's over; talk to them again.")
    world = Talk(save, cpu, talk["chatter"])
    start = chatter.after_choice(compiled, talk["at"], option, world)
    return carry_on(save, cpu, compiled, start, talk.get("after", []))


# ---------------------------------------------------------------- Gifts

def taste(cpu, item):
    """How a CPU takes a gift: loved, liked, disliked or neutral, by its tags (a loved tag wins over a disliked one)."""
    tastes, tags = cpu.gift_tastes or {}, set(item.tags or [])
    for kind, answer in (("loves", "loved"), ("dislikes", "disliked"), ("likes", "liked")):
        if tags & set(tastes.get(kind, [])):
            return answer
    return "neutral"


def inventory(save):
    """[{key, name, icon, about, price, have}] for every gift item, as the shop and the talk box show them."""
    return [{"key": item.key, "name": item.name, "icon": item.icon, "about": item.about, "price": item.price,
             "have": save.gifts.get(item.key, 0)} for item in GiftItem.objects.all()]


def buy_gift(save, key):
    here = place_of(save)
    if not here or not here.shop:
        raise ValueError("You need to be at the card shop.")
    item = GiftItem.objects.filter(key=key).first()
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
    item = GiftItem.objects.filter(key=key).first()
    if not item or save.gifts.get(key, 0) < 1:
        raise ValueError("You don't have that to give.")
    rel = relation(save, cpu.pk)
    if rel.get("gifted") == save.day:
        raise ValueError(f"You've given {cpu.name} something today already.")
    save.gifts[key] -= 1
    if not save.gifts[key]:
        del save.gifts[key]
    rel["gifted"] = save.day
    reaction = taste(cpu, item)
    world = Talk(save, cpu, "gift")
    gained = world.points(GIFT_POINTS[reaction])
    found = converse(save, cpu, f"gift_{reaction}", gained)
    found["talk"]["events"].insert(0, {"gave": item.name, "icon": item.icon, "reaction": reaction})  # handed over, then their answer
    if world.ranked_up is not None:
        if found["talk"]["waiting"] is None or "fight" in found["talk"]["waiting"]:
            found["talk"]["events"] += rank_up(save, cpu, world.ranked_up)
            changed(save, "flags", "relations", "today", "money", "gifts")
        else:
            save.today["talk"]["rank_up"] = world.ranked_up
            changed(save, "today")
    return found


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
        "people": [{"id": cpu.pk, "name": cpu.name, "portraits": cpu_portraits(cpu), "stake": rule.stake,
                    "intro": chatter.first_line(cpu, "before_duel", rank_of(save, cpu.pk), filler(save, cpu)) or cpu.intro_text,
                    "duelled": cpu.pk in save.today.get("duelled", []), "relation": standing(save, cpu.pk),
                    "offer": offered_stake(save, cpu.pk)} for cpu, rule in people],
        "gifts": inventory(save),
        "shop": shop(save) if here and here.shop else None,
        "deck_ready": deck_problem(save) is None,
        "duel": {"url": reverse("weiss:play_room", args=[duel.pk]), "cpu": duel.cpu_name} if duel else None,
    }
