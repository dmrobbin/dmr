"""World mode, phase 4: chatter (the compact script language and running it), friendship, gifts and rank-ups."""
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from . import chatter, world
from .models import Chatter, GiftItem, Scene, WorldSave, WorldSettings
from .test_world import SET, DuelTests, everywhere_rule, give_cpu, make_set, staff_user  # noqa: F401
from .world_views import read_ranks


def talk(save, cpu_id):
    """Talk to someone, as if it were the first time this time of day (these tests are about what's said, not when)."""
    world.relation(save, cpu_id).pop("talked_turn", None)
    return world.talk(save, cpu_id)


class Recorder:
    """Stands in for weiss.world.Talk, to run a script on its own."""

    def __init__(self, rank=0):
        self._rank, self.flags, self.paid = rank, set(), []

    def rank(self):
        return self._rank

    def flag(self, name):
        return name in self.flags

    def set_flag(self, name, on):
        (self.flags.add if on else self.flags.discard)(name)

    def points(self, n, at):
        self.paid.append(("points", n))
        return [{"points": n}]

    def money(self, n, at):
        self.paid.append(("money", n))
        return [{"money": n}]

    def gift(self, key, at):
        return [{"gift": key}]

    def fill(self, text):
        return text.replace("{player}", "Ash")


class CompileChatterTests(TestCase):
    def setUp(self):
        GiftItem.objects.get_or_create(key="iced-coffee", defaults={"name": "Iced coffee"})

    def problems(self, script):
        return [problem for _, problem in chatter.compile_chatter(script)[1]]

    def test_what_chatter_can_say(self):
        script = """# a note
them: Hi, {player}.
them (pleased): Good to see you.
player (smile): You too.
narrator: A breeze.
if rank >= 2 goto close
choice Duel?
- Sure -> duel (set keen)
- Not now
end
label close
points +5
give money 100
give gift iced-coffee
set met
if not met goto duel
label duel
fight stake 500"""
        compiled, errors = chatter.compile_chatter(script)
        self.assertEqual(errors, [])
        self.assertEqual([step["do"] for step in compiled["steps"]],
                         ["say", "say", "say", "say", "if_rank", "choice", "end", "points", "money", "gift", "set", "if", "fight"])
        self.assertEqual(compiled["steps"][-1]["stake"], 500)

    def test_staging_and_the_wrong_speakers_are_refused_clearly(self):
        cases = {
            "cast rapi as Rapi\nthem: hi": "no stage",
            "them enters left": "no stage",
            "background night": "no stage",
            "wait 2": "no stage",
            "rapi: hello": "the speakers are them",
            "them (win): hi": "moods are main, pleased, dismayed",
            "player (pleased): hi": "moods are happy",
            "narrator (pleased): hi": "no face",
            "give lucky_pack": "buffs are for challenge scenes",
            "give gift caviar": "no gift called",
            "fight rapi": "with the CPU you're talking to",
            "points +500": "Points go from",
            "goto nowhere": "no label called",
            "choice Well?": "at least one option",
            "- stray option": "straight after a choice",
            "them: hi\n- x -> y (give lucky_pack)": "straight after a choice",
            "": "Nothing's said",
        }
        for script, expected in cases.items():
            with self.subTest(script=script):
                self.assertTrue(any(expected in problem for problem in self.problems(script)), self.problems(script))

    def test_running_a_script(self):
        compiled, _ = chatter.compile_chatter("them: Hi, {player}.\nif rank >= 2 goto close\nchoice Duel?\n- Yes -> duel (set keen)\n- No\n"
                                              "them: Fine.\nend\nlabel close\nthem (pleased): Old friend!\npoints +2\nend\nlabel duel\nfight stake 300")
        world_ = Recorder(rank=0)
        events, waiting = chatter.play(compiled, 0, world_)
        self.assertEqual(events, [{"say": "Hi, Ash.", "who": "them", "mood": ""}])
        self.assertEqual((waiting["prompt"], waiting["options"]), ("Duel?", ["Yes", "No"]))
        start = chatter.after_choice(compiled, waiting["choice"], 0, world_)
        self.assertEqual(chatter.play(compiled, start, world_), ([], {"fight": 300}))
        self.assertIn("keen", world_.flags)
        self.assertEqual(chatter.play(compiled, chatter.after_choice(compiled, waiting["choice"], 1, world_), world_)[1], None)
        with self.assertRaises(ValueError):
            chatter.after_choice(compiled, waiting["choice"], 5, world_)
        events, waiting = chatter.play(compiled, 0, Recorder(rank=3))
        self.assertEqual([e.get("say") or e.get("points") for e in events], ["Hi, Ash.", "Old friend!", 2])
        self.assertIsNone(waiting)

    def test_a_goto_loop_stops(self):
        compiled, _ = chatter.compile_chatter("label a\nset x\ngoto a")
        self.assertEqual(chatter.play(compiled, 0, Recorder()), ([], None))

    def test_staff_get_the_mistakes_when_saving(self):
        with self.assertRaisesRegex(ValidationError, "Line 1"):
            Chatter(context="greet", script="them enters").clean()
        Chatter(context="greet", script="them: Hello.").clean()

    def test_every_built_in_line_compiles(self):
        for context, rank, script in chatter.DEFAULTS:
            with self.subTest(context=context, script=script):
                self.assertEqual(chatter.compile_chatter(script)[1], [])
        self.assertTrue({context for context, _, _ in chatter.DEFAULTS} >= set(chatter.CONTEXTS) - {"rank_up"} | {"rank_up"})


class TalkTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.client.force_login(self.user)
        self.save = world.start(self.user, 1, SET)
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.cinder)
        self.cinder.gift_tastes = {"loves": ["sweet"], "likes": ["drink"], "dislikes": ["spicy"]}
        self.cinder.save()
        self.cake = GiftItem.objects.create(key="cake", name="Cake", icon="🍰", price=200, tags=["sweet", "spicy"])
        self.tea = GiftItem.objects.create(key="tea", name="Tea", price=90, tags=["drink"])
        self.ramen = GiftItem.objects.create(key="ramen", name="Ramen", price=100, tags=["spicy"])
        self.rock = GiftItem.objects.create(key="rock", name="Rock", price=10, tags=["rock"])

    def points(self):
        return self.save.relations.get(str(self.cinder.pk), {}).get("points", 0)

    def test_the_first_talk_of_the_day_brings_points_and_the_rest_dont(self):
        said = talk(self.save, self.cinder.pk)["talk"]
        self.assertTrue(any(e.get("say") for e in said["events"]))
        self.assertIsNone(said["waiting"])  # the built-in first-rank greetings ask nothing
        self.assertEqual(said["events"][-1]["points"], world.TALK_POINTS)  # shown once they've said hello
        self.assertEqual(self.points(), world.TALK_POINTS)
        talk(self.save, self.cinder.pk)
        self.assertEqual(self.points(), world.TALK_POINTS)
        self.save.turn += 4  # tomorrow
        talk(self.save, self.cinder.pk)
        self.assertEqual(self.points(), world.TALK_POINTS * 2)

    def test_only_someone_here_can_be_talked_to(self):
        elsewhere = give_cpu("Katara", self.cards)
        everywhere_rule(elsewhere, "beach")
        for move in (lambda: talk(self.save, elsewhere.pk), lambda: world.give(self.save, elsewhere.pk, "tea")):
            with self.assertRaisesRegex(ValueError, "aren't here"):
                move()

    def test_their_own_lines_come_first_then_any_cpus_then_the_built_in_ones(self):
        self.assertTrue(talk(self.save, self.cinder.pk)["talk"]["events"])  # built in
        Chatter.objects.create(context="again", script="them: Anyone's line.")
        self.assertEqual(talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Anyone's line.")
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Mine, {player}.")
        Chatter.objects.create(cpu=self.cinder, context="again", script="them enters")  # a mistake: left out
        self.assertEqual(talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Mine, staff.")

    def test_lines_follow_rank(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Who are you?")
        Chatter.objects.create(cpu=self.cinder, context="again", min_rank=2, script="them: Old friend!")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        self.assertEqual(talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Who are you?")
        self.save.relations[str(self.cinder.pk)]["points"] = 45  # Friend: rank 2
        self.assertEqual(talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Old friend!")

    def test_a_scripts_coins_and_points_come_once_a_day(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Here.\ngive money 100\npoints +5\ngive gift tea")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        money = self.save.money
        talk(self.save, self.cinder.pk)
        talk(self.save, self.cinder.pk)
        self.assertEqual((self.save.money - money, self.points(), self.save.gifts), (100, 5, {"tea": 1}))
        self.save.turn += 4
        self.save.today = {}
        self.save.relations[str(self.cinder.pk)]["talked"] = self.save.day
        talk(self.save, self.cinder.pk)
        self.assertEqual(self.save.money - money, 200)

    def test_answering_a_choice(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="choice Coffee?\n- Yes -> yes\n- No\nthem: Suit yourself.\nend\n"
                                                                          "label yes\nthem (pleased): My treat.\nset coffee_date")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        said = talk(self.save, self.cinder.pk)["talk"]
        self.assertEqual(said["waiting"]["options"], ["Yes", "No"])
        said = world.answer(self.save, self.cinder.pk, 0)["talk"]
        self.assertEqual([e["say"] for e in said["events"]], ["My treat."])
        self.assertTrue(world.has_flag(self.save, "coffee_date"))
        with self.assertRaisesRegex(ValueError, "over"):
            world.answer(self.save, self.cinder.pk, 0)  # nothing's being asked now

    def test_a_flag_from_talk_can_open_a_place(self):
        from .models import WorldPlace
        WorldPlace.objects.create(key="bar", name="The bar", backdrops=["night"] * 4, order=20, unlock_flag="bar_open")
        self.assertNotIn("bar", [p.key for p in world.places(self.save)])
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Meet me at the bar.\nset bar_open")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        talk(self.save, self.cinder.pk)
        self.assertIn("bar", [p.key for p in world.places(self.save)])

    def test_a_script_cant_set_the_saves_own_flags(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Hm.\nset last_duel")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        talk(self.save, self.cinder.pk)
        self.assertNotIn("last_duel", self.save.flags.get("set", []))

    def test_gifts(self):
        world.travel(self.save, "shop")
        self.save.money = 1000
        for key in ("cake", "tea", "ramen", "rock"):
            world.buy_gift(self.save, key)
        self.assertEqual(self.save.money, 1000 - 400)
        world.travel(self.save, "plaza")
        with self.assertRaisesRegex(ValueError, "card shop"):
            world.buy_gift(self.save, "tea")
        self.assertEqual([world.taste(self.cinder, item) for item in (self.cake, self.tea, self.ramen, self.rock)],
                         ["loved", "liked", "disliked", "neutral"])  # a loved tag wins over a disliked one
        said = world.give(self.save, self.cinder.pk, "cake")["talk"]
        self.assertEqual(said["events"][0], {"gave": "Cake", "icon": "🍰", "reaction": "loved"})  # handed over first
        self.assertEqual(said["events"][-1]["points"], world.GIFT_POINTS["loved"])
        self.assertEqual(self.points(), world.GIFT_POINTS["loved"])
        self.assertNotIn("cake", self.save.gifts)
        with self.assertRaisesRegex(ValueError, "today already"):
            world.give(self.save, self.cinder.pk, "tea")  # one a day
        self.save.turn += 4
        world.give(self.save, self.cinder.pk, "ramen")
        self.assertEqual(self.points(), world.GIFT_POINTS["loved"] + world.GIFT_POINTS["disliked"])
        self.save.turn += 4
        with self.assertRaisesRegex(ValueError, "don't have"):
            world.give(self.save, self.cinder.pk, "cake")

    def test_points_never_go_below_nothing(self):
        world.travel(self.save, "shop")
        world.buy_gift(self.save, "ramen")
        world.travel(self.save, "plaza")
        world.give(self.save, self.cinder.pk, "ramen")
        self.assertEqual(self.points(), 0)

    def test_reaching_a_rank_plays_its_line(self):
        self.save.relations[str(self.cinder.pk)] = {"points": 13}  # Acquaintance is at 15
        said = talk(self.save, self.cinder.pk)["talk"]
        ups = [e for e in said["events"] if e.get("rank_up")]
        self.assertEqual(ups[0]["rank_up"], "Acquaintance")
        says = [e["say"] for e in said["events"] if "say" in e]
        self.assertIn("You know, you're not bad to have around.", says)  # the built-in rank_up line for rank 1

    def test_a_rank_up_can_play_a_full_scene(self):
        scene = Scene.objects.create(name="Cinder opens up", script="cast c as Cinder\nc: I never told anyone this.")
        Chatter.objects.create(cpu=self.cinder, context="rank_up", min_rank=1, scene=scene)
        self.save.relations[str(self.cinder.pk)] = {"points": 13}
        said = talk(self.save, self.cinder.pk)["talk"]
        self.assertIn({"scene": reverse("weiss:world_scene", args=[1])}, said["events"])
        self.save.save()
        page = self.client.get(reverse("weiss:world_scene", args=[1]))
        self.assertContains(page, "I never told anyone this.")
        self.assertRedirects(self.client.get(reverse("weiss:world_scene", args=[1])), reverse("weiss:world_town", args=[1]))  # once

    def test_talking_from_the_page(self):
        state = self.client.get(reverse("weiss:world_town_state", args=[1])).json()
        person = state["people"][0]
        self.assertEqual((person["relation"]["name"], person["relation"]["talked"]), ("Stranger", False))
        self.assertTrue(person["intro"])  # the line before a duel
        self.assertTrue({"cake", "tea", "ramen", "rock"} <= {item["key"] for item in state["gifts"]})
        answer = self.client.post(reverse("weiss:world_talk", args=[1]), {"cpu": self.cinder.pk, "version": state["version"]}).json()
        self.assertTrue(answer["talk"]["events"])
        self.assertTrue(answer["town"]["people"][0]["relation"]["talked"])
        stale = self.client.post(reverse("weiss:world_talk", args=[1]), {"cpu": self.cinder.pk, "version": state["version"]})
        self.assertEqual(stale.status_code, 409)
        page = self.client.get(reverse("weiss:world_town", args=[1]))
        self.assertContains(page, 'data-shop-tab="gifts"')


class TalkAndDuelTests(DuelTests):
    """Stakes offered in talk, and duels' points (the DuelTests setup: Cinder everywhere, a ready deck)."""

    def test_a_stake_offered_in_talk_is_the_fee(self):
        Chatter.objects.create(cpu=self.cinder, context="greet", script="them: Feeling lucky?\nfight stake 500")
        said = talk(self.save, self.cinder.pk)["talk"]
        self.assertEqual(said["waiting"], {"fight": 500})
        self.save.money = 1000
        room = world.start_duel(self.save, self.cinder.pk, high_stakes=True)
        self.assertEqual((room.world_stake, self.save.money), (500, 500))

    def test_duels_bring_points_and_their_word_on_it(self):
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=True)
        self.assertEqual(self.save.relations[str(self.cinder.pk)]["points"], world.WIN_POINTS)
        Chatter.objects.create(cpu=self.cinder, context="after_win", script="them (dismayed): Lucky draw, {player}.")
        result = world.duel_result(self.save)
        self.assertEqual((result["points"], result["line"]), (world.WIN_POINTS, "Lucky draw, staff."))
        room = world.start_duel(self.save, self.cinder.pk)
        self.finish(room, won=False)
        self.assertEqual(self.save.relations[str(self.cinder.pk)]["points"], world.WIN_POINTS + world.LOSS_POINTS)
        self.assertTrue(world.duel_result(self.save)["line"])  # the built-in one


class RankSettingsTests(TestCase):
    def test_reading_ranks(self):
        self.assertEqual(read_ranks("New: 0\nPal: 10\n\nBest pal: 30"),
                         [{"name": "New", "points": 0}, {"name": "Pal", "points": 10}, {"name": "Best pal", "points": 30}])
        for text in ("New: 0", "New: 5\nPal: 10", "New: 0\nPal: 10\nMeh: 10", "New: 0\nPal", "New: 0\nPal: x"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    read_ranks(text)

    def test_ranks_staff_set_are_used(self):
        WorldSettings.objects.update_or_create(pk=1, defaults={"ranks": [{"name": "New", "points": 0}, {"name": "Pal", "points": 5}]})
        self.assertEqual(world.rank_names(), ["New", "Pal"])
        self.assertEqual(world.rank_for(7), 1)


class GainAndRewardTests(DuelTests):
    """Temperaments' gain rates, what each rank brings, and rank-ups from duels (the DuelTests setup)."""

    def points(self):
        return self.save.relations.get(str(self.cinder.pk), {}).get("points", 0)

    def test_temperament_sets_how_fast_points_come(self):
        for temperament, expected in (("warm", 4), ("neutral", 3), ("villain", 2)):
            self.cinder.temperament = temperament
            self.assertEqual(world.gain(self.cinder, world.TALK_POINTS), expected)
            self.assertEqual(world.gain(self.cinder, -4), -4)  # losing points is never scaled
        self.cinder.save()
        talk(self.save, self.cinder.pk)
        self.assertEqual(self.points(), 2)

    def test_each_rank_brings_its_rewards_once(self):
        money = self.save.money
        self.save.relations[str(self.cinder.pk)] = {"points": 14}
        said = talk(self.save, self.cinder.pk)["talk"]  # +3: Acquaintance
        rewards = [event["reward"] for event in said["events"] if "reward" in event]
        self.assertEqual(rewards[0], "200 coins")
        self.assertEqual(self.save.money - money, 200)
        self.assertEqual(sum(self.save.gifts.values()), 1)
        from .models import PlayerProfile
        self.assertEqual(PlayerProfile.objects.get(user=self.user).progress[f"world_rank:{self.cinder.pk}"], 1)
        self.save.relations[str(self.cinder.pk)]["points"] = 10  # fell back a rank, then climbs again
        for _ in range(2):
            self.save.turn += 4
            talk(self.save, self.cinder.pk)
        self.assertEqual(self.save.money - money, 200)  # not paid twice

    def test_signature_cards_packs_and_stakes(self):
        pool = sum(self.save.pool.values())
        self.save.relations[str(self.cinder.pk)] = {"points": 39, "rewarded": 1}
        said = talk(self.save, self.cinder.pk)["talk"]  # Friend
        events = said["events"]
        if said["waiting"]:  # a friend's greeting can ask something: the points and rewards come once it's answered
            events = events + world.answer(self.save, self.cinder.pk, 0)["talk"]["events"]
        rewards = [event for event in events if "reward" in event]
        signature = world.signature_cards(self.cinder, "signature")[0]
        self.assertTrue(self.cinder.deck.entries.filter(card=signature).exists() and signature.card_type != "Climax")
        self.assertEqual(rewards[0]["reward"], f"{signature.name} \u00d72")
        self.assertIn("climax pack", rewards[1]["reward"])
        self.assertEqual(rewards[1]["link"], reverse("weiss:world_opened", args=[1]))
        self.assertEqual(sum(self.save.pool.values()) - pool, 2 + 8)
        self.save.relations[str(self.cinder.pk)].update(points=139, rewarded=3)
        self.save.turn += 4
        talk(self.save, self.cinder.pk)  # Close friend: stakes
        self.assertEqual(world.stake_with(self.save, self.cinder.pk), 500)
        self.save.money = 2000
        room = world.start_duel(self.save, self.cinder.pk, high_stakes=True)
        self.assertEqual(room.world_stake, 500)

    def test_the_town_says_what_the_next_rank_brings(self):
        self.assertEqual(world.standing(self.save, self.cinder.pk)["next_rewards"], ["200 coins", "a gift"])

    def test_a_rank_reached_in_a_duel_gives_its_rewards_and_says_its_line(self):
        self.save.relations[str(self.cinder.pk)] = {"points": 12}
        self.save.save()
        self.finish(world.start_duel(self.save, self.cinder.pk), won=True)  # +6: Acquaintance
        result = world.duel_result(self.save)
        self.assertEqual(result["rank_up"], "Acquaintance")
        self.assertEqual(result["rewards"][0], "200 coins")
        self.assertEqual(result["rank_line"], "You know, you're not bad to have around.")

    def test_a_rank_reached_in_a_duel_can_play_its_scene(self):
        scene = Scene.objects.create(name="Cinder opens up", script="cast c as Cinder\nc: Hm.")
        Chatter.objects.create(cpu=self.cinder, context="rank_up", min_rank=1, scene=scene)
        self.save.relations[str(self.cinder.pk)] = {"points": 12}
        self.save.save()
        self.finish(world.start_duel(self.save, self.cinder.pk), won=True)
        self.assertEqual(world.duel_result(self.save)["scene"], reverse("weiss:world_scene", args=[1]))
        self.assertEqual(self.save.flags["scene"]["scene"], scene.pk)


class WorldPackTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.cinder, "plaza")
        Chatter.objects.create(cpu=self.cinder, context="greet", script="them: Old line.")
        self.pack = {"cpus": [
            {"name": "cinder", "world": {"temperament": "villain",
                                         "schedule": [{"place": "alley", "days": [0, 1, 2, 3, 4, 5, 6], "times": [2, 3], "weight": 70}],
                                         "gift_tastes": {"loves": ["fancy"], "likes": [], "dislikes": ["cute"]},
                                         "chatter": [{"context": "greet", "script": "them: You again."},
                                                     {"context": "rank_up", "min_rank": 2, "scene": "World: Cinder, Friend"}]},
             "scenes": [{"name": "World: Cinder, Friend", "script": "cast cinder as Cinder\nbackground night\ncinder enters\ncinder: Well."}]},
            {"name": "Nobody Here", "world": {}},
        ]}

    def test_a_pack_gives_existing_cpus_their_world(self):
        from .cpu_corpus import import_world_pack
        result = import_world_pack([self.pack], dry_run=True)[0]
        self.assertEqual((result.problems, result.missing), ([], ["Nobody Here"]))
        self.assertEqual(self.cinder.schedule.get().place.key, "plaza")  # a dry run saves nothing
        import_world_pack([self.pack])
        self.cinder.refresh_from_db()
        self.assertEqual((self.cinder.temperament, self.cinder.gift_tastes["loves"]), ("villain", ["fancy"]))
        self.assertEqual([rule.place.key for rule in self.cinder.schedule.all()], ["alley"])  # replaced
        self.assertEqual(sorted(line.script for line in self.cinder.chatter.all()), ["", "them: You again."])
        self.assertEqual(self.cinder.chatter.get(context="rank_up").scene.name, "World: Cinder, Friend")
        self.pack["cpus"][0]["scenes"][0]["script"] += "\ncinder: Again."
        import_world_pack([self.pack])
        self.assertEqual(Scene.objects.filter(name="World: Cinder, Friend").count(), 1)  # updated, not doubled
        self.assertIn("Again.", Scene.objects.get(name="World: Cinder, Friend").script)

    def test_problems_save_nothing(self):
        from .cpu_corpus import import_world_pack
        self.pack["cpus"][0]["world"]["schedule"][0]["place"] = "moon"
        result = import_world_pack([self.pack])[0]
        self.assertTrue(any("Cinder: world schedule rule 1" in problem for problem in result.problems), result.problems)
        self.assertEqual(self.cinder.schedule.get().place.key, "plaza")
        self.assertFalse(Scene.objects.exists())

    def test_the_import_tab(self):
        import json
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(staff_user())
        upload = lambda: SimpleUploadedFile("cast.json", json.dumps(self.pack).encode(), content_type="application/json")
        page = self.client.post(reverse("weiss:world_pack_import"), {"step": "check", "packs": upload()})
        self.assertContains(page, "Ready to import")
        self.assertContains(page, "Not here, so skipped: Nobody Here")
        page = self.client.post(reverse("weiss:world_pack_import"), {"step": "import", "packs": upload()})
        self.assertContains(page, "Imported")
        self.assertEqual(self.cinder.schedule.get().place.key, "alley")


class SpendingTimeTests(TestCase):
    """Once the player spends a time of day with someone, they stay where they are until it passes: and it only passes
    once it's been spent (unless there's nobody out to spend it with)."""

    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.cinder)
        self.save.place = "plaza"
        GiftItem.objects.get_or_create(key="tea", defaults={"name": "Tea"})

    def test_looking_around_is_free_until_someone_is_talked_to(self):
        world.travel(self.save, "cafe")
        world.travel(self.save, "plaza")
        world.talk(self.save, self.cinder.pk)
        with self.assertRaisesRegex(ValueError, "pass time before you go"):
            world.travel(self.save, "cafe")
        world.travel(self.save, "plaza")  # staying put is fine
        world.wait(self.save)
        world.travel(self.save, "cafe")

    def test_time_only_passes_once_its_spent_with_someone(self):
        with self.assertRaisesRegex(ValueError, "Spend this time with someone first"):
            world.wait(self.save)
        town = world.town(self.save)
        self.assertEqual((town["engaged"], town["can_wait"], town["next_time"]), (False, False, "Noon"))
        world.give_tastes()
        self.save.gifts = {"tea": 1}
        world.give(self.save, self.cinder.pk, "tea")
        self.assertTrue(world.town(self.save)["can_wait"])
        world.wait(self.save)
        self.assertEqual(self.save.time_of_day, "Noon")

    def test_with_nobody_out_time_can_pass_anyway(self):
        self.cinder.schedule.all().delete()
        world.wait(self.save)
        self.assertEqual(self.save.time_of_day, "Noon")

    def test_the_shop_doesnt_count(self):
        self.save.place = "shop"
        self.save.money = 1000
        world.buy_gift(self.save, "tea")
        world.travel(self.save, "plaza")

    def test_each_person_once_a_time_of_day(self):
        world.talk(self.save, self.cinder.pk)
        with self.assertRaisesRegex(ValueError, "talked with Cinder this morning already"):
            world.talk(self.save, self.cinder.pk)
        self.assertTrue(world.town(self.save)["people"][0]["talked_now"])
        world.wait(self.save)
        world.travel(self.save, "plaza")  # where now? staying
        said = world.talk(self.save, self.cinder.pk)["talk"]  # later the same day: their "again" lines, no more points
        self.assertFalse(any("points" in event for event in said["events"]))

    def test_a_duel_spends_the_time_and_its_result_says_when_it_started(self):
        self.save.pool = {str(c.pk): 4 for c in self.cards}
        self.save.packs, self.save.rewards = 0, []
        climaxes = [c for c in self.cards if c.card_type == "Climax"][:2]
        others = [c for c in self.cards if c.card_type != "Climax"][:14]
        world.save_deck(self.save, {c.pk: 4 for c in climaxes} | {c.pk: 3 for c in others})
        room = world.start_duel(self.save, self.cinder.pk)
        self.assertTrue(world.engaged(self.save))
        over = {"winner": str(self.user.pk), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over
        room.save()
        world.game_finished(room, over)
        self.save.refresh_from_db()
        self.assertEqual(self.save.flags["last_duel"]["before"], {"time": 0, "label": "Monday morning", "day": 1})
        self.assertFalse(world.engaged(self.save))  # a new time of day: free to go


class GreetingTests(TestCase):
    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.cinder)
        self.save.place = "plaza"

    def person(self):
        return world.town(self.save)["people"][0]

    def test_everyone_has_a_hello_and_goodbye_that_warm_up_with_rank(self):
        stranger = self.person()
        self.assertTrue(stranger["hello"] and stranger["bye"])
        self.assertNotIn(self.user.username, stranger["hello"])
        world.relation(self.save, self.cinder.pk)["points"] = 500
        close = self.person()
        self.assertIn(close["hello"], [f"{self.user.username}! I was hoping you'd stop by."])

    def test_a_cpus_own_lines_come_first_and_stay_the_same_all_through_a_time_of_day(self):
        Chatter.objects.create(cpu=self.cinder, context="hello", script="them: Ah. The moth returns to the flame.")
        Chatter.objects.create(cpu=self.cinder, context="goodbye", script="them: Run along.")
        Chatter.objects.create(cpu=self.cinder, context="goodbye", script="them: Don't keep me waiting.")
        first = self.person()
        self.assertEqual(first["hello"], "Ah. The moth returns to the flame.")
        self.assertEqual([self.person()["bye"] for _ in range(5)], [first["bye"]] * 5)

    def test_someone_estranged_is_cold(self):
        from .models import Quest
        Quest.objects.create(key="q", title="Q", giver=self.cinder, gate_rank=2, spec={"stages": [], "endings": []})
        self.save.quests = {"log": {"q": {"status": "failed"}}}
        person = self.person()
        self.assertIn(person["bye"], ["Fine. Go."])


class ChoosingWhereTests(TestCase):
    """When time passes, the player chooses where to spend the new time of day (staying is a choice); staff can turn
    on test mode to skip the rules."""

    def setUp(self):
        self.cards = make_set()
        self.user = staff_user()
        self.save = world.start(self.user, 1, SET)
        self.cinder = give_cpu("Cinder", self.cards)
        everywhere_rule(self.cinder)
        self.save.place = "plaza"
        self.save.save()

    def test_after_time_passes_nobody_can_be_talked_to_till_a_place_is_chosen(self):
        world.talk(self.save, self.cinder.pk)
        world.wait(self.save)
        self.assertTrue(world.town(self.save)["choose"])
        with self.assertRaisesRegex(ValueError, "choose where to go first"):
            world.talk(self.save, self.cinder.pk)
        world.travel(self.save, "plaza")
        self.assertFalse(world.town(self.save)["choose"])
        world.talk(self.save, self.cinder.pk)

    def test_choosing_survives_a_reload(self):
        world.talk(self.save, self.cinder.pk)
        world.wait(self.save)
        self.save.refresh_from_db()
        self.assertTrue(world.choosing(self.save))

    def test_staying_says_so(self):
        from django.urls import reverse
        world.talk(self.save, self.cinder.pk)
        world.wait(self.save)
        self.client.force_login(self.user)
        said = self.client.post(reverse("weiss:world_travel", args=[1]), {"place": "plaza", "version": self.save.version}).json()
        self.assertEqual(said["said"], "You stay at the Plaza.")

    def test_test_mode_lets_staff_wait_and_travel_whenever(self):
        with self.assertRaises(ValueError):
            world.wait(self.save, staff=True)  # off: the real rules
        world.set_test_mode(self.save, True)
        world.wait(self.save, staff=True)
        world.talk(self.save, self.cinder.pk)  # no map to answer in test mode
        world.travel(self.save, "cafe")
        self.assertEqual((self.save.time_of_day, self.save.place), ("Noon", "cafe"))
        self.assertTrue(world.town(self.save)["test_mode"])

    def test_test_mode_is_for_staff(self):
        self.user.is_staff = False
        self.user.save()
        with self.assertRaisesRegex(ValueError, "for staff"):
            world.set_test_mode(self.save, True)
        self.save.flags["test_mode"] = True  # even if a flag says so
        self.assertFalse(world.test_mode(self.save))
