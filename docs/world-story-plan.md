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

## What's in now: a placeholder chain

`00_story.py` has three placeholder chapters, so the chain can be played through before anything's written. They
have plain objectives and no scenes:

| Chapter | Key | Stage | Reward |
|---|---|---|---|
| 1. A new town | `story-1` | Win your first duel | 300 coins |
| 2. Making a name | `story-2` | Beat three different duelists | A climax pack |
| 3. Tournament weekend | `story-3` | Enter the weekly tournament | 500 coins |

To try it: build the packs (`python world_pack/build.py`), import `00_story.json` on the Import tab, and start a
new save. Saves started before the import begin Chapter 1 the next time anything changes.

## Scenes to write

None of these are written. Names are suggestions; a chapter names whatever it's called.

### The opening (Chapter 1)

| Scene | Plays | What it needs to do |
|---|---|---|
| **World: Story, Opening** | The first time the player reaches the town (Chapter 1 begins with the save) | Welcome the player to town and set up why they're here. Point them at the card shop and the arena. End on what Chapter 1 asks ("win your first duel"). A narrator scene, or one with a guide character Chapter 1 names. |
| **World: Story, First win** | Chapter 1's stage done (its first duel won) | A short beat: someone noticed. Sets up Chapter 2. |
| **World: Story, Settled in** | Chapter 1's ending | Optional. A night in town, the player settling in. |

### Chapters 2 and 3 (the placeholders, once they're real)

| Scene | Plays | What it needs to do |
|---|---|---|
| **World: Story, Making a name** | Chapter 2 begins | The town starts talking about the newcomer. Introduce whoever Chapter 2 is about. |
| **World: Story, A name in town** | Chapter 2's ending | A rival or a mentor reacts to the player's three wins. |
| **World: Story, Tournament weekend** | Chapter 3 begins | The weekly tournament explained in story terms: who runs it, who's entering, why it matters to the story. |
| **World: Story, In the bracket** | Chapter 3's ending (entered) | The night before the rounds. |

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
