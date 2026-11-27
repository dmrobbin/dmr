# World mode: arrival scenes (plan)

A save now starts with a small cast and gets a few more CPUs each week (`weiss/world_roster.py`). When a newcomer
arrives, a scene plays: the newcomer meets someone already in town, with the player there, and the player's choice
gives a reward and friendship points. None of the scenes are written yet. This is the list of every one that's needed,
with a premise for each.

## How arrivals work (what the writing has to fit)

- **When:** at the start of each week (Monday morning). The town says who's new ("New in town this week: …") and
  plays each newcomer's scene in turn, straight away, as a quest's visit scene does.
- **Who's new is random per save.** The starting cast is 12 random CPUs (at least 2 villains), then about 4 more each
  week. Characters whose quests name each other always arrive in the same week. So **any of the 75 can be a
  newcomer**, and who they meet depends on who's already in town.
- **Which scene plays:** the town looks, in order, for:
  1. **"World: Arrival, <Newcomer> & <Other>"**, where Other is in town: someone already here, or a fellow newcomer
     that week. If several are written and fit, one's drawn for the save.
  2. **"World: Arrival, <Newcomer>"**, the solo fallback: the newcomer meets the player alone.
  3. If neither is written, the newcomer just arrives (the news line only).
- **The choice is the payoff.** Every arrival scene ends with a `choice` whose options each say whose side the player
  takes:
  - `(set side_<cast id>)`: that character gets friendship points (WorldSettings.arrival_points, 8 by default, scaled
    by temperament).
  - `(set side_x, give climax_pack)`: also gives that pack (`climax_pack`, `color_pack` or `lucky_pack`, from the
    newcomer's set) instead of the coins.
  - An option with no `give` gives the arrival coins (WorldSettings.arrival_coins, 200 by default).
  - An option with no `side_…` gives the points to the newcomer.
  - The scene ends on a "You got" panel with the points and the reward.
- **Example**, the shape every arrival scene follows (8–12 lines, the newcomer's first impression in their own voice):

  ```
  cast new as Toph
  cast old as Sokka
  background sakura
  new enters right with slide
  old enters left with fade
  new: So this is the big town. Smells like sweat and bad decisions.
  old: Hey! I'll have you know I bathed this week.
  player: Be nice, you two.
  new: Who's this one, Snoozles? They walk like they've got somewhere to be.
  choice Who do you back up?
  - The newcomer: "She's not wrong about the smell." (set side_new)
  - Sokka: "Give him a break, he's harmless." (set side_old, give climax_pack)
  ```

- **Names:** the scene's name has to match the CPU names exactly ("World: Arrival, Chisato Nishikigi & Takina Inoue").
- **In the pack files**, the newcomer is cast as `me` automatically (`build.py`), so the example's `new` would be `me`
  and its flag `side_me`.
- **Backgrounds:** use the newcomer's first haunt's place (see the outlines' "Where").

## What to write, and in what order

1. **A solo scene for every CPU: 75.** These guarantee every arrival plays something. Each is the newcomer meeting the
   player alone; the choice is between two attitudes to them, both siding with the newcomer, one giving coins and one
   a pack.
2. **The quest groups' joint scenes: 3** (those who always arrive together; more as quests are written):
   - **Aang & Azula** (their Best friend quests lock each other)
   - **Denji & Power** (their quests name each other)
   - **Chisato Nishikigi & Takina Inoue** (their quests lock each other)
3. **Two partner scenes for every CPU: 150.** The newcomer with a likely resident, usually one from their own series
   and one from another (cross-series meetings are half the fun of the town). As more are written, more arrivals play a
   real meeting rather than the solo fallback.

**Total: about 228 scenes.** The solo 75 come first: until they're written, most arrivals are only a news line.

As more quests are written, re-check the groups: any CPUs whose quests name each other become a group that arrives
together, and want a joint scene.

## The outlines

Each CPU: **where** its solo scene happens (its first haunt), a **solo** premise, and its two **partner** scenes. For
each partner scene, the choice is between siding with the newcomer and siding with the partner.

### Pack 01: Avatar and Gurren Lagann

| Newcomer | Where | Solo premise | Partner scenes |
|---|---|---|---|
| Aang | plaza | Lands from the sky on a glider, asks where the nearest air temple is | **Katara**: a reunion, she scolds him for flying off · **Toph**: she senses him coming and pranks him |
| Katara | beach | Bends water out of the fountain to cool off, startles you | **Sokka**: she drags him out of the food stalls · **Mami Tomoe**: tea, and two motherly types sizing each other up |
| Sokka | cafe | Tries to pay for food with a boomerang | **Toph**: "Snoozles" (the example above) · **Simon the digger**: two inventors compare gadgets |
| Toph | arena | Walks in blind and wins an arm-wrestle | **Aang**: her student, late again · **Ryuko Matoi**: two brawlers who want a rematch |
| Azula | plaza | Arrives as if she owns the town and asks who's in charge | **Aang**: the Avatar, again · **Satsuki Kiryuin**: two heirs, each certain she outranks the other |
| Simon the digger | plaza | Digs up through the plaza paving | **Yoko**: she pulls him out by the collar · **Okarun**: two shy boys who find each other |
| Simon | arena | Pierces the arena ceiling, then apologises | **Kittan**: old comrades · **Kirito**: two heroes who never asked to be |
| Kittan | arena | Challenges whoever looks strongest | **Yoko**: he's showing off for her, badly · **Gray Fullbuster**: someone else who loses his shirt |
| Yoko | beach | Snipes a falling coconut before it hits you | **Simon the digger**: she checks he's eating · **Rapi**: two sharpshooters compare scopes |
| Lord Genome | warehouse | Takes the warehouse as a throne room | **Simon**: the man who beat him · **Ainz Ooal Gown**: two kings at a cold summit |
| Anti Spiral | rooftop | The stars flicker; it's watching the town | **Simon**: the old enemy · **Frieren**: a being who has seen ages, and an elf who has too |

### Pack 02: Oshi no Ko and Madoka Magica

| Newcomer | Where | Solo premise | Partner scenes |
|---|---|---|---|
| Akane Kurokawa | library | Studies the town's people for a role, starting with you | **Aqua Hoshino**: she's worried about him · **Kana Arima**: actors' rivalry, at once |
| Aqua Hoshino | school | Films the town for "a project", too intently | **Ruby Hoshino**: twin bickering · **Twilight**: two people with secrets recognise each other |
| Kana Arima | school | Introduces herself as a former child star, then regrets it | **Ruby Hoshino**: idol practice gone wrong · **Mai Sakurajima**: two famous faces who want to be left alone |
| Ruby Hoshino | school | Hands out B-Komachi flyers to everyone, you twice | **Kana Arima**: idol group drama · **Kureiji Ollie**: two idols, one a zombie |
| Legendary Idol Ai | plaza | Draws a crowd just by walking past | **Ruby Hoshino**: mother and daughter (a heavy one) · **Ruby Rose**: the wrong Ruby, a mix-up |
| Madoka | school | New in class and nervous, latches onto you | **Homura Akemi**: the transfer student who knows her name · **Kanna**: two gentle souls |
| Homura Akemi | school | Warns you about a white creature, and leaves | **Madoka**: watching over her · **Shadow**: two loners with one person they'd die for |
| Kyoko Sakura | alley | Steals an apple and offers you half | **Sayaka Miki**: instant argument · **Megumin**: two who only care about one thing |
| Mami Tomoe | cafe | Hosts a tea party in the cafe uninvited | **Madoka**: a mentor and a student · **Tohru**: two hosts, one cake contest |
| Sayaka Miki | school | Asks the way to the hospital | **Kyoko Sakura**: rivalry from the first word · **Emilia**: two knights for someone else |

### Pack 03: Chainsaw Man, Attack on Titan and Kill la Kill

| Newcomer | Where | Solo premise | Partner scenes |
|---|---|---|---|
| Denji | plaza | Asks if anyone's giving away free food | **Power**: arrive together, arguing (joint scene) · **Megumin**: two very simple dreams |
| Power | plaza | Declares the town hers | **Denji**: (the joint scene) · **Kyoko Sakura**: a food fight |
| Aki Hayakawa | rooftop | Smoking on the roof, says nothing for a while | **Denji**: babysitting · **Levi**: two tired soldiers |
| Makima | rooftop | Already knows your name, kindly | **Aki Hayakawa**: an order to her subordinate · **Albedo**: two who want control, each politely |
| Beast Titan | forest | Throws a ball over the treetops and asks you to fetch | **Levi**: bad blood · **Lord Genome**: two who think the world needs ending |
| Eren | arena | Trains alone until his hands bleed | **Mikasa**: she wraps them · **Giorno Giovanna**: two who chose the hard path |
| Levi | cafe | Inspects the cafe for dust before sitting | **Eren**: tough love · **Erza Scarlet**: two commanders, one tea |
| Mikasa | arena | Asks if you've seen a boy with green eyes | **Eren**: found him · **Yor Forger**: two quiet killers, both blushing |
| Nui Harime | warehouse | Skips in sewing a doll of nobody you know | **Ryuko Matoi**: hatred at first sight · **Joker**: two terrifying smiles |
| Ragyo Kiryuin | warehouse | Arrives glowing, and the lights dim | **Satsuki Kiryuin**: mother and daughter · **DIO**: two who consider themselves gods |
| Ryuko Matoi | arena | Talks to her own uniform | **Satsuki Kiryuin**: sisters who don't know it yet · **Toph**: rematch |
| Satsuki Kiryuin | school | Takes over the school's student council by noon | **Ryuko Matoi**: rival · **Weiss Schnee**: two heiresses |

### Pack 04: Dandadan, RWBY, JoJo and Re:Zero

| Newcomer | Where | Solo premise | Partner scenes |
|---|---|---|---|
| Aira | school | Announces she's a chosen hero | **Okarun**: she's sure he needs saving · **Momo Ayase**: rivals who'd never admit they're friends |
| Momo Ayase | school | Asks if you believe in ghosts, or aliens | **Okarun**: their arguing is flirting · **Akane Kurokawa**: girls' cafe chat |
| Okarun | library | Reads about yokai and jumps when you speak | **Momo Ayase**: (as above, his side) · **Simon the digger**: two shy ones |
| Cinder Fall | alley | A fire starts and she smiles at it | **Ruby Rose**: the silver-eyed girl · **Azula**: two fire-wielders, one dangerous friendship |
| Ruby Rose | cafe | Eats every cookie at the counter | **Weiss Schnee**: team RWBY's oldest argument · **Chisato Nishikigi**: two cheerful fighters |
| Weiss Schnee | library | Corrects the library's filing | **Ruby Rose**: as above, her side · **Satsuki Kiryuin**: two heiresses |
| DIO | warehouse | Time stops; when it starts, he's behind you | **Giorno Giovanna**: father and son · **Ragyo Kiryuin**: two gods |
| Giorno Giovanna | cafe | Grows a flower from your coffee cup | **Jolyne Cujoh**: family, sort of · **Eren**: two with dreams |
| Jolyne Cujoh | beach | Escaped from somewhere, won't say | **Giorno Giovanna**: as above · **Ryuko Matoi**: two punks |
| Echidna | library | Invites you to tea in a place that isn't the library | **Emilia**: the witch's offer · **Frieren**: two centuries-old scholars |
| Emilia | forest | Lost in the forest, and very polite about it | **Ram/Rem**: her household · **Madoka**: two kind hearts |
| Ram/Rem | cafe | Arrive to clean a mansion that isn't here | **Emilia**: their lady · **Kanna**: two who serve someone they love |

### Pack 05: Overlord, SAO, Batman Ninja, Lycoris Recoil, NIKKE, KonoSuba and Fairy Tail

| Newcomer | Where | Solo premise | Partner scenes |
|---|---|---|---|
| Ainz Ooal Gown | warehouse | Arrives in full regalia, internally panicking | **Albedo**: she arrives a step behind him · **Lord Genome**: two kings |
| Albedo | warehouse | Asks where Lord Ainz is, sweetly and dangerously | **Ainz Ooal Gown**: as above · **Makima**: two controllers |
| Asuna Yuuki | cafe | Asks the cafe if she can cook | **Kirito**: a couple, arriving together if their quests ever tie them · **Tohru**: a cook-off |
| Kirito | arena | Logs in by mistake, assumes it's a game | **Asuna Yuuki**: as above · **Simon**: two heroes |
| Batman | rooftop | A shadow on the rooftop; he's been watching you | **Joker**: the old enemy · **Twilight**: two detectives |
| Joker | warehouse | Leaves you a playing card and a laugh | **Batman**: as above · **Nui Harime**: two smiles |
| Cinderella | plaza | Loses a glass slipper in the plaza | **Rapi**: squadmates · **Mai Sakurajima**: two who vanish at a deadline |
| Rapi | arena | Reports for duty to nobody | **Cinderella**: as above · **Yoko**: two snipers |
| Darkness | arena | Asks to be hit, for training | **Megumin**: party members · **Levi**: she wants him to scold her |
| Megumin | plaza | Explodes something on the edge of town | **Darkness**: as above · **Kyoko Sakura**: two with one thing |
| Erza Scarlet | arena | Requips in the arena, and asks where the cake is | **Gray Fullbuster**: guildmates · **Levi**: two commanders |
| Gray Fullbuster | arena | Freezes the fountain, shirtless | **Erza Scarlet**: as above · **Kittan**: two shirtless men |
| Chisato Nishikigi | cafe | Opens a cafe stall in the cafe | **Takina Inoue**: arrive together (joint scene) · **Ruby Rose**: two cheerful fighters |
| Takina Inoue | cafe | Asks where the cafe's manager is | **Chisato Nishikigi**: (the joint scene) · **Homura Akemi**: two serious ones |

### Pack 06: Frieren, Dragon Maid, Persona, Spy × Family and more

| Newcomer | Where | Solo premise | Partner scenes |
|---|---|---|---|
| Frieren | library | Looking for a spell that makes flowers bloom | **Fern**: her apprentice drags her to breakfast · **Echidna**: two old scholars |
| Fern | library | Looking for Frieren, who's late | **Frieren**: as above · **Ram/Rem**: two who keep someone else on schedule |
| Kanna | school | Wants to go to school, and brings snacks | **Tohru**: family · **Madoka**: two gentle souls |
| Tohru | cafe | Offers to be the town's maid | **Kanna**: as above · **Mami Tomoe**: hosts |
| Protagonist | school | Transfers in, says very little, everyone likes him | **Yukari**: SEES members · **Yu Narukami**: two silent leaders |
| Yukari | school | Archery practice nearly hits you | **Protagonist**: as above · **Sayaka Miki**: two loud hearts |
| Twilight | cafe | Introduces himself as an ordinary psychiatrist | **Yor Forger**: his "wife" · **Batman**: two detectives |
| Yor Forger | plaza | Very politely asks if anyone needs anything disposed of | **Twilight**: as above · **Mikasa**: two quiet killers |
| Enterprise | beach | Watches the sea like it owes her something | **Rapi**: two soldiers · **Eren**: what's beyond the sea |
| Joker (P5) | cafe | Asks the cafe if he can work here | **Yu Narukami**: two Persona users · **Batman**: two masks |
| Kureiji Ollie | plaza | A zombie idol's first concert in town | **Ruby Hoshino**: two idols · **Marceline**: two undead musicians |
| Mai Sakurajima | library | In a bunny suit in the library, and nobody notices but you | **Kana Arima**: two famous faces · **Cinderella**: two who vanish |
| Marceline | rooftop | Floats over the roof playing bass | **Kureiji Ollie**: as above · **Frieren**: two who outlive everyone |
| Shadow | rooftop | Searching for someone who isn't here | **Homura Akemi**: two loners · **Sol Badguy**: two who don't need anyone |
| Sol Badguy | alley | Looking for a fight, and a cold drink | **Shadow**: as above · **Toph**: rematch |
| Yu Narukami | school | Cooks for everyone on his first day | **Protagonist**: as above · **Tohru**: a cook-off |

## Writing checklist, per scene

- [ ] Named exactly "World: Arrival, <Newcomer>" or "World: Arrival, <Newcomer> & <Other>".
- [ ] Casts the newcomer (and the other) by their CPU names, and the player speaks at least once.
- [ ] 8–12 lines: a first impression in the newcomer's voice, and something for the player to react to.
- [ ] Ends with a `choice` of two (or three) options, each with `(set side_<cast id>)`. At most one gives a pack;
      the other gives coins.
- [ ] Uses a background that fits where the newcomer's first seen (the outline's "Where").
- [ ] Goes in `world_pack/src` with the newcomer (as `extra_scenes`, like the quest visit scenes), so the packs
      import it. There, `build.py` adds "cast me as <the CPU>" at the top: write the newcomer as `me` (so its side flag is
      `side_me`), and add a `cast` line for the other character.

## Pacing change (2026-11-26): a newcomer's arrival plays when the player meets them

**The problem (reported by the user):** at the start of a week, every newcomer's arrival scene played back to back,
five in a row with a choice in each, before the player had control again. It felt random and disorienting.
- `world_roster.week_started` queued all of the week's newcomers.
- `world.next_scene` called `next_arrival` after each scene ended, so the next one began at once.

**The change:**
- **The week's news** still says who's new: "New in town this week: …". The newcomers are pending arrivals
  (`flags["arrivals"]`), and they're in town at their places as usual.
- **The arrival scene plays when the player meets the newcomer:**
  - when the player talks to them (the arrival scene is their introduction, in place of the talk);
  - or when the player arrives at a place where one is, or stays there into a new time of day.
  - **At most one** arrival scene per arrival or time of day. Other newcomers at the same place wait until the player
    talks to them or comes back.
- **No chaining:** a scene's end never starts an arrival by itself. `next_scene` no longer calls `next_arrival`.
- **Newcomers not met yet** stay pending past the week's end; there's no deadline.
- **The town marks them:** `town()["people"][i]["new"]` is true for a pending newcomer, and the page shows a "New"
  marker on them.
- **Saves already mid-queue:** the queue is left to play out; nothing is lost.
