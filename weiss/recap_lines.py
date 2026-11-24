"""The duel recap's captions for its standout moments (docs/round-two-plan.md, section 1), read by play.duel_recap_view.

RECAP_LINES[kind]["you"] is for the viewing player's own moment, ["them"] for the other player's: the moment's side is
the winner's for comeback, close_finish and flawless, and the attacker's for big_hit, big_cancel and burst_turn. Each is
one line of at most 60 characters once filled. Fills: {turn} (the moment's turn), {n} (its damage), {name} (the other
player's name) and {player} (the viewing player's).
"""

RECAP_LINES = {
    "comeback": {"you": "You fought back from far behind to win.",
                 "them": "{name} fought back from far behind to win."},
    "close_finish": {"you": "Both at level 3, and you held on to win.",
                     "them": "Both at level 3, and {name} held on to win."},
    "flawless": {"you": "You won without getting past level 1.",
                 "them": "{name} won without getting past level 1."},
    "big_hit": {"you": "Turn {turn}: you landed a {n}-damage hit.",
                "them": "Turn {turn}: {name} landed a {n}-damage hit."},
    "big_cancel": {"you": "Turn {turn}: your {n}-damage attack was cancelled.",
                   "them": "Turn {turn}: you cancelled a {n}-damage attack."},
    "burst_turn": {"you": "Turn {turn}: you dealt {n} damage in one turn.",
                   "them": "Turn {turn}: {name} dealt {n} damage in one turn."},
}
