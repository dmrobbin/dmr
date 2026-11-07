"""Augments: what beating an infinite challenge's boss lets a player pick (see docs/infinite-bosses.md).

An augment changes the rest of the player's run, pushing them towards a playstyle. Each pick offers OFFER of them
the player doesn't have yet (settled when the pick is given, see offer), and they keep one. They're the player's
own, in co-op too, where the partner can see them.

Some change the run (deck rules, rewards, losses: see the functions below); the rest change every game the player
plays: those are put on their side of the game when it's dealt (see play.augment_start), and the game's rules read
them from there (see game.augment_stats, game.refresh and game.counter_play).
"""
import random
from dataclasses import dataclass

from .game import DEVOTION_POWER, GLASS_CANNON_SOUL, LOW_LEVEL_POWER
from .lists import CLIMAX_COUNT as CLIMAX_LIMIT, COPY_LIMIT

OFFER = 3  # augments a pick offers
OVERLOAD_CLIMAXES = 10  # ...with Climax Overload
HIGHLANDER_COPIES = 2  # the most copies of a card a Highlander deck can run...
HIGHLANDER_PACKS = 2  # ...and the packs each win brings it
RESERVES = 2  # cards in the stock Deep Reserves starts each game with
HEAD_START = 2  # cards in the clock every CPU starts with against Head Start


@dataclass(frozen=True)
class Augment:
    id: str
    name: str
    description: str
    playstyle: str
    coop_only: bool = False
    stacks: bool = False  # can be picked again
    in_game: bool = False  # changes the player's games (see play.augment_start)


AUGMENTS = {augment.id: augment for augment in (
    Augment("climax_overload", "Climax Overload", f"Your deck can run {CLIMAX_LIMIT} to {OVERLOAD_CLIMAXES} climaxes instead of exactly {CLIMAX_LIMIT}, "
            "and each win also gives a climax pick.", "Trigger-heavy, big swings"),
    Augment("deep_reserves", "Deep Reserves", f"You start each game with {RESERVES} cards in your stock.",
            "Expensive events and costly abilities early", in_game=True),
    Augment("devotion", "Devotion", f"If every card in your deck is one color, your characters get +{DEVOTION_POWER} power. "
            "The win prize lands on a color pack more often.", "Mono-color", in_game=True),
    Augment("head_start", "Head Start", f"Every CPU starts each game with {HEAD_START} cards in its clock.",
            "Aggro: close games out fast", in_game=True),
    Augment("clean_refresh", "Clean Refresh", "Your first refresh in each game deals no refresh damage.",
            "Long control games, thinning the deck", in_game=True),
    Augment("highlander", "Highlander", f"Your deck can't run more than {HIGHLANDER_COPIES} copies of any card. "
            f"In exchange, each win gives {HIGHLANDER_PACKS} extra packs.", "Variety, adapting to the pool"),
    Augment("glass_cannon", "Glass Cannon", f"Your characters get +{GLASS_CANNON_SOUL} soul, but each of your losses counts twice: "
            "two second chances, or two on the co-op loss counter.", "All-in aggression, high risk", in_game=True),
    Augment("low_level_army", "Low-Level Army", f"Your level 0 characters get +{LOW_LEVEL_POWER} power.", "Swarming with cheap cards", in_game=True),
    Augment("counter_specialist", "Counter Specialist", "Your counter cards cost 1 less stock (to a minimum of 0).",
            "Defense, outlasting the CPU", in_game=True),
    Augment("lifeline", "Lifeline", "The pair's loss limit goes up by 1. It stacks.", "Safety, room to experiment",
            coop_only=True, stacks=True),
)}


def has(run, augment_id):
    return bool(run) and augment_id in (run.augments or [])


def shown(augment_id):
    augment = AUGMENTS[augment_id]
    return {"id": augment.id, "name": augment.name, "text": augment.description, "playstyle": augment.playstyle}


def of(run):
    """The augments this player has picked, for showing: [shown(id)], once each, with "count" for those taken twice."""
    counts = {}
    for augment_id in run.augments or []:
        if augment_id in AUGMENTS:
            counts[augment_id] = counts.get(augment_id, 0) + 1
    return [{**shown(augment_id), "count": n} for augment_id, n in counts.items()]


def offer(run, rng=random):
    """OFFER augments this player could pick, at random: not one they have (unless it stacks), and in solo, none
    that are co-op only."""
    found = sorted(augment.id for augment in AUGMENTS.values()
                   if (run.coop_id or not augment.coop_only) and (augment.stacks or augment.id not in (run.augments or [])))
    return rng.sample(found, min(OFFER, len(found)))


def take(run, augment_id):
    """The player picks this augment (not saved here, but what it changes at once is)."""
    run.augments = [*(run.augments or []), augment_id]
    if augment_id == "lifeline" and run.coop_id:
        pair = run.coop
        pair.loss_limit += 1
        pair.version += 1
        pair.save(update_fields=["loss_limit", "version"])


# The run -----------------------------------------------------------------------------------------------------------

def climax_limit(run):
    return OVERLOAD_CLIMAXES if has(run, "climax_overload") else CLIMAX_LIMIT


def copy_limit(run):
    return HIGHLANDER_COPIES if has(run, "highlander") else COPY_LIMIT


def win_extras(run):
    """(packs, rewards) a win brings besides its usual reward, from the player's augments."""
    packs = HIGHLANDER_PACKS if has(run, "highlander") else 0
    rewards = ["climax_pick"] if has(run, "climax_overload") else []
    return packs, rewards


def loss_cost(run):
    """How many times a loss counts: twice with Glass Cannon."""
    return 2 if has(run, "glass_cannon") else 1


def prizes(run, prizes):
    """The prizes a win's prize is drawn from: with Devotion, a color pack twice as likely."""
    return (*prizes, "color_pack") if has(run, "devotion") and "color_pack" in prizes else prizes


# The game ----------------------------------------------------------------------------------------------------------

def in_game(run):
    """The augments that change this player's games, as their side of a game has them (see play.augment_start)."""
    return [augment_id for augment_id in dict.fromkeys(run.augments or []) if augment_id in AUGMENTS and AUGMENTS[augment_id].in_game]


def mono_color(cards):
    """Whether these cards (Card objects, or their details) are all one color."""
    colors = {getattr(card, "color", None) if not isinstance(card, dict) else card.get("color") for card in cards}
    colors.discard(None)
    colors.discard("")
    return len(colors) <= 1
