from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection

from weiss.cpu_corpus import export_corpus


class Command(BaseCommand):
    help = ("Write every CPU profile, its deck and its scenes out as JSON, with every scene and a reference of what a CPU's "
            "file can hold, as examples to write new CPUs from (see weiss.cpu_corpus).")

    def add_arguments(self, parser):
        parser.add_argument("--out", default="corpus", help="The folder to write to (default corpus)")

    def handle(self, *args, **options):
        database = connection.settings_dict
        self.stdout.write(f"Reading the {connection.vendor} database {database.get('NAME')}" + (f" on {database['HOST']}" if database.get("HOST") else ""))
        out = Path(options["out"])
        files = export_corpus()
        for path, text in files.items():
            (out / path).parent.mkdir(parents=True, exist_ok=True)
            (out / path).write_text(text, encoding="utf-8")
        cpus = sum(path.startswith("cpus/") for path in files)
        self.stdout.write(self.style.SUCCESS(f"Wrote {cpus} CPU{'s' if cpus != 1 else ''}, the scenes and the reference to {out.resolve()}"))
