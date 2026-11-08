"""Co-op challenge: two players' infinite challenge, played together (see docs/coop-challenge.md).

The host starts one and shares its invite link; whoever opens it first (with no challenge of their own under way)
is their partner. Each player has their own ChallengeRun, as in a solo infinite challenge: their own packs to open,
rewards to claim, deck and fights. What they share is on the CoopRun: the pool every pack opens into (a copy in one
deck can't be in the other), the path, the votes on where it goes, and the lost games, theirs together, that end it
at the loss limit staff set (each loss adds one; the run goes on until then). After each boss they play each other
once, for first pick of the curses beating it brings (see the vs. battles, below).
"""
import copy
from contextlib import contextmanager
from functools import wraps

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from . import augments, curses
from .models import CardList, ChallengeRun, ChallengeSettings, CoopRun

LOSS_LIMIT = 3  # lost games, both players' together, that end a co-op challenge, until staff set it (see loss_limit)
START_PACKS = 20  # packs each player starts with, until staff set it (see start_packs)
NAME = "Co-op challenge"
BOSS_HEALTH = 42  # the damage a boss takes, both players' games together, to go down, until staff set it (see boss_health)


def loss_limit():
    """What staff set on the CPU tab, or LOSS_LIMIT if they never have."""
    settings = ChallengeSettings.current()
    return settings.coop_loss_limit if settings else LOSS_LIMIT


def start_packs():
    """The packs each player of a co-op challenge starts with: what staff set, or START_PACKS."""
    settings = ChallengeSettings.current()
    return settings.coop_start_packs if settings else START_PACKS


def boss_health():
    """What staff set on the CPU tab, or BOSS_HEALTH if they never have."""
    settings = ChallengeSettings.current()
    return settings.coop_boss_health if settings else BOSS_HEALTH


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


# Bosses ------------------------------------------------------------------------------------------------------------
# A boss floor's boss is the pair's to wear down together: kept with the path as "boss", {"floor", "health", "max",
# "dealt": {user id: damage}, "down"}, for the boss the pair is on (or was on last).

def boss_of(path, floor):
    """The boss of this floor as the pair has left it; one at full health if they haven't fought it yet."""
    boss = (path or {}).get("boss")
    if boss and boss["floor"] == floor:
        return boss
    health = boss_health()
    return {"floor": floor, "health": health, "max": health, "dealt": {}}


def hit_boss(run, floor, dealt):
    """This player's game against the boss of `floor` has just dealt it this much damage (as it lands, see
    play.wear_boss). Call within `shared`. Returns whether that took it down."""
    boss = run.path["boss"] = boss_of(run.path, floor)
    boss["health"] = max(0, boss["health"] - dealt)
    boss["dealt"][str(run.user_id)] = boss["dealt"].get(str(run.user_id), 0) + dealt
    return boss["health"] == 0


def lost_game(run, count=1):
    """A game lost that counts (not one a second chance covered): one more towards the limit (or `count`: two with
    Glass Cannon), and at it, the end of the challenge for both. Call within `shared`. Returns whether that ended it."""
    pair = run.coop
    pair.losses += count
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


# Vs. battles -----------------------------------------------------------------------------------------------------
# After each boss the pair play each other, a game of its own that no loss counts from (see docs/coop-vs-battles.md).
# It's kept with the path as "duel", {"floor" of the boss, "options": the curses offered and "augments": the augments,
# the same for both, "ready": [user id, ...], "room" (its GameRoom, once dealt), "winner" and "loser" (user ids, once
# it's over), "picks": {user id: curse id}, "augment_picks": {user id: augment id, or None for packs instead}}. The
# winner takes their augment and curse first; the loser, of those left. Once both have, it's done with, kept as
# "last_duel" for the page to say how it went. The pair's rivalry, its wins, is CoopRun.duel_wins.

def start_duel(run, floor, rng):
    """The pair has beaten the boss of `floor`: their vs. battle is due, with the augments and curses it decides the
    picks of: augments either of them could take. Call within `shared`."""
    run.path["duel"] = {"floor": floor, "options": curses.offer(rng), "augments": augments.shared_offer([run, partner_run(run)], rng),
                        "ready": [], "room": None, "winner": None, "picks": {}, "augment_picks": {}}


def duel_of(run):
    """The pair's vs. battle still to be played or picked after, or None."""
    return (run.path or {}).get("duel")


def duel_due(run):
    """What's wrong if this player has the vs. battle, or its picks, still to come, which they must before their next
    fight; or None."""
    duel = duel_of(run)
    if not duel or str(run.user_id) in duel["picks"]:
        return None
    if not duel["winner"]:
        return "Your vs. battle with your partner comes first: its winner picks their augment and curse first."
    return "Take your augment and curse first: the vs. battle is over, and they're waiting."


def ready_for_duel(run):
    """This player is ready for the vs. battle. Once both are, it's dealt, with both decks as they are now (a partner
    whose deck isn't ready any more is made unready instead). Returns its room once dealt, else None. Call within
    `shared`."""
    from .challenge import deck_ready  # weiss.challenge uses this module
    from .models import GameRoom
    from .play import deal
    duel = duel_of(run)
    if duel["room"]:
        return GameRoom.objects.filter(pk=duel["room"]).first()
    if str(run.user_id) not in duel["ready"]:
        duel["ready"].append(str(run.user_id))
    other = partner_run(run)
    if not other or str(other.user_id) not in duel["ready"]:
        return None
    if deck_ready(other):
        duel["ready"].remove(str(other.user_id))
        return None
    pair = run.coop
    host, guest = (run, other) if run.user_id == pair.host_id else (other, run)
    room = GameRoom(host=host.user, guest=guest.user, host_deck=host.deck, guest_deck=guest.deck, coop_duel=pair, status=GameRoom.Status.PLAYING)
    deal(room)
    room.save()
    duel["room"] = room.pk
    return room


def duel_finished(room, over):
    """The vs. battle's game is over (`over`, its game_over): its winner's, and one more win in the pair's rivalry."""
    with transaction.atomic():
        pair = CoopRun.objects.select_for_update().get(pk=room.coop_duel_id)
        duel = (pair.path or {}).get("duel")
        if not duel or duel["room"] != room.pk or duel["winner"]:
            return
        duel["winner"], duel["loser"] = over["winner"], over["loser"]
        pair.duel_wins[over["winner"]] = pair.duel_wins.get(over["winner"], 0) + 1
        pair.version += 1
        pair.save(update_fields=["path", "duel_wins", "version"])


def duel_turn(duel):
    """Whose pick of the augments and curses it is (user id), or None: the winner's, then the loser's."""
    if not duel["winner"]:
        return None
    if duel["winner"] not in duel["picks"]:
        return duel["winner"]
    return duel["loser"] if duel["loser"] not in duel["picks"] else None


def augments_left(duel):
    """The vs. battle's augments not taken yet."""
    return [a for a in duel.get("augments", []) if a not in duel.get("augment_picks", {}).values()]


def pick_after_duel(run, curse_id, augment_id):
    """This player takes one of the vs. battle's augments and one of its curses, in their turn (duel_turn), neither
    one their partner took. With no augment left to take, they get packs instead (buffs.EXTRA_PACKS). Once both have,
    the battle's done with, and its room goes. Raises ValueError saying what's wrong. Call within `shared`."""
    from .buffs import EXTRA_PACKS  # weiss.buffs uses this module
    duel = duel_of(run)
    me = str(run.user_id)
    if not duel or not duel["winner"]:
        raise ValueError("The vs. battle isn't over yet.")
    if me in duel["picks"]:
        raise ValueError("You've taken your augment and curse already.")
    if duel_turn(duel) != me:
        raise ValueError("The winner picks first: wait for your partner.")
    left = augments_left(duel)
    if left and augment_id not in left:
        raise ValueError("Choose one of the augments left.")
    if curse_id not in duel["options"] or curse_id in duel["picks"].values():
        raise ValueError("Choose one of the curses left.")
    duel["picks"][me], duel.setdefault("augment_picks", {})[me] = curse_id, augment_id if left else None
    curses.take(run, curse_id)
    if left:
        augments.take(run, augment_id)
    else:
        run.packs += EXTRA_PACKS
    run.save(update_fields=["curses", "augments", "packs"])
    if len(duel["picks"]) == len(players(run.coop)):
        run.path["last_duel"] = run.path.pop("duel")
        run.coop.duel_rooms.all().delete()  # its game is recorded (GameRecord); the table needn't stay among their rooms


def rivalry(pair, user_id):
    """The pair's vs. battles won: (this player's, their partner's)."""
    wins = pair.duel_wins or {}
    theirs = sum(n for winner, n in wins.items() if winner != str(user_id))
    return wins.get(str(user_id), 0), theirs


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
    first, each with `duels`, the vs. battles that player won), `score`, `wins`, `rivalry` (whether they've played
    one) and `floor` worked out."""
    pairs = []
    for pair in CoopRun.objects.exclude(guest=None).select_related("host", "guest").prefetch_related("runs__arcade_run", "runs__user"):
        pair.halves = sorted(pair.runs.all(), key=lambda run: run.user_id != pair.host_id)
        pair.score = sum(run.arcade_run.score for run in pair.halves if run.arcade_run)
        pair.wins = sum(run.arcade_run.position for run in pair.halves if run.arcade_run)
        pair.floor = (pair.path or {}).get("done", 0) + 1
        for run in pair.halves:
            run.duels = (pair.duel_wins or {}).get(str(run.user_id), 0)
        pair.rivalry = bool(pair.duel_wins)
        if pair.score:
            pairs.append(pair)
    pairs.sort(key=lambda pair: (-pair.score, pair.started, pair.pk))
    return pairs[:limit]
