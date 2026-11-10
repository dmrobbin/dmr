"""Card sleeves (see weiss.sleeves): players choosing theirs on their profile, and staff making them on the CPU
creation tab: uploading a picture cropped to a card's shape, setting what unlocks it, hiding it, and giving it out."""
import logging
import uuid

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core import s3
from core.access import weiss_access_required

from . import sleeves
from .card_images import image_type
from .cpu_views import MAX_IMAGE_BYTES, back_to, forget_image, staff_required
from .models import ArcadeScenario, CpuProfile, NarrativeChallenge, PlayerProfile, Sleeve, SleeveUnlock

log = logging.getLogger(__name__)

CROP_WIDTH, CROP_HEIGHT = 500, 700  # what the cropper draws a sleeve's picture at: a card's shape (sleeve_crop.js)


# Players ------------------------------------------------------------------------------------------------------------

@weiss_access_required
def sleeve_image(request, pk):
    """A stable link to an uploaded sleeve's picture, redirecting to a fresh S3 link, as card images do. Anyone
    playing can see it: it's on their opponent's cards."""
    sleeve = get_object_or_404(Sleeve, pk=pk)
    if not sleeve.key:
        raise Http404("This sleeve has no picture")
    response = redirect(s3.presigned_image_urls([sleeve.key])[sleeve.key])
    response["Cache-Control"] = f"private, max-age={settings.IMAGE_LINK_SECONDS - 300}"
    return response


@weiss_access_required
@require_POST
def sleeve_choose(request):
    profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
    sleeve = Sleeve.objects.filter(pk=request.POST.get("sleeve") if str(request.POST.get("sleeve", "")).isdigit() else None).first()
    if not sleeve or not sleeves.can_use(request.user, sleeve, profile):
        messages.error(request, "You haven't unlocked that sleeve yet.")
    else:
        profile.sleeve = sleeve
        profile.save(update_fields=["sleeve"])
        messages.success(request, f"Your cards are in {sleeve.name} sleeves now.")
    return redirect(reverse("weiss:profile") + "#sleeves")


@weiss_access_required
@require_POST
def sleeves_seen(request):
    """The banner about new sleeves, put away."""
    SleeveUnlock.objects.filter(user=request.user, seen=False).update(seen=True)
    back = request.POST.get("next", "")
    return redirect(back if back.startswith("/") and not back.startswith("//") else reverse("weiss:profile"))


# Staff --------------------------------------------------------------------------------------------------------------

def staff_list():
    """Every sleeve, for the CPU tab: with how many players have it and its conditions in words."""
    found = list(Sleeve.objects.annotate(owners=Count("unlocks")))
    names = sleeves.target_names([c for sleeve in found for c in sleeve.conditions])
    for sleeve in found:
        sleeve.described = [sleeves.describe(c, names) for c in sleeve.conditions if c.get("kind") in sleeves.KINDS]
    return found


def form_context(sleeve=None):
    """What the sleeve form needs: the kinds of condition, and what each can be limited to."""
    rows = [{**c, "target_type": sleeves.KINDS[c["kind"]].target} for c in (sleeve.conditions if sleeve else []) if c.get("kind") in sleeves.KINDS]
    return {"sleeve": sleeve, "rows": rows, "kinds": [{"id": key, "label": kind.label, "target": kind.target} for key, kind in sleeves.KINDS.items()],
            "targets": [("cpu", "Any CPU", CpuProfile.objects.order_by("name")), ("scenario", "Any arcade list", ArcadeScenario.objects.order_by("name")),
                        ("narrative", "Any narrative challenge", NarrativeChallenge.objects.order_by("name"))],
            "crop_width": CROP_WIDTH, "crop_height": CROP_HEIGHT, "matches": Sleeve.Match.choices}


def read_fields(request):
    """(fields, error) from the sleeve form, its picture aside."""
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        return None, "Give the sleeve a name."
    conditions, error = sleeves.read_conditions(request.POST)
    if error:
        return None, error
    match = request.POST.get("match", Sleeve.Match.ALL)
    if match not in Sleeve.Match.values:
        return None, "That isn't a way of matching the conditions."
    return {"name": name, "description": request.POST.get("description", "").strip()[:300], "conditions": conditions,
            "match": match, "hidden": bool(request.POST.get("hidden"))}, None


def upload_picture(request):
    """(the new picture's S3 key, error) from the form's cropped picture; (None, None) if it has none.
    Only staff can put a file on the site. Its name and stated type are never used."""
    upload = request.FILES.get("image")
    if not upload:
        return None, None
    if upload.size > MAX_IMAGE_BYTES:
        return None, "That image is over 5 MB."
    kind = image_type(upload.read(12))
    upload.seek(0)
    if not kind:
        return None, "That isn't a PNG, JPEG, GIF or WebP image."
    if not settings.AWS_S3_BUCKET:
        return None, "Image storage isn't set up here."
    key = f"{settings.WEISS_S3_PREFIX}sleeves/{uuid.uuid4().hex}{kind[0]}"
    try:
        s3.upload(key, upload, kind[1])
    except (BotoCoreError, ClientError):
        log.exception("Couldn't upload a sleeve image")
        return None, "The image couldn't be uploaded. Try again."
    return key, None


@staff_required
def sleeve_create(request):
    """A new sleeve: its picture, cropped to a card's shape, and what unlocks it."""
    if request.method == "POST":
        fields, error = read_fields(request)
        key = None
        if not error:
            key, error = upload_picture(request)
            if not key and not error:
                error = "Choose a picture for the sleeve."
        if error:
            messages.error(request, error)
            return render(request, "weiss/sleeve_edit.html", {**form_context(Sleeve(**(fields or {}))), "creating": True}, status=400)
        sleeve = Sleeve.objects.create(key=key, created_by=request.user, **fields)
        messages.success(request, f"Made the {sleeve.name} sleeve.")
        return redirect("weiss:sleeve_edit", pk=sleeve.pk)
    return render(request, "weiss/sleeve_edit.html", {**form_context(), "creating": True})


@staff_required
def sleeve_edit(request, pk):
    """A sleeve's page: its picture (a built-in one's is drawn by CSS, and stays), what unlocks it, and who has it."""
    sleeve = get_object_or_404(Sleeve, pk=pk)
    if request.method == "POST":
        fields, error = read_fields(request)
        key = None
        if not error and not sleeve.style:
            key, error = upload_picture(request)
        if error:
            messages.error(request, error)
            return redirect("weiss:sleeve_edit", pk=pk)
        for field, value in fields.items():
            setattr(sleeve, field, value)
        old = None
        if key:
            old, sleeve.key = sleeve.key, key
        sleeve.save()
        if old:
            forget_image(old)
        messages.success(request, f"Saved {sleeve.name}.")
        return redirect("weiss:sleeve_edit", pk=pk)
    owners = SleeveUnlock.objects.filter(sleeve=sleeve).select_related("user", "awarded_by")
    return render(request, "weiss/sleeve_edit.html", {**form_context(sleeve), "owners": owners,
                                                      "using": PlayerProfile.objects.filter(sleeve=sleeve).count()})


@staff_required
@require_POST
def sleeve_award(request, pk):
    """Give a player the sleeve, whatever its conditions (and even if it's hidden)."""
    sleeve = get_object_or_404(Sleeve, pk=pk)
    username = request.POST.get("username", "").strip()
    user = User.objects.filter(username__iexact=username).first() if username else None
    if not user:
        messages.error(request, f"There's no player called {username}." if username else "Type the player's username.")
    elif SleeveUnlock.objects.filter(user=user, sleeve=sleeve).exists():
        messages.info(request, f"{user.username} has {sleeve.name} already.")
    else:
        SleeveUnlock.objects.create(user=user, sleeve=sleeve, awarded_by=request.user)
        messages.success(request, f"Gave {sleeve.name} to {user.username}.")
    return redirect("weiss:sleeve_edit", pk=pk)


@staff_required
@require_POST
def sleeve_revoke(request, pk):
    """Take the sleeve back from a player. If they're using it, they go back to the default. Meeting its conditions
    again would unlock it again: hide it, or change them, to stop that."""
    sleeve = get_object_or_404(Sleeve, pk=pk)
    user_id = request.POST.get("user", "")
    if user_id.isdigit():
        SleeveUnlock.objects.filter(user_id=user_id, sleeve=sleeve).delete()
        PlayerProfile.objects.filter(user_id=user_id, sleeve=sleeve).update(sleeve=None)
        messages.success(request, f"Took {sleeve.name} back.")
    return redirect("weiss:sleeve_edit", pk=pk)


@staff_required
@require_POST
def sleeve_delete(request, pk):
    """An uploaded sleeve, gone for good: those using it go back to the default. Built-in ones stay."""
    sleeve = get_object_or_404(Sleeve, pk=pk)
    if sleeve.style:
        messages.error(request, "Built-in sleeves can't be deleted. Hide it instead.")
        return redirect("weiss:sleeve_edit", pk=pk)
    key = sleeve.key
    sleeve.delete()
    if key:
        forget_image(key)
    messages.success(request, f"Deleted {sleeve.name}.")
    return back_to("sleeves")
