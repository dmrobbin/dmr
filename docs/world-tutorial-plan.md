# World mode: the tutorial (plan and contract)

The first time a player reaches the town, a guide walks them through world mode, step by step: dialogue in the talk
box, the thing to press highlighted, and nothing moving on until they've done it. It can't be skipped. Normal play
opens up after the first duel with the guide. The player is assumed to know Weiss Schwarz, but nothing about world
mode.

This doc is the contract between the server (World Planner), the town page (Sam), the other pages (Sam 2) and the
writing (Danny).

## The steps

The server keeps the step on the save (`save.flags["tutorial"]`, a new save only) and moves on when the player has
done what it asks. Each step's lines (the guide's dialogue) play first, in the talk box. Then the thing to press is
highlighted until it's done.

| Step | The guide talks about | Highlight (`data-tutorial`) | Done when |
|---|---|---|---|
| `arrive` | (No guide yet: narration.) The player's arrived somewhere unfamiliar; a few people are around. | `person`: the candidates standing in the plaza | The player clicks one (the town posts `approach`): they become the guide |
| `approach` | The player asks the guide where they are. The guide realises they're new, offers to show them around ("it's like this for everyone when they first get here"), and gives a non-answer to "where is here?" | — | Its lines are played |
| `talk` | Making friends: talk to people every day, friendship ranks, what friends do for you | `talk`: the talk menu's Talk option | The player talks to the guide |
| `gift` | Gifts: the guide hands over a gift (one they love), and explains loved, liked and disliked | `gift`: Give a gift, then the gift | The player gives the guide a gift |
| `map` | Places, the map, people being out at different places and times; "let's go to the card shop" | `map`, then `place-shop` | The player travels to the card shop (only there is allowed) |
| `shop` | The card shop: packs, specialty packs, single cards, gifts, the basket; "buy a pack" | `shop`, then `add-pack`, then `checkout` | The player checks out with at least one pack (they're topped up to afford one) |
| `quests` | Quests: the "!" over someone with a quest, the quest log, the notice board's weekly notices | `quests`: the Quests button | The player opens the quest log page |
| `time` | Time: four times of day, talking or duelling spends the time, then passing it; the map afterwards | `wait`: Pass time | Time passes |
| `deck` | Decks: built only from cards they've opened, several decks, the equipped one duels; "make it legal: 50 cards, 8 climaxes" | `decks`: the decks button | The equipped deck is legal (checked when its lines are played and on every visit to the town) |
| `duel` | "Let's see what you've got. I'll go easy on you." | `duel`: the talk menu's Duel option | The duel with the guide is over, win or lose. It's on Easy. |

After the duel the tutorial ends. Normal play opens, the story's "After the lesson" scene plays with its coins, and
Chapter 1 carries on.

### While it's on (enforced by the server, not just the page)

- **Who's in town:** in `arrive`, only the candidate guides, at the plaza. From then on only the guide, who's always
  wherever the player is.
- **Refused unless it's the step's own action:**
  - travel, except to the shop in `map` and the map after time passes in `time`;
  - passing time;
  - duels, except the guide in `duel`;
  - talking to or giving to anyone but the guide;
  - shopping (until `shop`);
  - quests (taking or finishing), the notice board's quests, and the tournament.

  A refusal says what the guide's waiting for.
- **Staff only:** in test mode, a "Skip the tutorial" control.

## The server's side (World Planner)

`town()` gains `"tutorial"`: `null` once it's over, or:

```
{
  "step": "map",
  "title": "Go to the card shop",        // the current goal, short: for a goal banner
  "hint": "Open the map and choose the card shop.",
  "highlight": ["map", "place-shop"],     // in order: highlight the first that's on screen
  "lines": [ {"who": "them" | "player" | "narrator", "say": "…", "mood": "pleased" | …}, … ],  // to play now; [] once played
  "guide": {"id": 12, "name": "Aang"} | null,
  "candidates": [ids]                     // in "arrive": who can be approached
}
```

A town move, `POST world/<slot>/town/tutorial/` (`data-tutorial-url`), with `act`:
- `said`: the lines have been played. The server marks them said, and moves on if the step's already done (for
  example a deck that's already legal).
- `approach` (with `cpu`): in `arrive`, this candidate becomes the guide. The answer's tutorial has the `approach`
  lines.
- `skip`: staff in test mode only.

It answers with the town, as every town move does. Everything else (talk, give, travel, checkout, wait, duel) is the
normal move, and the server moves the tutorial on by itself when it's the step's action.

## The town page (Sam)

- **Elements to mark:** put `data-tutorial` on everything the steps name:
  - `person`: each person on stage;
  - `talk`, `gift` and `duel`: the talk menu's options;
  - `map`: the map button;
  - `place-<key>`: each place on the map;
  - `shop`: the shop counter button;
  - `add-pack`: a set's "Add 1";
  - `checkout`;
  - `quests`;
  - `wait`;
  - `decks`: a new "Decks" button in the town bar, to the save's decks.
- **On every paint, if `town.tutorial` is set:**
  1. play its `lines` in the talk box (the guide as "them": their picture and name), then post `said`;
  2. spotlight the first `highlight` that's on screen: dim everything else, ring the target, and put a small pointer
     with the hint by it;
  3. show the `title` as a goal banner at the top;
  4. disable (not hide) everything that isn't part of the step, so the town still makes sense. A disabled control's
     title says what the guide's waiting for.
- **In `arrive`:** clicking a candidate posts `approach` (instead of opening the normal talk), then plays the answer.
- **Guide-led sub-steps:** in `map`, `shop` and `gift`, move the spotlight along `highlight` as the player opens
  things (the map open: the shop place; the shop open: Add 1, then Check out).
- **Accessibility:** the spotlight is reachable by keyboard (focus moves to the target), announced (an `aria-live`
  hint), and works at phone width and with reduced motion.
- **A staff-only "Skip the tutorial"** button, in test mode, posts `skip`.

## The other pages (Sam 2)

While a save's tutorial is on (`save.flags.tutorial`, passed to the templates as `tutorial`), each of these pages
shows a small guide banner saying what to do, with "Back to the town" highlighted once it's done:
- **The pack reveal** (after the shop step's checkout): "Open your packs, then head back to town."
- **The quest log** (the `quests` step): explain the sections, and "Back to the town".
- **The save page and deck builder** (the `deck` step): "Make your equipped deck legal: 50 cards, 8 climaxes, at most
  4 of a card." Show the live count and, once it's legal, highlight "Back to the town".

## The writing (Danny)

The lines for each step, as chatter (`them:`, `player:`, `narrator:`, with moods), per guide, in
`world_pack/src/00_story.py` as `TUTORIAL = {"guides": [...], "lines": {step: {"*": [...], "Aang": [...], ...}}}`.
- **`arrive`** is narration only. Every other step is one script per guide, in their voice, with `"*"` as the
  fallback.
- **Plain lines only:** `them`, `player` and `narrator` say things, with moods. No choices, no `points` or `give`:
  the server does those.
- **Short:** 3 to 8 lines a step. Teach one thing; end on what to do next ("Press Talk").
- **The tone:**
  - **Conversational.** The player approaches the guide ("Excuse me, where am I?").
  - **The guide realises they're new** and offers to show them around, mentioning vaguely that it's like this for
    everyone when they first get here.
  - **"Where is here?"** gets a non-answer, and the guide moves on to the tour.
