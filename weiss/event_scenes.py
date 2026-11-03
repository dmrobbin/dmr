"""Starter events for the infinite challenge: scenes staff can add from the CPU creation tab (scene_views.starter_events),
then change like any other. Each is a bargain, mostly a pact (weiss.buffs): something for something. They use only
the narrator and the player, so they don't depend on which CPUs there are."""

STARTERS = [
    ("Event: The Forge", """# An infinite challenge event. Reforge: spare cards from the pool melted down into new packs.
background crimson
screen flash
narrator: The path opens onto a forge. The heat reaches you before the light does.
narrator: A smith with no face holds out a blackened hand. "Your spares," it rasps. "Cards you don't use. I can make them into something new."
choice Feed the forge?
- Hand over your spare cards (give reforge)
- Keep what you have -> leave
narrator: The fire takes them. When it dies down, there are fresh packs cooling on the anvil.
end
label leave
narrator: The smith shrugs, and the forge roars on behind you.
"""),
    ("Event: Blood Moon Altar", """# An infinite challenge event. Blood pact: packs now, the next opponent at its hardest.
background night
narrator: A red moon hangs over a stone altar. Three packs lie on it, still sealed.
narrator: Carved into the stone: TAKE THEM, AND THE NEXT ONE YOU FACE WILL FIGHT WITH EVERYTHING IT HAS.
choice Take the packs?
- Take them (give blood_pact)
- Leave them -> leave
screen shake
narrator: Somewhere up the path, something wakes up angry.
end
label leave
narrator: The moon watches you go.
"""),
    ("Event: Ambush on the Road", """# An infinite challenge event. Ambush: the next fight starts with damage, and pays out if it's won.
background forest
narrator: Rustling in the trees. Someone's waiting for you up ahead.
player: I could go around...
narrator: ...or walk straight into it. Whoever's laying the trap is carrying something worth taking.
choice What do you do?
- Spring the trap (give ambush)
- Take the long way round -> around
screen shake
narrator: You walk on, ready for the hit.
end
label around
narrator: The long way is quiet, and empty-handed.
"""),
    ("Event: The Gambler", """# An infinite challenge event. All in: second chances traded for lucky packs.
background dusk
narrator: A gambler shuffles a deck that never seems to end.
narrator: "Those second chances of yours," she says, without looking up. "Bet them. Every one. Two lucky packs a chance."
choice Go all in?
- All in (give all_in)
- Fold -> fold
narrator: She sweeps your chips away and slides the packs across, grinning.
end
label fold
narrator: "Coward," she says, warmly.
"""),
    ("Event: Shrine of Sacrifice", """# An infinite challenge event. Sacrifice: every copy of a random deck card, for a lucky pack and a climax pick.
background void
narrator: A shrine of white stone, and a bowl in front of it.
narrator: Whatever you give it, you will never see again. What it gives back is rare.
choice Make an offering?
- Give it a card from your deck (give sacrifice)
- Back away -> away
screen flash
narrator: The bowl is empty. Something glitters where the card was.
end
label away
narrator: The shrine is silent.
"""),
    ("Event: Crossroads", """# An infinite challenge event. A choice of the next fight's terms: go first with nothing, or start with stock.
background dawn
narrator: The path splits. One way is short and steep; the other is long and gives you time to prepare.
choice Which way?
- The short way: they'll be waiting, but there's loot on the climb (give outpaced)
- The long way: arrive ready (give war_chest)
narrator: You set off.
"""),
    ("Event: The Devil's Bargain", """# An infinite challenge event. Two random pacts to pick from, or neither.
background crimson
narrator: A figure in a fine coat steps out of the dark, smiling too widely.
narrator: "I have deals, {player}. Wonderful deals. Every one has a small, small price."
offer 2 pacts: Shake on one?
narrator: "Pleasure doing business."
"""),
    ("Event: Wandering Spirit", """# An infinite challenge event. A plain gift, or a gamble on a random pact.
background ocean
narrator: A pale light drifts across the path and stops in front of you.
narrator: It offers a gift. Or, if you're brave, something stranger.
choice What do you ask for?
- A gift (give random)
- Something stranger (give pact)
narrator: The light fades, and leaves something behind.
"""),
]
