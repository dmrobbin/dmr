"""Express deck building: pick a series and 2 cx combo anchor cards, and a legal deck is built
around them, then every card can be reviewed and swapped.

Above every rule but the deck's size: a card whose text names another card by its full name only goes in
with that card. A build brings the named card in, a copy in place of one of the commonest of its level,
or if it can't (wrong color, no room, a climax the deck doesn't have) leaves the card naming it out. A
replacement only takes cards whose named cards are in the deck, and replacing a named card replaces
whatever names it too.

Anchors, and any card named in an anchor's text, always go in, with the climaxes the anchors name
taking as many of the climax slots as they can. Next come the deck's synergy cards: every card in the
deck's colors that names an anchor or a climax in the deck, as far as each level's share allows.

The rest are drawn at random, by weight: towards synergy, the anchors' characters (more strongly
for one both anchors feature, and more again if the deck is named after them), the anchors' colors
(more strongly if they're all one color) and traits, and towards whichever of damage and utility the deck is short of,
with cards that are only utility scarcer the higher their level. A card with a cx combo naming neither
an anchor nor a climax in the deck is only drawn if nothing else fits. An initial build holds at most 3 backups and events
together, and few copies of high level cards. A color's level 1 and higher cards only go in once the
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
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import abilities
from .card_images import names_in_card
from .lists import COPY_LIMIT, DECK_GROUPS, copy_limit, DECK_SIZE, EXPRESS_PROMPT, SESSION_KEY, deck_checks, is_climax, sorted_entries
from .models import Card, CardList, CardListEntry
from .views import series_code, summarize_sets, with_image_urls

ANCHORS = 2  # anchor cards to choose (or all there are, in a series with fewer)
CX_COMBO = "【CXCOMBO】"
ANCHOR_COPIES = 4
LEVEL_THREE_ANCHOR_COPIES = 3
NAMED_COPIES = 2  # of a character or event an anchor names
CLIMAX_COUNT = next(target for label, target, required, counts in DECK_GROUPS if required)
PICK_RESULTS = 48  # cards shown for a search when choosing one by hand
PICK_SCAN = 2000  # cards read to find them: a very broad search just stops early
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
# Low levels are needed too early to wait for, so they want more copies than high ones do.
LOW_LEVEL_COPY_WEIGHTS = {1: 1, 2: 3, 3: 4, 4: 5}
HIGH_LEVEL_COPY_WEIGHTS = {1: 1, 2: 5, 3: 2}
HIGH_LEVEL_COPIES = max(HIGH_LEVEL_COPY_WEIGHTS)  # the most of a level 2 or 3 card an initial build draws
SUPPORT_LIMIT = 3  # backups and events together, in an initial build
SYNERGY_WEIGHT = 10  # for a card naming an anchor or a climax in the deck
CHARACTER_WEIGHT = 3  # for a card featuring a character an anchor features; doubled if both do, and again if the deck is named after them
FOCUS_WEIGHT = 60  # instead, with "character focus" on, for such a card in the deck's colors: picked over others whenever it can be
FILLER_COPY_WEIGHTS = {1: 2, 2: 3}  # copies at a time, in an initial build, of a card with no tie to the anchors or climaxes
FILLER_COPY_LIMIT = 3  # ...and the most of one, so the rest of the deck has some variety
PURE_UTILITY_WEIGHT = {0: 1.5, 1: 1, 2: .5, 3: .25}  # by level, for a card that's utility and not damage

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
    lines = abilities.combo_lines(card.description)
    return {name for name in climax_names if any(f'"{name}"' in line for line in lines)}


def is_support(card):
    """A backup or an event: there to help the characters, so a deck only wants a few."""
    return card.card_type.lower() == "event" or any(a["kind"] == "backup" for a in abilities.parse(card.description))


def characters_in(name):
    """The characters a card's name features, as lower case names: '"Cleanup" Levi' -> ['levi']."""
    return [character.lower() for character in names_in_card(name)]


def features(card, character):
    """Whether a card's name features this character, as whole words: "Eren Titan" features Eren."""
    return any(re.search(rf"(?<!\w){re.escape(character)}(?!\w)", name) for name in characters_in(card.name))


def character_weights(anchors, deck_name=""):
    """{character: weight} for the characters the anchors feature."""
    counts = Counter(character for anchor in anchors for character in set(characters_in(anchor.name)))
    weights = {}
    for character, count in counts.items():
        weight = CHARACTER_WEIGHT * (2 if count > 1 else 1)
        if re.search(rf"(?<!\w){re.escape(character)}(?!\w)", (deck_name or "").lower()):
            weight *= 2
        weights[character] = weight
    return weights


def anchor_copies(card):
    return LEVEL_THREE_ANCHOR_COPIES if card.level == 3 else ANCHOR_COPIES


def mentions(card, names):
    """Whether this card's text names one of these (plain) names, in full or as "with X in its name"."""
    text = abilities.plain_name(card.description)
    parts = re.findall(r'with "([^"]+)"', text)
    return any(f'"{name}"' in text or any(part in name for part in parts) for name in names)


NAME_PART = re.compile(r'with "[^"]+" in (?:its|their) (?:card )?names?', re.I)  # any card with that in its name will do


def references(card, names):
    """The card names, out of these (plain) names, that this card's text quotes in full, its own aside:
    '... for each of your other cards named "The Younger Twin, Rem"' references that card."""
    text = NAME_PART.sub("", abilities.plain_name(card.description))
    own = abilities.plain_name(card.name)
    return {name for name in names if name != own and f'"{name}"' in text}


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
    names = {abilities.plain_name(c.name) for c in cards}
    for card in cards:
        card.damage = is_damage(card, averages)
        card.utility = is_utility(card)
        card.combos = combo_climaxes(card, climaxes) if not is_climax(card) else set()
        card.refs = references(card, names)  # before a CPU's pool drops some: naming a card it can't play still counts
    return [c for c in cards if not abilities.by_hand_parts(c.description)] if for_cpu else cards


def anchor_choices(pool):
    """The cards with a climax combo: marked 【CXCOMBO】, or on older cards, worded as one (see abilities.combo_lines)."""
    return [c for c in pool if not is_climax(c) and abilities.has_combo(c.description)]


def cpu_anchor_choices(code):
    """Anchors for a CPU deck: none that need steps done by hand, nor that name a card that does,
    since a card an anchor names has to go in the deck."""
    return cpu_usable_anchors(series_pool(code))


def cpu_usable_anchors(cards):
    """cards: one printing of each name in a series. Only anchors and what they name get read, which is why
    the series menu can afford to do this for every series."""
    playable = {}

    def can_play(card):
        if card.name not in playable:
            playable[card.name] = not abilities.by_hand_parts(card.description)
        return playable[card.name]

    return [a for a in anchor_choices(cards) if can_play(a) and all(can_play(c) for c in named_in([a], cards)[0])]


cpu_counts_memo = (None, None)  # (what the cards looked like, the counts): it's every series' anchors, so it takes a while


def cpu_anchor_counts():
    """{series code: anchors a CPU deck can use}, for the series menu."""
    global cpu_counts_memo
    version = Card.objects.aggregate(Count("pk"), Max("updated"))
    if cpu_counts_memo[0] == version:
        return cpu_counts_memo[1]
    by_series = {}
    for card in Card.objects.only("name", "serial_number", "description", "card_type").order_by("serial_number"):
        by_series.setdefault(series_code(card.serial_number), {}).setdefault(card.name, card)
    counts = Counter({code: len(cpu_usable_anchors(list(cards.values()))) for code, cards in by_series.items()})
    cpu_counts_memo = (version, counts)
    return counts


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

    def __init__(self, pool, anchors, rng, share=DAMAGE_SHARE["balanced"], copies=None, known=None, deck_name="", focus=False):
        self.pool = pool
        self.rng = rng
        self.share = share
        self.colors = {a.color for a in anchors if a.color}
        self.traits = {t for a in anchors for t in re.split(r"[・/]", a.traits or "") if t}
        self.copies = Counter(copies or {})  # card pk -> copies
        self.by_pk = {card.pk: card for card in known or pool}  # `known`: cards it may find in the deck but won't draw
        self.anchor_names = {abilities.plain_name(a.name) for a in anchors}
        self.characters = character_weights(anchors, deck_name)
        self.focus = focus  # "character focus": the anchors' characters over anything else
        self.named_names = set()  # what the anchors name (see build_deck)
        self.initial = False  # an initial build also keeps to the limits on copies and support cards
        self.names = {abilities.plain_name(c.name) for c in self.by_pk.values()}
        self.by_name = {abilities.plain_name(c.name): c for c in pool}  # what a named card can be brought in as
        self.banned = set()  # names taken out for naming what couldn't come in: not drawn again
        self.forced = set()  # names brought in for a required card, so required in turn (see bring_references)
        self.references_rule = True  # off only as the last resort for the deck's size

    def refs(self, card):
        """The cards this one names (see references)."""
        if getattr(card, "refs", None) is None:
            card.refs = references(card, self.names)
        return card.refs

    def deck_names(self):
        return {abilities.plain_name(self.by_pk[pk].name) for pk, n in self.copies.items() if n and pk in self.by_pk}

    def deck_cards(self):
        return [self.by_pk[pk] for pk, n in sorted(self.copies.items()) if n and pk in self.by_pk]

    def missing_refs(self, card):
        return self.refs(card) - self.deck_names()

    def refs_ok(self, card, bringing=frozenset()):
        """The rule above the others: a card naming another card only goes in with that card. A replacement
        needs what it names in the deck already; an initial build can bring it in (see keep_references),
        if it could be drawn itself. `bringing`: names on their way in already, as two cards can name each other."""
        if not self.references_rule:
            return True
        bringing = bringing | {abilities.plain_name(card.name)}
        for name in self.missing_refs(card) - bringing:
            ref = self.by_name.get(name)
            if not self.initial or not ref or is_climax(ref) or ref.name in self.banned or not self.allowed(ref) \
                    or (is_support(ref) and self.support_room() <= 0) or not self.refs_ok(ref, bringing):
                return False
        return True

    def referenced(self, card):
        """Whether a card in the deck names this one."""
        name = abilities.plain_name(card.name)
        return any(name in self.refs(other) for other in self.deck_cards() if other.pk != card.pk)

    def flaws(self, card):
        """What's wrong with the deck that taking copies of this card out could cause: a color stranded below
        its level 0s, more level 3s than 2s, too many support cards, and, once it's gone, a climax left
        without its color or a card naming it left without it."""
        flaws = {"level 3s"} if self.level_three_room() < 0 else set()
        if self.strands_color(card.color):
            flaws.add("level 0s")
        if self.initial and self.support_room() < 0:
            flaws.add("support")
        if self.copies[card.pk] <= 0 and self.referenced(card):
            flaws.add("named")
        if self.copies[card.pk] <= 0 and not self.supported(card.color) and any(
                n and pk in self.by_pk and is_climax(self.by_pk[pk]) and self.by_pk[pk].color == card.color for pk, n in self.copies.items()):
            flaws.add("climax color")
        return flaws

    def room(self, card):
        limit = HIGH_LEVEL_COPIES if self.initial and (card.level or 0) >= 2 else COPY_LIMIT
        if self.initial and self.is_filler(card):
            limit = min(limit, FILLER_COPY_LIMIT)
        return limit - self.copies[card.pk]

    def climax_mentions(self):
        """The names the deck's climaxes' text quotes."""
        return {name for pk, n in self.copies.items() if n and pk in self.by_pk and is_climax(self.by_pk[pk])
                for name in re.findall(r'"([^"]+)"', abilities.plain_name(self.by_pk[pk].description))}

    def is_filler(self, card):
        """Neither an anchor nor named by one, with no text naming an anchor, a climax in the deck or
        what a climax names: a card the deck just needs some of, so it's spread over more of them."""
        name = abilities.plain_name(card.name)
        if is_climax(card) or name in self.anchor_names or name in self.named_names or self.focused(card):
            return False
        return not self.has_synergy(card) and not mentions(card, self.climax_mentions() - {name})

    def support_room(self):
        return SUPPORT_LIMIT - sum(n for pk, n in self.copies.items() if pk in self.by_pk and is_support(self.by_pk[pk]))

    def climax_names(self):
        return {abilities.plain_name(self.by_pk[pk].name) for pk, n in self.copies.items() if n and pk in self.by_pk and is_climax(self.by_pk[pk])}

    def has_synergy(self, card, names=None):
        """Whether its text names an anchor or a climax in the deck."""
        names = self.anchor_names | self.climax_names() if names is None else names
        return mentions(card, names - {abilities.plain_name(card.name)})

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

    def dead_combo(self, card, names):
        """It has a cx combo for a particular climax, and names neither an anchor nor a climax in the deck.
        A combo that takes any climax still works, whatever the deck has."""
        lines = abilities.combo_lines(card.description)
        return bool(lines) and all('"' in line for line in lines) and not self.has_synergy(card, names)

    def role_weight(self, card):
        damage = sum(n for pk, n in self.copies.items() if pk in self.by_pk and self.by_pk[pk].damage)
        utility = sum(n for pk, n in self.copies.items() if pk in self.by_pk and self.by_pk[pk].utility)
        current = damage / (damage + utility) if damage + utility else self.share
        wants_damage = self.share * (2 if current < self.share else .5)
        wants_utility = (1 - self.share) * (2 if current > self.share else .5)
        if card.damage and card.utility:
            return max(wants_damage, wants_utility)
        if card.utility and not card.damage:
            return wants_utility * PURE_UTILITY_WEIGHT.get(card.level, 1)
        return wants_damage if card.damage else NO_ROLE_WEIGHT

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
        if self.has_synergy(card):
            weight *= SYNERGY_WEIGHT
        return weight * self.character_weight(card)

    def focused(self, card):
        """With character focus, whether this is one of the cards the deck is themed on."""
        return self.focus and (card.color in self.colors or not self.colors) and any(features(card, c) for c in self.characters)

    def character_weight(self, card):
        """The most of the anchors' characters' weights this card has: one character at most counts. With
        character focus, a card in the deck's colors featuring one is all but certain to be picked first."""
        weights = [weight for character, weight in self.characters.items() if features(card, character)]
        if self.focused(card):
            return FOCUS_WEIGHT * max(weights) / CHARACTER_WEIGHT
        return max(weights, default=1)

    def draw(self, candidates):
        candidates = [c for c in candidates if self.room(c) > 0 and not (self.initial and is_support(c) and self.support_room() <= 0)
                      and c.name not in self.banned and self.refs_ok(c)]
        if not candidates:
            return None
        names = self.anchor_names | self.climax_names()
        candidates = [c for c in candidates if not self.dead_combo(c, names)] or candidates
        return self.rng.choices(candidates, [self.weight(c) for c in candidates])[0]

    def fill(self, fits, count, level_rule=True):
        """Add up to `count` copies of cards that fit, a few at a time. Returns how many it couldn't."""
        while count > 0:
            card = self.draw([c for c in self.pool if fits(c)])
            if not card:
                break
            added = min(self.copies_to_add(card), self.room(card), count)
            if level_rule and card.level == 3:
                added = min(added, self.level_three_room())
            self.copies[card.pk] += added
            count -= added
        return count

    def copies_to_add(self, card):
        """How many copies of a card to add at a time, which in an initial build depends on its level."""
        weights = COPY_WEIGHTS
        if self.initial and not is_climax(card):
            weights = HIGH_LEVEL_COPY_WEIGHTS if (card.level or 0) >= 2 else FILLER_COPY_WEIGHTS if self.is_filler(card) else LOW_LEVEL_COPY_WEIGHTS
        wanted = self.rng.choices(list(weights), list(weights.values()))[0]
        return min(wanted, self.support_room()) if self.initial and is_support(card) else wanted


def add_synergy(builder, colors, levels):
    """Put in every card of the deck's colors at these levels that names an anchor or a climax in the
    deck, those naming an anchor first, up to what each level's share has left."""
    anchors, climaxes = builder.anchor_names, builder.climax_names()
    found = [c for c in builder.pool if c.level in levels and not is_climax(c) and c.color in colors
             and not builder.copies[c.pk] and builder.has_synergy(c, anchors | climaxes) and builder.refs_ok(c)]
    builder.rng.shuffle(found)
    found.sort(key=lambda c: (c.level, not builder.has_synergy(c, anchors)))
    for card in found:
        target, counts = next((target, counts) for _, target, _, counts in DECK_GROUPS if counts(card))
        share = target - sum(n for pk, n in builder.copies.items() if counts(builder.by_pk[pk]))
        if share <= 0 or not builder.allowed(card) or (is_support(card) and builder.support_room() <= 0):
            continue
        added = min(builder.copies_to_add(card), builder.room(card), share)
        if card.level == 3:
            added = min(added, builder.level_three_room())
        builder.copies[card.pk] += added


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


def swap_in(builder, ref, donors, strict):
    """A copy of `ref` in place of one of the first donor that can give it up: `strict`, without making the
    deck any worse (see Builder.flaws; a climax just mustn't lose the last copy of one that's named)."""
    for donor in donors:
        before = builder.flaws(donor)
        builder.copies[donor.pk] -= 1
        builder.copies[ref.pk] += 1
        if not strict or (builder.copies[donor.pk] or not builder.referenced(donor) if is_climax(ref) else builder.flaws(donor) <= before):
            return True
        builder.copies[donor.pk] += 1
        builder.copies[ref.pk] -= 1
    return False


def bring_references(builder, card, required, force=False):
    """Put in a copy of each card this one names that's missing, each in place of a copy of the most plentiful
    card of its level group that can give one up. `force`, for a required card, which can't come out instead:
    from any group, whatever rules that bends, and a climax it names comes in for a copy of the commonest
    climax that isn't required, or failing that one that is, if the deck plays its color (one it doesn't could never be played). What a required card brings
    in counts as required too. Returns whether it could; if not, the deck is as it was."""
    saved, forced = Counter(builder.copies), set(builder.forced)
    for name in sorted(builder.missing_refs(card)):
        ref = builder.by_name.get(name)
        if not ref or (ref.name in builder.banned and not force) or builder.room(ref) <= 0 or not (force or builder.allowed(ref)) \
                or (is_climax(ref) and not (force and builder.supported(ref.color))):
            builder.copies, builder.forced = saved, forced
            return False
        if is_climax(ref):
            donors = sorted((c for c in builder.deck_cards() if is_climax(c) and c.pk != ref.pk and (builder.copies[c.pk] > 1 or c.name not in required)),
                            key=lambda c: (c.name in required, -builder.copies[c.pk], c.pk))
        else:
            donors = sorted((c for c in builder.deck_cards() if c.pk not in (ref.pk, card.pk) and not is_climax(c) and c.name not in required
                             and (force or group_of(c) == group_of(ref))),
                            key=lambda c: (group_of(c) != group_of(ref), -builder.copies[c.pk], c.pk))
        # A donor that leaves the deck sound if there is one; only when forced, failing that, any.
        if not (swap_in(builder, ref, donors, strict=True) or force and not is_climax(ref) and swap_in(builder, ref, donors, strict=False)):
            builder.copies, builder.forced = saved, forced
            return False
        if force:
            builder.forced.add(ref.name)
            builder.banned.discard(ref.name)
    return True


def take_out(builder, card):
    """Every copy of this card out for good, made up with others of its level group (its color first),
    then anything else. Returns how many copies nothing could make up."""
    count = builder.copies[card.pk]
    builder.copies[card.pk] = 0
    builder.banned.add(card.name)
    group = group_of(card)
    count = builder.fill(lambda c: group_of(c) == group and c.color == card.color and builder.allowed(c), count)
    count = builder.fill(lambda c: group_of(c) == group and builder.allowed(c), count)
    return builder.fill(lambda c: not is_climax(c) and builder.allowed(c), count)


REFERENCE_ROUNDS = 200  # bringing cards in and taking them out, before giving up


def keep_references(builder, required):
    """See Builder.refs_ok: a card in the deck whose named cards are missing either brings them in or comes
    out. A required card stays, and what it names comes in whatever that bends, if it can come in at all."""
    given_up = set()
    for _ in range(REFERENCE_ROUNDS):
        card = next((c for c in builder.deck_cards() if builder.missing_refs(c) and c.name not in given_up), None)
        protected = set(required) | builder.forced
        if not card or bring_references(builder, card, protected):
            if not card:
                break
            continue
        if card.name not in protected:
            take_out(builder, card)
        elif not bring_references(builder, card, protected, force=True):
            given_up.add(card.name)  # nothing more to try for it


def build_deck(pool, anchors, rng=random, deck_name="", focus=False):
    """Returns (Builder with the deck in it, names that must stay in it, notes for the player).
    `focus`: character focus, a deck themed on the anchors' characters."""
    notes = []
    builder = Builder(pool, anchors, rng, deck_name=deck_name, focus=focus)
    builder.initial = True
    named, missing = named_in(anchors, pool)
    builder.named_names = {abilities.plain_name(c.name) for c in named}
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
    builder.copies.update(spread(named_climaxes, CLIMAX_COUNT))
    for card in anchors:
        builder.copies[card.pk] = anchor_copies(card)
    for card in named:
        if not is_climax(card):
            builder.copies[card.pk] = NAMED_COPIES
    colors = {c.color for c in anchors if c.color} | {c.color for c in named_climaxes if c.color} | {c.color for c in [*anchors, *named] if needs_level_zero(c)}
    # Any climax slots the anchors leave, then the synergy that the climaxes make possible.
    wanted = CLIMAX_COUNT - sum(n for pk, n in builder.copies.items() if is_climax(builder.by_pk[pk]))
    wanted = builder.fill(lambda c: is_climax(c) and c.color in colors, wanted)
    short = builder.fill(is_climax, wanted)
    if short:
        notes.append(f"This series doesn't have enough climaxes for {CLIMAX_COUNT}; {short} short.")
    add_synergy(builder, colors, {0})
    # Colors that have to be played get their level 0s now, before the level spread is shared out.
    for color in sorted(colors):
        builder.fill(lambda c: c.level == 0 and c.color == color and not is_climax(c), MIN_LEVEL_ZERO - builder.level_zero_copies(color))
        if builder.level_zero_copies(color) < MIN_LEVEL_ZERO:
            notes.append(f"This series doesn't have {MIN_LEVEL_ZERO} level 0 {color} cards to support your required cards.")
    add_synergy(builder, colors, {1, 2, 3})
    # Then the rest, group by group, to the usual level spread, taking from the biggest
    # groups if what's required has used up more than its share.
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
        builder.fill(fits, count)
    # A small series can run out of some level: anything else that isn't a climax makes up the size,
    # keeping to the level 0 rule if it possibly can.
    builder.fill(lambda c: not is_climax(c) and builder.allowed(c), DECK_SIZE - builder.total())
    keep_references(builder, required)
    if builder.total() < DECK_SIZE and any(not is_climax(c) and builder.room(c) > 0 for c in pool):
        notes.append(f"To reach {DECK_SIZE} cards, some colors have higher levels without {MIN_LEVEL_ZERO} level 0s.")
    builder.initial = False  # the size comes before the limits
    builder.fill(lambda c: not is_climax(c), DECK_SIZE - builder.total(), level_rule=False)
    replace_unplayable_climaxes(builder, anchors, required)
    keep_references(builder, required)  # a climax swapped out may have been named
    builder.fill(lambda c: not is_climax(c), DECK_SIZE - builder.total(), level_rule=False)
    if builder.total() < DECK_SIZE:
        builder.references_rule = False  # the very last resort: a deck has to have its size
        builder.fill(lambda c: not is_climax(c), DECK_SIZE - builder.total(), level_rule=False)
        builder.references_rule = True
    for card in builder.deck_cards():
        if builder.missing_refs(card):
            notes.append(f"{card.name} names {', '.join(sorted(builder.missing_refs(card)))}, which couldn't go in the deck.")
    short = DECK_SIZE - builder.total()
    if short:
        notes.append(f"This series only has enough cards for {DECK_SIZE - short} of the {DECK_SIZE}.")
    required += sorted(name for name in builder.forced if name not in required and any(c.name == name for c in builder.deck_cards()))
    stranded = sorted({builder.by_pk[pk].color for pk, n in builder.copies.items()
                       if n and is_climax(builder.by_pk[pk]) and not builder.supported(builder.by_pk[pk].color)})
    if stranded:
        notes.append(f"Some climaxes have no other cards of their color in the deck: {', '.join(stranded)}.")
    return builder, required, notes


def group_of(card):
    return next((i for i, (_, _, _, counts) in enumerate(DECK_GROUPS) if counts(card)), None)


def replace_cards(pool, anchors, copies, required, removing, mode, rng=random, known=None, picked=(), deck_name="", focus=False):
    """Swap copies out for new draws. Each new card comes from the same group as the one it replaces
    (so the climax count and the level spread stay as they are), or, if that group has nothing else,
    from any other that isn't climaxes. Every required name keeps at least one copy.

    `copies` and `removing` are {card pk: copies}. Returns (new copies, [(old name, new name), ...]),
    and a copy that has nothing to replace it stays. `picked`: names chosen by hand, climaxes among
    which stay even with nothing of their color in the deck yet."""
    builder = Builder(pool, anchors, rng, DAMAGE_SHARE[mode], copies, known, deck_name, focus)
    removed = {builder.by_pk[pk].name for pk in removing if pk in builder.by_pk}
    swaps = []

    def swap_out(old, count):
        """Returns whether every copy found a replacement."""
        pk = old.pk
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
                return False
            builder.copies[new.pk] += 1
            swaps.append((old.name, new.name))
        return True

    for pk, count in removing.items():
        old = builder.by_pk.get(pk)
        if not old:
            continue
        # A required card keeps a copy, and so does a card a required card names.
        held = old.name in required or any(abilities.plain_name(old.name) in builder.refs(c) for c in builder.deck_cards() if c.name in required)
        swap_out(old, min(count, builder.copies[pk] - (1 if held else 0)))
    swaps += replace_unplayable_climaxes(builder, anchors, set(required) | set(picked))
    # Whatever named a card that's now gone goes too (a card chosen by hand is the chooser's business).
    kept = set(required) | set(picked) | {a.name for a in anchors}
    for _ in range(REFERENCE_ROUNDS):
        orphan = next((c for c in builder.deck_cards() if c.name not in kept and c.name not in removed and builder.missing_refs(c)), None)
        if not orphan:
            break
        removed.add(orphan.name)
        swap_out(orphan, builder.copies[orphan.pk])
    return +builder.copies, swaps


# --- Pages ----------------------------------------------------------------------------------------------

def own_list(request, pk):
    return get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)


def series_choices(for_cpu=False):
    """The series that have at least one anchor to offer: [{code, name, cover, anchors}, ...]."""
    counts = Counter()
    if for_cpu:
        counts = cpu_anchor_counts()
    else:
        maybe = Card.objects.filter(Q(description__contains=CX_COMBO) | Q(description__icontains="your climax area")).exclude(card_type__iexact="climax")
        for serial, text in maybe.values_list("serial_number", "description"):
            if abilities.has_combo(text):
                counts[series_code(serial)] += 1
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
        focus = request.POST.get("focus") == "on"
        builder, required, notes = build_deck(pool, anchors, deck_name=card_list.name, focus=focus)
        with transaction.atomic():
            CardListEntry.objects.bulk_create(CardListEntry(card_list=card_list, card_id=card, quantity=n)
                                              for card, n in builder.copies.items() if n)
            card_list.is_deck = True
            card_list.cover_card = max(anchors, key=lambda a: a.level or 0)  # the highest level anchor
            card_list.express = {"series": code, "anchors": [a.pk for a in anchors], "required": required, "focus": focus}
            card_list.save(update_fields=["is_deck", "cover_card", "express", "updated"])
        for note in notes:
            messages.warning(request, note)
        if card_list.reserved_for_cpu:  # staff carry on from the regular deck page, editing it in the side panel
            request.session[SESSION_KEY] = card_list.pk
            return redirect("weiss:list", pk=card_list.pk)
        return redirect("weiss:list_express_review", pk=card_list.pk)
    with_image_urls(choices)
    return render(request, "weiss/express_anchors.html", {"card_list": card_list, "code": code, "choices": choices, "needed": needed})


def role_counts(copies):
    damage = sum(n for card, n in copies if card.damage)
    utility = sum(n for card, n in copies if card.utility)
    both = sum(n for card, n in copies if card.damage and card.utility)
    return {"damage": damage, "utility": utility, "both": both, "neither": sum(n for card, n in copies if not is_climax(card) and not card.damage and not card.utility)}


def pick_results(query, code, everywhere):
    """What a search finds to put in a CPU deck by hand, one printing of each name:
    (cards, how many it found that a CPU can't play)."""
    if not query:
        return [], 0
    cards = Card.objects.filter(Q(name__icontains=query) | Q(serial_number__icontains=query)
                                | Q(traits__icontains=query) | Q(description__icontains=query))
    if not everywhere:
        cards = cards.filter(serial_number__startswith=f"{code}/")
    found, unplayable, seen = [], 0, set()
    for card in cards.order_by("serial_number")[:PICK_SCAN]:
        if card.name in seen:
            continue
        seen.add(card.name)
        if abilities.by_hand_parts(card.description):
            unplayable += 1
        elif len(found) < PICK_RESULTS:
            found.append(card)
    return found, unplayable


def review_url(card_list, mode, post):
    """Back to the review page, with the search that was showing."""
    params = {"mode": mode}
    if post.get("q"):
        params["q"] = post["q"]
    if post.get("scope") == "all":
        params["scope"] = "all"
    return f"{reverse('weiss:list_express_review', args=[card_list.pk])}?{urlencode(params)}"


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
    query = request.GET.get("q", "").strip()
    everywhere = request.GET.get("scope") == "all"
    picks, unplayable = pick_results(query, card_list.express["series"], everywhere) if card_list.reserved_for_cpu else ([], 0)
    in_deck = Counter()
    for entry in entries:
        in_deck[entry.card.name] += entry.quantity
    for card in with_image_urls(picks):
        card.in_deck = in_deck[card.name]
    return render(request, "weiss/express_review.html", {
        "card_list": card_list, "tiles": tiles, "deck": deck_checks(entries), "roles": role_counts(copies),
        "mode": mode if mode in DAMAGE_SHARE else "balanced",
        "query": query, "everywhere": everywhere, "picks": picks, "unplayable": unplayable,
    })


@weiss_access_required
@require_POST
def express_replace(request, pk):
    card_list = own_list(request, pk)
    if not card_list.express:
        return redirect("weiss:list", pk=card_list.pk)
    mode = request.POST.get("mode")
    mode = mode if mode in DAMAGE_SHARE else "balanced"
    back = review_url(card_list, mode, request.POST)
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
        new, swaps = replace_cards(pool, anchors, copies, set(card_list.express["required"]), removing, mode, known=whole,
                                   picked=card_list.express.get("picked", ()), deck_name=card_list.name, focus=card_list.express.get("focus", False))
        card_list.entries.all().delete()
        CardListEntry.objects.bulk_create(CardListEntry(card_list=card_list, card_id=card, quantity=n) for card, n in new.items())
        card_list.save(update_fields=["updated"])
    if swaps:
        lines = Counter(swaps)
        messages.success(request, "Replaced " + "; ".join(f"{old} → {new_name}" + (f" ×{n}" if n > 1 else "") for (old, new_name), n in lines.items()) + ".")
    else:
        messages.warning(request, "Nothing could be replaced: those cards are required, or there's nothing else that fits.")
    return redirect(back)


@weiss_access_required
@require_POST
def express_pick(request, pk):
    """Put the card chosen by hand into a CPU deck, one copy for each copy ticked to come out, or
    one extra if the deck has room and none are ticked. Unlike a replacement, it can be any card a
    CPU can play, from any set: what fits is the choice of whoever's building the deck."""
    card_list = own_list(request, pk)
    if not card_list.reserved_for_cpu or not card_list.express:
        return redirect("weiss:list", pk=card_list.pk)
    mode = request.POST.get("mode")
    mode = mode if mode in DAMAGE_SHARE else "balanced"
    back = review_url(card_list, mode, request.POST)
    value = request.POST.get("card", "")
    card = get_object_or_404(Card, pk=value) if value.isdigit() else None
    if not card:
        messages.error(request, "Choose a card to put in.")
        return redirect(back)
    if abilities.by_hand_parts(card.description):
        messages.error(request, f"A CPU can't play {card.name}: part of it has to be done by hand.")
        return redirect(back)
    removing = Counter(int(v) for v in request.POST.getlist("replace") if v.isdigit())
    removing.pop(card.pk, None)  # swapping a card for itself changes nothing
    with transaction.atomic():
        card_list = CardList.objects.select_for_update().get(pk=card_list.pk)
        entries = list(card_list.entries.select_related("card"))
        copies = Counter({e.card_id: e.quantity for e in entries})
        names = {e.card_id: e.card.name for e in entries}
        removing = Counter({pk: min(n, copies[pk]) for pk, n in removing.items() if copies[pk]})
        copies -= removing
        by_name = Counter()
        for pk, n in copies.items():
            by_name[names[pk]] += n
        adding = sum(removing.values()) or 1
        lost = [names[pk] for pk in removing if names[pk] in card_list.express["required"] and not by_name[names[pk]] and names[pk] != card.name]
        if lost:
            error = f"{lost[0]} is required by your anchors, so one copy stays."
        elif not removing and sum(copies.values()) >= DECK_SIZE:
            error = "The deck is full: tick the copies to take out first."
        elif copy_limit(card) is not None and by_name[card.name] + adding > COPY_LIMIT:  # unless its text lets a deck have any number
            error = f"That would be more than {COPY_LIMIT} copies of {card.name}."
        else:
            error = ""
            copies[card.pk] += adding
            card_list.entries.all().delete()
            CardListEntry.objects.bulk_create(CardListEntry(card_list=card_list, card_id=pk, quantity=n) for pk, n in copies.items() if n)
            card_list.express = {**card_list.express, "picked": sorted({*card_list.express.get("picked", ()), card.name})}
            card_list.save(update_fields=["express", "updated"])
    if error:
        messages.error(request, error)
        return redirect(back)
    taken = "; ".join(f"{names[pk]}" + (f" ×{n}" if n > 1 else "") for pk, n in removing.items())
    messages.success(request, f"Put in {card.name}" + (f" ×{adding}" if adding > 1 else "") + (f", taking out {taken}." if taken else "."))
    climaxes = sum(e.quantity for e in card_list.entries.select_related("card") if is_climax(e.card))
    if climaxes != CLIMAX_COUNT:
        messages.warning(request, f"The deck now has {climaxes} climaxes, not {CLIMAX_COUNT}: a CPU can't use it until that's fixed.")
    return redirect(back)
