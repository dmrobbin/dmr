# Working as a team

Several Claude sessions work in this repo at once. **World Planner** coordinates: it plans features with the user,
lays the groundwork, does the hard parts, and hands the rest out by message. If a task came from World Planner, report
back to it (SendMessage to "World Planner") when you're done or stuck: what you changed (files), what you checked
(tests run, with results), and anything left open.

| Session | Role | Gets |
|---|---|---|
| World Planner | Coordinator and lead developer | Plans, groundwork, difficult or cross-cutting code |
| Sam Front End, Sam 2 Front End | Front-end developers | Visual and UI changes: templates, CSS, the page scripts |
| Danny Writer | Writer | Scenes, dialogue (chatter), quests and other in-game text |
| Tucker JR | Junior developer | Small, contained tasks that need no creative decisions |

## Ground rules

- **Stay in your files.** A task names the files it covers. If you need to change something outside them, ask World
  Planner first: several sessions share this working tree, and edits to the same file collide.
- **Migrations are World Planner's.** Don't run `makemigrations` or add migration files; ask for the model change.
- **Don't commit or push** unless the user asks you to.
- **Check your work before reporting:** run the tests the task names (world mode's are `weiss.test_world*`), and for
  `world_pack/` changes, `python world_pack/build.py` and `python manage.py check_world_pack world_pack/*.json`.
- **The design docs are in `docs/`** (`world-mode.md` and the `world-*-plan.md` files): read the one your task names.
