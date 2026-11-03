// The scene editor: the reference's examples go into the script where the cursor is (a whole line of its own, for
// those marked data-whole-line), the script is checked as it's typed (the server compiles it; nothing is saved), a
// mistake's line number or a label jumps to its line, the lines on the left can be searched, the palette's parts on
// the right stay open or closed as they were left, and Ctrl+S saves (Ctrl+Enter saves and plays).
(() => {
  const form = document.querySelector("[data-scene-editor]");
  if (!form) return;
  const script = form.querySelector("[data-scene-script]");
  const problems = form.querySelector("[data-scene-problems]");
  const labels = form.querySelector("[data-scene-labels]");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  const gutter = form.querySelector("[data-scene-gutter]");
  const saveState = form.querySelector("[data-save-state]");
  let timer = null;
  let dirty = false;

  function markDirty(now) {
    dirty = now;
    saveState.textContent = now ? "Unsaved changes" : "Saved";
    saveState.classList.toggle("unsaved", now);
  }

  // The palette's parts: open or closed as they were last left, in this browser.
  const PARTS_KEY = "weiss-scene-palette";
  let parts = {};
  try { parts = JSON.parse(localStorage.getItem(PARTS_KEY)) || {}; } catch (error) { /* as the page has them */ }
  for (const part of form.querySelectorAll("[data-part]")) {
    if (part.dataset.part in parts) part.open = parts[part.dataset.part];
    part.addEventListener("toggle", () => {
      parts[part.dataset.part] = part.open;
      try { localStorage.setItem(PARTS_KEY, JSON.stringify(parts)); } catch (error) { /* only this visit, then */ }
    });
  }

  // The lines on the left, narrowed to those whose example or meaning has every word typed.
  const linesSearch = form.querySelector("[data-lines-search]");
  linesSearch.addEventListener("input", () => {
    const words = linesSearch.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const line of form.querySelectorAll("[data-lines] [data-search]")) {
      line.hidden = !words.every((word) => line.dataset.search.includes(word));
      shown += !line.hidden;
    }
    form.querySelector("[data-lines-none]").hidden = shown > 0;
  });
  linesSearch.addEventListener("keydown", (event) => { if (event.key === "Enter") event.preventDefault(); });

  // The backgrounds to choose from, each drawn small (backdrops.js), still.
  if (window.SceneBackdrops) {
    for (const art of form.querySelectorAll("[data-backdrop]")) art.innerHTML = window.SceneBackdrops.draw(art.dataset.backdrop);
  }

  // The line numbers beside the script: as many as it has lines, those with mistakes marked (from the list of them).
  function numberLines() {
    const count = script.value.split("\n").length;
    const wrong = new Set([...problems.querySelectorAll("[data-line]")].map((button) => Number(button.dataset.line)));
    if (gutter.children.length !== count || gutter.dataset.wrong !== [...wrong].join()) {
      gutter.replaceChildren(...Array.from({ length: count }, (_, i) => {
        const number = document.createElement("span");
        number.textContent = i + 1;
        if (wrong.has(i + 1)) number.className = "scene-line-error";
        return number;
      }));
      gutter.dataset.wrong = [...wrong].join();
    }
    gutter.scrollTop = script.scrollTop;
  }

  // A whole line goes on a line of its own: after the line the cursor is on, if that has something on it.
  function insert(text, wholeLine = false) {
    let { selectionStart: start, selectionEnd: end, value } = script;
    if (wholeLine) {
      text = text.replace(/\n$/, "");
      const lineEnd = value.indexOf("\n", end) === -1 ? value.length : value.indexOf("\n", end);
      const lineStart = value.lastIndexOf("\n", start - 1) + 1;
      if (value.slice(lineStart, lineEnd).trim()) {
        start = end = lineEnd;
        text = `\n${text}`;
      }
      if (value[end] !== "\n") text += "\n";
    }
    script.value = value.slice(0, start) + text + value.slice(end);
    script.selectionStart = script.selectionEnd = start + text.length - (wholeLine && text.endsWith("\n") ? 1 : 0);
    script.focus();
    changed();
  }

  function goToLine(number) {
    const lines = script.value.split("\n");
    const start = lines.slice(0, number - 1).reduce((total, line) => total + line.length + 1, 0);
    script.focus();
    script.setSelectionRange(start, start + (lines[number - 1] || "").length);
    // Scroll the textarea so the line is in view: lines are all the same height.
    const lineHeight = parseFloat(getComputedStyle(script).lineHeight) || 20;
    script.scrollTop = Math.max(0, (number - 4) * lineHeight);
  }

  async function check() {
    const body = new FormData();
    body.append("script", script.value);
    try {
      const response = await fetch(form.dataset.checkUrl, { method: "POST", body, headers: { "X-CSRFToken": csrf }, credentials: "same-origin" });
      if (!response.ok) return;
      const data = await response.json();
      problems.innerHTML = data.errors.length
        ? `<p class="small panel-error">${data.errors.length} mistake${data.errors.length === 1 ? "" : "s"} to fix before it can be played:</p>
           <ul>${data.errors.map(([line, message]) => `<li><button type="button" class="link-button" data-line="${line}">Line ${line}</button> ${esc(message)}</li>`).join("")}</ul>`
        : '<p class="small muted">No mistakes.</p>';
      showLabels(data.labels);
      numberLines();
    } catch (error) { /* offline for a moment: the next change checks again */ }
  }

  // The labels, each a button to its line.
  function showLabels(names) {
    labels.innerHTML = names.length ? `Labels: ${names.map((name) => `<button type="button" class="link-button" data-label="${esc(name)}">${esc(name)}</button>`).join(", ")}` : "";
  }

  function labelLine(name) {
    const lines = script.value.split("\n");
    const at = lines.findIndex((line) => line.trim().toLowerCase() === `label ${name}`);
    return at + 1;
  }

  function changed() {
    markDirty(true);
    clearTimeout(timer);
    timer = setTimeout(check, 500);
  }

  script.addEventListener("input", changed);
  script.addEventListener("input", numberLines);
  script.addEventListener("scroll", () => { gutter.scrollTop = script.scrollTop; });
  // Resizing the textarea (its corner handle) changes how much of the gutter shows.
  new ResizeObserver(() => { gutter.style.height = `${script.offsetHeight}px`; gutter.scrollTop = script.scrollTop; }).observe(script);
  numberLines();
  showLabels((labels.dataset.labels || "").split(",").filter(Boolean));
  form.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-insert]");
    if (chip) insert(chip.dataset.insert, "wholeLine" in chip.dataset);
    const line = event.target.closest("[data-line]");
    if (line) goToLine(Number(line.dataset.line));
    const label = event.target.closest("[data-label]");
    if (label && labelLine(label.dataset.label)) goToLine(labelLine(label.dataset.label));
  });
  form.addEventListener("submit", () => { dirty = false; });
  form.querySelector("[name=name]").addEventListener("input", () => markDirty(true));
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      form.requestSubmit();
    }
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      form.requestSubmit(form.querySelector("[data-save-play]"));
    }
  });
  window.addEventListener("beforeunload", (event) => { if (dirty) event.preventDefault(); });
})();
