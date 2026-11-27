# World mode: the release

Agreed with the product owner on 2026-11-26, from `docs/world-release-ideas.md`. Owner: Bruce.

## Decisions

- **Roll out to everyone at once.** There are only a few players, so there's no beta group: one switch, staff only →
  everyone.
- **The economy simulation waits.** The product owner is playtesting the economy by hand for now.
- **The conflict pairs stay as built.** The packs have 13 pairs (26 of the 75 CPUs) plus two one-way locks (Power →
  Makima, Jolyne → DIO, both on CPUs already in pairs). One save can close at most 13 friendships (17%), and 35% of
  the cast can be closed in *some* save. Both are under the 40% ceiling.
- **Levi's `removes` is gone.** It isn't in the built pack, and no ending sends anyone away. `world-scenes-plan.md`'s
  open question is closed.

## The work

| # | Work | Who | Files |
|---|---|---|---|
| 0 | The model: `WorldSettings.open_to_players`, `WorldReport` (migration 0069) | Bruce | **done** |
| A | The on switch | Kal'el (logic), Diana (tab and toggle) | below |
| B | Tests before every deploy | Kal'el | `.github/workflows/deploy.yml` |
| C | Error logging in production | Kal'el | `mysite/settings.py` |
| F | Report a problem | Kal'el (endpoint, staff list), Diana (button, dialog, list page), Barry (copy) | below |
| E | Release check pass: first 10 minutes at 1280 and 390, a phone day, as a **non-staff** player | Bruce | `e2e/` |

### A. The on switch

**Done means:** with `open_to_players` off, a non-staff player sees no World tab and gets a friendly redirect from any
world URL. With it on, they can play everything a staff player can, except the staff tools. Staff see everything either
way.

Kal'el:
- `world.open_to(user)`: `user.is_staff`, or `has_weiss_access(user)` and `WorldSettings.current().open_to_players`
  (no settings row = closed).
- A `player_required` decorator in `world_views.py`, used instead of `@staff_required` on every **player** view there,
  including `deck_change` and `town_move`. A closed world redirects to `weiss:sets` with a message (copy below); a JSON
  endpoint answers 403 `{"error": ...}`.
- **Staff only, unchanged:** `world_test`, `world_settings`, `world_schedules`, and everything in
  `world_staff_views.py`, `minigame_views.py`, `scene_views.py`, `pack_views.py`, `cpu_import_views.py`. Test mode,
  `world_jump`, tutorial skip and rank-up already check staff in the logic: leave them, and test them.
- Sweep for anything else the town calls (a duel's play room, scene JSON, music, minigame data) that's staff gated, and
  open what a player needs. List what you found in your report.
- `world_open` in `weiss/context_processors.py` (true for staff, or when open).
- **The switch is its own form** (changed 2026-11-26, after review): `POST weiss:world_switch` (staff, `open` = 1/0)
  saves `open_to_players` at once. `world_settings` never touches it, so saving the settings can't close world mode
  by accident. The status line shows only what's saved.
- Tests in a new `weiss/test_world_access.py`: closed vs open for a non-staff player (pages, JSON, redirect); a player
  can't read or change another player's save by slot; a non-staff player can't use test mode, jump, skip or rank-up,
  even with `test_mode` set in their flags by hand; staff tools stay 403 for a non-staff player when open.

Diana:
- `core/templates/core/dashboard_base.html`: the World tab only `{% if world_open %}`.
- The CPU tab's World section, above the settings form: the switch as its own small form posting to `weiss:world_switch`,
  with one button saying what it will do and a status line showing the saved state only (copy below).

### B. Tests before every deploy

Kal'el: a `test` job in `deploy.yml`, and `deploy` gets `needs: test`. Use the Python version EB runs, install
`requirements.txt`, then `python manage.py test weiss` and `python manage.py check_world_pack world_pack/*.json`. If any
test needs something the runner hasn't got (MySQL, S3, network), say so rather than skipping it quietly. **Don't push**:
report the diff, and the user pushes.

### C. Error logging

Kal'el: a `LOGGING` setting so a server error's traceback reaches stdout/stderr (EB keeps those in `web.stdout.log`):
`django.request` at ERROR, the root logger at WARNING, all to the console. No email (there's no email set up). Check it
locally with `DEBUG` off and a view that raises: the traceback should be printed.

### F. Report a problem

Done means: from the town, a player can say what went wrong in a couple of clicks, and staff get it with the save as it
was.

Kal'el:
- `POST weiss:world_report` (slot): `player_required`, the player's own save. `text` 1–2000 characters (trimmed),
  `page` optional. At most 5 reports an hour per player (429 with a message). Stores a `WorldReport` with `state` =
  the save's fields plus `world.town(save)`. Answers JSON `{"said": ...}` or `{"error": ...}`. It **doesn't** go through
  `town_move`'s version check: a report has to get through even when the save is out of step.
- `weiss:world_reports` (staff): open reports first, each with its player, time, text, page, a link to the save's slot,
  the state as collapsible JSON, a resolve toggle and a staff note (POST). A link to it from the CPU tab's World section,
  with the count of open reports.
- Tests in `weiss/test_world_access.py` (or `test_world_report.py`): stores the report and its state, the length limits,
  the rate limit, someone else's slot, a closed world.

Diana:
- In the town's menu: "Report a problem". A `<dialog>` with a labelled textarea, Send and Cancel, a character count near
  the limit, and states for sending (the button disabled), sent (a thank-you, then close) and error (keep the text).
  It works at 390 width and from the keyboard, with focus going back to the menu button.
- The staff list's template, in the style of the other staff lists.
- A browser check for it in `e2e/checks/` (open, send, see it on the staff list).

### Copy (Barry fills this in; Diana and Kal'el use it word for word)

Use the copy exactly as written. In the UI strings, apostrophes are straight ('), and names get curly double quotes
(“{deck.name}”), as in the rest of world mode. The curly quotes around each line here only mark where it starts and
ends: they aren't part of the text. `{n}` is a number filled in by
the code.

- The closed-world message (redirect, `messages.info`): “World mode isn't open yet. It's coming soon!”
  - The same line is the JSON 403's `error`.
- The on switch (a button of its own on the CPU tab's World section, which saves straight away):
  - Status when on: “Open to every player”
  - Status when off: “Staff only”
  - Button when closed (opens it): “Open to all players”
  - Button when open (closes it): “Make staff only”
  - After opening (`messages.success`): “World mode is open to every player.”
  - After closing (`messages.success`): “World mode is staff only again. Players' saves are kept.”
- Menu item: “Report a problem”, with the hint “tell us what went wrong” (in `town-hud-menu-hint`, like the others)
- Dialog title: “Report a problem”
- Help line: “Tell us what happened and what you expected. We'll see your save as it is right now, so you don't need
  to describe it.”
- Textarea label: “What went wrong?”
- Placeholder: “I tried to buy a pack, but…”
- Character count (shown from 1,800 characters): “{n} characters left”, then “{n} too many” over 2,000
- Send: “Send report”. Cancel: “Cancel”. While sending, the button reads: “Sending…”
- Sent: “Thanks: we've got it. We'll look into it.” (shown for a moment, then the dialog closes). In this state,
  Cancel becomes “Close”.
- Errors:
  - Empty text: “Write a few words about what went wrong first.”
  - Too long: “That's over 2,000 characters. Could you shorten it a little?”
  - Too many reports (429): “You've sent a lot of reports this hour. Please try again a bit later.”
  - Couldn't send (network or server): “That didn't send. Your text is still here: try again in a moment.”
- Staff list:
  - Page title: “Player reports”
  - Link on the CPU tab: “Player reports ({n} open)”, or “Player reports” when none are open
  - Empty state: “No reports yet. When a player sends one from the town's menu, it shows up here.”
  - No open reports, but some resolved ones: “Nothing open. Resolved reports are below.”
  - Each report's save link: “Slot {n}”
  - Resolved toggle: “Resolved” (a checkbox)
  - Note label: “Staff note”, with the button “Save note”
  - The state's summary (collapsible): “Save state when reported”

## After release

- A save-safety check for pack updates (before the first content update): a new pack mustn't drop a CPU, quest or item
  that a save refers to.
- A second save can skip the tutorial.
- The town's stage on phones is only about 470px tall at 390×844 (notices and the goal bar sit above it), so the
  11-item menu scrolls (with a fade cue). Look at a taller stage or a slimmer header on phones.
- Two browser checks are flaky on timing: `recap` ("How the game went shows while the ceremony is still playing") and
  `ceremony` ("shows no coins"). Each passes alone and on a rerun. Make them wait on a state instead of a time.
- Later: the economy simulation, the "Today" card, "Previously…", achievements.
