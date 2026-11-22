from django.test import SimpleTestCase

from . import game


def duel(turn=1, levels=(0, 0)):
    """A duel's state with these many level cards on each side, at this turn."""
    return {"turn_number": turn, "players": {str(pk): {"zones": {"level": [None] * n}} for pk, n in zip((1, 2), levels)}}


class IntensityTests(SimpleTestCase):
    def test_level_0_at_the_start(self):
        self.assertEqual(game.intensity(duel(turn=1)), 0)

    def test_level_1_once_a_turn_has_passed(self):
        self.assertEqual(game.intensity(duel(turn=2)), 1)
        self.assertEqual(game.intensity(duel(turn=9, levels=(0, 1))), 1)  # one level each is 3 life: still 1

    def test_level_2_when_either_player_has_two_life_or_fewer(self):
        self.assertEqual(game.intensity(duel(turn=2, levels=(2, 0))), 2)
        self.assertEqual(game.intensity(duel(turn=2, levels=(0, 2))), 2)
        self.assertEqual(game.intensity(duel(turn=2, levels=(1, 1))), 1)  # three life each: not yet

    def test_level_3_when_either_player_has_one_life_or_fewer(self):
        self.assertEqual(game.intensity(duel(turn=2, levels=(3, 0))), 3)
        self.assertEqual(game.intensity(duel(turn=2, levels=(0, 3))), 3)
        self.assertEqual(game.intensity(duel(turn=2, levels=(2, 2))), 2)  # two life each: 2, not 3

    def test_the_life_count_is_the_levels_left(self):
        self.assertEqual(game.life(duel(levels=(0, 0)), "1"), game.LOSING_LEVEL)
        self.assertEqual(game.life(duel(levels=(3, 0)), "1"), 1)
