from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Card, CardList, CardListEntry, CardPrice
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

    def set_ids(self, **params):
        return [s["expansion_id"] for s in self.client.get(reverse("weiss:sets"), params).context["sets"]]

    def test_set_list_groups_cards_by_expansion_newest_first(self):
        response = self.client.get(reverse("weiss:sets"))
        self.assertEqual([(s["expansion_id"], s["cards"], s["code"]) for s in response.context["sets"]],
                         [(290, 3, "NIK"), (100, 1, "OSK")])
        self.assertContains(response, reverse("weiss:set", args=[290]))

    def test_set_list_sorting(self):
        self.assertEqual(self.set_ids(sort="number"), [100, 290])
        self.assertEqual(self.set_ids(sort="name"), [290, 100])  # "NIKKE Vol.2" before "Other"
        self.assertEqual(self.set_ids(sort="-cards"), [290, 100])
        self.assertEqual(self.set_ids(sort="bogus"), [290, 100])

    def test_set_list_search_by_name_number_and_series(self):
        self.assertEqual(self.set_ids(name="nikke"), [290])
        self.assertEqual(self.set_ids(number="10"), [100])
        self.assertEqual(self.set_ids(code="OSK"), [100])
        self.assertEqual(self.client.get(reverse("weiss:sets")).context["codes"], ["NIK", "OSK"])

    def test_cover_is_first_card_of_the_main_print_run(self):
        # A Vol.1 promo sorts before Vol.2's own cards but shouldn't be the cover.
        for serial in ["OSK/S107-PE02S", "OSK/S121-E002", "OSK/S121-E001"]:
            Card.objects.create(serial_number=serial, name=serial, expansion="Vol.2", expansion_id=278,
                                image_url=f"https://en.ws-tcg.com/{serial}.png")
        sets = {s["expansion_id"]: s for s in self.client.get(reverse("weiss:sets")).context["sets"]}
        self.assertEqual(sets[278]["cover"].serial_number, "OSK/S121-E001")
        self.assertEqual(sets[290]["cover"].serial_number, "NIK/S135-E001")

    def test_set_page_shows_only_that_set(self):
        self.assertEqual(self.names(), ["Anis", "Elegg", "Footstep"])

    def test_filter_by_name_color_and_level(self):
        self.assertEqual(self.names(name="eleg"), ["Elegg"])
        self.assertEqual(self.names(color="Red"), ["Anis", "Footstep"])
        self.assertEqual(self.names(level="0"), ["Anis"])
        self.assertEqual(self.names(level="none"), ["Footstep"])
        self.assertEqual(self.names(color="Red", level="0"), ["Anis"])
        self.assertEqual(self.names(color=["Red", "Yellow"]), ["Anis", "Elegg", "Footstep"])
        self.assertEqual(self.names(color=["Yellow", "Blue"]), ["Elegg"])

    def test_color_chips_show_which_colors_are_selected(self):
        response = self.client.get(reverse("weiss:set", args=[290]), {"color": ["Red", "Yellow"]})
        self.assertEqual(response.context["filters"]["colors"], ["Red", "Yellow"])
        self.assertContains(response, 'value="Red" checked')
        self.assertContains(response, 'value="Yellow" checked')

    def test_search_by_card_text(self):
        Card.objects.filter(name="Elegg").update(description="【AUTO】 When this card is placed on stage, draw 1 card.")
        Card.objects.filter(name="Anis").update(description="【CONT】 All your other characters get +500 power.")
        self.assertEqual(self.names(text="DRAW 1"), ["Elegg"])
        self.assertEqual(self.names(text="power", color="Red"), ["Anis"])
        self.assertEqual(self.names(text="nothing like this"), [])

    def serials(self, **params):
        response = self.client.get(reverse("weiss:set", args=[290]), params)
        return [card.serial_number[-4:] for card in response.context["cards"]]

    def test_filter_by_cost(self):
        Card.objects.filter(name="Elegg").update(cost=1)
        Card.objects.filter(name="Anis").update(cost=0)
        self.assertEqual(self.names(cost="1"), ["Elegg"])
        self.assertEqual(self.names(cost="none"), ["Footstep"])
        self.assertEqual(self.client.get(reverse("weiss:set", args=[290])).context["costs"], [0, 1, None])

    def test_sort_by_cost_level_and_price_with_blanks_last(self):
        Card.objects.filter(name="Elegg").update(cost=2)
        Card.objects.filter(name="Anis").update(cost=0)
        self.assertEqual(self.serials(), ["E001", "E002", "E120"])
        self.assertEqual(self.serials(sort="cost"), ["E002", "E001", "E120"])
        self.assertEqual(self.serials(sort="-cost"), ["E001", "E002", "E120"])
        self.assertEqual(self.serials(sort="-level"), ["E001", "E002", "E120"])
        self.assertEqual(self.serials(sort="level"), ["E120", "E002", "E001"])  # climax before level 0
        CardPrice.objects.create(card=Card.objects.get(name="Anis"), market_price="3.00")
        self.assertEqual(self.serials(sort="-price")[0], "E002")
        self.assertEqual(self.serials(sort="bogus"), ["E001", "E002", "E120"])

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

    def test_series_page_spans_every_set_with_the_same_filters(self):
        Card.objects.create(serial_number="NIK/S117-E001", name="Rapi", color="Red", level=0,
                            expansion="NIKKE Vol.1", expansion_id=270)
        url = reverse("weiss:series", args=["NIK"])
        response = self.client.get(url)
        self.assertEqual(sorted(c.name for c in response.context["cards"]), ["Anis", "Elegg", "Footstep", "Rapi"])
        self.assertEqual(response.context["sets"], [(290, "NIKKE Vol.2"), (270, "NIKKE Vol.1")])
        names = lambda **p: sorted(c.name for c in self.client.get(url, p).context["cards"])
        self.assertEqual(names(color="Red", level="0"), ["Anis", "Rapi"])
        self.assertEqual(names(set="270"), ["Rapi"])
        self.assertEqual(self.client.get(url, {"sort": "-level"}).context["cards"][0].name, "Elegg")
        self.assertEqual(self.client.get(reverse("weiss:series", args=["XYZ"])).status_code, 404)

    def test_set_and_card_pages_link_to_their_series(self):
        series_url = reverse("weiss:series", args=["NIK"])
        self.assertContains(self.client.get(reverse("weiss:set", args=[290])), series_url)
        card = Card.objects.get(name="Elegg")
        self.assertContains(self.client.get(reverse("weiss:card", args=[card.pk])), series_url)
        self.assertContains(self.client.get(reverse("weiss:sets"), {"code": "NIK"}), series_url)

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
        # Once next to the name in the grid, once in that card's hover details.
        self.assertContains(response, '<span class="card-price">$1.25</span>', count=2)

    def test_set_page_has_hover_details_for_each_card(self):
        response = self.client.get(reverse("weiss:set", args=[290]))
        self.assertContains(response, 'class="card-peek" role="tooltip" hidden', count=2)
        self.assertContains(response, "weiss/peek.js")

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

    def test_export_writes_a_spreadsheet_friendly_csv(self):
        import csv
        import tempfile
        Card.objects.create(serial_number="NIK/S135-E001", name="Elegg", expansion="x", expansion_id=290)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "expansions.csv"
            with patch("weiss.scraper.fetch_html", return_value=self.PAGE):
                call_command("export_expansions", "-o", str(path), stdout=StringIO())
            with open(path, encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
        self.assertEqual(rows, [
            ["Expansion number", "Name", "Saved on site", "Cards saved"],
            ["290", "GODDESS OF VICTORY: NIKKE Vol.2", "yes", "1"],
            ["252", "Booster Pack GODDESS OF VICTORY: NIKKE", "no", "0"],
            ["70", "Accel・World", "no", "0"],
        ])


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



class CardListTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user("daryl", password="x", is_staff=True)
        self.other = User.objects.create_user("other", password="x", is_staff=True)
        self.client.force_login(self.user)
        base = {"expansion": "NIKKE Vol.2", "expansion_id": 290}
        self.elegg = Card.objects.create(serial_number="NIK/S135-E001", name="Elegg", **base)
        self.anis = Card.objects.create(serial_number="NIK/S135-E002", name="Anis", **base)

    def create_list(self, name="Deck"):
        """A plain (non-deck) list; deck reminders are covered by DeckReminderTests."""
        self.client.post(reverse("weiss:list_create"), {"name": name})
        CardList.objects.filter(user=self.user, name=name).update(is_deck=False)
        return CardList.objects.get(user=self.user, name=name)

    def change(self, card_list, card, delta=1, json=False):
        headers = {"HTTP_ACCEPT": "application/json"} if json else {}
        return self.client.post(reverse("weiss:list_change", args=[card_list.pk]),
                                {"card": card.pk, "delta": delta, "next": "/dashboard/weiss/"}, **headers)

    def test_creating_a_list_starts_editing_it(self):
        deck = self.create_list()
        response = self.client.get(reverse("weiss:set", args=[290]))
        self.assertEqual(response.context["editing_list"], deck)
        self.assertContains(response, 'data-qty-for="%d"' % self.elegg.pk)

    def test_add_copies_and_remove_down_to_zero(self):
        deck = self.create_list()
        for _ in range(3):
            self.change(deck, self.elegg)
        self.change(deck, self.anis)
        self.assertEqual(deck.card_count(), 4)
        self.assertEqual(deck.entries.get(card=self.elegg).quantity, 3)
        for _ in range(3):
            self.change(deck, self.elegg, delta=-1)
        self.assertFalse(deck.entries.filter(card=self.elegg).exists())
        self.change(deck, self.anis, delta=-1)
        self.change(deck, self.anis, delta=-1)  # removing from zero stays at zero
        self.assertEqual(deck.card_count(), 0)

    def test_json_response_has_running_count_and_panel(self):
        deck = self.create_list()
        self.change(deck, self.elegg)
        data = self.change(deck, self.elegg, json=True).json()
        self.assertEqual((data["ok"], data["count"], data["quantity"], data["full"]), (True, 2, 2, False))
        self.assertIn("<strong>2</strong> / 100 cards", data["panel"])
        # Forms in the swapped-in panel point back at the page, not at the endpoint.
        self.assertIn('name="next" value="/dashboard/weiss/"', data["panel"])

    def test_panel_totals_prices_like_a_cart(self):
        deck = self.create_list()
        CardPrice.objects.create(card=self.elegg, market_price="1.25")
        self.change(deck, self.elegg)
        self.change(deck, self.anis)
        panel = self.change(deck, self.elegg, json=True).json()["panel"]
        self.assertIn("<strong>~$2.50</strong>", panel)
        self.assertIn("approx.", panel)
        self.assertIn('<span class="line-total">~$2.50</span>', panel)
        self.assertIn("Not counting 1 card without a price.", panel)

    def test_list_caps_at_100_cards(self):
        deck = self.create_list()
        CardListEntry.objects.create(card_list=deck, card=self.elegg, quantity=99)
        self.assertTrue(self.change(deck, self.anis, json=True).json()["full"])
        response = self.change(deck, self.anis, json=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already has 100 cards", response.json()["error"])
        self.assertEqual(deck.card_count(), 100)

    def test_user_caps_at_100_lists(self):
        CardList.objects.bulk_create([CardList(user=self.user, name=f"List {i}") for i in range(100)])
        response = self.client.post(reverse("weiss:list_create"), {"name": "One more"}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CardList.objects.filter(user=self.user).count(), 100)

    def test_lists_are_private_to_their_owner(self):
        theirs = CardList.objects.create(user=self.other, name="Theirs")
        self.assertEqual(self.client.get(reverse("weiss:list", args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.change(theirs, self.elegg).status_code, 404)
        self.assertEqual(self.client.post(reverse("weiss:list_edit", args=[theirs.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("weiss:sets")), "Theirs")

    def test_switching_stopping_renaming_and_deleting(self):
        deck = self.create_list("Deck")
        wants = self.create_list("Wants")
        self.client.post(reverse("weiss:list_edit", args=[deck.pk]))
        self.assertEqual(self.client.get(reverse("weiss:sets")).context["editing_list"], deck)
        self.client.post(reverse("weiss:list_stop_editing"))
        self.assertIsNone(self.client.get(reverse("weiss:sets")).context["editing_list"])
        self.client.post(reverse("weiss:list_rename", args=[wants.pk]), {"name": "Want list"})
        wants.refresh_from_db()
        self.assertEqual(wants.name, "Want list")
        self.client.post(reverse("weiss:list_edit", args=[wants.pk]))
        self.client.post(reverse("weiss:list_delete", args=[wants.pk]))
        self.assertFalse(CardList.objects.filter(pk=wants.pk).exists())
        self.assertIsNone(self.client.get(reverse("weiss:sets")).context["editing_list"])

    def test_add_cards_button_edits_the_list_and_goes_to_the_sets_page(self):
        deck = self.create_list("Deck")
        self.create_list("Other")  # now editing "Other"
        response = self.client.get(reverse("weiss:list", args=[deck.pk]))
        self.assertContains(response, f'<input type="hidden" name="next" value="{reverse("weiss:sets")}">')
        response = self.client.post(reverse("weiss:list_edit", args=[deck.pk]), {"next": reverse("weiss:sets")})
        self.assertRedirects(response, reverse("weiss:sets"))
        self.assertEqual(response.wsgi_request.session["weiss_editing_list"], deck.pk)

    def test_list_page_totals_market_value(self):
        deck = self.create_list()
        CardListEntry.objects.create(card_list=deck, card=self.elegg, quantity=4)
        CardListEntry.objects.create(card_list=deck, card=self.anis, quantity=1)
        CardPrice.objects.create(card=self.elegg, market_price="1.25")
        response = self.client.get(reverse("weiss:list", args=[deck.pk]))
        self.assertContains(response, "5 / 100 cards")
        self.assertContains(response, "~$5.00 approx. TCGplayer market value (1 card without a price)")
        self.assertContains(response, "4× Elegg")

    def test_no_panel_outside_weiss_pages(self):
        self.create_list()
        self.assertNotIn("editing_list", self.client.get(reverse("dashboard")).context)


class DeckReminderTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user("daryl", password="x", is_staff=True)
        self.client.force_login(self.user)
        self.deck = CardList.objects.create(user=self.user, name="OSK deck")
        self.client.post(reverse("weiss:list_edit", args=[self.deck.pk]))
        base = {"expansion": "OSHI NO KO", "expansion_id": 230}
        cards = {
            "lv0": Card.objects.create(serial_number="OSK/S107-E001", name="Ai", card_type="Character", level=0, **base),
            "event0": Card.objects.create(serial_number="OSK/S107-E002", name="Plan", card_type="Event", level=0, **base),
            "lv1": Card.objects.create(serial_number="OSK/S107-E003", name="Ruby", card_type="Character", level=1, **base),
            "lv2": Card.objects.create(serial_number="OSK/S107-E004", name="Aqua", card_type="Character", level=2, **base),
            "lv3": Card.objects.create(serial_number="OSK/S107-E005", name="Kana", card_type="Character", level=3, **base),
            "cx": Card.objects.create(serial_number="OSK/S107-E006", name="Idol", card_type="Climax", level=None, **base),
        }
        for key, quantity in {"lv0": 14, "event0": 4, "lv1": 12, "lv2": 8, "lv3": 4, "cx": 7}.items():
            CardListEntry.objects.create(card_list=self.deck, card=cards[key], quantity=quantity)
        self.cards = cards

    def checks(self):
        return self.client.get(reverse("weiss:list", args=[self.deck.pk])).context["deck"]

    def test_new_lists_are_decks_and_plain_lists_show_no_reminders(self):
        self.client.post(reverse("weiss:list_create"), {"name": "Fresh"})
        self.assertTrue(CardList.objects.get(name="Fresh").is_deck)
        CardList.objects.filter(pk=self.deck.pk).update(is_deck=False)
        self.assertIsNone(self.checks())

    def test_toggle_marks_a_list_as_a_plain_list_and_back(self):
        self.client.post(reverse("weiss:list_deck", args=[self.deck.pk]), {})
        self.deck.refresh_from_db()
        self.assertFalse(self.deck.is_deck)
        self.client.post(reverse("weiss:list_deck", args=[self.deck.pk]), {"is_deck": "on"})
        self.deck.refresh_from_db()
        self.assertTrue(self.deck.is_deck)

    def test_group_counts_and_colors(self):
        CardList.objects.filter(pk=self.deck.pk).update(is_deck=True)
        deck = self.checks()
        self.assertEqual(deck["total"], 49)
        self.assertFalse(deck["over"] or deck["exact"])
        self.assertEqual([(g["label"], g["count"], g["ok"], g["required"]) for g in deck["groups"]], [
            ("Climax", 7, False, True),
            ("Level 0", 18, True, False),  # events count toward their level
            ("Level 1", 12, True, False),
            ("Level 2 + 3", 12, True, False),
        ])
        CardListEntry.objects.filter(card=self.cards["cx"]).update(quantity=8)
        self.assertTrue(self.checks()["exact"])
        CardListEntry.objects.filter(card=self.cards["lv1"]).update(quantity=13)
        deck = self.checks()
        self.assertTrue(deck["over"])
        self.assertFalse(deck["groups"][2]["ok"])  # above the target is off too

    def test_counts_cards_by_color(self):
        Card.objects.filter(name__in=["Ai", "Ruby"]).update(color="Yellow")
        Card.objects.filter(name="Aqua").update(color="Red")
        CardList.objects.filter(pk=self.deck.pk).update(is_deck=True)
        self.assertEqual(self.checks()["colors"], [("Yellow", 26), ("No color", 15), ("Red", 8)])
        self.assertContains(self.client.get(reverse("weiss:sets")), '<strong>26</strong> Yellow')

    def test_panel_lists_climaxes_first_then_by_level(self):
        context = self.client.get(reverse("weiss:sets")).context
        self.assertEqual([e.card.name for e in context["editing_entries"]],
                         ["Idol", "Ai", "Plan", "Ruby", "Aqua", "Kana"])
        page = self.client.get(reverse("weiss:list", args=[self.deck.pk])).context
        self.assertEqual([e.card.name for e in page["entries"]], ["Idol", "Ai", "Plan", "Ruby", "Aqua", "Kana"])
        panel = self.client.get(reverse("weiss:sets")).content.decode()
        self.assertIn('<span class="panel-level" title="Level 3">3</span>', panel)
        self.assertIn('title="Climax">CX</span>', panel)

    def test_more_than_four_of_a_name_turns_its_buttons_red(self):
        # 14 copies of "Ai" are already in the deck; a second printing of the same name counts too.
        promo = Card.objects.create(serial_number="OSK/S107-E001SP", name="Ai", card_type="Character", level=0,
                                    expansion="OSHI NO KO", expansion_id=230)
        CardListEntry.objects.filter(card=self.cards["lv0"]).update(quantity=3)
        CardListEntry.objects.create(card_list=self.deck, card=promo, quantity=1)
        self.assertEqual(self.checks()["over_limit"], ["Aqua", "Idol", "Ruby"])  # Ai is at exactly 4
        response = self.client.post(reverse("weiss:list_change", args=[self.deck.pk]),
                                    {"card": promo.pk, "delta": 1}, HTTP_ACCEPT="application/json")
        self.assertIn("Ai", response.json()["over_limit"])
        page = self.client.get(reverse("weiss:set", args=[230]))
        self.assertContains(page, 'class="qty-controls over-limit" data-qty-controls data-card-name="Ai"', count=4)  # set grid + panel
        self.assertContains(page, 'class="qty-controls" data-qty-controls data-card-name="Ai"', count=0)
        CardList.objects.filter(pk=self.deck.pk).update(is_deck=False)  # plain lists have no limit
        self.assertNotContains(self.client.get(reverse("weiss:set", args=[230])), "over-limit")

    def test_panel_shows_reminders_and_thumbnails_and_json_refreshes_them(self):
        CardList.objects.filter(pk=self.deck.pk).update(is_deck=True)
        response = self.client.get(reverse("weiss:sets"))
        self.assertContains(response, "Level 2 + 3")
        self.assertContains(response, 'class="panel-thumb"')
        response = self.client.post(reverse("weiss:list_change", args=[self.deck.pk]),
                                    {"card": self.cards["cx"].pk, "delta": 1}, HTTP_ACCEPT="application/json")
        data = response.json()
        self.assertEqual(data["list"], self.deck.pk)
        self.assertIn("<strong>8</strong> / 8", data["deck"])


class CardPopupTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user("daryl", password="x", is_staff=True)
        self.client.force_login(self.user)
        self.card = Card.objects.create(serial_number="OSK/S107-E001", name="Ai", card_type="Character", level=0,
                                        description="【AUTO】 Draw 1 card.", expansion="OSHI NO KO", expansion_id=230)
        self.deck = CardList.objects.create(user=self.user, name="OSK deck")
        CardListEntry.objects.create(card_list=self.deck, card=self.card, quantity=3)

    def test_panel_links_open_the_popup_which_shows_text_and_qty(self):
        self.client.post(reverse("weiss:list_edit", args=[self.deck.pk]))
        popup_url = reverse("weiss:card_popup", args=[self.card.pk])
        self.assertContains(self.client.get(reverse("weiss:sets")), f'data-card-popup="{popup_url}"')
        response = self.client.get(popup_url, {"next": "/dashboard/weiss/sets/230/"})
        self.assertContains(response, "Draw 1 card.")
        self.assertContains(response, 'data-qty-for="%d">3<' % self.card.pk)
        self.assertContains(response, 'name="next" value="/dashboard/weiss/sets/230/"')
        self.assertNotContains(response, "<html")

    def test_next_must_be_on_this_site(self):
        self.client.post(reverse("weiss:list_edit", args=[self.deck.pk]))
        response = self.client.get(reverse("weiss:card_popup", args=[self.card.pk]), {"next": "https://evil.example/"})
        self.assertNotContains(response, "evil.example")


class FetchNewSetsTests(TestCase):
    AVAILABLE = [(252, "NIKKE"), (290, "NIKKE Vol.2"), (100, "Old"), (278, "OSK Vol.2"), (230, "OSK"), (229, "OSK TD")]

    def run_command(self, *args):
        out = StringIO()
        with patch("weiss.management.commands.fetch_new_sets.expansions", return_value=self.AVAILABLE), \
                patch("weiss.management.commands.fetch_new_sets.call_command") as fake_call:
            call_command("fetch_new_sets", *args, stdout=out)
        return fake_call, out.getvalue()

    def test_fetches_newest_unsaved_sets_first(self):
        Card.objects.create(serial_number="NIK/S135-E001", name="x", expansion="NIKKE Vol.2", expansion_id=290)
        fake_call, _ = self.run_command("--count", "3")
        self.assertEqual(fake_call.call_args.args, ("fetch_sets", "278", "252", "230"))

    def test_dry_run_only_lists(self):
        fake_call, output = self.run_command("--dry-run", "--count", "2")
        fake_call.assert_not_called()
        self.assertIn("  290  NIKKE Vol.2", output)
        self.assertIn("  278  OSK Vol.2", output)
        self.assertNotIn("252", output)

    def test_nothing_new(self):
        for number, name in self.AVAILABLE:
            Card.objects.create(serial_number=f"X/{number}", name="x", expansion=name, expansion_id=number)
        fake_call, output = self.run_command()
        fake_call.assert_not_called()
        self.assertIn("already saved", output)


class RefreshPricesTests(TestCase):
    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone
        fresh = Card.objects.create(serial_number="A/1", name="a", expansion="Fresh", expansion_id=1)
        stale = Card.objects.create(serial_number="B/1", name="b", expansion="Stale", expansion_id=2)
        Card.objects.create(serial_number="C/1", name="c", expansion="Never priced", expansion_id=3)
        CardPrice.objects.create(card=fresh, market_price="1")
        CardPrice.objects.create(card=stale, market_price="1")
        CardPrice.objects.filter(card=stale).update(fetched_at=timezone.now() - timedelta(hours=30))

    def run_command(self, *args):
        out = StringIO()
        with patch("weiss.management.commands.fetch_new_sets.expansions", return_value=[(1, "Fresh"), (2, "Stale"), (3, "x")]), \
                patch("weiss.management.commands.fetch_new_sets.call_command") as fake_call:
            call_command("fetch_new_sets", *args, stdout=out)
        return fake_call, out.getvalue()

    def test_refreshes_only_sets_priced_over_20_hours_ago_or_never(self):
        fake_call, output = self.run_command("--refresh-prices")
        self.assertEqual([c.kwargs["expansion"] for c in fake_call.call_args_list], [2, 3])
        self.assertIn("Refreshing prices for 2 sets: 2, 3", output)

    def test_without_the_option_prices_are_left_alone(self):
        fake_call, _ = self.run_command()
        fake_call.assert_not_called()

    def test_dry_run_lists_without_refreshing(self):
        fake_call, output = self.run_command("--refresh-prices", "--dry-run")
        fake_call.assert_not_called()
        self.assertIn("Refreshing prices for 2 sets", output)
