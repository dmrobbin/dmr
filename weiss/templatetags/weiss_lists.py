from django import template

from weiss import abilities

register = template.Library()


@register.filter
def cpu_by_hand(card):
    """What in this card's text a CPU can't carry out: the same check that keeps it out of CPU decks."""
    return abilities.by_hand_parts(card.description)


@register.filter
def copies(quantities, card_id):
    """How many copies of a card the list being edited has: {{ editing_quantities|copies:card.pk }}."""
    return (quantities or {}).get(card_id, 0)
