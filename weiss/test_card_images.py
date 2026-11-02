import io
import json
from unittest import mock

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from . import card_images
from .models import Card, CardPrice, CpuImage

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
EREN = {"name": "Eren Yeager", "names": ["Eren Yeager", "Eren"], "image": "https://art/eren.png"}
MIKASA = {"name": "Mikasa Ackerman", "names": ["Mikasa Ackerman"], "image": "https://art/mikasa.png"}
LEVI = {"name": "Levi", "names": ["Levi"], "image": "https://art/levi.png"}
CAST = [EREN, MIKASA, LEVI]
COMBO = '【AUTO】 【CXCOMBO】 When this card attacks, if "Outcry" is in your climax area, draw 1 card.'


def make(serial, name, **fields):
    return Card.objects.create(serial_number=serial, name=name, expansion=fields.pop("expansion", "Attack on Titan Vol.2"), expansion_id=1,
                               card_type=fields.pop("card_type", "Character"), **fields)


def post(**fields):
    return {"id": 1, "rating": "g", "file_url": "https://img/1.png", "file_ext": "png", "image_width": 800, "file_size": 1000, "score": 1,
            "tag_string": "1girl solo transparent_background", "tag_string_character": "levi_(shingeki_no_kyojin)", "tag_string_copyright": "shingeki_no_kyojin", **fields}


TAG = "levi_(shingeki_no_kyojin)"
SHOWS = {"attackontitan", "shingekinokyojin"}


class ArtChoiceTests(TestCase):
    def test_only_general_rated_images_are_asked_for(self):
        with mock.patch("weiss.card_images.get", return_value=(b"[]", "application/json")) as get:
            card_images.booru_posts("levi solo")
        self.assertIn("rating%3Ag", get.call_args.args[0])
        self.assertEqual(card_images.BOORU_RATING, "g")

    def test_any_other_rating_is_thrown_out_even_if_it_comes_back(self):
        answer = json.dumps([post(rating="s"), post(rating="q"), post(rating="e"), post(rating="g", id=2)]).encode()
        with mock.patch("weiss.card_images.get", return_value=(answer, "application/json")):
            self.assertEqual([p["id"] for p in card_images.booru_posts("levi solo")], [2])
        self.assertFalse(card_images.fits_art(post(rating="s"), TAG, SHOWS, False))

    def test_only_this_character_alone_from_this_show(self):
        self.assertTrue(card_images.fits_art(post(), TAG, SHOWS, False))
        self.assertFalse(card_images.fits_art(post(tag_string="2boys transparent_background"), TAG, SHOWS, False))
        self.assertFalse(card_images.fits_art(post(tag_string_character=f"{TAG} eren_yeager"), TAG, SHOWS, False))
        self.assertFalse(card_images.fits_art(post(tag_string_copyright="fear_&_hunger"), TAG, SHOWS, False))
        self.assertFalse(card_images.fits_art(post(image_width=40), TAG, SHOWS, False))
        self.assertTrue(card_images.fits_art(post(tag_string_character=f"{TAG} levi_(cleaning)_(shingeki_no_kyojin)"), TAG, SHOWS, False))

    @mock.patch("weiss.card_images.time.sleep")
    def test_it_looks_further_than_the_first_page(self, _):
        first = [post(id=n, tag_string_copyright="other_show") for n in range(100)]
        pages = {1: first, 2: [post(id=500)]}
        with mock.patch("weiss.card_images.booru_posts", side_effect=lambda tags, page=1: pages.get(page, [])), \
                mock.patch("weiss.card_images.download_image", return_value=(PNG, ".png", "image/png")):
            self.assertEqual(card_images.booru_art(TAG, SHOWS, False)[3], "https://danbooru.donmai.us/posts/500")

    def test_official_and_unofficial_are_kept_apart(self):
        official = post(tag_string="solo official_art")
        self.assertTrue(card_images.fits_art(official, TAG, SHOWS, True))
        self.assertFalse(card_images.fits_art(official, TAG, SHOWS, False))
        self.assertFalse(card_images.fits_art(post(), TAG, SHOWS, True))

    @mock.patch("weiss.card_images.time.sleep")
    def test_a_transparent_background_comes_first(self, _):
        plain = post(id=1, score=99, tag_string="solo")
        clear = post(id=2, score=1, file_url="https://img/2.png")
        with mock.patch("weiss.card_images.booru_posts", return_value=[plain, clear]), \
                mock.patch("weiss.card_images.download_image", return_value=(PNG, ".png", "image/png")) as download:
            found = card_images.booru_art(TAG, SHOWS, False)
        download.assert_called_once_with("https://img/2.png")
        self.assertEqual(found[3], "https://danbooru.donmai.us/posts/2")

    @mock.patch("weiss.card_images.time.sleep")
    def test_official_art_falls_back_on_the_wiki(self, _):
        with mock.patch("weiss.card_images.character_tag", return_value=None), mock.patch("weiss.card_images.fandom_image_url", return_value=None), \
                mock.patch("weiss.card_images.download_image", return_value=(PNG, ".png", "image/png")):
            art = card_images.character_art("Attack on Titan", ["Shingeki no Kyojin"], LEVI)
        self.assertEqual(art["official"][3], LEVI["image"])
        self.assertIsNone(art["unofficial"])

    @mock.patch("weiss.card_images.time.sleep")
    def test_a_tag_has_to_be_from_this_show(self, _):
        tags = json.dumps([{"name": "levi_(fear_&_hunger)"}, {"name": "leviathan_(nikke)"}, {"name": TAG}]).encode()
        with mock.patch("weiss.card_images.get", return_value=(tags, "application/json")), \
                mock.patch("weiss.card_images.booru_posts", side_effect=lambda q, page=1: [post(tag_string_copyright="fear_&_hunger")] if "fear" in q else [post()]):
            self.assertEqual(card_images.character_tag("Levi", SHOWS), TAG)


class ProductLookupTests(TestCase):
    def test_product_ids_come_from_each_group_found(self):
        with mock.patch("weiss.tcgcsv.find_groups", return_value=[({"groupId": 7}, 2)]), \
                mock.patch("weiss.tcgcsv.card_prices", return_value={"AOT/1": {"tcgplayer_product_id": 42}}) as prices:
            self.assertEqual(card_images.product_ids_for("Attack on Titan", ["AOT/1"]), {"AOT/1": 42})
        prices.assert_called_once_with(7)


class PoolMigrationTests(TransactionTestCase):
    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_each_cpus_image_moves_into_the_pool(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("weiss", "0013_arcade")])
        old = executor.loader.project_state([("weiss", "0013_arcade")]).apps.get_model("weiss", "CpuProfile")
        with_image = old.objects.create(name="Bot", image_key="weiss/cpu-images/1-abc.png")
        without = old.objects.create(name="Plain")
        executor = MigrationExecutor(connection)
        executor.migrate([("weiss", "0014_cpu_image_pool")])
        apps = executor.loader.project_state([("weiss", "0014_cpu_image_pool")]).apps
        profiles = apps.get_model("weiss", "CpuProfile").objects
        self.assertEqual(profiles.get(pk=with_image.pk).image.key, "weiss/cpu-images/1-abc.png")
        self.assertEqual(profiles.get(pk=with_image.pk).image.name, "Bot")
        self.assertIsNone(profiles.get(pk=without.pk).image)
        self.assertEqual(apps.get_model("weiss", "CpuImage").objects.count(), 1)


class WhoIsItAboutTests(TestCase):
    def test_the_show_from_the_set(self):
        self.assertEqual(card_images.series_title("Attack on Titan Vol.2"), "Attack on Titan")
        self.assertEqual(card_images.series_title("GODDESS OF VICTORY: NIKKE Vol. 2"), "GODDESS OF VICTORY: NIKKE")
        self.assertEqual(card_images.series_title("Persona 5"), "Persona 5")
        self.assertEqual(card_images.series_title("[EX] Premium Booster Persona 3 Reload™"), "Persona 3 Reload")
        self.assertEqual(card_images.series_title("[TD] Persona 5"), "Persona 5")
        self.assertEqual(card_images.series_title("Persona 4 ver.E"), "Persona 4")
        self.assertEqual(card_images.series_title("Premium Booster Attack on Titan"), "Attack on Titan")

    def test_a_short_title_doesnt_match_by_chance(self):
        self.assertFalse(card_images.from_the_show({"tag_string_copyright": "exia_the_game"}, {"ex"}))
        self.assertTrue(card_images.from_the_show({"tag_string_copyright": "persona_3 persona_3_reload"}, {"persona3reload"}))

    def test_wiki_addresses_narrow_down(self):
        self.assertEqual(card_images.fandom_slugs("Persona 3 Reload"), ["persona3reload", "persona3", "persona"])

    def test_names_in_the_order_given(self):
        found = card_images.characters_named("Mikasa and Eren, Together", CAST)
        self.assertEqual([c["name"] for c in found], ["Mikasa Ackerman", "Eren Yeager"])

    def test_part_of_a_name_must_be_a_whole_word(self):
        self.assertEqual(card_images.characters_named("Levitation", CAST), [])
        self.assertEqual([c["name"] for c in card_images.characters_named('"Cleanup" Levi', CAST)], ["Levi"])

    def test_a_card_naming_two_gets_both(self):
        card = make("A/1", "Eren & Mikasa")
        self.assertEqual([c["name"] for c in card_images.card_characters(card, CAST)], ["Eren Yeager", "Mikasa Ackerman"])

    def test_with_the_cast_unknown_the_cards_own_name_says(self):
        for name, expected in (('"Cleanup" Levi', ["Levi"]), ("“Cleanup” Levi", ["Levi"]), ("Levi: Cleanup", ["Levi"]), ("Cleaning Up, Levi", ["Levi"]),
                               ("Ann as PANTHER & Carmen", ["Ann"]), ("Simon & Nia", ["Simon", "Nia"]), ("Yosuke in Yukata", ["Yosuke"])):
            self.assertEqual(card_images.names_in_card(name), expected, name)

    def test_one_word_is_one_character(self):
        cast = [MIKASA, {"name": "Mikasa no Chichi", "names": ["Mikasa no Chichi"], "image": None}, EREN]
        self.assertEqual([c["name"] for c in card_images.characters_named('"To Seize Freedom" Mikasa', cast)], ["Mikasa Ackerman"])
        self.assertEqual([c["name"] for c in card_images.characters_named("Mikasa & Eren", cast)], ["Mikasa Ackerman", "Eren Yeager"])

    def test_a_protagonist_is_the_shows_lead(self):
        card = make("A/1", "Protagonist & Orpheus: Reload")
        orpheus = {"name": "Orpheus", "names": ["Orpheus"], "image": None}
        self.assertEqual([c["name"] for c in card_images.card_characters(card, [EREN, MIKASA, orpheus])], ["Eren Yeager", "Orpheus"])
        self.assertEqual([c["name"] for c in card_images.card_characters(card, [])], ["Protagonist", "Orpheus"])

    def test_spellings_of_a_long_vowel_match(self):
        self.assertTrue(card_images.names_match(["mitsuru", "kirijo"], "kirijou_mitsuru"))
        self.assertTrue(card_images.names_match(["ohno"], "ohno"))
        self.assertFalse(card_images.names_match(["mitsuru", "kirijo"], "mitsuru_(other)"))

    def test_a_show_it_doesnt_know_is_no_characters_and_it_tries_the_short_title(self):
        tried = []

        def answer(url, data=None, headers=None):
            tried.append(json.loads(data)["variables"]["title"])
            raise card_images.NotFound("HTTP 404")
        with mock.patch("weiss.card_images.get", side_effect=answer), mock.patch("weiss.card_images.time.sleep"):
            self.assertEqual(card_images.anilist_show("GODDESS OF VICTORY: NIKKE"), ([], []))
        self.assertEqual(tried, ["GODDESS OF VICTORY: NIKKE", "NIKKE"])

    def test_only_real_images_are_kept(self):
        with mock.patch("weiss.card_images.get", return_value=(b"<svg></svg>", "image/png")):
            self.assertIsNone(card_images.download_image("https://x"))
        with mock.patch("weiss.card_images.get", return_value=(PNG + b"\0" * card_images.MAX_IMAGE_BYTES, "image/png")):
            self.assertIsNone(card_images.download_image("https://x"))
        with mock.patch("weiss.card_images.get", return_value=(PNG, "text/html")):
            self.assertEqual(card_images.download_image("https://x")[1:], (".png", "image/png"))


@override_settings(AWS_S3_BUCKET="bucket")
@mock.patch("weiss.management.commands.find_card_images.time.sleep")
class CommandTests(TestCase):
    def run_it(self, *args):
        out = io.StringIO()
        call_command("find_card_images", "--delay", "0", *args, stdout=out, stderr=out)
        return out.getvalue()

    def test_a_card_borrows_another_printings_picture(self, _):
        make("AOT/1", "Levi", description="x", image_s3_key="weiss/1/AOT-1S.png")
        broken = make("AOT/2", "Levi", description="x")
        self.run_it("--skip-art")
        broken.refresh_from_db()
        self.assertEqual(broken.image_s3_key, "weiss/1/AOT-1S.png")

    def test_a_different_card_of_the_same_name_isnt_borrowed(self, _):
        make("AOT/1", "Levi", description="x", image_s3_key="k.png")
        other = make("AOT/2", "Levi", description="y")
        with mock.patch("weiss.card_images.product_ids_for", return_value={}):
            self.run_it("--skip-art")
        other.refresh_from_db()
        self.assertEqual(other.image_s3_key, "")

    def test_a_dead_link_falls_back_on_tcgplayer(self, _):
        card = make("AOT/3", "Eren", image_url="https://dead/x.png")
        CardPrice.objects.create(card=card, tcgplayer_product_id=42)
        def download(url):
            return (PNG, ".png", "image/png") if "42_in_1000x1000" in url else None
        with mock.patch("weiss.card_images.download_image", side_effect=download), mock.patch("weiss.card_images.product_ids_for", return_value={}), \
                mock.patch("weiss.management.commands.find_card_images.s3.upload") as upload:
            self.run_it("--skip-art")
        card.refresh_from_db()
        self.assertTrue(card.image_s3_key.endswith(".png"))
        self.assertIn("42_in_1000x1000", card.image_url)
        upload.assert_called_once()

    def test_a_working_picture_is_left_alone(self, _):
        card = make("AOT/3", "Eren", image_s3_key="k.png")
        with mock.patch("weiss.card_images.download_image") as download:
            self.run_it("--skip-art")
        download.assert_not_called()
        card.refresh_from_db()
        self.assertEqual(card.image_s3_key, "k.png")

    ART = {"official": (PNG, ".png", "image/png", "https://art/official"), "unofficial": (PNG, ".png", "image/png", "https://art/fan")}

    def test_a_dry_run_changes_nothing(self, _):
        card = make("AOT/4", "Eren & Mikasa", description=COMBO)
        with mock.patch("weiss.card_images.anilist_show", return_value=(CAST, [])), mock.patch("weiss.card_images.character_art", return_value=self.ART), \
                mock.patch("weiss.card_images.product_ids_for", return_value={}), \
                mock.patch("weiss.management.commands.find_card_images.s3.upload") as upload:
            output = self.run_it("--dry-run")
        upload.assert_not_called()
        self.assertEqual(CpuImage.objects.count(), 0)
        self.assertIn("Would add 4 avatar images", output)
        card.refresh_from_db()
        self.assertEqual(card.image_s3_key, "")

    def test_two_of_each_character_on_a_combo_card_once_each(self, _):
        make("AOT/4", "Eren", description=COMBO, image_s3_key="a.png")
        make("AOT/5", "Raging Eren", description=COMBO, image_s3_key="b.png")
        make("AOT/6", "Mikasa", description="Draw 1 card.", image_s3_key="c.png")  # no combo
        make("AOT/7", "Levi's Climax", description=COMBO, card_type="Climax", image_s3_key="d.png")
        with mock.patch("weiss.card_images.anilist_show", return_value=(CAST, [])), mock.patch("weiss.card_images.character_art", return_value=self.ART) as art, \
                mock.patch("weiss.management.commands.find_card_images.s3.upload") as upload:
            self.run_it("--skip-missing")
            self.run_it("--skip-missing")  # a second run finds them already there
        self.assertEqual(art.call_count, 1)
        self.assertEqual(upload.call_count, 2)
        self.assertEqual(sorted(CpuImage.objects.values_list("name", "kind")), [("Eren Yeager", "official"), ("Eren Yeager", "unofficial")])
        image = CpuImage.objects.get(kind="unofficial")
        self.assertTrue(image.key.startswith("weiss/cpu-images/pool-"))
        self.assertEqual((image.series, image.source_url), ("Attack on Titan", "https://art/fan"))

    def test_only_the_kind_missing_is_fetched_later(self, _):
        make("AOT/4", "Eren", description=COMBO, image_s3_key="a.png")
        with mock.patch("weiss.card_images.anilist_show", return_value=(CAST, [])), \
                mock.patch("weiss.card_images.character_art", return_value={"official": self.ART["official"], "unofficial": None}), \
                mock.patch("weiss.management.commands.find_card_images.s3.upload"):
            output = self.run_it("--skip-missing")
        self.assertIn("not found: Eren Yeager (unofficial)", output)
        with mock.patch("weiss.card_images.anilist_show", return_value=(CAST, [])), mock.patch("weiss.card_images.character_art", return_value=self.ART), \
                mock.patch("weiss.management.commands.find_card_images.s3.upload") as upload:
            self.run_it("--skip-missing")
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(CpuImage.objects.filter(kind="official").count(), 1)

    def test_a_series_can_be_chosen(self, _):
        make("AOT/4", "Eren", image_s3_key="a.png")
        make("NIK/4", "Rapi")
        output = self.run_it("--skip-art", "--series", "AOT")
        self.assertNotIn("NIK", output)
