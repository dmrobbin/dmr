"""World mode's events (WorldEvent): when they're on, by the save's calendar date (weiss.world_calendar); the card
shop's sales; and the weekly tournament.

What's on is worked out from the turn alone, as who's where is, so a reload never changes it. Each save draws its own
details (the featured set, who enters the tournament) from its seed. What a save did at an event is kept in
WorldSave.events, as {event key: {"week": n, ...}}: an occurrence's record is replaced when the next one starts.

The tournament: entry at its place (the arena) on Saturday or first thing Sunday, for a fee; the player and 7 CPUs,
drawn for the save and week; three rounds on Sunday (morning, noon, evening), each a real duel against the player's
opponent, who's at the arena for it. CPU-against-CPU matches are a coin flip, seeded so a reload never changes them.
A loss (or a round missed) knocks the player out with the prize for how far they got; the CPUs they beat get to know
them (points); the champion takes the top prize and a pack.
"""
import random
from types import SimpleNamespace

from . import quests, sleeves, world, world_calendar as calendar
from .models import CpuProfile, Scene, WorldEvent, WorldSave

TIMES = len(WorldSave.TIMES)


# ---------------------------------------------------------------- The calendar

def enabled():
    return list(WorldEvent.objects.filter(enabled=True).select_related("place").order_by("order", "pk"))


def runs(event, turn, all_day=False):
    """Whether the event's on at this turn (all_day: at any time that day). Every rule given must hold."""
    week = calendar.week_of(turn)
    if week < event.first_week or (week - event.offset) % max(event.every, 1):
        return False
    date = calendar.date_of(turn)
    if event.weekdays and date.weekday() not in event.weekdays:
        return False
    if event.months and date.month not in event.months:
        return False
    if event.dates and calendar.month_day(turn) not in event.dates:
        return False
    return all_day or not event.times or turn % TIMES in event.times


def on(save, turn=None, events=None):
    """The events on now (or at this turn)."""
    turn = save.turn if turn is None else turn
    return [event for event in (enabled() if events is None else events) if runs(event, turn)]


def when(event):
    """The times of day it's on, in words: "all day", "this evening", "morning and noon"."""
    if not event.times or len(event.times) == TIMES:
        return "all day"
    return " and ".join(WorldSave.TIMES[t].lower() for t in sorted(event.times))


def describe(event):
    return {"key": event.key, "name": event.name, "icon": event.icon, "about": event.about, "kind": event.kind,
            "when": when(event), "place": event.place.name if event.place_id else ""}


def week(save):
    """The save's week as the notice board shows it, Monday to Sunday: [{label, weekday, today, past, events}]."""
    events = enabled()
    today = calendar.day_of(save.turn)
    first = today - calendar.weekday_of(save.turn)
    days = []
    for day in range(first, first + 7):
        turn = day * TIMES
        days.append({"label": calendar.short_label(turn), "weekday": calendar.DAYS[calendar.weekday_of(turn)],
                     "today": day == today, "past": day < today,
                     "events": [describe(event) for event in events if runs(event, turn, all_day=True)]})
    return days


def today(save):
    """Today's events, each marked whether it's on now: for the town's banner."""
    events = enabled()
    day_turn = calendar.day_of(save.turn) * TIMES
    return [{**describe(event), "now": runs(event, save.turn)} for event in events if runs(event, day_turn, all_day=True)]


def record(save, event, fresh=True):
    """The save's record of this week's occurrence of an event: {"week": n, ...}, made (fresh) if there isn't one."""
    this_week = calendar.week_of(save.turn)
    found = save.events.get(event.key)
    if found and found.get("week") == this_week:
        return found
    if not fresh:
        return None
    save.events[event.key] = {"week": this_week}
    return save.events[event.key]


# ---------------------------------------------------------------- Sales at the card shop

def sale(save, what):
    """The sale on `what` ("packs", "specials" or "cards") now, or None."""
    return next((event for event in on(save) if event.kind == "sale" and event.settings.get("what") == what), None)


def sales_now(save):
    return [describe(event) for event in on(save) if event.kind == "sale"]


def discounted(price, event):
    """A price with the sale's discount (percent) off: never below 1 coin."""
    return max(1, round(price * (100 - int(event.settings.get("discount", 0))) / 100))


def featured_set(save):
    """{"id", "name"} the featured-set sale puts on the shelves this week: drawn for the save and week, never its own
    set. None if there's no other set."""
    others = [entry for entry in world.offered_sets() if entry["id"] != save.expansion_id]
    if not others:
        return None
    rng = random.Random(f"{save.seed}:{calendar.week_of(save.turn)}:featured")
    entry = rng.choice(others)
    return {"id": entry["id"], "name": entry["name"]}


def sale_left(save, event):
    """How many more can be bought at the sale price today (its `limit`), or None for no limit."""
    limit = event.settings.get("limit")
    if not limit:
        return None
    found = record(save, event, fresh=False) or {}
    used = found.get("bought", 0) if found.get("day") == calendar.day_of(save.turn) else 0
    return max(0, int(limit) - used)


def used_sale(save, event, count):
    found = record(save, event)
    day = calendar.day_of(save.turn)
    if found.get("day") != day:
        found.update(day=day, bought=0)
    found["bought"] += count


def pack_sale(save, expansion_id):
    """The sale on this set's packs now (the featured set's), or None."""
    event = sale(save, "packs")
    if not event:
        return None
    if event.settings.get("featured") and (featured_set(save) or {}).get("id") != expansion_id:
        return None
    return event


def pack_cost(save, expansion_id, count):
    """(coins for `count` packs of a set now, how many of them are at the sale price, the sale or None)."""
    base = world.pack_price()
    event = pack_sale(save, expansion_id)
    if not event:
        return base * count, 0, None
    left = sale_left(save, event)
    cheap = count if left is None else min(count, left)
    return discounted(base, event) * cheap + base * (count - cheap), cheap, event


def specialty_cost(save):
    """(a specialty pack's price now, its usual price)."""
    base = world.specialty_price()
    event = sale(save, "specials")
    return (discounted(base, event) if event else base), base


def card_cost(save):
    """(a single card's price now, its usual price)."""
    base = world.card_price()
    event = sale(save, "cards")
    return (discounted(base, event) if event else base), base


def extra_cards(save):
    """More single cards on the rack today, for a single-card sale."""
    event = sale(save, "cards")
    return int(event.settings.get("extra", 0)) if event else 0


# ---------------------------------------------------------------- The weekly tournament

SUNDAY = 6
ROUNDS = ("Round 1", "the semi-final", "the final")  # Sunday morning, noon and evening
ROUND_TITLES = ("Round 1", "Semi-final", "Final")
ENTRANTS = 7  # CPUs, with the player 8
PLAYER = 0  # the player's seat in the bracket


def tournament(save):
    """This week's tournament (the event), if there is one: one that runs on this week's Sunday."""
    sunday = (calendar.day_of(save.turn) - calendar.weekday_of(save.turn) + SUNDAY) * TIMES
    return next((event for event in enabled() if event.kind == "tournament" and runs(event, sunday, all_day=True)), None)


def entry(save, event=None):
    """The save's entry in this week's tournament ({"week", "entrants", "results", "out", "prize", ...}), or None."""
    event = event or tournament(save)
    found = record(save, event, fresh=False) if event else None
    return found if found and found.get("entrants") else None


def talk_context(save, cpu_id):
    """The talk context for a CPU on the tournament's days (Saturday and Sunday), or None. The player's result comes
    first (champion, out), then whether the CPU is in this week's bracket. Before the player enters, every CPU is a
    spectator."""
    event = tournament(save)
    if not event or calendar.weekday_of(save.turn) < SUNDAY - 1:
        return None
    found = entry(save, event)
    if found and found.get("champion"):
        return "tournament_champion"
    if found and found.get("out") is not None:
        return "tournament_out"
    return "tournament_entrant" if found and cpu_id in found["entrants"] else "tournament_spectator"


def is_sunday(save):
    return calendar.weekday_of(save.turn) == SUNDAY


def registration(save, event):
    """(whether the player can enter now, why not)."""
    found = entry(save, event)
    if found:
        return False, "You've entered already."
    weekday, time = calendar.weekday_of(save.turn), save.turn % TIMES
    if weekday == SUNDAY - 1 or (weekday == SUNDAY and time == 0):
        return True, ""
    if weekday == SUNDAY:
        return False, "Entry closed when Round 1 began this morning. There's another next week."
    return False, "Entry opens on Saturday."


def eligible(save):
    """The CPUs who can enter: those who duel in the town (finalized, with a deck), less any a quest sent away."""
    gone = quests.gone(save)
    in_town = world.roster.released(save)  # only those in the save's town so far
    return {cpu_id: rules for cpu_id, rules in world.haunts().items() if cpu_id not in gone and (in_town is None or cpu_id in in_town)}


def draw_entrants(save, event):
    """ENTRANTS CPUs for the save's week, those who haunt the tournament's place more likely: a weighted draw, seeded."""
    rng = random.Random(f"{save.seed}:{calendar.week_of(save.turn)}:tournament")
    place_id = event.place_id
    keyed = sorted(((rng.random() ** (1 / (3 if any(rule.place_id == place_id for rule in rules) else 1)), cpu_id)
                    for cpu_id, rules in sorted(eligible(save).items())), reverse=True)
    return [cpu_id for _, cpu_id in keyed[:ENTRANTS]]


def fee(event):
    return int(event.settings.get("fee", 0))


def enter(save):
    """Enter this week's tournament at its place: the fee's taken now, and the bracket drawn. Raises ValueError."""
    event = tournament(save)
    if not event:
        raise ValueError("There's no tournament this week.")
    here = world.place_of(save)
    if event.place_id and (not here or here.pk != event.place_id):
        raise ValueError(f"Enter at the {event.place.name}.")
    allowed, why = registration(save, event)
    if not allowed:
        raise ValueError(why)
    if (problem := world.deck_problem(save)):
        raise ValueError(f"Your equipped deck can't duel yet: {problem[0].lower()}{problem[1:]}")
    if fee(event) > save.money:
        raise ValueError(f"The entry fee is {fee(event)} coins, and you have {save.money}.")
    entrants = draw_entrants(save, event)
    if len(entrants) < ENTRANTS:
        raise ValueError("There aren't enough duelists in town for a tournament this week.")
    save.money -= fee(event)
    found = record(save, event)
    found.update(entrants=entrants, results={}, out=None, prize=0)
    quests.event_done(save, event.key, "enter")
    world.changed(save, "money", "events", "quests")
    return found


def coin_flip(save, found, round_no, a, b):
    """Who wins a CPU-against-CPU match: a coin flip, seeded by the save, week, round and pair."""
    rng = random.Random(f"{save.seed}:{found['week']}:{round_no}:{min(a, b)}:{max(a, b)}")
    return rng.choice(sorted((a, b)))


def bracket(save, found):
    """[[(a, b, winner or None)] for each round]: seats are CPU ids, the player PLAYER. A CPU match always has its
    (coin-flip) winner; the player's has one once it's been played."""
    seats, rounds = [PLAYER] + list(found["entrants"]), []
    for round_no in range(len(ROUNDS)):
        matches = []
        for a, b in zip(seats[0::2], seats[1::2]):
            if PLAYER in (a, b):
                result = found["results"].get(str(round_no))
                winner = None if result is None else PLAYER if result == "won" else (b if a == PLAYER else a)
            elif a is None or b is None:
                winner = None
            else:
                winner = coin_flip(save, found, round_no, a, b)
            matches.append((a, b, winner))
        rounds.append(matches)
        seats = [winner for _, _, winner in matches]
    return rounds


def player_round(found):
    """The round the player plays next (0 to 2), or None: out, or champion."""
    if not found or found.get("out") is not None:
        return None
    played = len(found["results"])
    return played if played < len(ROUNDS) else None


def opponent(save, found=None, event=None):
    """The CPU the player's due to duel now (it's Sunday, at their round's time), or None."""
    event = event or tournament(save)
    found = found if found is not None else entry(save, event)
    round_no = player_round(found)
    if round_no is None or not is_sunday(save) or save.turn % TIMES != round_no:
        return None
    match = next(match for match in bracket(save, found)[round_no] if PLAYER in match[:2])
    return match[1] if match[0] == PLAYER else match[0]


def presence(save, turn):
    """{cpu id: place key} an event puts somewhere at this turn: the player's tournament opponent, at the arena for their
    round. Read by world.whereabouts (only for the save's own turn: a sample save's grid isn't asked)."""
    if turn != save.turn:
        return {}
    event = tournament(save)
    if not event or not event.place_id:
        return {}
    cpu_id = opponent(save, event=event)
    return {cpu_id: event.place.key} if cpu_id else {}


def prize_for(event, round_no, won):
    """The coins for finishing at this round: losing Round 1 pays nothing, the semi-final and final pay their prizes,
    and winning the final pays the champion's."""
    prizes = event.settings.get("prizes", {})
    if won and round_no == len(ROUNDS) - 1:
        return int(prizes.get("champion", 0))
    return int({1: prizes.get("semi", 0), 2: prizes.get("final", 0)}.get(round_no, 0))


def round_started(save, room):
    """A duel's begun: if it's the player's tournament round, it's that round's (its room is kept on the entry)."""
    event = tournament(save)
    found = entry(save, event) if event else None
    if found and opponent(save, found, event) == room.cpu_profile_id:
        found["live"] = room.pk
        return True
    return False


def is_round(save, room):
    found = entry(save)
    return bool(found and found.get("live") == room.pk)


def points(event):
    return int(event.settings.get("points", 0))


def finish_round(save, room, won):
    """A tournament round's duel is over: the result goes in the bracket, and a loss (or the final) pays its prize.
    Returns (coins, the words for the result banner, [reward words])."""
    event = tournament(save)
    found = entry(save, event)
    round_no = player_round(found)
    found.pop("live", None)
    found["results"][str(round_no)] = "won" if won else "lost"
    return settle(save, event, found, round_no, won)


def settle(save, event, found, round_no, won):
    """After a round: out (with the prize for how far the player got), through, or champion."""
    title, rewards = ROUND_TITLES[round_no], []
    if won:
        quests.event_done(save, event.key, "round")
    if won and round_no < len(ROUNDS) - 1:
        words = f"{event.name}: you won {title.lower() if round_no else title}. Next, {ROUNDS[round_no + 1]}."
        quests.news(save, words)
        return 0, words, rewards
    coins = prize_for(event, round_no, won)
    found.update(out=None if won else round_no, prize=coins, champion=won)
    save.money += coins
    if won:
        given = quests.give_rewards(save, SimpleNamespace(giver_id=None, giver=None),
                                    [{"pack": event.settings["champion_pack"]}] if event.settings.get("champion_pack") else [])
        rewards = [text for text, _ in given]
        words = f"{event.name}: you're the champion! +{coins:,} coins."
        quests.event_done(save, event.key, "win")
        sleeves.record(save.user_id, counts={"world_events": 1})
        champion_scene(save, event)
    elif coins:
        words = f"{event.name}: out in {ROUNDS[round_no]}. +{coins:,} coins for getting this far."
    else:
        words = f"{event.name}: out in {ROUNDS[round_no]}. Better luck next week."
    quests.news(save, words)
    return coins, words, rewards


def time_passing(save):
    """Before time passes: a tournament round the player didn't turn up for is a forfeit (a loss)."""
    event = tournament(save)
    found = entry(save, event) if event else None
    round_no = player_round(found)
    if round_no is None or not is_sunday(save) or save.turn % TIMES != round_no or found.get("live"):
        return
    found["results"][str(round_no)] = "forfeit"
    settle(save, event, found, round_no, False)


def board(save):
    """The tournament as the notice board shows it: the event, whether the player can enter (and why not), and their
    entry with the bracket so far (CPU results shown once their round's time has come)."""
    event = tournament(save)
    if not event:
        return None
    found = entry(save, event)
    allowed, why = registration(save, event)
    here = world.place_of(save)
    at_place = not event.place_id or (here is not None and here.pk == event.place_id)
    view = {**describe(event), "fee": fee(event), "prizes": event.settings.get("prizes", {}),
            "can_enter": allowed and at_place, "why": why if not allowed else "" if at_place else f"Enter at the {event.place.name}.",
            "entered": bool(found), "rounds": []}
    if not found:
        return view
    names = dict(CpuProfile.objects.filter(pk__in=found["entrants"]).values_list("pk", "name"))
    name = lambda seat: "You" if seat == PLAYER else names.get(seat, "?") if seat is not None else "…"
    sunday = calendar.weekday_of(save.turn) == SUNDAY
    for round_no, matches in enumerate(bracket(save, found)):
        shown = sunday and save.turn % TIMES > round_no  # a CPU match's result, once its round's time has passed
        view["rounds"].append({"title": ROUND_TITLES[round_no], "time": WorldSave.TIMES[round_no], "matches": [
            {"a": name(a), "b": name(b), "player": PLAYER in (a, b),
             "winner": name(winner) if winner is not None and (PLAYER in (a, b) or shown) else ""}
            for a, b, winner in matches]})
    round_no = player_round(found)
    view.update(out=found.get("out"), champion=bool(found.get("champion")), prize=found.get("prize", 0),
                next=ROUNDS[round_no] if round_no is not None else "", next_time=WorldSave.TIMES[round_no].lower() if round_no is not None else "",
                opponent=name(opponent_for(save, found, round_no)) if round_no is not None else "")
    return view


def opponent_for(save, found, round_no):
    """The player's opponent in a round, whatever the time (for the notice board): None if not known yet."""
    match = next((match for match in bracket(save, found)[round_no] if PLAYER in match[:2]), None)
    return None if match is None else match[1] if match[0] == PLAYER else match[0]


def round_label(save, cpu_id):
    """"Round 1" if this CPU is the player's tournament opponent now (the talk box says so on its Duel), else ""."""
    found = entry(save)
    if found and opponent(save, found) == cpu_id:
        return ROUND_TITLES[player_round(found)]
    return ""


def town_view(save):
    """What the town shows of events: today's (for the banner), and the notice board's link."""
    from django.urls import reverse
    return {"today": today(save), "url": reverse("weiss:world_events", args=[save.slot]),
            "date": calendar.date_label(save.turn), "season": calendar.season_of(save.turn)}


def champion_scene(save, event):
    """The prize-giving: the scene the event's settings name ("champion_scene"), if it's written, waits in the town. Not
    written yet: see docs/world-events-plan.md, "Writing to do"."""
    name = event.settings.get("champion_scene")
    scene = Scene.objects.filter(name__iexact=name).first() if name else None
    if scene and not save.flags.get("scene"):
        save.flags["scene"] = {"scene": scene.pk}


# ---------------------------------------------------------------- Timed quests' windows (weiss.quests)

def window_event(window):
    """The WorldEvent a timed quest's window follows: the event it names, or one made from its own calendar rules."""
    if window.get("event"):
        return WorldEvent.objects.filter(key=window["event"], enabled=True).first()
    return WorldEvent(weekdays=window.get("weekdays", []), times=window.get("times", []), every=window.get("every", 1),
                      offset=window.get("offset", 0))


def window_runs(window, turn):
    event = window_event(window)
    return bool(event) and runs(event, turn)


def window_turns(window, start, end):
    """The turns from start (up to end) that a window is open."""
    event = window_event(window)
    return [turn for turn in range(start, end) if runs(event, turn)] if event else []


def at_places(save):
    """{place key: [event icons]} for events on now that happen somewhere: the map marks those places."""
    found = {}
    for event in on(save):
        if event.place_id:
            found.setdefault(event.place.key, []).append({"icon": event.icon, "name": event.name})
    return found
