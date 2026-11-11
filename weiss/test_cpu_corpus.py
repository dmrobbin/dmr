import json
import random
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase

from . import buffs, cpu, cpu_corpus
from .cpu_views import deck_problem
from .models import Card, CardList, CpuProfile, Scene
from .test_express import make_series

SCRIPT = """cast rapi as Rapi
rapi enters left with slide
rapi: Ready, {player}?
choice Well?
- Always. (give lucky_pack)
- Not yet. -> later
end
label later
rapi (win): Then I'll wait.
"""


def serial(name):
    return Card.objects.get(name=name).serial_number


class CpuCorpusTests(TestCase):
    def setUp(self):
        make_series()
        self.user = User.objects.create_superuser("staff", password="x")

    def cpu_file(self, **changes):
        data = {"profile": {"name": "Rapi", "model": "focused", "aggression": 2, "boss": False, "intro_text": "Let's go.",
                            "player_win_text": "Nice work.", "player_lose_text": "Again?", "combo_text": "Full burst!"},
                "deck": {"name": "Rapi's deck", "series": "TST", "anchors": [serial("Combo Red"), serial("Combo Blue")]},
                "scenes": [{"name": "Rapi: Hello", "script": SCRIPT}]}
        for part, value in changes.items():
            data[part] = value if not isinstance(value, dict) else {**data[part], **value}
        return data

    def import_cpu(self, data, **options):
        return cpu_corpus.import_cpu(data, self.user, rng=random.Random(1), **options)

    def test_a_cpu_is_made_with_an_express_built_deck_and_its_scenes_but_not_finalized(self):
        profile, _ = self.import_cpu(self.cpu_file())
        profile.refresh_from_db()
        self.assertEqual((profile.name, profile.model, profile.aggression, profile.combo_text), ("Rapi", "focused", 2, "Full burst!"))
        self.assertFalse(profile.finalized)
        self.assertTrue(profile.deck.reserved_for_cpu)
        self.assertIsNone(deck_problem(profile.deck))
        self.assertEqual(profile.deck.express["anchors"], [Card.objects.get(name="Combo Red").pk, Card.objects.get(name="Combo Blue").pk])
        self.assertEqual(Scene.objects.get().name, "Rapi: Hello")

    def test_everything_wrong_is_said_at_once_and_nothing_is_saved(self):
        data = self.cpu_file(profile={"model": "genius", "aggression": 9, "intro_text": "x" * 2000},
                             deck={"anchors": [serial("Combo Red"), "TST/S1-001"]})
        with self.assertRaises(cpu_corpus.CorpusError) as raised:
            self.import_cpu(data)
        problems = "\n".join(raised.exception.problems)
        for wanted in ("model", "aggression", "intro_text", "TST/S1-001"):
            self.assertIn(wanted, problems)
        self.assertFalse(CpuProfile.objects.exists() or CardList.objects.exists() or Scene.objects.exists())

    def test_a_scene_that_wont_compile_undoes_the_whole_cpu(self):
        data = self.cpu_file(scenes=[{"name": "Broken", "script": "cast rapi as Rapi\nanis: Who cast me?\nbackground moon"}])
        with self.assertRaises(cpu_corpus.CorpusError) as raised:
            self.import_cpu(data)
        self.assertEqual(len(raised.exception.problems), 2)
        self.assertIn("line 2", raised.exception.problems[0])
        self.assertFalse(CpuProfile.objects.exists() or CardList.objects.exists() or Scene.objects.exists())

    def test_a_dry_run_checks_everything_and_saves_nothing(self):
        profile, _ = self.import_cpu(self.cpu_file(), dry_run=True)
        self.assertEqual(profile.name, "Rapi")
        self.assertFalse(CpuProfile.objects.exists() or CardList.objects.exists() or Scene.objects.exists())

    def test_names_already_taken_are_refused(self):
        self.import_cpu(self.cpu_file())
        with self.assertRaises(cpu_corpus.CorpusError) as raised:
            self.import_cpu(self.cpu_file(profile={"name": "rapi"}))
        self.assertEqual(len(raised.exception.problems), 2)  # the CPU and the scene
        self.assertEqual(CpuProfile.objects.count(), 1)

    def test_an_exported_cpu_imports_back_with_the_same_deck(self):
        original, _ = self.import_cpu(self.cpu_file())
        record = cpu_corpus.export_profile(original, cpu_corpus.scene_casts(), {})
        self.assertEqual([s["name"] for s in record["scenes"]], ["Rapi: Hello"])
        self.assertLessEqual({"Combo Red", "Combo Blue"}, {c["name"] for c in record["context"]["key_cards"]})
        record["profile"]["name"] = "Rapi again"
        record["scenes"] = []
        copy, _ = self.import_cpu(record)
        cards = lambda deck: sorted(deck.entries.values_list("card__serial_number", "quantity"))
        self.assertEqual(cards(copy.deck), cards(original.deck))

    def test_anchors_show_their_climaxes_and_who_uses_them(self):
        self.import_cpu(self.cpu_file())
        anchors = {a["name"]: a for a in cpu_corpus.anchor_report("TST")}
        self.assertEqual(set(anchors), {"Combo Red", "Combo Blue", "Combo Naming"})
        self.assertEqual(anchors["Combo Red"]["used_by"], ["Rapi"])
        self.assertEqual([c["name"] for c in anchors["Combo Red"]["combos_with"]], ["BIG"])
        out = StringIO()
        call_command("list_cpu_anchors", "TST", "--unused", stdout=out)
        self.assertNotIn("Combo Red", [a["name"] for a in json.loads(out.getvalue())])

    def test_the_reference_covers_every_model_and_buff(self):
        text = cpu_corpus.reference()
        for name in [*cpu.MODELS, *buffs.BUFFS]:
            self.assertIn(f"`{name}`", text)

    def test_the_commands_write_the_corpus_and_read_a_cpu_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new.json"
            path.write_text(json.dumps(self.cpu_file()), encoding="utf-8")
            call_command("import_cpu", str(path), "--seed", "1", stdout=StringIO())
            call_command("export_cpu_corpus", "--out", folder, stdout=StringIO())
            self.assertTrue((Path(folder) / "cpus" / "rapi.json").exists())
            self.assertIn("Rapi: Hello", (Path(folder) / "scenes.json").read_text(encoding="utf-8"))
            with self.assertRaises(CommandError):  # the second time, the names are taken
                call_command("import_cpu", str(path), stdout=StringIO(), stderr=StringIO())
