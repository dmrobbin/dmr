/* The duel's versus intro and its rock, paper, scissors reveal (docs/duel-presentation-plan.md, part 1). play.js builds
   the intro with WeissVersus.intro and keeps its plain screen for when this file isn't there.

   Everything here skips: a click, or Enter, Space or Escape, jumps an animation to its end state, and nothing makes the
   player wait to act. With animations off (play.js's setting, or reduced motion) the end state is shown at once, with
   the words. A CPU with no image or picture gets a crest: its initial on a disc in its deck colours. */
(() => {
  const STEPS = { arrive: 300, impact: 1000, ribbon: 1200, line: 1400 }; // ms from the start, see the plan
  const TYPE_MS = 22; // per character of their line
  const SHAKE_MS = 900; // the rock, paper, scissors hands: three shakes
  const FIST = "✊"; // the hand shown while they shake
  // Weiss Schwarz's colours, as the deck's colours come from the server.
  const COLOURS = { Red: "#c8453c", Blue: "#2f72c4", Yellow: "#d9a620", Green: "#3d9a55", Purple: "#8052b8", White: "#d8d8de", Black: "#2a2a33" };
  const FALLBACK = ["#7a4f9a", "#2f5f8f", "#9a3b4a", "#3b7a6a", "#8a6a2a", "#4a5a8a"];
  const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // An element from a tag, its attributes (false and null are left out) and its children (text or elements).
  function make(tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === null || value === undefined || value === false) continue;
      el.setAttribute(key, value === true ? "" : String(value));
    }
    el.append(...children.flat().filter((child) => child !== null && child !== undefined && child !== false));
    return el;
  }

  const hashOf = (text) => [...text].reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) >>> 0, 7);

  // Two colours for a side: its deck's colours, else a pair picked from its name, so every CPU has its own disc.
  function coloursOf(list, name) {
    const known = (list || []).map((colour) => COLOURS[colour]).filter(Boolean);
    if (known.length >= 2) return known.slice(0, 2);
    if (known.length === 1) return [known[0], "#1b1b24"];
    const hash = hashOf(name || "?");
    return [FALLBACK[hash % FALLBACK.length], FALLBACK[(hash + 2) % FALLBACK.length]];
  }

  // The crest: the first letter of the name on a disc in the two colours.
  function crest(name, colours) {
    const initial = [...String(name || "?").trim()][0] || "?";
    const el = make("span", { class: "versus-crest", role: "img", "aria-label": name });
    el.style.setProperty("--crest-a", colours[0]);
    el.style.setProperty("--crest-b", colours[1]);
    el.append(make("span", { class: "versus-crest-initial", "aria-hidden": "true" }, initial.toUpperCase()));
    return el;
  }

  // A side's portrait: its image, else its picture (an avatar: the picture's place in the frame is in percent), else a crest.
  function portrait(name, colours, image, picture) {
    if (image) return make("img", { class: "versus-art", src: image, alt: "" });
    if (picture && picture.image) {
      const img = make("img", { src: picture.image, alt: "" });
      img.style.width = `${Number(picture.width) || 100}%`;
      img.style.left = `${Number(picture.left) || 0}%`;
      img.style.top = `${Number(picture.top) || 0}%`;
      return make("span", { class: "avatar versus-picture", role: "img", "aria-label": name }, img);
    }
    return crest(name, colours);
  }

  // The versus intro. cpu: the CPU's payload ({name, image, picture, intro}); versus: the payload's versus block, or null
  // (then the sides are the CPU and "You"); ribbon: what's at stake, or null; animations: play.js's setting.
  // Returns the overlay, with its Begin button (data-act intro_done, which play.js sends as before).
  function intro({ cpu, versus, ribbon, animations, onImpact }) {
    const me = (versus && versus.me) || { name: "You", colors: [], deck: "", picture: null };
    const them = (versus && versus.them) || { name: cpu.name, picture: cpu.picture, image: cpu.image, deck: "", colors: [], title: "" };
    const meColours = coloursOf(me.colors, me.name);
    const themColours = coloursOf(them.colors, them.name);
    const line = cpu.intro || "";
    const side = (kind, colours, who, caption) => {
      const el = make("div", { class: `versus-side versus-${kind}` }, make("div", { class: "versus-portrait" }, portrait(who.name, colours, who.image || "", who.picture)), caption);
      el.style.setProperty("--side-a", colours[0]);
      el.style.setProperty("--side-b", colours[1]);
      return el;
    };
    const themSide = side("them", themColours, { ...them, image: them.image || cpu.image }, make("div", { class: "versus-caption" },
      make("h2", { class: "cpu-intro-name" }, them.name),
      them.title ? make("p", { class: "versus-title" }, them.title) : null,
      them.deck ? make("p", { class: "versus-deck" }, them.deck) : null));
    const meSide = side("me", meColours, me, make("div", { class: "versus-caption" },
      make("p", { class: "versus-name" }, me.name),
      me.deck ? make("p", { class: "versus-deck" }, me.deck) : null));
    // Who's speaking is named above their line; the bubble's tail points up, towards their side.
    const speaker = make("p", { class: "versus-speaker" }, cpu.name);
    const speech = make("p", { class: "cpu-speech versus-line" });
    const begin = make("button", { type: "button", class: "button-small versus-begin", "data-act": '{"type":"intro_done"}', hidden: true }, "Begin");
    // The seam between the two halves, on the desktop: one line from the top of the join to the bottom (the same
    // proportions as the sides' clip paths). On a phone the two sides are bands, and the slash is drawn across them.
    const seam = make("div");
    seam.innerHTML = '<svg class="versus-seam" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><line x1="62" y1="0" x2="38" y2="100" vector-effect="non-scaling-stroke"/></svg>';
    const overlay = make("div", { class: "cpu-intro versus", role: "dialog", "aria-label": `${cpu.name} challenges you` },
      make("div", { class: "versus-stage" },
        make("div", { class: "versus-slash", "aria-hidden": "true" }), // phone only: the band's slash, under the sides
        themSide, meSide,
        seam.firstElementChild,
        make("div", { class: "versus-vs", "aria-hidden": "true" }, "VS"),
        ribbon ? make("p", { class: "versus-ribbon" }, ribbon) : null,
        make("div", { class: "versus-foot" }, speaker, speech, begin)));

    const timers = [];
    let typing = null;
    let ready = false;
    const later = (ms, action) => timers.push(setTimeout(action, ms));
    const stop = () => {
      timers.forEach(clearTimeout);
      timers.length = 0;
      if (typing) clearInterval(typing);
      typing = null;
      document.removeEventListener("keydown", onKey, true);
    };

    // Their line types out, then Begin appears and takes focus.
    function reveal() {
      if (ready) return;
      ready = true;
      stop();
      overlay.classList.add("is-split", "is-arrived", "is-impact", "is-ribbon", "is-line", "is-ready");
      speech.textContent = line;
      begin.hidden = false;
      setTimeout(() => begin.focus({ preventScroll: true }), 0); // after it's in the page: an intro built with animations off is attached after this

    }
    function typeLine() {
      overlay.classList.add("is-line");
      let index = 0;
      typing = setInterval(() => {
        index += 1;
        speech.textContent = line.slice(0, index);
        if (index >= line.length) { clearInterval(typing); typing = null; reveal(); }
      }, TYPE_MS);
      if (!line) reveal();
    }
    // Skipping jumps to the end: every stage at once, the whole line, Begin ready.
    function skip() {
      if (ready) return;
      reveal();
    }
    function onKey(event) {
      if (!overlay.isConnected) { stop(); return; }
      if (event.key === "Escape" && ready) return;
      if (!["Enter", " ", "Escape"].includes(event.key)) return;
      if (ready) return; // Enter or Space on the focused Begin is its click
      event.preventDefault();
      event.stopPropagation();
      skip();
    }
    overlay.addEventListener("click", (event) => {
      if (event.target.closest(".versus-begin")) return;
      skip();
    });
    // Begin: the panels slide apart while play.js sends the start (the overlay is removed when the board shows).
    begin.addEventListener("click", () => {
      overlay.classList.add("is-leaving");
      overlay.style.pointerEvents = "none";
      stop();
    });
    overlay._stop = stop;

    if (!animations || reduced()) overlay.classList.add("no-motion");
    if (animations && !reduced()) {
      document.addEventListener("keydown", onKey, true);
      later(STEPS.arrive, () => overlay.classList.add("is-split", "is-arrived"));
      later(STEPS.impact, () => { overlay.classList.add("is-impact"); if (onImpact) onImpact(); });
      later(STEPS.ribbon, () => overlay.classList.add("is-ribbon"));
      later(STEPS.line, typeLine);
    } else {
      reveal();
    }
    // Shown from the first frame: the split is the first thing in the animation.
    overlay.classList.add("is-split");
    return overlay;
  }

  // Removes an intro. One that's been begun slides off first, so a player who pressed Begin sees the board come in.
  function close(el) {
    if (!el) return;
    if (el._stop) el._stop();
    if (el.classList.contains("is-leaving") && !reduced()) {
      el.addEventListener("transitionend", () => el.remove(), { once: true });
      setTimeout(() => el.remove(), 700);
    } else {
      el.remove();
    }
  }

  // Game 1's rock, paper, scissors result: once both have picked, the hands shake three times, then the banner. Returns
  // a function that finishes it at once (a click or a key does too), or null when there's nothing to animate.
  function rpsReveal(modal, { animations }) {
    const hands = [...modal.querySelectorAll(".rps-hand .rps-symbol")];
    const banner = modal.querySelector(".rps-result");
    if (!animations || reduced() || !hands.length || !banner) return null;
    const finals = hands.map((hand) => hand.textContent);
    banner.hidden = true;
    hands.forEach((hand) => { hand.textContent = FIST; hand.classList.add("rps-shaking"); });
    let timer = null;
    const finish = () => {
      clearTimeout(timer);
      document.removeEventListener("keydown", onRpsKey, true);
      modal.removeEventListener("click", finish);
      hands.forEach((hand, index) => { hand.textContent = finals[index]; hand.classList.remove("rps-shaking"); });
      banner.hidden = false;
    };
    function onRpsKey(event) {
      if (!modal.isConnected) { finish(); return; }
      if (["Enter", " ", "Escape"].includes(event.key)) { event.preventDefault(); finish(); }
    }
    timer = setTimeout(finish, SHAKE_MS);
    modal.addEventListener("click", finish);
    document.addEventListener("keydown", onRpsKey, true);
    return finish;
  }

  window.WeissVersus = { intro, close, rpsReveal };
})();
