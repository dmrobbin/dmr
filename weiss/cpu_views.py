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

from . import abilities, arcade, challenge, coop, cpu, packs, scenes
from .lists import EXPRESS_PROMPT, SESSION_KEY, deck_checks, sorted_entries
from .card_images import image_type
from .event_scenes import STARTERS
from .models import ArcadeEntry, ArcadeScenario, Card, CardList, ChallengeSettings, CpuImage, CpuProfile, NarrativeChallenge, Scene
from .profiles import avatar_picker


log = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TEXT = 1000
IMAGES_PER_PAGE = 60
TEXT_FIELDS = ("intro_text", "player_win_text", "player_lose_text", "combo_text")
MAX_START_PACKS = 60  # the most an infinite challenge can be set to start with
MAX_LOADOUT = 10  # ...of each specialty pack
MAX_TIER_FLOORS = 30  # floors a tier of CPU can be set to last
MAX_COOP_LOSSES = 20  # the most lost games a co-op challenge can be set to take
MAX_BOSS_EVERY = 50  # the most floors apart bosses can be set
MAX_BOSS_HEALTH = 200  # the most a co-op boss's health can be set to


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
    return {"name": name, "model": model, "aggression": aggression, "deck": deck, "boss": bool(request.POST.get("boss")), **texts}, None


# The tab's own tabs: one at a time, each worked out only when it's open (?tab=...).
TABS = {"profiles": "Profiles", "scenes": "Scenes", "decks": "Decks", "arcade": "Arcade lists", "challenges": "Narrative challenges",
        "infinite": "Infinite challenge", "unplayable": "Unplayable cards"}


def back_to(tab):
    """Where a form on one of the tabs goes once it's done: back to that tab."""
    return redirect(f"{reverse('weiss:cpu_home')}?tab={tab}")


def cpu_decks():
    return CardList.objects.filter(reserved_for_cpu=True).select_related("user").annotate(total=Sum("entries__quantity")).order_by("-updated", "-pk")


def profile_form_context():
    return {"decks": cpu_decks(), "models": cpu.MODELS.items(), "aggressions": range(cpu.MIN_AGGRESSION, cpu.MAX_AGGRESSION + 1)}


def with_status(profiles):
    """Each profile with its label, whether it's ready (problem: why not), and its status for the filters."""
    for profile in profiles:
        profile.problem = deck_problem(profile.deck)
        profile.model_label = cpu.MODELS.get(profile.model, profile.model)
        profile.status = "live" if profile.finalized else "draft" if profile.problem else "ready"
    return profiles


def scene_uses():
    """{scene id: [where it plays, ...]}: the arcade lists' moments that play each scene, for the scenes list."""
    uses = {}
    for scenario in ArcadeScenario.objects.prefetch_related("entries__cpu"):
        for scene_id, moment in ((scenario.intro_scene_id, "opening"), (scenario.outro_scene_id, "ending")):
            if scene_id:
                uses.setdefault(scene_id, []).append(f"{scenario.name} ({moment})")
        for entry in scenario.entries.all():
            for scene_id, moment in ((entry.scene_before_id, "before"), (entry.scene_after_id, "after")):
                if scene_id:
                    uses.setdefault(scene_id, []).append(f"{scenario.name} ({moment} {entry.cpu.name})")
    return uses


@staff_required
def cpu_home(request):
    tab = request.GET.get("tab") if request.GET.get("tab") in TABS else "profiles"
    counts = {"profiles": CpuProfile.objects.count(), "scenes": Scene.objects.count(), "decks": CardList.objects.filter(reserved_for_cpu=True).count(),
              "arcade": ArcadeScenario.objects.count(), "challenges": NarrativeChallenge.objects.count()}
    context = {"tab": tab, "tabs": [(key, label, counts.get(key)) for key, label in TABS.items()]}
    if tab == "profiles":
        profiles = with_status(list(CpuProfile.objects.select_related("deck", "image").order_by("name")))
        lists = {}
        for entry in ArcadeEntry.objects.select_related("scenario"):
            lists.setdefault(entry.cpu_id, set()).add(entry.scenario.name)
        for profile in profiles:
            profile.lists = sorted(lists.get(profile.pk, ()))
        context.update(profiles=profiles, **profile_form_context())
    elif tab == "scenes":
        found = scenes.scene_list()
        uses = scene_uses()
        for scene in found:
            scene.uses = uses.get(scene.pk, [])
        context.update(scenes=found, starter_count=len(STARTERS))
    elif tab == "decks":
        users = {}
        for profile in CpuProfile.objects.exclude(deck=None).only("name", "deck_id"):
            users.setdefault(profile.deck_id, []).append(profile.name)
        decks = list(cpu_decks())
        for deck in decks:
            deck.cpus = sorted(users.get(deck.pk, []))
        context.update(decks=decks)
    elif tab == "arcade":
        scenarios = arcade.all_scenarios()
        for scenario in scenarios:
            scenario.problem = arcade.scenario_problem(scenario)
        context.update(scenarios=scenarios, profiles=CpuProfile.objects.order_by("name"), scenes=scenes.scene_list(), arcade_roles=ArcadeEntry.Role.choices)
    elif tab == "challenges":
        scenarios = arcade.all_scenarios()
        for scenario in scenarios:
            scenario.problem = arcade.scenario_problem(scenario)
        context.update(narratives=NarrativeChallenge.objects.select_related("scenario"), scenarios=scenarios, pack_sets=packs.pack_sets())
    elif tab == "infinite":
        from .buffs import BUFFS
        settings = ChallengeSettings.current()
        chosen = settings.loadout if settings else {}
        models = challenge.infinite_models()
        context.update(infinite=settings, event_percent=round(challenge.event_chance() * 100),
                       default_percent=round(challenge.EVENT_CHANCE * 100), event_scenes=len(challenge.event_scenes()),
                       path_ahead=challenge.PATH_AHEAD, start_packs=challenge.infinite_start_packs(), max_start_packs=MAX_START_PACKS,
                       loadout=[{"id": buff, "name": BUFFS[buff].name, "description": BUFFS[buff].description, "count": chosen.get(buff, 0)}
                                for buff in challenge.LOADOUT_BUFFS], max_loadout=MAX_LOADOUT, max_tier_floors=MAX_TIER_FLOORS,
                       tiers=[{"index": i, "name": name, "floors": count, "models": " or ".join(m.title() for m in tier_models),
                               "default": challenge.INFINITE_MODELS[i][0]}
                              for i, (name, (count, tier_models)) in enumerate(zip(challenge.INFINITE_TIERS, models))],
                       hard_from=sum(count for count, _ in models) + 1,
                       coop_losses=coop.loss_limit(), max_coop_losses=MAX_COOP_LOSSES, coop_start_packs=coop.start_packs(),
                       coop_loadout=[{"id": buff, "name": BUFFS[buff].name, "count": (settings.coop_loadout if settings else {}).get(buff, 0)}
                                     for buff in challenge.LOADOUT_BUFFS],
                       boss_every=challenge.boss_every(), coop_boss_every=challenge.boss_every(coop=True), coop_boss_health=coop.boss_health(),
                       max_boss_every=MAX_BOSS_EVERY, max_boss_health=MAX_BOSS_HEALTH, boss_stock=challenge.BOSS_STOCK, boss_packs=challenge.BOSS_PACKS,
                       bosses=CpuProfile.objects.filter(boss=True).order_by("name"))
    return render(request, "weiss/cpu_home.html", context)


@staff_required
def cpu_profile(request, pk):
    """One CPU profile's page: its pictures, how it plays and what it says, and where it's used. Saving comes back here."""
    profile = get_object_or_404(CpuProfile.objects.select_related("deck", "image"), pk=pk)
    if request.method == "POST":
        fields, error = read_profile_form(request)
        if error:
            messages.error(request, error)
            return redirect("weiss:cpu_profile_update", pk=pk)
        for field, value in fields.items():
            setattr(profile, field, value)
        if profile.finalized and deck_problem(profile.deck):
            profile.finalized = False
            messages.warning(request, f"{profile.name} is no longer available to players: {deck_problem(profile.deck)}")
        profile.save()
        messages.success(request, f"Saved {profile.name}.")
        return redirect("weiss:cpu_profile_update", pk=pk)
    with_status([profile])
    entries = ArcadeEntry.objects.filter(cpu=profile).select_related("scenario").order_by("scenario__name")
    # The scenes it's cast in (by its name or number, as a script's cast lines find it); only those that could be are read.
    maybe = Scene.objects.filter(Q(script__icontains=profile.name) | Q(script__contains=f"#{profile.pk}")).order_by("name")
    cast_in = [scene for scene in maybe if any(p.pk == profile.pk for p in scenes.compile_scene(scene.script)[0]["cast"].values())]
    return render(request, "weiss/cpu_profile.html", {"profile": profile, "entries": entries, "cast_in": cast_in, **profile_form_context()})


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
        return back_to("decks")
    deck = CardList.objects.create(user=request.user, name=name, reserved_for_cpu=True)
    request.session[SESSION_KEY] = deck.pk
    request.session[EXPRESS_PROMPT] = deck.pk
    return back_to("decks")


@staff_required
@require_POST
def cpu_profile_create(request):
    """A new profile, then its own page to finish it: pictures, lines and all."""
    fields, error = read_profile_form(request)
    if error:
        messages.error(request, error)
        return back_to("profiles")
    profile = CpuProfile.objects.create(created_by=request.user, **fields)
    return redirect("weiss:cpu_profile_update", pk=profile.pk)


cpu_profile_update = cpu_profile  # the profile's page answers both: showing it, and saving it


@staff_required
def cpu_picture(request, pk):
    profile = get_object_or_404(CpuProfile, pk=pk)
    return avatar_picker(request, profile, profile.name, reverse("weiss:cpu_profile_update", args=[pk]))


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
    return back_to("profiles")


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
    return back_to("arcade")


@staff_required
@require_POST
def arcade_delete(request, pk):
    get_object_or_404(ArcadeScenario, pk=pk).delete()  # runs under way carry on, and decks keep their markers
    return back_to("arcade")


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
    elif role in (ArcadeEntry.Role.OPENER, ArcadeEntry.Role.ANCHOR) and scenario.entries.filter(role=role).exists():
        messages.error(request, f"{scenario.name} already has an {role}. Remove that one first.")
    else:
        # A filler goes after those there are, in a narrative challenge's order.
        last = scenario.entries.filter(role=role).order_by("-position").values_list("position", flat=True).first()
        ArcadeEntry.objects.create(scenario=scenario, cpu=profile, role=role, position=(last or 0) + 1)
    return back_to("arcade")


@staff_required
@require_POST
def arcade_entry_remove(request, pk):
    get_object_or_404(ArcadeEntry, pk=pk).delete()
    return back_to("arcade")


@staff_required
@require_POST
def arcade_order(request, pk):
    """The order a narrative challenge fights an arcade list's fillers in (an arcade run shuffles them)."""
    scenario = get_object_or_404(ArcadeScenario, pk=pk)
    for entry in scenario.entries.filter(role=ArcadeEntry.Role.FILLER):
        value = request.POST.get(f"position-{entry.pk}", "")
        if value.isdigit():
            entry.position = min(int(value), 99)
            entry.save(update_fields=["position"])
    messages.success(request, f"Saved {scenario.name}'s order.")
    return back_to("arcade")


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
    return back_to("arcade")


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
def infinite_settings(request):
    """How the infinite challenge is tuned: how often its path offers an event (0, never, to 100, on every floor after
    the first), the packs it starts with and the specialty packs besides, and how many floors each tier of CPU lasts."""
    def whole(key, low, high, what):
        try:
            value = int(request.POST.get(key, ""))
        except ValueError:
            value = None
        if value is None or not low <= value <= high:
            raise ValueError(f"{what} goes from {low} to {high}.")
        return value

    from .buffs import BUFFS
    try:
        fields = {
            "event_percent": whole("event_percent", 0, 100, "The event chance"),
            "start_packs": whole("start_packs", 0, MAX_START_PACKS, "Starting packs"),
            "loadout": {buff: n for buff in challenge.LOADOUT_BUFFS if (n := whole(f"loadout_{buff}", 0, MAX_LOADOUT, BUFFS[buff].name))},
            "tier_floors": [whole(f"tier_{i}", 0, MAX_TIER_FLOORS, f"{name} floors") for i, name in enumerate(challenge.INFINITE_TIERS)],
            "coop_loss_limit": whole("coop_loss_limit", 1, MAX_COOP_LOSSES, "The co-op loss limit"),
            "coop_start_packs": whole("coop_start_packs", 0, MAX_START_PACKS, "Co-op starting packs"),
            "coop_loadout": {buff: n for buff in challenge.LOADOUT_BUFFS
                             if (n := whole(f"coop_loadout_{buff}", 0, MAX_LOADOUT, f"Co-op {BUFFS[buff].name.lower()}"))},
            "boss_every": whole("boss_every", 0, MAX_BOSS_EVERY, "Floors between solo bosses"),
            "coop_boss_every": whole("coop_boss_every", 0, MAX_BOSS_EVERY, "Floors between co-op bosses"),
            "coop_boss_health": whole("coop_boss_health", 1, MAX_BOSS_HEALTH, "A co-op boss's health"),
        }
    except ValueError as error:
        messages.error(request, str(error))
        return back_to("infinite")
    if not fields["start_packs"] and not fields["loadout"] or not fields["coop_start_packs"] and not fields["coop_loadout"]:
        messages.error(request, "A challenge needs something to build a deck from: some packs or some specialty packs.")
        return back_to("infinite")
    ChallengeSettings.objects.update_or_create(pk=1, defaults={**fields, "updated_by": request.user})
    messages.success(request, "Saved: new challenges start with these packs, and runs under way use the new event chance, tiers and "
                              "boss spacing from the next floors laid out.")
    return back_to("infinite")


@staff_required
@require_POST
def narrative_create(request):
    try:
        name, description, scenario, sets = narrative_fields(request)
        if NarrativeChallenge.objects.filter(name=name).exists():
            raise ValueError(f"There's already a challenge called {name}.")
    except ValueError as error:
        messages.error(request, str(error))
        return back_to("challenges")
    NarrativeChallenge.objects.create(name=name, description=description, scenario=scenario, sets=sets, created_by=request.user)
    return back_to("challenges")


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
        return back_to("challenges")
    narrative.name, narrative.description, narrative.scenario, narrative.sets = name, description, scenario, sets
    narrative.save()  # challenges under way keep the sets they started with
    messages.success(request, f"Saved {name}.")
    return back_to("challenges")


@staff_required
@require_POST
def narrative_delete(request, pk):
    get_object_or_404(NarrativeChallenge, pk=pk).delete()  # challenges under way carry on
    return back_to("challenges")


@staff_required
@require_POST
def cpu_profile_finalize(request, pk):
    """Offer this CPU to players, or (finalized=off) take it back."""
    profile = get_object_or_404(CpuProfile, pk=pk)
    wanted = request.POST.get("finalized") == "on"
    if wanted and deck_problem(profile.deck):
        messages.error(request, f"{profile.name} can't be finalized yet. {deck_problem(profile.deck)}")
        return redirect("weiss:cpu_profile_update", pk=pk)
    profile.finalized = wanted
    profile.save(update_fields=["finalized", "updated"])
    return redirect("weiss:cpu_profile_update", pk=pk)


@staff_required
@require_POST
def cpu_profile_delete(request, pk):
    profile = get_object_or_404(CpuProfile, pk=pk)
    messages.success(request, f"Deleted {profile.name}.")
    profile.delete()  # games against it keep going, at its default settings
    return back_to("profiles")
