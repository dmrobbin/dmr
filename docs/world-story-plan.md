# World mode: the story (plan)

The framework for the story is built: chapters that begin by themselves, one after another, with scenes at their
start, after each step and at their end. The story itself isn't written. This doc says how a chapter is written, and
lists every scene the story needs.

## How the story works

- **A chapter is a story quest** (`"story": true`, in `world_pack/src/00_story.py`, built into `00_story.json` and
  imported with the other packs on the Import tab).
- **It begins by itself** once what it `requires` is done: the chapter before it (`{"quests": ["story-1"]}`), or a
  flag (`{"flags": [...]}`). There's no offer and no accepting. The town says "Chapter 2: …", and the chapter's
  scene plays. The first chapter (no `requires`) begins when the save starts, so its scene plays the first time the
  player reaches the town, after opening their packs and building their first deck.
- **It finishes by itself** when its stages are done, by its one ending with no `to`. Its rewards and flags are
  given, its ending scene plays, and the next chapter begins.
  - **A chapter with a choice:** give it several endings, each with a `to` (the character it's settled with). The
    player chooses by talking to them, as with any quest, and the endings can lock or close other quests.
  - Only one ending can finish by itself.
- **Scenes a chapter can play** (each queued, so several in a row play one after another):

  | Where | Field | When it plays |
  |---|---|---|
  | The chapter | `"scene"` | When it begins |
  | A stage | `"scene"` in the stage | When that stage is done |
  | An ending | `"scene"` in the ending | When the chapter ends that way |
  | A visit objective | `"scene"` (and `"rewards"`) | When the player gets there, with its cast left there |

- **Its characters are always in town.** The cast arrives a few at a time, but whoever a chapter names (in its
  objectives or endings) is brought into town when the chapter begins ("Aang has come to town"). So a chapter can
  name anyone.
- **Objectives are all the quest objectives:** duels (`defeat`, `beat_different`, `streak`, `stakes`, `combo`,
  `win_with`, `win_deck`, `lose_to`), cards (`have_card`, `collect`, `give_card`), people (`talk`, `give_gift`, `rank`),
  places (`visit`), events (`event`) and flags (`flag`).
- **The quest log** shows the story first: the chapter under way in full, finished chapters a line each.

### Writing a scene for the story

Scenes go in `STORY_SCENES` in `00_story.py` as `{"name": "World: Story, …", "lines": [...]}`. They cast whoever they
need themselves (`cast aang as Aang`), with the player speaking as `player`. A chapter names the scene by its name.

- **Who's in a scene:**
  - **The opening scene's characters:** the starting cast is random per save, so the opening scene can't count on
    anyone. Either it's a narrator scene, or the first chapter names its characters (in an objective, such as "talk to
    them") so they're brought into town.
  - **Later scenes** can cast anyone a chapter names.
- **Keys never change:** saves refer to a chapter by its key (`story-1`). Rewording a chapter, adding stages to the
  end or adding scenes is safe. Changing a key, or removing a stage a save is on, isn't.

## Chapter 1 (built; its scenes are stubs to write)

`world_pack/src/00_story.py` holds Chapter 1's four quests. They run end to end now, with stub scenes (narrator lines
saying what goes there).

| Key | Quest | What the player does | Ends with |
|---|---|---|---|
| `c1-guide` | Choose your guide | Watches the welcome scene and chooses a guide (the scene's choice) | — |
| `c1-tutorial` | Learning the ropes | Meets the guide in the plaza (a visit scene, 100 coins), goes to the card shop with them (a visit scene, 200 coins), hears them out about friendship (a talk), and duels them; they play on Easy, and it counts win or lose | 1,500 coins, and the guide's "come back when you've won the tournament" scene |
| `c1-tournament` | Champion of the arena | Wins the weekly tournament | 1,000 coins, and the guide's scene on the player's friendships |
| `c1-best-friend` | A true friend | Becomes someone's Best friend (anyone; done at once if they are already), then tells the guide | A lucky pack, and the chapter's last scene |

**How the guide works:**
- **Choosing:** the welcome scene casts the candidate guides, and each option sets `mentor_<cast id>`. The one chosen
  becomes the guide and is brought into town.
- **Referring to them:** quests and scenes then write `{mentor}` for them: `"to": "{mentor}"`, `cast guide as {mentor}`.
- **One guide's own version:** a scene can have a version for one guide, named with theirs after it
  ("World: Story, C1 After the lesson (Aang)"), which plays instead of the general one when they're the guide.
- **Branching:** scenes can branch on `has_friend`, `has_close_friend`, `has_best_friend`, `has_mentor`, `champion`,
  and any flag a scene's choice set ("if has_best_friend goto proud").

### Chapter 1's scenes and talks to write

| Scene (or talk) | Plays | What it does |
|---|---|---|
| **World: Story, C1 Welcome** | The first time the player reaches the town | The player arrives; the candidate guides introduce themselves, each in their own voice; the player chooses (options `(set mentor_gN)`). The candidates are `GUIDES` in 00_story.py (now Aang, Chisato, Asuna and Erza): the writer picks the final few. |
| **World: Story, C1 Meet your guide** | Once the guide's chosen | The guide welcomes the player properly and says what they'll show them |
| **World: Story, C1 The town** | Visiting the plaza with the guide | People are out at different times, the map, passing time |
| **World: Story, C1 The card shop** | Visiting the shop with the guide | Packs, specialty packs, single cards, gifts, the basket |
| Talk: "Hear {mentor} out about making friends" | Talking to the guide | Talking each day, gifts (what people love), duels, ranks, what friends do for you |
| **World: Story, C1 After the lesson** | After the easy duel, win or lose | The guide pays the player to buy packs and says to come back once they've won the weekly tournament |
| **World: Story, C1 Champion** | Winning the tournament | The guide looks at the player's friendships: proud if `has_best_friend`; if not, encourages them to make a best friend first |
| Talk: "Tell {mentor}" | After making a best friend | The guide hears who it is |
| **World: Story, C1 Chapter end** | Chapter 1's end | The guide sees the player's made a true friend; a hint of Chapter 2 |

Each can be written once for any guide (casting `{mentor}`), or once per guide for the biggest moments.

### For every chapter after

Each chapter wants up to four scenes:
- **its start** (`scene`), which sets out what's happening and what to do;
- **one per important stage** (a stage's `scene`), for the beats in the middle;
- **its end** (an ending's `scene`, one per ending if there's a choice), the payoff;
- **visits** (`visit` objectives), meetings at places, each with its reward.

A chapter with a choice of endings also needs each ending's `about` (what the choice closes), and a cold line for
any character it closes off (as the conflict-pair quests do).

## Decisions for whoever writes the story

- **The guide:** does the story have a guide character (an existing CPU, or a new one made for the story), or is it
  told by the narrator? A guide gives the opening scene someone to talk to, and the story a voice.
- **Its shape:** how many chapters, and how they tie into the characters' own quests and the weekly events. A
  chapter can require a character's quest done, a rank reached or a tournament entered.
- **Its stakes:** does the story have big choices (endings that lock other chapters, so the three save slots tell
  different stories), or is it one line through?
