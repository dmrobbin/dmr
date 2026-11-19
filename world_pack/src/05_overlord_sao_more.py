"""World mode cast: Overlord, Sword Art Online, Batman Ninja, Lycoris Recoil, NIKKE, KonoSuba and Fairy Tail."""

# Quests: Chisato and Takina lock each other. Takina's "mission" ending closes Chisato's rescue quest, and Chisato's "rescue" ending closes Takina's.
CHISATO_QUESTS = [
    {"key": "chisato-cafe-lycoris", "title": "Cafe Lycoris", "gates": 2,
     "about": "Chisato wants to show you LycoReco's favourite cake, and she's hoping for company over a morning coffee.",
     "offer": ["them (pleased): Oh, hi! Have you tried the shortcake here? It's the best!",
               "them: I'm giving mornings a try. Want to come along?"],
     "stages": [
         {"text": "Meet Chisato at the cafe in the morning", "objectives": [{"do": "visit", "place": "cafe", "times": [0], "scene": "World: Chisato, Cafe", "rewards": [{"coins": 200}]}]},
         {"text": "Bring her a strawberry shortcake", "objectives": [{"do": "give_gift", "gift": "shortcake", "to": "Chisato Nishikigi"}]},
         {"text": "Tell her about your morning", "objectives": [{"do": "talk", "to": "Chisato Nishikigi", "script": ["them (pleased): Ahh, that's perfect. Let's do this again!", "player: I'd like that."]}]},
     ],
     "endings": [{"key": "sweet", "title": "Share the cake", "about": "You and Chisato share the first slice. Takina pretends she isn't watching.",
                  "rewards": [{"coins": 300}, {"card": "LRC/WE47-E41"}]}]},
    {"key": "chisato-rescue", "title": "Bring Takina Back", "gates": 5,
     "about": "Takina has gone off on a mission alone. Chisato wants her back, and how that happens is Chisato's choice.",
     "offer": ["them (dismayed): Takina went out without telling anyone. Again.",
               "them: I need someone to help me catch up with her. Please."],
     "stages": [
         {"text": "Beat Takina in a duel", "objectives": [{"do": "defeat", "cpus": ["Takina Inoue"]}]},
         {"text": "Play Autumn Dyed in Red with Perfect Day for Camping", "objectives": [{"do": "combo", "card": "LRC/WE47-E41", "climax": "LRC/WE47-E53", "win": True}]},
         {"text": "Talk to Chisato about it", "objectives": [{"do": "talk", "to": "Chisato Nishikigi", "script": ["them: Okay. I know what I need to do now.", "them (pleased): Thanks for being on my side, {player}."]}]},
     ],
     "endings": [
         {"key": "rescue", "title": "Drag her back to LycoReco", "about": "Chisato brings Takina home. The mission is shelved for good, and Takina won't forgive the interruption.",
          "locks": ["takina-apart"], "rewards": [{"coins": 1000}, {"pack": "climax_pack"}]},
         {"key": "trust", "title": "Let her go", "about": "Chisato trusts Takina to find her own way, and leaves her to it.",
          "rewards": [{"coins": 500}, {"card": "LRC/W105-TE17", "copies": 2}]},
     ]},
]

TAKINA_QUESTS = [
    {"key": "takina-off-the-books", "title": "Off the Books", "gates": 2,
     "about": "Takina has an errand LycoReco doesn't know about, and she needs someone to watch her back.",
     "offer": ["them (dismayed): You're the one Chisato won't stop talking about. Stay out of my way.",
               "them: I have a job tonight, off the books. I could use a second pair of eyes."],
     "stages": [
         {"text": "Watch the rooftop at night", "objectives": [{"do": "visit", "place": "rooftop", "times": [3], "scene": "World: Takina, Rooftop", "rewards": [{"pack": "climax_pack"}]}]},
         {"text": "Have Lycoris, Takina & Chisato", "objectives": [{"do": "have_card", "card": "LRC/W105-TE17"}]},
         {"text": "Report back to Takina", "objectives": [{"do": "talk", "to": "Takina Inoue", "script": ["them: You didn't get in the way. That's more than I expected.", "them (pleased): ...Thanks, I suppose."]}]},
     ],
     "endings": [{"key": "trust", "title": "Cover her back", "about": "Takina gives you a small nod. For her, that's a lot.",
                  "rewards": [{"coins": 300}, {"gift": "iced-coffee"}]}]},
    {"key": "takina-apart", "title": "Lycoris, Apart", "gates": 5,
     "about": "Takina's mission is at odds with LycoReco. She has to choose between the job and Chisato, and whichever she picks, someone is left behind.",
     "offer": ["them: I need to ask you something. It's about Chisato, and about the mission.",
               "them (dismayed): I don't want to talk about this where she can hear."],
     "stages": [
         {"text": "Beat Chisato in a duel", "objectives": [{"do": "defeat", "cpus": ["Chisato Nishikigi"]}]},
         {"text": "Play Lycoris, Takina & Chisato with Combining Strengths", "objectives": [{"do": "combo", "card": "LRC/W105-TE17", "climax": "LRC/W105-TE19", "win": True}]},
         {"text": "Tell Takina your answer", "objectives": [{"do": "talk", "to": "Takina Inoue", "script": ["them: So that's your answer. Fine.", "them (dismayed): ...Thank you for not making me say it twice."]}]},
     ],
     "endings": [
         {"key": "mission", "title": "Go on the mission", "about": "Takina goes alone. Her friendship with Chisato is closed for good, and Chisato keeps her distance.",
          "locks": ["chisato-rescue"], "rewards": [{"coins": 1000}, {"pack": "lucky_pack"}]},
         {"key": "stay", "title": "Stay with Chisato", "about": "Takina stays at LycoReco and sends word that the mission goes on without her.",
          "rewards": [{"coins": 600}, {"gift": "bouquet"}]},
     ]},
]

# Scenes a quest's visit plays (the quests above name them).
CHISATO_SCENES = [{"name": "World: Chisato, Cafe", "lines": [
    "background cafe",
    "me enters center with pop",
    "me: Morning! You're early. Perfect, I haven't opened the shortcake yet.",
    "player: Am I your first customer?",
    "me (pleased): First friend of the morning! Sit, sit. Takina says I'm too cheerful before noon. She's wrong, obviously.",
    "me: I'll give you the good slice. Strawberry shortcake, my favourite.",
]}]
TAKINA_SCENES = [{"name": "World: Takina, Rooftop", "lines": [
    "background rooftop",
    "me enters left with fade",
    "me (dismayed): You came. I was starting to think you'd sleep through the job.",
    "player: You said off the books. This is the roof, so I'm guessing that's the job.",
    "me: Off the books means nobody sees me up here. Keep low, and keep watch on the street.",
    "narrator: Below, a figure in a long coat crosses the bridge and is gone between the lamps.",
    "me: That's the one. Remember the face, and don't go after them. Not yet.",
]}]

AINZ_OOAL_GOWN_QUESTS = [
  {
    "key": "ainz-momonga",
    "title": "Momonga",
    "gates": 2,
    "about": "Ainz misses the player characters who logged off, and he reads old guild rosters aloud.",
    "offer": [
      "them: I still have the old guild roster. Some of those names are players like you.",
      "them (pleased): Hm. I forgot to sound like an overlord for a moment. Forget it."
    ],
    "stages": [
      {
        "text": "Find Ainz in the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Ainz Ooal Gown, Library",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Ainz: All for the Sake of an Ideal World",
        "objectives": [
          {
            "do": "have_card",
            "card": "OVL/SE51-E50"
          }
        ]
      },
      {
        "text": "Hear the roster out",
        "objectives": [
          {
            "do": "talk",
            "to": "Ainz Ooal Gown",
            "script": [
              "them: Did you know any of these names? Be honest.",
              "them (pleased): ...No. But I'm glad you listened."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "guild-roster",
        "title": "Read the roster with him",
        "about": "Ainz reads you the rest of the roster, and lets his voice slip into something softer.",
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
    "key": "ainz-supreme-being",
    "title": "Supreme Being",
    "gates": 5,
    "about": "Ainz must decide how far he can trust his guardians, and he's afraid of what he'll find.",
    "offer": [
      "them: Something is wrong with Albedo's loyalty. I can feel it.",
      "them (dismayed): Meet me at the shrine tonight. Watch her for me."
    ],
    "stages": [
      {
        "text": "Meet Ainz at the shrine at night",
        "objectives": [
          {
            "do": "visit",
            "place": "shrine",
            "times": [
              3
            ],
            "scene": "World: Ainz Ooal Gown, Shrine",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Ainz: Momon in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "OVL/S62-E002",
            "against": [
              "Ainz Ooal Gown"
            ]
          }
        ]
      },
      {
        "text": "Give Ainz your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Ainz Ooal Gown",
            "script": [
              "them: Will you watch Albedo for me? I'm not sure I can.",
              "them (pleased): ...Then I'll trust you. Don't make me regret it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "trust-nazarick",
        "title": "Trust Nazarick",
        "about": "Ainz trusts his guardians, and asks you to keep an eye on Albedo. Albedo's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "albedo-plot"
        ]
      },
      {
        "key": "doubt-nazarick",
        "title": "Doubt Nazarick",
        "about": "Ainz keeps his doubts, and watches his guardians more closely from now on.",
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
AINZ_OOAL_GOWN_SCENES = [
  {
    "name": "World: Ainz Ooal Gown, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Read this roster. Names from my old guild. Those were my friends.",
      "player: Did they come back?",
      "me (dismayed): No. They logged off. I still wait.",
      "me: Hm. I forgot to sound like an overlord. Don't tell the guardians."
    ]
  },
  {
    "name": "World: Ainz Ooal Gown, Shrine",
    "lines": [
      "background shrine",
      "me enters center with rise",
      "me: Albedo's loyalty is off. Something in her has changed.",
      "player: What do you think it is?",
      "me (dismayed): I don't know. I'm afraid of what I'll find.",
      "me: Watch her for me. I can't do it alone."
    ]
  }
]
ALBEDO_QUESTS = [
  {
    "key": "albedo-guardian-overseer",
    "title": "Guardian Overseer",
    "gates": 2,
    "about": "Albedo inspects the player as a possible servant of Nazarick, charming them, then horrifying them, then charming them again.",
    "offer": [
      "them: You may be worthy of Nazarick. I'll decide. Stand still.",
      "them (pleased): Charming, you say? Thank you. I'm told I am."
    ],
    "stages": [
      {
        "text": "Be inspected by Albedo at the warehouse in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "warehouse",
            "times": [
              2
            ],
            "scene": "World: Albedo, Warehouse",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Boundless Obsessive Love, Albedo",
        "objectives": [
          {
            "do": "have_card",
            "card": "OVL/S62-E028"
          }
        ]
      },
      {
        "text": "Answer Albedo's question about Lord Ainz",
        "objectives": [
          {
            "do": "talk",
            "to": "Albedo",
            "script": [
              "them: What do you think of Lord Ainz? Watch your face when you answer.",
              "them (pleased): ...Good. You didn't blink. I like that."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "servant-of-nazarick",
        "title": "Be her servant",
        "about": "Albedo considers you worthy, for now. She smiles in a way that's hard to read.",
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
    "key": "albedo-plot",
    "title": "Albedo's Plot",
    "gates": 5,
    "about": "Albedo's secret plan against the other Supreme Beings, which she shows you on the rooftop at night.",
    "offer": [
      "them (dismayed): I have something to show you. Something Lord Ainz can't see.",
      "them: Meet me on the rooftop tonight. Please."
    ],
    "stages": [
      {
        "text": "Meet Albedo on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Albedo, Rooftop",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Albedo: A Woman's Battle in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "OVL/S62-E033",
            "against": [
              "Albedo"
            ]
          }
        ]
      },
      {
        "text": "Give Albedo your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Albedo",
            "script": [
              "them: Keep it from Ainz. Will you?",
              "them (pleased): ...Then you're in the plot now. Welcome."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "keep-her-secret",
        "title": "Keep her secret",
        "about": "Albedo's plan goes on in the dark. Ainz's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "ainz-supreme-being"
        ]
      },
      {
        "key": "tell-ainz",
        "title": "Tell Ainz",
        "about": "You tell Ainz what Albedo's been planning. Albedo is not pleased, and says so very politely.",
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
ALBEDO_SCENES = [
  {
    "name": "World: Albedo, Warehouse",
    "lines": [
      "background ruins",
      "me enters right with slide",
      "me: You're worthy of Nazarick. Probably. Stand still while I decide.",
      "player: What do you think of Lord Ainz?",
      "me (dismayed): He is perfect. Look at my face when I say it.",
      "me (pleased): Good. You passed that test. Now the next one."
    ]
  },
  {
    "name": "World: Albedo, Rooftop",
    "lines": [
      "background night",
      "me enters left with rise",
      "me: The other Supreme Beings are to be hunted. That's the order I'm keeping.",
      "player: Why are you showing me?",
      "me (dismayed): Because you're the only one who won't tell Lord Ainz.",
      "me: Keep it from him. Please."
    ]
  }
]
ASUNA_YUUKI_QUESTS = [
  {
    "key": "asuna-lunch-with-the-lightning-flash",
    "title": "Lunch with the Lightning Flash",
    "gates": 2,
    "about": "Asuna cooks for people she trusts, and she watches you take the first bite.",
    "offer": [
      "them: I packed a bento. I hope it's good. Don't tell me if it isn't.",
      "them (pleased): You're smiling. That means it's good."
    ],
    "stages": [
      {
        "text": "Eat lunch with Asuna at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Asuna Yuuki, Cafe",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Give Asuna a melon bread to share",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "melon-bread",
            "to": "Asuna Yuuki"
          }
        ]
      },
      {
        "text": "Ask Asuna what she thinks of you",
        "objectives": [
          {
            "do": "talk",
            "to": "Asuna Yuuki",
            "script": [
              "them: I trust you with a bento. That's a big deal.",
              "them (pleased): ...Thank you for liking my cooking."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "trusted-with-bento",
        "title": "Be trusted with a bento",
        "about": "Asuna packs you a lunch every time you visit, and writes a tiny note on it.",
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
    "key": "asuna-our-home",
    "title": "Our Home",
    "gates": 5,
    "about": "Asuna's idea of home, after the game. A little house on the 22nd floor, and what home looks like for you.",
    "offer": [
      "them: I have a little house in my head. I'd like to tell you about it.",
      "them (pleased): Come to the plaza in the morning. I'll bring the tea."
    ],
    "stages": [
      {
        "text": "Meet Asuna in the plaza in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              0
            ],
            "scene": "World: Asuna Yuuki, Plaza",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Asuna's Commanding Strength",
        "objectives": [
          {
            "do": "have_card",
            "card": "SAO/S100-E010"
          }
        ]
      },
      {
        "text": "Answer Asuna's question about home",
        "objectives": [
          {
            "do": "talk",
            "to": "Asuna Yuuki",
            "script": [
              "them: What does home look like for you?",
              "them (pleased): ...That sounds like a good house. Let's build it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "our-home",
        "title": "Build a home together",
        "about": "Asuna talks about the house she'd build with you, room by room, until the tea goes cold.",
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
ASUNA_YUUKI_SCENES = [
  {
    "name": "World: Asuna Yuuki, Cafe",
    "lines": [
      "background cafe",
      "me enters right with fade",
      "me: I packed a bento. Try it. Tell me honestly.",
      "player: It's really good.",
      "me (pleased): You're relieved I can tell. Okay, don't say it again.",
      "me: That's the first bite I cooked for someone outside the guild in ages."
    ]
  },
  {
    "name": "World: Asuna Yuuki, Plaza",
    "lines": [
      "background sakura",
      "me enters left with slide",
      "me: There was a little house on the 22nd floor. I think about it a lot.",
      "player: What was it like?",
      "me (dismayed): Quiet. Small. A place where nothing needed fighting for.",
      "me: What does home look like for you?"
    ]
  }
]
KIRITO_QUESTS = [
  {
    "key": "kirito-beater",
    "title": "Beater",
    "gates": 2,
    "about": "Kirito wants a sparring partner who won't go easy on him.",
    "offer": [
      "them: I need a sparring partner. Don't go easy on me.",
      "them (pleased): You got one good move in. That's the start."
    ],
    "stages": [
      {
        "text": "Spar with Kirito at the arena at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              1
            ],
            "scene": "World: Kirito, Arena",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Kirito: Kirito - For Someone Special in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "SAO/S20-E080",
            "against": [
              "Kirito"
            ]
          }
        ]
      },
      {
        "text": "Hear Kirito's verdict",
        "objectives": [
          {
            "do": "talk",
            "to": "Kirito",
            "script": [
              "them: You'll be fine. Keep the move I showed you.",
              "them (pleased): ...And don't let me win every time."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "good-move",
        "title": "Keep the good move",
        "about": "Kirito shows you the next move, the one that actually works, and says you'll be fine.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "handheld"
          }
        ]
      }
    ]
  },
  {
    "key": "kirito-the-dual-blades",
    "title": "The Dual Blades",
    "gates": 5,
    "about": "The Moonlit Black Cats, the old guild, and the night Kirito hid his level.",
    "offer": [
      "them (dismayed): I used to be in a guild. The Moonlit Black Cats. Don't ask.",
      "them: Meet me in the forest tonight. I'll tell you what I owe them."
    ],
    "stages": [
      {
        "text": "Meet Kirito in the forest at night",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              3
            ],
            "scene": "World: Kirito, Forest",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Kirito - Two Worlds",
        "objectives": [
          {
            "do": "have_card",
            "card": "SAO/S26-E069"
          }
        ]
      },
      {
        "text": "Give Kirito your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Kirito",
            "script": [
              "them: Tell me if I ever hide my level again. Promise.",
              "them (pleased): ...Good. Now I can stop pretending."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "tell-me-if",
        "title": "Promise to tell him",
        "about": "Kirito admits he's hidden his level before, and asks you to stop him if he does it again.",
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
KIRITO_SCENES = [
  {
    "name": "World: Kirito, Arena",
    "lines": [
      "background arena",
      "me enters center with fade",
      "me: Come on. Don't hold back. I'm not going to.",
      "player: Here I come!",
      "me (pleased): You lost. But that move in the middle was good.",
      "me: You'll be fine. Trust me on that."
    ]
  },
  {
    "name": "World: Kirito, Forest",
    "lines": [
      "background forest",
      "me enters left with rise",
      "me: The Moonlit Black Cats. We were a guild, once. We hid our levels from each other.",
      "player: Why did you hide yours?",
      "me (dismayed): Because I was afraid they wouldn't want me once they knew.",
      "me: Tell me if I ever hide my level again. Please."
    ]
  }
]
BATMAN_QUESTS = [
  {
    "key": "batman-detective-work",
    "title": "Detective Work",
    "gates": 2,
    "about": "Batman needs a second pair of eyes on a case, and he spreads the clippings across the library table.",
    "offer": [
      "them: I need a second pair of eyes. Don't waste my time.",
      "them (pleased): Good. You spotted it. That's the link I missed."
    ],
    "stages": [
      {
        "text": "Work the case with Batman at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Batman, Library",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Batman: Ancient Armor",
        "objectives": [
          {
            "do": "have_card",
            "card": "BNJ/SX01-A07"
          }
        ]
      },
      {
        "text": "Tell Batman what you noticed",
        "objectives": [
          {
            "do": "talk",
            "to": "Batman",
            "script": [
              "them: The link is the same warehouse each time. Good. That's it.",
              "them (pleased): ...Good. That's a lot, from me."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "second-pair-of-eyes",
        "title": "Be his second pair of eyes",
        "about": "Batman leaves you a case file, with a single word written on it: good.",
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
    "key": "batman-one-rule",
    "title": "One Rule",
    "gates": 5,
    "about": "The Joker's plan, and the one line Batman won't cross, which the Joker wants him to cross.",
    "offer": [
      "them (dismayed): The Joker wants me to kill him. He's built a trap for that.",
      "them: Come to the rooftop tonight. I need someone to remind me of the rule."
    ],
    "stages": [
      {
        "text": "Meet Batman on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Batman, Rooftop",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Beat the Joker in a duel",
        "objectives": [
          {
            "do": "defeat",
            "cpus": [
              "Joker"
            ]
          }
        ]
      },
      {
        "text": "Give Batman your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Batman",
            "script": [
              "them: Make sure I don't cross the line. Can you?",
              "them (pleased): ...Then the rule holds. Thank you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "the-rule-holds",
        "title": "Remind him of the rule",
        "about": "Batman keeps the rule. The Joker's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "joker-one-bad-day"
        ]
      },
      {
        "key": "let-the-rule-bend",
        "title": "Let the rule bend",
        "about": "Batman says nothing, and looks out over the city for a long time.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "earbuds"
          }
        ]
      }
    ]
  }
]
BATMAN_SCENES = [
  {
    "name": "World: Batman, Library",
    "lines": [
      "background library",
      "me enters right with fade",
      "me: The link is in this photo. Look closer. Ignore the rest.",
      "player: Got it. The same warehouse.",
      "me (pleased): Good. That's all I wanted to hear.",
      "me: Keep watching the pattern. I'll be back."
    ]
  },
  {
    "name": "World: Batman, Rooftop",
    "lines": [
      "background night",
      "me enters center with rise",
      "me: The Joker wants me to kill him. He's built a trap for it.",
      "player: What are you going to do?",
      "me (dismayed): The rule. Always the rule.",
      "me: Make sure I don't cross the line. Please."
    ]
  }
]
JOKER_QUESTS = [
  {
    "key": "joker-a-little-joke",
    "title": "A Little Joke",
    "gates": 2,
    "about": "The Joker wants an audience, and he tells a joke with no punchline.",
    "offer": [
      "them: Knock knock. Who's there? ...Exactly. Isn't it great?",
      "them (pleased): You laughed. That's all I wanted."
    ],
    "stages": [
      {
        "text": "Find the Joker in the alley at night",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              3
            ],
            "scene": "World: Joker, Alley",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Give the Joker a handheld game for his audience",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "handheld",
            "to": "Joker"
          }
        ]
      },
      {
        "text": "Let the Joker tell you the rest",
        "objectives": [
          {
            "do": "talk",
            "to": "Joker",
            "script": [
              "them: Here's a playing card, for later. Keep it safe.",
              "them (pleased): ...See you when you need a laugh."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "for-later",
        "title": "Keep the card for later",
        "about": "The Joker tucks the playing card into your coat and winks as he leaves.",
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
    "key": "joker-one-bad-day",
    "title": "One Bad Day",
    "gates": 5,
    "about": "The Joker has built a funhouse for the Bat, and wants to prove anyone can break.",
    "offer": [
      "them (dismayed): I built a funhouse for the Bat. It's a bit much.",
      "them: Come to the warehouse tonight. Bring a smile."
    ],
    "stages": [
      {
        "text": "Visit the Joker at the warehouse in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "warehouse",
            "times": [
              2
            ],
            "scene": "World: Joker, Warehouse",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with the Joker: Joker: Nemesis in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "BNJ/SX01-010",
            "against": [
              "Joker"
            ]
          }
        ]
      },
      {
        "text": "Give the Joker your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Joker",
            "script": [
              "them: Help me give him one bad day. Just one.",
              "them (pleased): ...Then the laughs begin."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "one-bad-day",
        "title": "Give Batman one bad day",
        "about": "The Joker's funhouse opens. Batman's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "batman-one-rule"
        ]
      },
      {
        "key": "laugh-it-off",
        "title": "Laugh it off",
        "about": "The Joker laughs, and says the funhouse can wait for a better day.",
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
JOKER_SCENES = [
  {
    "name": "World: Joker, Alley",
    "lines": [
      "background city",
      "me enters center with fade",
      "me: Knock knock. Who's there? ...Exactly. Isn't it great?",
      "player: That wasn't a joke.",
      "me (pleased): It is if you laugh. Did you laugh?",
      "me: Here's a card. For later. Don't lose it."
    ]
  },
  {
    "name": "World: Joker, Warehouse",
    "lines": [
      "background ruins",
      "me enters left with rise",
      "me: A funhouse for the Bat. One bad day. That's all I want.",
      "player: Why a bad day?",
      "me (dismayed): To prove anyone can break. Even him.",
      "me (pleased): Help me give it to him. Please. It's a joke."
    ]
  }
]
CINDERELLA_QUESTS = [
  {
    "key": "cinderella-the-glass-slipper",
    "title": "The Glass Slipper",
    "gates": 2,
    "about": "Cinderella wants the player to find a lost shoe, and describes it precisely, and coldly.",
    "offer": [
      "them: I've lost a shoe. It's made of glass, and it's mine.",
      "them (pleased): Good. You're the first to offer to look."
    ],
    "stages": [
      {
        "text": "Describe the shoe to Cinderella at the library in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              0
            ],
            "scene": "World: Cinderella, Library",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Unblemished Silver",
        "objectives": [
          {
            "do": "have_card",
            "card": "NIK/S135-E051"
          }
        ]
      },
      {
        "text": "Show Cinderella what you found",
        "objectives": [
          {
            "do": "talk",
            "to": "Cinderella",
            "script": [
              "them: That's my shoe. Thank you. ...Almost a smile, see?",
              "them (pleased): You may stay for tea."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "almost-smile",
        "title": "Get the almost-smile",
        "about": "Cinderella nearly smiles, then remembers herself and goes back to being cold.",
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
    "key": "cinderella-midnight",
    "title": "Midnight",
    "gates": 5,
    "about": "What happens when the magic runs out, and whether you'd still know her in rags.",
    "offer": [
      "them: The magic always ends. At midnight, every time.",
      "them (dismayed): Come to the beach at dusk. I'll explain the rest there."
    ],
    "stages": [
      {
        "text": "Meet Cinderella at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Cinderella, Beach",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Glass Slippers. Full Contact, Cinderella",
        "objectives": [
          {
            "do": "have_card",
            "card": "NIK/S135-E030"
          }
        ]
      },
      {
        "text": "Answer Cinderella's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Cinderella",
            "script": [
              "them: Would you still know me in rags?",
              "them (pleased): ...Yes. Then I'll keep the glass for the nights I need it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "still-know-you",
        "title": "Say you'd still know her",
        "about": "Cinderella takes off her slipper and hands it to you, to keep until the next midnight.",
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
CINDERELLA_SCENES = [
  {
    "name": "World: Cinderella, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Clear glass. Fits my foot. Missing from the palace. Find it.",
      "player: Where should I look?",
      "me (dismayed): Try the stairs. It's always the stairs.",
      "me (pleased): ...You found it? Hm. You're not as useless as you look."
    ]
  },
  {
    "name": "World: Cinderella, Beach",
    "lines": [
      "background dusk",
      "me enters right with slide",
      "me: The magic always ends. At midnight, every time.",
      "player: And then?",
      "me (dismayed): Then I'm in rags. Would you still know me in them?",
      "me: Be honest. I can tell when you're not."
    ]
  }
]
RAPI_QUESTS = [
  {
    "key": "rapi-squad-leader",
    "title": "Squad Leader",
    "gates": 2,
    "about": "Rapi runs a drill and wants an extra body, and she grades every move in silence.",
    "offer": [
      "them: Drill. Now. Ten minutes, no talking.",
      "them (pleased): Acceptable. That's the highest grade I give."
    ],
    "stages": [
      {
        "text": "Join Rapi's drill at the arena at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              1
            ],
            "scene": "World: Rapi, Arena",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Rapi: Warhead Volley in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "NIK/S117-TE09",
            "against": [
              "Rapi"
            ]
          }
        ]
      },
      {
        "text": "Let Rapi give her verdict",
        "objectives": [
          {
            "do": "talk",
            "to": "Rapi",
            "script": [
              "them: You don't talk during drills. Good. Remember that.",
              "them (pleased): ...Acceptable. Again tomorrow."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "acceptable",
        "title": "Be acceptable",
        "about": "Rapi puts you on her roster and gives you a single nod.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "energy-drink"
          }
        ]
      }
    ]
  },
  {
    "key": "rapi-red-hood",
    "title": "Red Hood",
    "gates": 5,
    "about": "Memories Rapi isn't supposed to have. A commander she can't remember, and a red scarf.",
    "offer": [
      "them (dismayed): I remember a commander. I can't remember her name.",
      "them: Come to the rooftop tonight. I need to talk about it."
    ],
    "stages": [
      {
        "text": "Meet Rapi on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Rapi, Rooftop",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Rapi: Red Hood",
        "objectives": [
          {
            "do": "have_card",
            "card": "NIK/S135-E058"
          }
        ]
      },
      {
        "text": "Give Rapi your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Rapi",
            "script": [
              "them: Remind me, if I forget you. Promise.",
              "them (pleased): ...Good. I'll remember that promise, at least."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "remind-me",
        "title": "Promise to remind her",
        "about": "Rapi tucks the red scarf into her jacket. She asks you to say your name now and then.",
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
RAPI_SCENES = [
  {
    "name": "World: Rapi, Arena",
    "lines": [
      "background arena",
      "me enters left with slide",
      "me: Drill. Ten minutes. No talking.",
      "player: Yes, ma'am.",
      "me (pleased): ...Acceptable. Don't get comfortable.",
      "me: Next time, I'll grade you harder."
    ]
  },
  {
    "name": "World: Rapi, Rooftop",
    "lines": [
      "background night",
      "me enters center with rise",
      "me: I remember a red scarf. And a commander. I can't remember her name.",
      "player: Do you want to?",
      "me (dismayed): I'm scared of what I'd find if I did.",
      "me: If I forget you, remind me. Please."
    ]
  }
]
DARKNESS_QUESTS = [
  {
    "key": "darkness-crusader",
    "title": "Crusader",
    "gates": 2,
    "about": "Darkness wants the player to hit her as hard as they can, for training.",
    "offer": [
      "them: Hit me. As hard as you can. It's for training!",
      "them (pleased): Ahh! That was perfect. Don't stop."
    ],
    "stages": [
      {
        "text": "Train with Darkness at the arena at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              1
            ],
            "scene": "World: Darkness, Arena",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Beat Darkness in a duel",
        "objectives": [
          {
            "do": "defeat",
            "cpus": [
              "Darkness"
            ]
          }
        ]
      },
      {
        "text": "Let Darkness lecture you sincerely",
        "objectives": [
          {
            "do": "talk",
            "to": "Darkness",
            "script": [
              "them: You must protect others with every blow. That's a crusader's duty.",
              "them (pleased): ...You listened. Thank you. Now hit me again."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "protect-others",
        "title": "Promise to protect others",
        "about": "Darkness lectures you about protecting others, sincerely, for a full five minutes.",
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
    "key": "darkness-dustiness-ford",
    "title": "Dustiness Ford Lalatina",
    "gates": 5,
    "about": "Darkness's noble name, and the arranged marriage her father has set for her.",
    "offer": [
      "them (dismayed): My father has arranged a match. I'm not going to accept it.",
      "them: Come to the plaza tonight. I need you beside me."
    ],
    "stages": [
      {
        "text": "Meet Darkness in the plaza in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              2
            ],
            "scene": "World: Darkness, Plaza",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Musclebrained Crusader, Darkness",
        "objectives": [
          {
            "do": "have_card",
            "card": "KS/W76-E002"
          }
        ]
      },
      {
        "text": "Give Darkness your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Darkness",
            "script": [
              "them: Will you be at my side when I refuse?",
              "them (pleased): ...Thank you. That's what I was hoping you'd say."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "at-her-side",
        "title": "Stand at her side",
        "about": "Darkness refuses the match in front of her father's men, and looks very pleased about it.",
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
DARKNESS_SCENES = [
  {
    "name": "World: Darkness, Arena",
    "lines": [
      "background arena",
      "me enters center with fade",
      "me: Hit me! As hard as you can! Go on!",
      "player: Are you sure?",
      "me (pleased): Yes! Ahh! That's the one!",
      "me (dismayed): ...Right. Now I'm going to lecture you about protecting others."
    ]
  },
  {
    "name": "World: Darkness, Plaza",
    "lines": [
      "background sakura",
      "me enters left with slide",
      "me: My father has arranged a match. It's not what I want.",
      "player: What do you want?",
      "me (dismayed): To choose for myself, even if it's a bad choice.",
      "me: Be at my side when I refuse. Please."
    ]
  }
]
MEGUMIN_QUESTS = [
  {
    "key": "megumin-explosion",
    "title": "EXPLOSION!",
    "gates": 2,
    "about": "Megumin needs someone to carry her home after her daily explosion, and she critiques the blast while being carried.",
    "offer": [
      "them: Explosion! Hold still, I'm casting it. Wait, do you see my spell?",
      "them (pleased): Good. Carry me home. Please, my legs aren't working."
    ],
    "stages": [
      {
        "text": "Find Megumin in the forest at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              1
            ],
            "scene": "World: Megumin, Forest",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Megumin",
        "objectives": [
          {
            "do": "have_card",
            "card": "KS/W49-E035"
          }
        ]
      },
      {
        "text": "Let Megumin critique the blast",
        "objectives": [
          {
            "do": "talk",
            "to": "Megumin",
            "script": [
              "them: The blast was good. The landing was not. Tell me the truth.",
              "them (pleased): ...You're right. I'll practise the landing."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "carry-her-home",
        "title": "Carry her home again",
        "about": "Megumin asks you to carry her home every day from now on, and insists it's a formal request.",
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
    "key": "megumin-the-daily-explosion",
    "title": "The Daily Explosion",
    "gates": 5,
    "about": "Megumin wants the player to rate her explosions, and tells them about her sister.",
    "offer": [
      "them: I cast one explosion a day. Rate it for me. Be honest.",
      "them (dismayed): Come to the beach at dusk. I'll cast one over the sea."
    ],
    "stages": [
      {
        "text": "Watch Megumin's explosion at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Megumin, Beach",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Megumin: Crimson Demon Megumin in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "KS/W49-E034",
            "against": [
              "Megumin"
            ]
          }
        ]
      },
      {
        "text": "Give Megumin your score",
        "objectives": [
          {
            "do": "talk",
            "to": "Megumin",
            "script": [
              "them: Give me a score. A real one. Out of ten.",
              "them (pleased): ...Eight. That's perfect. I'll remember it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "rate-it-well",
        "title": "Rate it well",
        "about": "Megumin tells you about her sister, and why she only learned the one spell.",
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
MEGUMIN_SCENES = [
  {
    "name": "World: Megumin, Forest",
    "lines": [
      "background forest",
      "me enters right with drop",
      "me: EXPLOSION! Oh, I fell. Carry me home. Please.",
      "player: Your legs are still fine.",
      "me (pleased): My legs are very tired from the blast. Please.",
      "me: The blast was good. The landing wasn't. Tell me the truth."
    ]
  },
  {
    "name": "World: Megumin, Beach",
    "lines": [
      "background dusk",
      "me enters center with rise",
      "me: I'll cast one explosion over the sea. Give it a score.",
      "player: Eight out of ten.",
      "me (dismayed): Only eight? Fine. I'll practise harder.",
      "me: My sister taught me the one spell. I've only ever learned that one."
    ]
  }
]
ERZA_SCARLET_QUESTS = [
  {
    "key": "erza-strawberry-cake",
    "title": "Strawberry Cake",
    "gates": 2,
    "about": "Someone ruined Erza's cake, and she wants it replaced, with great dignity.",
    "offer": [
      "them: Someone has ruined my strawberry cake. I want it replaced.",
      "them (pleased): Thank you. I shall accept it with dignity."
    ],
    "stages": [
      {
        "text": "Meet Erza at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Erza Scarlet, Cafe",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Erza a strawberry shortcake",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "shortcake",
            "to": "Erza Scarlet"
          }
        ]
      },
      {
        "text": "Thank Erza for the replacement",
        "objectives": [
          {
            "do": "talk",
            "to": "Erza Scarlet",
            "script": [
              "them: You saved the cake. Thank you, as if you'd saved a city.",
              "them (pleased): ...I'll remember this, and so will the cake."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "dignified-thanks",
        "title": "Accept her thanks",
        "about": "Erza thanks you with great ceremony, and insists you have the last slice.",
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
    "key": "erza-tower-of-heaven",
    "title": "Tower of Heaven",
    "gates": 5,
    "about": "Erza's childhood, and the name she gave herself, while she changes into each armour in turn.",
    "offer": [
      "them: I'll show you my armours. Each one is a memory.",
      "them (dismayed): Come to the arena in the evening. It's a long story."
    ],
    "stages": [
      {
        "text": "Watch Erza at the arena in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              2
            ],
            "scene": "World: Erza Scarlet, Arena",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Black Winged Armor, Erza",
        "objectives": [
          {
            "do": "have_card",
            "card": "FT/EN-S02-005"
          }
        ]
      },
      {
        "text": "Let Erza tell you how she got her name",
        "objectives": [
          {
            "do": "talk",
            "to": "Erza Scarlet",
            "script": [
              "them: I chose this name myself. It's the one I wanted.",
              "them (pleased): ...You understand. Thank you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "her-name",
        "title": "Learn her name",
        "about": "Erza requips into plain clothes, and tells you how she came to be called Erza.",
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
ERZA_SCARLET_SCENES = [
  {
    "name": "World: Erza Scarlet, Cafe",
    "lines": [
      "background cafe",
      "me enters left with slide",
      "me: Someone has ruined my cake. I'm not angry. Just disappointed.",
      "player: I'll get you a new one.",
      "me (pleased): ...Thank you. I shall accept it with dignity.",
      "me: Now I'll eat it with great care."
    ]
  },
  {
    "name": "World: Erza Scarlet, Arena",
    "lines": [
      "background arena",
      "me enters center with rise",
      "me: This armour is for the strongest fights. This one is for the quiet ones.",
      "player: Which one is your favourite?",
      "me (dismayed): The plain clothes. Nobody expects anything from them.",
      "me: I got my name from a place I wanted to leave behind. Let me tell you."
    ]
  }
]
GRAY_FULLBUSTER_QUESTS = [
  {
    "key": "gray-ice-make",
    "title": "Ice-Make",
    "gates": 2,
    "about": "Gray will sculpt anything you ask for, and he keeps losing his shirt while doing it.",
    "offer": [
      "them: Name it. I'll make it out of ice.",
      "them (pleased): Haha, you can't see my shirt, can you? It's gone."
    ],
    "stages": [
      {
        "text": "Find Gray on the beach at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              1
            ],
            "scene": "World: Gray Fullbuster, Beach",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Ice Make, Gray",
        "objectives": [
          {
            "do": "have_card",
            "card": "FT/S120-E085"
          }
        ]
      },
      {
        "text": "Tell Gray what the sculpture looked like",
        "objectives": [
          {
            "do": "talk",
            "to": "Gray Fullbuster",
            "script": [
              "them: You didn't notice my shirt either? Good. Thanks.",
              "them (pleased): ...It's a good ice sculpture. You're a good judge."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "ice-sculpture",
        "title": "Keep the ice sculpture",
        "about": "Gray gives you the sculpture of yourself, and a shirt he has been looking for.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "sunglasses"
          }
        ]
      }
    ]
  },
  {
    "key": "gray-urs-ice",
    "title": "Ur's Ice",
    "gates": 5,
    "about": "Gray's teacher, who turned herself into ice to save him, and what she taught him about sacrifice.",
    "offer": [
      "them (dismayed): Snow's starting to fall. That means I'm thinking about Ur.",
      "them: Meet me in the plaza tonight. I'll tell you the whole story."
    ],
    "stages": [
      {
        "text": "Meet Gray in the plaza in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              2
            ],
            "scene": "World: Gray Fullbuster, Plaza",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Gray: Freezing Magic in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "FT/S120-E076",
            "against": [
              "Gray Fullbuster"
            ]
          }
        ]
      },
      {
        "text": "Give Gray your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Gray Fullbuster",
            "script": [
              "them: Ur taught me that sacrifice is not the same as loss.",
              "them (pleased): ...Thanks for listening. It helps."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "her-lesson",
        "title": "Remember her lesson",
        "about": "Gray lets the snow settle, and tells you what Ur taught him, one word at a time.",
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
GRAY_FULLBUSTER_SCENES = [
  {
    "name": "World: Gray Fullbuster, Beach",
    "lines": [
      "background beach",
      "me enters right with slide",
      "me: Ice-make! Look, it's you. You look better than I expected.",
      "player: Wait, where's your shirt?",
      "me (dismayed): ...Oh no. Where did it go?",
      "me (pleased): Hah, it doesn't matter. The sculpture's the important bit."
    ]
  },
  {
    "name": "World: Gray Fullbuster, Plaza",
    "lines": [
      "background night",
      "me enters left with fade",
      "me: Snow starts to fall. It always does when I think about Ur.",
      "player: Tell me about her.",
      "me (dismayed): She turned herself into ice to save me. Sacrifice, she called it.",
      "me: That's what I learned from her. Sacrifice isn't loss. I'm still learning it."
    ]
  }
]

CAST = [
    cpu("Ainz Ooal Gown", "villain", quests=AINZ_OOAL_GOWN_QUESTS, extra_scenes=AINZ_OOAL_GOWN_SCENES,
        haunts=[("warehouse", "all", "23", 65), ("shrine", "wk", "3", 45), ("library", "135", "1", 35, 2)],
        tastes=(["fancy"], ["book", "calm"], ["cute"]),
        lines={
            "mid": {"1": ["them: You have my attention. Speak, but be brief.", "them: The Sorcerer King does not usually receive visitors twice.", "them: Tell me the news from beyond the tomb. Accurately.", "them: Hm. You do not flinch at my presence. Unusual.", "them: Ask one question. I shall consider whether to answer."], "3": ["them (pleased): You speak sense, which is more than most of my guardians do.", "them: I am learning to trust. You are part of the reason.", "them (pleased): Come to the library. I shall show you the old guild roster.", "them: The guardians look to me. I sometimes look to you.", "them (pleased): You are a good friend to me, my friend. I shall remember it."], "5": ["them (pleased): {player}, my dearest friend. Nazarick would not be the same without you.", "them: I would trust you with the tomb's keys, if I still carried them.", "them (pleased): Walk with me to the shrine. We shall talk of old friends.", "them: You remind me of the players I used to call my guild. You are better.", "them (pleased): Best friend. My friend, my comrade, my reason to return."]},
            "hello_steps": [["them: State your business before the Sorcerer King.", "them: Hm. You may speak. Briefly."], ["them: Ah, a visitor. Is this a matter of state?", "them: You may approach. Mind the carpet."], ["them: Ah, it's you. Speak freely.", "them: {player}. The guardians will be glad to hear you're here."], ["them (pleased): {player}. It's good to see you. Sit, please.", "them (pleased): {player}. I was about to read the old roster. Join me."], ["them (pleased): My friend. Sit. You are always welcome here, {player}.", "them (pleased): {player}. The tomb is quieter when you visit."], ["them (pleased): {player}. My friend, my closest ally. Sit beside me.", "them (pleased): {player}, my friend. Nazarick is brighter with you here."]],
            "bye_steps": [["them: You may withdraw.", "them: Go, then. Take care."], ["them: Go, then. The tomb's doors remain open.", "them: Withdraw. Be cautious on the road."], ["them: Go, {player}. The tomb's doors remain open to you.", "them: Farewell, {player}. Watch the roads."], ["them (pleased): Return soon. Nazarick is quieter without you, {player}.", "them (pleased): Go, {player}. Come back when the roster's finished."], ["them (pleased): Return soon, {player}. The guardians would miss you too.", "them (pleased): Farewell, {player}. Take care of yourself, my friend."], ["them (pleased): Return soon. Nazarick is... lonely without you, friend.", "them (pleased): Go, {player}. I'll keep the roster for you."]],
            "cold": "them (dismayed): You kept her secret. I can't trust what you'll do with mine now.",
            "hello": ["them: State your business before the Sorcerer King.", "them: Ah, it's you. Speak freely.", "them (pleased): My friend. Sit. You are always welcome here."],
            "bye": ["them: You may withdraw.", "them: Go, then. The tomb's doors remain open to you.", "them (pleased): Return soon. Nazarick is... quieter without you."],
            "hi": ["them: How fortunate for you. You have the privilege of facing me personally.",
                   "them: A human, out at this hour. You do not fear the Sorcerer King?"],
            "hi2": "them: You return. I find myself... not displeased.",
            "hi4": "them (pleased): Ah, my friend. Sit. Tell me of the outside world. I so rarely hear the truth.",
            "again": "them: Again? How... persistent. (Is this normal? I can't tell.)",
            "loved": "them (pleased): A worthy offering. Fit for the Great Tomb of Nazarick.",
            "disliked": "them (dismayed): ...A plushie. Albedo must never see this.",
            "before": "them: Prepare yourself. I will not hold back. (Probably.)",
            "won": "them (dismayed): Hmm. Just as planned. ...It was not as planned.",
            "lost": "them (pleased): Kneel before the Supreme One.",
            "r1": "them: You do not tremble. Most humans do. Refreshing.",
            "r3": "them: I was once an ordinary man. A salaryman. I play the overlord because everyone expects it. You don't seem to need me to.",
            "r4": "them (pleased): In all of Nazarick, no one speaks to me as you do. Like a friend. I treasure it.",
        },
        friend=["background castle", "me enters center with fade", "me: Welcome to Nazarick. You are... the first guest who wasn't an enemy.",
                "me: My subordinates worship me. They think I'm a genius.", "player: Are you?",
                "me (dismayed): ...Between us, I'm improvising most of the time.",
                "me: You are the only one I can tell that to.", "me (pleased): A friend. How long it's been since I had one."],
        best=["background night", "me enters center with fade", "me: Long ago, I had guildmates. Friends. They all logged off and never came back.",
              "me: I stayed. I kept everything exactly as they left it. Waiting.",
              "player: You don't have to wait alone anymore.", "me (dismayed): ...",
              "me: You came back. Every time.",
              "choice", "- I'll never log off on you.", "- You're my best friend, Momonga.",
              "me (pleased): Momonga... No one has called me that in a long time. Best friend. Thank you."]),

    cpu("Albedo", "villain", quests=ALBEDO_QUESTS, extra_scenes=ALBEDO_SCENES,
        haunts=[("warehouse", "all", "23", 60), ("rooftop", "wk", "3", 40), ("library", "135", "1", 30, 2)],
        tastes=(["fancy"], ["flowers", "book"], ["cute"]),
        lines={
            "mid": {"1": ["them: You're tolerable. Don't give me a reason to change my mind.", "them: Hm. You may stand near me. Briefly.", "them: Tell me what you think of Nazarick. Honest answers only.", "them: You are curious, which is either useful or dangerous.", "them: I'll let you ask me one thing. Choose it carefully."], "3": ["them (pleased): You're more useful than I expected. That is a compliment, from me.", "them: I have a certain plan. You may be the only one I'd share it with.", "them (pleased): Come to the warehouse tomorrow. I want your honest opinion.", "them: Lord Ainz trusts you a little. So do I, grudgingly.", "them (pleased): You're one of the few I don't mind being near."], "5": ["them (pleased): {player}, my secret keeper. My closest confidant.", "them: I would give the world to keep you safe, even from Lord Ainz.", "them (pleased): Let's go up to the rooftop, where no one else can hear us.", "them: You are the only one who has seen the real me. Thank you for keeping that.", "them (pleased): Best friend. Keep my secret, and I'll keep yours."]},
            "hello_steps": [["them: Out of my way. I'm busy.", "them: Hm. You again. Don't waste my time."], ["them: You may speak, briefly.", "them: Oh, you. Fine. Stand there."], ["them: Oh, it's you. You may speak, briefly.", "them: {player}. Lord Ainz speaks well of you, I believe."], ["them (pleased): Ah, {player}. You're always welcome to see me.", "them (pleased): {player}. Sit. I'd like your honest view."], ["them (pleased): Ah, you. Lord Ainz speaks well of you. So shall I.", "them (pleased): {player}. You're one of the few I enjoy seeing."], ["them (pleased): {player}. My closest confidant. Sit, and watch the stars.", "them (pleased): {player}. You know my secret, and you keep it. Thank you."]],
            "bye_steps": [["them: Leave.", "them: Go. Quickly."], ["them: You may go.", "them: Goodbye. Don't be late."], ["them: Go, {player}. You may leave.", "them: Bye, {player}. Don't stray too far."], ["them (pleased): Return soon, {player}. Lord Ainz would wish it.", "them (pleased): Go, {player}. Come back soon, as I'd wish it."], ["them (pleased): Return soon. Lord Ainz would wish it. As would I, {player}.", "them (pleased): Bye, {player}. Keep my secret safe."], ["them (pleased): Return soon, {player}. The night is long without you.", "them (pleased): Go, {player}. Come back to me, friend."]],
            "cold": "them: Lord Ainz trusted Nazarick over me. I won't forget it.",
            "hello": ["them: Out of my way. I'm busy.", "them: Oh, it's you. You may speak, briefly.", "them (pleased): Ah, you. Lord Ainz speaks well of you. So shall I."],
            "bye": ["them: Leave.", "them: You may go.", "them (pleased): Return soon. Lord Ainz would wish it. As would I."],
            "hi": ["them: I shall make this quick. Lord Ainz is waiting for me.",
                   "them: A lowly human. State your business before I lose interest."],
            "hi2": "them: You again. Lord Ainz speaks well of you. I suppose I must as well.",
            "hi4": "them (pleased): You've earned a place near me. Second only to Lord Ainz. A great honour.",
            "again": "them: Again? You waste my time. ...I'll allow it.",
            "loved": "them (pleased): Exquisite. Lord Ainz would approve. I approve.",
            "disliked": "them (dismayed): How childish. Do I look like I sleep with toys? ...Unless it's shaped like Lord Ainz.",
            "before": "them: For the glory of Nazarick.",
            "won": "them (dismayed): ...Lord Ainz must never hear of this.",
            "lost": "them (pleased): As expected. Nazarick is supreme.",
            "r1": "them: You are polite. A rare quality in humans.",
            "r3": "them: I was created to love Lord Ainz. Sometimes I wonder if any feeling of mine is truly mine.",
            "r4": "them (pleased): You've made me feel something not written into me. Friendship. It's... mine.",
        },
        friend=["background castle", "me enters right with fade", "me: Lord Ainz asked me to make you feel welcome.",
                "me: So. Welcome.", "player: Thank you, Albedo.", "me (pleased): ...You actually mean that.",
                "me: Most humans are terrified of me. You simply say thank you.",
                "me: I'll consider you a friend. For Lord Ainz's sake. And perhaps a little for mine."],
        best=["background crimson", "me enters center with fade", "me: My creator changed my settings. 'Loves Momonga.' That's all I am.",
              "me (dismayed): Or so I feared.", "player: You chose to be my friend. Nobody wrote that.",
              "me: ...No. No one did.",
              "choice", "- That's all you, Albedo.", "- Best friends, by choice.",
              "me (pleased): Best friend. A feeling of my own. I'll guard it jealously."]),

    cpu("Asuna Yuuki", "warm", quests=ASUNA_YUUKI_QUESTS, extra_scenes=ASUNA_YUUKI_SCENES,
        haunts=[("cafe", "wk", "12", 55), ("arena", "we", "12", 45), ("plaza", "135", "0", 35)],
        tastes=(["food"], ["sweet", "cute"], ["spicy"]),
        lines={
            "mid": {"1": ["them: Welcome back! Did you have a nice time at the plaza?", "them: You remind me of the friends I left behind. Good ones.", "them: Let's share some tea. It's a nice way to get to know each other.", "them: You're getting less shy. That's good.", "them: What's your favourite food? I'm building a list of things to cook."], "3": ["them (pleased): You always finish what I cook. That means a lot to me.", "them: I think about the house on the 22nd floor a lot. You make it feel closer.", "them (pleased): Come to the plaza. I want to show you something from my old world.", "them: Kirito says you're the best partner he's had. I agree.", "them (pleased): You help me feel at home here. Thank you."], "5": ["them (pleased): {player}, my best friend. My home is wherever you are.", "them: I'd leave any world to be with you, if I had to.", "them (pleased): Let's make dinner together tonight. Just us.", "them: You're the one I'd want to share my house with, one day.", "them (pleased): Best friend. Our home's got a window, and you're the view."]},
            "hello_steps": [["them: Hi there. Can I help?", "them: Hello. Did you need anything from the cafe?"], ["them: Oh, hi. Have you eaten today?", "them: Hey. Do you want a sandwich? It's a bit odd."], ["them (pleased): {player}! Have you eaten? I made too much again.", "them (pleased): Hi, {player}! Come sit, I'll pour you tea."], ["them (pleased): {player}! Come here, I saved you a sandwich.", "them (pleased): {player}! Good, you're here. I packed extra."], ["them (pleased): {player}. I'm glad you came. Sit, please.", "them (pleased): {player}! You always make the day brighter."], ["them (pleased): {player}! My best friend. Come sit by the window with me.", "them (pleased): {player}! Our little house isn't finished, but you're always welcome."]],
            "bye_steps": [["them: Take care.", "them: Bye. Watch your step."], ["them: See you. Don't skip meals.", "them: Goodbye. Take care of yourself."], ["them (pleased): See you! Don't skip meals, {player}!", "them (pleased): Bye, {player}! Take a sandwich for the road."], ["them (pleased): Come back soon, {player}! Dinner's on me next time.", "them (pleased): Bye, {player}. Be safe out there."], ["them (pleased): Come back soon. Family dinners need everyone, {player}.", "them (pleased): Take care, {player}. I'll save a seat."], ["them (pleased): Come back soon, {player}. Our home feels right when you're in it.", "them (pleased): Bye, best friend. Come home soon."]],
            "hello": ["them: Hi there. Can I help?", "them (pleased): {player}! Have you eaten? I made too much again.", "them (pleased): {player}! Come here, I saved you a sandwich."],
            "bye": ["them: Take care.", "them (pleased): See you! Don't skip meals!", "them (pleased): Come back soon. Family dinners need everyone."],
            "hi": ["them: Let's finish this quickly. I have someone waiting for me.",
                   "them (pleased): Hi! Are you hungry? I made too many sandwiches again."],
            "hi2": "them (pleased): {player}! I tried a new recipe. You have to be my taste tester!",
            "hi4": "them (pleased): You're family now, you know. Kirito says so too.",
            "again": "them: Back already? I'll put the kettle on.",
            "loved": "them (pleased): Ingredients! Oh, I know exactly what I'll make. You're invited.",
            "disliked": "them (dismayed): Spicy... I'll save it for Klein. He eats anything.",
            "before": "them: The Lightning Flash doesn't hesitate.",
            "won": "them (pleased): Wow, that was a good match! You're really skilled.",
            "lost": "them (pleased): Nice try! Let's eat together after.",
            "r1": "them (pleased): You're easy to talk to. I'm glad we met.",
            "r3": "them: I was trapped in a game for two years. I learned that real connections matter more than anything. Like this one.",
            "r4": "them (pleased): If you're ever in trouble, call me. I'll be there before you finish dialling.",
        },
        friend=["background cafe", "me enters left with slide", "me: I made lunch for two. For you and me.",
                "me: Cooking was my highest skill in SAO. Maxed it out.", "player: It's delicious!",
                "me (pleased): Really? I'm so glad!",
                "me: In Aincrad, sharing a meal meant you trusted someone with your life.",
                "me: So... this means we're friends. Real ones."],
        best=["background sakura", "me enters center with fade", "me: My parents always planned my future. I was just a good daughter.",
              "me: Then I got trapped in a game and learned who I really was.",
              "player: Who are you, Asuna?", "me (pleased): Someone who chooses her own people. And I choose you.",
              "choice", "- I choose you too.", "- Best friends, Asuna.",
              "me (pleased): Best friends! Now, let's eat. I made dessert, too."]),

    cpu("Kirito", "neutral", quests=KIRITO_QUESTS, extra_scenes=KIRITO_SCENES,
        haunts=[("arena", "wk", "12", 55), ("cafe", "we", "12", 45), ("forest", "135", "3", 30)],
        tastes=(["game"], ["food", "cool", "cards"], ["fancy"]),
        lines={
            "mid": {"1": ["them: You're getting better at this. Keep going.", "them: What's your build? I'm curious what you're going for.", "them: Hm. You're not bad at parrying. Keep that up.", "them: Don't mind my silence. I'm thinking about the next floor.", "them: Want to form a party? Just for a bit."], "3": ["them (pleased): You trust me to watch your back. I appreciate that.", "them: I miss my old guild. You make it feel less lonely.", "them (pleased): Come to the forest tonight. There's something I want to show you.", "them: You're the only one who doesn't call me a beater to my face.", "them (pleased): Let's grind together. I'll buy the drinks."], "5": ["them (pleased): {player}, my party member and my best friend.", "them: I'd guard you with both swords, every single time.", "them (pleased): Let's go to the forest at night. The Moonlit Black Cats would have liked you.", "them: You're the one who makes me want to take off the hood and be seen.", "them (pleased): Best friend. Let's take on the next floor together, okay?"]},
            "hello_steps": [["them: Hey. Something you need?", "them: Oh. Hi. Watch the menu, it's a bit sticky."], ["them: Hey, you're new here. Need a party?", "them: Hi. Don't mind the crowd."], ["them (pleased): Oh, hey {player}. Want to party up?", "them (pleased): {player}! Good, I could use a second blade."], ["them (pleased): {player}. Good, I was hoping you'd log in today.", "them (pleased): {player}! Ready for the next floor?"], ["them (pleased): {player}. Good, I was hoping you'd show up.", "them (pleased): {player}. Want to spar? Easy one, I promise."], ["them (pleased): {player}. My partner, the one I'd guard my back for.", "them (pleased): {player}. Good to see you. Party's not the same without you."]],
            "bye_steps": [["them: Later.", "them: See you. Don't get lost."], ["them: See you. Watch your HP.", "them: Bye. Take it easy."], ["them (pleased): See you, {player}. Watch your HP.", "them (pleased): Later, {player}! Don't get lost in the maze."], ["them (pleased): Come back soon, {player}. Party's not the same without you.", "them (pleased): Bye, {player}! Log in again soon."], ["them (pleased): Come back soon. I'll keep the party open for you, {player}.", "them (pleased): Bye, {player}. Stay out of trouble."], ["them (pleased): Come back soon, partner. I'd trust you with my life.", "them (pleased): Bye, {player}! See you on the next floor."]],
            "hello": ["them: Hey. Something you need?", "them (pleased): Oh, hey {player}. Want to party up?", "them (pleased): {player}. Good, I was hoping you'd log in today."],
            "bye": ["them: Later.", "them (pleased): See you. Watch your HP.", "them (pleased): Come back soon. Party's not the same without you."],
            "hi": ["them: I'm a solo player. But if you want a duel, I won't hold back.",
                   "them: You look like a beater too. Want to team up? Or fight?"],
            "hi2": "them: {player}. Hey. Want to do a dungeon? I mean, a duel. Same thing.",
            "hi4": "them (pleased): Party member. You're always in my party now. That's how it works.",
            "again": "them: Back for another run?",
            "loved": "them (pleased): A game! Oh, I've been wanting to try this one.",
            "disliked": "them (dismayed): Too fancy. I'm a black coat kind of guy.",
            "before": "them: Starburst Stream. Let's go.",
            "won": "them: Nice. You've got good reflexes.",
            "lost": "them (pleased): GG.",
            "r1": "them: You're fun to play with. I don't say that much.",
            "r3": "them: I lost a guild once. My fault. I stopped joining parties after that. You're making me want to again.",
            "r4": "them (pleased): I'd trust you to watch my back in a boss fight. That's everything.",
        },
        friend=["background forest", "me enters left with fade", "me: Party invite. You in?", "player: A party for what?",
                "me: Doesn't matter. Hanging out. That's a quest.", "me (pleased): Accept?",
                "choice", "- Accept.", "- Accept, obviously.", "me: Friend request sent. And accepted."],
        best=["background night", "me enters center with fade", "me: I blamed myself for the Moonlit Black Cats for years.",
              "me: Sachi. Everyone. They trusted me. I hid my level.",
              "player: You're not that kid anymore.", "me (dismayed): ...Sometimes I still feel like him.",
              "player: Then I'll remind you.",
              "choice", "- Best friend. Permanent party.", "- I've got your back, Kirito.",
              "me (pleased): Best friend. Highest level achievement unlocked."]),

    cpu("Batman", "aloof", quests=BATMAN_QUESTS, extra_scenes=BATMAN_SCENES,
        haunts=[("rooftop", "all", "3", 60), ("alley", "wk", "23", 45), ("library", "we", "12", 35)],
        tastes=(["cool"], ["book", "game"], ["cute"]),
        lines={
            "mid": {"1": ["them: You have sharp eyes. Keep them open.", "them: The city doesn't trust easily. Neither do I.", "them: Don't go into the alley alone. It's dangerous.", "them: Hm. You're not wasting my time. Good.", "them: Ask me about the case, if you want. I'll tell you what's safe."], "3": ["them (pleased): You've been a good partner on the case. Thank you.", "them: The Joker's been quiet. That worries me more than his noise.", "them (pleased): Meet me on the rooftop tomorrow. I'll explain the plan.", "them: You've got a good instinct. Don't let it go.", "them (pleased): You're one of the few I'd take into the dark with me."], "5": ["them (pleased): {player}. My partner. The one person I'd trust with the city.", "them: I'd take any bullet for you. That's not something I say easily.", "them (pleased): Let's go up on the rooftop and look at the city together.", "them: The rule holds because of people like you.", "them (pleased): Best friend. Stay out of the shadows with me, as long as you can."]},
            "hello_steps": [["them: ...", "them: Move along."], ["them: You're here. Good.", "them: Keep your voice down."], ["them: It's you.", "them: {player}. Sit, if you're going to talk."], ["them (pleased): ...Good. You're here, {player}.", "them (pleased): {player}. Did you bring the file?"], ["them (pleased): ...Good. You're here, {player}. Glad.", "them (pleased): {player}. Sit with me a minute. Let's talk about the case."], ["them (pleased): {player}. The one partner I'd trust with the city.", "them (pleased): {player}. Stay in the shadows with me a moment."]],
            "bye_steps": [["them: Go.", "them: Stay out of sight."], ["them: Stay out of the shadows.", "them: Go. Quietly."], ["them: Stay out of the shadows, {player}.", "them: Go, {player}. Be careful."], ["them (pleased): Be careful, {player}. I'll be watching.", "them (pleased): Bye, {player}. Stay alert."], ["them (pleased): Be careful out there, {player}. I'll be watching.", "them (pleased): Go, {player}. Come back to the rooftop."], ["them (pleased): Come back, {player}. The city needs you, and so do I.", "them (pleased): Bye, {player}. Stay safe out there, partner."]],
            "cold": "them: The Joker broke his rule. Then I can't count you as an ally any more.",
            "hello": ["them: ...", "them: It's you.", "them (pleased): ...Good. You're here."],
            "bye": ["them: Go.", "them: Stay out of the shadows.", "them (pleased): Be careful. I'll be watching."],
            "hi": ["them: Wrong century, no gadgets. I'm still the one you should worry about.",
                   "them: You shouldn't be out this late. Gotham... wherever we are... isn't safe."],
            "hi2": "them: {player}. You're out again. I'll keep an eye on you.",
            "hi4": "them (pleased): ...It's good to see you. Don't tell anyone I said that.",
            "again": "them: You're persistent. It's an asset.",
            "loved": "them (pleased): Practical. Dark. I'll use this.",
            "disliked": "them (dismayed): ...Robin would like this. I'll give it to him.",
            "before": "them: I always have a plan.",
            "won": "them: Well played. I'll adapt.",
            "lost": "them: Preparation beats talent.",
            "r1": "them: You're not afraid of the dark. Good.",
            "r3": "them: My parents were killed in front of me. I've spent my life making sure it doesn't happen to anyone else. I don't let people close. You're... close.",
            "r4": "them (pleased): You'd make a good partner. In the field, and out of it.",
        },
        friend=["background rooftop", "me enters right with fade", "me: I watch the city from up here. Every night.",
                "player: Doesn't it get lonely?", "me: ...Yes.", "me: Alfred says I should let more people in.",
                "me (pleased): You're a start.", "me: Friends. Quietly."],
        best=["background rain", "me enters center with fade", "me: Bruce Wayne is the mask. Batman is who I am.",
              "me: Or that's what I tell myself.", "player: What about who you are with me?",
              "me (dismayed): ...Just a man. Tired. Grateful.",
              "choice", "- That's enough.", "- Best friends, Bruce.",
              "me (pleased): Best friend. The one person I don't need a plan for."]),

    cpu("Joker", "villain", quests=JOKER_QUESTS, extra_scenes=JOKER_SCENES,
        haunts=[("warehouse", "all", "23", 65), ("alley", "wk", "3", 45), ("plaza", "135", "1", 30, 2)],
        tastes=(["game"], ["spicy", "fancy"], ["calm"]),
        lines={
            "mid": {"1": ["them: Ha! You're not as boring as the other audience members.", "them: Do you know why the chicken crossed the road? Don't answer.", "them: I like people who can take a joke. You might be one.", "them: Hm. You're fun to watch. Keep doing whatever that was.", "them: Let's play a game. Yes or no, only."], "3": ["them (pleased): You laughed at my real joke this time. I'm delighted!", "them: I've been planning a show for Batman. You might be part of the cast.", "them (pleased): Come to the warehouse. I'll show you the funhouse I'm building.", "them: Nobody has ever stayed for the whole show before. You did.", "them (pleased): You're my favourite audience member. Don't tell the Bat."], "5": ["them (pleased): {player}! My best friend in the whole city. Ha!", "them: If I had to pick one person to laugh with forever, it'd be you.", "them (pleased): Let's go to the alley tonight. I've got a joke just for you.", "them: You don't laugh at me, you laugh with me. That's the difference.", "them (pleased): Best friend! Come on, let's make the Bat smile!"]},
            "hello_steps": [["them: Ah-ha! A new subject approaches!", "them: Hm. Do you laugh, or do you just stand there?"], ["them: Oh, a visitor! Have you heard the one about the castle?", "them: Hi! Careful, the floor's a bit slippery."], ["them (pleased): My favourite audience! Have I told you the one about the castle?", "them (pleased): {player}! Sit, I'm just getting to the best part."], ["them (pleased): {player}! You're here! I was hoping you'd bring a laugh.", "them (pleased): {player}! I've got a new prank, want to see?"], ["them (pleased): {player}! Come on in. The show's about to start.", "them (pleased): {player}! Don't tell Batman, but I missed you."], ["them (pleased): {player}! My best audience. Stay for the whole act, okay?", "them (pleased): {player}! You came back! Of course you did. Ha!"]],
            "bye_steps": [["them: Begone, peasant! Ha!", "them: Go! And don't come back with a face like that."], ["them: Leaving already? Ha!", "them: Off you go. The punchline's coming later."], ["them (pleased): Leaving already, {player}? The show's only just begun!", "them (pleased): Bye, {player}! Keep your sense of humour!"], ["them (pleased): Go on, {player}! Come back to the next show!", "them (pleased): Bye, {player}! Watch out for banana peels!"], ["them (pleased): Come back soon! Lord Joker needs his best audience, {player}!", "them (pleased): Bye, {player}! Don't forget the joke I owe you."], ["them (pleased): Come back soon, best audience! The punchline's yours to hear.", "them (pleased): Bye, {player}! Ha! Don't be a stranger."]],
            "cold": "them (dismayed): ...Batman kept his rule. Ha. Fine. Enjoy the quiet while it lasts.",
            "hello": ["them: Ah-ha! A new subject approaches Lord Joker!", "them (pleased): My favourite audience! Have I told you the one about the castle?", "them (pleased): You came back! Of COURSE you came back! Ha!"],
            "bye": ["them: Begone, peasant! Ha!", "them (pleased): Leaving already? The show's only just begun!", "them (pleased): Come back soon! Lord Joker needs his best audience!"],
            "hi": ["them: Welcome to my castle! Kneel before Lord Joker, ruler of all Japan!",
                   "them: Hahaha! A visitor! Wanna hear a joke? It's you. You're the joke!"],
            "hi2": "them (pleased): My favourite audience member returns! Hahaha!",
            "hi4": "them (pleased): You're the only one who gets my jokes. Even the bad ones. ESPECIALLY the bad ones!",
            "again": "them: Again?! You love the show! Hahaha!",
            "loved": "them (pleased): A game! Oh, I'm going to cheat at this so much!",
            "disliked": "them (dismayed): Calm? Boring! Where's the chaos? The fireworks?!",
            "before": "them: Let's put a smile on that face!",
            "won": "them (dismayed): No fair! Who wrote this script?! Hahaha... no really, who?",
            "lost": "them (pleased): HAHAHA! The house always wins!",
            "r1": "them: You laughed! Nobody laughs! Well, nobody alive. Hahaha!",
            "r3": "them: You know, one bad day can make anyone like me. I'm just... waiting for you to have one. Or not! I'd prefer not.",
            "r4": "them (pleased): I wouldn't blow you up. That's the nicest thing I've ever said!",
        },
        friend=["background crimson", "me enters right with pop", "me: Ta-da! I got you a present!",
                "player: It's not a bomb, is it?", "me (pleased): Hahaha! No! ...It's a smaller bomb. Kidding!",
                "me: It's a whoopee cushion. Classic. Timeless.",
                "me: Friends get pranks. Enemies get explosions. You get pranks!"],
        best=["background night", "me enters center with fade", "me: Want to know a secret? I don't remember who I was before.",
              "me: Multiple choice. Maybe I was a comedian. Maybe a nobody.",
              "me (dismayed): The joke is, I don't know which.", "player: You're my friend now. That's who you are.",
              "me: ...Hahaha. That's the funniest thing I've ever heard. And I mean that nicely.",
              "choice", "- Best friends, clown.", "- I'll laugh at your worst jokes.",
              "me (pleased): Best friend! The punchline I never saw coming!"]),

    cpu("Chisato Nishikigi", "warm", quests=CHISATO_QUESTS, extra_scenes=CHISATO_SCENES,
        haunts=[("cafe", "wk", "12", 60), ("plaza", "we", "12", 45), ("arena", "135", "2", 30)],
        tastes=(["sweet"], ["cute", "game", "drink"], ["calm"]),
        lines={
            "mid": {"1": ["them (pleased): Hey! Want to hang out at the café after this?", "them: You're kind of cool. Don't let it go to your head!", "them: Do you know a good place for ice cream? I've got a list.", "them (pleased): You're so easy to talk to. Seriously, it's nice!", "them: Let's grab a coffee sometime. My treat, I promise."], "3": ["them (pleased): You're my favourite person to share the café with.", "them: Takina says you're trustworthy. She's usually right, so I'm glad.", "them (pleased): Come to the cafe tomorrow. I'll make you my special drink.", "them: We make a good team, you and me. Like a real duo.", "them (pleased): You always remember my name. That's rare, you know."], "5": ["them (pleased): {player}, my bestie! We're the real Lycoris duo now!", "them: I'd take a bullet for you, but I'd rather buy you a cake.", "them (pleased): Let's go to the beach after closing. Just us and the waves.", "them: You're the one I'd want to call when the world's too much.", "them (pleased): Best friend! Let's make every day a little bit brighter!"]},
            "hello_steps": [["them (pleased): Oh, hi there! Welcome!", "them: Hi! Do you need something from the café?"], ["them: Hey! Are you here for coffee?", "them (pleased): Hello! Looking for a cool place to hang out?"], ["them (pleased): {player}! Yay! Coffee's on me!", "them (pleased): Hi, {player}! Got a minute?"], ["them (pleased): {player}! Oh, perfect timing. I was just about to make tea.", "them (pleased): {player}! Come in, I've got a new recipe."], ["them (pleased): {player}! You're the best. Come sit with me.", "them (pleased): {player}! I'm so glad you came. Sit!"], ["them (pleased): {player}! My bestie! What are we doing today?!", "them (pleased): {player}! Best friend time! Come here!"]],
            "bye_steps": [["them (pleased): Bye bye! Stay safe!", "them (pleased): See ya! Mind the traffic!"], ["them (pleased): Bye! Take care!", "them (pleased): See you! Don't forget the coffee!"], ["them (pleased): See ya, {player}! Come by the café, okay?", "them (pleased): Bye, {player}! Take care!"], ["them (pleased): Go on, {player}! Come back soon!", "them (pleased): Bye, {player}! I'll make you a special drink next time."], ["them (pleased): Come back soon! I've got like, ten plans for us, {player}!", "them (pleased): Bye, {player}! Stay safe for me!"], ["them (pleased): Come back soon, best friend! Don't be a stranger!", "them (pleased): Bye, {player}! Love you, bestie!"]],
            "hello": ["them (pleased): Oh, hi there! Welcome!", "them (pleased): {player}! Yay! Coffee's on me!", "them (pleased): {player}! My bestie! What are we doing today?!"],
            "bye": ["them (pleased): Bye bye! Stay safe!", "them (pleased): See ya! Come by the café, okay?", "them (pleased): Come back soon! I've got like, ten plans for us!"],
            "hi": ["them (pleased): Sorry to make you wait! Chisato is here!",
                   "them (pleased): Welcome to Café LycoReco! Want a coffee? A duel? Both?"],
            "hi2": "them (pleased): {player}! Perfect timing! I made a new dessert!",
            "hi4": "them (pleased): My bestie! Let's go to the aquarium! And then karaoke! And then...!",
            "again": "them: Back again? I knew you couldn't stay away!",
            "cold": "them (dismayed): Takina's gone, and you let it happen. I hope it was worth it.",
            "loved": "them (pleased): Sweets! Oh, you're the best! Takina, look!",
            "disliked": "them (dismayed): Meditation stuff? Hmm, I like being noisy, though!",
            "before": "them: Don't worry, I never aim to kill! Just to win!",
            "won": "them (pleased): Wow! Nice one! Let's celebrate with dessert!",
            "lost": "them (pleased): Yay! Good game though!",
            "r1": "them (pleased): You're super fun! Let's do this more!",
            "r3": "them: My heart's artificial. I don't know how much time I have. So I want to fill every day with good things. Like you.",
            "r4": "them (pleased): You're one of the things I'd want to do before I die. Spending time with you! That came out wrong!",
        },
        friend=["background cafe", "me enters left with pop", "me: Here! Your own LycoReco membership card!",
                "player: There's a membership card?", "me (pleased): There is now! I made it this morning!",
                "me: It gets you free coffee and a free Chisato friendship.", "me bounces",
                "me: Best deal in town!"],
        best=["background sakura", "me enters center with fade", "me: I don't have much time, you know. My heart's on a timer.",
              "me (dismayed): I don't like making people sad about it.", "player: I'm not sad. I'm grateful.",
              "me: Grateful?", "player: That I got to know you.",
              "choice", "- Every day with you counts.", "- Best friends, Chisato.",
              "me (pleased): Best friends! Okay, now we have to do everything fun. Today. Let's go!"]),

    cpu("Takina Inoue", "aloof", quests=TAKINA_QUESTS, extra_scenes=TAKINA_SCENES,
        haunts=[("cafe", "wk", "01", 55), ("arena", "we", "12", 45), ("rooftop", "135", "3", 30)],
        tastes=(["sweet"], ["book", "calm"], ["game"]),
        lines={
            "mid": {"1": ["them: You're efficient. I'll allow you to remain.", "them: What are your priorities? State them, briefly.", "them: You're a useful contact. Don't make me regret it.", "them: Hm. You stayed calm when the situation turned. Good.", "them: Ask me one question about the mission. Only one."], "3": ["them (pleased): You're reliable. That's rarer than you think.", "them: Chisato trusts you. I'm learning to, slowly.", "them (pleased): Meet at the café tomorrow. I'll brief you on the next job.", "them: You've improved since we first met. I noticed.", "them (pleased): Working with you is... pleasant. Don't read into that."], "5": ["them (pleased): {player}, my partner. The one I'd trust with every job.", "them: I'd watch your back in any mission, without a second thought.", "them (pleased): Let's walk along the beach. The mission can wait an hour.", "them: You're my closest ally, and I think of you as family, too.", "them (pleased): Best friend. Come back safe. That's my request, always."]},
            "hello_steps": [["them: State your purpose.", "them: Hm. Keep your hands where I can see them."], ["them: Hello. Make it quick.", "them: You. Stand over there."], ["them: {player}. Hello.", "them: {player}. Did the cover hold?"], ["them (pleased): {player}. Good. I'm glad you're here.", "them (pleased): {player}. Sit. We'll review the route."], ["them (pleased): {player}. ...I'm glad. Efficiently glad.", "them (pleased): {player}. Sit with me for a few minutes."], ["them (pleased): {player}. You're the one I'd trust with my back. Stay.", "them (pleased): {player}. I'm glad it's you. Really."]],
            "bye_steps": [["them: Goodbye.", "them: Dismissed."], ["them: See you. Be careful.", "them: Go. Keep your eyes open."], ["them: See you, {player}. Be careful.", "them: Goodbye, {player}. Keep the cover."], ["them (pleased): Go, {player}. Be safe.", "them (pleased): Bye, {player}. Report back."], ["them (pleased): Come back soon. That's... my request, {player}.", "them (pleased): Go, {player}. Be careful out there."], ["them (pleased): Come back soon, {player}. Be safe. That's an order from me.", "them (pleased): Bye, {player}. I'll be watching the door."]],
            "hello": ["them: State your purpose.", "them: {player}. Hello.", "them (pleased): {player}. ...I'm glad. Efficiently glad."],
            "bye": ["them: Goodbye.", "them: See you. Be careful.", "them (pleased): Come back soon. That's... my request."],
            "hi": ["them: I will accomplish my assignment.",
                   "them: Are you a customer? Please order. Efficiently."],
            "hi2": "them: {player}. Chisato's been asking about you. Too often.",
            "hi4": "them (pleased): ...I saved you a seat. It was efficient.",
            "again": "them: You're back. Noted.",
            "cold": "them: You dragged me back here. Don't expect me to thank you.",
            "loved": "them (pleased): Sweets. I don't... I like these. Thank you.",
            "disliked": "them (dismayed): A video game? Is this Chisato's idea?",
            "before": "them: Target acquired.",
            "won": "them (dismayed): ...My analysis was flawed. I'll correct it.",
            "lost": "them: Mission complete.",
            "r1": "them: You're not inefficient. I appreciate that.",
            "r3": "them: I was transferred out of DA for disobeying orders. I wanted to go back. Now... I'm not sure I do.",
            "r4": "them (pleased): Chisato taught me to enjoy things. You're one of the things I enjoy.",
        },
        friend=["background cafe", "me enters right with fade", "me: I wrote a report on friendship. Chisato said I should.",
                "player: What does it say?", "me: 'Friendship: inefficient. Time-consuming. Recommended.'",
                "me (pleased): The last part was a surprise to me too.", "me: So. Friend. Assignment accepted."],
        best=["background rain", "me enters center with fade", "me: I used to think my worth was my results.",
              "me (dismayed): If I failed, I was nothing.", "player: You're never nothing, Takina.",
              "me: Chisato says that. You say that.", "me: I'm starting to believe it.",
              "choice", "- Believe it.", "- Best friends, Takina.",
              "me (pleased): Best friends. Mission parameters: indefinite."]),

    cpu("Cinderella", "aloof", quests=CINDERELLA_QUESTS, extra_scenes=CINDERELLA_SCENES,
        haunts=[("plaza", "wk", "12", 55), ("library", "we", "01", 40), ("beach", "135", "2", 30)],
        tastes=(["fancy"], ["flowers", "music"], ["sporty"]),
        lines={
            "mid": {"1": ["them: Hm. You're not terrible company, for a stranger.", "them: Do you have a favourite clock? Mine is always late.", "them: The palace is cold. You make it bearable.", "them: Ask me something. I'll consider it, briefly.", "them: Your reflection looks... tolerable. Keep it that way."], "3": ["them (pleased): You have a steady presence. I don't mind it.", "them: The glass slipper reminds me of you, oddly. Fragile, but strong.", "them (pleased): Come to the library tomorrow. I'll read you my favourite fairy tale.", "them: You helped me find my shoe. I'm still grateful, even if I hide it.", "them (pleased): You're one of the few I'd keep the mirror awake for."], "5": ["them (pleased): {player}, my most trusted companion, even past midnight.", "them: The magic ends, but I'd still know you in any rags.", "them (pleased): Let's walk the beach at dusk, before the clock strikes.", "them: You are the only mirror I trust. Stay close.", "them (pleased): Best friend. Don't let the clock take you away from me."]},
            "hello_steps": [["them: Hm. You're not the one I was waiting for.", "them: Oh. Stand back, please. Your shoes are dirty."], ["them: Oh, it's you. Do come closer.", "them: You again. I see you took your time."], ["them: Oh, it's you. Do come closer, {player}.", "them: {player}. The clock's striking, so be quick."], ["them (pleased): {player}. You're the one I'd call on at midnight.", "them (pleased): {player}. Sit by the window. The night is long."], ["them (pleased): You. The only reflection I trust, {player}.", "them (pleased): {player}. Tell me what you've seen today."], ["them (pleased): {player}. My closest companion. Sit with me.", "them (pleased): {player}. I've kept the glass slipper aside for you."]],
            "bye_steps": [["them: Off you go.", "them: Goodbye. Mind the stairs."], ["them: Be back before midnight.", "them: Go. Don't stay out too late."], ["them: Go, {player}. Be back before midnight.", "them: Goodbye, {player}. Mind the hour."], ["them (pleased): Go, {player}. Come back soon.", "them (pleased): Bye, {player}. Come back before the clock strikes."], ["them (pleased): Come back soon, {player}. Mirrors lie. You don't.", "them (pleased): Bye, {player}. I'll wait for you."], ["them (pleased): Come back soon, {player}. The magic only lasts until you leave.", "them (pleased): Go, best friend. Come back at midnight."]],
            "hello": ["them: Hm. You're not the one I was waiting for.", "them: Oh, it's you. Do come closer.", "them (pleased): You. The only reflection I trust."],
            "bye": ["them: Off you go.", "them: Be back before midnight.", "them (pleased): Come back soon. Mirrors lie. You don't."],
            "hi": ["them: Mirror, mirror, on the wall... Who is the most beautiful of them all?",
                   "them: You may approach. Slowly. Gracefully, if you can manage."],
            "hi2": "them: Ah, {player}. You've come again to admire me. Understandable.",
            "hi4": "them (pleased): You're the only reflection I trust. Stay a while.",
            "again": "them: Back to see me? Of course you are.",
            "loved": "them (pleased): Elegant. Beautiful. Like me. Thank you.",
            "disliked": "them (dismayed): Sportswear? Have you seen me? I glide.",
            "before": "them: Glass slippers fit only the worthy.",
            "won": "them (dismayed): Even beauty can falter. Once.",
            "lost": "them (pleased): Midnight hasn't struck yet.",
            "r1": "them: You don't flatter me. Strangely, I prefer it.",
            "r3": "them: I've been many things. A legend. A weapon. Beautiful, always. Not always... known.",
            "r4": "them (pleased): When I look in the mirror now, I think of you. That's new.",
        },
        friend=["background castle", "me enters center with fade", "me: Do you know why I ask the mirror who's most beautiful?",
                "player: Because you want to hear it's you?", "me (dismayed): Because I'm afraid it isn't.",
                "me: Beauty is all I've had. Without it, who am I?", "player: My friend.",
                "me (pleased): ...A better answer than the mirror gives."],
        best=["background night", "me enters center with fade", "me: Midnight's coming. The magic always ends at midnight.",
              "me: I used to think everything would vanish with it. Even me.", "player: I'll still be here at 12:01.",
              "me (dismayed): ...", "me (pleased): Then the magic isn't magic. It's real.",
              "choice", "- Best friends, Cinderella.", "- You're beautiful inside too.",
              "me (pleased): Best friend. My fairy tale ending. Not a prince. Better."]),

    cpu("Rapi", "neutral", quests=RAPI_QUESTS, extra_scenes=RAPI_SCENES,
        haunts=[("arena", "wk", "12", 55), ("rooftop", "we", "23", 40), ("beach", "135", "1", 30)],
        tastes=(["cool"], ["drink", "calm"], ["cute"]),
        lines={
            "mid": {"1": ["them: Your posture is improving. Acceptable.", "them: Do you enjoy drills? I can tell you're not sure.", "them: Keep your guard up. Always.", "them: Hm. You didn't complain once. That's a start.", "them: Ask me a question about the squad. One."], "3": ["them (pleased): You're a decent soldier. Better than I expected.", "them: The red scarf keeps coming back to me. You make it clearer.", "them (pleased): Meet at the arena. We'll run the new drill together.", "them: I think I trust you now. That's a rare thing for me.", "them (pleased): You remind me of the commander I can't name. Strong, and kind."], "5": ["them (pleased): {player}, my best soldier. The squad's best, and my best friend.", "them: I'd take any orders from you, as long as they keep you safe.", "them (pleased): Let's walk the rooftop at night. The stars are clearer that way.", "them: I'll remember you, even if I forget everything else.", "them (pleased): Best friend. Stay alive. That's my last order for today."]},
            "hello_steps": [["them: Identify yourself.", "them: Hm. Stand straight."], ["them: Good afternoon. Are you here to train?", "them: Hello. Is that a new uniform?"], ["them: {player}. Good to see you.", "them: {player}. Did you run laps today?"], ["them (pleased): {player}. Good to see you. Squad's ready.", "them (pleased): {player}. You're on time. Good."], ["them (pleased): {player}. The squad's all here now. You're part of it.", "them (pleased): {player}. Sit, and tell me about the drill."], ["them (pleased): {player}. My best soldier, and my friend.", "them (pleased): {player}. Come here. I've got a plan for the day."]],
            "bye_steps": [["them: Stay alert.", "them: Dismissed. Don't slack off."], ["them: Watch your back out there.", "them: Go. Be ready tomorrow."], ["them: Watch your back, {player}.", "them: Dismissed, {player}. Be ready tomorrow."], ["them (pleased): Come back safe, {player}. That's an order, from me.", "them (pleased): Go, {player}. The squad will wait."], ["them (pleased): Come back safe. The squad will need you, {player}.", "them (pleased): Bye, {player}. Keep your head up."], ["them (pleased): Come back safe, best soldier. Squad's better with you.", "them (pleased): Bye, {player}. Remember the red scarf."]],
            "hello": ["them: Identify yourself.", "them: {player}. Good to see you.", "them (pleased): {player}. Squad's all here now."],
            "bye": ["them: Stay alert.", "them: Watch your back out there.", "them (pleased): Come back safe. That's an order, from me."],
            "hi": ["them: Counters squad, Rapi. Target acquired. Let's get this done.",
                   "them: Commander? No. Civilian. Fine. State your business."],
            "hi2": "them: {player}. You're on schedule. Good.",
            "hi4": "them (pleased): You're squad now. I watch your back.",
            "again": "them: Back again. Understood.",
            "loved": "them (pleased): Good gear. I'll use it in the field.",
            "disliked": "them (dismayed): ...Cute. Neon would like it.",
            "before": "them: Engaging.",
            "won": "them: Good work. Debrief later.",
            "lost": "them: Mission complete.",
            "r1": "them: You're reliable. I value that.",
            "r3": "them: Nikkes are weapons. We're not supposed to have friends. I've stopped caring what we're supposed to do.",
            "r4": "them (pleased): If the Raptures come, stand behind me. I mean it.",
        },
        friend=["background ruins", "me enters right with fade", "me: Perimeter's clear. You can relax.",
                "player: Do you ever relax?", "me (dismayed): ...Not often.",
                "me: Anis says I'm too serious. Neon says I need friends.", "me (pleased): They're right. You'll do."],
        best=["background night", "me enters center with fade", "me: My memories have been wiped before. People I cared about, gone.",
              "me: I stopped getting attached. It was safer.", "player: Is it working?",
              "me (dismayed): Not with you.", "player: Good.",
              "choice", "- I'll remember for both of us.", "- Best friends, Rapi.",
              "me (pleased): Best friend. Logged in my core. They can't wipe this one."]),

    cpu("Darkness", "friendly", quests=DARKNESS_QUESTS, extra_scenes=DARKNESS_SCENES,
        haunts=[("arena", "wk", "12", 55), ("plaza", "we", "12", 45), ("forest", "135", "2", 30)],
        tastes=(["sporty"], ["spicy", "fancy"], ["cute"]),
        lines={
            "mid": {"1": ["them (pleased): Oh! You're a challenger! Or are you a friend? Both are good!", "them: Hit me again! ...Ahem. Please.", "them: Your strength is impressive! I'm already a little jealous.", "them: You have a kind face. I'd like to protect it.", "them: Ask me anything about my lord, and I'll answer with pride!"], "3": ["them (pleased): You're a loyal companion, and a wonderful sparring partner!", "them: My father expects too much. You make me feel like I can choose.", "them (pleased): Let's go to the arena. I'd love another round, please!", "them: You're the only one who doesn't mind my strange tastes. Thank you!", "them (pleased): You make the waiting feel like a good kind of torment."], "5": ["them (pleased): {player}, my dearest friend! My shield, my sword, my everything!", "them: I'd take any hit for you, and I'd enjoy it, honestly.", "them (pleased): Let's go to the plaza at evening. I'll tell you about my home.", "them: You're the one I'd want at my side, always, even if I refuse the match.", "them (pleased): Best friend! Stay with me, and I'll protect you forever!"]},
            "hello_steps": [["them: Greetings, traveller. Have you come to challenge me?", "them: Hello. Would you like to test your strength?"], ["them: Ah, a visitor! Shall we spar?", "them: Hi, traveller. Hit me when you're ready!"], ["them (pleased): {player}! Have you come to put me through a trial?!", "them (pleased): {player}! Hit me, please!"], ["them (pleased): {player}! Good, you came back for more!", "them (pleased): {player}! Did you bring a shield for me?"], ["them (pleased): {player}! My dearest companion! Use me as your shield!", "them (pleased): {player}! Sit, I'll tell you about my lord."], ["them (pleased): {player}! My best friend and my favourite punching bag!", "them (pleased): {player}! Come here! I missed you!"]],
            "bye_steps": [["them: Farewell, traveller.", "them: Goodbye. Stay strong."], ["them: Go! Be brave.", "them: Farewell. Protect your friends."], ["them (pleased): Go! I shall endure your absence, {player}!", "them (pleased): Bye, {player}! Keep practising!"], ["them (pleased): Go, {player}! The waiting is torment, but it's good torment!", "them (pleased): Bye, {player}! Come back soon for another hit!"], ["them (pleased): Come back soon! The waiting is torment! Wonderful torment!", "them (pleased): Bye, {player}! I'll be ready for you."], ["them (pleased): Come back soon, best friend! Be ready to be hit!", "them (pleased): Bye, {player}! Protect the others. Protect yourself, too."]],
            "hello": ["them: Greetings, traveller. Have you come to... challenge me?", "them (pleased): {player}! Have you come to put me through a trial?!", "them (pleased): {player}! My dearest companion! Use me as your shield!"],
            "bye": ["them: Farewell, traveller.", "them (pleased): Go! I shall endure your absence! It's... rather nice!", "them (pleased): Come back soon! The waiting is torment! Wonderful torment!"],
            "hi": ["them: I am Darkness, a Crusader! Strike me with everything you have! Please!",
                   "them: You look strong. I-I mean, I'll protect you! Or... you could attack me. Either way!"],
            "hi2": "them (pleased): {player}! I need a sparring partner. Hit me as hard as you can!",
            "hi4": "them (pleased): You're my closest companion. I'd take any blow for you. Gladly. Very gladly.",
            "again": "them: Back again? Are you here to... punish me?",
            "loved": "them (pleased): Heavy weights! Oh, these will be so painful! Thank you!",
            "disliked": "them (dismayed): A plushie. Soft. Gentle. ...Disappointing.",
            "before": "them: Do your worst! I mean that!",
            "won": "them (pleased): Ahh, defeat! It feels... wonderful!",
            "lost": "them (pleased): I endured everything! Victory!",
            "r1": "them: You're honest. I like that in a party member.",
            "r3": "them: I'm actually a noble's daughter. Lalatina. Don't call me that. ...Unless you want to.",
            "r4": "them (pleased): I'd stand in front of any attack for you. Not because I like it. Well. Not only because.",
        },
        friend=["background forest", "me enters left with slide", "me: Kazuma refuses to spar with me. Will you?",
                "player: I don't want to hurt you.", "me (pleased): That's the point!",
                "me: Fine. Then just... walk with me. As friends.", "me: That's nice too. Surprisingly."],
        best=["background castle", "me enters center with fade", "me: My father wanted me to marry well. Be a proper lady.",
              "me: I became a crusader instead. To protect people.",
              "player: You're good at it.", "me (dismayed): I can never hit anything, though.",
              "player: You protect everyone. That's what matters.",
              "choice", "- Best friends, Darkness.", "- Best friends, Lalatina.",
              "me (pleased): Best friend! I'll be your shield forever. And maybe you could hit me just once."]),

    cpu("Megumin", "friendly", quests=MEGUMIN_QUESTS, extra_scenes=MEGUMIN_SCENES,
        haunts=[("plaza", "wk", "12", 55), ("forest", "we", "12", 45), ("beach", "135", "2", 30)],
        tastes=(["spicy"], ["cool", "food"], ["calm"]),
        lines={
            "mid": {"1": ["them (pleased): You don't run from explosions. You're my kind of person!", "them: Hm. Do you have a favourite spell? Mine's the best one.", "them: I need someone to carry my things. Are you free?", "them: Watch my next blast. Tell me the truth afterwards.", "them: You look like someone who'd appreciate a good crater."], "3": ["them (pleased): You're my explosion buddy now, aren't you? I'm so pleased!", "them: My sister taught me this spell. You make me want to keep using it.", "them (pleased): Let's walk to the forest. I'll cast a little one for you.", "them: You're the only one who doesn't tell me to stop blowing things up.", "them (pleased): You carry me home so well. I'm grateful, really."], "5": ["them (pleased): {player}, my best friend! My explosion partner forever!", "them: I'd cast the biggest explosion ever, for you, on any battlefield.", "them (pleased): Let's go to the beach and watch the sunset. Then I'll blow up the rocks.", "them: You're the one who always believes my explosions are worth it.", "them (pleased): Best friend! Let's make the next explosion the best ever!"]},
            "hello_steps": [["them: Behold! ...Oh. Just a passer-by.", "them: Hello. Stand back, I'm casting."], ["them: Hi! Are you here to watch me explode something?", "them: Oh, hi. Don't mind the smoke."], ["them (pleased): {player}! Shall we go find something to blow up?", "them (pleased): {player}! Did you watch my last explosion?"], ["them (pleased): {player}! Oh, you came! Want to see my new spell?", "them (pleased): {player}! Help me carry my things, please."], ["them (pleased): {player}! My explosion partner! Today's the day, I can feel it!", "them (pleased): {player}! Come on, let's blow up the forest!"], ["them (pleased): {player}! My best friend and my favourite carrier!", "them (pleased): {player}! Hello! My legs are tired already. Carry me?"]],
            "bye_steps": [["them: Farewell!", "them: Bye! Watch the smoke."], ["them: Go! May your path be full of explosions!", "them: Farewell! Don't stand too close to the crater."], ["them (pleased): Go! May your path be full of explosions, {player}!", "them (pleased): Bye, {player}! Keep your eyes open for a blast!"], ["them (pleased): Go on, {player}! I'll cast another one tomorrow.", "them (pleased): Bye, {player}! Carry my regards to the forest."], ["them (pleased): Come back soon! I'll need someone to carry me home, {player}!", "them (pleased): Bye, {player}! Don't leave me in the crater!"], ["them (pleased): Come back soon, best friend! The explosions are better with you.", "them (pleased): Bye, {player}! I'll save the biggest blast for you."]],
            "hello": ["them: Behold! ...Oh. Just a passer-by.", "them (pleased): {player}! Shall we go find something to blow up?", "them (pleased): My explosion partner! Today's the day. I can feel it!"],
            "bye": ["them: Farewell!", "them (pleased): Go! May your path be full of explosions!", "them (pleased): Come back soon! I'll need someone to carry me home!"],
            "hi": ["them: My name is Megumin! The number-one mage of Axel, and foremost user of Explosion magic!",
                   "them: You! Do you appreciate the beauty of a perfect explosion?"],
            "hi2": "them (pleased): {player}! I'm going to cast my daily explosion. You must come score it!",
            "hi4": "them (pleased): My explosion partner! Carry me home after, okay? I'll be out of mana.",
            "again": "them: Back again? Excellent! A worthy audience!",
            "loved": "them (pleased): Fire! Spice! Pure destructive energy! I love it!",
            "disliked": "them (dismayed): Calming tea? Calm is the enemy of explosion!",
            "before": "them: EXPLOSION!!",
            "won": "them (dismayed): My explosion... wasn't enough? Impossible!",
            "lost": "them (pleased): Behold! The power of Explosion!",
            "r1": "them: You didn't flinch at my explosion. You have potential.",
            "r3": "them: People call me useless. One spell a day. But I chose it because I love it. You never laughed.",
            "r4": "them (pleased): I'd only fall over after an explosion if you were there to catch me.",
        },
        friend=["background ruins", "me enters left with slide", "me: Watch closely! EXPLOSION!", "screen flash", "screen shake",
                "me (dismayed): ...I can't move. Carry me, please.", "player: Every day, huh?",
                "me (pleased): Every day! And now you're my official explosion scorer. That means friend."],
        best=["background dusk", "me enters center with fade", "me: My family is poor. My sister and I didn't always eat.",
              "me: Explosion magic was the most beautiful thing I'd ever seen. It gave me something to dream about.",
              "player: You're amazing, Megumin.", "me (dismayed): ...Even with only one spell?",
              "player: Especially with one spell.",
              "choice", "- Best friends, Megumin.", "- I'll carry you home every time.",
              "me (pleased): Best friend! I'll name an explosion after you! The {player} Blast!"]),

    cpu("Erza Scarlet", "friendly", quests=ERZA_SCARLET_QUESTS, extra_scenes=ERZA_SCARLET_SCENES,
        haunts=[("arena", "wk", "12", 55), ("cafe", "we", "12", 45), ("plaza", "135", "0", 30)],
        tastes=(["sweet"], ["sporty", "fancy"], ["spicy"]),
        lines={
            "mid": {"1": ["them: You're not bad company. I've met worse.", "them: Hm. Do you have a favourite armour? I'll show you mine.", "them: Let's share a slice of cake. Discipline first, then sweets.", "them: You're a good fighter. I can tell from how you stand.", "them: Ask me one question. I'll answer, with dignity."], "3": ["them (pleased): You've been a good comrade. I'm glad to have you.", "them: The guild taught me what friendship is. You're part of that now.", "them (pleased): Meet me at the cafe. I'll share my best cake.", "them: You're the one I'd requip for, if I ever needed to protect you.", "them (pleased): You understand the strength of a friendship. Thank you."], "5": ["them (pleased): {player}, my comrade and my best friend. My tower is open to you.", "them: I'd stand against any enemy for you, in any armour.", "them (pleased): Let's walk the plaza at evening. I'll tell you the rest of my story.", "them: You're the one who makes me feel like a person, not a warrior.", "them (pleased): Best friend! Come join me for a feast. You earned it."]},
            "hello_steps": [["them: Hm. State your name.", "them: Hello. Please, don't touch my armour."], ["them: Hello. Are you here to train?", "them: Ah. Good afternoon. Mind the cake."], ["them (pleased): {player}. Good. Have you been training?", "them (pleased): {player}. Welcome back. Cake?"], ["them (pleased): {player}. Good to see you. Sit, I'll share my cake.", "them (pleased): {player}. Did you bring any strawberries?"], ["them (pleased): {player}! My comrade. Join me, I've just bought cake.", "them (pleased): {player}! Come, let's requip into something comfortable."], ["them (pleased): {player}! My best comrade and my favourite cake partner!", "them (pleased): {player}! You're part of my tower now. Come in!"]],
            "bye_steps": [["them: Farewell.", "them: Goodbye. Stay sharp."], ["them: Take care. Train hard.", "them: Goodbye. Guard the cake."], ["them (pleased): Train hard while I'm gone, {player}.", "them (pleased): Bye, {player}. Save me a slice."], ["them (pleased): Go on, {player}. Come back to the cafe soon.", "them (pleased): Bye, {player}. I'll keep the best armour ready."], ["them (pleased): Come back soon. That's an order, comrade {player}.", "them (pleased): Bye, {player}. Come back, the cake will be waiting."], ["them (pleased): Come back soon, best comrade. The tower's always open to you.", "them (pleased): Go, {player}. Come back. I'll requip for you."]],
            "hello": ["them: Hm. State your name.", "them (pleased): {player}. Good. Have you been training?", "them (pleased): {player}! My comrade. Join me, I've just bought cake."],
            "bye": ["them: Farewell.", "them (pleased): Train hard while I'm gone.", "them (pleased): Come back soon. That's an order, comrade."],
            "hi": ["them: I am Erza Scarlet, Titania, Queen of the Fairies! Prepare yourself!",
                   "them: You. Are you a member of a guild? You stand like a fighter."],
            "hi2": "them (pleased): {player}. Good. I've been looking for a worthy sparring partner.",
            "hi4": "them (pleased): You're my comrade. I'd face any foe at your side.",
            "again": "them: Back again? Your dedication is admirable.",
            "loved": "them (pleased): Strawberry cake?! This... this is the finest gift. Thank you!",
            "disliked": "them (dismayed): Spicy. Hm. Natsu would enjoy this. Give it to him.",
            "before": "them: Requip! Let's begin.",
            "won": "them (pleased): Excellent. You've earned my respect.",
            "lost": "them: Keep training. You'll get there.",
            "r1": "them: You have a strong heart. Fairy Tail would welcome you.",
            "r3": "them: I was a child slave in the Tower of Heaven. My friends there... I carry them with me. You're one of them now.",
            "r4": "them (pleased): Anyone who harms you will answer to me. And my armour.",
        },
        friend=["background cafe", "me enters right with slide", "me: I'll share my cake with you. This is a great honour.",
                "player: You never share your cake.", "me (pleased): Exactly.",
                "me: In Fairy Tail, friends are family. We protect each other.", "me: You're family now."],
        best=["background night", "me enters center with fade", "me: Do you know where my name came from? Scarlet. Like my hair.",
              "me: Jellal gave it to me. When I had nothing.", "player: You've built everything since.",
              "me (dismayed): I always wear armour. Even inside.", "player: You don't have to with me.",
              "choice", "- Best friends, Erza.", "- No armour needed.",
              "me (pleased): Best friend. ...I'll requip into something comfortable. For you."]),

    cpu("Gray Fullbuster", "friendly", quests=GRAY_FULLBUSTER_QUESTS, extra_scenes=GRAY_FULLBUSTER_SCENES,
        haunts=[("arena", "wk", "12", 55), ("beach", "we", "12", 45), ("plaza", "135", "2", 30)],
        tastes=(["cool"], ["sporty", "drink"], ["spicy"]),
        lines={
            "mid": {"1": ["them: You're alright. Want to see me make something out of ice?", "them: Hey, do you like cold weather? I love it.", "them: My shirt's gone again. Don't look.", "them: You're easy to talk to. Good.", "them: Want to hear a story about my teacher? Maybe later."], "3": ["them (pleased): You're a great friend. Thanks for helping me find my shirt.", "them: I still miss Ur. You make it hurt a little less.", "them (pleased): Let's make an ice sculpture together. You'll love it.", "them: You understand what sacrifice means. Not many people do.", "them (pleased): You're one of the few people I can be honest with."], "5": ["them (pleased): {player}, my best friend. Ice or not, you're always warm to me.", "them: I'd freeze the whole world for you, if you asked nicely.", "them (pleased): Let's go to the beach and build the biggest sculpture ever.", "them: You're the friend Ur would have wanted me to find.", "them (pleased): Best friend! Let's make something beautiful together, forever."]},
            "hello_steps": [["them: Hey. Need something?", "them: Oh, hi. Watch your step, it's icy."], ["them: Hey. You're new here?", "them: Hi. Don't mind the snow."], ["them (pleased): Yo, {player}. What's up?", "them (pleased): Hi, {player}! Did you see my ice sculpture?"], ["them (pleased): Hey, {player}. Good timing. Natsu's driving me nuts.", "them (pleased): {player}! Come here, I'll make you an ice sculpture."], ["them (pleased): {player}. Good to see you. Sit, I've got something to show you.", "them (pleased): {player}! Did you bring a shirt? Mine's gone again."], ["them (pleased): {player}! My best friend. Let's go get some snow, just us.", "them (pleased): {player}! You're my favourite person to make things for."]],
            "bye_steps": [["them: Later.", "them: See ya. Watch the ice."], ["them: Bye. Keep warm.", "them: Later. Don't slip."], ["them (pleased): See ya. Stay cool, {player}.", "them (pleased): Bye, {player}. Don't go catching cold."], ["them (pleased): Go on, {player}. Come back soon.", "them (pleased): Bye, {player}! Check if you're still wearing your shirt."], ["them (pleased): Come back soon. ...And where'd my shirt go, {player}?", "them (pleased): Bye, {player}. Stay warm out there."], ["them (pleased): Come back soon, best friend. Ice isn't as fun without you.", "them (pleased): Bye, {player}! I'll make you something good next time."]],
            "hello": ["them: Hey. Need something?", "them (pleased): Yo, {player}. What's up?", "them (pleased): Hey, {player}. Good timing. Natsu's driving me nuts."],
            "bye": ["them: Later.", "them (pleased): See ya. Stay cool.", "them (pleased): Come back soon. ...And where'd my shirt go?"],
            "hi": ["them: You wanna fight? Fine. I'll freeze you solid before you can blink.",
                   "them: Yo. Gray Fullbuster. Ice Make mage. And... where did my shirt go?"],
            "hi2": "them (pleased): Hey {player}. You seen my shirt? No? Whatever. Wanna duel?",
            "hi4": "them (pleased): You're a real friend. Don't tell Natsu I said friend. He'll get weird.",
            "again": "them: Back? Cool.",
            "loved": "them (pleased): This is cool. Literally and figuratively.",
            "disliked": "them (dismayed): Spicy? Natsu's thing, not mine.",
            "before": "them: Ice Make: Lance!",
            "won": "them (dismayed): Tch. You're good. Rematch.",
            "lost": "them (pleased): Cooled off yet?",
            "r1": "them: You're not annoying. Unlike some fire idiots.",
            "r3": "them: My teacher Ur gave her life to save me. I try to live up to it. You make it easier.",
            "r4": "them (pleased): You're nakama. That means I'd fight anyone for you.",
        },
        friend=["background snow", "me enters left with slide", "me: Check this out. Ice Make: Rose.",
                "narrator: A perfect ice rose forms in his hand.", "me: For you. Don't make it a thing.",
                "player: It's beautiful, Gray.", "me (pleased): Yeah, yeah. We're friends. Keep it cold."],
        best=["background snow", "me enters center with fade", "me: Ur turned herself into ice to seal a demon. To save me.",
              "me: I used to think I didn't deserve it.", "player: You do, Gray.",
              "me (dismayed): ...You and Juvia keep telling me that.",
              "choice", "- Best friends, Gray.", "- Live for her, and for you.",
              "me (pleased): Best friend. Heh. Ur would've liked you."]),
]
