// The picture picker: find a card, then drag a circle over the part of its image to use.
// Positions are in widths of the card's image, the same as the server keeps them.
(() => {
  const root = document.querySelector("[data-avatar-picker]");
  if (!root) return;
  const $ = (selector) => root.querySelector(selector);
  const stage = $("[data-stage]");
  const image = $("[data-image]");
  const circle = $("[data-circle]");
  const size = $("[data-size]");
  const field = (name) => $(`[data-field="${name}"]`);
  const MIN_R = 0.08;
  const STEP = 0.01;

  let spot = null; // {x, y, r}
  let tall = 1; // the image's height, in widths
  let keep = null; // a saved circle to show when its card loads, instead of a new one

  function clamp() {
    spot.r = Math.max(MIN_R, Math.min(spot.r, 0.5, tall / 2));
    spot.x = Math.max(spot.r, Math.min(spot.x, 1 - spot.r));
    spot.y = Math.max(spot.r, Math.min(spot.y, tall - spot.r));
  }

  function show() {
    clamp();
    circle.style.left = `${(spot.x - spot.r) * 100}%`;
    circle.style.top = `${((spot.y - spot.r) / tall) * 100}%`;
    circle.style.width = `${spot.r * 200}%`;
    size.value = spot.r * 100;
    root.querySelectorAll("[data-preview] img").forEach((img) => {
      img.src = image.src;
      img.style.width = `${100 / (2 * spot.r)}%`;
      img.style.left = `${(-(spot.x - spot.r) / (2 * spot.r)) * 100}%`;
      img.style.top = `${(-(spot.y - spot.r) / (2 * spot.r)) * 100}%`;
    });
    for (const name of ["x", "y", "r"]) field(name).value = spot[name].toFixed(4);
  }

  function choose(pk, url, saved) {
    keep = saved || null;
    field("card").value = pk;
    $("[data-save]").disabled = true;
    image.src = url;
  }

  image.addEventListener("load", () => {
    tall = image.naturalHeight / image.naturalWidth;
    spot = keep || { x: 0.5, y: Math.min(tall / 2, 0.35), r: 0.3 };
    keep = null;
    size.min = MIN_R * 100;
    size.max = Math.min(50, tall * 50);
    stage.hidden = $("[data-size-label]").hidden = $("[data-preview-row]").hidden = false;
    $("[data-save]").disabled = false;
    $("[data-help]").textContent = "Drag the circle over the part you want.";
    show();
  });
  image.addEventListener("error", () => {
    stage.hidden = true;
    $("[data-save]").disabled = true;
    $("[data-help]").textContent = "That card's image couldn't be loaded. Try another.";
  });

  function moveTo(event) {
    const box = image.getBoundingClientRect();
    spot.x = (event.clientX - box.left) / box.width;
    spot.y = (event.clientY - box.top) / box.width;
    show();
  }
  let dragging = false;
  stage.addEventListener("pointerdown", (event) => {
    dragging = true;
    stage.setPointerCapture(event.pointerId);
    moveTo(event);
    event.preventDefault();
    circle.focus();
  });
  stage.addEventListener("pointermove", (event) => { if (dragging) moveTo(event); });
  for (const end of ["pointerup", "pointercancel"]) stage.addEventListener(end, () => { dragging = false; });

  circle.addEventListener("keydown", (event) => {
    const move = { ArrowLeft: [-STEP, 0], ArrowRight: [STEP, 0], ArrowUp: [0, -STEP], ArrowDown: [0, STEP] }[event.key];
    if (!move) return;
    event.preventDefault();
    spot.x += move[0];
    spot.y += move[1];
    show();
  });
  size.addEventListener("input", () => {
    spot.r = Number(size.value) / 100;
    show();
  });

  // Finding a card. Only the newest search's answer is shown.
  const results = $("[data-results]");
  const note = $("[data-search-note]");
  let timer = null;
  let latest = 0;

  function resultButton(card) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "avatar-result";
    button.title = `${card.name} (${card.serial})`;
    const img = document.createElement("img");
    img.src = card.image;
    img.alt = card.name;
    img.loading = "lazy";
    button.append(img);
    button.addEventListener("click", () => choose(card.pk, card.image));
    return button;
  }

  const seriesBox = $("[data-series]");
  const searchBox = $("[data-search]");

  async function search() {
    const mine = ++latest;
    const query = searchBox.value.trim();
    const series = seriesBox.value;
    if (query.length < 2 && !series) {
      results.replaceChildren();
      note.textContent = "Type at least 2 letters, or choose a series.";
      return;
    }
    try {
      const params = new URLSearchParams({ q: query.length < 2 ? "" : query, series });
      const response = await fetch(`${root.dataset.searchUrl}?${params}`, { credentials: "same-origin" });
      if (!response.ok) throw new Error(response.status);
      const { cards } = await response.json();
      if (mine !== latest) return;
      results.replaceChildren(...cards.map(resultButton));
      note.textContent = cards.length ? "" : "No cards found.";
    } catch (error) {
      if (mine === latest) note.textContent = "The search didn't work. Try again.";
    }
  }
  searchBox.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(search, 250);
  });
  seriesBox.addEventListener("change", () => {
    clearTimeout(timer);
    search();
  });

  const current = JSON.parse(document.getElementById("avatar-current").textContent);
  if (current) choose(current.card, current.image, { x: current.x, y: current.y, r: current.r });
})();
