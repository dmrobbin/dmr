"""World mode cast: Frieren, Dragon Maid, Persona, Spy x Family, Azur Lane, hololive, Bunny Girl Senpai, Adventure Time,
The Eminence in Shadow and Guilty Gear."""

FRIEREN_QUESTS = [
  {
    "key": "frieren-spell-collector",
    "title": "Spell Collector",
    "gates": 2,
    "about": "Frieren collects useless spells, and she has found a new one she wants to show you.",
    "offer": [
      "them: I found a new spell. It's useless. I think it's wonderful.",
      "them (pleased): Let me show you. It makes grapes sour."
    ],
    "stages": [
      {
        "text": "Watch Frieren at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Frieren, Library",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have New Year's Celebration, Frieren",
        "objectives": [
          {
            "do": "have_card",
            "card": "SFN/S108-E079"
          }
        ]
      },
      {
        "text": "Hear Frieren's verdict on the spell",
        "objectives": [
          {
            "do": "talk",
            "to": "Frieren",
            "script": [
              "them: You're delighted by a sour grape. Good. You understand.",
              "them (pleased): ...Would you like to learn it?"
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "learn-the-spell",
        "title": "Learn the useless spell",
        "about": "Frieren teaches you the sour-grape spell, and insists it is very useful indeed.",
        "rewards": [
          {
            "coins": 300
          },
          {
            "gift": "melon-bread"
          }
        ]
      }
    ]
  },
  {
    "key": "frieren-himmels-field",
    "title": "Himmel's Field",
    "gates": 5,
    "about": "The field of flowers Himmel loved, and what Frieren didn't understand until he was gone.",
    "offer": [
      "them (dismayed): Himmel loved flowers. I didn't understand until he was gone.",
      "them: Come to the shrine tonight. I want to show you his field."
    ],
    "stages": [
      {
        "text": "Meet Frieren at the shrine at night",
        "objectives": [
          {
            "do": "visit",
            "place": "shrine",
            "times": [
              3
            ],
            "scene": "World: Frieren, Shrine",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Frieren: Frieren the Slayer in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "SFN/S108-PE01",
            "against": [
              "Frieren"
            ]
          }
        ]
      },
      {
        "text": "Give Frieren your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Frieren",
            "script": [
              "them: I won't make that mistake twice. Will you stay with me?",
              "them (pleased): ...Thank you. I'll keep the field in bloom."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "the-field",
        "title": "Keep the field in bloom",
        "about": "Frieren casts the flower-field spell for you, and the petals drift around the shrine until dawn.",
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
FRIEREN_SCENES = [
  {
    "name": "World: Frieren, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Look at this spell. It makes grapes sour. Isn't it wonderful?",
      "player: It's... very useless.",
      "me (pleased): Yes. I thought you'd like it.",
      "me: Want to learn it? It takes a week and gives nothing back."
    ]
  },
  {
    "name": "World: Frieren, Shrine",
    "lines": [
      "background shrine",
      "me enters center with rise",
      "me: Himmel loved the flowers. I didn't understand why until he was gone.",
      "player: Will you show me?",
      "me (dismayed): I'll cast it. Don't make me say more than that.",
      "me: I don't want to make that mistake twice."
    ]
  }
]
FERN_QUESTS = [
  {
    "key": "fern-birthday",
    "title": "Fern's Birthday",
    "gates": 2,
    "about": "Fern was given a present she didn't expect, and doesn't know how to say thank you.",
    "offer": [
      "them: Someone gave me a present. I don't know how to thank them.",
      "them (pleased): Please don't laugh. I'm practising."
    ],
    "stages": [
      {
        "text": "Find Fern at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Fern, Cafe",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Mage Fern",
        "objectives": [
          {
            "do": "have_card",
            "card": "SFN/S108-E073"
          }
        ]
      },
      {
        "text": "Tell Fern which thank-you was best",
        "objectives": [
          {
            "do": "talk",
            "to": "Fern",
            "script": [
              "them: The plain one? Hm. You're right. It's the best.",
              "them (pleased): ...I'll say it to them tomorrow."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "plain-thanks",
        "title": "Give the plain thank-you",
        "about": "Fern practises the plain thank-you until it sounds sincere, then gives it to someone else.",
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
    "key": "fern-zoltraak",
    "title": "Zoltraak",
    "gates": 5,
    "about": "Fern's training, and the person who saved her, whom she still hasn't thanked.",
    "offer": [
      "them (dismayed): I trained for years to be able to save someone like Heiter.",
      "them: Meet me in the forest tonight. I'll show you."
    ],
    "stages": [
      {
        "text": "Watch Fern train in the forest in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              2
            ],
            "scene": "World: Fern, Forest",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Fern: Repaying, Fern in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "SFN/S108-E083",
            "against": [
              "Fern"
            ]
          }
        ]
      },
      {
        "text": "Give Fern your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Fern",
            "script": [
              "them: Heiter saved me. Now I'm the one who has to save others.",
              "them (pleased): ...Thank you for not telling me it's easy."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "heiters-spell",
        "title": "Learn Heiter's spell",
        "about": "Fern hits the target dead centre, and tells you the spell was Heiter's, before she was taught it.",
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
FERN_SCENES = [
  {
    "name": "World: Fern, Cafe",
    "lines": [
      "background cafe",
      "me enters right with fade",
      "me: Thank you. Thank you very much. Thank you, I really mean it.",
      "player: You sound very formal.",
      "me (dismayed): I'm practising. I'm bad at it.",
      "me (pleased): The plain one is best, you said. So: thank you."
    ]
  },
  {
    "name": "World: Fern, Forest",
    "lines": [
      "background forest",
      "me enters left with slide",
      "me: Watch me hit the target. Dead centre. Heiter taught me the spell.",
      "player: You never told me about him.",
      "me (dismayed): ...Because I'm still learning to say it.",
      "me: He saved me. I'm trying to be someone who can save others."
    ]
  }
]
KANNA_QUESTS = [
  {
    "key": "kanna-kobayashis-lunch",
    "title": "Kobayashi's Lunch",
    "gates": 2,
    "about": "Kanna wants to share her packed lunch, very seriously, and watches you eat it.",
    "offer": [
      "them: I packed too much lunch. You'll help me finish it.",
      "them (pleased): That's how friends work. You share."
    ],
    "stages": [
      {
        "text": "Eat lunch with Kanna at school in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Kanna, School",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Give Kanna a melon bread for the lunch",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "melon-bread",
            "to": "Kanna"
          }
        ]
      },
      {
        "text": "Talk to Kanna over the lunch",
        "objectives": [
          {
            "do": "talk",
            "to": "Kanna",
            "script": [
              "them: You ate it all. Good. Now we're friends properly.",
              "them (pleased): ...Sharing is the best part."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "share-lunch",
        "title": "Share lunch every day",
        "about": "Kanna packs you a lunch every morning, in a box with a dragon on the lid.",
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
    "key": "kanna-dragon-kid",
    "title": "Dragon Kid",
    "gates": 5,
    "about": "Kanna was exiled for pranks, and doesn't mind any more. She likes it better here.",
    "offer": [
      "them: I was sent away for pranks. I don't mind any more.",
      "them (pleased): Come to the beach at noon. I'll show you a trick."
    ],
    "stages": [
      {
        "text": "Meet Kanna at the beach at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              1
            ],
            "scene": "World: Kanna, Beach",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Kanna: Pranking With Whole Being in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "KMD/W96-E073",
            "against": [
              "Kanna"
            ]
          }
        ]
      },
      {
        "text": "Give Kanna your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Kanna",
            "script": [
              "them: I like it better here. Thank you for making it so.",
              "them (pleased): ...I'll show you the thunder trick next time."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "like-it-here",
        "title": "Stay here with her",
        "about": "Kanna sparks a little lightning over the waves, and says she's glad she was sent here.",
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
KANNA_SCENES = [
  {
    "name": "World: Kanna, School",
    "lines": [
      "background classroom",
      "me enters center with fade",
      "me: Here. Half my lunch. Take it, and eat it seriously.",
      "player: Thank you.",
      "me (pleased): That's how friends work. You share.",
      "me: Now watch me eat. Don't look away."
    ]
  },
  {
    "name": "World: Kanna, Beach",
    "lines": [
      "background beach",
      "me enters right with slide",
      "me: I got sent away for pranks. Honestly, I'd do them again.",
      "player: What kind of pranks?",
      "me (pleased): Lightning ones. Small. Over the waves.",
      "me: I like it better here. Really."
    ]
  }
]
TOHRU_QUESTS = [
  {
    "key": "tohru-tail-meat",
    "title": "Tail Meat",
    "gates": 2,
    "about": "Tohru insists you try her cooking, and she won't say what the dish is.",
    "offer": [
      "them: I cooked something. Try it. Don't ask what it is.",
      "them (pleased): It's good, isn't it? I knew it would be."
    ],
    "stages": [
      {
        "text": "Eat Tohru's cooking at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Tohru, Cafe",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Tohru some instant ramen to cook with",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "instant-ramen",
            "to": "Tohru"
          }
        ]
      },
      {
        "text": "Tell Tohru what the dish was",
        "objectives": [
          {
            "do": "talk",
            "to": "Tohru",
            "script": [
              "them: Did you guess it? I won't say. Just smile.",
              "them (pleased): ...See? Perfect Maid, Tohru, always wins."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "guess-the-dish",
        "title": "Guess the dish",
        "about": "Tohru tells you a secret ingredient, then says it's a lie. Mostly.",
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
    "key": "tohru-chaos-dragon",
    "title": "Chaos Dragon",
    "gates": 5,
    "about": "Tohru's past, the war between the dragon factions, and why a human life is worth staying for.",
    "offer": [
      "them (dismayed): There was a war between my kind. I want to tell you about it.",
      "them: Come to the beach at evening. The sunset helps."
    ],
    "stages": [
      {
        "text": "Watch the sunset with Tohru at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Tohru, Beach",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Perfect Maid, Tohru",
        "objectives": [
          {
            "do": "have_card",
            "card": "KMD/W96-E003"
          }
        ]
      },
      {
        "text": "Give Tohru your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Tohru",
            "script": [
              "them: Why do I stay with humans? Because of you, maybe.",
              "them (pleased): ...Yes. I think that's the answer."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "worth-staying-for",
        "title": "Be worth staying for",
        "about": "Tohru tells you what she learned from the war, and why she'd fight for the people here.",
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
TOHRU_SCENES = [
  {
    "name": "World: Tohru, Cafe",
    "lines": [
      "background cafe",
      "me enters left with slide",
      "me: Try this. Don't ask what it is. Just eat it.",
      "player: It's really good.",
      "me (pleased): Of course it is. I'm very smug about it.",
      "me: Nobody tells me what they're eating. I like that."
    ]
  },
  {
    "name": "World: Tohru, Beach",
    "lines": [
      "background dusk",
      "me enters center with fade",
      "me: The dragon factions fought for a long time. It was a terrible war.",
      "player: Why did you leave?",
      "me (dismayed): Because I found something worth staying for.",
      "me: Stay with me until the sun goes down. Please."
    ]
  }
]
PROTAGONIST_QUESTS = [
  {
    "key": "protagonist-the-dark-hour",
    "title": "The Dark Hour",
    "gates": 2,
    "about": "A hidden hour at midnight, where the city goes still and green. He wants to see if you can feel it.",
    "offer": [
      "them: There's an hour between days. Midnight. Can you feel it?",
      "them (pleased): Huh. You're awake. Good."
    ],
    "stages": [
      {
        "text": "Find the Protagonist on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Protagonist, Rooftop",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Aigis: Anti-Shadow Suppression Weapon",
        "objectives": [
          {
            "do": "have_card",
            "card": "P3/SE46-E10"
          }
        ]
      },
      {
        "text": "Tell the Protagonist what you felt",
        "objectives": [
          {
            "do": "talk",
            "to": "Protagonist",
            "script": [
              "them: It's quiet. Green. Like the world is holding its breath.",
              "them (pleased): ...Yeah. That's it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "felt-the-hour",
        "title": "Say you felt the hour",
        "about": "He nods once, and says the hour feels less lonely with someone else in it.",
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
    "key": "protagonist-memento-mori",
    "title": "Memento Mori",
    "gates": 5,
    "about": "The year he has left, and what he'll spend it on, which he tells you without much feeling.",
    "offer": [
      "them: I have a choice coming. It's the last one.",
      "them (dismayed): Come to the library at noon. I'll tell you the rest."
    ],
    "stages": [
      {
        "text": "Find the Protagonist at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Protagonist, Library",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with the Protagonist: Protagonist & Thanatos: Reload in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "P3/SE46-E16",
            "against": [
              "Protagonist"
            ]
          }
        ]
      },
      {
        "text": "Give the Protagonist your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Protagonist",
            "script": [
              "them: I'm glad I met you. That's more feeling than I usually show.",
              "them (pleased): ...Thank you. Let's spend the year well."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "spend-it-well",
        "title": "Spend the year well",
        "about": "He smiles, a little, and says the year will be better for having a friend in it.",
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
PROTAGONIST_SCENES = [
  {
    "name": "World: Protagonist, Rooftop",
    "lines": [
      "background night",
      "me enters left with slide",
      "me: Midnight. The city goes still. Look.",
      "player: It's gone green.",
      "me (dismayed): Huh. You can see it too. You're still awake.",
      "me: That's the dark hour. I'd hoped you'd feel it."
    ]
  },
  {
    "name": "World: Protagonist, Library",
    "lines": [
      "background library",
      "me enters right with fade",
      "me: I have a choice coming. Not a fight. A choice.",
      "player: What choice?",
      "me (dismayed): The one that decides what I spend my year on.",
      "me (pleased): I'm glad I met you. That's the feeling I'm least sure of."
    ]
  }
]
YUKARI_QUESTS = [
  {
    "key": "yukari-archery-club",
    "title": "Archery Club",
    "gates": 2,
    "about": "Yukari wants a partner for practice, and she laughs properly when you miss.",
    "offer": [
      "them: I'm practising at school. Want to try? You'll be terrible.",
      "them (pleased): Okay, you're terrible. Keep going."
    ],
    "stages": [
      {
        "text": "Practise archery with Yukari at school in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Yukari, School",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Give Yukari an energy drink for the practice",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "energy-drink",
            "to": "Yukari"
          }
        ]
      },
      {
        "text": "Tell Yukari how you did",
        "objectives": [
          {
            "do": "talk",
            "to": "Yukari",
            "script": [
              "them: You hit the target once! Twice, if you count the wall.",
              "them (pleased): ...Okay, I'm still laughing. Good."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "archery-partner",
        "title": "Be her archery partner",
        "about": "Yukari gives you her spare bow and promises to make you less terrible.",
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
    "key": "yukari-fathers-message",
    "title": "Father's Message",
    "gates": 5,
    "about": "A video her father left before he died, and how it changes the way she sees him.",
    "offer": [
      "them (dismayed): My father left a video. I haven't watched it all.",
      "them: Come to the beach in the evening. I want someone with me."
    ],
    "stages": [
      {
        "text": "Meet Yukari at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Yukari, Beach",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Mitsuru Kirijo: Member #0",
        "objectives": [
          {
            "do": "have_card",
            "card": "P3/SE46-E51"
          }
        ]
      },
      {
        "text": "Give Yukari your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Yukari",
            "script": [
              "them: He was more than I knew. I needed a minute.",
              "them (pleased): ...Thank you for waiting it out with me."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "his-message",
        "title": "Hear the rest of his message",
        "about": "Yukari watches the video to the end, and tells you what her father said in the last minute.",
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
YUKARI_SCENES = [
  {
    "name": "World: Yukari, School",
    "lines": [
      "background classroom",
      "me enters center with fade",
      "me: Watch this shot. Bullseye. Okay, you try.",
      "player: I'll miss.",
      "me (pleased): Hah! You did. That's the spirit.",
      "me: Try again. Properly this time."
    ]
  },
  {
    "name": "World: Yukari, Beach",
    "lines": [
      "background dusk",
      "me enters left with slide",
      "me: My father left a video. It changes how I see him.",
      "player: Do you want to watch it?",
      "me (dismayed): I've watched it. I need a minute first.",
      "me: Stay here with me. Please."
    ]
  }
]
TWILIGHT_QUESTS = [
  {
    "key": "twilight-operation-strix",
    "title": "Operation Strix",
    "gates": 2,
    "about": "Twilight needs a cover for a meeting, and he briefs you in under a minute.",
    "offer": [
      "them: I need a cover for a meeting. Be my family. Quick briefing.",
      "them (pleased): Good. You picked it up fast."
    ],
    "stages": [
      {
        "text": "Meet Twilight at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Twilight, Cafe",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Brilliant Spy From WISE, Twilight",
        "objectives": [
          {
            "do": "have_card",
            "card": "SPY/S106-E084"
          }
        ]
      },
      {
        "text": "Let Twilight tell you what you did right",
        "objectives": [
          {
            "do": "talk",
            "to": "Twilight",
            "script": [
              "them: You didn't break cover once. I'm impressed.",
              "them (pleased): ...Forgot to sound like a stranger again. Hm."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "trusted-cover",
        "title": "Be the trusted cover",
        "about": "Twilight files your name in his report as a useful contact, and lets it be known you're trusted.",
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
    "key": "twilight-a-spys-family",
    "title": "A Spy's Family",
    "gates": 5,
    "about": "The family he built for a mission, and whether a fake one can become real.",
    "offer": [
      "them: I built a family for a mission. Watch them with me in the plaza.",
      "them (dismayed): Can a fake family become real? I want to know."
    ],
    "stages": [
      {
        "text": "Watch Twilight's family in the plaza at evening",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              2
            ],
            "scene": "World: Twilight, Plaza",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Twilight: Agent Twilight in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "SPY/S106-E080",
            "against": [
              "Twilight"
            ]
          }
        ]
      },
      {
        "text": "Give Twilight your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Twilight",
            "script": [
              "them: Do you think it can be real? You can be honest.",
              "them (pleased): ...Then I'll keep the family. Thank you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "keep-the-family",
        "title": "Keep the family",
        "about": "Twilight keeps the family, quietly, and asks you to keep the secret for him.",
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
TWILIGHT_SCENES = [
  {
    "name": "World: Twilight, Cafe",
    "lines": [
      "background cafe",
      "me enters center with fade",
      "me: One minute briefing. You're my cousin. Don't forget it.",
      "player: Got it.",
      "me (pleased): Good. You're quick. Almost too quick.",
      "me: Keep your story straight. That's the whole mission."
    ]
  },
  {
    "name": "World: Twilight, Plaza",
    "lines": [
      "background sakura",
      "me enters left with slide",
      "me: I watch families here. The fake one I built, I wonder if it's real yet.",
      "player: Does it feel real?",
      "me (dismayed): Sometimes. That's the dangerous part.",
      "me: You'll keep the secret. I know you will."
    ]
  }
]
YOR_FORGER_QUESTS = [
  {
    "key": "yor-city-hall",
    "title": "City Hall",
    "gates": 2,
    "about": "Yor wants practice at being normal at work, and she's far too intense about small talk.",
    "offer": [
      "them: Small talk practice. Please. I need to be normal.",
      "them (pleased): That was very good. Did I do well?"
    ],
    "stages": [
      {
        "text": "Practise small talk with Yor in the plaza in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              0
            ],
            "scene": "World: Yor Forger, Plaza",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Give Yor a shortcake as a work treat",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "shortcake",
            "to": "Yor Forger"
          }
        ]
      },
      {
        "text": "Let Yor practise on you",
        "objectives": [
          {
            "do": "talk",
            "to": "Yor Forger",
            "script": [
              "them: Good morning. Lovely weather. Is that normal?",
              "them (pleased): ...Thank you. I feel almost normal."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "almost-normal",
        "title": "Tell her she's almost normal",
        "about": "Yor thanks you so intensely that you wonder if small talk was ever the point.",
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
    "key": "yor-thorn-princess",
    "title": "The Thorn Princess",
    "gates": 5,
    "about": "What Yor does at night, after a job, and her fear that you'll leave her.",
    "offer": [
      "them (dismayed): Please don't ask about my job. It's not what you think.",
      "them: Come to the alley at night. I'll be there. Probably."
    ],
    "stages": [
      {
        "text": "Find Yor in the alley at night",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              3
            ],
            "scene": "World: Yor Forger, Alley",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Thorn Princess, Yor",
        "objectives": [
          {
            "do": "have_card",
            "card": "SPY/S106-E059"
          }
        ]
      },
      {
        "text": "Give Yor your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Yor Forger",
            "script": [
              "them: Are you going to leave me? Be honest.",
              "them (pleased): ...You stayed. Thank you. I didn't think you would."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "you-stayed",
        "title": "Stay",
        "about": "Yor takes your hand in the alley, and says she'll try not to be scared of the next job.",
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
YOR_FORGER_SCENES = [
  {
    "name": "World: Yor Forger, Plaza",
    "lines": [
      "background sakura",
      "me enters center with fade",
      "me: Good morning. Lovely weather, isn't it? Is that normal?",
      "player: That's very normal.",
      "me (pleased): Thank you! I'll practise the next one.",
      "me (dismayed): Sorry. I'm too intense about small talk. I know."
    ]
  },
  {
    "name": "World: Yor Forger, Alley",
    "lines": [
      "background city",
      "me enters left with rise",
      "me: I finished a job. Don't ask about it.",
      "player: I'm not going anywhere.",
      "me (dismayed): You say that. Everyone says that.",
      "me: You stayed. Thank you."
    ]
  }
]
ENTERPRISE_QUESTS = [
  {
    "key": "enterprise-grey-ghost",
    "title": "The Grey Ghost",
    "gates": 2,
    "about": "Enterprise runs drills and wants a sparring partner who won't hold back.",
    "offer": [
      "them: Drill. Spar with me. Don't hold back.",
      "them (pleased): Good. You didn't flinch. That's rare."
    ],
    "stages": [
      {
        "text": "Spar with Enterprise at the arena in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              0
            ],
            "scene": "World: Enterprise, Arena",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Enterprise: Enterprise in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "AZL/S102-TE16",
            "against": [
              "Enterprise"
            ]
          }
        ]
      },
      {
        "text": "Ask Enterprise why you fight",
        "objectives": [
          {
            "do": "talk",
            "to": "Enterprise",
            "script": [
              "them: Have you ever wondered why you fight?",
              "them (pleased): ...Yes. Me too."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "why-we-fight",
        "title": "Wonder why you fight",
        "about": "Enterprise lowers her guard for a moment, and says she's never asked the question before.",
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
    "key": "enterprise-beyond-war",
    "title": "Beyond War",
    "gates": 5,
    "about": "What Enterprise will be if the fighting stops. She doesn't know who she is without a war.",
    "offer": [
      "them (dismayed): If the fighting stops, what am I?",
      "them: Come to the beach in the evening. Help me find out."
    ],
    "stages": [
      {
        "text": "Meet Enterprise at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Enterprise, Beach",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Aircraft Carrier, Enterprise",
        "objectives": [
          {
            "do": "have_card",
            "card": "AZL/S119-E099"
          }
        ]
      },
      {
        "text": "Give Enterprise your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Enterprise",
            "script": [
              "them: I don't know who I am without a war. Will you help?",
              "them (pleased): ...Then we'll find out together."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "find-out",
        "title": "Help her find out",
        "about": "Enterprise looks at the water for a long time, then says she's started to like the quiet.",
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
ENTERPRISE_SCENES = [
  {
    "name": "World: Enterprise, Arena",
    "lines": [
      "background arena",
      "me enters center with fade",
      "me: Drill like it's real. Full strength. Go.",
      "player: I'm going!",
      "me (pleased): Good. You're not afraid of me.",
      "me: Have you ever wondered why we fight? Think about it."
    ]
  },
  {
    "name": "World: Enterprise, Beach",
    "lines": [
      "background dusk",
      "me enters left with slide",
      "me: The water's quiet. I don't know what I'd be if the fighting stopped.",
      "player: You'd still be you.",
      "me (dismayed): I'm not sure I know who that is without a war.",
      "me: Help me find out. Please."
    ]
  }
]
JOKER_P5_QUESTS = [
  {
    "key": "joker-p5-leblanc-coffee",
    "title": "Leblanc Coffee",
    "gates": 2,
    "about": "Joker makes curry and coffee for people he trusts, and says almost nothing while he does it.",
    "offer": [
      "them: Sit. Curry and coffee. Don't ask for more.",
      "them (pleased): Good. You liked it. I could tell."
    ],
    "stages": [
      {
        "text": "Sit at Leblanc in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              2
            ],
            "scene": "World: Joker (P5), Cafe",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Joker an iced coffee for the shop",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "iced-coffee",
            "to": "Joker (P5)"
          }
        ]
      },
      {
        "text": "Let Joker say what he thinks",
        "objectives": [
          {
            "do": "talk",
            "to": "Joker (P5)",
            "script": [
              "them: You kept coming back. That's enough for me to trust you.",
              "them (pleased): ...Yeah. Thanks."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "trusted-regular",
        "title": "Be a trusted regular",
        "about": "Joker lets you a seat at the counter, and says nothing about it.",
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
    "key": "joker-p5-calling-card",
    "title": "Calling Card",
    "gates": 5,
    "about": "The Phantom Thieves' next target, and the question Joker asks you once he's handed you the card.",
    "offer": [
      "them (dismayed): I have a calling card. A target's name is on it.",
      "them: Come to the alley tonight. Bring your nerve."
    ],
    "stages": [
      {
        "text": "Meet Joker in the alley at night",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              3
            ],
            "scene": "World: Joker (P5), Alley",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Protagonist as JOKER: All-out Attack",
        "objectives": [
          {
            "do": "have_card",
            "card": "P5/S45-E006"
          }
        ]
      },
      {
        "text": "Give Joker your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Joker (P5)",
            "script": [
              "them: Are you in? Yes or no.",
              "them (pleased): ...Good. Then we're a team."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "im-in",
        "title": "I'm in",
        "about": "Joker tucks the card into your coat, and says the target will be dealt with soon.",
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
JOKER_P5_SCENES = [
  {
    "name": "World: Joker (P5), Cafe",
    "lines": [
      "background cafe",
      "me enters right with fade",
      "me: Curry. Coffee. Nothing else. Eat.",
      "player: It's really good.",
      "me (pleased): ...Yeah. I thought so too.",
      "me: You're welcome here. Any time."
    ]
  },
  {
    "name": "World: Joker (P5), Alley",
    "lines": [
      "background city",
      "me enters center with rise",
      "me: Here's a calling card. A target's name is on it.",
      "player: Who is it?",
      "me (dismayed): The next one. Are you in?",
      "me: Yes or no. I'm not asking twice."
    ]
  }
]
KUREIJI_OLLIE_QUESTS = [
  {
    "key": "ollie-zombie-idol",
    "title": "Zombie Idol",
    "gates": 2,
    "about": "Ollie wants to try out a new song at full volume, and an arm nearly falls off.",
    "offer": [
      "them: I have a new song! It's loud. Don't be scared.",
      "them (pleased): Did you stay for the whole song? You did!"
    ],
    "stages": [
      {
        "text": "Watch Ollie sing in the plaza at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              1
            ],
            "scene": "World: Kureiji Ollie, Plaza",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have A Step Towards the Future, Kureiji Ollie",
        "objectives": [
          {
            "do": "have_card",
            "card": "HOL/W104-E072"
          }
        ]
      },
      {
        "text": "Tell Ollie what you thought of the song",
        "objectives": [
          {
            "do": "talk",
            "to": "Kureiji Ollie",
            "script": [
              "them: Did my arm fall off? It didn't? Good. Oops.",
              "them (pleased): ...You liked it. That's all I wanted."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "full-volume",
        "title": "Keep the full-volume song",
        "about": "Ollie gives you the song's lyrics, with a note about the arm.",
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
    "key": "ollie-graveyard-shift",
    "title": "Graveyard Shift",
    "gates": 5,
    "about": "Ollie on not being alive, and being loved anyway.",
    "offer": [
      "them (dismayed): Being dead makes me less real. Does it?",
      "them: Come to the shrine tonight. Among the lanterns."
    ],
    "stages": [
      {
        "text": "Meet Ollie at the shrine at night",
        "objectives": [
          {
            "do": "visit",
            "place": "shrine",
            "times": [
              3
            ],
            "scene": "World: Kureiji Ollie, Shrine",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Ollie: A Step Towards the Future, Sakamata Chloe in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "HOL/W104-E070",
            "against": [
              "Kureiji Ollie"
            ]
          }
        ]
      },
      {
        "text": "Give Ollie your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Kureiji Ollie",
            "script": [
              "them: Am I less real? Honestly.",
              "them (pleased): ...No. Because you're here. Thank you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "because-youre-here",
        "title": "Say she's real because she's here",
        "about": "Ollie takes your hand under the lanterns, and sings the last line very quietly.",
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
KUREIJI_OLLIE_SCENES = [
  {
    "name": "World: Kureiji Ollie, Plaza",
    "lines": [
      "background sakura",
      "me enters center with rise",
      "me: One, two, three! Full volume! Here we go!",
      "player: Your arm just came off.",
      "me (pleased): It's fine! Put it back on, hold still.",
      "me: You stayed for the whole song. That's amazing."
    ]
  },
  {
    "name": "World: Kureiji Ollie, Shrine",
    "lines": [
      "background shrine",
      "me enters left with fade",
      "me: The lanterns are so pretty. Being dead doesn't make them less pretty.",
      "player: You're not less real.",
      "me (dismayed): ...Am I not? Honestly, tell me.",
      "me: You're here, so I think I'm real enough."
    ]
  }
]
MAI_SAKURAJIMA_QUESTS = [
  {
    "key": "mai-bunny-girl",
    "title": "Bunny Girl",
    "gates": 2,
    "about": "Mai is vanishing from people's sight, and she tests whether you can still see her by sitting very close.",
    "offer": [
      "them: Can you see me? Sit closer, and tell me honestly.",
      "them (pleased): You can. Good. I'm annoyed at how relieved I am."
    ],
    "stages": [
      {
        "text": "Sit with Mai at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Mai Sakurajima, Library",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Respective Choices, Mai Sakurajima",
        "objectives": [
          {
            "do": "have_card",
            "card": "SBY/W77-E002"
          }
        ]
      },
      {
        "text": "Answer Mai's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Mai Sakurajima",
            "script": [
              "them: Will you still see me tomorrow? Be honest.",
              "them (pleased): ...Thank you. I'll believe you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "still-see-her",
        "title": "Say you'll still see her",
        "about": "Mai sits a little closer than before, and asks you to say it once more.",
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
    "key": "mai-adolescence-syndrome",
    "title": "Adolescence Syndrome",
    "gates": 5,
    "about": "Will people forget her completely? She asks you to say her name out loud every day.",
    "offer": [
      "them (dismayed): Will people forget me completely? I'm scared they will.",
      "them: Come to the beach in the evening. Please."
    ],
    "stages": [
      {
        "text": "Meet Mai at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Mai Sakurajima, Beach",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Mai: Preparing Dinner, Mai Sakurajima in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "SBY/W77-E017",
            "against": [
              "Mai Sakurajima"
            ]
          }
        ]
      },
      {
        "text": "Give Mai your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Mai Sakurajima",
            "script": [
              "them: Say my name out loud, every day. Promise me.",
              "them (pleased): ...Okay. I'll keep you to that."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "say-her-name",
        "title": "Promise to say her name",
        "about": "Mai makes you promise, and you do. She says it's the first promise she's believed in a long time.",
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
MAI_SAKURAJIMA_SCENES = [
  {
    "name": "World: Mai Sakurajima, Library",
    "lines": [
      "background library",
      "me enters right with fade",
      "me: Sit closer. Closer. Can you see me?",
      "player: Yes, I can see you.",
      "me (dismayed): ...Good. Don't make a thing of it.",
      "me (pleased): I'm annoyed at how relieved I am. That's your fault."
    ]
  },
  {
    "name": "World: Mai Sakurajima, Beach",
    "lines": [
      "background dusk",
      "me enters left with slide",
      "me: Will people forget me completely? I'm afraid they will.",
      "player: I won't forget you.",
      "me (dismayed): Say my name, then. Out loud.",
      "me: Okay. Every day. Promise me."
    ]
  }
]
MARCELINE_QUESTS = [
  {
    "key": "marceline-bass-solo",
    "title": "Bass Solo",
    "gates": 2,
    "about": "Marceline wants a listener for a new song, and she floats above the roof while she plays.",
    "offer": [
      "them: I'm writing a song. It's not finished. I need a listener.",
      "them (pleased): Okay, what's it missing? Tell me."
    ],
    "stages": [
      {
        "text": "Listen to Marceline on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Marceline, Rooftop",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Marceline: Sanguine Form",
        "objectives": [
          {
            "do": "have_card",
            "card": "AT/WX02-062"
          }
        ]
      },
      {
        "text": "Tell Marceline what the song needs",
        "objectives": [
          {
            "do": "talk",
            "to": "Marceline",
            "script": [
              "them: That's it! That's the missing bit. Thanks.",
              "them (pleased): ...I'll finish it tomorrow."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "finished-song",
        "title": "Hear the finished song",
        "about": "Marceline plays the finished song, floating just above the roof, and it sounds like it was always meant to be that way.",
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
    "key": "marceline-simon-and-marcy",
    "title": "Simon and Marcy",
    "gates": 5,
    "about": "The Ice King, and the song she wrote for him, which she doesn't finish until you ask.",
    "offer": [
      "them (dismayed): I wrote a song about Simon. The Ice King. Don't laugh.",
      "them: Come to the forest in the evening. I'll play it there."
    ],
    "stages": [
      {
        "text": "Hear Marceline in the forest in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "forest",
            "times": [
              2
            ],
            "scene": "World: Marceline, Forest",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Marceline: Marceline the Vampire Queen in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "AT/WX02-042",
            "against": [
              "Marceline"
            ]
          }
        ]
      },
      {
        "text": "Give Marceline your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Marceline",
            "script": [
              "them: I never finish that song. Will you ask me to?",
              "them (pleased): ...Okay. I'll finish it for you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "finish-it",
        "title": "Ask her to finish it",
        "about": "Marceline finishes the song about Simon, and says it's the first time she's played it through.",
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
MARCELINE_SCENES = [
  {
    "name": "World: Marceline, Rooftop",
    "lines": [
      "background night",
      "me enters center with rise",
      "me: Okay, listen. It's not finished. I'm floating, so don't worry.",
      "player: What's it missing?",
      "me (dismayed): I don't know. You tell me.",
      "me (pleased): That's it! The bass. You fixed it!"
    ]
  },
  {
    "name": "World: Marceline, Forest",
    "lines": [
      "background forest",
      "me enters right with fade",
      "me: The Ice King. Simon. I wrote this song for him, and I never finish it.",
      "player: Will you finish it now?",
      "me (dismayed): ...I don't know if I can.",
      "me: Ask me again, and I'll try."
    ]
  }
]
SHADOW_QUESTS = [
  {
    "key": "shadow-maria",
    "title": "Maria",
    "gates": 2,
    "about": "Shadow remembers a promise to someone he lost, and says a name when he looks at the stars.",
    "offer": [
      "them: Look at the stars. I'm thinking about someone.",
      "them (pleased): You asked. Most don't."
    ],
    "stages": [
      {
        "text": "Find Shadow on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Shadow, Rooftop",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Ultimate, Shadow",
        "objectives": [
          {
            "do": "have_card",
            "card": "EIS/SX07-068"
          }
        ]
      },
      {
        "text": "Ask Shadow about the name",
        "objectives": [
          {
            "do": "talk",
            "to": "Shadow",
            "script": [
              "them: Someone who believed in people. That's all I'll say.",
              "them (pleased): ...Thank you for not pushing."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "someone-who-believed",
        "title": "Remember who believed in people",
        "about": "Shadow says the name quietly, and this time he says it like a promise.",
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
    "key": "shadow-ultimate-lifeform",
    "title": "Ultimate Lifeform",
    "gates": 5,
    "about": "Shadow says he was made a weapon. He asks if that's all he is, then decides it isn't.",
    "offer": [
      "them (dismayed): I was made a weapon. Do you think that's all I am?",
      "them: Come to the alley in the evening. I'll show you what I chose."
    ],
    "stages": [
      {
        "text": "Meet Shadow in the alley in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              2
            ],
            "scene": "World: Shadow, Alley",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Shadow: Bold Excuse, Cid Kagenou in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "EIS/SX07-051",
            "against": [
              "Shadow"
            ]
          }
        ]
      },
      {
        "text": "Give Shadow your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Shadow",
            "script": [
              "them: Is that all I am? Tell me honestly.",
              "them (pleased): ...Then I've decided it isn't. Thank you."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "not-all-i-am",
        "title": "Tell him he isn't only a weapon",
        "about": "Shadow decides, out loud, that he is more than what he was made to be.",
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
SHADOW_SCENES = [
  {
    "name": "World: Shadow, Rooftop",
    "lines": [
      "background night",
      "me enters left with fade",
      "me: The stars are out. Look at them. Someone I knew used to do the same.",
      "player: Who was it?",
      "me (dismayed): Someone who believed in people.",
      "me: That's all I'll say tonight."
    ]
  },
  {
    "name": "World: Shadow, Alley",
    "lines": [
      "background city",
      "me enters center with rise",
      "me: I was made a weapon. Do you think that's all I am?",
      "player: No.",
      "me (pleased): ...Good. I've decided it isn't either.",
      "me: Watch what I choose from now on."
    ]
  }
]
SOL_BADGUY_QUESTS = [
  {
    "key": "sol-rock-you",
    "title": "Rock You",
    "gates": 2,
    "about": "Sol needs a fight to clear his head, and he sizes you up before he'll take it.",
    "offer": [
      "them: I need a fight. Clear my head. Hmph.",
      "them (pleased): You didn't run. That's worth something."
    ],
    "stages": [
      {
        "text": "Find Sol at the arena at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "arena",
            "times": [
              1
            ],
            "scene": "World: Sol Badguy, Arena",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Sol: Bounty Hunter",
        "objectives": [
          {
            "do": "have_card",
            "card": "GGST/SX06-T05"
          }
        ]
      },
      {
        "text": "Let Sol show you one move",
        "objectives": [
          {
            "do": "talk",
            "to": "Sol Badguy",
            "script": [
              "them: Watch this. Properly. Once.",
              "them (pleased): ...That's how I say you're worth it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "one-move",
        "title": "Learn the one move",
        "about": "Sol shows you the move again, slower, and says you've got it.",
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
    "key": "sol-gear",
    "title": "Gear",
    "gates": 5,
    "about": "What Sol is, and who he used to be: a human once, and a scientist.",
    "offer": [
      "them (dismayed): I was human once. You didn't know that, did you?",
      "them: Come to the rooftop in the evening. Don't make a big deal of it."
    ],
    "stages": [
      {
        "text": "Meet Sol on the rooftop in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              2
            ],
            "scene": "World: Sol Badguy, Rooftop",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Sol: Sol: Savior of the World in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "GGST/BCS2023-P05",
            "against": [
              "Sol Badguy"
            ]
          }
        ]
      },
      {
        "text": "Give Sol your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Sol Badguy",
            "script": [
              "them: Don't tell me I'm a monster. I know.",
              "them (pleased): ...Thanks for not making it a big deal."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "not-a-big-deal",
        "title": "Keep it quiet",
        "about": "Sol nods, and asks you never to mention the scientist part again.",
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
SOL_BADGUY_SCENES = [
  {
    "name": "World: Sol Badguy, Arena",
    "lines": [
      "background arena",
      "me enters center with rise",
      "me: Hmph. You'll do. Watch this move.",
      "player: Show me.",
      "me (pleased): There. That's how it's done. Hit it.",
      "me: That's the one. Don't tell anyone I showed you."
    ]
  },
  {
    "name": "World: Sol Badguy, Rooftop",
    "lines": [
      "background night",
      "me enters left with fade",
      "me: I was human once. A scientist. Long before the gear.",
      "player: I didn't know that.",
      "me (dismayed): You know now. Don't make a big deal of it.",
      "me: Keep it quiet. Please."
    ]
  }
]
YU_NARUKAMI_QUESTS = [
  {
    "key": "yu-junes-food-court",
    "title": "Junes Food Court",
    "gates": 2,
    "about": "Yu wants to cook for the investigation team, and needs a taste-tester who'll be honest.",
    "offer": [
      "them: I'm cooking for the team. I need someone who'll be brutally honest.",
      "them (pleased): You took my one note seriously. Good."
    ],
    "stages": [
      {
        "text": "Taste Yu's cooking at the cafe in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              2
            ],
            "scene": "World: Yu Narukami, Cafe",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Yu a melon bread to try",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "melon-bread",
            "to": "Yu Narukami"
          }
        ]
      },
      {
        "text": "Give Yu your honest verdict",
        "objectives": [
          {
            "do": "talk",
            "to": "Yu Narukami",
            "script": [
              "them: Too much salt? Okay. I'll fix it.",
              "them (pleased): ...Thank you for being brutal. It helps."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "brutal-honesty",
        "title": "Give the brutal verdict",
        "about": "Yu makes the dish again with less salt, and it's perfect this time.",
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
    "key": "yu-midnight-channel",
    "title": "The Midnight Channel",
    "gates": 5,
    "about": "What Yu found on the other side of the TV, and the truth behind it.",
    "offer": [
      "them (dismayed): I found something on the other side of the TV.",
      "them: Come to the library at noon. I'll tell you the whole truth."
    ],
    "stages": [
      {
        "text": "Visit Yu at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Yu Narukami, Library",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Protagonist(P4)",
        "objectives": [
          {
            "do": "have_card",
            "card": "P4/EN-S01-001"
          }
        ]
      },
      {
        "text": "Give Yu your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Yu Narukami",
            "script": [
              "them: Would you go in with me? Be honest.",
              "them (pleased): ...Okay. Then we go in together."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "go-in-together",
        "title": "Go in together",
        "about": "Yu explains the TV world and what's behind it, and asks you to come with him when he goes in.",
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
YU_NARUKAMI_SCENES = [
  {
    "name": "World: Yu Narukami, Cafe",
    "lines": [
      "background cafe",
      "me enters center with fade",
      "me: Taste this. Be brutal. I mean it.",
      "player: It's a bit salty.",
      "me (pleased): Good. Honest. I'll fix it.",
      "me: That's the feedback I wanted. Thank you."
    ]
  },
  {
    "name": "World: Yu Narukami, Library",
    "lines": [
      "background library",
      "me enters right with slide",
      "me: On the other side of the TV, there's a world. And a truth behind it.",
      "player: What's the truth?",
      "me (dismayed): I'll tell you if you promise to come in with me.",
      "me: Will you go in with me?"
    ]
  }
]

CAST = [
    cpu("Frieren", "aloof", quests=FRIEREN_QUESTS, extra_scenes=FRIEREN_SCENES,
        haunts=[("library", "wk", "12", 55), ("forest", "we", "01", 45), ("shrine", "135", "3", 30)],
        tastes=(["book"], ["calm", "sweet"], ["sporty"]),
        lines={
            "mid": {"1": ["them: You're still here. Interesting. Most people leave.", "them: Do you know the time it takes to grow a flower? You don't, I think.", "them: Tell me what you saw on your walk. I'd like to hear.", "them: Hm. You remind me of someone. Not in a bad way.", "them: Ask me one question about the spells. Keep it short."], "3": ["them (pleased): You're a good companion for a short life. I don't mind.", "them: I'm starting to care about the time you have. That's new for me.", "them (pleased): Come to the library. I'll show you a spell you'll like.", "them: Fern says you're kind. I think she's right.", "them (pleased): I'd like to walk the forest with you, for as long as you're around."], "5": ["them (pleased): {player}, my friend. I'll remember you longer than you'd guess.", "them: I want to make the same mistake as Himmel, never. You're the reason.", "them (pleased): Let's go to the shrine at night. I'll show you the field.", "them: You're someone I'd like to see grow old. That's a strange wish from me.", "them (pleased): Best friend. Thank you for making the years feel longer and warmer."]},
            "hello_steps": [["them: Hm? Oh. Hello.", "them: You're standing in the grass. It's fine."], ["them: Hello. Are you here about the spell?", "them: Oh. A human. Good afternoon."], ["them (pleased): Oh, {player}. You came by. That's nice.", "them (pleased): {player}. The flowers are blooming today, look."], ["them (pleased): {player}. Good to see you. Sit, if you like.", "them (pleased): {player}. I was thinking about an old friend. Sit with me."], ["them (pleased): {player}. I was thinking about you. That's new for me.", "them (pleased): {player}. Come, I'll show you the field."], ["them (pleased): {player}. You're the one I want to remember. Please stay.", "them (pleased): {player}. I'm glad you're here. Truly."]],
            "bye_steps": [["them: Bye.", "them: See you."], ["them: Take care.", "them: Go on. The grass will wait."], ["them (pleased): See you. In a few decades. ...Kidding. Tomorrow, {player}.", "them (pleased): Bye, {player}. Mind the flowers."], ["them (pleased): Go on, {player}. Come back when the flowers bloom.", "them (pleased): Bye, {player}. Take care, please."], ["them (pleased): Come back soon. I'd like to remember today, {player}.", "them (pleased): Bye, {player}. Keep the spell safe."], ["them (pleased): Come back soon, {player}. You're worth remembering.", "them (pleased): Bye, friend. Himmel would have liked you."]],
            "hello": ["them: Hm? Oh. Hello.", "them (pleased): Oh, {player}. You came by. That's nice.", "them (pleased): {player}. I was thinking about you. That's new for me."],
            "bye": ["them: Bye.", "them (pleased): See you. In a few decades. ...Kidding. Tomorrow.", "them (pleased): Come back soon. I'd like to remember today."],
            "hi": ["them: I once knew Himmel the hero. Let's see how the champions of today measure up.",
                   "them: ...Oh. Hello. I was reading a grimoire. It turns flowers into slightly different flowers."],
            "hi2": "them: {player}. You've come again. Time feels shorter with you around. That's strange.",
            "hi4": "them (pleased): Sit. I found a spell for warm tea. It's useless and I love it.",
            "again": "them: Back already? Humans move so fast.",
            "loved": "them (pleased): A grimoire. Oh. Oh, this is wonderful.",
            "disliked": "them (dismayed): Exercise? I'm a thousand years old. I'll pass.",
            "before": "them: I'll show you what a thousand years of magic looks like.",
            "won": "them: Impressive. Himmel would've been proud of you.",
            "lost": "them: You'll understand more in a few decades.",
            "r1": "them: You remind me of someone. In a good way.",
            "r3": "them: I didn't understand Himmel until after he died. I don't want to make that mistake again.",
            "r4": "them (pleased): I'm trying to know people properly this time. You're the one I'm trying hardest with.",
        },
        friend=["background forest", "me enters left with fade", "me: Hold out your hand.",
                "narrator: A small field of blue flowers opens around your feet.",
                "me: Himmel's favourite spell. I used to think it was useless.", "player: It's beautiful.",
                "me (pleased): That's what he said.", "me: I want to remember the people I travel with. You're one of them now. A friend."],
        best=["background night", "me enters center with fade", "me: Fifty years with my party felt like a moment.",
              "me: I didn't cry when Himmel died. Then I couldn't stop.", "player: Because you loved them.",
              "me (dismayed): I didn't know it at the time.", "me: I know it now. With you, I know it right away.",
              "choice", "- Best friends, Frieren.", "- I'll make the moments count.",
              "me (pleased): Best friend. I'll remember this for a thousand more years. I promise."]),

    cpu("Fern", "neutral", quests=FERN_QUESTS, extra_scenes=FERN_SCENES,
        haunts=[("library", "wk", "01", 55), ("cafe", "we", "12", 45), ("forest", "135", "2", 30)],
        tastes=(["sweet"], ["book", "calm"], ["spicy"]),
        lines={
            "mid": {"1": ["them: Hm. Are you here to study? I might have a book for you.", "them: You're polite. That's a good start.", "them: Do you like practising magic? I'm always working on something.", "them: Frieren says you're interesting. I'm not sure yet.", "them: Ask me about Heiter, if you're curious. Only briefly."], "3": ["them (pleased): You're easier to thank than most people. I'm improving at it.", "them: I'm getting better at saying thank you. You're part of the reason.", "them (pleased): Let's train at the forest. I'll show you my best spell.", "them: You don't mind the quiet. I'm grateful for that.", "them (pleased): You helped me practise the thank-you. Thank you for that, too."], "5": ["them (pleased): {player}. My friend. Thank you, truly, for everything.", "them: I'd protect you the way Heiter protected me.", "them (pleased): Let's walk to the forest at dusk. I'll tell you the story.", "them: You're someone I can thank without practising first.", "them (pleased): Best friend. Thank you for being here. Really."]},
            "hello_steps": [["them: Hello. Do you need something?", "them: Hm. Are you a mage?"], ["them: Hi. Have you seen Frieren?", "them: Good afternoon. Please be quiet, I'm studying."], ["them: {player}. Good afternoon. Have you seen Frieren?", "them: {player}. Hello. Mind the books."], ["them (pleased): {player}. I'm glad you're here. Really.", "them (pleased): {player}. Hi. Sit, I've been practising."], ["them (pleased): {player}. Glad you came. I've been practising a thank-you.", "them (pleased): {player}. Good to see you. Did you bring the snacks?"], ["them (pleased): {player}. You're the one I'd thank every day. Thank you for coming.", "them (pleased): {player}. Hi. I've got something for you."]],
            "bye_steps": [["them: Goodbye.", "them: See you. Take care."], ["them: Bye. Don't be late next time.", "them: Goodbye. Mind the stairs."], ["them: See you. Please don't be late next time, {player}.", "them: Goodbye, {player}. Be careful."], ["them (pleased): Take care, {player}. Come back when you can.", "them (pleased): Bye, {player}. Thank you for visiting."], ["them (pleased): Come back soon. ...I'll be cross if you don't, {player}.", "them (pleased): Bye, {player}. You're kind to me."], ["them (pleased): Come back soon, {player}. I'll practise my thank-you for you.", "them (pleased): Bye, friend. Thank you for being here."]],
            "hello": ["them: Hello. Do you need something?", "them: {player}. Good afternoon. Have you seen Frieren?", "them (pleased): {player}. I'm glad you're here. Really."],
            "bye": ["them: Goodbye.", "them: See you. Please don't be late next time.", "them (pleased): Come back soon. ...I'll be cross if you don't."],
            "hi": ["them: My master says defeating you will make me a better mage.",
                   "them: Have you seen Frieren-sama? She was supposed to be up an hour ago."],
            "hi2": "them: {player}. Good morning. You're more punctual than Frieren-sama.",
            "hi4": "them (pleased): ...I'm happy you're here. That's all.",
            "again": "them: Back again? Please don't be late next time either.",
            "loved": "them (pleased): Sweets. ...Thank you. I'll eat these slowly.",
            "disliked": "them (dismayed): Spicy. Stark eats these. Not me.",
            "before": "them: Zoltraak.",
            "won": "them (dismayed): ...I'll study more.",
            "lost": "them: As expected.",
            "r1": "them: You're polite. I appreciate that.",
            "r3": "them: Heiter-sama raised me. When he died, Frieren-sama took me in. I've been lucky. You're part of that luck now.",
            "r4": "them (pleased): I'd cast a barrier around you without thinking. That's what you are to me.",
        },
        friend=["background library", "me enters right with fade", "me: Frieren-sama overslept again. So it's just us today.",
                "me: I brought extra sweets. In case.", "player: In case of what?",
                "me (pleased): In case you came.", "me: I don't say things like this often. We're friends. Please accept it."],
        best=["background dusk", "me enters center with fade", "me: I wanted to die once. Before Heiter-sama found me.",
              "me: He gave me a reason to live. Then Frieren-sama did.", "player: And now?",
              "me (dismayed): ...And now you, too.", "me: I have more reasons than I ever thought I'd have.",
              "choice", "- Best friends, Fern.", "- You'll always have a reason.",
              "me (pleased): Best friend. I'll protect it. Like a barrier spell."]),

    cpu("Kanna", "friendly", quests=KANNA_QUESTS, extra_scenes=KANNA_SCENES,
        haunts=[("school", "wk", "01", 55), ("plaza", "we", "12", 45), ("beach", "135", "1", 30)],
        tastes=(["sweet"], ["cute", "game"], ["book"]),
        lines={
            "mid": {"1": ["them: You're alright. Kanna approves, a little.", "them: Do you like dragons? I'm one. Sort of.", "them: Hm. Want to see a trick? It's lightning.", "them: You don't run away when I stare. Good.", "them: Ask Kanna one question. Only one."], "3": ["them (pleased): You share your snacks. Kanna likes that very much.", "them: Kanna thinks you're a good friend. Kanna is usually right.", "them (pleased): Let's go to the beach. Kanna will show you the waves.", "them: You don't make Kanna feel like the prankster. Thank you.", "them (pleased): Kanna wants you to come back. Please come back."], "5": ["them (pleased): {player}! Best friend! Kanna loves you the most!", "them: Kanna would share her last lunch with you, forever.", "them (pleased): Let's go to the beach at noon. Kanna has a surprise.", "them: You're the one who made Kanna want to stay here.", "them (pleased): Best friend! Don't ever leave Kanna alone with the dragons."]},
            "hello_steps": [["them: ...Who're you?", "them: Hm. Are you going to stare at me?"], ["them: Hello. Are you lost?", "them: Oh. Hi. Want to see my dragon?"], ["them (pleased): {player}. Kanna's friend. Hi.", "them (pleased): {player}. Hello. You came to play."], ["them (pleased): {player}! Kanna missed you. Play with Kanna.", "them (pleased): {player}! Did you bring snacks?"], ["them (pleased): {player}! Come here, sit by Kanna. I saved you a spot.", "them (pleased): {player}! Kanna wants to show you a trick."], ["them (pleased): {player}! My best friend. Kanna will share her lunch with you.", "them (pleased): {player}! Hi! Kanna is very happy you're here!"]],
            "bye_steps": [["them: Bye.", "them: See you, I guess."], ["them: Okay, bye.", "them: Go on. Don't cry."], ["them (pleased): Bye bye. Come back with snacks, {player}.", "them (pleased): Bye, {player}. Be safe."], ["them (pleased): Go on, {player}! Kanna will wait for you.", "them (pleased): Bye, {player}! Next time, we spark the waves."], ["them (pleased): Come back soon. Kanna will be sad if you don't, {player}.", "them (pleased): Bye, {player}. Don't forget your lunch."], ["them (pleased): Come back soon, best friend! Kanna loves you.", "them (pleased): Bye, {player}! Share your lunch with someone, okay?"]],
            "hello": ["them: ...Who're you?", "them (pleased): {player}. Kanna's friend. Hi.", "them (pleased): {player}! Kanna missed you. Play with Kanna."],
            "bye": ["them: Bye.", "them (pleased): Bye bye. Come back with snacks.", "them (pleased): Come back soon. Kanna will be sad if you don't."],
            "hi": ["them: Kanna Kamui. ...You look fun to prank.",
                   "them: Are you a human? Kobayashi is a human. Humans are interesting."],
            "hi2": "them (pleased): {player}. Saikawa says you're nice. I agree.",
            "hi4": "them (pleased): You're Kanna's friend. Kanna doesn't share friends.",
            "again": "them: Back. Good.",
            "loved": "them (pleased): Sweet. ...Kanna loves this. Kanna loves you. A little.",
            "disliked": "them (dismayed): A book with no pictures? ...Kanna sleeps now.",
            "before": "them: Kanna will zap you. Gently.",
            "won": "them (dismayed): ...Kanna will pout now.",
            "lost": "them (pleased): Kanna wins. Kanna is strong.",
            "r1": "them: You don't treat Kanna like a little kid. Kanna likes that.",
            "r3": "them: Kanna got exiled from the dragon world for pranks. Kanna was lonely. Not anymore.",
            "r4": "them (pleased): Kanna would fly you anywhere. Even to the moon.",
        },
        friend=["background sakura", "me enters left with pop", "me: Kanna has a present.", "player: A... bug?",
                "me (pleased): A cool bug. Kanna's favourite kind.", "me: Kanna only gives bugs to friends.",
                "me bounces", "me: So you're a friend."],
        best=["background space", "me enters center with fade", "me: Kanna's parents don't want Kanna back.",
              "me (dismayed): Kanna pretends it doesn't hurt.", "player: You have a family here.",
              "me: Kobayashi. Tohru. Saikawa. ...You.",
              "choice", "- Best friends, Kanna.", "- You'll never be lonely.",
              "me (pleased): Best friend. Kanna will remember for a thousand years. Dragons live long."]),

    cpu("Tohru", "friendly", quests=TOHRU_QUESTS, extra_scenes=TOHRU_SCENES,
        haunts=[("cafe", "wk", "12", 55), ("plaza", "we", "01", 45), ("beach", "135", "2", 30)],
        tastes=(["food"], ["cute", "calm"], ["fancy"]),
        lines={
            "mid": {"1": ["them: Oh, you're back! Did you eat? You look thin.", "them: I'm making something new. You should try it. Maybe.", "them: Is the house okay? Do you need anything from me?", "them: You're a good guest. I hope you stay.", "them: Tell me what you like to eat. I'll make it, honest."], "3": ["them (pleased): You've become one of the family. Miss Kobayashi agrees.", "them: I think about the war less when you're around. Thank you.", "them (pleased): Come to the cafe tomorrow. I'll make you something special.", "them: You don't mind my cooking. That's a big compliment.", "them (pleased): I'm glad you came to dinner. The house feels warmer."], "5": ["them (pleased): {player}! Best friend! The family table has your seat always.", "them: I'd fight any dragon that threatened you, even a bad one.", "them (pleased): Let's go to the beach at sunset, and I'll cook on the sand.", "them: You're the reason I stay here, with the humans.", "them (pleased): Best friend! Don't forget your lunch. Ever."]},
            "hello_steps": [["them: Oh. A human. What do you want?", "them: Hm. Are you hungry? You look hungry."], ["them: Hi. Are you here for dinner?", "them: Hello. Please don't touch the pot."], ["them (pleased): Ah, {player}! Miss Kobayashi says you're nice, so hello!", "them (pleased): {player}! I made something today. Want to try?"], ["them (pleased): {player}! Come in, I'm making dinner! You're staying!", "them (pleased): {player}! Oh, you came. Sit, sit!"], ["them (pleased): {player}! I saved you a dish. It's not suspicious, honest.", "them (pleased): {player}! Did you finish your lunch? Tell me honestly."], ["them (pleased): {player}! My best friend, and my favourite guest at the table!", "them (pleased): {player}! Come in, the house is warm with you here."]],
            "bye_steps": [["them: Go on, human.", "them: Bye. Watch the road."], ["them: Bye. Come back for dinner sometime.", "them: Go on. Mind the stairs."], ["them (pleased): Bye bye! Come by for lunch sometime, {player}!", "them (pleased): Bye, {player}! Take some leftovers for the road."], ["them (pleased): Go on, {player}! I'll cook more next time.", "them (pleased): Bye, {player}! Be careful out there."], ["them (pleased): Come back soon! I'll set a place for you at the table, {player}.", "them (pleased): Bye, {player}! Don't stay out too late."], ["them (pleased): Come back soon! The house is quieter without you, best friend.", "them (pleased): Bye, {player}! I'll keep dinner warm for you."]],
            "hello": ["them: Oh. A human. What do you want?", "them (pleased): Ah, {player}! Miss Kobayashi says you're nice, so hello!", "them (pleased): {player}! Come in, I'm making dinner! You're staying!"],
            "bye": ["them: Go on, human.", "them (pleased): Bye bye! Come by for lunch sometime!", "them (pleased): Come back soon! I'll set a place for you at the table!"],
            "hi": ["them: I'm Tohru, Miss Kobayashi's maid! Let's make this quick, human. I have dinner to make.",
                   "them: A human! Hmph. Well, you're polite. I'll allow it."],
            "hi2": "them (pleased): Oh, {player}! You're one of the good humans. I've decided.",
            "hi4": "them (pleased): You're family now! Miss Kobayashi says so, so it's true!",
            "again": "them: Back again? Want me to cook for you?",
            "loved": "them (pleased): Ingredients! Oh, I'll make Miss Kobayashi's favourite! And yours!",
            "disliked": "them (dismayed): Too fancy. Miss Kobayashi prefers simple things.",
            "before": "them: I'll go easy on you. Dragon's honour.",
            "won": "them (dismayed): A human beat a dragon?! ...Good job.",
            "lost": "them (pleased): That's dragon power!",
            "r1": "them: You're not bad, for a human.",
            "r3": "them: I hated humans before Miss Kobayashi. I almost died in the war. Now I live among you. It's nice.",
            "r4": "them (pleased): I'd burn down a city for you. ...Kidding! Mostly!",
        },
        friend=["background cafe", "me enters left with slide", "me: I made you an omelette! Dragon-made!",
                "player: There's a heart drawn on it.", "me (pleased): Ketchup heart! For friends!",
                "me: Miss Kobayashi gets one every day. Now you get one too.", "me: That makes you special. Eat!"],
        best=["background dusk", "me enters center with fade", "me: I came to this world to die. I was so tired of fighting.",
              "me: Miss Kobayashi saved me. Then everyone else made me want to stay.",
              "player: I'm glad you stayed.", "me (dismayed): ...So am I. More than I can say.",
              "choice", "- Best friends, Tohru.", "- You found your family.",
              "me (pleased): Best friend! I'll make you an omelette every day! With two hearts!"]),

    cpu("Protagonist", "neutral", quests=PROTAGONIST_QUESTS, extra_scenes=PROTAGONIST_SCENES,
        haunts=[("school", "wk", "01", 55), ("rooftop", "all", "3", 35), ("library", "we", "12", 40)],
        tastes=(["music"], ["calm", "food"], ["fancy"]),
        lines={
            "mid": {"1": ["them: ...You again. Okay.", "them: ...Is the night quiet for you too?", "them: ...I didn't expect to talk to anyone tonight.", "them: ...You can sit. If you want.", "them: ...One question. Make it count."], "3": ["them (pleased): ...You're easy to be around. I like that.", "them: ...Time is short. I'm glad I'm spending some of it with you.", "them (pleased): ...Meet me at the library. I'll show you what I've been reading.", "them: ...You make the dark hour feel less empty.", "them (pleased): ...You're the one I'd call when it's too late to call anyone."], "5": ["them (pleased): ...{player}. My friend. I'm glad you're here.", "them: ...If I had more time, I'd spend it all walking with you.", "them (pleased): ...Let's go out at midnight. The city's quiet, and so are we.", "them: ...You're the only one who knows what the hour feels like.", "them (pleased): ...Best friend. Thank you for the year. It was good."]},
            "hello_steps": [["them: ...", "them: ...Hey."], ["them: ...Hi.", "them: ...You're here. Okay."], ["them: ...Hey. You're here.", "them: ...{player}. Okay."], ["them (pleased): ...{player}. Hey.", "them (pleased): ...{player}. Sit down."], ["them (pleased): ...You're here. Good.", "them (pleased): ...{player}. Want to walk the streets?"], ["them (pleased): ...{player}. You're the one I'd want at midnight.", "them (pleased): ...{player}. Hey. I'm glad you came."]],
            "bye_steps": [["them: ...Later.", "them: ...See you."], ["them: ...Bye.", "them: ...Take care."], ["them (pleased): ...See you, {player}.", "them (pleased): ...Later, {player}."], ["them (pleased): ...Go on, {player}. Come back.", "them (pleased): ...Bye, {player}."], ["them (pleased): ...Come back soon, {player}.", "them (pleased): ...Take care, {player}. It's midnight soon."], ["them (pleased): ...Come back soon, best friend. I'll be waiting at midnight.", "them (pleased): ...Bye, {player}. Thanks."]],
            "hello": ["them: ...", "them: ...Hey.", "them (pleased): ...You're here. Good."],
            "bye": ["them: ...Later.", "them: ...See you.", "them (pleased): ...Come back soon."],
            "hi": ["them: ...If I have to.",
                   "them: *takes out one earbud* ...Hm?"],
            "hi2": "them: {player}. ...Hey.",
            "hi4": "them (pleased): ...You're here. Good.",
            "again": "them: ...Again? ...Okay.",
            "loved": "them (pleased): Music. ...Thanks. Really.",
            "disliked": "them (dismayed): ...Too much. I'm not a fancy guy.",
            "before": "them: PERSONA!",
            "won": "them: ...Nice.",
            "lost": "them: ...Hm.",
            "r1": "them: ...You're easy to be around. Quiet.",
            "r3": "them: I used to think it didn't matter. Living, dying. ...Now I want more days like this.",
            "r4": "them (pleased): ...My social link with you is maxed. That's a joke. ...Mostly.",
        },
        friend=["background rooftop", "me enters right with fade", "me: ...Want to listen?",
                "narrator: He offers you one earbud. The song is soft and bright.", "player: It's good.",
                "me (pleased): ...Yeah.", "me: ...Friends. That's what this is, right?"],
        best=["background night", "me enters center with fade", "me: ...There's an hour between days. The Dark Hour.",
              "me: Most people don't feel it. I do. Every night.", "player: That sounds lonely.",
              "me (dismayed): ...It was. Then I made friends. Then I made you.",
              "choice", "- Best friends.", "- I'll share the Dark Hour with you.",
              "me (pleased): ...Best friend. Memento mori. ...But let's live first."]),

    cpu("Yukari", "friendly", quests=YUKARI_QUESTS, extra_scenes=YUKARI_SCENES,
        haunts=[("school", "wk", "01", 55), ("beach", "we", "12", 45), ("plaza", "135", "2", 30)],
        tastes=(["sporty"], ["sweet", "cute"], ["spicy"]),
        lines={
            "mid": {"1": ["them: Hi again! Want to shoot a few arrows with me?", "them: You're getting better at talking to me. It's cute.", "them: Do you know any good places for practice? I need new spots.", "them: Oh, you're here! Did you bring your bow?", "them: Want to get a drink after school? My treat."], "3": ["them (pleased): You're the best partner for archery. Honestly, I'm so glad.", "them: My dad would've liked you. He liked people who weren't afraid to try.", "them (pleased): Let's go to the beach. I want to show you my favourite spot.", "them: You make school feel less lonely. Thank you.", "them (pleased): You helped me get over my fear of the bow. Thanks!"], "5": ["them (pleased): {player}! My best friend! My archery buddy forever!", "them: I'd shoot any target for you, even the scary ones.", "them (pleased): Let's watch the sunset at the beach. Just the two of us.", "them: You're the one who listens when I talk about my dad.", "them (pleased): Best friend! Come on, let's go shoot something amazing!"]},
            "hello_steps": [["them: Oh! Hi! Sorry, I didn't see you there!", "them: Hello! Are you here for archery?"], ["them: Hi! Are you new at school?", "them: Hey! Watch the target, it's kind of wobbly."], ["them (pleased): {player}! Hi! You're here!", "them (pleased): {player}! Did you come to shoot with me?"], ["them (pleased): {player}! Hi! Want to practise with me?", "them (pleased): {player}! Good, I've got a new target."], ["them (pleased): {player}! Yay! You came back for another round!", "them (pleased): {player}! Come sit, I'll show you my form."], ["them (pleased): {player}! My favourite person in the whole school!", "them (pleased): {player}! Best friend! Come on, let's go!"]],
            "bye_steps": [["them: Okay, bye!", "them: See ya! Don't trip on the stairs."], ["them: Bye! Watch out!", "them: See you! Mind the target."], ["them (pleased): See you! Text me, okay, {player}?", "them (pleased): Bye, {player}! Keep practising!"], ["them (pleased): Go on, {player}! Come back soon.", "them (pleased): Bye, {player}! I'll save you the best bow."], ["them (pleased): Come back soon! I'll miss you, {player}. Really really!", "them (pleased): Bye, {player}! Good luck with everything!"], ["them (pleased): Come back soon, best friend! The range is boring without you.", "them (pleased): Bye, {player}! See you tomorrow!"]],
            "hello": ["them: Oh! Hi! Sorry, I didn't see you there!", "them (pleased): {player}! Hi! You're here!", "them (pleased): {player}! Yay! My favourite person!"],
            "bye": ["them: Okay, bye!", "them (pleased): See you! Text me, okay?", "them (pleased): Come back soon! I'll miss you! Really really!"],
            "hi": ["them: I can do this... I can do this! Oh! Hi! Sorry, pep talk.",
                   "them: Yukari Takeba! Archery club. Want to duel? Don't go easy!"],
            "hi2": "them (pleased): {player}! Archery practice later? You can watch!",
            "hi4": "them (pleased): You're like my best friend! Like, really really!",
            "again": "them: You came back! Yay!",
            "loved": "them (pleased): New archery gear! Oh, you're the best!",
            "disliked": "them (dismayed): Spicy food? Ugh, my tongue.",
            "before": "them: Bullseye time!",
            "won": "them (dismayed): Argh! Okay, okay, you got me!",
            "lost": "them (pleased): Yes! I did it!",
            "r1": "them: You're fun! And easy to talk to!",
            "r3": "them: My dad died in an accident when I was little. I've been trying to find the truth ever since. Thanks for listening.",
            "r4": "them (pleased): I'd draw my bow for you any day. Seriously!",
        },
        friend=["background sakura", "me enters left with slide", "me: Okay, watch this! Perfect shot!", "screen flash",
                "player: Bullseye!", "me (pleased): Yes! You're my lucky charm!",
                "me: So, um, wanna be friends? Like, officially?", "player: Officially.", "me bounces"],
        best=["background night", "me enters center with fade", "me: I found out the truth about my dad. It wasn't what I hoped.",
              "me (dismayed): I was so angry. I still am, sometimes.", "player: That's okay.",
              "me: You never told me to just get over it. Everyone else did.",
              "choice", "- Best friends, Yukari.", "- I'll always listen.",
              "me (pleased): Best friend! You hit the bullseye on my heart. Ugh, that was cheesy!"]),

    cpu("Twilight", "neutral", quests=TWILIGHT_QUESTS, extra_scenes=TWILIGHT_SCENES,
        haunts=[("cafe", "wk", "12", 55), ("library", "we", "01", 45), ("plaza", "135", "2", 30)],
        tastes=(["drink"], ["book", "calm"], ["game"]),
        lines={
            "mid": {"1": ["them: You're quick. Keep it that way.", "them: Good. You've got a steady hand. Important in this line of work.", "them: Stay sharp. Some people are watching.", "them: I'm not sure if you're useful yet. Prove it.", "them: One question. I'll answer if it's relevant."], "3": ["them (pleased): You've proven yourself. I don't say that often.", "them: The family I built is starting to feel real. You're part of it.", "them (pleased): Meet me at the cafe tomorrow. There's a new target.", "them: You never let slip the cover. That's rare.", "them (pleased): You're someone I'd trust to watch the family while I'm gone."], "5": ["them (pleased): {player}. My closest ally, and my family.", "them: I'd protect you with my last breath. Don't ask me to explain why.", "them (pleased): Let's walk the plaza at evening. Pretend we're just a family.", "them: You're the one who makes the mission feel like home.", "them (pleased): Best friend. Stay safe, and keep the secret with me."]},
            "hello_steps": [["them: Good day. Is there something I can do for you?", "them: Hm. Please don't follow me."], ["them: Good day. You're not following me, are you?", "them: Hello. Nice weather. Don't you think?"], ["them (pleased): Ah, {player}. Good timing.", "them (pleased): {player}. Sit, I'll brief you in one minute."], ["them (pleased): {player}. Good, I was hoping you'd be here.", "them (pleased): {player}. Do you have a cover story today?"], ["them (pleased): {player}. I don't have to put on a face for you. Good.", "them (pleased): {player}. Sit with me. It's quiet today."], ["them (pleased): {player}. My family, and my closest friend. Sit down.", "them (pleased): {player}. I don't have to hide with you. Thank you."]],
            "bye_steps": [["them: Good day.", "them: Goodbye. Stay safe."], ["them: Until next time. Stay safe.", "them: Bye. Keep your story straight."], ["them (pleased): Until next time, {player}. Stay safe.", "them (pleased): Bye, {player}. Don't get caught."], ["them (pleased): Go, {player}. Be careful.", "them (pleased): Bye, {player}. Keep your cover."], ["them (pleased): Come back soon. That's not part of any plan, {player}.", "them (pleased): Bye, {player}. Be safe out there."], ["them (pleased): Come back soon. I just mean it, {player}.", "them (pleased): Goodbye, best friend. Come back to me."]],
            "hello": ["them: Good day. Is there something I can do for you?", "them (pleased): Ah, {player}. Good timing.", "them (pleased): {player}. I don't have to put on a face for you. Good."],
            "bye": ["them: Good day.", "them: Until next time. Stay safe.", "them (pleased): Come back soon. That's not part of any plan. I just mean it."],
            "hi": ["them: Every move you make, I've already planned for.",
                   "them: Loid Forger. Psychiatrist. A pleasure. ...Shall we duel?"],
            "hi2": "them: {player}. Good to see you. Coffee? I know a quiet place.",
            "hi4": "them (pleased): I don't have to perform around you. That's... unusual for me.",
            "again": "them: You're back. Good.",
            "loved": "them (pleased): Good coffee. You've done your research.",
            "disliked": "them (dismayed): A video game. Anya would love this. I'll give it to her.",
            "before": "them: Operation Strix. Commencing.",
            "won": "them: Unexpected. I'll adjust.",
            "lost": "them: Mission accomplished.",
            "r1": "them: You're honest. In my line of work, that's rare.",
            "r3": "them: I grew up in a war. I became someone else to stop it happening to other children. I've forgotten who I was.",
            "r4": "them (pleased): I'd trust you with my real name. If I remembered it.",
        },
        friend=["background cafe", "me enters right with fade", "me: Two coffees. Black. I noticed you take it black.",
                "player: You notice everything.", "me: Occupational habit.",
                "me (pleased): I'd like to call you a friend. I don't have many I can be honest with.",
                "me: Shall we?"],
        best=["background rain", "me enters center with fade", "me: I have a fake family. A cover. It was supposed to be temporary.",
              "me (dismayed): It's become the most real thing in my life. That scares me.",
              "player: Real things can be scary.", "me: You're real too. That doesn't scare me.",
              "choice", "- Best friends, Twilight.", "- You're allowed to be happy.",
              "me (pleased): Best friend. No cover. No mission. Just this."]),

    cpu("Yor Forger", "warm", quests=YOR_FORGER_QUESTS, extra_scenes=YOR_FORGER_SCENES,
        haunts=[("plaza", "wk", "01", 55), ("cafe", "we", "12", 45), ("alley", "135", "3", 25)],
        tastes=(["cute"], ["drink", "flowers"], ["game"]),
        lines={
            "mid": {"1": ["them: Oh, hello again! Lovely weather today, isn't it?", "them: Are you finding the city all right? It's very busy.", "them: I'm practising my smile. How does it look?", "them: You're nice to talk to. I'm not usually this talkative.", "them: Would you like some tea? I'm making it for two."], "3": ["them (pleased): You're so patient with me. Thank you, really.", "them: I'm getting better at being normal. You help me feel safe.", "them (pleased): Let's have lunch together. My treat, promise.", "them: You don't look at me strangely when I get nervous. That means a lot.", "them (pleased): You're one of the few who makes me feel like I can be a regular person."], "5": ["them (pleased): {player}! My best friend! I'd do anything for you, honestly!", "them: I'd keep you safe from anything, even the things I do at night.", "them (pleased): Let's go to the plaza at evening. Just a normal stroll, I promise.", "them: You're the one I'd want to tell the truth to, always.", "them (pleased): Best friend! Stay with me. I'll make dinner, and you can stay over."]},
            "hello_steps": [["them: Oh! Excuse me! Can I help you?", "them: Hello! Lovely to see you, I think."], ["them: Hi! Good morning! Is it?", "them: Hello! Did you need anything at the office?"], ["them (pleased): {player}! Oh, how lovely to see you!", "them (pleased): {player}! Good to see you, really!"], ["them (pleased): {player}! Please, come and sit. I made you something.", "them (pleased): {player}! Is this normal? Hi!"], ["them (pleased): {player}! Please, come here! I made you something!", "them (pleased): {player}! You look nice today. Sit."], ["them (pleased): {player}! My best friend. Come sit, I'll keep you safe.", "them (pleased): {player}! I'm so happy you came back. Really."]],
            "bye_steps": [["them: Take care, now!", "them: Goodbye! Mind the stairs!"], ["them: Bye! Be careful!", "them: Goodbye! Have a lovely day!"], ["them (pleased): Goodbye! Please be careful out there, {player}!", "them (pleased): Bye, {player}! Come back soon!"], ["them (pleased): Go on, {player}! Don't stay out too late!", "them (pleased): Bye, {player}! Be careful!"], ["them (pleased): Come back soon! I'll keep you safe. Somehow, {player}!", "them (pleased): Bye, {player}. I'll miss our small talk."], ["them (pleased): Come back soon! I'll keep you safe, best friend!", "them (pleased): Bye, {player}! You're the best person I know."]],
            "hello": ["them: Oh! Excuse me! Can I help you?", "them (pleased): {player}! Oh, how lovely to see you!", "them (pleased): {player}! Please, come here! I made you something!"],
            "bye": ["them: Take care, now!", "them (pleased): Goodbye! Please be careful out there!", "them (pleased): Come back soon! I'll keep you safe. Somehow!"],
            "hi": ["them: Excuse me, may I have the honour of taking your life? Oh! I mean, a match!",
                   "them (pleased): Oh, hello! I'm Yor! I work at City Hall! Nothing else! Just City Hall!"],
            "hi2": "them (pleased): {player}! I'm so happy to see you! Would you like some... I can't cook. Tea?",
            "hi4": "them (pleased): You're like family! I'd protect you. With... my City Hall skills.",
            "again": "them: Oh! Hello again!",
            "loved": "them (pleased): It's so cute! Anya will love it! I love it!",
            "disliked": "them (dismayed): A video game? I'm not very good with technology.",
            "before": "them: I'll do my best! Gently! I promise!",
            "won": "them (pleased): Oh my! You're wonderful!",
            "lost": "them (pleased): Oh! I won! Sorry! Was that too strong?",
            "r1": "them (pleased): You're very kind. I don't have many friends.",
            "r3": "them: I have a... second job. I can't tell anyone. But I want to be a good person. Do you think I can be?",
            "r4": "them (pleased): If anyone hurt you, I'd... take care of it. Ahaha! Never mind!",
        },
        friend=["background city", "me enters left with slide", "me: I've never had a friend before. Not really.",
                "me: Everyone at work gossips about me.", "player: I'd be your friend.",
                "me (pleased): Really?! Oh, oh, I'm so happy!", "me bounces",
                "me: I'll make you dinner! ...Actually, Loid should make dinner."],
        best=["background night", "me enters center with fade", "me: I'm not really just a City Hall worker.",
              "me (dismayed): I do terrible things at night. For my brother. For money.",
              "player: You're still kind, Yor.", "me: You... you still think so?",
              "player: I know so.",
              "choice", "- Best friends, Yor.", "- You're a good person.",
              "me (pleased): Best friend! Oh, I'm crying. Is this normal? Is this what friends do?"]),

    cpu("Enterprise", "neutral", quests=ENTERPRISE_QUESTS, extra_scenes=ENTERPRISE_SCENES,
        haunts=[("beach", "wk", "12", 55), ("arena", "we", "01", 45), ("rooftop", "135", "3", 30)],
        tastes=(["calm"], ["cool", "drink"], ["game"]),
        lines={
            "mid": {"1": ["them: You're getting into the rhythm of the drill.", "them: Hm. You keep your focus well. Keep that up.", "them: Do you ever think about the future? I'm trying.", "them: I'm glad you came to the beach. It's quiet.", "them: Ask me something about the war. Keep it short."], "3": ["them (pleased): You've become a good sparring partner. Thank you.", "them: The sea feels calmer when you're nearby. I notice.", "them (pleased): Let's walk the beach. I'll tell you what I think about.", "them: You're the one I'd want to fight beside, but I'm starting to wonder why.", "them (pleased): You help me see the quiet side of things."], "5": ["them (pleased): {player}, my friend. I'd be lost without you on the water.", "them: I'd protect you in any battle, and then sit by the sea with you after.", "them (pleased): Let's go to the beach at dusk. I want to talk about peace.", "them: You're the first person I've wanted to be with when there's no war.", "them (pleased): Best friend. We'll find out who we are together, right?"]},
            "hello_steps": [["them: Hello. Can I assist you?", "them: Hm. Mind the drill ground."], ["them: Good morning. What's your business?", "them: Hello. Did you need training?"], ["them (pleased): {player}. Good to see you.", "them (pleased): {player}. Sit, if you have a moment."], ["them (pleased): {player}. Good to see you. The drill's ready.", "them (pleased): {player}. Did you enjoy the last spar?"], ["them (pleased): {player}. Seeing you is... a calm sea.", "them (pleased): {player}. Sit with me at the beach. It's quiet."], ["them (pleased): {player}. My closest friend. The sea is calmer with you.", "them (pleased): {player}. Glad you came. I've been thinking."]],
            "bye_steps": [["them: Farewell.", "them: Goodbye. Stay sharp."], ["them: Fair winds.", "them: Take care. Watch the waves."], ["them (pleased): Fair winds, {player}.", "them (pleased): Bye, {player}. Take care."], ["them (pleased): Go, {player}. Come back to the drill ground.", "them (pleased): Bye, {player}. Stay safe."], ["them (pleased): Come back soon. I'll keep watch until you do, {player}.", "them (pleased): Bye, {player}. You're missed on the water."], ["them (pleased): Come back soon, best friend. The sea is quieter with you.", "them (pleased): Bye, {player}. I'm glad you're here."]],
            "hello": ["them: Hello. Can I assist you?", "them (pleased): {player}. Good to see you.", "them (pleased): {player}. Seeing you is... a calm sea."],
            "bye": ["them: Farewell.", "them (pleased): Fair winds, {player}.", "them (pleased): Come back soon. I'll keep watch until you do."],
            "hi": ["them: I am Enterprise. I'll fight for as long as there is something to protect.",
                   "them: The sea's calm today. Good day for a duel."],
            "hi2": "them: {player}. You're here. The sea feels quieter with you.",
            "hi4": "them (pleased): I fought for so long without knowing why. Now I think it was for moments like this.",
            "again": "them: Back again. Good.",
            "loved": "them (pleased): Peaceful. Thank you.",
            "disliked": "them (dismayed): A game? Laffey might like it.",
            "before": "them: Launching aircraft.",
            "won": "them: Well fought.",
            "lost": "them: The sea is vast. Keep sailing.",
            "r1": "them: You're steady. Like a good ship.",
            "r3": "them: I was made for war. I don't know what I am in peace. You're helping me find out.",
            "r4": "them (pleased): I'd sail through any storm for you.",
        },
        friend=["background ocean", "me enters right with fade", "me: Do you hear it? The waves.",
                "me: I used to only hear the war in them.", "player: What do you hear now?",
                "me (pleased): Peace. Friendship. Strange words for a warship.", "me: But true."],
        best=["background dusk", "me enters center with fade", "me: I asked myself once what I'd do when the war ended.",
              "me (dismayed): I had no answer. I was afraid there'd be nothing left of me.",
              "player: There's plenty of you.", "me: ...Because of people like you.",
              "choice", "- Best friends, Enterprise.", "- Let's find out together.",
              "me (pleased): Best friend. My new heading."]),

    cpu("Joker (P5)", "friendly", quests=JOKER_P5_QUESTS, extra_scenes=JOKER_P5_SCENES,
        haunts=[("cafe", "wk", "23", 55), ("alley", "we", "3", 40), ("library", "135", "1", 30)],
        tastes=(["drink"], ["cool", "book", "game"], ["fancy"]),
        lines={
            "mid": {"1": ["them: Hm. You're on time today. Good.", "them: Do you want a refill? It's on the house.", "them: Sit down, if you want. I'm working.", "them: You're the kind of customer I don't mind seeing.", "them: Ask me one question. Make it quick."], "3": ["them (pleased): You're a good friend to the team. We needed someone like you.", "them: I've been thinking about our next target. You're on my list of people to trust.", "them (pleased): Come to the café tomorrow. I'll make the curry you like.", "them: You don't pry too much. That's why I like you.", "them (pleased): We make a good team, don't we? Yeah."], "5": ["them (pleased): {player}, my confidant. Stay with the team, always.", "them: I'd take any risk for you, even the big heist.", "them (pleased): Let's go to the alley tonight. I've got something to show you.", "them: You're one of the few I'd trust with my real name.", "them (pleased): Best friend. Let's finish this, and then get some curry."]},
            "hello_steps": [["them: ...You've got a question?", "them: Hm. Coffee's on the counter."], ["them: Oh. Hi. The curry's still hot.", "them: Hey. Don't stay too long at the counter."], ["them (pleased): {player}. Good timing. Got a minute?", "them (pleased): {player}. Sit. I'll make you something."], ["them (pleased): {player}. Glad you came. Sit at the counter.", "them (pleased): {player}. The team's been asking about you."], ["them (pleased): {player}. Glad it's you. Let's take the day off.", "them (pleased): {player}. Sit. I've got something to tell you."], ["them (pleased): {player}. My closest confidant. Sit, and we'll talk about the heist.", "them (pleased): {player}. You're one of us. Welcome back."]],
            "bye_steps": [["them: Later.", "them: See you. Mind the stairs."], ["them: Bye. Careful out there.", "them: See you. Don't get caught."], ["them (pleased): See you. Stay out of the Metaverse, {player}.", "them (pleased): Bye, {player}. Watch yourself."], ["them (pleased): Go on, {player}. Come back to the café.", "them (pleased): Bye, {player}. Keep your nerve."], ["them (pleased): Come back soon. You're my favourite confidant, {player}.", "them (pleased): Bye, {player}. We'll talk about the next target."], ["them (pleased): Come back soon, best friend. The team needs you.", "them (pleased): Bye, {player}. Stay with the team."]],
            "hello": ["them: ...You've got a question?", "them (pleased): {player}. Good timing. Got a minute?", "them (pleased): {player}. Glad it's you. Let's take the day."],
            "bye": ["them: Later.", "them (pleased): See you. Stay out of the Metaverse.", "them (pleased): Come back soon. You're my favourite confidant."],
            "hi": ["them: Your heart is distorted. Consider this your calling card.",
                   "them: ...Leblanc's coffee is good. You should try it."],
            "hi2": "them (pleased): {player}. I brewed an extra cup. Sit.",
            "hi4": "them (pleased): You're in my confidant list. Max rank.",
            "again": "them: Back. Coffee's still hot.",
            "loved": "them (pleased): Good beans. You have taste.",
            "disliked": "them (dismayed): Too flashy. Morgana would say I'm a sellout.",
            "before": "them: It's showtime.",
            "won": "them (pleased): Not bad. You'd make a good Phantom Thief.",
            "lost": "them (pleased): Looking cool, Joker.",
            "r1": "them: You don't judge me. People usually do.",
            "r3": "them: I got framed for assault. I'm on probation. Most people avoid me. You didn't.",
            "r4": "them (pleased): I'd steal anyone's heart who hurt you. Literally.",
        },
        friend=["background cafe", "me enters left with fade", "me: Here. Leblanc house blend.", "player: It's amazing.",
                "me (pleased): Sojiro taught me.", "me: You've been coming around a lot. I like it.",
                "me: Bond strengthened. ...That's a Persona joke. We're friends."],
        best=["background night", "me enters center with fade", "me: I've fought gods. Corrupt adults. A whole society.",
              "me: The hardest part was admitting I needed people.", "player: You've got me.",
              "me (dismayed): ...I know. That still surprises me.",
              "choice", "- Best friends, Joker.", "- Take my heart. As a friend.",
              "me (pleased): Best friend. Thou art I. And I art thou. Something like that."]),

    cpu("Kureiji Ollie", "warm", quests=KUREIJI_OLLIE_QUESTS, extra_scenes=KUREIJI_OLLIE_SCENES,
        haunts=[("plaza", "wk", "12", 55), ("school", "we", "01", 40), ("shrine", "135", "3", 35)],
        tastes=(["music"], ["cute", "game"], ["calm"]),
        lines={
            "mid": {"1": ["them: Oh, you came back! Did you see my concert poster?", "them: Don't mind the dust. It's just me, being dead.", "them: Do you want to hear my new song? It's louder than the last.", "them: You're good company for a living person.", "them: Ask me anything. I'll answer, but you have to dance."], "3": ["them (pleased): You stayed for the whole song! You're the best audience!", "them: Being dead is less lonely with you here. I mean it.", "them (pleased): Let's go to the plaza. I'll sing for you, just you.", "them: You make me feel real, even when I'm falling apart.", "them (pleased): Come to the shrine tomorrow. I'll show you the lanterns."], "5": ["them (pleased): {player}!! My best friend, the one who makes Ollie feel alive!", "them: I'd sing for you forever, even when my arm falls off.", "them (pleased): Let's go to the shrine at night. The lanterns are for us.", "them: You're the only one who asks if I'm real. And you believe me.", "them (pleased): Best friend! Let's make the next concert the loudest ever!"]},
            "hello_steps": [["them (pleased): Oh! A living person! Hiii!", "them (pleased): Hello! Are you here for the concert?"], ["them (pleased): Hi! Don't scream, I'm not scary. Mostly.", "them (pleased): Hello! Want to see my new arm?"], ["them (pleased): {player}! Hi! Ollie's bestie is here!", "them (pleased): {player}! Did you bring the song?"], ["them (pleased): {player}!! Ollie's heart is beating again! Kind of!", "them (pleased): {player}! Come sing with me!"], ["them (pleased): {player}!!! Hi! You came to see the zombie idol!", "them (pleased): {player}! Sit with Ollie, let's practise!"], ["them (pleased): {player}! My best friend, my favourite living person!", "them (pleased): {player}! Ollie loves you! Really!"]],
            "bye_steps": [["them (pleased): Byeee! Don't die!", "them (pleased): See ya! Stay alive!"], ["them (pleased): Bye! Unless you want to hang out, of course!", "them (pleased): See you! Watch your arms!"], ["them (pleased): See you! Ollie will haunt you till you're back!", "them (pleased): Bye, {player}! Keep singing!"], ["them (pleased): Go on, {player}! Come back to the concert!", "them (pleased): Bye, {player}! Ollie will miss you!"], ["them (pleased): Come back soon or Ollie will cry! Zombie tears!", "them (pleased): Bye, {player}! Don't forget the song!"], ["them (pleased): Come back soon, best friend! Ollie's heart is yours!", "them (pleased): Bye, {player}! Haunt me back!"]],
            "hello": ["them (pleased): Oh! A living person! Hiii!", "them (pleased): {player}!! Ollie's bestie is here!", "them (pleased): {player}!!! Ollie's heart is beating again! Kind of!"],
            "bye": ["them (pleased): Byeee! Don't die! Unless you want to hang out!", "them (pleased): See you! Ollie will haunt you till you're back!", "them (pleased): Come back soon or Ollie will cry! Zombie tears!"],
            "hi": ["them (pleased): Zombie idol Kureiji Ollie is here! Let's have a fight that's to die for!",
                   "them (pleased): Zombieeee! Hi hi! Are you a zomrade? You are now!"],
            "hi2": "them (pleased): {player}! My favourite zomrade! Ollie's so happy!",
            "hi4": "them (pleased): You're Ollie's bestie! Ollie would come back from the dead for you! Again!",
            "again": "them: Back again?! Ollie loves it!",
            "loved": "them (pleased): Music! Ollie's gonna sing this all day! KYAAA!",
            "disliked": "them (dismayed): Calm? Ollie doesn't do calm! Ollie's a zombie!",
            "before": "them: Zombie power! Brrraaaains!",
            "won": "them (dismayed): Waaah! You beat Ollie! Ollie's crying! Zombie tears!",
            "lost": "them (pleased): Ollie wins! Zombie supremacy!",
            "r1": "them (pleased): You're not scared of zombies! You're so cool!",
            "r3": "them: Ollie doesn't remember her life before. Being a zombie's lonely sometimes. But not with you!",
            "r4": "them (pleased): Ollie would share her last brain with you! That's love!",
        },
        friend=["background shrine", "me enters left with pop", "me: Ollie made you a friendship bracelet!",
                "player: Is that... a stitch?", "me (pleased): Zombie stitch! Very trendy!",
                "me bounces", "me: Now we match! Zomrades forever!"],
        best=["background night", "me enters center with fade", "me: Ollie's been dead a long time. Everyone she knew is gone.",
              "me (dismayed): Ollie acts happy so nobody worries.", "player: You don't have to act with me.",
              "me: ...Ollie's not acting now. Ollie's really happy. With you.",
              "choice", "- Best friends, Ollie.", "- My favourite zombie.",
              "me (pleased): Best friend! Ollie's undead heart is beating! Kind of! Ahahaha!"]),

    cpu("Mai Sakurajima", "aloof", quests=MAI_SAKURAJIMA_QUESTS, extra_scenes=MAI_SAKURAJIMA_SCENES,
        haunts=[("library", "wk", "12", 55), ("beach", "we", "12", 45), ("school", "135", "0", 30)],
        tastes=(["book"], ["calm", "fancy"], ["cute"]),
        lines={
            "mid": {"1": ["them: You can still see me? Good. Keep looking.", "them: Do you think I'm strange? Be honest.", "them: I like the library. No one bothers me there.", "them: You didn't forget me when I was almost gone. Thank you.", "them: Ask me one thing. I'll answer if you can see me while I do."], "3": ["them (pleased): You've been a good friend, even when I'm hard to see.", "them: The fading gets worse when I'm alone. You make it easier.", "them (pleased): Let's walk the beach. You can see me better there.", "them: I trust you to say my name when I'm not around.", "them (pleased): You're the one person I'd want to remember me."], "5": ["them (pleased): {player}. My best friend, the one who keeps me here.", "them: I'd stay visible for you, even if it cost me everything.", "them (pleased): Let's sit on the beach at dusk. You'll see me the whole time.", "them: You say my name every day, don't you? That's why I'm still here.", "them (pleased): Best friend. Promise you'll never stop seeing me."]},
            "hello_steps": [["them: Oh. You can see me?", "them: Hm. Don't stare too long. People get confused."], ["them: Hello. You're looking right at me.", "them: Hi. Are you surprised I'm here?"], ["them (pleased): Hey, {player}. You found me again.", "them (pleased): {player}. Hi. Sit down, you're blocking the sun."], ["them (pleased): {player}. You found me. Good.", "them (pleased): {player}. Did you come to the beach?"], ["them (pleased): {player}. There you are. I was waiting, you know.", "them (pleased): {player}. Sit closer. I want to see if you still can."], ["them (pleased): {player}. The one person who never forgets me. Hi.", "them (pleased): {player}. I was hoping you'd come. Stay close."]],
            "bye_steps": [["them: Bye.", "them: See you. Be careful."], ["them: Goodbye. Don't stare too long.", "them: Go on. I'll still be here."], ["them (pleased): See you. Don't forget me, {player}.", "them (pleased): Bye, {player}. Say my name tomorrow."], ["them (pleased): Go on, {player}. Come back soon.", "them (pleased): Bye, {player}. Keep an eye out for me."], ["them (pleased): Come back soon. I'll be easier to see when you do, {player}.", "them (pleased): Bye, {player}. Remember what I said."], ["them (pleased): Come back soon. Say my name every day, {player}. Promise.", "them (pleased): Bye, best friend. Don't let me fade."]],
            "hello": ["them: Oh. You can see me?", "them (pleased): Hey, {player}. You found me again.", "them (pleased): {player}. There you are. I was waiting, you know."],
            "bye": ["them: Bye.", "them (pleased): See you. Don't forget me.", "them (pleased): Come back soon. I'll be easier to see when you do."],
            "hi": ["them: Oh, you can see me? Good. Then let's play, and don't go easy on me.",
                   "them: You're staring. ...It's fine. Most people can't see me at all lately."],
            "hi2": "them: {player}. You came. ...I'm glad. Don't make a fuss about it.",
            "hi4": "them (pleased): You're one of the few people I don't have to be an actress for.",
            "again": "them: Back again? You're as stubborn as Sakuta.",
            "loved": "them (pleased): A good book. You know me well.",
            "disliked": "them (dismayed): A plushie. ...I'm not a child.",
            "before": "them: Don't hold back. I won't.",
            "won": "them (dismayed): Hmph. Not bad.",
            "lost": "them (pleased): You'll have to do better than that.",
            "r1": "them: You remember me. That matters more than you know.",
            "r3": "them: I disappeared once. People forgot I existed. Sakuta didn't. You haven't either.",
            "r4": "them (pleased): I'll never be invisible around you. That's a comfort.",
        },
        friend=["background library", "me enters right with fade", "me: Do you remember my name?", "player: Mai Sakurajima.",
                "me (pleased): Good. Say it again sometimes.", "me: People forgetting you is lonelier than you'd think.",
                "me: Friends remember. That's what we are."],
        best=["background ocean", "me enters center with fade", "me: My mother managed my career. My life. Everything.",
              "me (dismayed): I quit to find out who I was. And then I started disappearing.",
              "player: I see you, Mai.", "me: I know. You always have.",
              "choice", "- Best friends, Mai.", "- I'll never forget you.",
              "me (pleased): Best friend. That's one thing I'm sure of, at least."]),

    cpu("Marceline", "neutral", quests=MARCELINE_QUESTS, extra_scenes=MARCELINE_SCENES,
        haunts=[("rooftop", "all", "3", 55), ("forest", "wk", "23", 45), ("alley", "we", "23", 35)],
        tastes=(["music"], ["cool", "spicy"], ["calm"]),
        lines={
            "mid": {"1": ["them: Oh, hey. Want to float a while?", "them: You're not as scared of me as the others. Good.", "them: I play the bass when I'm bored. Want to hear?", "them: Hm. You've got a good ear. I can tell.", "them: Ask me something about the old days. Quick."], "3": ["them (pleased): You're a good listener. Better than most mortals.", "them: The song I'm writing needs someone like you to finish it.", "them (pleased): Let's go to the forest. I'll play by the river.", "them: You don't make me feel like a monster. Thank you.", "them (pleased): You're the one I'd call a true friend, and I'm not used to that."], "5": ["them (pleased): {player}, my best friend. Eternity's better with you here.", "them: I'd sing the saddest song for you, and then the happiest.", "them (pleased): Let's play at the rooftop tonight. Just us and the stars.", "them: You're the one who finishes what I start, in songs and in life.", "them (pleased): Best friend. Let's keep playing forever, together."]},
            "hello_steps": [["them: Well, well. A mortal.", "them: Hm. Careful, it's a long drop from up here."], ["them: Hi. Are you here to listen to the song?", "them: Hey. Don't get too close to the bats."], ["them (pleased): Hey, {player}. Wanna hear a song?", "them (pleased): {player}! Did you come to hear the new track?"], ["them (pleased): {player}! Good to see you. Pull up a cloud.", "them (pleased): {player}! Sit, I've got a new riff for you."], ["them (pleased): {player}! My favourite mortal. Pull up a cloud.", "them (pleased): {player}! Come up here. The view's better from the roof."], ["them (pleased): {player}! My best friend, the one who finishes my songs.", "them (pleased): {player}! Eternity's better with you here."]],
            "bye_steps": [["them: Later, mortal.", "them: Bye. Watch the sun."], ["them: See ya. Don't get burned.", "them: Goodbye. Stay out of the rain."], ["them (pleased): See ya. Don't let the sun get you, {player}.", "them (pleased): Bye, {player}. Keep the song in your head."], ["them (pleased): Go on, {player}. Come back for the next verse.", "them (pleased): Bye, {player}. Don't get eaten by the bats."], ["them (pleased): Come back soon. Eternity's long without you, {player}.", "them (pleased): Bye, {player}. Pull up a cloud when you return."], ["them (pleased): Come back soon, best friend. The song's not finished without you.", "them (pleased): Bye, {player}. Let's finish the song together."]],
            "hello": ["them: Well, well. A mortal.", "them (pleased): Hey, {player}. Wanna hear a song?", "them (pleased): {player}! My favourite mortal. Pull up a cloud."],
            "bye": ["them: Later, mortal.", "them (pleased): See ya. Don't let the sun get you.", "them (pleased): Come back soon. Eternity's long without you."],
            "hi": ["them: I've been around for a thousand years. You really think you can surprise me?",
                   "them: Boo! Ha, gotcha. Marceline. Vampire Queen. Bass player."],
            "hi2": "them (pleased): {player}! Wanna hear a song I wrote? It's about fries. And loss.",
            "hi4": "them (pleased): You're my favourite mortal. Don't spread that around.",
            "again": "them: Back for more? I'll write you a song.",
            "loved": "them (pleased): Oh, this rocks. Literally. Thanks!",
            "disliked": "them (dismayed): Calming tea? Do I look like I need calming?",
            "before": "them: Let's rock and roll!",
            "won": "them (dismayed): Huh. You're good. I'll write a sad song about it.",
            "lost": "them (pleased): Vampire Queen wins! Woo!",
            "r1": "them: You don't run from vampires. That's cool.",
            "r3": "them: I lost everyone in the Mushroom War. Simon. My mom. I've been alone for centuries. Not tonight, though.",
            "r4": "them (pleased): I'd write a whole album about you. Some of it would even be nice.",
        },
        friend=["background night", "me enters left with fade", "me: Hey. Sit. I wrote you something.", "me sways",
                "narrator: She plucks a slow, warm bass line that sounds like a heartbeat.",
                "player: That was beautiful.", "me (pleased): Shh. It's a secret.", "me: Friends get secret songs."],
        best=["background space", "me enters center with fade", "me: Simon looked after me when the world ended.",
              "me (dismayed): He forgot me. The crown took his mind.", "player: I won't forget you.",
              "me: Everyone says that. Mortals don't live long, you know.",
              "player: Then let's make it count.",
              "choice", "- Best friends, Marceline.", "- Play me another song.",
              "me (pleased): Best friend. I'll write one for every year. Even after."]),

    cpu("Shadow", "aloof", quests=SHADOW_QUESTS, extra_scenes=SHADOW_SCENES,
        haunts=[("rooftop", "all", "3", 60), ("alley", "wk", "23", 40), ("library", "we", "1", 35)],
        tastes=(["cool"], ["book", "music"], ["cute"]),
        lines={
            "mid": {"1": ["them: You're not afraid of the dark. That's rare.", "them: I was made to be a weapon. You don't seem to mind.", "them: Do you believe in second chances? I'm trying to.", "them: The alley is quiet tonight. Keep close.", "them: Ask me something real. Not a trick question."], "3": ["them (pleased): You help me see the good side of the shadows.", "them: I think I'm starting to remember what it was like to be human.", "them (pleased): Let's walk the rooftop tonight. The stars are better with a friend.", "them: You make my promise feel less like a burden.", "them (pleased): You're one of the few who sees me as more than a weapon."], "5": ["them (pleased): {player}, my friend. You're the reason I chose not to be only what I was made for.", "them: I'd stand in any shadow for you, and walk out into the light after.", "them (pleased): Let's sit on the rooftop at night. Look at the stars, together.", "them: You're the only person I'd make a promise to, aside from Maria.", "them (pleased): Best friend. Come back to the shadows whenever you need the light."]},
            "hello_steps": [["them: ...You've seen me. Interesting.", "them: Hm. Careful. The shadows are restless."], ["them: You came to the shadows. Brave.", "them: Hello. Stay close to the light."], ["them: {player}. You come to the shadows again.", "them: {player}. Sit, if you dare."], ["them (pleased): {player}. The shadows welcome you.", "them (pleased): {player}. I was hoping you'd come. Stay for a moment."], ["them (pleased): {player}. The shadows welcome you. As do I.", "them (pleased): {player}. Look at the stars with me."], ["them (pleased): {player}. The one I'd call a true friend. Stay.", "them (pleased): {player}. Shadow Garden is quieter with you here."]],
            "bye_steps": [["them: Fade into the night.", "them: Go. Be quick."], ["them: Go. The shadows will watch over you.", "them: Goodbye. Keep to the light."], ["them (pleased): Go, {player}. The shadows will watch over you.", "them (pleased): Bye, {player}. Stay safe."], ["them (pleased): Go on, {player}. Come back before the next moon.", "them (pleased): Bye, {player}. I'll remember your face."], ["them (pleased): Return to us, {player}. Shadow Garden waits.", "them (pleased): Bye, {player}. Come back when the stars are out."], ["them (pleased): Return to us, best friend. Someone who believed in people.", "them (pleased): Bye, {player}. Come back. Please."]],
            "hello": ["them: ...You've seen me. Interesting.", "them: {player}. You come to the shadows again.", "them (pleased): {player}. The shadows welcome you. As do I."],
            "bye": ["them: Fade into the night.", "them: Go. The shadows will watch over you.", "them (pleased): Return to us. Shadow Garden waits."],
            "hi": ["them: We lurk in the shadows, and hunt the shadows. Now... you've seen too much.",
                   "them: *dramatic cape swish* ...Did that look cool? It looked cool."],
            "hi2": "them: {player}. You've returned to the Eminence. As foretold.",
            "hi4": "them (pleased): You're part of Shadow Garden now. Unofficially. Officially. Whichever's cooler.",
            "again": "them: You keep finding me. Impressive. I'm very hard to find. On purpose.",
            "loved": "them (pleased): This is... incredibly cool. Fitting for the Eminence.",
            "disliked": "them (dismayed): A plushie. The Eminence does not do plushies. In public.",
            "before": "them: I... am atomic.",
            "won": "them (dismayed): A setback. All according to plan. ...It was not according to plan.",
            "lost": "them (pleased): As expected of a shadow.",
            "r1": "them: You don't laugh at my monologues. That's rare.",
            "r3": "them: I just wanted to be a cool mastermind. Then everything I made up turned out to be real. It's a lot.",
            "r4": "them (pleased): In every cool story, the hero has a loyal friend. You're mine.",
        },
        friend=["background night", "me enters right with fade", "me: I've been preparing a speech. For when someone finally understood me.",
                "player: Go on.", "me (pleased): '...' I forgot it. You're the first to actually ask.",
                "me: Fine. You're my friend. That's cooler than any speech."],
        best=["background void", "me enters center with fade", "me: I wanted to be the eminence in shadow. Powerful. Mysterious.",
              "me (dismayed): Turns out it's lonely in the shadows.", "player: Not with me there.",
              "me: ...That's the coolest thing anyone's ever said to me.",
              "choice", "- Best friends, Shadow.", "- I'll stand in the shadows with you.",
              "me (pleased): Best friend. I am atomic. And grateful."]),

    cpu("Sol Badguy", "aloof", quests=SOL_BADGUY_QUESTS, extra_scenes=SOL_BADGUY_SCENES,
        haunts=[("alley", "all", "3", 55), ("arena", "wk", "12", 45), ("rooftop", "we", "23", 35)],
        tastes=(["music"], ["drink", "cool"], ["fancy"]),
        lines={
            "mid": {"1": ["them: Hmph. You're not completely useless.", "them: You fight well for a rookie. Don't get cocky.", "them: Keep your head down. The city's full of trouble.", "them: One question. Make it a good one.", "them: You're a decent partner, I guess. Fine."], "3": ["them (pleased): You're a good sparring partner. I'll admit it.", "them: I've got a lot on my mind. You're one of the few I don't mind talking to.", "them (pleased): Meet me at the arena at noon. Let's trade blows.", "them: You don't push me when I'm not in the mood. Thanks.", "them (pleased): You're someone I'd fight beside, no question."], "5": ["them (pleased): {player}. My partner. You're the one I'd trust with my life.", "them: I'd take a hit for you, and not complain about it.", "them (pleased): Let's go up to the rooftop at evening. I'll tell you a bit more.", "them: You're the one who keeps me human, even when I'm not.", "them (pleased): Best friend. Keep your gear sharp, and yourself sharper."]},
            "hello_steps": [["them: Gimme a break...", "them: Hm. Don't bother me right now."], ["them: Oh. You. What do you want?", "them: Hey. You're not that annoying."], ["them: Oh. You again. What.", "them: {player}. Hmph. Fine, you can stay."], ["them (pleased): Heh. Good to see ya, {player}.", "them (pleased): {player}. Hmph. You're here. Good."], ["them (pleased): Heh. Good to see ya, kid.", "them (pleased): {player}. You want a fight, or you want to talk?"], ["them (pleased): {player}. Glad you're here. Don't make a big deal of it.", "them (pleased): {player}. You're one of the few I'd fight beside. Good."]],
            "bye_steps": [["them: Yeah, yeah.", "them: Get outta here."], ["them: Get outta here.", "them: Later. Stay sharp."], ["them (pleased): Later, {player}. Don't go gettin' yourself hurt.", "them (pleased): Bye, {player}. Stay sharp."], ["them (pleased): Go on, {player}. Come back when you want a fight.", "them (pleased): Bye, {player}. Keep your guard up."], ["them (pleased): Don't go dyin' on me, kid. Come back soon.", "them (pleased): Bye, {player}. Keep that move in your head."], ["them (pleased): Come back, friend. Don't go dyin' on me. Ever.", "them (pleased): Bye, {player}. You're the one I'd keep alive."]],
            "hello": ["them: Gimme a break...", "them: Oh. You again. What.", "them (pleased): Heh. Good to see ya, kid."],
            "bye": ["them: Yeah, yeah.", "them: Get outta here.", "them (pleased): Don't go dyin' on me, kid."],
            "hi": ["them: Gimme a break...",
                   "them: You want something? Make it fast."],
            "hi2": "them: You again. ...Fine. Sit.",
            "hi4": "them (pleased): Heh. Good to see ya, kid.",
            "again": "them: You don't quit, do ya.",
            "loved": "them (pleased): Queen? ...Good taste.",
            "disliked": "them (dismayed): Fancy junk. Gimme a break.",
            "before": "them: Heaven or Hell. Let's rock.",
            "won": "them: Not bad. ...Don't let it go to your head.",
            "lost": "them: Too slow.",
            "r1": "them: You're not as annoying as most.",
            "r3": "them: I was the first Gear. I made the monsters that ended the world. Been tryin' to fix it ever since.",
            "r4": "them (pleased): You're one of the few people I'd fight a god for. Don't make it weird.",
        },
        friend=["background ruins", "me enters right with fade", "me: You keep showin' up. Why?",
                "player: I like your company.", "me (dismayed): ...Nobody likes my company.",
                "me: Fine. You're weird. Friends, I guess.", "me (pleased): Don't tell Ky."],
        best=["background night", "me enters center with fade", "me: I was human once. Frederick. A scientist with a girlfriend and a future.",
              "me (dismayed): Then I became this. A weapon.", "player: You're still Frederick to me.",
              "me: ...Nobody's called me that in a long time.",
              "choice", "- Best friends, Sol.", "- Best friends, Frederick.",
              "me (pleased): Heh. Best friend. Gimme a break... no, really. This is a good one."]),

    cpu("Yu Narukami", "friendly", quests=YU_NARUKAMI_QUESTS, extra_scenes=YU_NARUKAMI_SCENES,
        haunts=[("school", "wk", "01", 55), ("library", "we", "12", 40), ("cafe", "135", "2", 35)],
        tastes=(["food"], ["book", "game"], ["spicy"]),
        lines={
            "mid": {"1": ["them: Hey, you came back. Did you try the food I made?", "them: What's your favourite thing to cook? I'm curious.", "them: Hm. You've got a good sense of humour. I like it.", "them: Do you watch the TV? There's a lot of weird stuff on it.", "them: Ask me one question. I'll answer in one word."], "3": ["them (pleased): You're a great partner for the investigation. Thanks.", "them: I'm starting to trust my instincts more. You help me.", "them (pleased): Let's meet at the café. I'll make you something good.", "them: You don't freak out at the weird stuff. That's rare.", "them (pleased): We make a good team, you and me. Don't let it go to your head."], "5": ["them (pleased): {player}, my best friend. My partner in every mystery.", "them: I'd go into the TV world with you, anywhere, anytime.", "them (pleased): Let's go to the library and look at the old records together.", "them: You're the one who believes me, even when it sounds crazy.", "them (pleased): Best friend. Let's go in together. Always."]},
            "hello_steps": [["them: Hello. Can I help you?", "them: Hi. Sorry, I'm a bit busy."], ["them: Hey. Are you here for lunch?", "them: Hi. Want to try something I'm cooking?"], ["them (pleased): {player}. Good timing. Want to grab something to eat?", "them (pleased): {player}! Hi! I've got a new dish."], ["them (pleased): {player}. I was hoping I'd run into you. Sit.", "them (pleased): {player}. Did you watch the TV last night?"], ["them (pleased): {player}. I was hoping I'd run into you again.", "them (pleased): {player}. Come with me. We have a lot to talk about."], ["them (pleased): {player}. My partner in the investigation, and my friend.", "them (pleased): {player}. We're a team now. Good to see you."]],
            "bye_steps": [["them: See you.", "them: Bye. Watch your step."], ["them: Later. Be careful.", "them: See you. Don't forget the study."], ["them (pleased): Later. Stay out of the TV, {player}.", "them (pleased): Bye, {player}. Be safe."], ["them (pleased): Go on, {player}. See you at the next meeting.", "them (pleased): Bye, {player}. Keep an eye on the others."], ["them (pleased): Come back soon. We're a team now, {player}.", "them (pleased): Bye, {player}. Stay out of trouble."], ["them (pleased): Come back soon, partner. We'll go into the TV together.", "them (pleased): Bye, {player}. Stay safe. I'll be waiting."]],
            "hello": ["them: Hello. Can I help you?", "them (pleased): {player}. Good timing. Want to grab something to eat?", "them (pleased): {player}. I was hoping I'd run into you."],
            "bye": ["them: See you.", "them (pleased): Later. Stay out of the TV.", "them (pleased): Come back soon. We're a team now."],
            "hi": ["them: I'm Yu Narukami. I'm here to find the truth, wherever it's hiding.",
                   "them: You look like you've got a story. Want to share it over lunch?"],
            "hi2": "them (pleased): {player}. I made bento. Want some?",
            "hi4": "them (pleased): You're part of the Investigation Team now. Honorary member.",
            "again": "them: Back again. Want to talk?",
            "loved": "them (pleased): Fresh ingredients. I'll make something good. You're invited.",
            "disliked": "them (dismayed): ...Spicy. This reminds me of mystery food X. I'll pass.",
            "before": "them: Persona!",
            "won": "them (pleased): Nice. You've grown.",
            "lost": "them: The truth is out there. Keep looking.",
            "r1": "them: You're easy to talk to. I like that.",
            "r3": "them: I moved to Inaba for a year. I didn't think I'd make friends. I made the best ones. Now you too.",
            "r4": "them (pleased): Our bond is strong. I can feel it. Like a Persona awakening.",
        },
        friend=["background classroom", "me enters left with fade", "me: Here. Bento. I made it this morning.", "player: You cook?",
                "me (pleased): Nanako likes it.", "me: My friends and I solved mysteries over lunch. It's tradition.",
                "me: Friends share food. That's a fact. You're my friend."],
        best=["background rain", "me enters center with fade", "me: The Midnight Channel showed people their true selves. Not everyone liked what they saw.",
              "me: I learned that accepting yourself is the hardest thing.", "player: Have you accepted yourself?",
              "me (dismayed): ...Mostly. With help.", "player: Then I'll help too.",
              "choice", "- Best friends, Yu.", "- I'll face the truth with you.",
              "me (pleased): Best friend. I am thou. Thou art I. Something like that."]),
]
