"""Buffs: rewards a challenge's scenes give, to help build its deck.

A scene gives them by `give`, `offer`, or an option's `(give …)` (see weiss.scenes). Anything random in them is
settled when the scene is queued (`resolve`), and when the scene's done, what the page says was given is checked
against the scene (`given`) before `grant` puts it on the challenge. A buff that needs nothing more happens then;
the rest wait on the challenge's page as rewards, claimed (`claim`) before the next fight, deck changes and all.

Pacts are buffs with a price (an infinite challenge's events mostly give them): some happen at once, cards lost
and all; the rest change the next fight (`fight_mods`), a handicap in it with a reward for winning it, and last
until it's won. A random buff is never a pact unless a scene asks for one ("give pact", "offer 2 pacts").

Outside a challenge there's nothing for a buff to do, so a scene's buffs are left out (`resolve` with enabled off).
"""
import copy
import random
import secrets
from dataclasses import dataclass

from . import augments, challenge, coop, packs
from .models import Card

TRADE_IN = 5  # cards given up for a pack
EXTRA_PACKS = 2
COPIES = 3
CLIMAX_COPIES = 2
LEVELS = (0, 1, 2, 3)
COLORS = ("Yellow", "Green", "Red", "Blue", "Purple")
REFORGE_CARDS = 10  # spare cards a reforge takes from the pool...
REFORGE_PACKS = 2  # ...for this many packs
BLOOD_PACKS = 3
AMBUSH_DAMAGE = 2  # cards in the clock an ambushed fight starts with...
AMBUSH_PACKS = 2  # ...and the packs winning it brings
ALL_IN_PACKS = 2  # lucky packs, for every second chance
OUTPACED_PACKS = 2
WAR_CHEST = 3  # cards in the stock a war chest's fight starts with


@dataclass(frozen=True)
class Buff:
    id: str
    name: str
    description: str
    claim: str = ""  # what claiming it asks for; "" for one that happens at once
    pack: str = ""  # for a pack: which cards it's made of
    pact: bool = False  # it has a price: never given at random unless a scene asks for a pact
    next_fight: bool = False  # it changes the next fight (see fight_mods), until that's won
    special: bool = False  # only given for something (an augment pick, for beating a boss): never at random


BUFFS = {buff.id: buff for buff in (
    Buff("extra_packs", "Two more packs", f"Open {EXTRA_PACKS} additional packs."),
    Buff("lucky_pack", "Lucky pack", "Open a pack of rarer cards: uncommons for commons, an extra rare and two foils.", "pack", "lucky"),
    Buff("copies", "Three of a kind", f"Choose a card in your deck: {COPIES} more copies of it go in your pool.", "deck_card"),
    Buff("exchange", "Exchange", "Swap a card in your pool for another of the same rarity from its set.", "exchange"),
    Buff("climax_pack", "Climax pack", "Open a pack of nothing but climaxes.", "pack", "climax"),
    Buff("level_pack", "Level pack", "Open a pack of one level's cards: the level you choose.", "pack", "level"),
    Buff("second_chance", "Second chance", "Your next loss doesn't end the challenge: you fight again instead."),
    Buff("color_pack", "Color pack", "Open a pack of one color's cards: the color you choose.", "pack", "color"),
    Buff("trade_in", "Trade-in", f"Give up {TRADE_IN} cards from your pool for a new pack.", "trade_in"),
    Buff("wild_pack", "Wild pack", "Open a pack from any set at all, even one this challenge doesn't use.", "pack", "wild"),
    Buff("climax_pick", "Climax pick", f"Choose any climax from this challenge's sets: {CLIMAX_COPIES} copies go in your pool.", "climax"),
    # Pacts: something for something.
    Buff("reforge", "Reforge", f"Up to {REFORGE_CARDS} random cards from your pool that aren't in your deck are melted down: open {REFORGE_PACKS} new packs.", pact=True),
    Buff("sacrifice", "Sacrifice", "Every copy of a random card in your deck leaves your pool for good. In return: a lucky pack and a climax pick.", pact=True),
    Buff("all_in", "All in", f"Give up every second chance you have, for {ALL_IN_PACKS} lucky packs each.", pact=True),
    Buff("blood_pact", "Blood pact", f"Open {BLOOD_PACKS} packs now. Your next opponent plays at its hardest.", pact=True, next_fight=True),
    Buff("ambush", "Ambush", f"Your next fight starts with {AMBUSH_DAMAGE} damage in your clock. Win it for {AMBUSH_PACKS} more packs.", pact=True, next_fight=True),
    Buff("outpaced", "Outpaced", f"Open {OUTPACED_PACKS} packs now. Your next opponent takes the first turn.", pact=True, next_fight=True),
    Buff("war_chest", "War chest", f"Your next fight starts with {WAR_CHEST} cards in your stock.", next_fight=True),
    Buff("augment", "Augment", f"Choose one of {augments.OFFER} augments: a change to the rest of your run.", "augment", special=True),
)}
RANDOM = "random"
PACT = "pact"  # a scene's "give pact": a pact, at random


def roll(count, rng=random, pacts=False):
    """Some different buffs, at random: pacts, or the rest."""
    found = sorted(buff_id for buff_id, buff in BUFFS.items() if buff.pact == pacts and not buff.special)
    return rng.sample(found, min(count, len(found)))


def fight_mods(run):
    """The buffs changing a challenge's next fight (see grant), until it's won."""
    return [buff_id for buff_id in ((run.path or {}).get("next") or []) if buff_id in BUFFS] if run else []


def shown(buff_id):
    buff = BUFFS[buff_id]
    return {"buff": buff.id, "name": buff.name, "text": buff.description}


def resolve(payload, enabled, rng=random):
    """A scene payload with its buffs settled: random ones picked, and each with its name and description for
    the player. Not enabled (outside a challenge), they're taken out; steps become "skip", so labels still fit."""
    payload = copy.deepcopy(payload)
    payload["buffs"] = enabled
    for i, step in enumerate(payload["steps"]):
        if step["do"] in ("give", "offer") and not enabled:
            payload["steps"][i] = {"do": "skip", "line": step["line"]}
        elif step["do"] == "give":
            step.update(shown(roll(1, rng, step["buff"] == PACT)[0] if step["buff"] in (RANDOM, PACT) else step["buff"]))
        elif step["do"] == "offer":
            step["options"] = [shown(buff) for buff in (step.get("choices") or roll(step["count"], rng, step.get("pacts", False)))]
        elif step["do"] == "choice":
            for option in step["options"]:
                if not enabled:
                    option.pop("give", None)
                elif option.get("give"):
                    if option["give"] in (RANDOM, PACT):
                        option["give"] = roll(1, rng, option["give"] == PACT)[0]
                    option["give_name"] = BUFFS[option["give"]].name
                    option["give_text"] = BUFFS[option["give"]].description  # shown with the option: a pact's price is seen first
    return payload


def given(payload, picks):
    """The buffs a played scene gave, from what the page reports: [[step, option or None], ...], each one a
    step that gives a buff, at most once. Anything else is left out."""
    found, seen = [], set()
    for pick in picks if isinstance(picks, list) else []:
        try:
            at, option = pick
            step = payload["steps"][int(at)]
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if at in seen or not payload.get("buffs"):
            continue
        buff = None
        if step["do"] == "give" and option is None:
            buff = step.get("buff")
        elif step["do"] in ("offer", "choice") and isinstance(option, int) and 0 <= option < len(step["options"]):
            buff = step["options"][option].get("buff" if step["do"] == "offer" else "give")
        if buff in BUFFS:
            seen.add(at)
            found.append(buff)
    return found


@coop.sharing
def grant(run, buff_ids, source="", rng=random):
    """Put these buffs on a challenge: those needing nothing more happen now, the rest wait to be claimed. Returns
    what happened, a line for each that did something the player should hear about (pacts mostly)."""
    said = []

    def reward(buff_id, **extra):
        run.rewards.append({"key": secrets.token_hex(6), "buff": buff_id, "source": source, **extra})

    for buff_id in buff_ids:
        if buff_id == "extra_packs":
            run.packs += EXTRA_PACKS
        elif buff_id == "second_chance":
            run.lives += 1
        elif buff_id == "reforge":
            lost = take_spares(run, REFORGE_CARDS, rng)
            run.packs += REFORGE_PACKS
            said.append(f"Reforge: {cards_said(lost)} melted down, for {REFORGE_PACKS} packs to open.")
        elif buff_id == "sacrifice":
            in_deck = list(run.deck.entries.values_list("card_id", flat=True)) if run.deck else []
            usable = coop.available(run)  # in co-op, the partner's deck keeps its copies
            pk = rng.choice(in_deck or [int(pk) for pk in usable] or [0])
            copies = usable.get(str(pk), 0)
            if copies:
                take_from_pool(run, {pk: copies})
            reward("lucky_pack")
            reward("climax_pick")
            said.append(f"Sacrifice: {cards_said({pk: copies}) if copies else 'nothing'} gone for good; a lucky pack and a climax pick to claim.")
        elif buff_id == "all_in":
            for _ in range(run.lives * ALL_IN_PACKS):
                reward("lucky_pack")
            said.append(f"All in: {run.lives} second chance{'s' if run.lives != 1 else ''} given up, for {run.lives * ALL_IN_PACKS} lucky packs."
                        if run.lives else "All in: you had no second chances to give up, and nothing to show for it.")
            run.lives = 0
        elif buff_id == "augment":  # what it offers is settled now, so a reload doesn't change it
            if options := augments.offer(run, rng):
                reward(buff_id, options=options)
            else:
                run.packs += EXTRA_PACKS
                said.append(f"You have every augment there is: {EXTRA_PACKS} more packs instead.")
        elif BUFFS.get(buff_id) and BUFFS[buff_id].next_fight:
            run.packs += {"blood_pact": BLOOD_PACKS, "outpaced": OUTPACED_PACKS}.get(buff_id, 0)
            run.path = {**(run.path or {}), "next": [*fight_mods(run), *([] if buff_id in fight_mods(run) else [buff_id])]}  # once is enough
            said.append(f"{BUFFS[buff_id].name}: {BUFFS[buff_id].description}")
        else:
            reward(buff_id)
    run.save(update_fields=["packs", "lives", "rewards", "pool", "path"])
    return said


def take_spares(run, count, rng=random):
    """Take up to `count` random cards from the pool that the deck isn't using (copies beyond what it has, and in
    co-op, what the partner's deck has). Returns {card id: copies taken}."""
    in_deck = dict(run.deck.entries.values_list("card_id", "quantity")) if run.deck else {}
    spares = [int(pk) for pk, n in coop.available(run).items() for _ in range(n - in_deck.get(int(pk), 0))]
    taken = {}
    for pk in rng.sample(spares, min(count, len(spares))):
        taken[pk] = taken.get(pk, 0) + 1
    take_from_pool(run, taken)
    return taken


def cards_said(copies):
    """"3 cards (Rapi x2, Anis)": what some {card id: copies} are, for the player."""
    names = dict(Card.objects.filter(pk__in=copies).values_list("pk", "name"))
    total = sum(copies.values())
    if not total:
        return "no cards"
    listed = ", ".join(f"{names.get(pk, 'a card')}{f' ×{n}' if n > 1 else ''}" for pk, n in copies.items())
    return f"{total} card{'s' if total != 1 else ''} ({listed})"


def reward_of(run, key):
    return next((reward for reward in run.rewards if reward["key"] == key), None)


def climax_choices(run):
    """The climaxes a climax pick can be, from this challenge's sets."""
    sets = [entry["id"] for entry in challenge.allowed_sets(run)]
    return [card for card in Card.objects.filter(expansion_id__in=sets, card_type__iexact="climax").order_by("expansion_id", "serial_number")
            if packs.rarity_of(card) not in packs.NOT_IN_PACKS]


def exchange_choices(card):
    """What a card in the pool can be swapped for: the others of its set with the same rarity."""
    rarity = packs.rarity_of(card)
    return [other for other in Card.objects.filter(expansion_id=card.expansion_id).exclude(pk=card.pk).order_by("serial_number")
            if packs.rarity_of(other) == rarity]


def take_from_pool(run, copies):
    """Take {card id: copies} out of the pool, and out of the deck too where it no longer has them. In co-op, the
    two decks together can't have more than the pool: this player's gives way first, then the partner's."""
    other = coop.partner_run(run)
    decks = [deck for deck in (run.deck, other and other.deck) if deck]
    for pk, n in copies.items():
        left = run.pool.get(str(pk), 0) - n
        if left > 0:
            run.pool[str(pk)] = left
        else:
            run.pool.pop(str(pk), None)
        entries = [entry for deck in decks for entry in deck.entries.filter(card_id=pk)]
        over = sum(entry.quantity for entry in entries) - max(left, 0)
        for entry in entries:
            if over <= 0:
                break
            cut = min(over, entry.quantity)
            over -= cut
            if cut < entry.quantity:
                entry.quantity -= cut
                entry.save(update_fields=["quantity"])
            else:
                entry.delete()


def add_to_pool(run, pk, n):
    run.pool[str(pk)] = run.pool.get(str(pk), 0) + n


def number(data, field):
    """A whole number the player chose, or 0."""
    value = str(data.get(field) or "")
    return int(value) if value.isdigit() else 0


def reward_pack(run, buff, data):
    """(the cards a pack reward is made of, as a packs.Pool, and their set) from the set (and level or color) chosen."""
    expansion_id = number(data, "set")
    sets = packs.pack_sets() if buff.pack == "wild" else challenge.allowed_sets(run)
    if expansion_id not in {entry["id"] for entry in sets}:
        raise ValueError("Its pack can't come from that set.")
    cards = Card.objects.filter(expansion_id=expansion_id)
    if buff.pack == "climax":
        cards = cards.filter(card_type__iexact="climax")
    elif buff.pack == "level":
        if data.get("level") not in [str(level) for level in LEVELS]:
            raise ValueError("Choose a level.")
        cards = cards.filter(level=int(data["level"])).exclude(card_type__iexact="climax")
    elif buff.pack == "color":
        if data.get("color") not in COLORS:
            raise ValueError("Choose a color.")
        cards = cards.filter(color=data["color"])
    pool = packs.Pool(cards.order_by("serial_number"))
    if not pool:
        raise ValueError("That set has no cards like that in packs.")
    return pool, expansion_id


@coop.sharing
def claim(run, key, data, rng=random):
    """Claim a reward with what the player chose (`data`, as posted). Returns True if packs were opened (to be
    shown being opened). Raises ValueError saying what's wrong; nothing changes then."""
    reward = reward_of(run, key)
    if not reward:
        raise ValueError("That reward has been claimed already.")
    buff = BUFFS[reward["buff"]]
    opened = False
    if buff.claim == "pack":
        pool, expansion_id = reward_pack(run, buff, data)
        pack = packs.open_pack(pool, rng, packs.BOOSTED_PACK if buff.pack == "lucky" else packs.PACK)
        for pull in pack:
            add_to_pool(run, pull.card.pk, 1)
        run.last_opening = {**packs.opening(pool, [pack]), "set_id": expansion_id}
        opened = True
    elif buff.claim == "deck_card":
        pk = number(data, "card")
        if not run.deck or not run.deck.entries.filter(card_id=pk).exists():
            raise ValueError("Choose a card in your deck.")
        add_to_pool(run, pk, COPIES)
    elif buff.claim == "exchange":
        give, take = Card.objects.filter(pk=number(data, "give")).first(), Card.objects.filter(pk=number(data, "take")).first()
        if not give or str(give.pk) not in coop.available(run):
            raise ValueError("Choose a card from your pool.")
        if not take or take not in exchange_choices(give):
            raise ValueError("It can only be swapped for another card of its set with the same rarity.")
        take_from_pool(run, {give.pk: 1})
        add_to_pool(run, take.pk, 1)
    elif buff.claim == "trade_in":
        # trade-<card id>: how many of that card to give up.
        copies = {int(field[6:]): number(data, field) for field in data if field.startswith("trade-") and field[6:].isdigit() and number(data, field)}
        usable = coop.available(run)
        if sum(copies.values()) != TRADE_IN or any(n > usable.get(str(pk), 0) for pk, n in copies.items()):
            raise ValueError(f"Choose {TRADE_IN} cards from your pool to give up.")
        take_from_pool(run, copies)
        run.packs += 1
    elif buff.claim == "augment":
        if data.get("augment") not in reward.get("options", []):
            raise ValueError("Choose one of the augments offered.")
        augments.take(run, data["augment"])
    elif buff.claim == "climax":
        pk = number(data, "card")
        if pk not in {card.pk for card in climax_choices(run)}:
            raise ValueError("Choose one of the climaxes.")
        add_to_pool(run, pk, CLIMAX_COPIES)
    run.rewards = [r for r in run.rewards if r["key"] != key]
    run.save(update_fields=["pool", "packs", "rewards", "last_opening", "augments"])
    return opened
