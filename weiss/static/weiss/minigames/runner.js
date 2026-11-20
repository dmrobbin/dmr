/* Runner (docs/minigames-plan.md, "Round 2 changes"): an auto-runner in the spirit of Temple Run. The character runs on its
   own. Space or Up jumps, Down slides, and touch has jump and slide buttons. Obstacles and gaps come from the right: a
   level-0 card is a coin (points), level 1 and up are obstacles (low blocks to jump, high bars to slide under, tall
   blocks to jump over), and a climax is a shield that takes one hit. Three hits end the run; the CPU's target score is
   what to beat. The run ends only on the third hit, and the result is decided then: at or above the target wins. The
   course has no end: it gets faster with time and distance. Registers in window.MinigameGames and is started by the
   shell (shell.js), which gives the ctx: area, cards, cpu, difficulty, random, say, score, status and end. Its stop() is
   safe to call again. */
(() => {
  window.MinigameGames = window.MinigameGames || {};

  const TUNING = {
    easy: { target: 25, speed: 200, gap: 300 },
    normal: { target: 35, speed: 240, gap: 250 },
    hard: { target: 40, speed: 280, gap: 210 },
  };
  const W = 480; // the course, in its own units (the canvas scales to fit)
  const H = 240;
  const GROUND = H - 46; // the ground's top, in canvas units
  const PLAYER_X = 90;
  const GRAVITY = 1800;
  const JUMP_SPEED = 640;
  const JUMP_BUFFER = 0.14; // a jump pressed just before landing still counts
  const COYOTE = 0.08; // a jump just after running off a ledge still counts
  const SLIDE_MIN = 0.35; // a slide lasts at least this long
  const HITS_ALLOWED = 3;
  const INVULNERABLE = 1.2; // after a hit
  const COIN_POINTS = 10;
  const SAY_GAP = 4; // seconds between a coin's line, so they don't pile up
  const DPR = Math.min(2, window.devicePixelRatio || 1);
  // Sound (minigames/audio.js), if it's there: a short effect, or nothing.
  const sfx = (name) => { if (window.MinigameAudio) window.MinigameAudio.sfx(name); };

  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const isClimax = (card) => String(card.type || "").toLowerCase() === "climax";
  const levelOf = (card) => clamp(Number(card.level) || 0, 0, 3);

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function startRunner(ctx) {
    const rnd = ctx.random;
    const tune = TUNING[ctx.difficulty] || TUNING.normal;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pool = (ctx.cards || []).filter(Boolean);
    if (!pool.length) {
      ctx.status("No cards to run with.");
      ctx.end("draw");
      return null;
    }

    // ---- The page: the canvas and the touch buttons ----
    const board = el("div", "run-board");
    const canvas = el("canvas", "run-canvas");
    canvas.width = W * DPR;
    canvas.height = H * DPR;
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Runner. Space or Up to jump, Down to slide, P to pause.");
    const g = canvas.getContext("2d");
    g.setTransform(DPR, 0, 0, DPR, 0, 0);

    const touch = el("div", "run-touch");
    const touching = { jump: false, slide: false };
    const button = (label, aria) => {
      const node = el("button", "run-key", label);
      node.type = "button";
      node.setAttribute("aria-label", aria);
      return node;
    };
    const jumpButton = button("Jump", "Jump");
    const slideButton = button("Slide", "Slide");
    const pauseButton = button("Pause", "Pause");
    pauseButton.setAttribute("aria-pressed", "false");
    jumpButton.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      touching.jump = true;
      state.jumpBuffer = JUMP_BUFFER;
    });
    for (const type of ["pointerup", "pointercancel", "pointerleave"]) {
      jumpButton.addEventListener(type, () => { touching.jump = false; });
    }
    slideButton.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      touching.slide = true;
    });
    for (const type of ["pointerup", "pointercancel", "pointerleave"]) {
      slideButton.addEventListener(type, () => { touching.slide = false; });
    }
    pauseButton.addEventListener("click", () => togglePause());
    touch.append(jumpButton, slideButton, pauseButton);
    board.append(canvas, touch, el("p", "run-hint small", "Space or Up to jump · Down to slide · P to pause"));
    ctx.area.append(board);

    // ---- The pictures: each card's art, loaded once ----
    const images = new Map();
    for (const card of pool) {
      if (card.image && !images.has(card.image)) {
        const img = new Image();
        img.src = card.image;
        images.set(card.image, img);
      }
    }

    // ---- The state ----
    const state = {
      distance: 0, altitude: 0, vy: 0, jumpBuffer: 0, coyote: 0, slideTimer: 0, slideHeld: false, sliding: false,
      hits: 0, shield: false, coins: 0, score: 0, shownScore: -1, invulnerable: 0, time: 0,
      paused: false, over: false, objects: [], particles: [], nextAt: W, lastSay: -SAY_GAP, lastGap: false,
    };
    const stars = Array.from({ length: 30 }, () => ({ x: rnd() * W, y: rnd() * (GROUND - 30), s: 0.5 + rnd(), v: 0.2 + rnd() * 0.5 }));
    const hills = Array.from({ length: 6 }, (_, i) => ({ x: i * 120 + rnd() * 60, h: 30 + rnd() * 50 }));

    // The run gets harder on its own: faster with the distance covered, and with the time run, up to a limit.
    const speed = () => tune.speed + Math.min(180, state.distance / 35) + Math.min(60, state.time);

    let shownStatus = "";
    let wasSliding = false; // for the slide sound: once when it starts
    function status() {
      const text = `${Math.floor(state.distance / 10)} m · ${"♥".repeat(HITS_ALLOWED - state.hits)}${state.shield ? " · shield" : ""}`;
      if (text === shownStatus) return; // only when it changes: this runs every frame
      shownStatus = text;
      ctx.status(text);
    }

    // Points come from coins only: the distance covered scores nothing on its own.
    function points() {
      return state.coins * COIN_POINTS;
    }

    function reportScore() {
      const now = points();
      if (now === state.shownScore) return;
      state.shownScore = now;
      state.score = now;
      ctx.score(now, tune.target); // the CPU's number is its target: passing it is the lead changing
    }

    function burst(x, y, count, color) {
      const n = reduced ? Math.ceil(count / 3) : count;
      for (let i = 0; i < n && state.particles.length < 120; i++) {
        const angle = rnd() * Math.PI * 2;
        const v = (0.5 + rnd()) * 120;
        state.particles.push({ x, y, vx: Math.cos(angle) * v, vy: Math.sin(angle) * v, life: 0.4 + rnd() * 0.4, color });
      }
    }

    function finish() {
      if (state.over) return;
      state.over = true;
      const result = points() >= tune.target ? "win" : "lose";
      sfx(result);
      ctx.end(result); // the shell says the CPU's line and calls stop()
    }

    // A hit: the shield takes it once, otherwise it counts, and three of them end the run.
    function takeHit(x, y) {
      if (state.over || state.invulnerable > 0) return;
      if (state.shield) {
        state.shield = false;
        sfx("shield");
        burst(x, y, 12, "#8ff3ff");
        status();
        return;
      }
      state.hits += 1;
      state.invulnerable = INVULNERABLE;
      sfx("hit");
      burst(x, y, 16, "#ff8a7a");
      ctx.say("player_bad");
      if (state.hits >= HITS_ALLOWED) {
        finish();
        return;
      }
      status();
    }

    function collectCoin(obj) {
      obj.taken = true;
      sfx("pickup");
      state.coins += 1;
      burst(PLAYER_X, GROUND - state.altitude - 20, 6, "#ffd36b");
      if (state.time - state.lastSay >= SAY_GAP) {
        state.lastSay = state.time;
        ctx.say("player_good");
      }
    }

    // ---- The course: objects come from the right, one per stretch of ground ----

    function spawnObject(at) {
      const card = pool[Math.floor(rnd() * pool.length)];
      let kind;
      if (!state.lastGap && rnd() < 0.1) kind = "gap";
      else if (isClimax(card)) kind = "shield";
      else if (levelOf(card) === 0) kind = "coin";
      else kind = ["low", "high", "tall"][levelOf(card) - 1];
      const obj = { kind, at, card, taken: false, w: 30, lo: 0, hi: 34 };
      if (kind === "coin") Object.assign(obj, { w: 22, lo: rnd() < 0.5 ? 0 : 40, hi: 0 });
      if (kind === "shield") Object.assign(obj, { w: 22, lo: 40, hi: 0 });
      if (kind === "high") Object.assign(obj, { w: 40, lo: 30, hi: 60 });
      if (kind === "tall") Object.assign(obj, { w: 30, lo: 0, hi: 70 });
      if (kind === "gap") Object.assign(obj, { w: 70, lo: 0, hi: 0 });
      if (kind === "coin" || kind === "shield") obj.hi = obj.lo + 22;
      state.lastGap = kind === "gap";
      state.objects.push(obj);
    }

    // Each object's place on screen: the player stays put, and the course comes to them.
    const screenX = (obj) => PLAYER_X + (obj.at - state.distance);

    function overGap() {
      for (const obj of state.objects) {
        if (obj.kind !== "gap") continue;
        if (Math.abs(screenX(obj) - PLAYER_X) < obj.w / 2) return true;
      }
      return false;
    }

    // ---- One step of the game, dt seconds on ----

    function update(dt) {
      state.time += dt;
      for (const star of stars) {
        star.x -= star.v * speed() * dt * 0.1;
        if (star.x < 0) star.x += W;
      }

      // Input: a jump is buffered a moment, and a slide holds while Down is down (or for a short while).
      state.jumpBuffer -= dt; // set by a press (keyboard or touch), once
      const slideHeld = state.slideHeld || touching.slide;
      if (slideHeld && state.altitude <= 0) state.slideTimer = SLIDE_MIN;
      state.slideTimer -= dt;

      const gap = overGap();
      const onGround = state.altitude <= 0 && !gap;
      state.coyote = onGround ? COYOTE : state.coyote - dt;
      if (state.jumpBuffer > 0 && (onGround || state.coyote > 0)) {
        state.vy = JUMP_SPEED;
        sfx("jump");
        state.jumpBuffer = 0;
        state.coyote = 0;
      }
      state.sliding = onGround && (slideHeld || state.slideTimer > 0);
      if (state.sliding && !wasSliding) sfx("slide");
      wasSliding = state.sliding;

      // Gravity. Over a gap there's nothing under the player: they fall, and a long fall is a hit.
      state.vy -= GRAVITY * dt;
      state.altitude += state.vy * dt;
      if (state.altitude <= 0 && !gap) {
        state.altitude = 0;
        state.vy = 0;
      }
      if (state.altitude < -50) {
        takeHit(PLAYER_X, GROUND);
        state.altitude = 0;
        state.vy = 0;
      }
      state.invulnerable -= dt;

      // The course moves on.
      const step = speed() * dt;
      state.distance += step;
      while (state.nextAt < state.distance + W + 40) {
        spawnObject(state.nextAt);
        state.nextAt += tune.gap * (0.8 + rnd() * 0.5) * (state.lastGap ? 1.2 : 1);
      }

      // Things the player meets: coins, shields, obstacles and the gaps themselves.
      const playerH = state.sliding ? 22 : 44;
      for (const obj of state.objects) {
        if (obj.taken || obj.kind === "gap") continue;
        const x = screenX(obj);
        if (Math.abs(x - PLAYER_X) >= obj.w / 2 + 12) continue;
        const bottom = state.altitude;
        const top = state.altitude + playerH;
        if (obj.kind === "coin") {
          if (bottom < obj.hi + 16 && top > obj.lo - 4) collectCoin(obj);
        } else if (obj.kind === "shield") {
          if (bottom < obj.hi + 16 && top > obj.lo - 4) {
            obj.taken = true;
            state.shield = true;
            sfx("shield");
            status();
          }
        } else if (bottom < obj.hi && top > obj.lo) {
          obj.taken = true;
          takeHit(x, GROUND - obj.hi / 2);
        }
      }
      state.objects = state.objects.filter((obj) => !obj.taken && screenX(obj) > -60);

      for (const p of state.particles) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.life -= dt;
      }
      state.particles = state.particles.filter((p) => p.life > 0);

      reportScore();
      status();
    }

    // ---- Drawing ----

    function drawArt(card, x, y, w, h) {
      const img = card.image ? images.get(card.image) : null;
      if (img && img.complete && img.naturalWidth > 0) {
        g.drawImage(img, x, y, w, h);
        return;
      }
      g.fillStyle = "#1f2a4a";
      g.fillRect(x, y, w, h);
      g.fillStyle = "#f3efe7";
      g.font = "9px sans-serif";
      g.textAlign = "center";
      g.fillText(String(card.name || "").slice(0, 8), x + w / 2, y + h / 2 + 3);
    }

    function draw() {
      const sky = g.createLinearGradient(0, 0, 0, GROUND);
      sky.addColorStop(0, "#1b2347");
      sky.addColorStop(1, "#3a2a58");
      g.fillStyle = sky;
      g.fillRect(0, 0, W, H);
      g.fillStyle = "#cfd8ff";
      for (const star of stars) g.fillRect(star.x, star.y, star.s, star.s);
      g.fillStyle = "#2a2146";
      for (const hill of hills) {
        const x = ((hill.x - state.distance * 0.2) % (W + 120) + W + 120) % (W + 120) - 60;
        g.beginPath();
        g.ellipse(x, GROUND, 90, hill.h, 0, Math.PI, 0);
        g.fill();
      }

      g.fillStyle = "#4a3a2a";
      g.fillRect(0, GROUND, W, H - GROUND);
      g.fillStyle = "#7a6248";
      g.fillRect(0, GROUND, W, 4);

      // Gaps are holes in the ground, drawn over it.
      for (const obj of state.objects) {
        if (obj.kind !== "gap") continue;
        const x = screenX(obj);
        g.fillStyle = "#05060c";
        g.fillRect(x - obj.w / 2, GROUND, obj.w, H - GROUND);
      }

      g.textAlign = "center";
      for (const obj of state.objects) {
        if (obj.kind === "gap") continue;
        const x = screenX(obj);
        if (x < -40 || x > W + 40) continue;
        if (obj.kind === "coin") {
          g.fillStyle = "#ffd36b";
          g.beginPath();
          g.arc(x, GROUND - obj.lo - 11, 13, 0, Math.PI * 2);
          g.fill();
          drawArt(obj.card, x - 9, GROUND - obj.lo - 20, 18, 22);
        } else if (obj.kind === "shield") {
          g.strokeStyle = "#8ff3ff";
          g.lineWidth = 3;
          g.beginPath();
          g.arc(x, GROUND - obj.lo - 11, 13, 0, Math.PI * 2);
          g.stroke();
          drawArt(obj.card, x - 9, GROUND - obj.lo - 20, 18, 22);
        } else {
          const top = GROUND - obj.hi;
          drawArt(obj.card, x - obj.w / 2, top, obj.w, obj.hi - obj.lo || obj.hi);
          if (obj.kind === "high") {
            g.fillStyle = "#ff6b9a";
            g.fillRect(x - obj.w / 2 - 2, top - 2, obj.w + 4, 3);
          }
        }
      }

      // The player: a little runner, flat when sliding, legs moving while on the ground.
      const blink = state.invulnerable > 0 && Math.floor(state.time * 12) % 2 === 0;
      if (!blink) {
        const lift = state.altitude;
        const bodyTop = GROUND - lift - (state.sliding ? 22 : 44);
        const bodyH = state.sliding ? 22 : 44;
        g.fillStyle = "#8fd0ff";
        g.fillRect(PLAYER_X - 10, bodyTop, 20, bodyH);
        g.fillStyle = "#f3efe7";
        if (!state.sliding) {
          g.beginPath();
          g.arc(PLAYER_X, bodyTop - 6, 6, 0, Math.PI * 2);
          g.fill();
          const stride = state.altitude <= 0 ? Math.sin(state.distance / 14) * 6 : 0;
          g.fillStyle = "#8fd0ff";
          g.fillRect(PLAYER_X - 8 + stride, GROUND - lift - 4, 6, 6);
          g.fillRect(PLAYER_X + 2 - stride, GROUND - lift - 4, 6, 6);
        }
        if (state.shield) {
          g.strokeStyle = "rgba(143, 243, 255, 0.85)";
          g.lineWidth = 2;
          g.beginPath();
          g.arc(PLAYER_X, GROUND - lift - bodyH / 2, 30, 0, Math.PI * 2);
          g.stroke();
        }
      }

      for (const p of state.particles) {
        g.globalAlpha = Math.max(0, p.life);
        g.fillStyle = p.color;
        g.fillRect(p.x - 1.5, p.y - 1.5, 3, 3);
      }
      g.globalAlpha = 1;

      g.textAlign = "left";
      g.font = "bold 13px sans-serif";
      g.fillStyle = "#f3efe7";
      g.fillText(`${Math.floor(state.distance / 10)} m · ${points()} points`, 8, 18);

      if (state.paused) {
        g.fillStyle = "rgba(0,0,0,0.55)";
        g.fillRect(0, 0, W, H);
        g.textAlign = "center";
        g.fillStyle = "#f3efe7";
        g.font = "bold 22px sans-serif";
        g.fillText("Paused", W / 2, H / 2);
        g.font = "13px sans-serif";
        g.fillText("Press P or Pause to carry on", W / 2, H / 2 + 26);
      }
    }

    // ---- Pausing: by P, the Pause button, leaving the page, or the tab being hidden ----

    function togglePause() {
      if (state.over) return;
      state.paused = !state.paused;
      pauseButton.textContent = state.paused ? "Resume" : "Pause";
      pauseButton.setAttribute("aria-pressed", String(state.paused));
    }

    function pauseIfAway() {
      if (!state.paused && !state.over) togglePause();
    }

    // ---- Input ----

    function onKeyDown(event) {
      if (event.code === "KeyP") {
        event.preventDefault();
        togglePause();
        return;
      }
      if (event.code === "Space" || event.code === "ArrowUp") {
        event.preventDefault(); // the jump plays the game, not the page
        if (!event.repeat) state.jumpBuffer = JUMP_BUFFER;
      } else if (event.code === "ArrowDown") {
        event.preventDefault();
        state.slideHeld = true;
      }
    }

    function onKeyUp(event) {
      if (event.code === "ArrowDown") state.slideHeld = false;
    }

    function onVisibility() {
      if (document.hidden) pauseIfAway();
    }

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("keyup", onKeyUp);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", pauseIfAway);

    // ---- The loop, and stopping ----

    let raf = 0;
    let last = 0;
    let stopped = false;

    function frame(now) {
      if (stopped) return;
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      if (!state.paused && !state.over) update(dt);
      draw();
      raf = requestAnimationFrame(frame);
    }

    // The shell calls this when the run ends, when playing again, and when choosing another game. The last picture stays
    // on the area. Safe to call more than once.
    function stop() {
      if (stopped) return;
      stopped = true;
      cancelAnimationFrame(raf);
      if (window.MinigameAudio) window.MinigameAudio.stop();
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keyup", onKeyUp);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", pauseIfAway);
    }

    if (window.MinigameAudio) window.MinigameAudio.start("runner");
    status();
    reportScore();
    raf = requestAnimationFrame(frame);
    return { stop };
  }

  window.MinigameGames.runner = {
    title: "Runner",
    about: "The card runs on its own. Jump the low cards, slide under the high ones, and collect the coin cards. A climax is a shield for one hit. Three hits and it's over.",
    play: startRunner,
  };
})();
