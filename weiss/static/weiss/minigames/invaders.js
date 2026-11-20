/* Climax Invaders (docs/minigames-plan.md, "Two games (Sam 2)"): a ship at the bottom shoots up at a formation of card
   pictures. Level 0 cards are simple, level 1 take two hits, level 2 swoop down at the ship, and level 3 are bosses that
   shoot back. A shot-down climax drops a power-up by its trigger: soul gives a double shot for a while, draw an extra
   life, and the others a bonus. Three waves and three lives; the CPU's target score is what to beat. Registers in
   window.MinigameGames and is started by the shell (shell.js), which gives the ctx: area, cards, cpu, difficulty,
   random, say, score, status and end. The game stops itself when it ends, and its stop() is safe to call again. */
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

    // ---- The page: the canvas and the touch buttons ----
    const board = el("div", "inv-board");
    const canvas = el("canvas", "inv-canvas");
    canvas.width = W * DPR;
    canvas.height = H * DPR;
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Climax Invaders. Left and right to move, P to pause. The ship fires by itself.");
    const g = canvas.getContext("2d");
    g.setTransform(DPR, 0, 0, DPR, 0, 0);

    const touch = el("div", "inv-touch");
    const touching = { left: false, right: false };
    const button = (name, label) => {
      const node = el("button", "inv-key", label);
      node.type = "button";
      node.setAttribute("aria-label", name);
      return node;
    };
    const left = button("Move left", "◀");
    const right = button("Move right", "▶");
    const pause = button("Pause", "Pause");
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
    touch.append(left, right, pause);
    board.append(canvas, touch, el("p", "inv-hint small", "Arrows or A and D to move · P to pause · the ship fires by itself"));
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
    const stars = Array.from({ length: 40 }, () => ({ x: rnd() * W, y: rnd() * H, s: 0.4 + rnd() * 1.2, v: 12 + rnd() * 30 }));
    const state = {
      ship: W / 2, lives: LIVES, score: 0, wave: 0, paused: false, over: false,
      cooldown: 0, invulnerable: 0, double: 0, intermission: 0, swoopIn: tune.swoopEvery, time: 0,
      enemies: [], shots: [], enemyShots: [], drops: [], particles: [],
      idle: 0, // seconds since the last kill: a formation that's left alone widens and drifts down, so a wave ends
      drift: 0, // how far down the formation has come
    };
    const input = { left: false, right: false };
    const KEYS = { ArrowLeft: "left", KeyA: "left", ArrowRight: "right", KeyD: "right" };

    function status() {
      ctx.status(`Wave ${Math.min(state.wave + 1, WAVES)} of ${WAVES} · ${"♥".repeat(state.lives)}`);
    }

    function addScore(points) {
      state.score += points;
      ctx.score(state.score, tune.target); // the CPU's line is their target: passing it is the lead changing
    }

    function burst(x, y, count, color, speed = 3) {
      const n = reduced ? Math.ceil(count / 3) : count;
      for (let i = 0; i < n && state.particles.length < 160; i++) {
        const angle = rnd() * Math.PI * 2;
        const v = (0.5 + rnd()) * speed * 40;
        state.particles.push({ x, y, vx: Math.cos(angle) * v, vy: Math.sin(angle) * v, life: 0.5 + rnd() * 0.4, color });
      }
    }

    // The end: the game runs until the last wave is cleared or the lives run out. Then the score decides: at or above the
    // target wins, below it loses. Reaching the target mid-run doesn't end it. The shell says the CPU's line and calls stop().
    function finish(result) {
      if (state.over) return;
      state.over = true;
      sfx(result);
      ctx.end(result);
    }

    function loseLife() {
      if (state.invulnerable > 0 || state.over) return;
      state.lives -= 1;
      state.invulnerable = INVULNERABLE;
      sfx("hit");
      burst(state.ship, SHIP_Y, 18, "#ff8a7a", 3);
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
      ctx.status(`Wave ${state.wave + 1} cleared`);
    }

    // ---- Hits and power-ups ----

    function hitEnemy(e) {
      e.hp -= 1;
      e.flash = 0.12;
      sfx("hit");
      if (e.hp > 0) {
        burst(e.x, e.y, 4, "#ffffff", 2);
        return;
      }
      e.dead = true;
      state.idle = 0;
      addScore(e.climax ? CLIMAX_POINTS : POINTS[e.level]);
      burst(e.x, e.y, 16, e.boss ? "#ff7a9a" : "#ffd36b");
      if (e.drop) state.drops.push({ x: e.x, y: e.y, kind: e.drop, taken: false });
    }

    function collect(kind) {
      sfx("pickup");
      if (kind === "soul") {
        state.double = DOUBLE_SHOT;
      } else if (kind === "draw") {
        state.lives = Math.min(MAX_LIVES, state.lives + 1);
        status();
      } else {
        addScore(BONUS_POINTS);
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

    // ---- Drawing ----

    function drawEnemy(e) {
      const img = e.card.image ? images.get(e.card.image) : null;
      const ready = Boolean(img && img.complete && img.naturalWidth > 0);
      g.save();
      g.globalAlpha = e.hp < e.maxHp ? 0.7 : 1; // a hit one is a little faded
      if (ready && e.climax) {
        g.drawImage(img, e.x - e.w / 2, e.y - e.h / 2, e.w, e.h); // climaxes are printed sideways: the whole picture
      } else if (ready) {
        // A character's art: the picture cropped to the artwork, not the frame around it.
        g.drawImage(img, img.naturalWidth * 0.08, img.naturalHeight * 0.12, img.naturalWidth * 0.84, img.naturalHeight * 0.5,
          e.x - e.w / 2, e.y - e.h / 2, e.w, e.h);
      } else {
        g.fillStyle = e.boss ? "#5a1d3a" : "#1f2a4a";
        g.fillRect(e.x - e.w / 2, e.y - e.h / 2, e.w, e.h);
        g.fillStyle = "#f3efe7";
        g.font = "10px sans-serif";
        g.textAlign = "center";
        g.fillText(String(e.card.name || "").slice(0, 9), e.x, e.y + 3);
      }
      if (e.flash > 0) {
        g.fillStyle = "rgba(255,255,255,0.6)";
        g.fillRect(e.x - e.w / 2, e.y - e.h / 2, e.w, e.h);
      }
      if (e.boss) {
        g.strokeStyle = "#ff7a9a";
        g.lineWidth = 2;
        g.strokeRect(e.x - e.w / 2 - 2, e.y - e.h / 2 - 2, e.w + 4, e.h + 4);
      }
      g.restore();
    }

    function draw() {
      g.fillStyle = "#070812";
      g.fillRect(0, 0, W, H);
      g.fillStyle = "#cfd8ff";
      for (const star of stars) g.fillRect(star.x, star.y, star.s, star.s);

      for (const e of state.enemies) if (!e.dead) drawEnemy(e);

      g.fillStyle = "#ff6b6b";
      for (const shot of state.enemyShots) {
        g.beginPath();
        g.arc(shot.x, shot.y, 4, 0, Math.PI * 2);
        g.fill();
      }
      g.fillStyle = "#ffe27a";
      for (const shot of state.shots) g.fillRect(shot.x - 1.5, shot.y - 6, 3, 12);

      g.textAlign = "center";
      g.font = "bold 11px sans-serif";
      for (const drop of state.drops) {
        g.fillStyle = DROP_COLOR[drop.kind];
        g.beginPath();
        g.arc(drop.x, drop.y, 9, 0, Math.PI * 2);
        g.fill();
        g.fillStyle = "#070812";
        g.fillText(DROP_LABEL[drop.kind], drop.x, drop.y + 4);
      }

      const blink = state.invulnerable > 0 && Math.floor(state.time * 12) % 2 === 0;
      if (!blink) {
        g.fillStyle = state.double > 0 ? "#ffd36b" : "#8fd0ff";
        g.beginPath();
        g.moveTo(state.ship, SHIP_Y - 14);
        g.lineTo(state.ship - 14, SHIP_Y + 10);
        g.lineTo(state.ship + 14, SHIP_Y + 10);
        g.closePath();
        g.fill();
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
      g.fillText(`Score ${state.score}`, 8, 18);
      if (state.double > 0) {
        g.font = "11px sans-serif";
        g.fillStyle = "#ffd36b";
        g.fillText(`Double shot ${Math.ceil(state.double)}s`, 8, 34);
      }

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
      pause.textContent = state.paused ? "Resume" : "Pause";
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
      if (!state.paused && !state.over) update(dt);
      draw();
      raf = requestAnimationFrame(frame);
    }

    // The shell calls this when the game ends, when playing again, and when choosing another game. The last picture
    // stays on the area (the end screen sits over it, and the area is inert). Safe to call more than once.
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

    if (window.MinigameAudio) window.MinigameAudio.start("invaders");
    startWave();
    raf = requestAnimationFrame(frame);
    return { stop };
  }

  window.MinigameGames.invaders = {
    title: "Climax Invaders",
    about: "Shoot the cards before they reach you. Level 1 cards take two hits, level 2 swoop at you, and level 3 shoot back. A shot-down climax drops a power-up. Three waves, three lives.",
    play: startInvaders,
  };
})();
