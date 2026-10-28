from collections import Counter, defaultdict

from django.conf import settings
from django.db.models import F, Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from core import s3
from core.access import weiss_access_required

from .models import Card, CardList


def with_image_urls(cards):
    """Attach `image_src` to each card: our S3 copy when there is one, else the official site's image."""
    cards = list(cards)
    keys = [card.image_s3_key for card in cards if card.image_s3_key]
    signed = s3.presigned_image_urls(keys) if keys and settings.AWS_S3_BUCKET else {}
    for card in cards:
        card.image_src = signed.get(card.image_s3_key) or card.image_url
    return cards


SET_SORTS = {
    "number": lambda s: s["expansion_id"],
    "name": lambda s: s["name"].lower(),
    "cards": lambda s: s["cards"],
}


def series_code(serial_number):
    """'OSK/S107-TE01' -> 'OSK'."""
    return serial_number.split("/", 1)[0]


def summarize_sets():
    """One dict per saved expansion: number, name, series code, card count and cover card serial.

    The cover is the lowest serial among the set's main print run (the most common 'OSK/S121'-style
    prefix), so a promo from another set packed into this one doesn't become its cover.
    """
    serials = defaultdict(list)
    names = {}
    for expansion_id, name, serial in Card.objects.exclude(expansion_id=None).values_list(
        "expansion_id", "expansion", "serial_number"
    ):
        serials[expansion_id].append(serial)
        names[expansion_id] = name
    sets = []
    for expansion_id, set_serials in serials.items():
        main_prefix = Counter(s.split("-", 1)[0] for s in set_serials).most_common(1)[0][0]
        sets.append({
            "expansion_id": expansion_id,
            "name": names[expansion_id],
            "code": Counter(series_code(s) for s in set_serials).most_common(1)[0][0],
            "cards": len(set_serials),
            "cover_serial": min(s for s in set_serials if s.split("-", 1)[0] == main_prefix),
        })
    return sets


@weiss_access_required
def set_list(request):
    sets = summarize_sets()
    codes = sorted({s["code"] for s in sets})

    name = request.GET.get("name", "").strip()
    number = request.GET.get("number", "").strip()
    code = request.GET.get("code", "")
    if name:
        sets = [s for s in sets if name.lower() in s["name"].lower()]
    if number:
        sets = [s for s in sets if str(s["expansion_id"]).startswith(number)]
    if code:
        sets = [s for s in sets if s["code"] == code]

    sort = request.GET.get("sort", "-number")
    if sort.removeprefix("-") not in SET_SORTS:
        sort = "-number"
    sets.sort(key=SET_SORTS[sort.removeprefix("-")], reverse=sort.startswith("-"))

    covers = {card.serial_number: card for card in with_image_urls(
        Card.objects.filter(serial_number__in=[s["cover_serial"] for s in sets])
    )}
    for s in sets:
        s["cover"] = covers.get(s["cover_serial"])

    return render(request, "weiss/set_list.html", {
        "sets": sets,
        "codes": codes,
        "sort_options": [
            ("-number", "Expansion number, newest first"),
            ("number", "Expansion number, oldest first"),
            ("name", "Name, A–Z"),
            ("-name", "Name, Z–A"),
            ("-cards", "Most cards"),
        ],
        "filters": {"name": name, "number": number, "code": code, "sort": sort},
        "filtered": bool(name or number or code),
    })


# Card sort options on a set page: (value, label, ordering field). Blank values go last, except
# that climaxes (no level) come before level 0 when sorting by level, low to high.
CARD_SORTS = [
    ("serial", "Card number", "serial_number"),
    ("level", "Level, low to high", "level"),
    ("-level", "Level, high to low", "-level"),
    ("cost", "Cost, low to high", "cost"),
    ("-cost", "Cost, high to low", "-cost"),
    ("power", "Power, low to high", "power"),
    ("-power", "Power, high to low", "-power"),
    ("-price", "Price, high to low", "-price"),
    ("price", "Price, low to high", "price"),
    ("name", "Name, A–Z", "name"),
]


def filter_number(cards, field, value):
    """Filter on level or cost: a number, or 'none' for cards without one (e.g. climaxes)."""
    if value == "none":
        return cards.filter(**{field: None})
    if value.isdigit():
        return cards.filter(**{field: int(value)})
    return cards


def values_in(cards, field):
    """The distinct values of a numeric field in a set, with None (no value) last."""
    return sorted(set(cards.values_list(field, flat=True)), key=lambda v: (v is None, v))


def card_browser(request, pool, template_context):
    """The searchable, sortable card grid shared by the set and series pages. `pool` is every card
    the page covers; the filter dropdowns offer only values found in it."""
    cards = pool
    name = request.GET.get("name", "").strip()
    text = request.GET.get("text", "").strip()
    colors = [c for c in request.GET.getlist("color") if c]  # any of these (?color=Red&color=Blue)
    level = request.GET.get("level", "")
    cost = request.GET.get("cost", "")
    expansion = request.GET.get("set", "")
    if name:
        cards = cards.filter(name__icontains=name)
    if text:
        cards = cards.filter(description__icontains=text)
    if colors:
        cards = cards.filter(color__in=colors)
    cards = filter_number(cards, "level", level)
    cards = filter_number(cards, "cost", cost)
    if expansion.isdigit():
        cards = cards.filter(expansion_id=int(expansion))

    sort = request.GET.get("sort", "serial")
    orderings = {value: field for value, _, field in CARD_SORTS}
    if sort not in orderings:
        sort = "serial"
    field = orderings[sort]
    cards = cards.annotate(price=Max("prices__market_price"))
    expression = F(field.removeprefix("-"))
    if field.startswith("-"):
        expression = expression.desc(nulls_last=True)
    else:
        # Climaxes have no level and sort as if below level 0; other blanks go last.
        expression = expression.asc(nulls_first=True) if field == "level" else expression.asc(nulls_last=True)
    cards = cards.order_by(expression, "serial_number").prefetch_related("prices")

    return render(request, "weiss/set_detail.html", {
        **template_context,
        "total": pool.count(),
        "cards": with_image_urls(cards),
        "colors": sorted(set(pool.exclude(color="").values_list("color", flat=True))),
        "levels": values_in(pool, "level"),
        "costs": values_in(pool, "cost"),
        "sort_options": [(value, label) for value, label, _ in CARD_SORTS],
        "filters": {"name": name, "text": text, "colors": colors, "level": level, "cost": cost, "set": expansion,
                    "sort": sort},
        "filtered": bool(name or text or colors or level or cost or expansion),
    })


@weiss_access_required
def set_detail(request, expansion_id):
    in_set = Card.objects.filter(expansion_id=expansion_id)
    first = in_set.first()
    if not first:
        raise Http404("No cards saved for this set")
    return card_browser(request, in_set, {
        "title": first.expansion,
        "clear_url": reverse("weiss:set", args=[expansion_id]),
        "series": series_code(first.serial_number),
    })


@weiss_access_required
def series_detail(request, code):
    """Every saved card from one series (e.g. all OSK cards), across all of its sets."""
    in_series = Card.objects.filter(serial_number__startswith=f"{code}/")
    if not in_series.exists():
        raise Http404("No cards saved for this series")
    sets = dict(in_series.exclude(expansion_id=None).values_list("expansion_id", "expansion"))
    return card_browser(request, in_series, {
        "title": f"All {code} cards",
        "clear_url": reverse("weiss:series", args=[code]),
        "series_page": True,
        "sets": sorted(sets.items(), reverse=True),
    })


@weiss_access_required
def card_detail(request, pk):
    card = with_image_urls([get_object_or_404(Card.objects.prefetch_related("prices"), pk=pk)])[0]
    # Opened from one of the user's lists (?list=<pk>): offer a way back to it.
    from_list = None
    if request.GET.get("list", "").isdigit():
        from_list = CardList.objects.filter(pk=request.GET["list"], user=request.user).first()
    return render(request, "weiss/card_detail.html", {
        "card": card, "series": series_code(card.serial_number), "from_list": from_list,
    })


@weiss_access_required
def card_popup(request, pk):
    """Just the picture, stats and text of a card, for the deck builder's popup. ?next= is the page
    the popup opened on, so its +/- forms (and the panel they re-render) point back there."""
    card = with_image_urls([get_object_or_404(Card.objects.prefetch_related("prices"), pk=pk)])[0]
    next_url = request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse("weiss:card", args=[card.pk])
    return render(request, "weiss/card_popup.html", {"card": card, "panel_next": next_url})


@weiss_access_required
def card_image(request, pk):
    """A stable image URL for a card (the game board uses it), redirecting to a fresh S3 link.

    The browser may cache the redirect for a while, so the board doesn't refetch images every update.
    """
    card = get_object_or_404(Card, pk=pk)
    url = with_image_urls([card])[0].image_src
    if not url:
        raise Http404("No image for this card")
    response = redirect(url)
    response["Cache-Control"] = f"private, max-age={settings.IMAGE_LINK_SECONDS - 300}"
    return response
