// Menus with too many options to scroll through (all the sets): <select data-searchable="sets"> gets a search box
// before it. Typing hides the options that don't match (every word, in any order); the menu itself stays an
// ordinary one. If what's chosen stops matching, the first match is chosen instead, and Enter takes the first match,
// as if picked from the menu. Options with no value ("Any", "All series") always stay.
(() => {
  const words = (text) => text.toLowerCase().split(/\s+/).filter(Boolean);

  for (const select of document.querySelectorAll("select[data-searchable]")) {
    const options = [...select.options];
    const search = document.createElement("input");
    search.type = "search";
    search.className = "searchable-search";
    search.placeholder = `Search ${options.filter((o) => o.value).length} ${select.dataset.searchable || "options"}…`;
    search.setAttribute("aria-label", search.placeholder);
    search.autocomplete = "off";
    const count = document.createElement("span");
    count.className = "searchable-count muted small";
    count.setAttribute("aria-live", "polite");
    const box = document.createElement("span");
    box.className = "searchable";
    select.before(box);
    box.append(search, select, count);

    const matches = () => options.filter((o) => o.value && !o.hidden);

    function filter() {
      const wanted = words(search.value);
      for (const option of options) {
        option.hidden = Boolean(option.value) && !wanted.every((word) => option.text.toLowerCase().includes(word));
      }
      const shown = matches();
      count.textContent = wanted.length ? (shown.length ? `${shown.length} match${shown.length === 1 ? "" : "es"}` : "No matches") : "";
      if (select.selectedOptions[0] && select.selectedOptions[0].hidden && shown.length) select.value = shown[0].value;
    }

    search.addEventListener("input", filter);
    search.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault(); // picks, rather than sending the form
      const first = matches()[0];
      if (!first) return;
      select.value = first.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
})();
