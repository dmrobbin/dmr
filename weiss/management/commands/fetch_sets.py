from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "For each expansion given, run fetch_cards and then fetch_prices."

    def add_arguments(self, parser):
        parser.add_argument("expansions", nargs="+", type=int, metavar="EXPANSION", help="e.g. 290 291")
        parser.add_argument("--skip-existing", action="store_true", help="Don't re-fetch cards already saved")
        parser.add_argument("--refresh-images", action="store_true", help="Re-upload images already on S3")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests to the card site")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be saved without saving")

    def handle(self, *args, **options):
        card_options = {
            key: options[key] for key in ("skip_existing", "refresh_images", "delay", "dry_run")
        }
        failed = []
        for i, expansion in enumerate(options["expansions"], 1):
            self.stdout.write(self.style.MIGRATE_HEADING(f"[{i}/{len(options['expansions'])}] Expansion {expansion}"))
            try:
                call_command("fetch_cards", expansion=expansion, stdout=self.stdout, stderr=self.stderr, **card_options)
                if options["dry_run"]:
                    # Prices attach to saved cards, and a dry run doesn't save any.
                    self.stdout.write("Skipping prices on a dry run.")
                else:
                    call_command("fetch_prices", expansion=expansion, stdout=self.stdout, stderr=self.stderr)
            except CommandError as exc:
                # One bad set shouldn't stop the rest.
                self.stderr.write(self.style.ERROR(f"Expansion {expansion}: {exc}"))
                failed.append(expansion)

        done = len(options["expansions"]) - len(failed)
        summary = f"Finished {done} of {len(options['expansions'])} expansions"
        if failed:
            self.stdout.write(self.style.WARNING(f"{summary}; failed: {', '.join(map(str, failed))}."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{summary}."))
