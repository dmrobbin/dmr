"""A starting schedule in world mode's town for every CPU that can duel and has none, so the town has people from the
start; staff edit them under World mode -> CPU schedules. The same rules as weiss.world.starter_rules, copied here as a
migration should stand on its own: a home most weekdays, a weekend spot and somewhere to wander, each in whichever place
has the fewest rules so far."""
import random

from django.db import migrations


def starter_rules(cpu_id, places, usage):
    rng = random.Random(cpu_id * 7919)

    def pick(but=()):
        choices = [key for key in places if key not in but] or list(places)
        least = min(usage.get(key, 0) for key in choices)
        key = rng.choice([key for key in choices if usage.get(key, 0) == least])
        usage[key] = usage.get(key, 0) + 1
        return key

    home = pick()
    weekend = pick((home,))
    wander = pick((home, weekend))
    return [
        {"place": home, "days": [0, 1, 2, 3, 4], "times": sorted(rng.sample(range(4), 2)), "chance": 90, "priority": 1},
        {"place": weekend, "days": [5, 6], "times": sorted(rng.sample(range(4), rng.randint(1, 2))), "chance": 80, "priority": 1},
        {"place": wander, "days": sorted(rng.sample(range(7), 3)), "times": [rng.randrange(4)], "chance": 60, "priority": 0},
    ]


def add(apps, schema_editor):
    CpuProfile = apps.get_model("weiss", "CpuProfile")
    CpuSchedule = apps.get_model("weiss", "CpuSchedule")
    WorldPlace = apps.get_model("weiss", "WorldPlace")
    places = {place.key: place for place in WorldPlace.objects.filter(shop=False)}
    if not places:
        return
    usage = {}
    for rule in CpuSchedule.objects.select_related("place"):
        usage[rule.place.key] = usage.get(rule.place.key, 0) + 1
    for cpu in CpuProfile.objects.filter(finalized=True, deck__isnull=False, schedule__isnull=True).order_by("pk"):
        for rule in starter_rules(cpu.pk, sorted(places), usage):
            CpuSchedule.objects.create(cpu=cpu, **{**rule, "place": places[rule["place"]]})


class Migration(migrations.Migration):
    dependencies = [("weiss", "0049_card_shop_place")]
    # Going back leaves the rules: staff may have changed them since.
    operations = [migrations.RunPython(add, migrations.RunPython.noop)]
