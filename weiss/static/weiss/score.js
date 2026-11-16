// The battle music: an original piece written as code and played live in the browser (Web Audio), so the
// game can rearrange it as it goes. Nothing is a recording: every note is picked at the moment it's due,
// which is what lets the game's moments play *into* the music instead of over the top of it.
//
// - Versions. The piece has four arrangements, picked by how far the game has got: a lounge for the setup and
//   first turns, a groove, a drive once someone reaches level 2 (or a clock fills up), and a showdown at level 3.
//   Each level reached on the table moves the key up (D, E, F, G minor). Changes land on the next bar.
//   The opponent's turn is heard a little muffled; an attack phase brings in toms and a driving bass; a climax
//   in play adds brass; the end of a game resolves to a major chord or sinks to a minor one, and stops.
//   At match point (a player at level 3 with 4 or more in the clock) it strips back to the brink: pad,
//   bass and a heartbeat, the quietest the game gets when the most is riding on it.
// - Sections. Each version walks two eight-bar progressions in turn (A, then B), and the A section carries a
//   hook: a two-bar phrase asked at its top and answered four bars later, played from the chords as they go.
//   Drum fills and the keys' comping change from one pass to the next, so it takes minutes to come round again.
// - Themes (setTheme). A CPU opponent gets its own: a key, a tempo, which progressions, a hook and what plays
//   it, all made from its name, so it's the same every time it's fought. A boss's runs hotter and darker.
//   Anyone else gets the house theme.
// - Cues (Score.cue). A moment on the board lands on the next sixteenth or beat, played from the chord that is
//   sounding, so it is always in time and in tune. Cues in a row climb (three draws are three rising notes).
//   They feed energy (busier drums, the arpeggio) or tension (the music darkens, a heartbeat comes in), both
//   wearing off over a bar or two. And the last bar's cues are echoed back over the next chord, in the rhythm
//   they happened in, and again a bar later, quieter: in harmony once three kinds of moment are in it, with
//   a crash and a drum fill at four. So what happens, and in what order, changes what you hear.
// - The other side's cues are an octave down and muffled, as if from across the table.
//
// play.js makes one with WeissScore.create(audioContext, output), tells it about the board with setState
// and its moments with cue. score_preview.html renders it offline, for listening to without a game.
(function () {
  "use strict";

  const BPM = 94; // the house theme's
  const BEAT = 4; // sixteenths
  const BAR = 16;
  const LOOKAHEAD = 0.3; // seconds of music scheduled ahead of the clock
  const TICK_MS = 50;
  const TONIC = 50; // D3, as MIDI
  const MINE = 67; // the bottom of our cues' register (G4); the other side's is an octave down
  const THEIRS = 55;
  // The music under the cues, at the default music level (0.6): low enough that a cue stands out without
  // being loud, and that the music stays clear of the limiter (which would flatten the difference between the
  // quiet versions and the busy ones). setMusicLevel scales it.
  const MUSIC_LEVEL = 0.4;
  const DEFAULT_MUSIC = 0.6;

  const hz = (midi) => 440 * 2 ** ((midi - 69) / 12);
  const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
  // A note moved by octaves into [lo, lo + 12).
  const fold = (midi, lo) => lo + ((((midi - lo) % 12) + 12) % 12);

  // Chords, as semitones above their root.
  const MIN9 = [0, 3, 7, 10, 14];
  const MAJ9 = [0, 4, 7, 11, 14];
  const DOM9 = [0, 4, 7, 10, 14];
  const HALF = [0, 3, 6, 10];
  const ALT = [0, 4, 7, 10, 13];
  const MADD9 = [0, 3, 7, 14];
  // Eight bars each, a chord a bar, as [root above the key's tonic, chord]; each set is played A, B, A, B...
  // Every B ends on the dominant, leading back into A's tonic.
  const HOME_SETS = {
    // A: i - iv - bVII - bIII - bVI - ii - V - i, the walk round the key. B: out to the major side and back.
    house: [
      [[0, MIN9], [5, MIN9], [10, DOM9], [3, MAJ9], [8, MAJ9], [2, HALF], [7, ALT], [0, MADD9]],
      [[8, MAJ9], [10, DOM9], [3, MAJ9], [0, MIN9], [5, MIN9], [10, DOM9], [3, MAJ9], [7, ALT]],
    ],
    // Falling through the major chords of the key, then climbing back.
    drift: [
      [[0, MIN9], [8, MAJ9], [3, MAJ9], [10, DOM9], [0, MIN9], [5, MIN9], [8, MAJ9], [7, ALT]],
      [[5, MIN9], [10, DOM9], [3, MAJ9], [8, MAJ9], [2, HALF], [7, ALT], [0, MIN9], [7, ALT]],
    ],
    // Dorian: the minor tonic swapping with a bright IV.
    dorian: [
      [[0, MIN9], [5, DOM9], [0, MIN9], [5, DOM9], [10, MAJ9], [5, DOM9], [2, HALF], [7, ALT]],
      [[10, MAJ9], [8, MAJ9], [0, MIN9], [5, DOM9], [3, MAJ9], [2, HALF], [0, MIN9], [7, ALT]],
    ],
  };
  // Level 3 (and the brink): it stops wandering and circles the tonic, leaning on the dominant at the end.
  const SHOWDOWN = [
    [[0, MIN9], [8, MAJ9], [10, DOM9], [0, MIN9], [0, MIN9], [8, MAJ9], [5, MIN9], [7, ALT]],
    [[5, MIN9], [7, ALT], [0, MIN9], [8, MAJ9], [5, MIN9], [3, MAJ9], [2, HALF], [7, ALT]],
  ];
  // A boss's: the flat second (bII) pulling at the tonic.
  const BOSS_SHOWDOWN = [
    [[0, MIN9], [1, MAJ9], [0, MIN9], [8, MAJ9], [0, MIN9], [1, MAJ9], [10, DOM9], [7, ALT]],
    [[8, MAJ9], [1, MAJ9], [5, MIN9], [7, ALT], [0, MIN9], [1, MAJ9], [2, HALF], [7, ALT]],
  ];
  const KEYS = [0, 2, 3, 5]; // the key, above D (and the theme's shift), at the highest level on the table

  // The house hook: [step in the two bars, note of the chord counting up from G4, length in sixteenths]. The
  // call ends up in the air; the answer, in the same rhythm, comes down.
  const HOUSE_HOOK = {
    call: [[0, 4, 3], [3, 5, 3], [6, 4, 2], [8, 6, 6], [16, 5, 2], [18, 4, 2], [20, 3, 4], [26, 4, 6]],
    answer: [[0, 4, 3], [3, 5, 3], [6, 4, 2], [8, 3, 6], [16, 2, 2], [18, 1, 2], [20, 2, 4], [26, 0, 6]],
  };
  // The rhythms a theme's hook can take, as [step, length] over two bars.
  const HOOK_RHYTHMS = [
    [[0, 3], [3, 3], [6, 2], [8, 6], [16, 2], [18, 2], [20, 4], [26, 6]],
    [[0, 2], [2, 2], [4, 4], [10, 2], [12, 4], [16, 6], [24, 2], [26, 6]],
    [[0, 6], [6, 2], [8, 2], [10, 6], [16, 3], [19, 3], [22, 2], [24, 8]],
    [[2, 2], [4, 2], [6, 4], [12, 4], [18, 2], [20, 2], [22, 4], [28, 4]],
  ];
  const HOOK_VOICES = ["lead", "bell", "pluck", "keys"];

  const LAYERS = ["pad", "keys", "bass", "kit", "hats", "arp", "lead", "hook", "brass", "echo"];
  // Each arrangement's level for each layer; a layer left out is silent.
  const ARRANGEMENTS = {
    lounge: { pad: 0.9, keys: 0.85, bass: 0.6, hats: 0.5, hook: 0.55, echo: 1 },
    groove: { pad: 0.55, keys: 1, bass: 1, kit: 0.8, hats: 0.75, hook: 0.8, echo: 1 },
    drive: { pad: 0.55, keys: 0.9, bass: 1, kit: 1, hats: 0.9, arp: 0.6, hook: 0.65, echo: 1 },
    showdown: { pad: 0.75, keys: 0.75, bass: 1, kit: 1, hats: 1, arp: 0.75, lead: 0.7, echo: 1 },
    brink: { pad: 1, keys: 0.6, bass: 0.9, kit: 0.7, hats: 0.6, lead: 0.5, echo: 1 },
    coda: { pad: 1, keys: 0.8, bass: 0.8, echo: 0 },
  };
  // How much of each layer goes to the reverb.
  const REVERB = { pad: 0.5, keys: 0.3, bass: 0, kit: 0.08, hats: 0.05, arp: 0.3, lead: 0.4, hook: 0.35, brass: 0.25, echo: 0.55 };
  // The keys' comping, [step, length, velocity], in the A section and the B.
  const COMP = {
    lounge: [[[0, 10, 0.3], [10, 5, 0.18]], [[0, 6, 0.28], [6, 4, 0.16], [12, 4, 0.2]]],
    groove: [[[0, 3, 0.28], [6, 2, 0.2], [10, 3, 0.24]], [[0, 2, 0.26], [3, 3, 0.2], [8, 2, 0.22], [11, 4, 0.22]]],
    drive: [[[2, 1.5, 0.22], [6, 1.5, 0.2], [10, 1.5, 0.22], [14, 1.5, 0.18]], [[0, 1.5, 0.22], [3, 1.5, 0.2], [6, 1.5, 0.2], [10, 3, 0.22]]],
    showdown: [[[0, 7, 0.24], [8, 7, 0.2]], [[0, 3, 0.24], [4, 3, 0.18], [8, 7, 0.22]]],
    brink: [[[0, 14, 0.16]], [[0, 14, 0.16]]],
  };

  // A number from a string, and numbers from a number: the same name always makes the same theme.
  function hashOf(text) {
    let h = 2166136261;
    for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
    return h >>> 0;
  }
  function random(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // The theme for an opponent: {name, boss}, or nothing for the house theme.
  function makeTheme({ name = "", boss = false } = {}) {
    const id = `${name}|${boss ? "boss" : ""}`;
    const showdown = boss ? BOSS_SHOWDOWN : SHOWDOWN;
    if (!name) {
      return { id, seed: 0, shift: 0, bpm: BPM + (boss ? 6 : 0), home: HOME_SETS.house, showdown, hook: HOUSE_HOOK, voice: "lead", boss };
    }
    const seed = hashOf(name);
    const rng = random(seed);
    const pick = (list) => list[Math.floor(rng() * list.length)];
    const shift = pick([-3, -2, -1, 0, 1, 2, 3]);
    const bpm = 88 + Math.floor(rng() * 15) + (boss ? 6 : 0);
    const home = HOME_SETS[pick(Object.keys(HOME_SETS))];
    const voice = pick(HOOK_VOICES);
    // The hook: a walk over the chord's notes, the call ending up high and the answer coming home.
    const rhythm = pick(HOOK_RHYTHMS);
    let degree = 3 + Math.floor(rng() * 3);
    const walk = rhythm.map(() => {
      const here = degree;
      degree = clamp(degree + pick([-2, -1, -1, 1, 1, 2]), 1, 7);
      return here;
    });
    const call = rhythm.map(([step, len], n) => [step, n === rhythm.length - 1 ? Math.max(walk[n], 5) : walk[n], len]);
    const answer = rhythm.map(([step, len], n) => {
      const fromEnd = rhythm.length - 1 - n;
      return [step, fromEnd === 0 ? 0 : fromEnd === 1 ? Math.min(walk[n], 2) : walk[n], len];
    });
    return { id, seed, shift, bpm, home, showdown, hook: { call, answer }, voice, boss };
  }

  class Score {
    constructor(ctx, output) {
      this.ctx = ctx;
      this.now = () => ctx.currentTime; // a preview rendering offline sets its own clock
      this.running = false;
      this.volume = 0.6;
      this.musicLevel = DEFAULT_MUSIC;
      this.theme = makeTheme();
      this.stepDur = 60 / this.theme.bpm / 4; // a sixteenth, in seconds
      this.state = { setup: true, level: 0, clock: 0, turn: 0, myTurn: true, attacking: false, climax: false, matchPoint: false, over: null };
      this.plans = new Map(); // bar -> what that bar plays, fixed when it's first needed
      this.recent = []; // cues lately: {type, step, degree, opponent}
      this.runs = {}; // side + cue -> {step, run}, for cues in a row
      this.lastCueStep = -1;
      this.energy = 0;
      this.tension = 0;
      this.sparkle = 0;
      this.lastBar = -1;
      this.buildMixer(output);
    }

    // A sixteenth, in seconds, at this theme's tempo: what cues time their notes by.
    get STEP() {
      return this.stepDur;
    }

    // --- The mixer -------------------------------------------------------------------------------
    // Layers -> the music filter (muffled on their turn, darkened by tension) -> the music level -> the duck
    // (dips under damage) -> the master volume -> out. Our cues skip the filter and the duck, so they sit on top
    // of the music; the other side's go through their own muffle. Both feed a delay timed to the music (a dotted eighth).
    buildMixer(output) {
      const ctx = this.ctx;
      const gain = (value, to) => {
        const node = ctx.createGain();
        node.gain.value = value;
        if (to) node.connect(to);
        return node;
      };
      this.master = gain(0, output);
      this.duck = gain(1, this.master);
      this.filter = ctx.createBiquadFilter();
      this.filter.type = "lowpass";
      this.filter.frequency.value = 16000;
      this.filter.Q.value = 0.5;
      this.bed = gain(MUSIC_LEVEL, this.duck);
      this.filter.connect(this.bed);
      this.musicIn = gain(1, this.filter);

      const reverb = ctx.createConvolver();
      reverb.buffer = this.impulse(2.4);
      reverb.connect(gain(0.35, this.filter));
      this.reverbIn = gain(1, reverb);

      this.layers = {};
      for (const name of LAYERS) {
        const layer = gain(0, this.musicIn);
        if (REVERB[name]) layer.connect(gain(REVERB[name], this.reverbIn));
        this.layers[name] = layer;
      }

      this.delay = ctx.createDelay(2);
      this.delay.delayTime.value = this.stepDur * 3;
      const delayTone = ctx.createBiquadFilter();
      delayTone.type = "lowpass";
      delayTone.frequency.value = 3200;
      this.delay.connect(delayTone);
      delayTone.connect(gain(0.38, this.delay)); // feedback
      delayTone.connect(gain(0.6, this.master));
      this.delayIn = gain(0.18, this.delay);

      this.cueMine = gain(1, this.master);
      this.cueMine.connect(this.delayIn);
      this.cueMine.connect(gain(0.25, this.reverbIn));
      const muffle = ctx.createBiquadFilter();
      muffle.type = "lowpass";
      muffle.frequency.value = 2000;
      muffle.connect(gain(0.8, this.master));
      muffle.connect(this.delayIn);
      this.cueTheirs = gain(1, muffle);

      this.noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
      const data = this.noiseBuffer.getChannelData(0);
      for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    }

    impulse(seconds) {
      const length = Math.floor(this.ctx.sampleRate * seconds);
      const buffer = this.ctx.createBuffer(2, length, this.ctx.sampleRate);
      for (let channel = 0; channel < 2; channel++) {
        const data = buffer.getChannelData(channel);
        for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / length) ** 3;
      }
      return buffer;
    }

    // --- Starting, stopping, volume, the theme and the board -----------------------------------------

    start({ timer = true } = {}) {
      if (this.running) return;
      this.running = true;
      const now = this.now();
      this.origin = now + 0.1;
      this.step = 0;
      this.lastBar = -1;
      this.plans.clear();
      this.recent = [];
      this.runs = {};
      this.lastCueStep = -1;
      this.master.gain.cancelScheduledValues(now);
      this.master.gain.setTargetAtTime(this.volume, now, 0.4);
      if (timer) this.timer = setInterval(() => this.pump(this.now() + LOOKAHEAD), TICK_MS);
      this.pump(now + LOOKAHEAD);
    }

    stop() {
      if (!this.running) return;
      this.running = false;
      clearInterval(this.timer);
      const now = this.now();
      this.master.gain.cancelScheduledValues(now);
      this.master.gain.setTargetAtTime(0, now, 0.12);
    }

    // Everything, cues and music: 0 to 1.
    setVolume(volume) {
      this.volume = volume;
      if (this.running) this.master.gain.setTargetAtTime(volume, this.now(), 0.08);
    }

    // The music under the cues, 0 to 1 (0.6 is the default balance); the cues stay as they are.
    setMusicLevel(level) {
      this.musicLevel = clamp(level, 0, 1);
      this.bed.gain.setTargetAtTime(MUSIC_LEVEL * (this.musicLevel / DEFAULT_MUSIC), this.now(), 0.08);
    }

    // Whose music it is: {name, boss} for a CPU's theme, or nothing for the house theme. A new one takes over
    // at the next bar, from the top of its progression; its tempo from the next sixteenth not yet scheduled.
    setTheme(options) {
      const theme = makeTheme(options || {});
      if (theme.id === this.theme.id) return;
      this.theme = theme;
      const dur = 60 / theme.bpm / 4;
      if (dur === this.stepDur) return;
      if (this.running) this.origin = this.timeOf(this.step) - this.step * dur;
      this.stepDur = dur;
      this.delay.delayTime.setTargetAtTime(dur * 3, this.now(), 0.05);
    }

    // What the music follows: {setup, level (the highest on the table), clock (the fullest), turn, myTurn,
    // attacking, climax (one in play), matchPoint (someone's a few damage from losing), over (null, "win" or
    // "lose")}. Heard from the next bar.
    setState(state) {
      this.state = { ...this.state, ...state };
      // A filling clock brings the drive in at 5 and lets it go at 3 (a level up empties it), so a card
      // healed off it, or one more damage, doesn't flip the music back and forth from bar to bar.
      if (this.state.clock >= 5) this.clockHigh = true;
      else if (this.state.clock <= 3) this.clockHigh = false;
    }

    // --- The clock ----------------------------------------------------------------------------------

    timeOf(step) {
      return this.origin + step * this.stepDur;
    }

    // Everything due before `until` that isn't scheduled yet. A tab that was held up skips what it missed.
    pump(until) {
      const late = this.now() - this.timeOf(this.step);
      if (late > 0.05) this.step += Math.ceil(late / this.stepDur);
      while (this.timeOf(this.step) < until) {
        this.playStep(this.step, this.timeOf(this.step));
        this.step += 1;
      }
    }

    // Which arrangement the board calls for.
    versionFor(st) {
      const boss = this.theme.boss;
      if (st.over) return "coda";
      if (st.setup) return "lounge";
      if (st.matchPoint && st.level >= 3) return "brink";
      if (st.level >= 3 || (boss && st.level >= 2)) return "showdown";
      if (st.level >= 2 || this.clockHigh || (boss && st.level >= 1)) return "drive";
      return st.level === 0 && st.turn <= 2 ? "lounge" : "groove";
    }

    // What a bar plays: decided from the board the first time anything asks, and kept. `keep` false only
    // peeks (as the bass does, for the note leading into the next chord), so the board can still change it.
    plan(bar, keep = true) {
      const known = this.plans.get(bar);
      if (known) return known;
      const st = this.state;
      const prev = this.plans.get(bar - 1);
      const name = this.versionFor(st);
      const key = KEYS[clamp(st.level || 0, 0, 3)] + this.theme.shift;
      const prog = name === "showdown" || name === "brink" ? "showdown" : "home";
      const theme = this.theme.id;
      // A new key, progression or theme starts from the top, so it lands on its tonic; a new arrangement doesn't.
      const fresh = !prev || prev.key !== key || prev.prog !== prog || prev.theme !== theme || (prev.name === "coda") !== (name === "coda");
      const plan = {
        bar, name, key, prog, theme, since: fresh ? bar : prev.since,
        chords: this.theme[prog], // kept with the bar, so a theme arriving mid-bar waits for the next
        hook: this.theme.hook,
        mix: { ...ARRANGEMENTS[name] },
        myTurn: st.myTurn !== false,
        battle: Boolean(st.attacking) && name !== "coda",
        climax: Boolean(st.climax) && name !== "coda",
        over: st.over,
      };
      if (this.theme.boss && name === "showdown") plan.mix.brass = 0.3;
      if (plan.climax) plan.mix.brass = 0.55;
      // At the brink an attack brings the drums back in, for the toms.
      if (name === "brink" && plan.battle) plan.mix.kit = 1;
      if (!keep) return plan;
      this.plans.set(bar, plan);
      this.plans.delete(bar - 8);
      return plan;
    }

    // Where a bar is in its progression: {loop (0 to 7, the bar in the section), section (0 for A, 1 for B)}.
    placeOf(plan, bar) {
      const into = bar - plan.since;
      return { loop: into % 8, section: Math.floor(into / 8) % 2 };
    }

    // The chord sounding at a step: {root (MIDI), tones}.
    chordAt(step, keep = true) {
      const bar = Math.floor(step / BAR);
      const plan = this.plan(bar, keep);
      if (plan.name === "coda") {
        const into = bar - plan.since;
        if (plan.over === "win") return { root: TONIC + plan.key, tones: [0, 4, 7, 11, 14] };
        return into === 0 ? { root: TONIC + plan.key + 5, tones: MIN9 } : { root: TONIC + plan.key, tones: MIN9 };
      }
      const { loop, section } = this.placeOf(plan, bar);
      const [root, tones] = plan.chords[section][loop];
      return { root: TONIC + plan.key + root, tones };
    }

    // The chord's notes going up from `lo`, for three octaves: what melodies are picked from.
    ladder(chord, lo) {
      const classes = new Set(chord.tones.map((t) => (chord.root + t) % 12));
      const notes = [];
      for (let m = lo; m < lo + 36; m++) if (classes.has(m % 12)) notes.push(m);
      return notes;
    }

    // The chord's notes without its root (the bass has that), close together from `lo`.
    voicing(chord, lo) {
      return chord.tones.slice(1).map((t) => fold(chord.root + t, lo)).sort((a, b) => a - b);
    }

    // --- The arrangement, a sixteenth at a time ------------------------------------------------------

    playStep(step, t) {
      const STEP = this.stepDur;
      const bar = Math.floor(step / BAR);
      const i = step % BAR;
      const plan = this.plan(bar);
      if (bar !== this.lastBar) {
        this.lastBar = bar;
        this.startBar(plan, bar, t);
      }
      if (i % BEAT === 0) this.beat(plan, t);
      if (plan.name === "coda") {
        this.coda(plan, bar, i, t);
        return;
      }
      const chord = this.chordAt(step);
      const name = plan.name;
      const brink = name === "brink";
      const L = this.layers;
      const on = (layer) => this.heard[layer];
      const { loop, section } = this.placeOf(plan, bar);

      // Pad: the chord held across the bar.
      if (i === 0 && on("pad")) this.pad(t, this.voicing(chord, 57), BAR * STEP, 0.16, L.pad);

      // Keys: an electric piano comping, a different figure in each section.
      if (on("keys")) {
        for (const [at, len, vel] of COMP[name][section]) {
          if (at === i) for (const note of this.voicing(chord, 60)) this.keys(t, note, len * STEP, vel, L.keys);
        }
      }

      // Bass.
      if (on("bass")) {
        const root = fold(chord.root, 38);
        const fifth = root + chord.tones[2];
        const seventh = root + chord.tones[3];
        // A semitone under the next chord's root, leading into it (a peek: the next bar isn't decided yet).
        const approach = i === 14 ? fold(this.chordAt((bar + 1) * BAR, false).root, 38) - 1 : 0;
        let line;
        if (brink) {
          line = { 0: [root, 7], 8: [root, 7] };
        } else if (plan.battle || name === "drive" || name === "showdown") {
          line = { 0: [root, 1.5], 2: [root, 1], 4: [root + 12, 1], 6: [root, 1], 8: [fifth, 1.5], 10: [root, 1], 12: [root + 12, 1], 14: [approach, 1] };
        } else if (name === "groove" && section === 1) {
          line = { 0: [root, 1.5], 3: [root + 12, 1], 4: [fifth, 1.5], 7: [root, 1], 8: [root, 1.5], 10: [seventh, 1.5], 12: [fifth, 1], 14: [approach, 1] };
        } else if (name === "groove") {
          line = { 0: [root, 2.5], 3: [root, 1.5], 6: [root + 12, 1], 8: [fifth, 1.5], 10: [root, 2], 14: [approach, 1] };
        } else {
          line = { 0: [root, 7], 8: [fifth, 7] };
        }
        // Under tension the bass holds back: short notes, so the heartbeat can be heard.
        if (line[i]) this.bass(t, line[i][0], line[i][1] * STEP * (this.tension > 0.35 ? 0.5 : 1), 0.5, L.bass);
      }

      // Drums.
      if (on("kit")) {
        if (brink) {
          // Only a kick on the one, and the toms in an attack.
          if (i === 0) this.kick(t, 0.7, L.kit);
        } else {
          const kicks = name === "showdown" ? [0, 4, 8, 10, 12] : name === "drive" ? [0, 6, 10] : [0, 10];
          const filling = loop === 7 && i >= 12;
          if (!filling && (kicks.includes(i) || (plan.battle && (i === 3 || i === 11)))) this.kick(t, i === 0 ? 0.95 : 0.75, L.kit);
          if (!filling && (i === 4 || i === 12)) this.snare(t, 0.55, L.kit);
          if (name !== "showdown" && i === 7) this.snare(t, 0.12, L.kit); // a ghost note
          // The end of the section: a fill into the top, a different one each pass.
          if (filling) this.fill(bar, i, t, chord, L.kit);
          // Halfway through B, a pickup.
          if (section === 1 && loop === 3 && i >= 14) this.snare(t, 0.18 + (i - 14) * 0.1, L.kit);
          if (loop === 0 && i === 0 && bar !== plan.since) this.crash(t, 0.25, L.kit);
        }
        // In an attack: toms rolling down into the next bar.
        if (plan.battle && bar % 2 === 1 && i >= 12 && i % 2 === 0) this.tom(t, fold(chord.root, 45) - (i - 12) * 2, 0.45, L.kit);
      }
      if (this.flourish === bar && i >= 12) this.snare(t, 0.25 + (i - 12) * 0.1, L.echo);
      // The heartbeat, while tension is high: lub-dub on each half bar.
      if (this.tension > 0.3 && (i === 0 || i === 2 || i === 8 || i === 10)) {
        this.kick(t, (i % 8 === 0 ? 0.55 : 0.4) * Math.min(1, this.tension * 1.6), this.duck);
      }

      // Hats (a shaker, in the lounge). More energy, more of them; at the brink, a tick like a clock.
      if (on("hats")) {
        const sixteenths = name === "drive" || name === "showdown" || this.energy > 0.45;
        if (brink) {
          if (i % 4 === 2) this.hat(t, 0.12, L.hats);
        } else if (name === "lounge") {
          if (i % 2 === 0 || this.energy > 0.45) this.shaker(t, i % 4 === 0 ? 0.22 : 0.14, L.hats);
        } else if (i % 2 === 0 || sixteenths) {
          const open = (name === "showdown" && i % 4 === 2) || (name === "groove" && i === 14 && bar % 2 === 1);
          this.hat(t, i % 4 === 0 ? 0.3 : i % 2 === 0 ? 0.22 : 0.13, L.hats, open);
        }
      }

      // Arpeggio: up and down the chord in sixteenths.
      if (on("arp")) {
        const notes = this.ladder(chord, 62);
        const pattern = section === 1 ? [0, 2, 1, 3, 2, 4, 3, 1] : [0, 1, 2, 3, 4, 3, 2, 1];
        this.pluck(t, notes[pattern[i % 8]], i % 2 === 0 ? 0.2 : 0.13, L.arp, 0.7);
      }

      // Lead (the showdown): a slow line falling through the top of each chord. At the brink, one high bell a bar.
      if (on("lead")) {
        const notes = this.ladder(chord, 64);
        if (brink) {
          if (i === 0) this.bell(t, notes[5 + (bar % 2)], 0.1, L.lead, 2.4);
        } else if (i === 0 || i === 8) {
          this.lead(t, notes[(i === 0 ? 5 : 4) + (bar % 2)], 7 * STEP, 0.13, L.lead);
        }
      }

      // The hook, in the A section: asked in its first two bars, answered in its fifth and sixth.
      if (on("hook") && section === 0 && [0, 1, 4, 5].includes(loop)) {
        const phrase = loop < 4 ? plan.hook.call : plan.hook.answer;
        const at = (loop % 4) * BAR + i;
        for (const [when, degree, len] of phrase) {
          if (when === at) this.hookNote(t, this.ladder(chord, 62)[degree], len * STEP, L.hook);
        }
      }

      // Brass (a climax in play, or a boss's showdown): a swell on each bar.
      if (on("brass") && i === 0) this.brass(t, this.voicing(chord, 55), 12 * STEP, 0.14, L.brass);
    }

    // The last four sixteenths of a section: one of a few fills, picked by the bar (so it's the same if asked twice).
    fill(bar, i, t, chord, out) {
      const k = i - 12;
      switch ((Math.floor(bar / 8) + this.theme.seed) % 4) {
        case 0: // a snare roll, building
          this.snare(t, 0.2 + k * 0.12, out);
          break;
        case 1: // toms falling round the kit
          this.tom(t, fold(chord.root, 45) + 7 - k * 3, 0.4 + k * 0.05, out);
          break;
        case 2: // snare, snare, kick, snare with an open hat
          if (k === 2) this.kick(t, 0.8, out);
          else this.snare(t, 0.3 + k * 0.08, out);
          if (k === 3) this.hat(t, 0.25, out, true);
          break;
        default: // a gap, then one big hit into the top
          if (k === 3) {
            this.snare(t, 0.6, out);
            this.kick(t, 0.8, out);
          }
      }
    }

    // A note of the hook, in the theme's voice.
    hookNote(t, midi, dur, out) {
      switch (this.theme.voice) {
        case "bell": this.bell(t, midi, 0.13, out, Math.max(1, dur * 2)); break;
        case "pluck": this.pluck(t, midi, 0.24, out, 1.1); break;
        case "keys": this.keys(t, midi + 12, dur, 0.2, out); break;
        default: this.lead(t, midi, dur, 0.12, out);
      }
    }

    // The start of a bar: layers fade to this arrangement's levels over a beat, and last bar's cues echo.
    startBar(plan, bar, t) {
      const before = this.levels || {};
      this.levels = {};
      this.heard = {};
      for (const name of LAYERS) {
        let level = plan.mix[name] || 0;
        // Energy brings a little of the next arrangement in early.
        if (name === "arp" && plan.name === "groove") level = Math.max(level, (this.energy - 0.3) * 0.8);
        if (name === "kit" && plan.name === "lounge") level = Math.max(level, (this.energy - 0.4) * 0.9);
        level = Math.max(0, level);
        this.levels[name] = level;
        // A layer coming on, or fading out, gets its notes (so one fading out finishes its bar).
        this.heard[name] = level > 0.01 || (before[name] || 0) > 0.01;
        const g = this.layers[name].gain;
        g.cancelScheduledValues(t);
        g.setTargetAtTime(level, t, (BEAT * this.stepDur) / 3);
      }
      if (plan.name !== "coda") this.echo(bar);
    }

    // Each beat: energy and tension wear off (though never below the brink's), and the music's filter and the
    // delay follow them and whose turn it is.
    beat(plan, t) {
      this.energy *= 0.9;
      this.tension *= 0.87;
      this.sparkle *= 0.85;
      if (plan.name === "brink") this.tension = Math.max(this.tension, 0.4);
      const open = plan.myTurn || plan.name === "coda" ? 16000 : 3400;
      const cutoff = Math.max(450, open * (1 - 0.85 * this.tension));
      this.filter.frequency.setTargetAtTime(cutoff, t, 0.12);
      this.delayIn.gain.setTargetAtTime(0.18 + this.sparkle * 0.45, t, 0.1);
    }

    // The last bar's cues, again over this bar's chords, at the same places in the bar; the bar before's, quieter.
    echo(bar) {
      for (const [ago, level] of [[1, 0.5], [2, 0.22]]) {
        const from = (bar - ago) * BAR;
        const cues = this.recent.filter((c) => c.step >= from && c.step < from + BAR && c.degree !== null).slice(-6);
        if (cues.length < 2) continue; // one moment on its own isn't worth repeating
        const kinds = new Set(cues.map((c) => c.type)).size;
        for (const c of cues) {
          const step = c.step + ago * BAR;
          const notes = this.ladder(this.chordAt(step), c.opponent ? THEIRS : MINE);
          const at = this.timeOf(step);
          this.mallet(at, notes[Math.min(c.degree, notes.length - 1)], 0.32 * level, this.layers.echo);
          if (kinds >= 3) this.mallet(at, notes[Math.min(c.degree + 1, notes.length - 1)], 0.22 * level, this.layers.echo);
        }
        if (ago === 1 && kinds >= 4) {
          this.flourish = bar;
          this.crash(this.timeOf(bar * BAR), 0.3, this.layers.echo);
        }
      }
    }

    // The game is over: a final chord or two, then quiet. A win rings out the start of the hook.
    coda(plan, bar, i, t) {
      const into = bar - plan.since;
      if (i !== 0 || into > 1) return;
      const STEP = this.stepDur;
      const chord = this.chordAt(bar * BAR);
      const L = this.layers;
      if (plan.over === "win") {
        if (into) return;
        this.crash(t, 0.35, this.cueMine);
        this.pad(t, this.voicing(chord, 57), 4 * BAR * STEP, 0.2, L.pad);
        this.bass(t, fold(chord.root, 38), 3 * BAR * STEP, 0.5, L.bass);
        const notes = this.ladder(chord, 62);
        const opening = this.theme.hook.call.filter(([when]) => when < BAR).slice(0, 5);
        opening.forEach(([when, degree]) => this.bell(t + when * STEP, notes[degree], 0.16, this.cueMine));
        const last = opening.length ? opening[opening.length - 1][0] + 4 : 0;
        this.bell(t + last * STEP, fold(chord.root, 74), 0.18, this.cueMine, 2.6);
      } else {
        this.pad(t, this.voicing(chord, 55), (into ? 4 : 1) * BAR * STEP, 0.18, L.pad);
        this.bass(t, fold(chord.root, 38) - (into ? 12 : 0), (into ? 3 : 1) * BAR * STEP, 0.45, L.bass);
        if (into) this.bell(t, fold(chord.root, 62), 0.12, this.cueMine);
      }
    }

    // --- Cues ---------------------------------------------------------------------------------------

    // A moment on the board, played into the music. `opponent`: the other side's, lower and muffled. `count`:
    // how many cards it was (a damage's, flipped one by one); `icons`: a trigger check's trigger icons. Returns how
    // many seconds from now it lands, so the board can show it on the beat (or null if it isn't played).
    cue(type, { opponent = false, count = 1, icons = [] } = {}) {
      const def = CUES[type];
      if (!this.running || !def) return null;
      const nowStep = (this.now() + 0.03 - this.origin) / this.stepDur;
      // A cue with a `lead` builds into its landing: at least that many sixteenths away.
      let step = Math.ceil((nowStep + (def.lead || 0)) / def.grid) * def.grid;
      // Several at once play as a figure, one after another, rather than piling onto one note.
      if (step <= this.lastCueStep) step = Math.ceil((this.lastCueStep + 1) / def.grid) * def.grid;
      if (step - nowStep > BAR / 2) return null; // a flood of them: the rest only add to the mood
      if (this.plan(Math.floor(step / BAR)).name === "coda") return null;
      const side = opponent ? "theirs" : "mine";
      const last = this.runs[side + type];
      const run = last && step - last.step <= 12 ? last.run + 1 : 0;
      this.runs[side + type] = { step, run };
      const chord = this.chordAt(step);
      const c = {
        t: this.timeOf(step), step, chord, run, opponent, count: clamp(Math.round(count) || 1, 1, 8), icons,
        notes: this.ladder(chord, opponent ? THEIRS : MINE),
        out: opponent ? this.cueTheirs : this.cueMine,
        vel: opponent ? 0.8 : 1,
      };
      // A cue that takes a while (a damage's flips) holds the next one back until it's done.
      this.lastCueStep = step + (def.span ? def.span(c) : 0);
      const degree = def.play(this, c);
      this.recent.push({ type, step, degree: degree ?? null, opponent });
      this.recent = this.recent.filter((r) => r.step > step - 3 * BAR);
      const weight = opponent ? 0.7 : 1;
      const tension = typeof def.tension === "function" ? def.tension(c) : def.tension;
      this.energy = clamp(this.energy + (def.energy || 0) * weight, 0, 1);
      this.tension = tension === "release" ? 0 : clamp(this.tension + (tension || 0) * weight, 0, 1);
      this.sparkle = clamp(this.sparkle + (def.sparkle || 0), 0, 1);
      return Math.max(0, c.t - this.now());
    }

    // A damage's cards turned over one at a time before what they came to: a tick each, climbing, over a
    // riser once there are a few. The time the last one lands, for the payoff.
    flips(c) {
      const STEP = this.stepDur;
      const n = c.count - 1;
      for (let k = 0; k < n; k++) {
        const t = c.t + k * STEP;
        this.pluck(t, c.notes[Math.min(k, c.notes.length - 1)], (0.14 + 0.04 * k) * c.vel, c.out, 0.6);
        this.hat(t, (0.1 + 0.04 * k) * c.vel, c.out);
      }
      if (n >= 2) this.riser(c.t, n * STEP, 0.14 * c.vel, c.out);
      return c.t + n * STEP;
    }

    // --- Instruments ----------------------------------------------------------------------------------
    // Each plays one note (or chord) into `out` at time `t` and cleans up after itself.

    osc(type, freq, t, end) {
      const node = this.ctx.createOscillator();
      node.type = type;
      node.frequency.setValueAtTime(freq, t);
      node.start(t);
      node.stop(end);
      return node;
    }

    noise(t, end) {
      const node = this.ctx.createBufferSource();
      node.buffer = this.noiseBuffer;
      node.start(t, Math.random() * 1.5);
      node.stop(end);
      return node;
    }

    filtered(type, freq, q = 0.7) {
      const node = this.ctx.createBiquadFilter();
      node.type = type;
      node.frequency.value = freq;
      node.Q.value = q;
      return node;
    }

    // A gain shaped like a note: up to `peak` over `attack`, falling towards `sustain` x peak, let go at `t + hold`.
    envelope(t, { attack = 0.005, peak, decay = 0.3, sustain = 0, hold, release = 0.1 }, out) {
      const node = this.ctx.createGain();
      const g = node.gain;
      g.setValueAtTime(0, t);
      g.linearRampToValueAtTime(peak, t + attack);
      g.setTargetAtTime(peak * sustain, t + attack, decay / 3);
      if (hold !== undefined) g.setTargetAtTime(0, t + Math.max(hold, attack), release / 3);
      node.connect(out);
      return node;
    }

    // A struck percussive gain: `peak` falling away over `seconds`.
    hit(t, peak, seconds, out) {
      const node = this.ctx.createGain();
      node.gain.setValueAtTime(peak, t);
      node.gain.exponentialRampToValueAtTime(0.0001, t + seconds);
      node.connect(out);
      return node;
    }

    // Electric piano: a sine bent by another (FM), bright as it's struck and mellowing.
    keys(t, midi, dur, vel, out) {
      const f = hz(midi);
      const end = t + dur + 0.5;
      const carrier = this.osc("sine", f, t, end);
      const mod = this.osc("sine", f, t, end);
      const depth = this.ctx.createGain();
      depth.gain.setValueAtTime(f * 1.6, t);
      depth.gain.setTargetAtTime(f * 0.2, t, 0.15);
      mod.connect(depth).connect(carrier.frequency);
      carrier.connect(this.envelope(t, { peak: vel, decay: 1.2, sustain: 0.35, hold: dur, release: 0.35 }, out));
    }

    bass(t, midi, dur, vel, out) {
      const f = hz(midi);
      const end = t + dur + 0.2;
      const amp = this.envelope(t, { peak: vel, decay: 0.4, sustain: 0.6, hold: dur, release: 0.06 }, out);
      const tone = this.filtered("lowpass", f * 8, 3);
      tone.frequency.setValueAtTime(Math.min(1800, f * 9), t);
      tone.frequency.setTargetAtTime(f * 2.5, t, 0.06);
      this.osc("sawtooth", f, t, end).connect(tone).connect(amp);
      const sub = this.ctx.createGain();
      sub.gain.value = 0.7;
      this.osc("sine", f, t, end).connect(sub).connect(amp);
    }

    pad(t, notes, dur, vel, out) {
      const end = t + dur + 1;
      const amp = this.envelope(t, { attack: Math.min(0.8, dur * 0.25), peak: vel, decay: 1, sustain: 1, hold: dur, release: 0.9 }, out);
      const tone = this.filtered("lowpass", 1100, 0.3);
      tone.connect(amp);
      const each = this.ctx.createGain();
      each.gain.value = 1 / notes.length;
      each.connect(tone);
      for (const note of notes) {
        for (const cents of [-7, 7]) {
          const o = this.osc("sawtooth", hz(note), t, end);
          o.detune.value = cents;
          o.connect(each);
        }
      }
    }

    // A plucked string, bright at first and closing quickly.
    pluck(t, midi, vel, out, bright = 1) {
      const f = hz(midi);
      const amp = this.envelope(t, { attack: 0.002, peak: vel, decay: 0.5, hold: 0.45, release: 0.1 }, out);
      const tone = this.filtered("lowpass", f * 10, 1);
      tone.frequency.setValueAtTime(Math.min(10000, f * 10 * bright), t);
      tone.frequency.setTargetAtTime(f * 1.5, t, 0.09);
      tone.connect(amp);
      this.osc("triangle", f, t, t + 0.6).connect(tone);
      const edge = this.ctx.createGain();
      edge.gain.value = 0.3;
      this.osc("square", f * 1.002, t, t + 0.6).connect(edge).connect(tone);
    }

    // A marimba-ish mallet: a round note with a quick high overtone.
    mallet(t, midi, vel, out) {
      const f = hz(midi);
      this.osc("sine", f, t, t + 1).connect(this.hit(t, vel, 0.9, out));
      this.osc("sine", f * 3.93, t, t + 0.15).connect(this.hit(t, vel * 0.25, 0.12, out));
    }

    // A bell: a note with the inharmonic overtones that make it ring.
    bell(t, midi, vel, out, seconds = 1.6) {
      const f = hz(midi);
      for (const [ratio, level] of [[1, 1], [2.76, 0.35], [5.4, 0.15]]) {
        const ring = seconds / Math.sqrt(ratio);
        this.osc("sine", f * ratio, t, t + ring + 0.05).connect(this.hit(t, vel * level, ring, out));
      }
    }

    brass(t, notes, dur, vel, out) {
      const end = t + dur + 0.4;
      const amp = this.envelope(t, { attack: 0.04, peak: vel, decay: 0.5, sustain: 0.6, hold: dur, release: 0.25 }, out);
      const tone = this.filtered("lowpass", 300, 1.5);
      tone.frequency.setValueAtTime(300, t);
      tone.frequency.linearRampToValueAtTime(2600, t + 0.08);
      tone.frequency.setTargetAtTime(1100, t + 0.08, 0.3);
      tone.connect(amp);
      const each = this.ctx.createGain();
      each.gain.value = 1 / notes.length;
      each.connect(tone);
      for (const note of notes) {
        for (const cents of [-5, 6]) {
          const o = this.osc("sawtooth", hz(note), t, end);
          o.detune.value = cents;
          o.connect(each);
        }
      }
    }

    // A soft square lead, its vibrato coming in as the note is held.
    lead(t, midi, dur, vel, out) {
      const f = hz(midi);
      const end = t + dur + 0.4;
      const o = this.osc("square", f, t, end);
      const lfo = this.osc("sine", 5.2, t, end);
      const wobble = this.ctx.createGain();
      wobble.gain.setValueAtTime(0, t);
      wobble.gain.linearRampToValueAtTime(f * 0.007, t + 0.5);
      lfo.connect(wobble).connect(o.frequency);
      o.connect(this.filtered("lowpass", 1700, 1))
        .connect(this.envelope(t, { attack: 0.08, peak: vel, decay: 0.4, sustain: 0.75, hold: dur, release: 0.3 }, out));
    }

    kick(t, vel, out) {
      const o = this.osc("sine", 150, t, t + 0.45);
      o.frequency.exponentialRampToValueAtTime(42, t + 0.12);
      o.connect(this.hit(t, vel, 0.4, out));
    }

    snare(t, vel, out) {
      this.noise(t, t + 0.2).connect(this.filtered("bandpass", 1900, 0.8)).connect(this.hit(t, vel, 0.15, out));
      this.osc("triangle", 190, t, t + 0.1).connect(this.hit(t, vel * 0.5, 0.08, out));
    }

    hat(t, vel, out, open = false) {
      const len = open ? 0.25 : 0.04;
      this.noise(t, t + len + 0.02).connect(this.filtered("highpass", 7500)).connect(this.hit(t, vel, len, out));
    }

    shaker(t, vel, out) {
      const amp = this.envelope(t, { attack: 0.018, peak: vel, decay: 0.06, hold: 0.05, release: 0.03 }, out);
      this.noise(t, t + 0.12).connect(this.filtered("bandpass", 5500, 1.2)).connect(amp);
    }

    tom(t, midi, vel, out) {
      const f = hz(midi);
      const o = this.osc("sine", f * 1.5, t, t + 0.4);
      o.frequency.exponentialRampToValueAtTime(f, t + 0.15);
      o.connect(this.hit(t, vel, 0.35, out));
    }

    crash(t, vel, out) {
      this.noise(t, t + 1.8).connect(this.filtered("highpass", 3500)).connect(this.hit(t, vel, 1.7, out));
    }

    // Noise rising in pitch and volume over `dur`, into whatever comes next.
    riser(t, dur, vel, out) {
      const tone = this.filtered("bandpass", 400, 1.5);
      tone.frequency.setValueAtTime(400, t);
      tone.frequency.exponentialRampToValueAtTime(6000, t + dur);
      const amp = this.ctx.createGain();
      amp.gain.setValueAtTime(0.0001, t);
      amp.gain.exponentialRampToValueAtTime(vel, t + dur);
      amp.gain.linearRampToValueAtTime(0, t + dur + 0.03);
      amp.connect(out);
      this.noise(t, t + dur + 0.05).connect(tone).connect(amp);
    }

    // Damage: the music dips out from under the hit and comes back over a beat.
    duckUnder(t, depth) {
      const g = this.duck.gain;
      g.cancelScheduledValues(t);
      g.setTargetAtTime(1 - depth, t, 0.01);
      g.setTargetAtTime(1, t + 0.08, 0.3);
    }
  }

  // Each cue: `grid` is what it lands on (1 a sixteenth, 2 an eighth, 4 a beat); `play` returns the step of
  // the chord it played (the note the echo repeats), or nothing to leave it out of the echo. `energy`,
  // `tension` and `sparkle` are what it adds to the mood ("release" clears the tension; tension can depend on
  // the cue). `span`: how many sixteenths after its first it takes, which the next cue waits for.
  const CUES = {
    // A card drawn: a plucked note, a step higher for each one in a row.
    draw: {
      grid: 1, energy: 0.08,
      play(s, c) {
        const degree = 2 + (c.run % 6);
        s.pluck(c.t, c.notes[degree], 0.42 * c.vel, c.out);
        return degree;
      },
    },
    // A card put anywhere else: a soft mallet on one of the chord's lower notes, never the same twice running.
    move: {
      grid: 1, energy: 0.05,
      play(s, c) {
        const last = s.lastMove ?? -1;
        const choices = [1, 2, 3, 4].filter((d) => d !== last);
        const degree = choices[Math.floor(Math.random() * choices.length)];
        s.lastMove = degree;
        s.mallet(c.t, c.notes[degree], 0.38 * c.vel, c.out);
        return degree;
      },
    },
    // A card into the clock: a low pluck on the root and a tick, like a counter going over.
    clock: {
      grid: 2, tension: 0.12,
      play(s, c) {
        s.bass(c.t, fold(c.chord.root, 38) + (c.opponent ? 0 : 12), s.STEP * 1.5, 0.45 * c.vel, c.out);
        s.hat(c.t, 0.35 * c.vel, c.out);
        return 0;
      },
    },
    // Damage: its cards ticking over one by one, then a hit with the music ducking under it, and the floor
    // dropping out (a semitone slide down onto the root). The more cards, the more it hurts.
    damage: {
      grid: 1, energy: 0.1,
      tension: (c) => 0.3 + 0.05 * (c.count - 1),
      span: (c) => c.count - 1,
      play(s, c) {
        const STEP = s.STEP;
        const t = s.flips(c);
        s.duckUnder(t, Math.min(0.85, 0.55 + c.run * 0.1 + (c.count - 1) * 0.04));
        s.kick(t, 1 * c.vel, c.out);
        s.tom(t, fold(c.chord.root, 40) - c.run, 0.6 * c.vel, c.out);
        const root = fold(c.chord.root, 38);
        const f = hz(root + 1);
        const o = s.osc("sawtooth", f, t, t + BEAT * STEP + 0.2);
        o.frequency.setTargetAtTime(hz(root), t + STEP, 0.08);
        o.connect(s.filtered("lowpass", 600, 2)).connect(s.envelope(t, { peak: 0.35 * c.vel, decay: 0.5, sustain: 0.4, hold: BEAT * STEP, release: 0.1 }, c.out));
        if (c.count >= 4) s.crash(t, 0.25 * c.vel, c.out);
        return 0;
      },
    },
    // A climax cancelled the damage: the cards ticking over until it turned up, then bells running up the chord,
    // and the tension let go.
    negated: {
      grid: 1, tension: "release", energy: 0.15, sparkle: 0.3,
      span: (c) => c.count - 1,
      play(s, c) {
        const t = s.flips(c);
        [2, 3, 4, 5].forEach((d, n) => s.bell(t + n * s.STEP, c.notes[d], 0.2 * c.vel, c.out, 1.2));
        s.hat(t, 0.15, c.out, true);
        return 5;
      },
    },
    // A level up: a run up the chord to the next bar, which lands with a crash and a brass hit (in the new key).
    level: {
      grid: 1, energy: 0.5, tension: "release",
      play(s, c) {
        const left = BAR - (c.step % BAR);
        const spacing = left < 4 ? s.STEP / 2 : s.STEP;
        const count = Math.min(10, left < 4 ? left * 2 : left);
        for (let n = 0; n < count; n++) s.pluck(c.t + n * spacing, c.notes[Math.min(n, c.notes.length - 1)], (0.2 + 0.25 * n / count) * c.vel, c.out, 1.2);
        const landing = c.step + left;
        const t = s.timeOf(landing);
        s.crash(t, 0.4 * c.vel, c.out);
        s.brass(t, s.voicing(s.chordAt(landing), 60), 6 * s.STEP, 0.3 * c.vel, c.out);
        return Math.min(count, 7);
      },
    },
    // A climax played: a riser and a snare roll building from now into the next beat but one sixteenth (the board
    // charges up meanwhile), then it lands: a kick, a crash and a brass stab on the chord, answered an octave up.
    climax: {
      grid: 4, lead: 2, energy: 0.5, tension: "release",
      play(s, c) {
        const from = Math.max(s.now() + 0.02, c.t - BEAT * s.STEP);
        const build = c.t - from;
        if (build > 0.05) {
          s.riser(from, build, 0.22 * c.vel, c.out);
          const rolls = Math.floor(build / (s.STEP / 2));
          for (let n = 0; n < rolls; n++) s.snare(c.t - (rolls - n) * s.STEP / 2, (0.05 + 0.2 * n / rolls) * c.vel, c.out);
        }
        s.kick(c.t, 0.9 * c.vel, c.out);
        s.crash(c.t, 0.4 * c.vel, c.out);
        s.brass(c.t, s.voicing(c.chord, 60), 3 * s.STEP, 0.4 * c.vel, c.out);
        s.brass(c.t + 4 * s.STEP, s.voicing(c.chord, 72), 4 * s.STEP, 0.3 * c.vel, c.out);
        return 4;
      },
    },
    // A refresh (the waiting room shuffled back in): a snare roll and a riser over a beat, and a crash.
    shuffle: {
      grid: 4, energy: 0.3,
      play(s, c) {
        for (let n = 0; n < 8; n++) s.snare(c.t + n * s.STEP / 2, (0.08 + n * 0.05) * c.vel, c.out);
        s.riser(c.t, BEAT * s.STEP, 0.25 * c.vel, c.out);
        s.crash(c.t + BEAT * s.STEP, 0.3 * c.vel, c.out);
      },
    },
    // Something needs our answer: two bells, left on an open note like a question.
    prompt: {
      grid: 4,
      play(s, c) {
        s.bell(c.t, c.notes[2], 0.2, c.out, 1.2);
        s.bell(c.t + 2 * s.STEP, c.notes[4], 0.17, c.out, 1.4);
      },
    },
    // An ability going off: a quick harp run up the chord, into the delay.
    ability: {
      grid: 1, energy: 0.15, sparkle: 0.5,
      play(s, c) {
        for (let n = 0; n < 6; n++) s.pluck(c.t + n * s.STEP / 2, c.notes[1 + n], 0.25 * c.vel, c.out, 1.3);
        return 6;
      },
    },
    // A trigger check: each icon its own sound, one after another (souls ring high, a shot cracks, a draw
    // plucks, the rest chime twice); a card with none, one dull note.
    trigger: {
      grid: 1, energy: 0.1, sparkle: 0.3,
      span: (c) => Math.max(0, Math.min(c.icons.length, 3) - 1) * 2,
      play(s, c) {
        const icons = c.icons.slice(0, 3);
        if (!icons.length) {
          s.mallet(c.t, c.notes[1], 0.22 * c.vel, c.out);
          return null;
        }
        icons.forEach((icon, n) => {
          const t = c.t + n * 2 * s.STEP;
          if (icon === "soul") s.bell(t, c.notes[5 + n], 0.2 * c.vel, c.out, 1.4);
          else if (icon === "shot") {
            s.snare(t, 0.45 * c.vel, c.out);
            s.pluck(t, c.notes[6], 0.3 * c.vel, c.out, 1.4);
          } else if (icon === "draw") s.pluck(t, c.notes[3 + n], 0.34 * c.vel, c.out, 1.2);
          else {
            s.bell(t, c.notes[3], 0.16 * c.vel, c.out, 1);
            s.bell(t + s.STEP, c.notes[5], 0.14 * c.vel, c.out, 1.2);
          }
        });
        return icons[0] === "soul" ? 5 : 3;
      },
    },
    // A character reversed in battle: a note falling away an octave, over a low tom.
    reversed: {
      grid: 2, energy: 0.12, tension: 0.06,
      play(s, c) {
        const STEP = s.STEP;
        const from = c.notes[4];
        const o = s.osc("triangle", hz(from), c.t, c.t + BEAT * STEP + 0.1);
        o.frequency.exponentialRampToValueAtTime(hz(from - 12), c.t + 3 * STEP);
        o.connect(s.filtered("lowpass", 2400, 1)).connect(s.hit(c.t, 0.3 * c.vel, BEAT * STEP, c.out));
        s.tom(c.t, fold(c.chord.root, 41), 0.45 * c.vel, c.out);
        s.mallet(c.t + 2 * STEP, c.notes[0], 0.22 * c.vel, c.out);
        return 0;
      },
    },
    // A CPU's climax combo cutting in: the brass and the harp run together.
    combo: {
      grid: 2, energy: 0.5, sparkle: 0.5,
      play(s, c) {
        s.brass(c.t, s.voicing(c.chord, 60), 6 * s.STEP, 0.32 * c.vel, c.out);
        for (let n = 0; n < 8; n++) s.pluck(c.t + n * s.STEP / 2, c.notes[1 + n], 0.22 * c.vel, c.out, 1.3);
        s.crash(c.t, 0.3 * c.vel, c.out);
        return 7;
      },
    },
    // An attack declared: two toms, low then lower.
    attack: {
      grid: 2, energy: 0.2,
      play(s, c) {
        const low = fold(c.chord.root, 43);
        s.tom(c.t, low + 7, 0.55 * c.vel, c.out);
        s.tom(c.t + s.STEP, low, 0.6 * c.vel, c.out);
      },
    },
  };

  window.WeissScore = {
    create: (ctx, output) => new Score(ctx, output),
    cues: Object.keys(CUES),
    theme: makeTheme,
    STEP: 60 / BPM / 4, BAR, LOOKAHEAD,
  };
})();
