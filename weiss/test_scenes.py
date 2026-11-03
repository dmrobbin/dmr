from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from core.access import WEISS_GROUP

from . import scenes
from .models import CpuImage, CpuProfile, Scene

SCRIPT = """# Rapi meets the player
cast rapi as Rapi
cast anis as "Anis"

label start
background dusk
rapi enters left with slide
anis enters far-right
rapi: Commander {player}!
rapi bounces
anis (lose): Hi!
narrator: The wind picks up.
choice What do you say?
- Hello. -> friendly (set polite)
- ...
anis shakes
goto done

label friendly
if polite goto done
rapi shows win
rapi moves center
rapi turns around
rapi dims
rapi brightens
screen black
wait 1.5
screen clear
unset polite
rapi exits right with fade

label done
end
"""


def compile_with(script, **cast):
    """Compile against these CPUs (name: profile) instead of the database."""
    found = {name.lower(): profile for name, profile in cast.items()}
    return scenes.compile_scene(script, lambda who: (found.get(who.strip('"').lower()), None if who.strip('"').lower() in found else f"No {who}."))


class CompileTests(TestCase):
    def setUp(self):
        self.rapi = CpuProfile.objects.create(name="Rapi")
        self.anis = CpuProfile.objects.create(name="Anis")

    def test_a_whole_scene(self):
        scene, errors = scenes.compile_scene(SCRIPT)
        self.assertEqual(errors, [])
        self.assertEqual(scene["cast"], {"rapi": self.rapi, "anis": self.anis})
        steps = scene["steps"]
        self.assertEqual([s["do"] for s in steps], [
            "background", "enter", "enter", "say", "animate", "say", "say", "choice", "animate", "goto",
            "if", "show", "move", "turn", "dim", "brighten", "screen", "wait", "screen", "unset", "exit", "end"])
        self.assertEqual(scene["labels"], {"start": 0, "friendly": 10, "done": 21})
        self.assertEqual(steps[1], {"line": 7, "do": "enter", "who": "rapi", "at": "left", "how": "slide"})
        self.assertEqual(steps[2]["at"], "far-right")
        self.assertEqual(steps[2]["how"], "fade")  # the default way in
        self.assertEqual(steps[3], {"line": 9, "do": "say", "who": "rapi", "text": "Commander {player}!"})
        self.assertEqual(steps[5]["expression"], "lose")
        self.assertEqual(steps[6]["who"], None)  # the narrator
        self.assertEqual(steps[7]["prompt"], "What do you say?")
        self.assertEqual(steps[7]["options"], [{"text": "Hello.", "goto": "friendly", "set": "polite"}, {"text": "...", "goto": None}])
        self.assertEqual(steps[10], {"line": 20, "do": "if", "flag": "polite", "not": False, "label": "done"})
        self.assertEqual(steps[17]["seconds"], 1.5)
        self.assertEqual(steps[20], {"line": 30, "do": "exit", "who": "rapi", "at": "right", "how": "fade"})

    def test_every_animation_in_the_present_tense_or_not(self):
        for animation in scenes.ACTIONS:
            for verb in (animation, animation + ("es" if animation.endswith("sh") else "s")):
                scene, errors = compile_with(f"cast rapi as Rapi\nrapi {verb}", Rapi=self.rapi)
                self.assertEqual(errors, [], verb)
                self.assertEqual(scene["steps"][0]["animation"], animation)

    def test_mistakes_are_found_by_line(self):
        script = "\n".join([
            "cast rapi as Rapi",
            "cast ghost as Nobody",
            "rapi enters upstairs",
            "rapi enters left with teleport",
            "anis: hi",
            "rapi (angry): hi",
            "rapi juggles",
            "goto nowhere",
            "choice Pick",
            "background moon",
            "- stray option",  # after a choice with no options? no: after background, so it's stray
            "screen explode",
            "label a",
            "label a",
            "this is not a line",
            "cast late as Rapi",
        ])
        errors = dict(scenes.compile_scene(script)[1])
        self.assertIn("Nobody", errors[2])
        self.assertIn("Places are", errors[3])
        self.assertIn("Ways in", errors[4])
        self.assertIn("Nobody's cast as “anis”", errors[5])
        self.assertIn("Pictures are", errors[6])
        self.assertIn("juggles", errors[7])
        self.assertIn("no label called “nowhere”", errors[8])
        self.assertIn("at least one option", errors[9])
        self.assertIn("Backgrounds are", errors[10])
        self.assertIn("straight after a choice", errors[11])
        self.assertIn("Screen effects", errors[12])
        self.assertIn("already a label", errors[14])
        self.assertIn("don't understand", errors[15])
        self.assertIn("at the top", errors[16])

    def test_a_cpu_by_number_and_names_shared(self):
        CpuProfile.objects.create(name="Rapi")
        scene, errors = scenes.compile_scene(f"cast a as #{self.anis.pk}\ncast b as Rapi\na: hi")
        self.assertEqual(scene["cast"]["a"], self.anis)
        self.assertIn("More than one CPU profile is called “Rapi”", errors[0][1])

    def test_an_empty_scene(self):
        self.assertEqual(scenes.compile_scene("# just notes\n\n")[1], [(1, "Nothing happens in this scene yet.")])

    def test_the_payload_has_each_actors_pictures(self):
        self.rapi.image = CpuImage.objects.create(key="cpu/rapi.png")
        self.rapi.player_win_image = CpuImage.objects.create(key="cpu/rapi-sad.png")
        self.rapi.save()
        scene, _ = scenes.compile_scene(SCRIPT)
        payload = scenes.scene_payload(scene, "Hello")
        self.assertEqual(payload["title"], "Hello")
        self.assertEqual(set(payload["cast"]["rapi"]["images"]), {"main", "intro", "win", "lose"})  # the main one stands in for intro and lose
        self.assertIn("rapi-sad.png", payload["cast"]["rapi"]["images"]["win"])
        self.assertEqual(payload["cast"]["anis"]["images"], {})  # no pictures: the player shows its avatar or a letter
        self.assertEqual(payload["cast"]["anis"]["name"], "Anis")

    def test_the_player_is_always_in_the_cast(self):
        scene, errors = scenes.compile_scene("cast rapi as Rapi\nplayer enters left with slide\nplayer: I'm here.\nplayer bounces\nrapi: Good.")
        self.assertEqual(errors, [])
        self.assertEqual(scene["steps"][0], {"line": 2, "do": "enter", "who": "player", "at": "left", "how": "slide"})
        self.assertEqual(scene["steps"][1], {"line": 3, "do": "say", "who": "player", "text": "I'm here."})
        errors = dict(scenes.compile_scene("cast player as Rapi\nplayer (win): Hm.\nplayer shows lose\nrapi: x")[1])
        self.assertIn("already taken", errors[1])
        self.assertIn("one picture", errors[2])
        self.assertIn("one picture", errors[3])

    def test_the_player_in_the_payload_is_whoever_is_watching(self):
        from django.contrib.auth.models import User
        from .models import Card, PlayerProfile
        viewer = User.objects.create_user("daryl", password="x")
        card = Card.objects.create(serial_number="T/1", name="Rapi", expansion="E", expansion_id=1)
        PlayerProfile.objects.create(user=viewer, avatar_card=card)
        scene, _ = scenes.compile_scene("player: Hi.")
        player = scenes.scene_payload(scene, viewer=viewer)["cast"]["player"]
        self.assertEqual((player["name"], player["player"], player["images"]), ("daryl", True, {}))
        self.assertIn(f"/cards/{card.pk}/image/", player["avatar"]["image"])
        nobody = scenes.scene_payload(scene)["cast"]["player"]
        self.assertEqual((nobody["name"], nobody["avatar"]), ("You", None))
        self.assertEqual(scenes.cast_name(CpuProfile(pk=4, name="Player One")), "cpu4")

    def test_cast_names(self):
        self.assertEqual(scenes.cast_name(self.rapi), "rapi")
        self.assertEqual(scenes.cast_name(CpuProfile(pk=7, name="“Glass Slippers” Cinderella")), "glass")
        self.assertEqual(scenes.cast_name(CpuProfile(pk=7, name="2B")), "cpu7")

    def test_the_starter_script_compiles(self):
        self.assertEqual(scenes.compile_scene(scenes.starter_script([self.rapi]))[1], [])


class ScenePageTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.player = User.objects.create_user("player", password="x")
        self.player.groups.add(Group.objects.get_or_create(name=WEISS_GROUP)[0])
        CpuProfile.objects.create(name="Rapi")
        CpuProfile.objects.create(name="Anis")
        self.client.force_login(self.staff)

    def test_staff_only(self):
        scene = Scene.objects.create(name="S", script=SCRIPT)
        self.client.force_login(self.player)
        for url in (reverse("weiss:cpu_scene_edit", args=[scene.pk]), reverse("weiss:cpu_scene_play", args=[scene.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(reverse("weiss:cpu_scene_create"), {"name": "x"}).status_code, 403)

    def test_creating_one_starts_from_an_example(self):
        response = self.client.post(reverse("weiss:cpu_scene_create"), {"name": "Welcome"})
        scene = Scene.objects.get(name="Welcome")
        self.assertRedirects(response, reverse("weiss:cpu_scene_edit", args=[scene.pk]))
        self.assertIn("cast them as Anis", scene.script)  # the first CPU, by name
        page = self.client.get(reverse("weiss:cpu_scene_edit", args=[scene.pk]))
        self.assertContains(page, "No mistakes.")
        self.assertContains(page, 'data-insert="cast rapi as Rapi&#10;"')
        self.assertContains(self.client.get(reverse("weiss:cpu_home")), "Welcome")

    def test_saving_keeps_a_script_with_mistakes(self):
        scene = Scene.objects.create(name="S", script=SCRIPT)
        response = self.client.post(reverse("weiss:cpu_scene_edit", args=[scene.pk]), {"name": "S2", "script": "cast x as Nobody\r\nx: hi", "then": "play"})
        self.assertRedirects(response, reverse("weiss:cpu_scene_edit", args=[scene.pk]))  # not played: it has mistakes
        scene.refresh_from_db()
        self.assertEqual((scene.name, scene.script), ("S2", "cast x as Nobody\nx: hi"))
        self.assertContains(self.client.get(reverse("weiss:cpu_scene_edit", args=[scene.pk])), "2 mistakes")
        # And it can't be played until they're fixed.
        self.assertRedirects(self.client.get(reverse("weiss:cpu_scene_play", args=[scene.pk])), reverse("weiss:cpu_scene_edit", args=[scene.pk]))

    def test_save_and_play(self):
        scene = Scene.objects.create(name="S", script="")
        response = self.client.post(reverse("weiss:cpu_scene_edit", args=[scene.pk]), {"name": "S", "script": SCRIPT, "then": "play"})
        self.assertRedirects(response, reverse("weiss:cpu_scene_play", args=[scene.pk]))
        page = self.client.get(reverse("weiss:cpu_scene_play", args=[scene.pk]), {"from": "friendly"})
        self.assertEqual(page.context["payload"]["labels"], {"start": 0, "friendly": 10, "done": 21})
        self.assertEqual(page.context["start"], "friendly")
        self.assertContains(page, "weiss/scene.js")
        self.assertContains(page, 'playerName: "staff"')

    def test_checking_as_it_is_typed(self):
        scene = Scene.objects.create(name="S", script=SCRIPT)
        data = self.client.post(reverse("weiss:cpu_scene_check", args=[scene.pk]), {"script": "cast rapi as Rapi\nlabel go\nrapi waves"}).json()
        self.assertEqual(data["labels"], ["go"])
        self.assertEqual(data["errors"][0][0], 3)
        scene.refresh_from_db()
        self.assertEqual(scene.script, SCRIPT)  # checking doesn't save

    def test_names_are_unique_and_deleting(self):
        scene = Scene.objects.create(name="S", script=SCRIPT)
        Scene.objects.create(name="Taken")
        self.client.post(reverse("weiss:cpu_scene_create"), {"name": "Taken"})
        self.assertEqual(Scene.objects.filter(name="Taken").count(), 1)
        self.client.post(reverse("weiss:cpu_scene_edit", args=[scene.pk]), {"name": "Taken", "script": SCRIPT})
        scene.refresh_from_db()
        self.assertEqual(scene.name, "S")
        self.client.post(reverse("weiss:cpu_scene_delete", args=[scene.pk]))
        self.assertFalse(Scene.objects.filter(pk=scene.pk).exists())
