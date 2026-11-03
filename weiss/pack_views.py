"""Opening booster packs, under the Play tab. Staff only while it's being tried out; nothing opened is kept."""
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from . import packs
from .cpu_views import staff_required

MAX_PACKS = 24
BOX = 16  # packs in a box


@staff_required
def pack_home(request):
    """Pick a set and how many packs."""
    return render(request, "weiss/packs.html", {"sets": packs.pack_sets(), "max_packs": MAX_PACKS, "box": BOX,
                                               "slots": packs.PACK, "pack_size": packs.PACK_SIZE})


@staff_required
def pack_open(request):
    """Open the packs, then reveal them one card at a time. A GET: opening is free, so reloading opens new ones."""
    try:
        expansion_id = int(request.GET.get("set", ""))
        count = min(max(int(request.GET.get("count", 1)), 1), MAX_PACKS)
    except ValueError:
        raise Http404("No such set")
    pool = packs.Pool.for_set(expansion_id)
    if not pool:
        raise Http404("That set has no cards that come in packs")
    name = pool.set_name
    opened = packs.open_packs(pool, count)
    return render(request, "weiss/pack_open.html", {
        "set_id": expansion_id, "set_name": name, "count": count, "pack_size": packs.PACK_SIZE,
        "opening": {"set": name, "grades": packs.GRADE_NAMES, "packs": [[pull.as_dict() for pull in pack] for pack in opened]},
        "back_url": reverse("weiss:play_packs"), "back_label": "Booster packs",
        "actions": [(f"Open {count} more", f"{reverse('weiss:play_packs_open')}?set={expansion_id}&count={count}", True),
                    ("Choose another set", reverse("weiss:play_packs"), False)],
    })
