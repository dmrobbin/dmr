// The battle view (from play.js): while an attack plays out, a band across the screen shows the two characters in it,
// sized by their power, with their power and soul. The trigger check turns over between them and its soul icons fly into
// the attacker; a backup slides in beside the defender; the damage's souls fire at the defender's clock (shattering on a
// climax's shield if it's cancelled); and in a front attack the two clash, the stronger knocking the other back reversed,
// harder the bigger the gap. Side attacks show the defender greyed (its level taking soul away), direct ones no defender.
//
// It reads the board as play.js gets it: update(lastBoard) once each board is drawn, before tableFx. Everything it
// shows goes on a queue of timed steps, so a board that arrives with several things done at once (a CPU's attack can
// go by between two polls) still plays them in order. What it can't see live it plays from board.last_attack, the
// server's record of the attack once it's over (game.record_attack). The table's own show waits for it: damageLead(owner)
// is how long the clock's cards should wait to turn over (until the souls land), battleClaim(id) how long the battle's
// reversed card should wait (until the clash knocks it over), and claimsCheck(id) whether it shows the trigger check
// itself. Nothing on it can be clicked: the board under it and the prompts below it stay in use.
(function () {
  "use strict";

  const STEP = { open: 450, trigger: 1500, counter: 1100, damageBase: 650, soulGap: 110, clash: 1500, close: 450 };
  const MAX_SOULS = 10; // flying at once; more damage than that still fires 10
  const MIN_SCALE = 0.5; // the weaker card's size, at the least, beside the stronger one's

  function create(app) {
    const { root, cards, esc, climaxColor, reducedMotion, SOUL_ICON } = app;

    const band = document.createElement("div");
    band.className = "battle-band";
    band.hidden = true;
    band.setAttribute("aria-hidden", "true"); // the log and the attack panel say what happened; this only shows it
    document.body.appendChild(band);

    let seen = null; // {game, ability, record, battle}: what's been taken in, so reopening the page doesn't replay it
    let plan = null; // the attack the queue is on: {key, uid, owner, trigger, counters, damage, clash, closed, speed}
    let shown = null; // the attack the band shows: {key, left, right} fighters, as the steps have left them
    let queueEnds = 0; // when the last queued step finishes (performance.now())
    let leads = { me: 0, opponent: 0 };
    const claims = {}; // battle id -> when its clash knocks the loser over (performance.now())
    const checks = new Set(); // ability_show ids of trigger checks shown here
    const negatedShown = { me: 0, opponent: 0 }; // each side's cancel count as of the last cancel shown here

    const now = () => performance.now();
    const pause = () => !app.animations();

    // A step on the queue: it starts when the one before it ends. `ms` at normal speed; returns when it starts (ms from now).
    function enqueue(ms, run) {
      const t = now();
      const start = Math.max(t, queueEnds);
      const length = Math.round(ms / ((plan && plan.speed) || 1));
      queueEnds = start + length;
      setTimeout(() => {
        try {
          run(length);
        } catch (e) {
          console.error(e);
        }
      }, start - t);
      return start - t;
    }

    // --- Reading the board ------------------------------------------------------------------------------------

    const stageOf = (board, owner) => (board[owner] || {}).stage || {};
    const findOnStage = (board, owner, uid) => Object.values(stageOf(board, owner)).find((c) => c && c.uid === uid) || null;
    const statOf = (board, uid, stat, pk) => {
      const live = (board.stats || {})[uid];
      if (live && typeof live[stat] === "number") return live[stat];
      return Number((cards[pk] || {})[stat]) || 0;
    };

    // A fighter: one side of the band. `card` is its board card if we have it (for face-down, position), `pk` its picture.
    function fighter(board, owner, role, uid, pk, extraPower = 0) {
      const card = uid ? findOnStage(board, owner, uid) : null;
      const shownPk = card ? card.card : pk;
      return {
        owner, role, uid, pk: shownPk || null,
        power: uid ? statOf(board, uid, "power", shownPk) + extraPower : 0,
        soul: uid ? statOf(board, uid, "soul", shownPk) : 0,
        level: uid ? statOf(board, uid, "level", shownPk) : 0,
        backups: [],
      };
    }

    // The attack in progress, or the record of one, as the two fighters and what kind of attack it is.
    function sides(board, { uid, card, kind, target, defender, defender_card, backup = 0 }) {
      const attackerOwner = board.my_turn ? "me" : "opponent";
      const defenderOwner = attackerOwner === "me" ? "opponent" : "me";
      const defUid = defender || (target ? (stageOf(board, defenderOwner)[target] || {}).uid : null) || null;
      const attacker = fighter(board, attackerOwner, "attacker", uid, card);
      const def = kind === "direct" || !defUid ? fighter(board, defenderOwner, "empty", null, null) : fighter(board, defenderOwner, "defender", defUid, defender_card, backup);
      return { kind, attackerOwner, defenderOwner, attacker, defender: def };
    }

    const keyOf = (turn, number) => `${turn}:${number}`;

    function update(last) {
      const board = app.board();
      leads = { me: 0, opponent: 0 };
      if (!board) return;
      const ability = board.ability_show || {};
      const record = board.last_attack || null;
      const battle = board.battle || null;
      placeBand(); // a prompt may have come up or gone
      if (!seen || seen.game !== board.game_number || !last) {
        // The first board (or a new game): what's already happened was before we looked.
        seen = { game: board.game_number, ability: ability.id || null, record: record && record.id, battle: battle && battle.id };
        plan = null;
        close(0);
        // Opened mid-attack (a reload, a page come back to): the attack as it stands, from here on.
        const live = board.attack && board.attack.uid && board.attack.step !== "declare" ? board.attack : null;
        if (live && !pause() && !board.rps) {
          begin(keyOf(board.turn_number, board.attacks), board, live);
          plan.trigger = Boolean(live.checked_cards && live.checked_cards.length);
          plan.counters = (live.counter_cards || []).length;
          plan.damage = Boolean(live.dealt);
        }
        return;
      }
      if (pause() || board.rps) {
        seen = { game: board.game_number, ability: ability.id || null, record: record && record.id, battle: battle && battle.id };
        if (shown) close(0);
        plan = null;
        return;
      }
      const attack = board.attack && board.attack.uid && board.attack.step !== "declare" ? board.attack : null;
      const freshRecord = record && record.id !== seen.record ? record : null;
      seen.record = record ? record.id : null;

      // Which attack each piece belongs to: the one in progress (turn, attacks this turn), or the one just recorded.
      const liveKey = attack ? keyOf(board.turn_number, board.attacks) : null;
      const recordKey = freshRecord ? keyOf(freshRecord.turn, freshRecord.number) : null;

      // The recorded attack first (it came before any attack in progress), then the live one.
      if (freshRecord) {
        const info = { uid: freshRecord.attacker, card: freshRecord.card, kind: freshRecord.kind, target: freshRecord.target,
          defender: freshRecord.defender, defender_card: freshRecord.defender_card };
        begin(recordKey, board, info);
        trigger(freshRecord.checked || []);
        counters(board, freshRecord.counter_cards || []);
        damage(board, last, freshRecord);
        clash(board, battle, freshRecord.battle);
        finish();
      }
      if (attack) {
        begin(liveKey, board, { ...attack, defender: attack.defender, defender_card: attack.defender_card });
        if (ability.id && ability.id !== seen.ability && ability.check && !ability.label) {
          trigger(ability.check, ability.id);
        }
        counters(board, attack.counter_cards || []);
        if (attack.dealt) damage(board, last, attack);
      } else if (plan && !plan.closed && !freshRecord) {
        finish(); // the attack ended some other way (its attacker left the stage, the phase moved on)
      }
      seen.ability = ability.id || null;
      seen.battle = battle ? battle.id : null;
    }

    // An attack starts on the queue (if it isn't the one it's on): the band opens with its two fighters.
    function begin(key, board, info) {
      if (plan && plan.key === key) return;
      if (plan && !plan.closed) finish();
      const behind = Math.max(0, queueEnds - now());
      plan = { key, uid: info.uid, trigger: false, counters: 0, damage: false, clash: false, closed: false, speed: behind > 2500 ? 2 : 1 };
      const fight = sides(board, info);
      plan.attackerOwner = fight.attackerOwner;
      plan.defenderOwner = fight.defenderOwner;
      enqueue(STEP.open, () => open(key, fight));
    }

    function trigger(pks, abilityId = null) {
      if (!plan || plan.trigger || !pks.length) return;
      plan.trigger = true;
      if (abilityId) checks.add(abilityId);
      const souls = pks.reduce((n, pk) => n + ((cards[pk] || {}).trigger || "").toLowerCase().split(/\s+/).filter((i) => i === "soul").length, 0);
      enqueue(STEP.trigger, (ms) => showTrigger(pks, souls, ms));
    }

    function counters(board, list) {
      if (!plan) return;
      for (const played of list.slice(plan.counters)) {
        plan.counters += 1;
        enqueue(STEP.counter, (ms) => showCounter(played, ms));
      }
    }

    // The damage: as many souls as cards it put in the defender's clock (or the attack's damage, if cancelled).
    function damage(board, last, attack) {
      if (!plan || plan.damage) return;
      const owner = plan.defenderOwner;
      const was = last[owner];
      const is = board[owner];
      if (!was || !is) return;
      const negated = (is.negated || 0) > (was.negated || 0);
      const hit = Math.max(0, (is.damage_taken || 0) - (was.damage_taken || 0));
      if (!negated && !hit) return;
      plan.damage = true;
      const amount = negated ? Math.max(1, attack.damage ?? attack.soul ?? 1) : hit;
      const cancel = negated ? { color: climaxColor(cards[is.negated_card]), name: (cards[is.negated_card] || {}).name || "" } : null;
      if (negated) negatedShown[owner] = is.negated || 0; // the shield shows it, not "Damage Negated!"
      const souls = Math.min(MAX_SOULS, amount);
      const length = STEP.damageBase + STEP.soulGap * (souls - 1);
      const start = enqueue(length, (ms) => fireSouls(owner, souls, cancel, ms));
      leads[owner] = start + length * 0.75; // the clock's cards turn over as the souls land
    }

    function clash(board, battle, battleId) {
      if (!plan || plan.clash || !battle || battle.id !== battleId) return;
      plan.clash = true;
      const start = enqueue(STEP.clash, (ms) => showClash(battle, ms));
      claims[battle.id] = now() + start + STEP.clash * 0.45 / plan.speed;
    }

    function finish() {
      if (!plan || plan.closed) return;
      plan.closed = true;
      const key = plan.key;
      enqueue(STEP.close, (ms) => { if (shown && shown.key === key) close(ms); });
    }

    // --- Drawing ----------------------------------------------------------------------------------------------

    function soulsHtml(n) {
      return n > 4 ? `${SOUL_ICON}<b>×${n}</b>` : SOUL_ICON.repeat(Math.max(0, n));
    }

    function fighterHtml(f, kind) {
      const info = f.pk ? cards[f.pk] : null;
      if (f.role === "empty") {
        return `<div class="bv-fighter bv-empty" data-side="${f.owner}"><div class="bv-card-wrap"><div class="bv-card"><span class="bv-slot">No defender</span></div></div>
          <p class="bv-role">Direct attack</p></div>`;
      }
      const face = info ? `<img src="${esc(info.image)}" alt="">` : '<span class="pcard-back"></span>';
      const side = kind === "side" && f.role === "defender";
      return `<div class="bv-fighter bv-${f.role}${side ? " bv-bystander" : ""}" data-side="${f.owner}">
        <div class="bv-card-wrap"><div class="bv-card">${face}</div><div class="bv-backups"></div></div>
        <div class="bv-stats">
          <span class="bv-power" data-power="${f.power}">${f.power}</span>
          <span class="bv-souls">${soulsHtml(f.soul)}</span>
        </div>
        <p class="bv-role">${f.role === "attacker" ? "Attacking" : side ? `Level ${f.level}: −${f.level} soul` : "Defending"}</p>
      </div>`;
    }

    // Each card's size from its power: its area in proportion (so the width goes with the square root), never
    // smaller than MIN_SCALE of the stronger one's.
    function sizeFighters() {
      if (!shown) return;
      const fighters = [shown.left, shown.right].filter((f) => f.role === "attacker" || (f.role === "defender" && shown.kind === "front"));
      const top = Math.max(1, ...fighters.map((f) => f.power));
      for (const f of [shown.left, shown.right]) {
        const el = band.querySelector(`.bv-fighter[data-side="${f.owner}"]`);
        if (!el) continue;
        const scale = fighters.includes(f) ? Math.max(MIN_SCALE, Math.sqrt(Math.max(0, f.power) / top)) : 0.7;
        el.style.setProperty("--bv-scale", scale.toFixed(3));
      }
    }

    // Where the band sits: over the middle of the screen (the stages), so both clocks stay in sight for the souls; or,
    // while a prompt is up (the counter step, a trigger's choice), at the top, with the prompt below it.
    function placeBand() {
      if (band.hidden) return;
      const header = document.querySelector(".site-header");
      const pinned = header && getComputedStyle(header).position !== "static";
      const below = (pinned ? Math.max(0, header.getBoundingClientRect().bottom) : 0) + 8;
      const prompt = document.querySelector(".play-modal:not([hidden])");
      const height = band.getBoundingClientRect().height;
      const top = prompt ? below : Math.max(below, (window.innerHeight - height) / 2);
      band.style.top = `${Math.round(top)}px`;
      document.documentElement.style.setProperty("--battle-bottom", `${Math.round(top + height)}px`);
    }

    function open(key, fight) {
      // Ours on the left, theirs on the right, whichever is attacking.
      const left = fight.attackerOwner === "me" ? fight.attacker : fight.defender;
      const right = fight.attackerOwner === "me" ? fight.defender : fight.attacker;
      shown = { key, kind: fight.kind, left, right, attacker: fight.attacker, defender: fight.defender };
      const kinds = { front: "Front attack", side: "Side attack", direct: "Direct attack" };
      band.className = `battle-band bv-${fight.kind}${reducedMotion ? " bv-still" : ""}`;
      band.innerHTML = `<p class="bv-title">⚔ ${kinds[fight.kind] || "Attack"}</p>
        <div class="bv-arena">
          ${fighterHtml(left, fight.kind)}
          <div class="bv-center"><span class="bv-vs">VS</span><div class="bv-check"></div></div>
          ${fighterHtml(right, fight.kind)}
        </div>`;
      band.hidden = false;
      band.classList.remove("bv-leaving");
      void band.offsetWidth;
      band.classList.add("bv-entering");
      root.classList.add("battle-open");
      placeBand();
      sizeFighters();
    }

    function close(ms) {
      shown = null;
      if (band.hidden) return;
      const done = () => {
        if (shown) return; // another attack opened meanwhile
        band.hidden = true;
        band.innerHTML = "";
        root.classList.remove("battle-open");
      };
      if (!ms || reducedMotion) return done();
      band.classList.remove("bv-entering");
      band.classList.add("bv-leaving");
      setTimeout(done, ms);
    }

    const fighterEl = (f) => (f ? band.querySelector(`.bv-fighter[data-side="${f.owner}"]`) : null);

    // A number counting from what it shows to `to`.
    function countTo(el, to, ms) {
      if (!el) return;
      const from = Number(el.dataset.power ?? el.textContent) || 0;
      el.dataset.power = String(to);
      if (reducedMotion || from === to) {
        el.textContent = String(to);
        return;
      }
      const began = now();
      (function tick() {
        const k = Math.min(1, (now() - began) / ms);
        el.textContent = String(Math.round((from + (to - from) * k) / 50) * 50);
        if (k < 1 && el.isConnected) requestAnimationFrame(tick);
        else el.textContent = String(to);
      })();
    }

    // Something fixed on the screen at a point, gone once its animations are done (or after `ms`).
    function fxAt(x, y, className, html, ms) {
      const el = document.createElement("div");
      el.className = className;
      el.setAttribute("aria-hidden", "true");
      el.innerHTML = html;
      Object.assign(el.style, { left: `${x}px`, top: `${y}px` });
      document.body.appendChild(el);
      setTimeout(() => el.remove(), ms);
      return el;
    }

    const centerOf = (el) => { const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; };

    // The trigger check: the card turns over in the middle, its icons show, and each soul icon flies into the attacker.
    function showTrigger(pks, souls, ms) {
      if (!shown) return;
      const spot = band.querySelector(".bv-check");
      const vs = band.querySelector(".bv-vs");
      if (!spot) return;
      vs.classList.add("bv-dim");
      spot.innerHTML = pks.map((pk) => {
        const info = cards[pk] || {};
        const icons = (info.trigger || "").toLowerCase().split(/\s+/).filter(Boolean);
        return `<div class="bv-check-card"><div class="bv-flip"><span class="pcard-back"></span>${info.image ? `<img src="${esc(info.image)}" alt="">` : ""}</div>
          <span class="bv-icons">${icons.map((i) => `<span class="bv-icon bv-icon-${esc(i)}">${i === "soul" ? SOUL_ICON : esc(i)}</span>`).join("") || '<span class="bv-icon bv-none">no trigger</span>'}</span></div>`;
      }).join("");
      const attacker = fighterEl(shown.attacker);
      const target = attacker && attacker.querySelector(".bv-souls");
      if (souls && target && !reducedMotion) {
        setTimeout(() => {
          const from = centerOf(spot);
          const to = centerOf(target);
          for (let n = 0; n < souls; n += 1) {
            const s = fxAt(from.x, from.y, "bv-soul-fly", SOUL_ICON, 900);
            s.animate([{ transform: "translate(-50%, -50%) scale(1.4)", opacity: 0 }, { transform: "translate(-50%, -50%) scale(1.6)", opacity: 1, offset: 0.2 },
              { transform: `translate(calc(-50% + ${to.x - from.x}px), calc(-50% + ${to.y - from.y}px)) scale(.8)`, opacity: 1 }],
            { duration: 520, delay: n * 120, easing: "cubic-bezier(.5, 0, .3, 1)", fill: "both" });
          }
        }, ms * 0.45);
      }
      setTimeout(() => {
        if (!shown || !attacker) return;
        shown.attacker.soul += souls;
        if (souls) {
          attacker.querySelector(".bv-souls").innerHTML = soulsHtml(shown.attacker.soul);
          attacker.querySelector(".bv-souls").classList.add("bv-flare");
        }
      }, ms * 0.45 + 520 + Math.max(0, souls - 1) * 120);
      setTimeout(() => { spot.classList.add("bv-fade"); vs.classList.remove("bv-dim"); }, ms * 0.85);
      setTimeout(() => { spot.innerHTML = ""; spot.classList.remove("bv-fade"); }, ms);
    }

    // A counter played: the card slides in beside the defender, its backup counted onto the defender's power.
    function showCounter(played, ms) {
      if (!shown || !shown.defender || shown.defender.role !== "defender") return;
      const el = fighterEl(shown.defender);
      if (!el) return;
      const info = cards[played.card] || {};
      const slot = el.querySelector(".bv-backups");
      slot.insertAdjacentHTML("beforeend", `<div class="bv-backup">${info.image ? `<img src="${esc(info.image)}" alt="">` : '<span class="pcard-back"></span>'}
        ${played.power ? `<span class="bv-plus">+${played.power}</span>` : ""}</div>`);
      if (played.power) {
        shown.defender.power += played.power;
        setTimeout(() => {
          countTo(el.querySelector(".bv-power"), shown ? shown.defender.power : 0, ms * 0.4);
          sizeFighters();
        }, ms * 0.35);
      }
    }

    // Where the souls go: the defender's clock on the board, or, out of sight, off that side of the screen.
    function clockPoint(owner) {
      const clock = document.querySelector(`.mat-${owner} .zone-clock`);
      if (clock && clock.getClientRects().length) {
        const r = clock.getBoundingClientRect();
        if (r.bottom > 0 && r.top < window.innerHeight) return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      }
      return { x: window.innerWidth / 2, y: owner === "me" ? window.innerHeight + 40 : -40 };
    }

    // The damage: souls fire one after another from the attacker at the defender's clock, each a hit as it lands,
    // or, cancelled, they break on a shield of the cancelling climax's colour.
    function fireSouls(owner, count, cancel, ms) {
      placeBand();
      const attacker = shown && fighterEl(shown.attacker);
      const from = attacker ? centerOf(attacker.querySelector(".bv-card")) : { x: window.innerWidth / 2, y: 200 };
      const to = clockPoint(owner);
      if (attacker) attacker.classList.add("bv-firing");
      setTimeout(() => attacker && attacker.classList.remove("bv-firing"), ms);
      const FLIGHT = Math.min(520, ms - STEP.soulGap * (count - 1) - 80);
      const shieldColor = cancel && cancel.color;
      if (cancel) {
        // Kept inside the screen, so its name can be read even when the clock it guards is out of sight.
        const at = { x: Math.min(window.innerWidth - 80, Math.max(80, to.x)), y: Math.min(window.innerHeight - 110, Math.max(110, to.y)) }; // room for its name
        const shield = fxAt(at.x, at.y, "bv-shield", `<span class="bv-shield-name">${esc(cancel.name)}<b>Cancelled!</b></span>`, ms + 1400);
        shield.style.setProperty("--shield", shieldColor);
        if (at.y < band.getBoundingClientRect().top) shield.classList.add("bv-shield-above"); // its name above it, clear of the band
        setTimeout(() => shield.classList.add("bv-shield-break"), FLIGHT + STEP.soulGap * (count - 1) + 450);
        to.x = at.x;
        to.y = at.y;
      }
      if (reducedMotion) return;
      // A curve, bowing up and out, so they read as fired rather than slid.
      const bow = { x: (to.x - from.x) * 0.15, y: -Math.min(140, Math.abs(to.y - from.y) * 0.35) - 40 };
      for (let n = 0; n < count; n += 1) {
        const jitter = (n % 2 ? 1 : -1) * (8 + (n * 13) % 22);
        const mid = { x: (from.x + to.x) / 2 + bow.x + jitter, y: (from.y + to.y) / 2 + bow.y };
        const frames = [];
        for (let i = 0; i <= 10; i += 1) {
          const t = i / 10;
          const x = (1 - t) * (1 - t) * from.x + 2 * (1 - t) * t * mid.x + t * t * to.x;
          const y = (1 - t) * (1 - t) * from.y + 2 * (1 - t) * t * mid.y + t * t * to.y;
          frames.push({ transform: `translate(calc(-50% + ${x - from.x}px), calc(-50% + ${y - from.y}px)) scale(${1.3 - t * 0.4})`, opacity: i === 0 ? 0 : 1 });
        }
        const s = fxAt(from.x, from.y, "bv-soul-shot", SOUL_ICON, ms + 600);
        s.animate(frames, { duration: FLIGHT, delay: n * STEP.soulGap, easing: "cubic-bezier(.45, 0, .7, 1)", fill: "both" })
          .finished.then(() => {
            s.remove();
            if (shieldColor) shatter(to, shieldColor);
            else fxAt(to.x, to.y, "bv-soul-hit", "", 600);
          }).catch(() => s.remove());
      }
    }

    // A soul breaking on the shield: shards flying off it.
    function shatter(at, color) {
      for (let i = 0; i < 6; i += 1) {
        const angle = (Math.PI * 2 * i) / 6 + Math.random() * 0.6;
        const d = 26 + Math.random() * 22;
        const shard = fxAt(at.x, at.y, "bv-shard", "", 700);
        shard.style.background = color;
        shard.animate([{ transform: "translate(-50%, -50%) rotate(0deg)", opacity: 1 },
          { transform: `translate(calc(-50% + ${Math.cos(angle) * d}px), calc(-50% + ${Math.sin(angle) * d}px)) rotate(${120 + i * 40}deg)`, opacity: 0 }],
        { duration: 560, easing: "cubic-bezier(.2, .7, .3, 1)", fill: "both" });
      }
    }

    // The clash (a front attack's battle): the two rush in and meet in a flash; the stronger drives on and the weaker
    // is knocked back and turned over, reversed. The bigger the gap in power, the harder the hit, the further the
    // knockback and the bigger the flash. A tie knocks both back.
    function showClash(battle, ms) {
      if (!shown || shown.kind !== "front") return;
      const [mine, theirs] = battle.power; // the attacker's, the defender's (with its backup)
      const atk = fighterEl(shown.attacker);
      const def = fighterEl(shown.defender);
      if (!atk || !def) return;
      countTo(def.querySelector(".bv-power"), theirs, 250);
      countTo(atk.querySelector(".bv-power"), mine, 250);
      shown.attacker.power = mine;
      shown.defender.power = theirs;
      sizeFighters();
      const gap = Math.abs(mine - theirs) / Math.max(1, mine, theirs);
      const k = Math.min(1, gap * 2.2); // 0: evenly matched .. 1: a rout (45% apart or more)
      const reversed = new Set(battle.reversed || []);
      const lost = (f) => reversed.has(f.uid);
      // Which way each rushes: towards the middle of the band.
      const dir = (el) => (centerOf(el).x < centerOf(band).x ? 1 : -1);
      const meet = ms * 0.4;
      const center = centerOf(band.querySelector(".bv-center"));
      if (reducedMotion) {
        setTimeout(() => {
          for (const [el, f] of [[atk, shown.attacker], [def, shown.defender]]) if (lost(f)) el.classList.add("bv-reversed");
        }, meet);
        return;
      }
      for (const [el, f] of [[atk, shown.attacker], [def, shown.defender]]) {
        const d = dir(el);
        const reach = Math.abs(center.x - centerOf(el).x) - el.getBoundingClientRect().width * 0.45;
        const knock = 30 + 110 * k;
        const card = el.querySelector(".bv-card-wrap");
        const frames = [
          { transform: "translateX(0) rotate(0deg)" },
          { transform: `translateX(${-d * 18}px) rotate(0deg)`, offset: 0.22 }, // winding up
          { transform: `translateX(${d * reach}px) rotate(0deg)`, offset: 0.4, easing: "cubic-bezier(.6, 0, 1, 1)" }, // the hit
        ];
        if (lost(f)) {
          frames.push({ transform: `translateX(${d * (reach - knock)}px) rotate(${-d * (100 + 80 * k)}deg)`, offset: 0.62 });
          frames.push({ transform: "translateX(0) rotate(180deg)" });
        } else {
          frames.push({ transform: `translateX(${d * (reach * 0.55)}px) rotate(0deg)`, offset: 0.62 }); // driving on through
          frames.push({ transform: "translateX(0) rotate(0deg)" });
        }
        card.animate(frames, { duration: ms, easing: "cubic-bezier(.3, .7, .3, 1)", fill: "forwards" });
        if (lost(f)) setTimeout(() => el.classList.add("bv-reversed"), ms * 0.62);
      }
      setTimeout(() => {
        const burst = fxAt(center.x, center.y, "bv-impact", '<span class="bv-ring"></span><span class="bv-ring bv-ring-late"></span><span class="bv-flash"></span>', 1200);
        burst.style.setProperty("--bv-k", k.toFixed(2));
        const shake = 3 + 12 * k;
        // `transform`, not `translate`: the band's own translate centres it.
        band.animate([{ transform: "translate(0, 0)" }, { transform: `translate(${-shake}px, ${shake * 0.4}px)` }, { transform: `translate(${shake * 0.8}px, ${-shake * 0.3}px)` },
          { transform: `translate(${-shake * 0.4}px, 0)` }, { transform: "translate(0, 0)" }], { duration: 260 + 200 * k, easing: "ease-out" });
      }, meet);
    }

    return {
      update,
      damageLead: (owner) => leads[owner] || 0,
      battleClaim: (id) => (id in claims ? Math.max(0, claims[id] - now()) : null),
      claimsCheck: (id) => checks.has(id),
      claimsNegated: (owner, count) => negatedShown[owner] >= count,
      isOpen: () => !band.hidden,
    };
  }

  window.WeissBattle = { create };
})();
