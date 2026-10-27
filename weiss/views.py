from collections import Counter, defaultdict

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from core import s3

from .models import Card


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


@staff_member_required
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


@staff_member_required
def set_detail(request, expansion_id):
    in_set = Card.objects.filter(expansion_id=expansion_id)
    first = in_set.first()
    if not first:
        raise Http404("No cards saved for this set")

    cards = in_set
    name = request.GET.get("name", "").strip()
    color = request.GET.get("color", "")
    level = request.GET.get("level", "")
    if name:
        cards = cards.filter(name__icontains=name)
    if color:
        cards = cards.filter(color=color)
    if level == "none":
        cards = cards.filter(level=None)
    elif level.isdigit():
        cards = cards.filter(level=int(level))

    levels = sorted(set(in_set.values_list("level", flat=True)), key=lambda lv: (lv is None, lv))
    cards = cards.prefetch_related("prices")
    return render(request, "weiss/set_detail.html", {
        "expansion_id": expansion_id,
        "expansion": first.expansion,
        "total": in_set.count(),
        "cards": with_image_urls(cards),
        "colors": sorted(set(in_set.exclude(color="").values_list("color", flat=True))),
        "levels": levels,
        "filters": {"name": name, "color": color, "level": level},
        "filtered": bool(name or color or level),
    })


@staff_member_required
def card_detail(request, pk):
    card = with_image_urls([get_object_or_404(Card.objects.prefetch_related("prices"), pk=pk)])[0]
    return render(request, "weiss/card_detail.html", {"card": card})
