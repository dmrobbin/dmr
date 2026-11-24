"""Round two (docs/round-two-plan.md): the duel recap (the points by turn and the standout moments), the CPUs who remember
the player (history lines in a duel's intro) and the people journal in world mode."""
import json
from unittest import mock

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from . import game, play, test_world, world, world_people
from .models import Chatter, CpuProfile, GameRecord, GameRoom, GiftItem
from .test_world import staff_user


def state_with(points, facts=None, levels=(0, 0), winner="host", order=("1", "2")):
    """A finished game's state: `points` as [turn, host, guest] rows, `facts` as game.record_hit/record_climax write them."""
    timeline = {"points": [{"turn": turn, "by": "1", "damage": {order[0]: host, order[1]: guest}} for turn, host, guest in points], "hits": []}
    players = {pk: {"name": pk, "zones": {"level": ["card"] * level}} for pk, level in zip(order, levels)}
    return {"order": list(order), "players": players, "turn_number": points[-1][0] if points else 0, "timeline": timeline,
            "timeline_facts": facts or {"attacks": [], "climaxes": []},
            "game_over": {"winner": order[0] if winner == "host" else order[1], "loser": order[1] if winner == "host" else order[0]}}


class RecapRulesTests(TestCase):
    def kinds(self, recap):
        return [moment["kind"] for moment in recap["moments"]]

    def test_the_points_are_by_turn_as_host_then_guest(self):
        recap = game.duel_recap(state_with([(1, 0, 7), (2, 3, 14), (9, 21, 21)]))
        self.assertEqual(recap["points"], [[1, 0, 7], [2, 3, 14], [9, 21, 21]])

    def test_a_turn_recorded_twice_keeps_the_last(self):
        state = state_with([(1, 0, 7), (1, 0, 9)])
        self.assertEqual(game.duel_recap(state)["points"], [[1, 0, 9]])

    def test_a_comeback_needs_seven_points_behind_at_some_turn(self):
        self.assertIn("comeback", self.kinds(game.duel_recap(state_with([(1, 7, 0), (2, 14, 6), (3, 21, 14)]))))  # the host won from 8 behind
        self.assertNotIn("comeback", self.kinds(game.duel_recap(state_with([(1, 6, 0), (2, 12, 6), (3, 15, 9)]))))  # 6 behind at most

    def test_a_comeback_is_the_winners_deficit_at_its_turn(self):
        # The host (the winner) took 2, then 12 (10 more than the guest's 2), then the game-ending 14 against 28.
        recap = game.duel_recap(state_with([(1, 2, 0), (2, 12, 2), (4, 14, 28)]))
        comeback = next(moment for moment in recap["moments"] if moment["kind"] == "comeback")
        self.assertEqual((comeback["turn"], comeback["n"], comeback["side"]), (2, 10, "host"))

    def test_a_wire_to_wire_win_is_not_a_comeback(self):
        # The host led all game: the other player's points rise to 28, which is the final entry, not a deficit.
        recap = game.duel_recap(state_with([(1, 0, 2), (2, 2, 12), (5, 5, 28)]))
        self.assertNotIn("comeback", self.kinds(recap))

    def test_a_narrow_win_has_no_comeback(self):
        self.assertNotIn("comeback", self.kinds(game.duel_recap(state_with([(1, 1, 0), (2, 5, 3), (3, 8, 6)]))))

    def test_close_finish_is_both_at_level_three(self):
        recap = game.duel_recap(state_with([(9, 21, 21)], levels=(3, 3)))
        self.assertIn("close_finish", self.kinds(recap))
        self.assertNotIn("close_finish", self.kinds(game.duel_recap(state_with([(9, 21, 21)], levels=(3, 2)))))

    def test_flawless_is_the_winner_at_level_one_or_none(self):
        self.assertIn("flawless", self.kinds(game.duel_recap(state_with([(9, 0, 21)], levels=(1, 3)))))
        self.assertNotIn("flawless", self.kinds(game.duel_recap(state_with([(9, 0, 21)], levels=(2, 3)))))

    def test_a_big_hit_counts_from_three_damage_and_is_the_attackers(self):
        facts = {"attacks": [[4, 0, 2, 0], [5, 1, 3, 0], [6, 0, 3, 0]], "climaxes": []}
        recap = game.duel_recap(state_with([(6, 0, 0)], facts=facts))
        big = next(moment for moment in recap["moments"] if moment["kind"] == "big_hit")
        self.assertEqual((big["turn"], big["side"], big["n"]), (5, "guest", 3))  # the first 3 (turn 5), its attacker's seat

    def test_a_small_hit_is_no_moment(self):
        facts = {"attacks": [[4, 0, 2, 0]], "climaxes": []}
        self.assertNotIn("big_hit", self.kinds(game.duel_recap(state_with([(4, 0, 0)], facts=facts))))

    def test_a_big_cancel_is_for_the_attacker_whose_attack_was_cancelled(self):
        facts = {"attacks": [[3, 0, 4, 1]], "climaxes": []}  # the host's 4-damage attack, cancelled by the guest
        recap = game.duel_recap(state_with([(3, 0, 0)], facts=facts))
        cancel = next(moment for moment in recap["moments"] if moment["kind"] == "big_cancel")
        self.assertEqual((cancel["side"], cancel["n"]), ("host", 4))

    def test_a_burst_turn_is_six_damage_in_one_turn_from_one_side(self):
        facts = {"attacks": [[7, 0, 3, 0], [7, 0, 3, 0], [8, 1, 5, 0]], "climaxes": []}
        recap = game.duel_recap(state_with([(8, 0, 0)], facts=facts))
        burst = next(moment for moment in recap["moments"] if moment["kind"] == "burst_turn")
        self.assertEqual((burst["turn"], burst["side"], burst["n"]), (7, "host", 6))

    def test_at_most_three_moments_each_kind_once_in_priority_order(self):
        facts = {"attacks": [[2, 0, 9, 0], [2, 0, 9, 1], [3, 1, 6, 0]], "climaxes": []}
        recap = game.duel_recap(state_with([(1, 0, 7), (2, 0, 21), (9, 14, 21)], facts=facts, levels=(3, 3)))
        self.assertEqual(len(recap["moments"]), 3)
        self.assertEqual(self.kinds(recap), ["close_finish", "big_hit", "big_cancel"])  # no comeback: the host was ahead
        self.assertEqual(len(set(self.kinds(recap))), len(recap["moments"]))

    def test_a_game_with_nothing_to_say_has_no_moments(self):
        self.assertEqual(game.duel_recap(state_with([(1, 1, 2)], levels=(2, 2)))["moments"], [])  # no one at level 0 or 1, nothing close

    def test_a_game_that_ended_before_turn_one_has_no_points(self):
        self.assertEqual(game.duel_recap(state_with([]))["points"], [])


class RecapSizeTests(TestCase):
    def test_a_thirty_turn_game_keeps_its_facts_under_two_kilobytes(self):
        state = {"order": ["1", "2"], "turn_number": 1, "players": {}}
        for turn in range(1, 31):
            state["turn_number"] = turn
            for _ in range(3):  # a few attacks a turn, each way, and a climax now and then
                game.record_hit(state, "2", 3 + turn % 4, cancelled=turn % 5 == 0)
                game.record_hit(state, "1", 1 + turn % 3, cancelled=False)
            if turn % 6 == 0:
                game.record_climax(state, "1")
        facts = json.dumps(state["timeline_facts"], separators=(",", ":"))
        self.assertLess(len(facts), 2048)
        self.assertLessEqual(len(state["timeline_facts"]["attacks"]), game.FACT_LIMIT)

    def test_the_facts_are_capped_so_a_long_game_stays_small(self):
        state = {"order": ["1", "2"], "turn_number": 1, "players": {}}
        for _ in range(game.FACT_LIMIT + 50):
            game.record_hit(state, "2", 1, cancelled=False)
        self.assertEqual(len(state["timeline_facts"]["attacks"]), game.FACT_LIMIT)


class RecapViewTests(TestCase):
    RECAP = {"points": [[1, 0, 7], [2, 3, 14]], "moments": [{"kind": "comeback", "turn": 2, "side": "guest", "n": 11}]}

    def test_each_seat_sees_its_own_column_first(self):
        host = play.duel_recap_view(self.RECAP, "host", {"host": "Ann", "guest": "Ben"})
        guest = play.duel_recap_view(self.RECAP, "guest", {"host": "Ann", "guest": "Ben"})
        self.assertEqual(host["points"], [[1, 0, 7], [2, 3, 14]])
        self.assertEqual(guest["points"], [[1, 7, 0], [2, 14, 3]])
        self.assertEqual((host["me"], host["them"], guest["me"], guest["them"]), ("Ann", "Ben", "Ben", "Ann"))

    def test_a_moment_is_the_you_caption_when_the_viewer_did_it(self):
        lines = {"comeback": {"you": "You clawed back, {name} fell {n} down.", "them": "{name} clawed back from {n} points down."}}
        with mock.patch("weiss.play.RECAP_LINES", lines):
            guest = play.duel_recap_view(self.RECAP, "guest", {"host": "Ann", "guest": "Ben"})
            host = play.duel_recap_view(self.RECAP, "host", {"host": "Ann", "guest": "Ben"})
        self.assertEqual(guest["moments"], ["You clawed back, Ann fell 11 down."])
        self.assertEqual(host["moments"], ["Ben clawed back from 11 points down."])

    def test_no_points_means_no_recap_view(self):
        self.assertIsNone(play.duel_recap_view({}, "host", {"host": "Ann", "guest": "Ben"}))
        self.assertIsNone(play.duel_recap_view(None, "host", {"host": "Ann", "guest": "Ben"}))
        self.assertIsNone(play.duel_recap_view({"points": [], "moments": []}, "host", {"host": "Ann", "guest": "Ben"}))

    def test_a_kind_without_a_caption_is_left_out(self):
        with mock.patch("weiss.play.RECAP_LINES", {}):
            view = play.duel_recap_view(self.RECAP, "host", {"host": "Ann", "guest": "Ben"})
        self.assertEqual(view["moments"], [])


class RecordedRecapTests(TestCase):
    """A finished game's recap is kept on its record, and the game-over payload carries it for each player."""

    def setUp(self):
        test_world.DuelTests.setUp(self)  # a town save (its tests aren't run again here)

    def finished_game(self, winner):
        other = User.objects.create_user("opponent", password="x")
        state = game.new_game([(self.user.pk, self.user.username, []), (other.pk, other.username, [])])
        state["timeline"] = {"points": [{"turn": 1, "by": str(self.user.pk), "damage": {str(self.user.pk): 0, str(other.pk): 7}}],
                             "hits": []}
        state["turn_number"] = 1
        game.end_game(state, str(self.user.pk) if winner == "guest" else str(other.pk), "level", "lost")
        state["timeline"]["points"][-1]["damage"] = {str(self.user.pk): 0, str(other.pk): 7}  # the loser's 7 points, as the game ended with them
        state["game_over"]["recap"] = game.duel_recap(state)
        room = GameRoom.objects.create(host=self.user, guest=other, status=GameRoom.Status.PLAYING, state=state)
        return room, other

    def test_the_record_keeps_the_recap(self):
        room, other = self.finished_game(winner="host")
        play.record_game(room, room.state["game_over"])
        record = GameRecord.objects.get()
        self.assertEqual(record.recap["points"], [[1, 0, 7]])
        self.assertEqual(record.winner, "host")  # this user (the host) won: the other player lost on level

    def test_the_game_over_payload_has_the_recap_from_the_players_seat(self):
        room, other = self.finished_game(winner="host")
        board = play.board_payload(room, self.user)["board"]
        self.assertEqual(board["game_over"]["recap"]["points"], [[1, 0, 7]])
        self.assertEqual(board["game_over"]["recap"]["me"], self.user.username)
        board = play.board_payload(room, other)["board"]
        self.assertEqual(board["game_over"]["recap"]["points"], [[1, 7, 0]])

    def test_a_game_still_going_has_no_recap_in_its_payload(self):
        room = GameRoom.objects.create(host=self.user, guest=staff_user("other"), status=GameRoom.Status.PLAYING,
                                       state=game.new_game([(self.user.pk, self.user.username, []), (self.user.pk + 999, "other", [])]))
        self.assertNotIn("recap", (play.board_payload(room, self.user)["board"].get("game_over") or {}))

    def test_the_profile_gives_each_recent_game_its_recap_view(self):
        room, other = self.finished_game(winner="host")
        play.record_game(room, room.state["game_over"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("weiss:profile"))
        record = response.context["records"][0]
        self.assertEqual(record.recap_view["points"], [[1, 0, 7]])


class HistoryLineTests(TestCase):
    """The duel's intro remembers the player: the milestone, streak and 50% rules (docs/round-two-plan.md, section 2)."""

    def setUp(self):
        test_world.DuelTests.setUp(self)
        self.records = []

    def record(self, winner):
        """A town duel's record with Cinder (the player is always the host there)."""
        other = self.cinder
        self.records.append(GameRecord.objects.create(host=self.user, guest=None, host_name=self.user.username, guest_name=other.name,
                                                      cpu=True, cpu_profile=other, winner=winner))

    def record_results(self, results):
        for winner in reversed(results):  # oldest first, so the newest is the last one saved
            self.record(winner)

    def intro(self, rng_value=0.0):
        with mock.patch("weiss.world.random.random", return_value=rng_value):
            return world.duel_intro(self.save, self.cinder)

    def test_a_first_duel_has_no_history_line(self):
        self.assertIsNone(world.history_line(self.user, self.cinder, self.save))

    def test_the_tenth_duel_is_a_milestone_with_its_count(self):
        self.record_results(["host"] * 9)
        with mock.patch("weiss.chatter.reaction_lines", return_value=[("main", "Ten! {count} duels now, {player}.")]):
            self.assertEqual(self.intro(), f"Ten! 10 duels now, {self.user.username}.")

    def test_a_streak_of_three_wins_is_said_with_its_count(self):
        self.record_results(["host", "host", "host", "guest"])  # newest first: three wins, then a loss
        with mock.patch("weiss.chatter.reaction_lines", return_value=[("main", "{count} in a row!")]) as lines:
            self.assertEqual(self.intro(), "3 in a row!")
        self.assertEqual(lines.call_args.args[1], "history_streak_won")

    def test_a_streak_of_three_losses_is_its_own_context(self):
        self.record_results(["guest", "guest", "guest", "host"])
        with mock.patch("weiss.chatter.reaction_lines", return_value=[("main", "{count} losses.")]) as lines:
            self.assertEqual(self.intro(), "3 losses.")
        self.assertEqual(lines.call_args.args[1], "history_streak_lost")

    def test_a_short_streak_is_not_a_streak(self):
        self.record_results(["guest", "host"])  # newest first: a loss, then a win: no streak, so revenge, on the coin flip
        with mock.patch("weiss.chatter.reaction_lines", return_value=[("main", "Revenge.")]) as lines:
            self.assertEqual(self.intro(0.1), "Revenge.")
        self.assertEqual(lines.call_args.args[1], "history_revenge")

    def test_a_lost_last_duel_is_revenge_on_the_coin_flip(self):
        self.record_results(["guest"])
        with mock.patch("weiss.chatter.reaction_lines", return_value=[("main", "Revenge.")]):
            self.assertEqual(self.intro(0.3), "Revenge.")
            self.assertEqual(self.intro(0.7), self.intro(0.7))  # the flip failed: the usual line, each time
        self.assertNotIn("Revenge.", self.intro(0.7))

    def test_a_won_last_duel_is_a_rematch_on_the_coin_flip(self):
        self.record_results(["host"])
        with mock.patch("weiss.chatter.reaction_lines", return_value=[("main", "Rematch!")]) as lines:
            self.assertEqual(self.intro(0.2), "Rematch!")
        self.assertEqual(lines.call_args.args[1], "history_rematch_won")

    def test_a_cpu_with_no_line_for_the_rule_gets_the_usual_line(self):
        self.record_results(["guest"])
        with mock.patch("weiss.chatter.reaction_lines", return_value=[]):
            self.assertNotEqual(self.intro(0.1), "")

    def test_the_cpus_own_line_comes_first(self):
        Chatter.objects.create(cpu=self.cinder, context="history_revenge", min_rank=0, script="them: Mine, that revenge line.")
        self.record_results(["guest"])
        self.assertEqual(self.intro(0.1), "Mine, that revenge line.")

    def test_the_history_is_one_query_when_a_duel_starts(self):
        self.record_results(["host", "guest", "host"])
        with CaptureQueriesContext(connection) as queries:
            self.intro(0.1)
        records = [q["sql"] for q in queries.captured_queries if "weiss_gamerecord" in q["sql"]]
        self.assertEqual(len(records), 1)

    def test_a_duel_with_no_history_is_not_affected(self):
        self.assertIsNone(world.history_line(self.user, self.cinder, self.save))


class JournalTests(TestCase):
    """The people journal (docs/round-two-plan.md, section 4): who's met, the record, the gifts taken, the quests and the
    journal entries that unlock with rank."""

    def setUp(self):
        test_world.DuelTests.setUp(self)
        self.cinder.gift_tastes = {"loves": ["sweet"], "dislikes": ["bitter"]}
        self.cinder.save(update_fields=["gift_tastes"])
        self.sweet = GiftItem.objects.create(key="sweet-bun", name="Sweet bun", tags=["sweet"])
        self.bitter = GiftItem.objects.create(key="bitter-tea", name="Bitter tea", tags=["bitter"])
        Chatter.objects.create(cpu=self.cinder, context="journal", min_rank=0, script="narrator: She drinks tea at the café.")
        Chatter.objects.create(cpu=self.cinder, context="journal", min_rank=2, script="narrator: She's quieter with friends.")

    def meet(self):
        """The player has met this CPU in full (their relation is saved)."""
        world.relation(self.save, self.cinder.pk)
        world.changed(self.save, "relations")

    def journal(self):
        self.save.refresh_from_db()
        self.save.__dict__.pop("_quests", None)
        return world_people.people(self.save)

    def test_the_met_count_and_the_unmet_have_no_name(self):
        self.meet()
        journal = self.journal()
        self.assertEqual((journal["met_count"], journal["total"]), (1, CpuProfile.objects.filter(finalized=True).count()))
        self.assertTrue(all(set(entry) == {"id"} for entry in journal["unmet"]))

    def test_a_met_person_has_rank_progress_and_their_colours(self):
        self.meet()
        person = self.journal()["met"][0]
        self.assertEqual((person["name"], person["rank"], person["progress"]), ("Cinder", 0, 0.0))
        self.assertIsNotNone(person["next_rank_name"])
        self.assertEqual(person["colors"], play.deck_colors(self.cinder.deck))

    def test_the_record_is_the_wins_and_losses_in_town_duels(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        person = self.journal()["met"][0]
        self.assertEqual(person["record"], {"won": 1, "lost": 0})

    def test_gifts_are_listed_as_the_player_saw_them_taken(self):
        self.save.gifts = {"sweet-bun": 1, "bitter-tea": 1}
        self.save.save(update_fields=["gifts"])
        world.give(self.save, self.cinder.pk, "sweet-bun")
        person = self.journal()["met"][0]
        self.assertEqual(person["tastes"]["loved"], ["Sweet bun"])
        self.assertEqual(person["tastes"]["disliked"], [])  # only what the player has given

    def test_the_entries_unlock_with_rank(self):
        self.meet()
        entries = self.journal()["met"][0]["entries"]
        self.assertEqual([entry["unlocked"] for entry in entries], [True, False])
        self.assertEqual(entries[0]["text"], "She drinks tea at the café.")
        self.assertEqual(entries[1]["text"], "")  # a locked entry has no text
        self.assertTrue(entries[1]["rank_name"])

    def test_a_cpu_with_no_journal_has_no_entries(self):
        Chatter.objects.filter(cpu=self.cinder, context="journal").delete()
        self.meet()
        self.assertEqual(self.journal()["met"][0]["entries"], [])

    def test_the_quests_they_give_show_their_status(self):
        from .test_world_quests import make_quest, stage

        make_quest("tea", self.cinder, stages=[stage({"do": "flag", "flag": "tea_done", "text": "Find the tea"})])
        world.quest_act(self.save, self.cinder.pk, "accept", "tea", {})
        self.meet()
        self.assertEqual(self.journal()["met"][0]["quests"], [{"title": "Tea", "status": "active"}])

    def test_the_journal_page_opens_one_person_and_is_framed_same_origin(self):
        self.meet()
        self.client.force_login(self.user)
        with mock.patch("weiss.world_views.render", return_value=HttpResponse("ok")) as render:
            response = self.client.get(reverse("weiss:world_people", args=[self.save.slot]) + f"?cpu={self.cinder.pk}")
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        context = render.call_args.args[2]
        self.assertEqual(context["chosen"]["name"], "Cinder")
        self.assertEqual(context["journal"]["met_count"], 1)

    def finish(self, room, won):
        over = {"winner": str(room.host_id if won else room.guest_id), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over
        room.save(update_fields=["state"])
        world.game_finished(room, over)


class JournalPackTests(TestCase):
    def test_the_pack_builder_exports_history_and_journal_lines(self):
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location("build", Path(__file__).resolve().parent.parent / "world_pack" / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        cpu = build.cpu("Test", "Quiet.", [], ([], [], []),
                        {"hi": ["Hi."], "history": {"milestone": ["Ten, {player}."], "revenge": ["Next time."]},
                         "journal": {"0": "A note.", "4": "A closer note."}},
                        friend=["me: Hi."], best=["me: Hi."])
        chatter = build.entry(cpu)["world"]["chatter"]
        history = sorted((row["context"], row["script"][0]) for row in chatter if row["context"].startswith("history_"))
        self.assertEqual(history, [("history_milestone", "Ten, {player}."), ("history_revenge", "Next time.")])
        journal = sorted((row["min_rank"], row["script"][0]) for row in chatter if row["context"] == "journal")
        self.assertEqual(journal, [(0, "narrator: A note."), (4, "narrator: A closer note.")])

    def test_the_checker_accepts_history_and_journal_lines(self):
        import json
        from pathlib import Path

        from .cpu_corpus import import_world_pack

        pack = json.loads((Path(__file__).resolve().parent.parent / "world_pack" / "01_avatar_gurren.json").read_text(encoding="utf-8"))
        for cpu in pack["cpus"]:
            cpu["world"]["chatter"].append({"context": "history_streak_won", "min_rank": 0, "script": ["them: Three in a row."]})
            cpu["world"]["chatter"].append({"context": "journal", "min_rank": 0, "script": ["narrator: A note about them."]})
        results = import_world_pack([pack], dry_run=True, known=[cpu["name"] for cpu in pack["cpus"]])
        self.assertEqual([problem for problem in results[0].problems if "history" in problem or "journal" in problem], [])


class FreeHistoryTests(TestCase):
    """A history line also opens the free duels and arcade fights (any room with a CPU, not in narrative challenges): rank 0,
    the any-CPU and default lines, picked when the game is seated and kept for its rematches."""

    def setUp(self):
        test_world.DuelTests.setUp(self)
        self.others = User.objects.create_user("opponent", password="x")

    def record(self, winner):
        GameRecord.objects.create(host=self.user, guest=self.others, host_name=self.user.username, guest_name="x",
                                  cpu=True, cpu_profile=self.cinder, winner=winner)

    def seated(self):
        room = GameRoom(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING)
        play.seat_cpu(room, self.cinder)
        room.save()
        return room

    def test_a_free_duel_opens_with_a_line_that_remembers_the_player(self):
        for winner in ("host", "host", "host"):
            self.record(winner)
        Chatter.objects.create(cpu=None, context="history_streak_won", min_rank=0, script="them: {count} in a row, {player}!")
        room = self.seated()
        self.assertEqual(play.cpu_payload(room)["cpu"]["intro"], f"3 in a row, {self.user.username}!")

    def test_a_free_duel_uses_only_the_any_cpu_lines(self):
        self.record("host")
        self.record("host")
        self.record("host")
        Chatter.objects.create(cpu=self.cinder, context="history_streak_won", min_rank=0, script="them: Only Cinder says this.")
        Chatter.objects.create(cpu=None, context="history_streak_won", min_rank=0, script="them: Any CPU says this, {count}.")
        room = self.seated()
        self.assertEqual(play.cpu_payload(room)["cpu"]["intro"], "Any CPU says this, 3.")

    def test_a_free_duel_with_no_history_keeps_its_own_intro(self):
        room = self.seated()
        self.assertNotIn("intro", room.state)
        self.assertEqual(play.cpu_payload(room)["cpu"]["intro"], self.cinder.intro_text)

    def test_a_rematch_keeps_the_line_picked_for_game_one(self):
        for winner in ("host", "host", "host"):
            self.record(winner)
        Chatter.objects.create(cpu=None, context="history_streak_won", min_rank=0, script="them: Streak {count}.")
        room = self.seated()
        first = play.cpu_payload(room)["cpu"]["intro"]
        self.record("guest")  # the history changed in the meantime: a rematch still keeps game one's line
        play.deal(room, intro=True)
        room.save()
        self.assertEqual(play.cpu_payload(GameRoom.objects.get(pk=room.pk))["cpu"]["intro"], first)

    def test_a_narrative_challenge_gets_no_history_line(self):
        for winner in ("host", "host", "host"):
            self.record(winner)
        Chatter.objects.create(cpu=None, context="history_streak_won", min_rank=0, script="them: Streak {count}.")
        room = GameRoom(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING)
        with mock.patch("weiss.challenge.narrative", return_value=True):
            play.seat_cpu(room, self.cinder)
            room.save()
            payload = play.cpu_payload(room)
        self.assertNotIn("intro", room.state)
        self.assertEqual(payload["cpu"]["intro"], "")


class JournalQueryTests(TestCase):
    """The people journal is built in batches: its queries don't grow with the number of people in it."""

    def setUp(self):
        test_world.DuelTests.setUp(self)

    def meet_many(self, count):
        for n in range(count):
            cpu = test_world.give_cpu(f"Friend {n:02}", self.cards)
            test_world.everywhere_rule(cpu)
            world.relation(self.save, cpu.pk)["points"] = 40
            Chatter.objects.create(cpu=cpu, context="journal", min_rank=0, script=f"narrator: A note on {n}.")
            Chatter.objects.create(cpu=cpu, context="journal", min_rank=2, script=f"narrator: A closer note on {n}.")
        world.changed(self.save, "relations")

    def queries_for(self):
        self.save.refresh_from_db()
        self.save.__dict__.pop("_quests", None)
        with CaptureQueriesContext(connection) as queries:
            world_people.people(self.save)
        return len(queries.captured_queries)

    def test_the_query_count_stays_flat_as_people_are_added(self):
        self.meet_many(3)
        few = self.queries_for()
        self.meet_many(7)  # ten people in all
        many = self.queries_for()
        self.assertEqual(few, many)

    def test_the_cast_is_the_town_cast(self):
        self.meet_many(2)
        self.save.refresh_from_db()
        journal = world_people.people(self.save)
        self.assertEqual(journal["total"], world.town_cast().count())
        self.assertEqual(journal["met_count"], 2)


class CpuNoActionWarningTests(TestCase):
    """A CPU turn with nothing for the CPU to do logs a warning with its phase and what's pending (a stall's trace), and
    doesn't change what happens."""

    def setUp(self):
        test_world.DuelTests.setUp(self)

    def cpu_turn_room(self):
        room = GameRoom(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING)
        play.seat_cpu(room, self.cinder)
        room.save()
        room.state.pop("cpu_intro", None)
        room.state["scenes"] = []
        room.state["rps"] = None
        room.state["turn"] = str(room.guest_id)  # the CPU's turn
        room.state["phase"] = "clock"
        room.save(update_fields=["state"])
        return room

    def test_a_cpu_turn_with_no_action_logs_a_warning_with_its_phase(self):
        room = self.cpu_turn_room()
        with mock.patch("weiss.cpu.next_action", return_value=None), mock.patch("weiss.cpu.fallback_action", return_value=None):
            with self.assertLogs("weiss.play", level="WARNING") as logs:
                play.cpu_move(room, wait=False)
        self.assertIn(f"CPU {self.cinder.name} in room {room.pk} has no action on its own turn: phase clock", logs.output[0])

    def test_no_warning_on_the_players_turn(self):
        room = self.cpu_turn_room()
        room.state["turn"] = str(room.host_id)
        room.save(update_fields=["state"])
        with mock.patch("weiss.cpu.next_action", return_value=None):
            with self.assertNoLogs("weiss.play", level="WARNING"):
                play.cpu_move(room, wait=False)

    def test_the_warning_changes_nothing_about_the_move(self):
        room = self.cpu_turn_room()
        before = json.dumps(room.state, sort_keys=True, default=str)
        with mock.patch("weiss.cpu.next_action", return_value=None), mock.patch("weiss.cpu.fallback_action", return_value=None):
            with self.assertLogs("weiss.play", level="WARNING"):
                play.cpu_move(room, wait=False)
        self.assertEqual(json.dumps(GameRoom.objects.get(pk=room.pk).state, sort_keys=True, default=str), before)
