"""World mode's pages (see docs/world-mode.md): the saves, a new game, opening a save's packs and building its deck;
and the town test.

The town test is one page to try how meeting CPUs around town might feel. Places are illustrated backdrops
(weiss/static/weiss/backdrops.js), with the CPUs who are there standing in them as their pictures. Click one to talk,
give a gift or duel: the duel is a real game against that CPU. Everything else (the day and time, coins, friendship,
who's where) is made up for the test and kept only in the browser tab.

World mode is staff-only while it's being built.
"""
import json
import random
from functools import wraps
from datetime import timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_POST

from . import buffs, challenge, packs, quests, scenes, world
from . import world_calendar
from . import world_events as events
from .cpu_views import MAX_LOADOUT, MAX_START_PACKS, back_to, staff_required
from .lists import CLIMAX_COUNT, COPY_LIMIT, DECK_GROUPS, DECK_SIZE, unlimited
from .models import CardList, CpuProfile, CpuSchedule, Scene, WorldPlace, WorldSave, WorldSettings
from .views import attach_covers, card_types, summarize_sets

MAX_COINS = 1_000_000

# Places to visit: (key, name, backdrop for morning, noon, evening and night, from weiss.scenes.BACKGROUNDS). The
# backdrops are drawn at one time of day each (the city is always night), so a place changes backdrop with the time.
PLACES = (
    ("plaza", "Plaza", ("sakura", "sakura", "sakura", "city")),
    ("cafe", "Café", ("cafe",) * 4),
    ("library", "Library", ("library",) * 4),
    ("arena", "Duel arena", ("arena",) * 4),
    ("shrine", "Shrine", ("shrine",) * 4),
    ("beach", "Beach", ("beach", "beach", "dusk", "night")),
    ("forest", "Forest", ("forest",) * 4),
    ("school", "School", ("classroom", "classroom", "rooftop", "rooftop")),
)
GIFTS = (  # (key, name, price, what it is)
    ("booster", "Booster pack", 300, "A sealed pack. Who doesn't like a pack?"),
    ("coffee", "Iced coffee", 120, "From the café on the corner."),
    ("flowers", "Flowers", 200, "A small bouquet."),
    ("sleeves", "Card sleeves", 250, "A box of 60, in a pretty colour."),
    ("snack", "Snack bun", 80, "Melon bread, still warm."),
)
MAX_CPUS = 24  # more than this would be a crowd for a test


def schedule_for(cpu):
    """Made-up rules for where this CPU can be found, the same every time for the same CPU: a few
    {place, days (0 Monday to 6 Sunday), slots (0 morning to 3 night), chance, once (one slot a day only)}."""
    rng = random.Random(cpu.pk * 7919)
    rules = []
    for _ in range(3):
        rules.append({
            "place": rng.choice(PLACES)[0],
            "days": sorted(rng.sample(range(7), rng.randint(4, 7))),
            "slots": sorted(rng.sample(range(4), rng.randint(2, 3))),
            "chance": rng.choice((100, 100, 90, 70)),
            "once": rng.random() < .25,
        })
    return rules


@staff_required
def world_test(request):
    cpus = list(CpuProfile.objects.filter(Q(finalized=True) | Q(image__isnull=False))[:MAX_CPUS])
    decks = CardList.objects.players(request.user).order_by("-updated", "-pk")[:30]
    return render(request, "weiss/world_test.html", {
        "count": len(cpus),
        "world": {
            "places": [{"key": k, "name": n, "backdrops": b} for k, n, b in PLACES],
            "gifts": [{"key": k, "name": n, "price": p, "about": a} for k, n, p, a in GIFTS],
            "cpus": [{
                "id": cpu.pk, "name": cpu.name, "portraits": world.cpu_portraits(cpu), "avatar": cpu.avatar,
                "intro": cpu.intro_text, "beaten": cpu.player_win_text, "duel": bool(cpu.finalized and cpu.deck_id),
                "schedule": schedule_for(cpu),
                "likes": random.Random(cpu.pk).sample([g[0] for g in GIFTS], 3),  # loved, liked, disliked
            } for cpu in cpus],
            "decks": [{"id": d.pk, "name": d.name} for d in decks],
            "player": request.user.username,
        },
    })


# ---------------------------------------------------------------- Saves (see weiss.world)

def save_or_home(request, slot):
    """(the player's save in this slot, None), or (None, a redirect to the saves page saying the slot's empty)."""
    save = world.save_in(request.user, slot)
    if not save:
        messages.error(request, f"Slot {slot} has no save.")
        return None, redirect("weiss:world_home")
    return save, None


def played_ago(save):
    """When a save was last played, for its slot: "just now", or "5 minutes ago"."""
    if timezone.now() - save.played < timedelta(minutes=1):
        return "just now"
    return f"{timesince(save.played)} ago"


@staff_required
def world_home(request):
    """The three save slots: each one's progress, or a new game."""
    slots = [(slot, save, save and world.step(save), save and played_ago(save)) for slot, save in world.saves_of(request.user).items()]
    return render(request, "weiss/world_home.html", {"slots": slots})


@staff_required
def world_new(request, slot):
    """A new game in an empty slot: choose the set its packs come from."""
    if slot not in WorldSave.SLOTS:
        return redirect("weiss:world_home")
    if world.save_in(request.user, slot):
        return redirect("weiss:world_save", slot=slot)
    if request.method == "POST":
        try:
            world.start(request.user, slot, int(request.POST.get("set") or 0))
        except ValueError as error:
            messages.error(request, str(error) if str(error)[:1].isupper() else "Choose a set.")
            return redirect("weiss:world_new", slot=slot)
        return redirect("weiss:world_save", slot=slot)
    sets = world.offered_sets()
    summaries = {s["expansion_id"]: s for s in summarize_sets()}
    attach_covers(list(summaries.values()))
    for entry in sets:
        entry["cover"] = (summaries.get(entry["id"]) or {}).get("cover")
    return render(request, "weiss/world_new.html", {"slot": slot, "sets": sets, "start_packs": world.start_packs(),
                                                    "loadout": len(world.loadout()), "min_cards": world.MIN_SET_CARDS,
                                                    "start_money": world.start_money()})


def in_world(text):
    """A specialty pack's description as world mode says it: a save's cards, not a challenge's pool."""
    return (text.replace("this challenge's sets", "your save's set").replace("this challenge doesn't use", "your save doesn't use")
            .replace("in your pool", "in your cards"))


@staff_required
def world_save(request, slot):
    """A save's page: its packs to open, specialty packs to claim and its deck, until it's ready for the town."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    rewards = [{**reward, "buff": buffs.BUFFS[reward["buff"]], "text": in_world(buffs.BUFFS[reward["buff"]].description)}
               for reward in save.rewards if reward["buff"] in buffs.BUFFS]
    context = {
        "save": save, "step": world.step(save), "shortfall": world.pool_shortfall(save), "pool_count": sum(save.pool.values()),
        "decks": [{"deck": deck, "count": deck.card_count(), "problem": world.deck_problem(save, deck), "equipped": deck.pk == save.deck_id}
                  for deck in world.decks(save)],
        "max_decks": world.MAX_DECKS,
        "pack_counts": sorted({n for n in (1, 5, 10, save.packs) if 0 < n <= save.packs}), "pack_default": min(save.packs, 10),
        # For the specialty packs (weiss/challenge_rewards.html).
        "rewards": rewards, "claim_url": reverse("weiss:world_claim", args=[slot]), "rewards_title": "Specialty packs",
        "rewards_note": "Packs of their own kind, to open when you like: choose what each is made of.",
        "levels": buffs.LEVELS, "colors": buffs.COLORS, "sets": [{"id": save.expansion_id, "name": save.set_name}],
        "last_set": save.expansion_id,
    }
    if any(r["buff"].claim == "climax" for r in rewards):
        context["climaxes"] = buffs.climax_choices(save)
    if any(r["buff"].pack == "wild" for r in rewards):
        context["all_sets"] = packs.pack_sets()
    return render(request, "weiss/world_save.html", context)


@staff_required
@require_POST
def world_open(request, slot):
    save, away = save_or_home(request, slot)
    if away:
        return away
    try:
        with transaction.atomic():
            save = WorldSave.objects.select_for_update().get(pk=save.pk)
            world.open_packs(save, int(request.POST.get("count") or 1))
    except ValueError as error:
        messages.error(request, str(error) if str(error)[:1].isupper() else "Choose how many packs.")
        return redirect("weiss:world_save", slot=slot)
    return redirect("weiss:world_opened", slot=slot)


@staff_required
def world_opened(request, slot):
    """The packs just opened, revealed; they're in the cards already, so reloading only replays them."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    if not save.last_opening:
        return redirect("weiss:world_save", slot=slot)
    opening = save.last_opening
    back = reverse("weiss:world_save", args=[slot])
    if opening.get("bought"):
        town = reverse("weiss:world_town", args=[slot])
        actions = [("Back to the town", town, True), ("Change your decks", f"{back}#decks", False)]
    else:
        first = ("Open more", back, True) if save.packs or save.rewards else ("Build your deck", reverse("weiss:world_deck", args=[slot]), True)
        actions = [first, ("Back to your save", back, False)]
    return render(request, "weiss/pack_open.html", {
        "set_id": opening["set_id"], "set_name": opening["set"], "count": len(opening["packs"]), "pack_size": packs.PACK_SIZE,
        "opening": opening, "back_url": back, "back_label": f"Slot {slot}", "actions": actions,
    })


@staff_required
@require_POST
def world_claim(request, slot):
    save, away = save_or_home(request, slot)
    if away:
        return away
    try:
        with transaction.atomic():
            save = WorldSave.objects.select_for_update().get(pk=save.pk)
            opened = world.claim(save, request.POST.get("key", ""), request.POST)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("weiss:world_save", slot=slot)
    if opened:
        return redirect("weiss:world_opened", slot=slot)
    messages.success(request, "Added to your cards.")
    return redirect("weiss:world_save", slot=slot)


@staff_required
def world_deck(request, slot, deck=None):
    """Build one of the save's decks from its cards (the equipped one, without a deck in the link): the challenge deck
    builder, posting the whole deck to save it."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    if deck is None:
        return redirect("weiss:world_deck_edit", slot=slot, deck=save.deck_id) if save.deck_id else redirect("weiss:world_save", slot=slot)
    chosen = world.deck_in(save, deck)
    if not chosen:
        messages.error(request, "That deck isn't one of this save's.")
        return redirect("weiss:world_save", slot=slot)
    if request.method == "POST":
        try:
            copies = json.loads(request.POST.get("deck", "{}"))
            problem = world.save_deck(save, copies, chosen) if isinstance(copies, dict) else "That isn't a deck."
        except (ValueError, TypeError):
            problem = "That isn't a deck."
        if problem:
            messages.error(request, problem)
        else:
            still = world.deck_problem(save, chosen)
            messages.success(request, f"“{chosen.name}” saved. To duel with it: {still[0].lower()}{still[1:]}" if still
                             else f"“{chosen.name}” saved: it's ready to duel.")
        return redirect("weiss:world_deck_edit", slot=slot, deck=chosen.pk)
    cards = []
    for card, pulled, in_deck in world.deck_pool(save, chosen):
        card.image_src = reverse("weiss:card_image", args=[card.pk])
        rarity = packs.rarity_of(card)
        cards.append({"card": card, "pulled": pulled, "in_deck": in_deck, "theirs": 0, "total": pulled,
                      "rarity": rarity, "grade": packs.grade_of(rarity), "unlimited": unlimited(card)})
    pool = [item["card"] for item in cards]
    options = {  # what the filters offer: only what's in the cards (as the challenge's deck page does)
        "colors": sorted({card.color for card in pool if card.color}),
        "levels": sorted({card.level for card in pool if card.level is not None}),
        "costs": sorted({card.cost for card in pool if card.cost is not None}),
        "types": card_types(card.card_type for card in pool),
        "rarities": [rarity for rarity, _ in sorted({(item["rarity"], item["grade"]) for item in cards}, key=lambda pair: (-pair[1], pair[0]))],
        "sets": sorted({(card.expansion_id, card.expansion) for card in pool}, key=lambda pair: pair[1]),
    }
    levels = (["climax"], ["0"], ["1"], ["2", "3"])
    groups = [{"label": label, "target": target, "required": required, "levels": counted}
              for (label, target, required, _), counted in zip(DECK_GROUPS, levels)]
    back = reverse("weiss:world_save", args=[slot])
    return render(request, "weiss/challenge_deck.html", {
        "run": save, "cards": cards, "deck_size": DECK_SIZE, "climax_target": CLIMAX_COUNT, "climax_min": CLIMAX_COUNT,
        "copy_limit": COPY_LIMIT, "over_size_ok": False, "options": options, "partner": None, "deck_groups": groups, "state_url": "",
        "back_url": back, "back_label": f"Slot {slot}", "back_button": "Back to your save",
        "heading": f"Build “{chosen.name}”", "equipped": chosen.pk == save.deck_id,
    })


def deck_change(view):
    """A change to one of a save's decks, posted from its page: the view gets (save, deck), and any ValueError it
    raises is shown back there."""
    @wraps(view)
    def wrapper(request, slot, deck):
        save, away = save_or_home(request, slot)
        if away:
            return away
        chosen = world.deck_in(save, deck)
        if not chosen:
            messages.error(request, "That deck isn't one of this save's.")
        else:
            try:
                view(request, save, chosen)
            except ValueError as error:
                messages.error(request, str(error))
        return redirect(f"{reverse('weiss:world_save', args=[slot])}#decks")
    return staff_required(require_POST(wrapper))


@staff_required
@require_POST
def world_deck_new(request, slot):
    """Another deck: empty, or a copy of one of the save's."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    copy_from = world.deck_in(save, request.POST.get("copy", ""))
    try:
        deck = world.new_deck(save, request.POST.get("name", ""), copy_from)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect(f"{reverse('weiss:world_save', args=[slot])}#decks")
    return redirect("weiss:world_deck_edit", slot=slot, deck=deck.pk)


@deck_change
def world_deck_rename(request, save, deck):
    world.rename_deck(save, deck, request.POST.get("name", ""))
    messages.success(request, f"Renamed “{deck.name}”.")


@deck_change
def world_deck_equip(request, save, deck):
    world.equip(save, deck)
    problem = world.deck_problem(save)
    messages.success(request, f"Duelling with “{deck.name}” now." + (f" It can't yet: {problem[0].lower()}{problem[1:]}" if problem else ""))


@deck_change
def world_deck_delete(request, save, deck):
    name = deck.name
    world.delete_deck(save, deck)
    messages.success(request, f"“{name}” deleted.")


@staff_required
def world_town(request, slot):
    """The town: the save's place as a scene, the time, its coins, the map and waiting. The page asks for the town as
    JSON (world_town_state) and posts each move (world_travel, world_wait), getting the town back each time."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    return render(request, "weiss/world_town.html", {"save": save, "town": world.town(save), "result": world.duel_result(save),
                                                     "weekdays": world_calendar.DAYS})


@staff_required
def world_town_state(request, slot):
    save, away = save_or_home(request, slot)
    if away:
        return JsonResponse({"error": f"Slot {slot} has no save."}, status=404)
    return JsonResponse(world.town(save))


def town_move(move):
    """A move in the town, posted by its page: done under a lock on the save, and only if the page saw the save as it
    is (`version`), so two tabs can't both spend the same time. Answers with the town as it is now, and any error."""
    @wraps(move)
    def wrapper(request, slot):
        save, away = save_or_home(request, slot)
        if away:
            return JsonResponse({"error": f"Slot {slot} has no save."}, status=404)
        with transaction.atomic():
            save = WorldSave.objects.select_for_update().get(pk=save.pk)
            if request.POST.get("version") != str(save.version):
                return JsonResponse({"error": "This save changed somewhere else; here it is as it is now.", "town": world.town(save)}, status=409)
            try:
                said = move(request, save)
            except ValueError as error:
                return JsonResponse({"error": str(error), "town": world.town(save)}, status=400)
        if isinstance(said, dict):  # somewhere to go
            return JsonResponse({**said, "town": world.town(save)})
        return JsonResponse({"said": said or "", "town": world.town(save)})
    return staff_required(require_POST(wrapper))


@town_move
def world_travel(request, save):
    """Go somewhere (free until the time's spent), or choose where to spend a new time of day: staying is a choice."""
    was = save.place
    place = world.travel(save, request.POST.get("place", ""))
    return f"You stay at the {place.name}." if place.key == was else f"{place.name}."


@town_move
def world_test_mode(request, save):
    """Staff testing: turn on (or off) the staff Wait and free travel."""
    world.set_test_mode(save, request.POST.get("on") == "1")
    return "Test mode on: Wait any time, go anywhere." if world.test_mode(save) else "Test mode off: the real rules."


@town_move
def world_duel(request, save):
    """Duel someone who's here: off to the game (a high-stakes one takes its entry fee now)."""
    room = world.start_duel(save, request.POST.get("cpu", ""), high_stakes=request.POST.get("stakes") == "1")
    return {"go": reverse("weiss:play_room", args=[room.pk])}


@staff_required
@require_POST
def world_buy(request, slot):
    """Buy packs at the card shop (a specialty pack, with `special`): they open into the save's cards, shown being
    revealed."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    try:
        with transaction.atomic():
            save = WorldSave.objects.select_for_update().get(pk=save.pk)
            if request.POST.get("special"):
                world.buy_specialty(save, request.POST["special"], request.POST)
            else:
                world.buy_packs(save, int(request.POST.get("set") or 0), int(request.POST.get("count") or 1))
    except ValueError as error:
        messages.error(request, str(error) if str(error)[:1].isupper() else "Choose a set and how many packs.")
        return redirect("weiss:world_town", slot=slot)
    return redirect("weiss:world_opened", slot=slot)


@town_move
def world_checkout(request, save):
    """Buy everything in the basket (the page keeps it, and posts it as JSON) at once: one payment, and the packs
    revealed together. `expected` is the total the page showed, so a price that's moved is said, not charged."""
    try:
        items = json.loads(request.POST.get("basket") or "[]")
        expected = int(request.POST["expected"]) if request.POST.get("expected") else None
    except (ValueError, TypeError):
        raise ValueError("Your basket couldn't be read. Try again.")
    done = world.checkout(save, items, expected)
    if done["packs"]:
        return {"go": reverse("weiss:world_opened", args=[save.slot])}
    return f"Bought {', '.join(done['bought'])}."


@town_move
def world_buy_card(request, save):
    """Buy one of the shop's single cards: it goes straight into the save's cards."""
    card = world.buy_card(save, request.POST.get("card", ""))
    return f"{card.name} is yours."


@town_move
def world_talk(request, save):
    """Talk to someone here: what they say, played in the box, and the day's first talk's points."""
    return world.talk(save, request.POST.get("cpu", ""))


@town_move
def world_answer(request, save):
    """Answer what they asked: the talk carries on."""
    try:
        option = int(request.POST.get("option", ""))
    except ValueError:
        raise ValueError("Choose an answer.")
    return world.answer(save, request.POST.get("cpu", ""), option)


@town_move
def world_give(request, save):
    """Give someone here a gift."""
    return world.give(save, request.POST.get("cpu", ""), request.POST.get("gift", ""))


@town_move
def world_level(request, save):
    """Staff testing (test mode): raise the person here a friendship rank at once."""
    return world.staff_level(save, request.POST.get("cpu", ""))


@town_move
def world_request_set(request, save):
    """Ask the card shop to stock a set: on the shelves from tomorrow, for a few days."""
    try:
        expansion_id = int(request.POST.get("set") or 0)
    except ValueError:
        raise ValueError("Choose a set to ask for.")
    asked = world.request_set(save, expansion_id)
    return f"{asked['name']} is ordered: {world.request_words(save, asked)}"


@town_move
def world_quest(request, save):
    """Something about a quest, with someone here: its offer, taking it, talking it through, handing a card over, or
    choosing how it ends (see world.quest_act)."""
    return world.quest_act(save, request.POST.get("cpu", ""), request.POST.get("act", ""), request.POST.get("quest", ""), request.POST)


@staff_required
def world_quests(request, slot):
    """The save's quest log: what's offered, under way (each stage and objective, how far along), finished and closed."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    found = quests.journal(save)
    tab = request.GET.get("show") if request.GET.get("show") in ("done", "failed") else "active"
    return render(request, "weiss/world_quests.html", {"save": save, "journal": found, "tab": tab,
                                                       "tabs": [("active", "Under way", len(found["active"]) + len(found["offered"])),
                                                                ("done", "Finished", len(found["done"])),
                                                                ("failed", "Closed", len(found["failed"]))]})


@staff_required
def world_events(request, slot):
    """The notice board: the week's calendar (weiss.world_events), what's on today, and the weekly tournament (entry,
    and the bracket so far)."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    return render(request, "weiss/world_events.html", {
        "save": save, "week": events.week(save), "sales": events.sales_now(save), "tournament": events.board(save),
        "notices": quests.board(save),
        "date": world_calendar.full_label(save.turn), "season": world_calendar.season_of(save.turn),
    })


@staff_required
@require_POST
def world_event_enter(request, slot):
    """Enter this week's tournament (at its place, on Saturday or first thing Sunday): the fee's taken."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    try:
        with transaction.atomic():
            save = WorldSave.objects.select_for_update().get(pk=save.pk)
            events.enter(save)
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "You're in. Round 1 is Sunday morning, here at the arena. Your bracket's below.")
    return redirect("weiss:world_events", slot=slot)


@staff_required
@require_POST
def world_board(request, slot):
    """The notice board's quests (weiss.quests.board): take one, or claim one that's done."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    key = request.POST.get("quest", "")
    try:
        with transaction.atomic():
            save = WorldSave.objects.select_for_update().get(pk=save.pk)
            if request.POST.get("act") == "take":
                quests.accept(save, None, key)
                said = "Taken. It's in your quest log, and here on the board."
            else:
                _, given = quests.choose(save, None, key, request.POST.get("ending", ""), confirmed=True)
                rewards = [event["reward"] for event in given if event.get("reward")]
                said = "Claimed" + (f": {', '.join(rewards)}." if rewards else ".")
            world.changed(save, *world.TALK_FIELDS)
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, said)
    return redirect("weiss:world_events", slot=slot)


@town_move
def world_jump(request, save):
    """Staff testing (test mode): let time pass to the next morning of a weekday."""
    try:
        weekday = int(request.POST.get("weekday", ""))
    except ValueError:
        raise ValueError("Choose a day to jump to.")
    world.jump(save, weekday)
    return f"It's {save.date_label}, morning."


@town_move
def world_buy_gift(request, save):
    """Buy a gift at the card shop, to give later."""
    item = world.buy_gift(save, request.POST.get("gift", ""))
    return f"{item.icon} {item.name}: you have {save.gifts[item.key]}.".strip()


@staff_required
def world_scene(request, slot):
    """A full scene a rank-up plays (Chatter.scene), then back to the town. Shown once."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    pending = save.flags.pop("scene", None)
    scene = Scene.objects.filter(pk=(pending or {}).get("scene")).first()
    if pending:
        save.save(update_fields=["flags"])
    compiled, errors = scenes.compile_scene(scene.script) if scene else (None, True)
    if errors:
        return redirect("weiss:world_town", slot=slot)
    # A quest visit's rewards, given on arrival: shown when the scene ends, so the moment ends with something gained.
    rewards = [{"text": text, "link": link} for text, link in (pending or {}).get("rewards", [])]
    return render(request, "weiss/world_scene.html", {
        "save": save, "payload": scenes.scene_payload(compiled, scene.name, viewer=request.user), "player_name": request.user.username,
        "rewards": rewards, "reward_link": next((reward["link"] for reward in rewards if reward["link"]), ""),
    })


@town_move
def world_wait(request, save):
    world.wait(save, staff=request.POST.get("staff") == "1")
    return f"A new day: {save.weekday}." if save.turn % len(WorldSave.TIMES) == 0 else f"{save.time_of_day}."


@staff_required
@require_POST
def world_delete(request, slot):
    """Delete a save, its cards and its deck. It can't be undone, so the player types the slot's name to confirm."""
    save, away = save_or_home(request, slot)
    if away:
        return away
    if request.POST.get("confirm", "").strip().lower() != f"slot {slot}":
        messages.error(request, f"To delete it, type “Slot {slot}”.")
        return redirect("weiss:world_home")
    save.delete()
    messages.success(request, f"Slot {slot} deleted.")
    return redirect("weiss:world_home")


@staff_required
@require_POST
def world_settings(request):
    """How world mode is tuned (staff, on the CPU tab): what a new save starts with, and the coins."""
    def whole(key, low, high, what):
        try:
            value = int(request.POST.get(key, ""))
        except ValueError:
            value = None
        if value is None or not low <= value <= high:
            raise ValueError(f"{what} goes from {low} to {high}.")
        return value

    try:
        fields = {
            "start_packs": whole("start_packs", 0, MAX_START_PACKS, "Starting packs"),
            "loadout": {buff: n for buff in challenge.LOADOUT_BUFFS if (n := whole(f"loadout_{buff}", 0, MAX_LOADOUT, buffs.BUFFS[buff].name))},
            "start_money": whole("start_money", 0, MAX_COINS, "Starting coins"),
            "pack_price": whole("pack_price", 1, MAX_COINS, "A pack's price"),
            "specialty_price": whole("specialty_price", 1, MAX_COINS, "A specialty pack's price"),
            "card_price": whole("card_price", 1, MAX_COINS, "A single card's price"),
            "request_price": whole("request_price", 0, MAX_COINS, "A set request's price"),
            "win_payout": whole("win_payout", 0, MAX_COINS, "A win's payout"),
            "first_win_bonus": whole("first_win_bonus", 0, MAX_COINS, "The day's first win bonus"),
        }
    except ValueError as error:
        messages.error(request, str(error))
        return back_to("world")
    try:
        fields["ranks"] = read_ranks(request.POST.get("ranks", ""))
    except ValueError as error:
        messages.error(request, str(error))
        return back_to("world")
    if not fields["start_packs"] and not fields["loadout"]:
        messages.error(request, "A new save needs something to build a deck from: some packs or some specialty packs.")
        return back_to("world")
    WorldSettings.objects.update_or_create(pk=1, defaults={**fields, "updated_by": request.user})
    messages.success(request, "Saved. New saves start with these; the coins apply from now on.")
    return back_to("world")


MAX_RANKS = 10


def read_ranks(text):
    """[{name, points}] from "name: points" lines, the first at 0 and the rest needing more and more. Raises ValueError."""
    ranks = []
    for number, line in enumerate((line.strip() for line in text.splitlines() if line.strip()), 1):
        name, _, points = line.rpartition(":")
        name = name.strip()[:40]
        if not name or not points.strip().isdigit():
            raise ValueError(f"Write each rank as “name: points” (rank {number} isn't).")
        ranks.append({"name": name, "points": int(points)})
    if not 2 <= len(ranks) <= MAX_RANKS:
        raise ValueError(f"Have 2 to {MAX_RANKS} ranks.")
    if ranks[0]["points"] != 0:
        raise ValueError("The first rank is where everyone starts: 0 points.")
    if any(b["points"] <= a["points"] for a, b in zip(ranks, ranks[1:])):
        raise ValueError("Each rank needs more points than the one before.")
    return ranks


# ---------------------------------------------------------------- Staff: who's where (CpuSchedule)

DAY_LETTERS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def rule_summary(rule):
    """A haunt in words: "Weekdays, noon and evening, weight 80, once a day, from rank 2"."""
    days = sorted(rule.days)
    if days == list(range(7)):
        when = "Every day"
    elif days == list(range(5)):
        when = "Weekdays"
    elif days == [5, 6]:
        when = "Weekends"
    else:
        when = ", ".join(DAY_LETTERS[d] for d in days)
    times = " and ".join(WorldSave.TIMES[t].lower() for t in sorted(rule.times)) or "never"
    extras = [f"weight {rule.weight}", "once a day" if rule.once_per_day else "",
              f"from rank {rule.min_rank}" if rule.min_rank else "", f"stakes {rule.stake} coins" if rule.stake else ""]
    return ", ".join([when, times, *[e for e in extras if e]])


def read_rule(post, rule):
    """Fill a rule from the staff's form; raises ValueError saying what's wrong."""
    rule.cpu = CpuProfile.objects.filter(pk=post.get("cpu") or None).first()
    rule.place = WorldPlace.objects.filter(pk=post.get("place") or None).first()
    if not rule.cpu or not rule.place:
        raise ValueError("Choose a CPU and a place.")
    rule.days = sorted({int(d) for d in post.getlist("days") if d.isdigit() and int(d) < 7})
    rule.times = sorted({int(t) for t in post.getlist("times") if t.isdigit() and int(t) < 4})
    if not rule.days or not rule.times:
        raise ValueError("Choose at least one day and one time.")

    def whole(key, low, high, what, default):
        value = (post.get(key) or "").strip() or str(default)
        if not value.lstrip("-").isdigit() or not low <= int(value) <= high:
            raise ValueError(f"{what} goes from {low} to {high}.")
        return int(value)

    rule.weight = whole("weight", 1, 100, "The weight", 50)
    rule.min_rank = whole("min_rank", 0, len(world.rank_names()) - 1, "The rank", 0)
    rule.stake = whole("stake", 0, MAX_COINS, "The stakes", 0)
    rule.once_per_day = post.get("once") == "1"


@staff_required
def world_schedules(request):
    """Where each CPU can be found, and a week's grid of who's where (for a sample seed), to write and check them."""
    editing = CpuSchedule.objects.filter(pk=request.GET.get("edit") or None).first()
    if request.method == "POST":
        if "delete" in request.POST:
            CpuSchedule.objects.filter(pk=request.POST.get("delete") or None).delete()
            messages.success(request, "Haunt deleted.")
            return redirect("weiss:world_schedules")
        if "starters" in request.POST:
            made = world.starter_schedules()
            messages.success(request, f"Gave {made} CPU{'s' if made != 1 else ''} starting haunts: edit them as you like.")
            return redirect("weiss:world_schedules")
        rule = CpuSchedule.objects.filter(pk=request.POST.get("rule") or None).first() or CpuSchedule()
        try:
            read_rule(request.POST, rule)
        except ValueError as error:
            messages.error(request, str(error))
            return redirect(request.get_full_path())
        same = CpuSchedule.objects.filter(cpu=rule.cpu, place=rule.place, days=rule.days, times=rule.times, weight=rule.weight,
                                          once_per_day=rule.once_per_day, min_rank=rule.min_rank, stake=rule.stake).exclude(pk=rule.pk)
        if same.exists():
            messages.error(request, f"{rule.cpu.name} has that haunt already.")
            return redirect("weiss:world_schedules")
        rule.save()
        messages.success(request, f"Saved: {rule.cpu.name} at {rule.place.name}, {rule_summary(rule)}.")
        return redirect("weiss:world_schedules")
    seed = int(request.GET.get("seed") or 1) if str(request.GET.get("seed") or "1").isdigit() else 1
    day = int(request.GET.get("day") or 0) if str(request.GET.get("day") or "0").isdigit() and int(request.GET.get("day") or 0) < 7 else 0
    sample = WorldSave(seed=seed)
    places_list = list(WorldPlace.objects.all())
    grid = {place.pk: [[] for _ in WorldSave.TIMES] for place in places_list}
    names = dict(CpuProfile.objects.values_list("pk", "name"))
    cast = world.day_cast(sample, day)
    for time, out in enumerate(cast):
        for cpu_id, rule in out.items():
            grid[rule.place_id][time].append({"name": names.get(cpu_id, "?"), "stake": rule.stake, "min_rank": rule.min_rank})
    rules = list(CpuSchedule.objects.select_related("cpu", "place"))
    for rule in rules:
        rule.summary = rule_summary(rule)
    cpus = CpuProfile.objects.filter(finalized=True, deck__isnull=False).order_by("name")
    scheduled = {rule.cpu_id for rule in rules}
    return render(request, "weiss/world_schedules.html", {
        "rules": rules, "cpus": cpus, "places": places_list, "unscheduled": [cpu for cpu in cpus if cpu.pk not in scheduled],
        "grid": [(place, grid[place.pk]) for place in places_list], "times": WorldSave.TIMES, "out": [len(c) for c in cast],
        "max_per_place": world.MAX_PER_PLACE, "max_on_stage": world.MAX_ON_STAGE, "ranks": list(enumerate(world.rank_names())), "days": list(enumerate(WorldSave.DAYS)),
        "day": day, "day_name": WorldSave.DAYS[day], "seed": seed, "editing": editing, "day_letters": list(enumerate(DAY_LETTERS)),
        "other_seed": seed + 1,
    })
