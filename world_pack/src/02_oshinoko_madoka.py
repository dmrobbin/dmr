"""World mode cast: Oshi no Ko and Puella Magi Madoka Magica."""

AKANE_KUROKAWA_QUESTS = [
  {
    "key": "akane-method-acting",
    "title": "Method Acting",
    "gates": 2,
    "about": "Akane is studying the player, to play them in a role.",
    "offer": [
      "them: I've been watching how you walk. Hold still, I'm copying it.",
      "them (pleased): Don't worry, it's a compliment."
    ],
    "stages": [
      {
        "text": "Find Akane at the library at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "library",
            "times": [
              1
            ],
            "scene": "World: Akane Kurokawa, Library",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Give Akane a manga volume for research",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "manga",
            "to": "Akane Kurokawa"
          }
        ]
      },
      {
        "text": "Answer her question: what do you want?",
        "objectives": [
          {
            "do": "talk",
            "to": "Akane Kurokawa",
            "script": [
              "them: I can copy everything about you but that. Tell me.",
              "them (pleased): Hm. Honest. That I can use."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "let-her-play-you",
        "title": "Let her play you",
        "about": "Akane's copy of you is perfect now, and she's proud of it.",
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
    "key": "akane-profile-of-a-killer",
    "title": "Profile of a Killer",
    "gates": 5,
    "about": "Akane has worked out who Aqua is hunting, and what the hunt is doing to him.",
    "offer": [
      "them (dismayed): I have a profile. It's about Aqua, and it's not pretty.",
      "them: I need someone to help me stop him before he crosses a line."
    ],
    "stages": [
      {
        "text": "Meet Akane at the cafe in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              2
            ],
            "scene": "World: Akane Kurokawa, Cafe",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Perfect Trace, Akane Kurokawa",
        "objectives": [
          {
            "do": "have_card",
            "card": "OSK/S107-E068"
          }
        ]
      },
      {
        "text": "Decide what to do about Aqua",
        "objectives": [
          {
            "do": "talk",
            "to": "Akane Kurokawa",
            "script": [
              "them: Aqua's hunt is going to get him killed, or worse.",
              "them (dismayed): Stop him, or let him go. Your call."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "stop-him",
        "title": "Stop him",
        "about": "Akane tells Aqua's secret to the one person who can stop him. Aqua's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "aqua-revenge"
        ]
      },
      {
        "key": "let-him-go",
        "title": "Let him go his own way",
        "about": "Akane keeps the profile to herself and lets Aqua chase his revenge.",
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
AKANE_KUROKAWA_SCENES = [
  {
    "name": "World: Akane Kurokawa, Library",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Stay still. Your shoulders go up when you think. Like this.",
      "player: I'm not doing that.",
      "me (pleased): You just did it. Notebook page four.",
      "me: Don't worry. I won't play you badly. Just better than you'd like.",
      "player: What do you want from me?",
      "me (dismayed): ...That's the one line I can't copy. Tell me?"
    ]
  },
  {
    "name": "World: Akane Kurokawa, Cafe",
    "lines": [
      "background dusk",
      "me enters left with slide",
      "me: I wrote Aqua's profile. Read it, and tell me I'm wrong.",
      "player: Is he really hunting someone?",
      "me (dismayed): The man who had Ai killed. He's close.",
      "me: Watching him do this to himself is the worst part.",
      "me: I need you to decide what happens next. I can't carry it alone."
    ]
  }
]
AQUA_HOSHINO_QUESTS = [
  {
    "key": "aqua-behind-the-camera",
    "title": "Behind the Camera",
    "gates": 2,
    "about": "Aqua needs an extra for a reality show shoot, and he's not gentle about it.",
    "offer": [
      "them: I need an extra for a shoot. Someone who looks sincere on camera.",
      "them (pleased): That's rare in this business. Don't waste it."
    ],
    "stages": [
      {
        "text": "Go to school for the shoot in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Aqua Hoshino, School",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have Mask of Revenge, Aqua",
        "objectives": [
          {
            "do": "have_card",
            "card": "OSK/S107-E067"
          }
        ]
      },
      {
        "text": "Hear what Aqua thought of the shoot",
        "objectives": [
          {
            "do": "talk",
            "to": "Aqua Hoshino",
            "script": [
              "them (pleased): You were sincere on camera. I didn't expect that.",
              "them: Don't tell anyone I said it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "in-the-shot",
        "title": "Be in the shot",
        "about": "Aqua puts you in the final cut. He says it's the only honest take in the whole show.",
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
    "key": "aqua-revenge",
    "title": "Revenge",
    "gates": 5,
    "about": "Aqua has found a lead on the man who had Ai killed, and he needs a witness, not help.",
    "offer": [
      "them (dismayed): I found a name. A photo, too. I'm not asking for help.",
      "them: I'm asking you to watch."
    ],
    "stages": [
      {
        "text": "Meet Aqua in the alley at night",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              3
            ],
            "scene": "World: Aqua Hoshino, Alley",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Aqua: Wrap-up Party in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "OSK/S107-E084",
            "against": [
              "Aqua Hoshino"
            ]
          }
        ]
      },
      {
        "text": "Give Aqua your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Aqua Hoshino",
            "script": [
              "them: I need to know whether you'll stand there while I finish this.",
              "them (pleased): Okay. A witness, then."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "finish-it",
        "title": "Finish it",
        "about": "Aqua follows the lead to its end. Akane's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "akane-profile-of-a-killer"
        ]
      },
      {
        "key": "walk-away",
        "title": "Walk away from the lead",
        "about": "Aqua leaves the photo in a drawer and lets it go, for now.",
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
AQUA_HOSHINO_SCENES = [
  {
    "name": "World: Aqua Hoshino, School",
    "lines": [
      "background classroom",
      "me enters right with slide",
      "me: Action. No. Not that smile, a sincere one. Again.",
      "player: Like this?",
      "me (pleased): ...Yeah. Keep that. That's the one.",
      "me: Don't read anything into it. You're a prop with decent eyes.",
      "player: Thanks, I think.",
      "me (dismayed): It's not a compliment. It's a warning. Cameras see everything."
    ]
  },
  {
    "name": "World: Aqua Hoshino, Alley",
    "lines": [
      "background city",
      "me enters left with rise",
      "me: It's raining. Good. Nobody looks up.",
      "player: What's in the envelope?",
      "me (dismayed): A photo, and a name. The man who ordered Ai's death.",
      "me: I don't need your help. I need a witness.",
      "player: You'll have one.",
      "me (pleased): ...Good. Don't blink."
    ]
  }
]
KANA_ARIMA_QUESTS = [
  {
    "key": "kana-ten-second-crier",
    "title": "The Ten-Second Crier",
    "gates": 2,
    "about": "Kana is rehearsing crying on cue, and it won't come.",
    "offer": [
      "them (dismayed): Don't look. I'm practising.",
      "them: Ten seconds, on cue. It's not that hard. Apparently."
    ],
    "stages": [
      {
        "text": "Watch Kana rehearse at school at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              1
            ],
            "scene": "World: Kana Arima, School",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have POP IN 2, Kana Arima",
        "objectives": [
          {
            "do": "have_card",
            "card": "OSK/S121-E018"
          }
        ]
      },
      {
        "text": "Tell Kana what you saw",
        "objectives": [
          {
            "do": "talk",
            "to": "Kana Arima",
            "script": [
              "them (dismayed): You saw nothing. You understand? Nothing.",
              "them (pleased): ...Thanks for not making it a thing."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "never-saw-it",
        "title": "Never saw it",
        "about": "Kana's tears worked, and she swears you were never there to see them.",
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
    "key": "kana-child-star-no-more",
    "title": "Child Star No More",
    "gates": 5,
    "about": "Kana has been turned down for a role for being too old, and she won't say so out loud.",
    "offer": [
      "them: They said I'm too old. For a kid's role. I'm sixteen.",
      "them (dismayed): Don't say anything. I ordered three desserts. I'll eat none."
    ],
    "stages": [
      {
        "text": "Find Kana at the cafe in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              2
            ],
            "scene": "World: Kana Arima, Cafe",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Kana: POP IN 2 in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "OSK/S121-E018",
            "against": [
              "Kana Arima"
            ]
          }
        ]
      },
      {
        "text": "Ask Kana the question she can't answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Kana Arima",
            "script": [
              "them: Does anyone remember child stars once they grow up?",
              "them (pleased): ...You do. Okay. That helps."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "keep-her-company",
        "title": "Keep her company",
        "about": "Kana eats the desserts after all, and asks you to come to the next audition.",
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
KANA_ARIMA_SCENES = [
  {
    "name": "World: Kana Arima, School",
    "lines": [
      "background classroom",
      "me enters center with fade",
      "me: Okay. Sad face. Sad face. ...Why isn't it working?",
      "player: Think of something sad.",
      "me (dismayed): I'm thinking of you, and that's not helping.",
      "me: Fine. Okay. Last try.",
      "me bounces",
      "me: ...You saw that? Forget you saw that. Right now."
    ]
  },
  {
    "name": "World: Kana Arima, Cafe",
    "lines": [
      "background cafe",
      "me enters left with slide",
      "me: Three desserts. I'm not going to eat any of them.",
      "player: Why did you order them?",
      "me (dismayed): Because nobody's ever ordered dessert for me.",
      "me: Child stars grow up and nobody remembers them. I'm just... wondering if that's me.",
      "player: I'd remember you.",
      "me (pleased): ...Then eat the strawberry one. Don't tell me it's a lie."
    ]
  }
]
RUBY_HOSHINO_QUESTS = [
  {
    "key": "ruby-b-komachi-rehearsal",
    "title": "B-Komachi Rehearsal",
    "gates": 2,
    "about": "Ruby needs an audience of one for her new routine.",
    "offer": [
      "them (pleased): You're my audience today. Don't blink, okay?",
      "them: The routine is perfect, except the bow. I can't land the bow."
    ],
    "stages": [
      {
        "text": "Watch Ruby's routine in the plaza at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              1
            ],
            "scene": "World: Ruby Hoshino, Plaza",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Have To a Shining Stage, Ruby",
        "objectives": [
          {
            "do": "have_card",
            "card": "OSK/S107-E036"
          }
        ]
      },
      {
        "text": "Tell Ruby how the bow looked",
        "objectives": [
          {
            "do": "talk",
            "to": "Ruby Hoshino",
            "script": [
              "them (pleased): You didn't laugh when I tripped? Good. You're my first fan now.",
              "them: That's a promise, remember?"
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "first-fan",
        "title": "Be her first fan",
        "about": "Ruby lands the bow on the fourth try. She keeps your first autograph in her case.",
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
    "key": "ruby-ais-daughter",
    "title": "Ai's Daughter",
    "gates": 5,
    "about": "Ruby has found her mother's old concert ticket, and she isn't sure what it means.",
    "offer": [
      "them (dismayed): I found a ticket. Mum's last concert. I've never told anyone.",
      "them: Will you come to the cafe and look at it with me?"
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
            "scene": "World: Ruby Hoshino, Cafe",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Ruby: Flames of Revenge in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "OSK/S121-E032",
            "against": [
              "Ruby Hoshino"
            ]
          }
        ]
      },
      {
        "text": "Answer Ruby's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Ruby Hoshino",
            "script": [
              "them: Can you love someone you only remember from a stage?",
              "them (pleased): ...Okay. I think you can."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "love-from-the-stage",
        "title": "Love from the stage",
        "about": "Ruby keeps the ticket in her pocket for every show. She says it's lucky.",
        "rewards": [
          {
            "coins": 700
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
RUBY_HOSHINO_SCENES = [
  {
    "name": "World: Ruby Hoshino, Plaza",
    "lines": [
      "background sakura",
      "me enters center with rise",
      "me: Okay! Watch! Step, turn, point, and... wait, I'm falling. I'm not falling.",
      "player: You're fine. Keep going!",
      "me (pleased): Ha! That was the best trip I've ever done!",
      "me: Promise me you'll be my first fan. Like, officially.",
      "player: I promise.",
      "me bounces"
    ]
  },
  {
    "name": "World: Ruby Hoshino, Cafe",
    "lines": [
      "background cafe",
      "me enters right with fade",
      "me: Mum's ticket. Last show, same stage as ours.",
      "player: You kept it.",
      "me (dismayed): I didn't know what else to do with it.",
      "me: I never saw her perform. Only the videos. Is that the same as knowing her?",
      "player: It's a start.",
      "me (pleased): A start. Okay. I can work with that."
    ]
  }
]
LEGENDARY_IDOL_AI_QUESTS = [
  {
    "key": "ai-the-lie-of-love",
    "title": "The Lie of Love",
    "gates": 2,
    "about": "Ai runs a fan meet, and she wants to know if you can tell her real smile from the rest.",
    "offer": [
      "them: Watch carefully. Three smiles. Tell me which one is real.",
      "them (pleased): Whatever you say, I'll tell you it's wrong."
    ],
    "stages": [
      {
        "text": "Watch Ai's fan meet at the plaza in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              2
            ],
            "scene": "World: Legendary Idol Ai, Plaza",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Have Legendary Idol, Ai",
        "objectives": [
          {
            "do": "have_card",
            "card": "OSK/S107-E045"
          }
        ]
      },
      {
        "text": "Tell Ai which smile you think was real",
        "objectives": [
          {
            "do": "talk",
            "to": "Legendary Idol Ai",
            "script": [
              "them (dismayed): Wrong. Sweetly wrong. Remember that.",
              "them (pleased): ...But the last one was close."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "real-smile",
        "title": "Find the real smile",
        "about": "Ai smiles once, without the lights on. She says you're the only one who ever noticed.",
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
    "key": "ai-everyones-idol",
    "title": "Everyone's Idol",
    "gates": 5,
    "about": "Ai has never said \"I love you\" and meant it, and she's practising the words above the city.",
    "offer": [
      "them: I have to say something tonight. I don't know if I can.",
      "them (dismayed): Stay on the rooftop with me. Just listen."
    ],
    "stages": [
      {
        "text": "Find Ai on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Legendary Idol Ai, Rooftop",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Ai: Unshakable Center in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "OSK/S107-TE10",
            "against": [
              "Legendary Idol Ai"
            ]
          }
        ]
      },
      {
        "text": "Listen while she practises",
        "objectives": [
          {
            "do": "talk",
            "to": "Legendary Idol Ai",
            "script": [
              "them: I love you. ...It feels like a lie.",
              "them (pleased): Say it again. Let me listen until it doesn't."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "until-it-stops",
        "title": "Listen until it stops feeling a lie",
        "about": "Ai says the words once more, and this time she doesn't look away from you.",
        "rewards": [
          {
            "coins": 700
          },
          {
            "pack": "lucky_pack"
          }
        ]
      }
    ]
  }
]
LEGENDARY_IDOL_AI_SCENES = [
  {
    "name": "World: Legendary Idol Ai, Plaza",
    "lines": [
      "background dusk",
      "me enters center with fade",
      "me: Smile one. Smile two. Smile three. Which one's real?",
      "player: The second one.",
      "me (dismayed): Wrong. Sweetly wrong. I'll remember that.",
      "me: Next time, don't answer until I ask you properly."
    ]
  },
  {
    "name": "World: Legendary Idol Ai, Rooftop",
    "lines": [
      "background night",
      "me enters left with rise",
      "me: The city looks so small from up here. Everyone's so far away.",
      "player: Are you okay?",
      "me (dismayed): I'm practising. The words. They feel like a lie.",
      "me: Stay and listen. Not because you have to. Because I'd like you to."
    ]
  }
]
MADOKA_QUESTS = [
  {
    "key": "madoka-kyubeys-offer",
    "title": "Kyubey's Offer",
    "gates": 2,
    "about": "A small white creature offered Madoka a wish, and she wants your advice before she answers.",
    "offer": [
      "them: A small white creature came to me. It offered me a wish.",
      "them (dismayed): I don't know if it would be selfish. Will you tell me?"
    ],
    "stages": [
      {
        "text": "Meet Madoka at school in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Madoka, School",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Madoka a strawberry shortcake",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "shortcake",
            "to": "Madoka"
          }
        ]
      },
      {
        "text": "Tell Madoka what you think of the wish",
        "objectives": [
          {
            "do": "talk",
            "to": "Madoka",
            "script": [
              "them: Wishing for something isn't always selfish, is it?",
              "them (pleased): ...Thank you. I'll think about it."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "think-it-over",
        "title": "Let her think it over",
        "about": "Madoka thinks it over, and keeps the question to herself for a while.",
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
    "key": "madoka-a-wish",
    "title": "A Wish",
    "gates": 5,
    "about": "The witches are winning. Madoka has a wish that might end it, and it costs her.",
    "offer": [
      "them (dismayed): The witches are getting stronger. I've thought of a wish.",
      "them: I want you to hear it before I make it."
    ],
    "stages": [
      {
        "text": "Meet Madoka at the plaza in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "plaza",
            "times": [
              2
            ],
            "scene": "World: Madoka, Plaza",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Ultimate Madoka",
        "objectives": [
          {
            "do": "have_card",
            "card": "MM/W17-E030"
          }
        ]
      },
      {
        "text": "Hear the wish",
        "objectives": [
          {
            "do": "talk",
            "to": "Madoka",
            "script": [
              "them: It's for everyone. It costs me. Will you remember me?",
              "them (pleased): ...Thank you for not saying no."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "make-the-wish",
        "title": "Let her make the wish",
        "about": "Madoka makes her wish for everyone. Homura's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "homura-once-more"
        ]
      },
      {
        "key": "hold-her-hand",
        "title": "Hold her hand instead",
        "about": "Madoka keeps her wish for another day, and asks you to stay close while she decides.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "plushie"
          }
        ]
      }
    ]
  }
]
MADOKA_SCENES = [
  {
    "name": "World: Madoka, School",
    "lines": [
      "background classroom",
      "me enters center with fade",
      "me: Last night a small white creature appeared at my window. It said it could grant me a wish.",
      "player: What did you wish for?",
      "me (dismayed): I didn't. Not yet. I'm not sure what I'd ask for.",
      "me: Is it selfish, do you think? To wish for something that helps other people?"
    ]
  },
  {
    "name": "World: Madoka, Plaza",
    "lines": [
      "background dusk",
      "me enters left with slide",
      "me: I thought of a wish. It's for everyone, but it costs me.",
      "player: What does it cost?",
      "me (dismayed): Being forgotten, mostly. Everyone would forget me.",
      "me: Remember me, okay? Even if I'm the only one who does."
    ]
  }
]
HOMURA_AKEMI_QUESTS = [
  {
    "key": "homura-transfer-student",
    "title": "Transfer Student",
    "gates": 2,
    "about": "Homura warns the player to keep away from Madoka, and knows things she shouldn't.",
    "offer": [
      "them: Keep away from Madoka. Don't ask why. I'll only tell you once.",
      "them (dismayed): You don't believe me. You will."
    ],
    "stages": [
      {
        "text": "Find Homura at school in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Homura Akemi, School",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Best Friends, Madoka & Homura",
        "objectives": [
          {
            "do": "have_card",
            "card": "MM/W17-E047"
          }
        ]
      },
      {
        "text": "Hear Homura's warning again",
        "objectives": [
          {
            "do": "talk",
            "to": "Homura Akemi",
            "script": [
              "them: Madoka must never make a contract. I mean it.",
              "them (pleased): ...You listened. That's rarer than you think."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "keep-your-distance",
        "title": "Keep your distance",
        "about": "Homura doesn't say thanks, but she stops watching you the way she watched Madoka.",
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
    "key": "homura-once-more",
    "title": "Once More",
    "gates": 5,
    "about": "The truth about the time loops. Homura has lived this month more than once.",
    "offer": [
      "them (dismayed): I have lived this month more times than I can count.",
      "them: I need you to help me stop her once more."
    ],
    "stages": [
      {
        "text": "Meet Homura on the rooftop at night",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              3
            ],
            "scene": "World: Homura Akemi, Rooftop",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Win a duel with Homura: For Madoka's Sake in your deck",
        "objectives": [
          {
            "do": "win_with",
            "card": "MM/W35-E026",
            "against": [
              "Homura Akemi"
            ]
          }
        ]
      },
      {
        "text": "Give Homura your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Homura Akemi",
            "script": [
              "them: Turn back time with me, or let her make the wish?",
              "them (pleased): Then I'll do it alone. Thank you anyway."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "turn-back-time",
        "title": "Turn back time",
        "about": "Homura turns the clock back once more. Madoka's Best friend quest is closed for good.",
        "rewards": [
          {
            "coins": 800
          },
          {
            "pack": "lucky_pack"
          }
        ],
        "locks": [
          "madoka-a-wish"
        ]
      },
      {
        "key": "let-her-choose",
        "title": "Let her choose",
        "about": "Homura lets Madoka choose for herself, and watches from a distance.",
        "rewards": [
          {
            "coins": 500
          },
          {
            "gift": "manga"
          }
        ]
      }
    ]
  }
]
HOMURA_AKEMI_SCENES = [
  {
    "name": "World: Homura Akemi, School",
    "lines": [
      "background classroom",
      "me enters right with slide",
      "me: You shouldn't be here this early.",
      "player: I just wanted to talk.",
      "me (dismayed): You knew my name before we'd met. That's the first thing I'd like explained.",
      "player: I don't know how.",
      "me: Then stay away from her. Madoka must never make a contract."
    ]
  },
  {
    "name": "World: Homura Akemi, Rooftop",
    "lines": [
      "background night",
      "me enters center with fade",
      "me: I've lived this month more times than I can count. Every time, she makes the same wish.",
      "player: What happens after?",
      "me (dismayed): I don't remember how it ends, only how it starts again.",
      "me: Help me stop it. Once more."
    ]
  }
]
KYOKO_SAKURA_QUESTS = [
  {
    "key": "kyoko-eat-it-all",
    "title": "Eat It All",
    "gates": 2,
    "about": "Kyoko shares food with people who don't waste it, and she'll watch to see whether you do.",
    "offer": [
      "them: Here. Eat that. If you waste it, I'll know.",
      "them (pleased): Don't look so surprised. Just finish the apple."
    ],
    "stages": [
      {
        "text": "Find Kyoko in the alley in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "alley",
            "times": [
              2
            ],
            "scene": "World: Kyoko Sakura, Alley",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Share some melon bread with Kyoko",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "melon-bread",
            "to": "Kyoko Sakura"
          }
        ]
      },
      {
        "text": "Talk to Kyoko over the bread",
        "objectives": [
          {
            "do": "talk",
            "to": "Kyoko Sakura",
            "script": [
              "them: You finished the apple. So you get another. That's how it works.",
              "them (pleased): ...Friendship, by my rules."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "finish-the-apple",
        "title": "Finish the apple",
        "about": "Kyoko gives you another apple, then a third. You can't tell whether it's a gift or a test.",
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
    "key": "kyoko-fathers-church",
    "title": "Father's Church",
    "gates": 5,
    "about": "The ruined chapel that Kyoko never visits, and what her wish did to her family.",
    "offer": [
      "them (dismayed): There's a ruined chapel by the shrine. I haven't been back in years.",
      "them: Come with me. I don't want to go alone."
    ],
    "stages": [
      {
        "text": "Meet Kyoko at the shrine at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "shrine",
            "times": [
              1
            ],
            "scene": "World: Kyoko Sakura, Shrine",
            "rewards": [
              {
                "pack": "level_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Kyoko Wishes for a Miracle",
        "objectives": [
          {
            "do": "have_card",
            "card": "MM/W17-E069"
          }
        ]
      },
      {
        "text": "Let Kyoko pray",
        "objectives": [
          {
            "do": "talk",
            "to": "Kyoko Sakura",
            "script": [
              "them: I haven't prayed in years. I'm bad at it.",
              "them (pleased): ...There. That's enough for now."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "pray-with-her",
        "title": "Pray with her",
        "about": "Kyoko tells you what her wish cost her family, and asks you to keep it.",
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
KYOKO_SAKURA_SCENES = [
  {
    "name": "World: Kyoko Sakura, Alley",
    "lines": [
      "background city",
      "me enters right with slide",
      "me: Catch. Eat it. All of it. Core too.",
      "player: The core too?",
      "me (pleased): The core too. Nothing goes to waste around me.",
      "me: You didn't spit it out. That's the first good sign."
    ]
  },
  {
    "name": "World: Kyoko Sakura, Shrine",
    "lines": [
      "background shrine",
      "me enters center with fade",
      "me: My father's church. Ruined. My wish did that.",
      "player: You don't have to tell me.",
      "me (dismayed): I know. I want to. Once.",
      "me: My family was everything, and I wished for something that tore them apart.",
      "me (pleased): Now I pray, badly. You can laugh. I won't mind."
    ]
  }
]
MAMI_TOMOE_QUESTS = [
  {
    "key": "mami-tea-time",
    "title": "Tea Time",
    "gates": 2,
    "about": "Mami has baked far too much for one person, and she's set out a tea service for two.",
    "offer": [
      "them (pleased): Oh, you're here. I baked. Sit, please.",
      "them: There's far too much cake for one person, so you'll help."
    ],
    "stages": [
      {
        "text": "Join Mami for tea at the cafe at noon",
        "objectives": [
          {
            "do": "visit",
            "place": "cafe",
            "times": [
              1
            ],
            "scene": "World: Mami Tomoe, Cafe",
            "rewards": [
              {
                "coins": 150
              }
            ]
          }
        ]
      },
      {
        "text": "Bring Mami a strawberry shortcake",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "shortcake",
            "to": "Mami Tomoe"
          }
        ]
      },
      {
        "text": "Let Mami talk about the cakes",
        "objectives": [
          {
            "do": "talk",
            "to": "Mami Tomoe",
            "script": [
              "them: That one is a sponge. That one is a mistake. Don't tell anyone.",
              "them (pleased): Will you come back tomorrow? Please?"
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "come-back-tomorrow",
        "title": "Come back tomorrow",
        "about": "Mami sets out the cups for two every day now, and never explains why.",
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
    "key": "mami-not-alone",
    "title": "Not Alone",
    "gates": 5,
    "about": "Mami admits why she's always hosting. She's been alone since the accident, and fighting alone too.",
    "offer": [
      "them (dismayed): Can I tell you why I keep baking?",
      "them: I don't want you to think it's silly."
    ],
    "stages": [
      {
        "text": "Watch the sunset with Mami on the rooftop",
        "objectives": [
          {
            "do": "visit",
            "place": "rooftop",
            "times": [
              2
            ],
            "scene": "World: Mami Tomoe, Rooftop",
            "rewards": [
              {
                "pack": "color_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Mami is \"No Longer Alone\"",
        "objectives": [
          {
            "do": "have_card",
            "card": "MM/W17-E008"
          }
        ]
      },
      {
        "text": "Answer Mami's question",
        "objectives": [
          {
            "do": "talk",
            "to": "Mami Tomoe",
            "script": [
              "them: Will you be my partner? In the fights, and everything?",
              "them (pleased): ...Then I'm not alone, am I?"
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "partners",
        "title": "Be her partner",
        "about": "Mami holds out a cake for you to share at the next battle. She says it's a promise.",
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
MAMI_TOMOE_SCENES = [
  {
    "name": "World: Mami Tomoe, Cafe",
    "lines": [
      "background cafe",
      "me enters center with fade",
      "me: Oh, you came! I set out a full service. I hope you're hungry.",
      "player: Is all of this for me?",
      "me (pleased): For two. I hoped someone would come.",
      "me: That's a lemon curd tart. That's a vanilla sponge. Try the mistake, it's the best one."
    ]
  },
  {
    "name": "World: Mami Tomoe, Rooftop",
    "lines": [
      "background dusk",
      "me enters left with slide",
      "me: I always host because I'm afraid of an empty table.",
      "player: Since when?",
      "me (dismayed): Since the accident. Since it was only me.",
      "me: Will you be my partner? I don't want to fight alone any more.",
      "me (pleased): ...Thank you. Now eat your cake."
    ]
  }
]
SAYAKA_MIKI_QUESTS = [
  {
    "key": "sayaka-the-violinist",
    "title": "The Violinist",
    "gates": 2,
    "about": "Sayaka wants a CD signed for a friend in hospital, and she's practising what to say out loud.",
    "offer": [
      "them: I need to ask someone for a signature. I've practised all week.",
      "them (dismayed): Don't laugh. Please just listen to my lines."
    ],
    "stages": [
      {
        "text": "Find Sayaka at school in the morning",
        "objectives": [
          {
            "do": "visit",
            "place": "school",
            "times": [
              0
            ],
            "scene": "World: Sayaka Miki, School",
            "rewards": [
              {
                "coins": 200
              }
            ]
          }
        ]
      },
      {
        "text": "Give Sayaka a set of earbuds for her friend's playlist",
        "objectives": [
          {
            "do": "give_gift",
            "gift": "earbuds",
            "to": "Sayaka Miki"
          }
        ]
      },
      {
        "text": "Let Sayaka rehearse once more",
        "objectives": [
          {
            "do": "talk",
            "to": "Sayaka Miki",
            "script": [
              "them (pleased): You're a better friend than I deserve, you know that?",
              "them: Okay. Now the lines. Properly this time."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "be-her-friend",
        "title": "Be her friend",
        "about": "Sayaka gets the signature and gives you a copy of the CD, with the best track marked.",
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
    "key": "sayaka-mermaids-wish",
    "title": "Mermaid's Wish",
    "gates": 5,
    "about": "Sayaka made a wish for someone else, and wonders whether it was worth what it cost her.",
    "offer": [
      "them (dismayed): I made a wish once. For someone else. Was it worth it?",
      "them: Come to the beach. I'll tell you there."
    ],
    "stages": [
      {
        "text": "Meet Sayaka at the beach in the evening",
        "objectives": [
          {
            "do": "visit",
            "place": "beach",
            "times": [
              2
            ],
            "scene": "World: Sayaka Miki, Beach",
            "rewards": [
              {
                "pack": "climax_pack"
              }
            ]
          }
        ]
      },
      {
        "text": "Have Sayaka Finds Her Wish",
        "objectives": [
          {
            "do": "have_card",
            "card": "MM/W17-E088"
          }
        ]
      },
      {
        "text": "Give Sayaka your answer",
        "objectives": [
          {
            "do": "talk",
            "to": "Sayaka Miki",
            "script": [
              "them: Can anyone be a hero without getting anything back?",
              "them (pleased): ...You count as something back. Decided."
            ]
          }
        ]
      }
    ],
    "endings": [
      {
        "key": "something-back",
        "title": "Be something back",
        "about": "Sayaka decides you count as the thing she gets back, and she stops counting the cost.",
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
SAYAKA_MIKI_SCENES = [
  {
    "name": "World: Sayaka Miki, School",
    "lines": [
      "background classroom",
      "me enters center with fade",
      "me: Hi. I'm going to say hello to Kyosuke. Watch me do it.",
      "me (dismayed): Hi, Kyosuke. I... um. I'm... nevermind.",
      "player: Try again, slower.",
      "me (pleased): Hi, Kyosuke. I'm here to ask you something. Nice. Nice.",
      "me: You're not going to laugh at me. Thanks."
    ]
  },
  {
    "name": "World: Sayaka Miki, Beach",
    "lines": [
      "background dusk",
      "me enters right with slide",
      "me: Once I wished for a friend to be well. She is. I think.",
      "player: You don't know?",
      "me (dismayed): I don't know what I'd have had left, if I'd wished for myself.",
      "me: You stayed. That counts, doesn't it?",
      "player: It counts."
    ]
  }
]

CAST = [
    cpu("Akane Kurokawa", "friendly", quests=AKANE_KUROKAWA_QUESTS, extra_scenes=AKANE_KUROKAWA_SCENES,
        haunts=[("library", "wk", "12", 60), ("school", "we", "01", 40), ("cafe", "135", "2", 35)],
        tastes=(["book"], ["calm", "drink"], ["cool"]),
        lines={
            "repeat": {"future": ["them: Next I'm rehearsing the scene where I don't cry. It's harder than it sounds.", "them (pleased): Tomorrow I've got a read-through. Come and tell me if I'm believable.", "them (pleased): Tonight I'm writing a new character. I want you in it, if you'll let me."], "past": ["them: Earlier I walked the same hallway forty times, copying someone's walk.", "them (pleased): This morning I cried in the dressing room. Don't tell the director.", "them (pleased): Earlier I finally made a friend in the cast. You're not the only one, I promise."], "like": {"with": "Ai", "lines": ["them: You're nothing like Ai. She'd have had the audience in tears by now.", "them: You're a bit like Ai. Hm, that's a complicated compliment.", "them (pleased): You're like Ai, {player}, real behind the smile. That's the best I can say."]}, "dislike": {"with": "Aqua", "lines": ["them: You're so much like Aqua it makes me nervous.", "them: There's a bit of Aqua in how you hold the camera. Stop it.", "them (pleased): You're nothing like Aqua, {player}. I'm really glad about that."]}},
            "tournament": {"spectator": [["them: I'm not in the bracket. I'm studying the crowd instead."], ["them: Not in this one. But I'll copy your victory pose, I promise."], ["them (pleased): I'm not entering. Win it, and I'll write the scene for the story."]], "entrant": [["them: I'm in the bracket. I'll be in character the whole time.", "them: Don't take it personally when I win. It's just the role."], ["them (pleased): We're both in it! Let's make the crowd remember us.", "them: I'll be playing my best. Nothing less for a friend."], ["them (pleased): You and me in the same bracket, {player}. It's my favourite kind of script.", "them (pleased): Let's make the final a real performance."]], "out": [["them: Out already? Ah, it was a good scene, though."], ["them: You fought well. Let's go through the notes later."], ["them (pleased): You're out, but you were perfect in that last duel. Come rehearse with me."]], "champion": [["them (pleased): The champion! You were brilliant. I'll put it in the script."], ["them (pleased): You won! I could never have written that ending better."], ["them (pleased): Champion, {player}! Best audience and best duelist in town."]], "duel": [["them: It's the round. I'll do my best, and so should you.", "them: Lights, camera, duel. Don't blink."], ["them (pleased): Round time. Let's see whose performance is better.", "them: No holding back. Not for a friend."], ["them (pleased): Our round, {player}. I'd rather perform for you than against you.", "them (pleased): Give me your best, and I'll give you my honest one."]]},
            "mid": {"1": ["them: I've been reading your habits. Don't worry, it's for a role.", "them (pleased): You're not as dull as I first thought. That's a compliment.", "them: What's the one thing you'd never tell a stranger? I'm asking for the script.", "them: Do you know how many times I've practised walking into a room? Hundreds.", "them: Sit. I need a reaction from you. Be honest."], "3": ["them (pleased): Your face is my favourite study. Please don't stop being yourself.", "them: I used to play the perfect girl. You make me want to be a little messy.", "them: I've been thinking about Aqua. I'm worried about him. Are you?", "them (pleased): Come to the rehearsal. I want you to see the real me, not the role.", "them: You copy me better than I copy you. We'd make a good duo."], "5": ["them (pleased): {player}, my real friend, the one who isn't a character to me.", "them: I'd stop any role for you. That's the most honest thing I've ever said.", "them (pleased): Let's go somewhere quiet. I'm tired of being on stage.", "them: You're the only one who knows my real laugh. Keep it that way.", "them (pleased): Best friend. I'll keep the notebook, and throw away the role."]},
            "hello_steps": [["them: Oh! Sorry, I was miles away. Can I help you?", "them: Hi. Don't mind me, I'm running lines."], ["them: Ah, hello. Do you have time to talk for a second?", "them: Oh, hi! Are you here for the play?"], ["them (pleased): {player}! Good, I could use a break from this script.", "them (pleased): Hi, {player}. Want to help me rehearse?"], ["them (pleased): {player}! Perfect timing. I was just watching how you walk.", "them (pleased): {player}, hi! I've got a new idea for a role."], ["them (pleased): {player}. You're exactly who I wanted to see today.", "them (pleased): Hey, {player}. I'm glad you came. Sit with me a bit."], ["them (pleased): {player}. I like who I am around you. That's rare, you know.", "them (pleased): {player}! My favourite co-star. Come see the new scene!"]],
            "bye_steps": [["them: Ah, okay. Take care.", "them: Bye. Keep your head down out there."], ["them: See you. Good luck with whatever you're doing.", "them: Bye! Watch the crowd on the way out."], ["them (pleased): See you, {player}. Wish me luck at rehearsal.", "them (pleased): Bye, {player}! Don't forget your notebook."], ["them (pleased): Go on, {player}. Come back and tell me how you did.", "them (pleased): Bye, {player}! I'll be practising. Come watch."], ["them (pleased): Come back soon? I like who I am around you, {player}.", "them (pleased): Take care, {player}. Don't make me wait too long!"], ["them (pleased): Go, {player}. Come back. My best audience is you.", "them (pleased): Bye, best friend. Keep watching me."]],
            "cold": "them (dismayed): You let him cross the line. I can't play the friend who pretends that was fine.",
            "hello": ["them: Oh! Sorry, I was miles away. Can I help you?", "them (pleased): {player}! Good, I could use a break from this script.", "them (pleased): {player}. You're exactly who I wanted to see."],
            "bye": ["them: Ah, okay. Take care.", "them (pleased): See you, {player}. Wish me luck at rehearsal.", "them (pleased): Come back soon? I like who I am around you."],
            "hi": ["them: Oh, hello. I'm Akane. Sorry, I was studying a role. I sometimes forget where I am.",
                   "them: Are you here to duel? I've been reading up on it. Character analysis helps."],
            "hi2": "them (pleased): {player}! I've been thinking about how you'd play yourself in a drama. Is that strange?",
            "hi4": "them (pleased): You're the one person I don't have to perform for. It's such a relief.",
            "again": "them: Back again? I'll take notes. You're interesting.",
            "loved": "them (pleased): A book! I'll read it tonight. And probably analyse every character.",
            "disliked": "them (dismayed): It's very... cool. I'm not sure it's me. Unless I'm playing someone else.",
            "before": "them: I've studied your style. Let me show you what I've learned.",
            "won": "them (dismayed): I misread you. I'll do better research next time.",
            "lost": "them (pleased): Preparation is everything, you know.",
            "r1": "them: You don't judge people for what the internet says about them. Thank you.",
            "r3": "them: Once, I was hated by a whole country for a single scene. I nearly... It doesn't matter. I'm glad I'm here now.",
            "r4": "them (pleased): I'd cast you as a lead. In my life, I mean. Sorry, that was a lot.",
        },
        friend=["background library", "me enters left with fade", "me: Can you help me with something? I'm building a character.",
                "me: I need to understand what makes someone kind without trying to be.", "player: And you picked me?",
                "me (pleased): You're my reference. I've been watching how you talk to people.",
                "player: That's a little creepy.", "me (dismayed): I know! I'm sorry! It's how I learn!",
                "me: But I also just... like spending time with you. That part isn't research.",
                "me: Friends? Real ones, not scripted?", "player: Not scripted."],
        best=["background rain", "me enters center with fade", "me: Do you remember when I told you about the reality show?",
              "me: People said such cruel things. I believed every one of them.",
              "player: They didn't know you.", "me: You do. That's why it matters so much what you think.",
              "me (pleased): And you never once made me feel like a role.",
              "choice", "- You're more than any role.", "- I'll always see the real you.",
              "me (intro): Then I'll stop hiding behind characters around you. Best friends. No script."]),

    cpu("Aqua Hoshino", "aloof", quests=AQUA_HOSHINO_QUESTS, extra_scenes=AQUA_HOSHINO_SCENES,
        haunts=[("school", "wk", "01", 55), ("cafe", "we", "12", 45), ("alley", "135", "3", 30)],
        tastes=(["drink"], ["book", "cool"], ["sweet"]),
        lines={
            "repeat": {"future": ["them: Next I'm checking the shoot schedule. Don't be late.", "them (pleased): Tomorrow I'll look at the footage, and you're in it.", "them (pleased): Tonight I'm going to the alley. Come if you're not afraid of the rain."], "past": ["them: Earlier I stared at the same photo for an hour.", "them (pleased): This morning I made a lead chart on the wall. It's a mess.", "them (pleased): Earlier I didn't smile for the camera. Not once. You noticed?"], "like": {"with": "Ai", "lines": ["them: You're nothing like Ai. She never looked tired.", "them: You're a bit like Ai. The sincere part, maybe.", "them (pleased): You're like Ai, {player}, the real one. I trust you more for it."]}, "dislike": {"with": "Akane Kurokawa", "lines": ["them: You're so much like Akane. Always studying people.", "them: There's a little Akane in you. I'm watching that.", "them (pleased): You're nothing like Akane, {player}. Thank goodness."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament. I don't do crowds."], ["them: I'm not in the bracket. Keep the camera off me, please."], ["them (pleased): Not entering. I'll watch, and I'll see you win it."]], "entrant": [["them: I'm in the bracket. Don't expect me to smile for the cameras.", "them: Stay sharp. I'm not going easy."], ["them: We're both in it. Hm. I didn't expect that.", "them (pleased): Let's see who's more sincere on the big stage."], ["them (pleased): You and me in the bracket. I'd trust you with the final.", "them (pleased): Win it, then tell me something true."]], "out": [["them: Out. Fine. Next time, I'll see you on the other side of the bracket."], ["them: You lost. It happens. Don't make a show of it."], ["them (pleased): You're out. Come walk the alley with me. Quietly."]], "champion": [["them (pleased): You won. Ha. The cameras would have loved that."], ["them (pleased): Champion. I'll admit it. You're worth watching."], ["them (pleased): Champion, {player}. The only witness I'd want on that stage."]], "duel": [["them: It's our round. Don't waste my time.", "them: I'll be focused. Stay focused too."], ["them: Round time. Let's see what you've got.", "them (pleased): No camera. Just you and me."], ["them (pleased): Our round, {player}. I'd rather you were my witness than my opponent."]]},
            "mid": {"1": ["them: You're watching me. I can tell. Just don't film me.", "them: I don't trust people easily. You're in the middle, for now.", "them: The camera shows what people want. I don't.", "them: Do you ever get tired of pretending? I do.", "them: Fine. You can come to the set. Stay out of the shot."], "3": ["them (pleased): You're the only one I don't have to act around. It's a relief.", "them: I've been looking for a name. I think I'm getting close.", "them (pleased): That photo of Ai you saw. I wish I could forget it. You help.", "them: You're honest on camera and off. It's rare in this business.", "them (pleased): Come on, let's walk the alley. It's quieter that way."], "5": ["them (pleased): {player}, you're the witness I need, and the friend I want.", "them: Ai would've liked you. She was always honest with her fans.", "them (pleased): When this is over, I'll show you the real Aqua. No camera.", "them: You were the only one who didn't look away from me.", "them (pleased): Best friend. Stay close while I finish this, okay?"]},
            "hello_steps": [["them: ...What.", "them: Yeah? Can I help you?"], ["them: Oh. Hi. You're in the way of the lights, though.", "them: You again. Fine. Sit."], ["them (pleased): Oh, {player}. It's you. Fine. Sit.", "them (pleased): {player}. You're easy to be around. Sorry, that's a weird thing to say."], ["them (pleased): {player}. Good. I need someone who doesn't fake their face.", "them (pleased): ...{player}. Hey. Good to see you."], ["them (pleased): ...Hey. I was waiting. Don't make it weird.", "them (pleased): {player}. You know which of my smiles is real. Sit with me."], ["them (pleased): {player}. The only person I don't need to act for.", "them (pleased): {player}. You came back. I'm not going to say anything else."]],
            "bye_steps": [["them: Right.", "them: Go. Don't waste my lights."], ["them: See you.", "them: Later."], ["them (pleased): See you, {player}. Don't make it a big thing.", "them (pleased): Bye, {player}. Keep your shoulders loose."], ["them (pleased): Go on. Come back when the shoot's done.", "them (pleased): Bye, {player}. Stay sincere out there."], ["them (pleased): Come back tomorrow. If you want to.", "them (pleased): ...Bye, {player}. Don't get hurt."], ["them (pleased): Go. Come back soon. I'll keep your seat in the shot.", "them (pleased): Bye, {player}. You're the only one I'd trust with a witness."]],
            "cold": "them: You stopped me. Fine. Stay out of my way from now on.",
            "hello": ["them: ...What.", "them: Oh. It's you. Fine. Sit.", "them (pleased): ...Hey. I was waiting. Don't make it weird."],
            "bye": ["them: Right.", "them: See you.", "them (pleased): ...Come back tomorrow. If you want."],
            "hi": ["them: Aqua. I'm not interested in chatting, but I'll duel if that's why you're here.",
                   "them: You look like someone with too much free time. Lucky."],
            "hi2": "them: You again. Sit, if you want. I'm reading scripts.",
            "hi4": "them (pleased): ...Hey. I saved you a coffee. Don't make it a thing.",
            "again": "them: You're persistent. I'll give you that.",
            "loved": "them (pleased): Black coffee. You've been paying attention.",
            "disliked": "them (dismayed): Too sweet. Give it to Ruby, she'll love it.",
            "before": "them: I read people for a living. Let's see what you're hiding.",
            "won": "them (dismayed): ...I underestimated you. That won't happen again.",
            "lost": "them: Predictable. Work on that.",
            "r1": "them: You don't want anything from me. That's rarer than you'd think.",
            "r3": "them: I have something I have to do. Something I can't talk about. But being around you makes me forget it, for a while.",
            "r4": "them (pleased): If I ever lose myself... drag me back, okay? I mean it.",
        },
        friend=["background night", "me enters right with fade", "me: You keep showing up. Why?",
                "player: Because I like talking to you.", "me (dismayed): Nobody likes talking to me. I make sure of it.",
                "me: Everyone I get close to ends up in danger. It's easier to keep people away.",
                "player: You're not keeping me away.", "me: ...No. I'm apparently terrible at it with you.",
                "me (pleased): Fine. Friends. Don't say I didn't warn you."],
        best=["background sakura", "me enters center with fade", "me: My mother used to say lies are a kind of love.",
              "me: I've told so many. To everyone. Even to myself.", "player: Do you lie to me?",
              "me: Not once. That's the strange part. I can't, with you.",
              "me (intro): I spent years thinking I'd never get to just be... a person. You let me.",
              "choice", "- You deserve to be happy, Aqua.", "- No more lies between us.",
              "me (pleased): Best friend. Okay. Don't let me screw it up."]),

    cpu("Kana Arima", "aloof", quests=KANA_ARIMA_QUESTS, extra_scenes=KANA_ARIMA_SCENES,
        haunts=[("school", "wk", "12", 55), ("plaza", "we", "12", 45), ("cafe", "024", "2", 30)],
        tastes=(["sweet"], ["music", "cute"], ["cool"]),
        lines={
            "repeat": {"future": ["them: Next I'm practising the bow. Ugh, it's a pain.", "them (pleased): Tomorrow I've got an audition. Pretend you're the director.", "them (pleased): Tonight I'm going to have dessert. Come and judge my choice."], "past": ["them: Earlier I cried for ten seconds. Exactly. Don't mention it.", "them (pleased): This morning I told off a stylist. She deserved it.", "them (pleased): Earlier I laughed at my own joke. It wasn't even funny."], "like": {"with": "Ruby Hoshino", "lines": ["them: You're nothing like Ruby. She's all sunshine, and you're not.", "them: You're a bit like Ruby. Enthusiastic, I suppose.", "them (pleased): You're like Ruby, {player}, but with better manners. That's high praise, from me."]}, "dislike": {"with": "Akane Kurokawa", "lines": ["them: You're so much like Akane. You copy everyone.", "them: There's a bit of Akane in you. Please stop watching me.", "them (pleased): You're nothing like Akane, {player}. Good. I'd hate that."]}},
            "tournament": {"spectator": [["them: I'm not entering. Everyone would want my autograph and I'm busy."], ["them: Tournament? Please don't make me cry on the stage again."], ["them (pleased): I'm not in it. I'll cheer, quietly. Don't tell anyone."]], "entrant": [["them: I'm in the bracket. Don't look at me like that. I'm working.", "them: I'll win, and then I'll eat three desserts. That's the plan."], ["them: We're both in it. Ugh. Fine. Let's go.", "them (pleased): Don't go easy on me. I don't want charity."], ["them (pleased): You and me in the bracket. Of course it's you I'd want to face.", "them (pleased): Win it, and we'll eat cake after. Both of us."]], "out": [["them: Out. Fine. I'm not crying. The stage lights made my eyes wet, that's all."], ["them: You lost. It's fine. Don't say I was watching."], ["them (pleased): You're out. Come have dessert. I'll pay."]], "champion": [["them (pleased): The champion? Hmph. I knew you'd win. I'm not impressed. Okay, I am."], ["them (pleased): You won! I'm totally not crying. These are happy tears, obviously."], ["them (pleased): Champion, {player}. Dessert on me, for the whole week."]], "duel": [["them: It's our round. Ten seconds to cry, and then I'm winning.", "them: Don't go easy on me, or I'll know."], ["them: Round time. Do you think I can win this one?", "them (pleased): Let's see if you're as good as I think."], ["them (pleased): Our round, {player}. Please don't cry if I beat you. I'll be sad enough for both of us."]]},
            "mid": {"1": ["them: Don't get too comfortable. I'm still working on my face.", "them: You're not terrible at acting. You're just not trying.", "them: What makes you cry? Be honest. I'm taking notes.", "them: That dessert place is overrated. Don't tell the others.", "them: Stand over there. Your shadow is ruining my lighting."], "3": ["them (pleased): You actually listened when I said I was too old. Thanks.", "them: Nobody else asks me how the rehearsals went. You do.", "them (pleased): You can have the strawberry cake. I'm not hungry anyway.", "them: You're the first person I've cried in front of. Well, almost.", "them (pleased): Come with me to the audition. I'll get through it if you're there."], "5": ["them (pleased): {player}, my real friend. Not the child star. Just me.", "them: You're the only one who remembers me when I'm not on stage.", "them (pleased): Let's go somewhere with no cameras. Just the two of us.", "them: I'd cry for you, if I were ever sad. Real tears, I promise.", "them (pleased): Best friend. Don't tell anyone I said that. Okay?"]},
            "hello_steps": [["them: Yes? Autographs are five hundred yen.", "them: Hm. Don't stare. I'm working."], ["them: Oh. You. Need something?", "them: Hi. You're not going to ask me to cry again, are you?"], ["them (pleased): Oh, it's you! Took you long enough to say hi.", "them (pleased): {player}. Hi. Did you see my practice?"], ["them (pleased): {player}! Finally! Do you know how long I've been standing here?", "them (pleased): Hey, {player}. Don't tell anyone, but I was hoping you'd come."], ["them (pleased): {player}. You're the only one who saw me try to cry. Hi.", "them (pleased): {player}! Come on, let's eat something sweet."], ["them (pleased): {player}. Glad you're here. Really. Don't make it weird.", "them (pleased): {player}! My best friend, and I'm not saying it twice."]],
            "bye_steps": [["them: Hmph. Bye.", "them: Go on, then."], ["them: Fine, go.", "them: See you. Whatever."], ["them (pleased): Fine, go, {player}. Not like I'll miss you or anything.", "them (pleased): Bye, {player}. Don't tell anyone I said that."], ["them (pleased): Go, {player}. Come back before my next audition.", "them (pleased): Bye, {player}. You'd better come back."], ["them (pleased): You'd better come back, {player}. I mean it.", "them (pleased): Go. Ten seconds to cry, remember? Come back for that."], ["them (pleased): Go, {player}. Come back soon. I'll save you a dessert.", "them (pleased): Bye, best friend. I'm going to miss you, ugh."]],
            "hello": ["them: Yes? Autographs are five hundred yen.", "them (pleased): Oh, it's you! Took you long enough to come say hi.", "them (pleased): Finally! Do you know how long I've been standing here?"],
            "bye": ["them: Hmph. Bye.", "them (pleased): Fine, go. Not like I'll miss you or anything.", "them (pleased): You'd better come back. I mean it. Ten seconds to cry, remember?"],
            "hi": ["them: You know who I am, right? The genius child actor? Ten seconds to cry? No? Ugh.",
                   "them: If you're a fan, autographs are after the duel. If you're not, why not?"],
            "hi2": "them: Oh, it's you. I wasn't waiting or anything. I just happened to be here. For an hour.",
            "hi4": "them (pleased): Took you long enough! Come on, I'll buy. Just this once! ...Again.",
            "again": "them: Can't stay away from a star, huh? Understandable.",
            "loved": "them (pleased): S-sweets? For me? Well, I suppose I'll accept them. Graciously.",
            "disliked": "them (dismayed): This is way too edgy. Do I look like an edgy idol to you?",
            "before": "them: Watch closely. This is what a real performer looks like.",
            "won": "them (dismayed): That wasn't fair! I want a retake!",
            "lost": "them (pleased): Hmph! Ten seconds to win. A natural.",
            "r1": "them: You're not bad. Don't let it go to your head. I mean it!",
            "r3": "them: Everyone forgot me when I stopped being a child star. You didn't even know who I was, and you stayed. That's... nice.",
            "r4": "them (pleased): I'm going to be the brightest idol ever. And you're going to be in the front row. That's an order.",
        },
        friend=["background city", "me enters left with slide", "me: Okay. I need an audience. Just one person.",
                "me: I'm practising a song for the next show. Tell me honestly how it is.", "me sways", "narrator: She sings a verse, a little nervous, then not at all.",
                "player: It was really good.", "me (pleased): R-really? You're not just saying that?",
                "me: Everyone in the industry just says things. I can never tell what's true.",
                "me: But you're a terrible liar. So I believe you.", "me bounces",
                "me: Fine! You can be my friend! My first-row, honest friend!"],
        best=["background dusk", "me enters center with fade", "me: Can I tell you something embarrassing?",
              "me: When I was little, I was the best at everything. Then I wasn't. And everyone left.",
              "me: I got so scared of being forgotten that I pushed everyone away first.",
              "player: I'm not going anywhere, Kana.", "me (dismayed): You keep saying that. And you keep proving it.",
              "choice", "- I'll never forget you.", "- Front row, every show.",
              "me (pleased): Then I'll shine so bright you'll never need to look anywhere else. Best friend. Got it?"]),

    cpu("Ruby Hoshino", "warm", quests=RUBY_HOSHINO_QUESTS, extra_scenes=RUBY_HOSHINO_SCENES,
        haunts=[("school", "wk", "01", 55), ("plaza", "we", "12", 50), ("cafe", "135", "2", 35)],
        tastes=(["music"], ["cute", "sweet"], ["book"]),
        lines={
            "repeat": {"future": ["them: Next I'm practising the new routine. Watch me fall over!", "them (pleased): Tomorrow's the big rehearsal! You're coming, right?", "them (pleased): Tonight I'm going to the cafe. Save me a seat, okay?"], "past": ["them: Earlier I fell over in front of the whole crew. It was funny.", "them (pleased): This morning I sang for the cat. It loved it.", "them (pleased): Earlier I wrote a song about you. It's a bit silly."], "like": {"with": "Ai", "lines": ["them: You're nothing like Mum. Mum's the best, you're just not her.", "them: You're a bit like Mum. The way you listen, I think.", "them (pleased): You're like my mum, {player}. I think she'd have liked you."]}, "dislike": {"with": "Kana Arima", "lines": ["them: You're so much like Kana. All sulky and serious.", "them: There's a bit of Kana in you. Please smile more!", "them (pleased): You're nothing like Kana, {player}. Yay, that's a relief!"]}},
            "tournament": {"spectator": [["them: I'm not in the tournament! I'm your biggest cheerleader instead!"], ["them: Not in the bracket, but I'll be in the front row, yelling!"], ["them (pleased): I'm not in it! But I'll be dancing for you when you win!"]], "entrant": [["them: I'm in the bracket! Watch me, okay? I've got a new move!", "them: Don't go easy on me! That's no fun!"], ["them: We're both in the tournament! Yay! This is like a real show!", "them (pleased): Let's make the crowd go wild, both of us!"], ["them (pleased): You and me in the bracket! My favourite fan in the final!", "them (pleased): Win it, and we'll celebrate on the stage together!"]], "out": [["them: Aww, out already? You were so close! Next time!"], ["them: You lost, but you fought so hard! I'm still your fan, okay?"], ["them (pleased): You're out, but you're still my number one fan. Come to the show later!"]], "champion": [["them (pleased): CHAMPION! Yay! You're my favourite fan forever!"], ["them (pleased): You won! I'm going to sing you a victory song!"], ["them (pleased): Champion, {player}! Front row seat is yours for life!"]], "duel": [["them: It's our round! Show me your best! I'll show you mine!", "them: Let's dance through this one!"], ["them (pleased): Round time! Don't forget to smile!", "them: No holding back, okay? That's the fun part!"], ["them (pleased): Our round, {player}! I'd hate to beat my number one fan, but I'm going to try!"]]},
            "mid": {"1": ["them (pleased): You're my fan now, right? Please say yes.", "them: Do you like the new song? It's a little tricky to sing.", "them (pleased): Want to hear my favourite dance move? It's a bit silly.", "them: My mum used to dance with me. I still do it in the kitchen.", "them: I'm trying a new routine. Stay and watch me fall over, okay?"], "3": ["them (pleased): You remember all my routines. That's amazing, honestly.", "them: Sometimes I wonder if Mum would have liked you. I think she would.", "them (pleased): Come to the cafe after practice. I'll buy you cake.", "them: You make the stage feel smaller. In a good way.", "them (pleased): Want a sneak peek at the next show? You're the only one I'd show."], "5": ["them (pleased): {player}, you're the first fan who became a real friend.", "them: Mum's ticket is always in my pocket now. Because of you.", "them (pleased): Let's go to the show together. Front row, always.", "them: You're the one I'd want to dance with on the biggest stage.", "them (pleased): Best friend! Come on, let's dance it out together!"]},
            "hello_steps": [["them (pleased): Oh, hi! Are you a fan? You can be a fan!", "them (pleased): Hi! Want to see my dance?"], ["them (pleased): Hi! Have you seen my show poster? It's on every wall!", "them (pleased): Hey! You look like you'd like my new song."], ["them (pleased): {player}! My favourite fan is here!", "them (pleased): {player}! Did you come to watch me practise?"], ["them (pleased): {player}! Okay, today's going to be great now.", "them (pleased): {player}! I've got a new routine. You have to see it."], ["them (pleased): {player}! Yay! You're my first fan, remember?", "them (pleased): {player}! Come sit, I want to show you the bow I finally landed."], ["them (pleased): {player}! My best fan, my best friend. Front row!", "them (pleased): {player}! You're the reason I keep dancing. Hi!"]],
            "bye_steps": [["them (pleased): Byeee!", "them (pleased): See ya! Keep smiling!"], ["them (pleased): Bye! Stay sharp!", "them (pleased): Later! Don't be a stranger!"], ["them (pleased): See ya, {player}! Come to my next show, okay?", "them (pleased): Bye, {player}! Bring the whole team!"], ["them (pleased): Go, {player}! Watch the stage for me!", "them (pleased): Bye! Keep being my first fan!"], ["them (pleased): Come back soon, {player}! Don't keep me waiting!", "them (pleased): Bye, {player}! I'll practise the bow until you're back."], ["them (pleased): Come back soon! Front row seat's always yours, {player}!", "them (pleased): Bye, best friend! I'll be dancing for you!"]],
            "hello": ["them (pleased): Oh, hi! Are you a fan? You can be a fan!", "them (pleased): {player}! My favourite fan is here!", "them (pleased): {player}! Yay! Okay, today's going to be great now."],
            "bye": ["them (pleased): Byeee!", "them (pleased): See you! Come to my next show, okay?", "them (pleased): Come back soon! Front row seat's always yours!"],
            "hi": ["them (pleased): Hi hi! I'm Ruby! I'm going to be an idol like my mom! Want to be my first fan?",
                   "them: Ooh, a duel? I'm gonna win, and then I'm gonna do a little victory dance."],
            "hi2": "them (pleased): {player}! I learned a new dance! Wanna see? You have to say yes!",
            "hi4": "them (pleased): My number one fan! Okay, number two after Onii-chan. Okay, tied!",
            "again": "them: Back again? You must really like me! That's great idol energy!",
            "loved": "them (pleased): Music! Oh, I'm going to listen to this every day! Thank you thank you!",
            "disliked": "them (dismayed): A book... with no pictures? I'll, um, try my best.",
            "before": "them: Shine like a star! That's my strategy!",
            "won": "them (dismayed): Waaah, you're so strong! Teach me!",
            "lost": "them (pleased): I won! Idol power!",
            "r1": "them (pleased): You laughed at my jokes! You're officially my friend-in-training!",
            "r3": "them: Sometimes I miss my mom so much. Being around you makes it a little easier.",
            "r4": "them (pleased): When I'm on the big stage, I'll wave right at you. Promise!",
        },
        friend=["background sakura", "me enters left with pop", "me: {player}! Look! I got my first fan letter!",
                "me: It's from a little girl. She says she wants to be an idol like me.", "me bounces",
                "player: That's amazing, Ruby.", "me (pleased): I used to be in a hospital bed, you know. A long time ago.",
                "me: I watched idols on TV and dreamed. And now someone dreams about me!",
                "me: I wanted to tell my best people first. You're one of them now!"],
        best=["background night", "me enters center with fade", "me: The stars are really bright tonight.",
              "me: Mom used to be the brightest star. Everyone loved her. But she lied a lot, to keep shining.",
              "me: I don't want to lie. I want to shine and be real. Is that silly?",
              "player: It's the bravest thing I've heard.", "me (pleased): You always say exactly the right thing.",
              "choice", "- I'm your biggest fan.", "- Shine as yourself, Ruby.",
              "me (intro): Then I'll be the idol who's real. And you'll be my best friend forever. That's the dream!"]),

    cpu("Legendary Idol Ai", "neutral", quests=LEGENDARY_IDOL_AI_QUESTS, extra_scenes=LEGENDARY_IDOL_AI_SCENES,
        haunts=[("plaza", "wk", "12", 55), ("cafe", "we", "12", 45), ("rooftop", "135", "3", 30)],
        tastes=(["cute"], ["music", "sweet"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to smile for the cameras. All day, probably.", "them (pleased): Tomorrow I've got a fan meet. Come and watch me smile.", "them (pleased): Tonight I'm going up to the rooftop. You can come, if you want."], "past": ["them: Earlier I signed a hundred photos. My hand's still shaking.", "them (pleased): This morning I practised three smiles in the mirror. None felt real.", "them (pleased): Earlier I said something true to a fan. I think it was the first time."], "like": {"with": "Ruby Hoshino", "lines": ["them: You're nothing like Ruby. She's so easy to love.", "them: You're a bit like Ruby. Honest, I think, sometimes.", "them (pleased): You're like Ruby, {player}. Real, kind, and honest. I like that."]}, "dislike": {"with": "Akane Kurokawa", "lines": ["them: You're so much like Akane. Always pretending.", "them: There's a bit of Akane in your smile. I don't like that.", "them (pleased): You're nothing like Akane, {player}. I'm glad you're real."]}},
            "tournament": {"spectator": [["them: I'm not in the bracket. The lights are for someone else tonight."], ["them: Not entering. I'll be watching from the back, smiling."], ["them (pleased): I'm not in it, but I'll sit in the front row for your final."]], "entrant": [["them: I'm in the bracket. Don't mind the flashes.", "them: I'll win with a smile. Watch closely."], ["them (pleased): We're both in it. Oh, I like that.", "them: Let's see whose smile lasts the whole match."], ["them (pleased): You and me in the bracket, {player}. The real kind of smile, for once.", "them (pleased): Win it, and I'll stop acting for an afternoon."]], "out": [["them: Out already? Oh, sweetie. You were still lovely to watch."], ["them: You lost. I'll pretend I didn't notice the tears. Almost."], ["them (pleased): You're out. Come up to the rooftop. The city's quiet tonight."]], "champion": [["them (pleased): Champion. Okay, I'm not acting. That was real."], ["them (pleased): You won, {player}! Hah, I'm smiling for real this time."], ["them (pleased): Champion, {player}. Front row, always, for you."]], "duel": [["them: It's our round. Smile for me, even if you lose.", "them: No acting. Just the real game."], ["them (pleased): Round time! Let's give the fans a show.", "them: Don't hold back. I want to see the real you."], ["them (pleased): Our round, {player}. I'd like to lose to you, a little bit."]]},
            "mid": {"1": ["them: You're not like the other fans. You look at me like I'm a person.", "them (pleased): I wonder if you can tell when I'm smiling for real. Try me.", "them: Don't worry about the cameras. They don't matter here.", "them: What's your favourite song? Mine's the one I can't finish.", "them: You're a good audience. Better than the crowd."], "3": ["them (pleased): You know my real smile now, don't you? Honestly.", "them: I used to think fame was enough. You make it feel less lonely.", "them (pleased): Come to the rehearsal. I want you to hear the unfinished song.", "them: I've been practising the words. They still feel strange, but you help.", "them (pleased): You're the only one who calls me Ai and not the idol. Thank you."], "5": ["them (pleased): {player}... you're the one I'd say the words to, and mean them.", "them: The city lights don't seem as far away when you're beside me.", "them (pleased): Let's walk on the rooftop. No fans, no cameras. Just us.", "them: I love you, and this time it doesn't feel like a lie at all.", "them (pleased): Best friend. Stay with me until the sun comes up?"]},
            "hello_steps": [["them (pleased): Hi there~! Did you come to see me?", "them (pleased): Hello~! Smile for the camera!"], ["them (pleased): Oh, hi~! Don't tell anyone I wasn't ready.", "them (pleased): Hey~! You're in my light, but that's okay."], ["them (pleased): {player}! I saved my best smile for you.", "them (pleased): {player}~! It's always nice to see a familiar face."], ["them (pleased): {player}~! Good, you can tell me which smile is real.", "them (pleased): {player}! Shall we have coffee? Just us."], ["them (pleased): {player}... I'm really glad it's you. No acting.", "them (pleased): {player}. I'm practising with you. Stay a minute."], ["them (pleased): {player}. The one who makes the lights feel warm.", "them (pleased): {player}! My best friend. Don't tell the fans."]],
            "bye_steps": [["them (pleased): Bye-bye~! Love you!", "them (pleased): See you~! Take care!"], ["them (pleased): Bye~! Smile for me on the way out!", "them (pleased): Bye! Don't forget your shades!"], ["them (pleased): See you, {player}! Love you!", "them (pleased): Bye, {player}~! Watch the fans on the way out."], ["them (pleased): Go on, {player}. Come back to the next show!", "them (pleased): Bye, {player}! I'll be looking for you in the crowd."], ["them (pleased): See you soon, {player}. Come back. Please.", "them (pleased): Bye, {player}. I'll keep a smile for you."], ["them (pleased): See you soon. ...I think I really mean it, this time.", "them (pleased): Bye, best friend. I'll be missing you already."]],
            "hello": ["them (pleased): Hi there~! Did you come to see me?", "them (pleased): {player}! I saved my best smile for you.", "them (pleased): {player}... I'm really glad it's you. No acting."],
            "bye": ["them (pleased): Bye-bye~! Love you!", "them (pleased): See you, {player}! Love you!", "them (pleased): See you soon. ...I think I really mean it, this time."],
            "hi": ["them (pleased): Hi there! It's me, Ai! You came to see me, didn't you?",
                   "them: A duel? Sure! Idols should be good at everything. Even cards."],
            "hi2": "them (pleased): {player}! You came back! I remembered your name, see?",
            "hi4": "them (pleased): You know, I can just... talk with you. No smile needed. Isn't that funny?",
            "again": "them: Again? You're my most devoted fan today!",
            "loved": "them (pleased): So cute! I'll keep it on my dressing table.",
            "disliked": "them (dismayed): Spicy food before a show? That's an idol's nightmare!",
            "before": "them: Eyes on me. That's the rule.",
            "won": "them (dismayed): Oh! You beat the idol! That's going in my memory book.",
            "lost": "them (pleased): Sorry~ The spotlight's mine.",
            "r1": "them: You don't treat me like a poster. That's kind of rare.",
            "r3": "them: I've said 'I love you' so many times on stage. I never knew if I meant it. Isn't that sad?",
            "r4": "them (pleased): I think... I actually like you. Not idol-like. Real-like.",
        },
        friend=["background city", "me enters center with pop", "me: Ta-da! The legendary idol, all for you!",
                "player: You don't have to perform for me.", "me (dismayed): ...Oh. Really?",
                "me: I'm always performing. I don't know how to stop. Lies are kind of my thing.",
                "me: But I think I like you. As a friend. That one's true, I'm almost sure.", "me nods",
                "me (pleased): Let's find out together."],
        best=["background night", "me enters center with fade", "me: I have two kids, you know. A secret. Idols can't have kids.",
              "me: I tell them I love them every day. I never knew if it was true.",
              "player: It's true, Ai. You keep choosing them.", "me (dismayed): ...You think so?",
              "me: I think I'm learning. From them. From you.",
              "choice", "- You're not lying now.", "- Love can grow.",
              "me (pleased): I love you, {player}. As my best friend. ...Ah. That one was true. I could feel it."]),

    cpu("Madoka", "warm", quests=MADOKA_QUESTS, extra_scenes=MADOKA_SCENES,
        haunts=[("school", "wk", "01", 60), ("cafe", "we", "12", 45), ("plaza", "135", "2", 35)],
        tastes=(["cute"], ["sweet", "flowers"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to visit Mami's house. She'll have cake.", "them (pleased): Tomorrow I'll walk to school with you, if you'd like.", "them (pleased): Tonight I'm going to think about the wish. Stay with me a bit."], "past": ["them: Earlier a little white creature came to my window again.", "them (pleased): This morning I helped Sayaka with her violin. She was so cross.", "them (pleased): Earlier I told Homura I'd be careful. She didn't believe me."], "like": {"with": "Mami Tomoe", "lines": ["them: You're nothing like Mami. She'd have made me tea by now.", "them: You're a bit like Mami. Kind, I hope.", "them (pleased): You're like Mami, {player}. Kind, and always making the day warmer."]}, "dislike": {"with": "Kyubey", "lines": ["them: You're so much like Kyubey, always making deals.", "them: There's a bit of Kyubey in how you ask me things. Careful.", "them (pleased): You're nothing like Kyubey, {player}. Thank you."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament, but I'll cheer for you."], ["them: I'm not entering. I just want to watch you do your best."], ["them (pleased): I'm not in it. Win this one for me, okay?"]], "entrant": [["them: I'm in the bracket. I'll try my best, even if it's hard.", "them: Please don't be upset if I win. I'll be sorry."], ["them: We're both in it. I'm glad. Really.", "them (pleased): Let's make this a good match, whatever happens."], ["them (pleased): You and me in the bracket. Could there be anything better?", "them (pleased): Win the final, and let me see you smile."]], "out": [["them: You're out. I'm sorry. Next time will be better."], ["them: You lost, but you didn't give up. That's the important part."], ["them (pleased): You're out. Come walk with me. I'll make the time feel longer."]], "champion": [["them (pleased): You won! I'm so happy for you, {player}!"], ["them (pleased): Champion! Remember this moment. I'll keep it, always."], ["them (pleased): You're the champion. I'll make a wish for you tonight. A good one."]], "duel": [["them: It's our round. I'll try, really hard.", "them: Please don't be angry if I win."], ["them (pleased): Round time! Let's do our best together.", "them: I'll hold nothing back, I promise."], ["them (pleased): Our round, {player}. If I lose, I want it to be to you."]]},
            "mid": {"1": ["them: I've been wondering what you'd wish for, if you could. Be honest.", "them: Do you believe in fate? I'm not sure, but I'd like to.", "them: It's nice to have someone new to talk to. Thank you.", "them: Homura keeps telling me to be careful. You don't do that.", "them: Would you like to walk to school together sometime?"], "3": ["them (pleased): You make me feel less afraid of the witches. Thank you.", "them: I think about the wish every night. You're part of why it's easier.", "them (pleased): Let's go to the cafe. Mami will be so happy to see you.", "them: Sayaka and I used to talk like this. I miss her sometimes.", "them (pleased): You're easy to be around. That's what I wish everyone was like."], "5": ["them (pleased): {player}, I'd make any wish for you, if I could.", "them: You're the one I'd want to remember, even if nobody else did.", "them (pleased): Let's go up to the rooftop and see the city lights.", "them: I hope you'll still be here after everything. Please.", "them (pleased): Best friend. Thank you for seeing me, even when it's hard."]},
            "hello_steps": [["them: Oh, hello! Is everything okay?", "them: Hi! Did you need anything?"], ["them: Oh, hi. Nice to see you here.", "them: Hello! Did you come to see Mami?"], ["them (pleased): {player}! I was just thinking about you.", "them (pleased): Hi, {player}! Are you busy today?"], ["them (pleased): {player}! Good, I could use a friend today.", "them (pleased): {player}! Come sit with me. Just for a moment."], ["them (pleased): {player}! Seeing you makes the whole day brighter.", "them (pleased): {player}. Thank you for being here. It means a lot."], ["them (pleased): {player}! My best friend. Please stay as long as you can.", "them (pleased): Hi, {player}. I'll remember this one, I promise."]],
            "bye_steps": [["them: Okay! Take care!", "them: Bye! Be safe."], ["them: See you. Take care!", "them: Bye! Don't do anything reckless."], ["them (pleased): Bye, {player}! See you tomorrow?", "them (pleased): See you, {player}! Don't forget me."], ["them (pleased): Go on, {player}. Come back when you can.", "them (pleased): Bye, {player}! I'll be right here."], ["them (pleased): Come back soon, okay? I'll be right here.", "them (pleased): Bye, {player}. Thank you for coming."], ["them (pleased): Bye, best friend. Remember me, okay?", "them (pleased): Go, {player}. I'll keep the light on for you."]],
            "cold": "them (dismayed): Homura stopped me. I understand why. It still hurts that she had to.",
            "hello": ["them: Oh, hello! Is everything okay?", "them (pleased): {player}! I was just thinking about you!", "them (pleased): {player}! Seeing you makes the whole day brighter."],
            "bye": ["them: Okay! Take care!", "them (pleased): Bye, {player}! See you tomorrow?", "them (pleased): Come back soon, okay? I'll be right here."],
            "hi": ["them (pleased): Oh, hi! I'm Madoka Kaname. Are you new here? I can show you around!",
                   "them: Um, a duel? Okay! I'll do my best. Please go easy on me!"],
            "hi2": "them (pleased): {player}! I drew you a little picture. It's a magical girl version of you!",
            "hi4": "them (pleased): Being with you makes me feel like everything will turn out okay.",
            "again": "them: Hi again! I'm happy you came back.",
            "loved": "them (pleased): It's so cute! I'm going to put it on my bed with my other plushies!",
            "disliked": "them (dismayed): Oh... spicy. That's okay! It's the thought that counts!",
            "before": "them: I want everyone to have a happy ending. Even in a duel!",
            "won": "them (pleased): You're so strong! That was really fun though!",
            "lost": "them (pleased): I won? Wow! Thank you for playing with me!",
            "r1": "them (pleased): I'm really glad we met. You're easy to be around.",
            "r3": "them: Sometimes I feel useless. Everyone else has a power. But you make me feel like I matter just by being me.",
            "r4": "them (pleased): If I ever had one wish, I think I'd wish for everyone to be as kind as you.",
        },
        friend=["background sakura", "me enters left with slide", "me: I brought two bento today! My dad made extra.",
                "me: I thought we could eat together. If you want! No pressure!", "player: I'd love to.",
                "me (pleased): Yay!", "me bounces",
                "me: Mami-san says friends are what keep you going when things are hard.",
                "me: So you're my friend now. That means I'll keep going for you too!"],
        best=["background space", "me enters center with fade", "me: Do you ever wonder what you'd wish for, if you could have anything?",
              "player: What would you wish for?", "me: To save everyone. All the magical girls who suffered. Every single one.",
              "me (dismayed): Even if it meant I disappeared.", "player: Madoka, don't say that.",
              "me (pleased): It's okay. I'm still here. And you'd remember me. I know you would.",
              "choice", "- I'll always remember you.", "- Stay with us, Madoka.",
              "me (intro): Best friends, forever and ever. Across every timeline. That's my promise."]),

    cpu("Homura Akemi", "aloof", quests=HOMURA_AKEMI_QUESTS, extra_scenes=HOMURA_AKEMI_SCENES,
        haunts=[("school", "wk", "01", 55), ("rooftop", "all", "23", 40), ("shrine", "135", "2", 30)],
        tastes=(["calm"], ["book", "cool"], ["cute"]),
        lines={
            "repeat": {"future": ["them: Next I'm checking the timeline. Something's off today.", "them (pleased): Tomorrow I'll walk the school with you. Keep close.", "them (pleased): Tonight I'm going to the shrine. It's quieter there."], "past": ["them: Earlier I counted my loops again. Too many.", "them (pleased): This morning I watched Madoka smile. I'll keep that one.", "them (pleased): Earlier I warned a stranger about a dangerous corner. They listened."], "like": {"with": "Madoka", "lines": ["them: You're nothing like Madoka. She'd have trusted you already.", "them: You're a little like Madoka. Kind, but more careful.", "them (pleased): You're like Madoka, {player}. Kind, and I'd like to keep you close."]}, "dislike": {"with": "Kyubey", "lines": ["them: You're so much like Kyubey. You'd sell her out for a wish.", "them: There's a trace of Kyubey in you. Be careful.", "them (pleased): You're nothing like Kyubey, {player}. I'm glad."]}},
            "tournament": {"spectator": [["them: The tournament is a waste of a loop. I'm watching the crowd."], ["them: I'm not entering. Too many variables."], ["them (pleased): I'm not in it. Win this, and I'll remember it."]], "entrant": [["them: I'm in the bracket. Keep your distance from the scoring desk.", "them: I'll be focused. Stay focused too."], ["them: We're both in the bracket. Hm. Not what I expected this loop.", "them (pleased): Let's see whether we'll meet in the final, this time."], ["them (pleased): You and me in the same bracket. This timeline is a good one.", "them (pleased): Win it, and then let's walk the rooftop together."]], "out": [["them: Out. The timeline has changed. We'll try again next loop."], ["them: You lost. It happens. I'll remember it, though."], ["them (pleased): You're out. Come with me. I'd like someone to talk to today."]], "champion": [["them (pleased): Champion. Good. This one is worth keeping."], ["them (pleased): You won. I'd like to remember this one, as the best timeline."], ["them (pleased): Champion, {player}. The loop was worth it, this time."]], "duel": [["them: It's the round. Keep your guard up.", "them: No mercy. Not in this loop."], ["them (pleased): Round time. I'll try not to lose focus.", "them: Give me everything. Once more, and then never again."], ["them (pleased): Our round, {player}. I'd rather not beat you. But I will."]]},
            "mid": {"1": ["them: You're not the one I expected to see. That's not a bad thing.", "them: I've been counting my loops. You're not part of the count. Yet.", "them: Be careful who you trust. Including me.", "them: Do you like the rain? It reminds me of the first time I stayed.", "them: You may ask me one question. I'll answer it honestly."], "3": ["them (pleased): You're one of the few people I'm glad to see this loop.", "them: I've tried so many times to save her. You're the first to help me think.", "them (pleased): Let's walk to the shrine. It's quieter than the school.", "them: You didn't ask me to explain everything. Thank you for that.", "them (pleased): I would like you to know me, not just the timeline."], "5": ["them (pleased): {player}, my one constant. Please remember this, whatever happens.", "them: In every loop I forget everyone. You're the one I keep choosing.", "them (pleased): Let's sit on the rooftop and just breathe for a minute.", "them: I'll protect Madoka, and I'll protect you too. Both, if I can.", "them (pleased): Best friend. Stay with me. Once more, and then never again."]},
            "hello_steps": [["them: ...Do you need something?", "them: Hm. You shouldn't be here alone."], ["them: You're still around. Be careful.", "them: Oh. You. I didn't expect you to be here."], ["them: It's you. You're still here. Good.", "them: {player}. Don't come near her today."], ["them (pleased): {player}. I was hoping you'd be here.", "them (pleased): {player}. I'm glad this one is going well."], ["them (pleased): ...{player}. I'm glad this timeline has you in it.", "them (pleased): {player}. Sit. Let's breathe for a moment."], ["them (pleased): {player}. You're the one thing I've been able to keep, this time.", "them (pleased): {player}. Please stay. I want to remember this."]],
            "bye_steps": [["them: Be careful.", "them: Watch your back."], ["them: Don't do anything foolish.", "them: Stay away from danger."], ["them: Be careful out there, {player}.", "them: Don't do anything foolish, {player}."], ["them (pleased): Go, {player}. Be safe until next time.", "them (pleased): Bye, {player}. I'll find you again."], ["them (pleased): Come back. Please. I want to remember this one.", "them (pleased): Bye, {player}. You're the one I want to keep."], ["them (pleased): Come back. I'll keep this timeline safe for you.", "them (pleased): Bye, best friend. Come back. Please."]],
            "cold": "them: She chose it. Then I'll stop asking you to choose with me.",
            "hello": ["them: ...Do you need something?", "them: It's you. You're still here. Good.", "them (pleased): ...{player}. I'm glad this timeline has you in it."],
            "bye": ["them: Be careful.", "them: Don't do anything foolish.", "them (pleased): Come back. Please. I want to remember this one."],
            "hi": ["them: ...Who are you? You weren't here in any of the other timelines.",
                   "them: Stay away from Madoka Kaname. That's all I have to say."],
            "hi2": "them: You again. ...You're harmless. I've decided.",
            "hi4": "them (pleased): You remember things I've said. That matters more than you know.",
            "again": "them: You keep coming back. Like a loop.",
            "loved": "them (pleased): Quiet. Simple. ...Thank you.",
            "disliked": "them (dismayed): Cute things remind me of someone. Please don't.",
            "before": "them: I've seen this fight before. I know how it ends.",
            "won": "them (dismayed): ...Another variable I didn't account for.",
            "lost": "them: As expected.",
            "r1": "them: You're an irregularity. I'm starting not to mind.",
            "r3": "them: I've repeated the same month more times than I can count. You're the first new thing in a long time.",
            "r4": "them: In every timeline I've seen, I was alone. Not this one. Not with you.",
        },
        friend=["background rooftop", "me enters right with fade", "me: You keep finding me up here.",
                "player: You keep being up here.", "me: I'm watching. Waiting. For something I can't stop.",
                "me (dismayed): I've tried hundreds of times. Every ending is the same.",
                "player: Maybe this time is different.", "me: ...You sound like her.",
                "me (pleased): Maybe it is. Friend. That word feels strange. I'll get used to it."],
        best=["background night", "me enters center with fade", "me: I'll tell you the truth. I'm a time traveller. I've lived this month again and again.",
              "me: All to save one person. I forgot how to be anything else.",
              "player: You're still you, Homura. Not just your mission.",
              "me (dismayed): Then who am I? Without the loop, without the gun, without her?",
              "player: My best friend.", "me (intro): ...",
              "choice", "- You don't have to fight alone.", "- I'll remember every timeline with you.",
              "me (pleased): Then this is the one I want to keep. This one. With you in it."]),

    cpu("Kyoko Sakura", "aloof", quests=KYOKO_SAKURA_QUESTS, extra_scenes=KYOKO_SAKURA_SCENES,
        haunts=[("alley", "all", "23", 55), ("shrine", "wk", "1", 45), ("plaza", "we", "12", 35)],
        tastes=(["food"], ["sweet", "spicy"], ["fancy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to eat. All of it. Don't get in the way.", "them (pleased): Tomorrow I'll bring a bag of apples. Share them with me.", "them (pleased): Tonight I'm going to the church. Maybe. Come along if you're bored."], "past": ["them: Earlier I ate three hot dogs in a row. Nobody beat me.", "them (pleased): This morning I dropped my last apple. I'm still mad about it.", "them (pleased): Earlier I finished a whole meal without complaining. Don't tell anyone."], "like": {"with": "Mami Tomoe", "lines": ["them: You're nothing like Mami. She'd have made a cake.", "them: You're a bit like Mami. She shares, you share. Hm.", "them (pleased): You're like Mami, {player}. Sharing, and kind to strangers. Good."]}, "dislike": {"with": "Homura Akemi", "lines": ["them: You're so much like Homura. Always watching and judging.", "them: There's a trace of Homura in how you stare. Stop it.", "them (pleased): You're nothing like Homura, {player}. Phew."]}},
            "tournament": {"spectator": [["them: Tournament? Waste of food, if you ask me. I'm watching for the snacks."], ["them: Not in it. Whoever wins gets free snacks, right?"], ["them (pleased): Not in it, but I'll bring you a snack, win or lose."]], "entrant": [["them: I'm in the bracket. Don't cry when I win, I won't be nice.", "them: I'll eat your lunch if you lose. Fair warning."], ["them: We're both in it. Hmph. Let's see who eats more of the prize.", "them (pleased): Don't waste the match, okay?"], ["them (pleased): You and me in the bracket. I'd share my prize with you, if you win.", "them (pleased): Win it, and we'll split the bread."]], "out": [["them: Out. You wasted a good match. Don't waste the next one."], ["them: You lost. Here, have an apple. It's on the house."], ["them (pleased): You're out. Come eat with me. You look hungry."]], "champion": [["them (pleased): Champion? Good. You earned the big prize. Share it."], ["them (pleased): You won! Ha. The snacks are yours now."], ["them (pleased): Champion, {player}. The best eater in the whole tournament."]], "duel": [["them: It's our round. Don't waste the match, okay?", "them: Give it everything. I'm not holding back."], ["them: Round time. I'm hungry, so I'll win.", "them (pleased): Let's not waste this. Please."], ["them (pleased): Our round, {player}. I'd rather share the prize than beat you."]]},
            "mid": {"1": ["them: Hm. You didn't waste that apple. Respect.", "them: My dad's church is a mess. Don't ask about it yet.", "them: You're alright, for a stranger who eats their food.", "them: Want more? Don't make me say it twice.", "them: I don't talk to most people. You're doing okay so far."], "3": ["them (pleased): You keep showing up with food. That's the friend rule, right?", "them: I haven't prayed in years. You make me want to try.", "them (pleased): Come to the alley, I'll show you my favourite spot.", "them: You're the first person who didn't tell me to stop being rude.", "them (pleased): You're my kind of person. Don't tell anyone."], "5": ["them (pleased): {player}, you're my best friend, and you don't waste anything.", "them: I'd take the church back for you, if I could.", "them (pleased): Let's go to the shrine. I'll pray and you can eat.", "them: You're the only person I'd share my last apple with.", "them (pleased): Best friend. Thanks for being the one who finishes the food."]},
            "hello_steps": [["them: *crunch* Whaddaya want?", "them: Hm. You want something to eat?"], ["them: Oh, it's you. Yeah, hi.", "them: You look hungry. Want an apple?"], ["them (pleased): Hey, it's you. Want a pocky? Kidding. Here.", "them (pleased): {player}. Hungry? Come on, I'm buying."], ["them (pleased): {player}! Took you long enough. Want some ramen?", "them (pleased): Hey, {player}. Don't waste the food today."], ["them (pleased): There ya are, {player}! I saved you the best bite.", "them (pleased): {player}! Come sit. I've got news about the church."], ["them (pleased): {player}! You're my best friend. Eat up, okay?", "them (pleased): Hey, {player}. Didn't waste a thing today, right?"]],
            "bye_steps": [["them: Yeah, see ya.", "them: Later. Don't spill your food."], ["them: Bye. Keep your hands clean.", "them: See ya. Don't waste anything."], ["them (pleased): Later. Don't waste food while I'm gone, {player}.", "them (pleased): See ya, {player}. Eat something on the way."], ["them (pleased): Go on, {player}. I'll bring snacks next time.", "them (pleased): Bye, {player}. Stay out of trouble."], ["them (pleased): Come back, alright? It's boring without ya, {player}.", "them (pleased): Bye, {player}. Don't make me come find you."], ["them (pleased): Come back soon. Best friends share food, right?", "them (pleased): Bye, best friend. I'll save you a bite."]],
            "hello": ["them: *crunch* Whaddaya want?", "them (pleased): Hey, it's you. Want a pocky? Kidding. Here.", "them (pleased): There ya are! Took ya long enough."],
            "bye": ["them: Yeah, see ya.", "them (pleased): Later. Don't waste food while I'm gone.", "them (pleased): Come back, alright? It's boring without ya."],
            "hi": ["them: Want some? *crunch* No? More for me. Who're you?",
                   "them: Lookin' for a fight? I'm always up for one."],
            "hi2": "them: Oh. You. Here, have a pocky. Don't say I never gave you anything.",
            "hi4": "them (pleased): Hey, it's my favourite pushover! Kidding. Mostly. C'mere.",
            "again": "them: Back again? Bring snacks next time.",
            "loved": "them (pleased): Now we're talkin'! You're alright, you know that?",
            "disliked": "them (dismayed): What am I supposed to do with this? It's frilly and useless.",
            "before": "them: I fight for myself. Let's see what you fight for.",
            "won": "them (dismayed): Tch. Fine. You earned it. Want a snack?",
            "lost": "them (pleased): Ha! That's how it's done.",
            "r1": "them: You don't waste food, right? Good. Then we can be pals.",
            "r3": "them: My dad was a priest. Nobody listened to him, so I made 'em. With magic. It went real bad. Don't tell anyone.",
            "r4": "them (pleased): You know what? You're the only person I'd share my last snack with.",
        },
        friend=["background shrine", "me enters left with drop", "me: This used to be my dad's church. Kinda. Different town.",
                "me: I come to places like this when I don't wanna be around people.", "player: But I'm here.",
                "me (pleased): Yeah. Weird, right? I don't mind it.", "me: Here. Apple. Don't waste it.",
                "me: Eating together means something. My family used to. So... friends. Whatever."],
        best=["background rain", "me enters center with fade", "me: I used to say I only fight for myself. Selfish magic.",
              "me: 'Cause the one time I fought for someone else, I lost everything.",
              "player: Sayaka?", "me (dismayed): ...Yeah. Her too.",
              "me: But you showed up. And kept showing up. And I'd fight for you. Without thinking twice.",
              "choice", "- You don't have to be alone, Kyoko.", "- I'd fight for you too.",
              "me (pleased): Best friend, huh. Okay. Then you're stuck with me. Take an apple."]),

    cpu("Mami Tomoe", "friendly", quests=MAMI_TOMOE_QUESTS, extra_scenes=MAMI_TOMOE_SCENES,
        haunts=[("cafe", "wk", "12", 60), ("school", "we", "01", 40), ("rooftop", "024", "2", 30)],
        tastes=(["sweet"], ["drink", "fancy"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Next I'm going to bake a new cake. Strawberry, I think.", "them (pleased): Tomorrow I'll have tea ready. Please come, I've got too much.", "them (pleased): Tonight I'm going to the rooftop to watch the sunset. Join me."], "past": ["them: Earlier I set out a full tea service for nobody. Silly, I know.", "them (pleased): This morning I burnt a tart. Only a little bit burnt.", "them (pleased): Earlier I helped Kyoko find a good apple. She didn't say thanks."], "like": {"with": "Madoka", "lines": ["them: You're nothing like Madoka. She'd have smiled at me already.", "them: You're a bit like Madoka. Sweet, but a little shy.", "them (pleased): You're like Madoka, {player}. Sweet, kind, and very easy to be with."]}, "dislike": {"with": "Homura Akemi", "lines": ["them: You're so much like Homura. Cold and watchful.", "them: There's something of Homura in your silence. I don't like it.", "them (pleased): You're nothing like Homura, {player}. Thank goodness."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament, but I've baked for the crowd!"], ["them: I'm not entering, but I'll bring cakes for the whole arena."], ["them (pleased): I'm not in it, but I've saved the best cake for your victory."]], "entrant": [["them: I'm in the bracket! Please don't mind the crumbs.", "them: I'll do my best, but I'm going to be a little nervous."], ["them: We're both in the bracket. Oh, I'm so glad.", "them (pleased): Let's make it a fun match. Whatever happens."], ["them (pleased): You and me in the bracket, {player}. I'd like the final to be just us two."]], "out": [["them: Oh, you're out. Here, take a slice of cake. You deserve it."], ["them: You lost, but you were so brave out there."], ["them (pleased): You're out. Come sit, I saved you a cup of tea."]], "champion": [["them (pleased): You won! I baked a victory cake, just for you!"], ["them (pleased): Champion! You were brilliant. Here, have the biggest slice."], ["them (pleased): Champion, {player}! I'll bake one every week for you."]], "duel": [["them: It's our round. Please, let's both do our best.", "them: I'll be gentle, I promise."], ["them (pleased): Round time! Don't mind me, I'm just nervous.", "them: Let's give the crowd a good show."], ["them (pleased): Our round, {player}. Even if you win, I'll bring you cake."]]},
            "mid": {"1": ["them: Oh, you came back! Would you like another cup?", "them: I'm always baking. I hope you don't mind all the crumbs.", "them: Tell me about yourself. I'd like to know what you like.", "them: You're very polite. I appreciate that a great deal.", "them: Come sit by the window. It's a nice view from here."], "3": ["them (pleased): You always remember how I like my tea. Thank you.", "them: I've been thinking about my family. You make it easier to talk about.", "them (pleased): Let's bake something together. I'll let you help with the frosting.", "them: You're the one who keeps me company when the witches are quiet.", "them (pleased): I'd love to show you my favourite recipe. It's a secret."], "5": ["them (pleased): {player}, my partner and my friend. I can't imagine fighting without you.", "them: I don't feel alone with you. That means everything to me.", "them (pleased): Let's go to the rooftop and watch the sunset with cake.", "them: You're the one I'd save the last slice for, always.", "them (pleased): Best friend. Stay for dinner, please. The table's always set."]},
            "hello_steps": [["them: Oh, hello there. Can I help you?", "them: Hello! Would you like a little something?"], ["them: Hi, welcome. Please, have a seat.", "them: Oh, hello. Have you eaten yet?"], ["them (pleased): {player}! Perfect timing, the tea's just ready.", "them (pleased): Hello, {player}! I baked too much again."], ["them (pleased): {player}! Come in, come in. There's cake.", "them (pleased): {player}, welcome. You're just in time for the good part."], ["them (pleased): {player}, welcome. I set out a cup for you, just in case.", "them (pleased): Hi, {player}! You always make the house feel full."], ["them (pleased): {player}! My best friend and my favourite guest. Sit here.", "them (pleased): {player}! I saved the best slice for you, don't argue."]],
            "bye_steps": [["them: Take care, now.", "them: Goodbye. Mind the stairs."], ["them: Bye! Come back for tea sometime.", "them: Okay. Take care of yourself."], ["them (pleased): Do come by again, {player}. I'll have cake.", "them (pleased): Bye, {player}! Take a cake for the road."], ["them (pleased): Go on, {player}. Come back when you're hungry.", "them (pleased): Bye, {player}. Come back before the tea goes cold."], ["them (pleased): Come back soon. The house is too quiet without you.", "them (pleased): Take care, {player}. I'll set a place for you."], ["them (pleased): Bye, best friend. Come back soon, and bring an appetite.", "them (pleased): Bye, {player}. I'll keep a cup for you, always."]],
            "hello": ["them: Oh, hello there. Can I help you?", "them (pleased): {player}! Perfect timing, the tea's just ready.", "them (pleased): {player}, welcome. I set out a cup for you, just in case."],
            "bye": ["them: Take care, now.", "them (pleased): Do come by again. I'll have cake next time.", "them (pleased): Come back soon. The house is too quiet without you."],
            "hi": ["them (pleased): Oh, hello! I'm Mami Tomoe. Would you like some tea? I always make too much.",
                   "them: A duel? How lovely. Shall we begin? I'll show you how a senior fights."],
            "hi2": "them (pleased): {player}, I baked a cheesecake! You simply must try a slice.",
            "hi4": "them (pleased): Having you over for tea is the best part of my week. Truly.",
            "again": "them: You're back! Tea's still warm.",
            "loved": "them (pleased): Sweets! Oh, you've made my whole week. Let's share them.",
            "disliked": "them (dismayed): Spicy? Oh dear. Not with Earl Grey, I'm afraid.",
            "before": "them: Tiro... Finale! Ah, I'm sorry, I couldn't resist.",
            "won": "them (pleased): Splendid! You're becoming a fine duelist.",
            "lost": "them (pleased): A little more elegance, perhaps? You'll get there.",
            "r1": "them (pleased): It's so nice to have a guest. My apartment's too quiet, usually.",
            "r3": "them: I live alone. Since the accident. I made my wish to survive... but I didn't have time to wish for them.",
            "r4": "them (pleased): You've made me feel like I'm not alone anymore. That's the greatest magic I know.",
        },
        friend=["background cafe", "me enters left with fade", "me: Welcome to my little tea party. Just the two of us.",
                "me: I set out two cups. I always set two. Old habit.", "player: Who's the second cup for?",
                "me (dismayed): ...Someone I hope will come. Usually no one does.", "me (pleased): But today, you did.",
                "me: So, friend, how do you take your tea?", "choice", "- With milk.", "- With lots of sugar.",
                "me (pleased): Perfect. I'll remember that for next time."],
        best=["background night", "me enters center with fade", "me: Being a magical girl is lonely. You fight witches, smile, and go home to an empty room.",
              "me: I pretended I was fine. A good senior has to be strong.",
              "player: You don't have to be strong all the time.", "me (dismayed): ...I'm so tired, {player}.",
              "me: But when you're here, I don't have to pretend.",
              "choice", "- Lean on me.", "- You're never alone again.",
              "me (pleased): Then you're my dearest friend. My best friend. I'll set two cups for you, always."]),

    cpu("Sayaka Miki", "friendly", quests=SAYAKA_MIKI_QUESTS, extra_scenes=SAYAKA_MIKI_SCENES,
        haunts=[("school", "wk", "01", 55), ("beach", "we", "12", 45), ("plaza", "024", "2", 35)],
        tastes=(["music"], ["sweet", "sporty"], ["spicy"]),
        lines={
            "repeat": {"future": ["them: Next I'm practising the violin. Ugh, the high notes.", "them (pleased): Tomorrow I'm going to the hospital to see my friend. Come with me?", "them (pleased): Tonight I'll play at the beach. You can listen."], "past": ["them: Earlier I got into a fight with a witch. Okay, I won.", "them (pleased): This morning I made a new friend at school. It's a start.", "them (pleased): Earlier I finally talked to Kyosuke. It went badly, but I tried."], "like": {"with": "Madoka", "lines": ["them: You're nothing like Madoka. She's way braver than you.", "them: You're a bit like Madoka. Kind, but still finding your footing.", "them (pleased): You're like Madoka, {player}. Brave and kind, a real hero."]}, "dislike": {"with": "Homura Akemi", "lines": ["them: You're so much like Homura. Always so serious and cold.", "them: There's a bit of Homura in you. Lighten up, okay?", "them (pleased): You're nothing like Homura, {player}. Good, a hero should smile."]}},
            "tournament": {"spectator": [["them: I'm not in the tournament, but I'm cheering as loud as I can!"], ["them: Not in the bracket! But justice still needs cheering!"], ["them (pleased): I'm not in it! But you're my hero, so win it for justice!"]], "entrant": [["them: I'm in the bracket! Justice doesn't stop for brackets!", "them: Don't go easy on me! That's not heroic!"], ["them: We're both in it! This is the best day for heroes!", "them (pleased): Let's make the final an awesome fight!"], ["them (pleased): You and me in the bracket! My hero in the final, I can't wait!", "them (pleased): Win it, and then we'll stand at the top together!"]], "out": [["them: You're out? That's okay! Heroes get back up!"], ["them: You lost, but you were brave. That counts!"], ["them (pleased): You're out. Come on, let's go to the beach and clear our heads."]], "champion": [["them (pleased): CHAMPION! My hero! Justice has a new winner!"], ["them (pleased): You won! That's the most heroic thing I've seen all week!"], ["them (pleased): Champion, {player}! Stay heroic, partner. Always."]], "duel": [["them: It's our round! Justice is ready! Are you?", "them: No holding back, partner! That's the heroic way!"], ["them (pleased): Round time! My best move is ready!", "them: Let's show the crowd what heroes look like!"], ["them (pleased): Our round, {player}! I'd never want to beat my hero, but I'm going to try!"]]},
            "mid": {"1": ["them: Hey! You're cool. Do you play anything? I play violin.", "them: I'm practising my speech. Want to hear it?", "them: What's your favourite song? Mine's the one with the hero's theme.", "them: You look like someone who'd join the justice club. Want to?", "them: Don't laugh at my violin. Please."], "3": ["them (pleased): You're the best justice partner I could have asked for.", "them: I think about Kyosuke a lot. You make it less scary to say his name.", "them (pleased): Come to the beach. I'll play you the song I wrote.", "them: You helped me decide which wish I want. Thanks.", "them (pleased): You're the one I trust to tell me when I'm wrong."], "5": ["them (pleased): {player}, you're my best friend, and my hero too.", "them: I'd give up any wish for you. Actually, I already did, sort of.", "them (pleased): Let's go to the beach at sunset. I'll play just for you.", "them: You count as something back. I know that now.", "them (pleased): Best friend! Let's keep being heroes together, forever."]},
            "hello_steps": [["them: Yo! New face? Hi!", "them: Hey. You look like you could use a hero."], ["them: Hi! Are you here to help with something?", "them: Oh! Hello. Sorry, I'm practising."], ["them (pleased): {player}! Justice partner! What's the plan?", "them (pleased): {player}! Good to see you. Have you practised your lines?"], ["them (pleased): {player}! I've been waiting for you to ask me to play.", "them (pleased): {player}! Come on, let's do something good today."], ["them (pleased): THERE you are, {player}! I was about to send out a search party!", "them (pleased): {player}! Don't laugh, but I missed you."], ["them (pleased): {player}! My best friend. Justice is always better with you.", "them (pleased): Hi, {player}! Are you ready to be a hero with me?"]],
            "bye_steps": [["them: Okay, later!", "them: Bye! Stay out of trouble."], ["them: See you! Be careful!", "them: Okay, bye! Keep your head up."], ["them (pleased): See ya! Stay heroic, {player}!", "them (pleased): Bye, {player}! Don't forget your violin."], ["them (pleased): Go on, {player}! Justice doesn't wait.", "them (pleased): Bye, {player}! Keep a little light in the dark."], ["them (pleased): Come back soon, {player}! The town's quieter without you.", "them (pleased): Bye, {player}! Be safe, partner!"], ["them (pleased): Come back soon, partner! Justice waits for no one. Except you.", "them (pleased): Bye, best friend! Keep being a hero for me."]],
            "hello": ["them: Yo! New face? Hi!", "them (pleased): {player}! Justice partner! What's the plan?", "them (pleased): THERE you are! I was about to send out a search party!"],
            "bye": ["them: Okay, later!", "them (pleased): See ya! Stay heroic!", "them (pleased): Come back soon, partner! Justice waits for no one. Except you."],
            "hi": ["them: Yo! Sayaka Miki, magical girl of justice! Well, aspiring. Whatever!",
                   "them: Need someone to cheer you up? I'm great at that. Better at duels, though!"],
            "hi2": "them (pleased): {player}! I'm going to the hospital later to see Kyosuke. Wanna come?",
            "hi4": "them (pleased): You're my partner in justice. Don't argue, it's decided!",
            "again": "them: Hey again! Bored? I'm never bored.",
            "loved": "them (pleased): Classical music! Kyosuke would love this. ...I mean, I love it!",
            "disliked": "them (dismayed): Bleh, spicy. My justice can't handle that.",
            "before": "them: For justice! Let's do this!",
            "won": "them (dismayed): Argh! Okay, okay. You're good. I'll train harder!",
            "lost": "them (pleased): Justice prevails!",
            "r1": "them (pleased): You're fun! Way more fun than homework.",
            "r3": "them: I wished for someone else to be happy. Not me. Sometimes I wonder if that was dumb.",
            "r4": "them (pleased): I'd make a wish for you, you know. Any time. That's how much you matter.",
        },
        friend=["background ocean", "me enters left with slide", "me: I come here when I'm thinking about stuff. Big stuff.",
                "me: Like whether doing the right thing is worth it if nobody notices.", "player: I'd notice.",
                "me (pleased): Ha. Yeah, you would.", "me: That's the thing, isn't it? You don't need everyone. Just someone.",
                "me bounces", "me: Okay! Friendship justice alliance! You're in!"],
        best=["background rain", "me enters center with fade", "me: I made my wish for Kyosuke. And then he fell for someone else.",
              "me (dismayed): I felt so stupid. Like I threw everything away.",
              "player: You didn't. You were kind.", "me: Kind and alone.",
              "player: Not alone.", "me (dismayed): ...No. You're right.",
              "choice", "- I see you, Sayaka.", "- Your wish wasn't a waste.",
              "me (pleased): Best friend. That's my new wish. Except it already came true. Ha!"]),
]

ARRIVALS = [
  {
    "newcomer": "Akane Kurokawa",
    "name": "World: Arrival, Akane Kurokawa",
    "lines": [
      "background library",
      "me enters center with fade",
      "me: Hold still. Your posture is so interesting. I'm copying it for a role.",
      "me (pleased): Don't look so offended. Actors learn from everyone, even the rude ones.",
      "me: I'll need your name, your habits, and what makes you cry. Start with the name.",
      "player: Are you really studying me for a part?",
      "choice What's your reaction?",
      "- Tell her she can study you, but she'll have to pay for coffee. (set side_me)",
      "- Tell her you'll give her the honest answer, and she should keep the notes. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Aqua Hoshino",
    "name": "World: Arrival, Aqua Hoshino",
    "lines": [
      "background classroom",
      "me enters left with slide",
      "me: Hold the camera steady. No, not you, the town. I'm making a project.",
      "me (dismayed): Okay, you're in the frame now. Don't look at the lens too long.",
      "me: Be sincere. The camera picks up everything. Even your lies.",
      "player: Why are you filming the whole town?",
      "choice How do you respond?",
      "- Tell him the town doesn't want to be filmed, and he should stop. (set side_me)",
      "- Tell him you'll be sincere, and he should keep rolling. (set side_me, give climax_pack)"
    ]
  },
  {
    "newcomer": "Kana Arima",
    "name": "World: Arrival, Kana Arima",
    "lines": [
      "background classroom",
      "me enters right with pop",
      "me: I used to be a child star. Don't ask which show. Don't. I mean it.",
      "me (dismayed): ...I shouldn't have said that. Forget I said anything.",
      "me: Now I'm a regular person. Mostly. Hi.",
      "player: A former child star. Do you want to hear more?",
      "choice What do you say?",
      "- Tell her the past doesn't matter, and she should stop worrying. (set side_me)",
      "- Tell her you'll keep the secret, and she can talk when she's ready. (set side_me, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Ruby Hoshino",
    "name": "World: Arrival, Ruby Hoshino",
    "lines": [
      "background classroom",
      "me enters center with rise",
      "me: Want a B-Komachi flyer? It's our new show! Take two, one for a friend.",
      "me (pleased): Ha! You took two! That's my first fan of the day. Hi!",
      "me: We're the best group in town. Okay, the only group. But still the best.",
      "player: Did you really come to the school just to hand out flyers?",
      "choice What's your response?",
      "- Tell Ruby the flyers are tacky, and she should try a poster. (set side_me)",
      "- Tell Ruby you'll come to the show, and she should bring the second flyer. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Legendary Idol Ai",
    "name": "World: Arrival, Legendary Idol Ai",
    "lines": [
      "background sakura",
      "me enters center with zoom",
      "me: Oh, the crowd's gathering. Don't worry, I'll smile for everyone.",
      "me (pleased): You're not screaming. That's refreshing. Hi, I'm Ai.",
      "me: Be honest, are you here for me, or for the idol?",
      "player: The whole plaza is watching you. Is it too much?",
      "choice Which side do you take?",
      "- Tell Ai the crowd is a bit much, and she should go somewhere quiet. (set side_me)",
      "- Tell Ai the plaza loves her, and she should stay and smile. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Madoka",
    "name": "World: Arrival, Madoka",
    "lines": [
      "background classroom",
      "me enters left with fade",
      "me: Hi! I'm new here, and I don't know anyone. Is this seat taken?",
      "me (dismayed): Sorry, I'm really nervous. I hope I didn't startle you.",
      "me: You look like someone who's been here a while. Could you show me around?",
      "player: She's latched onto you already. Do you help her find her way?",
      "choice What do you say?",
      "- Tell her the school is huge, and she should find a friend in her own class. (set side_me)",
      "- Tell her you'll show her around, and she can sit with you. (set side_me, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Homura Akemi",
    "name": "World: Arrival, Homura Akemi",
    "lines": [
      "background classroom",
      "me enters right with drop",
      "me: That white creature at the window. Don't go near it, not for a wish.",
      "me (dismayed): You don't believe me. That's fine. You will. You always do.",
      "me: Let's keep this short. I'd like to leave before the bell.",
      "player: You warned me about a white creature, and you're leaving? What's going on?",
      "choice Who do you trust?",
      "- Tell Homura the warning is strange, and she should explain it. (set side_me)",
      "- Tell Homura you'll be careful, and she can rest for a minute. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Kyoko Sakura",
    "name": "World: Arrival, Kyoko Sakura",
    "lines": [
      "background city",
      "me enters center with pop",
      "me: *munch* This apple's good. Want half? I'm not going to ask twice.",
      "me (pleased): You took it. Good. Nobody wastes food around me.",
      "me: Don't look at my clothes. I have bigger problems than a hole in my jacket.",
      "player: You're giving away food, but you're not sharing it. Do you want the rest of the apple?",
      "choice What's your reaction?",
      "- Tell Kyoko she should share the whole apple, and not just the half. (set side_me)",
      "- Tell Kyoko you'll take the apple, and she can keep the rest. (set side_me, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Mami Tomoe",
    "name": "World: Arrival, Mami Tomoe",
    "lines": [
      "background cafe",
      "me enters right with slide",
      "me: Oh, you're here! Please sit down. I've made far too much tea, and far too much cake.",
      "me (pleased): Ahh, you're not shy. Wonderful. Here, try the strawberry one.",
      "me: Will you come back tomorrow? Please say yes.",
      "player: A tea party, without an invitation. Do you stay?",
      "choice What's your response?",
      "- Tell Mami the cake is too much, and she should save some for later. (set side_me)",
      "- Tell Mami you'll stay for the whole tea, and she should have the last slice. (set side_me, give color_pack)"
    ]
  },
  {
    "newcomer": "Sayaka Miki",
    "name": "World: Arrival, Sayaka Miki",
    "lines": [
      "background classroom",
      "me enters left with rise",
      "me: Excuse me! Do you know the way to the hospital? I'm going to visit a friend.",
      "me (dismayed): Oops, I'm rambling. Sorry. I'm nervous about the visit.",
      "me: You look like you'd be a good hero. Would you help me?",
      "player: Someone needs help getting to the hospital. Do you go with her?",
      "choice What's your reaction?",
      "- Tell Sayaka the hospital's down the road, and she can walk there herself. (set side_me)",
      "- Tell Sayaka you'll go with her, and she should lead the way. (set side_me, give climax_pack)"
    ]
  },
  {
    "newcomer": "Akane Kurokawa",
    "name": "World: Arrival, Akane Kurokawa & Aqua Hoshino",
    "lines": [
      "cast aqua as Aqua Hoshino",
      "background library",
      "me enters left with slide",
      "aqua enters right with fade",
      "aqua: Akane. I know you've been following me. Stop writing my name in your notebook.",
      "me (pleased): I'm not following you. I'm studying you. There's a difference.",
      "aqua (dismayed): Fine. But my lead is real. I'm not going to play your role.",
      "player: She's worried about him, and he's shutting her out. Do you back her, or him?",
      "choice Who do you side with?",
      "- Tell Aqua she should let Akane help him, even if it's a role. (set side_me)",
      "- Tell Akane she should give Aqua some room, and stop studying him. (set side_aqua, give color_pack)"
    ]
  },
  {
    "newcomer": "Akane Kurokawa",
    "name": "World: Arrival, Akane Kurokawa & Kana Arima",
    "lines": [
      "cast kana as Kana Arima",
      "background cafe",
      "me enters left with slide",
      "kana enters right with fade",
      "kana: Akane Kurokawa. You're the one who copies everyone's walk. It's creepy.",
      "me (pleased): Kana Arima. You're the one who cries on cue. Let's compare notes.",
      "kana (dismayed): I don't cry on cue! That was one time. It was real.",
      "player: Actors' rivalry, right away. Who do you support?",
      "choice Whose side do you take?",
      "- Tell Akane she's copying Kana, and she should stop. (set side_me)",
      "- Tell Kana she can cry on cue if she wants, and Akane should copy that. (set side_kana, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Aqua Hoshino",
    "name": "World: Arrival, Aqua Hoshino & Ruby Hoshino",
    "lines": [
      "cast ruby as Ruby Hoshino",
      "background classroom",
      "me enters left with slide",
      "ruby enters right with fade",
      "ruby: Aqua! You're filming my rehearsal again. You can't put me in your project!",
      "me (dismayed): It's a documentary, Ruby. The whole town should see your moves.",
      "ruby (pleased): Ha! Okay, but only if you give me the good angle. The good one.",
      "player: Twin bickering. Do you help Aqua keep filming, or Ruby keep her privacy?",
      "choice Who do you side with?",
      "- Tell Ruby the documentary is worth it, and she should give Aqua a chance. (set side_me)",
      "- Tell Aqua the rehearsal is private, and he should stop filming. (set side_ruby, give color_pack)"
    ]
  },
  {
    "newcomer": "Aqua Hoshino",
    "name": "World: Arrival, Aqua Hoshino & Twilight",
    "lines": [
      "cast twilight as Twilight",
      "background cafe",
      "me enters left with slide",
      "twilight enters right with fade",
      "twilight: I saw your camera from across the street. Are you making a documentary?",
      "me (dismayed): I'm not telling you anything. Who are you, really?",
      "twilight (pleased): Just a psychiatrist. Your secret's safe with me, I think.",
      "player: Two people with secrets recognise each other. Do you trust Twilight, or Aqua?",
      "choice Who do you back?",
      "- Tell Twilight he's clearly lying, and Aqua should be careful. (set side_me)",
      "- Tell Aqua the psychiatrist seems honest, and he should share. (set side_twilight, give color_pack)"
    ]
  },
  {
    "newcomer": "Kana Arima",
    "name": "World: Arrival, Kana Arima & Ruby Hoshino",
    "lines": [
      "cast ruby as Ruby Hoshino",
      "background classroom",
      "me enters left with slide",
      "ruby enters right with fade",
      "ruby: Kana! We're doing the group dance today, and you're late!",
      "me (dismayed): I'm not late, I'm practising my crying. It's hard.",
      "ruby (pleased): You're not practising crying! You're practising my dance, which is worse.",
      "player: Idol practice gone wrong. Do you pick a side?",
      "choice Who do you side with?",
      "- Tell Ruby the crying can wait, and the dance has to be perfect. (set side_me)",
      "- Tell Kana the dance can wait, and the crying is more important. (set side_ruby, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Kana Arima",
    "name": "World: Arrival, Kana Arima & Mai Sakurajima",
    "lines": [
      "cast mai as Mai Sakurajima",
      "background library",
      "me enters left with slide",
      "mai enters right with fade",
      "mai: Kana Arima. You're famous, and you look miserable. Same as me.",
      "me (dismayed): Mai Sakurajima. Please don't tell anyone I was here. I need quiet.",
      "mai (pleased): I'd never. I'm barely here myself. Let's just sit in silence.",
      "player: Two famous faces who want to be left alone. Do you give them the quiet?",
      "choice Who gets your support?",
      "- Tell Mai she should stop vanishing, and let Kana have some attention. (set side_me)",
      "- Tell Kana she should share the quiet, and not perform for everyone. (set side_mai, give color_pack)"
    ]
  },
  {
    "newcomer": "Ruby Hoshino",
    "name": "World: Arrival, Ruby Hoshino & Kana Arima",
    "lines": [
      "cast kana as Kana Arima",
      "background classroom",
      "me enters left with slide",
      "kana enters right with fade",
      "kana: Ruby. Stop waving your flyer in my face. I'm trying to study.",
      "me (pleased): Kana! You're the best idol in the group! Come be my partner!",
      "kana (dismayed): I'm not an idol. I'm a sad former child star. Stop it.",
      "player: Idol group drama, at lunch. Whose side are you on?",
      "choice Who do you back?",
      "- Tell Kana she should join Ruby's group, for the team. (set side_me)",
      "- Tell Ruby the group can wait, and Kana needs some time. (set side_kana, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Ruby Hoshino",
    "name": "World: Arrival, Ruby Hoshino & Kureiji Ollie",
    "lines": [
      "cast kureiji as Kureiji Ollie",
      "background sakura",
      "me enters left with slide",
      "kureiji enters right with fade",
      "kureiji: Hiii! Ruby! Are you the idol? Can I touch your flyer? It's warm.",
      "me (dismayed): Ollie! Don't touch it, it's not warm, it's just sweaty from my hand!",
      "kureiji (pleased): Ha! Ollie likes sweaty flyers. Ollie's a zombie, you know.",
      "player: Two idols, one of them a zombie. Do you help Ruby, or let Ollie have the flyer?",
      "choice Who do you side with?",
      "- Tell Ollie the flyer is Ruby's, and she should keep it. (set side_me)",
      "- Tell Ruby the flyer's fine, and Ollie can have it. (set side_kureiji, give color_pack)"
    ]
  },
  {
    "newcomer": "Legendary Idol Ai",
    "name": "World: Arrival, Legendary Idol Ai & Ruby Hoshino",
    "lines": [
      "cast ruby as Ruby Hoshino",
      "background sakura",
      "me enters left with slide",
      "ruby enters right with fade",
      "ruby: Mum? Wait. Is that you? Oh no, I'm so embarrassed!",
      "me (pleased): Ruby. My daughter. I thought you'd be taller. Hi, sweetheart.",
      "ruby (dismayed): Don't call me sweetheart in front of everyone! Mum!",
      "player: Mother and daughter, in the middle of the plaza. Do you stay out of it?",
      "choice Who do you support?",
      "- Tell Ai she should give Ruby some space, in front of the fans. (set side_me)",
      "- Tell Ruby she should listen to her mum, just this once. (set side_ruby, give color_pack)"
    ]
  },
  {
    "newcomer": "Legendary Idol Ai",
    "name": "World: Arrival, Legendary Idol Ai & Ruby Rose",
    "lines": [
      "cast ruby as Ruby Rose",
      "background sakura",
      "me enters left with slide",
      "ruby enters right with fade",
      "ruby: Hi! Are you the idol? Someone told me you were Ruby. I'm Ruby Rose!",
      "me (pleased): Oh! You're the other Ruby! Nice to meet you. Let's get cookies.",
      "ruby (pleased): Yes! Cookies! Okay, wait, that's not for you. It's mine.",
      "player: The wrong Ruby, a mix-up. Do you help Ai, or Ruby Rose?",
      "choice Who gets your help?",
      "- Tell Ai the cookies are hers, and she should share with Ruby Rose. (set side_me)",
      "- Tell Ruby Rose the cookies are hers, and she should keep them. (set side_ruby, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Madoka",
    "name": "World: Arrival, Madoka & Homura Akemi",
    "lines": [
      "cast homura as Homura Akemi",
      "background classroom",
      "me enters left with slide",
      "homura enters right with fade",
      "homura: Madoka. You're new here, and you're nervous. Don't worry about the wish.",
      "me (dismayed): Homura? How do you know my name? I don't even know yours.",
      "homura: I know many things I shouldn't. Stay close to me, and keep your distance from Kyubey.",
      "player: The transfer student who knows her name. Do you trust Homura?",
      "choice Who do you back?",
      "- Tell Madoka that Homura's a stranger, and she should walk away. (set side_me)",
      "- Tell Homura that Madoka needs a friend, and she should stay close. (set side_homura, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Madoka",
    "name": "World: Arrival, Madoka & Kanna",
    "lines": [
      "cast kanna as Kanna",
      "background beach",
      "me enters left with slide",
      "kanna enters right with fade",
      "kanna: You're new. Kanna likes new people. Want to share my lunch?",
      "me (pleased): Oh, Kanna! Thank you! Your lunch is so pretty, with the dragon on it.",
      "kanna: Kanna's dragon is shy. Don't tell him you noticed.",
      "player: Two gentle souls. Do you let them share lunch, or hurry Madoka along?",
      "choice Whose side do you take?",
      "- Tell Madoka the lunch can wait, and she should hurry to class. (set side_me)",
      "- Tell Kanna the lunch is a good idea, and Madoka should share. (set side_kanna, give color_pack)"
    ]
  },
  {
    "newcomer": "Homura Akemi",
    "name": "World: Arrival, Homura Akemi & Madoka",
    "lines": [
      "cast madoka as Madoka",
      "background classroom",
      "me enters left with slide",
      "madoka enters right with fade",
      "madoka: Homura, why do you keep watching me? You're like a guard.",
      "me (dismayed): Because I'm trying to keep you from a bad wish. It's not your fault.",
      "madoka (pleased): A wish? You know about that too? Okay, let's talk after school.",
      "player: Watching over her, from the other side of the room. Do you help Homura, or Madoka?",
      "choice Who do you side with?",
      "- Tell Madoka she should stop being watched, and make her own choices. (set side_me)",
      "- Tell Homura she should trust Madoka, and talk to her properly. (set side_madoka, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Homura Akemi",
    "name": "World: Arrival, Homura Akemi & Shadow",
    "lines": [
      "cast shadow as Shadow",
      "background rooftop",
      "me enters left with slide",
      "shadow enters right with fade",
      "shadow: You know her, the girl with the pink hair. She's the one you'd die for?",
      "me (dismayed): I don't know what you mean. Stay out of this, please.",
      "shadow (pleased): Then I'll stay quiet. But I know that look. I wear it too.",
      "player: Two loners with one person they'd die for. Do you side with Homura, or Shadow?",
      "choice Who do you back?",
      "- Tell Shadow he shouldn't be watching Homura, and he should leave. (set side_me)",
      "- Tell Homura that Shadow understands, and she can trust him. (set side_shadow, give color_pack)"
    ]
  },
  {
    "newcomer": "Kyoko Sakura",
    "name": "World: Arrival, Kyoko Sakura & Sayaka Miki",
    "lines": [
      "cast sayaka as Sayaka Miki",
      "background city",
      "me enters left with slide",
      "sayaka enters right with fade",
      "sayaka: Kyoko! You stole that apple from the stall, didn't you? Give it back!",
      "me (pleased): Stole? I'm sharing it. There's a difference, hero girl.",
      "sayaka (dismayed): That's not sharing, it's stealing with a smile! Justice demands it back!",
      "player: Instant argument, from the first word. Whose side are you on?",
      "choice Who do you back?",
      "- Tell Sayaka the apple's already gone, and she should let it go. (set side_me)",
      "- Tell Kyoko the apple's hers to share, and she should stop running. (set side_sayaka, give climax_pack)"
    ]
  },
  {
    "newcomer": "Kyoko Sakura",
    "name": "World: Arrival, Kyoko Sakura & Megumin",
    "lines": [
      "cast megumin as Megumin",
      "background city",
      "me enters left with slide",
      "megumin enters right with fade",
      "megumin: Kyoko! Do you have any food? I'm starving after my explosion!",
      "me (pleased): Food? Sure. Eat it, all of it. Nobody wastes food around me.",
      "megumin (pleased): Thank you! I'll explode something for you, as a gift!",
      "player: Two who only care about one thing. Do you help Kyoko feed Megumin, or stop her?",
      "choice Who do you side with?",
      "- Tell Megumin the food is Kyoko's, and she shouldn't take it all. (set side_me)",
      "- Tell Kyoko Megumin deserves a meal, and she should share. (set side_megumin, give color_pack)"
    ]
  },
  {
    "newcomer": "Mami Tomoe",
    "name": "World: Arrival, Mami Tomoe & Madoka",
    "lines": [
      "cast madoka as Madoka",
      "background cafe",
      "me enters left with slide",
      "madoka enters right with fade",
      "madoka: Mami! You invited me to tea, but there's no cake for me.",
      "me (pleased): Madoka, dear! Of course there's cake. I baked it just for you.",
      "madoka (pleased): You're so kind. I'll remember this, and I'll remember you.",
      "player: A mentor and a student at the tea table. Do you take Mami's side, or Madoka's?",
      "choice Who gets your support?",
      "- Tell Madoka that Mami's cake is hers, and she should have a second slice. (set side_me)",
      "- Tell Mami that Madoka needs a mentor, and she should stay close. (set side_madoka, give lucky_pack)"
    ]
  },
  {
    "newcomer": "Mami Tomoe",
    "name": "World: Arrival, Mami Tomoe & Tohru",
    "lines": [
      "cast tohru as Tohru",
      "background cafe",
      "me enters left with slide",
      "tohru enters right with fade",
      "tohru: Oh! Are you the host? I brought a dish. It's a bit suspicious, but it's good.",
      "me (pleased): A dish? Let's have a taste. I baked a cake, so we'll see who wins.",
      "tohru (pleased): Ooh, a contest! I'll make you my special stew. It's very good.",
      "player: Two hosts, one cake contest. Who gets your vote?",
      "choice Who do you vote for?",
      "- Tell Tohru her stew looks suspicious, and Mami should win. (set side_me)",
      "- Tell Mami her cake is great, and Tohru should show off her stew. (set side_tohru, give color_pack)"
    ]
  },
  {
    "newcomer": "Sayaka Miki",
    "name": "World: Arrival, Sayaka Miki & Kyoko Sakura",
    "lines": [
      "cast kyoko as Kyoko Sakura",
      "background classroom",
      "me enters left with slide",
      "kyoko enters right with fade",
      "kyoko: Hey, Sayaka. You're the hero girl with the violin, right? Want an apple?",
      "me (dismayed): No! I don't take food from strangers. Kyoko, you're a bad influence.",
      "kyoko (pleased): Bad influence, huh? I'll take that as a compliment. Eat the apple.",
      "player: Rivalry from the first word. Who do you support?",
      "choice Whose side do you take?",
      "- Tell Kyoko she's a bad influence, and Sayaka should be careful. (set side_me)",
      "- Tell Sayaka she's a hero, and Kyoko should stop tempting her. (set side_kyoko, give color_pack)"
    ]
  },
  {
    "newcomer": "Sayaka Miki",
    "name": "World: Arrival, Sayaka Miki & Emilia",
    "lines": [
      "cast emilia as Emilia",
      "background forest",
      "me enters left with slide",
      "emilia enters right with fade",
      "emilia: Hello! Are you looking for someone? I'm lost in the forest, and so is Puck.",
      "me (pleased): Oh, Emilia! A knight is always ready to help. Which way?",
      "emilia (pleased): Thank you! Puck says you're a hero too. How nice.",
      "player: Two knights, both looking for someone else. Who do you help?",
      "choice Who gets your help?",
      "- Tell Emilia the forest is her problem, and Sayaka should keep looking for her friend. (set side_me)",
      "- Tell Sayaka the forest is dangerous, and Emilia should follow her. (set side_emilia, give lucky_pack)"
    ]
  }
]
