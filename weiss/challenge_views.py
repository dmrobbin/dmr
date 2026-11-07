"""Challenge mode's pages, on the Arcade tab: starting a challenge, opening its packs, building its deck from
them, fighting its run, and keeping or discarding the deck at the end. See weiss.challenge."""
import json
import random

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import weiss_access_required

from . import arcade, augments, buffs, challenge, coop, game, packs, play
from .lists import CLIMAX_COUNT, DECK_GROUPS, DECK_SIZE, unlimited
from .models import ArcadeRun, ArcadeScenario, Card, ChallengeRun, CoopRun, CpuProfile, GameRoom, NarrativeChallenge, PlayerProfile
from .play import deal, not_begun, seat_cpu, snapshot_groups


def challenge_access(view):
    """Every Weiss player's: what they can start is up to challenge.can_start."""
    return weiss_access_required(view)


def narratives():
    """The narrative challenges players can start: those whose arcade list is ready and that have sets."""
    ready = {scenario.pk for scenario in arcade.ready_scenarios()}
    return [n for n in NarrativeChallenge.objects.select_related("scenario") if n.scenario_id in ready and n.sets]


def run_room(run):
    return GameRoom.objects.filter(arcade_run_id=run.arcade_run_id, host=run.user).first() if run.arcade_run_id else None


def in_a_fight(run):
    """This run's game, while one is being played (not over yet), or None."""
    room = run and run_room(run)
    return room if room and room.status == GameRoom.Status.PLAYING and not room.state.get("game_over") else None


def watchable(run):
    """Whether this co-op player is waiting on their partner's game, which they can watch then (see coop_spectate)."""
    other = coop.partner_run(run)
    return bool(other and not in_a_fight(run) and in_a_fight(other))


def partner_room(run):
    """The game a co-op partner is in now (over or not, until they leave it), or None."""
    other = coop.partner_run(run)
    room = other and run_room(other)
    return room if room and room.status == GameRoom.Status.PLAYING else None


@challenge_access
def challenge_home(request):
    run = challenge.current(request.user)
    if not run:
        return render(request, "weiss/challenge.html", {"scenarios": arcade.ready_scenarios(), "narratives": narratives(),
                                                        "staff_kinds": challenge.can_start(request.user, ChallengeRun.Kind.FREE),
                                                        "coop_open": challenge.can_start(request.user, challenge.COOP),
                                                        "start_packs": challenge.START_PACKS, "narrative_packs": challenge.NARRATIVE_START_PACKS,
                                                        "infinite_packs": challenge.infinite_start_packs(), "infinite_extras": len(challenge.loadout()),
                                                        "coop_packs": coop.start_packs(), "coop_extras": len(coop.loadout()), "coop_losses": coop.loss_limit(),
                                                        "win_reward": challenge.win_reward_text(ChallengeRun.Kind.FREE),
                                                        "narrative_win_reward": challenge.win_reward_text(ChallengeRun.Kind.NARRATIVE),
                                                        "cpu_count": len(challenge.opponents())})
    deck_total = sum(run.deck.entries.values_list("quantity", flat=True)) if run.deck else 0
    names = {entry["id"]: entry["name"] for entry in packs.pack_sets()}
    return render(request, "weiss/challenge.html", {
        "run": run, "sets": challenge.allowed_sets(run), "deck_total": deck_total, "deck_size": DECK_SIZE, **reward_context(run),
        "deck_problem": challenge.deck_ready(run) if deck_total else None,
        "pulled": sum(run.pool.values()), "arcade_run": run.arcade_run, "room": run_room(run), "win_reward": challenge.win_reward_text(run.kind),
        "lineup": arcade.lineup(run.scenario, request.user) if run.scenario else [],
        "set_names": [names.get(pk, f"Set {pk}") for pk in run.sets],
        "path": path_view(run) if run.kind == ChallengeRun.Kind.INFINITE else None,
        "mods": [buffs.BUFFS[buff_id] for buff_id in buffs.fight_mods(run)],
        "event_due": bool((run.path or {}).get("event")),
        "last_set": last_set(run),
        "augments": augments.of(run),
        "coop": coop_context(request, run),
    })


def coop_context(request, run):
    """What a co-op challenge's page shows of the pair: the partner (or the invite link, until there's one) and the
    lost games so far."""
    if not run.coop_id:
        return None
    pair = run.coop
    partner = pair.partner_of(request.user)
    profile = partner and PlayerProfile.objects.filter(user=partner, avatar_card__isnull=False).first()
    mine = challenge.floor_at(run)
    theirs = coop.floor_of(run.path, partner.pk) if partner else mine
    boss = None
    if challenge.is_boss(run.path, mine):  # the boss this player is on (or, once it's down, the one just beaten)
        boss = challenge.boss_shown(run, mine)
    elif (last := (run.path or {}).get("boss")) and last.get("down") and last["floor"] == mine - 1:
        boss = challenge.boss_shown(run, last["floor"])
    if boss:
        boss["mine"] = boss.get("dealt", {}).get(str(run.user_id), 0)
        boss["theirs"] = boss.get("dealt", {}).get(str(partner.pk), 0) if partner else 0
    other = coop.partner_run(run) if partner else None
    return {"boss": boss, "watchable": watchable(run), "partner_augments": augments.of(other) if other else [], "run": pair, "partner": partner, "partner_avatar": profile and profile.avatar, "hosting": pair.host_id == request.user.pk,
            "limit_range": range(pair.loss_limit), "floor": mine + 1, "partner_floor": theirs + 1, "behind": theirs < mine, "ahead": theirs > mine,
            "decided": decided_said(run, partner), "status_url": reverse("weiss:arcade_coop_status"),
            "invite_url": request.build_absolute_uri(reverse("weiss:arcade_coop_join", args=[pair.invite_token]))
            if pair.status == CoopRun.Status.WAITING else None}


def last_set(run):
    """The set an infinite challenge last opened packs from, picked already in its set choices until another is."""
    return run.last_opening.get("set_id") if run.kind == ChallengeRun.Kind.INFINITE and run.last_opening else None


PATH_BEHIND = 2  # floors of an infinite challenge's path still shown once they're won


def path_view(run):
    """An infinite challenge's path for its page, from the bottom up: {"floors": [{"number", "tier", "current",
    "nodes": [{"cpu" (None for an event), "event", "node", "x", "y", "state"}]}], "lines": [{"x1", "y1", "x2", "y2", "state"}], "defeated":
    [CPU, ...]}. Positions are percentages of the map. A node's state is "won", "passed" (not taken), "open" (can
    be fought now), "picked" (chosen, its fight under way), "closed" (on this floor, out of reach), "reach" (ahead,
    on the way from here) or "ahead". A boss floor's floor and node have "boss"."""
    path = challenge.path_of(run)
    floors, picks = path["floors"], path["picks"]
    at = challenge.floor_at(run)
    cpus = CpuProfile.objects.in_bulk({pk for floor in floors for pk in floor if pk not in (None, challenge.EVENT)} | set(challenge.defeated(run)))
    defeated = [cpus.get(pk) for pk in challenge.defeated(run)]
    first, last = max(0, at - PATH_BEHIND), min(len(floors), at + 1 + challenge.PATH_AHEAD)
    shown = range(first, last)
    open_now = set(challenge.choices(path, at))
    reach = {at: open_now}  # the nodes of each floor ahead that can be got to from here
    for f in range(at + 1, last):
        led = challenge.links(floors[f - 1], floors[f])
        reach[f] = {j for i in reach[f - 1] for j in led[i]}

    def place(f, i):
        rows = len(shown)
        return round(challenge.column_x(i) * 100, 2), round((rows - (f - first) - .5) / rows * 100, 2)

    def state(f, i):
        if f < at:
            return "won" if picks[f] == i else "passed"
        if f == at:
            return ("picked" if at < len(picks) else "open") if i in open_now else "closed"
        return "reach" if i in reach[f] else "ahead"

    key = f"floor:{at}"  # in co-op, where the pair's votes on this floor are
    my_vote, their_vote = (coop.vote_of(run, key), coop.partner_vote(run, key)) if run.coop_id else (None, None)
    view_floors, lines = [], []
    for f in shown:
        nodes, boss = [], challenge.is_boss(path, f)
        for i, pk in enumerate(floors[f]):
            if pk is None:  # a gap in the path
                continue
            x, y = place(f, i)
            nodes.append({"cpu": cpus.get(pk), "event": pk == challenge.EVENT, "boss": boss, "node": i, "x": x, "y": y, "state": state(f, i),
                          "my_vote": f == at and my_vote == i, "their_vote": f == at and their_vote == i})
        view_floors.append({"number": f + 1, "tier": "Boss" if boss else challenge.tier(f), "boss": boss, "current": f == at, "nodes": nodes})
        if f + 1 < last:
            for i, led in enumerate(challenge.links(floors[f], floors[f + 1])):
                for j in led:
                    (x1, y1), (x2, y2) = place(f, i), place(f + 1, j)
                    taken = f + 1 < len(picks) and picks[f] == i and picks[f + 1] == j
                    onward = f + 1 >= at and j in reach[f + 1] and (i in reach[f] if f >= at else picks[f] == i)
                    lines.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "state": "taken" if taken else "onward" if onward else "faint"})
    shows_bosses = challenge.boss_every(coop=bool(run.coop_id)) or path.get("bosses")
    return {"floors": view_floors[::-1], "lines": lines, "defeated": defeated, "height": len(shown) * 9, "coop": bool(run.coop_id),
            "voting": bool(run.coop_id) and at >= len(picks) and len(open_now) > 1,
            "boss_reward": challenge.boss_reward_text(run) if shows_bosses else ""}


def reward_context(run):
    """The rewards waiting to be claimed, and what each kind of claim chooses from."""
    rewards = [{**reward, "buff": buffs.BUFFS[reward["buff"]],
                "augments": [augments.shown(a) for a in reward.get("options", []) if a in augments.AUGMENTS]}
               for reward in run.rewards if reward["buff"] in buffs.BUFFS]
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
    if not reward or not card or str(card.pk) not in coop.available(run):
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
    kind = request.POST.get("kind", ChallengeRun.Kind.FREE)
    if not challenge.can_start(request.user, kind):
        raise PermissionDenied
    if challenge.current(request.user):
        messages.error(request, "Finish your challenge first, or reset it.")
        return redirect("weiss:arcade_challenge")
    if request.POST.get("kind") == ChallengeRun.Kind.NARRATIVE:
        narrative = next((n for n in narratives() if str(n.pk) == request.POST.get("narrative")), None)
        if not narrative:
            messages.error(request, "That challenge isn't available right now.")
            return redirect("weiss:arcade_challenge")
        challenge.start(request.user, ChallengeRun.Kind.NARRATIVE, narrative.scenario, narrative)
    elif request.POST.get("kind") == "coop":
        if not challenge.opponents():
            messages.error(request, "There are no CPUs to fight yet.")
            return redirect("weiss:arcade_challenge")
        coop.start(request.user)
        messages.success(request, "Co-op challenge started: send your partner the invite link.")
    elif request.POST.get("kind") == ChallengeRun.Kind.INFINITE:
        if not challenge.opponents():
            messages.error(request, "There are no CPUs to fight yet.")
            return redirect("weiss:arcade_challenge")
        challenge.start(request.user, ChallengeRun.Kind.INFINITE, None)
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
    """Build the deck from the cards pulled. The page edits it in place and posts the whole deck to save it; in co-op
    it saves each change as it's made (asking for JSON back: what went wrong, if anything, and the deck state)."""
    run = challenge.current(request.user)
    if not run or not run.deck:
        return redirect("weiss:arcade_challenge")
    if request.method == "POST":
        try:
            copies = json.loads(request.POST.get("deck", "{}"))
            problem = challenge.save_deck(run, copies) if isinstance(copies, dict) else "That isn't a deck."
        except (ValueError, TypeError):
            problem = "That isn't a deck."
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"error": problem, **deck_state(request.user)})
        if problem:
            messages.error(request, problem)
        else:
            messages.success(request, "Deck saved.")
        return redirect("weiss:arcade_challenge_deck")
    cards = []
    for card, pulled, in_deck, theirs in challenge.deck_pool(run):
        card.image_src = reverse("weiss:card_image", args=[card.pk])
        rarity = packs.rarity_of(card)
        cards.append({"card": card, "pulled": pulled, "in_deck": in_deck, "theirs": theirs, "total": pulled + theirs,
                      "rarity": rarity, "grade": packs.grade_of(rarity), "unlimited": unlimited(card)})
    climaxes = augments.climax_limit(run)  # the most a deck can have: the rules' 8, or more with an augment
    # What the filters offer: only what's in the pool (as the set pages do, see views.card_browser).
    pool = [item["card"] for item in cards]
    options = {
        "colors": sorted({card.color for card in pool if card.color}),
        "levels": sorted({card.level for card in pool if card.level is not None}),
        "costs": sorted({card.cost for card in pool if card.cost is not None}),
        "types": sorted({card.card_type for card in pool if card.card_type}),
        "rarities": [rarity for rarity, _ in sorted({(item["rarity"], item["grade"]) for item in cards}, key=lambda pair: (-pair[1], pair[0]))],
        "sets": sorted({(card.expansion_id, card.expansion) for card in pool}, key=lambda pair: pair[1]),
    }
    partner = run.coop.partner_of(request.user) if run.coop_id else None
    # Which of the pool's levels (as the page has them, see data-level) count towards each of the deck rules' groups.
    levels = (["climax"], ["0"], ["1"], ["2", "3"])
    groups = [{"label": label, "target": climaxes if required else target, "required": required, "levels": counted}
              for (label, target, required, _), counted in zip(DECK_GROUPS, levels)]
    return render(request, "weiss/challenge_deck.html", {"run": run, "cards": cards, "deck_size": DECK_SIZE, "climax_target": climaxes, "climax_min": CLIMAX_COUNT,
                                                         "copy_limit": augments.copy_limit(run), "over_size_ok": run.kind == ChallengeRun.Kind.INFINITE,
                                                         "options": options, "partner": partner, "deck_groups": groups,
                                                         "state_url": reverse("weiss:arcade_challenge_deck_state") if partner else ""})


def deck_state(user):
    """Both decks and the pool as they are now, for a co-op deck builder to catch up with: {"mine", "theirs", "pool"},
    each {card id: copies}."""
    run = challenge.current(user)
    if not run:
        return {"mine": {}, "theirs": {}, "pool": {}}
    rows = challenge.deck_pool(run)
    return {"mine": {card.pk: mine for card, _, mine, _ in rows if mine}, "theirs": {card.pk: theirs for card, _, _, theirs in rows if theirs},
            "pool": {card.pk: usable + theirs for card, usable, _, theirs in rows}}


@challenge_access
def challenge_deck_state(request):
    """A co-op deck builder polls this, to show the partner's changes as they make them (see deck_state)."""
    return JsonResponse(deck_state(request.user))


@challenge_access
def coop_partner_deck(request):
    """A co-op partner's deck as it is now, to look at: only they can change it."""
    run = challenge.current(request.user)
    partner_run = run and coop.partner_run(run)
    if not partner_run:
        return redirect("weiss:arcade_challenge")
    groups, total = snapshot_groups(challenge.deck_snapshot(partner_run.deck) if partner_run.deck else [])
    return render(request, "weiss/coop_partner_deck.html", {"run": run, "partner": partner_run.user, "groups": groups, "total": total})


@challenge_access
@require_POST
def challenge_fight(request):
    """On to the run's next fight: the one it stopped at, or its first. The deck goes in as it is now."""
    run = challenge.current(request.user)
    if not run or run.status != ChallengeRun.Status.ACTIVE:
        return redirect("weiss:arcade_challenge")
    endless = run.kind == ChallengeRun.Kind.INFINITE
    heading, node = None, None
    if endless:
        # Where next is the player's choice, on the path: a CPU it leads to, or an event.
        path, at = challenge.path_of(run), challenge.floor_at(run)
        options = challenge.choices(path, at)
        node = request.POST.get("node", "")
        node = int(node) if node.isdigit() else options[0] if len(options) == 1 else None
        if at < len(path["picks"]):
            node = path["picks"][at]
        heading = path["floors"][at][node] if node in options else None
    if heading != challenge.EVENT and (not run.deck or not run.deck.entries.exists()):  # an event needs no deck
        messages.error(request, "Your deck is empty: open some packs and build it first.")
        return redirect("weiss:arcade_challenge")
    if heading != challenge.EVENT and (problem := challenge.deck_ready(run)):
        messages.error(request, problem)
        return redirect("weiss:arcade_challenge")
    if endless and run.coop_id and run.coop.status == CoopRun.Status.WAITING:
        messages.error(request, "The path waits for you both: your partner hasn't joined yet.")
        return redirect("weiss:arcade_challenge")
    if endless and run.coop_id and challenge.is_boss(path, at) and coop.pair_floor(run) < at:
        partner = run.coop.partner_of(request.user)
        messages.info(request, f"The boss waits for you both: {partner.username} is still on fight {coop.pair_floor(run) + 1}.")
        return redirect("weiss:arcade_challenge")
    if endless:
        chosen = challenge.pick(run, node)
        if not chosen and run.coop_id and coop.vote_of(run, f"floor:{challenge.floor_at(run)}") is not None:
            messages.info(request, "Your vote is in. The path goes on once your partner has voted too.")
            return redirect("weiss:arcade_challenge")
        if not chosen:
            messages.error(request, "Choose who to fight next on the path." if options else "There are no CPUs to fight right now.")
            return redirect("weiss:arcade_challenge")
        if chosen == challenge.EVENT:
            if not challenge.start_event(run):
                messages.info(request, "Nothing happened there: on up the path.")
                return redirect("weiss:arcade_challenge")
            return redirect("weiss:arcade_challenge_event")
        arcade_run = run.arcade_run
        if arcade_run and arcade_run.status == ArcadeRun.Status.ACTIVE and arcade_run.order[arcade_run.position:] != [chosen]:
            arcade_run.order[arcade_run.position:] = [chosen]
            arcade_run.save(update_fields=["order"])
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
    if not endless and (not scenario or arcade.scenario_problem(scenario)):
        messages.error(request, "This challenge's arcade list isn't available right now.")
        return redirect("weiss:arcade_challenge")
    with transaction.atomic():
        if not run.arcade_run or run.arcade_run.status != ArcadeRun.Status.ACTIVE:
            # An infinite challenge's run has no list: its opponents are chosen as it goes, on its path.
            order = [chosen] if endless else arcade.fight_order(scenario, fixed=run.kind == ChallengeRun.Kind.NARRATIVE)
            run.arcade_run = ArcadeRun.objects.create(user=request.user, scenario=scenario, scenario_name=scenario.name if scenario else run.name,
                                                      deck_name=run.deck.name, order=order)
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
def challenge_event(request):
    """An infinite challenge's event: its scene, played; the page posts what was chosen (challenge_event_done)."""
    run = challenge.current(request.user)
    payload = run and (run.path or {}).get("event")
    if not payload or run.status != ChallengeRun.Status.ACTIVE:
        return redirect("weiss:arcade_challenge")
    partner = run.coop.partner_of(request.user) if run.coop_id else None
    return render(request, "weiss/challenge_event.html", {"run": run, "payload": payload, "player_name": request.user.username,
                                                          "coop": bool(run.coop_id), "partner": partner and partner.username})


@challenge_access
def coop_event_vote(request):
    """A co-op challenge's event, played by both players: POST a vote on one of its choices (step, visit, option);
    GET whether a choice (step, visit) is decided. Either way: {"decided": the option, or null}, with "flip" once
    it's decided whether a coin flip settled it."""
    run = challenge.current(request.user)
    if not run or not run.coop_id or not (run.path or {}).get("event") or run.status != ChallengeRun.Status.ACTIVE:
        return JsonResponse({"error": "There's no event under way.", "over": True}, status=400)
    data = request.POST if request.method == "POST" else request.GET
    try:
        step, visit = int(data.get("step", "")), int(data.get("visit", ""))
        if data.get("key") != run.path["event"]["key"]:
            return JsonResponse({"error": "That event is over.", "over": True}, status=400)
        if request.method == "POST":
            with transaction.atomic():
                run = ChallengeRun.objects.select_for_update().get(pk=run.pk)
                with coop.shared(run):
                    decided = coop.event_vote(run, step, visit, int(data.get("option", "")), random)
        else:
            decided = coop.event_decided(run, step, visit)
    except ValueError as error:
        return JsonResponse({"error": str(error) if str(error)[:1].isupper() else "That isn't a choice."}, status=400)
    last = (run.path or {}).get("decided") or {}
    return JsonResponse({"decided": decided, "flip": decided is not None and last.get("key") == f"event:{step}:{visit}" and last.get("flip")})


@challenge_access
@require_POST
def challenge_event_done(request):
    """The event's scene is over: what its choices gave goes on the challenge, and the path moves on."""
    run = challenge.current(request.user)
    if not run or run.status != ChallengeRun.Status.ACTIVE:
        return redirect("weiss:arcade_challenge")
    try:
        picks = json.loads(request.POST.get("buffs", "[]"))
    except ValueError:
        picks = []
    with transaction.atomic():
        run = ChallengeRun.objects.select_for_update().get(pk=run.pk)
        if (run.path or {}).get("event", {}).get("key") != request.POST.get("key"):
            return redirect("weiss:arcade_challenge")  # an old page's: that event is over
        said = challenge.end_event(run, picks)
    for line in said:
        messages.info(request, line)
    if not said:
        messages.success(request, "The event's over: on up the path.")
    return redirect("weiss:arcade_challenge")


@challenge_access
@require_POST
def challenge_reset(request):
    run = challenge.current(request.user)
    if run and run.coop_id:
        messages.error(request, "A co-op challenge can't start again: end it, and start a new one together.")
    elif run:
        challenge.reset(run)
        messages.success(request, f"{run.name} starts again: {challenge.start_packs(run.kind)} new packs, and a new deck.")
    return redirect("weiss:arcade_challenge")


@challenge_access
@require_POST
def challenge_end(request):
    """Give up a challenge in progress; the deck can still be kept."""
    run = challenge.current(request.user)
    if run and run.coop_id and run.coop.status == CoopRun.Status.WAITING:
        coop.cancel(run.coop)  # nobody joined: as if it never was
    elif run and run.coop_id and run.status == ChallengeRun.Status.ACTIVE:
        challenge.stop_fighting(run)
        coop.end(run.coop)  # for both: the partner's game under way is left to finish, but counts for nothing
        messages.info(request, "The co-op challenge is over, for you both.")
    elif run and run.status == ChallengeRun.Status.ACTIVE:
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


def decided_said(run, partner):
    """How the pair's last vote on the path went, for the co-op panel: "Floor 3: you both chose Rapi", or with a coin flip."""
    decided = (run.path or {}).get("decided")
    if not decided or not decided["key"].startswith("floor:") or not partner:
        return None
    floor = int(decided["key"][6:])
    floors = (run.path or {}).get("floors", [])

    def named(node):
        pk = floors[floor][node] if floor < len(floors) and node < len(floors[floor]) else None
        return "the event" if pk == challenge.EVENT else getattr(CpuProfile.objects.filter(pk=pk).first(), "name", "?")
    if not decided["flip"]:
        return f"Fight {floor + 1}: you both chose {named(decided['choice'])}."
    votes = decided["votes"]
    return (f"Fight {floor + 1}: you chose {named(votes[str(run.user_id)])}, {partner.username} chose {named(votes[str(partner.pk)])}. "
            f"The coin flip went to {named(decided['choice'])}.")


@challenge_access
def coop_spectate(request):
    """Watching a co-op partner's game while waiting for them: the board from their seat, with only what's public and
    their hand (game.spectator_view). Nothing on it can be played. The page follows them into their next fight."""
    run = challenge.current(request.user)
    room = run and run.coop_id and partner_room(run)
    if not room:
        messages.info(request, "Your partner isn't in a fight right now.")
        return redirect("weiss:arcade_challenge")
    if mine := in_a_fight(run):
        messages.info(request, "Your own fight is still going: finish it first.")
        return redirect("weiss:play_room", pk=mine.pk)
    return render(request, "weiss/play_room.html", {"room": room, "watching": run.coop.partner_of(request.user)})


@challenge_access
def coop_spectate_state(request):
    """Polled by the watching page, as play.room_state is by the players': 204 if nothing changed since ?v=, else the
    board. Watching doesn't move the CPU on: the player's own page does that."""
    run = challenge.current(request.user)
    room = run and run.coop_id and partner_room(run)
    if not room or in_a_fight(run):
        return JsonResponse({"version": None, "status": "gone"})  # the page reloads, and goes back to the challenge
    version = f"{room.pk}-{room.version}"
    if request.GET.get("v") == version:
        return HttpResponse(status=204)
    board = game.spectator_view(room.state, room.host_id)
    shown = {key: value for key, value in play.cpu_payload(room).items() if key != "intro"}
    return JsonResponse({"version": version, "status": room.status, "board": board, "cards": play.card_info(game.visible_cards(board)),
                         "avatars": play.room_avatars(room), **shown})


@challenge_access
def coop_status(request):
    """How far a co-op challenge has got, for its pages to poll: they reload when the version changes, or when the
    partner's game can be watched or no longer can."""
    run = challenge.current(request.user)
    coop_on = bool(run and run.coop_id)
    return JsonResponse({"version": run.coop.version if coop_on else None, "watchable": coop_on and watchable(run)})


@challenge_access
def coop_join(request, token):
    """A co-op challenge's invite link: who it's from, and joining it as their partner."""
    pair = get_object_or_404(CoopRun.objects.select_related("host", "guest"), invite_token=token)
    if not challenge.can_start(request.user, challenge.COOP):
        raise PermissionDenied
    if request.method == "POST":
        try:
            coop.join(pair, request.user)
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("weiss:arcade_coop_join", token=token)
        messages.success(request, f"You've joined {pair.host.username}'s co-op challenge.")
        return redirect("weiss:arcade_challenge")
    mine = pair.host_id == request.user.pk or pair.guest_id == request.user.pk
    return render(request, "weiss/coop_join.html", {"pair": pair, "mine": mine, "busy": not mine and challenge.current(request.user) is not None,
                                                    "packs": coop.start_packs(), "extras": len(coop.loadout())})


@challenge_access
@require_POST
def coop_cancel(request):
    """The host calls off a co-op challenge nobody has joined yet."""
    pair = coop.waiting_for(request.user)
    if pair:
        coop.cancel(pair)
        messages.success(request, "The co-op challenge is called off.")
    return redirect("weiss:arcade_challenge")
