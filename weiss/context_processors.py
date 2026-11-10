from core.access import has_weiss_access

from . import challenge, sleeves
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
    current = challenge.current(user)
    header = {"nav_avatar": profile.avatar if profile else None, "challenge_open": True,
              # The header's infinite challenge button: to the challenge menu, or with a challenge under way, back to it.
              "infinite_start": current is None,
              # The game board's sound effects (see play.js), as the player last set them.
              "sound_on": profile.sound_on if profile else True, "sound_volume": profile.sound_volume if profile else 60}
    if not match or match.namespace != "weiss":
        return header
    return {**header, **panel_context(request), "arcade_paused": paused_run(request),
            "sleeves_unlocked": sleeves.unseen(user) if match.url_name != "profile" else []}
