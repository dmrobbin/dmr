// Card type chips (weiss/type_filter.html): show only the ticked types among the cards they're over, each marked
// data-type, and hide any group of cards (data-type-group) left with none showing. None ticked shows every card.
// The side panel is re-rendered after each +/- (lists.js calls typeFilters.refresh), so each bar's choice is kept here
// and put back on its new chips.
(() => {
  if (window.typeFilters) return; // a page can load this more than once, e.g. once for each kept deck it shows
  const chosen = {}; // a bar's data-type-filter -> the types ticked on it

  function apply(bar) {
    const key = bar.dataset.typeFilter;
    const area = document.querySelector(`[data-type-cards="${key}"]`);
    if (!area) return;
    const ticked = [...bar.querySelectorAll("input:checked")].map((input) => input.value);
    chosen[key] = ticked;
    const cards = [...area.querySelectorAll("[data-type]")];
    const present = new Set(cards.map((card) => card.dataset.type));
    for (const input of bar.querySelectorAll("input")) input.closest("label").hidden = !present.has(input.value) && !input.checked;
    let shown = 0;
    for (const card of cards) {
      card.hidden = ticked.length > 0 && !ticked.includes(card.dataset.type);
      if (!card.hidden) shown += 1;
    }
    for (const group of area.querySelectorAll("[data-type-group]")) group.hidden = !group.querySelector("[data-type]:not([hidden])");
    const count = bar.querySelector("[data-type-filter-count]");
    count.textContent = ticked.length ? `${shown} of ${cards.length} card${cards.length === 1 ? "" : "s"} shown` : "";
    bar.hidden = present.size < 2 && !ticked.length; // nothing to choose between
  }

  function refresh(root = document) {
    for (const bar of root.querySelectorAll("[data-type-filter]")) {
      const kept = chosen[bar.dataset.typeFilter];
      if (kept) for (const input of bar.querySelectorAll("input")) input.checked = kept.includes(input.value);
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
