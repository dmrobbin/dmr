import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from weiss.cpu_corpus import import_cpus


class Command(BaseCommand):
    help = ("Make CPUs from their files: profile, deck (built by express building from its series and anchors) and scenes. "
            "The files go in together, whole or not at all, so their scenes can cast each other; none are finalized "
            "(see weiss.cpu_corpus). The CPU tab's Import page does the same from a browser.")

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
        paths, files = options["files"], []
        for path in paths:
            try:
                files.append(json.loads(Path(path).read_text(encoding="utf-8")))
            except (OSError, ValueError) as error:
                raise CommandError(f"{path}: couldn't be read: {error}") from error
        results = import_cpus(files, user, seed=options["seed"], dry_run=options["dry_run"])
        failed = [path for path, result in zip(paths, results) if result.problems]
        for path, result in zip(paths, results):
            if result.problems:
                self.stderr.write(f"{path}: not imported:")
                for problem in result.problems:
                    self.stderr.write(f"  - {problem}")
                continue
            for note in result.notes:
                self.stdout.write(f"{path}: {note}")
            done = "would be made" if options["dry_run"] or failed else f"made as #{result.profile.pk}, not finalized"
            self.stdout.write(self.style.SUCCESS(f"{path}: {result.profile.name} {done}, with {len(result.scenes)} scene(s)"))
        if failed:
            raise CommandError(f"{len(failed)} of {len(paths)} file{'s' if len(paths) != 1 else ''} had problems, so none were imported.")
