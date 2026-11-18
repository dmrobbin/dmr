"""World mode's first gift items, sold at the card shop, and gift tastes for every CPU that has none, so gifts mean
something from the start; staff change both in the admin. The tastes follow weiss.world.starter_tastes, copied here as
a migration should stand on its own."""
import random

from django.db import migrations

GIFTS = [  # (key, name, icon, price, tags, about)
    ("melon-bread", "Melon bread", "🍞", 80, ["sweet", "food"], "Still warm from the bakery."),
    ("bottled-tea", "Bottled tea", "🍵", 90, ["drink", "calm"], "Green tea, not too sweet."),
    ("energy-drink", "Energy drink", "⚡", 110, ["drink", "sporty"], "For late-night deck building."),
    ("iced-coffee", "Iced coffee", "☕", 120, ["drink", "cool"], "From the café on the corner."),
    ("instant-ramen", "Instant ramen", "🍜", 100, ["food", "spicy"], "Extra spicy, says the lid."),
    ("manga", "Manga volume", "📕", 180, ["book", "cute"], "The latest volume of something popular."),
    ("bouquet", "Bouquet", "💐", 200, ["flowers", "fancy", "cute"], "A small bunch of seasonal flowers."),
    ("shortcake", "Strawberry shortcake", "🍰", 220, ["sweet", "fancy"], "A slice from the good bakery."),
    ("sleeves", "Card sleeves", "🃏", 250, ["cards"], "A box of 60, in a pretty colour."),
    ("plushie", "Plushie", "🧸", 260, ["cute", "calm"], "Soft, round and very huggable."),
    ("sunglasses", "Sunglasses", "🕶️", 300, ["cool", "sporty"], "Look the part."),
    ("earbuds", "Earbuds", "🎧", 500, ["music", "cool"], "Wireless, in a little case."),
    ("playmat", "Playmat", "🎴", 600, ["cards", "fancy"], "A full-art playmat, rolled in a tube."),
    ("handheld", "Handheld game", "🎮", 700, ["game", "cool"], "Something to play between duels."),
]
TASTE_TAGS = ("sweet", "drink", "food", "spicy", "fancy", "cute", "cool", "flowers", "cards", "book", "music", "sporty", "game", "calm")


def starter_tastes(cpu_id):
    rng = random.Random(cpu_id * 104729)
    tags = rng.sample(TASTE_TAGS, 6)
    likes = rng.randint(2, 3)
    return {"loves": tags[:1], "likes": tags[1:1 + likes], "dislikes": tags[1 + likes:1 + likes + rng.randint(1, 2)]}


def add(apps, schema_editor):
    GiftItem = apps.get_model("weiss", "GiftItem")
    CpuProfile = apps.get_model("weiss", "CpuProfile")
    for order, (key, name, icon, price, tags, about) in enumerate(GIFTS):
        GiftItem.objects.get_or_create(key=key, defaults={"name": name, "icon": icon, "price": price, "tags": tags, "about": about, "order": order})
    for cpu in CpuProfile.objects.all():
        if not cpu.gift_tastes:
            cpu.gift_tastes = starter_tastes(cpu.pk)
            cpu.save(update_fields=["gift_tastes"])


class Migration(migrations.Migration):
    dependencies = [("weiss", "0052_world_talk_and_gifts")]
    # Going back leaves them: staff may have changed them since.
    operations = [migrations.RunPython(add, migrations.RunPython.noop)]
