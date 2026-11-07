# Co-op infinite challenge: plan

Two players play one infinite challenge together. They share a card pool and a path, each fights their own CPU
on every battle floor, and every lost game adds to a shared loss counter. The run ends when the counter reaches
the limit staff set.

## Decisions

| Topic | Decision |
|---|---|
| Joining | The host starts a co-op run and invites a partner by link. If either player leaves, the run waits for them. There are no timeouts. |
| Packs | Each player has their own packs to open: starting packs, loadout and win rewards. Every card opened goes into the shared pool. |
| Staff settings | Co-op has its own settings, apart from solo: loss limit (default 3), and starting packs and loadout per player. |
| Decks | Each player builds their own deck from the shared pool. A copy in one deck can't be in the other. A player can only add copies that aren't in either deck. |
| Battle floors | Each player fights the floor's CPU in their own game. Every loss adds 1 to the shared counter, so a floor can add 0, 1 or 2. Each win brings that player the usual reward. |
| Choices | Both players vote: on the next floor, on each event choice, and on event pick-one offers. If they agree, that's the choice. If they disagree, a coin flip picks one of their two votes. |
| Finishing first | A player whose game ends first can open packs, edit their deck, view the run screen and vote on the next floor. Nothing moves on until both have voted. |
| Events | Both players see the same scene and vote on each choice. What it gives goes to both players. |
| Leaderboard | A separate co-op board lists both players by name, and both decks can be viewed. |

### Choices I made where the design was silent

These are noted here so they can be changed.

- **Second chance** in co-op: a loss is used up from that player's second chances and doesn't add to the counter, and the run still moves on.
- **Next-fight pacts** from an event apply to both players' next fight. They clear when the floor is finished.
- **End challenge**: either player can end the run, and it ends for both. **Reset** isn't offered in co-op.
- **At the end**, each player keeps or discards their own deck, as in solo.
- **Who can play:** every Weiss player can start or join a co-op challenge, as with the solo infinite challenge. Free and narrative challenges are still staff-only.

## How it's built

- A new **`CoopRun`** model holds the shared state:
  - host and partner, and the invite token
  - pool and path
  - each player's progress (how many floors they have finished)
  - votes, the loss counter and its limit (copied from settings at the start)
  - status, version (raised on every change, so pages can poll cheaply), score and decks for the leaderboard
- Each player has their own **`ChallengeRun`** (kind infinite) with `coop` pointing to the `CoopRun`. It keeps that player's own packs, rewards, deck, arcade run, last opening and second chances, as in solo.
- **The shared pool and path** live on the `CoopRun`:
  - `challenge.current()` loads them into the player's run, so read code is unchanged.
  - Every write goes through `challenge.shared(run)`, which locks the `CoopRun`, loads the latest pool and path, and saves them back.
- **Floors:**
  - The pair is on floor `min(progress)`. A player who finishes their game goes to `progress + 1`, and can vote on that floor straight away.
  - A floor's pick is made once both players have voted on it.
  - The path is laid ahead of the player who is furthest along.

## Steps

1. **Models and staff settings**
   - `CoopRun`, `ChallengeRun.coop`, and the co-op fields on `ChallengeSettings` (loss limit, start packs, loadout), with a migration.
   - A "Co-op" section on the CPU tab's Infinite form.
   - Tests.
2. **Starting and invites**
   - The host starts a co-op run, which creates their `ChallengeRun` and gives them the co-op packs and loadout.
   - An invite link page: join (only with no challenge under way), or cancel before anyone has joined.
   - The partner gets their own packs and loadout on joining.
   - The challenge page shows the partner and waits until one has joined.
   - Tests.
3. **Shared pool and split decks**
   - `current()` and `shared()`. Pack opening, reward claims and buffs write to the shared pool under the lock.
   - `save_deck` refuses copies the partner's deck uses. The deck builder shows how many copies are free.
   - Taking cards out of the pool (exchange, trade-in, reforge, sacrifice) trims whichever deck can no longer have them: the player's own deck first, then the partner's.
   - Tests.
4. **Path and voting**
   - Per-player progress, and votes per floor, resolved by agreement or coin flip.
   - `floor_at`, `path_of`, `choices` and `pick` changed for co-op.
   - The path on the challenge page shows both players' votes and lets each player vote.
   - A fight only starts on a floor that has been picked.
   - Tests.
5. **Battles and the loss counter**
   - A co-op branch in `fight_finished`: the player's progress goes up, and a loss uses a second chance or adds to the counter.
   - Reaching the limit ends the run for both players.
   - Wins bring that player's own reward.
   - Next-fight pacts clear when both players have finished the floor.
   - The challenge page polls the `CoopRun` version and shows a waiting note, the partner's status and the counter.
   - Tests.
6. **Events together**
   - The event scene is played on a co-op event page. At each choice, both players vote and the page waits for the result (agreement or coin flip). Both pages then follow the same branch.
   - At the end, the scene's gifts go to both players.
   - Tests.
7. **Ending and leaderboard**
   - Either player can end the run, and it ends for both. Each player then keeps or discards their own deck.
   - A co-op leaderboard tab (both players, floor, combined score) with both decks viewable.
   - Tests.
8. **Finish**
   - The game page's arcade header shows the loss counter in co-op.
   - Docstrings, the full test run, and a check in the browser with two accounts.

## Progress

- [x] 1. Models and staff settings
- [x] 2. Starting and invites
- [x] 3. Shared pool and split decks
- [x] 4. Path and voting
- [x] 5. Battles and the loss counter
- [x] 6. Events together
- [x] 7. Ending and leaderboard
- [ ] 8. Finish: game page loss counter, docstrings and full test run done; the browser check with two accounts is still to do
