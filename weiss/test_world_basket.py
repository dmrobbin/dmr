"""World mode, the card shop's basket: several things bought at once, and the packs opened together."""
import json

from django.test import TestCase
from django.urls import reverse

from . import world, world_events as events
from .models import GiftItem
from .test_world import SET, make_set, staff_user

OTHER = 9
WEDNESDAY = 2


class BasketTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_set()
        for expansion_id in range(OTHER, OTHER + 4):
            make_set(expansion_id)
        GiftItem.objects.get_or_create(key="melon-bread", defaults={"name": "Melon bread", "price": 80})

    def setUp(self):
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.save.money = 50000
        self.save.save()
        world.travel(self.save, "shop")
        self.other = next(entry["id"] for entry in world.shop_stock(self.save) if entry["id"] != SET)

    def cards_held(self):
        return sum(self.save.pool.values())

    def test_everything_at_once_with_the_packs_revealed_together(self):
        card = world.shop_cards(self.save)[0]
        basket = [{"kind": "pack", "set": SET, "count": 3}, {"kind": "pack", "set": self.other, "count": 2},
                  {"kind": "special", "special": "climax_pack", "set": SET, "count": 1},
                  {"kind": "card", "card": card.pk}, {"kind": "gift", "gift": "melon-bread", "count": 2}]
        total, _ = world.basket_cost(self.save, world.read_basket(self.save, basket))
        self.assertEqual(total, world.pack_price() * 5 + world.specialty_price() + world.card_price() + 160)
        before, held = self.save.money, self.cards_held()
        done = world.checkout(self.save, basket, expected=total)
        self.assertEqual(before - self.save.money, total)
        self.assertEqual(done["packs"], 6)
        self.assertEqual(len(self.save.last_opening["packs"]), 6)  # every pack, revealed together
        self.assertEqual(self.save.last_opening["set"], "Your purchases")  # from more than one set
        self.assertGreater(self.cards_held(), held)
        self.assertIn(card.pk, self.save.today["bought_cards"])
        self.assertEqual(self.save.gifts.get("melon-bread"), 2)

    def test_the_same_thing_added_twice_is_one_line(self):
        lines = world.read_basket(self.save, [{"kind": "pack", "set": SET, "count": 2}, {"kind": "pack", "set": SET, "count": 3}])
        self.assertEqual([(line["set"], line["count"]) for line in lines], [(SET, 5)])
        card = world.shop_cards(self.save)[0]
        lines = world.read_basket(self.save, [{"kind": "card", "card": card.pk}, {"kind": "card", "card": card.pk}])
        self.assertEqual(len(lines), 1)

    def test_more_than_ten_packs_of_a_set(self):
        world.checkout(self.save, [{"kind": "pack", "set": SET, "count": 12}])
        self.assertEqual(len(self.save.last_opening["packs"]), 12)
        self.assertNotEqual(self.save.last_opening["set"], "Your purchases")  # one set: its own name

    def test_what_is_refused_before_anything_is_bought(self):
        before = self.save.money
        for basket, words in (([], "empty"), ([{"kind": "pack", "set": 12345, "count": 1}], "isn't on the shelves"),
                              ([{"kind": "card", "card": 12345}], "isn't on the rack"),
                              ([{"kind": "special", "special": "level_pack", "set": SET, "level": "9"}], "Choose a level"),
                              ([{"kind": "pack", "set": SET, "count": 31}], "Buy 1 to 30"),
                              ([{"kind": "pack", "set": SET, "count": 20}, {"kind": "special", "special": "climax_pack", "set": SET, "count": 11}],
                               "30 packs at most")):
            with self.subTest(words=words):
                with self.assertRaisesRegex(ValueError, words):
                    world.checkout(self.save, basket)
        self.save.money = 10
        with self.assertRaisesRegex(ValueError, "comes to"):
            world.checkout(self.save, [{"kind": "pack", "set": SET, "count": 1}])
        self.save.money = before
        with self.assertRaisesRegex(ValueError, "Prices have changed"):
            world.checkout(self.save, [{"kind": "pack", "set": SET, "count": 1}], expected=1)
        self.assertEqual(self.save.money, before)

    def test_a_sale_limit_holds_across_the_basket(self):
        self.save.turn = WEDNESDAY * 4
        self.save.save()
        featured = events.featured_set(self.save)["id"]
        base = world.pack_price()
        total, _ = world.basket_cost(self.save, world.read_basket(self.save, [{"kind": "pack", "set": featured, "count": 7}]))
        self.assertEqual(total, 5 * (base // 2) + 2 * base)
        before = self.save.money
        world.checkout(self.save, [{"kind": "pack", "set": featured, "count": 7}], expected=total)
        self.assertEqual(before - self.save.money, total)

    def test_checking_out_from_the_town(self):
        self.client.force_login(self.user)
        version = self.client.get(reverse("weiss:world_town_state", args=[1])).json()["version"]
        basket = [{"kind": "pack", "set": SET, "count": 2}]
        answer = self.client.post(reverse("weiss:world_checkout", args=[1]),
                                  {"basket": json.dumps(basket), "expected": world.pack_price() * 2, "version": version}).json()
        self.assertEqual(answer["go"], reverse("weiss:world_opened", args=[1]))
        page = self.client.get(answer["go"])
        self.assertContains(page, "2 packs")
        gifts = self.client.post(reverse("weiss:world_checkout", args=[1]),
                                 {"basket": json.dumps([{"kind": "gift", "gift": "melon-bread", "count": 1}]), "version": answer["town"]["version"]}).json()
        self.assertEqual(gifts["said"], "Bought Melon bread.")  # nothing to open: the town says so

    def test_a_basket_that_fails_buys_nothing(self):
        self.client.force_login(self.user)
        version = self.client.get(reverse("weiss:world_town_state", args=[1])).json()["version"]
        before = self.save.money
        basket = [{"kind": "pack", "set": SET, "count": 2}, {"kind": "card", "card": 12345}]
        answer = self.client.post(reverse("weiss:world_checkout", args=[1]), {"basket": json.dumps(basket), "version": version})
        self.assertEqual(answer.status_code, 400)
        self.save.refresh_from_db()
        self.assertEqual(self.save.money, before)
        bad = self.client.post(reverse("weiss:world_checkout", args=[1]), {"basket": "not json", "version": version})
        self.assertEqual(bad.json()["error"], "Your basket couldn't be read. Try again.")

    def test_the_town_page_has_the_basket(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_town", args=[1]))
        self.assertContains(page, "Your basket")
        self.assertContains(page, f'data-checkout-url="{reverse("weiss:world_checkout", args=[1])}"')
