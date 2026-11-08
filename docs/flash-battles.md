# Infinite challenge: flash battles

Some fights on the infinite challenge's path are flash battles: both players start at level 2, with stock, so the
game skips the slow start and goes straight to the big plays.

## Decisions

| Topic | Decision |
|---|---|
| Where | Any fight on the path can be one, never a boss's. Each CPU space on a newly laid floor has a chance of being one, set by staff on the CPU tab's Infinite form (default 15%). The path marks them "Flash". Solo and co-op alike. |
| The start | Before the mulligan, each player searches their deck for 2 cards for their level zone. The hand they were dealt goes back into the deck first; once they've chosen, the deck is shuffled and they draw it again. Then the mulligan, as usual. |
| Stock | Once both players have mulliganed, the top 3 cards of each deck go to the stock, and the first turn begins. |
| Clock | Empty: both players are 7 damage from level 3. |
| The CPU | Takes level 0 cards in the colors of its deck's two anchors, one for each (two of one color if both anchors are), so it can pay their colors. A climax only if it's the last level 0 card of that color. With no anchors (a deck not built by express), or no level 0 card in an anchor's color, it takes its highest-level cards instead, of the color its deck has most of. |
| Reward | A win's usual reward. |
| Augments and curses | Still apply on top: Deep Reserves and Hoard add to the 3 stock, Old Wounds still fills the clock, and Short Hand's smaller hand is the one drawn again. |

## How it's built

- **Settings:** `ChallengeSettings.flash_percent`.
- **The path** keeps its flash battles in `path["flash"]`, a list of `[floor, column]`, rolled when a floor is laid
  (`challenge.path_of`), and dropped for floors laid again. `challenge.flash_now(run)` says whether the space picked
  on the player's floor is one.
- **The game:** `play.deal` calls `game.flash_start` last, after the floor, augments and curses. `state["flash"] =
  {"picked": [player id]}` holds who has chosen. The `flash_level` action takes the 2 cards (`game.flash_due` says
  who still must), and the mulligan waits on it. The last mulligan puts `FLASH_STOCK` cards in each stock. The
  board view's `flash` gives the player their deck to choose from, and the game page shows it as a picker before
  the mulligan.
- **The CPU:** `play.deal` puts the colors of its deck's anchors on its side (`side["anchor_colors"]`, see
  `play.anchor_colors`), and `Mind.flash_level` picks from them.
