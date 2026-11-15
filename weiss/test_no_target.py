"""An ability that could only pay its cost, because there's nothing for it to choose, isn't offered: no "you may"
prompt for a player, nothing for a CPU to say yes to, and no ! button (game.may_no_target)."""
import random

from django.test import SimpleTestCase

from . import abilities, cpu, game
from .test_cpu import Table

CHANGE = ('【AUTO】 Change [(1) Put this card into your waiting room] At the beginning of your draw phase, you may pay the cost. '
          'If you do, choose a card named "Ultimate Madoka" in your waiting room, and put it on the stage position that this card was on.')
MADOKA = 500


class NoTargetTests(SimpleTestCase):
    def setUp(self):
        self.t = Table()
        self.t.card(MADOKA, name="Ultimate Madoka", level=3)
        self.env = game.SimpleNamespace(info=self.t.info, name=lambda pk: self.t.info(pk)["name"])

    def triggered(self, text, ctx=None):
        """Whether the CPU's card with this AUTO ability, on its stage, would have it come up."""
        t = self.t
        source = t.seat(t.me, "B1", t.card(2000, text=text))
        t.state["ability_queue"] = []
        game.queue_ability(t.state, "2", source, abilities.parse(text)[0], {**(ctx or {}), "old_slot": "B1"}, self.env)
        return bool(t.state["ability_queue"])

    def act_why(self, text):
        t = self.t
        source = t.seat(t.me, "B1", t.card(2001, text=text))
        return game.act_status(t.state, "2", source, abilities.parse(text)[0], "B1", self.env)

    def waiting(self, *pks):
        self.t.me["zones"]["waiting"] += [game.new_card(pk) for pk in pks]

    def test_change_with_no_madoka_to_change_into_isnt_offered(self):
        self.t.stock(2)
        self.waiting(900, 901)
        self.assertFalse(self.triggered(CHANGE))

    def test_change_with_a_madoka_in_the_waiting_room_is(self):
        self.t.stock(2)
        self.waiting(900, MADOKA)
        self.assertTrue(self.triggered(CHANGE))

    def test_counting_what_paying_the_cost_puts_there(self):
        self.t.stock(2)
        self.t.me["zones"]["stock"].append(game.new_card(MADOKA))  # the top of the stock: paid into the waiting room
        self.assertTrue(self.triggered(CHANGE))
        self.t.me["zones"]["stock"].insert(0, self.t.me["zones"]["stock"].pop())  # now at the bottom: it stays
        self.assertFalse(self.triggered(CHANGE))

    def test_an_ability_that_does_something_else_too_is_still_offered(self):
        text = ('【AUTO】 At the beginning of your draw phase, you may pay the cost. If you do, draw 1 card, '
                'choose 1 "Ultimate Madoka" in your waiting room, and return it to your hand.')
        self.assertTrue(self.triggered(text))

    def test_a_may_with_no_cost_and_nothing_to_choose_isnt_asked_either(self):
        text = '【AUTO】 [(1)] When this card is placed on the stage from your hand, you may pay the cost. If you do, choose 1 "Ultimate Madoka" in your waiting room, and return it to your hand.'
        self.t.stock(1)
        self.assertFalse(self.triggered(text))
        self.waiting(MADOKA)
        self.assertTrue(self.triggered(text))

    def test_an_act_with_nothing_to_choose_cant_be_used(self):
        text = '【ACT】 [(1) 【REST】 this card] Choose 1 "Ultimate Madoka" in your waiting room, and return it to your hand.'
        self.t.stock(1)
        self.assertEqual(self.act_why(text), "no valid target")
        self.waiting(MADOKA)
        self.assertIsNone(self.act_why(text))

    def test_choosing_on_the_stage_when_the_cost_leaves_it_alone(self):
        text = ('【AUTO】 [Put 1 card from your hand into your waiting room] When this card attacks, you may pay the cost. '
                'If you do, choose 1 of your other characters, and that character gets +1000 power until end of turn.')
        self.t.hand(901)
        self.assertFalse(self.triggered(text))  # it's alone on the stage
        self.t.seat(self.t.me, "C1", 902)
        self.assertTrue(self.triggered(text))

    def test_an_act_whose_cost_brings_its_own_target_can(self):
        text = '【ACT】 [Put 1 card from your hand into your waiting room] Choose 1 character in your waiting room, and return it to your hand.'
        self.assertEqual(self.act_why(text), "needs 1 more to pay with")  # nothing in hand to pay with
        self.t.hand(901)  # a character: discarded, it's the one to choose
        self.assertIsNone(self.act_why(text))

    def test_the_cpu_doesnt_use_an_act_with_nothing_to_choose(self):
        text = '【ACT】 [(1) 【REST】 this card] Choose 1 "Ultimate Madoka" in your waiting room, and return it to your hand.'
        t = self.t
        t.stock(3)
        t.seat(t.me, "B1", t.card(2002, text=text))
        t.refresh()
        t.state["acts"] = {p: game.player_acts(t.state, p, self.env) for p in t.state["players"]}
        rows = t.state["acts"]["2"][t.me["stage"]["B1"]["uid"]]
        self.assertEqual(rows[0]["why"], "no valid target")
        mind = cpu.Mind(t.state, "2", t.info, cpu.Temper(1), random.Random(1))
        self.assertFalse(list(mind.usable_acts()))
        self.waiting(MADOKA)  # with something to choose, it would
        t.state["acts"] = {p: game.player_acts(t.state, p, self.env) for p in t.state["players"]}
        self.assertTrue(list(mind.usable_acts()))
