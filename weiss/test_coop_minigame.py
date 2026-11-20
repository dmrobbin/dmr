from django.urls import reverse

from . import challenge
from .models import ChallengeRun
from .test_coop import PlayingSetup
from .test_minigames import make_set as pictured_set


class CoopMinigameTests(PlayingSetup):
    def setUp(self):
        super().setUp()
        pictured_set(30)  # the game's cards come from a pictured set, the same for both players
        self.pair.path = {"floors": [[self.opener.pk, self.filler.pk, None], [self.anchor.pk, None, None]], "picks": [0], "done": 0,
                          "minigames": [[0, 0]], "progress": {}}
        self.pair.save()

    def both_land(self):
        self.vote(self.staff, 0)
        self.vote(self.bo, 0)
        self.pair.refresh_from_db()

    def ripen(self):
        for started in self.pair.path["minigame"]["starts"]:
            self.pair.path["minigame"]["starts"][started] -= challenge.MINIGAME_MIN_SECONDS + 1
        self.pair.save()

    def post(self, user, score):
        return self.as_(user).client.post(reverse("weiss:arcade_challenge_minigame_done"), {"score": score})

    def run_of(self, user):
        return ChallengeRun.objects.get(user=user, coop=self.pair)

    def test_both_landing_starts_one_game_and_each_starts_their_clock(self):
        self.both_land()
        minigame = self.pair.path["minigame"]
        self.assertEqual(set(minigame["starts"]), {str(self.staff.pk), str(self.bo.pk)})
        self.assertEqual(self.fresh(self.staff).path["minigame"]["seed"], self.fresh(self.bo).path["minigame"]["seed"])

    def test_both_players_get_the_same_cards(self):
        self.both_land()
        mine = self.as_(self.staff).client.get(reverse("weiss:arcade_challenge_minigame_data")).json()
        theirs = self.as_(self.bo).client.get(reverse("weiss:arcade_challenge_minigame_data")).json()
        self.assertEqual(mine["game"], theirs["game"])
        self.assertEqual([c["id"] for c in mine["cards"]], [c["id"] for c in theirs["cards"]])

    def test_the_partner_has_not_posted_so_the_node_waits(self):
        self.both_land()
        self.ripen()
        answer = self.post(self.staff, 3).json()
        self.assertEqual(answer, {"waiting": True, "redirect": reverse("weiss:arcade_challenge")})
        self.pair.refresh_from_db()
        self.assertIn("minigame", self.pair.path)
        self.assertEqual(self.pair.path.get("progress", {}).get(str(self.staff.pk), 0), 0)

    def test_a_score_posted_too_early_counts_for_nothing(self):
        self.both_land()
        response = self.post(self.staff, 3)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "That game ended too quickly to count.")
        self.pair.refresh_from_db()
        self.assertNotIn(str(self.staff.pk), self.pair.path["minigame"]["scores"])

    def test_the_higher_score_wins_the_pick_and_the_other_gets_a_lucky_pack(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 3)
        answer = self.post(self.bo, 7).json()
        self.assertEqual(answer["result"], "win")
        winner, loser = self.run_of(self.bo), self.run_of(self.staff)
        self.assertEqual([r["buff"] for r in winner.rewards], ["minigame_pick"])
        self.assertEqual(len(winner.rewards[0]["options"]), 3)
        self.assertEqual([(r["buff"], r["source"]) for r in loser.rewards], [("lucky_pack", "minigame")])
        self.assertEqual(answer["result"], "win")
        self.pair.refresh_from_db()
        self.assertTrue(self.pair.path["minigame"]["decided"])  # kept for both pages to say how it went
        self.assertNotIn([0, 0], self.pair.path["minigames"])
        self.assertEqual(self.pair.path["progress"], {str(self.staff.pk): 1, str(self.bo.pk): 1})

    def test_a_tie_gives_each_a_lucky_pack(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 4)
        answer = self.post(self.bo, 4).json()
        self.assertEqual(answer["result"], "draw")
        for user in (self.staff, self.bo):
            self.assertEqual([(r["buff"], r["source"]) for r in self.run_of(user).rewards], [("lucky_pack", "minigame")])

    def test_a_second_post_is_refused(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 3)
        again = self.post(self.staff, 9)
        self.assertEqual(again.status_code, 400)

    def test_the_winner_picks_one_of_the_three_packs_on_offer(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 1)
        self.post(self.bo, 2)
        key = self.run_of(self.bo).rewards[0]["key"]
        options = self.run_of(self.bo).rewards[0]["options"]
        off = next(buff for buff in ("climax_pick", "extra_packs") if buff not in options)
        self.as_(self.bo).client.post(reverse("weiss:arcade_challenge_minigame_pick"), {"key": key, "choice": off})
        self.assertEqual(self.run_of(self.bo).rewards[0]["buff"], "minigame_pick")  # refused: not on offer
        chosen = options[0]
        response = self.as_(self.bo).client.post(reverse("weiss:arcade_challenge_minigame_pick"), {"key": key, "choice": chosen})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([(r["buff"], r["source"]) for r in self.run_of(self.bo).rewards], [(chosen, "minigame")])

    def page(self, user):
        return self.as_(user).client.get(reverse("weiss:arcade_challenge_minigame"))

    def test_the_page_shows_the_waiting_state_then_the_result_after_a_reload(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 3)
        waiting = self.page(self.staff).context
        self.assertTrue(waiting["coop"])
        self.assertTrue(waiting["waiting"])
        self.assertNotIn("result", waiting)
        self.post(self.bo, 7)
        loser, winner = self.page(self.staff).context, self.page(self.bo).context
        self.assertEqual(loser["result"]["scores"], {"you": 3, "partner": 7})
        self.assertTrue(loser["lucky_pack"])
        self.assertFalse(loser["pack_pick"])
        self.assertEqual(winner["result"]["title"], "You won the game!")
        self.assertTrue(winner["pack_pick"])
        self.assertEqual(len(winner["packs"]), 3)
        self.assertEqual(set(winner["packs"][0]), {"key", "name", "text"})
        self.assertEqual(winner["pick_key"], self.run_of(self.bo).rewards[0]["key"])
        self.assertEqual(winner["partner"], self.staff.username)

    def test_a_repeat_post_after_the_decision_changes_nothing(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 3)
        self.post(self.bo, 7)
        before = [(r["buff"], r["source"]) for r in self.run_of(self.staff).rewards]
        again = self.post(self.staff, 99)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["result"], "lose")
        self.assertEqual([(r["buff"], r["source"]) for r in self.run_of(self.staff).rewards], before)

    def test_the_pick_is_made_once(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 1)
        self.post(self.bo, 2)
        key = self.run_of(self.bo).rewards[0]["key"]
        options = self.run_of(self.bo).rewards[0]["options"]
        self.as_(self.bo).client.post(reverse("weiss:arcade_challenge_minigame_pick"), {"key": key, "choice": options[0]})
        again = self.as_(self.bo).client.post(reverse("weiss:arcade_challenge_minigame_pick"), {"key": key, "choice": options[1]})
        self.assertEqual(again.status_code, 400)
        self.assertEqual(self.run_of(self.bo).rewards[0]["buff"], options[0])

    def test_the_partner_cannot_take_the_winners_pick(self):
        self.both_land()
        self.ripen()
        self.post(self.staff, 1)
        self.post(self.bo, 2)
        key = self.run_of(self.bo).rewards[0]["key"]
        options = self.run_of(self.bo).rewards[0]["options"]
        refused = self.as_(self.staff).client.post(reverse("weiss:arcade_challenge_minigame_pick"), {"key": key, "choice": options[0]})
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(self.run_of(self.bo).rewards[0]["buff"], "minigame_pick")

    def test_a_stale_pick_is_refused_once_the_reward_has_changed(self):
        from . import challenge as chal
        self.both_land()
        self.ripen()
        self.post(self.staff, 1)
        self.post(self.bo, 2)
        stale = self.run_of(self.bo)  # loaded before the pick, as a second request at the same time would have it
        key = stale.rewards[0]["key"]
        options = stale.rewards[0]["options"]
        chal.pick_minigame_pack(self.run_of(self.bo), key, options[0])
        with self.assertRaisesRegex(ValueError, "isn't a pack to choose"):
            chal.pick_minigame_pack(stale, key, options[1])
        self.assertEqual(self.run_of(self.bo).rewards[0]["buff"], options[0])
