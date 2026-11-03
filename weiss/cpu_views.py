"""The staff's CPU creation tab: decks reserved for CPUs, the profiles players can challenge, and arcade lists."""
import logging
import uuid
from functools import wraps

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q, Sum, Value
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core import s3
from core.access import weiss_access_required

from . import abilities, arcade, cpu, packs, scenes
from .lists import EXPRESS_PROMPT, SESSION_KEY, deck_checks, sorted_entries
from .card_images import image_type
from .models import ArcadeEntry, ArcadeScenario, Card, CardList, CpuImage, CpuProfile, NarrativeChallenge, Scene
from .profiles import avatar_picker


log = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TEXT = 1000
IMAGES_PER_PAGE = 60
TEXT_FIELDS = ("intro_text", "player_win_text", "player_lose_text")


def staff_required(view):
    @wraps(view)
    @weiss_access_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def deck_problem(deck):
    """Why this deck isn't ready for a CPU to play, or None."""
    if not deck:
        return "It needs a deck."
    entries = sorted_entries(deck)
    by_hand = sorted({e.card.name for e in entries if abilities.by_hand_parts(e.card.description)})
    if by_hand:
        return "Its deck has cards a CPU can't play, needing steps done by hand: " + ", ".join(by_hand) + "."
    checks = deck_checks(entries)
    if not checks["exact"]:
        return f"Its deck has {checks['total']} cards, not {checks['size']}."
    climaxes = next(g for g in checks["groups"] if g["required"])
    if not climaxes["ok"]:
        return f"Its deck has {climaxes['count']} climaxes, not {climaxes['target']}."
    if checks["over_limit"]:
        return "Its deck has too many copies of " + ", ".join(checks["over_limit"]) + "."
    return None


excluded_memo = (None, None)  # (what the cards looked like, the answer): reading every card's text takes a while


def excluded_cards():
    """Cards left out of CPU decks, one printing of each name, with the parts that need doing by hand."""
    global excluded_memo
    version = Card.objects.exclude(description="").aggregate(Count("pk"), Max("updated"))
    if excluded_memo[0] == version:
        return excluded_memo[1]
    found = {}
    for card in Card.objects.exclude(description="").only("name", "serial_number", "description").order_by("serial_number"):
        if card.name not in found:
            parts = abilities.by_hand_parts(card.description)
            if parts:
                found[card.name] = {"name": card.name, "serial": card.serial_number, "text": card.description, "parts": parts}
    cards = sorted(found.values(), key=lambda c: c["name"])
    excluded_memo = (version, cards)
    return cards


def read_profile_form(request):
    """(fields, error) from a profile form."""
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        return None, "Give the CPU a name."
    model = request.POST.get("model", "standard")
    if model not in cpu.MODELS:
        return None, "That isn't a CPU model."
    try:
        aggression = int(request.POST.get("aggression", cpu.MIN_AGGRESSION))
    except ValueError:
        aggression = 0
    if not cpu.MIN_AGGRESSION <= aggression <= cpu.MAX_AGGRESSION:
        return None, f"Aggression goes from {cpu.MIN_AGGRESSION} to {cpu.MAX_AGGRESSION}."
    deck = CardList.objects.filter(pk=request.POST.get("deck") or None, reserved_for_cpu=True).first()
    texts = {field: request.POST.get(field, "").strip()[:MAX_TEXT] for field in TEXT_FIELDS}
    return {"name": name, "model": model, "aggression": aggression, "deck": deck, **texts}, None


@staff_required
def cpu_home(request):
    decks = CardList.objects.filter(reserved_for_cpu=True).select_related("user").annotate(total=Sum("entries__quantity"))
    profiles = list(CpuProfile.objects.select_related("deck", "image"))
    for profile in profiles:
        profile.problem = deck_problem(profile.deck)
        profile.model_label = cpu.MODELS.get(profile.model, profile.model)
    scenarios = arcade.all_scenarios()
    for scenario in scenarios:
        scenario.problem = arcade.scenario_problem(scenario)
    return render(request, "weiss/cpu_home.html", {
        "decks": decks, "profiles": profiles, "models": cpu.MODELS.items(), "scenes": scenes.scene_list(),
        "narratives": NarrativeChallenge.objects.select_related("scenario"), "pack_sets": packs.pack_sets(),
        "scenarios": scenarios, "arcade_roles": ArcadeEntry.Role.choices,
        "aggressions": range(cpu.MIN_AGGRESSION, cpu.MAX_AGGRESSION + 1),
    })


@staff_required
def cpu_excluded(request):
    """The list of cards a CPU can't play. It's long and slow to work out, so the tab fetches it when it's opened."""
    return render(request, "weiss/cpu_excluded.html", {"excluded": excluded_cards()})


@staff_required
def cpu_excluded_export(request):
    """The cards a CPU can't play, with their full text and what's stopping it, as a text file."""
    cards = excluded_cards()
    lines = [f"{len(cards)} card{'' if len(cards) == 1 else 's'} a CPU can't play", ""]
    for card in cards:
        lines += [f"{card['name']} ({card['serial']})", card["text"], "Needs doing by hand:"]
        lines += [f"  - {part}" for part in card["parts"]]
        lines.append("")
    response = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="cpu-unplayable-cards.txt"'
    return response


@staff_required
@require_POST
def cpu_deck_create(request):
    """A new deck, reserved for CPUs, built just like any other: the same prompt, express or by hand."""
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        messages.error(request, "Give the deck a name.")
        return redirect("weiss:cpu_home")
    deck = CardList.objects.create(user=request.user, name=name, reserved_for_cpu=True)
    request.session[SESSION_KEY] = deck.pk
    request.session[EXPRESS_PROMPT] = deck.pk
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def cpu_profile_create(request):
    fields, error = read_profile_form(request)
    if error:
        messages.error(request, error)
    else:
        CpuProfile.objects.create(created_by=request.user, **fields)
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def cpu_profile_update(request, pk):
    profile = get_object_or_404(CpuProfile, pk=pk)
    fields, error = read_profile_form(request)
    if error:
        messages.error(request, error)
        return redirect("weiss:cpu_home")
    for field, value in fields.items():
        setattr(profile, field, value)
    if profile.finalized and deck_problem(profile.deck):
        profile.finalized = False
        messages.warning(request, f"{profile.name} is no longer available to players: {deck_problem(profile.deck)}")
    profile.save()
    return redirect("weiss:cpu_home")


@staff_required
def cpu_picture(request, pk):
    profile = get_object_or_404(CpuProfile, pk=pk)
    return avatar_picker(request, profile, profile.name, reverse("weiss:cpu_home"))


def forget_image(key):
    """The old file isn't needed. If it can't be deleted it's only a stray file, nothing to stop for."""
    try:
        s3.delete(key)
    except (BotoCoreError, ClientError):
        log.warning("Couldn't delete %s from S3", key, exc_info=True)


def chosen_screen(params):
    screen = params.get("screen")
    return screen if screen in CpuProfile.SCREENS else "main"


def set_screen_image(profile, screen, image):
    field = CpuProfile.SCREENS[screen]
    setattr(profile, field, image)
    profile.save(update_fields=[field, "updated"])
    return redirect(f"{reverse('weiss:cpu_images', args=[profile.pk])}?screen={screen}")


def image_groups(images, current=None):
    """The images, one group to each character of a series, in the order their newest image comes.
    An image with no name is a group of its own. A page is so many groups, so none is split."""
    groups = {}
    for image in images:
        key = (image.name.strip().lower(), image.series.strip().lower()) if image.name.strip() else image.pk
        groups.setdefault(key, {"name": image.name, "series": image.series, "images": []})["images"].append(image)
    for group in groups.values():
        group["current"] = bool(current) and any(image.pk == current.pk for image in group["images"])
    return list(groups.values())


@staff_required
def cpu_images(request, pk):
    """The pool of images, to choose this CPU's avatar from. A page of its own: the pool can be large."""
    profile = get_object_or_404(CpuProfile.objects.select_related("image", "intro_image", "player_win_image", "player_lose_image"), pk=pk)
    screen = chosen_screen(request.GET)
    query = request.GET.get("q", "").strip()
    images = CpuImage.objects.order_by("-created", "-pk").annotate(uses=sum((Count(field, distinct=True) for field in ("profiles", "intro_profiles", "win_profiles", "lose_profiles")), Value(0)))
    if query:
        images = images.filter(Q(name__icontains=query) | Q(series__icontains=query))
    current = getattr(profile, CpuProfile.SCREENS[screen])
    return render(request, "weiss/cpu_images.html", {
        "profile": profile, "query": query, "page": Paginator(image_groups(images, current), IMAGES_PER_PAGE).get_page(request.GET.get("page")),
        "screen": screen, "current": getattr(profile, CpuProfile.SCREENS[screen]),
        "screens": [{"key": key, "label": label, "image": getattr(profile, CpuProfile.SCREENS[key])} for key, label in CpuProfile.SCREEN_LABELS.items()],
    })


@staff_required
def cpu_pool_image(request, pk):
    """A stable link to an image in the pool, redirecting to a fresh S3 link, as card images do."""
    image = get_object_or_404(CpuImage, pk=pk)
    response = redirect(s3.presigned_image_urls([image.key])[image.key])
    response["Cache-Control"] = f"private, max-age={settings.IMAGE_LINK_SECONDS - 300}"
    return response


@staff_required
@require_POST
def cpu_image_choose(request, pk):
    profile = get_object_or_404(CpuProfile, pk=pk)
    value = request.POST.get("image", "")
    return set_screen_image(profile, chosen_screen(request.POST), get_object_or_404(CpuImage, pk=value) if value.isdigit() else None)


@staff_required
@require_POST
def cpu_image_upload(request, pk):
    """Staff only: nobody else can put a file on the site. Its name and stated type are never used.
    The image joins the pool, and this CPU starts using it."""
    profile = get_object_or_404(CpuProfile, pk=pk)
    upload = request.FILES.get("image")
    if not upload:
        messages.error(request, "Choose an image to upload.")
    elif upload.size > MAX_IMAGE_BYTES:
        messages.error(request, "That image is over 5 MB.")
    else:
        kind = image_type(upload.read(12))
        upload.seek(0)
        if not kind:
            messages.error(request, "That isn't a PNG, JPEG, GIF or WebP image.")
        elif not settings.AWS_S3_BUCKET:
            messages.error(request, "Image storage isn't set up here.")
        else:
            key = f"{settings.WEISS_S3_PREFIX}cpu-images/pool-{uuid.uuid4().hex}{kind[0]}"
            try:
                s3.upload(key, upload, kind[1])
            except (BotoCoreError, ClientError):
                log.exception("Couldn't upload a CPU image")
                messages.error(request, "The image couldn't be uploaded. Try again.")
            else:
                return set_screen_image(profile, chosen_screen(request.POST), CpuImage.objects.create(key=key, name=request.POST.get("name", "").strip()[:200], created_by=request.user))
    return redirect(f"{reverse('weiss:cpu_images', args=[profile.pk])}?screen={chosen_screen(request.POST)}")


@staff_required
@require_POST
def cpu_image_remove(request, pk):
    """This CPU stops using its image. The image stays in the pool for any other."""
    return set_screen_image(get_object_or_404(CpuProfile, pk=pk), chosen_screen(request.POST), None)


@staff_required
@require_POST
def cpu_image_delete(request, pk):
    """Out of the pool for good: any CPU using it goes back to having no image."""
    image = get_object_or_404(CpuImage, pk=pk)
    key = image.key
    image.delete()
    forget_image(key)
    back = request.POST.get("profile", "")
    if back.isdigit() and CpuProfile.objects.filter(pk=back).exists():
        return redirect("weiss:cpu_images", pk=back)
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def arcade_create(request):
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        messages.error(request, "Give the arcade list a name.")
    elif ArcadeScenario.objects.filter(name=name).exists():
        messages.error(request, f"There's already an arcade list called {name}.")
    else:
        ArcadeScenario.objects.create(name=name, created_by=request.user)
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def arcade_delete(request, pk):
    get_object_or_404(ArcadeScenario, pk=pk).delete()  # runs under way carry on, and decks keep their markers
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def arcade_entry_add(request, pk):
    scenario = get_object_or_404(ArcadeScenario, pk=pk)
    profile = get_object_or_404(CpuProfile, pk=request.POST.get("cpu"))
    role = request.POST.get("role")
    if role not in ArcadeEntry.Role.values:
        messages.error(request, "That isn't a place in an arcade list.")
    elif scenario.entries.filter(cpu=profile).exists():
        messages.error(request, f"{profile.name} is already in {scenario.name}.")
    elif role != ArcadeEntry.Role.FILLER and scenario.entries.filter(role=role).exists():
        messages.error(request, f"{scenario.name} already has an {role}. Remove that one first.")
    else:
        ArcadeEntry.objects.create(scenario=scenario, cpu=profile, role=role)
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def arcade_entry_remove(request, pk):
    get_object_or_404(ArcadeEntry, pk=pk).delete()
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def arcade_scenes(request, pk):
    """Which scenes an arcade list plays: at its start and its clear, and before and after each CPU's fight."""
    scenario = get_object_or_404(ArcadeScenario, pk=pk)
    found = Scene.objects.in_bulk()
    pick = lambda field: found.get(int(request.POST[field])) if request.POST.get(field, "").isdigit() else None
    scenario.intro_scene, scenario.outro_scene = pick("intro"), pick("outro")
    scenario.save(update_fields=["intro_scene", "outro_scene"])
    for entry in scenario.entries.all():
        entry.scene_before, entry.scene_after = pick(f"before-{entry.pk}"), pick(f"after-{entry.pk}")
        entry.save(update_fields=["scene_before", "scene_after"])
    messages.success(request, f"Saved {scenario.name}'s scenes.")
    return redirect("weiss:cpu_home")


def narrative_fields(request):
    """(name, description, scenario, sets) from a narrative challenge's form, or raise ValueError saying what's wrong."""
    name = request.POST.get("name", "").strip()[:100]
    if not name:
        raise ValueError("Give the challenge a name.")
    scenario = ArcadeScenario.objects.filter(pk=request.POST.get("scenario") or 0).first()
    if not scenario:
        raise ValueError("Choose the arcade list it fights through.")
    sets = sorted({int(pk) for pk in request.POST.getlist("sets") if pk.isdigit()})
    if not sets:
        raise ValueError("Choose at least one set for its packs.")
    return name, request.POST.get("description", "").strip()[:2000], scenario, sets


@staff_required
@require_POST
def narrative_create(request):
    try:
        name, description, scenario, sets = narrative_fields(request)
        if NarrativeChallenge.objects.filter(name=name).exists():
            raise ValueError(f"There's already a challenge called {name}.")
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("weiss:cpu_home")
    NarrativeChallenge.objects.create(name=name, description=description, scenario=scenario, sets=sets, created_by=request.user)
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def narrative_update(request, pk):
    narrative = get_object_or_404(NarrativeChallenge, pk=pk)
    try:
        name, description, scenario, sets = narrative_fields(request)
        if NarrativeChallenge.objects.filter(name=name).exclude(pk=pk).exists():
            raise ValueError(f"There's already a challenge called {name}.")
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("weiss:cpu_home")
    narrative.name, narrative.description, narrative.scenario, narrative.sets = name, description, scenario, sets
    narrative.save()  # challenges under way keep the sets they started with
    messages.success(request, f"Saved {name}.")
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def narrative_delete(request, pk):
    get_object_or_404(NarrativeChallenge, pk=pk).delete()  # challenges under way carry on
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def cpu_profile_finalize(request, pk):
    """Offer this CPU to players, or (finalized=off) take it back."""
    profile = get_object_or_404(CpuProfile, pk=pk)
    wanted = request.POST.get("finalized") == "on"
    if wanted and deck_problem(profile.deck):
        messages.error(request, f"{profile.name} can't be finalized yet. {deck_problem(profile.deck)}")
        return redirect("weiss:cpu_home")
    profile.finalized = wanted
    profile.save(update_fields=["finalized", "updated"])
    return redirect("weiss:cpu_home")


@staff_required
@require_POST
def cpu_profile_delete(request, pk):
    profile = get_object_or_404(CpuProfile, pk=pk)
    messages.success(request, f"Deleted {profile.name}.")
    profile.delete()  # games against it keep going, at its default settings
    return redirect("weiss:cpu_home")
