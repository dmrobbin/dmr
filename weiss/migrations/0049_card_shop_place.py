"""World mode's card shop: a place of its own, with the shop's counter."""
from django.db import migrations


def add(apps, schema_editor):
    WorldPlace = apps.get_model("weiss", "WorldPlace")
    WorldPlace.objects.get_or_create(key="shop", defaults={"name": "Card shop", "backdrops": ["shop"] * 4, "order": 1, "shop": True})


def remove(apps, schema_editor):
    apps.get_model("weiss", "WorldPlace").objects.filter(key="shop").delete()


class Migration(migrations.Migration):
    dependencies = [("weiss", "0048_world_schedules_and_duels")]
    operations = [migrations.RunPython(add, remove)]
