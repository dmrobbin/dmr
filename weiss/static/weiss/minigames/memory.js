/* Memory (docs/minigames-plan.md): 16 face-down cards, 8 pairs of real cards. Flip two: a match keeps them and the turn.
   A miss passes the turn. The CPU remembers the cards it has seen, but not always: by difficulty. Most pairs wins. */
(() => {
  // How reliably the CPU remembers a card it has seen (per card, each time it chooses).
  const RECALL = { easy: 0.35, normal: 0.7, hard: 0.95 };
  const PAIRS = 8;

  function play(ctx) {
    const { area, cards, cpu, difficulty, random } = ctx;
    const recall = RECALL[difficulty] ?? RECALL.normal;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pause = (ms) => (reduced ? Math.min(ms, 120) : ms);
    const timers = [];
    let stopped = false;
    let turn = "player";
    let busy = false;
    let flipped = []; // indices face up this turn
    let matched = new Set();
    let seen = new Map(); // index -> card id, as the CPU has seen them
    let tiles = [];
    let pairsLeft = PAIRS;
    const score = { player: 0, cpu: 0 };

    const later = (fn, ms) => {
      const id = setTimeout(() => {
        if (!stopped) fn();
      }, pause(ms));
      timers.push(id);
    };

    // The pictured cards, shuffled, eight of them: each becomes a pair.
    const pool = (cards || []).filter((card) => card.image).slice();
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    const chosen = pool.slice(0, PAIRS);
    const deck = [];
    for (const card of chosen) deck.push(card, card);
    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }

    const grid = document.createElement("div");
    grid.className = "minigame-memory";
    grid.setAttribute("role", "group");
    grid.setAttribute("aria-label", "Memory cards");
    area.append(grid);
    tiles = deck.map((card, index) => {
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "minigame-tile";
      tile.dataset.index = String(index);
      tile.setAttribute("aria-label", `Card ${index + 1}, face down`);
      const back = document.createElement("span");
      back.className = "minigame-tile-back";
      back.setAttribute("aria-hidden", "true");
      const face = document.createElement("span");
      face.className = "minigame-tile-face";
      const img = document.createElement("img");
      img.alt = "";
      img.src = card.image;
      img.loading = "lazy";
      img.addEventListener("error", () => face.classList.add("no-art"), { once: true });
      const name = document.createElement("span");
      name.className = "minigame-tile-name";
      name.textContent = card.name;
      face.append(img, name);
      tile.append(back, face);
      tile.addEventListener("click", () => playerFlip(index));
      grid.append(tile);
      return tile;
    });

    const status = () => {
      if (stopped) return;
      ctx.status(`${turn === "player" ? "Your turn" : `${cpu.name}'s turn`} · pairs left ${pairsLeft}`);
    };

    const showFace = (index, up) => {
      const tile = tiles[index];
      tile.classList.toggle("is-up", up);
      tile.setAttribute("aria-label", `Card ${index + 1}, ${up ? deck[index].name : "face down"}`);
    };

    const scoreUp = () => ctx.score(score.player, score.cpu);

    // Keyboard focus: a matched pair is disabled, so the focus moves on to the next card still face down.
    const focusOpen = () => {
      const next = tiles.find((tile) => !tile.disabled);
      if (next) next.focus({ preventScroll: true });
    };

    const finish = () => {
      stopped = true;
      const result = score.player > score.cpu ? "win" : score.player < score.cpu ? "lose" : "draw";
      ctx.end(result);
    };

    // A pair is found: both tiles stay up, dim, and the finder keeps the turn.
    const found = (who, a, b) => {
      matched.add(a);
      matched.add(b);
      tiles[a].classList.add("is-matched");
      tiles[b].classList.add("is-matched");
      tiles[a].disabled = true;
      tiles[b].disabled = true;
      pairsLeft -= 1;
      score[who] += 1;
      scoreUp();
      ctx.sfx("match");
    };

    // The CPU sees every card that's turned up, and remembers it, most of the time.
    const remember = (index) => {
      seen.set(index, deck[index].id);
    };
    const recalls = (index) => seen.has(index) && random() < recall;

    // The CPU's pick: a pair it remembers in full, else a remembered card's partner, else any card it hasn't found.
    const cpuPick = () => {
      const open = tiles.map((_, i) => i).filter((i) => !matched.has(i));
      const known = open.filter((i) => recalls(i));
      for (const i of known) {
        const partner = open.find((j) => j !== i && recalls(j) && deck[j].id === deck[i].id);
        if (partner !== undefined) return [i, partner];
      }
      const first = known.length ? known[Math.floor(random() * known.length)] : open[Math.floor(random() * open.length)];
      const pairing = open.find((j) => j !== first && recalls(j) && deck[j].id === deck[first].id);
      const second = pairing !== undefined ? pairing : open.filter((j) => j !== first)[Math.floor(random() * (open.length - 1))];
      return [first, second];
    };

    function playerFlip(index) {
      if (stopped || busy || turn !== "player" || matched.has(index) || flipped.includes(index)) return;
      flip(index);
      remember(index);
      if (flipped.length < 2) return;
      busy = true;
      const [a, b] = flipped;
      later(() => {
        if (deck[a].id === deck[b].id) {
          found("player", a, b);
          ctx.say("player_good");
          flipped = [];
          busy = false;
          if (pairsLeft === 0) return finish();
          status();
          focusOpen();
          return;
        }
        ctx.say("player_bad");
        ctx.sfx("miss");
        later(() => {
          unflip();
          turn = "cpu";
          busy = false;
          status();
          later(cpuTurn, 700);
        }, 900);
      }, 500);
    }

    function flip(index) {
      flipped.push(index);
      showFace(index, true);
      ctx.sfx("flip");
    }
    function unflip() {
      for (const i of flipped) if (!matched.has(i)) showFace(i, false);
      flipped = [];
    }

    function cpuTurn() {
      if (stopped) return;
      const [a, b] = cpuPick();
      busy = true;
      flip(a);
      remember(a);
      later(() => {
        flip(b);
        remember(b);
        later(() => {
          if (deck[a].id === deck[b].id) {
            found("cpu", a, b);
            ctx.say("cpu_good");
            flipped = [];
            busy = false;
            if (pairsLeft === 0) return finish();
            status();
            later(cpuTurn, 800);
            return;
          }
          ctx.say("cpu_bad");
          ctx.sfx("miss");
          later(() => {
            unflip();
            turn = "player";
            busy = false;
            status();
            focusOpen();
          }, 900);
        }, 700);
      }, 700);
    }

    scoreUp();
    status();
    tiles[0].focus({ preventScroll: true });

    return {
      stop() {
        stopped = true;
        for (const id of timers) clearTimeout(id);
        timers.length = 0;
      },
    };
  }

  window.MinigameGames.memory = {
    title: "Memory",
    about: "Find the pairs. A match keeps your turn; a miss passes it.",
    play,
  };
})();
