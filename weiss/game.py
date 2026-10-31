"""A two-player Weiss Schwarz virtual tabletop: game state, moves, and what each player may see.

There is no rule checking; players move their own cards like at a real table. The server's job
is to keep hidden things hidden (hands, deck and stock order) and to keep both boards in sync.

State is plain JSON, stored on the GameRoom:

    {"players": {"<user id>": {"name": ..., "zones": {zone: [card, ...]}, "stage": {slot: card|None},
                               "markers": {slot: [card, ...]}, "refreshes": n, "level_ups": n, "climaxes": n}},
     "order": [host id, guest id], "turn": "<user id>", "turn_number": 1, "phase": "mulligan", "log": [...],
     "mulligan_done": [user id, ...],  # during the mulligan: who has finished theirs
     "reveal": {"player": id, "uid": ..., "card": pk},  # a hand card shown to the opponent, until they close it
     "pending_end": id,  # the end phase waits for end of turn effects to resolve, then carries on
     "pending_discard": {"player": id, "count": n},  # the end phase waits for a hand over 7 to be discarded
     "pending_damage": {...},  # only while a cancelled damage waits to be cleaned up
     "pending_refresh": {...},  # only while a damage waits for the emptied deck to be refreshed
     "pending_climax": "<user id>",  # only while a climax just played shows before the attack phase
     "attacks": n,  # attacks made this turn (the first player's first turn allows only one)
     "attack": {"step": ...},  # during the attack phase (with turn rules on): the attack in progress
     "rules": bool,  # turn rules on (the default) or off (a free-form table), changed by both players agreeing
     "rules_request": {"player": id, "on": bool},  # one player has asked to turn the rules on or off
     "auto_next": phase,  # a phase that has ended itself: the turn player's page moves on to this
                          # one after a pause, so phase changes can be followed
     "game_number": n, "first_player": id,  # which game of a series of rematches this is, and who went first
     "rps": {"picks": {id: choice}, "last": {id: choice}, "winner": id},  # game 1's rock, paper, scissors for going first
     "game_over": {"winner": id, "loser": id, "reason": "level"|"deck", "rematch": [id, ...]},  # who lost and how; who's asked for a rematch
     "match_wins": {user id: n},  # games each player has won in this series of rematches
     "ability_queue": [...], "resolving": {...},  # card abilities to trigger, and the one running (see Abilities)
     "ability_show": {...},  # an ability just resolved: both pages show it, and play waits (see show_ability)
     "needs_color": {user id: {uid: color}},  # hand cards the color rule is holding back
     "buffs": [...], "stats": {uid: {"power", "soul"}}, "granted": {uid: [text]},  # what's boosting characters
     "acts": {user id: {uid: [...]}}, "used": [...]}  # what each ! button can do, and 1/TURN abilities used

With turn rules on, phases end themselves when there's nothing left to do in them, the page offers
only the shortcuts for the current phase, playing a card pays its cost and needs its color (see
color_needed), and the attack phase runs as
the rules' steps: declare (front, side or direct), trigger, counter, damage and battle.

A card instance is {"uid": "a1b2c3d4", "card": <Card pk>, "pos": "stand"|"rest"|"reverse",
"face_down": bool}. The top of a pile is the end of its list.

Markers are cards set under a character on the stage. Each slot's markers are a pile named
"marker:<slot>"; they move with the character between slots and go to the waiting room when it
leaves the stage.
"""
import copy
import random
import re
import secrets
from types import SimpleNamespace

from . import abilities

ZONES = ["deck", "hand", "clock", "level", "stock", "waiting", "memory", "climax", "resolution"]
STAGE_SLOTS = ["C1", "C2", "C3", "B1", "B2"]
MARKER = "marker:"
MARKER_PILES = [MARKER + slot for slot in STAGE_SLOTS]
HIDDEN_ZONES = {"deck", "stock"}  # face down: no one sees the cards (the owner can search or peek)
PRIVATE_ZONES = {"hand"}  # only the owner sees the cards
POSITIONS = {"stand", "rest", "reverse"}
STARTING_HAND = 5
HAND_LIMIT = 7  # cards a player may keep in hand at the end of their turn
ENCORE_COST = 3  # stock paid to keep a reversed character on the stage, rested
LEVEL_UP_AT = 7  # clock cards that make a level
LOSING_LEVEL = 4  # a player who reaches this level has lost
MAX_SET_POWER = 99999  # the most power a character can be set to by hand
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
CLOCK_DRAW = 2  # cards drawn after putting a card from the hand into the clock
PHASES = ["mulligan", "stand", "draw", "clock", "main", "climax", "attack", "encore", "end"]  # mulligan: turn 1 only
PLAY_ZONES = set(STAGE_SLOTS) | {"climax", "resolution"}  # playing a card from the hand here pays its cost
ATTACK_STEPS = ["declare", "trigger", "counter", "damage", "battle"]
ATTACK_KINDS = {"front", "side", "direct"}
TRIGGER_CHOICES = {"comeback": {"hand"}, "gate": {"hand"}, "choice": {"hand", "stock"},
                   "standby": set(STAGE_SLOTS), "treasure": set()}  # trigger icon -> where its card may go
OPPOSITE = {"C1": "C3", "C2": "C2", "C3": "C1"}  # the opponent's slot facing each center slot
BACKUP = re.compile(r"【COUNTER】\s*Backup\s*(\d+)(?:,\s*Level\s*(\d+))?(?:\s*\[\((\d+)\))?", re.I)
MAX_LOG = 100

LABELS = {
    "deck": "deck", "hand": "hand", "clock": "clock", "level": "level", "stock": "stock",
    "waiting": "waiting room", "memory": "memory", "climax": "climax zone", "resolution": "resolution zone",
    "C1": "center stage (left)", "C2": "center stage (middle)", "C3": "center stage (right)",
    "B1": "back stage (left)", "B2": "back stage (right)",
}
LABELS |= {MARKER + slot: f"markers under {LABELS[slot]}" for slot in STAGE_SLOTS}


class GameError(Exception):
    pass


def new_uid():
    return secrets.token_hex(4)


def new_card(card_pk):
    return {"uid": new_uid(), "card": card_pk, "pos": "stand", "face_down": False}


def new_game(players, shuffle=random.shuffle, match_wins=None, game_number=1, first=None, rps=False):
    """players: [(user id, display name, [card pk, ...]), ...] with the host first. The first turn is
    `first`'s (the host's if not given), unless `rps`: then the winner of rock, paper, scissors takes it.
    match_wins and game_number: where a series of rematches has got to."""
    first = str(first or players[0][0])
    state = {"players": {}, "order": [str(p[0]) for p in players], "turn": first, "first_player": first, "game_number": game_number,
             "turn_number": 1, "phase": "mulligan", "mulligan_done": [], "log": [],
             "match_wins": dict(match_wins or {})}
    for user_id, name, cards in players:
        deck = [new_card(pk) for pk in cards]
        shuffle(deck)
        zones = {zone: [] for zone in ZONES}
        zones["deck"] = deck
        zones["hand"] = [deck.pop() for _ in range(min(STARTING_HAND, len(deck)))]
        state["players"][str(user_id)] = {"name": name, "zones": zones, "stage": {s: None for s in STAGE_SLOTS},
                                          "markers": {s: [] for s in STAGE_SLOTS}}
    add_log(state, None, f"Game started. Each player shuffled and drew {STARTING_HAND} cards. "
                         "Mulligan: each player may swap any cards in their hand for new ones.")
    if rps:
        state["rps"] = {"picks": {}, "last": None, "winner": None}
    elif game_number > 1:
        add_log(state, first, f"goes first in game {game_number}")
    return state


def play_rps(state, player, choice):
    """One player's pick. Once both have picked: a tie goes again, and otherwise the winner takes the
    first turn, which both pages show until one of them sends "rps_done"."""
    rps = state["rps"]
    if choice not in RPS_BEATS:
        raise GameError("Choose rock, paper or scissors.")
    if rps["winner"] or player in rps["picks"]:
        raise GameError("You've already chosen.")
    rps["picks"][player] = choice
    if len(rps["picks"]) < len(state["order"]):
        return
    first, second = state["order"]
    picks = rps["picks"]
    names = f"{state['players'][first]['name']} chose {picks[first]}, {state['players'][second]['name']} chose {picks[second]}"
    rps["last"], rps["picks"] = picks, {}
    if picks[first] == picks[second]:
        add_log(state, None, f"Rock, paper, scissors: {names}. A tie, so again!")
        return
    winner = first if RPS_BEATS[picks[first]] == picks[second] else second
    rps["winner"] = winner
    state["turn"] = state["first_player"] = winner
    add_log(state, None, f"Rock, paper, scissors: {names}.")
    add_log(state, winner, "won and goes first")


def rps_view(state, player):
    """What this player sees of rock, paper, scissors: never the other pick until both are in."""
    rps = state.get("rps")
    if not rps:
        return None
    other = other_player(state, player)
    last = rps["last"]
    return {"mine": rps["picks"].get(player), "opponent_chose": other in rps["picks"],
            "last": {"me": last[player], "opponent": last[other]} if last else None,
            "won": rps["winner"] == player if rps["winner"] else None}


def add_log(state, player, text):
    who = state["players"][player]["name"] if player else ""
    state["log"].append({"who": who, "text": text})
    del state["log"][:-MAX_LOG]


# --- Finding and moving cards ---------------------------------------------------------------------

def pile(side, where):
    """The list of cards in a zone or a marker pile."""
    if where.startswith(MARKER):
        return side.setdefault("markers", {s: [] for s in STAGE_SLOTS})[where.removeprefix(MARKER)]
    return side["zones"][where]


def find(side, uid):
    """(where, index) of a card on one player's side; where is a zone name, a stage slot or a marker pile."""
    for zone, cards in side["zones"].items():
        for i, card in enumerate(cards):
            if card["uid"] == uid:
                return zone, i
    for slot, card in side["stage"].items():
        if card and card["uid"] == uid:
            return slot, None
    for slot, cards in side.get("markers", {}).items():
        for i, card in enumerate(cards):
            if card["uid"] == uid:
                return MARKER + slot, i
    raise GameError("That card isn't on your side of the board.")


def take(side, uid):
    where, index = find(side, uid)
    if where in STAGE_SLOTS:
        card, side["stage"][where] = side["stage"][where], None
    else:
        card = pile(side, where).pop(index)
    return card, where


def check_marker_target(side, to, leaving=None):
    """Markers need a character to go under (and not the one being moved)."""
    if to in MARKER_PILES:
        slot = to.removeprefix(MARKER)
        if side["stage"][slot] is None or slot == leaving:
            raise GameError("There's no character in that slot to put a marker under.")


def put(side, card, to, where="top", face_down=False):
    """Place a card in a zone, stage slot or marker pile. Returns whatever was already in that slot, if anything."""
    if to in STAGE_SLOTS:
        occupant, side["stage"][to] = side["stage"][to], card
        return occupant
    if to in MARKER_PILES:
        card["pos"] = "stand"
        card["face_down"] = bool(face_down)
        pile(side, to).append(card)
        return None
    if to not in ZONES:
        raise GameError(f"Unknown zone: {to}")
    card["pos"] = "stand"
    if to in HIDDEN_ZONES or to == "hand":
        card["face_down"] = False  # orientation is meaningless once the card is hidden
    cards = side["zones"][to]
    if where == "bottom":
        cards.insert(0, card)
    else:
        cards.append(card)
    return None


def is_public(where, card):
    return where not in HIDDEN_ZONES and where not in PRIVATE_ZONES and not card["face_down"]


def describe_move(card, src, dst, name):
    """Log text for a move, naming the card only when either end is face up for both players."""
    shown = is_public(src, card) or (is_public(dst, card) and dst != "hand")
    what = name(card["card"]) if shown else "a card"
    if src == "deck" and dst == "hand":
        return "took a card from their deck into their hand"
    return f"moved {what} from {LABELS[src]} to {LABELS[dst]}"


def discard_markers(state, player, slot):
    """A character left the stage: the markers under it go to the waiting room, face up."""
    side = state["players"][player]
    cards = pile(side, MARKER + slot)
    if not cards:
        return
    side["markers"][slot] = []
    for card in cards:
        put(side, card, "waiting")
        card["face_down"] = False
    add_log(state, player, f"put {len(cards)} marker{'s' if len(cards) != 1 else ''} from "
                           f"{LABELS[slot]} into the waiting room")


def swap_markers(side, a, b):
    """Characters moving between stage slots take their markers with them."""
    markers = side.setdefault("markers", {s: [] for s in STAGE_SLOTS})
    markers[a], markers[b] = markers.get(b, []), markers.get(a, [])


def resolve_damage(state):
    """Finish a damage that a climax cancelled: its cards leave the clock for the waiting room.

    Taking damage puts the cards in the clock at once; when one is a climax, the board shows that
    for a moment (the damaged player's page sends "resolve_damage" after half a second) and then
    this cleans it up. Any other action finishes it first too, so it never gets stuck.
    """
    pending = state.pop("pending_damage", None)
    if not pending:
        return
    player = pending["player"]
    side = state["players"][player]
    uids = set(pending["uids"])
    clock = side["zones"]["clock"]
    side["zones"]["clock"] = [c for c in clock if c["uid"] not in uids]
    for card in (c for c in clock if c["uid"] in uids):
        put(side, card, "waiting")
    add_log(state, player, f"negated {pending['amount']} damage: revealed the climax {pending['climax']} "
                           f"({len(uids)} card{'s' if len(uids) != 1 else ''} to the waiting room)")


def refresh(state, player, name, shuffle):
    """Deck out: the waiting room is shuffled into a new deck and its top card goes to the clock
    (refresh damage, which a climax doesn't cancel)."""
    side = state["players"][player]
    zones = side["zones"]
    cards, zones["waiting"] = zones["waiting"], []
    for card in cards:
        put(side, card, "deck")
    shuffle(zones["deck"])
    for card in zones["deck"]:
        card["uid"] = new_uid()
    damage = zones["deck"].pop()
    put(side, damage, "clock")
    side["refreshes"] = side.get("refreshes", 0) + 1  # so both pages can show "Deck Out!"
    add_log(state, player, f"decked out: shuffled {len(cards)} cards from the waiting room into their deck "
                           f"and put {name(damage['card'])} into their clock")


def deal_damage(state, player, amount, remaining, dealt, name, is_climax):
    """Deal the `remaining` part of an `amount` damage: cards go from the deck to the clock one at a
    time, stopping at a climax, which cancels the whole damage (see resolve_damage). `dealt` is the
    [uid, name] of each card this damage has already put in the clock.

    If the deck runs out with damage still to deal, this stops and leaves a pending refresh: the
    damaged player's page waits a moment and sends "continue_damage" (see continue_damage).
    """
    side = state["players"][player]
    deck = side["zones"]["deck"]
    while remaining and deck:
        card = deck.pop()
        put(side, card, "clock")
        dealt.append([card["uid"], name(card["card"])])
        remaining -= 1
        if is_climax(card["card"]):
            state["pending_damage"] = {"player": player, "uids": [uid for uid, _ in dealt],
                                       "amount": amount, "climax": name(card["card"])}
            return
        if remaining and not deck and side["zones"]["waiting"]:
            state["pending_refresh"] = {"player": player, "amount": amount, "remaining": remaining, "dealt": dealt}
            return
    names = ", ".join(n for _, n in dealt)
    short = f" (deck ran out after {len(dealt)})" if remaining else ""
    add_log(state, player, f"took {amount} damage{short}: {names}")


def continue_damage(state, name, shuffle, is_climax):
    """A damage emptied the deck partway: announce it, refresh, and deal the rest. Cards this damage
    already put in the clock stay part of it, so a climax revealed afterwards still sends them all
    to the waiting room; the refresh card stays in the clock."""
    pending = state.pop("pending_refresh", None)
    if not pending:
        return
    player = pending["player"]
    remaining = pending["remaining"]
    state["log"].append({"who": state["players"][player]["name"], "chat": True,
                         "text": f"My deck is empty, so my waiting room gets shuffled into a new deck. "
                                 f"{remaining} damage will remain after that."})
    refresh(state, player, name, shuffle)
    deal_damage(state, player, pending["amount"], remaining, pending["dealt"], name, is_climax)


# --- Actions ---------------------------------------------------------------------------------------

def count_arg(action, default=1, most=50):
    try:
        count = int(action.get("count", default))
    except (TypeError, ValueError):
        raise GameError("Count must be a number.")
    if not 1 <= count <= most:
        raise GameError(f"Count must be between 1 and {most}.")
    return count


def zone_arg(action, key, allowed):
    value = action.get(key)
    if value not in allowed:
        raise GameError(f"Can't use {value!r} there.")
    return value


def damage_in_progress(state, player):
    """A damage of this player's is still being worked out (a cancel showing, or a refresh to come)."""
    return player in (state.get("pending_damage", {}).get("player"), state.get("pending_refresh", {}).get("player"))


def must_level_up(state, player):
    """7 or more cards in the clock, once any damage being dealt is over: the player picks a level card."""
    return len(state["players"][player]["zones"]["clock"]) >= LEVEL_UP_AT and not damage_in_progress(state, player)


def stand_all(side, held=()):
    """Stand every character but any held back; True if any wasn't standing."""
    changed = False
    for card in side["stage"].values():
        if card and card["pos"] != "stand" and card["uid"] not in held:
            card["pos"] = "stand"
            changed = True
    return changed


def rules_on(state):
    return state.get("rules", True)


def other_player(state, player):
    return next(p for p in state["order"] if p != player)


def number(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def can_attack(state, player):
    """A standing center-stage character, and attacks left this turn (one on the very first turn)."""
    if state["turn_number"] == 1 and state.get("attacks", 0) >= 1:
        return False
    stage = state["players"][player]["stage"]
    return any(stage[s] and stage[s]["pos"] == "stand" for s in OPPOSITE)


def color_free(state, player, card, info):
    """Whether an ability lets this hand card skip the color rule: its own, or one in play for it.
    Outside the stage, an ability only counts if it says it works from where its card is."""
    env = SimpleNamespace(info=info)
    side = state["players"][player]
    for ability in abilities_of(state, card, env):
        if ability.get("color_free", {}).get("self") and all_met(ability, state, player, card, {}, env):
            return True
    sources = [(c, "stage") for c in stage_cards(side) if not c["face_down"]]
    sources += [(c, zone) for zone in ("level", "memory", "climax") for c in side["zones"][zone] if not c["face_down"]]
    for source, zone in sources:
        for ability in abilities_of(state, source, env):
            free = ability.get("color_free")
            if not free or "filter" not in free or not fits(free["filter"], card, env):
                continue
            if zone != "stage" and not any(cond["type"] == "self_in" for cond in ability["cond"]):
                continue
            if all_met(ability, state, player, source, {}, env):
                return True
    return False


def color_needed(state, player, card, info):
    """The color this card is missing under the color rule, or None if it can be played: with turn
    rules on, a climax or a card of level 1 or higher needs its color among the cards in its player's
    clock and level zone, unless an ability says otherwise. A card whose color isn't known is let through."""
    details = info(card["card"]) or {}
    color = details.get("color")
    if not color or not rules_on(state):
        return None
    if (details.get("card_type") or "").lower() != "climax" and number(details.get("level")) < 1:
        return None
    zones = state["players"][player]["zones"]
    if any((info(c["card"]) or {}).get("color") == color for c in zones["clock"] + zones["level"]):
        return None
    return None if color_free(state, player, card, info) else color


def counter_play(state, player, card, info):
    """(stock to pay, backup power) if this hand card can be played as a counter right now, else None:
    it says 【COUNTER】, its level is within the player's, and the stock covers it."""
    details = info(card["card"])
    text = details.get("text") or ""
    if "【COUNTER】" not in text.upper():
        return None
    backup = BACKUP.search(text)
    if backup:  # exempt from the color rule
        power, level, price = int(backup[1]), number(backup[2]), number(backup[3])
    else:
        if color_needed(state, player, card, info):
            return None
        power, level, price = 0, number(details.get("level")), number(details.get("cost"))
    zones = state["players"][player]["zones"]
    if level > len(zones["level"]) or price > len(zones["stock"]):
        return None
    return price, power


def counters_for(state, player, info):
    return [c["uid"] for c in state["players"][player]["zones"]["hand"] if counter_play(state, player, c, info)]


def declare_attack(state, player, slot, kind, env):
    """The declaration step of an attack: rest the attacker, then any abilities its attack triggers
    resolve before the trigger step (see trigger_check)."""
    side = state["players"][player]
    defender = other_player(state, player)
    card = side["stage"][slot]
    target = OPPOSITE[slot]
    opposing = state["players"][defender]["stage"][target]
    if opposing and kind not in ("front", "side"):
        raise GameError("There's a character in front of it: choose a front or side attack.")
    if not opposing and kind != "direct":
        raise GameError("There's no character in front of it, so it's a direct attack.")
    card["pos"] = "rest"
    state["attacks"] = state.get("attacks", 0) + 1
    attacker = env.name(card["card"]) if not card["face_down"] else "a character"
    add_log(state, player, f"{kind} attack with {attacker}"
            + (f" against {env.name(opposing['card'])}" if opposing else ""))
    # The damage this attack will deal: soul, +1 if direct, or minus the defender's level for a side
    # attack (update_attack_soul keeps it up to date, with the trigger's soul in soul_extra).
    state["attack"] = {"step": "trigger", "slot": slot, "uid": card["uid"], "target": target, "kind": kind,
                       "soul": 0, "soul_extra": 1 if kind == "direct" else 0, "backup": 0, "shot": False, "checking": True}
    fire(state, env, "attack", uid=card["uid"], card=card["card"], kind=kind, player=player, defender=defender,
         target=opposing["uid"] if opposing else None, target_card=opposing["card"] if opposing else None)
    if not abilities_busy(state):
        trigger_check(state, env)


def trigger_check(state, env):
    """The trigger step: check the top card of the deck for its trigger (soul icons add to this
    attack's damage; the card then goes to the stock, or a treasure to the hand), and set up the
    counter or damage step."""
    player = state["turn"]
    side = state["players"][player]
    zones = side["zones"]
    attack = state["attack"]
    attack.pop("checking", None)
    icons = []
    shown = []
    checks = attack.pop("checks", 1)
    for _ in range(checks):
        if not zones["deck"] and zones["waiting"]:
            refresh(state, player, env.name, env.shuffle)
        if not zones["deck"]:
            break
        checked = zones["deck"].pop()
        shown.append(checked["card"])
        found = (env.trigger(checked["card"]) or "").split()
        icons += found
        put(side, checked, "hand" if "treasure" in found else "stock")
        add_log(state, player, f"trigger check: {env.name(checked['card'])}"
                + (f" [{' '.join(found)}]" if found else " (no trigger)")
                + (" — to their hand" if "treasure" in found else " — to their stock"))
        fire(state, env, "check_card", uid=attack["uid"], player=player, card=checked["card"])
        if env.is_climax(checked["card"]):
            fire(state, env, "check_climax", uid=attack["uid"], player=player)
            fire(state, env, "climax_trigger", player=player, card=checked["card"])
    if attack.pop("check_pay", 0) and checks == 2 and zones["stock"]:
        put(side, zones["stock"].pop(), "waiting")
        add_log(state, player, "paid 1 stock for the second trigger check")
    if shown:  # both pages show what was checked; anything it triggered resolves after that
        state["ability_show"] = {"id": new_uid(), "player": player, "uid": attack["uid"], "card": shown[0], "text": "Trigger check",
                                 "targets": [], "check": shown}
    attack["soul_extra"] += icons.count("soul")
    attack["shot"] = "shot" in icons
    update_attack_soul(state, compute_stats(state, env)[0], env)
    prompt = trigger_prompt(state, player, icons, env.info)
    if prompt:
        attack["prompt"] = prompt  # the attacker chooses (see the trigger_choice action)
    else:
        after_trigger(state, env.info)


def trigger_prompt(state, player, icons, info):
    """The choice a trigger icon gives the attacker, as {"kind", "options": [waiting room uids]}, or
    None when it gives none (or there's nothing to choose from):
    comeback: a character from the waiting room to the hand; gate: a climax from the waiting room
    to the hand; choice: a character with a soul trigger from the waiting room to the hand or
    stock; standby: a character of at most level + 1 from the waiting room onto the stage, rested;
    treasure: whether to put the top card of the deck into the stock."""
    zones = state["players"][player]["zones"]
    kind = next((icon for icon in icons if icon in TRIGGER_CHOICES), None)
    if kind == "treasure":
        return {"kind": kind, "options": []} if zones["deck"] else None
    if not kind:
        return None
    level = len(zones["level"])

    def fits(card):
        details = info(card["card"])
        is_character = (details.get("card_type") or "").lower() == "character"
        return {
            "comeback": is_character,
            "gate": (details.get("card_type") or "").lower() == "climax",
            "choice": is_character and "soul" in (details.get("trigger") or "").split(),
            "standby": is_character and number(details.get("level")) <= level + 1,
        }[kind]

    options = [c["uid"] for c in zones["waiting"] if fits(c)]
    return {"kind": kind, "options": options} if options else None


def bars_backups(state, uid, info):
    """Whether this character, attacking or defending, says no Backups can be played during its battle."""
    card = locate(state, uid)[1]
    return bool(card) and any(ability.get("no_backup") for ability in abilities_of(state, card, SimpleNamespace(info=info)))


def find_card(side, uid):
    where, index = find(side, uid)
    return side["stage"][where] if where in STAGE_SLOTS else pile(side, where)[index]


def after_trigger(state, info):
    """The trigger step is done: on to the counter step (if the defender can counter a front or side
    attack) or the damage step."""
    attack = state["attack"]
    attack["step"] = "damage"
    if attack["kind"] != "direct":
        counters = counters_for(state, other_player(state, state["turn"]), info)
        defender = state["players"][other_player(state, state["turn"])]
        if attack["kind"] == "front" and (bars_backups(state, attack["uid"], info) or bars_backups(state, (defender["stage"][attack["target"]] or {}).get("uid"), info)):
            add_log(state, state["turn"], "no Backups can be played in this battle")
            counters = [uid for uid in counters if not BACKUP.search(info(find_card(defender, uid)["card"]).get("text") or "")]
        if counters:
            attack.update(step="counter", counters=counters)


def end_attack(state, env):
    uid = (state.get("attack") or {}).get("uid")
    state["attack"] = {"step": "declare"}
    if uid:
        fire(state, env, "attack_end", uid=uid)


def advance_attack(state, env):
    """Move the attack phase along while nobody has a choice to make: deal an attack's damage once
    its counter step is over, battle once that damage (and any level up) is done, and end the
    phase when the turn player has no attack left to make. Abilities resolve first."""
    while rules_on(state) and state.get("phase") == "attack" and state.get("attack"):
        if abilities_busy(state):
            return
        attack = state["attack"]
        player = state["turn"]
        defender = other_player(state, player)
        step = attack["step"]
        if step == "declare":
            if not can_attack(state, player) and state.get("auto_next") != "encore":
                add_log(state, player, "no attacks left")
                state["auto_next"] = "encore"
            return
        if step == "trigger" and attack.get("checking"):
            trigger_check(state, env)
            continue
        if step in ("trigger", "counter"):
            return  # the attacker resolves a trigger, or the defender plays a counter or passes
        if step == "damage":
            if not attack.get("dealt"):
                update_attack_soul(state, compute_stats(state, env)[0], env)
                attack["dealt"] = True
                if attack["soul"]:
                    deal_damage(state, defender, attack["soul"], attack["soul"], [], env.name, env.is_climax)
                    attack["cancelled"] = state.get("pending_damage", {}).get("player") == defender
                else:
                    add_log(state, defender, "took no damage")
                continue
            if damage_in_progress(state, defender) or must_level_up(state, defender):
                return  # the damage or a level up is still being worked out
            if not attack.get("cancel_fired"):
                attack["cancel_fired"] = True
                if attack.get("cancelled"):
                    fire(state, env, "cancel", uid=attack["uid"])
                if attack["soul"]:
                    fire(state, env, "damage_result", uid=attack["uid"], defender=defender, cancelled=bool(attack.get("cancelled")))
                if abilities_busy(state):
                    continue
            if attack.pop("shot", False) and attack.get("cancelled"):
                # Shot trigger: this attack's damage was cancelled, so it deals 1 damage more.
                add_log(state, player, "shot trigger: 1 more damage")
                deal_damage(state, defender, 1, 1, [], env.name, env.is_climax)
                continue
            if attack["kind"] == "front":
                attack["step"] = "battle"
            else:
                end_attack(state, env)
            continue
        if step == "battle":
            attacker = state["players"][player]["stage"][attack["slot"]]
            target = state["players"][defender]["stage"][attack["target"]]
            if attacker and target and attacker["uid"] == attack["uid"]:
                stats = compute_stats(state, env)[0]
                mine = stats[attacker["uid"]]["power"]
                theirs = stats[target["uid"]]["power"] + attack["backup"]
                losers = ([attacker] if mine <= theirs else []) + ([target] if theirs <= mine else [])
                losers = [card for card in losers if not has_status(state, card["uid"], "no_reverse")]
                for card in losers:
                    card["pos"] = "reverse"
                add_log(state, player, f"battle: {env.name(attacker['card'])} ({mine}) against {env.name(target['card'])} ({theirs})"
                        + " — " + (", ".join(f"{env.name(c['card'])} reversed" for c in losers) or "neither reversed"))
                for card in losers:
                    other = target if card is attacker else attacker
                    fire(state, env, "reverse", uid=card["uid"], by=other["uid"], by_card=other["card"], by_owner=defender if card is attacker else player,
                         card=card["card"], owner=player if card is attacker else defender)
            end_attack(state, env)
            continue
        return


def reversed_characters(state):
    """Whether any reversed character, on either side, still needs an encore or the waiting room."""
    return any(card and card["pos"] == "reverse"
               for side in state["players"].values() for card in side["stage"].values())


def draw_step(state, player, name, shuffle):
    """The draw phase's card."""
    side = state["players"][player]
    zones = side["zones"]
    if not zones["deck"] and zones["waiting"]:
        refresh(state, player, name, shuffle)
    if zones["deck"]:
        put(side, zones["deck"].pop(), "hand")
        add_log(state, player, "draw phase: drew a card")
    else:
        add_log(state, player, "draw phase: no cards left to draw")


def enter_phase(state, player, phase, env):
    """Move the turn player into a phase. With turn rules on, the draw phase draws a card and ends
    itself; the end phase clears the climax zone and passes the turn into the next player's stand
    phase, which stands their characters and ends itself. ("Ends itself" sets auto_next.)
    Other phases only change what the page offers, and any abilities they trigger are queued."""
    name, shuffle = env.name, env.shuffle
    side = state["players"][player]
    zones = side["zones"]
    rules = rules_on(state)
    state["phase"] = phase
    for key in ("pending_climax", "attack", "auto_next"):
        state.pop(key, None)
    if phase == "attack" and rules:
        state["attack"] = {"step": "declare"}
    if phase == "draw" and rules:
        add_log(state, player, "moved to the draw phase")
        if state["turn_number"] <= len(state["order"]):
            fire(state, env, "phase", phase="first_turn", player=player)
        fire(state, env, "phase", phase="draw", player=player)
        draw_step(state, player, name, shuffle)
        state["auto_next"] = "clock"
    elif phase == "end":
        if rules:
            fire(state, env, "phase", phase="end", player=player)
            if abilities_busy(state):  # end of turn effects first; see finish_end_phase
                state["pending_end"] = player
                add_log(state, player, "moved to the end phase")
                return
        finish_end_phase(state, player, env)
    else:
        add_log(state, player, f"moved to the {phase} phase")
        if rules and phase in ("clock", "main", "climax", "attack", "encore"):
            fire(state, env, "phase", phase=phase, player=player)


def finish_end_phase(state, player, env):
    """The end phase after any end of turn effects: discard down to the hand limit (the turn waits
    for the "discard" action if that's needed), then the turn ends. Effects come first because they can
    change the hand, and because what lasts "until end of turn" still holds while they resolve."""
    zones = state["players"][player]["zones"]
    if rules_on(state) and len(zones["hand"]) > HAND_LIMIT:
        state["pending_discard"] = {"player": player, "count": len(zones["hand"]) - HAND_LIMIT}
        add_log(state, player, f"moved to the end phase: must discard down to {HAND_LIMIT} cards")
        return
    finish_turn(state, player, env.name)


def resume_end_phase(state, env):
    """The end of turn effects are all resolved: the end phase carries on."""
    if state.get("pending_end") and not abilities_busy(state):
        finish_end_phase(state, state.pop("pending_end"), env)


def finish_turn(state, player, name):
    """The rest of the end phase: the climax zone empties into the waiting room and the turn passes
    to the other player, whose stand phase (with turn rules on) stands their characters and ends
    itself."""
    side = state["players"][player]
    zones = side["zones"]
    rules = rules_on(state)
    climaxes, zones["climax"] = zones["climax"], []
    for card in climaxes:
        put(side, card, "waiting")
        card["face_down"] = False
    if climaxes:
        add_log(state, player, "put " + ", ".join(name(c["card"]) for c in climaxes)
                + " from the climax zone into the waiting room")
    other = next(p for p in state["order"] if p != player)
    state["turn"] = other
    state["buffs"] = [buff for buff in state.get("buffs", []) if buff["expires"] > state["turn_number"]]
    state["delayed"] = state.get("delayed", [])
    state["used"] = []
    state["turn_number"] += 1
    state["attacks"] = 0
    add_log(state, player, f"ended their turn. Turn {state['turn_number']}: {state['players'][other]['name']}")
    state["phase"] = "stand"
    if rules:
        held = {b["uid"] for b in state.get("buffs", []) if b.get("status") == "no_stand"}
        if stand_all(state["players"][other], held):
            add_log(state, other, "stand phase: stood all their characters")
        state["auto_next"] = "draw"


def auto_end_encore(state, name, shuffle):
    """The encore step is over once no reversed characters are left: the turn moves to its end."""
    if rules_on(state) and state.get("phase") == "encore" and not reversed_characters(state) and not abilities_busy(state):
        state["auto_next"] = "end"


def check_game_over(state):
    """A player at level 4 has lost, whatever got them there. So has one, with turn rules on, whose
    deck is out with no waiting room to refresh it from (once any damage of theirs is over: a cancelled
    damage's cards are about to reach the waiting room). Everything in progress stops."""
    if state.get("game_over"):
        return
    for player, side in state["players"].items():
        zones = side["zones"]
        reason = "level" if len(zones["level"]) >= LOSING_LEVEL else None
        if (not reason and rules_on(state) and state.get("phase") != "mulligan" and not zones["deck"]
                and not zones["waiting"] and not damage_in_progress(state, player)):
            reason = "deck"
        if reason:
            winner = other_player(state, player)
            state["game_over"] = {"winner": winner, "loser": player, "reason": reason, "rematch": []}
            wins = state.setdefault("match_wins", {})
            wins[winner] = wins.get(winner, 0) + 1
            for key in ("ability_queue", "resolving", "ability_show", "attack", "auto_next", "pending_end", "pending_damage", "pending_refresh",
                        "pending_climax", "pending_discard", "reveal", "rules_request"):
                state.pop(key, None)
            add_log(state, player, (f"reached level {LOSING_LEVEL}" if reason == "level" else "can't refresh their deck")
                    + f": {state['players'][winner]['name']} wins!")
            return


def rematch_agreed(state):
    """Both players have asked for a rematch: whoever holds the decks (play.py) deals the new game."""
    return len((state.get("game_over") or {}).get("rematch", [])) == len(state["order"])


def auto_refresh(state, name, shuffle):
    """Whenever a player's deck is empty and their waiting room isn't, they deck out at once, unless
    a damage of theirs is still being worked out (that refreshes, or resolves, first)."""
    for player, side in state["players"].items():
        if not damage_in_progress(state, player) and not side["zones"]["deck"] and side["zones"]["waiting"]:
            refresh(state, player, name, shuffle)


def played(state, player, card, to, env):
    """A card just played from the hand: what that triggers."""
    if to in STAGE_SLOTS:
        card["played_turn"] = state["turn_number"]
        fire(state, env, "play", uid=card["uid"], source=card, source_owner=player)
    elif to == "climax":
        fire(state, env, "climax", uid=card["uid"], source=card, source_owner=player, player=player, card=card["card"])
    elif to == "resolution" and rules_on(state):
        if (env.info(card["card"]).get("card_type") or "").lower() == "event":
            fire(state, env, "event", player=player)
        for ability in abilities.parse(env.info(card["card"]).get("text")):
            if ability["kind"] == "event" and ability["steps"]:
                queue_event(state, player, card, ability, env)


def apply(state, player, action, name=lambda pk: f"card {pk}", shuffle=random.shuffle,
          is_climax=lambda pk: False, trigger=lambda pk: "", cost=lambda pk: 0, info=lambda pk: {}):
    """Apply one player's action to the state in place. Returns extra data for that player only
    (e.g. the cards they searched), or {}. Raises GameError for anything invalid.

    `info` gives a card's details for the rules (power, soul, level, cost, text)."""
    env = SimpleNamespace(name=name, shuffle=shuffle, is_climax=is_climax, trigger=trigger, cost=cost, info=info)
    extra = apply_action(state, player, action, env)
    check_game_over(state)
    if state.get("game_over"):
        refresh_stats(state, env)
        return extra
    auto_refresh(state, name, shuffle)
    refresh_stats(state, env)
    run_abilities(state, env)
    resume_end_phase(state, env)
    refresh_stats(state, env)
    advance_attack(state, env)
    auto_end_encore(state, name, shuffle)
    check_game_over(state)
    refresh_stats(state, env)
    return extra


def apply_action(state, player, action, env):
    name, shuffle, is_climax, trigger, cost, info = env.name, env.shuffle, env.is_climax, env.trigger, env.cost, env.info
    player = str(player)
    if player not in state["players"]:
        raise GameError("You're not playing in this game.")
    side = state["players"][player]
    side.setdefault("markers", {s: [] for s in STAGE_SLOTS})  # games started before markers existed
    zones = side["zones"]
    kind = action.get("type")

    # A cancelled damage, or one waiting on a refresh, is always finished before anything else happens.
    resolve_damage(state)
    continue_damage(state, name, shuffle, is_climax)
    if kind in ("resolve_damage", "continue_damage"):
        return {}

    if kind == "rps_done":
        # Either page may send this; the other's copy finds it already done.
        if (state.get("rps") or {}).get("winner"):
            state.pop("rps")
        return {}
    if kind == "rps":
        if not state.get("rps"):
            raise GameError("Rock, paper, scissors is over.")
        play_rps(state, player, action.get("choice"))
        return {}
    if state.get("rps") and kind != "chat":
        if action.get("auto"):
            return {}
        raise GameError("Finish rock, paper, scissors first.")

    over = state.get("game_over")
    if kind == "rematch":
        if not over:
            raise GameError("The game isn't over.")
        if player not in over["rematch"]:
            over["rematch"].append(player)
            add_log(state, player, "asked for a rematch")
        return {}
    if over and kind != "chat":
        if action.get("auto") or kind == "ability_show_done":
            return {}  # a page's timer that hadn't heard yet
        raise GameError("The game is over.")

    if kind == "move":
        to = zone_arg(action, "to", set(ZONES) | set(STAGE_SLOTS) | set(MARKER_PILES))
        src, index = find(side, action.get("uid", ""))
        check_marker_target(side, to, leaving=src)
        if src == "hand" and to in PLAY_ZONES:
            missing = color_needed(state, player, zones["hand"][index], info)
            if missing:
                raise GameError(f"That card needs {missing} in your clock or level zone.")
        if (action.get("end_main") and to == "climax" and src == "hand" and rules_on(state)
                and state["turn"] == player and state.get("phase") == "main"):
            # A climax played from the main phase (the page asks first): that ends the main phase,
            # so it's played in the climax phase, and the attack phase follows.
            enter_phase(state, player, "climax", env)
        # Playing a card from the hand pays its cost from the stock.
        price = ((cost(zones["hand"][index]["card"]) or 0)
                 if rules_on(state) and src == "hand" and to in PLAY_ZONES else 0)
        if price > len(zones["stock"]):
            raise GameError(f"That card costs {price}; you have {len(zones['stock'])} stock.")
        card, src = take(side, action.get("uid", ""))
        occupant = put(side, card, to, action.get("where", "top"), face_down=action.get("face_down"))
        for _ in range(price):
            put(side, zones["stock"].pop(), "waiting")
        if src in STAGE_SLOTS and to in STAGE_SLOTS:
            swap_markers(side, src, to)
            if occupant:  # moving between stage slots swaps the two cards
                side["stage"][src] = occupant
        else:
            if occupant:  # playing onto an occupied slot sends the old card (and its markers) to the waiting room
                put(side, occupant, "waiting")
                add_log(state, player, f"sent {name(occupant['card'])} to the waiting room")
                discard_markers(state, player, to)
                fire(state, env, "leave", uid=occupant["uid"], source=occupant, source_owner=player, slot=to)
            if src in STAGE_SLOTS:
                discard_markers(state, player, src)
                if to == "waiting":
                    fire(state, env, "leave", uid=card["uid"], source=card, source_owner=player, slot=src)
        add_log(state, player, describe_move(card, src, to, name)
                + (f" (paid {price} stock)" if price else ""))
        if to == "climax" and rules_on(state) and state["turn"] == player and state.get("phase") == "climax":
            # Played in the climax phase: both pages show it, then the turn player's page moves on
            # to the attack phase.
            side["climaxes"] = side.get("climaxes", 0) + 1
            state["pending_climax"] = player
        if src == "hand":
            played(state, player, card, to, env)
        return {}

    if kind == "move_top":
        src = zone_arg(action, "from", HIDDEN_ZONES)
        to = zone_arg(action, "to", set(ZONES) | set(STAGE_SLOTS) | set(MARKER_PILES))
        check_marker_target(side, to)
        count = count_arg(action)
        if to in STAGE_SLOTS:
            count = 1
        if len(zones[src]) < count:
            raise GameError(f"Your {LABELS[src]} only has {len(zones[src])} cards.")
        bottom = action.get("where") == "bottom"
        moved = []
        for _ in range(count):
            card = zones[src].pop(0 if bottom else -1)
            occupant = put(side, card, to, face_down=action.get("face_down"))
            if occupant:
                put(side, occupant, "waiting")
                discard_markers(state, player, to)
            moved.append(card)
        end = "bottom" if bottom else "top"
        if src == "deck" and to == "hand" and not bottom:
            add_log(state, player, f"drew {count} card{'s' if count != 1 else ''}")
        elif is_public(to, moved[0]):
            names = ", ".join(name(c["card"]) for c in moved)
            add_log(state, player, f"put the {end} {count} of their {LABELS[src]} into {LABELS[to]}: {names}")
        else:
            add_log(state, player, f"moved the {end} {count} of their {LABELS[src]} to {LABELS[to]}")
        return {}

    if kind == "move_all":
        src = zone_arg(action, "from", (set(ZONES) - HIDDEN_ZONES - PRIVATE_ZONES) | set(MARKER_PILES))
        to = zone_arg(action, "to", set(ZONES))
        cards = list(pile(side, src))
        pile(side, src).clear()
        for card in cards:
            put(side, card, to)
            if to not in HIDDEN_ZONES and to != "hand":
                card["face_down"] = False
        if to == "deck":
            shuffle(zones["deck"])
            for card in zones["deck"]:
                card["uid"] = new_uid()
        add_log(state, player, f"moved all {len(cards)} cards from {LABELS[src]} to {LABELS[to]}"
                + (" and shuffled" if to == "deck" else ""))
        return {}

    if kind == "position":
        pos = zone_arg(action, "pos", POSITIONS)
        where, _ = find(side, action.get("uid", ""))
        if where not in STAGE_SLOTS:
            raise GameError("Only cards on the stage can be rested or reversed.")
        card = side["stage"][where]
        card["pos"] = pos
        verb = {"stand": "stood", "rest": "rested", "reverse": "reversed"}[pos]
        add_log(state, player, f"{verb} {name(card['card'])}")
        if pos == "reverse":
            fire(state, env, "reverse", uid=card["uid"], owner=player, card=card["card"])
        return {}

    if kind == "flip":
        where, index = find(side, action.get("uid", ""))
        if where in HIDDEN_ZONES or where in PRIVATE_ZONES:
            raise GameError("Cards there are already hidden.")
        card = side["stage"][where] if where in STAGE_SLOTS else pile(side, where)[index]
        card["face_down"] = not card["face_down"]
        add_log(state, player, f"turned a card in their {LABELS[where]} face {'down' if card['face_down'] else 'up'}")
        return {}

    if kind == "set_power":
        # For when an ability isn't doing what it should: this character's power, until the end of the turn.
        where, _ = find(side, action.get("uid", ""))
        if where not in STAGE_SLOTS:
            raise GameError("Only characters on the stage have power to set.")
        card = side["stage"][where]
        state["buffs"] = [b for b in state.get("buffs", []) if not (b["uid"] == card["uid"] and "set_power" in b)]
        if action.get("clear"):
            add_log(state, player, f"put the power of {name(card['card'])} back to normal")
            return {}
        try:
            power = int(action.get("count"))
        except (TypeError, ValueError):
            raise GameError("Power must be a number.")
        if not 0 <= power <= MAX_SET_POWER:
            raise GameError(f"Power must be between 0 and {MAX_SET_POWER}.")
        state["buffs"].append({"uid": card["uid"], "set_power": power, "expires": state["turn_number"]})
        add_log(state, player, f"set the power of {name(card['card'])} to {power} until the end of the turn")
        return {}

    if kind == "stand_all":
        stand_all(side)
        add_log(state, player, "stood all their characters")
        if rules_on(state) and state["turn"] == player and state.get("phase") == "stand":
            state["auto_next"] = "draw"  # that's the stand phase done
        return {}

    if kind == "shuffle":
        shuffle(zones["deck"])
        for card in zones["deck"]:
            card["uid"] = new_uid()  # so the opponent can't follow a card through the shuffle
        add_log(state, player, "shuffled their deck")
        return {}

    if kind in ("search", "peek"):
        deck = zones["deck"]
        if kind == "peek":
            count = min(count_arg(action), len(deck))
            cards = list(reversed(deck[-count:])) if count else []
            add_log(state, player, f"looked at the top {count} of their deck")
        else:
            cards = list(reversed(deck))
            add_log(state, player, "searched their deck")
        return {"revealed": {"zone": "deck", "title": "Top of your deck" if kind == "peek" else "Your deck",
                             "cards": [dict(c) for c in cards]}}

    if kind == "attack":
        # Rest a standing center-stage character and do its trigger check: the top card of the
        # deck goes face up to the resolution zone.
        where, _ = find(side, action.get("uid", ""))
        if where not in ("C1", "C2", "C3"):
            raise GameError("Only characters on the center stage can attack.")
        card = side["stage"][where]
        if card["pos"] != "stand":
            raise GameError("That character is already rested.")
        if rules_on(state):
            if state["turn"] != player or state.get("phase") != "attack":
                raise GameError("Attacks happen in your attack phase.")
            if (state.get("attack") or {}).get("step") != "declare":
                raise GameError("Finish the attack in progress first.")
            if abilities_busy(state):
                raise GameError("Finish resolving the abilities first.")
            if not can_attack(state, player):
                raise GameError("Only one character can attack on the first turn.")
            declare_attack(state, player, where, action.get("kind"), env)
            return {}
        state["attacks"] = state.get("attacks", 0) + 1
        card["pos"] = "rest"
        attacker = name(card["card"]) if not card["face_down"] else "a character"
        if not zones["deck"]:
            add_log(state, player, f"attacked with {attacker} (no cards left in the deck for a trigger check)")
            return {}
        checked = zones["deck"].pop()
        put(side, checked, "resolution")
        icons = trigger(checked["card"])
        add_log(state, player, f"attacked with {attacker} — trigger check: {name(checked['card'])}"
                               + (f" [{icons}]" if icons else " (no trigger)"))
        return {}

    if kind == "mulligan":
        # Turn 1, before the first stand phase: put any of the hand into the waiting room and draw
        # as many. Once both players have, the first player's turn begins.
        if state.get("phase") != "mulligan":
            raise GameError("The mulligan is only at the start of the game.")
        done = state.setdefault("mulligan_done", [])
        if player in done:
            raise GameError("You've already done your mulligan.")
        uids = list(dict.fromkeys(action.get("uids") or []))
        hand_uids = {c["uid"] for c in zones["hand"]}
        if not set(uids) <= hand_uids:
            raise GameError("Those cards aren't all in your hand.")
        for uid in uids:
            card, _ = take(side, uid)
            put(side, card, "waiting")
        for _ in range(min(len(uids), len(zones["deck"]))):
            put(side, zones["deck"].pop(), "hand")
        add_log(state, player, f"mulliganed {len(uids)} card{'s' if len(uids) != 1 else ''}" if uids else "kept their hand")
        done.append(player)
        if len(done) == len(state["order"]):
            state["phase"] = "stand"
            add_log(state, state["turn"], "moved to the stand phase")
            if rules_on(state):
                state["auto_next"] = "draw"
        return {}

    if kind == "discard":
        # The end phase's discard step: exactly enough cards from the hand to get down to 7.
        pending = state.get("pending_discard")
        if not pending or pending["player"] != player:
            raise GameError("You don't need to discard right now.")
        uids = list(dict.fromkeys(action.get("uids") or []))
        if len(uids) != pending["count"] or not set(uids) <= {c["uid"] for c in zones["hand"]}:
            raise GameError(f"Choose {pending['count']} card{'s' if pending['count'] != 1 else ''} from your hand.")
        cards = [take(side, uid)[0] for uid in uids]
        for card in cards:
            put(side, card, "waiting")
        add_log(state, player, "discarded " + ", ".join(name(c["card"]) for c in cards))
        state.pop("pending_discard")
        finish_turn(state, player, name)
        return {}

    if kind == "reveal":
        # Show a hand card to the opponent; the turn doesn't move on until they close it.
        if state.get("reveal"):
            raise GameError("Wait until the last revealed card has been closed.")
        where, index = find(side, action.get("uid", ""))
        if where != "hand":
            raise GameError("Only cards in your hand can be revealed.")
        card = zones["hand"][index]
        state["reveal"] = {"player": player, "uid": card["uid"], "card": card["card"]}
        add_log(state, player, f"revealed {name(card['card'])} from their hand")
        return {}

    if kind == "close_reveal":
        reveal = state.get("reveal")
        if not reveal or reveal["player"] == player:
            raise GameError("There's no revealed card for you to close.")
        state.pop("reveal")
        return {}

    if kind == "trigger_choice":
        # The attacker resolving a trigger's choice (see trigger_prompt): a waiting room card to
        # where the trigger allows, the treasure's top card to the stock, or nothing.
        attack = state.get("attack") or {}
        prompt = attack.get("prompt")
        if attack.get("step") != "trigger" or not prompt or player != state["turn"]:
            raise GameError("There's no trigger to resolve right now.")
        if state.get("ability_show"):
            raise GameError("Wait for the trigger check to finish showing.")
        trigger_kind = prompt["kind"]
        uid = action.get("uid")
        if trigger_kind == "treasure":
            if action.get("accept") and zones["deck"]:
                put(side, zones["deck"].pop(), "stock")
                add_log(state, player, "treasure trigger: put the top card of their deck into their stock")
            else:
                add_log(state, player, "treasure trigger: kept their deck as it is")
        elif uid:
            to = action.get("to")
            if uid not in prompt["options"] or to not in TRIGGER_CHOICES[trigger_kind]:
                raise GameError("That's not one of this trigger's choices.")
            card, _ = take(side, uid)
            occupant = put(side, card, to)
            if to in STAGE_SLOTS:
                card["pos"] = "rest"
                if occupant:
                    put(side, occupant, "waiting")
                    discard_markers(state, player, to)
            add_log(state, player, f"{trigger_kind} trigger: put {name(card['card'])} into their {LABELS[to]}")
        else:
            add_log(state, player, f"{trigger_kind} trigger: chose nothing")
        attack.pop("prompt")
        after_trigger(state, info)
        return {}

    if kind in ("counter", "no_counter"):
        # The defender's counter step: play one counter from the hand (paying for it; a backup's
        # power counts in the battle), or pass.
        attack = state.get("attack") or {}
        if attack.get("step") != "counter" or player == state["turn"]:
            raise GameError("There's no counter step for you right now.")
        if abilities_busy(state):
            raise GameError("Finish resolving the abilities first.")
        if kind == "counter":
            where, index = find(side, action.get("uid", ""))
            play = counter_play(state, player, zones["hand"][index], info) if where == "hand" else None
            if not play or action.get("uid") not in attack.get("counters", []):
                raise GameError("That card can't be played as a counter now.")
            price, power = play
            card = zones["hand"].pop(index)
            for _ in range(price):
                put(side, zones["stock"].pop(), "waiting")
            put(side, card, "waiting")
            attack["backup"] += power
            add_log(state, player, f"countered with {name(card['card'])}"
                    + (f" (+{power} power)" if power else "") + (f", paying {price} stock" if price else ""))
            fire(state, env, "backup", uid=card["uid"], source=card, source_owner=player)
            for ability in abilities.parse(info(card["card"]).get("text")):
                if ability["kind"] == "counter":
                    queue_event(state, player, card, ability, env)
        else:
            add_log(state, player, "didn't counter")
        attack["step"] = "damage"
        attack.pop("counters", None)
        return {}

    if kind == "rules_request":
        # Ask the other player to turn the turn rules off (or back on); see rules_answer.
        on = not rules_on(state)
        state["rules_request"] = {"player": player, "on": on}
        add_log(state, player, f"asked to turn the turn rules {'on' if on else 'off'}")
        return {}

    if kind == "rules_answer":
        request = state.get("rules_request")
        if not request:
            raise GameError("Nobody has asked to change the turn rules.")
        if request["player"] == player:  # the asker taking it back
            state.pop("rules_request")
            add_log(state, player, "withdrew their request to change the turn rules")
            return {}
        state.pop("rules_request")
        if not action.get("accept"):
            add_log(state, player, "kept the turn rules as they are")
            return {}
        state["rules"] = request["on"]
        if not request["on"] and state.get("pending_discard"):  # no longer required: the turn ends
            finish_turn(state, state.pop("pending_discard")["player"], name)
        state.pop("attack", None)
        state.pop("pending_climax", None)
        state.pop("ability_queue", None)
        state.pop("resolving", None)
        state.pop("ability_show", None)
        if request["on"] and state.get("phase") == "attack":
            state["attack"] = {"step": "declare"}
        add_log(state, player, f"agreed: turn rules are now {'on' if request['on'] else 'off'}")
        return {}

    if kind == "clock_draw":
        # Put a card from the hand into the clock, then draw 2 (refreshing if the deck runs out).
        where, index = find(side, action.get("uid", ""))
        if where != "hand":
            raise GameError("Only cards in your hand can be clocked to draw.")
        card = zones["hand"].pop(index)
        put(side, card, "clock")
        drawn = 0
        for _ in range(CLOCK_DRAW):
            if not zones["deck"] and zones["waiting"]:
                refresh(state, player, name, shuffle)
            if not zones["deck"]:
                break
            put(side, zones["deck"].pop(), "hand")
            drawn += 1
        add_log(state, player, f"put {name(card['card'])} into their clock and drew {drawn} card{'s' if drawn != 1 else ''}")
        if rules_on(state) and state["turn"] == player and state.get("phase") == "clock":
            state["auto_next"] = "main"  # that's the clock phase done
        return {}

    if kind == "level_up":
        # Level up: one of the first 7 clock cards goes to the level zone, the other 6 to the waiting room.
        if not must_level_up(state, player):
            raise GameError(f"You level up once your clock has {LEVEL_UP_AT} cards and any damage is done.")
        clock = zones["clock"]
        first = clock[:LEVEL_UP_AT]
        chosen = next((c for c in first if c["uid"] == action.get("uid")), None)
        if not chosen:
            raise GameError(f"Choose one of the first {LEVEL_UP_AT} cards in your clock.")
        del clock[:LEVEL_UP_AT]
        put(side, chosen, "level")
        for card in first:
            if card is not chosen:
                put(side, card, "waiting")
        side["level_ups"] = side.get("level_ups", 0) + 1  # so both pages can show the new level
        fire(state, env, "level_up", player=player)
        add_log(state, player, f"levelled up to level {len(zones['level'])} with {name(chosen['card'])}")
        return {}

    if kind == "encore":
        # Pay 3 stock to keep a reversed character on the stage; it stays in its slot, rested.
        where, _ = find(side, action.get("uid", ""))
        if where not in STAGE_SLOTS:
            raise GameError("Only characters on the stage can be encored.")
        card = side["stage"][where]
        if card["pos"] != "reverse":
            raise GameError("Only a reversed character can be encored.")
        if has_status(state, card["uid"], "no_encore"):
            raise GameError("That character can't be encored this turn.")
        if len(zones["stock"]) < ENCORE_COST:
            raise GameError(f"Encore costs {ENCORE_COST} stock; you have {len(zones['stock'])}.")
        for _ in range(ENCORE_COST):
            put(side, zones["stock"].pop(), "waiting")
        card["pos"] = "rest"
        who = name(card["card"]) if not card["face_down"] else "a character"
        add_log(state, player, f"encored {who} (paid {ENCORE_COST} stock)")
        return {}

    if kind == "damage":
        amount = count_arg(action, most=20)
        if not zones["deck"]:
            raise GameError("Your deck is empty.")
        deal_damage(state, player, amount, amount, [], name, is_climax)
        return {}

    if kind in ("phase", "end_turn"):
        # Move the turn on to a later phase (end_turn: straight to the end phase), doing the
        # automatic step of every phase passed through on the way.
        # The encore step holds the turn until every reversed character (both players') has been
        # encored or sent to the waiting room, and ends by itself once there are none (see
        # auto_end_encore). {"auto": true} is a page following auto_next: dropped if it's stale.
        if action.get("auto") and (state["turn"] != player or state.get("auto_next") != action.get("phase")):
            return {}
        if state["turn"] != player:
            raise GameError("It isn't your turn.")
        if rules_on(state) and state.get("reveal"):
            if action.get("auto"):
                return {}  # the page tries again once the revealed card is closed
            raise GameError("Wait until the revealed card has been closed.")
        if rules_on(state) and abilities_busy(state):
            if action.get("auto"):
                return {}  # the page tries again once the abilities are done
            raise GameError("Finish resolving the abilities first.")
        if rules_on(state) and state.get("phase") == "mulligan":
            raise GameError("Both players need to finish their mulligan first.")
        target = PHASES.index("end" if kind == "end_turn" else zone_arg(action, "phase", PHASES))
        current = PHASES.index(state.get("phase", "main"))  # games from before phases: main
        if target <= current:
            raise GameError("That phase has already passed this turn.")
        rules = rules_on(state)
        if rules and PHASES[current] == "encore" and reversed_characters(state):
            raise GameError("Every reversed character needs an encore or the waiting room first.")
        if rules and (state.get("attack") or {}).get("step", "declare") != "declare":
            raise GameError("Finish the attack in progress first.")
        for phase in PHASES[current + 1:target + 1]:
            enter_phase(state, player, phase, env)
            if rules and phase == "encore" and reversed_characters(state):
                break  # wait here for the encore choices
            if rules and abilities_busy(state):
                if phase != PHASES[target]:
                    state["auto_next"] = PHASES[target]  # picks up where it left off afterwards
                break
        return {}

    if kind == "ability_trigger":
        trigger_ability(state, player, action, env)
        return {}

    if kind == "ability_answer":
        answer_ability(state, player, action, env)
        return {}

    if kind == "ability_stop":
        # A way out of an ability, whatever it's waiting on (anything already done stays done).
        res = state.get("resolving")
        if not res or res["player"] != player:
            raise GameError("You aren't resolving an ability.")
        state.pop("resolving")
        finish_event(state, res, env)
        add_log(state, player, "stopped resolving the ability; the rest was not done")
        return {}

    if kind == "ability_show_done":
        # Either page may send this; the other's copy arrives too late to match and does nothing.
        if (state.get("ability_show") or {}).get("id") == action.get("id"):
            state.pop("ability_show")
        return {}

    if kind == "activate":
        activate(state, player, action, env)
        return {}

    if kind == "chat":
        text = " ".join(str(action.get("text", "")).split())[:300]
        if not text:
            raise GameError("Type a message first.")
        state["log"].append({"who": side["name"], "text": text, "chat": True})
        del state["log"][:-MAX_LOG]
        return {}

    raise GameError(f"Unknown action: {kind!r}")


# --- Abilities -------------------------------------------------------------------------------------
#
# Card text is read by abilities.py into plain JSON steps. An event in the game (fire) checks every
# card that could respond; each AUTO ability whose trigger and conditions are met joins
# state["ability_queue"], and its controller is asked whether to trigger it (the turn player first,
# picking the order). A triggered or activated ability then runs as state["resolving"]: its steps run
# one at a time until one needs an answer, which it asks as res["prompt"] and picks up again from
# the "ability_answer" action. Steps wait for any damage or level up they caused.
#
# CONT abilities and buffs aren't stored on cards: refresh_stats works out every character's power
# and soul after each action, into state["stats"], from the printed numbers, every CONT ability
# in play and state["buffs"] ({"uid", "power", "soul", "expires": turn number, "grant": [text]}).

PUBLIC_CHOICES = {"stage", "center", "back", "waiting", "clock", "level", "memory"}  # choices both players can see
STEP_LIMIT = 500  # steps one action may run: a safety net, far above what any card does
BOARD_ERRORS = (GameError, KeyError, IndexError, TypeError, ValueError, AttributeError)


def abilities_busy(state):
    return bool(state.get("ability_queue") or state.get("resolving") or state.get("ability_show"))


def details_of(card, env):
    return env.info(card["card"]) or {}


def abilities_of(state, card, env):
    """A card's abilities: printed, given by a buff, and given by a CONT ability (see refresh_stats)."""
    found = list(abilities.parse(details_of(card, env).get("text")))
    for buff in state.get("buffs", []):
        if buff["uid"] == card["uid"]:
            for text in buff.get("grant", []):
                found += abilities.parse(text)
    for text in state.get("granted", {}).get(card["uid"], []):
        found += abilities.parse(text)
    return found


def card_pks(state):
    """Every card pk in the game."""
    pks = set()
    for side in state["players"].values():
        for cards in [*side["zones"].values(), *side.get("markers", {}).values(), stage_cards(side)]:
            pks.update(card["card"] for card in cards)
    return pks


def stage_cards(side):
    return [card for card in side["stage"].values() if card]


def slot_of(side, uid):
    return next((slot for slot, card in side["stage"].items() if card and card["uid"] == uid), None)


def locate(state, uid):
    """(owner, card, where) of a card anywhere on the table, or (None, None, None)."""
    for owner, side in state["players"].items():
        try:
            where, index = find(side, uid)
        except GameError:
            continue
        return owner, side["stage"][where] if where in STAGE_SLOTS else pile(side, where)[index], where
    return None, None, None


def fits(filter_, card, env, x=None, level=0):
    return abilities.matches_filter(filter_, details_of(card, env), x=x, my_level=level)


def condition_met(cond, state, player, source, ctx, env):
    """Whether one parsed condition holds. `source` is the ability's card."""
    side = state["players"][player]
    zones = side["zones"]
    other = state["players"][other_player(state, player)]
    kind = cond["type"]
    uid = source["uid"] if source else None
    if kind == "my_turn":
        return state["turn"] == player
    if kind == "opp_turn":
        return state["turn"] != player
    if kind == "phase":
        whose = cond.get("whose")
        return state.get("phase") == cond["phase"] and (not whose or (state["turn"] == player) == (whose == "me"))
    if kind == "always":
        return True
    if kind == "that_no_markers":
        slot = slot_of(side, ctx.get("that")) if ctx.get("that") else None
        return bool(slot) and not pile(side, MARKER + slot)
    if kind == "no_standing_facing":
        facing = facing_card(state, player, source, None)
        return not facing or facing["pos"] == "reverse"
    if kind == "self_marker_count":
        slot = slot_of(side, uid) if uid else None
        return compare(len(pile(side, MARKER + slot)) if slot else 0, cond["n"], cond["dir"])
    if kind == "self_markers":
        slot = slot_of(side, uid) if uid else None
        return bool(slot and pile(side, MARKER + slot)) == cond["any"]
    if kind == "total_level":
        return compare(sum(number(details_of(c, env).get("level")) for c in zones["level"]), cond["n"], cond["dir"])
    if kind == "in_battle":
        attack = state.get("attack") or {}
        return bool(uid) and attack.get("kind") == "front" and uid in battle_uids(state)
    if kind == "facing_exists":
        slot = slot_of(side, uid) if uid else None
        there = bool(other["stage"].get(OPPOSITE.get(slot, "")))
        return not there if cond["absent"] else there
    if kind == "opp_stage_count":
        count = sum(1 for slot, c in other["stage"].items() if c and (slot in OPPOSITE) == (cond["zone"] == "center"))
        return compare(count, cond["n"], cond["dir"])
    if kind == "looked":
        return bool(ctx.get("among"))
    if kind == "have_markers":
        return any(fits(cond["filter"], card, env) and pile(side, MARKER + slot)
                   for slot, card in side["stage"].items() if card)
    if kind == "that_above_opponent_level":
        facing = facing_card(state, player, source, ctx)
        return bool(facing) and number(details_of(facing, env).get("level")) > len(other["zones"]["level"])
    if kind == "milled_higher":
        milled = ctx.get("milled", {})
        if player not in milled:
            return False
        theirs = milled.get(other_player(state, player))
        return number((env.info(milled[player]) or {}).get("level")) > number((env.info(theirs) or {}).get("level") if theirs else 0)
    if kind == "chose":
        return len(ctx.get("it", [])) == cond["n"]
    if kind == "same_power":
        cards = [card for card in (locate(state, uid)[1] for uid in ctx.get("among", [])) if card]
        stats = compute_stats(state, env)[0]
        return len({stats.get(card["uid"], {}).get("power") for card in cards}) == 1
    if kind == "played_this_turn":
        return bool(source) and source.get("played_turn") == state["turn_number"]
    if kind == "my_level":
        return compare(len(zones["level"]), cond["n"], cond["dir"])
    if kind == "zone_count":
        counted_zones = other["zones"] if cond.get("owner") == "opp" else zones
        return compare(sum(fits(cond["filter"], c, env) for c in counted_zones[cond["zone"]]), cond["n"], cond["dir"])
    if kind == "all_trait":
        trait_filter = {"any": [{"trait": trait} for trait in cond.get("traits") or [cond["trait"]]]}
        return all(fits(trait_filter, c, env) for c in stage_cards(side))
    if kind == "have":
        cards = [c for slot, c in side["stage"].items() if c and (cond.get("zone") is None or (slot in OPPOSITE) == (cond["zone"] == "center"))]
        count = sum(fits(cond["filter"], c, env) and not (cond["filter"].get("other") and c["uid"] == uid) for c in cards)
        return compare(count, cond["n"], cond["dir"])
    if kind == "have_each":
        if cond.get("level"):
            cards = [c for c in zones["level"] if not (cond["other"] and c["uid"] == uid)]
        else:
            cards = [c for slot, c in side["stage"].items() if c and (not cond["center"] or slot in OPPOSITE)
                     and (not cond.get("back") or slot not in OPPOSITE)
                     and not (cond["other"] and c["uid"] == uid)]
        found = all(any(fits(f, c, env) and position_fits(f, c) for c in cards) for f in cond["filters"])
        return not found if cond["absent"] else found
    if kind == "climax_is":
        climax = (other if cond["owner"] == "opp" else side)["zones"]["climax"]
        return any(not c["face_down"] and fits(cond["filter"], c, env) for c in climax)
    if kind == "self_in":
        _, _, where = locate(state, uid) if uid else (None, None, None)
        return {"center stage": where in OPPOSITE, "back stage": where in ("B1", "B2"), "middle": where == "C2",
                "waiting room": where == "waiting", "memory": where == "memory", "level": where == "level"}[cond["where"]]
    if kind == "self_rest":
        return bool(source) and source["pos"] == "rest"
    if kind == "self_stand":
        return bool(source) and source["pos"] == "stand"
    if kind == "self_clock_top":
        return bool(zones["clock"]) and zones["clock"][-1]["uid"] == uid
    if kind == "opp_has":
        return any(fits(cond["filter"], c, env) for c in stage_cards(other))
    if kind == "facing_level":
        facing = facing_card(state, player, source, ctx)
        return bool(facing) and compare(number(details_of(facing, env).get(cond.get("stat", "level"))), cond["n"], cond["dir"])
    if kind == "counted":
        return ctx.get("counts", {}).get(cond["key"], 0) >= 1
    if kind == "revealed":
        return ctx.get("revealed") is not None and abilities.matches_filter(cond["filter"], env.info(ctx["revealed"]) or {}) != bool(cond.get("negate"))
    if kind == "among_has":
        return any(abilities.matches_filter(cond["filter"], env.info(pk) or {}) for pk in ctx.get("flipped", []))
    return True


def position_fits(filter_, card):
    return not (filter_.get("stand") and card["pos"] != "stand") and not (filter_.get("rest") and card["pos"] != "rest")


def battle_uids(state):
    """The two characters in the battle in progress, if any."""
    attack = state.get("attack") or {}
    if "uid" not in attack:
        return set()
    target = state["players"][other_player(state, state["turn"])]["stage"].get(attack.get("target") or "")
    return {attack["uid"]} | ({target["uid"]} if target else set())


def compare(value, n, direction):
    if direction in ("more", "higher"):
        return value >= n
    if direction in ("less", "lower"):
        return value <= n
    return value == n


def facing_card(state, player, source, ctx):
    """The character battling or facing this one."""
    if ctx and ctx.get("that"):
        _, card, _ = locate(state, ctx["that"])
        if card:
            return card
    slot = slot_of(state["players"][player], source["uid"]) if source else None
    return state["players"][other_player(state, player)]["stage"].get(OPPOSITE.get(slot, ""))


def all_met(ability, state, player, source, ctx, env):
    return all(condition_met(cond, state, player, source, ctx, env) for cond in ability.get("cond", []))


def x_value(spec, state, player, target, ctx, env, stats=None):
    """The number an "X is equal to ..." sentence describes."""
    if not spec:
        return 0
    side = state["players"][player]
    kind = spec["of"]
    if kind == "my_level":
        value = len(side["zones"]["level"])
    elif kind == "target_level":
        value = number(details_of(target, env).get("level")) if target else 0
    elif kind == "target_soul":
        known = (stats or {}).get(target["uid"], {}) if target else {}
        value = known.get("soul", number(details_of(target, env).get("soul")) if target else 0)
    elif kind == "revealed_level":
        value = number((env.info(ctx.get("revealed")) or {}).get("level")) if ctx and ctx.get("revealed") is not None else 0
    elif kind == "chosen_level":
        chosen = locate(state, (ctx.get("it") or [None])[0])[1] if ctx else None
        value = number(details_of(chosen, env).get("level")) - spec.get("minus", 0) if chosen else 0
    elif kind == "self_soul":
        known = (stats or {}).get((ctx or {}).get("source_uid"), {})
        source = locate(state, (ctx or {}).get("source_uid"))[1]
        value = known.get("soul", number(details_of(source, env).get("soul")) if source else 0)
    elif kind == "that_level":
        that = locate(state, (ctx or {}).get("that"))[1] if (ctx or {}).get("that") else None
        value = number(details_of(that, env).get("level")) if that else 0
    elif kind == "flipped_total":
        value = sum(number((env.info(pk) or {}).get("level")) for pk in (ctx or {}).get("flipped", []))
    elif kind == "flipped_icons":
        value = sum(((env.info(pk) or {}).get("trigger") or "").split().count(spec["icon"]) for pk in (ctx or {}).get("flipped", []))
    elif kind == "markers":
        slot = slot_of(side, (ctx or {}).get("source_uid"))
        value = len(pile(side, MARKER + slot)) if slot else 0
    elif kind == "facing_level":
        facing = facing_card(state, player, locate(state, (ctx or {}).get("source_uid"))[1], ctx)
        value = number(details_of(facing, env).get("level")) if facing else 0
    elif kind == "opp_stage":
        them = state["players"][other_player(state, player)]
        value = sum(1 for slot, c in them["stage"].items() if c and (slot in OPPOSITE) == (spec["zone"] == "center"))
    elif kind == "flipped_level":
        last = (ctx or {}).get("flipped", [])
        value = (number((env.info(last[-1]) or {}).get("level")) + spec.get("plus", 0)) if last else 0
    elif kind == "flipped":
        value = sum(abilities.matches_filter(spec["filter"], env.info(pk) or {}) for pk in (ctx or {}).get("flipped", [])) + spec.get("plus", 0)
    elif kind == "marker_tiers":
        slot = slot_of(side, (ctx or {}).get("source_uid"))
        count = len(pile(side, MARKER + slot)) if slot else 0
        value = next((x for most, x in spec["tiers"] if count <= most), spec["above"])
    elif kind == "opp_chars":
        value = len(stage_cards(state["players"][other_player(state, player)]))
    elif kind == "my_chars":
        source_uid = (ctx or {}).get("source_uid")
        zone = spec.get("stage_zone")
        cards = [c for slot, c in side["stage"].items() if c and (zone is None or (slot in OPPOSITE) == (zone == "center"))]
        value = sum(fits(spec.get("filter"), c, env) and not (spec["filter"].get("other") and c["uid"] == source_uid) for c in cards)
    else:  # "zone"
        value = sum(fits(spec.get("filter"), c, env) for c in side["zones"][spec["zone"]])
    return value * spec.get("times", 1)


def cont_targets(effect, state, player, source, env):
    side = state["players"][player]
    target = effect["target"]
    slot = slot_of(side, source["uid"])
    if target["type"] == "facing":
        facing = state["players"][other_player(state, player)]["stage"].get(OPPOSITE.get(slot, ""))
        return [facing] if facing else []
    if target["type"] == "self":
        return [source] if slot else []
    if target["type"] == "front":
        slots = {"B1": ("C1", "C2"), "B2": ("C2", "C3")}.get(slot, ())
    elif target["type"] == "middle":
        slots = ("C2",)
    else:
        slots = STAGE_SLOTS
    filter_ = target.get("filter")
    return [card for card in (side["stage"][s] for s in slots) if card and fits(filter_, card, env)
            and not (filter_.get("other") and card["uid"] == source["uid"])]


def compute_stats(state, env):
    """Every character's power and soul right now, and the abilities CONT abilities are giving them.
    Soul first, since some power depends on it ("X is equal to that character's soul ×1000")."""
    stats = {}
    conts = []
    for player, side in state["players"].items():
        for card in stage_cards(side):
            details = details_of(card, env)
            stats[card["uid"]] = {"power": number(details.get("power")), "soul": number(details.get("soul"))}
        sources = [c for c in stage_cards(side) if not c["face_down"]]
        sources += [c for c in side["zones"]["climax"][-1:] if not c["face_down"]]
        for source in sources:
            for ability in abilities.parse(details_of(source, env).get("text")):
                if ability["kind"] == "cont" and ability["effects"]:
                    conts.append((player, source, ability))
    granted = {}
    for wanted in ("soul", "power"):
        for player, source, ability in conts:
            ctx = {"source_uid": source["uid"]}
            if not all_met(ability, state, player, source, ctx, env):
                continue
            for effect in ability["effects"]:
                for target in cont_targets(effect, state, player, source, env) if source["uid"] in stats or effect["target"]["type"] != "self" else []:
                    amount = effect.get(wanted, 0)
                    if effect.get("x_stat") == wanted:
                        amount += x_value(effect.get("x"), state, player, target, ctx, env, stats)
                    if effect.get("per"):
                        amount *= x_value(effect["per"], state, player, target, ctx, env, stats)
                    stats[target["uid"]][wanted] += amount
                    if wanted == "power" and effect.get("grant"):
                        granted.setdefault(target["uid"], []).extend(effect["grant"])
    for buff in state.get("buffs", []):
        if buff["uid"] in stats:
            stats[buff["uid"]]["power"] += buff.get("power", 0)
            stats[buff["uid"]]["soul"] += buff.get("soul", 0)
    for values in stats.values():
        values["power"] = max(0, values["power"])
        values["soul"] = max(0, values["soul"])
    for buff in state.get("buffs", []):  # power set by hand beats everything else, until the turn ends
        if "set_power" in buff and buff["uid"] in stats:
            stats[buff["uid"]].update(power=buff["set_power"], manual=True)
    return stats, granted


def level_buff(state, uid):
    return sum(buff.get("level", 0) for buff in state.get("buffs", []) if buff["uid"] == uid)


def update_attack_soul(state, stats, env):
    """The damage of the attack in progress follows its attacker's soul until it's dealt."""
    attack = state.get("attack") or {}
    if "soul_extra" not in attack or attack.get("dealt") or attack["uid"] not in stats:
        return
    soul = stats[attack["uid"]]["soul"] + attack["soul_extra"]
    if attack["kind"] == "side" and not has_status(state, attack["uid"], "no_side_loss"):
        target = state["players"][other_player(state, state["turn"])]["stage"][attack["target"]]
        soul = max(0, soul - (number(details_of(target, env).get("level")) + level_buff(state, target["uid"]) if target else 0))
    attack["soul"] = soul


def refresh_stats(state, env):
    on_stage = {card["uid"] for side in state["players"].values() for card in stage_cards(side)}
    if state.get("buffs"):
        state["buffs"] = [buff for buff in state["buffs"] if buff["uid"] in on_stage]
    state["stats"], state["granted"] = compute_stats(state, env)
    update_attack_soul(state, state["stats"], env)
    state["acts"] = {player: player_acts(state, player, env) for player in state["players"]}
    state["needs_color"] = {player: {card["uid"]: needed for card in side["zones"]["hand"]
                                     if (needed := color_needed(state, player, card, env.info))}
                            for player, side in state["players"].items()}


def stat_of(state, card, env, stat):
    stats, _ = compute_stats(state, env)
    return stats.get(card["uid"], {}).get(stat, 0)


# Paying costs ----------------------------------------------------------------------------------------

def cost_options(part, state, player, source, env):
    side = state["players"][player]
    filter_ = part.get("filter")
    if part["part"] == "rest_chars" or part.get("zone") == "stage":
        cards = stage_cards(side)
    elif part.get("zone") == "climax":
        cards = side["zones"]["climax"]
    else:
        cards = side["zones"][part["zone"]]
    level = len(side["zones"]["level"])
    return [c for c in cards if fits(filter_, c, env, level=level)
            and not (filter_.get("other") and source and c["uid"] == source["uid"])
            and not (filter_.get("stand") and c["pos"] != "stand")]


def can_pay(cost, state, player, source, env):
    """Why this cost can't be paid right now, or None if it can."""
    zones = state["players"][player]["zones"]
    for part in cost or []:
        kind = part["part"]
        if kind == "stock" and len(zones["stock"]) < part["n"]:
            return f"needs {part['n']} stock"
        if kind == "self_rest" and (not source or source["pos"] != "stand"):
            return "needs this card standing"
        if kind == "self_to" and part.get("stand") and (not source or source["pos"] != "stand"):
            return "needs this card standing"
        if kind == "deck_to_clock" and not zones["deck"]:
            return "needs a card in your deck"
        if kind == "stock_to_clock" and not zones["stock"]:
            return "needs a card in your stock"
        if kind == "markers":
            slot = slot_of(state["players"][player], source["uid"]) if source else None
            if not slot or len(pile(state["players"][player], MARKER + slot)) < part["n"]:
                return f"needs {part['n']} marker{'s' if part['n'] != 1 else ''} under this card"
        if kind in ("pick", "rest_chars") and len(cost_options(part, state, player, source, env)) < part["n"]:
            return f"needs {part['n']} more to pay with"
    return None


def cost_steps(cost):
    steps = []
    for part in cost or []:
        kind = part["part"]
        if kind == "stock":
            steps.append({"do": "pay_stock", "n": part["n"]})
        elif kind == "self_rest":
            steps.append({"do": "pos_self", "pos": "rest"})
        elif kind == "self_to":
            steps.append({"do": "self_to", "to": part["to"]})
        elif kind == "deck_to_clock":
            steps.append({"do": "top", "n": 1, "owner": "me", "to": "clock"})
        elif kind == "stock_to_clock":
            steps.append({"do": "stock_to_clock"})
        elif kind == "shuffle":
            steps.append({"do": "shuffle", "owner": "me"})
        elif kind == "markers":
            steps.append({"do": "pay_markers", "n": part["n"]})
        elif kind == "pick":
            steps.append({"do": "choose", "zone": part["zone"], "filter": part["filter"], "min": part["n"], "max": part["n"],
                          "text": "Cost: choose what to pay with", "cost": True})
            steps.append({"do": "move_it", "to": part["to"]} if part["to"] else {"do": "reveal_it"})
        elif kind == "rest_chars":
            steps.append({"do": "choose", "zone": "stage", "filter": part["filter"], "min": part["n"], "max": part["n"],
                          "text": "Cost: choose characters to rest", "cost": True})
            steps.append({"do": "pos_it", "pos": "rest"})
    return steps


# Triggering ------------------------------------------------------------------------------------------

def when_matches(when, event, data, player, card, env):
    """{"that": uid} and so on if this trigger is this event, for this ability's card, else None."""
    on = when["on"]
    uid = card["uid"]
    if on == "backup" and (when.get("opponent") or when.get("any_of_mine")):
        return {} if event == "backup" and (data.get("source_owner") == player) == bool(when.get("any_of_mine")) else None
    self_event = {"play": "play", "leave": "leave", "attack": "attack", "cancel": "cancel", "backup": "backup",
                  "check_climax": "check_climax", "attack_end": "attack_end", "climax_self": "climax"}
    if on in self_event:
        if event != self_event[on] or data.get("uid") != uid:
            return None
        if on == "attack" and when.get("kind") not in (None, data.get("kind")):
            return None
        return {}
    if on == "phase":
        mine = data.get("player") == player
        return {} if event == "phase" and when["phase"] == data["phase"] and (when["whose"] == "any" or mine == (when["whose"] == "me")) else None
    if on == "climax":
        if event != "climax" or (data.get("player") == player) != (when.get("whose") != "opp"):
            return None
        return {} if not when.get("filter") or abilities.matches_filter(when["filter"], env.info(data["card"]) or {}) else None
    if on == "climax_trigger":
        if event != "climax_trigger" or data.get("player") != player:
            return None
        return {} if not when.get("filter") or abilities.matches_filter(when["filter"], env.info(data["card"]) or {}) else None
    if on == "opp_act":
        return {} if event == "act" and data.get("player") != player else None
    if on == "play_other":
        if event == "play" and data.get("source_owner") == player and data.get("uid") != uid and abilities.matches_filter(when["filter"], env.info(data["source"]["card"]) or {}):
            return {"that": data["uid"]}
        return None
    if on == "level_up":
        return {} if event == "level_up" and (data.get("player") == player) != (when.get("whose") == "opp") else None
    if on == "check_card":
        if event != "check_card" or data.get("player") != player or (not when.get("any") and data.get("uid") != uid):
            return None
        return {} if abilities.matches_filter(when["filter"], env.info(data["card"]) or {}) else None
    if on == "other_battle_win":
        if event == "reverse" and data.get("by") and data["by"] != uid and locate_owner(data.get("by_owner"), player):
            attacker = data.get("by_card")
            return {"that": data["uid"]} if abilities.matches_filter(when["filter"], env.info(attacker) or {}) else None
        return None
    if on == "my_act":
        return {} if event == "act" and data.get("player") == player else None
    if on == "my_event":
        return {} if event == "event" and data.get("player") == player else None
    if on == "any_check_climax":
        return {} if event == "check_climax" and data.get("player") == player else None
    if on == "no_cancel":
        return {} if event == "damage_result" and not data["cancelled"] and data.get("uid") == uid else None
    if on == "received":
        return {} if event == "damage_result" and data["cancelled"] == when["cancelled"] and data.get("defender") == player else None
    if on == "leave_other":
        if event == "leave" and data.get("source_owner") == player and data.get("uid") != uid and abilities.matches_filter(when["filter"], env.info(data["source"]["card"]) or {}):
            return {"that": data["uid"]}
        return None
    if event == "reverse":
        reversed_card = data["uid"]
        if on == "reverse_self" and reversed_card == uid:
            return {"that": data.get("by"), "reversed": reversed_card}
        if on == "reverse_opponent" and data.get("by") == uid:
            level = number((env.info(data["card"]) or {}).get("level"))
            return {"that": reversed_card, "reversed": reversed_card} if level >= when.get("level_min", 0) else None
        if (on == "reverse_other" and data.get("owner") == player and reversed_card != uid
                and abilities.matches_filter(when["filter"], env.info(data["card"]) or {})):
            return {"that": reversed_card}
        return None
    if event == "attack":
        if on == "other_attacks" and data.get("player") == player and (when.get("any") or data.get("uid") != uid) and when.get("kind") in (None, data.get("kind")) \
                and (not when.get("filter") or abilities.matches_filter(when["filter"], env.info(data.get("card")) or {})):
            return {"that": data["uid"]}
        if on == "frontal_self" and data.get("target") == uid and data.get("kind") == when.get("kind", "front"):
            return {"that": data["uid"]}
        if on == "frontal" and data.get("kind") == "front" and data.get("defender") == player and data.get("target") != uid:
            target = locate_details(data.get("target_card"), env)
            return {"that": data["target"]} if abilities.matches_filter(when["filter"], target) else None
        if on == "facing_attacks" and data.get("target") == uid:
            return {"that": data.get("uid")}
    return None


def locate_owner(owner, player):
    return owner == player


def locate_details(card_pk, env):
    return (env.info(card_pk) or {}) if card_pk is not None else {}


def response_sources(side, data):
    """(card, zone) for each card of a side that could respond to an event."""
    sources = [(c, "stage") for c in stage_cards(side) if not c["face_down"]]
    sources += [(c, "waiting") for c in side["zones"]["waiting"]]
    sources += [(c, "memory") for c in side["zones"]["memory"]]
    sources += [(c, "clock") for c in side["zones"]["clock"]]
    return sources


def fire_delayed(state, env, phase, player):
    """Effects that said "at the beginning of your next ..." and have been waiting for this phase."""
    waiting = []
    for delayed in state.get("delayed", []):
        whose_turn = delayed["player"] == player
        if delayed["phase"] == phase and (delayed["whose"] == "any" or whose_turn == (delayed["whose"] == "me")):
            ability = {"kind": "delayed", "text": delayed["text"], "steps": delayed["steps"]}
            state.setdefault("ability_queue", []).append({"id": new_uid(), "player": delayed["player"], "uid": delayed["uid"], "card": delayed["card"],
                                                          "ability": ability, "ctx": delayed["ctx"]})
        else:
            waiting.append(delayed)
    if state.get("delayed"):
        state["delayed"] = waiting


def fire(state, env, event, **data):
    """An event happened: queue each AUTO ability it triggers. Only with turn rules on."""
    if not rules_on(state):
        return
    if event == "phase":
        fire_delayed(state, env, data["phase"], data["player"])
    first = state["turn"]
    for player in [first, other_player(state, first)]:
        side = state["players"][player]
        seen = set()
        explicit = data.get("source")
        sources = response_sources(side, data)
        if explicit is not None and data.get("source_owner") == player:
            sources.append((explicit, "event"))
        for card, zone in sources:
            for ability in abilities_of(state, card, env):
                if ability["kind"] != "auto" or not ability.get("when"):
                    continue
                where = ability.get("where")
                if zone != "event" and (where or "stage") != zone:
                    continue
                key = (card["uid"], ability["text"])
                if key in seen:
                    continue
                seen.add(key)
                for when in ability["when"]:
                    ctx = when_matches(when, event, data, player, card, env)
                    if ctx is None:
                        continue
                    if data.get("slot"):
                        ctx["old_slot"] = data["slot"]
                    queue_ability(state, player, card, ability, ctx, env)
                    break


def has_status(state, uid, status):
    """Whether a buff on this character says it can't do something (see the "status" step)."""
    return any(buff["uid"] == uid and buff.get("status") == status for buff in state.get("buffs", []))


def used_up(state, card, ability):
    """Whether this ability has been used as often as it can be this turn."""
    return bool(ability.get("once")) and state.get("used", []).count(used_key(card, ability)) >= (ability.get("limit") or 1)


def used_key(card, ability):
    return f"{card['uid']}:{ability['text'][:80]}"


def queue_ability(state, player, card, ability, ctx, env):
    """An AUTO ability triggered: queue it if it can still do something."""
    if used_up(state, card, ability):
        return
    if ability["text"].startswith("【AUTO】 Encore") and has_status(state, card["uid"], "no_encore"):
        return
    ctx = {**ctx, "source_uid": card["uid"]}
    if not all_met(ability, state, player, card, ctx, env):
        return
    first = (ability.get("steps") or [{}])[0]
    if first.get("do") == "may" and first.get("cost") and can_pay(first["cost"], state, player, card, env):
        return  # "you may pay the cost", and it can't be paid
    state.setdefault("ability_queue", []).append(
        {"id": new_uid(), "player": player, "uid": card["uid"], "card": card["card"], "ability": copy.deepcopy(ability), "ctx": ctx})


def queue_event(state, player, card, ability, env):
    """An event or counter card played: its text joins the queue like an ability."""
    state.setdefault("ability_queue", []).append(
        {"id": new_uid(), "player": player, "uid": card["uid"], "card": card["card"], "ability": copy.deepcopy(ability),
         "ctx": {"source_uid": card["uid"]}, "event": True})


def start_resolving(state, entry, env):
    """Start running an ability the player has triggered or activated."""
    ability = entry["ability"]
    steps = copy.deepcopy(ability.get("steps", []))
    if steps and steps[0].get("do") == "may" and entry.get("accepted", True):
        first = steps.pop(0)  # saying yes to the prompt was the "you may"
        steps[:0] = cost_steps(first.get("cost")) + first.get("then", [])
    if ability.get("once"):
        state.setdefault("used", []).append(used_key({"uid": entry["uid"]}, ability))
    if ability.get("manual_cost"):
        steps.insert(0, {"do": "manual", "text": "Pay this ability's cost by hand."})
    state["resolving"] = {"player": entry["player"], "uid": entry["uid"], "card": entry["card"], "text": ability["text"],
                          "steps": steps, "ctx": entry.get("ctx", {}), "prompt": None, "event": entry.get("event", False)}


def activate_steps(entry):
    """An activated ability's cost is paid first, then its effect."""
    ability = entry["ability"]
    entry["ability"] = {**ability, "steps": cost_steps(ability.get("cost")) + ability.get("steps", [])}


def finish_event(state, res, env):
    """An event that's done goes to the waiting room, unless its text put it somewhere else."""
    if not res.get("event"):
        return
    owner, card, where = locate(state, res["uid"])
    if card and where == "resolution":
        side = state["players"][owner]
        side["zones"]["resolution"].remove(card)
        put(side, card, "waiting")


# Running steps ---------------------------------------------------------------------------------------

def run_abilities(state, env):
    """Run the ability being resolved until it needs an answer, something it caused needs finishing
    first, or it's done."""
    for _ in range(STEP_LIMIT):
        res = state.get("resolving")
        if not res or res.get("prompt") or state.get("ability_show"):
            return
        if any(damage_in_progress(state, p) or must_level_up(state, p) for p in state["players"]):
            return
        if not res["steps"]:
            state.pop("resolving")
            finish_event(state, res, env)
            show_ability(state, res)
            continue
        step = res["steps"].pop(0)
        try:
            run_step(step, res, state, env)
        except BOARD_ERRORS as exc:  # a card this couldn't follow must not stop the game: hand it to the player
            res["steps"][:0] = [{"do": "manual", "text": step.get("text") or res["text"]}]
            add_log(state, res["player"], f"couldn't apply a step automatically ({exc}); resolve it by hand")


def among_them(state, ctx):
    """The cards "from among them" means: what was revealed, else what was looked at or last chosen,
    less any that have since been moved."""
    uids = ctx["pool"] if "pool" in ctx else ctx.get("among", [])
    return [card for card in (locate(state, uid)[1] for uid in uids if uid not in ctx.get("moved", [])) if card]


SHOW_TARGETS = 4  # at most this many targets shown with an ability


def note_target(res, card):
    """A card this ability is directed at, for show_ability. Only call this for cards both players can see."""
    if card and not card["face_down"] and card["uid"] != res["uid"]:
        targets = res["ctx"].setdefault("targets", [])
        if card["uid"] not in [t["uid"] for t in targets]:
            targets.append({"uid": card["uid"], "card": card["card"]})


def show_ability(state, res):
    """An ability finished, prompts and all: both pages show its card, with arrows to any cards it was
    directed at, and everything else waits until a page sends "ability_show_done". An ability that
    was declined and did nothing isn't shown."""
    ctx = res["ctx"]
    if ctx.get("declined") and not ctx.get("targets"):
        return
    state["ability_show"] = {"id": new_uid(), "player": res["player"], "uid": res["uid"], "card": res["card"], "text": res["text"],
                             "targets": [t["card"] for t in ctx.get("targets", [])[:SHOW_TARGETS]]}


def show_revealed(state, res, pks):
    """Cards an ability reveals: both pages show them straight away, and it carries on once they've been seen."""
    if pks:
        state["ability_show"] = {"id": new_uid(), "player": res["player"], "uid": res["uid"], "card": pks[0], "text": "Revealed",
                                 "targets": [], "check": list(pks), "label": "Revealed"}


def choose_options(step, res, state, env):
    """(owner, candidates) that a choose step could pick from."""
    player = res["player"]
    ctx = res["ctx"]
    opponent = other_player(state, player)
    owner = opponent if step.get("owner") == "opp" else player
    side = state["players"][owner]
    zone = step["zone"]
    if zone == "among":
        owner = ctx.get("among_owner", player)
        side = state["players"][owner]
        cards = among_them(state, ctx)
    elif zone == "stage":
        cards = stage_cards(side)
    elif zone in ("center", "back"):
        cards = [c for s, c in side["stage"].items() if c and (s in OPPOSITE) == (zone == "center")]
    elif zone == "marker":
        slot = slot_of(side, res["uid"])
        cards = pile(side, MARKER + slot) if slot else []
    elif zone == "hand_or_marker":
        slot = slot_of(side, res["uid"])
        cards = side["zones"]["hand"] + (pile(side, MARKER + slot) if slot else [])
    else:
        cards = side["zones"][zone]
    x = x_value(step.get("x"), state, player, None, ctx, env)
    filter_ = step.get("filter") or {}
    level = len(state["players"][player]["zones"]["level"])
    found = [c for c in cards if fits(filter_, c, env, x=x, level=level)
             and not (filter_.get("other") and c["uid"] == res["uid"])
             and position_fits(filter_, c)
             and not (filter_.get("in_battle") and c["uid"] not in battle_uids(state))
             and not (filter_.get("no_markers") and pile(side, MARKER + (slot_of(side, c["uid"]) or "C1")))
             and not (filter_.get("above_opponent_level") and number(details_of(c, env).get("level")) <= len(side["zones"]["level"]))]
    if owner != player and step.get("chooser") != "opp":  # "This card cannot be chosen by your opponent's effects."
        found = [c for c in found if not any("cannot be chosen by your opponent's effects" in a["text"]
                                             for a in abilities_of(state, c, env))]
    return owner, found


def ask_cards(res, cards, owner, minimum, maximum, title, purpose="it", options=None):
    res["prompt"] = {"kind": "cards", "for": purpose, "title": title[:1].upper() + title[1:], "owner": owner, "min": minimum, "max": maximum,
                     "cards": [dict(card) for card in cards], "options": [c["uid"] for c in (options if options is not None else cards)]}


def ask_choice(res, purpose, title, options, **extra):
    res["prompt"] = {"kind": "choice", "for": purpose, "title": title[:1].upper() + title[1:],
                     "options": [{"value": value, "label": label} for value, label in options], **extra}


def ask_number(res, step, title):
    ask_choice(res, "number", title, [(n, str(n)) for n in range(step["n"], -1, -1)], step=step)


def counted(ctx, key):
    counts = ctx.setdefault("counts", {})
    counts[key] = counts.get(key, 0) + 1


def move_card(state, env, actor, owner, uid, to):
    """An ability moving a card. Moving onto the stage goes through "place"; `to` here is a zone."""
    side = state["players"][owner]
    card, src = take(side, uid)
    if to == "deck_bottom":
        put(side, card, "deck", "bottom")
    elif to == "clock_bottom":
        put(side, card, "clock", "bottom")
    else:
        put(side, card, to)
    if to not in HIDDEN_ZONES and to != "hand":
        card["face_down"] = False
    if src in STAGE_SLOTS:
        discard_markers(state, owner, src)
        if to == "waiting":
            fire(state, env, "leave", uid=uid, source=card, source_owner=owner, slot=src)
    target = {"deck_bottom": "deck", "clock_bottom": "clock"}.get(to, to)
    add_log(state, actor, describe_move(card, src, target, env.name)
            + (" (bottom)" if to == "deck_bottom" else "")
            + (f" ({state['players'][owner]['name']}'s)" if owner != actor else ""))
    return card


def add_buff(state, uid, step, power, soul):
    expires = state["turn_number"] + (1 if step.get("until") == "next" else 0)
    state.setdefault("buffs", []).append({"uid": uid, "power": power, "soul": soul, "level": step.get("level", 0), "expires": expires, "grant": step.get("grant", [])})


def buff_label(power, soul, grant):
    parts = [f"{value:+d} {stat}" for value, stat in ((power, "power"), (soul, "soul")) if value]
    if grant:
        parts.append("a new ability")
    return " and ".join(parts) or "nothing"


def run_step(step, res, state, env):
    """One step of an ability. Steps that branch or repeat put what comes next on the front of res["steps"]."""
    player = res["player"]
    ctx = res["ctx"]
    do = step["do"]
    side = state["players"][player]
    zones = side["zones"]
    opponent = other_player(state, player)

    if do == "manual":
        res["prompt"] = {"kind": "manual", "title": "Do this by hand", "text": step["text"]}
    elif do == "if":
        source = locate(state, res["uid"])[1]
        if all(condition_met(cond, state, player, source, ctx, env) for cond in step["cond"]):
            res["steps"][:0] = step["then"]
    elif do == "may":
        source = locate(state, res["uid"])[1]
        why = can_pay(step.get("cost"), state, player, source, env)
        if why:
            add_log(state, player, f"couldn't pay the cost: {why}")
            return
        ask_choice(res, "may", step.get("text", "You may do this."), [("yes", "Yes"), ("no", "No")], step=step)
    elif do == "options":
        ask_choice(res, "options", "Choose 1 effect", [(i, o["text"]) for i, o in enumerate(step["options"])], step=step)
    elif do == "for_each":
        count = sum(abilities.matches_filter(step["filter"], env.info(pk) or {}) for pk in ctx.get("flipped", []))
        res["steps"][:0] = copy.deepcopy(step["then"]) * count
    elif do == "choose":
        owner, found = choose_options(step, res, state, env)
        if not found:
            ctx["it_before"], ctx["it"] = ctx.get("it", []), []
            add_log(state, player, "had nothing to choose")
            return
        minimum = min(step["min"], len(found))
        maximum = min(step["max"], len(found))
        shown = found
        if step["zone"] == "among":  # show everything looked at, though only some can be taken
            shown = among_them(state, ctx)
        ctx["it_owner"] = owner
        ask_cards(res, shown, owner, minimum, maximum, step.get("text", "Choose"), options=found)
        res["prompt"]["zone"] = step["zone"]
        res["prompt"]["cost"] = step.get("cost", False)
        if step.get("chooser") == "opp":  # the opponent answers this one
            res["prompt"]["player"] = opponent
    elif do == "search":
        cards = list(reversed(zones["deck"]))
        found = [c for c in cards if fits(step["filter"], c, env, level=len(zones["level"]))]
        add_log(state, player, "searched their deck")
        if not found:
            ctx["it"] = []
            ctx["among"] = []
            add_log(state, player, "found nothing to take")
            return
        ctx["it_owner"] = ctx["among_owner"] = player
        ask_cards(res, found, player, 0, min(step["max"], len(found)), step.get("text", "Search your deck"), purpose="search")
    elif do == "move_it":
        owner = ctx.get("it_owner", player)
        for uid in ctx.get("it", []):
            if locate(state, uid)[1]:
                move_card(state, env, player, owner, uid, step["to"])
                ctx.setdefault("moved", []).append(uid)
                if step["to"] in ("hand", "stock"):
                    counted(ctx, step["to"])
    elif do == "dest":
        if ctx.get("it"):
            labels = {"hand": "Hand", "stock": "Stock", "deck": "Top of deck", "deck_bottom": "Bottom of deck", "waiting": "Waiting room"}
            owner = ctx.get("it_owner", player)
            shown = [c for c in (locate(state, uid)[1] for uid in ctx["it"]) if c]
            ask_choice(res, "dest", "Where does it go?", [(to, labels[to]) for to in step["options"]],
                       cards=[dict(c) for c in shown], owner=owner)
    elif do == "place":
        if ctx.get("it"):
            other_stage = state["players"][opponent]["stage"]
            owner = opponent if step.get("opponent_places") or (step.get("on_owner") and ctx.get("it_owner") == opponent) else player
            side = state["players"][owner]
            slots = [s for s in STAGE_SLOTS if not (step.get("open") and side["stage"][s])]
            if step.get("only"):
                slots = [s for s in slots if s == step["only"]]
            if step.get("zone"):
                slots = [s for s in slots if (s in OPPOSITE) == (step["zone"] == "center")]
            if step.get("facing"):
                slots = [s for s in slots if other_stage[OPPOSITE[s]]]
            if not slots:
                add_log(state, player, "had no open stage position")
                return
            shown = [c for c in (locate(state, uid)[1] for uid in ctx["it"]) if c]
            ask_choice(res, "place", "Choose a stage position", [(s, LABELS[s].capitalize()) for s in slots],
                       cards=[dict(c) for c in shown], owner=owner, rest=step.get("rest", False), keep_pos=step.get("keep_pos", False))
            if step.get("opponent_places"):
                res["prompt"]["player"] = opponent
    elif do == "to_old_slot":
        uid = ctx.get("that") if step.get("that") else res["uid"] if step.get("self") else (ctx.get("it") or [None])[0]
        slot = ctx.get("old_slot") or ctx.get("self_slot")
        if uid and slot and not side["stage"][slot] and locate(state, uid)[0] == player:
            card, _ = take(side, uid)
            put(side, card, slot)
            card["pos"] = "rest" if step.get("rest") else "stand"
            add_log(state, player, f"put {env.name(card['card'])} on {LABELS[slot]}")
    elif do == "marker":
        slot = slot_of(side, res["uid"])
        if slot:
            for uid in ctx.get("it", []):
                owner = locate(state, uid)[0]
                card, src = take(state["players"][owner], uid)
                if src in STAGE_SLOTS:
                    discard_markers(state, owner, src)
                put(side, card, MARKER + slot, face_down=step.get("face_down"))
                ctx.setdefault("moved", []).append(uid)
            add_log(state, player, f"put {len(ctx.get('it', []))} marker(s) under {LABELS[slot]}")
    elif do == "rest":
        owner = ctx.get("among_owner", player)
        for uid in ctx.get("among", []):
            if uid not in ctx.get("moved", []) and locate(state, uid)[1]:
                move_card(state, env, player, owner, uid, step["to"])
                ctx.setdefault("moved", []).append(uid)
        ctx.pop("pool", None)
        ctx["among"] = []
    elif do == "order_top":
        owner = ctx.get("among_owner", player)
        cards = [c for c in among_them(state, {"among": ctx.get("among", []), "moved": ctx.get("moved", [])})]
        if len(cards) > 1:
            ask_cards(res, cards, owner, len(cards), len(cards), "Pick them in order: the first you pick goes on top", purpose="order")
    elif do == "reveal_it":
        cards = [card for card in (locate(state, uid)[1] for uid in ctx.get("it", [])) if card]
        if cards:
            add_log(state, player, "revealed " + ", ".join(env.name(card["card"]) for card in cards))
            show_revealed(state, res, [card["card"] for card in cards])
        for uid in ctx.get("it", []):
            note_target(res, locate(state, uid)[1])
        ctx["pool"] = list(ctx.get("it", []))
    elif do == "pos_it":
        for uid in ctx.get("it", []):
            card = locate(state, uid)[1]
            if card:
                set_position(state, env, player, card, step["pos"])
    elif do == "pos_self":
        card = locate(state, res["uid"])[1]
        if card:
            card["pos"] = step["pos"]
            ctx["self_slot"] = ctx.get("self_slot") or slot_of(side, res["uid"])
    elif do == "pos_that":
        card = locate(state, ctx.get("that"))[1] if ctx.get("that") else None
        if card:
            note_target(res, card)
            set_position(state, env, player, card, step["pos"])
    elif do == "pay_stock":
        for _ in range(min(step["n"], len(zones["stock"]))):
            put(side, zones["stock"].pop(), "waiting")
        add_log(state, player, f"paid {step['n']} stock")
    elif do == "buff":
        apply_buff(step, res, state, env)
    elif do == "draw":
        if step.get("upto"):
            ask_number(res, {**step, "upto": False}, "How many cards to draw?")
            return
        drawn = 0
        for _ in range(step["n"]):
            if not zones["deck"] and zones["waiting"]:
                refresh(state, player, env.name, env.shuffle)
            if not zones["deck"]:
                break
            put(side, zones["deck"].pop(), "hand")
            drawn += 1
            counted(ctx, "drew")
        add_log(state, player, f"drew {drawn} card{'s' if drawn != 1 else ''}")
    elif do == "top":
        if step.get("upto"):
            ask_number(res, {**step, "upto": False}, "How many cards?")
            return
        owner = opponent if step.get("owner") == "opp" else player
        target = state["players"][owner]
        moved = []
        count = ctx.get(step["n_from"], 0) if step.get("n_from") else x_value(step.get("x"), state, player, None, ctx, env) if step.get("x_stat") else step["n"]
        for _ in range(count):
            if not target["zones"]["deck"]:
                break
            card = target["zones"]["deck"].pop(0 if step.get("bottom") else -1)
            put(target, card, step["to"])
            moved.append(card)
        ctx["flipped"] = [c["card"] for c in moved]
        if moved:  # "If that card is ...", "put it ..."
            ctx["revealed"] = moved[-1]["card"]
            ctx["it"], ctx["it_owner"] = [c["uid"] for c in moved], owner
        add_log(state, owner, f"put the top {len(moved)} of their deck into {LABELS[step['to']]}"
                + (": " + ", ".join(env.name(c["card"]) for c in moved) if step["to"] != "stock" else ""))
    elif do == "clock_card":
        if step.get("upto"):
            ask_number(res, {**step, "upto": False}, "How many cards?")
            return
        owner = opponent if step.get("owner") == "opp" else player
        target = state["players"][owner]
        for _ in range(step.get("n", 1)):
            clock = target["zones"]["clock"]
            if not clock:
                break
            card = clock.pop(-1 if step["end"] == "top" else 0)
            put(target, card, step["to"])
            add_log(state, owner, f"put {env.name(card['card'])} from their clock into {LABELS[step['to']]}")
    elif do == "look":
        if step.get("x_stat"):
            step = {**step, "n": x_value(step.get("x"), state, player, None, ctx, env), "x_stat": None}
        if step.get("upto"):
            ask_number(res, {**step, "upto": False}, "Look at how many cards?")
            return
        owner = opponent if step.get("owner") == "opp" else player
        deck = state["players"][owner]["zones"]["deck"]
        cards = list(reversed(deck[-step["n"]:])) if step["n"] else []
        ctx["among"] = [c["uid"] for c in cards]
        ctx["it"] = list(ctx["among"])
        ctx.pop("pool", None)
        ctx["it_owner"] = ctx["among_owner"] = owner
        add_log(state, player, f"looked at the top {len(cards)} of {'their' if owner == player else 'the opponent'}'s deck".replace("their's", "their"))
    elif do == "shuffle":
        owner = opponent if step.get("owner") == "opp" else player
        target = state["players"][owner]["zones"]["deck"]
        env.shuffle(target)
        for card in target:
            card["uid"] = new_uid()
        add_log(state, owner, "shuffled their deck")
    elif do == "reveal_top":
        if zones["deck"]:
            top = zones["deck"][-1]
            ctx["revealed"] = top["card"]
            ctx["it"], ctx["it_owner"] = [top["uid"]], player  # "put it into your hand"
            add_log(state, player, f"revealed the top card of their deck: {env.name(top['card'])}")
            show_revealed(state, res, [top["card"]])
    elif do == "flip":
        cards = list(reversed(zones["deck"][-step["n"]:]))
        ctx["it"] = [c["uid"] for c in cards]
        ctx["it_owner"] = player
        ctx["flipped"] = [c["card"] for c in cards]
        add_log(state, player, "flipped over " + (", ".join(env.name(c["card"]) for c in cards) or "nothing"))
        show_revealed(state, res, ctx["flipped"])
    elif do == "damage":
        amount = x_value(step.get("x"), state, player, None, ctx, env) if step.get("x_stat") else step["n"]
        if amount > 0:
            deal_damage(state, opponent, amount, amount, [], env.name, env.is_climax)
    elif do == "top_marker":
        slot = slot_of(side, res["uid"])
        if slot and zones["deck"]:
            put(side, zones["deck"].pop(), MARKER + slot, face_down=step.get("face_down"))
            add_log(state, player, f"put the top card of their deck under {LABELS[slot]} as a marker")
    elif do == "waiting_to_deck":
        owner = opponent if step.get("owner") == "opp" else player
        target = state["players"][owner]
        kept = set(ctx.get("it", [])) if step.get("except_it") else set()
        going = [c for c in target["zones"]["waiting"] if c["uid"] not in kept]
        target["zones"]["waiting"] = [c for c in target["zones"]["waiting"] if c["uid"] in kept]
        for card in going:
            put(target, card, "deck")
        add_log(state, owner, f"returned {len(going)} cards from their waiting room to their deck")
    elif do == "delay":
        state.setdefault("delayed", []).append({"player": player, "uid": res["uid"], "card": res["card"], "text": res["text"], "phase": step["phase"],
                                                "whose": step["whose"], "steps": step["then"], "ctx": copy.deepcopy(ctx)})
    elif do == "choose_battle":
        cards = [card for card in (locate(state, uid)[1] for uid in battle_uids(state)) if card]
        if cards:
            ctx["it_owner"] = None
            ask_cards(res, cards, player, min(step["min"], len(cards)), min(step["max"], len(cards)), step.get("text", "Choose"))
            res["prompt"]["zone"] = "stage"
    elif do == "choose_facing":
        facing = facing_card(state, player, locate(state, res["uid"])[1], ctx)
        if facing:
            ctx["it_before"], ctx["it"], ctx["it_owner"] = ctx.get("it", []), [facing["uid"]], opponent
    elif do == "place_each":
        for uid in reversed(ctx.get("it", [])[1:]):
            res["steps"].insert(0, {"do": "place_one", "uid": uid})
        if ctx.get("it"):
            res["steps"].insert(0, {"do": "place_one", "uid": ctx["it"][0]})
    elif do == "place_one":
        if locate(state, step["uid"])[1]:
            ctx["it"] = [step["uid"]]
            res["steps"].insert(0, {"do": "place", "open": True})
    elif do == "stock_to_clock":
        if zones["stock"]:
            put(side, zones["stock"].pop(), "clock")
            add_log(state, player, "put the top card of their stock into their clock")
    elif do == "pay_markers":
        slot = slot_of(side, res["uid"])
        if slot:
            for _ in range(min(step["n"], len(pile(side, MARKER + slot)))):
                card = pile(side, MARKER + slot).pop()
                put(side, card, "waiting")
                card["face_down"] = False
            add_log(state, player, f"paid {step['n']} marker(s)")
    elif do == "stock_card":
        owner = opponent if step.get("owner") == "opp" else player
        target = state["players"][owner]
        for _ in range(step.get("n", 1)):
            if target["zones"]["stock"]:
                put(target, target["zones"]["stock"].pop(0 if step["end"] == "bottom" else -1), "waiting")
        add_log(state, owner, f"put {step.get('n', 1)} card(s) from their stock into their waiting room")
    elif do == "that_it":
        if ctx.get("that") and locate(state, ctx["that"])[1]:  # otherwise "that character" is the card just revealed
            ctx["it"], ctx["it_owner"] = [ctx["that"]], locate(state, ctx["that"])[0]
    elif do == "add_self_to_it":
        ctx["it"] = [*ctx.get("it", []), res["uid"]]
    elif do == "rest_all":
        for card in stage_cards(side):
            if card["uid"] != res["uid"] and fits(step["filter"], card, env) and position_fits(step["filter"], card):
                card["pos"] = "rest"
        add_log(state, player, "rested their other characters")
    elif do == "stock_to_deck":
        owner = opponent if step.get("owner") == "opp" else player
        target = state["players"][owner]
        ctx["stock_returned"] = len(target["zones"]["stock"])
        to = step.get("to", "deck")
        for card in target["zones"]["stock"]:
            put(target, card, to)
        target["zones"]["stock"] = []
        add_log(state, owner, f"put {ctx['stock_returned']} cards from their stock into {LABELS[to]}")
    elif do == "exchange":
        first, second = (ctx.get("it_before") or [None])[0], (ctx.get("it") or [None])[0]
        if first and second:
            exchange_places(state, env, player, first, second)
    elif do == "swap_stage":
        cards = [locate(state, uid) for uid in ctx.get("it", [])]
        if len(cards) == 2 and all(where in STAGE_SLOTS for _, _, where in cards) and cards[0][0] == cards[1][0]:
            (owner, one, first), (_, two, second) = cards
            target = state["players"][owner]
            target["stage"][first], target["stage"][second] = two, one
            swap_markers(target, first, second)
            one["pos"] = two["pos"] = step.get("pos", "stand")
            add_log(state, player, f"exchanged {env.name(one['card'])} and {env.name(two['card'])}, both {'resting' if step.get('pos') == 'rest' else 'standing'}")
    elif do == "status_all":
        owner = opponent if step.get("owner") == "opp" else player
        for card in stage_cards(state["players"][owner]):
            state.setdefault("buffs", []).append({"uid": card["uid"], "status": step["status"], "expires": state["turn_number"]})
        add_log(state, owner, "can't use Encore this turn")
    elif do == "status":
        uid = (ctx.get("it") or [None])[0] if step["target"] == "it_first" else ctx.get(step["target"])
        if uid and locate(state, uid)[1]:
            note_target(res, locate(state, uid)[1])
            state.setdefault("buffs", []).append({"uid": uid, "status": step["status"], "expires": state["turn_number"] + (1 if step.get("until") == "next" else 0)})
            add_log(state, player, f"{env.name(locate(state, uid)[1]['card'])} " + {
                "no_reverse": "can't become reversed", "no_encore": "can't be encored", "no_side_loss": "keeps its soul in side attacks", "no_stand": "won't stand next stand phase"}[step["status"]])
    elif do == "all_mill":
        ctx["milled"] = {}
        for owner, target in state["players"].items():
            if target["zones"]["deck"]:
                card = target["zones"]["deck"].pop()
                put(target, card, "waiting")
                ctx["milled"][owner] = card["card"]
                add_log(state, owner, f"put {env.name(card['card'])} from the top of their deck into their waiting room")
    elif do == "which_deck":
        ask_choice(res, "which_deck", "Whose deck?", [("opp", "Your opponent's deck"), ("me", "Your deck")], step=step)
    elif do == "damage_choice":
        ask_choice(res, "damage_choice", "How much damage?", [(n, f"{n} damage") for n in step["options"]])
    elif do == "damage_times":
        times = max(0, x_value(step.get("x"), state, player, None, ctx, env))
        add_log(state, player, f"deals {step['n']} damage {times} time{'s' if times != 1 else ''}")
        res["steps"][:0] = [{"do": "damage", "n": step["n"]}] * times
    elif do == "reveal_top_cards":
        cards = list(reversed(zones["deck"][-step["n"]:]))
        ctx["flipped"] = [c["card"] for c in cards]
        add_log(state, player, "revealed the top of their deck: " + (", ".join(env.name(c["card"]) for c in cards) or "nothing"))
        show_revealed(state, res, ctx["flipped"])
    elif do == "rest_choice":
        left = among_them(state, {"among": ctx.get("among", []), "moved": ctx.get("moved", [])})
        if left:
            ask_choice(res, "rest_choice", "Where does the rest go?", [("waiting", "Waiting room"), ("deck", "Top of deck, in any order")],
                       cards=[dict(c) for c in left], owner=ctx.get("among_owner", player))
    elif do == "lowest_power":
        cards = [card for card in (locate(state, uid)[1] for uid in ctx.get("among", [])) if card]
        if cards:
            stats = compute_stats(state, env)[0]
            lowest = min(stats[c["uid"]]["power"] for c in cards)
            tied = [c for c in cards if stats[c["uid"]]["power"] == lowest]
            if len(tied) > 1:
                ask_cards(res, tied, ctx.get("it_owner", player), 1, 1, "Which of the lowest power?")
                res["prompt"]["zone"] = "among"
            else:
                ctx["it"] = [tied[0]["uid"]]
    elif do == "any_order":
        ask_choice(res, "any_order", "Which first?", [(i, o["text"]) for i, o in enumerate(step["options"])], step=step)
    elif do == "memory_to_markers":
        slot = slot_of(side, res["uid"])
        if slot:
            going = [c for c in zones["memory"] if fits(step["filter"], c, env)]
            zones["memory"] = [c for c in zones["memory"] if c not in going]
            for card in going:
                put(side, card, MARKER + slot)
            add_log(state, player, f"put {len(going)} card{'s' if len(going) != 1 else ''} from their memory under {LABELS[slot]} as markers")
    elif do == "self_under_it":
        # This card and all its markers go under the chosen character.
        to = slot_of(side, (ctx.get("it") or [None])[0]) if ctx.get("it") else None
        here = slot_of(side, res["uid"])
        if to and here:
            going = pile(side, MARKER + here)
            side["markers"][here] = []
            card, _ = take(side, res["uid"])
            for under in [*going, card]:
                put(side, under, MARKER + to)
            add_log(state, player, f"put {env.name(card['card'])} and {len(going)} marker(s) under {LABELS[to]}")
    elif do == "self_marker_on_it":
        slot = slot_of(side, (ctx.get("it") or [None])[0]) if ctx.get("it") else None
        if slot and locate(state, res["uid"])[0] == player:
            card, _ = take(side, res["uid"])
            put(side, card, MARKER + slot)
            add_log(state, player, f"put {env.name(card['card'])} under {LABELS[slot]} as a marker")
    elif do == "self_to":
        owner, card, where = locate(state, res["uid"])
        if card:
            if where in STAGE_SLOTS:
                ctx["self_slot"] = where
            move_card(state, env, player, owner, res["uid"], step["to"])
    elif do == "self_it":
        ctx["it"] = [res["uid"]] if locate(state, res["uid"])[1] else []
        ctx["it_owner"] = player
    elif do == "that_to":
        owner, card, _ = locate(state, ctx.get("that")) if ctx.get("that") else (None, None, None)
        if card:
            note_target(res, card)
            move_card(state, env, player, owner, card["uid"], step["to"])
    elif do == "double_check":
        if state.get("attack") and "checking" in state["attack"]:
            state["attack"]["checks"] = 2
    elif do == "double_check_pay":
        if state.get("attack") and state["attack"].get("checks") == 2:
            state["attack"]["check_pay"] = 1
    else:
        res["prompt"] = {"kind": "manual", "title": "Do this by hand", "text": res["text"]}


def exchange_places(state, env, actor, first, second):
    """Two cards of one player's swap places, each keeping its own state: a rested character stays
    rested. One going from the stage to another zone loses its markers; between stage slots they
    go with it. A card coming from a zone was never rested, so it arrives standing."""
    owner, one, where_one = locate(state, first)
    other, two, where_two = locate(state, second)
    if not one or not two or owner != other:
        return
    side = state["players"][owner]
    if where_one in STAGE_SLOTS and where_two in STAGE_SLOTS:
        side["stage"][where_one], side["stage"][where_two] = two, one
        swap_markers(side, where_one, where_two)
        add_log(state, actor, f"exchanged {env.name(one['card'])} and {env.name(two['card'])}")
        return
    take(side, first)
    take(side, second)
    for card, to, leaving in ((one, where_two, where_one), (two, where_one, where_two)):
        put(side, card, to)
        if leaving in STAGE_SLOTS:
            discard_markers(state, owner, leaving)
            if to == "waiting":
                fire(state, env, "leave", uid=card["uid"], source=card, source_owner=owner, slot=leaving)
    add_log(state, actor, f"exchanged {env.name(one['card'])} and {env.name(two['card'])}"
            if is_public(where_one, one) and is_public(where_two, two) else "exchanged two cards")


def apply_buff(step, res, state, env):
    player = res["player"]
    ctx = res["ctx"]
    if step["target"] == "it":
        cards = [locate(state, uid)[1] for uid in ctx.get("it", [])]
    elif step["target"] == "self":
        cards = [locate(state, res["uid"])[1]]
    elif step["target"] == "opp_center":
        them = state["players"][other_player(state, player)]
        cards = [them["stage"][slot] for slot in OPPOSITE if them["stage"][slot]]
    else:
        side = state["players"][player]
        cards = [c for c in stage_cards(side) if fits(step["filter"], c, env)]
    on_stage = {card["uid"] for side in state["players"].values() for card in stage_cards(side)}
    for card in cards:
        if not card or card["uid"] not in on_stage:
            continue
        power, soul = step.get("power", 0), step.get("soul", 0)
        if step.get("x_stat"):
            amount = x_value(step.get("x"), state, player, card, ctx, env)
            if step["x_stat"] == "power":
                power += amount
            else:
                soul += amount
        note_target(res, card)
        add_buff(state, card["uid"], step, power, soul)
        add_log(state, player, f"gave {env.name(card['card'])} {buff_label(power, soul, step.get('grant'))}")


def set_position(state, env, actor, card, pos):
    card["pos"] = pos
    add_log(state, actor, f"{ {'stand': 'stood', 'rest': 'rested', 'reverse': 'reversed'}[pos] } {env.name(card['card'])}")
    if pos == "reverse":
        owner = locate(state, card["uid"])[0]
        fire(state, env, "reverse", uid=card["uid"], owner=owner, card=card["card"])


def answer_ability(state, player, action, env):
    """The player's answer to the prompt of the ability being resolved."""
    res = state.get("resolving")
    prompt = (res or {}).get("prompt")
    if not prompt or prompt.get("player", res["player"]) != player:
        raise GameError("There's nothing for you to answer right now.")
    ctx = res["ctx"]
    kind = prompt["kind"]
    if kind == "manual":
        res["prompt"] = None
        add_log(state, player, "passed over a step it can't do automatically" if action.get("passed") else "finished a step by hand")
    elif kind == "cards":
        uids = list(dict.fromkeys(action.get("uids") or []))
        if not set(uids) <= set(prompt["options"]) or not prompt["min"] <= len(uids) <= prompt["max"]:
            raise GameError(f"Choose between {prompt['min']} and {prompt['max']} of those cards.")
        res["prompt"] = None
        purpose = prompt.get("for")
        if purpose == "order":
            owner = prompt["owner"]
            side = state["players"][owner]
            taken = [take(side, uid)[0] for uid in uids]
            for card in reversed(taken):
                put(side, card, "deck")
            add_log(state, player, f"put {len(taken)} cards back on top of the deck")
            return
        ctx["it_before"], ctx["it"] = ctx.get("it", []), uids
        if prompt.get("zone") in PUBLIC_CHOICES and not prompt.get("cost"):
            for uid in uids:
                note_target(res, locate(state, uid)[1])
        if prompt.get("zone") != "among":  # what's chosen is what a later "from among them" or "the rest" means
            ctx["among"] = list(uids)
            ctx["among_owner"] = prompt["owner"]
            ctx.pop("pool", None)
    else:
        value = action.get("value")
        if value not in [option["value"] for option in prompt["options"]]:
            raise GameError("That's not one of the choices.")
        res["prompt"] = None
        purpose = prompt["for"]
        step = prompt.get("step")
        if purpose == "may":
            if value == "yes":
                res["steps"][:0] = cost_steps(step.get("cost")) + step.get("then", [])
            else:
                ctx["declined"] = True
                add_log(state, player, "chose not to")
        elif purpose == "options":
            res["steps"][:0] = step["options"][value]["steps"]
        elif purpose == "any_order":
            left = [o for i, o in enumerate(step["options"]) if i != value]
            res["steps"][:0] = step["options"][value]["steps"] + (
                [{"do": "any_order", "options": left}] if len(left) > 1 else left[0]["steps"] if left else [])
        elif purpose == "which_deck":
            res["steps"].insert(0, {"do": "top", "n": step["n"], "owner": value, "to": "waiting"})
        elif purpose == "damage_choice":
            res["steps"].insert(0, {"do": "damage", "n": value})
        elif purpose == "rest_choice":
            res["steps"].insert(0, {"do": "order_top"} if value == "deck" else {"do": "rest", "to": "waiting"})
        elif purpose == "number":
            res["steps"].insert(0, {**step, "n": value})
        elif purpose == "dest":
            owner = prompt.get("owner", player)
            for uid in ctx.get("it", []):
                if locate(state, uid)[1]:
                    move_card(state, env, player, owner, uid, value)
                    ctx.setdefault("moved", []).append(uid)
                    if value in ("hand", "stock"):
                        counted(ctx, value)
        elif purpose == "place":
            side = state["players"][prompt.get("owner", player)]
            for uid in ctx.get("it", []):
                card, src = take(side, uid)
                occupant = put(side, card, value)
                if src in STAGE_SLOTS:
                    swap_markers(side, src, value)
                if not prompt.get("keep_pos"):
                    card["pos"] = "rest" if prompt.get("rest") else "stand"
                if occupant:
                    put(side, occupant, "waiting")
                    discard_markers(state, player, value)
                    fire(state, env, "leave", uid=occupant["uid"], source=occupant, source_owner=player, slot=value)
                add_log(state, player, f"put {env.name(card['card'])} on {LABELS[value]}")
                break


def act_status(state, player, card, ability, where, env):
    """Why this card's ability can't be activated now, or None if it can."""
    if rules_on(state):
        if state["turn"] != player or state.get("phase") != "main":
            return "only in your main phase"
    if abilities_busy(state):
        return "another ability is resolving"
    if used_up(state, card, ability):
        return "already used this turn"
    if where in STAGE_SLOTS and card["face_down"]:
        return "this card is face down"
    return can_pay(ability.get("cost"), state, player, card, env)


def activatable(ability):
    """ACT abilities, and AUTO abilities whose trigger couldn't be read (so they can be started by hand)."""
    return ability["kind"] == "act" or (ability["kind"] == "auto" and not ability.get("when"))


def player_acts(state, player, env):
    """{uid: [{"index", "text", "why"}, ...]} for the cards that show the ! button."""
    side = state["players"][player]
    result = {}
    places = [(c, slot_of(side, c["uid"])) for c in stage_cards(side)] + [(c, "waiting") for c in side["zones"]["waiting"]]
    for card, where in places:
        rows = []
        for index, ability in enumerate(abilities_of(state, card, env)):
            if not activatable(ability):
                continue
            wants = ability.get("where")
            if (where == "waiting") != (wants == "waiting"):
                continue
            rows.append({"index": index, "card": card["card"], "text": ability["text"], "why": act_status(state, player, card, ability, where, env)})
        if rows:
            result[card["uid"]] = rows
    return result


def activate(state, player, action, env):
    """The ! button: pay an activated ability's cost and resolve it."""
    side = state["players"][player]
    where, _ = find(side, action.get("uid", ""))
    card = locate(state, action["uid"])[1]
    found = abilities_of(state, card, env)
    try:
        ability = found[int(action.get("index", 0))]
    except (TypeError, ValueError, IndexError):
        raise GameError("That card doesn't have that ability.")
    if not activatable(ability):
        raise GameError("That ability can't be activated.")
    why = act_status(state, player, card, ability, where, env)
    if why:
        raise GameError(f"Can't activate that: {why}.")
    add_log(state, player, f"activated {env.name(card['card'])}: {ability['text']}")
    if not ability.get("when") and ability["kind"] == "auto":
        ability = {**ability, "steps": [{"do": "manual", "text": ability["text"]}]}
    entry = {"player": player, "uid": card["uid"], "card": card["card"], "ability": copy.deepcopy(ability),
             "ctx": {"source_uid": card["uid"], "self_slot": where if where in STAGE_SLOTS else None}, "accepted": False}
    activate_steps(entry)
    start_resolving(state, entry, env)
    fire(state, env, "act", player=player)


def trigger_ability(state, player, action, env):
    """A queued ability's prompt answered: trigger it, or skip it."""
    if state.get("resolving") or state.get("ability_show"):
        raise GameError("Finish the ability being resolved first.")
    queue = state.get("ability_queue") or []
    entry = next((e for e in queue if e["id"] == action.get("id")), None)
    if not entry or entry["player"] != player:
        raise GameError("That ability isn't waiting for you.")
    if queue_chooser(state) != player:
        raise GameError("The other player's abilities go first.")
    queue.remove(entry)
    if not queue:
        state.pop("ability_queue", None)
    name = env.name(entry["card"])
    if not action.get("accept"):
        add_log(state, player, f"skipped the ability of {name}")
        if entry.get("event"):
            finish_event(state, {"event": True, "uid": entry["uid"]}, env)
        return
    add_log(state, player, f"triggered the ability of {name}")
    start_resolving(state, entry, env)


def queue_chooser(state):
    """Whose queued abilities come next: the turn player's first."""
    queue = state.get("ability_queue") or []
    if any(e["player"] == state["turn"] for e in queue):
        return state["turn"]
    return queue[0]["player"] if queue else None


def ability_view(state, player):
    """What the page shows about abilities: the running ability (its prompt, which can show hidden
    cards, only to the player answering it) and queued abilities to trigger."""
    shown = state.get("ability_show")
    if shown:
        return {"resolving": True, "mine": shown["player"] == player, "card": shown["card"], "uid": shown["uid"], "text": shown["text"],
                "by": state["players"][shown["player"]]["name"], "prompt": None}
    res = state.get("resolving")
    if res:
        prompt = res.get("prompt")
        answering = (prompt or {}).get("player", res["player"])
        mine = answering == player
        return {"resolving": True, "mine": mine, "card": res["card"], "uid": res["uid"], "text": res["text"],
                "by": state["players"][answering]["name"],
                "can_stop": res["player"] == player,
                "prompt": prompt_view(state, prompt) if prompt and mine else None}
    queue = state.get("ability_queue") or []
    if not queue:
        return None
    chooser = queue_chooser(state)
    if chooser != player:
        return {"resolving": False, "mine": False, "by": state["players"][chooser]["name"]}
    return {"resolving": False, "mine": True, "queue": [
        {"id": e["id"], "card": e["card"], "uid": e["uid"], "text": e["ability"]["text"], "event": e.get("event", False)}
        for e in queue if e["player"] == player]}


def prompt_view(state, prompt):
    """A prompt for the player answering it. Face-down cards of the opponent's stay face down."""
    shown = {key: value for key, value in prompt.items() if key != "step"}
    if "cards" in shown:
        cards = []
        for card in shown["cards"]:
            where = locate(state, card["uid"])[2]
            hidden = where in STAGE_SLOTS and card["face_down"] and prompt.get("owner") != state["resolving"]["player"]
            cards.append({**card_view(card, not hidden), "where": where})
        shown["cards"] = cards
    return shown


# --- What each player sees -------------------------------------------------------------------------

def card_view(card, visible):
    return {"uid": card["uid"], "card": card["card"] if visible else None,
            "pos": card["pos"], "face_down": card["face_down"]}


def side_view(side, mine):
    zones = {}
    for zone, cards in side["zones"].items():
        if zone in HIDDEN_ZONES or (zone in PRIVATE_ZONES and not mine):
            zones[zone] = {"count": len(cards)}
        else:
            zones[zone] = [card_view(c, mine or not c["face_down"]) for c in cards]
    stage = {slot: card_view(c, mine or not c["face_down"]) if c else None for slot, c in side["stage"].items()}
    markers = {slot: [card_view(c, mine or not c["face_down"]) for c in side.get("markers", {}).get(slot, [])]
               for slot in STAGE_SLOTS}
    return {"name": side["name"], "zones": zones, "stage": stage, "markers": markers,
            "refreshes": side.get("refreshes", 0), "level_ups": side.get("level_ups", 0),
            "climaxes": side.get("climaxes", 0)}


def visible_cards(view):
    """Card pks that appear face up in a player's view (so their details can be sent along)."""
    pks = set()
    for side in (view.get("me"), view.get("opponent")):
        if not side:
            continue
        for cards in side["zones"].values():
            if isinstance(cards, list):
                pks.update(c["card"] for c in cards if c["card"])
        pks.update(c["card"] for c in side["stage"].values() if c and c["card"])
        for cards in side.get("markers", {}).values():
            pks.update(c["card"] for c in cards if c["card"])
    if (view.get("reveal") or {}).get("card"):
        pks.add(view["reveal"]["card"])
    ability = view.get("ability") or {}
    if ability.get("card"):
        pks.add(ability["card"])
    pks.update(entry["card"] for entry in ability.get("queue", []))
    pks.update(c["card"] for c in (ability.get("prompt") or {}).get("cards", []) if c["card"])
    pks.update(row["card"] for rows in view.get("acts", {}).values() for row in rows)
    shown = view.get("ability_show") or {}
    if shown:
        pks.update([shown["card"], *shown["targets"], *(shown.get("check") or [])])
    return pks


def attack_view(state, player):
    attack = state.get("attack")
    if not attack:
        return None
    shown = {k: v for k, v in attack.items() if k not in ("counters", "dealt", "cancelled", "soul_extra", "cancel_fired", "checks", "check_pay")}
    if player != state["turn"]:
        shown["counters"] = attack.get("counters", [])
    return shown


def stats_view(state, player):
    """Characters' current power and soul, for the ones this player can see."""
    shown = {}
    for owner, side in state["players"].items():
        for card in stage_cards(side):
            if (owner == player or not card["face_down"]) and card["uid"] in state.get("stats", {}):
                shown[card["uid"]] = state["stats"][card["uid"]]
    return shown


def view(state, player):
    """The board from one player's seat: their own side in full, the opponent's with hidden zones as counts."""
    player = str(player)
    other = next((p for p in state["order"] if p != player), None)
    return {
        "me": side_view(state["players"][player], True),
        "opponent": side_view(state["players"][other], False) if other else None,
        "my_turn": state["turn"] == player,
        # This player's page should send "resolve_damage" shortly (a climax cancelled their damage).
        "damage_pending": state.get("pending_damage", {}).get("player") == player,
        # This player's page should send "continue_damage" shortly (a damage emptied their deck).
        "refresh_pending": state.get("pending_refresh", {}).get("player") == player,
        # This player has to choose a clock card for their level zone before playing on.
        "level_up_pending": must_level_up(state, player),
        "turn_number": state["turn_number"],
        "game_number": state.get("game_number", 1),
        "rps": rps_view(state, player),
        "phase": state.get("phase", "main"),
        "attacks": state.get("attacks", 0),
        "rules": rules_on(state),
        # The end phase's discard: {"count": n, "mine": is it this player's}.
        "discard": ({"count": state["pending_discard"]["count"], "mine": state["pending_discard"]["player"] == player}
                    if state.get("pending_discard") else None),
        # Whether each player has finished their mulligan (only during the mulligan phase).
        "mulligan": ({"me": player in state.get("mulligan_done", []),
                      "opponent": other in state.get("mulligan_done", [])} if state.get("phase") == "mulligan" else None),
        # A hand card being shown: to the opponent as {"card", "by"}, to its owner as {"mine": True}.
        "reveal": (None if not state.get("reveal")
                   else {"mine": True} if state["reveal"]["player"] == player
                   else {"card": state["reveal"]["card"], "by": state["players"][state["reveal"]["player"]]["name"]}),
        "auto_next": state.get("auto_next"),
        # {"mine": did this player ask, "on": turning the rules on (or off)}
        "rules_request": ({"mine": state["rules_request"]["player"] == player, "on": state["rules_request"]["on"]}
                          if state.get("rules_request") else None),
        # The attack in progress (step, kind, attacker's slot, target slot, soul) during the attack
        # phase; "counters" (the defender's playable counter cards) only goes to the defender.
        "attack": attack_view(state, player),
        # A climax this player just played is showing; their page moves on to the attack phase shortly.
        "climax_pending": state.get("pending_climax") == player,
        # {"won": did this player win, "rematch": have they asked, "opponent_rematch": has the other player}
        "game_over": ({"won": state["game_over"]["winner"] == player, "reason": state["game_over"].get("reason", "level"), "rematch": player in state["game_over"]["rematch"],
                       "opponent_rematch": other in state["game_over"]["rematch"]} if state.get("game_over") else None),
        # Games won in this series, for the first player and then the second, on both players' screens.
        "match_wins": [{"name": state["players"][p]["name"], "wins": state.get("match_wins", {}).get(p, 0)} for p in state["order"]],
        "ability": ability_view(state, player),
        # An ability that just resolved, for both pages to show: {"id", "card", "targets": [card, ...], "mine"}.
        "ability_show": ({"id": state["ability_show"]["id"], "card": state["ability_show"]["card"], "targets": state["ability_show"]["targets"],
                          "check": state["ability_show"].get("check"), "label": state["ability_show"].get("label"), "mine": state["ability_show"]["player"] == player} if state.get("ability_show") else None),
        "needs_color": state.get("needs_color", {}).get(player, {}),
        # Characters that can't be encored this turn.
        "no_encore": [b["uid"] for b in state.get("buffs", []) if b.get("status") == "no_encore"],
        "stats": stats_view(state, player),
        # This player's cards with a ! button, and why each ability can't be activated right now.
        "acts": state.get("acts", {}).get(player, {}),
        "log": state["log"][-50:],
    }
