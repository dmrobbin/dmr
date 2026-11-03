import json
import random
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import arcade, challenge, play
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

    def test_starting_gives_ten_packs_and_a_deck_kept_out_of_the_lists(self):
        run = self.start()
        self.assertEqual((run.kind, run.packs, run.name, run.scenario), ("free", 10, "Ark", self.scenario))
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
        self.assertEqual((run.packs, run.opened, sum(run.pool.values())), (6, 4, 32))
        self.assertEqual(len(run.last_opening["packs"]), 4)
        page = self.client.get(reverse("weiss:arcade_challenge_opened"))
        self.assertContains(page, "Build your deck")
        self.assertContains(page, 'data-pack="3"')
        self.open(7)  # more than are left
        run.refresh_from_db()
        self.assertEqual(run.packs, 6)

    def test_a_narrative_challenge_only_opens_its_own_sets(self):
        narrative = NarrativeChallenge.objects.create(name="Story", scenario=self.scenario, sets=[8])
        self.client.post(reverse("weiss:arcade_challenge_start"), {"kind": "narrative", "narrative": narrative.pk})
        run = challenge.current(self.staff)
        self.assertEqual((run.kind, run.name, run.sets), ("narrative", "Story", [8]))
        self.assertEqual([s["id"] for s in challenge.allowed_sets(run)], [8])
        self.open(1, set_id=7)
        run.refresh_from_db()
        self.assertEqual(run.packs, 10)
        self.open(1, set_id=8)
        run.refresh_from_db()
        self.assertEqual(run.packs, 9)
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
        self.assertEqual(data["arcade"]["challenge"], {"packs": 0, "won": 3, "lives": 0, "going": True, "rewards": 0})
        self.end_fight("me")
        run.refresh_from_db()
        self.assertEqual((run.packs, run.status), (3, "active"))
        url = reverse("weiss:play_action", args=[room.pk])
        self.assertEqual(self.post(url, {"type": "arcade_edit_deck"}).status_code, 400)  # packs and the deck are on the challenge's page
        self.assertEqual(self.post(url, {"type": "challenge_leave"}).json()["redirect"], reverse("weiss:arcade_challenge"))
        self.assertFalse(GameRoom.objects.exists())
        # Back from changing the deck: the next fight is the next CPU.
        self.client.post(reverse("weiss:arcade_challenge_fight"))
        self.assertEqual(self.room().cpu_profile_id, run.arcade_run.order[1])

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
        self.assertEqual((run.packs, run.pool, run.arcade_run, run.status), (10, {}, None, "active"))
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
