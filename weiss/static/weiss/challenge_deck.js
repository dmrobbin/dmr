// A challenge's deck builder: − / + change the deck on the page (never past what was pulled), the bar keeps
// count of the deck as it is, and saving posts the whole deck as {card id: copies}.
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

  function filter() {
    const show = form.querySelector("[data-deck-filter]").value;
    for (const tile of tiles) {
      tile.hidden = !(show === "all" || (show === "deck" && count(tile) > 0) || (show === "out" && count(tile) === 0) || tile.dataset.level === show);
    }
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
  form.querySelector("[data-deck-filter]").addEventListener("change", filter);
  form.addEventListener("submit", () => {
    const deck = {};
    for (const tile of tiles) if (count(tile)) deck[tile.dataset.card] = count(tile);
    form.querySelector("[data-deck-field]").value = JSON.stringify(deck);
    dirty = false;
  });
  window.addEventListener("beforeunload", (event) => { if (dirty) event.preventDefault(); });
})();
