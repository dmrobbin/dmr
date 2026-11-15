from django import template

from weiss import abilities, packs, roles

register = template.Library()


@register.simple_tag(takes_context=True)
def card_roles(context, card):
    """A card's roles for the Role filters, space-separated (e.g. "combo support"): data-roles="{% card_roles card %}"."""
    return " ".join(roles.roles_of(card.description, roles.climax_names_for(context.get("request"))))


@register.simple_tag
def role_options():
    """The Role filters' (value, label, hint) triples, so every page's chips match roles.py."""
    return roles.ROLES


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
