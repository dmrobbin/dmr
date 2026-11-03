"""CPU opponents: given the game from a CPU's seat, what it does next.

next_action looks at the state and returns one action, of the same kind a player's page sends, or
None when it's waiting on the other player. play.py feeds these to game.apply one at a time as the
player's page polls, so the turn plays out at a speed that can be followed. The CPU plays by the
same rules and only uses what a player in its seat could see: its own hand, public zones and the
stats on the board. It never reads the other hand, or either deck, except what an ability shows it.

The "standard" model:
- Fills the front line for the most power it can get, facing enemies it can beat where it can.
- Attacks to reverse enemy characters first, and avoids battles it would lose: with nothing left to
  reverse, it still makes a side attack, even for no damage, since its trigger check brings stock.
- Clocks a card every turn to draw, and uses abilities that bring cards to its hand. Stock comes third,
  after reversing enemies and cards in hand.
- Plays cards with a cx combo ahead of others when their climax is available, and that climax next.
- Plays a backup when that makes the defender at least as strong as the attacker.
- Encores only level 2 and up, and not if that leaves too little stock for an equal or better card in hand.

Aggression weighs these against each other: at 1 (standard) as above. Each point more values
reversing enemies more and its own characters less (see Temper).

The other models play as standard does, apart from:
- "focused" (Focused) works towards its cx combos. It knows what's in its own deck, as a player knows their
  deck list, though not the order. It picks the highest level combo it can reach by next level, then holds
  that card and its climax, saves the stock to pay for it, and levels up with the color it needs.
- "strategic" (Strategic) gets as many cards to work with as it can before building its board: it sets out and
  uses abilities and events that bring cards to the hand, and if one of them can take cards from the waiting
  room, it first uses what puts cards in there, such as brainstorm.
- "hard" (Hard) plays as strategic does, and gets more aggressive the closer its opponent is to defeat: from
  its own aggression with the opponent at level 0 and an empty clock, up to the most there is at level 3, 6 clock.
- "easy" (Easy) plays as standard does, carelessly, though always by the rules: it encores whatever it can pay
  for, however little the card's worth; mostly turns down "you may" abilities and back row abilities, and backups;
  keeps its opening hand; mostly puts any character it can play in any empty place, rather than building its
  front line; clocks, levels up with and takes trigger rewards of any card, not the right one; plays any climax,
  not its combos'; and attacks left to right, often into characters stronger than its own. Against standard,
  with the same decks, it wins about one game in five.
"""
import copy
import random
import re
from functools import cached_property
from types import SimpleNamespace

from . import abilities, game

MODELS = {"easy": "Easy", "standard": "Standard", "focused": "Focused", "strategic": "Strategic", "hard": "Hard mode"}
EASY_SLIP = .75  # how often an easy CPU passes up a chance: an optional ability, a backup, a losing attack held back
MIN_AGGRESSION = 1
MAX_AGGRESSION = 5
ENCORE_MIN_LEVEL = 2
COMBO_BONUS = 100000  # front line power a card with a live cx combo is worth: more than any card, so it's always played
PLAN_VALUE = 5  # what being part of a focused CPU's combo adds to a card's value in hand: more than any other card has
MIN_FRONT_LINE = 2  # a focused CPU saving stock still pays for characters up to this many at the front
FILL_MIN_DECK = 8  # a strategic CPU won't mill a deck this small, since refreshing costs damage
HAND_EFFECT = re.compile(r"\bdraw\b|into your hand|to your hand", re.I)
CHOICE_DESTINATIONS = ["hand", "stock", "deck", "deck_bottom", "waiting"]  # best first, for "where does it go?"
WAITS = {"ability_show": 2, "pending_climax": 2, "pending_damage": 2, "auto_next": .9}  # seconds to let these show; otherwise STEP_WAIT
STEP_WAIT = .8


class Temper:
    """What aggression changes: how much a battle it would win or lose is worth on the front line,
    and how far behind it will still make a front attack."""

    def __init__(self, aggression=MIN_AGGRESSION):
        self.aggression = max(MIN_AGGRESSION, aggression)
        self.win_bonus = 2000 * self.aggression
        self.lose_penalty = 2000 / self.aggression
        self.risk = (self.aggression - 1) * 1000


def wait_seconds(state):
    """How long the last thing that happened should stay on screen before the CPU moves."""
    return max([seconds for key, seconds in WAITS.items() if state.get(key)], default=STEP_WAIT)


def next_action(state, me, info, aggression=MIN_AGGRESSION, rng=random, model="standard"):
    """The CPU's next action in this game, or None if there's nothing for it to do yet."""
    if model == "hard":
        aggression = hard_aggression(state, str(me), aggression)
    return with_free_play(MINDS.get(model, Mind)(state, str(me), info, Temper(aggression), rng).act(), state, str(me), info)


def hard_aggression(state, me, aggression):
    """Hard mode's aggression right now: its own, rising to the most there is as the opponent nears defeat,
    measured by the damage they've taken towards level 4 (7 clock cards a level)."""
    them = state["players"][game.other_player(state, me)]["zones"]
    taken = len(them["level"]) * game.LEVEL_UP_AT + len(them["clock"])
    nearness = min(1, taken / (game.LOSING_LEVEL * game.LEVEL_UP_AT - 1))
    return aggression + (MAX_AGGRESSION - aggression) * nearness


def with_free_play(action, state, me, info):
    """A hand card it can't pay for, but may play by giving up a character: gives up the weakest."""
    if not action or action.get("type") != "move":
        return action
    card = next((c for c in state["players"][me]["zones"]["hand"] if c["uid"] == action.get("uid")), None)
    if card and game.play_cost(state, me, card, info) > len(state["players"][me]["zones"]["stock"]):
        options = game.free_play_options(state, me, card, info)
        if options:
            stats = state.get("stats", {})
            return {**action, "free_with": min(options, key=lambda c: stats.get(c["uid"], {}).get("power", 0))["uid"]}
    return action


def fallback_action(state, me):
    """Something safe to do when next_action's choice was refused, so a game can't stick on the CPU."""
    me = str(me)
    res = state.get("resolving")
    if res and res["player"] == me:
        return {"type": "ability_stop"}
    if game.queue_chooser(state) == me and state.get("ability_queue"):
        entry = next(e for e in state["ability_queue"] if e["player"] == me)
        return {"type": "ability_trigger", "id": entry["id"], "accept": False}
    attack = state.get("attack") or {}
    if attack.get("step") == "counter" and state["turn"] != me:
        return {"type": "no_counter"}
    if state["turn"] != me:
        return None
    if attack.get("step") == "trigger" and attack.get("prompt"):
        return {"type": "trigger_choice"}
    following = game.PHASES[game.PHASES.index(state.get("phase", "main")) + 1:]
    return {"type": "phase", "phase": following[0]} if following else None


class Mind:
    def __init__(self, state, me, info, temper, rng):
        self.state = state
        self.me = me
        self.info = info
        self.temper = temper
        self.rng = rng
        self.env = SimpleNamespace(info=info)
        self.side = state["players"][me]
        self.zones = self.side["zones"]
        self.them = game.other_player(state, me)
        self.their_side = state["players"][self.them]

    # What cards are like ----------------------------------------------------------------------------

    def details(self, card):
        return self.info(card["card"]) or {}

    def kind(self, card):
        return (self.details(card).get("card_type") or "").lower()

    def stat(self, card, stat):
        return self.state.get("stats", {}).get(card["uid"], {}).get(stat, game.number(self.details(card).get(stat)))

    def my_level(self):
        return len(self.zones["level"])

    def play_level(self, card):
        return game.play_level(self.state, self.me, card, self.info)

    def play_cost(self, card):
        if game.free_play_options(self.state, self.me, card, self.info):
            return 0  # it can always give up the character instead (see with_free_play)
        return game.play_cost(self.state, self.me, card, self.info)

    def can_play(self, card):
        return (self.play_level(card) <= self.my_level()
                and not game.play_banned(self.state, self.me, card, self.info)
                and self.play_cost(card) <= len(self.zones["stock"])
                and not game.color_needed(self.state, self.me, card, self.info))

    def value(self, card):
        """How much it's worth keeping a card in hand, for what to clock or discard."""
        details = self.details(card)
        if self.kind(card) == "climax":
            return 1.5
        level = self.play_level(card)  # one it could play soon is worth keeping, however it gets there
        value = 1 + game.number(details.get("power")) / 20000
        if level <= self.my_level() + 1:
            value += 2
        if game.color_needed(self.state, self.me, card, self.info):
            value -= 1
        return value

    def lowest_value(self, cards, count):
        return sorted(cards, key=self.value)[:count]

    def combo_climaxes(self, card):
        """The lines of this card's text with a cx combo."""
        return abilities.combo_lines(self.details(card).get("text"))

    def combo_live(self, card):
        """Whether this card has a cx combo whose climax is in the climax zone or the hand."""
        lines = self.combo_climaxes(card)
        if not lines:
            return False
        climaxes = [c for c in self.zones["hand"] + self.zones["climax"] if self.kind(c) == "climax"]
        return any(self.names_climax(line, c) for line in lines for c in climaxes)

    def names_climax(self, line, climax):
        return f'"{abilities.plain_name(self.details(climax).get("name"))}"' in line

    # The order things happen in -------------------------------------------------------------------------

    def act(self):
        state = self.state
        over = state.get("game_over")
        if over:
            # The CPU always takes a rematch; ending the match is up to the player.
            wanted = self.them in over["rematch"] and self.me not in over["rematch"]
            return {"type": "rematch"} if wanted else None
        rps = state.get("rps")
        if rps:
            if not rps["winner"] and self.me not in rps["picks"]:
                return {"type": "rps", "choice": self.rng.choice(list(game.RPS_BEATS))}
            return None
        if state.get("rules_request") and state["rules_request"]["player"] != self.me:
            return {"type": "rules_answer", "accept": False}  # the CPU only knows how to play by the rules
        if state.get("reveal") and state["reveal"]["player"] != self.me:
            return {"type": "close_reveal"}
        if state.get("phase") == "mulligan":
            return self.mulligan()
        if state.get("pending_damage", {}).get("player") == self.me:
            return {"type": "resolve_damage"}
        if state.get("pending_refresh", {}).get("player") == self.me:
            return {"type": "continue_damage"}
        if game.damage_in_progress(state, self.them):
            return None
        if game.must_level_up(state, self.me):
            return self.level_up()
        if game.must_level_up(state, self.them):
            return None
        if state.get("ability_show"):
            shown = state["ability_show"]
            return {"type": "ability_show_done", "id": shown["id"]} if shown["player"] == self.me else None
        res = state.get("resolving")
        if res:
            prompt = res.get("prompt")
            return self.answer(res) if prompt and prompt.get("player", res["player"]) == self.me else None
        if state.get("ability_queue"):
            return self.trigger_ability() if game.queue_chooser(state) == self.me else None
        if (state.get("pending_discard") or {}).get("player") == self.me:
            return self.discard()
        attack = state.get("attack") or {}
        if attack.get("step") == "counter" and state["turn"] != self.me:
            return self.counter(attack)
        if state.get("phase") == "encore":
            encore = self.encore()
            if encore:
                return encore
        return self.my_turn(attack) if state["turn"] == self.me else None

    def my_turn(self, attack):
        state = self.state
        if state.get("auto_next"):
            return {"type": "phase", "phase": state["auto_next"], "auto": True}
        if state.get("pending_climax") == self.me:
            return {"type": "phase", "phase": "attack"}
        phase = state.get("phase")
        if phase == "clock":
            return self.clock()
        if phase == "main":
            return self.main() or {"type": "phase", "phase": "climax"}
        if phase == "climax":
            return self.play_climax() or {"type": "phase", "phase": "attack"}
        if phase == "attack":
            if attack.get("step") == "trigger" and attack.get("prompt"):
                return self.trigger_choice(attack["prompt"])
            if attack.get("step", "declare") == "declare":
                return self.declare() or {"type": "phase", "phase": "encore"}
        return None

    # Before the game ------------------------------------------------------------------------------------

    def mulligan(self):
        if self.me in self.state.get("mulligan_done", []):
            return None
        hand = self.zones["hand"]
        climaxes = [c for c in hand if self.kind(c) == "climax"]
        swap = sorted(climaxes, key=self.value, reverse=True)[1:] + [c for c in hand if self.kind(c) != "climax" and game.number(self.details(c).get("level")) >= 2]
        return {"type": "mulligan", "uids": [c["uid"] for c in swap]}

    # Choices the rules force ---------------------------------------------------------------------------

    def level_up(self):
        first = self.zones["clock"][:game.LEVEL_UP_AT]
        # Whatever colors the hand is held back for, and otherwise the most useful card.
        wanted = self.colors_wanted()
        non_climax = self.level_up_choices([c for c in first if self.kind(c) != "climax"] or first)
        best = max(non_climax, key=lambda c: (self.details(c).get("color") in wanted, game.number(self.details(c).get("level"))))
        return {"type": "level_up", "uid": best["uid"]}

    def colors_wanted(self):
        return {self.details(c).get("color") for c in self.zones["hand"] if game.color_needed(self.state, self.me, c, self.info)}

    def level_up_choices(self, cards):
        return cards

    def discard(self):
        count = self.state["pending_discard"]["count"]
        return {"type": "discard", "uids": [c["uid"] for c in self.lowest_value(self.zones["hand"], count)]}

    def encore(self):
        """One reversed character of ours: the encore rule's choice for it."""
        for card in game.stage_cards(self.side):
            if card["pos"] == "reverse":
                return {"type": "encore" if self.worth_encore(card) else "move", "uid": card["uid"],
                        **({} if self.worth_encore(card) else {"to": "waiting"})}
        return None

    def worth_encore(self, card):
        stock = len(self.zones["stock"])
        if stock < game.ENCORE_COST or game.number(self.details(card).get("level")) < ENCORE_MIN_LEVEL:
            return False
        if game.has_status(self.state, card["uid"], "no_encore"):
            return False
        power = game.number(self.details(card).get("power"))
        left = stock - game.ENCORE_COST
        for other in self.zones["hand"]:
            details = self.details(other)
            if self.kind(other) == "character" and game.number(details.get("power")) >= power and self.can_play(other) \
                    and self.play_cost(other) > left:
                return False  # paying would cost it a card at least this strong
        return True

    def counter(self, attack):
        """A backup, if that's what it takes for the defender to at least match the attacker."""
        no = {"type": "no_counter"}
        if attack.get("kind") != "front":
            return no
        attacker = self.their_side["stage"].get(attack["slot"])
        defender = self.side["stage"].get(attack["target"])
        if not attacker or not defender:
            return no
        need = self.stat(attacker, "power") - self.stat(defender, "power") - attack.get("backup", 0)
        if need <= 0:
            return no
        options = []
        for card in self.zones["hand"]:
            if card["uid"] in attack.get("counters", []):
                play = game.counter_play(self.state, self.me, card, self.info)
                if play and play[1] >= need:
                    options.append((play[0], play[1], card))
        if not options:
            return no
        cheapest = min(options, key=lambda o: o[:2])
        return {"type": "counter", "uid": cheapest[2]["uid"]}

    # The turn -------------------------------------------------------------------------------------------

    def clock(self):
        """Clock and draw every turn, unless that's what would lose the game."""
        hand = self.zones["hand"]
        fatal = self.my_level() >= game.LOSING_LEVEL - 1 and len(self.zones["clock"]) + 1 >= game.LEVEL_UP_AT
        if hand and not fatal:
            return {"type": "clock_draw", "uid": self.lowest_value(hand, 1)[0]["uid"]}
        return {"type": "phase", "phase": "main"}

    def front_score(self, players=None):
        """What the front line is worth: its power, more for facing what it can beat, less for what beats it."""
        state = {**self.state, "players": players} if players else self.state
        stats, _ = game.compute_stats(state, self.env)
        side = state["players"][self.me]
        them = state["players"][self.them]
        score = 0
        for slot, facing in game.OPPOSITE.items():
            card = side["stage"][slot]
            if not card:
                continue
            power = stats[card["uid"]]["power"]
            score += power
            enemy = them["stage"][facing]
            if enemy:
                theirs = stats[enemy["uid"]]["power"]
                score += self.temper.win_bonus if power > theirs else -self.temper.lose_penalty if power < theirs else 0
        return score

    def try_play(self, card, slot):
        players = copy.deepcopy(self.state["players"])
        side = players[self.me]
        side["zones"]["hand"] = [c for c in side["zones"]["hand"] if c["uid"] != card["uid"]]
        side["stage"][slot] = dict(card)
        return self.front_score(players)

    def try_move(self, card, src, slot):
        players = copy.deepcopy(self.state["players"])
        side = players[self.me]
        side["stage"][src], side["stage"][slot] = side["stage"][slot], side["stage"][src]
        game.swap_markers(side, src, slot)  # as the real move does
        return self.front_score(players)

    def main(self):
        """The most useful thing left to do this main phase, or None when there's nothing."""
        current = self.front_score()
        best, best_gain = None, 0
        stage = self.side["stage"]
        for card in self.zones["hand"]:
            if self.kind(card) != "character" or not self.can_play(card):
                continue
            bonus = COMBO_BONUS if self.combo_live(card) else 0
            for slot in game.STAGE_SLOTS:
                if stage[slot] is not None and slot not in game.OPPOSITE:
                    continue
                gain = self.try_play(card, slot) - current + (bonus if slot in game.OPPOSITE else 0)
                if gain > best_gain:
                    best, best_gain = {"type": "move", "uid": card["uid"], "to": slot}, gain
        moved = self.state.get("cpu_moved", {})
        already = set(moved.get("uids", [])) if moved.get("turn") == self.state["turn_number"] else set()
        for src in game.STAGE_SLOTS:
            card = stage[src]
            for slot in game.OPPOSITE if card and card["uid"] not in already else ():
                if slot == src or (stage[slot] and stage[slot]["uid"] in already):
                    continue
                gain = self.try_move(card, src, slot) - current + self.move_bonus(card, src, slot)
                if gain > best_gain:
                    best, best_gain = {"type": "move", "uid": card["uid"], "to": slot}, gain
        if best and any(c and c["uid"] == best["uid"] for c in stage.values()):
            # A character is only rearranged once a turn, so this can never go round in circles.
            self.state["cpu_moved"] = {"turn": self.state["turn_number"], "uids": [*already, best["uid"]]}
        return best or self.useful_event() or self.back_row() or self.hand_ability()

    def move_bonus(self, card, src, slot):
        return 0

    def back_row(self):
        """An open back slot takes a card that pays nothing, to have more characters out."""
        open_slots = [s for s in ("B1", "B2") if not self.side["stage"][s]]
        if not open_slots:
            return None
        free = [c for c in self.zones["hand"] if self.kind(c) == "character" and self.can_play(c)
                and self.play_cost(c) == 0 and len(self.zones["hand"]) > 4]
        return {"type": "move", "uid": max(free, key=self.value)["uid"], "to": open_slots[0]} if free else None

    def by_hand_only(self, ability):
        return ability.get("manual_cost") or (ability.get("steps") and ability["steps"][0]["do"] == "manual")

    def useful_event(self):
        """An event that brings cards to the hand."""
        for card in self.zones["hand"]:
            if self.kind(card) == "event" and self.can_play(card):
                for ability in abilities.parse(self.details(card).get("text")):
                    if ability["kind"] == "event" and HAND_EFFECT.search(ability["text"]) and not self.by_hand_only(ability):
                        return {"type": "move", "uid": card["uid"], "to": "resolution"}
        return None

    def usable_acts(self):
        """(action, ability) for the back row's abilities it can use, without spending the hand on them.
        Only ones that rest the character or are once a turn, so this can't go round forever."""
        acts = self.state.get("acts", {}).get(self.me, {})
        for slot in ("B1", "B2"):
            card = self.side["stage"][slot]
            for row in acts.get(card["uid"], []) if card else ():
                if row["why"]:
                    continue
                ability = game.abilities_of(self.state, card, self.env)[row["index"]]
                parts = {part["part"] for part in ability.get("cost", [])}
                if (not self.by_hand_only(ability) and ability["kind"] == "act" and self.can_spend(stock_cost(ability))
                        and "pick" not in parts and ("self_rest" in parts or ability.get("once"))):
                    yield {"type": "activate", "uid": card["uid"], "index": row["index"]}, ability

    def can_spend(self, stock):
        return True

    def hand_ability(self):
        """A back row character's ability that brings cards to the hand."""
        return next((action for action, ability in self.usable_acts() if HAND_EFFECT.search(ability["text"])), None)

    def play_climax(self):
        """A climax, the one a character's cx combo wants if there is one."""
        if self.zones["climax"]:
            return None
        climaxes = [c for c in self.zones["hand"] if self.kind(c) == "climax" and self.can_play(c)]
        if not climaxes:
            return None
        lines = [line for card in game.stage_cards(self.side) for line in self.combo_climaxes(card)]
        wanted = [c for c in climaxes if any(self.names_climax(line, c) for line in lines)]
        spare = wanted or self.spare_climaxes(climaxes)
        return {"type": "move", "uid": spare[0]["uid"], "to": "climax"} if spare else None

    def spare_climaxes(self, climaxes):
        """The climaxes it's happy to play without a combo."""
        return climaxes

    def declare(self):
        """Reverse what it can, biggest first; then direct attacks; then side attacks instead of losing
        battles, even for no damage, because every attack's trigger check adds to its stock."""
        if not game.can_attack(self.state, self.me):
            return None
        wins, directs, sides = [], [], []
        for slot, facing in game.OPPOSITE.items():
            card = self.side["stage"][slot]
            if not card or card["pos"] != "stand":
                continue
            bans = game.attack_bans(self.state, self.me, card, self.env)
            if "all" in bans:
                continue
            enemy = self.their_side["stage"][facing]
            if not enemy:
                directs.append({"type": "attack", "uid": card["uid"], "kind": "direct"})
                continue
            power, theirs = self.stat(card, "power"), self.stat(enemy, "power")
            if "front" not in bans and (power + self.temper.risk >= theirs or "side" in bans):
                wins.append((theirs, {"type": "attack", "uid": card["uid"], "kind": "front"}))
            elif "side" not in bans:
                sides.append({"type": "attack", "uid": card["uid"], "kind": "side"})
        ordered = [a for _, a in sorted(wins, key=lambda w: -w[0])] + directs + sides
        return ordered[0] if ordered else None

    def trigger_choice(self, prompt):
        if prompt["kind"] == "treasure":
            return {"type": "trigger_choice", "accept": True}
        options = [c for c in self.zones["waiting"] if c["uid"] in prompt["options"]]
        if not options:
            return {"type": "trigger_choice"}
        best = max(options, key=self.value)
        if prompt["kind"] == "standby":
            return {"type": "trigger_choice", "uid": best["uid"], "to": self.best_slot()}
        return {"type": "trigger_choice", "uid": best["uid"], "to": "hand"}

    def best_slot(self):
        stage = self.side["stage"]
        for slot in game.STAGE_SLOTS:
            if not stage[slot]:
                return slot
        return min(game.STAGE_SLOTS, key=lambda s: self.stat(stage[s], "power"))

    # Abilities ----------------------------------------------------------------------------------------

    def trigger_ability(self):
        """Take every ability it can actually carry out. One that needs doing by hand can't be."""
        entry = next(e for e in self.state["ability_queue"] if e["player"] == self.me)
        return {"type": "ability_trigger", "id": entry["id"], "accept": not self.by_hand_only(entry["ability"])}

    def answer(self, res):
        prompt = res["prompt"]
        if prompt["kind"] == "manual":
            return {"type": "ability_answer", "passed": True}  # the CPU can't do this part; the log says so
        if prompt["kind"] == "cards":
            return {"type": "ability_answer", "uids": self.pick_cards(prompt)}
        options = [option["value"] for option in prompt["options"]]
        purpose = prompt["for"]
        if purpose == "may" and (not self.can_spend(stock_cost(prompt["step"])) or prompt["step"].get("again")):
            return {"type": "ability_answer", "value": "no"}  # an action it may repeat, it does once
        if purpose == "dest":
            return {"type": "ability_answer", "value": min(options, key=CHOICE_DESTINATIONS.index)}
        if purpose == "place":
            empty = [s for s in options if not self.side["stage"][s]]
            center = [s for s in empty if s in game.OPPOSITE]
            return {"type": "ability_answer", "value": (center or empty or options)[0]}
        if purpose == "options":
            steps = prompt["step"]["options"]
            usable = [i for i in options if not steps[i]["steps"] or steps[i]["steps"][0]["do"] != "manual"]
            return {"type": "ability_answer", "value": (usable or options)[0]}
        return {"type": "ability_answer", "value": options[0]}  # "yes", and the most on offer

    def pick_cards(self, prompt):
        cards = [c for c in prompt["cards"] if c["uid"] in prompt["options"]]
        count = prompt["max"] if not prompt.get("cost") else prompt["min"]
        if prompt.get("cost") or prompt.get("for") == "order":
            ranked = sorted(cards, key=self.value)  # pay with what it needs least
        elif prompt.get("owner") == self.them:
            ranked = sorted(cards, key=lambda c: -self.stat(c, "power"))  # after their best
        elif prompt.get("zone") in ("stage", "center", "back"):
            ranked = sorted(cards, key=lambda c: (c["uid"] not in self.front_uids(), -self.stat(c, "power")))  # helping its front line
        else:
            ranked = sorted(cards, key=self.value, reverse=True)
        if prompt.get("max_power") is not None:  # as many as fit in the power allowed, the biggest first
            ranked = sorted(cards, key=lambda c: -prompt["powers"].get(c["uid"], 0))
            picked, power = [], 0
            for card in ranked:
                if len(picked) < count and power + prompt["powers"].get(card["uid"], 0) <= prompt["max_power"]:
                    picked.append(card["uid"])
                    power += prompt["powers"].get(card["uid"], 0)
            return picked
        return [c["uid"] for c in ranked[:count]]

    def front_uids(self):
        return {self.side["stage"][s]["uid"] for s in game.OPPOSITE if self.side["stage"][s]}


def stock_cost(ability):
    return sum(part.get("n", 0) for part in ability.get("cost", []) if part["part"] == "stock")


def all_steps(steps):
    for step in steps:
        yield step
        yield from all_steps(step.get("then", []))
        for option in step.get("options", []):
            if isinstance(option, dict):
                yield from all_steps(option["steps"])


def fills_waiting(ability):
    """Whether this puts cards from the top of its own deck into the waiting room, as brainstorm does."""
    steps = list(all_steps(ability.get("steps", [])))
    return (any(s["do"] == "top" and s.get("to") == "waiting" and s.get("owner") == "me" for s in steps)
            or (any(s["do"] == "flip" for s in steps) and any(s["do"] == "move_it" and s.get("to") == "waiting" for s in steps)))


def takes_from_waiting(ability):
    """Whether this lets it choose cards in its own waiting room."""
    return any(s["do"] == "choose" and s.get("zone") == "waiting" and s.get("owner", "me") == "me" for s in all_steps(ability.get("steps", [])))


class Focused(Mind):
    @cached_property
    def plan(self):
        """The combo it's working towards: the highest level one it could play by its next level, one it
        already holds or has out if that's a choice, and only if its climax can still turn up."""
        zones = self.zones
        out = game.stage_cards(self.side)
        climaxes = [c for c in zones["hand"] + zones["deck"] + zones["waiting"] + zones["climax"] if self.kind(c) == "climax"]
        best, best_rank = None, None
        for card in zones["hand"] + out + zones["deck"] + zones["waiting"]:
            level = game.number(self.details(card).get("level"))
            if self.kind(card) != "character" or level > self.my_level() + 1:
                continue
            lines = self.combo_climaxes(card)
            needed = {c["card"] for c in climaxes if any(self.names_climax(line, c) for line in lines)}
            ready = any(c["uid"] == card["uid"] for c in zones["hand"] + out)
            if needed and (best is None or (level, ready) > best_rank):
                best, best_rank = SimpleNamespace(card=card["card"], climaxes=needed, details=self.details(card)), (level, ready)
        return best

    def in_plan(self, card):
        return bool(self.plan) and (card["card"] == self.plan.card or card["card"] in self.plan.climaxes)

    def reserve(self):
        """The stock being saved for the combo. None's needed once it's out."""
        if not self.plan or any(c["card"] == self.plan.card for c in game.stage_cards(self.side)):
            return 0
        return game.number(self.plan.details.get("cost"))

    def can_spend(self, stock):
        return not stock or len(self.zones["stock"]) - stock >= self.reserve()

    def value(self, card):
        return super().value(card) + (PLAN_VALUE if self.in_plan(card) else 0)

    def can_play(self, card):
        if not super().can_play(card):
            return False
        return (self.in_plan(card) or self.combo_live(card) or self.can_spend(self.play_cost(card))
                or len(self.front_uids()) < MIN_FRONT_LINE)

    def worth_encore(self, card):
        return self.can_spend(game.ENCORE_COST) and super().worth_encore(card)

    def move_bonus(self, card, src, slot):
        """A combo character waiting in the back row goes to where it can attack."""
        return COMBO_BONUS if src not in game.OPPOSITE and slot in game.OPPOSITE and self.combo_live(card) else 0

    def spare_climaxes(self, climaxes):
        return [c for c in climaxes if not self.in_plan(c)]

    def colors_wanted(self):
        return super().colors_wanted() | ({self.plan.details.get("color")} if self.plan else set())

    def level_up_choices(self, cards):
        return [c for c in cards if not self.in_plan(c)] or cards


class Strategic(Mind):
    def main(self):
        return self.prepare() or super().main()

    def open_slot(self, front_too=True):
        slots = [s for s in ("B1", "B2", *game.OPPOSITE) if not self.side["stage"][s]]
        return next((s for s in slots if front_too or s not in game.OPPOSITE), None)

    def from_hand(self):
        """(action, ability) for what it can do from its hand: events, and characters for what they do when played."""
        slot = self.open_slot()
        for card in self.zones["hand"]:
            kind = self.kind(card)
            if kind not in ("event", "character") or not self.can_play(card) or (kind == "character" and not slot):
                continue
            for ability in abilities.parse(self.details(card).get("text")):
                if self.by_hand_only(ability):
                    continue
                if kind == "event" and ability["kind"] == "event":
                    yield {"type": "move", "uid": card["uid"], "to": "resolution"}, ability
                elif kind == "character" and ability["kind"] == "auto" and any(w["on"] == "play" for w in ability.get("when") or []):
                    yield {"type": "move", "uid": card["uid"], "to": slot}, ability

    def set_out(self):
        """A character from the hand for the back row, for an ability it could then use right away."""
        slot = self.open_slot(front_too=False)
        for card in self.zones["hand"] if slot else ():
            if self.kind(card) != "character" or not self.can_play(card):
                continue
            left = len(self.zones["stock"]) - self.play_cost(card)
            for ability in abilities.parse(self.details(card).get("text")):
                parts = {part["part"] for part in ability.get("cost", [])}
                if (ability["kind"] == "act" and not self.by_hand_only(ability) and stock_cost(ability) <= left
                        and "pick" not in parts and ("self_rest" in parts or ability.get("once")) and self.brings_cards(ability)):
                    return {"type": "move", "uid": card["uid"], "to": slot}
        return None

    def brings_cards(self, ability):
        return fills_waiting(ability) or takes_from_waiting(ability) or HAND_EFFECT.search(ability["text"])

    def prepare(self):
        """Whatever brings it the most cards to work with, in the order that brings the most."""
        placed = self.set_out()
        if placed:
            return placed
        options = [*self.usable_acts(), *self.from_hand()]
        deck_ok = len(self.zones["deck"]) >= FILL_MIN_DECK
        if deck_ok and any(takes_from_waiting(ability) for _, ability in options):
            for action, ability in options:
                if fills_waiting(ability):
                    return action
        for action, ability in options:
            if HAND_EFFECT.search(ability["text"]) and not takes_from_waiting(ability) and (deck_ok or not fills_waiting(ability)):
                return action
        if self.zones["waiting"]:
            for action, ability in options:
                if takes_from_waiting(ability) and (deck_ok or not fills_waiting(ability)):
                    return action
        return None


class Hard(Strategic):
    """Strategic, with its aggression set by how close the opponent is to defeat (see hard_aggression)."""


class Easy(Mind):
    """Standard, played carelessly: every move is one the rules allow, just not a good one (see the module's notes)."""

    def slip(self):
        """Whether it passes up a chance this time."""
        return self.rng.random() < EASY_SLIP

    def mulligan(self):
        if self.me in self.state.get("mulligan_done", []):
            return None
        return {"type": "mulligan", "uids": []}  # keeps whatever it's dealt

    def level_up(self):
        first = self.zones["clock"][:game.LEVEL_UP_AT]
        return {"type": "level_up", "uid": self.rng.choice(first)["uid"]}

    def worth_encore(self, card):
        """Whatever it can pay for, however little the card's worth and whatever the stock was for."""
        return len(self.zones["stock"]) >= game.ENCORE_COST and not game.has_status(self.state, card["uid"], "no_encore")

    def counter(self, attack):
        return {"type": "no_counter"} if self.slip() else super().counter(attack)

    def clock(self):
        action = super().clock()
        if action["type"] == "clock_draw":
            action["uid"] = self.rng.choice(self.zones["hand"])["uid"]  # not its least useful card: any of them
        return action

    def combo_live(self, card):
        return False  # it doesn't plan around its climax combos

    def main(self):
        """Mostly, a character that's to go on the stage goes to any empty place, not the one that does the most."""
        action = super().main()
        stage = self.side["stage"]
        playing = action and action.get("type") == "move" and action.get("to") in game.STAGE_SLOTS \
            and any(c["uid"] == action["uid"] for c in self.zones["hand"])
        if playing and self.slip():
            empty = [slot for slot in game.STAGE_SLOTS if not stage[slot]]
            playable = [c for c in self.zones["hand"] if self.kind(c) == "character" and self.can_play(c)]
            if empty and playable:
                return {"type": "move", "uid": self.rng.choice(playable)["uid"], "to": self.rng.choice(empty)}
        return action

    def play_climax(self):
        if self.zones["climax"]:
            return None
        climaxes = [c for c in self.zones["hand"] if self.kind(c) == "climax" and self.can_play(c)]
        return {"type": "move", "uid": self.rng.choice(climaxes)["uid"], "to": "climax"} if climaxes else None

    def declare(self):
        """Left to right, not biggest first, and often into characters stronger than its own."""
        if not game.can_attack(self.state, self.me):
            return None
        for slot, facing in game.OPPOSITE.items():
            card = self.side["stage"][slot]
            if not card or card["pos"] != "stand":
                continue
            bans = game.attack_bans(self.state, self.me, card, self.env)
            if "all" in bans:
                continue
            enemy = self.their_side["stage"][facing]
            if not enemy:
                return {"type": "attack", "uid": card["uid"], "kind": "direct"}
            beats = self.stat(card, "power") >= self.stat(enemy, "power")
            if "front" not in bans and (beats or self.slip() or "side" in bans):
                return {"type": "attack", "uid": card["uid"], "kind": "front"}
            if "side" not in bans:
                return {"type": "attack", "uid": card["uid"], "kind": "side"}
        return None

    def trigger_choice(self, prompt):
        action = super().trigger_choice(prompt)
        options = [c for c in self.zones["waiting"] if c["uid"] in prompt.get("options", [])]
        if action.get("uid") and options:
            action["uid"] = self.rng.choice(options)["uid"]
        return action

    def hand_ability(self):
        return None if self.slip() else super().hand_ability()

    def trigger_ability(self):
        """One that starts "you may" is its to turn down, when it triggers, and it mostly does."""
        action = super().trigger_ability()
        entry = next(e for e in self.state["ability_queue"] if e["id"] == action["id"])
        if (entry["ability"].get("steps") or [{}])[0].get("do") == "may" and self.slip():
            action["accept"] = False
        return action

    def answer(self, res):
        """"You may" mostly gets a no: it seldom bothers with what it doesn't have to do."""
        if res["prompt"].get("for") == "may" and self.slip():
            return {"type": "ability_answer", "value": "no"}
        return super().answer(res)


MINDS = {"standard": Mind, "focused": Focused, "strategic": Strategic, "hard": Hard, "easy": Easy}
