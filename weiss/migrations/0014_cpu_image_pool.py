from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def into_the_pool(apps, schema_editor):
    """Each image a CPU already has becomes the first in the shared pool, still chosen by that CPU."""
    CpuProfile = apps.get_model("weiss", "CpuProfile")
    CpuImage = apps.get_model("weiss", "CpuImage")
    for profile in CpuProfile.objects.exclude(image_key=""):
        profile.image = CpuImage.objects.create(key=profile.image_key, name=profile.name)
        profile.save(update_fields=["image"])


def out_of_the_pool(apps, schema_editor):
    CpuProfile = apps.get_model("weiss", "CpuProfile")
    for profile in CpuProfile.objects.exclude(image=None).select_related("image"):
        profile.image_key = profile.image.key
        profile.save(update_fields=["image_key"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("weiss", "0013_arcade"),
    ]

    operations = [
        migrations.CreateModel(
            name="CpuImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(help_text="Where it is in the S3 bucket", max_length=500, unique=True)),
                ("name", models.CharField(blank=True, help_text="Who or what it shows", max_length=200)),
                ("series", models.CharField(blank=True, help_text="The show it's from, when known", max_length=200)),
                ("source_url", models.URLField(blank=True, help_text="Where a found image came from", max_length=1000)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("source_card", models.ForeignKey(null=True, blank=True, help_text="The climax it was found for", on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="weiss.card")),
            ],
            options={"ordering": ["series", "name", "pk"]},
        ),
        migrations.AddField(
            model_name="cpuprofile",
            name="image",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profiles", to="weiss.cpuimage"),
        ),
        migrations.RunPython(into_the_pool, out_of_the_pool),
        migrations.RemoveField(model_name="cpuprofile", name="image_key"),
    ]
