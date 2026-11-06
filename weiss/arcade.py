"""Arcade mode: a run through a scenario's CPUs, opener first, anchor last, fillers shuffled between.

A run keeps its order when it starts, and plays out in one room: each fight deals that room again with
the next CPU in its seat. Beating the anchor clears the scenario, which goes on the deck as a marker.

A scenario can have scenes: one before the first fight and one once it's cleared, and for each CPU one
before its fight and one after beating it. The room queues them (state["scenes"]) and the board plays them.
A challenge's run (weiss.challenge) is an arcade run too, with its own rules on winning and losing.
"""
import random

from django.db.models import F
from django.utils import timezone

from . import challenge, scenes
from .models import ArcadeClear, ArcadeEntry, ArcadeRun, ArcadeScenario, CpuProfile


def can_fight(cpu):
    return bool(cpu and cpu.finalized and cpu.deck_id)


def scenario_problem(scenario):
    """Why players can't play this scenario yet, or None."""
    entries = list(scenario.entries.all())
    roles = {entry.role for entry in entries}
    missing = [role for role in (ArcadeEntry.Role.OPENER, ArcadeEntry.Role.ANCHOR) if role not in roles]
    if missing:
        return "It needs " + " and ".join(f"an {role}" for role in missing) + "."
    unready = [entry.cpu.name for entry in entries if not can_fight(entry.cpu)]
    if unready:
        return "These CPUs aren't finalized with a deck: " + ", ".join(unready) + "."
    return None


def all_scenarios():
    return list(ArcadeScenario.objects.prefetch_related("entries__cpu"))


def ready_scenarios():
    return [scenario for scenario in all_scenarios() if not scenario_problem(scenario)]


def fight_count(scenario):
    """How many fights a run of this scenario is: a branch takes another's place rather than adding one."""
    return sum(entry.role != ArcadeEntry.Role.BRANCH for entry in scenario.entries.all())


def fight_order(scenario, rng=random, fixed=False):
    """The CPUs of a new run, as profile ids: the fillers shuffled, or (fixed, for a narrative challenge) in their
    set order. Branches aren't in it: a scene puts one in (see play.choose_fight)."""
    by_role = {role: [] for role in ArcadeEntry.Role.values}
    for entry in sorted(scenario.entries.all(), key=lambda entry: (entry.position, entry.pk)):
        by_role[entry.role].append(entry.cpu_id)
    if not fixed:
        rng.shuffle(by_role[ArcadeEntry.Role.FILLER])
    return by_role[ArcadeEntry.Role.OPENER] + by_role[ArcadeEntry.Role.FILLER] + by_role[ArcadeEntry.Role.ANCHOR]


def current_cpu(run):
    """The CPU this run fights now. A filler taken away since the run began is skipped; with the anchor
    gone there's nothing left to win, so that's None."""
    cpus = CpuProfile.objects.in_bulk(run.order)
    while run.position < len(run.order):
        cpu = cpus.get(run.order[run.position])
        if can_fight(cpu):
            return cpu
        if run.position == len(run.order) - 1:
            return None
        run.position += 1
        run.save(update_fields=["position"])
    return None


def lineup(scenario, user):
    """A scenario's CPUs in the order they're fought (fillers by name), each {"cpu", "role", "role_label",
    "met"}. The opener is always shown; the rest only once this player has played them in a run."""
    met = {cpu_id for run in ArcadeRun.objects.filter(user=user, scenario=scenario) for cpu_id in run.fought}
    return [{"cpu": entry.cpu, "role": entry.role, "role_label": entry.get_role_display(),
             "met": entry.role == ArcadeEntry.Role.OPENER or entry.cpu_id in met}
            for entry in scenario.ordered_entries if entry.role != ArcadeEntry.Role.BRANCH or entry.cpu_id in met]


def entry_of(run, cpu_id):
    return ArcadeEntry.objects.filter(scenario_id=run.scenario_id, cpu_id=cpu_id).select_related("scene_before", "scene_after").first() if run.scenario_id else None


def scenes_before(run, cpu, opening=True):
    """Scene payloads to play before fighting this CPU: the scenario's opening one first, if this is the first
    fight (and `opening`: not when a scene has just swapped the CPU, as the opening's been seen)."""
    scenario = run.scenario
    entry = entry_of(run, cpu.pk)
    first = scenario and run.position == 0 and opening
    return scenes.playable([scenario.intro_scene if first else None, entry and entry.scene_before],
                           with_buffs=challenge.of(run) is not None, viewer=run.user)


def scenes_after(run, cpu_id, cleared):
    """Scene payloads to play after beating this CPU, and the scenario's closing one if that cleared it."""
    entry = entry_of(run, cpu_id)
    return scenes.playable([entry and entry.scene_after, run.scenario.outro_scene if cleared and run.scenario else None],
                           with_buffs=challenge.of(run) is not None, viewer=run.user)


def game_finished(room, over, score=None):
    """A fight has ended: count it, add a win's score to the run, and clear the scenario if that was the anchor.
    A win queues the scenes that follow it; a challenge's run also hears how it went."""
    run = room.arcade_run
    if not run or run.status != ArcadeRun.Status.ACTIVE:
        return
    if room.cpu_profile_id and room.cpu_profile_id not in run.fought:
        run.fought.append(room.cpu_profile_id)  # met now, won or lost
        run.save(update_fields=["fought"])
    if over["winner"] != str(room.host_id):
        run.losses += 1
        run.save(update_fields=["losses"])
        challenge.fight_finished(run, won=False, cleared=False)
        return
    if score is not None:
        run.scores.append({"cpu": room.cpu_profile_id, "name": room.cpu_name, "score": score})
        run.score += score
    run.position += 1
    if room.host_deck_id:  # as it was for this win, for the high scores
        run.deck_snapshot = challenge.deck_snapshot(room.host_deck)
    cleared = run.position >= len(run.order) and not challenge.infinite(run)  # whose next is chosen on its path
    if queued := scenes_after(run, room.cpu_profile_id, cleared):
        room.state["scenes"] = queued
    if prize := challenge.fight_finished(run, won=True, cleared=cleared):
        room.state["prize"] = challenge.prize_shown(prize)  # the Victory screen draws it, slot machine and all
    if not cleared:
        run.save(update_fields=["position", "scores", "score", "order", "deck_snapshot"])
        return
    run.status, run.finished = ArcadeRun.Status.CLEARED, timezone.now()
    run.save(update_fields=["position", "status", "finished", "scores", "score", "deck_snapshot"])
    if room.host_deck_id and run.scenario_id:
        clear, _ = ArcadeClear.objects.get_or_create(deck_id=room.host_deck_id, scenario_id=run.scenario_id, defaults={"name": run.scenario_name})
        ArcadeClear.objects.filter(pk=clear.pk).update(count=F("count") + 1, name=run.scenario_name)


def high_scores(scenarios, limit=10):
    """Each scenario with its leaderboard as `leaders`: its best runs that have scored, the earliest first on a tie."""
    for scenario in scenarios:
        scenario.leaders = list(ArcadeRun.objects.filter(scenario=scenario, score__gt=0).select_related("user").order_by("-score", "started", "pk")[:limit])
    return scenarios


def end_run(run):
    """The player has stopped. A cleared run stays cleared."""
    if run.status == ArcadeRun.Status.ACTIVE:
        run.status, run.finished = ArcadeRun.Status.ABANDONED, timezone.now()
        run.save(update_fields=["status", "finished"])
