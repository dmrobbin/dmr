"""World mode's story: chapters (story quests) that begin by themselves, one after another, the scenes they play, and
the scene queue."""
from django.test import TestCase
from django.urls import reverse

from . import quests, world, world_roster as roster
from .cpu_corpus import import_world_pack
from .models import Quest, Scene
from .test_world import SET, everywhere_rule, give_cpu, make_set, staff_user


def chapter(key, number, requires=None, stages=None, endings=None, **spec):
    """A story chapter, checked as files and the staff editor would write it."""
    data = {"key": key, "title": spec.pop("title", key.title()), "story": True, "chapter": number,
            "about": spec.pop("about", "A chapter."),
            "stages": stages or [{"text": "Win a duel", "objectives": [{"do": "beat_different", "count": 1}]}],
            "endings": endings or [{"key": "done", "title": "Done", "rewards": [{"coins": 100}]}], **spec}
    if requires:
        data["requires"] = {"quests": requires}
    fields, problems = quests.check(data)
    assert not problems, problems
    return quests.save_quest(fields, order=number)


class StoryBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cards = make_set()

    def setUp(self):
        self.user = staff_user()
        self.ruby = give_cpu("Ruby", self.cards)
        everywhere_rule(self.ruby)
        for name in ("Opening", "Chapter two", "Stage done", "Ending"):
            Scene.objects.create(name=name, script="background sakura\nnarrator: Something happens.")

    def start(self):
        self.save = world.start(self.user, 1, SET)
        return self.save

    def fresh(self):
        self.save.refresh_from_db()
        for attr in ("_quests", "_quest_lookup"):
            self.save.__dict__.pop(attr, None)
        return self.save

    def win_a_duel(self, key):
        quest = Quest.objects.get(key=key)
        quests.tick(self.save, quest, "0.0", value=self.ruby.pk)
        world.changed(self.save, "quests")


class CheckTests(StoryBase):
    base = {"key": "s", "title": "S", "about": "x", "story": True,
            "stages": [{"text": "Go", "objectives": [{"do": "flag", "flag": "f", "text": "F"}]}], "endings": [{"key": "e", "title": "E"}]}

    def problems(self, **changes):
        return quests.check({**self.base, **changes})[1]

    def test_a_good_chapter(self):
        self.assertEqual(self.problems(chapter=1, scene="Opening"), [])

    def test_what_a_chapter_cannot_be(self):
        self.assertTrue(any("no giver" in p for p in self.problems(giver="Ruby")))
        self.assertTrue(any("can't gate a rank" in p for p in self.problems(window={})))
        self.assertTrue(any("chapter is a whole number" in p for p in self.problems(chapter=0)))
        two = [{"key": "a", "title": "A"}, {"key": "b", "title": "B"}]
        self.assertTrue(any("only one of a story chapter's endings" in p for p in self.problems(endings=two)))

    def test_its_scenes_have_to_exist(self):
        self.assertTrue(any("no scene called “Nope”" in p for p in self.problems(scene="Nope")))
        stage = {"text": "Go", "objectives": [{"do": "flag", "flag": "f", "text": "F"}], "scene": "Nope"}
        self.assertTrue(any("no scene called “Nope”" in p for p in self.problems(stages=[stage])))
        self.assertTrue(any("no scene called “Nope”" in p for p in self.problems(endings=[{"key": "e", "title": "E", "scene": "Nope"}])))

    def test_a_chapter_reads_back_as_written(self):
        stage = {"text": "Go", "objectives": [{"do": "flag", "flag": "f", "text": "F"}], "scene": "Stage done"}
        fields, _ = quests.check({**self.base, "chapter": 2, "scene": "Opening", "stages": [stage],
                                  "endings": [{"key": "e", "title": "E", "scene": "Ending"}]})
        quest = quests.save_quest(fields)
        again, problems = quests.check(quests.as_file(quest))
        self.assertEqual(problems, [])
        self.assertEqual(again["spec"], quest.spec)


class ChainTests(StoryBase):
    def test_the_first_chapter_begins_with_the_save_and_its_scene_waits_for_the_town(self):
        chapter("one", 1, scene="Opening")
        save = self.start()
        self.assertEqual(quests.status(save, "one"), "active")
        self.assertEqual(save.flags["scene"]["scene"], Scene.objects.get(name="Opening").pk)
        self.assertIn("Chapter 1: One", " ".join(item["text"] for item in save.quests.get("news", [])))
        self.assertTrue(world.town(save)["scene"]["auto"])  # plays on the first visit to the town

    def test_finishing_a_chapter_rewards_it_and_begins_the_next(self):
        chapter("one", 1)
        chapter("two", 2, requires=["one"], scene="Chapter two")
        save = self.start()
        self.assertEqual(quests.status(save, "two"), "")  # not before the first's done
        before = save.money
        self.win_a_duel("one")
        self.assertEqual(quests.status(save, "one"), "done")  # finished by itself: no one to hand it in to
        self.assertEqual(save.money - before, 100)
        self.assertEqual(quests.status(save, "two"), "active")
        self.assertEqual(save.flags["scene"]["scene"], Scene.objects.get(name="Chapter two").pk)

    def test_a_stage_and_an_ending_play_their_scenes_in_turn(self):
        stages = [{"text": "Win", "objectives": [{"do": "beat_different", "count": 1}], "scene": "Stage done"}]
        chapter("one", 1, scene="Opening", stages=stages, endings=[{"key": "done", "title": "Done", "scene": "Ending"}])
        save = self.start()
        self.win_a_duel("one")
        names = [Scene.objects.get(pk=item["scene"]).name for item in [save.flags["scene"], *save.flags.get("scene_queue", [])]]
        self.assertEqual(names, ["Opening", "Stage done", "Ending"])
        save.save()
        self.client.force_login(self.user)
        self.client.get(reverse("weiss:world_scene", args=[1]))
        self.client.post(reverse("weiss:world_scene_done", args=[1]), {"state": '{"flags": [], "buffs": []}'})  # watched to its end: the next comes up
        self.assertEqual(self.fresh().flags["scene"]["scene"], Scene.objects.get(name="Stage done").pk)

    def test_a_chapter_brings_whoever_it_names_into_town(self):
        others = [give_cpu(f"Duelist {n:02}", self.cards) for n in range(20)]
        for cpu in others:
            everywhere_rule(cpu, "cafe")
        save = self.start()
        later = next(pk for wave in save.roster["waves"][1:] for pk in wave)
        name = next(cpu.name for cpu in others + [self.ruby] if cpu.pk == later)
        chapter("meet", 1, stages=[{"text": "Beat them", "objectives": [{"do": "defeat", "cpus": [name]}]}])
        save = self.fresh()  # a new request, which sees the new chapter
        world.changed(save, "quests")
        self.assertEqual(quests.status(save, "meet"), "active")
        self.assertIn(later, roster.released(save))
        self.assertIn("come to town", " ".join(item["text"] for item in save.quests.get("news", [])))

    def test_a_chapter_is_never_offered(self):
        quest = chapter("one", 1)
        save = self.start()
        save.quests = {}
        self.assertFalse(quests.offerable(save, quest))

    def test_the_quest_log_shows_the_story_first(self):
        chapter("one", 1)
        chapter("two", 2, requires=["one"])
        save = self.start()
        self.win_a_duel("one")
        story = quests.journal(self.fresh())["story"]
        self.assertEqual([entry["key"] for entry in story], ["one", "two"])
        self.assertEqual(story[0]["chapter"], "Chapter 1")
        self.assertTrue(story[1]["stages"])  # the chapter under way, in full
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_quests", args=[1]))
        self.assertContains(page, "The story")
        self.assertContains(page, "Chapter 2")


class SceneQueueTests(StoryBase):
    def test_a_visit_scene_waits_its_turn_instead_of_being_skipped(self):
        save = self.start()
        world.queue_scene(save, "Opening")
        world.queue_scene(save, "Ending")
        self.assertEqual(save.flags["scene"]["scene"], Scene.objects.get(name="Opening").pk)
        self.assertEqual([item["scene"] for item in save.flags["scene_queue"]], [Scene.objects.get(name="Ending").pk])
        save.flags.pop("scene")
        world.next_scene(save)
        self.assertEqual(save.flags["scene"]["scene"], Scene.objects.get(name="Ending").pk)
        self.assertNotIn("scene_queue", save.flags)


class StoryFileTests(StoryBase):
    def story_file(self, **chapter_changes):
        return {"pack": "00_story", "cpus": [],
                "scenes": [{"name": "World: Story, Opening", "script": ["background sakura", "narrator: The town wakes up."]}],
                "story": [{"key": "story-1", "title": "A new town", "story": True, "chapter": 1, "about": "Find your feet.",
                           "scene": "World: Story, Opening",
                           "stages": [{"text": "Win a duel", "objectives": [{"do": "beat_different", "count": 1}]}],
                           "endings": [{"key": "done", "title": "Done"}], **chapter_changes}]}

    def test_a_story_file_is_imported_with_its_scenes(self):
        result = import_world_pack([self.story_file()])[0]
        self.assertEqual(result.problems, [])
        self.assertEqual(result.done, [("The story", "1 chapter")])
        quest = Quest.objects.get(key="story-1")
        self.assertTrue(quest.spec["story"])
        self.assertIsNone(quest.giver)
        self.assertTrue(Scene.objects.filter(name="World: Story, Opening").exists())

    def test_a_story_files_mistakes_are_named(self):
        result = import_world_pack([self.story_file(story=False)])[0]
        self.assertTrue(any("give it \"story\": true" in problem for problem in result.problems))
        self.assertFalse(Quest.objects.filter(key="story-1").exists())

    def test_the_built_story_checks_out(self):
        import json
        from pathlib import Path
        data = json.loads((Path(__file__).resolve().parent.parent / "world_pack" / "00_story.json").read_text(encoding="utf-8"))
        names = [line.split(" as ", 1)[1] for scene in data["scenes"] for line in scene["script"] if line.startswith("cast ") and "{mentor}" not in line]
        tutorial = data.get("tutorial") or {}  # and the tutorial's guides
        names += list(tutorial.get("guides", [])) + [who for lines in tutorial.get("lines", {}).values() for who in lines if who != "*"]
        result = import_world_pack([data], known=names)[0]  # checked against the CPUs its scenes cast, as the pack checker does
        self.assertEqual(result.problems, [])


# ---------------------------------------------------------------- Chapter 1's mechanics: the guide, an easy duel, a best friend

from .test_world_quests import QuestBase, make_quest, stage  # noqa: E402


class MentorTests(QuestBase):
    def finish(self, room, won):
        over = {"winner": str(room.host_id if won else room.guest_id), "loser": "x", "reason": "level", "rematch": []}
        room.state["game_over"] = over
        room.save(update_fields=["state"])
        world.game_finished(room, over)

    def choose_guide(self):
        script = "\n".join(["cast g0 as Ruby", "cast g1 as Cinder", "background sakura", "choice Who?",
                            "- Ruby (set mentor_g0)", "- Cinder (set mentor_g1)"])
        Scene.objects.create(name="Pick a guide", script=script)
        world.queue_scene(self.save, "Pick a guide")
        return world.scene_done(self.save, ["mentor_g0"], [])

    def test_a_scene_choice_makes_the_guide(self):
        done = self.choose_guide()
        self.assertEqual(self.save.flags["mentor"], self.ruby.pk)
        self.assertIn("mentor_chosen", self.save.flags["set"])
        self.assertIn("Ruby is your guide", done["rewards"])
        self.assertEqual(quests.mentor_name(self.save), "Ruby")

    def test_mentor_in_a_quest_is_the_guide(self):
        make_quest("lesson", self.cinder, stages=[stage({"do": "talk", "to": "{mentor}", "script": ["them: Hi."]})])
        self.choose_guide()
        save = self.fresh()
        objective = quests.quests(save)["lesson"].spec["stages"][0]["objectives"][0]
        self.assertEqual(objective["to"], "Ruby")
        self.assertEqual(Quest.objects.get(key="lesson").spec["stages"][0]["objectives"][0]["to"], "{mentor}")  # stored as written

    def test_a_scene_for_this_guide_comes_first(self):
        self.choose_guide()
        Scene.objects.create(name="Lesson", script="narrator: For any guide.")
        own = Scene.objects.create(name="Lesson (Ruby)", script="narrator: For Ruby.")
        world.queue_scene(self.save, "Lesson")
        self.assertEqual(self.save.flags["scene"]["scene"], own.pk)

    def test_a_scene_casts_the_guide_and_knows_the_save(self):
        self.choose_guide()
        Scene.objects.create(name="Guide talks", script="cast guide as {mentor}\nguide: Hello!")
        world.queue_scene(self.save, "Guide talks")
        self.save.save()
        self.client.force_login(self.user)
        page = self.client.get(reverse("weiss:world_scene", args=[1]))
        self.assertContains(page, "Ruby")
        self.assertContains(page, "has_mentor")

    def test_the_easy_duel_counts_win_or_lose(self):
        self.choose_guide()
        make_quest("spar", self.cinder, stages=[stage({"do": "duel", "cpu": "{mentor}", "model": "easy"})])
        save = self.fresh()
        world.quest_act(save, self.cinder.pk, "accept", "spar", {})
        save.today.pop("engaged", None)
        room = world.start_duel(save, self.ruby.pk)
        self.assertEqual(room.state["cpu_model"], "easy")  # the guide goes easy on you
        self.finish(room, won=False)
        self.assertEqual(quests.status(self.fresh(), "spar"), "settling")

    def test_a_best_friend_with_anyone(self):
        make_quest("friend", self.cinder, stages=[stage({"do": "rank", "rank": 5})])
        world.quest_act(self.save, self.cinder.pk, "accept", "friend", {})
        self.assertEqual(quests.describe(self.save, {"do": "rank", "rank": 5}), "Become Best friend with anyone")
        self.assertNotIn("has_best_friend", world.scene_flags(self.save))
        self.save.relations[str(self.ruby.pk)] = {"points": world.ranks()[5]["points"]}
        world.changed(self.save, "relations")
        self.assertEqual(quests.status(self.fresh(), "friend"), "settling")
        self.assertIn("has_best_friend", world.scene_flags(self.save))
