from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Max
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


@staff_member_required
def set_list(request):
    sets = (
        Card.objects.exclude(expansion_id=None)
        .values("expansion_id")
        .annotate(name=Max("expansion"), cards=Count("id"))
        .order_by("-expansion_id")
    )
    return render(request, "weiss/set_list.html", {"sets": sets})


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
