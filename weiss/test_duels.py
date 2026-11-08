"""Co-op vs. battles: after each boss the pair play each other, for first pick of the curses (see docs/coop-vs-battles.md)."""
import json
import random

from django.urls import reverse

from . import augments, buffs, challenge, coop, curses, game
from .models import ChallengeRun, CoopRun, GameRecord, GameRoom
from .test_bosses import CoopBossSetup, settings


class DuelSetup(CoopBossSetup):
    """The pair on the floor after the first boss, which they've just beaten."""

    def setUp(self):
        super().setUp()
        settings(coop_boss_health=10)
        self.fight(self.staff)
        self.hit(self.staff, 12)

    def ready(self, user):
        return self.as_(user).client.post(reverse("weiss:arcade_coop_duel_ready"))

    def duel(self):
        return coop.duel_of(self.fresh(self.staff))

    def duel_room(self):
        return GameRoom.objects.get(coop_duel=self.pair)

    def act(self, user, action):
        return self.as_(user).client.post(reverse("weiss:play_action", args=[self.duel_room().pk]), json.dumps(action), content_type="application/json")

    def pick(self, user, curse_id, augment_id=None):
        """This player's picks: the curse, and the augment (the first left, if not given)."""
        augment_id = augment_id if augment_id is not None else (coop.augments_left(self.duel()) or [""])[0]
        return self.as_(user).client.post(reverse("weiss:arcade_coop_duel_pick"), {"curse": curse_id, "augment": augment_id}, follow=True)


class DuelStartTests(DuelSetup):
    def test_the_boss_brings_a_vs_battle_instead_of_a_pick_each(self):
        duel = self.duel()
        self.assertEqual((duel["floor"], len(duel["options"]), len(duel["augments"]), duel["winner"], duel["room"]),
                         (4, curses.OFFER, augments.OFFER, None, None))
        for user in (self.staff, self.bo):
            rewards = [r["buff"] for r in self.fresh(user).rewards]
            self.assertNotIn("augment", rewards)
            self.assertNotIn("curse", rewards)

    def test_the_augments_offered_are_ones_both_could_take(self):
        ChallengeRun.objects.filter(pk=self.host.pk).update(augments=["devotion", "highlander"])
        ChallengeRun.objects.filter(pk=self.guest.pk).update(augments=["clean_refresh"])
        for _ in range(10):
            offered = augments.shared_offer([self.fresh(self.staff), self.fresh(self.bo)], random)
            self.assertFalse(set(offered) & {"devotion", "highlander", "clean_refresh"})
            self.assertEqual(len(offered), augments.OFFER)

    def test_the_next_fight_waits_for_it(self):
        page = self.fight(self.staff)
        self.assertContains(page, "Your vs. battle with your partner comes first")
        self.assertEqual(page.redirect_chain[-1][0], reverse("weiss:arcade_coop_duel"))
        self.assertContains(self.as_(self.bo).client.get(reverse("weiss:arcade_challenge")), "Your vs. battle with staff is due.")

    def test_leaving_the_boss_goes_to_it(self):
        response = self.as_(self.staff).client.post(reverse("weiss:play_action", args=[self.room_of(self.staff).pk]),
                                                    json.dumps({"type": "challenge_leave"}), content_type="application/json")
        self.assertEqual(response.json()["redirect"], reverse("weiss:arcade_coop_duel"))

    def test_its_dealt_once_both_are_ready(self):
        page = self.ready(self.staff)
        self.assertRedirects(page, reverse("weiss:arcade_coop_duel"))
        self.assertEqual(self.duel()["ready"], [str(self.staff.pk)])
        self.assertFalse(GameRoom.objects.filter(coop_duel=self.pair).exists())
        self.assertContains(self.as_(self.staff).client.get(reverse("weiss:arcade_coop_duel")), "You're ready.")
        page = self.ready(self.bo)
        room = self.duel_room()
        self.assertRedirects(page, reverse("weiss:play_room", args=[room.pk]), fetch_redirect_response=False)
        self.assertEqual((room.host_id, room.guest_id, room.host_deck_id, room.guest_deck_id, room.arcade_run_id, room.vs_cpu),
                         (self.staff.pk, self.bo.pk, self.fresh(self.staff).deck_id, self.fresh(self.bo).deck_id, None, False))
        self.assertEqual(self.duel()["room"], room.pk)
        self.assertRedirects(self.as_(self.staff).client.get(reverse("weiss:arcade_coop_duel")),  # the waiting player's page takes them there
                             reverse("weiss:play_room", args=[room.pk]), fetch_redirect_response=False)
        self.assertNotIn("curses", room.state["players"][str(self.staff.pk)])

    def test_a_partner_whose_deck_broke_is_made_unready(self):
        self.ready(self.bo)
        self.fresh(self.bo).deck.entries.all().delete()
        self.ready(self.staff)
        self.assertFalse(GameRoom.objects.filter(coop_duel=self.pair).exists())
        self.assertEqual(self.duel()["ready"], [str(self.staff.pk)])

    def test_each_players_augments_play_but_no_curses(self):
        ChallengeRun.objects.filter(pk=self.host.pk).update(augments=["deep_reserves", "head_start", "highlander"], curses=["hoard", "iron_skin"])
        ChallengeRun.objects.filter(pk=self.guest.pk).update(augments=["glass_cannon"], curses=["deep_pockets"])
        self.ready(self.staff)
        self.ready(self.bo)
        players = self.duel_room().state["players"]
        mine, theirs = players[str(self.staff.pk)], players[str(self.bo.pk)]
        self.assertEqual((mine["augments"], theirs["augments"]), (["deep_reserves", "head_start"], ["glass_cannon"]))
        self.assertEqual((len(mine["zones"]["stock"]), len(mine["zones"]["hand"])), (augments.RESERVES, game.STARTING_HAND + augments.HEAD_START))
        self.assertEqual((theirs["zones"]["stock"], len(theirs["zones"]["hand"])), ([], game.STARTING_HAND))
        self.assertNotIn("curses", mine)
        self.assertNotIn("curses", theirs)

    def test_its_table_cant_be_changed_or_played_again(self):
        self.ready(self.staff)
        self.ready(self.bo)
        room = self.duel_room()
        for name in ("weiss:play_reset", "weiss:play_start", "weiss:play_delete"):
            self.as_(self.staff).client.post(reverse(name, args=[room.pk]))
        room.refresh_from_db()
        self.assertEqual(room.status, GameRoom.Status.PLAYING)
        self.act(self.bo, {"type": "duel_concede"})
        self.assertEqual(self.act(self.staff, {"type": "rematch"}).status_code, 400)


class DuelResultTests(DuelSetup):
    def setUp(self):
        super().setUp()
        self.ready(self.staff)
        self.ready(self.bo)
        self.losses = CoopRun.objects.get(pk=self.pair.pk).losses
        self.lives = {user: self.fresh(user).lives for user in (self.staff, self.bo)}

    def test_conceding_ends_it_and_no_loss_counts(self):
        data = self.act(self.bo, {"type": "duel_concede"}).json()
        self.assertEqual((data["board"]["game_over"]["reason"], data["duel"]["mine"], data["duel"]["theirs"]), ("concede", 0, 1))
        duel = self.duel()
        self.assertEqual((duel["winner"], duel["loser"]), (str(self.staff.pk), str(self.bo.pk)))
        pair = CoopRun.objects.get(pk=self.pair.pk)
        self.assertEqual((pair.losses, pair.duel_wins), (self.losses, {str(self.staff.pk): 1}))
        self.assertEqual({user: self.fresh(user).lives for user in (self.staff, self.bo)}, self.lives)
        self.assertTrue(GameRecord.objects.filter(host=self.staff, guest=self.bo, cpu=False).exists())
        self.assertEqual(self.act(self.bo, {"type": "duel_concede"}).status_code, 400)  # once only

    def test_a_game_won_the_usual_way_counts_too(self):
        room = self.duel_room()
        game.end_game(room.state, str(self.staff.pk), "level", "reaches level 4")
        from .play import game_ended
        game_ended(room, room.state["game_over"])
        self.assertEqual(self.duel()["winner"], str(self.bo.pk))
        self.assertEqual(CoopRun.objects.get(pk=self.pair.pk).duel_wins, {str(self.bo.pk): 1})

    def test_the_winner_picks_first_and_the_loser_from_whats_left(self):
        self.act(self.bo, {"type": "duel_concede"})
        first, second, third = self.duel()["options"]
        boon, other, last = self.duel()["augments"]
        self.assertContains(self.pick(self.bo, first), "The winner picks first")
        page = self.as_(self.bo).client.get(reverse("weiss:arcade_coop_duel"))
        self.assertContains(page, "staff picks their augment and curse first.")
        self.assertNotContains(page, 'name="curse"')
        self.assertNotContains(page, 'name="augment"')
        self.assertContains(self.pick(self.staff, first, "nope"), "Choose one of the augments left.")
        self.pick(self.staff, first, boon)
        self.assertEqual((self.fresh(self.staff).curses, self.fresh(self.staff).augments), ([first], [boon]))
        page = self.as_(self.bo).client.get(reverse("weiss:arcade_coop_duel"))
        self.assertContains(page, "Taken by staff", count=2)
        for gone in (first, boon):
            self.assertNotContains(page, f'value="{gone}"')
        for left in (second, third, other, last):
            self.assertContains(page, f'value="{left}"')
        self.assertContains(self.pick(self.bo, first, other), "Choose one of the curses left.")
        self.assertContains(self.pick(self.bo, second, boon), "Choose one of the augments left.")
        self.assertContains(self.pick(self.staff, second), "taken your augment and curse already.")
        self.pick(self.bo, third, last)
        self.assertEqual((self.fresh(self.staff).curses, self.fresh(self.bo).curses), ([first], [third]))
        self.assertEqual((self.fresh(self.staff).augments, self.fresh(self.bo).augments), ([boon], [last]))
        self.assertIsNone(self.duel())
        self.assertFalse(GameRoom.objects.filter(coop_duel=self.pair).exists())
        self.assertIsNone(challenge.curse_due(self.fresh(self.bo)))
        page = self.as_(self.staff).client.get(reverse("weiss:arcade_coop_duel"))
        self.assertContains(page, "You've both taken your augment and curse")
        self.assertContains(page, "Taken by You", count=2)

    def test_with_no_augment_left_the_loser_gets_packs(self):
        self.act(self.bo, {"type": "duel_concede"})
        pair = CoopRun.objects.get(pk=self.pair.pk)
        pair.path["duel"]["augments"] = ["devotion"]
        CoopRun.objects.filter(pk=pair.pk).update(path=pair.path)
        options = self.duel()["options"]
        self.pick(self.staff, options[0], "devotion")
        packs = self.fresh(self.bo).packs
        self.assertContains(self.as_(self.bo).client.get(reverse("weiss:arcade_coop_duel")), "no augment left for you")
        self.pick(self.bo, options[1], "")
        self.assertEqual((self.fresh(self.bo).augments, self.fresh(self.bo).packs), ([], packs + buffs.EXTRA_PACKS))

    def test_curses_are_each_players_own(self):
        self.act(self.bo, {"type": "duel_concede"})
        options = self.duel()["options"]
        self.pick(self.staff, options[0])
        self.pick(self.bo, options[1])
        staff_curses = curses.for_game(self.fresh(self.staff), True)
        bo_curses = curses.for_game(self.fresh(self.bo), True)
        self.assertEqual({k for part in staff_curses for k in part}, {options[0]})
        self.assertEqual({k for part in bo_curses for k in part}, {options[1]})

    def test_the_rivalry_shows_on_the_pages_and_leaderboard(self):
        self.act(self.bo, {"type": "duel_concede"})
        self.assertContains(self.as_(self.bo).client.get(reverse("weiss:arcade_challenge")), "Vs. battles: you 0 – 1 staff")
        self.assertContains(self.as_(self.bo).client.get(reverse("weiss:arcade_coop_duel")), "staff won.")
        pair = coop.leaderboard()
        found = [p for p in pair if p.pk == self.pair.pk]
        if found:  # on the board once the pair has a score
            self.assertEqual([run.duels for run in found[0].halves], [1, 0])
