// Card type and role chips (weiss/type_filter.html): each row (fieldset[data-filter-field]) filters on that data
// attribute of the cards it's over: data-type holds one type, data-roles any number of roles, space-separated. Within a
// row a card shows if it has any ticked value; rows narrow each other (Character + Combo: character combo cards).
// None ticked in a row lets every card through it. Groups of cards (data-type-group) left with none showing are
// hidden. The side panel is re-rendered after each +/- (lists.js calls typeFilters.refresh), so each bar's choice is
// kept here and put back on its new chips.
(() => {
  if (window.typeFilters) return; // a page can load this more than once, e.g. once for each kept deck it shows
  const chosen = {}; // a bar's data-type-filter -> {field: the values ticked in that row}
  const valuesOf = (card, field) => (card.dataset[field] || "").split(" ").filter(Boolean);

  function apply(bar) {
    const key = bar.dataset.typeFilter;
    const area = document.querySelector(`[data-type-cards="${key}"]`);
    if (!area) return;
    const cards = [...area.querySelectorAll("[data-type]")];
    const rows = [...bar.querySelectorAll("[data-filter-field]")].map((row) => {
      const field = row.dataset.filterField;
      const ticked = [...row.querySelectorAll("input:checked")].map((input) => input.value);
      const present = new Set(cards.flatMap((card) => valuesOf(card, field)));
      for (const input of row.querySelectorAll("input")) input.closest("label").hidden = !present.has(input.value) && !input.checked;
      // Types: nothing to choose between with only one. Roles: one is still worth picking out, but none isn't.
      row.hidden = !ticked.length && (field === "type" ? present.size < 2 : present.size === 0);
      return { field, ticked };
    });
    chosen[key] = Object.fromEntries(rows.map(({ field, ticked }) => [field, ticked]));

    const filtering = rows.some(({ ticked }) => ticked.length);
    let shown = 0;
    for (const card of cards) {
      card.hidden = !rows.every(({ field, ticked }) => !ticked.length || valuesOf(card, field).some((value) => ticked.includes(value)));
      if (!card.hidden) shown += 1;
    }
    for (const group of area.querySelectorAll("[data-type-group]")) group.hidden = !group.querySelector("[data-type]:not([hidden])");
    const count = bar.querySelector("[data-type-filter-count]");
    count.textContent = filtering ? `${shown} of ${cards.length} card${cards.length === 1 ? "" : "s"} shown` : "";
    bar.hidden = [...bar.querySelectorAll("[data-filter-field]")].every((row) => row.hidden);
  }

  function refresh(root = document) {
    for (const bar of root.querySelectorAll("[data-type-filter]")) {
      const kept = chosen[bar.dataset.typeFilter];
      if (kept) {
        for (const row of bar.querySelectorAll("[data-filter-field]")) {
          const ticked = kept[row.dataset.filterField] || [];
          for (const input of row.querySelectorAll("input")) input.checked = ticked.includes(input.value);
        }
      }
      apply(bar);
    }
  }

  document.addEventListener("change", (event) => {
    const bar = event.target.closest("[data-type-filter]");
    if (bar) apply(bar);
  });
  window.typeFilters = { refresh };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => refresh());
  else refresh();
})();
