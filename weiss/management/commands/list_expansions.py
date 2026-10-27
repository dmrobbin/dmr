from django.core.management.base import BaseCommand, CommandError

from weiss.models import Card
from weiss.scraper import ScraperError, expansions, fetch_card


class Command(BaseCommand):
    help = "Look up expansion numbers: search the site's expansion list by name, or find the set a card is in."

    def add_arguments(self, parser):
        parser.add_argument("search", nargs="?", default="", help="Part of an expansion name, e.g. nikke")
        parser.add_argument("--card", metavar="SERIAL", help="Find the expansion this card is in, e.g. NIK/S135-E001")

    def handle(self, *args, **options):
        try:
            if options["card"]:
                self.find_card(options["card"])
            else:
                self.search(options["search"])
        except ScraperError as exc:
            raise CommandError(exc)

    def search(self, text):
        saved = set(Card.objects.values_list("expansion_id", flat=True).distinct())
        matches = [(number, name) for number, name in expansions() if text.lower() in name.lower()]
        if not matches:
            raise CommandError(f"No expansions match '{text}'.")
        for number, name in sorted(matches):
            self.stdout.write(f"{number:>5}  {name}{'   (saved)' if number in saved else ''}")
        self.stdout.write(f"{len(matches)} expansion{'s' if len(matches) != 1 else ''}.")

    def find_card(self, serial):
        card = fetch_card(serial)
        if not card:
            raise CommandError(f"{serial} isn't on the card list.")
        self.stdout.write(f"{card['serial_number']} {card['name']}")
        self.stdout.write(f"Expansion {card['expansion_id']}: {card['expansion']}")
