/* Runner (docs/minigames-plan.md, "Round 2 changes"; its look: docs/minigames-polish-plan.md): an auto-runner in the
   spirit of Temple Run. The character runs on its own. Space or Up jumps, Down slides, and touch has jump and slide
   buttons. Obstacles and gaps come from the right: a level-0 card is a coin (points), level 1 and up are obstacles (low
   cards on easels to jump, high banners to slide under, tall cards on posts to jump over), and a climax is a shield that
   takes one hit. Three hits end the run; the CPU's target score is what to beat. The run ends only on the third hit, and
   the result is decided then: at or above the target wins. The course has no end: it gets faster with time and distance.
   Registers in window.MinigameGames and is started by the shell (shell.js), which gives the ctx: area, cards, cpu,
   difficulty, random, say, score, status and end, and in the new frame player and countdown. Its stop() is safe to call
   again.

   The course is played in its own units, W by H (16:9), with the ground GROUND from the top; everything that matters to
   play (jumps, obstacles' heights, the gap) is measured from the ground, and the canvas scales the whole picture to fit
   the space it's given. Drawing is all in code: no images but the cards' own art and the player's picture. */
(() => {
  window.MinigameGames = window.MinigameGames || {};

  const TUNING = {
    easy: { target: 25, speed: 200, gap: 300 },
    normal: { target: 35, speed: 240, gap: 250 },
    hard: { target: 40, speed: 280, gap: 210 },
  };
  const W = 480; // the course, in its own units (the canvas scales to fit)
  const H = 270;
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

  // The palette: a moonlit evening over the town.
  const C = {
    skyTop: "#0b1030", skyMid: "#2a2158", skyLow: "#6a3466", moon: "#f7eed3", star: "#dfe6ff",
    peaks: ["#3b2f6b", "#1f1940"], town: "#17122e", window: "#ffd98a", hedge: "#0e0b1d",
    grass: "#3f7f4c", grassLit: "#79c07a", earth: ["#4b3424", "#24180f"], stone: "rgba(255, 236, 210, 0.07)",
    pit: "#05040b", gold: "#d4af37", goldLit: "#f4d77a", goldDark: "#9a7a1d", wood: "#6b4a2d", woodLit: "#8d6a43",
    outfit: "#2c3c6c", outfitLit: "#4560a0", skin: "#f1c9a5", hair: "#3b2b4f", shield: "#8ff3ff", hurt: "#ff8a7a",
    banner: "#c2385c", text: "#f6f1e7",
  };
  const DISPLAY_FONT = '"Cinzel", Georgia, serif';
  const UI_FONT = 'system-ui, "Segoe UI", sans-serif';

  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const isClimax = (card) => String(card.type || "").toLowerCase() === "climax";
  const levelOf = (card) => clamp(Number(card.level) || 0, 0, 3);

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  // ---- The backdrop's shapes, made once per run (seeded) as paths in course units, each a tile that repeats ----

  // Mountains along the horizon: a jagged ridge, one tile of width `w`, that starts and ends at the same height.
  function ridgePath(rnd, w) {
    const path = new Path2D();
    const base = GROUND - 30;
    path.moveTo(0, GROUND);
    let y = base - 40;
    path.lineTo(0, y);
    const steps = 16;
    for (let i = 1; i < steps; i++) {
      y = clamp(y + (rnd() - 0.5) * 46, base - 92, base - 18);
      path.lineTo((i / steps) * w, y);
    }
    path.lineTo(w, base - 40);
    path.lineTo(w, GROUND);
    path.closePath();
    return path;
  }

  // The town's rooftops: houses, a few with peaked roofs, one tower; and the lit windows, as a second path.
  function townPaths(rnd, w) {
    const roofs = new Path2D();
    const windows = new Path2D();
    let x = 0;
    while (x < w) {
      const bw = 22 + rnd() * 34;
      const bh = 26 + rnd() * 52;
      const top = GROUND - bh;
      roofs.rect(x, top, bw, bh + 1);
      if (rnd() < 0.45) { // a peaked roof
        roofs.moveTo(x - 2, top);
        roofs.lineTo(x + bw / 2, top - 8 - rnd() * 10);
        roofs.lineTo(x + bw + 2, top);
        roofs.closePath();
      } else if (rnd() < 0.2) { // a tower with a spire
        const tw = 8;
        roofs.rect(x + bw / 2 - tw / 2, top - 22, tw, 23);
        roofs.moveTo(x + bw / 2 - tw / 2 - 2, top - 22);
        roofs.lineTo(x + bw / 2, top - 36);
        roofs.lineTo(x + bw / 2 + tw / 2 + 2, top - 22);
        roofs.closePath();
      }
      for (let wy = top + 6; wy < GROUND - 8; wy += 9) {
        for (let wx = x + 4; wx < x + bw - 6; wx += 7) {
          if (rnd() < 0.3) windows.rect(wx, wy, 3, 4);
        }
      }
      x += bw + 2 + rnd() * 6;
    }
    return { roofs, windows };
  }

  // Bushes and pines along the near edge of the field.
  function hedgePath(rnd, w) {
    const path = new Path2D();
    let x = 0;
    while (x < w) {
      if (rnd() < 0.35) { // a pine
        const h = 16 + rnd() * 16;
        path.moveTo(x, GROUND + 1);
        path.lineTo(x + 7, GROUND - h);
        path.lineTo(x + 14, GROUND + 1);
        path.closePath();
        x += 14;
      } else { // a bush
        const r = 5 + rnd() * 7;
        path.moveTo(x + r * 2, GROUND + 1);
        path.arc(x + r, GROUND + 1, r, 0, Math.PI, true);
        path.closePath();
        x += r * 2 - 2;
      }
      x += rnd() * 26;
    }
    return path;
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

    // ---- The page: the screen (the canvas, with a pause button on it), the touch buttons, and a hint ----
    const board = el("div", "run-board");
    const screen = el("div", "run-screen");
    const canvas = el("canvas", "run-canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Runner. Space or Up to jump, Down to slide, P to pause.");
    const g = canvas.getContext("2d");

    const touch = el("div", "run-touch");
    const touching = { jump: false, slide: false };
    const button = (className, label, aria) => {
      const node = el("button", className, label);
      node.type = "button";
      node.setAttribute("aria-label", aria);
      return node;
    };
    const jumpButton = button("run-key run-key-jump", "↑ Jump", "Jump");
    const slideButton = button("run-key run-key-slide", "↓ Slide", "Slide");
    const pauseButton = button("run-pause", "❚❚", "Pause");
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
    touch.append(jumpButton, slideButton);
    screen.append(canvas, pauseButton);
    // For screen readers, what the canvas shows that matters: hits left and the shield (the words are Barry's).
    const spoken = el("p", "sr-only");
    spoken.setAttribute("aria-live", "polite");
    const hint = el("p", "run-hint small", "Space or Up to jump · Down to slide · P to pause");
    board.append(screen, touch, hint, spoken);
    ctx.area.append(board);

    // ---- Fitting the space: the screen is as wide as it can be at 16:9 in the space it's given ----
    let scale = 1; // canvas units per course unit, before the device's pixel ratio
    function fit() {
      // The area's inner size: its client size less its padding (the board sits inside the padding).
      const box = getComputedStyle(ctx.area);
      const padX = (parseFloat(box.paddingLeft) || 0) + (parseFloat(box.paddingRight) || 0);
      const padY = (parseFloat(box.paddingTop) || 0) + (parseFloat(box.paddingBottom) || 0) + 4; // and the screen's border
      const areaW = (ctx.area.clientWidth || W) - padX;
      const areaH = ctx.area.clientHeight - padY;
      const below = (touch.offsetParent ? touch.offsetHeight : 0) + (hint.offsetParent ? hint.offsetHeight : 0) + 20;
      let width = areaW;
      // The frame gives the area a definite height. A tiny one (under 120) is a space still sizing itself to us, as an
      // older frame's does: going by it would shrink the screen to nothing, so then the width alone decides.
      if (areaH >= 120) width = Math.min(width, ((areaH - below) * W) / H);
      width = Math.max(240, Math.floor(width));
      screen.style.width = `${width}px`;
      const pixelsW = Math.round(width * DPR);
      const pixelsH = Math.round((width * H / W) * DPR);
      if (canvas.width !== pixelsW || canvas.height !== pixelsH) {
        canvas.width = pixelsW;
        canvas.height = pixelsH;
      }
      scale = width / W;
    }
    const sizer = typeof ResizeObserver === "function" ? new ResizeObserver(() => fit()) : null;
    if (sizer) sizer.observe(ctx.area);
    ctx.area.addEventListener("resize", fit); // the frame's own signal, when it resizes the stage
    window.addEventListener("resize", fit);
    fit();

    // ---- The pictures: each card's art, and the player's, loaded once ----
    const images = new Map();
    const load = (src) => {
      if (!src) return null;
      if (!images.has(src)) {
        const img = new Image();
        img.src = src;
        images.set(src, img);
      }
      return images.get(src);
    };
    for (const card of pool) load(card.image);
    const ready = (img) => img && img.complete && img.naturalWidth > 0;
    const picture = ctx.player && ctx.player.picture && ctx.player.picture.image ? ctx.player.picture : null;
    const face = picture ? load(picture.image) : null;

    // ---- The backdrop: made once, from the run's seed ----
    const ridge = ridgePath(rnd, 480);
    const town = townPaths(rnd, 600);
    const hedge = hedgePath(rnd, 420);

    // ---- The state ----
    const state = {
      distance: 0, altitude: 0, vy: 0, jumpBuffer: 0, coyote: 0, slideTimer: 0, slideHeld: false, sliding: false,
      hits: 0, shield: false, coins: 0, score: 0, shownScore: -1, invulnerable: 0, time: 0,
      paused: false, over: false, objects: [], particles: [], nextAt: W, lastSay: -SAY_GAP, lastGap: false,
      started: !ctx.countdown, shake: 0, pops: [], dustClock: 0, wasAirborne: false, reached: false,
    };
    const stars = Array.from({ length: 46 }, () => ({ x: rnd() * W, y: rnd() * (GROUND - 70), s: 0.5 + rnd() * 1.1, v: 0.2 + rnd() * 0.5, phase: rnd() * 6.3 }));

    // The run gets harder on its own: faster with the distance covered, and with the time run, up to a limit.
    const speed = () => tune.speed + Math.min(180, state.distance / 35) + Math.min(60, state.time);

    let shownSpoken = "";
    function status() {
      const left = HITS_ALLOWED - state.hits;
      const text = `${left} ${left === 1 ? "hit" : "hits"} left${state.shield ? ". Shield" : ""}`;
      if (text === shownSpoken) return; // only when it changes: this runs every frame
      shownSpoken = text;
      spoken.textContent = text;
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
      if (!state.reached && now >= tune.target) {
        state.reached = true;
        pop(W / 2, 74, "Target reached!", { big: true, color: C.goldLit, life: 1.6 });
      }
    }

    function burst(x, y, count, color, spread = 120) {
      const n = reduced ? Math.ceil(count / 3) : count;
      for (let i = 0; i < n && state.particles.length < 160; i++) {
        const angle = rnd() * Math.PI * 2;
        const v = (0.5 + rnd()) * spread;
        state.particles.push({ x, y, vx: Math.cos(angle) * v, vy: Math.sin(angle) * v, life: 0.4 + rnd() * 0.4, color, size: 2 + rnd() * 2, drag: 0 });
      }
    }

    // A puff of dust from the runner's feet, drifting back with the ground.
    function dust(count, spread) {
      for (let i = 0; i < count && state.particles.length < 160; i++) {
        state.particles.push({ x: PLAYER_X - 4 + rnd() * 8, y: GROUND - 1, vx: -40 - rnd() * spread, vy: -10 - rnd() * 30, life: 0.35 + rnd() * 0.3,
          color: "rgba(214, 190, 160, 0.55)", size: 2.5 + rnd() * 2.5, drag: 1.5 });
      }
    }

    function pop(x, y, text, options = {}) {
      state.pops.push({ x, y, text, life: options.life || 0.8, total: options.life || 0.8, big: Boolean(options.big), color: options.color || C.goldLit });
    }

    function finish() {
      if (state.over) return;
      state.over = true;
      const result = points() >= tune.target ? "win" : "lose";
      sfx(result);
      // The results screen's line (Barry's words); a frame that doesn't take it shows its own.
      ctx.end(result, { line: `${points()} points in ${Math.floor(state.distance / 10)} m. Target: ${tune.target}.` });
    }

    // A hit: the shield takes it once, otherwise it counts, and three of them end the run.
    function takeHit(x, y) {
      if (state.over || state.invulnerable > 0) return;
      if (state.shield) {
        state.shield = false;
        sfx("shield");
        burst(x, y, 14, C.shield);
        status();
        return;
      }
      state.hits += 1;
      state.invulnerable = INVULNERABLE;
      state.shake = reduced ? 0 : 0.3;
      sfx("hit");
      burst(x, y, 18, C.hurt);
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
      burst(PLAYER_X, GROUND - state.altitude - 20, 8, C.goldLit, 90);
      pop(PLAYER_X + 6, GROUND - state.altitude - 52, `+${COIN_POINTS}`);
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
        if (!reduced) dust(5, 40);
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

      // The look of it: a landing puff, dust from running feet, sparks from a slide (none of it affects play).
      const airborne = state.altitude > 0;
      if (state.wasAirborne && !airborne && !reduced) dust(7, 60);
      state.wasAirborne = airborne;
      state.dustClock -= dt;
      if (!airborne && !gap && state.dustClock <= 0 && !reduced) {
        state.dustClock = state.sliding ? 0.03 : 0.09;
        dust(1, state.sliding ? 120 : 30);
      }
      state.shake = Math.max(0, state.shake - dt);

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
            burst(x, GROUND - obj.lo - 11, 10, C.shield, 80);
            pop(x, GROUND - obj.lo - 40, "Shield", { color: C.shield });
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
        if (p.drag) { p.vx *= 1 - p.drag * dt; p.vy *= 1 - p.drag * dt; }
        p.life -= dt;
      }
      state.particles = state.particles.filter((p) => p.life > 0);
      for (const p of state.pops) { p.y -= 26 * dt; p.life -= dt; }
      state.pops = state.pops.filter((p) => p.life > 0);

      reportScore();
      status();
    }

    // ---- Drawing: in course units, scaled to the canvas ----

    // A layer that repeats: `draw(x)` draws one tile with its left edge at x; tiles are laid side by side across the
    // screen, offset by the distance run times the layer's depth (far layers move slowly).
    function tiled(width, depth, draw) {
      const offset = ((state.distance * depth) % width + width) % width;
      for (let x = -offset; x < W; x += width) draw(x);
    }

    // A card's art in a frame, or its name on a plain card while the art loads.
    function drawCard(card, x, y, w, h, options = {}) {
      g.save();
      if (options.rotate) {
        g.translate(x + w / 2, y + h / 2);
        g.rotate(options.rotate);
        [w, h] = [h, w];
        x = -w / 2;
        y = -h / 2;
      }
      const img = card.image ? images.get(card.image) : null;
      g.fillStyle = options.frame || "#e9dcc0";
      g.fillRect(x - 1.5, y - 1.5, w + 3, h + 3);
      if (ready(img)) {
        g.drawImage(img, x, y, w, h);
      } else {
        g.fillStyle = "#1f2a4a";
        g.fillRect(x, y, w, h);
        g.fillStyle = C.text;
        g.font = `6px ${UI_FONT}`;
        g.textAlign = "center";
        g.fillText(String(card.name || "").slice(0, 9), x + w / 2, y + h / 2 + 2);
      }
      g.restore();
    }

    function shadow(x, w) {
      g.fillStyle = "rgba(0, 0, 0, 0.35)";
      g.beginPath();
      g.ellipse(x, GROUND + 2, w / 2, 3, 0, 0, Math.PI * 2);
      g.fill();
    }

    function drawSky() {
      const sky = g.createLinearGradient(0, 0, 0, GROUND);
      sky.addColorStop(0, C.skyTop);
      sky.addColorStop(0.6, C.skyMid);
      sky.addColorStop(1, C.skyLow);
      g.fillStyle = sky;
      g.fillRect(0, 0, W, GROUND);
      // The moon, with a glow, and a few darker seas.
      const mx = 392 - ((state.distance * 0.01) % 40);
      const my = 50;
      const glow = g.createRadialGradient(mx, my, 10, mx, my, 80);
      glow.addColorStop(0, "rgba(255, 240, 200, 0.35)");
      glow.addColorStop(1, "rgba(255, 240, 200, 0)");
      g.fillStyle = glow;
      g.fillRect(mx - 80, my - 80, 160, 160);
      g.fillStyle = C.moon;
      g.beginPath();
      g.arc(mx, my, 19, 0, Math.PI * 2);
      g.fill();
      g.fillStyle = "rgba(170, 160, 140, 0.35)";
      for (const [dx, dy, r] of [[-6, -4, 5], [6, 5, 3.5], [3, -8, 2.5]]) {
        g.beginPath();
        g.arc(mx + dx, my + dy, r, 0, Math.PI * 2);
        g.fill();
      }
      for (const star of stars) {
        g.globalAlpha = reduced ? 0.8 : 0.45 + 0.45 * Math.sin(state.time * 2.2 + star.phase);
        g.fillStyle = C.star;
        g.fillRect(star.x, star.y, star.s, star.s);
      }
      g.globalAlpha = 1;
    }

    function drawBackdrop() {
      const peaks = g.createLinearGradient(0, GROUND - 130, 0, GROUND);
      peaks.addColorStop(0, C.peaks[0]);
      peaks.addColorStop(1, C.peaks[1]);
      g.fillStyle = peaks;
      tiled(480, 0.06, (x) => { g.save(); g.translate(x, 0); g.fill(ridge); g.restore(); });
      // A haze over the far mountains, so the town stands out in front.
      const haze = g.createLinearGradient(0, GROUND - 60, 0, GROUND);
      haze.addColorStop(0, "rgba(106, 52, 102, 0)");
      haze.addColorStop(1, "rgba(106, 52, 102, 0.45)");
      g.fillStyle = haze;
      g.fillRect(0, GROUND - 60, W, 60);
      tiled(600, 0.22, (x) => {
        g.save();
        g.translate(x, 0);
        g.fillStyle = C.town;
        g.fill(town.roofs);
        g.fillStyle = C.window;
        g.globalAlpha = 0.75;
        g.fill(town.windows);
        g.restore();
      });
      g.fillStyle = C.hedge;
      tiled(420, 0.55, (x) => { g.save(); g.translate(x, 0); g.fill(hedge); g.restore(); });
    }

    function drawGround() {
      const earth = g.createLinearGradient(0, GROUND, 0, H);
      earth.addColorStop(0, C.earth[0]);
      earth.addColorStop(1, C.earth[1]);
      g.fillStyle = earth;
      g.fillRect(0, GROUND, W, H - GROUND);
      // Stones in the earth, moving with the course.
      g.fillStyle = C.stone;
      tiled(64, 1, (x) => {
        g.beginPath();
        for (const [sx, sy, rx, ry] of [[10, 18, 7, 3], [40, 31, 9, 3.5], [26, 41, 5, 2]]) {
          g.moveTo(x + sx + rx, GROUND + sy); // each stone its own shape: without the move, the path joins them up
          g.ellipse(x + sx, GROUND + sy, rx, ry, 0, 0, Math.PI * 2);
        }
        g.fill();
      });
      g.fillStyle = C.grass;
      g.fillRect(0, GROUND, W, 6);
      g.fillStyle = C.grassLit;
      g.fillRect(0, GROUND, W, 1.5);
      // Tufts along the edge.
      g.fillStyle = C.grass;
      tiled(23, 1, (x) => {
        g.beginPath();
        g.moveTo(x, GROUND + 1);
        g.lineTo(x + 2, GROUND - 3);
        g.lineTo(x + 4, GROUND + 1);
        g.fill();
      });
      // Gaps: pits cut into the ground, with dark depths and lit edges.
      for (const obj of state.objects) {
        if (obj.kind !== "gap") continue;
        const x = screenX(obj);
        if (x < -60 || x > W + 60) continue;
        const left = x - obj.w / 2;
        const pit = g.createLinearGradient(0, GROUND, 0, H);
        pit.addColorStop(0, "#130d1c");
        pit.addColorStop(1, C.pit);
        g.fillStyle = pit;
        g.fillRect(left, GROUND, obj.w, H - GROUND);
        g.fillStyle = "rgba(255, 255, 255, 0.06)";
        g.fillRect(left, GROUND + 6, 2, H - GROUND);
        g.fillRect(left + obj.w - 2, GROUND + 6, 2, H - GROUND);
      }
    }

    function drawCoin(x, y) {
      const turn = reduced ? 1 : Math.abs(Math.cos(state.time * 4 + x * 0.05));
      const rx = 10 * Math.max(0.18, turn);
      g.fillStyle = C.goldDark;
      g.beginPath();
      g.ellipse(x + 1, y, rx, 11, 0, 0, Math.PI * 2);
      g.fill();
      g.fillStyle = C.gold;
      g.beginPath();
      g.ellipse(x, y, rx, 11, 0, 0, Math.PI * 2);
      g.fill();
      g.fillStyle = C.goldLit;
      g.beginPath();
      g.ellipse(x, y, rx * 0.68, 7.5, 0, 0, Math.PI * 2);
      g.fill();
      if (turn > 0.5) { // the face: a star
        g.fillStyle = C.goldDark;
        g.beginPath();
        for (let i = 0; i < 10; i++) {
          const r = i % 2 ? 2 : 4.5;
          const a = -Math.PI / 2 + (i * Math.PI) / 5;
          g.lineTo(x + Math.cos(a) * r * turn, y + Math.sin(a) * r);
        }
        g.fill();
      }
    }

    function drawShieldOrb(card, x, y) {
      const bob = reduced ? 0 : Math.sin(state.time * 3 + x * 0.1) * 2;
      y += bob;
      const glow = g.createRadialGradient(x, y, 4, x, y, 20);
      glow.addColorStop(0, "rgba(143, 243, 255, 0.55)");
      glow.addColorStop(1, "rgba(143, 243, 255, 0)");
      g.fillStyle = glow;
      g.fillRect(x - 20, y - 20, 40, 40);
      g.save();
      g.beginPath();
      g.arc(x, y, 11, 0, Math.PI * 2);
      g.clip();
      drawCard(card, x - 9, y - 12, 18, 25);
      g.restore();
      g.strokeStyle = C.shield;
      g.lineWidth = 1.6;
      g.setLineDash([4, 3]);
      g.lineDashOffset = reduced ? 0 : -state.time * 12;
      g.beginPath();
      g.arc(x, y, 13, 0, Math.PI * 2);
      g.stroke();
      g.setLineDash([]);
    }

    function drawObjects() {
      for (const obj of state.objects) {
        if (obj.kind === "gap") continue;
        const x = screenX(obj);
        if (x < -40 || x > W + 40) continue;
        if (obj.kind === "coin") {
          drawCoin(x, GROUND - obj.lo - 11);
        } else if (obj.kind === "shield") {
          drawShieldOrb(obj.card, x, GROUND - obj.lo - 11);
        } else if (obj.kind === "low") {
          // A card on an easel: legs, and the card leaning on them.
          shadow(x, obj.w + 6);
          g.strokeStyle = C.wood;
          g.lineWidth = 2;
          g.beginPath();
          g.moveTo(x - 10, GROUND); g.lineTo(x - 4, GROUND - 32);
          g.moveTo(x + 10, GROUND); g.lineTo(x + 4, GROUND - 32);
          g.moveTo(x, GROUND); g.lineTo(x + 2, GROUND - 26);
          g.stroke();
          drawCard(obj.card, x - 12, GROUND - 34, 24, 33);
        } else if (obj.kind === "tall") {
          // A card high on a post: jump the whole thing.
          shadow(x, obj.w);
          g.fillStyle = C.wood;
          g.fillRect(x - 3, GROUND - 30, 6, 30);
          g.fillStyle = C.woodLit;
          g.fillRect(x - 3, GROUND - 30, 1.5, 30);
          drawCard(obj.card, x - 14, GROUND - 70, 28, 40);
        } else if (obj.kind === "high") {
          // A banner hung across the way: the card on its side, ropes up out of sight, and a warning edge to slide under.
          const top = GROUND - obj.hi;
          g.strokeStyle = "rgba(230, 210, 180, 0.6)";
          g.lineWidth = 1;
          g.beginPath();
          g.moveTo(x - 16, 0); g.lineTo(x - 16, top);
          g.moveTo(x + 16, 0); g.lineTo(x + 16, top);
          g.stroke();
          g.fillStyle = C.banner;
          g.fillRect(x - obj.w / 2 - 2, top - 2, obj.w + 4, obj.hi - obj.lo + 4);
          drawCard(obj.card, x - 19, top + 1, 38, 28, { rotate: Math.PI / 2, frame: C.banner });
          g.fillStyle = "#ff6b9a";
          g.fillRect(x - obj.w / 2 - 2, GROUND - obj.lo, obj.w + 4, 2);
          for (const tx of [x - obj.w / 2, x, x + obj.w / 2 - 3]) { // tassels
            g.fillRect(tx, GROUND - obj.lo + 2, 3, 4);
          }
        }
      }
    }

    // The runner: drawn about their feet, in a pose for running, jumping or sliding. The figure fits the hit box
    // (20 wide, 44 tall; 22 tall sliding), so what you see is what can be hit.
    function limb(x1, y1, angle1, length1, angle2, length2, width, color) {
      const kx = x1 + Math.sin(angle1) * length1;
      const ky = y1 + Math.cos(angle1) * length1;
      const fx = kx + Math.sin(angle2) * length2;
      const fy = ky + Math.cos(angle2) * length2;
      g.strokeStyle = color;
      g.lineWidth = width;
      g.lineCap = "round";
      g.lineJoin = "round";
      g.beginPath();
      g.moveTo(x1, y1);
      g.lineTo(kx, ky);
      g.lineTo(fx, fy);
      g.stroke();
    }

    function drawHead(x, y, r) {
      g.save();
      g.beginPath();
      g.arc(x, y, r, 0, Math.PI * 2);
      g.clip();
      if (picture && ready(face)) {
        // The avatar as the profile page crops it: its width and offsets are percents of the circle.
        const size = r * 2;
        const w = (Number(picture.width) || 100) / 100 * size;
        const h = w * (face.naturalHeight / face.naturalWidth);
        g.drawImage(face, x - r + (Number(picture.left) || 0) / 100 * size, y - r + (Number(picture.top) || 0) / 100 * size, w, h);
      } else {
        g.fillStyle = C.skin;
        g.fillRect(x - r, y - r, r * 2, r * 2);
        g.fillStyle = C.hair;
        g.beginPath();
        g.arc(x - 1, y - 3, r, Math.PI * 0.95, Math.PI * 2.1);
        g.fill();
        g.fillStyle = "#1c1426";
        g.fillRect(x + 3, y - 1, 1.6, 2.4);
      }
      g.restore();
      g.strokeStyle = "rgba(255, 255, 255, 0.85)";
      g.lineWidth = 1.2;
      g.beginPath();
      g.arc(x, y, r, 0, Math.PI * 2);
      g.stroke();
    }

    function drawRunner() {
      const flicker = state.invulnerable > 0 && Math.floor(state.time * 14) % 2 === 0;
      const feet = GROUND - state.altitude;
      const x = PLAYER_X;
      const phase = state.distance / 14;
      const airborne = state.altitude > 0;
      g.save();
      if (flicker) g.globalAlpha = 0.35;
      if (!airborne) {
        g.fillStyle = "rgba(0, 0, 0, 0.35)";
        g.beginPath();
        g.ellipse(x, GROUND + 2, 11, 2.5, 0, 0, Math.PI * 2);
        g.fill();
      }
      if (state.sliding) {
        // Leaning back on one hand, feet first: low enough to pass under a banner.
        const hip = { x: x - 2, y: feet - 6 };
        limb(hip.x, hip.y, 1.35, 9, 1.55, 9, 4, C.outfit); // the leading leg, out in front
        limb(hip.x, hip.y, 1.2, 8, 1.9, 8, 4, C.outfitLit);
        g.strokeStyle = C.outfit;
        g.lineWidth = 7;
        g.beginPath();
        g.moveTo(hip.x, hip.y);
        g.lineTo(hip.x - 9, hip.y - 8);
        g.stroke();
        limb(hip.x - 8, hip.y - 7, -2.3, 6, -3.0, 6, 3, C.outfitLit); // the arm behind, propping
        drawScarf(hip.x - 10, hip.y - 10, true);
        drawHead(hip.x - 13, hip.y - 14, 6.5);
      } else {
        const swing = airborne ? 0 : Math.sin(phase);
        const hip = { x, y: feet - 17 };
        const shoulder = { x: x + 2.5, y: feet - 31 };
        if (airborne) {
          // Knees tucked, arms up.
          limb(hip.x, hip.y, 0.9, 8, -0.4, 8, 4, C.outfit);
          limb(hip.x, hip.y, 0.5, 8, -0.7, 8, 4, C.outfitLit);
        } else {
          // The run: thighs swing opposite, each shin bending back as its foot comes through.
          limb(hip.x, hip.y, swing * 0.8, 9, swing * 0.8 - 0.4 - Math.max(0, -swing) * 0.9, 9, 4, C.outfit);
          limb(hip.x, hip.y, -swing * 0.8, 9, -swing * 0.8 - 0.4 - Math.max(0, swing) * 0.9, 9, 4, C.outfitLit);
        }
        // The body, leaning into the run.
        g.strokeStyle = C.outfitLit;
        g.lineWidth = 8;
        g.lineCap = "round";
        g.beginPath();
        g.moveTo(hip.x, hip.y);
        g.lineTo(shoulder.x, shoulder.y);
        g.stroke();
        g.strokeStyle = C.gold; // a gold belt
        g.lineWidth = 2;
        g.beginPath();
        g.moveTo(hip.x - 4, hip.y - 1);
        g.lineTo(hip.x + 4, hip.y - 2);
        g.stroke();
        if (airborne) {
          limb(shoulder.x, shoulder.y, -2.4, 7, -2.9, 6, 3, C.outfit);
          limb(shoulder.x, shoulder.y, -2.1, 7, -2.6, 6, 3, C.outfitLit);
        } else {
          limb(shoulder.x, shoulder.y, -swing * 0.9, 7, -swing * 0.9 + 1.2, 6, 3, C.outfit);
          limb(shoulder.x, shoulder.y, swing * 0.9, 7, swing * 0.9 + 1.2, 6, 3, C.outfitLit);
        }
        drawScarf(shoulder.x - 1, shoulder.y - 1, false);
        drawHead(shoulder.x + 1.5, shoulder.y - 7.5, 7);
      }
      if (state.shield) {
        const cy = feet - (state.sliding ? 11 : 22);
        const ring = g.createRadialGradient(x, cy, 18, x, cy, 30);
        ring.addColorStop(0, "rgba(143, 243, 255, 0)");
        ring.addColorStop(1, "rgba(143, 243, 255, 0.35)");
        g.fillStyle = ring;
        g.beginPath();
        g.arc(x, cy, 30, 0, Math.PI * 2);
        g.fill();
        g.strokeStyle = "rgba(143, 243, 255, 0.85)";
        g.lineWidth = 1.4;
        g.beginPath();
        for (let i = 0; i <= 6; i++) { // a slowly turning hexagon
          const a = (reduced ? 0 : state.time) + (i * Math.PI) / 3;
          g.lineTo(x + Math.cos(a) * 29, cy + Math.sin(a) * 29);
        }
        g.stroke();
      }
      g.restore();
    }

    // The scarf streams out behind, rippling: it makes the speed read even when the runner's in the air.
    function drawScarf(x, y, low) {
      g.strokeStyle = C.gold;
      g.lineWidth = 2.6;
      g.lineCap = "round";
      g.beginPath();
      g.moveTo(x, y);
      for (let k = 1; k <= 5; k++) {
        const wave = reduced ? 0 : Math.sin(state.time * 14 - k * 0.9) * (1 + k * 0.4);
        g.lineTo(x - k * 4, y + (low ? -k * 0.2 : k * 0.9) + wave);
      }
      g.stroke();
    }

    function drawEffects() {
      for (const p of state.particles) {
        g.globalAlpha = clamp(p.life * 2, 0, 1);
        g.fillStyle = p.color;
        g.beginPath();
        g.arc(p.x, p.y, p.size / 2, 0, Math.PI * 2);
        g.fill();
      }
      g.globalAlpha = 1;
      // Speed lines once the run is fast.
      const fast = clamp((speed() - tune.speed - 90) / 150, 0, 1);
      if (fast > 0 && !reduced) {
        g.strokeStyle = `rgba(255, 255, 255, ${0.12 * fast})`;
        g.lineWidth = 1;
        for (let i = 0; i < 7; i++) {
          const y = 30 + ((i * 37) % (GROUND - 50));
          const x = W - ((state.time * 900 + i * 173) % (W + 120));
          g.beginPath();
          g.moveTo(x, y);
          g.lineTo(x + 50, y);
          g.stroke();
        }
      }
      for (const p of state.pops) {
        const t = p.life / p.total;
        g.globalAlpha = clamp(t * 2, 0, 1);
        g.textAlign = "center";
        g.font = p.big ? `700 20px ${DISPLAY_FONT}` : `700 11px ${UI_FONT}`;
        g.lineWidth = p.big ? 4 : 3;
        g.strokeStyle = "rgba(0, 0, 0, 0.6)";
        g.strokeText(p.text, p.x, p.y);
        g.fillStyle = p.color;
        g.fillText(p.text, p.x, p.y);
      }
      g.globalAlpha = 1;
    }

    function heart(x, y, size, filled) {
      g.beginPath();
      g.moveTo(x, y + size * 0.3);
      g.bezierCurveTo(x, y, x - size * 0.5, y, x - size * 0.5, y + size * 0.3);
      g.bezierCurveTo(x - size * 0.5, y + size * 0.6, x, y + size * 0.8, x, y + size);
      g.bezierCurveTo(x, y + size * 0.8, x + size * 0.5, y + size * 0.6, x + size * 0.5, y + size * 0.3);
      g.bezierCurveTo(x + size * 0.5, y, x, y, x, y + size * 0.3);
      if (filled) {
        g.fillStyle = "#ff5a6e";
        g.fill();
      }
      g.strokeStyle = filled ? "#ffd1d7" : "rgba(255, 255, 255, 0.45)";
      g.lineWidth = 1;
      g.stroke();
    }

    function drawDisplay() {
      // Hits left, as hearts, and the shield beside them.
      for (let i = 0; i < HITS_ALLOWED; i++) heart(16 + i * 15, 9, 11, i < HITS_ALLOWED - state.hits);
      if (state.shield) {
        g.strokeStyle = C.shield;
        g.lineWidth = 1.5;
        g.beginPath();
        g.arc(16 + HITS_ALLOWED * 15 + 4, 14.5, 5.5, 0, Math.PI * 2);
        g.stroke();
      }
      // Coins towards the target, as a bar: gold, and lit once it's reached.
      const barW = 120;
      const bx = W - barW - 12;
      const share = clamp(points() / tune.target, 0, 1);
      g.fillStyle = "rgba(0, 0, 0, 0.45)";
      g.fillRect(bx, 10, barW, 8);
      g.fillStyle = state.reached ? "#7be495" : C.gold;
      g.fillRect(bx, 10, barW * share, 8);
      g.strokeStyle = "rgba(255, 255, 255, 0.35)";
      g.lineWidth = 1;
      g.strokeRect(bx, 10, barW, 8);
      g.font = `700 10px ${UI_FONT}`;
      g.textAlign = "right";
      g.fillStyle = C.text;
      g.fillText(`${points()} / ${tune.target}`, bx - 6, 18);
      g.textAlign = "right";
      g.fillStyle = "rgba(246, 241, 231, 0.75)";
      g.fillText(`${Math.floor(state.distance / 10)} m`, W - 12, 32);
    }

    function draw() {
      g.setTransform(DPR * scale, 0, 0, DPR * scale, 0, 0);
      g.save();
      if (state.shake > 0) g.translate((rnd() - 0.5) * 6 * (state.shake / 0.3), (rnd() - 0.5) * 4 * (state.shake / 0.3));
      drawSky();
      drawBackdrop();
      drawGround();
      drawObjects();
      drawRunner();
      drawEffects();
      g.restore();
      // A red edge when hit.
      if (state.invulnerable > INVULNERABLE - 0.25 && !reduced) {
        const edge = g.createRadialGradient(W / 2, H / 2, H * 0.4, W / 2, H / 2, W * 0.7);
        edge.addColorStop(0, "rgba(255, 60, 80, 0)");
        edge.addColorStop(1, "rgba(255, 60, 80, 0.35)");
        g.fillStyle = edge;
        g.fillRect(0, 0, W, H);
      }
      drawDisplay();

      if (state.paused) {
        g.fillStyle = "rgba(5, 4, 14, 0.62)";
        g.fillRect(0, 0, W, H);
        g.textAlign = "center";
        g.fillStyle = C.text;
        g.font = `700 26px ${DISPLAY_FONT}`;
        g.fillText("Paused", W / 2, H / 2 - 4);
        g.font = `13px ${UI_FONT}`;
        g.fillStyle = "rgba(246, 241, 231, 0.8)";
        g.fillText("Press P or ❚❚ to carry on", W / 2, H / 2 + 22);
      }
    }

    // ---- Pausing: by P, the pause button, leaving the page, or the tab being hidden ----

    function togglePause() {
      if (state.over || !state.started) return;
      state.paused = !state.paused;
      pauseButton.textContent = state.paused ? "▶" : "❚❚";
      pauseButton.setAttribute("aria-label", state.paused ? "Resume" : "Pause");
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

    let wasSliding = false; // for the slide sound: once when it starts
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
      if (state.started && !state.paused && !state.over) update(dt);
      draw();
      raf = requestAnimationFrame(frame);
    }

    // The shell calls this when the run ends, when playing again, and when choosing another game. The last picture stays
    // on the area. Safe to call more than once.
    function stop() {
      if (stopped) return;
      stopped = true;
      cancelAnimationFrame(raf);
      if (sizer) sizer.disconnect();
      ctx.area.removeEventListener("resize", fit);
      window.removeEventListener("resize", fit);
      if (window.MinigameAudio) window.MinigameAudio.stop();
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("keyup", onKeyUp);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", pauseIfAway);
    }

    function go() {
      if (stopped) return;
      state.started = true;
      last = 0;
      if (window.MinigameAudio) window.MinigameAudio.start("runner");
    }

    ctx.status(`Target ${tune.target}`);
    status();
    reportScore();
    raf = requestAnimationFrame(frame);
    // The new frame counts down first (3, 2, 1, Go!); the scene is drawn, standing still, until it's done.
    if (ctx.countdown) Promise.resolve(ctx.countdown()).then(go, go);
    else go();
    return { stop };
  }

  window.MinigameGames.runner = {
    title: "Runner",
    rule: "Jump, slide and grab the coins. Three hits ends it. Beat the target.",
    about: "The card runs on its own. Jump the low cards, slide under the high ones, and collect the coin cards. A climax is a shield for one hit. Three hits and it's over.",
    play: startRunner,
  };
})();
