/* ScenePlayer: plays a visual novel scene compiled by weiss.scenes (scene_payload) in an element of the page.

     const player = new ScenePlayer(element, payload, { playerName, onStep, onChoice, onEnd });
     player.start();            // from the top, or player.start("label")

   onStep(step, state) is called as each step begins, onChoice(step, option) when the player picks, and
   onEnd(state) when the scene ends. With decide(step, at, visit, i), a choice is a vote: the option clicked (i) is
   sent, and the scene waits on the promise it returns for the option decided (a co-op challenge's event, where both
   players vote; visit counts how often that choice has come up, so one that comes round again is a new vote).
   state is { line, flags: [...], choices: [{ line, prompt, text }], buffs }.
   buffs are those the scene gave (weiss.buffs), [{ step, option, buff, name }]: step is where in scene.steps,
   and option which of its options (null for a plain "give"), for the server to check them against the scene.
   fights are the fights it picked ("fight"), [{ step, option, who, name }], the same way: the last one counts.
   Stage directions (entering, moving, animating) play while the script carries on, one after another for
   each actor; dialogue waits for a click (or Space / Enter / →), and a choice for an option (or its number). */
(() => {
  const PLACES = { "far-left": 12, left: 28, center: 50, right: 72, "far-right": 88 };
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const TYPE_MS = 24; // per character of dialogue
  const RUNAWAY = 2000; // steps in a row with nothing to wait for: a goto loop
  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  // The animations an actor can do: keyframes for its body, how long, and how to ease.
  const repeat = (times, frames) => Array.from({ length: times }, () => frames).flat();
  const ANIMATIONS = {
    shake: { frames: [0, -14, 14, -10, 10, -5, 5, 0].map((x) => ({ transform: `translateX(${x}px)` })), ms: 500 },
    tremble: { frames: [...repeat(8, [{ transform: "translate(-2px, 1px)" }, { transform: "translate(2px, -1px)" }]), { transform: "none" }], ms: 800 },
    bounce: { frames: [0, -28, 0, -12, 0].map((y) => ({ transform: `translateY(${y}px)` })), ms: 650, easing: "ease-out" },
    jump: { frames: [{ transform: "none" }, { transform: "translateY(-70px)", offset: 0.4, easing: "ease-in" }, { transform: "scale(1.04, .94)", offset: 0.85 }, { transform: "none" }], ms: 600, easing: "ease-out" },
    nod: { frames: [0, 5, -2, 3, 0].map((r) => ({ transform: `rotate(${r}deg)` })), ms: 600 },
    spin: { frames: [{ transform: "rotateY(0deg)" }, { transform: "rotateY(360deg)" }], ms: 700, easing: "ease-in-out" },
    flip: { frames: [{ transform: "none" }, { transform: "translateY(-80px) rotate(-180deg)", offset: 0.5 }, { transform: "translateY(0) rotate(-360deg)" }], ms: 800, easing: "ease-in-out" },
    pulse: { frames: [1, 1.08, 1, 1.08, 1].map((s) => ({ transform: `scale(${s})` })), ms: 800 },
    flash: { frames: [{ filter: "brightness(1)" }, { filter: "brightness(2.4)", offset: 0.3 }, { filter: "brightness(1)" }], ms: 450 },
    sway: { frames: [0, -4, 4, -3, 0].map((r) => ({ transform: `rotate(${r}deg)` })), ms: 1400, easing: "ease-in-out" },
    glow: { frames: [{ filter: "drop-shadow(0 0 0 rgb(255 220 120 / 0))" }, { filter: "drop-shadow(0 0 28px rgb(255 220 120 / .95))", offset: 0.4 }, { filter: "drop-shadow(0 0 0 rgb(255 220 120 / 0))" }], ms: 1300 },
    wobble: { frames: [0, -10, 8, -5, 3, 0].map((k) => ({ transform: `skewX(${k}deg)` })), ms: 800 },
  };

  // Ways in, from an actor's side of the stage (-1 left, 1 right); ways out are the same, backwards.
  function entrance(how, side, width) {
    switch (how) {
      case "slide": return [{ transform: `translateX(${side * width * 0.6}px)`, opacity: 0 }, { transform: "none", opacity: 1 }];
      case "rise": return [{ transform: "translateY(100%)", opacity: 0 }, { transform: "none", opacity: 1 }];
      case "drop": return [{ transform: "translateY(-110%)", opacity: 0, easing: "cubic-bezier(.3,1.4,.5,1)" }, { transform: "none", opacity: 1 }];
      case "zoom": return [{ transform: "scale(.4)", opacity: 0 }, { transform: "none", opacity: 1 }];
      case "pop": return [{ transform: "scale(0)", opacity: 0 }, { transform: "scale(1.12)", opacity: 1, offset: 0.7 }, { transform: "none", opacity: 1 }];
      default: return [{ opacity: 0 }, { opacity: 1 }];
    }
  }

  class ScenePlayer {
    constructor(root, scene, options = {}) {
      this.root = root;
      this.scene = scene;
      this.options = options;
      this.token = 0;
      root.classList.add("vn");
      root.innerHTML = `
        <div class="vn-stage" tabindex="0" aria-label="${esc(scene.title || "Scene")}">
          <div class="vn-backdrop"></div>
          <div class="vn-actors"></div>
          <div class="vn-veil"></div>
          <div class="vn-flash"></div>
          <div class="vn-box" hidden aria-live="polite"><span class="vn-speaker" hidden></span><div class="vn-name"></div><p class="vn-text"></p><span class="vn-next" aria-hidden="true">&#9660;</span></div>
          <div class="vn-choices" hidden><p class="vn-prompt"></p><div class="vn-options"></div></div>
        </div>`;
      this.stage = root.querySelector(".vn-stage");
      this.backdrop = root.querySelector(".vn-backdrop");
      this.actorsEl = root.querySelector(".vn-actors");
      this.veil = root.querySelector(".vn-veil");
      this.flashEl = root.querySelector(".vn-flash");
      this.box = root.querySelector(".vn-box");
      this.nameEl = root.querySelector(".vn-name");
      this.speakerEl = root.querySelector(".vn-speaker");
      this.textEl = root.querySelector(".vn-text");
      this.choicesEl = root.querySelector(".vn-choices");
      // Pictures load before they're needed.
      for (const actor of Object.values(scene.cast)) for (const url of Object.values(actor.images)) new Image().src = url;
      this.stage.addEventListener("click", (event) => { if (!event.target.closest(".vn-choices")) this.next(); });
      this.stage.addEventListener("keydown", (event) => this.key(event));
    }

    // --- Running the steps ------------------------------------------------------------------------

    start(label = "") {
      this.token += 1;
      this.reset();
      this.index = label && label in this.scene.labels ? this.scene.labels[label] : 0;
      this.run(this.token);
      this.stage.focus({ preventScroll: true });
    }

    reset() {
      this.actors = {};
      this.actorsEl.innerHTML = "";
      this.flags = new Set();
      this.choices = [];
      this.buffs = [];
      this.fights = [];
      this.visits = {};
      this.stage.querySelectorAll(".vn-reward").forEach((card) => card.remove());
      this.line = 0;
      this.typing = null;
      this.waiting = null;
      this.box.hidden = true;
      this.choicesEl.hidden = true;
      this.veil.style.opacity = 0;
      this.background("default");
    }

    state() {
      return { line: this.line, flags: [...this.flags], choices: [...this.choices], buffs: [...this.buffs], fights: [...this.fights] };
    }

    async run(token) {
      let idle = 0;
      while (token === this.token) {
        const step = this.scene.steps[this.index];
        if (!step || step.do === "end") {
          if (step) this.line = step.line;
          this.finish();
          return;
        }
        const at = this.index;
        this.index += 1;
        this.line = step.line;
        if (this.options.onStep) this.options.onStep(step, this.state());
        const waits = this.perform(step, at);
        if (waits) {
          idle = 0;
          await waits;
        } else if (++idle > RUNAWAY) {
          this.say({ text: `The scene went round in circles at line ${step.line} without anything to show.` });
          return;
        }
      }
    }

    finish() {
      this.box.hidden = true;
      this.listening(null);
      if (this.options.onEnd) this.options.onEnd(this.state());
    }

    // Does a step (steps[at]). Returns a promise if the scene should wait for it, else nothing.
    perform(step, at) {
      const actor = step.who ? this.actors[step.who] : null;
      switch (step.do) {
        case "say": return this.say(step);
        case "choice": return this.choose(step, at);
        case "offer": return this.choose(step, at);
        case "give": return this.reward(step, at);
        case "fight": this.fight(at, null, step.who); return null;
        case "wait": return sleep(step.seconds * 1000);
        case "goto": this.index = this.scene.labels[step.label]; return null;
        case "if":
          if (this.flags.has(step.flag) !== step.not) this.index = this.scene.labels[step.label];
          return null;
        case "set": this.flags.add(step.flag); return null;
        case "unset": this.flags.delete(step.flag); return null;
        case "background": this.background(step.name); return null;
        case "screen": return this.screen(step.effect);
        case "enter": this.enter(step); return null;
        case "exit": if (actor) this.exit(actor, step); return null;
        case "move": if (actor) this.queue(actor, () => this.place(actor, step.at)); return null;
        case "show": this.express(step.who, step.expression); return null;
        case "turn": if (actor) actor.el.classList.toggle("vn-turned"); return null;
        case "dim": if (actor) actor.el.classList.add("vn-dimmed"); return null;
        case "brighten": if (actor) actor.el.classList.remove("vn-dimmed"); return null;
        case "animate": if (actor) this.animate(actor, step.animation); return null;
        default: return null;
      }
    }

    // --- Talking and choosing ---------------------------------------------------------------------

    fill(text) {
      return text.replaceAll("{player}", this.options.playerName || "you");
    }

    say(step) {
      const cast = step.who ? this.scene.cast[step.who] : null;
      if (step.expression) this.express(step.who, step.expression);
      this.listening(step.who || null);
      this.box.hidden = false;
      this.box.classList.toggle("vn-narration", !cast);
      this.nameEl.textContent = cast ? cast.name : "";
      this.nameEl.hidden = !cast;
      this.nameEl.classList.toggle("vn-name-player", Boolean(cast && cast.player));
      // Someone speaking from off the stage (the player, usually) shows their avatar beside their words.
      const offstage = cast && !this.actors[step.who];
      this.speakerEl.hidden = !offstage;
      this.box.classList.toggle("vn-has-speaker", Boolean(offstage));
      if (offstage) this.speakerEl.innerHTML = this.avatar(cast);
      const text = this.fill(step.text);
      return new Promise((resolve) => {
        this.textEl.textContent = "";
        this.box.classList.remove("vn-ready");
        let shown = 0;
        const done = () => {
          clearInterval(timer);
          this.textEl.textContent = text;
          this.typing = null;
          this.box.classList.add("vn-ready");
          this.waiting = resolve;
        };
        const timer = setInterval(() => {
          shown += 1;
          this.textEl.textContent = text.slice(0, shown);
          if (shown >= text.length) done();
        }, reduced ? 1 : TYPE_MS);
        this.typing = done;
      });
    }

    // A click or key: finish the line being typed, or go on to the next.
    next() {
      if (this.typing) this.typing();
      else if (this.waiting) {
        const go = this.waiting;
        this.waiting = null;
        go();
      }
    }

    key(event) {
      if ([" ", "Enter", "ArrowRight"].includes(event.key) && this.choicesEl.hidden) {
        event.preventDefault();
        this.next();
      } else if (/^[1-9]$/.test(event.key) && !this.choicesEl.hidden) {
        const option = this.choicesEl.querySelectorAll(".vn-option")[Number(event.key) - 1];
        if (option) option.click();
      }
    }

    // A buff, given: shown until a click, and counted.
    reward(step, at) {
      this.gain(at, null, step.buff, step.name);
      this.box.hidden = true;
      const card = document.createElement("div");
      card.className = "vn-reward";
      card.innerHTML = `<p class="vn-reward-kicker">Reward</p><p class="vn-reward-name">${esc(step.name)}</p><p class="vn-reward-text">${esc(step.text)}</p>`;
      this.stage.appendChild(card);
      return new Promise((resolve) => {
        this.waiting = () => {
          card.remove();
          resolve();
        };
      });
    }

    // Who the run fights next: settled by the server once the scene's done.
    fight(at, option, who) {
      const cast = this.scene.cast[who];
      this.fights.push({ step: at, option, who, name: cast ? cast.name : who });
      if (this.options.onFight) this.options.onFight(who, cast ? cast.name : who);
    }

    gain(at, option, buff, name) {
      if (this.buffs.some((given) => given.step === at)) return; // once per step, as the server counts them
      this.buffs.push({ step: at, option, buff, name });
      if (this.options.onBuff) this.options.onBuff(buff, name);
    }

    // A choice, or an offer of buffs: an offer's options are the buffs, with what each does; so is a choice's option
    // that gives one, under what it says.
    choose(step, at) {
      const offer = step.do === "offer";
      this.box.hidden = true;
      this.choicesEl.hidden = false;
      const prompt = this.choicesEl.querySelector(".vn-prompt");
      prompt.textContent = this.fill(step.prompt);
      prompt.hidden = !step.prompt;
      const options = this.choicesEl.querySelector(".vn-options");
      options.innerHTML = step.options.map((option, i) => offer
        ? `<button type="button" class="vn-option vn-buff" data-i="${i}"><span class="vn-key">${i + 1}</span><span><strong>${esc(option.name)}</strong><span class="vn-buff-text">${esc(option.text)}</span></span></button>`
        : option.give_text
          ? `<button type="button" class="vn-option vn-buff" data-i="${i}"><span class="vn-key">${i + 1}</span><span>${esc(this.fill(option.text))}<span class="vn-buff-text"><strong>${esc(option.give_name)}:</strong> ${esc(option.give_text)}</span></span></button>`
          : `<button type="button" class="vn-option" data-i="${i}"><span class="vn-key">${i + 1}</span>${esc(this.fill(option.text))}</button>`).join("");
      options.querySelector(".vn-option").focus({ preventScroll: true });
      const visit = this.visits[at] = (this.visits[at] || 0) + 1;
      return new Promise((resolve) => {
        const chosen = (i) => {
          const option = step.options[i];
          this.choicesEl.hidden = true;
          this.choices.push({ line: step.line, prompt: step.prompt, text: offer ? option.name : option.text });
          if (offer) this.gain(at, i, option.buff, option.name);
          else if (option.give) this.gain(at, i, option.give, option.give_name || option.give);
          if (!offer && option.fight) this.fight(at, i, option.fight);
          if (option.set) this.flags.add(option.set);
          if (option.unset) this.flags.delete(option.unset);
          if (option.goto) this.index = this.scene.labels[option.goto];
          if (this.options.onChoice) this.options.onChoice(step, option);
          this.stage.focus({ preventScroll: true });
          resolve();
        };
        options.onclick = (event) => {
          const button = event.target.closest(".vn-option");
          if (!button) return;
          const i = Number(button.dataset.i);
          options.onclick = null;
          if (!this.options.decide) return chosen(i);
          button.classList.add("voted");
          options.querySelectorAll(".vn-option").forEach((other) => { other.disabled = true; });
          this.options.decide(step, at, visit, i).then(chosen);
        };
      });
    }

    // Whoever's speaking stands out: the others on stage fade back a little. Nobody (narration) clears it.
    listening(speaker) {
      for (const [name, actor] of Object.entries(this.actors)) actor.el.classList.toggle("vn-listening", Boolean(speaker) && name !== speaker);
      if (speaker && this.actors[speaker]) this.raise(this.actors[speaker]);
    }

    // Bring an actor to the front, over anyone they overlap: whoever last spoke or moved stays on top.
    raise(actor) {
      this.topLayer = (this.topLayer || 0) + 1;
      actor.el.style.zIndex = this.topLayer;
    }

    // --- The stage --------------------------------------------------------------------------------

    background(name) {
      const old = this.backdrop.lastElementChild;
      if (old && old.dataset.bg === name) return;
      const layer = document.createElement("div");
      layer.className = "vn-bg";
      layer.dataset.bg = name;
      if (window.SceneBackdrops) layer.innerHTML = window.SceneBackdrops.draw(name); // the drawn scene (backdrops.js), over a plain gradient
      this.backdrop.appendChild(layer);
      layer.animate([{ opacity: 0 }, { opacity: 1 }], { duration: reduced || !old ? 1 : 900 }).finished
        .then(() => { while (this.backdrop.children.length > 1) this.backdrop.firstElementChild.remove(); }, () => {});
    }

    screen(effect) {
      if (effect === "shake" && !reduced) {
        this.stage.animate([0, -12, 12, -8, 8, -4, 0].map((x, i) => ({ transform: `translate(${x}px, ${i % 2 ? 4 : -4}px)` })), { duration: 500 });
      } else if (effect === "flash") {
        this.flashEl.animate([{ opacity: 0 }, { opacity: 0.9, offset: 0.2 }, { opacity: 0 }], { duration: 500 });
      } else if (effect === "black" || effect === "clear") {
        this.veil.style.opacity = effect === "black" ? 1 : 0;
        return sleep(reduced ? 0 : 800);
      }
      return null;
    }

    // An actor's picture: the one for this expression, else their main one, else their avatar, else a letter.
    face(cast, expression) {
      const url = cast.images[expression] || cast.images.main;
      if (url) return `<img class="vn-picture" src="${esc(url)}" alt="${esc(cast.name)}" draggable="false">`;
      return this.avatar(cast, "vn-avatar");
    }

    // Their avatar, a circle cut from a card, or the first letter of their name if they haven't one.
    avatar(cast, extraClass = "") {
      const avatar = cast.avatar;
      return `<span class="${extraClass} avatar" role="img" aria-label="${esc(cast.name)}">${avatar
        ? `<img src="${esc(avatar.image)}" alt="" draggable="false" style="width:${avatar.width}%;left:${avatar.left}%;top:${avatar.top}%">`
        : `<span class="avatar-letter">${esc(cast.name.slice(0, 1).toUpperCase())}</span>`}</span>`;
    }

    express(who, expression) {
      const actor = this.actors[who];
      if (!actor) return;
      actor.expression = expression;
      actor.body.innerHTML = this.face(this.scene.cast[who], expression);
    }

    enter(step) {
      const cast = this.scene.cast[step.who];
      let actor = this.actors[step.who];
      if (actor && !actor.leaving) return this.queue(actor, () => this.place(actor, step.at));
      const el = document.createElement("div");
      el.className = "vn-actor";
      el.dataset.who = step.who;
      el.innerHTML = '<div class="vn-body"></div>';
      this.actorsEl.appendChild(el);
      actor = { el, body: el.querySelector(".vn-body"), expression: "main", busy: Promise.resolve(), at: step.at };
      this.actors[step.who] = actor;
      actor.body.innerHTML = this.face(cast, "main");
      el.style.left = `${PLACES[step.at]}%`;
      const side = PLACES[step.at] < 50 ? -1 : 1;
      return this.queue(actor, () => actor.body.animate(entrance(step.how, side, this.stage.clientWidth), { duration: reduced ? 1 : 650, easing: "cubic-bezier(.2,.8,.3,1)" }).finished);
    }

    exit(actor, step) {
      actor.leaving = true;
      const side = step.at ? (step.at === "left" ? -1 : 1) : PLACES[actor.at] < 50 ? -1 : 1;
      const who = actor.el.dataset.who;
      this.queue(actor, () => actor.body.animate(entrance(step.how, side, this.stage.clientWidth).reverse(),
        { duration: reduced ? 1 : 550, easing: "ease-in", fill: "forwards" }).finished.then(() => {
        actor.el.remove();
        if (this.actors[who] === actor) delete this.actors[who];
      }));
    }

    place(actor, at) {
      actor.at = at;
      actor.el.style.left = `${PLACES[at]}%`;
      return sleep(reduced ? 0 : 700);
    }

    animate(actor, name) {
      const animation = ANIMATIONS[name];
      if (!animation || reduced) return;
      this.queue(actor, () => this.raise(actor) || actor.body.animate(animation.frames, { duration: animation.ms, easing: animation.easing || "ease-in-out" }).finished);
    }

    // An actor's directions play one after another, while the script carries on.
    queue(actor, run) {
      actor.busy = actor.busy.then(run).catch(() => {});
      return actor.busy;
    }
  }

  window.ScenePlayer = ScenePlayer;
})();
