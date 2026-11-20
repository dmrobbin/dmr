# Minigames in the game (plan and contract)

The five minigames (see [minigames-plan.md](minigames-plan.md)) go into three places, plus the tutorial and the
bounty board. Decisions marked **(default)** are ours, to change if the user disagrees.

## Decisions

| Topic | Decision |
|---|---|
| Which games | All five: memory, cups, invaders, runner, higher_lower. Chosen at random in the infinite challenge; picked by the player in world mode. |
| Difficulty | Normal everywhere, except the tutorial (easy). |
| Scores | Each game's own result: win, lose or draw, and both sides' scores. The CPU's target is its score (see the games). |
| Migrations | None. Everything lives in JSON (the path, the rewards, flags, the quest state). Ask World Planner before adding a field. |
| Dialogue | Each CPU gets its own lines for the world game (invite, start, win, lose, and a line for a second win in a day). Written by Tucker, as the user asked. Danny writes the tutorial guide's lines. |

## 1. Infinite challenge: the minigame space (solo)

- **New path node:** `MINIGAME`, like the existing `EVENT` node (weiss/challenge.py). It can appear on a floor the way an
  event does. Landing on it starts one random game (`random.choice` of the five), against the CPU of that column.
- **Stake:** a win gives a **lucky pack** (buff `lucky_pack`, source "minigame") into `run.rewards`. A loss gives
  nothing. A draw gives nothing. **(default)**
- **Where it's played:** the minigame page, with the run's id, so the result can be posted back. The result is saved
  into `path["minigame"]` and the node is cleared when it's posted. Repeats of the same game in a run are fine.
- **Tests:** a minigame node appears in the path; posting a win gives the lucky pack once; a loss gives nothing; the
  node can't be played twice.

## 2. Co-op: the minigame between the players

- **In a co-op challenge, the minigame space is player against player**, not against a CPU. **(default)**
- **Same game, same seed:** both players play the same game, dealt from the same seed (the path node's id), with the
  same cards. Each plays on their own, at their own time, and posts their score. This is asynchronous: no live link.
- **Winner:** the higher score wins. A tie is a draw: each gets a lucky pack. The winner picks **one of three
  specialty packs** (`challenge.LOADOUT_BUFFS`-style choice, reusing the curse/augment pick screen). The loser gets a
  lucky pack. **(default)**
- **Waiting:** the node waits until both have posted. Each player sees "Waiting for your partner" until then. The
  partner's score is hidden until both have posted.
- **State:** `path["minigame"]` on the shared CoopRun: `{"game", "seed", "scores": {user id: score}, "winner"}`.
  No new model; no migration.
- **Tests:** both players post; the higher score wins; a tie gives two lucky packs; the winner's pick is one of the
  three; a partner who never posts holds the node (as the vs battles do: no timeout).

## 3. World mode: play a game with a CPU

- **Who:** any CPU at least at the acquaintance rank (the first rank above a stranger). Not for villains who are cold to
  the player (`quests.estranged`).
- **Once a day, per CPU**, the same as the first talk of the day.
- **Points:** talk gives its base points (`WorldSettings.talk_points`). A game gives **2× the base** on a play and
  **3× on a win**.
- **Win reward:** a **lucky pack from the CPU's own deck set** (the set the CPU's deck is from). Put in the save's
  rewards so it can be opened from the town like any pack.
- **Time:** playing spends the time of day, like a duel. **(default)**
- **The game:** the player chooses one of the five games. The CPU plays normal difficulty.
- **Dialogue:** every CPU has its own lines: an invite, the start, a win, a loss, and a line for a second game in the
  same day. Written by Tucker; any CPU without its own lines falls back to the generic lines in `minigame_lines`.
- **Tests:** not before acquaintance; once a day per CPU; the points (2× and 3×); the pack from the CPU's set; time
  spent; the lines.

## 4. Bounty board: minigame objectives

- New objective kinds for quests, in `weiss/quests.py`:
  - **win a minigame** (any game, or one named game), and
  - **play a minigame** a number of times,
  - optionally **against a named CPU**.
- They count from all three places above: the infinite minigame, the co-op minigame and the world minigame.
- **Tests:** each objective counts the right results and not the others.

Note on the two conventions: the world game's "win" and "lose" lines are the CPU's (the CPU won, the CPU lost). The
tutorial's "minigame_win" and "minigame_lose" lines are the player's (minigame_win is the player winning, and the guide
says "good game"; minigame_lose is the player losing or drawing, and the guide says "I won that one"). The code's
minigame_done does this mapping.

## 5. Tutorial: a minigame before the duel

- A new step, `minigame`, between `deck` and `duel` (weiss/world_tutorial.py `STEPS`).
- The guide challenges the player: the player is the one who asks to play, as they do for the guide. The guide plays
  easy. **Either result** completes the step.
- While the step is on, only the minigame is open: the tutorial doesn't go on to the duel until it's done.
- The player isn't told how to play the game. The guide's line sets it up, the game's own start screen does the rest.
- Tests: the step blocks the duel; a win and a loss both finish it; the game's result is recorded.

## Who does what

- **Tucker JR:** the server for all of the above: the infinite minigame node, the co-op match state, the world minigame
  endpoints and rewards, the CPUs' dialogue, the bounty objectives, and the tutorial step. In that order. Tucker reports
  file by file.
- **Sam Front End:** the UI for the infinite minigame node on the path, the co-op waiting and pick screens, the world
  "Play a game" option in the talk menu, and the bounty objectives' text on the board.
- **Sam 2 Front End:** the game frame for these uses: a seed option (`MinigameShell.start(..., {seed})`), an end
  callback (`onEnd(result, scores)`), and each game using the seed for its deal. The frame's score and result are the
  same as now.
- **Danny Writer:** the tutorial guide's lines for the minigame step, and the lines for the world game's invite and
  results that are generic (not per CPU).
- **World Planner (me):** the contract, the review, and any migration (none planned).
