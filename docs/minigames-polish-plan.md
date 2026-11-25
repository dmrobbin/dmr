# Minigames: the visual pass (plan)

The five minigames all work. This pass is about how they look and feel, so they match the rest of the game: the duel's
versus intro and results screen, and the town. Owner: Bruce. **Done 2026-11-24** (approved by the user the same day). Checked: `python e2e/harness.py checks` (all 10, `minigames` among them) and the whole test suite.

## Where they stand (screenshots taken 2026-11-24, real layout, a stand-in for card art)

| Game | Today | Verdict |
|---|---|---|
| **The frame** (`shell.js`, all five) | A small grey title, the score twice, the CPU's portrait, name and bubble stacked, then the game in a dashed box. It reads like a debug page. Memory's board doesn't fit a laptop screen. | Rebuild |
| **Three cups** | The cups are wide flat gold slabs in an empty black box: no table, no cup shape. While they shuffle, the prompt names the card ("Where's NEW FLAVOR?") but doesn't show it. | Redo the look |
| **Runner** | The player is a pale blue rectangle with a dot for a head, on a flat brown strip; obstacles are bare card rectangles. A small 480×240 canvas sits in a much larger box. | Redo the look |
| **Climax Invaders** | A plain triangle ship, flat card rectangles, red dot shots. The best of the canvas games, but bare. | Polish |
| **Memory** | 16 tiles too big for the screen, generic striped backs (not the player's sleeve), a plain flip. | Polish |
| **Higher or Lower** | Clean, but the card you're comparing against is only a line of small text, and a guess has no reveal moment. | Polish |

**A bug to fix first:** the light theme leaks into the minigames, as it did into the duel. The speech bubble and the
cups' card details turn dark on dark. They should be pinned to the dark set the same way (`.dashboard:has(.play)` in
`site.css`).

## Shared look (all five)

1. **A game table, not a page.**
   - One stage, sized to the space it's given (the page, the town's play layer, or full screen), with no scrolling
     mid-game: the board scales to fit the height.
   - Each game has its own backdrop (felt for the card games, sky for the runner, space for Invaders), framed like the
     duel board.
2. **One header bar:**
   - the game's name in Cinzel;
   - the round or wave as a pill;
   - **one** scoreboard: "You 2 — 1 Aang", with both pictures.
3. **The CPU in its corner:**
   - its portrait comes from the versus intro's code: its intro art whole, its picture, or its crest, and it changes
     with mood (pleased or dismayed);
   - its line appears in a speech bubble like the duel's reactions, not a full-width bar.
4. **A start card:** the title, a one-line rule, Start, and a 3-2-1 for the action games.
5. **A results screen:**
   - "Victory" or "Defeat" and the score counting up, in the same style as the duel's results ceremony;
   - the CPU's line;
   - Play again and Back.
6. **Shared effects:**
   - a particle burst, screen shake and floating "+10" score pops, in one small helper (`minigames/fx.js`);
   - sounds stay in `audio.js`;
   - all of it honours reduced motion.
7. **The player's card sleeve** on every face-down card: Memory's backs and the cards under the cups. The pages pass
   it in, as the duel does.

## Each game

- **Three cups:**
  - a felt table seen slightly from above;
  - real cups: tapered, with a rim highlight and a shadow (SVG);
  - the three cards are shown face up, the cups come down over them, then they **swap along arcs** (one passes over,
    the other under), not just slide;
  - the prompt shows the card you're looking for as a small picture;
  - picking lifts the cup and slides the card out, with a burst for a find and a shake for a miss.
- **Runner:**
  - the canvas fills the stage at 16:9;
  - three layers of backdrop scroll at different speeds (sky with a moon, hills, near trees or town);
  - the ground is drawn with texture, not a flat strip;
  - a **real runner sprite**, drawn in code: a run cycle, a jump pose and a slide pose, with the player's avatar as
    the head;
  - obstacles are cards on stands and banners to duck under;
  - coins spin;
  - a hit gives a flash and a shake;
  - the display shows hearts for hits left, the distance, and a bar towards the CPU's target.
- **Climax Invaders:**
  - a drawn ship with an engine flame;
  - enemy cards framed, tilting, and glowing in their level's colour;
  - bosses are larger, with a health bar;
  - shots are glowing beams;
  - a card destroyed **shatters** into pieces;
  - the starfield has a slow nebula;
  - a "WAVE 2" banner, and clear icons for power-ups.
- **Memory:**
  - the board sized to the screen (4×4 at any size);
  - sleeve backs, and a 3D flip;
  - a matched pair glows and slides to its owner's pile, with pair counts beside each player;
  - on the CPU's turn, a "thinking" highlight on the tile it's about to pick;
  - a mismatch gives a small shake.
- **Higher or Lower:**
  - the last card on the left, smaller and dimmed, and the new card **flipping in** on the right, both with big power
    numbers;
  - a guess is stamped ✓ or ✗ with a streak counter;
  - whose turn it is is clear;
  - the buttons get arrows.

## The contract between the frame and the games

The frame (Diana) and the games (Diana and Bruce) are built at the same time, so the frame keeps to this:

- **The data:** `game_data` (Kal'el) adds `player: {name, picture: avatar dict or null, sleeve: CSS background or ""}`
  and `cpu.image` (its intro art URL, as in the versus intro, or ""). It's the same in the staff page, the town and the
  infinite challenge.
- **`ctx` gains, and keeps everything it has:**
  - `ctx.player`: as above.
  - `ctx.fx`: `{burst(x, y, options), shake(el), pop(x, y, text)}` for DOM games, in page coordinates. Canvas games
    draw their own effects.
  - `ctx.countdown()`: shows 3-2-1 over the stage and resolves when it's done. It's instant with reduced motion.
- **The start card is the frame's.** A game's registration gains `rule: "one line"`. The frame shows the title, the
  rule and Start, and only then calls `play(ctx)`. A game that has its own start button today (cups) drops it.
- **The stage:** `ctx.area` is a box of a definite size that fits the space without scrolling. The frame keeps it
  sized, and a game reads its size and listens for `resize` events on `ctx.area` (the frame dispatches them). Canvas
  games draw at 16:9, letterboxed, and fill it.
- **The sleeve:** the frame sets `--sleeve-me` on the stage from `ctx.player.sleeve` (the default sleeve when it's
  ""), and face-down cards use `var(--sleeve-me)`.
- **Themes:** the stage is pinned to the dark tokens in either theme.

## Who and in what order

| Step | What | Who |
|---|---|---|
| 0 | The light-theme leak; the sleeve passed in to the minigame pages | Diana; Kal'el (sleeve data) |
| 1 | The shared frame: stage, header, CPU corner, start card, results, `fx.js` | Diana |
| 2 | Three cups and the runner (the two worst) | Diana: cups. Bruce: the runner (the most art direction) |
| 3 | Climax Invaders | Bruce |
| 4 | Memory and Higher or Lower | Diana |
| — | Start-card rules, display labels, any new CPU lines for new moments | Barry |
| — | A browser check, `minigames`: each game started, played briefly and finished, at 1280 and 390, inside the town's play layer, in both themes; it fails on scrolling mid-game, overflow or low contrast | Bruce |

**Rules:**
- **No change to how the games play:** rules, scoring, CPU behaviour and difficulty stay as they are.
- **Same `ctx` contract** (`docs/minigames-plan.md`), so the town and the infinite challenge need no changes.
- **Size:** keep each script lean, with no image assets to download (sprites are drawn in code or SVG). Keep 60fps on
  a phone.
- **Accessibility:** keyboard and touch still work, focus stays visible, and reduced motion still shortens everything.

**Can't be checked here:** real card art. The local browser can't load it from the card publisher's site, so checks use
a stand-in picture. The user looks over the final pass with real art.
