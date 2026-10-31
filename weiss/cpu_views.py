"""The staff's CPU creation tab: decks reserved for CPUs, and the profiles players can challenge."""
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import abilities, cpu
from .lists import EXPRESS_PROMPT, SESSION_KEY, deck_checks, sorted_entries
from .models import Card, CardList, CpuProfile


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


def excluded_cards():
    """Cards left out of CPU decks, one printing of each name, with the parts that need doing by hand."""
    found = {}
    for card in Card.objects.exclude(description="").only("name", "serial_number", "description").order_by("serial_number"):
        if card.name not in found:
            parts = abilities.by_hand_parts(card.description)
            if parts:
                found[card.name] = {"name": card.name, "serial": card.serial_number, "text": card.description, "parts": parts}
    return sorted(found.values(), key=lambda c: c["name"])


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
    return {"name": name, "model": model, "aggression": aggression, "deck": deck}, None


@staff_required
def cpu_home(request):
    decks = CardList.objects.filter(reserved_for_cpu=True).select_related("user").annotate(total=Sum("entries__quantity"))
    profiles = list(CpuProfile.objects.select_related("deck"))
    for profile in profiles:
        profile.problem = deck_problem(profile.deck)
    return render(request, "weiss/cpu_home.html", {
        "decks": decks, "profiles": profiles, "models": cpu.MODELS.items(),
        "aggressions": range(cpu.MIN_AGGRESSION, cpu.MAX_AGGRESSION + 1),
        "excluded": excluded_cards(),
    })


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
