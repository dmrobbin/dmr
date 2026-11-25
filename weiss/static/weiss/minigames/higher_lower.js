/* Higher or Lower (docs/minigames-plan.md, "Two games (Sam 2)"): a big card with its power is shown. Guess whether the next
   card's power is higher or lower (equal counts as right). Turns alternate: a right guess scores and keeps the turn, a
   wrong one passes it. First to five. The CPU reads the odds from the cards still to come, more or less well by
   difficulty. Registers in window.MinigameGames and is started by the shell (shell.js), which gives the ctx: area, cards,
   cpu, difficulty, random, say, score, status, end, fx and countdown. Its stop() is safe to call again.
   The stage (docs/minigames-polish-plan.md): the card before on the left, small and dim; the new card on the right, flipping
   in, with a stamp for the guess and a streak count. */
(() => {
  window.MinigameGames = window.MinigameGames || {};

  const FIRST_TO = 5;
  const SKILL = { easy: 0.45, normal: 0.75, hard: 0.95 }; // how often the CPU reads the odds (else it guesses)
  const PAUSE_MS = { easy: 1100, normal: 850, hard: 600 }; // the CPU's pause before it guesses
  const REVEAL_MS = 700; // a card is shown this long before the result
  // Sound (minigames/audio.js), if it's there: a short effect, or nothing.
  const sfx = (name) => { if (window.MinigameAudio) window.MinigameAudio.sfx(name); };

  const powerOf = (card) => {
    const n = Number(card.power);
    return card.power != null && Number.isFinite(n) ? n : null;
  };

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function startHigherLower(ctx) {
    const rnd = ctx.random;
    const skill = SKILL[ctx.difficulty] ?? SKILL.normal;
    const pause = PAUSE_MS[ctx.difficulty] ?? PAUSE_MS.normal;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // The deck: the cards with a power, in a random order.
    const deck = (ctx.cards || []).map((card) => ({ card, power: powerOf(card) })).filter((item) => item.power !== null);
    if (deck.length < 2) {
      ctx.status("Not enough cards with a power to play.");
      ctx.end("draw");
      return null;
    }
    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }

    // ---- The page ----
    const game = el("div", "hl-game");
    const stage = el("div", "hl-stage");
    // The card before, on the left: small and dimmed, with its power.
    const prev = el("div", "hl-prev");
    prev.hidden = true;
    const prevArt = el("img", "hl-prev-art");
    prevArt.alt = "";
    prevArt.addEventListener("error", () => prevArt.remove());
    const prevPower = el("p", "hl-prev-power", "");
    const prevName = el("p", "hl-prev-name", "");
    prev.append(prevArt, prevPower, prevName);
    // The new card, on the right: big, flipping in, with its power, and the stamp for the guess over it.
    const cardBox = el("div", "hl-card");
    const art = el("img", "hl-art");
    art.alt = "";
    art.addEventListener("error", () => art.remove());
    const name = el("p", "hl-name", "");
    const power = el("p", "hl-power", "");
    const stamp = el("p", "hl-stamp", "");
    stamp.setAttribute("aria-hidden", "true");
    cardBox.append(art, stamp, name, power);
    stage.append(prev, cardBox);
    const streakLine = el("p", "hl-streak", "");
    streakLine.setAttribute("aria-live", "polite");
    const choices = el("div", "hl-choices");
    choices.setAttribute("role", "group");
    choices.setAttribute("aria-label", "Your guess");
    const higher = el("button", "hl-higher", "▲ Higher");
    higher.type = "button";
    higher.dataset.guess = "higher";
    higher.append(el("kbd", "", "H"));
    const lower = el("button", "hl-lower", "▼ Lower");
    lower.type = "button";
    lower.dataset.guess = "lower";
    lower.append(el("kbd", "", "L"));
    choices.append(higher, lower);
    game.append(stage, streakLine, choices);
    ctx.area.append(game);

    // ---- The state ----
    const state = { current: deck.shift(), turn: "player", player: 0, cpu: 0, streak: 0, busy: false, over: false, timer: 0, shown: 0 };
    let stopped = false;

    function show(item, shownBefore) {
      state.shown += 1;
      cardBox.classList.remove("hl-flip");
      void cardBox.offsetWidth; // restart the flip
      if (!reduced) cardBox.classList.add("hl-flip");
      name.textContent = item.card.name || "";
      power.replaceChildren("Power ", el("strong", "", String(item.card.power ?? item.power)));
      art.remove();
      if (item.card.image) {
        art.src = item.card.image;
        cardBox.prepend(art);
      }
      stamp.textContent = "";
      stamp.className = "hl-stamp";
      if (shownBefore) {
        prev.hidden = false;
        prevArt.remove();
        if (shownBefore.card.image) {
          prevArt.src = shownBefore.card.image;
          prev.prepend(prevArt);
        }
        // The number to beat: as large and gold as the new card's power, with the card's name under it.
        prevPower.replaceChildren("Power ", el("strong", "", String(shownBefore.card.power ?? shownBefore.power)));
        prevName.textContent = shownBefore.card.name || "";
      } else {
        prev.hidden = true;
      }
    }

    // Whose turn it is: the round pill (the frame's), and the buttons for it.
    function paintTurn() {
      const yours = state.turn === "player" && !state.over;
      higher.disabled = lower.disabled = !yours || state.busy;
      ctx.status(state.over ? "" : state.turn === "player" ? "Your turn" : `${ctx.cpu.name}'s turn`);
    }

    function score() {
      ctx.score(state.player, state.cpu);
    }

    // The guess, as the odds say: the share of cards still to come that would be right for each, read well or not.
    function cpuGuess() {
      const now = state.current.power;
      let higherRight = 0;
      let lowerRight = 0;
      for (const item of deck) {
        if (item.power >= now) higherRight += 1;
        if (item.power <= now) lowerRight += 1;
      }
      const sensible = higherRight === lowerRight ? (rnd() < 0.5 ? "higher" : "lower") : higherRight > lowerRight ? "higher" : "lower";
      return rnd() < skill ? sensible : rnd() < 0.5 ? "higher" : "lower";
    }

    // A guess: the next card is turned over, and the guess is right or wrong. A right guess scores and keeps the turn.
    function resolve(guess, who) {
      if (state.over || stopped) return;
      const next = deck.shift();
      if (!next) {
        finishByCount();
        return;
      }
      const previous = state.current;
      const right = guess === "higher" ? next.power >= previous.power : next.power <= previous.power; // equal is right
      state.current = next;
      show(next, previous);
      stamp.textContent = right ? "✓" : "✗";
      stamp.className = `hl-stamp ${right ? "is-right" : "is-wrong"}`;
      const box = cardBox.getBoundingClientRect();
      if (right) ctx.fx.burst(box.left + box.width / 2, box.top + box.height / 2, { count: 14 });
      else ctx.fx.shake(cardBox);
      if (who === "player") {
        sfx(right ? "correct" : "wrong");
        if (right) state.player += 1;
        state.streak = right ? state.streak + 1 : 0;
        ctx.say(right ? "player_good" : "player_bad");
      } else {
        if (right) state.cpu += 1;
        ctx.say(right ? "cpu_good" : "cpu_bad");
      }
      streakLine.textContent = state.streak >= 2 ? `Streak ×${state.streak}` : "";
      score();
      if (!right) state.turn = who === "player" ? "cpu" : "player";
      state.busy = true;
      paintTurn();
      clearTimeout(state.timer);
      state.timer = setTimeout(() => {
        state.busy = false;
        if (state.player >= FIRST_TO) finish(state.player > state.cpu ? "win" : "lose");
        else if (state.cpu >= FIRST_TO) finish("lose");
        else if (!deck.length) finishByCount();
        else if (state.turn === "cpu") cpuTurn();
        else paintTurn();
      }, reduced ? 120 : REVEAL_MS);
    }

    function cpuTurn() {
      if (state.over || stopped) return;
      paintTurn();
      clearTimeout(state.timer);
      state.timer = setTimeout(() => resolve(cpuGuess(), "cpu"), reduced ? 120 : pause);
    }

    function finishByCount() {
      finish(state.player > state.cpu ? "win" : state.cpu > state.player ? "lose" : "draw");
    }

    function finish(result) {
      if (state.over) return;
      state.over = true;
      clearTimeout(state.timer);
      paintTurn();
      sfx(result); // a draw has no sound of its own
      // The results screen's line: the right guesses on each side.
      ctx.end(result, { line: `${state.player} right to ${ctx.cpu.name}'s ${state.cpu}.` }); // the shell calls stop()
    }

    // ---- Input ----
    const onPlayerGuess = (event) => {
      const guess = event.currentTarget.dataset.guess;
      if (state.turn !== "player" || state.busy || state.over) return;
      resolve(guess, "player");
    };
    higher.addEventListener("click", onPlayerGuess);
    lower.addEventListener("click", onPlayerGuess);

    const onKey = (event) => {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const guess = event.code === "KeyH" ? "higher" : event.code === "KeyL" ? "lower" : null;
      if (!guess || state.turn !== "player" || state.busy || state.over) return;
      event.preventDefault();
      resolve(guess, "player");
    };
    document.addEventListener("keydown", onKey);

    // The shell calls this when the game ends, when playing again, and when choosing another game.
    function stop() {
      if (stopped) return;
      stopped = true;
      clearTimeout(state.timer);
      if (window.MinigameAudio) window.MinigameAudio.stop();
      document.removeEventListener("keydown", onKey);
      higher.disabled = lower.disabled = true;
    }

    // ---- Start: the first card, and the player's turn ----
    show(state.current, null);
    if (window.MinigameAudio) window.MinigameAudio.start("higher_lower");
    score();
    paintTurn();
    return { stop };
  }

  window.MinigameGames.higher_lower = {
    title: "Higher or Lower",
    rule: "Will the next card's power be higher or lower? First to 5 wins.",
    about: "A card and its power. Is the next card's power higher or lower? Equal counts as right. First to five.",
    play: startHigherLower,
  };
})();
