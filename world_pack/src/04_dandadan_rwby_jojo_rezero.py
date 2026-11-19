"""World mode cast: Dandadan, RWBY, JoJo's Bizarre Adventure and Re:Zero."""

AIRA_QUESTS = [
  {
    "key": "aira-the-chosen-one",
    "title": "The Chosen One",
    "gates": 2,
    "about": "Aira is certain she's destined for greatness, and she'll tell you so at length.",
    "offer": [
      "them: I'm a hero. It's my destiny. Pay attention.",
      "them (pleased): You agreed! I knew you would. Secretly, I mean."
    ],
    "stages": [
      {
        "text": "Hear Aira's speech at school in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Aira, School",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Because I'm the Chosen One, Aira",
        "objectives": [
          {
            "do": "have_card",
            "card": "DDD/S118-E022"
          }
        ]
      },
      {
        "text": "Let Aira tell you the rest of the destiny",
        "objectives": [
          {
            "do": "talk",
            "to": "Aira",
            "script": [
              "them: The spirit inside me is watching. It's very proud.",
              "them (pleased): ...Don't tell Okarun I said that."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "secret-thrill",
        "title": "Keep her secret",
        "about": "Aira announces herself a hero to the whole school. You're now the only one she trusts with the spirit.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "earbuds"
          }
        ]
      }
    ]
  },
  {
    "key": "aira-acrobatic-silkys-gift",
    "title": "Acrobatic Silky's Gift",
    "gates": 5,
    "about": "The spirit inside Aira has a lost daughter, and Aira cries about it without meaning to.",
    "offer": [
      "them (dismayed): The spirit's daughter is lost. I can feel her sometimes.",
      "them: Come to the plaza tonight. Please don't laugh."
    ],
    "stages": [
      {
        "text": "Meet Aira in the plaza in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              2
            ],
            "scene": "World: Aira, Plaza",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Aira: Acrobatic Pretty Girl in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "DDD/S118-E023",
            "against": [
              "Aira"
            ]
          }
        ]
      },
      {
        "text": "Give Aira your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Aira",
            "script": [
              "them: Okarun mustn't hear about this. Promise me.",
              "them (pleased): ...Thank you. You're a real friend."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "the-daughter",
        "title": "Help find the daughter",
        "about": "Aira's spirit gives you a small charm, and says the daughter is closer than they think.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
AIRA_SCENES = [
  {
    "name": "World: Aira, School",
    "lines": [
      "background classroom",
      "me enters center with rise",
      "me: I am the chosen one. I've said it. Now you must bow.",
      "player: Do you really think so?",
      "me (dismayed): ...Yes. Obviously. Stop looking at me like that.",
      "me (pleased): You're a good audience, though. Keep being one."
    ]
  },
  {
    "name": "World: Aira, Plaza",
    "lines": [
      "background dusk",
      "me enters left with slide",
      "me: The spirit had a daughter. She's lost somewhere.",
      "player: That's sad.",
      "me (dismayed): Stop. I'm not crying. It's just the wind.",
      "me: Don't tell Okarun. He'll make it into a documentary."
    ]
  }
]
MOMO_AYASE_QUESTS = [
  {
    "key": "momo-ken-takakura",
    "title": "Ken Takakura",
    "gates": 2,
    "about": "Momo's ideal man is a film actor, and she wants your opinion on him, loudly.",
    "offer": [
      "them: Ken Takakura is the most dreamy actor in the world. Don't argue.",
      "them (pleased): Look at his poster. Tell me he isn't perfect."
    ],
    "stages": [
      {
        "text": "Find Momo at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Momo Ayase, Cafe",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have That's Against the Rules! Momo",
        "objectives": [
          {
            "do": "have_card",
            "card": "DDD/S118-E065"
          }
        ]
      },
      {
        "text": "Hear what Momo really thinks",
        "objectives": [
          {
            "do": "talk",
            "to": "Momo Ayase",
            "script": [
              "them: My real crush isn't anything like him. Don't say anything.",
              "them (pleased): ...Let's talk about something else."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "real-crush",
        "title": "Keep her real crush a secret",
        "about": "Momo never mentions Ken Takakura again, and seems relieved about it.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "shortcake"
          }
        ]
      }
    ]
  },
  {
    "key": "momo-grandma-seikos-shrine",
    "title": "Grandma Seiko's Shrine",
    "gates": 5,
    "about": "Momo helps her grandmother with a spirit at the shrine, and wants someone to hold the lantern.",
    "offer": [
      "them (dismayed): There's a spirit at the shrine. Grandma can't do it alone.",
      "them: Come tonight. I'll do the talking. You do the lantern."
    ],
    "stages": [
      {
        "text": "Go to the shrine at night",
        "objectives": [
          {
            "do": "visit",
            "place": "shrine",
            "times": [
              3
            ],
            "scene": "World: Momo Ayase, Shrine",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Momo: Fashion is the Battle Uniform for Gyarus in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "DDD/S118-TE14",
            "against": [
              "Momo Ayase"
            ]
          }
        ]
      },
      {
        "text": "Give Momo your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Momo Ayase",
            "script": [
              "them: You held the lantern steady. Thank you.",
              "them (pleased): ...Next time, I'll ask you to hold the talismans too."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "hold-the-lantern",
        "title": "Hold the lantern",
        "about": "Momo gives you a talisman of your own, and says you're part of the family now.",
        "rewards": [
          {
            "coins": 600
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
MOMO_AYASE_SCENES = [
  {
    "name": "World: Momo Ayase, Cafe",
    "lines": [
      "background cafe",
      "me enters right with slide",
      "me: Look at this poster! Isn't he the most amazing man in the world?",
      "player: He's... very good looking.",
      "me (pleased): RIGHT? Thank you! Someone with taste.",
      "me (dismayed): ...My real crush isn't like him at all. Forget I said that."
    ]
  },
  {
    "name": "World: Momo Ayase, Shrine",
    "lines": [
      "background shrine",
      "me enters center with fade",
      "me: The talismans are fluttering. That means the spirit is close.",
      "player: Should I do anything?",
      "me (pleased): Hold the lantern. Steady. Don't let it go out.",
      "me: You're braver than you look. I'm not saying that to be nice."
    ]
  }
]
OKARUN_QUESTS = [
  {
    "key": "okarun-turbo-granny",
    "title": "Turbo Granny",
    "gates": 2,
    "about": "Okarun has research on a yokai, and nobody believes a word of it.",
    "offer": [
      "them: I have research. On a yokai. Nobody believes me, but you might.",
      "them (pleased): Look at these clippings. Don't rush me."
    ],
    "stages": [
      {
        "text": "Look at Okarun's clippings at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Okarun, Library",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Occultic Daily Life, Okarun",
        "objectives": [
          {
            "do": "have_card",
            "card": "DDD/S118-E002"
          }
        ]
      },
      {
        "text": "Tell Okarun what you think",
        "objectives": [
          {
            "do": "talk",
            "to": "Okarun",
            "script": [
              "them (pleased): You took me seriously? I'm so surprised I forgot what I was saying.",
              "them: Okay. Okay. Where was I?"
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "serious-research",
        "title": "Take the research seriously",
        "about": "Okarun shares the rest of his clippings, and asks you to come see the yokai with him.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "manga"
          }
        ]
      }
    ]
  },
  {
    "key": "okarun-golden-balls",
    "title": "Golden Balls",
    "gates": 5,
    "about": "Okarun is still missing part of himself, and he needs a companion for the cursed thing he has to recover.",
    "offer": [
      "them (dismayed): There's a cursed thing I have to recover. It's awkward to explain.",
      "them: Come along, please. Momo can't always go."
    ],
    "stages": [
      {
        "text": "Meet Okarun in the alley at night",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              3
            ],
            "scene": "World: Okarun, Alley",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Okarun: Full Throttle Strike in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "DDD/S118-E003",
            "against": [
              "Okarun"
            ]
          }
        ]
      },
      {
        "text": "Answer Okarun's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Okarun",
            "script": [
              "them: Will you come along? I mean it.",
              "them (pleased): ...Okay. Good. Don't tell Momo I was nervous."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "come-along",
        "title": "Come along",
        "about": "Okarun recovers the cursed thing with you at his side. It's the most awkward night he's had, and he's glad of it.",
        "rewards": [
          {
            "coins": 600
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
OKARUN_SCENES = [
  {
    "name": "World: Okarun, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: The yokai was seen three times. Three! Look at the photos. Look!",
      "player: Those are blurry.",
      "me (dismayed): They're blurry because it's FAST. Like me.",
      "me (pleased): Oh, you're taking this seriously? I'm so surprised I forgot what I was saying."
    ]
  },
  {
    "name": "World: Okarun, Alley",
    "lines": [
      "background city",
      "me enters left with rise",
      "me: The thing I have to recover is cursed. I'm not supposed to say the name.",
      "player: Then don't.",
      "me (dismayed): I wasn't going to. I was going to whisper it.",
      "me: Come along. Momo can't always be there."
    ]
  }
]
CINDER_FALL_QUESTS = [
  {
    "key": "cinder-the-maidens-power",
    "title": "The Maiden's Power",
    "gates": 2,
    "about": "Cinder wants to know what you'd do with power you weren't born with.",
    "offer": [
      "them: A flame in my palm, look. Power you weren't born with. What would you do?",
      "them (dismayed): Don't flinch. I'm not going to burn you. Yet."
    ],
    "stages": [
      {
        "text": "Meet Cinder in the alley in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              2
            ],
            "scene": "World: Cinder Fall, Alley",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Cinder: Leading a Grimm Invasion",
        "objectives": [
          {
            "do": "have_card",
            "card": "RWBY/WX03-057"
          }
        ]
      },
      {
        "text": "Answer Cinder's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Cinder Fall",
            "script": [
              "them: I was a nobody once. Is taking what you're owed wrong?",
              "them (pleased): ...You said it isn't. Interesting."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "owed",
        "title": "Say it isn't wrong",
        "about": "Cinder smiles for the first time, and hints that she'll be asking you for more later.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "instant-ramen"
          }
        ]
      }
    ]
  },
  {
    "key": "cinder-the-fall-of-beacon",
    "title": "The Fall of Beacon",
    "gates": 5,
    "about": "Cinder needs the silver-eyed girl out of the way, and she's offering a share of the power.",
    "offer": [
      "them (dismayed): Glass shards in the air. Feel that? That's what's coming.",
      "them: I need you to lure Ruby Rose somewhere quiet. Will you?"
    ],
    "stages": [
      {
        "text": "Meet Cinder in the warehouse at night",
        "objectives": [
          {
            "do": "visit",
            "place": "warehouse",
            "times": [
              3
            ],
            "scene": "World: Cinder Fall, Warehouse",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Beat Ruby Rose in a duel",
        "objectives": [
          {
            "do": "defeat",
            "cpus": [
              "Ruby Rose"
            ]
          }
        ]
      },
      {
        "text": "Give Cinder your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Cinder Fall",
            "script": [
              "them: Lure her away, or stand against me. Choose.",
              "them (pleased): ...Then we'll see how the power decides."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "take-the-power",
        "title": "Take the power",
        "about": "Cinder takes the power, and Ruby's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "ruby-silver-eyes"
        ]
      },
      {
        "key": "walk-away",
        "title": "Walk away from the fall",
        "about": "Cinder laughs and says the offer stands, in case you change your mind.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "handheld"
          }
        ]
      }
    ]
  }
]
CINDER_FALL_SCENES = [
  {
    "name": "World: Cinder Fall, Alley",
    "lines": [
      "background city",
      "me enters right with rise",
      "me: Feel the heat in my palm? That's the power of a maiden.",
      "player: It's beautiful, and a bit scary.",
      "me (pleased): Scary is honest. I like that.",
      "me: I was a nobody once. Is it wrong to take what I'm owed?"
    ]
  },
  {
    "name": "World: Cinder Fall, Warehouse",
    "lines": [
      "background ruins",
      "me enters center with fade",
      "me: Glass shards in the air. They hum when I think about the silver-eyed girl.",
      "player: What do you want with her?",
      "me (dismayed): Her out of the way. Quietly.",
      "me: Lure her somewhere quiet. I'll share the power with you. Promise."
    ]
  }
]
RUBY_ROSE_QUESTS = [
  {
    "key": "ruby-crescent-rose",
    "title": "Crescent Rose",
    "gates": 2,
    "about": "Ruby wants to show off her scythe, and she transforms it three ways in a row.",
    "offer": [
      "them: Watch this! Crescent Rose, three ways. Don't blink!",
      "them (pleased): Okay, I knocked over a rack. Still counts."
    ],
    "stages": [
      {
        "text": "Watch Ruby's scythe at the arena at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              1
            ],
            "scene": "World: Ruby Rose, Arena",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Ruby Rose",
        "objectives": [
          {
            "do": "have_card",
            "card": "RWBY/WX03-044"
          }
        ]
      },
      {
        "text": "Tell Ruby what you think of the scythe",
        "objectives": [
          {
            "do": "talk",
            "to": "Ruby Rose",
            "script": [
              "them: Do you think weapons can be friends?",
              "them (pleased): ...Crescent Rose says yes. It likes you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "weapons-friends",
        "title": "Think weapons can be friends",
        "about": "Ruby gives you a scythe charm, and says it's for good luck, and for showing off.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "playmat"
          }
        ]
      }
    ]
  },
  {
    "key": "ruby-silver-eyes",
    "title": "Silver Eyes",
    "gates": 5,
    "about": "Ruby learns what her silver eyes can do, and who's afraid of them.",
    "offer": [
      "them (dismayed): My eyes glow sometimes. Some people are scared of that.",
      "them: Come to the cafe tonight. I want to tell you about my mum."
    ],
    "stages": [
      {
        "text": "Meet Ruby at the cafe in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              2
            ],
            "scene": "World: Ruby Rose, Cafe",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Ruby: Ruby Rose in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "RWBY/WX03-044",
            "against": [
              "Ruby Rose"
            ]
          }
        ]
      },
      {
        "text": "Give Ruby your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Ruby Rose",
            "script": [
              "them: Cinder wants my eyes. Will you help me stop her?",
              "them (pleased): ...Thank you. That's what I needed to hear."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "stop-cinder",
        "title": "Stop Cinder",
        "about": "Ruby sets out to stop Cinder. Cinder's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "cinder-the-fall-of-beacon"
        ]
      },
      {
        "key": "keep-your-eyes-open",
        "title": "Keep your eyes open",
        "about": "Ruby decides to wait and watch, and asks you to watch with her.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "bouquet"
          }
        ]
      }
    ]
  }
]
RUBY_ROSE_SCENES = [
  {
    "name": "World: Ruby Rose, Arena",
    "lines": [
      "background arena",
      "me enters left with slide",
      "me: Crescent Rose! Scythe. Sniper. Gun. Okay, I hit the rack.",
      "player: Are you hurt?",
      "me (pleased): Nope! The rack is fine. Mostly.",
      "me: Do you think weapons can be friends? Crescent Rose says yes."
    ]
  },
  {
    "name": "World: Ruby Rose, Cafe",
    "lines": [
      "background cafe",
      "me enters center with fade",
      "me: Mum used to make cookies. I've been trying to make them since.",
      "player: How do they turn out?",
      "me (dismayed): Like a rack, a bit. But they taste good.",
      "me: I saw a light when Pyrrha fell. My eyes did that. I'm still scared of it."
    ]
  }
]
WEISS_SCHNEE_QUESTS = [
  {
    "key": "weiss-heiress",
    "title": "Heiress",
    "gates": 2,
    "about": "Weiss needs a study partner who won't flatter her.",
    "offer": [
      "them: My notes are perfect. Find an error, if you dare.",
      "them (pleased): You found one. Fine. Thank you. I'll pretend I didn't need it."
    ],
    "stages": [
      {
        "text": "Study with Weiss at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Weiss Schnee, Library",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Weiss Schnee",
        "objectives": [
          {
            "do": "have_card",
            "card": "RWBY/WX03-076"
          }
        ]
      },
      {
        "text": "Let Weiss decide whether you've earned her thanks",
        "objectives": [
          {
            "do": "talk",
            "to": "Weiss Schnee",
            "script": [
              "them: You didn't apologise once. I appreciate it.",
              "them (pleased): ...Thank you, stiffly. I mean it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "study-partner",
        "title": "Be her study partner",
        "about": "Weiss leaves a copy of her notes on your table, corrected in red.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "sleeves"
          }
        ]
      }
    ]
  },
  {
    "key": "weiss-summoning",
    "title": "Summoning",
    "gates": 5,
    "about": "Weiss is trying to summon her family's knight, and her father is still on her mind.",
    "offer": [
      "them (dismayed): The glyph won't light. I'm going to try again.",
      "them: Come to the arena at evening. I need someone watching."
    ],
    "stages": [
      {
        "text": "Watch Weiss summon at the arena in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              2
            ],
            "scene": "World: Weiss Schnee, Arena",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Weiss: Weiss: Teamwork in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "RWBY/WX03-T17",
            "against": [
              "Weiss Schnee"
            ]
          }
        ]
      },
      {
        "text": "Give Weiss your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Weiss Schnee",
            "script": [
              "them: My father would have wanted the knight. I want it for myself.",
              "them (pleased): ...You let me smile. Don't tell anyone."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "the-knight",
        "title": "See the knight arrive",
        "about": "The knight's arm appears, and Weiss lets you see her smile properly for once.",
        "rewards": [
          {
            "coins": 600
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
WEISS_SCHNEE_SCENES = [
  {
    "name": "World: Weiss Schnee, Library",
    "lines": [
      "background library",
      "me enters right with fade",
      "me: Your notes are wrong on the third page. Correct it.",
      "player: Where?",
      "me (dismayed): ...There. Yes. Don't tell anyone I said so.",
      "me: Thank you. Stiffly, as you can tell."
    ]
  },
  {
    "name": "World: Weiss Schnee, Arena",
    "lines": [
      "background arena",
      "me enters center with rise",
      "me: The glyph flickers. It always fails when I think about Father.",
      "player: Try again.",
      "me (dismayed): I'm trying. Look at it. Look at it!",
      "me (pleased): There! The arm. It's here. Do you see?",
      "me: Thank you for watching. I'd like you to keep watching."
    ]
  }
]
DIO_QUESTS = [
  {
    "key": "dio-the-world",
    "title": "The World",
    "gates": 2,
    "about": "DIO is curious whether the player fears him, and he watches their face closely.",
    "offer": [
      "them: Do you fear me? Look me in the eye and answer honestly.",
      "them (pleased): Interesting. You're nervous, but you aren't afraid."
    ],
    "stages": [
      {
        "text": "Visit DIO at the library in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              2
            ],
            "scene": "World: DIO, Library",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Horrifying Execution, DIO",
        "objectives": [
          {
            "do": "have_card",
            "card": "JJ/SE41-E15"
          }
        ]
      },
      {
        "text": "Give DIO your opinion of a philosopher",
        "objectives": [
          {
            "do": "talk",
            "to": "DIO",
            "script": [
              "them: Tell me your opinion of this philosopher. Then of yourself.",
              "them (pleased): ...Hm. Honest. Rare."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "honest-opinion",
        "title": "Give your honest opinion",
        "about": "DIO nods slowly and says time skipped a beat while he watched your face. He seems to enjoy it.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "manga"
          }
        ]
      }
    ]
  },
  {
    "key": "dio-heaven",
    "title": "Heaven",
    "gates": 5,
    "about": "DIO wants his son at his side, and he wants the player to bring him.",
    "offer": [
      "them: I have a son I've never met. He is destined for my side.",
      "them (dismayed): Come to the warehouse tonight. We'll discuss heaven."
    ],
    "stages": [
      {
        "text": "Visit DIO at the warehouse at night",
        "objectives": [
          {
            "do": "visit",
            "place": "warehouse",
            "times": [
              3
            ],
            "scene": "World: DIO, Warehouse",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with DIO: Complete Being, DIO & T.W in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "JJ/SE41-E17",
            "against": [
              "DIO"
            ]
          }
        ]
      },
      {
        "text": "Give DIO your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "DIO",
            "script": [
              "them: Persuade Giorno to come home. Will you?",
              "them (pleased): ...You're cleverer than you look. Good."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "join-your-father",
        "title": "Join your father",
        "about": "DIO's son is recruited into his heaven. Giorno's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "giorno-i-have-a-dream"
        ]
      },
      {
        "key": "refuse-him",
        "title": "Refuse him",
        "about": "DIO laughs and says he'll wait. He's very patient.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "bottled-tea"
          }
        ]
      }
    ]
  }
]
DIO_SCENES = [
  {
    "name": "World: DIO, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Read this. Then tell me what you think of the philosopher.",
      "player: He's wrong about most things.",
      "me (pleased): Good. And yourself? Be honest.",
      "player: I think you're afraid of time.",
      "me (dismayed): ...Time skipped a beat there. You noticed."
    ]
  },
  {
    "name": "World: DIO, Warehouse",
    "lines": [
      "background ruins",
      "me enters left with rise",
      "me: Heaven is a place I can give my son. He's never met me.",
      "player: Does he know you're his father?",
      "me (dismayed): He will. Once you persuade him to come home.",
      "me: Bring him to me. I'll be waiting, in the dark."
    ]
  }
]
GIORNO_GIOVANNA_QUESTS = [
  {
    "key": "giorno-gold-experience",
    "title": "Gold Experience",
    "gates": 2,
    "about": "Giorno makes a flower grow from a coin, and he'll say a lot about you from what you do with it.",
    "offer": [
      "them: Give me a coin. I'll make you a flower.",
      "them (pleased): Do you want it back? That tells me a lot."
    ],
    "stages": [
      {
        "text": "Find Giorno at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Giorno Giovanna, Cafe",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Give Giorno a bottled tea",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "bottled-tea",
            "to": "Giorno Giovanna"
          }
        ]
      },
      {
        "text": "Let Giorno read you",
        "objectives": [
          {
            "do": "talk",
            "to": "Giorno Giovanna",
            "script": [
              "them: You didn't want the coin back. I like that about you.",
              "them (pleased): ...Friends don't ask for change."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "keep-the-flower",
        "title": "Keep the flower",
        "about": "Giorno gives you the flower and keeps the coin. He says that's how you know it's a good deal.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "bouquet"
          }
        ]
      }
    ]
  },
  {
    "key": "giorno-i-have-a-dream",
    "title": "I, Giorno Giovanna, Have a Dream",
    "gates": 5,
    "about": "Giorno's father's shadow, and his own path, which he means to walk himself.",
    "offer": [
      "them: There's a man I used to call my father. He casts a long shadow.",
      "them (pleased): Meet me on the beach at sunset. I'll tell you everything."
    ],
    "stages": [
      {
        "text": "Meet Giorno at the beach at evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Giorno Giovanna, Beach",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Giorno: Golden Intentions, Giorno in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "JJ/S66-TE07",
            "against": [
              "Giorno Giovanna"
            ]
          }
        ]
      },
      {
        "text": "Give Giorno your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Giorno Giovanna",
            "script": [
              "them: Help me become something my father never was.",
              "them (pleased): ...Then it's settled. My dream, my path."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "my-own-dream",
        "title": "Help him find his own dream",
        "about": "Giorno sets out on his own path. DIO's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "dio-heaven"
        ]
      },
      {
        "key": "stay-by-his-side",
        "title": "Stay by his father's side",
        "about": "Giorno keeps his father's shadow close, and asks you to stay out of it.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "playmat"
          }
        ]
      }
    ]
  }
]
GIORNO_GIOVANNA_SCENES = [
  {
    "name": "World: Giorno Giovanna, Cafe",
    "lines": [
      "background cafe",
      "me enters right with slide",
      "me: Give me a coin. Now watch closely.",
      "player: Is that a flower?",
      "me (pleased): Gold Experience. It grows from anything you care about.",
      "me: Do you want the coin back? Tell me honestly."
    ]
  },
  {
    "name": "World: Giorno Giovanna, Beach",
    "lines": [
      "background dusk",
      "me enters center with fade",
      "me: The sun's going down. I've been thinking about my father.",
      "player: DIO?",
      "me (dismayed): Yes. The shadow. I want to be something he never was.",
      "me: Help me. My dream is mine, not his."
    ]
  }
]
JOLYNE_CUJOH_QUESTS = [
  {
    "key": "jolyne-stone-free",
    "title": "Stone Free",
    "gates": 2,
    "about": "Jolyne can unravel herself into string, and she wants to show someone who won't scream.",
    "offer": [
      "them: Watch this. I'll come apart. Don't scream.",
      "them (pleased): Good. You didn't. Now, cat's cradle."
    ],
    "stages": [
      {
        "text": "Watch Jolyne at the beach at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              1
            ],
            "scene": "World: Jolyne Cujoh, Beach",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Give Jolyne an energy drink for the stunt",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "energy-drink",
            "to": "Jolyne Cujoh"
          }
        ]
      },
      {
        "text": "Tell Jolyne what you thought",
        "objectives": [
          {
            "do": "talk",
            "to": "Jolyne Cujoh",
            "script": [
              "them: Never knew my dad until he came for me. Is it too late?",
              "them (pleased): ...You say it isn't. Okay."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "cats-cradle",
        "title": "Keep the cat's cradle",
        "about": "Jolyne leaves the string tied between your wrists, and says it'll hold for a while.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "earbuds"
          }
        ]
      }
    ]
  },
  {
    "key": "jolyne-green-dolphin-street",
    "title": "Green Dolphin Street",
    "gates": 5,
    "about": "Jolyne's father, and the prison she broke out of, which she never talks about.",
    "offer": [
      "them (dismayed): My dad came for me. I'd never met him before.",
      "them: Come to the arena tonight. I want to tell you the rest."
    ],
    "stages": [
      {
        "text": "Meet Jolyne at the arena in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              2
            ],
            "scene": "World: Jolyne Cujoh, Arena",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Connected Hope, Jolyne",
        "objectives": [
          {
            "do": "have_card",
            "card": "JJ/SE42-E54"
          }
        ]
      },
      {
        "text": "Give Jolyne your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Jolyne Cujoh",
            "script": [
              "them: Is it too late to start knowing him?",
              "them (pleased): ...Thanks for saying it's not. I needed that."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "not-too-late",
        "title": "Say it's not too late",
        "about": "Jolyne sets off to see her father, and asks you to be there when she does.",
        "rewards": [
          {
            "coins": 600
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
JOLYNE_CUJOH_SCENES = [
  {
    "name": "World: Jolyne Cujoh, Beach",
    "lines": [
      "background beach",
      "me enters right with slide",
      "me: Watch me come apart into string. Don't scream.",
      "player: I won't.",
      "me (pleased): You didn't even blink. Good. Now, cat's cradle.",
      "me: Look at that. You're tied to me now, a little."
    ]
  },
  {
    "name": "World: Jolyne Cujoh, Arena",
    "lines": [
      "background arena",
      "me enters center with rise",
      "me: My dad came for me. I'd never met him before.",
      "player: What was he like?",
      "me (dismayed): Stubborn. Like me. It's a bit terrifying.",
      "me: Is it too late to start knowing him? Honestly."
    ]
  }
]
ECHIDNA_QUESTS = [
  {
    "key": "echidna-tea-party",
    "title": "Tea Party",
    "gates": 2,
    "about": "The Witch of Greed invites the player to a tea that isn't tea, and asks questions for the joy of the answers.",
    "offer": [
      "them: Come to the library. I'll pour. You'll answer.",
      "them (pleased): How interesting. I mean that as a compliment."
    ],
    "stages": [
      {
        "text": "Take tea with Echidna at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Echidna, Library",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Echidna a strawberry shortcake",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "shortcake",
            "to": "Echidna"
          }
        ]
      },
      {
        "text": "Answer Echidna's questions",
        "objectives": [
          {
            "do": "talk",
            "to": "Echidna",
            "script": [
              "them: Why do you hope? Why do you wait? Answer me properly.",
              "them (pleased): ...How interesting. Really."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "tea-and-questions",
        "title": "Stay for tea",
        "about": "Echidna lets you leave with a cup of something that might not be tea.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "bottled-tea"
          }
        ]
      }
    ]
  },
  {
    "key": "echidna-witchs-contract",
    "title": "The Witch's Contract",
    "gates": 5,
    "about": "Echidna offers to solve Emilia's trial for a price, written in light.",
    "offer": [
      "them: I can solve Emilia's trial for her. For a price.",
      "them (pleased): Meet me in the forest tonight. The contract is ready."
    ],
    "stages": [
      {
        "text": "Meet Echidna in the forest at night",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              3
            ],
            "scene": "World: Echidna, Forest",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Embodiment of the Thirst for Knowledge, Echidna",
        "objectives": [
          {
            "do": "have_card",
            "card": "RZ/S116-E008"
          }
        ]
      },
      {
        "text": "Give Echidna your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Echidna",
            "script": [
              "them: Bring Emilia here to sign it. You'll do that for me.",
              "them (pleased): ...Lovely. The contract will wait for her."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "sign-the-contract",
        "title": "Sign the contract",
        "about": "Echidna signs the contract in light. Emilia's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "emilia-the-trial"
        ]
      },
      {
        "key": "refuse-the-contract",
        "title": "Refuse the contract",
        "about": "Echidna sighs, and says she'll keep the offer warm.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "playmat"
          }
        ]
      }
    ]
  }
]
ECHIDNA_SCENES = [
  {
    "name": "World: Echidna, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Pour, and I'll ask you something. How interesting.",
      "player: What's the question?",
      "me (pleased): Why do you wait for things you can't have?",
      "player: Because I hope they'll come.",
      "me (dismayed): ...How interesting. And sincere. That's worse."
    ]
  },
  {
    "name": "World: Echidna, Forest",
    "lines": [
      "background forest",
      "me enters left with fade",
      "me: The contract is written in light. Look at it closely.",
      "player: It looks dangerous.",
      "me (pleased): It is. That's why it's worth signing.",
      "me: Bring Emilia here. She'll sign it, one way or another."
    ]
  }
]
EMILIA_QUESTS = [
  {
    "key": "emilia-puck",
    "title": "Puck",
    "gates": 2,
    "about": "Emilia talks to her little cat spirit and introduces the player to it, formally.",
    "offer": [
      "them: This is Puck. Puck, this is {player}. Be polite.",
      "them (pleased): Puck approves of you. I'm very glad."
    ],
    "stages": [
      {
        "text": "Walk with Emilia in the forest in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              0
            ],
            "scene": "World: Emilia, Forest",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Let's Sing of the Future Together With You, Emilia",
        "objectives": [
          {
            "do": "have_card",
            "card": "RZ/S116-E026"
          }
        ]
      },
      {
        "text": "Let Emilia introduce you properly",
        "objectives": [
          {
            "do": "talk",
            "to": "Emilia",
            "script": [
              "them: Puck would like to meet you again. Formally, of course.",
              "them (pleased): You're my first proper friend in the forest. Thank you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "puck-approves",
        "title": "Be introduced to Puck",
        "about": "Puck curls up on your shoulder for the rest of the walk, and Emilia can't stop smiling.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "plushie"
          }
        ]
      }
    ]
  },
  {
    "key": "emilia-the-trial",
    "title": "The Trial",
    "gates": 5,
    "about": "Emilia must face her past in the tomb, on her own terms, and she's frightened of the witch's help.",
    "offer": [
      "them (dismayed): I saw the frozen forest in my trial. I have to go back.",
      "them: Meet me at the shrine tonight. Please come."
    ],
    "stages": [
      {
        "text": "Meet Emilia at the shrine in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "shrine",
            "times": [
              2
            ],
            "scene": "World: Emilia, Shrine",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Emilia: Derived Conclusion, Emilia in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "RZ/S116-E027",
            "against": [
              "Emilia"
            ]
          }
        ]
      },
      {
        "text": "Give Emilia your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Emilia",
            "script": [
              "them: I'll do it without the witch's help. I have to.",
              "them (pleased): ...Then I'm not alone. Thank you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "her-own-terms",
        "title": "Face the trial on her own terms",
        "about": "Emilia goes into the tomb alone, and comes out steadier. Echidna's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "echidna-witchs-contract"
        ]
      },
      {
        "key": "accept-the-help",
        "title": "Accept the witch's help",
        "about": "Emilia takes the help, and says she'll think about the cost later.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "bottled-tea"
          }
        ]
      }
    ]
  }
]
EMILIA_SCENES = [
  {
    "name": "World: Emilia, Forest",
    "lines": [
      "background forest",
      "me enters right with slide",
      "me: Puck! Be nice. This is the one I told you about.",
      "player: Hello, Puck.",
      "me (pleased): Puck says hello back. Formally. He likes you.",
      "me: We don't get many visitors in the forest. You're very welcome."
    ]
  },
  {
    "name": "World: Emilia, Shrine",
    "lines": [
      "background shrine",
      "me enters center with fade",
      "me: In the trial, I saw the frozen forest. I have to go back.",
      "player: Alone?",
      "me (dismayed): On my own terms. The witch offered to help, and I can't take it.",
      "me: Will you come with me to the tomb? Please?"
    ]
  }
]
RAM_REM_QUESTS = [
  {
    "key": "ram-rem-maid-duties",
    "title": "Maid Duties",
    "gates": 2,
    "about": "The twins are short a pair of hands at the mansion, and Ram calls the player barely adequate.",
    "offer": [
      "them: We're short of hands at the mansion. Are you useful?",
      "them (pleased): Rem says you're useful. I say you're barely adequate."
    ],
    "stages": [
      {
        "text": "Help the twins at the cafe in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              0
            ],
            "scene": "World: Ram/Rem, Cafe",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Give Ram and Rem a melon bread for the staff",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "melon-bread",
            "to": "Ram/Rem"
          }
        ]
      },
      {
        "text": "Hear Ram's verdict",
        "objectives": [
          {
            "do": "talk",
            "to": "Ram/Rem",
            "script": [
              "them: You're barely adequate. Rem thinks it's high praise.",
              "them (pleased): ...Don't tell Rem I said so. She'd cry."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "barely-adequate",
        "title": "Accept barely adequate",
        "about": "Ram gives you a small job and a nod. Rem beams at you across the room.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "instant-ramen"
          }
        ]
      }
    ]
  },
  {
    "key": "ram-rem-twin-horns",
    "title": "Twin Horns",
    "gates": 5,
    "about": "Rem's guilt about the night of the fire, and the horn Ram lost.",
    "offer": [
      "them (dismayed): The night of the fire. Rem still can't forget it.",
      "them: Come to the forest in the evening. Ram would rather I didn't say this."
    ],
    "stages": [
      {
        "text": "Walk with the twins in the forest in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              2
            ],
            "scene": "World: Ram/Rem, Forest",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Rem: Demon's Demeanor, Rem in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "RZ/S46-E067",
            "against": [
              "Ram/Rem"
            ]
          }
        ]
      },
      {
        "text": "Give the twins your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Ram/Rem",
            "script": [
              "them: Ram tells me to stop apologising. I can't yet.",
              "them (pleased): ...Thank you for seeing who's been holding up whom."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "see-who-holds",
        "title": "See who holds whom up",
        "about": "Rem stops apologising for an afternoon. Ram pretends not to notice, and is very pleased.",
        "rewards": [
          {
            "coins": 600
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
RAM_REM_SCENES = [
  {
    "name": "World: Ram/Rem, Cafe",
    "lines": [
      "background cafe",
      "me enters left with slide",
      "me: Ram gives the orders. Rem does the work. Let's begin.",
      "player: Which of you is which?",
      "me (pleased): I'm Ram. She's Rem. Don't mix us up or Rem will cry.",
      "me: Barely adequate. That's a compliment from me. Remember it."
    ]
  },
  {
    "name": "World: Ram/Rem, Forest",
    "lines": [
      "background forest",
      "me enters center with fade",
      "me: The night of the fire. I still think about it.",
      "player: Rem, you don't have to tell me.",
      "me (dismayed): I want to. Ram keeps telling me to stop apologising.",
      "me: Thank you for listening. Really."
    ]
  }
]

CAST = [
    cpu("Aira", "aloof", quests=AIRA_QUESTS, extra_scenes=AIRA_SCENES,
        haunts=[("school", "wk", "01", 55), ("plaza", "we", "12", 45), ("cafe", "135", "2", 30)],
        tastes=(["cute"], ["fancy", "sweet"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to practise my destiny pose. It's very important.", "them (pleased): Tomorrow I'll announce my powers to the school. You may cheer.", "them (pleased): Tonight I'll consult the spirit. Stay, if you want to hear it."], "past": ["them: Earlier I told the whole class I was a hero. Some of them clapped.", "them (pleased): This morning I fell off a bench. It was a sign, I'm sure.", "them (pleased): Earlier I cried a little about the spirit's daughter. Don't tell Okarun."], "like": {"with": "Okarun", "lines": ["them: You're nothing like Okarun. He's so weird and so loud about it.", "them: You're a bit like Okarun. Hm, not as weird, I hope.", "them (pleased): You're like Okarun, {player}, but you're actually cool. That's rare."]}, "dislike": {"with": "Momo Ayase", "lines": ["them: You're so much like Momo. Always judging my hair.", "them: There's a bit of Momo in you. Stop it!", "them (pleased): You're nothing like Momo, {player}. Good, she's annoying."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. The chosen one doesn't need a bracket."], ["them: Not entering. Destiny will find me at the next one."], ["them (pleased): I'm not in it, but I'll cheer for you as my chosen champion."]], "entrant": [["them: I'm in the bracket! Destiny says I'll win. Obviously.", "them: Don't be jealous. Okay, a little is fine."], ["them: We're both in it! Hm. A rival worthy of me.", "them (pleased): Let's give the crowd a show of destiny."], ["them (pleased): You and me in the same bracket. I'd like you to be my last opponent."]], "out": [["them: You're out? Hm. Destiny has other plans for you, I think."], ["them: You lost. Don't worry, you were a good follower."], ["them (pleased): You're out, but my chosen friend. Come with me, I'll make you feel better."]], "champion": [["them (pleased): Champion! As I said, destiny never lies!"], ["them (pleased): You won! I'll allow you to call yourself my champion. Once."], ["them (pleased): Champion, {player}! The spirit says you're my most important friend."]], "duel": [["them: It's our round! Prepare to meet my destiny!", "them: Don't cry when I win. Destiny is cruel, sometimes."], ["them (pleased): Round time! My destiny is ready!", "them: Don't hold back. I won't."], ["them (pleased): Our round, {player}. Destiny says I'll win. I'd rather it didn't."]]},
            "mid": {"1": ["them: You're starting to recognise my destiny. Good.", "them: The spirit approved of you, I think. Maybe.", "them: Are you going to follow me around now? Fine, but keep up.", "them: I'm the chosen one, and you're... acceptable as a companion.", "them: Ask me anything about my destiny. I'll answer, but briefly."], "3": ["them (pleased): You've been a loyal follower. The spirit likes you, I'm sure.", "them: I don't say this to many people, but you make me less scared of destiny.", "them (pleased): Come to the plaza with me. I want to show you my favourite spot.", "them: Okarun is still not convinced I'm the chosen one. You believe me, right?", "them (pleased): You're a real friend. Don't tell the spirit I said that."], "5": ["them (pleased): {player}, my best friend. You're the one who believes in me most.", "them: Whatever destiny says, I'd choose you as my companion.", "them (pleased): Let's go to the plaza at night. The spirit can watch us.", "them: The spirit's daughter is lost, but I'm not alone any more. Thanks to you.", "them (pleased): Best friend! I'll be the chosen one, and you'll be my chosen friend!"]},
            "hello_steps": [["them: Hm? A commoner seeks an audience with the chosen one?", "them: Oh, a visitor. State your name, chosen one's admirer."], ["them: Hello. You may approach, if you're worthy.", "them: Oh. You came. Fine."], ["them (pleased): Oh, it's my follower! I-I mean, it's you!", "them (pleased): {player}! You came to see me. Obviously."], ["them (pleased): You came to see me! Of course you did. Obviously.", "them (pleased): {player}! Hi! Don't tell anyone I was waiting."], ["them (pleased): {player}! My favourite follower. Sit, sit.", "them (pleased): {player}! The spirit says you're nice. It's right."], ["them (pleased): {player}! My best friend, and the only one who knows about the daughter.", "them (pleased): {player}. I'm glad you came. Really glad."]],
            "bye_steps": [["them: You're dismissed!", "them: Go, chosen admirer!"], ["them: You may go! For now!", "them: Bye! Don't get lost in the destiny!"], ["them (pleased): You may go, {player}! For now!", "them (pleased): See you, {player}! Don't forget to bow!"], ["them (pleased): Come back soon! Not that I'll be waiting!", "them (pleased): Bye, {player}! Be careful out there."], ["them (pleased): Come back soon! ...I'll be waiting, {player}.", "them (pleased): Bye, {player}! Keep my secret safe."], ["them (pleased): Come back, best friend. The spirit misses you too.", "them (pleased): Bye, {player}! You're my destiny, sort of."]],
            "hello": ["them: Hm? A commoner seeks an audience with the chosen one?", "them (pleased): Oh, it's my follower! I-I mean, it's you!", "them (pleased): You came to see me! Of course you did. Obviously."],
            "bye": ["them: You're dismissed!", "them (pleased): You may go! For now!", "them (pleased): Come back soon! Not that I'll be waiting! ...I'll be waiting."],
            "hi": ["them: Bow before me! I'm the chosen one! ...Why are you staring like that?",
                   "them: Ugh, a commoner. Fine, you may speak to me. Briefly."],
            "hi2": "them: Oh. It's you. I suppose I don't mind you being here. Don't get excited.",
            "hi4": "them (pleased): My loyal follower! I mean, my... friend. Whatever! Sit!",
            "again": "them: Again? You're obsessed with me. It's understandable. I'm amazing.",
            "loved": "them (pleased): Cute! I mean, acceptable. Very acceptable. Thank you.",
            "disliked": "them (dismayed): Spicy?! Are you trying to ruin my perfect complexion?",
            "before": "them: The chosen one doesn't lose! Watch me!",
            "won": "them (dismayed): That... doesn't count! I wasn't ready!",
            "lost": "them (pleased): Of course! I'm the chosen one!",
            "r1": "them: You don't laugh at me. Okay. You're tolerable.",
            "r3": "them: Everyone thinks I'm weird. Maybe I am. But being chosen is lonely, you know?",
            "r4": "them (pleased): You're chosen too. By me. As my best... important person.",
        },
        friend=["background sakura", "me enters left with slide", "me: I have something to confess. And you can't tell anyone.",
                "me: I'm not really chosen. Well, I am, but... I wanted to be special so badly.",
                "player: You're special without being chosen.", "me (dismayed): ...You mean that?",
                "player: I mean it.", "me (pleased): Fine! Then you're my friend. Officially chosen by me!"],
        best=["background dusk", "me enters center with fade", "me: My parents always expected me to be perfect.",
              "me: So I made myself the heroine of my own story. So nobody could see I was scared.",
              "player: You don't have to be the heroine with me.", "me (dismayed): ...Then what am I?",
              "player: My best friend.", "choice", "- Just be Aira.", "- The chosen one chose well.",
              "me (pleased): Okay. Best friends. And I'm still a little bit chosen. Deal with it!"]),

    cpu("Momo Ayase", "friendly", quests=MOMO_AYASE_QUESTS, extra_scenes=MOMO_AYASE_SCENES,
        haunts=[("school", "wk", "01", 55), ("cafe", "we", "12", 45), ("plaza", "135", "2", 35), ("shrine", "024", "3", 25)],
        tastes=(["cool"], ["music", "food", "cute"], ["book"]),
        lines={
            "repeat": {"future": ["them: Next I'm going shopping. I need a new outfit, obviously.", "them (pleased): Tomorrow I'm going to the shrine. You're coming, right?", "them (pleased): Tonight I'm going to the cafe. Save me a seat, okay?"], "past": ["them: Earlier I got a new bag. It's so cute.", "them (pleased): This morning I helped Grandma with a spirit. It was scary.", "them (pleased): Earlier I told Okarun to stop being weird. He didn't listen."], "like": {"with": "Aira", "lines": ["them: You're nothing like Aira. She's so full of herself.", "them: You're a bit like Aira. Dramatic, but I kind of like it.", "them (pleased): You're like Aira, {player}. Confident, and fun to be around."]}, "dislike": {"with": "Okarun", "lines": ["them: You're so much like Okarun. Weird and loud all the time.", "them: There's a bit of Okarun in you. Please stop.", "them (pleased): You're nothing like Okarun, {player}. Phew."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. Gyaru fashion beats brackets."], ["them: Not entering. I'm busy looking cute for the crowd."], ["them (pleased): I'm not in it, but I'll make you a lucky charm for the final!"]], "entrant": [["them: I'm in the bracket! Don't mess with my hair, okay?", "them: I'll win, obviously. Yes, I'm a little scary."], ["them: We're both in it! Oh, that's kind of cool.", "them (pleased): Let's make this a great match. Okay?"], ["them (pleased): You and me in the same bracket, {player}! Win it, and we'll go to the shrine after!"]], "out": [["them: Out already? Ugh, that's so unfair. Come on, let's get bubble tea."], ["them: You lost. Don't worry, you looked super cool doing it."], ["them (pleased): You're out. Come to the shrine. I'll give you a talisman for luck!"]], "champion": [["them (pleased): You won! Okay, that's totally awesome!"], ["them (pleased): Champion! You're amazing, and so is your fashion sense!"], ["them (pleased): Champion, {player}! The most amazing duelist in the whole arena!"]], "duel": [["them: It's our round! Don't mess up my perfect outfit!", "them: Let's do this! Gyaru style!"], ["them (pleased): Round time! Show me your best!", "them: Don't hold back, okay? That's rude."], ["them (pleased): Our round, {player}. I'd hate to beat you, but I'm not losing my cool!"]]},
            "mid": {"1": ["them: Hey, you're not so bad. Don't tell anyone I said that.", "them: Have you seen the new Ken Takakura poster? You have to see it.", "them: Are you afraid of ghosts? Be honest. I won't laugh.", "them: Okarun's weird, but you're fine. I like that.", "them: Want to get something sweet at the cafe? My treat."], "3": ["them (pleased): You're braver than you look. Thanks for coming to the shrine.", "them: I've been thinking about my crush. You're the only one I'd tell.", "them (pleased): Let's go to the shrine and check the talismans. Grandma will love you.", "them: You make Okarun less weird, and that's a miracle.", "them (pleased): You're my favourite lantern holder. I mean that."], "5": ["them (pleased): {player}! My best friend. Grandma says you're my destiny. Ha!", "them: I'd hold any lantern for you, in any shrine.", "them (pleased): Let's go to the shrine tonight. Just the two of us.", "them: You're the one who makes me brave enough to be myself.", "them (pleased): Best friend! Come on, let's go get some crepes!"]},
            "hello_steps": [["them: Hey. Need something?", "them: Oh, hi. Didn't know you were into ghosts."], ["them: Hi. Do you know any good cafes around here?", "them: Hey. Careful, there's a talisman on the floor."], ["them (pleased): Oh, {player}! What's up?", "them (pleased): Hi, {player}! Have you seen the new poster?"], ["them (pleased): {player}! Come sit, I've got a story about the shrine.", "them (pleased): {player}! Don't tell Okarun, but I was hoping you'd come."], ["them (pleased): {player}! Get over here, you weirdo. Missed you.", "them (pleased): {player}! Shrine business again. Come help!"], ["them (pleased): {player}! My best friend, the one who holds the lantern.", "them (pleased): {player}. You're my favourite weirdo. Sit down!"]],
            "bye_steps": [["them: Later.", "them: See ya. Keep away from the ghosts."], ["them: Bye. Don't get possessed.", "them: See you. Take care of yourself."], ["them (pleased): See ya! Watch out for ghosts, {player}!", "them (pleased): Bye, {player}! Keep an eye out for weird stuff!"], ["them (pleased): Go on, {player}! Come back soon for the next job.", "them (pleased): Bye, {player}! Tell me if you see anything strange."], ["them (pleased): Come back soon, okay? Weird stuff's more fun with you.", "them (pleased): See ya, {player}. Don't be a stranger!"], ["them (pleased): Come back, best friend! I'll have the lantern ready.", "them (pleased): Bye, {player}! You're my favourite ghost hunter."]],
            "hello": ["them: Hey. Need something?", "them (pleased): Oh, {player}! What's up?", "them (pleased): {player}! Get over here, you weirdo. Missed you."],
            "bye": ["them: Later.", "them (pleased): See ya! Watch out for ghosts!", "them (pleased): Come back soon, okay? Weird stuff's more fun with you."],
            "hi": ["them: Momo Ayase. I don't care if you're a ghost or an alien. Just don't be a jerk.",
                   "them: You're new. Granny said I'd meet weird people this week."],
            "hi2": "them (pleased): {player}! Okarun's being weird again. Wanna help me bully him a little?",
            "hi4": "them (pleased): You're one of my people now. Ghosts, aliens, you. My weird little family.",
            "again": "them: Back? Cool. I'm bored anyway.",
            "loved": "them (pleased): Oh, this is so cool! You totally get my style.",
            "disliked": "them (dismayed): A textbook? Seriously? Is this a hint?",
            "before": "them: I'll psychic-power you right off the table!",
            "won": "them (dismayed): Dang it! Okay, you're good. Don't tell Okarun.",
            "lost": "them (pleased): Yes! Granny's gonna be so proud.",
            "r1": "them: You're not totally boring. Okarun's boring. You're fine.",
            "r3": "them: People used to say my granny was a fraud. I believed in her anyway. You remind me of her a little. Stubborn.",
            "r4": "them (pleased): If a ghost ever came for you, I'd fight it with my bare hands. Seriously.",
        },
        friend=["background night", "me enters left with slide", "me: Okay, don't freak out, but there's a ghost behind you.",
                "player: What?!", "me (pleased): Kidding! Ha! Your face!",
                "me: Okarun fell for that like ten times.", "me: Seriously though, thanks for hanging out with me.",
                "me: Most people find me too loud. You just laugh. So we're friends now. Done."],
        best=["background rain", "me enters center with fade", "me: Can I be honest? I'm scared of losing people.",
              "me: My dad left. People talk behind my back. I act tough so nothing gets in.",
              "player: Something got in, though.", "me (dismayed): ...Yeah. You did. Annoying.",
              "choice", "- I'm staying, Momo.", "- Tough and soft. Both are fine.",
              "me (pleased): Best friends. If you ever leave, I'll haunt you. Got it?"]),

    cpu("Okarun", "friendly", quests=OKARUN_QUESTS, extra_scenes=OKARUN_SCENES,
        haunts=[("library", "wk", "12", 55), ("school", "we", "01", 40), ("alley", "135", "3", 30)],
        tastes=(["book"], ["game", "sweet", "cards"], ["sporty"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to check the sky for UFOs. Come with me?", "them (pleased): Tomorrow I'll look at my research. You can read it, if you're careful.", "them (pleased): Tonight I'm going to the alley. Bring a flashlight, okay?"], "past": ["them: Earlier I saw a weird light. It was probably a plane.", "them (pleased): This morning I wrote three pages about a ghost. It's a good story.", "them (pleased): Earlier I talked to Momo for five minutes. She hit me once."], "like": {"with": "Momo Ayase", "lines": ["them: You're nothing like Momo. She'd have laughed at my notes.", "them: You're a bit like Momo. Brave, I think, when it counts.", "them (pleased): You're like Momo, {player}, but you believe me. That's the best."]}, "dislike": {"with": "Aira", "lines": ["them: You're so much like Aira, so sure of yourself.", "them: There's a bit of Aira in you. Be careful about destiny.", "them (pleased): You're nothing like Aira, {player}. Good, I don't need a chosen one."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. I'm checking the arena for yokai."], ["them: Not in the bracket. There's something weird in the rafters, I think."], ["them (pleased): I'm not in it, but I'll be taking notes for you. Win for science!"]], "entrant": [["them: I'm in the bracket! Don't be scared of my speed, okay?", "them: Sorry for shouting. I'm just excited to duel!"], ["them: We're both in it! Oh no, I'm nervous. But good nervous!", "them (pleased): Let's see who's the fastest!"], ["them (pleased): You and me in the same bracket! I'm so glad! Really, really glad!"]], "out": [["them: Oh no, you're out. Sorry, I'm not good at this. Um, good match?"], ["them: You lost. But I saw the whole thing, and it was really cool!"], ["them (pleased): You're out. Come look at my notes! I found a yokai in the rafters!"]], "champion": [["them (pleased): You won! I'm writing it in my notes! CHAMPION!"], ["them (pleased): Champion! That's so cool! I'll never doubt you again!"], ["them (pleased): Champion, {player}! I'm honoured to know you!"]], "duel": [["them: It's our round! I'm faster than you think, okay?", "them: Sorry in advance if I'm too quick!"], ["them: Round time! Um, let's go!", "them (pleased): Don't hold back, or it's not fun, right?"], ["them (pleased): Our round, {player}! I'd never want to beat you, but I'll try my best!"]]},
            "mid": {"1": ["them: You're not like the other people who say I'm weird. Thanks.", "them: I've been working on my research. You can have a look, but don't touch.", "them: Do you believe in yokai? Not many do, but you might.", "them: Sorry for shouting before. I get excited about things.", "them: Want to see my clippings? I'll be quick, promise."], "3": ["them (pleased): You actually read my notes. Nobody does that. Thanks.", "them: I'm still scared of the yokai, but you make it less scary.", "them (pleased): Come to the library. I found a new lead.", "them: You're the one who doesn't think I'm crazy. That's rare.", "them (pleased): Momo says you're nice. I agree. Don't tell her I said that."], "5": ["them (pleased): {player}! You're my best friend. Seriously, you're the best.", "them: I'd go after any yokai with you, no matter how weird it is.", "them (pleased): Let's go to the alley tonight. I'll show you the cursed spot.", "them: You're the one who knows the real me, even the nervous bits.", "them (pleased): Best friend! Let's find something amazing together!"]},
            "hello_steps": [["them: Ah! S-sorry! Um, hello!", "them: Hi. Don't mind me, I'm checking the sky."], ["them: Hello. Did you see anything weird lately?", "them: Oh, hi. Are you here for the research?"], ["them (pleased): {player}! Did you see the news about the UFO?!", "them (pleased): {player}! Hi! Want to see my notes?"], ["them (pleased): {player}! I-I'm really glad you're here!", "them (pleased): {player}! I found a new yokai. Come look!"], ["them (pleased): {player}! I'm really glad you came. I was nervous.", "them (pleased): {player}! Sit, I've got the good clippings for you."], ["them (pleased): {player}! My best friend. Don't tell Momo I said that.", "them (pleased): {player}! Come along, I'll show you my favourite spot."]],
            "bye_steps": [["them: B-bye!", "them: Bye! Watch the sky!"], ["them: See ya! Stay safe!", "them: Bye, um, goodbye."], ["them (pleased): See you! Tell me if you see anything weird, {player}!", "them (pleased): Bye, {player}! Don't get possessed!"], ["them (pleased): Go on, {player}! I'll keep the notes safe.", "them (pleased): Bye, {player}! Keep your eyes open."], ["them (pleased): Come back soon, {player}! I'll save you a seat.", "them (pleased): See ya, {player}! I'll miss you. Um."], ["them (pleased): Come back soon, best friend! I'll be waiting!", "them (pleased): Bye, {player}! Stay safe for me!"]],
            "hello": ["them: Ah! S-sorry! Um, hello!", "them (pleased): {player}! Did you see the news about the UFO?!", "them (pleased): {player}! I-I'm really glad you're here!"],
            "bye": ["them: B-bye!", "them (pleased): See you! Tell me if you see anything weird!", "them (pleased): Come back soon! I'll... I'll save you a seat!"],
            "hi": ["them: I-I'm Okarun! Do you believe in aliens? No? Ghosts? Both? Neither? Sorry!",
                   "them: Oh, a duel? I-I'm not scared! Okay, I'm a little scared."],
            "hi2": "them (pleased): {player}! I found a new UFO sighting report! Do you want to read it with me?",
            "hi4": "them (pleased): You're my best... my... f-friend. Ahh, that sounded so weird!",
            "again": "them: You came back? For me? Wow.",
            "loved": "them (pleased): An occult book?! This is amazing! I'll read it tonight!",
            "disliked": "them (dismayed): Sports stuff... I'd probably trip on it. Thanks though!",
            "before": "them: I won't run away! I'll do my best!",
            "won": "them (dismayed): You're so good. I need to practise more.",
            "lost": "them (pleased): I-I won? I won! Momo, did you see?!",
            "r1": "them: You don't think I'm a creep. That's... really nice.",
            "r3": "them: I got bullied a lot. For liking aliens. You never made fun of me once.",
            "r4": "them (pleased): You make me brave. Like I could fight a whole yokai with you around.",
        },
        friend=["background library", "me enters left with fade", "me: So, um, I have a theory about the town's urban legends.",
                "me: There are seven! And I've only found three!", "player: Want help finding the rest?",
                "me (pleased): You'd help me?! Really?!", "me bounces",
                "me: Nobody ever wants to help with my stuff. You're my friend! An occult research partner!"],
        best=["background night", "me enters center with fade", "me: Remember when you said you didn't believe in ghosts?",
              "me: I didn't care. You listened anyway.", "me (dismayed): I used to eat lunch alone every day.",
              "player: Not anymore.", "me: Not anymore. Because of you and Momo.",
              "choice", "- You're my best friend, Okarun.", "- Let's find all seven legends.",
              "me (pleased): Best friend! I'll remember this forever! Even if aliens wipe my memory!"]),

    cpu("Cinder Fall", "villain", quests=CINDER_FALL_QUESTS, extra_scenes=CINDER_FALL_SCENES,
        haunts=[("alley", "all", "23", 65), ("warehouse", "wk", "3", 45), ("arena", "135", "1", 30, 2)],
        tastes=(["fancy"], ["cool", "spicy"], ["cute"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to train my flames. Don't stand too close.", "them (pleased): Tomorrow I'll walk the city. Come and see what I'm building.", "them (pleased): Tonight I'm going to the warehouse. You can come along, if you're brave."], "past": ["them: Earlier I burnt a whole table. It was an accident.", "them (pleased): This morning I thought about the maiden's power. Often.", "them (pleased): Earlier I watched Ruby fight. She's getting stronger."], "like": {"with": "Ozpin", "lines": ["them: You're nothing like Ozpin. He'd have been more honest with me.", "them: You're a bit like Ozpin. Careful, I think, and calculating.", "them (pleased): You're like Ozpin, {player}. Patient, and you see the bigger picture."]}, "dislike": {"with": "Ruby Rose", "lines": ["them: You're so much like Ruby. Bright, and in my way.", "them: There's a bit of Ruby in your eyes. I don't like it.", "them (pleased): You're nothing like Ruby, {player}. Good, I need an ally, not a rival."]}},
            "tournament": {"spectator": [["them: The tournament is a child's game. I'm only here to watch the flames."], ["them: I'm not entering. I'd burn the whole bracket down."], ["them (pleased): I'm not in it. Win the final, and show them what power looks like."]], "entrant": [["them: I'm in the bracket. The flames are ready for you.", "them: Be careful. I'm not kind in the arena."], ["them: We're both in it. Hm. This will be interesting.", "them (pleased): Let's see whose fire burns brighter."], ["them (pleased): You and me in the same bracket. Win it, and we'll take the power together."]], "out": [["them: You're out. The power would have been yours, if you'd listened."], ["them: You lost. Hm. You were worth watching, though."], ["them (pleased): You're out. Come to the alley. I have something to show you."]], "champion": [["them (pleased): Champion. The flames approve of you."], ["them (pleased): You won. Good. I'd expect nothing less from my ally."], ["them (pleased): Champion, {player}. Together, we'd take everything."]], "duel": [["them: Round time. Burn bright, or burn out.", "them: No mercy in the arena. Not from me."], ["them: It's our round. Show me the power you're hiding.", "them (pleased): Give me your best flame."], ["them (pleased): Our round, {player}. I'd rather you were my ally, but here we are."]]},
            "mid": {"1": ["them: You've got nerve. I respect that.", "them: Watch your step. The embers are hot tonight.", "them: You've seen my power. Most people run. You stayed.", "them: I don't trust many people. You might be the exception.", "them: Ask me one thing about the Fall. I'll answer, and then you go."], "3": ["them (pleased): You're one of the few who understands wanting more.", "them: Let's stop pretending you're just a passer-by. You're my ally, aren't you?", "them (pleased): Come to the warehouse at night. I'll show you what the power can do.", "them: I like how you think. You'd have made a fine maiden.", "them (pleased): You're the only one who doesn't flinch when the glass hums."], "5": ["them (pleased): {player}. You're my closest ally. Don't betray me.", "them: Together we'd take Beacon and the whole kingdom. That's a promise.", "them (pleased): Walk with me in the alley. The power feels warmer with you.", "them: You're the only one I'd share the power with.", "them (pleased): Best friend. Let's take what we're owed, together."]},
            "hello_steps": [["them: Can I help you?", "them: Hm. You don't look like a hunter. Good."], ["them: Oh. You found me. Good.", "them: Hello. Stand a little further away, please."], ["them (pleased): Ah, there you are. I wondered when you'd find me.", "them (pleased): {player}. Sit by the fire. It's warmer that way."], ["them (pleased): {player}. You're the one I wanted to see tonight.", "them (pleased): {player}. Come closer. You're safe with me."], ["them (pleased): My favourite. Come closer, {player}.", "them (pleased): {player}. I was hoping you'd come. Stay a while."], ["them (pleased): {player}. The only one I trust with my plans.", "them (pleased): {player}. Come here. Let's talk about the future."]],
            "bye_steps": [["them: Run along.", "them: Off you go."], ["them: Until next time.", "them: Go. Be careful."], ["them (pleased): Until next time, {player}.", "them (pleased): Go, {player}. Don't get burned."], ["them (pleased): Come back soon, {player}. I have plans for us.", "them (pleased): Bye, {player}. The night's getting colder."], ["them (pleased): Come back soon. I'll be waiting, {player}.", "them (pleased): Bye, {player}. Don't tell the others where I am."], ["them (pleased): Come back soon, best friend. The power's better with you.", "them (pleased): Bye, {player}. You're the only one I'd spare."]],
            "cold": "them: Ruby stopped me. Remember this when she comes asking for help again.",
            "hello": ["them: Can I help you?", "them (pleased): Ah, there you are. I wondered when you'd find me.", "them (pleased): My favourite. Come closer."],
            "bye": ["them: Run along.", "them (pleased): Until next time.", "them (pleased): Come back soon. I have plans for us."],
            "hi": ["them: We have big plans for you. All we ask is... a little cooperation.",
                   "them: Out in the dark, all alone? How brave. How foolish."],
            "hi2": "them: You keep finding me. Persistent little moth.",
            "hi4": "them (pleased): Ah, my favourite pawn. ...Friend. You may say friend.",
            "again": "them: Again? I'm beginning to think you enjoy danger.",
            "loved": "them (pleased): Something worthy of a queen. You have taste.",
            "disliked": "them (dismayed): How childish. Am I a little girl to you?",
            "before": "them: Fall, little one.",
            "won": "them (dismayed): ...This changes nothing.",
            "lost": "them (pleased): Kneel. It suits you.",
            "r1": "them: You don't fear me. That's either brave or stupid. I'm curious which.",
            "r3": "them: I was nothing once. A servant. Mocked and burned. I took power because no one would give it to me.",
            "r4": "them: You keep offering me something I never asked for. I'm starting to want it.",
        },
        friend=["background crimson", "me enters right with fade", "me: Power is the only thing that matters.",
                "me: People are tools, or obstacles. Which are you?", "player: Neither. I'm a friend.",
                "me (dismayed): ...Ridiculous.", "me: And yet I keep letting you near me.",
                "me (pleased): Fine. Friend. Don't make me burn it."],
        best=["background night", "me enters center with fade", "me: When I was young, I was a servant. They called me Cinder as an insult.",
              "me: I took the name and made it mean fire.", "player: You're more than your anger.",
              "me (dismayed): Am I? Then what's left?", "player: Whoever you choose to be.",
              "choice", "- I'm your friend, Cinder.", "- You don't have to burn anymore.",
              "me (pleased): Best friend. Heh. The maiden of fall with a friend. How the others would laugh."]),

    cpu("Ruby Rose", "warm", quests=RUBY_ROSE_QUESTS, extra_scenes=RUBY_ROSE_SCENES,
        haunts=[("cafe", "wk", "12", 55), ("arena", "we", "12", 45), ("plaza", "135", "0", 35)],
        tastes=(["sweet"], ["cool", "game"], ["fancy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to practise with Crescent Rose. Watch the rack!", "them (pleased): Tomorrow Weiss and I are going to the library. You can come, but no pranks.", "them (pleased): Tonight I'll make cookies. Come and taste them, please."], "past": ["them: Earlier I knocked over a whole rack again. Sorry.", "them (pleased): This morning I thought about Mum. It made me sad, but okay.", "them (pleased): Earlier I talked to Yang. She teased me, of course."], "like": {"with": "Yang Xiao Long", "lines": ["them: You're nothing like Yang. She'd have teased me for the rack thing.", "them: You're a bit like Yang. Funny, I think, when you're not scowling.", "them (pleased): You're like Yang, {player}, but nicer to me. That's my favourite kind of sister."]}, "dislike": {"with": "Cinder Fall", "lines": ["them: You're so much like Cinder. Scary and always smiling wrong.", "them: There's a bit of Cinder in you. Please stop looking at me like that.", "them (pleased): You're nothing like Cinder, {player}. Thank goodness!"]}},
            "tournament": {"spectator": [["them: I'm not in the tournament, but I've got cookies for the crowd!"], ["them: Not in the bracket! But I'll cheer for you super loud!"], ["them (pleased): I'm not entering. I'm your cheerleader, okay?"]], "entrant": [["them: I'm in the bracket! Crescent Rose is ready to rumble!", "them: Don't cry if I win. Okay, cry a little. It's fine."], ["them: We're both in it! Yay! Let's make it a show!", "them (pleased): I've got a new trick for the final, watch!"], ["them (pleased): You and me in the bracket! Win it, and we'll share the cookies!"]], "out": [["them: Aww, you're out? Come have a cookie. Right now."], ["them: You lost, but you were so cool out there!"], ["them (pleased): You're out. Come to the cafe. I'll buy you a whole plate."]], "champion": [["them (pleased): You won! I'm so proud, I'm going to scream!"], ["them (pleased): Champion! You're my hero, and my best friend!"], ["them (pleased): Champion, {player}! Team RWBY's favourite duelist!"]], "duel": [["them: It's our round! Crescent Rose says hi!", "them: No holding back, okay? That's no fun!"], ["them (pleased): Round time! Let's go, let's go!", "them: I'm ready! Are you?"], ["them (pleased): Our round, {player}! I'd rather win by cookies, but I'll try!"]]},
            "mid": {"1": ["them (pleased): You're fun! Do you like cookies? Everybody likes cookies!", "them: Hey, you're in my way! Oops, sorry, come sit.", "them (pleased): You're not scared of Crescent Rose, are you? She's a good girl.", "them: I'm still learning how to make friends. You're doing a great job helping.", "them (pleased): Want to see my silver eyes? They glow a little."], "3": ["them (pleased): You're the best at listening. Thanks for that.", "them: I think about my mum a lot when I'm fighting. You help me remember her.", "them (pleased): Let's go to the cafe, I'll buy you a cookie. Or three.", "them: You make the team feel bigger. Like we're really a family.", "them (pleased): You remind me of Yang. You're really cool. Just like her."], "5": ["them (pleased): {player}! My best friend in the whole world! Yay!", "them: You're the one I'd trust with my eyes, my scythe, and my cookies.", "them (pleased): Let's go to the arena and do a duel together, just for fun!", "them: I don't have to be the leader alone. You make it feel shared.", "them (pleased): Best friend! Team RWBY plus you forever! Okay?"]},
            "hello_steps": [["them (pleased): Oh, hi! Are you here for weapons? Or cookies?", "them (pleased): Hey! Watch out for the cookie crumbs."], ["them (pleased): Hi! Want to see my scythe?", "them (pleased): Oh, hi! Are you new in town?"], ["them (pleased): {player}! Yay! Do you want to see my new upgrade?", "them (pleased): {player}! Hi! Did you bring cookies?"], ["them (pleased): {player}! You're here! Okay, I'm gonna show you Crescent Rose.", "them (pleased): {player}! Did you see me on the rack? Haha."], ["them (pleased): {player}! Best day ever! Come here, sit with me.", "them (pleased): {player}! Team RWBY is missing its favourite person!"], ["them (pleased): {player}! My best friend. I'll always share my cookies with you.", "them (pleased): {player}! Come on, let's do something awesome today."]],
            "bye_steps": [["them (pleased): Bye! Stay sharp!", "them (pleased): See ya! Watch your back!"], ["them (pleased): Later! Be safe out there!", "them (pleased): Bye! Keep that smile!"], ["them (pleased): See ya! Bring cookies next time, {player}!", "them (pleased): Bye, {player}! Don't get hurt!"], ["them (pleased): Go on, {player}! Come back soon!", "them (pleased): Bye, {player}! I'll be sharpening Crescent Rose for you."], ["them (pleased): Come back soon, okay? Team RWBY plus one, remember!", "them (pleased): Bye, {player}! Don't forget your cookies!"], ["them (pleased): Come back, best friend! I'll keep your cookies warm!", "them (pleased): Bye, {player}! Team RWBY plus one, forever!"]],
            "cold": "them (dismayed): She took the power. Then I can't keep calling her my friend.",
            "hello": ["them (pleased): Oh, hi! Are you here for weapons? Or cookies?", "them (pleased): {player}! Yay! Do you want to see my new upgrade?", "them (pleased): {player}!! Best day ever! Come here!"],
            "bye": ["them (pleased): Bye! Stay sharp!", "them (pleased): See ya! Bring cookies next time!", "them (pleased): Come back soon, okay? Team RWBY plus one, remember!"],
            "hi": ["them (pleased): Hi! I'm Ruby! Do you like weapons? I love weapons! Crescent Rose is a sniper scythe!",
                   "them: Oh! Are you... robbing me? No? Okay! Let's duel, then!"],
            "hi2": "them (pleased): {player}! I saved you a cookie! Okay, I ate one. But I saved you two!",
            "hi4": "them (pleased): My bestie! Team RWBY plus one! Team RWBYP? We'll work on it!",
            "again": "them: You're back! Yay!",
            "loved": "them (pleased): COOKIES! You're the best! The very best!",
            "disliked": "them (dismayed): Ooh, fancy... I'll give it to Weiss. She likes fancy.",
            "before": "them: Crescent Rose, let's go!",
            "won": "them (dismayed): Aww! You're really good! Teach me your tricks!",
            "lost": "them (pleased): Woo! Rose petals for the win!",
            "r1": "them (pleased): You're super fun to talk to! Like, almost as fun as weapons!",
            "r3": "them: My mom was a huntress. She went on a mission and never came back. I try to be like her. You make it easier.",
            "r4": "them (pleased): You're a hero, you know that? Not with a scythe. Just... by being nice.",
        },
        friend=["background city", "me enters left with pop", "me: Okay, I made something! A friendship scythe!",
                "player: Is that a... cookie shaped like a scythe?", "me (pleased): It's edible weaponry!",
                "me: Yang says I need more friends who aren't weapons. So! You're a friend who isn't a weapon!",
                "me bounces", "me: That's the highest honour."],
        best=["background dusk", "me enters center with fade", "me: You know what I want to be? A hero, like in the stories.",
              "me (dismayed): But the world keeps getting darker. Sometimes I wonder if heroes are real.",
              "player: They are. I'm looking at one.", "me: ...Really?",
              "choice", "- You're my hero, Ruby.", "- Heroes need best friends too.",
              "me (pleased): Best friends! Forever and ever and cookies and ever!"]),

    cpu("Weiss Schnee", "aloof", quests=WEISS_SCHNEE_QUESTS, extra_scenes=WEISS_SCHNEE_SCENES,
        haunts=[("library", "wk", "12", 55), ("cafe", "we", "12", 45), ("arena", "135", "2", 30)],
        tastes=(["fancy"], ["music", "sweet"], ["food"]),
        lines={
            "repeat": {"future": ["them: Next I'm reviewing my notes. Do not interrupt.", "them (pleased): Tomorrow I shall visit the arena. You may accompany me.", "them (pleased): Tonight I'll attempt the glyph again. Stay, if you're quiet."], "past": ["them: Earlier I corrected a teacher's mistake. Publicly, I'm afraid.", "them (pleased): This morning I argued with Ruby about cookies. I was right.", "them (pleased): Earlier I thought about my father, for longer than I'd like."], "like": {"with": "Ruby Rose", "lines": ["them: You're nothing like Ruby. She is far too reckless.", "them: You're a bit like Ruby. Bright, though I'd never say so to her.", "them (pleased): You're like Ruby, {player}, but you can keep a plan. A fine partner."]}, "dislike": {"with": "Cinder Fall", "lines": ["them: You're so much like Cinder. Cold, and tiresome.", "them: There's a trace of Cinder in you. I won't have it.", "them (pleased): You're nothing like Cinder, {player}. I'm glad to say that."]}},
            "tournament": {"spectator": [["them: I am not in the tournament. The bracket is poorly organised, in any case."], ["them: Not entering. I have better things to do with my time."], ["them (pleased): I am not in it. Win it, and I'll concede you have manners."]], "entrant": [["them: I am in the bracket. I will not lose to anyone less prepared than I.", "them: Be prepared. I am."], ["them: We are both in it. Hm. You are not a complete disaster.", "them (pleased): Let us see who has the better plan."], ["them (pleased): You and I in the same bracket. I'd like the final to be ours."]], "out": [["them: You are out. A regrettable result. Prepare better next time."], ["them: You lost. That is acceptable, if you learned from it."], ["them (pleased): You're out. Come study with me. I'll correct your notes."]], "champion": [["them (pleased): You won. Adequate. Very adequate. Congratulations."], ["them (pleased): Champion. I'm not crying. It's the wind."], ["them (pleased): Champion, {player}. The Schnee name would approve of you."]], "duel": [["them: It's our round. Prepare yourself, and do not waste my time.", "them: I will not be merciful. Nor should you be."], ["them: Round time. Show me your best strategy.", "them (pleased): I'll do my best. I expect the same from you."], ["them (pleased): Our round, {player}. I'd rather summon my knight with you watching."]]},
            "mid": {"1": ["them: Your notes are passable. Barely.", "them: Do you always make such a mess? Never mind, don't answer that.", "them: I'll admit you're not a complete disaster.", "them: Ask me a question about the glyph, if you're curious.", "them: Mind the books. They're expensive."], "3": ["them (pleased): You've got better manners than most. I noticed.", "them: My father expected perfection. You make me feel like I can be imperfect.", "them (pleased): Come to the library tomorrow. I'll show you my best notes.", "them: You're the only partner who never makes me explain the plan twice.", "them (pleased): I'd like you to see the knight one day. He's magnificent."], "5": ["them (pleased): {player}, my partner in everything. Don't make me say it twice.", "them: Honestly, I'd trust you with the Schnee name. That's saying something.", "them (pleased): Let's go to the arena. I'd like to summon the knight with you watching.", "them: You're the only one who sees me, not the heiress.", "them (pleased): Best friend. I'm glad you're here, and I'm not embarrassed to say so."]},
            "hello_steps": [["them: Yes? Is there something you need?", "them: Hm. Mind the stack of books, please."], ["them: Oh. Hello, I suppose.", "them: Hi. Don't touch the notes."], ["them: Oh. It's you. Hello, I suppose.", "them: {player}. You're late, but I'll allow it."], ["them (pleased): {player}. Good, someone with manners has arrived.", "them (pleased): {player}. Hello. Sit, I've corrected your notes."], ["them (pleased): {player}. Good. Someone with manners has arrived.", "them (pleased): {player}. I'm glad you came. Don't tell anyone."], ["them (pleased): {player}. The one partner I'd trust with the knight.", "them (pleased): {player}. Sit with me. I'd like to try the glyph again."]],
            "bye_steps": [["them: Goodbye.", "them: Good day."], ["them: Do try to keep up next time.", "them: Goodbye. Don't lose your books."], ["them: Goodbye, {player}. Do try to keep up.", "them: Good day, {player}. Mind your posture."], ["them (pleased): Don't be gone long, {player}. ...I'd notice.", "them (pleased): Bye, {player}. Write me if you go anywhere."], ["them (pleased): Don't be gone long. I'll have new notes ready, {player}.", "them (pleased): Go, {player}. Come back soon, I've got a study plan."], ["them (pleased): Don't be gone long, best partner. I'd notice everything.", "them (pleased): Bye, {player}. The knight will be waiting for you."]],
            "hello": ["them: Yes? Is there something you need?", "them: Oh. It's you. Hello, I suppose.", "them (pleased): {player}. Good, someone with manners has arrived."],
            "bye": ["them: Goodbye.", "them: Do try to keep up next time.", "them (pleased): Don't be gone long. ...I'd notice."],
            "hi": ["them: I am Weiss Schnee, heiress to the Schnee Dust Company. Try to keep up.",
                   "them: If you're here to waste my time, please don't."],
            "hi2": "them: {player}. Your timing is... acceptable today.",
            "hi4": "them (pleased): I suppose I'm glad you're here. Don't repeat that to Ruby.",
            "again": "them: You're persistent. Like a dolt. A charming dolt.",
            "loved": "them (pleased): How refined. You do have some taste after all.",
            "disliked": "them (dismayed): Instant ramen? Is this a joke? Am I a student on a budget?",
            "before": "them: Glyphs. Precision. Elegance. Observe.",
            "won": "them (dismayed): Hmph. Beginner's luck. Clearly.",
            "lost": "them (pleased): As expected.",
            "r1": "them: You're less of a dolt than I assumed. That's a compliment.",
            "r3": "them: My father controlled everything. Who I talked to, what I sang. You're the first person I chose myself.",
            "r4": "them (pleased): I wrote a song. It's about friendship. ...It's about you. Don't you dare laugh.",
        },
        friend=["background castle", "me enters right with fade", "me: I'm practising for a recital. You may listen. Quietly.",
                "me sways", "narrator: Her voice is clear and cold as snow, then suddenly warm.",
                "player: That was beautiful, Weiss.", "me (pleased): ...Thank you.",
                "me: My father only ever said it was adequate.", "me: You're... my friend. I've decided. Accept it with dignity."],
        best=["background snow", "me enters center with fade", "me: My family is all appearances. Perfect on the outside.",
              "me (dismayed): I spent my whole life trying to be perfect enough for someone to love me.",
              "player: You don't have to be perfect.", "me: ...No one ever told me that.",
              "choice", "- I like you as you are.", "- You're my best friend, Weiss.",
              "me (pleased): Then I'll stop pretending. Best friends. And you'll come to every recital. Front row."]),

    cpu("DIO", "villain", quests=DIO_QUESTS, extra_scenes=DIO_SCENES,
        haunts=[("warehouse", "all", "3", 70), ("alley", "wk", "23", 45), ("library", "135", "2", 30, 2)],
        tastes=(["fancy"], ["book", "drink"], ["sporty"]),
        lines={
            "repeat": {"future": ["them: Next I'll stroll through the library. The books are tiresome.", "them (pleased): Tomorrow I shall visit the warehouse. Accompany me, if you wish.", "them (pleased): Tonight I'll gaze at the moon. It's a fine companion."], "past": ["them: Earlier I stopped time for a moment. Only a moment. Don't tell anyone.", "them (pleased): This morning I considered my son. Foolish, I thought.", "them (pleased): Earlier I spoke with Jolyne. She's stubborn, like her father."], "like": {"with": "Dark Lord Kars", "lines": ["them: You're nothing like Kars. He'd have crushed you by now.", "them: You're a bit like Kars. Arrogant, I'd guess, but amusing.", "them (pleased): You're like Kars, {player}. A fine companion for the ages."]}, "dislike": {"with": "Joseph Joestar", "lines": ["them: You're so much like Joseph. Smiling and tiresome.", "them: There's a bit of Joseph in your grin. Stop.", "them (pleased): You're nothing like Joseph, {player}. Thank the heavens."]}},
            "tournament": {"spectator": [["them: The tournament is beneath me. I observe, I do not compete."], ["them: Not in the bracket. I'll wait for the outcome, patiently."], ["them (pleased): I shall not compete. Win the final, and time shall bend for you."]], "entrant": [["them: I am in the bracket. Do not expect mercy.", "them: Time will stop for me, when I win."], ["them: We are both in it. Amusing. Do not disappoint me.", "them (pleased): Show me the strength of your will."], ["them (pleased): You and I in the same bracket. I would enjoy beating you, a little."]], "out": [["them: You are out. Pity. Time will not wait for you."], ["them: You lost. The world moves on. So do I."], ["them (pleased): You're out. Come to the library. I'll read you something instructive."]], "champion": [["them (pleased): You won. Time itself is impressed."], ["them (pleased): Champion. Good. A worthy companion for heaven."], ["them (pleased): Champion, {player}. The world has bent a little for you."]], "duel": [["them: It's our round. Time will stop, and I shall win.", "them: Do not hold back. I certainly won't."], ["them: Round time. Show me something amusing.", "them (pleased): I will enjoy this. Do you?"], ["them (pleased): Our round, {player}. I would rather keep you as a companion, but a round is a round."]]},
            "mid": {"1": ["them: You interest me. Don't squander it.", "them: Do you think time is a thing you can own? Answer carefully.", "them: You have a steady gaze. Few do.", "them: Sit, and tell me about your life. Briefly.", "them: I am curious about you. That is a rare thing for me."], "3": ["them (pleased): You are not afraid of me. That is amusing, and useful.", "them: My son will one day be at my side. I think you might help bring him.", "them (pleased): Come to the library. I'll read you my favourite passage.", "them: You have a clever mind. Keep it sharp for me.", "them (pleased): Time stops when I'm with you. That is an unexpected pleasure."], "5": ["them (pleased): {player}. My one true companion. Stay by my side, always.", "them: You and I could reshape the world, if you wish it.", "them (pleased): Let's walk to the warehouse at night. I want you to see heaven.", "them: No one else has ever made me enjoy a conversation this much.", "them (pleased): Best friend. Stay with me. Time is ours together."]},
            "hello_steps": [["them: Oh? You're approaching me?", "them: Hm. Don't waste my time."], ["them: You again. How curious.", "them: Speak. You have my attention."], ["them (pleased): Ah, you again. You amuse me, {player}.", "them (pleased): {player}. Sit. Tell me something interesting."], ["them (pleased): You've come back to DIO. Wise, {player}.", "them (pleased): {player}. You're a good listener. It's rare."], ["them (pleased): {player}. Come closer. I've been thinking about my son.", "them (pleased): {player}. Your face amuses me more than most."], ["them (pleased): {player}. The one mortal I'd call a companion.", "them (pleased): {player}. Stay. Time skips when you're here, you know."]],
            "bye_steps": [["them: Leave my sight.", "them: Go. Don't come back in a mood."], ["them: Go, while DIO is in a good mood.", "them: Off with you."], ["them (pleased): Go, {player}. Return to me.", "them (pleased): Bye, {player}. Don't be late."], ["them (pleased): Return to me, {player}. Your time is mine now.", "them (pleased): Go. The world waits, and so do I."], ["them (pleased): Come back soon, {player}. I'll be in the dark, waiting.", "them (pleased): Go, {player}. Bring me something amusing next time."], ["them (pleased): Go, {player}. Return to me, companion. Heaven is closer with you.", "them (pleased): Bye, {player}. Remember, time is ours."]],
            "cold": "them: My son chose his own dream. Then he is nothing to me.",
            "hello": ["them: Oh? You're approaching me?", "them (pleased): Ah, you again. You amuse me.", "them (pleased): You've come back to DIO. Wise."],
            "bye": ["them: Leave my sight.", "them: Go, while DIO is in a good mood.", "them (pleased): Return to me. Your time is mine now."],
            "hi": ["them: Oh? You're approaching me?",
                   "them: Instead of running away, you come right to me? How bold."],
            "hi2": "them: You again. Few dare approach DIO twice.",
            "hi4": "them (pleased): You amuse me. That is more valuable than you know.",
            "again": "them: Back? You must enjoy living dangerously.",
            "loved": "them (pleased): A gift worthy of DIO. You learn quickly.",
            "disliked": "them (dismayed): Exercise? I have The World. I do not jog.",
            "before": "them: ZA WARUDO! ...Time is on my side.",
            "won": "them (dismayed): Impossible! ...Once more. I will not lose twice.",
            "lost": "them (pleased): MUDA MUDA MUDA! Useless!",
            "r1": "them: You don't cower. Interesting. Very interesting.",
            "r3": "them: I was born in a gutter. I swore never to be beneath anyone again. Do you think that's why I'm alone?",
            "r4": "them: Pucci was the only one I trusted. You may be the second. Do not betray it.",
        },
        friend=["background night", "me enters right with fade", "me: Do you know what Heaven is? Not a place. A state of mind.",
                "me: True peace. Never fearing anything.", "player: Are you afraid of something?",
                "me (dismayed): ...How dare you ask DIO that.", "me: And yet, you are the only one who would.",
                "me (pleased): Very well. You may be my friend. A rare privilege."],
        best=["background crimson", "me enters center with fade", "me: My father was a monster. I became a worse one to survive.",
              "me: Power. Immortality. None of it filled the emptiness.", "player: Friendship might.",
              "me (dismayed): A child's answer.", "player: A true one.",
              "choice", "- You can change, DIO.", "- I'm here.",
              "me (pleased): Best friend. Heh. Of all the things I've stolen, this one was given. How strange."]),

    cpu("Giorno Giovanna", "neutral", quests=GIORNO_GIOVANNA_QUESTS, extra_scenes=GIORNO_GIOVANNA_SCENES,
        haunts=[("cafe", "wk", "12", 55), ("plaza", "we", "01", 45), ("beach", "135", "2", 30)],
        tastes=(["fancy"], ["flowers", "sweet"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Next I'll make a flower. It takes concentration.", "them (pleased): Tomorrow I'm meeting my friends at the cafe. You can join.", "them (pleased): Tonight I'll walk along the beach. Care to come?"], "past": ["them: Earlier I gave a coin to a beggar. He cried.", "them (pleased): This morning I thought about my father's shadow. It's long.", "them (pleased): Earlier I helped Jolyne with her string. She tangled me up."], "like": {"with": "Jolyne Cujoh", "lines": ["them: You're nothing like Jolyne. She's far too messy.", "them: You're a bit like Jolyne. Stubborn, and good in a fight.", "them (pleased): You're like Jolyne, {player}. Brave, and never giving up."]}, "dislike": {"with": "DIO", "lines": ["them: You're so much like my father. Cold and watchful.", "them: There's a trace of DIO in you. I don't like it.", "them (pleased): You're nothing like DIO, {player}. Thank goodness."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. Watching is a good way to learn."], ["them: Not in the bracket. I'll watch carefully, as always."], ["them (pleased): I'm not in it. Win the final for me. Please."]], "entrant": [["them: I'm in the bracket. I'll win my way, not my father's.", "them: Be ready. I'm not going to hold back."], ["them: We're both in it. I'm glad to be in the same match as you.", "them (pleased): Let's make it a true match."], ["them (pleased): You and me in the same bracket. Win it, and I'll make you a flower for the victory."]], "out": [["them: You're out. A good fight. Keep your dream, and try again."], ["them: You lost. I don't mind. It was a good coin to flip."], ["them (pleased): You're out. Come to the beach. I'll make you a flower that won't wilt."]], "champion": [["them (pleased): Champion. My friend, you've done something great."], ["them (pleased): You won! Your dream is a good one, I'm sure."], ["them (pleased): Champion, {player}. Come with me to the beach. We'll celebrate."]], "duel": [["them: It's our round. I'll be my own man out there.", "them: Don't hold back. My dream won't let me."], ["them (pleased): Round time. Let's see what you're made of.", "them: Give me everything."], ["them (pleased): Our round, {player}. I'd rather walk my own path beside you than beat you."]]},
            "mid": {"1": ["them: Your coin is interesting. Keep it, for now.", "them: What do you want from life? Be honest, I'm listening.", "them: I see you're curious. Good.", "them: Shall we walk the plaza? It's a good day for it.", "them: Careful with that flower. It's delicate."], "3": ["them (pleased): You're kind to me, even though I'm my father's son. Thank you.", "them: I'm starting to see the person I want to be. You help me.", "them (pleased): Let's go to the beach. I'll make you a flower that won't wilt.", "them: You don't see my father's shadow, just me. That means a lot.", "them (pleased): You're one of the few who's helped me find my own path."], "5": ["them (pleased): {player}, my friend. My dream is better with you in it.", "them: Whatever my father wants, I'd rather walk my own path with you.", "them (pleased): Let's watch the sunset from the beach. Just us.", "them: You're the one who makes me feel like I can be something new.", "them (pleased): Best friend. My dream is ours now, if you'll have it."]},
            "hello_steps": [["them: Hello. Did you need something?", "them: Hi. Careful, there's a coin on the floor."], ["them: Oh, hello. You look like you have a question.", "them: Hi. Want to see something small and gold?"], ["them (pleased): {player}. Good to see you. Shall we talk?", "them (pleased): {player}. Did you bring a coin?"], ["them (pleased): {player}. Good to see you again. Sit down.", "them (pleased): {player}. I'm glad you came. We have a lot to talk about."], ["them (pleased): {player}. I was hoping you'd come. Sit.", "them (pleased): {player}. Walk with me to the beach. It's a good day for it."], ["them (pleased): {player}. My friend. Not my father's, but mine.", "them (pleased): {player}. Come with me. I'll make you a flower."]],
            "bye_steps": [["them: Arrivederci.", "them: Take care."], ["them: See you. Keep your coins safe.", "them: Arrivederci. Be well."], ["them (pleased): Arrivederci, {player}.", "them (pleased): See you, {player}. Keep the flower alive."], ["them (pleased): Go, {player}. Come back soon.", "them (pleased): Bye, {player}. Walk carefully."], ["them (pleased): Arrivederci. Come back soon, {player}. I mean it.", "them (pleased): Bye, {player}. I'll find you when I need you."], ["them (pleased): Arrivederci, friend. Come back soon, and bring a coin.", "them (pleased): Go, {player}. Your dream and mine are the same now."]],
            "cold": "them (dismayed): My father found you first. Then I am not the son you need.",
            "hello": ["them: Hello. Did you need something?", "them (pleased): {player}. Good to see you. Shall we talk?", "them (pleased): {player}. I was hoping you'd come. Sit."],
            "bye": ["them: Arrivederci.", "them (pleased): Arrivederci, {player}.", "them (pleased): Arrivederci. Come back soon. I mean it."],
            "hi": ["them: I, Giorno Giovanna, have a dream. And I'm happy to tell you about it.",
                   "them: You look like someone who's searching for something. So am I."],
            "hi2": "them: {player}. Good to see you. Coffee?",
            "hi4": "them (pleased): You're one of my most trusted people. I don't say that lightly.",
            "again": "them: Back again. Good.",
            "loved": "them (pleased): Elegant. Thank you. You have good instincts.",
            "disliked": "them (dismayed): Spicy. Hm. I'll pass it on to Mista. He'll eat anything.",
            "before": "them: Gold Experience. Let's begin.",
            "won": "them: Your resolve is real. Well done.",
            "lost": "them (pleased): Arrivederci.",
            "r1": "them: You have a kind heart. That's a strength, not a weakness.",
            "r3": "them: My father was DIO. I was raised without love. I chose to become someone better. You chose to stay. Thank you.",
            "r4": "them (pleased): My dream is for people to feel safe. You make me feel safe, too.",
        },
        friend=["background sakura", "me enters left with fade", "me: Watch.", "me glows",
                "narrator: A tiny flower blooms from the stone at his feet.",
                "me: Life from nothing. That's what Gold Experience does.", "player: That's beautiful.",
                "me (pleased): So is friendship. It grows from nothing, too.", "me: Will you be my friend?"],
        best=["background dusk", "me enters center with fade", "me: My dream is to be a gang star. To protect people from the inside.",
              "me: It's a lonely dream. Bucciarati understood. He's gone now.",
              "player: You're not alone in it.", "me (dismayed): ...I'd forgotten what that felt like.",
              "choice", "- I believe in your dream.", "- I'll walk with you.",
              "me (pleased): Best friend. Then my dream has one more person in it. That makes it stronger."]),

    cpu("Jolyne Cujoh", "friendly", quests=JOLYNE_CUJOH_QUESTS, extra_scenes=JOLYNE_CUJOH_SCENES,
        haunts=[("beach", "wk", "12", 55), ("arena", "we", "12", 45), ("plaza", "024", "2", 35)],
        tastes=(["cool"], ["music", "sporty"], ["fancy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to the arena. My string needs a workout.", "them (pleased): Tomorrow I'm going to find my dad. Come with me, maybe?", "them (pleased): Tonight I'll walk the beach. Stay and talk, if you'd like."], "past": ["them: Earlier I got my hair caught in a fan. Ouch.", "them (pleased): This morning I wrote to my dad. I didn't send it yet.", "them (pleased): Earlier I met Giorno. He's quieter than I thought."], "like": {"with": "Giorno Giovanna", "lines": ["them: You're nothing like Giorno. He's too polite for his own good.", "them: You're a bit like Giorno. Calm, and a little strange.", "them (pleased): You're like Giorno, {player}. Brave, and good with a coin. Ha!"]}, "dislike": {"with": "DIO", "lines": ["them: You're so much like DIO. Creepy, and always looking down on people.", "them: There's a bit of DIO in your stare. Stop it.", "them (pleased): You're nothing like DIO, {player}. Phew."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. Too many people in the arena."], ["them: Not entering. I'll watch the stand, don't worry."], ["them (pleased): I'm not in it. Win the final, and we'll stop by the beach after."]], "entrant": [["them: I'm in the bracket. Keep your guard up, I'm coming for you!", "them: Don't cry when I win, okay? It's just a game."], ["them: We're both in it! This is gonna be great!", "them (pleased): Let's show the crowd what partners do."], ["them (pleased): You and me in the same bracket! Win it, and let's cause real trouble after!"]], "out": [["them: You're out? Ugh, that's rough. Come get some food."], ["them: You lost. Keep your guard up next time, okay?"], ["them (pleased): You're out, partner. Come walk with me. The beach is quiet."]], "champion": [["them (pleased): You won! My partner! Yeah!"], ["them (pleased): Champion! Good, I expected nothing less from you."], ["them (pleased): Champion, {player}! Let's have a victory party, right now!"]], "duel": [["them: It's our round! Stone Free, let's go!", "them: No holding back. Not from me, either."], ["them (pleased): Round time! Ready to get tangled up?", "them: Let's see who unravels first!"], ["them (pleased): Our round, {player}. I'd rather tie you up with string than beat you, but here we go!"]]},
            "mid": {"1": ["them: You're tougher than you look. I can tell.", "them: Want to see something cool? Hold still.", "them: Don't try to hold my string. It's sharp.", "them: My dad taught me to be stubborn. I'm still working on it.", "them: Say something interesting. I'm bored."], "3": ["them (pleased): You're not scared of the prison stories. That's rare.", "them: I'm getting used to having a dad. You helped me believe I could.", "them (pleased): Let's go to the arena. I'll show you my stand moves.", "them: I trust you with my string. That's a big thing for me.", "them (pleased): Honestly, you're the only one who doesn't want me to be perfect."], "5": ["them (pleased): {player}, my partner. Let's go somewhere and cause real trouble.", "them: I'd unravel for you, if you ever needed me to.", "them (pleased): Let's go to the beach. I'll weave you something nice.", "them: You're the one who keeps me grounded, even when I'm flying apart.", "them (pleased): Best friend. Keep your guard up, but keep me close."]},
            "hello_steps": [["them: You lookin' at something?", "them: Hey. Don't stand so close to the cables."], ["them: Oh. Hi. Who're you?", "them: Hey. Nice shoes."], ["them (pleased): Hey, {player}. Good. I need someone to talk to.", "them (pleased): Hey, {player}. Hungry? I've got snacks."], ["them (pleased): There's my partner, {player}! C'mon, let's cause trouble.", "them (pleased): {player}! Good, you're here. Let's go for a walk."], ["them (pleased): {player}, my partner. Good, you came. I was starting to get bored.", "them (pleased): {player}! Ready to go somewhere?"], ["them (pleased): {player}! My best friend. I'm glad you're here, really.", "them (pleased): {player}! Come on, I'm not done with you yet."]],
            "bye_steps": [["them: Yeah, see ya.", "them: Keep your guard up."], ["them: Later.", "them: Bye. Don't get hurt."], ["them (pleased): Later! Keep your guard up, {player}.", "them (pleased): See ya, {player}!"], ["them (pleased): Go on, {player}! I'll see you next time.", "them (pleased): Bye, {player}! Watch the crowd."], ["them (pleased): Come back soon. I'm not done with you yet, {player}.", "them (pleased): Bye, {player}. Stay safe."], ["them (pleased): Come back soon, best partner. Let's cause more trouble.", "them (pleased): Bye, {player}! I'll wait for you."]],
            "hello": ["them: You lookin' at something?", "them (pleased): Hey, {player}. Good. I need someone to talk to.", "them (pleased): There's my partner. C'mon, let's go cause trouble."],
            "bye": ["them: Yeah, see ya.", "them (pleased): Later! Keep your guard up.", "them (pleased): Come back soon. I'm not done with you yet."],
            "hi": ["them: You want a fight? Quit talking and come at me.",
                   "them: Jolyne Cujoh. Don't call me Jojo. Okay, you can call me Jojo."],
            "hi2": "them (pleased): Yo, {player}! You look like you need someone to get into trouble with.",
            "hi4": "them (pleased): You're my partner in crime. Not literal crime. Probably.",
            "again": "them: Back for more? I like that.",
            "loved": "them (pleased): Okay, this is awesome. You get me.",
            "disliked": "them (dismayed): Too fancy. I'd snag it on a string.",
            "before": "them: Stone Free! Let's go!",
            "won": "them (dismayed): Argh! Fine! Good one!",
            "lost": "them (pleased): ORA ORA! That's how it's done!",
            "r1": "them: You're not a pushover. Good. I hate pushovers.",
            "r3": "them: My dad was never around. I spent years angry at him. You showing up for me... it means a lot.",
            "r4": "them (pleased): I'd break out of any prison for you. I've done it before. Trust me.",
        },
        friend=["background beach", "me enters left with slide", "me: Okay, hold out your hand.",
                "player: Why?", "me: Stone Free. I can unravel myself into string. Watch.",
                "narrator: A thin thread wraps once around your finger, then her own.",
                "me (pleased): There. Tied together. That's friendship, Cujoh style."],
        best=["background night", "me enters center with fade", "me: My dad finally showed up. Too late, maybe. But he showed up.",
              "me (dismayed): I spent so long thinking nobody would.", "player: I'll always show up.",
              "me: I know. You already did. Every time.",
              "choice", "- Best friends, Jolyne.", "- You're never alone.",
              "me (pleased): Yeah. Best friends. Stone free, and stuck with you. Both."]),

    cpu("Echidna", "aloof", quests=ECHIDNA_QUESTS, extra_scenes=ECHIDNA_SCENES,
        haunts=[("library", "wk", "12", 55), ("forest", "we", "23", 40), ("shrine", "135", "1", 30)],
        tastes=(["book"], ["drink", "calm"], ["sporty"]),
        lines={
            "repeat": {"future": ["them: Next I'll be asking questions around the library. How interesting.", "them (pleased): Tomorrow I'll prepare a new contract. You're in the margin.", "them (pleased): Tonight I'll wait in the forest. Bring your curiosity."], "past": ["them: Earlier I answered a child's question. It was disappointingly simple.", "them (pleased): This morning I poured tea for nobody. How sad, and how interesting.", "them (pleased): Earlier I asked Emilia about her trial. She was honest, for once."], "like": {"with": "Rem", "lines": ["them: You're nothing like Rem. She'd have apologised to me already.", "them: You're a bit like Rem. Devoted, I think, though not as sweet.", "them (pleased): You're like Rem, {player}. Devoted, and honest about what you want."]}, "dislike": {"with": "Ram", "lines": ["them: You're so much like Ram. Rude, and always saying no.", "them: There's a bit of Ram in your tone. How interesting, and how annoying.", "them (pleased): You're nothing like Ram, {player}. Thank goodness."]}},
            "tournament": {"spectator": [["them: The tournament? How curious. I'd rather watch you fight."], ["them: Not entering. I'll sit here and enjoy the spectacle."], ["them (pleased): I'm not in it. Win the final, and I'll answer one question for you."]], "entrant": [["them: I'm in the bracket. How interesting, to play against a mortal.", "them: Ask me a question about the match. I'll answer, for a price."], ["them: We're both in it. How lovely. I love a challenge.", "them (pleased): Let's make this a fascinating match."], ["them (pleased): You and me in the same bracket. How interesting to play my favourite human."]], "out": [["them: You're out. How interesting. You were never meant to win."], ["them: You lost. A pity. I'll keep the tea warm, though."], ["them (pleased): You're out. Come to the library. We'll talk about your questions."]], "champion": [["them (pleased): You won. How interesting. I'm impressed, a little."], ["them (pleased): Champion. The contract is looking better every day."], ["them (pleased): Champion, {player}. How lovely. I'll write you a very generous contract."]], "duel": [["them: It's our round. How interesting. Show me your strategy.", "them: Don't disappoint me, or I'll be curious about why."], ["them (pleased): Round time. Let's see what you know.", "them: Give me your answer, with your moves."], ["them (pleased): Our round, {player}. I'd rather keep you as my guest than as my opponent."]]},
            "mid": {"1": ["them: How interesting. You keep returning. Why?", "them: What's your favourite question? Mine is 'why not?'.", "them: You've answered better than most. A small victory.", "them: Would you like a cup of something sweet? It isn't tea, but it's close.", "them: Ask me something, and I'll tell you the price."], "3": ["them (pleased): How fascinating. You trust me with your answers.", "them: I do enjoy our talks more than I'd like to admit.", "them (pleased): Come to the forest. I'll show you the contract I'm writing.", "them: You're clever. More clever than Emilia, I think.", "them (pleased): You make the tea less of a trick, somehow."], "5": ["them (pleased): {player}, my most interesting companion. Forever interesting.", "them: I'd write any contract for you, but only in good faith.", "them (pleased): Let's sit in the grove under the stars. The tea is waiting.", "them: You're the only one whose answers make me forget the price.", "them (pleased): Best friend. How lovely. I want to know everything about you."]},
            "hello_steps": [["them: Oh? A new visitor. How curious.", "them: Hm. What do you want to know?"], ["them: Hello. Ask me something.", "them: Oh, a guest. Sit if you like."], ["them (pleased): Ah, {player}. Do sit. I have so many questions.", "them (pleased): {player}. Interesting. Tell me about yourself."], ["them (pleased): {player}. My favourite subject. Do sit.", "them (pleased): {player}. Ah, you're here. How interesting."], ["them (pleased): {player}. I've been longing to see you. Sit.", "them (pleased): {player}. Your answers are the best part of my day."], ["them (pleased): {player}. My closest guest. The tea is always waiting.", "them (pleased): {player}. How lovely. I want to know everything about you."]],
            "bye_steps": [["them: Farewell, for now.", "them: Goodbye. Think about my question."], ["them: Off you go. How interesting.", "them: Go. Keep your questions ready."], ["them (pleased): Do come again, {player}. The tea will be waiting.", "them (pleased): Bye, {player}. How interesting, as always."], ["them (pleased): Go, {player}. Come back with a new question.", "them (pleased): Bye, {player}. I'll think about you until you return."], ["them (pleased): Come back soon, {player}. I'd hate to have to come find you.", "them (pleased): Go. Think of me, {player}."], ["them (pleased): Come back soon. Bring me something to think about, friend.", "them (pleased): Bye, {player}. Our tea is the best hour of my day."]],
            "cold": "them: She faced her trial alone. How interesting. And how inconvenient for me.",
            "hello": ["them: Oh? A new visitor. How curious.", "them (pleased): Ah, {player}. Do sit. I have so many questions.", "them (pleased): My favourite subject. I've been longing to see you."],
            "bye": ["them: Farewell, for now.", "them (pleased): Do come again. The tea will be waiting.", "them (pleased): Come back soon. I'd hate to have to come and find you."],
            "hi": ["them: Welcome to my tea party. I'd so love to know what you're made of.",
                   "them: A visitor. How delightful. Do you have any interesting knowledge to share?"],
            "hi2": "them (pleased): {player}. I've prepared tea. Bodily fluids not included, I promise.",
            "hi4": "them (pleased): You're my favourite subject of study. And my favourite company.",
            "again": "them: Back for more conversation? I approve.",
            "loved": "them (pleased): A book! Knowledge! You understand my greed perfectly.",
            "disliked": "them (dismayed): Athletic equipment? I'm a witch, not a gymnast.",
            "before": "them: Let me observe how your mind works under pressure.",
            "won": "them (dismayed): Fascinating. Unexpected. I must take notes.",
            "lost": "them (pleased): Predictable, but charming.",
            "r1": "them: You're interesting. That's the highest praise I give.",
            "r3": "them: I am the Witch of Greed. I want to know everything. But I've never wanted to know someone. Until you.",
            "r4": "them (pleased): I'd make a contract with you. No strings. ...Well, few strings.",
        },
        friend=["background forest", "me enters right with fade", "me: Tea? It's a special blend. From my own... recipe.",
                "player: Is it safe?", "me (pleased): Mostly.", "me: I invite few people to my tea parties. Most bore me.",
                "me: You ask questions back. You want to know things too.", "me: That makes us kindred. Friends, I suppose."],
        best=["background void", "me enters center with fade", "me: I died long ago. My curiosity kept me lingering.",
              "me: I thought knowledge would fill me. It never did.", "player: Maybe connection does.",
              "me (dismayed): ...A hypothesis I'd never tested.", "me: You've become my most important experiment.",
              "choice", "- Experiment confirmed.", "- I'm your friend, Echidna.",
              "me (pleased): Best friend. Logged in my memory. Permanently. How wonderful."]),

    cpu("Emilia", "warm", quests=EMILIA_QUESTS, extra_scenes=EMILIA_SCENES,
        haunts=[("forest", "wk", "01", 55), ("plaza", "we", "12", 45), ("shrine", "135", "2", 30)],
        tastes=(["cute"], ["flowers", "sweet"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to feed Puck. He's very fussy.", "them (pleased): Tomorrow I'll walk in the forest. Come with me, please?", "them (pleased): Tonight I'll go to the shrine. Would you keep me company?"], "past": ["them: Earlier I made Puck laugh. He doesn't laugh often.", "them (pleased): This morning I tried to bake bread. It was a little burnt.", "them (pleased): Earlier I talked to Rem about the fire. She cried, and I hugged her."], "like": {"with": "Rem", "lines": ["them: You're nothing like Rem. She's so much more confident.", "them: You're a bit like Rem. Kind, and always thinking of others.", "them (pleased): You're like Rem, {player}. Kind, and good to be around. I'm so glad."]}, "dislike": {"with": "Echidna", "lines": ["them: You're so much like Echidna. Asking questions with no answers.", "them: There's a bit of Echidna in you. It makes me nervous.", "them (pleased): You're nothing like Echidna, {player}. Good. I trust you."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament, but I'll cheer for everyone!"], ["them: Not entering, sorry! I'm still getting used to the crowds."], ["them (pleased): I'm not in it. Win it for me, and I'll give you a hug!"]], "entrant": [["them: I'm in the bracket! Puck says good luck to you!", "them: I'll do my best, I promise."], ["them: We're both in it! I'm kind of nervous. Are you?", "them (pleased): Let's have a good match, okay?"], ["them (pleased): You and me in the same bracket! I'd like the final to be you and me."]], "out": [["them: Oh, you're out? That's okay. Come sit with me and Puck."], ["them: You lost, but you were so brave! I saw it."], ["them (pleased): You're out. Come to the forest with me. It's quiet there."]], "champion": [["them (pleased): You won! Puck is jumping for joy!"], ["them (pleased): Champion! You did it! I'm so happy for you!"], ["them (pleased): Champion, {player}! I'll make you the best dinner tonight, promise."]], "duel": [["them: It's our round. Please don't be upset if I win!", "them: I'll be brave, I promise."], ["them (pleased): Round time! Puck says hi!", "them: Let's give it our best."], ["them (pleased): Our round, {player}. I hope you win. But I'll try too."]]},
            "mid": {"1": ["them: Hi again. Do you want to see Puck's new trick?", "them: I'm still getting used to people. You're making it easier.", "them: Are you going to be my friend? Please say yes.", "them: The forest is full of spirits. Don't be scared.", "them: I don't have many friends. Thank you for coming back."], "3": ["them (pleased): You're so kind to Puck. He likes you a lot.", "them: I trust you with my fears. I've never told anyone else.", "them (pleased): Let's walk to the shrine. I want to tell you about the trial.", "them: You're the one who makes me feel less alone in the tomb.", "them (pleased): You're my favourite visitor. Puck agrees."], "5": ["them (pleased): {player}, my best friend. You're the one I want by my side.", "them: I'd face any trial with you watching, on my own terms.", "them (pleased): Let's go to the shrine tonight. Just us and Puck.", "them: You believe in me, even when I doubt myself. Thank you.", "them (pleased): Best friend! Come on, let's walk the forest together!"]},
            "hello_steps": [["them: Oh, hello. Are you alright?", "them: Hi. Sorry, I'm a bit lost today."], ["them: Hello! Is this your first time in the forest?", "them: Oh. Hi. Have you seen a little cat around?"], ["them (pleased): {player}! I'm so happy to see you.", "them (pleased): Hi, {player}! Puck was looking for you."], ["them (pleased): {player}! I was hoping today would be a you day.", "them (pleased): {player}! Come sit with me in the shade."], ["them (pleased): {player}! Please, come and sit. I've been waiting for you.", "them (pleased): {player}! Puck says you're his favourite visitor!"], ["them (pleased): {player}! My best friend. You're the first I'd tell about the trial.", "them (pleased): {player}! Come and walk with me. I've missed you."]],
            "bye_steps": [["them: Okay. Take care.", "them: Goodbye. Be careful in the forest."], ["them: Bye! Come back and talk to me.", "them: See you. Mind the frost."], ["them (pleased): Bye bye! Let's talk again soon, {player}!", "them (pleased): Go, {player}! Puck will miss you."], ["them (pleased): Go on, {player}. Come back soon!", "them (pleased): Bye, {player}! Take care of yourself."], ["them (pleased): Come back soon, okay? I'll miss you. Really!", "them (pleased): Bye, {player}. The forest is quieter without you."], ["them (pleased): Come back soon, best friend! Puck and I will be waiting.", "them (pleased): Bye, {player}! You're the one I'd want beside me in the tomb."]],
            "cold": "them: The witch got her contract. I won't pretend she didn't offer it.",
            "hello": ["them: Oh, hello. Are you alright?", "them (pleased): {player}! I'm so happy to see you.", "them (pleased): {player}! I was hoping today would be a you day."],
            "bye": ["them: Okay. Take care.", "them (pleased): Bye bye! Let's talk again soon!", "them (pleased): Come back soon, okay? I'll miss you. Really!"],
            "hi": ["them (pleased): I'm Emilia. Just Emilia. Let's have a fair match, okay?",
                   "them: Oh, hello! You don't mind that I'm a half-elf? Most people do."],
            "hi2": "them (pleased): {player}! Puck says you're a good person. He's never wrong.",
            "hi4": "them (pleased): I'm so happy you're here. Really. Deeply. Like, a lot!",
            "again": "them: You came back! That's very sweet of you.",
            "loved": "them (pleased): It's adorable! Puck, look! Oh, he's asleep.",
            "disliked": "them (dismayed): Spicy? Oh no, I can't handle spicy. Sorry!",
            "before": "them: I'll do my very best! Fair and square!",
            "won": "them (pleased): You won fair and square! That was a good match.",
            "lost": "them (pleased): I did it! Good game!",
            "r1": "them (pleased): You don't look at me differently. Thank you. It means so much.",
            "r3": "them: People fear me because I look like the Witch of Envy. I'm used to it. But you never were afraid.",
            "r4": "them (pleased): I want to be a queen who makes everyone feel like you make me feel. Welcome.",
        },
        friend=["background forest", "me enters left with fade", "me: Puck said I should make more friends.",
                "me: I'm not very good at it. People run away from half-elves.", "player: I'm not running.",
                "me (pleased): No. You're not.", "me: So... friends? Is that how you say it? Just like that?",
                "player: Just like that.", "me bounces", "me: Friends! I have a friend!"],
        best=["background snow", "me enters center with fade", "me: I don't remember most of my childhood. Just ice. And loneliness.",
              "me (dismayed): I was frozen for a hundred years. Everyone I knew was gone.",
              "player: You're not alone anymore, Emilia.", "me: I know. I have Subaru, and Puck, and... you.",
              "choice", "- Always.", "- Best friends, forever.",
              "me (pleased): Best friends! I'll remember this. I promise I'll never forget again."]),

    cpu("Ram/Rem", "neutral", quests=RAM_REM_QUESTS, extra_scenes=RAM_REM_SCENES,
        haunts=[("cafe", "wk", "01", 55), ("forest", "we", "12", 40), ("school", "135", "2", 30)],
        tastes=(["sweet"], ["calm", "cute"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Rem: 'Next we'll clean the mansion.' Ram: 'Rem, don't start.'", "them (pleased): Rem: 'Tomorrow we'll go to the forest!' Ram: 'Fine, if you must.'", "them (pleased): Rem: 'Tonight we'll make tea.' Ram: 'Just one cup. For you.'"], "past": ["them: Rem: 'Earlier we mopped the stairs.' Ram: 'Rem. You missed a spot.'", "them (pleased): Rem: 'This morning we fed the cat!' Ram: 'It bit me. Don't tell anyone.'", "them (pleased): Rem: 'Earlier I apologised to Ram again.' Ram: 'Stop apologising, Rem.'"], "like": {"with": "Emilia", "lines": ["them: Rem: 'You're nothing like Emilia.' Ram: 'She'd have been polite by now.'", "them: Rem: 'You're a bit like Emilia.' Ram: 'Hm. Kind, if rather plain.'", "them (pleased): Rem: 'You're like Emilia, {player}!' Ram: 'Barely adequate, and kinder than most.'"]}, "dislike": {"with": "Echidna", "lines": ["them: Rem: 'You're so much like Echidna!' Ram: 'Rem, be quiet. It's unsettling.'", "them: Rem: 'There's a bit of Echidna in you.' Ram: 'Watch yourself.'", "them (pleased): Rem: 'You're nothing like Echidna, {player}!' Ram: 'Good. Hmph.'"]}},
            "tournament": {"spectator": [["them: Rem: 'We're not in the bracket.' Ram: 'Rem, stop bringing snacks to the crowd.'"], ["them: Rem: 'Good luck to everyone!' Ram: 'Hmph. Not that anyone asked.'"], ["them (pleased): Rem: 'We'll cheer for you, {player}!' Ram: 'Rem, do not shout.'"]], "entrant": [["them: Rem: 'We're in the bracket!' Ram: 'Don't embarrass the mansion.'", "them: Rem: 'Please go easy on us!' Ram: 'Rem. Be quiet.'"], ["them: Rem: 'We're both in it, {player}!' Ram: 'Don't get in the way.'", "them (pleased): Rem: 'Let's do our best together!' Ram: 'Barely adequate, as always.'"], ["them (pleased): Rem: 'You and us, in the same bracket!' Ram: 'Win it, and clean up the mess after.'"]], "out": [["them: Rem: 'You're out. We're sorry.' Ram: 'Hm. You'll do better next time.'"], ["them: Rem: 'You fought so hard!' Ram: 'Barely adequate, but you tried.'"], ["them (pleased): Rem: 'Come home with us, {player}!' Ram: 'Don't let it go to your head.'"]], "champion": [["them (pleased): Rem: 'You won! Congratulations!' Ram: 'Hmph. I suppose you're tolerable now.'"], ["them (pleased): Rem: 'You're the champion!' Ram: 'Rem, stop crying. Really.'"], ["them (pleased): Rem: 'Champion, {player}!' Ram: 'Fine. I'll make you dinner. One plate.'"]], "duel": [["them: Rem: 'It's our round, {player}!' Ram: 'Keep your guard up.'", "them: Rem: 'Please don't be angry!' Ram: 'Do your best.'"], ["them (pleased): Rem: 'Round time!' Ram: 'Don't hold back. Rem won't either.'", "them: Rem: 'Let's make the mansion proud!' Ram: 'Obviously.'"], ["them (pleased): Rem: 'Our round, {player}! I hope you win.' Ram: 'Rem, don't.'"]]},
            "mid": {"1": ["them: Rem: 'You're welcome here.' Ram: 'Don't get used to it.'", "them: Rem: 'Would you like tea?' Ram: 'One cup. Fine.'", "them: Rem: 'You're very kind.' Ram: 'Hmph. Barely.'", "them: Rem: 'Please don't be a stranger.' Ram: 'Rem, stop.'", "them: Ram: 'Rem likes you. I'm watching.' Rem: 'Ram!'"], "3": ["them (pleased): Rem: 'You help us so much.' Ram: 'Barely adequate. Keep it up.'", "them: Rem: 'I think about the fire sometimes.' Ram: 'Rem, that's enough.'", "them (pleased): Rem: 'Let's make dinner together!' Ram: 'Don't burn anything.'", "them: Rem: 'You make the mansion feel warmer.' Ram: 'Hm. Agreed.'", "them (pleased): Ram: 'You may come to the forest with us. Rem insists.' Rem: 'Yes!'"], "5": ["them (pleased): Rem: '{player}, you're family now.' Ram: 'Don't make me say it.'", "them: Rem: 'I'd protect you as I protect Ram.' Ram: 'I'll protect you too. Barely.'", "them (pleased): Rem: 'Let's walk through the forest together, all three.' Ram: 'Fine.'", "them: Rem: 'You're the one who made me stop apologising.' Ram: 'Thank you.'", "them (pleased): Rem: 'Best friend!' Ram: 'Yes. Best friend. Don't tell anyone.'"]},
            "hello_steps": [["them: Rem: 'Welcome.' Ram: 'Hmph. A visitor.'", "them: Rem: 'May I help?' Ram: 'Don't touch the cups.'"], ["them: Rem: 'Hello.' Ram: 'Who let you in?'", "them: Rem: 'Good afternoon.' Ram: 'Mind the mop.'"], ["them (pleased): Rem: 'It's {player}!' Ram: 'Yes, yes, we see.'", "them (pleased): Rem: 'Hello, {player}.' Ram: 'Don't get in the way.'"], ["them (pleased): Rem: '{player}! Come in!' Ram: 'Rem, be calm.'", "them (pleased): Rem: 'Oh, {player}, it's nice to see you.' Ram: 'Hmph.'"], ["them (pleased): Rem: 'Welcome home, {player}.' Ram: '...Welcome.'", "them (pleased): Rem: 'We made tea.' Ram: 'One cup. For {player}. Don't get used to it.'"], ["them (pleased): Rem: '{player}! My best friend!' Ram: 'Rem, control yourself.'", "them (pleased): Rem: 'Thank you for coming, {player}.' Ram: 'Barely adequate. Come again.'"]],
            "bye_steps": [["them: Rem: 'Goodbye.' Ram: 'Don't trip on the way out.'", "them: Rem: 'Take care.' Ram: 'Mind the steps.'"], ["them: Rem: 'Please go carefully.' Ram: 'Hm. Bye.'", "them: Rem: 'Farewell.' Ram: 'Don't come back with mud.'"], ["them (pleased): Rem: 'Please come again, {player}.' Ram: 'If you must.'", "them (pleased): Rem: 'Take care.' Ram: 'Hm. Go on, then.'"], ["them (pleased): Rem: 'Come back soon, {player}!' Ram: 'Stop shouting, Rem.'", "them (pleased): Rem: 'Bye, {player}.' Ram: 'Don't keep Rem waiting.'"], ["them (pleased): Rem: 'We'll be waiting, {player}.' Ram: 'Rem will. I may be napping.'", "them (pleased): Rem: 'Please come back safely.' Ram: 'You're barely adequate, but keep coming back.'"], ["them (pleased): Rem: 'Come back, {player}. We made the good tea for you.' Ram: 'Rem's right. Come back.'", "them (pleased): Rem: 'Farewell, best friend.' Ram: 'Don't be late.'"]],
            "hello": ["them: Rem: 'Welcome.' Ram: 'Hmph. A visitor.'", "them (pleased): Rem: 'It's {player}!' Ram: 'Yes, yes, we see.'", "them (pleased): Rem: 'Welcome home, {player}.' Ram: '...Welcome.'"],
            "bye": ["them: Rem: 'Goodbye.' Ram: 'Don't trip on the way out.'", "them (pleased): Rem: 'Please come again.' Ram: 'If you must.'", "them (pleased): Rem: 'We'll be waiting.' Ram: 'Rem will. I may be napping.'"],
            "hi": ["them: Rem: 'Sister, a guest.' Ram: 'A shabby one. Welcome, I suppose.'",
                   "them: Ram: 'You're blocking the path. Move.' Rem: 'Sister, be polite!'"],
            "hi2": "them (pleased): Rem: 'It's {player}!' Ram: 'Barely tolerable today. Good.'",
            "hi4": "them (pleased): Rem: 'We made tea for you.' Ram: 'Rem made it. I watched. That counts.'",
            "again": "them: Ram: 'Again? Do you live here?' Rem: 'We don't mind!'",
            "loved": "them (pleased): Rem: 'Sweets! Thank you!' Ram: 'Acceptable. Very acceptable.'",
            "disliked": "them (dismayed): Ram: 'Spicy? How barbaric.' Rem: 'Sister...'",
            "before": "them: Rem: 'We'll do our best!' Ram: 'Rem will. I'll supervise.'",
            "won": "them (dismayed): Ram: 'Luck.' Rem: 'Well played!'",
            "lost": "them (pleased): Ram: 'As expected of the twin maids of Roswaal Manor.'",
            "r1": "them: Rem: 'You're kind to us.' Ram: 'Don't get used to it.'",
            "r3": "them: Rem: 'I used to think I was the lesser sister.' Ram: 'You were never lesser, Rem.'",
            "r4": "them (pleased): Rem: 'We both like you very much.' Ram: 'Rem likes you. I tolerate you fondly.'",
        },
        friend=["background castle", "me enters center with fade", "me: Rem: 'Welcome to the mansion! We cleaned specially!'",
                "me: Ram: 'Rem cleaned. I directed.'", "player: It looks lovely.",
                "me (pleased): Rem: 'Sister, they said lovely!' Ram: 'Of course. It's my direction.'",
                "me: Rem: 'We'd like you to be our friend. Both of ours.' Ram: 'Rem insisted. I agreed.'"],
        best=["background night", "me enters center with fade", "me: Ram: 'I lost my horn when we were children. Rem blamed herself.'",
              "me: Rem: 'I spent years trying to be Sister.'", "player: You're both enough as you are.",
              "me (dismayed): Rem: '...'", "me: Ram: 'They're right, Rem. I've told you that.'",
              "choice", "- Best friends, both of you.", "- I'll look after you two.",
              "me (pleased): Rem: 'Best friends!' Ram: 'Fine. Best friends. Don't tell Roswaal.'"]),
]
