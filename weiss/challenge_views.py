"""Challenge mode's pages, on the Arcade tab: starting a challenge, opening its packs, building its deck from
them, fighting its run, and keeping or discarding the deck at the end. See weiss.challenge."""
import json
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import arcade, buffs, challenge, packs
from .lists import DECK_GROUPS, DECK_SIZE
from .models import ArcadeRun, ArcadeScenario, Card, ChallengeRun, GameRoom, NarrativeChallenge
from .play import deal, not_begun, seat_cpu


def challenge_access(view):
    @wraps(view)
    @weiss_access_required
    def wrapper(request, *args, **kwargs):
        if challenge.STAFF_ONLY and not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def narratives():
    """The narrative challenges players can start: those whose arcade list is ready and that have sets."""
    ready = {scenario.pk for scenario in arcade.ready_scenarios()}
    return [n for n in NarrativeChallenge.objects.select_related("scenario") if n.scenario_id in ready and n.sets]


def run_room(run):
    return GameRoom.objects.filter(arcade_run_id=run.arcade_run_id, host=run.user).first() if run.arcade_run_id else None


@challenge_access
def challenge_home(request):
    run = challenge.current(request.user)
    if not run:
        return render(request, "weiss/challenge.html", {"scenarios": arcade.ready_scenarios(), "narratives": narratives(),
                                                        "start_packs": challenge.START_PACKS, "win_packs": challenge.WIN_PACKS})
    deck_total = sum(run.deck.entries.values_list("quantity", flat=True)) if run.deck else 0
    names = {entry["id"]: entry["name"] for entry in packs.pack_sets()}
    return render(request, "weiss/challenge.html", {
        "run": run, "sets": challenge.allowed_sets(run), "deck_total": deck_total, "deck_size": DECK_SIZE, **reward_context(run),
        "pulled": sum(run.pool.values()), "arcade_run": run.arcade_run, "room": run_room(run), "win_packs": challenge.WIN_PACKS,
        "lineup": arcade.lineup(run.scenario, request.user) if run.scenario else [],
        "set_names": [names.get(pk, f"Set {pk}") for pk in run.sets],
    })


def reward_context(run):
    """The rewards waiting to be claimed, and what each kind of claim chooses from."""
    rewards = [{**reward, "buff": buffs.BUFFS[reward["buff"]]} for reward in run.rewards if reward["buff"] in buffs.BUFFS]
    kinds = {reward["buff"].claim for reward in rewards}
    context = {"rewards": rewards, "levels": buffs.LEVELS, "colors": buffs.COLORS, "trade_in": buffs.TRADE_IN}
    if kinds & {"exchange", "trade_in"}:
        context["pool"] = [(card, pulled) for card, pulled, _ in challenge.pool_cards(run)]
    if "deck_card" in kinds and run.deck:
        context["deck_cards"] = [entry.card for entry in run.deck.entries.select_related("card").order_by("card__level", "card__name")]
    if "climax" in kinds:
        context["climaxes"] = buffs.climax_choices(run)
    if "pack" in kinds:
        context["all_sets"] = packs.pack_sets()
    return context


@challenge_access
@require_POST
def challenge_claim(request):
    """Claim a reward with what the player chose. A pack is then shown being opened."""
    run = challenge.current(request.user)
    if not run:
        return redirect("weiss:arcade_challenge")
    try:
        with transaction.atomic():
            run = ChallengeRun.objects.select_for_update().get(pk=run.pk)
            opened = buffs.claim(run, request.POST.get("key", ""), request.POST)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("weiss:arcade_challenge")
    if opened:
        return redirect("weiss:arcade_challenge_opened")
    messages.success(request, "Claimed. Your pool's changed: have a look at your deck.")
    return redirect("weiss:arcade_challenge")


@challenge_access
def challenge_exchange(request):
    """An exchange's second step: what the chosen card can be swapped for."""
    run = challenge.current(request.user)
    reward = run and buffs.reward_of(run, request.GET.get("key", ""))
    card = Card.objects.filter(pk=buffs.number(request.GET, "give")).first()
    if not reward or not card or str(card.pk) not in run.pool:
        messages.error(request, "Choose a card from your pool to swap.")
        return redirect("weiss:arcade_challenge")
    choices = buffs.exchange_choices(card)
    for choice in [card, *choices]:
        choice.image_src = reverse("weiss:card_image", args=[choice.pk])
    return render(request, "weiss/challenge_exchange.html", {"run": run, "reward": reward, "card": card, "choices": choices,
                                                             "rarity": packs.rarity_of(card)})


@challenge_access
@require_POST
def challenge_start(request):
    if challenge.current(request.user):
        messages.error(request, "Finish your challenge first, or reset it.")
        return redirect("weiss:arcade_challenge")
    if request.POST.get("kind") == ChallengeRun.Kind.NARRATIVE:
        narrative = next((n for n in narratives() if str(n.pk) == request.POST.get("narrative")), None)
        if not narrative:
            messages.error(request, "That challenge isn't available right now.")
            return redirect("weiss:arcade_challenge")
        challenge.start(request.user, ChallengeRun.Kind.NARRATIVE, narrative.scenario, narrative)
    else:
        scenario = next((s for s in arcade.ready_scenarios() if str(s.pk) == request.POST.get("scenario")), None)
        if not scenario:
            messages.error(request, "That arcade list isn't available right now.")
            return redirect("weiss:arcade_challenge")
        challenge.start(request.user, ChallengeRun.Kind.FREE, scenario)
    return redirect("weiss:arcade_challenge")


@challenge_access
@require_POST
def challenge_open(request):
    """Open packs into the pool, then watch them being opened."""
    run = challenge.current(request.user)
    if not run:
        return redirect("weiss:arcade_challenge")
    try:
        with transaction.atomic():
            run = ChallengeRun.objects.select_for_update().get(pk=run.pk)
            challenge.open_packs(run, int(request.POST.get("set", "0")), int(request.POST.get("count", "1")))
    except ValueError as error:
        messages.error(request, str(error) if str(error)[:1].isupper() else "Choose a set and how many packs.")
        return redirect("weiss:arcade_challenge")
    return redirect("weiss:arcade_challenge_opened")


@challenge_access
def challenge_opened(request):
    """The packs just opened, revealed as booster packs are; they're in the pool already, so reloading only replays them."""
    run = challenge.current(request.user)
    if not run or not run.last_opening:
        return redirect("weiss:arcade_challenge")
    opening = run.last_opening
    return render(request, "weiss/pack_open.html", {
        "set_id": opening["set_id"], "set_name": opening["set"], "count": len(opening["packs"]), "pack_size": packs.PACK_SIZE,
        "opening": opening, "back_url": reverse("weiss:arcade_challenge"), "back_label": f"{run.name} challenge",
        "actions": [("Build your deck", reverse("weiss:arcade_challenge_deck"), True),
                    ("Back to the challenge", reverse("weiss:arcade_challenge"), False)],
    })


@challenge_access
def challenge_deck(request):
    """Build the deck from the cards pulled. The page edits it in place and posts the whole deck to save it."""
    run = challenge.current(request.user)
    if not run or not run.deck:
        return redirect("weiss:arcade_challenge")
    if request.method == "POST":
        try:
            copies = json.loads(request.POST.get("deck", "{}"))
            problem = challenge.save_deck(run, copies) if isinstance(copies, dict) else "That isn't a deck."
        except (ValueError, TypeError):
            problem = "That isn't a deck."
        if problem:
            messages.error(request, problem)
        else:
            messages.success(request, "Deck saved.")
        return redirect("weiss:arcade_challenge_deck")
    cards = []
    for card, pulled, in_deck in challenge.pool_cards(run):
        card.image_src = reverse("weiss:card_image", args=[card.pk])
        cards.append({"card": card, "pulled": pulled, "in_deck": in_deck})
    climaxes = next(target for _, target, required, _ in DECK_GROUPS if required)
    return render(request, "weiss/challenge_deck.html", {"run": run, "cards": cards, "deck_size": DECK_SIZE, "climax_target": climaxes})


@challenge_access
@require_POST
def challenge_fight(request):
    """On to the run's next fight: the one it stopped at, or its first. The deck goes in as it is now."""
    run = challenge.current(request.user)
    if not run or run.status != ChallengeRun.Status.ACTIVE:
        return redirect("weiss:arcade_challenge")
    if not run.deck or not run.deck.entries.exists():
        messages.error(request, "Your deck is empty: open some packs and build it first.")
        return redirect("weiss:arcade_challenge")
    room = run_room(run)
    if room:
        with transaction.atomic():
            room = GameRoom.objects.select_for_update().select_related("arcade_run").get(pk=room.pk)
            over = room.state.get("game_over")
            if not over and not_begun(room):
                # Set up but not begun (say, a scene before it gave buffs): dealt again, with the deck as it is now.
                queued = room.state.get("scenes")
                room.state = {}
                deal(room, intro=not challenge.narrative(room.arcade_run))
                if queued:
                    room.state["scenes"] = queued
                room.version += 1
                room.save()
            elif over and not room.state.get("scenes") and room.arcade_run and room.arcade_run.status == ArcadeRun.Status.ACTIVE:
                # Between fights: on to the next one, or the same one again after a second chance.
                won = over["winner"] == str(room.host_id)
                profile = arcade.current_cpu(room.arcade_run)
                if profile:
                    seat_cpu(room, profile, arcade.scenes_before(room.arcade_run, profile) if won else ())
                    room.version += 1
                    room.save()
        return redirect("weiss:play_room", pk=room.pk)
    if GameRoom.objects.filter(host=request.user).count() >= GameRoom.MAX_OPEN_ROOMS:
        messages.error(request, f"You already host {GameRoom.MAX_OPEN_ROOMS} rooms; delete an old one first.")
        return redirect("weiss:arcade_challenge")
    scenario = run.scenario and ArcadeScenario.objects.prefetch_related("entries__cpu").filter(pk=run.scenario_id).first()
    if not scenario or arcade.scenario_problem(scenario):
        messages.error(request, "This challenge's arcade list isn't available right now.")
        return redirect("weiss:arcade_challenge")
    with transaction.atomic():
        if not run.arcade_run or run.arcade_run.status != ArcadeRun.Status.ACTIVE:
            run.arcade_run = ArcadeRun.objects.create(user=request.user, scenario=scenario, scenario_name=scenario.name, deck_name=run.deck.name,
                                                      order=arcade.fight_order(scenario, fixed=run.kind == ChallengeRun.Kind.NARRATIVE))
            run.save(update_fields=["arcade_run"])
        profile = arcade.current_cpu(run.arcade_run)
        if not profile:
            messages.error(request, "This challenge's arcade list has no one left to fight.")
            return redirect("weiss:arcade_challenge")
        room = GameRoom(host=request.user, host_deck=run.deck, arcade_run=run.arcade_run, status=GameRoom.Status.PLAYING)
        seat_cpu(room, profile, arcade.scenes_before(run.arcade_run, profile))
        room.save()
    return redirect("weiss:play_room", pk=room.pk)


@challenge_access
@require_POST
def challenge_reset(request):
    run = challenge.current(request.user)
    if run:
        challenge.reset(run)
        messages.success(request, f"{run.name} starts again: {challenge.START_PACKS} new packs, and a new deck.")
    return redirect("weiss:arcade_challenge")


@challenge_access
@require_POST
def challenge_end(request):
    """Give up a challenge in progress; the deck can still be kept."""
    run = challenge.current(request.user)
    if run and run.status == ChallengeRun.Status.ACTIVE:
        challenge.give_up(run)
    return redirect("weiss:arcade_challenge")


@challenge_access
@require_POST
def challenge_close(request):
    """Keep the deck, under a name, or discard it: the challenge is over either way."""
    run = challenge.current(request.user)
    if not run:
        return redirect("weiss:arcade_challenge")
    if run.status == ChallengeRun.Status.ACTIVE:
        messages.error(request, "The challenge is still going: end it first.")
        return redirect("weiss:arcade_challenge")
    keep = request.POST.get("keep") == "on"
    problem = challenge.close(run, keep, request.POST.get("name", ""))
    if problem:
        messages.error(request, problem)
        return redirect("weiss:arcade_challenge")
    if keep:
        messages.success(request, "The deck is in your lists now.")
        return redirect("weiss:lists")
    messages.success(request, "The challenge deck is gone.")
    return redirect("weiss:arcade_challenge")
