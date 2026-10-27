from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from django.utils import timezone

from weiss.models import Card
from weiss.scraper import ScraperError, expansions

# TCGCSV updates once a day, so refreshing a set's prices more often than this gains nothing.
PRICE_REFRESH_HOURS = 20


class Command(BaseCommand):
    help = (
        "Fetch cards and prices for the newest expansions that haven't been saved yet. "
        "Newest means the highest expansion number, which the site assigns in release order."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=5, help="How many new sets to fetch (default 5)")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests to the card site")
        parser.add_argument("--refresh-prices", action="store_true",
                            help=f"Also update prices for saved sets not priced in the last {PRICE_REFRESH_HOURS} hours")
        parser.add_argument("--dry-run", action="store_true", help="Only list what would be fetched")

    def handle(self, *args, **options):
        self.fetch_new(options)
        if options["refresh_prices"]:
            self.refresh_prices(options["dry_run"])

    def fetch_new(self, options):
        try:
            available = expansions()
        except ScraperError as exc:
            raise CommandError(exc)
        saved = set(Card.objects.exclude(expansion_id=None).values_list("expansion_id", flat=True).distinct())
        new = sorted(((n, name) for n, name in available if n not in saved), reverse=True)[: options["count"]]
        if not new:
            self.stdout.write(self.style.SUCCESS("Every expansion on the site is already saved."))
            return

        self.stdout.write(f"{len(new)} newest set{'s' if len(new) != 1 else ''} not saved yet:")
        for number, name in new:
            self.stdout.write(f"{number:>5}  {name}")
        if options["dry_run"]:
            return

        # fetch_sets also prices each new set, so refresh_prices will find them up to date.
        call_command(
            "fetch_sets", *[str(number) for number, _ in new],
            delay=options["delay"], stdout=self.stdout, stderr=self.stderr,
        )

    def refresh_prices(self, dry_run):
        cutoff = timezone.now() - timedelta(hours=PRICE_REFRESH_HOURS)
        last_priced = (
            Card.objects.exclude(expansion_id=None)
            .values("expansion_id")
            .annotate(last=Max("prices__fetched_at"))
        )
        stale = sorted(row["expansion_id"] for row in last_priced if not row["last"] or row["last"] < cutoff)
        if not stale:
            self.stdout.write(f"Prices for every saved set are less than {PRICE_REFRESH_HOURS} hours old.")
            return
        self.stdout.write(f"Refreshing prices for {len(stale)} set{'s' if len(stale) != 1 else ''}: "
                          + ", ".join(map(str, stale)))
        if dry_run:
            return
        for expansion_id in stale:
            # fetch_prices reports its own per-set problems and carries on.
            call_command("fetch_prices", expansion=expansion_id, stdout=self.stdout, stderr=self.stderr)
