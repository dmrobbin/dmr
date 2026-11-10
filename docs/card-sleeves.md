# Card sleeves

A player's card sleeve is how their face-down cards look in a game (deck, stock, the hand their opponent sees, face-down
markers), on their side of the board and to their opponent. Three come built in and everyone has them; staff upload
more, each unlocked by conditions they set, or given to a player by hand.

## Decisions

| Topic | Decision |
|---|---|
| Whose | A player's, chosen on their profile (Card sleeves). One for every game. A CPU's is set on its profile page (Card sleeve), for its side of the board. None chosen: Classic. |
| Built in | Classic (the board's old card back), Midnight (navy, silver lattice), Crimson (dark red, gold seal). Drawn by CSS, no images. They can be renamed, hidden or given conditions like any other, but not deleted. |
| Uploaded | Staff choose a picture and drag and zoom it in a card-shaped frame. What the frame shows is saved at 500×700 (WebP), in the S3 bucket under `sleeves/`. Replacing the picture deletes the old file. |
| Conditions | Any number, needing all of them or any one. With none, everyone has it. The kinds are listed below. Some can be limited to one CPU, arcade list or narrative challenge, or left open to any. |
| Counting | Only what's done from launch onward: nothing from before counts. A sleeve added later unlocks for those who've already met it since launch, at their next game or the next time they open their profile. |
| Hidden | Not offered: nobody new unlocks it, and only those who have it see it (and keep using it). Staff can still give it out, which makes it a staff-only reward. |
| Giving and taking back | Staff give a sleeve to a player by username, whatever its conditions. Taking it back puts them back on Classic if they were using it. They'd unlock it again by meeting its conditions; hide it or change them to stop that. |
| Telling the player | The Victory screen shows a sleeve the game unlocked. On Weiss pages a banner shows new ones (unlocked or given) until the player opens their profile or dismisses it. On the profile, locked sleeves show each condition with a progress bar. |

### Kinds of condition

| Kind | Counts | Can be limited to |
|---|---|---|
| Games won, against anyone | Each win, against a CPU or a player | |
| Games won against CPUs | Each win against a CPU | A CPU |
| Flash battles won | Each win of an infinite challenge's flash battle | |
| Arcade lists cleared | Each clear in arcade mode (not a challenge's) | An arcade list |
| Score in one arcade run | The best run score, after each win | An arcade list |
| Free or narrative challenges cleared | Each one won | A narrative challenge |
| Floors climbed in one infinite challenge | The highest floor won, solo | |
| Score in one infinite challenge | The best run score, solo | |
| Infinite challenge bosses beaten | Each boss beaten, solo or co-op (in co-op, only once its health bar is empty) | |
| Floors climbed in one co-op challenge | The highest floor won | |

Floors count when a fight on them is won. A floor passed through an event counts at the next win.

## How it's built

- **Models:** `Sleeve` (`style` for a built-in one's CSS look, or `key` for an uploaded picture; `conditions`,
  `match`, `hidden`), `SleeveUnlock` (a player has it; `awarded_by` if staff gave it; `seen`), and
  `PlayerProfile.sleeve`, `PlayerProfile.progress`, `CpuProfile.sleeve`. Migration 0039 adds the three built-in ones.
- **Progress** (`weiss.sleeves`): `progress` is `{key: number}`, a key being a kind, or `kind:target id` for the same
  done against that one. `play.game_ended` calls `sleeves.game_ended` once a game is over, with the arcade run and
  challenge as they were. It works out the counts and bests, and `sleeves.record` adds them under a row lock, then
  `sleeves.check` unlocks whatever is newly met. What a game unlocked goes in `game_over["sleeves"]`, and
  `play.board_payload` hands each player theirs as `unlocked`.
- **On the board:** `Sleeve.css` is a CSS background (`var(--sleeve-midnight)`, or the picture's `url()`).
  `board_payload` (and the co-op spectator's state) sends `sleeves: {me, opponent}`. `play.js` sets them on the page
  as `--sleeve-me` and `--sleeve-opponent`, and `site.css` puts each on its side's `.pcard-back` through `--sleeve`.
  Card flights take the mover's.
- **Staff:** the CPU creation tab's Card sleeves tab (`cpu_sleeves.html`), and each sleeve's page
  (`weiss.sleeve_views`, `sleeve_edit.html`, `sleeve_edit.js` for the cropper and condition rows). The picture's
  link is `sleeves/<pk>/image/`, which redirects to a fresh S3 link, as CPU images do.
