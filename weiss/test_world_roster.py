"""World mode: the cast a few at a time (weiss.world_roster), newcomers' arrival scenes, and talk points."""
import json
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import world, world_events as events, world_roster as roster
from .models import CpuSchedule, Scene, WorldSettings
from .test_world import SET, everywhere_rule, give_cpu, make_set, staff_user
from .test_world_quests import make_quest, stage

WEEK = 28  # turns in a week
PLACES = ("plaza", "cafe", "library", "arena", "shrine", "beach", "forest", "school")


class RosterBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cards = make_set()

    def setUp(self):
        self.user = staff_user()
        self.cpus = []
        for n in range(30):
            cpu = give_cpu(f"Duelist {n:02}", self.cards)
            if n < 4:
                cpu.temperament = "villain"
                cpu.save()
            everywhere_rule(cpu, PLACES[n % len(PLACES)])
            self.cpus.append(cpu)

    def start(self):
        self.save = world.start(self.user, 1, SET)
        return self.save

    def next_week(self):
        """Let time pass to the next Monday morning (a new week)."""
        self.save.turn = (self.save.turn // WEEK + 1) * WEEK - 1
        world.time_passed(self.save)
        return self.save


class PlanTests(RosterBase):
    def test_a_new_save_starts_small_with_two_villains_and_everyone_placed_once(self):
        waves = self.start().roster["waves"]
        self.assertEqual(len(waves[0]), roster.START_CAST)
        villains = {cpu.pk for cpu in self.cpus if cpu.temperament == "villain"}
        self.assertGreaterEqual(len(set(waves[0]) & villains), 2)
        placed = [pk for wave in waves for pk in wave]
        self.assertEqual(sorted(placed), sorted(cpu.pk for cpu in self.cpus))
        self.assertTrue(all(len(wave) <= roster.WEEKLY_CAST for wave in waves[1:]))

    def test_the_plan_is_the_same_on_every_reload(self):
        save = self.start()
        self.assertEqual(roster.plan(save, roster.everyone()), save.roster["waves"])

    def test_characters_a_quest_ties_together_arrive_together(self):
        a, b, c = self.cpus[10], self.cpus[20], self.cpus[25]
        make_quest("rivals", a, stages=[stage({"do": "defeat", "cpus": [b.name]})])
        make_quest("theirs", c, endings=[{"key": "e", "title": "E", "locks": ["rivals"]}])
        waves = self.start().roster["waves"]
        wave_of = {pk: n for n, wave in enumerate(waves) for pk in wave}
        self.assertEqual(wave_of[a.pk], wave_of[b.pk])
        self.assertEqual(wave_of[a.pk], wave_of[c.pk])

    def test_only_those_in_town_are_drawn(self):
        save = self.start()
        first = set(save.roster["waves"][0])
        out = {cpu_id for time in range(4) for cpu_id in world.day_cast(save, 0)[time]}
        self.assertTrue(out and out <= first)
        self.next_week()
        out = {cpu_id for day in range(7, 14) for time in range(4) for cpu_id in world.day_cast(save, day)[time]}
        self.assertTrue(out <= first | set(save.roster["waves"][1]))

    def test_a_save_from_before_keeps_who_the_player_has_met(self):
        save = self.start()
        save.roster = {}
        met = self.cpus[29]
        save.relations = {str(met.pk): {"points": 5}}
        save.turn = 3 * WEEK
        save.save()
        roster.ensure(save)
        self.assertIn(met.pk, save.roster["waves"][0])
        self.assertEqual(save.roster["start_week"], 3)
        self.assertEqual(roster.released(save), set(save.roster["waves"][0]))

    def test_a_cpu_made_later_arrives_next_week(self):
        save = self.start()
        late = give_cpu("Late duelist", self.cards)
        everywhere_rule(late, "plaza")
        roster.ensure(save)
        self.assertIn(late.pk, save.roster["waves"][1])

    def test_the_tournament_draws_only_from_the_town(self):
        save = self.start()
        save.turn = 5 * 4  # Saturday
        save.save()
        self.assertTrue(set(events.eligible(save)) <= roster.released(save))

    def test_staff_set_the_cast_sizes(self):
        WorldSettings.objects.update_or_create(pk=1, defaults={"start_cast": 6, "weekly_cast": 2})
        waves = self.start().roster["waves"]
        self.assertEqual(len(waves[0]), 6)
        self.assertTrue(all(len(wave) <= 2 for wave in waves[1:]))


class ArrivalTests(RosterBase):
    """A newcomer's arrival scene plays when the player meets them, one at a time: never a week's worth in a row
    (docs/world-arrivals-plan.md, "Pacing change")."""

    def arrival(self, newcomer, resident):
        script = "\n".join([f"cast new as {newcomer.name}", f"cast old as {resident.name}", "background sakura",
                            "new: Hello, everyone!", "old: Oh, a new face.", "choice Who do you stand with?",
                            "- The newcomer (set side_new)", "- The one who was here first (set side_old, give climax_pack)"])
        return Scene.objects.create(name=f"World: Arrival, {newcomer.name} & {resident.name}", script=script)

    def cpu(self, pk):
        return next(cpu for cpu in self.cpus if cpu.pk == pk)

    def week_of_arrivals(self, how_many=None):
        """A save into its second week, with an arrival scene written for each of the week's newcomers."""
        save = self.start()
        resident = self.cpu(save.roster["waves"][0][0])
        newcomers = save.roster["waves"][1][:how_many]
        scenes = {pk: self.arrival(self.cpu(pk), resident) for pk in newcomers}
        self.next_week()
        return save, newcomers, scenes

    def out_now(self, save, among):
        """One of the newcomers out in town now, and where: the first of them, put at its haunt whatever the day's draw
        (which has caps, so it may have left them all at home), with everyone else where the draw has them."""
        pk = among[0]
        rule = CpuSchedule.objects.filter(cpu_id=pk).select_related("place").first()
        real = world.whereabouts
        patcher = mock.patch("weiss.world.whereabouts", side_effect=lambda s, turn=None: {**real(s, turn), pk: rule})
        patcher.start()
        self.addCleanup(patcher.stop)
        return pk, rule.place.key

    def test_a_new_week_says_who_arrived_and_plays_nothing_by_itself(self):
        save, newcomers, _ = self.week_of_arrivals()
        self.assertIn("New in town this week", " ".join(item["text"] for item in save.quests.get("news", [])))
        self.assertNotIn("scene", save.flags)  # no scene, let alone five in a row
        self.assertEqual(roster.pending(save), newcomers)

    def test_the_town_marks_a_newcomer_as_new_until_met(self):
        save, newcomers, _ = self.week_of_arrivals()
        pk, place = self.out_now(save, newcomers)
        save.place = place
        people = {person["id"]: person for person in world.town(save)["people"]}
        self.assertTrue(people[pk]["new"])
        roster.meet(save, pk)
        save.flags.pop("scene")
        people = {person["id"]: person for person in world.town(save)["people"]}
        self.assertFalse(people[pk]["new"])

    def test_talking_to_a_newcomer_plays_their_arrival_and_then_talks_as_usual(self):
        save, newcomers, scenes = self.week_of_arrivals()
        pk, place = self.out_now(save, newcomers)
        save.place = place
        save.flags.pop("choose", None)
        self.assertEqual(world.talk(save, pk), {"arrival": True})
        self.assertEqual((save.flags["scene"]["scene"], save.flags["scene"]["arrival"]), (scenes[pk].pk, pk))
        self.assertTrue(world.town(save)["scene"]["auto"])
        roster.arrival_done(save, ["side_new"], [])
        world.next_scene(save)
        self.assertIn("talk", world.talk(save, pk))  # an ordinary talk now

    def test_arriving_somewhere_meets_one_newcomer_at_most(self):
        save, newcomers, _ = self.week_of_arrivals()
        pk, place = self.out_now(save, newcomers)
        others = [other for other in newcomers if other != pk]
        for other in others:  # the rest of the week's newcomers are here too
            everywhere_rule(self.cpu(other), place)
        save.place = "nowhere"
        world.travel(save, place)
        met = save.flags["scene"]["arrival"]  # the first newcomer here, in the order they came (whoever the day put here)
        self.assertIn(met, newcomers)
        self.assertEqual(len(save.flags.get("scene_queue") or []), 0)  # nothing more waits to run on
        self.assertEqual(set(roster.pending(save)), set(newcomers) - {met})  # the rest wait to be met

    def test_a_scene_ending_never_starts_an_arrival(self):
        save, newcomers, _ = self.week_of_arrivals()
        world.next_scene(save)
        self.assertNotIn("scene", save.flags)
        self.assertEqual(roster.pending(save), newcomers)

    def test_nothing_is_met_while_another_scene_waits(self):
        save, newcomers, _ = self.week_of_arrivals()
        save.flags["scene"] = {"scene": 1, "auto": True}  # a quest visit's scene, say
        self.assertFalse(roster.meet(save, newcomers[0]))
        self.assertFalse(roster.meet_here(save))
        self.assertEqual(roster.pending(save), newcomers)

    def test_a_save_from_before_the_change_with_arrivals_waiting_carries_on(self):
        save, newcomers, _ = self.week_of_arrivals()
        save.flags["arrivals"] = [str(pk) for pk in newcomers]  # as an older save might hold them
        self.assertTrue(roster.meet(save, newcomers[0]))
        self.assertEqual(roster.pending(save), newcomers[1:])

    def test_the_choice_pays_the_side_taken_and_its_pack_or_coins(self):
        save, newcomers, _ = self.week_of_arrivals(1)
        newcomer = self.cpu(newcomers[0])
        roster.meet(save, newcomer.pk)
        before = save.money
        done = roster.arrival_done(save, ["side_new"], [])
        self.assertEqual(save.money - before, roster.ARRIVAL_COINS)
        self.assertEqual(save.relations[str(newcomer.pk)]["points"], world.gain(newcomer, roster.ARRIVAL_POINTS))
        self.assertIn(f"with {newcomer.name}", done["rewards"][0])
        self.assertNotEqual((save.flags.get("scene") or {}).get("arrival"), newcomer.pk)  # done: not again
        with self.assertRaises(ValueError):
            roster.arrival_done(save, ["side_new"], [])

    def test_siding_with_the_resident_can_give_a_pack(self):
        save = self.start()
        newcomer = self.cpu(save.roster["waves"][1][0])
        resident = self.cpu(save.roster["waves"][0][0])
        self.arrival(newcomer, resident)
        self.next_week()
        roster.meet(save, newcomer.pk)
        before = save.money
        done = roster.arrival_done(save, ["side_old"], ["climax_pack"])
        self.assertEqual(save.money, before)  # a pack instead of coins
        self.assertTrue(done["link"])
        self.assertEqual(save.relations[str(resident.pk)]["points"], world.gain(resident, roster.ARRIVAL_POINTS))

    def test_a_scene_with_someone_not_in_town_yet_isnt_played(self):
        save = self.start()
        newcomer = self.cpu(save.roster["waves"][1][0])
        later = self.cpu(save.roster["waves"][2][0])
        self.arrival(newcomer, later)
        solo = Scene.objects.create(name=f"World: Arrival, {newcomer.name}", script=f"cast new as {newcomer.name}\nnew: Hi!")
        self.next_week()
        roster.meet(save, newcomer.pk)
        self.assertEqual(save.flags["scene"]["scene"], solo.pk)  # its own scene instead

    def test_a_newcomer_with_no_scene_just_arrives(self):
        save = self.start()
        self.next_week()
        self.assertNotIn("scene", save.flags)
        self.assertNotIn("arrivals", save.flags)
        self.assertTrue(set(save.roster["waves"][1]) <= roster.released(save))

    def test_the_scene_page_sends_the_choice(self):
        save, newcomers, _ = self.week_of_arrivals(1)
        roster.meet(save, newcomers[0])
        save.save()
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_scene", args=[1]))
        self.assertContains(page, "data-scene-done")
        save.refresh_from_db()
        self.assertTrue(save.flags["scene"]["arrival"])  # kept until the choice is in
        answer = self.client.post(reverse("weiss:world_scene_done", args=[1]), {"state": json.dumps({"flags": ["side_new"], "buffs": []})})
        self.assertEqual(answer.status_code, 200)
        self.assertIn("coins", " ".join(answer.json()["rewards"]))
        again = self.client.post(reverse("weiss:world_scene_done", args=[1]), {"state": json.dumps({"flags": [], "buffs": []})})
        self.assertEqual(again.status_code, 400)


class TalkPointsTests(RosterBase):
    def test_talk_points_are_doubled_and_staff_set_them(self):
        self.assertEqual(world.talk_points(), 6)
        WorldSettings.objects.update_or_create(pk=1, defaults={"talk_points": 10})
        self.assertEqual(world.talk_points(), 10)
        save = self.start()
        cpu_id, rule = next(iter(world.whereabouts(save).items()))
        save.place = rule.place.key
        save.save()
        world.talk(save, cpu_id)
        cpu = next(cpu for cpu in self.cpus if cpu.pk == cpu_id)
        self.assertEqual(save.relations[str(cpu_id)]["points"], world.gain(cpu, 10))
