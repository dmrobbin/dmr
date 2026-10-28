"""A two-player Weiss Schwarz virtual tabletop: game state, moves, and what each player may see.

There is no rule checking; players move their own cards like at a real table. The server's job
is to keep hidden things hidden (hands, deck and stock order) and to keep both boards in sync.

State is plain JSON, stored on the GameRoom:

    {"players": {"<user id>": {"name": ..., "zones": {zone: [card, ...]}, "stage": {slot: card|None}}},
     "order": [host id, guest id], "turn": "<user id>", "turn_number": 1, "log": [...]}

A card instance is {"uid": "a1b2c3d4", "card": <Card pk>, "pos": "stand"|"rest"|"reverse",
"face_down": bool}. The top of a pile is the end of its list.
"""
import random
import secrets

ZONES = ["deck", "hand", "clock", "level", "stock", "waiting", "memory", "climax", "resolution"]
STAGE_SLOTS = ["C1", "C2", "C3", "B1", "B2"]
HIDDEN_ZONES = {"deck", "stock"}  # face down: no one sees the cards (the owner can search or peek)
PRIVATE_ZONES = {"hand"}  # only the owner sees the cards
POSITIONS = {"stand", "rest", "reverse"}
STARTING_HAND = 5
MAX_LOG = 100

LABELS = {
    "deck": "deck", "hand": "hand", "clock": "clock", "level": "level", "stock": "stock",
    "waiting": "waiting room", "memory": "memory", "climax": "climax zone", "resolution": "resolution zone",
    "C1": "center stage (left)", "C2": "center stage (middle)", "C3": "center stage (right)",
    "B1": "back stage (left)", "B2": "back stage (right)",
}


class GameError(Exception):
    pass


def new_uid():
    return secrets.token_hex(4)


def new_card(card_pk):
    return {"uid": new_uid(), "card": card_pk, "pos": "stand", "face_down": False}


def new_game(players, shuffle=random.shuffle):
    """players: [(user id, display name, [card pk, ...]), ...] with the host first, who takes the first turn."""
    state = {"players": {}, "order": [str(p[0]) for p in players], "turn": str(players[0][0]),
             "turn_number": 1, "log": []}
    for user_id, name, cards in players:
        deck = [new_card(pk) for pk in cards]
        shuffle(deck)
        zones = {zone: [] for zone in ZONES}
        zones["deck"] = deck
        zones["hand"] = [deck.pop() for _ in range(min(STARTING_HAND, len(deck)))]
        state["players"][str(user_id)] = {"name": name, "zones": zones, "stage": {s: None for s in STAGE_SLOTS}}
    add_log(state, None, f"Game started. Each player shuffled and drew {STARTING_HAND} cards.")
    return state


def add_log(state, player, text):
    who = state["players"][player]["name"] if player else ""
    state["log"].append({"who": who, "text": text})
    del state["log"][:-MAX_LOG]


# --- Finding and moving cards ---------------------------------------------------------------------

def find(side, uid):
    """(where, index) of a card on one player's side; where is a zone name or a stage slot."""
    for zone, cards in side["zones"].items():
        for i, card in enumerate(cards):
            if card["uid"] == uid:
                return zone, i
    for slot, card in side["stage"].items():
        if card and card["uid"] == uid:
            return slot, None
    raise GameError("That card isn't on your side of the board.")


def take(side, uid):
    where, index = find(side, uid)
    if where in STAGE_SLOTS:
        card, side["stage"][where] = side["stage"][where], None
    else:
        card = side["zones"][where].pop(index)
    return card, where


def put(side, card, to, where="top"):
    """Place a card in a zone or stage slot. Returns whatever was already in that slot, if anything."""
    if to in STAGE_SLOTS:
        occupant, side["stage"][to] = side["stage"][to], card
        return occupant
    if to not in ZONES:
        raise GameError(f"Unknown zone: {to}")
    card["pos"] = "stand"
    if to in HIDDEN_ZONES or to == "hand":
        card["face_down"] = False  # orientation is meaningless once the card is hidden
    pile = side["zones"][to]
    if where == "bottom":
        pile.insert(0, card)
    else:
        pile.append(card)
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


def apply(state, player, action, name=lambda pk: f"card {pk}", shuffle=random.shuffle):
    """Apply one player's action to the state in place. Returns extra data for that player only
    (e.g. the cards they searched), or {}. Raises GameError for anything invalid."""
    player = str(player)
    if player not in state["players"]:
        raise GameError("You're not playing in this game.")
    side = state["players"][player]
    zones = side["zones"]
    kind = action.get("type")

    if kind == "move":
        to = zone_arg(action, "to", set(ZONES) | set(STAGE_SLOTS))
        card, src = take(side, action.get("uid", ""))
        occupant = put(side, card, to, action.get("where", "top"))
        if occupant:
            if src in STAGE_SLOTS:  # moving between stage slots swaps the two cards
                side["stage"][src] = occupant
            else:  # playing onto an occupied slot sends the old card to the waiting room
                put(side, occupant, "waiting")
                add_log(state, player, f"sent {name(occupant['card'])} to the waiting room")
        add_log(state, player, describe_move(card, src, to, name))
        return {}

    if kind == "move_top":
        src = zone_arg(action, "from", HIDDEN_ZONES)
        to = zone_arg(action, "to", set(ZONES) | set(STAGE_SLOTS))
        count = count_arg(action)
        if to in STAGE_SLOTS:
            count = 1
        if len(zones[src]) < count:
            raise GameError(f"Your {LABELS[src]} only has {len(zones[src])} cards.")
        moved = []
        for _ in range(count):
            card = zones[src].pop()
            occupant = put(side, card, to)
            if occupant:
                put(side, occupant, "waiting")
            moved.append(card)
        if src == "deck" and to == "hand":
            add_log(state, player, f"drew {count} card{'s' if count != 1 else ''}")
        elif is_public(to, moved[0]):
            names = ", ".join(name(c["card"]) for c in moved)
            add_log(state, player, f"put the top {count} of their {LABELS[src]} into {LABELS[to]}: {names}")
        else:
            add_log(state, player, f"moved the top {count} of their {LABELS[src]} to {LABELS[to]}")
        return {}

    if kind == "move_all":
        src = zone_arg(action, "from", set(ZONES) - HIDDEN_ZONES - PRIVATE_ZONES)
        to = zone_arg(action, "to", set(ZONES))
        cards, zones[src] = zones[src], []
        for card in cards:
            put(side, card, to)
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
        card = side["stage"][where] if where in STAGE_SLOTS else zones[where][index]
        card["face_down"] = not card["face_down"]
        add_log(state, player, f"turned a card in their {LABELS[where]} face {'down' if card['face_down'] else 'up'}")
        return {}

    if kind == "stand_all":
        for card in side["stage"].values():
            if card:
                card["pos"] = "stand"
        add_log(state, player, "stood all their characters")
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

    if kind == "end_turn":
        if state["turn"] != player:
            raise GameError("It isn't your turn.")
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
        add_log(state, player, f"ended their turn. Turn {state['turn_number']}: {state['players'][other]['name']}")
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
    return {"name": side["name"], "zones": zones, "stage": stage}


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
    return pks


def view(state, player):
    """The board from one player's seat: their own side in full, the opponent's with hidden zones as counts."""
    player = str(player)
    other = next((p for p in state["order"] if p != player), None)
    return {
        "me": side_view(state["players"][player], True),
        "opponent": side_view(state["players"][other], False) if other else None,
        "my_turn": state["turn"] == player,
        "turn_number": state["turn_number"],
        "log": state["log"][-50:],
    }
