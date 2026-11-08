# Infinite challenge: bosses and augments

Every few floors, the infinite challenge's path reaches a boss: a single fight in the middle of the path that
everyone has to take. Beating it gives a big reward, including an **augment**: a lasting change to the run that
pushes the player towards a playstyle. In co-op, both players fight the boss in their own games and wear down
one shared health bar.

Bosses come first. Augments are built after them.

## Decisions

| Topic | Decision |
|---|---|
| When | A boss floor every N floors. Solo and co-op each have their own N, both on the CPU tab's Infinite form. 0 turns bosses off for that mode. |
| Who the boss is | Staff mark CPUs as bosses on the CPU tab. Boss floors pick one of them at random. Boss CPUs don't appear on ordinary floors. If no CPU is marked, any CPU can be a boss. |
| The path | A boss floor has one space, in the middle, so every column leads to it. It never has an event. In co-op there's nothing to vote on. |
| How it plays | The boss plays at its hardest (hard model, highest aggression) and starts with 3 cards in its stock. |
| Solo | A boss is a fight to win, as any other. A loss uses a second chance, or ends the run. A win gives the usual win reward plus the boss reward. |
| Co-op health | The boss has one health total for the pair, set by staff (default 42). Every damage that lands on it in either player's game comes off it as it lands, refresh damage included. Damage cancelled by a climax doesn't count. |
| Co-op losing | A co-op boss doesn't lose at level 4: it keeps levelling up. It loses only when the health bar is empty. |
| Co-op refights | Until the boss is down, a player who lost to it can fight it again; the damage they dealt stays off. Every lost game still adds to the loss counter (or uses a second chance). |
| Co-op boss down | Both players finish the floor and get the boss reward. Any game still under way against it ends as a win (with a win's usual reward), the partner's on its page's next check. A loss in the same action that empties the bar doesn't count. |
| Boss reward | 3 packs and an augment pick, on top of a win's usual reward for the game that won. In co-op, the augment and curse picks come from the vs. battle after the boss instead (see [coop-vs-battles.md](coop-vs-battles.md)). |
| Augments | Personal. Each pick offers 3 the player doesn't have yet, and they keep one for the rest of the run. Lifeline is co-op only and is the only one that can be taken twice. Every augment helps the player; none holds back their opponent. |
| Curses | Beating a boss also brings a curse to take: 3 offered, one taken, for the rest of the run. It must be taken before the next fight. Personal, like augments. They stack, the same curse included. Every curse makes the CPUs the player faces stronger; none weakens the player, so a curse never just cancels out an augment. |
| Curse strength | Every boss carries the whole stack; every other CPU carries half of it, rounded down. |

### Choices I made where the design was silent

These are noted here so they can be changed.

- The boss's start (3 stock) and its reward (3 packs) are constants in the code, not staff settings.
- In co-op, a boss that can't refresh its deck still loses that game, but with health left it counts for nothing: no
  reward, no loss, and the floor isn't done.
- The partner's damage shows on a player's game page the next time their own game changes, not the moment it lands.
- The floor numbers stay as they are: a boss floor counts as a floor, like an event.
- When every augment has been picked, a boss gives 2 more packs in place of the augment pick.
- Every deck is held to exactly 8 climaxes: it can't be built with more, and it can't be played with fewer (ordinary
  games, arcade and challenge fights alike; a challenge deck can still be short of 50 cards). Climax Overload makes
  that 8 to 10. Challenge decks are still only warned about the 4-copy rule; Highlander's 2-copy limit is enforced.
- Halving rounds down, so a curse whose step is 1 (all but Iron Skin and Bulwark) does nothing to ordinary CPUs until
  it's been taken twice.
- A curse can be offered and taken again, however many the player has: with 7 curses, a long run would run out
  otherwise.
- Deep Pockets adds at most 4 cards to the CPU's starting hand.
- Recovery heals at the start of the CPU's draw phase, before it draws, and only what's in its clock.
- Bulwark only counts for the CPU character being front attacked, not side attacked (a side attack's damage doesn't
  depend on power).
- Curses aren't shown on the co-op partner's panel (augments are).
- Glass Cannon with only one second chance left: the loss isn't covered. In solo the run ends; in co-op, 2 go on
  the counter.

## The augments

| Augment | What it does | Built in |
|---|---|---|
| Climax Overload | The deck can run up to 10 climaxes instead of 8, and each win also gives a climax pick. | Run rules |
| Deep Reserves | Start each game with 2 cards in stock. | Game start |
| Devotion | If every card in the deck is one color, its characters get +1000 power. The win prize lands on a color pack more often. | Game rules + run |
| Head Start | Start each game with 1 more card in your hand. | Game start |
| Clean Refresh | The first refresh in each game deals no refresh damage. | Game rules |
| Highlander | The deck can't run more than 2 copies of any card. Each win gives 2 extra packs. | Run rules |
| Glass Cannon | Characters get +1 soul. Each loss counts twice: two on the co-op loss counter, or two second chances in solo. | Game rules + run |
| Low-Level Army | Level 0 characters get +1500 power. | Game rules |
| Counter Specialist | Counter cards cost 1 less stock (to a minimum of 0). | Game rules |
| Lifeline (co-op) | The pair's loss limit goes up by 1. It stacks. | Run |

## The curses

| Curse | What it does, per pick | Built in |
|---|---|---|
| Iron Skin | CPU characters get +1000 power. | Game rules |
| Fury | CPU characters get +1 soul. | Game rules |
| Hoard | The CPU starts each game with 1 more card in its stock. | Game start |
| Deep Pockets | The CPU starts each game with 1 more card in its hand. | Game start |
| Second Wind | The CPU's first refresh in each game deals no refresh damage (one more refresh per pick). | Game rules |
| Bulwark | CPU characters get +2000 power while they're front attacked. | Game rules |
| Recovery | At the start of each of its turns, the CPU heals 1 damage. | Game rules |

Deep Pockets, Second Wind, Bulwark and Recovery replaced Short Hand, Heavy Refresh, Toll and Old Wounds, which
weakened the player instead (migration `0037_curses_buff_the_cpu` moves runs that had them onto their replacements).

## How it's built

- **Settings:** `ChallengeSettings.boss_every`, `coop_boss_every` and `coop_boss_health`. `CpuProfile.boss`.
- **The path** keeps the floors it laid as bosses in `path["bosses"]`, so changing N partway through a run
  doesn't move bosses already laid.
- **The game** is stamped with the floor it was dealt for and whether it's a boss (`room.state["floor"]`,
  `room.state["boss"]`). That's how the CPU knows to play at its hardest, and how a co-op game against a boss
  that's already down is told apart.
- **Co-op health** lives in the shared path: `path["boss"] = {"floor", "health", "max", "dealt": {user id: damage}, "down"}`.
  The game counts the damage that lands on each side (`side["damage_taken"]`); after every action, `play.wear_boss`
  takes what's new off the health bar. The boss's side has `shared_health`, so `game.check_game_over` doesn't end
  the game at its level 4 and the CPU doesn't play safe near it.
- **Curses** live on `ChallengeRun.curses` (a list of ids, repeats and all; see `weiss.curses`). A curse pick is a
  reward like an augment pick; `challenge.curse_due` keeps the player from fighting until it's taken. When a game
  is dealt, `play.curse_start` works out their strength (full against a boss, half otherwise), deals those that
  change the start, and puts the rest on the CPU's side as `side["curses"] = {curse id: strength}`
  (`game.curse_stats`, `game.refresh`, `game.heal`). A game between two players has none.
- **Augments** live on `ChallengeRun.augments` (a list of ids). An augment pick is a reward like the others,
  with its 3 options settled when it's given. In-game augments are put on the player's side of the game state
  when it's dealt (`side["augments"]`, see `play.augment_side`), co-op vs. battles included, and the game rules
  read them from there.

## Steps

### Part 1: bosses

1. **Settings**
   - The three settings and `CpuProfile.boss`, with a migration.
   - A "Bosses" section on the Infinite form, and a Boss checkbox on the CPU form.
   - Tests.
2. **Boss floors on the path**
   - Every Nth floor is a boss floor with one boss in the middle, kept in `path["bosses"]`.
   - Boss CPUs only appear on boss floors, with the fallback when none are marked.
   - No vote in co-op when there's only one way to go.
   - The path shows boss floors and boss spaces.
   - Tests.
3. **The boss fight, and solo rewards**
   - The room is stamped with its floor and boss flag. The boss plays at its hardest and starts with 3 stock.
   - A solo win gives the boss reward.
   - Tests.
4. **Co-op shared health**
   - Damage from each game comes off the shared health. Refights until it's down.
   - When it's down, both players finish the floor and get the boss reward. Games still under way against it stop counting.
   - Tests.
5. **Showing it**
   - A health bar on the co-op panel and on the path, and in the game page's arcade header.
   - A "the boss is down" note in a partner's game that no longer counts.
   - Tests.

### Part 2: augments

6. **Augment picks**
   - `ChallengeRun.augments`, the augment list, the augment pick reward (3 options, claim one), and the boss reward giving one.
   - Augments shown on the challenge page, the partner's panel, and the game page.
   - Tests.
7. **Run augments**
   - Climax Overload, Highlander, Lifeline, Glass Cannon's double loss, and Devotion's color pack odds.
   - Tests.
8. **Game augments**
   - Deep Reserves, Head Start, Clean Refresh, Devotion's power, Glass Cannon's soul, Low-Level Army and Counter Specialist.
   - Tests.
9. **Finish**
   - Docstrings, the full test run, and a check in the browser.

### Part 3: curses

10. **Curses**
    - `ChallengeRun.curses`, the curse list, the curse reward (3 options, take one) given with the augment pick, and
      no fight until it's taken.
    - Their strength in a game, full or half, and the rules that read them.
    - Shown on the challenge page, the reward pick, and the game page.
    - Tests.

## Progress

- [x] 1. Settings
- [x] 2. Boss floors on the path
- [x] 3. The boss fight, and solo rewards
- [x] 4. Co-op shared health
- [x] 5. Showing it
- [x] 6. Augment picks
- [x] 7. Run augments
- [x] 8. Game augments
- [ ] 9. Finish: docstrings and the full test run done; the check in the browser is still to do
- [x] 10. Curses
