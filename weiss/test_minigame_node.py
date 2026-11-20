from unittest import mock

from django.urls import reverse

from . import challenge
from .models import ChallengeRun, GameRoom
from .test_challenge import ArcadeSetup
from .test_minigames import make_set as pictured_set
from .test_packs import make_set


class MinigameNodeTests(ArcadeSetup):
    def setUp(self):
        super().setUp()
        make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4)
        pictured_set(30)
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "infinite"})
        self.run = challenge.current(self.staff)

    def lay(self, minigames=((0, 0),)):
        """A path whose first floor is opener, filler, and whose spaces in `minigames` are minigames."""
        self.run.path = {"floors": [[self.opener.pk, self.filler.pk, None], [self.anchor.pk, None, None]], "picks": [], "done": 0,
                         "minigames": [list(space) for space in minigames]}
        self.run.save()

    def enter(self, node=0):
        return self.client.post(reverse("weiss:arcade_challenge_fight"), {"node": node})

    def post_result(self, result, ripe=True):
        if ripe and (path := self.state()).get("minigame"):  # the game has run long enough to count
            path["minigame"]["started"] -= challenge.MINIGAME_MIN_SECONDS + 1
            self.run.path = path
            self.run.save()
        return self.client.post(reverse("weiss:arcade_challenge_minigame_done"), {"result": result})

    def state(self):
        self.run.refresh_from_db()
        return self.run.path

    def test_a_minigame_space_is_laid_on_a_fight_floor_but_not_the_first(self):
        self.run.path = {}
        with mock.patch.object(challenge, "MINIGAME_CHANCE", 1), mock.patch.object(challenge, "EVENT_CHANCE", 0):
            path = challenge.path_of(self.run)
        self.assertTrue(path["minigames"])
        for f, c in path["minigames"]:
            self.assertGreater(f, 0)
            self.assertIsNotNone(path["floors"][f][c])  # the space is a CPU's, the minigame's against them

    def test_no_minigame_spaces_without_the_chance(self):
        self.run.path = {}
        with mock.patch.object(challenge, "MINIGAME_CHANCE", 0):
            self.assertFalse(challenge.path_of(self.run).get("minigames"))

    def test_landing_on_a_minigame_starts_a_game_against_its_column_cpu(self):
        self.lay()
        response = self.enter(0)
        self.assertRedirects(response, reverse("weiss:arcade_challenge_minigame"))
        path = self.state()
        self.assertEqual(path["minigame"]["cpu"], self.opener.pk)
        self.assertIn(path["minigame"]["game"], challenge.MINIGAME_GAMES)
        self.assertFalse(GameRoom.objects.filter(host=self.staff, cpu_profile=self.opener).exists())  # no fight

    def test_the_minigame_needs_no_deck(self):
        self.lay()
        self.assertEqual(self.enter(0).status_code, 302)
        self.assertIn("minigame", self.state())

    def test_a_win_gives_a_lucky_pack_once_and_clears_the_space(self):
        self.lay()
        self.enter(0)
        packs = self.run.packs
        response = self.post_result("win")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rewards"], ["You won a lucky pack: claim it with your rewards."])
        run = ChallengeRun.objects.get(pk=self.run.pk)
        lucky = [r for r in run.rewards if r["buff"] == "lucky_pack" and r["source"] == "minigame"]
        self.assertEqual(len(lucky), 1)
        self.assertEqual(run.packs, packs)  # a lucky pack is a reward to claim, not packs
        path = self.state()
        self.assertNotIn("minigame", path)
        self.assertNotIn([0, 0], path["minigames"])
        self.assertEqual(path["done"], 1)

    def test_a_loss_or_a_draw_gives_nothing(self):
        for result in ("lose", "draw"):
            self.lay()
            self.enter(0)
            self.assertEqual(self.post_result(result).json()["rewards"], [])
            run = ChallengeRun.objects.get(pk=self.run.pk)
            self.assertFalse([r for r in run.rewards if r["source"] == "minigame"], result)

    def test_the_node_cannot_be_played_twice(self):
        self.lay()
        self.enter(0)
        self.post_result("win")
        second = self.post_result("win")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(sum(1 for r in ChallengeRun.objects.get(pk=self.run.pk).rewards if r["source"] == "minigame"), 1)
        self.assertNotIn([0, 0], self.state()["minigames"])

    def test_a_result_posted_too_early_gives_nothing_and_the_game_can_be_played_again(self):
        self.lay()
        self.enter(0)
        response = self.post_result("win", ripe=False)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "That game ended too quickly to count.")
        run = ChallengeRun.objects.get(pk=self.run.pk)
        self.assertFalse([r for r in run.rewards if r["source"] == "minigame"])
        self.assertIn("minigame", self.state())  # still to play
        self.assertEqual(self.post_result("win").status_code, 200)  # once it's run long enough

    def test_a_bad_result_is_refused(self):
        self.lay()
        self.enter(0)
        self.assertEqual(self.post_result("cheat").status_code, 400)
        self.assertIn("minigame", self.state())

    def test_a_solo_minigame_touches_no_world_save_or_bounty(self):
        from . import quests, world
        self.lay()
        self.enter(0)
        with mock.patch.object(quests, "minigame_finished") as bounties, mock.patch.object(world, "changed") as saved:
            self.post_result("win")
        bounties.assert_not_called()
        saved.assert_not_called()

    def test_the_game_data_has_its_seed_and_cards(self):
        self.lay()
        self.enter(0)
        data = self.client.get(reverse("weiss:arcade_challenge_minigame_data")).json()
        self.assertEqual(data["seed"], self.state()["minigame"]["seed"])
        self.assertTrue(data["cards"])
        self.assertEqual(data["cpu"]["id"], self.opener.pk)
