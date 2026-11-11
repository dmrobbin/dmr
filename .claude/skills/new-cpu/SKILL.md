---
name: new-cpu
description: Write a new CPU opponent (profile, deck anchors and scenes) for the Weiss Schwarz site as a file that import_cpu checks and loads, using the exported CPUs in corpus/ as examples. Use when asked to make, generate or draft a CPU, a CPU profile, or scenes for a CPU.
---

# Making a new CPU

You write one JSON file describing a CPU: its profile, the series and two anchor cards its deck is built
around (express building makes the rest of the deck), and its scenes. `import_cpu` checks it and loads it.
Pictures are chosen by staff afterwards, and staff finalize it.

## Input

Ask only for what you can't work out:
- **Series** (a code such as `NIK`): required.
- Optional: a character to build around, anchor cards, a model, whether it's a boss, how many scenes (default: STYLE.md's),
  and which existing CPUs to pair it with in them.

## Before writing

1. `corpus/reference.md` must exist. If it doesn't, stop: staff need to run `export_cpu_corpus` on production
   and copy its folder to `corpus/`. Read `reference.md` in full; it lists everything a file and a script can say.
2. Read `STYLE.md` beside this file. It overrides anything the examples do.
3. Find the existing CPUs from the same series: those in `corpus/cpus/` whose `deck.series` is the new CPU's. They
   decide the same-series and group scenes STYLE.md asks for.
4. Choose 3 or 4 examples: the same-series CPUs first, then STYLE.md's model examples closest to the new character.
   Read them whole, scenes included, and 2 or 3 of STYLE.md's model scenes from `corpus/scenes.json`.

## Choosing the anchors

Read `corpus/anchors/<SERIES>.json`: the cx combo cards a CPU can play in that series, with the climaxes they combo
with and `used_by`, the CPUs whose decks have them. No file means the series has none (or the export is older than
the series: say so). Use the serial numbers exactly as listed. Prefer:
- two anchors featuring the same character, or the character asked for;
- anchors no CPU uses yet (empty `used_by`), if there are two that fit;
- a combo whose climax is in the anchors' colors.

The CPU is that character. Its personality comes from the anchors' names, traits and flavor text and what
you know of the series. If you don't know the character well, say so in your summary instead of inventing lore.

## Writing the file

Write `corpus/new/<name>.json` in the format in `reference.md`. Leave out `deck.cards` and `context`.
- `name`: how the character is known; it must not be a CPU's already (check `corpus/cpus/`).
- `model` and `aggression`: by STYLE.md.
- The four texts: in the character's voice, as long as the examples' are. `combo_text` is said as it plays the combo.
- Scenes: infinite challenge events (`"infinite_event": true`), shaped as STYLE.md describes. Pair the new CPU with
  existing CPUs who'd make an interesting meeting (shared themes, opposite temperaments), favouring those in few scenes
  (count them in `corpus/scenes.json`'s `cast`); say why you chose each. Cast them by the exact `name` in their file in
  `corpus/cpus/`. Use only commands, backgrounds, buffs and pictures listed in `reference.md`.

## Checking

Run `.venv/Scripts/python.exe manage.py check_cpu_file corpus/new/<name>.json` and fix every problem it lists, then
run it again, until it passes. It checks against the export in `corpus/`, not a database, so it's safe to run any time.

Don't run `import_cpu` yourself. The local database doesn't have production's cards or CPUs, so it can only be run on
the production instance, by staff. Give them the commands in your summary.

## Summary for the user

Give the file's path, the CPU's name, model, anchors and why, each scene in a line (who it pairs with, and why), and
anything you were unsure of. Then what's left for them:
1. Copy the file to the instance: `scp -i $HOME\.ssh\aws-eb corpus\new\<name>.json ec2-user@<instance IP>:/tmp/`
2. There (`eb ssh`): `bash /var/app/current/go_time.sh import_cpu /tmp/<name>.json --dry-run --seed <N>`, then the same
   without `--dry-run` once it passes (the same seed builds the same deck). Express notes are worth a look; they aren't errors.
3. Pictures: `find_card_images --series <SERIES>`, then the CPU's images page.
4. Play the scenes on the scene page and a game against the CPU, then finalize it.
