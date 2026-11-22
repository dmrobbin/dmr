from django.test import SimpleTestCase

from . import game


def duel(levels=(0, 0), climax=(0, 0), tier=None):
    players = {}
    for pk, (lv, cl) in zip((1, 2), zip(levels, climax)):
        players[str(pk)] = {"zones": {"level": [None] * lv, "climax": [None] * cl}}
    state = {"turn_number": 1, "players": players}
    if tier is not None:
        state["music_tier"] = tier
    return state


class MusicTierTests(SimpleTestCase):
    def test_tier_0_at_the_start(self):
        self.assertEqual(game.music_tier(duel()), 0)

    def test_tier_1_after_a_level_up(self):
        self.assertEqual(game.music_tier(duel(levels=(1, 0))), 1)
        self.assertEqual(game.music_tier(duel(levels=(1, 1))), 2)

    def test_capped_at_6(self):
        self.assertEqual(game.music_tier(duel(levels=(4, 4))), 6)
        self.assertEqual(game.music_tier(duel(levels=(3, 3))), 6)
        self.assertEqual(game.music_tier(duel(levels=(2, 3))), 5)

    def test_never_falls(self):
        self.assertEqual(game.music_tier(duel(levels=(1, 0), tier=4)), 4)
        self.assertEqual(game.music_tier(duel(levels=(0, 0), tier=3)), 3)
        self.assertEqual(game.music_tier(duel(levels=(3, 0), tier=1)), 3)


class ClimaxTests(SimpleTestCase):
    def test_climax_on_while_a_climax_is_in_either_zone(self):
        self.assertFalse(game.climax_on(duel()))
        self.assertTrue(game.climax_on(duel(climax=(1, 0))))
        self.assertTrue(game.climax_on(duel(climax=(0, 1))))
        self.assertFalse(game.climax_on(duel(climax=(0, 0), levels=(2, 2))))


class MatchPointTests(SimpleTestCase):
    def test_off_at_two_life_each(self):
        self.assertFalse(game.match_point(duel(levels=(2, 2))))

    def test_on_when_either_side_is_at_one_life(self):
        self.assertTrue(game.match_point(duel(levels=(3, 0))))
        self.assertTrue(game.match_point(duel(levels=(0, 3))))

    def test_off_again_when_neither_is(self):
        self.assertFalse(game.match_point(duel(levels=(1, 1))))
        self.assertFalse(game.match_point(duel(levels=(0, 0))))
