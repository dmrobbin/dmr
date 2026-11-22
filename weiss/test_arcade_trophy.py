from django.contrib.auth.models import User
from django.test import TestCase

from . import arcade
from .models import ArcadeEntry, ArcadeRun, ArcadeScenario, CpuProfile


class TrophyTests(TestCase):
    def scenario(self, fights=2, branches=0):
        scenario = ArcadeScenario.objects.create(name=f"Ark {ArcadeScenario.objects.count()}")
        roles = [ArcadeEntry.Role.OPENER] + [ArcadeEntry.Role.FILLER] * (fights - 2) + [ArcadeEntry.Role.ANCHOR] + [ArcadeEntry.Role.BRANCH] * branches
        for i, role in enumerate(roles):
            ArcadeEntry.objects.create(scenario=scenario, cpu=CpuProfile.objects.create(name=f"C{scenario.pk}-{i}"), role=role)
        return scenario

    def clear(self, user, scenario, score):
        ArcadeRun.objects.create(user=user, scenario=scenario, scenario_name=scenario.name, score=score, status=ArcadeRun.Status.CLEARED)

    def test_par_is_per_win_times_the_fights_and_a_branch_adds_nothing(self):
        self.assertEqual(arcade.par(self.scenario(fights=2)), 2 * arcade.PAR_PER_WIN)
        self.assertEqual(arcade.par(self.scenario(fights=3, branches=2)), 3 * arcade.PAR_PER_WIN)

    def test_a_single_player_gets_a_trophy(self):
        scenario = self.scenario(fights=2)
        scenario.my_best = arcade.par(scenario)  # exactly par
        scenario.clears = 1
        arcade.attach_trophy(scenario)
        self.assertEqual((scenario.trophy["tier"], scenario.trophy["ratio"], scenario.trophy["par"]), ("Medium", 1.0, 2 * arcade.PAR_PER_WIN))

    def test_other_players_scores_do_not_change_your_trophy(self):
        scenario = self.scenario(fights=2)
        self.clear(User.objects.create_user("me"), scenario, 4000)
        scenario.clears, scenario.my_best = 1, 4000
        arcade.attach_trophy(scenario)
        before = scenario.trophy
        self.clear(User.objects.create_user("star"), scenario, 900000)
        arcade.attach_trophy(scenario)
        self.assertEqual(scenario.trophy, before)

    def test_each_tier_boundary_against_par(self):
        par = 2 * arcade.PAR_PER_WIN
        cases = [(0.74, "Small", 1), (0.75, "Medium", 2), (1.24, "Medium", 2), (1.25, "Large", 3), (1.74, "Large", 3), (1.75, "Huge", 4), (10, "Huge", 4)]
        for ratio, tier, level in cases:
            found = arcade.trophy(round(par * ratio), par)
            self.assertEqual((found["tier"], found["level"]), (tier, level), ratio)

    def test_no_trophy_without_a_clear(self):
        scenario = self.scenario(fights=2)
        scenario.clears, scenario.my_best = 0, 99999
        arcade.attach_trophy(scenario)
        self.assertIsNone(scenario.trophy)
        self.assertIsNone(arcade.trophy(99999, 0))
