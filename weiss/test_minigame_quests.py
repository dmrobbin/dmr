from . import quests, world
from .test_world_quests import QuestBase, make_quest, stage


class MinigameObjectiveTests(QuestBase):
    def under_way(self, key, *objectives):
        """A quest with these objectives, taken (its log set straight, as accept would)."""
        make_quest(key, giver=self.ruby, stages=[stage(*objectives)])
        quests.log(self.save)[key] = {"status": "active", "stage": 0, "since": self.save.turn, "progress": {}, "done": []}
        self.save.save()
        return self.fresh()

    def finish(self, cpu=None, game="memory", won=True):
        quests.minigame_finished(self.save, cpu, game, won)
        world.changed(self.save, "quests")  # as world.game_finished saves it
        return self.fresh()

    def progress(self, key, index=0):
        obj = quests.find_quest(self.save, key).spec["stages"][0]["objectives"][index]
        return quests.progress(self.save, quests.find_quest(self.save, key), f"0.{index}", obj)

    def test_the_check_takes_the_objective_and_says_what_is_wrong(self):
        _, problems = quests.check({"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "stages": [stage({"do": "minigame", "result": "lose"})],
                                    "endings": [{"key": "a", "title": "A"}]})
        self.assertTrue(any("result is one of any, win" in p for p in problems), problems)
        _, problems = quests.check({"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "stages": [stage({"do": "minigame", "game": "chess"})],
                                    "endings": [{"key": "a", "title": "A"}]})
        self.assertTrue(any("game is one of" in p for p in problems), problems)
        _, problems = quests.check({"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "stages": [stage({"do": "minigame", "result": "win", "game": "cups", "count": 2})],
                                    "endings": [{"key": "a", "title": "A"}]})
        self.assertEqual(problems, [])

    def test_a_win_objective_counts_only_wins(self):
        self.under_way("win", {"do": "minigame", "result": "win"})
        self.finish(won=False)
        self.assertEqual(self.progress("win"), (0, 1))
        self.finish(won=True)
        self.assertEqual(self.progress("win"), (1, 1))

    def test_a_play_objective_counts_every_result_and_its_count(self):
        self.under_way("play", {"do": "minigame", "count": 2})
        self.finish(won=False)
        self.assertEqual(self.progress("play"), (1, 2))
        self.finish(won=True)
        self.assertEqual(self.progress("play"), (2, 2))

    def test_a_named_game_counts_only_that_game(self):
        self.under_way("cups", {"do": "minigame", "result": "win", "game": "cups"})
        self.finish(game="memory")
        self.assertEqual(self.progress("cups"), (0, 1))
        self.finish(game="cups")
        self.assertEqual(self.progress("cups"), (1, 1))

    def test_a_named_cpu_counts_only_that_cpu(self):
        self.under_way("vs", {"do": "minigame", "result": "win", "cpu": "Ruby"})
        self.finish(cpu=self.cinder)
        self.assertEqual(self.progress("vs"), (0, 1))
        self.finish()  # no CPU at all: not against Ruby
        self.assertEqual(self.progress("vs"), (0, 1))
        self.finish(cpu=self.ruby)
        self.assertEqual(self.progress("vs"), (1, 1))

    def test_the_quest_log_says_what_it_is(self):
        self.under_way("words", {"do": "minigame", "result": "win", "game": "runner", "cpu": "Ruby", "count": 3})
        obj = quests.find_quest(self.save, "words").spec["stages"][0]["objectives"][0]
        self.assertEqual(quests.describe(self.save, obj), "Win a minigame (Runner) against Ruby 3 times")
