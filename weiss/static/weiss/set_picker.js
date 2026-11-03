// Set pickers (weiss/narrative_fields.html): typing filters the checklist (every word has to match, in any order),
// and the sets ticked show above it as chips, each with a × to untick it.
(() => {
  const words = (text) => text.toLowerCase().split(/\s+/).filter(Boolean);

  for (const picker of document.querySelectorAll("[data-set-picker]")) {
    const search = picker.querySelector("[data-set-search]");
    const items = [...picker.querySelectorAll("[data-set-list] li")];
    const chosen = picker.querySelector("[data-set-chosen]");
    const none = picker.querySelector("[data-set-none]");
    const nameOf = (item) => item.dataset.name;
    for (const item of items) item.dataset.text = item.textContent.toLowerCase();

    function showChosen() {
      chosen.replaceChildren(...items.filter((item) => item.querySelector("input").checked).map((item) => {
        const chip = document.createElement("li");
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "set-chip";
        remove.textContent = `${nameOf(item)} ×`;
        remove.setAttribute("aria-label", `Remove ${nameOf(item)}`);
        remove.addEventListener("click", () => {
          item.querySelector("input").checked = false;
          showChosen();
        });
        chip.appendChild(remove);
        return chip;
      }));
      chosen.hidden = !chosen.children.length;
    }

    function filter() {
      const wanted = words(search.value);
      let shown = 0;
      for (const item of items) {
        item.hidden = !wanted.every((word) => item.dataset.text.includes(word));
        if (!item.hidden) shown += 1;
      }
      none.hidden = shown > 0;
    }

    search.addEventListener("input", filter);
    // Enter in the search box ticks the only match, rather than sending the form.
    search.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      const visible = items.filter((item) => !item.hidden);
      if (visible.length === 1) {
        visible[0].querySelector("input").checked = true;
        search.value = "";
        filter();
        showChosen();
      }
    });
    // Only a box being ticked: the search box changes too, as it loses focus to a chip being clicked, and rebuilding
    // the chips then would take that chip away before its click lands.
    picker.addEventListener("change", (event) => { if (event.target.type === "checkbox") showChosen(); });
    showChosen();
  }
})();
