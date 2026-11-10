from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from . import play, sleeves
from .models import ArcadeEntry, ArcadeRun, ArcadeScenario, ChallengeRun, CpuProfile, GameRoom, PlayerProfile, Sleeve, SleeveUnlock, cpu_user
from .test_arcade import PNG, Base, player


def sleeve(name="Gold", conditions=(), **fields):
    return Sleeve.objects.create(name=name, key=f"weiss/sleeves/{name.lower()}.png", conditions=list(conditions), **fields)


def won(user, counts=None, bests=None):
    return [s.name for s in sleeves.record(user.pk, counts, bests)]


class BuiltInTests(TestCase):
    def test_three_everyone_has_drawn_by_css(self):
        built_in = Sleeve.objects.exclude(style="")
        self.assertEqual([s.style for s in built_in], ["classic", "midnight", "crimson"])
        self.assertTrue(all(s.free and not s.hidden for s in built_in))
        self.assertEqual(built_in[1].css, "var(--sleeve-midnight)")

    def test_an_uploaded_ones_picture_is_a_stable_link_that_changes_with_it(self):
        gold = sleeve()
        self.assertEqual(gold.css, f'url("{reverse("weiss:sleeve_image", args=[gold.pk])}?v=gold.png") center / cover no-repeat, #1b1b1b')


class UnlockTests(TestCase):
    def setUp(self):
        self.alice = player("alice")

    def test_reaching_the_count_unlocks_it_once(self):
        sleeve(conditions=[{"kind": "cpu_wins", "count": 3}])
        self.assertEqual(won(self.alice, {"cpu_wins": 2}), [])
        self.assertEqual(won(self.alice, {"cpu_wins": 1}), ["Gold"])
        self.assertEqual(won(self.alice, {"cpu_wins": 1}), [])
        self.assertEqual(SleeveUnlock.objects.get().user, self.alice)
        self.assertEqual(PlayerProfile.objects.get(user=self.alice).progress, {"cpu_wins": 4})

    def test_a_best_keeps_the_highest(self):
        sleeve(conditions=[{"kind": "arcade_score", "count": 1000}])
        self.assertEqual(won(self.alice, bests={"arcade_score": 900}), [])
        self.assertEqual(won(self.alice, bests={"arcade_score": 400}), [])
        self.assertEqual(PlayerProfile.objects.get(user=self.alice).progress["arcade_score"], 900)
        self.assertEqual(won(self.alice, bests={"arcade_score": 1000}), ["Gold"])

    def test_all_or_any_of_the_conditions(self):
        both = [{"kind": "wins", "count": 1}, {"kind": "bosses", "count": 1}]
        sleeve("All", both)
        sleeve("Any", both, match="any")
        self.assertEqual(won(self.alice, {"wins": 1}), ["Any"])
        self.assertEqual(won(self.alice, {"bosses": 1}), ["All"])

    def test_one_against_a_target_counts_only_that_one(self):
        bot = CpuProfile.objects.create(name="Bot")
        sleeve(conditions=[{"kind": "cpu_wins", "count": 2, "target": bot.pk}])
        self.assertEqual(won(self.alice, {"cpu_wins": 5, f"cpu_wins:{bot.pk + 1}": 5}), [])
        self.assertEqual(won(self.alice, {f"cpu_wins:{bot.pk}": 2}), ["Gold"])

    def test_a_hidden_one_isnt_unlocked(self):
        sleeve(conditions=[{"kind": "wins", "count": 1}], hidden=True)
        self.assertEqual(won(self.alice, {"wins": 1}), [])

    def test_one_added_later_is_theirs_if_theyve_done_it_since_sleeves_came_in(self):
        won(self.alice, {"wins": 5})
        sleeve(conditions=[{"kind": "wins", "count": 5}])
        self.assertEqual([s.name for s in sleeves.check(self.alice.pk)], ["Gold"])


class GameTests(Base):
    """What a finished game counts, through play.play_action as a real game ends."""

    def setUp(self):
        super().setUp()
        self.bot = self.cpu("Bot")
        self.client.force_login(self.alice)

    def room(self, guest=None, **fields):
        guest = guest or cpu_user()
        fields = {"cpu_name": "Bot", "cpu_profile": self.bot, **fields} if guest.username == "cpu-player" else fields
        room = GameRoom(host=self.alice, guest=guest, host_deck=self.deck, guest_deck=self.deck_for(guest, "Theirs"), status="playing", **fields)
        play.deal(room)
        room.save()
        return room

    def end(self, room, winner, **state):
        room.state.pop("cpu_intro", None)

        def ends(game_state, *args, **kwargs):
            game_state.update(state)
            game_state["game_over"] = {"winner": str(winner.pk), "reason": "level", "rematch": []}
            return {}
        with mock.patch.object(play.game, "apply", side_effect=ends):
            play.play_action(room, room.host_id, {"type": "x"}, lookups={"info": None})
        return GameRoom.objects.get(pk=room.pk)

    def progress(self, user):
        return PlayerProfile.objects.get(user=user).progress

    def test_beating_a_cpu_counts_and_the_victory_screen_hears_what_it_unlocked(self):
        sleeve(conditions=[{"kind": "cpu_wins", "count": 1, "target": self.bot.pk}])
        room = self.end(self.room(), self.alice, flash={"picked": []})
        self.assertEqual(self.progress(self.alice), {"wins": 1, "cpu_wins": 1, f"cpu_wins:{self.bot.pk}": 1, "flash_wins": 1})
        unlocked = play.board_payload(room, self.alice)["unlocked"]
        self.assertEqual([s["name"] for s in unlocked], ["Gold"])

    def test_losing_to_a_cpu_counts_nothing(self):
        room = self.room()
        self.end(room, room.guest)
        self.assertFalse(PlayerProfile.objects.filter(user=self.alice).exclude(progress={}).exists())

    def test_a_game_between_players_counts_for_the_winner(self):
        bob = player("bob")
        self.end(self.room(bob), bob)
        self.assertEqual(self.progress(bob), {"wins": 1})
        self.assertFalse(PlayerProfile.objects.filter(user=self.alice).exclude(progress={}).exists())

    def test_clearing_an_arcade_list(self):
        scenario = ArcadeScenario.objects.create(name="Ark")
        ArcadeEntry.objects.create(scenario=scenario, cpu=self.bot, role="opener")
        ArcadeEntry.objects.create(scenario=scenario, cpu=self.cpu("Last"), role="anchor")
        sleeve(conditions=[{"kind": "arcade_clears", "count": 1, "target": scenario.pk}])
        self.client.post(reverse("weiss:arcade_start"), {"scenario": scenario.pk, "deck": self.deck.pk})
        room = self.end(GameRoom.objects.get(), self.alice)
        self.assertNotIn("arcade_clears", self.progress(self.alice))
        self.client.post(reverse("weiss:play_action", args=[room.pk]), '{"type": "arcade_continue"}', content_type="application/json")
        room = self.end(GameRoom.objects.get(), self.alice)
        progress = self.progress(self.alice)
        self.assertEqual((progress["arcade_clears"], progress[f"arcade_clears:{scenario.pk}"]), (1, 1))
        self.assertEqual(progress.get("arcade_score", 0), ArcadeRun.objects.get().score)  # none for a run that scored nothing
        self.assertTrue(SleeveUnlock.objects.filter(user=self.alice).exists())


class ChallengeCountTests(TestCase):
    """sleeves.game_ended for a challenge's fights, given what play.game_ended hands it."""

    def setUp(self):
        self.alice = player("alice")

    def ended(self, trial, run_fields=None, reason="level", **state):
        room = SimpleNamespace(host_id=self.alice.pk, guest_id=0, vs_cpu=True, cpu_profile_id=None, state=state)
        run = SimpleNamespace(**{"score": 500, "scenario_id": None, "status": ArcadeRun.Status.ACTIVE, **(run_fields or {})})
        sleeves.game_ended(room, {"winner": str(self.alice.pk), "reason": reason}, run, trial)
        return PlayerProfile.objects.get(user=self.alice).progress

    def test_an_infinite_challenges_floor_score_and_boss(self):
        trial = SimpleNamespace(kind=ChallengeRun.Kind.INFINITE, coop_id=None, narrative_id=None)
        progress = self.ended(trial, floor=4, boss=True)
        self.assertEqual((progress["infinite_floors"], progress["infinite_score"], progress["bosses"]), (5, 500, 1))

    def test_a_coop_boss_counts_only_once_its_health_bar_is_empty(self):
        trial = SimpleNamespace(kind=ChallengeRun.Kind.INFINITE, coop_id=1, narrative_id=None)
        progress = self.ended(trial, floor=4, boss=True, shared_boss=True)
        self.assertNotIn("bosses", progress)
        progress = self.ended(trial, reason="boss", floor=4, boss=True, shared_boss=True)
        self.assertEqual((progress["bosses"], progress["coop_floors"]), (1, 5))
        self.assertNotIn("infinite_score", progress)

    def test_clearing_a_narrative_challenge(self):
        trial = SimpleNamespace(kind=ChallengeRun.Kind.NARRATIVE, coop_id=None, narrative_id=7)
        progress = self.ended(trial, {"status": ArcadeRun.Status.CLEARED})
        self.assertEqual((progress["challenge_clears"], progress["challenge_clears:7"]), (1, 1))
        self.assertNotIn("arcade_clears", progress)


class BoardTests(Base):
    def test_each_side_has_its_owners_sleeve_and_a_cpu_its_profiles(self):
        bot = self.cpu("Bot", sleeve=Sleeve.objects.get(style="crimson"))
        PlayerProfile.objects.create(user=self.alice, sleeve=Sleeve.objects.get(style="midnight"))
        room = GameRoom.objects.create(host=self.alice, guest=cpu_user(), cpu_name="Bot", cpu_profile=bot)
        self.assertEqual(sleeves.board_sleeves(room, self.alice.pk), {"me": "var(--sleeve-midnight)", "opponent": "var(--sleeve-crimson)"})

    def test_none_chosen_is_the_classic(self):
        bob = player("bob")
        room = GameRoom.objects.create(host=self.alice, guest=bob)
        self.assertEqual(sleeves.board_sleeves(room, bob.pk), {"me": "var(--sleeve-classic)", "opponent": "var(--sleeve-classic)"})


class ProfileTests(TestCase):
    def setUp(self):
        self.alice = player("alice")
        self.client.force_login(self.alice)
        self.gold = sleeve(conditions=[{"kind": "wins", "count": 4}])

    def choose(self, chosen):
        return self.client.post(reverse("weiss:sleeve_choose"), {"sleeve": chosen.pk})

    def test_the_profile_shows_progress_towards_a_locked_one(self):
        won(self.alice, {"wins": 1})
        item = next(i for i in self.client.get(reverse("weiss:profile")).context["shelf"] if i["sleeve"] == self.gold)
        self.assertFalse(item["owned"])
        self.assertEqual(item["conditions"], [{"text": "Win 4 games", "need": 4, "have": 1, "met": False, "percent": 25}])

    def test_choosing_one_they_have_and_not_one_they_dont(self):
        self.choose(self.gold)
        self.assertIsNone(PlayerProfile.objects.get(user=self.alice).sleeve)
        self.choose(Sleeve.objects.get(style="crimson"))
        self.assertEqual(PlayerProfile.objects.get(user=self.alice).sleeve.style, "crimson")
        won(self.alice, {"wins": 4})
        self.choose(self.gold)
        self.assertEqual(PlayerProfile.objects.get(user=self.alice).sleeve, self.gold)

    def test_a_hidden_one_shows_only_to_those_who_have_it(self):
        Sleeve.objects.filter(pk=self.gold.pk).update(hidden=True)
        shelf = lambda: [i["sleeve"] for i in self.client.get(reverse("weiss:profile")).context["shelf"]]
        self.assertNotIn(self.gold, shelf())
        SleeveUnlock.objects.create(user=self.alice, sleeve=self.gold)
        self.assertIn(self.gold, shelf())

    def test_new_ones_have_a_banner_until_seen_on_the_profile(self):
        SleeveUnlock.objects.create(user=self.alice, sleeve=self.gold)
        self.assertContains(self.client.get(reverse("weiss:lists")), "New card sleeve unlocked")
        self.client.get(reverse("weiss:profile"))
        self.assertNotContains(self.client.get(reverse("weiss:lists")), "New card sleeve unlocked")


@override_settings(AWS_S3_BUCKET="bucket")
class StaffTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.alice = player("alice")
        self.client.force_login(self.staff)
        self.bot = CpuProfile.objects.create(name="Bot")

    def make(self, image=PNG, **fields):
        form = {"name": "Gold", "match": "all", "kind": ["cpu_wins", "wins"], "target": [str(self.bot.pk), ""], "count": ["3", "10"], **fields}
        if image is not None:
            form["image"] = SimpleUploadedFile("crop.png", image, content_type="image/png")
        with mock.patch("weiss.sleeve_views.s3.upload") as upload:
            response = self.client.post(reverse("weiss:sleeve_create"), form)
        return response, upload

    def test_making_one_with_its_picture_and_conditions(self):
        response, upload = self.make()
        made = Sleeve.objects.get(name="Gold")
        self.assertRedirects(response, reverse("weiss:sleeve_edit", args=[made.pk]), fetch_redirect_response=False)
        self.assertEqual(made.key, upload.call_args.args[0])
        self.assertTrue(made.key.endswith(".png"))
        self.assertEqual(made.conditions, [{"kind": "cpu_wins", "count": 3, "target": self.bot.pk}, {"kind": "wins", "count": 10}])
        self.assertContains(self.client.get(reverse("weiss:cpu_home") + "?tab=sleeves"), "Win 3 games against Bot")

    def test_it_needs_a_picture_and_good_conditions(self):
        for image, fields in ((None, {}), (b"<svg>", {}), (PNG, {"count": ["0", "1"]}), (PNG, {"kind": ["nope", "wins"]}),
                              (PNG, {"target": ["999999", ""]}), (PNG, {"target": [""]})):
            response, upload = self.make(image, **fields)
            self.assertEqual(response.status_code, 400, fields)
        self.assertFalse(Sleeve.objects.filter(name="Gold").exists())

    def test_giving_one_and_taking_it_back(self):
        _, _ = self.make()
        gold = Sleeve.objects.get(name="Gold")
        self.client.post(reverse("weiss:sleeve_award", args=[gold.pk]), {"username": "ALICE"})
        unlock = SleeveUnlock.objects.get(user=self.alice)
        self.assertEqual(unlock.awarded_by, self.staff)
        PlayerProfile.objects.create(user=self.alice, sleeve=gold)
        self.client.post(reverse("weiss:sleeve_revoke", args=[gold.pk]), {"user": self.alice.pk})
        self.assertFalse(SleeveUnlock.objects.exists())
        self.assertIsNone(PlayerProfile.objects.get(user=self.alice).sleeve)

    def test_hiding_and_deleting(self):
        self.make()
        gold = Sleeve.objects.get(name="Gold")
        with mock.patch("weiss.sleeve_views.s3.upload"):
            self.client.post(reverse("weiss:sleeve_edit", args=[gold.pk]), {"name": "Gold", "match": "any", "hidden": "on"})
        gold.refresh_from_db()
        self.assertEqual((gold.hidden, gold.match, gold.conditions), (True, "any", []))
        with mock.patch("weiss.cpu_views.s3.delete") as delete:
            self.client.post(reverse("weiss:sleeve_delete", args=[gold.pk]))
        delete.assert_called_once_with(gold.key)
        self.assertFalse(Sleeve.objects.filter(pk=gold.pk).exists())

    def test_built_in_ones_stay(self):
        classic = Sleeve.objects.get(style="classic")
        self.client.post(reverse("weiss:sleeve_delete", args=[classic.pk]))
        self.assertTrue(Sleeve.objects.filter(pk=classic.pk).exists())

    def test_a_cpus_sleeve_is_set_on_its_profile(self):
        crimson = Sleeve.objects.get(style="crimson")
        self.client.post(reverse("weiss:cpu_profile_update", args=[self.bot.pk]), {"name": "Bot", "model": "standard", "aggression": 1, "sleeve": crimson.pk})
        self.bot.refresh_from_db()
        self.assertEqual(self.bot.sleeve, crimson)

    def test_players_cant(self):
        self.client.force_login(self.alice)
        response, upload = self.make()
        self.assertEqual(response.status_code, 403)
        upload.assert_not_called()
        self.assertEqual(self.client.get(reverse("weiss:cpu_home") + "?tab=sleeves").status_code, 403)
