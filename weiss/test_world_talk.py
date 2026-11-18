"""World mode, phase 4: chatter (the compact script language and running it), friendship, gifts and rank-ups."""
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from . import chatter, world
from .models import Chatter, GiftItem, Scene, WorldSave, WorldSettings
from .test_world import SET, DuelTests, everywhere_rule, give_cpu, make_set, staff_user
from .world_views import read_ranks


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
        said = world.talk(self.save, self.cinder.pk)["talk"]
        self.assertTrue(any(e.get("say") for e in said["events"]))
        self.assertIsNone(said["waiting"])  # the built-in first-rank greetings ask nothing
        self.assertEqual(said["events"][-1]["points"], world.TALK_POINTS)  # shown once they've said hello
        self.assertEqual(self.points(), world.TALK_POINTS)
        world.talk(self.save, self.cinder.pk)
        self.assertEqual(self.points(), world.TALK_POINTS)
        self.save.turn += 4  # tomorrow
        world.talk(self.save, self.cinder.pk)
        self.assertEqual(self.points(), world.TALK_POINTS * 2)

    def test_only_someone_here_can_be_talked_to(self):
        elsewhere = give_cpu("Katara", self.cards)
        everywhere_rule(elsewhere, "beach")
        for move in (lambda: world.talk(self.save, elsewhere.pk), lambda: world.give(self.save, elsewhere.pk, "tea")):
            with self.assertRaisesRegex(ValueError, "aren't here"):
                move()

    def test_their_own_lines_come_first_then_any_cpus_then_the_built_in_ones(self):
        self.assertTrue(world.talk(self.save, self.cinder.pk)["talk"]["events"])  # built in
        Chatter.objects.create(context="again", script="them: Anyone's line.")
        self.assertEqual(world.talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Anyone's line.")
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Mine, {player}.")
        Chatter.objects.create(cpu=self.cinder, context="again", script="them enters")  # a mistake: left out
        self.assertEqual(world.talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Mine, staff.")

    def test_lines_follow_rank(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Who are you?")
        Chatter.objects.create(cpu=self.cinder, context="again", min_rank=2, script="them: Old friend!")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        self.assertEqual(world.talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Who are you?")
        self.save.relations[str(self.cinder.pk)]["points"] = 45  # Friend: rank 2
        self.assertEqual(world.talk(self.save, self.cinder.pk)["talk"]["events"][0]["say"], "Old friend!")

    def test_a_scripts_coins_and_points_come_once_a_day(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Here.\ngive money 100\npoints +5\ngive gift tea")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        money = self.save.money
        world.talk(self.save, self.cinder.pk)
        world.talk(self.save, self.cinder.pk)
        self.assertEqual((self.save.money - money, self.points(), self.save.gifts), (100, 5, {"tea": 1}))
        self.save.turn += 4
        self.save.today = {}
        self.save.relations[str(self.cinder.pk)]["talked"] = self.save.day
        world.talk(self.save, self.cinder.pk)
        self.assertEqual(self.save.money - money, 200)

    def test_answering_a_choice(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="choice Coffee?\n- Yes -> yes\n- No\nthem: Suit yourself.\nend\n"
                                                                          "label yes\nthem (pleased): My treat.\nset coffee_date")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        said = world.talk(self.save, self.cinder.pk)["talk"]
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
        world.talk(self.save, self.cinder.pk)
        self.assertIn("bar", [p.key for p in world.places(self.save)])

    def test_a_script_cant_set_the_saves_own_flags(self):
        Chatter.objects.create(cpu=self.cinder, context="again", script="them: Hm.\nset last_duel")
        self.save.relations[str(self.cinder.pk)] = {"points": 0, "talked": self.save.day}
        world.talk(self.save, self.cinder.pk)
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
        said = world.talk(self.save, self.cinder.pk)["talk"]
        ups = [e for e in said["events"] if e.get("rank_up")]
        self.assertEqual(ups[0]["rank_up"], "Acquaintance")
        says = [e["say"] for e in said["events"] if "say" in e]
        self.assertIn("You know, you're not bad to have around.", says)  # the built-in rank_up line for rank 1

    def test_a_rank_up_can_play_a_full_scene(self):
        scene = Scene.objects.create(name="Cinder opens up", script="cast c as Cinder\nc: I never told anyone this.")
        Chatter.objects.create(cpu=self.cinder, context="rank_up", min_rank=1, scene=scene)
        self.save.relations[str(self.cinder.pk)] = {"points": 13}
        said = world.talk(self.save, self.cinder.pk)["talk"]
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
        said = world.talk(self.save, self.cinder.pk)["talk"]
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
