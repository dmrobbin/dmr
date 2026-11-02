import io
import time
import uuid
from collections import defaultdict

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from core import s3
from weiss import card_images
from weiss.express import CX_COMBO
from weiss.management.commands.fetch_cards import image_key
from weiss.models import Card, CpuImage
from weiss.views import series_code


class Command(BaseCommand):
    help = ("Find another source for cards with no working picture (another printing of the card, or TCGplayer), "
            "and put an official and an unofficial image of the characters on cx combo cards into the pool of CPU avatar images.")

    def add_arguments(self, parser):
        parser.add_argument("--series", nargs="+", metavar="CODE", help="Only these series, e.g. AOT NIK")
        parser.add_argument("--skip-missing", action="store_true", help="Don't look for missing card pictures")
        parser.add_argument("--skip-art", action="store_true", help="Don't look for character art")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests to a site (default 1)")
        parser.add_argument("--dry-run", action="store_true", help="Show what it would do without saving or uploading")

    def handle(self, *args, **options):
        self.delay = options["delay"]
        self.dry_run = options["dry_run"]
        self.failed = []
        database = connection.settings_dict
        # Said first, so a run against the wrong database or bucket is plain to see.
        self.stdout.write(f"Saving to the {connection.vendor} database {database.get('NAME')}" + (f" on {database['HOST']}" if database.get("HOST") else "")
                          + f", images to s3://{settings.AWS_S3_BUCKET or '(no bucket set)'}/{settings.WEISS_S3_PREFIX}"
                          + (" (dry run: nothing will be saved)" if self.dry_run else ""))
        if not settings.AWS_S3_BUCKET and not self.dry_run and not options["skip_art"]:
            raise CommandError("AWS_S3_BUCKET isn't set, so there's nowhere to put avatar images. Use --skip-art or --dry-run.")
        cards = Card.objects.select_related().prefetch_related("prices").order_by("serial_number")
        by_series = defaultdict(list)
        for card in cards:
            if not options["series"] or series_code(card.serial_number) in options["series"]:
                by_series[series_code(card.serial_number)].append(card)
        if not by_series:
            raise CommandError("No cards in those series.")
        if not options["skip_missing"]:
            self.fix_missing(by_series)
        if not options["skip_art"]:
            self.combo_art(by_series)
        if self.failed:
            raise CommandError(f"{len(self.failed)} image{'s' if len(self.failed) != 1 else ''} couldn't be saved: " + "; ".join(self.failed))

    # --- Card pictures --------------------------------------------------------------------------------

    def picture_works(self, card):
        if card.image_s3_key:
            return True
        if not card.image_url:
            return False
        time.sleep(self.delay)
        return bool(card_images.download_image(card.image_url))

    def fix_missing(self, by_series):
        fixed, unfound = 0, []
        for code, cards in by_series.items():
            missing = [card for card in cards if not self.picture_works(card)]
            self.stdout.write(f"{code}: {len(missing)} of {len(cards)} cards have no working picture")
            if not missing:
                continue
            products = {}
            for expansion in {card.expansion for card in missing}:
                products |= card_images.product_ids_for(expansion, [c.serial_number for c in cards if c.expansion == expansion])
            for card in missing:
                source = self.fix_card(card, cards, products)
                if source:
                    fixed += 1
                    self.stdout.write(f"  {card.serial_number} {card.name}: {source}")
                else:
                    unfound.append(card)
                    self.stderr.write(self.style.WARNING(f"  {card.serial_number} {card.name}: nothing found"))
        verb = "Would fix" if self.dry_run else "Fixed"
        self.stdout.write(self.style.SUCCESS(f"{verb} {fixed} card pictures; {len(unfound)} still have none."))

    def fix_card(self, card, series_cards, products):
        """Give this card a picture, and say where it came from; None if nothing could be found."""
        others = sorted(Card.objects.filter(name=card.name, description=card.description).exclude(pk=card.pk).exclude(image_s3_key="", image_url=""),
                        key=lambda other: (series_code(other.serial_number) != series_code(card.serial_number), other.serial_number))
        for other in others:
            if other.image_s3_key:
                if not self.dry_run:
                    card.image_s3_key = other.image_s3_key
                    card.save(update_fields=["image_s3_key"])
                return f"the picture of {other.serial_number}"
            time.sleep(self.delay)
            found = card_images.download_image(other.image_url)
            if found:
                return self.keep_picture(card, other.image_url, found, f"the picture of {other.serial_number}")
        url = card_images.tcgplayer_image_url(card, products)
        if url:
            time.sleep(self.delay)
            found = card_images.download_image(url)
            if found:
                return self.keep_picture(card, url, found, "TCGplayer")
        return None

    def keep_picture(self, card, url, found, source):
        if self.dry_run:
            return source
        data, extension, content_type = found
        if settings.AWS_S3_BUCKET:
            key = image_key({"expansion_id": card.expansion_id, "serial_number": card.serial_number}) + extension
            problem = self.upload(key, data, content_type)
            if problem:
                self.stderr.write(self.style.ERROR(f"  {card.serial_number}: not saved: {problem}"))
                self.failed.append(f"{card.serial_number}: {problem}")
                return None
            card.image_s3_key = key
        card.image_url = url
        card.save(update_fields=["image_s3_key", "image_url"])
        return source

    # --- Character art --------------------------------------------------------------------------------

    def combo_art(self, by_series):
        added, missed = 0, []
        for code, cards in by_series.items():
            combos = [card for card in cards if CX_COMBO in (card.description or "") and card.card_type.lower() != "climax"]
            if not combos:
                continue
            title = card_images.series_title(combos[0].expansion)
            time.sleep(card_images.ANILIST_DELAY)
            try:
                cast, other_titles = card_images.anilist_show(title)
            except card_images.ImageSourceError as exc:
                self.stderr.write(self.style.WARNING(f"{code}: {exc}"))
                cast, other_titles = [], []
            self.stdout.write(f"{code}: {len(combos)} cx combo cards, {len(cast)} characters known for “{title}”")
            seen = set()
            for card in combos:
                for character in card_images.card_characters(card, cast):
                    if character["name"] in seen:
                        continue
                    seen.add(character["name"])
                    got, wanted = self.add_art(title, other_titles, character, card)
                    added += got
                    missed += [f"{character['name']} ({kind})" for kind in wanted]
        verb = "Would add" if self.dry_run else "Added"
        self.stdout.write(self.style.SUCCESS(f"{verb} {added} avatar images; {len(missed)} not found."))
        for miss in missed:
            self.stderr.write(self.style.WARNING(f"  not found: {miss}"))

    def add_art(self, title, other_titles, character, card):
        """(how many images it added, the kinds it couldn't find). What's already in the pool isn't fetched again."""
        name = character["name"]
        have = set(CpuImage.objects.filter(name=name, series=title).values_list("kind", flat=True))
        if {"official", "unofficial"} <= have:
            return 0, []
        time.sleep(self.delay)
        art = card_images.character_art(title, other_titles, character)
        added, missing = 0, []
        for kind in ("official", "unofficial"):
            if kind in have:
                continue
            if not art[kind]:
                missing.append(kind)
                continue
            data, extension, content_type, url = art[kind]
            self.stdout.write(f"  {card.name} → {name}, {kind}: {url}")
            if self.dry_run:
                added += 1
                continue
            key = f"{settings.WEISS_S3_PREFIX}cpu-images/pool-{uuid.uuid4().hex}{extension}"
            problem = self.upload(key, data, content_type)
            if problem:
                self.stderr.write(self.style.ERROR(f"    not saved: {problem}"))
                self.failed.append(f"{name} ({kind}): {problem}")
                continue
            image = CpuImage.objects.create(key=key, name=name, series=title, kind=kind, source_url=url, source_card=card)
            self.stdout.write(f"    saved as image {image.pk}, {key}")
            added += 1
        return added, missing

    def upload(self, key, data, content_type):
        """Upload and make sure it arrived. What went wrong, or None. Every failure counts:
        boto3 wraps a refused upload in an error of its own, outside the botocore ones."""
        try:
            s3.upload(key, io.BytesIO(data), content_type)
            if not s3.exists(key):
                return "the upload said it worked, but the image isn't in the bucket"
        except Exception as exc:  # noqa: BLE001: whatever it is, it's reported and the run carries on
            return f"{type(exc).__name__}: {exc}"
        return None
