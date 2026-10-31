from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weiss", "0009_cardlist_express"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardlist",
            name="reserved_for_cpu",
            field=models.BooleanField(default=False, help_text="Made in the CPU creation tab; kept out of players' lists and deck choices"),
        ),
        migrations.CreateModel(
            name="CpuProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("model", models.CharField(default="standard", help_text="Which behaviour it plays by; see weiss.cpu", max_length=20)),
                ("aggression", models.PositiveSmallIntegerField(default=1, help_text="1 is the standard behaviour")),
                ("finalized", models.BooleanField(default=False, help_text="Offered to players under VS CPU")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("deck", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cpu_profiles", to="weiss.cardlist")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="gameroom",
            name="cpu_name",
            field=models.CharField(blank=True, help_text="The CPU in the guest seat, if it's a game against one", max_length=100),
        ),
        migrations.AddField(
            model_name="gameroom",
            name="cpu_profile",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="weiss.cpuprofile"),
        ),
    ]
