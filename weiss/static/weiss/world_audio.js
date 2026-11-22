/* World mode's town sound (weiss/world_town.html).
   Music: score.js's lounge arrangement (the setup music of a duel), in the key and tempo of the CPU being talked to, so a
   duel with them carries on from the town's tune. The town's fade into the duel is in the fetch wrapper below.
   Ambience: quiet sound generated here, for the place and time: birds in the day, crickets at dusk and night, waves at
   the beach, wind in the forest, chatter in the café, a hum in the library and a crowd at the arena while the
   tournament's on. Layers crossfade as the place or time changes. Clicks: short CC0 sounds from sounds/ (Kenney).
   Nothing plays until the player first touches the page, it pauses when the tab's hidden, and the on/off setting is the
   duel's ("weiss-music"), so muting in one mutes in the other. Listens for "world:town" (world_town.js) for the place,
   time, today's events and who's being talked to. */
(() => {
  const root = document.querySelector("[data-world-town]");
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!root || !AudioCtx) return;
  const base = new URL("sounds/", document.currentScript ? document.currentScript.src : location.href);

  const MUSIC_KEY = "weiss-music"; // shared with the duel page (play.js): "on" or "off"
  // The town's style, chosen on the music page (world_music): lofi is the town's lounge, as it has always been; a rock style
  // plays through the minigames' synthesized music (minigames/audio.js), loaded here when it's needed.
  const TOWN_MUSIC_KEY = "weiss-town-music";
  const TOWN_STYLES = ["lofi", "rock_1", "rock_2", "rock_3", "rock_4", "hip_hop", "jazz", "funk", "synthwave", "emo", "metal", "cc0_1", "cc0_2", "cc0_3", "cc0_4", "cc0_5", "cc0_6", "cc0_7", "cc0_8"];
  const SCRIPT_URL = document.currentScript ? document.currentScript.src : location.href;
  // The songs the town offers: the page's song list (the json_script "song-tracks", the tracks the staff haven't deleted).
  // TOWN_STYLES is only the fallback when that tag is missing. A chosen song that's no longer offered plays lofi.
  const readTownSongs = () => {
    try {
      const el = document.getElementById("song-tracks");
      const list = el ? JSON.parse(el.textContent) : null;
      if (Array.isArray(list)) return list.filter((t) => t && typeof t.key === "string").map((t) => t.key);
    } catch (e) { /* the fallback below */ }
    return TOWN_STYLES;
  };
  const TOWN_SONGS = readTownSongs();
  const storedStyle = (() => { try { return localStorage.getItem(TOWN_MUSIC_KEY); } catch { return null; } })();
  const townStyle = TOWN_SONGS.includes(storedStyle) ? storedStyle : "lofi";
  const isRock = () => townStyle !== "lofi";
  let minigameMusic = null; // the audio module's load, once started
  const VOLUME_KEY = "weiss-music-volume"; // 0 to 100: shared with the duel (play.js), the same music volume on both
  const OLD_VOLUME_KEY = "weiss-town-volume"; // the town's own before the duel shared one: migrated, then dropped
  const TOWN_MUSIC = 0.4; // score.js's music level for the town (its duel default is 0.6): calmer
  const AMBIENCE = 0.5; // the ambience under the music and the clicks
  const OUTDOORS = ["plaza", "shrine", "school", "forest"];
  const CLICKS = [ // [selector, sound], the first one that matches a button or link wins
    ["[data-wait], [data-menu-wait], [data-jump-go]", "shuffle"], // passing time
    [".town-place, [data-places] button", "travel"], // a place on the map
    [".town-option, [data-menu] button", "talk"], // what to say or do with someone
    ["[data-checkout], .town-stock button, .town-cards button, [data-gift-stock] button", "buy"],
    ["[data-open-map], [data-open-shop], [data-open-menu], [data-sheet-open], [data-sheet-close]", "open"],
  ];
  const FILES = {
    tap: ["card-slide-1.ogg", "card-slide-2.ogg"],
    shuffle: ["card-shuffle.ogg"],
    travel: ["card-place-1.ogg", "card-place-2.ogg"],
    talk: ["prompt.ogg"],
    buy: ["chip-lay-1.ogg", "chip-lay-2.ogg"],
    open: ["card-fan-1.ogg", "card-fan-2.ogg"],
  };
  const LAYERS = ["wind", "waves", "hum", "crowd", "chatter", "birds", "crickets"];

  const read = (key, fallback) => {
    try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
  };
  const write = (key, value) => {
    try { localStorage.setItem(key, value); } catch { /* only this visit, then */ }
  };
  const rand = (from, to) => from + Math.random() * (to - from);

  let on = read(MUSIC_KEY, "on") === "on";
  let stored = read(VOLUME_KEY, null);
  const old = read(OLD_VOLUME_KEY, null);
  if (stored === null && old !== null) {
    stored = old;
    write(VOLUME_KEY, old);
  }
  try { localStorage.removeItem(OLD_VOLUME_KEY); } catch { /* nothing to drop */ }
  let volume = stored !== null && Number.isFinite(Number(stored)) ? Number(stored) : 60; // the duel's default too
  let ctx = null; // made on the first touch (browsers won't play sound before one)
  let master, music, ambience, clicks, noise, score;
  let unlocking = false;
  const levels = {}; // layer -> its gain node, crossfaded
  const sounds = {}; // click sound -> decoded buffers
  let place = null; // a place key, as weiss.world_views.PLACES has them
  let time = 0; // 0 morning, 1 noon, 2 evening, 3 night
  let tournament = false; // the weekly tournament's on here
  let talking = null; // the CPU's name being talked to: the town's music takes its key (their profile name, as the duel's)
  let talkingNow = false; // someone's being talked to: the music and ambience duck under the words

  // ---- Building the sound ----

  function noiseBuffer() {
    const buffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    return buffer;
  }

  // A looping noise through a filter; the caller connects the filter onward.
  function noiseFilter(type, frequency, q) {
    const source = ctx.createBufferSource();
    source.buffer = noise;
    source.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = type;
    filter.frequency.value = frequency;
    filter.Q.value = q;
    source.connect(filter);
    source.start();
    return filter;
  }

  // A gain that swells slowly around `base`, so a sound comes and goes like waves or a murmur.
  function swell(target, base, rate, depth) {
    const gain = ctx.createGain();
    gain.gain.value = base;
    gain.connect(target);
    const wobble = ctx.createOscillator();
    wobble.frequency.value = rate;
    const amount = ctx.createGain();
    amount.gain.value = depth;
    wobble.connect(amount);
    amount.connect(gain.gain);
    wobble.start();
    return gain;
  }

  function tone(frequency, gain, target) {
    const osc = ctx.createOscillator();
    osc.frequency.value = frequency;
    const amp = ctx.createGain();
    amp.gain.value = gain;
    osc.connect(amp);
    amp.connect(target);
    osc.start();
  }

  // Each continuous layer: its sources feed `out`, the layer's own level.
  const BUILD = {
    wind(out) {
      const filter = noiseFilter("bandpass", 420, 0.5);
      filter.connect(swell(out, 0.7, 0.07, 0.3));
      const drift = ctx.createOscillator(); // the wind's pitch drifts up and down
      drift.frequency.value = 0.07;
      const depth = ctx.createGain();
      depth.gain.value = 260;
      drift.connect(depth);
      depth.connect(filter.frequency);
      drift.start();
    },
    waves(out) {
      noiseFilter("lowpass", 900, 0.5).connect(swell(out, 0.6, 0.1, 0.35));
    },
    hum(out) {
      tone(110, 0.035, out);
      tone(220, 0.012, out);
    },
    crowd(out) {
      noiseFilter("bandpass", 900, 0.5).connect(swell(out, 0.45, 0.35, 0.25));
      noiseFilter("bandpass", 2200, 0.8).connect(swell(out, 0.12, 0.6, 0.08));
    },
    chatter(out) {
      noiseFilter("bandpass", 650, 1.1).connect(swell(out, 0.4, 3.7, 0.35));
    },
    birds() {}, // chirps are scheduled, see scheduleChirps
    crickets() {}, // see scheduleCrickets
  };

  // One chirp: a short tone that glides up and back.
  function chirp(at, frequency, out, length, amp) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.setValueAtTime(frequency, at);
    if (length > 0.1) {
      osc.frequency.exponentialRampToValueAtTime(frequency * rand(1.3, 1.7), at + length * 0.4);
      osc.frequency.exponentialRampToValueAtTime(frequency * 0.9, at + length);
    }
    gain.gain.setValueAtTime(0, at);
    gain.gain.linearRampToValueAtTime(amp, at + length * 0.12);
    gain.gain.linearRampToValueAtTime(0, at + length);
    osc.connect(gain);
    gain.connect(out);
    osc.start(at);
    osc.stop(at + length + 0.02);
  }

  // Birds: a few chirps at a time, every few seconds, while the layer is up.
  function scheduleChirps() {
    const level = levels.birds;
    if (ctx && level && level.gain.value > 0.02) {
      const t = ctx.currentTime;
      const count = 1 + Math.floor(Math.random() * 3);
      for (let c = 0; c < count; c++) chirp(t + c * 0.22 + rand(0, 0.1), rand(2400, 3600), level, 0.16, 0.05);
    }
    setTimeout(scheduleChirps, rand(1800, 4200));
  }

  // Crickets: trains of quick ticks, high and steady, while the layer is up.
  function scheduleCrickets() {
    const level = levels.crickets;
    if (ctx && level && level.gain.value > 0.02) {
      const t = ctx.currentTime;
      for (let train = 0; train < 3; train++) {
        const start = t + train * 0.9 + rand(0, 0.2);
        for (let tick = 0; tick < 12; tick++) chirp(start + tick * 0.06, rand(4200, 4600), level, 0.03, 0.02);
      }
    }
    setTimeout(scheduleCrickets, 2600);
  }

  // The layers' levels for this place and time: birds by day, crickets from evening, the rest by place.
  function mix() {
    const birds = time <= 1 ? 1 : 0;
    const crickets = time >= 2 ? 1 : 0;
    const m = {};
    if (place === "cafe") m.chatter = time === 3 ? 0.35 : 0.9;
    else if (place === "library") m.hum = 0.45;
    else if (place === "arena") m.crowd = tournament ? 1 : 0;
    else if (place === "beach") Object.assign(m, { waves: 1, birds: birds * 0.6 });
    else if (place === "forest") Object.assign(m, { wind: 0.8, birds, crickets });
    else if (OUTDOORS.includes(place)) Object.assign(m, { birds: birds * 0.5, crickets: crickets * 0.6 });
    return m;
  }

  function applyAmbience() {
    if (!ctx) return;
    const wanted = mix();
    const now = ctx.currentTime;
    for (const name of LAYERS) {
      levels[name].gain.setTargetAtTime((wanted[name] || 0) * AMBIENCE, now, 1.2); // a slow crossfade
    }
  }

  // ---- The music ----

  function applyMusic() {
    if (!score || isRock()) return;
    score.setTheme(talking ? { name: talking } : {}); // the house theme when nobody's being talked to
    score.setState({ setup: true }); // the lounge: the calm arrangement
    score.setMusicLevel(TOWN_MUSIC);
  }

  // ---- Clicks ----

  function playClick(kind) {
    const list = sounds[kind];
    if (!ctx || !list || !list.length || !on) return;
    const source = ctx.createBufferSource();
    source.buffer = list[Math.floor(Math.random() * list.length)];
    source.playbackRate.value = rand(0.96, 1.04);
    source.connect(clicks);
    source.start();
  }

  function clickKind(el) {
    for (const [selector, kind] of CLICKS) if (el.closest(selector)) return kind;
    return "tap";
  }

  async function loadClicks() {
    for (const [kind, files] of Object.entries(FILES)) {
      const buffers = await Promise.all(files.map(async (file) => {
        try {
          const response = await fetch(new URL(file, base));
          return await ctx.decodeAudioData(await response.arrayBuffer());
        } catch {
          return null; // a sound that won't load is simply silent
        }
      }));
      sounds[kind] = buffers.filter(Boolean);
    }
  }

  // ---- Starting, stopping and the controls ----

  function applyVolume() {
    if (!master) return;
    master.gain.setTargetAtTime(on ? volume / 100 : 0, ctx.currentTime, 0.15);
  }

  function paintControls() {
    for (const toggle of root.querySelectorAll("[data-sound-toggle]")) {
      toggle.setAttribute("aria-pressed", String(on));
      toggle.classList.toggle("is-off", !on);
      toggle.title = on ? "Sound on: click to mute" : "Sound off: click to turn it on";
    }
    for (const slider of root.querySelectorAll("[data-sound-volume]")) slider.value = String(volume);
  }

  // The first touch makes the sound: browsers only allow it then.
  async function unlock() {
    if (ctx || unlocking) return;
    unlocking = true;
    ctx = new AudioCtx();
    master = ctx.createGain();
    master.connect(ctx.destination);
    music = ctx.createGain();
    music.connect(master);
    ambience = ctx.createGain();
    ambience.connect(master);
    clicks = ctx.createGain();
    clicks.gain.value = 0.35;
    clicks.connect(master);
    noise = noiseBuffer();
    for (const name of LAYERS) {
      const level = ctx.createGain();
      level.gain.value = 0;
      level.connect(ambience);
      levels[name] = level;
      BUILD[name](level);
    }
    if (window.WeissScore) score = window.WeissScore.create(ctx, music);
    applyVolume();
    duck();
    await loadClicks();
    scheduleChirps();
    scheduleCrickets();
    if (on) start();
    paintControls();
  }

  // The minigames' audio module, loaded the first time a rock style is wanted (it's a separate file, beside this one).
  function loadMinigameAudio() {
    if (window.MinigameAudio) return Promise.resolve();
    if (!minigameMusic) {
      minigameMusic = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = new URL("minigames/audio.js", SCRIPT_URL).href;
        script.onload = resolve;
        script.onerror = reject;
        document.head.append(script);
      });
    }
    return minigameMusic;
  }

  function start() {
    if (isRock()) {
      if (score && score.running) score.stop();
      loadMinigameAudio()
        .then(() => { if (on && isRock()) window.MinigameAudio.start(townStyle); })
        .catch(() => { /* the lounge can't stand in for it; the town is quiet */ });
      applyAmbience();
      applyVolume();
      return;
    }
    applyMusic();
    if (score && !score.running) score.start();
    applyAmbience();
    applyVolume();
  }

  function stop() {
    if (score && score.running) score.stop();
    if (window.MinigameAudio) window.MinigameAudio.stop();
    applyVolume();
  }

  function setOn(next) {
    on = next;
    write(MUSIC_KEY, on ? "on" : "off");
    if (on) {
      if (ctx) start();
      else unlock();
    } else {
      stop();
    }
    paintControls();
  }

  // The fade into a duel: the town's sound drops over 600 ms, while the page is about to change to the duel. The
  // duel's own request is let through as it is; if the page doesn't change, the sound comes back.
  function fadeOut(ms) {
    return new Promise((resolve) => {
      if (!ctx) return resolve();
      const now = ctx.currentTime;
      master.gain.cancelScheduledValues(now);
      master.gain.setValueAtTime(master.gain.value, now);
      master.gain.linearRampToValueAtTime(0, now + ms / 1000);
      setTimeout(resolve, ms);
    });
  }

  const realFetch = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    const request = realFetch(input, init);
    if (!url || !url.includes("/town/duel/") || !ctx) return request;
    return request.then(async (response) => {
      await fadeOut(600);
      setTimeout(applyVolume, 2500); // still here? the sound comes back
      return response;
    });
  };

  // ---- The town's state ----

  // The name of the person being talked to, as the town shows it: their profile's name, the same as the duel's CPU.
  const speakerName = () => root.querySelector(".town-person.town-chosen .town-tag")?.textContent || null;

  // The town's "world:town" detail: { place (a key), time (0-3), events (today's: {key, name, now}), talking (a boolean) }.
  function update({ place: where, time: when, events, talking: who } = {}) {
    if (where !== undefined) place = where && typeof where === "object" ? where.key : where;
    if (when !== undefined && when !== null) time = when;
    if (Array.isArray(events)) tournament = events.some((event) => event.key === "weekly-tournament" && event.now);
    if (who !== undefined) {
      talkingNow = who === true || typeof who === "string";
      talking = talkingNow ? (typeof who === "string" ? who : speakerName()) : null;
    }
    if (!ctx) return;
    applyAmbience();
    if (on) applyMusic();
    duck();
  }

  // While someone's being talked to, the music and ambience sit a little lower, so the words carry.
  function duck() {
    const now = ctx.currentTime;
    music.gain.setTargetAtTime(talkingNow ? 0.6 : 1, now, 0.3);
    ambience.gain.setTargetAtTime(talkingNow ? 0.5 : 1, now, 0.3);
  }

  document.addEventListener("world:town", (event) => update(event.detail || {}));

  // Start from the state the page was drawn with; world:town takes over from there.
  try {
    const initial = JSON.parse(document.getElementById("town-state").textContent);
    update({ place: initial.place && initial.place.key, time: initial.time, events: initial.events && initial.events.today });
  } catch { /* the first world:town will do */ }

  // ---- Listening ----

  document.addEventListener("click", (event) => {
    const el = event.target.closest?.("button, a");
    if (!el || !root.contains(el) || el.disabled || !ctx) return;
    playClick(clickKind(el));
  });

  for (const type of ["pointerdown", "keydown"]) {
    document.addEventListener(type, () => {
      if (on && !ctx) unlock();
    }, { capture: true });
  }

  document.addEventListener("visibilitychange", () => {
    if (!ctx) return;
    if (document.hidden) ctx.suspend();
    else if (on) ctx.resume();
  });

  for (const toggle of root.querySelectorAll("[data-sound-toggle]")) {
    toggle.addEventListener("click", () => setOn(!on));
  }
  for (const slider of root.querySelectorAll("[data-sound-volume]")) {
    slider.addEventListener("input", () => {
      volume = Number(slider.value);
      write(VOLUME_KEY, String(volume));
      paintControls();
      applyVolume();
    });
  }
  paintControls(); // a returning player's sound starts on their first touch (see pointerdown above)
})();
