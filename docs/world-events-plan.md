# World mode: weekly events and timed quests (plan)

A plan for approval: nothing here is built yet. It covers the framework all timed things share, then the two events
asked for (sale days and the weekly tournament), timed quests, and a list of other events to consider.

## Built so far

Decided (2026-11-18):
- **Tournament:** it uses all of Sunday.
- **Tournament friendship:** points only for the CPUs the player beats (8, scaled by temperament).
- **CPU against CPU:** a seeded coin flip.
- **Sales:** as proposed.
- **Calendar:** a full calendar now, starting on 18 November.

Built:
- **The calendar** (`weiss/world_calendar.py`):
  - Every save starts on Monday 18 November. The calendar is a real one (month lengths, leap years), anchored on 2024,
    when 18 November was a Monday, so weekdays (and every haunt) mean what they always did.
  - The year is the save's own: Year 1 until its first 1 January.
  - `date_of`, `month_day` ("12-25") and `season_of` are the groundwork for seasonal and holiday events.
  - The town, the save list, the save page and the quest log show the date ("Wednesday 20 November").
- **Events** (`WorldEvent`, migration 0061, `weiss/world_events.py`):
  - Rules: weekdays, times, every N weeks with an offset, a first week, months and dates. Every rule given must hold.
  - `WorldSave.events` keeps what a save did at each event, per week.
  - Staff edit events on the World mode tab's Events page, with a preview of a save's first four weeks.
- **The notice board** (`world/<slot>/events/`, the town's "This week" button): the week's calendar, today's sales,
  and the tournament (entry, then the bracket).
- **Today's events** show in a line above the town's stage.
- **Sales:** featured set (Wednesday, half price, 5 packs a day, put on the shelves), specialty happy hour (Friday
  evening, 30% off) and single card Saturday (25% off, 2 more rares). The shop shows sale prices with the usual one
  struck through.
- **The weekly tournament:**
  - **Entry:** at the arena on Saturday or first thing Sunday, for 500 coins.
  - **The draw:** 7 CPUs per save and week, those who haunt the arena three times as likely.
  - **Rounds:** Sunday morning, noon and evening, each a real duel against the player's opponent. The opponent stands
    at the arena for it, and the talk box's Duel says "tournament Round 1".
  - **CPU against CPU:** coin flips.
  - **Prizes:** a loss (or a missed round) knocks the player out with that round's prize; the champion takes 3,000 and
    a lucky pack. The normal duel payout doesn't apply.
- **Staff testing:** test mode's "Jump to" passes time to the next morning of a weekday.

Built next:
- **The map** marks places with an event on now (its icon).
- **The time-passing animation** names the events on as the new time of day comes in.
- **The `event` quest objective:** `{"do": "event", "event": key, "result": "enter" | "round" | "win", "count": n}`,
  counted by the tournament.
- **A sleeve condition:** "World mode events won" (`world_events`, counted when the player wins the tournament).
- **Timed quests:**
  - **The window:** `window` on a quest is written like an event's calendar (`weekdays`, `times`, `every`,
    `offset`; `{}` is all week) or tied to an event (`{"event": "weekly-tournament"}`).
  - **Offering:** it's offered only while the window is open, once a week.
  - **Expiry:** under way when the window closes (or the week ends), it **expires**. That's a new status that closes
    nothing, and it's on offer again next time.
  - **Repeats:** done, it's offered again next week, and the log counts how many times.
  - **Limits:** a timed quest can't gate a rank or close anything.
- **Board quests** (`board: true`, no giver): taken and claimed on the notice board ("Pinned to the board"). Their
  endings need no `to`.
- **The first board quests** (migration 0063):
  - three weekly bounties: beat three different duelists (400 coins), beat a villain (300), win a high-stakes duel of
    300 or more (a climax pack);
  - "Tournament day", on the board only for tournament weekend: win a round (300).
- **The quest log** shows when a timed quest ends ("Ends Sunday night") and how many times one's been done.
- **The prize-giving scene's hook:** a tournament's settings can name `champion_scene`, which waits in the town for
  the champion. It isn't written yet (below).

Not built yet:
- The other events (the list below): friendship day, night market and rival's challenge are the small ones.
- Rotating bounties: every bounty is on the board every week. A larger pool, each on some weeks (the window's
  `every` and `offset`), would keep the board fresh.

## Writing to do

Nothing here is written yet. Each item says where it goes and how much of it there is.

### The weekly tournament

- **The prize-giving scene** ("World: Tournament, Champion"):
  - **When:** it plays for the champion on Sunday evening, after the final. Name it in the tournament's settings as
    `"champion_scene"` (staff Events page) once it exists.
  - **What:** about 6–8 lines at the arena (`background arena`, or `night`). The trophy, the crowd, the player's name
    called.
  - **Cast:** none fixed. The final opponent changes every week, and a scene casts by name, so it's a narrator scene,
    or one that casts a fixed host. A host would be a new character, or an existing CPU who doesn't enter.
- **Tournament chatter** (contexts `tournament_spectator`, `tournament_entrant`, `tournament_out`,
  `tournament_champion`, `tournament_duel`; built-in lines exist): one line of each per CPU, in its voice. That's up
  to 5 × 75 lines. It'd go in `world_pack/src` as new `lines` keys, so `build.py` would need keys for them, as it
  has for `hello` and `bye`.
- **The tournament's `about`** (the Events page): the notice board's description. It's functional now, and could use
  a line of flavour.

### The notice board

- **The bounties' wording** (migration 0063: `bounty-three-duelists`, `bounty-villain`, `bounty-high-roller`,
  `tournament-day`): each title, `about` and stage text is a first draft. Better wording goes in through the staff
  quest editor (or a new migration).
- **A pool of bounties** to rotate: about 12, each with a window's `every`/`offset` so 3–4 are up each week. Ideas:
  - win with a one-color deck;
  - win a duel at night;
  - beat a CPU you've never duelled;
  - win three duels in a row;
  - collect 10 cards with a trait;
  - give three gifts.
  Each needs a title, an `about` (one sentence, in the voice of whoever pinned it up), and a stage text.
- **Timed quests from CPUs** (a CPU as giver, with a window): "a weekly favour". For example, "Give Tohru something
  sweet before Friday". One per CPU would be 75 small quests, each an offer line or two and a thank-you ending
  script. Optional: start with the pilot six.
- **The board's own text:** the page's empty state ("Nothing pinned up right now…") and section titles are written
  plainly, and could be given the town's voice.

### Sales

- **The sales' `about` lines** (the Events page) are functional. If the shop ever has a shopkeeper, each sale wants
  an announcement line. There's no shopkeeper character yet.

### Holidays and seasons (the calendar's ready: `dates` and `months` on an event)

Each holiday needs: an event (name, icon, `about`, its date), its effect (a sale, a festival, doubled friendship), a
notice for the board, and **optionally** a short scene per arc and a chatter line per CPU (a new chatter context, such
as `holiday`).

| Date | Holiday | Suggested effect |
|---|---|---|
| 11-18 | The save's anniversary (from Year 2) | A gift from every CPU at Close friend or above |
| 12-24 / 12-25 | Christmas Eve and Christmas | Gift points doubled, a winter scene at the plaza |
| 01-01 | New Year | A shrine visit (a `visit` scene), a lucky pack |
| 02-14 | Valentine's Day | Sweet gifts loved by everyone |
| 03-14 | White Day | Return gifts from CPUs given something on 02-14 |
| 07-07 | Tanabata | Wishes at the shrine (a talk with a choice) |
| 10-31 | Halloween | A night market at the plaza; villains out by day |

**Seasons** (`season_of`): seasonal backdrops for places, and seasonal gift stock, need art or item lists, not
writing.

### Other events, when they're built

- **Rival's challenge:** for each villain (12), a challenge line and a defeat line.
- **Night market:** 6–10 market-only gift items, each a name, icon, `about` and tags.
- **Friendship day:** one `event` chatter line per CPU (optional; the built-in line covers them).
- **CPU birthdays:** a birthday for each of the 75 CPUs, plus a birthday line, and optionally a scene, per CPU.

## What's there already

- **Total game time is already kept.** `WorldSave.turn` counts every time of day since the save began. Day
  (`turn // 4`), weekday (`day % 7`) and time of day (`turn % 4`) all come from it, so a week is `day // 7`. Nothing new
  has to be stored to know "when" it is.
- **Things that already depend on time, and that events will reuse:**
  - the day's cast (`world.day_cast`), drawn from the seed and the day, so a reload never changes it;
  - the shop's stock and single cards, which change each day (`shop_stock`, `shop_cards`), and a requested set's days;
  - putting a CPU at a place for one time of day (`world.meet`, used by quest scenes);
  - the duel hook (`world.game_finished`), which pays out and moves time on.
- **Quests have no deadlines** (phase 6). Timed quests below are a separate kind that never gate a rank, so that
  decision still holds for the friendship quests.

## The framework

### 1. A calendar: when events happen

A new model, **`WorldEvent`**, one row per recurring event, edited by staff on the World mode tab:

| Field | What it's for |
|---|---|
| `key`, `name`, `about`, `icon` | What it is, as the town and the notice board show it |
| `kind` | Which rules it runs: `sale`, `tournament`, and later the others below |
| `weekdays`, `times` | When in the week it's on (as haunts are written: 0 Monday… 6 Sunday; 0 morning… 3 night) |
| `every`, `offset` | Every week (1), every other week (2), and so on; `offset` shifts which weeks |
| `first_week` | It doesn't start before this week of a save (so a new save isn't swamped) |
| `place` | Where it happens, if anywhere (the arena for a tournament; none for a sale) |
| `settings` | The kind's own numbers, as JSON (a sale's discounts; a tournament's fee, prizes and size) |
| `enabled` | Staff can switch an event off without deleting it |

Working out what's on is a pure function of the save and the turn, like who's where: **`events.on(save, turn)`** returns
the events running at that time of day, and **`events.week(save)`** returns the week's calendar. A reload never changes
either, and two saves see the same calendar (the rules are global), with seeded details (which set is on sale, who
enters) differing per save.

### 2. What a save remembers

A new JSON field on the save, **`WorldSave.events`**: `{event key: {"week": n, ...the kind's own state}}`. It's cleared
for an event when a new occurrence starts, so it stays small. A tournament keeps its bracket and the player's run there;
a sale keeps what was bought on the day, where a sale has a limit.

### 3. How the town shows it

- **The notice board** (at the plaza, and as a "This week" button by the map): the week's events, each with day, time,
  place and what it costs or pays. Today's are first. Upcoming ones say "in 2 days", and finished ones fade.
- **A banner over the stage** when an event is on now or later today ("Tournament at the arena tonight: entry
  closes at noon"), dismissible like quest news.
- **The map** marks a place with an event on now (an icon on its card).
- **The passage of time** names an event that just started ("Sunday morning: tournament day").

### 4. Hooks into what exists

- **Prices** go through one function, `world.price(save, what)`, instead of reading the settings directly. Sales
  adjust it, and the shop shows the old price struck through.
- **Who's where:** an event can put CPUs at its place for its times, through the same mechanism as `world.meet`
  (generalised to "a list of overrides for this turn"). So tournament entrants stand in the arena.
- **Duels:** `game_finished` hands an event's duel to its kind (a tournament round) before the normal payout.
- **Quests:** two new objectives, `event` ("enter / win this event", optionally N times) and the timed quests below.
- **Sleeves:** a new condition, "Won a world event" (with a particular event, optionally).

### 5. Staff tools

- **An events page** (World mode tab): the events, each with a calendar preview for a sample save, edited like
  places.
- **In test mode:** a "Jump to…" control in the town bar (next Sunday, next event), so an event can be tested without
  passing 28 times of day. It moves the save's turn forward and runs everything time passing runs.

## Event 1: sale days

Shop days with prices cut, so players have a reason to save coins for a day.

- **What a sale is:** a discount on one thing or more, for the day or one time of day:
  - `packs`: every pack, or one featured set (seeded per save and week, from the sets the shop can get);
  - `specials`: specialty packs, or one kind (climax packs, say);
  - `cards`: single cards, with an extra card or two on the rack that day;
  - `gifts`: gift items, or one tag ("sweets day").
- **Proposed starting calendar:**

  | Day | Sale | Discount |
  |---|---|---|
  | Wednesday | Featured set: one set's packs (it's put on the shelves if it isn't) | 50% |
  | Friday evening | Specialty pack happy hour | 30% |
  | Saturday | Single cards: two more rares on the rack | 25% |

- **Limits**, so a sale isn't just "buy everything then": a sale can cap how many a save buys of the discounted
  thing that day (say 5 featured packs). The shop shows "3 of 5 left today".
- **Showing it:** the sale price with the old price struck through, a "Sale" tag on the item, and the banner in the
  shop's own header ("Featured set: half price today").

## Event 2: the weekly tournament

A Sunday at the arena: an entry fee, three rounds against CPUs, a big payout, and friendship with everyone who took part.

### The shape of the day

| Time | What happens |
|---|---|
| Saturday (any time) | Registration opens at the arena: pay the entry fee (proposed 500). The bracket is drawn when the player enters. |
| Sunday morning | Round 1 (quarter-final) |
| Sunday noon | Round 2 (semi-final) |
| Sunday evening | The final |
| Sunday night | Prize-giving at the arena: a short scene, the prizes, friendship with the entrants |

- **8 entrants:** the player and 7 CPUs drawn for that save and week, weighted towards CPUs whose haunts include
  the arena, never someone a quest sent away.
- **Each round is a real duel** against the player's opponent, started from the arena at that time of day. It uses
  the time slot, as any duel does.
- **The other matches** (CPU against CPU) are decided by a seeded roll, weighted by a strength rating for each CPU.
  The ratings could come from `cpu_selfplay` win rates, worked out offline and stored on the CPU profile. The roll is
  made when the round starts, so a reload never changes a result.
- **Losing** knocks the player out. They keep any round prizes, and can still watch the rest: the bracket fills in
  as time passes.
- **Missing a round** (not at the arena at that time) is a forfeit, which counts as a loss.
- **Entrants are at the arena** for the tournament's times, through the presence override, so the player can talk to
  them between rounds.
- **The bracket** shows on the notice board and in the arena all day: who's in, who's through, and the player's
  next opponent.

### Prizes and friendship (proposed)

| Result | Coins | Also |
|---|---|---|
| Win the final | 3,000 | a lucky pack, and a "tournament champion" sleeve condition |
| Lose the final | 1,500 | |
| Lose a semi-final | 600 | |
| Lose in round 1 | 0 (the fee's gone) | |

- **Friendship:** every CPU who entered that week gets points with the player (proposed +4, scaled by temperament as
  usual). Each opponent the player actually duelled gets more (+8 win or lose, on top of the duel's own points).
- **Rank-ups** reached this way play as they do after any duel: in the result banner, with the scene waiting.

### Rules that follow from what exists

- **It's a duel each time of day,** so "spending the time" and the map after time passes work unchanged.
- **The equipped deck is the one used,** checked when the player enters (it must be legal) and at each round.
- **Unfinished round:** as with any duel, the time is held until it's finished; conceding is a loss.
- **High stakes don't apply** to tournament rounds.

## Timed quests

Quests that are only on offer for a while, and repeat. They never gate a friendship rank.

- **A `window` on the quest's spec:** when it's offered and how long it can be done, written like an event's
  calendar (`weekdays`, `times`, `every`) or tied to an event (`"event": "weekly-tournament"`).
- **Offered only inside the window.** It's under way until the window ends; if it isn't finished by then, it
  **expires**. That's a new status, not `failed`, so it closes nothing, and it's offered again next time.
- **Repeatable:** rewards come each time it's finished (once per occurrence), and the log keeps a count ("Done 3
  times").
- **Who gives them:** a CPU (as now), or **the notice board** (no giver), so events can carry quests without a
  particular CPU.
- **In the quest log:** a "This week" section, with how long is left ("ends Sunday night").
- **Examples:**
  - "Beat 3 different CPUs this week" (bounty board, 400 coins).
  - "Win a round at the tournament" (Sunday).
  - "Give Tohru something sweet before Friday" (a CPU's own weekly favour).

## Other events to consider

Ranked by how much they'd add for how much work. Each uses the framework above; none needs a new engine feature
unless it says so.

| Event | When | What it does | Work |
|---|---|---|---|
| **Bounty board** | Weekly, posted Monday | Three timed quests at the notice board ("beat a villain", "win with a green deck", "win a high-stakes duel"), coins for each, a pack for all three | Small: timed quests only |
| **Friendship day** | One day a week | Talk and gift points doubled; CPUs say an `event` chatter line | Small: a points multiplier and a chatter context |
| **Night market** | Friday night, plaza | Gift items you can't get at the shop, and a gift sale | Small: event-only gift stock |
| **Rival's challenge** | Weekly, a rotating villain | A villain takes over the arena for an evening: a high-stakes boss duel at a big fee and prize, and points with them | Small: an event-placed CPU and a stake |
| **New set launch** | When staff add a set | The set is featured in the shop for a week, with a promo card for the first box bought | Medium: needs a "set added" trigger |
| **Card trade fair** | Every other Saturday, shop | Trade in duplicates (say 4 spares) for a card of your choice from a list | Medium: a trade screen |
| **Weekly league** | All week | Standings by wins against different CPUs. Top of the table on Sunday night wins a prize, and CPUs "play" each other in the background | Medium: CPU results like the tournament's |
| **Shrine festival** | Every fourth week, shrine, evening and night | Festival stalls (gifts, a lottery), CPUs gathered at the shrine, each with an `event` line, and a short festival scene per arc | Medium: writing, plus a once-a-month calendar |
| **Weather** | Seeded per day | A rainy day empties the beach and fills the cafe and library (it changes the day's draw weights) | Medium: haunt weights by weather |
| **CPU birthdays** | Once a year per CPU | Loved gifts count triple; a birthday line and a small scene | Needs a year (below) |
| **Sealed tournament** | Monthly | Open 6 packs of one set at the door and duel with only those cards | Large: a temporary pool and a deck from it |
| **Tag duels** | Any | 2v2 with a CPU partner | Large: needs the engine to support it |

### A calendar longer than a week

Weeks need nothing new. Monthly and yearly events (the festival, birthdays) need a calendar on top of `turn`. A
proposal: 4 weeks a month, 12 months a year (336 days), each month with a name and a season, all derived from `turn`.
It's worth deciding before any yearly event is written.

## The order to build it

1. **The framework:** `WorldEvent`, `events.on`, `WorldSave.events`, the notice board and banner, `world.price`,
   presence overrides, and the staff events page with "Jump to…". With tests for the calendar (it never changes on
   reload, every N weeks, first week) and for prices.
2. **Sale days:** the three proposed sales, limits, and the shop's sale display.
3. **The tournament:** entry, bracket, CPU results, the three rounds through `game_finished`, prizes, friendship, the
   prize-giving scene, and forfeits.
4. **Timed quests:** `window`, the `expired` status, repeats, the notice board as giver, and the "This week" log
   section. The bounty board comes with it.
5. **The next events:** picked from the list above.

**Done when:** a save sees the same week's calendar on every reload. A Wednesday sale cuts the featured set's price
up to its limit. A player can enter the Sunday tournament, duel three rounds, be paid by result, and gain friendship
with every entrant. A timed quest expires without closing anything and is offered again the next week.

## Decisions needed

- **Tournament numbers:** entry fee (500?), prizes (3,000 / 1,500 / 600?), size (8, three rounds?), and whether the
  rounds use the whole of Sunday.
- **Friendship from the tournament:** points for every entrant, or only those the player duelled? (The plan does both,
  with more for opponents.)
- **CPU-against-CPU results:** a weighted roll from strength ratings, as proposed, or something simpler (a fair coin)?
- **Sales:** are the three proposed days right? Should sales have limits?
- **A longer calendar:** should there be months and seasons now (for festivals and birthdays), or later?
- **Which other events to build first:** my suggestion is the bounty board (it comes with timed quests), then the
  rival's challenge and the night market. All three are small, and each uses a different part of the framework.
