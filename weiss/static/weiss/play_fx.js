// The game board's show (from play.js): damage turning over a card at a time, the battle's clash and power duel, stat
// changes floating off the cards, the turn banner, an ability's trails to its targets, and the table's mood. All of it
// worked out from the difference between the last board and this one, after it's drawn.
//
// play.js makes one with WeissTableFx.create(app), once everything in `app` exists, and calls tableFx(lastBoard) after
// drawing each board, setTableMood() as it draws, negatedWait(owner) before showing "Damage Negated!", and
// noteOwnDamage() when its own "Take damage" flies cards in. `app` gives what it reads from the page: the live board,
// avatars, animations setting and music as functions, and play.js's helpers and constants.
(function () {
  "use strict";

  function create(app) {
    const { boardEl, cards, STAGE, CLIMAX_SHOW_MS, SPECTATING, reducedMotion, esc, who, outOfSight, pileCount, musicTheme, atBrink } = app;

    const FX_STEP_MS = 160; // between damage cards turning over when the music isn't setting the beat
    const MAX_STAT_POPS = 6; // characters whose stats float a change at once (an end-of-turn reset is left out anyway)
    const BATTLE_MS = 1700; // the power duel's time on screen
    const LETHAL_STEP_MS = 420; // at least this long between cards of a damage that could end the game: slow motion
    const LOSING_CLOCK = 7; // a full clock levels up, and at level 3 that's the game
    let fxSeen = null; // {game, battle, ability}: what's been shown, so reopening the page doesn't replay it
    let negatedWait = { me: 0, opponent: 0 }; // how long "Damage Negated!" waits for its cards to turn over
    let ownDamageAt = -Infinity; // when our own "Take damage" flew its cards in, so they don't turn over twice
    let surgeFrom = null; // {last, owners}: a board with a climax just played, whose stat changes wait for its surge

    const cardEl = (uid) => (uid ? boardEl.querySelector(`.pcard[data-uid="${CSS.escape(uid)}"]`) : null);
    const visibleCard = (uid) => { const el = cardEl(uid); return el && !outOfSight(el) ? el : null; };
    const centerOf = (el) => { const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; };
    // The music's sixteenth, so the cards turn over on its ticks; a steady beat without it.
    const fxStep = () => (app.score() && app.score().running ? app.score().STEP * 1000 : FX_STEP_MS);

    // Something fixed over the board at a point, gone when its animation ends (or after `ms`, in case it never runs).
    function fxAt(at, className, html, ms = 2500) {
      const el = document.createElement("div");
      el.className = className;
      el.setAttribute("aria-hidden", "true"); // the log and the board say what happened; this only shows it
      el.innerHTML = html;
      Object.assign(el.style, { left: `${at.x}px`, top: `${at.y}px` });
      document.body.appendChild(el);
      el.addEventListener("animationend", (event) => { if (event.target === el) el.remove(); });
      setTimeout(() => el.remove(), ms);
      return el;
    }

    // A class that plays an animation on a card, taken off again once it has.
    function pulse(el, className) {
      el.classList.remove(className);
      void el.offsetWidth; // restart it
      el.classList.add(className);
      el.addEventListener("animationend", () => el.classList.remove(className), { once: true });
    }

    function tableFx(last) {
      negatedWait = { me: 0, opponent: 0 };
      const now = { game: app.board().game_number, battle: (app.board().battle || {}).id || "", ability: (app.board().ability_show || {}).id || "" };
      const before = fxSeen && fxSeen.game === now.game ? fxSeen : null;
      fxSeen = now;
      if (!before || !last || !app.animations() || app.board().rps || last.game_number !== app.board().game_number) return;
      // Damage first (it comes before the battle in an attack), then the clash once its cards have turned over.
      const flipping = Math.max(damageFlips(last, "me"), damageFlips(last, "opponent"));
      // The damage that ended the game turns over before the game-over screen comes up.
      if (flipping && app.board().game_over) app.holdGameOver(flipping + 500);
      if (now.battle && now.battle !== before.battle) {
        const battle = app.board().battle;
        // The board already has the loser reversed: it stays upright until the clash turns it over.
        battle.reversed.map(visibleCard).filter(Boolean).forEach((el) => el.classList.add("battle-pending"));
        setTimeout(() => showBattle(battle), flipping);
      }
      const newTurn = app.board().turn_number !== last.turn_number || app.board().my_turn !== last.my_turn;
      // A climax just played: its side's stat changes come with its surge, once its takeover has shown
      // (climaxSurge, called by it in a moment); the other side's now. If no takeover claims them, they all show now.
      const climaxed = ["me", "opponent"].filter((owner) => last[owner] && app.board()[owner]
        && (app.board()[owner].climaxes || 0) > (last[owner].climaxes || 0));
      if (newTurn) showTurnBanner();
      else if (climaxed.length) {
        statPops(last, { skip: climaxed });
        surgeFrom = { last, owners: climaxed };
        setTimeout(() => {
          if (!surgeFrom || surgeFrom.last !== last) return;
          surgeFrom = null;
          statPops(last, { only: climaxed });
        }, 0);
      } else statPops(last);
      // An ability's trails, once its card has shown in the middle of the screen (which would hide them).
      if (now.ability && now.ability !== before.ability && !app.board().ability_show.check) {
        const shown = app.board().ability_show;
        setTimeout(() => abilityTrails(shown), CLIMAX_SHOW_MS * 0.75);
      }
    }

    // A damage's new clock cards turn over one at a time, on the music's ticks: the last one lands the hit (the
    // side shakes) or, a climax, the cancel (it flares gold, and "Damage Negated!" waits for it). How long it takes.
    function damageFlips(last, owner) {
      const was = last[owner];
      const is = app.board()[owner];
      if (!was || !is || !Array.isArray(was.zones.clock) || !Array.isArray(is.zones.clock)) return 0;
      const negated = (is.negated || 0) > (was.negated || 0);
      if (!negated && (is.damage_taken || 0) <= (was.damage_taken || 0)) return 0;
      if (owner === "me" && performance.now() - ownDamageAt < 3000) return 0;
      const mat = boardEl.querySelector(`.mat-${owner}`);
      if (outOfSight(mat)) return 0;
      const old = new Set(was.zones.clock.map((c) => c.uid));
      const fresh = is.zones.clock.filter((c) => !old.has(c.uid)).map((c) => cardEl(c.uid)).filter(Boolean);
      if (!fresh.length) return 0;
      // A damage that would take them to level 4 if it lands: the table dims round their clock and the cards turn
      // over in slow motion (on every third tick of the music, if it's playing).
      const lethal = pileCount(was.zones.level) >= 3 && was.zones.clock.length + fresh.length >= LOSING_CLOCK && fresh.length > 1;
      const step = lethal ? Math.max(fxStep() * 3, LETHAL_STEP_MS) : fxStep();
      if (lethal) {
        boardEl.dataset.lethal = owner;
        setTimeout(() => { if (boardEl.dataset.lethal === owner) delete boardEl.dataset.lethal; }, (fresh.length - 1) * step + 900);
      }
      fresh.forEach((el, n) => {
        el.classList.add("dmg-wait");
        setTimeout(() => {
          el.classList.remove("dmg-wait");
          pulse(el, n < fresh.length - 1 ? "dmg-flip" : negated ? "dmg-cancel" : "dmg-hit");
        }, n * step);
      });
      const end = (fresh.length - 1) * step;
      if (negated) negatedWait[owner] = end + 250;
      else setTimeout(() => shakeSide(mat, fresh.length), end);
      return end + 350;
    }

    // The hit lands: the side of the table jolts (harder for more damage), or, without motion, flashes red.
    function shakeSide(mat, amount) {
      if (!mat.isConnected) return;
      if (reducedMotion) {
        pulse(mat, "mat-hurt");
        return;
      }
      const d = Math.min(3 + amount, 8);
      mat.animate([{ translate: "0 0" }, { translate: `${-d}px 1px` }, { translate: `${d * 0.8}px -1px` }, { translate: `${-d * 0.5}px 0` }, { translate: "0 0" }],
        { duration: 320, easing: "ease-out" });
      pulse(mat, "mat-hurt");
    }

    // The battle: the attacker lunges into the defender, they meet in a flash with their power counting up between
    // them, and the loser turns over to reversed with a crack.
    function showBattle(battle) {
      const attacker = visibleCard(battle.attacker);
      const defender = visibleCard(battle.defender);
      let impact = 0;
      if (attacker && defender) {
        const from = centerOf(attacker);
        const to = centerOf(defender);
        const mid = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 };
        if (!reducedMotion) {
          const dx = (to.x - from.x) * 0.38;
          const dy = (to.y - from.y) * 0.38;
          attacker.animate([{ translate: "0 0", scale: "1" }, { translate: `${dx * -0.12}px ${dy * -0.12}px`, scale: "1.04", offset: 0.25 },
            { translate: `${dx}px ${dy}px`, scale: "1.08", offset: 0.5 }, { translate: "0 0", scale: "1" }], { duration: 560, easing: "cubic-bezier(.5, 0, .3, 1)" });
          impact = 280;
        }
        setTimeout(() => {
          fxAt(mid, "clash-burst", '<span class="clash-ring"></span><span class="clash-ring clash-ring-late"></span><span class="clash-flash"></span>', 1200);
          powerDuel(mid, battle, attacker, defender);
        }, impact);
      } else {
        const one = attacker || defender;
        if (one) powerDuel(centerOf(one), battle, attacker, defender);
      }
      setTimeout(() => {
        for (const uid of battle.reversed) {
          const el = visibleCard(uid);
          if (!el) continue;
          el.classList.remove("battle-pending");
          if (!reducedMotion) el.animate([{ rotate: "-180deg" }, { rotate: "-200deg", offset: 0.2 }, { rotate: "0deg" }], { duration: 520, easing: "cubic-bezier(.3, .8, .3, 1.15)" });
          pulse(el, "reverse-crack");
        }
      }, impact + 260);
    }

    // The power duel: each side's number counting up from what's printed to what it battled at.
    function powerDuel(at, battle, attackerEl, defenderEl) {
      const [mine, theirs] = battle.power;
      const printed = (el, fallback) => Number((cards[el && el.dataset.card] || {}).power ?? fallback) || 0;
      const tie = mine === theirs;
      const side = (cls, value, won) => `<span class="duel-side ${cls}${won ? " duel-won" : tie ? " duel-tie" : " duel-lost"}"><b data-to="${value}">${value}</b></span>`;
      const el = fxAt(at, "battle-duel",
        `${side("duel-attacker", mine, mine > theirs)}<span class="duel-vs">vs</span>${side("duel-defender", theirs, theirs > mine)}`, BATTLE_MS + 400);
      el.style.setProperty("--duel-ms", `${BATTLE_MS}ms`);
      if (reducedMotion) return;
      const numbers = el.querySelectorAll("b");
      const starts = [printed(attackerEl, mine), printed(defenderEl, theirs)];
      const began = performance.now();
      const COUNT_MS = 420;
      (function tick(t) {
        const k = Math.min(1, (t - began) / COUNT_MS);
        numbers.forEach((b, i) => {
          const to = Number(b.dataset.to);
          b.textContent = String(Math.round((starts[i] + (to - starts[i]) * k) / 50) * 50);
        });
        if (k < 1 && el.isConnected) requestAnimationFrame(tick);
        else numbers.forEach((b) => { b.textContent = b.dataset.to; });
      })(began);
    }

    // A character's power, soul or level changed without a new turn: the change floats up off it, green or red,
    // and the number on the card flares. `only`/`skip`: the sides to do or leave out; `delayOf(el)`: when each
    // character's pops start (a climax's surge reaching it).
    function statPops(last, { only = null, skip = [], delayOf = () => 0 } = {}) {
      const was = last.stats || {};
      const is = app.board().stats || {};
      let shown = 0;
      for (const owner of ["me", "opponent"]) {
        if ((only && !only.includes(owner)) || skip.includes(owner)) continue;
        const side = app.board()[owner];
        const before = last[owner];
        if (!side || !before) continue;
        const stood = new Set(STAGE.map((slot) => (before.stage[slot] || {}).uid).filter(Boolean));
        for (const slot of STAGE) {
          const card = side.stage[slot];
          if (!card || !stood.has(card.uid) || !was[card.uid] || !is[card.uid] || shown >= MAX_STAT_POPS) continue;
          const el = visibleCard(card.uid);
          if (!el) continue;
          const changes = [["power", "", ".stat-power"], ["soul", " soul", ".stat-soul"], ["level", " level", ".stat-level"]]
            .filter(([stat]) => typeof was[card.uid][stat] === "number" && typeof is[card.uid][stat] === "number" && was[card.uid][stat] !== is[card.uid][stat])
            .map(([stat, label, sel]) => ({ change: is[card.uid][stat] - was[card.uid][stat], label, sel }));
          if (!changes.length) continue;
          shown += 1;
          setTimeout(() => {
            if (!el.isConnected) return;
            const box = el.getBoundingClientRect();
            changes.forEach(({ change, label, sel }, n) => {
              const up = change > 0;
              const pop = fxAt({ x: box.left + box.width / 2, y: box.top + n * 16 }, `stat-pop ${up ? "stat-pop-up" : "stat-pop-down"}`,
                `${up ? "+" : "−"}${Math.abs(change)}${label}`, 1600);
              pop.style.animationDelay = `${n * 120}ms`;
              const number = el.querySelector(sel);
              if (number) pulse(number, up ? "stat-flare-up" : "stat-flare-down");
            });
          }, delayOf(el));
        }
      }
    }

    // A new turn: a banner across the middle of the table with whose it is (their picture, if they have one).
    function showTurnBanner() {
      if (app.board().game_over || !app.board().opponent) return;
      const divider = boardEl.querySelector(".table-divider");
      if (outOfSight(divider)) return;
      const mine = app.board().my_turn;
      const name = mine ? app.board().me.name : app.board().opponent.name;
      const box = divider.getBoundingClientRect();
      const words = mine && !SPECTATING ? "Your turn" : `${esc(name)}'s turn`;
      fxAt({ x: box.left + box.width / 2, y: box.top + box.height / 2 }, `turn-banner ${mine ? "turn-banner-me" : "turn-banner-opponent"}`,
        `${app.avatars()[name] ? who(name, "turn-banner-face") : ""}<span>${words}</span>`, 2600);
    }

    // An ability that resolved: its card pulses where it is on the board and trails run to the cards it was directed at.
    function abilityTrails(shown) {
      const source = visibleCard(shown.uid);
      const targets = (shown.target_uids || []).map(visibleCard).filter((el) => el && el !== source);
      if (source) pulse(source, "fx-source");
      targets.forEach((el, n) => setTimeout(() => pulse(el, "fx-target"), 220 + n * 90));
      if (!source || !targets.length || reducedMotion) return;
      const from = centerOf(source);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("class", "ability-trails");
      svg.setAttribute("aria-hidden", "true");
      svg.innerHTML = targets.map((el) => {
        const to = centerOf(el);
        // A gentle arc, bowing away from the middle of the line.
        const mx = (from.x + to.x) / 2 - (to.y - from.y) * 0.18;
        const my = (from.y + to.y) / 2 + (to.x - from.x) * 0.18;
        return `<path d="M${from.x} ${from.y} Q${mx} ${my} ${to.x} ${to.y}" pathLength="1"/><circle cx="${to.x}" cy="${to.y}" r="5"/>`;
      }).join("");
      document.body.appendChild(svg);
      svg.addEventListener("animationend", (event) => { if (event.target === svg) svg.remove(); });
      setTimeout(() => svg.remove(), 2000);
    }

    // A climax's power going out to its side, `after` ms from now (as its takeover fades): a ring in its colour
    // spreads from the climax zone, and each character charges up as it reaches them, nearest first, with its stat
    // changes floating off it then (held back from tableFx for this).
    function climaxSurge(owner, color, after) {
      const waiting = surgeFrom && surgeFrom.owners.includes(owner) ? surgeFrom : null;
      if (waiting) surgeFrom = null;
      setTimeout(() => {
        const mat = boardEl.querySelector(`.mat-${owner}`);
        const zone = mat && mat.querySelector('[data-pile="climax"]');
        if (!zone || outOfSight(zone)) {
          if (waiting) statPops(waiting.last, { only: [owner] });
          return;
        }
        const from = centerOf(zone);
        const wave = fxAt(from, "cx-wave", "", 1600);
        wave.style.setProperty("--cx", color);
        pulse(zone, "cx-zone-burst");
        zone.style.setProperty("--cx", color);
        const SPEED = 1.5; // px per ms
        const delayOf = (el) => Math.min(700, Math.hypot(centerOf(el).x - from.x, centerOf(el).y - from.y) / SPEED);
        for (const slot of STAGE) {
          const card = app.board()[owner] && app.board()[owner].stage[slot];
          const el = card && visibleCard(card.uid);
          if (!el) continue;
          el.style.setProperty("--cx", color);
          setTimeout(() => pulse(el, "cx-charge"), delayOf(el));
        }
        if (waiting) statPops(waiting.last, { only: [owner], delayOf });
      }, after);
    }

    // The table's mood, from the same reading of the board as the music: warmer as the levels climb, a boss's
    // tint, a red heartbeat at the edges at match point (and that side's clock glowing), and whose turn it is.
    function setTableMood() {
      const live = app.board() && !app.board().game_over && !app.board().rps;
      const sides = [app.board().me, app.board().opponent].filter(Boolean);
      const level = live ? Math.max(0, ...sides.map((side) => pileCount(side.zones.level))) : 0;
      const theme = musicTheme();
      boardEl.dataset.tier = String(Math.min(level, 3));
      boardEl.dataset.boss = live && theme && theme.boss ? "1" : "";
      boardEl.dataset.brink = live ? ["me", "opponent"].filter(atBrink).join(" ") : "";
      boardEl.dataset.turn = live && app.board().opponent ? (app.board().my_turn ? "me" : "opponent") : "";
      boardEl.dataset.still = app.animations() ? "" : "1"; // animations off: the match point's edges glow without pulsing
      // A climax in play powers its side for the turn: that side tinted in its colour and its climax zone aglow.
      const powered = [];
      for (const owner of ["me", "opponent"]) {
        const zone = live && app.board()[owner] ? app.board()[owner].zones.climax : null;
        const top = Array.isArray(zone) && zone.length ? zone[zone.length - 1] : null;
        if (!top || !top.card) continue;
        powered.push(owner);
        boardEl.style.setProperty(`--cx-${owner}`, app.climaxColor(cards[top.card]));
      }
      boardEl.dataset.cx = powered.join(" ");
    }

    return {
      tableFx,
      setTableMood,
      climaxSurge,
      negatedWait: (owner) => negatedWait[owner] || 0,
      noteOwnDamage: () => { ownDamageAt = performance.now(); },
    };
  }

  window.WeissTableFx = { create };
})();
