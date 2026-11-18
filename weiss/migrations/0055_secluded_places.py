"""Out-of-the-way places in world mode's town, where villains keep to: a back alley, an old warehouse and a rooftop,
open from the start. The shrine and the forest are quiet enough to count too."""
from django.db import migrations

PLACES = [  # (key, name, backdrops: morning, noon, evening, night)
    ("alley", "Back alley", ["rain", "rain", "dusk", "night"]),
    ("warehouse", "Old warehouse", ["ruins", "ruins", "ruins", "crimson"]),
    ("rooftop", "Rooftop", ["rooftop", "rooftop", "dusk", "night"]),
]


def add(apps, schema_editor):
    WorldPlace = apps.get_model("weiss", "WorldPlace")
    order = max(WorldPlace.objects.values_list("order", flat=True), default=0)
    for key, name, backdrops in PLACES:
        order += 1
        WorldPlace.objects.get_or_create(key=key, defaults={"name": name, "backdrops": backdrops, "order": order, "secluded": True})
    WorldPlace.objects.filter(key__in=["shrine", "forest"]).update(secluded=True)


def remove(apps, schema_editor):
    apps.get_model("weiss", "WorldPlace").objects.filter(key__in=[key for key, _, _ in PLACES]).delete()


class Migration(migrations.Migration):
    dependencies = [("weiss", "0054_haunts_and_temperaments")]
    operations = [migrations.RunPython(add, remove)]
