from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from . import world
from .models import Card, WorldSave, WorldSettings
from .test_minigames import make_set as pictured_set
from .test_profile import player
from .test_world import LOADOUT_FIELDS, SET, everywhere_rule, give_cpu, make_set, staff_user
from .world_views import CLOSED_MESSAGE


def open_world(on=True):
    WorldSettings.objects.update_or_create(pk=1, defaults={"open_to_players": on})


class AccessBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_set()

    def setUp(self):
        self.staff = staff_user()
        self.alice = player("alice")
        self.bob = player("bob")
        self.save = world.start(self.alice, 1, SET)
        self.bobs = world.start(self.bob, 2, SET)

    def town(self, slot=1):
        return reverse("weiss:world_town", args=[slot])

    def post_move(self, name, user, slot=1, **fields):
        save = world.save_in(user, slot)
        return self.client.post(reverse(name, args=[slot]), {"version": str(save.version), **fields})


class ClosedWorldTests(AccessBase):
    def test_a_player_is_redirected_to_the_sets_with_a_message(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.town())
        self.assertRedirects(response, reverse("weiss:sets"), fetch_redirect_response=False)
        self.assertIn(CLOSED_MESSAGE, [str(m) for m in get_messages(response.wsgi_request)])

    def test_a_player_gets_a_403_with_the_message_from_a_json_endpoint(self):
        self.client.force_login(self.alice)
        for response in (self.client.get(reverse("weiss:world_town_state", args=[1])),
                         self.post_move("weiss:world_travel", self.alice, place="cafe")):
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json(), {"error": CLOSED_MESSAGE})

    def test_a_player_gets_the_redirect_from_every_world_page(self):
        self.client.force_login(self.alice)
        for url in (reverse("weiss:world_home"), reverse("weiss:world_save", args=[1]), reverse("weiss:world_new", args=[3]),
                    reverse("weiss:world_quests", args=[1]), reverse("weiss:world_events", args=[1]),
                    reverse("weiss:world_people", args=[1]), reverse("weiss:world_deck", args=[1])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertEqual(response.url, reverse("weiss:sets"), url)

    def test_staff_still_play(self):
        world.start(self.staff, 1, SET)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.town()).status_code, 200)

    def test_a_weiss_user_outside_the_group_is_sent_to_log_in(self):
        self.client.force_login(User.objects.create_user("outsider", password="x"))
        response = self.client.get(self.town())
        self.assertRedirects(response, f"{reverse('login')}?next={self.town()}", fetch_redirect_response=False)


class OpenWorldTests(AccessBase):
    def setUp(self):
        super().setUp()
        open_world()
        self.client.force_login(self.alice)

    def test_a_player_can_see_every_player_page(self):
        for url in (reverse("weiss:world_home"), reverse("weiss:world_save", args=[1]), self.town(),
                    reverse("weiss:world_quests", args=[1]), reverse("weiss:world_events", args=[1]),
                    reverse("weiss:world_people", args=[1])):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get(reverse("weiss:world_town_state", args=[1])).status_code, 200)

    def test_a_player_can_move_in_the_town(self):
        response = self.post_move("weiss:world_travel", self.alice, place="cafe")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(world.save_in(self.alice, 1).place, "cafe")

    def test_staff_only_tools_stay_forbidden_to_a_player(self):
        for url in (reverse("weiss:world_test"), reverse("weiss:world_settings"), reverse("weiss:world_schedules"),
                    reverse("weiss:world_reports"), reverse("weiss:world_events_staff"), reverse("weiss:world_minigames")):
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(self.client.post(reverse("weiss:world_settings")).status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:world_report_update", args=[1]), {"resolved": "1"}).status_code, 403)

    def test_a_player_cannot_see_the_staff_report_list(self):
        self.assertEqual(self.client.get(reverse("weiss:world_reports")).status_code, 403)

    def test_a_player_cannot_use_the_staff_test_tools_by_hand(self):
        save = world.save_in(self.alice, 1)
        save.flags["test_mode"] = True
        save.save(update_fields=["flags"])
        self.assertFalse(world.test_mode(world.save_in(self.alice, 1)))
        self.assertEqual(self.post_move("weiss:world_jump", self.alice, weekday="1").status_code, 400)
        self.assertEqual(self.post_move("weiss:world_level", self.alice, cpu="1").status_code, 400)
        self.assertEqual(self.post_move("weiss:world_tutorial", self.alice, act="skip").status_code, 400)
        response = self.post_move("weiss:world_test_mode", self.alice, on="1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("staff", response.json()["error"].lower())

    def test_staff_test_mode_still_works(self):
        self.client.force_login(self.staff)
        world.start(self.staff, 1, SET)
        response = self.post_move("weiss:world_test_mode", self.staff, on="1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(world.test_mode(world.save_in(self.staff, 1)))

    def test_a_player_only_reaches_their_own_saves(self):
        self.assertEqual(self.client.get(self.town(2)).status_code, 302)
        self.assertEqual(self.client.get(self.town(2)).url, reverse("weiss:world_home"))
        response = self.client.post(reverse("weiss:world_travel", args=[2]), {"version": str(self.bobs.version), "place": "cafe"})
        self.assertEqual(response.status_code, 404)
        self.bobs.refresh_from_db()
        self.assertEqual(self.bobs.place, "")

    def test_a_player_cannot_read_someone_elses_save_by_slot(self):
        self.assertEqual(self.client.get(reverse("weiss:world_town_state", args=[2])).status_code, 404)


class OpenFlagTests(AccessBase):
    def test_no_settings_row_means_closed(self):
        self.assertFalse(world.open_to(self.alice))
        self.assertTrue(world.open_to(self.staff))

    def test_open_lets_weiss_players_in(self):
        open_world()
        self.assertTrue(world.open_to(self.alice))

    def test_a_user_outside_the_weiss_group_is_never_let_in(self):
        open_world()
        self.assertFalse(world.open_to(User.objects.create_user("outsider", password="x")))

    def test_saving_the_settings_form_leaves_the_switch_as_it_was(self):
        self.client.force_login(self.staff)
        form = {"start_packs": "20", "start_money": "1000", "pack_price": "300", "specialty_price": "600",
                "card_price": "3000", "request_price": "300", "win_payout": "200", "first_win_bonus": "100",
                "talk_points": "6", "start_cast": "12", "weekly_cast": "4", "arrival_coins": "200",
                "arrival_points": "8", "ranks": "Stranger: 0\nFriend: 40", **LOADOUT_FIELDS}
        open_world()
        self.client.post(reverse("weiss:world_settings"), form)
        self.assertTrue(WorldSettings.current().open_to_players)
        self.client.post(reverse("weiss:world_settings"), {**form, "open_to_players": "0"})
        self.assertTrue(WorldSettings.current().open_to_players)
        open_world(False)
        self.client.post(reverse("weiss:world_settings"), {**form, "open_to_players": "1"})
        self.assertFalse(WorldSettings.current().open_to_players)


class SwitchTests(AccessBase):
    def switch(self, value):
        return self.client.post(reverse("weiss:world_switch"), {"open": value} if value is not None else {})

    def test_staff_open_and_close_the_world(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.switch("1").status_code, 302)
        self.assertTrue(WorldSettings.current().open_to_players)
        self.assertEqual(WorldSettings.current().updated_by, self.staff)
        self.switch("0")
        self.assertFalse(WorldSettings.current().open_to_players)

    def test_closing_keeps_every_save(self):
        open_world()
        before = {save.pk: (save.version, save.place, save.money) for save in WorldSave.objects.all()}
        self.client.force_login(self.staff)
        self.switch("0")
        self.assertEqual({save.pk: (save.version, save.place, save.money) for save in WorldSave.objects.all()}, before)
        self.assertEqual(len(before), 2)

    def test_the_switch_creates_the_settings_row_when_missing(self):
        self.assertFalse(WorldSettings.objects.exists())
        self.client.force_login(self.staff)
        self.switch("1")
        self.assertTrue(WorldSettings.current().open_to_players)

    def test_a_player_cannot_open_the_world(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.switch("1").status_code, 403)
        self.assertFalse(WorldSettings.objects.exists())

    def test_a_get_is_refused(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("weiss:world_switch")).status_code, 405)

    def test_a_value_other_than_1_or_0_is_refused(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.switch("yes").status_code, 400)
        self.assertEqual(self.switch(None).status_code, 400)
        self.assertFalse(WorldSettings.objects.exists())

    def test_the_context_says_whether_world_is_open(self):
        self.client.force_login(self.alice)
        self.assertFalse(self.client.get(reverse("weiss:sets")).context["world_open"])
        open_world()
        self.assertTrue(self.client.get(reverse("weiss:sets")).context["world_open"])


class PlayerSweepTests(AccessBase):
    def setUp(self):
        super().setUp()
        self.cards = list(Card.objects.all())
        pictured_set(30)  # a minigame plays from a pictured set
        self.save.pool = {str(c.pk): 4 for c in self.cards}
        self.save.packs, self.save.rewards = 0, []
        self.save.save()
        climaxes = [c for c in self.cards if c.card_type == "Climax"][:2]
        others = [c for c in self.cards if c.card_type != "Climax"][:14]
        world.save_deck(self.save, {c.pk: 4 for c in climaxes} | {c.pk: 3 for c in others})
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.cinder)
        world.travel(self.save, "plaza")
        world.relation(self.save, self.cinder.pk)["points"] = 1000  # a friend: a minigame's played with those
        world.changed(self.save, "relations")
        open_world()
        self.client.force_login(self.alice)

    def test_a_player_duels_someone_in_town_and_plays_the_room(self):
        response = self.post_move("weiss:world_duel", self.alice, cpu=self.cinder.pk)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get(response.json()["go"]).status_code, 200)

    def test_a_player_plays_a_minigame_with_someone_in_town(self):
        response = self.post_move("weiss:world_minigame", self.alice, cpu=self.cinder.pk, game="memory")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get(response.json()["go"]).status_code, 200)
        data = self.client.get(reverse("weiss:world_minigame_data", args=[1]))
        self.assertEqual(data.status_code, 200, data.content)
