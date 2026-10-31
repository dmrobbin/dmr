import random
from collections import Counter

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import express
from .models import Card, CardList, CardListEntry

COLORS = ["Red", "Blue", "Green", "Yellow"]
COMBO = '【AUTO】 【CXCOMBO】 When "BIG" is placed on your climax area, draw 1 card.'
HITTER = "【CONT】 During your turn, this card gets +9000 power."
FIXER = "【AUTO】 When this card attacks, choose 1 character in your waiting room, and return it to your hand."


def make_series(code="TST", per_group=9):
    """A set with characters of every level and color, half hitting hard and half fixing things, and climaxes."""
    cards = []
    n = 0

    def add(**fields):
        nonlocal n
        n += 1
        fields.setdefault("name", f"{code} card {n}")
        fields.setdefault("traits", "Hero")
        cards.append(Card(serial_number=f"{code}/S1-{n:03}", expansion="Test set", expansion_id=1, **fields))

    for level in range(4):
        for color in COLORS:
            for i in range(per_group):
                add(card_type="Character", level=level, color=color, power=3000, soul=1,
                    description=HITTER if i % 2 else FIXER)
    for color in COLORS:
        for i in range(3):
            add(card_type="Climax", color=color, description="【CONT】 All of your characters get +1000 power and +1 soul.")
    add(card_type="Climax", color="Red", name="BIG", description="")
    add(card_type="Character", level=1, color="Red", power=3000, soul=1, name="Combo Red", description=COMBO)
    add(card_type="Character", level=3, color="Blue", power=3000, soul=1, name="Combo Blue", description=COMBO)
    add(card_type="Character", level=2, color="Red", power=3000, soul=1, name="“Curly” Friend", description="")
    add(card_type="Character", level=1, color="Red", power=3000, soul=1, name="Combo Naming",
        description='【AUTO】 【CXCOMBO】 When this card attacks, if "BIG" is in your climax area, choose 1 ""Curly" Friend" in your waiting room, and return it to your hand.')
    Card.objects.bulk_create(cards)


def in_pool(pool, name):
    return next(c for c in pool if c.name == name)


class RolesTests(TestCase):
    def card(self, **fields):
        return Card(serial_number="X/1", name="x", expansion="E", expansion_id=1, card_type=fields.pop("card_type", "Character"),
                    level=fields.pop("level", 1), **fields)

    def test_damage_is_above_average_for_the_level_printed_or_boosted(self):
        averages = {(1, 1): 5000}
        self.assertTrue(express.is_damage(self.card(power=6000), averages))
        self.assertFalse(express.is_damage(self.card(power=5000), averages))
        self.assertFalse(express.is_damage(self.card(power=4000), averages))
        self.assertTrue(express.is_damage(self.card(power=4000, description="【CONT】 If you have 2 or more other 《X》 characters, this card gets +2000 power."), averages))
        self.assertTrue(express.is_damage(self.card(power=4000, description="【AUTO】 When this card attacks, this card gets +2000 power until end of turn."), averages))
        self.assertFalse(express.is_damage(self.card(power=4000, description="【AUTO】 When this card attacks, this card gets +500 power until end of turn."), averages))
        self.assertFalse(express.is_damage(self.card(power=4000, description="【AUTO】 When this card attacks, choose 1 of your characters, and that character gets +9000 power until end of turn."), averages))

    def test_a_boost_that_counts_something_is_estimated(self):
        self.assertEqual(express.self_boost("【AUTO】 When this card attacks, this card gets +X power until end of turn. X is equal to the number of characters your opponent has ×2000."), 4000)
        self.assertEqual(express.self_boost("【CONT】 Experience This card gets +2500 power for each 《NIKKE》 character in your level."), 5000)

    def test_only_a_characters_power_counts_and_averages_are_per_set_and_level(self):
        self.assertFalse(express.is_damage(self.card(card_type="Event", power=9000), {(1, 1): 1}))
        cards = [self.card(power=1000), self.card(power=3000), self.card(power=9000, level=2), self.card(card_type="Event", power=99)]
        self.assertEqual(express.power_averages(cards), {(1, 1): 2000, (1, 2): 9000})

    def test_utility_is_the_effects_reach_not_their_cost(self):
        for text in ("【AUTO】 When this card attacks, choose 1 character in your waiting room, and return it to your hand.",
                     "【AUTO】 When this card attacks, you may put the top card of your clock into your waiting room.",
                     "【ACT】 Choose 1 of your opponent's characters, and return it to their hand.",
                     "【AUTO】 When this card's battle opponent becomes 【REVERSE】, you may put that character into your opponent's memory.",
                     "Choose 1 level 0 or lower character in your opponent's center stage, and put it into their waiting room."):
            self.assertTrue(express.is_utility(self.card(description=text)), text)
        for text in ("【ACT】 [Put 1 card from your hand into your waiting room & Put this card into your clock] Draw 1 card.",
                     "【CONT】 If your waiting room has 2 or less climax, this card gets +1000 power.",
                     "【AUTO】 When this card attacks, look at up to 3 cards from the top of your deck, choose up to 1 card from among them, put it into your hand, and put the rest into your waiting room."):
            self.assertFalse(express.is_utility(self.card(description=text)), text)

    def test_a_climax_is_neither(self):
        self.assertFalse(express.is_utility(self.card(card_type="Climax", description="【AUTO】 choose 1 card in your waiting room")))


class BuildTests(TestCase):
    def setUp(self):
        make_series()
        self.pool = express.series_pool("TST")

    def build(self, *names, seed=1):
        return express.build_deck(self.pool, [in_pool(self.pool, n) for n in names], random.Random(seed))

    def named_copies(self, builder):
        return {builder.by_pk[pk].name: n for pk, n in builder.copies.items()}

    def test_a_deck_follows_the_rules_and_the_level_spread(self):
        for seed in range(25):
            builder, _, notes = self.build("Combo Red", seed=seed)
            cards = [(builder.by_pk[pk], n) for pk, n in builder.copies.items()]
            self.assertEqual(sum(n for _, n in cards), 50)
            self.assertEqual(notes, [])
            self.assertLessEqual(max(n for _, n in cards), 4)
            levels = Counter()
            for card, n in cards:
                levels["cx" if card.card_type == "Climax" else min(card.level, 2)] += n
            self.assertEqual(levels, {"cx": 8, 0: 18, 1: 12, 2: 12})

    def test_anchors_and_what_they_name_go_in(self):
        builder, required, _ = self.build("Combo Naming")
        copies = self.named_copies(builder)
        self.assertEqual(copies["Combo Naming"], 4)
        self.assertEqual(copies["BIG"], 4)
        self.assertEqual(copies["“Curly” Friend"], 2)  # the card has curly quotes, the text straight ones
        self.assertEqual(set(required), {"Combo Naming", "BIG", "“Curly” Friend"})

    def test_a_name_thats_not_in_the_series_is_reported(self):
        anchor = Card.objects.create(serial_number="TST/S1-999", name="Lonely", expansion="Test set", expansion_id=1, card_type="Character", level=0, power=1, color="Red",
                                     description='【AUTO】 【CXCOMBO】 When "NOT HERE" is placed on your climax area, draw 1 card.')
        pool = express.series_pool("TST")
        _, _, notes = express.build_deck(pool, [in_pool(pool, anchor.name)], random.Random(1))
        self.assertIn("NOT HERE", notes[0])

    def color_share(self, *names):
        """The share of non-anchor, non-required copies in the anchors' colors, over many decks."""
        hits, total = 0, 0
        for seed in range(30):
            builder, required, _ = self.build(*names, seed=seed)
            colors = {in_pool(self.pool, n).color for n in names}
            for pk, n in builder.copies.items():
                card = builder.by_pk[pk]
                if card.name not in required:
                    total += n
                    hits += n * (card.color in colors)
        return hits / total

    def test_the_bias_is_towards_the_anchors_colors_and_stronger_for_one_color(self):
        one = self.color_share("Combo Red")
        two = self.color_share("Combo Red", "Combo Blue")
        self.assertGreater(one, .6)  # a quarter of the cards are red
        self.assertGreater(two, .6)  # half are red or blue
        self.assertLess(self.chance_of_each_color(two=True), self.chance_of_each_color())

    def chance_of_each_color(self, two=False):
        """How much of a deck one of its colors takes: spread over two, it's less than a mono deck's."""
        names = ("Combo Red", "Combo Blue") if two else ("Combo Red",)
        reds, total = 0, 0
        for seed in range(30):
            builder, _, _ = self.build(*names, seed=seed)
            for pk, n in builder.copies.items():
                total += n
                reds += n * (builder.by_pk[pk].color == "Red")
        return reds / total

    def test_the_default_balance_is_about_2_to_3(self):
        damage, utility = 0, 0
        for seed in range(30):
            builder, _, _ = self.build("Combo Red", seed=seed)
            for pk, n in builder.copies.items():
                damage += n * builder.by_pk[pk].damage
                utility += n * builder.by_pk[pk].utility
        self.assertAlmostEqual(damage / (damage + utility), .4, delta=.08)

    def test_more_climaxes_named_than_slots_are_shared_out(self):
        names = [f"CX{i}" for i in range(3)]
        text = " ".join(f'When "{n}" is placed on your climax area.' for n in names)
        for name in names:
            Card.objects.create(serial_number=f"TST/S1-{name}", name=name, expansion="Test set", expansion_id=1, card_type="Climax", color="Red")
        Card.objects.create(serial_number="TST/S1-A", name="Hungry", expansion="Test set", expansion_id=1, card_type="Character", level=0, power=1, color="Red", description=f"【AUTO】 【CXCOMBO】 {text}")
        pool = express.series_pool("TST")
        builder, _, _ = express.build_deck(pool, [in_pool(pool, "Hungry")], random.Random(1))
        copies = {builder.by_pk[pk].name: n for pk, n in builder.copies.items()}
        self.assertTrue(all(copies[n] >= 2 for n in names), copies)  # the last 2 slots are drawn at random
        self.assertEqual(sum(n for pk, n in builder.copies.items() if builder.by_pk[pk].card_type == "Climax"), 8)

    def test_a_small_series_builds_what_it_can_and_says_so(self):
        Card.objects.create(serial_number="TNY/1", name="Tiny", expansion="Tiny", expansion_id=2, card_type="Character", level=0, power=1, color="Red", description=COMBO)
        pool = express.series_pool("TNY")
        builder, _, notes = express.build_deck(pool, pool, random.Random(1))
        self.assertEqual(builder.total(), 4)
        self.assertTrue(any("climaxes" in n for n in notes) and any("only has enough" in n for n in notes))

    def test_replacing_keeps_the_rules_required_cards_and_changes_the_card(self):
        builder, required, _ = self.build("Combo Naming")
        by_name = {builder.by_pk[pk].name: pk for pk in builder.copies}
        removing = Counter({by_name["Combo Naming"]: 4, by_name["BIG"]: 2})
        for pk, n in builder.copies.items():
            if builder.by_pk[pk].name not in required and builder.by_pk[pk].level == 0:
                removing[pk] = n
                break
        anchors = [in_pool(self.pool, "Combo Naming")]
        new, swaps = express.replace_cards(self.pool, anchors, builder.copies, set(required), removing, "balanced", random.Random(2))
        self.assertEqual(sum(new.values()), 50)
        self.assertGreaterEqual(new[by_name["Combo Naming"]], 1)  # one copy stays
        self.assertEqual(new[by_name["BIG"]], 2)
        climaxes = sum(n for pk, n in new.items() if builder.by_pk[pk].card_type == "Climax")
        self.assertEqual(climaxes, 8)
        self.assertLessEqual(max(new.values()), 4)
        for old, replacement in swaps:
            self.assertNotEqual(old, replacement)
            self.assertEqual(express.group_of(in_pool(self.pool, old)), express.group_of(in_pool(self.pool, replacement)))

    def test_the_toggle_changes_what_replacements_are(self):
        results = {}
        anchors = [in_pool(self.pool, "Combo Red")]
        for mode in express.DAMAGE_SHARE:
            damage, utility = 0, 0
            for seed in range(20):
                builder, required, _ = self.build("Combo Red", seed=seed)
                before = Counter(builder.copies)
                removing = Counter({pk: n for pk, n in builder.copies.items() if builder.by_pk[pk].name not in required and builder.by_pk[pk].card_type != "Climax"})
                new, _ = express.replace_cards(self.pool, anchors, builder.copies, set(required), Counter(dict(list(removing.items())[:6])), mode, random.Random(seed))
                for pk, n in (Counter(new) - before).items():
                    damage += n * builder.by_pk[pk].damage
                    utility += n * builder.by_pk[pk].utility
            results[mode] = damage / (damage + utility)
        self.assertGreater(results["damage"], results["balanced"])
        self.assertGreater(results["balanced"], results["utility"])


class LevelZeroRuleTests(TestCase):
    def setUp(self):
        make_series()
        self.pool = express.series_pool("TST")

    def assert_rule_holds(self, builder):
        for pk, n in builder.copies.items():
            card = builder.by_pk[pk]
            if n and express.needs_level_zero(card):
                self.assertGreaterEqual(builder.level_zero_copies(card.color), express.MIN_LEVEL_ZERO, card.name)

    def test_what_the_rule_applies_to(self):
        card = lambda **f: Card(card_type=f.pop("card_type", "Character"), level=f.pop("level", 1), description=f.pop("description", ""))
        self.assertTrue(express.needs_level_zero(card()))
        self.assertTrue(express.needs_level_zero(card(card_type="Event", level=2)))
        self.assertFalse(express.needs_level_zero(card(level=0)))
        self.assertFalse(express.needs_level_zero(card(card_type="Climax", level=None)))
        self.assertFalse(express.needs_level_zero(card(description="【ACT】 【COUNTER】 Backup 2000, Level 1 [(1) Put this card from your hand into your waiting room]")))
        self.assertFalse(express.needs_level_zero(card(description="【CONT】 This card can be played from your hand without fulfilling color requirements.")))

    def test_every_deck_keeps_to_it(self):
        for seed in range(40):
            for names in (("Combo Red",), ("Combo Red", "Combo Blue")):
                builder, _, notes = express.build_deck(self.pool, [in_pool(self.pool, n) for n in names], random.Random(seed))
                self.assert_rule_holds(builder)
                self.assertEqual((builder.total(), notes), (50, []))

    def test_an_anchors_color_always_gets_its_level_0s(self):
        for seed in range(20):
            builder, _, _ = express.build_deck(self.pool, [in_pool(self.pool, "Combo Blue")], random.Random(seed))
            self.assertGreaterEqual(builder.level_zero_copies("Blue"), 5)

    def test_a_backup_or_any_color_card_goes_in_without_them(self):
        fields = {"expansion": "Test set", "expansion_id": 1, "card_type": "Character", "level": 1, "power": 9000, "traits": "Hero", "color": "Green"}
        Card.objects.filter(color="Green", level__gte=1).delete()
        Card.objects.filter(color="Green", level=0).delete()  # no green level 0s at all
        Card.objects.create(serial_number="TST/S1-B", name="Green Backup", description="【ACT】 【COUNTER】 Backup 2000, Level 1 [(1) Put this card from your hand into your waiting room]", **fields)
        Card.objects.create(serial_number="TST/S1-F", name="Green Free", description="【CONT】 This card can be played from your hand without fulfilling color requirements.", **fields)
        Card.objects.create(serial_number="TST/S1-G", name="Green Plain", description=FIXER, **fields)
        pool = express.series_pool("TST")
        names = Counter()
        for seed in range(60):
            builder, _, _ = express.build_deck(pool, [in_pool(pool, "Combo Red")], random.Random(seed))
            names.update(builder.by_pk[pk].name for pk, n in builder.copies.items() if n)
        self.assertGreater(names["Green Backup"], 0)
        self.assertGreater(names["Green Free"], 0)
        self.assertEqual(names["Green Plain"], 0)

    def test_a_required_card_with_no_support_is_kept_and_reported(self):
        Card.objects.filter(color="Green", level=0).delete()
        anchor = Card.objects.create(serial_number="TST/S1-Z", name="Lone Green", expansion="Test set", expansion_id=1, card_type="Character", level=2, power=1, color="Green", description=COMBO)
        pool = express.series_pool("TST")
        builder, _, notes = express.build_deck(pool, [in_pool(pool, anchor.name)], random.Random(1))
        self.assertEqual(builder.copies[anchor.pk], 4)
        self.assertTrue(any("level 0 Green" in n for n in notes))
        self.assertEqual(builder.total(), 50)

    def test_replacements_keep_to_it(self):
        for seed in range(25):
            anchors = [in_pool(self.pool, "Combo Red"), in_pool(self.pool, "Combo Blue")]
            builder, required, _ = express.build_deck(self.pool, anchors, random.Random(seed))
            # Replace every level 0 of the anchors' colors: each color must keep 5 and the rest stay legal.
            removing = Counter({pk: n for pk, n in builder.copies.items() if builder.by_pk[pk].level == 0 and builder.by_pk[pk].color in ("Red", "Blue") and builder.by_pk[pk].name not in required})
            new, _ = express.replace_cards(self.pool, anchors, builder.copies, set(required), removing, "balanced", random.Random(seed))
            builder.copies = Counter(new)
            self.assert_rule_holds(builder)
            self.assertEqual(sum(new.values()), 50)

    def test_a_level_1_replacement_wont_bring_in_an_unsupported_color(self):
        anchors = [in_pool(self.pool, "Combo Red")]
        red = [c for c in self.pool if c.color == "Red" and c.level == 0][:2]
        level_1 = next(c for c in self.pool if c.color == "Red" and c.level == 1 and c.name != "Combo Red")
        copies = {red[0].pk: 4, red[1].pk: 1, level_1.pk: 1, in_pool(self.pool, "Combo Red").pk: 1}
        for seed in range(30):
            new, swaps = express.replace_cards(self.pool, anchors, copies, set(), {level_1.pk: 1}, "balanced", random.Random(seed))
            self.assertEqual(len(swaps), 1)
            added = next(pk for pk in new if pk not in copies)
            self.assertEqual({c.pk: c for c in self.pool}[added].color, "Red")


class MissingComboTests(TestCase):
    def setUp(self):
        make_series()
        self.pool = express.series_pool("TST")
        self.combo = in_pool(self.pool, "Combo Blue")
        self.other = in_pool(self.pool, "Combo Red")

    def test_what_a_card_references(self):
        self.assertEqual(self.combo.combos, {"BIG"})
        self.assertEqual(in_pool(self.pool, "BIG").combos, set())
        self.assertEqual(next(c for c in self.pool if c.description == FIXER).combos, set())

    def test_a_named_climax_outside_a_combo_line_doesnt_count(self):
        card = Card(card_type="Character", description='【AUTO】 When "BIG" is placed on your climax area, draw 1 card.\n【AUTO】 【CXCOMBO】 When a climax is placed on your climax area, draw 1 card.')
        self.assertEqual(express.combo_climaxes(card, {"BIG"}), set())

    def test_its_weight_drops_until_the_climax_is_in_the_deck(self):
        builder = express.Builder(self.pool, [], random.Random(1))
        without = builder.weight(self.combo)
        self.assertTrue(builder.missing_combo(self.combo))
        builder.copies[in_pool(self.pool, "BIG").pk] = 1
        self.assertFalse(builder.missing_combo(self.combo))
        self.assertAlmostEqual(without, builder.weight(self.combo) * express.MISSING_COMBO_WEIGHT)

    def test_a_combo_with_any_of_its_climaxes_is_fine(self):
        self.combo.combos = {"BIG", "OTHER"}
        builder = express.Builder(self.pool, [], random.Random(1))
        builder.copies[in_pool(self.pool, "BIG").pk] = 1
        self.assertFalse(builder.missing_combo(self.combo))

    def test_decks_rarely_draw_a_card_whose_combo_is_missing(self):
        # Combo Blue names BIG; an anchor naming nothing leaves BIG to chance, and if it's not drawn
        # the card should almost never be.
        anchor = in_pool(self.pool, "Combo Naming")
        anchor.description = ""
        seen = 0
        for seed in range(60):
            big_free = [c for c in self.pool if c.name != "BIG"]
            builder, _, _ = express.build_deck(big_free, [self.other], random.Random(seed))
            seen += self.combo.pk in builder.copies
        self.assertLessEqual(seen, 3)

    def test_anchors_stay_whatever_their_weight(self):
        no_big = [c for c in self.pool if c.name != "BIG"]
        builder, required, _ = express.build_deck(no_big, [self.combo], random.Random(1))
        self.assertEqual(builder.copies[self.combo.pk], 4)


class UnplayableClimaxTests(TestCase):
    def setUp(self):
        make_series()
        self.pool = express.series_pool("TST")
        self.anchor = in_pool(self.pool, "Combo Naming")  # names the climax BIG; red
        self.by_pk = {c.pk: c for c in self.pool}
        self.green_cx = next(c for c in self.pool if c.card_type == "Climax" and c.color == "Green")
        self.other_red_cx = next(c for c in self.pool if c.card_type == "Climax" and c.color == "Red" and c.name != "BIG")

    def builder(self, copies):
        return express.Builder(self.pool, [self.anchor], random.Random(1), copies=copies)

    def assert_every_climax_is_playable(self, builder):
        for pk, n in builder.copies.items():
            if n and builder.by_pk[pk].card_type == "Climax":
                self.assertTrue(builder.supported(builder.by_pk[pk].color), builder.by_pk[pk].name)

    def test_a_climax_alone_in_its_color_becomes_more_of_the_anchors_climax(self):
        big = in_pool(self.pool, "BIG")
        builder = self.builder({self.anchor.pk: 4, big.pk: 2, self.other_red_cx.pk: 4, self.green_cx.pk: 2})
        swaps = express.replace_unplayable_climaxes(builder, [self.anchor], {"Combo Naming", "BIG"})
        self.assertEqual(builder.copies[self.green_cx.pk], 0)
        self.assertEqual(builder.copies[big.pk], 4)
        self.assertEqual(swaps, [(self.green_cx.name, "BIG")] * 2)

    def test_when_the_anchors_climax_is_full_it_uses_the_anchors_color(self):
        big = in_pool(self.pool, "BIG")
        builder = self.builder({self.anchor.pk: 4, big.pk: 4, self.green_cx.pk: 4})
        express.replace_unplayable_climaxes(builder, [self.anchor], {"Combo Naming", "BIG"})
        self.assertEqual(builder.copies[self.green_cx.pk], 0)
        reds = sum(n for pk, n in builder.copies.items() if self.by_pk[pk].card_type == "Climax" and self.by_pk[pk].color == "Red")
        self.assertEqual(reds, 8)

    def test_a_supported_color_is_left_alone(self):
        green = next(c for c in self.pool if c.color == "Green" and c.level == 0)
        builder = self.builder({green.pk: 1, self.green_cx.pk: 2, self.anchor.pk: 4})
        self.assertEqual(express.replace_unplayable_climaxes(builder, [self.anchor], {"Combo Naming"}), [])

    def test_a_required_climax_stays(self):
        builder = self.builder({self.anchor.pk: 4, self.green_cx.pk: 2})
        express.replace_unplayable_climaxes(builder, [self.anchor], {self.green_cx.name})
        self.assertEqual(builder.copies[self.green_cx.pk], 2)

    def test_no_generated_deck_has_one(self):
        for seed in range(60):
            builder, _, notes = express.build_deck(self.pool, [self.anchor], random.Random(seed))
            self.assert_every_climax_is_playable(builder)
            self.assertEqual(sum(n for pk, n in builder.copies.items() if builder.by_pk[pk].card_type == "Climax"), 8)
            self.assertEqual((builder.total(), notes), (50, []))

    def test_a_named_climax_gets_cards_of_its_color(self):
        anchor = Card.objects.create(serial_number="TST/S1-Q", name="Blue Names Green", expansion="Test set", expansion_id=1, card_type="Character", level=0, power=1, color="Blue",
                                     description=f'【AUTO】 【CXCOMBO】 When "{self.green_cx.name}" is placed on your climax area, draw 1 card.')
        pool = express.series_pool("TST")
        for seed in range(10):
            builder, _, _ = express.build_deck(pool, [in_pool(pool, anchor.name)], random.Random(seed))
            self.assertGreaterEqual(builder.level_zero_copies("Green"), 5)

    def test_replacing_the_last_card_of_a_color_takes_its_climax_too(self):
        big = in_pool(self.pool, "BIG")
        green = next(c for c in self.pool if c.color == "Green" and c.level == 0)
        red = [c for c in self.pool if c.color == "Red" and c.level == 0]
        copies = {self.anchor.pk: 4, big.pk: 2, self.green_cx.pk: 2, green.pk: 1, red[0].pk: 4, red[1].pk: 1}
        new, swaps = express.replace_cards(self.pool, [self.anchor], copies, {"Combo Naming", "BIG"}, {green.pk: 1}, "balanced", random.Random(3))
        builder = self.builder(new)
        if not builder.supported("Green"):
            self.assertEqual(new.get(self.green_cx.pk, 0), 0)
            self.assertEqual(new[big.pk], 4)
        self.assert_every_climax_is_playable(builder)
        self.assertEqual(sum(new.values()), sum(copies.values()))

    def test_a_required_climax_keeps_a_card_of_its_color(self):
        red = next(c for c in self.pool if c.color == "Red" and c.level == 0)
        green = next(c for c in self.pool if c.color == "Green" and c.level == 0)
        for seed in range(20):
            copies = {self.anchor.pk: 4, red.pk: 4, self.green_cx.pk: 2, green.pk: 2}
            new, _ = express.replace_cards(self.pool, [self.anchor], copies, {"Combo Naming", self.green_cx.name}, {green.pk: 2}, "balanced", random.Random(seed))
            self.assertEqual(new[self.green_cx.pk], 2)
            self.assert_every_climax_is_playable(self.builder(new))

    def test_a_replacement_climax_comes_from_a_color_in_the_deck(self):
        big = in_pool(self.pool, "BIG")
        red = next(c for c in self.pool if c.color == "Red" and c.level == 0)
        for seed in range(30):
            copies = {self.anchor.pk: 4, big.pk: 4, self.other_red_cx.pk: 4, red.pk: 4}
            new, _ = express.replace_cards(self.pool, [self.anchor], copies, {"Combo Naming", "BIG"}, {self.other_red_cx.pk: 2}, "balanced", random.Random(seed))
            self.assert_every_climax_is_playable(self.builder(new))


class PagesTests(TestCase):
    def setUp(self):
        make_series()
        self.user = User.objects.create_user("daryl", password="x", is_staff=True)
        self.client.force_login(self.user)
        self.deck = CardList.objects.create(user=self.user, name="Deck")
        self.start = reverse("weiss:list_express", args=[self.deck.pk])
        self.review = reverse("weiss:list_express_review", args=[self.deck.pk])

    def anchor(self, name="Combo Red"):
        return Card.objects.get(name=name).pk

    def build(self):
        return self.client.post(self.start, {"series": "TST", "anchor": [self.anchor(), self.anchor("Combo Blue")]})

    def test_the_header_links_to_the_lists(self):
        page = self.client.get(reverse("weiss:sets")).content.decode()
        self.assertIn(f'href="{reverse("weiss:lists")}"', page.split("</nav>")[0])
        page = self.client.get(reverse("weiss:lists")).content.decode().split("</nav>")[0]
        self.assertIn('class="current"', page.split("Weiss cards")[1].split("</a>")[1])

    def test_creating_a_list_prompts_until_answered(self):
        self.client.post(reverse("weiss:list_create"), {"name": "Fresh"})
        fresh = CardList.objects.get(name="Fresh")
        page = self.client.get(reverse("weiss:lists"))
        self.assertContains(page, "Express build")
        self.assertContains(page, reverse("weiss:list_express", args=[fresh.pk]))
        self.client.post(reverse("weiss:list_express_skip"))
        self.assertNotContains(self.client.get(reverse("weiss:lists")), "data-express-prompt")

    def test_starting_answers_the_prompt(self):
        self.client.post(reverse("weiss:list_create"), {"name": "Fresh"})
        self.client.get(reverse("weiss:list_express", args=[CardList.objects.get(name="Fresh").pk]))
        self.assertNotContains(self.client.get(reverse("weiss:lists")), "data-express-prompt")

    def test_the_steps(self):
        self.assertContains(self.client.get(self.start), "?series=TST")
        page = self.client.get(self.start, {"series": "TST"})
        self.assertContains(page, "Combo Red")
        self.assertContains(page, "Combo Blue")
        self.assertNotContains(page, "BIG</a>")  # a climax isn't an anchor
        self.assertRedirects(self.build(), self.review)
        self.deck.refresh_from_db()
        self.assertEqual(self.deck.card_count(), 50)
        self.assertEqual(self.deck.express["series"], "TST")
        page = self.client.get(self.review)
        self.assertEqual(page.content.decode().count('class="card-name small"'), 50)  # every copy is shown

    def test_anchors_are_checked(self):
        fixer = Card.objects.filter(card_type="Character", description=FIXER).first().pk
        for anchors in ([], [self.anchor()], [self.anchor(), Card.objects.get(name="BIG").pk], [self.anchor(), fixer], [self.anchor(), self.anchor()],
                        [self.anchor(), self.anchor("Combo Blue"), self.anchor("Combo Naming")]):
            self.client.post(self.start, {"series": "TST", "anchor": anchors})
            self.assertEqual(self.deck.entries.count(), 0, anchors)

    def test_a_series_with_only_one_anchor_can_still_build(self):
        only = Card.objects.create(serial_number="ONE/1", name="Only", expansion="One", expansion_id=2, card_type="Character", level=0, power=1, color="Red", description=COMBO)
        self.assertContains(self.client.get(self.start, {"series": "ONE"}), "choose 1 anchor card.")
        self.client.post(self.start, {"series": "ONE", "anchor": [only.pk]})
        self.assertGreater(self.deck.entries.count(), 0)

    def test_tiles_carry_the_cards_color_for_their_selected_border(self):
        self.assertContains(self.client.get(self.start, {"series": "TST"}), 'class="express-tile color-blue"')
        self.build()
        self.assertContains(self.client.get(self.review), "express-tile color-red")

    def test_a_deck_with_cards_isnt_overwritten(self):
        CardListEntry.objects.create(card_list=self.deck, card=Card.objects.first(), quantity=1)
        self.build()
        self.assertEqual(self.deck.card_count(), 1)

    def test_replacing(self):
        self.build()
        self.deck.refresh_from_db()
        target = next(e for e in self.deck.entries.select_related("card") if e.card.name not in self.deck.express["required"] and e.card.card_type == "Character")
        before = target.quantity
        response = self.client.post(reverse("weiss:list_express_replace", args=[self.deck.pk]), {"replace": [target.card_id], "mode": "damage"}, follow=True)
        self.assertContains(response, "Replaced")
        self.assertEqual(response.context["mode"], "damage")
        self.assertEqual(self.deck.card_count(), 50)
        now = self.deck.entries.filter(card=target.card).first()
        self.assertEqual(now.quantity if now else 0, before - 1)

    def test_replacing_nothing_or_a_required_last_copy_changes_nothing(self):
        self.build()
        self.deck.entries.filter(card_id=self.anchor()).update(quantity=1)
        extra = self.deck.entries.exclude(card_id=self.anchor()).first()
        extra.quantity += 3
        extra.save()
        url = reverse("weiss:list_express_replace", args=[self.deck.pk])
        self.assertContains(self.client.post(url, {}, follow=True), "Select the cards")
        self.client.post(url, {"replace": [self.anchor()]})
        self.assertEqual(self.deck.entries.get(card_id=self.anchor()).quantity, 1)

    def test_the_highest_level_anchor_is_the_cover(self):
        self.build()  # Combo Red is level 1, Combo Blue level 3
        self.deck.refresh_from_db()
        self.assertEqual(self.deck.cover_card, Card.objects.get(name="Combo Blue"))

    def test_done_stops_editing_and_goes_to_the_lists(self):
        self.client.post(reverse("weiss:list_edit", args=[self.deck.pk]))
        self.build()
        page = self.client.get(self.review).content.decode()
        self.assertIn(f'formaction="{reverse("weiss:list_stop_editing")}"', page)
        # What the browser sends for that button: the whole form, to its formaction.
        response = self.client.post(reverse("weiss:list_stop_editing"), {"next": reverse("weiss:lists"), "mode": "balanced"})
        self.assertRedirects(response, reverse("weiss:lists"))
        self.assertNotIn("weiss_editing_list", self.client.session)
        self.assertEqual(self.deck.card_count(), 50)

    def test_only_the_owner(self):
        self.client.force_login(User.objects.create_user("other", password="x", is_staff=True))
        self.assertEqual(self.client.get(self.start).status_code, 404)
        self.assertEqual(self.client.post(reverse("weiss:list_express_replace", args=[self.deck.pk]), {}).status_code, 404)
