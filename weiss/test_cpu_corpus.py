import io
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

    def test_a_new_cpu_is_checked_against_an_export_without_its_database(self):
        self.import_cpu(self.cpu_file(profile={"name": "Anis"}, scenes=[]))
        with tempfile.TemporaryDirectory() as folder:
            call_command("export_cpu_corpus", "--out", folder, stdout=StringIO())
            self.assertTrue((Path(folder) / "anchors" / "TST.json").exists())
            corpus = cpu_corpus.load_corpus(Path(folder))
        CpuProfile.objects.all().delete()  # what's checked is the export, not the database
        pair = self.cpu_file(scenes=[{"name": "Rapi/Anis", "script": "cast rapi as Rapi\ncast anis as Anis\nanis: Hi.\nrapi: Hello.",
                                      "infinite_event": True}])
        self.assertEqual(cpu_corpus.check_offline(pair, *corpus), [])
        wrong = self.cpu_file(profile={"name": "anis"}, deck={"anchors": [serial("Combo Red"), "TST/S1-001"]},
                              scenes=[{"name": "Bad", "script": "cast neon as Neon\nneon: Hi."}])
        problems = cpu_corpus.check_offline(wrong, *corpus)
        self.assertEqual(len(problems), 4, problems)  # the taken name, the anchor, and the unknown CPU cast and speaking
        self.assertIn("Neon", problems[2])

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


class CpuDeckAccessTests(TestCase):
    """An imported CPU's deck belongs to the superuser import_cpu ran as: any staff member can still open and edit it."""

    def setUp(self):
        from django.contrib.auth.models import Group
        from core.access import WEISS_GROUP
        group = Group.objects.get_or_create(name=WEISS_GROUP)[0]
        self.owner = User.objects.create_superuser("importer", password="x")
        self.staff = User.objects.create_user("staff", password="x", is_staff=True)
        self.player = User.objects.create_user("player", password="x")
        for user in (self.owner, self.staff, self.player):
            user.groups.add(group)
        self.cpu_deck = CardList.objects.create(user=self.owner, name="CPU deck", reserved_for_cpu=True)
        self.private = CardList.objects.create(user=self.owner, name="Mine")

    def get(self, user, deck):
        from django.urls import reverse
        self.client.force_login(user)
        return self.client.get(reverse("weiss:list", args=[deck.pk])).status_code

    def test_staff_open_any_cpu_deck(self):
        self.assertEqual(self.get(self.staff, self.cpu_deck), 200)

    def test_staff_start_editing_any_cpu_deck(self):
        from django.urls import reverse
        self.client.force_login(self.staff)
        self.client.post(reverse("weiss:list_edit", args=[self.cpu_deck.pk]))
        self.assertEqual(self.client.session.get("weiss_editing_list"), self.cpu_deck.pk)

    def test_but_not_someone_elses_own_list(self):
        self.assertEqual(self.get(self.staff, self.private), 404)

    def test_players_cant_open_cpu_decks(self):
        self.assertEqual(self.get(self.player, self.cpu_deck), 404)


class CpuBatchImportTests(TestCase):
    """Several CPU files in one go, from the command or the CPU page's Import tab: their scenes can cast each other."""

    def setUp(self):
        from django.contrib.auth.models import Group
        from core.access import WEISS_GROUP
        make_series()
        self.user = User.objects.create_user("staff", password="x", is_staff=True)
        self.user.groups.add(Group.objects.get_or_create(name=WEISS_GROUP)[0])
        self.client.force_login(self.user)

    def cpu_file(self, name, partner=None):
        script = f"cast me as {name}\n" + (f"cast them as {partner}\nthem: Hello.\n" if partner else "") + "me: Hi."
        return {"profile": {"name": name, "intro_text": "Hi."},
                "deck": {"series": "TST", "anchors": [serial("Combo Red"), serial("Combo Blue")]},
                "scenes": [{"name": f"{name} meets {partner or 'nobody'}", "script": script, "infinite_event": True}]}

    def upload(self, *files, **extra):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse
        uploads = [SimpleUploadedFile(f"{data['profile']['name'].lower()}.json", json.dumps(data).encode(), "application/json") for data in files]
        return self.client.post(reverse("weiss:cpu_import"), {"step": "check", "files": uploads, **extra})

    def test_files_in_a_batch_can_cast_each_other_whatever_their_order(self):
        # The first file's scene casts a CPU that only the second file makes.
        results = cpu_corpus.import_cpus([self.cpu_file("Joker", "Batman"), self.cpu_file("Batman")], self.user, seed=1)
        self.assertEqual([r.problems for r in results], [[], []])
        self.assertEqual(sorted(CpuProfile.objects.values_list("name", flat=True)), ["Batman", "Joker"])
        self.assertEqual(Scene.objects.count(), 2)

    def test_one_bad_file_keeps_the_whole_batch_out(self):
        bad = self.cpu_file("Batman")
        bad["profile"]["model"] = "genius"
        results = cpu_corpus.import_cpus([self.cpu_file("Joker", "Batman"), bad], self.user, seed=1)
        self.assertIn("model", results[1].problems[0])
        self.assertFalse(CpuProfile.objects.exists() or CardList.objects.exists() or Scene.objects.exists())

    def test_two_files_cant_share_a_scene_name(self):
        twin = self.cpu_file("Batman")
        twin["scenes"][0]["name"] = "Joker meets nobody"
        results = cpu_corpus.import_cpus([self.cpu_file("Joker"), twin], self.user, seed=1, dry_run=True)
        self.assertIn("another file", results[1].problems[0])

    def test_the_command_imports_files_together(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = []
            for data in (self.cpu_file("Joker", "Batman"), self.cpu_file("Batman")):
                paths.append(Path(folder) / f"{data['profile']['name']}.json")
                paths[-1].write_text(json.dumps(data), encoding="utf-8")
            call_command("import_cpu", *map(str, paths), "--user", "staff", "--dry-run", stdout=StringIO())
            self.assertFalse(CpuProfile.objects.exists())
            call_command("import_cpu", *map(str, paths), "--user", "staff", "--seed", "1", stdout=StringIO())
        self.assertEqual(CpuProfile.objects.count(), 2)

    def test_a_check_saves_nothing_and_its_import_builds_the_decks_it_showed(self):
        page = self.upload(self.cpu_file("Joker", "Batman"), self.cpu_file("Batman"))
        self.assertEqual(page.status_code, 200)
        self.assertTrue(page.context["ready"])
        self.assertFalse(CpuProfile.objects.exists() or CardList.objects.exists() or Scene.objects.exists())
        checked = [[(card.serial_number, n) for card, n in entry["result"].cards] for entry in page.context["batch"]]
        self.assertContains(page, "Import 2 CPUs")
        from django.urls import reverse
        form = {"step": "import", "seed": page.context["seed"],
                "name": [e["name"] for e in page.context["batch"]], "text": [e["text"] for e in page.context["batch"]]}
        done = self.client.post(reverse("weiss:cpu_import"), form)
        self.assertTrue(done.context["imported"])
        made = [[(card.serial_number, n) for card, n in entry["result"].cards] for entry in done.context["batch"]]
        self.assertEqual(made, checked)
        self.assertFalse(CpuProfile.objects.filter(finalized=True).exists())
        self.assertEqual(CpuProfile.objects.get(name="Joker").deck.user, self.user)
        self.assertContains(done, r"shortlist_renders --cpu corpus\new\joker.json corpus\new\batman.json")

    def test_a_check_with_problems_offers_no_import(self):
        page = self.upload(self.cpu_file("Joker", "Nobody"))
        self.assertFalse(page.context["ready"])
        self.assertContains(page, "Nobody")
        self.assertNotContains(page, "Import 1 CPU")

    def test_a_file_that_isnt_json_is_refused(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse
        page = self.client.post(reverse("weiss:cpu_import"), {"step": "check", "files": [SimpleUploadedFile("x.json", b"{nope")]}, follow=True)
        self.assertContains(page, "not JSON")

    def test_the_export_downloads_as_a_zip(self):
        import zipfile
        from django.urls import reverse
        cpu_corpus.import_cpus([self.cpu_file("Batman")], self.user, seed=1)
        response = self.client.get(reverse("weiss:cpu_corpus_download"))
        self.assertEqual(response["Content-Type"], "application/zip")
        names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
        self.assertLessEqual({"cpus/batman.json", "scenes.json", "reference.md", "anchors/TST.json"}, set(names))

    def test_only_staff_can_import_or_download(self):
        from django.urls import reverse
        player = User.objects.create_user("player", password="x")
        player.groups.add(*self.user.groups.all())
        self.client.force_login(player)
        self.assertEqual(self.client.get(reverse("weiss:cpu_corpus_download")).status_code, 403)
        self.assertEqual(self.upload(self.cpu_file("Batman")).status_code, 403)
        self.assertFalse(CpuProfile.objects.exists())
