"""Challenge mode: build a deck from packs, then fight through an arcade list with it.

A challenge starts with START_PACKS packs (NARRATIVE_START_PACKS for a narrative one). Opening them adds their cards to the challenge's pool, and its
deck can hold only what's in the pool (sealed: nothing else, so a deck can be short of 50 or of climaxes
until more packs come). Each win in its arcade run brings more (see win_reward); a loss ends the challenge. In a
free challenge the player picks any set for each pack, an arbitrary arcade list to fight; a narrative one
(NarrativeChallenge, set up by staff) fixes the list, and the sets its packs come from. An infinite one has no
list: every CPU there is, drawn one at a time, harder as it goes (INFINITE_MODELS), for as long as the player wins,
each win bringing a random reward and no scenes.

Stopping partway keeps the run where it is: the next fight starts with the CPU it stopped at. Resetting
starts again from nothing, deck and all. At the end, cleared or lost, the player keeps the deck (it joins
their lists) or discards it; until then it's kept out of their lists (CardList.challenge).
"""
import random
import secrets

from django.db import transaction
from django.utils import timezone

from . import packs
from .lists import DECK_SIZE
from .models import ArcadeRun, Card, CardList, CardListEntry, ChallengeRun, CpuProfile, GameRoom

START_PACKS = 20  # packs to open at the start of a free challenge
NARRATIVE_START_PACKS = 20  # ...and of a narrative one
WIN_PACKS = 3  # what a win in a free challenge brings
NARRATIVE_WIN_PACKS = 2  # ...and in a narrative one, with these rewards to claim besides (weiss.buffs)
NARRATIVE_WIN_REWARDS = ("color_pack",)
STAFF_ONLY = True  # being tried out, as booster packs are
INFINITE_NAME = "Infinite challenge"
INFINITE_WIN_PACKS = 1  # what a win in an infinite challenge brings, with one of these besides, at random: its prize,
INFINITE_PRIZES = ("climax_pack", "color_pack", "lucky_pack")  # which the Victory screen's slot machine lands on (play.js)
# How an infinite challenge's CPUs play, whatever their own model: (fights, the model or the models to pick from),
# in turn, then hard, from an aggression picked at random, for the rest.
INFINITE_MODELS = ((2, ("easy",)), (1, ("standard",)), (3, ("focused", "strategic")))


def current(user):
    """This player's challenge, from starting it until they've kept or discarded its deck; or None."""
    return ChallengeRun.objects.filter(user=user, finished__isnull=True).select_related("deck", "arcade_run", "scenario", "narrative").first()


def start_packs(kind):
    """How many packs a challenge of this kind starts with."""
    return NARRATIVE_START_PACKS if kind == ChallengeRun.Kind.NARRATIVE else START_PACKS


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


def infinite(arcade_run):
    """Whether this arcade run is an infinite challenge's."""
    return bool(arcade_run and ChallengeRun.objects.filter(arcade_run=arcade_run, kind=ChallengeRun.Kind.INFINITE).exists())


def opponents():
    """The CPUs an infinite challenge draws from: every one players can fight."""
    return list(CpuProfile.objects.filter(finalized=True, deck__entries__isnull=False).distinct())


def next_opponent(order, rng=random):
    """A CPU for an infinite challenge's next fight, at random, not the one just fought if there's another; or None."""
    found = opponents()
    others = [cpu for cpu in found if not order or cpu.pk != order[-1]] or found
    return rng.choice(others).pk if others else None


def extend(arcade_run):
    """An infinite challenge's run just won a fight: one more opponent at the end, so it never runs out."""
    if infinite(arcade_run):
        nxt = next_opponent(arcade_run.order)
        if nxt:
            arcade_run.order.append(nxt)


def infinite_style(arcade_run, profile):
    """(model, aggression) a CPU plays an infinite challenge's fight with, by how many fights there have been (see
    INFINITE_MODELS). Random choices are settled by the run and fight, so a fight keeps them, reloads and all."""
    rng = random.Random(f"{arcade_run.pk}:{arcade_run.position}")
    fight = arcade_run.position
    for count, models in INFINITE_MODELS:
        if fight < count:
            return rng.choice(models), profile.aggression
        fight -= count
    from .cpu import MAX_AGGRESSION, MIN_AGGRESSION  # weiss.cpu needs nothing from here; this keeps it that way
    return "hard", rng.randint(MIN_AGGRESSION, MAX_AGGRESSION)


def of(arcade_run):
    """The challenge in progress that this arcade run is fought for, if it's one."""
    return ChallengeRun.objects.filter(arcade_run=arcade_run, status=ChallengeRun.Status.ACTIVE).first() if arcade_run else None


def narrative(arcade_run):
    """Whether this arcade run is a narrative challenge's: its scenes do the talking, so the CPUs' own intro and
    end-of-fight lines are left out."""
    run = of(arcade_run)
    return bool(run and run.kind == ChallengeRun.Kind.NARRATIVE)


def deck_name(name):
    return f"{name} challenge"[:100]


def start(user, kind, scenario, narrative=None):
    """A new challenge: an empty deck and its packs to open (see start_packs)."""
    name = narrative.name if narrative else scenario.name if scenario else INFINITE_NAME
    with transaction.atomic():
        deck = CardList.objects.create(user=user, name=deck_name(name), challenge=True)
        return ChallengeRun.objects.create(user=user, kind=kind, narrative=narrative, scenario=scenario, name=name, deck=deck,
                                           sets=list(narrative.sets) if narrative else [], packs=start_packs(kind))


def allowed_sets(run):
    """[{"id", "name", "cards"}] that this challenge's packs can come from (see packs.pack_sets)."""
    sets = packs.pack_sets()
    return [entry for entry in sets if entry["id"] in run.sets] if run.sets else sets


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
    """[(card, copies pulled, copies in the deck)], in the order a deck lists them."""
    in_deck = dict(run.deck.entries.values_list("card_id", "quantity")) if run.deck else {}
    cards = Card.objects.filter(pk__in=[int(pk) for pk in run.pool]).order_by("level", "card_type", "serial_number")
    return [(card, run.pool[str(card.pk)], in_deck.get(card.pk, 0)) for card in cards]


def save_deck(run, copies):
    """Make the deck exactly these {card id: copies}. Returns what's wrong with them (nothing is saved then), or None."""
    copies = {int(pk): int(n) for pk, n in copies.items() if int(n) > 0}
    for pk, n in copies.items():
        if n > run.pool.get(str(pk), 0):
            return "A deck can only have the cards you've pulled from your packs."
    if sum(copies.values()) > DECK_SIZE:
        return f"A deck has at most {DECK_SIZE} cards."
    with transaction.atomic():
        run.deck.entries.all().delete()
        CardListEntry.objects.bulk_create(CardListEntry(card_list=run.deck, card_id=pk, quantity=n) for pk, n in copies.items())
        run.deck.save(update_fields=["updated"])
    return None


def fight_finished(arcade_run, won, cleared, rng=random):
    """A fight in a challenge's run has ended (see arcade.game_finished): a win brings packs; a loss ends it.
    Returns the prize a win drew (an infinite challenge's), for the Victory screen to show being drawn; or None."""
    run = of(arcade_run)
    if not run:
        return None
    prize = None
    if won:
        from .buffs import EXTRA_PACKS, roll  # weiss.buffs uses this module
        count, rewards = win_reward(run.kind)
        run.packs += count
        drawn = []
        for buff in rewards:
            if buff == "prize":
                buff = prize = rng.choice(INFINITE_PRIZES)
            elif buff == "random":
                buff = roll(1, rng)[0]
            drawn.append(buff)
        for buff in drawn:
            if buff == "extra_packs":  # those needing nothing more happen now, as buffs.grant does them
                run.packs += EXTRA_PACKS
            elif buff == "second_chance":
                run.lives += 1
            else:
                run.rewards = [*run.rewards, {"key": secrets.token_hex(6), "buff": buff, "source": "Victory"}]
        if cleared:
            run.status = ChallengeRun.Status.WON
    elif run.lives:  # a second chance: the fight's there to try again
        run.lives -= 1
    else:
        run.status = ChallengeRun.Status.LOST
        arcade_run.status, arcade_run.finished = ArcadeRun.Status.ABANDONED, timezone.now()
        arcade_run.save(update_fields=["status", "finished"])
    run.save(update_fields=["packs", "rewards", "status", "lives"])
    return prize


def prize_shown(prize):
    """What the slot machine needs: its reel (the prizes there are) and which one it stops on."""
    from .buffs import BUFFS  # weiss.buffs uses this module
    return {"reel": [{"buff": buff, "name": BUFFS[buff].name} for buff in INFINITE_PRIZES],
            "won": INFINITE_PRIZES.index(prize), "packs": INFINITE_WIN_PACKS}


def stop_fighting(run):
    """Take down the room its run is being fought in, if there is one; the run stays where it is."""
    if run.arcade_run_id:
        GameRoom.objects.filter(arcade_run_id=run.arcade_run_id).delete()


def give_up(run):
    """End an active challenge as lost, so the player can keep or discard its deck."""
    stop_fighting(run)
    if run.arcade_run and run.arcade_run.status == ArcadeRun.Status.ACTIVE:
        run.arcade_run.status, run.arcade_run.finished = ArcadeRun.Status.ABANDONED, timezone.now()
        run.arcade_run.save(update_fields=["status", "finished"])
    run.status = ChallengeRun.Status.LOST
    run.save(update_fields=["status"])


def reset(run):
    """Start the challenge again from nothing: the old deck goes, and with it the pool and the run."""
    with transaction.atomic():
        give_up(run)
        if run.deck:
            run.deck.delete()
        run.deck = CardList.objects.create(user=run.user, name=deck_name(run.name), challenge=True)
        run.pool, run.packs, run.opened, run.last_opening, run.rewards, run.lives = {}, start_packs(run.kind), 0, {}, [], 0
        run.arcade_run, run.status, run.started = None, ChallengeRun.Status.ACTIVE, timezone.now()
        run.save()


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
