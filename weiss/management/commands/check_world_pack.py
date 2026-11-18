"""Check world pack files (corpus/world/) against the export's CPUs, without them being in this database: every
problem the Import tab would find with the packs, and the CPUs they name that the export hasn't got."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from weiss.cpu_corpus import import_world_pack


class Command(BaseCommand):
    help = "Check world pack files against an export's CPUs (default corpus/)."

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+", help="World pack files to check")
        parser.add_argument("--corpus", default="corpus", help="The export's folder (default corpus)")

    def handle(self, *args, **options):
        folder = Path(options["corpus"]) / "cpus"
        if not folder.exists():
            raise CommandError(f"There's no export in {folder.parent.resolve()}: download it from the Import tab.")
        known = [json.loads(path.read_text(encoding="utf-8"))["profile"]["name"] for path in folder.glob("*.json")]
        datas = [json.loads(Path(path).read_text(encoding="utf-8")) for path in options["files"]]
        failed = 0
        for path, result in zip(options["files"], import_world_pack(datas, known=known)):
            if result.problems or result.missing:
                failed += 1
                self.stderr.write(f"{path}:")
                for problem in result.problems:
                    self.stderr.write(f"  - {problem}")
                if result.missing:
                    self.stderr.write(f"  - not in the export: {', '.join(result.missing)}")
            else:
                self.stdout.write(self.style.SUCCESS(f"{path}: {len(result.done)} CPUs, no problems found"))
        if failed:
            raise CommandError(f"{failed} file{'s' if failed != 1 else ''} with problems.")
