# Duel music, version 2: songs that build with the duel

The first version split each song into three parts (drums, bass, melody) and changed their volume by about 1 dB per level.
That isn't audible, and the drum-only songs had nothing to change. Version 2 makes every change a part you can hear.

## The songs (kept by the user; this list stays for a while)

| Key | Name | Kind |
|---|---|---|
| lofi | Lo-fi | synth |
| rock_3 | Rock | synth |
| rock_4 | Groove | synth |
| hip_hop | Hip hop | synth |
| jazz | Jazz | synth |
| funk | Funk | synth |
| synthwave | Synthwave | synth |
| emo | Emo | synth |
| metal | Metal | synth |
| cc0_1 | CC0 drums 1 | samples |
| cc0_3 | CC0 drums 3 | samples |
| cc0_4 | CC0 jazz | samples |
| cc0_5 | CC0 hip hop | samples |
| cc0_6 | CC0 funk | samples |
| cc0_7 | CC0 emo | samples |
| cc0_8 | CC0 metal | samples |

Deleted by the user, and not to be worked on: rock_1, rock_2, cc0_2. Names are the user's (the music page's MusicTrack table).

## What drives the music in a duel

| Driver | Rule | Lasts |
|---|---|---|
| **Tier**, 0 to 6 | Starts at 0. Goes up by one every time either player levels up (the two players' levels added, at most 6). | For the rest of the duel: it never goes down. |
| **Climax** | On while a climax card is in either player's climax zone. | Until the climax leaves the zone. |
| **Splash** | A short burst on every activated ability and every sound-effect cue the duel plays. | About one bar, starting on the next beat. A new splash during one restarts it; they don't stack. |

| **Match point** | On while either player is one level from losing (1 life: three level cards). The life-based rule from version 1, kept by the user. | Until neither player is at match point (in practice, the rest of the duel). |

At match point the music is raised to at least tier 5 (drive on), and a **tension** layer comes in: a heartbeat pulse
and a rising string swell, in the song's key. The tier, climax and splash work as before on top of it.

## The layers (every song has all of them)

| Layer | What it is |
|---|---|
| core | Kick and snare: the song's backbeat. |
| top | Hats or ride. |
| bass | The bass line. |
| chords | Pads, keys or rhythm guitar: the harmony. |
| lead | The melody. |
| extra | A counter-melody, an arpeggio, or percussion. |
| drive | Busier drums (ghost notes, sixteenth hats, crashes on the bar) and a doubled bass. |
| tension | Match point only: a heartbeat pulse (two kicks a beat apart, quiet) and a string swell rising over each two bars. |
| climax | Its own layer: double-time drums, a riser or swell, and the lead an octave up, or the song's equivalent. Only on while a climax is on the field. |
| splash | A one-bar stinger in the song's style: a fill and a crash, or a stab. One-shot. |

Tier map (the same for every song, so the tiers mean the same thing everywhere):

| Tier | Layers on | In the duel |
|---|---|---|
| 0 | core, bass | The duel starts |
| 1 | + top | First level-up |
| 2 | + chords | Second |
| 3 | + lead | Third |
| 4 | + extra | Fourth |
| 5 | + drive | Fifth |
| 6 | everything, louder | Both players at level 3 |

Each tier must sound clearly different from the one before it. A layer comes in on the next bar, with a short fade, so
it doesn't cut in mid-phrase.

## Sound

- **Real drums everywhere.** The synth songs play the CC0 kits' drum hits (one-shots exported to music/kit/), not
  synthesized drums. Their bass, chords and leads stay synthesized for now.
- **Sample songs.** The CC0 songs are rendered with all nine layers from free samples (CC0 first; CC-BY where a CC0
  instrument doesn't exist, credited in LICENSES.md).
- **Sound effects** stay per song, as in version 1.

## Testing on the staff music page

For each song, the page has: a **tier** slider (0 to 6, each stop named), a **climax** on/off switch, a **splash**
button, and a row of the song's **sound effects**. Every state the duel can reach can be heard from the page.

## Who

- **Me (World Planner):** the CC0 songs' layers, rendered from samples; more free instrument sources (bass guitar,
  guitars, keys); the one-shot drum kit for the synth songs.
- **Sam 2 (engine, audio.js):** layers by name for any song; the tier map; the climax layer; the splash stinger on the
  next beat; the crossfade; the synth songs rebuilt to all nine layers on the real drum kit.
- **Tucker (server):** the duel's state: each player's level (or the tier), whether a climax is on the field, and a
  count of activated abilities, so the page can splash once per activation. Tests for each.
- **Sam (pages, play.js):** the duel's wiring (tier, climax, splash on each ability and sound effect), and the music
  page's test controls.
