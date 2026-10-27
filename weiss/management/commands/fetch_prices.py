from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from weiss import tcgcsv
from weiss.models import Card, CardPrice

PRICE_FIELDS = ("market_price", "low_price", "mid_price", "high_price")


class Command(BaseCommand):
    help = "Update TCGplayer prices (from tcgcsv.com) for saved Weiss Schwarz cards, matched by serial number."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--expansion", type=int, help="Our expansion number, e.g. 290")
        target.add_argument("--all", action="store_true", help="Every expansion with saved cards")
        parser.add_argument("--group", type=int, help="TCGplayer group ID, if the set name doesn't match (with --expansion)")
        parser.add_argument("--dry-run", action="store_true", help="Show matches without saving")

    def handle(self, *args, **options):
        if options["expansion"]:
            expansions = [options["expansion"]]
            if not Card.objects.filter(expansion_id=options["expansion"]).exists():
                raise CommandError(f"No saved cards for expansion {options['expansion']}; run fetch_cards first.")
        else:
            expansions = list(Card.objects.exclude(expansion_id=None).values_list("expansion_id", flat=True)
                              .distinct().order_by("expansion_id"))

        for expansion_id in expansions:
            try:
                self.update_set(expansion_id, options["group"], options["dry_run"])
            except tcgcsv.TcgcsvError as exc:
                self.stderr.write(self.style.ERROR(f"Expansion {expansion_id}: {exc}"))

    def update_set(self, expansion_id, group_id, dry_run):
        cards = list(Card.objects.filter(expansion_id=expansion_id))
        name = cards[0].expansion
        if group_id:
            group_ids, label = [group_id], f"group #{group_id}"
        else:
            found = tcgcsv.find_groups(name, [card.serial_number for card in cards])
            if not found:
                self.stderr.write(self.style.ERROR(
                    f"{name}: couldn't find these cards on TCGplayer. Find the set's group ID on "
                    f"https://tcgcsv.com/tcgplayer/{tcgcsv.WEISS_CATEGORY_ID}/groups and pass --group."
                ))
                return
            group_ids = [group["groupId"] for group, _ in found]
            label = ", ".join(f"{group['name']} #{group['groupId']}" for group, _ in found)

        # The best-matching group wins when a card number appears in more than one.
        prices = {}
        for gid in reversed(group_ids):
            prices.update(tcgcsv.card_prices(gid))
        matched = [card for card in cards if card.serial_number in prices]
        for card in matched:
            info = prices[card.serial_number]
            if dry_run:
                self.stdout.write(f"  {card.serial_number} {card.name}: {self.money(info['market_price'])}")
                continue
            values = {k: Decimal(str(v)) if k in PRICE_FIELDS and v is not None else v for k, v in info.items()}
            CardPrice.objects.update_or_create(card=card, source=CardPrice.Source.TCGPLAYER, defaults=values)

        missing = len(cards) - len(matched)
        verb = "would update" if dry_run else "updated"
        self.stdout.write(self.style.SUCCESS(
            f"{name} (TCGplayer: {label}): {verb} {len(matched)} prices"
            + (f", {missing} cards not on TCGplayer" if missing else "")
        ))

    def money(self, value):
        return f"${value:,.2f}" if value is not None else "no market price"
