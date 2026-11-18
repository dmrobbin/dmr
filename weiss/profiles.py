"""Player profiles: their lists, the games they've played, a picture cut from a card, and their card sleeve.

A picture is a card and a circle on its image, kept as numbers and cropped by the browser. The same
picker sets a CPU's picture, from the CPU creation tab.
"""
import json
import math
from collections import Counter

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import portraits, sleeves
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
def profile_portrait(request):
    """The page for making the player's portrait (see weiss.portraits), and what it posts: a recipe, or none."""
    owner, _ = PlayerProfile.objects.get_or_create(user=request.user)
    back = reverse("weiss:profile")
    if not portraits.is_ready():
        messages.error(request, "Portraits aren't set up yet.")
        return redirect(back)
    if request.method == "POST":
        if "remove" in request.POST:
            owner.portrait = {}
        else:
            try:
                recipe = json.loads(request.POST.get("recipe", ""))
            except ValueError:
                recipe = None
            recipe, problem = portraits.clean(recipe)
            if problem:
                messages.error(request, problem)
                return redirect(request.path)
            owner.portrait = recipe
        owner.save(update_fields=["portrait"])
        messages.success(request, "Portrait removed." if "remove" in request.POST else "Portrait saved.")
        return redirect(back)
    return render(request, "weiss/portrait_editor.html", {
        "back": back, "saved": bool(owner.portrait), "recipe": owner.portrait or portraits.default_recipe(),
        "editor": portraits.editor_data(), "credits": portraits.credits(),
        "scenes": (("classroom", "Classroom"), ("cafe", "Café"), ("sakura", "Outdoors"), ("city", "Night")),
        "moods": (("", "As saved"), ("happy", "Happy"), ("sad", "Sad"), ("surprised", "Surprised"), ("angry", "Angry"), ("smug", "Smug")),
    })


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
    shelf = sleeves.shelf(user, owner)
    return render(request, "weiss/profile.html", {
        "avatar": owner.avatar if owner else None, "shelf": shelf, "new_sleeves": new,
        "portrait": owner.portrait if owner else None, "portrait_json": json.dumps(owner.portrait) if owner and owner.portrait else "",
        "portraits_ready": portraits.is_ready(),
        "trophies": trophies(user, tally["played"], tally["won"], shelf),
        "lists": CardList.objects.players(user).annotate(total=Sum("entries__quantity")).order_by("-updated", "-pk").prefetch_related("arcade_clears"),
        "runs": ArcadeRun.objects.filter(user=user)[:RECORDS_PER_PAGE],
        "records": records, "page": page, "played": tally["played"], "won": tally["won"], "lost": tally["played"] - tally["won"],
    })


MAX_DEFEATED_SHOWN = 24  # CPUs in the profile's gallery of the beaten; the rest are counted


def trophies(user, played, won, shelf):
    """The top of a player's profile, what they've achieved: their win rate, the CPUs they've beaten (most beaten
    first, each with how many times), the arcade lists they've cleared with their best score on each, the deck
    they've won most with, and how many of the sleeves they can see are theirs."""
    mine = Q(host=user, winner="host") | Q(guest=user, winner="guest")
    wins = GameRecord.objects.filter(mine)
    beaten = Counter(wins.filter(cpu=True, cpu_profile__isnull=False).values_list("cpu_profile", flat=True))
    cpus = CpuProfile.objects.in_bulk(beaten)
    defeated = sorted(({"cpu": cpus[pk], "times": n} for pk, n in beaten.items() if pk in cpus),
                      key=lambda d: (-d["times"], d["cpu"].name.lower()))
    decks = Counter(name for host_id, host_deck, guest_deck in wins.values_list("host_id", "host_deck_name", "guest_deck_name")
                    for name in [host_deck if host_id == user.pk else guest_deck] if name)
    cleared = list(ArcadeRun.objects.filter(user=user, status=ArcadeRun.Status.CLEARED).values("scenario_name")
                   .annotate(times=Count("pk"), best=Max("score")).order_by("-best", "scenario_name"))
    best_run = ArcadeRun.objects.filter(user=user).aggregate(best=Max("score"))["best"] or 0
    return {
        "win_rate": round(100 * won / played) if played else None,
        "defeated": defeated[:MAX_DEFEATED_SHOWN], "defeated_more": max(0, len(defeated) - MAX_DEFEATED_SHOWN),
        "defeated_count": len(defeated),
        "cleared": cleared, "best_run": best_run,
        "top_deck": decks.most_common(1)[0] if decks else None,
        "sleeves_owned": sum(1 for item in shelf if item["owned"]), "sleeves_seen": len(shelf),
        "empty": not played and not cleared,
    }


@weiss_access_required
def profile_picture(request):
    owner, _ = PlayerProfile.objects.get_or_create(user=request.user)
    return avatar_picker(request, owner, request.user.username, reverse("weiss:profile"))


@weiss_access_required
@require_POST
def sound_settings(request):
    """The game board's sound: on or off, its volume, and the battle music's level under it (both 0 to 100).
    Any of them can be sent alone."""
    owner, _ = PlayerProfile.objects.get_or_create(user=request.user)
    if "on" in request.POST:
        owner.sound_on = request.POST["on"] == "1"
    if str(request.POST.get("volume", "")).isdigit():
        owner.sound_volume = min(100, int(request.POST["volume"]))
    if str(request.POST.get("music", "")).isdigit():
        owner.music_volume = min(100, int(request.POST["music"]))
    owner.save(update_fields=["sound_on", "sound_volume", "music_volume"])
    return JsonResponse({"on": owner.sound_on, "volume": owner.sound_volume, "music": owner.music_volume})
