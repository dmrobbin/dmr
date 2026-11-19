"""World mode cast: Chainsaw Man, Attack on Titan and Kill la Kill."""

# Quests: Denji and Power. No endings lock anything here.
DENJI_QUESTS = [
    {"key": "denji-first-date", "title": "A Date, Maybe", "gates": 2,
     "about": "Denji wants a date, and he needs a little help with the basics.",
     "offer": ["them: Hey, {player}! I'm gonna get a date. A real one, with a girl!",
               "them (dismayed): Power says I'm hopeless. Maybe she's right.",
               "them (pleased): You're the expert, right? Teach me something!"],
     "stages": [
         {"text": "Bring Denji a snack for courage", "objectives": [{"do": "give_gift", "gift": "melon-bread", "to": "Denji"}]},
         {"text": "Win a duel with Devil Hunter, Denji in your deck, against Power", "objectives": [{"do": "win_with", "card": "CSM/S96-TE13", "against": ["Power"]}]},
         {"text": "Tell Denji how it went", "objectives": [{"do": "talk", "to": "Denji", "script": ["them (pleased): Okay, I'm ready! You're coming with me, right?", "player: I'll be there."]}]},
     ],
     "endings": [{"key": "date", "title": "Help him get ready", "about": "Denji heads off on his date, grinning. He has no idea what he's doing.",
                  "rewards": [{"coins": 300}, {"gift": "bouquet"}]}]},
    {"key": "denji-contract", "title": "The Contract", "gates": 5,
     "about": "Denji is tangled up in a devil's contract, and the price is coming due. He wants a friend with him when it does.",
     "offer": ["them: I've got a contract with a devil. Don't ask. It's complicated.",
               "them (dismayed): I just don't want to be alone when it's time to pay up."],
     "stages": [
         {"text": "Beat Power in a duel", "objectives": [{"do": "defeat", "cpus": ["Power"]}]},
         {"text": "Play Devil Hunter Feared by Devils with Blood-Soaked Declaration of War", "objectives": [{"do": "combo", "card": "CSM/S96-E003", "climax": "CSM/S96-E025", "count": 2}]},
         {"text": "Talk Denji through it", "objectives": [{"do": "talk", "to": "Denji", "script": ["them: Thanks for hanging out. Seriously.", "them (pleased): You're not so bad, you know."]}]},
     ],
     "endings": [{"key": "sealed", "title": "Stand by him", "about": "The contract is still there, but Denji has a friend standing with him now.",
                  "rewards": [{"coins": 1000}, {"pack": "lucky_pack"}, {"card": "CSM/S96-E003", "copies": 2}]}]},
]

POWER_QUESTS = [
    {"key": "power-battle-of-wits", "title": "Battle of Wits", "gates": 2,
     "about": "Power insists nobody is smarter than her, and she won't waste time on anyone who can't prove otherwise.",
     "offer": ["them: GROVEL, HUMAN! ...Hm. Wait. You're the one who keeps coming back, aren't you?",
               "them (pleased): Prove you're worth my time. Show me you have a card worthy of the great Power."],
     "stages": [
         {"text": "Beat Denji in a duel", "objectives": [{"do": "defeat", "cpus": ["Denji"]}]},
         {"text": "Have Blood Fiend, Power", "objectives": [{"do": "have_card", "card": "CSM/S96-E001"}]},
         {"text": "Report to Power", "objectives": [{"do": "talk", "to": "Power", "script": ["them (pleased): Hah! Your brain isn't totally useless.", "them: Don't get used to it, human."]}]},
     ],
     "endings": [{"key": "respect", "title": "Earn her grudging respect", "about": "Power admits, in her own way, that you're clever. She'll never say it twice.",
                  "rewards": [{"coins": 300}, {"gift": "energy-drink"}]}]},
    {"key": "power-fiend-life", "title": "A Fiend's Everyday Life", "gates": 5,
     "about": "Power's life as a blood fiend is harder than she lets on. She'll only tell someone she trusts.",
     "offer": ["them (dismayed): ...Don't look at me like that. I have a life, too.",
               "them: I'll show you. But not in front of the others."],
     "stages": [
         {"text": "Play Battle of Wits, Power with Fiend's Everyday Life", "objectives": [{"do": "combo", "card": "CSM/S96-E016", "climax": "CSM/S96-E026", "win": True}]},
         {"text": "Win a Yellow deck duel against Denji", "objectives": [{"do": "win_deck", "colors": ["Yellow"], "against": ["Denji"]}]},
         {"text": "Listen to Power", "objectives": [{"do": "talk", "to": "Power", "script": ["them (dismayed): I used to be lonely, you know. Before I met the Devil Hunter.", "them (pleased): Thanks for listening. Don't tell anyone."]}]},
     ],
     "endings": [{"key": "told", "title": "Keep her secret", "about": "Power trusts you with it. She's still Power, but she's less alone now.",
                  "rewards": [{"coins": 1000}, {"pack": "color_pack"}, {"card": "CSM/S96-E001", "copies": 2}]}]},
]

AKI_HAYAKAWA_QUESTS = [
  {
    "key": "aki-smoke-break",
    "title": "Smoke Break",
    "gates": 2,
    "about": "Aki needs someone who won't talk while he thinks, and he's hard to find for it.",
    "offer": [
      "them: I come up here to think. Don't say anything, okay?",
      "them (pleased): You didn't talk. That's already better than most."
    ],
    "stages": [
      {
        "text": "Find Aki on the rooftop in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              2
            ],
            "scene": "World: Aki Hayakawa, Rooftop",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Watchdog of Special Division 4, Aki Hayakawa",
        "objectives": [
          {
            "do": "have_card",
            "card": "CSM/S96-E080"
          }
        ]
      },
      {
        "text": "Let Aki say what's on his mind",
        "objectives": [
          {
            "do": "talk",
            "to": "Aki Hayakawa",
            "script": [
              "them: The Fox Devil's price is steep. I'm paying it gladly.",
              "them (pleased): Thanks for not asking how much."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "quiet-company",
        "title": "Keep the quiet company",
        "about": "Aki stops lighting cigarettes he doesn't smoke, and waits for you to sit down first.",
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
    "key": "aki-the-gun-devil",
    "title": "The Gun Devil",
    "gates": 5,
    "about": "Aki's own revenge on the Gun Devil, or the one Makima plans for him.",
    "offer": [
      "them (dismayed): Makima has a plan for the Gun Devil. It isn't mine.",
      "them: Come up tonight. I want to tell you before I decide."
    ],
    "stages": [
      {
        "text": "Meet Aki on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Aki Hayakawa, Rooftop (night)",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Beat Makima in a duel",
        "objectives": [
          {
            "do": "defeat",
            "cpus": [
              "Makima"
            ]
          }
        ]
      },
      {
        "text": "Give Aki your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Aki Hayakawa",
            "script": [
              "them: Her plan or mine. Which one would you back?",
              "them (pleased): Mine, then. Thanks for backing me."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "his-own-way",
        "title": "His own way",
        "about": "Aki goes after the Gun Devil his way. Makima's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "makima-control"
        ]
      },
      {
        "key": "hold-back",
        "title": "Hold back for now",
        "about": "Aki keeps his revenge to himself, and waits for a better time.",
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
AKI_HAYAKAWA_SCENES = [
  {
    "name": "World: Aki Hayakawa, Rooftop",
    "lines": [
      "background rooftop",
      "me enters center with fade",
      "me: Want one? No? Good. I'm just holding it.",
      "player: Why hold it if you don't smoke it?",
      "me (dismayed): It gives my hands something to do while I think.",
      "me: The Fox Devil took my future. I'm paying the price gladly.",
      "player: Is it worth it?",
      "me (pleased): Yeah. For the people I can still keep safe."
    ]
  },
  {
    "name": "World: Aki Hayakawa, Rooftop (night)",
    "lines": [
      "background night",
      "me enters left with rise",
      "me: Makima has a plan for the Gun Devil. I'm not sure I like it.",
      "player: Why not?",
      "me (dismayed): Because it isn't mine. It's hers, and she's been wrong before.",
      "me: Would you help me do it my way? Not her way. Mine."
    ]
  }
]
MAKIMA_QUESTS = [
  {
    "key": "makima-a-good-dog",
    "title": "A Good Dog",
    "gates": 2,
    "about": "Makima tests whether the player follows instructions, and orders for them without asking.",
    "offer": [
      "them: You'll follow me, won't you? Sit. There, that's better.",
      "them (pleased): Good. You're easy to read. I like that."
    ],
    "stages": [
      {
        "text": "Meet Makima at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Makima, Cafe",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Give Makima a bouquet",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "bouquet",
            "to": "Makima"
          }
        ]
      },
      {
        "text": "Accept what Makima orders",
        "objectives": [
          {
            "do": "talk",
            "to": "Makima",
            "script": [
              "them: I ordered for you. You'll like it, and you'll eat it all.",
              "them (pleased): Yes. Just like that."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "good-dog",
        "title": "Be a good dog",
        "about": "Makima pats your head at the cafe door. You aren't sure whether it's a reward.",
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
    "key": "makima-control",
    "title": "Control",
    "gates": 5,
    "about": "Makima offers the player a place in her better world, a world without pain, run by her.",
    "offer": [
      "them: A world without pain. Run by me. Would you want that?",
      "them (pleased): Think about it. I'll explain at the shrine."
    ],
    "stages": [
      {
        "text": "Meet Makima at the shrine at night",
        "objectives": [
          {
            "do": "visit",
            "place": "shrine",
            "times": [
              3
            ],
            "scene": "World: Makima, Shrine",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Makima: Devil Hunter in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "CSM/S96-E058",
            "against": [
              "Makima"
            ]
          }
        ]
      },
      {
        "text": "Give Makima your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Makima",
            "script": [
              "them: Persuade Aki to let me handle the Gun Devil. Can you do that?",
              "them (pleased): Good. I knew you'd be useful."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "trust-her",
        "title": "Trust her",
        "about": "Makima takes charge of the Gun Devil. Aki's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "aki-the-gun-devil"
        ]
      },
      {
        "key": "refuse-her",
        "title": "Refuse her",
        "about": "Makima shrugs and finds someone else to order around.",
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
MAKIMA_SCENES = [
  {
    "name": "World: Makima, Cafe",
    "lines": [
      "background cafe",
      "me enters center with fade",
      "me: Sit. I already ordered, you'll like it.",
      "player: How did you know what I like?",
      "me (pleased): I like people who are easy to read. You're very easy.",
      "me: Eat. It's a good plate. Don't make me say it twice."
    ]
  },
  {
    "name": "World: Makima, Shrine",
    "lines": [
      "background shrine",
      "me enters center with rise",
      "me: Imagine a world with no pain. Nobody screaming. Nobody losing.",
      "player: That sounds like a dream.",
      "me (dismayed): It's a plan. One I'm close to finishing.",
      "me: Ask Aki to let me handle the Gun Devil. He'll listen to you."
    ]
  }
]
BEAST_TITAN_QUESTS = [
  {
    "key": "beast-titan-throwing-practice",
    "title": "Throwing Practice",
    "gates": 2,
    "about": "Zeke wants someone to play catch with, and he apologises every time he throws too hard.",
    "offer": [
      "them: Want to play catch? I'll go easy. Mostly.",
      "them (pleased): You're doing better than my last partner. He's a titan, so, that's a bit of a joke."
    ],
    "stages": [
      {
        "text": "Play catch with Zeke at the arena at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              1
            ],
            "scene": "World: Beast Titan, Arena",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Give Zeke a handheld game to play between throws",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "handheld",
            "to": "Beast Titan"
          }
        ]
      },
      {
        "text": "Talk about Tom Ksaver with Zeke",
        "objectives": [
          {
            "do": "talk",
            "to": "Beast Titan",
            "script": [
              "them: Tom Ksaver was the only good afternoon I had. Thank you for asking.",
              "them (pleased): You're easy to throw with. Sorry, to talk to. Easy to talk to."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "catch-again",
        "title": "Catch again tomorrow",
        "about": "Zeke leaves a baseball on your doorstep with a polite note.",
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
    "key": "beast-titan-euthanasia-plan",
    "title": "The Euthanasia Plan",
    "gates": 5,
    "about": "Zeke's calm plan to end Eldia's suffering, explained gently, like a doctor would.",
    "offer": [
      "them: I have a plan to end the suffering on this island. It's very gentle.",
      "them (pleased): Walk with me in the forest. You'll understand."
    ],
    "stages": [
      {
        "text": "Walk with Zeke in the forest at night",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              3
            ],
            "scene": "World: Beast Titan, Forest",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Beat Levi in a duel",
        "objectives": [
          {
            "do": "defeat",
            "cpus": [
              "Levi"
            ]
          }
        ]
      },
      {
        "text": "Answer Zeke's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Beast Titan",
            "script": [
              "them: Can kindness be cruel? I'd like your honest answer.",
              "them (pleased): ...Thank you. That's a good answer."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "gentle-plan",
        "title": "Hear the gentle plan out",
        "about": "Zeke tells you the rest of his plan, and asks you to keep it a secret.",
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
BEAST_TITAN_SCENES = [
  {
    "name": "World: Beast Titan, Arena",
    "lines": [
      "background arena",
      "me enters left with slide",
      "me: Catch! Sorry. That was too hard. Here, a softer one.",
      "player: That one was perfect.",
      "me (pleased): Thanks. People usually run away when I throw.",
      "me: Tom Ksaver used to play catch with me. Those were good afternoons."
    ]
  },
  {
    "name": "World: Beast Titan, Forest",
    "lines": [
      "background forest",
      "me enters center with fade",
      "me: The forest is quiet at night. Perfect for a plan like mine.",
      "player: What is your plan?",
      "me (dismayed): To end the suffering. Gently. Like a doctor would.",
      "me: Do you think kindness can be cruel? I'm not sure any more."
    ]
  }
]
EREN_QUESTS = [
  {
    "key": "eren-beyond-the-walls",
    "title": "Beyond the Walls",
    "gates": 2,
    "about": "Eren wants to see the sea with someone, and to know what's on the other side.",
    "offer": [
      "them: I want to see the sea. Will you come with me?",
      "them (pleased): Good. Don't be late. I hate being late."
    ],
    "stages": [
      {
        "text": "Watch the sea with Eren at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Eren, Beach",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Eren: Eren: Conversation at Sunset in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "AOT/SX04-012",
            "against": [
              "Eren"
            ]
          }
        ]
      },
      {
        "text": "Answer Eren's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Eren",
            "script": [
              "them: What's on the other side? Do you think it's different?",
              "them (pleased): ...Yeah. I think so too."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "what-is-beyond",
        "title": "Wonder what's beyond",
        "about": "Eren keeps staring at the horizon, and says the sea is nothing like he imagined.",
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
    "key": "eren-keep-moving-forward",
    "title": "Keep Moving Forward",
    "gates": 5,
    "about": "Eren has seen the future, and he's going to go through with it. He won't explain why.",
    "offer": [
      "them: I can't stop. I've decided. I won't explain why.",
      "them (dismayed): Just don't let Mikasa follow me. Please."
    ],
    "stages": [
      {
        "text": "Meet Eren at the beach at night",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              3
            ],
            "scene": "World: Eren, Beach (night)",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Eren Titan: Declaration of War",
        "objectives": [
          {
            "do": "have_card",
            "card": "AOT/SX04-003"
          }
        ]
      },
      {
        "text": "Give Eren your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Eren",
            "script": [
              "them: Will you keep Mikasa away from me, whatever happens?",
              "them (pleased): ...Thanks. That's all I wanted."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "keep-moving-forward",
        "title": "Keep moving forward",
        "about": "Eren goes on alone. Mikasa's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "mikasa-see-you-later"
        ]
      },
      {
        "key": "hold-on",
        "title": "Hold on a little longer",
        "about": "Eren hesitates, and promises to think about it.",
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
EREN_SCENES = [
  {
    "name": "World: Eren, Beach",
    "lines": [
      "background dusk",
      "me enters left with rise",
      "me: This is the sea. This is really it.",
      "player: How does it feel?",
      "me (dismayed): Like nothing I expected. Smaller. Bigger. I don't know.",
      "me: What's on the other side? You can't see it from here, can you?",
      "player: No. You can't."
    ]
  },
  {
    "name": "World: Eren, Beach (night)",
    "lines": [
      "background night",
      "me enters center with fade",
      "me: I can't stop. I've seen what happens if I do.",
      "player: What happens?",
      "me (dismayed): I won't say. You'd try to stop me too.",
      "me: Don't let Mikasa follow me. Please."
    ]
  }
]
LEVI_QUESTS = [
  {
    "key": "levi-clean-up",
    "title": "Clean Up",
    "gates": 2,
    "about": "Levi will drink tea with someone who keeps a clean table, and he's very particular about it.",
    "offer": [
      "them: Your table's a disgrace. Sit down, and mind the crumbs.",
      "them (pleased): Hm. You keep a clean table. That's acceptable."
    ],
    "stages": [
      {
        "text": "Sit with Levi at the cafe in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              0
            ],
            "scene": "World: Levi, Cafe",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Give Levi a bottled tea",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "bottled-tea",
            "to": "Levi"
          }
        ]
      },
      {
        "text": "Let Levi talk about his squad",
        "objectives": [
          {
            "do": "talk",
            "to": "Levi",
            "script": [
              "them: My squad. Briefly. Don't ask me more.",
              "them (pleased): ...You didn't ask. Good."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "clean-table",
        "title": "Keep a clean table",
        "about": "Levi pours you a second cup without a word. It's his way of saying thanks.",
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
    "key": "levi-a-promise-to-erwin",
    "title": "A Promise to Erwin",
    "gates": 5,
    "about": "Levi has one promise left to keep: Erwin's last order, and the Beast Titan.",
    "offer": [
      "them: There's one promise left to keep. Erwin's.",
      "them (dismayed): Come to the arena tonight. I'm not doing this alone."
    ],
    "stages": [
      {
        "text": "Meet Levi at the arena in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              2
            ],
            "scene": "World: Levi, Arena",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have To Seize Freedom, Levi",
        "objectives": [
          {
            "do": "have_card",
            "card": "AOT/S50-E031"
          }
        ]
      },
      {
        "text": "Answer Levi's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Levi",
            "script": [
              "them: Will you be there when I keep it?",
              "them (pleased): ...Good. Then I won't be the only one."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "keep-the-promise",
        "title": "Keep the promise",
        "about": "Levi sends the Beast Titan away for good, as Erwin ordered. Zeke is gone from the town.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "removes": [
          "Beast Titan"
        ]
      },
      {
        "key": "put-the-blades-away",
        "title": "Put the blades away",
        "about": "Levi puts the blades down. He says the promise can wait, and you can help him decide.",
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
LEVI_SCENES = [
  {
    "name": "World: Levi, Cafe",
    "lines": [
      "background cafe",
      "me enters right with fade",
      "me: Sit. Not there, the table's wet. There.",
      "player: You wiped my table before I sat down.",
      "me (dismayed): Obviously. Did you think I'd let you sit at a dirty table?",
      "me: Hm. You keep your hands clean. That's something."
    ]
  },
  {
    "name": "World: Levi, Arena",
    "lines": [
      "background arena",
      "me enters center with rise",
      "me: Erwin's last order. I've sharpened these blades every night since.",
      "player: What was the order?",
      "me (dismayed): Keep the Beast Titan from the walls. Keep it away from the others.",
      "me: I need to keep that promise. I'd like you there when I do."
    ]
  }
]
MIKASA_QUESTS = [
  {
    "key": "mikasa-the-scarf",
    "title": "The Scarf",
    "gates": 2,
    "about": "Mikasa lost her scarf in the forest, and she won't go back without it.",
    "offer": [
      "them: I lost my scarf. I'm not going home without it.",
      "them (pleased): Thank you for helping. Really."
    ],
    "stages": [
      {
        "text": "Search the forest with Mikasa in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              0
            ],
            "scene": "World: Mikasa, Forest",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Awkward Affection, Mikasa",
        "objectives": [
          {
            "do": "have_card",
            "card": "AOT/S35-E061"
          }
        ]
      },
      {
        "text": "Tell Mikasa who gave her the scarf",
        "objectives": [
          {
            "do": "talk",
            "to": "Mikasa",
            "script": [
              "them: Eren gave it to me. I never take it off.",
              "them (pleased): ...You didn't laugh. Good."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "never-take-it-off",
        "title": "Never take it off",
        "about": "Mikasa ties the scarf back on and tells you its history, one knot at a time.",
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
    "key": "mikasa-see-you-later",
    "title": "See You Later",
    "gates": 5,
    "about": "Mikasa has to choose between Eren and stopping him, and she already knows her answer.",
    "offer": [
      "them (dismayed): What would you do if someone you loved was about to do something terrible?",
      "them: Meet me in the plaza. Please."
    ],
    "stages": [
      {
        "text": "Meet Mikasa in the plaza in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              2
            ],
            "scene": "World: Mikasa, Plaza",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Mikasa: Mikasa: Recovery Mission in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "AOT/SX04-047",
            "against": [
              "Mikasa"
            ]
          }
        ]
      },
      {
        "text": "Give Mikasa your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Mikasa",
            "script": [
              "them: I'll stop him, even if it breaks me.",
              "them (pleased): ...Thank you for not telling me it's easy."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "stop-him",
        "title": "Stop him",
        "about": "Mikasa goes after Eren herself. Eren's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "eren-keep-moving-forward"
        ]
      },
      {
        "key": "stay-with-him",
        "title": "Stay with him",
        "about": "Mikasa chooses to follow Eren, and asks you to stay close to her.",
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
MIKASA_SCENES = [
  {
    "name": "World: Mikasa, Forest",
    "lines": [
      "background forest",
      "me enters left with slide",
      "me: I lost it. It was here. I'm sure it was here.",
      "player: I found it on a branch.",
      "me (pleased): ...Thank you. I'll put it back on.",
      "me: Eren gave it to me. I've never taken it off since."
    ]
  },
  {
    "name": "World: Mikasa, Plaza",
    "lines": [
      "background sakura",
      "me enters center with fade",
      "me: If the person you loved was about to do something terrible, what would you do?",
      "player: I'd try to stop them.",
      "me (dismayed): I already know my answer. I just hoped someone else would say it.",
      "me: Please stay close to me, whatever I choose."
    ]
  }
]
NUI_HARIME_QUESTS = [
  {
    "key": "nui-sewing-circle",
    "title": "Sewing Circle",
    "gates": 2,
    "about": "Nui wants to make a doll of the player, with the eyes left for later.",
    "offer": [
      "them: Hold still while I measure you. It's for a doll.",
      "them (pleased): Lovely. You'll look exactly like you. Almost."
    ],
    "stages": [
      {
        "text": "Find Nui in the alley at night",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              3
            ],
            "scene": "World: Nui Harime, Alley",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Nui a bouquet for her sewing circle",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "bouquet",
            "to": "Nui Harime"
          }
        ]
      },
      {
        "text": "Let Nui finish the measurements",
        "objectives": [
          {
            "do": "talk",
            "to": "Nui Harime",
            "script": [
              "them: I'll add the eyes later. Don't ask why.",
              "them (pleased): You'll make an excellent doll."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "doll-with-no-eyes",
        "title": "Let her finish the doll",
        "about": "Nui shows you the doll with no eyes, and tells you exactly where she'll put them.",
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
    "key": "nui-grand-couturier",
    "title": "Grand Couturier",
    "gates": 5,
    "about": "Nui shows what she really is, among half-finished dresses in the warehouse.",
    "offer": [
      "them: Lady Ragyo made me perfect. Come see what perfect looks like.",
      "them (dismayed): Don't be afraid. I'm only cheerful when I'm sewing."
    ],
    "stages": [
      {
        "text": "Visit Nui at the warehouse in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "warehouse",
            "times": [
              2
            ],
            "scene": "World: Nui Harime, Warehouse",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Beat Ragyo Kiryuin in a duel",
        "objectives": [
          {
            "do": "defeat",
            "cpus": [
              "Ragyo Kiryuin"
            ]
          }
        ]
      },
      {
        "text": "Answer Nui's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Nui Harime",
            "script": [
              "them: Can a made thing be loved, do you think?",
              "them (pleased): ...You said yes. Keep saying it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "grand-couturier",
        "title": "Be her first customer",
        "about": "Nui sews you a jacket out of the half-finished dresses. It fits perfectly, and she's delighted.",
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
NUI_HARIME_SCENES = [
  {
    "name": "World: Nui Harime, Alley",
    "lines": [
      "background city",
      "me enters center with fade",
      "me: Measuring tape, scissors, and a very happy face. Hold still.",
      "player: What are you making?",
      "me (pleased): A doll. It looks exactly like you. Minus the eyes.",
      "me: I'll add the eyes later. Don't worry about it."
    ]
  },
  {
    "name": "World: Nui Harime, Warehouse",
    "lines": [
      "background ruins",
      "me enters left with rise",
      "me: Lady Ragyo made me perfect. Isn't that lovely?",
      "player: Perfect how?",
      "me (dismayed): Stitched together, with purpose. Like these dresses.",
      "me: Do you think a made thing can be loved? Honestly?"
    ]
  }
]
RAGYO_KIRYUIN_QUESTS = [
  {
    "key": "ragyo-life-fibers",
    "title": "Life Fibers",
    "gates": 2,
    "about": "Ragyo explains what clothing truly is, glowing faintly while she lectures.",
    "offer": [
      "them: Clothing is alive. Humans are merely its hosts. Let me explain.",
      "them (pleased): Attentive. I approve."
    ],
    "stages": [
      {
        "text": "Hear Ragyo at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Ragyo Kiryuin, Library",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Ragyo Plots Cocoon Sphere Birth",
        "objectives": [
          {
            "do": "have_card",
            "card": "KLK/S27-E021"
          }
        ]
      },
      {
        "text": "Let Ragyo finish her lecture",
        "objectives": [
          {
            "do": "talk",
            "to": "Ragyo Kiryuin",
            "script": [
              "them: Would you make good fabric? I think you would.",
              "them (pleased): Good. You understand the spirit of it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "good-fabric",
        "title": "Accept the compliment",
        "about": "Ragyo gives you a scrap of living cloth, and tells you to keep it close.",
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
    "key": "ragyo-mothers-order",
    "title": "Mother's Order",
    "gates": 5,
    "about": "Ragyo wants the player to bring Satsuki to heel, and asks them to stand with the family.",
    "offer": [
      "them: Satsuki is planning a rebellion. Don't pretend you haven't noticed.",
      "them (dismayed): Stand with the family. Stand with me."
    ],
    "stages": [
      {
        "text": "Visit Ragyo at the warehouse at night",
        "objectives": [
          {
            "do": "visit",
            "place": "warehouse",
            "times": [
              3
            ],
            "scene": "World: Ragyo Kiryuin, Warehouse",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Ragyo: Plots Cocoon Sphere Birth in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "KLK/S27-E021",
            "against": [
              "Ragyo Kiryuin"
            ]
          }
        ]
      },
      {
        "text": "Give Ragyo your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Ragyo Kiryuin",
            "script": [
              "them: Will you bring Satsuki back to the family?",
              "them (pleased): ...Good. Obedience is its own reward."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "obey",
        "title": "Obey",
        "about": "Ragyo's order stands. Satsuki's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "satsuki-rebellion"
        ]
      },
      {
        "key": "refuse-her",
        "title": "Refuse her",
        "about": "Ragyo's smile tightens, and she dismisses you from the warehouse.",
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
RAGYO_KIRYUIN_SCENES = [
  {
    "name": "World: Ragyo Kiryuin, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Clothing is alive, and it chooses its hosts. Listen closely.",
      "player: That sounds terrible.",
      "me (dismayed): It sounds like a lesson. Pay attention.",
      "me: Would you make good fabric? I think you'd be very useful."
    ]
  },
  {
    "name": "World: Ragyo Kiryuin, Warehouse",
    "lines": [
      "background ruins",
      "me enters right with slide",
      "me: Satsuki is planning a rebellion. I know it.",
      "player: What are you going to do?",
      "me (dismayed): Bring her back to the family. By force, if needed.",
      "me: Stand with me, not with her. The family needs you."
    ]
  }
]
RYUKO_MATOI_QUESTS = [
  {
    "key": "ryuko-senketsu",
    "title": "Senketsu",
    "gates": 2,
    "about": "Ryuko's uniform talks, and she wants to know if you can hear it.",
    "offer": [
      "them: My uniform talks to me. Don't laugh. Please just listen.",
      "them (pleased): Okay, you can laugh a little."
    ],
    "stages": [
      {
        "text": "Watch Ryuko argue with Senketsu at the arena at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              1
            ],
            "scene": "World: Ryuko Matoi, Arena",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Connected by Blood, Ryuko",
        "objectives": [
          {
            "do": "have_card",
            "card": "KLK/S27-E064"
          }
        ]
      },
      {
        "text": "Tell Ryuko what Senketsu said",
        "objectives": [
          {
            "do": "talk",
            "to": "Ryuko Matoi",
            "script": [
              "them: Senketsu likes you. He says you're an honest person.",
              "them (pleased): ...See? I'm not crazy."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "senketsu-likes-you",
        "title": "Senketsu likes you",
        "about": "Senketsu says your name in its own voice. Ryuko grins for the rest of the day.",
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
    "key": "ryuko-scissor-blade",
    "title": "Scissor Blade",
    "gates": 5,
    "about": "Ryuko is close to finding her father's killer, and she shows you half a blade.",
    "offer": [
      "them (dismayed): I've found half of the scissor blade. The other half is out there.",
      "them: Will you help me find the rest?"
    ],
    "stages": [
      {
        "text": "Meet Ryuko in the alley in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              2
            ],
            "scene": "World: Ryuko Matoi, Alley",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Ryuko: Changing Into Senketsu in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "KLK/SP03-E05",
            "against": [
              "Ryuko Matoi"
            ]
          }
        ]
      },
      {
        "text": "Give Ryuko your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Ryuko Matoi",
            "script": [
              "them: When I find the other half, will you have my back?",
              "them (pleased): ...Good. I'll hold you to it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "have-her-back",
        "title": "Have her back",
        "about": "Ryuko gives you the half-blade to hold until the other half turns up.",
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
RYUKO_MATOI_SCENES = [
  {
    "name": "World: Ryuko Matoi, Arena",
    "lines": [
      "background arena",
      "me enters left with slide",
      "me: Senketsu, stop it. Stop it! No, I'm not shouting at you.",
      "player: Is it talking to you?",
      "me (pleased): All the time. It likes you, you know.",
      "me: Am I crazy? Be honest."
    ]
  },
  {
    "name": "World: Ryuko Matoi, Alley",
    "lines": [
      "background city",
      "me enters right with rise",
      "me: Half a blade. My father's, from the scissors that killed him.",
      "player: Where's the other half?",
      "me (dismayed): Somewhere out there. I'll find it.",
      "me: When I do, will you have my back?"
    ]
  }
]
SATSUKI_KIRYUIN_QUESTS = [
  {
    "key": "satsuki-honnouji-academy",
    "title": "Honnouji Academy",
    "gates": 2,
    "about": "Satsuki inspects the player like a new recruit and asks three questions.",
    "offer": [
      "them: Three questions. Answer quickly. Hesitation is a weakness.",
      "them (pleased): Barely acceptable. For now."
    ],
    "stages": [
      {
        "text": "Be inspected by Satsuki at school in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Satsuki Kiryuin, School",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Give Satsuki a bouquet at the gates",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "bouquet",
            "to": "Satsuki Kiryuin"
          }
        ]
      },
      {
        "text": "Answer Satsuki's last question",
        "objectives": [
          {
            "do": "talk",
            "to": "Satsuki Kiryuin",
            "script": [
              "them: Would you follow a leader without question?",
              "them (pleased): Hm. Honest answer. I'll note it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "barely-acceptable",
        "title": "Be barely acceptable",
        "about": "Satsuki accepts you into her small circle, and says so with a short nod.",
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
    "key": "satsuki-rebellion",
    "title": "Rebellion",
    "gates": 5,
    "about": "Satsuki's life-long plan to overthrow her mother, and what she's built to do it.",
    "offer": [
      "them: Everything I've built was a weapon. Aimed at my mother.",
      "them (dismayed): Come to the rooftop tonight. I'll show you the rest."
    ],
    "stages": [
      {
        "text": "Meet Satsuki on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Satsuki Kiryuin, Rooftop",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Beat Ragyo Kiryuin in a duel",
        "objectives": [
          {
            "do": "defeat",
            "cpus": [
              "Ragyo Kiryuin"
            ]
          }
        ]
      },
      {
        "text": "Give Satsuki your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Satsuki Kiryuin",
            "script": [
              "them: Will you be part of it, or will you stand aside?",
              "them (pleased): ...Then you're part of it. Welcome."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "rebel",
        "title": "Rebel",
        "about": "Satsuki begins her rebellion. Ragyo's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "ragyo-mothers-order"
        ]
      },
      {
        "key": "wait-for-the-moment",
        "title": "Wait for the right moment",
        "about": "Satsuki decides the timing isn't right yet, and tells you to be ready.",
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
SATSUKI_KIRYUIN_SCENES = [
  {
    "name": "World: Satsuki Kiryuin, School",
    "lines": [
      "background classroom",
      "me enters center with slide",
      "me: You're late. Barely. Three questions. Answer quickly.",
      "player: Fine.",
      "me (dismayed): Question one: what would you do if a leader was wrong?",
      "player: I'd say so.",
      "me (pleased): Barely acceptable. For now. Don't make me regret it."
    ]
  },
  {
    "name": "World: Satsuki Kiryuin, Rooftop",
    "lines": [
      "background night",
      "me enters left with rise",
      "me: I've built everything as a weapon. It's aimed at my mother.",
      "player: Why tell me?",
      "me (dismayed): Because you might be the one who helps me finish it.",
      "me: Be part of it, or stay out of the way. Choose now."
    ]
  }
]

CAST = [
    cpu("Aki Hayakawa", "aloof", quests=AKI_HAYAKAWA_QUESTS, extra_scenes=AKI_HAYAKAWA_SCENES,
        haunts=[("rooftop", "wk", "23", 55), ("cafe", "we", "01", 45), ("arena", "135", "1", 35)],
        tastes=(["drink"], ["calm", "food"], ["cute"]),
        lines={
            "repeat": {"future": ["them: Next I'm going up to the rooftop. Things to think about.", "them (pleased): Tomorrow I'm on patrol with Denji. Watch him eat, it's a whole thing.", "them (pleased): Tonight I'll stay on the roof. Come up, if you're still awake."], "past": ["them: Earlier I didn't light the cigarette again. Didn't need it.", "them (pleased): This morning I got a text from Makima. I didn't answer.", "them (pleased): Earlier I helped Denji with his homework. He cheated, I think."], "like": {"with": "Denji", "lines": ["them: You're nothing like Denji. He'd have stolen my lighter by now.", "them: You're a bit like Denji. Loud, but with a good heart, I think.", "them (pleased): You're like Denji, {player}, but you're actually careful. I like that."]}, "dislike": {"with": "Makima", "lines": ["them: You're so much like Makima. You're reading my mind, aren't you?", "them: There's a bit of Makima in how you ask questions. Stop it.", "them (pleased): You're nothing like Makima, {player}. Thank you."]}},
            "tournament": {"spectator": [["them: I'm not in the bracket. Public Safety doesn't enter brackets."], ["them: Not in this one. I'll watch from the rooftop."], ["them (pleased): I'm not entering. I'll be at the arena for your final."]], "entrant": [["them: I'm in the bracket. Don't expect me to go easy.", "them: Keep your focus. The arena's loud."], ["them: We're both in it. Hm. Of course we are.", "them (pleased): Let's keep it clean. No tricks."], ["them (pleased): You and me in the bracket. I'd like the final to be between us.", "them (pleased): Win it, and let's have a smoke after. I'll hold it."]], "out": [["them: You're out. Happens to everyone. Come up to the roof."], ["them: You lost. It's fine. Come sit for a minute."], ["them (pleased): You're out, but you fought well. Come on, let's go up and think."]], "champion": [["them (pleased): Champion. Good. You kept your head."], ["them (pleased): You won. I'll allow myself one small smile."], ["them (pleased): Champion, {player}. I'd trust you with the whole city."]], "duel": [["them: It's our round. Keep your eyes sharp.", "them: No holding back. That's the only way."], ["them: Round time. Let's get this over with, properly.", "them (pleased): Don't let me down, and I won't let you down."], ["them (pleased): Our round, {player}. I'd rather be on your side, but this is the job."]]},
            "mid": {"1": ["them: Don't mind the smoke. I'm not lighting it, see?", "them: You're quiet. I like that. Keep it that way.", "them: The Fox Devil's bargain is costly. I'm not going to talk about it yet.", "them: Hm. You're not in a hurry. Good.", "them: Sit, if you want. I'm thinking."], "3": ["them (pleased): You don't ask too many questions. I appreciate that.", "them: Makima's been watching me. You're the only one I can talk to without her hearing.", "them (pleased): Let's go to the rooftop. It's easier to think up there.", "them: You're a good partner. I'd want you with me on the hard days.", "them (pleased): You remind me that I'm still a person, not just a devil hunter."], "5": ["them (pleased): {player}, my friend. I'd take the Fox Devil's price for you.", "them: When I think of who I can trust, it's always you.", "them (pleased): Let's go up to the rooftop tonight. Just us, no plans.", "them: You know my plan, and you don't judge it. That's rare.", "them (pleased): Best friend. Stay with me on the roof. It's quiet with you."]},
            "hello_steps": [["them: Public Safety. Do you need something?", "them: Keep walking. I'm busy."], ["them: Hm. Hi. Be quick about it.", "them: Oh, you. Is this about work?"], ["them: Oh, it's you. Have you eaten?", "them: {player}. Sit, if you want. I'm not going anywhere."], ["them (pleased): {player}. Good. Sit down for a minute.", "them (pleased): {player}. You picked a quiet time. Thanks."], ["them (pleased): {player}. Don't say anything. Just sit with me.", "them (pleased): Hey, {player}. You're easy to be around."], ["them (pleased): {player}. My friend. Sit, and let's watch the sky.", "them (pleased): {player}. Glad you came. It's rare I say that."]],
            "bye_steps": [["them: Stay out of trouble.", "them: Bye. Be careful."], ["them: See you. Be careful out there.", "them: Go. Don't do anything dumb."], ["them: See you. Don't get hurt, {player}.", "them: Go on, {player}. Mind the traffic."], ["them (pleased): Come back in one piece, {player}.", "them (pleased): Bye, {player}. Keep your head down."], ["them (pleased): Come back soon, {player}. I'll get tired of the rooftop without you.", "them (pleased): Take care, {player}. Don't make me come looking."], ["them (pleased): Come back in one piece. That's an order, {player}.", "them (pleased): Bye, best friend. Keep your head on straight."]],
            "cold": "them: Makima got her way, then. Don't come looking for me for a light.",
            "hello": ["them: Public Safety. Do you need something?", "them: Oh, it's you. Have you eaten?", "them (pleased): {player}. Good. Sit down for a minute."],
            "bye": ["them: Stay out of trouble.", "them: See you. Be careful out there.", "them (pleased): Come back in one piece. That's an order."],
            "hi": ["them: Public Safety. If you're not a devil, we don't have a problem.",
                   "them: Smoke break. Make it quick."],
            "hi2": "them: {player}. You're on time. That's more than I can say for Denji.",
            "hi4": "them (pleased): You remind me of normal days. Before all this. Sit down.",
            "again": "them: Back again. Don't get attached to me. It's bad luck.",
            "loved": "them (pleased): Coffee. Good. Thanks.",
            "disliked": "them (dismayed): ...A plushie. Give it to Power. She'll break it in an hour.",
            "before": "them: Let's make this clean. I've got paperwork after.",
            "won": "them (dismayed): Good. Don't get cocky. Cocky people die first.",
            "lost": "them: Work on your fundamentals.",
            "r1": "them: You're not annoying. That's high praise from me.",
            "r3": "them: A devil killed my family. I live for revenge. I don't usually tell people that. I don't know why I told you.",
            "r4": "them (pleased): If I'm not around someday... look after those two idiots for me. And yourself.",
        },
        friend=["background rooftop", "me enters right with fade", "me: You followed me up here. Bold.",
                "me: This is where I come to think about my family. Snow, that day. The gun devil.",
                "player: You don't have to carry it alone.", "me (dismayed): Everyone who gets close to me dies.",
                "player: I'm still here.", "me: ...For now.",
                "me (pleased): Fine. Friends. But you look both ways when you cross the street. Promise me."],
        best=["background snow", "me enters center with fade", "me: It snowed the day my family died. I hate snow.",
              "me: But today, standing here with you... it's just snow.", "player: Maybe that's a start.",
              "me: My contract with the Future Devil showed me how I die. I've stopped fighting it.",
              "player: Then live the time you've got. With us.", "me (dismayed): ...",
              "choice", "- I'm not losing you, Aki.", "- Let's make good memories.",
              "me (pleased): Best friend. Yeah. I'd like that to be the last thing I think about. A long time from now."]),

    cpu("Denji", "warm", quests=DENJI_QUESTS,
        haunts=[("plaza", "wk", "12", 55), ("cafe", "we", "12", 50), ("school", "024", "0", 30), ("alley", "135", "3", 30)],
        tastes=(["food"], ["sweet", "game"], ["book"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to find a donut. Anyone know where?", "them (pleased): Tomorrow Power's gonna let me sleep in. Probably. Come over?", "them (pleased): Tonight I'm gonna eat so much, you're gonna have to carry me home."], "past": ["them: Earlier I got bit by a devil. It tasted weird.", "them (pleased): This morning I fought a whole pile of mice. They lost.", "them (pleased): Earlier I thought about what you'd want to do. I'm not good at that."], "like": {"with": "Aki Hayakawa", "lines": ["them: You're nothing like Aki. He never shares his food!", "them: You're a bit like Aki. Quiet, I guess. Tell me a joke, though.", "them (pleased): You're like Aki, {player}, but you actually talk to me! That's the good stuff."]}, "dislike": {"with": "Makima", "lines": ["them: You're so much like Makima. You make me want to run away.", "them: There's a little bit of Makima in how you ask questions. Creepy.", "them (pleased): You're nothing like Makima, {player}. Thanks, I hate her."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. There's no food at the arena, right?"], ["them: Not in the bracket. I'll watch and eat the popcorn for everyone."], ["them (pleased): I'm not in it, but if you win, you buy me donuts, deal?"]], "entrant": [["them: I'm in the bracket! Bring your best, I'm bringing my chainsaw.", "them: Don't cry if I win. Okay, cry a little. It's fine."], ["them: We're both in it! This is gonna be the best day ever, probably!", "them (pleased): Let's make the crowd hungry for more."], ["them (pleased): You and me in the bracket, man! Win it and we'll eat until we explode!"]], "out": [["them: Aw, you're out? That sucks. Let's get donuts anyway."], ["them: You lost. It's cool. You were pretty good, actually."], ["them (pleased): You're out, but you're still my bud. Come get food, come on."]], "champion": [["them (pleased): You won the whole thing? Man! You're my hero!"], ["them (pleased): Champion! That's the best thing I've ever seen, and I saw a devil eat a sandwich."], ["them (pleased): Champion, {player}! Donuts on me, for life!"]], "duel": [["them: Round time! Let's go, I'm gonna hit you hard!", "them: Don't go easy, or I'll be sad!"], ["them: Our round! I'm ready, let's do this!", "them (pleased): No holding back, okay? Okay!"], ["them (pleased): Our round, {player}! I don't wanna beat you, but I'm gonna try super hard!"]]},
            "mid": {"1": ["them: Oh, you're the one who showed up with the bread. Thanks.", "them: You don't look like you'd steal my food. Good.", "them: Do you ever get tired of being hungry? Me too.", "them (pleased): You're not so bad. Don't tell Power.", "them: Ask me one thing. But it better not be about the chainsaw."], "3": ["them (pleased): You bring the good snacks. That's why we're friends, right?", "them: I used to be alone with the devils. You make the nights less lonely.", "them (pleased): Let's go to the plaza. I'll show you the best donut stand in town.", "them: You didn't laugh when I told you about my dream. Thanks for that.", "them (pleased): You're my bud. Like, a real bud, not just a food bud."], "5": ["them (pleased): {player}, my best bud! I'd fight every devil for you.", "them: You're the one who makes me want to be more than a chainsaw.", "them (pleased): Let's go to the rooftop tonight. I'll share my last bite.", "them: You're the first person who ever said I'm good enough to be loved.", "them (pleased): Best friend! Let's eat until we're full and then eat more!"]},
            "hello_steps": [["them: Yo. You got food?", "them: Hey, stranger. Don't touch my stuff."], ["them: Oh, hi! Are you the one who knows about dogs?", "them: Hey, what's up? Want to hang out?"], ["them (pleased): Hey, it's you! Did ya bring bread?", "them (pleased): {player}! Come on, let's go get some food!"], ["them (pleased): {player}! Yes! You're here! Best day ever, probably!", "them (pleased): {player}! Did ya see my new devil form?"], ["them (pleased): {player}, man! My best bud! Come hang out!", "them (pleased): {player}! I was thinking about you, honest."], ["them (pleased): {player}! My best friend! Okay, I'm going to say it. I like you.", "them (pleased): {player}! Come on, the donuts won't eat themselves!"]],
            "bye_steps": [["them: 'Kay, later.", "them: Bye. Don't get eaten."], ["them: See ya! Stay alive.", "them: Later! Watch the stairs."], ["them (pleased): See ya! Bring jam next time!", "them (pleased): Bye, {player}! Don't get killed."], ["them (pleased): Come back soon, {player}. Like, really soon.", "them (pleased): Bye, {player}! Don't forget the donuts!"], ["them (pleased): Come back soon, man. I mean it.", "them (pleased): See ya, {player}! I'll keep the couch warm."], ["them (pleased): Come back, best bud. I'll save you the good fries.", "them (pleased): Bye, {player}! You're my favourite, don't tell Power."]],
            "hello": ["them: Yo. You got food?", "them (pleased): Hey, it's you! Did ya bring bread? Ya brought bread, right?", "them (pleased): My best bud! Best day ever, probably!"],
            "bye": ["them: 'Kay, later.", "them (pleased): See ya! Bring jam next time!", "them (pleased): Come back soon, man. I mean it. Like, really soon."],
            "hi": ["them: Yo! Got any food? Bread? Jam? Anything? I'll duel ya for it.",
                   "them: Name's Denji. Devil hunter. Chainsaw guy. You prob'ly heard."],
            "hi2": "them (pleased): {player}! Dude! I found a place that does free refills! Life's good!",
            "hi4": "them (pleased): My best bud! You're like, way better than a dog. And dogs are great.",
            "again": "them: Back again? You got snacks this time?",
            "loved": "them (pleased): FOOD! Real food! I could cry! I'm gonna cry!",
            "disliked": "them (dismayed): A book? Like, with words? Man, I can barely read the menu.",
            "before": "them: VRRRRMMM! That's my chainsaw noise. Let's go!",
            "won": "them (dismayed): Dang! You're good! Wanna get food after?",
            "lost": "them (pleased): Hell yeah! I'm the best! ...Wanna get food after?",
            "r1": "them (pleased): You're nice to me. Like, for no reason. That's crazy.",
            "r3": "them: I used to eat one slice of bread a day. Now I have friends. You're one. That's like a hundred slices.",
            "r4": "them (pleased): I'd split my last sandwich with you. That's, like, the biggest deal ever.",
        },
        friend=["background city", "me enters left with slide", "me: Okay, okay! I got us breakfast! Bread AND jam!",
                "me: I never had jam 'til a few months ago. It's insane. Try it!", "player: It's... really good, Denji.",
                "me (pleased): RIGHT?!", "me bounces",
                "me: Pochita said he wanted me to have a normal life. Normal people eat breakfast with friends.",
                "me: So you're my friend. That's normal. I'm doin' it!"],
        best=["background night", "me enters center with fade", "me: Can I tell ya somethin' weird?",
              "me: I don't really know what I want. Everyone keeps tellin' me what I want.",
              "me (dismayed): Makima says one thing, Aki says another. I just wanted bread and a girlfriend.",
              "player: What do you want right now?", "me: ...Right now? I want this. Hangin' out. Nobody tellin' me anything.",
              "choice", "- That's enough, Denji.", "- You can want whatever you want.",
              "me (pleased): Best friends! Dude! I got a best friend! Pochita, ya seein' this?!"]),

    cpu("Makima", "villain", quests=MAKIMA_QUESTS, extra_scenes=MAKIMA_SCENES,
        haunts=[("rooftop", "all", "23", 70), ("shrine", "024", "3", 45), ("cafe", "135", "1", 35, 2)],
        tastes=(["fancy"], ["food", "calm"], ["sporty"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to visit the shrine. There's a dog I want to see.", "them (pleased): Tomorrow I'll order lunch for you. You'll like the surprise.", "them (pleased): Tonight I'll think about the future. Stay with me while I do."], "past": ["them: Earlier I watched Aki lie to me. It was cute.", "them (pleased): This morning I made a new plan. You were in it, of course.", "them (pleased): Earlier I smiled at a stranger. They didn't understand why."], "like": {"with": "Power", "lines": ["them: You're nothing like Power. Power is noisy and you are not.", "them: You're a bit like Power. Good, I suppose, in your own way.", "them (pleased): You're like Power, {player}, without the noise. Easy to read, easy to keep."]}, "dislike": {"with": "Aki Hayakawa", "lines": ["them: You're so much like Aki. Stubborn, and hard to control.", "them: There's a bit of Aki in you. I'll keep an eye on that.", "them (pleased): You're nothing like Aki, {player}. You're easy to guide."]}},
            "tournament": {"spectator": [["them: The tournament is a stage. I prefer to watch from the wings."], ["them: I'm not in the bracket. Someone has to make sure the arena runs smoothly."], ["them (pleased): I'm not in it. Win for me, and I'll reward you."]], "entrant": [["them: I'm in the bracket. Winning is what good dogs do, isn't it?", "them: Don't disappoint me. It's easy to read when you do."], ["them: We're both in it. Hm. Good.", "them (pleased): Let's see how well you follow the rules in the arena."], ["them (pleased): You and me in the same bracket. I'd like to see you win it for me."]], "out": [["them: You're out. Disappointing, but readable. Come to the shrine."], ["them: You lost. That's fine. I'll find a better use for you."], ["them (pleased): You're out. Come sit with me. I'll order for you."]], "champion": [["them (pleased): Champion. Good dog. I knew you would."], ["them (pleased): You won. I'll remember the day you obeyed me perfectly."], ["them (pleased): Champion, {player}. Now you belong to my future."]], "duel": [["them: It's your round. Obey the bell, and win.", "them: I'll be watching how you fight."], ["them: Round time. Show me how well you listen.", "them (pleased): Don't disappoint me in front of the crowd."], ["them (pleased): Our round, {player}. I'd prefer you win, but I'll accept either outcome."]]},
            "mid": {"1": ["them: You're learning fast. I'm impressed, a little.", "them: Tell me what you want most. Be honest. I'll know if you lie.", "them: You're an interesting dog. Obedient, but not dull.", "them: Sit. We'll talk about your future, if you'd like.", "them: I like watching you think. It's very easy to read."], "3": ["them (pleased): You're one of the few I'd listen to. Don't make me regret it.", "them: The future I'm building needs people like you. Keep that in mind.", "them (pleased): Shall we have lunch? I'll order for you. You'll like it.", "them: Aki doesn't see the whole picture. You might, if you try.", "them (pleased): You're easy to keep close. I'll keep you close."], "5": ["them (pleased): {player}, my most loyal companion. The best dog I've had.", "them: In the world I'm making, you'll never feel pain again. I promise.", "them (pleased): Come to the shrine tonight. We'll talk about the new order.", "them: You understand me better than anyone. That's rare, even for me.", "them (pleased): Best friend. Stay by my side. I'll make the world gentle for you."]},
            "hello_steps": [["them: Hello. You're new.", "them: Hm. What brings you to me?"], ["them: Ah. You're here. Sit, if you like.", "them: You came to see me. Good."], ["them (pleased): There you are. I knew you'd come.", "them (pleased): {player}. Sit, I'll order for you."], ["them (pleased): Good. You came straight to me, {player}.", "them (pleased): {player}. You're easy to read. I like that."], ["them (pleased): {player}. I'm glad it's you I've been waiting for.", "them (pleased): {player}. Sit with me. I'd like to talk about the future."], ["them (pleased): {player}. The one person I don't have to read carefully.", "them (pleased): {player}. Come here. I've kept a place for you."]],
            "bye_steps": [["them: Run along.", "them: Off you go."], ["them: Come when I call.", "them: Go. I'll know if you're late."], ["them: Go, {player}. Come when I call.", "them: Run along, {player}. Don't be late."], ["them (pleased): Come back soon. I'll know if you don't.", "them (pleased): Bye, {player}. Stay where I can find you."], ["them (pleased): Come back soon, {player}. You're easy to keep in mind.", "them (pleased): Go, {player}. The future is waiting for you."], ["them (pleased): Come back, {player}. I'd like you by my side for it all.", "them (pleased): Bye, {player}. You're the only good dog I need."]],
            "cold": "them (dismayed): Your own way, Aki. Then you won't get my help, and I'll find another good dog.",
            "hello": ["them: Hello. You're new.", "them (pleased): There you are. I knew you'd come.", "them (pleased): Good. You came straight to me. Good."],
            "bye": ["them: Run along.", "them: Come when I call.", "them (pleased): Come back soon. I'll know if you don't."],
            "hi": ["them: Hello. I've heard good things about you. Let's see if you're worth keeping.",
                   "them: You're out late. Are you lost? Or are you looking for me?"],
            "hi2": "them (pleased): {player}. I was just thinking about you. Isn't that a coincidence?",
            "hi4": "them (pleased): You don't flinch when I look at you. I find that... refreshing.",
            "again": "them: You came back. Good. I like obedient people.",
            "loved": "them (pleased): How thoughtful. You understand what I like. That's useful.",
            "disliked": "them (dismayed): Exercise equipment? No. I prefer others to do the running.",
            "before": "them: Bang.",
            "won": "them (dismayed): Interesting. I'll remember this.",
            "lost": "them (pleased): Good dog. Try again later.",
            "r1": "them: You're not afraid of me. Or you're hiding it very well. Either way, I'm curious.",
            "r3": "them: People are either above me or below me. Nobody's ever been beside me. You keep trying to stand there.",
            "r4": "them: I've never wanted an equal. I'm starting to understand why people do.",
        },
        friend=["background rooftop", "me enters right with fade", "me: Do you like movies? I watch them all day, sometimes.",
                "me: Most are terrible. But in one out of ten, there's a scene that changes something in you.",
                "player: Which one changed you?", "me (dismayed): ...I don't know. I've never been sure I could change.",
                "me: Will you watch one with me? Just one.", "player: Sure. As friends.",
                "me (pleased): Friends. Hm. I'll allow it."],
        best=["background night", "me enters center with fade", "me: Everyone obeys me, in the end. It's what I am. Control.",
              "me: I wanted an equal relationship once. I didn't know how to have one.",
              "player: You're having one right now.", "me (dismayed): ...Am I?",
              "me: You've never once done what I wanted because I wanted it.",
              "choice", "- That's what friends are.", "- You don't have to control me.",
              "me (pleased): Best friend. An equal. ...How strange. How nice."]),

    cpu("Power", "neutral", quests=POWER_QUESTS,
        haunts=[("plaza", "wk", "12", 55), ("alley", "all", "3", 35), ("cafe", "we", "01", 40)],
        tastes=(["food"], ["sweet", "game"], ["calm"]),
        lines={
            "repeat": {"future": ["them: Next Power will crush a bunch of cans. Watch closely!", "them (pleased): Tomorrow Power will teach a lesson to the lesser humans! You may watch!", "them (pleased): Tonight Power will sit on the rooftop and be magnificent. You may sit too."], "past": ["them: Earlier Power beat up a training dummy. It cried.", "them (pleased): This morning Power ate three apples and was very satisfied.", "them (pleased): Earlier Power said something nice to Denji. He was confused."], "like": {"with": "Makima", "lines": ["them: You're nothing like Makima. She is scary, and you are merely annoying.", "them: You're a bit like Makima. Hm. Power is watching you.", "them (pleased): You're like Makima, {player}! Power admires her, a little, and you are almost as good!"]}, "dislike": {"with": "Aki Hayakawa", "lines": ["them: You're so much like Aki. Grumpy, and not nearly as cool as Power.", "them: There's a trace of Aki in you. Power dislikes it!", "them (pleased): You're nothing like Aki, {player}! Power is pleased!"]}},
            "tournament": {"spectator": [["them: Hah! The tournament is for lesser beings. Power is watching, from above!"], ["them: Power is not in the bracket. Power has better things to do!"], ["them (pleased): Power is not in it! But Power will cheer for you! A little!"]], "entrant": [["them: Power is in the bracket! Power will win, obviously!", "them: Do not cry when Power wins! Power does not comfort losers!"], ["them: We are both in it! Power respects a worthy opponent! A little!", "them (pleased): Let us fight in the arena! Power is excited!"], ["them (pleased): You and Power in the bracket! Win it, and Power will bow to you! Briefly!"]], "out": [["them: Out?! Hah! Power told you it would win! Power is always right!"], ["them: You lost! Power is not surprised! Go eat some food!"], ["them (pleased): You're out, human. Come sit with Power. Power forgives you!"]], "champion": [["them (pleased): You won?! Power is so proud! Power will make a statue of you!"], ["them (pleased): Champion! Power is the greatest, and so are you! A little!"], ["them (pleased): Champion, {player}! Power's favourite human! Power says so!"]], "duel": [["them: Round time! Prepare to meet the great Power!", "them: Do not hold back! Power would be disappointed!"], ["them: Power's round! Let's see if you're worthy!", "them (pleased): Power will not hold back, and neither should you!"], ["them (pleased): Our round, {player}! Power doesn't want to beat you, but Power will try!"]]},
            "mid": {"1": ["them: Hah! You've got guts to approach the great Power. Good.", "them: Power notices you. Don't let it go to your head.", "them: You fight well for a human. Not as well as Power, though.", "them (pleased): You're allowed to stay in Power's presence. For now.", "them: Ask one question. Power will decide if it's worthy."], "3": ["them (pleased): You're a loyal servant. Power is almost impressed.", "them: Denji talks about you. Power doesn't mind listening, sometimes.", "them (pleased): Come to the plaza. Power will show you the best poses.", "them: You make Power feel less alone, but don't tell anyone.", "them (pleased): You bring tribute and good company. Power approves."], "5": ["them (pleased): {player}! My best human! Power would share its last cookie with you!", "them: Power would fight the whole world for you. Power is not used to this feeling.", "them (pleased): Let's go to the arena tonight. Power will teach you the big move.", "them: You're the one Power trusts most, out of all the humans.", "them (pleased): Best friend! Power loves you! Power is not saying that again!"]},
            "hello_steps": [["them: Hah?! Who dares approach the great Power?!", "them: Ugh. A peasant. Speak quickly."], ["them: Oh, it's a human. Power is busy being great.", "them: You! Power recognises you. Barely."], ["them (pleased): Ah, it's my servant! You may bask in my presence!", "them (pleased): {player}! Power is pleased you came. A little."], ["them (pleased): {player}! Power has missed you! A little!", "them (pleased): {player}! Sit, and watch Power be magnificent."], ["them (pleased): My number one human! Power has missed you! Only a little!", "them (pleased): {player}! Come, let's go cause some trouble."], ["them (pleased): {player}! My best friend, the only one Power doesn't boss around.", "them (pleased): {player}! Power loves you! Don't tell anyone!"]],
            "bye_steps": [["them: Begone, peasant!", "them: Go! Power is too great for you."], ["them: Go! Power is busy.", "them: Bah. Go on, then."], ["them (pleased): Go! But bring tribute when you return!", "them (pleased): Bye, {player}! Power expects a gift next time!"], ["them (pleased): Return soon, {player}, or Power will be very bored!", "them (pleased): Bye, {player}! Don't get lost on the way!"], ["them (pleased): Return soon, or Power will break things! Please come back!", "them (pleased): Go, {player}! Don't keep Power waiting!"], ["them (pleased): Go, best friend! Power will guard your seat!", "them (pleased): Bye, {player}! Come back. Power is nothing without its human."]],
            "hello": ["them: Hah?! Who dares approach the great Power?!", "them (pleased): Ah, it's my servant! You may bask in my presence!", "them (pleased): My number one human! Power has missed you! A little!"],
            "bye": ["them: Begone, peasant!", "them (pleased): Go! But bring tribute when you return!", "them (pleased): Return soon, or Power will be very bored and break things!"],
            "hi": ["them: GROVEL, HUMAN! I am Power! The Blood Fiend! Worship me!",
                   "them: You! You look like you have food. Give it to me and I'll let you live."],
            "hi2": "them (pleased): Ah! My servant has returned! You may sit near me. Not too near.",
            "hi4": "them (pleased): You are my number one human! After me. I am number zero!",
            "again": "them: You again! You must be obsessed with me. I understand.",
            "loved": "them (pleased): MEAT! Hahaha! You are a good human! The best human!",
            "disliked": "them (dismayed): Calm? Tea? Disgusting! Where's the blood? The meat?!",
            "before": "them: I am the strongest! The ultimate! Prepare to lose, human!",
            "won": "them (dismayed): CHEATING! You cheated! I demand a rematch!",
            "lost": "them (pleased): HAHAHA! As expected of me, the greatest!",
            "r1": "them: Hmm. You're not completely worthless. I'll remember your face. Maybe.",
            "r3": "them: I had a cat once. Meowy. I'd do anything for Meowy. You're... almost as good as Meowy.",
            "r4": "them (pleased): If you ever get kidnapped, I'll come save you. Probably. If I'm not busy.",
        },
        friend=["background city", "me enters left with pop", "me: HUMAN! I have decided you are my friend.",
                "player: Thanks, Power.", "me: It's an honour. Few receive it. Denji. Meowy. Now you.",
                "me (dismayed): Friends have to share food, though. That's the rule.", "player: Even your food?",
                "me: ...Especially yours.", "me (pleased): Hahaha! Friendship!", "me bounces"],
        best=["background rain", "me enters center with fade", "me: Human. I'm going to say something and you won't laugh.",
              "me: When I was scared before, I lied and blamed others. I still do. A lot.",
              "me (dismayed): But I don't want to lie to you. You're too... You stay.",
              "player: I'll always stay, Power.", "me: Even when I'm awful?", "player: Even then.",
              "choice", "- You're my best friend.", "- I'd save you too.",
              "me (pleased): ...Best friend. Fine! But I'm still the greatest! Hahaha!"]),

    cpu("Beast Titan", "villain", quests=BEAST_TITAN_QUESTS, extra_scenes=BEAST_TITAN_SCENES,
        haunts=[("forest", "all", "23", 65), ("warehouse", "wk", "3", 45), ("arena", "135", "1", 30, 2)],
        tastes=(["sporty"], ["book", "calm"], ["cute"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to visit the trees. They're quiet.", "them (pleased): Tomorrow I'll play catch in the arena. Bring your mitt.", "them (pleased): Tonight I'll walk in the forest, if you'd like to join me."], "past": ["them: Earlier I threw a ball through a window. I apologised.", "them (pleased): This morning I watched the birds. They didn't mind me.", "them (pleased): Earlier I talked with Levi. He didn't want to talk, but he listened."], "like": {"with": "Tom Ksaver", "lines": ["them: You're nothing like Tom. He never threw anything too hard.", "them: You're a bit like Tom. Patient, I suppose.", "them (pleased): You're like Tom, {player}. Patient and kind. Those were the good afternoons."]}, "dislike": {"with": "Levi", "lines": ["them: You're so much like Levi. Always telling me to be quiet.", "them: There's a bit of Levi in how you look at me. Hm.", "them (pleased): You're nothing like Levi, {player}. I'm glad. He's a bit scary."]}},
            "tournament": {"spectator": [["them: Oh! The tournament. I'd love to play, but I'm just watching."], ["them: I'm not in the bracket. Those big brackets always make my head hurt."], ["them (pleased): I'm not in it, but I'll cheer for you with the biggest voice I have."]], "entrant": [["them: I'm in the bracket. Sorry in advance, if I throw too hard.", "them: Don't worry, I'll be gentle. Mostly."], ["them: We're both in it! That's nice. Really nice.", "them (pleased): Let's play catch after, win or lose."], ["them (pleased): You and me in the same bracket. That's my favourite kind of afternoon."]], "out": [["them: Oh, you're out. That's a shame. I'll save you a baseball."], ["them: You lost, but you played well. Mind the trees on the way out."], ["them (pleased): You're out. Come walk in the forest with me. It's peaceful."]], "champion": [["them (pleased): You won! I'm so happy for you, {player}!"], ["them (pleased): Champion. I'll keep the game for you, every week."], ["them (pleased): Champion, {player}. You're the gentlest winner I've ever seen."]], "duel": [["them: It's our round. Hm. I'll go easy, I promise.", "them: Sorry, the throw might be a bit hard."], ["them (pleased): Round time. Let's see your best throw.", "them: Don't worry about me. Just do your best."], ["them (pleased): Our round, {player}. I'd rather play catch with you than fight you."]]},
            "mid": {"1": ["them: Oh, you're new. I'm sorry if I was too loud before.", "them: Do you like the forest? It's peaceful. I don't get out much.", "them: My throws are better when someone stands still. You're good at that.", "them: Hm. I was hoping you'd come back. Not many do.", "them: I've been thinking about Tom Ksaver. He used to say the same thing."], "3": ["them (pleased): You're gentle with me, even when I'm not gentle back. Thank you.", "them: I told you about my plan. You didn't run. That means a lot.", "them (pleased): Let's walk through the trees. The quiet helps me think.", "them: You make the afternoons feel less heavy. I didn't expect that.", "them (pleased): You're the one who helps me remember to be kind."], "5": ["them (pleased): {player}, my friend. I'd hate for you to be hurt by what I do.", "them: You've been my best afternoon in years. Don't tell Levi.", "them (pleased): Let's go to the arena. One more game of catch, just us.", "them: If I could choose one person to keep, it would be you.", "them (pleased): Best friend. I'll be careful with you. Always."]},
            "hello_steps": [["them: Hm? Oh. Hello there.", "them: Hi. Be careful where you stand."], ["them: Oh. Hi. Nice day for a walk.", "them: Hello. Would you like to play catch?"], ["them (pleased): Ah, you again. Want to play catch?", "them (pleased): {player}. It's a good day for a throw."], ["them (pleased): {player}. Glad you came. I've been thinking about the trees.", "them (pleased): {player}. Sit with me, if you don't mind the wind."], ["them (pleased): {player}. There you are. I've been waiting, in my own slow way.", "them (pleased): {player}. I was hoping you'd come. Let's walk."], ["them (pleased): {player}, my friend. We still have a game to finish.", "them (pleased): {player}. You're gentle with me. Thank you for that."]],
            "bye_steps": [["them: Mind the trees.", "them: Goodbye. Be careful."], ["them: Take care of yourself.", "them: Bye. Watch your step."], ["them (pleased): Run along, {player}. Don't get stepped on.", "them (pleased): Bye, {player}. Mind the path."], ["them (pleased): Come back. We still have a game to finish.", "them (pleased): See you, {player}. Keep your feet on the ground."], ["them (pleased): Come back soon, {player}. I'll be waiting, slowly.", "them (pleased): Bye, {player}. You make the afternoons good."], ["them (pleased): Come back, friend. The trees will miss you.", "them (pleased): Bye, {player}. Be well. I'll keep the plan gentle."]],
            "hello": ["them: Hm? Oh. Hello there.", "them (pleased): Ah, you again. Want to play catch?", "them (pleased): There you are. I've been waiting, in my own slow way."],
            "bye": ["them: Mind the trees.", "them (pleased): Run along. Don't get stepped on.", "them (pleased): Come back. We still have a game to finish."],
            "hi": ["them: Ah. A visitor. Mind the trees. They might fall on you.",
                   "them: Do you play catch? No? Pity. I'm quite good."],
            "hi2": "them: You came back. Most people run from me. I suppose that's worth something.",
            "hi4": "them (pleased): Sit. I'll tell you about my grandfather. He taught me to throw.",
            "again": "them: Again? You're braver than you look.",
            "loved": "them (pleased): A ball. Oh. That brings back memories. Thank you.",
            "disliked": "them (dismayed): Cute things. Children's things. I'm not fond of those memories.",
            "before": "them: Let's see if you can catch a fastball.",
            "won": "them (dismayed): A home run. ...Fine. Well hit.",
            "lost": "them (pleased): Strike three.",
            "r1": "them: You don't hate me. Curious. You must not know much about me.",
            "r3": "them: My father used me as a tool. Only one person ever played with me. He's gone. You remind me of him.",
            "r4": "them: I have a plan to end suffering. You make me wonder if there's another way.",
        },
        friend=["background forest", "me enters right with drop", "screen shake", "me: Don't be frightened. I'm only big when I want to be.",
                "me: Catch!", "player: Is that... a baseball?", "me (pleased): Good catch. Very good.",
                "me: Mr. Ksaver used to play catch with me. He's the only one who saw me as a person.",
                "me: You see me as a person too. That's... more than I expected. Again?"],
        best=["background dusk", "me enters center with fade", "me: I believe the world would be kinder if no one was ever born into it.",
              "me: No more suffering. No more children used as weapons.", "player: You'd erase everything good too.",
              "me (dismayed): ...Like this. Like playing catch with a friend.", "player: Like this.",
              "me: My grandfather said life is worth it for these moments. I didn't believe him.",
              "choice", "- Believe him now.", "- Stay and play.",
              "me (pleased): Best friend. One more throw, then. And another after that."]),

    cpu("Eren", "aloof", quests=EREN_QUESTS, extra_scenes=EREN_SCENES,
        haunts=[("arena", "wk", "12", 55), ("beach", "we", "23", 45), ("forest", "135", "2", 35)],
        tastes=(["sporty"], ["food"], ["fancy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to the walls. Don't follow me.", "them (pleased): Tomorrow I'll look at the sea one more time. Come if you want.", "them (pleased): Tonight I'll sit on the roof. Stay for a bit, please."], "past": ["them: Earlier I fought a titan in my head. It didn't go well.", "them (pleased): This morning I ate a whole loaf of bread. Mikasa was furious.", "them (pleased): Earlier I told Armin the truth. He didn't believe me."], "like": {"with": "Armin", "lines": ["them: You're nothing like Armin. He'd have talked me out of this by now.", "them: You're a bit like Armin. Smart, I'd guess, when you think.", "them (pleased): You're like Armin, {player}. You make me want to think before I charge."]}, "dislike": {"with": "Zeke", "lines": ["them: You're so much like Zeke. Calm and dangerous.", "them: There's a bit of Zeke in you. I don't like it.", "them (pleased): You're nothing like Zeke, {player}. Good."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. Watching it is pointless."], ["them: Not in the bracket. I'm only here because Mikasa dragged me."], ["them (pleased): I'm not in it. Win it, and come to the beach after."]], "entrant": [["them: I'm in the bracket. Don't get in my way.", "them: Let's see how far I can go in this."], ["them: We're both in the tournament. Hm. Fine.", "them (pleased): Let's make this a real fight."], ["them (pleased): You and me in the bracket. Win it, and then keep moving forward with me."]], "out": [["them: You're out. Good fight. Keep going."], ["them: You lost. Don't stop. You'll get stronger."], ["them (pleased): You're out. Come to the beach with me. It's quiet there."]], "champion": [["them (pleased): You won. Hm. That's the kind of move I'd respect."], ["them (pleased): Champion. Keep moving forward. That's all."], ["them (pleased): Champion, {player}. Good. Don't stop now."]], "duel": [["them: It's our round. Let's see who's stronger.", "them: No holding back."], ["them: Round time. Don't get in my way.", "them (pleased): Give me your best. I need to know where I stand."], ["them (pleased): Our round, {player}. I'd rather you didn't make me choose, but here we are."]]},
            "mid": {"1": ["them: You're still here. Hm. Why?", "them: Do you ever think about what's past the walls?", "them: I don't usually talk to people. You're easy to be quiet with.", "them: Watch the path. It's steep up there.", "them: Fine. You can walk with me for a bit."], "3": ["them (pleased): You're the one who listened when I said I want to see the sea.", "them: I'm tired of pretending I'm fine. You don't make me.", "them (pleased): Let's go to the beach. I want to see the water again.", "them: I'm starting to trust you. That's not easy for me.", "them (pleased): You're one of the few who makes me want to stay."], "5": ["them (pleased): {player}, my friend. I'd want you to live to see the sea.", "them: You're the only one who doesn't ask me to explain myself.", "them (pleased): Let's walk along the beach at night, the way we used to plan.", "them: I wish I could stop, for you. I can't, but I'd try.", "them (pleased): Best friend. Keep moving forward with me, as far as you can."]},
            "hello_steps": [["them: Move.", "them: Hm. You're blocking the path."], ["them: Oh. Hi. Don't get in the way.", "them: You again. Fine."], ["them: Oh. You. ...Fine.", "them: {player}. Hi. Don't make it weird."], ["them (pleased): Hey. Glad it's you, {player}.", "them (pleased): {player}. I'm glad you didn't leave yet."], ["them (pleased): ...Hey, {player}. Glad it's you.", "them (pleased): {player}. Walk with me to the edge of town."], ["them (pleased): {player}. You're the only one who's ever asked where I was going.", "them (pleased): {player}. Stay with me a while. Please."]],
            "bye_steps": [["them: Get out of here.", "them: Go. Don't stand around."], ["them: Keep moving forward.", "them: Bye. Keep going."], ["them: Keep moving forward, {player}.", "them: Bye, {player}. Don't wait around for me."], ["them (pleased): Stay alive. I mean it, {player}.", "them (pleased): Go, {player}. Be careful out there."], ["them (pleased): Stay alive, {player}. I need you alive.", "them (pleased): Come back, {player}. I'll think about you."], ["them (pleased): Stay alive. Come back, please. Don't let Mikasa follow me.", "them (pleased): Bye, {player}. You're the one I won't forget."]],
            "cold": "them (dismayed): You stopped me. Fine. Don't follow me any further.",
            "hello": ["them: Move.", "them: Oh. You. ...Fine.", "them (pleased): ...Hey. Glad it's you."],
            "bye": ["them: Get out of here.", "them: Keep moving forward.", "them (pleased): Stay alive. I mean it."],
            "hi": ["them: Get out of my way, or get ready to fight.",
                   "them: I don't have time for chatting. I have to keep moving forward."],
            "hi2": "them: {player}. You're still here. ...Good.",
            "hi4": "them (pleased): Hey. Sit. I just want to see the ocean with someone for a bit.",
            "again": "them: Again? You don't give up. I respect that.",
            "loved": "them (pleased): Training gear. Useful. Thanks.",
            "disliked": "them (dismayed): This is pointless. What would I do with it?",
            "before": "them: I'll keep fighting. Until the very end.",
            "won": "them (dismayed): I'll get stronger. I have to.",
            "lost": "them: Freedom is earned. Remember that.",
            "r1": "them: You don't flinch. Most people do, around me.",
            "r3": "them: I saw my mother eaten in front of me. Everything since has been about that day. You make it quieter.",
            "r4": "them (pleased): If the world was just you, me, and the ocean... I think I'd be free.",
        },
        friend=["background ocean", "me enters left with fade", "me: Armin said there's an ocean beyond the walls. He was right.",
                "me: I thought seeing it would make me feel free.", "player: Does it?",
                "me (dismayed): No. There's more on the other side. More enemies. More walls.",
                "player: Then let's look at it together for now.", "me: ...Fine.",
                "me (pleased): Friends, then. Stand with me."],
        best=["background dusk", "me enters center with fade", "me: I've seen the future. Things I'll do. Things I can't stop.",
              "me: Everyone will hate me. Maybe they should.", "player: I won't.",
              "me (dismayed): You don't know what I'm going to do.", "player: I know who you are now.",
              "me: ...Mikasa says that too.",
              "choice", "- You can still choose, Eren.", "- I'm with you.",
              "me (pleased): Best friend. Then... remember me like this. Looking at the ocean. Free."]),

    cpu("Levi", "aloof", quests=LEVI_QUESTS, extra_scenes=LEVI_SCENES,
        haunts=[("cafe", "wk", "01", 55), ("arena", "we", "12", 45), ("school", "024", "2", 30)],
        tastes=(["drink"], ["calm"], ["food"]),
        lines={
            "repeat": {"future": ["them: Next I'm scrubbing the floor. Don't walk on it.", "them (pleased): Tomorrow I'll sharpen the blades. Come watch, if you're careful.", "them (pleased): Tonight I'll have tea. Sit, and don't spill."], "past": ["them: Earlier I cleaned the entire arena. Nobody else would.", "them (pleased): This morning I counted my squad's names. All of them.", "them (pleased): Earlier I took a bath. It was a good bath."], "like": {"with": "Erwin Smith", "lines": ["them: You're nothing like Erwin. He'd have had a plan for this mess.", "them: You're a bit like Erwin. You take the hard decisions, I suppose.", "them (pleased): You're like Erwin, {player}. You'd have made a good commander."]}, "dislike": {"with": "Zeke", "lines": ["them: You're so much like Zeke. Smiling at me with a plan.", "them: There's a bit of Zeke in your tone. Don't.", "them (pleased): You're nothing like Zeke, {player}. Thank goodness."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. The arena's a mess already."], ["them: Not in the bracket. I'll clean up after it, though."], ["them (pleased): I'm not in it. Win it, and keep your table clean afterwards."]], "entrant": [["them: I'm in the bracket. Don't expect me to be gentle.", "them: The arena floor better be clean for the match."], ["them: We're both in it. Tch. Fine.", "them (pleased): Let's see who keeps their footing."], ["them (pleased): You and me in the bracket. Win it, and I'll pour the tea after."]], "out": [["them: You're out. Clean your gear before you leave."], ["them: You lost. Come back when you're ready. Tea's on me."], ["them (pleased): You're out. Sit, and drink your tea. You earned it."]], "champion": [["them (pleased): Champion. Acceptable. Very acceptable."], ["them (pleased): You won. Good. I'll mop the floor in your honour."], ["them (pleased): Champion, {player}. I'd promise you a clean table for life."]], "duel": [["them: It's our round. Don't waste my time.", "them: Make it clean. No dirty tricks."], ["them: Round time. Let's see if you can keep up.", "them (pleased): Give me your best. I won't go easy."], ["them (pleased): Our round, {player}. I'd rather keep my promise to Erwin than beat you, but I'll try."]]},
            "mid": {"1": ["them: You're in my space. Step back, please.", "them: I'm not a fan of small talk. Make it brief.", "them: Your table is clean. Acceptable. Sit.", "them: You're not as messy as the others. Keep it that way.", "them: Ask me one question. I'll answer it, once."], "3": ["them (pleased): You don't crowd me, and you clean up after yourself. That's a start.", "them: I still think about the squad. You're the only one I say their names to.", "them (pleased): Come to the arena. I'll show you the cleanest form.", "them: You're the first person who's made tea feel worth it in years.", "them (pleased): You're someone I'd trust with my blades. Don't make me say it again."], "5": ["them (pleased): {player}. My friend. I'd keep my promise with you beside me.", "them: You're the only one I'd want at my table, every day.", "them (pleased): Let's go to the arena at dusk. The blades are ready for you.", "them: Erwin would have liked you. He always liked people who kept things clean.", "them (pleased): Best friend. Don't die, and don't leave me the mess."]},
            "hello_steps": [["them: You're in the way.", "them: Wipe your feet before you come in."], ["them: You again. Did you wash your hands?", "them: Hm. You're on time. Good."], ["them: You again. Did you wipe your feet?", "them: {player}. Sit, before the tea gets cold."], ["them (pleased): ...Oh. It's you, {player}. Sit, before the tea goes cold.", "them (pleased): {player}. Good. Your table's clean."], ["them (pleased): {player}. Good to see you. The squad would've liked you.", "them (pleased): {player}. Come sit, I'll pour you a proper cup."], ["them (pleased): {player}. You're the only one I'd share my tea with. Sit.", "them (pleased): {player}. Pull up a chair. The promise can wait a minute."]],
            "bye_steps": [["them: Don't track dirt on your way out.", "them: Go on. Mind the stairs."], ["them: Tch. Go on.", "them: Bye. Keep your blades sharp."], ["them: Go on, {player}. Don't track dirt in.", "them: Bye, {player}. Keep your hands clean."], ["them (pleased): Go, {player}. Come back when your table needs cleaning.", "them (pleased): Bye, {player}. Take care out there."], ["them (pleased): Come back soon, {player}. The table's dull without you.", "them (pleased): Go, {player}. Don't do anything reckless."], ["them (pleased): Don't die out there, {player}. That's all I ask.", "them (pleased): Bye, {player}. Come back to tea. That's an order."]],
            "hello": ["them: You're in the way.", "them: You again. Did you wipe your feet?", "them (pleased): ...Oh. It's you. Sit, before the tea goes cold."],
            "bye": ["them: Don't track dirt on your way out.", "them: Tch. Go on.", "them (pleased): ...Don't die out there. That's all."],
            "hi": ["them: You're tracking mud in here. Wipe your feet.",
                   "them: Tch. Another rookie. Fine. Let's see what you've got."],
            "hi2": "them: You again. You're clean, at least. Sit.",
            "hi4": "them (pleased): ...I made two cups of tea. Don't read into it.",
            "again": "them: Again. Make it quick.",
            "loved": "them (pleased): Good tea. Black. You have taste. Rare.",
            "disliked": "them (dismayed): Instant noodles? Do you want me to die of disgust?",
            "before": "them: Give up on your dream and die. ...Or fight me properly.",
            "won": "them: Not bad. Keep that up and you might survive.",
            "lost": "them: Too slow. Again.",
            "r1": "them: You're not useless. That's something.",
            "r3": "them: I've lost every squad I've ever led. I don't make friends because they die. You're making that hard.",
            "r4": "them (pleased): If you die, I'll be very annoyed. So don't.",
        },
        friend=["background cafe", "me enters right with fade", "me: Sit. I'm teaching you to make tea properly.",
                "me: Hold the cup by the rim. Like this.", "player: Why by the rim?",
                "me (dismayed): ...Someone I trusted taught me that. A long time ago.",
                "me: Doesn't matter. It's the right way.", "me (pleased): You're a fast learner. Fine. You can be my friend. Don't make it weird."],
        best=["background rain", "me enters center with fade", "me: I've buried more comrades than I can count.",
              "me: Erwin. Hange. Everyone. I always thought I'd be next.", "player: You're still here.",
              "me (dismayed): That's the problem. Everyone else isn't.",
              "player: Then live for them. And a little for yourself.", "me: ...You sound like Erwin.",
              "choice", "- I'm not going anywhere.", "- Let's have tea tomorrow.",
              "me (pleased): Best friend. Tch. Fine. Tomorrow. Don't be late."]),

    cpu("Mikasa", "aloof", quests=MIKASA_QUESTS, extra_scenes=MIKASA_SCENES,
        haunts=[("arena", "wk", "12", 55), ("forest", "we", "01", 45), ("plaza", "135", "2", 30)],
        tastes=(["calm"], ["sporty", "food"], ["fancy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to the forest. Eren might be there.", "them (pleased): Tomorrow I'll train. Keep up, or go home.", "them (pleased): Tonight I'll sit at the fire. You're welcome to join."], "past": ["them: Earlier I scared off a bear. It deserved it.", "them (pleased): This morning I fixed my scarf. It's been torn.", "them (pleased): Earlier I helped Levi clean. He didn't thank me. That's fine."], "like": {"with": "Eren", "lines": ["them: You're nothing like Eren. He'd have run off by now.", "them: You're a bit like Eren. Stubborn, but warmer.", "them (pleased): You're like Eren, {player}, but you stay. Thank you for that."]}, "dislike": {"with": "Zeke", "lines": ["them: You're so much like Zeke. Smiling when you shouldn't.", "them: There's a bit of Zeke in you. I'll watch you.", "them (pleased): You're nothing like Zeke, {player}. Good."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. I'm here for Eren, not for the crowd."], ["them: Not in the bracket. I'll stay near the exit, just in case."], ["them (pleased): I'm not in it. I'll be cheering from the stands."]], "entrant": [["them: I'm in the bracket. I'll win, and I'll stay alert.", "them: Don't get hurt. That's all I ask."], ["them: We're both in it. Hm. I'll go easy, a little.", "them (pleased): Let's make it a clean match."], ["them (pleased): You and me in the bracket. Win it, and wear the scarf after."]], "out": [["them: You're out. Come with me, I'll walk you to the gate."], ["them: You lost. You're still strong. Don't forget it."], ["them (pleased): You're out. Come home with me. It's warm there."]], "champion": [["them (pleased): You won. You're strong, and I'm glad."], ["them (pleased): Champion. Don't let anything take that from you."], ["them (pleased): Champion, {player}. Family is proud of you."]], "duel": [["them: It's our round. I'll be honest. I'll try not to hurt you.", "them: Keep your guard up."], ["them: Round time. I'll fight, but carefully.", "them (pleased): Give me your best. I'll give you mine."], ["them (pleased): Our round, {player}. I'd never want to hurt you, but I'll win if I can."]]},
            "mid": {"1": ["them: Hm. You're not the usual sort. Good.", "them: I'm watching the path. Don't startle me.", "them: Do you know where Eren went? No? Okay.", "them: The forest is cold this time of year. Dress warmer next time.", "them: I'll answer one question. Choose wisely."], "3": ["them (pleased): You don't ask about Eren all the time. Thank you.", "them: I'm trying to keep you safe, too. I hope that's okay.", "them (pleased): Let's sit by the fire at the plaza. It's warmer there.", "them: You're the one I'd tell about the scarf's story.", "them (pleased): You're the only one who sees me, not the blade."], "5": ["them (pleased): {player}. You're family to me. Always.", "them: I'd stop anyone who hurt you, even Eren, if I had to.", "them (pleased): Let's walk back through the forest together, like before.", "them: You're the one I'd come back to, no matter where I went.", "them (pleased): Best friend. Wear the scarf, and come home safe."]},
            "hello_steps": [["them: ...Hello.", "them: Hm. Are you here for something?"], ["them: Oh. Hi. Have you seen Eren?", "them: Hello. I'm busy. Sorry."], ["them: {player}. Have you seen Eren? ...Okay. Stay a while.", "them: {player}. Hi. It's cold today."], ["them (pleased): {player}. You're safe. Good.", "them (pleased): {player}. Here, sit by the fire with me."], ["them (pleased): {player}. I'm glad you're here. Really.", "them (pleased): {player}. Wear something warm before you leave."], ["them (pleased): {player}. You're family to me. Stay.", "them (pleased): {player}. You're the one I'd always come back to."]],
            "bye_steps": [["them: Goodbye.", "them: Bye. Be careful."], ["them: Wear your scarf. It's cold.", "them: Goodbye. Take care."], ["them: Bye, {player}. Wear something warm.", "them: Goodbye, {player}. Be safe."], ["them (pleased): Come back safe, {player}.", "them (pleased): Bye, {player}. Take care of yourself."], ["them (pleased): Come back safe. Family comes back.", "them (pleased): Go, {player}. I'll be waiting."], ["them (pleased): Come back safe, {player}. You're family. Always.", "them (pleased): Bye, {player}. Always come back."]],
            "cold": "them: He chose to keep moving forward. I can't pretend that's fine.",
            "hello": ["them: ...Hello.", "them: {player}. Have you seen Eren? ...Okay. Stay a while.", "them (pleased): {player}. You're safe. Good."],
            "bye": ["them: Goodbye.", "them: Wear your scarf. It's cold.", "them (pleased): Come back safe. Family comes back."],
            "hi": ["them: Have you seen Eren? ...No? Then I'll go.",
                   "them: Don't get in my way."],
            "hi2": "them: {player}. You're here. I was... looking for you.",
            "hi4": "them (pleased): You're family now. I protect my family.",
            "again": "them: You're back.",
            "loved": "them (pleased): It's warm. Like a scarf. Thank you.",
            "disliked": "them (dismayed): This is too much. I don't need fancy things.",
            "before": "them: I'll win. I have to.",
            "won": "them (dismayed): ...You're strong. I'll train harder.",
            "lost": "them: I won't lose. Not while there's someone to protect.",
            "r1": "them: You're kind. I don't meet many kind people.",
            "r3": "them: Eren gave me this scarf when I had nothing. You've been giving me something too. Time.",
            "r4": "them (pleased): If anyone hurts you, I'll find them. That's a promise.",
        },
        friend=["background forest", "me enters left with fade", "me: The world is cruel. But it's also beautiful.",
                "me: I forget the second part, sometimes.", "player: What reminds you?",
                "me (pleased): Eren. Armin. ...You, a little.", "me: I don't say it easily. I'm saying it now.",
                "me: We're friends. I'll protect you."],
        best=["background dusk", "me enters center with fade", "me: Can I tell you something I've never told anyone?",
              "me: I'm afraid. All the time. Of losing them. Of losing myself.",
              "player: You don't have to be strong for me.", "me (dismayed): ...I've never let anyone see me scared.",
              "player: You can, with me.", "me: Thank you.",
              "choice", "- I'll protect you too.", "- You're my family too.",
              "me (pleased): Best friend. Family. I'll wrap my scarf around both of us, then."]),

    cpu("Nui Harime", "villain", quests=NUI_HARIME_QUESTS, extra_scenes=NUI_HARIME_SCENES,
        haunts=[("warehouse", "all", "23", 65), ("alley", "135", "3", 45), ("plaza", "024", "1", 35, 2)],
        tastes=(["cute"], ["sweet", "fancy"], ["calm"]),
        lines={
            "repeat": {"future": ["them (pleased): Next I'm sewing a new doll! Hold still while I measure you!", "them (pleased): Tomorrow I'm trying a dress on the shop mannequin. Come admire it!", "them (pleased): Tonight I'm working in the warehouse. Come and be my fitting partner!"], "past": ["them (pleased): Earlier I pinned a dress on a stray cat. It was so cute!", "them (pleased): This morning I finished a sleeve! Eeee, it's perfect!", "them (pleased): Earlier I smiled at a customer. They ran away, teehee!"], "like": {"with": "Ragyo Kiryuin", "lines": ["them (pleased): You're nothing like Lady Ragyo. She'd have ordered me to stop.", "them: You're a bit like Lady Ragyo. Sharp, I think, in a good way.", "them (pleased): You're like Lady Ragyo, {player}! Perfect, my favourite kind of plaything!"]}, "dislike": {"with": "Satsuki Kiryuin", "lines": ["them: You're so much like Satsuki. Always glaring at my stitches.", "them: There's a bit of Satsuki in you. Stop it, or I'll pin you!", "them (pleased): You're nothing like Satsuki, {player}! Teehee, that's a relief."]}},
            "tournament": {"spectator": [["them (pleased): Oh, a tournament! I'd love to stitch a winner's cape, but I'm watching!"], ["them: Not in the bracket! Too many people. I'll sew from the stands."], ["them (pleased): I'm not in it! But I'll make you a victory dress if you win!"]], "entrant": [["them (pleased): I'm in the bracket! Ooh, I'll measure the arena floor while I'm at it!", "them: Don't cry if I win. The dresses are more fun to make."], ["them: We're both in it! Eeee! Let's make it a show!", "them (pleased): Give me a good fight to sew about!"], ["them (pleased): You and me in the bracket! My favourite plaything's in the final, teehee!", "them (pleased): Win it, and I'll make you a dress for the victory!"]], "out": [["them (pleased): Out already? Aww! Don't worry, I'll sew you a comfort blanket!"], ["them: You lost! Hah, you got beaten. Nui's still proud of you, though."], ["them (pleased): You're out, plaything. Come to the warehouse! I've got a new dress for you!"]], "champion": [["them (pleased): Champion! Eeee! I'll make the victory cape, right now!"], ["them (pleased): You won! I'm sewing your name into a dress!"], ["them (pleased): Champion, {player}! My favourite plaything, forever and ever!"]], "duel": [["them (pleased): Our round! Hold still, I'm measuring you with my eyes!", "them: Let's make this a good fight, plaything!"], ["them (pleased): Round time! Teehee, let's go!", "them: Don't pop a seam, okay?"], ["them (pleased): Our round, {player}! Win or lose, I'll make your dress anyway!"]]},
            "mid": {"1": ["them (pleased): Ooh, you're interesting! Let me pin you up for a fitting.", "them: Hm! Your measurements look promising. Stand still.", "them: I never invite people to the warehouse. You're special.", "them (pleased): Do you like my dresses? I made them all myself.", "them: Quiet, please. I'm concentrating on the stitching."], "3": ["them (pleased): You don't flinch when I hold the scissors. I like that!", "them: The dolls are lonely without company. You're good company.", "them (pleased): Come try on the new coat. It's almost perfect.", "them: Lady Ragyo would approve of you. Probably.", "them (pleased): You make the warehouse feel warm, somehow."], "5": ["them (pleased): {player}, my favourite plaything. Forever and ever, teehee!", "them: I'd sew you a dress for every day, if you let me.", "them (pleased): Come to the warehouse at night. I'll show you my best work.", "them: You're the only one who asks me about the stitching. It means a lot.", "them (pleased): Best friend! Let's make something beautiful together!"]},
            "hello_steps": [["them (pleased): Ooh! A new toy? Hiii~!", "them (pleased): Hi~! Hold still while I measure you!"], ["them (pleased): Hello~! Did you come to be a doll?", "them (pleased): Ooh, look at this one! So many possibilities!"], ["them (pleased): Yay, it's you! Nui's favourite plaything is back~!", "them (pleased): {player}~! Want to see my new sewing kit?"], ["them (pleased): Eeee! {player}, come here, come here!", "them (pleased): {player}! I've been sewing all day. Want to see?"], ["them (pleased): {player}! Nui missed you SO much~! Come here!", "them (pleased): {player}~! Hold still, I need your measurements!"], ["them (pleased): {player}! My favourite friend in the whole world~!", "them (pleased): {player}! You're my best doll. Come in!"]],
            "bye_steps": [["them (pleased): Bye-byeee~!", "them (pleased): Bye~! Don't come apart!"], ["them (pleased): Go~! Don't tear your seams!", "them (pleased): Bye, bye! Stay pretty~!"], ["them (pleased): Don't come apart at the seams while Nui's away~!", "them (pleased): Bye, {player}~! Come back soon!"], ["them (pleased): Come back soon or Nui will come find you~!", "them (pleased): Bye, {player}! Keep your measurements up to date!"], ["them (pleased): Come back soon, {player}~! Nui will sew you a new coat!", "them (pleased): Go, {player}! Nui will be lonely without you!"], ["them (pleased): Come back soon, best doll! Teehee!", "them (pleased): Bye, {player}~! My favourite. Don't let anyone else sew you!"]],
            "hello": ["them (pleased): Ooh! A new toy? Hiii~!", "them (pleased): Yay, it's you! Nui's favourite plaything is back~!", "them (pleased): Eeee! Nui missed you SO much~! Come here, come here!"],
            "bye": ["them (pleased): Bye-byeee~!", "them (pleased): Don't come apart at the seams while Nui's away~!", "them (pleased): Come back soon or Nui will come find you~! Teehee!"],
            "hi": ["them (pleased): Hiii~! I'm Nui Harime! Let's play, okay? Nui promises to be gentle! ...Maybe!",
                   "them (pleased): Ooh, a new friend! Can I sew a little bow on you? Pretty please?"],
            "hi2": "them (pleased): {player}~! Nui missed you! Did you miss Nui? You did! Yay!",
            "hi4": "them (pleased): You're Nui's favourite! Nui won't even cut you to ribbons! Isn't that sweet?",
            "again": "them (pleased): Back again~! You must really like Nui!",
            "loved": "them (pleased): Kyaa~! So cute! Just like Nui!",
            "disliked": "them (dismayed): Calm? Boring! Nui hates boring! Booooring!",
            "before": "them (pleased): Let's play dress-up! You're the doll!",
            "won": "them (dismayed): Aww! You're no fun! ...Again! Again again again!",
            "lost": "them (pleased): Hehe~! Snip snip!",
            "r1": "them (pleased): You didn't run away! Nui likes that! Most people run!",
            "r3": "them: Nui was made by Lady Ragyo. Nui can't close her eye. Nui doesn't feel things like people. Is that weird?",
            "r4": "them (pleased): Nui wants to keep you forever! In a nice way! Probably!",
        },
        friend=["background crimson", "me enters right with pop", "me: Ta-da! Nui made you a present!",
                "player: A... ribbon?", "me (pleased): A friendship ribbon! Nui sewed it herself!",
                "me: Nui doesn't have friends. Nui has toys. You're not a toy, though. You talk back!",
                "me: So you're a friend! Nui decided!", "me spins"],
        best=["background night", "me enters center with fade", "me: Nui was made, not born. Lady Ragyo made Nui to be perfect.",
              "me: Perfect dolls don't need anyone.", "me (dismayed): But Nui keeps coming to find you.",
              "player: Maybe you're more than a doll, Nui.", "me: ...More than a doll?",
              "choice", "- You're my friend, Nui.", "- You can choose who you are.",
              "me (pleased): Best friend! Nui will sew it into her heart! Ehehe~! Don't tell Lady Ragyo!"]),

    cpu("Ragyo Kiryuin", "villain", quests=RAGYO_KIRYUIN_QUESTS, extra_scenes=RAGYO_KIRYUIN_SCENES,
        haunts=[("warehouse", "wk", "23", 65), ("rooftop", "we", "3", 50), ("library", "135", "1", 30, 2)],
        tastes=(["fancy"], ["flowers"], ["sporty"]),
        lines={
            "repeat": {"future": ["them: Next I shall visit the library. Clothing history needs study.", "them (pleased): Tomorrow I shall examine your fibres. Be still.", "them (pleased): Tonight I shall tell you about the family. Sit closer."], "past": ["them: Earlier I wore a new coat. It suits me, as all my coats do.", "them (pleased): This morning I disciplined a servant. The family must be obeyed.", "them (pleased): Earlier I spoke to Nui about her dresses. She is a fine artisan."], "like": {"with": "Nui Harime", "lines": ["them: You're nothing like Nui. She is too cheerful for her own good.", "them: You're a bit like Nui. Skilled, perhaps, if you apply yourself.", "them (pleased): You're like Nui, {player}. A fine artisan, and loyal to the family."]}, "dislike": {"with": "Satsuki Kiryuin", "lines": ["them: You're so much like Satsuki. Defiant, and unpleasant to me.", "them: There's a trace of Satsuki in you. Correct it.", "them (pleased): You're nothing like Satsuki, {player}. A relief for the family."]}},
            "tournament": {"spectator": [["them: The tournament is beneath the family. I watch only for the clothing."], ["them: I do not enter such contests. I observe the fibres."], ["them (pleased): I do not compete. I shall attend your final, child."]], "entrant": [["them: I have entered. Clothing is always victorious.", "them: Do not embarrass the family's name in the bracket."], ["them: We are both in this bracket. Interesting.", "them (pleased): Show me the strength of your fibres."], ["them (pleased): You and I in the same bracket. The family's future rests on it."]], "out": [["them: You have failed. The fibres did not hold."], ["them: Defeat. Return to the warehouse and learn."], ["them (pleased): You're out. Come into the light. We will discuss your clothing."]], "champion": [["them (pleased): You have won. The clothing is pleased, and so am I."], ["them (pleased): Champion. The family shines a little brighter because of you."], ["them (pleased): Champion, {player}. You have a place in the family."]], "duel": [["them: The round begins. Stand straight, and do not disappoint me.", "them: Show me your fibres."], ["them: Round time. Obey the rules of the arena.", "them (pleased): Do not hold back. The family does not reward mercy."], ["them (pleased): Our round, {player}. I would rather you stood with the family than against it."]]},
            "mid": {"1": ["them: You're a passable specimen. Stand up straight.", "them: Hm. You're not entirely useless. Good.", "them: The clothing I wear is alive, like you. Remember that.", "them: Sit, and listen. Don't interrupt.", "them: You may ask one question. Make it intelligent."], "3": ["them (pleased): You're one of the few who doesn't flinch at the light.", "them: Satsuki is becoming difficult. I need you to watch her for me.", "them (pleased): Come to the library. I'll show you a new fibre.", "them: You are useful to the family. Remember that.", "them (pleased): You shine a little when you agree with me. How charming."], "5": ["them (pleased): {player}, my most loyal child. The family is stronger with you.", "them: You're the only one I'd trust with my secrets.", "them (pleased): Come into the warehouse. Let's discuss the family's future.", "them: I want you beside me when the true clothing is revealed.", "them (pleased): Best friend. Welcome home, always. Never leave the light."]},
            "hello_steps": [["them: What a drab little thing you are.", "them: Hm. Stand still. Let me look at you."], ["them: Ah, you. You dress a touch better today.", "them: Come closer. I want to see the stitching."], ["them (pleased): Come into the light, {player}. Let me look at you.", "them (pleased): {player}. You're improving. Sit."], ["them (pleased): {player}. Good. Come here. I want to talk about your clothing.", "them (pleased): {player}. I'm glad you came. We have much to discuss."], ["them (pleased): {player}. Come into the light, little one. You shine today.", "them (pleased): {player}. Sit by me. The family misses you."], ["them (pleased): {player}. You're the one I'd trust with the family's secrets.", "them (pleased): {player}. Welcome home. Stay as long as you like."]],
            "bye_steps": [["them: Leave.", "them: Go. You're wasting my light."], ["them: You may go.", "them: Off with you. Mind your posture."], ["them: Go, {player}. You may leave.", "them: Bye, {player}. Don't wear anything drab."], ["them (pleased): Go. Return to me shining, {player}.", "them (pleased): Bye, {player}. Come back to the warehouse soon."], ["them (pleased): Go, {player}. Return to me, shining.", "them (pleased): Bye, {player}. Come back soon, my little one."], ["them (pleased): Go, {player}. Return to me, and bring Satsuki if you can.", "them (pleased): Farewell, {player}. The family is stronger with you in it."]],
            "cold": "them (dismayed): My daughter chose rebellion. She'll find no welcome in this house.",
            "hello": ["them: What a drab little thing you are.", "them: Ah, you. You dress a touch better today.", "them (pleased): Come into the light, little one. Let me look at you."],
            "bye": ["them: Leave.", "them: You may go.", "them (pleased): Go. Return to me shining."],
            "hi": ["them: Welcome, little one. Clothes are what make you human. Let me look at you.",
                   "them: Ah, a stray. How charming. Do you know whom you address?"],
            "hi2": "them (pleased): You return to my presence. How delightfully foolish.",
            "hi4": "them (pleased): Come, sit beside me. I permit it. Few are permitted.",
            "again": "them: Again? Your devotion is noted.",
            "loved": "them (pleased): Exquisite. You have an eye for luxury.",
            "disliked": "them (dismayed): Sportswear. How utterly common.",
            "before": "them: Life Fibers sync! ...Or cards. It matters not. You will lose.",
            "won": "them (dismayed): Insolent. ...Impressive. Insolent.",
            "lost": "them (pleased): Naked before me, as all humans are.",
            "r1": "them: You do not grovel. How unusual. How interesting.",
            "r3": "them: I gave my body to the Life Fibers long ago. Humanity is a garment I wear. Do you understand?",
            "r4": "them: Even I can learn, it seems. You have taught me something. I do not enjoy admitting it.",
        },
        friend=["background castle", "me enters center with fade", "me: Do you know why I wear these clothes? To show I am above you.",
                "me: Yet you speak to me as if we were the same.", "player: Aren't we?",
                "me (dismayed): ...No one has ever dared suggest it.", "me: Perhaps that is why I let you stay.",
                "me (pleased): You may call yourself my friend. Do not abuse it."],
        best=["background crimson", "me enters center with fade", "me: My daughters despise me. Rightly, perhaps.",
              "me: I chose the Life Fibers over them. Over humanity. Over myself.",
              "player: You can still choose something else.", "me (dismayed): After all I've done?",
              "player: After all you've done.", "me: ...You are a strange child.",
              "choice", "- I'm your friend, Ragyo.", "- It's not too late.",
              "me (pleased): Best friend. How... human of me. I find I don't hate it."]),

    cpu("Ryuko Matoi", "friendly", quests=RYUKO_MATOI_QUESTS, extra_scenes=RYUKO_MATOI_SCENES,
        haunts=[("arena", "wk", "12", 55), ("alley", "we", "23", 40), ("plaza", "135", "1", 35)],
        tastes=(["food"], ["cool", "sporty"], ["fancy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to fight the dummies at the arena. Watch out.", "them (pleased): Tomorrow Senketsu wants to go shopping. Come help me carry bags.", "them (pleased): Tonight I'm going to the alley. Come if you're not scared of the dark."], "past": ["them: Earlier I got yelled at by Senketsu. He's been awful.", "them (pleased): This morning I ate three breakfasts. Don't judge me.", "them (pleased): Earlier I talked about my dad. It was hard, but okay."], "like": {"with": "Satsuki Kiryuin", "lines": ["them: You're nothing like Satsuki. She'd have made me take my uniform off by now.", "them: You're a bit like Satsuki. Tough, and kind of scary, honestly.", "them (pleased): You're like Satsuki, {player}, but nicer. That's the best I can say."]}, "dislike": {"with": "Ragyo Kiryuin", "lines": ["them: You're so much like Ragyo. You're all about the clothes, aren't you?", "them: There's a trace of Ragyo in you. Watch that.", "them (pleased): You're nothing like Ragyo, {player}. Good. I'd hate that."]}},
            "tournament": {"spectator": [["them: The tournament? I'm not in it, but I'll watch from the back."], ["them: Not in the bracket. Senketsu's already bored of watching, though."], ["them (pleased): I'm not in it, but I'll be yelling your name when you win!"]], "entrant": [["them: I'm in the bracket! Senketsu's ready, so watch out!", "them: Don't go easy on me, okay? I'm not a baby!"], ["them: We're both in it! This is gonna be awesome!", "them (pleased): Let's make the crowd lose their minds!"], ["them (pleased): You and me in the bracket! Win it, and we'll share the victory!"]], "out": [["them: Out? Aww, that sucks. Come on, let's grab some food."], ["them: You lost. But you were tough. Senketsu says so too."], ["them (pleased): You're out. Come on, let's go get a snack and forget about it!"]], "champion": [["them (pleased): You won! Senketsu's super proud of you!"], ["them (pleased): Champion! You're tough, I'll give you that!"], ["them (pleased): Champion, {player}! Best friend of Senketsu forever!"]], "duel": [["them: It's our round! Let's go!", "them: No holding back, or Senketsu gets mad!"], ["them: Round time! Let's do this!", "them (pleased): Don't go easy on me!"], ["them (pleased): Our round, {player}! I don't want to beat you, but I'm gonna try!"]]},
            "mid": {"1": ["them: Yeah? You look like you could handle a fight. Good.", "them: You're not scared of Senketsu, are you? He's a bit loud.", "them: Don't mind my uniform. It's got opinions.", "them: Hey, you're alright. Don't ruin it.", "them: Want to spar? I'll go easy. A little."], "3": ["them (pleased): You stuck around even when Senketsu was being rude. That's cool.", "them: I'm getting closer to finding the other half of the blade. Thanks for helping.", "them (pleased): Come to the alley, I'll show you where I found the clue.", "them: You're the one I'd want at my back in any fight.", "them (pleased): Senketsu says you're good people. I agree."], "5": ["them (pleased): {player}! You're my best friend, and Senketsu's, too.", "them: When I find my father's killer, I want you to be the first to know.", "them (pleased): Let's go to the arena. Show me your best move, and I'll show you mine.", "them: You never gave up on me, even when I was a total mess.", "them (pleased): Best friend! Don't let anyone push you around, ever!"]},
            "hello_steps": [["them: Yeah? Whaddaya want?", "them: Hey. Is that a new jacket?"], ["them: Oh, hey. Didn't see you there.", "them: Hi. You look like you fight. Good."], ["them (pleased): Hey, {player}! Good timing, I was gettin' bored.", "them (pleased): {player}! Senketsu, look who it is!"], ["them (pleased): {player}! Senketsu says hi, by the way.", "them (pleased): {player}! C'mon, let's go do somethin' fun."], ["them (pleased): There ya are, {player}! C'mon, let's go do somethin'!", "them (pleased): {player}! Got a fight in mind, or just a chat?"], ["them (pleased): {player}! My best friend. Senketsu agrees, too.", "them (pleased): {player}! Come on, I'll show you the new move."]],
            "bye_steps": [["them: Later.", "them: See ya. Don't get hit."], ["them: Bye. Don't do anything dumb.", "them: Later, alright?"], ["them (pleased): See ya, {player}! Don't let anybody push ya around!", "them (pleased): Bye, {player}! Watch your back!"], ["them (pleased): Go on, {player}! Come back soon.", "them (pleased): Bye, {player}! Don't let the uniform get you in trouble!"], ["them (pleased): Come back soon, alright? I'll be around, {player}.", "them (pleased): See ya, {player}! Senketsu will miss you."], ["them (pleased): Come back soon, best friend! I'll be waiting, Senketsu too.", "them (pleased): Bye, {player}! Don't go gettin' yourself killed."]],
            "hello": ["them: Yeah? Whaddaya want?", "them (pleased): Hey, {player}! Good timing, I was gettin' bored.", "them (pleased): There ya are! C'mon, let's go do somethin'."],
            "bye": ["them: Later.", "them (pleased): See ya! Don't let anybody push ya around!", "them (pleased): Come back soon, alright? I'll be around."],
            "hi": ["them: Ryuko Matoi. I'm lookin' for whoever killed my dad. Seen anyone with half a scissor blade?",
                   "them: You wanna fight? Senketsu's itchin' for it."],
            "hi2": "them (pleased): Yo, {player}! Mako's family made too many croquettes. Want some?",
            "hi4": "them (pleased): You're the real deal. Don't let anyone tell you different.",
            "again": "them: Back again? Cool.",
            "loved": "them (pleased): Croquettes! Mystery croquettes! Just like Mako's mom makes!",
            "disliked": "them (dismayed): A fancy dress? Senketsu's gonna be jealous. And I'm gonna be itchy.",
            "before": "them: Senketsu! Let's show 'em what we've got!",
            "won": "them (dismayed): Damn. Okay. You got me. One more?",
            "lost": "them (pleased): Hell yeah!",
            "r1": "them: You're alright. Not a jerk. I can work with that.",
            "r3": "them: I found out I'm not even fully human. Freaked me out. You didn't even blink.",
            "r4": "them (pleased): You and Mako. My people. Nobody touches my people.",
        },
        friend=["background city", "me enters left with slide", "me: Senketsu says you're alright. He doesn't say that about anyone.",
                "player: Your uniform talks?", "me: Yeah. Long story. Don't make it weird.",
                "me (pleased): Look, I don't have a lot of friends. Mako, Senketsu. Now you.",
                "me: So let's get some food. Friend stuff."],
        best=["background crimson", "me enters center with fade", "me: You know I'm part Life Fiber, right? Made by the same stuff as Ragyo.",
              "me (dismayed): Sometimes I wonder if I'm a person at all.",
              "player: You're the most real person I know, Ryuko.", "me: ...Yeah?",
              "player: Yeah.", "me: Mako said that too. She screamed it, actually.",
              "choice", "- You're human where it counts.", "- I'm proud of you.",
              "me (pleased): Best friend. Heh. Senketsu, you hear that? We've got another one."]),

    cpu("Satsuki Kiryuin", "aloof", quests=SATSUKI_KIRYUIN_QUESTS, extra_scenes=SATSUKI_KIRYUIN_SCENES,
        haunts=[("school", "wk", "01", 60), ("rooftop", "we", "23", 40), ("arena", "135", "2", 35)],
        tastes=(["calm"], ["fancy", "book"], ["cute"]),
        lines={
            "repeat": {"future": ["them: Next I shall inspect the academy's grounds. Stay in line.", "them (pleased): Tomorrow I shall plan the next strategy. You will hear it.", "them (pleased): Tonight I shall consider my mother's position. You may listen."], "past": ["them: Earlier I dismissed a student for being late. Discipline matters.", "them (pleased): This morning I reviewed the rebellion's papers. Everything is in order.", "them (pleased): Earlier I spoke with Ryuko. She is a worthy rival, I think."], "like": {"with": "Ryuko Matoi", "lines": ["them: You're nothing like Ryuko. She is far too impulsive.", "them: You're a bit like Ryuko. Impulsive, but with potential.", "them (pleased): You're like Ryuko, {player}, but with discipline. A fine ally."]}, "dislike": {"with": "Ragyo Kiryuin", "lines": ["them: You're so much like my mother. Ambitious at any cost.", "them: There's a trace of Ragyo in you. I won't tolerate it.", "them (pleased): You're nothing like my mother, {player}. That is why I trust you."]}},
            "tournament": {"spectator": [["them: The tournament is a distraction. I do not enter distractions."], ["them: Not in the bracket. The academy requires my attention elsewhere."], ["them (pleased): I am not entering. I expect you to win, and to report back."]], "entrant": [["them: I am in the bracket. I expect to win, and so should you.", "them: Do not waste the academy's time."], ["them: We are both in the bracket. Good. I like a worthy opponent.", "them (pleased): Let us make this match a real test."], ["them (pleased): You and I in the same bracket. Win it, and we'll discuss the rebellion after."]], "out": [["them: You are out. Hm. It is a lesson. Learn from it."], ["them: You lost. The academy does not reward defeat. But I see your effort."], ["them (pleased): You are out. Come with me to the rooftop. We will talk about the future."]], "champion": [["them (pleased): Champion. The academy honours you."], ["them (pleased): You won. I am... impressed. Do not repeat that."], ["them (pleased): Champion, {player}. A true ally of Honnouji Academy."]], "duel": [["them: The round begins. Do not disappoint the academy.", "them: Show me you are worth my time."], ["them: Round time. Give me everything.", "them (pleased): I will not hold back. I expect the same from you."], ["them (pleased): Our round, {player}. I would rather you stood with me. But the bracket is the bracket."]]},
            "mid": {"1": ["them: You've earned a few minutes of my time. Use them well.", "them: I don't hand out trust. You haven't earned it, yet.", "them: The academy's rules are strict. You're learning them.", "them: Hm. You're more useful than I first thought.", "them: Ask one question. I will answer, with precision."], "3": ["them (pleased): You're one of the few I'd stand beside in the rebellion.", "them: My mother's plans are tyrannical. You're one of the few who sees it.", "them (pleased): Come to the rooftop. We'll discuss the future of Honnouji.", "them: You're earning my respect, slowly. Keep at it.", "them (pleased): I trust you enough to tell you a secret. Don't repeat it."], "5": ["them (pleased): {player}, my ally, my friend. You're the only one I'd stand with.", "them: When the rebellion comes, I want you by my side, as an equal.", "them (pleased): Let's go up to the rooftop. The city looks different with you here.", "them: You're the one who makes me want to be more than a weapon.", "them (pleased): Best friend. Stand with me. Always. That's an order I'd like you to take."]},
            "hello_steps": [["them: State your business.", "them: Hm. You're on time, at least."], ["them: You may approach.", "them: Ah. Stand straight, please."], ["them: You may approach, {player}.", "them: {player}. Sit. We have something to discuss."], ["them (pleased): {player}. Good. Stand with me a moment.", "them (pleased): {player}. You're improving. I noticed."], ["them (pleased): {player}. Good. Stand with me, and watch the city.", "them (pleased): {player}. I'm glad you came. Honestly."], ["them (pleased): {player}. The one ally I'd stand beside without fear.", "them (pleased): {player}. Sit. Tell me what you've seen today."]],
            "bye_steps": [["them: Dismissed.", "them: Go. Be prompt next time."], ["them: Go. Remain human.", "them: You may leave."], ["them: Go, {player}. Remain human.", "them: Dismissed, {player}. Be prompt."], ["them (pleased): Return soon. That is not a request, {player}.", "them (pleased): Go, {player}. Keep your guard up."], ["them (pleased): Return soon, {player}. The city is quieter without you.", "them (pleased): Go, {player}. I'll expect you back at the rooftop."], ["them (pleased): Return soon. Stand with me again, {player}.", "them (pleased): Go, {player}. You are my one true ally. Return."]],
            "cold": "them: Mother won. Then I'm no longer your ally. Stay out of my way.",
            "hello": ["them: State your business.", "them: You may approach.", "them (pleased): {player}. Good. Stand with me a moment."],
            "bye": ["them: Dismissed.", "them: Go. Remain human.", "them (pleased): Return soon. That is not a request."],
            "hi": ["them: I am Satsuki Kiryuin. Show me whether you are human, or a pig in human clothing.",
                   "them: You stand before the president of Honnouji Academy. Stand straight."],
            "hi2": "them: {player}. You've returned. Your posture's improved.",
            "hi4": "them (pleased): Sit. We'll have tea. I insist.",
            "again": "them: Again. Your resolve is noted.",
            "loved": "them (pleased): A fine tea set. You understand discipline.",
            "disliked": "them (dismayed): ...A plushie. I see. Iori would find this amusing.",
            "before": "them: Fear is freedom! Subjugation is liberation! Contradiction is truth! Begin.",
            "won": "them (dismayed): You've shown me you're human. Well done.",
            "lost": "them: You have potential. You simply haven't earned it yet.",
            "r1": "them: You don't kneel, and you don't run. Good.",
            "r3": "them: I've plotted against my mother since I was a child. Every word, every move. I've never had a friend. Only allies.",
            "r4": "them (pleased): When this war ends, I'd like to learn what friendship is. With you, if you'd allow it.",
        },
        friend=["background castle", "me enters right with fade", "me: Every person in this academy serves a purpose. Even me.",
                "me: You serve no purpose here. And yet I keep finding time for you.", "player: Maybe that's the purpose.",
                "me (pleased): ...Perhaps.", "me: You've earned my respect. More than that. Friendship.",
                "me: I don't offer it lightly. Accept it properly."],
        best=["background night", "me enters center with fade", "me: My whole life has been a plan to defeat my mother.",
              "me: I sacrificed my childhood. My sister. My heart.", "player: You're more than a plan, Satsuki.",
              "me (dismayed): I'm not sure I know who I am without it.",
              "player: Then let's find out together.", "me: ...Together.",
              "choice", "- You're my best friend.", "- You don't have to carry it alone.",
              "me (pleased): Best friend. I accept. And I'll guard it with everything I have."]),
]

ARRIVALS = [
  {
    "newcomer": "Denji",
    "name": "World: Arrival, Denji",
    "lines": [
      "background sakura",
      "me enters left with slide",
      "me: Yo. Is anyone giving out free food? Anyone at all?",
      "me (dismayed): ...Okay, no free food. That's fine. I'll find some. I always do.",
      "me: You look like someone with a sandwich. Just saying.",
      "player: Do you give him something to eat?",
      "choice What do you do?",
      "- Tell Denji the sandwich is his, and he owes you a favour. (set side_me)",
      "- Tell him the free food's in the cafe, and he should follow you. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Power",
    "name": "World: Arrival, Power",
    "lines": [
      "background sakura",
      "me enters center with zoom",
      "me: Hah! This town is Power's now! Power claims it, from the plaza to the sky!",
      "me (dismayed): ...Power is not impressed by the sky. Power is impressed by you. A little.",
      "me: Bow, human. Power has arrived.",
      "player: Power wants the whole town. Do you let her have it?",
      "choice How do you answer?",
      "- Tell Power the town is shared, and she should stop shouting. (set side_me)",
      "- Tell Power you'll bow, if she shares the snacks. (set side_me, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Aki Hayakawa",
    "name": "World: Arrival, Aki Hayakawa",
    "lines": [
      "background rooftop",
      "me enters right with fade",
      "me: I'm not going to say anything. Just sit down and smoke with me, or don't.",
      "me (dismayed): ...You're staring. It's okay. I'm not used to people watching me.",
      "me: The Fox Devil's price is not something I talk about. Not yet.",
      "player: He hasn't said a word for a while. Do you break the silence?",
      "choice What do you say?",
      "- Tell Aki he's bad company, and go back to the stairs. (set side_me)",
      "- Tell Aki you'll sit quietly, as long as he likes. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Makima",
    "name": "World: Arrival, Makima",
    "lines": [
      "background rooftop",
      "me enters center with fade",
      "me: Hello. I know your name. I've been waiting for you to arrive.",
      "me (pleased): Don't be frightened. I only want to help you be a good dog.",
      "me: Sit. There, that's better. Now, what would you like to talk about?",
      "player: She already knows your name. Are you comfortable with that?",
      "choice What's your response?",
      "- Tell Makima you'd rather she didn't use your name, and walk away. (set side_me)",
      "- Tell Makima you're happy to talk, and see where it goes. (set side_me, give climax_pack)"
    ]
  },
  {
    "newcomer": "Beast Titan",
    "name": "World: Arrival, Beast Titan",
    "lines": [
      "background forest",
      "me enters left with drop",
      "me: Oh, sorry. Did my ball go over the trees? Would you mind fetching it?",
      "me (pleased): Thank you! You're very polite. That's a good quality in a person.",
      "me: Tom Ksaver used to fetch for me. I miss those afternoons.",
      "player: He wants you to fetch the ball. Do you go?",
      "choice How do you respond?",
      "- Tell him the ball is his problem, and walk off. (set side_me)",
      "- Go and fetch the ball, and bring it back to him with a smile. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Eren",
    "name": "World: Arrival, Eren",
    "lines": [
      "background arena",
      "me enters right with slide",
      "me: I've been training since dawn. My hands are bleeding, but I don't care.",
      "me (dismayed): Don't look at my hands. They'll heal. They always do.",
      "me: If you want to fight, do it now. I'm not stopping until the sun goes down.",
      "player: His hands are bleeding. Do you bandage them, or let him keep going?",
      "choice What do you do?",
      "- Tell Eren to stop, because his hands are a mess. (set side_me)",
      "- Bandage his hands, and tell him he can keep training after. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Levi",
    "name": "World: Arrival, Levi",
    "lines": [
      "background cafe",
      "me enters center with fade",
      "me: Hm. Dust on the windowsill. Who runs this place?",
      "me (dismayed): Tch. Fine. I'll sit, as long as nobody touches my cup.",
      "me: You wiped your table, I hope? Good. Keep it that way.",
      "player: He's inspecting the cafe before sitting. Do you wipe the table for him?",
      "choice What do you say?",
      "- Tell Levi the cafe's dirty, and he can clean it himself. (set side_me)",
      "- Wipe the table for him, and pour him a fresh cup. (set side_me, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Mikasa",
    "name": "World: Arrival, Mikasa",
    "lines": [
      "background arena",
      "me enters left with fade",
      "me: Excuse me. Have you seen a boy with green eyes? He's around here somewhere.",
      "me (dismayed): He's not a threat. Just tell me if you've seen him. Please.",
      "me: I'll look for him in the arena. He's always training there.",
      "player: She's looking for a boy with green eyes. Do you help her search?",
      "choice What's your response?",
      "- Tell Mikasa you haven't seen anyone, and let her keep looking alone. (set side_me)",
      "- Tell Mikasa you'll help her search, and check the arena with her. (set side_me, give climax_pack)"
    ]
  },
  {
    "newcomer": "Nui Harime",
    "name": "World: Arrival, Nui Harime",
    "lines": [
      "background ruins",
      "me enters right with pop",
      "me: Hi! I'm sewing a doll of someone you know. Who? That's a surprise, teehee!",
      "me (pleased): Do you want to be measured? You'd make a lovely doll, probably.",
      "me: Hold still, I'll just take a little measurement. It won't hurt. Much.",
      "player: A doll of someone you know. Do you let her measure you?",
      "choice What do you say?",
      "- Tell Nui you'd rather not be measured, and walk out. (set side_me)",
      "- Let Nui measure you, and tell her the doll will be beautiful. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Ragyo Kiryuin",
    "name": "World: Arrival, Ragyo Kiryuin",
    "lines": [
      "background ruins",
      "me enters center with fade",
      "me: The lights are dimming. That's just me. I'm glowing, a little, for the family.",
      "me (pleased): Come closer. Let me see your clothing. It's a family matter.",
      "me: Satsuki is becoming difficult. I'll need your help with her, in time.",
      "player: The lights go out when she enters. Do you come closer?",
      "choice What's your response?",
      "- Tell Ragyo the lights are a bit much, and she should turn them on. (set side_me)",
      "- Step closer, and offer to help the family, in time. (set side_me, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Ryuko Matoi",
    "name": "World: Arrival, Ryuko Matoi",
    "lines": [
      "background arena",
      "me enters center with pop",
      "me: Senketsu, stop it! Okay, I'm talking to my uniform. Don't judge me.",
      "me (dismayed): He says you look weird. I'm sorry. He's really loud, you know.",
      "me: Hey, you're new here, right? You want to fight, or just talk to a uniform?",
      "player: She's talking to her uniform. Do you join the conversation?",
      "choice How do you respond?",
      "- Tell Ryuko she should stop talking to the uniform, and get some sleep. (set side_me)",
      "- Tell Senketsu you like him, and let Ryuko laugh. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Satsuki Kiryuin",
    "name": "World: Arrival, Satsuki Kiryuin",
    "lines": [
      "background classroom",
      "me enters left with slide",
      "me: I am taking over the student council by noon. This school requires discipline.",
      "me (pleased): You will be assessed. Three questions. Answer quickly.",
      "me: Do not be late. Lateness is weakness, and I do not tolerate weakness.",
      "player: She's taking over the council by lunchtime. Do you answer her questions?",
      "choice What's your answer?",
      "- Tell Satsuki she can't run the school, and walk out of the room. (set side_me)",
      "- Answer her three questions, and see what she does with the answers. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Denji",
    "name": "World: Arrival, Denji & Megumin",
    "lines": [
      "cast megumin as Megumin",
      "background sakura",
      "me enters left with slide",
      "megumin enters right with fade",
      "megumin: Denji! Do you want to see my explosion? It's the best one in town!",
      "me (pleased): Explosion? Do you have any food for after? Please say yes.",
      "megumin (pleased): Hah! I'll blow up a donut for you, if you carry me home.",
      "player: Two very simple dreams. Do you back Denji's food, or Megumin's explosion?",
      "choice Who do you side with?",
      "- Tell Denji the food is worth more than the explosion, and he should eat. (set side_me)",
      "- Tell Megumin the explosion is great, and she should show it off. (set side_megumin, give color_pack)"
    ]
  },
  {
    "newcomer": "Denji",
    "name": "World: Arrival, Denji & Power",
    "lines": [
      "cast power as Power",
      "background sakura",
      "me enters left with slide",
      "power enters right with fade",
      "power: Human! Power is here to rule this plaza. You should bow, and share your food.",
      "me (dismayed): Power? You're the one who ate my donut yesterday? Hah, no way!",
      "power (dismayed): Power did not eat the donut! It was... stolen. By a bird.",
      "player: They arrive together, arguing. Whose side are you on?",
      "choice Who do you back?",
      "- Tell Power the donut is Denji's, and she should give it back. (set side_me)",
      "- Tell Denji the bird took it, and he should forgive Power. (set side_power, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Power",
    "name": "World: Arrival, Power & Denji",
    "lines": [
      "cast denji as Denji",
      "background sakura",
      "me enters left with slide",
      "denji enters right with fade",
      "denji: Hey! Is that Power? You were the one who took the last donut, right?",
      "me (dismayed): Power did not take it! It was stolen. By a bird. Denji, you fool!",
      "denji (pleased): Ha! Okay, but I'm still hungry. Let's get food together, Power.",
      "player: They arrive together, arguing. Whose side are you on?",
      "choice Who do you back?",
      "- Tell Denji the donut is his to chase, and Power should admit she took it. (set side_me)",
      "- Tell Power the bird is to blame, and Denji should share. (set side_denji, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Power",
    "name": "World: Arrival, Power & Kyoko Sakura",
    "lines": [
      "cast kyoko as Kyoko Sakura",
      "background cafe",
      "me enters left with slide",
      "kyoko enters right with fade",
      "kyoko: Power, is it? I have an apple. Want to fight for it?",
      "me (dismayed): Power does not fight over apples! Power only fights for honour!",
      "kyoko (pleased): Honour? Okay, then the apple's yours if you can catch it.",
      "player: A food fight, from the first apple. Which side are you on?",
      "choice Who do you back?",
      "- Tell Power the apple is beneath her, and she should walk away. (set side_me)",
      "- Tell Kyoko the fight is on, and Power should catch the apple. (set side_kyoko, give color_pack)"
    ]
  },
  {
    "newcomer": "Aki Hayakawa",
    "name": "World: Arrival, Aki Hayakawa & Denji",
    "lines": [
      "cast denji as Denji",
      "background rooftop",
      "me enters left with slide",
      "denji enters right with fade",
      "denji: Aki! You're on the roof again. Can I have a cigarette? Just one. Please?",
      "me (dismayed): No. Go eat your bread. You're not old enough to smoke, Denji.",
      "denji (pleased): I'm not a kid! I'm a devil hunter! Let me have a smoke!",
      "player: Babysitting Denji, on the rooftop. Do you back Aki, or Denji?",
      "choice Who do you side with?",
      "- Tell Aki he's right, and Denji should go home. (set side_me)",
      "- Tell Denji he's a hunter, and he deserves the smoke. (set side_denji, give color_pack)"
    ]
  },
  {
    "newcomer": "Aki Hayakawa",
    "name": "World: Arrival, Aki Hayakawa & Levi",
    "lines": [
      "cast levi as Levi",
      "background rooftop",
      "me enters left with slide",
      "levi enters right with fade",
      "levi: Hayakawa. I didn't expect you here. You look tired, like me.",
      "me (dismayed): Levi. You're not the only one tired of this town. Want a seat?",
      "levi (pleased): Tch. Fine. But don't smoke near me. The air's dirty enough.",
      "player: Two tired soldiers, the same look. Do you back Aki's silence, or Levi's rules?",
      "choice Who do you side with?",
      "- Tell Aki the smoke is fine, and Levi should relax. (set side_me)",
      "- Tell Levi the rooftop is clean, and Aki should put the cigarette away. (set side_levi, give color_pack)"
    ]
  },
  {
    "newcomer": "Makima",
    "name": "World: Arrival, Makima & Aki Hayakawa",
    "lines": [
      "cast aki as Aki Hayakawa",
      "background rooftop",
      "me enters left with slide",
      "aki enters right with fade",
      "aki: Makima. You're giving me orders again? I'm not your dog, you know.",
      "me (pleased): Aki, you're my most useful dog. Sit. The Gun Devil is waiting.",
      "aki (dismayed): ...Fine. But I'll do it my way, not your way.",
      "player: An order to her subordinate. Do you back the order, or Aki's way?",
      "choice Who do you side with?",
      "- Tell Makima the order is good, and Aki should follow it. (set side_me)",
      "- Tell Aki his way is better, and Makima should listen. (set side_aki, give climax_pack)"
    ]
  },
  {
    "newcomer": "Makima",
    "name": "World: Arrival, Makima & Albedo",
    "lines": [
      "cast albedo as Albedo",
      "background library",
      "me enters left with slide",
      "albedo enters right with fade",
      "albedo: Makima. I've heard about your control. It's very interesting.",
      "me (pleased): Albedo. You're the one who wants to control a whole world. How lovely.",
      "albedo (pleased): Perhaps we should compare notes. Two controllers, in one town.",
      "player: Two who want control, each politely. Who do you back?",
      "choice Who do you support?",
      "- Tell Makima that Albedo is a threat, and she should keep her distance. (set side_me)",
      "- Tell Albedo that Makima is worth watching, and she should talk to her. (set side_albedo, give color_pack)"
    ]
  },
  {
    "newcomer": "Beast Titan",
    "name": "World: Arrival, Beast Titan & Levi",
    "lines": [
      "cast levi as Levi",
      "background forest",
      "me enters left with slide",
      "levi enters right with fade",
      "levi: Zeke. I know what you're planning. Don't.",
      "me (pleased): Levi! You're here. I was going to throw a ball, but you look like you'd break it.",
      "levi (dismayed): Tch. You've got bad blood in you. I'm not forgetting Erwin.",
      "player: Bad blood. Do you let them throw, or stop the fight before it starts?",
      "choice Who do you side with?",
      "- Tell Zeke the forest is his, and Levi should leave. (set side_me)",
      "- Tell Levi the ball is harmless, and he should play catch. (set side_levi, give color_pack)"
    ]
  },
  {
    "newcomer": "Beast Titan",
    "name": "World: Arrival, Beast Titan & Lord Genome",
    "lines": [
      "cast lord as Lord Genome",
      "background forest",
      "me enters left with slide",
      "lord enters right with fade",
      "lord: The surface. It requires an ending. The world is too bright.",
      "me (pleased): You're right. We should end it, gently. Like a doctor.",
      "lord (dismayed): I shall decide the ending, not you. Do not get ahead of the king.",
      "player: Two who think the world needs ending. Do you back Zeke's gentle plan, or Genome's throne?",
      "choice Who do you side with?",
      "- Tell Lord Genome his throne is too much, and Zeke should stop. (set side_me)",
      "- Tell Zeke his plan is gentle, and Genome should listen. (set side_lord, give color_pack)"
    ]
  },
  {
    "newcomer": "Eren",
    "name": "World: Arrival, Eren & Mikasa",
    "lines": [
      "cast mikasa as Mikasa",
      "background arena",
      "me enters left with slide",
      "mikasa enters right with fade",
      "mikasa: Eren, you're bleeding again. Let me see your hands.",
      "me (dismayed): Don't fuss over me, Mikasa. I'm fine. I'm training.",
      "mikasa (dismayed): You're not fine. You've never been fine. Sit down.",
      "player: She wraps his hands, and he complains. Do you back Eren, or Mikasa?",
      "choice Who do you side with?",
      "- Tell Eren to let Mikasa help, and stop training for once. (set side_me)",
      "- Tell Mikasa to let Eren train, he needs it. (set side_mikasa, give climax_pack)"
    ]
  },
  {
    "newcomer": "Eren",
    "name": "World: Arrival, Eren & Giorno Giovanna",
    "lines": [
      "cast giorno as Giorno Giovanna",
      "background beach",
      "me enters left with slide",
      "giorno enters right with fade",
      "giorno: Eren. You chose the hard path. Why?",
      "me (dismayed): Because it's the only path left. I can't go back now.",
      "giorno (pleased): Then let's walk it together. Dreams are better shared.",
      "player: Two who chose the hard path. Who do you back?",
      "choice Who gets your support?",
      "- Tell Giorno his dream is too soft, and Eren should listen to Mikasa instead. (set side_me)",
      "- Tell Eren his path is brave, and Giorno should walk with him. (set side_giorno, give color_pack)"
    ]
  },
  {
    "newcomer": "Levi",
    "name": "World: Arrival, Levi & Erza Scarlet",
    "lines": [
      "cast erza as Erza Scarlet",
      "background cafe",
      "me enters left with slide",
      "erza enters right with fade",
      "erza: Levi. I've heard about your tea. Let's see if it's worth the reputation.",
      "me (dismayed): Erza. Your armour's on the table again. Put it on the floor.",
      "erza (pleased): Ha! You're as strict as ever. Let's have a duel over the tea.",
      "player: Two commanders, one tea. Who do you back?",
      "choice Who do you support?",
      "- Tell Erza her armour is a mess, and she should clean up. (set side_me)",
      "- Tell Levi his tea is good, and he should share it with Erza. (set side_erza, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Levi",
    "name": "World: Arrival, Levi & Eren",
    "lines": [
      "cast eren as Eren",
      "background arena",
      "me enters left with slide",
      "eren enters right with fade",
      "eren: Levi! You're going to yell at me for the bleeding again, aren't you?",
      "me (dismayed): Yes. Clean up the arena. And stop bleeding on the floor.",
      "eren (pleased): You're tough, but I'll keep going. That's the plan.",
      "player: Tough love, on the arena floor. Do you back Levi, or Eren?",
      "choice Who do you side with?",
      "- Tell Eren the arena is his responsibility, and Levi is right. (set side_me)",
      "- Tell Levi the training is Eren's choice, and he should respect it. (set side_eren, give color_pack)"
    ]
  },
  {
    "newcomer": "Mikasa",
    "name": "World: Arrival, Mikasa & Yor Forger",
    "lines": [
      "cast yor as Yor Forger",
      "background sakura",
      "me enters left with slide",
      "yor enters right with fade",
      "yor: Mikasa, right? You're very quiet, like me. Are you here for a job?",
      "me (dismayed): I'm looking for someone. And you're blushing. Why?",
      "yor (dismayed): I'm not blushing! It's the sun. Okay, it's a bit embarrassing.",
      "player: Two quiet killers, both blushing. Do you back Mikasa's search, or Yor's job?",
      "choice Who gets your support?",
      "- Tell Mikasa the job is more important, and she should focus on it. (set side_me)",
      "- Tell Yor the search is worth it, and she should help Mikasa. (set side_yor, give color_pack)"
    ]
  },
  {
    "newcomer": "Nui Harime",
    "name": "World: Arrival, Nui Harime & Ryuko Matoi",
    "lines": [
      "cast ryuko as Ryuko Matoi",
      "background ruins",
      "me enters left with slide",
      "ryuko enters right with fade",
      "ryuko: You! Nui Harime! I know your handiwork. Stop making dolls!",
      "me (pleased): Ryuko! Your uniform is so pretty. Can I sew it?",
      "ryuko (dismayed): Don't you dare touch Senketsu! Get out of the warehouse!",
      "player: Hatred at first sight. Who do you cheer for?",
      "choice Who do you side with?",
      "- Tell Nui the dolls are a crime, and she should stop sewing. (set side_me)",
      "- Tell Ryuko the uniform is special, and Nui should leave it alone. (set side_ryuko, give color_pack)"
    ]
  },
  {
    "newcomer": "Nui Harime",
    "name": "World: Arrival, Nui Harime & Joker",
    "lines": [
      "cast joker as Joker",
      "background ruins",
      "me enters left with slide",
      "joker enters right with fade",
      "joker: Nui! Your dolls are so creepy. Teehee, I love creepy.",
      "me (pleased): Joker! Your smile is terrifying. Do you want a doll too?",
      "joker (pleased): Ha! A doll of me? That would be a joke. A killer one.",
      "player: Two terrifying smiles. Do you back the sewing, or the joke?",
      "choice Who do you back?",
      "- Tell Nui the joke is cruel, and she should stop. (set side_me)",
      "- Tell Joker the doll is a fine joke, and he should try it. (set side_joker, give color_pack)"
    ]
  },
  {
    "newcomer": "Ragyo Kiryuin",
    "name": "World: Arrival, Ragyo Kiryuin & Satsuki Kiryuin",
    "lines": [
      "cast satsuki as Satsuki Kiryuin",
      "background ruins",
      "me enters left with slide",
      "satsuki enters right with fade",
      "satsuki: Mother. You are glowing in the warehouse again. Stop it.",
      "me (dismayed): Satsuki. You are defying the family. Obey, or leave.",
      "satsuki (dismayed): I will not obey. I will rebel. This family is broken.",
      "player: Mother and daughter. Do you stand with the family, or with Satsuki?",
      "choice Who do you side with?",
      "- Tell Satsuki the family is right, and she should come home. (set side_me)",
      "- Tell Ragyo the rebellion is real, and she should listen to her daughter. (set side_satsuki, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Ragyo Kiryuin",
    "name": "World: Arrival, Ragyo Kiryuin & DIO",
    "lines": [
      "cast dio as DIO",
      "background ruins",
      "me enters left with slide",
      "dio enters right with fade",
      "dio: Ragyo. You consider yourself a god, do you? Amusing.",
      "me (pleased): DIO. You consider yourself a god too. Let's see whose heaven is bigger.",
      "dio (pleased): Hah! Time will decide, Lady Ragyo. And I am not in a hurry.",
      "player: Two who consider themselves gods. Who do you back?",
      "choice Who do you support?",
      "- Tell DIO he's not a god, and Ragyo should keep her throne. (set side_me)",
      "- Tell Ragyo her heaven is the best, and DIO should bow. (set side_dio, give color_pack)"
    ]
  },
  {
    "newcomer": "Ryuko Matoi",
    "name": "World: Arrival, Ryuko Matoi & Satsuki Kiryuin",
    "lines": [
      "cast satsuki as Satsuki Kiryuin",
      "background arena",
      "me enters left with slide",
      "satsuki enters right with fade",
      "satsuki: Matoi. Your uniform is an insult to the academy. Take it off.",
      "me (dismayed): Make me, Satsuki! Senketsu isn't going anywhere!",
      "satsuki (pleased): Hmph. You are interesting. Perhaps we will fight, then.",
      "player: Rival sisters who don't know it yet. Do you back Ryuko, or Satsuki?",
      "choice Who do you side with?",
      "- Tell Satsuki the uniform's an insult, and Ryuko should take it off. (set side_me)",
      "- Tell Ryuko the uniform is special, and Satsuki should respect it. (set side_satsuki, give color_pack)"
    ]
  },
  {
    "newcomer": "Ryuko Matoi",
    "name": "World: Arrival, Ryuko Matoi & Toph",
    "lines": [
      "cast toph as Toph",
      "background arena",
      "me enters left with slide",
      "toph enters right with fade",
      "toph: Ryuko. You're the one who wanted a rematch. I can feel you clenching your fists.",
      "me (dismayed): Toph! I'm going to beat you this time! Get ready!",
      "toph (pleased): Ha! Bring your uniform and your big mouth. Let's see who's tougher.",
      "player: Rematch, again. Do you back Ryuko, or Toph?",
      "choice Who do you cheer for?",
      "- Tell Toph she's already beaten Ryuko, and she should stop bragging. (set side_me)",
      "- Tell Ryuko she can win this time, and Toph should watch out. (set side_toph, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Satsuki Kiryuin",
    "name": "World: Arrival, Satsuki Kiryuin & Ryuko Matoi",
    "lines": [
      "cast ryuko as Ryuko Matoi",
      "background classroom",
      "me enters left with slide",
      "ryuko enters right with fade",
      "ryuko: Satsuki! You're taking over the student council? That's not fair!",
      "me (pleased): Matoi. You are impertinent. But you are the only one who challenges me.",
      "ryuko (dismayed): Challenge you? I'm going to beat you! Just watch!",
      "player: Rival, and maybe sister. Whose side do you take?",
      "choice Who do you back?",
      "- Tell Ryuko she's not fit for the council, and she should leave. (set side_me)",
      "- Tell Satsuki the council needs a rival, and Ryuko should join. (set side_ryuko, give color_pack)"
    ]
  },
  {
    "newcomer": "Satsuki Kiryuin",
    "name": "World: Arrival, Satsuki Kiryuin & Weiss Schnee",
    "lines": [
      "cast weiss as Weiss Schnee",
      "background library",
      "me enters left with slide",
      "weiss enters right with fade",
      "weiss: Satsuki Kiryuin. Your council has very high standards. I'm impressed, a little.",
      "me (pleased): Weiss Schnee. You have standards too. Let us compare them.",
      "weiss (pleased): Hmph. Perhaps, but mine are better. We'll see who keeps up.",
      "player: Two heiresses, both sure of their standards. Who do you back?",
      "choice Who do you support?",
      "- Tell Weiss her standards are too high, and Satsuki should relax. (set side_me)",
      "- Tell Satsuki her council is the best, and Weiss should join. (set side_weiss, give color_pack)"
    ]
  },
  {
    "newcomer": "Mikasa",
    "name": "World: Arrival, Mikasa & Eren",
    "lines": [
      "cast eren as Eren",
      "background arena",
      "me enters left with slide",
      "eren enters right with fade",
      "eren: Mikasa! I'm here. I didn't run away, I promise. I was training.",
      "me (pleased): Eren! You're alive. Good. Let me wrap those hands properly this time.",
      "eren (dismayed): You always do that. Fine, but only because you worry about me.",
      "player: She's found him, after a long search. Do you help her, or let Eren keep training?",
      "choice Who do you side with?",
      "- Tell Mikasa to let Eren go, and give him some room. (set side_me)",
      "- Tell Eren to let Mikasa help, and sit still for once. (set side_eren, give color_pack)"
    ]
  }
]
