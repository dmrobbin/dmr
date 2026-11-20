"""Audit: every way a player can change their world-mode save, checked mid-tutorial (docs/world-tutorial-plan.md,
"While it's on"). One test per move, at the "talk" step (a guide's chosen; nothing past "talk" is open yet).
"""
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from . import world, world_events as events, world_rewards
from .test_profile import player
from .test_world import SET
from .test_world_tutorial import TutorialBase


class MovesAreRefusedTests(TutorialBase):
    """Every save-changing function, called directly (as the rest of the tutorial suite does), refused mid-tutorial."""

    def setUp(self):
        super().setUp()
        self.save = self.through("talk")

    def test_travel_is_refused(self):
        self.refused(world.travel, self.save, "cafe")

    def test_waiting_is_refused(self):
        self.refused(world.wait, self.save)

    def test_dueling_the_guide_is_refused_before_its_step(self):
        self.refused(world.start_duel, self.save, self.aang.pk)

    def test_dueling_someone_else_is_refused(self):
        self.refused(world.start_duel, self.save, self.other.pk)

    def test_giving_a_gift_is_refused_before_its_step(self):
        self.refused(world.give, self.save, self.aang.pk, "cake")

    def test_talking_to_someone_not_the_guide_is_refused(self):
        self.refused(world.talk, self.save, self.other.pk)

    def test_buying_packs_is_refused(self):
        self.refused(world.buy_packs, self.save, SET, 1)

    def test_buying_a_specialty_pack_is_refused(self):
        self.refused(world.buy_specialty, self.save, "lucky_pack", {})

    def test_checking_out_the_basket_is_refused(self):
        self.refused(world.checkout, self.save, [{"kind": "pack", "set": SET, "count": 1}])

    def test_buying_a_single_card_is_refused(self):
        self.refused(world.buy_card, self.save, "1")

    def test_buying_a_gift_is_refused(self):
        self.refused(world.buy_gift, self.save, "cake")

    def test_requesting_a_set_is_refused(self):
        self.refused(world.request_set, self.save, SET)

    def test_taking_or_finishing_a_quest_is_refused(self):
        self.refused(world.quest_act, self.save, self.aang.pk, "offer", "nothing", {})

    def test_entering_the_tournament_is_refused(self):
        self.refused(events.enter, self.save)

    def test_picking_a_card_is_refused(self):
        self.refused(world_rewards.pick_card, self.save, 1)


class ViewsRefuseThroughThePageTests(TutorialBase):
    """The views that aren't a simple @town_move wrapper (world_buy, world_event_enter, world_board): they catch the
    ValueError themselves and redirect, so posting through the test client is the only way to see the refusal."""

    def setUp(self):
        super().setUp()
        self.save = self.through("talk")
        self.save.save()
        self.client.force_login(self.user)

    def test_the_shop_view_refuses_buying_packs(self):
        money = self.save.money
        response = self.client.post(reverse("weiss:world_buy", args=[1]), {"set": SET, "count": 1})
        self.assertRedirects(response, reverse("weiss:world_town", args=[1]))  # buying would go to world_opened instead
        self.save.refresh_from_db()
        self.assertEqual(self.save.money, money)

    def test_the_tournament_entry_view_refuses(self):
        response = self.client.post(reverse("weiss:world_event_enter", args=[1]))
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("is waiting" in t for t in texts), texts)

    def test_the_notice_board_view_refuses_taking_a_quest(self):
        before = dict(self.save.quests)
        response = self.client.post(reverse("weiss:world_board", args=[1]), {"act": "take", "quest": "anything"})
        texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("is waiting" in t for t in texts), texts)
        self.save.refresh_from_db()
        self.assertEqual(self.save.quests, before)


class NonStaffProtectionTests(TutorialBase):
    """The first pass flagged test mode's staff shortcuts (wait with staff=True, and jump) as bypassing the
    tutorial. World Planner's call: by design, since test mode -- and skipping the tutorial outright -- are
    staff-only already, so a staff player's own shortcuts don't let anyone skip anything. What actually protects a
    non-staff player is tested directly here instead."""

    def setUp(self):
        super().setUp()
        self.player = player("player")
        self.save = world.start(self.player, 2, SET, tutorial_on=True)
        self.save.money = 5000
        self.save.save()
        self.save = self.through("talk")

    def test_a_non_staff_player_cant_turn_test_mode_on(self):
        self.refused(world.set_test_mode, self.save, True)

    def test_the_test_mode_view_refuses_a_non_staff_player(self):
        self.client.force_login(self.player)
        response = self.client.post(reverse("weiss:world_test_mode", args=[2]), {"on": "1"})
        self.assertEqual(response.status_code, 403)

    def test_a_non_staff_players_staff_wait_still_goes_through_the_tutorial(self):
        # test_mode(save) is False for a non-staff user regardless of the flag (it checks save.user.is_staff), so
        # wait(staff=True) still falls to the `else` branch and tutorial.allows -- that's what actually makes the
        # staff shortcut harmless, not anything tutorial-specific in wait() itself.
        self.save.flags["test_mode"] = True  # even if it were somehow set
        self.save.save()
        self.refused(world.wait, self.save, staff=True)
