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

  // Two bars (32 steps) as one pattern: the rock and lo-fi loops don't repeat every bar.
  const two = (first, second) => pattern(`${first} ${second}`);

  // Each style: the key (root, a MIDI note), the scale (semitones), the tempo, the voices and their patterns. A style
  // with `loop` (32) plays its patterns across that many steps; without it, the 16-step loop.
  const STYLES = {
    memory: { bpm: 84, root: 57, scale: [0, 2, 3, 5, 7, 8, 10], wave: "triangle", leadLen: 4, bassLen: 4, leadGain: 0.25, bassGain: 0.25,
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
    higher_lower: { bpm: 128, root: 60, scale: [0, 2, 4, 5, 7, 9, 11], wave: "triangle", leadLen: 1, bassLen: 1, leadGain: 0.2, bassGain: 0.25,
      lead: pattern("4 . 5 . 7 . 9 . 7 . 5 . 4 . 2 ."), bass: pattern("0 . . . 4 . . . 5 . . . 4 . . ."),
      kick: pattern(". . . . . . . . . . . . . . . ."), hat: pattern(". x . x . x . x . x . x . x . x") },
    lofi: { name: "Lo-fi", bpm: 80, root: 53, scale: [0, 2, 4, 5, 7, 9, 11], wave: "sine", loop: 32, leadLen: 4, bassLen: 2,
      leadGain: 0.02, bassGain: 0.06, bassWave: "sine", bassFilter: 500, keysLen: 8, keysGain: 0.022, kickGain: 0.4, hatGain: 0.025,
      lead: two("7 . . . 4 . . . 5 . . . 2 . . .", "4 . . . 5 . . . 7 . . . 4 . . ."),
      bass: two("0 . . . 0 . . . 3 . . . 4 . . .", "0 . . . 0 . . . 3 . . . 2 . . ."),
      keys: two("0 . . . . . . . 3 . . . . . . .", "4 . . . . . . . 0 . . . . . . ."),
      kick: two("x . . . . . x . x . . . . . . .", "x . . . . . x . . . x . . . . ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . ."),
      hat: two("x . x . x . x . x . x . x . x .", "x . x . x . x . x . x . x . x .") },
    rock_1: { name: "Driving rock", bpm: 124, root: 52, scale: [0, 2, 3, 5, 7, 8, 10], wave: "square", loop: 32, bassLen: 1,
      bassGain: 0.05, bassWave: "sawtooth", bassFilter: 600, guitarLen: 8, guitarShape: "power", guitarGain: 0.03, kickGain: 0.5, hatGain: 0.04,
      bass: two("0 . 0 . 0 . 0 . 0 . 0 . 3 . 4 .", "0 . 0 . 0 . 0 . 6 . 6 . 4 . 3 ."),
      guitar: two("0 . . . . . . . 5 . . . . . . .", "6 . . . . . . . 4 . . . . . . ."),
      kick: two("x . . . x . . . x . . . x . x .", "x . . . x . . x x . . . x . x ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . x"),
      hat: two("x . x . x . x . x . x . x . x .", "x . x . x . x . x . x . x . x x") },
    rock_2: { name: "Half-time, moody", bpm: 84, root: 57, scale: [0, 2, 3, 5, 7, 8, 10], wave: "triangle", loop: 32, bassLen: 4,
      bassGain: 0.07, bassWave: "triangle", bassFilter: 900, guitarLen: 4, guitarShape: "clean", guitarGain: 0.03,
      keysLen: 16, keysGain: 0.02, kickGain: 0.45, hatGain: 0.03,
      bass: two("0 . . . . . . . 0 . . . 3 . . .", "0 . . . . . . . 5 . . . 4 . . ."),
      guitar: two("0 . . . 0 . . . 3 . . . 4 . . .", "5 . . . 4 . . . 0 . . . 0 . . ."),
      keys: two("0 . . . . . . . . . . . . . . .", "5 . . . . . . . . . . . . . . ."),
      kick: two("x . . . . . . . x . . . . . x .", "x . . . . . . . x . . . . . x ."),
      snare: two(". . . . . . . . x . . . . . . .", ". . . . . . . . x . . . . . . ."),
      hat: two("x . . . x . . . x . . . x . . .", "x . . . x . . . x . . . x . . .") },
    rock_3: { name: "Rock", bpm: 178, root: 55, scale: [0, 2, 4, 5, 7, 9, 10], wave: "square", loop: 32, bassLen: 1,
      bassGain: 0.05, bassWave: "sawtooth", bassFilter: 700, guitarLen: 1, guitarShape: "power", guitarGain: 0.035, kickGain: 0.5, hatGain: 0.035,
      bass: two("0 . 0 . 0 . 0 . 3 . 3 . 0 . 0 .", "0 . 0 . 0 . 0 . 4 . 4 . 5 . 6 ."),
      guitar: two("0 . 0 . 0 . 0 . 3 . 0 . 0 . 4 .", "0 . 0 . 4 . 0 . 3 . 0 . 5 . 6 ."),
      kick: two("x . x . x . x . x . x . x . x .", "x . x . x . x . x . x . x . x ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . ."),
      hat: two("x x x x x x x x x x x x x x x x", "x x x x x x x x x x x x x x x x") },
    rock_4: { name: "Groove", bpm: 100, root: 50, scale: [0, 2, 4, 5, 7, 9, 11], wave: "triangle", loop: 32, leadLen: 4,
      leadGain: 0.03, bassLen: 4, bassGain: 0.06, bassWave: "triangle", bassFilter: 1000, guitarLen: 4, guitarShape: "clean", guitarGain: 0.025,
      kickGain: 0.45, hatGain: 0.03,
      lead: two("4 . . . 5 . . . 7 . . . 5 . . .", "7 . . . 9 . . . 7 . . . 5 . . ."),
      bass: two("0 . . . 0 . . . 4 . . . 3 . . .", "0 . . . 4 . . . 5 . . . 4 . . ."),
      guitar: two("0 . . . 2 . . . 4 . . . 2 . . .", "3 . . . 5 . . . 4 . . . 2 . . ."),
      kick: two("x . . . . . . . x . . . . . . .", "x . . . . . . . x . . . x . . ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . ."),
      hat: two("x . x . x . x . x . x . x . x .", "x . x . x . x . x . x . x . x .") },
    // Synthesized, not recorded: the same voices as the rock styles, shaped into four more moods.
    hip_hop: { name: "Boom-bap hip hop", bpm: 90, root: 50, scale: [0, 2, 3, 5, 7, 8, 10], wave: "sine", loop: 32, bassLen: 2,
      bassGain: 0.09, bassWave: "sine", bassFilter: 160, keysLen: 4, keysGain: 0.018, kickGain: 0.6, hatGain: 0.03,
      bass: two("0 . . . . . . . 0 . . . 3 . . .", "0 . . . . . . . 5 . . . 4 . . ."),
      keys: two("0 . . . . . . . 3 . . . . . . .", "4 . . . . . . . 0 . . . . . . ."),
      kick: two("x . . . . . . x . . . . . x . .", "x . . . . . . x . . . . . . . ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . ."),
      hat: two("x . . x . x . . x . . x . x . .", "x . . x . x . . x . . x . x . .") },
    jazz: { name: "Walking jazz", bpm: 120, root: 50, scale: [0, 2, 3, 5, 7, 9, 10], wave: "triangle", loop: 32, bassLen: 4,
      bassGain: 0.07, bassWave: "triangle", bassFilter: 900, guitarLen: 4, guitarShape: "clean", guitarGain: 0.02, kickGain: 0.3, hatGain: 0.02,
      bass: two("0 . . . 2 . . . 4 . . . 3 . . .", "5 . . . 4 . . . 2 . . . 0 . . ."),
      guitar: two("0 . . . . . . . 3 . . . . . . .", "2 . . . . . . . 4 . . . . . . ."),
      kick: two("x . . . . . . . x . . . . . . .", "x . . . . . . . x . . . . . . ."),
      hat: two("x . x . x . x . x . x . x . x .", "x . x . x . x . x . x . x . x .") },
    funk: { name: "Funk, slap and clav", bpm: 100, root: 52, scale: [0, 2, 3, 5, 7, 9, 10], wave: "square", loop: 32, bassLen: 1,
      bassGain: 0.06, bassWave: "sawtooth", bassFilter: 1200, guitarLen: 1, guitarShape: "stab", guitarGain: 0.018, kickGain: 0.5, hatGain: 0.03,
      bass: two("0 . . 0 . . 0 . 0 . . 4 . . 0 .", "0 . . 0 . . 5 . 0 . . 3 . 4 . ."),
      guitar: two("0 . . . . 0 . . . 0 . . . . 0 .", "3 . . . . 0 . . . . 0 . . . 0 ."),
      kick: two("x . . x . . x . . . x . . x . .", "x . . x . . x . . . x . . x . ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . ."),
      hat: two("x . x x x . x x x . x x x . x .", "x . x x x . x x x . x x x . x .") },
    synthwave: { name: "Synthwave, pulsing", bpm: 110, root: 57, scale: [0, 2, 3, 5, 7, 8, 10], wave: "square", loop: 32, leadLen: 1,
      leadGain: 0.02, bassLen: 1, bassGain: 0.05, bassWave: "sawtooth", bassFilter: 700, kickGain: 0.5, hatGain: 0.025,
      bass: two("0 . 0 . 0 . 0 . 0 . 0 . 0 . 0 .", "0 . 0 . 0 . 0 . 3 . 3 . 5 . 5 ."),
      lead: two("0 . 2 . 4 . 7 . 4 . 2 . 0 . 2 .", "3 . 4 . 7 . 9 . 7 . 4 . 3 . 0 ."),
      kick: two("x . . . x . . . x . . . x . . .", "x . . . x . . . x . . . x . . ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . ."),
      hat: two("x . x . x . x . x . x . x . x .", "x . x . x . x . x . x . x . x .") },
    emo: { name: "Emo, melodic", bpm: 130, root: 57, scale: [0, 2, 3, 5, 7, 8, 10], wave: "triangle", loop: 32, leadLen: 4,
      leadGain: 0.03, bassLen: 1, bassGain: 0.05, bassWave: "triangle", bassFilter: 700, guitarLen: 2, guitarShape: "arp", guitarGain: 0.03,
      kickGain: 0.45, hatGain: 0.025,
      guitar: two("0 . 0 . 0 . 0 . 3 . 3 . 4 . 4 .", "0 . 0 . 0 . 0 . 5 . 5 . 4 . 3 ."),
      bass: two("0 . 0 . 0 . 0 . 0 . 0 . 3 . 3 .", "0 . 0 . 0 . 0 . 4 . 4 . 5 . 5 ."),
      lead: two("7 . . . 5 . . . 4 . . . 2 . . .", "4 . . . 5 . . . 7 . . . 9 . . ."),
      kick: two("x . . . . . . . x . . . . . . .", "x . . . . . . . x . . . . . . ."),
      snare: two(". . . . . . . . x . . . . . . .", ". . . . . . . . x . . . . . . ."),
      hat: two("x . x . x . x . x . x . x . x .", "x . x . x . x . x . x . x . x .") },
    metal: { name: "Metal, palm-muted", bpm: 160, root: 45, scale: [0, 1, 3, 5, 7, 8, 10], wave: "square", loop: 32, bassLen: 1,
      bassGain: 0.05, bassWave: "sawtooth", bassFilter: 500, guitarLen: 2, guitarShape: "power", guitarGain: 0.035, kickGain: 0.55, hatGain: 0.03,
      guitar: two("0 . 0 . 0 . 0 . 0 . 0 . 0 . 0 .", "0 . 0 . 0 . 1 . 0 . 0 . 3 . 1 ."),
      bass: two("0 . 0 . 0 . 0 . 0 . 0 . 0 . 0 .", "0 . 0 . 0 . 0 . 1 . 1 . 0 . 0 ."),
      kick: two("x x . x x . x . x x . x x . x .", "x x . x x . x . x x . x x . x ."),
      snare: two(". . . . x . . . . . . . x . . .", ". . . . x . . . . . . . x . . ."),
      hat: two("x x x x x x x x x x x x x x x x", "x x x x x x x x x x x x x x x x") },
    // Real drums (CC0, Karoryfer kits): 2-bar loops rendered to WAV in sounds/music/cc0/, loaded on first play.
    cc0_1: { name: "CC0 drums 1", sample: "music/cc0/cc0_1.wav", gain: 0.6, bpm: 118 },
    cc0_2: { name: "CC0 drums 2", sample: "music/cc0/cc0_2.wav", gain: 0.6, bpm: 84 },
    cc0_3: { name: "CC0 drums 3", sample: "music/cc0/cc0_3.wav", gain: 0.6, bpm: 160 },
    cc0_4: { name: "CC0 jazz", sample: "music/cc0/cc0_4.wav", gain: 0.6, bpm: 120 },
    cc0_5: { name: "CC0 hip hop", sample: "music/cc0/cc0_5.wav", gain: 0.6, bpm: 90 },
    cc0_6: { name: "CC0 funk", sample: "music/cc0/cc0_6.wav", gain: 0.6, bpm: 100 },
    cc0_7: { name: "CC0 emo", sample: "music/cc0/cc0_7.wav", gain: 0.6, bpm: 130 },
    cc0_8: { name: "CC0 metal", sample: "music/cc0/cc0_8.wav", gain: 0.6, bpm: 160 },
  };

  // Version 2: the layered songs. Each has its drum feel, its extra part (a counter-melody, arpeggio or percussion) and its splash.
  // The core, top, bass, chords, lead, drive and climax layers come from the patterns above, so each song has all nine layers.
  const LAYER_DATA = {
    lofi: { drumGain: 0.6, topKit: "hat", splash: "fill", extraWave: "triangle", extraGain: 0.03,
      extra: two("0 . . . 2 . . . 4 . . . 2 . . .", "4 . . . 2 . . . 0 . . . 2 . . .") },
    rock_3: { drumGain: 1, topKit: "hat", splash: "fill", extraKit: "tom_low",
      extra: two("x . . . . . x . . . . . x . x .", ". . . . . . . . . . . . x x x x") },
    rock_4: { drumGain: 0.9, topKit: "ride", splash: "fill", extraWave: "triangle", extraGain: 0.025,
      extra: two("0 . 2 . 4 . 2 . 0 . 2 . 4 . 2 .", "3 . 5 . 4 . 2 . 0 . 2 . 3 . 1 .") },
    hip_hop: { drumGain: 0.9, topKit: "hat", splash: "stab", extraKit: "rim",
      extra: two("x . . x . . x . . x . . x . . .", ". . x . . . . . x . . . . . x .") },
    jazz: { drumGain: 0.5, topKit: "ride", splash: "fill", extraWave: "triangle", extraGain: 0.025,
      extra: two("4 . . . 2 . . . 5 . . . 3 . . .", "2 . . . 4 . . . 1 . . . 0 . . .") },
    funk: { drumGain: 0.9, topKit: "hat", splash: "stab", extraKit: "cowbell",
      extra: two("x . . x . . x . x . . x . . x .", "x . . x . . x . x . . x . . x .") },
    synthwave: { drumGain: 0.9, topKit: "hat", splash: "fill", extraWave: "square", extraGain: 0.02,
      extra: two("4 . 5 . 7 . 5 . 4 . 2 . 0 . 2 .", "0 . 2 . 4 . 7 . 4 . 2 . 0 . 2 .") },
    emo: { drumGain: 0.9, topKit: "ride", splash: "fill", extraWave: "triangle", extraGain: 0.02,
      extra: two("0 . . . 0 . . . 2 . . . 0 . . .", "3 . . . 2 . . . 0 . . . 2 . . .") },
    metal: { drumGain: 1.1, topKit: "hat", splash: "stab", extraKit: "kick",
      extra: two("x x . x x . x . x x . x x . x .", "x x . x x . x . x x . x x . x .") },
  };
  for (const key of Object.keys(LAYER_DATA)) Object.assign(STYLES[key], { layered: true }, LAYER_DATA[key]);
  // The tension pad's voice, per song (the match-point swell).
  const TENSION_WAVE = { lofi: "sine", rock_3: "square", rock_4: "triangle", hip_hop: "sine", jazz: "triangle", funk: "sawtooth", synthwave: "square", emo: "triangle", metal: "sawtooth" };
  for (const key of Object.keys(TENSION_WAVE)) STYLES[key].tensionWave = TENSION_WAVE[key];
  // The CC0 songs are layered too: each layer is its own loop (see beginSample).
  for (const key of ["cc0_1", "cc0_3", "cc0_4", "cc0_5", "cc0_6", "cc0_7", "cc0_8"]) STYLES[key].layered = true;

  // Sample loops (the cc0 styles) are decoded once and cached; a file that's missing or won't decode is cached as null,
  // and its style plays nothing, quietly.
  const SOUNDS_BASE = new URL("../sounds/", document.currentScript ? document.currentScript.src : location.href);
  const samples = new Map(); // url -> Promise of an AudioBuffer, or null

  function loadSample(path) {
    if (!samples.has(path)) {
      samples.set(path, (async () => {
        try {
          const response = await fetch(new URL(path, SOUNDS_BASE));
          if (!response.ok) return null;
          return await ctx.decodeAudioData(await response.arrayBuffer());
        } catch {
          return null;
        }
      })());
    }
    return samples.get(path);
  }

  let ctx = null;
  let master = null;
  let musicBus = null;
  let sfxBus = null;
  let noise = null;
  let muted = false;
  let wanted = null; // the game's music, as the game asked for it
  let playing = null; // the loop actually running now
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

  // ---- The music. A song is a track with layers (core, top, bass, chords, lead, extra, drive, climax), each with its own
  // gain. The tier (0 to 6) brings layers in on the next bar; the climax layer fades in and out over half a bar; a splash
  // plays a one-bar stinger on the next beat. The drums of the layered songs are the CC0 kit's one-shots (synth drums when a
  // kit file is missing). Minigames and the older songs play the full mix, as they always have.

  const MINIGAME_KEYS = new Set(["memory", "cups", "invaders", "runner", "higher_lower"]); // their own fixed music
  const LAYERS = ["core", "top", "bass", "chords", "lead", "extra", "drive", "climax", "tension"];
  const FULL_MIX = ["core", "top", "bass", "chords", "lead"]; // the layers of a song that isn't layered (and the minigames)
  // The layers on at each tier. Each tier adds a part you can hear.
  const TIER_LAYERS = [
    ["core", "bass"],
    ["core", "bass", "top"],
    ["core", "bass", "top", "chords"],
    ["core", "bass", "top", "chords", "lead"],
    ["core", "bass", "top", "chords", "lead", "extra"],
    ["core", "bass", "top", "chords", "lead", "extra", "drive"],
    ["core", "bass", "top", "chords", "lead", "extra", "drive"],
  ];
  const TIER_OF_LEVEL = [0, 2, 4, 6]; // setLevel(0 to 3), kept until play.js is rewired
  const LOUD = 1.25; // the top tier is a little louder
  const KIT = ["kick", "snare", "hat", "open", "ride", "crash", "tom_low", "tom_high", "clap", "cowbell", "rim"];
  const KIT_GAIN = { kick: 0.8, snare: 0.6, hat: 0.5, open: 0.5, ride: 0.5, crash: 0.45, tom_low: 0.6, tom_high: 0.6, clap: 0.5, cowbell: 0.5, rim: 0.5 };
  const kitBuffers = {}; // name -> AudioBuffer, once loaded

  let tier = 0;
  let climaxOn = false;
  let matchPoint = false; // at match point, the tier is at least 5 and the tension layer comes in
  const tracks = []; // the songs playing, the newest last; an old one is fading out
  let pumpTimer = 0;

  const barSeconds = (key) => (4 * 60) / (STYLES[key].bpm || 120);
  const isLayered = (key) => Boolean(STYLES[key].layered);

  // The gain each layer should have now, for this song.
  function layerTarget(key, name) {
    if (name === "climax") return isLayered(key) && climaxOn ? 1 : 0;
    if (name === "tension") return isLayered(key) && matchPoint ? 1 : 0;
    if (!isLayered(key)) return FULL_MIX.includes(name) ? 1 : 0;
    const effective = matchPoint ? Math.max(tier, 5) : tier; // at match point the drive is on, whatever the tier
    if (!TIER_LAYERS[effective].includes(name)) return 0;
    return effective === 6 ? LOUD : 1;
  }

  const lowpass = (freq, bus) => {
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = freq;
    filter.connect(bus);
    return filter;
  };

  // A soft clip, for the guitar.
  function driveCurve(amount) {
    const curve = new Float32Array(1024);
    for (let i = 0; i < curve.length; i++) {
      const x = (i / (curve.length - 1)) * 2 - 1;
      curve[i] = Math.tanh(amount * x) / Math.tanh(amount);
    }
    return curve;
  }

  // A chord from a scale degree: "power" is a root and a fifth through the distorted guitar; "clean", "keys" and "stab" are triads.
  function chord(style, degree, at, dur, shape, gain, out) {
    if (shape === "power") {
      tone(at, midi(note(style, degree, 0)), dur, "sawtooth", gain, null, out.guitar);
      tone(at, midi(note(style, degree + 4, 0)), dur, "sawtooth", gain, null, out.guitar);
      return;
    }
    const wave = shape === "keys" ? "sine" : shape === "stab" ? "square" : "triangle";
    for (const step of [0, 2, 4]) tone(at, midi(note(style, degree + step, 0)), dur, wave, gain, null, out.melody);
  }

  // A snare: a crack of noise over a short body (the synth drum).
  function snare(at, bus) {
    burst(at, 0.16, 1800, 0.3, "bandpass", bus);
    tone(at, 190, 0.1, "triangle", 0.12, 120, bus);
  }

  // The synth drums, for a song without its kit file (and the older songs, which keep their own drums).
  function synthDrum(name, at, gain, bus) {
    if (name === "kick") tone(at, 140, 0.12, "sine", gain, 45, bus);
    else if (name === "snare") snare(at, bus);
    else if (name === "tom_low") tone(at, 110, 0.25, "sine", gain * 0.5, 70, bus);
    else if (name === "tom_high") tone(at, 180, 0.2, "sine", gain * 0.5, 110, bus);
    else if (name === "cowbell") tone(at, 800, 0.12, "square", gain * 0.1, null, bus);
    else if (name === "clap") burst(at, 0.08, 1500, gain * 0.15, "bandpass", bus);
    else if (name === "rim") burst(at, 0.03, 2500, gain * 0.15, "bandpass", bus);
    else if (name === "crash" || name === "open" || name === "ride") burst(at, 0.4, 6000, gain * 0.12, "highpass", bus);
    else burst(at, 0.035, 7000, gain * 0.12, "highpass", bus); // hat
  }

  // A drum hit for a layered song: the kit's one-shot, scaled by the song's drum feel and this hit's gain (or the synth drum).
  function hit(name, at, bus, style, scale = 1) {
    const gain = KIT_GAIN[name] * (style.drumGain || 1) * scale;
    const buffer = kitBuffers[name];
    if (!buffer) {
      synthDrum(name, at, gain, bus);
      return;
    }
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    const trim = ctx.createGain();
    trim.gain.value = gain;
    source.connect(trim);
    trim.connect(bus);
    source.start(at);
  }

  // ---- One step (a sixteenth) of a style's loop, into the track's layers. A pattern repeats across the loop.

  function playStep(style, index, at, stepDur, L) {
    const i = index % (style.loop || 16);
    const pick = (list) => list[i % list.length];
    const layered = Boolean(style.layered);
    if (style.lead) {
      const lead = pick(style.lead);
      if (lead !== null) tone(at, midi(note(style, lead, 1)), stepDur * style.leadLen * 0.9, style.wave, style.leadGain, null, L.lead);
    }
    if (style.bass) {
      const bass = pick(style.bass);
      if (bass !== null) tone(at, midi(note(style, bass, 0) - 12), stepDur * style.bassLen * 0.9, style.bassWave || "triangle",
        style.bassGain, null, style.bassFilter ? lowpass(style.bassFilter, L.bass) : L.bass);
    }
    if (style.guitar) {
      const guitar = pick(style.guitar);
      if (guitar !== null && style.guitarShape === "arp") {
        const walk = [0, 2, 4, 2][(i >> 1) % 4]; // up the chord and back, one note per eighth
        tone(at, midi(note(style, guitar + walk, 0)), stepDur * style.guitarLen * 0.9, "triangle", style.guitarGain, null, L.chords);
      } else if (guitar !== null) chord(style, guitar, at, stepDur * style.guitarLen * 0.92, style.guitarShape, style.guitarGain, { melody: L.chords, guitar: L.guitar });
    }
    if (style.keys) {
      const keys = pick(style.keys);
      if (keys !== null) chord(style, keys, at, stepDur * style.keysLen * 0.95, "keys", style.keysGain, { melody: L.chords, guitar: L.guitar });
    }
    if (pick(style.kick)) {
      if (layered) hit("kick", at, L.core, style);
      else tone(at, 140, 0.12, "sine", style.kickGain || 0.5, 45, L.core);
    }
    if (style.snare && pick(style.snare)) {
      if (layered) hit("snare", at, L.core, style);
      else snare(at, L.core);
    }
    if (pick(style.hat)) {
      if (layered) hit(style.topKit || "hat", at, L.top, style);
      else burst(at, 0.035, 7000, style.hatGain || 0.05, "highpass", L.top);
    }
    if (layered) playLayers(style, i, at, stepDur, L);
  }

  // The layers only a layered song has: its extra part, the drive, and the climax.
  function playLayers(style, i, at, stepDur, L) {
    const pick = (list) => list[i % list.length];
    if (style.extra) {
      const e = pick(style.extra);
      if (e !== null) {
        if (style.extraKit) hit(style.extraKit, at, L.extra, style);
        else tone(at, midi(note(style, e, 1)), stepDur * 2 * 0.9, style.extraWave, style.extraGain, null, L.extra);
      }
    }
    // Drive: sixteenth hats, ghost snares, a crash on each bar, and the bass doubled an octave down.
    hit("hat", at, L.drive, style, 0.5);
    if (i % 8 === 6) hit("snare", at, L.drive, style, 0.3);
    if (i % 16 === 0) hit("crash", at, L.drive, style, 0.8);
    if (style.bass) {
      const bass = pick(style.bass);
      if (bass !== null) tone(at, midi(note(style, bass, 0) - 24), stepDur * style.bassLen * 0.9, style.bassWave || "triangle", style.bassGain, null, L.drive);
    }
    // Climax: double time, the lead an octave up, and a swell on each bar.
    if (i % 2 === 0) hit("kick", at, L.climax, style);
    else hit("hat", at, L.climax, style, 0.7);
    if (style.lead) {
      const lead = pick(style.lead);
      if (lead !== null) tone(at, midi(note(style, lead, 2)), stepDur * style.leadLen * 0.9, style.wave, style.leadGain, null, L.climax);
    }
    if (i % 16 === 0) burst(at, stepDur * 16, 1500, 0.06, "bandpass", L.climax);
    // Tension (match point): a heartbeat on each bar (beat 1, then just after), and a pad rising over the two bars, in the key.
    if (i % 16 === 0) hit("kick", at, L.tension, style, 0.4);
    if (i % 16 === 2) hit("kick", at, L.tension, style, 0.25);
    if (i === 0 && style.loop === 32) {
      const low = midi(note(style, 0, -1));
      const wave = style.tensionWave || "triangle";
      tone(at, low, stepDur * 32 * 0.95, wave, 0.03, low * 1.25, L.tension);
      const fifth = midi(note(style, 4, -1));
      tone(at, fifth, stepDur * 32 * 0.95, wave, 0.02, fifth * 1.25, L.tension);
    }
  }

  // The splash: a one-bar stinger, a tom fill with a crash, or a chord stab with a crash and a kick.
  function playSplash(style, bus, at, stepDur) {
    hit("crash", at, bus, style);
    if (style.splash === "stab") {
      chord(style, 0, at, stepDur * 8, style.guitarShape || "clean", 0.05, { melody: bus, guitar: bus });
      hit("kick", at, bus, style);
    } else {
      for (let k = 8; k < 16; k++) hit(k % 2 ? "tom_high" : "tom_low", at + k * stepDur, bus, style);
    }
  }

  function pump() {
    if (!ctx) return;
    for (const track of tracks) {
      const style = STYLES[track.key];
      if (!style || style.sample || track.dead) continue;
      const stepDur = 60 / style.bpm / 4;
      if (track.nextTime < ctx.currentTime - 0.5) track.nextTime = ctx.currentTime + 0.05; // after a pause, don't rush to catch up
      while (track.nextTime < ctx.currentTime + STEP_LOOKAHEAD) {
        playStep(style, track.stepIndex, track.nextTime, stepDur, track.layers);
        track.stepIndex += 1;
        track.nextTime += stepDur;
      }
    }
  }

  // A track: its layers, each through its own gain, into the track's gain (for the crossfade), into the music bus.
  function makeTrack(key) {
    const bus = ctx.createGain();
    bus.gain.value = 0; // faded in by beginTrack
    bus.connect(musicBus);
    const layers = {};
    for (const name of LAYERS) {
      layers[name] = ctx.createGain();
      layers[name].gain.value = layerTarget(key, name);
      layers[name].connect(bus);
    }
    // The distorted guitar: a soft clip, then the top rolled off, into the chords.
    const clip = ctx.createWaveShaper();
    clip.curve = driveCurve(4);
    const guitarTone = ctx.createBiquadFilter();
    guitarTone.type = "lowpass";
    guitarTone.frequency.value = 2400;
    clip.connect(guitarTone);
    guitarTone.connect(layers.chords);
    layers.guitar = clip;
    return { key, bus, layers, sources: [], stepIndex: 0, nextTime: 0, dead: false, t0: 0, splashBus: null, splashBuffer: null, splashes: 0 };
  }

  // A ramp to `to` from now until `at + seconds`, starting at `at`.
  function ramp(param, to, at, seconds) {
    param.cancelScheduledValues(at);
    param.setValueAtTime(param.value, at);
    param.linearRampToValueAtTime(to, at + seconds);
  }

  // The next bar line of a track (the layers change there).
  function nextBar(track) {
    const barSec = barSeconds(track.key);
    const k = Math.max(0, Math.ceil((ctx.currentTime - track.t0) / barSec - 1e-9));
    return track.t0 + k * barSec;
  }

  // Each layer goes to its target: the tier's layers on the next bar, the climax over half a bar.
  function applyLayers(track, initial = false) {
    const now = ctx.currentTime;
    const barSec = barSeconds(track.key);
    const bar = nextBar(track);
    for (const name of LAYERS) {
      const to = layerTarget(track.key, name);
      if (initial) track.layers[name].gain.value = to;
      else if (name === "climax") ramp(track.layers[name].gain, to, now, barSec / 2);
      else if (name === "tension") ramp(track.layers[name].gain, to, bar, barSec);
      else ramp(track.layers[name].gain, to, bar, 0.15);
    }
  }

  function fadeTo(bus, to, seconds) {
    const now = ctx.currentTime;
    if (seconds <= 0) {
      bus.gain.setValueAtTime(to, now);
      return;
    }
    ramp(bus.gain, to, now, seconds);
  }

  function stopTrack(track) {
    if (track.dead) return;
    track.dead = true;
    for (const source of track.sources) {
      try { source.stop(); } catch { /* already stopped */ }
      source.disconnect();
    }
    track.bus.disconnect();
    const at = tracks.indexOf(track);
    if (at >= 0) tracks.splice(at, 1);
    if (!tracks.length) {
      clearInterval(pumpTimer);
      pumpTimer = 0;
    }
    playing = tracks.length ? tracks[tracks.length - 1].key : null;
  }

  function stopMusic() {
    for (const track of [...tracks]) stopTrack(track);
    clearInterval(pumpTimer);
    pumpTimer = 0;
    playing = null;
  }

  // A CC0 song: its layer loops (cc0_N_<layer>.wav; a missing one is silent), with its splash kept for a stinger. If none of
  // its layer files are there, its one loop plays, as before.
  async function beginSample(track) {
    const style = STYLES[track.key];
    const base = style.sample.replace(/\.wav$/, "");
    const names = [...LAYERS, "splash"];
    const buffers = await Promise.all(names.map((name) => loadSample(`${base}_${name}.wav`)));
    if (track.dead) return;
    if (buffers.some(Boolean)) {
      names.forEach((name, n) => {
        const buffer = buffers[n];
        if (!buffer) return;
        if (name === "splash") {
          track.splashBuffer = buffer;
          return;
        }
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.loop = true;
        const trim = ctx.createGain();
        trim.gain.value = style.gain || 0.8;
        source.connect(trim);
        trim.connect(track.layers[name]);
        source.start(track.t0);
        track.sources.push(source);
      });
      return;
    }
    const buffer = await loadSample(style.sample);
    if (!buffer || track.dead) return; // missing: the song is quiet, as before
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.loop = true;
    const gain = ctx.createGain();
    gain.gain.value = style.gain || 0.8;
    source.connect(gain);
    gain.connect(track.bus);
    source.start(track.t0);
    track.sources.push(source);
  }

  // Starts a song. With `fade` (seconds), the songs playing fade out as this one fades in; without, they stop at once.
  function beginTrack(key, fade = 0) {
    if (!ctx || muted || !STYLES[key]) return;
    const current = tracks[tracks.length - 1];
    if (current && current.key === key && !current.dead) return; // already playing
    for (const old of [...tracks]) {
      if (fade > 0) {
        fadeTo(old.bus, 0, fade);
        setTimeout(() => stopTrack(old), fade * 1000 + 50);
      } else {
        stopTrack(old);
      }
    }
    const track = makeTrack(key);
    track.t0 = ctx.currentTime + 0.05;
    track.nextTime = track.t0;
    tracks.push(track);
    playing = key;
    fadeTo(track.bus, 1, fade);
    if (STYLES[key].sample) {
      beginSample(track);
      return;
    }
    if (!pumpTimer) pumpTimer = setInterval(pump, PUMP_MS);
    pump();
  }

  // The tier, 0 to 6: the layers come in or out on the next bar.
  function setTierNow(n) {
    const next = Math.round(Number(n));
    if (Number.isNaN(next)) return;
    tier = Math.max(0, Math.min(6, next));
    if (ctx) for (const track of tracks) applyLayers(track);
  }

  // A splash on the next beat. A new one replaces the one playing; they don't stack.
  function splash() {
    if (!ctx || muted) return;
    const track = tracks[tracks.length - 1];
    if (!track) return;
    const beat = barSeconds(track.key) / 4;
    const at = track.t0 + Math.max(0, Math.ceil((ctx.currentTime - track.t0) / beat - 1e-9)) * beat;
    if (track.splashBus) track.splashBus.disconnect();
    const bus = ctx.createGain();
    bus.connect(track.bus);
    track.splashBus = bus;
    track.splashes += 1;
    const style = STYLES[track.key];
    if (style.sample) {
      if (track.splashBuffer) {
        const source = ctx.createBufferSource();
        source.buffer = track.splashBuffer;
        source.connect(bus);
        source.start(at);
      }
      return;
    }
    if (isLayered(track.key)) playSplash(style, bus, at, beat / 4);
  }

  // The kit's one-shots, loaded once (the first time the engine is made); a missing file leaves its synth drum in place.
  function preloadKit() {
    for (const name of KIT) {
      loadSample(`music/kit/${name}.wav`).then((buffer) => {
        if (buffer) kitBuffers[name] = buffer;
      });
    }
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

  // The sound effects of a song. A synth song uses the engine's own cues; a CC0 song uses its kit's sounds, and a kit sound
  // that's missing falls back to the synth cue. A name the bank doesn't have plays the effect of that name, as before.
  const SYNTH_BANK = { hit: "hit", block: "shield", play: "flip", win: "win", lose: "lose", draw: "reveal", damage: "hit" };
  const KIT_BANK = {
    hit: { sample: "music/cc0/kit/hit.wav" }, // Frankensnare: snare
    block: { sample: "music/cc0/kit/block.wav" }, // Swirly: closed hat
    play: { sample: "music/cc0/kit/play.wav" }, // Swirly: closed hat
    win: { sample: "music/cc0/kit/win.wav" }, // Swirly: crash
    lose: { sample: "music/cc0/kit/lose.wav" }, // Big Rusty: kick
    draw: { sample: "music/cc0/kit/draw.wav" }, // Swirly (Gogodze): cowbell
    damage: { sample: "music/cc0/kit/damage.wav" }, // Big Rusty: kick
  };
  const bankFor = (key) => (!STYLES[key] || MINIGAME_KEYS.has(key) ? null : STYLES[key].sample ? KIT_BANK : SYNTH_BANK);

  // A kit sound, played when it's loaded; if the file is missing, the synth cue plays instead.
  function playKit(path, fallbackCue) {
    loadSample(path).then((buffer) => {
      if (muted || !ctx) return;
      if (!buffer) {
        if (SFX[fallbackCue]) SFX[fallbackCue](ctx.currentTime + 0.01);
        return;
      }
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(sfxBus);
      source.start(ctx.currentTime + 0.01);
    });
  }

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
    preloadKit();
    if (wanted) beginTrack(wanted, 0);
  }

  for (const type of ["pointerdown", "keydown", "touchend"]) {
    document.addEventListener(type, unlock, { capture: true });
  }

  // A hidden tab stops the music (the games pause themselves too); it comes back when the tab does, if a game is on.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopMusic();
    } else if (wanted) {
      beginTrack(wanted, 0);
    }
  });

  window.MinigameAudio = {
    // The game's music, switched at once. Starting again for the same game is harmless.
    start(key) {
      if (!STYLES[key]) return;
      wanted = key;
      beginTrack(key, 0);
    },
    // A song change: the song playing fades out and this one fades in over about a bar, at the current tier.
    setSong(key) {
      if (!STYLES[key]) return;
      wanted = key;
      beginTrack(key, barSeconds(key));
    },
    // The tier, 0 to 6: the layers of the song that are on. Each tier adds a part; the change comes on the next bar.
    setTier: setTierNow,
    // Kept until play.js moves to setTier: 0 to 3 maps to tiers 0, 2, 4 and 6.
    setLevel(n) {
      const next = Math.round(Number(n));
      if (Number.isNaN(next)) return;
      setTierNow(TIER_OF_LEVEL[Math.max(0, Math.min(3, next))]);
    },
    // The climax: its layer fades in (or out) over half a bar.
    setClimax(on) {
      climaxOn = Boolean(on);
      if (ctx) for (const track of tracks) applyLayers(track);
    },
    // Match point: the drive is on whatever the tier, and the tension layer comes in over a bar. Off, the tier is as set.
    setMatchPoint(on) {
      matchPoint = Boolean(on);
      if (ctx) for (const track of tracks) applyLayers(track);
    },
    // A one-bar stinger, on the next beat. A new one replaces the one playing.
    splash,
    // The game's end (or a new game): the music stops. Effects, such as the win or lose sound, still play.
    stop() {
      wanted = null;
      stopMusic();
    },
    // A short effect, by name (see SFX), or by the song's bank (see SYNTH_BANK and KIT_BANK). Silent when muted.
    sfx(name) {
      lastSfx = name;
      if (muted || !ctx) return;
      const current = tracks[tracks.length - 1];
      const bank = current ? bankFor(current.key) : null;
      const entry = bank && bank[name];
      if (entry && typeof entry === "object") {
        playKit(entry.sample, SYNTH_BANK[name]);
        return;
      }
      const cue = entry || name;
      if (SFX[cue]) SFX[cue](ctx.currentTime + 0.01);
    },
    // Mute silences the music and the effects. The shell keeps the button and its saved setting.
    setMuted(on) {
      muted = Boolean(on);
      if (master) master.gain.setTargetAtTime(muted ? 0 : 0.8, ctx.currentTime, 0.05);
      if (muted) stopMusic();
      else if (wanted) beginTrack(wanted, 0);
    },
    muted() {
      return muted;
    },
    // For tests and the shell: what is playing, the tier, the climax, and the layers' targets for the current song.
    status() {
      const main = tracks[tracks.length - 1];
      const layers = main ? Object.fromEntries(LAYERS.map((name) => [name, layerTarget(main.key, name)])) : null;
      return {
        ready: Boolean(ctx), playing, step: main ? main.stepIndex : 0, muted, wanted, lastSfx,
        clock: ctx ? ctx.currentTime : 0, tier, climax: climaxOn, tracks: tracks.length, layers,
        splashes: main ? main.splashes : 0, kit: Object.keys(kitBuffers).length,
        sources: main ? main.sources.length : 0, splashReady: Boolean(main && main.splashBuffer), matchPoint,
      };
    },
  };
})();
