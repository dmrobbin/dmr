# World mode: ideas for the release (on hold)

Proposed 2026-11-25. **Decided 2026-11-26: see `docs/world-release-plan.md`** for what's in the release, who does
it, and what waits.

## Before release: must-dos
1. **Hide the World tab until a player can use it.** Verified: a regular (non-staff) player sees the tab, and it gives
   them a 403 error page (`world_home` is `@staff_required`; the tab in `core/templates/core/dashboard_base.html` has no
   condition).
2. **A proper on switch.**
   - Split the player pages from the staff tools. `world_test`, `world_settings`, `world_schedules`, test mode and
     `world_jump` stay staff only; `world.test_mode()` already requires staff.
   - Add a setting: staff only, then a beta group, then everyone.
   - Make every player action check that the save is the player's own. Today it's safe only because non-staff can't
     make a save; `town_move` and `deck_change` don't check staff.
3. **Error reporting in production.** `mysite/settings.py` has no `LOGGING` or `ADMINS`.
4. **Content goes live with the deploy.** The world pack import is manual today. Add a check that an updated pack
   doesn't break saves already in progress.
5. **An economy simulation** of weeks of play, to check coins against prices and look for money loops (like
   `cpu_selfplay`).

## A good first impression
6. **Time a new player's first 10 minutes** (`e2e/tutorial.py` at 1280 and 390), and trim what's slow. Let a second
   save skip the tutorial.
7. **A "Today" card in the town:** two or three suggestions, from quests and the week's events.
8. **A "Previously…" recap** for a player coming back after days away.
9. **A "Report a problem" button:** what the player says, plus the save's state, on a staff list.

## Polish
10. **A full phone playthrough** as a browser check (a whole in-game day at 390).
11. **Achievements:** first Best friend, all 75 met, first tournament win, a set completed.
12. **Decide the open story questions** in `docs/world-scenes-plan.md` ("Open questions": the number of conflict pairs,
    and Levi's `removes`).

Checked then, and fine:
- The town doesn't poll; it refreshes on a return to the tab. Its state costs 42 queries in about 24 ms.
- Production is MySQL, a single instance, and the duel's long poll is capped (`PLAY_LONG_POLL_MAX`).
- A minigame result is trusted only after a minimum play time, which is acceptable for a single-player save.
