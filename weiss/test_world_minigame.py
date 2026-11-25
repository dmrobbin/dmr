from unittest import mock

from django.urls import reverse

from . import challenge, minigame_views, quests, world
from .test_minigames import make_set as pictured_set
from .test_world_quests import QuestBase


class WorldMinigameTests(QuestBase):
    def setUp(self):
        super().setUp()
        pictured_set(30)  # the pack a win gives comes from a pictured set (the CPUs' own are unpictured here)
        self.points(self.ruby, 1000)
        self.points(self.cinder, 1000)

    def play(self, cpu=None, game="memory"):
        return world.start_minigame(self.save, (cpu or self.ruby).pk, game)

    def finish(self, result):
        done = world.finish_minigame(self.save, result)
        self.fresh()
        if world.choosing(self.save):  # time's passed: the player says where to spend it (staying is an answer)
            world.travel(self.save, world.place_of(self.save).key)
        return done

    def ripen(self):
        """Pretend the game started long enough ago to count."""
        self.save.today["minigame"]["started"] -= challenge.MINIGAME_MIN_SECONDS + 1
        self.save.save()

    def test_a_stranger_or_a_cold_cpu_plays_no_game(self):
        self.points(self.ruby, 0)
        with self.assertRaisesRegex(ValueError, "doesn't want to play"):
            self.play()
        self.points(self.ruby, 1000)
        with mock.patch.object(quests, "estranged", return_value=True):
            with self.assertRaisesRegex(ValueError, "doesn't want to play"):
                self.play()

    def test_no_game_while_the_tutorial_is_on(self):
        self.save.flags["tutorial"] = {"step": "arrive", "said": False}
        self.save.save()
        with self.assertRaises(ValueError):
            self.play()

    def test_starting_spends_the_time_and_holds_the_time_of_day(self):
        turn = self.save.turn
        self.play()
        self.save.refresh_from_db()
        self.assertEqual(self.save.today["minigame"]["cpu"], self.ruby.pk)
        self.assertEqual(self.save.turn, turn)  # spent when the result is posted
        with self.assertRaisesRegex(ValueError, "Finish the game"):
            self.play(cpu=self.cinder)
        self.assertFalse(world.can_wait(self.save)[0])

    def test_once_a_day_per_cpu(self):
        self.play()
        self.ripen()
        self.finish("draw")
        self.fresh()
        with self.assertRaisesRegex(ValueError, "today already"):
            self.play()
        self.play(cpu=self.cinder)  # another CPU is another game

    def test_a_result_posted_too_early_counts_for_nothing(self):
        self.play()
        money, relation, rewards = self.save.money, dict(world.relation(self.save, self.ruby.pk)), list(self.save.rewards)
        with self.assertRaisesRegex(ValueError, "That game ended too quickly to count."):
            self.finish("win")
        self.fresh()
        self.assertEqual((self.save.money, world.relation(self.save, self.ruby.pk)["points"], self.save.rewards),
                         (money, relation["points"], rewards))
        self.assertIn("minigame", self.save.today)  # still to play: the game may be played again

    def test_after_the_minimum_a_result_counts_once(self):
        self.play()
        self.ripen()
        before = world.relation(self.save, self.ruby.pk)["points"]
        self.finish("draw")
        self.fresh()
        self.assertEqual(world.relation(self.save, self.ruby.pk)["points"], before + world.gain(self.ruby, world.talk_points() * 2))
        self.assertNotIn("minigame", self.save.today)
        with self.assertRaisesRegex(ValueError, "no game to finish"):
            self.finish("win")  # a second post for the same game

    def test_a_win_gives_triple_points_and_a_lucky_pack_from_the_cpus_set(self):
        self.play()
        self.ripen()
        before = world.relation(self.save, self.ruby.pk)["points"]
        done = self.finish("win")
        self.fresh()
        self.assertEqual(world.relation(self.save, self.ruby.pk)["points"], before + world.gain(self.ruby, world.talk_points() * 3))
        lucky = [r for r in self.save.rewards if r["buff"] == "lucky_pack"]
        self.assertEqual(len(lucky), 1)
        self.assertEqual(lucky[0]["set"], 30)
        self.assertTrue(any("lucky pack" in line for line in done["rewards"]))

    def test_the_lucky_pack_opens_from_its_set(self):
        self.play()
        self.ripen()
        self.finish("win")
        self.fresh()
        key = next(r["key"] for r in self.save.rewards if r["buff"] == "lucky_pack")
        cards_before = sum(self.save.pool.values())
        self.assertTrue(world.claim(self.save, key, {}))
        self.fresh()
        self.assertGreater(sum(self.save.pool.values()), cards_before)
        self.assertFalse(any(r["key"] == key for r in self.save.rewards))

    def test_a_rank_up_is_reported_and_its_rewards_given(self):
        self.points(self.ruby, world.ranks()[2]["points"] - 2)  # an acquaintance: a win takes them to a friend
        self.play()
        self.ripen()
        done = self.finish("win")
        self.assertEqual(done["rank_up"], "Friend")
        self.assertTrue(done["rewards"][0].startswith("+"))
        self.assertEqual(world.rank_of(self.fresh(), self.ruby.pk), 2)

    def test_the_world_lines_are_the_cpus_own_then_the_generic(self):
        lines = {"*": {"world": {"invite": ["Anyone?"], "again": ["Again, {player}?"]}},
                 "Ruby": {"world": {"invite": ["Ruby asks, {player}."]}}}
        self.play()
        with mock.patch.object(minigame_views, "pack_lines", return_value=lines):
            data = world.minigame_data(self.fresh(), self.user)
        self.assertEqual(data["lines"]["invite"], [f"Ruby asks, {self.user.username}."])
        self.assertEqual(data["lines"]["again"], [f"Again, {self.user.username}?"])
        self.assertEqual(set(data["lines"]), set(minigame_views.WORLD_MOMENTS))
        self.assertFalse(data["again"])

    def test_the_again_line_is_for_a_second_game_the_same_day(self):
        self.play()
        self.ripen()
        self.finish("draw")
        self.play(cpu=self.cinder)
        self.assertTrue(world.minigame_data(self.fresh(), self.user)["again"])

    def test_time_passes_when_the_result_is_posted(self):
        self.play()
        self.ripen()
        turn = self.save.turn
        self.finish("lose")
        self.fresh()
        self.assertEqual(self.save.turn, turn + 1)

    def test_the_result_reaches_the_quests_of_this_save_only(self):
        self.play()
        self.ripen()
        with mock.patch.object(quests, "minigame_finished") as counted:
            self.finish("win")
        counted.assert_called_once()
        self.assertIs(counted.call_args.args[0], self.save)
        self.assertEqual((counted.call_args.args[1].pk, counted.call_args.args[2], counted.call_args.args[3]), (self.ruby.pk, "memory", True))

    def test_the_town_move_plays_and_the_page_posts_back(self):
        self.client.force_login(self.user)
        version = world.town(self.save)["version"]
        answer = self.client.post(reverse("weiss:world_minigame", args=[1]), {"cpu": self.ruby.pk, "game": "cups", "version": version})
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.json()["go"], reverse("weiss:world_minigame_play", args=[1]))
        self.assertEqual(self.client.get(reverse("weiss:world_minigame_play", args=[1])).status_code, 200)
        data = self.client.get(reverse("weiss:world_minigame_data", args=[1])).json()
        self.assertEqual((data["game"], data["cpu"]["id"]), ("cups", self.ruby.pk))
        self.assertTrue(data["cards"])
        early = self.client.post(reverse("weiss:world_minigame_done", args=[1]), {"result": "win"})
        self.assertEqual(early.status_code, 400)
        self.assertEqual(early.json()["error"], "That game ended too quickly to count.")
        self.fresh()
        self.ripen()
        done = self.client.post(reverse("weiss:world_minigame_done", args=[1]), {"result": "win"}).json()
        self.assertEqual(done["redirect"], reverse("weiss:world_town", args=[1]))

    def test_the_town_says_what_a_game_gives_and_whether_it_is_on_offer(self):
        offer = next(p for p in world.town(self.fresh())["people"] if p["id"] == self.ruby.pk)["minigame"]
        self.assertTrue(offer["allowed"])
        self.assertEqual((offer["base"], offer["points"], offer["win_points"]),
                         (world.gain(self.ruby, world.talk_points()), world.gain(self.ruby, world.talk_points() * 2),
                          world.gain(self.ruby, world.talk_points() * 3)))
        self.play()
        offer = next(p for p in world.town(self.fresh())["people"] if p["id"] == self.ruby.pk)["minigame"]
        self.assertFalse(offer["allowed"])
        self.assertFalse(offer["played"])  # played counts once the result is posted
