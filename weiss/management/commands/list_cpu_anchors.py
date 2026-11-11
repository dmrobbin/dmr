import json

from django.core.management.base import BaseCommand, CommandError

from weiss.cpu_corpus import anchor_report


class Command(BaseCommand):
    help = ("List, as JSON, the cx combo cards a CPU deck in a series can be built around: each with its climaxes "
            "and the CPUs whose decks already have it. Reads only.")

    def add_arguments(self, parser):
        parser.add_argument("series", help="A series code, e.g. NIK")
        parser.add_argument("--unused", action="store_true", help="Only cards no CPU's deck has yet")

    def handle(self, *args, **options):
        anchors = anchor_report(options["series"])
        if not anchors:
            raise CommandError(f"The series {options['series']} has no cx combo cards a CPU can play.")
        if options["unused"]:
            anchors = [a for a in anchors if not a["used_by"]]
        self.stdout.write(json.dumps(anchors, indent=2, ensure_ascii=False))
