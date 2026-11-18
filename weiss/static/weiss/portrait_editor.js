/* The portrait editor (weiss/portrait_editor.html): an art style and body, its choices (skin tone, hair and eye
   colour, expression), then a part for each slot, shown standing in a scene as you go. Undo and redo step through
   every change; Save posts the recipe (checked again by weiss.portraits.clean). Uses Portrait (portrait.js) to draw. */
(() => {
  const root = document.querySelector("[data-doll-editor]");
  if (!root) return;
  const editor = JSON.parse(document.getElementById("doll-editor").textContent);
  const saved = JSON.parse(document.getElementById("doll-recipe").textContent);
  const $ = (sel) => root.querySelector(sel);
  const controls = $("[data-controls]");
  const figure = $("[data-figure]");
  const backdrop = $("[data-backdrop]");
  const status = $("[data-status]");
  const undoButton = $("[data-undo]");
  const redoButton = $("[data-redo]");
  const saveButton = $("[data-save]");
  const field = $("[data-recipe-field]");
  const scenes = [...root.querySelectorAll("[data-scene]")];
  const moodButtons = [...root.querySelectorAll("[data-mood]")];

  // Which heading each choice and slot goes under.
  const GROUPS = [
    ["Body", ["skin", "ears"]],
    ["Hair", ["hair", "hair_front", "hair_back", "hair_side", "hair_extension", "ahoge"]],
    ["Face and expression", ["eyes:slot", "iris", "eyes", "sclera", "eye_state", "brows", "brow_state", "mouth", "mouth_state", "expression", "lipstick", "marks", "face"]],
    ["Outfit and accessories", ["outfit", "glasses", "earrings", "head", "neck", "mask", "hat"]],
  ];

  let kit = null;
  let manifest = null;
  let recipe = null;
  let history = [];
  let at = -1;
  let leaving = false;
  let mood = "";
  const savedJson = root.dataset.saved === "1" ? JSON.stringify(saved) : null; // null: nothing saved yet
  const say = (text) => { status.textContent = text; };
  const clone = (r) => JSON.parse(JSON.stringify(r));
  const baseOf = (r = recipe) => manifest.bases[r.base];
  const partsFor = (baseKey, slot) => manifest.parts.filter((p) => p.base === baseKey && p.slot === slot);
  const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const nearest = (options, hex) => options.reduce((best, o) => {
    const d = rgb(o.swatch).reduce((sum, v, i) => sum + (v - rgb(hex)[i]) ** 2, 0);
    return d < best[0] ? [d, o.key] : best;
  }, [Infinity, options[0].key])[1];

  // Make a recipe fit what's there: unknown choices and parts give way to the base's defaults.
  function fit(r) {
    r = kit.upgrade(clone(r));
    const removed = [];
    if (!manifest.bases[r.base]) r = clone({ base: editor.default_base, ...manifest.bases[editor.default_base].defaults });
    const base = baseOf(r);
    r.choices = r.choices || {};
    for (const choice of base.choices) {
      if (!choice.options.some((o) => o.key === r.choices[choice.key])) r.choices[choice.key] = base.defaults.choices[choice.key];
    }
    for (const key of Object.keys(r.choices)) if (!base.choices.some((c) => c.key === key)) delete r.choices[key];
    r.parts = r.parts || {};
    for (const [slot, pick] of Object.entries(r.parts)) {
      const part = pick && kit.parts.get(pick.id);
      if (!part || part.base !== r.base || part.slot !== slot || !base.slots.some((s) => s.key === slot)) {
        if (part) removed.push(part.name);
        delete r.parts[slot];
        continue;
      }
      const colours = (part.colors || []).map((c) => c.key);
      if (colours.length && !colours.includes(pick.color)) pick.color = colours[0];
      if (!colours.length) pick.color = "";
    }
    for (const slot of base.slots) {
      if (slot.required && !r.parts[slot.key] && base.defaults.parts[slot.key]) r.parts[slot.key] = { ...base.defaults.parts[slot.key] };
    }
    return [r, removed];
  }

  // ---- History ----

  function commit(next, note = "") {
    history = history.slice(0, at + 1);
    history.push(JSON.stringify(next));
    at = history.length - 1;
    recipe = next;
    refresh(note);
  }

  function step(by) {
    const to = at + by;
    if (to < 0 || to >= history.length) return;
    at = to;
    recipe = JSON.parse(history[at]);
    refresh(by < 0 ? "Undone." : "Redone.");
  }

  const change = (mutate) => {
    const next = clone(recipe);
    const note = mutate(next) || "";
    commit(next, note);
  };

  // A new base: its own parts from its defaults; the skin tone kept, the hair and eyes as near as it has.
  function switchTo(baseKey, next) {
    const from = baseOf(next);
    const to = manifest.bases[baseKey];
    const fresh = { base: baseKey, choices: { ...to.defaults.choices }, parts: clone(to.defaults.parts) };
    for (const choice of to.choices) {
      const old = from.choices.find((c) => c.key === choice.key);
      const value = next.choices[choice.key];
      if (choice.options.some((o) => o.key === value)) fresh.choices[choice.key] = value;
      else if (old && choice.kind === "swatch") {
        const was = old.options.find((o) => o.key === value);
        if (was) fresh.choices[choice.key] = nearest(choice.options, was.swatch);
      }
    }
    Object.assign(next, fresh);
  }

  // ---- Controls ----

  function fieldset(label, id) {
    const set = document.createElement("fieldset");
    set.className = "char-field";
    const legend = document.createElement("legend");
    if (id) legend.innerHTML = `<label for="${id}"></label>`;
    (legend.querySelector("label") || legend).textContent = label;
    set.append(legend);
    return [set, legend];
  }

  function radios(name, label, options, current, onPick, swatches) {
    const [set, legend] = fieldset(label);
    const chosen = document.createElement("span");
    chosen.className = "muted char-chosen";
    chosen.textContent = (options.find((o) => o.key === current) || {}).label || "";
    legend.append(chosen);
    const row = document.createElement("div");
    row.className = swatches ? "char-swatches" : "char-segments";
    for (const option of options) {
      const wrap = document.createElement("label");
      wrap.className = swatches ? "char-swatch" : "char-segment";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = name;
      input.value = option.key;
      input.checked = option.key === current;
      input.addEventListener("change", () => onPick(option.key));
      wrap.append(input);
      if (swatches) {
        const dot = document.createElement("span");
        dot.className = "char-dot";
        dot.style.setProperty("--swatch", option.swatch || "#777");
        const text = document.createElement("span");
        text.className = "visually-hidden";
        text.textContent = option.label;
        wrap.title = option.label;
        wrap.append(dot, text);
      } else {
        const text = document.createElement("span");
        text.textContent = option.label;
        wrap.append(text);
      }
      row.append(wrap);
    }
    set.append(row);
    return set;
  }

  // A dropdown with previous and next buttons beside it, for browsing quickly.
  function picker(id, label, options, current, onPick) {
    const [set] = fieldset(label, id);
    const select = document.createElement("select");
    select.id = id;
    for (const o of options) select.add(new Option(o.label, o.key, false, o.key === current));
    select.addEventListener("change", () => onPick(select.value));
    const nudge = (by, text) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "button-small secondary char-nudge";
      button.id = `${id}-${by > 0 ? "next" : "prev"}`;
      button.setAttribute("aria-label", `${by > 0 ? "Next" : "Previous"} ${label.toLowerCase()}`);
      button.textContent = text;
      button.disabled = options.length < 2;
      button.addEventListener("click", () => {
        const i = options.findIndex((o) => o.key === select.value);
        onPick(options[(i + by + options.length) % options.length].key);
      });
      return button;
    };
    const row = document.createElement("div");
    row.className = "char-pick";
    row.append(nudge(-1, "‹"), select, nudge(1, "›"));
    set.append(row);
    return set;
  }

  function choiceControl(choice) {
    const current = recipe.choices[choice.key];
    const pick = (value) => change((next) => { next.choices[choice.key] = value; });
    return choice.kind === "swatch"
      ? radios(`doll-choice-${choice.key}`, choice.label, choice.options, current, pick, true)
      : picker(`doll-choice-${choice.key}`, choice.label, choice.options, current, pick);
  }

  function slotControl(slot) {
    const options = partsFor(recipe.base, slot.key);
    if (!options.length) return null;
    const pick = recipe.parts[slot.key];
    const choices = [...(slot.required ? [] : [{ key: "", label: "None" }]), ...options.map((p) => ({ key: p.id, label: p.name }))];
    const set = picker(`doll-slot-${slot.key}`, slot.label, choices, pick ? pick.id : "", (id) => change((next) => {
      if (!id) {
        delete next.parts[slot.key];
        return;
      }
      const part = kit.parts.get(id);
      const colours = (part.colors || []).map((c) => c.key);
      const keep = next.parts[slot.key] && colours.includes(next.parts[slot.key].color) ? next.parts[slot.key].color : colours[0] || "";
      next.parts[slot.key] = { id, color: keep };
    }));
    const part = pick && kit.parts.get(pick.id);
    if (part && part.colors && part.colors.length > 1) {
      set.append(radios(`doll-colour-${slot.key}`, "Colour", part.colors, pick.color,
        (value) => change((next) => { next.parts[slot.key].color = value; }), true));
    }
    return set;
  }

  function build() {
    const active = document.activeElement;
    const focusId = active && controls.contains(active) ? active.id : null;
    const focusRadio = active && active.type === "radio" ? active.name : null;
    controls.replaceChildren();
    const base = baseOf();

    // The style and body: each pair is a base.
    const styles = [...new Set(Object.values(manifest.bases).map((b) => b.style))];
    const bodies = Object.entries(manifest.bases).filter(([, b]) => b.style === base.style);
    const top = document.createElement("div");
    top.className = "char-group";
    top.append(
      radios("doll-style", "Art style", styles.map((s) => ({ key: s, label: s })), base.style, (style) => {
        if (style === base.style) return;
        change((next) => {
          const same = Object.entries(manifest.bases).find(([, b]) => b.style === style && b.label === base.label)
            || Object.entries(manifest.bases).find(([, b]) => b.style === style);
          switchTo(same[0], next);
          return `Now in ${style}'s style: its own parts. Your skin tone came along; undo goes back.`;
        });
      }, false),
      radios("doll-body", "Body", bodies.map(([key, b]) => ({ key, label: b.label })), recipe.base, (key) => {
        if (key === recipe.base) return;
        change((next) => {
          switchTo(key, next);
          return `Switched to ${manifest.bases[key].label.toLowerCase()}: its own parts. Undo goes back.`;
        });
      }, false),
    );
    controls.append(top);

    const placed = new Set();
    for (const [heading, keys] of GROUPS) {
      const group = document.createElement("div");
      group.className = "char-group";
      const h = document.createElement("h2");
      h.textContent = heading;
      const items = [];
      for (const key of keys) {
        const slotKey = key.endsWith(":slot") ? key.slice(0, -5) : key;
        const choice = !key.endsWith(":slot") && base.choices.find((c) => c.key === key);
        if (choice && !placed.has(`c:${key}`)) {
          placed.add(`c:${key}`);
          items.push(choiceControl(choice));
        }
        const slot = (key.endsWith(":slot") || !choice) && base.slots.find((s) => s.key === slotKey);
        if (slot && !placed.has(`s:${slotKey}`)) {
          placed.add(`s:${slotKey}`);
          items.push(slotControl(slot));
        }
      }
      const shown = items.filter(Boolean);
      if (shown.length) {
        group.append(h, ...shown);
        controls.append(group);
      }
    }
    // Anything a style has that no heading names, at the end.
    const rest = [...base.choices.filter((c) => !placed.has(`c:${c.key}`)).map(choiceControl),
      ...base.slots.filter((s) => !placed.has(`s:${s.key}`)).map(slotControl)].filter(Boolean);
    if (rest.length) {
      const group = document.createElement("div");
      group.className = "char-group";
      const h = document.createElement("h2");
      h.textContent = "More";
      group.append(h, ...rest);
      controls.append(group);
    }
    if (focusId && document.getElementById(focusId)) document.getElementById(focusId).focus();
    else if (focusRadio) controls.querySelector(`input[name="${focusRadio}"]:checked`)?.focus();
  }

  function draw() {
    kit.draw(figure, recipe, mood ? { mood } : {});
    const moods = baseOf().moods || {};
    for (const button of moodButtons) {
      const key = button.dataset.mood;
      button.hidden = Boolean(key) && !moods[key];
      button.setAttribute("aria-pressed", String(key === mood));
    }
  }

  function refresh(note = "") {
    build();
    draw();
    undoButton.disabled = at <= 0;
    redoButton.disabled = at >= history.length - 1;
    const json = JSON.stringify(recipe);
    saveButton.disabled = savedJson !== null && json === savedJson;
    field.value = json;
    say(note);
  }

  function randomise() {
    const pick = (list) => list[Math.floor(Math.random() * list.length)];
    change((next) => {
      const base = baseOf(next);
      for (const choice of base.choices) {
        // Expressions stay as they are: a random face is rarely a good one.
        if (choice.kind === "swatch") next.choices[choice.key] = pick(choice.options).key;
      }
      next.parts = {};
      for (const slot of base.slots) {
        const options = partsFor(next.base, slot.key);
        if (!options.length) continue;
        const odds = { hair_back: 0.85, hair_extension: 0.3, ahoge: 0.15, glasses: 0.2, head: 0.15, neck: 0.3, face: 0.15, hair_side: 0.3,
          earrings: 0.3, mask: 0.05, hat: 0.15, marks: 0.1, lipstick: 0.2 }[slot.key] ?? 1;
        if (!slot.required && Math.random() >= odds) continue;
        const part = slot.key === "expression" && base.defaults.parts.expression ? kit.parts.get(base.defaults.parts.expression.id) : pick(options);
        next.parts[slot.key] = { id: part.id, color: part.colors ? pick(part.colors).key : "" };
      }
      return "A new look. Undo goes back to the last one.";
    });
  }

  function showIn(scene) {
    backdrop.dataset.bg = scene;
    backdrop.innerHTML = window.SceneBackdrops ? SceneBackdrops.draw(scene) : "";
    for (const button of scenes) button.setAttribute("aria-pressed", String(button.dataset.scene === scene));
  }

  async function start() {
    controls.innerHTML = '<p class="muted">Loading the parts…</p>';
    try {
      kit = await Portrait.load(root.dataset.manifest);
      manifest = kit.manifest;
    } catch {
      controls.innerHTML = "";
      const message = document.createElement("p");
      message.textContent = "The parts couldn't be loaded. Check your connection and try again.";
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "button-small";
      retry.textContent = "Try again";
      retry.addEventListener("click", start);
      controls.append(message, retry);
      return;
    }
    const [first, off] = fit(saved);
    history = [JSON.stringify(first)];
    at = 0;
    recipe = first;
    refresh(off.length ? `${off.join(", ")} ${off.length === 1 ? "isn't" : "aren't"} available any more, so ${off.length === 1 ? "it's" : "they've"} been taken off.` : "");
  }

  scenes.forEach((button) => button.addEventListener("click", () => showIn(button.dataset.scene)));
  moodButtons.forEach((button) => button.addEventListener("click", () => {
    mood = button.dataset.mood;
    draw();
  }));
  undoButton.addEventListener("click", () => step(-1));
  redoButton.addEventListener("click", () => step(1));
  $("[data-randomise]").addEventListener("click", () => kit && randomise());
  document.addEventListener("keydown", (event) => {
    if (!(event.ctrlKey || event.metaKey) || event.altKey) return;
    if (event.target.matches("input[type=text], input[type=search], textarea")) return;
    const key = event.key.toLowerCase();
    if (key === "z" && !event.shiftKey) step(-1);
    else if ((key === "z" && event.shiftKey) || key === "y") step(1);
    else return;
    event.preventDefault();
  });
  $("[data-save-form]").addEventListener("submit", () => {
    leaving = true;
    field.value = JSON.stringify(recipe);
  });
  document.querySelectorAll("[data-leave]").forEach((el) => el.addEventListener("click", () => { leaving = true; }));
  window.addEventListener("beforeunload", (event) => {
    if (leaving || !recipe || saveButton.disabled || (savedJson === null && at === 0)) return;
    event.preventDefault();
  });
  showIn(scenes[0] ? scenes[0].dataset.scene : "classroom");
  start();
})();
