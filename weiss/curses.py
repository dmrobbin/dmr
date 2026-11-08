"""Curses: what beating an infinite challenge's boss makes a player take, besides an augment (see docs/infinite-bosses.md).

The longer a run goes, the stronger a player's deck gets; curses keep the CPUs up with it. Each boss beaten offers
OFFER of them (settled when the pick is given, see offer), and the player has to take one before their next fight
(see challenge.curse_due). They stack, the same curse included: every pick makes the rest of the run harder.

Every curse makes the CPUs the player faces stronger, and never the player weaker, so a curse never just cancels
out an augment: augments build the player up, curses build the enemy up. Each changes the rules, never a card, so it
works whatever deck the CPU has. A boss fight carries the whole stack; any other fight carries half of it, rounded
down (see strengths). Those that change how a game starts do so when it's dealt (see play.curse_start); the rest are
put on the CPU's side of the game, and the game's rules read them from there (see game.curse_stats, game.refresh
and game.heal). A game between two players (a co-op vs. battle) has none.
"""
import random
from collections import Counter
from dataclasses import dataclass

OFFER = 3  # curses a pick offers
MOST_HAND = 4  # the most cards a curse adds to a starting hand


@dataclass(frozen=True)
class Curse:
    id: str
    name: str
    text: str  # what it does at strength {n}
    step: int = 1  # the strength each pick adds
    side: str = ""  # "cpu" for one put on the CPU's side of the game as {id: strength}; "" for one dealt at the start

    def said(self, n):
        return self.text.format(n=n, s="" if n == 1 else "s", es="" if n == 1 else "es")


CURSES = {curse.id: curse for curse in (
    Curse("iron_skin", "Iron Skin", "CPU characters get +{n} power.", step=1000, side="cpu"),
    Curse("fury", "Fury", "CPU characters get +{n} soul.", side="cpu"),
    Curse("hoard", "Hoard", "The CPU starts each game with {n} more card{s} in its stock."),
    Curse("deep_pockets", "Deep Pockets", "The CPU starts each game with {n} more card{s} in its hand."),
    Curse("second_wind", "Second Wind", "The CPU's first {n} refresh{es} in each game deal no refresh damage.", side="cpu"),
    Curse("bulwark", "Bulwark", "CPU characters get +{n} power while they're front attacked.", step=2000, side="cpu"),
    Curse("recovery", "Recovery", "At the start of each of its turns, the CPU heals {n} damage: the top of its clock goes to its waiting room.", side="cpu"),
)}


def offer(rng=random):
    """OFFER different curses, at random: any of them, those the player has already taken too (they stack)."""
    return rng.sample(sorted(CURSES), min(OFFER, len(CURSES)))


def take(run, curse_id):
    """The player takes this curse (not saved here)."""
    run.curses = [*(run.curses or []), curse_id]


def strengths(run, boss):
    """{curse id: strength} this player's fights carry: the whole stack against a boss, half of it (rounded down)
    against anyone else. A curse at 0 is left out."""
    found = {}
    for curse_id, count in Counter(run.curses or []).items():
        if curse_id in CURSES:
            n = count * CURSES[curse_id].step
            if (n := n if boss else n // 2):
                found[curse_id] = n
    return found


def shown(curse_id, n=None):
    curse = CURSES[curse_id]
    return {"id": curse.id, "name": curse.name, "text": curse.said(curse.step if n is None else n)}


def of(run):
    """The curses this player has taken, for showing: [shown(id)], once each, with "count" (times taken) and what
    it does against a boss ("text") and against anyone else ("ordinary"; "" for nothing yet)."""
    bosses, others = strengths(run, True), strengths(run, False)
    counts = Counter(c for c in run.curses or [] if c in CURSES)
    return [{**shown(curse_id, bosses[curse_id]), "count": count,
             "ordinary": CURSES[curse_id].said(others[curse_id]) if curse_id in others else ""}
            for curse_id, count in counts.items()]


def for_game(run, boss):
    """What this player's curses give the CPU in a game: ({id: strength} put on its side, {id: strength} of those
    dealt at the start, see play.curse_start)."""
    cpu, start = {}, {}
    for curse_id, n in strengths(run, boss).items():
        (cpu if CURSES[curse_id].side == "cpu" else start)[curse_id] = n
    return cpu, start
