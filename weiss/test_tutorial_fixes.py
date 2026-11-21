from . import challenge, world, world_tutorial as tutorial
from .models import GiftItem
from .test_world_tutorial import TutorialBase


class TutorialFixTests(TutorialBase):
    def test_the_gift_step_always_has_a_gift_to_give(self):
        save = self.through("gift")
        self.assertGreaterEqual(sum(save.gifts.values()), 1)
        self.assertIn("gift-item", tutorial.view(save)["highlight"])

    def test_the_starter_gift_comes_once_when_the_step_begins(self):
        save = self.through("talk")
        world.talk(save, self.aang.pk)
        self.assertEqual(self.step(), "gift")
        self.assertEqual(sum(save.gifts.values()), 1)
        tutorial.said(save)  # the lines played again change nothing
        self.assertEqual(sum(save.gifts.values()), 1)

    def test_with_no_gifts_in_the_game_the_step_is_passed_not_stuck(self):
        GiftItem.objects.all().delete()
        save = self.through("talk")
        world.talk(save, self.aang.pk)
        self.assertEqual(self.step(), "map")

    def test_asking_someone_else_during_the_tutorial_gets_the_guides_refusal(self):
        save = self.through("talk")
        with self.assertRaisesRegex(ValueError, "Only your guide is here for now."):
            world.talk(save, self.other.pk)

    def test_the_duel_step_shows_the_map_first_when_the_time_needs_answering(self):
        save = self.through("minigame")
        world.start_minigame(save, self.aang.pk, "cups")
        save.today["minigame"]["started"] -= challenge.MINIGAME_MIN_SECONDS + 1
        save.save()
        world.finish_minigame(save, "win")  # time's passed: the map is to be answered before the duel
        save.refresh_from_db()
        self.assertEqual(self.step(), "duel")
        found = tutorial.view(save)
        self.assertTrue(found["highlight"][0].startswith("place-"))
        self.assertIn("Choose where to go next", found["hint"])

    def test_a_legal_deck_saved_then_back_in_the_town_moves_on_to_the_minigame(self):
        save = self.through("deck")  # the deck step, its lines not yet said
        self.assertEqual(self.step(), "deck")
        self.legal_deck()
        world.town(save)  # back in the town: the deck's step is done without its lines being said
        save.refresh_from_db()
        self.assertEqual(self.step(), "minigame")
