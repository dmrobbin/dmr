// A challenge's deck builder: − / + change the deck on the page (never past what was pulled, or in co-op, past what
// the partner's deck leaves: a card they have every copy of is greyed out), and the deck is listed on the right as
// the card lists' side panel lists one, with the same checks. Solo, saving posts the whole deck as {card id: copies}.
// In co-op (data-live) each change is saved as it's made, the partner's deck is listed on the left, and the page
// polls for the partner's changes, so both players always see the whole pool and both decks. The filters above it
// (name, text, trait, colors, level, cost, type, rarity, set, in the deck or not) and the sort work on the page, so
// nothing unsaved is lost to a reload.
(() => {
  const form = document.querySelector("[data-challenge-deck]");
  if (!form) return;
  const tiles = [...form.querySelectorAll(".pool-card")];
  const byCard = new Map(tiles.map((tile) => [tile.dataset.card, tile]));
  const size = Number(form.dataset.deckSize);
  const climaxTarget = Number(form.dataset.climaxes); // the most a deck can have: 8, or more with an augment...
  const climaxMin = Number(form.dataset.climaxMin) || 8; // ...and the fewest it needs to fight
  const groups = JSON.parse(document.getElementById("deck-groups").textContent);
  const live = "live" in form.dataset;
  const COPY_LIMIT = Number(form.dataset.copyLimit) || 4; // the rules' 4, or fewer with an augment
  const POLL_MS = 3000;
  let dirty = false;

  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  const count = (tile) => Number(tile.dataset.inDeck);
  const theirs = (tile) => Number(tile.dataset.theirs || 0);

  function set(tile, n) {
    n = Math.max(0, Math.min(n, Number(tile.dataset.pulled)));
    tile.dataset.inDeck = n;
    tile.querySelector("[data-count]").textContent = n;
    tile.classList.toggle("in-deck", n > 0);
    tile.classList.toggle("taken", Number(tile.dataset.pulled) === 0); // a co-op partner's deck has every copy
    tile.querySelector('[data-delta="-1"]').disabled = n === 0;
    tile.querySelector('[data-delta="1"]').disabled = n >= Number(tile.dataset.pulled);
  }

  // A deck's cards listed as the card lists' side panel lists them: level, picture, name and number, and copies.
  function entry(tile, copies, controls) {
    const d = tile.dataset;
    const level = d.level === "climax" ? `<span class="panel-level climax" title="Climax">CX</span>`
      : `<span class="panel-level" title="${d.level === "" ? "No level" : `Level ${esc(d.level)}`}">${d.level === "" ? "–" : esc(d.level)}</span>`;
    const picture = tile.querySelector(".pool-picture");
    const img = tile.querySelector("img");
    const name = `<a href="${esc(picture.getAttribute("href"))}" data-card-popup="${esc(picture.dataset.cardPopup)}" class="panel-entry-name">${esc(d.name)}</a>`;
    const qty = controls
      ? `<span class="qty-controls"><button type="button" data-side-delta="-1" data-card="${esc(d.card)}" aria-label="One fewer ${esc(d.name)}">−</button><span class="qty">${copies}</span>`
        + `<button type="button" data-side-delta="1" data-card="${esc(d.card)}" aria-label="One more ${esc(d.name)}"${copies >= Number(d.pulled) ? " disabled" : ""}>+</button></span>`
      : `<span class="qty-controls"><span class="qty">×${copies}</span></span>`;
    return `<li>${level}<a href="${esc(picture.getAttribute("href"))}" data-card-popup="${esc(picture.dataset.cardPopup)}" class="panel-thumb" tabindex="-1" aria-hidden="true">`
      + `${img ? `<img src="${esc(img.getAttribute("src"))}" alt="" loading="lazy">` : ""}</a>${name}<span class="muted small">${esc(d.serial)}</span>${qty}</li>`;
  }

  // In the order the page came in: level, then type, then number.
  const listed = (copiesOf) => tiles.filter((tile) => copiesOf(tile) > 0);

  function summarize() {
    const mine = listed(count);
    const total = mine.reduce((sum, tile) => sum + count(tile), 0);
    const byName = {};
    const free = new Set(); // names whose card says a deck can have any number of them
    for (const tile of mine) {
      byName[tile.dataset.name] = (byName[tile.dataset.name] || 0) + count(tile);
      if ("unlimited" in tile.dataset) free.add(tile.dataset.name);
    }
    const over = Object.entries(byName).filter(([name, n]) => n > COPY_LIMIT && !free.has(name)).map(([name]) => name);
    const climaxes = mine.filter((tile) => tile.dataset.level === "climax").reduce((sum, tile) => sum + count(tile), 0);
    form.querySelector("[data-deck-total]").textContent = `${total} / ${size} cards`;
    const warnings = [];
    if (total > size) warnings.push(`More than ${size} cards`);
    else if (total < size) warnings.push(`${size - total} short of a full deck`);
    const climaxRange = climaxMin === climaxTarget ? `${climaxMin}` : `${climaxMin} to ${climaxTarget}`;
    if (climaxes > climaxTarget) warnings.push(`${climaxes} climaxes: a deck has at most ${climaxTarget}`);
    else if (climaxes < climaxMin) warnings.push(`${climaxes} climaxes: a deck needs ${climaxRange} to fight`);
    if (over.length) warnings.push(`more than ${COPY_LIMIT} of ${over.join(", ")}`);
    form.querySelector("[data-deck-warnings]").textContent = warnings.join(" · ");
    const save = form.querySelector('button[type="submit"]');
    if (save) save.disabled = total > size || climaxes > climaxTarget || (COPY_LIMIT < 4 && over.length > 0); // the server won't take those (Highlander's limit is kept)

    // The deck on the right, with the card lists' checks: rules go red when broken, the level spread amber when off.
    const sideTotal = document.querySelector("[data-side-total]");
    sideTotal.textContent = total;
    sideTotal.parentElement.className = `deck-total${total > size ? " bad" : total === size ? " good" : ""}`;
    document.querySelector("[data-side-groups]").innerHTML = groups.map((group) => {
      const n = mine.filter((tile) => group.levels.includes(tile.dataset.level)).reduce((sum, tile) => sum + count(tile), 0);
      const ok = group.required ? n >= climaxMin && n <= group.target : n === group.target; // the climaxes: any number in range
      const state = ok ? "good" : group.required ? "bad" : "suggest";
      return `<li class="${state}"><span>${esc(group.label)}${group.required ? "" : ' <span class="deck-hint">suggested</span>'}</span><span><strong>${n}</strong> / ${group.required ? climaxRange : group.target}</span></li>`;
    }).join("") + `<li class="${over.length ? "bad" : "good"}"><span>Max ${COPY_LIMIT} of a card</span><span><strong>${over.length ? `${over.length} over` : "OK"}</strong></span></li>`;
    document.querySelector("[data-side-entries]").innerHTML = mine.map((tile) => entry(tile, count(tile), true)).join("");
    document.querySelector("[data-side-empty]").hidden = mine.length > 0;

    const partner = document.querySelector("[data-partner-entries]");
    if (partner) {
      const theirDeck = listed(theirs);
      partner.innerHTML = theirDeck.map((tile) => entry(tile, theirs(tile), false)).join("");
      document.querySelector("[data-partner-total]").textContent = theirDeck.reduce((sum, tile) => sum + theirs(tile), 0);
      document.querySelector("[data-partner-empty]").hidden = theirDeck.length > 0;
    }
  }

  const filters = document.querySelector("[data-pool-filters]");
  const grid = form.querySelector(".pool-grid");
  const shown = document.querySelector("[data-pool-count]");
  const first = new Map(tiles.map((tile, i) => [tile, i])); // the order the page came in: level, then type
  const has = (value, words) => !words || value.toLowerCase().includes(words);
  const number = (tile, field) => (tile.dataset[field] === "" ? null : Number(tile.dataset[field]));

  function filter() {
    const f = new FormData(filters);
    const words = (field) => String(f.get(field) || "").trim().toLowerCase();
    const colors = f.getAll("color");
    const { level, cost, type, rarity, set, show } = Object.fromEntries(["level", "cost", "type", "rarity", "set", "show"].map((k) => [k, f.get(k) || ""]));
    let visible = 0;
    for (const tile of tiles) {
      const d = tile.dataset;
      const ok = has(d.name, words("name")) && has(d.text, words("text")) && has(d.traits, words("trait"))
        && (!colors.length || colors.includes(d.color)) && (!level || d.level === level) && (!cost || d.cost === cost)
        && (!type || d.type === type) && (!rarity || d.rarity === rarity) && (!set || d.set === set)
        && (!show || (show === "theirs" ? theirs(tile) > 0 : show === "free" ? count(tile) < Number(d.pulled) : (show === "deck") === (count(tile) > 0)));
      tile.hidden = !ok;
      if (ok) visible += 1;
    }
    shown.textContent = `${visible} of ${tiles.length} card${tiles.length === 1 ? "" : "s"} in your pool`;
  }

  // Missing numbers (a climax's level, cost and power) go first going up, as on the set pages, and last going down.
  function sort() {
    const by = new FormData(filters).get("sort") || "";
    const field = by.replace("-", "");
    const down = by.startsWith("-");
    const order = [...tiles].sort((a, b) => {
      if (!by) return first.get(a) - first.get(b);
      if (field === "serial" || field === "name") return a.dataset[field].localeCompare(b.dataset[field], undefined, { numeric: true }) || first.get(a) - first.get(b);
      const x = number(a, field);
      const y = number(b, field);
      if (x === y) return first.get(a) - first.get(b);
      if (x === null) return down ? 1 : -1;
      if (y === null) return down ? -1 : 1;
      return down ? y - x : x - y;
    });
    grid.append(...order);
  }

  const deckNow = () => {
    const deck = {};
    for (const tile of tiles) if (count(tile)) deck[tile.dataset.card] = count(tile);
    return deck;
  };

  // Co-op: the server's word on both decks and the pool. A card the page doesn't have yet (packs just opened) needs
  // the page again, which loses nothing, as every change is saved already.
  function catchUp(state) {
    const pool = state.pool || {};
    if (Object.keys(pool).some((pk) => !byCard.has(String(pk)))) {
      if (!pending && !saving) location.reload();
      return;
    }
    for (const tile of tiles) {
      const pk = tile.dataset.card;
      const total = Number(pool[pk] || 0);
      const partner = Number((state.theirs || {})[pk] || 0);
      tile.dataset.theirs = partner;
      tile.dataset.pulled = Math.max(0, total - partner);
      const info = tile.querySelector(".pool-theirs");
      if (info) info.innerHTML = `${partner ? `<strong>${partner}</strong> in ${esc(form.dataset.partner || "your partner")}'s deck · ` : ""}${total} in the pool`;
      if (!pending && !saving) set(tile, Number((state.mine || {})[pk] || 0));
      else set(tile, count(tile));
      tile.querySelector(".pool-count .muted").textContent = ` / ${tile.dataset.pulled}`;
    }
    summarize();
    filter();
  }

  let pending = null;
  let saving = false;
  const savedNote = document.querySelector("[data-deck-saved]");

  // Co-op: save a moment after the last change, so a run of clicks is one save.
  function saveSoon() {
    clearTimeout(pending);
    if (savedNote) savedNote.textContent = "Saving…";
    pending = setTimeout(() => {
      pending = null;
      saving = true;
      const body = new FormData(form);
      body.set("deck", JSON.stringify(deckNow()));
      fetch(form.action || location.href, { method: "POST", body, headers: { Accept: "application/json" } })
        .then((r) => r.json())
        .then((state) => {
          saving = false;
          if (savedNote) {
            savedNote.textContent = state.error || "Saved.";
            savedNote.classList.toggle("panel-error", Boolean(state.error));
          }
          catchUp(state); // refused (their partner took the copies first)? Back to what's saved.
        })
        .catch(() => {
          saving = false;
          if (savedNote) savedNote.textContent = "Couldn't save: check your connection.";
        });
    }, 400);
  }

  function change(tile, n) {
    set(tile, n);
    summarize();
    if (live) saveSoon();
    else dirty = true;
  }

  tiles.forEach((tile) => set(tile, count(tile)));
  summarize();
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delta], [data-side-delta]");
    if (button) {
      const tile = button.dataset.sideDelta ? byCard.get(button.dataset.card) : button.closest(".pool-card");
      if (tile) change(tile, count(tile) + Number(button.dataset.delta || button.dataset.sideDelta));
    }
    if (event.target.closest("[data-deck-clear]")) {
      tiles.forEach((tile) => set(tile, 0));
      summarize();
      filter();
      if (live) saveSoon();
      else dirty = true;
    }
  });
  filters.addEventListener("input", filter);
  filters.addEventListener("change", (event) => (event.target.name === "sort" ? sort() : filter()));
  filters.addEventListener("submit", (event) => event.preventDefault());
  filters.addEventListener("reset", () => setTimeout(() => { sort(); filter(); })); // once the fields have been reset
  filter();
  form.addEventListener("submit", (event) => {
    if (live) {
      event.preventDefault();
      return;
    }
    form.querySelector("[data-deck-field]").value = JSON.stringify(deckNow());
    dirty = false;
  });
  window.addEventListener("beforeunload", (event) => { if (dirty || pending || saving) event.preventDefault(); });

  if (live) {
    setInterval(() => {
      if (document.hidden || pending || saving) return;
      fetch(form.dataset.stateUrl, { headers: { Accept: "application/json" } }).then((r) => (r.ok ? r.json() : null)).then((state) => {
        if (state && !pending && !saving) catchUp(state);
      }).catch(() => {});
    }, POLL_MS);
  }
})();
