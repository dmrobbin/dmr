/* Three cups (docs/minigames-plan.md): three real cards are shown face up, then the cups come down over them and they're
   shuffled. "Where's <card>?" Pick a cup. The CPU is the dealer: the shuffle gets faster each round (by difficulty) and the
   CPU taunts while it shuffles. Five rounds; find three or more to win.
   The table (docs/minigames-polish-plan.md): a felt table seen from above, SVG cups, swaps along arcs (one passes in front,
   the other behind), the target card's picture in the prompt, and the lift that slides the picked card out. The frame's
   start card begins the game; each round shows the cards for a moment, then the cups come down (no Start button). */
(() => {
  // The shuffle's step time for the first round, by difficulty (ms); each round it gets a little faster.
  const STEP_MS = { easy: 560, normal: 400, hard: 270 };
  const ROUNDS = 5;
  const WIN_AT = 3;
  const REVEAL_MS = 2200; // the three cards show face up this long before the cups come down
  const ARC = 14; // how far a swapping cup arcs, in per cent of the table's height (up or down): the arc stays on the felt

  // A cup, in SVG: tapered, with a rim, an opening and a highlight down the side. Its gradient id is per cup.
  function cupSvg(index) {
    const id = `minigame-cup-body-${index}`;
    // The cup sits on the bottom of its button (so its shadow, under the button, is right under it).
    return `<svg viewBox="0 0 100 120" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">
      <defs><linearGradient id="${id}" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0" stop-color="#7a5714"/><stop offset=".3" stop-color="#e8c25c"/><stop offset=".55" stop-color="#c39430"/><stop offset="1" stop-color="#5c410f"/>
      </linearGradient></defs>
      <path d="M18 24 L82 24 L75 110 Q74 116 68 116 L32 116 Q26 116 25 110 Z" fill="url(#${id})"/>
      <path d="M30 34 L33 104" stroke="#fff6d0" stroke-opacity=".45" stroke-width="4" stroke-linecap="round" fill="none"/>
      <ellipse cx="50" cy="24" rx="32" ry="8" fill="#f3d57f"/>
      <ellipse cx="50" cy="25" rx="23" ry="5" fill="#2a1d07" fill-opacity=".6"/>
      <ellipse cx="50" cy="24" rx="32" ry="8" fill="none" stroke="#fff3c4" stroke-opacity=".7"/>
    </svg>`;
  }

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function play(ctx) {
    const { area, cards, cpu, difficulty, random, fx } = ctx;
    const step = STEP_MS[difficulty] ?? STEP_MS.normal;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pause = (ms) => (reduced ? Math.min(ms, 120) : ms);
    const timers = [];
    const frames = [];
    let stopped = false;
    let busy = true;
    let round = 0;
    const score = { player: 0, cpu: 0 };

    const later = (fn, ms) => {
      timers.push(setTimeout(() => {
        if (!stopped) fn();
      }, pause(ms)));
    };

    // Each round's three cards: pictured, and three different names. Names match ignoring case and the spaces around
    // them, so two printings of one card (RR and PR, say) never share a round. A set with fewer distinct names fills the
    // rest from what's there, and the status says so.
    const nameKey = (card) => String(card.name || "").trim().toLowerCase();
    const pictured = (cards || []).filter((card) => card.image);
    let trio = [];
    let distinctShortfall = 0;
    function chooseTrio() {
      const pool = pictured.slice();
      for (let i = pool.length - 1; i > 0; i--) {
        const j = Math.floor(random() * (i + 1));
        [pool[i], pool[j]] = [pool[j], pool[i]];
      }
      const picked = [];
      const names = new Set();
      for (const card of pool) {
        if (picked.length === 3) break;
        if (names.has(nameKey(card))) continue;
        names.add(nameKey(card));
        picked.push(card);
      }
      distinctShortfall = picked.length < 3 ? 3 - picked.length : 0;
      for (const card of pool) {
        if (picked.length === 3) break;
        if (!picked.includes(card)) picked.push(card);
      }
      trio = picked;
    }

    // ---- The table ----
    const stage = el("div", "minigame-cups");
    const prompt = el("p", "minigame-cups-prompt");
    prompt.setAttribute("aria-live", "polite");
    const felt = el("div", "minigame-felt");
    felt.setAttribute("role", "group");
    felt.setAttribute("aria-label", "Cups");
    const row = el("div", "minigame-cups-row");
    felt.append(row);
    stage.append(prompt, felt);
    area.append(stage);

    // Each cup covers one card. order[slot] is the cup now in that slot (left to right).
    const cupEls = [0, 1, 2].map((index) => {
      const holder = el("div", "minigame-cup-slot");
      const shadow = el("div", "minigame-cup-shadow");
      shadow.setAttribute("aria-hidden", "true");
      const card = el("div", "minigame-card-under");
      const img = el("img");
      img.alt = "";
      const name = el("span", "minigame-card-name");
      card.append(img, name);
      const cup = el("button", "minigame-cup");
      cup.type = "button";
      cup.setAttribute("aria-label", `Cup ${index + 1}`);
      cup.innerHTML = cupSvg(index);
      cup.addEventListener("click", () => pick(index));
      cup.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const slot = slotOf(index);
        const next = order[event.key === "ArrowLeft" ? Math.max(0, slot - 1) : Math.min(2, slot + 1)];
        cupEls[next].cup.focus();
      });
      holder.append(shadow, card, cup);
      row.append(holder);
      return { holder, card, img, nameEl: name, cup, index };
    });
    let order = [0, 1, 2]; // slot -> cup index
    let target = 0; // the cup index holding the card asked for this round

    const slotOf = (cupIndex) => order.indexOf(cupIndex);
    // A cup's place: x in slots (a slot is one holder's width), y in per cent of a holder's height (negative is up).
    const place = (cupIndex, x, y) => {
      const { holder } = cupEls[cupIndex];
      holder.style.setProperty("--x", String(x));
      holder.style.setProperty("--y", String(y));
    };
    const layout = () => {
      order.forEach((cupIndex, slot) => place(cupIndex, slot, 0));
    };

    // Two cups swap places along arcs: one passes in front (down), the other behind (up). Their order changes at once.
    function swapSlots(sa, sb, duration, done) {
      const ca = order[sa];
      const cb = order[sb];
      [order[sa], order[sb]] = [cb, ca];
      if (duration <= 0) {
        layout();
        return done();
      }
      const started = performance.now();
      const frame = (now) => {
        if (stopped) return;
        const t = Math.min(1, (now - started) / duration);
        const eased = t * t * (3 - 2 * t);
        const arc = Math.sin(Math.PI * t) * ARC;
        place(ca, sa + (sb - sa) * eased, arc);
        place(cb, sb + (sa - sb) * eased, -arc);
        if (t < 1) frames.push(requestAnimationFrame(frame));
        else done();
      };
      frame(started);
      frames.push(requestAnimationFrame(frame));
    }

    // The cups up (cards in view, for the reveal) or down (covering them).
    const raise = (on) => row.classList.toggle("is-raised", on);
    // The cups can be picked only when they're to be picked.
    const setPickable = (on) => {
      for (const { cup } of cupEls) cup.disabled = !on;
    };

    const setStatus = () => ctx.status(`Round ${round} of ${ROUNDS}${distinctShortfall ? " · a name repeats in this set" : ""}`);

    // The prompt: the card asked for, with its picture.
    function askFor() {
      const card = trio[target];
      const picture = el("img", "minigame-prompt-art");
      picture.alt = "";
      picture.src = card.image;
      picture.addEventListener("error", () => picture.remove(), { once: true });
      prompt.replaceChildren(el("span", "", "Where's "), picture, el("strong", "", card.name), el("span", "", "?"));
    }

    // Fills the cups' cards with this round's three cards.
    function showTrio() {
      cupEls.forEach(({ card, img, nameEl }, index) => {
        const c = trio[index];
        card.classList.remove("no-art");
        img.src = c.image;
        img.onerror = () => card.classList.add("no-art");
        nameEl.textContent = c.name;
        card.classList.remove("is-out");
      });
      for (const { holder } of cupEls) holder.classList.remove("is-picked", "is-answer");
    }

    // The round: the cards show face up with the cups raised, then the cups come down, the shuffle runs, and the question
    // comes after it.
    function nextRound() {
      if (stopped) return;
      round += 1;
      if (round > ROUNDS) return finish();
      chooseTrio();
      if (trio.length < 3) {
        // Not enough pictured cards to lay out three cups: say so, and end the game as a draw.
        ctx.status("This set has too few pictured cards for Three Cups.");
        stopped = true;
        return ctx.end("draw");
      }
      showTrio();
      setStatus();
      prompt.textContent = "Remember where they are.";
      order = [0, 1, 2];
      layout();
      target = Math.floor(random() * 3);
      busy = true;
      setPickable(false);
      raise(true);
      later(begin, REVEAL_MS);
    }

    // The cups come down over the cards, and the shuffle begins, with the CPU's patter.
    function begin() {
      raise(false);
      prompt.textContent = "Watch the shuffle.";
      later(() => {
        ctx.say("cpu_good"); // the dealer's patter, as the cups go down
        shuffle(3 + round, () => {
          askFor();
          busy = false;
          setPickable(true);
          cupEls[0].cup.focus({ preventScroll: true });
        });
      }, 300);
    }

    // Swaps two cups at a time, each step visible, with a line from the CPU now and then.
    function shuffle(swaps, done) {
      const stepTime = Math.max(160, step * Math.pow(0.9, round - 1));
      let k = 0;
      ctx.sfx("shuffle");
      const go = () => {
        if (stopped) return;
        if (k >= swaps) return done();
        const a = Math.floor(random() * 3);
        let b = Math.floor(random() * 3);
        if (b === a) b = (a + 1) % 3;
        swapSlots(a, b, reduced ? 0 : stepTime * 0.85, () => {});
        k += 1;
        if (k % 3 === 0) ctx.say("cpu_good");
        later(go, stepTime);
      };
      go();
    }

    function pick(index) {
      if (stopped || busy) return;
      busy = true;
      setPickable(false);
      const hit = index === target;
      const picked = cupEls[index];
      const answer = cupEls[target];
      picked.holder.classList.add("is-picked"); // the cup lifts
      picked.card.classList.add("is-out"); // and the card slides out from under it
      answer.card.classList.add("is-out");
      answer.holder.classList.add("is-answer");
      ctx.sfx("cup");
      ctx.sfx("reveal");
      const cupBox = picked.cup.getBoundingClientRect();
      const answerBox = answer.card.getBoundingClientRect();
      if (hit) {
        score.player += 1;
        prompt.textContent = `Yes: ${trio[target].name}.`;
        fx.burst(answerBox.left + answerBox.width / 2, answerBox.top + answerBox.height / 2, { count: 16 });
        fx.pop(cupBox.left + cupBox.width / 2, cupBox.top, "+1", { tone: "good" });
        ctx.say("player_good");
        ctx.sfx("correct");
      } else {
        score.cpu += 1;
        prompt.textContent = `No: ${trio[target].name} is under cup ${slotOf(target) + 1}.`;
        fx.shake(picked.cup);
        fx.pop(answerBox.left + answerBox.width / 2, answerBox.top, "+1", { tone: "bad" });
        ctx.say("cpu_good");
        ctx.sfx("wrong");
      }
      ctx.score(score.player, score.cpu);
      later(() => {
        for (const { holder, card } of cupEls) {
          holder.classList.remove("is-picked", "is-answer");
          card.classList.remove("is-out");
        }
        nextRound();
      }, 1800);
    }

    function finish() {
      stopped = true;
      const result = score.player >= WIN_AT ? "win" : "lose";
      ctx.end(result, { line: `You found ${score.player} of ${ROUNDS}.` });
    }

    ctx.score(0, 0);
    ctx.say("start");
    setStatus();
    later(nextRound, 600);

    return {
      stop() {
        stopped = true;
        for (const id of timers) clearTimeout(id);
        timers.length = 0;
        for (const id of frames) cancelAnimationFrame(id);
        frames.length = 0;
      },
    };
  }

  window.MinigameGames.cups = {
    title: "Three Cups",
    rule: "Watch the shuffle, then find the card. Find 3 of 5 to win.",
    about: "Find the card under the right cup. Three right of five wins.",
    play,
  };
})();
