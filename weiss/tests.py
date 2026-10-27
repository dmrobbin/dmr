from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Card, CardPrice
from .scraper import expansion_serials, parse_card

TESTDATA = Path(__file__).parent / "testdata"


def page(name):
    return BeautifulSoup((TESTDATA / name).read_text(encoding="utf-8"), "html.parser")


def results_page(*serials):
    return BeautifulSoup("".join(f'<li><p class="number">{s}</p></li>' for s in serials), "html.parser")


class ParseCardTests(TestCase):
    def test_character_card(self):
        card = parse_card(page("card_character.html"))
        self.assertEqual(card["serial_number"], "NIK/S135-E001S")
        self.assertEqual(card["name"], "Elegg: Boom and Shock")
        self.assertEqual(card["expansion"], "GODDESS OF VICTORY: NIKKE Vol.2")
        self.assertEqual(card["expansion_id"], 290)
        self.assertEqual(card["traits"], "NIKKE・Electric Shock")
        self.assertEqual(card["card_type"], "Character")
        self.assertEqual(card["rarity"], "SR⁂")
        self.assertEqual(card["side"], "Schwarz")
        self.assertEqual(card["color"], "Yellow")
        self.assertEqual((card["level"], card["cost"], card["power"], card["soul"]), (1, 0, 2500, 1))
        self.assertEqual(card["trigger"], "soul")
        self.assertTrue(card["description"].startswith("【AUTO】 At the beginning of your climax phase"))
        self.assertIn("\n【AUTO】 【CXCOMBO】", card["description"])
        self.assertEqual(card["flavor_text"], "")
        self.assertEqual(card["image_url"], "https://en.ws-tcg.com/wordpress/wp-content/images/cardimages/NIK/S135-E001S.png")

    def test_climax_card_has_no_stats_and_icons_in_text(self):
        card = parse_card(page("card_climax.html"))
        self.assertEqual(card["card_type"], "Climax")
        self.assertEqual(card["traits"], "")
        self.assertEqual((card["level"], card["cost"], card["power"], card["soul"]), (None, None, None, None))
        self.assertEqual(card["trigger"], "comeback")
        self.assertIn("([comeback]: When this card triggers", card["description"])

    def test_missing_card_returns_none(self):
        self.assertIsNone(parse_card(BeautifulSoup("<main></main>", "html.parser")))


class ExpansionSerialsTests(TestCase):
    def test_reads_pages_until_one_is_empty(self):
        pages = [results_page("A-001", "A-002"), results_page("A-003"), results_page()]
        with patch("weiss.scraper.fetch_html", side_effect=pages) as fetch_html, patch("weiss.scraper.time.sleep"):
            self.assertEqual(expansion_serials(290), ["A-001", "A-002", "A-003"])
        self.assertEqual(fetch_html.call_args_list[1].args[1]["page"], 2)


@override_settings(AWS_S3_BUCKET="my-bucket")
class FetchCardsCommandTests(TestCase):
    def setUp(self):
        self.fake_s3 = MagicMock()
        for target, value in [
            ("core.s3.boto3.client", self.fake_s3),
            ("weiss.management.commands.fetch_cards.time.sleep", None),
            ("weiss.management.commands.fetch_cards.fetch", (b"PNGDATA", "image/png")),
        ]:
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_command(self, *args):
        with patch("weiss.scraper.fetch_html", return_value=page("card_character.html")):
            call_command("fetch_cards", *args, stdout=StringIO(), stderr=StringIO())

    def test_saves_card_and_uploads_image_by_expansion_and_serial(self):
        self.run_command("--card", "NIK/S135-E001S")
        card = Card.objects.get()
        self.assertEqual(card.power, 2500)
        self.assertEqual(card.image_s3_key, "weiss/290/NIK-S135-E001S.png")
        args, kwargs = self.fake_s3.upload_fileobj.call_args
        self.assertEqual(args[1:], ("my-bucket", "weiss/290/NIK-S135-E001S.png"))
        self.assertEqual(kwargs["ExtraArgs"], {"ContentType": "image/png"})

    def test_refetch_updates_card_without_reuploading_image(self):
        self.run_command("--card", "NIK/S135-E001S")
        Card.objects.update(power=0)
        self.run_command("--card", "NIK/S135-E001S")
        self.assertEqual(Card.objects.get().power, 2500)
        self.assertEqual(self.fake_s3.upload_fileobj.call_count, 1)

    def test_dry_run_saves_nothing(self):
        self.run_command("--card", "NIK/S135-E001S", "--dry-run")
        self.assertFalse(Card.objects.exists())
        self.fake_s3.upload_fileobj.assert_not_called()

    def test_skip_existing(self):
        self.run_command("--card", "NIK/S135-E001S")
        with patch("weiss.scraper.fetch_html") as fetch_html:
            call_command("fetch_cards", "--card", "NIK/S135-E001S", "--skip-existing", stdout=StringIO())
        fetch_html.assert_not_called()


class CardPagesTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.client.force_login(User.objects.create_user("daryl", password="x", is_staff=True))
        base = {"expansion": "NIKKE Vol.2", "expansion_id": 290, "image_url": "https://en.ws-tcg.com/x.png"}
        Card.objects.create(serial_number="NIK/S135-E001", name="Elegg", color="Yellow", level=1, **base)
        Card.objects.create(serial_number="NIK/S135-E002", name="Anis", color="Red", level=0, **base)
        Card.objects.create(serial_number="NIK/S135-E120", name="Footstep", color="Red", level=None,
                            image_s3_key="weiss/290/NIK-S135-E120.png", **base)
        Card.objects.create(serial_number="OSK/S01-001", name="Other set card", expansion="Other", expansion_id=100)

    def names(self, **params):
        response = self.client.get(reverse("weiss:set", args=[290]), params)
        return sorted(card.name for card in response.context["cards"])

    def test_set_list_groups_cards_by_expansion(self):
        response = self.client.get(reverse("weiss:sets"))
        self.assertEqual([(s["expansion_id"], s["cards"]) for s in response.context["sets"]], [(290, 3), (100, 1)])
        self.assertContains(response, reverse("weiss:set", args=[290]))

    def test_set_page_shows_only_that_set(self):
        self.assertEqual(self.names(), ["Anis", "Elegg", "Footstep"])

    def test_filter_by_name_color_and_level(self):
        self.assertEqual(self.names(name="eleg"), ["Elegg"])
        self.assertEqual(self.names(color="Red"), ["Anis", "Footstep"])
        self.assertEqual(self.names(level="0"), ["Anis"])
        self.assertEqual(self.names(level="none"), ["Footstep"])
        self.assertEqual(self.names(color="Red", level="0"), ["Anis"])

    def test_filter_options_come_from_the_set(self):
        response = self.client.get(reverse("weiss:set", args=[290]))
        self.assertEqual(response.context["colors"], ["Red", "Yellow"])
        self.assertEqual(response.context["levels"], [0, 1, None])

    def test_unknown_set_is_404(self):
        self.assertEqual(self.client.get(reverse("weiss:set", args=[999])).status_code, 404)

    @override_settings(AWS_S3_BUCKET="my-bucket")
    def test_images_use_s3_copy_when_available_else_official_site(self):
        fake_s3 = MagicMock()
        fake_s3.generate_presigned_url.return_value = "https://s3.example/signed"
        with patch("core.s3.boto3.client", return_value=fake_s3):
            response = self.client.get(reverse("weiss:set", args=[290]))
        sources = {card.name: card.image_src for card in response.context["cards"]}
        self.assertEqual(sources["Footstep"], "https://s3.example/signed")
        self.assertEqual(sources["Elegg"], "https://en.ws-tcg.com/x.png")
        self.assertEqual(fake_s3.generate_presigned_url.call_count, 1)

    def test_card_page(self):
        card = Card.objects.get(name="Elegg")
        response = self.client.get(reverse("weiss:card", args=[card.pk]))
        self.assertContains(response, "NIK/S135-E001")
        self.assertContains(response, reverse("weiss:set", args=[290]))

    def test_pages_require_staff(self):
        self.client.logout()
        for url in (reverse("weiss:sets"), reverse("weiss:set", args=[290])):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_dashboard_tabs_mark_current_section(self):
        response = self.client.get(reverse("weiss:sets"))
        self.assertContains(response, 'href="/dashboard/weiss/" class="current"')
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, 'href="/dashboard/" class="current"')


GROUPS = [{"groupId": 24696, "name": "GODDESS OF VICTORY: NIKKE Vol.2"}, {"groupId": 1, "name": "Other"}]
PRODUCTS = [
    {"productId": 1, "name": "Booster Box", "url": "https://tcgplayer.com/product/1", "extendedData": []},
    {"productId": 718179, "name": "Guillotine", "url": "https://www.tcgplayer.com/product/718179/x",
     "extendedData": [{"name": "Number", "value": "NIK/S135-E032"}]},
    {"productId": 718200, "name": "Elegg", "url": "", "extendedData": [{"name": "Number", "value": "NIK/S135-E001"}]},
]
PRICES = [
    {"productId": 718179, "subTypeName": "Foil", "marketPrice": 9.0, "lowPrice": 8.0, "midPrice": 9, "highPrice": 10},
    {"productId": 718179, "subTypeName": "Normal", "marketPrice": 1.25, "lowPrice": 0.99, "midPrice": 1.5, "highPrice": 3.0},
    {"productId": 718200, "subTypeName": "Normal", "marketPrice": None, "lowPrice": 0.5, "midPrice": None, "highPrice": None},
]


def fake_tcgcsv(path):
    if path.endswith("/groups"):
        return GROUPS
    return PRODUCTS if path.endswith("/products") else PRICES


@patch("weiss.tcgcsv.get", side_effect=fake_tcgcsv)
class TcgcsvTests(TestCase):
    def test_find_group_ignores_case_and_spacing(self, _):
        from .tcgcsv import find_groups
        [(group, overlap)] = find_groups("goddess of victory:  NIKKE Vol.2 ", ["NIK/S135-E032"])
        self.assertEqual((group["groupId"], overlap), (24696, 1))
        self.assertEqual(find_groups("Unknown Set", ["XYZ/S01-001"]), [])

    def test_card_prices_keyed_by_number_preferring_normal_printing(self, _):
        from .tcgcsv import card_prices
        prices = card_prices(24696)
        self.assertEqual(set(prices), {"NIK/S135-E032", "NIK/S135-E001"})
        self.assertEqual(prices["NIK/S135-E032"]["market_price"], 1.25)
        self.assertEqual(prices["NIK/S135-E032"]["tcgplayer_product_id"], 718179)


@patch("weiss.tcgcsv.get", side_effect=fake_tcgcsv)
class FetchPricesCommandTests(TestCase):
    def setUp(self):
        base = {"expansion": "GODDESS OF VICTORY: NIKKE Vol.2", "expansion_id": 290}
        self.guillotine = Card.objects.create(serial_number="NIK/S135-E032", name="Guillotine", **base)
        Card.objects.create(serial_number="NIK/S135-E001", name="Elegg", **base)
        Card.objects.create(serial_number="NIK/S135-E999", name="Not on TCGplayer", **base)

    def run_command(self, *args):
        out = StringIO()
        call_command("fetch_prices", *args, stdout=out, stderr=out)
        return out.getvalue()

    def test_saves_prices_matched_by_serial(self, _):
        output = self.run_command("--expansion", "290")
        price = self.guillotine.tcgplayer_price
        self.assertEqual(str(price.market_price), "1.25")
        self.assertEqual(str(price.low_price), "0.99")
        self.assertEqual(price.product_url, "https://www.tcgplayer.com/product/718179/x")
        self.assertIn("updated 2 prices, 1 cards not on TCGplayer", output)

    def test_rerun_updates_in_place(self, _):
        self.run_command("--all")
        self.run_command("--all")
        self.assertEqual(CardPrice.objects.count(), 2)

    def test_dry_run_saves_nothing(self, _):
        self.run_command("--expansion", "290", "--dry-run")
        self.assertFalse(CardPrice.objects.exists())

    def test_unmatched_set_name_explains_group_option(self, get):
        Card.objects.update(expansion="Renamed Set")
        self.assertIn("pass --group", self.run_command("--expansion", "290"))
        self.assertFalse(CardPrice.objects.exists())
        self.run_command("--expansion", "290", "--group", "24696")
        self.assertEqual(CardPrice.objects.count(), 2)


class PriceDisplayTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.client.force_login(User.objects.create_user("daryl", password="x", is_staff=True))
        self.card = Card.objects.create(serial_number="NIK/S135-E032", name="Guillotine",
                                        expansion="NIKKE Vol.2", expansion_id=290)
        Card.objects.create(serial_number="NIK/S135-E033", name="No price yet", expansion="NIKKE Vol.2", expansion_id=290)
        CardPrice.objects.create(card=self.card, market_price="1.25", low_price="0.99",
                                 product_url="https://www.tcgplayer.com/product/718179/x")

    def test_set_page_shows_price_next_to_name(self):
        response = self.client.get(reverse("weiss:set", args=[290]))
        self.assertContains(response, '<span class="card-price">$1.25</span>', count=1)

    def test_card_page_shows_price_and_tcgplayer_link(self):
        response = self.client.get(reverse("weiss:card", args=[self.card.pk]))
        self.assertContains(response, '<span class="card-price">$1.25</span>')
        self.assertContains(response, "lowest listing $0.99")
        self.assertContains(response, "https://www.tcgplayer.com/product/718179/x")


class FetchSetsCommandTests(TestCase):
    def test_runs_cards_then_prices_for_each_set_and_continues_after_a_failure(self):
        calls = []

        def fake_call(name, **kwargs):
            calls.append((name, kwargs["expansion"]))
            if name == "fetch_cards" and kwargs["expansion"] == 291:
                from django.core.management.base import CommandError
                raise CommandError("No cards found")

        out = StringIO()
        with patch("weiss.management.commands.fetch_sets.call_command", side_effect=fake_call):
            call_command("fetch_sets", "290", "291", "292", "--skip-existing", stdout=out, stderr=out)
        self.assertEqual(calls, [
            ("fetch_cards", 290), ("fetch_prices", 290),
            ("fetch_cards", 291),
            ("fetch_cards", 292), ("fetch_prices", 292),
        ])
        self.assertIn("Finished 2 of 3 expansions; failed: 291.", out.getvalue())

    def test_passes_card_options_through_and_skips_prices_on_dry_run(self):
        with patch("weiss.management.commands.fetch_sets.call_command") as fake_call:
            call_command("fetch_sets", "290", "--dry-run", "--delay", "2", stdout=StringIO())
        fake_call.assert_called_once()
        kwargs = fake_call.call_args.kwargs
        self.assertEqual((kwargs["expansion"], kwargs["dry_run"], kwargs["delay"]), (290, True, 2.0))


class ListExpansionsTests(TestCase):
    PAGE = BeautifulSoup(
        '<select id="expansion_select"><option value="">All</option>'
        '<option value="252">Booster Pack GODDESS OF VICTORY: NIKKE</option>'
        '<option value="290">GODDESS OF VICTORY: NIKKE Vol.2</option>'
        '<option value="70">Accel・World</option></select>',
        "html.parser",
    )

    def test_search_by_name_marks_saved_sets(self):
        Card.objects.create(serial_number="NIK/S135-E001", name="Elegg", expansion="x", expansion_id=290)
        out = StringIO()
        with patch("weiss.scraper.fetch_html", return_value=self.PAGE):
            call_command("list_expansions", "nikke", stdout=out)
        self.assertEqual(out.getvalue().splitlines(), [
            "  252  Booster Pack GODDESS OF VICTORY: NIKKE",
            "  290  GODDESS OF VICTORY: NIKKE Vol.2   (saved)",
            "2 expansions.",
        ])

    def test_card_lookup_shows_its_expansion(self):
        out = StringIO()
        with patch("weiss.scraper.fetch_html", return_value=page("card_character.html")):
            call_command("list_expansions", "--card", "NIK/S135-E001S", stdout=out)
        self.assertIn("Expansion 290: GODDESS OF VICTORY: NIKKE Vol.2", out.getvalue())


class ImageUrlTests(TestCase):
    def test_spaces_in_image_paths_are_encoded_once(self):
        from .scraper import safe_url
        url = "https://en.ws-tcg.com/wordpress/wp-content/images/cardimages/updates/errata/OSK_S107_E086 (E).png"
        self.assertEqual(safe_url(url), url.replace(" ", "%20"))
        self.assertEqual(safe_url(safe_url(url)), safe_url(url))

    def test_bad_url_becomes_scraper_error(self):
        from http.client import InvalidURL

        from .scraper import ScraperError, fetch
        with patch("weiss.scraper.urlopen", side_effect=InvalidURL("bad")), self.assertRaises(ScraperError):
            fetch("/x.png")


@override_settings(AWS_S3_BUCKET="my-bucket")
class FetchCardsRecoveryTests(TestCase):
    def setUp(self):
        for target in ("core.s3.boto3.client", "weiss.management.commands.fetch_cards.time.sleep"):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_image_failure_skips_that_card_and_skip_existing_retries_it(self):
        from .scraper import ScraperError
        out = StringIO()
        with patch("weiss.scraper.fetch_html", return_value=page("card_character.html")), \
                patch("weiss.management.commands.fetch_cards.fetch", side_effect=ScraperError("boom")):
            call_command("fetch_cards", "--card", "NIK/S135-E001S", stdout=out, stderr=out)
        self.assertIn("NIK/S135-E001S: boom", out.getvalue())
        self.assertEqual(Card.objects.get().image_s3_key, "")

        with patch("weiss.scraper.fetch_html", return_value=page("card_character.html")), \
                patch("weiss.management.commands.fetch_cards.fetch", return_value=(b"PNG", "image/png")):
            call_command("fetch_cards", "--card", "NIK/S135-E001S", "--skip-existing", stdout=StringIO())
        self.assertEqual(Card.objects.get().image_s3_key, "weiss/290/NIK-S135-E001S.png")


OSK_GROUPS = [
    {"groupId": 23507, "name": "[OSHI NO KO]", "abbreviation": "OSK"},
    {"groupId": 24530, "name": "[OSHI NO KO] Vol.2", "abbreviation": "OSK"},
    {"groupId": 999, "name": "Unrelated", "abbreviation": "ABC/S01"},
]
OSK_NUMBERS = {
    # TCGplayer lists some numbers with the rarity appended.
    23507: ["OSK/S107-E001 RR", "OSK/S107-E002 RR", "OSK/S107-T01 TD", "OSK/S107-T02 TD"],
    24530: ["OSK/S121-E001", "OSK/S121-E002"],
    999: ["ABC/S01-001"],
}


def fake_osk_tcgcsv(path):
    if path.endswith("/groups"):
        return OSK_GROUPS
    group_id = int(path.split("/")[1])
    if path.endswith("/prices"):
        return [{"productId": i, "subTypeName": "Normal", "marketPrice": 1.0, "lowPrice": None,
                 "midPrice": None, "highPrice": None} for i, _ in enumerate(OSK_NUMBERS[group_id])]
    return [{"productId": i, "url": "", "extendedData": [{"name": "Number", "value": n}]}
            for i, n in enumerate(OSK_NUMBERS[group_id])]


@patch("weiss.tcgcsv.get", side_effect=fake_osk_tcgcsv)
class GroupMatchingByCardNumberTests(TestCase):
    """The official site's set names don't match TCGplayer's (e.g. the trial deck lives in the booster's group)."""

    def test_official_names_find_the_group_holding_their_cards(self, _):
        from .tcgcsv import find_groups
        cases = [
            ("[TD] 【OSHI NO KO】", ["OSK/S107-T01", "OSK/S107-T02"], 23507),
            ("【OSHI NO KO】", ["OSK/S107-E001", "OSK/S107-E002"], 23507),
            ("Booster Pack 【OSHI NO KO】 Vol.2", ["OSK/S121-E001", "OSK/S121-E002"], 24530),
        ]
        for name, serials, expected in cases:
            with self.subTest(name):
                group, overlap = find_groups(name, serials)[0]
                self.assertEqual((group["groupId"], overlap), (expected, 2))

    def test_cards_listed_under_another_group_still_get_prices(self, _):
        # A Vol.1 promo packed in Vol.2 boxes: the Vol.2 set's cards span both TCGplayer groups.
        for serial in ["OSK/S121-E001", "OSK/S121-E002", "OSK/S107-E001"]:
            Card.objects.create(serial_number=serial, name=serial, expansion="Booster Pack 【OSHI NO KO】 Vol.2",
                                expansion_id=278)
        call_command("fetch_prices", "--expansion", "278", stdout=StringIO())
        self.assertEqual(CardPrice.objects.count(), 3)

    def test_fetch_prices_all_prices_each_osk_set(self, _):
        for expansion_id, name, serials in [
            (1, "[TD] 【OSHI NO KO】", ["OSK/S107-T01"]),
            (2, "【OSHI NO KO】", ["OSK/S107-E001"]),
            (3, "Booster Pack 【OSHI NO KO】 Vol.2", ["OSK/S121-E001"]),
        ]:
            for serial in serials:
                Card.objects.create(serial_number=serial, name=serial, expansion=name, expansion_id=expansion_id)
        out = StringIO()
        call_command("fetch_prices", "--all", stdout=out, stderr=out)
        self.assertEqual(CardPrice.objects.count(), 3)
        self.assertNotIn("couldn't find", out.getvalue())

