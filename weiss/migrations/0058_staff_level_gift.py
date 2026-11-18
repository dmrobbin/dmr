from django.db import migrations, models


def add_staff_token(apps, schema_editor):
    GiftItem = apps.get_model("weiss", "GiftItem")
    GiftItem.objects.get_or_create(key="staff-token", defaults={
        "name": "Staff token", "icon": "🎫", "about": "Staff testing: raises someone here a friendship rank.",
        "price": 0, "tags": [], "order": 99, "staff_only": True,
    })


def remove_staff_token(apps, schema_editor):
    apps.get_model("weiss", "GiftItem").objects.filter(key="staff-token", staff_only=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('weiss', '0057_hello_goodbye_chatter'),
    ]

    operations = [
        migrations.AddField(
            model_name='giftitem',
            name='staff_only',
            field=models.BooleanField(default=False, help_text='Staff testing: only staff see it in the shop, and giving it raises the CPU a rank at once'),
        ),
        migrations.RunPython(add_staff_token, remove_staff_token),
    ]
