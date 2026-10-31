"""Express deck building: pick a series and 2 cx combo anchor cards, and a legal deck is built
around them, then every card can be reviewed and swapped.

Cards are drawn at random, by weight: towards the anchors' colors (more strongly if they're all one
color) and traits, and towards whichever of damage and utility the deck is short of. Anchors, and any
card named in an anchor's text, always go in. A card whose cx combo names climaxes the deck doesn't
have is very unlikely to be drawn. A color's level 1 and higher cards only go in once the
deck has 5 level 0 cards of that color to get it started, except backups and cards any color can play.
A climax needs a character or event of its color in the deck, or it could never be played: one
without gives way to more of the climaxes the anchors need.

Damage: power above the average for its level in its set, printed or with its own AUTO or CONT boost.
Utility: an effect that reaches the waiting room or the clock, or targets the opponent's board.
A card can be both; a climax is neither.
"""
import random
import re
from collections import Counter

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import abilities
from .lists import COPY_LIMIT, DECK_GROUPS, DECK_SIZE, EXPRESS_PROMPT, deck_checks, is_climax, sorted_entries
from .models import Card, CardList, CardListEntry
from .views import series_code, summarize_sets, with_image_urls

ANCHORS = 2  # anchor cards to choose (or all there are, in a series with fewer)
CX_COMBO = "【CXCOMBO】"
ANCHOR_COPIES = 4
NAMED_COPIES = 2  # of a character or event an anchor names
CLIMAX_COUNT = next(target for label, target, required, counts in DECK_GROUPS if required)
# The share of the deck's damage and utility cards that should be damage. By default damage/utility
# is 2/3, so 2 parts in 5; a replacement can lean further either way.
DAMAGE_SHARE = {"balanced": 2 / 5, "damage": 3 / 4, "utility": 1 / 8}
COLOR_WEIGHT = 3  # for a card in one of the anchors' colors
ONE_COLOR_WEIGHT = 8  # ...when the anchors are all that one color
TRAIT_WEIGHT = 1.5  # for a card sharing a trait with an anchor
NO_ROLE_WEIGHT = .05  # a card that's neither damage nor utility, against a share of 1
MISSING_COMBO_WEIGHT = .02  # a card whose cx combo's climax isn't in the deck (draw weights can't go below 0)
MIN_LEVEL_ZERO = 5  # copies of level 0 cards of a color before its higher levels are drawn
COPY_WEIGHTS = {1: 1, 2: 2, 3: 2, 4: 3}  # how many copies of a card to add at a time

UTILITY = re.compile(r"\bin your waiting room|from your waiting room|\bclock\b|your opponent's [^.,]*characters?"
                     r"|your opponent's (?:center|back) stage|(?:put|【REVERSE】) that character|the character facing", re.I)


# --- Damage and utility ---------------------------------------------------------------------------------

def walk(steps):
    for step in steps:
        yield step
        yield from walk(step.get("then", []))
        for option in step.get("options", []):
            if isinstance(option, dict):
                yield from walk(option["steps"])


def self_boost(text):
    """The most power a card's own AUTO and CONT abilities can be counted on to add to itself. An
    amount that depends on the board is taken at 2 of whatever it counts."""
    best = 0
    for ability in abilities.parse(text):
        if ability["kind"] == "cont":
            changes = [e for e in ability["effects"] if e["target"]["type"] == "self"]
        elif ability["kind"] == "auto":
            changes = [s for s in walk(ability["steps"]) if s["do"] == "buff" and s["target"] == "self"]
        else:
            continue
        for change in changes:
            amount = change.get("power", 0)
            if change.get("per"):
                amount *= 2
            if change.get("x_stat") == "power" and change.get("x"):
                amount += change["x"].get("times", 1) * 2
            best = max(best, amount)
    return best


def is_utility(card):
    """Whether its effects (not its costs) reach the waiting room or clock, or the opponent's board."""
    if is_climax(card):
        return False
    return bool(UTILITY.search(re.sub(r"\[[^\]]*\]", "", card.description or "")))


def combo_climaxes(card, climax_names):
    """The climaxes this card's cx combo lines name, out of the given (plain) names. Empty for a combo
    that takes any climax."""
    lines = [line for line in abilities.plain_name_lines(card.description) if CX_COMBO in line]
    return {name for name in climax_names if any(f'"{name}"' in line for line in lines)}


def needs_level_zero(card):
    """Whether the level 0 rule applies to this card: level 1 or higher, not a backup (played as a
    counter, whatever the color) and not a card that can be played without its color."""
    if is_climax(card) or card.level is None or card.level < 1:
        return False
    return not any(a["kind"] == "backup" or a.get("color_free", {}).get("self") for a in abilities.parse(card.description))


def power_averages(cards):
    """{(set, level): average printed power} over the characters given."""
    powers = {}
    for card in cards:
        if card.card_type.lower() == "character" and card.level is not None and card.power is not None:
            powers.setdefault((card.expansion_id, card.level), []).append(card.power)
    return {key: sum(values) / len(values) for key, values in powers.items()}


def is_damage(card, averages):
    average = averages.get((card.expansion_id, card.level))
    if average is None or card.card_type.lower() != "character" or card.power is None:
        return False
    return card.power > average or card.power + self_boost(card.description) > average


def series_pool(code, for_cpu=False):
    """One printing of each card name in a series, with `damage` and `utility` set on it. A CPU can
    only play what the game can carry out by itself, so `for_cpu` leaves out cards that need steps
    done by hand (the averages for damage still take in the whole set)."""
    cards = {}
    for card in Card.objects.filter(serial_number__startswith=f"{code}/").order_by("serial_number"):
        cards.setdefault(card.name, card)
    cards = list(cards.values())
    averages = power_averages(cards)
    climaxes = {abilities.plain_name(c.name) for c in cards if is_climax(c)}
    for card in cards:
        card.damage = is_damage(card, averages)
        card.utility = is_utility(card)
        card.combos = combo_climaxes(card, climaxes) if not is_climax(card) else set()
    return [c for c in cards if not abilities.by_hand_parts(c.description)] if for_cpu else cards


def anchor_choices(pool):
    return [c for c in pool if not is_climax(c) and CX_COMBO in (c.description or "")]


def cpu_anchor_choices(code):
    """Anchors for a CPU deck: none that need steps done by hand, nor that name a card that does,
    since a card an anchor names has to go in the deck."""
    whole = series_pool(code)
    usable = series_pool(code, for_cpu=True)
    usable_names = {c.name for c in usable}
    return [a for a in anchor_choices(usable) if all(c.name in usable_names for c in named_in([a], whole)[0])]


def named_in(anchors, pool):
    """(cards in the pool that an anchor's text names, names it uses that aren't in the pool)."""
    names = {abilities.plain_name(c.name): c for c in pool}
    found, missing = {}, set()
    anchor_names = {a.name for a in anchors}
    for anchor in anchors:
        text = abilities.plain_name(anchor.description)
        for plain, card in names.items():
            if f'"{plain}"' in text and card.name not in anchor_names:
                found[card.name] = card
        for name in parsed_names(abilities.parse(anchor.description)):
            if abilities.plain_name(name) not in names:
                missing.add(name)
    return list(found.values()), missing


def parsed_names(node):
    if isinstance(node, dict):
        if "name" in node:
            yield node["name"]
        for key, value in node.items():
            if key != "text":
                yield from parsed_names(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from parsed_names(value)


# --- Drawing cards --------------------------------------------------------------------------------------

class Builder:
    """A deck being put together: card -> copies, and the weights for what to add next."""

    def __init__(self, pool, anchors, rng, share=DAMAGE_SHARE["balanced"], copies=None, known=None):
        self.pool = pool
        self.rng = rng
        self.share = share
        self.colors = {a.color for a in anchors if a.color}
        self.traits = {t for a in anchors for t in re.split(r"[・/]", a.traits or "") if t}
        self.copies = Counter(copies or {})  # card pk -> copies
        self.by_pk = {card.pk: card for card in known or pool}  # `known`: cards it may find in the deck but won't draw

    def room(self, card):
        return COPY_LIMIT - self.copies[card.pk]

    def total(self):
        return sum(self.copies.values())

    def level_zero_copies(self, color):
        return sum(n for pk, n in self.copies.items()
                   if pk in self.by_pk and self.by_pk[pk].level == 0 and self.by_pk[pk].color == color and not is_climax(self.by_pk[pk]))

    def allowed(self, card):
        """The level 0 rule (see needs_level_zero), for a card about to be drawn."""
        if card.level == 3 and self.level_three_room() <= 0:
            return False
        return not needs_level_zero(card) or self.level_zero_copies(card.color) >= MIN_LEVEL_ZERO

    def level_copies(self, level):
        return sum(n for pk, n in self.copies.items() if pk in self.by_pk and self.by_pk[pk].level == level and not is_climax(self.by_pk[pk]))

    def level_three_room(self):
        """How many more level 3s fit: a deck shouldn't have more of them than level 2s."""
        return self.level_copies(2) - self.level_copies(3)

    def strands_color(self, color):
        """Whether this color has higher cards in the deck but too few level 0s now."""
        return self.level_zero_copies(color) < MIN_LEVEL_ZERO and any(
            n and pk in self.by_pk and self.by_pk[pk].color == color and needs_level_zero(self.by_pk[pk]) for pk, n in self.copies.items())

    def missing_combo(self, card):
        """Its cx combo names climaxes and none of them are in the deck."""
        return card.combos and not card.combos & {abilities.plain_name(self.by_pk[pk].name) for pk, n in self.copies.items()
                                                  if n and pk in self.by_pk and is_climax(self.by_pk[pk])}

    def supported(self, color):
        """Whether the deck has a card other than a climax in this color."""
        return any(n and pk in self.by_pk and self.by_pk[pk].color == color and not is_climax(self.by_pk[pk])
                   for pk, n in self.copies.items())

    def role_weight(self, card):
        damage = sum(n for pk, n in self.copies.items() if pk in self.by_pk and self.by_pk[pk].damage)
        utility = sum(n for pk, n in self.copies.items() if pk in self.by_pk and self.by_pk[pk].utility)
        current = damage / (damage + utility) if damage + utility else self.share
        wants_damage = self.share * (2 if current < self.share else .5)
        wants_utility = (1 - self.share) * (2 if current > self.share else .5)
        if card.damage and card.utility:
            return max(wants_damage, wants_utility)
        return wants_damage if card.damage else wants_utility if card.utility else NO_ROLE_WEIGHT

    def weight(self, card):
        weight = 1
        if card.color in self.colors:
            weight *= ONE_COLOR_WEIGHT if len(self.colors) == 1 else COLOR_WEIGHT
        if self.traits & set(re.split(r"[・/]", card.traits or "")):
            weight *= TRAIT_WEIGHT
        if not is_climax(card):
            weight *= self.role_weight(card)
        if self.missing_combo(card):
            weight *= MISSING_COMBO_WEIGHT
        return weight

    def draw(self, candidates):
        candidates = [c for c in candidates if self.room(c) > 0]
        if not candidates:
            return None
        return self.rng.choices(candidates, [self.weight(c) for c in candidates])[0]

    def fill(self, fits, count, level_rule=True):
        """Add up to `count` copies of cards that fit, a few at a time. Returns how many it couldn't."""
        while count > 0:
            card = self.draw([c for c in self.pool if fits(c)])
            if not card:
                break
            wanted = self.rng.choices(list(COPY_WEIGHTS), list(COPY_WEIGHTS.values()))[0]
            added = min(wanted, self.room(card), count)
            if level_rule and card.level == 3:
                added = min(added, self.level_three_room())
            self.copies[card.pk] += added
            count -= added
        return count


def before_high(builder):
    """The level 2 copies there were before the level 2 + 3 group started filling."""
    return builder.level_twos_at_start


def spread(cards, total):
    """`total` copies shared out as evenly as possible, up to the copy limit each."""
    shares = Counter()
    while total > 0 and any(shares[c.pk] < COPY_LIMIT for c in cards):
        for card in cards:
            if total > 0 and shares[card.pk] < COPY_LIMIT:
                shares[card.pk] += 1
                total -= 1
    return shares


def replace_unplayable_climaxes(builder, anchors, required):
    """Swap out any climax with no other card of its color in the deck: first for more of the climaxes
    the anchors name, then ones in the anchors' colors, then any in a color the deck plays. A required
    climax stays. Returns [(old name, new name), ...]; anything with no replacement stays too."""
    named = {c.pk for c in named_in(anchors, builder.pool)[0] if is_climax(c)}
    colors = {a.color for a in anchors}
    climaxes = [c for c in builder.pool if is_climax(c)]
    tiers = [lambda c: c.pk in named, lambda c: c.color in colors, lambda c: True]
    swaps = []
    for old in climaxes:
        if old.name in required or builder.supported(old.color):
            continue
        while builder.copies[old.pk] > 0:
            new = None
            for tier in tiers:
                fits = [c for c in climaxes if tier(c) and builder.room(c) > 0 and builder.supported(c.color)]
                if fits:
                    new = min(fits, key=lambda c: builder.copies[c.pk])  # evens them out, a copy at a time
                    break
            if not new:
                return swaps
            builder.copies[old.pk] -= 1
            builder.copies[new.pk] += 1
            swaps.append((old.name, new.name))
    return swaps


def build_deck(pool, anchors, rng=random):
    """Returns (Builder with the deck in it, names that must stay in it, notes for the player)."""
    notes = []
    builder = Builder(pool, anchors, rng)
    named, missing = named_in(anchors, pool)
    if missing:
        notes.append("Named on your anchors but not in the card database, so left out: " + ", ".join(sorted(missing)) + ".")
    required = [c.name for c in [*anchors, *named]]
    # Anchors first, then what they name. Climaxes share out the 8 slots; every card gets at least one
    # copy, so a long list can't crowd out the rest of the deck's rules.
    named_climaxes = [c for c in named if is_climax(c)]
    if len(named_climaxes) > CLIMAX_COUNT:
        notes.append(f"Your anchors name more than {CLIMAX_COUNT} climaxes; only the first {CLIMAX_COUNT} fit.")
        required = [n for n in required if n not in {c.name for c in named_climaxes[CLIMAX_COUNT:]}]
        named_climaxes = named_climaxes[:CLIMAX_COUNT]
    per_climax = min(COPY_LIMIT, CLIMAX_COUNT // max(len(named_climaxes), 1))
    builder.copies.update(spread(named_climaxes, min(CLIMAX_COUNT, per_climax * len(named_climaxes))))
    for card in anchors:
        builder.copies[card.pk] = ANCHOR_COPIES
    for card in named:
        if not is_climax(card):
            builder.copies[card.pk] = NAMED_COPIES
    # Colors that have to be played get their level 0s now, before the level spread is shared out.
    for color in sorted({c.color for c in anchors if c.color} | {c.color for c in named_climaxes if c.color}
                        | {c.color for c in [*anchors, *named] if needs_level_zero(c)}):
        builder.fill(lambda c: c.level == 0 and c.color == color and not is_climax(c), MIN_LEVEL_ZERO - builder.level_zero_copies(color))
        if builder.level_zero_copies(color) < MIN_LEVEL_ZERO:
            notes.append(f"This series doesn't have {MIN_LEVEL_ZERO} level 0 {color} cards to support your required cards.")
    # Then the rest, group by group: climaxes to the rule, the others to the usual level spread,
    # taking from the biggest groups if what's required has used up more than its share.
    wanting = []
    for label, target, needed, counts in DECK_GROUPS:
        have = sum(n for pk, n in builder.copies.items() if counts(builder.by_pk[pk]))
        wanting.append([counts, max(0, target - have), needed])
    # Required level 3s need as many level 2s beside them, even if that's more than the group's share.
    high_group = wanting[-1]
    high_group[1] = max(high_group[1], -builder.level_three_room())
    while sum(w[1] for w in wanting) > DECK_SIZE - builder.total():
        max(wanting[1:-1] if wanting[1:-1] and max(w[1] for w in wanting[1:-1]) > 0 else wanting[1:], key=lambda w: w[1])[1] -= 1
    builder.level_twos_at_start = builder.level_copies(2)
    for counts, count, needed in wanting:
        fits = (lambda c, counts=counts: counts(c) and builder.allowed(c))
        if counts is high_group[0]:  # level 2s first, if required level 3s are waiting for them
            builder.fill(lambda c: c.level == 2 and builder.allowed(c), min(count, max(0, -builder.level_three_room())))
            count = max(0, count - max(0, builder.level_copies(2) - before_high(builder)))
        short = builder.fill(fits, count)
        if short and needed:
            notes.append(f"This series doesn't have enough climaxes for {CLIMAX_COUNT}; {short} short.")
    # A small series can run out of some level: anything else that isn't a climax makes up the size,
    # keeping to the level 0 rule if it possibly can.
    builder.fill(lambda c: not is_climax(c) and builder.allowed(c), DECK_SIZE - builder.total())
    if builder.total() < DECK_SIZE and any(not is_climax(c) and builder.room(c) > 0 for c in pool):
        notes.append(f"To reach {DECK_SIZE} cards, some colors have higher levels without {MIN_LEVEL_ZERO} level 0s.")
    short = builder.fill(lambda c: not is_climax(c), DECK_SIZE - builder.total(), level_rule=False)
    if short:
        notes.append(f"This series only has enough cards for {DECK_SIZE - short} of the {DECK_SIZE}.")
    replace_unplayable_climaxes(builder, anchors, required)
    stranded = sorted({builder.by_pk[pk].color for pk, n in builder.copies.items()
                       if n and is_climax(builder.by_pk[pk]) and not builder.supported(builder.by_pk[pk].color)})
    if stranded:
        notes.append(f"Some climaxes have no other cards of their color in the deck: {', '.join(stranded)}.")
    return builder, required, notes


def group_of(card):
    return next((i for i, (_, _, _, counts) in enumerate(DECK_GROUPS) if counts(card)), None)


def replace_cards(pool, anchors, copies, required, removing, mode, rng=random, known=None):
    """Swap copies out for new draws. Each new card comes from the same group as the one it replaces
    (so the climax count and the level spread stay as they are), or, if that group has nothing else,
    from any other that isn't climaxes. Every required name keeps at least one copy.

    `copies` and `removing` are {card pk: copies}. Returns (new copies, [(old name, new name), ...]),
    and a copy that has nothing to replace it stays."""
    builder = Builder(pool, anchors, rng, DAMAGE_SHARE[mode], copies, known)
    removed = {builder.by_pk[pk].name for pk in removing if pk in builder.by_pk}
    swaps = []
    for pk, count in removing.items():
        old = builder.by_pk.get(pk)
        if not old:
            continue
        count = min(count, builder.copies[pk] - (1 if old.name in required else 0))
        for _ in range(max(count, 0)):
            builder.copies[pk] -= 1
            # A level 0 that's holding up its color's higher cards can only give way to the same color.
            # So does the last card of a color a required climax needs.
            needed_climax = not is_climax(old) and not builder.supported(old.color) and any(
                n and is_climax(builder.by_pk[p]) and builder.by_pk[p].color == old.color and builder.by_pk[p].name in required
                for p, n in builder.copies.items() if p in builder.by_pk)
            color = old.color if needed_climax or (old.level == 0 and builder.strands_color(old.color)) else None
            # Taking out a level 2 can't leave more level 3s than level 2s.
            level = 2 if old.level == 2 and builder.level_three_room() < 0 else None
            others = [c for c in pool if c.name not in removed and builder.allowed(c) and (not color or c.color == color)
                      and (not level or c.level == level)
                      and (not is_climax(c) or builder.supported(c.color))]
            new = builder.draw([c for c in others if group_of(c) == group_of(old)])
            if not new and not is_climax(old):
                new = builder.draw([c for c in others if not is_climax(c)])
            if not new:
                builder.copies[pk] += 1
                break
            builder.copies[new.pk] += 1
            swaps.append((old.name, new.name))
    swaps += replace_unplayable_climaxes(builder, anchors, required)
    return +builder.copies, swaps


# --- Pages ----------------------------------------------------------------------------------------------

def own_list(request, pk):
    return get_object_or_404(CardList, pk=pk, user=request.user)


def series_choices(for_cpu=False):
    """The series that have at least one anchor to offer: [{code, name, cover, anchors}, ...]."""
    counts = Counter()
    for serial in Card.objects.filter(description__contains=CX_COMBO).exclude(card_type__iexact="climax").values_list("serial_number", flat=True):
        counts[series_code(serial)] += 1
    if for_cpu:
        counts = Counter({code: len(cpu_anchor_choices(code)) for code in counts})
    found = {}
    for summary in sorted(summarize_sets(), key=lambda s: -s["expansion_id"]):
        if counts[summary["code"]] and summary["code"] not in found:
            found[summary["code"]] = {"code": summary["code"], "name": summary["name"], "anchors": counts[summary["code"]],
                                      "cover_serial": summary["cover_serial"]}
    covers = {c.serial_number: c for c in with_image_urls(Card.objects.filter(serial_number__in=[f["cover_serial"] for f in found.values()]))}
    for choice in found.values():
        choice["cover"] = covers.get(choice["cover_serial"])
    return list(found.values())


@weiss_access_required
def express_start(request, pk):
    """Steps 1 and 2: choose a series, then its anchors (posting those builds the deck)."""
    card_list = own_list(request, pk)
    request.session.pop(EXPRESS_PROMPT, None)
    if card_list.entries.exists():
        messages.error(request, "Express building starts from an empty deck, and this one already has cards.")
        return redirect("weiss:list", pk=card_list.pk)
    code = request.POST.get("series") or request.GET.get("series")
    if not code:
        return render(request, "weiss/express_series.html", {"card_list": card_list, "series": series_choices(card_list.reserved_for_cpu)})
    pool = series_pool(code, for_cpu=card_list.reserved_for_cpu)
    choices = cpu_anchor_choices(code) if card_list.reserved_for_cpu else anchor_choices(pool)
    if not choices:
        messages.error(request, "That series has no cx combo cards to build around.")
        return redirect("weiss:list_express", pk=card_list.pk)
    needed = min(ANCHORS, len(choices))
    if request.method == "POST":
        wanted = request.POST.getlist("anchor")
        anchors = [c for c in choices if str(c.pk) in wanted]
        if len(anchors) != needed or len(anchors) != len(set(wanted)):
            messages.error(request, f"Choose {needed} anchor card{'s' if needed != 1 else ''}.")
            return redirect(f"{reverse('weiss:list_express', args=[card_list.pk])}?series={code}")
        builder, required, notes = build_deck(pool, anchors)
        with transaction.atomic():
            CardListEntry.objects.bulk_create(CardListEntry(card_list=card_list, card_id=card, quantity=n)
                                              for card, n in builder.copies.items() if n)
            card_list.is_deck = True
            card_list.cover_card = max(anchors, key=lambda a: a.level or 0)  # the highest level anchor
            card_list.express = {"series": code, "anchors": [a.pk for a in anchors], "required": required}
            card_list.save(update_fields=["is_deck", "cover_card", "express", "updated"])
        for note in notes:
            messages.warning(request, note)
        return redirect("weiss:list_express_review", pk=card_list.pk)
    with_image_urls(choices)
    return render(request, "weiss/express_anchors.html", {"card_list": card_list, "code": code, "choices": choices, "needed": needed})


def role_counts(copies):
    damage = sum(n for card, n in copies if card.damage)
    utility = sum(n for card, n in copies if card.utility)
    both = sum(n for card, n in copies if card.damage and card.utility)
    return {"damage": damage, "utility": utility, "both": both, "neither": sum(n for card, n in copies if not is_climax(card) and not card.damage and not card.utility)}


@weiss_access_required
def express_review(request, pk):
    """Every card in the built deck, one tile per copy, with what's selected to be replaced."""
    card_list = own_list(request, pk)
    if not card_list.express:
        return redirect("weiss:list", pk=card_list.pk)
    roles = {c.pk: c for c in series_pool(card_list.express["series"])}
    entries = sorted_entries(card_list)
    with_image_urls([e.card for e in entries])
    required = set(card_list.express["required"])
    tiles, copies = [], []
    kept = set()
    for entry in entries:
        card = entry.card
        known = roles.get(card.pk)
        card.damage, card.utility = bool(known and known.damage), bool(known and known.utility)
        copies.append((card, entry.quantity))
        for _ in range(entry.quantity):
            locked = card.name in required and card.name not in kept
            kept.add(card.name)
            tiles.append({"card": card, "locked": locked})
    mode = request.GET.get("mode")
    return render(request, "weiss/express_review.html", {
        "card_list": card_list, "tiles": tiles, "deck": deck_checks(entries), "roles": role_counts(copies),
        "mode": mode if mode in DAMAGE_SHARE else "balanced",
    })


@weiss_access_required
@require_POST
def express_replace(request, pk):
    card_list = own_list(request, pk)
    if not card_list.express:
        return redirect("weiss:list", pk=card_list.pk)
    mode = request.POST.get("mode")
    mode = mode if mode in DAMAGE_SHARE else "balanced"
    back = f"{reverse('weiss:list_express_review', args=[card_list.pk])}?mode={mode}"
    removing = Counter()
    for value in request.POST.getlist("replace"):
        if value.isdigit():
            removing[int(value)] += 1
    if not removing:
        messages.error(request, "Select the cards you want to replace first.")
        return redirect(back)
    whole = series_pool(card_list.express["series"])
    pool = series_pool(card_list.express["series"], for_cpu=card_list.reserved_for_cpu)
    anchors = [c for c in whole if c.pk in card_list.express["anchors"]]
    with transaction.atomic():
        card_list = CardList.objects.select_for_update().get(pk=card_list.pk)
        copies = dict(card_list.entries.values_list("card_id", "quantity"))
        # A card added by hand from another printing or series isn't in the pool, so replace_cards leaves it.
        removing =Counter({card: min(n, copies.get(card, 0)) for card, n in removing.items()})
        new, swaps = replace_cards(pool, anchors, copies, set(card_list.express["required"]), removing, mode, known=whole)
        card_list.entries.all().delete()
        CardListEntry.objects.bulk_create(CardListEntry(card_list=card_list, card_id=card, quantity=n) for card, n in new.items())
        card_list.save(update_fields=["updated"])
    if swaps:
        lines = Counter(swaps)
        messages.success(request, "Replaced " + "; ".join(f"{old} → {new_name}" + (f" ×{n}" if n > 1 else "") for (old, new_name), n in lines.items()) + ".")
    else:
        messages.warning(request, "Nothing could be replaced: those cards are required, or there's nothing else that fits.")
    return redirect(back)
