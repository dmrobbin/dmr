/* Moved from play.js (docs/round-two-plan.md, item 8): the section "// --- Card movement: our own moves". The code is unchanged;
   it reads the live duel through `app` (functions as app.name, values as app.name()). play.js makes one with
   WeissMovement.create(app) and uses the names it returns. */
(function () {
  "use strict";

  function create(app) {
    // --- Card movement: our own moves fly a card from where it is to where it's going, and then the
    // action is sent, so the real card appears as the flight lands ---------------------------------

    const FLIGHT_MS = 420; // each card's flight
    const FLIGHT_STAGGER_MS = 140; // between cards when several move
    const MAX_FLIGHTS = 10;
    const BACK = '<span class="pcard-back"></span>';

    // The element showing one of our zones: a stage slot (markers fly to their character), a pile,
    // or the hand.
    function zoneEl(zone) {
      if (zone === "hand") return app.boardEl().querySelector(".hand-me .hand-cards");
      const slot = app.isMarkerPile()(zone) ? zone.slice("marker:".length) : zone;
      if (app.STAGE().includes(slot)) return app.boardEl().querySelector(`.mat-me [data-slot="${slot}"]`);
      return app.boardEl().querySelector(`.mat-me [data-pile="${zone}"]`);
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
      return img ? `<img src="${app.esc()(img.src)}" alt="">` : BACK;
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
      const at = app.PHASE_NAMES().indexOf(app.board().phase);
      const target = action.type === "end_turn" ? app.PHASE_NAMES().length - 1 : app.PHASE_NAMES().indexOf(action.phase);
      const passes = (phase) => at < app.PHASE_NAMES().indexOf(phase) && app.PHASE_NAMES().indexOf(phase) <= target;
      switch (action.type) {
        case "move": {
          const el = app.root().querySelector(`.pcard[data-uid="${action.uid}"]`);
          if (!el) break;
          fly(layoutBox(el), action.to, faceOf(el), 1, FLIGHT_MS, el);
          // Moving onto an occupied slot from another slot swaps them: the other card flies back.
          const other = app.STAGE().includes(el.dataset.zone) && app.STAGE().includes(action.to) && topCardEl(action.to);
          if (other) fly(layoutBox(other), el.dataset.zone, faceOf(other), 1, FLIGHT_MS, other);
          const info = el.dataset.card ? app.cards()[el.dataset.card] : null;
          if (el.dataset.zone === "hand" && app.PLAY_ZONES().includes(action.to) && info && info.cost && !action.free_with) {
            fromZone("stock", "waiting", info.cost); // paying the cost
          }
          break;
        }
        case "move_top": fromZone(action.from, action.to, action.count || 1); break;
        case "move_all": fromZone(action.from, action.to, Math.min(app.pileCards(app.board().me, action.from).length, 6), faceOf(topCardEl(action.from))); break;
        case "attack": fromZone("deck", app.board().rules ? "stock" : "resolution"); break;
        case "discard":
          for (const uid of action.uids) {
            const el = app.root().querySelector(`.hand-me .pcard[data-uid="${uid}"]`);
            if (el) fly(layoutBox(el), "waiting", faceOf(el), 1, FLIGHT_MS, el);
          }
          break;
        case "mulligan":
          for (const uid of action.uids) {
            const el = app.root().querySelector(`.hand-me .pcard[data-uid="${uid}"]`);
            if (el) fly(layoutBox(el), "waiting", faceOf(el), 1, FLIGHT_MS, el);
          }
          fromZone("deck", "hand", action.uids.length);
          break;
        case "trigger_choice": {
          // A bounce has no `to`: its card goes to the opponent's hand, which isn't one of our zones.
          const el = action.uid && action.to && app.root().querySelector(`.pcard[data-uid="${action.uid}"]`);
          if (el) fly(layoutBox(el), action.to, faceOf(el));
          if (action.accept) fromZone("deck", "stock");
          break;
        }
        case "counter": {
          const el = app.root().querySelector(`.pcard[data-uid="${action.uid}"]`);
          if (el) fly(layoutBox(el), "waiting", faceOf(el));
          break;
        }
        case "damage":
          fromZone("deck", "clock", action.count || 1);
          app.fx().noteOwnDamage(); // these cards have flown in: the table's show doesn't turn them over again
          break;
        case "encore": fromZone("stock", "waiting", app.ENCORE_COST()); break;
        case "clock_draw": {
          const el = app.root().querySelector(`.pcard[data-uid="${action.uid}"]`);
          if (el) fly(layoutBox(el), "clock", faceOf(el));
          fromZone("deck", "hand", app.CLOCK_DRAW());
          break;
        }
        case "phase":
        case "end_turn":
          if (app.board().rules && passes("draw")) fromZone("deck", "hand", 1, BACK, FLIGHT_MS * 1.2); // the draw phase's draw, a little slower
          if (passes("end") && app.board().me.zones.climax.length) fromZone("climax", "waiting", app.board().me.zones.climax.length, faceOf(topCardEl("climax")));
          break;
        default: break;
      }
      return flights;
    }

    // The action waits for its flights, but never for long: a browser can hold animations back (a tab out of
    // sight, a phone put down), and the action, and the game with it, mustn't wait on that.
    async function animateAction(action) {
      if (!app.animations() || !app.board()) return;
      const flights = flightsFor(action);
      await Promise.race([flyAll(flights), wait(FLIGHT_MS * 2 + flights.length * FLIGHT_STAGGER_MS)]);
    }

    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    // A request that gives up: one a phone has left hanging (put away mid-request, or between networks)
    // would otherwise hold up every one after it until the page is reloaded.
    async function fetchWithin(ms, url, options = {}) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), ms);
      try {
        return await fetch(url, { ...options, signal: controller.signal });
      } finally {
        clearTimeout(timer);
      }
    }

    // Fly card-shaped boxes {from, to, face, ms}: `hide` is hidden for the flight (it's the card
    // leaving; the board is redrawn afterwards anyway), `show` is hidden until its flight lands.
    function flyAll(flights) {
      // A compact screen shows one side of the table at a time: nothing flies to or from the side out of sight.
      flights = flights.filter(({ from, to }) => from && to && from.width && to.width);
      return Promise.all(flights.map(({ from, to, face, ms = FLIGHT_MS, hide, show, opponent }, i) => {
        const el = document.createElement("div");
        el.className = opponent ? "card-flight card-flight-opponent" : "card-flight";
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
      if (!app.board() || !app.board().opponent || !app.animations()) return null;
      const mat = app.boardEl().querySelector(".mat-opponent");
      if (!mat) return null;
      const slots = {};
      const boxes = {};
      for (const slot of app.STAGE()) {
        const card = app.board().opponent.stage[slot];
        if (card) slots[card.uid] = slot;
        const el = mat.querySelector(`[data-slot="${slot}"] .pcard, [data-slot="${slot}"] .zone-empty`);
        if (el) boxes[slot] = layoutBox(el);
      }
      const handCards = app.boardEl().querySelectorAll(".hand-opponent .pcard");
      const hand = handCards.length ? layoutBox(handCards[handCards.length - 1]) : null;
      return { slots, boxes, hand, handCount: app.board().opponent.zones.hand.count };
    }

    function animateOpponent(before) {
      if (!before || !app.board().opponent || !app.animations()) return;
      const mat = app.boardEl().querySelector(".mat-opponent");
      const flights = [];
      for (const slot of app.STAGE()) {
        const card = app.board().opponent.stage[slot];
        const el = card && mat && mat.querySelector(`[data-slot="${slot}"] .pcard`);
        if (!el || before.slots[card.uid] === slot) continue;
        const from = before.slots[card.uid] ? before.boxes[before.slots[card.uid]]
          : app.board().opponent.zones.hand.count < before.handCount ? before.hand : null;
        if (from) flights.push({ from, to: layoutBox(el), face: faceOf(el), show: el, opponent: true });
      }
      flyAll(flights);
    }

    // Asking for the board: one request at a time, from pollLoop. The server may hold a request until something changes
    // (its long-poll, weiss.play.room_state): a "nothing new" that took a while says it does, and then the next request
    // goes straight out, so a move shows as soon as it's made. Otherwise this is plain polling, every POLL_MS.
    const LONG_POLL_SIGN_MS = 1500;
    let polling = false;
    let longPoll = false;
    let pollWake = null; // ends pollLoop's pause early (the tab coming back into view)

    // "board", "nothing" or "failed" (what came back), or "skipped" (an action of ours is out, or a poll already is).
    async function poll() {
      if (app.busy() || polling) return "skipped";
      polling = true;
      let data = null;
      let problem = "";
      try {
        const started = performance.now();
        // A tab out of sight doesn't hold a server thread waiting: it only checks, and less often (pollLoop).
        const response = await fetchWithin(app.POLL_TIMEOUT_MS(), `${app.STATE_URL()}?v=${app.version()}&wait=${document.hidden ? 0 : 1}`, { credentials: "same-origin" });
        if (response.status === 200) data = await response.json();
        else if (response.status === 204) longPoll = performance.now() - started > LONG_POLL_SIGN_MS;
        else if (response.status >= 500) problem = app.SERVER_ERROR();
      } catch (e) { problem = app.CONNECTION_ERROR(); } // offline for a moment, or timed out; try again next tick
      finally { polling = false; }
      // Our own action's answer may have brought this board already: nothing to draw again.
      if (data && data.version !== undefined && String(data.version) === app.version() && !problem) data = null;
      // Outside the try: a mistake in drawing the board must show in the console, not pass for being offline.
      if (data && [app.CONNECTION_ERROR(), app.DRAW_ERROR(), app.SERVER_ERROR()].includes(app.error())) app.setError(""); // through again: the board says where things stand
      if (data) app.receive(data);
      else {
        if (problem) pollFailed(problem);
        if (!app.busy()) app.armTimers(); // nothing new: anything we owe the game that didn't get through goes again
      }
      return data ? "board" : problem ? "failed" : "nothing";
    }

    async function pollLoop() {
      for (;;) {
        const got = await poll();
        // Held requests come back as soon as there's news, so the next goes out at once; plain polling waits its turn,
        // as does a failure (no hammering a server that's struggling) and a tab out of sight (less often still).
        const pause = document.hidden ? app.POLL_MS() * 3 : longPoll && (got === "board" || got === "nothing") ? 50 : app.POLL_MS();
        await new Promise((resolve) => {
          pollWake = resolve;
          setTimeout(resolve, pause);
        });
        pollWake = null;
      }
    }

    // A poll that didn't get through. Before the first board there's nothing else on screen, so the table says what's
    // wrong rather than looking like it's still loading; after it, a server error shows where errors do (a moment
    // offline is left to the next tick).
    function pollFailed(problem) {
      if (!app.board()) {
        app.boardEl().innerHTML = `<p class="panel-error" role="alert">${app.esc()(problem === app.SERVER_ERROR()
          ? "The table couldn't be loaded: the server ran into a problem with this game. Still trying…"
          : "The table couldn't be loaded: can't reach the server. Still trying…")}</p>`;
      } else if (problem === app.SERVER_ERROR() && app.error() !== app.SERVER_ERROR()) {
        app.setError(app.SERVER_ERROR());
        app.render();
      }
    }

    async function act(action) {
      if (app.SPECTATING()) return;
      if (action.type === "duel_concede" && !window.confirm(`Concede the vs. battle? ${app.duel().partner} picks their augment and curse first.`)) return;
      // A card its own text lets us play for free by giving up a character: asks how to pay.
      if (action.type === "move" && !action.free_with && !action.pay_full && (app.board().free_plays || {})[action.uid]
          && (action.to in app.board().me.stage || action.to === "resolution" || action.to === "climax")) {
        app.setModal({ confirmFree: action });
        app.renderModal();
        return;
      }
      if (app.modal() && app.modal().confirmFree) {
        app.setModal(null);
        app.renderModal();
      }
      app.setBusy(true);
      let failed = false;
      app.hideMenu();
      try {
        await animateAction(action);
        const response = await fetchWithin(app.ACTION_TIMEOUT_MS(), app.ACTION_URL(), {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": app.CSRF() },
          body: JSON.stringify(action),
        });
        const data = await response.json();
        if (data.redirect) {
          window.location.href = data.redirect;
          return;
        }
        app.setError(data.error || "");
        if (app.modal() && app.modal().revealed && action.uid && !data.error) {
          app.modal().revealed = app.modal().revealed.filter((c) => c.uid !== action.uid);
        }
        if (data.board || data.status) app.receive(data); else app.render();
      } catch (e) {
        failed = true;
        const offline = e.name === "AbortError" || e instanceof TypeError; // timed out, or no connection
        if (!offline) console.error(e);
        app.setError(offline ? app.CONNECTION_ERROR() : app.DRAW_ERROR());
        try {
          app.render();
        } catch (again) {
          console.error(again);
        }
      } finally {
        app.setBusy(false);
      }
      // It may have gone through all the same (an answer that was lost, or a board that didn't draw): catch up now.
      if (failed) poll();
    }

    return { FLIGHT_MS, act, animateOpponent, opponentSnapshot, pollLoop, wakePoll: () => { if (pollWake) pollWake(); }, zoneEl };
  }

  window.WeissMovement = { create };
})();
