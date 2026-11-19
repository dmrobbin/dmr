"""World mode's story: its chapters (weiss.quests story quests), built into 00_story.json and imported with the packs.

A chapter begins by itself once what it `requires` is done (the chapter before it, a flag), and finishes by itself
when its stages are done (its one ending with no "to"; others are chosen by talking to someone). It can play scenes:
`scene` when it begins, a stage's `scene` when that stage is done, an ending's `scene` when it's reached. Whoever a
chapter names is brought into town when it begins, even if they hadn't arrived yet.

These three chapters are PLACEHOLDERS, so the chain can be played through before the story's written: plain
objectives, no scenes. The scenes the real chapters need are listed in docs/world-story-plan.md. A scene is written
in STORY_SCENES as {"name", "lines"}, casting whoever it needs ("cast aang as Aang"), and named in a chapter's "scene".
"""

STORY = [
    {"key": "story-1", "title": "A new town", "story": True, "chapter": 1,
     "about": "You've just arrived in town with a deck and a few coins. Find your feet.",
     "stages": [{"text": "Win your first duel", "objectives": [{"do": "beat_different", "count": 1}]}],
     "endings": [{"key": "done", "title": "Settled in", "rewards": [{"coins": 300}]}]},
    {"key": "story-2", "title": "Making a name", "story": True, "chapter": 2, "requires": {"quests": ["story-1"]},
     "about": "People are starting to notice the newcomer with the deck. Show them what you can do.",
     "stages": [{"text": "Beat three different duelists", "objectives": [{"do": "beat_different", "count": 3}]}],
     "endings": [{"key": "done", "title": "A name in town", "rewards": [{"pack": "climax_pack"}]}]},
    {"key": "story-3", "title": "Tournament weekend", "story": True, "chapter": 3, "requires": {"quests": ["story-2"]},
     "about": "The arena runs a tournament every weekend. It's time you entered.",
     "stages": [{"text": "Enter the weekly tournament", "objectives": [{"do": "event", "event": "weekly-tournament"}]}],
     "endings": [{"key": "done", "title": "In the bracket", "rewards": [{"coins": 500}]}]},
]

STORY_SCENES = []
