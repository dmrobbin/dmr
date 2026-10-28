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
  if (panel) panel.innerHTML = data.panel;
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

// Cards in the panel open a small popup (picture, stats, text, +/-) instead of the full card page.
// Ctrl/Cmd/Shift/middle-click still open the full page as usual.
document.addEventListener("click", async (event) => {
  const link = event.target.closest("a[data-card-popup]");
  const dialog = document.querySelector("[data-card-popup-dialog]");
  if (!link || !dialog || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  const url = new URL(link.dataset.cardPopup, window.location.href);
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

// Clicking the dimmed area outside the popup closes it.
document.addEventListener("click", (event) => {
  if (event.target.matches("[data-card-popup-dialog]")) event.target.close();
});
