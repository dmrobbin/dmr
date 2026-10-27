import csv
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from weiss.models import Card
from weiss.scraper import ScraperError, expansions


class Command(BaseCommand):
    help = "Save every expansion on the Weiss Schwarz site to a CSV file (opens in Excel / Google Sheets)."

    def add_arguments(self, parser):
        parser.add_argument("--output", "-o", default="expansions.csv", help="File to write (default: expansions.csv)")

    def handle(self, *args, **options):
        try:
            found = expansions()
        except ScraperError as exc:
            raise CommandError(exc)
        saved = Counter(Card.objects.exclude(expansion_id=None).values_list("expansion_id", flat=True))

        # utf-8-sig adds the byte-order mark Excel needs to show accented and special characters correctly.
        with open(options["output"], "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Expansion number", "Name", "Saved on site", "Cards saved"])
            for number, name in sorted(found, reverse=True):
                writer.writerow([number, name, "yes" if saved[number] else "no", saved[number]])

        self.stdout.write(self.style.SUCCESS(f"Wrote {len(found)} expansions to {options['output']}"))
