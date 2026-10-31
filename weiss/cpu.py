"""CPU opponents: given the game from a CPU's seat, what it does next.

next_action looks at the state and returns one action, of the same kind a player's page sends, or
None when it's waiting on the other player. play.py feeds these to game.apply one at a time as the
player's page polls, so the turn plays out at a speed that can be followed. The CPU plays by the
same rules and only uses what a player in its seat could see: its own hand, public zones and the
stats on the board. It never reads the other hand, or either deck, except what an ability shows it.

The "standard" model:
- Fills the front line for the most power it can get, facing enemies it can beat where it can.
- Attacks to reverse enemy characters first, and avoids battles it would lose (a side attack instead).
- Clocks a card every turn to draw, and uses abilities that bring cards to its hand.
- Plays cards with a cx combo ahead of others when their climax is available, and that climax next.
- Plays a backup when that makes the defender at least as strong as the attacker.
- Encores only level 2 and up, and not if that leaves too little stock for an equal or better card in hand.

Aggression weighs these against each other: at 1 (standard) as above. Each point more values
reversing enemies more and its own characters less (see Temper).
"""
import copy
import random
import re
from types import SimpleNamespace

from . import abilities, game

MODELS = {"standard": "Standard"}
MIN_AGGRESSION = 1
MAX_AGGRESSION = 5
ENCORE_MIN_LEVEL = 2
COMBO_BONUS = 100000  # front line power a card with a live cx combo is worth: more than any card, so it's always played
HAND_EFFECT = re.compile(r"\bdraw\b|into your hand|to your hand", re.I)
CHOICE_DESTINATIONS = ["hand", "stock", "deck", "deck_bottom", "waiting"]  # best first, for "where does it go?"
WAITS = {"ability_show": 2, "pending_climax": 2, "auto_next": .9}  # seconds to let these show; otherwise STEP_WAIT
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


def next_action(state, me, info, aggression=MIN_AGGRESSION, rng=random):
    """The CPU's next action in this game, or None if there's nothing for it to do yet."""
    return Mind(state, str(me), info, Temper(aggression), rng).act()


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

    def can_play(self, card):
        details = self.details(card)
        return (game.number(details.get("level")) <= self.my_level()
                and game.number(details.get("cost")) <= len(self.zones["stock"])
                and not game.color_needed(self.state, self.me, card, self.info))

    def value(self, card):
        """How much it's worth keeping a card in hand, for what to clock or discard."""
        details = self.details(card)
        if self.kind(card) == "climax":
            return 1.5
        level = game.number(details.get("level"))
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
        return [line for line in abilities.plain_name_lines(self.details(card).get("text")) if "【CXCOMBO】" in line]

    def combo_live(self, card):
        """Whether this card has a cx combo whose climax is in the climax zone or the hand."""
        lines = self.combo_climaxes(card)
        if not lines:
            return False
        climaxes = [c for c in self.zones["hand"] + self.zones["climax"] if self.kind(c) == "climax"]
        return any(any(f'"{abilities.plain_name(self.details(c).get("name"))}"' in line for c in climaxes) for line in lines)

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
        swap = climaxes[1:] + [c for c in hand if self.kind(c) != "climax" and game.number(self.details(c).get("level")) >= 2]
        return {"type": "mulligan", "uids": [c["uid"] for c in swap]}

    # Choices the rules force ---------------------------------------------------------------------------

    def level_up(self):
        first = self.zones["clock"][:game.LEVEL_UP_AT]
        # Whatever colors the hand is held back for, and otherwise the most useful card.
        wanted = {self.details(c).get("color") for c in self.zones["hand"] if game.color_needed(self.state, self.me, c, self.info)}
        non_climax = [c for c in first if self.kind(c) != "climax"] or first
        best = max(non_climax, key=lambda c: (self.details(c).get("color") in wanted, game.number(self.details(c).get("level"))))
        return {"type": "level_up", "uid": best["uid"]}

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
                    and game.number(details.get("cost")) > left:
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
        stage = players[self.me]["stage"]
        stage[src], stage[slot] = stage[slot], stage[src]
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
        for src in game.STAGE_SLOTS:
            card = stage[src]
            for slot in game.OPPOSITE if card else ():
                if slot == src:
                    continue
                gain = self.try_move(card, src, slot) - current
                if gain > best_gain:
                    best, best_gain = {"type": "move", "uid": card["uid"], "to": slot}, gain
        return best or self.useful_event() or self.back_row() or self.hand_ability()

    def back_row(self):
        """An open back slot takes a card that pays nothing, to have more characters out."""
        open_slots = [s for s in ("B1", "B2") if not self.side["stage"][s]]
        if not open_slots:
            return None
        free = [c for c in self.zones["hand"] if self.kind(c) == "character" and self.can_play(c)
                and game.number(self.details(c).get("cost")) == 0 and len(self.zones["hand"]) > 4]
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

    def hand_ability(self):
        """A back row character's ability that brings cards to the hand, without spending the hand on it.
        Only ones that rest the character or are once a turn, so this can't go round forever."""
        acts = self.state.get("acts", {}).get(self.me, {})
        for slot in ("B1", "B2"):
            card = self.side["stage"][slot]
            for row in acts.get(card["uid"], []) if card else ():
                if row["why"]:
                    continue
                ability = game.abilities_of(self.state, card, self.env)[row["index"]]
                parts = {part["part"] for part in ability.get("cost", [])}
                if (HAND_EFFECT.search(ability["text"]) and not self.by_hand_only(ability) and ability["kind"] == "act"
                        and "pick" not in parts and ("self_rest" in parts or ability.get("once"))):
                    return {"type": "activate", "uid": card["uid"], "index": row["index"]}
        return None

    def play_climax(self):
        """A climax, the one a character's cx combo wants if there is one."""
        if self.zones["climax"]:
            return None
        climaxes = [c for c in self.zones["hand"] if self.kind(c) == "climax" and self.can_play(c)]
        if not climaxes:
            return None
        lines = [line for card in game.stage_cards(self.side) for line in self.combo_climaxes(card)]
        wanted = [c for c in climaxes if any(f'"{abilities.plain_name(self.details(c).get("name"))}"' in line for line in lines)]
        return {"type": "move", "uid": (wanted or climaxes)[0]["uid"], "to": "climax"}

    def declare(self):
        """Reverse what it can, biggest first; then direct attacks; a losing battle becomes a side attack."""
        if not game.can_attack(self.state, self.me):
            return None
        wins, directs, sides = [], [], []
        for slot, facing in game.OPPOSITE.items():
            card = self.side["stage"][slot]
            if not card or card["pos"] != "stand":
                continue
            enemy = self.their_side["stage"][facing]
            if not enemy:
                directs.append({"type": "attack", "uid": card["uid"], "kind": "direct"})
                continue
            power, theirs = self.stat(card, "power"), self.stat(enemy, "power")
            if power + self.temper.risk >= theirs:
                wins.append((theirs, {"type": "attack", "uid": card["uid"], "kind": "front"}))
            elif self.stat(card, "soul") > game.number(self.details(enemy).get("level")):
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
        return [c["uid"] for c in ranked[:count]]

    def front_uids(self):
        return {self.side["stage"][s]["uid"] for s in game.OPPOSITE if self.side["stage"][s]}
