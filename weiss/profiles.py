"""Player profiles: their lists, the games they've played, a picture cut from a card, and their card sleeve.

A picture is a card and a circle on its image, kept as numbers and cropped by the browser. The same
picker sets a CPU's picture, from the CPU creation tab.
"""
import math

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import sleeves
from .card_images import series_title
from .models import ArcadeRun, Card, CardList, CpuProfile, GameRecord, PlayerProfile, SleeveUnlock
from .views import summarize_sets

MIN_RADIUS = .05
MAX_TALL = 2  # how many image widths tall a card can be, for checking a circle's center
SEARCH_RESULTS = 24
RECORDS_PER_PAGE = 25
HAS_IMAGE = ~Q(image_s3_key="") | ~Q(image_url="")


def read_avatar(post):
    """(fields, error) from the picker's form."""
    card = Card.objects.filter(HAS_IMAGE, pk=post.get("card") if str(post.get("card", "")).isdigit() else None).first()
    if not card:
        return None, "Choose a card with an image."
    try:
        x, y, r = float(post.get("x", "")), float(post.get("y", "")), float(post.get("r", ""))
    except ValueError:
        return None, "That isn't a circle on the card."
    tolerance = .001  # the page rounds what it sends
    if not (all(map(math.isfinite, (x, y, r))) and MIN_RADIUS <= r <= .5 + tolerance
            and r - tolerance <= x <= 1 - r + tolerance and r - tolerance <= y <= MAX_TALL):
        return None, "That isn't a circle on the card."
    return {"avatar_card": card, "avatar_x": x, "avatar_y": y, "avatar_r": r}, None


def series_options():
    """[(code, name)] for limiting the search to a series, by name: each under its newest set's title."""
    newest = {}
    for summary in sorted(summarize_sets(), key=lambda s: s["expansion_id"]):
        newest[summary["code"]] = series_title(summary["name"])
    return sorted(newest.items(), key=lambda item: item[1].lower())


def avatar_picker(request, owner, name, back):
    """The page for choosing owner's picture, and what it posts: a new picture, or none."""
    if request.method == "POST":
        fields, error = ({"avatar_card": None}, None) if "remove" in request.POST else read_avatar(request.POST)
        if error:
            messages.error(request, error)
            return redirect(request.path)
        for field, value in fields.items():
            setattr(owner, field, value)
        owner.save()
        return redirect(back)
    current = None
    if owner.avatar:
        current = {"card": owner.avatar_card_id, "image": owner.avatar["image"], "x": owner.avatar_x, "y": owner.avatar_y, "r": owner.avatar_r}
    return render(request, "weiss/avatar_picker.html", {"name": name, "avatar": owner.avatar, "current": current, "back": back,
                                                        "series": series_options()})


@weiss_access_required
def avatar_search(request):
    """Cards to choose a picture from. With a series chosen, no words are needed: its cards come up."""
    query = request.GET.get("q", "").strip()
    series = request.GET.get("series", "").strip()
    if len(query) < 2 and not series:
        return JsonResponse({"cards": []})
    cards = Card.objects.filter(HAS_IMAGE)
    if series:
        cards = cards.filter(serial_number__startswith=f"{series}/")
    if query:
        cards = cards.filter(Q(name__icontains=query) | Q(serial_number__icontains=query))
    cards = cards[:SEARCH_RESULTS]
    return JsonResponse({"cards": [{"pk": c.pk, "name": c.name, "serial": c.serial_number,
                                    "image": reverse("weiss:card_image", args=[c.pk])} for c in cards]})


def opponents_avatars(records, user):
    """Each record's other side's picture, for the page's rows."""
    cpus = {p.pk: p for p in CpuProfile.objects.filter(pk__in={r.cpu_profile_id for r in records if r.cpu_profile_id})}
    theirs = {r.guest_id if r.host_id == user.pk else r.host_id for r in records}
    people = {p.user_id: p for p in PlayerProfile.objects.filter(user_id__in=theirs - {None})}
    for record in records:
        if record.cpu_profile_id:
            owner = cpus.get(record.cpu_profile_id)
        else:
            owner = people.get(record.guest_id if record.host_id == user.pk else record.host_id)
        record.opponent_avatar = owner.avatar if owner else None


@weiss_access_required
def profile(request):
    user = request.user
    owner = PlayerProfile.objects.filter(user=user).first()
    mine = GameRecord.objects.filter(Q(host=user) | Q(guest=user))
    tally = mine.aggregate(played=Count("pk"), won=Count("pk", filter=Q(host=user, winner="host") | Q(guest=user, winner="guest")))
    page = Paginator(mine, RECORDS_PER_PAGE).get_page(request.GET.get("page"))
    records = list(page.object_list)
    opponents_avatars(records, user)
    for record in records:
        record.view_for(user)
    sleeves.check(user.pk)  # one added since their last game may be theirs already
    fresh = SleeveUnlock.objects.filter(user=user, seen=False)
    new = set(fresh.values_list("sleeve_id", flat=True))
    fresh.update(seen=True)  # they're seeing them now
    return render(request, "weiss/profile.html", {
        "avatar": owner.avatar if owner else None, "shelf": sleeves.shelf(user, owner), "new_sleeves": new,
        "lists": CardList.objects.players(user).annotate(total=Sum("entries__quantity")).order_by("-updated", "-pk").prefetch_related("arcade_clears"),
        "runs": ArcadeRun.objects.filter(user=user)[:RECORDS_PER_PAGE],
        "records": records, "page": page, "played": tally["played"], "won": tally["won"], "lost": tally["played"] - tally["won"],
    })


@weiss_access_required
def profile_picture(request):
    owner, _ = PlayerProfile.objects.get_or_create(user=request.user)
    return avatar_picker(request, owner, request.user.username, reverse("weiss:profile"))


@weiss_access_required
@require_POST
def sound_settings(request):
    """The game board's sound effects: on or off, and their volume (0 to 100). Either can be sent alone."""
    owner, _ = PlayerProfile.objects.get_or_create(user=request.user)
    if "on" in request.POST:
        owner.sound_on = request.POST["on"] == "1"
    if str(request.POST.get("volume", "")).isdigit():
        owner.sound_volume = min(100, int(request.POST["volume"]))
    owner.save(update_fields=["sound_on", "sound_volume"])
    return JsonResponse({"on": owner.sound_on, "volume": owner.sound_volume})
