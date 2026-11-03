/* Booster pack opening. Clicking the pack shakes it as the screen dims, then it bursts and its cards are revealed one
   at a time, the rarer the grander; further packs follow on, and the end shows every card pulled.
   The page gives {set, grades: [name per grade], packs: [[card, ...], ...]}, each pack in reveal order. */
(() => {
  const source = document.getElementById("pack-opening");
  const table = document.querySelector("[data-pack-table]");
  const results = document.querySelector("[data-pack-results]");
  if (!source || !table || !results) return;
  const data = JSON.parse(source.textContent);
  const packs = data.packs;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, reduced ? Math.min(ms, 120) : ms));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const isClimax = (card) => card.type === "Climax";

  // Per grade: how long the card trembles before it flips, sparks, how bright the flash is, and the rest.
  const EFFECTS = [
    {},
    { ring: true },
    { ring: true, sparks: 14 },
    { ring: true, sparks: 26, flash: 0.35, charge: 450, banner: true },
    { ring: true, sparks: 44, flash: 0.7, charge: 950, banner: true, rays: true, quake: 1 },
    { ring: true, sparks: 80, flash: 1, charge: 1500, banner: true, rays: true, quake: 2, confetti: true },
  ];
  const RAINBOW = ["#ff6b8b", "#ffd36b", "#7dffb0", "#6bc6ff", "#c88bff"];
  const COLORS = [[], ["#bcdcff"], ["#ffd36b", "#fff1c1"], ["#ffd36b", "#ffffff", "#fff1c1"], RAINBOW, [...RAINBOW, "#ffffff"]];
  const effects = (card) => EFFECTS[Math.min(card.grade, EFFECTS.length - 1)];
  const colors = (card) => COLORS[Math.min(card.grade, COLORS.length - 1)];

  let overlay, stage, banner, flashEl, tray, statusEl, nextButton;
  let packIndex = -1;
  let cardIndex = -1;
  let cardEls = [];
  let busy = false;
  let finished = false;

  // A card's face. Climaxes are printed sideways, so in the portrait frame of the opening their art is turned too.
  function face(card, upright) {
    const shape = isClimax(card) ? (upright ? " pk-wide" : " pk-turned") : "";
    return `<span class="pk-face${shape}"><img src="${esc(card.image)}" alt="" draggable="false" data-name="${esc(card.name)}"><span class="pk-sheen"></span></span>`;
  }

  function withFallbacks(root) {
    root.querySelectorAll(".pk-face img").forEach((img) => img.addEventListener("error", () => {
      const named = document.createElement("span");
      named.className = "pk-noimg";
      named.textContent = img.dataset.name;
      img.replaceWith(named);
    }, { once: true }));
    return root;
  }

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function buildOverlay() {
    overlay = document.createElement("div");
    overlay.className = "pk-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", `Opening ${data.set} packs`);
    overlay.innerHTML = `
      <div class="pk-dim"></div>
      <div class="pk-stage"><div class="pk-rays"></div><div class="pk-banner" aria-hidden="true"></div></div>
      <div class="pk-flash"></div>
      <div class="pk-bar">
        <ol class="pk-tray" aria-label="This pack so far"></ol>
        <p class="pk-status" aria-live="polite"></p>
        <div class="pk-controls">
          <button type="button" class="button-small pk-next" disabled>Next card</button>
          <button type="button" class="button-small secondary pk-skip">Skip to the end</button>
        </div>
      </div>`;
    document.body.append(overlay);
    document.body.classList.add("pk-locked");
    stage = overlay.querySelector(".pk-stage");
    banner = overlay.querySelector(".pk-banner");
    flashEl = overlay.querySelector(".pk-flash");
    tray = overlay.querySelector(".pk-tray");
    statusEl = overlay.querySelector(".pk-status");
    nextButton = overlay.querySelector(".pk-next");
    nextButton.addEventListener("click", next);
    overlay.querySelector(".pk-skip").addEventListener("click", finish);
    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Escape") finish();
      else if (event.key === "ArrowRight") next();
    });
    overlay.querySelector(".pk-skip").focus();
    void overlay.offsetWidth;
    overlay.classList.add("pk-open");  // the screen dims
  }

  async function openPack(i) {
    busy = true;
    nextButton.disabled = true;
    nextButton.textContent = "Next card";
    packIndex = i;
    cardIndex = -1;
    tray.innerHTML = "";
    const pageButton = table.querySelector(`[data-pack="${i}"]`);
    pageButton.disabled = true;
    pageButton.classList.add("opened");
    packs[i].forEach((card) => { new Image().src = card.image; });
    setStatus(packs.length > 1 ? `Pack ${i + 1} of ${packs.length}` : "");

    const pack = document.createElement("div");
    pack.className = "pk-pack";
    pack.innerHTML = pageButton.innerHTML;
    stage.append(pack);
    if (i > 0 && !reduced) {
      await pack.animate([{ transform: "translateY(70vh) rotate(10deg)" }, { transform: "none" }],
                         { duration: 550, easing: "cubic-bezier(.2,.8,.3,1)" }).finished;
    }
    pack.classList.add("shaking");
    await wait(1100);
    if (finished) return;
    pack.classList.add("burst");
    flash(0.9);
    sparks(30, COLORS[3], false);
    await deal(packs[i]);
    pack.remove();
    if (!finished) await reveal(0);
  }

  // Where each card sits in the stack once dealt: the first to be revealed on top.
  const stackSpot = (k) => `translate(${k * 2}px, ${k * -2}px) rotate(${((k % 3) - 1) * 1.5}deg)`;

  async function deal(cards) {
    const box = stage.getBoundingClientRect();
    const reach = Math.min(box.width, box.height) * 0.42;
    cardEls = cards.map((card, k) => {
      const el = document.createElement("div");
      el.className = "pk-card";
      el.dataset.grade = card.grade;
      el.style.zIndex = String(cards.length - k);
      el.innerHTML = `<div class="pk-wobble"><div class="pk-flip"><span class="pk-back"></span>${face(card, false)}</div></div>`;
      stage.append(withFallbacks(el));
      return el;
    });
    const flights = cardEls.map((el, k) => {
      const angle = (k / cardEls.length) * Math.PI * 2 + Math.random() * 0.6;
      const x = Math.cos(angle) * reach;
      const y = Math.sin(angle) * reach * 0.8;
      const spin = (Math.random() - 0.5) * 140;
      return el.animate([
        { transform: "translate(0, 0) scale(.2) rotate(0deg)", opacity: 0, easing: "cubic-bezier(.1,.8,.3,1)" },
        { transform: `translate(${x}px, ${y}px) scale(.8) rotate(${spin}deg)`, opacity: 1, offset: 0.45, easing: "cubic-bezier(.5,0,.3,1)" },
        { transform: stackSpot(k), opacity: 1 },
      ], { duration: reduced ? 1 : 1300, delay: reduced ? 0 : k * 40, fill: "forwards" });
    });
    await Promise.all(flights.map((flight) => flight.finished));
    cardEls.forEach((el, k) => {
      el.style.transform = stackSpot(k);
      flights[k].cancel();
      el.classList.add("pk-dealt");
    });
  }

  async function reveal(k) {
    busy = true;
    nextButton.disabled = true;
    clearEffects();
    if (cardIndex >= 0) toTray(cardIndex);
    cardIndex = k;
    const pack = packs[packIndex];
    const card = pack[k];
    const el = cardEls[k];
    const fx = effects(card);
    el.style.zIndex = "50";
    el.style.transform = "translate(0, -1rem) scale(1.06)";
    await wait(300);
    if (fx.charge && !reduced) {
      overlay.classList.add("pk-hush");  // the room goes quiet
      el.classList.add("charging");
      await wait(fx.charge);
      el.classList.remove("charging");
    }
    if (finished) return;
    el.classList.add("flipped");
    await wait(300);
    flourish(card, fx);
    await wait(450);
    if (isClimax(card)) el.classList.add("turned");  // turn it round to read it

    const where = packs.length > 1 ? `Pack ${packIndex + 1} of ${packs.length} · ` : "";
    setStatus(`${where}Card ${k + 1} of ${pack.length}: ${card.name} (${card.rarity})`);
    if (k < pack.length - 1) nextButton.textContent = "Next card";
    else if (packIndex < packs.length - 1) nextButton.textContent = `Open pack ${packIndex + 2}`;
    else nextButton.textContent = "See all cards";
    busy = false;
    nextButton.disabled = false;
    nextButton.focus();
  }

  function flourish(card, fx) {
    overlay.classList.remove("pk-hush");
    if (fx.ring) ring(colors(card)[0]);
    if (fx.sparks && !reduced) sparks(fx.sparks, colors(card), fx.confetti);
    if (fx.flash) flash(reduced ? fx.flash / 3 : fx.flash);
    if (fx.rays) overlay.classList.add("pk-rays-on", `pk-rays-${card.grade >= 5 ? 5 : 4}`);
    if (fx.banner) {
      banner.dataset.grade = Math.min(card.grade, 5);
      banner.innerHTML = `<span class="pk-banner-rarity">${esc(card.rarity)}</span><span class="pk-banner-word">${esc(data.grades[Math.min(card.grade, data.grades.length - 1)])}</span>`;
      banner.classList.remove("show");
      void banner.offsetWidth;
      banner.classList.add("show");
    }
    if (fx.quake && !reduced) {
      const a = fx.quake * 5;
      stage.animate([
        { transform: "none" }, { transform: `translate(${-a}px, ${a / 2}px)` }, { transform: `translate(${a}px, ${-a / 2}px)` },
        { transform: `translate(${-a / 2}px, ${-a}px)` }, { transform: `translate(${a / 2}px, ${a}px)` }, { transform: "none" },
      ], { duration: 450 + fx.quake * 150, easing: "ease-out" });
    }
  }

  function clearEffects() {
    overlay.classList.remove("pk-hush", "pk-rays-on", "pk-rays-4", "pk-rays-5");
    banner.classList.remove("show");
  }

  function flash(peak) {
    flashEl.animate([{ opacity: 0 }, { opacity: peak, offset: 0.15 }, { opacity: 0 }], { duration: 650, easing: "ease-out" });
  }

  function ring(color) {
    const el = document.createElement("span");
    el.className = "pk-ring";
    el.style.borderColor = color;
    stage.append(el);
    el.animate([{ transform: "scale(.6)", opacity: 0.9 }, { transform: "scale(3.4)", opacity: 0 }], { duration: 900, easing: "ease-out" })
      .finished.then(() => el.remove());
  }

  function sparks(count, palette, confetti) {
    const box = stage.getBoundingClientRect();
    const far = Math.min(box.width, box.height) * 0.6;
    for (let n = 0; n < count; n++) {
      const el = document.createElement("span");
      const paper = confetti && n % 2 === 0;
      el.className = paper ? "pk-spark confetti" : "pk-spark";
      el.style.color = palette[n % palette.length];
      stage.append(el);
      const angle = Math.random() * Math.PI * 2;
      const distance = far * (0.35 + Math.random() * 0.65);
      const x = Math.cos(angle) * distance;
      const y = Math.sin(angle) * distance;
      const turn = (Math.random() - 0.5) * 720;
      const frames = paper
        ? [{ transform: "translate(0, 0) rotate(0deg)", opacity: 1 },
           { transform: `translate(${x}px, ${y}px) rotate(${turn}deg)`, opacity: 1, offset: 0.5 },
           { transform: `translate(${x * 1.1}px, ${y + far * 0.6}px) rotate(${turn * 2}deg)`, opacity: 0 }]
        : [{ transform: "translate(0, 0) scale(1.2)", opacity: 1 },
           { transform: `translate(${x}px, ${y}px) scale(.3)`, opacity: 0 }];
      el.animate(frames, { duration: (paper ? 1800 : 800) + Math.random() * 600, easing: "cubic-bezier(.1,.8,.3,1)" })
        .finished.then(() => el.remove());
    }
  }

  // The revealed card drops into the strip of this pack's cards.
  function toTray(k) {
    const el = cardEls[k];
    const card = packs[packIndex][k];
    const thumb = document.createElement("li");
    thumb.className = "pk-thumb";
    thumb.dataset.grade = card.grade;
    thumb.innerHTML = `<a href="${esc(card.url)}" data-card-popup="${esc(card.popup)}" title="${esc(card.name)} (${esc(card.rarity)})">${face(card, true)}</a>`;
    tray.append(withFallbacks(thumb));
    el.animate([{ opacity: 1 }, { transform: "translate(0, 45vh) scale(.2)", opacity: 0 }], { duration: 350, easing: "ease-in", fill: "forwards" })
      .finished.then(() => el.remove());
  }

  async function next() {
    if (busy || finished) return;
    if (cardIndex < packs[packIndex].length - 1) {
      await reveal(cardIndex + 1);
      return;
    }
    if (packIndex < packs.length - 1) {
      busy = true;
      nextButton.disabled = true;
      clearEffects();
      toTray(cardIndex);
      await wait(600);
      if (!finished) await openPack(packIndex + 1);
      return;
    }
    finish();
  }

  function finish() {
    if (finished) return;
    finished = true;
    if (overlay) {
      overlay.classList.add("pk-closing");
      setTimeout(() => overlay.remove(), 400);
      document.body.classList.remove("pk-locked");
    }
    table.hidden = true;
    showResults();
  }

  function showResults() {
    const all = packs.flatMap((pack, p) => pack.map((card) => ({ ...card, pack: p + 1 })));
    const total = results.querySelector("[data-pack-total]");
    total.textContent = `${all.length} card${all.length === 1 ? "" : "s"} from ${packs.length} pack${packs.length === 1 ? "" : "s"}`;

    const tally = new Map();
    all.forEach((card) => {
      const entry = tally.get(card.rarity) || { rarity: card.rarity, grade: card.grade, count: 0 };
      entry.count += 1;
      tally.set(card.rarity, entry);
    });
    results.querySelector("[data-pack-tally]").innerHTML = [...tally.values()]
      .sort((a, b) => b.grade - a.grade || b.count - a.count)
      .map((entry) => `<li><span class="pk-rarity" data-grade="${entry.grade}">${esc(entry.rarity)}</span> × ${entry.count}</li>`)
      .join("");

    // Best first; cards of a rarity stay in the order they were pulled.
    const sorted = [...all].sort((a, b) => b.grade - a.grade);
    const grid = results.querySelector("[data-pack-grid]");
    grid.innerHTML = sorted.map((card, i) => `
      <li><a class="pk-result" data-grade="${card.grade}" style="--i: ${i}" href="${esc(card.url)}" data-card-popup="${esc(card.popup)}">
        ${face(card, true)}
        <span class="pk-result-name"><span class="pk-rarity" data-grade="${card.grade}">${esc(card.rarity)}</span> ${esc(card.name)}</span>
        <span class="pk-result-meta">${esc(card.serial)}${packs.length > 1 ? ` · pack ${card.pack}` : ""}</span>
      </a></li>`).join("");
    withFallbacks(grid);
    results.hidden = false;
    total.setAttribute("tabindex", "-1");
    total.focus();
  }

  table.querySelector('[data-pack="0"]').addEventListener("click", () => {
    if (overlay) return;
    buildOverlay();
    openPack(0);
  });
})();
