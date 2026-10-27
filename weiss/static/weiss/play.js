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
  const MOVE_TARGETS = ["hand", "C1", "C2", "C3", "B1", "B2", "climax", "clock", "level", "stock",
    "memory", "waiting", "resolution"];
  const PUBLIC_PILES = ["waiting", "memory", "level", "clock", "climax", "resolution"];

  let version = "";
  let board = null;
  const cards = {}; // card pk -> details; entries are never replaced so image URLs stay stable
  let modal = null; // {title, owner: "me"|"opponent", zone} or {title, revealed: [...]}
  let error = "";
  let busy = false;

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
    return `<div class="${classes.join(" ")}" ${attrs} tabindex="0">${face}${badge}</div>`;
  }

  function backHtml() {
    return '<div class="pcard"><span class="pcard-back"></span></div>';
  }

  function pileHtml(side, owner, zone) {
    const pile = side.zones[zone];
    const hidden = !Array.isArray(pile);
    const count = hidden ? pile.count : pile.length;
    const top = hidden ? (count ? backHtml() : "") : cardHtml(pile[pile.length - 1], owner, zone);
    return `<div class="zone pile" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${LABELS[zone]} <b>${count}</b></span>
      <div class="pile-top">${top || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  function slotHtml(side, owner, slot) {
    return `<div class="zone slot" data-drop="${owner === "me" ? slot : ""}" data-owner="${owner}">
      <span class="zone-label">${LABELS[slot]}</span>
      ${cardHtml(side.stage[slot], owner, slot) || '<span class="zone-empty"></span>'}
    </div>`;
  }

  function spreadHtml(side, owner, zone) {
    const pile = side.zones[zone];
    return `<div class="zone spread" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${LABELS[zone]} <b>${pile.length}</b></span>
      <div class="spread-cards">${pile.map((c) => cardHtml(c, owner, zone)).join("") || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  function matHtml(side, owner) {
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

    controlsEl.innerHTML = `
      ${error ? `<p class="panel-error" role="alert">${esc(error)}</p>` : ""}
      <p class="play-turn ${board.my_turn ? "mine" : ""}">${board.my_turn ? "Your turn" : "Opponent's turn"} · turn ${board.turn_number}</p>
      <div class="play-buttons">
        <button type="button" data-act='{"type":"move_top","from":"deck","to":"hand"}'>Draw</button>
        <button type="button" data-act='{"type":"stand_all"}'>Stand all</button>
        <button type="button" data-act='{"type":"move_top","from":"deck","to":"clock"}'>Damage</button>
        <button type="button" data-act='{"type":"move_top","from":"deck","to":"resolution"}'>Trigger</button>
        <button type="button" data-act='{"type":"end_turn"}' ${board.my_turn ? "" : "disabled"}>End turn</button>
      </div>`;

    const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 20;
    logEl.innerHTML = board.log.map((entry) => entry.chat
      ? `<p class="log-chat"><b>${esc(entry.who)}:</b> ${esc(entry.text)}</p>`
      : `<p>${entry.who ? `<b>${esc(entry.who)}</b> ` : ""}${esc(entry.text)}</p>`).join("");
    if (atBottom) logEl.scrollTop = logEl.scrollHeight;

    renderModal();
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
      list = (side.zones[modal.zone] || []).slice().reverse().map((c) => cardHtml(c, owner, modal.zone));
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

  const ZOOM_DELAY_MS = 1000;
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
    return [info ? info.name : "Card", items];
  }

  function pileMenu(zone, owner) {
    const view = { owner, zone, title: `${owner === "me" ? "Your" : `${board.opponent.name}'s`} ${LABELS[zone].toLowerCase()}` };
    if (owner !== "me") return PUBLIC_PILES.includes(zone) ? [LABELS[zone], [{ label: "View all", view }]] : null;
    if (zone === "deck") {
      return ["Deck", [
        { label: "Draw 1", action: { type: "move_top", from: "deck", to: "hand" } },
        { label: "Draw…", action: { type: "move_top", from: "deck", to: "hand" }, prompt: "How many cards to draw?" },
        "-",
        { label: "Damage: top → clock", action: { type: "move_top", from: "deck", to: "clock" } },
        { label: "Trigger: top → resolution", action: { type: "move_top", from: "deck", to: "resolution" } },
        { label: "Top → stock", action: { type: "move_top", from: "deck", to: "stock" } },
        { label: "Top → waiting room", action: { type: "move_top", from: "deck", to: "waiting" } },
        { label: "Mill…", action: { type: "move_top", from: "deck", to: "waiting" }, prompt: "How many cards to put into the waiting room?" },
        "-",
        { label: "Look at top…", action: { type: "peek" }, prompt: "Look at how many cards?" },
        { label: "Search deck", action: { type: "search" } },
        { label: "Shuffle", action: { type: "shuffle" } },
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
    const button = event.target.closest("[data-act]");
    if (button) {
      act(JSON.parse(button.dataset.act));
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

  $("[data-chat]").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = event.target.elements.text;
    if (input.value.trim()) act({ type: "chat", text: input.value });
    input.value = "";
  });

  poll();
  setInterval(poll, POLL_MS);
})();
