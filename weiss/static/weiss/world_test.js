/* The town test (weiss/world_test.html): places drawn as backdrops, the CPUs who are there standing in them, and
   talking, gifts and duels in a box over the scene. Time, coins and friendship are made up and kept in this tab
   (sessionStorage); the duel posts to the real "play a CPU" form. */
(() => {
  const root = document.querySelector("[data-town]");
  if (!root) return;
  const world = JSON.parse(document.getElementById("town-data").textContent);
  const $ = (sel) => root.querySelector(sel);
  const stage = $("[data-stage]");
  const backdrop = $("[data-backdrop]");
  const light = $("[data-light]");
  const people = $("[data-people]");
  const empty = $("[data-empty]");
  const box = $("[data-box]");
  const nameEl = $("[data-name]");
  const bondEl = $("[data-bond]");
  const textEl = $("[data-text]");
  const menu = $("[data-menu]");
  const nextEl = $("[data-next]");
  const map = $("[data-map]");
  const mapButton = $("[data-open-map]");
  const toast = $("[data-toast]");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const SLOTS = ["Morning", "Noon", "Evening", "Night"];
  const RANKS = [[0, "Stranger"], [10, "Acquaintance"], [25, "Friend"], [45, "Good friend"], [70, "Close friend"], [100, "Best friend"]];
  const TYPE_MS = 22;
  const KEY = "town-test";
  const places = new Map(world.places.map((p) => [p.key, p]));
  const cpus = new Map(world.cpus.map((c) => [c.id, c]));

  // ---- State, kept in this tab ----

  const fresh = () => ({ turn: 0, place: world.places[0].key, coins: 1000, bonds: {}, talked: {}, gifted: {} });
  let state;
  let returning = false;
  try {
    const kept = sessionStorage.getItem(KEY);
    returning = Boolean(kept);
    state = { ...fresh(), ...JSON.parse(kept || "{}") };
  } catch {
    state = fresh();
  }
  const save = () => {
    try { sessionStorage.setItem(KEY, JSON.stringify(state)); } catch { /* a private window: it lasts until the page goes */ }
  };
  const today = () => Math.floor(state.turn / 4);
  const weekday = () => today() % 7;
  const slot = () => state.turn % 4;
  const bond = (cpu) => state.bonds[cpu.id] || 0;
  const rank = (cpu) => RANKS.reduce((at, [points], i) => (bond(cpu) >= points ? i : at), 0);

  // ---- Who's where ----

  // A number from 0 to 1 that's always the same for the same inputs: the same CPU is in the same place on reload.
  function chance(...parts) {
    let h = 2166136261;
    for (const c of parts.join(":")) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    return ((h ^ (h >>> 13)) >>> 0) / 4294967296;
  }

  // Where a CPU is at a moment, by its rules in order: the first whose day and time match, and whose roll comes up.
  // A "once a day" rule picks one of its times each day, and holds only then.
  function whereIs(cpu, turn = state.turn) {
    const day = Math.floor(turn / 4);
    const time = turn % 4;
    for (const [i, rule] of cpu.schedule.entries()) {
      if (!rule.days.includes(day % 7) || !rule.slots.includes(time)) continue;
      if (rule.once && rule.slots[Math.floor(chance(cpu.id, day, i, "once") * rule.slots.length)] !== time) continue;
      if (chance(cpu.id, turn, i) * 100 < rule.chance) return rule.place;
    }
    return null;
  }
  const here = (place = state.place, turn = state.turn) => world.cpus.filter((cpu) => whereIs(cpu, turn) === place);

  // ---- The scene ----

  const LIGHTS = ["town-morning", "town-noon", "town-evening", "town-night"];
  const DAYLIT = new Set(["sakura", "beach", "ocean", "classroom", "forest", "snow", "desert"]);

  function paintPlace() {
    const place = places.get(state.place);
    const art = place.backdrops[slot()];
    backdrop.dataset.bg = art;
    backdrop.innerHTML = window.SceneBackdrops ? SceneBackdrops.draw(art) : "";
    // Light for the time of day, only over scenes drawn in daylight: the others are drawn at their own time already.
    light.className = `town-light ${DAYLIT.has(art) ? LIGHTS[slot()] : ""}`;
    $("[data-place-name]").textContent = place.name;
    $("[data-when]").textContent = `${DAYS[weekday()]} · ${SLOTS[slot()]}`;
    $("[data-coins]").textContent = `${state.coins.toLocaleString()} coins`;
    paintPeople();
  }

  function portrait(cpu, mood = "main") {
    const pics = cpu.portraits;
    if (pics.kind === "none") return silhouette(cpu);
    const img = document.createElement("img");
    img.className = `town-picture town-${pics.kind}`;
    img.src = pics[mood] || pics.main;
    img.alt = "";
    img.draggable = false;
    img.addEventListener("error", () => img.replaceWith(portrait({ ...cpu, portraits: { kind: "none" } })), { once: true });
    return img;
  }

  // Someone with no picture (or one that won't load): a figure in a colour of their own, their initial on it.
  function silhouette(cpu) {
    const hue = (cpu.id * 47) % 360;
    const id = `town-sil-${cpu.id}-${Math.floor(Math.random() * 1e6)}`;
    const wrap = document.createElement("span");
    wrap.className = "town-picture town-silhouette";
    wrap.innerHTML = `<svg viewBox="0 0 200 400" aria-hidden="true" focusable="false">
      <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="hsl(${hue} 45% 62%)"/><stop offset="1" stop-color="hsl(${hue} 40% 26%)"/></linearGradient></defs>
      <g fill="url(#${id})">
        <path d="M100 18c-34 0-52 24-52 54 0 20 6 34 10 44-4 18-10 34-18 44l26-4c6 6 20 12 34 12s28-6 34-12l26 4c-8-10-14-26-18-44 4-10 10-24 10-44 0-30-18-54-52-54z"/>
        <path d="M84 158h32v22c30 6 54 22 62 52l10 168H12l10-168c8-30 32-46 62-52z"/>
      </g>
      <path d="M100 52c-24 0-38 14-40 30 6-6 18-12 30-14 14 6 30 8 50 6-2 26-10 52-40 60-22-4-36-24-40-52-4 30 10 66 40 70 32-4 44-38 42-70-4-18-18-30-42-30z"
        fill="hsl(${hue} 30% 86% / .5)"/>
      <text x="100" y="300" text-anchor="middle" font-family="Georgia, serif" font-size="64" font-weight="700" fill="rgb(255 255 255 / .55)">${cpu.name.slice(0, 1).toUpperCase()}</text>
    </svg>`;
    return wrap;
  }

  function paintPeople() {
    const present = here();
    people.replaceChildren();
    const spots = present.length === 1 ? [50] : present.map((_, i) => 14 + (72 / (present.length - 1)) * i);
    present.forEach((cpu, i) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "town-person";
      button.dataset.cpu = cpu.id;
      button.style.left = `${spots[i]}%`;
      button.style.setProperty("--delay", `${i * 90}ms`);
      button.setAttribute("aria-label", `Talk to ${cpu.name}`);
      const tag = document.createElement("span");
      tag.className = "town-tag";
      tag.textContent = cpu.name;
      button.append(portrait(cpu), tag);
      button.addEventListener("click", () => meet(cpu));
      people.append(button);
    });
    empty.hidden = present.length > 0;
  }

  let toastTimer;
  function say(text) {
    toast.textContent = text;
    toast.classList.add("town-toast-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("town-toast-on"), 3200);
  }

  // A soft fade between places and times (none for anyone who's asked for less motion).
  function fade(change) {
    if (reduced) {
      change();
      return;
    }
    stage.classList.add("town-fading");
    setTimeout(() => {
      change();
      stage.classList.remove("town-fading");
    }, 260);
  }

  // ---- Talking ----

  let talking = null; // the CPU being talked to
  let advance = null; // what a click or key does while a line is showing

  const fill = (text) => text.replaceAll("{player}", world.player).replaceAll("{place}", places.get(state.place).name.toLowerCase());
  const pick = (list, ...salt) => list[Math.floor(chance(talking ? talking.id : 0, state.turn, ...salt) * list.length)];

  const LINES = {
    greet: [
      ["Hm? Do I know you?", "Oh. Hello.", "You look like a duelist. Are you?"],
      ["Oh, {player}. Hi.", "Back again?", "Hey, {player}."],
      ["{player}! Good to see you.", "I was hoping you'd turn up.", "Hey! Got your deck with you?"],
      ["{player}! Perfect timing, I was bored.", "There you are. I saved you a seat.", "{player}! I've been thinking about my next deck. Want to hear it?"],
    ],
    chat: [
      ["The {place} is nice this time of day.", "I come here to think about my deck.", "Have you opened any good packs lately?"],
      ["I lost a game yesterday to a climax I never saw coming. Still annoyed.", "Do you play more for the cards or the people?",
       "Someone here keeps winning with a deck I can't figure out."],
      ["You're getting stronger. I can tell from how you talk about your games.", "Promise me a proper rematch some time.",
       "I've been saving a card for a deck I haven't built yet. Silly, right?"],
    ],
    again: ["We already talked today, {player}. Not that I mind.", "Again? You must like the {place}.", "Same as earlier, still here."],
    loved: ["For me? I love this!", "How did you know? Thank you!"],
    liked: ["Thanks, {player}. That's nice of you.", "Oh, nice. Thank you."],
    meh: ["Oh. Thank you, I suppose.", "Huh. Thanks."],
    disliked: ["…Thanks. I'll find a use for it.", "Ah. That's… not really my thing."],
    gifted: ["You've already given me something today. Save your coins!"],
    leave: ["See you around.", "Later, {player}.", "Don't be a stranger."],
  };

  function bondText(cpu) {
    const r = rank(cpu);
    const hearts = "♥".repeat(r) + "♡".repeat(RANKS.length - 1 - r);
    const next = RANKS[r + 1];
    return `<span class="town-hearts" aria-hidden="true">${hearts}</span> ${RANKS[r][1]}` +
      (next ? ` <span class="town-to-next">${next[0] - bond(cpu)} to ${next[1].toLowerCase()}</span>` : "");
  }

  function setMood(cpu, mood) {
    const img = people.querySelector(`[data-cpu="${cpu.id}"] .town-picture`);
    if (img && cpu.portraits[mood]) img.src = cpu.portraits[mood];
  }

  function gain(cpu, points) {
    if (!points) return;
    const before = rank(cpu);
    state.bonds[cpu.id] = Math.max(0, bond(cpu) + points);
    save();
    const button = people.querySelector(`[data-cpu="${cpu.id}"]`);
    if (button) {
      const float = document.createElement("span");
      float.className = `town-float ${points < 0 ? "town-float-down" : ""}`;
      float.textContent = `${points > 0 ? "+" : ""}${points} ♥`;
      button.append(float);
      setTimeout(() => float.remove(), 1400);
    }
    bondEl.innerHTML = bondText(cpu);
    if (rank(cpu) > before) say(`${cpu.name} is now your ${RANKS[rank(cpu)][1].toLowerCase()}!`);
  }

  // Show lines one after another, each typed out; a click, Enter or Space shows it all, then goes on.
  function lines(list, then) {
    menu.replaceChildren();
    let i = 0;
    const show = () => {
      const text = fill(list[i]);
      nextEl.hidden = true;
      box.classList.remove("vn-ready");
      let shown = reduced ? text.length : 0;
      textEl.textContent = text.slice(0, shown);
      const done = () => {
        clearInterval(timer);
        textEl.textContent = text;
        box.classList.add("vn-ready");
        nextEl.hidden = false;
        advance = () => {
          i += 1;
          if (i < list.length) show();
          else {
            advance = null;
            box.classList.remove("vn-ready");
            nextEl.hidden = true;
            then();
          }
        };
      };
      const timer = setInterval(() => {
        shown += 1;
        textEl.textContent = text.slice(0, shown);
        if (shown >= text.length) done();
      }, TYPE_MS);
      if (shown >= text.length) done();
      else advance = done;
    };
    show();
    box.focus({ preventScroll: true });
  }

  function options(list) {
    menu.replaceChildren();
    for (const [label, act, extra = {}] of list) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `town-option ${extra.quiet ? "town-option-quiet" : ""}`;
      button.innerHTML = label;
      button.disabled = Boolean(extra.disabled);
      if (extra.title) button.title = extra.title;
      button.addEventListener("click", act);
      menu.append(button);
    }
    menu.querySelector("button:not(:disabled)")?.focus({ preventScroll: true });
  }

  // ---- You, in a conversation: your portrait comes in on the left, and the one you're talking to moves right ----

  const me = $("[data-me]");
  const meFigure = $("[data-me-figure]");
  let myKit = null;
  if (world.portrait && window.Portrait) {
    Portrait.load(root.dataset.portraits).then((kit) => { myKit = kit; }).catch(() => { myKit = null; });
  }
  // How you look: your saved expression, or one for a feeling (Portrait.MOODS) where your portrait has one.
  function myMood(mood) {
    if (myKit) myKit.draw(meFigure, world.portrait, mood ? { mood } : {});
  }

  function stageFor(cpu) {
    const chosen = people.querySelector(`[data-cpu="${cpu.id}"]`);
    if (!myKit || !chosen) return;
    chosen.dataset.home = chosen.style.left;
    chosen.style.left = "70%";
    myMood("smile");
    stage.classList.add("town-staged");
    me.hidden = false;
    requestAnimationFrame(() => me.classList.add("town-me-in"));
  }

  function unstage(cpu) {
    me.classList.remove("town-me-in");
    me.hidden = true;
    stage.classList.remove("town-staged");
    const chosen = cpu && people.querySelector(`[data-cpu="${cpu.id}"]`);
    if (chosen && chosen.dataset.home) chosen.style.left = chosen.dataset.home;
  }

  function meet(cpu) {
    if (talking) return;
    talking = cpu;
    for (const el of people.children) el.classList.toggle("town-away", Number(el.dataset.cpu) !== cpu.id);
    people.querySelector(`[data-cpu="${cpu.id}"]`)?.classList.add("town-chosen");
    stageFor(cpu);
    box.hidden = false;
    nameEl.textContent = cpu.name;
    bondEl.innerHTML = bondText(cpu);
    lines([pick(LINES.greet[Math.min(rank(cpu), 3)], "greet")], mainMenu);
  }

  function mainMenu() {
    const cpu = talking;
    setMood(cpu, "main");
    myMood("smile");
    textEl.textContent = fill(`What would you like to do?`);
    options([
      ["Talk", talk],
      ["Give a gift", giftMenu],
      ["Duel", duelMenu],
      ["Leave", leave, { quiet: true }],
    ]);
  }

  function talk() {
    const cpu = talking;
    if (state.talked[cpu.id] === today()) {
      lines([pick(LINES.again, "again")], mainMenu);
      return;
    }
    state.talked[cpu.id] = today();
    save();
    const tier = Math.min(rank(cpu), 2);
    lines([pick(LINES.chat[tier], "chat1"), pick(LINES.chat[Math.max(0, tier - 1)], "chat2")], () => {
      gain(cpu, bond(cpu) ? 2 : 3);
      mainMenu();
    });
  }

  function giftMenu() {
    const cpu = talking;
    if (state.gifted[cpu.id] === today()) {
      lines([LINES.gifted[0]], mainMenu);
      return;
    }
    textEl.textContent = `Give ${cpu.name} something? You have ${state.coins.toLocaleString()} coins.`;
    options([
      ...world.gifts.map((gift) => [`${gift.name} <span class="town-price">${gift.price}</span>`, () => give(gift),
        { disabled: state.coins < gift.price, title: gift.about }]),
      ["Back", mainMenu, { quiet: true }],
    ]);
  }

  function give(gift) {
    const cpu = talking;
    state.coins -= gift.price;
    state.gifted[cpu.id] = today();
    save();
    $("[data-coins]").textContent = `${state.coins.toLocaleString()} coins`;
    const [loved, liked, disliked] = cpu.likes;
    const [kind, points, mood] = gift.key === loved ? ["loved", 8, "pleased"] : gift.key === liked ? ["liked", 4, "pleased"]
      : gift.key === disliked ? ["disliked", -3, "dismayed"] : ["meh", 1, "main"];
    setMood(cpu, mood);
    myMood({ loved: "happy", liked: "smile", disliked: "sad", meh: "neutral" }[kind]);
    lines([pick(LINES[kind], "gift")], () => {
      gain(cpu, points);
      mainMenu();
    });
  }

  function duelMenu() {
    const cpu = talking;
    if (!cpu.duel) {
      lines([`${cpu.name} isn't ready to duel yet. (Not finalized, or no deck.)`], mainMenu);
      return;
    }
    if (!world.decks.length) {
      lines(["You'll need a deck first. Build one under My lists."], mainMenu);
      return;
    }
    setMood(cpu, "pleased");
    myMood("smug");
    lines([cpu.intro || "A duel? Sure. Show me what you've got."], () => {
      textEl.textContent = "Which deck? The duel uses up this part of the day.";
      const select = document.createElement("select");
      select.className = "town-deck";
      select.setAttribute("aria-label", "Your deck");
      for (const deck of world.decks) select.add(new Option(deck.name, deck.id));
      options([
        ["Start the duel", () => duel(select.value)],
        ["Back", mainMenu, { quiet: true }],
      ]);
      menu.prepend(select);
      select.focus({ preventScroll: true });
    });
  }

  function duel(deckId) {
    const cpu = talking;
    state.turn += 1; // a duel takes up the time slot, win or lose
    gain(cpu, 2);
    save();
    const form = document.querySelector("[data-duel-form]");
    form.querySelector("[data-duel-cpu]").value = cpu.id;
    form.querySelector("[data-duel-deck]").value = deckId;
    form.submit();
  }

  function leave() {
    const cpu = talking;
    lines([pick(LINES.leave, "leave")], () => close(cpu));
  }

  function close(cpu = talking) {
    talking = null;
    advance = null;
    box.hidden = true;
    unstage(cpu);
    for (const el of people.children) el.classList.remove("town-away", "town-chosen");
    if (cpu) {
      setMood(cpu, "main");
      people.querySelector(`[data-cpu="${cpu.id}"]`)?.focus({ preventScroll: true });
    }
  }

  // ---- The map and the clock ----

  function openMap() {
    if (talking) close();
    const list = $("[data-places]");
    list.replaceChildren();
    for (const place of world.places) {
      const who = here(place.key);
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "town-place";
      button.disabled = place.key === state.place;
      button.innerHTML = `<span class="town-place-art">${window.SceneBackdrops ? SceneBackdrops.draw(place.backdrops[slot()]) : ""}</span>
        <span class="town-place-name">${place.name}${place.key === state.place ? ' <span class="muted small">(you’re here)</span>' : ""}</span>
        <span class="town-place-who small muted">${who.length ? who.map((c) => c.name).join(", ") : "Nobody right now"}</span>`;
      button.addEventListener("click", () => go(place.key));
      item.append(button);
      list.append(item);
    }
    map.hidden = false;
    mapButton.setAttribute("aria-expanded", "true");
    list.querySelector("button:not(:disabled)")?.focus({ preventScroll: true });
  }

  function closeMap() {
    map.hidden = true;
    mapButton.setAttribute("aria-expanded", "false");
    mapButton.focus({ preventScroll: true });
  }

  function go(key) {
    map.hidden = true;
    mapButton.setAttribute("aria-expanded", "false");
    fade(() => {
      state.place = key;
      save();
      paintPlace();
      const who = here();
      say(who.length ? `${places.get(key).name}: ${who.map((c) => c.name).join(", ")} ${who.length === 1 ? "is" : "are"} here.` : `${places.get(key).name}: nobody's here right now.`);
      (people.querySelector("button") || mapButton).focus({ preventScroll: true });
    });
  }

  function wait() {
    if (talking) close();
    const before = new Set(here().map((c) => c.id));
    fade(() => {
      const newDay = slot() === 3;
      state.turn += 1;
      save();
      paintPlace();
      const after = here();
      const came = after.filter((c) => !before.has(c.id)).map((c) => c.name);
      const went = [...before].filter((id) => !after.some((c) => c.id === id)).map((id) => cpus.get(id).name);
      const news = [newDay ? `A new day: ${DAYS[weekday()]}.` : `${SLOTS[slot()]}.`];
      if (went.length) news.push(`${went.join(", ")} left.`);
      if (came.length) news.push(`${came.join(", ")} arrived.`);
      say(news.join(" "));
    });
  }

  // ---- Input ----

  box.tabIndex = -1;
  box.addEventListener("click", (event) => {
    if (advance && !event.target.closest("button, select")) advance();
  });
  stage.addEventListener("click", (event) => {
    if (advance && !event.target.closest("button, select, [data-box]")) advance();
  });
  mapButton.addEventListener("click", () => (map.hidden ? openMap() : closeMap()));
  $("[data-close-map]").addEventListener("click", closeMap);
  $("[data-wait]").addEventListener("click", wait);
  $("[data-reset]").addEventListener("click", () => {
    state = fresh();
    save();
    close();
    paintPlace();
    say("Started over: Monday morning, 1,000 coins, no friends yet.");
  });
  document.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea, select") && event.key !== "Escape") return;
    if ((event.key === "Enter" || event.key === " ") && advance && !event.target.closest("button")) {
      event.preventDefault();
      advance();
    } else if (event.key === "Escape") {
      if (!map.hidden) closeMap();
      else if (talking && !advance) {
        if (menu.querySelector(".town-option") && textEl.textContent === "What would you like to do?") leave();
        else mainMenu();
      }
    } else if (event.key.toLowerCase() === "m" && !talking && !event.ctrlKey && !event.metaKey && !event.altKey) {
      map.hidden ? openMap() : closeMap();
    }
  });

  // Start somewhere with company, the first time.
  if (!returning) {
    const busiest = world.places.map((p) => [p.key, here(p.key).length]).sort((a, b) => b[1] - a[1])[0];
    if (busiest && busiest[1]) state.place = busiest[0];
    save();
  }
  paintPlace();
})();
