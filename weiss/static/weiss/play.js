// Weiss Schwarz virtual tabletop. The server holds the game; this draws the board from the
// current player's seat (their side at the bottom, the opponent's mirrored at the top), sends
// moves, and polls for the opponent's moves. Players move their own cards by dragging them
// onto a zone, or by clicking a card or pile for a menu.
(() => {
  const root = document.getElementById("play");
  if (!root) return;
  const STATE_URL = root.dataset.stateUrl;
  const ACTION_URL = root.dataset.actionUrl;
  const CSRF = root.dataset.csrf;
  const POLL_MS = Number(root.dataset.pollMs) || 1500; // quicker against a CPU: polling is what moves it

  const $ = (sel) => root.querySelector(sel);
  const boardEl = $("[data-board]");
  const previewEl = $("[data-preview]");
  const controlsEl = $("[data-controls]");
  const logEl = $("[data-log]");
  const menuEl = $("[data-menu]");
  const modalEl = $("[data-modal]");

  const LABELS = {
    deck: "Deck", hand: "Hand", clock: "Clock", level: "Level", stock: "Stock", waiting: "Waiting room",
    memory: "Memory", climax: "CX", resolution: "Resolution",
    C1: "Center left", C2: "Center middle", C3: "Center right", B1: "Back left", B2: "Back right",
  };
  const STAGE = ["C1", "C2", "C3", "B1", "B2"];
  // Each stage slot has a pile of markers under it, named "marker:<slot>" like the server does.
  for (const slot of STAGE) LABELS[`marker:${slot}`] = `Markers under ${LABELS[slot].toLowerCase()}`;
  const isMarkerPile = (zone) => zone.startsWith("marker:");
  const DAMAGE_RESOLVE_MS = 500; // how long a climax-cancelled damage stays on the board
  const REFRESH_PAUSE_MS = 250; // how long an emptied deck shows before it's refreshed mid-damage
  const CLIMAX_SHOW_MS = 2000; // how long a climax played in the climax phase shows before the attack phase
  const PHASE_PAUSE_MS = 900; // how long a phase that ended itself stays before the next begins
  const PHASE_NAME_FX = ["fx-pop", "fx-flip", "fx-slide", "fx-glow"]; // a new phase's name comes in with one of these
  const RPS_SHOW_MS = 3000; // how long rock, paper, scissors' result shows before the mulligan
  const SHOW_FALLBACK_MS = 3000; // how much later than its owner the other player's page ends an ability's show
  const CLIMAX_EFFECTS = ["climax-zoom", "climax-spin", "climax-slide", "climax-flip", "climax-drop", "climax-blur"];
  const MOVE_TARGETS = ["hand", "C1", "C2", "C3", "B1", "B2", "climax", "clock", "level", "stock",
    "memory", "waiting", "resolution"];
  const PUBLIC_PILES = ["waiting", "memory", "level", "clock", "climax", "resolution"];
  const ENCORE_COST = 3; // stock, as on the server
  const LEVEL_UP_AT = 7; // clock cards that make a level, as on the server
  const CLOCK_DRAW = 2; // cards drawn after clocking a card from the hand, as on the server
  const PHASES = { mulligan: "Mulligan", stand: "Stand", draw: "Draw", clock: "Clock", main: "Main", climax: "CX", attack: "Attack", encore: "Encore", end: "End" };
  const PHASE_NAMES = Object.keys(PHASES);
  const ATTACK_STEPS = { declare: "Declare", trigger: "Trigger", counter: "Counter", damage: "Damage", battle: "Battle" };
  const OPPOSITE = { C1: "C3", C2: "C2", C3: "C1" }; // the opponent's slot facing each of our center slots
  // Neighbouring stage slots, each linked by a button on the first slot: [first, second, direction].
  // The back row sits under the gaps of the center row, so center-to-back links are diagonal.
  const SLOT_LINKS = [["C1", "C2", "h"], ["C2", "C3", "h"], ["B1", "B2", "h"],
    ["C1", "B1", "dr"], ["C2", "B1", "dl"], ["C2", "B2", "dr"], ["C3", "B2", "dl"]];
  // [both occupied (swap), first to second, second to first]
  const LINK_SYMBOLS = { h: ["⇄", "→", "←"], dr: ["⇅", "↘", "↖"], dl: ["⇅", "↙", "↗"] };
  // Entrances for the panel that takes over from the phase bar during the attack phase (and back).
  const PANEL_SWAPS = ["swap-slide", "swap-flip", "swap-zoom", "swap-skew"];
  // Playing a card from the hand into one of these pays its cost from the stock (as on the server).
  const PLAY_ZONES = ["C1", "C2", "C3", "B1", "B2", "climax", "resolution"];
  const COLORS = ["Yellow", "Green", "Red", "Blue", "Purple"];

  let version = "";
  let board = null;
  const cards = {}; // card pk -> details; entries are never replaced so image URLs stay stable
  let modal = null; // {title, owner: "me"|"opponent", zone} or {title, revealed: [...]}
  let error = "";
  let busy = false;
  let resolveTimer = null; // pending "resolve_damage" after a climax cancels our damage
  let refreshTimer = null; // pending "continue_damage" after a damage empties our deck
  let climaxTimer = null; // pending move to the attack phase after we play a climax
  let autoTimer = null; // pending move to the next phase after one ended itself (board.auto_next)
  let showTimer = null; // pending end of an ability being shown (board.ability_show)
  let rpsTimer = null; // pending end of rock, paper, scissors' result
  const mulliganPicks = new Set(); // hand cards picked to mulligan away
  const discardPicks = new Set(); // hand cards picked for the end phase's discard
  let abilityPicks = []; // cards picked for an ability's prompt, in the order they were picked

  // Board view: "focus" (big stage, piles around it) or "classic" (three even rows). Remembered
  // per browser; storage can be unavailable (private windows), so it falls back to focus.
  const LAYOUT_KEY = "weiss-board-layout";
  const LAYOUTS = { focus: "Focused", classic: "Classic" };
  let layout = "focus";
  try {
    if (LAYOUTS[localStorage.getItem(LAYOUT_KEY)]) layout = localStorage.getItem(LAYOUT_KEY);
  } catch (e) { /* keep the default */ }

  function setLayout(next) {
    layout = next;
    try { localStorage.setItem(LAYOUT_KEY, next); } catch (e) { /* only this visit, then */ }
    for (const name of Object.keys(LAYOUTS)) root.classList.toggle(`layout-${name}`, name === layout);
    if (board) render();
  }
  setLayout(layout);

  // Animations ("Deck Out!", level ups, drawing) can be turned off; remembered per browser like
  // the layout. Off by default for people who've asked their system for reduced motion.
  const ANIMATIONS_KEY = "weiss-animations";
  let animations = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  try {
    const saved = localStorage.getItem(ANIMATIONS_KEY);
    if (saved) animations = saved === "on";
  } catch (e) { /* keep the default */ }

  function setAnimations(on) {
    animations = on;
    try { localStorage.setItem(ANIMATIONS_KEY, on ? "on" : "off"); } catch (e) { /* only this visit, then */ }
    if (board) renderControls();
  }

  // --- Talking to the server -------------------------------------------------------------------

  function receive(data) {
    if (data.status && data.status !== "playing") {
      window.location.reload(); // back to deck choice
      return;
    }
    version = String(data.version);
    for (const [pk, info] of Object.entries(data.cards || {})) {
      if (!cards[pk]) cards[pk] = info;
    }
    const before = opponentSnapshot();
    board = data.board;
    if (data.revealed) modal = { title: data.revealed.title, revealed: data.revealed.cards };
    render();
    animateOpponent(before);
    announce();
    // A climax cancelled our damage: leave it on the board for a moment, then let the server clean up.
    if (board.damage_pending && !resolveTimer) {
      resolveTimer = setTimeout(() => {
        resolveTimer = null;
        act({ type: "resolve_damage" });
      }, DAMAGE_RESOLVE_MS);
    }
    // A phase of our turn ended itself: pause on it, then move on (the server drops this if the
    // turn has moved on some other way in the meantime). Abilities being resolved hold this up;
    // the board that arrives once they're done starts it again.
    if (board.auto_next && board.my_turn && !board.ability && !autoTimer) {
      const next = board.auto_next;
      autoTimer = setTimeout(() => {
        autoTimer = null;
        if (board.auto_next === next && board.my_turn && !board.ability) act({ type: "phase", phase: next, auto: true });
      }, PHASE_PAUSE_MS);
    }
    // We played a climax in the climax phase: let it show, then move on to the attack phase
    // (once any abilities it triggered have been resolved).
    if (board.climax_pending && !board.ability && !climaxTimer) {
      climaxTimer = setTimeout(() => {
        climaxTimer = null;
        if (board.climax_pending && !board.ability) act({ type: "phase", phase: "attack" });
      }, CLIMAX_SHOW_MS);
    }
    // An ability is being shown: once it has been, play carries on. Its owner's page says so; the
    // other page does too a little later, in case the owner has gone away.
    if (board.ability_show && !showTimer) {
      const { id, mine } = board.ability_show;
      const delay = (animations ? CLIMAX_SHOW_MS : 0) + (mine ? 0 : SHOW_FALLBACK_MS);
      showTimer = setTimeout(() => {
        showTimer = null;
        if (board.ability_show && board.ability_show.id === id) act({ type: "ability_show_done", id });
      }, delay);
    }
    // Rock, paper, scissors has a winner: let both players see it, then on to the mulligan.
    if (board.rps && board.rps.won !== null && !rpsTimer) {
      rpsTimer = setTimeout(() => {
        rpsTimer = null;
        if (board.rps) act({ type: "rps_done" });
      }, RPS_SHOW_MS);
    }
    // A damage emptied our deck: pause a moment, then the server refreshes it and deals the rest.
    if (board.refresh_pending && !refreshTimer) {
      refreshTimer = setTimeout(() => {
        refreshTimer = null;
        act({ type: "continue_damage" });
      }, REFRESH_PAUSE_MS);
    }
  }

  // --- Announcements: "Deck Out!" and level ups, shown on the side they happened on -----------------

  // How many refreshes and level ups each side had at the last board we saw; the first board only
  // sets these, so reopening the page doesn't replay old ones.
  let seen = null;

  let shownAbility = null; // the id of the last ability shown

  function announce() {
    const now = {};
    const show = animations && seen;
    const ability = board.ability_show;
    if (ability && ability.id !== shownAbility) {
      shownAbility = ability.id;
      if (show) showAbility(ability);
    }
    for (const owner of ["me", "opponent"]) {
      const side = owner === "me" ? board.me : board.opponent;
      if (!side) continue;
      now[owner] = { refreshes: side.refreshes || 0, level_ups: side.level_ups || 0, climaxes: side.climaxes || 0 };
      if (!show || !seen[owner]) continue;
      const mat = boardEl.querySelector(`.mat-${owner}`);
      if (now[owner].refreshes > seen[owner].refreshes) {
        flash(between(mat, '[data-pile="deck"]', '[data-slot="C3"]'), "Deck Out!", "flash-deck-out");
      }
      if (now[owner].climaxes > seen[owner].climaxes) showClimax(side.zones.climax[side.zones.climax.length - 1]);
      if (now[owner].level_ups > seen[owner].level_ups) {
        const level = side.zones.level.length;
        flash(levelGap(mat), `lv.${level - 1}`, "flash-level", `lv.${level}`);
      }
    }
    seen = now;
  }

  // A climax just played, in the middle of the screen, coming in with a randomly picked effect and
  // fading away over the time the turn waits before the attack phase.
  function showClimax(card) {
    const info = card && card.card ? cards[card.card] : null;
    if (!info) return;
    const el = document.createElement("div");
    el.className = `climax-show ${CLIMAX_EFFECTS[Math.floor(Math.random() * CLIMAX_EFFECTS.length)]}`;
    el.style.animationDuration = `${CLIMAX_SHOW_MS}ms`;
    el.innerHTML = `<img src="${esc(info.image)}" alt="Climax: ${esc(info.name)}">`;
    document.body.appendChild(el);
    el.addEventListener("animationend", () => el.remove());
  }

  // An ability that has resolved: its card, in the middle of the screen with the same entrance as a
  // climax, with an arrow to each card it was directed at.
  function showAbility(ability) {
    if (ability.check) return showTriggerCheck(ability.check);
    const source = cards[ability.card];
    if (!source) return;
    const targets = ability.targets.map((pk) => cards[pk]).filter(Boolean);
    const el = document.createElement("div");
    el.className = `climax-show ${CLIMAX_EFFECTS[Math.floor(Math.random() * CLIMAX_EFFECTS.length)]}`;
    el.style.animationDuration = `${CLIMAX_SHOW_MS}ms`;
    el.innerHTML = targets.length
      ? `<div class="ability-show" style="--targets: ${targets.length}">
          <img data-source src="${esc(source.image)}" alt="Ability: ${esc(source.name)}">
          <div class="ability-show-targets">${targets.map((t) => `<img data-target src="${esc(t.image)}" alt="Target: ${esc(t.name)}">`).join("")}</div>
          <svg class="ability-arrows" aria-hidden="true"></svg>
        </div>`
      : `<img src="${esc(source.image)}" alt="Ability: ${esc(source.name)}">`;
    document.body.appendChild(el);
    el.addEventListener("animationend", () => el.remove());
    if (targets.length) {
      const images = [...el.querySelectorAll("img")].map((img) => img.decode().catch(() => {}));
      Promise.all(images).then(() => drawArrows(el));
    }
  }

  // A trigger check: the card or cards it turned over, with their icons, or that they have none.
  function showTriggerCheck(pks) {
    const checked = pks.map((pk) => cards[pk]).filter(Boolean);
    if (!checked.length) return;
    const icons = checked.map((c) => c.trigger).filter(Boolean).join(" ");
    const el = document.createElement("div");
    el.className = `climax-show ${CLIMAX_EFFECTS[Math.floor(Math.random() * CLIMAX_EFFECTS.length)]}`;
    el.style.animationDuration = `${CLIMAX_SHOW_MS}ms`;
    el.innerHTML = `<div class="trigger-show">
      <p class="trigger-show-title">Trigger check</p>
      <div class="trigger-show-cards">${checked.map((c) => `<img src="${esc(c.image)}" alt="${esc(c.name)}">`).join("")}</div>
      <p class="trigger-show-icons">${icons ? esc(icons) : "No trigger"}</p>
    </div>`;
    document.body.appendChild(el);
    el.addEventListener("animationend", () => el.remove());
  }

  // Arrows from the shown ability's card to its targets, measured without the entrance's transform.
  function drawArrows(el) {
    const box = el.querySelector(".ability-show");
    const svg = box.querySelector(".ability-arrows");
    const from = box.querySelector("[data-source]");
    const startX = from.offsetLeft + from.offsetWidth;
    const startY = from.offsetTop + from.offsetHeight / 2;
    const GAP = 8;
    svg.setAttribute("width", box.offsetWidth);
    svg.setAttribute("height", box.offsetHeight);
    svg.innerHTML = `<defs><marker id="ability-arrowhead" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
        <path d="M0 0 L5 2.5 L0 5 z" fill="#ffd964"/></marker></defs>`
      + [...box.querySelectorAll("[data-target]")].map((to) => `<line x1="${startX + GAP}" y1="${startY}"
        x2="${to.offsetLeft - GAP}" y2="${to.offsetTop + to.offsetHeight / 2}" stroke="#ffd964" stroke-width="5" marker-end="url(#ability-arrowhead)"/>`).join("");
  }

  // The point halfway between the centers of two zones on one side of the table.
  function between(mat, fromSel, toSel) {
    const from = mat && mat.querySelector(fromSel);
    const to = mat && mat.querySelector(toSel);
    if (!from || !to) return null;
    const a = from.getBoundingClientRect();
    const b = to.getBoundingClientRect();
    return { x: (a.left + a.right + b.left + b.right) / 4, y: (a.top + a.bottom + b.top + b.bottom) / 4 };
  }

  // The middle of the empty stretch between the level zone and the clock's cards (the level zone
  // is on the clock's left on our side, on its right on the opponent's).
  function levelGap(mat) {
    const level = mat && mat.querySelector('[data-pile="level"]');
    const clock = mat && mat.querySelector('[data-pile="clock"]');
    if (!level || !clock) return null;
    const l = level.getBoundingClientRect();
    const clockCards = [...clock.querySelectorAll(".pcard")].map((c) => c.getBoundingClientRect());
    const c = clock.getBoundingClientRect();
    const left = clockCards.length ? Math.min(...clockCards.map((r) => r.left)) : c.left + c.width / 2;
    const right = clockCards.length ? Math.max(...clockCards.map((r) => r.right)) : c.left + c.width / 2;
    const x = l.right <= left ? (l.right + left) / 2 : (right + l.left) / 2;
    return { x, y: c.top + c.height / 2 };
  }

  // Text over the board at a point. It fades in and out; with `next` it flickers as `text`, then
  // changes to `next` and fades out.
  function flash(at, text, className, next = null) {
    if (!at) return;
    const el = document.createElement("div");
    el.className = `play-flash ${className}`;
    el.textContent = text;
    el.setAttribute("aria-live", "polite");
    el.style.left = `${at.x}px`;
    el.style.top = `${at.y}px`;
    document.body.appendChild(el);
    el.addEventListener("animationend", () => {
      if (next && !el.classList.contains("flash-next")) {
        el.textContent = next;
        el.classList.add("flash-next");
      } else {
        el.remove();
      }
    });
  }

  // --- Card movement: our own moves fly a card from where it is to where it's going, and then the
  // action is sent, so the real card appears as the flight lands ---------------------------------

  const FLIGHT_MS = 420; // each card's flight
  const FLIGHT_STAGGER_MS = 140; // between cards when several move
  const MAX_FLIGHTS = 10;
  const BACK = '<span class="pcard-back"></span>';

  // The element showing one of our zones: a stage slot (markers fly to their character), a pile,
  // or the hand.
  function zoneEl(zone) {
    if (zone === "hand") return boardEl.querySelector(".hand-me .hand-cards");
    const slot = isMarkerPile(zone) ? zone.slice("marker:".length) : zone;
    if (STAGE.includes(slot)) return boardEl.querySelector(`.mat-me [data-slot="${slot}"]`);
    return boardEl.querySelector(`.mat-me [data-pile="${zone}"]`);
  }

  // An element's box as laid out, ignoring rotation, so a rested card still flies card-shaped.
  function layoutBox(el) {
    const r = el.getBoundingClientRect();
    const w = el.offsetWidth || r.width;
    const h = el.offsetHeight || r.height;
    return { left: r.left + r.width / 2 - w / 2, top: r.top + r.height / 2 - h / 2, width: w, height: h };
  }

  // The top (last) card shown in a zone, if any.
  function topCardEl(zone) {
    const el = zoneEl(zone);
    const shown = el ? el.querySelectorAll(".pcard") : [];
    return shown.length ? shown[shown.length - 1] : null;
  }

  // Where a card leaves a zone from: its top card, or the empty space.
  function originBox(zone) {
    const top = topCardEl(zone);
    const empty = zoneEl(zone) && zoneEl(zone).querySelector(".zone-empty");
    return top ? layoutBox(top) : empty ? layoutBox(empty) : null;
  }

  // Where a card arriving in a zone lands: past the end of the hand or clock, below the level
  // stack's last card, or on the pile or slot itself. `size` is used when there's nothing to match.
  function landingBox(zone, size) {
    const el = zoneEl(zone);
    if (!el) return null;
    const top = topCardEl(zone);
    if (top) {
      const last = layoutBox(top);
      if (zone === "hand" || zone === "clock") return { ...last, left: last.left + last.width * .6 };
      if (zone === "level") return { ...last, top: last.top + last.height * .22 };
      return last;
    }
    const empty = el.querySelector(".zone-empty");
    if (empty) return layoutBox(empty);
    const r = el.getBoundingClientRect(); // an empty hand
    return { left: r.left + r.width / 2 - size.width / 2, top: r.top, width: size.width, height: size.height };
  }

  const faceOf = (el) => {
    const img = el && !el.classList.contains("face-down") && el.querySelector("img");
    return img ? `<img src="${esc(img.src)}" alt="">` : BACK;
  };

  // The cards an action of ours moves, as [{from, to, face}] boxes, in the order they move.
  function flightsFor(action) {
    const flights = [];
    // `hide`: the card on the board that's moving, hidden while its flight stands in for it.
    const fly = (from, toZone, face = BACK, times = 1, ms = FLIGHT_MS, hide = null) => {
      const to = from && landingBox(toZone, from);
      for (let i = 0; to && i < Math.min(times, MAX_FLIGHTS); i++) flights.push({ from, to, face, ms, hide });
    };
    const fromZone = (zone, toZone, times = 1, face = BACK, ms = FLIGHT_MS) => fly(originBox(zone), toZone, face, times, ms);
    const at = PHASE_NAMES.indexOf(board.phase);
    const target = action.type === "end_turn" ? PHASE_NAMES.length - 1 : PHASE_NAMES.indexOf(action.phase);
    const passes = (phase) => at < PHASE_NAMES.indexOf(phase) && PHASE_NAMES.indexOf(phase) <= target;
    switch (action.type) {
      case "move": {
        const el = root.querySelector(`.pcard[data-uid="${action.uid}"]`);
        if (!el) break;
        fly(layoutBox(el), action.to, faceOf(el), 1, FLIGHT_MS, el);
        // Moving onto an occupied slot from another slot swaps them: the other card flies back.
        const other = STAGE.includes(el.dataset.zone) && STAGE.includes(action.to) && topCardEl(action.to);
        if (other) fly(layoutBox(other), el.dataset.zone, faceOf(other), 1, FLIGHT_MS, other);
        const info = el.dataset.card ? cards[el.dataset.card] : null;
        if (el.dataset.zone === "hand" && PLAY_ZONES.includes(action.to) && info && info.cost) {
          fromZone("stock", "waiting", info.cost); // paying the cost
        }
        break;
      }
      case "move_top": fromZone(action.from, action.to, action.count || 1); break;
      case "move_all": fromZone(action.from, action.to, Math.min(pileCards(board.me, action.from).length, 6), faceOf(topCardEl(action.from))); break;
      case "attack": fromZone("deck", board.rules ? "stock" : "resolution"); break;
      case "discard":
        for (const uid of action.uids) {
          const el = root.querySelector(`.hand-me .pcard[data-uid="${uid}"]`);
          if (el) fly(layoutBox(el), "waiting", faceOf(el), 1, FLIGHT_MS, el);
        }
        break;
      case "mulligan":
        for (const uid of action.uids) {
          const el = root.querySelector(`.hand-me .pcard[data-uid="${uid}"]`);
          if (el) fly(layoutBox(el), "waiting", faceOf(el), 1, FLIGHT_MS, el);
        }
        fromZone("deck", "hand", action.uids.length);
        break;
      case "trigger_choice": {
        const el = action.uid && root.querySelector(`.pcard[data-uid="${action.uid}"]`);
        if (el) fly(layoutBox(el), action.to, faceOf(el));
        if (action.accept) fromZone("deck", "stock");
        break;
      }
      case "counter": {
        const el = root.querySelector(`.pcard[data-uid="${action.uid}"]`);
        if (el) fly(layoutBox(el), "waiting", faceOf(el));
        break;
      }
      case "damage": fromZone("deck", "clock", action.count || 1); break;
      case "encore": fromZone("stock", "waiting", ENCORE_COST); break;
      case "clock_draw": {
        const el = root.querySelector(`.pcard[data-uid="${action.uid}"]`);
        if (el) fly(layoutBox(el), "clock", faceOf(el));
        fromZone("deck", "hand", CLOCK_DRAW);
        break;
      }
      case "phase":
      case "end_turn":
        if (board.rules && passes("draw")) fromZone("deck", "hand", 1, BACK, FLIGHT_MS * 1.2); // the draw phase's draw, a little slower
        if (passes("end") && board.me.zones.climax.length) fromZone("climax", "waiting", board.me.zones.climax.length, faceOf(topCardEl("climax")));
        break;
      default: break;
    }
    return flights;
  }

  async function animateAction(action) {
    if (!animations || !board) return;
    await flyAll(flightsFor(action));
  }

  // Fly card-shaped boxes {from, to, face, ms}: `hide` is hidden for the flight (it's the card
  // leaving; the board is redrawn afterwards anyway), `show` is hidden until its flight lands.
  function flyAll(flights) {
    return Promise.all(flights.map(({ from, to, face, ms = FLIGHT_MS, hide, show }, i) => {
      const el = document.createElement("div");
      el.className = "card-flight";
      el.innerHTML = face;
      Object.assign(el.style, { left: `${from.left}px`, top: `${from.top}px`, width: `${from.width}px`, height: `${from.height}px` });
      document.body.appendChild(el);
      if (hide) hide.style.visibility = "hidden";
      if (show) show.style.visibility = "hidden";
      const animation = el.animate([
        { transform: "translate(0, 0) scale(1)" },
        { transform: `translate(${to.left - from.left}px, ${to.top - from.top}px) scale(${to.width / from.width})` },
      ], { duration: ms, delay: i * FLIGHT_STAGGER_MS, easing: "cubic-bezier(.3, .7, .4, 1)", fill: "forwards" });
      return animation.finished.catch(() => {}).then(() => {
        el.remove();
        if (show) show.style.visibility = "";
      });
    }));
  }

  // The opponent's moves arrive already made, so their stage changes are animated after the fact:
  // a character that changed slots flies from its old slot, and one played from their hand flies
  // from there, while the card in its new slot stays hidden until the flight lands.
  function opponentSnapshot() {
    if (!board || !board.opponent || !animations) return null;
    const mat = boardEl.querySelector(".mat-opponent");
    if (!mat) return null;
    const slots = {};
    const boxes = {};
    for (const slot of STAGE) {
      const card = board.opponent.stage[slot];
      if (card) slots[card.uid] = slot;
      const el = mat.querySelector(`[data-slot="${slot}"] .pcard, [data-slot="${slot}"] .zone-empty`);
      if (el) boxes[slot] = layoutBox(el);
    }
    const handCards = boardEl.querySelectorAll(".hand-opponent .pcard");
    const hand = handCards.length ? layoutBox(handCards[handCards.length - 1]) : null;
    return { slots, boxes, hand, handCount: board.opponent.zones.hand.count };
  }

  function animateOpponent(before) {
    if (!before || !board.opponent || !animations) return;
    const mat = boardEl.querySelector(".mat-opponent");
    const flights = [];
    for (const slot of STAGE) {
      const card = board.opponent.stage[slot];
      const el = card && mat && mat.querySelector(`[data-slot="${slot}"] .pcard`);
      if (!el || before.slots[card.uid] === slot) continue;
      const from = before.slots[card.uid] ? before.boxes[before.slots[card.uid]]
        : board.opponent.zones.hand.count < before.handCount ? before.hand : null;
      if (from) flights.push({ from, to: layoutBox(el), face: faceOf(el), show: el });
    }
    flyAll(flights);
  }

  async function poll() {
    if (busy || (document.hidden && Math.random() < 0.7)) return; // check less often in background tabs
    try {
      const response = await fetch(`${STATE_URL}?v=${version}`, { credentials: "same-origin" });
      if (response.status === 200) receive(await response.json());
    } catch (e) { /* offline for a moment; try again next tick */ }
  }

  async function act(action) {
    busy = true;
    hideMenu();
    try {
      await animateAction(action);
      const response = await fetch(ACTION_URL, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": CSRF },
        body: JSON.stringify(action),
      });
      const data = await response.json();
      error = data.error || "";
      if (modal && modal.revealed && action.uid && !data.error) {
        modal.revealed = modal.revealed.filter((c) => c.uid !== action.uid);
      }
      if (data.board || data.status) receive(data); else render();
    } catch (e) {
      error = "Couldn't reach the server. Try again.";
      render();
    } finally {
      busy = false;
    }
  }

  // --- Drawing ---------------------------------------------------------------------------------

  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  // Text as HTML with the word "climax" (or the label "CX") drawn as the stylized CX mark.
  const CX_HTML = '<span class="cx" title="Climax">CX</span>';
  const cxHtml = (text) => esc(text).replace(/\b(climax|CX)\b/gi, CX_HTML);

  function cardHtml(card, owner, zone, extraClass = "") {
    if (!card) return "";
    const info = card.card ? cards[card.card] : null;
    const classes = ["pcard", `pos-${card.pos}`, extraClass];
    if (card.face_down) classes.push("face-down");
    const mine = owner === "me";
    const attrs = [
      `data-uid="${esc(card.uid)}"`, `data-owner="${owner}"`, `data-zone="${zone}"`,
      card.card ? `data-card="${card.card}"` : "",
      mine && zone !== "deck" ? 'draggable="true"' : "",
    ].join(" ");
    const face = info
      ? `<img src="${esc(info.image)}" alt="${esc(info.name)}" loading="lazy" draggable="false">`
      : '<span class="pcard-back"></span>';
    const badge = card.pos === "reverse" ? '<span class="pcard-badge">REVERSE</span>'
      : card.face_down && info ? '<span class="pcard-badge">face down</span>' : "";
    const stats = info && !card.face_down
      ? statsHtml(info, { live: (board.stats || {})[card.uid], soul: STAGE.includes(zone) && zone.startsWith("C") })
      : "";
    return `<div class="${classes.join(" ")}" ${attrs} tabindex="0">${face}${stats}${badge}</div>`;
  }

  // The soul icon: a flame-like wisp, close to the one printed on Weiss Schwarz cards.
  const SOUL_ICON = '<svg viewBox="0 0 16 22" aria-hidden="true"><path d="M8.6 0c.6 3.4 3.2 5 5 8.3 2.6 4.6.4 11.9-5.6 12.9C2.4 22-1.6 15.8 1.3 10.9c.9-1.6 2.4-2.6 2.9-4.6.9 1.9.6 3.6 2 4.4C5.5 7 9.4 4.4 8.6 0z"/></svg>';

  // Level and cost in the top-left corner and power in the bottom-left, where the printed card has
  // them, but large enough to read at board size. Left-side so they show on overlapped piles too.
  // Front-row characters also show their soul in the bottom-right. `live` is the character's power
  // and soul right now, worked out by the server from climaxes, abilities and effects on it: numbers
  // above the printed ones glow green, numbers below it glow red.
  function statsHtml(info, { live = null, soul = false } = {}) {
    const has = (value) => value !== null && value !== undefined && value !== "";
    const corner = [
      has(info.level) ? `<span class="stat stat-level" title="Level">${esc(info.level)}</span>` : "",
      has(info.cost) ? `<span class="stat stat-cost" title="Cost">${esc(info.cost)}</span>` : "",
    ].join("");
    // A number's value right now, its glow, and its tooltip's note about the change from the card.
    const current = (printed, now) => {
      const value = now === undefined ? Number(printed) : now;
      const change = value - Number(printed);
      return { value, glow: change > 0 ? " boosted" : change < 0 ? " lowered" : "", note: change ? ` (${change > 0 ? "+" : ""}${change} from abilities)` : "" };
    };
    let power = "";
    if (has(info.power)) {
      const { value, glow, note } = current(info.power, live ? live.power : undefined);
      power = `<span class="stat stat-power${glow}" title="Power${note}">${esc(value)}</span>`;
    }
    let souls = "";
    if (soul && has(info.soul)) {
      const { value, glow, note } = current(info.soul, live ? live.soul : undefined);
      const icons = value <= 3 ? SOUL_ICON.repeat(value) : `${SOUL_ICON}<b>×${value}</b>`;
      souls = `<span class="stat-soul${glow}" title="Soul ${value}${note}">${icons}</span>`;
    }
    if (!corner && !power && !souls) return "";
    return `<span class="pcard-stats">${corner ? `<span class="stat-corner">${corner}</span>` : ""}${power}${souls}</span>`;
  }

  function backHtml() {
    return '<div class="pcard"><span class="pcard-back"></span></div>';
  }

  // A magnifying glass shown while hovering a pile of more than one card that its viewer may look
  // through: the full list of a public pile, or a search of our own deck.
  function searchHtml(owner, zone, count) {
    if (count < 2 || zone === "stock" || (owner !== "me" && !PUBLIC_PILES.includes(zone))) return "";
    const title = `${owner === "me" ? "Your" : `${board.opponent.name}'s`} ${LABELS[zone].toLowerCase()}`;
    const what = zone === "deck" ? `data-act='{"type":"search"}'` : `data-search-view='${esc(JSON.stringify({ owner, zone, title }))}'`;
    return `<button type="button" class="zone-search" ${what} title="Search ${esc(title.toLowerCase())}" aria-label="Search">🔍</button>`;
  }

  // The resolution zone's top card can go to the hand (✋, bottom left) or the waiting room (🪦,
  // bottom right) in one click.
  function resolutionButtonsHtml(card) {
    return `<div class="slot-pos slot-pos-bottom">${iconButton({ type: "move", uid: card.uid, to: "hand" }, "✋", "To hand")}</div>
      <div class="slot-pos slot-pos-right slot-pos-bottom">${iconButton({ type: "move", uid: card.uid, to: "waiting" }, "🪦", "Waiting room")}</div>`;
  }

  function pileHtml(side, owner, zone) {
    const pile = side.zones[zone];
    const hidden = !Array.isArray(pile);
    const count = hidden ? pile.count : pile.length;
    const top = hidden ? (count ? backHtml() : "") : cardHtml(pile[pile.length - 1], owner, zone);
    return `<div class="zone pile zone-${zone}" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${cxHtml(LABELS[zone])} <b>${count}</b></span>
      ${searchHtml(owner, zone, count)}
      ${zone === "deck" && owner === "me" ? `<div class="slot-pos slot-pos-right">${zoneMenuButton("deck")}</div>` : ""}
      ${zone === "deck" && owner === "me" && count ? `<div class="slot-pos slot-pos-center">${
        iconButton({ type: "move_top", from: "deck", to: "hand" }, "✋", "Draw")}</div>` : ""}
      ${zone === "resolution" && owner === "me" && count ? resolutionButtonsHtml(pile[pile.length - 1]) : ""}
      <div class="pile-top">${top || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  function pileCards(side, zone) {
    if (isMarkerPile(zone)) return (side.markers || {})[zone.slice("marker:".length)] || [];
    return side.zones[zone] || [];
  }

  // A character's markers: a small badge under it (top marker's picture, or a card back if it's
  // face down, plus the count). Click it like any pile; drop a card on it to add a marker.
  function markerHtml(side, owner, slot) {
    const markers = pileCards(side, `marker:${slot}`);
    if (!markers.length) return "";
    const top = markers[markers.length - 1];
    const info = top.card && !top.face_down ? cards[top.card] : null;
    const face = info ? `<img src="${esc(info.image)}" alt="" draggable="false">` : '<span class="pcard-back"></span>';
    return `<div class="marker-pile" data-pile="marker:${slot}" data-owner="${owner}" data-drop="${owner === "me" ? `marker:${slot}` : ""}"
        title="${markers.length} marker${markers.length === 1 ? "" : "s"} — click for options">
      <span class="marker-face">${face}</span><span>${markers.length} marker${markers.length === 1 ? "" : "s"}</span>
    </div>`;
  }

  // A small button showing just a symbol, with its name as the tooltip.
  function iconButton(action, symbol, label) {
    return `<button type="button" class="icon-button" title="${label}" aria-label="${label}"
      data-act='${esc(JSON.stringify(action))}'>${symbol}</button>`;
  }

  // Quick actions shown on one of our characters while hovering it: attack (⚔) for a standing
  // center-stage character on our turn, encore once reversed (with enough stock), and waiting
  // room (🪦). Stand, rest and reverse are the corner buttons (slotPosHtml); everything else is in
  // the full menu that opens beside the slot.
  // With turn rules on, a standing center character in our attack's declare step offers the
  // attacks the rules allow: front or side against the character facing it, direct if there's none.
  function slotActionsHtml(card, slot) {
    let quick = "";
    if (slot.startsWith("C") && card.pos === "stand") {
      if (!board.rules) {
        quick = iconButton({ type: "attack", uid: card.uid }, "⚔", "Attack");
      } else if (inPhase("attack") && board.attack && board.attack.step === "declare"
          && !(board.turn_number === 1 && board.attacks >= 1)) { // only one attack on turn 1
        const attack = (kind, label) => `<button type="button" data-act='${esc(JSON.stringify({ type: "attack", uid: card.uid, kind }))}'>⚔ ${label}</button>`;
        quick = board.opponent && board.opponent.stage[OPPOSITE[slot]]
          ? attack("front", "Front") + attack("side", "Side") : attack("direct", "Direct");
      }
    }
    return `<div class="slot-actions">
      ${quick}
      ${iconButton({ type: "move", uid: card.uid, to: "waiting" }, "🪦", "Waiting room")}
    </div>`;
  }

  // Quick moves shown on a hand card while hovering it: where characters and climaxes usually go
  // (events go to the resolution zone to be played), then "More" for the full menu. A character's
  // stage slots are rows of boxes: L / M / R for the center stage, L / R under it for the back stage.
  // The clock (🕒) and waiting room (🪦) are symbol buttons side by side.
  function handActionsHtml(card) {
    const move = (to, symbol) => iconButton({ type: "move", uid: card.uid, to }, symbol, LABELS[to]);
    const moveText = (to) => `<button type="button" data-act='${esc(JSON.stringify({ type: "move", uid: card.uid, to }))}'>→ ${cxHtml(LABELS[to])}</button>`;
    const info = card.card ? cards[card.card] : null;
    const type = info && info.type ? info.type.toLowerCase() : "";
    const clockDraw = inPhase("clock") ? iconButton({ type: "clock_draw", uid: card.uid }, "🕒+2", "Clock and draw 2") : "";
    const clock = inPhase("clock") ? move("clock", "🕒") : "";
    const reveal = board.reveal ? "" : iconButton({ type: "reveal", uid: card.uid }, "👁", "Reveal to your opponent");
    const piles = `<div class="hand-center">${clock}${move("waiting", "🪦")}${clockDraw}${reveal}</div>`;
    const affordable = canPay(info) && !colorMissing(card);
    let rows = "";
    if (type === "character" && affordable && inPhase("main")) {
      rows = `<div class="hand-center">${move("C1", "L")}${move("C2", "M")}${move("C3", "R")}</div>
        <div class="hand-center hand-back">${move("B1", "L")}${move("B2", "R")}</div>`;
    } else if (type === "climax" && affordable && inPhase("climax")) {
      rows = moveText("climax");
    } else if (type === "climax" && affordable && board.rules && inPhase("main")) {
      // Playing a climax from the main phase ends it: asks first (see renderClimaxConfirm).
      rows = `<button type="button" data-confirm-climax="${esc(card.uid)}">→ ${CX_HTML}</button>`;
    } else if (type !== "character" && type !== "climax" && affordable && inPhase("main")) {
      rows = moveText("resolution"); // events in our main phase
    }
    // Our counter step (the opponent is attacking): the counters we can play right now.
    const attack = board.attack;
    if (attack && attack.step === "counter" && (attack.counters || []).includes(card.uid)) {
      rows = `<button type="button" class="counter-button" data-act='${esc(JSON.stringify({ type: "counter", uid: card.uid }))}'>Counter</button>` + rows;
    }
    const needs = inPhase("main", "climax") ? colorMissing(card) : null;
    if (needs) rows = `<span class="hand-needs">Needs ${esc(needs)}</span>` + rows;
    rows += piles;
    return `<div class="hand-actions">
      ${rows}
      <button type="button" data-more>More…</button>
    </div>`;
  }

  const canEncore = () => board.me.zones.stock.count >= ENCORE_COST;
  // Our turn, in one of these phases.
  // With turn rules off every shortcut is offered, in any phase.
  const inPhase = (...phases) => !board.rules || (board.my_turn && phases.includes(board.phase));
  // Whether our stock covers a card's cost (cards with no cost are free; so is everything with the rules off).
  const canPay = (info) => !board.rules || !info || !info.cost || board.me.zones.stock.count >= info.cost;

  // The color the server says the color rule is holding this hand card back for, or null.
  const colorMissing = (card) => (board.needs_color || {})[card.uid] || null;

  // Which colors are in our clock and level zone (how many cards doesn't matter), in a strip
  // between the board and the hand, under the waiting room.
  function activeColorsHtml(side) {
    const present = new Set([...side.zones.clock, ...side.zones.level]
      .map((c) => (c.card && cards[c.card] ? cards[c.card].color : "")).filter(Boolean));
    const colors = [...COLORS.filter((c) => present.has(c)), ...[...present].filter((c) => !COLORS.includes(c))];
    const chips = colors.map((c) => `<span class="active-color color-${esc(c.toLowerCase())}">${esc(c)}</span>`).join("");
    return `<div class="active-colors"><span class="zone-label">Active colors</span>${chips || '<span class="muted small">none yet</span>'}</div>`;
  }

  // In the encore step every reversed character of ours gets two always-visible choices: encore
  // (pay 3 stock, stay rested; unavailable without the stock) or the waiting room. The turn can't
  // go on until each reversed character on the table has had one.
  function encoreChoiceHtml(card) {
    if (board.phase !== "encore" || card.pos !== "reverse") return "";
    const encore = canEncore() && !(board.no_encore || []).includes(card.uid)
      ? `<button type="button" data-act='${esc(JSON.stringify({ type: "encore", uid: card.uid }))}' title="Pay ${ENCORE_COST} stock, stay rested">Encore</button>`
      : `<button type="button" disabled title="Encore needs ${ENCORE_COST} stock">Encore</button>`;
    return `<div class="encore-choice" role="group" aria-label="Encore or waiting room">
      ${encore}${iconButton({ type: "move", uid: card.uid, to: "waiting" }, "🪦", "Waiting room")}
    </div>`;
  }

  // Any reversed character on either side (the encore step waits for them).
  const reversedLeft = () => [board.me, board.opponent].some((side) => side && Object.values(side.stage).some((c) => c && c.pos === "reverse"));

  const zoneMenuButton = (zone) => `<button type="button" class="zone-menu" title="More actions" aria-label="More actions" data-zone-menu="${zone}">[…]</button>`;

  // Small always-visible buttons in the corners of our occupied slots: stand (|) and rest (—) top
  // left, reverse (↷, center stage only) top right, and back to hand (✋) bottom left.
  function slotPosHtml(card, slot) {
    const button = (action, symbol, label, pressed = false) => `<button type="button" title="${label}" aria-label="${label}"
      aria-pressed="${pressed}" data-act='${esc(JSON.stringify(action))}'>${symbol}</button>`;
    const pos = (p, symbol, label) => button({ type: "position", uid: card.uid, pos: p }, symbol, label, card.pos === p);
    return `<div class="slot-pos">${pos("stand", "|", "Stand")}${pos("rest", "—", "Rest")}</div>
      <div class="slot-pos slot-pos-right">${slot.startsWith("C") ? pos("reverse", "↷", "Reverse") : ""}${zoneMenuButton(slot)}</div>
      <div class="slot-pos slot-pos-bottom">${button({ type: "move", uid: card.uid, to: "hand" }, "✋", "To hand")}</div>`;
  }

  // The ! button, on any card of ours with an ability that can be activated. It opens the list of
  // those abilities (see renderAbilityList); it's dimmed when none of them can be used right now.
  function activateButtonHtml(card) {
    const rows = (board.acts || {})[card.uid];
    if (!rows) return "";
    const ready = rows.some((row) => !row.why);
    const label = ready ? "Activate an ability" : `Ability: ${rows[0].why}`;
    return `<button type="button" class="ability-button${ready ? " ready" : ""}" title="${esc(label)}" aria-label="${esc(label)}" data-abilities="${esc(card.uid)}">!</button>`;
  }

  // Buttons between neighbouring slots of ours (in the main phase, with turn rules on): swap the two
  // characters, or an arrow moving one into the empty slot beside it.
  function slotLinksHtml(side, slot) {
    if (!inPhase("main")) return "";
    return SLOT_LINKS.filter(([first]) => first === slot).map(([first, second, direction]) => {
      const a = side.stage[first];
      const b = side.stage[second];
      if (!a && !b) return "";
      const [swap, forward, back] = LINK_SYMBOLS[direction];
      const [symbol, uid, to, label] = a && b ? [swap, a.uid, second, `Swap with ${LABELS[second].toLowerCase()}`]
        : a ? [forward, a.uid, second, `Move to ${LABELS[second].toLowerCase()}`]
        : [back, b.uid, first, `Move to ${LABELS[first].toLowerCase()}`];
      return `<button type="button" class="slot-link link-${direction}" title="${label}" aria-label="${label}"
        data-act='${esc(JSON.stringify({ type: "move", uid, to }))}'>${symbol}</button>`;
    }).join("");
  }

  // A stage slot's name sits outside it: above the center row, below the back row.
  function slotHtml(side, owner, slot) {
    const card = side.stage[slot];
    const center = slot.startsWith("C");
    const label = `<span class="zone-label slot-label">${LABELS[slot]}</span>`;
    return `<div class="slot-wrap ${center ? "slot-wrap-center" : "slot-wrap-back"}">
      ${center ? label : ""}
      <div class="zone slot" data-slot="${slot}" data-drop="${owner === "me" ? slot : ""}" data-owner="${owner}">
        ${cardHtml(card, owner, slot) || '<span class="zone-empty"></span>'}
        ${card && owner === "me" ? slotPosHtml(card, slot) + slotActionsHtml(card, slot) + encoreChoiceHtml(card) : ""}
        ${card && owner === "me" && board.acts && board.acts[card.uid] ? `<div class="slot-pos slot-pos-right slot-pos-bottom">${activateButtonHtml(card)}</div>` : ""}
        ${markerHtml(side, owner, slot)}
        ${owner === "me" ? slotLinksHtml(side, slot) : ""}
      </div>
      ${center ? "" : label}
    </div>`;
  }

  // The level zone: a narrow column, its (at most 4) cards stacked closely top to bottom so each
  // one's level and cost corner still shows.
  function levelHtml(side, owner) {
    const pile = side.zones.level;
    return `<div class="zone spread zone-level" data-pile="level" data-owner="${owner}" data-drop="${owner === "me" ? "level" : ""}">
      <span class="zone-label">${LABELS.level} <b>${pile.length}</b></span>
      ${searchHtml(owner, "level", pile.length)}
      <div class="level-stack">${pile.map((c) => cardHtml(c, owner, "level")).join("") || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  function spreadHtml(side, owner, zone) {
    const pile = side.zones[zone];
    return `<div class="zone spread zone-${zone}" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${LABELS[zone]} <b>${pile.length}</b></span>
      ${searchHtml(owner, zone, pile.length)}
      <div class="spread-cards">${pile.map((c) => cardHtml(c, owner, zone)).join("") || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  function matHtml(side, owner) {
    return layout === "classic" ? classicMatHtml(side, owner) : focusMatHtml(side, owner);
  }

  function classicMatHtml(side, owner) {
    // Rows from the middle of the table outwards; the opponent's side is mirrored by CSS.
    return `<div class="mat mat-${owner}">
      <div class="mat-row">${pileHtml(side, owner, "climax")}
        <div class="stage">${["C1", "C2", "C3"].map((s) => slotHtml(side, owner, s)).join("")}</div>
        ${pileHtml(side, owner, "resolution")}</div>
      <div class="mat-row">${pileHtml(side, owner, "stock")}
        <div class="stage">${["B1", "B2"].map((s) => slotHtml(side, owner, s)).join("")}</div>
        ${pileHtml(side, owner, "deck")}</div>
      <div class="mat-row">${levelHtml(side, owner)}${spreadHtml(side, owner, "clock")}
        ${pileHtml(side, owner, "memory")}${pileHtml(side, owner, "waiting")}</div>
    </div>`;
  }

  function focusMatHtml(side, owner) {
    // From the middle of the table outwards: the stage (center row, then back row) with stock and
    // memory above the climax zone on the left (the climax level with the middle of the stage),
    // level beneath that, and the clock under the stage (centered on the board). Resolution, deck
    // and waiting room run down the right edge.
    // The opponent's side is the same turned around by CSS.
    return `<div class="mat mat-${owner}">
      <div class="mat-left">
        <div class="mat-left-piles">${pileHtml(side, owner, "stock")}${pileHtml(side, owner, "memory")}</div>
        ${pileHtml(side, owner, "climax")}
      </div>
      <div class="mat-stage">
        <div class="stage">${["C1", "C2", "C3"].map((s) => slotHtml(side, owner, s)).join("")}</div>
        <div class="stage">${["B1", "B2"].map((s) => slotHtml(side, owner, s)).join("")}</div>
      </div>
      <div class="mat-right">${pileHtml(side, owner, "resolution")}${pileHtml(side, owner, "deck")}${pileHtml(side, owner, "waiting")}</div>
      ${levelHtml(side, owner)}${spreadHtml(side, owner, "clock")}
    </div>`;
  }

  function render() {
    if (!board) return;
    if (zoomCard) hideZoom();
    const me = board.me;
    const opp = board.opponent;
    const oppHand = opp ? opp.zones.hand.count : 0;
    boardEl.innerHTML = `
      ${opp ? `<div class="table-side side-opponent">
        <div class="hand hand-opponent"><span class="zone-label">${esc(opp.name)}'s hand <b>${oppHand}</b></span>
          <div class="hand-cards">${Array.from({ length: oppHand }, backHtml).join("")}</div></div>
        ${matHtml(opp, "opponent")}</div>` : ""}
      <div class="table-divider">${matchStarsHtml(0)}<span class="table-turn">${board.rps ? `Game ${gameNumber()} · rock, paper, scissors` : `${board.my_turn ? "Your turn" : `${esc(opp ? opp.name : "Opponent")}'s turn`} · game ${gameNumber()} · turn ${board.turn_number} · ${cxHtml(PHASES[board.phase])} phase`}</span>${matchStarsHtml(1)}</div>
      <div class="table-side side-me">
        ${matHtml(me, "me")}
        ${activeColorsHtml(me)}
        <div class="hand hand-me zone" data-drop="hand" data-owner="me"><span class="zone-label">Your hand <b>${me.zones.hand.length}</b></span>
          <div class="hand-cards">${me.zones.hand.map((c) => `<div class="hand-card">${cardHtml(c, "me", "hand")}${handActionsHtml(c)}</div>`).join("")}</div></div>
      </div>`;

    renderControls();
    announcePhase();

    const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 20;
    logEl.innerHTML = board.log.map((entry) => entry.chat
      ? `<p class="log-chat"><b>${esc(entry.who)}:</b> ${esc(entry.text)}</p>`
      : `<p>${entry.who ? `<b>${esc(entry.who)}</b> ` : ""}${cxHtml(entry.text)}</p>`).join("");
    if (atBottom) logEl.scrollTop = logEl.scrollHeight;

    renderModal();
    renderGameOver();
  }

  const gameNumber = () => board.game_number || 1;

  // The controls are built once and then only updated, so the damage amount being typed survives
  // the board redrawing on every opponent move.
  function renderControls() {
    if (!controlsEl.dataset.built) {
      controlsEl.dataset.built = "1";
      controlsEl.innerHTML = `
        <p class="panel-error" role="alert" data-error hidden></p>
        <div class="ability-dock" data-ability-dock role="alertdialog" aria-live="assertive" hidden></div>
        <p class="play-turn" data-turn></p>
        <div class="phase-area">
          <div class="phase-bar" role="group" aria-label="Turn phase" data-phase-bar>
            ${PHASE_NAMES.map((p) => `<button type="button" data-phase="${p}">${cxHtml(PHASES[p])}</button>`).join("")}
          </div>
          <div class="attack-panel" data-attack-panel hidden></div>
        </div>
        <p class="muted small phase-note"></p>
        <div class="play-buttons">
          <button type="button" data-act='{"type":"move_top","from":"deck","to":"resolution"}'>Trigger</button>
        </div>
        <form class="damage-form" data-damage>
          <label>Damage <input type="number" name="count" min="1" max="20" value="1" required></label>
          <button type="submit">Take damage</button>
        </form>
        <p class="muted small damage-note">Cards go to your clock one at a time; a climax cancels it all.</p>
        <div class="view-options">
          <div class="layout-switch" role="group" aria-label="Board view">
            ${Object.entries(LAYOUTS).map(([name, label]) => `<button type="button" data-layout="${name}">${label}</button>`).join("")}
          </div>
          <div class="layout-switch">
            <button type="button" data-animations title="Turn animations on or off">Animations</button>
          </div>
          <div class="layout-switch">
            <button type="button" data-rules title="Turn the turn rules on or off (both players have to agree)">Turn rules</button>
          </div>
        </div>
        <div class="rules-prompt" data-rules-prompt role="alertdialog" aria-live="assertive" hidden></div>`;
    }
    controlsEl.querySelectorAll("[data-layout]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.layout === layout));
    });
    controlsEl.querySelector("[data-animations]").setAttribute("aria-pressed", String(animations));
    const errorEl = controlsEl.querySelector("[data-error]");
    errorEl.textContent = error;
    errorEl.hidden = !error;
    renderRules();
    renderAbilityDock();
    const turn = controlsEl.querySelector("[data-turn]");
    turn.textContent = board.rps ? `Game ${gameNumber()} · rock, paper, scissors`
      : `${board.my_turn ? "Your turn" : "Opponent's turn"} · game ${gameNumber()} · turn ${board.turn_number} · ${PHASES[board.phase]} phase`;
    turn.classList.toggle("mine", board.my_turn);
    // Only the turn player moves the phase on, and only forwards.
    const at = PHASE_NAMES.indexOf(board.phase);
    controlsEl.querySelectorAll("[data-phase]").forEach((button) => {
      const index = PHASE_NAMES.indexOf(button.dataset.phase);
      button.classList.toggle("current", index === at);
      button.classList.toggle("past", index < at);
      if (index === at) button.setAttribute("aria-current", "step"); else button.removeAttribute("aria-current");
      button.disabled = !board.my_turn || index <= at || Boolean(board.ability || board.rps) || (board.rules && board.phase === "encore" && reversedLeft());
      if (button.dataset.phase === "mulligan" && button.closest("[data-phase-bar]")) button.hidden = board.phase !== "mulligan";
    });
    renderAttackPanel();
    const note = controlsEl.querySelector(".phase-note");
    const ability = board.ability;
    note.textContent = board.ability_show && board.ability_show.check ? "Trigger check…"
      : ability && !ability.mine ? `Waiting for ${ability.by} to resolve ${ability.resolving ? "an ability" : "their abilities"}…`
      : ability && ability.resolving && !ability.prompt ? "Finishing the ability…"
      : board.reveal && board.reveal.mine ? `Waiting for ${board.opponent ? board.opponent.name : "your opponent"} to close the card you revealed.`
      : board.discard ? (board.discard.mine ? `End phase: discard ${board.discard.count} to get down to 7.`
        : `Waiting for ${board.opponent ? board.opponent.name : "your opponent"} to discard down to 7…`)
      : board.mulligan ? (board.mulligan.me ? `Waiting for ${board.opponent ? board.opponent.name : "your opponent"} to finish their mulligan…` : "Mulligan: choose cards to swap.")
      : !board.rules ? "Turn rules are off: anything goes."
      : board.attack ? ""
      : board.phase === "encore" && reversedLeft() ? "Encore step: every reversed character needs Encore or 🪦 before the turn can end."
      : inPhase("draw") ? "Draw phase: draw a card (✋ on your deck) to move on."
      : "End clears your climax zone and passes the turn.";
    note.hidden = !note.textContent;
  }

  // During the attack phase (turn rules on) the phase bar gives way to the attack's steps, with a
  // randomly picked transition each time one takes over from the other.
  let panelMode = null;

  function renderAttackPanel() {
    const bar = controlsEl.querySelector("[data-phase-bar]");
    const panel = controlsEl.querySelector("[data-attack-panel]");
    const attack = board.rules && board.phase === "attack" ? board.attack : null;
    const mode = attack ? "attack" : "phases";
    if (attack) {
      const oppName = board.opponent ? board.opponent.name : "Your opponent";
      const kinds = { front: "Front attack", side: "Side attack", direct: "Direct attack" };
      const steps = Object.entries(ATTACK_STEPS).map(([step, label]) =>
        `<span class="attack-step${step === attack.step ? " current" : ""}"${step === attack.step ? ' aria-current="step"' : ""}>${label}</span>`).join("");
      let status = "";
      let buttons = "";
      if (attack.step === "declare") {
        status = board.my_turn ? "Choose an attacker: hover a standing center-stage character." : `Waiting for ${esc(oppName)} to attack…`;
        if (board.my_turn) buttons = '<button type="button" data-phase="encore">End attack phase</button>';
      } else {
        status = `${kinds[attack.kind]} · ${attack.soul} damage${attack.backup ? ` · backup +${attack.backup}` : ""}`;
        if (attack.step === "trigger" && attack.prompt) {
          status += board.my_turn ? ` — resolve the ${attack.prompt.kind} trigger.` : ` — waiting for ${esc(oppName)} to resolve a ${attack.prompt.kind} trigger…`;
        }
        if (attack.step === "counter") {
          status += board.my_turn ? ` — waiting for ${esc(oppName)} to counter…` : " — play a counter from your hand, or:";
          if (!board.my_turn) buttons = `<button type="button" data-act='{"type":"no_counter"}'>No counter</button>`;
        }
      }
      panel.innerHTML = `<p class="attack-title">⚔ Attack phase</p>
        <div class="attack-steps" role="list">${steps}</div>
        <p class="small attack-status">${status}</p>${buttons ? `<div class="attack-buttons">${buttons}</div>` : ""}`;
    }
    bar.hidden = Boolean(attack);
    panel.hidden = !attack;
    if (panelMode && panelMode !== mode && animations) {
      const shown = attack ? panel : bar;
      const effect = PANEL_SWAPS[Math.floor(Math.random() * PANEL_SWAPS.length)];
      shown.classList.remove(...PANEL_SWAPS);
      void shown.offsetWidth; // restart the animation
      shown.classList.add(effect);
      shown.addEventListener("animationend", () => shown.classList.remove(effect), { once: true });
    }
    panelMode = mode;
  }

  // A step of an ability the page can't do for us: it goes here, beside the board, so the cards can
  // still be moved by hand. The ability carries on once we say it's done.
  function renderAbilityDock() {
    const dock = controlsEl.querySelector("[data-ability-dock]");
    const ability = board.ability;
    const prompt = ability && ability.mine && ability.resolving ? ability.prompt : null;
    const manual = prompt && prompt.kind === "manual";
    dock.hidden = !manual;
    if (manual) {
      dock.innerHTML = `<p><b>Do this by hand</b>, then press Done:</p>
        <p class="small">${abilityText(prompt.text)}</p>
        <div class="attack-buttons">
          <button type="button" data-act='{"type":"ability_answer"}'>Done</button>
          <button type="button" data-act='{"type":"ability_stop"}' title="Leave the rest of this ability undone">Stop</button>
        </div>`;
    }
  }

  // The turn rules toggle: asking sends the other player a prompt; the rules change only if they agree.
  function renderRules() {
    const button = controlsEl.querySelector("[data-rules]");
    const request = board.rules_request;
    button.setAttribute("aria-pressed", String(board.rules));
    button.textContent = request && request.mine ? "Turn rules: asked…" : `Turn rules: ${board.rules ? "on" : "off"}`;
    button.title = request && request.mine ? "Waiting for your opponent. Click to take the request back."
      : `Ask your opponent to turn the turn rules ${board.rules ? "off" : "on"}`;
    const prompt = controlsEl.querySelector("[data-rules-prompt]");
    const asked = request && !request.mine;
    prompt.hidden = !asked;
    if (asked) {
      prompt.innerHTML = `<p><b>${esc(board.opponent ? board.opponent.name : "Your opponent")}</b> wants to turn the turn rules
        <b>${request.on ? "on" : "off"}</b>. ${request.on ? "Phases and attacks will follow the rules again." : "Phases, attacks and costs will no longer be enforced."}</p>
        <div class="attack-buttons">
          <button type="button" data-act='{"type":"rules_answer","accept":true}'>Agree</button>
          <button type="button" data-act='{"type":"rules_answer","accept":false}'>Keep them ${board.rules ? "on" : "off"}</button>
        </div>`;
    }
  }

  // Game 1 starts with rock, paper, scissors for who goes first: picks stay secret until both are
  // in, a tie goes again, and the result shows for a moment before the mulligan.
  const RPS_HANDS = { rock: ["✊", "Rock"], paper: ["✋", "Paper"], scissors: ["✌️", "Scissors"] };

  function renderRps() {
    const rps = board.rps;
    const name = board.opponent ? board.opponent.name : "Your opponent";
    const hand = (choice, label, extra = "") => `<div class="rps-hand ${extra}"><span class="rps-symbol" role="img" aria-label="${RPS_HANDS[choice][1]}">${RPS_HANDS[choice][0]}</span><span class="small muted">${esc(label)}</span></div>`;
    const faceOff = rps.last ? `<div class="rps-faceoff">${hand(rps.last.me, "You", rps.won === false ? "rps-lost" : "")}<span class="rps-vs">vs</span>${hand(rps.last.opponent, name, rps.won ? "rps-lost" : "")}</div>` : "";
    let body;
    if (rps.won !== null) {
      body = `<p class="rps-result ${rps.won ? "rps-won" : "rps-beaten"}">${rps.won ? "You win! You go first." : `${esc(name)} wins and goes first.`}</p>`;
    } else if (rps.mine) {
      body = `<p>You chose ${RPS_HANDS[rps.mine][1].toLowerCase()}. Waiting for ${esc(name)}…</p>`;
    } else {
      body = `<p>${rps.last ? "A tie! Choose again." : "The winner goes first."}${rps.opponent_chose ? ` ${esc(name)} has chosen.` : ""}</p>
        <div class="rps-choices">${Object.entries(RPS_HANDS).map(([choice, [symbol, label]]) => `<button type="button" data-act='${esc(JSON.stringify({ type: "rps", choice }))}'>
          <span class="rps-symbol" aria-hidden="true">${symbol}</span>${label}</button>`).join("")}</div>`;
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box confirm-box rps-box" role="dialog" aria-label="Rock, paper, scissors">
      <h2>Rock, paper, scissors</h2>${faceOff}${body}</div>`;
  }

  // Games won in this series of rematches, either side of the turn counter: the first player on the
  // left and the second on the right, on both players' screens.
  const MAX_STARS = 8;
  function matchStarsHtml(index) {
    const { name, wins } = (board.match_wins || [])[index] || { name: "", wins: 0 };
    const stars = wins > MAX_STARS ? `★ ×${wins}` : "★".repeat(wins);
    const label = wins ? `${esc(name)}: ${wins} win${wins === 1 ? "" : "s"}` : "";
    return `<span class="match-stars match-stars-${index ? "right" : "left"}"${wins ? ` title="${label}" aria-label="${label}"` : ""}>${stars}</span>`;
  }

  // Victory or Defeat, over everything, until both players ask for a rematch or either ends the match.
  // Built once per game so its entrance plays once; only the buttons change as the other player answers.
  const CREST = `<svg class="game-over-crest" viewBox="0 0 240 150" aria-hidden="true">
    <defs><linearGradient id="crest-metal" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="var(--crest-light)"/><stop offset=".5" stop-color="var(--crest-mid)"/><stop offset="1" stop-color="var(--crest-dark)"/>
    </linearGradient></defs>
    <path fill="url(#crest-metal)" d="M96 60 L14 22 L30 58 L6 56 L34 86 L16 92 L62 108 L96 96 Z"/>
    <path fill="url(#crest-metal)" d="M144 60 L226 22 L210 58 L234 56 L206 86 L224 92 L178 108 L144 96 Z"/>
    <path fill="url(#crest-metal)" d="M120 6 L164 32 L164 84 L120 144 L76 84 L76 32 Z"/>
    <path fill="var(--crest-core)" d="M120 24 L150 42 L150 80 L120 122 L90 80 L90 42 Z"/>
    <path fill="var(--crest-gem)" d="M120 44 L136 58 L120 92 L104 58 Z"/>
  </svg>`;
  let gameOverEl = null;

  function renderGameOver() {
    const over = board.game_over;
    if (!over) {
      if (gameOverEl) gameOverEl.remove();
      gameOverEl = null;
      return;
    }
    if (!gameOverEl) {
      hideMenu();
      hideZoom();
      gameOverEl = document.createElement("div");
      gameOverEl.className = `game-over ${over.won ? "game-over-victory" : "game-over-defeat"}${animations ? " animated" : ""}`;
      gameOverEl.setAttribute("role", "alertdialog");
      gameOverEl.setAttribute("aria-label", over.won ? "Victory" : "Defeat");
      const loser = over.won ? (board.opponent ? board.opponent.name : "Your opponent") : "You";
      const reason = over.reason === "deck" ? `${esc(loser)} can't refresh ${over.won ? "their" : "your"} deck.` : `${esc(loser)} reached level 4.`;
      gameOverEl.innerHTML = `<div class="game-over-rays"></div>
        <div class="game-over-banner">${CREST}<h2 class="game-over-word">${over.won ? "Victory" : "Defeat"}</h2>
          <p class="game-over-reason">${reason}</p>
          <p class="game-over-status" data-game-over-status></p>
          <div class="game-over-buttons" data-game-over-buttons></div></div>`;
      root.appendChild(gameOverEl);
    }
    const name = board.opponent ? board.opponent.name : "Your opponent";
    gameOverEl.querySelector("[data-game-over-status]").textContent = error
      || (over.rematch ? `Waiting for ${name} to accept the rematch…` : over.opponent_rematch ? `${name} wants a rematch.` : "");
    gameOverEl.querySelector("[data-game-over-buttons]").innerHTML = `
      <button type="button" data-act='{"type":"rematch"}'${over.rematch ? " disabled" : ""}>Rematch</button>
      <button type="button" class="game-over-end" data-act='{"type":"end_match"}'>End match</button>`;
  }

  function renderModal() {
    if (board.game_over) {
      modalEl.hidden = true;
      return;
    }
    if (board.rps) return renderRps();
    if (board.reveal && board.reveal.card) return renderReveal();
    if (modal && modal.confirmClimax) return renderClimaxConfirm();
    if (board.mulligan && !board.mulligan.me) return renderMulligan();
    if (board.discard && board.discard.mine) return renderDiscard();
    if (board.level_up_pending) return renderLevelUp();
    if (board.ability && board.ability.mine && !board.ability.resolving) return renderAbilityQueue();
    if (board.ability && board.ability.mine && board.ability.prompt && board.ability.prompt.kind !== "manual") return renderAbilityPrompt();
    if (modal && modal.abilities) return renderAbilityList();
    if (board.my_turn && board.attack && board.attack.step === "trigger" && board.attack.prompt && !board.ability_show) return renderTriggerPrompt();
    if (!modal) {
      modalEl.hidden = true;
      return;
    }
    let list;
    let owner = "me";
    if (modal.revealed) {
      list = modal.revealed.map((c) => cardHtml(c, "me", "deck"));
    } else {
      owner = modal.owner;
      const side = owner === "me" ? board.me : board.opponent;
      list = pileCards(side, modal.zone).slice().reverse().map((c) => {
        const button = owner === "me" ? activateButtonHtml(c) : "";
        return button ? `<div class="trigger-option">${cardHtml(c, owner, modal.zone)}${button}</div>` : cardHtml(c, owner, modal.zone);
      });
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="${esc(modal.title)}">
      <div class="play-modal-head"><h2>${esc(modal.title)}</h2><button type="button" data-close>Close</button></div>
      <p class="muted small">${owner === "me" ? "Click a card to move it. Top of the pile first." : "Top of the pile first."}</p>
      <div class="play-modal-cards">${list.join("") || '<p class="empty">Empty.</p>'}</div>
    </div>`;
  }

  // Ability text, with CX marks and line breaks.
  const abilityText = (text) => cxHtml(text).replace(/\n/g, "<br>");

  // A small picture of the card an ability belongs to.
  function abilitySourceHtml(pk) {
    const info = pk ? cards[pk] : null;
    return info ? `<img class="ability-source" src="${esc(info.image)}" alt="${esc(info.name)}" data-card="${pk}">` : "";
  }

  // Abilities of ours that have triggered: each can be triggered or skipped, in any order.
  function renderAbilityQueue() {
    const queue = board.ability.queue;
    const send = (entry, accept, label, extra = "") => `<button type="button" ${extra} data-act='${esc(JSON.stringify({ type: "ability_trigger", id: entry.id, accept }))}'>${label}</button>`;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box ability-box" role="alertdialog" aria-label="Ability triggered">
      <div class="play-modal-head"><h2>Ability triggered${queue.length > 1 ? `: ${queue.length} to resolve` : ""}</h2></div>
      ${queue.length > 1 ? '<p class="muted small">Resolve them in any order.</p>' : ""}
      ${queue.map((entry) => {
        const info = cards[entry.card];
        return `<div class="ability-row">${abilitySourceHtml(entry.card)}
          <div><p class="play-preview-name">${esc(info ? info.name : "Card")}</p>
            <div class="card-peek-text">${abilityText(entry.text)}</div>
            <div class="trigger-buttons">${send(entry, true, entry.event ? "Play it" : "Trigger")}${send(entry, false, "Skip", 'class="button-cancel"')}</div>
          </div></div>`;
      }).join("")}
    </div>`;
  }

  // An ability being resolved needs an answer: cards to pick, or one choice from a list.
  function renderAbilityPrompt() {
    const ability = board.ability;
    const prompt = ability.prompt;
    const info = cards[ability.card];
    const options = new Set(prompt.options && prompt.kind === "cards" ? prompt.options : []);
    abilityPicks = abilityPicks.filter((uid) => options.has(uid));
    // The other player's ability can't be stopped from here, though it may be asking us to choose.
    const stopButton = ability.can_stop ? '<button type="button" class="button-cancel" data-act=\'{"type":"ability_stop"}\' title="Leave the rest of this ability undone">Stop</button>' : "";
    const label = (card) => (card.where && LABELS[card.where] ? `<span class="muted small">${esc(LABELS[card.where])}</span>` : "");
    let body;
    if (prompt.kind === "cards") {
      const count = abilityPicks.length;
      const need = prompt.min === prompt.max ? `${prompt.max}` : `${prompt.min}–${prompt.max}`;
      const ready = count >= prompt.min && count <= prompt.max;
      const ordered = prompt.for === "order";
      body = `<p class="small"><b>${esc(prompt.title)}</b> (${count} of ${need} chosen)</p>
        <div class="play-modal-cards">${prompt.cards.map((c) => {
          const can = options.has(c.uid);
          const picked = abilityPicks.indexOf(c.uid);
          return `<div class="trigger-option"><div class="level-pick${picked >= 0 ? " picked" : ""}${can ? "" : " unpickable"}"${can ? ` role="button" tabindex="0" aria-pressed="${picked >= 0}" data-ability-pick="${esc(c.uid)}"` : ""}>
            ${cardHtml(c, "view", "ability")}${ordered && picked >= 0 ? `<span class="ability-order">${picked + 1}</span>` : ""}</div>${label(c)}</div>`;
        }).join("")}</div>
        <div class="trigger-buttons"><button type="button" data-ability-submit${ready ? "" : " disabled"}>${count || prompt.min ? "Confirm" : "Choose none"}</button>${stopButton}</div>`;
    } else {
      const shown = prompt.cards || [];
      body = `<p class="small"><b>${abilityText(prompt.title)}</b></p>
        ${shown.length ? `<div class="play-modal-cards">${shown.map((c) => `<div class="trigger-option">${cardHtml(c, "view", "ability")}${label(c)}</div>`).join("")}</div>` : ""}
        <div class="trigger-buttons ability-choices">${prompt.options.map((option) => `<button type="button" data-act='${esc(JSON.stringify({ type: "ability_answer", value: option.value }))}'>${abilityText(option.label)}</button>`).join("")}${stopButton}</div>`;
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box ability-box" role="dialog" aria-label="Resolve ability">
      <div class="ability-row">${abilitySourceHtml(ability.card)}
        <div><p class="play-preview-name">${esc(info ? info.name : "Ability")}</p>
          <div class="card-peek-text">${abilityText(ability.text)}</div></div></div>
      ${body}
    </div>`;
  }

  // The ! button's list: this card's activated abilities, each with what's stopping it, if anything.
  // Asks first because activating pays the cost straight away.
  function renderAbilityList() {
    const rows = (board.acts || {})[modal.abilities];
    if (!rows) {
      modal = null;
      return renderModal();
    }
    const pk = rows[0].card;
    const info = cards[pk];
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box ability-box" role="dialog" aria-label="Activate an ability">
      <div class="play-modal-head"><h2>${esc(info ? info.name : "Abilities")}</h2><button type="button" data-close>Close</button></div>
      ${rows.map((row) => `<div class="ability-row">${abilitySourceHtml(pk)}
        <div><div class="card-peek-text">${abilityText(row.text)}</div>
          <div class="trigger-buttons">${row.why
            ? `<button type="button" disabled>Activate</button> <span class="muted small">Can't now: ${esc(row.why)}</span>`
            : `<button type="button" data-act='${esc(JSON.stringify({ type: "activate", uid: modal.abilities, index: row.index }))}' data-close-after>Activate</button>`}</div></div></div>`).join("")}
    </div>`;
  }

  // A card the opponent revealed from their hand: shown large with its text until we close it
  // (their turn waits for that).
  function renderReveal() {
    const info = cards[board.reveal.card];
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box reveal-box" role="dialog" aria-label="Revealed card">
      <div class="play-modal-head"><h2>${esc(board.reveal.by)} reveals</h2>
        <button type="button" data-act='{"type":"close_reveal"}'>Close</button></div>
      ${info ? `<div class="reveal-card"><img src="${esc(info.image)}" alt="${esc(info.name)}">
        <div><p class="play-preview-name">${esc(info.name)}</p>
          <p class="small muted">${esc([info.type, info.color, info.level != null ? `Level ${info.level}` : "", info.cost != null ? `Cost ${info.cost}` : "",
            info.power != null ? `Power ${info.power}` : "", info.soul != null ? `Soul ${info.soul}` : ""].filter(Boolean).join(" · "))}</p>
          ${info.text ? `<div class="card-peek-text">${esc(info.text).replace(/\n/g, "<br>")}</div>` : ""}</div></div>` : ""}
    </div>`;
  }

  // Playing a climax from the main phase ends the main phase: confirm first.
  function renderClimaxConfirm() {
    const card = board.me.zones.hand.find((c) => c.uid === modal.confirmClimax);
    const info = card && cards[card.card];
    if (!card || !inPhase("main")) {
      modal = null;
      return renderModal();
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box confirm-box" role="alertdialog" aria-label="Play a climax">
      <div class="play-modal-head"><h2>Play ${CX_HTML}${info ? ` ${esc(info.name)}` : ""}?</h2></div>
      <p>Playing a climax card ends your main phase: it goes into your ${CX_HTML} zone, and your attack phase follows.</p>
      <div class="trigger-buttons">
        <button type="button" data-act='${esc(JSON.stringify({ type: "move", uid: card.uid, to: "climax", end_main: true }))}'>Play it</button>
        <button type="button" class="button-cancel" data-close>Cancel</button>
      </div>
    </div>`;
  }

  // The end phase's discard: pick exactly enough cards to bring the hand down to 7.
  function renderDiscard() {
    const hand = board.me.zones.hand;
    const need = board.discard.count;
    for (const uid of [...discardPicks]) if (!hand.some((c) => c.uid === uid)) discardPicks.delete(uid);
    const picked = discardPicks.size;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="Discard">
      <div class="play-modal-head"><h2>Discard ${need} card${need === 1 ? "" : "s"}</h2></div>
      <p class="muted small">Your hand is over 7 at the end of your turn. Choose ${need} card${need === 1 ? "" : "s"} for your waiting room (${picked} of ${need} chosen).</p>
      <div class="play-modal-cards">${hand.map((c) => `<div class="level-pick${discardPicks.has(c.uid) ? " picked" : ""}" role="button"
        tabindex="0" aria-pressed="${discardPicks.has(c.uid)}" data-discard-pick="${esc(c.uid)}">${cardHtml(c, "me", "discard")}</div>`).join("")}</div>
      <div class="trigger-buttons"><button type="button" data-discard-submit${picked === need ? "" : " disabled"}>Discard ${picked === need ? "them" : `${need}`}</button></div>
    </div>`;
  }

  // Turn 1's mulligan: pick any cards in the hand to swap for new ones (or keep it as it is).
  function renderMulligan() {
    const hand = board.me.zones.hand;
    for (const uid of [...mulliganPicks]) if (!hand.some((c) => c.uid === uid)) mulliganPicks.delete(uid);
    const count = mulliganPicks.size;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="Mulligan">
      <div class="play-modal-head"><h2>Mulligan</h2></div>
      <p class="muted small">Pick any cards to put into your waiting room; you'll draw as many new ones.</p>
      <div class="play-modal-cards">${hand.map((c) => `<div class="level-pick${mulliganPicks.has(c.uid) ? " picked" : ""}" role="button"
        tabindex="0" aria-pressed="${mulliganPicks.has(c.uid)}" data-mulligan-pick="${esc(c.uid)}">${cardHtml(c, "me", "mulligan")}</div>`).join("")}</div>
      <div class="trigger-buttons"><button type="button" data-mulligan-submit>${count ? `Mulligan ${count} card${count === 1 ? "" : "s"}` : "Keep my hand"}</button></div>
    </div>`;
  }

  // A trigger with a choice in it, for the attacker (see trigger_prompt in game.py).
  const TRIGGERS = {
    comeback: { title: "Comeback trigger", text: "You may return a character from your waiting room to your hand.", to: { hand: "→ Hand" } },
    gate: { title: "Gate trigger", text: "You may return a climax from your waiting room to your hand.", to: { hand: "→ Hand" } },
    choice: { title: "Choice trigger", text: "You may put a character with a soul trigger from your waiting room into your hand or your stock.", to: { hand: "→ Hand", stock: "→ Stock" } },
    standby: { title: "Standby trigger", text: "You may put a character of up to your level + 1 from your waiting room onto your stage, rested.", to: { C1: "Center L", C2: "Center M", C3: "Center R", B1: "Back L", B2: "Back R" } },
    treasure: { title: "Treasure trigger", text: "The treasure went to your hand. Put the top card of your deck into your stock?" },
  };

  function renderTriggerPrompt() {
    const prompt = board.attack.prompt;
    const trigger = TRIGGERS[prompt.kind];
    const choice = (action, label) => `<button type="button" data-act='${esc(JSON.stringify({ type: "trigger_choice", ...action }))}'>${label}</button>`;
    let body;
    if (prompt.kind === "treasure") {
      body = `<div class="trigger-buttons">${choice({ accept: true }, "Yes, to my stock")}${choice({ accept: false }, "No")}</div>`;
    } else {
      const options = board.me.zones.waiting.filter((c) => prompt.options.includes(c.uid));
      body = `<div class="play-modal-cards">${options.map((c) => `<div class="trigger-option">${cardHtml(c, "me", "waiting")}
          <div class="trigger-buttons">${Object.entries(trigger.to).map(([to, label]) => choice({ uid: c.uid, to }, label)).join("")}</div>
        </div>`).join("")}</div>
        <div class="trigger-buttons">${choice({}, "Choose nothing")}</div>`;
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="${trigger.title}">
      <div class="play-modal-head"><h2>${trigger.title}</h2></div>
      <p class="muted small">${trigger.text}</p>${body}
    </div>`;
  }

  // 7 or more cards in our clock: choose which of the first 7 goes to the level zone (the rest go to
  // the waiting room). This stays up until a card is chosen.
  function renderLevelUp() {
    const first = board.me.zones.clock.slice(0, LEVEL_UP_AT);
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="Level up">
      <div class="play-modal-head"><h2>Level up to level ${board.me.zones.level.length + 1}</h2></div>
      <p class="muted small">Choose a card from your clock for your level zone. The other ${LEVEL_UP_AT - 1} go to the waiting room.</p>
      <div class="play-modal-cards">${first.map((c) => `<div class="level-pick" role="button" tabindex="0"
        data-level-up="${esc(c.uid)}" aria-label="Level up with this card">${cardHtml(c, "me", "clock")}</div>`).join("")}</div>
    </div>`;
  }

  // A new phase's name (in the side panel, on the board and on the phase bar) comes in with a
  // randomly picked little animation.
  let phaseKey = null;
  let phaseWas = null;

  // The phase that's ending in the middle of the screen, replaced by the new one.
  const PHASE_ICONS = { mulligan: "🔄", stand: "⬆", draw: "🃏", clock: "🕒", main: "🎯", climax: "⚡", attack: "⚔", encore: "♻", end: "🏁" };
  const phaseCard = (phase, which) => `<div class="phase-show-card ${which}"><span class="phase-show-icon" aria-hidden="true">${PHASE_ICONS[phase] || ""}</span>
    <span class="phase-show-name">${cxHtml(PHASES[phase] || phase)}</span><span class="phase-show-word">phase</span></div>`;

  function showPhaseChange(from, to) {
    document.querySelectorAll(".phase-show").forEach((el) => el.remove());
    const el = document.createElement("div");
    el.className = "phase-show";
    el.style.setProperty("--phase-ms", `${PHASE_PAUSE_MS}ms`);
    el.setAttribute("aria-live", "polite");
    el.innerHTML = phaseCard(from, "phase-show-out") + phaseCard(to, "phase-show-in");
    document.body.appendChild(el);
    el.querySelector(".phase-show-in").addEventListener("animationend", () => el.remove());
  }

  function announcePhase() {
    const key = `${board.turn_number}:${board.phase}`;
    if (phaseKey && key !== phaseKey && animations && phaseWas && phaseWas !== board.phase && !board.game_over && !board.rps) {
      showPhaseChange(phaseWas, board.phase);
    }
    phaseWas = board.phase;
    if (phaseKey && key !== phaseKey && animations) {
      const effect = PHASE_NAME_FX[Math.floor(Math.random() * PHASE_NAME_FX.length)];
      const names = [controlsEl.querySelector("[data-turn]"), boardEl.querySelector(".table-turn"),
        controlsEl.querySelector("[data-phase].current")];
      for (const el of names.filter(Boolean)) {
        el.classList.remove(...PHASE_NAME_FX);
        void el.offsetWidth; // restart the animation
        el.classList.add(effect);
        el.addEventListener("animationend", () => el.classList.remove(effect), { once: true });
      }
    }
    phaseKey = key;
  }

  // --- Card preview ----------------------------------------------------------------------------

  function showPreview(pk) {
    const info = cards[pk];
    if (!info) return;
    const stats = [
      info.type, info.rarity, info.color,
      info.level != null ? `Level ${info.level}` : "", info.cost != null ? `Cost ${info.cost}` : "",
      info.power != null ? `Power ${info.power}` : "", info.soul != null ? `Soul ${info.soul}` : "",
      info.trigger ? `Trigger: ${info.trigger}` : "",
    ].filter(Boolean).join(" · ");
    previewEl.innerHTML = `<img src="${esc(info.image)}" alt="">
      <p class="muted small">${esc(info.serial)}</p><p class="play-preview-name">${esc(info.name)}</p>
      <p class="small">${esc(stats)}</p>${info.traits ? `<p class="small muted">${esc(info.traits)}</p>` : ""}
      ${info.text ? `<div class="card-peek-text">${esc(info.text).replace(/\n/g, "<br>")}</div>` : ""}`;
  }

  root.addEventListener("mouseover", (event) => {
    const el = event.target.closest(".pcard[data-card]");
    if (el) showPreview(el.dataset.card);
  });

  // --- Enlarged card art after resting the mouse on a card -------------------------------------

  const ZOOM_DELAY_MS = 0;
  const zoomEl = document.createElement("div");
  zoomEl.className = "play-zoom";
  zoomEl.hidden = true;
  document.body.appendChild(zoomEl);
  let zoomTimer = null;
  let zoomCard = null; // the .pcard element being hovered

  function hideZoom() {
    clearTimeout(zoomTimer);
    zoomTimer = null;
    zoomCard = null;
    zoomEl.hidden = true;
  }

  function showZoom(el) {
    const info = cards[el.dataset.card];
    if (!info) return;
    zoomEl.innerHTML = `<img src="${esc(info.image)}" alt="${esc(info.name)}">`;
    zoomEl.classList.toggle("zoom-climax", (info.type || "").toLowerCase() === "climax");
    zoomEl.hidden = false;
  }

  root.addEventListener("mousemove", (event) => {
    const el = event.target.closest(".pcard[data-card]");
    if (el === zoomCard) return;
    hideZoom();
    if (!el) return;
    zoomCard = el;
    zoomTimer = setTimeout(() => {
      if (zoomCard === el && el.isConnected) showZoom(el);
    }, ZOOM_DELAY_MS);
  });
  root.addEventListener("mouseleave", hideZoom);
  root.addEventListener("mousedown", hideZoom);
  root.addEventListener("dragstart", hideZoom);
  window.addEventListener("scroll", hideZoom, { passive: true });

  // --- Menus -----------------------------------------------------------------------------------

  let menuZone = null; // the deck or stage slot whose [...] menu is open, if any

  function showMenu(x, y, title, items) {
    menuZone = null;
    menuEl.classList.remove("see-through");
    menuEl.innerHTML = `<p class="play-menu-title">${esc(title)}</p>` + items.map((item) => item === "-"
      ? "<hr>"
      : `<button type="button" data-menu-item='${esc(JSON.stringify(item.action || {}))}' ${item.prompt ? `data-prompt="${esc(item.prompt)}" data-prompt-default="${esc(item.promptDefault ?? 1)}"` : ""} ${item.view ? `data-view='${esc(JSON.stringify(item.view))}'` : ""}>${esc(item.label)}</button>`).join("");
    menuEl.hidden = false;
    const box = menuEl.getBoundingClientRect();
    menuEl.style.left = `${Math.min(x, window.innerWidth - box.width - 8)}px`;
    menuEl.style.top = `${Math.min(y, window.innerHeight - box.height - 8)}px`;
  }

  function hideMenu() {
    menuEl.hidden = true;
    menuZone = null;
  }

  // The [...] button on our deck and our occupied stage slots opens its full menu beside the zone.
  function openZoneMenu(zone, zoneEl) {
    const card = zone === "deck" ? null : zoneEl.querySelector(".pcard[data-uid]");
    const [title, items] = zone === "deck" ? pileMenu("deck", "me") : cardMenu(card);
    const box = zoneEl.getBoundingClientRect();
    showMenu(box.right + 6, box.top, title, items);
    menuEl.classList.toggle("see-through", zone !== "deck"); // over the stage: let the board show through
    const width = menuEl.getBoundingClientRect().width;
    if (box.right + 6 + width > window.innerWidth - 8) { // no room on the right: open to the left
      menuEl.style.left = `${Math.max(8, box.left - 6 - width)}px`;
    }
    menuZone = zone;
  }

  function cardMenu(el) {
    const uid = el.dataset.uid;
    const zone = el.dataset.zone;
    const info = el.dataset.card ? cards[el.dataset.card] : null;
    const items = [];
    if (["C1", "C2", "C3"].includes(zone) && el.classList.contains("pos-stand") && board.my_turn) {
      items.push({ label: "⚔ Attack (rest + trigger check)", action: { type: "attack", uid } }, "-");
    }
    if (STAGE.includes(zone) && el.classList.contains("pos-reverse") && canEncore()) {
      items.push({ label: `Encore: pay ${ENCORE_COST} stock, rest`, action: { type: "encore", uid } }, "-");
    }
    if (["C1", "C2", "C3", "B1", "B2"].includes(zone)) {
      items.push({ label: "Stand", action: { type: "position", uid, pos: "stand" } },
        { label: "Rest", action: { type: "position", uid, pos: "rest" } },
        { label: "Reverse", action: { type: "position", uid, pos: "reverse" } }, "-");
      // For when an ability isn't doing what it should: back to normal at the end of the turn.
      const live = (board.stats || {})[uid];
      items.push({ label: "Set power…", action: { type: "set_power", uid }, prompt: "Set this card's power until the end of the turn:", promptDefault: live ? live.power : (info && info.power) || 0 });
      if (live && live.manual) items.push({ label: "Put power back to normal", action: { type: "set_power", uid, clear: true } });
      items.push("-");
    }
    if (!["hand", "deck", "stock"].includes(zone)) {
      items.push({ label: el.classList.contains("face-down") ? "Turn face up" : "Turn face down", action: { type: "flip", uid } }, "-");
    }
    const unaffordable = zone === "hand" && (!canPay(info) || colorMissing({ uid }));
    for (const to of MOVE_TARGETS) {
      if (unaffordable && PLAY_ZONES.includes(to)) continue;
      if (to !== zone) items.push({ label: `→ ${LABELS[to]}`, action: { type: "move", uid, to } });
    }
    items.push({ label: "→ Deck (top)", action: { type: "move", uid, to: "deck", where: "top" } },
      { label: "→ Deck (bottom)", action: { type: "move", uid, to: "deck", where: "bottom" } });
    items.push(...markerItems((slot, face_down) => ({ type: "move", uid, to: `marker:${slot}`, face_down }),
      (slot) => slot !== zone && `marker:${slot}` !== zone));
    return [info ? info.name : "Card", items];
  }


  // "Marker under <character>" choices, face up and face down, for each of our occupied stage slots.
  function markerItems(makeAction, allowed = () => true, prefix = "Marker") {
    const items = [];
    for (const slot of STAGE) {
      const character = board.me.stage[slot];
      if (!character || !allowed(slot)) continue;
      const info = character.card ? cards[character.card] : null;
      const under = `${LABELS[slot].toLowerCase()}${info ? ` (${info.name})` : ""}`;
      items.push({ label: `${prefix} under ${under}, face up`, action: makeAction(slot, false) },
        { label: `${prefix} under ${under}, face down`, action: makeAction(slot, true) });
    }
    return items.length ? ["-", ...items] : [];
  }

  function pileMenu(zone, owner) {
    const view = { owner, zone, title: `${owner === "me" ? "Your" : `${board.opponent.name}'s`} ${LABELS[zone].toLowerCase()}` };
    if (owner !== "me") {
      return PUBLIC_PILES.includes(zone) || isMarkerPile(zone) ? [LABELS[zone], [{ label: "View all", view }]] : null;
    }
    if (isMarkerPile(zone)) {
      return [LABELS[zone], [
        { label: "View all", view },
        { label: "All → waiting room", action: { type: "move_all", from: zone, to: "waiting" } },
        { label: "All → hand", action: { type: "move_all", from: zone, to: "hand" } },
        { label: "All → stock", action: { type: "move_all", from: zone, to: "stock" } },
      ]];
    }
    if (zone === "deck") {
      return ["Deck", [
        { label: "Shuffle", action: { type: "shuffle" } },
        { label: "Top → waiting room", action: { type: "move_top", from: "deck", to: "waiting" } },
        { label: "Bottom → waiting room", action: { type: "move_top", from: "deck", to: "waiting", where: "bottom" } },
        "-",
        { label: "Draw 1", action: { type: "move_top", from: "deck", to: "hand" } },
        { label: "Draw…", action: { type: "move_top", from: "deck", to: "hand" }, prompt: "How many cards to draw?" },
        "-",
        { label: "Take damage…", action: { type: "damage" }, prompt: "How much damage?" },
        { label: "Trigger: top → resolution", action: { type: "move_top", from: "deck", to: "resolution" } },
        { label: "Top → stock", action: { type: "move_top", from: "deck", to: "stock" } },
        { label: "Mill…", action: { type: "move_top", from: "deck", to: "waiting" }, prompt: "How many cards to put into the waiting room?" },
        "-",
        { label: "Look at top…", action: { type: "peek" }, prompt: "Look at how many cards?" },
        { label: "Search deck", action: { type: "search" } },
        ...markerItems((slot, face_down) => ({ type: "move_top", from: "deck", to: `marker:${slot}`, face_down }),
          () => true, "Top card → marker"),
      ]];
    }
    if (zone === "stock") {
      return ["Stock", [
        { label: "Pay 1: top → waiting room", action: { type: "move_top", from: "stock", to: "waiting" } },
        { label: "Pay…", action: { type: "move_top", from: "stock", to: "waiting" }, prompt: "Pay how many stock?" },
      ]];
    }
    const items = [{ label: "View all", view }];
    if (zone === "waiting") items.push({ label: "Refresh: all → deck and shuffle", action: { type: "move_all", from: "waiting", to: "deck" } });
    if (["clock", "resolution", "climax", "memory"].includes(zone)) {
      items.push({ label: "All → waiting room", action: { type: "move_all", from: zone, to: "waiting" } });
    }
    if (zone === "resolution") items.push({ label: "All → stock", action: { type: "move_all", from: zone, to: "stock" } });
    return [LABELS[zone], items];
  }

  root.addEventListener("click", (event) => {
    const menuItem = event.target.closest("[data-menu-item]");
    if (menuItem) {
      if (menuItem.dataset.view) {
        modal = JSON.parse(menuItem.dataset.view);
        hideMenu();
        renderModal();
        return;
      }
      const action = JSON.parse(menuItem.dataset.menuItem);
      if (menuItem.dataset.prompt) {
        const answer = window.prompt(menuItem.dataset.prompt, menuItem.dataset.promptDefault);
        if (!answer) return hideMenu();
        action.count = Number(answer);
      }
      act(action);
      return;
    }
    const zoneMenu = event.target.closest("[data-zone-menu]");
    if (zoneMenu) {
      if (menuZone === zoneMenu.dataset.zoneMenu && !menuEl.hidden) hideMenu();
      else openZoneMenu(zoneMenu.dataset.zoneMenu, zoneMenu.closest(".zone"));
      return;
    }
    const confirmClimax = event.target.closest("[data-confirm-climax]");
    if (confirmClimax) {
      modal = { confirmClimax: confirmClimax.dataset.confirmClimax };
      renderModal();
      return;
    }
    const mulliganPick = event.target.closest("[data-mulligan-pick]");
    if (mulliganPick) {
      const uid = mulliganPick.dataset.mulliganPick;
      if (mulliganPicks.has(uid)) mulliganPicks.delete(uid); else mulliganPicks.add(uid);
      renderModal();
      return;
    }
    const abilityPick = event.target.closest("[data-ability-pick]");
    if (abilityPick) {
      const uid = abilityPick.dataset.abilityPick;
      const prompt = board.ability.prompt;
      if (abilityPicks.includes(uid)) abilityPicks = abilityPicks.filter((u) => u !== uid);
      else if (prompt.max === 1) abilityPicks = [uid];
      else if (abilityPicks.length < prompt.max) abilityPicks.push(uid);
      renderModal();
      return;
    }
    if (event.target.closest("[data-ability-submit]")) {
      const uids = abilityPicks;
      abilityPicks = [];
      act({ type: "ability_answer", uids });
      return;
    }
    const abilities = event.target.closest("[data-abilities]");
    if (abilities) {
      modal = { abilities: abilities.dataset.abilities };
      hideMenu();
      renderModal();
      return;
    }
    if (event.target.closest("[data-close-after]")) modal = null;
    const discardPick = event.target.closest("[data-discard-pick]");
    if (discardPick) {
      const uid = discardPick.dataset.discardPick;
      if (discardPicks.has(uid)) discardPicks.delete(uid);
      else if (discardPicks.size < board.discard.count) discardPicks.add(uid);
      renderModal();
      return;
    }
    if (event.target.closest("[data-discard-submit]")) {
      const uids = [...discardPicks];
      discardPicks.clear();
      act({ type: "discard", uids });
      return;
    }
    if (event.target.closest("[data-mulligan-submit]")) {
      const uids = [...mulliganPicks];
      mulliganPicks.clear();
      act({ type: "mulligan", uids });
      return;
    }
    const levelPick = event.target.closest("[data-level-up]");
    if (levelPick) {
      act({ type: "level_up", uid: levelPick.dataset.levelUp });
      return;
    }
    const search = event.target.closest("[data-search-view]");
    if (search) {
      modal = JSON.parse(search.dataset.searchView);
      hideMenu();
      renderModal();
      return;
    }
    const phaseButton = event.target.closest("[data-phase]");
    if (phaseButton) {
      act({ type: "phase", phase: phaseButton.dataset.phase });
      return;
    }
    if (event.target.closest("[data-rules]")) {
      act(board.rules_request && board.rules_request.mine ? { type: "rules_answer" } : { type: "rules_request" });
      return;
    }
    if (event.target.closest("[data-animations]")) {
      setAnimations(!animations);
      return;
    }
    const layoutButton = event.target.closest("[data-layout]");
    if (layoutButton) {
      setLayout(layoutButton.dataset.layout);
      return;
    }
    const button = event.target.closest("[data-act]");
    if (button) {
      act(JSON.parse(button.dataset.act));
      return;
    }
    const more = event.target.closest("[data-more]");
    if (more) {
      const card = more.closest(".hand-card").querySelector(".pcard[data-uid]");
      if (card) {
        const [title, items] = cardMenu(card);
        showMenu(event.clientX, event.clientY, title, items);
      }
      return;
    }
    if (event.target.closest("[data-close]") || event.target === modalEl) {
      modal = null;
      renderModal();
      return;
    }
    // The deck's and stage cards' menus are on their [...] buttons.
    if (event.target.closest('[data-pile="deck"][data-owner="me"]') || event.target.closest('.zone.slot[data-owner="me"]:not(:has(.marker-pile:hover))')) {
      hideMenu();
      return;
    }
    // A stacked pile opens the pile's menu (its cards are reachable through "View all");
    // cards in the hand, spread in clock/level, or in a viewer open their own menu.
    const pile = event.target.closest("[data-pile]");
    const card = event.target.closest(".pcard[data-uid]");
    if (card && card.dataset.owner === "me" && !(pile && pile.classList.contains("pile"))) {
      const [title, items] = cardMenu(card);
      showMenu(event.clientX, event.clientY, title, items);
      event.stopPropagation();
      return;
    }
    if (pile) {
      const menu = pileMenu(pile.dataset.pile, pile.dataset.owner);
      if (menu) {
        showMenu(event.clientX, event.clientY, menu[0], menu[1]);
        return;
      }
    }
    if (!event.target.closest("[data-menu]")) hideMenu();
  });

  document.addEventListener("keydown", (event) => {
    const abilityPick = event.target.closest && event.target.closest("[data-ability-pick]");
    if (abilityPick && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      abilityPick.click();
      return;
    }
    const levelPick = event.target.closest && event.target.closest("[data-level-up]");
    if (levelPick && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      act({ type: "level_up", uid: levelPick.dataset.levelUp });
      return;
    }
    if (event.key === "Escape") {
      hideZoom();
      hideMenu();
      modal = null;
      renderModal();
    }
  });

  // --- Drag and drop ---------------------------------------------------------------------------

  root.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".pcard[data-uid][draggable]");
    if (!card) return;
    event.dataTransfer.setData("text/plain", card.dataset.uid);
    event.dataTransfer.effectAllowed = "move";
    hideMenu();
  });
  root.addEventListener("dragover", (event) => {
    const zone = event.target.closest("[data-drop]");
    if (zone && zone.dataset.drop) {
      event.preventDefault();
      zone.classList.add("drop-over");
    }
  });
  root.addEventListener("dragleave", (event) => {
    const zone = event.target.closest("[data-drop]");
    if (zone) zone.classList.remove("drop-over");
  });
  root.addEventListener("drop", (event) => {
    const zone = event.target.closest("[data-drop]");
    if (!zone || !zone.dataset.drop) return;
    event.preventDefault();
    zone.classList.remove("drop-over");
    const uid = event.dataTransfer.getData("text/plain");
    if (uid) act({ type: "move", uid, to: zone.dataset.drop });
  });

  // --- Chat ------------------------------------------------------------------------------------

  controlsEl.addEventListener("submit", (event) => {
    if (!event.target.matches("[data-damage]")) return;
    event.preventDefault();
    const count = Number(event.target.elements.count.value);
    if (count >= 1) act({ type: "damage", count });
  });

  $("[data-chat]").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = event.target.elements.text;
    if (input.value.trim()) act({ type: "chat", text: input.value });
    input.value = "";
  });

  poll();
  setInterval(poll, POLL_MS);
})();
