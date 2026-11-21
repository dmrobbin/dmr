"""Seed the scratch database for the end-to-end tests: a staff user, the 75 corpus CPUs (finalized where their decks are
legal), and the world pack. Run after fetch_cards.py. Refuses to run against anything but the scratch database."""
import glob
import json
import os
import pathlib
import random
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.core.management import call_command  # noqa: E402

from weiss.cpu_corpus import import_cpus, import_world_pack  # noqa: E402
from weiss.cpu_views import deck_problem  # noqa: E402
from weiss.models import Card, CpuProfile  # noqa: E402

PLACEHOLDER_SET = 9001  # a set of placeholder cards, so a new save has enough cards to make packs (not a real set)


def placeholder_set():
    """120 placeholder cards in one set: characters at levels 0 to 3 in each rarity, and climaxes. No pictures."""
    if Card.objects.filter(expansion_id=PLACEHOLDER_SET).exists():
        return
    colors = ["Red", "Blue", "Yellow", "Green", "Purple"]
    cards = []
    for n in range(100):
        level = n % 4
        cards.append(Card(serial_number=f"E2E/PH-{n:03}", name=f"Placeholder {n}", expansion="E2E Placeholder",
                          expansion_id=PLACEHOLDER_SET, card_type="Character", rarity=["C", "C", "U", "R", "RR"][n % 5],
                          pack_rarity="", level=level, cost=1 + n % 3, power=1000 * (level + 1) + n, color=colors[n % 5]))
    for n in range(20):
        cards.append(Card(serial_number=f"E2E/PH-C{n:03}", name=f"Placeholder climax {n}", expansion="E2E Placeholder",
                          expansion_id=PLACEHOLDER_SET, card_type="Climax", rarity="CC", pack_rarity="", level=None,
                          cost=0, power=0, color=colors[n % 5]))
    Card.objects.bulk_create(cards)
    print(f"placeholder set {PLACEHOLDER_SET}: {len(cards)} cards")



assert "scratch" in str(settings.DATABASES["default"]["NAME"]), "not the scratch database"
user, _ = User.objects.get_or_create(username="e2e", defaults={"is_staff": True, "is_superuser": True})
user.set_password("e2e-pass")
user.save()

GUIDES = {"Aang", "Asuna Yuuki", "Chisato Nishikigi", "Erza Scarlet", "Ruby Hoshino", "Ruby Rose"}  # see serials.py
placeholder_set()
paths = sorted(path for path in glob.glob(str(ROOT / "corpus" / "cpus" / "*.json"))
               if json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["profile"]["name"] in GUIDES)
files = [json.loads(pathlib.Path(path).read_text(encoding="utf-8")) for path in paths]
# Only the six CPUs are imported, so a scene that casts anyone else can't be made: those scenes are left out here.
# (The full world pack's scenes need all 75 CPUs, which the scratch database doesn't have yet.)
allowed = {name.lower() for name in GUIDES}
def casts(script):
    if isinstance(script, list):
        script = chr(10).join(script)
    for line in script.splitlines():
        line = line.strip()
        if line.startswith("cast ") and " as " in line:
            yield line[5:line.index(" as ")].strip().strip('"').lower()
for data in files:
    kept = [scene for scene in data.get("scenes", []) if all(name in allowed for name in casts(scene.get("script", "")))]
    print(f"{data['profile']['name']}: {len(data.get('scenes', []))} scenes, {len(kept)} kept")
    data["scenes"] = kept
if CpuProfile.objects.filter(name__in=GUIDES).count() == len(GUIDES):
    results = []  # already imported by an earlier run of this script: the seed is safe to run again
    print("CPUs already imported")
else:
    results = import_cpus(files, user, seed=1)
problems = [(path, result.problems) for path, result in zip(paths, results) if result.problems]
if problems:
    for path, found in problems:
        print(path, found)
    raise SystemExit(f"{len(problems)} CPU file(s) not imported")
print(f"CPU files: {len(paths)}")

finalized = skipped = 0
for profile in CpuProfile.objects.filter(finalized=False):
    if deck_problem(profile.deck):
        skipped += 1
        continue
    profile.finalized = True
    profile.save(update_fields=["finalized"])
    finalized += 1
print(f"finalized {finalized} CPUs; {skipped} still have a deck problem")

packs = sorted(glob.glob(str(ROOT / "world_pack" / "*.json")))
packs = [path for path in packs if "minigame_lines" not in path]
datas = [json.loads(pathlib.Path(path).read_text(encoding="utf-8")) for path in packs]
# Same limit as the CPUs: only the six guides' world parts, and scenes that cast only people who are here.
allowed = allowed | {"me", "you"}
def keep_scenes(scenes):
    return [scene for scene in scenes if all(name in allowed for name in casts(scene.get("script", "")))]
for data in datas:
    if "cpus" in data:
        data["cpus"] = [cpu for cpu in data["cpus"] if cpu.get("name", "").lower() in allowed]
        for cpu in data["cpus"]:
            if isinstance(cpu.get("scenes"), list):
                cpu["scenes"] = keep_scenes(cpu["scenes"])
            if isinstance(cpu.get("world"), dict):
                cpu["world"]["quests"] = []
    # The story's own scenes and quests are the tutorial's, and import as they are. A CPU's world quests can point at
    # CPUs and quests that the scratch database doesn't have: they're left out of the test copy.
for path, result in zip(packs, import_world_pack(datas, dry_run=False, user=user)):
    if result.problems:
        print(path, result.problems)
    else:
        print(f"{pathlib.Path(path).name}: {len(result.done)} CPUs given their world part")
print("seed done")
