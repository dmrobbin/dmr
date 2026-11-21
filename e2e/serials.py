"""Every card the corpus CPUs' decks and anchors name, one serial per line: what the scratch database needs."""
import glob
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The tutorial's four guides, and Ruby (Hoshino and Rose): the CPUs the scratch database is built with.
GUIDES = {"Aang", "Asuna Yuuki", "Chisato Nishikigi", "Erza Scarlet", "Ruby Hoshino", "Ruby Rose"}
serials = set()
for path in glob.glob(str(ROOT / "corpus" / "cpus" / "*.json")):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if data["profile"]["name"] not in GUIDES:
        continue
    deck = data["deck"]
    serials.update(serial for serial, _ in deck["cards"])
    serials.update(deck.get("anchors", []))
out = ROOT / "e2e" / "scratch" / "serials.txt"
out.write_text("\n".join(sorted(serials)) + "\n", encoding="utf-8")
print(len(serials), "serials ->", out)
