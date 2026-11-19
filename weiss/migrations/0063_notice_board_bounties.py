"""The notice board's first quests: weekly bounties and the tournament-day notice (weiss.quests: board quests with a
window). Their wording is a first draft: see docs/world-events-plan.md, "Writing to do"."""
from django.db import migrations

BOUNTIES = [
    {
        "key": "bounty-three-duelists",
        "title": "Bounty: three duelists",
        "gate_rank": None,
        "spec": {
            "about": "The arena wants new blood. Beat three different duelists this week.",
            "offer": "",
            "requires": {},
            "stages": [
                {
                    "text": "Beat three different duelists this week",
                    "objectives": [
                        {
                            "do": "beat_different",
                            "count": 3
                        }
                    ]
                }
            ],
            "endings": [
                {
                    "key": "claim",
                    "title": "Claim the bounty",
                    "rewards": [
                        {
                            "coins": 400
                        }
                    ],
                    "about": "",
                    "to": "",
                    "locks": [],
                    "removes": [],
                    "flags": [],
                    "requires": [],
                    "script": ""
                }
            ],
            "rewards": [],
            "hidden": False,
            "window": {},
            "board": True
        }
    },
    {
        "key": "bounty-villain",
        "title": "Bounty: a villain brought down",
        "gate_rank": None,
        "spec": {
            "about": "Someone wants a villain taught a lesson. Any of them will do.",
            "offer": "",
            "requires": {},
            "stages": [
                {
                    "text": "Beat a villain in a duel",
                    "objectives": [
                        {
                            "do": "beat_different",
                            "count": 1,
                            "temperament": "villain"
                        }
                    ]
                }
            ],
            "endings": [
                {
                    "key": "claim",
                    "title": "Claim the bounty",
                    "rewards": [
                        {
                            "coins": 300
                        }
                    ],
                    "about": "",
                    "to": "",
                    "locks": [],
                    "removes": [],
                    "flags": [],
                    "requires": [],
                    "script": ""
                }
            ],
            "rewards": [],
            "hidden": False,
            "window": {},
            "board": True
        }
    },
    {
        "key": "bounty-high-roller",
        "title": "Bounty: high roller",
        "gate_rank": None,
        "spec": {
            "about": "Win a high-stakes duel this week, of 300 coins or more.",
            "offer": "",
            "requires": {},
            "stages": [
                {
                    "text": "Win a high-stakes duel of 300 coins or more",
                    "objectives": [
                        {
                            "do": "stakes",
                            "fee": 300
                        }
                    ]
                }
            ],
            "endings": [
                {
                    "key": "claim",
                    "title": "Claim the bounty",
                    "rewards": [
                        {
                            "pack": "climax_pack"
                        }
                    ],
                    "about": "",
                    "to": "",
                    "locks": [],
                    "removes": [],
                    "flags": [],
                    "requires": [],
                    "script": ""
                }
            ],
            "rewards": [],
            "hidden": False,
            "window": {},
            "board": True
        }
    },
    {
        "key": "tournament-day",
        "title": "Tournament day",
        "gate_rank": None,
        "spec": {
            "about": "Win a round at the weekly tournament. On the board for tournament weekend only.",
            "offer": "",
            "requires": {},
            "stages": [
                {
                    "text": "Win a round at the weekly tournament",
                    "objectives": [
                        {
                            "do": "event",
                            "event": "weekly-tournament",
                            "result": "round"
                        }
                    ]
                }
            ],
            "endings": [
                {
                    "key": "claim",
                    "title": "Claim the prize",
                    "rewards": [
                        {
                            "coins": 300
                        }
                    ],
                    "about": "",
                    "to": "",
                    "locks": [],
                    "removes": [],
                    "flags": [],
                    "requires": [],
                    "script": ""
                }
            ],
            "rewards": [],
            "hidden": False,
            "window": {
                "event": "weekly-tournament"
            },
            "board": True
        }
    }
]


def add_bounties(apps, schema_editor):
    Quest = apps.get_model("weiss", "Quest")
    top = max(Quest.objects.values_list("order", flat=True), default=0)
    for n, quest in enumerate(BOUNTIES, 1):
        Quest.objects.get_or_create(key=quest["key"], defaults={**quest, "order": top + n})


def remove_bounties(apps, schema_editor):
    apps.get_model("weiss", "Quest").objects.filter(key__in=[quest["key"] for quest in BOUNTIES], giver__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("weiss", "0062_tournament_chatter"),
    ]

    operations = [
        migrations.RunPython(add_bounties, remove_bounties),
    ]
