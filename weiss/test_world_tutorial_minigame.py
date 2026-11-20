from . import challenge, world, world_tutorial as tutorial
from .test_minigames import make_set as pictured_set
from .test_world_tutorial import TutorialBase


class TutorialMinigameTests(TutorialBase):
    def setUp(self):
        super().setUp()
        pictured_set(30)  # the game plays from a pictured set

    def ripen(self, save):
        save.today["minigame"]["started"] -= challenge.MINIGAME_MIN_SECONDS + 1
        save.save()

    def play(self, save, game="cups"):
        world.start_minigame(save, self.aang.pk, game)
        self.ripen(save)

    def finish(self, save, result):
        world.finish_minigame(save, result)
        save.refresh_from_db()
        if world.choosing(save):  # time's passed: where to spend it
            world.travel(save, world.place_of(save).key)

    def test_the_minigame_step_sits_between_the_deck_and_the_duel(self):
        steps = tutorial.STEPS
        self.assertEqual(steps[steps.index("deck") + 1], "minigame")
        self.assertEqual(steps[steps.index("minigame") + 1], "duel")

    def test_only_the_game_is_open_until_it_is_played(self):
        save = self.through("minigame")
        self.refused(world.start_duel, save, self.aang.pk)
        self.refused(world.talk, save, self.aang.pk)
        self.refused(world.travel, save, "cafe")
        self.refused(world.wait, save)
        self.refused(world.start_minigame, save, self.other.pk, "cups")  # not the guide
        self.assertEqual(self.step(), "minigame")

    def test_the_guide_plays_easy_and_a_too_early_result_leaves_the_step(self):
        save = self.through("minigame")
        world.start_minigame(save, self.aang.pk, "cups")
        self.assertEqual(world.minigame_data(save, self.user.username)["difficulty"], "easy")
        with self.assertRaisesRegex(ValueError, "too quickly"):
            world.finish_minigame(save, "win")
        self.assertEqual(self.step(), "minigame")

    def test_a_win_completes_the_step_and_the_guide_answers_it(self):
        save = self.through("minigame")
        self.play(save)
        self.finish(save, "win")
        self.assertEqual(self.step(), "duel")
        self.assertEqual(save.flags["last_minigame"]["result"], "win")
        self.assertEqual(tutorial.state(save)["reply"], "minigame_win")
        self.assertTrue(tutorial.view(save)["lines"][0]["say"].startswith("Good game"))

    def test_a_loss_completes_the_step_and_the_guide_answers_it(self):
        save = self.through("minigame")
        self.play(save, "memory")
        self.finish(save, "lose")
        self.assertEqual(self.step(), "duel")
        self.assertEqual(tutorial.state(save)["reply"], "minigame_lose")

    def test_a_draw_completes_the_step_too(self):
        save = self.through("minigame")
        self.play(save, "runner")
        self.finish(save, "draw")
        self.assertEqual(self.step(), "duel")
        self.assertEqual(tutorial.state(save)["reply"], "minigame_lose")

    def test_the_duel_comes_after_the_game(self):
        save = self.through("minigame")
        self.play(save)
        self.finish(save, "win")
        room = world.start_duel(save, self.aang.pk)
        self.assertEqual(room.state["cpu_model"], "easy")
