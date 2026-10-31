"""Game rooms: create a table, invite an opponent by link, pick decks, and play.

The board page polls `room_state` every second or two; it answers 204 when nothing has changed
(one cheap query) and the full board from this player's seat when something has. Moves go to
`room_action` as JSON and are applied under a row lock, so both players' moves land in order.
"""
import json

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import has_weiss_access, weiss_access_required

from . import game
from .models import Card, CardList, GameRoom


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
            "type": card.card_type, "rarity": card.rarity, "color": card.color, "level": card.level,
            "cost": card.cost, "power": card.power, "soul": card.soul, "trigger": card.trigger,
            "traits": card.traits, "text": card.description,
        }
    return info


def board_payload(room, user, extra=None):
    board = game.view(room.state, user.pk)
    pks = game.visible_cards(board)
    if extra and "revealed" in extra:
        pks.update(c["card"] for c in extra["revealed"]["cards"])
    return {"version": room.version, "status": room.status, "board": board, "cards": card_info(pks), **(extra or {})}


@weiss_access_required
def room_list(request):
    rooms = (GameRoom.objects.filter(host=request.user) | GameRoom.objects.filter(guest=request.user)) \
        .select_related("host", "guest").distinct()
    return render(request, "weiss/play_list.html", {"rooms": rooms})


@weiss_access_required
@require_POST
def room_create(request):
    if GameRoom.objects.filter(host=request.user).count() >= GameRoom.MAX_OPEN_ROOMS:
        messages.error(request, f"You already host {GameRoom.MAX_OPEN_ROOMS} rooms; delete an old one first.")
        return redirect("weiss:play_rooms")
    room = GameRoom.objects.create(host=request.user)
    return redirect("weiss:play_room", pk=room.pk)


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
    seat = room.seat_of(request.user)
    return render(request, "weiss/play_room.html", {
        "room": room,
        "seat": seat,
        "opponent": room.opponent_of(request.user),
        "invite_url": request.build_absolute_uri(reverse("weiss:play_join", args=[room.invite_token])),
        "my_deck": room.host_deck if seat == "host" else room.guest_deck,
        "decks": CardList.objects.filter(user=request.user),
    })


@weiss_access_required
@require_POST
def room_deck(request, pk):
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    deck = get_object_or_404(CardList, pk=request.POST.get("deck"), user=request.user)
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


def deal(room):
    """A new game with both decks as they are now. Game 1 starts with rock, paper, scissors for who
    goes first; each game after that keeps the series' tally, and the first turn alternates."""
    old = room.state or {}
    series = {"rps": True}
    if old:
        went_first = old.get("first_player", str(room.host_id))
        series = {"match_wins": old.get("match_wins"), "game_number": old.get("game_number", 1) + 1,
                  "first": room.guest_id if went_first == str(room.host_id) else room.host_id}
    room.state = game.new_game([
        (room.host_id, room.host.username, deck_cards(room.host_deck)),
        (room.guest_id, room.guest.username, deck_cards(room.guest_deck)),
    ], **series)


@weiss_access_required
@require_POST
def room_start(request, pk):
    """Shuffle both decks (copied as they are now) and deal game 1 of a new set. The host starts the
    first set; either player can start a new one once one is going, which clears the tally."""
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
    with transaction.atomic():
        room = GameRoom.objects.select_for_update().select_related("host", "guest").get(pk=room.pk)
        if room.status != GameRoom.Status.PLAYING and room.seat_of(request.user) != "host":
            return HttpResponseForbidden("Only the host can start the game.")
        if not (room.guest and room.host_deck and room.guest_deck):
            messages.error(request, "Both players need to choose a deck first.")
            return redirect("weiss:play_room", pk=room.pk)
        room.state = {}
        deal(room)
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
    room.delete()
    messages.success(request, "Room deleted.")
    return redirect("weiss:play_rooms")


@weiss_access_required
def room_state(request, pk):
    """Polled by the page: 204 if nothing changed since ?v=, else the board (or just the status in setup)."""
    room = my_room(request, pk)
    if not room:
        return HttpResponseForbidden()
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

    def name(card_pk):
        return lookup(card_pk)["name"]

    def is_climax(card_pk):
        return lookup(card_pk)["card_type"].lower() == "climax"

    with transaction.atomic():
        room = GameRoom.objects.select_for_update().get(pk=room.pk)
        if room.status != GameRoom.Status.PLAYING:
            return JsonResponse({"error": "The game hasn't started."}, status=409)
        if action.get("type") == "end_match":
            # From the victory or defeat screen, either player: back to choosing decks.
            if not room.state.get("game_over"):
                return JsonResponse({"error": "The game isn't over.", **board_payload(room, request.user)}, status=400)
            room.status, room.state = GameRoom.Status.SETUP, {}
            room.version += 1
            room.save()
            return JsonResponse({"version": room.version, "status": room.status})
        was_over = bool(room.state.get("game_over"))
        load(game.card_pks(room.state))  # abilities look through every card in play, so get them all at once
        try:
            extra = game.apply(room.state, request.user.pk, action, name=name, is_climax=is_climax,
                               trigger=lambda card_pk: lookup(card_pk)["trigger"],
                               cost=lambda card_pk: lookup(card_pk).get("cost"), info=lookup)
        except game.GameError as exc:
            return JsonResponse({"error": str(exc), **board_payload(room, request.user)}, status=400)
        over = room.state.get("game_over")
        if over and not was_over:  # counted once: this is the action that ended the game
            deck_id = room.host_deck_id if over["winner"] == str(room.host_id) else room.guest_deck_id
            CardList.objects.filter(pk=deck_id).update(wins=F("wins") + 1)
        if game.rematch_agreed(room.state):
            if room.host_deck and room.guest_deck:
                deal(room)
            else:  # a deck was deleted during the game
                over["rematch"] = []
                extra = {"error": "A deck has been deleted, so there can't be a rematch."}
        room.version += 1
        room.save(update_fields=["state", "version", "updated"])
    return JsonResponse(board_payload(room, request.user, extra))
