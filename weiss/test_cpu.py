import json
import random
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.access import WEISS_GROUP

from . import abilities, cpu, cpu_views, express, game, play
from .models import Card, CardList, CardListEntry, CpuProfile, GameRoom, cpu_user


def no_shuffle(cards):
    pass


class Table:
    """A game at a chosen point, for seeing what the CPU (player 2, "2") does."""

    def __init__(self, cards=None):
        self.cards = cards or {}
        self.state = game.new_game([(1, "alice", list(range(1, 31))), (2, "cpu", list(range(101, 131)))], shuffle=no_shuffle)
        self.state["phase"] = "main"
        self.state["turn"] = "2"
        self.state["turn_number"] = 3
        self.me = self.state["players"]["2"]
        self.them = self.state["players"]["1"]
        self.me["zones"]["hand"] = []

    def info(self, pk):
        return self.cards.get(pk, {"name": f"Card{pk}", "card_type": "Character", "level": 0, "cost": 0, "power": 1000, "soul": 1, "color": "", "traits": "", "text": ""})

    def card(self, pk, **details):
        self.cards[pk] = {"name": f"Card{pk}", "card_type": "Character", "level": 0, "cost": 0, "power": 1000, "soul": 1, "color": "", "traits": "", "text": "", "trigger": "", **details}
        return pk

    def hand(self, *pks):
        cards = [game.new_card(pk) for pk in pks]
        self.me["zones"]["hand"] += cards
        return cards

    def seat(self, side, slot, pk, pos="stand"):
        card = game.new_card(pk)
        card["pos"] = pos
        side["stage"][slot] = card
        return card

    def stock(self, count):
        self.me["zones"]["stock"] += [game.new_card(900) for _ in range(count)]

    def level(self, count):
        self.me["zones"]["level"] += [game.new_card(900) for _ in range(count)]

    def refresh(self):
        game.refresh_stats(self.state, game.SimpleNamespace(info=self.info, name=lambda pk: "x"))

    def next(self, aggression=1):
        self.refresh()
        return cpu.next_action(self.state, "2", self.info, aggression, random.Random(1))

    def apply(self, player, action, show_checks=False):
        kwargs = dict(shuffle=no_shuffle, info=self.info, name=lambda pk: self.info(pk)["name"],
                      is_climax=lambda pk: (self.info(pk).get("card_type") or "").lower() == "climax",
                      trigger=lambda pk: self.info(pk).get("trigger", ""), cost=lambda pk: self.info(pk).get("cost", 0))
        game.apply(self.state, player, action, **kwargs)
        shown = self.state.get("ability_show")
        if shown and shown.get("check") and not show_checks:  # as a page would, once it's been seen
            game.apply(self.state, player, {"type": "ability_show_done", "id": shown["id"]}, **kwargs)


class FrontLineTests(TestCase):
    def test_plays_the_strongest_it_can_to_the_front(self):
        t = Table()
        t.card(1001, power=2000)
        strong = t.card(1002, power=6000)
        cards = t.hand(1001, strong)
        action = t.next()
        self.assertEqual(action["uid"], cards[1]["uid"])
        self.assertIn(action["to"], game.OPPOSITE)

    def test_wont_play_above_its_level_stock_or_color(self):
        t = Table()
        t.card(1001, power=9000, level=1)
        t.card(1002, power=9000, cost=2)
        t.card(1003, power=9000, level=1, color="Red")
        t.hand(1001, 1002, 1003)
        self.assertEqual(t.next(), {"type": "phase", "phase": "climax"})
        t.level(1)
        t.stock(2)
        action = t.next()
        self.assertNotEqual(next(c["card"] for c in t.me["zones"]["hand"] if c["uid"] == action["uid"]), 1003)

    def test_upgrades_a_weaker_front_character(self):
        t = Table()
        t.seat(t.me, "C1", t.card(1001, power=1000))
        t.seat(t.me, "C2", t.card(1002, power=5000))
        t.seat(t.me, "C3", t.card(1003, power=5000))
        strong = t.hand(t.card(1004, power=8000))[0]
        self.assertEqual(t.next(), {"type": "move", "uid": strong["uid"], "to": "C1"})

    def test_faces_what_it_can_beat(self):
        t = Table()
        t.seat(t.them, game.OPPOSITE["C1"], t.card(1, power=9000))
        t.seat(t.them, game.OPPOSITE["C3"], t.card(2, power=1000))
        t.seat(t.them, game.OPPOSITE["C2"], t.card(3, power=9000))
        t.hand(t.card(1004, power=3000))
        self.assertEqual(t.next()["to"], "C3")

    def test_counts_what_a_back_row_assist_adds(self):
        t = Table()
        t.seat(t.me, "C1", t.card(1001, power=1000))
        t.seat(t.me, "C2", t.card(1002, power=1000))
        t.seat(t.me, "C3", t.card(1003, power=1000))
        helper = t.hand(t.card(1004, power=500, text="【CONT】 Assist All of your characters in front of this card get +1000 power."))[0]
        action = t.next()
        self.assertEqual((action["uid"], action["to"][0]), (helper["uid"], "B"))

    def test_a_card_with_a_live_combo_goes_first(self):
        t = Table()
        t.card(1001, power=8000)
        anchor = t.card(1002, power=1000, text='【AUTO】 【CXCOMBO】 When "BIG" is placed on your climax area, draw 1 card.')
        t.card(1003, card_type="Climax", name="BIG", power=None, level=None)
        cards = t.hand(1001, anchor, 1003)
        self.assertEqual(t.next()["uid"], cards[1]["uid"])

    def test_no_combo_bonus_without_the_climax(self):
        t = Table()
        t.card(1001, power=8000)
        t.card(1002, power=1000, text='【AUTO】 【CXCOMBO】 When "BIG" is placed on your climax area, draw 1 card.')
        cards = t.hand(1001, 1002)
        self.assertEqual(t.next()["uid"], cards[0]["uid"])

    def test_plays_the_climax_its_combo_wants(self):
        t = Table()
        t.state["phase"] = "climax"
        t.seat(t.me, "C1", t.card(1002, text='【AUTO】 【CXCOMBO】 When "BIG" is placed on your climax area, draw 1 card.'))
        t.card(1003, card_type="Climax", name="OTHER", power=None, level=None)
        t.card(1004, card_type="Climax", name="BIG", power=None, level=None)
        cards = t.hand(1003, 1004)
        self.assertEqual(t.next(), {"type": "move", "uid": cards[1]["uid"], "to": "climax"})


class AttackTests(TestCase):
    def attacking(self, mine, theirs, level=1, aggression=1):
        t = Table()
        t.state["phase"] = "attack"
        t.state["attack"] = {"step": "declare"}
        card = t.seat(t.me, "C2", t.card(1001, power=mine))
        t.seat(t.them, "C2", t.card(1, power=theirs, level=level))
        return card, t.next(aggression)

    def test_a_front_attack_to_reverse_what_it_can(self):
        card, action = self.attacking(5000, 3000)
        self.assertEqual(action, {"type": "attack", "uid": card["uid"], "kind": "front"})

    def test_a_side_attack_rather_than_lose_its_character(self):
        card, action = self.attacking(3000, 5000, level=0)
        self.assertEqual(action, {"type": "attack", "uid": card["uid"], "kind": "side"})

    def test_a_side_attack_even_for_no_damage_because_the_trigger_check_gives_stock(self):
        card, action = self.attacking(3000, 5000, level=2)
        self.assertEqual(action, {"type": "attack", "uid": card["uid"], "kind": "side"})

    def test_side_attacks_come_after_everything_that_can_reverse_something(self):
        t = Table()
        t.state["phase"] = "attack"
        t.state["attack"] = {"step": "declare"}
        loser = t.seat(t.me, "C1", t.card(1001, power=1000))
        winner = t.seat(t.me, "C2", t.card(1002, power=9000))
        t.seat(t.them, game.OPPOSITE["C1"], t.card(1, power=8000))
        t.seat(t.them, game.OPPOSITE["C2"], t.card(2, power=8000))
        self.assertEqual(t.next(), {"type": "attack", "uid": winner["uid"], "kind": "front"})
        winner["pos"] = "rest"
        self.assertEqual(t.next(), {"type": "attack", "uid": loser["uid"], "kind": "side"})

    def test_aggression_takes_on_battles_standard_wont(self):
        card, action = self.attacking(4000, 5000, level=0, aggression=3)
        self.assertEqual(action["kind"], "front")
        self.assertEqual(self.attacking(4000, 5000, level=0)[1]["kind"], "side")

    def test_direct_when_nothing_faces_it(self):
        t = Table()
        t.state["phase"] = "attack"
        t.state["attack"] = {"step": "declare"}
        card = t.seat(t.me, "C1", t.card(1001))
        self.assertEqual(t.next(), {"type": "attack", "uid": card["uid"], "kind": "direct"})

    def test_the_biggest_it_can_beat_comes_first(self):
        t = Table()
        t.state["phase"] = "attack"
        t.state["attack"] = {"step": "declare"}
        t.seat(t.me, "C1", t.card(1001, power=9000))
        big = t.seat(t.me, "C2", t.card(1002, power=9000))
        t.seat(t.them, game.OPPOSITE["C1"], t.card(1, power=1000))
        t.seat(t.them, game.OPPOSITE["C2"], t.card(2, power=8000))
        self.assertEqual(t.next()["uid"], big["uid"])


class DefendingTests(TestCase):
    def setup_attack(self, attacker, defender, *hand, kind="front"):
        t = Table()
        t.state["turn"] = "1"
        attack_card = t.seat(t.them, "C2", t.card(1, power=attacker))
        t.seat(t.me, "C2", t.card(1001, power=defender))
        cards = t.hand(*hand)
        t.level(3)
        t.stock(5)
        t.state["attack"] = {"step": "counter", "slot": "C2", "target": "C2", "uid": attack_card["uid"], "kind": kind, "soul": 1, "backup": 0,
                             "counters": [c["uid"] for c in cards]}
        return t, cards

    BACKUP = "【ACT】 【COUNTER】 Backup {}, Level 1 [(1) Put this card from your hand into your waiting room]"

    def test_a_backup_that_reaches_the_attacker_is_played(self):
        t = Table()
        t2, cards = self.setup_attack(5000, 3000, 2001)
        t2.card(2001, text=self.BACKUP.format(2000))
        self.assertEqual(t2.next(), {"type": "counter", "uid": cards[0]["uid"]})

    def test_one_too_small_to_reach_it_isnt(self):
        t, _ = self.setup_attack(6000, 3000, 2001)
        t.card(2001, text=self.BACKUP.format(2000))
        self.assertEqual(t.next(), {"type": "no_counter"})

    def test_not_when_it_already_holds(self):
        t, _ = self.setup_attack(3000, 3000, 2001)
        t.card(2001, text=self.BACKUP.format(2000))
        self.assertEqual(t.next(), {"type": "no_counter"})

    def test_not_in_a_side_attack(self):
        t, _ = self.setup_attack(5000, 3000, 2001, kind="side")
        t.card(2001, text=self.BACKUP.format(2000))
        self.assertEqual(t.next(), {"type": "no_counter"})

    def test_the_cheapest_that_does_the_job(self):
        t, cards = self.setup_attack(5000, 3000, 2001, 2002)
        t.card(2001, text=self.BACKUP.format(3000).replace("(1)", "(1)").replace("[(1)", "[(2)"))
        t.card(2002, text=self.BACKUP.format(2000))
        action = t.next()
        self.assertEqual(action["type"], "counter")


class EncoreTests(TestCase):
    def encore_table(self, level, stock, *hand):
        t = Table()
        t.state["phase"] = "encore"
        card = t.seat(t.me, "C1", t.card(1001, level=level, power=5000), pos="reverse")
        t.stock(stock)
        t.level(3)
        t.hand(*hand)
        return t, card

    def test_low_levels_go_to_the_waiting_room(self):
        t, card = self.encore_table(1, 9)
        self.assertEqual(t.next(), {"type": "move", "uid": card["uid"], "to": "waiting"})

    def test_level_2_and_up_is_encored(self):
        t, card = self.encore_table(2, 9)
        self.assertEqual(t.next(), {"type": "encore", "uid": card["uid"]})

    def test_not_without_the_stock(self):
        t, card = self.encore_table(3, 2)
        self.assertEqual(t.next()["type"], "move")

    def test_not_if_that_would_cost_it_a_stronger_card_in_hand(self):
        t, card = self.encore_table(2, 4, 2001)
        t.card(2001, power=6000, cost=2)
        self.assertEqual(t.next()["type"], "move")

    def test_fine_if_it_can_still_afford_that_card(self):
        t, card = self.encore_table(2, 5, 2001)
        t.card(2001, power=6000, cost=2)
        self.assertEqual(t.next()["type"], "encore")

    def test_a_weaker_card_in_hand_doesnt_stop_it(self):
        t, card = self.encore_table(2, 4, 2001)
        t.card(2001, power=4000, cost=2)
        self.assertEqual(t.next()["type"], "encore")


class HandTests(TestCase):
    def test_clocks_to_draw_its_least_useful_card(self):
        t = Table()
        t.state["phase"] = "clock"
        t.card(1001, level=3, power=1000)
        t.card(1002, level=0, power=5000)
        cards = t.hand(1002, 1001)
        self.assertEqual(t.next(), {"type": "clock_draw", "uid": cards[1]["uid"]})

    def test_not_if_clocking_would_lose_the_game(self):
        t = Table()
        t.state["phase"] = "clock"
        t.level(3)
        t.me["zones"]["clock"] += [game.new_card(900) for _ in range(6)]
        t.hand(t.card(1001))
        self.assertEqual(t.next(), {"type": "phase", "phase": "main"})

    def test_uses_a_back_row_ability_that_draws(self):
        t = Table()
        for slot in game.OPPOSITE:
            t.seat(t.me, slot, t.card(1000, power=9000))
        card = t.seat(t.me, "B1", t.card(1001, text="【ACT】 [【REST】 this card] Draw 1 card."))
        self.assertEqual(t.next(), {"type": "activate", "uid": card["uid"], "index": 0})

    def test_not_one_that_cant_be_paid_for_or_on_the_front_line(self):
        t = Table()
        for slot in ("C2", "C3"):
            t.seat(t.me, slot, t.card(1000, power=9000))
        t.seat(t.me, "C1", t.card(1001, power=9000, text="【ACT】 [【REST】 this card] Draw 1 card."))
        t.seat(t.me, "B1", t.card(1002, text="【ACT】 [(5) 【REST】 this card] Draw 1 card."))
        self.assertEqual(t.next(), {"type": "phase", "phase": "climax"})


class AbilityAnswerTests(TestCase):
    def test_it_triggers_and_answers_an_ability_through_to_the_end(self):
        t = Table()
        t.seat(t.me, "C1", t.card(1002, power=1000))
        t.hand(t.card(1001, power=9000, text="【AUTO】 When this card is placed on the stage from your hand, choose 1 of your characters, and that character gets +2000 power until end of turn."))
        for _ in range(12):
            action = t.next()
            if action["type"] == "phase":
                break
            t.apply(2, action)
        self.assertEqual(sum(b.get("power", 0) for b in t.state.get("buffs", [])), 2000)

    def test_it_skips_what_it_cant_do(self):
        t = Table()
        t.card(1001, text="【AUTO】 When this card is placed on the stage from your hand, juggle the dice.")
        t.seat(t.me, "C1", 1001)
        t.state["ability_queue"] = [{"id": "x", "player": "2", "uid": "u", "card": 1001, "ability": {"steps": [{"do": "manual", "text": "juggle"}], "text": "t"}, "ctx": {}}]
        self.assertEqual(t.next(), {"type": "ability_trigger", "id": "x", "accept": False})

    def test_a_step_it_cant_do_is_logged_as_passed_over(self):
        t = Table()
        t.seat(t.me, "C1", t.card(1001))
        t.state["resolving"] = {"player": "2", "uid": "u", "card": 1001, "text": "t", "steps": [], "ctx": {}, "prompt": {"kind": "manual", "title": "x", "text": "juggle"}}
        t.apply(2, t.next())
        self.assertTrue(any("passed over" in entry["text"] for entry in t.state["log"]))

    def test_only_its_own_prompts(self):
        t = Table()
        t.state["ability_queue"] = [{"id": "x", "player": "1", "uid": "u", "card": 1, "ability": {"steps": [], "text": "t"}, "ctx": {}}]
        self.assertIsNone(t.next())


class FairPlayTests(TestCase):
    def test_it_doesnt_read_the_other_hand(self):
        # Same board, wildly different hidden cards on the other side: same decision.
        results = []
        for their_hand in (1, 2):
            t = Table()
            t.state["phase"] = "attack"
            t.state["attack"] = {"step": "declare"}
            t.seat(t.me, "C2", t.card(1001, power=5000))
            t.seat(t.them, "C2", t.card(5, power=3000))
            t.card(300, text="【ACT】 【COUNTER】 Backup 9000, Level 0 [(0) Put this card from your hand into your waiting room]" if their_hand == 1 else "")
            t.them["zones"]["hand"] = [game.new_card(300)]
            results.append(t.next()["kind"])
        self.assertEqual(results[0], results[1])


def bot_game(state, info, players=("1", "2"), limit=4000, rng=None):
    """Both seats played by CPUs until the game ends. Returns the number of actions."""
    rng = rng or random.Random(1)
    kwargs = dict(shuffle=rng.shuffle, info=info, name=lambda pk: info(pk).get("name", "?"),
                  is_climax=lambda pk: (info(pk).get("card_type") or "").lower() == "climax",
                  trigger=lambda pk: info(pk).get("trigger", ""), cost=lambda pk: info(pk).get("cost", 0))
    for count in range(limit):
        if state.get("game_over"):
            return count
        moved = False
        for player in players:
            action = cpu.next_action(state, player, info, 1, rng)
            if action:
                game.apply(state, player, action, **kwargs)
                moved = True
                break
        if not moved:
            if state.get("rps", {}).get("winner"):
                game.apply(state, players[0], {"type": "rps_done"}, **kwargs)
                continue
            raise AssertionError(f"Stuck in {state.get('phase')}: {state['log'][-3:]}")
    raise AssertionError("Too long")


class WholeGameTests(TestCase):
    def test_two_cpus_can_play_a_whole_game_from_rock_paper_scissors(self):
        cards = {}
        for pk in range(1, 61):
            cards[pk] = {"name": f"C{pk}", "card_type": "Climax" if pk % 7 == 0 else "Character", "level": pk % 4, "cost": pk % 3, "power": 1000 + pk * 100, "soul": 1,
                         "color": "", "traits": "", "trigger": "soul" if pk % 5 == 0 else "", "text": "【CONT】 All of your characters get +1000 power and +1 soul." if pk % 7 == 0 else ""}
        info = lambda pk: cards.get(pk, {})
        for seed in range(5):
            rng = random.Random(seed)
            state = game.new_game([(1, "a", list(range(1, 51))), (2, "b", list(range(11, 61)))], shuffle=rng.shuffle, rps=True)
            self.assertGreater(bot_game(state, info, rng=rng), 20)
            self.assertIn("game_over", state)


class ByHandTests(TestCase):
    def test_finding_steps_done_by_hand(self):
        self.assertEqual(abilities.by_hand_parts("【AUTO】 When this card attacks, draw 1 card."), [])
        self.assertEqual(abilities.by_hand_parts("【CONT】 During your turn, this card gets +1000 power."), [])
        self.assertEqual(abilities.by_hand_parts("【AUTO】 When this card attacks, juggle the dice."), ["juggle the dice"])
        self.assertTrue(abilities.by_hand_parts("【AUTO】 When the moon is full, draw 1 card."))  # never triggers by itself
        self.assertTrue(abilities.by_hand_parts("【ACT】 [Juggle] Draw 1 card."))  # a cost it can't pay

    def test_inside_a_choice_and_an_ability_given_away(self):
        self.assertEqual(abilities.by_hand_parts('【AUTO】 When this card attacks, choose 1 of the following effects, and perform it. "Draw 1 card." "Juggle the dice."'), ["Juggle the dice"])
        self.assertTrue(abilities.by_hand_parts('【AUTO】 When this card attacks, this card gets the following ability until end of turn. "【AUTO】 When this card attacks, juggle the dice."'))
        self.assertTrue(abilities.by_hand_parts('【CONT】 During your turn, this card gets +1000 power and the following ability. "【AUTO】 When this card attacks, juggle the dice."'))

    def test_an_encore_given_without_its_reminder_works(self):
        ability = abilities.parse("【AUTO】 Encore [Put 1 character from your hand into your waiting room]")[0]
        self.assertEqual(ability["when"], [{"on": "leave"}])
        self.assertEqual(abilities.by_hand_parts(ability["text"]), [])
        t = Table()
        t.card(1001, text='【CONT】 During your turn, this card gets +1000 power and "【AUTO】 Encore [Put 1 character from your hand into your waiting room]".')
        card = t.seat(t.me, "C1", 1001)
        t.hand(t.card(1002))
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "waiting"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_answer", "uids": t.state["resolving"]["prompt"]["options"]})
        self.assertEqual(t.me["stage"]["C1"]["uid"], card["uid"])
        self.assertEqual(t.me["stage"]["C1"]["pos"], "rest")


class AutomatedEffectTests(TestCase):
    """The effects that used to need doing by hand, using the text printed on the real cards."""

    def setUp(self):
        self.t = Table()
        self.me = self.t.me
        self.them = self.t.them

    def play(self, text, card_type="Character", to="C2", **details):
        """Play a card with this text and start its ability. Player 2 is ours."""
        self.t.card(2000, text=text, card_type=card_type, **details)
        card = self.t.hand(2000)[0]
        self.t.refresh()
        self.t.apply(2, {"type": "move", "uid": card["uid"], "to": to})
        return card

    def fire(self, accept=True):
        self.t.apply(2, {"type": "ability_trigger", "id": self.t.state["ability_queue"][0]["id"], "accept": accept})

    def prompt(self):
        return (self.t.state.get("resolving") or {}).get("prompt")

    def answer(self, player=2, **action):
        self.t.apply(player, {"type": "ability_answer", **action})

    def done(self):
        shown = self.t.state.get("ability_show")
        if shown:
            self.t.apply(2, {"type": "ability_show_done", "id": shown["id"]})
        self.assertFalse(game.abilities_busy(self.t.state))

    def hand_cards(self, side, *pks):
        cards = [game.new_card(pk) for pk in pks]
        side["zones"]["hand"] += cards
        return cards

    def put_in(self, side, zone, *pks):
        cards = [game.new_card(pk) for pk in pks]
        side["zones"][zone] += cards
        return cards

    def test_nothing_on_the_real_cards_needs_doing_by_hand_in_these(self):
        for text in (self.RESTOCK, self.ADE, self.POLI, self.ROUGE, self.MARCIANA, self.MORI, self.MODERNIA, self.SCARLET, self.COFFIN, self.NAYUTA,
                     self.A_WORLD, self.UNBLEMISHED, self.HARRAN, self.DRAKE, self.MIRANDA, self.SUPER_HERO, self.QUENCY, self.K, self.CINDERELLA,
                     self.ISABEL, self.YUNI, self.GUILTY, self.RED_HOOD, self.TRONY):
            self.assertEqual(abilities.by_hand_parts(text), [], text)

    RESTOCK = ('【AUTO】 When this card is placed on the stage from your hand, you may perform the following effect. "Your opponent returns all cards from their stock to their deck, '
               'shuffles their deck, puts the same number of cards from the top of their deck into their stock, and you draw up to 1 card. If you drew 1 card, choose 1 card in your hand, and put it into your waiting room."')

    def test_the_opponent_rebuilds_their_stock(self):
        self.put_in(self.them, "stock", 1, 2, 3)
        before = len(self.them["zones"]["deck"])
        self.hand_cards(self.me, 7)
        self.play(self.RESTOCK)
        self.fire()
        self.assertEqual(len(self.them["zones"]["stock"]), 3)
        self.assertEqual(len(self.them["zones"]["deck"]), before)
        self.answer(value=1)  # draw 1
        self.answer(uids=[self.prompt()["options"][0]])  # so discard 1
        self.done()

    ADE = ('【AUTO】 [(1) Put 1 card from your hand into your waiting room] When this card is placed on the stage from your hand, you may pay the cost. If you do, your opponent chooses 1 climax '
           'in their waiting room, returns all cards except that card from their waiting room to their deck, and shuffles their deck.')

    def test_the_opponent_is_the_one_asked_to_choose(self):
        self.t.card(50, card_type="Climax", power=None, level=None)
        self.t.card(51)
        keep, other = self.put_in(self.them, "waiting", 50, 50)
        self.put_in(self.them, "waiting", 51)
        self.t.stock(1)
        self.hand_cards(self.me, 7)
        self.play(self.ADE)
        self.fire()
        self.answer(uids=[self.prompt()["options"][0]])  # our cost
        self.assertEqual(self.prompt()["player"], "1")
        self.assertIsNone(game.view(self.t.state, 2)["ability"]["prompt"])
        theirs = game.view(self.t.state, 1)["ability"]
        self.assertTrue(theirs["mine"])
        self.assertFalse(theirs["can_stop"])
        self.assertEqual(set(theirs["prompt"]["options"]), {keep["uid"], other["uid"]})
        with self.assertRaises(game.GameError):
            self.answer(player=2, uids=[keep["uid"]])
        self.answer(player=1, uids=[keep["uid"]])
        self.assertEqual([c["uid"] for c in self.them["zones"]["waiting"]], [keep["uid"]])
        self.done()

    def test_a_cpu_answers_when_its_the_one_asked(self):
        self.t.state["resolving"] = {"player": "1", "uid": "x", "card": 1, "text": "t", "steps": [], "ctx": {},
                                     "prompt": {"kind": "cards", "for": "it", "player": "2", "title": "t", "owner": "2", "min": 1, "max": 1,
                                                "cards": self.put_in(self.me, "waiting", 900), "options": [self.me["zones"]["waiting"][0]["uid"]]}}
        self.assertEqual(self.t.next()["type"], "ability_answer")

    POLI = ('【AUTO】 When this card is placed on the stage from your hand, perform the following action 2 times. "You may choose 1 of your opponent\'s level 1 or higher characters. '
            'If you do, your opponent chooses 1 level X or lower character in their waiting room, and exchanges them. X is equal to the level of the character you chose -1."')

    def resolve(self, *steps, it=None, it_before=None):
        me = self.t.seat(self.me, "B2", 900)
        self.t.state["resolving"] = {"player": "2", "uid": me["uid"], "card": 900, "text": "t", "prompt": None, "steps": list(steps),
                                     "ctx": {"it": it or [], "it_before": it_before or [], "source_uid": me["uid"]}}
        self.t.apply(2, {"type": "chat", "text": "."})

    def test_exchanging_stage_characters_keeps_each_ones_state_and_markers(self):
        rested = self.t.seat(self.them, "C1", self.t.card(300), pos="rest")
        standing = self.t.seat(self.them, "C3", self.t.card(301))
        self.them["markers"]["C1"] = [game.new_card(1)]
        self.resolve({"do": "exchange"}, it_before=[rested["uid"]], it=[standing["uid"]])
        self.assertEqual(self.them["stage"]["C3"]["uid"], rested["uid"])
        self.assertEqual(self.them["stage"]["C1"]["uid"], standing["uid"])
        self.assertEqual((rested["pos"], standing["pos"]), ("rest", "stand"))
        self.assertEqual((len(self.them["markers"]["C3"]), len(self.them["markers"]["C1"])), (1, 0))

    def test_a_card_coming_from_a_zone_keeps_its_own_state_not_the_old_ones(self):
        rested = self.t.seat(self.them, "C1", self.t.card(300), pos="rest")
        coming = self.put_in(self.them, "waiting", 301)[0]
        self.them["markers"]["C1"] = [game.new_card(1)]
        self.resolve({"do": "exchange"}, it_before=[rested["uid"]], it=[coming["uid"]])
        self.assertEqual(self.them["stage"]["C1"]["uid"], coming["uid"])
        self.assertEqual(coming["pos"], "stand")
        self.assertIn(rested["uid"], [c["uid"] for c in self.them["zones"]["waiting"]])
        self.assertEqual(rested["pos"], "stand")  # nothing in the waiting room is rested
        self.assertEqual(self.them["markers"]["C1"], [])

    def test_when_the_effect_names_a_state_both_take_it(self):
        one = self.t.seat(self.them, "C1", self.t.card(300), pos="rest")
        two = self.t.seat(self.them, "C3", self.t.card(301))
        self.resolve(abilities.parse("Choose 2 of your opponent's characters, and exchange them as 【REST】.")[0]["steps"][1], it=[one["uid"], two["uid"]])
        self.assertEqual((one["pos"], two["pos"]), ("rest", "rest"))
        self.assertEqual(abilities.parse("Choose 2 of your opponent's characters, and exchange them as 【STAND】.")[0]["steps"][1]["pos"], "stand")

    def test_poli_swaps_a_character_for_a_lower_one_twice(self):
        for pk, level in ((60, 2), (61, 3), (62, 1), (63, 2), (64, 3)):
            self.t.card(pk, level=level)
        first = self.t.seat(self.them, "C1", 60)
        second = self.t.seat(self.them, "C3", 61)
        one, two, three = self.put_in(self.them, "waiting", 62, 63, 64)
        self.play(self.POLI)
        self.fire()
        # Round 1: saying yes to the prompt was the "you may". First is level 2, so level 1 or lower.
        self.answer(uids=[first["uid"]])
        self.assertEqual(set(self.prompt()["options"]), {one["uid"]})
        self.answer(player=1, uids=[one["uid"]])
        # Round 2 goes by its own choice: second is level 3, so level 2 or lower, which now includes first.
        self.answer(value="yes")
        self.answer(uids=[second["uid"]])
        self.assertEqual(set(self.prompt()["options"]), {two["uid"], first["uid"]})
        self.answer(player=1, uids=[two["uid"]])
        self.assertEqual(self.them["stage"]["C1"]["uid"], one["uid"])
        self.assertEqual(self.them["stage"]["C3"]["uid"], two["uid"])
        self.assertIn(first["uid"], [c["uid"] for c in self.them["zones"]["waiting"]])
        self.done()

    ROUGE = "【AUTO】 When this card is placed on the stage from your hand, you may choose 1 card in your level and 1 card in your waiting room, and exchange them."

    def test_a_level_card_and_a_waiting_room_card_change_over(self):
        level = self.put_in(self.me, "level", 70)[0]
        waiting = self.put_in(self.me, "waiting", 71)[0]
        self.play(self.ROUGE)
        self.fire()
        self.answer(uids=[level["uid"]])
        self.answer(uids=[waiting["uid"]])
        self.assertEqual(self.me["zones"]["level"][0]["uid"], waiting["uid"])
        self.assertEqual(self.me["zones"]["waiting"][0]["uid"], level["uid"])
        self.done()

    MARCIANA = "【ACT】 [Put 1 card from your hand into your waiting room & Put this card into your waiting room] Choose 2 of your opponent's characters, and exchange them as 【STAND】."

    def test_two_enemy_characters_swap_and_stand(self):
        self.t.card(2000, text=self.MARCIANA)
        me = self.t.seat(self.me, "C2", 2000)
        self.hand_cards(self.me, 7)
        one = self.t.seat(self.them, "C1", self.t.card(80), pos="rest")
        two = self.t.seat(self.them, "C3", self.t.card(81), pos="rest")
        self.them["markers"]["C1"] = [game.new_card(1)]
        self.t.refresh()
        self.t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
        self.answer(uids=[self.prompt()["options"][0]])
        self.answer(uids=[one["uid"], two["uid"]])
        self.assertEqual((self.them["stage"]["C1"]["uid"], self.them["stage"]["C3"]["uid"]), (two["uid"], one["uid"]))
        self.assertEqual((one["pos"], two["pos"]), ("stand", "stand"))
        self.assertEqual(len(self.them["markers"]["C3"]), 1)  # its marker went with it
        self.done()

    MORI = ('【AUTO】 【CXCOMBO】 When this card is placed on the stage from your hand, you may perform the following action. "Search your deck for up to 1 "UNBREAKABLE SPHERE" or "OLD TALES", '
            'reveal it to your opponent, choose up to 1 "UNBREAKABLE SPHERE" or "OLD TALES" in your hand, reveal it to your opponent, exchange them, and shuffle your deck."')

    def test_a_climax_in_hand_for_one_in_the_deck(self):
        self.t.card(90, name="OLD TALES", card_type="Climax", power=None, level=None)
        self.t.card(91, name="UNBREAKABLE SPHERE", card_type="Climax", power=None, level=None)
        in_deck = self.put_in(self.me, "deck", 90)[0]
        in_hand = self.hand_cards(self.me, 91)[0]
        self.play(self.MORI)
        self.fire()
        self.answer(uids=[in_deck["uid"]])
        self.answer(uids=[in_hand["uid"]])
        self.assertIn(in_deck["uid"], [c["uid"] for c in self.me["zones"]["hand"]])
        self.assertEqual(sum(c["card"] == 91 for c in self.me["zones"]["deck"]), 1)
        self.assertNotIn(in_deck["uid"], [c["uid"] for c in self.me["zones"]["deck"]])
        self.done()

    MODERNIA = ('【AUTO】 When this card is placed on the stage from your hand, choose 1 of your characters, and that character gets the following ability until end of turn. '
                '"【AUTO】 When this card\'s battle opponent becomes 【REVERSE】, choose 1 of your other characters, 【REST】 it, and move it to an open position of your back stage."')

    def test_moving_to_an_open_back_slot_keeps_markers_and_rest(self):
        other = self.t.seat(self.me, "C1", self.t.card(100))
        self.me["markers"]["C1"] = [game.new_card(1)]
        self.t.seat(self.me, "B1", self.t.card(101))
        self.t.state["resolving"] = {"player": "2", "uid": "src", "card": 1, "text": "t", "ctx": {}, "prompt": None, "steps": [
            {"do": "choose", "zone": "stage", "filter": {"any": [{"type": "character"}]}, "min": 1, "max": 1}, {"do": "pos_it", "pos": "rest"},
            {"do": "place", "open": True, "zone": "back", "keep_pos": True}]}
        self.t.apply(2, {"type": "chat", "text": "."})
        self.answer(uids=[other["uid"]])
        self.assertEqual([o["value"] for o in self.prompt()["options"]], ["B2"])
        self.answer(value="B2")
        self.assertEqual(self.me["stage"]["B2"]["uid"], other["uid"])
        self.assertIsNone(self.me["stage"]["C1"])
        self.assertEqual(other["pos"], "rest")
        self.assertEqual(len(self.me["markers"]["B2"]), 1)
        self.done()

    SCARLET = "【AUTO】 At the beginning of your opponent's attack phase, you may move this card to an open position of your center stage with a character facing this card."

    def test_moving_only_where_a_character_faces_it(self):
        self.t.card(2000, text=self.SCARLET)
        me = self.t.seat(self.me, "B1", 2000)
        self.t.seat(self.them, game.OPPOSITE["C3"], self.t.card(110))
        self.t.state["turn"] = "1"
        self.t.refresh()
        self.t.apply(1, {"type": "phase", "phase": "attack"})
        self.assertEqual(self.t.state["ability_queue"][0]["player"], "2")
        self.fire()
        self.assertEqual([o["value"] for o in self.prompt()["options"]], ["C3"])
        self.answer(value="C3")
        self.assertEqual(self.me["stage"]["C3"]["uid"], me["uid"])
        self.done()

    COFFIN = ('【AUTO】 【CXCOMBO】 During your climax phase, when "OLD TALES" is placed on your climax area, if this card is 【STAND】, you may perform the following action. '
              '"Choose 1 ""Glass Slippers. Full Contact" Cinderella" in your hand or marker underneath this card, put it in any position of your stage, and put this card into your waiting room."')

    def test_a_card_from_the_hand_or_a_marker_takes_the_stage(self):
        self.t.card(120, name="“Glass Slippers. Full Contact” Cinderella")
        self.t.card(121, name="OLD TALES", card_type="Climax", power=None, level=None)
        self.t.card(2000, text=self.COFFIN)
        me = self.t.seat(self.me, "C1", 2000)
        marker = game.new_card(120)
        self.me["markers"]["C1"] = [marker]
        cx = self.hand_cards(self.me, 121)[0]
        self.t.state["phase"] = "climax"
        self.t.refresh()
        self.t.apply(2, {"type": "move", "uid": cx["uid"], "to": "climax"})
        self.fire()
        self.assertEqual(self.prompt()["options"], [marker["uid"]])
        self.answer(uids=[marker["uid"]])
        self.answer(value="C2")
        self.assertEqual(self.me["stage"]["C2"]["uid"], marker["uid"])
        self.assertIn(me["uid"], [c["uid"] for c in self.me["zones"]["waiting"]])
        self.done()

    NAYUTA = ('【AUTO】 【CXCOMBO】 Memory When this card attacks, if "GODDESS FALL" is in your climax area, and your hand has 5 or less cards, choose 1 of the following effects, and perform it. '
              '"Deal 1 damage to your opponent." "[(2) Put 3 cards from your hand into your waiting room] You may pay the cost. If you do, put all of your "Two Thousand Replicas, Nayuta" from your memory face up underneath this card in any order as markers, '
              'and deal 2 damage X times to your opponent. X is equal to 1 if there are 3 or less markers underneath this card, 2 if there are 4 or 5 markers underneath this card, and 3 if there are 6 or more markers underneath this card." (Damage may be canceled)')

    def test_memory_cards_become_markers_and_damage_repeats_by_how_many(self):
        steps = abilities.parse(self.NAYUTA)[0]["steps"][0]["options"][1]["steps"][0]["then"]
        self.assertEqual([s["do"] for s in steps], ["memory_to_markers", "damage_times"])
        self.t.card(130, name="Two Thousand Replicas, Nayuta")
        self.put_in(self.me, "memory", *[130] * 4, 131)
        me = self.t.seat(self.me, "C1", 2000)
        self.t.card(2000)
        before = len(self.them["zones"]["deck"])
        self.t.state["resolving"] = {"player": "2", "uid": me["uid"], "card": 2000, "text": "t", "ctx": {"source_uid": me["uid"]}, "prompt": None, "steps": steps}
        self.t.apply(2, {"type": "chat", "text": "."})
        self.assertEqual(len(self.me["markers"]["C1"]), 4)
        self.assertEqual([c["card"] for c in self.me["zones"]["memory"]], [131])
        self.assertEqual(before - len(self.them["zones"]["deck"]), 4)  # 4 markers: 2 damage, 2 times
        self.done()

    def test_the_marker_tiers(self):
        spec = abilities.parse_x("1 if there are 3 or less markers underneath this card, 2 if there are 4 or 5 markers underneath this card, and 3 if there are 6 or more markers underneath this card", [])
        me = self.t.seat(self.me, "C1", 900)
        for count, expected in ((0, 1), (3, 1), (4, 2), (5, 2), (6, 3), (9, 3)):
            self.me["markers"]["C1"] = [game.new_card(1) for _ in range(count)]
            self.assertEqual(game.x_value(spec, self.t.state, "2", None, {"source_uid": me["uid"]}, game.SimpleNamespace(info=self.t.info)), expected, count)

    A_WORLD = ('【AUTO】 Memory If this card is in your memory, at the beginning of your climax phase, you may choose 1 of your "Rapi: Red Hood" without markers, and put this card face up underneath that character as a marker. '
               'If you do, that character gets +3000 power and the following ability until end of turn. "【AUTO】 [(1) Put 2 cards from your hand into your waiting room] At the end of this card\'s attack, you may pay the cost. If you do, deal 2 damage to your opponent." (Damage may be canceled)')

    def test_from_memory_onto_a_character_without_markers(self):
        self.t.card(140, name="Rapi: Red Hood")
        rapi = self.t.seat(self.me, "C1", 140)
        taken = self.t.seat(self.me, "C2", 140)
        self.me["markers"]["C2"] = [game.new_card(1)]
        self.t.card(2000, text=self.A_WORLD, card_type="Event")
        me = self.put_in(self.me, "memory", 2000)[0]
        self.t.refresh()
        self.t.apply(2, {"type": "phase", "phase": "climax"})
        self.fire()
        self.assertEqual(self.prompt()["options"], [rapi["uid"]])  # not the one with a marker
        self.answer(uids=[rapi["uid"]])
        self.assertEqual(self.me["markers"]["C1"][0]["uid"], me["uid"])
        self.done()
        self.t.refresh()
        self.assertEqual(self.t.state["stats"][rapi["uid"]]["power"], 4000)
        self.assertEqual(taken["pos"], "stand")

    UNBLEMISHED = '[(2)] If your level is 3 or higher, and you have a ""Glass Slippers. Full Contact" Cinderella" with 1 or more markers, you may pay the cost. If you do, deal either 2 or 4 damage to your opponent. (Damage may be canceled)'

    def test_a_choice_of_damage_only_with_a_marked_character(self):
        self.t.card(150, name="“Glass Slippers. Full Contact” Cinderella")
        self.t.seat(self.me, "C1", 150)
        self.t.level(3)
        self.t.stock(2)
        before = len(self.them["zones"]["deck"])
        self.play(self.UNBLEMISHED, card_type="Event", to="resolution")
        self.fire()
        self.t.apply(2, {"type": "chat", "text": "."})
        self.assertIsNone(self.prompt())  # no marker yet, so it comes to nothing
        self.done()
        self.me["markers"]["C1"] = [game.new_card(1)]
        self.t.stock(2)
        self.t.card(2001, text=self.UNBLEMISHED, card_type="Event")
        card = self.t.hand(2001)[0]
        self.t.refresh()
        self.t.apply(2, {"type": "move", "uid": card["uid"], "to": "resolution"})
        self.fire()
        self.answer(value="yes")
        self.assertEqual([o["value"] for o in self.prompt()["options"]], [4, 2])
        self.answer(value=2)
        self.assertEqual(before - len(self.them["zones"]["deck"]), 2)
        self.done()

    HARRAN = ('【AUTO】 [Put 1 climax from your hand into your waiting room & Put this card into your waiting room] When your other 《NIKKE》 character is frontal attacked, if you have another 《NIKKE》 character, '
              'you may pay the cost. If you do, that character cannot become 【REVERSE】 until end of turn.')

    def test_a_protected_character_isnt_reversed_by_the_battle(self):
        self.t.card(160, traits="NIKKE", power=1000)
        self.t.card(161, traits="NIKKE", power=9000)
        self.t.card(162, card_type="Climax", power=None, level=None)
        self.t.card(2000, text=self.HARRAN, traits="NIKKE")
        protected = self.t.seat(self.me, "C2", 160)
        self.t.seat(self.me, "B1", 2000)
        self.t.seat(self.me, "C1", 160)
        self.hand_cards(self.me, 162)
        attacker = self.t.seat(self.them, "C2", 161)
        self.t.state.update(turn="1", phase="attack", attack={"step": "declare"})
        self.t.refresh()
        self.t.apply(1, {"type": "attack", "uid": attacker["uid"], "kind": "front"})
        self.fire()
        self.answer(uids=[self.prompt()["options"][0]])
        self.done_show()
        if self.t.state["attack"]["step"] == "counter":
            self.t.apply(2, {"type": "no_counter"})
        self.assertEqual(protected["pos"], "stand")
        self.assertIn("neither reversed", " ".join(e["text"] for e in self.t.state["log"]))

    def done_show(self):
        shown = self.t.state.get("ability_show")
        if shown:
            self.t.apply(2, {"type": "ability_show_done", "id": shown["id"]})

    DRAKE = ('【AUTO】 When this card or this card\'s battle opponent becomes 【REVERSE】, that character cannot use "【AUTO】 Encore" until end of turn. (The "【AUTO】 Encore [(3)]" rule cannot be used either)')

    def test_a_reversed_character_cant_be_encored_this_turn(self):
        enemy = self.t.seat(self.them, "C2", self.t.card(170, power=500, text="【AUTO】 Encore [Put 1 character from your hand into your waiting room] (When this card is put into your waiting room from the stage, you may pay the cost. If you do, return this card to its previous stage position as 【REST】)"))
        self.t.card(2000, text=self.DRAKE, power=5000)
        me = self.t.seat(self.me, "C2", 2000)
        self.t.state.update(phase="attack", attack={"step": "declare"})
        self.t.refresh()
        self.t.apply(2, {"type": "attack", "uid": me["uid"], "kind": "front"})
        if self.t.state["attack"]["step"] == "counter":
            self.t.apply(1, {"type": "no_counter"})
        self.assertEqual(enemy["pos"], "reverse")
        self.fire()
        self.done_show()
        self.assertEqual(game.view(self.t.state, 1)["no_encore"], [enemy["uid"]])
        self.put_in(self.them, "stock", 1, 2, 3)
        with self.assertRaises(game.GameError):
            self.t.apply(1, {"type": "encore", "uid": enemy["uid"]})
        self.hand_cards(self.them, 1)
        self.t.apply(1, {"type": "move", "uid": enemy["uid"], "to": "waiting"})
        self.assertFalse(self.t.state.get("ability_queue"))  # its own Encore doesn't come up either

    def test_the_cpu_wont_try_to_encore_it(self):
        t = Table()
        t.state["phase"] = "encore"
        card = t.seat(t.me, "C1", t.card(1001, level=2, power=5000), pos="reverse")
        t.stock(9)
        t.state["buffs"] = [{"uid": card["uid"], "status": "no_encore", "expires": 99}]
        self.assertEqual(t.next()["type"], "move")

    MIRANDA = ('【AUTO】 When this card is placed on the stage from your hand, all players put the top card of their deck into their waiting room. If the level of the card put into your waiting room by this effect is higher than your opponent\'s, you may draw 1 card. (Climax are regarded as level 0)')

    def test_both_players_mill_and_the_higher_level_draws(self):
        self.t.card(180, level=2)
        self.t.card(181, level=1)
        self.me["zones"]["deck"][-1]["card"] = 180
        self.them["zones"]["deck"][-1]["card"] = 181
        self.play(self.MIRANDA)
        self.fire()
        self.assertEqual(self.me["zones"]["waiting"][-1]["card"], 180)
        self.assertEqual(self.them["zones"]["waiting"][-1]["card"], 181)
        self.assertEqual(self.prompt()["for"], "may")
        self.answer(value="yes")
        self.done()

    def test_no_draw_when_its_not_higher(self):
        self.t.card(180, level=1)
        self.t.card(181, level=1)
        self.me["zones"]["deck"][-1]["card"] = 180
        self.them["zones"]["deck"][-1]["card"] = 181
        self.play(self.MIRANDA)
        self.fire()
        self.assertIsNone(self.prompt())
        self.done()

    SUPER_HERO = ('[(2) Put 1 "Protecting Your Hope, Laplace" and 1 "Maxwell - Mechanic White" and 1 "The Greatest Villain, Drake" from your hand into your waiting room] You may pay the cost. '
                  'If you do, your opponent puts 12 cards from the top of their deck into their waiting room, and you deal 4 damage to your opponent. (Damage may be canceled)')

    def test_a_cost_naming_three_cards_then_a_big_mill(self):
        for pk, name in ((190, "Protecting Your Hope, Laplace"), (191, "Maxwell - Mechanic White"), (192, "The Greatest Villain, Drake")):
            self.t.card(pk, name=name)
        self.hand_cards(self.me, 190, 191, 192)
        self.t.stock(2)
        before = len(self.them["zones"]["deck"])
        self.play(self.SUPER_HERO, card_type="Event", to="resolution")
        self.fire()
        for _ in range(3):
            self.assertEqual(len(self.prompt()["options"]), 1)
            self.answer(uids=self.prompt()["options"])
        self.assertEqual(len(self.t.me["zones"]["stock"]), 0)
        self.assertEqual(before - len(self.them["zones"]["deck"]), 12 + 4)
        self.done()

    QUENCY = '【AUTO】 When you use this card\'s "Backup", if you have a 《NIKKE》 character, put 3 cards from the top of your or your opponent\'s deck into the waiting room.'

    def test_choosing_whose_deck_is_milled(self):
        steps = abilities.parse(self.QUENCY)[0]["steps"]
        me = self.t.seat(self.me, "C1", 900)
        before = len(self.them["zones"]["deck"])
        self.t.state["resolving"] = {"player": "2", "uid": me["uid"], "card": 900, "text": "t", "ctx": {}, "prompt": None, "steps": steps}
        self.t.apply(2, {"type": "chat", "text": "."})
        self.assertEqual({o["value"] for o in self.prompt()["options"]}, {"me", "opp"})
        self.answer(value="opp")
        self.assertEqual(before - len(self.them["zones"]["deck"]), 3)
        self.assertEqual(len(self.them["zones"]["waiting"]), 3)

    K = ('【AUTO】 When this card\'s battle opponent becomes 【REVERSE】, perform the following effects 1 time in any order. "You may put the top card of your opponent\'s clock into their waiting room. '
         'If you do, put that character into your opponent\'s clock." "Choose 1 《NIKKE》 character in your waiting room, return it to your hand, choose 1 card in your hand, and put it into your waiting room."')

    def test_both_effects_in_the_order_chosen(self):
        steps = abilities.parse(self.K)[0]["steps"]
        self.assertEqual(steps[0]["do"], "any_order")
        me = self.t.seat(self.me, "C1", 900)
        enemy = self.t.seat(self.them, "C2", 900)
        self.put_in(self.them, "clock", 1)
        self.t.state["resolving"] = {"player": "2", "uid": me["uid"], "card": 900, "text": "t", "ctx": {"that": enemy["uid"]}, "prompt": None, "steps": steps}
        self.t.apply(2, {"type": "chat", "text": "."})
        self.assertEqual(len(self.prompt()["options"]), 2)
        self.answer(value=1)  # the second one first; nothing to choose, so on to the first
        self.assertEqual(self.prompt()["for"], "may")
        self.answer(value="yes")
        self.assertEqual(self.them["zones"]["clock"][-1]["uid"], enemy["uid"])
        self.assertIsNone(self.them["stage"]["C2"])

    CINDERELLA = ('【AUTO】 When this card attacks, this card gets the following ability until the end of your opponent\'s next turn. "【AUTO】 When the character facing this card attacks, look at up to 2 cards from the top of your deck, '
                  'choose up to 1 card from among them, put it face down underneath this card as a marker, and put the rest on the top of your deck in any order or into your waiting room."')

    def test_a_marker_from_the_top_and_a_choice_for_the_rest(self):
        ability = abilities.parse(self.CINDERELLA)[0]["steps"][0]["grant"][0]
        steps = abilities.parse(ability)[0]["steps"]
        me = self.t.seat(self.me, "C1", 900)
        self.t.state["resolving"] = {"player": "2", "uid": me["uid"], "card": 900, "text": "t", "ctx": {}, "prompt": None, "steps": steps}
        self.t.apply(2, {"type": "chat", "text": "."})
        self.answer(value=2)
        chosen = self.prompt()["options"][0]
        other = self.prompt()["options"][1]
        self.answer(uids=[chosen])
        self.assertEqual(self.me["markers"]["C1"][0]["uid"], chosen)
        self.assertTrue(self.me["markers"]["C1"][0]["face_down"])
        self.assertEqual([c["uid"] for c in self.prompt()["cards"]], [other])  # the marker isn't part of the rest
        self.answer(value="waiting")
        self.assertEqual(self.me["zones"]["waiting"][-1]["uid"], other)

    ISABEL = '【AUTO】 When this card becomes 【REVERSE】, if the level of this card\'s battle opponent is higher than your opponent\'s level, you may put that character at the bottom of your opponent\'s deck.'

    def test_comparing_a_battle_opponents_level_to_its_player(self):
        self.t.card(2000, text=self.ISABEL, power=500)
        self.t.card(210, level=2, power=9000)
        me = self.t.seat(self.me, "C2", 2000)
        attacker = self.t.seat(self.them, "C2", 210)
        self.t.state.update(turn="1", phase="attack", attack={"step": "declare"})
        self.t.refresh()
        self.t.apply(1, {"type": "attack", "uid": attacker["uid"], "kind": "front"})
        if self.t.state["attack"]["step"] == "counter":
            self.t.apply(2, {"type": "no_counter"})
        self.assertEqual(me["pos"], "reverse")
        self.fire()
        self.assertEqual(self.them["zones"]["deck"][0]["uid"], attacker["uid"])  # level 2 against a player at level 0

    def test_not_when_the_level_isnt_higher(self):
        self.t.card(2000, text=self.ISABEL, power=500)
        self.t.card(210, level=2, power=9000)
        self.t.seat(self.me, "C2", 2000)
        attacker = self.t.seat(self.them, "C2", 210)
        self.put_in(self.them, "level", 1, 2)
        self.t.state.update(turn="1", phase="attack", attack={"step": "declare"})
        self.t.refresh()
        self.t.apply(1, {"type": "attack", "uid": attacker["uid"], "kind": "front"})
        if self.t.state["attack"]["step"] == "counter":
            self.t.apply(2, {"type": "no_counter"})
        self.assertFalse(self.t.state.get("ability_queue"))

    YUNI = ('【AUTO】 [Put 1 card from your hand into your waiting room & Put 1 character from your stage into your waiting room] When you use this card\'s "Backup", you may pay the cost. '
            'If you do, choose 1 of your opponent\'s characters with level higher than your opponent\'s level, and return it to their hand.')

    def test_only_characters_above_their_players_level(self):
        steps = abilities.parse(self.YUNI)[0]["steps"][0]["then"]
        low = self.t.seat(self.them, "C1", self.t.card(220, level=1))
        high = self.t.seat(self.them, "C2", self.t.card(221, level=2))
        self.put_in(self.them, "level", 1)
        me = self.t.seat(self.me, "C1", 900)
        self.t.state["resolving"] = {"player": "2", "uid": me["uid"], "card": 900, "text": "t", "ctx": {}, "prompt": None, "steps": steps}
        self.t.apply(2, {"type": "chat", "text": "."})
        self.assertEqual(self.prompt()["options"], [high["uid"]])
        self.answer(uids=[high["uid"]])
        self.assertIn(high["uid"], [c["uid"] for c in self.them["zones"]["hand"]])
        self.assertEqual(self.them["stage"]["C1"]["uid"], low["uid"])

    GUILTY = ('【AUTO】 [Put 1 《NIKKE》 character from your hand into your waiting room] When this card is placed on the stage from your hand, you may pay the cost. If you do, choose 2 level 2 or lower characters in your opponent\'s center stage. '
              'If you chose 2 characters, choose 1 of the following effects, and perform it. "Choose the character with the lowest power from among those cards, and put it into your opponent\'s waiting room." '
              '"If all of the characters from among those cards have the same power, put all of the characters from among those cards into your opponent\'s waiting room."')

    def guilty(self, one, two):
        self.t.card(230, level=1, power=one)
        self.t.card(231, level=1, power=two)
        first = self.t.seat(self.them, "C1", 230)
        second = self.t.seat(self.them, "C2", 231)
        self.t.card(232, traits="NIKKE")
        self.hand_cards(self.me, 232)
        self.play(self.GUILTY)
        self.fire()
        self.answer(uids=[self.prompt()["options"][0]])
        self.answer(uids=[first["uid"], second["uid"]])
        return first, second

    def test_the_lower_power_goes(self):
        first, second = self.guilty(1000, 2000)
        self.answer(value=0)
        self.assertEqual([c["uid"] for c in self.them["zones"]["waiting"]], [first["uid"]])
        self.assertEqual(self.them["stage"]["C2"]["uid"], second["uid"])

    def test_both_go_if_theyre_equal(self):
        first, second = self.guilty(1000, 1000)
        self.answer(value=1)
        self.assertEqual({c["uid"] for c in self.them["zones"]["waiting"]}, {first["uid"], second["uid"]})

    def test_neither_by_the_second_effect_if_they_arent(self):
        self.guilty(1000, 2000)
        self.answer(value=1)
        self.assertEqual(self.them["zones"]["waiting"], [])

    RED_HOOD = ('【AUTO】 【CXCOMBO】 1/TURN@ When damage dealt by this card is canceled, if "FOOTSTEP, WALK, RUN" is in your climax area, reveal the top 4 cards of your deck, shuffle your deck, and deal 4 damage X times to your opponent. '
                'X is equal to the number of climax among those cards. (Return the revealed card to its original place. Damage may be canceled)')

    def test_damage_for_each_climax_revealed(self):
        steps = abilities.parse(self.RED_HOOD)[0]["steps"]
        self.t.card(240, card_type="Climax", power=None, level=None)
        self.put_in(self.me, "deck", 240, 1, 240, 2)
        me = self.t.seat(self.me, "C1", 900)
        cards_before = len(self.me["zones"]["deck"])
        before = len(self.them["zones"]["deck"])
        self.t.state["resolving"] = {"player": "2", "uid": me["uid"], "card": 900, "text": "t", "ctx": {"source_uid": me["uid"]}, "prompt": None, "steps": steps}
        self.t.apply(2, {"type": "chat", "text": "."})
        self.assertEqual(before - len(self.them["zones"]["deck"]), 8)  # 2 climaxes: 4 damage, twice
        self.assertEqual(len(self.me["zones"]["deck"]), cards_before)  # revealed, not taken

    TRONY = "【AUTO】 If this card is in your waiting room, at the beginning of your first turn, you may put this card into your stock."

    def test_a_trigger_on_the_first_turn_only(self):
        self.t.card(2000, text=self.TRONY)
        me = self.put_in(self.me, "waiting", 2000)[0]
        self.t.state.update(turn_number=2, phase="stand")
        self.t.refresh()
        self.t.apply(2, {"type": "phase", "phase": "draw"})
        self.fire()
        self.done_show()
        self.assertIn(me["uid"], [c["uid"] for c in self.me["zones"]["stock"]])

    def test_not_on_a_later_turn(self):
        self.t.card(2000, text=self.TRONY)
        self.put_in(self.me, "waiting", 2000)
        self.t.state.update(turn_number=5, phase="stand")
        self.t.refresh()
        self.t.apply(2, {"type": "phase", "phase": "draw"})
        self.assertFalse(self.t.state.get("ability_queue"))


class NoBackupTests(TestCase):
    TEXT = '【CONT】 During this card\'s battle, all players cannot play "Backup" from their hands.'
    BACKUP = "【ACT】 【COUNTER】 Backup 3000, Level 0 [(0) Put this card from your hand into your waiting room]"
    EVENT = "【COUNTER】 Draw 1 card."

    def attack(self, kind="front", text=TEXT, power=9000, hand=(), opposing=True):
        """Player 2 attacks with a card having this text; player 1 holds these cards."""
        t = Table()
        t.card(400, text=self.BACKUP, power=1000)
        t.card(401, text=self.EVENT, card_type="Event", power=None)
        t.card(2000, text=text, power=power)
        me = t.seat(t.me, "C2", 2000)
        if opposing:
            self.defender = t.seat(t.them, "C2", t.card(1, power=1000))
        self.held = [game.new_card(pk) for pk in hand]
        t.them["zones"]["hand"] = self.held
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": me["uid"], "kind": kind})
        return t

    def test_it_is_read_from_the_card(self):
        self.assertTrue(abilities.parse(self.TEXT)[0]["no_backup"])
        self.assertFalse(abilities.parse("【CONT】 During your turn, this card gets +1000 power.")[0].get("no_backup"))

    def test_the_backup_step_is_skipped(self):
        t = self.attack(hand=(400,))
        self.assertEqual(t.state["attack"], {"step": "declare"})  # straight through damage and the battle
        self.assertEqual(self.defender["pos"], "reverse")
        self.assertIn(self.held[0]["uid"], [c["uid"] for c in t.them["zones"]["hand"]])
        self.assertTrue(any("no Backups" in e["text"] for e in t.state["log"]))

    def test_the_log_doesnt_give_away_the_hand(self):
        with_backup = [e["text"] for e in self.attack(hand=(400,)).state["log"] if "Backup" in e["text"]]
        without = [e["text"] for e in self.attack(hand=()).state["log"] if "Backup" in e["text"]]
        self.assertEqual(with_backup, without)

    def test_without_that_text_the_step_comes_up(self):
        t = self.attack(text="", hand=(400,))
        self.assertEqual(t.state["attack"]["step"], "counter")

    def test_a_counter_thats_not_a_backup_can_still_be_played(self):
        t = self.attack(hand=(400, 401))
        self.assertEqual(t.state["attack"]["step"], "counter")
        self.assertEqual(t.state["attack"]["counters"], [self.held[1]["uid"]])
        with self.assertRaises(game.GameError):  # the page doesn't offer the backup, and the server won't take it
            t.apply(1, {"type": "counter", "uid": self.held[0]["uid"]})
        t.apply(1, {"type": "counter", "uid": self.held[1]["uid"]})

    def test_a_side_attack_isnt_a_battle(self):
        t = self.attack(kind="side", hand=(400,))
        self.assertEqual(t.state["attack"]["step"], "counter")
        self.assertFalse(any("no Backups" in e["text"] for e in t.state["log"]))

    def defended_by(self, text):
        """Player 2 front attacks a defender with this text, while player 1 holds a Backup."""
        t = Table()
        t.card(400, text=self.BACKUP, power=1000)
        attacker = t.seat(t.me, "C2", t.card(2001, power=5000))
        t.seat(t.them, "C2", t.card(2000, text=text, power=1000))
        t.them["zones"]["hand"] = [game.new_card(400)]
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": attacker["uid"], "kind": "front"})
        return t

    def test_it_also_counts_when_that_card_is_defending(self):
        t = self.defended_by(self.TEXT)
        self.assertEqual(t.state["attack"], {"step": "declare"})
        self.assertEqual(t.them["stage"]["C2"]["pos"], "reverse")
        self.assertTrue(any("no Backups" in e["text"] for e in t.state["log"]))
        self.assertEqual(len(t.them["zones"]["hand"]), 1)  # the Backup stays in hand

    def test_a_defender_without_it_can_be_backed_up(self):
        self.assertEqual(self.defended_by("").state["attack"]["step"], "counter")

    def test_it_only_counts_for_the_characters_in_the_battle(self):
        t = Table()
        t.card(400, text=self.BACKUP)
        attacker = t.seat(t.me, "C2", t.card(2001, power=5000))
        t.seat(t.me, "C1", t.card(2000, text=self.TEXT))
        t.seat(t.them, "C2", t.card(1, power=1000))
        t.them["zones"]["hand"] = [game.new_card(400)]
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": attacker["uid"], "kind": "front"})
        self.assertEqual(t.state["attack"]["step"], "counter")

    def test_the_cpu_is_held_to_it_too(self):
        t = Table()
        t.card(400, text=self.BACKUP, power=1000)
        t.card(2000, text=self.TEXT, power=9000)
        attacker = t.seat(t.them, "C2", 2000)
        defender = t.seat(t.me, "C2", t.card(1001, power=1000))
        t.hand(400)
        t.state.update(turn="1", phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(1, {"type": "attack", "uid": attacker["uid"], "kind": "front"})
        self.assertEqual(defender["pos"], "reverse")


class UnusualCardTextTests(TestCase):
    """New sets have wording nothing here has seen. None of it may ever stop a page or a game."""

    def test_a_cost_that_never_closes(self):
        for text in ("【AUTO】 [(1) Put 1 card from your hand into your waiting room When this card attacks, draw 1 card.",
                     "【ACT】 [【REST】 this card Draw 1 card."):
            self.assertTrue(abilities.by_hand_parts(text), text)

    def test_marker_tiers_with_no_top_tier(self):
        text = '【AUTO】 When this card attacks, deal 2 damage X times to your opponent. X is equal to 1 if there are 3 or less markers underneath this card.'
        self.assertTrue(abilities.by_hand_parts(text))

    def test_a_line_that_crashes_the_reader_becomes_a_step_by_hand(self):
        original = abilities.parse_auto
        abilities.parse_auto = lambda *a: 1 / 0
        abilities.parse_cached.cache_clear()
        try:
            with self.assertLogs("weiss.abilities", "ERROR"):
                parsed = abilities.parse("【AUTO】 When this card attacks, draw 1 card.\n【CONT】 During your turn, this card gets +1000 power.")
            self.assertEqual(parsed[0]["steps"][0]["do"], "manual")
            self.assertIsNone(parsed[0]["when"])
            self.assertEqual(parsed[1]["effects"][0]["power"], 1000)  # the rest of the card still works
        finally:
            abilities.parse_auto = original
            abilities.parse_cached.cache_clear()

    def test_the_cpu_tab_survives_such_a_card(self):
        staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.client.force_login(staff)
        Card.objects.create(serial_number="ODD/1", name="Odd", expansion="E", expansion_id=9, card_type="Character", level=0,
                            description="【AUTO】 [(1) Put 1 card from your hand into your waiting room When this card attacks, draw 1 card.")
        self.assertEqual(self.client.get(reverse("weiss:cpu_home")).status_code, 200)
        page = self.client.get(reverse("weiss:cpu_excluded"))
        self.assertEqual(page.status_code, 200)
        self.assertEqual([c["name"] for c in page.context["excluded"]], ["Odd"])

    def test_a_game_survives_such_a_card(self):
        t = Table()
        card = t.hand(t.card(2000, text="【AUTO】 [(1) Put 1 card from your hand When this card attacks, draw 1 card.", power=3000))[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        self.assertEqual(t.me["stage"]["C1"]["uid"], card["uid"])
        self.assertTrue(t.state["acts"]["2"][card["uid"]])  # it can still be started by hand


class RunTogetherAbilitiesTests(TestCase):
    TEXT = ('【CONT】 Your other character in the middle position of your center stage gets the following ability. "【AUTO】 At the beginning of your opponent\'s draw phase, reveal the top card of your deck. '
            'If that card is level 2 or higher, you may return this card to your hand." (Climax are regarded as level -. Return the revealed card to its original place)'
            '【ACT】 【CXCOMBO】 Brainstorm [(1) 【REST】 this card] Flip over 5 cards from the top of your deck, and put them into your waiting room. '
            'For each "Superstar\'s Acting" or "Wound-shifting Scabbard" revealed among those cards, choose up to 1 character in your waiting room, and return it to your hand.')

    def test_two_abilities_on_one_line_are_read_apart(self):
        cont, act = abilities.parse(self.TEXT)
        self.assertEqual((cont["kind"], act["kind"]), ("cont", "act"))
        self.assertEqual(cont["effects"][0]["target"]["type"], "middle")
        self.assertEqual(abilities.parse(cont["effects"][0]["grant"][0])[0]["when"], [{"on": "phase", "phase": "draw", "whose": "opp"}])
        self.assertEqual([s["do"] for s in act["steps"]], ["flip", "move_it", "for_each"])
        self.assertEqual(abilities.by_hand_parts(self.TEXT), [])

    def test_a_tag_in_the_middle_of_a_sentence_doesnt_split(self):
        for text in ("【AUTO】 When your opponent uses an 【ACT】, this card gets +1500 power until end of turn.",
                     '【AUTO】 [(1)] When this card is placed on the stage from your hand or by the 【ACT】 effect of "Viper", you may pay the cost. If you do, draw 1 card.',
                     "【ACT】 【COUNTER】 Backup 2000, Level 1 [(1) Put this card from your hand into your waiting room] (Choose 1 of your characters that is being frontal attacked, and that character gets +2000 power until end of turn)",
                     '【AUTO】 When this card attacks, this card gets "【AUTO】 Encore [(3)]" until end of turn.'):
            self.assertEqual(len(abilities.parse(text)), 1, text)

    def test_every_tag_after_a_full_stop_starts_a_new_ability(self):
        self.assertEqual(len(abilities.parse("【CONT】 During your turn, this card gets +1000 power.【AUTO】 When this card attacks, draw 1 card.")), 2)

    def table(self):
        t = Table()
        t.card(500, name="Superstar's Acting", card_type="Climax", power=None, level=None)
        t.card(501)
        t.card(2000, text=self.TEXT)
        return t

    def test_the_brainstorm_works_from_the_button(self):
        t = self.table()
        me = t.seat(t.me, "C1", 2000)
        t.stock(1)
        t.me["zones"]["deck"][-5:] = [game.new_card(pk) for pk in (501, 500, 501, 501, 501)]
        keep = game.new_card(501)
        t.me["zones"]["waiting"].append(keep)
        t.refresh()
        row = t.state["acts"]["2"][me["uid"]][0]
        self.assertIsNone(row["why"])
        t.apply(2, {"type": "activate", "uid": me["uid"], "index": row["index"]})
        self.assertEqual(me["pos"], "rest")
        self.assertEqual(len(t.me["zones"]["waiting"]), 7)  # 5 flipped, 1 paid, and it was there
        prompt = t.state["resolving"]["prompt"]  # one of them's the climax it names: one character back
        self.assertEqual(prompt["max"], 1)
        t.apply(2, {"type": "ability_answer", "uids": [keep["uid"]]})
        self.assertIn(keep["uid"], [c["uid"] for c in t.me["zones"]["hand"]])

    def test_the_cx_combo_line_is_found_for_a_cpu(self):
        t = self.table()
        mind = cpu.Mind(t.state, "2", t.info, cpu.Temper(), random.Random(1))
        card = t.seat(t.me, "C1", 2000)
        self.assertFalse(mind.combo_live(card))
        t.hand(500)
        self.assertTrue(mind.combo_live(card))

    def test_the_ability_it_gives_triggers_in_the_opponents_draw_phase(self):
        t = self.table()
        t.seat(t.me, "C1", 2000)
        middle = t.seat(t.me, "C2", t.card(502))
        t.card(503, level=2)
        t.me["zones"]["deck"][-1]["card"] = 503
        t.state.update(turn="1", phase="stand", turn_number=5)
        t.refresh()
        t.apply(1, {"type": "phase", "phase": "draw"})
        entry = t.state["ability_queue"][0]
        self.assertEqual((entry["player"], entry["uid"]), ("2", middle["uid"]))
        t.apply(2, {"type": "ability_trigger", "id": entry["id"], "accept": True})
        t.apply(2, {"type": "ability_answer", "value": "yes"})
        self.assertIn(middle["uid"], [c["uid"] for c in t.me["zones"]["hand"]])


class TriggerCheckShowTests(TestCase):
    def attack(self, text="", trigger=""):
        t = Table()
        t.card(600, trigger=trigger, card_type="Climax" if trigger == "comeback" else "Character")
        t.me["zones"]["deck"][-1]["card"] = 600
        me = t.seat(t.me, "C2", t.card(2000, text=text))
        t.me["zones"]["waiting"].append(game.new_card(2001))
        t.card(2001)
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": me["uid"], "kind": "direct"}, show_checks=True)
        return t

    def test_both_players_see_the_check_even_with_no_trigger(self):
        t = self.attack()
        for player in (1, 2):
            view = game.view(t.state, player)
            self.assertEqual(view["ability_show"]["check"], [600])
            self.assertIn(600, game.visible_cards(view))

    def test_damage_waits_until_its_been_shown(self):
        t = self.attack()
        self.assertEqual(t.them["zones"]["clock"], [])
        t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        self.assertEqual(len(t.them["zones"]["clock"]), 2)

    def test_a_triggers_choice_waits_too(self):
        t = self.attack(trigger="comeback")
        self.assertEqual(t.state["attack"]["prompt"]["kind"], "comeback")
        with self.assertRaises(game.GameError):
            t.apply(2, {"type": "trigger_choice"})
        t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        t.apply(2, {"type": "trigger_choice"})

    def test_abilities_the_check_triggers_wait_too(self):
        t = Table()
        t.card(600, card_type="Climax", power=None, level=None)
        t.me["zones"]["deck"][-1]["card"] = 600
        me = t.seat(t.me, "C2", t.card(2000, text="【AUTO】 When this card's trigger check reveals a climax, draw 1 card."))
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": me["uid"], "kind": "direct"}, show_checks=True)
        self.assertTrue(t.state["ability_queue"])
        with self.assertRaises(game.GameError):
            t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertEqual(game.view(t.state, 2)["ability"]["prompt"], None)
        t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def test_the_other_page_can_end_it(self):
        t = self.attack()
        t.apply(1, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        self.assertIsNone(t.state.get("ability_show"))

    def test_the_cpu_carries_on_by_itself(self):
        t = self.attack()
        action = t.next()
        self.assertEqual(action["type"], "ability_show_done")


class SetPowerTests(TestCase):
    def setUp(self):
        self.t = Table()
        self.card = self.t.seat(self.t.me, "C2", self.t.card(700, power=3000, text="【CONT】 During your turn, this card gets +1000 power."))
        self.t.refresh()

    def set(self, **action):
        self.t.apply(2, {"type": "set_power", "uid": self.card["uid"], **action})
        return self.t.state["stats"][self.card["uid"]]

    def test_it_replaces_whatever_the_power_was_and_both_players_see_it(self):
        self.assertEqual(self.set(count=9000)["power"], 9000)
        self.assertEqual(game.view(self.t.state, 1)["stats"][self.card["uid"]]["power"], 9000)
        self.assertIn("set the power", self.t.state["log"][-1]["text"])

    def test_it_counts_in_battle(self):
        self.set(count=500)
        self.t.card(1, power=1000)
        enemy = self.t.seat(self.t.them, "C2", 1)
        self.t.state.update(phase="attack", attack={"step": "declare"})
        self.t.refresh()
        self.t.apply(2, {"type": "attack", "uid": self.card["uid"], "kind": "front"})
        self.assertEqual(self.card["pos"], "reverse")
        self.assertEqual(enemy["pos"], "stand")

    def test_it_returns_to_normal_when_the_turn_ends(self):
        self.set(count=9000)
        self.t.state["phase"] = "main"
        self.t.apply(2, {"type": "phase", "phase": "end"})
        self.t.refresh()
        self.assertEqual(self.t.state["stats"][self.card["uid"]]["power"], 3000)
        self.assertNotIn("manual", self.t.state["stats"][self.card["uid"]])

    def test_setting_it_again_or_clearing_it(self):
        self.set(count=9000)
        self.assertEqual(self.set(count=100)["power"], 100)
        self.assertEqual(self.set(clear=True)["power"], 4000)

    def test_bad_values_and_other_cards(self):
        for bad in ({"count": -1}, {"count": 100000}, {"count": "lots"}, {}):
            with self.assertRaises(game.GameError):
                self.set(**bad)
        in_hand = self.t.hand(700)[0]
        with self.assertRaises(game.GameError):
            self.t.apply(2, {"type": "set_power", "uid": in_hand["uid"], "count": 1})
        enemy = self.t.seat(self.t.them, "C1", 700)
        with self.assertRaises(game.GameError):  # your own characters only
            self.t.apply(2, {"type": "set_power", "uid": enemy["uid"], "count": 1})


class OlderWordingTests(TestCase):
    """Older sets say the same things in other words."""

    def steps(self, text):
        return abilities.parse(text)[0]["steps"]

    def test_the_same_effect_in_other_words_reads_the_same(self):
        new = "【AUTO】 When this card is placed on the stage from your hand, choose 1 of your characters, and that character gets +1000 power until end of turn."
        for old in ("【AUTO】 When this card is placed on stage from your hand, choose one of your characters, and that character gets +1000 power until end of turn.",
                    "【AUTO】When this card is placed on stage from hand, choose one of your characters, and that character gets +1000 power until end of turn."):
            self.assertEqual(self.steps(old), self.steps(new), old)
            self.assertEqual(abilities.parse(old)[0]["when"], [{"on": "play"}])

    def test_card_names_are_never_changed(self):
        ability = abilities.parse('【AUTO】 When this card attacks, choose a card named "One on stage from hand" in your waiting room, and return it to your hand.')[0]
        self.assertEqual(ability["steps"][0]["filter"]["any"][0]["name"], "One on stage from hand")

    def test_full_width_brackets_and_missing_spaces(self):
        ability = abilities.parse("【AUTO】［(1)］When this card's battle opponent becomes【REVERSE】, you may pay the cost. If you do, draw 1 card.")[0]
        self.assertEqual(ability["cost"], [{"part": "stock", "n": 1}])
        self.assertEqual(ability["when"], [{"on": "reverse_opponent"}])
        self.assertEqual(abilities.by_hand_parts("【ACT】 [(1)【REST】this card] Draw 1 card."), [])

    def test_a_cost_holding_a_trigger_icon(self):
        ability = abilities.parse("【AUTO】 [Put 1 climax with [gate] in its trigger icon from your hand into your waiting room] When this card attacks, you may pay the cost. If you do, draw 1 card.")[0]
        self.assertEqual(ability["when"], [{"on": "attack"}])
        self.assertEqual(ability["cost"][0]["filter"]["any"][0]["icon"], "gate")

    def test_mid_sentence_act_is_still_not_a_new_ability(self):
        self.assertEqual(len(abilities.parse("【AUTO】 When you use an 【ACT】, this card gets +1000 power until end of turn.")), 1)

    def test_a_limit_of_twice_a_turn(self):
        t = Table()
        t.card(2000, text="【ACT】 This ability activates up to 2 times per turn. Draw 1 card.")
        me = t.seat(t.me, "C1", 2000)
        t.refresh()
        for _ in range(2):
            self.assertIsNone(t.state["acts"]["2"][me["uid"]][0]["why"])
            t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        self.assertEqual(t.state["acts"]["2"][me["uid"]][0]["why"], "already used this turn")

    def test_colors_and_costs_in_filters(self):
        filter_ = abilities.parse_filter("cost 1 or lower blue character", [])
        self.assertIsNone(filter_)  # the words come the other way round on cards
        filter_ = abilities.parse_filter("blue cost 1 or lower character", [])
        self.assertTrue(abilities.matches_filter(filter_, {"color": "Blue", "cost": 1, "card_type": "Character"}))
        self.assertFalse(abilities.matches_filter(filter_, {"color": "Red", "cost": 1, "card_type": "Character"}))
        self.assertFalse(abilities.matches_filter(filter_, {"color": "Blue", "cost": 2, "card_type": "Character"}))


class RevealThenMoveTests(TestCase):
    def play(self, text, top):
        t = Table()
        t.card(900, **top)
        t.me["zones"]["deck"][-1]["card"] = 900
        self.top = t.me["zones"]["deck"][-1]
        t.card(2000, text=text)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        return t

    TO_HAND = "【AUTO】 When this card is placed on the stage from your hand, reveal the top card of your deck. If that card is a 《Fleet Girl》 character, put it into your hand. (If it is not, return the revealed card to its original place)"
    TO_CLOCK = "【AUTO】 When this card is placed on the stage from your hand, reveal the top card of your deck. If that card is not a 《Music》 character, put it into your clock. (If it is, return the revealed card to its original place)"

    def test_a_match_goes_to_the_hand(self):
        t = self.play(self.TO_HAND, {"traits": "Fleet Girl"})
        self.assertIn(self.top["uid"], [c["uid"] for c in t.me["zones"]["hand"]])

    def test_anything_else_stays_on_top(self):
        t = self.play(self.TO_HAND, {"traits": "Other"})
        self.assertEqual(t.me["zones"]["deck"][-1]["uid"], self.top["uid"])

    def test_not_a_match_goes_to_the_clock(self):
        t = self.play(self.TO_CLOCK, {"traits": "Other"})
        self.assertIn(self.top["uid"], [c["uid"] for c in t.me["zones"]["clock"]])

    def test_a_match_stays_on_top_when_the_text_is_negated(self):
        t = self.play(self.TO_CLOCK, {"traits": "Music"})
        self.assertEqual(t.me["zones"]["deck"][-1]["uid"], self.top["uid"])

    def test_either_trait_means_a_character(self):
        filter_ = abilities.parse_filter("《Avatar》 or 《Net》 character", [])
        self.assertEqual(filter_["any"], [{"trait": "Avatar", "type": "character"}, {"trait": "Net", "type": "character"}])


class CountedPowerTests(TestCase):
    def table(self, text, **details):
        t = Table()
        t.card(2000, text=text, power=1000, **details)
        self.me = t.seat(t.me, "C1", 2000)
        return t

    def power(self, t):
        t.refresh()
        return t.state["stats"][self.me["uid"]]["power"]

    def test_for_each_of_your_other_characters(self):
        t = self.table("【CONT】 This card gets +500 power for each of your other 《Hero》 characters.", traits="Hero")
        self.assertEqual(self.power(t), 1000)  # not counting itself
        t.seat(t.me, "C2", t.card(901, traits="Hero"))
        t.seat(t.me, "C3", t.card(902, traits="Other"))
        self.assertEqual(self.power(t), 1500)

    def test_for_each_in_the_back_stage_only(self):
        t = self.table("【CONT】 This card gets +500 power for each other 《Hero》 character in your back stage.")
        t.seat(t.me, "C2", t.card(901, traits="Hero"))
        t.seat(t.me, "B1", 901)
        self.assertEqual(self.power(t), 1500)

    def test_for_each_marker(self):
        t = self.table("【CONT】 This card gets +1000 power for each marker underneath this card.")
        t.me["markers"]["C1"] = [game.new_card(1), game.new_card(1)]
        self.assertEqual(self.power(t), 3000)

    def test_for_each_character_in_their_back_stage(self):
        t = self.table("【CONT】 This card gets +1000 power for each character in your opponent's back stage.")
        t.seat(t.them, "B1", t.card(901))
        self.assertEqual(self.power(t), 2000)

    def test_only_on_your_turn(self):
        t = self.table("【CONT】 During your turn, this card gets +500 power for each of your other 《Hero》 characters.")
        t.seat(t.me, "C2", t.card(901, traits="Hero"))
        self.assertEqual(self.power(t), 1500)
        t.state["turn"] = "1"
        self.assertEqual(self.power(t), 1000)

    def test_the_character_facing_this_card_loses_soul(self):
        t = self.table("【CONT】 The character facing this card gets -1 soul.")
        enemy = t.seat(t.them, game.OPPOSITE["C1"], t.card(901, soul=2))
        t.refresh()
        self.assertEqual(t.state["stats"][enemy["uid"]]["soul"], 1)

    def test_multiplied_by_a_level(self):
        t = Table()
        t.card(901, level=2, power=1000)
        front = t.seat(t.me, "C1", 901)
        t.seat(t.me, "B1", t.card(2000, text="【CONT】 Assist All of your characters in front of this card get +X power. X is equal to 500 multiplied by that character's level."))
        t.refresh()
        self.assertEqual(t.state["stats"][front["uid"]]["power"], 2000)


class ThatCardTests(TestCase):
    def test_if_that_card_after_putting_the_top_card_away(self):
        t = Table()
        t.card(900, level=1)
        top = t.me["zones"]["deck"][-1]
        top["card"] = 900
        t.card(2000, text="【AUTO】 When this card is placed on the stage from your hand, you may put the top card of your deck into your waiting room. If that card is a level 1 or higher character, this card gets +2000 power until end of turn.")
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.refresh()
        self.assertEqual(t.state["stats"][card["uid"]]["power"], 3000)

    def test_that_character_is_the_card_just_put_away(self):
        t = Table()
        t.card(900, level=0)
        top = t.me["zones"]["deck"][-1]
        top["card"] = 900
        t.card(2000, text="【AUTO】 When this card attacks, you may put the top card of your deck into your waiting room. If that card is a level 0 or lower character, put that character in any position of your back stage.")
        me = t.seat(t.me, "C2", 2000)
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": me["uid"], "kind": "direct"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertEqual({o["value"] for o in t.state["resolving"]["prompt"]["options"]}, {"B1", "B2"})
        t.apply(2, {"type": "ability_answer", "value": "B1"})
        self.assertEqual(t.me["stage"]["B1"]["uid"], top["uid"])


class NewerMechanicsTests(TestCase):
    def play(self, text, table=None, **details):
        t = table or Table()
        t.card(2000, text=text, **details)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C2"})
        return t, card

    def fire(self, t):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def finish(self, t):
        if t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})

    def test_another_character_attacking_triggers_it(self):
        t = Table()
        t.card(800, traits="Hero")
        watcher = t.seat(t.me, "C1", t.card(2000, text="【AUTO】 When your other 《Hero》 character attacks, this card gets +1000 power until end of turn."))
        attacker = t.seat(t.me, "C2", 800)
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": attacker["uid"], "kind": "direct"}, show_checks=True)
        self.assertEqual(t.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_a_character_in_battle_can_be_chosen(self):
        t = Table()
        mine = t.seat(t.me, "C2", t.card(801))
        t.seat(t.me, "C1", t.card(802))
        t.seat(t.them, "C2", t.card(803))
        t.state["attack"] = {"step": "counter", "uid": mine["uid"], "target": "C2", "slot": "C2", "kind": "front"}
        t.state["resolving"] = {"player": "2", "uid": mine["uid"], "card": 801, "text": "t", "ctx": {}, "prompt": None,
                                "steps": abilities.parse("Choose 1 of your characters in battle, and that character gets +1000 power until end of turn.")[0]["steps"]}
        t.apply(2, {"type": "chat", "text": "."})
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [mine["uid"]])

    def test_a_level_buff_counts_for_side_attacks(self):
        t = Table()
        t.card(1, level=0)
        t.seat(t.them, "C2", 1)
        steps = abilities.parse("Choose 1 of your opponent's characters, and that character gets +2 level until end of turn.")[0]["steps"]
        self.assertEqual(steps[1]["level"], 2)

    def test_power_from_the_total_level_milled(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, put the top 2 cards of your deck into your waiting room, and this card gets +X power until end of turn. X is equal to the total level of the cards put into your waiting room by this effect ×1000.")
        t.card(810, level=2)
        t.card(811, level=1)
        t.me["zones"]["deck"][-2:] = [game.new_card(810), game.new_card(811)]
        self.fire(t)
        self.finish(t)
        t.refresh()
        self.assertEqual(t.state["stats"][card["uid"]]["power"], 1000 + 3000)

    def test_a_delayed_effect_waits_for_its_phase(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, this card gets +1000 power until end of turn. At the beginning of your next encore step, put this card into your waiting room.")
        self.fire(t)
        self.finish(t)
        self.assertEqual(len(t.state["delayed"]), 1)
        self.assertEqual(t.me["stage"]["C2"]["uid"], card["uid"])  # not yet
        t.state["phase"] = "attack"
        t.state["attack"] = {"step": "declare"}
        t.apply(2, {"type": "phase", "phase": "encore"})
        self.fire(t)
        self.assertIsNone(t.me["stage"]["C2"])
        self.assertIn(card["uid"], [c["uid"] for c in t.me["zones"]["waiting"]])
        self.assertEqual(t.state["delayed"], [])

    def test_a_character_that_wont_stand(self):
        t = Table()
        t.state["turn"] = "1"
        enemy = t.seat(t.me, "C1", t.card(820), pos="rest")
        other = t.seat(t.me, "C2", t.card(821), pos="rest")
        t.state["buffs"] = [{"uid": enemy["uid"], "status": "no_stand", "expires": t.state["turn_number"] + 1}]
        t.state["phase"] = "main"
        t.refresh()
        t.apply(1, {"type": "phase", "phase": "end"})
        self.assertEqual((enemy["pos"], other["pos"]), ("rest", "stand"))

    def test_shift_exchanges_a_clock_card_with_one_of_its_color_in_hand(self):
        text = "【AUTO】【CLOCK】 Shift, Level 0 (At the beginning of your main phase, you may choose a green card in your hand and this card in your clock, and exchange them)"
        self.assertEqual(abilities.by_hand_parts(text), [])
        t = Table()
        t.card(2000, text=text)
        t.card(830, color="Green")
        t.card(831, color="Red")
        clock = game.new_card(2000)
        t.me["zones"]["clock"].append(clock)
        green, red = t.hand(830, 831)
        t.state["phase"] = "clock"
        t.refresh()
        t.apply(2, {"type": "phase", "phase": "main"})
        self.fire(t)
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [green["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [green["uid"]]})
        self.assertIn(clock["uid"], [c["uid"] for c in t.me["zones"]["hand"]])
        self.assertIn(green["uid"], [c["uid"] for c in t.me["zones"]["clock"]])


class ReportedCardTests(TestCase):
    NAMED = ('Choose up to 2 characters in your waiting room with "LAGANN(ラガン)" in its card name, return them to your hand, '
             'choose 1 of your other 《Team DAI-GURREN》 characters, and that character gets +1000 power until end of turn.')
    MARKERS = "【AUTO】 When this card is placed on the stage from your hand, choose up to four cards in your waiting room, and put them face up in any order underneath this card as markers."
    SUNDER = ('【AUTO】 【CXCOMBO】 When a card named "My Drill Is the Drill That Creates the Heavens!!!!" is placed on your climax area, if you do not have any other characters, this card gets the following ability until end of turn. '
              '"【AUTO】 Sunder/"Super Galaxy GURREN LAGANN" [(2) Put four cards from your hand into your waiting room]" (At the end of this card\'s attack, you may pay the cost. If you do, choose a marker of this card named '
              '"Super Galaxy GURREN LAGANN", put it on any position of your stage, and put this card and all markers underneath this card face up in any order underneath that character as markers)')

    def test_nothing_here_needs_doing_by_hand(self):
        for text in (self.NAMED, self.MARKERS, self.SUNDER):
            self.assertEqual(abilities.by_hand_parts(text), [], text)

    def test_choosing_by_part_of_a_name_in_either_case(self):
        t = Table()
        t.card(1, name="Simon: Lagann Pilot")
        t.card(2, name="Viral")
        t.card(3, traits="Team DAI-GURREN")
        lagann, viral = [game.new_card(1)], game.new_card(2)
        t.me["zones"]["waiting"] += [*lagann, viral]
        friend = t.seat(t.me, "C1", 3)
        t.card(2000, text=self.NAMED, card_type="Event", power=None)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "resolution"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [lagann[0]["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [lagann[0]["uid"]]})
        self.assertIn(lagann[0]["uid"], [c["uid"] for c in t.me["zones"]["hand"]])
        t.apply(2, {"type": "ability_answer", "uids": [friend["uid"]]})
        self.assertEqual(sum(b.get("power", 0) for b in t.state["buffs"]), 1000)

    def test_cards_from_the_waiting_room_become_markers(self):
        t = Table()
        waiting = [game.new_card(pk) for pk in (1, 2, 3, 4, 5)]
        t.me["zones"]["waiting"] += waiting
        t.card(2000, text=self.MARKERS)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertEqual(t.state["resolving"]["prompt"]["max"], 4)
        t.apply(2, {"type": "ability_answer", "uids": [c["uid"] for c in waiting[:4]]})
        self.assertEqual([c["uid"] for c in t.me["markers"]["C1"]], [c["uid"] for c in waiting[:4]])
        self.assertEqual(len(t.me["zones"]["waiting"]), 1)
        self.assertFalse(t.me["markers"]["C1"][0]["face_down"])

    def test_sunder(self):
        t = Table()
        t.card(10, name="Super Galaxy GURREN LAGANN")
        t.card(11)
        t.card(2000, text=self.SUNDER, power=9000)
        t.card(12, name="My Drill Is the Drill That Creates the Heavens!!!!", card_type="Climax", power=None, level=None)
        me = t.seat(t.me, "C2", 2000)
        big, small = game.new_card(10), game.new_card(11)
        t.me["markers"]["C2"] = [big, small]
        cx = t.hand(12)[0]
        t.hand(11, 11, 11, 11)
        t.stock(2)
        t.state["phase"] = "climax"
        t.refresh()
        t.apply(2, {"type": "move", "uid": cx["uid"], "to": "climax"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        t.state.pop("pending_climax", None)
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": me["uid"], "kind": "direct"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        prompt = t.state["resolving"]["prompt"]  # the cost: 4 cards from the hand
        self.assertEqual(prompt["min"], 4)
        t.apply(2, {"type": "ability_answer", "uids": prompt["options"][:4]})
        prompt = t.state["resolving"]["prompt"]
        self.assertEqual(prompt["options"], [big["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [big["uid"]]})
        t.apply(2, {"type": "ability_answer", "value": "C1"})
        self.assertEqual(t.me["stage"]["C1"]["uid"], big["uid"])
        self.assertIsNone(t.me["stage"]["C2"])
        self.assertEqual({c["uid"] for c in t.me["markers"]["C1"]}, {me["uid"], small["uid"]})


class MoreWordingTests(TestCase):
    def test_options_on_the_next_line_belong_to_the_ability(self):
        text = '【AUTO】 When this card attacks, choose 1 of the following effects, and perform it.\n"Draw 1 card." "This card gets +1000 power until end of turn."'
        parsed = abilities.parse(text)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["steps"][0]["do"], "options")
        self.assertEqual(abilities.by_hand_parts(text), [])

    def test_a_trigger_with_two_conditions(self):
        when = abilities.parse("【AUTO】 When this card attacks or is frontal attacked, draw 1 card.")[0]["when"]
        self.assertEqual(when, [{"on": "attack"}, {"on": "frontal_self"}])
        self.assertEqual(abilities.parse("【AUTO】 When this card attacks or becomes 【REVERSE】, draw 1 card.")[0]["when"], [{"on": "attack"}, {"on": "reverse_self"}])

    def test_choosing_which_ability_to_gain(self):
        t = Table()
        t.card(2000, text='【AUTO】 When this card is placed on the stage from your hand, choose 1 of the following abilities, this card gets that ability until end of turn. "【AUTO】 When this card attacks, draw 1 card." "【AUTO】 When this card is frontal attacked, draw 1 card."')
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertEqual(len(t.state["resolving"]["prompt"]["options"]), 2)
        t.apply(2, {"type": "ability_answer", "value": 1})
        self.assertEqual(t.state["buffs"][0]["grant"], ["【AUTO】 When this card is frontal attacked, draw 1 card."])

    def test_at_the_end_of_the_turn(self):
        t = Table()
        t.card(2000, text="【AUTO】 When this card is placed on the stage from your hand, this card gets +1000 power until end of turn. At the end of the turn, put this card into your waiting room.")
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        self.assertEqual(t.state["delayed"][0]["phase"], "end")
        t.apply(2, {"type": "phase", "phase": "end"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertIn(card["uid"], [c["uid"] for c in t.me["zones"]["waiting"]])
        self.assertEqual(t.state["delayed"], [])

    def test_your_opponent_cant_encore_this_turn(self):
        t = Table()
        enemy = t.seat(t.them, "C1", t.card(1))
        t.state["resolving"] = {"player": "2", "uid": "x", "card": 1, "text": "t", "ctx": {}, "prompt": None,
                                "steps": abilities.parse('【AUTO】 When this card attacks, your opponent cannot use "【AUTO】 Encore" until end of turn.')[0]["steps"]}
        t.apply(2, {"type": "chat", "text": "."})
        self.assertTrue(game.has_status(t.state, enemy["uid"], "no_encore"))


class NoEndlessRearrangingTests(TestCase):
    def test_power_from_markers_doesnt_make_it_swap_forever(self):
        t = Table()
        text = "【CONT】 This card gets +1000 power for each marker underneath this card."
        t.card(1001, text=text, power=1000)
        t.card(1002, text=text, power=1000)
        t.seat(t.me, "C1", 1001)
        t.seat(t.me, "C2", 1002)
        t.me["markers"]["C1"] = [game.new_card(1), game.new_card(1)]
        self.assertEqual(t.next(), {"type": "phase", "phase": "climax"})  # markers go with the character: nothing to gain

    def test_a_character_is_rearranged_at_most_once_a_turn(self):
        t = Table()
        text = "【CONT】 If this card is in the middle position of your center stage, this card gets +3000 power."
        t.card(1001, text=text, power=1000)
        t.card(1002, text=text, power=1000)
        t.seat(t.me, "C1", 1001)
        t.seat(t.me, "C3", 1002)
        moves = 0
        for _ in range(12):
            action = t.next()
            if action["type"] != "move":
                break
            t.apply(2, action)
            moves += 1
        self.assertLessEqual(moves, 2)
        self.assertEqual(action, {"type": "phase", "phase": "climax"})


class WordingSpeedTests(TestCase):
    def test_the_shortcut_only_names_text_every_match_has(self):
        self.assertEqual(abilities.required_text(r"\bmultiplied by by\b"), "multiplied by by")
        self.assertEqual(abilities.required_text(r"(?i)some text"), "")
        self.assertIn(abilities.required_text(r"\b(?:on|at) the bottom of\b"), (" the bottom of",))
        self.assertEqual(abilities.required_text(r"a|b"), "")

    def test_every_rule_still_matches_what_it_says_it_needs(self):
        for pattern, _, needs in abilities.WORDING_RULES:
            self.assertIsInstance(needs, str, pattern.pattern)

    def test_the_shortcut_never_changes_a_reading(self):
        samples = ["【AUTO】 When this card attacks, choose two of your other characters, and until end of turn, those characters get +500 power and the following ability. \"【CONT】 This card gets +1 soul.\"",
                   "【ACT】 [Put a blue card from your hand into waiting room] Search you deck for up to one character with \"Rapi\", reveal it to your opponent, put it into your hand, and shuffle your deck afterwards.",
                   "COUNTER@ Backup 2500, Level 2 [Put this card from your hand into your waiting room]"]
        for text in samples:
            slow = abilities.mask(text.translate(abilities.FULL_WIDTH))[0]
            for _ in range(2):
                for pattern, replacement in abilities.WORDING:
                    slow = abilities._re.sub(pattern, replacement, slow)
            fast = abilities.mask(abilities.canonical(text))[0]
            self.assertEqual(abilities.mask(abilities.unmask(slow, abilities.mask(text.translate(abilities.FULL_WIDTH))[1]))[0], fast)


class SeventhBatchTests(TestCase):
    def table(self, text, stock=0):
        t = Table()
        t.card(2000, text=text)
        card = t.hand(2000)[0]
        t.stock(stock)
        t.refresh()
        return t, card

    def fire(self, t):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def shows(self, t):
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})

    def test_the_sentence_after_a_quote_is_its_own(self):
        steps = abilities.parse('【AUTO】 When this card attacks, this card gets the following ability until end of turn. "【CONT】 This card gets +500 power." Then, reveal the top card of your deck.')[0]["steps"]
        self.assertEqual([s["do"] for s in steps], ["buff", "reveal_top"])
        self.assertEqual(len(steps[0]["grant"]), 1)

    def test_x_after_a_quote(self):
        text = '【AUTO】 When this card attacks, choose 1 character facing this card, deal X damage to your opponent, and that character gets the following ability until end of turn. \n"【CONT】 This card gets +500 power." X is equal to that character\'s soul.'
        self.assertEqual(abilities.by_hand_parts(text), [])

    def test_several_quoted_names_arent_split(self):
        ability = abilities.parse('【AUTO】 When this card attacks, if "One" is in your climax area, this card gets +500 power until end of turn.')[0]
        self.assertEqual(ability["steps"][0]["power"], 500)

    def test_if_you_do_after_a_plain_action(self):
        text = '【COUNTER】 Choose 1 of your characters, and put it into your waiting room. If you do, draw 1 card.'
        steps = abilities.parse(text)[0]["steps"]
        self.assertEqual(steps[-1]["cond"], [{"type": "did_it"}])
        self.assertEqual(abilities.by_hand_parts(text), [])

    def test_if_you_do_after_something_that_just_happens(self):
        for text in ("【AUTO】 At the beginning of your climax phase, put this card into your memory. If you do, draw 1 card.",
                     "【AUTO】 When this card is placed on the stage from your hand, return all cards in your waiting room to your deck. If you do, shuffle your deck, and draw 1 card."):
            steps = abilities.parse(text)[0]["steps"]
            self.assertNotIn("if", [s["do"] for s in steps], text)
            self.assertEqual(steps[-1]["do"], "draw", text)

    BANNED = 'If you do not have a 《Hero》 character, this card cannot be played from your hand.\nDraw 1 card.'

    def test_a_card_that_cant_be_played_yet(self):
        t = Table()
        event = t.hand(t.card(2000, card_type="Event", text=self.BANNED))[0]
        t.refresh()
        self.assertEqual(t.state["play_banned"]["2"], [event["uid"]])
        self.assertEqual(abilities.by_hand_parts(self.BANNED), [])
        with self.assertRaises(game.GameError):
            t.apply(2, {"type": "move", "uid": event["uid"], "to": "resolution"})
        t.seat(t.me, "C1", t.card(800, traits="Hero"))
        t.refresh()
        self.assertEqual(t.state["play_banned"]["2"], [])
        t.apply(2, {"type": "move", "uid": event["uid"], "to": "resolution"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertEqual(len(t.me["zones"]["hand"]), 1)

    def test_the_cpu_keeps_to_it_too(self):
        t = Table()
        t.card(800, traits="Hero")
        event = t.hand(t.card(2000, card_type="Event", text="If you do not have a 《Hero》 character, this card cannot be played from your hand.\nDraw 1 card."))[0]
        mind = cpu.Mind(t.state, "2", t.info, cpu.Temper(), random.Random(1))
        self.assertFalse(mind.can_play(event))
        t.seat(t.me, "C1", 800)
        self.assertTrue(mind.can_play(event))

    def test_a_counter_with_a_condition_stays_a_counter(self):
        text = '【COUNTER】 If you have 1 or less 《Hero》 characters, this card cannot be played from your hand.\nChoose 1 character in battle, and that character gets +1000 power until end of turn.'
        kinds = [a["kind"] for a in abilities.parse(text)]
        self.assertEqual(kinds, ["cont", "counter"])
        t = Table()
        t.card(2000, text=text)
        t.card(800, traits="Hero")
        card = game.new_card(2000)
        self.assertIsNone(game.counter_play(t.state, "2", card, t.info))
        t.seat(t.me, "C1", 800)
        t.seat(t.me, "C2", 800)
        self.assertIsNotNone(game.counter_play(t.state, "2", card, t.info))

    def test_a_ban_it_cant_read_is_flagged(self):
        self.assertTrue(abilities.by_hand_parts("If the moon is full, this card cannot be played from your hand.\nDraw 1 card."))

    def test_if_you_do_needs_it_to_have_happened(self):
        t = Table()
        env = game.SimpleNamespace(info=t.info)
        self.assertFalse(game.condition_met({"type": "did_it"}, t.state, "2", None, {"it": []}, env))
        self.assertTrue(game.condition_met({"type": "did_it"}, t.state, "2", None, {"it": ["x"]}, env))

    FUSION = ('【ACT】 Fusion [Put 1 "Partner" from your stage face up underneath this card as a marker] Search your deck for up to 1 "Merged", put it in the stage position that this card was in, '
              'put this card and all markers underneath this card underneath it as markers, and shuffle your deck.')

    def test_fusion_end_to_end(self):
        self.assertEqual(abilities.by_hand_parts(self.FUSION), [])
        t = Table()
        me = t.seat(t.me, "C2", t.card(2000, text=self.FUSION))
        partner = t.seat(t.me, "B1", t.card(801, name="Partner"))
        merged = game.new_card(t.card(802, name="Merged"))
        t.me["zones"]["deck"].append(merged)
        t.refresh()
        t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
        t.apply(2, {"type": "ability_answer", "uids": [partner["uid"]]})
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [merged["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [merged["uid"]]})
        self.assertEqual(t.me["stage"]["C2"]["uid"], merged["uid"])
        self.assertEqual({c["uid"] for c in t.me["markers"]["C2"]}, {me["uid"], partner["uid"]})
        self.assertIsNone(t.me["stage"]["B1"])

    def test_the_old_position_still_works_once_this_card_has_gone(self):
        t = Table()
        me = t.seat(t.me, "C2", t.card(2000, text='【ACT】 [Put this card into your waiting room] Choose 1 "Next" in your waiting room, and put it in the stage position that this card was in.'))
        nxt = game.new_card(t.card(802, name="Next"))
        t.me["zones"]["waiting"] = [nxt]
        t.refresh()
        t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
        t.apply(2, {"type": "ability_answer", "uids": [nxt["uid"]]})
        self.assertEqual(t.me["stage"]["C2"]["uid"], nxt["uid"])
        self.assertEqual(t.me["markers"]["C2"], [])

    def test_an_all_hand_discard_counts(self):
        text = "【AUTO】 When this card is placed on the stage from your hand, put all cards from your hand into your waiting room, and draw X cards. X is equal to the number of cards revealed."
        self.assertEqual(abilities.by_hand_parts(text), [])

    def test_position_conditions(self):
        t = Table()
        me = t.seat(t.me, "C3", t.card(2000))
        env = game.SimpleNamespace(info=t.info)
        cond = abilities.parse_condition("if this card is in the right position of your center stage", [])
        self.assertTrue(game.condition_met(cond, t.state, "2", me, {}, env))
        self.assertFalse(game.condition_met({**cond, "slot": "C1"}, t.state, "2", me, {}, env))

    def test_colors_turned_over(self):
        cond = abilities.parse_condition("if there are 3 or more colors", [])
        t = Table()
        t.card(801, color="Red"); t.card(802, color="Blue"); t.card(803, color="Green")
        env = game.SimpleNamespace(info=t.info)
        self.assertTrue(game.condition_met(cond, t.state, "2", None, {"flipped": [801, 802, 803]}, env))
        self.assertFalse(game.condition_met(cond, t.state, "2", None, {"flipped": [801, 802]}, env))


class SixthBatchTests(TestCase):
    def play(self, text, stock=0, **details):
        t = Table()
        t.card(2000, text=text, **details)
        card = t.hand(2000)[0]
        t.stock(stock)
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        return t, card

    def fire(self, t):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def shows(self, t):
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})

    def test_choose_with_nowhere_named_means_the_stage(self):
        t = Table()
        t.card(2000, text="【AUTO】 When this card is placed on the stage from your hand, choose up to 1 《Hero》 character, and that character gets +1500 power until end of turn.")
        ally = t.seat(t.me, "C2", t.card(800, traits="Hero"))
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        self.fire(t)
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [ally["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [ally["uid"]]})
        self.shows(t)
        t.refresh()
        self.assertEqual(t.state["stats"][ally["uid"]]["power"], 2500)

    def test_choose_with_nowhere_named_after_looking_means_those(self):
        t = Table()
        t.card(2000, text="【AUTO】 When this card is placed on the stage from your hand, look at up to 1 cards from the top of your deck, choose up to 1 《Hero》 character, reveal it to your opponent, put it into your hand, and put the rest into your waiting room.")
        t.seat(t.me, "C2", t.card(800, traits="Hero"))
        top = game.new_card(800)
        t.me["zones"]["deck"].append(top)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        self.fire(t)
        t.apply(2, {"type": "ability_answer", "value": 1})
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [top["uid"]])

    def test_x_with_a_plus(self):
        spec = abilities.parse_x("the number of colors of your characters on the stage +1", [])
        self.assertEqual((spec["of"], spec["add"]), ("colors_stage", 1))
        t = Table()
        t.seat(t.me, "C1", t.card(801, color="Red"))
        t.seat(t.me, "C2", t.card(802, color="Blue"))
        self.assertEqual(game.x_value(spec, t.state, "2", None, {}, game.SimpleNamespace(info=t.info)), 3)

    def test_x_multiplied_in_words(self):
        step = abilities.parse("【AUTO】 When this card attacks, this card gets +X power until end of turn. X is equal to 500 multiplied by the number of your other 《Hero》 characters.")[0]["steps"][0]
        self.assertEqual((step["x"]["of"], step["x"]["times"]), ("my_chars", 500))

    def test_the_older_x_with_a_plus_is_unchanged(self):
        self.assertEqual(abilities.parse_x("the level of that card +1", [])["plus"], 1)

    def test_characters_named_or_of_a_trait(self):
        f = abilities.parse_filter("characters with 《Hero》 or ⟦0⟧ in its card name", ["Rapi"])
        self.assertTrue(abilities.matches_filter(f, {"card_type": "Character", "traits": "Hero"}))
        self.assertTrue(abilities.matches_filter(f, {"card_type": "Character", "name": "Rapi: Red"}))
        self.assertFalse(abilities.matches_filter(f, {"card_type": "Character", "name": "Anis"}))

    def test_the_low_cost_wording(self):
        steps = abilities.parse("【AUTO】 When this card attacks, choose 1 of your opponent's cost 1 or less characters, and put it into their waiting room.")[0]["steps"]
        self.assertEqual(steps[0]["filter"]["any"][0]["cost_max"], 1)

    IF_ELSE = ("【AUTO】 When this card is placed on the stage from your hand, reveal the top card of your deck. If that card is a 《Hero》 character, this card gets +1000 power until end of turn. "
               "If it is not, this card gets +500 power until end of turn.")

    def test_if_it_is_not_takes_the_other_branch(self):
        self.assertEqual(abilities.by_hand_parts(self.IF_ELSE), [])
        for traits, power in (("Hero", 2000), ("Villain", 1500)):
            t, card = self.play(self.IF_ELSE)
            t.card(801, traits=traits)
            t.me["zones"]["deck"].append(game.new_card(801))
            self.fire(t)
            self.shows(t)
            t.refresh()
            self.assertEqual(t.state["stats"][card["uid"]]["power"], power, traits)

    def test_otherwise_reads_the_same(self):
        steps = abilities.parse("【AUTO】 When this card attacks, if you have another 《Hero》 character, draw 1 card. Otherwise, put this card into your waiting room.")[0]
        self.assertEqual(abilities.by_hand_parts(steps["text"]), [])

    def test_exchanging_this_card_with_a_chosen_one(self):
        t = Table()
        t.card(801, name="Partner")
        me = t.seat(t.me, "C1", t.card(2000, text='【ACT】 [【REST】 this card] Choose this card and 1 "Partner" in your hand, and exchange them.'))
        partner = t.hand(801)[0]
        t.refresh()
        t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
        t.apply(2, {"type": "ability_answer", "uids": [partner["uid"]]})
        self.assertEqual(t.me["stage"]["C1"]["uid"], partner["uid"])
        self.assertIn(me["uid"], [c["uid"] for c in t.me["zones"]["hand"]])

    def test_exchanging_written_the_other_way_round(self):
        self.assertEqual(abilities.by_hand_parts("【AUTO】 When this card attacks, choose 1 character in your waiting room and this card, and exchange them."), [])

    def test_several_picks_together(self):
        text = "【AUTO】 When this card is placed on the stage from your hand, look at up to 3 cards from the top of your deck, choose up to 1 yellow character and up to 1 red character from among them, put them into your hand, and put the rest into your waiting room."
        self.assertEqual(abilities.by_hand_parts(text), [])
        t, _ = self.play(text)
        t.card(801, color="Yellow")
        t.card(802, color="Red")
        t.card(803, color="Blue")
        yellow, red, blue = game.new_card(801), game.new_card(802), game.new_card(803)
        t.me["zones"]["deck"] += [blue, red, yellow]
        self.fire(t)
        t.apply(2, {"type": "ability_answer", "value": 3})
        t.apply(2, {"type": "ability_answer", "uids": [yellow["uid"]]})
        t.apply(2, {"type": "ability_answer", "uids": [red["uid"]]})
        hand = [c["uid"] for c in t.me["zones"]["hand"]]
        self.assertIn(yellow["uid"], hand)
        self.assertIn(red["uid"], hand)
        self.assertIn(blue["uid"], [c["uid"] for c in t.me["zones"]["waiting"]])

    def test_a_random_card_from_their_hand(self):
        text = "【AUTO】 When this card is placed on the stage from your hand, choose 1 random card in your opponent's hand, and put it into their waiting room."
        self.assertEqual(abilities.by_hand_parts(text), [])
        t, _ = self.play(text)
        t.them["zones"]["hand"] = [game.new_card(1)]
        self.fire(t)
        self.assertEqual((t.them["zones"]["hand"], len(t.them["zones"]["waiting"])), ([], 1))

    def test_a_level_limit_on_the_character_facing(self):
        step = abilities.parse("【AUTO】 When this card attacks, choose 1 level 1 or lower character facing this card, and put it into their waiting room.")[0]["steps"][0]
        self.assertEqual(step["filter"]["any"][0]["level_max"], 1)

    def test_a_marker_or_a_named_card(self):
        steps = abilities.parse('【AUTO】 At the beginning of your encore step, you may choose 1 marker underneath this card or 1 "Father" in your waiting room, and put it in the stage position that this card was in.')[0]["steps"]
        self.assertEqual(steps[0]["then"][0]["do"], "options")

    def test_cannot_be_chosen_for_a_turn(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, this card gets +1000 power and this card cannot be chosen by your opponent's effects until end of turn.")
        self.fire(t)
        self.shows(t)
        t.refresh()
        self.assertTrue(game.has_status(t.state, card["uid"], "no_chosen"))
        self.assertEqual(t.state["stats"][card["uid"]]["power"], 2000)

    def test_conditions_on_what_was_turned_over(self):
        cond = abilities.parse_condition("if there are 2 or more climax among those cards", [])
        t = Table()
        t.card(913, card_type="Climax")
        env = game.SimpleNamespace(info=t.info)
        self.assertFalse(game.condition_met(cond, t.state, "2", None, {"flipped": [913, 1]}, env))
        self.assertTrue(game.condition_met(cond, t.state, "2", None, {"flipped": [913, 913]}, env))

    def test_typos_on_real_cards(self):
        for text in ("【AUTO】 When this card attacks, search you deck for up to 1 level 1 or lower character, reveal it to your opponent, put it into your hand, and shuffle your deck.",
                     "【ACT】 [(1)] Choose up to 2 of your ?Strange? characters, and those characters get +500 power until end of turn.",
                     "【CONT】 All of your other <<Master>> or <<Homunculus>> characters get +500 power."):
            self.assertEqual(abilities.by_hand_parts(text), [], text)


class FifthBatchTests(TestCase):
    def play(self, text, stock=0, **details):
        t = Table()
        t.card(2000, text=text, **details)
        card = t.hand(2000)[0]
        t.stock(stock)
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        return t, card

    def fire(self, t):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def shows(self, t):
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})

    def queued(self, t):
        return [e["ability"]["text"] for e in t.state.get("ability_queue", [])]

    def test_a_backup_marked_with_the_climax_icon(self):
        t = Table()
        t.card(2000, text="【ACT】 [c-icon] Backup 1500, Level 0 [Put this card from your hand into your waiting room] (Choose one of your characters that is being frontal attacked.)")
        self.assertEqual(abilities.by_hand_parts(t.info(2000)["text"]), [])
        self.assertEqual(game.counter_play(t.state, "2", game.new_card(2000), t.info), (0, 1500))

    def test_two_of_an_icon(self):
        two = {"any": [{"icon": "soulx2"}]}
        self.assertTrue(abilities.matches_filter(two, {"trigger": "soul soul"}))
        self.assertFalse(abilities.matches_filter(two, {"trigger": "soul"}))
        when = abilities.parse("【AUTO】 When your character's trigger check reveals a climax with [soul][soul] in its trigger icon, this card gets +500 power until end of turn.")[0]["when"][0]
        self.assertEqual(when["filter"]["any"][0]["icon"], "soulx2")

    def test_a_trigger_icon_written_with_a_tag(self):
        self.assertEqual(abilities.parse_condition("if that card's trigger icon is [treasure]", [])["filter"]["any"][0]["icon"], "treasure")
        self.assertEqual(abilities.by_hand_parts("【AUTO】 When this card attacks, reveal the top card of your deck. If that card's trigger icon is 【TREASURE】, draw 1 card."), [])

    def test_color_free_and_lowered_together(self):
        ability = abilities.parse("【CONT】 If you have 4 or more 《Hero》 characters, this card can be played from your hand without fulfilling color requirements, and this card gets -1 level while in your hand.")[0]
        self.assertEqual((ability["color_free"], ability["hand_mod"]["level"], len(ability["cond"])), ({"self": True}, -1, 1))

    def test_into_stock_instead_of_the_waiting_room(self):
        text = ("【AUTO】 When this card is placed on the stage from your hand, put up to 1 card from the top of your clock into your waiting room. "
                "If you have 1 or more other 《Hero》 characters, you may put that card into your stock instead of into your waiting room.")
        self.assertEqual(abilities.by_hand_parts(text), [])
        t = Table()
        t.card(2000, text=text)
        t.seat(t.me, "C2", t.card(800, traits="Hero"))
        top = game.new_card(1)
        t.me["zones"]["clock"] = [top]
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        self.fire(t)
        t.apply(2, {"type": "ability_answer", "value": 1})
        t.apply(2, {"type": "ability_answer", "value": "yes"})
        self.assertEqual(t.me["zones"]["stock"][-1]["uid"], top["uid"])

    def test_if_the_character_chosen_is(self):
        text = "【AUTO】 When this card attacks, choose 1 character in your waiting room, and return it to your hand. If the character chosen is level 3 or higher, this card gets +3000 power until end of turn."
        step = abilities.parse(text)[0]["steps"][-1]
        self.assertEqual(step["cond"][0]["type"], "it_is")
        t = Table()
        t.card(801, level=3)
        high = game.new_card(801)
        env = game.SimpleNamespace(info=t.info)
        t.me["zones"]["hand"] = [high]
        self.assertTrue(game.condition_met(step["cond"][0], t.state, "2", None, {"it": [high["uid"]]}, env))
        t.cards[801]["level"] = 2
        self.assertFalse(game.condition_met(step["cond"][0], t.state, "2", None, {"it": [high["uid"]]}, env))

    def test_if_x_is(self):
        text = ("【AUTO】 When this card is placed on the stage from your hand, reveal the top card of your deck, choose 1 level X or lower character in your waiting room, and return it to your hand. "
                "If X is 2 or higher, you may draw 1 card. X is equal to the level of the revealed card.")
        self.assertEqual(abilities.by_hand_parts(text), [])
        cond = abilities.parse(text)[0]["steps"][-1]["cond"][0]
        self.assertEqual((cond["type"], cond["x"]["of"]), ("x_is", "revealed_level"))

    def test_the_opponent_character_triggers(self):
        t = Table()
        watcher = t.seat(t.me, "C1", t.card(2000, text="【AUTO】 When your opponent's character attacks, this card gets +500 power until end of turn."))
        attacker = t.seat(t.them, "C1", 1)
        t.state.update(turn="1", phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(1, {"type": "attack", "uid": attacker["uid"], "kind": "direct"})
        self.assertEqual(t.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_the_opponent_reversed(self):
        t = Table()
        watcher = t.seat(t.me, "C1", t.card(2000, text="【AUTO】 When your opponent's character becomes 【REVERSE】, this card gets +500 power until end of turn."))
        enemy = t.seat(t.them, "C2", 1)
        t.refresh()
        t.apply(1, {"type": "position", "uid": enemy["uid"], "pos": "reverse"})
        self.assertEqual(t.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_the_middle_position_attacking(self):
        t = Table()
        watcher = t.seat(t.me, "B1", t.card(2000, text="【AUTO】 When your character in the middle position of your center stage attacks, this card gets +500 power until end of turn."))
        left, middle = t.seat(t.me, "C1", 1), t.seat(t.me, "C2", 2)
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": left["uid"], "kind": "direct"})
        self.assertFalse(any(e["uid"] == watcher["uid"] for e in t.state.get("ability_queue", [])))
        t2 = Table()
        watcher = t2.seat(t2.me, "B1", t2.card(2000, text=t.info(2000)["text"]))
        middle = t2.seat(t2.me, "C2", 2)
        t2.state.update(phase="attack", attack={"step": "declare"})
        t2.refresh()
        t2.apply(2, {"type": "attack", "uid": middle["uid"], "kind": "direct"})
        self.assertEqual(t2.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_refreshing_triggers(self):
        t = Table()
        watcher = t.seat(t.me, "C1", t.card(2000, text="【AUTO】 When you refresh your deck, you may put this card into your stock."))
        t.me["zones"]["deck"] = [game.new_card(1)]
        t.me["zones"]["waiting"] = [game.new_card(2), game.new_card(3)]
        t.refresh()
        game.refresh(t.state, "2", lambda pk: "x", no_shuffle)
        game.run_abilities(t.state, game.SimpleNamespace(info=t.info, name=lambda pk: "x"))
        self.assertEqual(t.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_a_card_going_to_memory_triggers(self):
        t = Table()
        watcher = t.seat(t.me, "C1", t.card(2000, text="【AUTO】 When your card is put into your memory, this card gets +500 power until end of turn."))
        event = t.hand(t.card(801, card_type="Event", text="Put this card into your memory."))[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": event["uid"], "to": "resolution"})
        self.fire(t)
        self.assertEqual(t.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_playing_a_named_card_triggers(self):
        t = Table()
        watcher = t.seat(t.me, "C1", t.card(2000, text='【AUTO】 When you play "Named", this card gets +500 power until end of turn.'))
        named = t.hand(t.card(801, name="Named"))[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": named["uid"], "to": "C2"})
        self.assertEqual(t.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_moving_triggers(self):
        t = Table()
        watcher = t.seat(t.me, "B1", t.card(2000, text="【AUTO】 When your character moves to another stage position, this card gets +500 power until end of turn."))
        mover = t.seat(t.me, "C1", 1)
        t.refresh()
        t.apply(2, {"type": "move", "uid": mover["uid"], "to": "C2"})
        self.assertEqual(t.state["ability_queue"][0]["uid"], watcher["uid"])

    def test_opponent_cannot_play_events(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, until the end of your opponent's next turn, your opponent cannot play event from your hand.")
        self.fire(t)
        self.shows(t)
        event = game.new_card(t.card(801, card_type="Event"))
        t.them["zones"]["hand"].append(event)
        with self.assertRaisesMessage(game.GameError, "events"):
            t.apply(1, {"type": "move", "uid": event["uid"], "to": "resolution"})
        game.finish_turn(t.state, "2", lambda pk: "x")
        self.assertTrue(game.banned(t.state, "1", "event"))  # through their next turn
        game.finish_turn(t.state, "1", lambda pk: "x")
        self.assertFalse(game.banned(t.state, "1", "event"))

    def test_no_backup_this_turn(self):
        t, _ = self.play('【AUTO】 When this card is placed on the stage from your hand, until end of turn, your opponent cannot use "Backup".')
        self.fire(t)
        self.shows(t)
        t.card(801, text="【ACT】 【COUNTER】 Backup 1000, Level 0 [Put this card from your hand into your waiting room]")
        self.assertIsNone(game.counter_play(t.state, "1", game.new_card(801), t.info))

    def test_this_card_and_a_marker_go_under_the_new_character(self):
        text = ("【AUTO】 Inspire When your other character is placed on the stage from your hand, if there are no markers underneath that character, you may choose this card and up to 1 marker underneath this card, "
                "and put them face up underneath that card in any order as markers. If you do, put the rest of the markers into your waiting room.")
        self.assertEqual(abilities.by_hand_parts(text), [])
        t = Table()
        me = t.seat(t.me, "C1", t.card(2000, text=text))
        keep, drop = game.new_card(1), game.new_card(2)
        t.me["markers"]["C1"] = [keep, drop]
        arrival = t.hand(t.card(801))[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": arrival["uid"], "to": "C2"})
        self.fire(t)
        t.apply(2, {"type": "ability_answer", "uids": [keep["uid"]]})
        self.assertIsNone(t.me["stage"]["C1"])
        self.assertEqual(sorted(c["uid"] for c in t.me["markers"]["C2"]), sorted([me["uid"], keep["uid"]]))
        self.assertIn(drop["uid"], [c["uid"] for c in t.me["zones"]["waiting"]])

    def test_a_marker_from_the_hand_as_a_cost(self):
        text = '【ACT】 [Put 1 "Named" from your hand face up underneath this card as a marker] Draw 1 card.'
        self.assertEqual(abilities.by_hand_parts(text), [])
        t = Table()
        me = t.seat(t.me, "C1", t.card(2000, text=text))
        named = t.hand(t.card(801, name="Named"))[0]
        t.refresh()
        t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
        t.apply(2, {"type": "ability_answer", "uids": [named["uid"]]})
        self.assertEqual(t.me["markers"]["C1"][0]["uid"], named["uid"])


class UnplayableMarkTests(TestCase):
    MARK = "cpu-flag"

    def setUp(self):
        common = {"expansion": "E", "expansion_id": 77, "card_type": "Character", "level": 0}
        self.bad = Card.objects.create(serial_number="MRK/1", name="Bad One", description="【AUTO】 When this card attacks, juggle the dice.", **common)
        self.good = Card.objects.create(serial_number="MRK/2", name="Good One", description="【AUTO】 When this card attacks, draw 1 card.", **common)
        self.staff = User.objects.create_user("staff2", password="x", is_staff=True)
        self.player = User.objects.create_user("player3", password="x")
        Group.objects.get_or_create(name=WEISS_GROUP)[0].user_set.add(self.player)

    def pages(self, user):
        deck = CardList.objects.create(user=user, name="Marked")
        CardListEntry.objects.create(card_list=deck, card=self.bad, quantity=1)
        self.client.force_login(user)
        session = self.client.session
        session["weiss_editing_list"] = deck.pk
        session.save()
        return [reverse("weiss:set", args=[77]), reverse("weiss:card", args=[self.bad.pk]), reverse("weiss:card_popup", args=[self.bad.pk]), reverse("weiss:list", args=[deck.pk])]

    def test_staff_see_it_everywhere_a_card_shows(self):
        for url in self.pages(self.staff):
            self.assertContains(self.client.get(url), self.MARK)

    def test_players_never_do(self):
        for url in self.pages(self.player):
            self.assertNotContains(self.client.get(url), self.MARK)

    def test_it_says_why_on_the_card(self):
        self.pages(self.staff)
        self.assertContains(self.client.get(reverse("weiss:card", args=[self.bad.pk])), "juggle the dice")

    def test_a_playable_card_has_no_mark(self):
        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(reverse("weiss:card", args=[self.good.pk])), self.MARK)

    def test_the_side_panel_keeps_it_when_redrawn(self):
        pages = self.pages(self.staff)
        deck = CardList.objects.get(user=self.staff)
        data = self.client.post(reverse("weiss:list_change", args=[deck.pk]), {"card": self.good.pk, "delta": 1}, HTTP_ACCEPT="application/json").json()
        self.assertIn(self.MARK, data["panel"])


class AuditFixesTests(TestCase):
    def test_the_top_of_their_deck_is_the_top(self):
        step = abilities.parse("【AUTO】 When this card attacks, put the top X of your opponent's deck into his or her waiting room. X is equal to the number of 《Music》 characters you have.")[0]["steps"][0]
        self.assertEqual((step["do"], step["owner"], step.get("bottom")), ("top", "opp", None))
        self.assertEqual(step["x"]["of"], "my_chars")

    def test_one_loses_and_the_other_gains(self):
        steps = abilities.parse("【AUTO】 When this card attacks, choose 1 of your opponent's characters, and that character gets -1000 power and this card gets +1000 power until end of turn.")[0]["steps"]
        self.assertEqual([(s["target"], s["power"]) for s in steps if s["do"] == "buff"], [("it", -1000), ("self", 1000)])

    def test_except_climax_cards(self):
        steps = abilities.parse("Choose up to five cards in your waiting room except climax cards, and return them to your deck.")[0]["steps"]
        self.assertEqual((steps[0]["zone"], steps[0]["filter"]["not_climax"]), ("waiting", True))

    def test_another_of_a_card_in_memory_doesnt_count_itself(self):
        t = Table()
        t.card(800, name="Twin")
        me = game.new_card(800)
        t.me["zones"]["memory"] = [me]
        cond = abilities.parse_condition("if you do not have another ⟦0⟧ in your memory", ["Twin"])
        self.assertTrue(cond["not_self"])
        env = game.SimpleNamespace(info=t.info)
        self.assertTrue(game.condition_met(cond, t.state, "2", me, {}, env))
        t.me["zones"]["memory"].append(game.new_card(800))
        self.assertFalse(game.condition_met(cond, t.state, "2", me, {}, env))

    def test_an_older_counter_can_be_played_as_one(self):
        t = Table()
        t.card(2000, text="COUNTER@ Backup 2500, Level 0 [Put this card from your hand into your waiting room]")
        self.assertEqual(game.counter_play(t.state, "2", game.new_card(2000), t.info), (0, 2500))
        self.assertEqual(abilities.by_hand_parts(t.info(2000)["text"]), [])

    def test_a_backup_on_a_later_line_of_text(self):
        t = Table()
        t.card(2000, text="【CONT】 This card gets +500 power.\nBackup 1500, Level 0 [(1) Put this card from your hand into your waiting room]")
        t.stock(1)
        self.assertEqual(game.counter_play(t.state, "2", game.new_card(2000), t.info), (1, 1500))


class FourthBatchTests(TestCase):
    def fire(self, t):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def play(self, text, **details):
        t = Table()
        t.card(2000, text=text, **details)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        return t, card

    def test_choosing_up_to_x(self):
        text = "【AUTO】 When this card is placed on the stage from your hand, choose up to X cards in your opponent's waiting room, and return them to their deck. X is equal to your level."
        self.assertEqual(abilities.by_hand_parts(text), [])
        t, _ = self.play(text)
        t.them["zones"]["waiting"] = [game.new_card(1), game.new_card(2), game.new_card(3)]
        t.level(2)
        self.fire(t)
        self.assertEqual(t.state["resolving"]["prompt"]["max"], 2)

    def test_up_to_x_of_nothing_asks_nothing(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, choose up to X cards in your opponent's waiting room, and return them to their deck. X is equal to your level.")
        t.them["zones"]["waiting"] = [game.new_card(1)]
        self.fire(t)
        self.assertFalse(t.state.get("resolving"))
        self.assertEqual(len(t.them["zones"]["waiting"]), 1)

    def test_several_things_gained_with_a_comma(self):
        step = abilities.parse('【AUTO】 When this card attacks, this card gets +1000 power, +1 soul and the following ability until end of turn. "【AUTO】 When this card attacks, draw 1 card."')[0]["steps"][0]
        self.assertEqual((step["power"], step["soul"], len(step["grant"])), (1000, 1, 1))

    def test_each_part_lasts_as_long_as_it_says(self):
        steps = abilities.parse('【AUTO】 When this card attacks, this card gets +1000 power until end of turn and the following ability until the end of your opponent\'s next turn. "【CONT】 This card gets +500 power."')[0]["steps"]
        self.assertEqual([(s["until"], s["power"], len(s["grant"])) for s in steps], [("turn", 1000, 0), ("next", 0, 1)])

    def test_all_characters_in_battle(self):
        t, card = self.play('【AUTO】 When this card is placed on the stage from your hand, all of your characters in your center stage get +500 power until end of turn.')
        back = t.seat(t.me, "B1", 1)
        self.fire(t)
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        t.refresh()
        self.assertEqual(t.state["stats"][card["uid"]]["power"], 1500)
        self.assertEqual(t.state["stats"][back["uid"]]["power"], 1000)

    def test_damage_to_all_players(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, deal 1 damage to all players.")
        self.fire(t)
        self.assertEqual((len(t.them["zones"]["clock"]), len(t.me["zones"]["clock"])), (1, 1))

    def test_a_card_going_face_down_as_a_cost(self):
        text = "【ACT】 [Put a face up card in your level face down] Draw 1 card."
        self.assertEqual(abilities.by_hand_parts(text), [])
        t = Table()
        me = t.seat(t.me, "B1", t.card(2000, text=text))
        up = game.new_card(1)
        down = game.new_card(2)
        down["face_down"] = True
        t.me["zones"]["level"] = [up, down]
        t.refresh()
        t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [up["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [up["uid"]]})
        self.assertTrue(up["face_down"])

    def test_no_face_up_card_cant_pay(self):
        t = Table()
        down = game.new_card(2)
        down["face_down"] = True
        t.me["zones"]["level"] = [down]
        self.assertTrue(game.can_pay([{"part": "level_face_down"}], t.state, "2", None, game.SimpleNamespace(info=t.info)))


class ThirdExportTests(TestCase):
    """Mechanics that the newer export of unplayable cards needed, played through the game."""

    def play(self, text, stock=0, **details):
        t = Table()
        t.card(2000, text=text, **details)
        card = t.hand(2000)[0]
        t.stock(stock)
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        return t, card

    def fire(self, t):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def shows(self, t):
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})

    def fits(self, t, card, trait):
        return game.fits({"any": [{"trait": trait}]}, card, game.SimpleNamespace(info=t.info))

    def test_gaining_a_trait_until_end_of_turn(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, this card gets +1000 power and 《Hero》 until end of turn.", traits="Villain")
        self.assertFalse(self.fits(t, card, "Hero"))
        self.fire(t)
        self.shows(t)
        self.assertTrue(self.fits(t, card, "Hero"))
        self.assertTrue(self.fits(t, card, "Villain"))
        game.finish_turn(t.state, "2", lambda pk: "x")
        self.assertFalse(self.fits(t, card, "Hero"))

    def test_losing_a_chosen_trait(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, choose 1 of your opponent's characters and 1 trait of that character, and that character loses all of that trait until end of turn.")
        enemy = t.seat(t.them, "C2", t.card(700, traits="Hero・Mage"))
        t.refresh()
        self.fire(t)
        t.apply(2, {"type": "ability_answer", "uids": [enemy["uid"]]})
        self.assertEqual([o["value"] for o in t.state["resolving"]["prompt"]["options"]], ["Hero", "Mage"])
        t.apply(2, {"type": "ability_answer", "value": "Hero"})
        self.assertFalse(self.fits(t, enemy, "Hero"))
        self.assertTrue(self.fits(t, enemy, "Mage"))
        game.finish_turn(t.state, "2", lambda pk: "x")
        self.assertTrue(self.fits(t, enemy, "Hero"))

    def test_a_trait_given_while_a_condition_holds(self):
        t = Table()
        card = t.seat(t.me, "C1", t.card(2000, text="【CONT】 If your level is 1 or higher, this card gets 《Hero》."))
        t.refresh()
        self.assertFalse(self.fits(t, card, "Hero"))
        t.level(1)
        t.refresh()
        self.assertTrue(self.fits(t, card, "Hero"))
        t.me["zones"]["level"] = []
        t.refresh()
        self.assertFalse(self.fits(t, card, "Hero"))

    def attack_table(self, text):
        t = Table()
        card = t.seat(t.me, "C1", t.card(2000, text=text, power=9000))
        t.seat(t.them, "C3", t.card(700, power=1000))
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        return t, card

    def test_cannot_side_attack_is_enforced(self):
        t, card = self.attack_table("【CONT】 This card cannot side attack.")
        with self.assertRaises(game.GameError):
            t.apply(2, {"type": "attack", "uid": card["uid"], "kind": "side"})
        t.apply(2, {"type": "attack", "uid": card["uid"], "kind": "front"})

    def test_cannot_attack_while_a_condition_holds(self):
        t, card = self.attack_table("【CONT】 If you do not have another 《Hero》 character, this card cannot attack.")
        self.assertEqual(t.state["attack_bans"]["2"], {card["uid"]: ["all"]})
        with self.assertRaises(game.GameError):
            t.apply(2, {"type": "attack", "uid": card["uid"], "kind": "front"})
        self.assertEqual(t.next(), {"type": "phase", "phase": "encore"})

    def test_the_cpu_keeps_to_what_it_may_do(self):
        t, card = self.attack_table("【CONT】 This card cannot frontal attack.")
        self.assertEqual(t.next()["kind"], "side")

    def test_a_card_forced_to_front_attack_does(self):
        t, card = self.attack_table("【CONT】 This card cannot side attack.")
        t.cards[2000]["power"] = 0
        t.refresh()
        self.assertEqual(t.next()["kind"], "front")

    def test_cannot_frontal_attack_until_end_of_turn(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, this card cannot frontal attack until end of turn.")
        self.fire(t)
        t.refresh()
        self.assertEqual(t.state["attack_bans"]["2"][card["uid"]], ["front"])
        self.assertEqual(abilities.by_hand_parts(t.info(2000)["text"]), [])

    def test_every_attack_ban_can_be_carried_out(self):
        for words, ban in (("cannot frontal attack", "front"), ("cannot side attack", "side"), ("cannot attack", "all")):
            t, card = self.play(f"【AUTO】 When this card is placed on the stage from your hand, this card {words} until end of turn.")
            self.fire(t)
            t.refresh()
            self.assertEqual(t.state["attack_bans"]["2"][card["uid"]], [ban], words)
            self.assertIn("this turn", t.state["log"][-1]["text"])

    def test_an_opponent_paying_to_stop_a_frontal_attack(self):
        t = Table()
        card = t.seat(t.me, "C1", t.card(2000, text="【AUTO】 At the beginning of your climax phase, your opponent may put the top 2 cards of their stock into their waiting room. If they do, this card cannot frontal attack until end of turn."))
        t.them["zones"]["stock"] = [game.new_card(1), game.new_card(2)]
        t.refresh()
        game.fire(t.state, game.SimpleNamespace(info=t.info, name=lambda pk: "x"), "phase", phase="climax", player="2")
        self.fire(t)
        t.apply(1, {"type": "ability_answer", "value": "yes"})
        t.refresh()
        self.assertEqual(t.them["zones"]["stock"], [])
        self.assertEqual(t.state["attack_bans"]["2"][card["uid"]], ["front"])

    def test_declining_a_follow_up_ends_a_chain_of_cancelled_damage(self):
        text = ("【AUTO】 When this card is placed on the stage from your hand, deal 1 damage to your opponent. If this damage is canceled, you may deal 2 damage to your opponent. "
                "If this damage is canceled, you may deal 3 damage to your opponent.")
        t = Table()
        t.card(2000, text=text)
        t.card(913, card_type="Climax", level=None, cost=None, power=None)
        t.them["zones"]["deck"] = [game.new_card(1) for _ in range(10)] + [game.new_card(913)]
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        self.fire(t)
        t.apply(1, {"type": "resolve_damage"})
        self.shows(t)
        t.apply(2, {"type": "ability_answer", "value": "no"})
        self.shows(t)
        self.assertFalse(t.state.get("resolving"))

    def test_same_damage_as_what_was_cancelled(self):
        ability = abilities.parse("【AUTO】 When damage dealt by this card is canceled, you may deal the same damage to your opponent.")[0]
        self.assertEqual(ability["when"], [{"on": "cancel"}])
        self.assertEqual(ability["steps"][0]["then"][0]["from_ctx"], "damage_amount")
        t = Table()
        card = t.seat(t.me, "C1", t.card(2000, text=ability["text"]))
        self.assertEqual(game.when_matches(ability["when"][0], "cancel", {"uid": card["uid"], "amount": 3}, "2", card, game.SimpleNamespace(info=t.info)), {"damage_amount": 3})

    def test_if_this_damage_is_cancelled(self):
        text = "【AUTO】 When this card is placed on the stage from your hand, deal 2 damage to your opponent. If this damage is canceled, you may deal 1 damage to your opponent."
        self.assertEqual(abilities.by_hand_parts(text), [])
        t = Table()
        t.card(2000, text=text)
        t.card(913, card_type="Climax", level=None, cost=None, power=None)
        t.them["zones"]["deck"] = [game.new_card(1) for _ in range(10)] + [game.new_card(913)]
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        self.fire(t)
        self.assertTrue(t.state.get("pending_damage"))
        t.apply(1, {"type": "resolve_damage"})
        self.shows(t)
        self.assertEqual(t.state["resolving"]["prompt"]["for"], "may")

    def test_an_uncancelled_damage_has_no_follow_up(self):
        text = "【AUTO】 When this card is placed on the stage from your hand, deal 1 damage to your opponent. If this damage is canceled, you may deal 1 damage to your opponent."
        t, _ = self.play(text)
        t.them["zones"]["deck"][-1] = game.new_card(1)
        self.fire(t)
        self.shows(t)
        self.assertFalse(t.state.get("resolving"))

    DECLARE = ("【AUTO】 When this card is placed on the stage from your hand, your opponent declares 0 or 1 or 2 or 3. Reveal the top card of your deck, "
               "and if that card is a character of the level that your opponent declared, put it on any position of your stage. (Otherwise, return it to its original place)")

    def test_the_opponent_declares_and_a_match_comes_out(self):
        self.assertEqual(abilities.by_hand_parts(self.DECLARE), [])
        t, _ = self.play(self.DECLARE)
        t.card(915, level=2)
        top = game.new_card(915)
        t.me["zones"]["deck"].append(top)
        self.fire(t)
        self.assertEqual(t.state["resolving"]["prompt"]["player"], "1")
        t.apply(1, {"type": "ability_answer", "value": 2})
        self.shows(t)
        self.assertEqual(t.state["resolving"]["prompt"]["for"], "place")
        t.apply(2, {"type": "ability_answer", "value": "C2"})
        self.assertEqual(t.me["stage"]["C2"]["uid"], top["uid"])

    def test_a_wrong_declaration_leaves_it_on_the_deck(self):
        t, _ = self.play(self.DECLARE)
        t.card(915, level=2)
        top = game.new_card(915)
        t.me["zones"]["deck"].append(top)
        self.fire(t)
        t.apply(1, {"type": "ability_answer", "value": 1})
        self.shows(t)
        self.assertEqual(t.me["zones"]["deck"][-1]["uid"], top["uid"])
        self.assertFalse(t.state.get("resolving"))

    def test_revealing_a_hand_can_be_read_from(self):
        text = "【AUTO】 When this card attacks, you may reveal your hand. If you do, if there is a climax among those cards, this card gets +2000 power until end of turn."
        self.assertEqual(abilities.by_hand_parts(text), [])

    def test_placed_by_a_named_effect(self):
        ability = abilities.parse('【AUTO】 [(1)] During your climax phase, when this card is placed on the stage by the effect of "Sunny Day", you may pay the cost. If you do, 【STAND】 this card.')[0]
        self.assertEqual(ability["when"][0]["on"], "placed_by")
        t = Table()
        t.card(916, name="Sunny Day")
        card = game.new_card(1)
        env = game.SimpleNamespace(info=t.info)
        self.assertEqual(game.when_matches(ability["when"][0], "placed", {"uid": card["uid"], "by": 916}, "2", card, env), {})
        self.assertIsNone(game.when_matches(ability["when"][0], "placed", {"uid": card["uid"], "by": 1}, "2", card, env))

    def test_a_placement_tells_who_placed_it(self):
        t, _ = self.play('【AUTO】 When this card is placed on the stage from your hand, choose 1 character in your waiting room, and put it in any position of your stage.')
        t.card(917, text='【AUTO】 When this card is placed on the stage by the effect of "Card2000", draw 1 card.')
        t.cards[2000]["name"] = "Card2000"
        arrival = game.new_card(917)
        t.me["zones"]["waiting"] = [arrival]
        self.fire(t)
        t.apply(2, {"type": "ability_answer", "uids": [arrival["uid"]]})
        t.apply(2, {"type": "ability_answer", "value": "C2"})
        self.assertEqual(t.state["ability_queue"][0]["uid"], arrival["uid"])

    def test_wiping_the_stage_spares_this_card(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, put all players' characters except this card into their waiting rooms.")
        t.seat(t.me, "C2", 1)
        t.seat(t.them, "C2", 2)
        self.fire(t)
        self.assertEqual([c["uid"] for c in game.stage_cards(t.me)], [card["uid"]])
        self.assertEqual(game.stage_cards(t.them), [])

    def test_a_shift_with_a_full_stop_reads(self):
        self.assertEqual(abilities.by_hand_parts("【AUTO】【CLOCK】 Shift, Level 0 (At the beginning of your main phase, you may choose a green card in your hand and this card in your clock, and exchange them.)"), [])

    def test_the_opponent_may_choose_from_my_waiting_room(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, your opponent may choose a character in your waiting room, and put it on the top of your deck.")
        mine = game.new_card(1)
        t.me["zones"]["waiting"] = [mine]
        self.fire(t)
        t.apply(1, {"type": "ability_answer", "value": "yes"})
        self.assertEqual(t.state["resolving"]["prompt"]["player"], "1")
        t.apply(1, {"type": "ability_answer", "uids": [mine["uid"]]})
        self.assertEqual(t.me["zones"]["deck"][-1]["uid"], mine["uid"])

    def test_cards_except_climaxes(self):
        f = abilities.parse_filter("cards except climax", [])
        self.assertFalse(abilities.matches_filter(f, {"card_type": "Climax"}))
        self.assertTrue(abilities.matches_filter(f, {"card_type": "Event"}))


class ReportedComboTests(TestCase):
    """Cards reported as missing from CPU decks, played through the game."""

    RELOAD = ('【AUTO】 When this card is placed on the stage from your hand, you may put the top card of your clock into your waiting room.\n'
              '【AUTO】 【CXCOMBO】 When this card attacks, if "DONE AND DUSTED." is in your climax area, and all of your characters are 《Reload》, choose 1 of the following effects, and perform it. '
              '"Choose up to 1 《Reload》 or 《Magic》 or 《Weapon》 character in your waiting room, or up to 1 of your opponent\'s characters, return it to their respective player\'s hands, and put up to 1 card from the top of your deck into your stock." '
              '"[Put 1 《Reload》 or 《Magic》 or 《Weapon》 character from your hand into your waiting room] You may pay the cost. If you do, deal 2 damage to your opponent." (Damage may be canceled)')
    PARTNER = ('【AUTO】 [Put 1 《Reload》 or 《Magic》 or 《Weapon》 character from your hand into your waiting room] When this card is placed on the stage from your hand, you may pay the cost. If you do, draw 1 card.\n'
               '【AUTO】 【CXCOMBO】 [Put this 【STAND】 card into your memory] During your climax phase, when "DONE AND DUSTED." is placed on your climax area, you may pay the cost. If you do, choose up to 1 "Protagonist & Thanatos: Reload" in your hand, and put it in the stage position that this card was in.')
    THANKS = ('【AUTO】 When this card is placed on the stage from your hand, draw up to one card, and this card gets +2000 power until end of turn.\n'
              '【AUTO】 【CXCOMBO】 When this card attacks, if a card named "Thank You..." is in your climax area, you may deal one damage to your opponent. (This damage may be canceled)\n'
              '【AUTO】 [(2)] When this card\'s battle opponent becomes 【REVERSE】, you may pay the cost. If you do, deal one damage to your opponent. (This damage may be canceled)')
    CORPS = ('【CONT】 If you have 2 or more other 《Eldian》 or 《Corps》 characters, this card gets +1000 power.\n'
             '【AUTO】 【CXCOMBO】 When this card attacks, if "Perfect Timing" is in your climax area, and all of your characters are 《Eldian》 or 《Corps》, look at up to 4 cards from the top of your deck, choose up to 1 "New Omni Directional Mobility Gear" or 《Eldian》 or 《Corps》 character from among them, reveal it to your opponent, put it into your hand, put the rest into your waiting room, and this card gets +1000 power until end of turn.')
    TITAN = ('【CONT】 If you have 2 or more other 《Eldian》 or 《Titan》 characters, this card gets +1500 power and "【AUTO】 Encore [Put 1 《Eldian》 or 《Titan》 character from your hand into your waiting room]".\n'
             '【AUTO】 【CXCOMBO】 [(2) Put 1 card from your hand into your waiting room] When this card attacks, if "Facing Off" is in your climax area, and you have 4 or more other 《Eldian》 or 《Titan》 characters, you may pay the cost. If you do, reveal the top 9 cards of your deck, shuffle your deck, and deal X damage to your opponent 2 times. X is equal to the total number of [gate] in the trigger icons of those cards. (Damage may be canceled. Return the revealed cards to their original places)')

    def test_none_of_them_need_anything_done_by_hand(self):
        for text in (self.RELOAD, self.PARTNER, self.THANKS, self.CORPS, self.TITAN):
            self.assertEqual(abilities.by_hand_parts(text), [], text[:60])

    def finish_stock_prompt(self, t, stock_before):
        prompt = t.state["resolving"]["prompt"]
        t.apply(2, {"type": "ability_answer", "value": 1 if prompt["kind"] == "choice" else None})
        self.assertEqual(len(t.me["zones"]["stock"]), stock_before + 1)

    def test_reload_returns_one_from_my_waiting_room(self):
        mine = game.new_card(911)
        t = self.attack_with_reload_after(lambda t: (t.card(911, traits="Magic"), t.me["zones"]["waiting"].append(mine)))
        t.apply(2, {"type": "ability_answer", "value": 0})
        t.apply(2, {"type": "ability_answer", "uids": [mine["uid"]]})
        self.assertIn(mine["uid"], [c["uid"] for c in t.me["zones"]["hand"]])
        self.finish_stock_prompt(t, 0)

    def test_reload_returns_an_opposing_character_to_its_owner(self):
        enemy = game.new_card(700)
        t = self.attack_with_reload_after(lambda t: t.them["stage"].__setitem__("C2", {**enemy, "pos": "stand"}))
        t.apply(2, {"type": "ability_answer", "value": 1})
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [enemy["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [enemy["uid"]]})
        self.assertIn(enemy["uid"], [c["uid"] for c in t.them["zones"]["hand"]])
        self.assertIsNone(t.them["stage"]["C2"])
        self.finish_stock_prompt(t, 0)

    def attack_with_reload_after(self, setup):
        t = Table()
        t.card(2000, text=self.RELOAD, traits="Reload")
        t.card(910, name="DONE AND DUSTED.", card_type="Climax", level=None, cost=None, power=None)
        t.me["zones"]["climax"].append(game.new_card(910))
        setup(t)
        me = t.seat(t.me, "C1", 2000)
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": me["uid"], "kind": "direct"})
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_answer", "value": 0})
        return t

    def test_the_cpu_can_play_reload_through(self):
        t = self.attack_with_reload_after(lambda t: (t.card(911, traits="Magic"), t.me["zones"]["waiting"].append(game.new_card(911))))
        for _ in range(8):
            if not t.state.get("resolving"):
                break
            t.apply(2, t.next())
        self.assertFalse(t.state.get("resolving"))

    def test_titan_deals_x_twice_counting_gates_among_the_nine(self):
        t = Table()
        t.card(2000, text=self.TITAN, traits="Titan")
        t.card(800, traits="Eldian")
        t.card(910, name="Facing Off", card_type="Climax", level=None, cost=None, power=None)
        t.card(912, trigger="gate")
        t.me["zones"]["climax"].append(game.new_card(910))
        me = t.seat(t.me, "C1", 2000)
        for slot in ("C2", "C3", "B1", "B2"):
            t.seat(t.me, slot, 800)
        t.me["zones"]["deck"][-9:] = [game.new_card(912) if i < 2 else game.new_card(1) for i in range(9)]
        t.them["zones"]["deck"] = [game.new_card(1) for _ in range(20)]
        t.stock(2)
        pay = t.hand(1)[0]
        t.state.update(phase="attack", attack={"step": "declare"})
        t.refresh()
        t.apply(2, {"type": "attack", "uid": me["uid"], "kind": "direct"})
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_answer", "uids": [pay["uid"]]})
        self.assertEqual(len(t.them["zones"]["clock"]), 4)  # 2 gates, twice; the attack's own damage comes after

    def test_titan_first_hit_cancelled_doesnt_lose_the_second(self):
        t = Table()
        t.card(2000, text="【ACT】 [(0)] Reveal the top 9 cards of your deck, shuffle your deck, and deal X damage to your opponent 2 times. X is equal to the total number of [gate] in the trigger icons of those cards.")
        t.card(912, trigger="gate")
        t.card(913, card_type="Climax", level=None, cost=None, power=None)
        me = t.seat(t.me, "B1", 2000)
        t.me["zones"]["deck"][-9:] = [game.new_card(912) if i < 2 else game.new_card(1) for i in range(9)]
        # The first hit's second card is a climax: it cancels, and those two go to the waiting room.
        t.them["zones"]["deck"] = [game.new_card(1) for _ in range(10)] + [game.new_card(913), game.new_card(1)]
        t.refresh()
        t.apply(2, {"type": "activate", "uid": me["uid"], "index": 0})
        for _ in range(10):
            if t.state.get("pending_damage"):
                t.apply(1, {"type": "resolve_damage"})
            elif t.state.get("ability_show"):
                t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
            else:
                break
        self.assertEqual(len(t.them["zones"]["waiting"]), 2)
        self.assertEqual(len(t.them["zones"]["clock"]), 2)

    def test_the_partner_swaps_itself_for_the_named_card(self):
        t = Table()
        t.card(2000, text=self.PARTNER, traits="Reload")
        t.card(910, name="DONE AND DUSTED.", card_type="Climax", level=None, cost=None, power=None)
        t.card(913, name="Protagonist & Thanatos: Reload", traits="Reload")
        me = t.seat(t.me, "C2", 2000)
        climax, named = t.hand(910, 913)
        t.state["phase"] = "climax"
        t.refresh()
        t.apply(2, {"type": "move", "uid": climax["uid"], "to": "climax"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_answer", "uids": [named["uid"]]})
        self.assertEqual(t.me["stage"]["C2"]["uid"], named["uid"])
        self.assertEqual(t.me["zones"]["memory"][-1]["uid"], me["uid"])

    def test_thanks_draws_and_boosts_when_played(self):
        t = Table()
        t.card(2000, text=self.THANKS, power=1000)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_answer", "value": 1})
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        t.refresh()
        self.assertEqual(len(t.me["zones"]["hand"]), 1)
        self.assertEqual(t.state["stats"][card["uid"]]["power"], 3000)

    def test_a_card_naming_them_is_now_a_usable_anchor(self):
        common = {"expansion": "E", "expansion_id": 9, "traits": "Reload", "power": 1000, "soul": 1, "level": 0}
        Card.objects.create(serial_number="RLD/1", name="Protagonist & Thanatos: Reload", card_type="Character", description=self.RELOAD, **common)
        Card.objects.create(serial_number="RLD/2", name="Partner", card_type="Character", description=self.PARTNER, **common)
        self.assertEqual({c.name for c in express.cpu_anchor_choices("RLD")}, {"Protagonist & Thanatos: Reload", "Partner"})


class ReportedLeviTests(TestCase):
    TEXT = ("【CONT】 If the number of your 《Corps》 characters is four or more, this card gets -1 level while in your hand.\n\n\n"
            "【CONT】 If all of your characters are 《Corps》, this card gets +1000 power.\n\n\n"
            '【CONT】 During this card\'s battle, all players cannot play "Backup" from hand.')

    def test_nothing_on_the_card_needs_doing_by_hand(self):
        self.assertEqual(abilities.by_hand_parts(self.TEXT), [])

    def test_every_line_does_something(self):
        lowered, boost, backup = abilities.parse(self.TEXT)
        self.assertEqual(lowered["hand_mod"]["level"], -1)
        self.assertEqual(boost["effects"][0]["power"], 1000)
        self.assertTrue(backup["no_backup"])

    def test_it_counts_four_characters_of_the_trait(self):
        t = Table()
        t.card(2000, text=self.TEXT, level=2)
        t.card(800, traits="Corps")
        card = game.new_card(2000)
        for slot in ("C1", "C2", "C3"):
            t.seat(t.me, slot, 800)
        self.assertEqual(game.play_level(t.state, "2", card, t.info), 2)
        t.seat(t.me, "B1", 800)
        self.assertEqual(game.play_level(t.state, "2", card, t.info), 1)

    def test_a_cpu_deck_with_it_is_ready(self):
        self.assertEqual(abilities.by_hand_parts('【CONT】 If the number of your other 《Corps》 or 《Scouts》 characters is 2 or less, this card gets -1 level while in your hand.'), [])


class NotPlayedThisTurnTests(TestCase):
    TEXT = ('【CONT】 If you have another "Partner", and you did not play "Big Climax" during this turn, your "Big Climax" get -1 cost while in your hand.')

    def table(self):
        t = Table()
        t.card(800, name="Partner")
        t.card(910, name="Big Climax", card_type="Event", cost=2, level=0, power=None)
        t.seat(t.me, "C1", t.card(2000, text=self.TEXT))
        t.seat(t.me, "C2", 800)
        return t

    def test_it_reads(self):
        self.assertEqual(abilities.by_hand_parts(self.TEXT), [])

    def test_it_applies_until_one_is_played_then_comes_back_next_turn(self):
        t = self.table()
        waiting, first = game.new_card(910), t.hand(910)[0]
        self.assertEqual(game.play_cost(t.state, "2", waiting, t.info), 1)
        t.stock(1)
        t.refresh()
        t.apply(2, {"type": "move", "uid": first["uid"], "to": "resolution"})
        self.assertEqual(len(t.me["zones"]["stock"]), 0)  # paid the lower cost
        self.assertEqual(game.play_cost(t.state, "2", waiting, t.info), 2)
        game.finish_turn(t.state, "2", lambda pk: "x")
        self.assertEqual(game.play_cost(t.state, "2", waiting, t.info), 1)


class DamageNegatedTests(TestCase):
    def damage(self, t, top):
        t.them["zones"]["deck"][-1]["card"] = top
        game.deal_damage(t.state, "1", 2, 2, [], lambda pk: "x", lambda pk: t.info(pk)["card_type"] == "Climax")

    def table(self):
        t = Table()
        t.card(901, card_type="Climax", name="Big Climax", power=None, level=None)
        return t

    def test_both_players_are_told_which_climax_negated_it(self):
        t = self.table()
        self.damage(t, 901)
        for viewer, key in ((1, "me"), (2, "opponent")):
            side = game.view(t.state, viewer)[key]
            self.assertEqual((side["negated"], side["negated_card"]), (1, 901))

    def test_the_card_can_be_shown_to_both_players(self):
        t = self.table()
        self.damage(t, 901)
        for viewer in (1, 2):
            self.assertIn(901, game.visible_cards(game.view(t.state, viewer)))

    def test_damage_that_gets_through_says_nothing(self):
        t = self.table()
        self.damage(t, 5)
        self.assertEqual(game.view(t.state, 2)["opponent"]["negated"], 0)

    def test_it_counts_each_time(self):
        t = self.table()
        self.damage(t, 901)
        self.damage(t, 901)
        self.assertEqual(t.them["negated"], 2)

    def test_a_cpu_gives_it_time_to_be_seen(self):
        t = self.table()
        self.damage(t, 901)
        self.assertEqual(cpu.wait_seconds(t.state), 2)


class CharactersWithMarkersTests(TestCase):
    TEXT = "【CONT】 All of your other 《Team DAI-GURREN》 characters with a marker get +500 power."

    def table(self):
        t = Table()
        t.card(800, traits="Team DAI-GURREN", power=3000)
        t.card(801, traits="Someone Else", power=3000)
        self.source = t.seat(t.me, "C1", t.card(2000, text=self.TEXT, traits="Team DAI-GURREN", power=1000))
        self.marked = t.seat(t.me, "C2", 800)
        self.bare = t.seat(t.me, "C3", 800)
        self.outsider = t.seat(t.me, "B1", 801)
        t.me["markers"]["C2"] = [game.new_card(1)]
        t.me["markers"]["B1"] = [game.new_card(1)]
        t.me["markers"]["C1"] = [game.new_card(1)]
        t.refresh()
        return t

    def power(self, t, card):
        return t.state["stats"][card["uid"]]["power"]

    def test_only_characters_of_that_trait_with_a_marker_get_it(self):
        t = self.table()
        self.assertEqual(self.power(t, self.marked), 3500)
        self.assertEqual(self.power(t, self.bare), 3000)
        self.assertEqual(self.power(t, self.outsider), 3000)

    def test_not_this_card_itself(self):
        self.assertEqual(self.power(self.table(), self.source), 1000)

    def test_it_follows_the_markers(self):
        t = self.table()
        t.me["markers"]["C2"] = []
        t.me["markers"]["C3"] = [game.new_card(1)]
        t.refresh()
        self.assertEqual(self.power(t, self.marked), 3000)
        self.assertEqual(self.power(t, self.bare), 3500)

    def test_other_wordings_for_having_markers(self):
        for words in ("with a marker", "with markers", "with 1 or more markers"):
            self.assertTrue(abilities.parse_filter(f"《Hero》 characters {words}", [])["has_markers"], words)

    def test_a_trait_matches_whatever_its_case(self):
        self.assertTrue(abilities.matches_filter({"any": [{"trait": "Team DAI-GURREN"}]}, {"traits": "team dai-gurren・Mecha"}))


class ReportedLagannTests(TestCase):
    TEXT = ('【AUTO】 [(1) Put two cards from your hand into your waiting room] When this card is placed on the stage from your hand, you may pay the cost. If you do, '
            'choose up to two characters in your waiting room with "LAGANN(ラガン)" in its card name, return them to your hand, chooase one of your other 《Team DAI-GURREN》 characters, '
            'and that character gets +1000 power until end of turn.')

    def test_the_whole_effect_happens(self):
        t = Table()
        t.card(2000, text=self.TEXT, traits="Team DAI-GURREN")
        other = t.seat(t.me, "C2", t.card(801, traits="Team DAI-GURREN", power=3000))
        t.card(910, name="LAGANN(ラガン)")
        t.card(911, name="Big LAGANN(ラガン)")
        t.card(912, name="Someone Else")
        card = t.hand(2000)[0]
        payment = t.hand(1, 2)
        t.me["zones"]["waiting"] = [game.new_card(910), game.new_card(911), game.new_card(912)]
        wanted = [c["uid"] for c in t.me["zones"]["waiting"][:2]]
        t.stock(1)
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        t.apply(2, {"type": "ability_answer", "uids": [c["uid"] for c in payment]})
        self.assertEqual(sorted(t.state["resolving"]["prompt"]["options"]), sorted(wanted))
        t.apply(2, {"type": "ability_answer", "uids": wanted})
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [other["uid"]])
        t.apply(2, {"type": "ability_answer", "uids": [other["uid"]]})
        t.refresh()
        self.assertEqual(sorted(c["uid"] for c in t.me["zones"]["hand"]), sorted(wanted))
        self.assertEqual(t.me["zones"]["stock"], [])
        self.assertEqual(t.state["stats"][other["uid"]]["power"], 4000)


class LowerWhileInHandTests(TestCase):
    TEXT = "【CONT】 If you have 2 or more other 《Hero》 characters, this card gets -1 level while in your hand."

    def table(self, text=TEXT, **details):
        t = Table()
        t.card(800, traits="Hero")
        t.card(2000, text=text, level=1, power=9000, color="Red", **details)
        t.cards[2000]["cost"] = details.get("cost", 0)
        self.card = t.hand(2000)[0]
        return t

    def heroes(self, t):
        t.seat(t.me, "B1", 800)
        t.seat(t.me, "B2", 800)

    def play(self, t, to="C1"):
        t.refresh()
        t.apply(2, {"type": "move", "uid": self.card["uid"], "to": to})

    def test_it_reads_as_a_level_change_not_a_step_by_hand(self):
        ability = abilities.parse(self.TEXT)[0]
        self.assertEqual(ability["hand_mod"], {"level": -1, "cost": 0})
        self.assertEqual(abilities.by_hand_parts(self.TEXT), [])

    def test_every_wording_on_the_cards_reads(self):
        for text in ("If your waiting room has 3 or less climax, this card gets -1 level while in your hand.",
                     'If "Name" is in your clock, this card gets -1 level while in your hand.',
                     'If a card named "Name" is in your clock, this card gets -1 level while in your hand.',
                     'If you have "One" and "Other", this card gets -1 level while in your hand.',
                     "If your opponent has a level 3 or higher character, this card gets -1 level while in your hand.",
                     "When your opponent has a level 3 or higher character, this card gets -1 level while in your hand.",
                     "If your waiting room has 3 or more climax with [treasure] in the trigger icons, this card gets -1 level while in your hand.",
                     'If you have 2 or more "Name" in your waiting room, this card gets -1 level while in your hand.',
                     'Experience If "One" and "Other" are in your level, this card gets -1 level while in your hand.',
                     "Memory If your memory has 2 or more green cards, this card gets -1 level while in your hand.",
                     "If the number of climax in your waiting room is 2 or less, this card gets -1 level while in your hand.",
                     "If you or your opponent has 2 or less climax in the waiting room, this card gets -1 level while in your hand.",
                     "If there are 2 or less climax in your waiting room, this card gets -1 level while in your hand.",
                     'If there is a card named "Name" in your clock, this card gets -1 level while in your hand.',
                     "If your level is 1, and there is a blue card in your clock, this card gets -1 levels and -1 cost while in your hand.",
                     "If your deck has 5 or less cards, this card gets -1 level while in your hand.",
                     "This card gets -1 level while in your hand."):
            ability = abilities.parse("【CONT】 " + text)[0]
            self.assertIn("hand_mod", ability, text)
            self.assertEqual(abilities.by_hand_parts("【CONT】 " + text), [], text)

    def test_a_trait_with_a_comma_in_its_name(self):
        text = "【CONT】 If you have 4 or more 《Anniversary》 or 《Hello, Happy World!》 characters, this card gets -1 level while in your hand."
        self.assertEqual(abilities.parse(text)[0]["cond"][0]["filter"]["any"][1]["trait"], "Hello, Happy World!")

    def test_a_condition_it_cant_read_is_done_by_hand_not_ignored(self):
        self.assertTrue(abilities.by_hand_parts("【CONT】 If the moon is full, this card gets -1 level while in your hand."))

    def test_level_is_enforced_when_playing_from_hand(self):
        t = Table()
        t.card(2000, level=2, power=9000)
        self.card = t.hand(2000)[0]
        with self.assertRaisesMessage(game.GameError, "level 2"):
            self.play(t)
        t.level(2)
        self.play(t)
        self.assertEqual(t.me["stage"]["C1"]["uid"], self.card["uid"])

    def test_with_the_rules_off_level_doesnt_matter(self):
        t = Table()
        t.card(2000, level=3)
        self.card = t.hand(2000)[0]
        t.state["rules"] = False
        self.play(t)
        self.assertEqual(t.me["stage"]["C1"]["uid"], self.card["uid"])

    def test_it_can_only_be_played_early_when_the_condition_holds(self):
        t = self.table()
        with self.assertRaises(game.GameError):
            self.play(t)
        self.heroes(t)
        self.play(t)
        self.assertEqual(t.me["stage"]["C1"]["uid"], self.card["uid"])

    def test_lowered_to_level_0_it_doesnt_need_its_color(self):
        t = self.table()
        t.me["zones"]["level"] = [game.new_card(t.card(801, color="Blue"))]
        t.refresh()
        self.assertEqual(t.state["needs_color"]["2"], {self.card["uid"]: "Red"})
        self.heroes(t)
        t.me["zones"]["level"] = []
        t.refresh()
        self.assertEqual(t.state["needs_color"]["2"], {})

    def test_lowered_to_level_1_it_still_needs_its_color(self):
        t = Table()
        t.card(800, traits="Hero")
        t.card(2000, text=self.TEXT, level=2, color="Red")
        self.card = t.hand(2000)[0]
        t.level(1)
        self.heroes(t)
        t.refresh()
        self.assertEqual(t.state["needs_color"]["2"], {self.card["uid"]: "Red"})

    def test_it_never_goes_below_0(self):
        t = Table()
        t.card(2000, text="【CONT】 This card gets -2 level while in your hand.", level=1)
        self.assertEqual(game.play_level(t.state, "2", game.new_card(2000), t.info), 0)

    def test_a_cost_reduction_is_what_gets_paid(self):
        t = Table()
        t.card(2000, text="【CONT】 This card gets -1 cost while in your hand.", cost=2)
        self.card = t.hand(2000)[0]
        t.stock(2)
        self.play(t)
        self.assertEqual(len(t.me["zones"]["stock"]), 1)

    def test_a_cost_reduction_lets_you_afford_it(self):
        t = Table()
        t.card(2000, text="【CONT】 This card gets -1 cost while in your hand.", cost=1)
        self.card = t.hand(2000)[0]
        self.play(t)
        self.assertEqual(t.me["zones"]["stock"], [])
        self.assertIsNotNone(t.me["stage"]["C1"])

    def test_another_character_can_lower_a_named_card(self):
        t = Table()
        t.card(2000, name="Named", cost=2)
        t.card(801, text='【CONT】 "Named" gets -1 cost while in your hand.')
        card = t.hand(2000)[0]
        self.assertEqual(game.play_cost(t.state, "2", card, t.info), 2)
        t.seat(t.me, "B1", 801)
        self.assertEqual(game.play_cost(t.state, "2", card, t.info), 1)

    def test_once_on_the_stage_it_is_its_printed_level_again(self):
        t = self.table()
        self.heroes(t)
        self.play(t)
        t.refresh()
        self.assertNotIn(self.card["uid"], t.state["hand_mods"]["2"])
        self.assertEqual(game.details_of(t.me["stage"]["C1"], game.SimpleNamespace(info=t.info))["level"], 1)

    def test_the_board_shows_it_only_to_its_owner(self):
        t = self.table()
        self.heroes(t)
        t.refresh()
        self.assertEqual(game.view(t.state, 2)["hand_mods"], {self.card["uid"]: {"level": 0, "cost": 0}})
        self.assertEqual(game.view(t.state, 1)["hand_mods"], {})

    def test_the_cpu_plays_it_early_when_it_can(self):
        t = self.table()
        self.assertNotEqual((t.next() or {}).get("uid"), self.card["uid"])
        self.heroes(t)
        action = t.next()
        self.assertEqual(action["uid"], self.card["uid"])
        self.assertIn(action["to"], game.OPPOSITE)

    def test_the_cpu_counts_the_lower_cost(self):
        t = Table()
        t.card(2000, text="【CONT】 This card gets -1 cost while in your hand.", cost=1, power=9000)
        card = t.hand(2000)[0]
        self.assertEqual(t.next()["uid"], card["uid"])

    def test_the_cpu_keeps_a_card_it_can_lower_over_one_it_cant_play(self):
        t = self.table()
        self.heroes(t)
        t.card(802, level=3, power=9000)
        mind = cpu.Mind(t.state, "2", t.info, cpu.Temper(), random.Random(1))
        self.assertGreater(mind.value(self.card), mind.value(game.new_card(802)))


class SecondExportTests(TestCase):
    """Wording from the newer export of unplayable cards, and what the game does with it."""

    def play(self, text, stock=0, **details):
        t = Table()
        t.card(2000, text=text, **details)
        card = t.hand(2000)[0]
        t.stock(stock)
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        return t, card

    def fire(self, t):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})

    def show_done(self, t):
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})

    def test_number_words_reach_every_wording_rule(self):
        self.assertEqual(abilities.parse("【ACT】 [Return two characters in your waiting room to your deck. Shuffle your deck] Draw 1 card.")[0]["cost"][0]["n"], 2)
        self.assertEqual(abilities.parse("【ACT】 [【REST】 two of your characters] Draw 1 card.")[0]["cost"][0]["n"], 2)

    def test_markup_left_in_card_text_is_ignored(self):
        self.assertEqual(abilities.by_hand_parts("【AUTO】 Encore [Put 1 card from your hand into your waiting room] (When this card is put into your waiting room from the stage, you may pay the cost. If you do, return this card to its previous stage position as 【REST】' />)"), [])
        self.assertEqual(abilities.parse("【ACT】 [Put 1 climax with [[gate.gif]] in its trigger icon from your hand into your waiting room] Draw 1 card.")[0]["cost"][0]["filter"]["any"][0]["icon"], "gate")

    def test_during_the_turn_placed_when_it_attacks(self):
        ability = abilities.parse("【AUTO】 During the turn that this card is placed on the stage from your hand, when this card attacks, this card gets +1000 power until end of turn.")[0]
        self.assertEqual(ability["when"], [{"on": "attack"}])
        self.assertEqual(ability["cond"][0]["type"], "played_this_turn")

    def test_limits_written_in_words(self):
        for text, limit in (("up to one time", 1), ("up to two times", 2), ("up to once", 1)):
            ability = abilities.parse(f"【AUTO】 This ability activates {text} per turn. When your other character attacks, this card gets +500 power until end of turn.")[0]
            self.assertEqual((ability["once"], ability["limit"], abilities.by_hand_parts(ability["text"])), (True, limit, []), text)

    def test_a_climax_icon_effect_happens_when_the_climax_is_placed(self):
        ability = abilities.parse("[c-icon] All of your characters get +1000 power until end of turn.")[0]
        self.assertEqual((ability["kind"], ability["when"]), ("auto", [{"on": "climax_self"}]))
        self.assertEqual(ability["steps"][0]["power"], 1000)

    OR_ELSE = "【AUTO】 [(1)] When this card is placed on the stage from your hand, you may pay the cost. If you do, draw 1 card. If you do not, put this card into your waiting room."

    def test_if_you_do_not_when_you_decline(self):
        t, card = self.play(self.OR_ELSE, stock=1)
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": False})
        self.assertEqual(len(t.me["zones"]["stock"]), 1)
        self.assertIsNone(t.me["stage"]["C1"])
        self.assertEqual(t.me["zones"]["waiting"][-1]["uid"], card["uid"])

    def test_if_you_do_not_when_you_cant_pay(self):
        t, _ = self.play(self.OR_ELSE)
        self.fire(t)
        self.assertIsNone(t.me["stage"]["C1"])

    def test_if_you_do_not_doesnt_happen_when_you_do(self):
        t, _ = self.play(self.OR_ELSE, stock=1)
        hand = len(t.me["zones"]["hand"])
        self.fire(t)
        self.assertIsNotNone(t.me["stage"]["C1"])
        self.assertEqual(len(t.me["zones"]["hand"]), hand + 1)

    def test_if_you_paid_the_cost_needs_you_to_have_paid(self):
        text = "【AUTO】 [(1)] When this card is placed on the stage from your hand, you may pay the cost. If you paid the cost, draw 1 card."
        t, _ = self.play(text, stock=1)
        hand = len(t.me["zones"]["hand"])
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": False})
        self.assertEqual((len(t.me["zones"]["hand"]), len(t.me["zones"]["stock"])), (hand, 1))
        t, _ = self.play(text, stock=1)
        hand = len(t.me["zones"]["hand"])
        self.fire(t)
        self.assertEqual((len(t.me["zones"]["hand"]), len(t.me["zones"]["stock"])), (hand + 1, 0))

    def test_your_opponent_may_is_their_choice_and_their_card(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, your opponent may draw 1 card.")
        t.me["zones"]["deck"], mine = t.me["zones"]["deck"], len(t.me["zones"]["hand"])
        theirs = len(t.them["zones"]["hand"])
        self.fire(t)
        self.assertEqual(t.state["resolving"]["prompt"]["player"], "1")
        t.apply(1, {"type": "ability_answer", "value": "yes"})
        self.assertEqual((len(t.them["zones"]["hand"]), len(t.me["zones"]["hand"])), (theirs + 1, mine))

    def test_the_cpu_answers_when_it_is_the_opponent_being_asked(self):
        t = Table()
        t.card(2000, text="【AUTO】 When this card is placed on the stage from your hand, your opponent may draw 1 card.")
        t.state["turn"] = "1"
        card = game.new_card(2000)
        t.them["zones"]["hand"].append(card)
        t.refresh()
        t.apply(1, {"type": "move", "uid": card["uid"], "to": "C1"})
        t.apply(1, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True})
        self.assertEqual(t.next(), {"type": "ability_answer", "value": "yes"})

    def test_the_opponent_chooses_for_you_from_among_them(self):
        text = ("【AUTO】 When this card is placed on the stage from your hand, look at the top 2 cards of your deck, your opponent chooses 1 event or character from among them, "
                "you put it into your hand, and put the rest into your waiting room.").replace("look at the top 2 cards", "look at 2 cards from the top")
        t, _ = self.play(text)
        self.fire(t)
        prompt = t.state["resolving"]["prompt"]
        self.assertEqual(prompt["player"], "1")
        wanted = prompt["options"][0]
        t.apply(1, {"type": "ability_answer", "uids": [wanted]})
        self.assertIn(wanted, [c["uid"] for c in t.me["zones"]["hand"]])
        self.assertEqual(len(t.me["zones"]["waiting"]), 1)

    def test_this_card_stays_rested_through_my_next_stand_phase_only(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, this card cannot 【STAND】 during your next stand phase.")
        self.fire(t)
        self.assertEqual(t.state["buffs"][-1]["expires"], t.state["turn_number"] + 2)

    def test_each_player_keeps_cards_in_memory(self):
        text = ('【AUTO】 When this card is placed on the stage from your hand, all players perform the following action. '
                '"If your memory has 2 or more cards, choose 1 cards in your memory, and put all cards in your memory except those cards into your waiting room."')
        t, _ = self.play(text)
        t.me["zones"]["memory"] = [game.new_card(1), game.new_card(2)]
        t.them["zones"]["memory"] = [game.new_card(3), game.new_card(4), game.new_card(5)]
        self.fire(t)
        keep = t.state["resolving"]["prompt"]["options"][0]
        t.apply(2, {"type": "ability_answer", "uids": [keep]})
        self.assertEqual([c["uid"] for c in t.me["zones"]["memory"]], [keep])
        prompt = t.state["resolving"]["prompt"]
        self.assertEqual(prompt["player"], "1")
        theirs = prompt["options"][0]
        t.apply(1, {"type": "ability_answer", "uids": [theirs]})
        self.assertEqual([c["uid"] for c in t.them["zones"]["memory"]], [theirs])
        self.assertEqual(len(t.them["zones"]["waiting"]), 2)

    def test_search_for_the_same_name_as_a_climax_in_the_waiting_room(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, search your deck for up to 1 climax with the same card name as a climax in your waiting room, reveal it to your opponent, put it into your hand, and shuffle your deck.")
        t.card(910, name="Match", card_type="Climax", level=None, cost=None, power=None)
        t.card(911, name="Other", card_type="Climax", level=None, cost=None, power=None)
        t.me["zones"]["waiting"].append(game.new_card(910))
        match, other = game.new_card(910), game.new_card(911)
        t.me["zones"]["deck"] += [match, other]
        self.fire(t)
        self.assertEqual(t.state["resolving"]["prompt"]["options"], [match["uid"]])

    def test_the_bottom_of_the_clock_exchanged_with_a_chosen_card(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, you may choose the bottom card of your clock and 1 character in your waiting room, and exchange them.")
        bottom, top, chosen = game.new_card(1), game.new_card(2), game.new_card(3)
        t.me["zones"]["clock"] = [bottom, top]
        t.me["zones"]["waiting"] = [chosen]
        self.fire(t)
        t.apply(2, {"type": "ability_answer", "uids": [chosen["uid"]]})
        self.assertEqual([c["uid"] for c in t.me["zones"]["clock"]].count(chosen["uid"]), 1)
        self.assertIn(bottom["uid"], [c["uid"] for c in t.me["zones"]["waiting"]])
        self.assertIn(top["uid"], [c["uid"] for c in t.me["zones"]["clock"]])

    def test_markers_move_where_the_card_says(self):
        t, card = self.play("【AUTO】 When this card is placed on the stage from your hand, put 1 marker underneath this card into your stock.")
        marker = game.new_card(5)
        t.me["markers"]["C1"] = [marker]
        self.fire(t)
        if t.state.get("resolving"):
            t.apply(2, {"type": "ability_answer", "uids": [marker["uid"]]})
        self.assertIn(marker["uid"], [c["uid"] for c in t.me["zones"]["stock"]])
        self.assertEqual(t.me["markers"]["C1"], [])

    def test_all_opposing_characters_lose_power(self):
        t, _ = self.play("【AUTO】 When this card is placed on the stage from your hand, all of your opponent's characters get -500 power until end of turn.")
        enemy = t.seat(t.them, "C2", t.card(700, power=3000))
        self.fire(t)
        self.show_done(t)
        t.refresh()
        self.assertEqual(t.state["stats"][enemy["uid"]]["power"], 2500)

    def test_reversing_the_battle_opponent(self):
        steps = abilities.parse("【AUTO】 When this card attacks, 【REVERSE】 this card's battle opponent.")[0]["steps"]
        self.assertEqual([s["do"] for s in steps], ["choose_facing", "pos_it"])

    def test_conditions_comparing_with_the_opponent(self):
        t = Table()
        cond = abilities.parse_condition("if your stock has less cards than your opponent's stock", [])
        env = game.SimpleNamespace(info=t.info)
        self.assertFalse(game.condition_met(cond, t.state, "2", None, {}, env))
        t.them["zones"]["stock"].append(game.new_card(1))
        self.assertTrue(game.condition_met(cond, t.state, "2", None, {}, env))

    def test_counting_colors(self):
        t = Table()
        t.seat(t.me, "C1", t.card(701, color="Red"))
        t.seat(t.me, "C2", t.card(702, color="Blue"))
        cond = abilities.parse_condition("if the number of colors of your characters on the stage is 2 or more", [])
        env = game.SimpleNamespace(info=t.info)
        self.assertTrue(game.condition_met(cond, t.state, "2", None, {}, env))
        self.assertFalse(game.condition_met({**cond, "n": 3}, t.state, "2", None, {}, env))


class FocusedModelTests(TestCase):
    def table(self):
        t = Table()
        t.card(800, name="Big Finish", card_type="Climax", level=None, cost=None, power=None)
        t.card(801, level=3, cost=2, power=9000, color="Red", text='【AUTO】 【CXCOMBO】 When this card attacks, if "Big Finish" is in your climax zone, draw 1 card.')
        t.card(802, level=1, cost=1, power=9000)
        t.level(2)
        t.me["zones"]["deck"] = [game.new_card(801), game.new_card(800), *[game.new_card(1) for _ in range(20)]]
        return t

    def next(self, t, model="focused"):
        t.refresh()
        return cpu.next_action(t.state, "2", t.info, 1, random.Random(1), model=model)

    def fill_front(self, t):
        t.seat(t.me, "C1", t.card(1001, power=1000))
        t.seat(t.me, "C2", t.card(1002, power=1000))

    def test_at_level_2_it_saves_stock_for_its_level_3_combo(self):
        t = self.table()
        self.fill_front(t)
        t.stock(2)
        t.hand(802)
        self.assertEqual(self.next(t), {"type": "phase", "phase": "climax"})
        self.assertEqual(self.next(t, "standard")["type"], "move")

    def test_it_spends_what_it_can_spare(self):
        t = self.table()
        self.fill_front(t)
        t.stock(3)
        cards = t.hand(802)
        self.assertEqual(self.next(t)["uid"], cards[0]["uid"])

    def test_it_doesnt_save_with_too_few_characters_out(self):
        t = self.table()
        t.stock(2)
        cards = t.hand(802)
        self.assertEqual(self.next(t)["uid"], cards[0]["uid"])

    def test_it_doesnt_think_ahead_too_far(self):
        t = self.table()
        t.me["zones"]["level"] = t.me["zones"]["level"][:1]
        self.fill_front(t)
        t.stock(1)
        cards = t.hand(802)
        self.assertEqual(self.next(t)["uid"], cards[0]["uid"])

    def test_it_holds_the_climax_for_the_combo(self):
        t = self.table()
        t.state["phase"] = "climax"
        t.hand(800)
        self.assertEqual(self.next(t), {"type": "phase", "phase": "attack"})
        self.assertEqual(self.next(t, "standard")["to"], "climax")

    def test_it_plays_a_climax_that_isnt_for_the_combo(self):
        t = self.table()
        t.state["phase"] = "climax"
        t.card(803, card_type="Climax", level=None, cost=None, power=None)
        cards = t.hand(800, 803)
        self.assertEqual(self.next(t)["uid"], cards[1]["uid"])

    def test_it_plays_the_climax_once_the_combo_is_out(self):
        t = self.table()
        t.state["phase"] = "climax"
        t.seat(t.me, "C2", 801)
        cards = t.hand(800)
        self.assertEqual(self.next(t)["uid"], cards[0]["uid"])

    def test_it_clocks_something_other_than_the_combo(self):
        t = self.table()
        t.state["phase"] = "clock"
        t.card(804, level=0, power=9000)
        cards = t.hand(801, 800, 804)
        self.assertEqual(self.next(t)["uid"], cards[2]["uid"])

    def test_it_takes_the_combo_from_a_choice(self):
        t = self.table()
        mind = cpu.Focused(t.state, "2", t.info, cpu.Temper(), random.Random(1))
        combo, other = game.new_card(801), game.new_card(802)
        self.assertEqual(mind.pick_cards({"cards": [other, combo], "options": [other["uid"], combo["uid"]], "max": 1, "min": 1, "zone": "waiting"}), [combo["uid"]])

    def test_it_levels_up_with_the_color_it_needs_and_keeps_the_combo(self):
        t = self.table()
        t.card(805, color="Red", level=0)
        t.card(806, color="Blue", level=2)
        t.me["zones"]["clock"] = [game.new_card(806), game.new_card(805), game.new_card(801), *[game.new_card(806) for _ in range(4)]]
        action = self.next(t)
        self.assertEqual(action["type"], "level_up")
        self.assertEqual(action["uid"], t.me["zones"]["clock"][1]["uid"])

    def test_a_combo_in_the_back_row_moves_up_when_its_climax_is_ready(self):
        t = self.table()
        t.hand(800)
        card = t.seat(t.me, "B1", 801)
        action = self.next(t)
        self.assertEqual(action["uid"], card["uid"])
        self.assertIn(action["to"], game.OPPOSITE)

    def test_it_declines_an_optional_cost_it_is_saving_for(self):
        t = self.table()
        mind = cpu.Focused(t.state, "2", t.info, cpu.Temper(), random.Random(1))
        t.stock(2)
        prompt = {"kind": "choice", "for": "may", "step": {"cost": [{"part": "stock", "n": 1}]}, "options": [{"value": "yes"}, {"value": "no"}]}
        self.assertEqual(mind.answer({"prompt": prompt})["value"], "no")

    def test_with_no_combo_in_the_deck_it_plays_like_standard(self):
        t = Table()
        t.card(802, level=0, cost=1, power=9000)
        t.stock(1)
        t.hand(802)
        t.refresh()
        self.assertEqual(self.next(t)["type"], self.next(t, "standard")["type"])


class StrategicModelTests(TestCase):
    BRAINSTORM = "【ACT】 Brainstorm [(1) 【REST】 this card] Flip over 4 cards from the top of your deck, and put them into your waiting room. For each climax revealed among those cards, draw 1 card."
    SALVAGE = "【ACT】 [(1) 【REST】 this card] Choose 1 character in your waiting room, and return it to your hand."

    def next(self, t, model="strategic"):
        t.refresh()
        return cpu.next_action(t.state, "2", t.info, 1, random.Random(1), model=model)

    def test_it_fills_the_waiting_room_before_taking_from_it(self):
        t = Table()
        salvage = t.seat(t.me, "B1", t.card(1001, text=self.SALVAGE))
        brainstorm = t.seat(t.me, "B2", t.card(1002, text=self.BRAINSTORM))
        t.me["zones"]["waiting"] = [game.new_card(1)]
        t.stock(2)
        self.assertEqual(self.next(t)["uid"], brainstorm["uid"])
        t.apply(2, self.next(t))
        while t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})
        self.assertEqual(self.next(t)["uid"], salvage["uid"])

    def test_it_acts_before_building_its_board(self):
        t = Table()
        t.card(1003, power=9000)
        t.hand(1003)
        brainstorm = t.seat(t.me, "B1", t.card(1002, text=self.BRAINSTORM))
        t.stock(1)
        self.assertEqual(self.next(t)["uid"], brainstorm["uid"])

    def test_it_sets_out_a_character_to_use_its_ability(self):
        t = Table()
        t.card(1003, power=9000)
        strong, brainstorm = t.hand(1003, t.card(1002, power=500, text=self.BRAINSTORM))
        t.stock(1)
        self.assertEqual(self.next(t), {"type": "move", "uid": brainstorm["uid"], "to": "B1"})
        self.assertEqual(self.next(t, "standard")["uid"], strong["uid"])

    def test_a_card_that_mills_when_played_counts(self):
        t = Table()
        salvage = t.seat(t.me, "B1", t.card(1001, text=self.SALVAGE))
        mill = t.hand(t.card(1004, text="【AUTO】 When this card is placed on the stage from your hand, put the top 2 cards of your deck into your waiting room."))[0]
        t.stock(1)
        action = self.next(t)
        self.assertEqual(action["uid"], mill["uid"])
        self.assertNotEqual(action["uid"], salvage["uid"])

    def test_milling_alone_isnt_worth_doing(self):
        t = Table()
        t.card(1005, text="【ACT】 [【REST】 this card] Put the top 2 cards of your deck into your waiting room.")
        t.seat(t.me, "B1", 1005)
        self.assertNotEqual(self.next(t)["type"], "activate")

    def test_it_wont_mill_a_small_deck(self):
        t = Table()
        t.seat(t.me, "B1", t.card(1001, text=self.SALVAGE))
        t.seat(t.me, "B2", t.card(1002, text=self.BRAINSTORM))
        t.me["zones"]["deck"] = t.me["zones"]["deck"][:cpu.FILL_MIN_DECK - 1]
        t.me["zones"]["waiting"] = [game.new_card(1)]
        t.stock(2)
        self.assertEqual(self.next(t)["uid"], t.me["stage"]["B1"]["uid"])

    def test_salvage_with_an_empty_waiting_room_waits(self):
        t = Table()
        t.seat(t.me, "B1", t.card(1001, text=self.SALVAGE))
        t.stock(1)
        self.assertNotEqual(self.next(t)["type"], "activate")


class ModelChoiceTests(TestCase):
    def test_every_model_has_a_mind(self):
        self.assertEqual(set(cpu.MODELS), set(cpu.MINDS))

    def test_an_unknown_model_plays_as_standard(self):
        t = Table()
        t.refresh()
        self.assertEqual(cpu.next_action(t.state, "2", t.info, model="gone"), {"type": "phase", "phase": "climax"})


class EndOfTurnTimingTests(TestCase):
    TRIGGER = "【AUTO】 At the end of your turn, this card gets +1000 power until end of turn."

    def table(self, text=TRIGGER):
        t = Table()
        t.card(2000, text=text)
        self.me = t.seat(t.me, "C1", 2000)
        t.state["phase"] = "main"
        t.refresh()
        return t

    def fire(self, t, accept=True):
        t.apply(2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": accept})

    def show_done(self, t):
        if t.state.get("ability_show"):
            t.apply(2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]})

    def test_the_turn_waits_in_the_end_phase_until_its_resolved(self):
        t = self.table()
        t.apply(2, {"type": "phase", "phase": "end"})
        self.assertEqual((t.state["phase"], t.state["turn"], t.state["turn_number"]), ("end", "2", 3))
        self.fire(t)
        self.assertEqual((t.state["phase"], t.state["turn"]), ("end", "2"))  # still showing it
        self.show_done(t)
        self.assertEqual((t.state["phase"], t.state["turn"], t.state["turn_number"]), ("stand", "1", 4))

    def test_nothing_moves_on_meanwhile(self):
        t = self.table()
        t.apply(2, {"type": "phase", "phase": "end"})
        with self.assertRaises(game.GameError):
            t.apply(1, {"type": "end_turn"})
        t.apply(2, {"type": "phase", "phase": "end", "auto": True})  # a page's timer does nothing
        self.assertEqual(t.state["turn"], "2")

    def test_skipping_it_also_lets_the_turn_end(self):
        t = self.table()
        t.apply(2, {"type": "phase", "phase": "end"})
        self.fire(t, accept=False)
        self.assertEqual(t.state["turn"], "1")

    def test_no_effects_means_no_wait(self):
        t = self.table("")
        t.apply(2, {"type": "phase", "phase": "end"})
        self.assertEqual(t.state["turn"], "1")

    def test_until_end_of_turn_still_holds_while_it_resolves(self):
        t = self.table()
        t.state["buffs"] = [{"uid": self.me["uid"], "power": 500, "soul": 0, "expires": 3}]
        t.apply(2, {"type": "phase", "phase": "end"})
        t.refresh()
        self.assertEqual(t.state["stats"][self.me["uid"]]["power"], 1500)
        self.fire(t)
        self.show_done(t)
        t.refresh()
        self.assertEqual(t.state["stats"][self.me["uid"]]["power"], 1000)

    def test_the_climax_is_still_there_while_it_resolves(self):
        t = self.table()
        t.me["zones"]["climax"].append(game.new_card(t.card(900, card_type="Climax", power=None, level=None)))
        t.apply(2, {"type": "phase", "phase": "end"})
        self.assertEqual(len(t.me["zones"]["climax"]), 1)
        self.fire(t)
        self.show_done(t)
        self.assertEqual(t.me["zones"]["climax"], [])

    def test_a_delayed_effect_waits_the_same_way(self):
        t = self.table("【AUTO】 When this card attacks, this card gets +1000 power until end of turn. At the end of the turn, put this card into your waiting room.")
        t.state.update(phase="attack", attack={"step": "declare"})
        t.apply(2, {"type": "attack", "uid": self.me["uid"], "kind": "direct"})
        self.fire(t)
        self.show_done(t)
        t.apply(2, {"type": "phase", "phase": "end"})
        self.assertEqual(t.state["turn"], "2")
        self.assertEqual(t.me["stage"]["C1"]["uid"], self.me["uid"])
        self.fire(t)
        self.assertIsNone(t.me["stage"]["C1"])
        self.show_done(t)
        self.assertEqual(t.state["turn"], "1")

    def test_a_choice_in_the_effect_is_waited_for(self):
        t = self.table("【AUTO】 At the end of your turn, choose 1 of your characters, and that character gets +1000 power until end of turn.")
        t.apply(2, {"type": "phase", "phase": "end"})
        self.fire(t)
        self.assertEqual(t.state["turn"], "2")
        t.apply(2, {"type": "ability_answer", "uids": [self.me["uid"]]})
        self.show_done(t)
        self.assertEqual(t.state["turn"], "1")

    def test_the_hand_limit_comes_after_so_a_draw_counts(self):
        t = self.table("【AUTO】 At the end of your turn, draw 1 card.")
        t.hand(*[1] * 7)
        t.apply(2, {"type": "phase", "phase": "end"})
        self.assertNotIn("pending_discard", t.state)
        self.fire(t)
        self.show_done(t)
        self.assertEqual(t.state["pending_discard"]["count"], 1)
        self.assertEqual(t.state["turn"], "2")
        t.apply(2, {"type": "discard", "uids": [t.me["zones"]["hand"][0]["uid"]]})
        self.assertEqual(t.state["turn"], "1")

    def test_damage_from_it_finishes_before_the_turn_ends(self):
        t = self.table("【AUTO】 At the end of your turn, deal 1 damage to your opponent.")
        t.them["zones"]["deck"][-1]["card"] = t.card(901, card_type="Climax", power=None, level=None)
        t.apply(2, {"type": "phase", "phase": "end"})
        kwargs = dict(shuffle=no_shuffle, info=t.info, name=lambda pk: t.info(pk)["name"], cost=lambda pk: 0, trigger=lambda pk: "",
                      is_climax=lambda pk: t.info(pk)["card_type"] == "Climax")
        game.apply(t.state, 2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True}, **kwargs)
        self.assertEqual(t.state["turn"], "2")  # the cancelled damage is still showing
        game.apply(t.state, 1, {"type": "resolve_damage"}, **kwargs)
        self.show_done(t)
        self.assertEqual(t.state["turn"], "1")

    def test_the_cpu_plays_through_it(self):
        t = self.table()
        t.state["phase"] = "encore"
        t.refresh()
        for _ in range(8):
            if t.state["turn"] == "1":
                break
            action = t.next() or {"type": "phase", "phase": "end"}
            t.apply(2, action)
        self.assertEqual(t.state["turn"], "1")

    def test_with_the_rules_off_nothing_waits(self):
        t = self.table()
        t.state["rules"] = False
        t.apply(2, {"type": "phase", "phase": "end"})
        self.assertEqual(t.state["turn"], "1")


class RevealShowTests(TestCase):
    TEXT = "【AUTO】 When this card is placed on the stage from your hand, reveal the top card of your deck. If that card is a 《Hero》 character, put it into your hand."

    def start(self, text=TEXT):
        t = Table()
        t.card(900, traits="Hero")
        self.top = t.me["zones"]["deck"][-1]
        self.top["card"] = 900
        t.card(2000, text=text)
        card = t.hand(2000)[0]
        t.refresh()
        t.apply(2, {"type": "move", "uid": card["uid"], "to": "C1"})
        kwargs = dict(shuffle=no_shuffle, info=t.info, name=lambda pk: t.info(pk)["name"], is_climax=lambda pk: False, trigger=lambda pk: "", cost=lambda pk: 0)
        game.apply(t.state, 2, {"type": "ability_trigger", "id": t.state["ability_queue"][0]["id"], "accept": True}, **kwargs)
        self.kwargs = kwargs
        return t

    def test_it_shows_before_anything_happens_to_the_card(self):
        t = self.start()
        for player in (1, 2):
            view = game.view(t.state, player)
            self.assertEqual((view["ability_show"]["label"], view["ability_show"]["check"]), ("Revealed", [900]))
            self.assertIn(900, game.visible_cards(view))
        self.assertEqual(t.me["zones"]["deck"][-1]["uid"], self.top["uid"])  # not moved yet
        game.apply(t.state, 2, {"type": "ability_show_done", "id": t.state["ability_show"]["id"]}, **self.kwargs)
        self.assertIn(self.top["uid"], [c["uid"] for c in t.me["zones"]["hand"]])

    def test_a_search_shows_what_it_found(self):
        t = self.start("【AUTO】 When this card is placed on the stage from your hand, search your deck for up to 1 《Hero》 character, reveal it to your opponent, put it into your hand, and shuffle your deck.")
        game.apply(t.state, 2, {"type": "ability_answer", "uids": [self.top["uid"]]}, **self.kwargs)
        self.assertEqual(t.state["ability_show"]["check"], [900])

    def test_nothing_is_shown_if_nothing_was_taken(self):
        t = self.start("【AUTO】 When this card is placed on the stage from your hand, search your deck for up to 1 《Hero》 character, reveal it to your opponent, put it into your hand, and shuffle your deck.")
        game.apply(t.state, 2, {"type": "ability_answer", "uids": []}, **self.kwargs)
        self.assertFalse((t.state.get("ability_show") or {}).get("label"))

    def test_the_cpu_carries_on_after_it(self):
        t = self.start()
        self.assertEqual(t.next()["type"], "ability_show_done")


class CpuDeckBuildingTests(TestCase):
    JUGGLE = "【AUTO】 When this card attacks, juggle the dice."
    COMBO = '【AUTO】 【CXCOMBO】 When "BIG" is placed on your climax area, draw 1 card.'

    def setUp(self):
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.client.force_login(self.staff)
        common = {"expansion": "E", "expansion_id": 1, "traits": "Hero", "soul": 1, "power": 3000}
        n = 0

        def add(**fields):
            nonlocal n
            n += 1
            fields.setdefault("name", f"Card {n}")
            return Card.objects.create(serial_number=f"TST/{n}", **{**common, **fields})

        for level in range(4):
            for color in ("Red", "Blue"):
                for i in range(8):
                    add(card_type="Character", level=level, color=color, description="【AUTO】 When this card attacks, choose 1 character in your waiting room, and return it to your hand." if i % 2 else "")
        for i in range(3):
            add(card_type="Climax", color="Red", description="")
        self.big = add(card_type="Climax", color="Red", name="BIG", description="")
        self.bad = [add(card_type="Character", level=0, color="Red", name=f"Bad {i}", power=9000, description=self.JUGGLE) for i in range(8)]
        self.clean_anchor = add(card_type="Character", level=1, color="Red", name="Clean Anchor", description=self.COMBO)
        self.other_anchor = add(card_type="Character", level=2, color="Red", name="Other Anchor", description=self.COMBO)
        self.bad_anchor = add(card_type="Character", level=1, color="Red", name="Bad Anchor", description=self.COMBO + "\n" + self.JUGGLE)
        self.naming_anchor = add(card_type="Character", level=1, color="Red", name="Naming Anchor", description=self.COMBO + ' Choose 1 "Bad 0" in your waiting room.')
        self.deck = CardList.objects.create(user=self.staff, name="Bot", reserved_for_cpu=True)
        self.start = reverse("weiss:list_express", args=[self.deck.pk])

    def test_the_pool_leaves_them_out(self):
        names = {c.name for c in express.series_pool("TST", for_cpu=True)}
        self.assertFalse(names & {c.name for c in self.bad})
        self.assertIn("Bad 0", {c.name for c in express.series_pool("TST")})

    def test_anchors_that_need_them_arent_offered(self):
        names = {c.name for c in express.cpu_anchor_choices("TST")}
        self.assertEqual(names, {"Clean Anchor", "Other Anchor"})
        page = self.client.get(self.start, {"series": "TST"})
        self.assertContains(page, "Clean Anchor")
        self.assertNotContains(page, "Bad Anchor")
        self.assertNotContains(page, "Naming Anchor")
        self.client.post(self.start, {"series": "TST", "anchor": [self.clean_anchor.pk, self.bad_anchor.pk]})
        self.assertEqual(self.deck.entries.count(), 0)

    def test_a_built_cpu_deck_has_none_and_a_players_can(self):
        self.client.post(self.start, {"series": "TST", "anchor": [self.clean_anchor.pk, self.other_anchor.pk]})
        cards = [e.card for e in self.deck.entries.select_related("card")]
        self.assertEqual(self.deck.card_count(), 50)
        self.assertEqual([c.name for c in cards if abilities.by_hand_parts(c.description)], [])
        self.assertIn("Bad Anchor", {c.name for c in express.anchor_choices(express.series_pool("TST"))})

    def test_replacements_for_a_cpu_deck_have_none(self):
        self.client.post(self.start, {"series": "TST", "anchor": [self.clean_anchor.pk, self.other_anchor.pk]})
        self.deck.refresh_from_db()
        replacing = [e.card_id for e in self.deck.entries.select_related("card") if e.card.name not in self.deck.express["required"] for _ in range(e.quantity)]
        self.client.post(reverse("weiss:list_express_replace", args=[self.deck.pk]), {"replace": replacing})
        self.assertEqual(self.deck.card_count(), 50)
        self.assertEqual([e.card.name for e in self.deck.entries.select_related("card") if abilities.by_hand_parts(e.card.description)], [])

    def test_an_older_deck_can_replace_its_way_out(self):
        self.client.post(self.start, {"series": "TST", "anchor": [self.clean_anchor.pk, self.other_anchor.pk]})
        self.deck.refresh_from_db()
        swap = self.deck.entries.select_related("card").filter(card__level=0).first()
        quantity = swap.quantity
        swap.card = self.bad[0]
        swap.save()
        self.client.post(reverse("weiss:list_express_replace", args=[self.deck.pk]), {"replace": [self.bad[0].pk] * quantity})
        self.assertFalse(self.deck.entries.filter(card=self.bad[0]).exists())
        self.assertEqual(self.deck.card_count(), 50)

    def test_they_cant_be_added_by_hand(self):
        url = reverse("weiss:list_change", args=[self.deck.pk])
        response = self.client.post(url, {"card": self.bad[0].pk, "delta": 1}, follow=True)
        self.assertContains(response, "done by hand")
        self.assertEqual(self.deck.entries.count(), 0)
        self.client.post(url, {"card": self.clean_anchor.pk, "delta": 1})
        self.assertEqual(self.deck.entries.count(), 1)

    def test_a_built_cpu_deck_opens_on_the_regular_deck_page(self):
        response = self.client.post(self.start, {"series": "TST", "anchor": [self.clean_anchor.pk, self.other_anchor.pk]})
        self.assertRedirects(response, reverse("weiss:list", args=[self.deck.pk]))
        page = self.client.get(reverse("weiss:list", args=[self.deck.pk]))
        self.assertContains(page, "Add cards to this list")
        self.assertContains(page, reverse("weiss:list_rename", args=[self.deck.pk]))
        self.assertContains(page, "Adding cards to")  # the side panel has it open for editing
        self.assertContains(page, reverse("weiss:list_express_review", args=[self.deck.pk]))  # the replace tool is still a click away

    def test_a_players_built_deck_still_goes_to_the_review(self):
        mine = CardList.objects.create(user=self.staff, name="Mine")
        response = self.client.post(reverse("weiss:list_express", args=[mine.pk]), {"series": "TST", "anchor": [self.clean_anchor.pk, self.other_anchor.pk]})
        self.assertRedirects(response, reverse("weiss:list_express_review", args=[mine.pk]))

    def test_a_players_deck_can_still_have_them(self):
        mine = CardList.objects.create(user=self.staff, name="Mine")
        self.client.post(reverse("weiss:list_change", args=[mine.pk]), {"card": self.bad[0].pk, "delta": 1})
        self.assertEqual(mine.entries.count(), 1)

    def test_a_deck_with_one_cant_be_finalized(self):
        from .cpu_views import deck_problem
        CardListEntry.objects.create(card_list=self.deck, card=self.bad[0], quantity=1)
        self.assertIn("Bad 0", deck_problem(self.deck))

    def test_exporting_them_as_a_file(self):
        response = self.client.get(reverse("weiss:cpu_excluded_export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("text/plain", response["Content-Type"])
        text = response.content.decode()
        self.assertIn("9 cards a CPU can't play", text)
        self.assertIn("Bad Anchor (TST/", text)
        self.assertIn(self.COMBO, text)  # the card's full text
        self.assertIn("  - juggle the dice", text)
        self.assertNotIn("Clean Anchor", text)
        self.assertContains(self.client.get(reverse("weiss:cpu_home")), reverse("weiss:cpu_excluded_export"))

    def test_only_staff_can_export(self):
        player = User.objects.create_user("player", password="x")
        player.groups.add(Group.objects.get_or_create(name=WEISS_GROUP)[0])
        self.client.force_login(player)
        self.assertEqual(self.client.get(reverse("weiss:cpu_excluded_export")).status_code, 403)

    def test_the_tab_lists_them(self):
        page = self.client.get(reverse("weiss:cpu_excluded"))
        self.assertEqual([c["name"] for c in page.context["excluded"]], ["Bad 0", "Bad 1", "Bad 2", "Bad 3", "Bad 4", "Bad 5", "Bad 6", "Bad 7", "Bad Anchor"])
        self.assertContains(page, "juggle the dice")

    def test_the_tab_itself_doesnt_read_any_card_text(self):
        with mock.patch.object(cpu_views, "excluded_cards") as excluded:
            page = self.client.get(reverse("weiss:cpu_home"))
        excluded.assert_not_called()
        self.assertContains(page, reverse("weiss:cpu_excluded"))
        self.assertNotContains(page, "juggle the dice")

    def test_the_list_is_only_worked_out_again_when_the_cards_change(self):
        with mock.patch.object(abilities, "by_hand_parts", wraps=abilities.by_hand_parts) as reader:
            first = cpu_views.excluded_cards()
            reader.reset_mock()
            self.assertEqual(cpu_views.excluded_cards(), first)
            reader.assert_not_called()
        Card.objects.create(serial_number="NEW/1", name="Brand New", expansion="E", expansion_id=9, card_type="Character", level=0, description="【AUTO】 When this card attacks, juggle the dice.")
        self.assertIn("Brand New", [c["name"] for c in cpu_views.excluded_cards()])
        card = Card.objects.get(serial_number="NEW/1")
        card.description = "【AUTO】 When this card attacks, draw 1 card."
        card.save()
        self.assertNotIn("Brand New", [c["name"] for c in cpu_views.excluded_cards()])

    def test_only_staff_can_see_the_list(self):
        player = User.objects.create_user("player2", password="x")
        Group.objects.get_or_create(name=WEISS_GROUP)[0].user_set.add(player)
        self.client.force_login(player)
        self.assertEqual(self.client.get(reverse("weiss:cpu_excluded")).status_code, 403)

    def test_a_series_with_nothing_left_isnt_offered_for_a_cpu(self):
        Card.objects.create(serial_number="ONLY/1", name="Only", expansion="O", expansion_id=2, card_type="Character", level=0, description=self.COMBO + "\n" + self.JUGGLE)
        codes = {c["code"] for c in express.series_choices(for_cpu=True)}
        self.assertNotIn("ONLY", codes)
        self.assertIn("ONLY", {c["code"] for c in express.series_choices()})

    def test_the_menu_can_be_searched_by_name_and_code(self):
        page = self.client.get(reverse("weiss:list_express", args=[self.deck.pk]))
        self.assertContains(page, "data-series-search")
        self.assertContains(page, 'data-series-text="')
        self.assertRegex(page.content.decode(), r'data-series-text="[^"]* TST"')

    def test_the_menu_counts_what_the_next_step_offers(self):
        counts = express.cpu_anchor_counts()
        self.assertEqual(counts["TST"], len(express.cpu_anchor_choices("TST")))

    def test_the_menu_only_reads_anchors_and_what_they_name(self):
        express.cpu_counts_memo = (None, None)
        with mock.patch.object(abilities, "by_hand_parts", wraps=abilities.by_hand_parts) as reader:
            express.cpu_anchor_counts()
        anchors = Card.objects.filter(description__contains=express.CX_COMBO).exclude(card_type__iexact="climax").count()
        self.assertLess(reader.call_count, Card.objects.count())
        self.assertGreaterEqual(reader.call_count, 1 if anchors else 0)

    def test_the_menu_is_only_worked_out_again_when_the_cards_change(self):
        first = express.cpu_anchor_counts()
        with mock.patch.object(abilities, "by_hand_parts", wraps=abilities.by_hand_parts) as reader:
            self.assertEqual(express.cpu_anchor_counts(), first)
            reader.assert_not_called()
        card = Card.objects.get(name="Clean Anchor")
        before = first["TST"]
        card.description += " Juggle the dice."
        card.save()
        self.assertEqual(express.cpu_anchor_counts()["TST"], before - 1)


class PagesTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.player = User.objects.create_user("player", password="x")
        self.player.groups.add(Group.objects.get_or_create(name=WEISS_GROUP)[0])
        self.climax = Card.objects.create(serial_number="T/1", name="CX", expansion="E", expansion_id=1, card_type="Climax")
        self.chars = [Card.objects.create(serial_number=f"T/{i}", name=f"Char {i}", expansion="E", expansion_id=1, card_type="Character", level=0, cost=0, power=1000, soul=1) for i in range(2, 13)]
        self.client.force_login(self.staff)

    def legal_deck(self, user=None, **fields):
        deck = CardList.objects.create(user=user or self.staff, name="Deck", **fields)
        CardListEntry.objects.create(card_list=deck, card=self.climax, quantity=4)
        CardListEntry.objects.create(card_list=deck, card=Card.objects.create(serial_number=f"T/C{deck.pk}", name=f"CX {deck.pk}", expansion="E", expansion_id=1, card_type="Climax"), quantity=4)
        for card in self.chars[:10]:
            CardListEntry.objects.create(card_list=deck, card=card, quantity=4)
        CardListEntry.objects.create(card_list=deck, card=self.chars[10], quantity=2)
        return deck

    def test_the_tab_is_staff_only(self):
        self.assertContains(self.client.get(reverse("weiss:sets")), "CPU creation")
        self.client.force_login(self.player)
        self.assertNotContains(self.client.get(reverse("weiss:sets")), "CPU creation")
        self.assertEqual(self.client.get(reverse("weiss:cpu_home")).status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:cpu_deck_create"), {"name": "x"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:cpu_profile_create"), {"name": "x"}).status_code, 403)

    def test_a_reserved_deck_is_built_the_usual_way_but_kept_out_of_lists(self):
        self.client.post(reverse("weiss:cpu_deck_create"), {"name": "Bot deck"})
        deck = CardList.objects.get(name="Bot deck")
        self.assertTrue(deck.reserved_for_cpu)
        self.assertContains(self.client.get(reverse("weiss:cpu_home")), "data-express-prompt")
        self.client.post(reverse("weiss:list_express_skip"))
        lists = self.client.get(reverse("weiss:lists"))
        self.assertEqual(list(lists.context["lists"]), [])
        self.assertNotIn(deck, lists.context["card_lists"])
        self.assertEqual(self.client.get(reverse("weiss:list", args=[deck.pk])).status_code, 200)
        self.assertNotIn(deck, self.client.get(reverse("weiss:play_rooms")).context["decks"])

    def test_a_player_cant_use_a_reserved_deck(self):
        deck = self.legal_deck(reserved_for_cpu=True)
        room = GameRoom.objects.create(host=self.staff)
        self.assertEqual(self.client.post(reverse("weiss:play_deck", args=[room.pk]), {"deck": deck.pk}).status_code, 404)

    def create_profile(self, **fields):
        deck = self.legal_deck(reserved_for_cpu=True)
        self.client.post(reverse("weiss:cpu_profile_create"), {"name": "Rapi Bot", "aggression": 1, "model": "standard", "deck": deck.pk, **fields})
        return CpuProfile.objects.get(name=fields.get("name", "Rapi Bot"))

    def test_creating_a_profile_and_its_checks(self):
        profile = self.create_profile()
        self.assertEqual((profile.aggression, profile.model, profile.finalized), (1, "standard", False))
        for bad in ({"name": ""}, {"name": "A", "aggression": 9}, {"name": "A", "aggression": 0}, {"name": "A", "model": "psychic"}):
            self.client.post(reverse("weiss:cpu_profile_create"), {"aggression": 1, "model": "standard", **bad})
        self.assertEqual(CpuProfile.objects.count(), 1)

    def test_only_a_reserved_deck_can_go_on_a_profile(self):
        ordinary = self.legal_deck()
        self.client.post(reverse("weiss:cpu_profile_create"), {"name": "A", "aggression": 1, "model": "standard", "deck": ordinary.pk})
        self.assertIsNone(CpuProfile.objects.get(name="A").deck)

    def test_finalizing_needs_a_legal_deck(self):
        deck = CardList.objects.create(user=self.staff, name="Short", reserved_for_cpu=True)
        profile = CpuProfile.objects.create(name="A", deck=deck)
        response = self.client.post(reverse("weiss:cpu_profile_finalize", args=[profile.pk]), {"finalized": "on"}, follow=True)
        self.assertContains(response, "be finalized yet")
        profile.refresh_from_db()
        self.assertFalse(profile.finalized)
        good = self.create_profile()
        self.client.post(reverse("weiss:cpu_profile_finalize", args=[good.pk]), {"finalized": "on"})
        good.refresh_from_db()
        self.assertTrue(good.finalized)

    def test_setting_aggression(self):
        profile = self.create_profile()
        self.client.post(reverse("weiss:cpu_profile_update", args=[profile.pk]), {"name": "Mean", "aggression": 3, "model": "standard", "deck": profile.deck_id})
        profile.refresh_from_db()
        self.assertEqual((profile.name, profile.aggression), ("Mean", 3))

    def challenge(self):
        profile = self.create_profile()
        self.client.post(reverse("weiss:cpu_profile_finalize", args=[profile.pk]), {"finalized": "on"})
        self.client.force_login(self.player)
        mine = self.legal_deck(user=self.player)
        response = self.client.post(reverse("weiss:play_vs_cpu"), {"cpu": profile.pk, "deck": mine.pk})
        room = GameRoom.objects.get(host=self.player)
        self.assertRedirects(response, reverse("weiss:play_room", args=[room.pk]))
        self.client.post(reverse("weiss:play_action", args=[room.pk]), json.dumps({"type": "intro_done"}), content_type="application/json")
        room.refresh_from_db()
        return room, profile

    def test_only_finalized_cpus_are_offered(self):
        profile = self.create_profile()
        self.client.force_login(self.player)
        mine = self.legal_deck(user=self.player)
        self.assertNotContains(self.client.get(reverse("weiss:play_rooms")), "Rapi Bot")
        self.assertEqual(self.client.post(reverse("weiss:play_vs_cpu"), {"cpu": profile.pk, "deck": mine.pk}).status_code, 404)
        CpuProfile.objects.filter(pk=profile.pk).update(finalized=True)
        self.assertContains(self.client.get(reverse("weiss:play_rooms")), "Rapi Bot")

    def test_a_challenge_starts_a_game_with_the_cpu_seated(self):
        room, profile = self.challenge()
        self.assertEqual(room.status, "playing")
        self.assertEqual(room.guest, cpu_user())
        self.assertEqual(room.guest_deck, profile.deck)
        self.assertIn("rps", room.state)
        self.assertEqual(room.state["players"][str(room.guest_id)]["name"], "Rapi Bot")
        self.assertContains(self.client.get(reverse("weiss:play_room", args=[room.pk])), 'data-poll-ms="700"')

    def test_nobody_can_log_in_as_the_cpu(self):
        self.assertFalse(cpu_user().has_usable_password())
        self.assertFalse(cpu_user().is_active)

    def test_polling_moves_the_cpu_a_step_at_a_time_after_a_wait(self):
        room, _ = self.challenge()
        state_url = reverse("weiss:play_state", args=[room.pk])
        self.client.get(state_url)
        room.refresh_from_db()
        self.assertEqual(room.state["rps"]["picks"], {})  # too soon
        GameRoom.objects.filter(pk=room.pk).update(updated="2000-01-01T00:00:00Z")
        self.client.get(state_url)
        room.refresh_from_db()
        self.assertIn(str(room.guest_id), room.state["rps"]["picks"])

    def play_out(self, room, limit=1500):
        """A full game against the CPU through the real code, with a player who only does the minimum."""
        rng = random.Random(3)
        action_url = reverse("weiss:play_action", args=[room.pk])
        me = str(self.player.pk)
        for _ in range(limit):
            room = GameRoom.objects.get(pk=room.pk)
            if room.state.get("game_over"):
                return room
            room = play.cpu_step(room, wait=False)
            action = cpu.next_action(room.state, me, play.card_lookups(room.state)["info"], 1, rng)
            if action:
                response = self.client.post(action_url, json.dumps(action), content_type="application/json")
                self.assertEqual(response.status_code, 200, response.content[:300])
            elif room.state.get("rps", {}).get("winner"):
                self.client.post(action_url, json.dumps({"type": "rps_done"}), content_type="application/json")
        self.fail("The game didn't finish")

    def finish(self, room, loser):
        """The game ends by this player reaching level 4."""
        side = room.state["players"][str(loser)]
        side["zones"]["level"] = [game.new_card(self.climax.pk) for _ in range(game.LOSING_LEVEL)]
        room.state.pop("rps", None)
        play.play_action(room, self.player.pk, {"type": "chat", "text": "."})
        room.refresh_from_db()

    def wins_of(self, deck):
        deck.refresh_from_db()
        return deck.wins, deck.cpu_wins

    def test_a_players_deck_beating_a_cpu_counts_apart(self):
        room, profile = self.challenge()
        self.finish(room, room.guest_id)
        self.assertEqual(self.wins_of(room.host_deck), (0, 1))
        self.assertEqual(self.wins_of(profile.deck), (0, 0))

    def test_a_cpus_deck_beating_a_player_is_a_win_against_a_human(self):
        room, profile = self.challenge()
        self.finish(room, self.player.pk)
        self.assertEqual(self.wins_of(profile.deck), (1, 0))
        self.assertEqual(self.wins_of(room.host_deck), (0, 0))

    def test_a_game_between_players_counts_as_before(self):
        other = User.objects.create_user("other", password="x")
        mine, theirs = self.legal_deck(user=self.player), self.legal_deck(user=other)
        room = GameRoom(host=self.player, guest=other, host_deck=mine, guest_deck=theirs, status="playing")
        play.deal(room)
        room.save()
        self.finish(room, other.pk)
        self.assertEqual(self.wins_of(mine), (1, 0))

    def test_the_decks_page_shows_each_with_its_own_icon(self):
        deck = self.legal_deck()
        CardList.objects.filter(pk=deck.pk).update(wins=2, cpu_wins=3)
        for url in (reverse("weiss:lists"), reverse("weiss:list", args=[deck.pk])):
            page = self.client.get(url)
            self.assertContains(page, "★★<")
            self.assertContains(page, "🤖🤖🤖")
            self.assertContains(page, "3 wins against CPUs")
        self.assertEqual(CardList(cpu_wins=25).cpu_win_icons, "🤖 ×25")

    def test_a_deck_with_no_wins_shows_neither(self):
        self.assertNotContains(self.client.get(reverse("weiss:list", args=[self.legal_deck().pk])), "deck-wins")

    def test_a_room_plays_by_its_profiles_model(self):
        room, profile = self.challenge()
        CpuProfile.objects.filter(pk=profile.pk).update(model="strategic", aggression=3)
        with mock.patch.object(cpu, "next_action", return_value=None) as chooser:
            play.cpu_step(room, wait=False)
        self.assertEqual(chooser.call_args.args[3], 3)
        self.assertEqual(chooser.call_args.kwargs["model"], "strategic")

    def test_a_whole_game_a_win_and_a_rematch_against_the_cpu(self):
        room, profile = self.challenge()
        room = self.play_out(room)
        over = room.state["game_over"]
        host_won = over["winner"] == str(room.host_id)
        self.assertEqual(self.wins_of(room.host_deck if host_won else room.guest_deck), (0, 1) if host_won else (1, 0))
        action_url = reverse("weiss:play_action", args=[room.pk])
        self.client.post(action_url, json.dumps({"type": "rematch"}), content_type="application/json")
        room.refresh_from_db()
        room = play.cpu_step(room, wait=False)
        self.assertEqual(room.state["game_number"], 2)
        self.assertIsNone(room.state.get("game_over"))

    def test_ending_the_match_goes_back_to_setup_and_a_new_game_still_works(self):
        room, _ = self.challenge()
        room = self.play_out(room)
        action_url = reverse("weiss:play_action", args=[room.pk])
        self.assertEqual(self.client.post(action_url, json.dumps({"type": "end_match"}), content_type="application/json").json()["status"], "setup")
        page = self.client.get(reverse("weiss:play_room", args=[room.pk]))
        self.assertContains(page, "Rapi Bot")
        self.client.post(reverse("weiss:play_start", args=[room.pk]))
        room.refresh_from_db()
        self.assertEqual(room.status, "playing")

    def test_it_turns_down_changing_the_rules(self):
        room, _ = self.challenge()
        action_url = reverse("weiss:play_action", args=[room.pk])
        self.client.post(action_url, json.dumps({"type": "rules_request"}), content_type="application/json")
        room.refresh_from_db()
        room = play.cpu_step(room, wait=False)
        self.assertTrue(game.rules_on(room.state))
        self.assertNotIn("rules_request", room.state)

    def test_a_refused_action_doesnt_stick_the_game(self):
        room, _ = self.challenge()
        room.state.pop("rps")
        room.state["phase"] = "main"
        room.state["turn"] = str(room.guest_id)
        room.save()
        original = cpu.next_action
        cpu.next_action = lambda *a, **k: {"type": "nonsense"}
        try:
            with self.assertLogs("weiss.play", "WARNING"):
                room = play.cpu_step(room, wait=False)
        finally:
            cpu.next_action = original
        self.assertEqual(room.state["phase"], "climax")  # moved on instead

    def test_a_deleted_profile_leaves_the_game_playable(self):
        room, profile = self.challenge()
        profile.delete()
        room.refresh_from_db()
        self.assertTrue(room.vs_cpu)
        self.assertIsNotNone(play.cpu_step(room, wait=False))
