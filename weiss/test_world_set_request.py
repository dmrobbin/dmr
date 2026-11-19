"""World mode, the card shop: asking for a set, on the shelves from the next day for a few days, one at a time."""
from django.test import TestCase
from django.urls import reverse

from . import world
from .models import WorldSettings
from .test_world import SET, make_set, staff_user

OTHERS = range(9, 15)  # more sets than the shelves hold, so a set can be missing from today's


class SetRequestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_set()
        for expansion_id in OTHERS:
            make_set(expansion_id)

    def setUp(self):
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.save.money = 5000
        self.save.save()
        world.travel(self.save, "shop")

    def next_day(self, days=1):
        self.save.turn += 4 * days
        self.save.save()

    def ids(self):
        return [entry["id"] for entry in world.shop_stock(self.save)]

    def missing(self):
        """A set the shop isn't selling today."""
        return next(expansion_id for expansion_id in OTHERS if expansion_id not in self.ids())

    def test_a_set_is_on_the_shelves_from_tomorrow_for_three_days(self):
        wanted, before = self.missing(), self.save.money
        world.request_set(self.save, wanted)
        self.assertEqual(before - self.save.money, 300)  # the default price
        self.assertNotIn(wanted, self.ids())  # not today
        for _ in range(world.REQUEST_DAYS):
            self.next_day()
            stock = world.shop_stock(self.save)
            self.assertEqual((stock[1]["id"], stock[1]["requested"]), (wanted, True))  # next to the save's own set
            self.assertEqual(sum(entry["id"] == wanted for entry in stock), 1)  # never twice
        self.next_day()
        self.assertFalse(any(entry["requested"] for entry in world.shop_stock(self.save)))

    def test_one_set_at_a_time_until_it_is_gone(self):
        wanted = self.missing()
        world.request_set(self.save, wanted)
        with self.assertRaisesRegex(ValueError, "already"):
            world.request_set(self.save, wanted)  # still to come
        self.next_day(world.REQUEST_DAYS)
        with self.assertRaisesRegex(ValueError, "its last day"):
            world.request_set(self.save, wanted)  # on the shelves
        self.next_day()
        world.request_set(self.save, wanted)  # gone: another can be asked for

    def test_what_cannot_be_asked_for(self):
        with self.assertRaisesRegex(ValueError, "every day already"):
            world.request_set(self.save, SET)
        with self.assertRaisesRegex(ValueError, "can't get"):
            world.request_set(self.save, 12345)
        self.save.money = 10
        with self.assertRaisesRegex(ValueError, "costs 300 coins"):
            world.request_set(self.save, self.missing())
        self.save.money = 5000
        world.travel(self.save, "plaza")
        with self.assertRaisesRegex(ValueError, "card shop"):
            world.request_set(self.save, self.missing())

    def test_staff_set_the_price(self):
        WorldSettings.objects.update_or_create(pk=1, defaults={"request_price": 750})
        before = self.save.money
        world.request_set(self.save, self.missing())
        self.assertEqual(before - self.save.money, 750)

    def test_the_counter_says_what_was_asked_for_and_when(self):
        offered = world.shop_request(self.save)
        self.assertIsNone(offered["asked"])
        self.assertEqual(sorted(entry["id"] for entry in offered["sets"]), list(OTHERS))  # every set but the save's own
        world.request_set(self.save, self.missing())
        self.assertIn("from tomorrow", world.shop_request(self.save)["asked"]["when"])
        self.next_day()
        self.assertIn("until", world.shop_request(self.save)["asked"]["when"])

    def test_packs_of_the_set_can_be_bought_while_it_is_on_the_shelves(self):
        wanted = self.missing()
        world.request_set(self.save, wanted)
        with self.assertRaisesRegex(ValueError, "doesn't have that set"):
            world.buy_packs(self.save, wanted, 1)  # not till tomorrow
        self.next_day()
        world.buy_packs(self.save, wanted, 1)
        self.assertEqual(self.save.last_opening["set_id"], wanted)

    def test_asking_from_the_town_page(self):
        wanted = self.missing()
        self.client.force_login(self.user)
        version = self.client.get(reverse("weiss:world_town_state", args=[1])).json()["version"]
        answer = self.client.post(reverse("weiss:world_request_set", args=[1]), {"set": wanted, "version": version}).json()
        self.assertIn("is ordered", answer["said"])
        self.assertIsNotNone(answer["town"]["shop"]["request"]["asked"])
        bad = self.client.post(reverse("weiss:world_request_set", args=[1]), {"set": "x", "version": answer["town"]["version"]})
        self.assertEqual(bad.json()["error"], "Choose a set to ask for.")
