import json
import random
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.access import WEISS_GROUP

from . import arcade, play
from .models import ArcadeClear, ArcadeEntry, ArcadeRun, ArcadeScenario, Card, CardList, CardListEntry, CpuImage, CpuProfile, GameRecord, GameRoom

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32


def player(name):
    user = User.objects.create_user(name, password="x")
    Group.objects.get_or_create(name=WEISS_GROUP)[0].user_set.add(user)
    return user


class Base(TestCase):
    def setUp(self):
        self.card = Card.objects.create(serial_number="T/1", name="Rapi", expansion="E", expansion_id=1, card_type="Character", level=0)
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.alice = player("alice")
        self.deck = self.deck_for(self.alice, "Mine")

    def deck_for(self, user, name, **fields):
        deck = CardList.objects.create(user=user, name=name, **fields)
        CardListEntry.objects.create(card_list=deck, card=self.card, quantity=4)
        return deck

    def cpu(self, name, **fields):
        return CpuProfile.objects.create(name=name, finalized=True, deck=self.deck_for(self.staff, f"{name} deck", reserved_for_cpu=True), **fields)

    def post(self, url, action):
        return self.client.post(url, json.dumps(action), content_type="application/json")


class CpuImageTests(Base):
    def setUp(self):
        super().setUp()
        self.profile = self.cpu("Bot")
        self.url = reverse("weiss:cpu_image_upload", args=[self.profile.pk])
        self.client.force_login(self.staff)

    def upload(self, content=PNG, name="a.png"):
        return self.client.post(self.url, {"image": SimpleUploadedFile(name, content, content_type="image/png")})

    @override_settings(AWS_S3_BUCKET="bucket")
    def test_staff_upload_goes_to_s3_with_the_type_its_contents_show(self):
        with mock.patch("weiss.cpu_views.s3.upload") as upload:
            self.upload(b"\xff\xd8\xff" + b"\0" * 32, "sneaky.png")
        self.profile.refresh_from_db()
        key = upload.call_args.args[0]
        self.assertEqual(self.profile.image.key, key)
        self.assertTrue(key.endswith(".jpg"))
        self.assertNotIn("sneaky", key)
        self.assertEqual(upload.call_args.args[2], "image/jpeg")

    def test_only_staff_can_ever_upload(self):
        self.client.force_login(self.alice)
        with mock.patch("weiss.cpu_views.s3.upload") as upload:
            self.assertEqual(self.upload().status_code, 403)
        upload.assert_not_called()
        self.client.logout()
        with mock.patch("weiss.cpu_views.s3.upload") as upload:
            self.assertEqual(self.upload().status_code, 302)
        upload.assert_not_called()

    @override_settings(AWS_S3_BUCKET="bucket")
    def test_what_isnt_an_image_is_refused(self):
        for content in (b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", b"<html><script>", b""):
            with mock.patch("weiss.cpu_views.s3.upload") as upload:
                self.upload(content)
            upload.assert_not_called()
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.image)

    @override_settings(AWS_S3_BUCKET="bucket")
    def test_too_big_is_refused(self):
        with mock.patch("weiss.cpu_views.s3.upload") as upload:
            self.upload(PNG + b"\0" * (5 * 1024 * 1024))
        upload.assert_not_called()

    @override_settings(AWS_S3_BUCKET="bucket")
    def test_a_failed_upload_keeps_the_old_one(self):
        self.profile.image = CpuImage.objects.create(key="old")
        self.profile.save()
        from botocore.exceptions import BotoCoreError
        with mock.patch("weiss.cpu_views.s3.upload", side_effect=BotoCoreError()):
            self.assertEqual(self.upload().status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.image.key, "old")

    def test_removing_it_leaves_it_in_the_pool(self):
        self.profile.image = image = CpuImage.objects.create(key="weiss/cpu-images/x.png")
        self.profile.save()
        with mock.patch("weiss.cpu_views.s3.delete") as delete:
            self.client.post(reverse("weiss:cpu_image_remove", args=[self.profile.pk]))
        delete.assert_not_called()
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.image)
        self.assertTrue(CpuImage.objects.filter(pk=image.pk).exists())

    def test_each_screen_can_have_its_own_image(self):
        main, intro = CpuImage.objects.create(key="main.png"), CpuImage.objects.create(key="intro.png")
        choose = reverse("weiss:cpu_image_choose", args=[self.profile.pk])
        self.client.post(choose, {"image": main.pk})
        self.client.post(choose, {"image": intro.pk, "screen": "intro"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.screen_image("intro"), intro)
        self.assertEqual(self.profile.screen_image("win"), main)  # falls back on the main one
        self.assertEqual(self.profile.image, main)
        with mock.patch("weiss.play.s3.presigned_image_urls", side_effect=lambda keys: {k: f"https://s3/{k}" for k in keys}):
            self.assertRedirects(self.client.get(self.profile.screen_url("intro")), "https://s3/intro.png", fetch_redirect_response=False)
            self.assertRedirects(self.client.get(self.profile.screen_url("lose")), "https://s3/main.png", fetch_redirect_response=False)
        self.client.post(reverse("weiss:cpu_image_remove", args=[self.profile.pk]), {"screen": "intro"})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.screen_image("intro"), main)

    def test_the_page_says_which_screen_and_counts_uses_across_them(self):
        image = CpuImage.objects.create(key="k.png")
        CpuProfile.objects.filter(pk=self.profile.pk).update(image=image, intro_image=image)
        page = self.client.get(reverse("weiss:cpu_images", args=[self.profile.pk]), {"screen": "lose"})
        self.assertEqual(page.context["screen"], "lose")
        self.assertIsNone(page.context["current"])
        self.assertEqual(page.context["page"].object_list[0].uses, 2)
        self.assertContains(page, 'name="screen" value="lose"')
        self.assertEqual(self.client.get(reverse("weiss:cpu_images", args=[self.profile.pk]), {"screen": "nope"}).context["screen"], "main")

    def test_two_cpus_can_share_one(self):
        image = CpuImage.objects.create(key="shared.png")
        other = self.cpu("Other")
        for profile in (self.profile, other):
            self.client.post(reverse("weiss:cpu_image_choose", args=[profile.pk]), {"image": image.pk})
            profile.refresh_from_db()
            self.assertEqual(profile.image, image)

    def test_deleting_from_the_pool_clears_it_everywhere(self):
        self.profile.image = image = CpuImage.objects.create(key="gone.png")
        self.profile.save()
        with mock.patch("weiss.cpu_views.s3.delete") as delete:
            self.client.post(reverse("weiss:cpu_image_delete", args=[image.pk]), {"profile": self.profile.pk})
        delete.assert_called_once_with("gone.png")
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.image)

    def test_the_pool_page_searches_and_pages(self):
        for i in range(61):
            CpuImage.objects.create(key=f"k{i}.png", name=f"Levi {i}", series="Attack on Titan")
        CpuImage.objects.create(key="other.png", name="Rapi", series="NIKKE")
        page = self.client.get(reverse("weiss:cpu_images", args=[self.profile.pk]), {"q": "levi"})
        self.assertEqual(len(page.context["page"].object_list), 60)
        self.assertEqual(page.context["page"].paginator.count, 61)
        self.assertNotContains(page, "Rapi")
        self.assertEqual(page.context["page"].object_list[0].name, "Levi 60")  # the newest first
        self.assertContains(self.client.get(reverse("weiss:cpu_images", args=[self.profile.pk]), {"q": "nikke"}), "Rapi")

    def test_only_staff_see_the_pool(self):
        image = CpuImage.objects.create(key="k.png")
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("weiss:cpu_images", args=[self.profile.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("weiss:cpu_pool_image", args=[image.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:cpu_image_choose", args=[self.profile.pk]), {"image": image.pk}).status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:cpu_image_delete", args=[image.pk])).status_code, 403)

    def test_players_can_view_it(self):
        self.profile.image = CpuImage.objects.create(key="k.png")
        self.profile.save()
        self.client.force_login(self.alice)
        with mock.patch("weiss.play.s3.presigned_image_urls", return_value={"k.png": "https://s3/k"}):
            response = self.client.get(self.profile.image_url)
        self.assertRedirects(response, "https://s3/k", fetch_redirect_response=False)

    def test_texts_are_saved_from_the_form(self):
        self.client.post(reverse("weiss:cpu_profile_update", args=[self.profile.pk]), {
            "name": "Bot", "model": "standard", "aggression": 1, "deck": self.profile.deck_id, "intro_text": "Hi", "player_win_text": "Ow", "player_lose_text": "Ha"})
        self.profile.refresh_from_db()
        self.assertEqual((self.profile.intro_text, self.profile.player_win_text, self.profile.player_lose_text), ("Hi", "Ow", "Ha"))


class IntroAndEndScreenTests(Base):
    def challenge(self, **fields):
        profile = self.cpu("Bot", intro_text="Prepare yourself", player_win_text="You got me", player_lose_text="Too easy", **fields)
        self.client.force_login(self.alice)
        self.client.post(reverse("weiss:play_vs_cpu"), {"cpu": profile.pk, "deck": self.deck.pk})
        return GameRoom.objects.get(host=self.alice), profile

    def test_a_cpu_battle_opens_on_its_screen(self):
        room, _ = self.challenge()
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertTrue(data["intro"])
        self.assertEqual((data["cpu"]["name"], data["cpu"]["intro"]), ("Bot", "Prepare yourself"))

    def test_nothing_happens_until_it_is_dismissed(self):
        room, _ = self.challenge()
        before = json.dumps(room.state)
        url = reverse("weiss:play_action", args=[room.pk])
        self.assertEqual(self.post(url, {"type": "rps", "choice": "rock"}).status_code, 409)
        self.assertEqual(json.dumps(play.cpu_step(room, wait=False).state), before)
        self.assertFalse(self.post(url, {"type": "intro_done"}).json().get("intro"))
        room.refresh_from_db()
        self.assertIsNotNone(play.cpu_step(room, wait=False).state["rps"]["picks"].get(str(room.guest_id)))

    def test_a_game_between_players_has_no_such_screen(self):
        bob = player("bob")
        room = GameRoom(host=self.alice, guest=bob, host_deck=self.deck, guest_deck=self.deck_for(bob, "B"), status="playing")
        play.deal(room)
        room.save()
        self.assertNotIn("intro", play.board_payload(room, self.alice))
        self.assertNotIn("cpu", play.board_payload(room, self.alice))

    def test_a_rematch_doesnt_show_it_again_but_a_new_set_does(self):
        room, _ = self.challenge()
        room.state.pop("cpu_intro")
        play.deal(room)
        self.assertNotIn("cpu_intro", room.state)
        room.save()
        self.client.post(reverse("weiss:play_start", args=[room.pk]))
        room.refresh_from_db()
        self.assertTrue(room.state["cpu_intro"])

    def test_the_end_screen_gets_both_texts_and_the_image(self):
        room, profile = self.challenge()
        CpuProfile.objects.filter(pk=profile.pk).update(image=CpuImage.objects.create(key="k.png"))
        room.refresh_from_db()
        cpu = play.board_payload(room, self.alice)["cpu"]
        self.assertEqual((cpu["win"], cpu["lose"]), ("You got me", "Too easy"))
        self.assertIn("/image/", cpu["image"])
        self.assertIn("screen=win", cpu["images"]["win"])


class ArcadeBuilderTests(Base):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:arcade_create"), {"name": "Ark"})
        self.scenario = ArcadeScenario.objects.get()

    def add(self, cpu, role):
        return self.client.post(reverse("weiss:arcade_entry_add", args=[self.scenario.pk]), {"cpu": cpu.pk, "role": role}, follow=True)

    def test_only_one_opener_and_one_anchor(self):
        self.add(self.cpu("A"), "opener")
        self.assertContains(self.add(self.cpu("B"), "opener"), "already has")
        self.add(self.cpu("C"), "anchor")
        self.assertContains(self.add(self.cpu("D"), "anchor"), "already has")
        self.add(self.cpu("E"), "filler")
        self.add(self.cpu("F"), "filler")
        self.assertEqual(self.scenario.entries.count(), 4)

    def test_a_cpu_only_goes_in_a_list_once(self):
        cpu = self.cpu("A")
        self.add(cpu, "opener")
        self.add(cpu, "anchor")
        self.assertEqual(self.scenario.entries.count(), 1)

    def test_it_isnt_ready_without_both_ends_and_finalized_cpus(self):
        self.assertIn("opener and an anchor", arcade.scenario_problem(self.scenario))
        a, b = self.cpu("A"), self.cpu("B")
        self.add(a, "opener")
        self.assertIn("anchor", arcade.scenario_problem(self.scenario))
        self.add(b, "anchor")
        self.assertIsNone(arcade.scenario_problem(ArcadeScenario.objects.get()))
        CpuProfile.objects.filter(pk=b.pk).update(finalized=False)
        self.assertIn("B", arcade.scenario_problem(ArcadeScenario.objects.get()))
        self.assertEqual(arcade.ready_scenarios(), [])

    def test_a_bad_role_is_refused(self):
        self.add(self.cpu("A"), "boss")
        self.assertEqual(self.scenario.entries.count(), 0)

    def test_players_cant_build(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.post(reverse("weiss:arcade_create"), {"name": "X"}).status_code, 403)
        self.assertEqual(self.add(self.cpu("A"), "opener").status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:arcade_delete", args=[self.scenario.pk])).status_code, 403)

    def test_the_tab_shows_it(self):
        self.add(self.cpu("A"), "opener")
        self.assertContains(self.client.get(reverse("weiss:cpu_home")), "Ark")

    def test_profiles_and_lists_can_each_be_collapsed(self):
        cpu = self.cpu("A")
        page = self.client.get(reverse("weiss:cpu_home"))
        self.assertContains(page, f'data-collapse="profile-{cpu.pk}"')
        self.assertContains(page, f'data-collapse="arcade-{self.scenario.pk}"')


class ArcadeRunTests(Base):
    def setUp(self):
        super().setUp()
        self.scenario = ArcadeScenario.objects.create(name="Ark")
        self.opener, self.filler1, self.filler2, self.anchor = self.cpu("Open"), self.cpu("F1"), self.cpu("F2"), self.cpu("Last", intro_text="The end")
        for cpu, role in ((self.opener, "opener"), (self.filler1, "filler"), (self.filler2, "filler"), (self.anchor, "anchor")):
            ArcadeEntry.objects.create(scenario=self.scenario, cpu=cpu, role=role)
        self.client.force_login(self.alice)

    def start(self):
        response = self.client.post(reverse("weiss:arcade_start"), {"scenario": self.scenario.pk, "deck": self.deck.pk})
        room = GameRoom.objects.get(host=self.alice)
        self.assertRedirects(response, reverse("weiss:play_room", args=[room.pk]))
        self.url = reverse("weiss:play_action", args=[room.pk])
        return room

    def end_fight(self, winner):
        room = GameRoom.objects.get(host=self.alice)
        room.state.pop("cpu_intro", None)
        who = room.host_id if winner == "me" else room.guest_id

        def ends(state, *args, **kwargs):
            state["game_over"] = {"winner": str(who), "reason": "level", "rematch": []}
            return {}
        with mock.patch.object(play.game, "apply", side_effect=ends):
            play.play_action(room, room.host_id, {"type": "x"}, lookups={"info": None})
        return GameRoom.objects.get(pk=room.pk)

    def test_opener_first_anchor_last_fillers_between_in_random_order(self):
        seen = set()
        for seed in range(30):
            order = arcade.fight_order(ArcadeScenario.objects.prefetch_related("entries").get(), random.Random(seed))
            self.assertEqual((order[0], order[-1]), (self.opener.pk, self.anchor.pk))
            self.assertCountEqual(order[1:3], [self.filler1.pk, self.filler2.pk])
            seen.add(tuple(order))
        self.assertEqual(len(seen), 2)

    def test_it_starts_on_the_openers_screen(self):
        room = self.start()
        self.assertEqual(room.cpu_profile, self.opener)
        data = self.client.get(reverse("weiss:play_state", args=[room.pk])).json()
        self.assertTrue(data["intro"])
        self.assertEqual((data["arcade"]["fight"], data["arcade"]["total"], data["arcade"]["cleared"]), (1, 4, False))

    def test_only_a_ready_scenario_and_my_own_deck(self):
        CpuProfile.objects.filter(pk=self.anchor.pk).update(finalized=False)
        self.assertEqual(self.client.post(reverse("weiss:arcade_start"), {"scenario": self.scenario.pk, "deck": self.deck.pk}).status_code, 302)
        self.assertFalse(GameRoom.objects.exists())
        CpuProfile.objects.filter(pk=self.anchor.pk).update(finalized=True)
        theirs = self.deck_for(player("bob"), "Theirs")
        self.assertEqual(self.client.post(reverse("weiss:arcade_start"), {"scenario": self.scenario.pk, "deck": theirs.pk}).status_code, 404)

    def test_winning_continues_to_the_next_cpu_with_a_new_screen(self):
        self.start()
        self.end_fight("me")
        data = self.post(self.url, {"type": "arcade_continue"}).json()
        self.assertTrue(data["intro"])
        room = GameRoom.objects.get(host=self.alice)
        self.assertEqual(room.cpu_profile_id, room.arcade_run.order[1])
        self.assertEqual(room.guest_deck, room.cpu_profile.deck)
        self.assertIsNone(room.state.get("game_over"))
        self.assertEqual(room.state["game_number"] if "game_number" in room.state else 1, 1)

    def test_losing_retries_the_same_cpu_with_a_new_screen(self):
        self.start()
        self.end_fight("cpu")
        self.assertTrue(self.post(self.url, {"type": "arcade_retry"}).json()["intro"])
        room = GameRoom.objects.get(host=self.alice)
        self.assertEqual(room.cpu_profile, self.opener)
        self.assertEqual((room.arcade_run.position, room.arcade_run.losses), (0, 1))

    def test_continue_needs_a_win_and_retry_a_loss(self):
        self.start()
        self.post(self.url, {"type": "intro_done"})
        self.assertEqual(self.post(self.url, {"type": "arcade_continue"}).status_code, 400)
        self.end_fight("cpu")
        self.assertEqual(self.post(self.url, {"type": "arcade_continue"}).status_code, 400)
        self.post(self.url, {"type": "arcade_retry"})
        self.end_fight("me")
        self.assertEqual(self.post(self.url, {"type": "arcade_retry"}).status_code, 400)

    def test_a_rematch_and_the_side_links_arent_for_a_run(self):
        room = self.start()
        self.end_fight("me")
        self.assertEqual(self.post(self.url, {"type": "rematch"}).status_code, 400)
        self.assertEqual(self.post(self.url, {"type": "end_match"}).status_code, 400)
        before = GameRoom.objects.get(pk=room.pk).cpu_profile_id
        self.client.post(reverse("weiss:play_start", args=[room.pk]))
        self.client.post(reverse("weiss:play_reset", args=[room.pk]))
        room = GameRoom.objects.get(pk=room.pk)
        self.assertEqual((room.status, room.cpu_profile_id), ("playing", before))
        self.assertTrue(room.state.get("game_over"))

    def clear(self, deck_url=True):
        self.start()
        for i in range(4):
            self.end_fight("me")
            if i < 3:
                self.post(self.url, {"type": "arcade_continue"})

    def test_beating_the_anchor_clears_it_and_marks_the_deck(self):
        self.clear()
        run = ArcadeRun.objects.get()
        self.assertEqual(run.status, "cleared")
        clear = ArcadeClear.objects.get()
        self.assertEqual((clear.deck, clear.count, clear.name), (self.deck, 1, "Ark"))
        self.assertTrue(self.client.get(reverse("weiss:play_state", args=[GameRoom.objects.get().pk])).json()["arcade"]["cleared"])
        self.assertContains(self.client.get(reverse("weiss:lists")), "Ark")
        self.assertContains(self.client.get(reverse("weiss:list", args=[self.deck.pk])), "Ark ×1")

    def test_finishing_goes_to_the_profile_and_clearing_again_counts_up(self):
        self.clear()
        response = self.post(self.url, {"type": "arcade_quit"}).json()
        self.assertEqual(response["redirect"], reverse("weiss:profile"))
        self.assertFalse(GameRoom.objects.exists())
        self.clear()
        self.assertEqual(ArcadeClear.objects.get().count, 2)
        self.assertEqual(ArcadeRun.objects.filter(status="cleared").count(), 2)

    def test_a_marker_is_per_deck(self):
        self.clear()
        self.post(self.url, {"type": "arcade_quit"})
        self.assertNotContains(self.client.get(reverse("weiss:list", args=[self.deck_for(self.alice, "Other").pk])), "Ark ×")

    def test_quitting_ends_the_run_and_it_stays_on_the_profile(self):
        self.start()
        self.end_fight("me")
        self.client.post(reverse("weiss:arcade_quit", args=[GameRoom.objects.get().pk]))
        run = ArcadeRun.objects.get()
        self.assertEqual((run.status, run.position), ("abandoned", 1))
        self.assertFalse(GameRoom.objects.exists())
        page = self.client.get(reverse("weiss:profile"))
        self.assertContains(page, "Ark")
        self.assertContains(page, "Stopped")
        self.assertEqual(ArcadeClear.objects.count(), 0)

    def test_deleting_the_room_ends_the_run(self):
        room = self.start()
        self.client.post(reverse("weiss:play_delete", args=[room.pk]))
        self.assertEqual(ArcadeRun.objects.get().status, "abandoned")

    def test_a_filler_taken_away_is_skipped(self):
        self.start()
        run = ArcadeRun.objects.get()
        CpuProfile.objects.filter(pk=run.order[1]).update(finalized=False)
        self.end_fight("me")
        self.post(self.url, {"type": "arcade_continue"})
        self.assertEqual(GameRoom.objects.get().cpu_profile_id, run.order[2])

    def test_with_the_anchor_gone_the_run_stops_rather_than_breaking(self):
        self.start()
        CpuProfile.objects.filter(pk=self.anchor.pk).delete()
        run = ArcadeRun.objects.get()
        run.position = len(run.order) - 2
        run.save()
        self.end_fight("me")
        self.assertEqual(self.post(self.url, {"type": "arcade_continue"}).json()["redirect"], reverse("weiss:play_rooms"))
        self.assertEqual(ArcadeRun.objects.get().status, "abandoned")

    def test_a_deleted_deck_stops_the_run(self):
        self.start()
        self.end_fight("me")
        CardList.objects.filter(pk=self.deck.pk).delete()
        self.assertIn("redirect", self.post(self.url, {"type": "arcade_continue"}).json())

    def test_another_players_room_is_off_limits(self):
        room = self.start()
        self.client.force_login(player("bob"))
        self.assertEqual(self.post(self.url, {"type": "arcade_quit"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:arcade_quit", args=[room.pk])).status_code, 403)

    def test_each_game_is_still_in_the_match_history(self):
        self.start()
        self.end_fight("cpu")
        self.post(self.url, {"type": "arcade_retry"})
        self.end_fight("me")
        self.assertEqual(GameRecord.objects.count(), 2)

    def test_the_play_page_offers_ready_scenarios(self):
        page = self.client.get(reverse("weiss:play_rooms"))
        self.assertContains(page, "Arcade Mode")
        self.assertContains(page, "Ark")
