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
