import json

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.access import WEISS_GROUP

from . import game
from .models import Card, CardList, CardListEntry, GameRoom


def no_shuffle(cards):
    pass


def started(deck_a=range(1, 21), deck_b=range(101, 121), mulligan=False):
    """A new game, past the mulligan (into alice's stand phase) unless `mulligan`."""
    state = game.new_game([(1, "alice", list(deck_a)), (2, "bob", list(deck_b))], shuffle=no_shuffle)
    if not mulligan:
        state["phase"] = "stand"
    return state


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

    def test_attack_rests_and_trigger_checks(self):
        self.state["rules"] = False  # the free-form attack; see AttackStepTests for the rules' steps
        uid = self.hand[0]["uid"]
        self.play(uid, "C2")
        game.apply(self.state, 1, {"type": "attack", "uid": uid},
                   name=lambda pk: f"Card{pk}", trigger=lambda pk: "soul" if pk == 15 else "")
        self.assertEqual(self.state["players"]["1"]["stage"]["C2"]["pos"], "rest")
        self.assertEqual([c["card"] for c in zones(self.state, 1)["resolution"]], [15])
        self.assertEqual(self.state["log"][-1]["text"], "attacked with Card20 — trigger check: Card15 [soul]")
        with self.assertRaises(game.GameError):  # already rested
            game.apply(self.state, 1, {"type": "attack", "uid": uid})
        back = self.hand[0]["uid"]
        self.play(back, "B1")
        with self.assertRaises(game.GameError):  # back stage can't attack
            game.apply(self.state, 1, {"type": "attack", "uid": back})

    def test_deck_bottom_card_to_waiting_room(self):
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "waiting", "where": "bottom"},
                   name=lambda pk: f"Card{pk}")
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [1])
        self.assertEqual(zones(self.state, 1)["deck"][-1]["card"], 15)  # the top is untouched
        self.assertEqual(self.state["log"][-1]["text"], "put the bottom 1 of their deck into waiting room: Card1")

    def test_encore_pays_three_stock_and_rests_a_reversed_character(self):
        uid = self.hand[0]["uid"]
        self.play(uid, "C1")
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "stock", "count": 2})
        with self.assertRaises(game.GameError):  # not reversed
            game.apply(self.state, 1, {"type": "encore", "uid": uid})
        game.apply(self.state, 1, {"type": "position", "uid": uid, "pos": "reverse"})
        with self.assertRaises(game.GameError):  # only 2 stock
            game.apply(self.state, 1, {"type": "encore", "uid": uid})
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "stock"})
        game.apply(self.state, 1, {"type": "encore", "uid": uid}, name=lambda pk: f"Card{pk}")
        self.assertEqual(self.state["players"]["1"]["stage"]["C1"]["pos"], "rest")
        self.assertEqual(zones(self.state, 1)["stock"], [])
        self.assertEqual(len(zones(self.state, 1)["waiting"]), 3)
        self.assertEqual(self.state["log"][-1]["text"], "encored Card20 (paid 3 stock)")

    def test_an_empty_deck_refreshes_from_the_waiting_room_at_once_and_takes_one_damage(self):
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "waiting", "count": 15},
                   shuffle=no_shuffle, name=lambda pk: f"Card{pk}")
        self.assertEqual(zones(self.state, 1)["waiting"], [])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [1])
        self.assertEqual(len(zones(self.state, 1)["deck"]), 14)
        self.assertIn("decked out", self.state["log"][-1]["text"])

    def test_turns_alternate(self):
        with self.assertRaises(game.GameError):
            game.apply(self.state, 2, {"type": "end_turn"})
        game.apply(self.state, 1, {"type": "end_turn"})
        self.assertEqual((self.state["turn"], self.state["turn_number"]), ("2", 2))
        self.assertTrue(game.view(self.state, 2)["my_turn"])


class MarkerTests(TestCase):
    def setUp(self):
        self.state = started()
        self.hand = zones(self.state, 1)["hand"]  # cards 20, 19, 18, 17, 16
        game.apply(self.state, 1, {"type": "move", "uid": self.hand[0]["uid"], "to": "C1"})  # 20 on C1

    def markers(self, slot, player=1):
        return [c["card"] for c in self.state["players"][str(player)]["markers"][slot]]

    def test_markers_face_up_or_down_and_hidden_from_opponent_when_down(self):
        game.apply(self.state, 1, {"type": "move", "uid": self.hand[0]["uid"], "to": "marker:C1"})
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "marker:C1", "face_down": True})
        self.assertEqual(self.markers("C1"), [19, 15])
        opponent_view = game.view(self.state, 2)["opponent"]["markers"]["C1"]
        self.assertEqual([c["card"] for c in opponent_view], [19, None])
        self.assertEqual([c["card"] for c in game.view(self.state, 1)["me"]["markers"]["C1"]], [19, 15])
        self.assertIn("markers under center stage (left)", self.state["log"][-1]["text"])

    def test_marker_needs_a_character(self):
        with self.assertRaises(game.GameError):
            game.apply(self.state, 1, {"type": "move", "uid": self.hand[0]["uid"], "to": "marker:C2"})
        character = self.state["players"]["1"]["stage"]["C1"]["uid"]
        with self.assertRaises(game.GameError):  # not under itself
            game.apply(self.state, 1, {"type": "move", "uid": character, "to": "marker:C1"})
        self.assertIsNotNone(self.state["players"]["1"]["stage"]["C1"])  # nothing moved

    def test_markers_follow_the_character_and_go_to_waiting_room_when_it_leaves(self):
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "marker:C1", "face_down": True})
        character = self.state["players"]["1"]["stage"]["C1"]["uid"]
        game.apply(self.state, 1, {"type": "move", "uid": character, "to": "C3"})
        self.assertEqual((self.markers("C1"), self.markers("C3")), ([], [15]))
        game.apply(self.state, 1, {"type": "move", "uid": character, "to": "waiting"})
        self.assertEqual(self.markers("C3"), [])
        waiting = zones(self.state, 1)["waiting"]
        self.assertEqual([c["card"] for c in waiting], [20, 15])  # the character, then its marker
        self.assertFalse(waiting[1]["face_down"])

    def test_marker_pile_works_like_other_piles(self):
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "marker:C1", "count": 2})
        marker = self.state["players"]["1"]["markers"]["C1"][0]
        game.apply(self.state, 1, {"type": "flip", "uid": marker["uid"]})
        self.assertTrue(marker["face_down"])
        game.apply(self.state, 1, {"type": "move", "uid": marker["uid"], "to": "hand"})
        game.apply(self.state, 1, {"type": "move_all", "from": "marker:C1", "to": "stock"})
        self.assertEqual(self.markers("C1"), [])
        self.assertEqual(len(zones(self.state, 1)["stock"]), 1)

    def test_old_games_without_markers_still_work(self):
        for side in self.state["players"].values():
            del side["markers"]
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "marker:C1"})
        self.assertEqual(self.markers("C1"), [15])
        self.assertEqual(game.view(self.state, 2)["me"]["markers"]["C1"], [])


class DamageTests(TestCase):
    def setUp(self):
        self.state = started()  # deck top is card 15, then 14, 13, ...

    def damage(self, amount, climaxes=()):
        return game.apply(self.state, 1, {"type": "damage", "count": amount},
                          name=lambda pk: f"Card{pk}", is_climax=lambda pk: pk in climaxes)

    def test_damage_goes_to_the_clock_at_once(self):
        self.damage(3)
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [15, 14, 13])
        self.assertEqual(self.state["log"][-1]["text"], "took 3 damage: Card15, Card14, Card13")
        self.assertFalse(game.view(self.state, 1)["damage_pending"])

    def test_climax_cancels_the_damage_after_the_board_shows_it(self):
        self.damage(4, climaxes={14})
        # Revealing stops at the climax; for now both cards sit in the clock.
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [15, 14])
        self.assertTrue(game.view(self.state, 1)["damage_pending"])
        self.assertFalse(game.view(self.state, 2)["damage_pending"])
        game.apply(self.state, 1, {"type": "resolve_damage"})
        self.assertEqual(zones(self.state, 1)["clock"], [])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [15, 14])
        self.assertEqual(self.state["log"][-1]["text"],
                         "negated 4 damage: revealed the climax Card14 (2 cards to the waiting room)")
        self.assertFalse(game.view(self.state, 1)["damage_pending"])

    def test_any_action_finishes_a_cancelled_damage_first(self):
        self.damage(2, climaxes={15})
        game.apply(self.state, 2, {"type": "chat", "text": "nice"})
        self.assertEqual(zones(self.state, 1)["clock"], [])
        self.assertIn("negated 2 damage", self.state["log"][-2]["text"])

    def test_damage_limits(self):
        with self.assertRaises(game.GameError):
            self.damage(0)
        zones(self.state, 1)["deck"][:] = zones(self.state, 1)["deck"][-2:]
        self.damage(5)
        self.assertIn("deck ran out after 2", self.state["log"][-1]["text"])


    def empty_deck_but_two(self):
        """Deck: 14, 15 (15 on top). Waiting room: 1..13, which a refresh (unshuffled) puts 13 on top."""
        deck = zones(self.state, 1)["deck"]
        zones(self.state, 1)["waiting"][:] = deck[:-2]
        deck[:] = deck[-2:]

    def continue_damage(self, climaxes=()):
        return game.apply(self.state, 1, {"type": "continue_damage"}, shuffle=no_shuffle,
                          name=lambda pk: f"Card{pk}", is_climax=lambda pk: pk in climaxes)

    def test_running_out_mid_damage_refreshes_then_finishes_the_damage(self):
        self.empty_deck_but_two()
        self.damage(4)
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [15, 14])
        self.assertTrue(game.view(self.state, 1)["refresh_pending"])
        self.assertFalse(game.view(self.state, 2)["refresh_pending"])
        self.continue_damage()
        self.assertFalse(game.view(self.state, 1)["refresh_pending"])
        # 13 is the refresh card, then the last 2 damage.
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [15, 14, 13, 12, 11])
        log = [entry["text"] for entry in self.state["log"][-3:]]
        self.assertIn("2 damage will remain", log[0])
        self.assertTrue(self.state["log"][-3]["chat"])
        self.assertIn("decked out", log[1])
        self.assertEqual(log[2], "took 4 damage: Card15, Card14, Card12, Card11")

    def test_climax_after_a_refresh_cancels_the_damage_but_keeps_the_refresh_card(self):
        self.empty_deck_but_two()
        self.damage(4, climaxes={12})
        self.continue_damage(climaxes={12})
        game.apply(self.state, 1, {"type": "resolve_damage"})
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [13])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [15, 14, 12])
        self.assertIn("negated 4 damage", self.state["log"][-1]["text"])

    def test_any_action_finishes_a_damage_waiting_on_a_refresh(self):
        self.empty_deck_but_two()
        self.damage(3)
        game.apply(self.state, 2, {"type": "chat", "text": "ouch"}, shuffle=no_shuffle)
        self.assertNotIn("pending_refresh", self.state)
        self.assertEqual(len(zones(self.state, 1)["clock"]), 4)  # 2 damage, the refresh card, 1 damage

    def test_no_refresh_when_the_waiting_room_is_empty_too(self):
        zones(self.state, 1)["deck"][:] = zones(self.state, 1)["deck"][-2:]
        self.damage(5)
        self.assertNotIn("pending_refresh", self.state)
        self.assertIn("deck ran out after 2", self.state["log"][-1]["text"])

    def test_damage_that_empties_the_deck_on_its_last_card_refreshes_after(self):
        self.empty_deck_but_two()
        game.apply(self.state, 1, {"type": "damage", "count": 2}, shuffle=no_shuffle, name=lambda pk: f"Card{pk}")
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [15, 14, 13])
        self.assertIn("decked out", self.state["log"][-1]["text"])

    def test_a_climax_on_the_last_card_resolves_before_the_refresh(self):
        self.empty_deck_but_two()
        self.damage(2, climaxes={14})
        self.assertEqual(zones(self.state, 1)["deck"], [])  # still showing the cancelled damage
        game.apply(self.state, 1, {"type": "resolve_damage"}, shuffle=no_shuffle, name=lambda pk: f"Card{pk}")
        # 15 and 14 went to the waiting room first, so they're in the new deck: 14 on top is the refresh card.
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [14])
        self.assertEqual(len(zones(self.state, 1)["deck"]), 14)


class ClockAndLevelTests(TestCase):
    def setUp(self):
        self.state = started()  # hand 20..16, deck top is 15, then 14, ...

    def test_clock_a_hand_card_and_draw_two(self):
        uid = zones(self.state, 1)["hand"][0]["uid"]
        game.apply(self.state, 1, {"type": "clock_draw", "uid": uid}, name=lambda pk: f"Card{pk}")
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [20])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["hand"]], [19, 18, 17, 16, 15, 14])
        self.assertEqual(self.state["log"][-1]["text"], "put Card20 into their clock and drew 2 cards")

    def test_clock_draw_refreshes_between_the_two_draws(self):
        deck = zones(self.state, 1)["deck"]
        zones(self.state, 1)["waiting"][:] = deck[:-1]
        deck[:] = deck[-1:]  # just 15
        game.apply(self.state, 1, {"type": "clock_draw", "uid": zones(self.state, 1)["hand"][0]["uid"]}, shuffle=no_shuffle)
        self.assertEqual([c["card"] for c in zones(self.state, 1)["hand"]][-2:], [15, 13])  # 14 was the refresh card
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [20, 14])
        self.assertEqual(self.state["players"]["1"]["refreshes"], 1)

    def test_seven_in_the_clock_means_choosing_a_level_card(self):
        game.apply(self.state, 1, {"type": "damage", "count": 8})  # 15..8
        self.assertTrue(game.view(self.state, 1)["level_up_pending"])
        self.assertFalse(game.view(self.state, 2)["level_up_pending"])
        clock = zones(self.state, 1)["clock"]
        with self.assertRaises(game.GameError):  # the 8th card isn't one of the first 7
            game.apply(self.state, 1, {"type": "level_up", "uid": clock[7]["uid"]})
        game.apply(self.state, 1, {"type": "level_up", "uid": clock[2]["uid"]}, name=lambda pk: f"Card{pk}")
        self.assertEqual([c["card"] for c in zones(self.state, 1)["level"]], [13])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["clock"]], [8])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [15, 14, 12, 11, 10, 9])
        self.assertEqual(self.state["log"][-1]["text"], "levelled up to level 1 with Card13")
        self.assertEqual(game.view(self.state, 2)["opponent"]["level_ups"], 1)
        self.assertFalse(game.view(self.state, 1)["level_up_pending"])

    def test_level_up_waits_for_the_damage_to_finish(self):
        game.apply(self.state, 1, {"type": "damage", "count": 6})
        game.apply(self.state, 1, {"type": "damage", "count": 3}, is_climax=lambda pk: pk == 7)  # 9, 8, 7 (climax)
        self.assertEqual(len(zones(self.state, 1)["clock"]), 9)
        self.assertFalse(game.view(self.state, 1)["level_up_pending"])
        with self.assertRaises(game.GameError):  # the cancelled damage is still showing
            game.apply(self.state, 1, {"type": "level_up", "uid": zones(self.state, 1)["clock"][0]["uid"]})
        game.apply(self.state, 1, {"type": "resolve_damage"})
        self.assertFalse(game.view(self.state, 1)["level_up_pending"])  # back to 6


def follow(state, **kwargs):
    """Move the phase on as the turn player's page does when a phase has ended itself."""
    while state.get("auto_next"):
        game.apply(state, state["turn"], {"type": "phase", "phase": state["auto_next"], "auto": True},
                   shuffle=no_shuffle, **kwargs)


class MulliganTests(TestCase):
    def setUp(self):
        self.state = started(mulligan=True)

    def test_both_players_mulligan_then_the_first_turn_begins(self):
        self.assertEqual(game.view(self.state, 1)["phase"], "mulligan")
        hand = zones(self.state, 1)["hand"]  # 20..16; deck top 15
        with self.assertRaises(game.GameError):  # no phases until both are done
            game.apply(self.state, 1, {"type": "phase", "phase": "draw"})
        game.apply(self.state, 1, {"type": "mulligan", "uids": [hand[0]["uid"], hand[2]["uid"]]})
        self.assertEqual([c["card"] for c in zones(self.state, 1)["hand"]], [19, 17, 16, 15, 14])
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [20, 18])
        self.assertEqual(game.view(self.state, 2)["mulligan"], {"me": False, "opponent": True})
        with self.assertRaises(game.GameError):  # once each
            game.apply(self.state, 1, {"type": "mulligan", "uids": []})
        game.apply(self.state, 2, {"type": "mulligan", "uids": []})
        self.assertEqual((self.state["phase"], self.state["auto_next"]), ("stand", "draw"))
        self.assertEqual(self.state["log"][-2]["text"], "kept their hand")


class RevealTests(TestCase):
    def setUp(self):
        self.state = started()

    def test_a_revealed_card_holds_the_turn_until_the_opponent_closes_it(self):
        card = zones(self.state, 1)["hand"][0]
        game.apply(self.state, 1, {"type": "reveal", "uid": card["uid"]}, name=lambda pk: f"Card{pk}")
        bob = game.view(self.state, 2)
        self.assertEqual(bob["reveal"], {"card": 20, "by": "alice"})
        self.assertIn(20, game.visible_cards(bob))
        self.assertEqual(game.view(self.state, 1)["reveal"], {"mine": True})
        with self.assertRaises(game.GameError):
            game.apply(self.state, 1, {"type": "phase", "phase": "draw"})
        with self.assertRaises(game.GameError):  # only the opponent closes it
            game.apply(self.state, 1, {"type": "close_reveal"})
        game.apply(self.state, 2, {"type": "close_reveal"})
        game.apply(self.state, 1, {"type": "phase", "phase": "draw"})
        self.assertEqual(self.state["phase"], "draw")


class PhaseTests(TestCase):
    def setUp(self):
        self.state = started()  # alice's turn, stand phase; hand 20..16, deck top 15

    def phase(self, phase, player=1):
        game.apply(self.state, player, {"type": "phase", "phase": phase}, shuffle=no_shuffle)

    def test_a_game_starts_in_the_first_players_stand_phase(self):
        self.assertEqual(game.view(self.state, 1)["phase"], "stand")

    def test_moving_past_the_draw_phase_draws_its_card(self):
        self.phase("clock")
        self.assertEqual(zones(self.state, 1)["hand"][-1]["card"], 15)

    def test_skipping_ahead_still_does_the_steps_passed_through(self):
        self.phase("main")
        self.assertEqual(len(zones(self.state, 1)["hand"]), 6)  # drew on the way through the draw phase
        self.assertEqual(self.state["phase"], "main")
        with self.assertRaises(game.GameError):  # no going back
            self.phase("clock")
        with self.assertRaises(game.GameError):  # only the turn player moves the phase on
            self.phase("climax", player=2)

    def test_the_end_phase_passes_the_turn_into_the_next_stand_phase(self):
        bob = self.state["players"]["2"]
        card = zones(self.state, 2)["hand"][0]
        game.apply(self.state, 2, {"type": "move", "uid": card["uid"], "to": "C1"})
        game.apply(self.state, 2, {"type": "position", "uid": card["uid"], "pos": "rest"})
        self.phase("end")
        self.assertEqual((self.state["turn"], self.state["phase"], self.state["turn_number"]), ("2", "stand", 2))
        self.assertEqual(bob["stage"]["C1"]["pos"], "stand")  # bob's stand phase stood it
        self.assertEqual(self.state["log"][-1]["text"], "stand phase: stood all their characters")
        self.assertEqual(game.view(self.state, 2)["auto_next"], "draw")  # then bob's page moves on
        follow(self.state)
        self.assertEqual((self.state["phase"], len(zones(self.state, 2)["hand"])), ("clock", 5))  # 4 + the draw

    def test_a_stale_automatic_phase_change_is_dropped(self):
        game.apply(self.state, 1, {"type": "stand_all"})
        self.phase("main")  # the player moved on by hand first
        game.apply(self.state, 1, {"type": "phase", "phase": "draw", "auto": True})
        self.assertEqual(self.state["phase"], "main")


    def test_the_draw_phase_draws_and_ends_itself(self):
        self.phase("draw")
        self.assertEqual(zones(self.state, 1)["hand"][-1]["card"], 15)
        self.assertEqual((self.state["phase"], self.state["auto_next"]), ("draw", "clock"))

    def test_standing_all_in_the_stand_phase_ends_it(self):
        game.apply(self.state, 1, {"type": "stand_all"})
        self.assertEqual(self.state["auto_next"], "draw")

    def test_the_encore_step_ends_itself_without_reversed_characters(self):
        self.phase("encore")
        self.assertEqual(self.state["auto_next"], "end")
        follow(self.state)
        self.assertEqual(self.state["turn"], "2")

    def test_only_one_attack_on_the_first_turn(self):
        a, b = zones(self.state, 1)["hand"][0], zones(self.state, 1)["hand"][1]
        game.apply(self.state, 1, {"type": "move", "uid": a["uid"], "to": "C1"})
        game.apply(self.state, 1, {"type": "move", "uid": b["uid"], "to": "C2"})
        self.phase("attack")
        game.apply(self.state, 1, {"type": "attack", "uid": a["uid"], "kind": "direct"})
        # No attacks left on turn 1, so the attack phase ends itself (then the encore step, and the turn).
        self.assertEqual(self.state["auto_next"], "encore")
        self.assertEqual(self.state["players"]["1"]["stage"]["C2"]["pos"], "stand")
        follow(self.state)
        self.assertEqual(self.state["turn"], "2")

    def test_clocking_to_draw_ends_the_clock_phase(self):
        self.phase("clock")
        game.apply(self.state, 1, {"type": "clock_draw", "uid": zones(self.state, 1)["hand"][0]["uid"]})
        self.assertEqual(self.state["auto_next"], "main")

    def test_a_climax_played_in_the_climax_phase_waits_then_the_page_moves_to_attack(self):
        self.phase("climax")
        uid = zones(self.state, 1)["hand"][0]["uid"]
        game.apply(self.state, 1, {"type": "move", "uid": uid, "to": "climax"})
        self.assertTrue(game.view(self.state, 1)["climax_pending"])
        self.assertFalse(game.view(self.state, 2)["climax_pending"])
        self.assertEqual(game.view(self.state, 2)["opponent"]["climaxes"], 1)
        self.phase("attack")
        self.assertFalse(game.view(self.state, 1)["climax_pending"])

    def test_a_climax_played_from_the_main_phase_ends_it(self):
        self.phase("main")
        uid = zones(self.state, 1)["hand"][0]["uid"]
        game.apply(self.state, 1, {"type": "move", "uid": uid, "to": "climax", "end_main": True})
        self.assertEqual(self.state["phase"], "climax")
        self.assertTrue(game.view(self.state, 1)["climax_pending"])  # then on to the attack phase

    def test_the_encore_step_waits_for_every_reversed_character(self):
        mine, theirs = zones(self.state, 1)["hand"][0], zones(self.state, 2)["hand"][0]
        for player, card in ((1, mine), (2, theirs)):
            game.apply(self.state, player, {"type": "move", "uid": card["uid"], "to": "C1"})
            game.apply(self.state, player, {"type": "position", "uid": card["uid"], "pos": "reverse"})
        self.phase("end")  # stops at the encore step
        self.assertEqual((self.state["phase"], self.state["turn"]), ("encore", "1"))
        with self.assertRaises(game.GameError):
            self.phase("end")
        game.apply(self.state, 1, {"type": "move", "uid": mine["uid"], "to": "waiting"})
        with self.assertRaises(game.GameError):  # bob's is still reversed
            self.phase("end")
        game.apply(self.state, 2, {"type": "move_top", "from": "deck", "to": "stock", "count": 3})
        game.apply(self.state, 2, {"type": "encore", "uid": theirs["uid"]})
        self.assertEqual(self.state["auto_next"], "end")  # the last choice ended the encore step


CARDS = {
    16: {"card_type": "Character", "level": 0},  # in alice's waiting room for the trigger tests
    20: {"power": 5000, "soul": 1, "level": 0},   # alice's attacker
    19: {"power": 3000, "soul": 2, "level": 0},
    101: {"power": 3000, "soul": 1, "level": 1},  # bob's defender
    120: {"power": 1000, "level": 0, "text": "【ACT】 【COUNTER】 Backup 3000, Level 0 [(0) Put this card into your waiting room]"},
}


class AttackStepTests(TestCase):
    def setUp(self):
        self.state = started()  # alice: hand 20..16, deck top 15; bob: hand 120..116
        self.alice = zones(self.state, 1)["hand"]
        self.bob = zones(self.state, 2)["hand"]

    def act(self, player, action, **kwargs):
        return game.apply(self.state, player, action, shuffle=no_shuffle, name=lambda pk: f"Card{pk}",
                          info=lambda pk: CARDS.get(pk, {}), **kwargs)

    def stage(self, player, slot):
        return self.state["players"][str(player)]["stage"][slot]

    def setup_battle(self, defender=True):
        self.act(1, {"type": "move", "uid": self.alice[0]["uid"], "to": "C2"})  # card 20
        if defender:
            self.state["turn"] = "2"
            self.act(2, {"type": "move", "uid": self.bob[1]["uid"], "to": "C2"})  # card 119, then make it 101
            self.stage(2, "C2")["card"] = 101
            self.state["turn"] = "1"
        self.act(1, {"type": "phase", "phase": "attack"})
        self.assertEqual(self.state["attack"], {"step": "declare"})

    def test_a_direct_attack_deals_soul_plus_one(self):
        self.setup_battle(defender=False)
        with self.assertRaises(game.GameError):  # nothing in front of it: direct only
            self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "front"})
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "direct"})
        self.assertEqual(len(zones(self.state, 2)["clock"]), 2)  # soul 1, +1 direct
        self.assertEqual([c["card"] for c in zones(self.state, 1)["stock"]], [14])  # the trigger card (15 was drawn)
        self.assertEqual(self.state["auto_next"], "encore")  # no attacks left

    def test_a_front_attack_with_a_backup_counter(self):
        self.setup_battle()
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "front"})
        self.assertEqual(game.view(self.state, 2)["attack"]["step"], "counter")
        self.assertEqual(game.view(self.state, 2)["attack"]["counters"], [self.bob[0]["uid"]])
        with self.assertRaises(game.GameError):  # mid-attack, the turn can't move on
            self.act(1, {"type": "phase", "phase": "encore"})
        self.act(2, {"type": "counter", "uid": self.bob[0]["uid"]})
        # Damage 1, then the battle: 5000 against 3000 + 3000 backup reverses the attacker.
        self.assertEqual(len(zones(self.state, 2)["clock"]), 1)
        self.assertEqual(self.stage(1, "C2")["pos"], "reverse")
        self.assertEqual(self.stage(2, "C2")["pos"], "stand")
        self.assertTrue(any("battle: Card20 (5000) against Card101 (6000)" in e["text"] for e in self.state["log"]))
        # No attacks left; the encore step then waits for alice's reversed character.
        follow(self.state)
        self.assertEqual((self.state["phase"], self.state["turn"]), ("encore", "1"))

    def test_a_front_attack_without_a_counter_reverses_the_weaker_defender(self):
        self.setup_battle()
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "front"})
        self.act(2, {"type": "no_counter"})
        self.assertEqual(self.stage(2, "C2")["pos"], "reverse")
        follow(self.state)
        self.assertEqual(self.state["phase"], "encore")  # bob's reversed character holds the encore step

    def test_a_side_attack_loses_soul_for_the_defenders_level_and_has_no_battle(self):
        self.setup_battle()
        self.stage(1, "C2")["card"] = 19  # soul 2, against a level 1 defender: 1 damage
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "side"})
        self.act(2, {"type": "no_counter"})
        self.assertEqual(len(zones(self.state, 2)["clock"]), 1)
        self.assertEqual(self.stage(2, "C2")["pos"], "stand")

    def test_a_comeback_trigger_asks_the_attacker_for_a_character(self):
        self.setup_battle(defender=False)
        self.act(1, {"type": "move", "uid": next(c["uid"] for c in self.alice if c["card"] == 16), "to": "waiting"})
        waiting_uid = zones(self.state, 1)["waiting"][-1]["uid"]
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "direct"},
                 trigger=lambda pk: "comeback" if pk == 14 else "")
        attack = game.view(self.state, 1)["attack"]
        self.assertEqual((attack["step"], attack["prompt"]), ("trigger", {"kind": "comeback", "options": [waiting_uid]}))
        self.assertEqual(zones(self.state, 2)["clock"], [])  # damage waits for the choice
        with self.assertRaises(game.GameError):  # comeback goes to the hand only
            self.act(1, {"type": "trigger_choice", "uid": waiting_uid, "to": "stock"})
        self.act(1, {"type": "trigger_choice", "uid": waiting_uid, "to": "hand"})
        self.assertEqual(zones(self.state, 1)["hand"][-1]["uid"], waiting_uid)
        self.assertEqual(len(zones(self.state, 2)["clock"]), 2)

    def test_a_standby_trigger_puts_a_character_on_the_stage_rested(self):
        self.setup_battle(defender=False)
        self.act(1, {"type": "move", "uid": next(c["uid"] for c in self.alice if c["card"] == 16), "to": "waiting"})
        waiting_uid = zones(self.state, 1)["waiting"][-1]["uid"]
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "direct"},
                 trigger=lambda pk: "soul standby" if pk == 14 else "")
        self.act(1, {"type": "trigger_choice", "uid": waiting_uid, "to": "B1"})
        self.assertEqual((self.stage(1, "B1")["uid"], self.stage(1, "B1")["pos"]), (waiting_uid, "rest"))
        self.assertEqual(len(zones(self.state, 2)["clock"]), 3)  # soul 1, +1 direct, +1 trigger soul

    def test_a_treasure_trigger_offers_the_top_card_to_the_stock(self):
        self.setup_battle(defender=False)
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "direct"},
                 trigger=lambda pk: "treasure" if pk == 14 else "")
        self.assertEqual(zones(self.state, 1)["hand"][-1]["card"], 14)  # the treasure card itself
        self.act(1, {"type": "trigger_choice", "accept": True})
        self.assertEqual([c["card"] for c in zones(self.state, 1)["stock"]], [13])

    def test_a_shot_trigger_deals_one_more_when_the_damage_is_cancelled(self):
        self.setup_battle(defender=False)
        climax = {"is_climax": lambda pk: pk == 115}
        self.act(1, {"type": "attack", "uid": self.stage(1, "C2")["uid"], "kind": "direct"},
                 trigger=lambda pk: "soul shot" if pk == 14 else "", **climax)
        self.assertTrue(game.view(self.state, 2)["damage_pending"])  # 115, the first card, cancelled it
        self.act(2, {"type": "resolve_damage"}, **climax)
        self.assertEqual([c["card"] for c in zones(self.state, 2)["clock"]], [114])
        self.assertTrue(any("shot trigger" in e["text"] for e in self.state["log"]))

    def test_turn_rules_change_only_when_both_agree(self):
        self.act(2, {"type": "rules_request"})
        self.assertEqual(game.view(self.state, 1)["rules_request"], {"mine": False, "on": False})
        self.act(1, {"type": "rules_answer", "accept": False})
        self.assertTrue(game.view(self.state, 1)["rules"])
        self.act(2, {"type": "rules_request"})
        self.act(1, {"type": "rules_answer", "accept": True})
        self.assertFalse(game.view(self.state, 2)["rules"])
        # With the rules off, playing a card is free and attacks need no phase.
        self.act(1, {"type": "move", "uid": self.alice[0]["uid"], "to": "C1"})
        self.act(1, {"type": "attack", "uid": self.stage(1, "C1")["uid"]})
        self.assertEqual([c["card"] for c in zones(self.state, 1)["resolution"]], [15])


class CostTests(TestCase):
    def setUp(self):
        self.state = started()
        self.hand = zones(self.state, 1)["hand"]  # 20..16

    def play(self, uid, to):
        game.apply(self.state, 1, {"type": "move", "uid": uid, "to": to},
                   cost=lambda pk: 2 if pk == 20 else 0, name=lambda pk: f"Card{pk}")

    def test_playing_a_card_pays_its_cost_from_the_stock(self):
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "stock", "count": 3})
        self.play(self.hand[0]["uid"], "C2")
        self.assertEqual(len(zones(self.state, 1)["stock"]), 1)
        self.assertEqual(len(zones(self.state, 1)["waiting"]), 2)
        self.assertIn("(paid 2 stock)", self.state["log"][-1]["text"])

    def test_cant_play_a_card_without_the_stock_for_it(self):
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "stock"})
        uid = self.hand[0]["uid"]
        with self.assertRaises(game.GameError):
            self.play(uid, "C2")
        self.assertEqual(self.hand[0]["uid"], uid)  # still in the hand
        self.play(uid, "waiting")  # other moves are free
        self.assertEqual(len(zones(self.state, 1)["stock"]), 1)


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

        # Once a game is going, either player can call a rematch or go back to changing decks.
        self.client.post(reverse("weiss:play_start", args=[room.pk]))
        room.refresh_from_db()
        self.assertEqual((room.status, room.state["turn_number"]), ("playing", 1))
        self.assertIsNone(room.state["players"][str(self.host.pk)]["stage"]["C2"])
        self.client.post(reverse("weiss:play_reset", args=[room.pk]))
        room.refresh_from_db()
        self.assertEqual(room.status, "setup")
        # ...but only the host starts from setup.
        self.assertEqual(self.client.post(reverse("weiss:play_start", args=[room.pk])).status_code, 403)

    def test_room_is_private_and_seats_are_limited_to_two(self):
        room = GameRoom.objects.create(host=self.host, guest=self.guest)
        self.as_user(self.stranger)
        self.assertEqual(self.client.get(reverse("weiss:play_room", args=[room.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("weiss:play_state", args=[room.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("weiss:play_join", args=[room.invite_token])).status_code, 403)
        room.refresh_from_db()
        self.assertEqual(room.guest, self.guest)

    def test_damage_through_the_room_spots_climaxes_by_card_type(self):
        climax = Card.objects.create(serial_number="NIK/S135-E099", name="Victory", card_type="Climax",
                                     expansion="NIKKE", expansion_id=290)
        room = GameRoom.objects.create(host=self.host, guest=self.guest, status="playing",
                                       state=game.new_game([(self.host.pk, "alice", [climax.pk] * 10),
                                                            (self.guest.pk, "bob", [climax.pk] * 10)]))
        self.as_user(self.host)
        url = reverse("weiss:play_action", args=[room.pk])
        data = self.client.post(url, json.dumps({"type": "damage", "count": 3}), content_type="application/json").json()
        self.assertTrue(data["board"]["damage_pending"])
        data = self.client.post(url, json.dumps({"type": "resolve_damage"}), content_type="application/json").json()
        self.assertEqual(data["board"]["me"]["zones"]["clock"], [])
        self.assertIn("negated 3 damage: revealed the climax Victory", data["board"]["log"][-1]["text"])

    def test_bad_action_returns_error_with_board(self):
        state = game.new_game([(self.host.pk, "alice", [1] * 10), (self.guest.pk, "bob", [1] * 10)])
        state["phase"] = "stand"  # past the mulligan
        room = GameRoom.objects.create(host=self.host, guest=self.guest, status="playing", state=state)
        self.as_user(self.host)
        response = self.client.post(reverse("weiss:play_action", args=[room.pk]),
                                    json.dumps({"type": "end_turn"}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("weiss:play_action", args=[room.pk]),
                                    json.dumps({"type": "end_turn"}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("isn't your turn", response.json()["error"])
        self.assertIn("board", response.json())
