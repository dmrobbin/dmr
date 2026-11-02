from django.db import migrations, models


def fill_fought(apps, schema_editor):
    """Runs from before this was kept: the CPUs already beaten are the ones known to have been fought."""
    ArcadeRun = apps.get_model("weiss", "ArcadeRun")
    for run in ArcadeRun.objects.all():
        run.fought = list(run.order[:run.position])
        run.save(update_fields=["fought"])


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0015_cpu_image_screens"),
    ]

    operations = [
        migrations.AddField(
            model_name="arcaderun",
            name="fought",
            field=models.JSONField(default=list, help_text="CpuProfile ids this run has played a game against, won or lost"),
        ),
        migrations.RunPython(fill_fought, migrations.RunPython.noop),
    ]
