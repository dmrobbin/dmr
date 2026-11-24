/* Moved from play.js (docs/round-two-plan.md, item 8): the section "// --- Enlarged card art after resting". The code is unchanged;
   it reads the live duel through `app` (functions as app.name, values as app.name()). play.js makes one with
   WeissArt.create(app) and uses the names it returns. */
(function () {
  "use strict";

  function create(app) {
    // --- Enlarged card art after resting the mouse on a card -------------------------------------

    const ZOOM_DELAY_MS = 0;
    const zoomEl = document.createElement("div");
    zoomEl.className = "play-zoom";
    zoomEl.hidden = true;
    document.body.appendChild(zoomEl);
    // Beside the zoom of a character whose power, soul or level has changed: the cards (or augments, curses...) changing it.
    const sourcesEl = document.createElement("div");
    sourcesEl.className = "play-zoom-sources";
    sourcesEl.hidden = true;
    document.body.appendChild(sourcesEl);
    let zoomTimer = null;
    let zoomCard = null; // the .pcard element being hovered

    function hideZoom() {
      clearTimeout(zoomTimer);
      zoomTimer = null;
      zoomCard = null;
      zoomEl.hidden = true;
      sourcesEl.hidden = true;
    }

    // Where a card giving a boost is now, as "Your back left" or "Bob's climax area", or "" if it's not on the board.
    function whereIs(uid) {
      const sides = [["me", app.SPECTATING() ? `${app.board().me.name}'s` : "Your"], ["opponent", app.board().opponent ? `${app.board().opponent.name}'s` : "Opponent's"]];
      for (const [key, owner] of sides) {
        const side = app.board()[key];
        if (!side) continue;
        const slot = app.STAGE().find((s) => side.stage[s] && side.stage[s].uid === uid);
        if (slot) return `${owner} ${app.LABELS()[slot].toLowerCase()}`;
        for (const [zone, name] of [["climax", "climax area"], ["memory", "memory"], ["waiting", "waiting room"]]) {
          const pile = side.zones[zone];
          if (Array.isArray(pile) && pile.some((c) => c.uid === uid)) return `${owner} ${name}`;
        }
      }
      return "";
    }

    function showSources(el) {
      const html = sourcesHtml(el.dataset.uid, el.dataset.card, el.dataset.zone);
      if (!html) {
        sourcesEl.hidden = true;
        return;
      }
      sourcesEl.innerHTML = html;
      sourcesEl.hidden = false;
      const zoomBox = zoomEl.getBoundingClientRect();
      const width = sourcesEl.getBoundingClientRect().width;
      // To the right of the zoomed card, or to its left if the window's too narrow.
      const right = zoomBox.right + 16;
      sourcesEl.style.left = `${right + width <= window.innerWidth - 8 ? right : Math.max(8, zoomBox.left - 16 - width)}px`;
    }

    // What's changing a character's power, soul or level, and by how much ("" if nothing is).
    function sourcesHtml(uid, pk, zone) {
      const entries = app.STAGE().includes(zone) && (app.board().stat_sources || {})[uid];
      const info = app.cards()[pk];
      if (!entries || !entries.length || !info) return "";
      const live = (app.board().stats || {})[uid] || {};
      const signed = (n) => `${n > 0 ? "+" : ""}${n}`;
      const totals = [["power", "Power"], ["soul", "Soul"], ["level", "Level"]]
        .filter(([stat]) => live[stat] !== undefined && info[stat] !== null && info[stat] !== undefined && info[stat] !== "" && Number(live[stat]) !== Number(info[stat]))
        .map(([stat, label]) => `<span class="${Number(live[stat]) > Number(info[stat]) ? "boosted" : "lowered"}">${label} ${app.esc()(info[stat])} → ${app.esc()(live[stat])}</span>`);
      const rows = entries.map((entry) => {
        const changes = [["power", "power"], ["soul", "soul"], ["level", "level"]]
          .filter(([stat]) => entry[stat])
          .map(([stat, label]) => `<b class="${entry[stat] > 0 ? "boosted" : "lowered"}">${signed(entry[stat])} ${label}</b>`);
        if (entry.set_power !== undefined) changes.push(`<b>power set to ${app.esc()(entry.set_power)}</b>`);
        if (entry.set_soul !== undefined) changes.push(`<b>soul set to ${app.esc()(entry.set_soul)}</b>`);
        const source = entry.card ? app.cards()[entry.card] : null;
        const name = source ? source.name : entry.label || "An effect";
        const where = entry.uid === uid ? "Its own ability" : entry.uid ? whereIs(entry.uid) : "";
        const face = source
          ? `<img src="${app.esc()(source.image)}" alt="" class="${(source.type || "").toLowerCase() === "climax" ? "source-climax" : ""}">`
          : '<span class="source-chip" aria-hidden="true">✦</span>';
        return `<li>${face}<span class="source-text">${changes.join("")}<span class="source-name">${app.esc()(name)}</span>${where ? `<span class="muted small">${app.esc()(where)}</span>` : ""}</span></li>`;
      });
      return `${totals.length ? `<p class="source-totals">${totals.join("")}</p>` : ""}<ul>${rows.join("")}</ul>`;
    }

    let pointer = null; // where the mouse last was, to find the hovered card again after a redraw

    // After a redraw (as animations cause), the zoom stays up on the card still under the pointer.
    function keepZoom() {
      const under = pointer && document.elementFromPoint(pointer.x, pointer.y);
      const el = under && under.closest && under.closest(".pcard[data-card]");
      if (!el) return hideZoom();
      const showing = !zoomEl.hidden;
      zoomCard = el;
      if (showing) showZoom(el);
    }

    function showZoom(el) {
      const info = app.cards()[el.dataset.card];
      if (!info) return;
      zoomEl.innerHTML = `<img src="${app.esc()(info.image)}" alt="${app.esc()(info.name)}">${info.grade >= 3 ? '<span class="rfx-sheen" aria-hidden="true"></span>' : ""}`;
      zoomEl.classList.toggle("zoom-climax", (info.type || "").toLowerCase() === "climax");
      if (info.grade) zoomEl.dataset.grade = info.grade; else delete zoomEl.dataset.grade;
      zoomEl.hidden = false;
      showSources(el);
    }

    app.root().addEventListener("mousemove", (event) => {
      if (app.touch()) return; // a tap sends a mousemove too: a touch screen has the tray and the full-screen view instead
      pointer = { x: event.clientX, y: event.clientY };
      const el = event.target.closest(".pcard[data-card]");
      if (el === zoomCard) return;
      hideZoom();
      if (!el) return;
      zoomCard = el;
      zoomTimer = setTimeout(() => {
        if (zoomCard === el && el.isConnected) showZoom(el);
      }, ZOOM_DELAY_MS);
    });
    app.root().addEventListener("mouseleave", hideZoom);
    app.root().addEventListener("mousedown", hideZoom);
    app.root().addEventListener("dragstart", hideZoom);
    window.addEventListener("scroll", hideZoom, { passive: true });

    return { hideZoom, keepZoom, sourcesHtml, hasZoom: () => Boolean(zoomCard) };
  }

  window.WeissArt = { create };
})();
