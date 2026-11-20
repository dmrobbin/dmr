/* The minigames' shared frame (docs/minigames-plan.md, "The frame"): the CPU panel with a portrait and a speech bubble,
   the scoreboard, the game's area and the end screen. A game registers itself in MinigameGames and is started with
   MinigameShell.start(root, data, options); it gets a ctx (below) and returns { stop() }. */
(() => {
  // Keep any registrations already made: a game script may load before this one.
  const games = window.MinigameGames || {};
  window.MinigameGames = games;

  const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // The shared audio module (audio.js, docs/minigames-plan.md "Round 3"). Until it loads, sound calls do nothing.
  const audio = () => window.MinigameAudio || null;

  // A seed as a number: a number as it is, anything else (a text id) hashed (FNV-1a), so every id gives its own game.
  function seedOf(value) {
    if (typeof value === "number" && Number.isFinite(value)) return Math.floor(value) >>> 0;
    let hash = 2166136261;
    for (const ch of String(value)) {
      hash ^= ch.charCodeAt(0);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  // A seeded random number generator (mulberry32): a game replays the same way from the same seed.
  function seeded(seed) {
    let a = seed >>> 0 || 1;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  // The CPU's picture for a mood: pleased when they're ahead, dismayed when behind, otherwise their main picture.
  function portraitSrc(cpu, mood = "main") {
    const pics = cpu.portraits || {};
    if (pics.kind === "none") return cpu.avatar || null;
    return pics[mood] || pics.main || cpu.avatar || null;
  }

  // The CPU's line for a moment, not the same as the last one. {player} is the player's name.
  function pickLine(lines, moment, rng, last, playerName) {
    const list = (lines && lines[moment]) || [];
    if (!list.length) return "";
    const pool = list.length > 1 ? list.filter((line) => line !== last) : list;
    const line = pool[Math.floor(rng() * pool.length)];
    return line.replace(/\{player\}/g, playerName);
  }

  // start(root, data, options): builds the frame into root and plays the game. Returns { stop(), restart() }.
  function start(root, data, options = {}) {
    const game = games[data.game];
    if (!game) throw new Error(`No minigame called "${data.game}".`);
    // With a seed (a co-op match, a world game), every play deals and plays the same game from it. Without one, as before:
    // a random deal once, and each play after it carries on from there.
    const seed = options.seed != null ? seedOf(options.seed) : null;
    let rng = seeded(seed != null ? seed : Math.floor(Math.random() * 1e9));
    // The CPU's lines have their own generator, so what they say (and when) can't change the game's deal.
    let lineRng = seeded(seed != null ? (seed ^ 0x5bd1e995) >>> 0 : Math.floor(Math.random() * 1e9));
    const playerName = options.playerName || "You";
    let score = { player: 0, cpu: 0 };
    let lead = "tie";
    let lastLine = "";
    let running = null;
    let ended = false;

    root.replaceChildren();
    const section = el("section", "minigame");
    section.dataset.game = data.game;
    const head = el("header", "minigame-head");
    head.append(el("h2", "minigame-title", game.title || data.game), el("p", "minigame-status", ""));
    const scoreline = el("p", "minigame-scoreline");
    const youScore = el("span", "minigame-score minigame-score-you", playerName);
    const cpuScore = el("span", "minigame-score minigame-score-cpu", data.cpu.name);
    youScore.append(" ", el("b", "", "0"));
    cpuScore.append(" ", el("b", "", "0"));
    scoreline.append(youScore, el("span", "minigame-sep", " · "), cpuScore);

    const cpuBox = el("div", "minigame-cpu");
    const portrait = el("div", "minigame-portrait");
    const src = portraitSrc(data.cpu);
    if (src) {
      const img = el("img", "minigame-picture");
      img.alt = "";
      img.src = src;
      img.addEventListener("error", () => img.replaceWith(el("span", "minigame-initial", data.cpu.name.slice(0, 1))), { once: true });
      portrait.append(img);
    } else {
      portrait.append(el("span", "minigame-initial", data.cpu.name.slice(0, 1)));
    }
    const bubble = el("p", "minigame-bubble");
    bubble.setAttribute("aria-live", "polite");
    cpuBox.append(portrait, el("span", "minigame-name", data.cpu.name), bubble);

    const area = el("div", "minigame-area");
    area.tabIndex = -1;
    const end = el("div", "minigame-end");
    end.hidden = true;
    const endTitle = el("h3", "minigame-end-title", "");
    const endScore = el("p", "minigame-end-score", "");
    const endLine = el("p", "minigame-end-line", "");
    endLine.setAttribute("aria-live", "polite");
    const again = el("button", "button-small", "Play again");
    again.type = "button";
    const choose = el("button", "button-small secondary", "Choose another game");
    choose.type = "button";
    // A seeded game (the infinite challenge, co-op, a world game) can't be replayed for the same deal, so there's no
    // "Play again" there; "Choose another game" only where the page allows it (options.allowChoose). Unseeded: as before.
    again.hidden = seed != null;
    choose.hidden = seed != null && !options.allowChoose;
    end.append(endTitle, endScore, endLine, el("div", "minigame-end-buttons"));
    end.querySelector(".minigame-end-buttons").append(again, choose);

    section.append(head, scoreline, cpuBox, area, end);
    root.append(section);

    const paintScore = () => {
      youScore.querySelector("b").textContent = String(score.player);
      cpuScore.querySelector("b").textContent = String(score.cpu);
      endScore.textContent = `${playerName} ${score.player} · ${data.cpu.name} ${score.cpu}`;
    };

    const setMood = (mood) => {
      const img = portrait.querySelector("img");
      const next = portraitSrc(data.cpu, mood);
      if (img && next) img.src = next;
    };

    const say = (moment) => {
      const line = pickLine(data.lines, moment, lineRng, lastLine, playerName);
      if (!line) return;
      lastLine = line;
      bubble.textContent = line;
      bubble.classList.remove("minigame-bubble-on");
      void bubble.offsetWidth; // restart the bubble's little rise
      bubble.classList.add("minigame-bubble-on");
      return line;
    };

    const ctx = {
      area,
      cards: data.cards,
      cpu: data.cpu,
      difficulty: data.difficulty,
      random: rng,
      say,
      sfx(name) {
        const sound = audio();
        if (sound && sound.sfx) sound.sfx(name);
      },
      status(text) {
        head.querySelector(".minigame-status").textContent = text;
      },
      score(player, cpu) {
        score = { player, cpu };
        paintScore();
        const next = player > cpu ? "player" : cpu > player ? "cpu" : "tie";
        if (next !== lead) {
          lead = next;
          if (next === "player") setMood("dismayed");
          else if (next === "cpu") setMood("pleased");
          else setMood("main");
          if (next === "player") say("player_ahead");
          else if (next === "cpu") say("cpu_ahead");
        }
      },
      end(result) {
        if (ended) return;
        ended = true;
        if (running && running.stop) running.stop();
        running = null;
        // The music stops and the jingle plays: "win" is the player's win, "lose" is the CPU's.
        stopMusic();
        if (result === "win" || result === "lose") ctx.sfx(result);
        // The CPU's line is the opposite of the result: "win" is their win, "lose" is theirs to lose.
        const cpuLine = result === "win" ? say("lose") : result === "lose" ? say("win") : "";
        endTitle.textContent = result === "win" ? "You win!" : result === "lose" ? `${data.cpu.name} wins` : "A draw";
        endLine.textContent = cpuLine || "";
        endScore.textContent = `${playerName} ${score.player} · ${data.cpu.name} ${score.cpu}`;
        setMood(result === "win" ? "dismayed" : result === "lose" ? "pleased" : "main");
        end.hidden = false;
        area.setAttribute("inert", "");
        (!again.hidden ? again : !choose.hidden ? choose : null)?.focus({ preventScroll: true });
        // Once per game (end() returns early after the first): the page's result, from the player's side.
        if (options.onEnd) options.onEnd(result, { player: score.player, cpu: score.cpu });
      },
      random: rng,
    };

    function play() {
      if (seed != null) {
        rng = seeded(seed);
        lineRng = seeded((seed ^ 0x5bd1e995) >>> 0);
        ctx.random = rng;
      }
      ended = false;
      score = { player: 0, cpu: 0 };
      lead = "tie";
      lastLine = "";
      paintScore();
      setMood("main");
      bubble.textContent = "";
      area.removeAttribute("inert");
      area.replaceChildren();
      end.hidden = true;
      head.querySelector(".minigame-status").textContent = "";
      ctx.say("start");
      const sound = audio();
      if (sound && sound.start) sound.start(data.game);
      running = game.play(ctx) || null;
    }

    function stopMusic() {
      const sound = audio();
      if (sound && sound.stop) sound.stop();
    }

    function stop() {
      if (running && running.stop) running.stop();
      running = null;
      stopMusic();
      root.replaceChildren();
    }

    again.addEventListener("click", () => {
      if (running && running.stop) running.stop();
      running = null;
      play();
    });
    choose.addEventListener("click", () => {
      stop();
      if (options.onChoose) options.onChoose();
    });

    play();
    return { stop, restart: () => { if (running && running.stop) running.stop(); running = null; play(); } };
  }

  window.MinigameShell = { start, seeded, portraitSrc };
})();
