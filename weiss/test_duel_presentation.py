"""The duel presentation's server side (docs/duel-presentation-plan.md): the versus intro's data, the reactions the CPU
says in a duel, and the results ceremony's data in a town duel's last_duel."""
from unittest import mock

from django.test import TestCase

from . import chatter, play, test_world, world
from .models import Chatter, CpuProfile, GameRoom, PlayerProfile
from .test_world import give_cpu


class PresentationBase(TestCase):
    """A town duel's setup (the duel tests' save and CPU), without their tests."""

    def setUp(self):
        test_world.DuelTests.setUp(self)

    def duel(self):
        return world.start_duel(self.save, self.cinder.pk)

    def payload(self, room):
        return play.cpu_payload(GameRoom.objects.get(pk=room.pk))

    def fresh(self):
        self.save.refresh_from_db()
        self.save.__dict__.pop("_quests", None)
        return self.save

    def finish(self, room, won):
        over = {"winner": str(room.host_id if won else room.guest_id), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over
        room.save(update_fields=["state"])
        world.game_finished(room, over)
        return self.fresh()


class VersusTests(PresentationBase):
    def test_a_friendly_town_duel_has_both_sides_and_a_friendly_ribbon(self):
        room = self.duel()
        versus = self.payload(room)["versus"]
        self.assertEqual(versus["me"]["name"], self.user.username)
        self.assertIsNone(versus["me"]["picture"])
        self.assertEqual(versus["me"]["deck"], self.save.deck.name)
        self.assertEqual(versus["them"]["name"], "Cinder")
        self.assertEqual(versus["them"]["deck"], self.cinder.deck.name)
        self.assertEqual(versus["them"]["title"], world.rank_names()[world.rank_of(self.save, self.cinder.pk)])
        self.assertEqual(versus["ribbon"], {"kind": "friendly", "text": "A friendly duel"})

    def test_colours_are_the_decks_most_common_two(self):
        counts = {}
        for i, entry in enumerate(self.save.deck.entries.select_related("card")):
            entry.card.color = ("Red", "Blue", "Green")[i % 3]  # three colours, so the top two are told apart by count
            entry.card.save(update_fields=["color"])
            counts[entry.card.color] = counts.get(entry.card.color, 0) + entry.quantity
        expected = sorted(counts, key=lambda color: -counts[color])[:2]
        room = self.duel()
        self.assertEqual(self.payload(room)["versus"]["me"]["colors"], expected)
        self.assertEqual(play.deck_colors(None), [])

    def test_high_stakes_is_the_ribbon_when_no_tournament_or_quest_is_on(self):
        self.save.money = 10_000
        self.save.save(update_fields=["money"])
        room = world.start_duel(self.save, self.cinder.pk, high_stakes=True)
        self.assertEqual(self.payload(room)["versus"]["ribbon"]["kind"], "stakes")

    def test_a_tournament_round_beats_a_quest(self):
        room = self.duel()
        with mock.patch("weiss.world_events.round_label", return_value="Semi-final"), \
                mock.patch("weiss.quests.duel_quest", return_value="Beat Cinder"):
            ribbon = world.duel_ribbon(self.save, room, self.cinder)
        self.assertEqual(ribbon["kind"], "tournament")

    def test_a_quest_duel_beats_high_stakes(self):
        room = self.duel()
        room.world_stake = 500
        with mock.patch("weiss.quests.duel_quest", return_value="Beat Cinder"):
            ribbon = world.duel_ribbon(self.save, room, self.cinder)
        self.assertEqual(ribbon, {"kind": "quest", "text": "Quest · Beat Cinder"})

    def test_the_intro_line_is_picked_once_and_stays_the_same_across_polls(self):
        room = self.duel()
        with mock.patch("weiss.world.duel_intro", return_value="SHOULD NOT BE USED"):
            first = self.payload(room)["cpu"]["intro"]
            second = self.payload(room)["cpu"]["intro"]
        self.assertEqual(first, second)
        self.assertEqual(GameRoom.objects.get(pk=room.pk).state["intro"], first)
        self.assertNotIn("SHOULD", first)

    def test_a_deleted_cpu_has_a_versus_with_no_picture_or_deck(self):
        room = GameRoom.objects.create(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING,
                                       cpu_name="Gone", cpu_profile=None)  # the CPU was deleted before the game
        versus = play.cpu_payload(room)["versus"]
        self.assertEqual(versus["them"]["name"], "Gone")  # the name the room kept
        self.assertIsNone(versus["them"]["picture"])
        self.assertEqual((versus["them"]["image"], versus["them"]["deck"], versus["them"]["colors"]), ("", "", []))
        self.assertIsNone(versus["ribbon"])  # no CPU to say what it stakes

    def test_the_host_has_their_own_picture_when_they_have_an_avatar(self):
        PlayerProfile.objects.create(user=self.user, avatar_card=self.cards[0])
        room = self.duel()
        picture = self.payload(room)["versus"]["me"]["picture"]
        self.assertIsNotNone(picture)
        self.assertIn("image", picture)

    def test_a_non_world_cpu_duel_has_generic_sides_and_no_ribbon(self):
        room = GameRoom.objects.create(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING,
                                       cpu_name=self.cinder.name, cpu_profile=self.cinder)
        self.assertIsNone(room.world_save)
        versus = play.cpu_payload(room)["versus"]
        self.assertIsNone(versus["ribbon"])
        self.assertEqual(versus["them"]["title"], "")
        self.assertEqual(versus["them"]["name"], "Cinder")


class ReactionTests(PresentationBase):
    def texts(self, room, context):
        return [line["text"] for line in self.payload(room)["cpu"]["reactions"][context]]

    def test_every_reaction_context_is_sent(self):
        room = self.duel()
        self.assertEqual(set(self.payload(room)["cpu"]["reactions"]), set(chatter.DUEL_CONTEXTS))

    def test_a_rank_two_friend_hears_both_tiers(self):
        with mock.patch("weiss.world.rank_of", return_value=2):  # the rank the duel is started at
            room = self.duel()
        texts = self.texts(room, "duel_hurt")
        self.assertIn("That one stung.", texts)  # the rank-0 line
        self.assertIn(f"{self.user.username}! You could have warned me.", texts)  # the rank-2 line, filled in

    def test_a_stranger_hears_only_the_base_tier(self):
        room = self.duel()
        texts = self.texts(room, "duel_hurt")
        self.assertIn("That one stung.", texts)
        self.assertNotIn(f"{self.user.username}! You could have warned me.", texts)

    def test_the_cpus_own_lines_replace_the_defaults_in_town(self):
        Chatter.objects.create(cpu=self.cinder, context="duel_hurt", min_rank=0, script="them: Ouch, that's mine.")
        room = self.duel()
        self.assertEqual(self.texts(room, "duel_hurt"), ["Ouch, that's mine."])

    def test_outside_town_only_the_generic_lines_are_used(self):
        Chatter.objects.create(cpu=self.cinder, context="duel_hurt", min_rank=0, script="them: Ouch, that's mine.")
        room = GameRoom.objects.create(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING,
                                       cpu_name=self.cinder.name, cpu_profile=self.cinder)
        texts = self.texts(room, "duel_hurt")
        self.assertNotIn("Ouch, that's mine.", texts)
        self.assertIn("That one stung.", texts)

    def test_a_narrative_challenge_has_no_reactions(self):
        room = GameRoom(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING)
        with mock.patch("weiss.challenge.narrative", return_value=True):
            play.seat_cpu(room, self.cinder)  # a narrative fight is seated and dealt as one
            room.save()
            payload = play.cpu_payload(room)
        self.assertEqual(payload["cpu"]["reactions"], {})

    def test_the_presentation_is_worked_out_once_per_game_not_per_poll(self):
        room = self.duel()
        self.assertIn("presentation", GameRoom.objects.get(pk=room.pk).state)
        with mock.patch("weiss.play.versus") as versus, mock.patch("weiss.play.reactions") as reactions,                 mock.patch("weiss.chatter.reaction_lines") as lines:
            self.payload(room)
            self.payload(room)
        versus.assert_not_called()
        reactions.assert_not_called()
        lines.assert_not_called()

    def test_a_room_dealt_before_it_was_stored_still_gets_its_presentation_without_saving(self):
        room = self.duel()
        GameRoom.objects.filter(pk=room.pk).update(state={k: v for k, v in GameRoom.objects.get(pk=room.pk).state.items() if k != "presentation"})
        payload = self.payload(room)
        self.assertIn("duel_hurt", payload["cpu"]["reactions"])
        self.assertNotIn("presentation", GameRoom.objects.get(pk=room.pk).state)  # not written from the read path

    def test_a_deleted_cpu_has_no_reactions(self):
        room = GameRoom.objects.create(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING,
                                       cpu_name="Gone", cpu_profile=None)
        self.assertEqual(play.cpu_payload(room)["cpu"]["reactions"], {})


class PackTests(TestCase):
    """A pack's duel lines are accepted by the import (the same check as manage.py check_world_pack)."""

    def test_the_pack_builder_exports_the_duel_lines_as_chatter(self):
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location("build", Path(__file__).resolve().parent.parent / "world_pack" / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        cpu = build.cpu("Test", "Quiet.", [], ([], [], []), {"hi": ["Hi."], "duel": {"hurt": ["them: Ouch."], "winning": ["them: Oh no."]}},
                        friend=["me: Hi."], best=["me: Hi."])
        chatter = build.entry(cpu)["world"]["chatter"]
        duel = [(row["context"], row["script"]) for row in chatter if row["context"].startswith("duel_")]
        self.assertEqual(duel, [("duel_hurt", ["them: Ouch."]), ("duel_winning", ["them: Oh no."])])

    def test_the_checker_accepts_duel_lines_in_a_pack(self):
        import json
        from pathlib import Path

        from .cpu_corpus import import_world_pack

        pack = json.loads((Path(__file__).resolve().parent.parent / "world_pack" / "01_avatar_gurren.json").read_text(encoding="utf-8"))
        for cpu in pack["cpus"]:
            cpu["world"]["chatter"].append({"context": "duel_cancel", "min_rank": 0, "script": ["them (pleased): Not today."]})
            cpu["world"]["chatter"].append({"context": "duel_level", "min_rank": 0, "script": ["them: Level up."]})
        results = import_world_pack([pack], dry_run=True, known=[cpu["name"] for cpu in pack["cpus"]])
        # Checked alone, a pack's scenes name CPUs from the others, so only the duel lines' own problems count here.
        self.assertEqual([problem for problem in results[0].problems if "duel_" in problem], [])

    def test_the_checker_rejects_a_duel_line_in_an_unknown_context(self):
        import json
        from pathlib import Path

        from .cpu_corpus import import_world_pack

        pack = json.loads((Path(__file__).resolve().parent.parent / "world_pack" / "01_avatar_gurren.json").read_text(encoding="utf-8"))
        for cpu in pack["cpus"]:
            cpu["world"]["chatter"].append({"context": "duel_nope", "min_rank": 0, "script": ["them: Hm."]})
        results = import_world_pack([pack], dry_run=True, known=[cpu["name"] for cpu in pack["cpus"]])
        self.assertTrue(any("the context must be one of" in problem for problem in results[0].problems))  # the checker's wording


class CeremonyTests(PresentationBase):
    """A town duel's results ceremony data in flags["last_duel"] (docs/duel-presentation-plan.md, section 3)."""

    def test_a_won_duel_has_the_friend_bar_the_cpu_line_and_no_quest_words(self):
        save = self.finish(self.duel(), won=True)
        last = save.flags["last_duel"]
        self.assertEqual(set(last["friend"]), {"before", "after", "from", "to"})
        self.assertEqual(last["friend"]["before"], last["friend"]["after"])  # no rank reached
        self.assertLessEqual(last["friend"]["from"], last["friend"]["to"])
        self.assertIsInstance(last["cpu_line"], str)
        self.assertEqual(last["quests"], [])

    def test_a_rank_reached_fills_the_bar_and_names_the_new_rank(self):
        rows = world.ranks()
        before = world.friend_progress(rows[1]["points"] - 1, rows[1]["points"])
        self.assertEqual((before["before"], before["after"]), (rows[0]["name"], rows[1]["name"]))
        self.assertEqual(before["to"], 1.0)  # a rank up ends at the end of the rank before
        self.assertLess(before["from"], 1.0)

    def test_the_top_rank_fills_the_bar(self):
        top = world.ranks()[-1]["points"]
        bar = world.friend_progress(top, top + 10)
        self.assertEqual((bar["from"], bar["to"]), (1.0, 1.0))

    def test_a_share_is_the_way_through_the_rank_before(self):
        rows = world.ranks()
        halfway = (rows[0]["points"] + rows[1]["points"]) // 2
        bar = world.friend_progress(rows[0]["points"], halfway)
        self.assertEqual((bar["before"], bar["after"]), (rows[0]["name"], rows[0]["name"]))
        self.assertAlmostEqual(bar["to"], 0.5, delta=0.05)

    def test_a_quest_the_duel_moved_on_is_said_in_words_with_its_count(self):
        from .test_world_quests import make_quest, stage

        give_cpu("Ruby", self.cards)  # the quest's second CPU, not yet beaten
        make_quest("pair", self.cinder, stages=[stage({"do": "defeat", "cpus": ["Cinder", "Ruby"]})])
        world.quest_act(self.save, self.cinder.pk, "accept", "pair", {})
        room = self.duel()
        save = self.finish(room, won=True)
        self.assertEqual(save.flags["last_duel"]["quests"], [{"text": mock.ANY, "done": False, "n": 1, "total": 2}])

    def test_a_deleted_cpu_has_no_friend_bar_or_line(self):
        room = self.duel()
        CpuProfile.objects.filter(pk=self.cinder.pk).delete()
        save = self.finish(room, won=True)
        self.assertIsNone(save.flags["last_duel"]["friend"])
        self.assertEqual(save.flags["last_duel"]["cpu_line"], "")


class CardPickFlagTests(PresentationBase):
    """last_duel's card_pick: True when a win made a card pick offer for this game, False otherwise."""

    def test_a_win_offers_a_card_pick(self):
        self.assertTrue(self.finish(self.duel(), won=True).flags["last_duel"]["card_pick"])

    def test_a_loss_offers_no_card_pick(self):
        self.assertFalse(self.finish(self.duel(), won=False).flags["last_duel"]["card_pick"])

    def test_a_win_against_a_cpu_with_no_cards_offers_no_card_pick(self):
        room = self.duel()
        with mock.patch("weiss.world.deck_cards", return_value=[]):
            save = self.finish(room, won=True)
        self.assertFalse(save.flags["last_duel"]["card_pick"])
        self.assertNotIn("card_pick", save.flags)
