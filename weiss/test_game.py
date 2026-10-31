import json

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.access import WEISS_GROUP

from . import abilities, game
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
        self.assertIn("deck ran out after 2", self.state["log"][-2]["text"])


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
        self.assertIn("deck ran out after 2", self.state["log"][-2]["text"])
        self.assertEqual(self.state["game_over"]["reason"], "deck")  # and that's the game

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
        game.apply(self.state, 1, {"type": "ability_show_done", "id": self.state["ability_show"]["id"]})  # the trigger check
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

    def test_the_end_phase_waits_for_a_hand_over_seven_to_be_discarded(self):
        game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "hand", "count": 3})  # 8 cards
        self.phase("end")  # passes the draw phase too: 9 cards
        self.assertEqual((self.state["phase"], self.state["turn"]), ("end", "1"))
        self.assertEqual(game.view(self.state, 1)["discard"], {"count": 2, "mine": True})
        self.assertEqual(game.view(self.state, 2)["discard"], {"count": 2, "mine": False})
        hand = zones(self.state, 1)["hand"]
        with self.assertRaises(game.GameError):  # exactly 2
            game.apply(self.state, 1, {"type": "discard", "uids": [hand[0]["uid"]]})
        game.apply(self.state, 1, {"type": "discard", "uids": [hand[0]["uid"], hand[1]["uid"]]})
        self.assertEqual(len(zones(self.state, 1)["hand"]), 7)
        self.assertEqual((self.state["turn"], self.state["phase"]), ("2", "stand"))

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
        common = dict(shuffle=no_shuffle, name=lambda pk: f"Card{pk}", info=lambda pk: CARDS.get(pk, {}), **kwargs)
        extra = game.apply(self.state, player, action, **common)
        if self.state.get("ability_show"):  # the trigger check shows, then a page moves things on
            game.apply(self.state, player, {"type": "ability_show_done", "id": self.state["ability_show"]["id"]}, **common)
        return extra

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
        self.assertIsNotNone(data["board"]["rps"])  # game 1 starts with rock, paper, scissors
        room.refresh_from_db()
        room.state.pop("rps")
        room.save()

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


class AbilityParsingTests(TestCase):
    def only(self, text):
        return abilities.parse(text)[0]

    def test_a_trigger_with_a_choice_and_a_buff(self):
        ability = self.only("【AUTO】 When this card attacks, choose 1 of your 《NIKKE》 characters, and that character gets +1500 power until end of turn.")
        self.assertEqual(ability["when"], [{"on": "attack"}])
        self.assertEqual([s["do"] for s in ability["steps"]], ["choose", "buff"])
        self.assertEqual(ability["steps"][1]["power"], 1500)

    def test_a_cost_is_read_into_its_parts(self):
        ability = self.only("【ACT】 [(1) Put 1 card from your hand into your waiting room & 【REST】 this card] Draw 1 card.")
        self.assertEqual([p["part"] for p in ability["cost"]], ["stock", "pick", "self_rest"])

    def test_quotes_inside_names_and_granted_abilities_dont_confuse_it(self):
        ability = self.only('【AUTO】 [(1)] When this card is placed on the stage from your hand, you may pay the cost. If you do, '
                            'choose 1 ""Glass Slippers. Full Contact" Cinderella" in your waiting room, and return it to your hand.')
        choose = ability["steps"][0]["then"][0]
        self.assertEqual(choose["filter"]["any"][0]["name"], '"Glass Slippers. Full Contact" Cinderella')
        given = self.only('【AUTO】 When this card attacks, this card gets +1000 power and the following ability until end of turn. '
                          '"【AUTO】 When this card\'s battle opponent becomes 【REVERSE】, draw 1 card."')
        self.assertEqual(given["steps"][0]["grant"], ["【AUTO】 When this card's battle opponent becomes 【REVERSE】, draw 1 card."])

    def test_text_it_cant_read_becomes_a_step_done_by_hand(self):
        ability = self.only("【AUTO】 When this card attacks, draw 1 card, and juggle three of your opponent's dice.")
        self.assertEqual([s["do"] for s in ability["steps"]], ["draw", "manual"])
        self.assertIn("juggle", ability["steps"][1]["text"])

    def test_a_trigger_it_cant_read_is_left_for_the_button(self):
        self.assertIsNone(self.only("【AUTO】 When the moon is full, draw 1 card.")["when"])
        self.assertTrue(game.activatable(self.only("【AUTO】 When the moon is full, draw 1 card.")))

    def test_curly_quotes_on_a_card_match_straight_quotes_in_text(self):
        filter_ = abilities.parse_filter("⟦0⟧", ['"First Winner" Bay'])
        self.assertTrue(abilities.matches_filter(filter_, {"name": "“First Winner” Bay"}))

    def test_keywords_with_their_rules_in_the_reminder_text(self):
        encore = self.only("【AUTO】 Encore [Put 1 character from your hand into your waiting room] (When this card is put into your "
                           "waiting room from the stage, you may pay the cost. If you do, return this card to its previous stage position as 【REST】)")
        self.assertEqual(encore["when"], [{"on": "leave"}])
        self.assertEqual(encore["steps"][0]["then"][0]["do"], "to_old_slot")


NIKKE = "NIKKE・Electric Shock"


class AbilityGameTests(TestCase):
    """Alice's hand is 20..16 and her deck's top is 15; bob's hand is 120..116. self.cards gives the details."""

    def setUp(self):
        self.state = started()
        self.state["phase"] = "main"
        self.cards = {}

    def info(self, pk):
        return self.cards.get(pk, {"card_type": "Character", "traits": NIKKE, "power": 1000, "soul": 1, "level": 0, "name": f"Card{pk}"})

    def card(self, pk, text="", **details):
        self.cards[pk] = {"name": f"Card{pk}", "card_type": "Character", "traits": NIKKE, "power": 1000, "soul": 1, "level": 0, "text": text, **details}

    def apply(self, player, action):
        return game.apply(self.state, player, action, shuffle=no_shuffle, name=lambda pk: self.info(pk)["name"], info=self.info,
                          is_climax=lambda pk: (self.info(pk).get("card_type") or "").lower() == "climax",
                          trigger=lambda pk: self.info(pk).get("trigger", ""), cost=lambda pk: self.info(pk).get("cost", 0))

    def act(self, player, action):
        """An action, and then any ability's show plays out as the pages would let it."""
        extra = self.apply(player, action)
        while self.state.get("ability_show"):
            self.last_show = self.state["ability_show"]
            self.apply(player, {"type": "ability_show_done", "id": self.state["ability_show"]["id"]})
        return extra

    def hand(self, player=1):
        return zones(self.state, player)["hand"]

    def uid(self, pk, player=1):
        return next(c["uid"] for c in self.hand(player) if c["card"] == pk)

    def play(self, pk, slot, player=1):
        uid = self.uid(pk, player)
        self.act(player, {"type": "move", "uid": uid, "to": slot})
        return uid

    def seat(self, pk, slot, player=1):
        """Put a character on the stage without playing it, so nothing triggers."""
        card = game.new_card(pk)
        self.state["players"][str(player)]["stage"][slot] = card
        self.act(player, {"type": "chat", "text": "."})  # works out the stats
        return card["uid"]

    def stock(self, count, player=1):
        self.act(player, {"type": "move_top", "from": "deck", "to": "stock", "count": count})

    def stats(self, uid, player=1):
        return game.view(self.state, player)["stats"][uid]

    def ability(self, player=1):
        return game.view(self.state, player)["ability"]

    def trigger(self, accept=True, player=1):
        self.act(player, {"type": "ability_trigger", "id": self.ability(player)["queue"][0]["id"], "accept": accept})

    # Power and soul

    def test_a_climax_boosts_power_and_soul_for_battle_and_damage(self):
        self.card(16, "【CONT】 All of your characters get +1000 power and +1 soul.", card_type="Climax", power=None, soul=None)
        uid = self.seat(50, "C1")
        self.act(1, {"type": "move", "uid": self.uid(16), "to": "climax"})
        self.assertEqual(self.stats(uid), {"power": 2000, "soul": 2})
        self.assertEqual(self.stats(uid, player=2), {"power": 2000, "soul": 2})  # both players see it

    def test_a_character_boost_only_on_its_owners_turn(self):
        self.card(20, "【CONT】 During your turn, this card gets +2000 power.")
        uid = self.play(20, "C1")
        self.assertEqual(self.stats(uid)["power"], 3000)
        self.state["turn"] = "2"
        self.act(1, {"type": "chat", "text": "."})
        self.assertEqual(self.stats(uid)["power"], 1000)

    def test_assist_boosts_only_the_characters_in_front_of_it(self):
        self.card(20, "【CONT】 Assist All of your 《NIKKE》 characters in front of this card get +X power. X is equal to that character's level ×500.")
        self.card(51, level=2)
        self.card(52, level=3)
        self.card(53, level=2, traits="Other")
        in_front = self.seat(51, "C1")
        not_in_front = self.seat(52, "C3")
        wrong_trait = self.seat(53, "C2")
        self.play(20, "B1")
        self.assertEqual(self.stats(in_front)["power"], 2000)
        self.assertEqual(self.stats(not_in_front)["power"], 1000)
        self.assertEqual(self.stats(wrong_trait)["power"], 1000)

    def test_conditional_boosts_count_other_characters(self):
        self.card(20, "【CONT】 If you have 2 or more other 《NIKKE》 characters, this card gets +6000 power.")
        uid = self.play(20, "C1")
        self.seat(50, "C2")
        self.assertEqual(self.stats(uid)["power"], 1000)
        self.seat(51, "C3")
        self.assertEqual(self.stats(uid)["power"], 7000)

    def test_boosts_decide_a_battle(self):
        self.card(20, "【CONT】 During your turn, this card gets +2000 power.")
        self.card(120, power=2500)
        uid = self.play(20, "C2")
        self.seat(120, "C2", player=2)
        self.act(1, {"type": "phase", "phase": "attack"})
        self.act(1, {"type": "attack", "uid": uid, "kind": "front"})
        if self.state["attack"]["step"] == "counter":
            self.act(2, {"type": "no_counter"})
        self.assertEqual(self.state["players"]["2"]["stage"]["C2"]["pos"], "reverse")  # 3000 against 2500
        self.assertEqual(self.state["players"]["1"]["stage"]["C2"]["pos"], "rest")

    # Triggering

    def test_playing_a_card_prompts_and_the_buff_ends_with_the_turn(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, choose 1 of your characters, and that character gets +2000 power until end of turn.")
        other = self.seat(50, "C1")
        self.play(20, "C2")
        self.assertEqual(len(self.ability()["queue"]), 1)
        self.assertEqual(self.ability(player=2), {"resolving": False, "mine": False, "by": "alice"})
        self.trigger()
        prompt = self.ability()["prompt"]
        self.assertEqual(prompt["kind"], "cards")
        self.assertEqual(len(prompt["options"]), 2)
        self.act(1, {"type": "ability_answer", "uids": [other]})
        self.assertIsNone(self.ability())
        self.assertEqual(self.stats(other)["power"], 3000)
        self.act(1, {"type": "phase", "phase": "end"})
        self.assertEqual(self.stats(other, player=1)["power"], 1000)

    def test_a_buff_until_the_opponents_next_turn_lasts_through_it(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, this card gets +1000 power until the end of your opponent's next turn.")
        uid = self.play(20, "C1")
        self.trigger()
        self.act(1, {"type": "phase", "phase": "end"})
        self.assertEqual(self.stats(uid)["power"], 2000)  # bob's turn
        follow(self.state)
        self.act(2, {"type": "phase", "phase": "end"})
        self.assertEqual(self.stats(uid)["power"], 1000)

    def test_no_prompt_when_the_condition_isnt_met(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, if you have 4 or more other 《NIKKE》 characters, draw 1 card.")
        self.play(20, "C1")
        self.assertIsNone(self.ability())

    def test_no_prompt_when_the_cost_cant_be_paid(self):
        self.card(20, "【AUTO】 [(2)] When this card is placed on the stage from your hand, you may pay the cost. If you do, draw 1 card.")
        self.play(20, "C1")
        self.assertIsNone(self.ability())

    def test_triggering_pays_the_cost_and_resolves(self):
        self.card(20, "【AUTO】 [(1) Put 1 card from your hand into your waiting room] When this card is placed on the stage from your hand, you may pay the cost. If you do, draw 1 card.")
        self.stock(2)
        self.play(20, "C1")
        hand_before = len(self.hand())
        self.trigger()
        self.assertEqual(len(zones(self.state, 1)["stock"]), 1)  # the stock is paid straight away
        discard = self.ability()["prompt"]["options"][0]
        self.act(1, {"type": "ability_answer", "uids": [discard]})
        self.assertEqual(len(self.hand()), hand_before)  # one out, one drawn
        self.assertEqual(zones(self.state, 1)["waiting"][-1]["uid"], discard)
        self.assertIsNone(self.ability())

    def test_skipping_does_nothing_and_is_logged(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, draw 1 card.")
        self.play(20, "C1")
        hand_before = len(self.hand())
        self.trigger(accept=False)
        self.assertEqual(len(self.hand()), hand_before)
        self.assertIn("skipped the ability", self.state["log"][-1]["text"])

    def test_abilities_of_a_climax_being_placed(self):
        self.card(50, '【AUTO】 【CXCOMBO】 When "BIG" is placed on your climax area, this card gets +1000 power until end of turn.')
        self.card(16, card_type="Climax", name="BIG")
        self.card(17, card_type="Climax", name="SMALL")
        uid = self.seat(50, "C1")
        self.act(1, {"type": "move", "uid": self.uid(17), "to": "climax"})
        self.assertIsNone(self.ability())
        self.act(1, {"type": "move", "uid": self.uid(16), "to": "climax"})
        self.trigger()
        self.assertEqual(self.stats(uid)["power"], 2000)

    def test_a_phase_trigger_holds_the_phases_until_its_resolved(self):
        self.card(50, "【AUTO】 At the beginning of your climax phase, this card gets +1000 power until end of turn.")
        uid = self.seat(50, "C1")
        self.act(1, {"type": "phase", "phase": "attack"})  # through the climax phase
        self.assertEqual(self.state["phase"], "climax")
        with self.assertRaises(game.GameError):
            self.act(1, {"type": "phase", "phase": "attack"})
        self.trigger()
        self.assertEqual(self.stats(uid)["power"], 2000)
        self.assertEqual(self.state["auto_next"], "attack")  # and then it carries on

    def test_attack_abilities_resolve_before_the_trigger_check(self):
        self.card(20, "【AUTO】 When this card attacks, this card gets +1 soul until end of turn.")
        uid = self.play(20, "C2")
        self.act(1, {"type": "phase", "phase": "attack"})
        deck_before = len(zones(self.state, 1)["deck"])
        self.act(1, {"type": "attack", "uid": uid, "kind": "direct"})
        self.assertEqual(len(zones(self.state, 1)["deck"]), deck_before)  # no trigger check yet
        with self.assertRaises(game.GameError):
            self.act(1, {"type": "phase", "phase": "encore"})
        self.trigger()
        self.assertEqual(len(zones(self.state, 1)["deck"]), deck_before - 1)
        self.assertEqual(len(zones(self.state, 2)["clock"]), 3)  # soul 1 +1 from the ability, +1 direct

    def test_a_granted_ability_triggers_when_the_battle_opponent_is_reversed(self):
        self.card(20, '【AUTO】 When this card is placed on the stage from your hand, this card gets +5000 power and the following ability until end of turn. '
                      '"【AUTO】 When this card\'s battle opponent becomes 【REVERSE】, draw 1 card."')
        uid = self.play(20, "C2")
        self.trigger()
        self.seat(120, "C2", player=2)
        self.act(1, {"type": "phase", "phase": "attack"})
        self.act(1, {"type": "attack", "uid": uid, "kind": "front"})
        if self.state["attack"]["step"] == "counter":
            self.act(2, {"type": "no_counter"})
        self.assertEqual(self.state["players"]["2"]["stage"]["C2"]["pos"], "reverse")
        hand_before = len(self.hand())
        self.trigger()
        self.assertEqual(len(self.hand()), hand_before + 1)

    def test_put_that_character_acts_on_the_battle_opponent(self):
        self.card(20, "【AUTO】 When this card's battle opponent becomes 【REVERSE】, you may put that character into your opponent's memory.")
        self.card(120, power=500)
        uid = self.play(20, "C2")
        target = self.seat(120, "C2", player=2)
        self.act(1, {"type": "phase", "phase": "attack"})
        self.act(1, {"type": "attack", "uid": uid, "kind": "front"})
        if self.state["attack"]["step"] == "counter":
            self.act(2, {"type": "no_counter"})
        self.trigger()
        self.assertEqual(zones(self.state, 2)["memory"][-1]["uid"], target)
        self.assertIsNone(self.state["players"]["2"]["stage"]["C2"])

    def test_encore_keyword_brings_the_character_back_rested(self):
        self.card(20, "【AUTO】 Encore [Put 1 card from your hand into your waiting room] (When this card is put into your waiting room from the stage, "
                      "you may pay the cost. If you do, return this card to its previous stage position as 【REST】)")
        uid = self.play(20, "C2")
        self.act(1, {"type": "move", "uid": uid, "to": "waiting"})
        self.trigger()
        self.act(1, {"type": "ability_answer", "uids": [self.ability()["prompt"]["options"][0]]})
        card = self.state["players"]["1"]["stage"]["C2"]
        self.assertEqual((card["uid"], card["pos"]), (uid, "rest"))

    # Prompts

    def test_looking_at_the_deck_hides_it_from_the_opponent(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, look at up to 3 cards from the top of your deck, choose up to 1 《NIKKE》 character from among them, "
                      "reveal it to your opponent, put it into your hand, and put the rest into your waiting room.")
        self.play(20, "C1")
        self.trigger()
        self.act(1, {"type": "ability_answer", "value": 2})  # how many to look at
        mine = game.view(self.state, 1)
        theirs = game.view(self.state, 2)
        self.assertEqual([c["card"] for c in mine["ability"]["prompt"]["cards"]], [15, 14])
        self.assertIn(15, game.visible_cards(mine))
        self.assertIsNone(theirs["ability"]["prompt"])
        self.assertNotIn(15, game.visible_cards(theirs))
        self.act(1, {"type": "ability_answer", "uids": [mine["ability"]["prompt"]["cards"][1]["uid"]]})
        self.assertEqual(self.hand()[-1]["card"], 14)
        self.assertEqual(zones(self.state, 1)["waiting"][-1]["card"], 15)

    def test_look_then_split_the_chosen_cards_between_hand_and_stock(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, look at up to 3 cards from the top of your deck, choose up to 2 《NIKKE》 characters from among them, "
                      "reveal them to your opponent, choose 1 card from among them, put it into your hand, choose 1 card from among them, put it into your stock, and put the rest into your waiting room.")
        self.play(20, "C1")
        self.trigger()
        self.act(1, {"type": "ability_answer", "value": 3})
        looked = {c["card"]: c["uid"] for c in self.ability()["prompt"]["cards"]}
        self.assertEqual(sorted(looked), [13, 14, 15])
        self.act(1, {"type": "ability_answer", "uids": [looked[15], looked[14]]})
        self.assertEqual(sorted(self.ability()["prompt"]["options"]), sorted([looked[15], looked[14]]))  # only what was revealed
        self.act(1, {"type": "ability_answer", "uids": [looked[15]]})
        self.assertEqual(self.ability()["prompt"]["options"], [looked[14]])  # not the card already taken
        self.act(1, {"type": "ability_answer", "uids": [looked[14]]})
        self.assertEqual(self.hand()[-1]["card"], 15)
        self.assertEqual(zones(self.state, 1)["stock"][-1]["card"], 14)
        self.assertEqual(zones(self.state, 1)["waiting"][-1]["card"], 13)

    def test_choosing_nothing_from_a_look_sends_it_all_to_the_waiting_room(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, look at up to 2 cards from the top of your deck, choose up to 1 《NIKKE》 character from among them, "
                      "reveal it to your opponent, put it into your hand, and put the rest into your waiting room.")
        self.play(20, "C1")
        hand_before = len(self.hand())
        self.trigger()
        self.act(1, {"type": "ability_answer", "value": 2})
        self.act(1, {"type": "ability_answer", "uids": []})
        self.assertEqual(len(self.hand()), hand_before)
        self.assertEqual([c["card"] for c in zones(self.state, 1)["waiting"]], [15, 14])
        self.assertIsNone(self.ability())

    def test_choose_from_the_waiting_room_then_the_rest(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, choose up to 2 characters in your waiting room, choose 1 card from among them, return it to your hand, and put the rest into your stock.")
        for pk in (19, 18):
            self.act(1, {"type": "move", "uid": self.uid(pk), "to": "waiting"})
        self.play(20, "C1")
        self.trigger()
        a, b = self.ability()["prompt"]["options"]
        self.act(1, {"type": "ability_answer", "uids": [a, b]})
        self.act(1, {"type": "ability_answer", "uids": [a]})
        self.assertEqual(self.hand()[-1]["uid"], a)
        self.assertEqual(zones(self.state, 1)["stock"][-1]["uid"], b)

    def test_a_search_offers_only_what_fits_and_shuffles(self):
        self.card(15, card_type="Climax", traits="")
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, search your deck for up to 1 《NIKKE》 character, reveal it to your opponent, put it into your hand, and shuffle your deck.")
        self.play(20, "C1")
        self.trigger()
        prompt = self.ability()["prompt"]
        self.assertEqual(len(prompt["options"]), 14)  # all of the deck but the climax on top
        self.act(1, {"type": "ability_answer", "uids": [prompt["options"][0]]})
        self.assertEqual(len(zones(self.state, 1)["deck"]), 14)
        self.assertIn("shuffled", self.state["log"][-1]["text"])

    def test_choosing_between_effects(self):
        self.card(20, '【AUTO】 When this card is placed on the stage from your hand, choose 1 of the following effects, and perform it. '
                      '"Draw 1 card." "This card gets +3000 power until end of turn."')
        uid = self.play(20, "C1")
        self.trigger()
        self.assertEqual([o["label"] for o in self.ability()["prompt"]["options"]], ["Draw 1 card.", "This card gets +3000 power until end of turn."])
        self.act(1, {"type": "ability_answer", "value": 1})
        self.assertEqual(self.stats(uid)["power"], 4000)

    def test_an_answer_outside_the_choices_is_refused(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, choose 1 of your characters, and that character gets +1 soul until end of turn.")
        self.play(20, "C1")
        self.trigger()
        with self.assertRaises(game.GameError):
            self.act(1, {"type": "ability_answer", "uids": ["nope"]})
        with self.assertRaises(game.GameError):
            self.act(2, {"type": "ability_answer", "uids": []})

    def test_a_step_by_hand_leaves_the_board_usable_until_done(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, draw 1 card, and juggle.")
        self.play(20, "C1")
        self.trigger()
        self.assertEqual(self.ability()["prompt"]["kind"], "manual")
        self.act(1, {"type": "move", "uid": self.hand()[0]["uid"], "to": "stock"})  # moves still work
        with self.assertRaises(game.GameError):
            self.act(1, {"type": "phase", "phase": "end"})
        self.act(1, {"type": "ability_answer"})
        self.assertIsNone(self.ability())

    def test_damage_from_an_ability_finishes_before_the_next_step(self):
        self.card(100, card_type="Climax", power=None)  # bob's deck top is 100... made a climax below
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, deal 1 damage to your opponent, and draw 1 card.")
        zones(self.state, 2)["deck"][-1]["card"] = 100
        self.play(20, "C1")
        hand_before = len(self.hand())
        self.trigger()
        self.assertTrue(game.view(self.state, 2)["damage_pending"])
        self.assertEqual(len(self.hand()), hand_before)  # it waits for the cancel to be shown
        self.act(2, {"type": "resolve_damage"})
        self.assertEqual(len(self.hand()), hand_before + 1)

    def test_stopping_leaves_the_rest_undone(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, choose 1 of your characters, and that character gets +1 soul until end of turn.")
        uid = self.play(20, "C1")
        self.trigger()
        self.act(1, {"type": "ability_stop"})
        self.assertIsNone(self.ability())
        self.assertEqual(self.stats(uid)["soul"], 1)

    # The ! button

    def test_activating_pays_the_cost_and_resolves(self):
        self.card(20, "【ACT】 [(1) 【REST】 this card] Choose 1 of your characters, and that character gets +1000 power until end of turn.")
        uid = self.play(20, "C1")
        self.stock(1)
        row = game.view(self.state, 1)["acts"][uid][0]
        self.assertIsNone(row["why"])
        self.assertEqual(game.view(self.state, 2)["acts"], {})  # only the owner sees their buttons
        self.act(1, {"type": "activate", "uid": uid, "index": row["index"]})
        self.assertEqual(self.state["players"]["1"]["stage"]["C1"]["pos"], "rest")
        self.assertEqual(zones(self.state, 1)["stock"], [])
        self.act(1, {"type": "ability_answer", "uids": [uid]})
        self.assertEqual(self.stats(uid)["power"], 2000)

    def test_the_button_says_why_it_cant_be_used(self):
        self.card(20, "【ACT】 [(1) 【REST】 this card] Draw 1 card.")
        uid = self.play(20, "C1")
        self.assertEqual(game.view(self.state, 1)["acts"][uid][0]["why"], "needs 1 stock")
        with self.assertRaises(game.GameError):
            self.act(1, {"type": "activate", "uid": uid, "index": 0})
        self.stock(1)
        self.act(1, {"type": "position", "uid": uid, "pos": "rest"})
        self.assertEqual(game.view(self.state, 1)["acts"][uid][0]["why"], "needs this card standing")
        self.act(1, {"type": "position", "uid": uid, "pos": "stand"})
        self.act(1, {"type": "phase", "phase": "climax"})
        self.assertEqual(game.view(self.state, 1)["acts"][uid][0]["why"], "only in your main phase")

    def test_cards_with_only_other_abilities_get_no_button(self):
        self.card(20, "【CONT】 During your turn, this card gets +2000 power.")
        uid = self.play(20, "C1")
        self.assertNotIn(uid, game.view(self.state, 1)["acts"])

    def test_once_per_turn(self):
        self.card(20, "【ACT】 1/TURN@ Draw 1 card.")
        uid = self.play(20, "C1")
        self.act(1, {"type": "activate", "uid": uid, "index": 0})
        self.assertEqual(game.view(self.state, 1)["acts"][uid][0]["why"], "already used this turn")

    def test_an_ability_usable_from_the_waiting_room(self):
        self.card(20, "【ACT】 [(1)] If this card is in your waiting room, your level is 1 or higher, put this card in an open position of your stage.")
        self.stock(1)
        zones(self.state, 1)["level"].append(game.new_card(99))
        uid = self.uid(20)
        self.act(1, {"type": "move", "uid": uid, "to": "waiting"})
        self.act(1, {"type": "activate", "uid": uid, "index": 0})
        self.act(1, {"type": "ability_answer", "value": "C2"})
        self.assertEqual(self.state["players"]["1"]["stage"]["C2"]["uid"], uid)

    # Showing an ability once it's done

    def buff_card(self, pk):
        self.card(pk, "【AUTO】 When this card is placed on the stage from your hand, choose 1 of your characters, and that character gets +1 soul until end of turn.")

    def test_an_ability_is_shown_to_both_players_with_its_target(self):
        self.buff_card(20)
        other = self.seat(50, "C1")
        self.play(20, "C2")
        self.apply(1, {"type": "ability_trigger", "id": self.ability()["queue"][0]["id"], "accept": True})
        self.assertIsNone(self.state.get("ability_show"))  # not until the prompts are answered
        self.apply(1, {"type": "ability_answer", "uids": [other]})
        for player, mine in ((1, True), (2, False)):
            view = game.view(self.state, player)
            self.assertEqual({k: view["ability_show"][k] for k in ("card", "targets", "mine")}, {"card": 20, "targets": [50], "mine": mine})
            self.assertLessEqual({20, 50}, game.visible_cards(view))

    def test_a_card_directed_at_itself_has_no_target(self):
        self.buff_card(20)
        uid = self.play(20, "C1")
        self.apply(1, {"type": "ability_trigger", "id": self.ability()["queue"][0]["id"], "accept": True})
        self.apply(1, {"type": "ability_answer", "uids": [uid]})
        self.assertEqual(self.state["ability_show"]["targets"], [])

    def test_play_waits_for_the_show_and_a_stale_end_does_nothing(self):
        self.card(20, "【AUTO】 When this card attacks, this card gets +1 soul until end of turn.")
        uid = self.play(20, "C2")
        self.act(1, {"type": "phase", "phase": "attack"})
        deck_before = len(zones(self.state, 1)["deck"])
        self.act(1, {"type": "attack", "uid": uid, "kind": "direct"})
        self.apply(1, {"type": "ability_trigger", "id": self.ability()["queue"][0]["id"], "accept": True})
        self.assertEqual(len(zones(self.state, 1)["deck"]), deck_before)  # the trigger check waits
        with self.assertRaises(game.GameError):
            self.apply(1, {"type": "phase", "phase": "encore"})
        self.apply(2, {"type": "ability_show_done", "id": "stale"})
        self.assertTrue(self.state.get("ability_show"))
        self.apply(2, {"type": "ability_show_done", "id": self.state["ability_show"]["id"]})  # the other page can end it too
        self.assertEqual(len(zones(self.state, 1)["deck"]), deck_before - 1)

    def test_hidden_cards_arent_shown_as_targets(self):
        self.card(20, "【AUTO】 [Put 1 card from your hand into your waiting room] When this card is placed on the stage from your hand, you may pay the cost. If you do, "
                      "look at up to 1 cards from the top of your deck, choose up to 1 card from among them, and put it into your hand.")
        self.play(20, "C1")
        self.apply(1, {"type": "ability_trigger", "id": self.ability()["queue"][0]["id"], "accept": True})
        self.apply(1, {"type": "ability_answer", "uids": [self.ability()["prompt"]["options"][0]]})  # the cost
        self.apply(1, {"type": "ability_answer", "value": 1})
        self.apply(1, {"type": "ability_answer", "uids": [self.ability()["prompt"]["options"][0]]})  # into the hand, unrevealed
        self.assertEqual(self.state["ability_show"]["targets"], [])

    def test_a_revealed_card_and_a_battle_opponent_are_targets(self):
        self.card(20, "【AUTO】 When this card's battle opponent becomes 【REVERSE】, you may put that character into your opponent's memory.")
        self.card(120, power=500)
        uid = self.play(20, "C2")
        self.seat(120, "C2", player=2)
        self.act(1, {"type": "phase", "phase": "attack"})
        self.act(1, {"type": "attack", "uid": uid, "kind": "front"})
        if self.state["attack"]["step"] == "counter":
            self.act(2, {"type": "no_counter"})
        self.trigger()
        self.assertEqual(self.last_show["targets"], [120])

    def test_skipping_or_declining_shows_nothing(self):
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, draw 1 card.")
        self.play(20, "C1")
        self.apply(1, {"type": "ability_trigger", "id": self.ability()["queue"][0]["id"], "accept": False})
        self.assertIsNone(self.state.get("ability_show"))
        self.card(19, '【AUTO】 When this card is placed on the stage from your hand, this card gets +1 soul until end of turn, and you may draw 1 card.')
        self.play(19, "C2")
        self.apply(1, {"type": "ability_trigger", "id": self.ability()["queue"][0]["id"], "accept": True})
        self.apply(1, {"type": "ability_answer", "value": "no"})
        self.assertIsNone(self.state.get("ability_show"))  # the buff to itself was done, but there's nothing left to point at

    def test_stopping_shows_nothing(self):
        self.buff_card(20)
        self.play(20, "C1")
        self.apply(1, {"type": "ability_trigger", "id": self.ability()["queue"][0]["id"], "accept": True})
        self.apply(1, {"type": "ability_stop"})
        self.assertIsNone(self.state.get("ability_show"))

    # Events, and with the rules off

    def test_an_event_resolves_then_goes_to_the_waiting_room(self):
        self.card(20, "Draw 1 card.", card_type="Event", power=None)
        uid = self.play(20, "resolution")
        hand_before = len(self.hand())
        self.trigger()
        self.assertEqual(len(self.hand()), hand_before + 1)
        self.assertEqual(zones(self.state, 1)["waiting"][-1]["uid"], uid)

    def test_an_event_can_put_itself_somewhere_else(self):
        self.card(20, "Draw 1 card. Put this card into your memory.", card_type="Event", power=None)
        uid = self.play(20, "resolution")
        self.trigger()
        self.assertEqual(zones(self.state, 1)["memory"][-1]["uid"], uid)

    def test_with_the_rules_off_nothing_triggers_but_boosts_and_the_button_work(self):
        self.state["rules"] = False
        self.card(20, "【AUTO】 When this card is placed on the stage from your hand, draw 1 card.")
        self.card(19, "【CONT】 All of your characters get +500 power.\n【ACT】 Draw 1 card.")
        self.play(20, "C1")
        self.assertIsNone(self.ability())
        uid = self.play(19, "C2")
        self.assertEqual(self.stats(uid)["power"], 1500)
        self.state["phase"] = "attack"
        self.act(1, {"type": "chat", "text": "."})
        self.assertIsNone(game.view(self.state, 1)["acts"][uid][0]["why"])


class GameOverTests(TestCase):
    def setUp(self):
        self.state = started()
        self.level = zones(self.state, 1)["level"]
        self.level += [game.new_card(50) for _ in range(3)]

    def level_up(self):
        clock = zones(self.state, 1)["clock"]
        clock += [game.new_card(60) for _ in range(game.LEVEL_UP_AT)]
        game.apply(self.state, 1, {"type": "level_up", "uid": clock[0]["uid"]})

    def test_reaching_level_4_makes_the_other_player_the_winner(self):
        self.level_up()
        self.assertEqual(self.state["game_over"], {"winner": "2", "loser": "1", "reason": "level", "rematch": []})
        self.assertFalse(game.view(self.state, 1)["game_over"]["won"])
        self.assertTrue(game.view(self.state, 2)["game_over"]["won"])
        self.assertEqual(game.view(self.state, 1)["match_wins"], [{"name": "alice", "wins": 0}, {"name": "bob", "wins": 1}])
        self.assertEqual(game.view(self.state, 2)["match_wins"][0]["name"], "alice")  # the same way round for both

    def test_level_3_is_still_playing(self):
        self.level.pop()
        self.level_up()
        self.assertNotIn("game_over", self.state)

    def test_getting_there_any_other_way_counts_too(self):
        game.apply(self.state, 1, {"type": "move", "uid": zones(self.state, 1)["hand"][0]["uid"], "to": "level"})
        self.assertEqual(self.state["game_over"]["winner"], "2")

    def test_everything_in_progress_stops_and_only_the_end_of_game_actions_work(self):
        self.state["attack"] = {"step": "damage"}
        self.state["ability_queue"] = [{"id": "x", "player": "1"}]
        self.level_up()
        self.assertNotIn("attack", self.state)
        self.assertIsNone(game.view(self.state, 1)["ability"])
        with self.assertRaises(game.GameError):
            game.apply(self.state, 1, {"type": "move_top", "from": "deck", "to": "hand"})
        game.apply(self.state, 1, {"type": "phase", "phase": "end", "auto": True})  # a page's timer: ignored
        game.apply(self.state, 2, {"type": "chat", "text": "gg"})
        self.assertEqual(self.state["log"][-1]["text"], "gg")

    def test_a_rematch_takes_both_players(self):
        with self.assertRaises(game.GameError):
            game.apply(self.state, 1, {"type": "rematch"})
        self.level_up()
        game.apply(self.state, 1, {"type": "rematch"})
        game.apply(self.state, 1, {"type": "rematch"})
        self.assertFalse(game.rematch_agreed(self.state))
        self.assertTrue(game.view(self.state, 2)["game_over"]["opponent_rematch"])
        game.apply(self.state, 2, {"type": "rematch"})
        self.assertTrue(game.rematch_agreed(self.state))


class DeckOutLossTests(TestCase):
    def setUp(self):
        self.state = started()
        self.mine = zones(self.state, 1)

    def act(self, player, action, **kwargs):
        game.apply(self.state, player, action, shuffle=no_shuffle, **kwargs)

    def test_no_deck_and_no_waiting_room_loses(self):
        self.act(1, {"type": "move_top", "from": "deck", "to": "stock", "count": 15})
        self.assertEqual(self.state["game_over"], {"winner": "2", "loser": "1", "reason": "deck", "rematch": []})
        self.assertEqual(game.view(self.state, 2)["game_over"]["reason"], "deck")
        self.assertIn("can't refresh", self.state["log"][-1]["text"])

    def test_a_waiting_room_to_refresh_from_keeps_you_in(self):
        for _ in range(2):
            self.act(1, {"type": "move", "uid": self.mine["hand"][0]["uid"], "to": "waiting"})
        self.act(1, {"type": "move_top", "from": "deck", "to": "stock", "count": 15})
        self.assertNotIn("game_over", self.state)
        self.assertEqual(self.state["players"]["1"]["refreshes"], 1)

    def test_refreshing_the_last_card_away_loses(self):
        self.act(1, {"type": "move", "uid": self.mine["hand"][0]["uid"], "to": "waiting"})
        self.act(1, {"type": "move_top", "from": "deck", "to": "stock", "count": 15})  # the only card goes to the clock
        self.assertEqual(self.mine["deck"], [])
        self.assertEqual(self.mine["waiting"], [])
        self.assertEqual(self.state["game_over"]["reason"], "deck")

    def test_damage_running_out_of_cards_loses(self):
        del self.mine["deck"][2:]
        self.act(1, {"type": "damage", "count": 3})
        self.assertEqual(self.state["game_over"]["loser"], "1")

    def test_a_cancelled_damage_that_empties_the_deck_refreshes_instead(self):
        del self.mine["deck"][1:]
        self.mine["waiting"].append(game.new_card(50))
        climax = self.mine["deck"][0]["card"]
        self.act(1, {"type": "damage", "count": 2}, is_climax=lambda pk: pk == climax, name=str)
        self.assertNotIn("game_over", self.state)  # its cards are still on their way to the waiting room
        self.act(1, {"type": "resolve_damage"}, is_climax=lambda pk: pk == climax, name=str)
        self.assertNotIn("game_over", self.state)
        self.assertEqual((len(self.mine["deck"]), len(self.mine["clock"])), (1, 1))

    def test_the_mulligan_and_turn_rules_off_dont_count(self):
        state = game.new_game([(1, "alice", [1, 2]), (2, "bob", list(range(101, 121)))], shuffle=no_shuffle)
        game.apply(state, 2, {"type": "chat", "text": "."})
        self.assertNotIn("game_over", state)
        self.state["rules"] = False
        self.act(1, {"type": "move_top", "from": "deck", "to": "stock", "count": 15})
        self.assertNotIn("game_over", self.state)


class RockPaperScissorsTests(TestCase):
    def setUp(self):
        self.state = game.new_game([(1, "alice", list(range(1, 21))), (2, "bob", list(range(101, 121)))], shuffle=no_shuffle, rps=True)

    def pick(self, player, choice):
        game.apply(self.state, player, {"type": "rps", "choice": choice})

    def test_the_other_pick_stays_secret_until_both_are_in(self):
        self.pick(1, "rock")
        bob = game.view(self.state, 2)["rps"]
        self.assertEqual((bob["mine"], bob["opponent_chose"], bob["last"]), (None, True, None))
        self.assertNotIn("rock", json.dumps(bob))
        self.assertNotIn("rock", json.dumps(self.state["log"]))
        self.assertEqual(game.view(self.state, 1)["rps"]["mine"], "rock")

    def test_each_hand_beats_the_right_one(self):
        for winner, loser in game.RPS_BEATS.items():
            self.setUp()
            self.pick(1, loser)
            self.pick(2, winner)
            self.assertEqual((self.state["turn"], self.state["first_player"]), ("2", "2"))
            self.assertTrue(game.view(self.state, 2)["rps"]["won"])
            self.assertFalse(game.view(self.state, 1)["rps"]["won"])
            self.assertEqual(game.view(self.state, 1)["rps"]["last"], {"me": loser, "opponent": winner})

    def test_a_tie_goes_again(self):
        self.pick(1, "rock")
        self.pick(2, "rock")
        view = game.view(self.state, 1)["rps"]
        self.assertEqual((view["mine"], view["won"], view["last"]["opponent"]), (None, None, "rock"))
        self.pick(1, "paper")
        self.pick(2, "rock")
        self.assertEqual(self.state["turn"], "1")

    def test_one_pick_each_and_nothing_else_until_its_over(self):
        self.pick(1, "rock")
        with self.assertRaises(game.GameError):
            self.pick(1, "paper")
        with self.assertRaises(game.GameError):
            self.pick(2, "dynamite")
        with self.assertRaises(game.GameError):
            game.apply(self.state, 2, {"type": "mulligan", "uids": []})
        self.pick(2, "paper")
        with self.assertRaises(game.GameError):  # the result is still showing
            game.apply(self.state, 2, {"type": "mulligan", "uids": []})

    def test_then_on_to_the_mulligan_and_the_winners_turn(self):
        self.pick(1, "rock")
        self.pick(2, "paper")
        game.apply(self.state, 1, {"type": "rps_done"})
        game.apply(self.state, 2, {"type": "rps_done"})  # the other page's copy
        self.assertIsNone(game.view(self.state, 1)["rps"])
        game.apply(self.state, 1, {"type": "mulligan", "uids": []})
        game.apply(self.state, 2, {"type": "mulligan", "uids": []})
        self.assertEqual((self.state["turn"], self.state["phase"]), ("2", "stand"))


class MatchFlowTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name=WEISS_GROUP)
        self.host = User.objects.create_user("alice", password="x")
        self.guest = User.objects.create_user("bob", password="x")
        card = Card.objects.create(serial_number="X/1", name="X", expansion="E", card_type="Character", level=0, power=1000, soul=1)
        self.decks = {}
        for user in (self.host, self.guest):
            user.groups.add(group)
            self.decks[user] = CardList.objects.create(user=user, name=f"{user.username}'s")
            CardListEntry.objects.create(card_list=self.decks[user], card=card, quantity=30)
        self.room = GameRoom.objects.create(host=self.host, guest=self.guest, host_deck=self.decks[self.host], guest_deck=self.decks[self.guest])
        self.client.force_login(self.host)
        self.client.post(reverse("weiss:play_start", args=[self.room.pk]))
        self.room.refresh_from_db()
        self.client.force_login(self.guest)
        self.post(self.host, {"type": "rps", "choice": "rock"})
        self.post(self.guest, {"type": "rps", "choice": "scissors"})
        self.post(self.guest, {"type": "rps_done"})
        self.room.refresh_from_db()

    def post(self, user, action):
        self.client.force_login(user)
        return self.client.post(reverse("weiss:play_action", args=[self.room.pk]), json.dumps(action), content_type="application/json")

    def lose(self, user):
        """Put this player on the brink, then an action takes them to level 4."""
        self.room.refresh_from_db()
        side = self.room.state["players"][str(user.pk)]
        card = side["zones"]["deck"][0]["card"]
        side["zones"]["level"] = [game.new_card(card) for _ in range(game.LOSING_LEVEL)]
        self.room.state.pop("game_over", None)
        self.room.save()
        return self.post(user, {"type": "shuffle"})

    def wins(self):
        return [self.decks[u].__class__.objects.get(pk=self.decks[u].pk).wins for u in (self.host, self.guest)]

    def test_the_winners_deck_gets_one_win(self):
        data = self.lose(self.host).json()
        self.assertFalse(data["board"]["game_over"]["won"])
        self.assertEqual(self.wins(), [0, 1])
        self.post(self.guest, {"type": "chat", "text": "gg"})
        self.post(self.host, {"type": "rematch"})
        self.assertEqual(self.wins(), [0, 1])  # only the action that ended it counts

    def test_a_rematch_deals_again_and_keeps_the_tally(self):
        self.lose(self.host)
        self.post(self.host, {"type": "rematch"})
        data = self.post(self.guest, {"type": "rematch"}).json()
        self.assertIsNone(data["board"]["game_over"])
        self.assertEqual(data["board"]["phase"], "mulligan")
        self.assertEqual(data["board"]["me"]["zones"]["level"], [])
        self.assertEqual(data["board"]["match_wins"], [{"name": "alice", "wins": 0}, {"name": "bob", "wins": 1}])
        data = self.lose(self.guest).json()
        self.assertEqual(data["board"]["match_wins"], [{"name": "alice", "wins": 1}, {"name": "bob", "wins": 1}])
        self.assertEqual(self.wins(), [1, 1])

    def test_game_1_has_rock_paper_scissors_and_rematches_count_up_and_alternate(self):
        self.assertEqual((self.room.state["game_number"], self.room.state["first_player"]), (1, str(self.host.pk)))  # she won
        firsts = [str(self.guest.pk), str(self.host.pk), str(self.guest.pk)]
        for number, first in enumerate(firsts, start=2):
            self.lose(self.host)
            self.post(self.host, {"type": "rematch"})
            data = self.post(self.guest, {"type": "rematch"}).json()
            self.room.refresh_from_db()
            self.assertEqual((data["board"]["game_number"], self.room.state["turn"]), (number, first))
            self.assertIsNone(data["board"]["rps"])

    def test_rematches_alternate_from_whoever_won_game_1(self):
        self.room.refresh_from_db()
        self.client.force_login(self.host)
        self.client.post(reverse("weiss:play_reset", args=[self.room.pk]))
        self.client.post(reverse("weiss:play_start", args=[self.room.pk]))
        self.post(self.host, {"type": "rps", "choice": "rock"})
        self.post(self.guest, {"type": "rps", "choice": "paper"})  # bob wins this time
        self.post(self.guest, {"type": "rps_done"})
        self.room.refresh_from_db()
        self.assertEqual(self.room.state["turn"], str(self.guest.pk))
        self.lose(self.host)
        self.post(self.host, {"type": "rematch"})
        self.post(self.guest, {"type": "rematch"})
        self.room.refresh_from_db()
        self.assertEqual(self.room.state["turn"], str(self.host.pk))

    def test_a_new_set_goes_back_to_game_1_for_either_player(self):
        self.lose(self.guest)
        self.post(self.host, {"type": "rematch"})
        self.post(self.guest, {"type": "rematch"})
        self.room.refresh_from_db()
        self.assertEqual(self.room.state["game_number"], 2)
        self.client.force_login(self.guest)
        self.client.post(reverse("weiss:play_start", args=[self.room.pk]))
        self.room.refresh_from_db()
        self.assertEqual((self.room.state["game_number"], self.room.state["match_wins"]), (1, {}))
        self.assertEqual((self.room.state["turn_number"], self.room.state["phase"]), (1, "mulligan"))
        self.assertIn("rps", self.room.state)
        self.assertEqual(self.wins(), [1, 0])  # a deck keeps wins it has earned
        self.assertContains(self.client.get(reverse("weiss:play_room", args=[self.room.pk])), "New Set")

    def test_a_new_match_is_game_1_again(self):
        self.lose(self.host)
        self.post(self.host, {"type": "end_match"})
        self.client.post(reverse("weiss:play_start", args=[self.room.pk]))
        self.room.refresh_from_db()
        self.assertEqual(self.room.state["game_number"], 1)
        self.assertIn("rps", self.room.state)

    def test_either_player_can_end_the_match(self):
        self.lose(self.host)
        self.assertEqual(self.post(self.guest, {"type": "end_match"}).json()["status"], "setup")
        self.room.refresh_from_db()
        self.assertEqual((self.room.status, self.room.state), ("setup", {}))
        self.assertEqual(self.wins(), [0, 1])  # the deck keeps its win

    def test_the_match_cant_be_ended_during_a_game(self):
        self.assertEqual(self.post(self.guest, {"type": "end_match"}).status_code, 400)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, "playing")

    def test_a_new_match_starts_the_tally_again(self):
        self.lose(self.host)
        self.post(self.host, {"type": "end_match"})
        self.client.post(reverse("weiss:play_start", args=[self.room.pk]))
        self.room.refresh_from_db()
        self.assertEqual(self.room.state["match_wins"], {})

    def test_a_deleted_deck_stops_the_rematch_with_a_reason(self):
        self.lose(self.host)
        self.decks[self.guest].delete()
        self.post(self.host, {"type": "rematch"})
        data = self.post(self.guest, {"type": "rematch"}).json()
        self.assertIn("deleted", data["error"])
        self.assertIsNotNone(data["board"]["game_over"])

    def test_stars_show_on_the_deck_screens(self):
        self.decks[self.host].wins = 3
        self.decks[self.host].save()
        self.client.force_login(self.host)
        self.assertContains(self.client.get(reverse("weiss:lists")), "★★★")
        self.assertContains(self.client.get(reverse("weiss:list", args=[self.decks[self.host].pk])), "★★★")
        self.assertEqual(CardList(wins=25).win_stars, "★ ×25")


class ColorRuleTests(TestCase):
    """Alice's hand is 20..16; card 50 is a red card for her clock."""

    def setUp(self):
        self.state = started()
        self.state["phase"] = "main"
        self.cards = {50: {"color": "Red", "level": 0}, 20: {"color": "Red", "level": 1, "card_type": "Character"},
                      19: {"color": "Blue", "level": 0, "card_type": "Character"},
                      18: {"color": "Blue", "card_type": "Climax"}, 17: {"color": "Blue", "level": 1, "card_type": "Event"}}

    def info(self, pk):
        return self.cards.get(pk, {})

    def play(self, pk, to, **extra):
        uid = next(c["uid"] for c in zones(self.state, 1)["hand"] if c["card"] == pk)
        game.apply(self.state, 1, {"type": "move", "uid": uid, "to": to, **extra}, info=self.info)
        return uid

    def test_level_one_needs_its_color(self):
        with self.assertRaisesMessage(game.GameError, "needs Red"):
            self.play(20, "C1")
        self.assertEqual(len(zones(self.state, 1)["hand"]), 5)

    def test_its_color_in_the_clock_or_level_zone_is_enough(self):
        for zone in ("clock", "level"):
            self.setUp()
            zones(self.state, 1)[zone].append(game.new_card(50))
            self.play(20, "C1")

    def test_another_color_doesnt_count(self):
        zones(self.state, 1)["clock"].append(game.new_card(19))
        with self.assertRaises(game.GameError):
            self.play(20, "C1")

    def test_level_zero_is_free(self):
        self.play(19, "C1")

    def test_a_climax_needs_its_color_and_being_refused_leaves_the_phase_alone(self):
        with self.assertRaisesMessage(game.GameError, "needs Blue"):
            self.play(18, "climax", end_main=True)
        self.assertEqual(self.state["phase"], "main")

    def test_an_event_needs_its_color(self):
        with self.assertRaises(game.GameError):
            self.play(17, "resolution")

    def test_other_moves_from_the_hand_are_free(self):
        self.play(20, "waiting")
        self.play(18, "stock")

    def test_with_the_rules_off_anything_goes(self):
        self.state["rules"] = False
        self.play(20, "C1")

    def test_a_card_that_says_so_skips_the_color_rule(self):
        self.cards[20]["text"] = "【CONT】 This card can be played from your hand without fulfilling color requirements."
        self.play(20, "C1")

    def test_a_condition_on_that_ability_counts(self):
        self.cards[20]["text"] = "【CONT】 If your level is 1 or higher, this card can be played from your hand without fulfilling color requirements."
        with self.assertRaises(game.GameError):
            self.play(20, "C1")
        zones(self.state, 1)["level"].append(game.new_card(19))  # blue
        self.play(20, "C1")

    def test_two_of_a_card_in_the_level_zone_free_the_others_in_hand(self):
        self.cards[60] = {"name": "CEO", "color": "Blue", "text": '【CONT】 Experience If this card is in your level, and you have another "CEO" in your level, '
                          'all of your 《NIKKE》 characters get the following ability while in your hand. "【CONT】 This card can be played from your hand without fulfilling color requirements."'}
        self.cards[20]["traits"] = "NIKKE・Electric Shock"
        self.cards[16] = {"color": "Red", "level": 1, "card_type": "Character", "traits": "Other"}
        level = zones(self.state, 1)["level"]
        level.append(game.new_card(60))
        with self.assertRaises(game.GameError):  # only one
            self.play(20, "C1")
        level.append(game.new_card(60))
        game.apply(self.state, 1, {"type": "chat", "text": "."}, info=self.info)
        hand = {c["card"]: c["uid"] for c in zones(self.state, 1)["hand"]}
        self.assertNotIn(hand[20], game.view(self.state, 1)["needs_color"])
        self.assertIn(hand[16], game.view(self.state, 1)["needs_color"])  # not 《NIKKE》, and red isn't in play
        self.play(20, "C1")
        with self.assertRaises(game.GameError):
            self.play(16, "C2")

    def test_the_page_is_told_what_the_rule_holds_back(self):
        game.apply(self.state, 1, {"type": "chat", "text": "."}, info=self.info)
        hand = {c["card"]: c["uid"] for c in zones(self.state, 1)["hand"]}
        self.assertEqual(game.view(self.state, 1)["needs_color"][hand[20]], "Red")
        self.assertNotIn(hand[19], game.view(self.state, 1)["needs_color"])  # level 0
        self.assertEqual(game.view(self.state, 2)["needs_color"], {})  # bob's cards aren't known to be anything here

    def test_a_backup_is_exempt_but_another_counter_isnt(self):
        self.cards[20]["text"] = "【ACT】 【COUNTER】 Backup 2000, Level 0 [(0) Put this card from your hand into your waiting room]"
        self.cards[17]["text"] = "【COUNTER】 Draw 1 card."
        self.cards[17]["card_type"] = "Event"
        hand = {c["card"]: c for c in zones(self.state, 1)["hand"]}
        self.assertEqual(game.counter_play(self.state, "1", hand[20], self.info), (0, 2000))
        self.assertIsNone(game.counter_play(self.state, "1", hand[17], self.info))
        zones(self.state, 1)["level"].append(game.new_card(19))  # blue, and level 1 for the counter
        self.assertIsNotNone(game.counter_play(self.state, "1", hand[17], self.info))
