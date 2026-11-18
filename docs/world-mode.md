# World mode: plan

A single-player world. The player visits places around a town, each an illustrated scene, and meets the CPUs their
schedules put there. They talk to them, give them gifts and duel them. Wins bring money, and money buys packs at the
card shop. The player builds decks only from cards they've opened. Time moves through four slots a day, seven days a
week, and each CPU has places it can be found at certain times.

## Decisions

| Topic | Decision |
|---|---|
| Time | 4 slots a day: morning, noon, evening, night. 7 days, Monday to Sunday, then the week repeats. |
| Moving around | Places are scenes: an illustrated backdrop (one per time of day where it matters), with the CPUs who are there standing in it. The player travels by a map of places, not by walking. (A walking avatar was tried first; see "What's built".) |
| How people look | CPUs appear as their own uploaded art (their card-art pictures where they have none). The player has no figure in the scene: they rarely speak, so they're just their name in the box. (A paper-doll portrait was tried; see "What's built".) |
| Talking | In a box over the scene, not a full visual novel scene: the others clear and the CPU reacts with its pictures. Full scenes are kept for big moments. |
| New game | The player picks a set; only sets with 100+ cards are offered. They get a number of packs from it plus specialty packs, both set by staff in the admin. Staff make sure that's always enough for a legal deck. |
| Cards and decks | World mode has its own collection and decks, kept apart from the site's free deck building and from challenges. |
| Saves | 3 save slots per player. |
| Losing a duel | It uses up the time slot, and that's all. |
| High-stakes duels | The player may pay to enter. A loss forfeits the fee; a win pays a larger prize. |

### Choices I made where the design was silent

These are noted here so they can be changed.

- **What moves time on:** a duel (win or lose), and "pass time". Looking around (travelling, the map) and shopping
  are free. Since "Spending the time" (below), talking and gifts commit the player to the place until time passes.
- **The set must have 100+ cards that can come from packs.** Promos and trial deck cards (`packs.NOT_IN_PACKS`)
  don't count, so the set can really fill packs.
- **Several decks per save, one equipped.** Duels use the equipped deck. A duel can't start unless it's legal.
- **Duels left unfinished:** the save stays in that time slot until the game ends; conceding counts as a loss.
- **Only one save is played at a time.** Each save gets a `version` field, raised on every change, as on
  `CoopRun`, so a second tab can't double-spend money or time.
- **The server is the authority on time, place, money, cards and friendship.** The page only shows them. Whenever the
  player acts on a CPU, the server checks that CPU is actually at that place in that slot.

## What's built

### The town test (`world/test/`, staff only)

A try-out of how meeting CPUs should feel, with everything but the duel made up and kept in the browser tab.

- **Places:** eight (plaza, café, library, duel arena, shrine, beach, forest, school), drawn with the scene backdrops
  (`static/weiss/backdrops.js`). A place can change backdrop with the time of day (the plaza is under sakura by day and
  a lit city at night), and daylit scenes are tinted for morning and evening.
- **Who's where:** made-up schedule rules per CPU (days, times, a chance, "once a day"), resolved from the time alone,
  so reloading never moves anyone.
- **Talking:** click someone and the others clear; a box over the scene offers Talk, Give a gift, Duel and Leave, with
  a friendship badge (hearts, rank, points to the next). Talk once a day for points; gifts are loved, liked or
  disliked, with the CPU's pleased or dismayed picture and a floating "+8 ♥". **Duel** starts a real game against
  that CPU with the player's deck.
- **Map and time:** the map shows every place and who's there; "wait" moves time on and says who left and arrived.
- **Fallbacks:** a CPU with no picture (or one that won't load) stands as a tinted silhouette with its initial.

### The paper-doll portrait (removed)

The player's own anime portrait, layered from two artists' sprite kits (Sutemo's and Tainara-P's, about 60 MB of
images), made in an editor on the profile and shown in town conversations, reacting with moods. Removed after
testing: the player rarely speaks, so it added little. Its `portrait` field came and went in migrations 0043 and
0059. Chatter still accepts a mood on a `player` line (`player (smile): …`) and drops it, so older scripts compile.

### The pixel-art character creator (removed)

Built first, for the walking map, with LPC pixel art; removed once the world became scenes. Its
`character` fields came and went in migrations 0042 and 0045.

## Open decisions

- **An intermittent test:** `test_buffs.SceneBuffFlowTests.test_no_scene_and_so_no_buffs_outside_a_narrative_challenge`
  failed once in a parallel run and passed on every rerun.

## Phase 1: saves, new game and collection — built

At `world/` (staff only while world mode is built), with the settings on the CPU creation page's **World mode** tab.
Built as planned below, with these differences:

- **Several decks per save** (up to 10), every one built from the same cards opened, so a card can be in all of them.
  `WorldSave.deck` is the **equipped** one, which duels use. The save's page lists them: build, equip, rename, delete
  (a save keeps at least one; deleting the equipped one equips the next), and a new deck, empty or a copy of another.
  A deck's builder is at `world/<slot>/decks/<id>/`; `world/<slot>/deck/` opens the equipped one's.
- **The challenge code isn't changed to take a save.** Its wrappers carry challenge-only things (co-op sharing,
  augments, kinds), so `weiss/world.py` has small functions of its own on the layer underneath: `weiss.packs` for
  pools and opening, `weiss.buffs` for the specialty packs (a save has the fields it reads: `pool`, `rewards`,
  `last_opening`, `sets`) and `weiss.lists` for the deck rules. The challenge templates for the pack reveal, the
  specialty packs and the deck builder take their links as context, so world mode uses them too.
- **Duelling needs a full deck:** 50 cards, 8 climaxes, at most 4 of a card by name (`world.deck_problem`). While it's
  built, a deck can be saved short, as a challenge's can.
- **World decks can't be edited on the lists pages** (`lists.editable_lists` leaves them out), so the only way to change
  one is the save's deck builder, which keeps to the cards opened.
- **If the cards opened can't make a legal deck** once every pack's open, the save's page says what's missing.

The plan as it was:

- **`WorldSettings`** (one row, like `ChallengeSettings`) on a staff admin page:
  starting packs, starting specialty packs (`{buff id: count}`, the same picker as the challenge loadout), and the
  economy (starting money, pack price, win payout, payout per score point, first win of the day bonus).
- **`WorldSave`**: `user`, `slot` (1–3, unique per user), `set` (the expansion it started with), `turn` (the slot of
  time since it began: the day, weekday and time of day all follow from it), `place`, `money`, `pool`
  (`{card id: copies}`, as in challenges), `packs`, `rewards`, `last_opening`, `equipped_deck`, `relations` (phase 4),
  `flags`, `today` (per-day counters, cleared at day rollover), `seed`, `version`, and timestamps.
- **World decks:** `CardList` gets a `world_save` foreign key. Lists that have one are hidden from the normal
  list pages and challenge pickers, and deleting a save deletes them.
- **Share the challenge code instead of copying it:** pack opening, the specialty pack buffs and the pool-limited
  deck builder read and write fields on a `ChallengeRun`. Change them to work on anything that has `pool`, `packs`,
  `rewards` and `last_opening`, and give `WorldSave` those same fields. Only the specialty packs staff can choose for
  a loadout (`challenge.LOADOUT_BUFFS`) are allowed in world mode.
- **Pages:**
  - Save select: 3 slots, each showing the day and time, money, the set it started with, and when it was last
    played. An empty slot offers a new game. Deleting a save asks the player to type its slot name, since it can't be undone.
  - New game: choose the set (with the art of one of its cards, and its card count) → open the packs (reuses the
    reveal) → claim the specialty packs → build the first deck → into the town.
- **An empty state no one should hit:** if a starting pool still can't make a legal deck, say what's missing
  instead of trapping the player. The staff settings page also warns when the counts look too low.

**Done when:** a player can start a save in any of 3 slots, open their starting packs, build a legal deck, and
find it again in that slot later. Their other decks and challenges are untouched.

## Phase 2: places and time — built

The town page is at `world/<slot>/town/`, linked from the save's page (any time: looking around needs no deck, and
the town says when the equipped deck isn't ready to duel).

- **`WorldPlace`**: key, name, four backdrops (morning to night), map order, and `unlock_flag` (empty for open from
  the start). Migration 0047 adds the town test's eight places. Unlocks by rank or day can join the flag when
  something needs them; staff editing of places comes with the World tab (phase 5).
- **`weiss/world.py`** keeps the time and place: `places` (those the save can go), `travel` (free), `wait` (the next
  part of the day; after night a new day, and `today` is cleared) and `town`, the state the page draws.
- **The page** (`static/weiss/world_town.js`) draws what the server says and posts each move with the save's
  `version`. A move from a tab that's behind is refused (409) with the town as it is now, so two tabs can't both
  spend the same time; a tab coming back into view catches up by itself. Keys: M for the map, W to pass time.
- **Nobody's in the town yet:** people come with their schedules in phase 3. Until then the town test
  (`world/test/`) still shows how meeting them will feel; it goes once phases 3 and 4 have brought that over.

The plan as it was:

- **`WorldPlace`** model: name, a backdrop for each time of day, whether it's a starting place, an unlock condition (a
  flag, a rank, a day), and its order on the map. The town test's eight places become the first rows.
- **The town page** for a save: the place, its scene, the day and time, money, the map and "wait", as in the test,
  with every change posted to the server and the page redrawn from its answer.
- **Endpoints:** travel, wait (advance the slot, rolling the day over after night), and the place as it is now.

**Done when:** a save travels between places and waits, the time and money shown are the server's, and a reload
puts the player back where they were.

## Phase 3: schedules, duels and the shop — built

- **Schedules:** `CpuSchedule` rules (a CPU, a place, days, times, a chance, once a day, a priority, and a high-stakes
  entry fee). `world.whereabouts` works out who's where from the save's seed and the turn alone, so reloading never
  moves anyone and two saves see different rolls. Only finalized CPUs with a deck appear.
- **The staff's page** (`world/schedules/`, linked from the World mode tab): a grid of who's where for each day of a
  sample save ("try another save" re-rolls it), the rules by CPU to edit or delete, and the form to add one (an exact
  repeat is refused).
- **Every CPU starts with a schedule:** migration 0050 gave each existing CPU that can duel one, and finalizing a CPU
  with no rules gives it one (a CPU with rules keeps them as staff left them). `world.starter_rules` makes three: a
  home most weekdays at two times, a weekend spot and somewhere it wanders on three days, each in whichever place has
  the fewest rules so far, so the town fills evenly. Staff edit them from there; the page's button does the same for
  any CPU still without rules.
- **People in the town:** whoever's at the place stands in the scene; waiting says who left and who arrived. The map
  shows who's at every place right now (their circle pictures and names, four at most and how many more), so the
  player can go and find someone. Talking to
  someone offers **Duel**, a **high-stakes duel** where their rule has a fee, and
  Leave. Talk and gifts come with phase 4.
- **Duels:** a real game against the CPU with the equipped deck, linked to the save (`GameRoom.world_save`, and
  `world_stake` for the fee, taken when it starts). When the game ends, `play.game_ended` hands it to
  `world.game_finished`, once per game: a win pays `win_payout`, plus `first_win_bonus` for the day's first win, plus
  twice a high-stakes fee; win or lose, the time slot's used up. The game-over screen says what it paid and goes
  "Back to the town", where the result is said once. A town duel can't be rematched, reset or given another deck.
- **An unfinished duel holds the time:** while it's under way, the town says so (with a link back to it), waiting is
  refused and no other duel can start. Travelling and shopping still work.
- **The card shop:** a place of its own (migration 0049) with a new backdrop, `shop`, drawn in `backdrops.js` (and
  usable in scenes). Its counter sells packs at `pack_price`: the save's set always, and up to three other sets that
  change each day. Bought packs open straight into the save's cards, with the reveal, then back to the town.
- **The shop counter's three tabs** (`world.shop`):
  - **Packs:** each set is shown with its cover card, the same rule as the set list (the lowest number of its main
    print run, `world.set_cover`).
  - **Specialty packs:** lucky, climax, level and color packs (`SHOP_SPECIALS`) at `specialty_price` (600 by
    default). They're made from any of the day's sets by `buffs.reward_pack`, and opened with the reveal.
  - **Single cards:** a row of ten rares and better (R/CR and up, never promos or trial deck cards) to scroll through.
    They come from the day's sets, change each day, and are shown rarest first. Each costs a flat `card_price` (3,000
    by default), and you can buy one of each a day. A card goes straight into the save's cards without leaving the
    town (`world_buy_card`, a town move).
  - Staff set both prices on the World mode tab (migration 0051).
  - The grade table (`packs.GRADES`) learned "N", an extra booster's plain print. It had been graded as a special
    foil, which skewed that set's packs and would have put plain cards among the shop's rares.

The plan as it was:

- **`CpuSchedule`** rows: `cpu`, `place`, `days` (a set of 0–6), `slots` (a set of 0–3), `chance` (0–100),
  `once_per_day`, `priority`.
- **Resolving who's where:** a function of (save seed, turn) only, as in the town test. Per CPU and slot: take the
  rules that match, highest priority first; roll each one's chance. For a once-per-day rule, the seed picks one of its
  slots for the day and the CPU appears only in that slot. A CPU is never in two places at once.
  - Cinder: bar, Tue + Fri, night; forest, Sat + Sun, evening.
  - Katara: plaza, Mon–Fri, noon, 80%.
  - Mai: cafe, every day, morning/noon/night, once per day.
- **Staff schedule grid:** a 7 × 4 table showing who's where for a given seed, with clashes and empty places
  marked. It's both the writing tool and the debugging tool.
- **Duels from the world:** `GameRoom` gets a `world_save` foreign key; the room is made with the existing
  `seat_cpu`. When it's over, `play.game_ended` calls a new `world.game_finished(room, over, score)`:
  - a win pays the base payout + score × rate (from `scoring.win_score`), plus the first win of the day bonus
  - a loss or win uses up the slot
  - the player goes back to the place they left from
- **High-stakes duels:** an entry fee that is paid when the game starts and isn't refunded if it's lost, and a
  prize for winning, offered from dialogue (phase 4) or on a schedule rule. The fee is taken in the same transaction
  that makes the room, so it can't be paid twice or skipped.
- **The card shop:** a place with a shop counter. Packs are priced per set, and the stock changes by day (from the
  seed). Phase 4 adds gifts. Buying opens the packs into the pool with the reveal.

**Done when:** CPUs appear by their schedules and stay put on reload; a duel started from a place pays out and
moves time on; a high-stakes loss keeps the fee; the shop sells packs. The full loop works: visit, duel, earn, buy,
build, duel again.

## Phase 4: dialogue, relationships and gifts — built

- **Talking:** clicking someone offers Talk, Give a gift, Duel (and a high-stakes duel where they play for stakes) and
  Leave. Their lines play in the box, with the CPU's mood (its pleased and dismayed pictures). Friendship shows at the box's top right: hearts, the rank's name and points to the next.
- **Chatter** (`weiss.chatter`, the `Chatter` model): a compact form of the scene language. `them`, `player` and
  `narrator` speak (the CPU with moods), and there are choices, labels, flags, `if rank >= N goto`, `points ±N`,
  `give money N`, `give gift <key>`, `fight` and `fight stake N`. Staging lines (cast, entrances, backgrounds and the
  like) are refused, each with a message saying why.
  - **The server runs the script** and the page only plays what it says happened, so points, coins and stakes can't be
    forged. A choice posts the answer and the server carries on.
  - **Coins, points and gifts a line gives come once a day per line**, so talking again can't farm them.
  - **Flags a script sets belong to the save** and can open places (`WorldPlace.unlock_flag`). The save's own flags
    (last_duel and so on) can't be set.
- **Contexts:** greet (the day's first talk), again, four gift reactions (loved, liked, neutral, disliked),
  before_duel, after_win, after_loss and rank_up.
  - **Picking a line:** a CPU's own lines come first, then lines for any CPU (`cpu` left empty), then the built-in
    `chatter.DEFAULTS`, so no CPU is ever silent. Within those, the highest `min_rank` the player has reached wins,
    picked by `weight`. A line with mistakes is skipped, never shown.
  - **One-line contexts:** before_duel, after_win and after_loss show their first line. The duel's line is said before
    it starts, and the after-duel line goes in the result banner above the stage.
  - **Stakes:** these are offered in talk, with `fight stake 500`. That replaces the planned "stake offer" context;
    a schedule rule's stake still works as before.
- **Friendship** (`save.relations`):
  - **Points:** 3 for the day's first talk, 6 for a win and 2 for a loss. Gifts give 12 loved, 6 liked, 2 neutral and
    −4 disliked; points never go below 0. You can give each CPU one gift a day.
  - **Ranks:** set by staff on the World mode tab as "name: points" lines. The defaults are Stranger, Acquaintance,
    Friend, Good friend, Close friend and Best friend.
  - **Reaching a rank** plays that rank's rank_up line, or its full `Scene` if the Chatter row names one. The scene
    plays once on its own page, then the player is back in the town.
- **Gifts:**
  - `GiftItem` (key, name, emoji, about, price, tags): 14 starter items (migration 0053), sold on the shop's Gifts tab.
    The save keeps what's bought (`save.gifts`).
  - Each CPU's `gift_tastes` lists the tags it loves, likes and dislikes; a loved tag wins over a disliked one.
    Starter tastes are given to every CPU (by the migration, and on finalizing a new one), the same way starter
    schedules are.
- **Editing:** staff pages for all of it came with phase 5. The Django admin also lists gift items and chatter.
- **Not done:**
  - A rank reached through a duel shows in the result banner, but doesn't play its rank-up line or scene.
  - The other unlocks the plan mentions (a stronger deck, a rank condition for sleeves) aren't built. Places can open
    on a flag that chatter sets.

The plan as it was:


- **Dialogue in the box:** the town test's box, driven by the scene script language (`compile_scene`) in a "compact"
  mode that allows speech, choices, `set`/`if`/`goto` and `fight`, and refuses staging lines (enters, moves,
  background, screen) with a clear error. Staff keep one language. Lines can ask for a mood, for the CPU's picture.
- **New script verbs:** `if rank >= 3 goto …`, `points +5`, `fight stake 500`, `give money 100`.
- **`Chatter`** rows: `cpu`, `context`, `min_rank`, `weight`, `script`. Contexts: greet, already talked today, gift
  (loved / liked / disliked), before a duel, after a win, after a loss, stake offer. One is picked at random from
  those that fit. A CPU with none for a context falls back to a generic line, so new CPUs are never silent.
- **Relationships:** `relations` on the save: `{cpu id: {points, rank, talked_day, gifts_today}}`.
  - Points from the first talk of the day, a win, a loss (a little), and gifts.
  - A cap on gifts per CPU per day.
  - Rank thresholds and names in `WorldSettings`.
  - Reaching a rank can play a full `Scene` and unlock dialogue, places, high-stakes duels, a stronger deck or a sleeve
    (a new `rank` condition in `weiss.sleeves`).
- **Gifts:** `GiftItem` (name, icon, price, tags), sold at the shop; an inventory on the save; each CPU has liked and
  disliked tags.

**Done when:** talking, gifts and wins raise a CPU's rank; dialogue changes with rank; the caps hold; and a rank-up
can play its scene.

## Phase 5: staff tools and CPU format — built

- **The World mode tab** links to every world page: the settings (starting packs, coins, prices, friendship ranks) on
  the tab itself, CPU schedules, and three new pages (`weiss.world_staff_views`):
  - **Places:** each place's name, its backdrop for each time of day (with a picture of each), map order, unlock
    flag and whether it has the shop counter. Places can be added, and deleted (with their schedule rules; the last
    one stays).
  - **Gifts:** gift items (icon, name, price, tags, order), with how many CPUs love, like and dislike each one, and a
    table of every CPU's tastes to edit, plus a button to give starter tastes to CPUs that have none.
  - **Chatter:** every line by CPU and moment, with any mistakes flagged, and how many lines each moment has. Lines
    are written in the scene editor: same reference, palette, live checking and Ctrl+S. The palette has speakers and
    moods, ranks and gift keys, and a rank-up can name a scene to play instead.
- **CPU files** (`weiss.cpu_corpus`) gain a `world` part: schedule rules (places by key), gift tastes and chatter
  (a rank-up's `scene` by name, from the same file or one that's there already).
  - **Import** checks it all, with every problem listed, and makes it once the batch's scenes exist.
  - **Export** writes it for each CPU, plus `world.json` (places, gifts, tags, contexts, ranks, moods), `chatter.json`
    (the built-in lines and those for any CPU) and a World mode section in `reference.md`.
  - **`check_cpu_file`** checks a file's world part against `world.json`. An export from before world mode says it
    needs exporting again.
- **The `new-cpu` skill** writes a world part for every new CPU. STYLE.md says how many rules, tastes and lines, and
  in what voice.

The plan as it was:


- A **World** tab for staff: settings, places, the schedule grid, gift items, and chatter (in the scene editor, in
  compact mode).
- **CPU export and import** (`import_cpu`, the files in `corpus/`): add schedule rules, gift likes and chatter. Update
  the `new-cpu` skill to write them, so new CPUs arrive ready for the world.

## After phase 5: the cast, haunts and rank rewards — built

The town is written for the 75 CPUs there are now; no new ones are planned for a while.

- **Who's where is drawn fresh each day** (`world.day_cast`).
  - **What a haunt is:** a CPU's schedule rows are now haunts (migration 0054). Each has a place, days, times, a
    `weight` (the old chance), an optional `min_rank`, and a stake.
  - **How the draw works:** each save draws each day's cast from its seed, so a reload never moves anyone. Every
    time of day puts 6 to 10 CPUs out in the town, never more than 2 at a place. Someone out already that day is less
    likely to turn up again.
  - **Rank-gated haunts:** a haunt with a `min_rank` is drawn like the rest but left out until the player knows that
    CPU well enough, so getting closer to one CPU never moves another.
  - **The staff grid** shows the draw for a sample save, with how many are out at each time and rank-gated haunts
    marked.
- **Villains keep to the dark.** Three secluded places (back alley, old warehouse, rooftop; migration 0055) join the
  shrine and the forest. The twelve villains haunt them in the evening and at night, and each has one daytime haunt
  somewhere busy that opens at Friend (rank 2).
- **Temperament** (`CpuProfile.temperament`): warm, friendly, neutral, aloof or villain. It scales the points from
  talk, gifts and duels (×1.5, ×1.25, ×1, ×0.75, ×0.6). Lost points and a script's own points aren't scaled.
- **Rank rewards** (`world.RANK_REWARDS`), each given once per save and CPU, however the rank was reached:

  | Rank | Rewards |
  |---|---|
  | 1 Acquaintance | 200 coins, and a gift they love |
  | 2 Friend | 2 copies of a signature card from their deck, and a climax pack of their set |
  | 3 Good friend | a color pack in their deck's main color, and 400 coins |
  | 4 Close friend | high-stakes duels with them for 500 coins wherever they are, and 2 copies of their ace |
  | 5 Best friend | 2 copies each of their key cards and their climax, a lucky pack, and 1,000 coins |

  The talk box plays each reward as it comes, with "See the cards" for a pack. The friendship badge says what the
  next rank brings. A rank reached in a duel gives its rewards in the result banner, along with the rank-up line or
  a link to its scene (this closes the earlier gap). Every rank reached also counts for card sleeves, through a new
  condition: "Friendship rank reached in world mode", optionally with a particular CPU.
- **The cast pack** (`world_pack/`):
  - **What it holds:** every CPU's temperament, 3–4 haunts, gift tastes, 13 lines of chatter (greetings for a
    stranger, a friend and a close friend, talking again, gifts, duels, and rank-ups 1, 3 and 4), and two full scenes:
    "World: <name>, Friend" and "World: <name>, Best friend".
  - **Sources:** written in `world_pack/src/` and built with `python world_pack/build.py`.
  - **Checking:** `python manage.py check_world_pack world_pack/*.json` checks them against the export's CPUs.
  - **Loading:** staff upload the JSON files on the Import tab's new "World mode packs" section, which checks first
    and replaces each named CPU's haunts and chatter. CPUs it can't find are skipped and listed.
- **To put it live:** deploy (migrations 0052 to 0055 run), then upload the six `world_pack/*.json` files on the
  Import tab: Check, then Import.

## Phase 6: quests — built

The system is built; the quests themselves are written later. Until a CPU has gate quests, its friendship ranks up
on points alone, as before. World mode stays staff-only until the quests are in.

### Decisions

| Topic | Decision |
|---|---|
| What they're for | For now, gating the big rank-ups: the ones with scenes (Friend and Best friend). The main story will use them too. |
| Choices | Endings are a choice point, made by talking to whoever that ending's turned in to. An ending can close other quests for good (`locks`) and send CPUs away for good (`removes`). This is an RPG, not a sandbox: the three save slots are how a player tries the other road. |
| A closed friendship | A hard cap: the CPU stays at the rank below the closed quest's, for that save. They're still in town to talk to, duel and give gifts to, and points still count, but they don't rank up. They speak coldly (`estranged` chatter). |
| A CPU sent away | Gone from that save's town for good. Their quests close, and so does any quest that can't be done without them. |
| Warnings | Taking a quest closes nothing. Before an ending is chosen, the player sees exactly what it closes: the quests (and why), who leaves, and who stays at what rank. An ending that closes anything is asked about a second time, with the focus on "Go back". |
| Failing | Only by being closed. There are no deadlines and no giving up. |
| How many | No limit on quests under way. Each is a small record on the save, and checking one is cheap. |

### How it works (`weiss.quests`)

- **`Quest`** (migration 0056): key, title, giver, `gate_rank`, and a `spec` (about, offer, requires, stages,
  endings, rewards, hidden), all checked by `quests.check`. The staff editor and both importers use that same check.
- **On the save** (`WorldSave.quests`): `log` {quest key: status, stage, progress, ending or what closed it},
  `gone` (CPUs sent away) and `news`.
- **Gating** (`quests.cap`): `world.rank_of` never passes one below a gate quest that isn't done. Points keep coming.
  The gate quest is offered once the points are there, so finishing it jumps the rank, which plays its scene.
- **Objectives:**
  - `have_card`, `collect`, `rank` and `flag` are checked whenever the save changes. `world.changed` calls
    `quests.advance`, so a card from any source counts.
  - The duel objectives are counted from what the game recorded: `defeat`, `lose_to`, `combo`, `win_with`,
    `win_deck`, `stakes`, `streak` and `beat_different`. The engine keeps a whole-game record per player
    (`game.record`: `played` cards, and `combos` as [character, climax] when a combo ability starts).
    `win_deck` checks the deck as it was when the duel started.
  - `visit` counts when the player travels, waits or finishes a duel. `give_gift` counts when a gift is given.
  - `talk` and `give_card` are done from the talk box.
  - A card is any printing of its name.
- **In the town:**
  - Someone with a quest has "!" over them, and someone with something to do about one has "★".
  - The talk menu lists quest options first: hear an offer, talk it through, hand a card over (asked about first,
    with what it means for the decks) and finish it (the endings).
  - Quest news from duels and travel stays above the stage until dismissed.
  - The friendship badge says when the next rank waits on a quest, or is closed.
  - A rank-up scene that's still to be watched waits in the town, so following "See the cards" never loses it. Packs
    given together are revealed together.
- **The quest log** (`world/<slot>/quests/`): under way (with what's offered, each stage, progress counts and the
  endings once it's ready), finished (with the ending) and closed (by which choice, and the rank that stays). Hidden
  rewards say "A surprise".
- **Staff:**
  - **The list** (`world/quests/`, on the World mode tab): each quest's endings and what they close or send away,
    any that no longer check out, and which CPUs' rank-up scenes have no gate quest yet.
  - **The editor:** the quest as JSON, checked as it's typed, with a preview as the log shows it. A quest with
    mistakes isn't saved, but its text stays on the page. A quest can lock or require one that isn't written yet
    (noted, not refused), so two quests that close each other can be written one at a time.
- **Files:**
  - A CPU's `world` part has `quests` (its own: no giver). Packs check that every quest key they name exists, in the
    database or the pack.
  - A pack import replaces a CPU's quests only if its entry has `quests`.
  - `world_pack/build.py` takes `quests=` per CPU. The export writes them, and `reference.md` documents them.
  - The `new-cpu` skill's STYLE.md says how to write them.

### Written so far

- **Pilot (six CPUs, each with a Friend and a Best friend gate quest):** Aang and Azula (`01_avatar_gurren.py`),
  Denji and Power (`03_chainsaw_titan_killlakill.py`), Chisato and Takina (`05_overlord_sao_more.py`). Two pairs lock
  each other: Aang's "reach" ending closes Azula's "Heir of Fire", and her "crown" closes his "Avatar State";
  Takina's "mission" closes Chisato's "Bring Takina Back", and Chisato's "rescue" closes Takina's "Lycoris, Apart".
  Each CPU that a quest can close has a `cold` line (the new `estranged` context, in `build.py`).
- Card serials are taken from each CPU's own finalized deck. The dev database holds only a few hundred cards, so the
  pack check ran offline and didn't confirm them; the server's import checks them against the real card table.
- Not yet played in the browser.

### Not done

- The quests for the other 69 CPUs.
- A `visit` objective's scene is skipped if another scene is already waiting to be watched when the player arrives.
- Editing a quest that saves have started changes it under them. The editor warns, but nothing migrates their place.

## Spending the time, and time passing — built

Time is the player's budget. Where to go and whom to see should be a choice.

- **Spending a time of day** (`world.engaged`):
  - Looking around (travel, the map) and the shop are free.
  - Talking to someone, giving a gift, anything about a quest, or starting a duel spends the time of day at that place.
    The map gives way to "Pass time" until it passes, and travel is refused.
  - Passing time needs the time to have been spent with someone, so the old Wait button is gone. The exception: with
    nobody out anywhere in town, time can pass anyway, so a save can't get stuck.
  - At most one talk with each person per time of day, plus one gift each a day as before. So at a place with two
    people, the most a time of day holds is two talks, two gifts and a duel, and the duel passes the time itself.
  - The first time the player spends a time of day, the town says so.
- **Time passing** (`world_town.js` `passage`): over the stage, the sky turns and the sun moves along its arc. Into
  the night, the moon fades in instead. The new day and time are shown, then the place as it is now. It runs:
  - after "Pass time";
  - when the player comes back from a duel. That page arrives with the transition already covering the place, so
    nobody vanishes on screen. It starts from the duel's own time (`last_duel["before"]`), and if the CPU duelled has
    moved on, the town says they've gone on their way.

  A click or key skips it, and reduced motion gets a short fade.
- **Where now?** (`world.choosing`): every time time passes, whether you waited or a duel ended, the map opens under
  the transition and has to be answered. The place the player is at is offered as "Stay here". It can't be closed,
  and nobody can be talked to or duelled until a place is chosen. It's kept on the save, so a reload brings it back.
- **Staff test mode** (`world.test_mode`, `flags["test_mode"]`, staff only):
  - A "Test mode" toggle in the town's bar, dashed so it never looks like part of the game.
  - When it's on: a "Wait (staff)" button passes time whenever, travel is free, and the map after time passes can be
    skipped.
  - When it's off: staff play by the real rules.
- **Hello and goodbye** (chatter contexts `hello` and `goodbye`, first line only, migration 0057):
  - What a CPU says when the player walks up and leaves, by rank, picked once per time of day.
  - Built-in lines cover a stranger, a friend and a close friend. An estranged CPU is cold.
  - All 75 CPUs have their own: three of each in `world_pack/src` (`hello` and `bye`: a stranger's, a friend's
    (rank 2) and a close friend's (rank 4)), built into the packs. Re-import the six packs to put them live.

## Staff testing: raising a rank — built

Checking a quest or a rank-up scene used to mean playing for days. Two quick routes, both staff only:

- **The talk box's "Raise a rank (staff)" button** (test mode on): takes the person here up one rank at once, by the
  points that rank needs. No time is spent and the daily talk and gift limits don't apply. It plays what a rank reached
  by points plays (the rank-up line or scene, and that rank's rewards, once).
  - **A gated rank is tested in steps:** the first press stops one point short of the gate's rank, so the quest isn't
    offered yet. The next press reaches the rank's points, which offers the quest, and the rank holds. Further presses
    say which quest holds it. Finishing the quest then lets the rank go up.
- **The staff token** (a `GiftItem`, migration 0058): 0 coins, sold at the card shop to staff only (players never see
  it, and rank rewards never give it). Giving it does the same as the button, without the day's gift limit or any time.
  It's bought at the shop as any gift is, so staff use the same flow to test.

## Testing

- **Unit tests:** schedule resolving (the same for a seed, once-per-day, no double placement, priority), time
  and day rollover, payouts, stake fees on a win, a loss and an unfinished game, save slot limits, keeping world
  decks out of other lists, gift caps and rank thresholds, and the compact mode refusing staging lines.
- **In the browser:** every page at phone width, by keyboard, with zoomed text and reduced motion, and on a slow
  network (scene and CPU images loading). Headless browsers run with `--mute-audio`.

## Risks

- **CPU art:** a place looks best when its CPUs have uploaded art; ones without fall back to card art or a silhouette.
- **Writing:** dialogue is what makes CPUs feel alive, and it's the slowest part to make. Generic lines cover the gaps.
- **Scope:** phases 1–3 make a complete game. Relationships and staff tooling can land after players are already
  playing it.
