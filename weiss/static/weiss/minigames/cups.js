/* Three cups (docs/minigames-plan.md): three real cards are shown, then covered by cups and shuffled. "Where's <card>?"
   Pick a cup. The CPU is the dealer: the shuffle gets faster each round (by difficulty) and the CPU taunts while it
   shuffles. Five rounds; find three or more to win. */
(() => {
  // The shuffle's step time for the first round, by difficulty (ms); each round it gets a little faster.
  const STEP_MS = { easy: 560, normal: 400, hard: 270 };
  const ROUNDS = 5;
  const WIN_AT = 3;

  function play(ctx) {
    const { area, cards, cpu, difficulty, random } = ctx;
    const step = STEP_MS[difficulty] ?? STEP_MS.normal;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pause = (ms) => (reduced ? Math.min(ms, 120) : ms);
    const timers = [];
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

    const stage = document.createElement("div");
    stage.className = "minigame-cups";
    const prompt = document.createElement("p");
    prompt.className = "minigame-cups-prompt";
    prompt.setAttribute("aria-live", "polite");
    const row = document.createElement("div");
    row.className = "minigame-cups-row";
    row.setAttribute("role", "group");
    row.setAttribute("aria-label", "Cups");
    stage.append(prompt, row);
    area.append(stage);

    // Each cup covers one card. order[slot] is the cup now in that slot (left to right).
    const cupEls = [0, 1, 2].map((index) => {
      const holder = document.createElement("div");
      holder.className = "minigame-cup-slot";
      const card = document.createElement("div");
      card.className = "minigame-card-under";
      const img = document.createElement("img");
      img.alt = "";
      const name = document.createElement("span");
      name.className = "minigame-card-name";
      card.append(img, name);
      const cup = document.createElement("button");
      cup.type = "button";
      cup.className = "minigame-cup";
      cup.setAttribute("aria-label", `Cup ${index + 1}`);
      cup.addEventListener("click", () => pick(index));
      cup.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const slot = slotOf(index);
        const next = order[event.key === "ArrowLeft" ? Math.max(0, slot - 1) : Math.min(2, slot + 1)];
        cupEls[next].cup.focus();
      });
      holder.append(card, cup);
      row.append(holder);
      return { holder, card, img, nameEl: name, cup, index };
    });
    let order = [0, 1, 2]; // slot -> cup index
    let target = 0; // the cup index holding the card asked for this round

    const slotOf = (cupIndex) => order.indexOf(cupIndex);
    // Cups are placed by slot; the card under each cup moves with it.
    const layout = () => {
      order.forEach((cupIndex, slot) => {
        cupEls[cupIndex].holder.style.setProperty("--slot", String(slot));
      });
    };

    const showCards = (up) => {
      for (const { card } of cupEls) card.classList.toggle("is-up", up);
    };
    const covered = (on) => {
      for (const { cup } of cupEls) {
        cup.classList.toggle("is-lifted", !on);
        cup.disabled = on; // the cups are live only when they're to be picked
      }
    };

    const setStatus = () => ctx.status(`Round ${round} of ${ROUNDS} · you ${score.player} · ${cpu.name} ${score.cpu}${distinctShortfall ? ` · this set has only ${3 - distinctShortfall} different names, so a name repeats` : ""}`);

    // The three cards, in full: picture, name and the characteristics the card view shows. Shown before each shuffle,
    // until the player presses Start.
    const reveal = document.createElement("div");
    reveal.className = "minigame-reveal";
    const startButton = document.createElement("button");
    startButton.type = "button";
    startButton.className = "minigame-start";
    startButton.textContent = "Start";
    startButton.addEventListener("click", () => begin());
    stage.insertBefore(reveal, row);

    function revealCard(card) {
      const box = document.createElement("article");
      box.className = "minigame-reveal-card";
      const art = document.createElement("div");
      art.className = "minigame-reveal-art";
      const img = document.createElement("img");
      img.alt = "";
      img.src = card.image;
      img.addEventListener("error", () => art.classList.add("no-art"), { once: true });
      art.append(img);
      const title = document.createElement("h3");
      title.className = "minigame-reveal-name";
      title.textContent = card.name;
      const facts = document.createElement("dl");
      facts.className = "minigame-reveal-facts";
      const rows = [["Level", card.level], ["Power", card.power], ["Cost", card.cost], ["Color", card.color], ["Type", card.type], ["Trigger", card.trigger], ["Rarity", card.rarity]];
      for (const [label, value] of rows) {
        const dt = document.createElement("dt");
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.textContent = value === undefined || value === null || value === "" ? "—" : String(value);
        facts.append(dt, dd);
      }
      box.append(art, title, facts);
      return box;
    }

    // Fills the reveal and the cups with this round's three cards.
    function showTrio() {
      cupEls.forEach(({ card, img, nameEl }, index) => {
        const c = trio[index];
        card.classList.remove("no-art");
        img.src = c.image;
        img.onerror = () => card.classList.add("no-art");
        nameEl.textContent = c.name;
      });
      reveal.replaceChildren(...trio.map((card) => revealCard(card)), startButton);
    }

    // The round: show the cards, wait for Start (no timer), then cover them and shuffle. The question comes after.
    function nextRound() {
      if (stopped) return;
      round += 1;
      if (round > ROUNDS) return finish();
      chooseTrio();
      if (trio.length < 3) {
        // Not enough pictured cards to lay out three cups: say so, and end the game as a draw.
        ctx.status("This set has too few pictured cards for Three cups.");
        stopped = true;
        return ctx.end("draw");
      }
      showTrio();
      setStatus();
      prompt.textContent = "";
      covered(false);
      showCards(true);
      order = [0, 1, 2];
      layout();
      target = Math.floor(random() * 3);
      busy = true;
      row.hidden = true;
      reveal.hidden = false;
      startButton.disabled = false;
      startButton.focus({ preventScroll: true });
    }

    // Start: the cards go under the cups and the shuffle begins, with the CPU's patter.
    function begin() {
      if (stopped || reveal.hidden) return; // Start only while the cards are showing
      startButton.disabled = true;
      reveal.hidden = true;
      row.hidden = false;
      later(() => {
        ctx.say("cpu_good"); // the dealer's patter, as the cups go down
        covered(true);
        showCards(false);
        shuffle(3 + round, () => {
          covered(false);
          prompt.textContent = `Where's ${trio[target].name}?`;
          busy = false;
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
        [order[a], order[b]] = [order[b], order[a]];
        layout();
        k += 1;
        if (k % 3 === 0) ctx.say("cpu_good");
        later(go, stepTime);
      };
      go();
    }

    function pick(index) {
      if (stopped || busy) return;
      busy = true;
      covered(true);
      cupEls[index].holder.classList.add("is-picked");
      const hit = index === target;
      ctx.sfx("cup");
      // Lift the cup to show the card under it, and the card asked for.
      cupEls[index].cup.classList.add("is-lifted");
      cupEls[index].card.classList.add("is-up");
      cupEls[target].card.classList.add("is-up");
      cupEls[target].holder.classList.add("is-answer");
      ctx.sfx("reveal");
      if (hit) {
        score.player += 1;
        prompt.textContent = `Yes: ${trio[target].name}.`;
        ctx.say("player_good");
        ctx.sfx("correct");
      } else {
        score.cpu += 1;
        prompt.textContent = `No: ${trio[target].name} is under cup ${slotOf(target) + 1}.`;
        ctx.say("cpu_good");
        ctx.sfx("wrong");
      }
      ctx.score(score.player, score.cpu);
      later(() => {
        cupEls.forEach(({ holder }) => holder.classList.remove("is-picked", "is-answer"));
        nextRound();
      }, 1800);
    }

    function finish() {
      stopped = true;
      const result = score.player >= WIN_AT ? "win" : "lose";
      ctx.end(result);
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
      },
    };
  }

  window.MinigameGames.cups = {
    title: "Three cups",
    about: "Find the card under the right cup. Three right of five wins.",
    play,
  };
})();
