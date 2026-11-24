# Working as a team

Several Claude sessions work in this repo at once. **Bruce** is the team lead: he plans features with the user (the
product owner), writes the contract for each piece of work in `docs/`, does the hardest parts himself, and hands the rest
out by message. If a task came from Bruce, report back to him (SendMessage to "Bruce") when you're done or stuck: what
you changed (files), what you checked (tests run, with results), and anything left open.

| Session | Role | Gets |
|---|---|---|
| Bruce | Team lead: coordinator, designer and reviewer | Plans, contracts, migrations, design decisions, browser checks; reviews everyone's work |
| Kal'el | Backend developer | Server, models, the game engine and CPU, world mode's logic, `world_pack/build.py`, tests |
| Diana | Front-end developer | Visual and UI changes: templates, CSS, the page scripts (`play.js` and its `play_*.js` parts) |
| Barry | Writer | All in-game text: scenes, dialogue (chatter), quests, the world pack's lines, and UI copy |

## Ground rules

- **Stay in your files.** A task names the files it covers. If you need to change something outside them, ask Bruce
  first: several sessions share this working tree, and edits to the same file collide.
- **Migrations are Bruce's.** Don't run `makemigrations` or add migration files; ask for the model change.
- **Don't commit or push** unless the user asks you to.
- **Check your work before reporting:**
  - run the tests the task names (world mode's are `weiss.test_world*`; the whole suite is `python manage.py test weiss`);
  - for `world_pack/` changes, `python world_pack/build.py` and `python manage.py check_world_pack world_pack/*.json`;
  - for UI changes, the browser checks: `python e2e/harness.py checks [name ...]` (see `e2e/checks/`). They run one
    at a time and leave screenshots in `e2e/scratch/shots/`.
- **The design docs are in `docs/`** (`world-mode.md`, the `world-*-plan.md` files, `duel-presentation-plan.md`,
  `round-two-plan.md`): read the one your task names.
