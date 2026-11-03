"""Game rooms: create a table, invite an opponent by link, pick decks, and play.

The board page polls `room_state` every second or two; it answers 204 when nothing has changed
(one cheap query) and the full board from this player's seat when something has. Moves go to
`room_action` as JSON and are applied under a row lock, so both players' moves land in order.
"""
import json
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from core import s3
from core.access import has_weiss_access, weiss_access_required

from . import arcade, buffs, challenge, cpu, game, lists, packs, scenes, scoring
from .models import ArcadeRun, ArcadeScenario, Card, CardList, ChallengeRun, CpuProfile, GameRecord, GameRoom, PlayerProfile, cpu_user

log = logging.getLogger(__name__)


def my_room(request, pk):
    """The room, if the current user has a seat in it."""
    room = get_object_or_404(GameRoom.objects.select_related("host", "guest"), pk=pk)
    if not room.seat_of(request.user):
        return None
    return room


def card_info(pks):
    """What the board needs to show each card face up."""
    info = {}
    for card in Card.objects.filter(pk__in=pks).prefetch_related("prices"):
        info[str(card.pk)] = {
            "name": card.name, "serial": card.serial_number, "image": reverse("weiss:card_image", args=[card.pk]),
            "type": card.card_type, "rarity": card.rarity, "grade": packs.grade_of(packs.rarity_of(card)), "color": card.color, "level": card.level,
            "cost": card.cost, "power": card.power, "soul": card.soul, "trigger": card.trigger,
            "traits": card.traits, "text": card.description,
        }
    return info


def room_avatars(room):
    """{player name: picture} for those with one. The game's log only knows players by name, so that's the
    key; if both have the same name, there'd be no telling them apart, so they keep their names."""
    players = room.state.get("players", {})
    names = [side["name"] for side in players.values()]
    if len(set(names)) < len(names):
        return {}
    owners = {str(p.user_id): p for p in PlayerProfile.objects.filter(user_id__in=[room.host_id, room.guest_id], avatar_card__isnull=False)}
    if room.cpu_profile_id and room.cpu_profile and room.cpu_profile.avatar_card_id:
        owners[str(room.guest_id)] = room.cpu_profile
    return {players[pk]["name"]: owner.avatar for pk, owner in owners.items() if pk in players}


def cpu_payload(room):
    """What a game against a CPU adds: its screens, and where an arcade run has got to."""
    if not room.vs_cpu:
        return {}
    payload = {}
    if room.state.get("cpu_intro"):
        payload["intro"] = True
    profile = room.cpu_profile
    if profile:
        # In a narrative challenge the scenes say what the CPUs have to say, so their own lines are left out.
        said = not challenge.narrative(room.arcade_run)
        payload["cpu"] = {"name": profile.name, "image": profile.image_url, "images": {screen: profile.screen_url(screen) for screen in ("intro", "win", "lose")},
                          "picture": profile.avatar, "intro": profile.intro_text if said else "",
                          "win": profile.player_win_text if said else "", "lose": profile.player_lose_text if said else ""}
    else:  # it was deleted during the game
        payload["cpu"] = {"name": room.cpu_name, "image": "", "images": {}, "picture": None, "intro": "", "win": "", "lose": ""}
    run = room.arcade_run
    if run:
        endless = challenge.infinite(run)
        payload["arcade"] = {"scenario": run.scenario_name, "fight": run.position + 1 if endless else min(run.position + 1, run.total),
                             "total": None if endless else run.total,
                             "cleared": run.status == ArcadeRun.Status.CLEARED, "score": run.score}
        trial = ChallengeRun.objects.filter(arcade_run=run).only("kind", "packs", "lives", "status", "rewards").first()
        if trial:
            payload["arcade"]["challenge"] = {"packs": trial.packs, "won": challenge.win_reward_text(trial.kind), "lives": trial.lives,
                                              "going": trial.status == ChallengeRun.Status.ACTIVE, "rewards": len(trial.rewards)}
    return payload


def board_payload(room, user, extra=None):
    board = game.view(room.state, user.pk)
    pks = game.visible_cards(board)
    if extra and "revealed" in extra:
        pks.update(c["card"] for c in extra["revealed"]["cards"])
    scene = {"scene": room.state["scenes"][0], "player_name": user.username} if room.state.get("scenes") else {}
    return {"version": room.version, "status": room.status, "board": board, "cards": card_info(pks),
            "avatars": room_avatars(room), **cpu_payload(room), **scene, **(extra or {})}


ARCADE_EDITING = "arcade_editing"  # session: the room of a run whose player has gone to change their deck


def paused_run(request):
    """The arcade room this player left between fights to change their deck, while that's still so; else None."""
    pk = request.session.get(ARCADE_EDITING)
    if not pk:
        return None
    room = GameRoom.objects.filter(pk=pk, host=request.user).select_related("arcade_run", "host_deck").first()
    run = room and room.arcade_run
    if not run or run.status != ArcadeRun.Status.ACTIVE or not room.state.get("game_over"):
        request.session.pop(ARCADE_EDITING, None)
        return None
    return room


@weiss_access_required
def room_list(request):
    rooms = (GameRoom.objects.filter(host=request.user) | GameRoom.objects.filter(guest=request.user)) \
        .select_related("host", "guest", "arcade_run").distinct()
    return render(request, "weiss/play_list.html", {
        "rooms": rooms,
        "cpus": CpuProfile.objects.filter(finalized=True, deck__isnull=False),
        "decks": CardList.objects.players(request.user),
    })


@weiss_access_required
def arcade_home(request):
    """The Arcade tab: each scenario with the CPUs this player has met in it, and a run to start."""
    scenarios = arcade.ready_scenarios()
    clears = {}
    for run in ArcadeRun.objects.filter(user=request.user, status=ArcadeRun.Status.CLEARED):
        clears[run.scenario_id] = clears.get(run.scenario_id, 0) + 1
    best = {}
    for run in ArcadeRun.objects.filter(user=request.user, score__gt=0).only("scenario_id", "score"):
        best[run.scenario_id] = max(best.get(run.scenario_id, 0), run.score)
    for scenario in scenarios:
        scenario.lineup = arcade.lineup(scenario, request.user)
        scenario.clears = clears.get(scenario.pk, 0)
        scenario.my_best = best.get(scenario.pk, 0)
    return render(request, "weiss/arcade.html", {
        "scenarios": scenarios,
        "decks": CardList.objects.players(request.user),
    })


@weiss_access_required
def arcade_scores(request):
    """The Arcade tab's high scores: each scenario's best run, and who played it."""
    return render(request, "weiss/arcade_scores.html", {"scenarios": arcade.high_scores(arcade.all_scenarios()),
                                                       "weights": [(scoring.LABELS[key], weight) for key, weight in scoring.WEIGHTS.items()]})


@weiss_access_required
@require_POST
def room_create(request):
    if GameRoom.objects.filter(host=request.user).count() >= GameRoom.MAX_OPEN_ROOMS:
        messages.error(request, f"You already host {GameRoom.MAX_OPEN_ROOMS} rooms; delete an old one first.")
        return redirect("weiss:play_rooms")
    room = GameRoom.objects.create(host=request.user)
    return redirect("weiss:play_room", pk=room.pk)


@weiss_access_required
@require_POST
def room_vs_cpu(request):
    """Challenge a CPU: a room with it in the other seat, and the game under way."""
    if GameRoom.objects.filter(host=request.user).count() >= GameRoom.MAX_OPEN_ROOMS:
        messages.error(request, f"You already host {GameRoom.MAX_OPEN_ROOMS} rooms; delete an old one first.")
        return redirect("weiss:play_rooms")
    profile = get_object_or_404(CpuProfile, pk=request.POST.get("cpu"), finalized=True, deck__isnull=False)
    deck = get_object_or_404(CardList.objects.players(request.user), pk=request.POST.get("deck"))
    if not deck.entries.exists():
        messages.error(request, f"“{deck.name}” is empty; add some cards first.")
        return redirect("weiss:play_rooms")
    room = GameRoom(host=request.user, host_deck=deck, status=GameRoom.Status.PLAYING)
    seat_cpu(room, profile)
    room.save()
    return redirect("weiss:play_room", pk=room.pk)


def seat_cpu(room, profile, scenes=()):
    """This CPU in the other seat, and a new match against it, starting on its screen, after any scenes
    (payloads from weiss.scenes) the board has to play first. A narrative challenge's fights skip the CPU's
    screen: its scenes have introduced them."""
    room.guest, room.guest_deck, room.cpu_name, room.cpu_profile = cpu_user(), profile.deck, profile.name, profile
    room.state = {}
    deal(room, intro=not challenge.narrative(room.arcade_run))
    if scenes:
        room.state["scenes"] = list(scenes)


def not_begun(room):
    """Whether a fight is still to start: on the CPU's screen, or not yet past the player's first mulligan."""
    state = room.state
    return bool(state.get("cpu_intro") or (state.get("phase") == "mulligan" and state.get("game_number", 1) == 1
                                           and str(room.host_id) not in state.get("mulligan_done", [])))


def choose_fight(room, cpu_id):
    """A scene picked who to fight next (scenes.chosen_fight): the next fight of the run that hasn't begun becomes
    that CPU's, if it's in the run's arcade list and ready. A fight about to start changes there and then, the new
    CPU in the seat; otherwise it's the one after. If that CPU was due later in the run, the two swap places."""
    run = room.arcade_run
    cpu = CpuProfile.objects.filter(pk=cpu_id).first()
    if not run or run.status != ArcadeRun.Status.ACTIVE or not arcade.can_fight(cpu) or not arcade.entry_of(run, cpu.pk):
        return
    over = room.state.get("game_over")
    now = not over and not_begun(room)
    at = run.position if now or over else run.position + 1  # after a win the run has already moved on
    if at >= len(run.order):
        return
    later = run.order.index(cpu.pk, at + 1) if cpu.pk in run.order[at + 1:] else None
    if later is not None:
        run.order[later] = run.order[at]
    run.order[at] = cpu.pk
    run.save(update_fields=["order"])
    if now and cpu.pk != room.cpu_profile_id:
        seat_cpu(room, cpu, arcade.scenes_before(run, cpu, opening=False))


@weiss_access_required
@require_POST
def arcade_start(request):
    """A new run: its order is settled now, and the first fight is under way."""
    if GameRoom.objects.filter(host=request.user).count() >= GameRoom.MAX_OPEN_ROOMS:
        messages.error(request, f"You already host {GameRoom.MAX_OPEN_ROOMS} rooms; delete an old one first.")
        return redirect("weiss:arcade")
    scenario = get_object_or_404(ArcadeScenario.objects.prefetch_related("entries__cpu"), pk=request.POST.get("scenario"))
    deck = get_object_or_404(CardList.objects.players(request.user), pk=request.POST.get("deck"))
    if arcade.scenario_problem(scenario):
        messages.error(request, f"{scenario.name} isn't available right now.")
        return redirect("weiss:arcade")
    if not deck.entries.exists():
        messages.error(request, f"“{deck.name}” is empty; add some cards first.")
        return redirect("weiss:arcade")
    with transaction.atomic():
        run = ArcadeRun.objects.create(user=request.user, scenario=scenario, scenario_name=scenario.name, deck_name=deck.name, order=arcade.fight_order(scenario))
        room = GameRoom(host=request.user, host_deck=deck, arcade_run=run, status=GameRoom.Status.PLAYING)
        profile = arcade.current_cpu(run)
        seat_cpu(room, profile, arcade.scenes_before(run, profile))
        room.save()
    return redirect("weiss:play_room", pk=room.pk)


@weiss_access_required
@require_POST
def arcade_quit(request, pk):
    """Stop a run from the side panel, partway through a fight."""
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().get(pk=room.pk)
        paused = leave_run(room)
    return redirect("weiss:arcade_challenge" if paused else "weiss:profile")


def leave_run(room):
    """Leave a run's room. A challenge's run only stops for now, to go on from this fight later: returns
    whether that's what happened."""
    paused = bool(room.arcade_run and ChallengeRun.objects.filter(arcade_run=room.arcade_run, finished__isnull=True).exists())
    if room.arcade_run and not paused:
        arcade.end_run(room.arcade_run)
    room.delete()
    return paused


def arcade_action(request, room, action):
    """The buttons on a run's end screen, on a locked room."""
    kind = action["type"]
    run = room.arcade_run
    if not run:
        return JsonResponse({"error": "This isn't an arcade run.", **board_payload(room, request.user)}, status=400)
    if kind in ("arcade_quit", "challenge_leave"):
        # A challenge's player goes back to its page: to open packs and change the deck, or to see how it ended.
        paused = leave_run(room)
        return JsonResponse({"redirect": reverse("weiss:arcade_challenge" if paused else "weiss:profile")})
    over = room.state.get("game_over")
    won = over and over["winner"] == str(room.host_id)
    if kind == "arcade_edit_deck":
        # Between fights: off to change the deck, with the side panel adding to it and a way back here.
        # The next fight deals the deck as it is then.
        if not over or run.status != ArcadeRun.Status.ACTIVE or not room.host_deck or room.host_deck.challenge:
            return JsonResponse({"error": "That isn't possible right now.", **board_payload(room, request.user)}, status=400)
        request.session[ARCADE_EDITING] = room.pk
        request.session[lists.SESSION_KEY] = room.host_deck_id
        return JsonResponse({"redirect": reverse("weiss:list", args=[room.host_deck_id])})
    if not over or run.status != ArcadeRun.Status.ACTIVE or (kind == "arcade_continue") != bool(won):
        return JsonResponse({"error": "That isn't possible right now.", **board_payload(room, request.user)}, status=400)
    profile = arcade.current_cpu(run)
    if not profile or not room.host_deck or not room.host_deck.entries.exists() or not profile.deck.entries.exists():
        messages.error(request, f"Your {run.scenario_name} run had to stop: its deck or CPU is no longer available.")
        leave_run(room)
        return JsonResponse({"redirect": reverse("weiss:play_rooms")})
    seat_cpu(room, profile, arcade.scenes_before(run, profile) if won else ())  # a retry doesn't play its scenes again
    room.version += 1
    room.save()
    return JsonResponse(board_payload(room, request.user))


@weiss_access_required
def cpu_image(request, pk):
    """A stable link to a CPU's uploaded image, redirecting to a fresh S3 link, as card images do."""
    profile = get_object_or_404(CpuProfile, pk=pk)
    image = profile.screen_image(request.GET.get("screen", "main"))
    if not image:
        raise Http404("This CPU has no image")
    response = redirect(s3.presigned_image_urls([image.key])[image.key])
    response["Cache-Control"] = f"private, max-age={settings.IMAGE_LINK_SECONDS - 300}"
    return response


def room_join(request, token):
    """The invite link. Anyone with Weiss access who opens it first takes the open seat."""
    room = get_object_or_404(GameRoom, invite_token=token)
    if not has_weiss_access(request.user):
        return redirect_to_login(request.get_full_path())
    if room.seat_of(request.user):
        return redirect("weiss:play_room", pk=room.pk)
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().get(pk=room.pk)
        if room.guest_id:
            return render(request, "weiss/play_full.html", {"room": room}, status=403)
        room.guest = request.user
        room.version += 1
        room.save(update_fields=["guest", "version", "updated"])
    return redirect("weiss:play_room", pk=room.pk)


@weiss_access_required
def room_detail(request, pk):
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden("This room is for its two players only.")
    if request.session.get(ARCADE_EDITING) == room.pk:  # back from changing the deck
        request.session.pop(ARCADE_EDITING)
    seat = room.seat_of(request.user)
    return render(request, "weiss/play_room.html", {
        "room": room,
        "seat": seat,
        "opponent": room.opponent_of(request.user),
        "opponent_name": room.guest_name if seat == "host" else room.host.username,
        "invite_url": request.build_absolute_uri(reverse("weiss:play_join", args=[room.invite_token])),
        "my_deck": room.host_deck if seat == "host" else room.guest_deck,
        "decks": CardList.objects.players(request.user),
    })


@weiss_access_required
@require_POST
def room_deck(request, pk):
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    if room.arcade_run_id:
        return not_for_a_run(request, room)
    deck = get_object_or_404(CardList.objects.players(request.user), pk=request.POST.get("deck"))
    if not deck.entries.exists():
        messages.error(request, f"“{deck.name}” is empty; add some cards first.")
        return redirect("weiss:play_room", pk=room.pk)
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().get(pk=room.pk)
        setattr(room, f"{room.seat_of(request.user)}_deck", deck)
        room.version += 1
        room.save()
    return redirect("weiss:play_room", pk=room.pk)


def deck_cards(card_list):
    return [entry.card_id for entry in card_list.entries.all() for _ in range(entry.quantity)]


def not_for_a_run(request, room):
    messages.error(request, "An arcade run keeps its deck and opponents. You can stop the run instead.")
    return redirect("weiss:play_room", pk=room.pk)


def deal(room, intro=False):
    """A new game with both decks as they are now. Game 1 starts with rock, paper, scissors for who
    goes first; each game after that keeps the series' tally, and the first turn alternates. With intro,
    the CPU's screen comes first, and neither side can act until the player has dismissed it."""
    old = room.state or {}
    series = {"rps": True}
    if old:
        went_first = old.get("first_player", str(room.host_id))
        series = {"match_wins": old.get("match_wins"), "game_number": old.get("game_number", 1) + 1,
                  "first": room.guest_id if went_first == str(room.host_id) else room.host_id}
    room.state = game.new_game([
        (room.host_id, room.host.username, deck_cards(room.host_deck)),
        (room.guest_id, room.guest_name, deck_cards(room.guest_deck)),
    ], **series)
    if intro:
        room.state["cpu_intro"] = True


@weiss_access_required
@require_POST
def room_start(request, pk):
    """Shuffle both decks (copied as they are now) and deal game 1 of a new set. The host starts the
    first set; either player can start a new one once one is going, which clears the tally."""
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    if room.arcade_run_id:
        return not_for_a_run(request, room)
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().select_related("host", "guest").get(pk=room.pk)
        if room.status != GameRoom.Status.PLAYING and room.seat_of(request.user) != "host":
            return HttpResponseForbidden("Only the host can start the game.")
        if not (room.guest and room.host_deck and room.guest_deck):
            messages.error(request, "Both players need to choose a deck first.")
            return redirect("weiss:play_room", pk=room.pk)
        room.state = {}
        deal(room, intro=room.vs_cpu)
        room.status = GameRoom.Status.PLAYING
        room.version += 1
        room.save()
    return redirect("weiss:play_room", pk=room.pk)


@weiss_access_required
@require_POST
def room_reset(request, pk):
    """Either player: back to choosing decks."""
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    if room.arcade_run_id:
        return not_for_a_run(request, room)
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().get(pk=room.pk)
        room.status, room.state = GameRoom.Status.SETUP, {}
        room.version += 1
        room.save()
    return redirect("weiss:play_room", pk=room.pk)


@weiss_access_required
@require_POST
def room_delete(request, pk):
    room = my_room(request, pk)
    if not room or room.seat_of(request.user) != "host":
        return HttpResponseForbidden()
    leave_run(room)
    messages.success(request, "Room deleted.")
    return redirect("weiss:play_rooms")


@weiss_access_required
def room_state(request, pk):
    """Polled by the page: 204 if nothing changed since ?v=, else the board (or just the status in setup)."""
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    if room.vs_cpu and room.status == GameRoom.Status.PLAYING:
        room = cpu_step(room)
    if request.GET.get("v") == str(room.version):
        return HttpResponse(status=204)
    if room.status != GameRoom.Status.PLAYING:
        return JsonResponse({"version": room.version, "status": room.status})
    return JsonResponse(board_payload(room, request.user))


@weiss_access_required
@require_POST
def room_action(request, pk):
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    try:
        action = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "Bad request."}, status=400)
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().get(pk=room.pk)
        if room.status != GameRoom.Status.PLAYING:
            return JsonResponse({"error": "The game hasn't started."}, status=409)
        kind = action.get("type")
        if room.state.get("scenes"):
            # A scene is being played: nothing else happens until it's over, and then the next one, if any.
            if kind != "scene_done":
                return JsonResponse({"error": "A scene is playing.", **board_payload(room, request.user)}, status=409)
            if action.get("key") != room.state["scenes"][0].get("key"):
                return JsonResponse(board_payload(room, request.user))
            scene = room.state["scenes"].pop(0)
            if not room.state["scenes"]:
                room.state.pop("scenes")
            fight = scenes.chosen_fight(scene, action.get("fights"))
            if fight:
                choose_fight(room, fight)
            room.version += 1
            room.save()
            # A challenge's scene can give buffs: they're the player's now, to claim on the challenge's page before
            # the next fight. What the page says was given is checked against the scene.
            trial = challenge.of(room.arcade_run)
            given = buffs.given(scene, action.get("buffs")) if trial else []
            if given:
                buffs.grant(trial, given, scene.get("title", ""))
                messages.success(request, "From “{}”: {}.".format(scene.get("title", "the scene"), ", ".join(buffs.BUFFS[b].name for b in given)))
                return JsonResponse({"redirect": reverse("weiss:arcade_challenge")})
            return JsonResponse(board_payload(room, request.user))
        if room.state.get("cpu_intro"):
            if kind != "intro_done":
                return JsonResponse({"error": "The match hasn't started yet.", **board_payload(room, request.user)}, status=409)
            room.state.pop("cpu_intro")
            room.version += 1
            room.save()
            return JsonResponse(board_payload(room, request.user))
        if kind in ("arcade_continue", "arcade_retry", "arcade_quit", "arcade_edit_deck", "challenge_leave"):
            return arcade_action(request, room, action)
        if room.arcade_run_id and kind in ("rematch", "end_match"):
            return JsonResponse({"error": "An arcade run goes on with Continue or Retry.", **board_payload(room, request.user)}, status=400)
        if action.get("type") == "end_match":
            # From the victory or defeat screen, either player: back to choosing decks.
            if not room.state.get("game_over"):
                return JsonResponse({"error": "The game isn't over.", **board_payload(room, request.user)}, status=400)
            room.status, room.state = GameRoom.Status.SETUP, {}
            room.version += 1
            room.save()
            return JsonResponse({"version": room.version, "status": room.status})
        try:
            extra = play_action(room, request.user.pk, action)
        except game.GameError as exc:
            return JsonResponse({"error": str(exc), **board_payload(room, request.user)}, status=400)
    return JsonResponse(board_payload(room, request.user, extra))


def card_lookups(state):
    """What game.apply needs to know about cards. Abilities look through every card in play, so
    they're all fetched at once."""
    details = {}

    def load(pks):
        for row in Card.objects.filter(pk__in=pks).values(
                "pk", "name", "card_type", "color", "trigger", "cost", "level", "power", "soul", "traits", "description"):
            row["text"] = row["description"] or ""
            details[row["pk"]] = row

    def lookup(card_pk):
        if card_pk not in details:
            load([card_pk])
            details.setdefault(card_pk, {"name": "a card", "card_type": "", "trigger": ""})
        return details[card_pk]

    load(game.card_pks(state))
    return {"name": lambda card_pk: lookup(card_pk)["name"],
            "is_climax": lambda card_pk: lookup(card_pk)["card_type"].lower() == "climax",
            "trigger": lambda card_pk: lookup(card_pk)["trigger"],
            "cost": lambda card_pk: lookup(card_pk).get("cost"), "info": lookup}


def record_game(room, over, score=None):
    players = room.state["players"]
    GameRecord.objects.create(score=score,
        host_id=room.host_id, guest_id=room.guest_id, host_name=players[str(room.host_id)]["name"], guest_name=players[str(room.guest_id)]["name"],
        host_deck_name=room.host_deck.name if room.host_deck else "", guest_deck_name=room.guest_deck.name if room.guest_deck else "",
        cpu=room.vs_cpu, cpu_profile=room.cpu_profile, winner="host" if over["winner"] == str(room.host_id) else "guest",
        reason=over.get("reason", ""), game_number=room.state.get("game_number", 1), turns=room.state.get("turn_number", 0))


def play_action(room, player, action, lookups=None):
    """One player's action on a locked room, and what follows from it: a win for a deck, a rematch
    dealt. Saves the room. Returns the extras for that player."""
    was_over = bool(room.state.get("game_over"))
    extra = game.apply(room.state, player, action, **(lookups or card_lookups(room.state)))
    over = room.state.get("game_over")
    if over and not was_over:  # counted once: this is the action that ended the game
        host_won = over["winner"] == str(room.host_id)
        deck_id = room.host_deck_id if host_won else room.guest_deck_id
        # The player's deck beating a CPU counts apart; a CPU's deck has beaten a human.
        field = "cpu_wins" if room.vs_cpu and host_won else "wins"
        CardList.objects.filter(pk=deck_id).update(**{field: F(field) + 1})
        score = None
        if room.vs_cpu and host_won:  # only a player's win against a CPU is scored
            over["score"] = scoring.win_score(room.state, room.host_id)
            score = over["score"]["total"]
        record_game(room, over, score)
        arcade.game_finished(room, over, score)
    if game.rematch_agreed(room.state):
        if room.host_deck and room.guest_deck:
            deal(room)
        else:  # a deck was deleted during the game
            over["rematch"] = []
            extra = {"error": "A deck has been deleted, so there can't be a rematch."}
    room.version += 1
    room.save(update_fields=["state", "version", "updated"])
    return extra


def cpu_step(room, wait=True):
    """Let the CPU in this room take its next action, if it has one and what happened last has had
    time to be seen. The player's page polling is what drives this. Returns the room as it now is."""
    if wait and timezone.now() - room.updated < timedelta(seconds=cpu.wait_seconds(room.state)):
        return room
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().select_related("host", "guest", "cpu_profile").get(pk=room.pk)
        if room.status != GameRoom.Status.PLAYING or room.state.get("cpu_intro") or room.state.get("scenes"):
            return room
        if wait and timezone.now() - room.updated < timedelta(seconds=cpu.wait_seconds(room.state)):
            return room  # the other poll got in first
        lookups = card_lookups(room.state)
        aggression = room.cpu_profile.aggression if room.cpu_profile else cpu.MIN_AGGRESSION
        model = room.cpu_profile.model if room.cpu_profile else "standard"
        if room.cpu_profile and challenge.infinite(room.arcade_run):  # harder as it goes, whatever the CPU
            model, aggression = challenge.infinite_style(room.arcade_run, room.cpu_profile)
        action = cpu.next_action(room.state, room.guest_id, lookups["info"], aggression, model=model)
        if not action:
            return room
        try:
            play_action(room, room.guest_id, action, lookups)
        except game.GameError as exc:  # it must never leave the player waiting: do something safe instead
            log.warning("CPU in room %s: %s refused: %s", room.pk, action, exc)
            fallback = cpu.fallback_action(room.state, room.guest_id)
            if fallback:
                try:
                    play_action(room, room.guest_id, fallback, lookups)
                except game.GameError as second:
                    log.warning("CPU in room %s: fallback %s refused: %s", room.pk, fallback, second)
    return room
