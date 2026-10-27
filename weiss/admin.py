from django.contrib import admin

from .models import Card, CardPrice


class CardPriceInline(admin.TabularInline):
    model = CardPrice
    extra = 0
    readonly_fields = ("fetched_at",)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    inlines = [CardPriceInline]
    list_display = ("serial_number", "name", "expansion", "card_type", "rarity", "color", "level", "power")
    list_filter = ("expansion", "card_type", "color", "side", "rarity")
    search_fields = ("serial_number", "name", "traits", "description")


@admin.register(CardPrice)
class CardPriceAdmin(admin.ModelAdmin):
    list_display = ("card", "market_price", "low_price", "source", "fetched_at")
    list_filter = ("source", "card__expansion")
    search_fields = ("card__serial_number", "card__name")
    raw_id_fields = ("card",)
