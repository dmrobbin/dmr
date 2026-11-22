"""World mode's play layer: the pages the town frames in its own stage (same-origin only), the rank-up scene that plays
right away with whatever was waiting kept next in the queue, and a scene's one playing (a scene left early is not
played again; one never reported done waits for the next travel)."""
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import world
from .models import Chatter, GameRoom, Scene
from . import test_world

SAME_ORIGIN = "SAMEORIGIN"
DONE_EMPTY = '{"flags": [], "buffs": []}'  # what the scene page posts when a scene is left with no choices made


class PlayLayerBase(TestCase):
    """A town with a duel-ready save and a CPU who's here (the duel tests' setup, without their tests)."""

    def setUp(self):
        test_world.DuelTests.setUp(self)
        self.client.force_login(self.user)
        world.relation(self.save, self.cinder.pk)["points"] = 1000  # friends enough to play a game
        world.changed(self.save, "relations")
        self.opening = Scene.objects.create(name="Opening", script="background sakura\nnarrator: Something happens.")
        self.rank_scene = Scene.objects.create(name="Rank up", script="background cafe\nnarrator: Friends now.")

    def fresh(self):
        self.save.refresh_from_db()
        self.save.__dict__.pop("_quests", None)
        return self.save


class FramedPagesTests(PlayLayerBase):
    """The pages the town frames answer X-Frame-Options SAMEORIGIN (anything else stays DENY)."""

    def assertSameOrigin(self, url):
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 404, url)
        self.assertEqual(response.get("X-Frame-Options"), SAME_ORIGIN, url)

    def test_the_scene_page(self):
        world.queue_scene(self.save, "Opening")
        self.assertSameOrigin(reverse("weiss:world_scene", args=[self.save.slot]))

    def test_the_duel_room(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.assertIsInstance(room, GameRoom)
        self.assertSameOrigin(reverse("weiss:play_room", args=[room.pk]))

    def test_the_rooms_list_a_duel_page_links_back_to(self):
        self.assertSameOrigin(reverse("weiss:play_rooms"))

    def test_the_pack_reveal(self):
        self.save.packs = 1
        self.save.save(update_fields=["packs"])
        world.open_packs(self.save, 1)
        self.assertSameOrigin(reverse("weiss:world_opened", args=[self.save.slot]))

    def test_the_minigame_page(self):
        world.travel(self.save, "plaza")
        world.start_minigame(self.save, self.cinder.pk, "memory")
        self.assertSameOrigin(reverse("weiss:world_minigame_play", args=[self.save.slot]))

    def test_the_town_the_frame_navigates_back_to(self):
        self.assertSameOrigin(reverse("weiss:world_town", args=[self.save.slot]))

    def test_the_save_page_the_pack_reveal_links_to(self):
        self.assertSameOrigin(reverse("weiss:world_save", args=[self.save.slot]))

    def test_the_saves_list_and_new_game_the_save_page_links_to(self):
        self.assertSameOrigin(reverse("weiss:world_home"))
        self.assertSameOrigin(reverse("weiss:world_new", args=[2]))

    def test_pages_outside_the_play_layer_stay_denied(self):
        # Staff editors (here the places editor) are never reached from the town's flow, so they keep the default DENY.
        response = self.client.get(reverse("weiss:world_places"))
        self.assertNotEqual(response.get("X-Frame-Options"), SAME_ORIGIN)


class RankUpSceneTests(PlayLayerBase):
    def test_a_waiting_scene_plays_after_a_rank_up_scene(self):
        world.queue_scene(self.save, "Opening")
        Chatter.objects.create(cpu=self.cinder, context="rank_up", min_rank=2, scene=self.rank_scene)
        world.rank_up(self.save, self.cinder, 2)  # the rank-up scene plays right away
        world.changed(self.save, "flags")
        save = self.fresh()
        self.assertEqual(save.flags["scene"]["scene"], self.rank_scene.pk)
        self.assertEqual([item["scene"] for item in save.flags["scene_queue"]], [self.opening.pk])

        url = reverse("weiss:world_scene", args=[self.save.slot])
        self.client.get(url)
        self.client.post(reverse("weiss:world_scene_done", args=[self.save.slot]), {"state": DONE_EMPTY})
        self.assertEqual(self.fresh().flags["scene"]["scene"], self.opening.pk)  # the waiting one is next, not lost

    def test_the_waiting_scenes_keep_their_order_at_the_front_of_the_queue(self):
        third = Scene.objects.create(name="Third", script="narrator: Last.")
        world.queue_scene(self.save, "Opening")
        world.queue_scene(self.save, "Third")
        world.changed(self.save, "flags")
        world.play_rank_scene(self.save, self.rank_scene.pk, self.cinder.pk)
        world.changed(self.save, "flags")
        save = self.fresh()
        self.assertEqual(save.flags["scene"]["scene"], self.rank_scene.pk)
        self.assertEqual([item["scene"] for item in save.flags["scene_queue"]], [self.opening.pk, third.pk])

    def test_nothing_waiting_means_no_queue(self):
        world.play_rank_scene(self.save, self.rank_scene.pk, self.cinder.pk)
        world.changed(self.save, "flags")
        self.assertEqual(self.fresh().flags["scene"]["scene"], self.rank_scene.pk)
        self.assertNotIn("scene_queue", self.fresh().flags)


class CutsceneRepeatTests(PlayLayerBase):
    def test_a_scene_left_early_with_no_choices_is_not_played_again(self):
        world.queue_scene(self.save, "Opening")
        world.changed(self.save, "flags")
        self.client.get(reverse("weiss:world_scene", args=[self.save.slot]))  # it's played; the player leaves early
        response = self.client.post(reverse("weiss:world_scene_done", args=[self.save.slot]), {"state": DONE_EMPTY})
        self.assertEqual(response.status_code, 200)
        save = self.fresh()
        self.assertIsNone(world.scene_waiting(save))
        self.assertEqual(self.client.get(reverse("weiss:world_scene", args=[self.save.slot])).status_code, 302)  # nothing to play
        world.travel(save, "cafe")  # the next travel
        self.assertIsNone(world.scene_waiting(self.fresh()))

    def test_a_scene_never_reported_done_waits_for_the_next_travel(self):
        world.queue_scene(self.save, "Opening")
        world.changed(self.save, "flags")
        self.client.get(reverse("weiss:world_scene", args=[self.save.slot]))  # played, but never reported done
        world.travel(self.fresh(), "cafe")  # the next travel
        pending = world.scene_waiting(self.fresh())
        self.assertIsNotNone(pending)
        self.assertEqual(pending["url"], reverse("weiss:world_scene", args=[self.save.slot]))
        response = self.client.get(pending["url"])
        self.assertEqual(response.status_code, 200)  # and it plays
        self.assertContains(response, "Opening")


class PacksFromTheTownTests(PlayLayerBase):
    """Packs opened from the town (its play layer's ?from=town) go back to the town; without it, as before."""

    def open_one_with_packs_left(self):
        self.save.packs = 2
        self.save.save(update_fields=["packs"])
        world.open_packs(self.save, 1)

    def test_the_packs_page_from_the_town_goes_back_to_it(self):
        self.open_one_with_packs_left()
        town = reverse("weiss:world_town", args=[self.save.slot])
        response = self.client.get(reverse("weiss:world_opened", args=[self.save.slot]) + "?from=town")
        self.assertEqual(response.context["actions"], [("Back to the town", town, True)])
        self.assertTrue(response.context["again"]["url"].endswith("/open/?from=town"))  # the next packs keep the flow

    def test_the_packs_page_without_it_goes_back_to_the_save(self):
        self.open_one_with_packs_left()
        save_page = reverse("weiss:world_save", args=[self.save.slot])
        response = self.client.get(reverse("weiss:world_opened", args=[self.save.slot]))
        self.assertEqual(response.context["actions"], [("Back to your save", save_page, False)])
        self.assertFalse(response.context["again"]["url"].endswith("?from=town"))

    def test_checkout_sends_the_packs_with_the_flow(self):
        with mock.patch("weiss.world.checkout", return_value={"packs": 1, "bought": ["Pack"]}):
            response = self.client.post(reverse("weiss:world_checkout", args=[self.save.slot]),
                                        {"version": str(self.save.version), "basket": "[]"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["go"].endswith("/opened/?from=town"), response.json())

    def test_the_next_packs_keep_the_flow_when_opened_from_the_town(self):
        self.save.packs = 2
        self.save.save(update_fields=["packs"])
        response = self.client.post(reverse("weiss:world_open", args=[self.save.slot]), {"count": "1", "from": "town"})
        self.assertTrue(response["Location"].endswith("/opened/?from=town"), response["Location"])
        response = self.client.post(reverse("weiss:world_open", args=[self.save.slot]), {"count": "1"})
        self.assertTrue(response["Location"].endswith("/opened/"), response["Location"])
