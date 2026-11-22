from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase

from . import arcade
from .models import ArcadeRun, ArcadeScenario


class TrophyTests(TestCase):
    def scenario(self, name="Ark"):
        return ArcadeScenario.objects.create(name=name)

    def players(self, scenario, scores):
        """One player per score, each with a cleared run on the scenario."""
        for i, score in enumerate(scores):
            user = User.objects.create_user(f"p{scenario.pk}-{i}")
            ArcadeRun.objects.create(user=user, scenario=scenario, scenario_name=scenario.name, score=score, status=ArcadeRun.Status.CLEARED)

    def test_no_average_below_five_players(self):
        scenario = self.scenario()
        self.players(scenario, [100, 100, 100, 100])
        self.assertNotIn(scenario.pk, arcade.trophy_averages())
        self.assertIsNone(arcade.trophy(100, arcade.trophy_averages().get(scenario.pk)))

    def test_the_average_is_of_everyones_best(self):
        scenario = self.scenario()
        self.players(scenario, [80, 90, 100, 110, 120])
        self.assertEqual(arcade.trophy_averages()[scenario.pk], 100)
        user = User.objects.create_user("again")
        ArcadeRun.objects.create(user=user, scenario=scenario, scenario_name=scenario.name, score=300, status=ArcadeRun.Status.CLEARED)
        ArcadeRun.objects.create(user=user, scenario=scenario, scenario_name=scenario.name, score=50, status=ArcadeRun.Status.CLEARED)
        self.assertEqual(round(arcade.trophy_averages()[scenario.pk]), round((80 + 90 + 100 + 110 + 120 + 300) / 6))

    def test_each_tier_boundary(self):
        cases = [(74, "Small", 1), (75, "Medium", 2), (124, "Medium", 2), (125, "Large", 3), (174, "Large", 3), (175, "Huge", 4), (1000, "Huge", 4)]
        for score, tier, level in cases:
            found = arcade.trophy(score, 100)
            self.assertEqual((found["tier"], found["level"]), (tier, level), score)
            self.assertEqual(found["ratio"], round(score / 100, 2))
            self.assertEqual(found["average"], 100)

    def test_a_scenario_not_cleared_gets_no_trophy(self):
        scenario = SimpleNamespace(pk=1, clears=0, my_best=100)
        arcade.attach_trophy(scenario, {1: 100})
        self.assertIsNone(scenario.trophy)
        scenario.clears = 1
        arcade.attach_trophy(scenario, {1: 100})
        self.assertEqual(scenario.trophy["tier"], "Medium")
