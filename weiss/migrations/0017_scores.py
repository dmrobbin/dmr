from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0016_arcade_run_fought"),
    ]

    operations = [
        migrations.AddField(
            model_name="gamerecord",
            name="score",
            field=models.PositiveIntegerField(blank=True, null=True, help_text="A win against a CPU's score; none for other games"),
        ),
        migrations.AddField(
            model_name="arcaderun",
            name="score",
            field=models.PositiveIntegerField(db_index=True, default=0, help_text="The run's total: its wins' scores added up"),
        ),
        migrations.AddField(
            model_name="arcaderun",
            name="scores",
            field=models.JSONField(default=list, help_text="Each win's score, in order: [{cpu, name, score}]"),
        ),
    ]
