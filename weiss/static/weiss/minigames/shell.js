/* The minigames' shared frame (docs/minigames-plan.md, "The frame"; docs/minigames-polish-plan.md, "The contract between the
   frame and the games"). MinigameShell.start(root, data, options) builds the stage into root: a header with the title, the
   round pill and one scoreboard; the CPU's corner; the game's area (ctx.area), sized to fit the space with no scrolling; a
   start card (the title, the game's rule and Start), a 3-2-1 countdown, and the results screen. Then it calls the game's
   play(ctx) and the game returns { stop() }. A game registers itself in MinigameGames. */
(() => {
  // Keep any registrations already made: a game script may load before this one.
  const games = window.MinigameGames || {};
  window.MinigameGames = games;

  const DEFAULT_SLEEVE = "var(--sleeve-classic)"; // the duel's default sleeve (site.css), when the player has none
  const MIN_STAGE_PX = 360; // the stage never gets shorter than this (a very short window scrolls instead)
  const AREA_MIN_SHARE = 0.6; // the game area is at least this share of the screen's height, so a game fits (the page scrolls)
  const COUNT_UP_MS = 700; // the results screen's score counts up in this long

  const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // The shared audio module (audio.js, docs/minigames-plan.md "Round 3"). Until it loads, sound calls do nothing.
  const audio = () => window.MinigameAudio || null;

  // The shared effects (fx.js): burst, shake and pop. Until it loads, the effects do nothing.
  const NO_FX = { burst() {}, shake() {}, pop() {} };

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

  // A side's face: its picture, else its initial on a disc (the duel's crest, in the stage's colours).
  function face(src, name, className) {
    const initial = () => el("span", `${className} ${className}-initial`, String(name || "?").slice(0, 1).toUpperCase());
    if (!src) return initial();
    const img = el("img", className);
    img.alt = "";
    img.src = src;
    img.addEventListener("error", () => img.replaceWith(initial()), { once: true });
    return img;
  }

  // Counts a number up from 0 to `to` (instant with reduced motion).
  function countUp(node, to) {
    if (reducedMotion() || to === 0) {
      node.textContent = String(to);
      return;
    }
    const started = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - started) / COUNT_UP_MS);
      node.textContent = String(Math.round(to * t));
      if (t < 1 && node.isConnected) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  // A phone: the stage isn't squeezed into the window. Its game area is at least 60% of the screen, the page scrolls to it,
  // and Start brings it into view (see startButton below).
  const narrow = () => window.matchMedia("(max-width: 40rem)").matches;

  // The stage's height: the space left below it in the window (or the whole screen when it's full screen).
  function fitStage(section) {
    if (document.fullscreenElement === section) {
      section.style.height = `${window.innerHeight}px`;
      return;
    }
    if (narrow()) {
      section.style.height = ""; // the stylesheet sets its height on a phone: the area's minimum decides it
      return;
    }
    const height = window.visualViewport ? window.visualViewport.height : window.innerHeight;
    const top = Math.max(0, section.getBoundingClientRect().top);
    const fit = Math.max(MIN_STAGE_PX, height - top - 12);
    // The game area is at least 60% of the screen, whatever space is left: the page scrolls to the stage instead.
    const area = section.querySelector(".minigame-area");
    const chrome = area ? section.offsetHeight - area.offsetHeight : 0;
    section.style.height = `${Math.max(fit, Math.round(height * AREA_MIN_SHARE) + chrome)}px`;
  }

  // start(root, data, options): builds the stage into root and shows its start card. Returns { stop(), restart() }.
  // options: playerName, seed (a seeded game: the same deal each play, no "Play again"), onEnd(result, scores), onBack()
  // (the results screen's way out, with backLabel for its button) and onEnd's result is "win", "lose" or "draw".
  function start(root, data, options = {}) {
    const game = games[data.game];
    if (!game) throw new Error(`No minigame called "${data.game}".`);
    // With a seed (a co-op match, a world game), every play deals and plays the same game from it. Without one, as before:
    // a random deal once, and each play after it carries on from there.
    const seed = options.seed != null ? seedOf(options.seed) : null;
    let rng = seeded(seed != null ? seed : Math.floor(Math.random() * 1e9));
    // The CPU's lines have their own generator, so what they say (and when) can't change the game's deal.
    let lineRng = seeded(seed != null ? (seed ^ 0x5bd1e995) >>> 0 : Math.floor(Math.random() * 1e9));
    const player = data.player || { name: options.playerName || "You", picture: null, sleeve: "" };
    const cpu = data.cpu;
    let score = { player: 0, cpu: 0 };
    let lead = "tie";
    let lastLine = "";
    let running = null;
    let ended = false;
    let countdownTimer = 0;
    let countdownResolve = null;
    const teardown = [];

    root.replaceChildren();
    const section = el("section", "minigame");
    section.dataset.game = data.game;
    section.style.setProperty("--sleeve-me", player.sleeve || DEFAULT_SLEEVE);

    // ---- The header: the title, the round pill, one scoreboard, full screen ----
    const head = el("header", "minigame-head");
    const title = el("h2", "minigame-title", game.title || data.game);
    const pill = el("p", "minigame-pill", "");
    pill.hidden = true;
    pill.setAttribute("aria-live", "polite");
    const board = el("p", "minigame-scoreboard");
    board.setAttribute("aria-label", `Score: you ${0}, ${cpu.name} ${0}`);
    const youSide = el("span", "minigame-side minigame-side-you");
    const youNum = el("b", "minigame-num", "0");
    youSide.append(face(player.picture && player.picture.image, player.name, "minigame-mini"), el("span", "", "You "), youNum);
    const cpuSide = el("span", "minigame-side minigame-side-cpu");
    const cpuNum = el("b", "minigame-num", "0");
    const cpuLabel = el("span", "minigame-side-name", cpu.name);
    cpuLabel.title = cpu.name; // the full name, when a phone shows it cut short
    cpuSide.append(cpuNum, cpuLabel, face(portraitSrc(cpu), cpu.name, "minigame-mini"));
    board.append(youSide, el("span", "minigame-dash", "—"), cpuSide);
    // Full screen: an icon on a phone (the label is still its name, for screen readers); the words on a wider screen.
    const fullButton = el("button", "button-small secondary minigame-full");
    fullButton.type = "button";
    fullButton.setAttribute("aria-label", "Full screen");
    fullButton.append(el("span", "minigame-full-icon", "⛶"), el("span", "minigame-full-label", "Full screen"));
    fullButton.hidden = !section.requestFullscreen;
    head.append(title, pill, board, fullButton);

    // ---- The table: the CPU's corner, the game's area, and the layers over them ----
    const table = el("div", "minigame-table");
    const cpuBox = el("div", "minigame-cpu");
    const portrait = el("div", "minigame-portrait");
    const bubble = el("p", "minigame-bubble");
    bubble.setAttribute("aria-live", "polite");
    // The portrait, as the versus intro has it: the CPU's intro art whole when it has some, else its picture (which
    // changes with the mood), else its crest. Only a picture changes with the mood; art is shown as it is.
    const setPortrait = (mood) => {
      const current = portrait.firstElementChild;
      const next = portraitSrc(cpu, mood);
      if (current && current.classList.contains("minigame-picture") && current.tagName === "IMG" && next && current.getAttribute("src") !== next) {
        current.src = next;
      }
    };
    portrait.append(cpu.image ? artOf(cpu.image, cpu.name) : face(portraitSrc(cpu), cpu.name, "minigame-picture"));
    cpuBox.append(portrait, bubble);

    const area = el("div", "minigame-area");
    area.tabIndex = -1;
    const fxLayer = el("div", "minigame-fx");
    fxLayer.setAttribute("aria-hidden", "true");
    const countdown = el("p", "minigame-countdown", "");
    countdown.setAttribute("aria-hidden", "true");
    countdown.hidden = true;
    area.append(countdown);

    // The start card and the results screen share one layer over the table.
    const over = el("div", "minigame-over");
    const startCard = el("section", "minigame-card minigame-start-card");
    startCard.setAttribute("aria-label", "Start");
    const startTitle = el("h3", "minigame-card-title", game.title || data.game);
    const rule = el("p", "minigame-rule", game.rule || "");
    const startButton = el("button", "button-small minigame-start-go", "Start");
    startButton.type = "button";
    startCard.append(startTitle, rule, startButton);

    const endCard = el("section", "minigame-card minigame-end-card");
    endCard.hidden = true;
    const endTitle = el("h3", "minigame-card-title minigame-end-title", "");
    const endScore = el("p", "minigame-end-score", "");
    const endNumYou = el("b", "", "0");
    const endNumCpu = el("b", "", "0");
    endScore.append(endNumYou, el("span", "", " — "), endNumCpu);
    const endLine = el("p", "minigame-end-line", "");
    endLine.setAttribute("aria-live", "polite");
    const again = el("button", "button-small", "Play again");
    again.type = "button";
    const back = el("button", "button-small secondary", "Back");
    back.type = "button";
    // A seeded game (the infinite challenge, co-op, a world game) can't be replayed for the same deal, so there's no
    // "Play again" there. "Back" only where the page gives a way out.
    again.hidden = seed != null;
    back.hidden = !options.onBack;
    if (options.backLabel) back.textContent = options.backLabel;
    const endButtons = el("div", "minigame-end-buttons");
    endButtons.append(again, back);
    endCard.append(endTitle, endScore, endLine, endButtons);

    over.append(startCard, endCard);
    table.append(cpuBox, area, over);
    section.append(head, table, fxLayer);
    root.append(section);

    // Effects over the whole stage: ctx.fx takes page coordinates, and the layer is where they're drawn.
    const fx = window.MinigameFx ? window.MinigameFx.create(fxLayer) : NO_FX;

    // ---- Painting ----
    const paintScore = () => {
      youNum.textContent = String(score.player);
      cpuNum.textContent = String(score.cpu);
      board.setAttribute("aria-label", `Score: you ${score.player}, ${cpu.name} ${score.cpu}`);
    };

    const setMood = (mood) => setPortrait(mood);

    const say = (moment) => {
      const line = pickLine(data.lines, moment, lineRng, lastLine, player.name);
      if (!line) return;
      lastLine = line;
      bubble.textContent = line;
      bubble.classList.remove("minigame-bubble-on");
      void bubble.offsetWidth; // restart the bubble's little rise
      bubble.classList.add("minigame-bubble-on");
      return line;
    };

    const sfx = (name) => {
      const sound = audio();
      if (sound && sound.sfx) sound.sfx(name);
    };

    function stopMusic() {
      const sound = audio();
      if (sound && sound.stop) sound.stop();
    }

    // The 3-2-1 over the stage, then Go. Resolves when it's done; at once with reduced motion.
    function countdownFn() {
      if (reducedMotion() || ended) return Promise.resolve();
      return new Promise((resolve) => {
        countdownResolve = resolve;
        const steps = ["3", "2", "1", "Go!"];
        let i = 0;
        countdown.hidden = false;
        const tick = () => {
          countdown.textContent = steps[i];
          countdown.classList.remove("minigame-countdown-on");
          void countdown.offsetWidth;
          countdown.classList.add("minigame-countdown-on");
          i += 1;
          countdownTimer = setTimeout(() => {
            if (i < steps.length) return tick();
            countdown.hidden = true;
            countdownTimer = 0;
            countdownResolve = null;
            resolve();
          }, i < steps.length ? 700 : 500);
        };
        tick();
      });
    }

    const ctx = {
      area,
      cards: data.cards,
      cpu,
      player,
      difficulty: data.difficulty,
      random: rng,
      fx,
      say,
      sfx,
      countdown: countdownFn,
      status(text) {
        pill.textContent = text || "";
        pill.hidden = !text;
      },
      score(playerScore, cpuScore) {
        score = { player: playerScore, cpu: cpuScore };
        paintScore();
        const next = playerScore > cpuScore ? "player" : cpuScore > playerScore ? "cpu" : "tie";
        if (next !== lead) {
          lead = next;
          if (next === "player") setMood("dismayed");
          else if (next === "cpu") setMood("pleased");
          else setMood("main");
          if (next === "player") say("player_ahead");
          else if (next === "cpu") say("cpu_ahead");
        }
      },
      // result: "win", "lose" or "draw". extra.line: the game's own line for the results screen (its score, in words).
      end(result, extra = {}) {
        if (ended) return;
        ended = true;
        if (running && running.stop) running.stop();
        running = null;
        cancelCountdown();
        // The music stops and the jingle plays: "win" is the player's win, "lose" is the CPU's.
        stopMusic();
        if (result === "win" || result === "lose") sfx(result);
        // The CPU's line is the opposite of the result: "win" is their win, "lose" is theirs to lose.
        const cpuLine = result === "win" ? say("lose") : result === "lose" ? say("win") : "";
        endTitle.textContent = result === "win" ? "Victory" : result === "lose" ? "Defeat" : "Draw";
        endTitle.dataset.result = result;
        endLine.textContent = (extra && extra.line) || cpuLine || "";
        endNumYou.textContent = "0";
        endNumCpu.textContent = "0";
        countUp(endNumYou, score.player);
        countUp(endNumCpu, score.cpu);
        setMood(result === "win" ? "dismayed" : result === "lose" ? "pleased" : "main");
        startCard.hidden = true;
        endCard.hidden = false;
        over.hidden = false;
        area.setAttribute("inert", "");
        (!again.hidden ? again : !back.hidden ? back : null)?.focus({ preventScroll: true });
        // Once per game (end() returns early after the first): the page's result, from the player's side.
        if (options.onEnd) options.onEnd(result, { player: score.player, cpu: score.cpu });
      },
    };

    function cancelCountdown() {
      clearTimeout(countdownTimer);
      countdownTimer = 0;
      countdown.hidden = true;
      if (countdownResolve) {
        const resolve = countdownResolve;
        countdownResolve = null;
        resolve();
      }
    }

    // ---- Starting and playing ----
    // The start card first: the game is played when Start is pressed (begin).
    function showStartCard() {
      over.hidden = false;
      startCard.hidden = false;
      endCard.hidden = true;
      area.setAttribute("inert", "");
      status("");
      startButton.disabled = false;
      startButton.focus({ preventScroll: true });
    }

    function status(text) {
      ctx.status(text);
    }

    function begin() {
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
      over.hidden = true;
      startCard.hidden = true;
      endCard.hidden = true;
      area.removeAttribute("inert");
      area.replaceChildren(countdown);
      countdown.hidden = true;
      status("");
      ctx.say("start");
      const sound = audio();
      if (sound && sound.start) sound.start(data.game);
      running = game.play(ctx) || null;
    }

    function stop() {
      if (running && running.stop) running.stop();
      running = null;
      cancelCountdown();
      stopMusic();
      for (const undo of teardown.splice(0)) undo();
      root.replaceChildren();
    }

    startButton.addEventListener("click", () => {
      startButton.disabled = true;
      // The stage may start below the fold (the page scrolls to it, as its area is most of the screen): bring it into view.
      section.scrollIntoView({ block: "nearest", behavior: reducedMotion() ? "auto" : "smooth" });
      begin();
    });
    again.addEventListener("click", () => {
      if (running && running.stop) running.stop();
      running = null;
      cancelCountdown();
      showStartCard();
    });
    back.addEventListener("click", () => {
      if (options.onBack) options.onBack();
    });

    // ---- Full screen, and the stage's size ----
    const onFullscreen = () => {
      fullButton.querySelector(".minigame-full-label").textContent = document.fullscreenElement === section ? "Exit full screen" : "Full screen";
      fitStage(section);
    };
    fullButton.addEventListener("click", () => {
      // The label says what the button does now (the icon is the same either way).
      fullButton.querySelector(".minigame-full-label").textContent = document.fullscreenElement === section ? "Exit full screen" : "Full screen";
      if (document.fullscreenElement === section) document.exitFullscreen?.();
      else section.requestFullscreen?.({ navigationUI: "hide" })?.catch(() => {});
    });
    document.addEventListener("fullscreenchange", onFullscreen);
    teardown.push(() => document.removeEventListener("fullscreenchange", onFullscreen));
    const onWindowResize = () => fitStage(section);
    window.addEventListener("resize", onWindowResize);
    teardown.push(() => window.removeEventListener("resize", onWindowResize));
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", onWindowResize);
      teardown.push(() => window.visualViewport.removeEventListener("resize", onWindowResize));
    }
    // A game reads its size from ctx.area and listens for "resize" on it: the frame dispatches them when the area changes.
    const sizes = new ResizeObserver(() => area.dispatchEvent(new Event("resize")));
    sizes.observe(area);
    teardown.push(() => sizes.disconnect());

    paintScore();
    fitStage(section);
    showStartCard();

    return {
      stop,
      restart: () => {
        if (running && running.stop) running.stop();
        running = null;
        cancelCountdown();
        begin();
      },
    };
  }

  // The CPU's intro art, whole (object-fit: contain): as the versus intro shows it.
  function artOf(src, name) {
    const img = el("img", "minigame-art");
    img.alt = "";
    img.src = src;
    img.addEventListener("error", () => img.replaceWith(face(null, name, "minigame-picture")), { once: true });
    return img;
  }

  window.MinigameShell = { start, seeded, portraitSrc };
})();
