"""The whole tutorial, walked through the real views from a new save, in order: nothing is set by flag, every step is
done the way the town's page does it (World Planner's report of a playthrough that couldn't reach the shop)."""
from unittest import mock

from django.urls import reverse

from . import challenge, world, world_tutorial as tutorial
from .test_minigames import make_set as pictured_set
from .test_world_tutorial import TutorialBase


class TutorialWalkTests(TutorialBase):
    def setUp(self):
        super().setUp()
        pictured_set(30)
        self.client.force_login(self.user)

    def town(self):
        return self.client.get(reverse("weiss:world_town_state", args=[1])).json()

    def move(self, name, **data):
        version = self.town()["version"]
        response = self.client.post(reverse(name, args=[1]), {**data, "version": version})
        self.assertEqual(response.status_code, 200, response.content[:300])
        return response.json()

    def step(self):
        found = self.town()["tutorial"]
        return found["step"] if found else None

    def lines_said(self):
        if self.town()["tutorial"] and self.town()["tutorial"]["lines"]:
            self.move("weiss:world_tutorial", act="said")

    def expect(self, name):
        self.lines_said()
        self.assertEqual(self.step(), name)

    def test_the_whole_tutorial_through_the_views(self):
        self.expect("arrive")
        self.move("weiss:world_tutorial", act="approach", cpu=self.aang.pk)
        self.expect("talk")  # approach is done once its lines are said
        self.move("weiss:world_talk", cpu=self.aang.pk)
        self.expect("gift")
        gift = next(item["key"] for item in self.town()["gifts"] if item["have"] > 0)
        self.move("weiss:world_give", cpu=self.aang.pk, gift=gift)
        self.expect("map")
        self.assertFalse(self.town()["engaged"], "the map must be open in the map step: nothing holds it shut")
        self.move("weiss:world_travel", place="shop")
        self.expect("shop")
        self.move("weiss:world_checkout", basket='[{"kind": "pack", "set": %d, "count": 1}]' % self.save.expansion_id)
        self.expect("quests")
        self.client.get(reverse("weiss:world_quests", args=[1]))
        self.expect("time")
        self.assertTrue(self.town()["can_wait"], "the time step's Pass time must be open")
        self.move("weiss:world_wait")
        self.assertTrue(self.town()["choose_required"], "the map opens after time passes")
        self.move("weiss:world_travel", place=self.town()["place"]["key"])
        self.expect("deck")
        self.legal_deck()
        self.expect("minigame")
        self.move("weiss:world_minigame", cpu=self.aang.pk, game="cups")
        with mock.patch("time.time", return_value=challenge.time.time() + challenge.MINIGAME_MIN_SECONDS + 5):
            self.move("weiss:world_minigame_done", result="win")
        if self.town()["choose_required"]:  # the game passed time: the map asks where to spend it
            self.move("weiss:world_travel", place=self.town()["place"]["key"])
        self.expect("duel")
        room = world.start_duel(self.fresh(), self.aang.pk)
        over = {"winner": str(room.host_id), "loser": str(room.guest_id), "reason": "level", "rematch": []}
        room.state["game_over"] = over
        room.save(update_fields=["state"])
        world.game_finished(room, over)
        self.assertIsNone(self.town()["tutorial"])

    def fresh(self):
        self.save.refresh_from_db()
        return self.save

    def climaxes(self):
        return [c for c in self.cards if c.card_type == "Climax"][:2]

    def others(self):
        return [c for c in self.cards if c.card_type != "Climax"][:14]
