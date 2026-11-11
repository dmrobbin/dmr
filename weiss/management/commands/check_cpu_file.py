import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from weiss.cpu_corpus import check_offline, load_corpus


class Command(BaseCommand):
    help = ("Check new CPUs' files against an export from export_cpu_corpus rather than the database: profile, anchors, "
            "names already taken and every scene. For writing CPUs away from the database they'll go in; "
            "import_cpu --dry-run there is the last word.")

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+", help="CPU files to check")
        parser.add_argument("--corpus", default="corpus", help="The export's folder (default corpus)")

    def handle(self, *args, **options):
        folder = Path(options["corpus"])
        if not (folder / "scenes.json").exists():
            raise CommandError(f"There's no export in {folder.resolve()}: run export_cpu_corpus where the CPUs are.")
        cpus, scene_names, anchors = load_corpus(folder)
        failed = 0
        for path in options["files"]:
            try:
                problems = check_offline(json.loads(Path(path).read_text(encoding="utf-8")), cpus, scene_names, anchors)
            except (OSError, ValueError) as error:
                problems = [f"couldn't be read: {error}"]
            if problems:
                failed += 1
                self.stderr.write(f"{path}:")
                for problem in problems:
                    self.stderr.write(f"  - {problem}")
            else:
                self.stdout.write(self.style.SUCCESS(f"{path}: no problems found"))
        if failed:
            raise CommandError(f"{failed} of {len(options['files'])} file{'s' if len(options['files']) != 1 else ''} had problems.")
