# Co-op challenge: vs. battles

After each boss in a co-op challenge, the two players play each other once. It's a break from fighting CPUs and a
way to compare the decks they've built. It also has a stake: the winner picks their augment and curse first.

## Decisions

| Topic | Decision |
|---|---|
| When | After every boss, once the boss is down. The pair's next fight, and any event, waits until the battle is played and both have taken their curse. |
| The decks | Each player's challenge deck, as it is once both have clicked Ready. Players can open packs and change decks before readying. A player whose deck stops being ready before the game is dealt is made unready. |
| Augments and curses | Each player's augments apply, as they do against a CPU. Curses don't: they only make CPUs stronger. |
| Losses | Neither loss counts: not on the pair's loss counter, and no second chance is used. |
| Ending | One game, no rematch. Either player can concede from the board's side panel. There's no timeout: a partner who never readies or never finishes holds the pair up, as anywhere else in co-op. |
| The picks | Beating the boss offers 3 augments and 3 curses, the same to both players, in place of each player's own augment and curse picks. The augments are ones both players could take. On the shared screen the winner takes one of each first. Theirs are marked as taken, and the loser takes one of each from what's left. With no augment left for the loser, they get 2 packs instead. |
| Picks stay personal | Every augment only helps the player who took it, and every curse only strengthens the CPUs that player faces, so who picks first always matters. |
| The rivalry | The pair's wins against each other are counted for the whole run. They're shown on the vs. battle page, the co-op panel, the board and the co-op leaderboard. |

## How it's built

- **State:** `coop.start_duel` (called from `challenge.coop_boss_down`) puts `path["duel"]` on the shared path:
  `{"floor", "options", "augments", "ready", "room", "winner", "loser", "picks", "augment_picks"}`. The augments
  are `augments.shared_offer` of both runs. Once both have picked it moves to
  `path["last_duel"]`, for the page to show how it went. The rivalry is `CoopRun.duel_wins`, `{user id: wins}`.
- **Blocking:** `coop.duel_due` gives the message, and `challenge.curse_due` and `challenge_fight` check it.
  `challenge.beat_boss` grants a co-op player only the packs: no augment or curse reward.
- **The game:** `coop.ready_for_duel` deals a `GameRoom` with `coop_duel` set and no `arcade_run`. It's a plain
  two-player room, so nothing about it touches the run's losses or lives. `play.duel_augments` puts each player's
  augments on their side; no curses are dealt. Reset, start, delete before the end, and
  rematch are refused for it. `play.game_ended` calls `coop.duel_finished`, which records the winner and the tally.
  The `duel_concede` action ends it.
- **Pages:** `challenge_views.coop_duel` is the vs. battle page, with Ready before the game and the curses after it.
  It reloads on `coop_status`, and redirects to the table while the game is being played. `coop_duel_ready` and
  `coop_duel_pick` take the posts (`coop.pick_after_duel` takes both picks at once). The board's `duel` payload
  drives the side panel, the Concede button and the end screen's "On to the augments & curses".
