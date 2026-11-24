/* The CPU's reactions in a duel (docs/duel-presentation-plan.md, part 2): a speech bubble on their side of the board, and
   the line in the game log. Moved here from play.js (docs/round-two-plan.md, item 8); the code is unchanged, and it reads
   the live duel through `app` (functions and getters: board(), cpuInfo(), the page's elements, promptKey(), atBrink()).

   play.js makes one with WeissReactions.create(app) and calls consider(before, now) as the board changes, and logHtml() for
   the game log. */
(function () {
  "use strict";

  function create(app) {
    // --- The CPU's reactions (docs/duel-presentation-plan.md, part 2): a speech bubble on their side of the board, and the
    // line in the game log. At most one a turn and six a game, 15 s apart; brink and winning once a game each and first.
    // A reaction waits while the intro, a combo cut-in, a climax takeover, a level-up or a prompt is on, and is dropped
    // if it's more than REACTION_WAIT_MS late, or the game's over.
    const REACTION_SHOW_MS = 3500;
    const REACTION_WAIT_MS = 4000;
    const REACTION_GAP_MS = 15000;
    const REACTION_MAX = 6;
    const REACTION_ONCE = ["duel_brink", "duel_winning"];
    let reactionGame = null; // the game the counts below are for
    let reactionState = null;
    let reactionPending = null; // {context, priority, at}: the one waiting to be said
    let reactionTimer = null;
    let reactionEl = null; // the bubble, on the root (the board redraws; this stays)
    let reactionHideTimer = null;
    let reactionLog = []; // what the CPU has said this game, for the log: {turn, name, text}

    function resetReactions() {
      reactionState = { count: 0, lastAt: -Infinity, lastTurn: null, used: new Set(), once: {} };
      reactionPending = null;
      reactionLog = [];
    }

    // The reactions to what this board update did, from the same before and now snapshots as the sounds.
    function considerReactions(before, now) {
      if (!app.cpuInfo() || !app.cpuInfo().reactions || app.SPECTATING()) return;
      if (app.board().game_number !== reactionGame || !reactionState) {
        reactionGame = app.board().game_number;
        resetReactions();
      }
      const was = before.opponent;
      const is = now.opponent;
      if (was && is) {
        const hit = is.damage_taken - was.damage_taken;
        if (is.level_ups > was.level_ups) queueReaction("duel_level");
        else if (is.negated > was.negated) queueReaction("duel_cancel");
        else if (hit >= 3) queueReaction("duel_hurt");
      }
      // Brink and winning are checked on every update while the side is at match point, and count as said only once
      // they're shown: a dropped one (late, or a prompt on) is tried again.
      if (app.atBrink("opponent")) queueReaction("duel_brink", true);
      if (app.atBrink("me")) queueReaction("duel_winning", true);
    }

    function queueReaction(context, priority = false) {
      const s = reactionState;
      const lines = (app.cpuInfo().reactions || {})[context] || [];
      if (!lines.length || s.count >= REACTION_MAX) return;
      if (priority) {
        if (s.once[context] || (reactionPending && reactionPending.context === context)) return;
      } else {
        if (s.lastTurn === app.board().turn_number) return; // one a turn
        if (performance.now() - s.lastAt < REACTION_GAP_MS) return; // 15 s between them
      }
      if (reactionPending && !(priority && !reactionPending.priority)) return; // a priority one takes the place of a normal one
      reactionPending = { context, priority, at: performance.now() };
      if (!reactionTimer) reactionTimer = setInterval(tryReaction, 250);
      tryReaction();
    }

    function tryReaction() {
      const pending = reactionPending;
      if (!pending) { clearInterval(reactionTimer); reactionTimer = null; return; }
      const late = performance.now() - pending.at > REACTION_WAIT_MS;
      if (late || !app.cpuInfo() || !app.board() || app.board().game_over || app.gameOverEl() || app.board().game_number !== reactionGame) {
        reactionPending = null;
        return tryReaction();
      }
      // The centred graphics (a turn's banner, a phase card, a cut-in, a takeover, a level-up) wait their turn: the late
      // clock restarts while one is up, so it's measured from when it clears. Prompts and the intro never clear on their own.
      const graphic = document.querySelector(".turn-banner, .phase-show, .combo-cutin, .cx-takeover") || app.board().level_up_pending;
      if (graphic) pending.at = performance.now();
      if (app.introEl() || graphic || app.promptKey()) return;
      reactionPending = null;
      showReaction(pending.context);
      tryReaction();
    }

    function showReaction(context) {
      const s = reactionState;
      const fresh = ((app.cpuInfo().reactions || {})[context] || []).filter((line) => !s.used.has(line.text));
      if (!fresh.length) return;
      const line = fresh[Math.floor(Math.random() * fresh.length)];
      s.used.add(line.text);
      s.count += 1;
      s.lastAt = performance.now();
      s.lastTurn = app.board().turn_number;
      if (REACTION_ONCE.includes(context)) s.once[context] = true;
      reactionLog.push({ turn: app.board().turn_number, name: app.cpuInfo().name, text: line.text });
      drawReaction(line);
      if (app.logEl()) app.logEl().insertAdjacentHTML("beforeend", reactionLogHtml(reactionLog.slice(-1)));
    }

    // The bubble, by the top corner of the board (their side: the opponent's back row is at its top).
    function drawReaction(line) {
      if (!app.boardEl()) return;
      if (!reactionEl) {
        reactionEl = document.createElement("div");
        reactionEl.className = "cpu-reaction";
        reactionEl.addEventListener("click", hideReaction);
        app.root().appendChild(reactionEl);
      }
      const picture = app.cpuInfo().picture;
      const face = picture && picture.image ? `<img class="cpu-reaction-face" src="${app.esc(picture.image)}" alt="">`
        : app.cpuInfo().image ? `<img class="cpu-reaction-face" src="${app.esc(app.cpuInfo().image)}" alt="">`
          : `<span class="cpu-reaction-face cpu-reaction-crest" aria-hidden="true">${app.esc(app.cpuInfo().name.slice(0, 1).toUpperCase())}</span>`;
      reactionEl.className = `cpu-reaction cpu-reaction-${line.mood === "pleased" || line.mood === "dismayed" ? line.mood : "main"}`;
      reactionEl.innerHTML = `${face}<p class="cpu-reaction-text">${app.esc(line.text)}</p>`;
      // On a phone the board's tabs ("Your board", "Aang's board") sit across its top: the bubble goes just below them.
      const rect = app.boardEl().getBoundingClientRect();
      const tabs = [...app.boardEl().querySelectorAll("button")].find((button) => /board/.test(button.textContent));
      // Absolute in the root, at the board's place now: it then scrolls with the board, not over it.
      reactionEl.hidden = false;
      const base = reactionEl.offsetParent || document.body;
      const origin = base.getBoundingClientRect();
      const below = tabs && window.matchMedia("(max-width: 40rem)").matches ? tabs.getBoundingClientRect().bottom + 6 : rect.top + 12;
      reactionEl.style.top = `${Math.max(8, below - origin.top)}px`;
      reactionEl.style.left = `${Math.max(8, rect.left - origin.left + 12)}px`;
      clearTimeout(reactionHideTimer);
      reactionHideTimer = setTimeout(hideReaction, REACTION_SHOW_MS);
    }

    function hideReaction() {
      clearTimeout(reactionHideTimer);
      if (reactionEl) reactionEl.hidden = true;
    }

    // The lines said this game, in the log after the game's own lines.
    function reactionLogHtml(lines = reactionLog) {
      return lines.map((entry) => `<p class="log-chat"><b>${app.esc(entry.name)}:</b> ${app.esc(entry.text)}</p>`).join("");
    }

    return { consider: considerReactions, logHtml: reactionLogHtml };
  }

  window.WeissReactions = { create };
})();
