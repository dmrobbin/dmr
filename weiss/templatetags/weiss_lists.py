from django import template

register = template.Library()


@register.filter
def copies(quantities, card_id):
    """How many copies of a card the list being edited has: {{ editing_quantities|copies:card.pk }}."""
    return (quantities or {}).get(card_id, 0)
