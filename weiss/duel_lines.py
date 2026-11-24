"""Built-in duel lines any CPU can say: reactions in a speech bubble mid-duel (docs/duel-presentation-plan.md,
section 2), and the pre-duel lines about the player's history with it (docs/round-two-plan.md, section 2: see the
comment there).

DUEL_DEFAULTS is a list of (context, min rank, script), merged into chatter.DEFAULTS. Each script is one line of at most
45 characters of speech, so it fits two lines of a phone's bubble, with no card-rule jargon. "They" is the CPU:
- duel_hurt: they took a big hit (3 or more damage from one attack)
- duel_cancel: they cancelled the player's damage
- duel_level: they levelled up
- duel_brink: they're at match point
- duel_winning: the player is at match point

Reactions draw from every tier up to the player's rank, so at rank 2 and above the rank-2 lines play alongside the
rank-0 ones, and a CPU's own duel lines play alongside both.
"""

DUEL_DEFAULTS = [
    # They took a big hit.
    ("duel_hurt", 0, "them (dismayed): That one stung."),
    ("duel_hurt", 0, "them (dismayed): Okay. I felt that."),
    ("duel_hurt", 0, "them (dismayed): Ow. Noted."),
    ("duel_hurt", 0, "them: Not bad. Don't get used to it."),
    ("duel_hurt", 0, "them (dismayed): Hm. I walked right into that."),
    ("duel_hurt", 0, "them: Lucky. Let's see you do it twice."),
    ("duel_hurt", 2, "them (dismayed): {player}! You could have warned me."),
    ("duel_hurt", 2, "them (pleased): Ha, okay, that was a good one. Ow."),
    ("duel_hurt", 2, "them (dismayed): You've been practising. I can tell."),
    # They cancelled the player's damage.
    ("duel_cancel", 0, "them (pleased): Not today."),
    ("duel_cancel", 0, "them (pleased): Missed me."),
    ("duel_cancel", 0, "them (pleased): Close, but no."),
    ("duel_cancel", 0, "them: Nothing landed. Try again."),
    ("duel_cancel", 0, "them (pleased): Ha. Shrugged that right off."),
    ("duel_cancel", 0, "them: The deck's on my side for once."),
    ("duel_cancel", 2, "them (pleased): Sorry, {player}. Not sorry."),
    ("duel_cancel", 2, "them (pleased): You'll have to hit harder than that."),
    ("duel_cancel", 2, "them (pleased): Ooh, so close. I'd be annoyed too."),
    # They levelled up.
    ("duel_level", 0, "them: That's a level. I'm just getting started."),
    ("duel_level", 0, "them (dismayed): Fine. That hurt. Now I'm stronger."),
    ("duel_level", 0, "them: Every point you take makes me stronger."),
    ("duel_level", 0, "them (pleased): Now we're talking."),
    ("duel_level", 0, "them: Up a level. Things change from here."),
    ("duel_level", 0, "them (pleased): Now the good cards come out."),
    ("duel_level", 2, "them (pleased): Level up! Brace yourself, {player}."),
    ("duel_level", 2, "them (pleased): Here's the part you won't like."),
    ("duel_level", 2, "them: Don't worry, I'll go easy. That's a lie."),
    # They're at match point.
    ("duel_brink", 0, "them (dismayed): One more and it's over. I know."),
    ("duel_brink", 0, "them (dismayed): Not like this. Not yet."),
    ("duel_brink", 0, "them: Back to the wall. That's when I fight best."),
    ("duel_brink", 0, "them (dismayed): Okay. No more mistakes."),
    ("duel_brink", 0, "them: You'll have to finish it. I won't fold."),
    ("duel_brink", 0, "them (dismayed): How did it get this close?"),
    ("duel_brink", 2, "them (dismayed): You're really going to do this to me?"),
    ("duel_brink", 2, "them: If I go down, {player}, I go down swinging."),
    # The player is at match point.
    ("duel_winning", 0, "them (pleased): One more, {player}. Just one."),
    ("duel_winning", 0, "them: You're on the edge. Careful now."),
    ("duel_winning", 0, "them (pleased): Almost there. Shall I finish it?"),
    ("duel_winning", 0, "them: Brace yourself. This is where it ends."),
    ("duel_winning", 0, "them (pleased): You held on well. Not for long."),
    ("duel_winning", 0, "them: Last chance. Make it count."),
    ("duel_winning", 2, "them (pleased): Don't you dare give up on me now."),
    ("duel_winning", 2, "them: One hit left, {player}. Show me a comeback."),

    # Before a duel: the player's history with this CPU (docs/round-two-plan.md, section 2). One line each, at most 90
    # characters of speech (the versus intro's bubble). {count} is the duel number for a milestone (10, 25, 50, 100) and
    # the streak's length for a streak.
    # The duel with this CPU is a milestone.
    ("history_milestone", 0, "them (pleased): Duel number {count}, {player}. Who's counting? Me, apparently."),
    ("history_milestone", 0, "them: That's {count} duels between us. I know your tricks by now."),
    ("history_milestone", 0, "them (pleased): {count} duels, {player}. Let's make this one worth remembering."),
    ("history_milestone", 0, "them: {count} times across this table. You'd think one of us would've learned by now."),
    # The player won the last 3 or more.
    ("history_streak_won", 0, "them (dismayed): You've beaten me {count} times running. That ends now."),
    ("history_streak_won", 0, "them (dismayed): {count} in a row, {player}? I've been studying. This one's mine."),
    ("history_streak_won", 0, "them: Your streak's at {count}. Enjoy it while it lasts."),
    ("history_streak_won", 0,
     "them (dismayed): I've lost {count} straight. I'm not saying I'm desperate. I'm desperate."),
    # The player lost the last 3 or more.
    ("history_streak_lost", 0, "them (pleased): That's {count} wins in a row for me. Want to make it one more?"),
    ("history_streak_lost", 0, "them: {count} in a row, {player}. Maybe try something different this time?"),
    ("history_streak_lost", 0, "them (pleased): I've won the last {count}. Don't let it get to you."),
    ("history_streak_lost", 0, "them: {count} straight. Come on, {player}, I know you've got better than that."),
    # The player lost the last one.
    ("history_revenge", 0, "them (pleased): Back for a rematch? I'd want one too."),
    ("history_revenge", 0, "them: Last time went my way. Think you've worked it out?"),
    ("history_revenge", 0, "them (pleased): Back for revenge, {player}? Good. I like a grudge match."),
    ("history_revenge", 0, "them: I remember our last duel. I bet you do too."),
    # The player won the last one.
    ("history_rematch_won", 0, "them (dismayed): You beat me last time. I haven't forgotten."),
    ("history_rematch_won", 0, "them: Last time was yours, {player}. This time won't be."),
    ("history_rematch_won", 0, "them (dismayed): I've thought about our last duel ever since. Let's go."),
    ("history_rematch_won", 0, "them: You won last time. I've made some changes since."),
]
