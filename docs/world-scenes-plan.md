# World mode: the scenes still to write

The plan and outline for the quest scenes of the 69 CPUs that don't have quests yet. Nothing here is written yet:
each entry is a premise and a beat outline, to be written up in `world_pack/src/` the way the pilot was.

## Where things stand

- **Done (the pilot):** Aang, Azula, Denji, Power, Chisato and Takina. Each has a Friend and a Best friend gate quest,
  and every visit in them has a scene and a reward.
- **Already written for everyone, not part of this plan:** each CPU's two rank-up scenes ("World: <name>, Friend" and
  "World: <name>, Best friend"), its chatter, haunts and gift tastes. A quest leads into its rank-up scene, so each
  quest below is shaped to end where that scene picks up; read the CPU's rank-up scenes before writing its quests.
- **Written:** all six packs. Every CPU has its two gate quests and visit scenes (138 new quests, 138 scenes), and the
  22 conflict-pair CPUs have their `cold` lines. Each pack passes `check_world_pack`. Nothing is imported to the live
  site yet, and none of it has been played in the browser.

## What each CPU needs

For each CPU, in its `cpu(...)` call (see the pilot in `01_avatar_gurren.py`):

1. **Two gate quests** (`quests=`): one with `"gates": 2` (Friend) and one with `"gates": 5` (Best friend). Each has:
   - an `about` (one or two sentences) and an `offer` (2–4 lines in the CPU's voice);
   - 2–3 stages: **one of them a visit**, and the others duels, a card to have, a gift to give or a talk;
   - an ending (two only for the conflict pairs below), with its rewards.
2. **Two visit scenes** (`extra_scenes=`), one per quest, named in the visit objective.
3. **A `cold` line**, only for the CPUs in conflict pairs (what they say once a choice has closed their friendship).

## Rules every scene follows

These come from playing the pilot:

- **Something happens where the player goes.** Every visit plays a scene, and the scene plays the moment the player
  arrives (or stays there when time passes) at the right time of day.
- **The scene always gives something.** Every visit has `rewards`: coins or a pack, usually. The scene ends on a "You
  got" panel.
  - **Friend quests:** 150–250 coins, or a climax pack.
  - **Best friend quests:** a color, level or climax pack. Save the lucky pack for an ending.
- **The cast is there afterwards.** Everyone the scene casts is put at that place for that time of day, so after the
  scene the player can walk up and talk to them. A scene that casts two CPUs brings both.
- **Short and specific:** 5–8 lines, one moment, one thing learned about the character. The quest's talk step and
  ending carry the rest.
- **The place fits the character:** each scene below is at one of the CPU's haunts, at a time it's there, where that
  works for the story.
- **Card objectives name a card from the CPU's own deck** (its key cards, from `corpus/cpus/<name>.json`), so the quest
  log can show the card and say which set's packs to open.

### Conventions

- **Scene names:** "World: <CPU name>, <Place>". If a CPU has two scenes at one place, add a word: "World: Toph, Arena
  (belt)".
- **Times:** morning `[0]`, noon `[1]`, evening `[2]`, night `[3]`.
- **Backgrounds by place:**

  | Place | Background |
  |---|---|
  | plaza | `sakura` by day, `city` at night |
  | cafe | `cafe` |
  | library | `library` |
  | arena | `arena` |
  | shrine | `shrine` |
  | beach | `beach`, or `dusk` for evening |
  | forest | `forest` |
  | school | `classroom` |
  | alley | `city` or `rain` |
  | warehouse | `ruins` |
  | rooftop | `rooftop`, or `night` |

- **Rank-up rewards** are given separately, and a quest's ending rewards are the bigger ones. A visit's reward is the
  "keep going" reward in the middle.

## Conflict pairs: endings that close each other

As with Aang and Azula, each pair's Best friend quests end with a choice, and each side's main ending `locks` the other
side's Best friend quest. Whichever is finished first closes the other's friendship at Close friend, and that CPU then
speaks its `cold` line. Both CPUs in a pair need a `cold` line.

| Pack | Pair | The conflict |
|---|---|---|
| 01 | Simon ↔ Anti Spiral | Pierce the heavens, or accept the limit on evolution |
| 02 | Aqua Hoshino ↔ Akane Kurokawa | Aqua's revenge, or Akane stopping him from becoming a killer |
| 02 | Madoka ↔ Homura Akemi | Madoka makes her wish, or Homura turns back time to stop her |
| 03 | Aki Hayakawa ↔ Makima | Aki's own revenge on the Gun Devil, or Makima's control |
| 03 | Eren ↔ Mikasa | Eren keeps moving forward, or Mikasa stops him |
| 03 | Satsuki Kiryuin ↔ Ragyo Kiryuin | Satsuki's rebellion, or her mother's order |
| 04 | Ruby Rose ↔ Cinder Fall | The silver eyes, or the Fall Maiden's power |
| 04 | Giorno Giovanna ↔ DIO | His own dream, or his father's heaven |
| 04 | Emilia ↔ Echidna | Emilia's trial on her own terms, or the witch's contract |
| 05 | Ainz Ooal Gown ↔ Albedo | Ainz's trust in Nazarick, or Albedo's secret plot |
| 05 | Batman ↔ Joker | The one rule holds, or one bad day breaks it |

**One `removes`, the only one in the cast:** Levi's Best friend ending "Keep the promise" sends the Beast Titan away
for good (his promise to Erwin). Every other ending keeps everyone in town.

## The order to write them

One pack at a time, matching the files, so each batch is built, checked (`check_world_pack`) and imported together:

1. `01_avatar_gurren.py`: 9 CPUs (finishes Avatar, then Gurren Lagann)
2. `02_oshinoko_madoka.py`: 10 CPUs
3. `03_chainsaw_titan_killlakill.py`: 10 CPUs
4. `04_dandadan_rwby_jojo_rezero.py`: 12 CPUs
5. `05_overlord_sao_more.py`: 12 CPUs
6. `06_frieren_persona_more.py`: 16 CPUs

Within a pack, write the conflict pairs together, since their endings name each other's quest keys.

## A checklist for each CPU

- [ ] Read its rank-up scenes and chatter, so the quests lead into them in the same voice.
- [ ] Friend quest: offer, stages (with the visit), ending, rewards.
- [ ] Best friend quest: the same; two endings with `locks` if it's in a conflict pair.
- [ ] Two visit scenes, each with a reward.
- [ ] Any card objective uses a card from its own deck.
- [ ] A `cold` line, if it's in a conflict pair.
- [ ] `python world_pack/build.py` and `python manage.py check_world_pack world_pack/*.json` pass.

---

## The outlines

Each CPU's haunts are listed as place (times). Times: m = morning, n = noon, e = evening, N = night.

### Pack 01: Avatar and Gurren Lagann

#### Katara · warm · beach (n, e), plaza (m, n), shrine (e), cafe (m)

| | Friend | Best friend |
|---|---|---|
| Quest | **Without a Master**: Katara is teaching herself waterbending forms from a scroll, and wants someone to watch. | **The Southern Lights**: the anniversary of her mother's death; she wants company, not comfort. |
| Scene | "World: Katara, Beach" · beach · evening | "World: Katara, Shrine" · shrine · evening |
| Beats | Katara practises forms at the waterline and gets one wrong. A wave soaks you both, she laughs, then heals a scrape on your hand and realises she's better than she thought. | She lights a candle and talks about the raid, and her mother's necklace. She asks you to stay until it burns down, and you do. |
| Reward | 200 coins | color pack |

#### Sokka · warm · cafe (n, e), beach (m, n), plaza (e), arena (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Master Plan**: Sokka has a plan to win the town tournament, drawn on napkins. | **Space Sword**: he's forged a sword from a meteorite and needs a worthy test. |
| Scene | "World: Sokka, Cafe" · cafe · noon | "World: Sokka, Arena" · arena · noon |
| Beats | He lays out napkin diagrams across three tables. Halfway through he admits the plan is mostly sandwiches. You fix one step, and he insists it was his idea. | He unwraps the black blade, nervous it's ugly. His test cut splits a training dummy clean, and he admits he's never felt like a warrior before. |
| Reward | 150 coins | level pack |

#### Toph · aloof · arena (n, e), forest (n, e), plaza (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Seismic Sense**: Toph will only bother with someone who can "see" the way she does. | **The Blind Bandit**: her old Earth Rumble belt, and the family who never knew. |
| Scene | "World: Toph, Forest" · forest · evening | "World: Toph, Arena" · arena · evening |
| Beats | She makes you take your shoes off and close your eyes. She calls out every footstep in the forest, then admits she's showing off because no one ever asked. | She tosses you the championship belt and admits she misses her parents, then denies it. She says you're the first person she didn't have to fight to be seen. |
| Reward | climax pack | color pack |

#### Simon the digger · warm · plaza (m, n), beach (n, e), warehouse (N), school (m)

| | Friend | Best friend |
|---|---|---|
| Quest | **Dig Deeper**: Simon's drill found something under the old warehouse. | **Kamina's Shades**: Simon wears Kamina's glasses for the first time. |
| Scene | "World: Simon the digger, Warehouse" · warehouse · night | "World: Simon the digger, Plaza" · plaza · morning |
| Beats | He shows you a glowing core he dug up, scared to touch it alone. It hums when he holds it, and he says, quietly, "I found it. Me." | He tries the shades on, they're too big, and he laughs. He repeats Kamina's words, then says them in his own way. |
| Reward | 200 coins | level pack |

#### Simon · friendly · arena (n, e), rooftop (e, N), plaza (n) · **pair: Anti Spiral**

| | Friend | Best friend |
|---|---|---|
| Quest | **Row, Row**: the grown-up Simon can't sleep and goes looking at the stars. | **Pierce the Heavens**: the Anti Spiral says evolution must stop; Simon disagrees. |
| Scene | "World: Simon, Rooftop" · rooftop · evening | "World: Simon, Rooftop (night)" · rooftop · night |
| Beats | He names the stars Nia liked and asks if you think people get to keep the ones they lose. | The sky goes wrong. He tells you what the Anti Spiral offered, and that he's going to say no. He asks if you'll stand with him. |
| Reward | 200 coins | color pack |
| Endings | | "Pierce the heavens" locks Anti Spiral's Best friend quest |

#### Kittan · friendly · arena (n, e), plaza (n, e), warehouse (N), beach (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **Black Siblings**: Kittan is trying to buy presents for his three sisters. | **Last Stand**: Kittan talks about what courage costs. |
| Scene | "World: Kittan, Plaza" · plaza · noon | "World: Kittan, Arena" · arena · evening |
| Beats | He's holding three gifts and can't tell which sister gets which. You help, and he brags that his sisters would fight anyone for each other. | He wraps his fists, says he'd charge in first every time, and asks you to remember him loud. |
| Reward | 150 coins | climax pack |

#### Yoko · friendly · beach (n, e), arena (n, e), plaza (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Long-Range Support**: Yoko wants a spotter for target practice. | **Teacher Yoko**: after the war, Yoko wants to teach. |
| Scene | "World: Yoko, Beach" · beach · noon | "World: Yoko, Plaza" · plaza · evening |
| Beats | She lines up cans on the rocks, you call the wind, and she hits all six. Then she misses the seventh on purpose, so you don't get cocky. | She's sketching a lesson plan, and admits she's scared kids won't listen. She tests it on you and you listen. |
| Reward | 200 coins | color pack |

#### Lord Genome · villain · warehouse (e, N), shrine (N), library (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Spiral King's Library**: Genome wants someone to read the old histories to. | **The Last Lesson**: he warns you what's waiting beyond the spiral. |
| Scene | "World: Lord Genome, Library" · library · noon | "World: Lord Genome, Shrine" · shrine · night |
| Beats | He reads a chronicle aloud and corrects it from memory. He tests whether you'd have made his choices, and says you're less foolish than most. | He tells you why he ruled by fear: the Anti-Spirals. He gives you a warning to carry, and asks nothing back. |
| Reward | 200 coins | level pack |

#### Anti Spiral · villain · rooftop (N), warehouse (e, N), library (e) · **pair: Simon**

| | Friend | Best friend |
|---|---|---|
| Quest | **Observation**: the Anti Spiral studies the player like a specimen. | **The Spiral Nemesis**: it offers the player a quiet, finished universe. |
| Scene | "World: Anti Spiral, Library" · library · evening | "World: Anti Spiral, Rooftop" · rooftop · night |
| Beats | It asks why you read and why you hope. It records your answers without judging them, which is unsettling. | It shows you a sky with no growth and no loss. It asks you to help it persuade Simon to stop. |
| Reward | climax pack | color pack |
| Endings | | "Accept the limit" locks Simon's Best friend quest |

### Pack 02: Oshi no Ko and Madoka Magica

#### Akane Kurokawa · friendly · library (n, e), school (m, n), cafe (e) · **pair: Aqua**

| | Friend | Best friend |
|---|---|---|
| Quest | **Method Acting**: Akane is studying the player to play them in a role. | **Profile of a Killer**: Akane has worked out who Aqua is hunting, and what it's doing to him. |
| Scene | "World: Akane Kurokawa, Library" · library · noon | "World: Akane Kurokawa, Cafe" · cafe · evening |
| Beats | She has a notebook of your habits and copies your walk perfectly. Then she asks the one thing she can't work out: what do you want? | She lays out her profile of the man behind Ai's death. She asks you to help her stop Aqua before he crosses a line. |
| Reward | 200 coins | color pack |
| Endings | | "Stop him" locks Aqua's Best friend quest |

#### Aqua Hoshino · aloof · school (m, n), cafe (n, e), alley (N) · **pair: Akane**

| | Friend | Best friend |
|---|---|---|
| Quest | **Behind the Camera**: Aqua needs an extra for a reality show shoot. | **Revenge**: he's found a lead on the man who had Ai killed. |
| Scene | "World: Aqua Hoshino, School" · school · morning | "World: Aqua Hoshino, Alley" · alley · night |
| Beats | He directs you through a fake "candid" scene, coldly, then admits he likes how sincere you are on camera. That's rare in this business. | In the rain he shows you a photo and a name. He says he doesn't need your help, he needs a witness. |
| Reward | 150 coins | climax pack |
| Endings | | "Finish it" locks Akane's Best friend quest |

#### Kana Arima · aloof · school (n, e), plaza (n, e), cafe (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Ten-Second Crier**: Kana is rehearsing crying on cue, and it won't come. | **Child Star No More**: she's turned down for a role for being "too old". |
| Scene | "World: Kana Arima, School" · school · noon | "World: Kana Arima, Cafe" · cafe · evening |
| Beats | She fails twice, snaps at you, and then cries for real, which works. She swears you never saw it. | She orders three desserts and eats none. She asks if anyone remembers child stars once they grow up, then answers herself. |
| Reward | 200 coins | color pack |

#### Ruby Hoshino · warm · school (m, n), plaza (n, e), cafe (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **B-Komachi Rehearsal**: Ruby needs an audience of one for the new routine. | **Ai's Daughter**: she's found her mother's old concert ticket. |
| Scene | "World: Ruby Hoshino, Plaza" · plaza · noon | "World: Ruby Hoshino, Cafe" · cafe · evening |
| Beats | She dances the routine, nails the ending, then trips bowing. She makes you promise to be her first fan. | She turns the ticket over and asks whether you can love someone you only remember from a stage. |
| Reward | 150 coins | level pack |

#### Legendary Idol Ai · neutral · plaza (n, e), cafe (n, e), rooftop (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Lie of Love**: Ai runs a fan meet and wants to know if you can tell her real smile. | **Everyone's Idol**: Ai has never said "I love you" and meant it. |
| Scene | "World: Legendary Idol Ai, Plaza" · plaza · evening | "World: Legendary Idol Ai, Rooftop" · rooftop · night |
| Beats | She flashes three smiles and asks which was real. Whatever you answer, she says "wrong", sweetly, and remembers it. | Alone above the city lights she practises the words, and they feel like a lie. She asks you to listen until they don't. |
| Reward | 200 coins | color pack |

#### Madoka · warm · school (m, n), cafe (n, e), plaza (e) · **pair: Homura**

| | Friend | Best friend |
|---|---|---|
| Quest | **Kyubey's Offer**: a small white creature offered Madoka a wish; she wants your advice. | **A Wish**: the witches are winning; Madoka thinks she can make a wish that ends it. |
| Scene | "World: Madoka, School" · school · morning | "World: Madoka, Plaza" · plaza · evening |
| Beats | She describes the creature (narrated, no cast) and the contract. She asks if wishing for something is selfish. | She tells you the wish she's thought of. It's for everyone, and it costs her. She asks you to remember her. |
| Reward | 150 coins | color pack |
| Endings | | "Make the wish" locks Homura's Best friend quest |

#### Homura Akemi · aloof · school (m, n), rooftop (e, N), shrine (e) · **pair: Madoka**

| | Friend | Best friend |
|---|---|---|
| Quest | **Transfer Student**: Homura warns the player to keep away from Madoka. | **Once More**: the truth about the time loops. |
| Scene | "World: Homura Akemi, School" · school · morning | "World: Homura Akemi, Rooftop" · rooftop · night |
| Beats | She knows things she shouldn't, including your name. She says Madoka must never make a contract, and walks off. | She tells you how many times she's lived this month, then asks you to help her stop Madoka's wish, once more. |
| Reward | climax pack | color pack |
| Endings | | "Turn back time" locks Madoka's Best friend quest |

#### Kyoko Sakura · aloof · alley (e, N), shrine (n), plaza (n, e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Eat It All**: Kyoko shares food with people who don't waste it. | **Father's Church**: the ruin she never visits. |
| Scene | "World: Kyoko Sakura, Alley" · alley · evening | "World: Kyoko Sakura, Shrine" · shrine · noon |
| Beats | She tosses you an apple and watches whether you finish it. You do, so she gives you another, which is friendship by her rules. | She stands in the ruined chapel and tells you what her wish did to her family. Then she prays, badly, for the first time in years. |
| Reward | 200 coins | level pack |

#### Mami Tomoe · friendly · cafe (n, e), school (m, n), rooftop (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Tea Time**: Mami has baked far too much for one person. | **Not Alone**: Mami admits why she's always hosting. |
| Scene | "World: Mami Tomoe, Cafe" · cafe · noon | "World: Mami Tomoe, Rooftop" · rooftop · evening |
| Beats | She's set out a full tea service for two, as if she expected you. She explains each cake, then asks if you'll come back tomorrow. | Watching the sunset she says she's been alone since the accident, and fighting alone too. She asks if you'll be her partner. |
| Reward | 150 coins | color pack |

#### Sayaka Miki · friendly · school (m, n), beach (n, e), plaza (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Violinist**: Sayaka wants to get a CD signed for a friend in hospital. | **Mermaid's Wish**: she made a wish for someone else, and wonders if it was worth it. |
| Scene | "World: Sayaka Miki, School" · school · morning | "World: Sayaka Miki, Beach" · beach · evening |
| Beats | She's practising what to say to Kyosuke, out loud, badly. You coach her, and she says you're a better friend than she deserves. | She asks if anyone can be a hero without getting anything back. Then she decides you count as something back. |
| Reward | 200 coins | climax pack |

### Pack 03: Chainsaw Man, Attack on Titan and Kill la Kill

#### Aki Hayakawa · aloof · rooftop (e, N), cafe (m, n), arena (n) · **pair: Makima**

| | Friend | Best friend |
|---|---|---|
| Quest | **Smoke Break**: Aki needs someone who won't talk while he thinks. | **The Gun Devil**: his own revenge, or the one Makima plans for him. |
| Scene | "World: Aki Hayakawa, Rooftop" · rooftop · evening | "World: Aki Hayakawa, Rooftop (night)" · rooftop · night |
| Beats | He doesn't light the cigarette, he just holds it. He tells you about the Fox Devil's price, and that he's paying it gladly. | He says Makima has a plan for the Gun Devil and it isn't his. He asks if you'd help him do it his own way. |
| Reward | 150 coins | color pack |
| Endings | | "His own way" locks Makima's Best friend quest |

#### Makima · villain · rooftop (e, N), shrine (N), cafe (n) · **pair: Aki**

| | Friend | Best friend |
|---|---|---|
| Quest | **A Good Dog**: Makima tests whether the player follows instructions. | **Control**: Makima offers the player a place in her better world. |
| Scene | "World: Makima, Cafe" · cafe · noon | "World: Makima, Shrine" · shrine · night |
| Beats | She orders for you without asking, and it's exactly right. She says she likes people who are easy to read. | She explains a world without pain, run by her. She asks you to persuade Aki to let her handle the Gun Devil. |
| Reward | climax pack | color pack |
| Endings | | "Trust her" locks Aki's Best friend quest |

#### Beast Titan · villain · forest (e, N), warehouse (N), arena (n) · **can be sent away by Levi's ending**

| | Friend | Best friend |
|---|---|---|
| Quest | **Throwing Practice**: Zeke wants someone to play catch with. | **The Euthanasia Plan**: Zeke's calm plan to end Eldia's suffering. |
| Scene | "World: Beast Titan, Arena" · arena · noon | "World: Beast Titan, Forest" · forest · night |
| Beats | He throws a baseball far too hard and apologises politely. He talks about Tom Ksaver and the only good afternoons he had. | Among the trees he explains his plan gently, like a doctor. He asks if you think kindness can be cruel. |
| Reward | 150 coins | level pack |

#### Eren · aloof · arena (n, e), beach (e, N), forest (e) · **pair: Mikasa**

| | Friend | Best friend |
|---|---|---|
| Quest | **Beyond the Walls**: Eren wants to see the sea with someone. | **Keep Moving Forward**: he's seen the future, and he's going to go through with it. |
| Scene | "World: Eren, Beach" · beach · evening | "World: Eren, Beach (night)" · beach · night |
| Beats | He stands at the water's edge and says this is all he wanted as a kid. Then: "What's on the other side?" | In the dark he tells you he can't stop, and he won't explain why. He asks you not to let Mikasa follow him. |
| Reward | 200 coins | color pack |
| Endings | | "Keep moving forward" locks Mikasa's Best friend quest |

#### Levi · aloof · cafe (m, n), arena (n, e), school (e) · **the one `removes`**

| | Friend | Best friend |
|---|---|---|
| Quest | **Clean Up**: Levi will drink tea with someone who keeps a clean table. | **A Promise to Erwin**: Levi has one promise left to keep. |
| Scene | "World: Levi, Cafe" · cafe · morning | "World: Levi, Arena" · arena · evening |
| Beats | He wipes your table before you sit, and holds his cup oddly. He talks about his squad, briefly, then changes the subject. | Sharpening his blades, he tells you about Erwin's last order, and the Beast Titan. He asks if you'll be there when he keeps the promise. |
| Reward | 150 coins | color pack |
| Endings | | "Keep the promise" **removes** the Beast Titan |

#### Mikasa · aloof · arena (n, e), forest (m, n), plaza (e) · **pair: Eren**

| | Friend | Best friend |
|---|---|---|
| Quest | **The Scarf**: Mikasa lost her scarf in the forest. | **See You Later**: she has to choose between Eren and stopping him. |
| Scene | "World: Mikasa, Forest" · forest · morning | "World: Mikasa, Plaza" · plaza · evening |
| Beats | You find it on a branch. She ties it on, and tells you who gave it to her and why she never takes it off. | She asks what you'd do if the person you loved was about to do something terrible. She already knows her answer. |
| Reward | 200 coins | climax pack |
| Endings | | "Stop him" locks Eren's Best friend quest |

#### Nui Harime · villain · warehouse (e, N), alley (N), plaza (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **Sewing Circle**: Nui wants to make a doll of the player. | **Grand Couturier**: Nui shows what she really is. |
| Scene | "World: Nui Harime, Alley" · alley · night | "World: Nui Harime, Warehouse" · warehouse · evening |
| Beats | She measures you with scissors, cheerfully. The doll looks exactly like you, minus the eyes, which she says she'll "add later". | Among half-finished dresses she says Lady Ragyo made her perfect, and asks if you think a made thing can be loved. |
| Reward | climax pack | level pack |

#### Ragyo Kiryuin · villain · warehouse (e, N), rooftop (N), library (n) · **pair: Satsuki**

| | Friend | Best friend |
|---|---|---|
| Quest | **Life Fibers**: Ragyo explains what clothing truly is. | **Mother's Order**: Ragyo wants the player to bring Satsuki to heel. |
| Scene | "World: Ragyo Kiryuin, Library" · library · noon | "World: Ragyo Kiryuin, Warehouse" · warehouse · night |
| Beats | She glows faintly while she lectures. She says humanity is merely clothing's host, and wonders if you'd make good fabric. | She tells you Satsuki is planning a rebellion. She asks you to stand with the family, meaning her. |
| Reward | climax pack | color pack |
| Endings | | "Obey" locks Satsuki's Best friend quest |

#### Ryuko Matoi · friendly · arena (n, e), alley (e, N), plaza (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **Senketsu**: Ryuko's uniform talks, and she wants to know if you can hear it. | **Scissor Blade**: she's close to finding her father's killer. |
| Scene | "World: Ryuko Matoi, Arena" · arena · noon | "World: Ryuko Matoi, Alley" · alley · evening |
| Beats | She argues with her uniform in front of you, then asks if she's crazy. You say no, and she grins. Senketsu likes you. | She shows you the half-scissor and says she'll find the other half. She asks if you'll have her back when she does. |
| Reward | 200 coins | color pack |

#### Satsuki Kiryuin · aloof · school (m, n), rooftop (e, N), arena (e) · **pair: Ragyo**

| | Friend | Best friend |
|---|---|---|
| Quest | **Honnouji Academy**: Satsuki inspects the player like a new recruit. | **Rebellion**: Satsuki's life-long plan to overthrow her mother. |
| Scene | "World: Satsuki Kiryuin, School" · school · morning | "World: Satsuki Kiryuin, Rooftop" · rooftop · night |
| Beats | She asks three questions and judges each answer instantly. You pass, barely. She says "barely" is acceptable, for now. | Looking over the city she tells you everything she's built was a weapon aimed at Ragyo. She asks you to be part of it. |
| Reward | 150 coins | color pack |
| Endings | | "Rebel" locks Ragyo's Best friend quest |

### Pack 04: Dandadan, RWBY, JoJo and Re:Zero

#### Aira · aloof · school (m, n), plaza (n, e), cafe (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Chosen One**: Aira is certain she's destined for greatness. | **Acrobatic Silky's Gift**: the spirit inside her, and its daughter. |
| Scene | "World: Aira, School" · school · morning | "World: Aira, Plaza" · plaza · evening |
| Beats | She announces she's a hero, to you, at length. She's embarrassed when you agree, and secretly thrilled. | She tells you about the spirit's lost daughter and cries without meaning to. She asks you not to tell Okarun. |
| Reward | 150 coins | climax pack |

#### Momo Ayase · friendly · school (m, n), cafe (n, e), plaza (e), shrine (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **Ken Takakura**: Momo's ideal man is a film actor; she wants your opinion. | **Grandma Seiko's Shrine**: Momo helps her grandmother with a spirit, and wants backup. |
| Scene | "World: Momo Ayase, Cafe" · cafe · noon | "World: Momo Ayase, Shrine" · shrine · night |
| Beats | She shows you a poster and defends it fiercely. Then she admits her real crush is nothing like him, and changes the subject. | Talismans flutter at the shrine. Momo is braver than she looks, and asks you to hold the lantern. |
| Reward | 200 coins | color pack |

#### Okarun · friendly · library (n, e), school (m, n), alley (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **Turbo Granny**: Okarun has research on a yokai, and nobody believes him. | **Golden Balls**: he's still missing part of himself. |
| Scene | "World: Okarun, Library" · library · noon | "World: Okarun, Alley" · alley · night |
| Beats | He spreads out clippings and talks too fast. When you take him seriously, he's so surprised he forgets what he was saying. | He explains (awkwardly) the cursed thing he has to recover. He asks you to come along, because Momo can't always. |
| Reward | 150 coins | level pack |

#### Cinder Fall · villain · alley (e, N), warehouse (N), arena (n) · **pair: Ruby Rose**

| | Friend | Best friend |
|---|---|---|
| Quest | **The Maiden's Power**: Cinder wants to know what you'd do with power you weren't born with. | **The Fall of Beacon**: she needs the silver-eyed girl out of the way. |
| Scene | "World: Cinder Fall, Alley" · alley · evening | "World: Cinder Fall, Warehouse" · warehouse · night |
| Beats | A flame burns in her palm. She tells you she was a nobody once, and asks if taking what you're owed is wrong. | Glass shards hang in the air. She asks you to lure Ruby Rose somewhere quiet, and promises a share of the power. |
| Reward | climax pack | color pack |
| Endings | | "Take the power" locks Ruby Rose's Best friend quest |

#### Ruby Rose · warm · cafe (n, e), arena (n, e), plaza (m) · **pair: Cinder Fall**

| | Friend | Best friend |
|---|---|---|
| Quest | **Crescent Rose**: Ruby wants to show off her scythe. | **Silver Eyes**: Ruby learns what her eyes can do, and who's afraid of them. |
| Scene | "World: Ruby Rose, Arena" · arena · noon | "World: Ruby Rose, Cafe" · cafe · evening |
| Beats | She transforms the scythe three ways, and knocks over a rack doing it. She asks if you think weapons can be friends. | Over cookies she tells you about her mother, and the light she saw when Pyrrha fell. She asks you to help her stop Cinder. |
| Reward | 200 coins | color pack |
| Endings | | "Stop Cinder" locks Cinder Fall's Best friend quest |

#### Weiss Schnee · aloof · library (n, e), cafe (n, e), arena (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Heiress**: Weiss needs a study partner who won't flatter her. | **Summoning**: she's trying to summon her family's knight. |
| Scene | "World: Weiss Schnee, Library" · library · noon | "World: Weiss Schnee, Arena" · arena · evening |
| Beats | She corrects your notes and then thanks you, stiffly, for not apologising. | A glyph flickers and fails. She talks about her father, tries again, and the knight's arm appears. She lets you see her smile. |
| Reward | 150 coins | level pack |

#### DIO · villain · warehouse (N), alley (e, N), library (e) · **pair: Giorno**

| | Friend | Best friend |
|---|---|---|
| Quest | **The World**: DIO is curious whether the player fears him. | **Heaven**: DIO wants his son at his side, and the player to bring him. |
| Scene | "World: DIO, Library" · library · evening | "World: DIO, Warehouse" · warehouse · night |
| Beats | He reads by candlelight and asks your opinion of a philosopher, then of yourself. Time skips a beat, and he enjoys your face. | He speaks of "heaven" and of the son he's never met. He asks you to persuade Giorno to come home. |
| Reward | climax pack | color pack |
| Endings | | "Join your father" locks Giorno's Best friend quest |

#### Giorno Giovanna · neutral · cafe (n, e), plaza (m, n), beach (e) · **pair: DIO**

| | Friend | Best friend |
|---|---|---|
| Quest | **Gold Experience**: Giorno makes a flower grow from a coin. | **I, Giorno Giovanna, Have a Dream**: his father's shadow, and his own path. |
| Scene | "World: Giorno Giovanna, Cafe" · cafe · noon | "World: Giorno Giovanna, Beach" · beach · evening |
| Beats | He turns your coin into a flower and back again. He says he can tell a lot about people by whether they want it back. | At sunset he tells you what he knows of DIO. He asks you to help him become something his father never was. |
| Reward | 200 coins | color pack |
| Endings | | "My own dream" locks DIO's Best friend quest |

#### Jolyne Cujoh · friendly · beach (n, e), arena (n, e), plaza (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Stone Free**: Jolyne can unravel herself into string, and wants to show someone who won't scream. | **Green Dolphin Street**: her father, and the prison she broke out of. |
| Scene | "World: Jolyne Cujoh, Beach" · beach · noon | "World: Jolyne Cujoh, Arena" · arena · evening |
| Beats | She ties the string into a cat's cradle between you, and laughs when you're not scared. | She says she never knew her dad until he came for her. She asks if you think it's too late to start. |
| Reward | 150 coins | level pack |

#### Echidna · aloof · library (n, e), forest (e, N), shrine (n) · **pair: Emilia**

| | Friend | Best friend |
|---|---|---|
| Quest | **Tea Party**: the Witch of Greed invites the player to a tea that isn't tea. | **The Witch's Contract**: she offers to solve Emilia's trial for a price. |
| Scene | "World: Echidna, Library" · library · noon | "World: Echidna, Forest" · forest · night |
| Beats | She asks questions for the joy of the answers. She says "how interesting" once, sincerely, and makes it sound like a threat. | In a grove she lays out a contract written in light. She asks you to bring Emilia to sign. |
| Reward | climax pack | color pack |
| Endings | | "Sign the contract" locks Emilia's Best friend quest |

#### Emilia · warm · forest (m, n), plaza (n, e), shrine (e) · **pair: Echidna**

| | Friend | Best friend |
|---|---|---|
| Quest | **Puck**: Emilia talks to her little cat spirit and introduces the player. | **The Trial**: she must face her past in the tomb, on her own terms. |
| Scene | "World: Emilia, Forest" · forest · morning | "World: Emilia, Shrine" · shrine · evening |
| Beats | She introduces Puck (narrated), who approves of you. She's delighted and very formal about it. | She tells you what she saw in the trial: the frozen forest. She asks you to help her do it without the witch's help. |
| Reward | 200 coins | color pack |
| Endings | | "Her own terms" locks Echidna's Best friend quest |

#### Ram/Rem · neutral · cafe (m, n), forest (n, e), school (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Maid Duties**: the twins are short a pair of hands at the mansion. | **Twin Horns**: Rem's guilt about Ram's lost horn. |
| Scene | "World: Ram/Rem, Cafe" · cafe · morning | "World: Ram/Rem, Forest" · forest · evening |
| Beats | Ram gives the orders and Rem does the work. You help, and Ram calls you "barely adequate", which Rem says is high praise. | Rem tells you about the night of the fire, and Ram tells her to stop apologising. You see who's been holding up whom. |
| Reward | 150 coins | climax pack |

### Pack 05: Overlord, SAO, Batman Ninja, NIKKE, KonoSuba and Fairy Tail

#### Ainz Ooal Gown · villain · warehouse (e, N), shrine (N), library (n) · **pair: Albedo**

| | Friend | Best friend |
|---|---|---|
| Quest | **Momonga**: Ainz misses the player characters who logged off. | **Supreme Being**: Ainz must decide how far he trusts the guardians. |
| Scene | "World: Ainz Ooal Gown, Library" · library · noon | "World: Ainz Ooal Gown, Shrine" · shrine · night |
| Beats | He reads old guild rosters aloud. He forgets to sound like an overlord, then remembers abruptly. | He tells you something is wrong with Albedo's loyalty. He asks you to watch her, and admits he's afraid of what he'll find. |
| Reward | 200 coins | color pack |
| Endings | | "Trust Nazarick" locks Albedo's Best friend quest |

#### Albedo · villain · warehouse (e, N), rooftop (N), library (n) · **pair: Ainz**

| | Friend | Best friend |
|---|---|---|
| Quest | **Guardian Overseer**: Albedo inspects the player as a possible servant of Nazarick. | **Albedo's Plot**: her secret plan against the other Supreme Beings. |
| Scene | "World: Albedo, Warehouse" · warehouse · evening | "World: Albedo, Rooftop" · rooftop · night |
| Beats | She's charming, then horrifying, then charming again. She asks what you think of Lord Ainz and watches your face closely. | She shows you the order she's hiding: the other Supreme Beings are to be hunted. She asks you to keep it from Ainz. |
| Reward | climax pack | color pack |
| Endings | | "Keep her secret" locks Ainz's Best friend quest |

#### Asuna Yuuki · warm · cafe (n, e), arena (n, e), plaza (m)

| | Friend | Best friend |
|---|---|---|
| Quest | **Lunch with the Lightning Flash**: Asuna cooks for people she trusts. | **Our Home**: Asuna's idea of home, after the game. |
| Scene | "World: Asuna Yuuki, Cafe" · cafe · noon | "World: Asuna Yuuki, Plaza" · plaza · morning |
| Beats | She unpacks a bento she's proud of and watches you eat the first bite. She's relieved when you like it. | She talks about the little house on the 22nd floor, and asks what home looks like for you. |
| Reward | 200 coins | color pack |

#### Kirito · neutral · arena (n, e), cafe (n, e), forest (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **Beater**: Kirito wants a sparring partner who won't go easy on him. | **The Dual Blades**: the Moonlit Black Cats, and what he owes them. |
| Scene | "World: Kirito, Arena" · arena · noon | "World: Kirito, Forest" · forest · night |
| Beats | He spars with you, you lose, and he points out your one good move. He says you'll be fine. | He tells you about his old guild, and the night he hid his level. He asks you to tell him if he ever does it again. |
| Reward | 150 coins | level pack |

#### Batman · aloof · rooftop (N), alley (e, N), library (n, e) · **pair: Joker**

| | Friend | Best friend |
|---|---|---|
| Quest | **Detective Work**: Batman needs a second pair of eyes on a case. | **One Rule**: the Joker's plan, and the line Batman won't cross. |
| Scene | "World: Batman, Library" · library · noon | "World: Batman, Rooftop" · rooftop · night |
| Beats | He has clippings spread out and you spot the link he missed. He says "good" once, which is a lot. | Over the city he tells you the Joker wants him to kill. He asks you to make sure he doesn't. |
| Reward | 200 coins | color pack |
| Endings | | "The rule holds" locks Joker's Best friend quest |

#### Joker · villain · warehouse (e, N), alley (N), plaza (n) · **pair: Batman**

| | Friend | Best friend |
|---|---|---|
| Quest | **A Little Joke**: the Joker wants an audience. | **One Bad Day**: the Joker wants to prove anyone can break. |
| Scene | "World: Joker, Alley" · alley · night | "World: Joker, Warehouse" · warehouse · evening |
| Beats | He tells a joke with no punchline and laughs anyway. He gives you a playing card "for later". | He's built a funhouse for the Bat. He asks you to help him give Batman one bad day. |
| Reward | climax pack | color pack |
| Endings | | "One bad day" locks Batman's Best friend quest |

#### Cinderella · aloof · plaza (n, e), library (m, n), beach (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Glass Slipper**: Cinderella wants the player to find a lost shoe. | **Midnight**: what happens when the magic runs out. |
| Scene | "World: Cinderella, Library" · library · morning | "World: Cinderella, Beach" · beach · evening |
| Beats | She describes the slipper precisely, and coldly. When you find it, she nearly smiles. | At dusk she says the magic always ends, and asks if you'd still know her in rags. |
| Reward | 150 coins | climax pack |

#### Rapi · neutral · arena (n, e), rooftop (e, N), beach (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **Squad Leader**: Rapi runs a drill and wants an extra body. | **Red Hood**: memories she's not supposed to have. |
| Scene | "World: Rapi, Arena" · arena · noon | "World: Rapi, Rooftop" · rooftop · night |
| Beats | She drills you for ten minutes without a word, then says "acceptable". It's the highest grade she gives. | She tells you about a commander she can't remember, and a red scarf. She asks you to remind her, if she forgets you. |
| Reward | 200 coins | level pack |

#### Darkness · friendly · arena (n, e), plaza (n, e), forest (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Crusader**: Darkness wants the player to hit her as hard as they can. For training. | **Dustiness Ford Lalatina**: her noble name, and an arranged marriage. |
| Scene | "World: Darkness, Arena" · arena · noon | "World: Darkness, Plaza" · plaza · evening |
| Beats | She asks you to attack, enjoys it too much, and then lectures you sincerely about protecting others. | She admits her father arranged a match. She asks you to be at her side when she refuses it. |
| Reward | 150 coins | color pack |

#### Megumin · friendly · plaza (n, e), forest (n, e), beach (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **EXPLOSION!**: Megumin needs someone to carry her home after her daily explosion. | **The Daily Explosion**: she wants the player to rate her explosions. |
| Scene | "World: Megumin, Forest" · forest · noon | "World: Megumin, Beach" · beach · evening |
| Beats | She chants, the forest booms, and she falls flat. You carry her home while she critiques the blast. | She casts over the sea at sunset and asks for a score. Then she tells you about her sister, and why she only learned the one spell. |
| Reward | 200 coins | level pack |

#### Erza Scarlet · friendly · arena (n, e), cafe (n, e), plaza (m)

| | Friend | Best friend |
|---|---|---|
| Quest | **Strawberry Cake**: someone ruined Erza's cake, and she wants it replaced. | **Tower of Heaven**: Erza's childhood, and the name she gave herself. |
| Scene | "World: Erza Scarlet, Cafe" · cafe · noon | "World: Erza Scarlet, Arena" · arena · evening |
| Beats | You bring her a new slice and she eats it with great dignity, then thanks you as if you'd saved a city. | She requips into each armour, then into plain clothes. She tells you how she got her name. |
| Reward | 150 coins | color pack |

#### Gray Fullbuster · friendly · arena (n, e), beach (n, e), plaza (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Ice-Make**: Gray will sculpt anything you ask for (and he keeps losing his shirt). | **Ur's Ice**: his teacher, who turned herself into ice to save him. |
| Scene | "World: Gray Fullbuster, Beach" · beach · noon | "World: Gray Fullbuster, Plaza" · plaza · evening |
| Beats | He makes an ice sculpture of you, and his shirt is gone by the end. He doesn't notice until you tell him. | Snow starts to fall. He tells you about Ur, and what she taught him about sacrifice. |
| Reward | 200 coins | climax pack |

### Pack 06: Frieren, Dragon Maid, Persona, Spy × Family, Azur Lane, hololive and more

#### Frieren · aloof · library (n, e), forest (m, n), shrine (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **Spell Collector**: Frieren collects useless spells, and has found a new one. | **Himmel's Field**: the field of flowers Himmel loved. |
| Scene | "World: Frieren, Library" · library · noon | "World: Frieren, Shrine" · shrine · night |
| Beats | She shows you a spell that makes grapes sour. She's genuinely delighted, and asks if you'd like to learn it. | She casts the flower-field spell for you and says she didn't understand Himmel until he was gone. She doesn't want to make that mistake twice. |
| Reward | 150 coins | color pack |

#### Fern · neutral · library (m, n), cafe (n, e), forest (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Fern's Birthday**: Fern was given a present she didn't expect, and doesn't know how to say thank you. | **Zoltraak**: Fern's training, and the person who saved her. |
| Scene | "World: Fern, Cafe" · cafe · noon | "World: Fern, Forest" · forest · evening |
| Beats | She practises a thank-you on you, three ways, all very formal. You tell her the plain one is best, and she pouts. | She hits a target dead centre and tells you about Heiter, and why she trains so hard. |
| Reward | 200 coins | level pack |

#### Kanna · friendly · school (m, n), plaza (n, e), beach (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **Kobayashi's Lunch**: Kanna wants to share her packed lunch. | **Dragon Kid**: Kanna was exiled, and doesn't mind any more. |
| Scene | "World: Kanna, School" · school · morning | "World: Kanna, Beach" · beach · noon |
| Beats | She gives you half her lunch, very seriously, and watches you eat. That's how friends work, she explains. | She sparks a little lightning over the waves, and says she got sent away for pranks. She likes it better here. |
| Reward | 150 coins | climax pack |

#### Tohru · friendly · cafe (n, e), plaza (m, n), beach (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Tail Meat**: Tohru insists you try her cooking. | **Chaos Dragon**: Tohru's past, and why she stays. |
| Scene | "World: Tohru, Cafe" · cafe · noon | "World: Tohru, Beach" · beach · evening |
| Beats | She brings a dish of something suspicious and won't say what it is. It's good, and she's very smug. | At sunset she tells you about the war between dragon factions, and why a human life is worth staying for. |
| Reward | 200 coins | color pack |

#### Protagonist · neutral · school (m, n), rooftop (N), library (n, e)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Dark Hour**: there's a hidden hour at midnight, and he wants to see if you can feel it. | **Memento Mori**: the year he has left, and what he'll spend it on. |
| Scene | "World: Protagonist, Rooftop" · rooftop · night | "World: Protagonist, Library" · library · noon |
| Beats | At midnight the city goes still and green. He's unsurprised you're still awake, and says "huh" quietly. | He tells you, without much feeling, that he has a choice coming. Then, with more feeling, that he's glad he met you. |
| Reward | climax pack | color pack |

#### Yukari · friendly · school (m, n), beach (n, e), plaza (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Archery Club**: Yukari wants a partner for practice. | **Father's Message**: a video her father left before he died. |
| Scene | "World: Yukari, School" · school · morning | "World: Yukari, Beach" · beach · evening |
| Beats | She fires at a target, then asks you to try. You're terrible, and she laughs properly. | She plays you the video. It changes how she sees him, and she needs a minute. |
| Reward | 200 coins | level pack |

#### Twilight · neutral · cafe (n, e), library (m, n), plaza (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Operation Strix**: Twilight needs a cover for a meeting. | **A Spy's Family**: the family he built for a mission. |
| Scene | "World: Twilight, Cafe" · cafe · noon | "World: Twilight, Plaza" · plaza · evening |
| Beats | He briefs you in under a minute. You play your part, he's quietly impressed, and he forgets to sound like a stranger. | He watches families in the plaza and asks if a fake one can become real. He knows you'll keep the secret. |
| Reward | 150 coins | color pack |

#### Yor Forger · warm · plaza (m, n), cafe (n, e), alley (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **City Hall**: Yor wants practice at being "normal" at work. | **The Thorn Princess**: what Yor does at night. |
| Scene | "World: Yor Forger, Plaza" · plaza · morning | "World: Yor Forger, Alley" · alley · night |
| Beats | She practises small talk on you, and is far too intense about it. She's thrilled when you say she did well. | You find her after a "job". She's terrified you'll leave, and you don't. |
| Reward | 200 coins | climax pack |

#### Enterprise · neutral · beach (n, e), arena (m, n), rooftop (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **The Grey Ghost**: Enterprise runs drills and wants a sparring partner. | **Beyond War**: what she'll be if the fighting stops. |
| Scene | "World: Enterprise, Arena" · arena · morning | "World: Enterprise, Beach" · beach · evening |
| Beats | She drills like it's real, then asks if you've ever wondered why you fight. | She looks at the water and says she doesn't know who she is without a war. She asks you to help her find out. |
| Reward | 150 coins | color pack |

#### Joker (P5) · friendly · cafe (e, N), alley (N), library (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **Leblanc Coffee**: Joker makes curry and coffee for people he trusts. | **Calling Card**: the Phantom Thieves' next target. |
| Scene | "World: Joker (P5), Cafe" · cafe · evening | "World: Joker (P5), Alley" · alley · night |
| Beats | He serves you curry and coffee and says almost nothing. When you say it's good, he smiles once. | He hands you a calling card with a target's name. He asks if you're in. |
| Reward | 200 coins | color pack |

#### Kureiji Ollie · warm · plaza (n, e), school (m, n), shrine (N)

| | Friend | Best friend |
|---|---|---|
| Quest | **Zombie Idol**: Ollie wants to try out a new song. | **Graveyard Shift**: Ollie on not being alive, and being loved anyway. |
| Scene | "World: Kureiji Ollie, Plaza" · plaza · noon | "World: Kureiji Ollie, Shrine" · shrine · night |
| Beats | She sings at full volume and an arm nearly falls off. She's delighted you stayed for the whole song. | Among lanterns she asks if being dead makes her less real. She decides it doesn't, because you're here. |
| Reward | 150 coins | climax pack |

#### Mai Sakurajima · aloof · library (n, e), beach (n, e), school (m)

| | Friend | Best friend |
|---|---|---|
| Quest | **Bunny Girl**: Mai is vanishing from people's sight, and you can still see her. | **Adolescence Syndrome**: will people forget her completely? |
| Scene | "World: Mai Sakurajima, Library" · library · noon | "World: Mai Sakurajima, Beach" · beach · evening |
| Beats | She tests whether you can see her by sitting very close. You can, and she's annoyed by how relieved she is. | She asks you to say her name out loud every day. Then she makes you promise, and you do. |
| Reward | 200 coins | color pack |

#### Marceline · neutral · rooftop (N), forest (e, N), alley (e, N)

| | Friend | Best friend |
|---|---|---|
| Quest | **Bass Solo**: Marceline wants a listener for a new song. | **Simon and Marcy**: the Ice King, and the song she wrote for him. |
| Scene | "World: Marceline, Rooftop" · rooftop · night | "World: Marceline, Forest" · forest · evening |
| Beats | She floats above the roof and plays something unfinished. She asks you what it's missing, then fixes it. | She plays the song about Simon and doesn't finish it. You ask her to, and she does. |
| Reward | 150 coins | level pack |

#### Shadow · aloof · rooftop (N), alley (e, N), library (n)

| | Friend | Best friend |
|---|---|---|
| Quest | **Maria**: Shadow remembers a promise to someone he lost. | **Ultimate Lifeform**: what he was made to be, and what he chooses. |
| Scene | "World: Shadow, Rooftop" · rooftop · night | "World: Shadow, Alley" · alley · evening |
| Beats | He looks at the stars and says a name. When you ask who, he says, "someone who believed in people." | He says he was made a weapon. He asks if you think that's all he is, then says he's decided it isn't. |
| Reward | climax pack | color pack |

#### Sol Badguy · aloof · alley (N), arena (n, e), rooftop (e, N)

| | Friend | Best friend |
|---|---|---|
| Quest | **Rock You**: Sol needs a fight to clear his head. | **Gear**: what Sol is, and who he used to be. |
| Scene | "World: Sol Badguy, Arena" · arena · noon | "World: Sol Badguy, Rooftop" · rooftop · evening |
| Beats | He sizes you up, says "Hmph", then shows you one move properly. That's how he says you're worth it. | He tells you he was human once, and a scientist. He asks you not to make a big deal of it. |
| Reward | 200 coins | level pack |

#### Yu Narukami · friendly · school (m, n), library (n, e), cafe (e)

| | Friend | Best friend |
|---|---|---|
| Quest | **Junes Food Court**: Yu wants to cook for the investigation team, and needs a taste-tester. | **The Midnight Channel**: what Yu found on the other side of the TV. |
| Scene | "World: Yu Narukami, Cafe" · cafe · evening | "World: Yu Narukami, Library" · library · noon |
| Beats | He cooks something perfect and asks for brutal honesty. He takes your one note seriously. | He tells you about the TV world and the truth behind it. He asks if you'd go in with him. |
| Reward | 150 coins | color pack |

---

## Tally

| Pack | CPUs | Quests | Visit scenes | Conflict pairs | `cold` lines |
|---|---|---|---|---|---|
| 01 | 9 | 18 | 18 | 1 | 2 |
| 02 | 10 | 20 | 20 | 2 | 4 |
| 03 | 10 | 20 | 20 | 3 (and Levi's `removes`) | 6 |
| 04 | 12 | 24 | 24 | 3 | 6 |
| 05 | 12 | 24 | 24 | 2 | 4 |
| 06 | 16 | 32 | 32 | 0 | 0 |
| **All** | **69** | **138** | **138** | **11** | **22** |

## Open questions

- **Conflict pairs:** 11 pairs means 22 CPUs can end up with a closed friendship. That's more than the pilot's 2 of 6.
  Fewer pairs keep the town friendlier; more make each save's story its own. Which pairs to keep is a choice for
  whoever approves this plan.
- **Levi's `removes`:** it's the only CPU sent away in the whole cast. Keep it, or make it a lock like the others?
- **Pack 06 has no conflicts.** Its series are mostly standalone in this cast. A Spy × Family pair (Twilight ↔ Yor:
  telling each other the truth) could be a choice with no lock.
