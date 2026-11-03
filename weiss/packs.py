"""Booster packs: what a pack of one set holds, and opening them.

Everything about the distribution is in the tables below: how grand each rarity's reveal is (`GRADES`) and the
slots of a pack with their odds (`PACK`), so packs can be retuned without touching the code that uses them.

A card's rarity here is its printed one (`Card.rarity`) unless staff have set `Card.pack_rarity` in the admin.
Refreshing the cards from the site rewrites `rarity` but leaves `pack_rarity` alone, so that's where changes go.

Nothing here touches a request, so other features can open packs too:

    pool = Pool.for_set(expansion_id)
    for pull in open_pack(pool):
        pull.card, pull.rarity, pull.grade
"""
import random
import re
from dataclasses import dataclass

from django.urls import reverse

from .models import Card

# How grand a rarity's reveal is: 0 plain, up to 5 for the rarest pulls. A rarity not listed is some special foil.
GRADES = {
    "C": 0, "CC": 0, "U": 0,
    "R": 1, "CR": 1,
    "RR": 2, "RR+": 2,
    "RRR": 3, "SR": 3,
    "SR⁑": 4, "SR⁂": 4, "SP": 4, "OFR": 4, "HYR": 4, "AGR": 4,
    "SSP": 5, "SEC": 5,
}
SPECIAL_GRADE = 4
GRADE_NAMES = ("Common", "Rare", "Double rare", "Foil", "Special", "Secret")

NOT_IN_PACKS = {"", "PR", "TD", "TD+"}  # promos and trial deck cards

OTHER = "other"  # in a slot's odds: any rarity of the set that no slot names, such as a set's own special foil


@dataclass(frozen=True)
class Slot:
    name: str
    count: int
    odds: tuple  # weight tables, tried in turn: the first naming a rarity this set has is used


# An 8-card pack: four commons, an uncommon, a climax, a rare and a foil. Box odds work out at about
# 10 R : 4 RR : 2 CR in the rare slot, and an SP every box or so, an SSP or SEC every few.
PACK = (
    Slot("Common", 4, ({"C": 1},)),
    Slot("Uncommon", 1, ({"U": 1}, {"C": 1})),
    Slot("Climax", 1, ({"CC": 1}, {"CR": 1}, {"C": 1})),
    Slot("Rare", 1, ({"R": 10, "RR": 4, "CR": 2}, {"U": 1})),
    Slot("Foil", 1, ({"SR": 70, "RRR": 13, "SP": 6, "SR⁑": 3, "SR⁂": 3, "SSP": 1.5, "SEC": 1, OTHER: 1}, {"RR": 1}, {"R": 1})),
)
PACK_SIZE = sum(slot.count for slot in PACK)
NAMED = {rarity for slot in PACK for table in slot.odds for rarity in table if rarity != OTHER}


def normalize(rarity):
    """'SR ⁑' and 'SR⁑' are one rarity."""
    return re.sub(r"\s+", "", rarity or "").upper()


def rarity_of(card):
    return normalize(card.pack_rarity or card.rarity)


def grade_of(rarity):
    return GRADES.get(rarity, SPECIAL_GRADE)


@dataclass(frozen=True)
class Pull:
    card: Card
    rarity: str
    grade: int
    slot: str

    def as_dict(self):
        """What the opening screen needs to show it."""
        card = self.card
        return {"id": card.pk, "name": card.name, "serial": card.serial_number, "type": card.card_type,
                "rarity": self.rarity, "grade": self.grade, "slot": self.slot,
                "image": reverse("weiss:card_image", args=[card.pk]), "url": reverse("weiss:card", args=[card.pk])}


class Pool:
    """A set's cards that come in packs, by rarity."""

    def __init__(self, cards):
        self.by_rarity = {}
        for card in cards:
            rarity = rarity_of(card)
            if rarity not in NOT_IN_PACKS:
                self.by_rarity.setdefault(rarity, []).append(card)

    @classmethod
    def for_set(cls, expansion_id):
        return cls(Card.objects.filter(expansion_id=expansion_id).order_by("serial_number"))

    def __bool__(self):
        return bool(self.by_rarity)

    @property
    def set_name(self):
        return next(iter(self.by_rarity.values()))[0].expansion if self else ""

    def odds(self, slot):
        """[(rarity, weight)] for a slot: its first table this set has any of."""
        for table in slot.odds:
            found = [(rarity, weight) for rarity, weight in table.items() if rarity != OTHER and rarity in self.by_rarity]
            if OTHER in table:
                found += [(rarity, table[OTHER]) for rarity in self.by_rarity if rarity not in NAMED]
            if found:
                return found
        return [(rarity, 1) for rarity in self.by_rarity]  # a set none of the tables fit: anything it has

    def draw(self, slot, rng=random):
        rarities, weights = zip(*self.odds(slot))
        rarity = rng.choices(rarities, weights)[0]
        return Pull(rng.choice(self.by_rarity[rarity]), rarity, grade_of(rarity), slot.name)


def open_pack(pool, rng=random):
    """One pack's pulls, in the order they're revealed: the best last."""
    pulls = [pool.draw(slot, rng) for slot in PACK for _ in range(slot.count)]
    return sorted(pulls, key=lambda pull: pull.grade)


def open_packs(pool, count, rng=random):
    return [open_pack(pool, rng) for _ in range(count)]


def pack_sets():
    """[{"id", "name", "cards"}] for each set that can make packs, newest first."""
    sets = {}
    for expansion_id, name, rarity, pack_rarity in Card.objects.exclude(expansion_id=None) \
            .values_list("expansion_id", "expansion", "rarity", "pack_rarity"):
        if normalize(pack_rarity or rarity) not in NOT_IN_PACKS:
            entry = sets.setdefault(expansion_id, {"id": expansion_id, "name": name, "cards": 0})
            entry["cards"] += 1
    return sorted(sets.values(), key=lambda entry: -entry["id"])
