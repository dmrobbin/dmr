"""World mode, staff testing: raising a friendship rank at once (the talk box's staff button and the staff-only gift)."""
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import world
from .models import GiftItem, WorldSave
from .test_world import SET, everywhere_rule, give_cpu, make_set, staff_user


class StaffLevelTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.cinder, "plaza")  # Cinder is at the plaza all day, so talking to them works at turn 0
        GiftItem.objects.get_or_create(key="staff-token", defaults={"name": "Staff token", "price": 0, "staff_only": True})
        self.save.flags["test_mode"] = True
        self.save.save()

    def points(self):
        return self.save.relations.get(str(self.cinder.pk), {}).get("points", 0)

    def test_a_level_takes_them_to_the_next_rank_by_the_points_it_needs(self):
        names = world.rank_names()
        world.level_up(self.save, self.cinder)
        self.save.refresh_from_db()
        self.assertEqual(self.points(), world.ranks()[1]["points"])
        self.assertEqual(world.rank_of(self.save, self.cinder.pk), 1)
        self.assertEqual(names[1], "Acquaintance")

    def test_a_rank_reached_this_way_pays_its_rewards_once(self):
        before = self.save.money
        world.level_up(self.save, self.cinder)
        self.save.refresh_from_db()
        self.assertEqual(self.save.money - before, 200)  # rank 1's coins
        world.level_up(self.save, self.cinder)
        self.save.refresh_from_db()
        self.assertEqual(self.save.money - before, 200)  # rank 2 has no coins; rank 1 isn't paid again

    def test_the_top_rank_says_so(self):
        for _ in range(len(world.ranks())):
            try:
                world.level_up(self.save, self.cinder)
            except ValueError:
                break
            self.save.refresh_from_db()
        with self.assertRaisesRegex(ValueError, "already"):
            world.level_up(self.save, self.cinder)

    def test_a_rank_a_quest_holds_back_waits_and_says_what_it_waits_on(self):
        self.save.relations[str(self.cinder.pk)] = {"points": world.ranks()[2]["points"]}  # the points for rank 2 are there
        self.save.save()
        gate = SimpleNamespace(title="Ember", key="ember")
        patches = [mock.patch.object(world.quests, "cap", return_value=1), mock.patch.object(world.quests, "gate_quest", return_value=gate),
                   mock.patch.object(world.quests, "offerable", return_value=False), mock.patch.object(world.quests, "status", return_value="")]
        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaisesRegex(ValueError, "Ember"):
                world.level_up(self.save, self.cinder)  # the points are there already; the quest holds the rank

    def test_only_staff_in_test_mode_can_use_the_button(self):
        self.save.flags["test_mode"] = False
        self.save.save()
        with self.assertRaisesRegex(ValueError, "test mode"):
            world.staff_level(self.save, self.cinder.pk)
        self.save.flags["test_mode"] = True
        self.save.user = User.objects.create_user("player", password="x")
        with self.assertRaisesRegex(ValueError, "test mode"):
            world.staff_level(self.save, self.cinder.pk)

    def test_the_staff_token_raises_a_rank_without_using_the_day_or_time(self):
        self.save.gifts = {"staff-token": 2}
        self.save.save()
        world.give(self.save, self.cinder.pk, "staff-token")
        self.save.refresh_from_db()
        self.assertEqual(self.save.gifts.get("staff-token"), 1)
        self.assertEqual(world.rank_of(self.save, self.cinder.pk), 1)
        self.assertFalse(world.engaged(self.save))
        self.assertNotIn("gifted", world.relation(self.save, self.cinder.pk))
        world.give(self.save, self.cinder.pk, "staff-token")  # no daily limit on it
        self.save.refresh_from_db()
        self.assertEqual(world.rank_of(self.save, self.cinder.pk), 2)
        self.assertNotIn("staff-token", self.save.gifts)

    def test_rewards_never_give_the_staff_token(self):
        for _ in range(20):
            item = world.give_reward(self.save, self.cinder, "gift", "loved")
            self.assertIsNotNone(item)
        self.assertNotIn("staff-token", self.save.gifts)

    def test_players_do_not_see_or_get_the_staff_token(self):
        player = User.objects.create_user("player", password="x")
        self.save.user = player
        self.save.gifts = {"staff-token": 1}
        keys = [item["key"] for item in world.inventory(self.save)]
        self.assertNotIn("staff-token", keys)
        with self.assertRaisesRegex(ValueError, "don't have that"):
            world.give(self.save, self.cinder.pk, "staff-token")

    def test_the_shop_sells_the_token_free_to_staff_only(self):
        self.assertIn("staff-token", [item["key"] for item in world.inventory(self.save)])
        self.assertEqual(GiftItem.objects.get(key="staff-token").price, 0)

    def test_the_town_page_offers_the_button_to_staff_in_test_mode(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_town", args=[1]))
        self.assertContains(page, f'data-level-url="{reverse("weiss:world_level", args=[1])}"')

    def test_the_button_answers_with_the_town_and_the_rank(self):
        self.client.force_login(self.user)
        version = self.client.get(reverse("weiss:world_town_state", args=[1])).json()["version"]
        answer = self.client.post(reverse("weiss:world_level", args=[1]), {"cpu": self.cinder.pk, "version": version}).json()
        self.assertEqual(answer["talk"]["relation"]["rank"], 1)
        self.assertEqual(answer["talk"]["waiting"], None)
        self.assertTrue(any("points" in event for event in answer["talk"]["events"]))
        self.assertEqual(WorldSave.objects.get(pk=self.save.pk).relations[str(self.cinder.pk)]["points"], world.ranks()[1]["points"])
