# Minigames: prototypes (plan and contract)

Four small games that link back to Weiss Schwarz, each played against a CPU who talks during the match. They're
prototypes to try out, on one staff page. Later, they'll become playable events in world mode, and a minigame room
type in the infinite challenge (see "Later" at the end). Nothing here touches a save yet: no rewards and no
migrations.

This doc is the contract between the server (Tucker), the shared frame and two games (Sam), the other two games
(Sam 2), and the dialogue (Danny).

## The games

| Key | Game | How it plays | Against the CPU |
|---|---|---|---|
| `memory` | **Memory** | 16 face-down cards (8 pairs of real cards). Flip two; a match keeps them and your turn. | Turns alternate. The CPU remembers cards it has seen, imperfectly (by difficulty). Most pairs wins. |
| `cups` | **Three cups** | Three real cards are shown, then covered by cups and shuffled. "Where's [card name]?" Pick a cup. | The CPU is the dealer: it shuffles faster each round and taunts. 5 rounds; find 3 or more to win. |
| `invaders` | **Climax Invaders** (Galaga-like) | A ship at the bottom shoots up at a formation of card "ships". Level 0 cards are simple and slow; level 1 take 2 hits; level 2 swoop down; level 3 are bosses that shoot back. A shot-down climax card drops a power-up (soul: a double shot for a while; draw: an extra life; and so on). 3 waves, 3 lives. | The CPU sets a target score (by difficulty). Beat it to win. The CPU comments on waves, hits and lives lost. |
| `higher_lower` | **Higher or Lower** | A card is shown, with its power. Guess whether the next card's power is higher or lower (equal counts as right). | Turns alternate. A right guess scores and keeps the turn; a wrong one passes it. First to 5. The CPU guesses sensibly, by difficulty. |

**Difficulty** (easy, normal, hard) is chosen on the page. It sets the CPU's memory in Memory, the shuffle speed in
cups, the target score and enemy speed in Invaders, and how sensibly the CPU guesses in Higher or Lower.

## The page and the server (Tucker)

- **A staff-only page:** `world/minigames/` (name `world_minigames`), linked from the World mode tab. Its template is
  `weiss/templates/weiss/minigames.html`.
  - **Choosing:** a game, a CPU opponent (any finalized CPU) and a difficulty. Then a stage area where the game plays.
  - **Scripts:** `weiss/static/weiss/minigames/shell.js` and each game's `<key>.js`. Then
    `MinigameShell.start(...)`.
- **The data:** `GET world/minigames/data/?game=<key>&cpu=<id>&difficulty=<…>` (name `world_minigame_data`) returns
  JSON:

```
{
  "game": "memory",
  "difficulty": "normal",
  "cpu": {"id": 12, "name": "Aang", "portraits": {...as world.cpu_portraits...}, "avatar": url or null},
  "cards": [ {"id", "name", "image", "level", "power", "cost", "color", "type", "trigger", "rarity"} ],
  "lines": {"start": [...], "player_good": [...], "player_bad": [...], "cpu_good": [...], "cpu_bad": [...],
            "player_ahead": [...], "cpu_ahead": [...], "win": [...], "lose": [...]}
}
```

- **The cards:** about 40 real cards with pictures (an `image_url` or an S3 key), drawn from one set. The CPU's own
  deck's set if it has one, else a random set with enough pictured cards. Include characters at every level (0 to 3)
  and some climaxes, since Invaders needs them. `image` is `reverse("weiss:card_image", args=[pk])`.
- **The lines:** for the CPU and that game, merged in this order:
  1. the CPU's own lines for the game;
  2. the CPU's own lines for any game;
  3. the `"*"` lines for the game;
  4. the `"*"` lines for any game.

  For each moment, the first of those that has lines wins. `{player}` is filled in with the player's name. They're read
  from `world_pack/minigame_lines.json`, which `world_pack/build.py` builds from Danny's
  `world_pack/src/minigame_lines.py`. For a prototype, no database model: the JSON is read from disk (cached).
- **Tests** (`weiss/test_minigames.py`):
  - the page renders for staff and is refused for non-staff;
  - the data endpoint returns cards with every field, the right lines with the fallbacks, and an error for an unknown
    game or CPU;
  - a set with too few pictured cards still works (it falls back to another set).

## The frame (Sam)

`weiss/static/weiss/minigames/shell.js` defines `window.MinigameShell` and a registry, `window.MinigameGames`.

- **`MinigameShell.start(root, data, options)`** builds:
  - **the CPU panel:** their portrait (the `pleased` picture when they're ahead, `dismayed` when they're behind) and
    a speech bubble;
  - **the scoreboard:** "You 3 · Aang 2", and the round or wave;
  - **the game area;**
  - **an end screen:** win, lose or draw, the score, the CPU's line, "Play again" and "Choose another game".

  Then it calls the game's `play(ctx)`.
- **`ctx`, what a game gets:**
  - `area`: the game's element;
  - `cards`, `cpu` and `difficulty`;
  - `say(moment)`: a random line for that moment, shown in the bubble, not repeating the last;
  - `score(player, cpu)`: updates the scoreboard, and has the CPU say `player_ahead` or `cpu_ahead` when the lead
    changes;
  - `status(text)`: the round or wave label;
  - `end(result)`: `result` is "win", "lose" or "draw". It shows the end screen, says `win` or `lose`, and stops the
    game;
  - `random`: a seeded random, so a game can be replayed in tests.
- **A game registers itself:** `MinigameGames.memory = { title, about, play(ctx) }`, returning `{ stop() }`.
- **Accessibility and comfort:**
  - every game is playable by keyboard (with focus kept visible) and by touch;
  - the speech bubble is an `aria-live` region;
  - reduced motion shortens the animations;
  - the layout works at 390px.
- **Sounds:** reuse Sam 2's `world_audio.js` click sounds if they're easy to call; optional.

**Sam also builds `memory.js` and `cups.js`.**

## Two games (Sam 2)

**`invaders.js` and `higher_lower.js`**, registered in `MinigameGames` against Sam's frame. Until Sam's `shell.js`
is in, build against a small stub of `ctx`.

- **Invaders** is a canvas game.
  - **Controls:** arrows or A/D to move, Space to shoot, P to pause. On touch, buttons for left, right and fire.
  - **Enemies:** the cards' pictures, cropped to their art, drawn as the enemies. Level sets their behaviour (above).
  - **The CPU:** says `cpu_good` when you lose a life, `player_good` on a wave cleared, and `cpu_ahead` or
    `player_ahead` as you pass its target.
  - **Rendering:** keep to 60fps with requestAnimationFrame, and pause when the tab is hidden.
- **Higher or Lower:** a big card in the middle, with its power shown; two buttons, Higher and Lower (keys H and L).
  The CPU's turns play out with a short pause and a line.

## The dialogue (Danny)

In `world_pack/src/minigame_lines.py`:

```
MINIGAME_LINES = {
  "*": {"*": {moment: [lines]}, "memory": {...}, "cups": {...}, "invaders": {...}, "higher_lower": {...}},
  "Aang": {"*": {moment: [lines]}, "cups": {...}, ...},
  ...
}
```

- **Moments:** `start`, `player_good`, `player_bad`, `cpu_good`, `cpu_bad`, `player_ahead`, `cpu_ahead`, `win`
  (the CPU won) and `lose` (the CPU lost).
- **Lines:** plain text, said by the CPU, in their voice. `{player}` is the player's name. One sentence each; short
  enough for a speech bubble.
- **For every one of the 75 CPUs:** at least one line for each moment, under `"*"` (any game).
  - **Game-specific lines** where the character would say something particular. For example, a cups taunt from a
    trickster, or Invaders lines from a pilot or a fighter.
- **For `"*"`:** the generic voice, with 3 or more lines per moment, and per-game lines for each game.

## Later: from prototype to the game

- **World mode:** a minigame becomes a challenge a CPU can offer (a talk option, or an event such as a fair day at
  the plaza). Win or lose spends the time of day, like a duel. A win gives friendship points and a small reward.
- **Infinite challenge:** a "minigame" room type. Win to pass the floor, with a reward like the other rooms.
- **The lines move into the database** (the Chatter model or their own) once the games stay.

## Round 2 changes (from the user's notes)

- **Three cups (Sam):** before the shuffle, show each of the three cards in full (picture, name, and its
  characteristics as in the card view). The player reads them, then presses **Start** to begin shuffling. The question
  ("Where's [card name]?") shows only after the shuffle, so the player can't miss which card it is.
- **Climax Invaders (Sam 2):** shooting is automatic. The ship fires on its own while the player moves (arrows or A/D,
  and touch left/right). Space and the fire button are removed. Power-ups still apply: a double shot is just a faster
  or wider automatic fire.
- **Memory and Higher or Lower:** kept as they are.
- **New game, `runner` (Sam 2):** an auto-runner platformer in the spirit of Temple Run. The character runs on its own.
  - **Controls:** Space or Up to jump, Down to slide. On touch, a jump button and a slide button.
  - **Play:** obstacles and gaps come from the right. Each card is a pickup or an obstacle: the level-0 cards are coins
    (points), level 1 and up are obstacles to jump or slide under, and climaxes are power-ups (a shield for one hit).
  - **Win/lose:** the CPU sets a target distance or score (by difficulty), as in Invaders. Three hits and it's over.
  - **Lines:** `start`, `player_good` (a coin), `player_bad` (a hit), `cpu_ahead` / `player_ahead` as the target nears.
  - It registers as `MinigameGames.runner`, and goes in the `GAMES` dict in `weiss/minigame_views.py` (Tucker adds it).
- **Five games:** the page now lists Memory, Three cups, Climax Invaders, Higher or Lower, and Runner.

## Round 3: sound and music

- **One audio module:** `weiss/static/weiss/minigames/audio.js` (Sam 2) defines `window.MinigameAudio`. It makes music and
  effects with Web Audio, the same approach as `world_audio.js`, with no new audio files. It must unlock on the first
  user gesture, and stop when the tab is hidden or the game ends.
- **Music (BGM):** one loop per game, each with its own tempo and mood: memory (calm), cups (playful, a bit tense),
  invaders (driving), runner (fast and bouncy), higher_lower (light and quick). The shell starts the loop when a game
  starts and stops it when the end screen shows. The end screen plays a short win or lose jingle.
- **Effects (SFX):** `ctx.sfx(name)` in the shell (Sam), which calls `MinigameAudio.sfx(name)`. Names: `flip`,
  `match`, `miss`, `cup`, `reveal`, `shuffle`, `correct`, `wrong`, `shoot`, `hit`, `pickup`, `shield`, `jump`, `slide`,
  `wave`, `win`, `lose`. Each game calls the ones that fit its events.
- **Mute:** one Sound on/off button on the minigame page, remembered in localStorage (per viewer). Off means no music
  or effects. Respect the user's world-mode sound setting if it's easy to read; otherwise keep the page setting.
- **Accessibility:** the button has a visible label and state (`aria-pressed`). Effects are short and never the only
  signal of a result, since the text and speech bubble carry it too.
- **Tests:** headless Edge runs with `--mute-audio` (as with all headless browsers here). Check that each game starts
  and stops its loop and that mute silences it.
