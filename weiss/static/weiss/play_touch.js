/* Moved from play.js (docs/round-two-plan.md, item 8): the section "// --- Touch screens:". The code is unchanged;
   it reads the live duel through `app` (functions as app.name, values as app.name()). play.js makes one with
   WeissTouch.create(app) and uses the names it returns. */
(function () {
  "use strict";

  function create(app) {
    // --- Touch screens: a tapped card's buttons in a tray, and cards full screen ----------------------
    // On a desktop a card's quick buttons sit on it and show while the mouse is over it, and resting on a card
    // enlarges it. With no mouse, a tap picks the card (it's outlined) and the tray along the bottom of the
    // screen has the same buttons, big enough to press, with their names written out. The tray's View, or a
    // long press on any card (pop-ups included), shows the card full screen: its picture, or its text.

    const LONG_PRESS_MS = 450;
    const trayEl = document.createElement("div");
    trayEl.className = "play-tray";
    trayEl.dataset.tray = "";
    trayEl.hidden = true;
    trayEl.setAttribute("role", "region");
    trayEl.setAttribute("aria-label", "Picked card");
    app.root().appendChild(trayEl);

    const selectedEl = () => (app.selected() ? app.boardEl().querySelector(`.pcard[data-uid="${CSS.escape(app.selected())}"]`) : null);

    function select(uid) {
      app.setSelected(app.selected() === uid ? null : uid); // tapping the picked card again puts it down
      app.hideMenu();
      renderTray();
    }

    function clearSelection() {
      app.setSelected(null);
      renderTray();
    }

    // A board button copied into the tray: its symbol, then its name (only in its tooltip on the board).
    function trayButton(b, { symbolOnly = false } = {}) {
      const copy = b.cloneNode(true);
      copy.className = [...b.classList].filter((c) => ["ability-button", "ready", "counter-button"].includes(c)).join(" ");
      copy.removeAttribute("style");
      const label = b.getAttribute("aria-label");
      if (label && !symbolOnly && b.textContent.trim() !== label) {
        copy.innerHTML = `<span class="tray-symbol" aria-hidden="true">${b.innerHTML}</span><span>${app.esc()(label)}</span>`;
      }
      return copy;
    }

    const actOf = (b) => {
      try { return JSON.parse(b.dataset.act || "{}"); } catch (e) { return {}; }
    };

    // The picked card's name and numbers as they are now (abilities included), and where it is.
    function trayStats(el, info) {
      const live = (app.board().stats || {})[el.dataset.uid] || {};
      const has = (value) => value !== null && value !== undefined && value !== "";
      const parts = [info.type];
      if (has(info.level)) parts.push(`Level ${has(live.level) ? live.level : info.level}`);
      if (has(info.cost)) parts.push(`Cost ${info.cost}`);
      if (has(info.power)) parts.push(`Power ${has(live.power) ? live.power : info.power}`);
      if (has(info.soul)) parts.push(`Soul ${has(live.soul) ? live.soul : info.soul}`);
      const where = el.dataset.zone === "hand" ? "In hand" : app.LABELS()[el.dataset.zone];
      const pos = el.classList.contains("pos-rest") ? "rested" : el.classList.contains("pos-reverse") ? "reversed" : "";
      return [parts.filter(Boolean).join(" · "), [where, pos].filter(Boolean).join(", ")];
    }

    function renderTray() {
      if (!app.board()) return;
      app.boardEl().querySelectorAll(".pcard.selected").forEach((el) => el.classList.remove("selected"));
      const el = selectedEl();
      const holder = el && (el.closest(".hand-card") || el.closest(".zone.slot"));
      const show = Boolean(app.touch() && holder && !app.prizeScreen().outOfSight(el) && !app.board().game_over);
      if (!show) app.setSelected(null);
      trayEl.hidden = !show || !app.modalEl().hidden; // a pop-up comes first; the tray is back once it's closed
      app.root().classList.toggle("tray-open", !trayEl.hidden);
      // Where the card can go, lit up on the board: a picked hand card goes to one with a tap; a dragged one, dropped.
      if (app.dragUid()) app.showDropHints(app.dragUid());
      else if (show && !trayEl.hidden && el.dataset.zone === "hand") app.showDropHints(el.dataset.uid);
      else app.clearDropHints();
      if (!show) return;
      el.classList.add("selected");

      const pk = el.dataset.card;
      const info = pk ? app.cards()[pk] : null;
      const zone = el.dataset.zone;
      const mine = el.dataset.owner === "me" && !app.SPECTATING();
      const zoomAttrs = `data-zoom-card="${app.esc()(pk)}" data-zoom-uid="${app.esc()(el.dataset.uid)}" data-zoom-zone="${app.esc()(zone)}"`;
      const [stats, where] = info ? trayStats(el, info) : ["", app.LABELS()[zone] || ""];
      const notes = [...holder.querySelectorAll(".hand-needs")].map((n) => `<p class="play-tray-note">${app.esc()(n.textContent)}</p>`).join("")
        + (zone === "hand" && app.boardEl().querySelector(".drop-hint") ? '<p class="play-tray-hint">Or tap a lit-up place on the board.</p>' : "");
      trayEl.innerHTML = `<div class="play-tray-head">
          ${info ? `<button type="button" class="play-tray-thumb" ${zoomAttrs} aria-label="Show ${app.esc()(info.name)} full screen"><img src="${app.esc()(info.image)}" alt=""></button>`
            : '<span class="play-tray-thumb"><span class="pcard-back"></span></span>'}
          <div class="play-tray-info"><p class="play-tray-name">${info ? app.esc()(info.name) : "Face-down card"}</p>
            <p class="play-tray-stats">${app.esc()(stats)}${stats && where ? " · " : ""}${app.esc()(where)}</p>${notes}</div>
          <button type="button" class="play-tray-close" data-tray-close aria-label="Put the card down">×</button>
        </div>`;

      const actions = document.createElement("div");
      actions.className = "play-tray-actions";
      if (info) actions.insertAdjacentHTML("beforeend", `<button type="button" ${zoomAttrs}>🔍 View</button>`);
      if (mine && zone === "hand") {
        // Where it can be played on the stage, laid out like the stage (front row, then back row), then the rest.
        const buttons = [...holder.querySelectorAll(".hand-actions button")];
        const toStage = (b) => actOf(b).type === "move" && app.STAGE().includes(actOf(b).to);
        const stage = buttons.filter(toStage);
        if (stage.length) {
          const row = (slots) => `<div class="tray-stage-row">${slots.map((s) => `<span data-tray-slot="${s}"></span>`).join("")}</div>`;
          actions.insertAdjacentHTML("beforeend", `<div class="tray-stage" role="group" aria-label="Play to the stage">
            <span class="tray-group-label">Play to</span>${row(["C1", "C2", "C3"])}${row(["B1", "B2"])}</div>`);
          for (const b of stage) actions.querySelector(`[data-tray-slot="${actOf(b).to}"]`).replaceWith(trayButton(b, { symbolOnly: true }));
          actions.querySelectorAll("[data-tray-slot]").forEach((gap) => gap.remove());
        }
        for (const b of buttons.filter((b) => !toStage(b))) actions.appendChild(trayButton(b));
      } else if (mine) {
        // Attacks first, then abilities, then the card's corner buttons, then moves to the slots beside it
        // (a move between two slots is drawn on the first of them, so it may be on a neighbour).
        const found = new Set([
          ...holder.querySelectorAll(".slot-actions button"),
          ...holder.querySelectorAll(".ability-button"),
          ...holder.querySelectorAll(".slot-pos button"),
          ...[...app.boardEl().querySelectorAll(".mat-me .slot-link")].filter((b) => actOf(b).uid === app.selected() || actOf(b).to === zone),
        ]);
        for (const b of found) actions.appendChild(trayButton(b));
      }
      trayEl.appendChild(actions);
    }

    const viewerEl = document.createElement("div");
    viewerEl.className = "play-viewer";
    viewerEl.hidden = true;
    viewerEl.setAttribute("role", "dialog");
    viewerEl.setAttribute("aria-modal", "true");
    document.body.appendChild(viewerEl);
    let viewerReturn = null; // where the focus goes back to once it's closed

    // A card full screen: its picture, or its text (with what's changing its power, soul or level, on the stage).
    function openViewer(pk, uid = null, zone = null) {
      const info = app.cards()[pk];
      if (!info) return;
      app.art().hideZoom();
      app.hideMenu();
      const sources = uid ? app.art().sourcesHtml(uid, pk, zone) : "";
      viewerReturn = document.activeElement;
      viewerEl.setAttribute("aria-label", info.name);
      viewerEl.innerHTML = `<div class="play-viewer-bar">
          <div class="layout-switch" role="group" aria-label="Show">
            <button type="button" data-viewer-tab="picture">Picture</button><button type="button" data-viewer-tab="text">${sources ? "Text and boosts" : "Text"}</button>
          </div>
          <button type="button" class="play-viewer-close" data-viewer-close aria-label="Close">×</button>
        </div>
        <div class="play-viewer-picture" data-viewer-panel="picture"><img src="${app.esc()(info.image)}" alt="${app.esc()(info.name)}"></div>
        <div class="play-viewer-text" data-viewer-panel="text">${app.cardTextHtml(info)}${sources ? `<div class="play-viewer-sources">${sources}</div>` : ""}</div>`;
      showViewerTab("picture");
      viewerEl.hidden = false;
      viewerEl.querySelector("[data-viewer-close]").focus({ preventScroll: true });
    }

    function showViewerTab(tab) {
      viewerEl.querySelectorAll("[data-viewer-tab]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.viewerTab === tab)));
      viewerEl.querySelectorAll("[data-viewer-panel]").forEach((panel) => { panel.hidden = panel.dataset.viewerPanel !== tab; });
    }

    function closeViewer() {
      if (viewerEl.hidden) return false;
      viewerEl.hidden = true;
      viewerEl.innerHTML = "";
      if (viewerReturn && viewerReturn.isConnected) viewerReturn.focus({ preventScroll: true });
      return true;
    }

    viewerEl.addEventListener("click", (event) => {
      const tab = event.target.closest("[data-viewer-tab]");
      if (tab) return showViewerTab(tab.dataset.viewerTab);
      if (event.target.closest("[data-viewer-close]")) return closeViewer();
      if (event.target.matches(".play-viewer-picture img")) return showViewerTab("text"); // the picture, tapped: its text
      if (event.target === viewerEl || event.target.matches(".play-viewer-picture")) closeViewer(); // the dark space around it
    });

    // A long press on a card (not a mouse's) shows it full screen. The tap that ends it does nothing else.
    let pressTimer = null;
    let pressAt = null;
    let swallowClick = false;
    const cancelPress = () => {
      clearTimeout(pressTimer);
      pressTimer = null;
    };
    app.root().addEventListener("pointerdown", (event) => {
      swallowClick = false;
      cancelPress();
      const el = event.pointerType !== "mouse" && event.target.closest(".pcard[data-card]");
      if (!el) return;
      pressAt = { x: event.clientX, y: event.clientY };
      pressTimer = setTimeout(() => {
        pressTimer = null;
        swallowClick = true;
        openViewer(el.dataset.card, el.dataset.uid, el.dataset.zone);
      }, LONG_PRESS_MS);
    });
    app.root().addEventListener("pointermove", (event) => {
      if (pressTimer && pressAt && Math.hypot(event.clientX - pressAt.x, event.clientY - pressAt.y) > 10) cancelPress(); // scrolling
    });
    app.root().addEventListener("pointerup", cancelPress);
    app.root().addEventListener("pointercancel", cancelPress);
    document.addEventListener("click", (event) => {
      if (!swallowClick) return;
      swallowClick = false;
      event.preventDefault();
      event.stopPropagation();
    }, true);
    // Not the browser's own long-press menu (save image...) over a card, but the card full screen: some browsers
    // (Chrome on Android) end the press themselves to bring up their menu, before the timer above goes off.
    app.root().addEventListener("contextmenu", (event) => {
      const el = app.touch() && event.target.closest(".pcard");
      if (!el) return;
      event.preventDefault();
      if (el.dataset.card && viewerEl.hidden) {
        cancelPress();
        swallowClick = true;
        openViewer(el.dataset.card, el.dataset.uid, el.dataset.zone);
      }
    });

    return { clearSelection, closeViewer, openViewer, renderTray, select, selectedEl };
  }

  window.WeissTouch = { create };
})();
