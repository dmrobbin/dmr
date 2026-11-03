from django import template

from weiss import abilities, packs

register = template.Library()


@register.filter
def rarity_grade(card):
    """How grand a card's rarity effect is, 0 (none) for commons up to 5 for SSP and SEC (see packs.GRADES)."""
    return packs.grade_of(packs.rarity_of(card))


@register.filter
def cpu_by_hand(card):
    """What in this card's text a CPU can't carry out: the same check that keeps it out of CPU decks."""
    return abilities.by_hand_parts(card.description)


@register.filter
def copies(quantities, card_id):
    """How many copies of a card the list being edited has: {{ editing_quantities|copies:card.pk }}."""
    return (quantities or {}).get(card_id, 0)
