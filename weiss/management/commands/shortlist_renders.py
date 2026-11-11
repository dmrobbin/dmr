import html
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from weiss import card_images


class Command(BaseCommand):
    help = ("List PNGitem's likeliest full body renders of characters, for a CPU's pictures: download one from its page by hand "
            "(PNGitem doesn't allow robots to), then upload it on the CPU's images page. Reads no database.")

    def add_arguments(self, parser):
        parser.add_argument("names", nargs="*", help='Characters to look for, e.g. "Mami Tomoe" Kirito')
        parser.add_argument("--cpu", nargs="+", default=[], metavar="FILE", help="CPU files (as in corpus/new/): their profiles' names")
        parser.add_argument("--show", default="", help="The show, searched with the name when the name alone finds too few")
        parser.add_argument("--count", type=int, default=card_images.SHORTLIST, help=f"Renders for each (default {card_images.SHORTLIST})")
        parser.add_argument("--html", metavar="FILE", help="Also write a page of them, with pictures, to open in a browser")

    def handle(self, *args, **options):
        names = list(options["names"])
        for path in options["cpu"]:
            try:
                names.append(json.loads(Path(path).read_text(encoding="utf-8"))["profile"]["name"])
            except (OSError, ValueError, KeyError) as error:
                raise CommandError(f"{path}: no CPU's name in it ({error}).") from error
        if not names:
            raise CommandError("Give some characters' names, or --cpu files.")
        cast, titles = [], []
        if options["show"]:  # the show's cast, so group pictures can be told apart from pictures of one character
            try:
                cast, titles = card_images.anilist_show(options["show"])
            except card_images.ImageSourceError as error:
                self.stderr.write(f"AniList couldn't be searched, so group pictures may be listed too: {error}")
            if not cast:
                self.stderr.write(f"AniList knows no cast for “{options['show']}”, so group pictures may be listed too.")
        found = {}
        for name in names:
            # AniList's other names for them (often surname first) count as naming them too.
            character = next((c for c in cast if card_images.names_match(name.lower().split(), " ".join(c["names"]).lower())),
                             {"name": name, "names": [name]})
            character = {**character, "name": name}
            try:
                found[name] = card_images.render_shortlist(character, options["show"], options["count"], cast=cast, show_titles=titles)
            except card_images.ImageSourceError as error:
                self.stderr.write(f"{name}: PNGitem couldn't be searched: {error}")
                continue
            self.stdout.write(f"{name}: {len(found[name]) or 'nothing'}{' found' if not found[name] else ''}")
            for result in found[name]:
                self.stdout.write(f"  {result['width']}x{result['height']}  {result['title']}\n    {result['page']}")
        if options["html"]:
            Path(options["html"]).write_text(self.page(found), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Wrote {Path(options['html']).resolve()}"))

    def page(self, found):
        sections = []
        for name, results in found.items():
            cards = "".join(
                f'<a class="card" href="{html.escape(r["page"])}" target="_blank" rel="noopener">'
                f'<img src="{html.escape(r["thumb"])}" alt="" loading="lazy"><span>{html.escape(r["title"])}</span>'
                f'<small>{r["width"]}×{r["height"]}</small></a>' for r in results) or "<p>Nothing on PNGitem.</p>"
            sections.append(f"<h2>{html.escape(name)}</h2><div class=\"cards\">{cards}</div>")
        return ("<!doctype html><meta charset=\"utf-8\"><title>Render shortlist</title><style>"
                "body{font:15px system-ui,sans-serif;margin:24px;background:#f4f4f6;color:#222}"
                ".cards{display:flex;flex-wrap:wrap;gap:12px}.card{width:180px;background:#fff;border-radius:8px;padding:8px;"
                "text-decoration:none;color:inherit;box-shadow:0 1px 3px #0002}.card img{width:100%;height:220px;object-fit:contain}"
                ".card span{display:block;font-size:13px;margin-top:6px}.card small{color:#777}</style>"
                "<h1>Render shortlist</h1><p>Open one, use its Download button for the transparent PNG, then upload it on the CPU's images page.</p>"
                + "".join(sections))
