"""Arcade mode: a run through a scenario's CPUs, opener first, anchor last, fillers shuffled between.

A run keeps its order when it starts, and plays out in one room: each fight deals that room again with
the next CPU in its seat. Beating the anchor clears the scenario, which goes on the deck as a marker.
"""
import random

from django.db.models import F
from django.utils import timezone

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


def fight_order(scenario, rng=random):
    """The CPUs of a new run, as profile ids."""
    by_role = {role: [] for role in ArcadeEntry.Role.values}
    for entry in scenario.entries.all():
        by_role[entry.role].append(entry.cpu_id)
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


def game_finished(room, over):
    """A fight has ended: count it, and clear the scenario if that was the anchor."""
    run = room.arcade_run
    if not run or run.status != ArcadeRun.Status.ACTIVE:
        return
    if over["winner"] != str(room.host_id):
        run.losses += 1
        run.save(update_fields=["losses"])
        return
    run.position += 1
    if run.position < len(run.order):
        run.save(update_fields=["position"])
        return
    run.status, run.finished = ArcadeRun.Status.CLEARED, timezone.now()
    run.save(update_fields=["position", "status", "finished"])
    if room.host_deck_id and run.scenario_id:
        clear, _ = ArcadeClear.objects.get_or_create(deck_id=room.host_deck_id, scenario_id=run.scenario_id, defaults={"name": run.scenario_name})
        ArcadeClear.objects.filter(pk=clear.pk).update(count=F("count") + 1, name=run.scenario_name)


def end_run(run):
    """The player has stopped. A cleared run stays cleared."""
    if run.status == ArcadeRun.Status.ACTIVE:
        run.status, run.finished = ArcadeRun.Status.ABANDONED, timezone.now()
        run.save(update_fields=["status", "finished"])
