from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0014_cpu_image_pool"),
    ]

    operations = [
        migrations.AddField(
            model_name="cpuimage",
            name="kind",
            field=models.CharField(blank=True, help_text="official or unofficial, for a found image", max_length=20),
        ),
        migrations.AlterField(
            model_name="cpuimage",
            name="source_card",
            field=models.ForeignKey(blank=True, help_text="The card it was found for", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="weiss.card"),
        ),
        migrations.AddField(
            model_name="cpuprofile",
            name="intro_image",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="intro_profiles", to="weiss.cpuimage"),
        ),
        migrations.AddField(
            model_name="cpuprofile",
            name="player_win_image",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="win_profiles", to="weiss.cpuimage"),
        ),
        migrations.AddField(
            model_name="cpuprofile",
            name="player_lose_image",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lose_profiles", to="weiss.cpuimage"),
        ),
    ]
