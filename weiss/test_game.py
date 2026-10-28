import json

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.access import WEISS_GROUP

from . import game
from .models import Card, CardList, CardListEntry, GameRoom


def no_shuffle(cards):
    pass


def started(deck_a=range(1, 21), deck_b=range(101, 121)):
    return game.new_game([(1, "alice", list(deck_a)), (2, "bob", list(deck_b))], shuffle=no_shuffle)


def zones(state, player):
    return state["players"][str(player)]["zones"]


class NewGameTests(TestCase):
    def test_each_player_draws_five_from_their_own_deck(self):
        state = started()
        self.assertEqual([c["card"] for c in zones(state, 1)["hand"]], [20, 19, 18, 17, 16])
        self.assertEqual(len(zones(state, 1)["deck"]), 15)
        self.assertEqual(len(zones(state, 2)["hand"]), 5)
        self.assertEqual(state["turn"], "1")


class HiddenInformationTests(TestCase):
    def test_opponent_sees_counts_not_cards_for_hand_deck_and_stock(self):
        state = started()
        game.apply(state, 2, {"type": "move_top", "from": "deck", "to": "stock", "count": 2})
        alice = game.view(state, 1)
        self.assertEqual(alice["opponent"]["zones"]["hand"], {"count": 5})
        self.assertEqual(alice["opponent"]["zones"]["deck"], {"count": 13})
        self.assertEqual(alice["opponent"]["zones"]["stock"], {"count": 2})
        self.assertEqual(alice["me"]["zones"]["deck"], {"count": 15})  # your own deck order is hidden too
        self.assertEqual(len(alice["me"]["zones"]["hand"]), 5)
        self.assertNotIn(101, game.visible_cards(alice))

    def test_face_down_cards_hidden_from_opponent_only(self):
        state = started()
        card = zones(state, 1)["hand"][0]
        game.apply(state, 1, {"type": "move", "uid": card["uid"], "to": "memory"})
        game.apply(state, 1, {"type": "flip", "uid": card["uid"]})
        self.assertIsNone(game.view(state, 2)["opponent"]["zones"]["memory"][0]["card"])
        self.assertEqual(game.view(state, 1)["me"]["zones"]["memory"][0]["card"], card["card"])

    def test_log_names_public_cards_only(self):
        state = started()
        names = {20: "Elegg", 19: "Anis"}.get
        hand = zones(state, 1)["hand"]
        game.apply(state, 1, {"type": "move", "uid": hand[0]["uid"], "to": "C1"}, name=names)
        game.apply(state, 1, {"type": "move", "uid": hand[0]["uid"], "to": "stock"}, name=names)
        self.assertIn("Elegg", state["log"][-2]["text"])
        self.assertEqual(state["log"][-1]["text"], "moved a card from hand to stock")


class MoveTests(TestCase):
    def setUp(self):
        self.state = started()
        self.hand = zones(self.state, 1)["hand"]

    def play(self, uid, to):
        game.apply(self.state, 1, {"type": "move", "uid": uid, "to": to})

    def stage(self):
        return {slot: (c["card"] if c else None) for slot, c in self.state["players"]["1"]["stage"].items()}

    def test_play_rest_and_swap_on_stage(self):
        first, second = self.hand[0]["uid"], self.hand[1]["uid"]
        self.play(first, "C1")
        self.play(second, "C2")
        game.apply(self.state, 1, {"type": "position", "uid": first, "pos": "rest"})
        self.assertEqual(self.state["players"]["1"]["stage"]["C1"]["pos"], "rest")
        self.play(first, "C2")  # stage to stage swaps
        self.assertEqual(self.stage()["C1"], 19)
        self.assertEqual(self.stage()["C2"], 20)

    def test_playing_onto_occupied_slot_sends_old_card_to_waiting_room(self):
        first, second = self.hand[0]["uid"], self.hand[1]["uid"]
        self.play(first, "C1")
        self.play(second, "C1")
        self.assertEqual(self.stage()["C1"], 19)
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [20])

    def test_leaving_the_stage_stands_the_card(self):
        uid = self.hand[0]["uid"]
        self.play(uid, "C1")
        game.apply(self.state, 1, {"type": "position", "uid": uid, "pos": "reverse"})
        self.play(uid, "waiting")
        self.assertEqual(zones(self.state, 1)["waiting"][0]["pos"], "stand")

    def test_damage_trigger_pay_and_refresh(self):
        z = zones(self.state, 1)
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "clock", "count": 2})
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "stock", "count": 3})
        game.apply(self.state, 1, {"type": "move_top", "from": "stock", "to": "waiting", "count": 2})
        self.assertEqual((len(z["clock"]), len(z["stock"]), len(z["waiting"]), len(z["deck"])), (2, 1, 2, 10))
        game.apply(self.state, 1, {"type": "move_all", "from": "waiting", "to": "deck"})
        self.assertEqual((len(z["waiting"]), len(z["deck"])), (0, 12))

    def test_search_reveals_deck_to_owner_and_lets_them_take_a_card(self):
        extra = game.apply(self.state, 1, {"type": "search"})
        revealed = extra["revealed"]["cards"]
        self.assertEqual(len(revealed), 15)
        self.play(revealed[3]["uid"], "hand")
        self.assertEqual(len(zones(self.state, 1)["hand"]), 6)
        self.assertIn("searched their deck", self.state["log"][-2]["text"])

    def test_cannot_touch_opponents_cards_or_overdraw(self):
        opponent_card = zones(self.state, 2)["hand"][0]["uid"]
        with self.assertRaises(game.GameError):
            self.play(opponent_card, "waiting")
        with self.assertRaises(game.GameError):
            game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "hand", "count": 16})
        with self.assertRaises(game.GameError):
            game.apply(self.state, 3, {"type": "stand_all"})
        with self.assertRaises(game.GameError):
            game.apply(self.state, 1, {"type": "move", "uid": self.hand[0]["uid"], "to": "nowhere"})

    def test_ending_the_turn_clears_your_climax_zone(self):
        self.play(self.hand[0]["uid"], "climax")
        game.apply(self.state, 2, {"type": "move", "uid": zones(self.state, 2)["hand"][0]["uid"], "to": "climax"})
        game.apply(self.state, 1, {"type": "end_turn"})
        self.assertEqual(zones(self.state, 1)["climax"], [])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [20])
        self.assertEqual(len(zones(self.state, 2)["climax"]), 1)  # only the player whose turn ended
        self.assertIn("climax zone into the waiting room", self.state["log"][-2]["text"])

    def test_turns_alternate(self):
        with self.assertRaises(game.GameError):
            game.apply(self.state, 2, {"type": "end_turn"})
        game.apply(self.state, 1, {"type": "end_turn"})
        self.assertEqual((self.state["turn"], self.state["turn_number"]), ("2", 2))
        self.assertTrue(game.view(self.state, 2)["my_turn"])


class RoomFlowTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name=WEISS_GROUP)
        self.host = User.objects.create_user("alice", password="x", is_staff=True)
        self.guest = User.objects.create_user("bob", password="x")
        self.guest.groups.add(group)
        self.stranger = User.objects.create_user("eve", password="x")
        self.stranger.groups.add(group)
        card = Card.objects.create(serial_number="NIK/S135-E001", name="Elegg", expansion="NIKKE", expansion_id=290)
        self.decks = {}
        for user in (self.host, self.guest):
            deck = CardList.objects.create(user=user, name=f"{user.username} deck")
            CardListEntry.objects.create(card_list=deck, card=card, quantity=20)
            self.decks[user] = deck

    def as_user(self, user):
        self.client.force_login(user)

    def test_invite_join_choose_decks_start_and_play(self):
        self.as_user(self.host)
        self.client.post(reverse("weiss:play_create"))
        room = GameRoom.objects.get()
        page = self.client.get(reverse("weiss:play_room", args=[room.pk]))
        join_url = reverse("weiss:play_join", args=[room.invite_token])
        self.assertContains(page, join_url)
        self.client.post(reverse("weiss:play_deck", args=[room.pk]), {"deck": self.decks[self.host].pk})

        self.as_user(self.guest)
        self.assertRedirects(self.client.get(join_url), reverse("weiss:play_room", args=[room.pk]))
        self.client.post(reverse("weiss:play_deck", args=[room.pk]), {"deck": self.decks[self.guest].pk})
        # Only the host starts.
        self.assertEqual(self.client.post(reverse("weiss:play_start", args=[room.pk])).status_code, 403)

        self.as_user(self.host)
        self.client.post(reverse("weiss:play_start", args=[room.pk]))
        room.refresh_from_db()
        self.assertEqual(room.status, "playing")

        state_url = reverse("weiss:play_state", args=[room.pk])
        data = self.client.get(state_url).json()
        self.assertEqual(len(data["board"]["me"]["zones"]["hand"]), 5)
        self.assertEqual(data["board"]["opponent"]["zones"]["hand"], {"count": 5})
        self.assertEqual(data["cards"][str(Card.objects.get().pk)]["name"], "Elegg")
        # Nothing changed since that version: cheap 204.
        self.assertEqual(self.client.get(state_url, {"v": data["version"]}).status_code, 204)

        uid = data["board"]["me"]["zones"]["hand"][0]["uid"]
        response = self.client.post(reverse("weiss:play_action", args=[room.pk]),
                                    json.dumps({"type": "move", "uid": uid, "to": "C2"}), content_type="application/json")
        self.assertEqual(response.json()["board"]["me"]["stage"]["C2"]["uid"], uid)

        # The guest sees it on their next poll.
        self.as_user(self.guest)
        guest_view = self.client.get(state_url, {"v": data["version"]}).json()
        self.assertEqual(guest_view["board"]["opponent"]["stage"]["C2"]["uid"], uid)

    def test_room_is_private_and_seats_are_limited_to_two(self):
        room = GameRoom.objects.create(host=self.host, guest=self.guest)
        self.as_user(self.stranger)
        self.assertEqual(self.client.get(reverse("weiss:play_room", args=[room.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("weiss:play_state", args=[room.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("weiss:play_join", args=[room.invite_token])).status_code, 403)
        room.refresh_from_db()
        self.assertEqual(room.guest, self.guest)

    def test_bad_action_returns_error_with_board(self):
        room = GameRoom.objects.create(host=self.host, guest=self.guest, status="playing",
                                       state=game.new_game([(self.host.pk, "alice", [1] * 10),
                                                            (self.guest.pk, "bob", [1] * 10)]))
        self.as_user(self.host)
        response = self.client.post(reverse("weiss:play_action", args=[room.pk]),
                                    json.dumps({"type": "end_turn"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("weiss:play_action", args=[room.pk]),
                                    json.dumps({"type": "end_turn"}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("isn't your turn", response.json()["error"])
        self.assertIn("board", response.json())
