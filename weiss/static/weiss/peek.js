// Hovering (or tabbing to) a card in a set grid shows its details beside it.
// Only on devices with a real pointer; on touch screens a tap still opens the card page.
(() => {
  if (!window.matchMedia("(hover: hover)").matches) return;
  const DELAY = 250; // ms, so sweeping the mouse across the grid doesn't flash every card
  const GAP = 12;
  let timer = null;
  let shown = null;

  function hide() {
    clearTimeout(timer);
    if (shown) shown.hidden = true;
    shown = null;
  }

  function show(item) {
    const peek = item.querySelector(".card-peek");
    if (!peek) return;
    if (shown && shown !== peek) shown.hidden = true;
    peek.hidden = false;
    shown = peek;

    // Beside the card on whichever side has room, kept inside the window.
    const card = item.getBoundingClientRect();
    const box = peek.getBoundingClientRect();
    let left = card.right + GAP;
    if (left + box.width > window.innerWidth - GAP) left = card.left - GAP - box.width;
    left = Math.max(GAP, left);
    let top = Math.min(card.top, window.innerHeight - box.height - GAP);
    top = Math.max(GAP, top);
    peek.style.left = `${left}px`;
    peek.style.top = `${top}px`;
  }

  document.querySelectorAll("[data-peek]").forEach((item) => {
    item.addEventListener("mouseenter", () => {
      clearTimeout(timer);
      timer = setTimeout(() => show(item), DELAY);
    });
    item.addEventListener("mouseleave", hide);
    item.addEventListener("focusin", () => show(item));
    item.addEventListener("focusout", hide);
  });
  window.addEventListener("scroll", hide, { passive: true });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") hide(); });
})();
