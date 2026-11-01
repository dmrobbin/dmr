from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.access import WEISS_GROUP

from . import play
from .models import Card, CardList, CardListEntry, CpuProfile, GameRecord, GameRoom, PlayerProfile, cpu_user


def player(name):
    user = User.objects.create_user(name, password="x")
    Group.objects.get_or_create(name=WEISS_GROUP)[0].user_set.add(user)
    return user


def add_card(serial="T/1", name="Rapi", image="https://example.com/rapi.png"):
    return Card.objects.create(serial_number=serial, name=name, expansion="E", expansion_id=1, card_type="Character", level=0, image_url=image)


def deck_for(user, card, name="My deck"):
    deck = CardList.objects.create(user=user, name=name)
    CardListEntry.objects.create(card_list=deck, card=card, quantity=4)
    return deck


def end_game(room, winner, reason="level"):
    """The action that ends a game, as far as play_action can tell."""
    def ends(state, *args, **kwargs):
        state["game_over"] = {"winner": str(winner.pk), "reason": reason, "rematch": []}
        return {}
    with mock.patch.object(play.game, "apply", side_effect=ends):
        play.play_action(room, room.host_id, {"type": "x"}, lookups={"info": None})


class PictureTests(TestCase):
    def setUp(self):
        self.user = player("alice")
        self.client.force_login(self.user)
        self.card = add_card()
        self.url = reverse("weiss:profile_picture")

    def save(self, **fields):
        return self.client.post(self.url, {"card": self.card.pk, "x": .5, "y": .6, "r": .25, **fields})

    def test_saving_a_circle_on_a_card(self):
        self.assertRedirects(self.save(), reverse("weiss:profile"), fetch_redirect_response=False)
        avatar = PlayerProfile.objects.get(user=self.user).avatar
        self.assertEqual(avatar["image"], reverse("weiss:card_image", args=[self.card.pk]))
        self.assertEqual((avatar["width"], avatar["left"], avatar["top"]), (200, -50, -70))

    def test_the_profile_page_shows_it(self):
        self.save()
        self.assertContains(self.client.get(reverse("weiss:profile")), reverse("weiss:card_image", args=[self.card.pk]))

    def test_circles_off_the_card_are_refused(self):
        for bad in ({"x": .9}, {"x": .1}, {"y": .1}, {"y": 5}, {"r": .9}, {"r": 0}, {"r": "nan"}, {"x": "inf"}, {"x": "left"}):
            self.save(**bad)
            self.assertFalse(PlayerProfile.objects.get(user=self.user).avatar, bad)

    def test_a_card_must_exist_and_have_an_image(self):
        for card in (999999, "x", add_card("T/2", "Blank", "").pk):
            self.save(card=card)
            self.assertFalse(PlayerProfile.objects.get(user=self.user).avatar, card)

    def test_removing_it(self):
        self.save()
        self.client.post(self.url, {"remove": "1"})
        self.assertIsNone(PlayerProfile.objects.get(user=self.user).avatar)

    def test_the_picker_starts_from_the_saved_circle(self):
        self.save()
        self.assertEqual(self.client.get(self.url).context["current"]["r"], .25)

    def test_it_goes_if_the_card_does(self):
        self.save()
        self.card.delete()
        self.assertIsNone(PlayerProfile.objects.get(user=self.user).avatar)

    def test_search_finds_cards_with_images(self):
        add_card("T/2", "Rapid Blank", "")
        add_card("NIK/9", "Anis")
        search = reverse("weiss:avatar_search")
        self.assertEqual([c["name"] for c in self.client.get(search, {"q": "rap"}).json()["cards"]], ["Rapi"])
        self.assertEqual([c["name"] for c in self.client.get(search, {"q": "nik/"}).json()["cards"]], ["Anis"])
        self.assertEqual(self.client.get(search, {"q": "r"}).json()["cards"], [])

    def test_logged_out_visitors_are_sent_to_log_in(self):
        self.client.logout()
        for name in ("profile", "profile_picture", "avatar_search"):
            self.assertEqual(self.client.get(reverse(f"weiss:{name}")).status_code, 302)

    def test_the_menu_links_to_it(self):
        self.assertContains(self.client.get(reverse("weiss:sets")), f'href="{reverse("weiss:profile")}"')


class CpuPictureTests(TestCase):
    def setUp(self):
        self.card = add_card()
        self.profile = CpuProfile.objects.create(name="Bot")
        self.url = reverse("weiss:cpu_picture", args=[self.profile.pk])

    def test_staff_can_set_a_cpus_picture(self):
        self.client.force_login(User.objects.create_user("staff", password="x", is_staff=True))
        self.assertContains(self.client.get(self.url), "Picture for Bot")
        self.assertRedirects(self.client.post(self.url, {"card": self.card.pk, "x": .5, "y": .5, "r": .25}), reverse("weiss:cpu_home"), fetch_redirect_response=False)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.avatar_card, self.card)
        self.assertContains(self.client.get(reverse("weiss:cpu_home")), reverse("weiss:card_image", args=[self.card.pk]))

    def test_players_cant(self):
        self.client.force_login(player("alice"))
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {"card": self.card.pk, "x": .5, "y": .5, "r": .25}).status_code, 403)


class InGameTests(TestCase):
    def setUp(self):
        self.card = add_card()
        self.alice, self.bob = player("alice"), player("bob")

    def room(self, guest=None, **fields):
        guest = guest or self.bob
        room = GameRoom(host=self.alice, guest=guest, host_deck=deck_for(self.alice, self.card), guest_deck=deck_for(guest, self.card, "Theirs"), status="playing", **fields)
        play.deal(room)
        room.save()
        return room

    def picture(self, owner):
        owner.avatar_card, owner.avatar_x, owner.avatar_y, owner.avatar_r = self.card, .5, .5, .25
        owner.save()

    def test_the_board_gets_pictures_by_player_name(self):
        room = self.room()
        self.picture(PlayerProfile.objects.create(user=self.bob))
        avatars = play.board_payload(room, self.alice)["avatars"]
        self.assertEqual(list(avatars), ["bob"])
        self.assertEqual(avatars["bob"]["image"], reverse("weiss:card_image", args=[self.card.pk]))

    def test_a_cpus_picture_too(self):
        profile = CpuProfile.objects.create(name="Bot")
        self.picture(profile)
        room = self.room(cpu_user(), cpu_name="Bot", cpu_profile=profile)
        self.assertEqual(list(play.board_payload(room, self.alice)["avatars"]), ["Bot"])

    def test_no_picture_means_the_name_stays(self):
        PlayerProfile.objects.create(user=self.bob)
        self.assertEqual(play.board_payload(self.room(), self.alice)["avatars"], {})

    def test_two_players_with_one_name_keep_their_names(self):
        namesake = CpuProfile.objects.create(name="alice")
        self.picture(namesake)
        room = self.room(cpu_user(), cpu_name="alice", cpu_profile=namesake)
        self.assertEqual(play.board_payload(room, self.alice)["avatars"], {})


class MatchHistoryTests(TestCase):
    def setUp(self):
        self.card = add_card()
        self.alice, self.bob = player("alice"), player("bob")
        self.room = GameRoom(host=self.alice, guest=self.bob, host_deck=deck_for(self.alice, self.card), guest_deck=deck_for(self.bob, self.card, "Theirs"), status="playing")
        play.deal(self.room)
        self.room.save()

    def test_a_finished_game_is_recorded_once(self):
        end_game(self.room, self.bob)
        record = GameRecord.objects.get()
        self.assertEqual((record.host, record.guest, record.winner, record.host_deck_name, record.guest_deck_name), (self.alice, self.bob, "guest", "My deck", "Theirs"))
        with mock.patch.object(play.game, "apply", return_value={}):
            play.play_action(self.room, self.alice.pk, {"type": "x"}, lookups={"info": None})
        self.assertEqual(GameRecord.objects.count(), 1)

    def test_each_side_sees_their_own_result(self):
        end_game(self.room, self.bob)
        self.client.force_login(self.alice)
        page = self.client.get(reverse("weiss:profile"))
        self.assertEqual((page.context["played"], page.context["won"], page.context["lost"]), (1, 0, 1))
        self.assertContains(page, "vs bob")
        self.assertContains(page, "with My deck")
        self.client.force_login(self.bob)
        page = self.client.get(reverse("weiss:profile"))
        self.assertEqual((page.context["won"], page.context["lost"]), (1, 0))
        self.assertContains(page, "vs alice")
        self.assertContains(page, "with Theirs")

    def test_it_outlasts_the_room_and_the_deck(self):
        end_game(self.room, self.alice)
        CardList.objects.all().delete()
        self.room.delete()
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("weiss:profile")), "with My deck")

    def test_nobody_else_sees_it(self):
        end_game(self.room, self.alice)
        self.client.force_login(player("carol"))
        self.assertEqual(self.client.get(reverse("weiss:profile")).context["played"], 0)

    def test_a_game_against_a_cpu_says_so(self):
        cpu = cpu_user()
        profile = CpuProfile.objects.create(name="Bot")
        room = GameRoom(host=self.alice, guest=cpu, host_deck=deck_for(self.alice, self.card), guest_deck=deck_for(cpu, self.card), cpu_name="Bot", cpu_profile=profile, status="playing")
        play.deal(room)
        room.save()
        end_game(room, self.alice)
        self.client.force_login(self.alice)
        page = self.client.get(reverse("weiss:profile"))
        self.assertContains(page, "vs Bot")
        self.assertContains(page, ">CPU<")

    def test_lists_on_the_page_are_only_my_own(self):
        CardList.objects.create(user=self.alice, name="Reserved", reserved_for_cpu=True)
        self.client.force_login(self.alice)
        names = {c.name for c in self.client.get(reverse("weiss:profile")).context["lists"]}
        self.assertEqual(names, {"My deck"})
