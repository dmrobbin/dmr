// The scene editor: the reference's examples go into the script where the cursor is, the script is checked
// as it's typed (the server compiles it; nothing is saved), a mistake's line number jumps to that line,
// and Ctrl+S saves.
(() => {
  const form = document.querySelector("[data-scene-editor]");
  if (!form) return;
  const script = form.querySelector("[data-scene-script]");
  const problems = form.querySelector("[data-scene-problems]");
  const labels = form.querySelector("[data-scene-labels]");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  const gutter = form.querySelector("[data-scene-gutter]");
  let timer = null;
  let dirty = false;

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

  function insert(text) {
    const { selectionStart: start, selectionEnd: end, value } = script;
    script.value = value.slice(0, start) + text + value.slice(end);
    script.selectionStart = script.selectionEnd = start + text.length;
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
      labels.textContent = data.labels.length ? `Labels: ${data.labels.join(", ")}` : "";
      numberLines();
    } catch (error) { /* offline for a moment: the next change checks again */ }
  }

  function changed() {
    dirty = true;
    clearTimeout(timer);
    timer = setTimeout(check, 500);
  }

  script.addEventListener("input", changed);
  script.addEventListener("input", numberLines);
  script.addEventListener("scroll", () => { gutter.scrollTop = script.scrollTop; });
  // Resizing the textarea (its corner handle) changes how much of the gutter shows.
  new ResizeObserver(() => { gutter.style.height = `${script.offsetHeight}px`; gutter.scrollTop = script.scrollTop; }).observe(script);
  numberLines();
  form.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-insert]");
    if (chip) insert(chip.dataset.insert);
    const line = event.target.closest("[data-line]");
    if (line) goToLine(Number(line.dataset.line));
  });
  form.addEventListener("submit", () => { dirty = false; });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  window.addEventListener("beforeunload", (event) => { if (dirty) event.preventDefault(); });
})();
