// Card-list buttons (− / +, create, edit, done) post in the background instead of reloading.
// The server answers with the re-rendered side panel; the running count and every card's
// copy count on the page are updated from it. If anything goes wrong, fall back to a normal post.
document.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-list-form]");
  if (!form) return;
  event.preventDefault();
  const buttons = form.querySelectorAll("button");
  buttons.forEach((b) => { b.disabled = true; });

  let data;
  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    data = await response.json();
  } catch (error) {
    form.submit();
    return;
  }

  // Creating or switching lists changes which controls the page should show, so reload it.
  if (form.dataset.listForm === "reload" && data.ok) {
    window.location.reload();
    return;
  }

  const panel = document.querySelector("[data-list-panel]");
  if (panel) {
    panel.innerHTML = data.panel;
    window.typeFilters?.refresh(panel); // its type chips, as they were
    showPanelSummary({ bump: true });
  }
  if (data.list) {
    document.querySelectorAll(`[data-deck-checks="${data.list}"]`).forEach((el) => { el.innerHTML = data.deck; });
  }
  if (data.card !== undefined) {
    document.querySelectorAll(`[data-qty-for="${data.card}"]`).forEach((el) => { el.textContent = data.quantity; });
  }
  // In a deck, names past the 4-copy limit get red buttons everywhere they appear on the page.
  const overLimit = new Set(data.over_limit || []);
  document.querySelectorAll("[data-qty-controls]").forEach((controls) => {
    const quantity = Number(controls.querySelector("[data-qty-for]").textContent);
    controls.querySelector('[data-delta="-1"]').disabled = quantity === 0;
    controls.querySelector('[data-delta="1"]').disabled = data.full;
    const over = overLimit.has(controls.dataset.cardName);
    controls.classList.toggle("over-limit", over);
    if (over) controls.title = "More than 4 copies of this card";
    else controls.removeAttribute("title");
  });
  if (form.dataset.listForm === "reload") buttons.forEach((b) => { b.disabled = false; });
});

// Phones and tablets: no mouse to hover with.
const touchScreen = window.matchMedia("(hover: none) and (pointer: coarse)");

// Cards in the panel open a small popup (picture, stats, text, +/-) instead of the full card page; so do the
// cards in a set on a touch screen, where there's no hovering over them to see them (data-card-popup-touch).
// Ctrl/Cmd/Shift/middle-click still open the full page as usual.
document.addEventListener("click", async (event) => {
  const link = event.target.closest("a[data-card-popup], a[data-card-popup-touch]");
  const dialog = document.querySelector("[data-card-popup-dialog]");
  if (!link || !dialog || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  const popup = link.dataset.cardPopup || (touchScreen.matches ? link.dataset.cardPopupTouch : "");
  if (!popup) return;
  event.preventDefault();
  dialog.classList.remove("zoomed");
  const url = new URL(popup, window.location.href);
  url.searchParams.set("next", window.location.pathname + window.location.search);
  try {
    const response = await fetch(url, { credentials: "same-origin" });
    if (!response.ok) throw new Error(response.status);
    dialog.querySelector("[data-card-popup-body]").innerHTML = await response.text();
  } catch (error) {
    window.location.href = link.href;
    return;
  }
  if (!dialog.open) dialog.showModal();
});

// Clicking the dimmed area outside the popup closes it. Clicking its picture fills the screen with it, and
// clicking again puts it back.
document.addEventListener("click", (event) => {
  if (event.target.matches("[data-card-popup-dialog]")) event.target.close();
  const dialog = event.target.closest("[data-card-popup-dialog]");
  if (dialog && event.target.matches(".card-popup-image")) dialog.classList.toggle("zoomed");
});
document.addEventListener("close", (event) => {
  if (event.target.matches && event.target.matches("[data-card-popup-dialog]")) event.target.classList.remove("zoomed");
}, true);

// Phones and tablets: the card lists panel is a drawer (site.css), opened and closed by the bar along the bottom
// of the screen. The bar shows the list being edited and its count, and flashes when a card goes in or out.
const panelToggle = document.querySelector("[data-list-panel-toggle]");

function showPanelSummary({ bump = false } = {}) {
  const panel = document.querySelector("[data-list-panel]");
  if (!panelToggle || !panel) return;
  const name = panel.querySelector(".panel-list-name a");
  const count = panel.querySelector(".deck-total, .list-counter");
  const summary = panelToggle.querySelector("[data-list-panel-summary]");
  summary.textContent = "";
  if (name) {
    if (count) {
      const strong = document.createElement("strong");
      strong.textContent = count.querySelector("strong")?.textContent || "";
      summary.append(strong, ` ${count.textContent.replace(strong.textContent, "").trim()} · `);
    }
    summary.append(name.textContent.trim());
  } else {
    summary.textContent = "Card lists";
  }
  if (bump && !panel.classList.contains("open")) {
    panelToggle.classList.remove("bumped");
    void panelToggle.offsetWidth; // start the flash again
    panelToggle.classList.add("bumped");
  }
}

function openPanel(open) {
  const panel = document.querySelector("[data-list-panel]");
  if (!panelToggle || !panel) return;
  panel.classList.toggle("open", open);
  panelToggle.setAttribute("aria-expanded", String(open));
  panelToggle.querySelector("[data-list-panel-hint]").textContent = open ? "Hide ▼" : "Show ▲";
}

if (panelToggle) {
  showPanelSummary();
  panelToggle.addEventListener("click", () => openPanel(panelToggle.getAttribute("aria-expanded") !== "true"));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && panelToggle.getAttribute("aria-expanded") === "true" && !document.querySelector("dialog[open]")) openPanel(false);
  });
}

// A set's filters on a phone: all but the name search are behind the Filters button, which says how many are in use.
document.querySelectorAll("[data-filters]").forEach((form) => {
  const toggle = form.querySelector("[data-filters-toggle]");
  if (!toggle) return;
  const inUse = [...form.querySelectorAll(".filter-extra")].reduce((n, el) => n
    + el.querySelectorAll("input[type=checkbox]:checked").length
    + [...el.querySelectorAll("input[type=search]")].filter((input) => input.value.trim()).length
    + [...el.querySelectorAll("select")].filter((select) => select.selectedIndex > 0).length, 0);
  const label = () => {
    const open = form.classList.contains("open");
    toggle.textContent = open ? "Hide filters" : `Filters${inUse ? ` (${inUse})` : ""}`;
    toggle.setAttribute("aria-expanded", String(open));
  };
  toggle.addEventListener("click", () => {
    form.classList.toggle("open");
    label();
  });
  label();
});
