# End-to-end findings (real clicks in Edge)

1. **Shop counter covered by the guide (step: shop).** The counter's hotspot sits under the guide's figure in the
   middle of the stage. A click on the middle of the counter lands on the guide, not the counter. The left side of the
   counter is clear and works. Found by e2e/tutorial.py; screenshot in e2e/scratch/shots/debug-shop.png.
2. **Deck step never completes (softlock, reported by the user as "play a game" unreachable).** With a legal deck saved
   and the player back in the town, the server's tutorial is still on step `deck`, with the deck step's lines
   unplayed (`tutorial.lines`: "Almost there! Your deck is what you'll duel with." and three more). The town shows
   "Your deck is legal" and the goal, but the lines never play. The guide's click plays only its greeting and closes,
   with no choices, so "Play a game" never appears. Reproduced by real clicks: e2e/tutorial.py, stuck at "minigame".
   Evidence: e2e/scratch/shots/stuck.png and the server state printed by the run.
   Likely split: the step should complete when the deck becomes legal (server), and the town should play the pending
   tutorial lines when it opens (page). Both paths were checked separately in the earlier playthroughs with stubs, which
   is why it got through them.
3. **Play a game blocked by the tutorial gate (step: minigame).** The guide's "Play a game" option is shown, and the
   server allows it, but the page disables it ("Not yet: Play a game with Aang"). tutLabel in world_town.js doesn't map
   "Play a game" to the minigame step, so the tutorial's gate treats it as an unrelated option. Found by e2e/tutorial.py.
4. **Intermittent tab crash after the minigame (step: minigame to duel). Status: not reproduced since the script's last-pair fix (2 clean runs, both reach the duel); watch it.** In about 3 of 7 runs, the page crashed on the
   town straight after the memory game returned to it ("Target crashed" / "Page crashed"). Not memory: about 50 GB
   free. Not reproduced when run alone. Needs a look at the town's first render after a world game (the tutorial's
   lines, the "Where to now?" chooser). Probe output: e2e/tutorial.py --probe.
5. **Card pictures re-requested on every deck click (step: deck).** The deck builder re-creates its pool on each + or
   − click, so each card's picture is requested again: 50+ times for one card in one run. Harmless with pictures that
   are cached, but wasteful. The placeholder cards 404 (no pictures), so the requests show up in the run.
6. **A memory win in under 20 seconds is refused ("That game ended too quickly to count").** Expected by design, but the
   end screen then offers only "Back to the town". Check the player can play the game again (it isn't counted, so
   they should be able to). The script waits 22 seconds before finishing a game for this reason.
