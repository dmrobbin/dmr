"""Card lists: create, pick one to edit, and add or remove copies while browsing cards.

The list being edited is remembered in the session. Every Weiss page shows a side panel with it
(see `panel_context`, wired in through the `card_lists` context processor). The +/- buttons post
here; the page's script sends them in the background and swaps in the re-rendered panel, so the
running count updates without reloading a page full of card images. Without JavaScript the same
forms work as ordinary posts that redirect back.
"""
import re
from collections import Counter
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import abilities
from .models import Card, CardList, CardListEntry
from .views import with_image_urls

SESSION_KEY = "weiss_editing_list"
EXPRESS_PROMPT = "weiss_express_prompt"  # a list just created, to offer express building for

DECK_SIZE = 50
COPY_LIMIT = 4  # copies of any one card name in a deck
# Reminders shown while building a deck: (label, target copies, required by the rules?, which cards count).
# The climax count is a rule; the level spread is only the usual recommendation.
DECK_GROUPS = [
    ("Climax", 8, True, lambda card: is_climax(card)),
    ("Level 0", 18, False, lambda card: not is_climax(card) and card.level == 0),
    ("Level 1", 12, False, lambda card: not is_climax(card) and card.level == 1),
    ("Level 2 + 3", 12, False, lambda card: not is_climax(card) and card.level in (2, 3)),
]


CLIMAX_COUNT = next(target for _, target, required, _ in DECK_GROUPS if required)  # a legal deck has exactly this many climaxes


def is_climax(card):
    return card.card_type.lower() == "climax"


def climaxes_in(card_list):
    return sum(e.quantity for e in card_list.entries.select_related("card") if is_climax(e.card))


def climax_problem(count, most=CLIMAX_COUNT):
    """What's wrong with a deck having this many climaxes, or None: it needs CLIMAX_COUNT, or with an infinite
    challenge's Climax Overload, anything from that to `most` (see weiss.augments)."""
    if CLIMAX_COUNT <= count <= most:
        return None
    needs = f"exactly {CLIMAX_COUNT}" if most == CLIMAX_COUNT else f"{CLIMAX_COUNT} to {most}"
    return f"A deck needs {needs} climaxes, and this one has {count}."


def unplayable(deck):
    """Why this deck can't be played with as it is, or None: it's empty, or hasn't the climaxes a deck must have."""
    if not deck.entries.exists():
        return f"“{deck.name}” is empty; add some cards first."
    if problem := climax_problem(climaxes_in(deck)):
        return f"“{deck.name}”: {problem[0].lower()}{problem[1:]}"
    return None


# "【CONT】 You can put any number of cards with the same card name as this card into your deck."
ANY_NUMBER = re.compile(r"any number of (?:cards with the same (?:card )?name as this card|copies of this card)", re.I)


def unlimited(card):
    """Whether this card's own text lets a deck have any number of it, past COPY_LIMIT."""
    return bool(ANY_NUMBER.search(card.description or ""))


def copy_limit(card):
    """How many copies of this card's name a deck can have: COPY_LIMIT, or None for no limit."""
    return None if unlimited(card) else COPY_LIMIT


def over_copy_limit(entries):
    """Names with more than COPY_LIMIT copies. The rule is per name, so different printings
    (rarities, promos) of the same card count together. A name whose card says any number can go in
    a deck has no limit."""
    copies = Counter()
    free = set()
    for entry in entries:
        copies[entry.card.name] += entry.quantity
        if unlimited(entry.card):
            free.add(entry.card.name)
    return {name for name, count in copies.items() if count > COPY_LIMIT and name not in free}


def deck_checks(entries):
    """Card counts against the deck rules and the usual level spread. Only going over 50 total is
    flagged, since a deck in progress is naturally under."""
    total = sum(e.quantity for e in entries)
    groups = []
    for label, target, required, counts in DECK_GROUPS:
        count = sum(e.quantity for e in entries if counts(e.card))
        groups.append({"label": label, "count": count, "target": target, "required": required,
                       "ok": count == target})
    over = sorted(over_copy_limit(entries))
    colors = Counter()
    for entry in entries:
        colors[entry.card.color or "No color"] += entry.quantity
    return {"total": total, "size": DECK_SIZE, "over": total > DECK_SIZE, "exact": total == DECK_SIZE,
            "groups": groups, "copy_limit": COPY_LIMIT, "over_limit": over,
            "colors": colors.most_common()}  # [(color, copies), ...], most first


class ListError(Exception):
    pass


def editing_list(request):
    """The list this user is currently adding cards to, if any."""
    pk = request.session.get(SESSION_KEY)
    if not pk:
        return None
    card_list = CardList.objects.filter(pk=pk, user=request.user).first()
    if not card_list:
        request.session.pop(SESSION_KEY, None)
    return card_list


def sorted_entries(card_list):
    """A list's entries the way a deck list reads: climaxes (no level) first, then by level."""
    return list(card_list.entries.select_related("card").prefetch_related("card__prices")
                .order_by(F("card__level").asc(nulls_first=True), "card__serial_number"))


def panel_context(request):
    """Everything the side panel and the per-card +/- controls need."""
    # Grouped for the totals, so the model's ordering doesn't apply: newest-modified first, said here.
    lists = list(CardList.objects.players(request.user).annotate(total=Sum("entries__quantity")).order_by("-updated", "-pk"))
    active = editing_list(request)
    entries = []
    if active:
        entries = sorted_entries(active)
        with_image_urls([e.card for e in entries])  # thumbnails in the panel
    count = sum(e.quantity for e in entries)
    total, unpriced = price_entries(entries)
    deck = deck_checks(entries) if active and active.is_deck else None
    prompt_pk = request.session.get(EXPRESS_PROMPT)
    return {
        "express_prompt": CardList.objects.filter(pk=prompt_pk, user=request.user).first() if prompt_pk else None,
        "card_lists": lists,
        "editing_list": active,
        "editing_entries": entries,
        "editing_deck": deck,
        # Card names past the copy limit; their +/- controls turn red (see qty_controls.html).
        "editing_over_limit": set(deck["over_limit"]) if deck else set(),
        "editing_count": count,
        "editing_full": count >= CardList.MAX_CARDS,
        "editing_total": total,
        "editing_unpriced": unpriced,
        "editing_quantities": {e.card_id: e.quantity for e in entries},
        "max_cards": CardList.MAX_CARDS,
        "max_lists": CardList.MAX_LISTS_PER_USER,
        "lists_full": len(lists) >= CardList.MAX_LISTS_PER_USER,
    }


def price_entries(entries):
    """Set `line_total` on each entry (copies x TCGplayer market price, or None) and return
    (total of the priced cards, number of copies without a price)."""
    total, unpriced = Decimal("0"), 0
    for entry in entries:
        price = entry.card.tcgplayer_price
        if price and price.market_price is not None:
            entry.line_total = price.market_price * entry.quantity
            total += entry.line_total
        else:
            entry.line_total = None
            unpriced += entry.quantity
    return total, unpriced


def wants_json(request):
    return request.headers.get("Accept", "").startswith("application/json")


def back(request, fallback):
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(fallback)


def respond(request, fallback, error="", **extra):
    """JSON with a fresh panel for the page script, or a redirect back for plain form posts."""
    if wants_json(request):
        context = panel_context(request)
        # Forms in the re-rendered panel should still point back at the page, not at this endpoint.
        context |= {"panel_error": error, "panel_next": request.POST.get("next", "")}
        panel = render_to_string("weiss/list_panel.html", context, request)
        # The list's own page shows the same deck reminders; send them so it can refresh them too.
        deck = ""
        if context["editing_deck"]:
            deck = render_to_string("weiss/deck_checks.html", {"deck": context["editing_deck"]}, request)
        return JsonResponse({
            "ok": not error, "error": error, "panel": panel,
            "list": context["editing_list"].pk if context["editing_list"] else None, "deck": deck,
            "over_limit": sorted(context["editing_over_limit"]),
            "count": context["editing_count"], "full": context["editing_full"], **extra,
        }, status=400 if error else 200)
    if error:
        messages.error(request, error)
    return back(request, fallback)


def change_quantity(card_list, card, delta):
    """Add (delta > 0) or remove (delta < 0) copies, keeping the list within MAX_CARDS, and a deck within
    CLIMAX_COUNT climaxes. Returns the new quantity."""
    with transaction.atomic():
        card_list = CardList.objects.select_for_update().get(pk=card_list.pk)
        entry = CardListEntry.objects.filter(card_list=card_list, card=card).first()
        current = entry.quantity if entry else 0
        if delta > 0:
            room = CardList.MAX_CARDS - card_list.card_count()
            if room <= 0:
                raise ListError(f"“{card_list.name}” already has {CardList.MAX_CARDS} cards.")
            if card_list.is_deck and is_climax(card):
                room = min(room, CLIMAX_COUNT - climaxes_in(card_list))
                if room <= 0:
                    raise ListError(f"A deck has at most {CLIMAX_COUNT} climaxes, and “{card_list.name}” has them all.")
            delta = min(delta, room)
        quantity = max(current + delta, 0)
        if quantity == 0:
            if entry:
                entry.delete()
        elif entry:
            entry.quantity = quantity
            entry.save(update_fields=["quantity"])
        else:
            CardListEntry.objects.create(card_list=card_list, card=card, quantity=quantity)
        card_list.save(update_fields=["updated"])
    return quantity


def attach_covers(lists):
    """Set `cover` on each list: its chosen cover card if that's still in the list, else its first
    card in deck order, skipping climaxes (their art is printed sideways) unless that's all it has."""
    lists = list(lists)
    entries = (CardListEntry.objects.filter(card_list__in=lists).select_related("card")
               .order_by(F("card__level").asc(nulls_first=True), "card__serial_number"))
    cards_in = {}
    first, first_any = {}, {}
    for entry in entries:
        cards_in.setdefault(entry.card_list_id, {})[entry.card_id] = entry.card
        first_any.setdefault(entry.card_list_id, entry.card)
        if not is_climax(entry.card):
            first.setdefault(entry.card_list_id, entry.card)
    for card_list in lists:
        in_list = cards_in.get(card_list.pk, {})
        card_list.cover = (in_list.get(card_list.cover_card_id)
                           or first.get(card_list.pk) or first_any.get(card_list.pk))
    with_image_urls([card_list.cover for card_list in lists if card_list.cover])
    return lists


@weiss_access_required
def list_index(request):
    lists = CardList.objects.players(request.user).annotate(total=Sum("entries__quantity")).order_by("-updated", "-pk").prefetch_related("arcade_clears")
    return render(request, "weiss/list_index.html", {"lists": attach_covers(lists)})


@weiss_access_required
@require_POST
def list_cover(request, pk):
    """Pick the card pictured for this list (one of its own cards); an empty `card` goes back to the default."""
    card_list = get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)
    card_pk = request.POST.get("card", "")
    if card_pk:
        entry = get_object_or_404(CardListEntry, card_list=card_list, card_id=card_pk)
        card_list.cover_card_id = entry.card_id
    else:
        card_list.cover_card = None
    card_list.save(update_fields=["cover_card", "updated"])
    return redirect("weiss:list", pk=card_list.pk)


@weiss_access_required
@require_POST
def list_create(request):
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        return respond(request, reverse("weiss:lists"), error="Give the list a name.")
    if CardList.objects.players(request.user).count() >= CardList.MAX_LISTS_PER_USER:
        return respond(request, reverse("weiss:lists"),
                       error=f"You already have {CardList.MAX_LISTS_PER_USER} lists; delete one first.")
    card_list = CardList.objects.create(user=request.user, name=name)
    request.session[SESSION_KEY] = card_list.pk  # start adding to it straight away
    request.session[EXPRESS_PROMPT] = card_list.pk  # and offer to build it automatically instead
    return respond(request, reverse("weiss:list", args=[card_list.pk]))


@weiss_access_required
@require_POST
def list_express_skip(request):
    """No thanks to the express building prompt: this list gets built by hand."""
    request.session.pop(EXPRESS_PROMPT, None)
    return respond(request, reverse("weiss:lists"))


@weiss_access_required
@require_POST
def list_edit(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)
    request.session[SESSION_KEY] = card_list.pk
    return respond(request, reverse("weiss:sets"))


@weiss_access_required
@require_POST
def list_stop_editing(request):
    request.session.pop(SESSION_KEY, None)
    return respond(request, reverse("weiss:sets"))


@weiss_access_required
@require_POST
def list_change(request, pk):
    """Change how many copies of a card a list has: delta=1 adds one, delta=-1 removes one."""
    card_list = get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)
    card = get_object_or_404(Card, pk=request.POST.get("card"))
    try:
        delta = int(request.POST.get("delta", "1"))
    except ValueError:
        delta = 1
    fallback = reverse("weiss:list", args=[card_list.pk])
    if card_list.reserved_for_cpu and delta > 0 and abilities.by_hand_parts(card.description):
        current = CardListEntry.objects.filter(card_list=card_list, card=card).values_list("quantity", flat=True)
        return respond(request, fallback, error=f"A CPU can't play {card.name}: part of it has to be done by hand.",
                       card=card.pk, quantity=next(iter(current), 0))
    try:
        quantity = change_quantity(card_list, card, delta)
    except ListError as exc:
        current = CardListEntry.objects.filter(card_list=card_list, card=card).values_list("quantity", flat=True)
        return respond(request, fallback, error=str(exc), card=card.pk, quantity=next(iter(current), 0))
    return respond(request, fallback, card=card.pk, quantity=quantity)


@weiss_access_required
def list_detail(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)
    entries = sorted_entries(card_list)
    with_image_urls([e.card for e in entries])
    value, unpriced = price_entries(entries)
    return render(request, "weiss/list_detail.html", {
        "card_list": card_list,
        "entries": entries,
        "count": sum(e.quantity for e in entries),
        "value": value,
        "unpriced": unpriced,
        "deck": deck_checks(entries) if card_list.is_deck else None,
        "cover": attach_covers([card_list])[0].cover,
    })


@weiss_access_required
@require_POST
def list_deck(request, pk):
    """Mark a list as a deck (is_deck=on) or as a plain list."""
    card_list = get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)
    card_list.is_deck = request.POST.get("is_deck") == "on"
    card_list.save(update_fields=["is_deck", "updated"])
    return respond(request, reverse("weiss:list", args=[card_list.pk]))


@weiss_access_required
@require_POST
def list_rename(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)
    name = request.POST.get("name", "").strip()[:100]
    if name:
        card_list.name = name
        card_list.save(update_fields=["name", "updated"])
    return redirect("weiss:list", pk=card_list.pk)


@weiss_access_required
@require_POST
def list_delete(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user, challenge=False)
    if request.session.get(SESSION_KEY) == card_list.pk:
        request.session.pop(SESSION_KEY)
    messages.success(request, f"Deleted “{card_list.name}”.")
    reserved = card_list.reserved_for_cpu
    card_list.delete()
    return redirect("weiss:cpu_home" if reserved else "weiss:lists")
