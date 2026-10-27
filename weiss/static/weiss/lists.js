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
  if (data.card !== undefined) {
    document.querySelectorAll(`[data-qty-for="${data.card}"]`).forEach((el) => { el.textContent = data.quantity; });
  }
  document.querySelectorAll("[data-qty-controls]").forEach((controls) => {
    const quantity = Number(controls.querySelector("[data-qty-for]").textContent);
    controls.querySelector('[data-delta="-1"]').disabled = quantity === 0;
    controls.querySelector('[data-delta="1"]').disabled = data.full;
  });
  if (form.dataset.listForm === "reload") buttons.forEach((b) => { b.disabled = false; });
});
