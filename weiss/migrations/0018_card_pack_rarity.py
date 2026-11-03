from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0017_scores"),
    ]

    operations = [
        migrations.AddField(
            model_name="card",
            name="pack_rarity",
            field=models.CharField(blank=True, help_text="The rarity booster packs treat this card as; blank uses its printed rarity. 'PR' keeps it out of packs.", max_length=20),
        ),
    ]
