"""Card sleeves: how a player's face-down cards look, on their side of the board and to their opponent.

Three are built in and everyone has them; staff upload the rest, each unlocked by conditions they set (all of them,
or any one), or given to a player by hand. A condition is {kind, count, target}: one of KINDS, the number to reach,
and for some kinds a CPU, arcade list or narrative challenge it has to be done against (none: any of them).

What a player does is counted from when sleeves came in, never before: each finished game adds to their profile's
progress ({key: number}, a key being a kind, or "kind:target" for the same done against that one), and whatever
sleeve that newly meets is theirs. Some kinds count things up (games won); the "best" ones keep the highest yet
(an arcade run's score).
"""
from dataclasses import dataclass
from typing import Callable

from django.db import transaction

from .models import ArcadeRun, ArcadeScenario, ChallengeRun, CpuProfile, NarrativeChallenge, PlayerProfile, Sleeve, SleeveUnlock

MAX_COUNT = 1_000_000


def times(n):
    return "" if n == 1 else f" {n} times"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


@dataclass(frozen=True)
class Kind:
    label: str  # for staff choosing it
    text: Callable  # (count, target name or None) -> what the player is told to do
    target: str = ""  # what it can be limited to: "cpu", "scenario" or "narrative"
    best: bool = False  # the highest reached in one go, rather than a count


KINDS = {
    "wins": Kind("Games won, against anyone", lambda n, t: f"Win {plural(n, 'game')}"),
    "cpu_wins": Kind("Games won against CPUs", lambda n, t: f"Win {plural(n, 'game')} against {t or 'CPUs'}", target="cpu"),
    "flash_wins": Kind("Flash battles won", lambda n, t: f"Win {plural(n, 'flash battle')}"),
    "arcade_clears": Kind("Arcade lists cleared", lambda n, t: f"Clear {t or 'an arcade list'} in arcade mode{times(n)}", target="scenario"),
    "arcade_score": Kind("Score in one arcade run", lambda n, t: f"Score {n} in one arcade run{f' of {t}' if t else ''}", target="scenario", best=True),
    "challenge_clears": Kind("Free or narrative challenges cleared",
                             lambda n, t: f"Clear {f'the {t} challenge' if t else 'a free or narrative challenge'}{times(n)}", target="narrative"),
    "infinite_floors": Kind("Floors climbed in one infinite challenge", lambda n, t: f"Climb {plural(n, 'floor')} in one infinite challenge", best=True),
    "infinite_score": Kind("Score in one infinite challenge", lambda n, t: f"Score {n} in one infinite challenge", best=True),
    "bosses": Kind("Infinite challenge bosses beaten (solo or co-op)", lambda n, t: f"Beat {'an infinite challenge boss' if n == 1 else f'{n} infinite challenge bosses'}"),
    "coop_floors": Kind("Floors climbed in one co-op challenge", lambda n, t: f"Climb {plural(n, 'floor')} in one co-op challenge", best=True),
}

TARGETS = {"cpu": CpuProfile, "scenario": ArcadeScenario, "narrative": NarrativeChallenge}


def key_of(condition):
    return f"{condition['kind']}:{condition['target']}" if condition.get("target") else condition["kind"]


def met(sleeve, progress):
    """Whether this progress meets the sleeve's conditions (as it has them: all, or any one)."""
    done = [progress.get(key_of(c), 0) >= c["count"] for c in sleeve.conditions if c.get("kind") in KINDS]
    return bool(done) and (all(done) if sleeve.match == Sleeve.Match.ALL else any(done))


def target_names(conditions):
    """{(target type, id): name} for the targets of these conditions."""
    wanted = {}
    for condition in conditions:
        kind = KINDS.get(condition.get("kind"))
        if kind and kind.target and condition.get("target"):
            wanted.setdefault(kind.target, set()).add(condition["target"])
    return {(what, pk): str(found) for what, pks in wanted.items() for pk, found in TARGETS[what].objects.in_bulk(pks).items()}


def describe(condition, names, progress=None):
    """A condition as the player reads it: {text, have, need, percent, met}; have and the rest only with progress."""
    kind = KINDS[condition["kind"]]
    target = condition.get("target")
    name = names.get((kind.target, target), "(deleted)") if target else None
    shown = {"text": kind.text(condition["count"], name), "need": condition["count"]}
    if progress is not None:
        have = progress.get(key_of(condition), 0)
        shown.update(have=min(have, condition["count"]), met=have >= condition["count"], percent=min(100, round(have * 100 / condition["count"])))
    return shown


# Progress, and what it unlocks ------------------------------------------------------------------------------------

def check(user_id, progress=None):
    """Unlock every offered sleeve this player now meets the conditions of. Returns those newly unlocked."""
    if progress is None:
        progress = PlayerProfile.objects.filter(user_id=user_id).values_list("progress", flat=True).first() or {}
    have = set(SleeveUnlock.objects.filter(user_id=user_id).values_list("sleeve_id", flat=True))
    new = [sleeve for sleeve in Sleeve.objects.filter(hidden=False) if sleeve.pk not in have and sleeve.conditions and met(sleeve, progress)]
    SleeveUnlock.objects.bulk_create([SleeveUnlock(user_id=user_id, sleeve=sleeve) for sleeve in new], ignore_conflicts=True)
    return new


def record(user_id, counts=None, bests=None):
    """Add to a player's progress (counts: {key: how many more}; bests: {key: a value, kept if it's the highest}),
    then unlock what that meets. Returns the sleeves newly unlocked."""
    if not counts and not bests:
        return []
    with transaction.atomic():
        profile, _ = PlayerProfile.objects.select_for_update().get_or_create(user_id=user_id)
        progress = profile.progress or {}
        for key, more in (counts or {}).items():
            progress[key] = progress.get(key, 0) + more
        for key, value in (bests or {}).items():
            progress[key] = max(progress.get(key, 0), value)
        profile.progress = progress
        profile.save(update_fields=["progress"])
        return check(user_id, progress)


def with_target(counts, kind, target):
    """Count one of `kind`, and one against this target too."""
    counts[kind] = counts.get(kind, 0) + 1
    if target:
        counts[f"{kind}:{target}"] = counts.get(f"{kind}:{target}", 0) + 1


def game_ended(room, over, run=None, trial=None):
    """A game has just ended (see play.game_ended): count it towards the players' sleeves. `run` is the arcade run it
    was fought for, if it was still going, as arcade.game_finished has left it; `trial` the challenge that was for, as
    it was before. What each player newly unlocked goes in over["sleeves"] ({user id: [{name, css}]}), for their
    Victory or Defeat screen."""
    host_won = over["winner"] == str(room.host_id)
    winner = room.host_id if host_won else room.guest_id
    counts, bests = {}, {}
    if not room.vs_cpu:
        record_for(over, winner, {"wins": 1})
        return
    if not host_won:
        return
    state = room.state
    counts["wins"] = 1
    with_target(counts, "cpu_wins", room.cpu_profile_id)
    if state.get("flash"):
        counts["flash_wins"] = 1
    if run and trial is None:
        if run.score:
            bests["arcade_score"] = run.score
            if run.scenario_id:
                bests[f"arcade_score:{run.scenario_id}"] = run.score
        if run.status == ArcadeRun.Status.CLEARED:
            with_target(counts, "arcade_clears", run.scenario_id)
    elif run and trial.kind == ChallengeRun.Kind.INFINITE:
        # A co-op boss is beaten only once its health bar is empty: a win any other way doesn't count (see challenge.coop_fight_finished).
        beaten = not state.get("shared_boss") or over.get("reason") == "boss"
        if beaten and state.get("floor") is not None:
            bests["coop_floors" if trial.coop_id else "infinite_floors"] = state["floor"] + 1
        if beaten and state.get("boss"):
            counts["bosses"] = 1
        if not trial.coop_id and run.score:
            bests["infinite_score"] = run.score
    elif run and run.status == ArcadeRun.Status.CLEARED:  # a free or narrative challenge, won
        with_target(counts, "challenge_clears", trial.narrative_id)
    record_for(over, winner, counts, bests)


def record_for(over, user_id, counts, bests=None):
    unlocked = record(user_id, counts, bests)
    if unlocked:
        over.setdefault("sleeves", {})[str(user_id)] = [{"name": sleeve.name, "css": sleeve.css} for sleeve in unlocked]


# What players see -------------------------------------------------------------------------------------------------

def css_of(sleeve):
    return sleeve.css if sleeve else Sleeve(style=Sleeve.DEFAULT).css


def board_sleeves(room, seat_user_id):
    """{"me": css, "opponent": css}: each side's face-down look, from this player's seat. A CPU's is its profile's."""
    chosen = dict(PlayerProfile.objects.filter(user_id__in=[room.host_id, room.guest_id], sleeve__isnull=False).values_list("user_id", "sleeve"))
    sleeves = Sleeve.objects.in_bulk(chosen.values())

    def of(user_id):
        if room.vs_cpu and user_id == room.guest_id:
            return css_of(room.cpu_profile.sleeve if room.cpu_profile_id and room.cpu_profile else None)
        return css_of(sleeves.get(chosen.get(user_id)))

    other = room.guest_id if seat_user_id == room.host_id else room.host_id
    return {"me": of(seat_user_id), "opponent": of(other)}


def owned_ids(user, profile=None):
    """The sleeves this player can use: everyone's (unless hidden), those unlocked or given, and the one they have on."""
    ids = set(SleeveUnlock.objects.filter(user=user).values_list("sleeve_id", flat=True))
    if profile and profile.sleeve_id:
        ids.add(profile.sleeve_id)
    return ids


def shelf(user, profile):
    """Every sleeve this player can see, for their profile: [{sleeve, owned, chosen, conditions}], theirs first. A
    hidden sleeve shows only to those who have it."""
    owned = owned_ids(user, profile)
    progress = profile.progress if profile else {}
    sleeves = list(Sleeve.objects.all())
    names = target_names([c for sleeve in sleeves for c in sleeve.conditions])
    chosen = profile.sleeve_id if profile and profile.sleeve_id else next((s.pk for s in sleeves if s.style == Sleeve.DEFAULT), None)
    found = []
    for sleeve in sleeves:
        mine = sleeve.pk in owned or (sleeve.free and not sleeve.hidden)
        if sleeve.hidden and not mine:
            continue
        conditions = [] if mine else [describe(c, names, progress) for c in sleeve.conditions if c.get("kind") in KINDS]
        found.append({"sleeve": sleeve, "owned": mine, "chosen": sleeve.pk == chosen, "conditions": conditions})
    found.sort(key=lambda item: not item["owned"])
    return found


def can_use(user, sleeve, profile=None):
    return (sleeve.free and not sleeve.hidden) or sleeve.pk in owned_ids(user, profile)


def unseen(user):
    """Sleeves this player has newly got and not yet been told about."""
    return list(SleeveUnlock.objects.filter(user=user, seen=False).select_related("sleeve").order_by("unlocked", "pk"))


# Staff --------------------------------------------------------------------------------------------------------------

def read_conditions(post):
    """(conditions, error) from the sleeve form's rows: each a kind, a target and a count. A row with no kind is skipped."""
    kinds, targets, counts = post.getlist("kind"), post.getlist("target"), post.getlist("count")
    if not len(kinds) == len(targets) == len(counts):
        return None, "The conditions didn't come through whole. Try again."
    conditions = []
    for kind_id, target, count in zip(kinds, targets, counts):
        if not kind_id:
            continue
        kind = KINDS.get(kind_id)
        if not kind:
            return None, "That isn't a kind of condition."
        if not count.isdigit() or not 1 <= int(count) <= MAX_COUNT:
            return None, f"{kind.label}: the number to reach goes from 1 to {MAX_COUNT:,}."
        condition = {"kind": kind_id, "count": int(count)}
        if kind.target and target:
            if not target.isdigit() or not TARGETS[kind.target].objects.filter(pk=target).exists():
                return None, f"{kind.label}: that {kind.target.replace('scenario', 'arcade list')} doesn't exist."
            condition["target"] = int(target)
        conditions.append(condition)
    return conditions, None
