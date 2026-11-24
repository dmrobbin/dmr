/* Moved from play.js (docs/round-two-plan.md, item 8): the section "// --- Menus ---". The code is unchanged;
   it reads the live duel through `app` (functions as app.name, values as app.name()). play.js makes one with
   WeissMenus.create(app) and uses the names it returns. */
(function () {
  "use strict";

  function create(app) {
    // --- Menus -----------------------------------------------------------------------------------

    let menuZone = null; // the deck or stage slot whose [...] menu is open, if any

    function showMenu(x, y, title, items) {
      if (app.SPECTATING()) items = items.filter((item) => item !== "-" && (item.view || item.zoom));
      if (!items.length) return hideMenu();
      menuZone = null;
      app.menuEl().classList.remove("see-through");
      const zoom = (z) => `data-zoom-card="${app.esc()(z.pk)}" data-zoom-uid="${app.esc()(z.uid || "")}" data-zoom-zone="${app.esc()(z.zone || "")}"`;
      app.menuEl().innerHTML = `<p class="play-menu-title">${app.esc()(title)}</p>` + items.map((item) => item === "-"
        ? "<hr>"
        : item.zoom ? `<button type="button" ${zoom(item.zoom)}>${app.esc()(item.label)}</button>`
        : `<button type="button" data-menu-item='${app.esc()(JSON.stringify(item.action || {}))}' ${item.prompt ? `data-prompt="${app.esc()(item.prompt)}" data-prompt-default="${app.esc()(item.promptDefault ?? 1)}"` : ""} ${item.view ? `data-view='${app.esc()(JSON.stringify(item.view))}'` : ""}>${app.esc()(item.label)}</button>`).join("")
        + (app.touch() ? '<hr><button type="button" class="play-menu-cancel" data-menu-cancel>Cancel</button>' : ""); // a sheet over the board needs a way out
      app.menuEl().hidden = false;
      const box = app.menuEl().getBoundingClientRect();
      app.menuEl().style.left = `${Math.min(x, window.innerWidth - box.width - 8)}px`;
      app.menuEl().style.top = `${Math.min(y, window.innerHeight - box.height - 8)}px`;
    }

    function hideMenu() {
      app.menuEl().hidden = true;
      menuZone = null;
    }

    // The [...] button on our deck and our occupied stage slots opens its full menu beside the zone.
    function openZoneMenu(zone, zoneEl) {
      const card = zone === "deck" ? null : zoneEl.querySelector(".pcard[data-uid]");
      const [title, items] = zone === "deck" ? pileMenu("deck", "me") : cardMenu(card);
      const box = zoneEl.getBoundingClientRect();
      showMenu(box.right + 6, box.top, title, items);
      app.menuEl().classList.toggle("see-through", zone !== "deck"); // over the stage: let the board show through
      const width = app.menuEl().getBoundingClientRect().width;
      if (box.right + 6 + width > window.innerWidth - 8) { // no room on the right: open to the left
        app.menuEl().style.left = `${Math.max(8, box.left - 6 - width)}px`;
      }
      menuZone = zone;
    }

    function cardMenu(el) {
      const uid = el.dataset.uid;
      const zone = el.dataset.zone;
      const info = el.dataset.card ? app.cards()[el.dataset.card] : null;
      const items = [];
      // With no mouse to rest on a card, the menu is the way to see it whole.
      if (app.touch() && info) items.push({ label: "🔍 View card", zoom: { pk: el.dataset.card, uid, zone } }, "-");
      if (["C1", "C2", "C3"].includes(zone) && el.classList.contains("pos-stand") && app.board().my_turn) {
        items.push({ label: "⚔ Attack (rest + trigger check)", action: { type: "attack", uid } }, "-");
      }
      if (app.STAGE().includes(zone) && el.classList.contains("pos-reverse") && app.canEncore()()) {
        items.push({ label: `Encore: pay ${app.ENCORE_COST()} stock, rest`, action: { type: "encore", uid } }, "-");
      }
      if (["C1", "C2", "C3", "B1", "B2"].includes(zone)) {
        items.push({ label: "Stand", action: { type: "position", uid, pos: "stand" } },
          { label: "Rest", action: { type: "position", uid, pos: "rest" } },
          { label: "Reverse", action: { type: "position", uid, pos: "reverse" } }, "-");
        // For when an ability isn't doing what it should: back to normal at the end of the turn.
        const live = (app.board().stats || {})[uid];
        items.push({ label: "Set power…", action: { type: "set_power", uid }, prompt: "Set this card's power until the end of the turn:", promptDefault: live ? live.power : (info && info.power) || 0 });
        if (live && live.manual) items.push({ label: "Put power back to normal", action: { type: "set_power", uid, clear: true } });
        items.push({ label: "Set soul…", action: { type: "set_soul", uid }, prompt: "Set this card's soul until the end of the turn:", promptDefault: live ? live.soul : (info && info.soul) || 0 });
        if (live && live.manual_soul) items.push({ label: "Put soul back to normal", action: { type: "set_soul", uid, clear: true } });
        items.push("-");
      }
      if (!["hand", "deck", "stock"].includes(zone)) {
        items.push({ label: el.classList.contains("face-down") ? "Turn face up" : "Turn face down", action: { type: "flip", uid } }, "-");
      }
      const unaffordable = zone === "hand" && (!app.canPay()(info) || app.colorMissing()({ uid }));
      for (const to of app.MOVE_TARGETS()) {
        if (unaffordable && app.PLAY_ZONES().includes(to)) continue;
        if (to !== zone) items.push({ label: `→ ${app.LABELS()[to]}`, action: { type: "move", uid, to } });
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
      for (const slot of app.STAGE()) {
        const character = app.board().me.stage[slot];
        if (!character || !allowed(slot)) continue;
        const info = character.card ? app.cards()[character.card] : null;
        const under = `${app.LABELS()[slot].toLowerCase()}${info ? ` (${info.name})` : ""}`;
        items.push({ label: `${prefix} under ${under}, face up`, action: makeAction(slot, false) },
          { label: `${prefix} under ${under}, face down`, action: makeAction(slot, true) });
      }
      return items.length ? ["-", ...items] : [];
    }

    function pileMenu(zone, owner) {
      const view = { owner, zone, title: `${owner === "me" ? "Your" : `${app.board().opponent.name}'s`} ${app.LABELS()[zone].toLowerCase()}` };
      if (owner !== "me") {
        return app.PUBLIC_PILES().includes(zone) || app.isMarkerPile()(zone) ? [app.LABELS()[zone], [{ label: "View all", view }]] : null;
      }
      if (app.isMarkerPile()(zone)) {
        return [app.LABELS()[zone], [
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
      return [app.LABELS()[zone], items];
    }

    app.root().addEventListener("click", (event) => {
      const viewButton = event.target.closest("[data-zoom-card]");
      if (viewButton) {
        app.touchScreen().openViewer(viewButton.dataset.zoomCard, viewButton.dataset.zoomUid || null, viewButton.dataset.zoomZone || null);
        return;
      }
      if (event.target.closest("[data-tray-close]")) {
        app.touchScreen().clearSelection();
        return;
      }
      const sideButton = event.target.closest("[data-board-view]");
      if (sideButton) {
        app.setBoardView(sideButton.dataset.boardView);
        if (app.boardView() === "opponent") app.setOppMoved(false);
        app.setSelected(null);
        hideMenu();
        app.render();
        return;
      }
      const augment = event.target.closest("[data-augment]");
      if (augment) {
        app.showAugment(augment);
        return;
      }
      if (event.target.closest("[data-menu-cancel]")) {
        hideMenu();
        return;
      }
      const menuItem = event.target.closest("[data-menu-item]");
      if (menuItem) {
        if (app.touch()) app.setSelected(null); // the card's been dealt with: put it down
        if (menuItem.dataset.view) {
          app.setModal(JSON.parse(menuItem.dataset.view));
          hideMenu();
          app.renderModal();
          return;
        }
        const action = JSON.parse(menuItem.dataset.menuItem);
        if (menuItem.dataset.prompt) {
          const answer = window.prompt(menuItem.dataset.prompt, menuItem.dataset.promptDefault);
          if (!answer) return hideMenu();
          action.count = Number(answer);
        }
        app.movement().act(action);
        return;
      }
      const zoneMenu = event.target.closest("[data-zone-menu]");
      if (zoneMenu) {
        if (menuZone === zoneMenu.dataset.zoneMenu && !app.menuEl().hidden) hideMenu();
        else openZoneMenu(zoneMenu.dataset.zoneMenu, zoneMenu.closest(".zone") || app.movement().zoneEl(zoneMenu.dataset.zoneMenu)); // or from the tray
        return;
      }
      const confirmClimax = event.target.closest("[data-confirm-climax]");
      if (confirmClimax) {
        app.setModal({ confirmClimax: confirmClimax.dataset.confirmClimax });
        app.renderModal();
        return;
      }
      const flashPick = event.target.closest("[data-flash-pick]");
      if (flashPick) {
        const uid = flashPick.dataset.flashPick;
        if (app.flashPicks().has(uid)) app.flashPicks().delete(uid); else if (app.board().flash && app.flashPicks().size < app.board().flash.need) app.flashPicks().add(uid);
        app.renderModal();
        return;
      }
      const mulliganPick = event.target.closest("[data-mulligan-pick]");
      if (mulliganPick) {
        const uid = mulliganPick.dataset.mulliganPick;
        if (app.mulliganPicks().has(uid)) app.mulliganPicks().delete(uid); else app.mulliganPicks().add(uid);
        app.renderModal();
        return;
      }
      const abilityPick = event.target.closest("[data-ability-pick]");
      if (abilityPick) {
        const uid = abilityPick.dataset.abilityPick;
        const prompt = app.board().ability.prompt;
        if (app.abilityPicks().includes(uid)) app.setAbilityPicks(app.abilityPicks().filter((u) => u !== uid));
        else if (prompt.max === 1) app.setAbilityPicks([uid]);
        else if (app.abilityPicks().length < prompt.max) app.abilityPicks().push(uid);
        app.renderModal();
        return;
      }
      if (event.target.closest("[data-ability-submit]")) {
        const uids = app.abilityPicks();
        app.setAbilityPicks([]);
        app.movement().act({ type: "ability_answer", uids });
        return;
      }
      // Putting a card on the stage: picking previews it; the button below puts it there.
      const placeSlot = event.target.closest("[data-place-pick]");
      const standbyPick = event.target.closest("[data-standby-pick]");
      if (placeSlot || standbyPick) {
        if (placeSlot) app.setPlacePick({ ...app.placePick(), slot: placeSlot.dataset.placePick });
        else app.setPlacePick({ ...app.placePick(), uid: standbyPick.dataset.standbyPick });
        const again = placeSlot ? `[data-place-pick="${app.placePick().slot}"]` : `[data-standby-pick="${app.placePick().uid}"]`;
        app.renderModal();
        const el = app.modalEl().querySelector(again);
        if (el) el.focus(); // the redraw replaced what had focus
        return;
      }
      if (event.target.closest("[data-place-submit], [data-standby-submit]")) {
        const { uid, slot } = app.placePick();
        const standby = Boolean(event.target.closest("[data-standby-submit]"));
        app.setPlacePick({ kind: null, uid: null, slot: null });
        app.movement().act(standby ? { type: "trigger_choice", uid, to: slot } : { type: "ability_answer", value: slot });
        return;
      }
      const abilities = event.target.closest("[data-abilities]");
      if (abilities) {
        app.setModal({ abilities: abilities.dataset.abilities });
        hideMenu();
        app.renderModal();
        return;
      }
      if (event.target.closest("[data-close-after]")) app.setModal(null);
      const discardPick = event.target.closest("[data-discard-pick]");
      if (discardPick) {
        const uid = discardPick.dataset.discardPick;
        if (app.discardPicks().has(uid)) app.discardPicks().delete(uid);
        else if (app.discardPicks().size < app.board().discard.count) app.discardPicks().add(uid);
        app.renderModal();
        return;
      }
      if (event.target.closest("[data-discard-submit]")) {
        const uids = [...app.discardPicks()];
        app.discardPicks().clear();
        app.movement().act({ type: "discard", uids });
        return;
      }
      if (event.target.closest("[data-flash-submit]")) {
        const uids = [...app.flashPicks()];
        app.flashPicks().clear();
        app.movement().act({ type: "flash_level", uids });
        return;
      }
      if (event.target.closest("[data-mulligan-submit]")) {
        const uids = [...app.mulliganPicks()];
        app.mulliganPicks().clear();
        app.movement().act({ type: "mulligan", uids });
        return;
      }
      const levelPick = event.target.closest("[data-level-up]");
      if (levelPick) {
        app.movement().act({ type: "level_up", uid: levelPick.dataset.levelUp });
        return;
      }
      const search = event.target.closest("[data-search-view]");
      if (search) {
        app.setModal(JSON.parse(search.dataset.searchView));
        hideMenu();
        app.renderModal();
        return;
      }
      const phaseButton = event.target.closest("[data-phase]");
      if (phaseButton) {
        app.movement().act({ type: "phase", phase: phaseButton.dataset.phase });
        return;
      }
      if (event.target.closest("[data-rules]")) {
        app.movement().act(app.board().rules_request && app.board().rules_request.mine ? { type: "rules_answer" } : { type: "rules_request" });
        return;
      }
      if (event.target.closest("[data-animations]")) {
        app.setAnimations(!app.animations());
        return;
      }
      if (event.target.closest("[data-sound]")) {
        app.setSound(!app.soundOn());
        return;
      }
      if (event.target.closest("[data-song]")) {
        app.cycleSong();
        return;
      }
      if (event.target.closest("[data-music]")) {
        app.setMusic(!app.musicOn());
        return;
      }
      const layoutButton = event.target.closest("[data-layout]");
      if (layoutButton) {
        app.setLayout(layoutButton.dataset.layout);
        return;
      }
      if (event.target.closest("[data-recap-close]")) {
        app.recap().dismiss();
        return;
      }
      const button = event.target.closest("[data-act]");
      if (button) {
        if (button.closest("[data-tray]")) app.touchScreen().clearSelection(); // done with the picked card
        app.movement().act(JSON.parse(button.dataset.act));
        return;
      }
      const more = event.target.closest("[data-more]");
      if (more) {
        const card = more.closest(".hand-card") ? more.closest(".hand-card").querySelector(".pcard[data-uid]") : app.touchScreen().selectedEl(); // or from the tray
        if (card) {
          const [title, items] = cardMenu(card);
          showMenu(event.clientX, event.clientY, title, items);
        }
        return;
      }
      if (event.target.closest("[data-peek]") || event.target.closest("[data-peek-back]")) {
        app.setPeekKey(event.target.closest("[data-peek]") ? app.shownKey() : null);
        app.renderModal();
        return;
      }
      const peekPile = event.target.closest("[data-peek-pile]");
      if (peekPile) {
        const zone = peekPile.dataset.peekPile;
        app.setPeekKey(app.shownKey());
        app.setModal({ owner: "me", zone, title: `Your ${app.LABELS()[zone].toLowerCase()}`, backToChoice: true });
        app.renderModal();
        return;
      }
      if (event.target.closest("[data-counter-hide]") || event.target.closest("[data-counter-show]")) {
        app.setCounterHidden(event.target.closest("[data-counter-hide]") ? app.counterKey()() : null);
        app.renderModal();
        app.renderAttackPanel();
        return;
      }
      if (event.target.closest("[data-close]") || event.target === app.modalEl()) {
        if (app.modal() && app.modal().backToChoice) app.setPeekKey(null);
        app.setModal(null);
        app.renderModal();
        return;
      }
      // A touch screen: a tap on a card in the hand or on the stage picks it (its buttons go in the tray); one
      // on the other side's card in a pop-up shows it; one on our deck opens its menu (there's no hovering to
      // find the [...] button). A tap anywhere else on the board puts the picked card down.
      if (app.touch()) {
        // A picked hand card, and a tap on a place it can go that's lit up for it: it goes there.
        const spot = app.selected() && event.target.closest(".mat-me .drop-hint[data-drop]");
        if (spot && app.board().me.zones.hand.some((c) => c.uid === app.selected())) {
          const uid = app.selected();
          app.touchScreen().clearSelection();
          app.playTo(uid, spot.dataset.drop);
          return;
        }
        const tapped = event.target.closest(".pcard[data-uid]");
        if (tapped && app.boardEl().contains(tapped) && (tapped.closest(".zone.slot") || tapped.closest(".hand-card"))) {
          app.touchScreen().select(tapped.dataset.uid);
          return;
        }
        if (tapped && app.modalEl().contains(tapped) && tapped.dataset.card && (tapped.dataset.owner !== "me" || app.SPECTATING())) {
          app.touchScreen().openViewer(tapped.dataset.card, tapped.dataset.uid, tapped.dataset.zone);
          return;
        }
        if (!app.SPECTATING() && event.target.closest('[data-pile="deck"][data-owner="me"]')) {
          openZoneMenu("deck", app.movement().zoneEl("deck"));
          return;
        }
        if (app.selected() && app.boardEl().contains(event.target)) app.touchScreen().clearSelection();
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
      const abilityPick = event.target.closest && event.target.closest("[data-ability-pick], [data-place-pick], [data-standby-pick]");
      if (abilityPick && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        abilityPick.click();
        return;
      }
      const flashPick = event.target.closest && event.target.closest("[data-flash-pick]");
      if (flashPick && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        flashPick.click();
        return;
      }
      const levelPick = event.target.closest && event.target.closest("[data-level-up]");
      if (levelPick && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        app.movement().act({ type: "level_up", uid: levelPick.dataset.levelUp });
        return;
      }
      // Ctrl+Z (⌘Z on a Mac): take back our last move, while it can be (not while typing, where it undoes the typing).
      if ((event.key === "z" || event.key === "Z") && (event.ctrlKey || event.metaKey) && !event.shiftKey && !event.altKey
          && !(event.target.closest && event.target.closest("input, textarea, select, [contenteditable]"))) {
        if (app.board() && app.board().undo && !app.SPECTATING() && !app.busy()) {
          event.preventDefault();
          app.movement().act({ type: "undo" });
        }
        return;
      }
      // M: the music on or off, unless typing (chat, a damage amount) or with a modifier held.
      if ((event.key === "m" || event.key === "M") && !event.ctrlKey && !event.metaKey && !event.altKey && !event.repeat
          && !(event.target.closest && event.target.closest("input, textarea, select, [contenteditable]"))) {
        app.toggleMusicKey();
        return;
      }
      if (event.key === "Escape") {
        if (app.closeSummary()) return; // the game's summary over the game-over screen
        if (app.touchScreen().closeViewer()) return; // the full-screen card first, then the rest
        app.touchScreen().clearSelection();
        app.art().hideZoom();
        hideMenu();
        if (app.modal() && app.modal().backToChoice) app.setPeekKey(null);
        app.setModal(null);
        app.renderModal();
      }
    });

    // A tap outside the table (the header, say) closes a menu: on a touch screen it covers the bottom of the screen.
    document.addEventListener("click", (event) => {
      if (!app.menuEl().hidden && !app.root().contains(event.target)) hideMenu();
    });

    return { hideMenu };
  }

  window.WeissMenus = { create };
})();
