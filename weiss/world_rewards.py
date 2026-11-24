"""The card pick a world-mode duel win offers: one card from the beaten CPU's deck, picked at the town (see
docs/world-mode.md)."""
from django.urls import reverse

from . import buffs, packs
from .lists import is_climax
from .models import Card


def offer_card_pick(save, room):
    """A win's offer: the CPU's deck's distinct cards (its climaxes left out, unless that's all it has), kept on the
    save until picked. A new win replaces an unclaimed offer. Returns whether an offer was made: a CPU with no cards
    makes none."""
    from . import world  # weiss.world imports this module

    cpu = room.cpu_profile
    cards = sorted((card for card, _ in world.deck_cards(cpu)), key=lambda card: card.serial_number)
    choices = [card for card in cards if not is_climax(card)] or cards
    if not choices:
        return False
    save.flags["card_pick"] = {"room": room.pk, "cpu": cpu.pk, "cpu_name": room.cpu_name, "cards": [card.pk for card in choices]}
    return True


def card_pick_view(save):
    """What the town shows for the save's offer, or None."""
    offer = save.flags.get("card_pick")
    if not offer:
        return None
    cards = Card.objects.in_bulk(offer["cards"])
    return {"cpu": offer["cpu_name"], "cards": [{"id": card.pk, "name": card.name, "image": reverse("weiss:card_image", args=[card.pk]),
                                                  "url": reverse("weiss:card", args=[card.pk]), "rarity": packs.rarity_of(card),
                                                  "color": card.color, "level": card.level, "type": card.card_type}
                                                 for pk in offer["cards"] if (card := cards.get(pk))]}


def pick_card(save, card_id):
    """Takes the offer's card: a copy goes in the save's cards, and the offer's gone. Raises ValueError."""
    from . import world  # weiss.world imports this module

    world.tutorial.allows(save, "pick")  # not in its table: refused with the guide's waiting message, while it's on
    offer = save.flags.get("card_pick")
    if not offer:
        raise ValueError("There's no card to choose.")
    try:
        card_id = int(card_id)
    except (TypeError, ValueError):
        card_id = None
    if card_id not in offer["cards"]:
        raise ValueError("That card isn't one of the choices.")
    card = Card.objects.get(pk=card_id)
    buffs.add_to_pool(save, card.pk, 1)
    del save.flags["card_pick"]
    world.changed(save, "pool", "flags")
    return card
