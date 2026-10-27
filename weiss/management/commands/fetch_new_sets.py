from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from weiss.models import Card
from weiss.scraper import ScraperError, expansions


class Command(BaseCommand):
    help = (
        "Fetch cards and prices for the newest expansions that haven't been saved yet. "
        "Newest means the highest expansion number, which the site assigns in release order."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=5, help="How many new sets to fetch (default 5)")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests to the card site")
        parser.add_argument("--dry-run", action="store_true", help="Only list which sets would be fetched")

    def handle(self, *args, **options):
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

        call_command(
            "fetch_sets", *[str(number) for number, _ in new],
            delay=options["delay"], stdout=self.stdout, stderr=self.stderr,
        )
