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
  const waitButton = $("[data-wait]");
  const toast = $("[data-toast]");
  const me = $("[data-me]");
  const meFigure = $("[data-me-figure]");
  const csrf = root.querySelector("[name=csrfmiddlewaretoken]").value;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const LIGHTS = ["town-morning", "town-noon", "town-evening", "town-night"];
  const DAYLIT = new Set(["sakura", "beach", "ocean", "classroom", "forest", "snow", "desert"]); // drawn in daylight: tinted for the time
  const TYPE_MS = 22;

  let town = JSON.parse(document.getElementById("town-state").textContent);
  const result = JSON.parse(document.getElementById("town-result").textContent);
  const portrait = JSON.parse(document.getElementById("town-portrait").textContent);
  let busy = false;
  let talking = null; // the person being talked to
  let advance = null; // what a click or key does while a line is showing

  // ---- Drawing the place ----

  function paint() {
    const place = town.place;
    if (place) {
      backdrop.dataset.bg = place.backdrop;
      backdrop.innerHTML = window.SceneBackdrops ? SceneBackdrops.draw(place.backdrop) : "";
      light.className = `town-light ${DAYLIT.has(place.backdrop) ? LIGHTS[town.time] : ""}`;
      $("[data-place-name]").textContent = place.name;
      document.title = `${place.name} · ${document.title.split(" · ").slice(1).join(" · ")}`;
    }
    $("[data-when]").textContent = `Day ${town.day} · ${town.weekday} ${town.time_name.toLowerCase()}`;
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
    waitButton.disabled = Boolean(town.duel);
    $("[data-deck-notice]").hidden = town.deck_ready;
    paintPeople();
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
      button.style.setProperty("--delay", `${i * 90}ms`);
      button.setAttribute("aria-label", `Talk to ${person.name}`);
      const tag = document.createElement("span");
      tag.className = "town-tag";
      tag.textContent = person.name;
      button.append(picture(person), tag);
      button.addEventListener("click", () => meet(person));
      people.append(button);
    });
    empty.hidden = here.length > 0;
  }

  let toastTimer;
  function say(text) {
    if (!text) return;
    toast.textContent = text;
    toast.classList.add("town-toast-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("town-toast-on"), 4200);
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
      if (data.town) town = data.town;
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
      waitButton.disabled = Boolean(town.duel);
    }
  }

  async function go(key) {
    closeMap(false);
    closeTalk(false);
    const data = await post(root.dataset.travelUrl, { place: key });
    if (!data) return;
    await fade(paint);
    say(data.said);
  }

  async function wait() {
    if (town.duel) return say("You're in a duel: finish it first.");
    closeTalk(false);
    const before = new Set(town.people.map((p) => p.name));
    const data = await post(root.dataset.waitUrl, {});
    if (!data) return;
    await fade(paint);
    const after = new Set(town.people.map((p) => p.name));
    const went = [...before].filter((n) => !after.has(n));
    const came = [...after].filter((n) => !before.has(n));
    say([data.said, went.length ? `${went.join(", ")} left.` : "", came.length ? `${came.join(", ")} arrived.` : ""].filter(Boolean).join(" "));
  }

  // ---- Talking ----
  // Talk and gifts are played from what the server says happened (weiss.world.talk / give / answer): lines, points,
  // coins and gifts, then what it's waiting for (a choice, a duel on offer) or nothing (back to the menu).

  let myKit = null;
  if (portrait && window.Portrait) Portrait.load(root.dataset.portraits).then((kit) => { myKit = kit; }).catch(() => {});
  const myMood = (mood) => myKit && myKit.draw(meFigure, portrait, mood ? { mood } : {});
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
      button.className = `town-option ${extra.quiet ? "town-option-quiet" : ""}`;
      button.textContent = label;
      if (extra.title) button.title = extra.title;
      button.disabled = Boolean(extra.disabled);
      button.addEventListener("click", act);
      menu.append(button);
    }
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
    relationEl.title = relation.next === null ? "The closest you can be." : `${relation.next - relation.points} more to the next rank.`;
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
    for (const el of people.children) el.classList.toggle("town-away", Number(el.dataset.cpu) !== person.id);
    const chosen = people.querySelector(`[data-cpu="${person.id}"]`);
    chosen?.classList.add("town-chosen");
    if (myKit && chosen) {
      chosen.dataset.home = chosen.style.left;
      chosen.style.left = "70%";
      myMood("smile");
      stage.classList.add("town-staged");
      me.hidden = false;
      requestAnimationFrame(() => me.classList.add("town-me-in"));
    }
    box.hidden = false;
    speaker("them");
    showRelation(person.relation);
    const hello = person.duelled ? "Back again?" : person.relation && person.relation.rank >= 2 ? `Hey, ${root.dataset.player || "you"}.` : "Hm? Oh, hello.";
    lines([hello], choices);
  }

  // Keeps `talking` up to date with the town as the server last said it.
  function refreshTalking() {
    if (talking) talking = town.people.find((p) => p.id === talking.id) || talking;
  }

  function choices() {
    if (!talking) return;
    refreshTalking();
    const person = talking;
    speaker("them");
    theirMood("main");
    myMood("smile");
    const stake = person.offer || person.stake;
    textEl.textContent = stake
      ? `${person.name} plays for stakes: ${stake} coins to enter, ${stake * 2} back if you win.`
      : "What would you like to do?";
    const why = town.duel ? "You're in a duel already." : !town.deck_ready ? "Your equipped deck isn't ready." : "";
    const relation = person.relation || {};
    const held = (town.gifts || []).filter((item) => item.have > 0);
    const noGift = relation.gifted ? "You've given them something today." : !held.length ? "Buy gifts at the card shop." : "";
    const list = [
      ["Talk", talk, { title: relation.talked ? "" : "The day's first talk brings them closer." }],
      ["Give a gift", giftMenu, { disabled: Boolean(noGift), title: noGift }],
      ["Duel", () => duel(false), { disabled: Boolean(why), title: why }],
    ];
    if (stake) {
      const short = town.money < stake ? `You have ${town.money} coins.` : "";
      list.push([`High-stakes duel (${stake} coins)`, () => duel(true), { disabled: Boolean(why || short), title: why || short }]);
    }
    list.push(["Leave", leave, { quiet: true }]);
    options(list);
    if (why) note(why, !town.deck_ready && !town.duel ? { href: root.dataset.decksUrl, text: "Your decks" } : null);
  }

  async function talk() {
    const data = await post(root.dataset.talkUrl, { cpu: talking.id });
    if (data && talking) play(data.talk);
    else if (talking) choices();
  }

  function giftMenu() {
    speaker("player");
    myMood("smile");
    textEl.textContent = "What will you give them?";
    const held = (town.gifts || []).filter((item) => item.have > 0);
    options([
      ...held.map((item) => [`${item.icon} ${item.name}${item.have > 1 ? ` (${item.have})` : ""}`, () => give(item)]),
      ["Back", choices, { quiet: true }],
    ]);
  }

  async function give(item) {
    menu.replaceChildren();
    const data = await post(root.dataset.giveUrl, { cpu: talking.id, gift: item.key });
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
        if (event.who === "player") myMood(event.mood || "smile");
        return lines([event.say], next);
      }
      if (event.gave) {
        theirMood({ loved: "pleased", liked: "pleased", disliked: "dismayed" }[event.reaction] || "main");
        myMood(event.reaction === "disliked" ? "surprised" : "happy");
        speaker("player");
        return lines([`You give ${talking.name} the ${event.icon} ${event.gave}.`], next);
      }
      if (event.points !== undefined) {
        floatPoints(event.points);
        showRelation(event.relation);
        if (event.rank_up) {
          speaker("");
          myMood("happy");
          return lines([`♥ You and ${talking.name} are now: ${event.rank_up}.`], next);
        }
        return next();
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
    if (why) note(why, !town.deck_ready && !town.duel ? { href: root.dataset.decksUrl, text: "Your decks" } : null);
  }

  async function duel(stakes) {
    const person = talking;
    speaker("them");
    theirMood("main");
    myMood("smug");
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
    lines(["See you around."], () => closeTalk());
  }

  function closeTalk(refocus = true) {
    const person = talking;
    talking = null;
    advance = null;
    box.hidden = true;
    relationEl.hidden = true;
    me.classList.remove("town-me-in");
    me.hidden = true;
    stage.classList.remove("town-staged");
    for (const el of people.children) {
      el.classList.remove("town-away", "town-chosen");
      if (el.dataset.home) el.style.left = el.dataset.home;
    }
    if (person && refocus) people.querySelector(`[data-cpu="${person.id}"]`)?.focus({ preventScroll: true });
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
      button.disabled = place.here;
      button.innerHTML = `<span class="town-place-art">${window.SceneBackdrops ? SceneBackdrops.draw(place.backdrop) : ""}</span>
        <span class="town-place-name"></span><span class="town-place-who small"></span>`;
      button.querySelector(".town-place-name").textContent = place.name;
      if (place.here) {
        const note = document.createElement("span");
        note.className = "muted small";
        note.textContent = " (you're here)";
        button.querySelector(".town-place-name").append(note);
      }
      button.querySelector(".town-place-who").append(...whoIsThere(place.who));
      button.setAttribute("aria-label", `${place.name}${place.here ? " (you're here)" : ""}: ${place.who.length ? place.who.map((p) => p.name).join(", ") : "nobody right now"}`);
      button.addEventListener("click", () => go(place.key));
      item.append(button);
      list.append(item);
    }
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

  function openMap() {
    closeShop(false);
    closeTalk(false);
    listPlaces();
    map.hidden = false;
    mapButton.setAttribute("aria-expanded", "true");
    $("[data-places] button:not(:disabled)")?.focus({ preventScroll: true });
  }

  function closeMap(refocus = true) {
    map.hidden = true;
    mapButton.setAttribute("aria-expanded", "false");
    if (refocus) mapButton.focus({ preventScroll: true });
  }

  // ---- The card shop ----

  let shopTab = "packs";
  let specialSet = null; // the set chosen for specialty packs, kept while the shop's open

  const coins = (n) => n.toLocaleString();

  function buyButton(label, cost, onBuy, secondary = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = secondary ? "button-small secondary" : "button-small";
    button.textContent = `${label} · ${coins(cost)}`;
    button.disabled = town.money < cost;
    if (button.disabled) button.title = `You have ${coins(town.money)} coins.`;
    button.addEventListener("click", onBuy);
    return button;
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
    listSpecials();
    listCards();
    listGifts();
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
      const button = buyButton("Buy", item.price, () => buyGift(item));
      button.setAttribute("aria-label", `Buy ${item.name} for ${coins(item.price)} coins`);
      button.dataset.gift = item.key;
      buttons.append(button);
      row.append(icon, text, buttons);
      list.append(row);
    }
  }

  async function buyGift(item) {
    const data = await post(root.dataset.buyGiftUrl, { gift: item.key });
    if (!data) return;
    paint();
    say(data.said);
    $(`[data-gift-stock] [data-gift="${item.key}"]`)?.focus({ preventScroll: true });
  }

  function listPacks() {
    const list = $("[data-stock]");
    list.replaceChildren();
    const { price, stock } = town.shop;
    $("[data-shop-note]").textContent = `Packs are ${coins(price)} coins each. They open straight into your cards. The shelves change every day.`;
    for (const set of stock) {
      const item = document.createElement("li");
      item.className = "town-stock-item";
      const name = document.createElement("p");
      name.className = "town-stock-name";
      name.textContent = set.name;
      const buttons = document.createElement("div");
      buttons.className = "town-stock-buy";
      buttons.append(
        buyButton("1 pack", price, () => buy({ set: set.id, count: 1 })),
        buyButton("5 packs", price * 5, () => buy({ set: set.id, count: 5 }), true),
      );
      item.append(cover(set, "town-stock-cover"), name, buttons);
      list.append(item);
    }
  }

  function listSpecials() {
    const { specialty_price: price, stock, specials, levels, colors } = town.shop;
    $("[data-specials-note]").textContent = `Specialty packs are ${coins(price)} coins each: a pack made to order from one of today's sets.`;
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
      buttons.append(buyButton("Buy", price, () => buy({ special: special.key, set: specialSet, [special.asks || "none"]: choice?.value ?? "" })));
      item.append(text, buttons);
      list.append(item);
    }
  }

  function listCards() {
    const { card_price: price, cards } = town.shop;
    const row = $("[data-cards]");
    const scrolled = row.scrollLeft;
    $("[data-cards-note]").textContent = cards.length
      ? `Today's rares, ${coins(price)} coins each, one of each a day. A new selection comes in tomorrow.`
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
      } else {
        button = buyButton("Buy", price, () => buyCard(card));
        button.setAttribute("aria-label", `Buy ${card.name} for ${coins(price)} coins`);
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

  async function buyCard(card) {
    const data = await post(root.dataset.buyCardUrl, { card: card.id });
    if (!data) return;
    paint();
    say(data.said);
  }

  function buy(fields) {
    const form = document.querySelector("[data-buy-form]");
    for (const input of form.querySelectorAll("input[type=hidden]:not([name=csrfmiddlewaretoken])")) input.value = fields[input.name] ?? "";
    form.submit();
  }

  function openShop() {
    closeMap(false);
    closeTalk(false);
    listStock();
    shop.hidden = false;
    shopButton.setAttribute("aria-expanded", "true");
    $(`[data-shop-tab="${shopTab}"]`).focus({ preventScroll: true });
  }

  function closeShop(refocus = true) {
    shop.hidden = true;
    shopButton.setAttribute("aria-expanded", "false");
    if (refocus) shopButton.focus({ preventScroll: true });
  }

  // ---- Input ----

  box.tabIndex = -1;
  box.addEventListener("click", (event) => {
    if (advance && !event.target.closest("button, a")) advance();
  });
  stage.addEventListener("click", (event) => {
    if (advance && !event.target.closest("button, a, [data-box]")) advance();
  });
  mapButton.addEventListener("click", () => (map.hidden ? openMap() : closeMap()));
  shopButton.addEventListener("click", () => (shop.hidden ? openShop() : closeShop()));
  $("[data-close-map]").addEventListener("click", () => closeMap());
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
  waitButton.addEventListener("click", wait);
  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.target.matches("input, textarea, select")) return;
    const key = event.key.toLowerCase();
    if ((key === "enter" || key === " ") && advance && !event.target.closest("button, a")) {
      event.preventDefault();
      advance();
    } else if (key === "escape") {
      if (!map.hidden) closeMap();
      else if (!shop.hidden) closeShop();
      else if (talking && !advance) closeTalk();
    } else if (key === "m" && !talking) map.hidden ? openMap() : closeMap();
    else if (key === "w" && !talking) wait();
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
  if (result) {
    const banner = $("[data-result]");
    banner.querySelector("[data-result-text]").textContent = result.won
      ? `You beat ${result.cpu}: +${result.coins} coins${result.first ? " (with the day's first-win bonus)" : ""}.`
      : `${result.cpu} won this time${result.stake ? `; the ${result.stake}-coin entry fee is gone` : ""}. Time moved on.`;
    const quote = banner.querySelector("[data-result-line]");
    quote.hidden = !result.line;
    quote.textContent = result.line ? `${result.cpu}: “${result.line}”` : "";
    const points = banner.querySelector("[data-result-points]");
    points.textContent = result.points ? `+${result.points} ♥${result.rank_up ? ` · You and ${result.cpu} are now: ${result.rank_up}` : ""}` : "";
    banner.hidden = false;
    banner.querySelector("[data-result-close]").addEventListener("click", () => (banner.hidden = true));
  }
})();
