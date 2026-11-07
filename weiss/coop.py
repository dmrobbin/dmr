"""Co-op challenge: two players' infinite challenge, played together (see docs/coop-challenge.md).

The host starts one and shares its invite link; whoever opens it first (with no challenge of their own under way)
is their partner. Each player has their own ChallengeRun, as in a solo infinite challenge: their own packs to open,
rewards to claim, deck and fights. What they share is on the CoopRun: the pool every pack opens into (a copy in one
deck can't be in the other), the path, the votes on where it goes, and the lost games, theirs together, that end it
at the loss limit staff set (each loss adds one; the run goes on until then).
"""
import copy
from contextlib import contextmanager
from functools import wraps

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import CardList, ChallengeRun, ChallengeSettings, CoopRun

LOSS_LIMIT = 3  # lost games, both players' together, that end a co-op challenge, until staff set it (see loss_limit)
START_PACKS = 20  # packs each player starts with, until staff set it (see start_packs)
NAME = "Co-op challenge"


def loss_limit():
    """What staff set on the CPU tab, or LOSS_LIMIT if they never have."""
    settings = ChallengeSettings.current()
    return settings.coop_loss_limit if settings else LOSS_LIMIT


def start_packs():
    """The packs each player of a co-op challenge starts with: what staff set, or START_PACKS."""
    settings = ChallengeSettings.current()
    return settings.coop_start_packs if settings else START_PACKS


def loadout():
    """The specialty packs each player starts with besides, to claim: [buff id, ...] (see challenge.LOADOUT_BUFFS)."""
    from .challenge import LOADOUT_BUFFS  # weiss.challenge uses this module
    settings = ChallengeSettings.current()
    chosen = settings.coop_loadout if settings else {}
    return [buff for buff in LOADOUT_BUFFS for _ in range(int(chosen.get(buff, 0)))]


# What the two players share --------------------------------------------------------------------------------------

def load(run, coop=None):
    """Put what the co-op challenge shares (its pool and path) on this player's run, as a solo run has them, so the
    rest of weiss.challenge reads them as it would. Returns the run."""
    if run and run.coop_id:
        coop = coop or run.coop
        run.pool, run.path = coop.pool, coop.path
    return run


@contextmanager
def shared(run):
    """Change what a co-op challenge shares: the CoopRun is locked, its pool and path put on the run, and whatever the
    run has then is saved back to it (unless something goes wrong: then nothing is). For a solo run, nothing happens.
    It can be nested: only the outermost locks and saves."""
    if not run.coop_id or getattr(run, "_sharing", False):
        yield
        return
    with transaction.atomic():
        coop = CoopRun.objects.select_for_update().get(pk=run.coop_id)
        load(run, coop)
        run.coop = coop  # locked: what else of it changes (lost games, say) can be saved by whatever's in here
        before = copy.deepcopy((coop.pool, coop.path))
        run._sharing = True
        try:
            yield
        finally:
            run._sharing = False
        if (run.pool, run.path) != before:
            coop.pool, coop.path = run.pool, run.path
            coop.version += 1
            coop.save(update_fields=["pool", "path", "version"])


def sharing(change):
    """A change to a run (its first argument) made within `shared`."""
    @wraps(change)
    def wrapper(run, *args, **kwargs):
        with shared(run):
            return change(run, *args, **kwargs)
    return wrapper


def partner_run(run):
    """The other player's ChallengeRun in this one's co-op challenge, or None."""
    if not run.coop_id:
        return None
    return ChallengeRun.objects.filter(coop_id=run.coop_id).exclude(pk=run.pk).select_related("deck").first()


def partner_copies(run):
    """{card id: copies} the partner's deck uses, which this player's can't."""
    other = partner_run(run)
    return dict(other.deck.entries.values_list("card_id", "quantity")) if other and other.deck else {}


def available(run):
    """{card id as str: copies} of the pool this player can use: what the partner's deck doesn't."""
    taken = partner_copies(run)
    return {pk: n - taken.get(int(pk), 0) for pk, n in run.pool.items() if n - taken.get(int(pk), 0) > 0}


def bump(coop):
    """Something changed that both pages should see."""
    CoopRun.objects.filter(pk=coop.pk).update(version=F("version") + 1)


# Floors and votes ----------------------------------------------------------------------------------------------------
# Kept with the shared path: "progress", {user id: floors that player has finished}, and "votes", {what's being decided:
# {user id: their vote}}. The last thing decided is kept as "decided", for both pages to say how it went.

def players(pair):
    return [pair.host_id] + ([pair.guest_id] if pair.guest_id else [])


def floor_of(path, user_id):
    """The floor this player is on: how many they've finished."""
    return (path or {}).get("progress", {}).get(str(user_id), 0)


def pair_floor(run):
    """The floor the pair is on: the one both are on, the slower one's."""
    return min(floor_of(run.path, user_id) for user_id in players(run.coop))


def furthest_floor(run):
    return max(floor_of(run.path, user_id) for user_id in players(run.coop))


def vote(run, path, key, choice, rng):
    """This player's vote on `key` (what's being decided: "floor:3", say), kept with the path. Once both players have
    voted it's decided, and that's returned: what they both chose, or if they chose differently, one of the two by a
    coin flip. Until then, None. A player can change their vote until it's decided."""
    votes = path.setdefault("votes", {})
    cast = votes.setdefault(key, {})
    cast[str(run.user_id)] = choice
    voters = [str(user_id) for user_id in players(run.coop)]
    if len(voters) < 2 or any(voter not in cast for voter in voters):
        return None
    chosen = [cast[voter] for voter in voters]
    decided = chosen[0] if chosen[0] == chosen[1] else rng.choice(chosen)
    path["decided"] = {"key": key, "votes": {voter: cast[voter] for voter in voters}, "flip": chosen[0] != chosen[1], "choice": decided}
    del votes[key]
    return decided


def vote_of(run, key):
    """This player's vote on `key`, if they've cast one and it's not decided yet."""
    return (run.path or {}).get("votes", {}).get(key, {}).get(str(run.user_id))


def partner_vote(run, key):
    return next((choice for voter, choice in (run.path or {}).get("votes", {}).get(key, {}).items() if voter != str(run.user_id)), None)


def event_vote(run, step, visit, option, rng):
    """This player's vote on a choice in the event the pair is at: the option they clicked of steps[step], the
    `visit`th time it's come up. Returns the option decided, once both have voted (see vote), else None. Call within
    `shared`. Raises ValueError if there's no such choice."""
    payload = run.path.get("event")
    steps = payload["steps"] if payload else []
    if not 0 <= step < len(steps) or steps[step]["do"] not in ("choice", "offer") or not 0 <= option < len(steps[step]["options"]):
        raise ValueError("There's no such choice in this event.")
    key = f"event:{step}:{visit}"
    decided = event_decided(run, step, visit)
    if decided is None:
        decided = vote(run, run.path, key, option, rng)
        if decided is not None:
            run.path.setdefault("event_choices", {})[key] = decided
    return decided


def event_decided(run, step, visit):
    """The option decided on a choice in the pair's event (see event_vote), or None if it's not decided yet."""
    return (run.path or {}).get("event_choices", {}).get(f"event:{step}:{visit}")


def agreed(path, payload, picks):
    """Of what a page says its event's choices gave ([[step, option], ...], see buffs.given), only what the pair
    decided: a choice's option counts only if it was decided on. The event's votes are done with then."""
    decided = {(int(key.split(":")[1]), option) for key, option in path.pop("event_choices", {}).items()}
    path["votes"] = {key: cast for key, cast in path.get("votes", {}).items() if not key.startswith("event:")}
    kept = []
    for pick in picks if isinstance(picks, list) else []:
        try:
            at, option = pick
            voted = payload["steps"][int(at)]["do"] in ("choice", "offer")
        except (TypeError, ValueError, IndexError, KeyError):
            continue
        if not voted or (int(at), option) in decided:
            kept.append(pick)
    return kept


def for_partner(run, change):
    """change(the partner's run), made within this run's `shared`: the partner's run gets the same pool and path,
    and whatever it does to them is this run's to save. Returns what change returns (None without a partner)."""
    other = partner_run(run)
    if not other:
        return None
    other.coop, other.pool, other.path, other._sharing = run.coop, run.pool, run.path, True
    try:
        return change(other)
    finally:
        other._sharing = False
        run.pool, run.path = other.pool, other.path


def finish_floor(run, players_done=None):
    """This player (or `players_done`, user ids: both, after an event) has finished the floor they were on. Once
    both have, the pair moves on, and the next fight's modifiers are done with. Call within `shared`."""
    progress = run.path.setdefault("progress", {})
    before = pair_floor(run)
    for user_id in players_done or [run.user_id]:
        progress[str(user_id)] = floor_of(run.path, user_id) + 1
    if pair_floor(run) > before:
        run.path["done"] = pair_floor(run)
        run.path["next"] = []


def lost_game(run):
    """A game lost that counts (not one a second chance covered): one more towards the limit, and at it, the end
    of the challenge for both. Call within `shared`. Returns whether that ended it."""
    pair = run.coop
    pair.losses += 1
    pair.save(update_fields=["losses"])
    if pair.losses < pair.loss_limit:
        return False
    end(pair)
    return True


def end(pair):
    """The co-op challenge is over, for both: each player's run is lost, as a solo one would be, and each keeps or
    discards their own deck."""
    from .challenge import give_up  # weiss.challenge uses this module
    pair.status, pair.finished = CoopRun.Status.LOST, timezone.now()
    pair.version += 1
    pair.save(update_fields=["status", "finished", "version"])
    for half in ChallengeRun.objects.filter(coop=pair, status=ChallengeRun.Status.ACTIVE).select_related("arcade_run", "deck"):
        give_up(half, keep_room=True)


# Starting --------------------------------------------------------------------------------------------------------

def new_half(user, coop):
    """A player's own run in a co-op challenge: an empty deck, their packs to open, and their loadout to claim."""
    from .buffs import grant  # weiss.buffs uses weiss.challenge, which uses this module
    from .challenge import deck_name
    deck = CardList.objects.create(user=user, name=deck_name(NAME), challenge=True)
    run = ChallengeRun.objects.create(user=user, kind=ChallengeRun.Kind.INFINITE, name=NAME, deck=deck, coop=coop, packs=start_packs())
    if buffs := loadout():
        grant(run, buffs, "Starting loadout")
    return run


def start(host):
    """A new co-op challenge, waiting for the host's partner to join by its invite link. Returns the host's run."""
    with transaction.atomic():
        coop = CoopRun.objects.create(host=host, loss_limit=loss_limit())
        return new_half(host, coop)


def join(coop, user):
    """Join a co-op challenge as the host's partner. Returns the partner's run, or raises ValueError saying why not."""
    from .challenge import current  # weiss.challenge uses this module
    with transaction.atomic():
        coop = CoopRun.objects.select_for_update().get(pk=coop.pk)
        if user.pk == coop.host_id:
            raise ValueError("This is your own co-op challenge: send the link to the friend you want to play it with.")
        if coop.status != CoopRun.Status.WAITING:
            raise ValueError("Someone has joined this co-op challenge already." if coop.status == CoopRun.Status.ACTIVE else "This co-op challenge is over.")
        if current(user):
            raise ValueError("Finish your own challenge first, or end it, to join this one.")
        coop.guest, coop.status = user, CoopRun.Status.ACTIVE
        coop.version += 1
        coop.save(update_fields=["guest", "status", "version"])
        return new_half(user, coop)


def cancel(coop):
    """The host calls it off before anyone has joined: their run and its deck go, as if it never was."""
    with transaction.atomic():
        for run in ChallengeRun.objects.filter(coop=coop).select_related("deck"):
            if run.deck:
                run.deck.delete()
            run.delete()
        coop.delete()


def waiting_for(user):
    """This player's co-op challenge still waiting for a partner, if they host one."""
    return CoopRun.objects.filter(host=user, status=CoopRun.Status.WAITING).first()


# The leaderboard -------------------------------------------------------------------------------------------------

def leaderboard(limit=50):
    """The best co-op challenges, by both players' scores added up (each win's score, see arcade.game_finished), the
    earliest first on a tie: those that have won at least once. Each has `halves` (both players' runs, the host's
    first), `score`, `wins` and `floor` worked out."""
    pairs = []
    for pair in CoopRun.objects.exclude(guest=None).select_related("host", "guest").prefetch_related("runs__arcade_run", "runs__user"):
        pair.halves = sorted(pair.runs.all(), key=lambda run: run.user_id != pair.host_id)
        pair.score = sum(run.arcade_run.score for run in pair.halves if run.arcade_run)
        pair.wins = sum(run.arcade_run.position for run in pair.halves if run.arcade_run)
        pair.floor = (pair.path or {}).get("done", 0) + 1
        if pair.score:
            pairs.append(pair)
    pairs.sort(key=lambda pair: (-pair.score, pair.started, pair.pk))
    return pairs[:limit]
