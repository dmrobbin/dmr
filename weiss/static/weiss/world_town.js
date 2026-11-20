/* The town (weiss/world_town.html): a save's place as a scene, with who's there, the time, coins, the map, the card
   shop and waiting. The server keeps it all (weiss.world.town): the page draws what it's given, and posts each move
   with the version it saw, so two tabs can't both spend the same time. Talking to someone offers a duel (a real game,
   world_views.world_duel), talking (their lines play out here, but run on the server: weiss.chatter), and gifts. */
(() => {
  const root = document.querySelector("[data-world-town]");
  if (!root) return;
  const $ = (sel) => root.querySelector(sel);
  const stage = $("[data-stage]");
  const backdrop = $("[data-backdrop]");
  const light = $("[data-light]");
  const people = $("[data-people]");
  const empty = $("[data-empty]");
  const box = $("[data-box]");
  const textEl = $("[data-text]");
  const menu = $("[data-menu]");
  const nextEl = $("[data-next]");
  const map = $("[data-map]");
  const shop = $("[data-shop]");
  const mapButton = $("[data-open-map]");
  const shopButton = $("[data-open-shop]");
  const waitButton = $("[data-wait]"); // the HUD's, once the time's spent here
  const menuButton = $("[data-open-menu]");
  const menuPanel = $("[data-menu-panel]");
  const menuWait = $("[data-menu-wait]");
  const fullscreenButtons = root.querySelectorAll("[data-fullscreen], [data-menu-fullscreen]");
  const toast = $("[data-toast]");
  const csrf = root.querySelector("[name=csrfmiddlewaretoken]").value;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const TYPE_MS = 22;

  let town = JSON.parse(document.getElementById("town-state").textContent);
  const result = JSON.parse(document.getElementById("town-result").textContent);
  let busy = false;
  let talking = null; // the person being talked to
  let advance = null; // what a click or key does while a line is showing

  // ---- Drawing the place ----

  function paint() {
    const place = town.place;
    if (place) {
      backdrop.dataset.bg = place.backdrop;
      backdrop.innerHTML = window.SceneBackdrops ? SceneBackdrops.draw(place.backdrop, town.time) : "";
      light.className = "town-light"; // the time of day is drawn into the backdrop (backdrops.js)
      $("[data-place-name]").textContent = place.name;
      document.title = `${place.name} · ${document.title.split(" · ").slice(1).join(" · ")}`;
    }
    $("[data-when]").textContent = `${town.date} · ${town.time_name.toLowerCase()}`;
    paintEvents();
    $("[data-coins]").textContent = `${town.money.toLocaleString()} coins`;
    shopButton.hidden = !town.shop;
    const banner = $("[data-duel-banner]");
    banner.hidden = !town.duel;
    if (town.duel) {
      banner.innerHTML = "";
      banner.append(`You're in a duel with ${town.duel.cpu}; time stays where it is until it's over. `);
      const back = document.createElement("a");
      back.href = town.duel.url;
      back.textContent = "Back to the duel";
      banner.append(back);
    }
    paintTime();
    $("[data-deck-notice]").hidden = town.deck_ready || Boolean(town.tutorial && town.tutorial.step !== "deck");
    $("[data-deck-hint]").textContent = town.deck_ready ? "" : "Not ready to duel yet";
    paintQuests();
    const waiting = $("[data-scene-waiting]");
    const linked = result && result.scene; // the duel's result banner links to it already
    waiting.hidden = !town.scene || Boolean(linked);
    if (town.scene && !linked) {
      waiting.replaceChildren(`♥ ${town.scene.who ? `A moment with ${town.scene.who}` : "A moment"} is waiting for you. `,
        Object.assign(document.createElement("a"), { href: town.scene.url, textContent: "Watch it now" }));
    }
    showNews(town.news);
    town.news = [];
    paintPeople();
    paintPick();
    renderTutorial();
    announce();
    if (!map.hidden) listPlaces();
    if (!shop.hidden) listStock();
  }

  function silhouette(person) {
    const hue = (person.id * 47) % 360;
    const id = `town-sil-${person.id}-${Math.floor(Math.random() * 1e6)}`;
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
    </svg>`;
    return wrap;
  }

  function picture(person, mood = "main") {
    const pics = person.portraits;
    if (pics.kind === "none") return silhouette(person);
    const img = document.createElement("img");
    img.className = `town-picture town-${pics.kind}`;
    img.src = pics[mood] || pics.main;
    img.alt = "";
    img.draggable = false;
    img.addEventListener("error", () => img.replaceWith(silhouette(person)), { once: true });
    return img;
  }

  function paintPeople() {
    if (talking && !town.people.some((p) => p.id === talking.id)) closeTalk(false);
    people.replaceChildren();
    const here = town.people;
    const spots = here.length === 1 ? [50] : here.map((_, i) => 14 + (72 / (here.length - 1)) * i);
    here.forEach((person, i) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "town-person";
      button.dataset.cpu = person.id;
      button.style.left = `${spots[i]}%`;
      button.dataset.spot = spots[i]; // where they stand when nobody's talking to them (applyTalkFocus)
      button.style.setProperty("--delay", `${i * 90}ms`);
      const marker = questMarker(person);
      button.setAttribute("aria-label", `Talk to ${person.name}${marker ? `: ${marker.label}` : ""}`);
      const tag = document.createElement("span");
      tag.className = "town-tag";
      tag.textContent = person.name;
      button.append(picture(person), tag);
      if (marker) {
        const badge = document.createElement("span");
        badge.className = `town-quest-mark town-quest-${marker.kind}`;
        badge.setAttribute("aria-hidden", "true");
        badge.textContent = marker.kind === "offer" ? "!" : "★";
        badge.title = marker.label;
        button.append(badge);
      }
      button.dataset.tutorial = "person";
      button.addEventListener("click", () => (town.tutorial && town.tutorial.step === "arrive" ? approach(person) : meet(person)));
      people.append(button);
    });
    empty.hidden = here.length > 0;
    applyTalkFocus();
  }

  // Talking to someone moves them to the middle of the stage and dims the place behind them (the .town-talking CSS);
  // the others step back as they always have. Undone when the talk closes. Under reduced motion nobody moves: the
  // place just fades.
  function applyTalkFocus() {
    stage.classList.toggle("town-talking", Boolean(talking));
    for (const el of people.children) {
      const focused = Boolean(talking) && Number(el.dataset.cpu) === talking.id;
      el.classList.toggle("town-away", Boolean(talking) && !focused);
      el.classList.toggle("town-chosen", focused);
      if (!reduced) el.style.left = `${focused ? 50 : el.dataset.spot}%`;
    }
  }

  // Tells the rest of the page (the sound, see world:town in the docs) what the town is showing now.
  function announce() {
    document.dispatchEvent(new CustomEvent("world:town", { detail: {
      place: town.place && town.place.key, time: town.time, events: (town.events && town.events.today) || [], talking: Boolean(talking) } }));
  }

  // Someone with a quest for the player ("!") or something to do about one ("★"): marked over their head.
  function questMarker(person) {
    const q = person.quests || {};
    if ((q.settles || []).length) return { kind: "act", label: "a quest to finish" };
    if ((q.talks || []).length || (q.hands || []).length) return { kind: "act", label: "something about a quest" };
    if ((q.offers || []).length) return { kind: "offer", label: "has something to ask you" };
    return null;
  }

  // Quest news (a duel won, somewhere reached): kept above the stage until dismissed, so nothing's missed.
  function showNews(items) {
    const box = $("[data-news]");
    if (!items || !items.length) return;
    const list = box.querySelector("ul");
    for (const item of items) {
      const li = document.createElement("li");
      if (item.quest) {
        const title = document.createElement("strong");
        title.textContent = `${item.quest}: `;
        li.append(title);
      }
      li.append(item.text);
      if (item.link) {
        li.append(" ");
        li.append(Object.assign(document.createElement("a"), { href: item.link, textContent: "Watch" }));
      }
      list.append(li);
    }
    box.hidden = false;
  }

  function paintQuests() {
    const link = $("[data-quests]");
    const { active = 0, ready = 0 } = town.quests || {};
    link.querySelector("[data-quests-count]").textContent = active ? ` (${active})` : "";
    link.classList.toggle("town-quests-ready", ready > 0);
    menuButton.classList.toggle("town-hud-alert", ready > 0); // so the menu says something's waiting, shut or not
    link.title = ready ? `${ready} ready to finish` : active ? `${active} under way` : "Your quest log";
    link.setAttribute("aria-label", `Quests${active ? `: ${active} under way` : ""}${ready ? `, ${ready} ready to finish` : ""}`);
  }

  let toastTimer;
  function say(text) {
    if (!text) return;
    toast.textContent = text;
    toast.classList.add("town-toast-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("town-toast-on"), 4200);
  }

  // Spending the time: free to look around until the player talks to someone, gives a gift or duels; then the map
  // gives way to passing time (weiss.world.engaged). With nobody out anywhere, time can pass anyway.
  const thisTime = () => ["this morning", "this afternoon", "this evening", "tonight"][town.time]; // as weiss.world.this_time
  function paintTime() {
    if (town.engaged && !map.hidden) closeMap(false);
    mapButton.hidden = town.choose; // while choosing, the map is already open
    mapButton.disabled = Boolean(town.engaged); // spent here: the map says why it's shut, rather than vanishing
    $("[data-map-hint]").hidden = !town.engaged;
    // Time has just passed: where now? The map opens under the passage's cover, so it's there when the new time of day
    // is shown. It has to be answered (staying is a choice); in staff test mode it can be closed, which is staying.
    if (town.choose && (map.hidden || (town.choose_required && !mapRequired))) openMap(town.choose_required);
    else if (!town.choose && mapRequired) closeMap(false);
    const staffWait = $("[data-staff-wait]");
    const testToggle = $("[data-test-mode]");
    testToggle.hidden = !town.staff;
    testToggle.setAttribute("aria-pressed", String(Boolean(town.test_mode)));
    testToggle.textContent = town.test_mode ? "Test mode: on" : "Test mode";
    staffWait.hidden = !town.test_mode;
    $("[data-jump]").hidden = !town.test_mode;
    staffWait.disabled = busy || Boolean(town.duel);
    // Passing time sits top right once the time's spent here (committed); the menu always has it, saying why not if it can't.
    const next = town.next_time.toLowerCase();
    waitButton.hidden = !town.engaged;
    waitButton.textContent = `Pass time: ${next}`;
    waitButton.title = town.duel ? "You're in a duel: finish it first." : `You've spent ${thisTime()} here. Pass time to go somewhere else.`;
    waitButton.disabled = busy || Boolean(town.duel);
    menuWait.querySelector("[data-menu-wait-hint]").textContent = town.can_wait ? `to ${next}` : town.wait_why;
    menuWait.disabled = busy || Boolean(town.duel);
  }

  // Time passing, over the stage: the sky turns and the sun (or moon) moves on to the new time of day, then the place
  // as it is now. `change` redraws underneath while it's covered. A click or key skips it; reduced motion just fades.
  const passageEl = $("[data-passage]");
  let skipPassage = null;
  function passageWords(when, note) {
    passageEl.querySelector("[data-passage-note]").textContent = note;
    passageEl.querySelector("[data-passage-when]").textContent = when.label;
  }
  function passage(from, to, note, change = () => {}) {
    return new Promise((resolve) => {
      const timers = [];
      const at = (ms, fn) => timers.push(setTimeout(fn, ms));
      let changed = false;
      const doChange = () => { if (!changed) { changed = true; change(); } };
      const newDay = to.day !== from.day;
      const end = () => {
        timers.forEach(clearTimeout);
        skipPassage = null;
        doChange();
        passageEl.dataset.time = to.time;
        passageWords(to, newDay ? "A new day" : note);
        passageEl.classList.remove("is-on");
        setTimeout(() => {
          passageEl.hidden = true;
          if (town.choose) $("[data-places] .town-place-here, [data-places] button:not(:disabled)")?.focus({ preventScroll: true });
          resolve();
        }, reduced ? 0 : 450);
      };
      skipPassage = end;
      passageEl.hidden = false;
      passageEl.classList.remove("orb-out");
      passageEl.dataset.time = from.time;
      passageWords(from, note);
      if (reduced) {
        passageEl.classList.add("is-on");
        doChange();
        passageEl.dataset.time = to.time;
        passageWords(to, newDay ? "A new day" : note);
        at(900, end);
        return;
      }
      requestAnimationFrame(() => passageEl.classList.add("is-on"));
      if (to.time < from.time || to.time === 3) {
        // Into the night, or night into morning: the sun (or moon) fades out, and the other fades in where it belongs.
        at(450, () => passageEl.classList.add("orb-out"));
        at(800, () => { passageEl.dataset.time = to.time; });
        at(870, () => passageEl.classList.remove("orb-out"));
      } else {
        at(450, () => { passageEl.dataset.time = to.time; }); // the sun moves along its arc
      }
      at(850, () => { doChange(); passageWords(to, newDay ? "A new day" : note); }); // the place and the words move on together
      at(2300, end);
    });
  }
  const nowWhen = () => ({ time: town.time, label: `${town.date}, ${town.time_name.toLowerCase()}`, day: town.day });

  // What's on now, for the passage of time to name as the new time of day comes in: "🏆 The weekly tournament".
  const eventsNow = () => ((town.events && town.events.today) || []).filter((event) => event.now).map((event) => `${event.icon} ${event.name}`).join(" · ");

  // Today's events (weiss.world_events), in a line above the stage, with the notice board for the rest of the week.
  function paintEvents() {
    const line = $("[data-events]");
    const today = (town.events && town.events.today) || [];
    line.hidden = !today.length;
    if (!today.length) return;
    const words = today.map((event) => `${event.icon} ${event.name}${event.now ? "" : ` (${event.when})`}${event.place ? ` at the ${event.place}` : ""}`);
    line.replaceChildren(`Today: ${words.join(" · ")}.`,
      Object.assign(document.createElement("a"), { href: town.events.url, textContent: "Notice board" }));
  }

  // A soft fade over a change (none for anyone who's asked for less motion).
  function fade(change) {
    if (reduced) return Promise.resolve(change());
    stage.classList.add("town-fading");
    return new Promise((resolve) => setTimeout(() => {
      change();
      stage.classList.remove("town-fading");
      resolve();
    }, 260));
  }

  // ---- Moves ----

  async function post(url, fields) {
    if (busy) return null;
    busy = true;
    waitButton.disabled = true;
    try {
      const body = new URLSearchParams({ ...fields, version: town.version });
      const response = await fetch(url, { method: "POST", headers: { "X-CSRFToken": csrf }, body });
      const data = await response.json().catch(() => null);
      if (!data) throw new Error("bad answer");
      const wasEngaged = town.engaged;
      if (data.town) town = data.town;
      if (!wasEngaged && town.engaged && !data.go && town.place) {
        say(`You're spending ${thisTime()} at the ${town.place.name}. When you're done here, pass time.`);
      }
      if (data.error) {
        paint();
        say(data.error);
        return null;
      }
      return data;
    } catch {
      say("That didn't go through. Check your connection and try again.");
      return null;
    } finally {
      busy = false;
      paintTime();
    }
  }

  async function go(key) {
    const staying = town.place && key === town.place.key;
    const data = await post(root.dataset.travelUrl, { place: key });
    if (!data) return;
    if (playSceneNow()) return;
    mapRequired = false;
    closeMap(false);
    closeTalk(false);
    if (staying) paint();
    else await fade(paint);
    say(data.said);
  }

  async function wait(staff = false) {
    if (!staff && !town.can_wait) return say(town.wait_why);
    closeTalk(false);
    const before = new Set(town.people.map((p) => p.name));
    const from = nowWhen();
    const data = await post(root.dataset.waitUrl, staff ? { staff: "1" } : {});
    if (!data) return;
    await passage(from, nowWhen(), eventsNow() || "Time passes…", paint);
    const after = new Set(town.people.map((p) => p.name));
    const went = [...before].filter((n) => !after.has(n));
    const came = [...after].filter((n) => !before.has(n));
    say([data.said, went.length ? `${went.join(", ")} left.` : "", came.length ? `${came.join(", ")} arrived.` : ""].filter(Boolean).join(" "));
  }

  // ---- Talking ----
  // Talk and gifts are played from what the server says happened (weiss.world.talk / give / answer): lines, points,
  // coins and gifts, then what it's waiting for (a choice, a duel on offer) or nothing (back to the menu).

  const nameEl = $("[data-name]");
  const relationEl = $("[data-relation]");
  let goScene = null; // a rank-up's full scene, gone to once the talk's done

  function lines(list, then) {
    menu.replaceChildren();
    let i = 0;
    const show = () => {
      const text = list[i];
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
      button.className = `town-option ${extra.quiet ? "town-option-quiet" : ""} ${extra.quest ? "town-option-quest" : ""} ${extra.danger ? "town-option-danger" : ""}`;
      button.textContent = label;
      if (extra.title) button.title = extra.title;
      button.disabled = Boolean(extra.disabled);
      button.dataset.tutorial = extra.tut || tutLabel(label) || (extra.quiet ? "back" : "other");
      button.addEventListener("click", act);
      menu.append(button);
    }
    renderTutorial();
    menu.querySelector("button:not(:disabled)")?.focus({ preventScroll: true });
  }

  function note(text, link) {
    const why = document.createElement("p");
    why.className = "small town-why";
    why.textContent = `${text} `;
    if (link) {
      const a = document.createElement("a");
      a.href = link.href;
      a.textContent = link.text;
      if (link.title) Object.assign(a.dataset, { sheetOpen: "", title: link.title }); // opens its panel, not its page
      why.append(a);
    }
    menu.append(why);
  }

  // Friendship: hearts for the rank, its name, and the points to the next.
  function showRelation(relation) {
    if (!relation) return;
    relationEl.hidden = false;
    relationEl.replaceChildren();
    const hearts = document.createElement("span");
    hearts.className = "town-hearts";
    hearts.setAttribute("aria-hidden", "true");
    hearts.textContent = "♥".repeat(relation.rank) + "♡".repeat(Math.max(relation.ranks - 1 - relation.rank, 0));
    const words = document.createElement("span");
    words.textContent = ` ${relation.name}`;
    const points = document.createElement("span");
    points.className = "muted";
    points.textContent = relation.next === null ? ` · ${relation.points} ♥` : ` · ${relation.points}/${relation.next} ♥`;
    relationEl.append(hearts, words, points);
    const next = relation.next_rewards && relation.next_rewards.length ? ` Next rank: ${relation.next_rewards.join(", ")}.` : "";
    relationEl.title = relation.next === null ? "The closest you can be." : `${relation.next - relation.points} more to the next rank.${next}`;
    const gate = relation.gate;
    if (gate && (gate.ready || gate.status === "failed")) {
      // Points enough, but the next rank waits on a quest (or a choice closed it for good): say so instead of the points.
      const why = {
        failed: "closed for good",
        offered: "they have a quest for you",
        active: `quest: ${gate.title}`,
        settling: `finish “${gate.title}”`,
      }[gate.status] || `waits on a quest`;
      points.textContent = ` · ${why}`;
      relationEl.title = gate.status === "failed"
        ? "A choice you made closed this friendship's next rank, in this save."
        : `The next rank waits on “${gate.title}”.${next}`;
    }
  }

  function floatPoints(n) {
    const chosen = people.querySelector(`[data-cpu="${talking?.id}"]`);
    if (!chosen) return;
    const float = document.createElement("span");
    float.className = `town-float ${n < 0 ? "town-float-down" : ""}`;
    float.textContent = `${n > 0 ? "+" : ""}${n} ♥`;
    chosen.append(float);
    setTimeout(() => float.remove(), 1400);
  }

  // Their picture for a mood: pleased and dismayed are their uploaded "player lost" and "player won" screens.
  function theirMood(mood) {
    const img = people.querySelector(`[data-cpu="${talking?.id}"] img.town-picture`);
    const pics = talking?.portraits;
    if (img && pics && pics.kind !== "none") img.src = pics[mood] || pics.main;
  }

  function speaker(who) {
    nameEl.textContent = who === "them" ? talking.name : who === "player" ? root.dataset.player || "You" : "";
    nameEl.hidden = !nameEl.textContent;
    nameEl.classList.toggle("vn-name-player", who === "player");
  }

  function meet(person) {
    if (talking) return;
    talking = person;
    applyTalkFocus();
    announce();
    box.hidden = false;
    speaker("them");
    showRelation(person.relation);
    const hello = person.hello || "Hm? Oh, hello.";
    lines([hello], choices);
  }

  // Keeps `talking` up to date with the town as the server last said it.
  function refreshTalking() {
    if (talking) talking = town.people.find((p) => p.id === talking.id) || talking;
  }

  function choices() {
    if (!talking) return;
    clearPanel();
    refreshTalking();
    const person = talking;
    speaker("them");
    theirMood("main");
    const stake = person.offer || person.stake;
    textEl.textContent = stake
      ? `${person.name} plays for stakes: ${stake} coins to enter, ${stake * 2} back if you win.`
      : "What would you like to do?";
    const why = town.duel ? "You're in a duel already." : !town.deck_ready ? "Your equipped deck isn't ready." : "";
    const relation = person.relation || {};
    const held = (town.gifts || []).filter((item) => item.have > 0);
    // A staff token isn't limited to one gift a day, so it stays available after the day's gift.
    const hasToken = held.some((item) => item.staff);
    const noGift = relation.gifted && !hasToken ? "You've given them something today." : !held.length ? "Buy gifts at the card shop." : "";
    const q = person.quests || {};
    const list = [
      // Quests first: they're what's new.
      ...(q.offers || []).map((item) => [`❗ ${person.name} wants to ask you something`, () => questAct("offer", item.quest), { quest: true }]),
      ...(q.settles || []).map((item) => [`★ Finish “${item.title}”`, () => questAct("settle", item.quest), { quest: true }]),
      ...(q.talks || []).map((item) => [`★ About “${item.title}”`, () => questAct("talk", item.quest, { objective: item.objective }), { quest: true }]),
      ...(q.hands || []).map((item) => {
        const short = item.have < item.copies ? `You have ${item.have} of the ${item.copies} needed.` : "";
        return [`★ Hand over ${item.card}${item.copies > 1 ? ` ×${item.copies}` : ""}`, () => confirmHand(item),
          { quest: true, disabled: Boolean(short), title: short || item.title }];
      }),
      ["Talk", talk, person.talked_now
        ? { disabled: true, title: `You've talked ${thisTime()} already.` }
        : { title: relation.talked ? "" : "The day's first talk brings them closer." }],
      ["Give a gift", giftMenu, { disabled: Boolean(noGift), title: noGift }],
      [person.tournament ? `🏆 Duel: tournament ${person.tournament}` : "Duel", () => duel(false), { disabled: Boolean(why), title: why }],
    ];
    if (stake && !person.tournament) {
      const short = town.money < stake ? `You have ${town.money} coins.` : "";
      list.push([`High-stakes duel (${stake} coins)`, () => duel(true), { disabled: Boolean(why || short), title: why || short }]);
    }
    if (town.staff && town.test_mode) {  // staff testing: a rank at once, no time spent
      const top = relation.rank + 1 >= relation.ranks;
      const hint = top ? "Already at the top rank."
        : relation.gate ? "Testing: stops one point short of the quest, then the next press offers it."
        : "Testing: a rank at once.";
      list.push(["⬆ Raise a rank (staff)", raiseLevel, { disabled: top, title: hint }]);
    }
    list.push(["Leave", leave, { quiet: true }]);
    options(list);
    if (why && !(town.tutorial && town.tutorial.step !== "deck")) note(why, !town.deck_ready && !town.duel ? { href: root.dataset.decksUrl, text: "Your decks", title: "Your deck" } : null);
  }

  // ---- Quests in the talk box (weiss.world.quest_act): offers, talking them through, handing cards over, endings ----

  async function questAct(act, quest, extra = {}) {
    menu.replaceChildren();
    clearPanel();
    const data = await post(root.dataset.questUrl, { cpu: talking.id, act, quest, ...extra });
    if (data && talking) play(data.talk);
    else if (talking) choices();
  }

  // A panel under the words, for an offer or the endings: built from text nodes only (quest text is staff-written).
  const panelEl = $("[data-quest-panel]");
  function clearPanel() {
    panelEl.replaceChildren();
    panelEl.hidden = true;
  }
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  // A card an objective asks for, with what says how to get it (quests.card_facts, as the quest log shows it).
  function cardFacts(card) {
    const box = el("div", "quest-card-facts");
    const link = el("a", "quest-card-picture");
    link.href = card.url;
    const img = document.createElement("img");
    Object.assign(img, { src: card.image, alt: "", width: 54, height: 75, loading: "lazy" });
    link.append(img);
    const text = el("div", "quest-card-text");
    const name = el("p", "small");
    name.append(el("strong", "", card.name), " ", el("span", "muted", card.serial));
    const stats = el("dl", "quest-card-stats small");
    for (const [label, value] of [["Colour", card.color], ["Level", card.level], ["Cost", card.cost], ["Rarity", card.rarity], ["Type", card.type], ["Set", card.set]]) {
      if (value === null || value === undefined || value === "") continue;
      const row = el("div");
      row.append(el("dt", "", label), el("dd", "", String(value)));
      stats.append(row);
    }
    text.append(name, stats);
    if (card.set) text.append(el("p", "small muted", `Any printing of it counts. Packs of ${card.set} are where to look.`));
    box.append(link, text);
    return box;
  }

  // Objectives as {text, card}: a card's facts sit under its line.
  function objectiveItems(items, className = "") {
    const ul = el("ul", className);
    for (const item of items) {
      const li = el("li", "", item.text);
      if (item.card) li.append(cardFacts(item.card));
      ul.append(li);
    }
    return ul;
  }

  function bullets(items, className = "") {
    const ul = el("ul", className);
    for (const item of items) ul.append(el("li", "", item));
    return ul;
  }

  // A decision (an offer, the endings, a confirmation) is never left below the fold: the box's buttons come into view.
  function reveal() {
    requestAnimationFrame(() => box.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" }));
  }

  // Handing a card over can't be undone: say so, and what it means for the decks, before it's done.
  function confirmHand(item) {
    speaker("");
    textEl.textContent = `Give ${item.card}${item.copies > 1 ? ` ×${item.copies}` : ""} to ${talking.name}? It leaves your cards for good: `
      + `you'll have ${item.have - item.copies} left, and any deck with more than that loses the rest.`;
    options([
      [`Hand it over`, () => questAct("hand", item.quest, { objective: item.objective })],
      ["Not yet", choices, { quiet: true }],
    ]);
    reveal();
  }

  function offerPanel(offer) {
    speaker("");
    textEl.textContent = `Quest: ${offer.title}`;
    clearPanel();
    panelEl.append(el("p", "", offer.about));
    const first = el("p", "town-quest-first");
    first.append(el("strong", "", offer.stages > 1 ? `First, of ${offer.stages} steps: ` : "To do: "), offer.first);
    panelEl.append(first, objectiveItems(offer.objectives, "town-quest-objectives"));
    if (offer.rewards.length) panelEl.append(el("p", "small", `Reward: ${offer.rewards.join(" · ")}`));
    if (offer.gate) panelEl.append(el("p", "small muted", `Finishing it unlocks ${offer.gate} with ${offer.giver}.`));
    if (offer.closes) {
      panelEl.append(el("p", "small town-quest-warn", "It ends with a choice, and some endings close other quests for good. "
        + "Taking it closes nothing: you'll see exactly what each ending closes before you choose."));
    } else if (offer.choice) {
      panelEl.append(el("p", "small muted", "It ends with a choice."));
    }
    panelEl.hidden = false;
    options([
      ["Take the quest", () => questAct("accept", offer.quest)],
      ["Not now", () => { clearPanel(); choices(); }, { quiet: true }],
    ]);
    reveal();
  }

  function endingsPanel(found) {
    speaker("");
    textEl.textContent = found.endings.length > 1 ? `How does “${found.title}” end?` : `Finish “${found.title}”?`;
    clearPanel();
    const list = el("ul", "town-endings");
    for (const ending of found.endings) {
      const item = el("li", "town-ending");
      item.append(el("p", "town-ending-title", ending.title));
      if (ending.about) item.append(el("p", "small", ending.about));
      if (ending.rewards.length) item.append(el("p", "small muted", `Reward: ${ending.rewards.join(" · ")}`));
      const closes = closeWords(ending.fallout);
      if (closes.length) {
        item.append(el("p", "small town-quest-warn", "This closes, for good:"), bullets(closes, "town-quest-closes"));
      } else {
        item.append(el("p", "small muted", "It closes nothing else."));
      }
      if (ending.missing.length) item.append(el("p", "small muted", `First: ${ending.missing.join("; ")}.`));
      list.append(item);
    }
    panelEl.append(list);
    if (found.elsewhere.length) panelEl.append(el("p", "small muted", `Other endings are with ${found.elsewhere.join(", ")}.`));
    panelEl.hidden = false;
    options([
      ...found.endings.map((ending) => [ending.title, () => pickEnding(found, ending),
        { disabled: ending.missing.length > 0, title: ending.missing.length ? `First: ${ending.missing.join("; ")}` : "" }]),
      ["Not yet", () => { clearPanel(); choices(); }, { quiet: true }],
    ]);
    reveal();
  }

  function closeWords(fallout) {
    return [
      ...fallout.leave.map((name) => `${name} leaves town, and you won't see them again in this save.`),
      ...fallout.quests.map((q) => `“${q.title}”${q.giver ? ` (${q.giver})` : ""}: ${q.why}${q.held ? ` ${q.giver} stays at ${q.held} with you.` : ""}`),
    ];
  }

  // An ending that closes anything is asked about once more, saying what, since it can't be undone.
  function pickEnding(found, ending) {
    const closes = closeWords(ending.fallout);
    if (!closes.length) return questAct("choose", found.quest, { ending: ending.key });
    textEl.textContent = `“${ending.title}”: this can't be undone.`;
    clearPanel();
    panelEl.append(el("p", "small town-quest-warn", "Choosing it closes, for good:"), bullets(closes, "town-quest-closes"),
      el("p", "small muted", "Your other saves aren't touched."));
    panelEl.hidden = false;
    options([
      [`Choose “${ending.title}”`, () => questAct("choose", found.quest, { ending: ending.key, confirm: "1" }), { danger: true }],
      ["Go back", () => endingsPanel(found), { quiet: true }],
    ]);
    menu.querySelector(".town-option-quiet")?.focus({ preventScroll: true }); // the safe choice has the focus
    reveal();
  }

  async function talk() {
    const data = await post(root.dataset.talkUrl, { cpu: talking.id });
    if (data && talking) play(data.talk);
    else if (talking) choices();
  }

  function giftMenu() {
    speaker("player");
    textEl.textContent = "What will you give them?";
    const held = (town.gifts || []).filter((item) => item.have > 0);
    options([
      ...held.map((item) => [`${item.icon} ${item.name}${item.have > 1 ? ` (${item.have})` : ""}`, () => give(item), { tut: "gift-item" }]),
      ["Back", choices, { quiet: true }],
    ]);
  }

  async function give(item) {
    menu.replaceChildren();
    const data = await post(root.dataset.giveUrl, { cpu: talking.id, gift: item.key });
    if (data && talking) play(data.talk);
    else if (talking) choices();
  }

  // Staff testing: the same playing-out as a gift that raised them (weiss.world.level_up).
  async function raiseLevel() {
    menu.replaceChildren();
    const data = await post(root.dataset.levelUrl, { cpu: talking.id });
    if (data && talking) play(data.talk);
    else if (talking) choices();
  }

  async function answer(i) {
    menu.replaceChildren();
    const data = await post(root.dataset.answerUrl, { cpu: talking.id, option: i });
    if (data && talking) play(data.talk);
    else if (talking) choices();
  }

  // Plays what happened, one event after another, then what it's waiting for.
  function play(said) {
    refreshTalking();
    const queue = [...said.events];
    const next = () => {
      if (!talking) return;
      const event = queue.shift();
      if (!event) return waitingFor(said.waiting);
      if (event.say !== undefined) {
        speaker(event.who);
        if (event.who === "them") theirMood(event.mood || "main");
        return lines([event.say], next);
      }
      if (event.gave) {
        theirMood({ loved: "pleased", liked: "pleased", disliked: "dismayed" }[event.reaction] || "main");
        speaker("player");
        return lines([`You give ${talking.name} the ${event.icon} ${event.gave}.`], next);
      }
      if (event.points !== undefined) {
        floatPoints(event.points);
        showRelation(event.relation);
        if (event.rank_up) {
          speaker("");
          return lines([`♥ You and ${talking.name} are now: ${event.rank_up}.`], next);
        }
        return next();
      }
      if (event.reward) {
        speaker("");
        $("[data-coins]").textContent = `${town.money.toLocaleString()} coins`;
        return lines([`★ ${event.reward}`], () => {
          // Packs given together are revealed together: offer to see them once, after the last.
          if (!event.link || queue.some((later) => later.link)) return next();
          options([["See the cards", () => { window.location.href = event.link; }], ["Carry on", next, { quiet: true }]]);
        });
      }
      if (event.quest) {
        speaker("");
        paintQuests();
        return lines([`★ ${event.quest}`], next);
      }
      if (event.rank_reached) {
        speaker("");
        if (event.relation && event.who === talking.name) showRelation(event.relation);
        return lines([`♥ You and ${event.who} are now: ${event.rank_reached}.`], next);
      }
      if (event.money) say(`+${event.money.toLocaleString()} coins.`);
      if (event.gift) say(`${talking.name} gave you ${event.icon} ${event.gift}.`);
      if (event.scene) goScene = event.scene;
      return next();
    };
    $("[data-coins]").textContent = `${town.money.toLocaleString()} coins`;
    showRelation(said.relation);
    next();
  }

  function waitingFor(waiting) {
    if (goScene) {
      window.location.href = goScene;
      return;
    }
    if (!waiting) return choices();
    if (waiting.quest_offer) return offerPanel(waiting.quest_offer);
    if (waiting.endings) return endingsPanel(waiting.endings);
    if (waiting.choice !== undefined) {
      if (waiting.prompt) {
        speaker("them");
        textEl.textContent = waiting.prompt;
      }
      return options(waiting.options.map((text, i) => [text, () => answer(i)]));
    }
    // A duel offered in talk ("fight", "fight stake 500").
    refreshTalking();
    const why = town.duel ? "You're in a duel already." : !town.deck_ready ? "Your equipped deck isn't ready." : "";
    const stake = waiting.fight;
    const short = stake && town.money < stake ? `You have ${town.money} coins.` : "";
    options([
      stake ? [`Duel for ${stake} coins`, () => duel(true), { disabled: Boolean(why || short), title: why || short }]
        : ["Duel", () => duel(false), { disabled: Boolean(why), title: why }],
      ["Not now", choices, { quiet: true }],
    ]);
    // The deck's note waits for the deck step (the guide handles it there); the note's own link is the same.
    if (why && !(town.tutorial && town.tutorial.step !== "deck")) note(why, !town.deck_ready && !town.duel ? { href: root.dataset.decksUrl, text: "Your decks", title: "Your deck" } : null);
  }

  async function duel(stakes) {
    const person = talking;
    speaker("them");
    theirMood("main");
    const intro = person.intro || "Let's see what you've got.";
    lines([intro], async () => {
      const data = await post(root.dataset.duelUrl, { cpu: person.id, stakes: stakes ? "1" : "0" });
      if (data && data.go) {
        window.location.href = data.go;
        return;
      }
      if (talking) choices();
    });
  }

  function leave() {
    speaker("them");
    lines([talking.bye || "See you around."], () => closeTalk());
  }

  function closeTalk(refocus = true) {
    const person = talking;
    talking = null;
    advance = null;
    clearPanel();
    box.hidden = true;
    relationEl.hidden = true;
    applyTalkFocus();
    announce();
    if (person && refocus) people.querySelector(`[data-cpu="${person.id}"]`)?.focus({ preventScroll: true });
  }

  // ---- The tutorial (docs/world-tutorial-plan.md): the first chapter's guide walks the player through the town. The
  // server keeps the step and says what to press (town.tutorial); the page plays the guide's lines, spotlights the
  // target, shows the goal, and holds everything else until the step is done. ----
  const tutGoal = $("[data-goal]");
  const tutGoalText = $("[data-goal-text]");
  const tutHint = $("[data-tutorial-hint]");
  const tutSkip = $("[data-tutorial-skip]");
  let tutPlaying = false; // the guide's lines are on, and their "said" hasn't been sent yet
  const tutVeil = $("[data-tutorial-veil]");
  let tutTarget = null; // the spotlit element, and whether its position was changed to show the ring
  let tutRepositioned = false;
  let tutLifted = []; // the containers raised above the veil with the target: [element, its old z-index]

  // The steps that open the talk menu: after the guide's lines, the menu is the thing to press.
  const TALK_STEPS = ["talk", "gift", "duel"];

  // A control that's outside the step is disabled, not hidden. Its title says what the guide's waiting for.
  function tutGate(id) {
    const tut = town.tutorial;
    if (!tut || !id || id === "back") return { blocked: false };
    if (tut.highlight.includes(id)) return { blocked: false };
    return { blocked: true, title: `Not yet: ${tut.title}` };
  }

  // Is an element on screen (laid out, and not inside a hidden panel)?
  const onScreen = (el) => Boolean(el) && el.getClientRects().length > 0;

  // The first highlight that's on screen. The Menu button is the way in to the things kept in the menu (the quest
  // log, the decks, passing time), so when one of those is the step's, the menu's button is spotlit until it's open.
  function tutTargetEl() {
    const tut = town.tutorial;
    // While a panel is open, its button (the counter, the map) is behind it: the spotlight goes to what's inside.
    const behind = [!shop.hidden && "shop", !map.hidden && "map"].filter(Boolean);
    for (const id of tut.highlight) {
      if (behind.includes(id)) continue;
      const el = root.querySelector(`[data-tutorial="${id}"]`);
      if (onScreen(el)) return el;
    }
    return tut.highlight.length ? root.querySelector("[data-open-menu]") : null;
  }

  // Which people can be clicked: in arrive, the candidates (clicking one asks them to show you round); later, the guide.
  function tutPersonAllowed(person) {
    const tut = town.tutorial;
    if (!tut) return true;
    if (tut.step === "arrive") return tut.candidates.includes(person.id);
    return Boolean(tut.guide) && tut.guide.id === person.id;
  }

  // Marks the spotlit element: it's raised and ringed, and the rest of the stage is dimmed behind it.
  function spotlight(el) {
    if (tutTarget === el) return;
    if (tutTarget) {
      tutTarget.classList.remove("town-tut-target");
      if (tutRepositioned) tutTarget.style.position = "";
    }
    for (const [box, z] of tutLifted) box.style.zIndex = z;
    tutLifted = [];
    tutTarget = el;
    tutRepositioned = false;
    tutVeil.hidden = !el;
    if (!el) return;
    if (getComputedStyle(el).position === "static") {
      el.style.position = "relative";
      tutRepositioned = true;
    }
    // The veil sits over the stage, so the target and every panel it's in (the talk box, the HUD, the map) are raised
    // above it, by their stacking order, to stay bright.
    for (let node = el; node && node !== stage; node = node.parentElement) {
      const cs = getComputedStyle(node);
      if (cs.position !== "static" && cs.zIndex !== "auto") {
        tutLifted.push([node, node.style.zIndex]);
        node.style.zIndex = "36";
      }
    }
    // The people and the talk box stay bright too: the one being talked to, and the candidates, are the people.
    for (const panel of [people, box]) {
      if (!panel.hidden && !tutLifted.some(([node]) => node === panel)) {
        tutLifted.push([panel, panel.style.zIndex]);
        panel.style.zIndex = "36";
      }
    }
    el.classList.add("town-tut-target");
  }

  // Puts the hint by the spotlit element: above it (or below, when there's no room above), kept inside the stage. A
  // target in the talk box puts the hint beside the speaker's name, so the name stays visible.
  function placeHint(el) {
    if (!el) return;
    const sb = stage.getBoundingClientRect();
    const eb = el.getBoundingClientRect();
    const hw = tutHint.offsetWidth;
    const hh = tutHint.offsetHeight;
    const inBox = el.closest("[data-box]");
    const nameBox = inBox && !nameEl.hidden ? nameEl.getBoundingClientRect() : null;
    tutHint.classList.toggle("town-tut-hint-left", Boolean(nameBox));
    tutHint.classList.remove("town-tut-hint-below");
    let left;
    let top;
    if (nameBox) {
      left = Math.min(nameBox.right - sb.left + 12, sb.width - hw - 8);
      top = inBox.getBoundingClientRect().top - sb.top - 8;
    } else if (!box.hidden) {
      // A target with the talk box open (the candidates, in arrive): the hint sits just above the box, out of the way.
      const center = eb.left + eb.width / 2 - sb.left;
      left = Math.max(hw / 2 + 8, Math.min(sb.width - hw / 2 - 8, center));
      top = box.getBoundingClientRect().top - sb.top - 8;
    } else {
      const center = eb.left + eb.width / 2 - sb.left;
      left = Math.max(hw / 2 + 8, Math.min(sb.width - hw / 2 - 8, center));
      if (eb.top - sb.top - 8 - hh >= 8) {
        top = eb.top - sb.top - 8;
      } else {
        top = eb.bottom - sb.top + 8;
        tutHint.classList.add("town-tut-hint-below");
      }
    }
    tutHint.style.left = `${Math.max(8, left)}px`;
    tutHint.style.top = `${top}px`;
  }

  function renderTutorial() {
    const tut = town.tutorial;
    root.classList.toggle("town-tutorial-on", Boolean(tut));
    tutGoal.hidden = !tut;
    tutSkip.hidden = !(tut && town.staff && town.test_mode);
    const help = root.querySelector(".town-help"); // the free-play paragraph under the stage
    if (help) help.hidden = Boolean(tut);
    $("[data-deck-notice]").hidden = town.deck_ready || Boolean(tut && tut.step !== "deck");
    if (!tut) {
      spotlight(null);
      tutHint.hidden = true;
      root.querySelectorAll(".town-tut-blocked").forEach((el) => {
        el.classList.remove("town-tut-blocked");
        el.removeAttribute("aria-disabled");
        if (el.dataset.tutDisabled) el.disabled = false;
        delete el.dataset.tutDisabled;
        el.removeAttribute("title");
      });
      return;
    }
    tutGoalText.textContent = tut.title;
    // Everything in the step's own list stays live; the rest are held.
    for (const el of root.querySelectorAll("[data-tutorial]")) {
      let blocked = tutGate(el.dataset.tutorial).blocked;
      if (el.dataset.cpu !== undefined) {
        const person = town.people.find((p) => p.id === Number(el.dataset.cpu));
        blocked = !person || !tutPersonAllowed(person);
      }
      el.classList.toggle("town-tut-blocked", blocked);
      if (blocked) {
        if (el.tagName === "BUTTON" && !el.disabled) el.dataset.tutDisabled = "1";
        if (el.tagName === "BUTTON") el.disabled = true;
        el.setAttribute("aria-disabled", "true");
        el.title = `Not yet: ${tut.title}`;
      } else {
        if (el.dataset.tutDisabled) el.disabled = false;
        delete el.dataset.tutDisabled;
        el.removeAttribute("aria-disabled");
        el.removeAttribute("title");
      }
    }
    // Once the guide's lines are done: the talk steps open the guide's talk menu; the others close the talk, so the
    // map, shop or quest button can be reached.
    if (!tutPlaying && !tut.lines.length) {
      if (TALK_STEPS.includes(tut.step) && tut.guide && !talking) openGuideMenu();
      // The guide's talk is open (their lines set it) but its menu isn't: open it. A menu already showing a talk
      // option or a gift is left as it is.
      else if (TALK_STEPS.includes(tut.step) && talking && !menu.querySelector("[data-tutorial='talk'], [data-tutorial='gift'], [data-tutorial='gift-item'], [data-tutorial='duel']")) choices();
      else if (!TALK_STEPS.includes(tut.step) && talking && tut.step !== "arrive") closeTalk(false);
    }
    // While the guide is still talking, nothing is spotlit: the step's control isn't on yet.
    const target = tutPlaying || tut.lines.length ? null : tutTargetEl();
    spotlight(target);
    tutHint.hidden = !tut.hint || Boolean(tutPlaying);
    tutHint.textContent = tut.hint || "";
    if (target && !tutHint.hidden) placeHint(target);
    // Focus moves to the target, once the guide has finished talking, so the keyboard lands on what to press.
    if (target && !tutPlaying && typeof target.focus === "function" && !tut.lines.length) {
      target.focus({ preventScroll: true });
    }
    tutSkip.disabled = busy;
    playTutorialLines();
  }

  // Plays the guide's lines in the talk box (the guide as "them", the player as "player", narration with no name),
  // then sends "said": the server marks them and moves on if the step's already done.
  function playTutorialLines() {
    const tut = town.tutorial;
    if (!tut || !tut.lines.length || tutPlaying) return;
    tutPlaying = true;
    const guide = tut.guide ? town.people.find((p) => p.id === tut.guide.id) || tut.guide : null;
    const list = tut.lines.slice();
    let i = 0;
    const next = async () => {
      if (i >= list.length) {
        tutPlaying = false;
        const data = await post(root.dataset.tutorialUrl, { act: "said" });
        if (data) {
          paint();
          return;
        }
        renderTutorial();
        return;
      }
      const line = list[i++];
      if (guide) talking = guide;
      if (talking) applyTalkFocus();
      box.hidden = false;
      nameEl.textContent = line.who === "them" && guide ? guide.name : line.who === "player" ? root.dataset.player || "You" : "";
      nameEl.hidden = !nameEl.textContent;
      nameEl.classList.toggle("vn-name-player", line.who === "player");
      if (talking && line.who === "them") theirMood(line.mood || "main");
      lines([line.say], next);
    };
    next();
  }

  // Dims and rings the target, and keeps the hint and the goal in step with it when the page moves.
  window.addEventListener("resize", () => { if (town.tutorial && tutTarget) placeHint(tutTarget); });

  // Talking to the guide (in the talk steps, once their lines are done): the talk menu opens for them.
  function openGuideMenu() {
    const guide = town.people.find((p) => p.id === town.tutorial.guide?.id);
    if (!guide || talking) return;
    talking = guide;
    applyTalkFocus();
    announce();
    box.hidden = false;
    speaker("them");
    choices();
  }

  // Approaching a candidate in "arrive": they become the guide, and their answer's lines play.
  async function approach(person) {
    const data = await post(root.dataset.tutorialUrl, { act: "approach", cpu: person.id });
    if (data) paint();
  }

  async function skipTutorial() {
    const data = await post(root.dataset.tutorialUrl, { act: "skip" });
    if (data) paint();
  }
  tutSkip.addEventListener("click", skipTutorial);

  // Which talk-menu option a label is, for the tutorial's highlights ("Talk", "Give a gift", "Duel").
  function tutLabel(label) {
    if (label.startsWith("Talk")) return "talk";
    if (label.startsWith("Give a gift")) return "gift";
    if (label.startsWith("Duel")) return "duel";
    return "";
  }

  // ---- The map ----

  function listPlaces() {
    const list = $("[data-places]");
    list.replaceChildren();
    for (const place of town.places) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "town-place";
      button.disabled = place.here && !town.choose; // choosing where to spend a new time of day: staying is an answer
      button.innerHTML = `<span class="town-place-art">${window.SceneBackdrops ? SceneBackdrops.draw(place.backdrop, town.time) : ""}</span>
        <span class="town-place-name"></span><span class="town-place-who small"></span>`;
      button.querySelector(".town-place-name").textContent = place.name;
      button.dataset.tutorial = `place-${place.key}`;
      if (place.events && place.events.length) {  // an event on there now (weiss.world_events.at_places)
        const mark = el("span", "town-place-event", ` ${place.events.map((event) => event.icon).join("")}`);
        mark.title = place.events.map((event) => event.name).join(", ");
        button.querySelector(".town-place-name").append(mark, el("span", "visually-hidden", `: ${mark.title} on now`));
      }
      const hereWords = town.choose ? " (stay here)" : " (you're here)";
      if (place.here) {
        const note = document.createElement("span");
        note.className = "muted small";
        note.textContent = hereWords;
        button.querySelector(".town-place-name").append(note);
        if (town.choose) button.classList.add("town-place-here");
      }
      button.querySelector(".town-place-who").append(...whoIsThere(place.who));
      button.setAttribute("aria-label", `${place.name}${place.here ? hereWords : ""}: ${place.who.length ? place.who.map((p) => p.name).join(", ") : "nobody right now"}`);
      button.addEventListener("click", () => go(place.key));
      item.append(button);
      list.append(item);
    }
    renderTutorial(); // the places and the stock are built now: the spotlight can find them
  }

  // Who's at a place, for its card on the map: their circle pictures and names, a few at most and how many more.
  const SHOWN = 4;
  function whoIsThere(who) {
    if (!who.length) {
      const none = document.createElement("span");
      none.className = "muted";
      none.textContent = "Nobody right now";
      return [none];
    }
    const items = who.slice(0, SHOWN).map((person) => {
      const item = document.createElement("span");
      item.className = "town-who";
      const face = document.createElement("span");
      face.className = "avatar town-who-face";
      face.setAttribute("aria-hidden", "true");
      if (person.avatar) {
        const img = document.createElement("img");
        img.src = person.avatar.image;
        img.alt = "";
        img.style.width = `${person.avatar.width}%`;
        img.style.left = `${person.avatar.left}%`;
        img.style.top = `${person.avatar.top}%`;
        img.addEventListener("error", () => { img.remove(); face.textContent = person.name.slice(0, 1).toUpperCase(); }, { once: true });
        face.append(img);
      } else {
        face.textContent = person.name.slice(0, 1).toUpperCase();
      }
      const name = document.createElement("span");
      name.textContent = person.name;
      item.append(face, name);
      return item;
    });
    if (who.length > SHOWN) {
      const more = document.createElement("span");
      more.className = "muted";
      more.textContent = `and ${who.length - SHOWN} more`;
      items.push(more);
    }
    return items;
  }

  // The map; `required` after time passes: where to spend the new time of day, with no closing it.
  let mapRequired = false;
  function openMap(required = false) {
    closeShop(false);
    closeTalk(false);
    mapRequired = required;
    $("[data-close-map]").hidden = required;
    const choosingNow = required || Boolean(town.choose); // time has passed (closable only in staff test mode)
    $("[data-map-title]").textContent = choosingNow ? "Where to now?" : "Where to?";
    const note = $("[data-map-note]");
    note.hidden = !choosingNow;
    note.textContent = choosingNow ? `It's ${town.weekday} ${town.time_name.toLowerCase()}. Choose where to spend it: staying here is fine too.` : "";
    listPlaces();
    map.hidden = false;
    mapButton.setAttribute("aria-expanded", "true");
    if (!skipPassage) $("[data-places] button:not(:disabled)")?.focus({ preventScroll: true });
    renderTutorial();
  }

  // Closing the map: after time passes (test mode, where it can be closed), that's staying where the player is.
  function dismissMap() {
    if (town.choose && town.place) return go(town.place.key);
    closeMap();
  }

  // A quest's visit scene (weiss.quests.arrived) plays as soon as the player's there: off to it.
  function playSceneNow() {
    if (!town.scene || !town.scene.auto) return false;
    window.location.assign(town.scene.url);
    return true;
  }

  function closeMap(refocus = true) {
    if (mapRequired && town.choose) return; // it has to be answered
    mapRequired = false;
    map.hidden = true;
    mapButton.setAttribute("aria-expanded", "false");
    if (refocus) menuButton.focus({ preventScroll: true }); // the map's button lives in the menu, which is shut
    renderTutorial();
  }

  // ---- The card shop ----

  let shopTab = "packs";
  let specialSet = null; // the set chosen for specialty packs, kept while the shop's open

  const coins = (n) => n.toLocaleString();

  // `was`: the usual price, when a sale has cut it (shown struck through, and said in full to screen readers).
  function buyButton(label, cost, onBuy, secondary = false, was = null) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = secondary ? "button-small secondary" : "button-small";
    button.textContent = `${label} · `;
    if (was && was > cost) {
      const old = el("s", "town-was", coins(was));
      old.setAttribute("aria-label", `usually ${coins(was)}`);
      button.append(old, " ");
    }
    button.append(coins(cost));
    button.disabled = town.money < cost;
    if (button.disabled) button.title = `You have ${coins(town.money)} coins.`;
    button.addEventListener("click", onBuy);
    return button;
  }

  // ---- The basket: things are added from every tab and bought at once (weiss.world.checkout), so packs open
  // together. It's kept in this tab's session storage, so leaving the shop (or reloading) doesn't lose it; the server
  // prices it again and is the one that's right.

  const basketKey = `world-basket-${root.dataset.slot}`;
  let basket = (() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(basketKey) || "[]");
      return Array.isArray(saved) ? saved : [];
    } catch {
      return [];
    }
  })();

  function keepBasket() {
    try {
      if (basket.length) sessionStorage.setItem(basketKey, JSON.stringify(basket));
      else sessionStorage.removeItem(basketKey);
    } catch { /* the basket lasts this page, then */ }
  }

  const sameLine = (a, b) => a.kind === b.kind && ["set", "special", "level", "color", "card", "gift"].every((field) => (a[field] ?? "") === (b[field] ?? ""));
  const PACK_KINDS = ["pack", "special"];
  const MAX_BASKET_PACKS = 30;

  // An "Add" button: like a buy button, but never disabled for money (the basket says if it's over).
  function addButton(label, cost, onAdd, secondary = false, was = null) {
    const button = buyButton(label, cost, onAdd, secondary, was);
    button.disabled = false;
    button.removeAttribute("title");
    button.dataset.tutorial = label === "Add 1" ? "add-pack" : "other";
    return button;
  }

  function addToBasket(line, label) {
    const packs = basket.filter((item) => PACK_KINDS.includes(item.kind)).reduce((n, item) => n + item.count, 0);
    if (PACK_KINDS.includes(line.kind) && packs + line.count > MAX_BASKET_PACKS) return say(`A basket holds ${MAX_BASKET_PACKS} packs at most.`);
    const found = basket.find((item) => sameLine(item, line));
    if (found && line.kind === "card") return say(`${label} is in your basket already: one of each a day.`);
    if (found) found.count += line.count;
    else basket.push({ ...line, label });
    keepBasket();
    paintBasket();
    if (line.kind === "card") listCards();
    say(`Added ${line.count > 1 ? `${line.count} × ` : ""}${label} to your basket.`);
  }

  function setCount(line, count) {
    if (count < 1) basket = basket.filter((item) => item !== line);
    else line.count = Math.min(count, MAX_BASKET_PACKS);
    keepBasket();
    paintBasket();
    if (line.kind === "card") listCards();
  }

  // What a line costs now, as the server works it out (weiss.world.basket_cost); null if the shop no longer has it.
  function lineCost(line) {
    const shopNow = town.shop;
    if (line.kind === "pack") {
      const set = shopNow.stock.find((entry) => entry.id === line.set);
      if (!set) return null;
      if (!set.was) return set.price * line.count;
      const cheap = set.sale_left === null || set.sale_left === undefined ? line.count : Math.min(line.count, set.sale_left);
      return set.price * cheap + shopNow.price * (line.count - cheap);
    }
    if (line.kind === "special") return shopNow.stock.some((entry) => entry.id === line.set) ? shopNow.specialty_price * line.count : null;
    if (line.kind === "card") {
      const card = shopNow.cards.find((entry) => entry.id === line.card);
      return card && !card.sold ? shopNow.card_price : null;
    }
    const item = (shopNow.gifts || []).find((entry) => entry.key === line.gift);
    return item ? item.price * line.count : null;
  }

  function basketTotal() {
    return basket.reduce((sum, line) => sum + (lineCost(line) ?? 0), 0);
  }

  function paintBasket() {
    if (!town.shop) return;
    const lines = $("[data-basket-lines]");
    lines.replaceChildren();
    for (const line of basket) {
      const cost = lineCost(line);
      const row = el("li", `town-basket-line${cost === null ? " is-gone" : ""}`);
      const name = el("span", "town-basket-name", line.label);
      if (cost === null) name.append(" ", el("span", "small muted", "(not in the shop today)"));
      row.append(name);
      if (line.kind !== "card" && cost !== null) {
        const stepper = el("span", "town-basket-stepper");
        const less = el("button", "button-small secondary", "−");
        less.type = "button";
        less.setAttribute("aria-label", `One fewer ${line.label}`);
        less.addEventListener("click", () => setCount(line, line.count - 1));
        const more = el("button", "button-small secondary", "+");
        more.type = "button";
        more.setAttribute("aria-label", `One more ${line.label}`);
        more.addEventListener("click", () => setCount(line, line.count + 1));
        stepper.append(less, el("span", "town-basket-count", `× ${line.count}`), more);
        row.append(stepper);
      }
      row.append(el("span", "town-basket-cost", cost === null ? "" : coins(cost)));
      const remove = el("button", "town-basket-remove", "×");
      remove.type = "button";
      remove.setAttribute("aria-label", `Take ${line.label} out of the basket`);
      remove.addEventListener("click", () => setCount(line, 0));
      row.append(remove);
      lines.append(row);
    }
    const total = basketTotal();
    const gone = basket.some((line) => lineCost(line) === null);
    const units = basket.reduce((n, line) => n + line.count, 0);
    $("[data-basket-count]").textContent = units ? `(${units})` : "";
    $("[data-basket-none]").hidden = Boolean(basket.length);
    $("[data-basket-empty]").hidden = !basket.length;
    $("[data-basket-foot]").hidden = !basket.length;
    const short = total > town.money;
    $("[data-basket-total]").textContent = gone
      ? "Take out what the shop doesn't have today to check out."
      : `Total ${coins(total)} coins. You have ${coins(town.money)}${short ? `: ${coins(total - town.money)} short.` : "."}`;
    const checkout = $("[data-checkout]");
    checkout.disabled = !basket.length || gone || short;
    checkout.textContent = `Check out · ${coins(total)}`;
  }

  async function checkOut() {
    const total = basketTotal();
    const items = basket.map(({ label, ...line }) => line);
    const data = await post(root.dataset.checkoutUrl, { basket: JSON.stringify(items), expected: total });
    if (!data) return; // said why (post); the basket's kept
    basket = [];
    keepBasket();
    if (data.go) {
      window.location.assign(data.go); // the packs, revealed together
      return;
    }
    listStock();
    say(data.said);
  }

  function cover(set, className) {
    const img = document.createElement("img");
    img.className = className;
    img.alt = "";
    img.loading = "lazy";
    img.addEventListener("error", () => (img.hidden = true));
    if (set.cover) img.src = set.cover;
    else img.hidden = true;
    return img;
  }

  function showTab(key, focus = false) {
    shopTab = key;
    for (const tab of root.querySelectorAll("[data-shop-tab]")) {
      const on = tab.dataset.shopTab === key;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      if (on && focus) tab.focus();
    }
    for (const panel of root.querySelectorAll("[data-shop-panel]")) panel.hidden = panel.dataset.shopPanel !== key;
  }

  function listStock() {
    if (!town.shop) return;
    showTab(shopTab);
    listPacks();
    listRequest();
    listSpecials();
    listCards();
    listGifts();
    paintBasket();
    renderTutorial(); // the places and the stock are built now: the spotlight can find them
  }

  function listGifts() {
    const list = $("[data-gift-stock]");
    list.replaceChildren();
    $("[data-gifts-note]").textContent = "Something to give the people you meet: one gift each a day. What they think of it depends on them.";
    for (const item of town.shop.gifts) {
      const row = document.createElement("li");
      row.className = "town-stock-item";
      const icon = document.createElement("span");
      icon.className = "town-gift-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = item.icon;
      const text = document.createElement("div");
      text.className = "town-stock-text";
      const name = document.createElement("p");
      name.className = "town-stock-name";
      name.textContent = item.name;
      if (item.have) {
        const have = document.createElement("span");
        have.className = "muted small";
        have.textContent = ` · you have ${item.have}`;
        name.append(have);
      }
      const about = document.createElement("p");
      about.className = "small muted";
      about.textContent = item.about;
      text.append(name, about);
      const buttons = document.createElement("div");
      buttons.className = "town-stock-buy";
      const button = addButton("Add", item.price, () => addToBasket({ kind: "gift", gift: item.key, count: 1 }, `${item.icon} ${item.name}`.trim()));
      button.setAttribute("aria-label", `Add ${item.name} to your basket, ${coins(item.price)} coins`);
      button.dataset.gift = item.key;
      buttons.append(button);
      row.append(icon, text, buttons);
      list.append(row);
    }
  }

  function listPacks() {
    const list = $("[data-stock]");
    list.replaceChildren();
    const { price, stock, sales } = town.shop;
    const onSale = (sales || []).map((sale) => `${sale.icon} ${sale.name}: ${sale.about}`).join(" ");
    $("[data-shop-note]").textContent = `${onSale ? `${onSale} ` : ""}Packs are ${coins(price)} coins each. They open straight into your cards. The shelves change every day.`;
    for (const set of stock) {
      const item = document.createElement("li");
      item.className = "town-stock-item";
      const name = document.createElement("p");
      name.className = "town-stock-name";
      name.textContent = set.name;
      if (set.requested) name.append(" ", el("span", "town-stock-tag", "Requested"));
      if (set.sale) name.append(" ", el("span", "town-stock-tag town-sale-tag", set.sale_left === null || set.sale_left === undefined
        ? "Sale" : set.sale_left ? `Sale: ${set.sale_left} left today` : "Sale: sold out today"));
      const buttons = document.createElement("div");
      buttons.className = "town-stock-buy";
      buttons.append(
        addButton("Add 1", set.price, () => addToBasket({ kind: "pack", set: set.id, count: 1 }, `${set.name} pack`), false, set.was),
        addButton("Add 5", set.price_5, () => addToBasket({ kind: "pack", set: set.id, count: 5 }, `${set.name} pack`), true,
          set.price_5 < price * 5 ? price * 5 : null),
      );
      item.append(cover(set, "town-stock-cover"), name, buttons);
      list.append(item);
    }
  }

  // Asking the shop for a set (weiss.world.request_set): on the shelves from tomorrow for a few days, one at a time.
  let requestSet = null;
  function listRequest() {
    const { price, days, asked, sets } = town.shop.request;
    const note = $("[data-request-note]");
    const form = $("[data-request-form]");
    if (asked) {
      note.textContent = `You've asked for ${asked.name}: it's ${asked.when} You can ask for another once it's gone.`;
      form.hidden = true;
      return;
    }
    form.hidden = !sets.length;
    note.textContent = sets.length
      ? `Not seeing the set you want? Ask for it: it's on the shelves from tomorrow for ${days} days. One set at a time.`
      : "There are no other sets the shop can get.";
    if (!sets.some((set) => set.id === requestSet)) requestSet = sets[0]?.id ?? null;
    const select = $("[data-request-set]");
    select.replaceChildren(...sets.map((set) => new Option(set.name, set.id, false, set.id === requestSet)));
    select.onchange = () => { requestSet = Number(select.value); };
    const holder = $("[data-request-button]");
    const button = buyButton("Ask for it", price, () => askForSet(Number(select.value)));
    button.setAttribute("aria-label", `Ask for the chosen set, ${coins(price)} coins`);
    holder.replaceChildren(button);
  }

  async function askForSet(id) {
    const data = await post(root.dataset.requestSetUrl, { set: id });
    if (!data) return;
    listStock();
    say(data.said);
    $("[data-request-note]").focus({ preventScroll: true }); // the button it was is gone: say what happened there
  }

  function listSpecials() {
    const { specialty_price: price, stock, specials, levels, colors } = town.shop;
    const specialSale = town.shop.specialty_was ? ` On sale now: usually ${coins(town.shop.specialty_was)}.` : "";
    $("[data-specials-note]").textContent = `Specialty packs are ${coins(price)} coins each: a pack made to order from one of today's sets.${specialSale}`;
    const setSelect = $("[data-special-set]");
    if (!stock.some((set) => set.id === specialSet)) specialSet = stock[0]?.id ?? null;
    setSelect.replaceChildren(...stock.map((set) => new Option(set.name, set.id, false, set.id === specialSet)));
    const list = $("[data-specials]");
    list.replaceChildren();
    for (const special of specials) {
      const item = document.createElement("li");
      item.className = "town-stock-item";
      const text = document.createElement("div");
      text.className = "town-stock-text";
      const name = document.createElement("p");
      name.className = "town-stock-name";
      name.textContent = special.name;
      const about = document.createElement("p");
      about.className = "small muted";
      about.textContent = special.about;
      text.append(name, about);
      const buttons = document.createElement("div");
      buttons.className = "town-stock-buy";
      let choice = null;
      if (special.asks) {
        choice = document.createElement("select");
        choice.setAttribute("aria-label", special.asks === "level" ? `${special.name}: which level` : `${special.name}: which color`);
        const options = special.asks === "level" ? levels.map((level) => new Option(`Level ${level}`, level)) : colors.map((color) => new Option(color, color));
        choice.append(...options);
        buttons.append(choice);
      }
      buttons.append(addButton("Add", price, () => {
        const setName = stock.find((set) => set.id === specialSet)?.name || "";
        const picked = special.asks ? { [special.asks]: choice.value } : {};
        const what = special.asks === "level" ? `, level ${choice.value}` : special.asks === "color" ? `, ${choice.value}` : "";
        addToBasket({ kind: "special", special: special.key, set: specialSet, ...picked, count: 1 }, `${special.name} (${setName}${what})`);
      }, false, town.shop.specialty_was));
      item.append(text, buttons);
      list.append(item);
    }
  }

  function listCards() {
    const { card_price: price, cards } = town.shop;
    const row = $("[data-cards]");
    const scrolled = row.scrollLeft;
    $("[data-cards-note]").textContent = cards.length
      ? `Today's rares, ${coins(price)} coins each${town.shop.card_was ? ` (on sale: usually ${coins(town.shop.card_was)})` : ""}, one of each a day. A new selection comes in tomorrow.`
      : "No single cards today. A new selection comes in tomorrow.";
    row.replaceChildren();
    for (const card of cards) {
      const item = document.createElement("li");
      item.className = "town-card";
      if (card.sold) item.classList.add("is-sold");
      const link = document.createElement("a");
      link.href = card.url;
      link.target = "_blank";
      link.rel = "noopener";
      link.className = "town-card-art";
      link.title = `${card.name}: open the card's page`;
      const img = document.createElement("img");
      img.src = card.image;
      img.alt = card.name;
      img.loading = "lazy";
      img.addEventListener("error", () => {
        img.remove();
        link.classList.add("no-art");
      });
      link.append(img);
      const rarity = document.createElement("span");
      rarity.className = "town-card-rarity";
      rarity.textContent = card.rarity;
      link.append(rarity);
      const name = document.createElement("p");
      name.className = "town-card-name";
      name.textContent = card.name;
      const set = document.createElement("p");
      set.className = "small muted town-card-set";
      set.textContent = card.set;
      let button;
      if (card.sold) {
        button = document.createElement("button");
        button.type = "button";
        button.className = "button-small secondary";
        button.textContent = "Bought today";
        button.disabled = true;
      } else if (basket.some((line) => line.kind === "card" && line.card === card.id)) {
        button = document.createElement("button");
        button.type = "button";
        button.className = "button-small secondary";
        button.textContent = "In your basket";
        button.disabled = true;
      } else {
        button = addButton("Add", price, () => addToBasket({ kind: "card", card: card.id, count: 1 }, card.name), false, town.shop.card_was);
        button.setAttribute("aria-label", `Add ${card.name} to your basket, ${coins(price)} coins`);
      }
      item.append(link, name, set, button);
      row.append(item);
    }
    row.scrollLeft = scrolled;
    stepButtons();
  }

  function stepButtons() {
    const row = $("[data-cards]");
    const [back, more] = root.querySelectorAll("[data-cards-step]");
    back.disabled = row.scrollLeft <= 2;
    more.disabled = row.scrollLeft + row.clientWidth >= row.scrollWidth - 2;
  }

  function openShop() {
    closeMap(false);
    closeTalk(false);
    listStock();
    shop.hidden = false;
    shopButton.setAttribute("aria-expanded", "true");
    $(`[data-shop-tab="${shopTab}"]`).focus({ preventScroll: true });
    renderTutorial();
  }

  function closeShop(refocus = true) {
    shop.hidden = true;
    shopButton.setAttribute("aria-expanded", "false");
    if (refocus) menuButton.focus({ preventScroll: true }); // likewise the shop's
    renderTutorial();
  }

  // ---- The card pick: after a win, one card from the beaten CPU's deck (town.card_pick, weiss.world_rewards). It waits
  // in a notice above the stage, and in the duel's result banner, until it's taken or a later win replaces it. ----
  const pick = $("[data-pick]");
  const pickList = $("[data-pick-list]");
  const pickConfirm = $("[data-pick-confirm]");
  const pickNotice = $("[data-pick-notice]");
  const pickOpen = $("[data-pick-open]");
  let pickChosen = null; // the card waiting for its confirmation

  function paintPick() {
    const offer = town.card_pick;
    pickNotice.hidden = !offer;
    if (offer) $("[data-pick-text]").textContent = `${offer.cpu}'s deck has a card for you to take. `;
    if (!offer) {
      if (!pick.hidden) closePick(false);
    } else if (!pick.hidden) {
      listPick(offer); // the offer changed under the open picker: show the new one
    }
  }

  function openPick() {
    const offer = town.card_pick;
    if (!offer) return;
    closeMap(false);
    closeShop(false);
    closeTalk(false);
    $("[data-pick-title]").textContent = `Choose a card from ${offer.cpu}'s deck`;
    $("[data-pick-note]").textContent = "Pick one card to keep. Use the arrow keys to look along the row; Esc decides later.";
    listPick(offer);
    backPick(false);
    pick.hidden = false;
    pickOpen.setAttribute("aria-expanded", "true");
    (pickList.querySelector(".town-pick-card") || $("[data-pick-close]")).focus({ preventScroll: true });
  }

  // Esc, or "Decide later": the offer stays in the notice until a card is taken or a later win replaces it.
  function closePick(refocus = true) {
    pick.hidden = true;
    pickChosen = null;
    pickConfirm.hidden = true;
    pickOpen.setAttribute("aria-expanded", "false");
    if (refocus) pickOpen.focus({ preventScroll: true });
  }

  function listPick(offer) {
    pickList.replaceChildren();
    if (!offer.cards.length) {
      pickList.append(el("li", "small muted", "There are no cards left to choose from."));
      return;
    }
    for (const card of offer.cards) {
      const item = document.createElement("li");
      item.className = "town-card town-pick-item";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "town-pick-card";
      const facts = [card.color, card.level != null ? `Level ${card.level}` : ""].filter(Boolean).join(" · ");
      button.setAttribute("aria-label", `${card.name}, ${card.rarity}${facts ? `, ${facts}` : ""}`);
      const art = el("span", "town-card-art");
      if (card.image) {
        const img = document.createElement("img");
        img.src = card.image;
        img.alt = "";
        img.loading = "lazy";
        img.addEventListener("error", () => { img.remove(); art.classList.add("no-art"); }, { once: true });
        art.append(img);
      } else {
        art.classList.add("no-art"); // no picture: the name and rarity still say which card it is
      }
      art.append(el("span", "town-card-rarity", card.rarity));
      button.append(art, el("span", "town-card-name", card.name), el("span", "town-pick-meta small muted", facts));
      button.addEventListener("click", () => askPick(card));
      item.append(button);
      pickList.append(item);
    }
  }

  // Arrow keys move through the grid of cards: across a row, and up or down a row.
  pickList.addEventListener("keydown", (event) => {
    const buttons = [...pickList.querySelectorAll(".town-pick-card")];
    const at = buttons.indexOf(document.activeElement);
    if (at < 0) return;
    const perRow = Math.max(1, buttons.findIndex((b) => b.offsetTop > buttons[0].offsetTop) || buttons.length);
    const step = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: perRow, ArrowUp: -perRow }[event.key];
    if (!step) return;
    event.preventDefault();
    buttons[Math.min(buttons.length - 1, Math.max(0, at + step))].focus();
  });

  function askPick(card) {
    pickChosen = card;
    $("[data-pick-confirm-text]").textContent = `Take ${card.name} from ${town.card_pick.cpu}'s deck?`;
    pickConfirm.hidden = false;
    pickConfirm.querySelector("[data-pick-take]").focus({ preventScroll: true });
  }

  function backPick(refocus = true) {
    pickConfirm.hidden = true;
    const chosen = pickChosen;
    pickChosen = null;
    if (refocus && chosen) {
      [...pickList.querySelectorAll(".town-pick-card")].find((b) => b.getAttribute("aria-label").startsWith(chosen.name))?.focus({ preventScroll: true });
    }
  }

  async function takePick(card) {
    const data = await post(root.dataset.pickCardUrl, { card: card.id });
    if (!data) return;
    closePick(false);
    paint();
    say(data.said);
  }

  pickOpen.addEventListener("click", openPick);
  $("[data-pick-close]").addEventListener("click", () => closePick());
  $("[data-pick-back]").addEventListener("click", () => backPick());
  $("[data-pick-take]").addEventListener("click", () => pickChosen && takePick(pickChosen));

  // ---- The menu: everything the town offers, from the HUD's Menu button. Choosing an item closes it. ----
  function openMenu() {
    menuPanel.hidden = false;
    menuButton.setAttribute("aria-expanded", "true");
    menuPanel.querySelector("a[href], button:not(:disabled)")?.focus({ preventScroll: true });
  }

  function closeMenu(refocus = true) {
    if (menuPanel.hidden) return;
    const inside = menuPanel.contains(document.activeElement); // focus shouldn't fall out of the page with it
    menuPanel.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
    if (refocus || inside) menuButton.focus({ preventScroll: true });
  }

  menuButton.addEventListener("click", () => (menuPanel.hidden ? openMenu() : closeMenu()));
  menuPanel.addEventListener("click", (event) => {
    if (event.target.closest("a, button:not(:disabled)")) closeMenu(false);
  });
  document.addEventListener("click", (event) => {
    if (!menuPanel.hidden && !menuPanel.contains(event.target) && !menuButton.contains(event.target)) closeMenu(false);
  });

  // ---- Panels: the town's own pages (quests, the deck, the bounty board), framed in the stage so the town never reloads.
  // Each one is the real page, so its forms and scripts work as they do anywhere. A link back to the town, or Esc, closes
  // it; closing catches the town up, as what was done there may change what's shown. ----
  const sheet = $("[data-sheet]");
  const sheetFrame = $("[data-sheet-frame]");
  const sheetTitle = $("[data-sheet-title]");
  const townPath = root.dataset.townUrl;

  function openSheet(title, url) {
    if (mapRequired) return say("Choose where to spend the new time first.");
    closeMenu(false);
    closeMap(false);
    closeShop(false);
    closeTalk(false);
    sheetTitle.textContent = title;
    sheetFrame.title = title;
    sheetFrame.src = url;
    sheet.hidden = false;
    $("[data-sheet-close]").focus({ preventScroll: true });
  }

  function closeSheet(refocus = true) {
    if (sheet.hidden) return;
    sheet.hidden = true;
    sheetFrame.src = "about:blank";
    if (refocus) menuButton.focus({ preventScroll: true });
    refreshTown();
  }

  // Each page the panel shows: a link back to the town closes it, from inside.
  function onSheetLoad() {
    if (sheet.hidden) return;
    let doc;
    try {
      doc = sheetFrame.contentDocument;
      if (sheetFrame.contentWindow.location.pathname === townPath) return closeSheet();
      if (!doc.querySelector("main")) throw new Error("no page"); // a refused or failed page is an error page, with no main
    } catch {
      // The browser wouldn't show the page here (it refuses to frame it, or it failed): say so, rather than a blank panel.
      say("That page couldn't open in the town. Try it again, or use Full screen and the menu.");
      return closeSheet();
    }
    doc.addEventListener("click", (event) => {
      const link = event.target.closest?.("a[href]");
      if (link && link.pathname === townPath) {
        event.preventDefault();
        closeSheet();
      }
    });
    doc.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeSheet();
    });
  }

  async function refreshTown() {
    if (busy) return;
    try {
      const response = await fetch(root.dataset.stateUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) return;
      const fresh = await response.json();
      if (fresh.version !== town.version) {
        town = fresh;
        paint();
      }
    } catch { /* what's shown will do */ }
  }

  sheetFrame.addEventListener("load", onSheetLoad);
  $("[data-sheet-close]").addEventListener("click", () => closeSheet());
  // Anything marked to open a panel (the menu, the news, the deck's notice) does, without going to its page.
  root.addEventListener("click", (event) => {
    const opener = event.target.closest("[data-sheet-open]");
    if (!opener || !root.contains(opener)) return;
    event.preventDefault();
    openSheet(opener.dataset.title, opener.dataset.url || opener.href);
  });

  // ---- Full screen: the stage (the game window) fills the browser window. Esc or F leaves it. ----
  const fullscreenable = Boolean(stage.requestFullscreen);
  function paintFullscreen() {
    const on = document.fullscreenElement === stage;
    for (const button of fullscreenButtons) {
      button.hidden = !fullscreenable;
      button.setAttribute("aria-pressed", String(on));
    }
    $("[data-fullscreen]").title = on ? "Leave full screen (F)" : "Full screen (F)";
    $("[data-menu-fullscreen]").textContent = on ? "Leave full screen" : "Full screen";
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await stage.requestFullscreen();
    } catch {
      say("Full screen isn't available here.");
    }
  }

  document.addEventListener("fullscreenchange", paintFullscreen);
  $("[data-fullscreen]").addEventListener("click", toggleFullscreen);
  $("[data-menu-fullscreen]").addEventListener("click", toggleFullscreen);
  paintFullscreen();

  // ---- Input ----

  box.tabIndex = -1;
  box.addEventListener("click", (event) => {
    if (advance && !event.target.closest?.("button, a")) advance();
  });
  stage.addEventListener("click", (event) => {
    if (advance && !event.target.closest("button, a, [data-box], [data-sheet]")) advance();
  });
  mapButton.addEventListener("click", () => (map.hidden ? openMap() : dismissMap()));
  shopButton.addEventListener("click", () => (shop.hidden ? openShop() : closeShop()));
  $("[data-checkout]").addEventListener("click", checkOut);
  $("[data-basket-empty]").addEventListener("click", () => {
    const had = basket.length;
    basket = [];
    keepBasket();
    listStock();
    if (had) say("Your basket's empty.");
  });
  $("[data-close-map]").addEventListener("click", () => dismissMap());
  $("[data-close-shop]").addEventListener("click", () => closeShop());
  for (const tab of root.querySelectorAll("[data-shop-tab]")) tab.addEventListener("click", () => showTab(tab.dataset.shopTab));
  $("[role=tablist]").addEventListener("keydown", (event) => {
    const keys = [...root.querySelectorAll("[data-shop-tab]")].map((tab) => tab.dataset.shopTab);
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    showTab(keys[(keys.indexOf(shopTab) + step + keys.length) % keys.length], true);
  });
  $("[data-special-set]").addEventListener("change", (event) => (specialSet = Number(event.target.value)));
  $("[data-cards]").addEventListener("scroll", stepButtons, { passive: true });
  for (const step of root.querySelectorAll("[data-cards-step]")) {
    step.addEventListener("click", () => {
      const row = $("[data-cards]");
      row.scrollBy({ left: Number(step.dataset.cardsStep) * row.clientWidth * 0.8, behavior: reduced ? "auto" : "smooth" });
    });
  }
  // (Not passed straight to wait: its argument is the staff flag, and a click event would count as one.)
  waitButton.addEventListener("click", () => wait());
  menuWait.addEventListener("click", () => wait());
  $("[data-staff-wait]").addEventListener("click", () => wait(true));
  $("[data-jump-go]").addEventListener("click", async () => {
    closeTalk(false);
    const from = nowWhen();
    const data = await post(root.dataset.jumpUrl, { weekday: $("[data-jump-day]").value });
    if (!data) return;
    await passage(from, nowWhen(), eventsNow() || "Time passes…", paint);
    say(data.said);
  });
  $("[data-test-mode]").addEventListener("click", async () => {
    const data = await post(root.dataset.testModeUrl, { on: town.test_mode ? "0" : "1" });
    if (!data) return;
    paint();
    say(data.said);
  });
  $("[data-news-close]").addEventListener("click", () => {
    const box = $("[data-news]");
    box.hidden = true;
    box.querySelector("ul").replaceChildren();
  });
  passageEl.addEventListener("click", () => skipPassage && skipPassage());
  document.addEventListener("keydown", (event) => {
    if (skipPassage && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      return skipPassage();
    }
    if (event.ctrlKey || event.metaKey || event.altKey || event.target.matches?.("input, textarea, select")) return;
    const key = event.key.toLowerCase();
    if (!sheet.hidden && key !== "escape") return; // a panel's open: its page has the keys
    if (!pick.hidden && key !== "escape") return; // the card pick has its own keys
    if ((key === "enter" || key === " ") && advance && !event.target.closest?.("button, a")) {
      event.preventDefault();
      advance();
    } else if (key === "escape") {
      if (!sheet.hidden) closeSheet();
      else if (!pick.hidden) (pickConfirm.hidden ? closePick() : backPick());
      else if (!menuPanel.hidden) closeMenu();
      else if (!map.hidden && !mapRequired) dismissMap();
      else if (!shop.hidden) closeShop();
      else if (talking && !advance) closeTalk();
    } else if (key === "m" && !talking && !mapButton.hidden && !mapButton.disabled && !mapRequired) map.hidden ? openMap() : dismissMap();
    else if (key === "w" && !talking && !mapRequired) wait(Boolean(town.test_mode && !town.can_wait));
    else if (key === "f") toggleFullscreen();
  });
  // Coming back to the tab (from a duel, or another tab): catch up.
  document.addEventListener("visibilitychange", async () => {
    if (document.hidden || busy) return;
    try {
      const response = await fetch(root.dataset.stateUrl, { headers: { Accept: "application/json" } });
      if (!response.ok) return;
      const fresh = await response.json();
      if (fresh.version !== town.version) {
        town = fresh;
        paint();
      }
    } catch { /* the page as it is will do */ }
  });

  paint();
  playSceneNow(); // one left waiting (a reload on arriving): it still plays
  if (result) {
    const banner = $("[data-result]");
    banner.querySelector("[data-result-text]").textContent = result.event ? result.event : result.won
      ? `You beat ${result.cpu}: +${result.coins} coins${result.first ? " (with the day's first-win bonus)" : ""}.`
      : `${result.cpu} won this time${result.stake ? `; the ${result.stake}-coin entry fee is gone` : ""}${result.coins ? `. +${result.coins} coins anyway` : ""}. Time moved on.`;
    const quote = banner.querySelector("[data-result-line]");
    quote.hidden = !result.line;
    quote.textContent = result.line ? `${result.cpu}: “${result.line}”` : "";
    const points = banner.querySelector("[data-result-points]");
    points.textContent = result.points ? `+${result.points} ♥${result.rank_up ? ` · You and ${result.cpu} are now: ${result.rank_up}` : ""}` : "";
    const more = banner.querySelector("[data-result-more]");
    more.replaceChildren();
    if (result.rank_line) more.append(Object.assign(document.createElement("p"), { className: "town-result-line", textContent: `${result.cpu}: “${result.rank_line}”` }));
    if (result.rewards && result.rewards.length) more.append(Object.assign(document.createElement("p"), { textContent: `★ ${result.rewards.join(" · ")}` }));
    if (result.scene) {
      const link = Object.assign(document.createElement("a"), { href: result.scene, className: "button-small", textContent: `A moment with ${result.cpu}` });
      more.append(Object.assign(document.createElement("p"), {}), link);
    }
    if (town.card_pick) {
      const choose = Object.assign(document.createElement("button"), { type: "button", className: "button-small", textContent: `Choose a card from ${town.card_pick.cpu}'s deck` });
      choose.addEventListener("click", openPick);
      more.append(choose);
    }
    banner.hidden = false;
    banner.querySelector("[data-result-close]").addEventListener("click", () => (banner.hidden = true));
    if (result.before) {
      // Back from a duel: the time it took passes over the place (the page came with it covered), and if they've
      // moved on, say so, so nobody seems to vanish.
      passage(result.before, nowWhen(), `After your duel with ${result.cpu}`).then(() => {
        if (!town.people.some((p) => p.id === result.cpu_id)) say(`${result.cpu} has gone on their way.`);
      });
    }
  }
})();
