from core.access import has_weiss_access

from . import challenge
from .lists import panel_context
from .play import paused_run


def card_lists(request):
    """What every dashboard page's header needs from Weiss (the player's avatar, the infinite challenge button),
    and on Weiss pages, the card-list side panel's data too."""
    match = getattr(request, "resolver_match", None)
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and has_weiss_access(user)):
        return {}
    profile = getattr(user, "player_profile", None) if hasattr(user, "player_profile") else None
    challenge_open = user.is_staff or not challenge.STAFF_ONLY
    current = challenge.current(user) if challenge_open else None
    header = {"nav_avatar": profile.avatar if profile else None, "challenge_open": challenge_open,
              # The header's infinite challenge button starts one, unless a challenge is under way: then it goes to it.
              "infinite_start": challenge_open and current is None}
    if not match or match.namespace != "weiss":
        return header
    return {**header, **panel_context(request), "arcade_paused": paused_run(request)}
