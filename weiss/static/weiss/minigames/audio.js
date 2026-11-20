/* Minigame sound (docs/minigames-plan.md, "Round 3: sound and music"). Music and effects are made with Web Audio, the same
   approach as world_audio.js: no audio files. One loop per game, each with its own tempo, key and mood (memory calm, cups
   playful and a bit tense, invaders driving, runner fast and bouncy, higher_lower light and quick), and short effects.
   The API: MinigameAudio.start(key), stop(), sfx(name), setMuted(on), muted(). Nothing plays until the first user gesture.
   Music stops when the tab is hidden and when a game stops. Mute silences music and effects; the shell owns the button
   and its saved setting. */
(() => {
  const STEP_LOOKAHEAD = 0.12; // seconds of music scheduled ahead
  const PUMP_MS = 25;

  // A pattern is 16 steps (a sixteenth each): a number is a scale degree (or the drum is hit with "x"), "." is a rest.
  const pattern = (text) => text.trim().split(/\s+/).map((token) => (token === "." ? null : token === "x" ? true : Number(token)));

  // Each style: the key (root, a MIDI note), the scale (semitones), the tempo, the voices and their patterns.
  const STYLES = {
    memory: { bpm: 84, root: 57, scale: [0, 2, 3, 5, 7, 8, 10], wave: "triangle", leadLen: 4, bassLen: 4, leadGain: 0.05, bassGain: 0.05,
      lead: pattern("0 . . . 2 . . . 4 . . . 2 . . ."), bass: pattern("0 . . . . . . . 3 . . . 2 . . ."),
      kick: pattern(". . . . . . . . . . . . . . . ."), hat: pattern("x . . . x . . . x . . . x . . .") },
    cups: { bpm: 120, root: 62, scale: [0, 2, 3, 6, 7, 8, 11], wave: "square", leadLen: 1, bassLen: 1, leadGain: 0.035, bassGain: 0.06,
      lead: pattern("0 . 2 . 3 . 6 . 7 . 6 . 3 . 2 ."), bass: pattern("0 . . . 0 . 0 . 3 . . . 0 . 0 ."),
      kick: pattern("x . . . . . . . x . . . . . . ."), hat: pattern("x . x . x . x . x . x . x . x .") },
    invaders: { bpm: 140, root: 52, scale: [0, 2, 3, 5, 7, 8, 10], wave: "square", leadLen: 2, bassLen: 1, leadGain: 0.03, bassGain: 0.07,
      lead: pattern("0 . . . 4 . 3 . 5 . . . 7 . 5 ."), bass: pattern("0 . 0 . 0 . 0 . 3 . 3 . 4 . 4 ."),
      kick: pattern("x . . . x . . . x . . . x . . ."), hat: pattern(". . x . . . x . . . x . . . x .") },
    runner: { bpm: 150, root: 55, scale: [0, 2, 4, 7, 9], wave: "triangle", leadLen: 1, bassLen: 1, leadGain: 0.04, bassGain: 0.07,
      lead: pattern("2 . 4 . 3 . 4 . 2 . 4 . 0 . 1 ."), bass: pattern("0 . . 0 . 0 . . 0 . . 0 . 0 . ."),
      kick: pattern("x . . x . . x . x . . x . . x ."), hat: pattern("x x x x x x x x x x x x x x x x") },
    higher_lower: { bpm: 128, root: 60, scale: [0, 2, 4, 5, 7, 9, 11], wave: "triangle", leadLen: 1, bassLen: 1, leadGain: 0.04, bassGain: 0.05,
      lead: pattern("4 . 5 . 7 . 9 . 7 . 5 . 4 . 2 ."), bass: pattern("0 . . . 4 . . . 5 . . . 4 . . ."),
      kick: pattern(". . . . . . . . . . . . . . . ."), hat: pattern(". x . x . x . x . x . x . x . x") },
  };

  let ctx = null;
  let master = null;
  let musicBus = null;
  let sfxBus = null;
  let noise = null;
  let muted = false;
  let wanted = null; // the game's music, as the game asked for it
  let playing = null; // the loop actually running now
  let timer = 0;
  let nextTime = 0;
  let stepIndex = 0;
  let lastSfx = "";

  const midi = (note) => 440 * 2 ** ((note - 69) / 12);

  // A scale degree (any octave) on a style's key, shifted by `octaves` octaves.
  function note(style, degree, octaves) {
    const len = style.scale.length;
    const octave = Math.floor(degree / len);
    return style.root + 12 * octaves + style.scale[degree % len] + 12 * octave;
  }

  function tone(at, freq, dur, type, gain, glideTo, bus) {
    const osc = ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, at);
    if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo, at + dur);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0.0001, at);
    env.gain.exponentialRampToValueAtTime(gain, at + 0.01);
    env.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    osc.connect(env);
    env.connect(bus);
    osc.start(at);
    osc.stop(at + dur + 0.02);
  }

  function burst(at, dur, freq, gain, type, bus) {
    const src = ctx.createBufferSource();
    src.buffer = noise;
    const filter = ctx.createBiquadFilter();
    filter.type = type;
    filter.frequency.value = freq;
    const env = ctx.createGain();
    env.gain.setValueAtTime(gain, at);
    env.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    src.connect(filter);
    filter.connect(env);
    env.connect(bus);
    src.start(at, Math.random());
    src.stop(at + dur + 0.02);
  }

  // ---- The music: one step (a sixteenth) of a style's loop ----

  function playStep(style, index, at, stepDur) {
    const i = index % 16;
    const lead = style.lead[i];
    if (lead !== null) tone(at, midi(note(style, lead, 1)), stepDur * style.leadLen * 0.9, style.wave, style.leadGain, null, musicBus);
    const bass = style.bass[i];
    if (bass !== null) tone(at, midi(note(style, bass, 0) - 12), stepDur * style.bassLen * 0.9, "triangle", style.bassGain, null, musicBus);
    if (style.kick[i]) tone(at, 140, 0.12, "sine", 0.5, 45, musicBus);
    if (style.hat[i]) burst(at, 0.035, 7000, 0.05, "highpass", musicBus);
  }

  function pump() {
    const style = STYLES[playing];
    if (!style || !ctx) return;
    const stepDur = 60 / style.bpm / 4;
    if (nextTime < ctx.currentTime - 0.5) nextTime = ctx.currentTime + 0.05; // after a pause, don't rush to catch up
    while (nextTime < ctx.currentTime + STEP_LOOKAHEAD) {
      playStep(style, stepIndex, nextTime, stepDur);
      stepIndex += 1;
      nextTime += stepDur;
    }
  }

  function stopMusic() {
    clearInterval(timer);
    timer = 0;
    playing = null;
  }

  function beginMusic(key) {
    if (!ctx || muted || !STYLES[key] || playing === key) return;
    stopMusic();
    playing = key;
    stepIndex = 0;
    nextTime = ctx.currentTime + 0.05;
    timer = setInterval(pump, PUMP_MS);
    pump();
  }

  // ---- The effects: short, and never the only sign of a result (the text and the bubble say it too) ----

  const SFX = {
    flip: (t) => tone(t, 1800, 0.03, "square", 0.05, null, sfxBus),
    match: (t) => { tone(t, 659, 0.12, "triangle", 0.2, null, sfxBus); tone(t + 0.1, 880, 0.2, "triangle", 0.2, null, sfxBus); },
    miss: (t) => tone(t, 300, 0.25, "sawtooth", 0.12, 150, sfxBus),
    cup: (t) => burst(t, 0.05, 900, 0.5, "bandpass", sfxBus),
    reveal: (t) => [0, 0.06, 0.12, 0.18].forEach((d, i) => tone(t + d, 523 * (1 + i * 0.25), 0.12, "triangle", 0.15, null, sfxBus)),
    shuffle: (t) => burst(t, 0.3, 1500, 0.15, "bandpass", sfxBus),
    correct: (t) => { tone(t, 523, 0.1, "triangle", 0.2, null, sfxBus); tone(t + 0.08, 784, 0.18, "triangle", 0.2, null, sfxBus); },
    wrong: (t) => tone(t, 220, 0.3, "sawtooth", 0.12, 110, sfxBus),
    shoot: (t) => tone(t, 1000, 0.12, "square", 0.06, 250, sfxBus),
    hit: (t) => { burst(t, 0.15, 800, 0.4, "lowpass", sfxBus); tone(t, 110, 0.2, "sine", 0.3, 60, sfxBus); },
    pickup: (t) => [1046, 1318, 1568].forEach((f, i) => tone(t + i * 0.05, f, 0.12, "triangle", 0.18, null, sfxBus)),
    shield: (t) => tone(t, 600, 0.5, "triangle", 0.15, 1200, sfxBus),
    jump: (t) => tone(t, 300, 0.18, "square", 0.1, 620, sfxBus),
    slide: (t) => burst(t, 0.22, 600, 0.2, "bandpass", sfxBus),
    wave: (t) => [523, 659, 784, 1046].forEach((f, i) => tone(t + i * 0.09, f, 0.16, "triangle", 0.2, null, sfxBus)),
    win: (t) => [523, 659, 784, 1046].forEach((f, i) => tone(t + i * 0.13, f, i === 3 ? 0.6 : 0.2, "triangle", 0.22, null, sfxBus)),
    lose: (t) => [659, 622, 587, 554].forEach((f, i) => tone(t + i * 0.22, f, 0.3, "triangle", 0.18, null, sfxBus)),
  };

  // ---- Making the sound (on the first user gesture: browsers allow no sound before one) ----

  function unlock() {
    if (ctx) {
      if (ctx.state === "suspended") ctx.resume().catch(() => {});
      return;
    }
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return;
    ctx = new Context();
    master = ctx.createGain();
    master.gain.value = muted ? 0 : 0.8;
    master.connect(ctx.destination);
    musicBus = ctx.createGain();
    musicBus.gain.value = 0.55;
    musicBus.connect(master);
    sfxBus = ctx.createGain();
    sfxBus.gain.value = 0.7;
    sfxBus.connect(master);
    noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const data = noise.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    if (wanted) beginMusic(wanted);
  }

  for (const type of ["pointerdown", "keydown", "touchend"]) {
    document.addEventListener(type, unlock, { capture: true });
  }

  // A hidden tab stops the music (the games pause themselves too); it comes back when the tab does, if a game is on.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopMusic();
    } else if (wanted) {
      beginMusic(wanted);
    }
  });

  window.MinigameAudio = {
    // The game's loop. Starting again for the same game is harmless.
    start(key) {
      if (!STYLES[key]) return;
      wanted = key;
      if (ctx) beginMusic(key);
    },
    // The game's end (or a new game): the music stops. Effects, such as the win or lose sound, still play.
    stop() {
      wanted = null;
      stopMusic();
    },
    // A short effect, by name (see SFX). Silent when muted.
    sfx(name) {
      lastSfx = name;
      if (muted || !ctx || !SFX[name]) return;
      SFX[name](ctx.currentTime + 0.01);
    },
    // Mute silences the music and the effects. The shell keeps the button and its saved setting.
    setMuted(on) {
      muted = Boolean(on);
      if (master) master.gain.setTargetAtTime(muted ? 0 : 0.8, ctx.currentTime, 0.05);
      if (muted) stopMusic();
      else if (wanted) beginMusic(wanted);
    },
    muted() {
      return muted;
    },
    // For tests and the shell: what is playing, and how far the loop has got.
    status() {
      return { ready: Boolean(ctx), playing, step: stepIndex, muted, wanted, lastSfx, clock: ctx ? ctx.currentTime : 0 };
    },
  };
})();
