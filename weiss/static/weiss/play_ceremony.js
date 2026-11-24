/* The results ceremony of a world duel (docs/duel-presentation-plan.md, part 3): the game-over screen's rewards, played out
   one after another. play.js calls WeissCeremony.play with the result (flags["last_duel"]) and a container for it.

   Each step is skipped when it has nothing to show. A click on the screen, or Enter, Space or Escape, finishes every
   step at once. With animations off every step shows at once, with no movement. When the last step is done, onDone runs
   (play.js shows "Back to the town" and takes focus). Words are Barry's copy (docs/duel-presentation-plan.md). */
(() => {
  const STEP_MS = 600; // between steps
  const COUNT_MS = 800; // the coins count up
  const BAR_MS = 800; // the friendship bar fills
  const NBSP = " ";
  const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const money = (n) => Number(n || 0).toLocaleString();

  // An element from a tag, its attributes (false and null are left out) and its children (text or elements).
  function make(tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) continue;
      el.setAttribute(key, value === true ? "" : String(value));
    }
    el.append(...children.flat().filter((child) => child !== null && child !== undefined && child !== false));
    return el;
  }

  // The steps, as {el, show(instant)}: what each shows, in order. show(true) shows it at once.
  function steps(result, { won, cpuName, onTick }) {
    const list = [];
    const step = (el, show) => { list.push({ el, show }); return el; };

    // 1. Coins: the count, the day's first win and the stakes won as tags. A loss pays a share, and a lost stake is a line.
    const coins = Number(result.coins || 0);
    const stake = Number(result.stake || 0);
    if (coins > 0 || (stake && !won)) {
      const count = make("p", { class: "ceremony-coins" }, `+${money(0)} coins`);
      const tags = [];
      if (won && result.first) tags.push(make("span", { class: "ceremony-tag" }, "First win of the day"));
      if (won && stake) tags.push(make("span", { class: "ceremony-tag" }, "Stakes won"));
      if (!won && coins > 0) tags.push(make("span", { class: "ceremony-tag" }, "For a hard-fought game"));
      const lost = !won && stake ? make("p", { class: "ceremony-muted" }, `The ${money(stake)}-coin stake is gone`) : null;
      const el = make("div", { class: "ceremony-step ceremony-money" }, count, tags.length ? make("div", { class: "ceremony-tags" }, tags) : null, lost);
      step(el, (instant) => {
        el.classList.add("is-in");
        if (instant || reduced()) { count.textContent = `+${money(coins)} coins`; if (coins > 0 && onTick) onTick(); return; }
        const started = performance.now();
        const frame = () => {
          const share = Math.min(1, (performance.now() - started) / COUNT_MS);
          count.textContent = `+${money(Math.round(coins * share))} coins`;
          if (share < 1) requestAnimationFrame(frame);
          else if (onTick) onTick();
        };
        requestAnimationFrame(frame);
      });
    }

    // 2. Friendship: the name, the bar from one share to the next, and +points. A rank reached flourishes.
    const friend = result.friend;
    if (friend) {
      const rankUp = friend.after !== friend.before;
      const fill = make("div", { class: "ceremony-fill" });
      const bar = make("div", { class: "ceremony-bar", role: "img", "aria-label": `${friend.before}: ${Math.round(friend.to * 100)}%` }, fill);
      const rank = make("p", { class: "ceremony-rank" }, rankUp ? friend.before : friend.after);
      const caption = rankUp ? make("p", { class: "ceremony-caption", hidden: true }, "New rank") : null;
      const line = rankUp && result.rank_line ? make("p", { class: "ceremony-muted", hidden: true }, result.rank_line) : null;
      // A friendship that goes down (a loss) shows its bar and points in plain colours, not the gold of a gain.
      const down = Number(friend.to) < Number(friend.from) || Number(result.points || 0) < 0;
      const el = make("div", { class: `ceremony-step ceremony-friend${down ? " is-down" : ""}` },
        make("p", { class: "ceremony-name" }, cpuName),
        bar,
        make("p", { class: "ceremony-points" }, Number(result.points || 0) < 0 ? `-${money(-result.points)}` : `+${money(result.points || 0)}`),
        caption, rank, line); // "New rank" first, then the name with its "!"
      step(el, (instant) => {
        el.classList.add("is-in");
        if (instant || reduced()) {
          fill.style.width = `${friend.to * 100}%`;
          if (rankUp) { rank.textContent = `${friend.after}!`; caption.hidden = false; if (line) line.hidden = false; }
          return;
        }
        fill.style.transition = `width ${BAR_MS}ms ease-out`;
        fill.style.width = `${friend.from * 100}%`;
        requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.width = `${friend.to * 100}%`; }));
        if (rankUp) {
          setTimeout(() => {
            el.classList.add("ceremony-flash");
            rank.textContent = `${friend.after}!`;
            caption.hidden = false;
            if (line) line.hidden = false;
          }, BAR_MS);
        }
      });
    }

    // 3. Quests: one line each, a check ticking in when it's done, or the count on its way.
    for (const quest of result.quests || []) {
      const text = quest.done ? `${quest.text}: done` : `${quest.text}: ${quest.n}${NBSP}/${NBSP}${quest.total}`;
      const el = make("p", { class: `ceremony-step ceremony-quest${quest.done ? " is-done" : ""}` },
        make("span", { class: "ceremony-check", "aria-hidden": "true" }, quest.done ? "✓" : "•"), text);
      step(el, (instant) => el.classList.add("is-in"));
    }

    // 4. The tournament's words, as they come (the server's).
    if (result.event) {
      const el = make("p", { class: "ceremony-step ceremony-event" }, result.event);
      step(el, (instant) => el.classList.add("is-in"));
    }

    // 5. Rewards: as the server gives them.
    for (const reward of result.rewards || []) {
      const el = make("p", { class: "ceremony-step ceremony-reward" }, `★ ${reward}`);
      step(el, (instant) => el.classList.add("is-in"));
    }
    // A card pick won with the duel waits in the town (last_duel.card_pick, from the server). Barry's copy.
    if (result.card_pick) {
      const el = make("p", { class: "ceremony-step ceremony-reward" }, "★ A card pick is waiting in the town");
      step(el, (instant) => el.classList.add("is-in"));
    }

    // 6. Defeat: a muted line, last, above the button that goes back to the town.
    if (!won) {
      const el = make("p", { class: "ceremony-step ceremony-muted ceremony-leave" }, "Shake it off. There's always a rematch.");
      step(el, (instant) => el.classList.add("is-in"));
    }
    return list;
  }

  // Plays the result into the container. skipTarget: the screen a click or key skips the ceremony on.
  // Returns {finish}: finishes it at once.
  function play(container, result, { won, cpuName, animations, skipTarget, onTick, onDone }) {
    const list = steps(result || {}, { won: Boolean(won), cpuName: cpuName || result.cpu || "", onTick });
    container.classList.add("ceremony");
    container.replaceChildren(...list.map((item) => item.el));
    const timers = [];
    let next = 0;
    let finished = false;
    const instant = !animations || reduced();

    const done = () => {
      if (finished) return;
      finished = true;
      timers.forEach(clearTimeout);
      skipTarget.removeEventListener("click", finish);
      document.removeEventListener("keydown", onKey, true);
      setTimeout(() => { if (onDone) onDone(); }, 0);
    };
    function finish() {
      while (next < list.length) list[next++].show(true);
      done();
    }
    function onKey(event) {
      if (!container.isConnected) { done(); return; }
      if (["Enter", " ", "Escape"].includes(event.key)) { event.preventDefault(); finish(); }
    }

    if (instant || list.length === 0) {
      finish();
      return { finish };
    }
    skipTarget.addEventListener("click", finish);
    document.addEventListener("keydown", onKey, true);
    const runNext = () => {
      if (finished) return;
      if (next >= list.length) { done(); return; }
      list[next++].show(false);
      timers.push(setTimeout(runNext, STEP_MS));
    };
    timers.push(setTimeout(runNext, 400)); // the Victory or Defeat word first
    return { finish };
  }

  window.WeissCeremony = { play };
})();
