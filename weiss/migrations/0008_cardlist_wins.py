from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0007_cardlist_cover_card"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardlist",
            name="wins",
            field=models.PositiveIntegerField(default=0, help_text="Games this list has won as a deck; shown as stars"),
        ),
    ]
