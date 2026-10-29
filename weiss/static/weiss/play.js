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
  const POLL_MS = 1500;

  const $ = (sel) => root.querySelector(sel);
  const boardEl = $("[data-board]");
  const previewEl = $("[data-preview]");
  const controlsEl = $("[data-controls]");
  const logEl = $("[data-log]");
  const menuEl = $("[data-menu]");
  const modalEl = $("[data-modal]");

  const LABELS = {
    deck: "Deck", hand: "Hand", clock: "Clock", level: "Level", stock: "Stock", waiting: "Waiting room",
    memory: "Memory", climax: "Climax", resolution: "Resolution",
    C1: "Center left", C2: "Center middle", C3: "Center right", B1: "Back left", B2: "Back right",
  };
  const STAGE = ["C1", "C2", "C3", "B1", "B2"];
  // Each stage slot has a pile of markers under it, named "marker:<slot>" like the server does.
  for (const slot of STAGE) LABELS[`marker:${slot}`] = `Markers under ${LABELS[slot].toLowerCase()}`;
  const isMarkerPile = (zone) => zone.startsWith("marker:");
  const DAMAGE_RESOLVE_MS = 500; // how long a climax-cancelled damage stays on the board
  const MOVE_TARGETS = ["hand", "C1", "C2", "C3", "B1", "B2", "climax", "clock", "level", "stock",
    "memory", "waiting", "resolution"];
  const PUBLIC_PILES = ["waiting", "memory", "level", "clock", "climax", "resolution"];

  let version = "";
  let board = null;
  const cards = {}; // card pk -> details; entries are never replaced so image URLs stay stable
  let modal = null; // {title, owner: "me"|"opponent", zone} or {title, revealed: [...]}
  let error = "";
  let busy = false;
  let resolveTimer = null; // pending "resolve_damage" after a climax cancels our damage

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
    board = data.board;
    if (data.revealed) modal = { title: data.revealed.title, revealed: data.revealed.cards };
    render();
    // A climax cancelled our damage: leave it on the board for a moment, then let the server clean up.
    if (board.damage_pending && !resolveTimer) {
      resolveTimer = setTimeout(() => {
        resolveTimer = null;
        act({ type: "resolve_damage" });
      }, DAMAGE_RESOLVE_MS);
    }
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
      if (data.board) receive(data); else render();
    } catch (e) {
      error = "Couldn't reach the server. Try again.";
      render();
    } finally {
      busy = false;
    }
  }

  // --- Drawing ---------------------------------------------------------------------------------

  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

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
    const stats = info && !card.face_down ? statsHtml(info) : "";
    return `<div class="${classes.join(" ")}" ${attrs} tabindex="0">${face}${stats}${badge}</div>`;
  }

  // Level and cost in the top-left corner and power in the bottom-left, where the printed card has
  // them, but large enough to read at board size. Left-side so they show on overlapped piles too.
  function statsHtml(info) {
    const has = (value) => value !== null && value !== undefined && value !== "";
    const corner = [
      has(info.level) ? `<span class="stat stat-level" title="Level">${esc(info.level)}</span>` : "",
      has(info.cost) ? `<span class="stat stat-cost" title="Cost">${esc(info.cost)}</span>` : "",
    ].join("");
    const power = has(info.power) ? `<span class="stat stat-power" title="Power">${esc(info.power)}</span>` : "";
    if (!corner && !power) return "";
    return `<span class="pcard-stats">${corner ? `<span class="stat-corner">${corner}</span>` : ""}${power}</span>`;
  }

  function backHtml() {
    return '<div class="pcard"><span class="pcard-back"></span></div>';
  }

  function pileHtml(side, owner, zone) {
    const pile = side.zones[zone];
    const hidden = !Array.isArray(pile);
    const count = hidden ? pile.count : pile.length;
    const top = hidden ? (count ? backHtml() : "") : cardHtml(pile[pile.length - 1], owner, zone);
    return `<div class="zone pile zone-${zone}" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${LABELS[zone]} <b>${count}</b></span>
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

  // Quick actions shown while hovering one of our characters: waiting room, attack (standing
  // center-stage characters only) and "More" for the full menu.
  function slotActionsHtml(card, slot) {
    const act = (action) => esc(JSON.stringify(action));
    const attack = slot.startsWith("C") && card.pos === "stand"
      ? `<button type="button" data-act='${act({ type: "attack", uid: card.uid })}'>⚔ Attack</button>` : "";
    return `<div class="slot-actions">
      ${attack}
      <button type="button" data-act='${act({ type: "move", uid: card.uid, to: "waiting" })}'>→ Waiting room</button>
      <button type="button" data-more>More…</button>
    </div>`;
  }

  function slotHtml(side, owner, slot) {
    const card = side.stage[slot];
    return `<div class="zone slot" data-drop="${owner === "me" ? slot : ""}" data-owner="${owner}">
      <span class="zone-label">${LABELS[slot]}</span>
      ${cardHtml(card, owner, slot) || '<span class="zone-empty"></span>'}
      ${card && owner === "me" ? slotActionsHtml(card, slot) : ""}
      ${markerHtml(side, owner, slot)}
    </div>`;
  }

  // The level zone: a narrow column, its (at most 4) cards stacked closely top to bottom so each
  // one's level and cost corner still shows.
  function levelHtml(side, owner) {
    const pile = side.zones.level;
    return `<div class="zone spread zone-level" data-pile="level" data-owner="${owner}" data-drop="${owner === "me" ? "level" : ""}">
      <span class="zone-label">${LABELS.level} <b>${pile.length}</b></span>
      <div class="level-stack">${pile.map((c) => cardHtml(c, owner, "level")).join("") || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  function spreadHtml(side, owner, zone) {
    const pile = side.zones[zone];
    return `<div class="zone spread zone-${zone}" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${LABELS[zone]} <b>${pile.length}</b></span>
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
      <div class="mat-row">${spreadHtml(side, owner, "level")}${spreadHtml(side, owner, "clock")}
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
      <div class="table-divider">${board.my_turn ? "Your turn" : `${esc(opp ? opp.name : "Opponent")}'s turn`} · turn ${board.turn_number}</div>
      <div class="table-side side-me">
        ${matHtml(me, "me")}
        <div class="hand hand-me zone" data-drop="hand" data-owner="me"><span class="zone-label">Your hand <b>${me.zones.hand.length}</b></span>
          <div class="hand-cards">${me.zones.hand.map((c) => cardHtml(c, "me", "hand")).join("")}</div></div>
      </div>`;

    renderControls();

    const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 20;
    logEl.innerHTML = board.log.map((entry) => entry.chat
      ? `<p class="log-chat"><b>${esc(entry.who)}:</b> ${esc(entry.text)}</p>`
      : `<p>${entry.who ? `<b>${esc(entry.who)}</b> ` : ""}${esc(entry.text)}</p>`).join("");
    if (atBottom) logEl.scrollTop = logEl.scrollHeight;

    renderModal();
  }

  // The controls are built once and then only updated, so the damage amount being typed survives
  // the board redrawing on every opponent move.
  function renderControls() {
    if (!controlsEl.dataset.built) {
      controlsEl.dataset.built = "1";
      controlsEl.innerHTML = `
        <p class="panel-error" role="alert" data-error hidden></p>
        <p class="play-turn" data-turn></p>
        <div class="play-buttons">
          <button type="button" data-act='{"type":"move_top","from":"deck","to":"hand"}'>Draw</button>
          <button type="button" data-act='{"type":"stand_all"}'>Stand all</button>
          <button type="button" data-act='{"type":"move_top","from":"deck","to":"resolution"}'>Trigger</button>
          <button type="button" data-act='{"type":"end_turn"}' data-end-turn>End turn</button>
        </div>
        <form class="damage-form" data-damage>
          <label>Damage <input type="number" name="count" min="1" max="20" value="1" required></label>
          <button type="submit">Take damage</button>
        </form>
        <p class="muted small damage-note">Cards go to your clock one at a time; a climax cancels it all.</p>
        <div class="layout-switch" role="group" aria-label="Board view">
          ${Object.entries(LAYOUTS).map(([name, label]) => `<button type="button" data-layout="${name}">${label}</button>`).join("")}
        </div>`;
    }
    controlsEl.querySelectorAll("[data-layout]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.layout === layout));
    });
    const errorEl = controlsEl.querySelector("[data-error]");
    errorEl.textContent = error;
    errorEl.hidden = !error;
    const turn = controlsEl.querySelector("[data-turn]");
    turn.textContent = `${board.my_turn ? "Your turn" : "Opponent's turn"} · turn ${board.turn_number}`;
    turn.classList.toggle("mine", board.my_turn);
    controlsEl.querySelector("[data-end-turn]").disabled = !board.my_turn;
  }

  function renderModal() {
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
      list = pileCards(side, modal.zone).slice().reverse().map((c) => cardHtml(c, owner, modal.zone));
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="${esc(modal.title)}">
      <div class="play-modal-head"><h2>${esc(modal.title)}</h2><button type="button" data-close>Close</button></div>
      <p class="muted small">${owner === "me" ? "Click a card to move it. Top of the pile first." : "Top of the pile first."}</p>
      <div class="play-modal-cards">${list.join("") || '<p class="empty">Empty.</p>'}</div>
    </div>`;
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

  function showMenu(x, y, title, items) {
    menuEl.innerHTML = `<p class="play-menu-title">${esc(title)}</p>` + items.map((item) => item === "-"
      ? "<hr>"
      : `<button type="button" data-menu-item='${esc(JSON.stringify(item.action || {}))}' ${item.prompt ? `data-prompt="${esc(item.prompt)}"` : ""} ${item.view ? `data-view='${esc(JSON.stringify(item.view))}'` : ""}>${esc(item.label)}</button>`).join("");
    menuEl.hidden = false;
    const box = menuEl.getBoundingClientRect();
    menuEl.style.left = `${Math.min(x, window.innerWidth - box.width - 8)}px`;
    menuEl.style.top = `${Math.min(y, window.innerHeight - box.height - 8)}px`;
  }

  function hideMenu() {
    menuEl.hidden = true;
  }

  function cardMenu(el) {
    const uid = el.dataset.uid;
    const zone = el.dataset.zone;
    const info = el.dataset.card ? cards[el.dataset.card] : null;
    const items = [];
    if (["C1", "C2", "C3"].includes(zone) && el.classList.contains("pos-stand")) {
      items.push({ label: "⚔ Attack (rest + trigger check)", action: { type: "attack", uid } }, "-");
    }
    if (["C1", "C2", "C3", "B1", "B2"].includes(zone)) {
      items.push({ label: "Stand", action: { type: "position", uid, pos: "stand" } },
        { label: "Rest", action: { type: "position", uid, pos: "rest" } },
        { label: "Reverse", action: { type: "position", uid, pos: "reverse" } }, "-");
    }
    if (!["hand", "deck", "stock"].includes(zone)) {
      items.push({ label: el.classList.contains("face-down") ? "Turn face up" : "Turn face down", action: { type: "flip", uid } }, "-");
    }
    for (const to of MOVE_TARGETS) {
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
        { label: "Draw 1", action: { type: "move_top", from: "deck", to: "hand" } },
        { label: "Draw…", action: { type: "move_top", from: "deck", to: "hand" }, prompt: "How many cards to draw?" },
        "-",
        { label: "Take damage…", action: { type: "damage" }, prompt: "How much damage?" },
        { label: "Trigger: top → resolution", action: { type: "move_top", from: "deck", to: "resolution" } },
        { label: "Top → stock", action: { type: "move_top", from: "deck", to: "stock" } },
        { label: "Top → waiting room", action: { type: "move_top", from: "deck", to: "waiting" } },
        { label: "Mill…", action: { type: "move_top", from: "deck", to: "waiting" }, prompt: "How many cards to put into the waiting room?" },
        "-",
        { label: "Look at top…", action: { type: "peek" }, prompt: "Look at how many cards?" },
        { label: "Search deck", action: { type: "search" } },
        { label: "Shuffle", action: { type: "shuffle" } },
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
        const answer = window.prompt(menuItem.dataset.prompt, "1");
        if (!answer) return hideMenu();
        action.count = Number(answer);
      }
      act(action);
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
      const card = more.closest(".zone.slot").querySelector(".pcard[data-uid]");
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
    // A stacked pile opens the pile's menu (its cards are reachable through "View all");
    // cards on the stage, in the hand, spread in clock/level, or in a viewer open their own menu.
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
