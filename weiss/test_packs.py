import random
from collections import Counter

from django.contrib.auth.models import Group, User
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from core.access import WEISS_GROUP

from . import packs, play
from .lists import CLIMAX_COUNT, is_climax
from .models import Card, CardListEntry
from .templatetags.weiss_lists import rarity_grade


def make_set(expansion_id=1, name="Vol.1", **rarities):
    """{rarity: how many} cards of a set; climax commons and rares are climaxes."""
    cards = []
    for rarity, count in rarities.items():
        rarity = rarity.replace("_", " ")
        for n in range(count):
            card_type = "Climax" if rarity in ("CC", "CR", "RRR") else "Character"
            cards.append(Card.objects.create(serial_number=f"S{expansion_id}/{rarity}-{n}", name=f"{rarity} {n}", expansion=name,
                                             expansion_id=expansion_id, card_type=card_type, rarity=rarity))
    return cards


TEST_CLIMAX_COPIES = 2  # of each test climax: few enough for Highlander's limit


def with_climaxes(deck):
    """Top this deck up to the CLIMAX_COUNT climaxes it needs to be played, with test climaxes (TEST_CLIMAX_COPIES of
    each). Returns {card id: copies added}."""
    short = CLIMAX_COUNT - sum(e.quantity for e in deck.entries.select_related("card") if is_climax(e.card))
    added, n = {}, 0
    while short > 0:
        n += 1
        card, _ = Card.objects.get_or_create(serial_number=f"TEST/CX{n}", defaults={
            "name": f"Test climax {n}", "expansion": "Test", "expansion_id": 999, "card_type": "Climax", "rarity": "CC"})
        entry, _ = CardListEntry.objects.get_or_create(card_list=deck, card=card, defaults={"quantity": 0})
        more = min(short, TEST_CLIMAX_COPIES - entry.quantity)
        if more > 0:
            entry.quantity += more
            entry.save(update_fields=["quantity"])
            added[card.pk] = more
            short -= more
    return added


def run_with_climaxes(run):
    """with_climaxes for a challenge run's deck, the copies going in its pool too (the pair's, in co-op). Returns the
    run as it now is."""
    from .challenge import current
    added = with_climaxes(run.deck)
    holder = run.coop if run.coop_id else run
    holder.refresh_from_db()
    for pk, n in added.items():
        holder.pool[str(pk)] = holder.pool.get(str(pk), 0) + n
    holder.save(update_fields=["pool"])
    return current(run.user)


class PackTests(TestCase):
    def test_a_pack_has_a_card_for_each_slot_best_last(self):
        make_set(C=10, U=6, CC=2, CR=2, R=5, RR=3, SR=6, RRR=2, SP=2)
        pack = packs.open_pack(packs.Pool.for_set(1), random.Random(1))
        self.assertEqual(len(pack), packs.PACK_SIZE)
        self.assertEqual(Counter(pull.slot for pull in pack), {"Common": 4, "Uncommon": 1, "Climax": 1, "Rare": 1, "Foil": 1})
        self.assertEqual([pull.grade for pull in pack], sorted(pull.grade for pull in pack))
        by_slot = {pull.slot: pull.rarity for pull in pack}
        self.assertEqual(by_slot["Uncommon"], "U")
        self.assertEqual(by_slot["Climax"], "CC")
        self.assertIn(by_slot["Rare"], {"R", "RR", "CR"})
        self.assertIn(by_slot["Foil"], {"SR", "RRR", "SP"})

    def test_the_odds_follow_the_tables(self):
        make_set(C=10, U=6, CC=2, R=5, RR=3, SR=6, SP=2)
        pool, rng = packs.Pool.for_set(1), random.Random(7)
        foils = Counter(pull.rarity for _ in range(2000) for pull in packs.open_pack(pool, rng) if pull.slot == "Foil")
        self.assertGreater(foils["SR"], foils["SP"] * 5)  # 70 : 6
        self.assertGreater(foils["SP"], 0)

    def test_promos_and_other_sets_never_turn_up(self):
        make_set(C=5, U=2, R=2, SR=2)
        make_set(PR=5)
        make_set(expansion_id=2, name="Vol.2", C=5)
        pool = packs.Pool.for_set(1)
        self.assertNotIn("PR", pool.by_rarity)
        pulled = {pull.card.expansion_id for _ in range(50) for pull in packs.open_pack(pool)}
        self.assertEqual(pulled, {1})

    def test_a_slot_falls_back_when_the_set_has_none_of_its_rarities(self):
        make_set(C=8, CR=2, R=3)  # no uncommons, climax commons or foils, like some older and extra sets
        pack = packs.open_pack(packs.Pool.for_set(1), random.Random(3))
        by_slot = {pull.slot: pull.rarity for pull in pack}
        self.assertEqual(by_slot["Uncommon"], "C")
        self.assertEqual(by_slot["Climax"], "CR")
        self.assertIn(by_slot["Foil"], {"R"})

    def test_a_set_of_its_own_rarities_still_makes_packs(self):
        make_set(TTR=4)
        pack = packs.open_pack(packs.Pool.for_set(1))
        self.assertEqual({pull.rarity for pull in pack}, {"TTR"})
        self.assertEqual(pack[0].grade, packs.SPECIAL_GRADE)

    def test_a_special_foil_the_tables_dont_name_comes_in_the_foil_slot(self):
        make_set(C=4, U=2, CC=1, R=2, SR=1, OFR=1, ZZR=1)
        pool = packs.Pool.for_set(1)
        foil = next(slot for slot in packs.PACK if slot.name == "Foil")
        self.assertIn(("ZZR", 1), pool.odds(foil))
        common = next(slot for slot in packs.PACK if slot.name == "Common")
        self.assertNotIn("ZZR", dict(pool.odds(common)))

    def test_rarities_are_read_however_they_are_spaced(self):
        self.assertEqual(packs.normalize("SR ⁑"), "SR⁑")
        self.assertEqual(packs.grade_of("SR⁑"), 4)
        self.assertEqual(packs.grade_of("C"), 0)
        self.assertEqual(packs.grade_of("SEC"), 5)

    def test_a_pack_rarity_overrides_the_printed_one(self):
        common, = make_set(C=1)
        promo, = make_set(PR=1)
        common.pack_rarity = "SEC"
        common.save()
        promo.pack_rarity = "U"
        promo.save()
        pool = packs.Pool.for_set(1)
        self.assertEqual(pool.by_rarity, {"SEC": [common], "U": [promo]})
        common.pack_rarity = "PR"  # and keeps a card out
        common.save()
        self.assertEqual(packs.Pool.for_set(1).by_rarity, {"U": [promo]})

    def test_the_sets_that_make_packs(self):
        make_set(C=3)
        make_set(expansion_id=5, name="Promos", PR=4)
        make_set(expansion_id=9, name="Vol.9", C=2, SR=1)
        self.assertEqual(packs.pack_sets(), [{"id": 9, "name": "Vol.9", "cards": 3}, {"id": 1, "name": "Vol.1", "cards": 3}])

    def test_a_pull_has_what_the_page_shows(self):
        card, = make_set(SR=1)
        shown = packs.open_pack(packs.Pool.for_set(1))[0].as_dict()
        self.assertEqual(shown["id"], card.pk)
        self.assertEqual((shown["rarity"], shown["grade"]), ("SR", 3))
        self.assertEqual(shown["image"], reverse("weiss:card_image", args=[card.pk]))


class RarityEffectTests(TestCase):
    def test_grades_for_the_effects(self):
        for rarity, grade in (("C", 0), ("U", 0), ("PR", 0), ("TD", 0), ("", 0), ("R", 1), ("CR", 1), ("RR", 2),
                              ("SR", 3), ("RRR", 3), ("SP", 4), ("SR ⁑", 4), ("SSP", 5), ("SEC", 5)):
            self.assertEqual(rarity_grade(Card(rarity=rarity)), grade, rarity)
        self.assertEqual(rarity_grade(Card(rarity="C", pack_rarity="SP")), 4)  # what the packs treat it as

    def test_a_picture_in_its_rarity_frame(self):
        def art(rarity):
            card = Card(rarity=rarity)
            card.image_src = "https://example.com/a.png"  # set by views.with_image_urls
            return Template('{% include "weiss/card_art.html" with alt="x" lazy=True %}').render(Context({"card": card}))
        self.assertEqual(art("C"), '<span class="rfx"><img src="https://example.com/a.png" alt="x" loading="lazy"></span>')
        self.assertIn('data-grade="1"', art("R"))
        self.assertNotIn("rfx-sheen", art("RR"))
        self.assertIn('<span class="rfx" data-grade="3">', art("SR"))
        self.assertIn("rfx-sheen", art("SR"))  # SR and up shine

    def test_the_board_knows_each_cards_grade(self):
        card, = make_set(SSP=1)
        self.assertEqual(play.card_info([card.pk])[str(card.pk)]["grade"], 5)


class PackPageTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.player = User.objects.create_user("player", password="x")
        self.player.groups.add(Group.objects.get_or_create(name=WEISS_GROUP)[0])
        make_set(C=10, U=4, CC=2, R=4, RR=2, SR=4)
        self.client.force_login(self.staff)

    def test_it_is_staff_only(self):
        self.assertContains(self.client.get(reverse("weiss:play_rooms")), reverse("weiss:play_packs"))
        self.client.force_login(self.player)
        self.assertNotContains(self.client.get(reverse("weiss:play_rooms")), reverse("weiss:play_packs"))
        self.assertEqual(self.client.get(reverse("weiss:play_packs")).status_code, 403)
        self.assertEqual(self.client.get(reverse("weiss:play_packs_open"), {"set": 1}).status_code, 403)

    def test_choosing_a_set(self):
        response = self.client.get(reverse("weiss:play_packs"))
        self.assertContains(response, "Vol.1 (26 cards)")
        self.assertContains(response, "Open a box (16)")

    def test_opening_packs(self):
        response = self.client.get(reverse("weiss:play_packs_open"), {"set": 1, "count": 3})
        self.assertEqual(response.status_code, 200)
        opening = response.context["opening"]
        self.assertEqual(len(opening["packs"]), 3)
        self.assertTrue(all(len(pack) == packs.PACK_SIZE for pack in opening["packs"]))
        self.assertContains(response, 'id="pack-opening"')
        self.assertContains(response, 'data-pack="2"')
        self.assertContains(response, "weiss/packs.js")
        # A pulled card opens its details, as in the deck builder.
        self.assertContains(response, "data-card-popup-dialog")
        self.assertContains(response, "weiss/lists.js")
        pull = opening["packs"][0][0]
        self.assertEqual(pull["popup"], reverse("weiss:card_popup", args=[pull["id"]]))

    def test_the_count_is_kept_in_bounds(self):
        many = self.client.get(reverse("weiss:play_packs_open"), {"set": 1, "count": 500})
        self.assertEqual(len(many.context["opening"]["packs"]), 24)
        none = self.client.get(reverse("weiss:play_packs_open"), {"set": 1, "count": 0})
        self.assertEqual(len(none.context["opening"]["packs"]), 1)

    def test_a_set_without_packs(self):
        make_set(expansion_id=5, PR=3)
        self.assertEqual(self.client.get(reverse("weiss:play_packs_open"), {"set": 5}).status_code, 404)
        self.assertEqual(self.client.get(reverse("weiss:play_packs_open"), {"set": "x"}).status_code, 404)

    def test_the_play_tab_stays_current(self):
        self.assertContains(self.client.get(reverse("weiss:play_packs")),
                            f'<a href="{reverse("weiss:play_rooms")}" class="current" aria-current="page">Play</a>', html=False)
