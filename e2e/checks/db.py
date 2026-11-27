"""Set up the scratch database for a browser check. Refuses to touch any other database.

Run: python e2e/checks/db.py <command>    (the checks call it for you; see e2e/checks/__init__.py)
  migrate   apply any new migrations to the scratch database
  packs     import world_pack/*.json again (its haunts, chatter and scenes), as the CPU page's Import tab does
  save      a fresh world save past the tutorial: a ready deck, coins, standing where someone is
  duel      a fresh town duel against the first person present (needs `save`); prints the room's id
  people    (after `save`) three people met: one a Friend with a record and a gift's reaction, one just met, one at the top
  played    (after `duel`) the latest town duel gets six turns of history: a comeback with a big hit and a cancel
  record    a finished game against a CPU on the profile, with a recap
  stock     the latest town duel: three cards from the player's deck go to their stock (to pay for a card)
  newcomer  (after `save`) someone at the player's place is a newcomer whose arrival hasn't played, with a scene for it;
            prints their name
  finish    the latest town duel ends, the player winning
  lose      the latest town duel ends, the player losing
  player    the non-staff test player (e2e-player): Weiss access, a known password, and no saves, rooms or reports left
  reports   the player's reports are deleted (they are limited to five an hour, so a check that sends some starts clear)
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
os.environ["DJANGO_SQLITE_PATH"] = str(ROOT / "e2e" / "scratch" / "e2e.sqlite3")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
sys.path.insert(0, str(ROOT))
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402

assert "e2e.sqlite3" in str(settings.DATABASES["default"]["NAME"]), "not the scratch database"

from django.contrib.auth.models import User  # noqa: E402
from django.core.management import call_command  # noqa: E402

from weiss import world  # noqa: E402
from weiss.models import Card, GameRoom, WorldReport, WorldSave  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from core.access import WEISS_GROUP  # noqa: E402

USER = "e2e"
SLOT = 1
PLACEHOLDER_SET = 9001  # seed.py's placeholder cards


def migrate():
    call_command("migrate", verbosity=0)
    print("migrated")


def packs():
    """As seed.py does it: the scratch database has only some of the CPUs, so only theirs, and only scenes that cast
    nobody else; world quests are left out (they can point at CPUs that aren't here)."""
    import glob
    import json

    from weiss.cpu_corpus import import_world_pack
    from weiss.models import CpuProfile
    here = {name.lower() for name in CpuProfile.objects.values_list("name", flat=True)} | {"me", "you"}

    def casts(script):
        for line in (chr(10).join(script) if isinstance(script, list) else script).splitlines():
            line = line.strip()
            if line.startswith("cast ") and " as " in line:
                yield line[5:line.index(" as ")].strip().strip('"').lower()

    def fits(scene):
        return all(name in here for name in casts(scene.get("script", "")))

    paths = [path for path in sorted(glob.glob(str(ROOT / "world_pack" / "*.json"))) if "minigame_lines" not in path]
    datas = [json.loads(pathlib.Path(path).read_text(encoding="utf-8")) for path in paths]
    for data in datas:
        data["scenes"] = [scene for scene in data.get("scenes") or [] if fits(scene)]
        if "cpus" in data:
            data["cpus"] = [cpu for cpu in data["cpus"] if cpu.get("name", "").lower() in here]
            for cpu in data["cpus"]:
                if isinstance(cpu.get("scenes"), list):
                    cpu["scenes"] = [scene for scene in cpu["scenes"] if fits(scene)]
                if isinstance(cpu.get("world"), dict):
                    cpu["world"]["quests"] = []
    results = import_world_pack(datas, dry_run=False, user=User.objects.get(username=USER))
    problems = [problem for result in results for problem in result.problems]
    assert not problems, problems[:5]
    print("packs imported:", sum(len(result.done) for result in results), "CPUs")


def save():
    user = User.objects.get(username=USER)
    GameRoom.objects.filter(host=user).delete()
    WorldSave.objects.filter(user=user).delete()
    found = world.start(user, SLOT, PLACEHOLDER_SET)
    cards = list(Card.objects.filter(expansion_id=PLACEHOLDER_SET))
    found.pool = {str(card.pk): 4 for card in cards}
    found.money = 5000
    found.save()
    climax = [card for card in cards if card.card_type == "Climax"][:2]
    # Level 0 characters, the cheapest first (level 0 needs no colour): the board check plays one (with `stock`).
    others = sorted((card for card in cards if card.card_type != "Climax"),
                    key=lambda card: (card.level or 0, card.cost or 0, card.pk))[:14]
    world.save_deck(found, {card.pk: 4 for card in climax} | {card.pk: 3 for card in others})
    found.flags.pop("scene", None)
    found.flags["scene_queue"] = []
    for place in world.places(found):
        if world.present(found, place.key):
            found.place = place.key
            break
    found.save()
    print("save", found.pk, "at", found.place)


def latest_save():
    return WorldSave.objects.get(user__username=USER, slot=SLOT)


def duel():
    found = latest_save()
    GameRoom.objects.filter(host=found.user).delete()
    found.flags.pop("scene", None)
    found.flags["scene_queue"] = []
    found.save()
    cpu = world.town(found)["people"][0]
    room = world.start_duel(found, cpu["id"])
    print(room.pk)


def people():
    """Three people met, for the people journal: the one with the most journal entries a Friend (40 points), with a
    record and a gift they loved; another just met; a third at the top rank. Prints the Friend's id."""
    from weiss.models import Chatter, CpuProfile, GiftItem
    found = latest_save()
    found.relations = {}
    by_entries = sorted(CpuProfile.objects.filter(finalized=True, deck__isnull=False),
                        key=lambda cpu: (-Chatter.objects.filter(cpu=cpu, context="journal").count(), cpu.pk))
    friend, new, best = by_entries[:3]
    gift = GiftItem.objects.order_by("pk").first()
    found.relations[str(friend.pk)] = {"points": 40, "won": 2, "lost": 1, **({"tastes": {gift.key: "loved"}} if gift else {})}
    found.relations[str(new.pk)] = {"points": 0}
    found.relations[str(best.pk)] = {"points": 999}
    found.save()
    print(friend.pk)


def played():
    """Six turns: the player falls 9 points behind (points are damage taken), lands a 5, has a 4 cancelled, and comes
    back to win at the end."""
    room = GameRoom.objects.filter(world_save__user__username=USER).order_by("-pk").first()
    me, cpu = room.state["order"]
    swings = [(2, 0), (5, 1), (12, 3), (14, 9), (15, 16), (16, 28)]  # [my points, theirs] at each turn's end
    room.state["timeline"] = {"points": [{"turn": n, "by": me if n % 2 else cpu, "damage": {me: mine, cpu: theirs}}
                                         for n, (mine, theirs) in enumerate(swings, 1)], "hits": []}
    room.state["timeline_facts"] = {"attacks": [[4, 0, 5, 0], [5, 0, 4, 1], [3, 1, 2, 0]], "climaxes": [[4, 0]]}
    room.state["turn_number"] = len(swings)
    room.save(update_fields=["state"])
    print("played", room.pk)


def record():
    from weiss.models import CpuProfile, GameRecord
    user = User.objects.get(username=USER)
    cpu = CpuProfile.objects.filter(finalized=True).order_by("pk").first()
    GameRecord.objects.filter(host=user).delete()
    GameRecord.objects.create(host=user, guest=None, host_name=USER, guest_name=cpu.name, cpu=True, cpu_profile=cpu, winner="host",
                              reason="level", turns=6, recap={"points": [[1, 2, 0], [2, 5, 1], [3, 12, 3], [4, 14, 9], [5, 15, 16], [6, 16, 28]],
                                                               "moments": [{"kind": "comeback", "turn": 3, "side": "host", "n": 9},
                                                                           {"kind": "big_hit", "turn": 4, "side": "host", "n": 5}]})
    GameRecord.objects.create(host=user, guest=None, host_name=USER, guest_name=cpu.name, cpu=True, cpu_profile=cpu, winner="guest",
                              reason="level", turns=0)  # an older game: no recap, so no button
    print("recorded")


def stock():
    room = GameRoom.objects.filter(world_save__user__username=USER).order_by("-pk").first()
    zones = room.state["players"][str(room.host_id)]["zones"]
    for _ in range(3):
        zones["stock"].append(zones["deck"].pop())
    room.version += 1
    room.save(update_fields=["state", "version"])
    print("stock", len(zones["stock"]))


def newcomer():
    """Someone here now is a newcomer not met yet (as a new week leaves them: world_roster.week_started), with an arrival
    scene with someone else in town. The scratch database's cast is too small for a real second week."""
    from weiss.models import Scene
    found = latest_save()
    here = [cpu for cpu, _ in world.present(found)]
    assert here, "nobody's at the save's place"
    cpu = here[0]
    other = next(c for c in CpuProfile_all() if c.pk != cpu.pk)
    Scene.objects.filter(name__istartswith=f"World: Arrival, {cpu.name}").delete()
    Scene.objects.create(name=f"World: Arrival, {cpu.name} & {other.name}", script="\n".join([
        f"cast new as {cpu.name}", f"cast old as {other.name}", "background sakura",
        "new: Hello! I've only just got here.", "old: Welcome to town.", "choice Who do you stand with?",
        "- The newcomer (set side_new)", "- The one who was here first (set side_old)"]))
    found.flags["arrivals"] = [cpu.pk]
    found.flags.pop("scene", None)
    found.flags.pop("scene_queue", None)
    found.save()
    print(cpu.name)


def CpuProfile_all():
    from weiss.models import CpuProfile
    return list(CpuProfile.objects.filter(finalized=True).order_by("pk"))


def finish(player_wins=True):
    room = GameRoom.objects.filter(world_save__user__username=USER).order_by("-pk").first()
    winner = str(room.host_id) if player_wins else str(room.guest_id)
    over = {"winner": winner, "reason": "level", "rematch": []}
    room.state["game_over"] = over
    room.version += 1
    room.save(update_fields=["state", "version"])
    world.game_finished(room, over)
    print("finished", room.pk)


PLAYER = "e2e-player"
PLAYER_PASSWORD = "e2e-player-pass"


def player():
    """A regular player: not staff, in the Weiss group, with nothing left from an earlier run (saves, rooms, reports)."""
    user, _ = User.objects.get_or_create(username=PLAYER)
    user.is_staff = user.is_superuser = False
    user.is_active = True
    user.set_password(PLAYER_PASSWORD)
    user.save()
    user.groups.add(Group.objects.get_or_create(name=WEISS_GROUP)[0])
    GameRoom.objects.filter(host=user).delete()
    WorldSave.objects.filter(user=user).delete()
    WorldReport.objects.filter(user=user).delete()
    print("player", user.pk)


def reports():
    from weiss.models import WorldReport
    deleted, _ = WorldReport.objects.filter(user__username=USER).delete()
    print("reports deleted", deleted)


COMMANDS = {"player": player, "reports": reports, "migrate": migrate, "packs": packs, "save": save, "duel": duel, "people": people, "played": played, "record": record, "stock": stock, "newcomer": newcomer, "finish": finish, "lose": lambda: finish(False)}

if __name__ == "__main__":
    for name in sys.argv[1:]:
        COMMANDS[name]()
