"""Scoring a win against a CPU, from what the game counted as it went (state["tallies"], see game.tally).

Only wins are scored. What counts, heaviest first:
- the level gap: how many levels the loser was above the winner when the game ended (high);
- the opponent's characters reversed, or put into the waiting room from the stage by an effect (medium);
- cards drawn, in the draw phase, the clock phase or by an effect (low);
- abilities used: every one that resolved, ACT, AUTO or an event (very low).
"""

WEIGHTS = {"level_gap": 1000, "knocked": 100, "drawn": 10, "abilities": 2}
LABELS = {"level_gap": "level gap", "knocked": "characters knocked out", "drawn": "cards drawn", "abilities": "abilities used"}


def win_score(state, winner):
    """{"total", "parts": [{"key", "label", "count", "points"}]} for the winner of a finished game."""
    loser = next((p for p in state["order"] if p != str(winner)), None)
    stats = state.get("tallies", {}).get(str(winner), {})
    levels = {p: len(state["players"][p]["zones"]["level"]) for p in state["order"]}
    counts = {"level_gap": max(0, levels.get(loser, 0) - levels.get(str(winner), 0)) if loser else 0,
              "knocked": stats.get("knocked", 0), "drawn": stats.get("drawn", 0), "abilities": stats.get("abilities", 0)}
    parts = [{"key": key, "label": LABELS[key], "count": counts[key], "points": counts[key] * weight} for key, weight in WEIGHTS.items()]
    return {"total": sum(part["points"] for part in parts), "parts": parts}
