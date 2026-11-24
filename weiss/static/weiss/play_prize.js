/* Moved from play.js (docs/round-two-plan.md, item 8): the section "// --- An infinite challenge's prize: a slot machine". The code is unchanged;
   it reads the live duel through `app` (functions as app.name, values as app.name()). play.js makes one with
   WeissPrize.create(app) and uses the names it returns. */
(function () {
  "use strict";

  function create(app) {
    // --- An infinite challenge's prize: a slot machine on the Victory screen -----------------------------------

    const PRIZE_ICONS = { climax_pack: "⚡", color_pack: "🎨", lucky_pack: "💎" };
    const SLOT_SPINS = 8; // times round the reel before it stops

    function prizeSlotHtml(drawn) {
      // The reel: round and round, then the prize, as the last of its items.
      const items = [];
      for (let turn = 0; turn < SLOT_SPINS; turn++) items.push(...drawn.reel);
      items.push(...drawn.reel.slice(0, drawn.won + 1));
      return `<div class="slot" role="img" aria-label="Your prize: ${app.esc()(drawn.reel[drawn.won].name)}">
        <div class="slot-lights" aria-hidden="true">${"<i></i>".repeat(10)}</div>
        <div class="slot-window" aria-hidden="true"><div class="slot-reel">${items.map((item) =>
          `<div class="slot-item"><span class="slot-icon">${PRIZE_ICONS[item.buff] || "★"}</span><span>${app.esc()(item.name)}</span></div>`).join("")}</div></div>
        <p class="slot-result" hidden>+${drawn.packs} pack and a <strong>${app.esc()(drawn.reel[drawn.won].name)}</strong>!</p>
      </div>`;
    }

    // Spin the reel down to its last item, slowing as it goes, then light up. Seen once a win: a redraw shows it stopped.
    let slotSpun = null;
    function spinPrizeSlot(el, drawn) {
      const reel = el.querySelector(".slot-reel");
      const items = reel.children;
      const stop = items.length - 1;
      const height = items[0].getBoundingClientRect().height;
      const done = () => {
        reel.style.transform = `translateY(${-stop * height}px)`;
        el.classList.add("slot-won");
        el.querySelector(".slot-result").hidden = false;
      };
      const key = `${app.version()}:${drawn.won}`;
      if (!app.animations() || slotSpun === key || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        done();
        return;
      }
      slotSpun = key;
      el.classList.add("slot-spinning");
      reel.animate([{ transform: "translateY(0)" }, { transform: `translateY(${-stop * height}px)` }],
                   { duration: 3200, delay: 900, easing: "cubic-bezier(.15,.55,.15,1)", fill: "forwards" })
        .finished.then(() => {
          el.classList.remove("slot-spinning");
          done();
        }, () => {});
    }

    // A scene the run plays: over the whole board, then the server is told it's done and the run goes on. After a
    // win it waits a moment, so the victory is seen first.
    function showScene() {
      if (!app.sceneData() || app.sceneData().key === app.sceneShown() || !window.ScenePlayer) return;
      const scene = app.sceneData();
      app.setSceneShown(scene.key);
      const overlay = document.createElement("div");
      overlay.className = "scene-overlay";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-label", scene.title || "Scene");
      overlay.innerHTML = `<div class="scene-overlay-stage"></div><button type="button" class="scene-skip">Skip scene</button>`;
      let player = null;
      // With the buffs it gave, if any: in a challenge they're the player's now (the server checks them against the scene).
      const done = () => {
        overlay.remove();
        const picked = player ? player.state() : { buffs: [], fights: [] };
        act({ type: "scene_done", key: scene.key, buffs: picked.buffs.map((given) => [given.step, given.option]),
              fights: picked.fights.map((chosen) => [chosen.step, chosen.option]) });
      };
      overlay.querySelector(".scene-skip").addEventListener("click", done, { once: true });
      const start = () => {
        // The game-over screen is waiting for the last damage to turn over (holdGameOver): the scene comes after it.
        if (app.gameOverHeld()()) return setTimeout(start, app.gameOverHeldUntil() - performance.now() + 1600);
        document.body.appendChild(overlay);
        player = new ScenePlayer(overlay.querySelector(".scene-overlay-stage"), scene, { playerName: app.sceneViewer(), onEnd: () => setTimeout(done, 600) });
        player.start();
      };
      setTimeout(start, app.board() && app.board().game_over ? 1600 : 0);
    }

    const climaxColor = (info) => app.CLIMAX_COLORS()[String((info && info.color) || "").toLowerCase()] || "#ffb347";

    // A climax just played takes over the screen: it darkens in the climax's colour with streaks drawing in while
    // the music builds (or a whoosh rises), then the card and its name slam in on the beat with a flash, rings and a
    // jolt of the board. As it fades, its power surges across its side's stage (play_fx.js climaxSurge). A click puts
    // it away early. `count`: that side's climaxes played, so its sound isn't played twice (playBoardSounds).
    function showClimax(card, owner, count) {
      const info = card && card.card ? app.cards()[card.card] : null;
      if (!info) return;
      app.cuedClimaxes()[owner] = count;
      const heard = app.playSound("climax", { quiet: owner === "opponent" });
      const lead = Math.round(Math.min(900, heard ?? app.CLIMAX_LEAD_MS()));
      const end = lead + app.CLIMAX_HOLD_MS();
      app.setClimaxShowEnds(performance.now() + end + app.CLIMAX_FADE_MS());
      const color = climaxColor(info);
      const whose = owner === "me" && !app.SPECTATING() ? "You play a climax" : `${app.board()[owner] ? app.board()[owner].name : "Your opponent"} plays a climax`;
      const el = document.createElement("div");
      el.className = `cx-takeover${app.reducedMotion() ? " still" : ""}`;
      el.setAttribute("aria-hidden", "true"); // the log says it; this only shows it
      el.style.setProperty("--cx", color);
      el.style.setProperty("--lead", `${lead}ms`);
      el.innerHTML = `<div class="cx-veil"></div><div class="cx-streaks"></div><div class="cx-flash"></div>
        <div class="cx-core">
          <div class="cx-rings"><i></i><i></i><i></i></div>
          <div class="cx-card"${info.grade ? ` data-grade="${info.grade}"` : ""}><img src="${app.esc()(info.image)}" alt="">${info.grade >= 3 ? '<span class="rfx-sheen"></span>' : ""}</div>
          <p class="cx-title">${app.CX_HTML()}<span class="cx-name">${app.esc()(info.name)}</span></p>
          <p class="cx-who">${app.esc()(whose)}</p>
        </div>`;
      document.body.appendChild(el);
      let gone = false;
      const leave = () => {
        if (gone) return;
        gone = true;
        el.classList.add("cx-out");
        setTimeout(() => el.remove(), app.CLIMAX_FADE_MS());
      };
      el.addEventListener("click", leave);
      setTimeout(leave, end);
      // The board jolts as it lands.
      if (!app.reducedMotion()) {
        setTimeout(() => app.boardEl().animate([{ translate: "0 0" }, { translate: "-7px 3px" }, { translate: "6px -3px" }, { translate: "-4px 1px" }, { translate: "2px 0" }, { translate: "0 0" }],
          { duration: 380, easing: "ease-out" }), lead);
      }
      app.fx().climaxSurge(owner, color, end);
    }

    // A climax revealed by damage: it cancels the damage, and both players see that it did.
    function showNegated(pk) {
      const info = app.cards()[pk];
      if (!info) return;
      const el = document.createElement("div");
      el.className = `climax-show ${app.CLIMAX_EFFECTS()[Math.floor(Math.random() * app.CLIMAX_EFFECTS().length)]}`;
      el.style.animationDuration = `${app.CLIMAX_SHOW_MS()}ms`;
      el.innerHTML = `<div class="trigger-show">
        <p class="trigger-show-title damage-negated">Damage Negated!</p>
        <div class="trigger-show-cards"><div class="tc-card negate-card">
          <svg class="negate-shield" viewBox="0 0 100 116" aria-hidden="true"><path d="M50 4 94 20v34c0 28-19 48-44 58C25 102 6 82 6 54V20z"/></svg>
          <img src="${app.esc()(info.image)}" alt="${app.esc()(info.name)}"></div></div>
      </div>`;
      document.body.appendChild(el);
      el.addEventListener("animationend", (event) => { if (event.target === el) el.remove(); }); // not its pieces' own animations
    }

    // An ability that has resolved: its card, in the middle of the screen with the same entrance as a
    // climax, with an arrow to each card it was directed at.
    function showAbility(ability) {
      if (ability.check && app.battle().claimsCheck(ability.id)) return; // an attack's trigger check: the battle view shows it
      if (ability.check) return showTriggerCheck(ability.check, ability.label);
      const source = app.cards()[ability.card];
      if (!source) return;
      const targets = ability.targets.map((pk) => app.cards()[pk]).filter(Boolean);
      const el = document.createElement("div");
      el.className = `climax-show ${app.CLIMAX_EFFECTS()[Math.floor(Math.random() * app.CLIMAX_EFFECTS().length)]}`;
      el.style.animationDuration = `${app.CLIMAX_SHOW_MS()}ms`;
      el.innerHTML = targets.length
        ? `<div class="ability-show" style="--targets: ${targets.length}">
            <img data-source src="${app.esc()(source.image)}" alt="Ability: ${app.esc()(source.name)}">
            <div class="ability-show-targets">${targets.map((t) => `<img data-target src="${app.esc()(t.image)}" alt="Target: ${app.esc()(t.name)}">`).join("")}</div>
            <svg class="ability-arrows" aria-hidden="true"></svg>
          </div>`
        : `<img src="${app.esc()(source.image)}" alt="Ability: ${app.esc()(source.name)}">`;
      document.body.appendChild(el);
      el.addEventListener("animationend", (event) => { if (event.target === el) el.remove(); }); // not its pieces' own animations
      if (targets.length) {
        const images = [...el.querySelectorAll("img")].map((img) => img.decode().catch(() => {}));
        Promise.all(images).then(() => drawArrows(el));
      }
    }

    // A trigger check: the card or cards it turned over, with their icons, or that they have none.
    // Trigger icons as Card.trigger spells them: what the reveal shows for each.
    const TRIGGER_BADGES = {
      soul: ["", "Soul"], draw: ["✋", "Draw"], gate: ["⛩", "Gate"], treasure: ["💰", "Treasure"], choice: ["🔀", "Choice"],
      comeback: ["↩", "Comeback"], standby: ["⏳", "Standby"], shot: ["🎯", "Shot"], bounce: ["↪", "Bounce"], pool: ["💧", "Pool"],
    };

    // A checked card's trigger icons as badges, popping in one after another once the card has turned over; a double
    // soul is one "Soul +2" badge.
    function triggerBadgesHtml(checked) {
      const icons = checked.flatMap((c) => (c.trigger || "").split(/\s+/).filter(Boolean));
      if (!icons.length) return '<p class="tc-none">No trigger</p>';
      const souls = icons.filter((icon) => icon === "soul").length;
      const others = [...new Set(icons.filter((icon) => icon !== "soul"))];
      const badges = [
        ...(souls ? [`<li class="tc-badge tc-soul">${app.SOUL_ICON()}<span>Soul +${souls}</span></li>`] : []),
        ...others.map((icon) => {
          const [symbol, word] = TRIGGER_BADGES[icon] || ["✦", icon.charAt(0).toUpperCase() + icon.slice(1)];
          return `<li class="tc-badge tc-${app.esc()(icon)}"><span aria-hidden="true">${symbol}</span><span>${app.esc()(word)}</span></li>`;
        }),
      ];
      return `<ul class="tc-badges">${badges.map((b, n) => b.replace('class="tc-badge', `style="--n: ${n}" class="tc-badge`)).join("")}</ul>`;
    }

    // Cards checked or revealed, in the middle of the screen: each comes in face down and turns over (a high rarity
    // with its shine), then a trigger check's icons pop in under them.
    function showTriggerCheck(pks, label = null) {
      const checked = pks.map((pk) => app.cards()[pk]).filter(Boolean);
      if (!checked.length) return;
      const el = document.createElement("div");
      el.className = `climax-show ${app.CLIMAX_EFFECTS()[Math.floor(Math.random() * app.CLIMAX_EFFECTS().length)]}`;
      el.style.animationDuration = `${app.CLIMAX_SHOW_MS()}ms`;
      el.innerHTML = `<div class="trigger-show${app.reducedMotion() ? "" : " tc-reveal"}">
        <p class="trigger-show-title">${app.esc()(label || "Trigger check")}</p>
        <div class="trigger-show-cards">${checked.map((c) => `<div class="tc-card"${c.grade ? ` data-grade="${c.grade}"` : ""}>
          <img src="${app.esc()(c.image)}" alt="${app.esc()(c.name)}">${c.grade >= 3 ? '<span class="rfx-sheen" aria-hidden="true"></span>' : ""}
          <span class="tc-back pcard-back" aria-hidden="true"></span></div>`).join("")}</div>
        ${label ? "" : triggerBadgesHtml(checked)}
      </div>`;
      document.body.appendChild(el);
      el.addEventListener("animationend", (event) => { if (event.target === el) el.remove(); }); // not its pieces' own animations
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
    // A side of the table a compact screen isn't showing (announcements on it are left out; its button gets a dot).
    const outOfSight = (el) => !el || !el.getClientRects().length;

    function between(mat, fromSel, toSel) {
      if (outOfSight(mat)) return null;
      const from = mat && mat.querySelector(fromSel);
      const to = mat && mat.querySelector(toSel);
      if (!from || !to) return null;
      const a = from.getBoundingClientRect();
      const b = to.getBoundingClientRect();
      return { x: (a.left + a.right + b.left + b.right) / 4, y: (a.top + a.bottom + b.top + b.bottom) / 4 };
    }

    // A level up, in the middle of the screen for both players as a phase change is (the opponent's level
    // zone may be off the screen): who levelled, and their old level rolling over to the new one. One
    // that comes with a phase change waits for its graphic to go, and two at once take turns.
    let levelShowFree = 0; // when the last level up queued has finished showing (performance.now())
    function showLevelUp(who, level) {
      const now = performance.now();
      const phaseShowing = document.querySelector(".phase-show") ? app.PHASE_PAUSE_MS() : 0;
      const start = Math.max(now + phaseShowing, levelShowFree);
      levelShowFree = start + app.LEVEL_SHOW_MS();
      setTimeout(() => {
        const el = document.createElement("div");
        el.className = "level-show";
        el.style.setProperty("--level-ms", `${app.LEVEL_SHOW_MS()}ms`);
        el.setAttribute("role", "status");
        el.innerHTML = `<div class="phase-show-card level-show-card">
            <span class="phase-show-word">Level up</span>
            <span class="level-show-numbers" aria-hidden="true"><span class="level-show-old">${level - 1}</span><span class="level-show-new">${level}</span></span>
            <span class="level-show-who">${app.esc()(who)}</span>
            <span class="sr-only">${app.esc()(who)} ${who === "You" ? "are" : "is"} now level ${level}</span>
          </div>`;
        document.body.appendChild(el);
        el.addEventListener("animationend", (event) => { if (event.target === el) el.remove(); });
      }, start - now);
    }

    // Text over the board at a point, fading in and out.
    function flash(at, text, className) {
      if (!at) return;
      const el = document.createElement("div");
      el.className = `play-flash ${className}`;
      el.textContent = text;
      el.setAttribute("aria-live", "polite");
      el.style.left = `${at.x}px`;
      el.style.top = `${at.y}px`;
      document.body.appendChild(el);
      el.addEventListener("animationend", (event) => { if (event.target === el) el.remove(); }); // not its pieces' own animations
    }

    return { between, climaxColor, flash, outOfSight, prizeSlotHtml, showAbility, showClimax, showLevelUp, showNegated, showScene, slotSpun, spinPrizeSlot };
  }

  window.WeissPrize = { create };
})();
