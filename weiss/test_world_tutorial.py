"""World mode's tutorial (weiss.world_tutorial): a new player's first time in town, step by step, and nothing else until
the first duel with their guide."""
import json

from django.test import TestCase
from django.urls import reverse

from . import quests, world, world_tutorial as tutorial
from .cpu_corpus import read_tutorial
from .models import GiftItem, TutorialLine
from .test_world import SET, everywhere_rule, give_cpu, make_set, staff_user


class TutorialBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cards = make_set()
        GiftItem.objects.get_or_create(key="cake", defaults={"name": "Cake", "price": 100, "tags": ["sweet"]})

    def setUp(self):
        self.user = staff_user()
        self.aang = give_cpu("Aang", self.cards)
        self.erza = give_cpu("Erza Scarlet", self.cards)
        self.other = give_cpu("Somebody", self.cards)
        for cpu in (self.aang, self.erza, self.other):
            everywhere_rule(cpu, "cafe")
        self.save = world.start(self.user, 1, SET, tutorial_on=True)
        self.save.money = 5000
        self.save.save()

    def step(self):
        return tutorial.step(self.save)

    def refused(self, fn, *args, **kwargs):
        with self.assertRaises(ValueError):
            fn(*args, **kwargs)

    def legal_deck(self):
        self.save.pool = {str(card.pk): 4 for card in self.cards}
        climaxes = [card for card in self.cards if card.card_type == "Climax"][:2]
        others = [card for card in self.cards if card.card_type != "Climax"][:14]
        world.save_deck(self.save, {card.pk: 4 for card in climaxes} | {card.pk: 3 for card in others})

    def through(self, name):
        """Walk the tutorial to the start of this step, as a player would."""
        save = self.save
        while self.step() != name:
            current = self.step()
            if current == "arrive":
                tutorial.said(save)
                tutorial.approach(save, self.aang.pk)
            elif current == "approach":
                tutorial.said(save)
            elif current == "talk":
                tutorial.said(save)
                world.talk(save, self.aang.pk)
            elif current == "gift":
                tutorial.said(save)
                world.give(save, self.aang.pk, next(key for key, n in save.gifts.items() if n))
            elif current == "map":
                tutorial.said(save)
                world.travel(save, "shop")
            elif current == "shop":
                tutorial.said(save)
                world.checkout(save, [{"kind": "pack", "set": SET, "count": 1}])
            elif current == "quests":
                tutorial.said(save)
                tutorial.did(save, "quests")
            elif current == "time":
                tutorial.said(save)
                world.wait(save)
                world.travel(save, world.place_of(save).key)
            elif current == "deck":
                self.legal_deck()
                tutorial.said(save)
        save.save()  # as the tutorial's town move would
        return save


class StartTests(TutorialBase):
    def test_a_new_save_begins_in_the_tutorial_with_only_the_candidates_in_town(self):
        town = world.town(self.save)
        found = town["tutorial"]
        self.assertEqual((found["step"], found["highlight"]), ("arrive", ["person"]))
        self.assertTrue(found["lines"])
        self.assertTrue(all(line["who"] == "narrator" for line in found["lines"]))
        self.assertEqual(sorted(found["candidates"]), sorted([self.aang.pk, self.erza.pk]))
        self.assertEqual(sorted(p["id"] for p in town["people"]), sorted([self.aang.pk, self.erza.pk]))  # not Somebody

    def test_nothing_else_can_be_done_before_asking_someone(self):
        self.refused(world.travel, self.save, "cafe")
        self.refused(world.wait, self.save)
        self.refused(world.talk, self.save, self.aang.pk)
        self.refused(world.start_duel, self.save, self.aang.pk)
        with self.assertRaisesRegex(ValueError, "ask someone"):
            world.buy_packs(self.save, SET, 1)

    def test_asking_someone_makes_them_the_guide_and_they_follow_the_player(self):
        tutorial.said(self.save)
        tutorial.approach(self.save, self.erza.pk)
        self.assertEqual(self.save.flags["mentor"], self.erza.pk)
        self.assertEqual(self.step(), "approach")
        self.assertEqual([p["id"] for p in world.town(self.save)["people"]], [self.erza.pk])
        self.refused(tutorial.approach, self.save, self.aang.pk)  # once
        tutorial.said(self.save)
        self.assertEqual(self.step(), "talk")

    def test_a_guide_must_be_a_candidate(self):
        self.refused(tutorial.approach, self.save, self.other.pk)


class StepTests(TutorialBase):
    def test_talking_then_a_gift_they_hand_you(self):
        save = self.through("talk")
        self.refused(world.give, save, self.aang.pk, "cake")  # not yet
        world.talk(save, self.aang.pk)
        self.assertEqual(self.step(), "gift")
        self.assertTrue(any(save.gifts.values()))  # the guide handed one over

    def test_the_map_only_goes_to_the_card_shop(self):
        save = self.through("map")
        self.refused(world.travel, save, "cafe")
        world.travel(save, "shop")  # even though talking spent the time
        self.assertEqual(self.step(), "shop")
        self.assertEqual([p["id"] for p in world.town(save)["people"]], [self.aang.pk])  # the guide came along

    def test_buying_a_pack_then_the_quest_log(self):
        save = self.through("shop")
        world.checkout(save, [{"kind": "pack", "set": SET, "count": 1}])
        self.assertEqual(self.step(), "quests")
        save.save()
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_quests", args=[1]))
        save.refresh_from_db()
        self.assertEqual(tutorial.step(save), "time")
        self.assertIn("tutorial", page.context)

    def test_passing_time_only_at_its_step(self):
        save = self.through("time")
        world.wait(save)
        self.assertEqual(self.step(), "time")  # the map's open: the step waits for an answer
        world.travel(save, world.place_of(save).key)
        self.assertEqual(self.step(), "deck")

    def test_the_map_after_passing_time_lets_every_place_through(self):
        save = self.through("time")
        world.wait(save)
        view = tutorial.view(save)
        self.assertEqual(view["highlight"], [f"place-{place.key}" for place in world.places(save)])
        self.assertIn(f"place-{world.place_of(save).key}", view["highlight"])  # staying put is an answer too

    def test_going_somewhere_else_answers_the_map_too(self):
        save = self.through("time")
        world.wait(save)
        other = next(place.key for place in world.places(save) if place.key != save.place)
        world.travel(save, other)
        self.assertEqual(self.step(), "deck")

    def test_the_gift_step_lets_the_player_pick_a_gift(self):
        save = self.through("gift")
        self.assertIn("gift-item", tutorial.view(save)["highlight"])

    def test_the_deck_step_waits_for_a_legal_deck(self):
        save = self.through("deck")
        tutorial.said(save)
        self.assertEqual(self.step(), "deck")  # not legal yet
        self.assertFalse(tutorial.banner(save)["legal"])
        self.legal_deck()
        world.town(save)  # the town sees it's legal now
        self.assertEqual(self.step(), "duel")

    def test_the_duel_is_with_the_guide_on_easy_and_ends_the_tutorial(self):
        save = self.through("duel")
        self.refused(world.start_duel, save, self.other.pk)
        room = world.start_duel(save, self.aang.pk)
        self.assertEqual(room.state["cpu_model"], "easy")
        over = {"winner": str(room.guest_id), "loser": "x", "reason": "level", "rematch": []}  # lost: it still counts
        room.state["game_over"] = over
        room.save(update_fields=["state"])
        world.game_finished(room, over)
        save.refresh_from_db()
        self.assertFalse(tutorial.active(save))
        self.assertIn(tutorial.DONE_FLAG, save.flags["set"])
        self.assertIsNone(world.town(save)["tutorial"])

    def test_quests_board_and_tournament_wait(self):
        save = self.through("shop")
        self.refused(world.quest_act, save, self.aang.pk, "accept", "nothing", {})
        self.refused(world.events.enter, save)


class LinesTests(TutorialBase):
    def test_the_guides_own_lines_then_any_guides_then_the_built_in(self):
        self.through("talk")
        self.assertEqual(tutorial.lines(self.save, "talk")[0]["say"], tutorial.DEFAULT_LINES["talk"][0].split(": ", 1)[1])
        TutorialLine.objects.create(step="talk", cpu=None, script="them: Any guide says this.")
        self.assertEqual(tutorial.lines(self.save, "talk")[0]["say"], "Any guide says this.")
        TutorialLine.objects.create(step="talk", cpu=self.aang, script="them (pleased): Aang says this.")
        self.assertEqual(tutorial.lines(self.save, "talk"), [{"who": "them", "say": "Aang says this.", "mood": "pleased"}])

    def test_reading_a_story_files_tutorial(self):
        names = {"aang": "Aang"}
        problems = []
        found = read_tutorial({"guides": ["Aang"], "lines": {"talk": {"*": ["them: Hi."], "Aang": ["them: Hey!"]}}}, problems, names)
        self.assertEqual(problems, [])
        self.assertEqual(found, (["Aang"], [("talk", None, "them: Hi."), ("talk", "Aang", "them: Hey!")]))
        problems = []
        read_tutorial({"guides": ["Nobody"], "lines": {"dance": {"*": ["them: Hi."]}, "talk": {"*": ["choice Yes?", "- Yes"]}}},
                      problems, names)
        self.assertTrue(any("Nobody" in p for p in problems))
        self.assertTrue(any("no step “dance”" in p for p in problems))
        self.assertTrue(any("only lines" in p for p in problems))


class PageTests(TutorialBase):
    def post(self, **data):
        version = self.client.get(reverse("weiss:world_town_state", args=[1])).json()["version"]
        return self.client.post(reverse("weiss:world_tutorial", args=[1]), {**data, "version": version})

    def test_the_town_move(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_town", args=[1]))
        self.assertContains(page, "data-tutorial-url")
        answer = self.post(act="approach", cpu=self.aang.pk).json()
        self.assertEqual(answer["town"]["tutorial"]["step"], "approach")
        self.assertTrue(answer["town"]["tutorial"]["lines"])
        answer = self.post(act="said").json()
        self.assertEqual(answer["town"]["tutorial"]["step"], "talk")
        bad = self.post(act="dance")
        self.assertEqual(bad.status_code, 400)

    def test_staff_can_skip_it_in_test_mode(self):
        self.client.force_login(self.user)
        self.assertEqual(self.post(act="skip").status_code, 400)  # not in test mode
        self.save.flags["test_mode"] = True
        self.save.save()
        answer = self.post(act="skip").json()
        self.assertIsNone(answer["town"]["tutorial"])

    def test_the_other_pages_get_the_banner(self):
        self.through("deck")
        self.save.save()
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_save", args=[1]))
        self.assertEqual(page.context["tutorial"]["step"], "deck")
        self.assertIn("legal", page.context["tutorial"])

    def test_a_save_from_before_has_no_tutorial(self):
        self.save.flags.pop("tutorial")
        self.save.save()
        self.assertIsNone(world.town(self.save)["tutorial"])
        world.travel(self.save, "cafe")  # free to go


class NewGameTests(TutorialBase):
    def test_a_new_game_from_its_page_begins_in_the_tutorial(self):
        from .models import WorldSave
        self.client.force_login(self.user)
        self.client.post(reverse("weiss:world_new", args=[2]), {"set": SET})
        save = WorldSave.objects.get(user=self.user, slot=2)
        self.assertEqual(tutorial.step(save), "arrive")


class BannerTests(TutorialBase):
    def test_away_from_the_town_the_banner_sends_the_player_back(self):
        self.through("quests")
        self.assertIn("Head back to the town", tutorial.banner(self.save, "reveal")["hint"])  # just bought a pack
        self.through("deck")
        self.assertIn("Decks", tutorial.banner(self.save, "deck")["hint"])  # the deck step's done on the deck pages


class NoSceneDuringTheTutorialTests(TutorialBase):
    def test_a_scene_waits_until_the_tutorial_is_over(self):
        from .models import Scene
        Scene.objects.create(name="Old welcome", script="narrator: The old opening.")
        world.queue_scene(self.save, "Old welcome")
        self.save.save()
        self.assertIsNone(world.town(self.save)["scene"])  # the town doesn't play it
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("weiss:world_scene", args=[1])), reverse("weiss:world_town", args=[1]))
        tutorial.finish(self.save)
        self.assertIsNotNone(world.town(self.save)["scene"])  # once it's over, it plays
