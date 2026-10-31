"""A two-player Weiss Schwarz virtual tabletop: game state, moves, and what each player may see.

There is no rule checking; players move their own cards like at a real table. The server's job
is to keep hidden things hidden (hands, deck and stock order) and to keep both boards in sync.

State is plain JSON, stored on the GameRoom:

    {"players": {"<user id>": {"name": ..., "zones": {zone: [card, ...]}, "stage": {slot: card|None},
                               "markers": {slot: [card, ...]}, "refreshes": n, "level_ups": n, "climaxes": n}},
     "order": [host id, guest id], "turn": "<user id>", "turn_number": 1, "phase": "mulligan", "log": [...],
     "mulligan_done": [user id, ...],  # during the mulligan: who has finished theirs
     "reveal": {"player": id, "uid": ..., "card": pk},  # a hand card shown to the opponent, until they close it
     "pending_damage": {...},  # only while a cancelled damage waits to be cleaned up
     "pending_refresh": {...},  # only while a damage waits for the emptied deck to be refreshed
     "pending_climax": "<user id>",  # only while a climax just played shows before the attack phase
     "attacks": n,  # attacks made this turn (the first player's first turn allows only one)
     "attack": {"step": ...},  # during the attack phase (with turn rules on): the attack in progress
     "rules": bool,  # turn rules on (the default) or off (a free-form table), changed by both players agreeing
     "rules_request": {"player": id, "on": bool},  # one player has asked to turn the rules on or off
     "auto_next": phase}  # a phase that has ended itself: the turn player's page moves on to this
                         # one after a pause, so phase changes can be followed

With turn rules on, phases end themselves when there's nothing left to do in them, the page offers
only the shortcuts for the current phase, playing a card pays its cost, and the attack phase runs as
the rules' steps: declare (front, side or direct), trigger, counter, damage and battle.

A card instance is {"uid": "a1b2c3d4", "card": <Card pk>, "pos": "stand"|"rest"|"reverse",
"face_down": bool}. The top of a pile is the end of its list.

Markers are cards set under a character on the stage. Each slot's markers are a pile named
"marker:<slot>"; they move with the character between slots and go to the waiting room when it
leaves the stage.
"""
import random
import re
import secrets

ZONES = ["deck", "hand", "clock", "level", "stock", "waiting", "memory", "climax", "resolution"]
STAGE_SLOTS = ["C1", "C2", "C3", "B1", "B2"]
MARKER = "marker:"
MARKER_PILES = [MARKER + slot for slot in STAGE_SLOTS]
HIDDEN_ZONES = {"deck", "stock"}  # face down: no one sees the cards (the owner can search or peek)
PRIVATE_ZONES = {"hand"}  # only the owner sees the cards
POSITIONS = {"stand", "rest", "reverse"}
STARTING_HAND = 5
ENCORE_COST = 3  # stock paid to keep a reversed character on the stage, rested
LEVEL_UP_AT = 7  # clock cards that make a level
CLOCK_DRAW = 2  # cards drawn after putting a card from the hand into the clock
PHASES = ["mulligan", "stand", "draw", "clock", "main", "climax", "attack", "encore", "end"]  # mulligan: turn 1 only
PLAY_ZONES = set(STAGE_SLOTS) | {"climax", "resolution"}  # playing a card from the hand here pays its cost
ATTACK_STEPS = ["declare", "trigger", "counter", "damage", "battle"]
ATTACK_KINDS = {"front", "side", "direct"}
TRIGGER_CHOICES = {"comeback": {"hand"}, "gate": {"hand"}, "choice": {"hand", "stock"},
                   "standby": set(STAGE_SLOTS), "treasure": set()}  # trigger icon -> where its card may go
OPPOSITE = {"C1": "C3", "C2": "C2", "C3": "C1"}  # the opponent's slot facing each center slot
CLIMAX_BOOST = re.compile(r"all of your characters get \+(\d+) power and \+(\d+) soul", re.I)
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


def new_game(players, shuffle=random.shuffle):
    """players: [(user id, display name, [card pk, ...]), ...] with the host first, who takes the first turn."""
    state = {"players": {}, "order": [str(p[0]) for p in players], "turn": str(players[0][0]),
             "turn_number": 1, "phase": "mulligan", "mulligan_done": [], "log": []}
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
    return state


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


def stand_all(side):
    """Stand every character; True if any wasn't standing."""
    changed = False
    for card in side["stage"].values():
        if card and card["pos"] != "stand":
            card["pos"] = "stand"
            changed = True
    return changed


def rules_on(state):
    return state.get("rules", True)


def other_player(state, player):
    return next(p for p in state["order"] if p != player)


def climax_boost(state, player, info):
    """(power, soul) every character of this player gets from the climax in their climax zone."""
    climax = state["players"][player]["zones"]["climax"]
    if climax and not climax[-1]["face_down"]:
        match = CLIMAX_BOOST.search(info(climax[-1]["card"]).get("text") or "")
        if match:
            return int(match[1]), int(match[2])
    return 0, 0


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


def counter_play(state, player, card, info):
    """(stock to pay, backup power) if this hand card can be played as a counter right now, else None:
    it says 【COUNTER】, its level is within the player's, and the stock covers it."""
    details = info(card["card"])
    text = details.get("text") or ""
    if "【COUNTER】" not in text.upper():
        return None
    backup = BACKUP.search(text)
    if backup:
        power, level, price = int(backup[1]), number(backup[2]), number(backup[3])
    else:
        power, level, price = 0, number(details.get("level")), number(details.get("cost"))
    zones = state["players"][player]["zones"]
    if level > len(zones["level"]) or price > len(zones["stock"]):
        return None
    return price, power


def counters_for(state, player, info):
    return [c["uid"] for c in state["players"][player]["zones"]["hand"] if counter_play(state, player, c, info)]


def declare_attack(state, player, slot, kind, name, shuffle, trigger, info):
    """The declaration and trigger steps of an attack: rest the attacker, check the top card of the
    deck for its trigger (soul icons add to this attack's damage; the card then goes to the stock,
    or a treasure to the hand), and set up the counter or damage step."""
    side = state["players"][player]
    zones = side["zones"]
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
    attacker = name(card["card"]) if not card["face_down"] else "a character"
    add_log(state, player, f"{kind} attack with {attacker}"
            + (f" against {name(opposing['card'])}" if opposing else ""))
    # Trigger step.
    if not zones["deck"] and zones["waiting"]:
        refresh(state, player, name, shuffle)
    icons = []
    if zones["deck"]:
        checked = zones["deck"].pop()
        icons = (trigger(checked["card"]) or "").split()
        put(side, checked, "hand" if "treasure" in icons else "stock")
        add_log(state, player, f"trigger check: {name(checked['card'])}"
                + (f" [{' '.join(icons)}]" if icons else " (no trigger)")
                + (" — to their hand" if "treasure" in icons else " — to their stock"))
    trigger_soul = icons.count("soul")
    # The damage this attack will deal: soul, plus the climax's and the trigger's, +1 if direct, or
    # minus the defender's level for a side attack.
    soul = number(info(card["card"]).get("soul")) + climax_boost(state, player, info)[1] + trigger_soul
    if kind == "direct":
        soul += 1
    elif kind == "side":
        soul = max(0, soul - number(info(opposing["card"]).get("level")))
    state["attack"] = {"step": "trigger", "slot": slot, "uid": card["uid"], "target": target, "kind": kind,
                       "soul": soul, "backup": 0, "shot": "shot" in icons}
    prompt = trigger_prompt(state, player, icons, info)
    if prompt:
        state["attack"]["prompt"] = prompt  # the attacker chooses (see the trigger_choice action)
    else:
        after_trigger(state, info)


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


def after_trigger(state, info):
    """The trigger step is done: on to the counter step (if the defender can counter a front or side
    attack) or the damage step."""
    attack = state["attack"]
    attack["step"] = "damage"
    if attack["kind"] != "direct":
        counters = counters_for(state, other_player(state, state["turn"]), info)
        if counters:
            attack.update(step="counter", counters=counters)


def power_of(state, player, card, info):
    return number(info(card["card"]).get("power")) + climax_boost(state, player, info)[0]


def advance_attack(state, name, shuffle, is_climax, info):
    """Move the attack phase along while nobody has a choice to make: deal an attack's damage once
    its counter step is over, battle once that damage (and any level up) is done, and end the
    phase when the turn player has no attack left to make."""
    while rules_on(state) and state.get("phase") == "attack" and state.get("attack"):
        attack = state["attack"]
        player = state["turn"]
        defender = other_player(state, player)
        step = attack["step"]
        if step == "declare":
            if not can_attack(state, player) and state.get("auto_next") != "encore":
                add_log(state, player, "no attacks left")
                state["auto_next"] = "encore"
            return
        if step in ("trigger", "counter"):
            return  # the attacker resolves a trigger, or the defender plays a counter or passes
        if step == "damage":
            if not attack.get("dealt"):
                attack["dealt"] = True
                if attack["soul"]:
                    deal_damage(state, defender, attack["soul"], attack["soul"], [], name, is_climax)
                    attack["cancelled"] = state.get("pending_damage", {}).get("player") == defender
                else:
                    add_log(state, defender, "took no damage")
                continue
            if damage_in_progress(state, defender) or must_level_up(state, defender):
                return  # the damage or a level up is still being worked out
            if attack.pop("shot", False) and attack.get("cancelled"):
                # Shot trigger: this attack's damage was cancelled, so it deals 1 damage more.
                add_log(state, player, "shot trigger: 1 more damage")
                deal_damage(state, defender, 1, 1, [], name, is_climax)
                continue
            attack["step"] = "battle" if attack["kind"] == "front" else "declare"
            if attack["step"] == "declare":
                state["attack"] = {"step": "declare"}
            continue
        if step == "battle":
            attacker = state["players"][player]["stage"][attack["slot"]]
            target = state["players"][defender]["stage"][attack["target"]]
            if attacker and target and attacker["uid"] == attack["uid"]:
                mine = power_of(state, player, attacker, info)
                theirs = power_of(state, defender, target, info) + attack["backup"]
                losers = ([attacker] if mine <= theirs else []) + ([target] if theirs <= mine else [])
                for card in losers:
                    card["pos"] = "reverse"
                add_log(state, player, f"battle: {name(attacker['card'])} ({mine}) against {name(target['card'])} ({theirs})"
                        + " — " + (", ".join(f"{name(c['card'])} reversed" for c in losers)))
            state["attack"] = {"step": "declare"}
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


def enter_phase(state, player, phase, name, shuffle):
    """Move the turn player into a phase. With turn rules on, the draw phase draws a card and ends
    itself; the end phase clears the climax zone and passes the turn into the next player's stand
    phase, which stands their characters and ends itself. ("Ends itself" sets auto_next.)
    Other phases only change what the page offers."""
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
        draw_step(state, player, name, shuffle)
        state["auto_next"] = "clock"
    elif phase == "end":
        climaxes, zones["climax"] = zones["climax"], []
        for card in climaxes:
            put(side, card, "waiting")
            card["face_down"] = False
        if climaxes:
            add_log(state, player, "put " + ", ".join(name(c["card"]) for c in climaxes)
                    + " from the climax zone into the waiting room")
        other = next(p for p in state["order"] if p != player)
        state["turn"] = other
        state["turn_number"] += 1
        state["attacks"] = 0
        add_log(state, player, f"ended their turn. Turn {state['turn_number']}: {state['players'][other]['name']}")
        state["phase"] = "stand"
        if rules:
            if stand_all(state["players"][other]):
                add_log(state, other, "stand phase: stood all their characters")
            state["auto_next"] = "draw"
    else:
        add_log(state, player, f"moved to the {phase} phase")


def auto_end_encore(state, name, shuffle):
    """The encore step is over once no reversed characters are left: the turn moves to its end."""
    if rules_on(state) and state.get("phase") == "encore" and not reversed_characters(state):
        state["auto_next"] = "end"


def auto_refresh(state, name, shuffle):
    """Whenever a player's deck is empty and their waiting room isn't, they deck out at once, unless
    a damage of theirs is still being worked out (that refreshes, or resolves, first)."""
    for player, side in state["players"].items():
        if not damage_in_progress(state, player) and not side["zones"]["deck"] and side["zones"]["waiting"]:
            refresh(state, player, name, shuffle)


def apply(state, player, action, name=lambda pk: f"card {pk}", shuffle=random.shuffle,
          is_climax=lambda pk: False, trigger=lambda pk: "", cost=lambda pk: 0, info=lambda pk: {}):
    """Apply one player's action to the state in place. Returns extra data for that player only
    (e.g. the cards they searched), or {}. Raises GameError for anything invalid.

    `info` gives a card's details for the rules (power, soul, level, cost, text)."""
    extra = apply_action(state, player, action, name, shuffle, is_climax, trigger, cost, info)
    auto_refresh(state, name, shuffle)
    advance_attack(state, name, shuffle, is_climax, info)
    auto_end_encore(state, name, shuffle)
    return extra


def apply_action(state, player, action, name, shuffle, is_climax, trigger, cost, info):
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

    if kind == "move":
        to = zone_arg(action, "to", set(ZONES) | set(STAGE_SLOTS) | set(MARKER_PILES))
        src, index = find(side, action.get("uid", ""))
        check_marker_target(side, to, leaving=src)
        if (action.get("end_main") and to == "climax" and src == "hand" and rules_on(state)
                and state["turn"] == player and state.get("phase") == "main"):
            # A climax played from the main phase (the page asks first): that ends the main phase,
            # so it's played in the climax phase, and the attack phase follows.
            enter_phase(state, player, "climax", name, shuffle)
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
            if src in STAGE_SLOTS:
                discard_markers(state, player, src)
        add_log(state, player, describe_move(card, src, to, name)
                + (f" (paid {price} stock)" if price else ""))
        if to == "climax" and rules_on(state) and state["turn"] == player and state.get("phase") == "climax":
            # Played in the climax phase: both pages show it, then the turn player's page moves on
            # to the attack phase.
            side["climaxes"] = side.get("climaxes", 0) + 1
            state["pending_climax"] = player
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
        return {}

    if kind == "flip":
        where, index = find(side, action.get("uid", ""))
        if where in HIDDEN_ZONES or where in PRIVATE_ZONES:
            raise GameError("Cards there are already hidden.")
        card = side["stage"][where] if where in STAGE_SLOTS else pile(side, where)[index]
        card["face_down"] = not card["face_down"]
        add_log(state, player, f"turned a card in their {LABELS[where]} face {'down' if card['face_down'] else 'up'}")
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
            if not can_attack(state, player):
                raise GameError("Only one character can attack on the first turn.")
            declare_attack(state, player, where, action.get("kind"), name, shuffle, trigger, info)
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
        if kind == "counter":
            where, index = find(side, action.get("uid", ""))
            play = counter_play(state, player, zones["hand"][index], info) if where == "hand" else None
            if not play:
                raise GameError("That card can't be played as a counter now.")
            price, power = play
            card = zones["hand"].pop(index)
            for _ in range(price):
                put(side, zones["stock"].pop(), "waiting")
            put(side, card, "waiting")
            attack["backup"] += power
            add_log(state, player, f"countered with {name(card['card'])}"
                    + (f" (+{power} power)" if power else "") + (f", paying {price} stock" if price else ""))
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
        state.pop("attack", None)
        state.pop("pending_climax", None)
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
            enter_phase(state, player, phase, name, shuffle)
            if rules and phase == "encore" and reversed_characters(state):
                break  # wait here for the encore choices
        return {}

    if kind == "chat":
        text = " ".join(str(action.get("text", "")).split())[:300]
        if not text:
            raise GameError("Type a message first.")
        state["log"].append({"who": side["name"], "text": text, "chat": True})
        del state["log"][:-MAX_LOG]
        return {}

    raise GameError(f"Unknown action: {kind!r}")


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
    return pks


def attack_view(state, player):
    attack = state.get("attack")
    if not attack:
        return None
    shown = {k: v for k, v in attack.items() if k not in ("counters", "dealt", "cancelled")}
    if player != state["turn"]:
        shown["counters"] = attack.get("counters", [])
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
        "phase": state.get("phase", "main"),
        "attacks": state.get("attacks", 0),
        "rules": rules_on(state),
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
        "log": state["log"][-50:],
    }
