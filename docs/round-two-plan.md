# Round two plan

Six changes, then a seventh. Owner: Bruce (lead). Front end: Diana. Server: Kal'el. Writing: Barry. This file is the
contract between them: if something here has to change, ask Bruce first.

| # | Change | Who |
|---|---|---|
| 1 | **Duel recap**: a damage chart and up to three standout moments, after every duel and on the profile | Kal'el, Diana, Barry |
| 2 | **CPUs remember you**: the pre-duel line can come from your history against that CPU | Kal'el, Barry |
| 4 | **The people journal** in world mode: everyone you've met, what you know about them | Kal'el, Diana, Barry |
| 5 | **A light theme** for the site's pages, with a toggle (the site is dark today) | Diana |
| 6 | **Installable app**: manifest, icons, service worker, offline page | Bruce |
| 9 | **Browser checks** kept in `e2e/`, repeatable, with screenshots | Bruce |
| 8 | *After the rest:* split `play.js` into smaller files, with no change in behaviour | Diana, with Bruce reviewing |

Done by Bruce already: migration `0068_round_two`. It adds `GameRecord.recap` (JSON, default `{}`) and these Chatter
contexts: `history_milestone`, `history_streak_won`, `history_streak_lost`, `history_revenge`, `history_rematch_won` and
`journal`.

Shared rules:
- Every state is handled: no data, one item, very many, very long names, a deleted CPU, a CPU with no art.
- Works at 390px wide and at desktop widths, in the town's play layer (iframe) and in full screen.
- Keyboard and screen readers: real buttons, visible focus, text alternatives for charts.
- Checks before reporting: `python manage.py test weiss` (the whole suite: these changes touch shared code), and for
  `world_pack/` changes, `python world_pack/build.py` and `python manage.py check_world_pack world_pack/*.json`.

---

## 1. Duel recap

### Data (Kal'el: `weiss/game.py`, `weiss/play.py`, `weiss/profiles.py`)
- **During the game**, at the end of each turn (and once more when the game ends), `game.py` appends to
  `state["timeline"]` the turn number and each player's *points*. A player's points are level × 7 + cards in clock,
  so 0 to 28.
- **The same code notes the raw facts for moments** in `state["timeline_facts"]`:
  - each attack's damage, whether it was cancelled, and the turn and side;
  - each climax played.
  Keep it small: under 2 KB for a 30-turn game.
- **At game end**, `game.recap(state)` turns those into:
  ```
  {"points": [[turn, host_points, guest_points], ...],
   "moments": [{"kind": str, "turn": int, "side": "host" | "guest", "n": int}, ...]}   # at most 3, best first
  ```
  `record_game` stores it in `GameRecord.recap`.
- **Moment kinds**, in priority order. Each needs its threshold to count:

  | kind | meaning | threshold |
  |---|---|---|
  | `comeback` | the winner was 7 or more points behind at the end of some turn | 7 behind |
  | `close_finish` | both players were at level 3 at the end | |
  | `flawless` | the winner finished at level 0 or 1 | |
  | `big_hit` | the biggest single attack's damage that wasn't cancelled | `n` ≥ 3 |
  | `big_cancel` | the biggest attack cancelled | `n` ≥ 3 |
  | `burst_turn` | the most damage dealt in one turn | `n` ≥ 6 |

  Take each kind at most once. Leave a kind out when it's below its threshold.
- **`play.recap_view(recap, seat, names)`** gives the view from one player's seat:
  ```
  {"me": name, "them": name, "points": [[turn, mine, theirs], ...], "moments": [str, ...]}
  ```
  - The moments are Barry's captions with the fills done: `{turn}`, `{n}`, `{name}` (the other player's name),
    `{player}`.
  - Captions come from `weiss/recap_lines.py`'s `RECAP_LINES[kind]["you" | "them"]`. "you" means the viewing player
    did it.
  - It returns `None` when `points` is empty (old records, or games that ended before turn 1).
- **The game-over payload** (both players, PvP too) carries `game_over["recap"]` for that player: the view from their
  seat.
- **On the profile**, each recent game row gets its `recap` view.

### Front end (Diana: `play_summary.js`, `play.js`, `profile.html`, `recap.js`, `site.css`)
**Changed during the work:** the game-over screen already had a damage graph, play_summary.js's "How the game went"
panel, which the first plan missed. So there is one chart, not two:
- **On the game-over screen:** the moments go at the top of that panel. In the world ceremony, its button appears once
  the ceremony is done.
- **On the profile:** `WeissSummary.recapHtml(view)` draws the same graph from a record's recap, with its moments and
  no stat tiles. `recap.js` only wires the profile's Recap disclosure.
- **Names:** the server's duel recap functions are `game.duel_recap` and `play.duel_recap_view`. `game.recap_view` and
  `play_recap.js` are the older recap of the opponent's turn, a different thing.

### Copy (Barry: `weiss/recap_lines.py` (new))
- `RECAP_LINES = {kind: {"you": str, "them": str}}` for the six kinds above.
- One line each, at most 60 characters, in the game's voice.
- Examples:
  - `big_hit` "you": "Turn {turn}: you landed a {n}-damage hit."
  - `comeback` "them": "{name} clawed back from 7 points down."

---

## 2. CPUs remember you

### Which line (Kal'el: `weiss/play.py`, `weiss/world.py`, `weiss/chatter.py`)
The intro line before a CPU duel is picked once, when the duel starts, as now. The new order is:
1. A tournament round's line (town duels; as now).
2. **A history line**, when one applies and the CPU has a line for it.
3. The usual line: `before_duel` in town, or `intro_text` elsewhere.

**History** is the `GameRecord`s with this user and this CPU profile (`cpu=True`), newest first, before this game. Count
across all modes. The first rule that matches wins:

| context | when | always? | fills |
|---|---|---|---|
| `history_milestone` | this is the 10th, 25th, 50th or 100th duel with this CPU | yes | `{count}` |
| `history_streak_won` | the player won the last 3 or more | yes | `{count}`: the streak |
| `history_streak_lost` | the player lost the last 3 or more | yes | `{count}`: the streak |
| `history_revenge` | the player lost the last one | 50% | |
| `history_rematch_won` | the player won the last one | 50% | |

Some exceptions and rules:
- **Narrative challenges are left out**: their scenes speak for the CPU.
- **The coin flip:** when a 50% rule's flip fails, stop checking and use the usual line.
- **Fills:** `{player}`, `{name}` and `{rank}` are filled as usual.
- **Tiers and ranks:** lines come through the same tiers as reactions (the CPU's own, then any CPU's, then the
  defaults), at the player's rank in town and rank 0 elsewhere.
- **Cost:** one indexed query (`[:100]`, values only). Never per poll.
- **Pack data:** `world_pack/build.py` exports `lines["history"]` (`{"milestone": [...], "streak_won": [...], ...}`)
  as these contexts at `min_rank` 0. The pack checker accepts it.

### Copy (Barry: `weiss/duel_lines.py`, `world_pack/src/0*.py`)
- **Defaults first:** 4 lines for each of the five contexts, appended to `DUEL_DEFAULTS`. They work for any CPU.
- **Then per CPU:** `lines["history"]` for each of the 75 CPUs, 1 or 2 lines per context, in their voice. Use
  `{count}` where it fits.
- **Length:** 90 characters at most (the versus intro's speech bubble).

---

## 4. The people journal (world mode)

### Data (Kal'el: `weiss/world_people.py` (new), `weiss/world.py`, `weiss/world_views.py`, `weiss/urls.py`)
- **Page:** `world/<slot>/people/` (`weiss:world_people`). The same page with `?cpu=<id>` opens that person's entry.
  Frame the view `sameorigin`, like `world_quests`.
- **Who:** everyone in the world's cast.
  - **Met:** the save has a relation with them.
  - **Not met:** listed after, as locked entries with no name. Count them: "23 of 75 met".
- **Each met person:**
  ```
  {"id", "name", "avatar", "image", "colors",            # colors as in versus (for the crest when there's no art)
   "rank": int, "rank_name", "next_rank_name" or None, "progress": 0..1 toward the next rank,
   "record": {"won": int, "lost": int},                   # town duels in this save
   "tastes": {"loved": [gift names], "liked": [...], "disliked": [...]},  # only gifts the player has given them
   "quests": [{"title", "status": "active" | "done" | "failed"}],         # quests they give
   "entries": [{"text", "unlocked": bool, "rank_name"}]}   # their journal lines; a locked one has text ""
  ```
- **Recorded from now on**, in the save's relation:
  - `rel["won"]` and `rel["lost"]`, in `game_finished`;
  - `rel["tastes"][gift key]`, set to the reaction, in `give`.
  - Old saves start empty; that's fine.
- **Journal lines:** the `journal` chatter context, its first line only, every script at its `min_rank`, in order of
  `min_rank`. A CPU with none has `entries: []`.
- **Pack data:** `world_pack/build.py` exports `lines["journal"]` (`{"0": text, "2": text, "4": text, "5": text}`, keyed
  by min_rank).

### Front end (Diana: `weiss/templates/weiss/world_people.html` (new), the town's link to it, `site.css`)
- **A grid of people:** portrait or crest, name, rank, and a thin progress bar. Unmet people are silhouettes marked "???".
- **Selecting one** shows their entry, beside the grid on desktop and as a full page on a phone:
  - a larger portrait;
  - rank, with progress and "Next: Good friend";
  - their record against you;
  - gifts they loved, liked and disliked, with "Give gifts to learn what they like" when empty;
  - their quests;
  - the journal entries. A locked entry reads "Reach {rank_name} to learn more".
- **From the town:** a "People" link next to the quest log, in the same style.

### Copy (Barry: `world_pack/src/0*.py`)
- `lines["journal"]` for each of the 75 CPUs: 4 entries at ranks 0, 2, 4 and 5, each 1 to 3 sentences.
- They're written as the player's notes about them, and get more personal at higher ranks.
- Rank 0 is what anyone in town would know.
- Barry also writes the page's empty states and the locked-entry wording.

---

## 5. A light theme (Diana: `core/static/core/site.css`, the base templates' theme script, a toggle)
- **What changes:** the colours, as variables on `:root`.
  - Today's dark set stays the default.
  - `:root[data-theme="light"]` gives the light set.
  - With no choice saved, the device setting (`prefers-color-scheme`) picks.
- **First, swap literal colours for variables** in the site's page styles. Leave alone the game screens that are
  meant to look a fixed way: the duel board, the town scene, minigames, card art and sleeves.
- **The toggle:** System, Light or Dark, in the site's header menu.
  - The choice is saved in `localStorage`, in a try/catch.
  - It is applied by a small inline script in `<head>`, before the first paint, so pages don't flash.
- **Contrast:** check it in both themes (WCAG AA for text).

## 6. Installable app (Bruce)
- **Files:**
  - `core/static/core/manifest.webmanifest` and icons at 192 and 512 px, plus a maskable one;
  - a service worker served at `/sw.js` (a view, so its scope is the whole site);
  - an offline page.
- **The service worker caches:**
  - static files, stale while revalidating;
  - pages and API requests: never cached (always the network), with the offline page as the fallback for a page
    request.

## 9. Browser checks (Bruce)
`python e2e/harness.py checks [name ...]`, in `e2e/checks/`, sets up the scratch database through `e2e/checks/db.py`.
Only one run goes at a time (a lock file), since runs share a port and the database.

| Check | What it covers |
|---|---|
| `app` | the manifest, the icons, the service worker taking control, and the offline page |
| `versus` | the intro in the town's play layer, skipping, focus on Begin, and the first-player banner, at desktop and phone widths |
| `reactions` | the CPU's reactions driven by a faked board: the limits, priority, and the game log |
| `ceremony` | the world results screen, its steps, focus, and coins, at desktop and phone widths |
| `board` | the main phase, hover actions, playing a card to the stage, More… and Escape, the preview, and chat |
| `board-phone` | the touch tray at 390px |
| `recap` | the moments in "How the game went" after the ceremony, and the profile's Recap disclosure |
| `people` | the journal's grid and entry at both widths, and opening it from the town |
| `theme` | WCAG AA text contrast on 8 pages in both themes, the toggle with no flash, and the duel staying dark |

## 8. Split play.js (after the rest)
- Move whole sections into their own files beside it (as `play_versus.js` and `play_ceremony.js` were):
  - reactions;
  - the game log;
  - prompts;
  - the hand;
  - sounds.
- No change in behaviour. `test_level_four`'s script checks pass, and the browser checks from 9 pass before and after.

## Order
- **Barry:** the history defaults first (Kal'el's tests need them), then the recap captions and the journal page's
  copy, then the per-CPU history and journal lines.
- **Kal'el:** recap data, then history lines, then journal data.
- **Diana:**
  - `recap.js` with stand-in data in this shape;
  - the journal page;
  - the light theme;
  - then 8, when Bruce says.
