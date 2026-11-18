# CPU style guide

How the site's CPUs read, worked out from the 42 CPUs and 75 scenes exported on 2026-11-10, with staff's rules
where they've set them. Where the two differ, staff's rules win.

## Model examples

The standard to match. Read the closest of these before writing; when a series has CPUs of its own, read those too.

**CPUs** (files in `corpus/cpus/`): `frieren`, `megumin`, `ryuko-matoi`, `power`, `lord-genome`, `aang`,
`asuna-yuuki`, `denji`, `takina-inoue`, `albedo`.

**Scenes** (names in `corpus/scenes.json`):
- Crossovers: `aang/frieren`, `Ai/Cinder`, `Denji/Chisato`, `Kana/Yukari`, `Levi/Beast`, `LordGenome/Cinder`,
  `Power/Aang`, `Sayaka/Frieren`, `Takina/Levi`, `Yoko/Cinder`, `DIO/Cinder`.
- Two CPUs from the same series: `Madoka/Homura`, `Takina/Chisato`.
- Other: `Rescued From Tartarus`.

## Character notes

Which version of a character an existing CPU is, where the obvious guess is wrong. Their pictures show this version,
so scenes must match it.

- **Madoka**: Ultimate Madoka, the goddess who became the Law of Cycles. Not the schoolgirl: she appears from
  beyond time, watches over magical girls, and most people don't remember her (Homura does). See `LordGenome/Madoka`.

## Content rules (not negotiable)

- Stay true to the character: their way of speaking, what they care about, who they know. When unsure, keep it
  general and say so, rather than invent lore.
- No real people, no slurs, nothing cruel aimed at the player.

## Profile texts

One line each, in the character's voice, often nodding to their story (Frieren: "I once knew Himmel the hero.").
None of them use `{player}`. All four are required.

- `intro_text`: one or two sentences, about 55 characters (the longest is 233). A challenge or a greeting.
- `player_win_text` (the player beat it): one sentence, about 45 characters. Gracious, sore or wry, as suits them.
- `player_lose_text` (it beat the player): one sentence, about 50 characters.
- `combo_text`: short, about 18 characters (at most 80): a battle cry or a signature line. Always write one, even
  though 9 of the existing CPUs have none.

## Model and aggression

Both are chosen mostly to spread the difficulty across the roster, not from the character.

**Model**, from most to least common:
- `standard` and `strategic`: common. The default.
- `focused`: uncommon.
- `easy` and `hard`: rare.

**Aggression**: 1 by far the most common, each level above it much rarer than the one below.

How to choose: count the models and aggression levels across `corpus/cpus/` and pick what keeps the roster closest
to that spread. Today it's 14 standard, 14 strategic, 9 focused, 4 hard and 1 easy, so standard or strategic is
the usual pick, whichever suits the character; aggression is 30 at 1, 6 at 2, 3 at 3, 3 at 4 and none at 5. Use the character
to settle close calls: higher aggression for those known for charging in (Denji 3, Power 4, Simon 4). Say in the
summary why you chose what you did. Never make a CPU a boss unless asked.

For comparison, the existing CPUs by model:
- `standard`: Aang, DIO, Madoka, Kana Arima, Sol Badguy...
- `strategic`: Frieren, Ainz Ooal Gown, Erza Scarlet, Homura Akemi, Lord Genome, Asuna Yuuki...
- `focused`: Megumin, Levi, Albedo, Chisato Nishikigi, Ryuko Matoi, Ram/Rem...
- `hard`: Akane Kurokawa, Cinderella, Legendary Idol Ai, Ruby Rose.
- `easy`: Yoko.

## Scenes

73 of the 75 scenes are infinite challenge events (`infinite_event: true`): played at random on the challenge's
event spaces, not tied to a fight. The other two belong to an arcade list. A new CPU's scenes are events.

### How many, and with whom

- **3 scenes** for every new CPU, each with a different existing CPU.
- **Same series:** if any existing CPUs are from the new CPU's series, at least one of the 3 scenes pairs it with one of them.
- **Group scene:** if two or more existing CPUs are from its series, also write one scene with the new CPU and all
  of them together (up to 4 of them, since the stage has 5 places), named for the whole cast, e.g.
  `Takina/Chisato/Kana`. It's extra, not one of the 3.
- The rest are crossovers with CPUs from other series, favouring CPUs in few scenes so far.

### How they read

- **Crossovers.** 65 scenes cast two CPUs, nearly always from different series, meeting and finding common ground
  or clashing (Aang offers Frieren a lesson in bending; she offers magic). 7 are one CPU alone with the player.
  Every CPU so far is in at least one; most are in 2–6.
- **Names**: the cast's short names, `Aang/Frieren`; one CPU alone, just their name.
- **Length**: 22–52 lines, about 30.
- **Shape**, nearly every scene:
  1. `background` (city, ruins and forest most; then castle, cafe, crimson, shrine), the cast `enters`.
  2. A few exchanges in character; the player may speak a line or two (`player: ...`).
  3. One `choice`, usually 2 options, each going to its own label. The option's text ends with the reward in
     brackets, for the player to see, e.g. `- Kana was the star of the show! (lucky pack) -> kana_route`. That's
     only words: the reward is given by a `give` line in that option's branch.
  4. Each branch: a reaction, then `give <buff>` (every scene but one gives one), then `end`.
- **Buffs**, most given first: second_chance, lucky_pack, war_chest, extra_packs, reforge, climax_pack, level_pack,
  color_pack; pacts (outpaced, blood_pact, ambush, all_in, sacrifice) for darker characters or a tempting offer.
  Suit the buff to who gives it and why.
- **Staging**: an animation now and then to show feeling (bounce for joy, tremble or shake for upset, wobble when
  flustered, nod, glow), not on every line. Pictures (`(win)`, `(lose)`) rarely.
- `fight` is in only 7 scenes, and `offer` in 1: avoid them in events.

## World mode

What a CPU does in world mode's town, in its file's `world` part.

- **Schedule**: 3 or 4 rules. A home place on 4 or 5 weekdays at 2 times (chance 80–90, priority 1); a weekend place
  (Sat and Sun, 1–2 times, chance 70–80, priority 1); somewhere it wanders (2–3 days, 1 time, chance 50–60,
  priority 0). Places that suit the character: a scholar at the library, a fighter at the arena, an idol at the
  plaza. A stake (300–800) on one rule at most, for a character who'd gamble or a boss-like one.
- **Gift tastes**: one tag loved, two or three liked, one or two disliked, all from `world.json`'s tags. A loved tag
  should be one some gift has, or no gift is ever loved.
- **Chatter**, in the character's voice, short (1–4 lines each; a choice at most in a greeting):
  - `greet`: 3 lines: 2 for rank 0 (meeting a stranger), 1 for rank 2 or more (a friend).
  - `again`: 1 line.
  - `hello` and `goodbye`: 3 each, one spoken line apiece, for rank 0 (a stranger), rank 2 (a friend) and rank 4
    (a close friend), warming up as they go: said when the player walks up and leaves, every time, so keep them short.
  - `gift_loved`, `gift_disliked`: 1 line each (liked and neutral can use the built-in lines).
  - `before_duel`, `after_win`, `after_loss`: 1 line each, one spoken line apiece (only the first line is said). The
    profile's intro and win/lose texts are for games; these are the town's, shorter.
  - `rank_up`: one for rank 2 and one for rank 4, warmer each time. Give `points` only in a choice's branch, sparingly
    (+2 to +5); `give money` and `give gift` rarely, as thanks. `fight stake …` only for a character who'd bet.
- **Moods**: `them (pleased)` for happy, `them (dismayed)` for put out; the player's replies (`player:`,
  with no mood: they have no face in the box) are rare: chatter is mostly the CPU talking.
- **Quests** (`quests`, optional for now; reference.md has the format): when asked for them, two gate quests, one with
  `"gates": 2` (Friend) and one with `"gates": 5` (Best friend), since those rank-ups play scenes and should be
  earned. Each: an `about` in one or two sentences, an `offer` of 2–4 chatter lines in the character's voice, 1–3
  stages of 1–3 objectives that suit the character (a rival's `defeat`, a collector's `have_card` of a card from
  their own deck, a schemer's `talk` with a choice that sets a flag), and endings. Most quests have one ending; give
  a choice (and `locks` or `removes`) only where the story has a real conflict, and say why in the ending's `about`.
  `removes` is for the rare, dramatic case (one character finishing another): use it sparingly. Keep objectives
  winnable in a fair game: no luck-based feats.
- **`estranged`** chatter: one or two cold lines, said once a quest choice has closed this CPU's friendship.
