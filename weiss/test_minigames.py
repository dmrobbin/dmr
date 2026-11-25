from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import minigame_views
from .models import Card, CpuProfile
from .test_profile import player
from .test_world import give_cpu, staff_user


def make_set(set_id, characters=24, climaxes=4, pictured=True):
    """A set: characters at levels 0 to 3 and some climaxes, with pictures unless `pictured` is off."""
    cards = []
    for n in range(characters + climaxes):
        climax = n >= characters
        cards.append(Card(serial_number=f"S{set_id}-{n:03}", name=f"Card {set_id}-{n}", expansion=f"Set {set_id}", expansion_id=set_id,
                          card_type="Climax" if climax else "Character", level=None if climax else n % 4, power=1000 + n,
                          rarity="C", image_url=f"https://example.com/{set_id}-{n}.png" if pictured else ""))
    Card.objects.bulk_create(cards)
    return list(Card.objects.filter(expansion_id=set_id).order_by("serial_number"))


class MinigameTests(TestCase):
    def setUp(self):
        self.staff = staff_user()
        self.main = make_set(30)
        self.few = make_set(31, characters=4, climaxes=0)
        make_set(32, characters=20, climaxes=0, pictured=False)  # plenty of cards, none with pictures
        self.aang = give_cpu("Aang", self.main)
        self.solo = CpuProfile.objects.create(name="Solo", finalized=True)

    def data(self, **params):
        return self.client.get(reverse("weiss:world_minigame_data"), {"game": "memory", "cpu": self.aang.pk, **params})


class MinigamePageTests(MinigameTests):
    def test_the_page_renders_for_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("weiss:world_minigames"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-minigame-form")
        self.assertContains(response, "Climax Invaders")
        self.assertContains(response, "Aang")

    def test_the_page_offers_the_runner(self):
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("weiss:world_minigames")), 'value="runner">Runner')

    def test_the_page_is_refused_for_non_staff(self):
        self.client.force_login(player("alice"))
        self.assertEqual(self.client.get(reverse("weiss:world_minigames")).status_code, 403)

    def test_the_data_is_refused_for_non_staff(self):
        self.client.force_login(player("alice"))
        self.assertEqual(self.data().status_code, 403)


class MinigameDataTests(MinigameTests):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_the_cards_have_every_field_and_a_picture(self):
        body = self.data(difficulty="hard").json()
        self.assertEqual((body["game"], body["difficulty"]), ("memory", "hard"))
        self.assertEqual(set(body["cpu"]), {"id", "name", "portraits", "avatar", "image"})  # image: the intro art, or ""
        self.assertEqual(body["cpu"]["name"], "Aang")
        self.assertTrue(body["cards"])
        for card in body["cards"]:
            self.assertEqual(set(card), {"id", "name", "image", "level", "power", "cost", "color", "type", "trigger", "rarity"})
            self.assertEqual(card["image"], reverse("weiss:card_image", args=[card["id"]]))

    def test_the_cards_cover_every_level_and_some_climaxes(self):
        cards = self.data().json()["cards"]
        self.assertEqual({card["level"] for card in cards if card["type"] != "Climax"}, {0, 1, 2, 3})
        self.assertTrue(any(card["type"] == "Climax" for card in cards))

    def test_the_cards_come_from_the_cpus_deck_set(self):
        ids = {card["id"] for card in self.data().json()["cards"]}
        self.assertTrue(ids <= {card.pk for card in self.main})

    def test_a_set_with_too_few_pictured_cards_falls_back_to_another(self):
        erza = give_cpu("Erza", self.few)  # its deck's set has only four pictures
        ids = {card["id"] for card in self.client.get(reverse("weiss:world_minigame_data"),
                                                       {"game": "memory", "cpu": erza.pk}).json()["cards"]}
        self.assertTrue(ids <= {card.pk for card in self.main})

    def test_a_cpu_with_no_deck_still_plays(self):
        body = self.client.get(reverse("weiss:world_minigame_data"), {"game": "cups", "cpu": self.solo.pk}).json()
        self.assertTrue(body["cards"])

    def test_the_avatar_is_a_picture_url_or_null(self):
        self.assertIsNone(self.data().json()["cpu"]["avatar"])

    def test_the_runner_plays_from_the_same_cards_and_falls_back_to_the_generic_lines(self):
        with mock.patch.object(minigame_views, "pack_lines", return_value={"*": {"*": {"start": ["generic any"]}}}):
            body = self.data(game="runner").json()
        self.assertEqual(body["game"], "runner")
        self.assertTrue(body["cards"])
        self.assertEqual(body["lines"]["start"], ["generic any"])

    def test_an_unknown_game_is_an_error(self):
        response = self.data(game="snakes")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_an_unknown_difficulty_is_an_error(self):
        self.assertEqual(self.data(difficulty="impossible").status_code, 400)

    def test_an_unknown_cpu_is_an_error(self):
        self.assertEqual(self.data(cpu=999999).status_code, 404)

    def test_the_lines_fall_back_in_order(self):
        lines = {
            "*": {"*": {"start": ["generic any"], "win": ["generic win"]}, "memory": {"start": ["generic memory"]}},
            "Aang": {"*": {"win": ["Aang any win, {player}"]}, "memory": {"start": ["Aang memory start"]}},
        }
        with mock.patch.object(minigame_views, "pack_lines", return_value=lines):
            memory = self.data().json()["lines"]
            cups = self.data(game="cups").json()["lines"]
        self.assertEqual(memory["start"], ["Aang memory start"])  # the CPU's own, for the game
        self.assertEqual(memory["win"], ["Aang any win, staff"])  # then its own for any game, with the player's name
        self.assertEqual(memory["lose"], [])  # no layer has it
        self.assertEqual(cups["start"], ["generic any"])  # no Aang cups lines: the "*" for any game
        self.assertEqual(cups["win"], ["Aang any win, staff"])

    def test_the_lines_are_empty_without_the_file(self):
        with mock.patch.object(minigame_views, "LINES_FILE", Path("no-such-minigame-lines.json")):
            minigame_views.pack_lines.cache_clear()
            try:
                lines = self.data().json()["lines"]
            finally:
                minigame_views.pack_lines.cache_clear()
        self.assertEqual(set(lines), set(minigame_views.MOMENTS))
        self.assertTrue(all(value == [] for value in lines.values()))
