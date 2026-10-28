"""Card lists: create, pick one to edit, and add or remove copies while browsing cards.

The list being edited is remembered in the session. Every Weiss page shows a side panel with it
(see `panel_context`, wired in through the `card_lists` context processor). The +/- buttons post
here; the page's script sends them in the background and swaps in the re-rendered panel, so the
running count updates without reloading a page full of card images. Without JavaScript the same
forms work as ordinary posts that redirect back.
"""
from collections import Counter
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from .models import Card, CardList, CardListEntry
from .views import with_image_urls

SESSION_KEY = "weiss_editing_list"

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


def is_climax(card):
    return card.card_type.lower() == "climax"


def over_copy_limit(entries):
    """Names with more than COPY_LIMIT copies. The rule is per name, so different printings
    (rarities, promos) of the same card count together."""
    copies = Counter()
    for entry in entries:
        copies[entry.card.name] += entry.quantity
    return {name for name, count in copies.items() if count > COPY_LIMIT}


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
    return {"total": total, "size": DECK_SIZE, "over": total > DECK_SIZE, "exact": total == DECK_SIZE,
            "groups": groups, "copy_limit": COPY_LIMIT, "over_limit": over}


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


def panel_context(request):
    """Everything the side panel and the per-card +/- controls need."""
    lists = list(CardList.objects.filter(user=request.user).annotate(total=Sum("entries__quantity")))
    active = editing_list(request)
    entries = []
    if active:
        entries = list(active.entries.select_related("card").prefetch_related("card__prices")
                       .order_by("card__expansion_id", "card__serial_number"))
        with_image_urls([e.card for e in entries])  # thumbnails in the panel
    count = sum(e.quantity for e in entries)
    total, unpriced = price_entries(entries)
    deck = deck_checks(entries) if active and active.is_deck else None
    return {
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
    """Add (delta > 0) or remove (delta < 0) copies, keeping the list within MAX_CARDS. Returns the new quantity."""
    with transaction.atomic():
        card_list = CardList.objects.select_for_update().get(pk=card_list.pk)
        entry = CardListEntry.objects.filter(card_list=card_list, card=card).first()
        current = entry.quantity if entry else 0
        if delta > 0:
            room = CardList.MAX_CARDS - card_list.card_count()
            if room <= 0:
                raise ListError(f"“{card_list.name}” already has {CardList.MAX_CARDS} cards.")
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


@weiss_access_required
def list_index(request):
    lists = CardList.objects.filter(user=request.user).annotate(total=Sum("entries__quantity"))
    return render(request, "weiss/list_index.html", {"lists": lists})


@weiss_access_required
@require_POST
def list_create(request):
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        return respond(request, reverse("weiss:lists"), error="Give the list a name.")
    if CardList.objects.filter(user=request.user).count() >= CardList.MAX_LISTS_PER_USER:
        return respond(request, reverse("weiss:lists"),
                       error=f"You already have {CardList.MAX_LISTS_PER_USER} lists; delete one first.")
    card_list = CardList.objects.create(user=request.user, name=name)
    request.session[SESSION_KEY] = card_list.pk  # start adding to it straight away
    return respond(request, reverse("weiss:list", args=[card_list.pk]))


@weiss_access_required
@require_POST
def list_edit(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user)
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
    card_list = get_object_or_404(CardList, pk=pk, user=request.user)
    card = get_object_or_404(Card, pk=request.POST.get("card"))
    try:
        delta = int(request.POST.get("delta", "1"))
    except ValueError:
        delta = 1
    fallback = reverse("weiss:list", args=[card_list.pk])
    try:
        quantity = change_quantity(card_list, card, delta)
    except ListError as exc:
        current = CardListEntry.objects.filter(card_list=card_list, card=card).values_list("quantity", flat=True)
        return respond(request, fallback, error=str(exc), card=card.pk, quantity=next(iter(current), 0))
    return respond(request, fallback, card=card.pk, quantity=quantity)


@weiss_access_required
def list_detail(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user)
    entries = list(card_list.entries.select_related("card").prefetch_related("card__prices")
                   .order_by("card__expansion_id", "card__serial_number"))
    with_image_urls([e.card for e in entries])
    value, unpriced = price_entries(entries)
    return render(request, "weiss/list_detail.html", {
        "card_list": card_list,
        "entries": entries,
        "count": sum(e.quantity for e in entries),
        "value": value,
        "unpriced": unpriced,
        "deck": deck_checks(entries) if card_list.is_deck else None,
    })


@weiss_access_required
@require_POST
def list_deck(request, pk):
    """Mark a list as a deck (is_deck=on) or as a plain list."""
    card_list = get_object_or_404(CardList, pk=pk, user=request.user)
    card_list.is_deck = request.POST.get("is_deck") == "on"
    card_list.save(update_fields=["is_deck", "updated"])
    return respond(request, reverse("weiss:list", args=[card_list.pk]))


@weiss_access_required
@require_POST
def list_rename(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user)
    name = request.POST.get("name", "").strip()[:100]
    if name:
        card_list.name = name
        card_list.save(update_fields=["name", "updated"])
    return redirect("weiss:list", pk=card_list.pk)


@weiss_access_required
@require_POST
def list_delete(request, pk):
    card_list = get_object_or_404(CardList, pk=pk, user=request.user)
    if request.session.get(SESSION_KEY) == card_list.pk:
        request.session.pop(SESSION_KEY)
    messages.success(request, f"Deleted “{card_list.name}”.")
    card_list.delete()
    return redirect("weiss:lists")
