# CPU style guide

A first draft, written from the site's code before the production CPUs were exported. **Staff: go through
`corpus/` and replace everything marked TODO with how your best CPUs actually read.**

## Model examples

TODO: the 8–12 CPUs, and 10–15 scenes, that are the standard to match (by file name in `corpus/cpus/`), and
what makes each one good. Until this is filled in, take examples from the same series.

## Content rules (not negotiable)

- Many of these characters are minors, or look young. Nothing romantic, flirtatious or suggestive, ever,
  whatever the source material does. Rivalry, friendship, teasing, pride and competitiveness are all fine.
- Stay true to the character: their way of speaking, what they care about, who they know. When unsure, keep it
  general and say so, rather than invent lore.
- No real people, no slurs, nothing cruel aimed at the player.

## Profile texts

- `intro_text`: TODO length (e.g. 1–2 sentences). Sets up the match in the character's voice; may use the
  series' own terms.
- `player_win_text` (the player beat it): TODO. Gracious, sore, or vowing a rematch, as suits the character.
- `player_lose_text` (it beat the player): TODO. Short; it won.
- `combo_text`: TODO. A short shout as it plays its combo, ideally tied to the anchors or their climax.
- `{player}` is the player's name in scenes; TODO whether the profile texts use it too.

## Model and aggression

TODO: confirm. A suggested default until then:
- `standard` and aggression 1 for most CPUs.
- `focused` for a deck that lives or dies by its combo, or a character known for single-mindedness.
- `strategic` or `hard` for a rival or boss character; `easy` for a beginner-friendly or comic one.
- Aggression above 1 for characters known for rushing in.
- `boss`: only when asked.

## Scenes

- Naming: TODO (e.g. "<CPU>: <title>"). Infinite challenge events are "Event: <title>".
- Length: TODO (e.g. 10–30 lines). A click per line of speech, so keep lines short.
- Start with a `background`, then bring the cast on with `enters`. Use pictures (`(win)`, `(lose)`, `(intro)`)
  to show feeling, and the odd animation, not one on every line.
- A choice should matter: a different reply, a flag used later, or a buff. TODO how often scenes give buffs, and which.
- Only `fight` a CPU that's in the arcade list the scene plays in.
