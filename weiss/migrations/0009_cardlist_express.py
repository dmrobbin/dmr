from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0008_cardlist_wins"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardlist",
            name="express",
            field=models.JSONField(blank=True, default=dict, help_text="How express building made this deck: series, anchors, required names"),
        ),
    ]
