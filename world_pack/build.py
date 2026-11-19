"""Builds world mode's packs (world_pack/*.json, uploaded on the CPU creation page's Import tab) from the cast files in
world_pack/src/: each CPU's temperament, haunts, gift tastes, chatter and its two rank-up scenes, written compactly.

    python world_pack/build.py           # writes world_pack/<cast file>.json
    python manage.py check_world_pack world_pack/*.json

A cast file has CAST = [cpu(...), ...]. In a CPU:
- haunts: (place, days, times, weight[, min_rank]): days "wk" (Mon-Fri), "we" (Sat, Sun), "all", or a string of
  day numbers ("135": Tue, Thu, Sat); times a string of 0 morning, 1 noon, 2 evening, 3 night ("23").
- tastes: (loves, likes, dislikes), lists of gift tags.
- lines: chatter by moment, each a script (lines split on "\\n"): hi (a list: greetings for a stranger), hi2 (a
  friend's greeting, rank 2), hi4 (a close friend's, rank 4), again, loved, disliked, before, won (after the player
  wins), lost (after the player loses), r1, r3, r4 (what reaching ranks 1, 3 and 4 says); hello and bye (each a list
  of three one-line scripts: what it says when the player walks up and when they leave, to a stranger, a friend
  (rank 2) and a close friend (rank 4)).
- repeat (optional): lines for talking again, at each tier: "future" and "past" (lists of three), and "like" and
  "dislike" (each {"with", "lines"}: three comparisons, unfavourable to favourable).
- tournament (optional): lines for the tournament week, by spectator, entrant, out, champion and duel, each three
  lists (ranks 0, 2, 4).
- mid (optional): first-talk lines for the in-between ranks, a dict of rank ("1", "3", "5") to lines.
- hello_steps and bye_steps (optional): two lines of greeting and two of goodbye for each of the six relationship steps,
  a list of six pairs, rank 0 (Stranger) first. They come on top of hello and bye.
- friend, best: the scenes reaching Friend (rank 2) and Best friend (rank 5) play, as script lines; the cast line
  for the CPU (as `me`) is added at the top. "me (pleased):" and "me (dismayed):" become its screens.
- quests (optional): the quests it gives, as weiss.quests writes them (without the giver: it's this CPU). The ones
  with "gates": 2 and "gates": 5 hold those rank-ups (and their scenes) until they're done. Leave it out and an import
  leaves the CPU's quests as they are.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
GREETING_RANKS = (0, 2, 4)  # hello and bye: a stranger's, a friend's, a close friend's
DAYS = {"wk": [0, 1, 2, 3, 4], "we": [5, 6], "all": list(range(7))}
MOMENTS = {"again": ("again", 0), "loved": ("gift_loved", 0), "disliked": ("gift_disliked", 0), "before": ("before_duel", 0),
           "won": ("after_win", 0), "lost": ("after_loss", 0), "hi2": ("greet", 2), "hi4": ("greet", 4),
           "r1": ("rank_up", 1), "r3": ("rank_up", 3), "r4": ("rank_up", 4), "cold": ("estranged", 0)}


# In a scene, a CPU's pictures are its screens: "lose" (the player lost) is it pleased, "win" (the player won) dismayed.
SCENE_MOODS = {"(pleased)": "(lose)", "(dismayed)": "(win)"}


def staged(line):
    """A scene line with the chatter-style moods turned into the CPU's screens."""
    for mood, screen in SCENE_MOODS.items():
        line = line.replace(f"me {mood}:", f"me {screen}:")
    return line


def cpu(name, temperament, haunts, tastes, lines, friend, best, quests=None, extra_scenes=None):
    return {"name": name, "temperament": temperament, "haunts": haunts, "tastes": tastes, "lines": lines, "friend": friend, "best": best,
            "quests": quests, "extra_scenes": extra_scenes or []}


def entry(spec):
    """A CPU's pack entry from its spec."""
    name = spec["name"]
    schedule = []
    for haunt in spec["haunts"]:
        place, days, times, weight, *rank = haunt
        schedule.append({"place": place, "days": DAYS.get(days) or sorted(int(d) for d in days),
                         "times": sorted(int(t) for t in times), "weight": weight, "min_rank": rank[0] if rank else 0})
    loves, likes, dislikes = spec["tastes"]
    chatter = [{"context": "greet", "min_rank": 0, "script": script.split("\n")} for script in spec["lines"]["hi"]]
    for key, (context, rank) in MOMENTS.items():
        if key in spec["lines"]:
            chatter.append({"context": context, "min_rank": rank, "script": spec["lines"][key].split("\n")})
    for key, context in (("hello", "hello"), ("bye", "goodbye")):
        for rank, script in zip(GREETING_RANKS, spec["lines"].get(key, [])):
            chatter.append({"context": context, "min_rank": rank, "script": [script]})
    # hello_steps and bye_steps: two lines for each relationship step, rank 0 (Stranger) to 5 (Best friend).
    for key, context in (("hello_steps", "hello"), ("bye_steps", "goodbye")):
        for rank, pair in enumerate(spec["lines"].get(key, [])):
            for line in pair:
                chatter.append({"context": context, "min_rank": rank, "script": [line]})
    # mid: first-talk lines for the in-between ranks, keyed by rank ("1", "3", "5").
    for rank, scripts in spec["lines"].get("mid", {}).items():
        for script in scripts:
            chatter.append({"context": "greet", "min_rank": int(rank), "script": [script]})
    # tournament: lines for the tournament week, by context (spectator, entrant, out, champion, duel); each a list of
    # three lists of lines, for ranks 0, 2 and 4.
    for key, tiers in spec["lines"].get("tournament", {}).items():
        for rank, scripts in zip((0, 2, 4), tiers):
            for script in scripts:
                chatter.append({"context": f"tournament_{key}", "min_rank": rank, "script": [script]})
    # repeat: lines for talking again (the again context), at each of the three tiers (ranks 0, 2, 4): a future and a past
    # line, and comparisons with a liked and a disliked character (each a list of three, unfavourable to favourable).
    repeat = spec["lines"].get("repeat")
    if repeat:
        for index, rank in enumerate((0, 2, 4)):
            scripts = [repeat["future"][index], repeat["past"][index], repeat["like"]["lines"][index], repeat["dislike"]["lines"][index]]
            for script in scripts:
                chatter.append({"context": "again", "min_rank": rank, "script": [script]})
    scenes = []
    for rank, title, lines in ((2, "Friend", spec["friend"]), (5, "Best friend", spec["best"])):
        scene = f"World: {name}, {title}"
        chatter.append({"context": "rank_up", "min_rank": rank, "scene": scene})
        scenes.append({"name": scene, "script": [f"cast me as {name}", *(staged(line) for line in lines)]})
    # Scenes a quest's visit plays: {"name", "lines"}, cast the same way (a visit always has something happening).
    for extra in spec.get("extra_scenes", []):
        scenes.append({"name": extra["name"], "script": [f"cast me as {name}", *(staged(line) for line in extra["lines"])]})
    world = {"temperament": spec["temperament"], "schedule": schedule,
             "gift_tastes": {"loves": loves, "likes": likes, "dislikes": dislikes}, "chatter": chatter}
    if spec.get("quests") is not None:
        world["quests"] = spec["quests"]
    return {"name": name, "world": world, "scenes": scenes}


def main():
    built = 0
    for source in sorted((HERE / "src").glob("*.py")):
        module_spec = importlib.util.spec_from_file_location(source.stem, source)
        module = importlib.util.module_from_spec(module_spec)
        module.cpu = cpu
        module_spec.loader.exec_module(module)
        pack = {"pack": source.stem, "cpus": [entry(spec) for spec in module.CAST]}
        (HERE / f"{source.stem}.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{source.stem}.json: {len(pack['cpus'])} CPUs")
        built += len(pack["cpus"])
    print(f"{built} CPUs in all")


if __name__ == "__main__":
    main()
