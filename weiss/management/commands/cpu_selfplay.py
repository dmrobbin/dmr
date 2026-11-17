"""CPU against CPU, many games, for measuring how well the CPU plays (see weiss.cpu).

Plays the decks given (or every playable deck) against each other, both seats taken by CPUs, and reports who won
and how each model used what it had. The numbers to watch:
- lanes left open: front slots still empty when its main phase ended, though it had a back row character it could have
  brought up or a character in hand it could have played. Each is an attack, a trigger check's stock and the damage
  it would have dealt, given up, and a direct attack offered to the opponent.
- attacks a turn: how many it made out of the front slots it has.
- stock at the end: what was still in stock when the game ended. A lot left over is stock that did nothing.

    python manage.py cpu_selfplay --games 40 --models standard,standard
    python manage.py cpu_selfplay --games 200 --baseline HEAD   # seat 1 plays as the committed code, seat 2 as the working copy
"""
import os
import subprocess
import types
import random
from collections import defaultdict
from statistics import mean

from django.core.management.base import BaseCommand, CommandError

from weiss import cpu, game, lists
from weiss.models import CardList
from weiss.play import card_lookups, deck_cards

MAX_ACTIONS = 6000  # a game that takes more than this has stuck: it's counted as a draw, and reported


class Command(BaseCommand):
    help = "Play CPUs against each other and report how they use their resources."

    def add_arguments(self, parser):
        parser.add_argument("--games", type=int, default=20)
        parser.add_argument("--models", default="standard,standard", help="the two seats' models, comma separated")
        parser.add_argument("--aggression", default="1,1", help="the two seats' aggression, comma separated")
        parser.add_argument("--decks", default="", help="deck ids to play with, comma separated (default: every playable deck)")
        parser.add_argument("--seed", type=int, default=1)
        parser.add_argument("--baseline", default="", help="a git revision, or a file: seat 1 plays with weiss/cpu.py as it was "
                                                             "there, or with that file's code")
        parser.add_argument("--show", type=int, default=0, help="print the board for this many of the lanes left open")

    def handle(self, *args, **opts):
        models = opts["models"].split(",")
        aggression = [int(a) for a in opts["aggression"].split(",")]
        if len(models) != 2 or len(aggression) != 2 or any(m not in cpu.MINDS for m in models):
            raise CommandError(f"--models and --aggression take two values each; models are {', '.join(cpu.MINDS)}")
        decks = CardList.objects.filter(pk__in=opts["decks"].split(",")) if opts["decks"] else CardList.objects.all()
        decks = [d for d in decks if len(deck_cards(d)) == 50 and not lists.unplayable(d)]
        if len(decks) < 1:
            raise CommandError("No playable decks.")
        brains = [baseline_cpu(opts["baseline"]) if opts["baseline"] else cpu, cpu]
        rng = random.Random(opts["seed"])
        stats = {seat: defaultdict(list) for seat in "12"}
        for seat in "12":
            stats[seat]["show"] = [opts["show"], self.stdout.write]
        wins, stuck = {"1": 0, "2": 0}, 0
        for n in range(opts["games"]):
            # Games come in twos: the same decks, swapped between the seats, and the first turn the other seat's, so
            # neither model gets the better deck or always goes first.
            pair = [rng.choice(decks), rng.choice(decks)] if n % 2 == 0 else pair[::-1]
            winner = play(pair, models, aggression, random.Random(rng.random()), first="1" if n % 2 == 0 else "2", stats=stats,
                          brains=brains)
            if winner:
                wins[winner] += 1
            else:
                stuck += 1
            self.stdout.write(f"game {n + 1}: {pair[0].name} vs {pair[1].name}: "
                              f"{'stuck' if not winner else f'seat {winner} ({models[int(winner) - 1]}) won'}")
        self.stdout.write("")
        for seat in "12":
            s = stats[seat]
            label = f"seat {seat} {models[int(seat) - 1]} (aggression {aggression[int(seat) - 1]})"
            if opts["baseline"]:
                label += f" [{opts['baseline'] if seat == '1' else 'working copy'}]"
            played = opts["games"] - stuck
            error = 196 * (.25 / played) ** .5 if played else 0
            self.stdout.write(f"{label}: won {wins[seat]}/{played} "
                              f"({100 * wins[seat] / max(1, played):.0f}% +/- {error:.0f}, 95% confidence)")
            self.stdout.write(f"  turns ending main with a lane it could have filled left open: "
                              f"{sum(s['open_lanes'])} of {len(s['open_lanes'])} ({share(s['open_lanes'])})")
            self.stdout.write(f"  turns ending main with a back row place open and a character it could play there: "
                              f"{sum(s['open_back'])} of {len(s['open_back'])} ({share(s['open_back'])})")
            self.stdout.write(f"  climax phases with a playable climax and attackers, but no climax played: "
                              f"{sum(s['climax_held'])} of {len(s['climax_held'])} ({share(s['climax_held'])})")
            self.stdout.write(f"  attacks a turn: {avg(s['attacks'])} (front slots filled at attack: {avg(s['front'])})")
            self.stdout.write(f"  stock at the end of main: {avg(s['stock_main'])}; at the game's end: {avg(s['stock_end'])}, "
                              f"in the games it lost: {avg(s['stock_lost'])}")
            encores = s["encores"]
            for level in (0, 1, 2, 3):
                at = [took for took, lvl, _ in encores if lvl == level]
                if at:
                    self.stdout.write(f"  level {level} reversed with the stock to encore: encored {sum(at)} of {len(at)} ({share(at)})")
            self.stdout.write(f"  game length (turns): {avg(s['turns'])}")
        if stuck:
            self.stdout.write(self.style.WARNING(f"{stuck} game(s) stuck past {MAX_ACTIONS} actions"))


def share(flags):
    return f"{100 * sum(flags) / len(flags):.0f}%" if flags else "-"


def avg(values):
    return f"{mean(values):.2f}" if values else "-"


def baseline_cpu(rev):
    """weiss/cpu.py as it was at this git revision (or the code in this file), as a module of its own."""
    if os.path.isfile(rev):
        with open(rev, encoding="utf-8") as file:
            source = file.read()
    else:
        source = git_source(rev)
    module = types.ModuleType("weiss._cpu_baseline")
    module.__package__ = "weiss"
    exec(compile(source, rev, "exec"), module.__dict__)
    return module


def git_source(rev):
    try:
        source = subprocess.run(["git", "show", f"{rev}:weiss/cpu.py"], capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except subprocess.CalledProcessError as exc:
        raise CommandError(f"Can't read weiss/cpu.py at {rev}: {exc.stderr.strip()}")
    return source


def play(pair, models, aggression, rng, first, stats, brains=(cpu, cpu)):
    """One game between two CPUs; returns the winning seat, or None if it stuck."""
    state = game.new_game([(1, "one", deck_cards(pair[0])), (2, "two", deck_cards(pair[1]))], shuffle=rng.shuffle, first=first)
    lookups = card_lookups(state)
    kwargs = dict(shuffle=rng.shuffle, **lookups)
    attacks = defaultdict(int)
    for _ in range(MAX_ACTIONS):
        over = state.get("game_over")
        if over:
            for seat in "12":
                stock = len(state["players"][seat]["zones"]["stock"])
                stats[seat]["stock_end"].append(stock)
                if over["winner"] != seat:
                    stats[seat]["stock_lost"].append(stock)
                stats[seat]["turns"].append(state["turn_number"])
            return over["winner"]
        moved = False
        for seat in "12":
            brain = brains[int(seat) - 1]
            action = brain.next_action(state, seat, lookups["info"], aggression[int(seat) - 1], rng, model=models[int(seat) - 1])
            if not action:
                continue
            observe(state, seat, action, lookups["info"], models[int(seat) - 1], stats[seat], attacks)
            try:
                game.apply(state, seat, action, **kwargs)
            except game.GameError:
                fallback = brain.fallback_action(state, seat)
                if not fallback:
                    continue
                game.apply(state, seat, fallback, **kwargs)
            moved = True
            break
        if not moved:
            return None
    return None


def observe(state, seat, action, info, model, stats, attacks):
    """What this action says about how the CPU used its resources."""
    if state.get("phase") == "encore" and action.get("type") in ("encore", "move"):
        stock = len(state["players"][seat]["zones"]["stock"])
        if action["type"] == "encore" or stock >= game.ENCORE_COST:  # one it couldn't pay for wasn't a choice
            card = game.locate(state, action["uid"])[1]
            level = game.number((info(card["card"]) or {}).get("level")) if card else 0
            stats["encores"].append((action["type"] == "encore", level, stock))
        return
    if state.get("turn") != seat or action.get("type") not in ("phase", "attack"):
        return
    side = state["players"][seat]
    key = (state["game_number"], state["turn_number"])
    if action["type"] == "attack":
        attacks[key] += 1
        return
    if action["phase"] == "climax" and state.get("phase") == "main":
        mind = cpu.MINDS[model](state, seat, info, cpu.Temper(), random.Random(0))
        stage = side["stage"]
        empty = [s for s in game.OPPOSITE if not stage[s]]
        back = [stage[s] for s in ("B1", "B2") if stage[s]]
        playable = [c for c in side["zones"]["hand"] if mind.kind(c) == "character" and mind.can_play(c)]
        missed = bool(empty and (back or playable)) and state["turn_number"] > 1
        stats["open_lanes"].append(missed)
        if missed and stats["show"][0] > 0:
            stats["show"][0] -= 1
            show_board(state, seat, mind, stats["show"][1])
        stats["stock_main"].append(len(side["zones"]["stock"]))
        open_back = [s for s in ("B1", "B2") if not stage[s]]
        stats["open_back"].append(bool(open_back and playable and not empty) and state["turn_number"] > 1)
    if action["phase"] == "attack" and state.get("phase") == "climax":
        mind = cpu.MINDS[model](state, seat, info, cpu.Temper(), random.Random(0))
        if mind.playable_climaxes() and mind.attackers():
            stats["climax_held"].append(not side["zones"]["climax"])
    if action["phase"] == "encore" and state.get("phase") == "attack":
        stats["attacks"].append(attacks[key])
        stats["front"].append(sum(1 for s in game.OPPOSITE if side["stage"][s]))


def show_board(state, seat, mind, write):
    """The board when it left a lane open, and what it could have filled it with."""
    side, them = state["players"][seat], state["players"][game.other_player(state, seat)]
    stats = state.get("stats", {})

    def describe(card):
        if not card:
            return "-"
        d = mind.details(card)
        power = stats.get(card["uid"], {}).get("power", d.get("power"))
        return f"{d.get('name', '?')[:28]} L{d.get('level')} {power}{' ' + card['pos'] if card.get('pos') not in (None, 'stand') else ''}"

    write(f"--- seat {seat}, turn {state['turn_number']}, level {mind.my_level()}, stock {len(side['zones']['stock'])}, "
          f"hand {len(side['zones']['hand'])}")
    for slot in game.OPPOSITE:
        write(f"  {slot}: {describe(side['stage'][slot]):45} vs {describe(them['stage'][game.OPPOSITE[slot]])}")
    for slot in ("B1", "B2"):
        card = side["stage"][slot]
        idle = "" if not card else " (idle)" if mind.idle_in_back(card) else " (busy)"
        write(f"  {slot}: {describe(card)}{idle}")
        if card and not mind.idle_in_back(card):
            write(f"      {(mind.details(card).get('text') or '').splitlines()[0][:150]}")
    for card in side["zones"]["hand"]:
        if mind.kind(card) == "character":
            write(f"  hand: {describe(card)} cost {mind.play_cost(card)} playable={mind.can_play(card)}")
