"""Curses that hurt the player become curses that make the CPU stronger (see weiss.curses): each run's taken curses,
the curse picks waiting to be claimed, and a co-op pair's vs. battle offers move to their replacements."""
from django.db import migrations

RENAMED = {"old_wounds": "recovery", "short_hand": "deep_pockets", "heavy_refresh": "second_wind", "toll": "bulwark"}


def renamed(ids):
    return [RENAMED.get(curse_id, curse_id) for curse_id in ids]


def forwards(apps, schema_editor):
    ChallengeRun = apps.get_model("weiss", "ChallengeRun")
    CoopRun = apps.get_model("weiss", "CoopRun")
    for run in ChallengeRun.objects.all():
        curses = renamed(run.curses or [])
        rewards = [{**reward, "options": renamed(reward.get("options", []))} if reward.get("buff") == "curse" else reward for reward in run.rewards or []]
        if curses != (run.curses or []) or rewards != (run.rewards or []):
            run.curses, run.rewards = curses, rewards
            run.save(update_fields=["curses", "rewards"])
    for pair in CoopRun.objects.all():
        path = pair.path or {}
        changed = False
        for key in ("duel", "last_duel"):
            duel = path.get(key)
            if duel:
                options, picks = renamed(duel.get("options", [])), {voter: RENAMED.get(c, c) for voter, c in duel.get("picks", {}).items()}
                changed = changed or options != duel.get("options", []) or picks != duel.get("picks", {})
                duel["options"], duel["picks"] = options, picks
        if changed:
            pair.save(update_fields=["path"])


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0036_coop_duels"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
