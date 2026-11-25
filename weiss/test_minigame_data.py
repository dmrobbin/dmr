"""The minigame data's player and CPU sides for the frame (docs/minigames-polish-plan.md, the contract): the same keys from all
three entry points (the staff page, the town, and the infinite challenge), with the player's picture and sleeve and the
CPU's intro art."""
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import minigame_views, test_world, world
from .models import Card, CpuProfile, PlayerProfile, Sleeve
from .test_minigames import make_set as pictured_set
from .test_world import staff_user

PLAYER_KEYS = {"name", "picture", "sleeve"}


class GameDataTests(TestCase):
    """game_data itself: the player and the CPU's image."""

    def setUp(self):
        self.user = staff_user()
        self.cpu = CpuProfile.objects.create(name="Iris", finalized=True)
        self.set_id = 30
        pictured_set(self.set_id)

    def data(self):
        with mock.patch("weiss.minigame_views.game_set", return_value=self.set_id):
            return minigame_views.game_data("memory", self.cpu, "normal", self.user, seed=1)

    def test_a_player_without_a_profile_has_no_picture_and_the_default_sleeve(self):
        self.assertEqual(self.data()["player"], {"name": self.user.username, "picture": None, "sleeve": ""})

    def test_a_player_with_a_picture_has_its_avatar(self):
        PlayerProfile.objects.create(user=self.user, avatar_card=Card.objects.filter(expansion_id=self.set_id).first())
        picture = self.data()["player"]["picture"]
        self.assertIn("image", picture)
        self.assertIn("width", picture)

    def test_a_chosen_sleeve_is_its_css_background(self):
        sleeve = Sleeve.objects.create(style=Sleeve.DEFAULT, key="sleeves/test/abc.png")
        PlayerProfile.objects.create(user=self.user, sleeve=sleeve)
        self.assertEqual(self.data()["player"]["sleeve"], sleeve.css)
        self.assertIn("url(", self.data()["player"]["sleeve"])

    def test_the_default_sleeve_is_the_empty_string_even_with_a_profile(self):
        PlayerProfile.objects.create(user=self.user)
        self.assertEqual(self.data()["player"]["sleeve"], "")

    def test_the_cpu_image_is_its_intro_art(self):
        with mock.patch.object(CpuProfile, "screen_url", return_value="/cpu/intro.png") as screen:
            self.assertEqual(self.data()["cpu"]["image"], "/cpu/intro.png")
        screen.assert_called_with("intro")

    def test_the_cpu_has_no_image_when_it_has_no_art(self):
        self.assertEqual(self.data()["cpu"]["image"], "")


class EntryPointTests(TestCase):
    """Each entry point's data has the frame's keys: the staff page's, the town's (a game under way) and the challenge's."""

    def setUp(self):
        test_world.DuelTests.setUp(self)  # a town save and a CPU who's here (the duel tests' setup, not their tests)

    def assertFrameKeys(self, data):
        self.assertEqual(set(data["player"]), PLAYER_KEYS)
        self.assertEqual(data["player"]["name"], self.user.username)
        self.assertIn("image", data["cpu"])

    def test_the_staff_page_data_has_the_frame_keys(self):
        pictured_set(30)
        self.client.force_login(self.user)
        response = self.client.get(reverse("weiss:world_minigame_data"), {"game": "memory", "cpu": self.cinder.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFrameKeys(response.json())

    def test_the_town_data_has_the_frame_keys(self):
        pictured_set(30)
        world.travel(self.save, "plaza")
        world.relation(self.save, self.cinder.pk)["points"] = 1000
        world.changed(self.save, "relations")
        world.start_minigame(self.save, self.cinder.pk, "memory")
        self.assertFrameKeys(world.minigame_data(self.save, self.user))

    def test_the_challenge_data_has_the_frame_keys(self):
        pictured_set(30)
        self.client.force_login(self.user)
        pending = {"game": "memory", "cpu": self.cinder.pk, "seed": 7, "decided": False}
        with mock.patch("weiss.challenge_views.minigame_under_way", return_value=(None, pending)):
            response = self.client.get(reverse("weiss:arcade_challenge_minigame_data"))
        self.assertEqual(response.status_code, 200)
        self.assertFrameKeys(response.json())
