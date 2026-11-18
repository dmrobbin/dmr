/* The staff's quest editor (weiss/world_quest_edit.html): the quest's JSON, checked on the server as it's typed
   (world_staff_views.world_quest_check), with its mistakes and how the player's log will read it. Ctrl+S saves;
   leaving with unsaved changes asks first. */
(() => {
  const form = document.querySelector("[data-quest-editor]");
  if (!form) return;
  const text = form.querySelector("[data-quest-text]");
  const state = form.querySelector("[data-quest-state]");
  const problemsEl = form.querySelector("[data-quest-problems]");
  const preview = form.querySelector("[data-quest-preview]");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
  let timer = null;
  let asked = 0;
  let dirty = false;

  function showProblems(problems) {
    problemsEl.replaceChildren();
    if (!problems.length) return;
    const head = document.createElement("p");
    head.className = "small panel-error";
    head.textContent = `${problems.length} mistake${problems.length === 1 ? "" : "s"} to fix before it can be saved:`;
    const list = document.createElement("ul");
    for (const problem of problems) list.append(Object.assign(document.createElement("li"), { textContent: problem }));
    problemsEl.append(head, list);
  }

  // Quests it locks or requires that aren't written yet: it can be saved, but they're said.
  const notesEl = form.querySelector("[data-quest-notes]");
  function showNotes(notes) {
    notesEl.replaceChildren();
    if (!notes.length) return;
    const list = document.createElement("ul");
    list.className = "small";
    for (const note of notes) list.append(Object.assign(document.createElement("li"), { textContent: note }));
    notesEl.append(Object.assign(document.createElement("p"), { className: "small muted", textContent: "It can be saved, but:" }), list);
  }

  async function check() {
    const mine = ++asked;
    state.textContent = "Checking…";
    try {
      const body = new URLSearchParams({ quest: text.value, pk: form.dataset.pk || "" });
      const response = await fetch(form.dataset.checkUrl, { method: "POST", headers: { "X-CSRFToken": csrf }, body });
      const data = await response.json();
      if (mine !== asked) return; // a later check is on its way
      showProblems(data.problems);
      showNotes(data.notes || []);
      if (data.preview) preview.innerHTML = data.preview; // rendered (and escaped) by the server's template
      state.textContent = data.problems.length ? `${data.problems.length} mistake${data.problems.length === 1 ? "" : "s"}` : dirty ? "Unsaved, no mistakes" : "Checked";
    } catch {
      if (mine === asked) state.textContent = "Couldn't check: is the connection down?";
    }
  }

  text.addEventListener("input", () => {
    dirty = true;
    state.textContent = "Unsaved";
    clearTimeout(timer);
    timer = setTimeout(check, 450);
  });
  // Tab indents (two spaces) rather than leaving the box; Esc then Tab leaves it, for keyboard users.
  let escaped = false;
  text.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { escaped = true; return; }
    if (event.key === "Tab" && !event.shiftKey && !escaped) {
      event.preventDefault();
      text.setRangeText("  ", text.selectionStart, text.selectionEnd, "end");
      text.dispatchEvent(new Event("input"));
    }
    escaped = false;
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      dirty = false;
      form.requestSubmit();
    }
  });
  form.addEventListener("submit", () => { dirty = false; });
  window.addEventListener("beforeunload", (event) => {
    if (dirty) event.preventDefault();
  });
})();
