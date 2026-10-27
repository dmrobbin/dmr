import io
import time

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import s3
from weiss.models import Card
from weiss.scraper import ScraperError, expansion_serials, fetch, fetch_card

IMAGE_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}


def image_key(card):
    """weiss/<expansion number>/<serial>.png; the '/' inside serials like NIK/S135-E001 becomes '-'."""
    expansion = card["expansion_id"] or "unknown"
    return f"{settings.WEISS_S3_PREFIX}{expansion}/{card['serial_number'].replace('/', '-')}"


class Command(BaseCommand):
    help = "Save Weiss Schwarz card details from en.ws-tcg.com, with each card image copied to S3."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--expansion", type=int, help="Every card in this expansion, e.g. 290")
        target.add_argument("--card", nargs="+", metavar="SERIAL", help="One or more serial numbers, e.g. NIK/S135-E001S")
        parser.add_argument("--skip-existing", action="store_true", help="Don't re-fetch cards already saved")
        parser.add_argument("--refresh-images", action="store_true", help="Re-upload images already on S3")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests to the site (default 1)")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be saved without saving")

    def handle(self, *args, **options):
        self.delay = options["delay"]
        if options["expansion"]:
            self.stdout.write(f"Listing cards in expansion {options['expansion']}...")
            try:
                serials = expansion_serials(options["expansion"], self.delay)
            except ScraperError as exc:
                raise CommandError(exc)
            if not serials:
                raise CommandError(f"No cards found for expansion {options['expansion']}.")
            self.stdout.write(f"Found {len(serials)} cards.")
        else:
            serials = options["card"]

        if options["skip_existing"]:
            existing = Card.objects.filter(serial_number__in=serials)
            if settings.AWS_S3_BUCKET:
                # A card whose image never made it to S3 (e.g. the download failed) isn't done yet.
                existing = existing.exclude(image_s3_key="", image_url__gt="")
            existing = set(existing.values_list("serial_number", flat=True))
            serials = [s for s in serials if s not in existing]
            self.stdout.write(f"Skipping {len(existing)} cards already saved.")

        if not settings.AWS_S3_BUCKET and not options["dry_run"]:
            self.stderr.write(self.style.WARNING("AWS_S3_BUCKET isn't set, so card images won't be copied to S3."))

        saved = failed = 0
        for i, serial in enumerate(serials):
            if i:
                time.sleep(self.delay)
            try:
                card = fetch_card(serial)
                if not card:
                    self.stderr.write(self.style.ERROR(f"{serial}: not found on the card list"))
                    failed += 1
                    continue
                if options["dry_run"]:
                    self.stdout.write(f"  {self.describe(card)}")
                else:
                    self.save(card, options["refresh_images"])
                saved += 1
            except (ScraperError, BotoCoreError, ClientError) as exc:
                self.stderr.write(self.style.ERROR(f"{serial}: {exc}"))
                failed += 1

        verb = "Would save" if options["dry_run"] else "Saved"
        self.stdout.write(self.style.SUCCESS(f"{verb} {saved} cards" + (f", {failed} failed." if failed else ".")))

    def save(self, card, refresh_image):
        obj, created = Card.objects.update_or_create(serial_number=card["serial_number"], defaults=card)
        image_note = ""
        if settings.AWS_S3_BUCKET and card["image_url"] and (refresh_image or not obj.image_s3_key):
            time.sleep(self.delay)
            data, content_type = fetch(card["image_url"])
            key = image_key(card) + IMAGE_EXTENSIONS.get(content_type, "")
            s3.upload(key, io.BytesIO(data), content_type)
            obj.image_s3_key = key
            obj.save(update_fields=["image_s3_key"])
            image_note = f" → s3://{settings.AWS_S3_BUCKET}/{key}"
        self.stdout.write(f"  {'+' if created else '~'} {self.describe(card)}{image_note}")

    def describe(self, card):
        return f"{card['serial_number']} {card['name']} ({card['card_type']}, {card['rarity']})"
