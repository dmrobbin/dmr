from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0010_cpu"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cardlist",
            name="wins",
            field=models.PositiveIntegerField(default=0, help_text="Games this list has won against human players; shown as stars"),
        ),
        migrations.AddField(
            model_name="cardlist",
            name="cpu_wins",
            field=models.PositiveIntegerField(default=0, help_text="Games this list has won against CPUs; shown as robots"),
        ),
    ]
