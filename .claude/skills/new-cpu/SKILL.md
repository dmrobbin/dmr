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
- Optional: a character to build around, anchor cards, a model, whether it's a boss, how many scenes (default 1, an intro).

## Before writing

1. `corpus/reference.md` must exist. If it doesn't, stop: staff need to run `export_cpu_corpus` on production
   and copy its folder to `corpus/`. Read `reference.md` in full; it lists everything a file and a script can say.
2. Read `STYLE.md` beside this file. It overrides anything the examples do.
3. Choose 3 or 4 examples in `corpus/cpus/`: the same series first, then the same model, then whatever is
   marked as a model example in STYLE.md. Read them whole, scenes included. Skim `corpus/scenes.json` for
   how scenes are named and where they play.

## Choosing the anchors

Run `./go_time.sh list_cpu_anchors <SERIES> --unused` (`.\go_time.ps1` on Windows). It lists the cx combo cards a CPU can
play, with the climaxes they combo with. Prefer:
- two anchors featuring the same character, or the character asked for;
- anchors no CPU uses yet (`--unused`; drop it if that leaves fewer than two);
- a combo whose climax is in the anchors' colors.

The CPU is that character. Its personality comes from the anchors' names, traits and flavor text and what
you know of the series. If you don't know the character well, say so in your summary instead of inventing lore.

## Writing the file

Write `corpus/new/<name>.json` in the format in `reference.md`. Leave out `deck.cards` and `context`.
- `name`: how the character is known; it must not be a CPU's already (check `corpus/cpus/`).
- `model` and `aggression`: by STYLE.md.
- The four texts: in the character's voice, as long as the examples' are. `combo_text` is said as it plays the combo.
- Scenes: cast the new CPU by its `name`, and only CPUs that exist (from `corpus/cpus/`). Use only commands,
  backgrounds, buffs and pictures listed in `reference.md`. Name scenes as the examples do.

## Checking

Run `./go_time.sh import_cpu corpus/new/<name>.json --dry-run --seed <any number>` and fix every problem it lists,
then run it again, until it passes. Express notes (things the deck couldn't fit) are worth mentioning but aren't errors.

**Never run import_cpu without `--dry-run` unless the user asks you to** in this conversation: it writes to whichever
database `.env` points at, which it prints first. When asked, use the same `--seed` as the passing dry run, so the deck is the one checked.

## Summary for the user

Give the file's path, the CPU's name, model, anchors and why, each scene in a line, and anything you were unsure of.
Remind them of what's left: the import, if not done; pictures (`find_card_images --series <SERIES>`, then the
CPU's images page); a look at the scenes on the scene page; a game against it; then finalizing it.
