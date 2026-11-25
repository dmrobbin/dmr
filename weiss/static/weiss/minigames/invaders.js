/* Climax Invaders (docs/minigames-plan.md, "Two games (Sam 2)"; its look: docs/minigames-polish-plan.md): a ship at the
   bottom shoots up at a formation of card pictures. Level 0 cards are simple, level 1 take two hits, level 2 swoop down
   at the ship, and level 3 are bosses that shoot back. A shot-down climax drops a power-up by its trigger: soul gives a
   double shot for a while, draw an extra life, and the others a bonus. Three waves and three lives; the CPU's target
   score is what to beat. Registers in window.MinigameGames and is started by the shell (shell.js), which gives the ctx:
   area, cards, cpu, difficulty, random, say, score, status and end, and in the new frame countdown. The game stops itself
   when it ends, and its stop() is safe to call again.

   The field is played in its own units, W by H (3:4); the canvas scales the whole picture to fit the space it's given.
   Drawing is all in code: no images but the cards' own art. */
(() => {
  window.MinigameGames = window.MinigameGames || {};

  const TUNING = {
    easy: { target: 4000, swoopEvery: 4.0, bossFire: 2.2, sway: 0.8, shot: 150 },
    normal: { target: 6000, swoopEvery: 2.8, bossFire: 1.6, sway: 1.0, shot: 190 },
    hard: { target: 8000, swoopEvery: 1.8, bossFire: 1.2, sway: 1.2, shot: 230 },
  };
  const W = 360; // the play field, in its own units (the canvas scales to fit)
  const H = 480;
  const SHIP_Y = H - 34;
  const SHIP_SPEED = 230;
  const SHOT_SPEED = 460;
  const SHOT_GAP = 0.26; // seconds between shots
  const LIVES = 3;
  const MAX_LIVES = 5;
  const WAVES = 3;
  const INVULNERABLE = 1.5; // seconds after a hit
  const DOUBLE_SHOT = 8; // seconds
  const SWOOP_TIME = 1.8; // seconds for a swoop from formation to the bottom
  const POINTS = [100, 150, 200, 300]; // by level
  const CLIMAX_POINTS = 150;
  const BONUS_POINTS = 200;
  const SPACING = 46; // between enemies across a row
  const ROW = 50; // between rows
  const TOP = 64; // the first row
  const DROP_SPEED = 90;
  const STALL_AFTER = 20; // seconds with no kill before the formation starts to widen and drift down
  const MAX_DRIFT = 120; // how far down it can come
  const LEAN_SPEED = 12; // how fast it leans toward the ship, units per second
  const BANNER_TIME = 1.8; // a wave's name on screen
  const DPR = Math.min(2, window.devicePixelRatio || 1);
  // Sound (minigames/audio.js), if it's there: a short effect, or nothing.
  const sfx = (name) => { if (window.MinigameAudio) window.MinigameAudio.sfx(name); };

  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const isClimax = (card) => String(card.type || "").toLowerCase() === "climax";
  const levelOf = (card) => (isClimax(card) ? 0 : clamp(Number(card.level) || 0, 0, 3));
  const dropOf = (card) => {
    const trigger = String(card.trigger || "").toLowerCase();
    if (trigger.includes("soul")) return "soul";
    if (trigger.includes("draw")) return "draw";
    return "bonus";
  };
  const DROP_LABEL = { soul: "S", draw: "+", bonus: "★" };
  const DROP_COLOR = { soul: "#ffd36b", draw: "#7dffb0", bonus: "#e8f0ff" };
  // Each level's colour, for the card's frame and glow; a climax is gold.
  const LEVEL_COLOR = ["#a9bde0", "#4fc3f7", "#ffaa4d", "#ff5d8f"];
  const CLIMAX_COLOR = "#f4cf5a";
  const DISPLAY_FONT = '"Cinzel", Georgia, serif';
  const UI_FONT = 'system-ui, "Segoe UI", sans-serif';
  const TEXT = "#f6f1e7";

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function startInvaders(ctx) {
    const rnd = ctx.random;
    const tune = TUNING[ctx.difficulty] || TUNING.normal;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const pool = (ctx.cards || []).filter(Boolean);
    if (!pool.length) {
      ctx.status("No cards to fight with.");
      ctx.end("draw");
      return null;
    }

    // ---- The page: the screen (the canvas, with a pause button on it), the touch buttons, and a hint ----
    const board = el("div", "inv-board");
    const screen = el("div", "inv-screen");
    const canvas = el("canvas", "inv-canvas");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Climax Invaders. Left and right to move, P to pause. The ship fires by itself.");
    const g = canvas.getContext("2d");

    const touch = el("div", "inv-touch");
    const touching = { left: false, right: false };
    const button = (className, name, label) => {
      const node = el("button", className, label);
      node.type = "button";
      node.setAttribute("aria-label", name);
      return node;
    };
    const left = button("inv-key", "Move left", "◀");
    const right = button("inv-key", "Move right", "▶");
    const pause = button("inv-pause", "Pause", "❚❚");
    pause.setAttribute("aria-pressed", "false");
    for (const [name, node] of [["left", left], ["right", right]]) {
      node.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        touching[name] = true;
      });
      for (const type of ["pointerup", "pointercancel", "pointerleave"]) {
        node.addEventListener(type, () => { touching[name] = false; });
      }
    }
    pause.addEventListener("click", () => togglePause());
    touch.append(left, right);
    screen.append(canvas, pause);
    const spoken = el("p", "sr-only"); // for screen readers: lives left, and the wave
    spoken.setAttribute("aria-live", "polite");
    const hint = el("p", "inv-hint small", "Arrows or A and D to move · P to pause · the ship fires by itself");
    board.append(screen, touch, hint, spoken);
    ctx.area.append(board);

    // ---- Fitting the space: the screen is as large as it can be at 3:4 in the space it's given ----
    let scale = 1;
    function fit() {
      // The area's inner size: its client size less its padding (the board sits inside the padding).
      const box = getComputedStyle(ctx.area);
      const padX = (parseFloat(box.paddingLeft) || 0) + (parseFloat(box.paddingRight) || 0);
      const padY = (parseFloat(box.paddingTop) || 0) + (parseFloat(box.paddingBottom) || 0) + 4; // and the screen's border
      const areaW = (ctx.area.clientWidth || W) - padX;
      const areaH = ctx.area.clientHeight - padY;
      const below = (touch.offsetParent ? touch.offsetHeight : 0) + (hint.offsetParent ? hint.offsetHeight : 0) + 20;
      let width = Math.min(areaW, 560);
      // The frame gives the area a definite height. A tiny one (under 120) is a space still sizing itself to us, as an
      // older frame's does: going by it would shrink the screen to nothing, so then the width alone decides.
      if (areaH >= 120) width = Math.min(width, ((areaH - below) * W) / H);
      width = Math.max(220, Math.floor(width));
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
    ctx.area.addEventListener("resize", fit);
    window.addEventListener("resize", fit);
    fit();

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
    const stars = Array.from({ length: 70 }, () => ({ x: rnd() * W, y: rnd() * H, s: 0.4 + rnd() * 1.3, v: 10 + rnd() * 40, phase: rnd() * 6.3 }));
    const nebulae = [
      { x: W * 0.25, y: H * 0.3, r: 170, color: "110, 60, 170", drift: 0.6 },
      { x: W * 0.8, y: H * 0.65, r: 150, color: "40, 120, 160", drift: -0.4 },
    ];
    const state = {
      ship: W / 2, lives: LIVES, score: 0, wave: 0, paused: false, over: false,
      cooldown: 0, invulnerable: 0, double: 0, intermission: 0, swoopIn: tune.swoopEvery, time: 0,
      enemies: [], shots: [], enemyShots: [], drops: [], particles: [], shards: [], pops: [],
      idle: 0, // seconds since the last kill: a formation that's left alone widens and drifts down, so a wave ends
      drift: 0, // how far down the formation has come
      started: !ctx.countdown, banner: { text: "", life: 0 }, shake: 0, reached: false, tilt: 0,
    };
    const input = { left: false, right: false };
    const KEYS = { ArrowLeft: "left", KeyA: "left", ArrowRight: "right", KeyD: "right" };

    const waveName = (n) => (n >= WAVES - 1 ? "Final wave" : `Wave ${n + 1}`);

    function status() {
      ctx.status(`Wave ${Math.min(state.wave + 1, WAVES)} of ${WAVES}`);
      spoken.textContent = `${waveName(state.wave)}. ${state.lives} ${state.lives === 1 ? "life" : "lives"} left.`;
    }

    function addScore(points) {
      state.score += points;
      ctx.score(state.score, tune.target); // the CPU's line is their target: passing it is the lead changing
      if (!state.reached && state.score >= tune.target) {
        state.reached = true;
        pop(W / 2, H * 0.42, "Target reached!", { big: true, color: "#7be495", life: 1.6 });
      }
    }

    function burst(x, y, count, color, speed = 3) {
      const n = reduced ? Math.ceil(count / 3) : count;
      for (let i = 0; i < n && state.particles.length < 200; i++) {
        const angle = rnd() * Math.PI * 2;
        const v = (0.5 + rnd()) * speed * 40;
        state.particles.push({ x, y, vx: Math.cos(angle) * v, vy: Math.sin(angle) * v, life: 0.5 + rnd() * 0.4, color, size: 1.5 + rnd() * 2 });
      }
    }

    // A card shot down breaks into pieces of itself: each a little shard with its piece of the picture, spinning off.
    function shatter(e) {
      const n = reduced ? 4 : 9;
      for (let i = 0; i < n && state.shards.length < 80; i++) {
        const angle = rnd() * Math.PI * 2;
        const v = 40 + rnd() * 120;
        const sx = rnd() * 0.66;
        const sy = rnd() * 0.66;
        state.shards.push({ card: e.card, climax: e.climax, color: e.color, x: e.x + (sx - 0.33) * e.w, y: e.y + (sy - 0.33) * e.h,
          w: e.w / 3, h: e.h / 3, sx, sy, vx: Math.cos(angle) * v, vy: Math.sin(angle) * v - 40, spin: (rnd() - 0.5) * 10, angle: 0, life: 0.8 + rnd() * 0.4 });
      }
    }

    function pop(x, y, text, options = {}) {
      state.pops.push({ x, y, text, life: options.life || 0.9, total: options.life || 0.9, big: Boolean(options.big), color: options.color || TEXT });
    }

    // The end: the game runs until the last wave is cleared or the lives run out. Then the score decides: at or above the
    // target wins, below it loses. Reaching the target mid-run doesn't end it. The shell says the CPU's line and calls stop().
    function finish(result) {
      if (state.over) return;
      state.over = true;
      sfx(result);
      ctx.end(result, { line: `${state.score} points. Target: ${tune.target}.` }); // Barry's words, for the results screen
    }

    function loseLife() {
      if (state.invulnerable > 0 || state.over) return;
      state.lives -= 1;
      state.invulnerable = INVULNERABLE;
      state.shake = reduced ? 0 : 0.35;
      sfx("hit");
      burst(state.ship, SHIP_Y, 22, "#ff8a7a", 3);
      ctx.say("cpu_good");
      if (state.lives <= 0) {
        finish(state.score >= tune.target ? "win" : "lose"); // the game ends with the lives: decided by the score then
        return;
      }
      status();
    }

    // ---- Waves ----

    function makeEnemy(card, x, y) {
      const level = levelOf(card);
      const boss = level === 3;
      const maxHp = level === 1 ? 2 : boss ? 3 : 1;
      return {
        card, level, boss, climax: isClimax(card), maxHp, hp: maxHp, x, y, homeX: x, homeY: y, lean: 0,
        w: boss ? 56 : 42, h: boss ? 48 : 36,
        mode: "formation", // or "swoop", once it dives at the ship
        t: 0, fromX: x, fromY: y, aimX: x, dir: 1,
        fireIn: rnd() * tune.bossFire + 0.5,
        flash: 0, dead: false,
        drop: isClimax(card) ? dropOf(card) : null,
        color: isClimax(card) ? CLIMAX_COLOR : LEVEL_COLOR[level],
        phase: rnd() * 6.3,
      };
    }

    function startWave() {
      const cols = 6 + (state.wave === WAVES - 1 ? 1 : 0);
      const rows = 3 + state.wave;
      const first = (W - (cols - 1) * SPACING) / 2;
      state.enemies = [];
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const card = pool[Math.floor(rnd() * pool.length)];
          state.enemies.push(makeEnemy(card, first + col * SPACING, TOP + row * ROW));
        }
      }
      state.swoopIn = tune.swoopEvery;
      state.idle = 0;
      state.drift = 0;
      state.banner = { text: waveName(state.wave), life: BANNER_TIME };
      status();
    }

    function startSwoop(e) {
      e.mode = "swoop";
      e.t = 0;
      e.fromX = e.x;
      e.fromY = e.y;
      e.aimX = state.ship;
      e.dir = e.x < W / 2 ? 1 : -1;
    }

    function waveCleared() {
      if (state.wave >= WAVES - 1) {
        finish(state.score >= tune.target ? "win" : "lose"); // the last wave cleared: decided by the score
        return;
      }
      ctx.say("player_good");
      state.intermission = 1.8;
      state.banner = { text: `${waveName(state.wave)} cleared`, life: 1.6 };
    }

    // ---- Hits and power-ups ----

    function hitEnemy(e) {
      e.hp -= 1;
      e.flash = 0.12;
      sfx("hit");
      if (e.hp > 0) {
        burst(e.x, e.y, 5, "#ffffff", 2);
        return;
      }
      e.dead = true;
      state.idle = 0;
      const points = e.climax ? CLIMAX_POINTS : POINTS[e.level];
      addScore(points);
      burst(e.x, e.y, 18, e.color);
      shatter(e);
      pop(e.x, e.y - 6, `+${points}`, { color: e.color });
      if (e.drop) state.drops.push({ x: e.x, y: e.y, kind: e.drop, taken: false });
    }

    function collect(kind) {
      sfx("pickup");
      burst(state.ship, SHIP_Y - 8, 12, DROP_COLOR[kind], 2);
      if (kind === "soul") {
        state.double = DOUBLE_SHOT;
        pop(state.ship, SHIP_Y - 34, "Double shot", { color: DROP_COLOR.soul });
      } else if (kind === "draw") {
        const full = state.lives >= MAX_LIVES;
        state.lives = Math.min(MAX_LIVES, state.lives + 1);
        pop(state.ship, SHIP_Y - 34, full ? "Lives full" : "Extra life", { color: DROP_COLOR.draw });
        status();
      } else {
        addScore(BONUS_POINTS);
        pop(state.ship, SHIP_Y - 34, `+${BONUS_POINTS}`, { color: DROP_COLOR.bonus });
      }
    }

    // ---- One step of the game, dt seconds on ----

    function update(dt) {
      state.time += dt;
      for (const star of stars) {
        star.y += star.v * dt;
        if (star.y > H) {
          star.y = 0;
          star.x = rnd() * W;
        }
      }

      // The ship and its shots.
      const moveLeft = input.left || touching.left;
      const moveRight = input.right || touching.right;
      const move = (moveRight ? 1 : 0) - (moveLeft ? 1 : 0);
      state.ship = clamp(state.ship + move * SHIP_SPEED * dt, 12, W - 12);
      state.tilt += (move - state.tilt) * Math.min(1, dt * 10); // the ship banks as it moves (only its look)
      state.cooldown -= dt;
      state.invulnerable -= dt;
      state.double -= dt;
      // The ship fires by itself. A double shot is faster and wider fire, not a key press.
      if (state.cooldown <= 0 && state.shots.length < (state.double > 0 ? 6 : 3)) {
        state.cooldown = state.double > 0 ? SHOT_GAP * 0.55 : SHOT_GAP;
        for (const offset of state.double > 0 ? [-7, 7] : [0]) {
          state.shots.push({ x: state.ship + offset, y: SHIP_Y - 14 });
        }
        sfx("shoot");
      }
      for (const shot of state.shots) shot.y -= SHOT_SPEED * dt;

      // The formation sways; level 2 cards now and then break off and dive at the ship; bosses fire back.
      // Left alone (no kill for a while), the formation sways wider and drifts down, so a wave always ends.
      if (state.enemies.length && state.intermission <= 0) state.idle += dt;
      const stalled = state.idle > STALL_AFTER;
      if (stalled) state.drift = Math.min(MAX_DRIFT, state.drift + dt * 4);
      const spread = stalled ? Math.min(64, (state.idle - STALL_AFTER) * 4) : 0;
      const sway = Math.sin(state.time * 0.9 * tune.sway) * (26 + spread);
      for (const e of state.enemies) {
        if (e.dead) continue;
        e.flash = Math.max(0, e.flash - dt);
        if (e.mode === "formation") {
          // Left alone, each card leans across toward the ship's column, so a ship that doesn't move still meets it.
          if (stalled) {
            const want = state.ship - e.homeX;
            e.lean += Math.sign(want - e.lean) * Math.min(Math.abs(want - e.lean), LEAN_SPEED * dt);
          }
          e.x = e.homeX + sway + e.lean;
          e.y = e.homeY + state.drift;
          if (e.boss) {
            e.fireIn -= dt;
            if (e.fireIn <= 0) {
              e.fireIn = tune.bossFire * (0.8 + rnd() * 0.4);
              state.enemyShots.push({ x: e.x, y: e.y + e.h / 2, vx: clamp((state.ship - e.x) * 0.35, -70, 70), vy: tune.shot });
            }
          }
        } else {
          e.t += dt;
          const p = Math.min(1, e.t / SWOOP_TIME);
          e.x = e.fromX + (e.aimX - e.fromX) * p + Math.sin(p * Math.PI) * 70 * e.dir;
          e.y = e.fromY + (H + 60 - e.fromY) * p;
          if (!reduced && Math.floor(e.t * 30) % 2 === 0) { // a trail behind a diving card
            state.particles.push({ x: e.x, y: e.y - e.h / 2, vx: 0, vy: -20, life: 0.35, color: e.color, size: 2.5 });
          }
          if (p >= 1) {
            // It got past the ship: no harm, but it isn't cleared. It climbs back into its place in the formation, so a
            // wave only ends when its cards are shot down (or the ship is).
            e.mode = "formation";
            e.t = 0;
            e.x = e.homeX;
            e.y = e.homeY + state.drift;
          } else if (Math.abs(e.x - state.ship) < 22 && Math.abs(e.y - SHIP_Y) < 22) {
            e.dead = true;
            burst(e.x, e.y, 14, "#ffb0a0");
            shatter(e);
            loseLife();
          }
        }
      }
      state.swoopIn -= dt;
      if (state.swoopIn <= 0) {
        state.swoopIn = tune.swoopEvery * (0.7 + rnd() * 0.6);
        const ready = state.enemies.filter((e) => e.level === 2 && e.mode === "formation" && !e.dead);
        if (ready.length) startSwoop(ready[Math.floor(rnd() * ready.length)]);
      }

      // Shots meet enemies.
      for (const shot of state.shots) {
        const hit = state.enemies.find((e) => !e.dead && Math.abs(shot.x - e.x) < e.w / 2 && Math.abs(shot.y - e.y) < e.h / 2);
        if (hit) {
          shot.y = -99;
          hitEnemy(hit);
        }
      }
      state.shots = state.shots.filter((shot) => shot.y > -10);

      // Enemy shots meet the ship.
      for (const shot of state.enemyShots) {
        shot.x += shot.vx * dt;
        shot.y += shot.vy * dt;
        if (state.invulnerable <= 0 && Math.abs(shot.x - state.ship) < 11 && Math.abs(shot.y - SHIP_Y) < 12) {
          shot.y = H + 99;
          loseLife();
        }
      }
      state.enemyShots = state.enemyShots.filter((shot) => shot.y < H + 20 && shot.x > -20 && shot.x < W + 20);

      // Power-ups fall; the ship takes them.
      for (const drop of state.drops) {
        drop.y += DROP_SPEED * dt;
        if (Math.abs(drop.x - state.ship) < 18 && Math.abs(drop.y - SHIP_Y) < 18) {
          drop.taken = true;
          collect(drop.kind);
        }
      }
      state.drops = state.drops.filter((drop) => !drop.taken && drop.y < H + 20);

      for (const p of state.particles) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.life -= dt;
      }
      state.particles = state.particles.filter((p) => p.life > 0);
      for (const s of state.shards) {
        s.x += s.vx * dt;
        s.y += s.vy * dt;
        s.vy += 160 * dt;
        s.angle += s.spin * dt;
        s.life -= dt;
      }
      state.shards = state.shards.filter((s) => s.life > 0);
      for (const p of state.pops) { p.y -= 28 * dt; p.life -= dt; }
      state.pops = state.pops.filter((p) => p.life > 0);
      state.banner.life -= dt;
      state.shake = Math.max(0, state.shake - dt);

      // Waves: the next one after a short pause, or the end once the last is cleared.
      state.enemies = state.enemies.filter((e) => !e.dead);
      if (state.intermission > 0) {
        state.intermission -= dt;
        if (state.intermission <= 0 && !state.over) {
          state.wave += 1;
          sfx("wave");
          startWave();
        }
      } else if (!state.enemies.length && !state.over) {
        waveCleared();
      }
    }

    // ---- Drawing: in field units, scaled to the canvas ----

    function drawSpace() {
      const space = g.createLinearGradient(0, 0, 0, H);
      space.addColorStop(0, "#05061a");
      space.addColorStop(1, "#0b0a24");
      g.fillStyle = space;
      g.fillRect(0, 0, W, H);
      for (const n of nebulae) {
        const x = n.x + (reduced ? 0 : Math.sin(state.time * 0.05 * n.drift) * 30);
        const cloud = g.createRadialGradient(x, n.y, 10, x, n.y, n.r);
        cloud.addColorStop(0, `rgba(${n.color}, 0.32)`);
        cloud.addColorStop(1, `rgba(${n.color}, 0)`);
        g.fillStyle = cloud;
        g.fillRect(x - n.r, n.y - n.r, n.r * 2, n.r * 2);
      }
      for (const star of stars) {
        g.globalAlpha = reduced ? 0.8 : 0.5 + 0.45 * Math.sin(state.time * 3 + star.phase);
        g.fillStyle = star.v > 35 ? "#ffffff" : "#bcc8ff";
        g.fillRect(star.x, star.y, star.s, star.s * (star.v > 40 ? 2.4 : 1)); // the nearest stream past
      }
      g.globalAlpha = 1;
    }

    function cardArt(card, climax, sx, sy, sw, sh, dx, dy, dw, dh) {
      const img = card.image ? images.get(card.image) : null;
      if (!(img && img.complete && img.naturalWidth > 0)) return false;
      if (climax) {
        // Climaxes are printed sideways: the whole picture.
        g.drawImage(img, sx * img.naturalWidth, sy * img.naturalHeight, sw * img.naturalWidth, sh * img.naturalHeight, dx, dy, dw, dh);
      } else {
        // A character's art: the picture cropped to the artwork, not the frame around it.
        const ax = 0.08, ay = 0.12, aw = 0.84, ah = 0.5;
        g.drawImage(img, (ax + sx * aw) * img.naturalWidth, (ay + sy * ah) * img.naturalHeight, sw * aw * img.naturalWidth,
          sh * ah * img.naturalHeight, dx, dy, dw, dh);
      }
      return true;
    }

    function drawEnemy(e) {
      const tilt = reduced ? 0 : Math.sin(state.time * 2 + e.phase) * 0.06 + (e.mode === "swoop" ? e.dir * 0.35 : 0);
      const bob = reduced ? 0 : Math.sin(state.time * 2.4 + e.phase) * 1.5;
      g.save();
      g.translate(e.x, e.y + bob);
      g.rotate(tilt);
      // A glow in the level's colour behind the card.
      const glow = g.createRadialGradient(0, 0, e.w * 0.2, 0, 0, e.w * 0.9);
      glow.addColorStop(0, `${e.color}55`);
      glow.addColorStop(1, `${e.color}00`);
      g.fillStyle = glow;
      g.fillRect(-e.w, -e.h, e.w * 2, e.h * 2);
      // The frame, then the art.
      g.fillStyle = e.color;
      g.fillRect(-e.w / 2 - 2, -e.h / 2 - 2, e.w + 4, e.h + 4);
      if (!cardArt(e.card, e.climax, 0, 0, 1, 1, -e.w / 2, -e.h / 2, e.w, e.h)) {
        g.fillStyle = e.boss ? "#5a1d3a" : "#1f2a4a";
        g.fillRect(-e.w / 2, -e.h / 2, e.w, e.h);
        g.fillStyle = TEXT;
        g.font = `9px ${UI_FONT}`;
        g.textAlign = "center";
        g.fillText(String(e.card.name || "").slice(0, 9), 0, 3);
      }
      if (e.flash > 0) {
        g.fillStyle = "rgba(255, 255, 255, 0.7)";
        g.fillRect(-e.w / 2, -e.h / 2, e.w, e.h);
      }
      // Its level, in a badge on the corner (a climax: CX).
      g.fillStyle = "#0b0a24";
      g.beginPath();
      g.arc(-e.w / 2 + 5, e.h / 2 - 5, 6.5, 0, Math.PI * 2);
      g.fill();
      g.strokeStyle = e.color;
      g.lineWidth = 1.2;
      g.stroke();
      g.fillStyle = e.color;
      g.font = `700 ${e.climax ? 6 : 8}px ${UI_FONT}`;
      g.textAlign = "center";
      g.fillText(e.climax ? "CX" : String(e.level), -e.w / 2 + 5, e.h / 2 - 2.2);
      g.restore();
      // Hits left, for cards that take more than one: pips under a level 1, a bar over a boss.
      if (e.maxHp > 1 && e.mode === "formation") {
        if (e.boss) {
          g.fillStyle = "rgba(0, 0, 0, 0.6)";
          g.fillRect(e.x - e.w / 2, e.y - e.h / 2 - 9, e.w, 4);
          g.fillStyle = e.color;
          g.fillRect(e.x - e.w / 2, e.y - e.h / 2 - 9, e.w * (e.hp / e.maxHp), 4);
        } else {
          for (let i = 0; i < e.maxHp; i++) {
            g.fillStyle = i < e.hp ? e.color : "rgba(255, 255, 255, 0.2)";
            g.fillRect(e.x - 6 + i * 7, e.y + e.h / 2 + 4, 5, 2.5);
          }
        }
      }
    }

    function drawShip() {
      const x = state.ship;
      const y = SHIP_Y;
      const gold = state.double > 0;
      const blink = state.invulnerable > 0 && Math.floor(state.time * 14) % 2 === 0;
      g.save();
      if (blink) g.globalAlpha = 0.35;
      g.translate(x, y);
      g.rotate(state.tilt * 0.18);
      // The engine's flame, flickering.
      const flame = reduced ? 1 : 0.8 + 0.4 * Math.sin(state.time * 40);
      const fire = g.createLinearGradient(0, 8, 0, 8 + 16 * flame);
      fire.addColorStop(0, "rgba(255, 240, 180, 0.95)");
      fire.addColorStop(0.4, "rgba(255, 150, 60, 0.8)");
      fire.addColorStop(1, "rgba(255, 80, 40, 0)");
      g.fillStyle = fire;
      g.beginPath();
      g.moveTo(-5, 8);
      g.lineTo(0, 8 + 16 * flame);
      g.lineTo(5, 8);
      g.fill();
      // Wings, then the hull, then the cockpit.
      const hull = gold ? ["#ffe9a3", "#c99a2e"] : ["#bfe4ff", "#4f7fc0"];
      g.fillStyle = gold ? "#a87a1c" : "#2d4f86";
      g.beginPath();
      g.moveTo(-3, -2);
      g.lineTo(-16, 9);
      g.lineTo(-14, 12);
      g.lineTo(-3, 7);
      g.moveTo(3, -2);
      g.lineTo(16, 9);
      g.lineTo(14, 12);
      g.lineTo(3, 7);
      g.fill();
      const body = g.createLinearGradient(-6, 0, 6, 0);
      body.addColorStop(0, hull[1]);
      body.addColorStop(0.5, hull[0]);
      body.addColorStop(1, hull[1]);
      g.fillStyle = body;
      g.beginPath();
      g.moveTo(0, -16);
      g.lineTo(6, 4);
      g.lineTo(4, 10);
      g.lineTo(-4, 10);
      g.lineTo(-6, 4);
      g.closePath();
      g.fill();
      g.fillStyle = "#1a2a4a";
      g.beginPath();
      g.ellipse(0, -4, 2.4, 5, 0, 0, Math.PI * 2);
      g.fill();
      g.fillStyle = "rgba(160, 230, 255, 0.8)";
      g.beginPath();
      g.ellipse(-0.6, -6, 1, 2.2, 0, 0, Math.PI * 2);
      g.fill();
      g.restore();
    }

    function drawShots() {
      g.save();
      g.globalCompositeOperation = "lighter";
      for (const shot of state.shots) {
        const beam = g.createLinearGradient(0, shot.y - 10, 0, shot.y + 8);
        beam.addColorStop(0, "rgba(255, 245, 200, 1)");
        beam.addColorStop(1, "rgba(255, 190, 70, 0)");
        g.fillStyle = beam;
        g.fillRect(shot.x - 2.5, shot.y - 10, 5, 18);
        g.fillStyle = "rgba(255, 255, 255, 0.9)";
        g.fillRect(shot.x - 0.8, shot.y - 9, 1.6, 10);
      }
      for (const shot of state.enemyShots) {
        const orb = g.createRadialGradient(shot.x, shot.y, 0, shot.x, shot.y, 8);
        orb.addColorStop(0, "rgba(255, 230, 230, 1)");
        orb.addColorStop(0.35, "rgba(255, 80, 110, 0.9)");
        orb.addColorStop(1, "rgba(255, 40, 80, 0)");
        g.fillStyle = orb;
        g.fillRect(shot.x - 8, shot.y - 8, 16, 16);
      }
      g.restore();
    }

    function drawDrops() {
      for (const drop of state.drops) {
        const turn = reduced ? 0 : state.time * 2;
        const color = DROP_COLOR[drop.kind];
        const glow = g.createRadialGradient(drop.x, drop.y, 2, drop.x, drop.y, 18);
        glow.addColorStop(0, `${color}88`);
        glow.addColorStop(1, `${color}00`);
        g.fillStyle = glow;
        g.fillRect(drop.x - 18, drop.y - 18, 36, 36);
        g.fillStyle = "#0b0a24";
        g.strokeStyle = color;
        g.lineWidth = 1.6;
        g.beginPath();
        for (let i = 0; i < 6; i++) {
          const a = turn + (i * Math.PI) / 3;
          g.lineTo(drop.x + Math.cos(a) * 10, drop.y + Math.sin(a) * 10);
        }
        g.closePath();
        g.fill();
        g.stroke();
        g.fillStyle = color;
        g.font = `700 11px ${UI_FONT}`;
        g.textAlign = "center";
        g.fillText(DROP_LABEL[drop.kind], drop.x, drop.y + 4);
      }
    }

    function drawEffects() {
      for (const s of state.shards) {
        g.save();
        g.globalAlpha = clamp(s.life * 1.5, 0, 1);
        g.translate(s.x, s.y);
        g.rotate(s.angle);
        if (!cardArt(s.card, s.climax, s.sx, s.sy, 0.34, 0.34, -s.w / 2, -s.h / 2, s.w, s.h)) {
          g.fillStyle = s.color;
          g.fillRect(-s.w / 2, -s.h / 2, s.w, s.h);
        }
        g.strokeStyle = s.color;
        g.lineWidth = 0.8;
        g.strokeRect(-s.w / 2, -s.h / 2, s.w, s.h);
        g.restore();
      }
      g.save();
      g.globalCompositeOperation = "lighter";
      for (const p of state.particles) {
        g.globalAlpha = clamp(p.life * 1.6, 0, 1);
        g.fillStyle = p.color;
        g.beginPath();
        g.arc(p.x, p.y, p.size / 2, 0, Math.PI * 2);
        g.fill();
      }
      g.restore();
      for (const p of state.pops) {
        g.globalAlpha = clamp((p.life / p.total) * 2, 0, 1);
        g.textAlign = "center";
        g.font = p.big ? `700 24px ${DISPLAY_FONT}` : `700 11px ${UI_FONT}`;
        g.lineWidth = p.big ? 4 : 3;
        g.strokeStyle = "rgba(0, 0, 0, 0.65)";
        g.strokeText(p.text, p.x, p.y);
        g.fillStyle = p.color;
        g.fillText(p.text, p.x, p.y);
      }
      g.globalAlpha = 1;
    }

    function drawBanner() {
      if (state.banner.life <= 0) return;
      const t = state.banner.life;
      const alpha = clamp(Math.min(t, BANNER_TIME - t + 0.25) * 3, 0, 1);
      g.save();
      g.globalAlpha = alpha;
      g.fillStyle = "rgba(5, 6, 26, 0.55)";
      g.fillRect(0, H * 0.44 - 26, W, 44);
      g.strokeStyle = "rgba(212, 175, 55, 0.6)";
      g.lineWidth = 1;
      g.beginPath();
      g.moveTo(0, H * 0.44 - 26);
      g.lineTo(W, H * 0.44 - 26);
      g.moveTo(0, H * 0.44 + 18);
      g.lineTo(W, H * 0.44 + 18);
      g.stroke();
      g.textAlign = "center";
      g.font = `700 24px ${DISPLAY_FONT}`;
      g.fillStyle = "#f4d77a";
      g.fillText(state.banner.text, W / 2, H * 0.44 + 4);
      g.restore();
    }

    function drawDisplay() {
      // Lives, as little ships.
      for (let i = 0; i < Math.max(state.lives, 0); i++) {
        const x = 14 + i * 16;
        g.fillStyle = "#8fd0ff";
        g.beginPath();
        g.moveTo(x, 10);
        g.lineTo(x + 5, 22);
        g.lineTo(x, 19);
        g.lineTo(x - 5, 22);
        g.closePath();
        g.fill();
      }
      // The score towards the target.
      const barW = 110;
      const bx = W - barW - 10;
      const share = clamp(state.score / tune.target, 0, 1);
      g.fillStyle = "rgba(0, 0, 0, 0.5)";
      g.fillRect(bx, 12, barW, 7);
      g.fillStyle = state.reached ? "#7be495" : "#d4af37";
      g.fillRect(bx, 12, barW * share, 7);
      g.strokeStyle = "rgba(255, 255, 255, 0.35)";
      g.lineWidth = 1;
      g.strokeRect(bx, 12, barW, 7);
      g.font = `700 10px ${UI_FONT}`;
      g.textAlign = "right";
      g.fillStyle = TEXT;
      g.fillText(`${state.score} / ${tune.target}`, bx - 6, 19);
      if (state.double > 0) { // the double shot running down
        g.fillStyle = DROP_COLOR.soul;
        g.fillRect(bx, 23, barW * clamp(state.double / DOUBLE_SHOT, 0, 1), 2);
      }
    }

    function draw() {
      g.setTransform(DPR * scale, 0, 0, DPR * scale, 0, 0);
      g.save();
      if (state.shake > 0) g.translate((rnd() - 0.5) * 7 * (state.shake / 0.35), (rnd() - 0.5) * 5 * (state.shake / 0.35));
      drawSpace();
      for (const e of state.enemies) if (!e.dead) drawEnemy(e);
      drawDrops();
      drawShots();
      if (!state.over || state.lives > 0) drawShip();
      drawEffects();
      g.restore();
      if (state.invulnerable > INVULNERABLE - 0.3 && !reduced) { // a red edge when hit
        const edge = g.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 0.75);
        edge.addColorStop(0, "rgba(255, 60, 80, 0)");
        edge.addColorStop(1, "rgba(255, 60, 80, 0.35)");
        g.fillStyle = edge;
        g.fillRect(0, 0, W, H);
      }
      drawBanner();
      drawDisplay();

      if (state.paused) {
        g.fillStyle = "rgba(5, 4, 14, 0.62)";
        g.fillRect(0, 0, W, H);
        g.textAlign = "center";
        g.fillStyle = TEXT;
        g.font = `700 26px ${DISPLAY_FONT}`;
        g.fillText("Paused", W / 2, H / 2);
        g.font = `13px ${UI_FONT}`;
        g.fillStyle = "rgba(246, 241, 231, 0.8)";
        g.fillText("Press P or ❚❚ to carry on", W / 2, H / 2 + 26);
      }
    }

    // ---- Pausing: by P, the pause button, leaving the page, or the tab being hidden ----

    function togglePause() {
      if (state.over || !state.started) return;
      state.paused = !state.paused;
      pause.textContent = state.paused ? "▶" : "❚❚";
      pause.setAttribute("aria-label", state.paused ? "Resume" : "Pause");
      pause.setAttribute("aria-pressed", String(state.paused));
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
      const name = KEYS[event.code];
      if (!name) return;
      input[name] = true;
      event.preventDefault(); // the arrows play the game, not the page
    }

    function onKeyUp(event) {
      const name = KEYS[event.code];
      if (name) input[name] = false;
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
      if (state.started && !state.paused && !state.over) update(dt);
      draw();
      raf = requestAnimationFrame(frame);
    }

    // The shell calls this when the game ends, when playing again, and when choosing another game. The last picture
    // stays on the area (the end screen sits over it, and the area is inert). Safe to call more than once.
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
      state.banner = { text: waveName(state.wave), life: BANNER_TIME }; // the first wave's name, once play starts
      if (window.MinigameAudio) window.MinigameAudio.start("invaders");
    }

    startWave(); // the first formation is in place during the countdown
    state.banner.life = 0;
    raf = requestAnimationFrame(frame);
    // The new frame counts down first (3, 2, 1, Go!); the field is drawn, standing still, until it's done.
    if (ctx.countdown) Promise.resolve(ctx.countdown()).then(go, go);
    else go();
    return { stop };
  }

  window.MinigameGames.invaders = {
    title: "Climax Invaders",
    rule: "Shoot down the cards. Three waves, three lives. Beat the target.",
    about: "Shoot the cards before they reach you. Level 1 cards take two hits, level 2 swoop at you, and level 3 shoot back. A shot-down climax drops a power-up. Three waves, three lives.",
    play: startInvaders,
  };
})();
