import json
import random
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import arcade, challenge, play, scenes
from .models import ArcadeEntry, ArcadeRun, ArcadeScenario, CardList, ChallengeRun, GameRoom, NarrativeChallenge, Scene
from .test_arcade import Base, player
from .test_packs import make_set
from .test_scenes import SCRIPT


class ArcadeSetup(Base):
    """A ready arcade list of three CPUs, and alice logged in."""

    def setUp(self):
        super().setUp()
        self.scenario = ArcadeScenario.objects.create(name="Ark")
        self.opener, self.filler, self.anchor = self.cpu("Rapi"), self.cpu("Anis"), self.cpu("Last")
        for cpu, role in ((self.opener, "opener"), (self.filler, "filler"), (self.anchor, "anchor")):
            ArcadeEntry.objects.create(scenario=self.scenario, cpu=cpu, role=role)
        self.client.force_login(self.alice)

    def post(self, url, action):
        return self.client.post(url, json.dumps(action), content_type="application/json")

    def room(self):
        return GameRoom.objects.get(host__in=[self.alice, self.staff])

    def end_fight(self, winner):
        """End the room's game, as if the last move had just been made."""
        room = self.room()
        room.state.pop("cpu_intro", None)
        room.state.pop("scenes", None)
        who = room.host_id if winner == "me" else room.guest_id

        def ends(state, *args, **kwargs):
            state["game_over"] = {"winner": str(who), "reason": "level", "rematch": []}
            return {}
        with mock.patch.object(play.game, "apply", side_effect=ends):
            play.play_action(room, room.host_id, {"type": "x"}, lookups={"info": None})
        return GameRoom.objects.get(pk=room.pk)


class ArcadeSceneTests(ArcadeSetup):
    def setUp(self):
        super().setUp()
        script = "cast rapi as Rapi\nrapi enters\nrapi: Welcome."
        self.intro, self.before, self.after, self.outro = (Scene.objects.create(name=n, script=script) for n in ("Intro", "Before", "After", "Outro"))
        self.scenario.intro_scene, self.scenario.outro_scene = self.intro, self.outro
        self.scenario.save()
        ArcadeEntry.objects.filter(cpu=self.opener).update(scene_before=self.before, scene_after=self.after)

    def start(self):
        self.client.post(reverse("weiss:arcade_start"), {"scenario": self.scenario.pk, "deck": self.deck.pk})
        room = self.room()
        self.url = reverse("weiss:play_action", args=[room.pk])
        return room

    def test_scenes_play_before_the_first_fight_and_hold_everything_up(self):
        room = self.start()
        self.assertEqual([s["title"] for s in room.state["scenes"]], ["Intro", "Before"])
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual(data["scene"]["title"], "Intro")
        self.assertEqual(data["scene"]["cast"]["rapi"]["name"], "Rapi")
        self.assertEqual(data["player_name"], "alice")
        self.assertEqual(self.post(self.url, {"type": "intro_done"}).status_code, 409)  # nothing else until the scenes are done
        # The CPU waits too.
        with mock.patch.object(play.cpu, "next_action") as choose:
            play.cpu_step(GameRoom.objects.get(pk=room.pk), wait=False)
        choose.assert_not_called()
        key = data["scene"]["key"]
        self.post(self.url, {"type": "scene_done", "key": "stale"})  # an old page's message changes nothing
        self.assertEqual(len(GameRoom.objects.get(pk=room.pk).state["scenes"]), 2)
        self.assertEqual(self.post(self.url, {"type": "scene_done", "key": key}).json()["scene"]["title"], "Before")
        data = self.post(self.url, {"type": "scene_done", "key": GameRoom.objects.get(pk=room.pk).state["scenes"][0]["key"]}).json()
        self.assertNotIn("scene", data)
        self.assertTrue(data["intro"])  # on to the CPU's screen

    def test_winning_plays_the_scene_after_and_the_next_fight_has_none(self):
        self.start()
        room = self.end_fight("me")
        self.assertEqual([s["title"] for s in room.state["scenes"]], ["After"])
        self.assertEqual(self.post(self.url, {"type": "arcade_continue"}).status_code, 409)
        self.post(self.url, {"type": "scene_done", "key": room.state["scenes"][0]["key"]})
        self.post(self.url, {"type": "arcade_continue"})
        self.assertNotIn("scenes", self.room().state)  # the filler has no scenes, and the intro was for the start

    def test_clearing_plays_the_closing_scene(self):
        self.start()
        run = self.room().arcade_run
        run.position = 2
        run.save()
        room = self.end_fight("me")
        # The CPU just beaten (the opener, still seated) has its scene after, then the list's closing one.
        self.assertEqual([s["title"] for s in room.state["scenes"]], ["After", "Outro"])

    def test_a_scene_with_mistakes_is_skipped(self):
        Scene.objects.filter(pk=self.intro.pk).update(script="cast x as Nobody")
        self.assertEqual([s["title"] for s in self.start().state["scenes"]], ["Before"])

    def test_staff_choose_the_scenes(self):
        self.client.force_login(self.staff)
        entry = ArcadeEntry.objects.get(cpu=self.filler)
        self.client.post(reverse("weiss:arcade_scenes", args=[self.scenario.pk]), {"intro": "", "outro": self.after.pk, f"before-{entry.pk}": self.before.pk})
        self.scenario.refresh_from_db()
        entry.refresh_from_db()
        self.assertEqual((self.scenario.intro_scene, self.scenario.outro_scene, entry.scene_before, entry.scene_after), (None, self.after, self.before, None))
        self.assertContains(self.client.get(reverse("weiss:cpu_home")), "Before the first fight")


class FightOrderTests(ArcadeSetup):
    """A narrative challenge's set order, branches, and scenes that pick the next fight."""

    def setUp(self):
        super().setUp()
        self.second, self.branch_a, self.branch_b = self.cpu("Neon"), self.cpu("Helm"), self.cpu("Drake")
        ArcadeEntry.objects.filter(cpu=self.filler).update(position=2)
        ArcadeEntry.objects.create(scenario=self.scenario, cpu=self.second, role="filler", position=1)
        ArcadeEntry.objects.create(scenario=self.scenario, cpu=self.branch_a, role="branch", position=1)
        ArcadeEntry.objects.create(scenario=self.scenario, cpu=self.branch_b, role="branch", position=2)

    def test_a_set_order_or_shuffled_and_no_branches(self):
        scenario = ArcadeScenario.objects.prefetch_related("entries").get()
        fixed = [self.opener.pk, self.second.pk, self.filler.pk, self.anchor.pk]
        self.assertEqual(arcade.fight_order(scenario, fixed=True), fixed)
        orders = {tuple(arcade.fight_order(scenario, random.Random(seed))) for seed in range(20)}
        self.assertEqual(len(orders), 2)  # the two fillers either way round
        self.assertTrue(all(self.branch_a.pk not in order for order in orders))
        names = [fighter["cpu"].name for fighter in arcade.lineup(scenario, self.alice)]
        self.assertEqual(names, ["Rapi", "Neon", "Anis", "Last"])  # a branch shows once it's been met

    def test_the_script_lines(self):
        script = "cast rapi as Rapi\ncast helm as Helm\nfight helm\nchoice Who?\n- Her (fight helm)\n- Nobody"
        scene, errors = scenes.compile_scene(script)
        self.assertEqual(errors, [])
        self.assertEqual(scene["steps"][0], {"line": 3, "do": "fight", "who": "helm"})
        self.assertEqual(scene["steps"][1]["options"][0]["fight"], "helm")
        errors = dict(scenes.compile_scene("cast rapi as Rapi\nfight drake\nchoice x\n- y (fight drake)")[1])
        self.assertIn("Only a CPU in the cast", errors[2])
        self.assertIn("Only a CPU in the cast", errors[4])

    def test_what_the_page_says_was_picked_is_checked(self):
        compiled = scenes.compile_scene("cast helm as Helm\ncast drake as Drake\nfight helm\nchoice Who?\n- Drake (fight drake)\n- Nobody")[0]
        payload = scenes.scene_payload(compiled)
        self.assertEqual(scenes.chosen_fight(payload, [[0, None], [1, 0]]), self.branch_b.pk)  # the last one counts
        self.assertEqual(scenes.chosen_fight(payload, [[0, None], [1, 1]]), self.branch_a.pk)  # "Nobody" fights nobody
        self.assertIsNone(scenes.chosen_fight(payload, [[1, 9], [5, None], "x"]))

    def start(self, script, where="after"):
        scene = Scene.objects.create(name="Fork", script=script)
        ArcadeEntry.objects.filter(cpu=self.opener).update(**{f"scene_{where}": scene})
        self.client.post(reverse("weiss:arcade_start"), {"scenario": self.scenario.pk, "deck": self.deck.pk})
        room = self.room()
        self.url = reverse("weiss:play_action", args=[room.pk])
        return room

    def finish_scene(self, fights):
        room = self.room()
        return self.post(self.url, {"type": "scene_done", "key": room.state["scenes"][0]["key"], "fights": fights}).json()

    def test_a_scene_after_a_win_picks_the_next_fight(self):
        self.start("cast helm as Helm\nchoice Where to?\n- The tower (fight helm)\n- Onwards")
        self.end_fight("me")
        self.finish_scene([[0, 0]])
        run = self.room().arcade_run
        self.assertEqual(run.order[1], self.branch_a.pk)
        self.assertEqual(len(run.order), 4)  # in place of whoever was next, not as well
        self.post(self.url, {"type": "arcade_continue"})
        self.assertEqual(self.room().cpu_profile, self.branch_a)

    def test_picking_one_due_later_swaps_them(self):
        self.start("cast last as Last\nfight last")
        run = self.room().arcade_run
        next_up = run.order[1]
        self.end_fight("me")
        self.finish_scene([[0, None]])
        run.refresh_from_db()
        self.assertEqual((run.order[1], run.order[3]), (self.anchor.pk, next_up))

    def test_a_scene_before_a_fight_changes_who_it_is_against(self):
        self.start("cast helm as Helm\nfight helm", where="before")
        self.assertEqual(self.room().cpu_profile, self.opener)
        data = self.finish_scene([[0, None]])
        room = self.room()
        self.assertEqual(room.cpu_profile, self.branch_a)  # straight in the seat
        self.assertEqual(room.arcade_run.order[0], self.branch_a.pk)
        self.assertEqual(data["cpu"]["name"], "Helm")

    def test_only_a_cpu_in_the_list_can_be_picked(self):
        outsider = self.cpu("Outsider")
        self.start(f"cast them as #{outsider.pk}\nfight them")
        self.end_fight("me")
        before = list(self.room().arcade_run.order)
        self.finish_scene([[0, None]])
        self.assertEqual(self.room().arcade_run.order, before)

    def test_a_narrative_challenge_fights_in_the_set_order(self):
        self.client.force_login(self.staff)
        narrative = NarrativeChallenge.objects.create(name="Story", scenario=self.scenario, sets=[7])
        make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "narrative", "narrative": narrative.pk})
        run = challenge.current(self.staff)
        challenge.open_packs(run, 7, 2)
        challenge.save_deck(run, {pk: 1 for pk in run.pool})
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        run.refresh_from_db()
        self.assertEqual(run.arcade_run.order, [self.opener.pk, self.second.pk, self.filler.pk, self.anchor.pk])

    def test_staff_set_the_order_and_add_branches(self):
        self.client.force_login(self.staff)
        neon = ArcadeEntry.objects.get(cpu=self.second)
        anis = ArcadeEntry.objects.get(cpu=self.filler)
        self.client.post(reverse("weiss:arcade_order", args=[self.scenario.pk]), {f"position-{neon.pk}": 5, f"position-{anis.pk}": 1})
        scenario = ArcadeScenario.objects.prefetch_related("entries").get()
        self.assertEqual(arcade.fight_order(scenario, fixed=True)[1:3], [self.filler.pk, self.second.pk])
        self.client.post(reverse("weiss:arcade_entry_add", args=[self.scenario.pk]), {"cpu": self.cpu("Third branch").pk, "role": "branch"})
        self.assertEqual(ArcadeEntry.objects.filter(role="branch").count(), 3)  # as many branches as a story needs
        self.assertContains(self.client.get(reverse("weiss:cpu_home")), "Filler order in narrative challenges")


class HeaderTests(ArcadeSetup):
    def test_the_profile_is_the_players_avatar_at_the_far_right(self):
        page = self.client.get(reverse("weiss:arcade")).content.decode()
        self.assertIn('class="nav-profile', page)
        self.assertIn(">Profile</a>", page)  # no picture chosen: the word
        self.assertGreater(page.index("nav-profile"), page.index("Log out"))  # after everything else
        from .models import PlayerProfile
        PlayerProfile.objects.create(user=self.alice, avatar_card=self.card)
        page = self.client.get(reverse("weiss:arcade")).content.decode()
        self.assertIn("avatar-nav", page)
        self.assertIn(f"/cards/{self.card.pk}/image/", page)

    def test_the_infinite_challenge_button(self):
        self.client.force_login(self.alice)
        self.assertNotIn("nav-infinite", self.client.get(reverse("weiss:arcade")).content.decode())  # staff only, for now
        self.client.force_login(self.staff)
        page = self.client.get(reverse("weiss:arcade")).content.decode()
        self.assertIn("∞ Infinite challenge", page)
        self.assertRedirects(self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "infinite"}), reverse("weiss:arcade_challenge"))
        self.assertEqual(challenge.current(self.staff).kind, "infinite")
        page = self.client.get(reverse("weiss:play_rooms")).content.decode()
        self.assertIn("∞ Your challenge", page)  # one's under way: the button goes to it


class InfiniteChallengeTests(ArcadeSetup):
    def setUp(self):
        super().setUp()
        make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4)
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "infinite"})
        self.run = challenge.current(self.staff)
        challenge.open_packs(self.run, 7, 2)
        challenge.save_deck(self.run, {pk: 1 for pk in self.run.pool})

    def test_starting_one(self):
        self.assertEqual((self.run.kind, self.run.name, self.run.scenario, self.run.sets), ("infinite", "Infinite challenge", None, []))
        self.assertEqual(self.run.packs + 2, challenge.START_PACKS)
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Infinite challenge")

    def fight(self, node=0):
        return self.client.post(reverse("weiss:arcade_challenge_fight"), {"node": node})

    def path(self):
        self.run.refresh_from_db()
        return challenge.path_of(self.run)

    def win_and_leave(self):
        room = self.end_fight("me")
        self.post(reverse("weiss:play_action", args=[room.pk]), {"type": "challenge_leave"})

    def test_it_fights_every_cpu_for_as_long_as_it_wins(self):
        self.fight()
        room = self.room()
        run = room.arcade_run
        self.assertEqual((run.scenario, run.scenario_name, run.order), (None, "Infinite challenge", [self.path()["floors"][0][0]]))
        self.assertIn(room.cpu_profile, [self.opener, self.filler, self.anchor])
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual((data["arcade"]["fight"], data["arcade"]["total"], data["arcade"]["defeated"]), (1, None, []))
        packs = self.run.packs
        for fight in range(1, 5):
            self.win_and_leave()
            run.refresh_from_db()
            self.assertEqual((run.position, len(run.order), run.status), (fight, fight, ArcadeRun.Status.ACTIVE))
            path = self.path()
            node = challenge.choices(path, fight)[-1]
            self.fight(node)
            run.refresh_from_db()
            self.assertEqual(run.order[-1], path["floors"][fight][node])  # the one chosen
            self.assertEqual(self.room().cpu_profile_id, path["floors"][fight][node])
        self.run.refresh_from_db()
        self.assertEqual(self.run.packs, packs + 4 * challenge.INFINITE_WIN_PACKS)  # a pack each win
        self.assertEqual(len(self.run.rewards), 4)  # and a prize to claim
        self.assertTrue(all(r["buff"] in challenge.INFINITE_PRIZES for r in self.run.rewards))
        self.assertEqual(self.run.status, "active")
        self.assertEqual(challenge.defeated(self.run), run.order[:4])

    def test_the_path_is_laid_out_ahead(self):
        path = self.path()
        self.assertEqual(len(path["floors"]), 1 + challenge.PATH_AHEAD)
        for floor in path["floors"]:
            self.assertIn(len(floor), (2, 3))
            self.assertEqual(len(set(floor)), len(floor))  # all different
        self.assertEqual(challenge.choices(path, 0), list(range(len(path["floors"][0]))))  # any to start
        self.fight(1)
        self.win_and_leave()
        path = self.path()
        self.assertEqual(len(path["floors"]), 2 + challenge.PATH_AHEAD)  # one more floor, as it goes up
        self.assertEqual(challenge.choices(path, 1), challenge.links(len(path["floors"][0]), len(path["floors"][1]))[1])

    def test_each_cpu_leads_to_two_or_three(self):
        for count in (1, 2, 3):
            for ahead in (2, 3):
                led = challenge.links(count, ahead)
                self.assertTrue(all(len(nodes) >= 2 for nodes in led))
                self.assertEqual({j for nodes in led for j in nodes}, set(range(ahead)))  # every one can be got to
        self.assertEqual(challenge.links(2, 3), [[0, 1], [1, 2]])
        self.assertEqual(challenge.links(3, 3), [[0, 1], [0, 1, 2], [1, 2]])

    def test_only_a_cpu_the_path_leads_to_can_be_chosen(self):
        self.run.path = {"floors": [[self.opener.pk, self.filler.pk], [self.opener.pk, self.filler.pk, self.anchor.pk]], "picks": [0]}
        self.run.save()
        self.fight(0)
        self.win_and_leave()
        response = self.fight(2)  # the first on the left leads to the first two on the next floor, not the third
        self.assertEqual(response.status_code, 302)
        self.assertFalse(GameRoom.objects.filter(host=self.staff).exists())
        self.fight(1)
        self.assertEqual(self.room().cpu_profile, self.filler)

    def test_a_choice_stands_until_the_fight_is_won(self):
        self.fight(1)
        chosen = self.room().cpu_profile_id
        self.post(reverse("weiss:play_action", args=[self.room().pk]), {"type": "challenge_leave"})
        self.fight(0)  # changing their mind: no
        self.assertEqual(self.room().cpu_profile_id, chosen)

    def test_a_cpu_gone_from_the_path_is_replaced(self):
        path = self.path()
        gone = path["floors"][1][0]
        type(self.opener).objects.filter(pk=gone).update(finalized=False)
        path = self.path()
        self.assertTrue(all(gone not in floor for floor in path["floors"]))
        self.assertTrue(all(floor for floor in path["floors"]))

    def test_the_page_shows_the_path_and_who_is_beaten(self):
        page = self.client.get(reverse("weiss:arcade_challenge")).content.decode()
        self.assertIn("The path", page)
        self.assertIn("<strong>0</strong> defeated", page)
        self.assertEqual(page.count('name="node"'), len(self.path()["floors"][0]))  # one to fight on each node of the first floor
        self.fight(0)
        beaten = self.room().cpu_profile
        self.win_and_leave()
        page = self.client.get(reverse("weiss:arcade_challenge")).content.decode()
        self.assertIn("<strong>1</strong> defeated", page)
        self.assertIn(f'aria-label="{beaten.name}"', page)
        self.fight(challenge.choices(self.path(), 1)[0])
        data = self.client.get(reverse("weiss:play_state", args=[self.room().pk])).json()
        self.assertEqual([cpu["name"] for cpu in data["arcade"]["defeated"]], [beaten.name])
        for fight in (2, 3):  # further up, the floors behind go on being shown
            self.win_and_leave()
            self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), f"<strong>{fight}</strong> defeated")
            self.fight(challenge.choices(self.path(), fight)[0])

    def test_a_win_goes_back_to_the_path(self):
        self.fight()
        room = self.end_fight("me")
        response = self.post(reverse("weiss:play_action", args=[room.pk]), {"type": "arcade_continue"})
        self.assertEqual(response.status_code, 400)  # the next one's chosen on the path

    def test_resetting_lays_a_new_path(self):
        self.fight()
        self.win_and_leave()
        self.run.refresh_from_db()
        challenge.reset(self.run)
        self.run.refresh_from_db()
        self.assertEqual(self.run.path, {})

    def test_the_victory_screen_draws_the_prize_won(self):
        self.fight()
        room = self.end_fight("me")
        self.run.refresh_from_db()
        won = self.run.rewards[-1]["buff"]
        prize = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()["prize"]
        self.assertEqual([item["name"] for item in prize["reel"]], ["Climax pack", "Color pack", "Lucky pack"])
        self.assertEqual((prize["reel"][prize["won"]]["buff"], prize["packs"]), (won, 1))  # what it lands on is what's given
        self.post(reverse("weiss:play_action", args=[room.pk]), {"type": "challenge_leave"})
        self.fight(challenge.choices(self.path(), 1)[0])
        self.assertNotIn("prize", self.client.get(reverse("weiss:play_state", args=[self.room().pk])).json())  # gone with the next fight

    def test_a_loss_ends_it_and_the_deck_can_be_kept(self):
        self.fight()
        self.end_fight("cpu")
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, "lost")
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Keep your deck?")

    def test_the_cpus_get_harder(self):
        self.fight()
        run = self.room().arcade_run
        models = []
        for floor in range(9):  # by how far up the path it is, events and all
            ChallengeRun.objects.filter(pk=self.run.pk).update(path={**self.path(), "done": floor})
            models.append(challenge.infinite_style(run, self.opener))
        self.assertEqual([m for m, _ in models[:3]], ["easy", "easy", "standard"])
        self.assertTrue(all(m in ("focused", "strategic") for m, _ in models[3:6]))
        self.assertTrue(all(m == "hard" for m, _ in models[6:]))
        self.assertTrue(all(1 <= a <= 5 for _, a in models[6:]))
        self.assertEqual(models[0][1], self.opener.aggression)  # before hard, the CPU's own
        self.assertEqual(challenge.infinite_style(run, self.opener), models[-1])  # settled for the fight

    def test_the_cpu_plays_by_the_challenges_model_not_its_own(self):
        type(self.opener).objects.update(model="hard")
        self.fight()
        room = self.room()
        room.state.pop("cpu_intro", None)
        room.save()
        with mock.patch.object(play.cpu, "next_action", return_value=None) as chooser:
            play.cpu_step(GameRoom.objects.get(pk=room.pk), wait=False)
        self.assertEqual(chooser.call_args.kwargs["model"], "easy")

    def test_the_cpus_own_lines_are_kept(self):
        type(self.opener).objects.update(intro_text="Hello!", player_win_text="Ugh.", player_lose_text="Ha!")
        self.fight()
        room = self.room()
        self.assertTrue(room.state["cpu_intro"])  # its usual screen before the fight
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual((data["cpu"]["intro"], data["cpu"]["win"], data["cpu"]["lose"]), ("Hello!", "Ugh.", "Ha!"))

    def test_no_scenes(self):
        scene = Scene.objects.create(name="Hi", script="cast a as Rapi\na: Hi.")
        ArcadeEntry.objects.update(scene_before=scene, scene_after=scene)
        self.fight()
        self.assertNotIn("scenes", self.room().state)
        room = self.end_fight("me")
        self.assertNotIn("scenes", room.state)


class ChallengeTests(ArcadeSetup):
    def setUp(self):
        super().setUp()
        self.cards = make_set(expansion_id=7, name="Vol.7", C=12, U=6, CC=2, R=4, RR=2, SR=4)
        make_set(expansion_id=8, name="Vol.8", C=8, R=2)
        self.client.force_login(self.staff)  # staff only, while it's being tried out

    def start(self, **data):
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "free", "scenario": self.scenario.pk, **data})
        return challenge.current(self.staff)

    def open(self, count, set_id=7):
        return self.client.post(reverse("weiss:arcade_challenge_open"), {"set": set_id, "count": count})

    def build(self, run):
        """A deck of everything pulled, up to 50."""
        copies, room = {}, 50
        for pk, n in run.pool.items():
            copies[pk] = min(n, room)
            room -= copies[pk]
        self.client.post(reverse("weiss:arcade_challenge_deck"), {"deck": json.dumps(copies)})
        return copies

    def test_staff_only_for_now(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("weiss:arcade_challenge")).status_code, 403)
        self.assertNotContains(self.client.get(reverse("weiss:arcade")), "Challenge</a>")
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("weiss:arcade")), "Challenge</a>")

    def test_starting_gives_its_packs_and_a_deck_kept_out_of_the_lists(self):
        run = self.start()
        self.assertEqual((run.kind, run.packs, run.name, run.scenario), ("free", challenge.START_PACKS, "Ark", self.scenario))
        self.assertTrue(run.deck.challenge)
        self.assertNotIn(run.deck, CardList.objects.players(self.staff))
        self.assertNotIn(run.deck, self.client.get(reverse("weiss:lists")).context["lists"])
        self.assertEqual(self.client.get(reverse("weiss:list", args=[run.deck.pk])).status_code, 404)  # not for the list editor
        self.start()  # one at a time
        self.assertEqual(ChallengeRun.objects.count(), 1)

    def test_opening_packs_fills_the_pool(self):
        run = self.start()
        self.assertRedirects(self.open(4), reverse("weiss:arcade_challenge_opened"))
        run.refresh_from_db()
        left = challenge.START_PACKS - 4
        self.assertEqual((run.packs, run.opened, sum(run.pool.values())), (left, 4, 32))
        self.assertEqual(len(run.last_opening["packs"]), 4)
        page = self.client.get(reverse("weiss:arcade_challenge_opened"))
        self.assertContains(page, "Build your deck")
        self.assertContains(page, 'data-pack="3"')
        self.open(left + 1)  # more than are left
        run.refresh_from_db()
        self.assertEqual(run.packs, left)

    def test_a_narrative_challenge_only_opens_its_own_sets(self):
        narrative = NarrativeChallenge.objects.create(name="Story", scenario=self.scenario, sets=[8])
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "narrative", "narrative": narrative.pk})
        run = challenge.current(self.staff)
        self.assertEqual((run.kind, run.name, run.sets), ("narrative", "Story", [8]))
        self.assertEqual([s["id"] for s in challenge.allowed_sets(run)], [8])
        self.assertEqual(run.packs, challenge.NARRATIVE_START_PACKS)
        self.open(1, set_id=7)
        run.refresh_from_db()
        self.assertEqual(run.packs, challenge.NARRATIVE_START_PACKS)
        self.open(1, set_id=8)
        run.refresh_from_db()
        self.assertEqual(run.packs, challenge.NARRATIVE_START_PACKS - 1)
        self.client.post(reverse("weiss:arcade_challenge_reset"))
        run.refresh_from_db()
        self.assertEqual(run.packs, challenge.NARRATIVE_START_PACKS)  # and again after a reset
        narrative.sets = [7]
        narrative.save()  # a challenge under way keeps its sets
        run.refresh_from_db()
        self.assertEqual(run.sets, [8])

    def test_the_deck_only_takes_what_was_pulled(self):
        run = self.start()
        self.open(10)
        run.refresh_from_db()
        copies = self.build(run)
        self.assertEqual(sum(run.deck.entries.values_list("quantity", flat=True)), min(80, 50))
        pk, n = next(iter(run.pool.items()))
        self.client.post(reverse("weiss:arcade_challenge_deck"), {"deck": json.dumps({pk: n + 1})})
        self.assertEqual(sum(run.deck.entries.values_list("quantity", flat=True)), sum(copies.values()))  # unchanged
        unpulled = next(c for c in self.cards if str(c.pk) not in run.pool) if len(run.pool) < len(self.cards) else None
        if unpulled:
            self.client.post(reverse("weiss:arcade_challenge_deck"), {"deck": json.dumps({unpulled.pk: 1})})
            self.assertFalse(run.deck.entries.filter(card=unpulled).exists())
        page = self.client.get(reverse("weiss:arcade_challenge_deck"))
        self.assertContains(page, "data-pulled=")

    def ready_to_fight(self):
        run = self.start()
        self.open(10)
        run.refresh_from_db()
        self.build(run)
        return run

    def test_fighting_wins_bring_packs(self):
        run = self.ready_to_fight()
        response = self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        self.assertRedirects(response, reverse("weiss:play_room", args=[room.pk]))
        self.assertEqual((room.host_deck, room.cpu_profile), (run.deck, self.opener))
        self.assertRedirects(self.client.post(reverse("weiss:arcade_challenge_fight")), reverse("weiss:play_room", args=[room.pk]))  # the same room
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        left = challenge.START_PACKS - 10  # ready_to_fight opened 10
        self.assertEqual(data["arcade"]["challenge"], {"packs": left, "won": "3 packs", "lives": 0, "going": True, "rewards": 0})
        self.end_fight("me")
        run.refresh_from_db()
        self.assertEqual((run.packs, run.status, run.rewards), (left + challenge.WIN_PACKS, "active", []))
        url = reverse("weiss:play_action", args=[room.pk])
        self.assertEqual(self.post(url, {"type": "arcade_edit_deck"}).status_code, 400)  # packs and the deck are on the challenge's page
        self.assertEqual(self.post(url, {"type": "challenge_leave"}).json()["redirect"], reverse("weiss:arcade_challenge"))
        self.assertFalse(GameRoom.objects.exists())
        # Back from changing the deck: the next fight is the next CPU.
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        self.assertEqual(self.room().cpu_profile_id, run.arcade_run.order[1])

    def test_a_narrative_win_brings_two_packs_and_a_color_pack(self):
        narrative = NarrativeChallenge.objects.create(name="Story", scenario=self.scenario, sets=[7])
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "narrative", "narrative": narrative.pk})
        run = challenge.current(self.staff)
        self.open(run.packs)
        run.refresh_from_db()
        self.build(run)
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual(data["arcade"]["challenge"]["won"], "2 packs and a color pack")
        self.end_fight("me")
        run.refresh_from_db()
        self.assertEqual(run.packs, challenge.NARRATIVE_WIN_PACKS)
        self.assertEqual([(r["buff"], r["source"]) for r in run.rewards], [("color_pack", "Victory")])
        page = self.client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, "Rewards to claim")
        self.assertContains(page, "Color pack")

    def test_a_loss_ends_it(self):
        run = self.ready_to_fight()
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.end_fight("cpu")
        run.refresh_from_db()
        self.assertEqual(run.status, "lost")
        self.assertEqual(run.arcade_run.status, ArcadeRun.Status.ABANDONED)
        self.assertEqual(self.post(reverse("weiss:play_action", args=[room.pk]), {"type": "arcade_retry"}).status_code, 400)
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Keep your deck?")

    def test_clearing_it(self):
        run = self.ready_to_fight()
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        run.refresh_from_db()
        run.arcade_run.position = 2
        run.arcade_run.save()
        self.end_fight("me")
        run.refresh_from_db()
        self.assertEqual(run.status, "won")

    def test_stopping_mid_fight_picks_up_at_that_fight(self):
        run = self.ready_to_fight()
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        self.end_fight("me")
        self.post(reverse("weiss:play_action", args=[self.room().pk]), {"type": "arcade_continue"})
        room = self.room()
        self.assertRedirects(self.client.post(reverse("weiss:arcade_quit", args=[room.pk])), reverse("weiss:arcade_challenge"))
        run.refresh_from_db()
        self.assertEqual((run.status, run.arcade_run.status, run.arcade_run.position), ("active", ArcadeRun.Status.ACTIVE, 1))
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        self.assertEqual(self.room().cpu_profile_id, run.arcade_run.order[1])

    def test_reset_starts_again_from_nothing(self):
        run = self.ready_to_fight()
        old_deck = run.deck.pk
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        self.client.post(reverse("weiss:arcade_challenge_reset"))
        run.refresh_from_db()
        self.assertFalse(CardList.objects.filter(pk=old_deck).exists())
        self.assertEqual((run.packs, run.pool, run.arcade_run, run.status), (challenge.START_PACKS, {}, None, "active"))
        self.assertTrue(run.deck.challenge)
        self.assertFalse(GameRoom.objects.exists())

    def test_keeping_the_deck(self):
        run = self.ready_to_fight()
        self.client.post(reverse("weiss:arcade_challenge_end"))
        self.assertRedirects(self.client.post(reverse("weiss:arcade_challenge_close"), {"keep": "on", "name": "Drafted"}), reverse("weiss:lists"))
        deck = CardList.objects.get(pk=run.deck.pk)
        self.assertEqual((deck.name, deck.challenge), ("Drafted", False))
        self.assertIn(deck, CardList.objects.players(self.staff))
        self.assertIsNone(challenge.current(self.staff))

    def test_discarding_the_deck(self):
        run = self.ready_to_fight()
        self.client.post(reverse("weiss:arcade_challenge_close"))  # still going: it has to be ended first
        self.assertIsNotNone(challenge.current(self.staff))
        self.client.post(reverse("weiss:arcade_challenge_end"))
        self.client.post(reverse("weiss:arcade_challenge_close"))
        self.assertFalse(CardList.objects.filter(pk=run.deck_id).exists())
        self.assertIsNone(challenge.current(self.staff))
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Free challenge")

    def test_staff_set_up_narrative_challenges(self):
        self.client.post(reverse("weiss:cpu_narrative_create"), {"name": "Story", "scenario": self.scenario.pk, "sets": ["7", "8"], "description": "Once upon a time"})
        narrative = NarrativeChallenge.objects.get()
        self.assertEqual((narrative.sets, narrative.description, narrative.scenario), ([7, 8], "Once upon a time", self.scenario))
        self.client.post(reverse("weiss:cpu_narrative_create"), {"name": "No sets", "scenario": self.scenario.pk})
        self.assertEqual(NarrativeChallenge.objects.count(), 1)
        self.client.post(reverse("weiss:cpu_narrative_update", args=[narrative.pk]), {"name": "Story 2", "scenario": self.scenario.pk, "sets": ["8"]})
        narrative.refresh_from_db()
        self.assertEqual((narrative.name, narrative.sets), ("Story 2", [8]))
        self.assertContains(self.client.get(reverse("weiss:arcade_challenge")), "Story 2")
        self.client.post(reverse("weiss:cpu_narrative_delete", args=[narrative.pk]))
        self.assertFalse(NarrativeChallenge.objects.exists())

    def test_a_narrative_challenge_leaves_the_cpus_own_lines_to_its_scenes(self):
        type(self.opener).objects.filter(pk=self.opener.pk).update(intro_text="Hello!", player_win_text="Ugh.", player_lose_text="Ha!")
        narrative = NarrativeChallenge.objects.create(name="Story", scenario=self.scenario, sets=[7])
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "narrative", "narrative": narrative.pk})
        run = challenge.current(self.staff)
        self.open(10)
        run.refresh_from_db()
        self.build(run)
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        self.assertNotIn("cpu_intro", room.state)  # straight to the game
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertEqual((data["cpu"]["intro"], data["cpu"]["win"], data["cpu"]["lose"]), ("", "", ""))
        self.assertNotIn("intro", data)
        # A fight not yet begun is still dealt again with the deck as it is now.
        card = next(iter(run.pool))
        challenge.save_deck(run, {card: 1})
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        me = self.room().state["players"][str(self.staff.pk)]
        self.assertEqual(sum(len(zone) for zone in me["zones"].values() if isinstance(zone, list)), 1)

    def test_a_free_challenge_keeps_them(self):
        type(self.opener).objects.filter(pk=self.opener.pk).update(intro_text="Hello!")
        self.ready_to_fight()
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        room = self.room()
        self.assertTrue(room.state["cpu_intro"])
        self.assertEqual(self.client.get(reverse("weiss:play_state", args=[room.pk])).json()["cpu"]["intro"], "Hello!")

    def test_the_arcade_tab_stays_current(self):
        page = self.client.get(reverse("weiss:arcade_challenge"))
        self.assertContains(page, f'<a href="{reverse("weiss:arcade")}" class="current" aria-current="page">Arcade</a>', html=False)
