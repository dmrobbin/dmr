// A challenge's deck builder: − / + change the deck on the page (never past what was pulled), the bar keeps
// count of the deck as it is, and saving posts the whole deck as {card id: copies}. The filters above it (name, text,
// trait, colors, level, cost, type, rarity, set, in the deck or not) and the sort work on the page, so nothing unsaved
// is lost to a reload.
(() => {
  const form = document.querySelector("[data-challenge-deck]");
  if (!form) return;
  const tiles = [...form.querySelectorAll(".pool-card")];
  const size = Number(form.dataset.deckSize);
  const climaxTarget = Number(form.dataset.climaxes);
  const COPY_LIMIT = 4;
  let dirty = false;

  const count = (tile) => Number(tile.dataset.inDeck);

  function set(tile, n) {
    n = Math.max(0, Math.min(n, Number(tile.dataset.pulled)));
    tile.dataset.inDeck = n;
    tile.querySelector("[data-count]").textContent = n;
    tile.classList.toggle("in-deck", n > 0);
    tile.querySelector('[data-delta="-1"]').disabled = n === 0;
    tile.querySelector('[data-delta="1"]').disabled = n >= Number(tile.dataset.pulled);
  }

  function summarize() {
    const total = tiles.reduce((sum, tile) => sum + count(tile), 0);
    const groups = { climax: 0, 0: 0, 1: 0, 2: 0, 3: 0 };
    const byName = {};
    for (const tile of tiles) {
      if (tile.dataset.level in groups) groups[tile.dataset.level] += count(tile);
      byName[tile.dataset.name] = (byName[tile.dataset.name] || 0) + count(tile);
    }
    form.querySelector("[data-deck-total]").textContent = `${total} / ${size} cards`;
    form.querySelector("[data-deck-groups]").textContent =
      `Climaxes ${groups.climax} / ${climaxTarget} · Level 0: ${groups[0]} · 1: ${groups[1]} · 2: ${groups[2]} · 3: ${groups[3]}`;
    const warnings = [];
    if (total > size) warnings.push(`More than ${size} cards`);
    else if (total < size) warnings.push(`${size - total} short of a full deck`);
    if (groups.climax !== climaxTarget) warnings.push(`${groups.climax} climaxes, not ${climaxTarget}`);
    const over = Object.entries(byName).filter(([, n]) => n > COPY_LIMIT).map(([name]) => name);
    if (over.length) warnings.push(`more than ${COPY_LIMIT} of ${over.join(", ")}`);
    form.querySelector("[data-deck-warnings]").textContent = warnings.join(" · ");
    form.querySelector('button[type="submit"]').disabled = total > size;
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
        && (!show || (show === "deck") === (count(tile) > 0));
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

  tiles.forEach((tile) => set(tile, count(tile)));
  summarize();
  form.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delta]");
    if (button) {
      const tile = button.closest(".pool-card");
      set(tile, count(tile) + Number(button.dataset.delta));
      dirty = true;
      summarize();
    }
    if (event.target.closest("[data-deck-clear]")) {
      tiles.forEach((tile) => set(tile, 0));
      dirty = true;
      summarize();
      filter();
    }
  });
  filters.addEventListener("input", filter);
  filters.addEventListener("change", (event) => (event.target.name === "sort" ? sort() : filter()));
  filters.addEventListener("submit", (event) => event.preventDefault());
  filters.addEventListener("reset", () => setTimeout(() => { sort(); filter(); })); // once the fields have been reset
  filter();
  form.addEventListener("submit", () => {
    const deck = {};
    for (const tile of tiles) if (count(tile)) deck[tile.dataset.card] = count(tile);
    form.querySelector("[data-deck-field]").value = JSON.stringify(deck);
    dirty = false;
  });
  window.addEventListener("beforeunload", (event) => { if (dirty) event.preventDefault(); });
})();
