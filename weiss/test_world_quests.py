"""World mode's quests: checking them, gating ranks, objectives, endings and what they close."""
from django.test import TestCase
from django.urls import reverse

from . import game, quests, world
from .models import CardList, Chatter, GameRoom, GiftItem, Quest, Scene, WorldPlace, WorldSettings
from .test_world import SET, everywhere_rule, give_cpu, make_set, staff_user


def stage(*objectives, text="Do it"):
    return {"text": text, "objectives": list(objectives)}


def make_quest(key, giver=None, gates=None, stages=None, endings=None, **spec):
    """A quest, checked as staff and files would write it."""
    data = {"key": key, "title": spec.pop("title", key.title()), "about": spec.pop("about", "Something to do."),
            "stages": stages or [stage({"do": "flag", "flag": f"{key}_done", "text": "Do the thing"})],
            "endings": endings or [{"key": "end", "title": "Finish"}], **spec}
    if giver:
        data["giver"] = giver.name
    if gates:
        data["gates"] = gates
    fields, problems = quests.check(data)
    assert not problems, problems
    return quests.save_quest(fields)


class QuestBase(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.save.pool = {str(c.pk): 4 for c in self.cards}
        self.save.packs, self.save.rewards = 0, []
        self.save.save()
        climaxes = [c for c in self.cards if c.card_type == "Climax"][:2]
        others = [c for c in self.cards if c.card_type != "Climax"][:14]
        world.save_deck(self.save, {c.pk: 4 for c in climaxes} | {c.pk: 3 for c in others})
        WorldSettings.objects.update_or_create(pk=1, defaults={"win_payout": 200, "first_win_bonus": 100})
        self.ruby = give_cpu("Ruby", self.cards)
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.ruby)
        everywhere_rule(self.cinder)

    def fresh(self):
        """The save as the database has it, as a new request would."""
        self.save.refresh_from_db()
        for attr in ("_quests", "_quest_lookup"):
            self.save.__dict__.pop(attr, None)
        return self.save

    def points(self, cpu, n):
        world.relation(self.save, cpu.pk)["points"] = n
        world.changed(self.save, "relations")
        return self.fresh()

    def duel(self, cpu, won, records=None, stake=0):
        room = GameRoom.objects.create(host=self.user, host_deck=self.save.deck, status=GameRoom.Status.PLAYING, world_save=self.save,
                                       cpu_name=cpu.name, cpu_profile=cpu, world_stake=stake)
        quests.duel_started(self.save, room)
        world.changed(self.save, "quests")
        room.state = {"records": {str(self.user.pk): records or {}}}
        over = {"winner": str(self.user.pk if won else 0), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over
        room.save()
        world.game_finished(room, over)
        return self.fresh()


class CheckTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.ruby = give_cpu("Ruby", self.cards)

    def test_a_good_quest_has_no_problems(self):
        fields, problems = quests.check({
            "key": "ember", "title": "Ember", "giver": "ruby", "gates": 2, "about": "A test.",
            "offer": ["them: Help me?"],
            "stages": [stage({"do": "defeat", "cpus": ["Ruby"]}, {"do": "have_card", "card": self.cards[0].serial_number, "copies": 2}),
                       stage({"do": "talk", "to": "Ruby", "script": ["them: Thanks.", "choice Well?", "- Sure -> x (set yes)", "label x"]})],
            "endings": [{"key": "a", "title": "Ending A", "rewards": [{"coins": 100}, {"pack": "lucky_pack"}]}],
            "rewards": [{"card": self.cards[1].serial_number, "copies": 2}],
        })
        self.assertEqual(problems, [])
        self.assertEqual((fields["giver"], fields["gate_rank"]), ("Ruby", 2))
        self.assertEqual(fields["spec"]["endings"][0]["to"], "Ruby")  # turned in to the giver unless it says

    def test_mistakes_are_all_listed_clearly(self):
        _, problems = quests.check({
            "key": "Bad Key", "title": "", "gates": 9, "about": "",
            "stages": [stage({"do": "defeat", "cpus": ["Nobody"]}, {"do": "teleport"}, {"do": "flag", "flag": "x"})],
            "endings": [{"key": "a", "title": "A", "locks": ["missing"]}, {"key": "a", "title": "B"}],
        })
        text = " | ".join(problems)
        for expected in ("key is lowercase", "needs a title", "only a quest with a giver can gate", "needs an about",
                         "no CPU called “Nobody”", "no objective “teleport”", "say what the player has to do", "locks “missing”",
                         "a key of its own", "since the quest has no giver"):
            self.assertIn(expected, text)

    def test_chatter_mistakes_in_its_scripts_are_found(self):
        _, problems = quests.check({"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "offer": "background night",
                                    "stages": [stage({"do": "flag", "flag": "f", "text": "t"})], "endings": [{"key": "a", "title": "A"}]})
        self.assertTrue(any("offer, line 1" in problem and "no stage" in problem for problem in problems))

    def test_a_quest_reads_back_as_it_was_written(self):
        quest = make_quest("round", self.ruby, gates=2, stages=[stage({"do": "talk", "to": "Ruby", "script": ["them: Hi.", "them: Bye."]})],
                           endings=[{"key": "a", "title": "A", "script": ["them: Done."]}], rewards=[{"coins": 50}], hidden=True)
        fields, problems = quests.check(quests.as_file(quest))
        self.assertEqual(problems, [])
        self.assertEqual(fields["spec"], quest.spec)


class GateTests(QuestBase):
    def test_a_gate_quest_holds_the_rank_however_many_points_pile_up(self):
        make_quest("ember", self.ruby, gates=2)
        save = self.points(self.ruby, 500)
        self.assertEqual(world.rank_of(save, self.ruby.pk), 1)
        standing = world.standing(save, self.ruby.pk)
        self.assertEqual((standing["gate"]["title"], standing["gate"]["status"], standing["gate"]["ready"]), ("Ember", "offered", True))

    def test_a_cpu_with_no_quests_ranks_up_as_before(self):
        save = self.points(self.ruby, 500)
        self.assertEqual(world.rank_of(save, self.ruby.pk), 5)

    def test_its_offered_only_once_the_points_are_there(self):
        quest = make_quest("ember", self.ruby, gates=2)
        save = self.points(self.ruby, 20)
        self.assertFalse(quests.offerable(save, quest))
        save = self.points(self.ruby, 40)
        self.assertTrue(quests.offerable(save, quest))
        self.assertEqual(world.town(save)["people"][0]["quests"]["offers"] if world.town(save)["people"][0]["id"] == self.ruby.pk else
                         world.town(save)["people"][1]["quests"]["offers"], [{"quest": "ember", "title": "Ember"}])

    def test_a_later_gate_waits_for_the_earlier_one(self):
        first = make_quest("first", self.ruby, gates=2)
        later = make_quest("later", self.ruby, gates=5)
        save = self.points(self.ruby, 1000)
        self.assertEqual(world.rank_of(save, self.ruby.pk), 1)
        self.assertTrue(quests.offerable(save, first))
        self.assertFalse(quests.offerable(save, later))

    def test_taking_it_and_finishing_it_reaches_the_rank_with_its_scene(self):
        scene = Scene.objects.create(name="Ruby, friend", script="cast me as Ruby\nme: Friends!")
        Chatter.objects.create(cpu=self.ruby, context="rank_up", min_rank=2, scene=scene)
        make_quest("ember", self.ruby, gates=2, offer=["them: Will you help?"],
                   endings=[{"key": "end", "title": "Done", "script": ["them (pleased): Thank you."], "rewards": [{"coins": 250}]}])
        save = self.points(self.ruby, 60)
        said = world.quest_act(save, self.ruby.pk, "offer", "ember", {})["talk"]
        self.assertEqual(said["events"][0]["say"], "Will you help?")
        self.assertEqual(said["waiting"]["quest_offer"]["title"], "Ember")
        self.assertEqual(said["waiting"]["quest_offer"]["gate"], "Friend")
        world.quest_act(save, self.ruby.pk, "accept", "ember", {})
        save = self.fresh()
        self.assertEqual(quests.status(save, "ember"), "active")
        world.Talk(save, self.ruby, "x").set_flag("ember_done", True)
        world.changed(save, "flags")
        save = self.fresh()
        self.assertEqual(quests.status(save, "ember"), "settling")
        self.assertEqual(world.quest_act(save, self.ruby.pk, "settle", "ember", {})["talk"]["waiting"]["endings"]["endings"][0]["key"], "end")
        money = save.money
        said = world.quest_act(save, self.ruby.pk, "choose", "ember", {"ending": "end"})["talk"]
        save = self.fresh()
        self.assertEqual(quests.status(save, "ember"), "done")
        self.assertEqual(world.rank_of(save, self.ruby.pk), 2)
        kinds = [next(iter(event)) for event in said["events"]]
        self.assertEqual(said["events"][0]["say"], "Thank you.")  # the ending's script, then what it did
        self.assertIn("rank_reached", kinds)
        self.assertTrue(any("scene" in event for event in said["events"]))
        self.assertGreaterEqual(save.money, money + 250 + 200)  # the quest's coins and the rank's own (Acquaintance) reward


class LockoutTests(QuestBase):
    def setUp(self):
        super().setUp()
        self.ruby_q = make_quest("rose", self.ruby, gates=2)
        self.cinder_q = make_quest("ashes", self.cinder, gates=2, endings=[
            {"key": "burn", "title": "Burn it down", "locks": ["rose"]},
            {"key": "spare", "title": "Walk away"}])
        save = self.points(self.ruby, 60)
        save = self.points(self.cinder, 60)
        world.quest_act(save, self.cinder.pk, "accept", "ashes", {})
        world.Talk(save, self.cinder, "x").set_flag("ashes_done", True)
        world.changed(save, "flags")
        self.save = self.fresh()

    def test_each_ending_says_what_it_would_close_before_its_chosen(self):
        panel = quests.settle_panel(self.save, self.cinder, "ashes")
        burn, spare = panel["endings"]
        self.assertEqual([q["title"] for q in burn["fallout"]["quests"]], ["Rose"])
        self.assertEqual(burn["fallout"]["quests"][0]["held"], "Acquaintance")  # Ruby stays at that for good
        self.assertEqual(spare["fallout"]["quests"], [])

    def test_an_ending_that_closes_something_must_be_confirmed(self):
        with self.assertRaisesRegex(ValueError, "confirm"):
            quests.choose(self.save, self.cinder, "ashes", "burn", confirmed=False)
        self.assertEqual(quests.status(self.save, "ashes"), "settling")

    def test_the_locked_quest_fails_and_its_giver_stays_capped_and_cold(self):
        world.quest_act(self.save, self.cinder.pk, "choose", "ashes", {"ending": "burn", "confirm": "1"})
        save = self.fresh()
        self.assertEqual((quests.status(save, "ashes"), quests.status(save, "rose")), ("done", "failed"))
        self.assertFalse(quests.offerable(save, self.ruby_q))
        self.points(self.ruby, 2000)
        self.assertEqual(world.rank_of(self.fresh(), self.ruby.pk), 1)
        self.assertTrue(quests.estranged(self.save, self.ruby.pk))
        Chatter.objects.create(cpu=self.ruby, context="estranged", script="them (dismayed): After what you did?")
        said = world.talk(self.save, self.ruby.pk)["talk"]
        self.assertIn("After what you did?", [event["say"] for event in said["events"] if "say" in event])
        failed = quests.journal(self.fresh())["failed"][0]
        self.assertEqual((failed["title"], failed["by"], failed["by_ending"], failed["held"]), ("Rose", "Ashes", "Burn it down", "Acquaintance"))

    def test_the_other_ending_closes_nothing(self):
        world.quest_act(self.save, self.cinder.pk, "choose", "ashes", {"ending": "spare"})
        save = self.fresh()
        self.assertEqual(quests.status(save, "rose"), "")
        self.assertTrue(quests.offerable(save, self.ruby_q))


class RemovalTests(QuestBase):
    def test_an_ending_can_send_someone_away_for_good_and_whatever_needs_them_closes(self):
        make_quest("rose", self.ruby, gates=2)
        make_quest("hunt", self.cinder, stages=[stage({"do": "defeat", "cpus": ["Ruby"]})])
        make_quest("ashes", self.cinder, endings=[{"key": "kill", "title": "Finish her", "removes": ["Ruby"]}])
        save = self.points(self.cinder, 10)
        for key in ("hunt", "ashes"):
            world.quest_act(save, self.cinder.pk, "accept", key, {})
        world.Talk(save, self.cinder, "x").set_flag("ashes_done", True)
        world.changed(save, "flags")
        save = self.fresh()
        found = quests.fallout(save, quests.quests(save)["ashes"], quests.ending_of(quests.quests(save)["ashes"], "kill"))
        self.assertEqual(found["leave"], ["Ruby"])
        self.assertEqual(sorted(q["key"] for q in found["quests"]), ["hunt", "rose"])
        world.quest_act(save, self.cinder.pk, "choose", "ashes", {"ending": "kill", "confirm": "1"})
        save = self.fresh()
        self.assertNotIn(self.ruby.pk, world.whereabouts(save))
        self.assertEqual((quests.status(save, "rose"), quests.status(save, "hunt")), ("failed", "failed"))
        with self.assertRaises(ValueError):
            world.talk(save, self.ruby.pk)


class ObjectiveTests(QuestBase):
    def take(self, key, *objectives, giver=None):
        giver = giver or self.ruby
        make_quest(key, giver, stages=[stage(*objectives)])
        world.quest_act(self.save, giver.pk, "accept", key, {})
        return self.fresh()

    def test_beating_each_named_cpu(self):
        self.take("q", {"do": "defeat", "cpus": ["Ruby", "Cinder"]})
        self.duel(self.ruby, won=True)
        self.assertEqual(quests.status(self.save, "q"), "active")
        self.duel(self.cinder, won=False)
        self.assertEqual(quests.status(self.save, "q"), "active")
        self.duel(self.cinder, won=True)
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_progress_from_a_duel_is_news_in_the_town(self):
        self.take("q", {"do": "defeat", "cpus": ["Ruby", "Cinder"]})
        self.duel(self.ruby, won=True)
        news = world.town(self.save)["news"]
        self.assertTrue(any("1/2" in item["text"] for item in news))
        self.assertEqual(world.town(self.fresh())["news"], [])  # told once

    def test_a_climax_combo_against_the_named_cpu(self):
        character, climax = self.cards[0], [c for c in self.cards if c.card_type == "Climax"][0]
        self.take("q", {"do": "combo", "card": character.serial_number, "climax": climax.serial_number, "against": ["Cinder"]})
        self.duel(self.ruby, won=True, records={"combos": [[character.pk, climax.pk]]})
        self.assertEqual(quests.status(self.save, "q"), "active")
        self.duel(self.cinder, won=False, records={"combos": [[character.pk, self.cards[5].pk]]})
        self.assertEqual(quests.status(self.save, "q"), "active")  # the wrong climax
        self.duel(self.cinder, won=False, records={"combos": [[character.pk, climax.pk]]})
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_losing_to_someone_on_purpose(self):
        self.take("q", {"do": "lose_to", "cpu": "Cinder"})
        self.duel(self.cinder, won=True)
        self.assertEqual(quests.status(self.save, "q"), "active")
        self.duel(self.cinder, won=False)
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_winning_having_played_a_card_any_printing_of_it(self):
        twin = self.cards[0]
        twin_copy = type(twin).objects.create(serial_number="ALT-001", name=twin.name, expansion=twin.expansion, expansion_id=99, card_type="Character")
        self.take("q", {"do": "win_with", "card": twin.serial_number})
        self.duel(self.cinder, won=True, records={"played": [self.cards[3].pk]})
        self.assertEqual(quests.status(self.save, "q"), "active")
        self.duel(self.cinder, won=True, records={"played": [twin_copy.pk]})
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_a_deck_rule_is_checked_against_the_deck_the_duel_started_with(self):
        self.take("q", {"do": "win_deck", "max_rarity": "C"})
        rares = [c for c in self.cards if c.rarity == "R"]
        world.save_deck(self.save, {c.pk: 1 for c in rares[:2]})
        self.duel(self.cinder, won=True)  # the deck has rares
        self.assertEqual(quests.status(self.save, "q"), "active")
        commons = [c for c in self.cards if c.rarity in ("C", "CC")]
        world.save_deck(self.save, {c.pk: 1 for c in commons[:50]})
        self.duel(self.cinder, won=True)
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_stakes_and_a_run_of_wins_that_a_loss_restarts(self):
        self.take("q", {"do": "stakes", "fee": 300}, {"do": "streak", "wins": 2})
        self.duel(self.cinder, won=True, stake=100)
        self.duel(self.cinder, won=False)
        self.duel(self.cinder, won=True, stake=500)
        entry = quests.log(self.save)["q"]
        self.assertIn("0.0", entry["progress"])
        self.assertEqual(entry["progress"]["0.1"], 1)  # the loss started the run again
        self.duel(self.ruby, won=True)
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_beating_different_villains(self):
        self.cinder.temperament = "villain"
        self.cinder.save()
        neo = give_cpu("Neo", self.cards)
        neo.temperament = "villain"
        neo.save()
        self.take("q", {"do": "beat_different", "count": 2, "temperament": "villain"})
        self.duel(self.cinder, won=True)
        self.duel(self.cinder, won=True)
        self.duel(self.ruby, won=True)
        self.assertEqual(quests.status(self.save, "q"), "active")
        self.duel(neo, won=True)
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_having_a_card_counts_as_soon_as_its_opened(self):
        card = self.cards[10]
        self.save.pool.pop(str(card.pk))
        world.changed(self.save, "pool")
        self.take("q", {"do": "have_card", "card": card.serial_number, "copies": 2})
        self.assertEqual(quests.status(self.save, "q"), "active")
        self.save.pool[str(card.pk)] = 2
        world.changed(self.save, "pool")
        self.assertEqual(quests.status(self.fresh(), "q"), "settling")

    def test_collecting_cards_of_a_trait(self):
        for card in self.cards[:3]:
            card.traits = "Magic・Weapon"
            card.save()
        self.take("q", {"do": "collect", "count": 3, "trait": "magic"})
        self.assertEqual(quests.status(self.save, "q"), "settling")

    def test_going_somewhere_at_a_time(self):
        Scene.objects.create(name="Beach at night", script="background beach")
        self.take("q", {"do": "visit", "place": "beach", "times": [3], "scene": "Beach at night", "rewards": [{"coins": 50}]})
        self.save.today.pop("engaged")  # taking it was time spent at the plaza: as if taken earlier
        world.travel(self.save, "beach")
        self.assertEqual(quests.status(self.fresh(), "q"), "active")
        for _ in range(3):
            world.engage(self.save)
            world.wait(self.save)
            self.assertEqual(quests.status(self.fresh(), "q"), "active")  # not till they've said where to spend it
            world.travel(self.save, "beach")  # the map after time passes: staying
        self.assertEqual(self.save.time_of_day, "Night")
        self.assertEqual(quests.status(self.fresh(), "q"), "settling")

    def test_giving_a_gift(self):
        GiftItem.objects.create(key="rose", name="Rose", tags=["flowers"])
        self.take("q", {"do": "give_gift", "gift": "rose", "to": "Ruby"})
        self.save.gifts = {"rose": 2}
        self.save.save()
        world.give(self.save, self.cinder.pk, "rose")
        self.assertEqual(quests.status(self.fresh(), "q"), "active")
        world.give(self.save, self.ruby.pk, "rose")
        self.assertEqual(quests.status(self.fresh(), "q"), "settling")

    def test_handing_a_card_over_takes_it_from_the_cards_and_the_decks(self):
        card = self.save.deck.entries.first().card
        self.take("q", {"do": "give_card", "card": card.serial_number, "copies": 2, "to": "Ruby"})
        hands = world.town(self.save)
        ruby = next(p for p in hands["people"] if p["id"] == self.ruby.pk)
        self.assertEqual(ruby["quests"]["hands"][0]["have"], 4)
        said = world.quest_act(self.save, self.ruby.pk, "hand", "q", {"objective": "0.0"})["talk"]
        save = self.fresh()
        self.assertEqual(save.pool[str(card.pk)], 2)
        self.assertLessEqual(save.deck.entries.get(card=card).quantity, 2)
        self.assertTrue(any("gone from" in event.get("quest", "") for event in said["events"]))
        self.assertEqual(quests.status(save, "q"), "settling")

    def test_talking_it_through_plays_its_script_and_its_choices(self):
        self.take("q", {"do": "talk", "to": "Ruby", "script": ["them: Which?", "choice Pick", "- Red (set red)", "- Blue", "them: Okay."]})
        said = world.quest_act(self.save, self.ruby.pk, "talk", "q", {"objective": "0.0"})["talk"]
        self.assertEqual(said["waiting"]["options"], ["Red", "Blue"])
        self.assertEqual(quests.status(self.fresh(), "q"), "active")
        said = world.answer(self.save, self.ruby.pk, 0)["talk"]
        self.assertTrue(any("done" in event.get("quest", "") for event in said["events"]))
        save = self.fresh()
        self.assertTrue(world.has_flag(save, "red"))
        self.assertEqual(quests.status(save, "q"), "settling")

    def test_ending_requirements_wait_until_theyre_met(self):
        make_quest("q", self.ruby, endings=[{"key": "a", "title": "A", "requires": [{"do": "defeat", "cpus": ["Cinder"]}]}])
        world.quest_act(self.save, self.ruby.pk, "accept", "q", {})
        world.Talk(self.save, self.ruby, "x").set_flag("q_done", True)
        world.changed(self.save, "flags")
        save = self.fresh()
        panel = quests.settle_panel(save, self.ruby, "q")
        self.assertEqual(panel["endings"][0]["missing"], ["Beat Cinder in a duel"])
        with self.assertRaisesRegex(ValueError, "Not yet"):
            quests.choose(save, self.ruby, "q", "a", True)
        self.duel(self.cinder, won=True)
        quests.choose(self.fresh(), self.ruby, "q", "a", True)

    def test_stages_go_in_order(self):
        make_quest("q", self.ruby, stages=[stage({"do": "lose_to", "cpu": "Cinder"}, text="First"),
                                           stage({"do": "defeat", "cpus": ["Cinder"]}, text="Second")])
        world.quest_act(self.save, self.ruby.pk, "accept", "q", {})
        self.duel(self.cinder, won=True)  # not the second stage's yet
        self.assertEqual(quests.log(self.save)["q"]["stage"], 0)
        self.duel(self.cinder, won=False)
        self.assertEqual(quests.log(self.save)["q"]["stage"], 1)
        self.duel(self.cinder, won=True)
        self.assertEqual(quests.status(self.save, "q"), "settling")


class PageTests(QuestBase):
    def test_the_quest_log_shows_whats_under_way(self):
        make_quest("q", self.ruby, title="Rose petals", stages=[stage({"do": "defeat", "cpus": ["Cinder"]}, text="Beat her")],
                   rewards=[{"coins": 300}])
        world.quest_act(self.save, self.ruby.pk, "accept", "q", {})
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_quests", args=[1]))
        self.assertContains(page, "Rose petals")
        self.assertContains(page, "Beat Cinder in a duel")
        self.assertContains(page, "300 coins")

    def test_hidden_rewards_stay_hidden(self):
        make_quest("q", self.ruby, rewards=[{"coins": 300}], hidden=True)
        world.quest_act(self.save, self.ruby.pk, "accept", "q", {})
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_quests", args=[1]))
        self.assertNotContains(page, "300 coins")
        self.assertContains(page, "A surprise")

    def test_quest_moves_are_posted_like_other_town_moves(self):
        make_quest("q", self.ruby)
        self.client.force_login(self.user)
        answer = self.client.post(reverse("weiss:world_quest", args=[1]), {"cpu": self.ruby.pk, "act": "accept", "quest": "q",
                                                                            "version": self.save.version})
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.json()["town"]["quests"]["active"], 1)
        stale = self.client.post(reverse("weiss:world_quest", args=[1]), {"cpu": self.ruby.pk, "act": "accept", "quest": "q", "version": 0})
        self.assertEqual(stale.status_code, 409)


class VisitAndCardTests(QuestBase):
    def test_a_visit_must_name_the_scene_that_plays_there(self):
        _, problems = quests.check({"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "offer": "",
                                    "stages": [{"text": "Go", "objectives": [{"do": "visit", "place": "beach"}]}],
                                    "endings": [{"key": "e", "title": "E"}]})
        self.assertTrue(any("name the scene" in problem for problem in problems), problems)

    def test_a_visit_must_give_something(self):
        Scene.objects.create(name="Beach", script="background beach")
        _, problems = quests.check({"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "offer": "",
                                    "stages": [{"text": "Go", "objectives": [{"do": "visit", "place": "beach", "scene": "Beach"}]}],
                                    "endings": [{"key": "e", "title": "E"}]})
        self.assertTrue(any("give it a reward" in problem for problem in problems), problems)

    def visit_quest(self, rewards):
        script = "\n".join(["cast ruby as Ruby", "background beach", "ruby enters center with fade", "ruby: You came!"])
        Scene.objects.create(name="Ruby at the beach", script=script)
        make_quest("q", self.ruby, stages=[stage({"do": "visit", "place": "beach", "scene": "Ruby at the beach", "rewards": rewards})])
        world.quest_act(self.save, self.ruby.pk, "accept", "q", {})
        save = self.fresh()
        save.today.pop("engaged", None)  # as if taken earlier: free to go
        save.save()
        return save

    def test_arriving_plays_the_scene_gives_its_reward_and_brings_its_cast(self):
        save = self.visit_quest([{"coins": 50}])
        before = save.money
        world.travel(save, "beach")
        save = self.fresh()
        self.assertEqual(save.money - before, 50)
        self.assertTrue(save.flags["scene"]["auto"])
        self.assertEqual(save.flags["scene"]["rewards"], [["50 coins", ""]])
        town = world.town(save)
        self.assertTrue(town["scene"]["auto"])  # the town goes straight to it
        self.assertEqual(town["scene"]["who"], "Ruby")
        self.assertIn(self.ruby.pk, [cpu.pk for cpu, _ in world.present(save)])  # Ruby is at the beach afterwards
        self.assertNotIn(self.ruby.pk, [cpu.pk for cpu, _ in world.present(save, "plaza")])  # and only there

    def test_the_cast_stays_only_for_that_time_of_day(self):
        save = self.visit_quest([{"coins": 50}])
        world.travel(save, "beach")
        save = self.fresh()
        world.engage(save)
        world.wait(save)
        world.travel(save, "beach")
        self.assertNotIn(self.ruby.pk, [cpu.pk for cpu, _ in world.present(self.fresh())])

    def test_the_scene_ends_on_what_it_gave(self):
        save = self.visit_quest([{"coins": 50}])
        world.travel(save, "beach")
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_scene", args=[1]))
        self.assertContains(page, "data-scene-done")
        self.assertIn("scene", self.fresh().flags)  # waiting until it's been played to its end
        done = self.client.post(reverse("weiss:world_scene_done", args=[1]), {"state": '{"flags": [], "buffs": []}'}).json()
        self.assertEqual(done["rewards"], ["50 coins"])  # it ends on what the visit gave
        self.assertNotIn("scene", self.fresh().flags)  # played once

    def test_after_time_passes_the_map_opens_even_in_test_mode(self):
        self.save.flags["test_mode"] = True
        world.engage(self.save)
        world.wait(self.save, staff=True)
        town = world.town(self.save)
        self.assertTrue(town["choose"])  # the map opens
        self.assertFalse(town["choose_required"])  # and in test mode can be closed (which is staying)
        self.save.flags["test_mode"] = False
        self.assertTrue(world.town(self.save)["choose_required"])
        world.travel(self.save, world.place_of(self.save).key)  # staying is an answer
        self.assertFalse(world.town(self.save)["choose"])

    def test_a_card_objective_carries_the_card_to_show(self):
        card = self.cards[0]
        Scene.objects.create(name="Beach at night", script="background beach")
        make_quest("q", self.ruby, stages=[stage({"do": "have_card", "card": card.serial_number}, text="Find the card")])
        world.quest_act(self.save, self.ruby.pk, "accept", "q", {})
        objective = quests.journal(self.fresh())["active"][0]["stages"][0]["objectives"][0]
        self.assertTrue(objective["text"].startswith("Have the card "), objective["text"])
        self.assertEqual(objective["card"]["serial"], card.serial_number)
        self.assertEqual(objective["card"]["name"], card.name)
        self.assertTrue(objective["card"]["image"].endswith("/image/"))
        self.assertEqual(objective["card"]["set"], card.expansion)

    def test_an_objective_without_a_card_has_no_card_to_show(self):
        self.assertIsNone(quests.objective_card(self.save, {"do": "talk", "to": "Ruby", "script": ["them: Hi."]}))


class RecordTests(TestCase):
    """The game keeps what each player played, and the climax combos they started, for the whole game."""

    def test_records_last_the_whole_game_each_thing_once(self):
        state = {"records": {}}
        game.record(state, "1", "played", 5)
        game.record(state, "1", "played", 5)
        game.record(state, "1", "combos", [5, 9])
        self.assertEqual(state["records"]["1"], {"played": [5], "combos": [[5, 9]]})


class StaffPageTests(QuestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_the_list_shows_what_each_ending_closes_and_which_scene_ranks_have_no_quest(self):
        scene = Scene.objects.create(name="Cinder, friend", script="cast me as Cinder\nme: Hm.")
        Chatter.objects.create(cpu=self.cinder, context="rank_up", min_rank=2, scene=scene)
        make_quest("rose", self.ruby, gates=2, title="Rose")
        make_quest("ashes", self.ruby, endings=[{"key": "burn", "title": "Burn it", "locks": ["rose"], "removes": ["Cinder"]}])
        page = self.client.get(reverse("weiss:world_quest_list"))
        self.assertContains(page, "Closes: Rose")
        self.assertContains(page, "Sends away: Cinder")
        self.assertContains(page, "<strong>Cinder</strong>: Friend", html=False)

    def test_a_quest_with_mistakes_isnt_saved_but_stays_on_the_page(self):
        text = '{"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "stages": [], "endings": []}'
        page = self.client.post(reverse("weiss:world_quest_new"), {"quest": text})
        self.assertEqual(page.status_code, 200)
        self.assertFalse(Quest.objects.filter(key="q").exists())
        self.assertContains(page, "1 to 12 stages")
        self.assertContains(page, "&quot;key&quot;: &quot;q&quot;")

    def test_a_good_quest_is_saved_and_checked_as_its_typed(self):
        text = ('{"key": "q", "title": "Q", "giver": "Ruby", "gates": 2, "about": "x",'
                ' "stages": [{"text": "Go", "objectives": [{"do": "lose_to", "cpu": "Cinder"}]}], "endings": [{"key": "a", "title": "A"}]}')
        checked = self.client.post(reverse("weiss:world_quest_check"), {"quest": text}).json()
        self.assertEqual(checked["problems"], [])
        self.assertIn("Lose a duel to Cinder", checked["preview"])
        broken = self.client.post(reverse("weiss:world_quest_check"), {"quest": "{"}).json()
        self.assertTrue(broken["problems"][0].startswith("That isn't JSON yet"))
        answer = self.client.post(reverse("weiss:world_quest_new"), {"quest": text})
        quest = Quest.objects.get(key="q")
        self.assertRedirects(answer, reverse("weiss:world_quest_edit", args=[quest.pk]))
        self.assertEqual((quest.giver, quest.gate_rank), (self.ruby, 2))
        self.assertEqual(self.client.get(reverse("weiss:world_quest_edit", args=[quest.pk])).status_code, 200)


class FileTests(QuestBase):
    """Quests in a CPU's world part: world packs, CPU files and the export."""

    def pack(self, quests_part):
        return {"pack": "test", "cpus": [{"name": "Ruby", "world": {"schedule": [], "chatter": [], "quests": quests_part}}]}

    def good(self, **extra):
        return {"key": "rose", "title": "Rose", "gates": 2, "about": "x", "stages": [stage({"do": "lose_to", "cpu": "Cinder"})],
                "endings": [{"key": "a", "title": "A", "locks": ["ashes"]}], **extra}

    def test_a_pack_gives_a_cpu_its_quests_and_one_can_lock_another_cpus(self):
        from .cpu_corpus import import_world_pack
        pack = self.pack([self.good()])
        pack["cpus"].append({"name": "Cinder", "world": {"schedule": [], "chatter": [], "quests": [
            {"key": "ashes", "title": "Ashes", "about": "y", "stages": [stage({"do": "defeat", "cpus": ["Ruby"]})], "endings": [{"key": "b", "title": "B"}]}]}})
        result = import_world_pack([pack])[0]
        self.assertEqual(result.problems, [])
        self.assertIn("1 quest", result.done[0][1])
        self.assertEqual(Quest.objects.get(key="rose").giver, self.ruby)
        self.assertEqual(Quest.objects.get(key="ashes").giver, self.cinder)

    def test_a_packs_quest_mistakes_are_named_with_the_cpu(self):
        from .cpu_corpus import import_world_pack
        bad = self.good(stages=[stage({"do": "defeat", "cpus": ["Nobody"]})])
        result = import_world_pack([self.pack([bad])])[0]
        self.assertTrue(any(problem.startswith("Ruby: world quest 1") and "Nobody" in problem for problem in result.problems))
        self.assertTrue(any("locks “ashes”" in problem for problem in result.problems))
        self.assertFalse(Quest.objects.filter(giver__isnull=False).exists())  # none of the pack's (the board's own are there)

    def test_importing_again_replaces_the_cpus_quests_and_a_pack_without_any_leaves_them(self):
        from .cpu_corpus import import_world_pack
        make_quest("ashes", self.cinder)
        make_quest("old", self.ruby)
        import_world_pack([self.pack([self.good()])])
        self.assertEqual(sorted(self.ruby.quests.values_list("key", flat=True)), ["rose"])
        no_quests = {"pack": "test", "cpus": [{"name": "Ruby", "world": {"schedule": [], "chatter": []}}]}
        import_world_pack([no_quests])
        self.assertEqual(sorted(self.ruby.quests.values_list("key", flat=True)), ["rose"])

    def test_the_export_writes_them_back_as_they_read(self):
        from .cpu_corpus import quest_context, read_quests, world_info, world_record
        quest = make_quest("q", self.ruby, gates=2, offer=["them: Hm?"], rewards=[{"coins": 10}])
        written = world_record(self.ruby)["quests"]
        self.assertNotIn("giver", written[0])
        problems = []
        found = read_quests(written, "Ruby", problems, quest_context(world_info()))
        self.assertEqual(problems, [])
        self.assertEqual(found[0]["spec"], quest.spec)


class TwoAtATimeTests(QuestBase):
    def test_in_the_editor_a_quest_can_lock_one_not_written_yet(self):
        self.client.force_login(self.user)
        text = ('{"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "stages": [{"text": "Go", "objectives": [{"do": "lose_to", "cpu": "Cinder"}]}],'
                ' "endings": [{"key": "a", "title": "A", "locks": ["later"]}]}')
        checked = self.client.post(reverse("weiss:world_quest_check"), {"quest": text}).json()
        self.assertEqual(checked["problems"], [])
        self.assertIn("isn't written yet", checked["notes"][0])
        self.client.post(reverse("weiss:world_quest_new"), {"quest": text})
        self.assertTrue(Quest.objects.filter(key="q").exists())

    def test_but_a_pack_must_name_quests_that_are_there(self):
        _, problems = quests.check({"key": "q", "title": "Q", "giver": "Ruby", "about": "x", "stages": [stage({"do": "lose_to", "cpu": "Cinder"})],
                                    "endings": [{"key": "a", "title": "A", "locks": ["later"]}]})
        self.assertTrue(any("no quest with that key" in problem for problem in problems))


class RewardPackTests(QuestBase):
    def test_packs_given_together_are_revealed_together(self):
        make_quest("q", self.ruby, gates=2, rewards=[{"pack": "lucky_pack"}])
        save = self.points(self.ruby, 60)
        world.quest_act(save, self.ruby.pk, "accept", "q", {})
        world.Talk(save, self.ruby, "x").set_flag("q_done", True)
        world.changed(save, "flags")
        save = self.fresh()
        _, events = quests.choose(save, self.ruby, "q", "end", True)
        linked = [event for event in events if event.get("link")]
        self.assertEqual(len(linked), 2)  # the quest's lucky pack, and Friend's climax pack
        self.assertEqual(events[-len(linked):], linked)  # after everything else
        self.assertEqual(len(save.last_opening["packs"]), 2)
