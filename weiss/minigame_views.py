"""Minigame prototypes (docs/minigames-plan.md): a staff page to try the four games against a CPU, and the JSON the games
play from. Nothing here touches a save."""
import json
import random
from collections import Counter
from functools import cache
from pathlib import Path

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

from . import packs, world
from .cpu_views import staff_required
from .lists import is_climax
from .models import Card, CardListEntry, CpuProfile

GAMES = {"memory": "Memory", "cups": "Three cups", "invaders": "Climax Invaders", "higher_lower": "Higher or Lower", "runner": "Runner"}
DIFFICULTIES = ("easy", "normal", "hard")
MOMENTS = ("start", "player_good", "player_bad", "cpu_good", "cpu_bad", "player_ahead", "cpu_ahead", "win", "lose")
WORLD_MOMENTS = ("invite", "start", "win", "lose", "again")  # the world game's (lines under each CPU's "world")
LINES_FILE = Path(__file__).resolve().parent.parent / "world_pack" / "minigame_lines.json"  # built by world_pack/build.py
MIN_PICTURED = 16  # a set needs this many pictured cards to play from (memory's 8 pairs, and a mix of levels)
CHARACTER_TARGET = 32  # cards per game: characters first, split across levels 0 to 3
CLIMAX_TARGET = 8


@cache
def pack_lines():
    """MINIGAME_LINES as world_pack/build.py wrote them ({cpu name or "*": {game or "*": {moment: [lines]}}}), or {}."""
    if not LINES_FILE.exists():
        return {}
    return json.loads(LINES_FILE.read_text(encoding="utf-8"))


def lines_for(cpu_name, game, player_name, moments=MOMENTS):
    """Every moment's lines for this CPU and game: the CPU's own for the game, then its own for any game, then the "*"
    ones for the game, then for any game. The first layer with lines for a moment wins."""
    data = pack_lines()
    own, generic = data.get(cpu_name, {}), data.get("*", {})
    layers = [own.get(game), own.get("*"), generic.get(game), generic.get("*")]
    return {moment: [line.replace("{player}", player_name) for line in next((found[moment] for found in layers if found and found.get(moment)), [])]
            for moment in moments}


def pictured(queryset):
    return queryset.filter(~Q(image_url="") | ~Q(image_s3_key=""))


def usable_sets():
    """expansion_id -> its pictured cards, for every set with enough of them to play from."""
    by_set = {}
    for card in pictured(Card.objects.filter(expansion_id__isnull=False)).only("pk", "expansion_id"):
        by_set.setdefault(card.expansion_id, 0)
        by_set[card.expansion_id] += 1
    return {set_id: count for set_id, count in by_set.items() if count >= MIN_PICTURED}


def game_set(cpu, rng=random):
    """The set a CPU's game uses: its deck's most common set when that has enough pictures, else a random one that does."""
    usable = usable_sets()
    if cpu.deck_id:
        deck_sets = Counter()
        for entry in CardListEntry.objects.filter(card_list_id=cpu.deck_id).select_related("card"):
            if entry.card.expansion_id is not None:
                deck_sets[entry.card.expansion_id] += entry.quantity
        for set_id, _ in deck_sets.most_common():
            if set_id in usable:
                return set_id
    return rng.choice(sorted(usable)) if usable else None


def game_cards(set_id, rng=random):
    """About CHARACTER_TARGET pictured characters spread over levels 0 to 3, and some climaxes, from one set."""
    cards = list(pictured(Card.objects.filter(expansion_id=set_id)))
    climaxes = [card for card in cards if is_climax(card)]
    characters = [card for card in cards if not is_climax(card)]
    chosen = []
    per_level = CHARACTER_TARGET // 4
    for level in range(4):
        pool = [card for card in characters if card.level == level]
        chosen += rng.sample(pool, min(per_level, len(pool)))
    leftover = [card for card in characters if card not in chosen]
    chosen += rng.sample(leftover, min(CHARACTER_TARGET - len(chosen), len(leftover)))
    chosen += rng.sample(climaxes, min(CLIMAX_TARGET, len(climaxes)))
    return chosen


def card_json(card):
    return {"id": card.pk, "name": card.name, "image": reverse("weiss:card_image", args=[card.pk]), "level": card.level,
            "power": card.power, "cost": card.cost, "color": card.color, "type": card.card_type, "trigger": card.trigger,
            "rarity": packs.rarity_of(card)}


@staff_required
def world_minigames(request):
    cpus = CpuProfile.objects.filter(finalized=True).order_by("name")
    return render(request, "weiss/minigames.html", {
        "games": GAMES.items(), "difficulties": DIFFICULTIES, "cpus": cpus,
        "data_url": reverse("weiss:world_minigame_data"),
    })


@staff_required
@require_GET
def world_minigame_data(request):
    game = request.GET.get("game", "")
    difficulty = request.GET.get("difficulty", "normal")
    if game not in GAMES:
        return JsonResponse({"error": "There's no minigame called that."}, status=400)
    if difficulty not in DIFFICULTIES:
        return JsonResponse({"error": "Choose easy, normal or hard."}, status=400)
    cpu = CpuProfile.objects.filter(pk=request.GET.get("cpu", ""), finalized=True).first()
    if not cpu:
        return JsonResponse({"error": "There's no CPU like that."}, status=404)
    data = game_data(game, cpu, difficulty, request.user.username)
    if data is None:
        return JsonResponse({"error": "No set has enough pictured cards to play from yet."}, status=400)
    return JsonResponse(data)


def game_data(game, cpu, difficulty, player_name, seed=None):
    """What a minigame plays from, against this CPU: its cards (from one set) and its lines. None if no set can play."""
    rng = random.Random(seed) if seed is not None else random
    set_id = game_set(cpu, rng)
    if set_id is None:
        return None
    return {
        "game": game, "difficulty": difficulty,
        "cpu": {"id": cpu.pk, "name": cpu.name, "portraits": world.cpu_portraits(cpu), "avatar": cpu.avatar["image"] if cpu.avatar else None},
        "cards": [card_json(card) for card in game_cards(set_id, rng)],
        "lines": lines_for(cpu.name, game, player_name),
    }
