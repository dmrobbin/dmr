import random
from unittest import mock

from django.urls import reverse

from . import buffs, challenge, coop, play, scenes
from .event_scenes import STARTERS
from .models import ChallengeRun, ChallengeSettings, GameRoom, Scene
from .test_arcade import player
from .test_buffs import ChallengeBuffBase
from .test_challenge import ArcadeSetup
from .test_packs import make_set, run_with_climaxes

EVENT_SCRIPT = """narrator: A stranger offers you a deal.
give extra_packs
choice Take it?
- Yes (give ambush)
- No
"""


class PactTests(ChallengeBuffBase):
    def pool_of(self, copies):
        self.run.pool = {str(card.pk): n for card, n in zip(self.cards, copies)}
        self.run.save()

    def test_random_buffs_are_never_pacts_unless_asked_for(self):
        rng = random.Random(3)
        plain = {buff for _ in range(50) for buff in buffs.roll(3, rng)}
        self.assertFalse(any(buffs.BUFFS[b].pact for b in plain))
        pacts = {buff for _ in range(50) for buff in buffs.roll(2, rng, pacts=True)}
        self.assertTrue(pacts and all(buffs.BUFFS[b].pact for b in pacts))

    def test_scripts_ask_for_pacts(self):
        compiled, errors = scenes.compile_scene("give pact\noffer 2 pacts: Pick\nchoice x\n- y (give pact)\n- z")
        self.assertEqual(errors, [])
        payload = buffs.resolve(scenes.scene_payload(compiled, "Deals"), True, random.Random(1))
        given = [payload["steps"][0]["buff"], *(o["buff"] for o in payload["steps"][1]["options"]), payload["steps"][2]["options"][0]["give"]]
        self.assertEqual(len(given), 4)
        self.assertTrue(all(buffs.BUFFS[b].pact for b in given))

    def test_reforge_melts_spares_only(self):
        self.pool_of([3, 3, 3, 3, 3, 3])  # 18 cards
        play_set = {self.cards[0].pk: 3, self.cards[1].pk: 2}
        challenge.save_deck(self.run, play_set)
        packs = self.run.packs
        said = buffs.grant(self.run, ["reforge"], rng=random.Random(2))
        self.run.refresh_from_db()
        self.assertEqual(sum(self.run.pool.values()), 18 - buffs.REFORGE_CARDS)
        for pk, n in play_set.items():  # the deck's cards are all still there
            self.assertGreaterEqual(self.run.pool.get(str(pk), 0), n)
        self.assertEqual(dict(self.run.deck.entries.values_list("card_id", "quantity")), play_set)
        self.assertEqual(self.run.packs, packs + buffs.REFORGE_PACKS)
        self.assertIn(f"{buffs.REFORGE_CARDS} cards", said[0])

    def test_reforge_with_few_spares(self):
        self.pool_of([2, 1])
        challenge.save_deck(self.run, {self.cards[0].pk: 1})
        buffs.grant(self.run, ["reforge"])
        self.run.refresh_from_db()
        self.assertEqual(self.run.pool, {str(self.cards[0].pk): 1})  # the two spares went; the deck's copy stayed

    def test_sacrifice(self):
        self.pool_of([3, 2])
        challenge.save_deck(self.run, {self.cards[0].pk: 2})
        said = buffs.grant(self.run, ["sacrifice"])
        self.run.refresh_from_db()
        self.assertEqual(self.run.pool, {str(self.cards[1].pk): 2})  # every copy of the deck's card
        self.assertFalse(self.run.deck.entries.exists())
        self.assertEqual([r["buff"] for r in self.run.rewards], ["lucky_pack", "climax_pick"])
        self.assertIn("3 cards", said[0])

    def test_all_in(self):
        self.run.lives = 2
        self.run.save()
        buffs.grant(self.run, ["all_in"])
        self.run.refresh_from_db()
        self.assertEqual(self.run.lives, 0)
        self.assertEqual([r["buff"] for r in self.run.rewards], ["lucky_pack"] * 2 * buffs.ALL_IN_PACKS)
        said = buffs.grant(self.run, ["all_in"])
        self.assertIn("no second chances", said[0])

    def test_next_fight_pacts_change_the_fight_until_its_won(self):
        challenge.open_packs(self.run, 7, 2)
        challenge.save_deck(self.run, {pk: 1 for pk in self.run.pool})
        self.run = run_with_climaxes(self.run)
        packs = self.run.packs
        buffs.grant(self.run, ["ambush", "war_chest", "outpaced"])
        self.run.refresh_from_db()
        self.assertEqual(buffs.fight_mods(self.run), ["ambush", "war_chest", "outpaced"])
        self.assertEqual(self.run.packs, packs + buffs.OUTPACED_PACKS)
        page = self.client.get(reverse("weiss:arcade_challenge")).content.decode()
        self.assertIn("Your next fight, until you win it", page)
        self.assertIn("Ambush", page)
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        me = room.state["players"][str(room.host_id)]
        self.assertEqual((len(me["zones"]["clock"]), len(me["zones"]["stock"])), (buffs.AMBUSH_DAMAGE, buffs.WAR_CHEST))
        self.assertEqual(room.state["turn"], str(room.guest_id))  # outpaced: they go first
        self.assertNotIn("rps", room.state)
        packs = ChallengeRun.objects.get(pk=self.run.pk).packs
        self.end_fight("me")
        self.run.refresh_from_db()
        self.assertEqual(buffs.fight_mods(self.run), [])  # won: they're done with
        self.assertEqual(self.run.packs, packs + challenge.WIN_PACKS + buffs.AMBUSH_PACKS)

    def test_a_loss_with_a_second_chance_keeps_them(self):
        challenge.open_packs(self.run, 7, 2)
        challenge.save_deck(self.run, {pk: 1 for pk in self.run.pool})
        self.run = run_with_climaxes(self.run)
        buffs.grant(self.run, ["ambush", "second_chance"])
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        self.end_fight("cpu")
        self.run.refresh_from_db()
        self.assertEqual(buffs.fight_mods(self.run), ["ambush"])

    def test_a_blood_pact_cpu_plays_at_its_hardest(self):
        challenge.open_packs(self.run, 7, 2)
        challenge.save_deck(self.run, {pk: 1 for pk in self.run.pool})
        self.run = run_with_climaxes(self.run)
        buffs.grant(self.run, ["blood_pact"])
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        room.state.pop("cpu_intro", None)
        room.save()
        with mock.patch.object(play.cpu, "next_action", return_value=None) as chooser:
            play.cpu_step(GameRoom.objects.get(pk=room.pk), wait=False)
        self.assertEqual((chooser.call_args.kwargs["model"], chooser.call_args.args[3]), ("hard", play.cpu.MAX_AGGRESSION))


class EventTests(ArcadeSetup):
    def setUp(self):
        super().setUp()
        make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4)
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "infinite"})
        self.run = challenge.current(self.staff)

    def event_scene(self, script=EVENT_SCRIPT, name="Deal"):
        return Scene.objects.create(name=name, script=script, infinite_event=True)

    def lay(self, *floors, picks=()):
        """A path of these floors (CPU profiles, or challenge.EVENT), at its start."""
        ids = [[node if node == challenge.EVENT else node.pk for node in floor] for floor in floors]
        self.run.path = {"floors": ids, "picks": list(picks), "done": 0}
        self.run.save()

    def enter(self, node=0):
        return self.client.post(reverse("weiss:arcade_challenge_fight"), {"node": node})

    def state(self):
        self.run.refresh_from_db()
        return self.run.path

    def save_settings(self, **changes):
        """The infinite settings form as it is, with these changes, posted."""
        form = {"event_percent": "60", "start_packs": "20", **{f"loadout_{buff}": "0" for buff in challenge.LOADOUT_BUFFS},
                **{f"tier_{i}": str(count) for i, (count, _) in enumerate(challenge.INFINITE_MODELS)},
                "coop_loss_limit": "3", "coop_start_packs": "20", **{f"coop_loadout_{buff}": "0" for buff in challenge.LOADOUT_BUFFS},
                "boss_every": "5", "coop_boss_every": "5", "coop_boss_health": "42"}
        return self.client.post(reverse("weiss:cpu_infinite_settings"), {**form, **{k: str(v) for k, v in changes.items()}})

    def test_staff_set_what_a_challenge_starts_with(self):
        page = self.client.get(reverse("weiss:cpu_home") + "?tab=infinite")
        self.assertContains(page, f'name="start_packs" min="0" max="60" value="{challenge.INFINITE_START_PACKS}"')
        self.save_settings(start_packs=8, loadout_climax_pack=2, loadout_color_pack=1)
        self.assertEqual(ChallengeSettings.current().loadout, {"climax_pack": 2, "color_pack": 1})
        challenge.reset(self.run)
        self.run.refresh_from_db()
        self.assertEqual(self.run.packs, 8)
        self.assertEqual(sorted(r["buff"] for r in self.run.rewards), ["climax_pack", "climax_pack", "color_pack"])
        self.assertEqual({r["source"] for r in self.run.rewards}, {"Starting loadout"})
        free = challenge.start(player("bo"), ChallengeRun.Kind.FREE, None)  # only the infinite challenge's
        self.assertEqual((free.packs, free.rewards), (challenge.START_PACKS, []))

    def test_a_challenge_must_start_with_something(self):
        self.save_settings(start_packs=0)
        self.assertIsNone(ChallengeSettings.current())
        self.save_settings(start_packs=0, loadout_lucky_pack=3)
        self.assertEqual(challenge.start_packs(ChallengeRun.Kind.INFINITE), 0)
        for bad in ({"start_packs": 61}, {"loadout_wild_pack": -1}, {"tier_0": "x"}, {"tier_2": 31}):
            self.save_settings(**bad)
            self.assertEqual(ChallengeSettings.current().loadout, {"lucky_pack": 3})

    def test_staff_set_the_difficulty_curve(self):
        self.assertEqual([challenge.tier(f) for f in range(7)], ["Easy"] * 2 + ["Standard"] + ["Tough"] * 3 + ["Hard"])
        self.save_settings(tier_0=1, tier_1=0, tier_2=2)
        self.assertEqual([challenge.tier(f) for f in range(4)], ["Easy", "Tough", "Tough", "Hard"])
        self.assertContains(self.client.get(reverse("weiss:cpu_home") + "?tab=infinite"), "Hard from floor 4")

    def test_staff_set_the_coop_challenge(self):
        self.assertEqual((coop.loss_limit(), coop.start_packs(), coop.loadout()), (coop.LOSS_LIMIT, coop.START_PACKS, []))
        self.assertContains(self.client.get(reverse("weiss:cpu_home") + "?tab=infinite"), f'name="coop_loss_limit" min="1" max="20" value="{coop.LOSS_LIMIT}"')
        self.save_settings(coop_loss_limit=5, coop_start_packs=10, coop_loadout_level_pack=2)
        self.assertEqual((coop.loss_limit(), coop.start_packs(), coop.loadout()), (5, 10, ["level_pack", "level_pack"]))
        self.assertEqual((challenge.infinite_start_packs(), challenge.loadout()), (20, []))  # solo's are apart
        for bad in ({"coop_loss_limit": 0}, {"coop_loss_limit": 21}, {"coop_loadout_wild_pack": 11}, {"coop_start_packs": 0, "coop_loadout_level_pack": 0}):
            self.save_settings(**bad)
            self.assertEqual(coop.loss_limit(), 5)

    def test_staff_set_the_bosses(self):
        self.assertEqual((challenge.boss_every(), challenge.boss_every(coop=True), coop.boss_health()),
                         (challenge.BOSS_EVERY, challenge.BOSS_EVERY, coop.BOSS_HEALTH))
        page = self.client.get(reverse("weiss:cpu_home") + "?tab=infinite")
        self.assertContains(page, f'name="coop_boss_health" min="1" max="200" value="{coop.BOSS_HEALTH}"')
        self.assertContains(page, "none marked, so any CPU can be one")
        self.save_settings(boss_every=0, coop_boss_every=3, coop_boss_health=60)
        self.assertEqual((challenge.boss_every(), challenge.boss_every(coop=True), coop.boss_health()), (0, 3, 60))
        for bad in ({"boss_every": -1}, {"coop_boss_every": 51}, {"coop_boss_health": 0}):
            self.save_settings(**bad)
            self.assertEqual(coop.boss_health(), 60)

    def test_staff_mark_cpus_as_bosses(self):
        cpu = self.opener
        form = {"name": cpu.name, "model": cpu.model, "aggression": cpu.aggression, "deck": cpu.deck_id, "boss": "on"}
        self.client.post(reverse("weiss:cpu_profile_update", args=[cpu.pk]), form)
        cpu.refresh_from_db()
        self.assertTrue(cpu.boss)
        self.assertNotContains(self.client.get(reverse("weiss:cpu_home") + "?tab=infinite"), "none marked")
        form.pop("boss")
        self.client.post(reverse("weiss:cpu_profile_update", args=[cpu.pk]), form)
        cpu.refresh_from_db()
        self.assertFalse(cpu.boss)

    def test_staff_set_how_often_the_path_offers_an_event(self):
        self.event_scene()
        self.assertEqual(challenge.event_chance(), challenge.EVENT_CHANCE)  # never set: the default
        page = self.client.get(reverse("weiss:cpu_home") + "?tab=infinite")
        self.assertContains(page, f'value="{round(challenge.EVENT_CHANCE * 100)}"')
        self.assertNotContains(page, "There are no event scenes")
        self.save_settings(event_percent="0")
        self.assertEqual(challenge.event_chance(), 0)
        self.assertEqual(ChallengeSettings.current().updated_by, self.staff)
        self.assertFalse(any(challenge.EVENT in floor for floor in challenge.path_of(self.run)["floors"]))
        self.save_settings(event_percent="100")
        self.run.path = {}
        path = challenge.path_of(self.run)
        self.assertTrue(all(challenge.EVENT in floor for floor in path["floors"][1:]))  # every floor but the first
        for bad in ("101", "-5", "lots"):
            self.save_settings(event_percent=bad)
            self.assertEqual(ChallengeSettings.current().event_percent, 100)

    def test_only_staff_set_it(self):
        self.client.force_login(player("ann"))
        self.save_settings(event_percent="10")
        self.assertIsNone(ChallengeSettings.current())

    def test_no_events_without_event_scenes(self):
        with mock.patch.object(challenge, "EVENT_CHANCE", 1):
            path = challenge.path_of(self.run)
        self.assertFalse(any(challenge.EVENT in floor for floor in path["floors"]))

    def test_events_on_the_path(self):
        self.event_scene()
        Scene.objects.create(name="Broken", script="nonsense line", infinite_event=True)  # left out: it has mistakes
        self.assertEqual([s.name for s in challenge.event_scenes()], ["Deal"])
        with mock.patch.object(challenge, "EVENT_CHANCE", 1):
            path = challenge.path_of(self.run)
        self.assertNotIn(challenge.EVENT, path["floors"][0])  # never the first floor
        for floor in path["floors"][1:]:
            self.assertEqual(floor.count(challenge.EVENT), 1)
            self.assertLessEqual(len([pk for pk in floor if pk is not None]), max(challenge.PATH_WIDTHS))
        page = self.client.get(reverse("weiss:arcade_challenge")).content.decode()
        self.assertIn('<span class="spire-name">Event</span>', page)

    def test_events_go_if_there_are_no_event_scenes_any_more(self):
        scene = self.event_scene()
        self.lay([self.opener, self.filler], [challenge.EVENT, self.anchor])
        scene.delete()
        self.assertEqual(challenge.path_of(self.run)["floors"][1], [None, None, self.anchor.pk])  # an older path, put on the grid

    def test_an_event_plays_its_scene_and_gives_what_was_chosen(self):
        self.event_scene()
        self.lay([challenge.EVENT, self.opener], [self.filler, self.anchor])
        self.assertRedirects(self.enter(0), reverse("weiss:arcade_challenge_event"))  # no deck needed for an event
        payload = self.state()["event"]
        self.assertEqual(payload["title"], "Deal")
        page = self.client.get(reverse("weiss:arcade_challenge_event"))
        self.assertContains(page, "scene-payload")
        self.assertRedirects(self.enter(1), reverse("weiss:arcade_challenge_event"))  # the event's under way: back to it
        packs = self.run.packs
        response = self.client.post(reverse("weiss:arcade_challenge_event_done"), {"key": payload["key"], "buffs": "[[1, null], [2, 0]]"}, follow=True)
        self.assertContains(response, "Ambush")
        self.run.refresh_from_db()
        self.assertEqual(self.run.packs, packs + buffs.EXTRA_PACKS)
        self.assertEqual(buffs.fight_mods(self.run), ["ambush"])
        path = self.state()
        self.assertEqual((challenge.floor_at(self.run), path.get("event")), (1, None))  # up a floor
        self.assertEqual(challenge.defeated(self.run), [])  # an event isn't a win
        self.assertEqual(challenge.choices(path, 1), [0])  # from the left: the left; the right's out of reach
        self.assertEqual(path["seen"], [Scene.objects.get(name="Deal").pk])

    def test_walking_away_gives_nothing(self):
        self.event_scene()
        self.lay([challenge.EVENT, self.opener], [self.filler, self.anchor])
        self.enter(0)
        key = self.state()["event"]["key"]
        self.client.post(reverse("weiss:arcade_challenge_event_done"), {"key": "stale", "buffs": "[[1, 0]]"})
        self.assertTrue(self.state().get("event"))  # an old page's: nothing
        packs = self.run.packs
        self.client.post(reverse("weiss:arcade_challenge_event_done"), {"key": key, "buffs": "[]"})
        self.run.refresh_from_db()
        self.assertEqual((self.run.packs, buffs.fight_mods(self.run), challenge.floor_at(self.run)), (packs, [], 1))

    def test_an_event_with_no_scene_left_is_passed_by(self):
        scene = self.event_scene()
        self.lay([challenge.EVENT, self.opener], [self.filler, self.anchor])
        with mock.patch.object(scenes, "playable", return_value=[]):  # say it gained a mistake as it was chosen
            response = self.client.post(reverse("weiss:arcade_challenge_fight"), {"node": 0}, follow=True)
        self.assertContains(response, "Nothing happened")
        self.state()
        self.assertEqual((challenge.floor_at(self.run), self.run.path.get("event")), (1, None))
        scene.delete()

    def test_the_cpus_go_by_floor_events_and_all(self):
        self.event_scene()
        challenge.open_packs(self.run, 7, 2)
        challenge.save_deck(self.run, {pk: 1 for pk in self.run.pool})
        self.run = run_with_climaxes(self.run)
        self.lay([challenge.EVENT, self.opener], [self.filler, self.anchor], [self.opener, self.anchor], [self.filler, self.anchor])
        self.enter(0)
        self.client.post(reverse("weiss:arcade_challenge_event_done"), {"key": self.state()["event"]["key"], "buffs": "[]"})
        self.enter(0)
        room = GameRoom.objects.get(host=self.staff)
        self.state()
        self.assertEqual(challenge.floor_at(self.run), 1)
        self.end_fight("me")
        self.run.refresh_from_db()
        self.assertEqual((challenge.floor_at(self.run), challenge.defeated(self.run)), (2, [room.cpu_profile_id]))


class EventSetupTests(ArcadeSetup):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_the_starter_events_are_written_right(self):
        for name, script in STARTERS:
            self.assertEqual(scenes.compile_scene(script)[1], [], name)

    def test_adding_the_starter_events(self):
        Scene.objects.create(name=STARTERS[0][0], script="narrator: Mine.")
        self.client.post(reverse("weiss:cpu_starter_events"))
        self.assertEqual(Scene.objects.filter(infinite_event=True).count(), len(STARTERS) - 1)  # one of that name already
        self.assertEqual(Scene.objects.get(name=STARTERS[0][0]).script, "narrator: Mine.")
        self.client.post(reverse("weiss:cpu_starter_events"))
        self.assertEqual(Scene.objects.count(), len(STARTERS))

    def test_making_a_scene_an_event(self):
        scene = Scene.objects.create(name="Mine", script="narrator: Hi.")
        self.client.post(reverse("weiss:cpu_scene_event", args=[scene.pk]), {"on": "1"})
        self.assertTrue(Scene.objects.get(pk=scene.pk).infinite_event)
        self.assertContains(self.client.get(reverse("weiss:cpu_home") + "?tab=scenes"), "Not an event")
        self.client.post(reverse("weiss:cpu_scene_event", args=[scene.pk]), {"on": "0"})
        self.assertFalse(Scene.objects.get(pk=scene.pk).infinite_event)

    def test_staff_only(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("weiss:cpu_starter_events"))
        self.assertFalse(Scene.objects.exists())
