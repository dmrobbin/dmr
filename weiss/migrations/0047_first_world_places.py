"""World mode's first places: the town test's eight (weiss.world_views.PLACES), each with its backdrops."""
from django.db import migrations

PLACES = (
    ("plaza", "Plaza", ["sakura", "sakura", "sakura", "city"]),
    ("cafe", "Café", ["cafe"] * 4),
    ("library", "Library", ["library"] * 4),
    ("arena", "Duel arena", ["arena"] * 4),
    ("shrine", "Shrine", ["shrine"] * 4),
    ("beach", "Beach", ["beach", "beach", "dusk", "night"]),
    ("forest", "Forest", ["forest"] * 4),
    ("school", "School", ["classroom", "classroom", "rooftop", "rooftop"]),
)


def add(apps, schema_editor):
    WorldPlace = apps.get_model("weiss", "WorldPlace")
    for order, (key, name, backdrops) in enumerate(PLACES):
        WorldPlace.objects.get_or_create(key=key, defaults={"name": name, "backdrops": backdrops, "order": order})


def remove(apps, schema_editor):
    apps.get_model("weiss", "WorldPlace").objects.filter(key__in=[key for key, _, _ in PLACES]).delete()


class Migration(migrations.Migration):
    dependencies = [("weiss", "0046_world_places")]
    operations = [migrations.RunPython(add, remove)]
