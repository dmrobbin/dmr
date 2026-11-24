# Duel presentation plan

Three changes to how a duel against a CPU is presented. Owner: Bruce (lead). Front end: Diana. Server: Kal'el.
Writing: Barry. This file is the contract between them: if something here has to change, ask Bruce first.

1. **The versus intro**: an animated opening that replaces the static CPU screen (`renderIntro` in play.js), and runs
   into a livelier rock, paper, scissors.
2. **Reactions**: the CPU says short lines in a speech bubble at key moments of the duel.
3. **The results ceremony**: a world duel's Victory and Defeat screen plays out its rewards in turn, instead of one
   "+300 coins" line.

Shared rules for all three:
- **Skippable:** a click, tap, Enter, Space or Escape jumps an animation to its end state. Nothing makes the player
  wait to act.
- **Animations off:** when play.js's `animations` is false or reduced motion is set, show the end state with no
  movement. The words still show.
- **Works without art:** every CPU in the local database lacks portrait art. A CPU with no image or picture shows a
  crest: its initial on a disc in its deck colours. The design has to look finished like that.
- **Works in the town's play layer** (an iframe, and the `html.in-frame` class) and in full screen, at 390px wide and
  at desktop widths.
- **Loudness:** any new sound goes through play.js `SOUNDS`. Its momentary peak should be at most the damage cue's
  (about -15.5 dB K-weighted at the default volume). Bruce measures it.

---

## 1. The versus intro

### What the player sees (about 2.5 s from start to Begin)
1. **0 to 0.4 s, the split:** the screen darkens and a diagonal slash wipes across, dividing it into two panels.
   Your side is at the bottom left in your colours; theirs is at the top right in theirs.
2. **0.3 to 1.0 s, the arrivals:** each side's portrait (image, then picture, then crest) slides in from its own edge,
   with the name and deck name under it. Names use Cinzel and are large. The current `.cpu-intro-name` renders far
   smaller than its CSS says: find out why and fix it.
3. **1.0 s, the impact:** a "VS" emblem slams into the centre with a short flash, a small screen shake and the stinger
   sound.
4. **1.2 s, the ribbon:** what's at stake (`versus.ribbon.text`, or the arcade `fightLabel()`) unfurls under the VS.
   Leave it out when it is null.
5. **1.4 s on, the line and Begin:** their pre-duel line types out in a speech bubble, then the Begin button appears
   and takes focus. Begin sends `intro_done` as it does today.

**Leaving the intro:** after Begin, the panels slide apart to reveal the board.

**Game 1's rock, paper, scissors:** once both players have picked, show each hand shaking three times before the
reveal (about 0.9 s in total). Then a banner reads "You go first" or "{name} goes first" before the mulligan. Keep
`RPS_SHOW_MS` as the total.

### Data (Kal'el, in `play.cpu_payload`)
```
payload["versus"] = {
  "me":   {"name": str, "picture": avatar dict or null, "deck": str, "colors": ["Red", "Blue"]},   # up to 2, most cards first
  "them": {"name": str, "picture": avatar dict or null, "image": str ("" if none), "deck": str, "colors": [...],
           "title": str},          # world mode: the friendship rank's name ("Stranger", "Friend"…); "" elsewhere
  "ribbon": {"kind": "tournament" | "quest" | "stakes" | "story" | "friendly", "text": str} or null,   # world duels only
}
```
- `payload["cpu"]["intro"]` in a world duel is `world.duel_intro(save, cpu)`.
  - Pick it **once**, when the duel starts, and store it in `room.state`, so it doesn't change on each poll.
  - It gets `{player}` filled in.
- **Ribbon precedence:** tournament round, then quest duel, then high stakes ("High stakes · 500 coins"), then the
  story or tutorial duel. Otherwise "friendly", with text such as "A friendly duel" (null is also fine).
- Barry writes the ribbon wording: see Copy below.

---

## 2. Reactions

### Triggers (Diana, from board changes in play.js; "they" is the CPU)

| Context | When |
|---|---|
| `duel_hurt` | they take 3 or more damage from a single attack, and it isn't cancelled |
| `duel_cancel` | they cancel the player's damage |
| `duel_level` | they level up |
| `duel_brink` | they reach match point (`atBrink`) |
| `duel_winning` | the player reaches match point |

Limits:
- At most one reaction per turn, and at most 6 a game. Leave at least 15 s between them.
- `duel_brink` and `duel_winning` fire once a game each and take priority over the others.
- Never during the intro, the game-over screen, the combo cut-in, or a level-up or climax graphic. Wait for these to
  clear, and drop the reaction if it's more than 4 s late.
- Pick the line at random from that context's list, and don't repeat a line within a game.

**The bubble:**
- It sits next to the CPU's nameplate or avatar on their side of the board, with a small portrait or crest.
- The line's mood shows on it: `dismayed` and `pleased` tint the bubble differently.
- It stays about 3.5 s; a click dismisses it.
- The line also goes into the game log as "{name}: {text}", which the existing `aria-live` region reads out.
- It must never cover the player's hand or a prompt. On a phone, it sits over the opponent's back row.

### Data (Kal'el)
```
payload["cpu"]["reactions"] = {"duel_hurt": [{"mood": "main" | "pleased" | "dismayed", "text": str}, ...], ...}
```
- **Where the lines come from:**
  - Only the first line of each script, with `{player}`, `{name}` and `{rank}` filled in.
  - In a world duel, the lines fitting the player's rank: the CPU's own if it has any for that context, else the
    any-CPU lines, else the built-in defaults (as `chatter.pick` already falls back).
  - Outside world mode, the any-CPU lines and the defaults.
- **When it's empty:** it is `{}` in a narrative challenge (`challenge.narrative`), and for a deleted CPU.
- Worked out once per game (when it's dealt; a world duel's ribbon and title at `start_duel`) and kept in
  `room.state["presentation"]`, so the payload, which is rebuilt on every board change, only reads it.
- **Built-in defaults:** `weiss/duel_lines.py` (Barry's file) holds `DUEL_DEFAULTS`, a list of (context, min_rank,
  script) tuples. Merge it into `chatter.DEFAULTS`.
- **Chatter rules:** add the five contexts to `FIRST_LINE_ONLY`. The model choices and migration 0067 are already in
  (Bruce).
- **The world pack:** `world_pack/build.py` exports a cast file's `lines["duel"]` as chatter. Its shape is
  `{"hurt": [...], "cancel": [...], "level": [...], "brink": [...], "winning": [...]}`, each a list of one-line
  scripts, at `min_rank` 0. `check_world_pack` must accept them.

---

## 3. The results ceremony (world duels)

### What the player sees
The game-over screen's world part (`gameOverButtons` when `world` is set) plays out in steps, one after another,
about 0.6 s apart. Each step is skipped when it has nothing to show:
1. **Coins:** count up from 0 to `coins` over about 0.8 s, with a soft tick at the end. The day's first win and the
   stakes won show as tags under it. On a loss, the consolation payout shows the same way, and a lost stake shows as a
   muted line.
2. **Friendship:** `{name}`, a bar that fills from `friend.from` to `friend.to`, and `+{points}`. If the rank went up,
   the bar fills, flashes, and the new rank's name ("Friend!") replaces the old one, followed by `rank_line`.
3. **Quests:** each entry is a line with a check that ticks in, such as "Beat Aang: done" or "Win 3 duels: 2 / 3".
4. **The tournament:** the `event` words, for example "Through to the semi-final".
5. **Rewards:** anything in `rewards`, and that a card pick is waiting in the town.

Then "Back to the town" appears and takes focus. A click anywhere before that finishes all the steps at once. The
town's result banner afterwards stays as it is: it's the summary for those who skipped.

### Data (Kal'el: add to `flags["last_duel"]` in `world.game_finished`)
```
"friend": {"before": "Stranger", "after": "Acquaintance", "from": 0.4, "to": 1.0},    # from and to: the share of the way
                                                                                     # through the "before" rank (a rank up ends at 1.0)
"quests": [{"text": str, "done": bool}],   # what this duel moved on, in words; [] if nothing
"cpu_line": str,                            # the after_win / after_loss line (first line, filled); the game-over speech in world mode
```
- The keys already there (`coins`, `first`, `stake`, `points`, `rank_up`, `rank_line`, `rewards`, `event`) stay as
  they are.
- `quests.duel_finished` runs after `last_duel` is written: put the quest words in after it runs, inside the same
  transaction.

---

## Copy (Barry)
Barry writes these. Diana and Kal'el use them exactly; until they arrive, use a stand-in marked `TODO(copy)`.
- **Ribbon texts:**
  - a tournament round: "Tournament · Round {n}", plus the semi-final and final;
  - a quest duel: uses the quest's title;
  - high stakes: uses the fee;
  - the story or tutorial duel;
  - a friendly duel.
- **The first-player banner:** "You go first" and "{name} goes first", or better.
- **The ceremony's labels:**
  - the coins line;
  - the day's first win;
  - stakes won and lost;
  - the consolation on a loss;
  - the friendship rank-up flourish;
  - the card pick waiting;
  - and what Defeat says on its way back to the town.

## Who does what
| | Files |
|---|---|
| Bruce | this plan, `weiss/models.py` and migration 0067 (done), the sound check, review, end-to-end tests in a browser |
| Kal'el | `weiss/play.py`, `weiss/world.py`, `weiss/chatter.py`, `weiss/quests.py` (only if the quest words need it), `world_pack/build.py`, the pack checker, new `weiss/test_duel_presentation.py` |
| Diana | new `weiss/static/weiss/play_versus.js` (the intro and rock, paper, scissors) and `play_ceremony.js`, `play.js` (hooks, reactions and the stinger in `SOUNDS`), `play_room.html` (script tags), `core/static/core/site.css` |
| Barry | new `weiss/duel_lines.py`, `world_pack/src/0*.py` (the `duel` lines for all 75 CPUs), the Copy above (send it to Bruce, who passes it on) |

**Order:**
- Diana starts the intro at once, with stand-in data that has this shape.
- Kal'el does the payload first, then the reactions plumbing, then the ceremony data.
- Barry writes `duel_lines.py` first (Diana needs lines to test with), then the Copy, then the cast files.
- **Checks before reporting:**
  - `python manage.py test weiss.test_world* weiss.test_duel_presentation weiss.test_arcade weiss.test_cpu weiss.test_game`;
  - for `world_pack/` changes, `python world_pack/build.py` and `python manage.py check_world_pack world_pack/*.json`.
