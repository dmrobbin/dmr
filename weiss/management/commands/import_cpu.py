import json
import random
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from weiss.cpu_corpus import CorpusError, import_cpu


class Command(BaseCommand):
    help = ("Make CPUs from their files: profile, deck (built by express building from its series and anchors) and scenes. "
            "Each file goes in whole or not at all, and none are finalized (see weiss.cpu_corpus).")

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+", help="CPU files, as export_cpu_corpus writes them")
        parser.add_argument("--user", help="Who owns the decks and made the CPUs (default: the first superuser)")
        parser.add_argument("--seed", type=int, help="For express building, so a dry run's deck is the one a real run builds")
        parser.add_argument("--dry-run", action="store_true", help="Check the files without saving anything")

    def handle(self, *args, **options):
        database = connection.settings_dict
        # Said first, so a run against the wrong database is plain to see.
        self.stdout.write(f"Saving to the {connection.vendor} database {database.get('NAME')}" + (f" on {database['HOST']}" if database.get("HOST") else "")
                          + (" (dry run: nothing will be saved)" if options["dry_run"] else ""))
        users = User.objects.filter(username=options["user"]) if options["user"] else User.objects.filter(is_superuser=True).order_by("pk")
        user = users.first()
        if not user:
            raise CommandError(f"There's no user {options['user']}." if options["user"] else "There's no superuser: use --user.")
        failed = 0
        for path in options["files"]:
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                profile, notes = import_cpu(data, user, rng=random.Random(options["seed"]), dry_run=options["dry_run"])
            except (OSError, ValueError) as error:
                failed += 1
                self.stderr.write(f"{path}: couldn't be read: {error}")
                continue
            except CorpusError as error:
                failed += 1
                self.stderr.write(f"{path}: not imported:")
                for problem in error.problems:
                    self.stderr.write(f"  - {problem}")
                continue
            for note in notes:
                self.stdout.write(f"{path}: {note}")
            done = "would be made" if options["dry_run"] else f"made as #{profile.pk}, not finalized"
            self.stdout.write(self.style.SUCCESS(f"{path}: {profile.name} {done}, with {len(data.get('scenes') or [])} scene(s)"))
        if failed:
            raise CommandError(f"{failed} of {len(options['files'])} file{'s' if len(options['files']) != 1 else ''} couldn't be imported.")
