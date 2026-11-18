"""World mode, phase 5: the staff pages (places, gifts and tastes, chatter) and world mode in CPU files."""
import json
import random
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from . import cpu_corpus, world
from .models import Chatter, CpuProfile, CpuSchedule, GiftItem, Scene, WorldPlace
from .test_cpu_corpus import SCRIPT, serial
from .test_express import make_series
from .world_staff_views import read_tags


class StaffPagesTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.client.force_login(self.staff)
        self.cpu = CpuProfile.objects.create(name="Cinder")

    def test_only_staff_see_them(self):
        self.client.force_login(User.objects.create_user("player", password="x"))
        for name in ("world_places", "world_gifts", "world_chatter"):
            with self.subTest(page=name):
                self.assertNotEqual(self.client.get(reverse(f"weiss:{name}")).status_code, 200)

    def test_the_world_tab_links_to_them(self):
        page = self.client.get(reverse("weiss:cpu_home") + "?tab=world")
        for name in ("world_places", "world_gifts", "world_chatter"):
            self.assertContains(page, reverse(f"weiss:{name}"))

    def test_places(self):
        url = reverse("weiss:world_places")
        self.assertContains(self.client.get(url), "Plaza")
        self.client.post(url, {"add": "1", "name": "The bar"})
        bar = WorldPlace.objects.get(key="the-bar")
        self.assertEqual((bar.backdrops, bar.order), (["default"] * 4, WorldPlace.objects.exclude(pk=bar.pk).order_by("-order")[0].order + 1))
        self.client.post(url, {"place": bar.pk, "name": "Cinder's bar", "backdrop_0": "dusk", "backdrop_1": "dusk", "backdrop_2": "night",
                               "backdrop_3": "night", "order": 3, "unlock_flag": "bar_open", "shop": "on"})
        bar.refresh_from_db()
        self.assertEqual((bar.name, bar.backdrops, bar.unlock_flag, bar.shop, bar.order), ("Cinder's bar", ["dusk", "dusk", "night", "night"], "bar_open", True, 3))
        response = self.client.post(url, {"place": bar.pk, "name": "x", **{f"backdrop_{t}": "lava" for t in range(4)}}, follow=True)
        self.assertContains(response, "Backdrops are")
        self.assertContains(self.client.post(url, {"add": "1", "name": "Bar", "key": "the-bar"}, follow=True), "already a place")
        CpuSchedule.objects.create(cpu=self.cpu, place=bar, days=[0], times=[0])
        self.assertContains(self.client.post(url, {"delete": bar.pk}, follow=True), "with its 1 schedule rule")
        self.assertFalse(CpuSchedule.objects.exists())

    def test_the_last_place_stays(self):
        WorldPlace.objects.exclude(key="plaza").delete()
        response = self.client.post(reverse("weiss:world_places"), {"delete": WorldPlace.objects.get().pk}, follow=True)
        self.assertContains(response, "at least one place")
        self.assertTrue(WorldPlace.objects.exists())

    def test_reading_tags(self):
        self.assertEqual(read_tags(" Sweet, drink ,, sweet, ice cream"), ["sweet", "drink", "ice-cream"])
        for text in ("café!", "a" * 21, ",".join(str(n) for n in range(11))):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    read_tags(text)

    def test_gifts(self):
        url = reverse("weiss:world_gifts")
        self.client.post(url, {"add": "1", "name": "Hot cocoa", "icon": "☕", "price": "140", "tags": "Sweet, drink", "about": "Warm."})
        cocoa = GiftItem.objects.get(key="hot-cocoa")
        self.assertEqual((cocoa.tags, cocoa.price), (["sweet", "drink"], 140))
        self.client.post(url, {"gift": cocoa.pk, "name": "Cocoa", "price": "160", "tags": "sweet", "order": "2"})
        cocoa.refresh_from_db()
        self.assertEqual((cocoa.name, cocoa.price, cocoa.tags, cocoa.key), ("Cocoa", 160, ["sweet"], "hot-cocoa"))
        self.assertContains(self.client.post(url, {"gift": cocoa.pk, "name": "Cocoa", "price": "0"}, follow=True), "price goes from")
        self.client.post(url, {"tastes": self.cpu.pk, "loves": "sweet", "likes": "drink, cards", "dislikes": ""})
        self.cpu.refresh_from_db()
        self.assertEqual(self.cpu.gift_tastes, {"loves": ["sweet"], "likes": ["drink", "cards"], "dislikes": []})
        self.assertContains(self.client.get(url), "loved by 1")
        response = self.client.post(url, {"tastes": self.cpu.pk, "loves": "sweet", "likes": "", "dislikes": "sweet"}, follow=True)
        self.assertContains(response, "two ways about sweet")
        self.client.post(url, {"delete": cocoa.pk})
        self.assertFalse(GiftItem.objects.filter(key="hot-cocoa").exists())

    def test_filling_in_tastes(self):
        CpuProfile.objects.update(gift_tastes={})
        self.assertContains(self.client.get(reverse("weiss:world_gifts")), "Give it starter tastes")
        self.client.post(reverse("weiss:world_gifts"), {"fill": "1"})
        self.cpu.refresh_from_db()
        self.assertEqual(self.cpu.gift_tastes, world.starter_tastes(self.cpu.pk))

    def test_chatter(self):
        self.client.post(reverse("weiss:world_chatter_new"), {"cpu": self.cpu.pk, "context": "greet"})
        line = Chatter.objects.get()
        self.assertEqual((line.cpu, line.context), (self.cpu, "greet"))
        edit = reverse("weiss:world_chatter_edit", args=[line.pk])
        page = self.client.get(edit)
        self.assertContains(page, "if rank &gt;= 2 goto close")  # the reference
        self.assertContains(page, "No mistakes.")
        self.client.post(edit, {"cpu": "", "context": "again", "min_rank": "2", "weight": "3", "script": "them: Hi.\r\nthem enters"})
        line.refresh_from_db()
        self.assertEqual((line.cpu, line.context, line.min_rank, line.weight, line.script), (None, "again", 2, 3, "them: Hi.\nthem enters"))
        listing = self.client.get(reverse("weiss:world_chatter") + "?cpu=any")
        self.assertContains(listing, "1 mistake")
        self.assertContains(self.client.get(reverse("weiss:world_chatter") + f"?cpu={self.cpu.pk}"), "No lines like that")
        checked = self.client.post(reverse("weiss:world_chatter_check"), {"script": "them: Hi.\nlabel x\nbackground night"}).json()
        self.assertEqual(checked["labels"], ["x"])
        self.assertEqual(checked["errors"][0][0], 3)
        self.assertContains(self.client.post(edit, {"context": "again", "min_rank": "9", "weight": "1", "script": "them: Hi."}, follow=True), "Ranks go from")
        self.client.post(reverse("weiss:world_chatter_delete", args=[line.pk]))
        self.assertFalse(Chatter.objects.exists())

    def test_a_rank_up_can_play_a_scene_instead(self):
        scene = Scene.objects.create(name="Cinder opens up", script="cast c as Cinder\nc: Hm.")
        line = Chatter.objects.create(context="rank_up", min_rank=1, script="them: Hi.")
        edit = reverse("weiss:world_chatter_edit", args=[line.pk])
        self.client.post(edit, {"context": "rank_up", "min_rank": "1", "weight": "1", "scene": scene.pk, "script": ""})
        line.refresh_from_db()
        self.assertEqual(line.scene, scene)
        self.assertContains(self.client.get(reverse("weiss:world_chatter")), "Plays the scene Cinder opens up")
        self.client.post(edit, {"context": "greet", "min_rank": "0", "weight": "1", "scene": scene.pk, "script": "them: Hi."})
        line.refresh_from_db()
        self.assertIsNone(line.scene)  # only a rank-up plays a scene


class WorldInCpuFilesTests(TestCase):
    def setUp(self):
        make_series()
        self.user = User.objects.create_superuser("staff", password="x")
        GiftItem.objects.get_or_create(key="iced-coffee", defaults={"name": "Iced coffee", "tags": ["drink"]})

    def cpu_file(self, world_part=None, name="Rapi"):
        return {"profile": {"name": name, "model": "standard"},
                "deck": {"name": f"{name}'s deck", "series": "TST", "anchors": [serial("Combo Red"), serial("Combo Blue")]},
                "scenes": [{"name": f"{name}: Hello", "script": SCRIPT}] if name == "Rapi" else [],
                **({"world": world_part} if world_part is not None else {})}

    WORLD = {"schedule": [{"place": "cafe", "days": [0, 1, 2], "times": [1, 2], "chance": 90, "priority": 1},
                          {"place": "beach", "days": [5, 6], "times": [2], "stake": 400}],
             "gift_tastes": {"loves": ["sweet"], "likes": ["drink"], "dislikes": ["spicy"]},
             "chatter": [{"context": "greet", "script": "them: Hi, {player}.\ngive gift iced-coffee"},
                         {"context": "rank_up", "min_rank": 2, "scene": "Rapi: Hello"}]}

    def test_a_cpu_files_world_is_made(self):
        profile, _ = cpu_corpus.import_cpu(self.cpu_file(self.WORLD), self.user, rng=random.Random(1))
        profile.refresh_from_db()
        rules = list(profile.schedule.order_by("-priority"))
        self.assertEqual([(r.place.key, r.days, r.times, r.chance, r.stake) for r in rules],
                         [("cafe", [0, 1, 2], [1, 2], 90, 0), ("beach", [5, 6], [2], 100, 400)])
        self.assertEqual(profile.gift_tastes, self.WORLD["gift_tastes"])
        lines = {line.context: line for line in profile.chatter.all()}
        self.assertEqual(lines["rank_up"].scene.name, "Rapi: Hello")  # a scene from the same file
        self.assertEqual(lines["greet"].min_rank, 0)

    def test_and_written_out_again(self):
        profile, _ = cpu_corpus.import_cpu(self.cpu_file(self.WORLD), self.user, rng=random.Random(1))
        record = cpu_corpus.export_profile(profile, cpu_corpus.scene_casts(), {})
        self.assertEqual(record["world"]["gift_tastes"], self.WORLD["gift_tastes"])
        self.assertEqual(record["world"]["schedule"][1], {"place": "beach", "days": [5, 6], "times": [2], "chance": 100,
                                                          "once_per_day": False, "priority": 0, "stake": 400})
        self.assertIn({"context": "rank_up", "min_rank": 2, "weight": 1, "script": "", "scene": "Rapi: Hello"}, record["world"]["chatter"])

    def test_everything_wrong_with_a_world_is_said(self):
        wrong = {"schedule": [{"place": "moon", "days": [7], "times": [], "chance": 0, "colour": "red"}],
                 "gift_tastes": {"loves": ["sweet"], "dislikes": ["sweet"]},
                 "chatter": [{"context": "brunch", "script": "them: Hi."}, {"context": "greet", "script": "them enters\ngive gift caviar"},
                             {"context": "greet", "scene": "Rapi: Hello"}, {"context": "again", "min_rank": 99, "script": "them: Hi."}],
                 "weather": "rain"}
        with self.assertRaises(cpu_corpus.CorpusError) as caught:
            cpu_corpus.import_cpu(self.cpu_file(wrong), self.user, rng=random.Random(1))
        text = "\n".join(caught.exception.problems)
        for expected in ("no such fields as weather", "no place “moon”", "days are", "times are", "chance goes", "no such fields as colour",
                         "sweet can only be in one list", "context must be one of", "no stage", "no gift called “caviar”",
                         "only a rank_up line can play a scene", "min_rank goes from"):
            self.assertIn(expected, text)
        self.assertFalse(CpuProfile.objects.exists())

    def test_no_world_is_fine(self):
        profile, _ = cpu_corpus.import_cpu(self.cpu_file(), self.user, rng=random.Random(1))
        self.assertFalse(profile.schedule.exists())

    def test_checked_offline_against_an_export(self):
        cpu_corpus.import_cpu(self.cpu_file(self.WORLD), self.user, rng=random.Random(1))
        with tempfile.TemporaryDirectory() as folder:
            call_command("export_cpu_corpus", "--out", folder, stdout=StringIO())
            info = json.loads((Path(folder) / "world.json").read_text(encoding="utf-8"))
            self.assertIn("cafe", [place["key"] for place in info["places"]])
            self.assertTrue(json.loads((Path(folder) / "chatter.json").read_text(encoding="utf-8")))
            self.assertIn("## World mode", (Path(folder) / "reference.md").read_text(encoding="utf-8"))
            corpus = cpu_corpus.load_corpus(Path(folder))
        world_part = {**self.WORLD, "chatter": [{"context": "rank_up", "min_rank": 1, "scene": "Rapi: Hello"},
                                                {"context": "greet", "script": "them: Hi.\ngive gift caviar"}]}
        problems = cpu_corpus.check_offline(self.cpu_file(world_part, name="Anis"), *corpus)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("caviar", problems[0])
        self.assertIn("before world mode", cpu_corpus.check_offline(self.cpu_file(world_part, name="Anis"), *corpus[:3])[-1])
