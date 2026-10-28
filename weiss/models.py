import secrets

from django.db import models


class Card(models.Model):
    """One Weiss Schwarz card as listed on en.ws-tcg.com."""

    serial_number = models.CharField(max_length=50, unique=True, help_text="e.g. 'NIK/S135-E001S'")
    name = models.CharField(max_length=200)
    expansion = models.CharField(max_length=200, help_text="Expansion (set) name")
    expansion_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True, help_text="The site's expansion number, e.g. 290"
    )
    traits = models.CharField(max_length=300, blank=True, help_text="Separated by '・' as on the site")
    card_type = models.CharField(max_length=50, blank=True)
    rarity = models.CharField(max_length=20, blank=True)
    side = models.CharField(max_length=10, blank=True, help_text="Weiss or Schwarz")
    color = models.CharField(max_length=20, blank=True)
    level = models.IntegerField(null=True, blank=True)
    cost = models.IntegerField(null=True, blank=True)
    power = models.IntegerField(null=True, blank=True)
    trigger = models.CharField(max_length=100, blank=True, help_text="Trigger icons, e.g. 'soul' or 'soul soul'")
    soul = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True, help_text="Card text; icons appear as e.g. [comeback]")
    flavor_text = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True, help_text="Original image on en.ws-tcg.com")
    image_s3_key = models.CharField(max_length=500, blank=True, help_text="Copy of the image in the S3 bucket")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expansion_id", "serial_number"]

    def __str__(self):
        return f"{self.serial_number} {self.name}"

    @property
    def tcgplayer_price(self):
        """This card's TCGplayer price row, if any (uses prefetched `prices` when available)."""
        return next((p for p in self.prices.all() if p.source == CardPrice.Source.TCGPLAYER), None)


class CardPrice(models.Model):
    """A card's price from one source; refreshed in place by `manage.py fetch_prices`."""

    class Source(models.TextChoices):
        TCGPLAYER = "tcgplayer", "TCGplayer (via TCGCSV)"

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="prices")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.TCGPLAYER)
    market_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Based on recent sales; the price we show"
    )
    low_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Lowest current listing"
    )
    mid_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    high_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    printing = models.CharField(max_length=50, blank=True, help_text="TCGplayer sub-type, e.g. 'Normal'")
    tcgplayer_product_id = models.PositiveIntegerField(null=True, blank=True)
    product_url = models.URLField(max_length=500, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["card", "source"], name="one_price_per_card_per_source")]

    def __str__(self):
        return f"{self.card.serial_number}: {self.market_price or '—'} ({self.get_source_display()})"


class CardList(models.Model):
    """A user's named list of cards (a deck, a want list, ...), with any number of copies per card."""

    MAX_LISTS_PER_USER = 100
    MAX_CARDS = 100  # total copies across the whole list

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="card_lists")
    name = models.CharField(max_length=100)
    # A deck gets deck-building reminders (50 cards, 8 climaxes, 4 copies, level spread); nothing is enforced.
    is_deck = models.BooleanField(default=True)
    # The card pictured for this list on the lists page; blank means its first card (see lists.attach_covers).
    cover_card = models.ForeignKey("Card", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return self.name

    def card_count(self):
        return self.entries.aggregate(total=models.Sum("quantity"))["total"] or 0


class CardListEntry(models.Model):
    card_list = models.ForeignKey(CardList, on_delete=models.CASCADE, related_name="entries")
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="list_entries")
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["card_list", "card"], name="one_entry_per_card_per_list")]
        verbose_name_plural = "card list entries"

    def __str__(self):
        return f"{self.quantity}× {self.card}"


def new_room_token():
    return secrets.token_urlsafe(24)


class GameRoom(models.Model):
    """A two-player table. The host shares an invite link; whoever opens it first takes the other seat."""

    MAX_OPEN_ROOMS = 20  # per host

    class Status(models.TextChoices):
        SETUP = "setup", "Choosing decks"
        PLAYING = "playing", "Playing"

    host = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="rooms_hosted")
    guest = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="rooms_joined")
    invite_token = models.CharField(max_length=64, unique=True, default=new_room_token, editable=False)
    host_deck = models.ForeignKey(CardList, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    guest_deck = models.ForeignKey(CardList, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SETUP)
    state = models.JSONField(default=dict, blank=True, help_text="See weiss.game for the format")
    version = models.PositiveIntegerField(default=0, help_text="Goes up on every change, so browsers can poll cheaply")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return f"{self.host} vs {self.guest or '(open seat)'}"

    def seat_of(self, user):
        if user.pk == self.host_id:
            return "host"
        if user.pk == self.guest_id:
            return "guest"
        return None

    def opponent_of(self, user):
        return self.guest if user.pk == self.host_id else self.host
