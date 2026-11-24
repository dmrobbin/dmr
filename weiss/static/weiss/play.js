// Weiss Schwarz virtual tabletop. The server holds the game; this draws the board from the
// current player's seat (their side at the bottom, the opponent's mirrored at the top), sends
// moves, and polls for the opponent's moves. Players move their own cards by dragging them
// onto a zone, or by clicking a card or pile for a menu.
(() => {
  const root = document.getElementById("play");
  if (!root) return;
  const STATE_URL = root.dataset.stateUrl;
  const ACTION_URL = root.dataset.actionUrl;
  const CSRF = root.dataset.csrf;
  const POLL_MS = Number(root.dataset.pollMs) || 1500; // quicker against a CPU: polling is what moves it
  // How long a request may take before it's given up on (a poll moves a CPU, which can take a while).
  const POLL_TIMEOUT_MS = 15000;
  const ACTION_TIMEOUT_MS = 20000;
  const CONNECTION_ERROR = "Couldn't reach the server. Try again.";
  const DRAW_ERROR = "Something went wrong showing that. Checking the game again…";
  const SERVER_ERROR = "The server ran into a problem with this game. Still trying…";
  // A co-op partner watching this game (challenge_views.coop_spectate): the board from the player's seat, with only
  // what's public and their hand. Nothing is sent, and the cards and piles can only be looked at.
  const SPECTATING = "spectate" in root.dataset;

  const $ = (sel) => root.querySelector(sel);
  const boardEl = $("[data-board]");
  const previewEl = $("[data-preview]");
  const controlsEl = $("[data-controls]");
  const logEl = $("[data-log]");
  const menuEl = $("[data-menu]");
  const modalEl = $("[data-modal]");

  const LABELS = {
    deck: "Deck", hand: "Hand", clock: "Clock", level: "Level", stock: "Stock", waiting: "Waiting room",
    memory: "Memory", climax: "CX", resolution: "Resolution",
    C1: "Center left", C2: "Center middle", C3: "Center right", B1: "Back left", B2: "Back right",
  };
  const STAGE = ["C1", "C2", "C3", "B1", "B2"];
  // Each stage slot has a pile of markers under it, named "marker:<slot>" like the server does.
  for (const slot of STAGE) LABELS[`marker:${slot}`] = `Markers under ${LABELS[slot].toLowerCase()}`;
  const isMarkerPile = (zone) => zone.startsWith("marker:");
  const DAMAGE_RESOLVE_MS = 500; // how long a climax-cancelled damage stays on the board, with animations off
  const REFRESH_PAUSE_MS = 250; // how long an emptied deck shows before it's refreshed mid-damage
  const CLIMAX_SHOW_MS = 2000; // how long a climax played in the climax phase shows before the attack phase
  const CLIMAX_LEAD_MS = 380; // a played climax's build-up before it lands, without the music to time it (at most 900)
  const CLIMAX_HOLD_MS = 1250; // how long a played climax stays once it has landed, before it fades
  const CLIMAX_FADE_MS = 420;
  // A climax's colour, for its takeover and the turn it powers; any other is gold.
  const CLIMAX_COLORS = { red: "#ff4d5e", blue: "#4da3ff", yellow: "#ffd23f", green: "#46d07a", purple: "#b46bff" };
  const PHASE_PAUSE_MS = 900; // how long a phase that ended itself stays before the next begins
  const LEVEL_SHOW_MS = 2200; // how long a level up shows in the middle of the screen
  const PHASE_NAME_FX = ["fx-pop", "fx-flip", "fx-slide", "fx-glow"]; // a new phase's name comes in with one of these
  const RPS_SHOW_MS = 3000; // how long rock, paper, scissors' result shows before the mulligan
  const SHOW_FALLBACK_MS = 3000; // how much later than its owner the other player's page ends an ability's show
  const CLIMAX_EFFECTS = ["climax-zoom", "climax-spin", "climax-slide", "climax-flip", "climax-drop", "climax-blur"];
  const MOVE_TARGETS = ["hand", "C1", "C2", "C3", "B1", "B2", "climax", "clock", "level", "stock",
    "memory", "waiting", "resolution"];
  const PUBLIC_PILES = ["waiting", "memory", "level", "clock", "climax", "resolution"];
  const ENCORE_COST = 3; // stock, as on the server
  const LEVEL_UP_AT = 7; // clock cards that make a level, as on the server
  const CLOCK_DRAW = 2; // cards drawn after clocking a card from the hand, as on the server
  const PHASES = { mulligan: "Mulligan", stand: "Stand", draw: "Draw", clock: "Clock", main: "Main", climax: "CX", attack: "Attack", encore: "Encore", end: "End" };
  const PHASE_NAMES = Object.keys(PHASES);
  const ATTACK_STEPS = { declare: "Declare", trigger: "Trigger", counter: "Counter", damage: "Damage", battle: "Battle" };
  const OPPOSITE = { C1: "C3", C2: "C2", C3: "C1" }; // the opponent's slot facing each of our center slots
  // Neighbouring stage slots, each linked by a button on the first slot: [first, second, direction].
  // The back row sits under the gaps of the center row, so center-to-back links are diagonal.
  const SLOT_LINKS = [["C1", "C2", "h"], ["C2", "C3", "h"], ["B1", "B2", "h"],
    ["C1", "B1", "dr"], ["C2", "B1", "dl"], ["C2", "B2", "dr"], ["C3", "B2", "dl"]];
  // [both occupied (swap), first to second, second to first]
  const LINK_SYMBOLS = { h: ["⇄", "→", "←"], dr: ["⇅", "↘", "↖"], dl: ["⇅", "↙", "↗"] };
  // Entrances for the panel that takes over from the phase bar during the attack phase (and back).
  const PANEL_SWAPS = ["swap-slide", "swap-flip", "swap-zoom", "swap-skew"];
  // Playing a card from the hand into one of these pays its cost from the stock (as on the server).
  const PLAY_ZONES = ["C1", "C2", "C3", "B1", "B2", "climax", "resolution"];
  const COLORS = ["Yellow", "Green", "Red", "Blue", "Purple"];

  let version = "";
  let board = null;
  let avatars = {}; // {player name: picture}, for those who have one
  let cpuInfo = null; // the CPU in a game against one: its images and what it says
  let versus = null; // a game against a CPU: who's on each side (the names, decks and colours) and what's at stake
  let arcade = null; // where an arcade run has got to
  let world = null; // a town duel: where to go back to, and what it paid
  let prize = null; // an infinite challenge's prize for this win: what the Victory screen's slot machine lands on
  let duel = null; // a co-op challenge's vs. battle: the pair's rivalry, and the way to its curses
  let unlocked = null; // card sleeves this game unlocked for the player: [{name, css}], for the Victory or Defeat screen
  let sceneData = null; // a scene the run plays before the board goes on (weiss.scenes), until the server hears it's done
  let sceneViewer = ""; // the player's name, for {player} in a scene
  let sceneShown = null; // the key of the scene being played, so a poll doesn't start it again
  let intro = false; // the CPU's screen is up, and the match waits for it
  const cards = {}; // card pk -> details; entries are never replaced so image URLs stay stable
  let modal = null; // {title, owner: "me"|"opponent", zone} or {title, revealed: [...]}
  let error = "";
  let busy = false;
  let resolveTimer = null; // pending "resolve_damage" after a climax cancels our damage
  let refreshTimer = null; // pending "continue_damage" after a damage empties our deck
  let climaxShowEnds = 0; // when the climax takeover on screen is over (performance.now() time)
  const cuedClimaxes = {}; // per side, the climax count whose sound the takeover has played (playBoardSounds skips it)
  let gameOverHeldUntil = 0; // the game-over screen waits till then for the last damage to turn over (holdGameOver)
  const gameOverHeld = () => performance.now() < gameOverHeldUntil;
  let climaxTimer = null; // pending move to the attack phase after we play a climax
  let autoTimer = null; // pending move to the next phase after one ended itself (board.auto_next)
  let showTimer = null; // pending end of an ability being shown (board.ability_show)
  let comboTimer = null; // ...and of a CX combo's cut-in (board.combo_show)
  const COMBO_SHOW_MS = 1600; // the cut-in's time on screen: a second, then it fades (as cpu.WAITS has it)
  let rpsTimer = null; // pending end of rock, paper, scissors' result
  const mulliganPicks = new Set(); // hand cards picked to mulligan away
  const flashPicks = new Set(); // deck cards picked for a flash battle's level zone
  const discardPicks = new Set(); // hand cards picked for the end phase's discard
  let abilityPicks = []; // cards picked for an ability's prompt, in the order they were picked
  let placePick = { kind: null, uid: null, slot: null }; // the card and stage position picked to put it on, before confirming

  // Phones and tablets. Touch: there's no mouse to hover with, so a tap picks a card and its buttons go in a
  // tray along the bottom of the screen, and a long press (or the tray's View) shows it full screen.
  // Compact: the screen is too narrow for both sides of the table, so one side shows at a time.
  const touchQuery = window.matchMedia("(hover: none) and (pointer: coarse)");
  const compactQuery = window.matchMedia("(max-width: 48rem)");
  let touch = touchQuery.matches;
  let compact = compactQuery.matches;
  let boardView = "me"; // compact: the side of the table showing, "me" or "opponent"
  let oppSeen = ""; // compact: the opponent's side as last drawn, to tell when it changes out of sight...
  let oppMoved = false; // ...and whether it has since we last looked at it
  let selected = null; // touch: the uid of the card picked by a tap, its buttons in the tray
  let dragUid = null; // the card being dragged, so a redraw mid-drag keeps its drop hints

  function setModes() {
    touch = touchQuery.matches;
    compact = compactQuery.matches;
    root.classList.toggle("touch", touch);
    root.classList.toggle("compact", compact);
    const tools = root.querySelector("[data-tools]");
    if (tools) tools.open = !compact;
    if (!touch) selected = null;
    showLayout();
    if (board) render();
  }
  root.classList.toggle("touch", touch);
  root.classList.toggle("compact", compact);
  touchQuery.addEventListener("change", setModes);
  compactQuery.addEventListener("change", setModes);

  // Board view: "focus" (big stage, piles around it), "classic" (three even rows) or "wide" (the focused
  // board turned on its side: you on the left, your opponent on the right, your hand along the bottom).
  // Remembered per browser; storage can be unavailable (private windows), so it falls back to focus.
  const LAYOUT_KEY = "weiss-board-layout";
  const LAYOUTS = { focus: "Focused", classic: "Classic", wide: "Widescreen" };
  let layout = "focus";
  try {
    if (LAYOUTS[localStorage.getItem(LAYOUT_KEY)]) layout = localStorage.getItem(LAYOUT_KEY);
  } catch (e) { /* keep the default */ }

  function setLayout(next) {
    layout = next;
    try { localStorage.setItem(LAYOUT_KEY, next); } catch (e) { /* only this visit, then */ }
    showLayout();
    if (board) render();
  }

  // A compact screen has the focused board whichever is picked (its own layout is built on that one).
  function showLayout() {
    const shown = compact ? "focus" : layout;
    for (const name of Object.keys(LAYOUTS)) root.classList.toggle(`layout-${name}`, name === shown);
    // Widescreen is built from the focused mats (turned, not redrawn), so it carries their classes too.
    root.classList.toggle("layout-focus", shown === "focus" || shown === "wide");
  }
  setLayout(layout);

  // Animations ("Deck Out!", level ups, drawing) can be turned off; remembered per browser like
  // the layout. Off by default for people who've asked their system for reduced motion.
  const ANIMATIONS_KEY = "weiss-animations";
  let animations = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  try {
    const saved = localStorage.getItem(ANIMATIONS_KEY);
    if (saved) animations = saved === "on";
  } catch (e) { /* keep the default */ }

  function setAnimations(on) {
    animations = on;
    try { localStorage.setItem(ANIMATIONS_KEY, on ? "on" : "off"); } catch (e) { /* only this visit, then */ }
    if (board) {
      fx.setTableMood();
      renderControls();
    }
  }

  // --- Sound effects: recorded card sounds and a prompt blip (Kenney's CC0 casino and interface packs, in
  // static/weiss/sounds), with hits and chimes made in the browser (Web Audio) on top of them ----------
  // On or off and the volume are kept on the player's profile (profiles.sound_settings). The other
  // side's draws, damage and so on play the same sounds, quieter; prompts are only ever for us.
  // With music on (the default, remembered per browser like the animations) the battle music (score.js)
  // plays instead, and each of these moments is played into it as a cue rather than as a sound of its own.

  const SOUND_URL = root.dataset.soundUrl;
  const SOUND_BASE = root.dataset.soundBase || "";
  let soundOn = "soundOn" in root.dataset;
  let soundVolume = Number(root.dataset.soundVolume ?? 60); // 0 to 100
  // The music under the cues, 0 to 100 (60 is the default balance). Remembered per browser under a key the town shares
  // (world_audio.js); with nothing stored, the player's saved setting, then 60.
  const MUSIC_VOLUME_KEY = "weiss-music-volume";
  let musicVolume = Number(root.dataset.musicVolume ?? 60);
  try {
    const remembered = localStorage.getItem(MUSIC_VOLUME_KEY);
    if (remembered !== null && Number.isFinite(Number(remembered))) musicVolume = Number(remembered);
  } catch (e) { /* the saved setting, then */ }
  const OPPONENT_VOLUME = 0.55; // the other side's sounds, against ours
  const SOUND_BOOST = 2.2; // into the limiter, so sounds are loud without clipping
  const SOUND_STAGGER_MS = 140; // between sounds from the same board, e.g. clocking a card and then drawing
  const SOUND_SAVE_MS = 400; // the slider's last value is saved once it stops moving
  const takes = (prefix, n) => Array.from({ length: n }, (_, i) => `${prefix}-${i + 1}`);
  // Each recording's takes; one is picked at random each time, so repeats don't sound canned.
  const SAMPLE_FILES = {
    slide: takes("card-slide", 8), place: takes("card-place", 4), shove: takes("card-shove", 4),
    fan: takes("card-fan", 2), shuffle: ["card-shuffle"], chip: takes("chip-lay", 3), prompt: ["prompt"],
  };
  const samples = {}; // name -> [AudioBuffer, ...], filled in as they load
  let audio = null; // the AudioContext, made on the first click (browsers only start one after a click)
  let mix = null; // where every sound goes: a boost into a limiter
  let noiseBuffer = null;
  let soundSaveTimer = null;
  let musicSaveTimer = null;
  const MUSIC_KEY = "weiss-music";
  let musicOn = Boolean(window.WeissScore);
  try {
    const saved = localStorage.getItem(MUSIC_KEY);
    if (saved && window.WeissScore) musicOn = saved === "on";
  } catch (e) { /* keep the default */ }
  let score = null; // the battle music, made with the AudioContext

  // The song the town chose (world_audio.js, weiss-town-music). When one is chosen, the duel plays it through the
  // minigames' engine (minigames/audio.js) in place of the battle music. Nothing chosen: the battle music, as before.
  const TOWN_MUSIC_KEY = "weiss-town-music";
  // The songs the page offers, with the names the staff gave them (the music page's MusicTrack rows, without the deleted
  // ones: the duel page's song_tracks, rendered as json). The list below is only the fallback if that's missing.
  const FALLBACK_SONGS = [
    { key: "lofi", name: "Lo-fi" }, { key: "rock_1", name: "Rock 1" }, { key: "rock_2", name: "Rock 2" }, { key: "rock_3", name: "Rock 3" },
    { key: "rock_4", name: "Rock 4" }, { key: "hip_hop", name: "Hip hop" }, { key: "jazz", name: "Jazz" }, { key: "funk", name: "Funk" },
    { key: "synthwave", name: "Synthwave" }, { key: "emo", name: "Emo" }, { key: "metal", name: "Metal" }, { key: "cc0_1", name: "CC0 drums 1" },
    { key: "cc0_2", name: "CC0 drums 2" }, { key: "cc0_3", name: "CC0 drums 3" }, { key: "cc0_4", name: "CC0 jazz" }, { key: "cc0_5", name: "CC0 hip hop" },
    { key: "cc0_6", name: "CC0 funk" }, { key: "cc0_7", name: "CC0 emo" }, { key: "cc0_8", name: "CC0 metal" },
  ];
  const readSongTracks = () => {
    try {
      const el = document.getElementById("song-tracks");
      const list = el ? JSON.parse(el.textContent) : null;
      if (Array.isArray(list)) return list.filter((t) => t && typeof t.key === "string" && typeof t.name === "string");
    } catch (e) { /* the fallback below */ }
    return FALLBACK_SONGS;
  };
  const SONG_LIST = readSongTracks();
  const SONGS = SONG_LIST.map((t) => t.key);
  const chosenSong = () => {
    try {
      const saved = localStorage.getItem(TOWN_MUSIC_KEY);
      return SONGS.includes(saved) ? saved : null;
    } catch (e) { return null; }
  };
  let song = chosenSong();
  let songLoading = null;
  const SONG_NAMES = Object.fromEntries(SONG_LIST.map((t) => [t.key, t.name]));
  const songName = () => (song ? SONG_NAMES[song] || song : "Battle music");
  // The song follows the duel: its tier (0 to 6, from the payload's music_tier; it only builds) and its climax (climax_on).
  // A splash marks each activated ability (the payload's abilities going up) and each sound-effect cue.
  let songTier = 0;
  let songClimax = false;
  let songMatchPoint = false; // match point: the life-based effect (the payload's match_point)
  let abilityCount = null; // the payload's abilities; null until the first payload, which only sets the count
  // Calls the engine's method when it has it (the engine's duel methods are still being built).
  const songCall = (name, ...args) => {
    const fn = window.MinigameAudio && window.MinigameAudio[name];
    if (typeof fn === "function") fn.apply(window.MinigameAudio, args);
  };
  const PLAY_SCRIPT = document.currentScript ? document.currentScript.src : location.href;
  function loadSongEngine() {
    if (window.MinigameAudio) return Promise.resolve();
    if (!songLoading) {
      songLoading = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = new URL("minigames/audio.js", PLAY_SCRIPT).href;
        script.onload = resolve;
        script.onerror = reject;
        document.head.append(script);
      });
    }
    return songLoading;
  }
  // The battle music is what's playing (cues go into it); with a song chosen, the cues are the ordinary sounds.
  const battleMusic = () => musicOn && score && !song;

  function audioContext() {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return null;
    if (!audio) {
      audio = new Context();
      const limiter = audio.createDynamicsCompressor();
      limiter.threshold.value = -8;
      limiter.knee.value = 6;
      limiter.ratio.value = 12;
      limiter.attack.value = 0.002;
      limiter.release.value = 0.15;
      limiter.connect(audio.destination);
      mix = audio.createGain();
      mix.gain.value = SOUND_BOOST;
      mix.connect(limiter);
      noiseBuffer = audio.createBuffer(1, audio.sampleRate, audio.sampleRate);
      const data = noiseBuffer.getChannelData(0);
      for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
      loadSamples(audio);
      if (window.WeissScore) score = window.WeissScore.create(audio, limiter);
    }
    // A hidden page stays paused (see the visibilitychange listener), whatever wants to make a sound.
    if (audio.state === "suspended" && !document.hidden) audio.resume().catch(() => {});
    return audio;
  }

  // The music plays while sound and music are both on and the volume is up; it follows the board from the next bar.
  function syncMusic() {
    if (song) return syncSong();
    if (!score) return;
    score.setVolume(soundVolume / 100);
    score.setMusicLevel(musicVolume / 100);
    const wanted = soundOn && musicOn && soundVolume > 0;
    if (wanted && board) tellScore();
    if (wanted && !score.running) score.start();
    else if (!wanted && score.running) score.stop();
  }

  // The song's own loudness follows the music slider: 1 is the engine's level, so the default (60) is unchanged.
  // Guarded: until the engine has the setVolume call, the slider does nothing to a song.
  function setSongVolume() {
    if (window.MinigameAudio && window.MinigameAudio.setVolume) window.MinigameAudio.setVolume(musicVolume / 60);
  }

  // The chosen song: on while sound and music are on and the duel isn't over; off otherwise (and on leaving).
  function syncSong() {
    if (score && score.running) score.stop();
    const wanted = soundOn && musicOn && soundVolume > 0 && !(board && board.game_over);
    if (!wanted) {
      if (window.MinigameAudio) window.MinigameAudio.stop();
      return;
    }
    const playing = song;
    loadSongEngine().then(() => {
      // Still wanted, and still the same song? (The settings may have moved on while it loaded.)
      if (song !== playing || !soundOn || !musicOn || !soundVolume || (board && board.game_over)) return;
      window.MinigameAudio.setMuted(false);
      setSongVolume();
      // A song already playing crossfades to the new one; otherwise it starts. The tier and climax follow the duel.
      const current = window.MinigameAudio.status ? window.MinigameAudio.status().playing : null;
      if (current && current !== song) window.MinigameAudio.setSong(song);
      else window.MinigameAudio.start(song);
      songCall("setTier", songTier);
      songCall("setClimax", songClimax);
      songCall("setMatchPoint", songMatchPoint);
    }).catch(() => { /* the engine didn't load: the duel is quiet, as its cues still play */ });
  }

  // The song changed (the Song button here, or another tab's setting): read it again and play it, or the battle music.
  function songChanged() {
    const next = chosenSong();
    if (!next && song && window.MinigameAudio) window.MinigameAudio.stop();
    song = next;
    syncMusic();
  }
  // The Song dropdown: the battle music ("") or one of the songs. The choice is kept under the town's key, and the duel
  // re-reads it on the change event (songChanged), so the music switches as soon as it's picked.
  function chooseSong(next) {
    next = SONGS.includes(next) ? next : null;
    if (next === song) return;
    try {
      if (next) localStorage.setItem(TOWN_MUSIC_KEY, next);
      else localStorage.removeItem(TOWN_MUSIC_KEY);
    } catch (e) { /* only this visit, then */ }
    window.dispatchEvent(new Event("weiss:song-change"));
    sayStatus(`Song: ${songName()}`);
  }
  const songOptionsHtml = () => [`<option value="">Battle music</option>`,
    ...SONG_LIST.map((t) => `<option value="${esc(t.key)}">${esc(t.name)}</option>`)].join("");
  window.addEventListener("weiss:song-change", songChanged);
  window.addEventListener("storage", (event) => { if (event.key === TOWN_MUSIC_KEY) songChanged(); });
  // The music slider moved in another tab (the town's): take it here, as the slider does.
  window.addEventListener("storage", (event) => {
    if (event.key !== MUSIC_VOLUME_KEY || event.newValue === null || !Number.isFinite(Number(event.newValue))) return;
    musicVolume = Number(event.newValue);
    if (song) setSongVolume(); else syncMusic();
  });

  // The board, and whose theme it is, as the music follows them.
  function tellScore() {
    score.setTheme(musicTheme());
    score.setState(scoreState());
  }

  // A CPU opponent has its own theme (made from its name, so it's the same every time); a boss's, or an arcade
  // run's last fight, is its boss version. Anyone else gets the house theme.
  function musicTheme() {
    if (!cpuInfo) return null;
    const lastFight = Boolean(arcade && arcade.total && arcade.fight === arcade.total && !arcade.cleared);
    return { name: cpuInfo.name, boss: Boolean(arcade && arcade.boss) || lastFight };
  }

  // What the music follows (see score.js setState).
  function scoreState() {
    const sides = [board.me, board.opponent].filter(Boolean);
    const over = board.game_over;
    return {
      setup: Boolean(board.rps) || board.phase === "mulligan",
      level: Math.max(0, ...sides.map((side) => pileCount(side.zones.level))),
      clock: Math.max(0, ...sides.map((side) => pileCount(side.zones.clock))),
      turn: board.turn_number || 0,
      myTurn: Boolean(board.my_turn),
      attacking: board.phase === "attack",
      climax: sides.some((side) => pileCount(side.zones.climax) > 0),
      matchPoint: atBrink("me") || atBrink("opponent"),
      over: over && !gameOverHeld() ? (over.won ? "win" : "lose") : null,
    };
  }

  // Match point for a side: level 3 with 4 or more in its clock, a big attack from losing. Not a co-op boss with a
  // health bar, which doesn't lose at level 4. The music strips back for it and the table's edges pulse red.
  function atBrink(owner) {
    const side = board && board[owner];
    if (!side || (owner === "opponent" && arcade && arcade.boss && arcade.boss.max)) return false;
    return pileCount(side.zones.level) >= 3 && pileCount(side.zones.clock) >= 4;
  }

  function setMusic(on) {
    musicOn = on;
    try { localStorage.setItem(MUSIC_KEY, on ? "on" : "off"); } catch (e) { /* only this visit, then */ }
    if (on && soundOn) audioContext();
    syncMusic();
    if (board) renderControls();
  }

  // The M key: the music on or off from anywhere on the board, said for screen readers (it's heard anyway).
  function toggleMusicKey() {
    if (!window.WeissScore || !board) return;
    if (!soundOn) {
      sayStatus("Sound is off: turn it on to hear the music.");
      return;
    }
    setMusic(!musicOn);
    sayStatus(musicOn ? "Music on" : "Music off");
  }

  function sayStatus(text) {
    const el = controlsEl.querySelector("[data-sound-status]");
    if (el) el.textContent = text;
  }

  function setMusicVolume(volume, save) {
    musicVolume = volume;
    try { localStorage.setItem(MUSIC_VOLUME_KEY, String(volume)); } catch (e) { /* only this visit, then */ }
    // A song playing takes the slider as its volume only: syncMusic would restart it from the top.
    if (song) setSongVolume(); else syncMusic();
    clearTimeout(musicSaveTimer);
    if (save) musicSaveTimer = setTimeout(() => saveSound({ music: String(volume) }), SOUND_SAVE_MS);
  }

  // A browser that can't decode them (or a failed download) leaves a recording out; its sound falls back on Web Audio.
  function loadSamples(ctx) {
    for (const [name, files] of Object.entries(SAMPLE_FILES)) {
      samples[name] = [];
      for (const file of files) {
        fetch(`${SOUND_BASE}${file}.ogg`)
          .then((response) => (response.ok ? response.arrayBuffer() : Promise.reject(response.status)))
          .then((data) => ctx.decodeAudioData(data))
          .then((buffer) => samples[name].push(buffer))
          .catch(() => {});
      }
    }
  }

  // One of a recording's takes, a touch faster or slower each time. False if none has loaded.
  function sample(ctx, out, name, { at = 0, gain = 1, rate = 1 } = {}) {
    const loaded = samples[name] || [];
    if (!loaded.length) return false;
    const source = ctx.createBufferSource();
    const amp = ctx.createGain();
    source.buffer = loaded[Math.floor(Math.random() * loaded.length)];
    source.playbackRate.value = rate * (0.94 + Math.random() * 0.12);
    amp.gain.value = gain;
    source.connect(amp).connect(out);
    source.start(ctx.currentTime + at / 1000);
    return true;
  }

  // One note: a wave gliding from `from` to `to` Hz, quickly in and fading out over `ms`.
  function tone(ctx, out, { at = 0, ms, from, to = from, wave = "sine", gain = 1 }) {
    const start = ctx.currentTime + at / 1000;
    const end = start + ms / 1000;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = wave;
    osc.frequency.setValueAtTime(from, start);
    osc.frequency.exponentialRampToValueAtTime(to, end);
    amp.gain.setValueAtTime(0.0001, start);
    amp.gain.exponentialRampToValueAtTime(gain, start + 0.006);
    amp.gain.exponentialRampToValueAtTime(0.0001, end);
    osc.connect(amp).connect(out);
    osc.start(start);
    osc.stop(end + 0.02);
  }

  // A burst of noise through a filter sweeping from `from` to `to` Hz: swishes, cracks and rumbles.
  function noise(ctx, out, { at = 0, ms, from, to = from, type = "bandpass", q = 0.7, gain = 1 }) {
    const start = ctx.currentTime + at / 1000;
    const end = start + ms / 1000;
    const source = ctx.createBufferSource();
    const filter = ctx.createBiquadFilter();
    const amp = ctx.createGain();
    source.buffer = noiseBuffer;
    filter.type = type;
    filter.Q.value = q;
    filter.frequency.setValueAtTime(from, start);
    filter.frequency.exponentialRampToValueAtTime(to, end);
    amp.gain.setValueAtTime(0.0001, start);
    amp.gain.exponentialRampToValueAtTime(gain, start + 0.005);
    amp.gain.exponentialRampToValueAtTime(0.0001, end);
    source.connect(filter).connect(amp).connect(out);
    source.start(start, Math.random() * 0.5);
    source.stop(end + 0.02);
  }

  // A bell: a note with the inharmonic overtones that make it ring, decaying over `ms`.
  function bell(ctx, out, { at = 0, ms = 900, hz, gain = 0.5 }) {
    for (const [ratio, level] of [[1, 1], [2.76, 0.4], [5.4, 0.18]]) {
      tone(ctx, out, { at, ms: ms / Math.sqrt(ratio), from: hz * ratio, gain: gain * level });
    }
  }

  // A heavy hit, for damage: a falling boom under a crack.
  function impact(ctx, out, { at = 0, gain = 1 } = {}) {
    tone(ctx, out, { at, ms: 420, from: 150, to: 38, gain });
    noise(ctx, out, { at, ms: 260, from: 1200, to: 120, type: "lowpass", q: 1, gain: gain * 0.9 });
    noise(ctx, out, { at, ms: 70, from: 4000, to: 1500, q: 0.8, gain: gain * 0.6 });
  }

  const SOUNDS = {
    // The soft tick at the end of the results ceremony's coin count: a small, high blip.
    tick: (ctx, out) => tone(ctx, out, { ms: 90, from: 1400, to: 1400, wave: "sine", gain: 0.12 }),
    // The VS stinger, as the duel's versus intro hits (play_versus.js): a low hit under a rising whoosh and a bright chord.
    // It plays over the music, not as a music cue (see playSound), and its peak stays at or below the damage cue's.
    versus: (ctx, out) => {
      noise(ctx, out, { ms: 240, from: 300, to: 5000, q: 1, gain: 0.22 });
      tone(ctx, out, { ms: 320, from: 180, to: 60, gain: 0.35 });
      for (const hz of [392, 494, 587]) bell(ctx, out, { ms: 900, hz, gain: 0.12 });
    },
    // A climax played, without the music: a whoosh rising for CLIMAX_LEAD_MS, then it lands with a boom and a chord.
    climax: (ctx, out) => {
      noise(ctx, out, { ms: CLIMAX_LEAD_MS, from: 300, to: 6000, q: 1.2, gain: 0.5 });
      impact(ctx, out, { at: CLIMAX_LEAD_MS, gain: 1.1 });
      for (const hz of [392, 494, 587]) bell(ctx, out, { at: CLIMAX_LEAD_MS + 20, ms: 1100, hz, gain: 0.22 });
    },
    // A card slid off the deck into the hand.
    draw: (ctx, out) => sample(ctx, out, "slide", { gain: 1.2 })
      || noise(ctx, out, { ms: 160, from: 1500, to: 5000, gain: 0.9 }),
    // Any other card going anywhere: set down on the table.
    move: (ctx, out) => sample(ctx, out, "place")
      || noise(ctx, out, { ms: 90, from: 3000, to: 900, gain: 0.8 }),
    // A card going into the clock: set down hard, with a click like a counter ticking over.
    clock: (ctx, out) => {
      if (!sample(ctx, out, "place", { gain: 1.1, rate: 0.85 })) tone(ctx, out, { ms: 150, from: 520, to: 300, wave: "triangle", gain: 0.8 });
      if (!sample(ctx, out, "chip", { at: 35, gain: 0.9 })) noise(ctx, out, { at: 35, ms: 45, from: 3500, q: 2, gain: 0.6 });
    },
    // Damage landed: the card slammed into the clock with a hit.
    damage: (ctx, out) => {
      sample(ctx, out, "shove", { gain: 1.1, rate: 0.8 });
      impact(ctx, out);
    },
    // A climax cancelled the damage: the hit glances off with a falling shimmer.
    negated: (ctx, out) => {
      sample(ctx, out, "shove", { gain: 0.9 });
      tone(ctx, out, { ms: 380, from: 1600, to: 520, wave: "triangle", gain: 0.5 });
      noise(ctx, out, { ms: 380, from: 7000, to: 2500, q: 2, gain: 0.4 });
    },
    // A level up: cards fanned out under a rising arpeggio, ending on a ringing chord. Trimmed about 3 dB: it stood above the other effects.
    level: (ctx, out) => {
      sample(ctx, out, "fan", { gain: 0.8 });
      noise(ctx, out, { ms: 420, from: 600, to: 6000, gain: 0.35 });
      [523, 659, 784].forEach((hz, i) => tone(ctx, out, { at: i * 80, ms: 180, from: hz, wave: "triangle", gain: 0.4 }));
      for (const hz of [1047, 1319, 1568]) bell(ctx, out, { at: 240, ms: 1400, hz, gain: 0.22 });
    },
    // Something needs our answer: a low, rising game-menu blip. Level with damage (momentary max about -15.4 dB after the limiter): it plays on nearly every decision.
    prompt: (ctx, out) => {
      if (sample(ctx, out, "prompt", { gain: 0.37 })) return;
      [392, 523, 784].forEach((hz, i) => tone(ctx, out, { at: i * 75, ms: i === 2 ? 220 : 110, from: hz, wave: "square", gain: 0.084 }));
    },
    // A deck out: the waiting room shuffled into a new deck.
    shuffle: (ctx, out) => {
      if (sample(ctx, out, "shuffle", { gain: 1.2 })) return;
      for (const at of [0, 70, 140, 210, 280]) noise(ctx, out, { at, ms: 70, from: 2500, to: 4500, gain: 0.6 });
    },
  };

  // `count` (how many cards a damage turned over) and `icons` (a trigger check's) are for the music's cues.
  // Returns how many ms from now the music lands it, if the music plays it (null otherwise).
  function playSound(name, { quiet = false, at = 0, count = 1, icons = [] } = {}) {
    if (!soundOn || !soundVolume) return null;
    const ctx = audioContext();
    if (!ctx) return null;
    // A sound-effect cue splashes the chosen song too (the engine ignores it while the song isn't playing).
    if (song) songCall("splash");
    // The VS stinger has no music cue (score.js), so it plays over the music like the sounds with a song chosen.
    if (battleMusic() && !["versus", "tick"].includes(name)) {
      // Played in time with the music, so no stagger: several at once become a little figure (see score.js cue).
      syncMusic();
      const lands = score.cue(name, { opponent: quiet, count, icons });
      return typeof lands === "number" ? lands * 1000 : null;
    }
    if (!SOUNDS[name]) return null;
    const out = ctx.createGain();
    out.gain.value = (soundVolume / 100) * (quiet ? OPPONENT_VOLUME : 1);
    out.connect(mix);
    setTimeout(() => SOUNDS[name](ctx, out), at);
  }

  function saveSound(fields) {
    if (!SOUND_URL) return;
    fetch(SOUND_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": CSRF },
      body: new URLSearchParams(fields),
    }).catch(() => { /* only this visit, then */ });
  }

  function setSound(on) {
    soundOn = on;
    saveSound({ on: on ? "1" : "0" });
    if (on) playSound("prompt");
    syncMusic();
    if (board) renderControls();
  }

  function setSoundVolume(volume, save) {
    soundVolume = volume;
    syncMusic();
    clearTimeout(soundSaveTimer);
    if (save) soundSaveTimer = setTimeout(() => saveSound({ volume: String(volume) }), SOUND_SAVE_MS);
  }

  // What each side's sounds come from, at the last board we heard: the first board (and a new
  // game's) only sets this, so reopening the page doesn't replay anything.
  let heard = null;
  let heardPrompt = "";

  const pileCount = (zone) => (Array.isArray(zone) ? zone.length : (zone && zone.count) || 0);

  function soundSnapshot(side) {
    const counts = Object.entries(side.zones).map(([zone, cardsThere]) => `${zone}:${pileCount(cardsThere)}`);
    const stage = STAGE.map((slot) => `${(side.stage[slot] || {}).uid || ""}/${(side.markers[slot] || []).length}`);
    return {
      deck: pileCount(side.zones.deck), hand: pileCount(side.zones.hand), clock: pileCount(side.zones.clock),
      refreshes: side.refreshes || 0, level_ups: side.level_ups || 0, damage_taken: side.damage_taken || 0, negated: side.negated || 0,
      climaxes: side.climaxes || 0, layout: `${counts.join(",")}|${stage.join(",")}`,
      reversed: STAGE.filter((slot) => side.stage[slot] && side.stage[slot].pos === "reverse").length,
    };
  }

  // The prompt that's waiting on us, if any, as a key that changes when a new one comes up (as drawModal picks them).
  function promptKey() {
    if (SPECTATING || board.game_over) return "";
    const attack = board.attack;
    if (board.rps) return board.rps.mine || board.rps.won !== null ? "" : `rps:${JSON.stringify(board.rps.last)}`;
    if (board.flash && board.flash.deck) return "flash";
    if (board.mulligan && !board.mulligan.me) return "mulligan";
    if (board.discard && board.discard.mine) return `discard:${board.turn_number}`;
    if (board.level_up_pending) return `level:${board.me.level_ups || 0}`;
    if (board.ability && board.ability.mine && (!board.ability.resolving || (board.ability.prompt && board.ability.prompt.kind !== "manual"))) {
      return `ability:${JSON.stringify(board.ability.resolving ? board.ability.prompt : board.ability.queue || "queue")}`;
    }
    if (board.my_turn && attack && attack.step === "trigger" && attack.prompt && !board.ability_show) return `trigger:${attack.uid}:${attack.prompt.kind}`;
    if (!board.my_turn && attack && attack.step === "counter" && (attack.counters || []).length && !board.ability && !board.ability_show) {
      return `counter:${board.turn_number}:${board.attacks}`;
    }
    if (encoreDue()) return `encore:${board.turn_number}`;
    if (board.rules_request && !board.rules_request.mine) return "rules";
    return "";
  }

  function playBoardSounds() {
    // The music hears the board first, so a cue that reaches into the next bar (a level up's) finds it.
    if (score && score.running) tellScore();
    const now = { game: board.game_number, attacks: board.attacks || 0, turn: board.turn_number,
      ability: (board.ability_show || {}).id || "", combo: (board.combo_show || {}).id || "" };
    for (const owner of ["me", "opponent"]) {
      const side = board[owner];
      if (side) now[owner] = soundSnapshot(side);
    }
    const before = heard && heard.game === now.game ? heard : null;
    heard = now;
    const prompt = promptKey();
    if (!before) {
      heardPrompt = prompt;
      return;
    }
    let at = 0;
    // Only the music has these (the sound effects don't): an attack, an ability going off, a CPU's combo cutting in.
    if (now.attacks > before.attacks && now.turn === before.turn) playSound("attack", { quiet: !board.my_turn });
    if (now.ability && now.ability !== before.ability) {
      // A trigger check plays its icons (the attacker's, so on their side); any other ability, its run.
      const check = board.ability_show.check;
      if (check) {
        const icons = check.flatMap((pk) => ((cards[pk] || {}).trigger || "").toLowerCase().split(/\s+/).filter(Boolean));
        playSound("trigger", { quiet: !board.my_turn, icons });
      } else playSound("ability", { quiet: !board.ability_show.mine });
    }
    if (now.combo && now.combo !== before.combo) playSound("combo", { quiet: !board.combo_show.mine });
    for (const owner of ["me", "opponent"]) {
      const was = before[owner];
      const is = now[owner];
      if (!was || !is) continue;
      const sounds = [];
      // A climax's sound: the takeover plays it, timed with it (showClimax); here when there's been no takeover.
      if (is.climaxes > was.climaxes && cuedClimaxes[owner] !== is.climaxes) sounds.push("climax");
      // A damage's cards, which the music turns over one by one before the hit (or the cancel).
      const flipped = { damage: is.damage_taken - was.damage_taken, negated: Math.max(1, is.clock - was.clock) };
      if (is.refreshes > was.refreshes) sounds.push("shuffle");
      if (battleMusic() && is.reversed > was.reversed) sounds.push("reversed"); // only the music has this
      if (is.level_ups > was.level_ups) sounds.push("level");
      else if (is.damage_taken > was.damage_taken) sounds.push("damage");
      else if (is.negated > was.negated) sounds.push("negated");
      else {
        if (is.clock > was.clock) sounds.push("clock");
        if (is.hand > was.hand && is.deck < was.deck) sounds.push("draw");
        if (!sounds.length && is.layout !== was.layout) sounds.push("move");
      }
      for (const name of sounds) {
        playSound(name, { quiet: owner === "opponent", at, count: flipped[name] || 1 });
        at += SOUND_STAGGER_MS;
      }
    }
    reactions.consider(before, now);
    if (prompt && prompt !== heardPrompt) playSound("prompt", { at: at && at + SOUND_STAGGER_MS });
    heardPrompt = prompt;
  }

  // --- Talking to the server -------------------------------------------------------------------

  // --- The CPU's reactions: play_reactions.js (WeissReactions), made here, once what it reads is defined -----------------
  const reactions = window.WeissReactions.create({
    SPECTATING: () => SPECTATING, boardEl: () => boardEl, cpuInfo: () => cpuInfo, board: () => board,
    gameOverEl: () => gameOverEl, introEl: () => introEl, logEl: () => logEl, root: () => root, esc: (value) => esc(value),
    promptKey: () => promptKey(), atBrink: (owner) => atBrink(owner),
  });

  function receive(data) {
    if (data.status && data.status !== "playing") {
      window.location.reload(); // back to deck choice
      return;
    }
    const previous = version;
    version = String(data.version);
    for (const [pk, info] of Object.entries(data.cards || {})) {
      if (!cards[pk]) cards[pk] = info;
    }
    const before = movement.opponentSnapshot();
    const wasInPlay = board ? inPlay(board) : null;
    const wasMyTurn = board ? board.my_turn : null;
    const lastBoard = board;
    board = data.board;
    // The song's tier and climax come with the payload (music_tier, climax_on). A new activated ability (abilities going
    // up) splashes the song once; the first payload only sets the count.
    if (typeof data.music_tier === "number" && data.music_tier !== songTier) {
      songTier = data.music_tier;
      if (song) songCall("setTier", songTier); // safe before the song starts: the tier is kept for when it does
    }
    if (typeof data.climax_on === "boolean" && data.climax_on !== songClimax) {
      songClimax = data.climax_on;
      if (song) songCall("setClimax", songClimax);
    }
    if (typeof data.match_point === "boolean" && data.match_point !== songMatchPoint) {
      songMatchPoint = data.match_point;
      if (song) songCall("setMatchPoint", songMatchPoint);
    }
    if (typeof data.abilities === "number") {
      if (abilityCount !== null && data.abilities > abilityCount && song) songCall("splash");
      abilityCount = data.abilities;
    }
    // Compact: our turn starting brings our side back into view (it's where the hand is), and a change on the
    // opponent's side while it's out of sight puts a dot on the button that shows it.
    if (wasMyTurn === false && board.my_turn) boardView = "me";
    const opp = board.opponent;
    const oppNow = opp ? JSON.stringify([opp.stage, opp.markers, opp.zones.hand.count, opp.zones.clock.length, opp.zones.level.length,
      opp.zones.climax, opp.zones.waiting.length, opp.zones.stock.count]) : "";
    if (oppSeen && oppNow !== oppSeen && compact && boardView === "me") oppMoved = true;
    oppSeen = oppNow;
    avatars = data.avatars || {};
    cpuInfo = data.cpu || null;
    arcade = data.arcade || null;
    world = data.world || null;
    intro = Boolean(data.intro);
    sceneData = data.scene || null;
    prize = data.prize || null;
    duel = data.duel || null;
    unlocked = data.unlocked || null;
    // Each side's card sleeve (weiss.sleeves), a CSS background: site.css puts it on that side's face-down cards.
    for (const side of ["me", "opponent"]) {
      const sleeve = (data.sleeves || {})[side];
      if (sleeve) document.documentElement.style.setProperty(`--sleeve-${side}`, sleeve);
      else document.documentElement.style.removeProperty(`--sleeve-${side}`);
    }
    sceneViewer = data.player_name || sceneViewer;
    if (data.revealed) modal = { title: data.revealed.title, revealed: data.revealed.cards };
    // What this page owes the game (finishing a damage, moving a phase on...) is set going first: a
    // mistake in drawing must never leave the game waiting on us.
    armTimers();
    try {
      render();
      renderDefeated();
      renderBoss();
      renderDuel();
      renderAugments();
      prizeScreen.showScene();
    } catch (e) {
      version = previous === version ? "" : previous; // not drawn: the next poll fetches this board again
      throw e;
    }
    // The show around it (flights, bursts, announcements, sounds) is extra: if it goes wrong, the board stands.
    // The battle view reads the board before the table's show, which waits on it (the clock's cards turning over
    // until its souls land, the battle's loser until its clash).
    for (const extra of [() => movement.animateOpponent(before), () => wasInPlay && animations && celebrate(wasInPlay), () => battle.update(lastBoard),
      () => fx.tableFx(lastBoard), announce, playBoardSounds]) {
      try {
        extra();
      } catch (e) {
        console.error(e);
      }
    }
  }

  // What this page sends by itself after a moment: each waits for the board to say it's due, and is set
  // going again by any board that still says so (a poll that finds nothing new as well), so one that
  // didn't get through is sent again rather than leaving the game stuck.
  function armTimers() {
    if (!board) return;
    // A climax cancelled our damage: leave it on the board for a moment, then let the server clean up.
    if (board.damage_pending && !resolveTimer) {
      resolveTimer = setTimeout(() => {
        resolveTimer = null;
        movement.act({ type: "resolve_damage" });
      }, animations ? CLIMAX_SHOW_MS : DAMAGE_RESOLVE_MS); // long enough for "Damage Negated!" to be seen
    }
    // A phase of our turn ended itself: pause on it, then move on (the server drops this if the
    // turn has moved on some other way in the meantime). Abilities being resolved hold this up;
    // the board that arrives once they're done starts it again.
    if (board.auto_next && board.my_turn && !board.ability && !autoTimer) {
      const next = board.auto_next;
      autoTimer = setTimeout(() => {
        autoTimer = null;
        if (board.auto_next === next && board.my_turn && !board.ability) movement.act({ type: "phase", phase: next, auto: true });
      }, PHASE_PAUSE_MS);
    }
    // We played a climax in the climax phase: let it show, then move on to the attack phase
    // (once any abilities it triggered have been resolved).
    if (board.climax_pending && !board.ability && !climaxTimer) {
      // Not while the climax's takeover is still on screen (it starts after this, in announce): it waits that out.
      const moveOn = () => {
        const left = animations ? climaxShowEnds - performance.now() : 0;
        if (left > 0) {
          climaxTimer = setTimeout(moveOn, left);
          return;
        }
        climaxTimer = null;
        if (board.climax_pending && !board.ability) movement.act({ type: "phase", phase: "attack" });
      };
      climaxTimer = setTimeout(moveOn, CLIMAX_SHOW_MS);
    }
    // An ability is being shown: once it has been, play carries on. Its owner's page says so; the
    // other page does too a little later, in case the owner has gone away.
    if (board.ability_show && !showTimer) {
      const { id, mine } = board.ability_show;
      const delay = (animations ? CLIMAX_SHOW_MS : 0) + (mine ? 0 : SHOW_FALLBACK_MS);
      showTimer = setTimeout(() => {
        showTimer = null;
        if (board.ability_show && board.ability_show.id === id) movement.act({ type: "ability_show_done", id });
      }, delay);
    }
    // A CX combo's cut-in: the CPU moves on once it's been seen; this page does too, a little later, in case.
    if (board.combo_show && !comboTimer) {
      const { id } = board.combo_show;
      comboTimer = setTimeout(() => {
        comboTimer = null;
        if (board.combo_show && board.combo_show.id === id) movement.act({ type: "combo_show_done", id });
      }, COMBO_SHOW_MS + SHOW_FALLBACK_MS);
    }
    // Rock, paper, scissors has a winner: let both players see it, then on to the mulligan.
    if (board.rps && board.rps.won !== null && !rpsTimer) {
      rpsTimer = setTimeout(() => {
        rpsTimer = null;
        if (board.rps) movement.act({ type: "rps_done" });
      }, RPS_SHOW_MS);
    }
    // A damage emptied our deck: pause a moment, then the server refreshes it and deals the rest.
    if (board.refresh_pending && !refreshTimer) {
      refreshTimer = setTimeout(() => {
        refreshTimer = null;
        movement.act({ type: "continue_damage" });
      }, REFRESH_PAUSE_MS);
    }
  }

  // --- Announcements: "Deck Out!" and level ups, shown on the side they happened on -----------------

  // How many refreshes and level ups each side had at the last board we saw; the first board only
  // sets these, so reopening the page doesn't replay old ones.
  let seen = null;

  let shownAbility = null; // the id of the last ability shown
  let shownCombo = null; // ...and of the last CX combo cut-in

  // A CPU's CX combo: its picture and its line (its "CXCOMBO" text) cut in over the board, for a second, then fade.
  // Shown with animations off too, as it's what the CPU says; only the movement goes.
  function showCutIn() {
    if (!cpuInfo || !cpuInfo.combo) return;
    const picture = cpuInfo.picture;
    const face = picture
      ? `<span class="avatar combo-cutin-face" aria-hidden="true"><img src="${esc(picture.image)}" alt="" style="width:${picture.width}%;left:${picture.left}%;top:${picture.top}%"></span>`
      : cpuInfo.image ? `<img class="combo-cutin-face" src="${esc(cpuInfo.image)}" alt="">`
        : `<span class="avatar combo-cutin-face" aria-hidden="true"><span class="avatar-letter">${esc(cpuInfo.name.slice(0, 1).toUpperCase())}</span></span>`;
    const el = document.createElement("div");
    el.className = `combo-cutin${animations ? "" : " still"}`;
    el.setAttribute("role", "status");
    el.innerHTML = `${face}<div class="combo-cutin-words"><span class="combo-cutin-name">${esc(cpuInfo.name)} <b>CX COMBO</b></span>
      <p class="combo-cutin-line">${esc(cpuInfo.combo)}</p></div>`;
    root.appendChild(el);
    setTimeout(() => el.remove(), COMBO_SHOW_MS);
  }

  function announce() {
    const now = {};
    const show = animations && seen;
    const combo = board.combo_show;
    if (combo && combo.id !== shownCombo) {
      shownCombo = combo.id;
      if (seen) showCutIn();
    }
    const ability = board.ability_show;
    if (ability && ability.id !== shownAbility) {
      shownAbility = ability.id;
      if (show) prizeScreen.showAbility(ability);
    }
    for (const owner of ["me", "opponent"]) {
      const side = owner === "me" ? board.me : board.opponent;
      if (!side) continue;
      now[owner] = { refreshes: side.refreshes || 0, level_ups: side.level_ups || 0, climaxes: side.climaxes || 0, negated: side.negated || 0 };
      if (!show || !seen[owner]) continue;
      const mat = boardEl.querySelector(`.mat-${owner}`);
      if (now[owner].refreshes > seen[owner].refreshes) {
        prizeScreen.flash(prizeScreen.between(mat, '[data-pile="deck"]', '[data-slot="C3"]'), "Deck Out!", "flash-deck-out");
      }
      if (now[owner].climaxes > seen[owner].climaxes) prizeScreen.showClimax(side.zones.climax[side.zones.climax.length - 1], owner, now[owner].climaxes);
      if (now[owner].negated > seen[owner].negated && !battle.claimsNegated(owner, now[owner].negated)) { // the battle view's shield shows it
        const card = side.negated_card;
        setTimeout(() => prizeScreen.showNegated(card), fx.negatedWait(owner)); // once the damage's cards have turned over (tableFx)
      }
      if (now[owner].level_ups > seen[owner].level_ups) {
        prizeScreen.showLevelUp(owner === "me" && !SPECTATING ? "You" : side.name, side.zones.level.length);
      }
    }
    seen = now;
  }

  // --- Rarity: a card of R and up coming into play bursts, the rarer the grander ----------------------

  const RAINBOW = ["#ff6b8b", "#ffd36b", "#7dffb0", "#6bc6ff", "#c88bff"];
  const RARITY_COLORS = [[], ["#bcdcff"], ["#ffd36b", "#fff1c1"], ["#ffd36b", "#ffffff", "#fff1c1"], RAINBOW, [...RAINBOW, "#ffffff"]];
  const RARITY_SPARKS = [0, 0, 8, 14, 24, 40];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // {uid: card pk} for the cards in play: on the stage, in the climax area, and events being played.
  function inPlay(b) {
    const found = {};
    for (const side of [b.me, b.opponent]) {
      if (!side) continue;
      const cardsHere = [...STAGE.map((slot) => side.stage[slot]), ...(Array.isArray(side.zones.climax) ? side.zones.climax : []),
        ...(Array.isArray(side.zones.resolution) ? side.zones.resolution.filter((c) => c.card && (cards[c.card] || {}).type === "Event") : [])];
      for (const card of cardsHere) if (card && card.card && !card.face_down) found[card.uid] = card.card;
    }
    return found;
  }

  function celebrate(before) {
    for (const [uid, pk] of Object.entries(inPlay(board))) {
      const info = cards[pk];
      if (before[uid] || !info || !info.grade) continue;
      const el = boardEl.querySelector(`.pcard[data-uid="${CSS.escape(uid)}"]`);
      if (outOfSight(el)) continue;
      // The opponent's card flies in first (animateOpponent): burst once it lands.
      setTimeout(() => { if (el.isConnected) rarityBurst(el, info); }, el.style.visibility === "hidden" ? movement.FLIGHT_MS + 80 : 0);
    }
  }

  function rarityBurst(el, info) {
    const grade = Math.min(info.grade, RARITY_COLORS.length - 1);
    const palette = RARITY_COLORS[grade];
    const box = el.getBoundingClientRect();
    const burst = document.createElement("div");
    burst.className = "rarity-burst";
    burst.dataset.grade = grade;
    Object.assign(burst.style, { left: `${box.left + box.width / 2}px`, top: `${box.top + box.height / 2}px` });
    burst.style.setProperty("--size", `${Math.max(box.width, box.height)}px`);
    document.body.appendChild(burst);
    const add = (className) => burst.appendChild(Object.assign(document.createElement("span"), { className }));
    const ring = add("rb-ring");
    ring.style.borderColor = palette[0];
    ring.animate([{ transform: "scale(.6)", opacity: 0.9 }, { transform: `scale(${1.6 + grade * 0.35})`, opacity: 0 }], { duration: 650 + grade * 80, easing: "ease-out" });
    if (grade >= 2) el.animate([{ filter: "brightness(1)" }, { filter: "brightness(1.9)", offset: 0.25 }, { filter: "brightness(1)" }], { duration: 600 });
    if (grade >= 4) add("rb-rays");
    if (grade >= 4) {
      const label = add("rb-label");
      label.textContent = info.rarity;
    }
    if (!reducedMotion) {
      for (let n = 0; n < RARITY_SPARKS[grade]; n++) {
        const spark = add("rb-spark");
        spark.style.color = palette[n % palette.length];
        const angle = Math.random() * Math.PI * 2;
        const reach = box.height * (0.6 + Math.random() * (0.4 + grade * 0.15));
        spark.animate([{ transform: "translate(0, 0) scale(1.2)", opacity: 1 },
                       { transform: `translate(${Math.cos(angle) * reach}px, ${Math.sin(angle) * reach}px) scale(.3)`, opacity: 0 }],
                      { duration: 650 + Math.random() * 500, easing: "cubic-bezier(.1,.8,.3,1)", fill: "forwards" });
      }
    }
    setTimeout(() => burst.remove(), 1800);
  }

  // --- An infinite challenge's CPUs beaten so far: their pictures, top left, as on its page (defeated_tally.html) --

  let defeatedEl = null;
  let defeatedKey = "";
  function renderDefeated() {
    const beaten = arcade && arcade.defeated;
    const key = beaten ? JSON.stringify(beaten) : "";
    if (key === defeatedKey) return;
    defeatedKey = key;
    if (defeatedEl) defeatedEl.remove();
    defeatedEl = null;
    if (!beaten) return;
    const face = (cpu) => `<li><span class="avatar" role="img" aria-label="${esc(cpu.name)}" title="${esc(cpu.name)}">${cpu.picture
      ? `<img src="${esc(cpu.picture.image)}" alt="" draggable="false" style="width:${cpu.picture.width}%;left:${cpu.picture.left}%;top:${cpu.picture.top}%">`
      : `<span class="avatar-letter" aria-hidden="true">${esc(cpu.name.slice(0, 1).toUpperCase())}</span>`}</span></li>`;
    defeatedEl = document.createElement("div");
    defeatedEl.className = "defeated-tally play-defeated";
    defeatedEl.setAttribute("aria-label", `${beaten.length} CPU${beaten.length === 1 ? "" : "s"} defeated`);
    defeatedEl.innerHTML = `<span class="defeated-count" aria-hidden="true"><strong>${beaten.length}</strong> defeated</span>
      ${beaten.length ? `<ol class="defeated-faces">${beaten.map(face).join("")}</ol>` : ""}`;
    (root.querySelector(".play-chat-side") || root).prepend(defeatedEl);
  }

  // --- An infinite challenge's boss: what beating it brings, and in co-op its health, worn down by both players' games --

  let bossEl = null;
  let bossKey = "";
  function renderBoss() {
    const boss = arcade && arcade.boss;
    const key = boss ? JSON.stringify([boss, !!board.game_over]) : "";
    if (key === bossKey) return;
    bossKey = key;
    if (bossEl) bossEl.remove();
    bossEl = null;
    if (!boss) return;
    bossEl = document.createElement("div");
    bossEl.className = "play-boss";
    const health = boss.max ? `<div class="boss-health" role="meter" aria-label="Boss health" aria-valuemin="0" aria-valuemax="${boss.max}" aria-valuenow="${boss.health}">
        <span class="boss-health-fill" style="width: ${boss.percent}%"></span><span class="boss-health-text">${boss.health} / ${boss.max}</span></div>` : "";
    const note = boss.down ? `<p><strong>The boss is down!</strong> ${arcade.coop ? `You and ${esc(arcade.coop.partner)} beat it` : "Beaten"}.</p>`
      : boss.max ? `<p>It doesn't lose at level 4: every damage that lands on it, in your game or ${esc(arcade.coop ? arcade.coop.partner : "")}'s, comes off this bar. Beating it: ${esc(boss.reward)}.</p>`
      : `<p>It plays at its hardest. Beating it: ${esc(boss.reward)}.</p>`;
    bossEl.innerHTML = `<p class="play-boss-title">Boss</p>${health}${note}
      ${boss.down && !board.game_over ? `<button type="button" class="button-small" data-act='{"type":"challenge_leave"}'>Back to the path</button>` : ""}`;
    (root.querySelector(".play-chat-side") || root).prepend(bossEl);
  }

  // --- A co-op challenge's vs. battle: what's at stake, the rivalry so far, and a way to concede ----------------------

  let duelEl = null;
  let duelKey = "";
  function renderDuel() {
    const key = duel ? JSON.stringify([duel, !!board.game_over]) : "";
    if (key === duelKey) return;
    duelKey = key;
    if (duelEl) duelEl.remove();
    duelEl = null;
    if (!duel) return;
    duelEl = document.createElement("div");
    duelEl.className = "play-boss play-duel";
    duelEl.innerHTML = `<p class="play-boss-title">Vs. battle</p>
      <p>Neither loss counts against you. The winner picks their augment and curse first.</p>
      <p>Rivalry: you ${duel.mine} – ${duel.theirs} ${esc(duel.partner)}</p>
      ${board.game_over ? "" : `<button type="button" class="button-small secondary" data-act='{"type":"duel_concede"}'>Concede</button>`}`;
    (root.querySelector(".play-chat-side") || root).prepend(duelEl);
  }

  // --- The player's augments (weiss.augments) and curses (weiss.curses), named, with what each does on hover -------

  let augmentsEl = null;
  let augmentsKey = "";
  function renderAugments() {
    const picked = arcade && arcade.augments;
    const cursed = arcade && arcade.curses;
    const key = picked || cursed ? JSON.stringify([picked, cursed]) : "";
    if (key === augmentsKey) return;
    augmentsKey = key;
    if (augmentsEl) augmentsEl.remove();
    augmentsEl = null;
    if (!key) return;
    // Each one says what it does when hovered, or clicked or tapped (there's no hovering on a touch screen).
    const tags = (list) => list.map((a) => `<button type="button" class="deck-tag" title="${esc(a.text)}" data-augment="${esc(a.text)}" aria-expanded="false">${esc(a.name)}${a.count > 1 ? ` ×${a.count}` : ""}</button>`).join(" ");
    augmentsEl = document.createElement("div");
    augmentsEl.className = "play-augments small";
    augmentsEl.innerHTML = `<p>${[picked && `Augments: ${tags(picked)}`, cursed && `Curses: ${tags(cursed)}`].filter(Boolean).join("<br>")}</p>
      <p class="augment-text" aria-live="polite" hidden></p>`;
    (root.querySelector(".play-chat-side") || root).prepend(augmentsEl);
  }

  // An augment or curse's text under the list of them; clicking it again hides it.
  function showAugment(tag) {
    const text = augmentsEl && augmentsEl.querySelector(".augment-text");
    if (!text) return;
    const open = tag.getAttribute("aria-expanded") !== "true";
    augmentsEl.querySelectorAll("[data-augment]").forEach((t) => t.setAttribute("aria-expanded", "false"));
    tag.setAttribute("aria-expanded", String(open));
    text.textContent = open ? `${tag.textContent}: ${tag.dataset.augment}` : "";
    text.hidden = !open;
  }

  // --- An infinite challenge's prize: a slot machine: play_prize.js (WeissPrize), made here once what it reads is defined
  const prizeScreen = window.WeissPrize.create({
    CLIMAX_COLORS: () => CLIMAX_COLORS,
    CLIMAX_EFFECTS: () => CLIMAX_EFFECTS,
    CLIMAX_FADE_MS: () => CLIMAX_FADE_MS,
    CLIMAX_HOLD_MS: () => CLIMAX_HOLD_MS,
    CLIMAX_LEAD_MS: () => CLIMAX_LEAD_MS,
    CLIMAX_SHOW_MS: () => CLIMAX_SHOW_MS,
    CX_HTML: () => CX_HTML,
    LEVEL_SHOW_MS: () => LEVEL_SHOW_MS,
    PHASE_PAUSE_MS: () => PHASE_PAUSE_MS,
    SOUL_ICON: () => SOUL_ICON,
    SPECTATING: () => SPECTATING,
    animations: () => animations,
    battle: () => battle,
    board: () => board,
    boardEl: () => boardEl,
    cards: () => cards,
    climaxShowEnds: () => climaxShowEnds,
    cuedClimaxes: () => cuedClimaxes,
    esc: () => esc,
    fx: () => fx,
    gameOverHeld: () => gameOverHeld,
    gameOverHeldUntil: () => gameOverHeldUntil,
    heard: () => heard,
    playSound: (...args) => playSound(...args),
    reducedMotion: () => reducedMotion,
    sceneData: () => sceneData,
    sceneShown: () => sceneShown,
    sceneViewer: () => sceneViewer,
    version: () => version,
    who: (...args) => who(...args),
    setClimaxShowEnds: (value) => { climaxShowEnds = value; },
    setSceneShown: (value) => { sceneShown = value; },
  });

  // --- The table's show and mood: play_fx.js (WeissTableFx), made at the end once all it uses is defined -------

  let fx = null;

  // --- The recap of the opponent's turn: play_recap.js (WeissRecap), made at the end too --------------------------

  let recap = null;

  // --- The battle view, while an attack plays out: play_battle.js (WeissBattle), made at the end too ---------------

  let battle = { update() {}, damageLead: () => 0, battleClaim: () => null, claimsCheck: () => false, claimsNegated: () => false };

  // --- Card movement: our own moves: play_movement.js (WeissMovement), made here once what it reads is defined
  const movement = window.WeissMovement.create({
    ACTION_TIMEOUT_MS: () => ACTION_TIMEOUT_MS,
    ACTION_URL: () => ACTION_URL,
    CLOCK_DRAW: () => CLOCK_DRAW,
    CONNECTION_ERROR: () => CONNECTION_ERROR,
    CSRF: () => CSRF,
    DRAW_ERROR: () => DRAW_ERROR,
    ENCORE_COST: () => ENCORE_COST,
    PHASE_NAMES: () => PHASE_NAMES,
    PLAY_ZONES: () => PLAY_ZONES,
    POLL_MS: () => POLL_MS,
    POLL_TIMEOUT_MS: () => POLL_TIMEOUT_MS,
    SERVER_ERROR: () => SERVER_ERROR,
    SPECTATING: () => SPECTATING,
    STAGE: () => STAGE,
    STATE_URL: () => STATE_URL,
    animations: () => animations,
    armTimers: (...args) => armTimers(...args),
    board: () => board,
    boardEl: () => boardEl,
    busy: () => busy,
    cards: () => cards,
    duel: () => duel,
    error: () => error,
    esc: () => esc,
    fx: () => fx,
    hideMenu: (...args) => menus.hideMenu(...args),
    isMarkerPile: () => isMarkerPile,
    modal: () => modal,
    pileCards: (...args) => pileCards(...args),
    receive: (...args) => receive(...args),
    render: (...args) => render(...args),
    renderModal: (...args) => renderModal(...args),
    root: () => root,
    version: () => version,
    setBusy: (value) => { busy = value; },
    setError: (value) => { error = value; },
    setModal: (value) => { modal = value; },
  });

  // --- Drawing ---------------------------------------------------------------------------------

  const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  // A player, for writing into the page: their picture if they have one, otherwise their name.
  function who(name, extraClass = "") {
    const avatar = avatars[name];
    if (!avatar) return esc(name);
    return `<span class="avatar ${extraClass}" role="img" aria-label="${esc(name)}" title="${esc(name)}"><img src="${esc(avatar.image)}" alt="" draggable="false" style="width:${avatar.width}%;left:${avatar.left}%;top:${avatar.top}%"></span>`;
  }
  const whose = (name) => (avatars[name] ? who(name) : `${esc(name)}'s`);
  // A log line's text. Only lines the game writes about the players themselves are changed, so a card
  // sharing a player's name stays as it is: those with nobody as their subject, and who won.
  function logHtml(entry) {
    let html = cxHtml(entry.text);
    for (const name of Object.keys(avatars)) {
      const plain = esc(name);
      html = entry.who ? html.replace(`: ${plain} wins!`, () => `: ${who(name)} wins!`) : html.split(plain).join(who(name));
    }
    return html;
  }
  const handPortrait = (name) => (avatars[name] ? who(name, "hand-portrait") : "");
  const opponentWho = (otherwise = "your opponent") => (board.opponent ? who(board.opponent.name) : otherwise);
  // Text as HTML with the word "climax" (or the label "CX") drawn as the stylized CX mark.
  const CX_HTML = '<span class="cx" title="Climax">CX</span>';
  const cxHtml = (text) => esc(text).replace(/\b(climax|CX)\b/gi, CX_HTML);

  function cardHtml(card, owner, zone, extraClass = "") {
    if (!card) return "";
    const info = card.card ? cards[card.card] : null;
    const classes = ["pcard", `pos-${card.pos}`, extraClass];
    if (card.face_down) classes.push("face-down");
    // A climax is printed sideways: in the hand's upright frame its picture is turned to show all of it, and it
    // has no level, cost or power to show.
    const climax = Boolean(info) && !card.face_down && (info.type || "").toLowerCase() === "climax";
    if (climax && zone === "hand") classes.push("pcard-turned");
    const mine = owner === "me";
    const grade = info && !card.face_down ? info.grade || 0 : 0; // its rarity's glow and shine (site.css, "Rarity effects")
    const attrs = [
      `data-uid="${esc(card.uid)}"`, `data-owner="${owner}"`, `data-zone="${zone}"`,
      card.card ? `data-card="${card.card}"` : "",
      grade ? `data-grade="${grade}"` : "",
      mine && zone !== "deck" ? 'draggable="true"' : "",
    ].join(" ");
    const face = info
      ? `<img src="${esc(info.image)}" alt="${esc(info.name)}" loading="lazy" draggable="false">${grade >= 3 ? '<span class="rfx-sheen" aria-hidden="true"></span>' : ""}`
      : '<span class="pcard-back"></span>';
    const badge = card.pos === "reverse" ? '<span class="pcard-badge">REVERSE</span>'
      : card.face_down && info ? '<span class="pcard-badge">face down</span>' : "";
    const stats = info && !card.face_down && !climax
      ? statsHtml(info, { live: (board.stats || {})[card.uid], soul: STAGE.includes(zone) && zone.startsWith("C"), lowered: zone === "hand" ? handMod(card) : null })
      : "";
    const pinnacle = STAGE.includes(zone) && info && !card.face_down && !climax ? pinnacleHtml(card, info, owner) : "";
    if (pinnacle) classes.push("pinnacle");
    const aura = pinnacle ? ` data-aura="${pinnacleAura(info)}"` : "";
    return `<div class="${classes.join(" ")}" ${attrs}${aura} tabindex="0">${face}${pinnacle}${stats}${badge}</div>`;
  }

  // A character at 10,000 power or more has reached the pinnacle of strength: a ring of light runs round its edge,
  // its power is gilded, and the moment it gets there it flares once (on the board). Each redraw makes the card anew,
  // so the flare carries on from where it was (a negative delay) rather than starting over. Each colour has an aura
  // of its own (site.css, "The pinnacle of strength"), here and in the battle view; one of no colour we know is gold.
  const PINNACLE_POWER = 10000;
  const PINNACLE_AURAS = { yellow: "Radiant", red: "Blazing", blue: "Glacial", green: "Verdant", purple: "Arcane" };
  function pinnacleAura(info) {
    const color = String((info && info.color) || "").toLowerCase();
    return color in PINNACLE_AURAS ? color : "yellow";
  }
  // The aura's layers: its colour's motif (rays, embers, frost, ripples, a sigil), the ring and, as it gets there, the flare.
  const pinnacleLayers = (flare = "") =>
    `<span class="pinnacle-aura" aria-hidden="true"></span><span class="pinnacle-ring" aria-hidden="true"></span>${flare}`;
  const PINNACLE_FLARE_MS = 1300;
  const pinnacleSince = {}; // uid -> when it reached the pinnacle (performance.now()), for the board's cards
  function pinnacleHtml(card, info, owner) {
    const live = (board.stats || {})[card.uid];
    const power = live && live.power !== undefined ? live.power : Number(info.power) || 0;
    const onBoard = owner !== "view";
    if (power < PINNACLE_POWER) {
      if (onBoard) delete pinnacleSince[card.uid];
      return "";
    }
    let flare = "";
    if (onBoard) {
      // On the first board seen, a card already there doesn't flare: it was there before we looked.
      if (!(card.uid in pinnacleSince)) pinnacleSince[card.uid] = heard ? performance.now() : -Infinity;
      const age = performance.now() - pinnacleSince[card.uid];
      if (age < PINNACLE_FLARE_MS) flare = `<span class="pinnacle-flare" aria-hidden="true" style="animation-delay: ${-Math.round(age)}ms"></span>`;
    }
    return pinnacleLayers(flare);
  }

  // The soul icon: a flame-like wisp, close to the one printed on Weiss Schwarz cards.
  const SOUL_ICON = '<svg viewBox="0 0 16 22" aria-hidden="true"><path d="M8.6 0c.6 3.4 3.2 5 5 8.3 2.6 4.6.4 11.9-5.6 12.9C2.4 22-1.6 15.8 1.3 10.9c.9-1.6 2.4-2.6 2.9-4.6.9 1.9.6 3.6 2 4.4C5.5 7 9.4 4.4 8.6 0z"/></svg>';

  // Level and cost in the top-left corner and power in the bottom-left, where the printed card has
  // them, but large enough to read at board size. Left-side so they show on overlapped piles too.
  // Front-row characters also show their soul in the bottom-right. `live` is the character's power
  // and soul right now, worked out by the server from climaxes, abilities and effects on it: numbers
  // above the printed ones glow green, numbers below it glow red.
  function statsHtml(info, { live = null, soul = false, lowered = null } = {}) {
    const has = (value) => value !== null && value !== undefined && value !== "";
    // In the hand, an ability can lower what a card counts as: that shows, glowing, in place of what's printed.
    // On the stage, an effect can raise a character's level for a while: that shows, glowing, the same way.
    const corner = [["level", "Level"], ["cost", "Cost"]].map(([stat, label]) => {
      if (!has(info[stat])) return "";
      if (stat === "level" && live && has(live.level) && live.level !== info.level) {
        const glow = live.level > info.level ? " boosted" : " lowered";
        return `<span class="stat stat-level${glow}" title="Level ${live.level} (printed ${info.level})">${esc(live.level)}</span>`;
      }
      const now = lowered ? lowered[stat] : info[stat];
      const changed = now !== info[stat];
      return `<span class="stat stat-${stat}${changed ? " boosted" : ""}" title="${label}${changed ? ` ${now} while in your hand (printed ${info[stat]})` : ""}">${esc(now)}</span>`;
    }).join("");
    // A number's value right now, its glow, and its tooltip's note about the change from the card.
    const current = (printed, now) => {
      const value = now === undefined ? Number(printed) : now;
      const change = value - Number(printed);
      return { value, glow: change > 0 ? " boosted" : change < 0 ? " lowered" : "", note: change ? ` (${change > 0 ? "+" : ""}${change} from abilities)` : "" };
    };
    let power = "";
    if (has(info.power)) {
      const { value, glow, note } = current(info.power, live ? live.power : undefined);
      const peak = value >= PINNACLE_POWER ? ` — the pinnacle of strength (${PINNACLE_AURAS[pinnacleAura(info)]})` : "";
      power = `<span class="stat stat-power${glow}" title="Power${note}${peak}">${esc(value)}</span>`;
    }
    let souls = "";
    if (soul && has(info.soul)) {
      const { value, glow, note } = current(info.soul, live ? live.soul : undefined);
      const icons = value <= 3 ? SOUL_ICON.repeat(value) : `${SOUL_ICON}<b>×${value}</b>`;
      souls = `<span class="stat-soul${glow}" title="Soul ${value}${note}">${icons}</span>`;
    }
    if (!corner && !power && !souls) return "";
    return `<span class="pcard-stats">${corner ? `<span class="stat-corner">${corner}</span>` : ""}${power}${souls}</span>`;
  }

  function backHtml() {
    return '<div class="pcard"><span class="pcard-back"></span></div>';
  }

  // A magnifying glass shown while hovering a pile of more than one card that its viewer may look
  // through: the full list of a public pile, or a search of our own deck.
  function searchHtml(owner, zone, count) {
    if (count < 2 || zone === "stock" || (owner !== "me" && !PUBLIC_PILES.includes(zone))) return "";
    const title = `${owner === "me" ? "Your" : `${board.opponent.name}'s`} ${LABELS[zone].toLowerCase()}`;
    const what = zone === "deck" ? `data-act='{"type":"search"}'` : `data-search-view='${esc(JSON.stringify({ owner, zone, title }))}'`;
    return `<button type="button" class="zone-search" ${what} title="Search ${esc(title.toLowerCase())}" aria-label="Search">🔍</button>`;
  }

  // The resolution zone's top card can go to the hand (✋, bottom left) or the waiting room (🪦,
  // bottom right) in one click.
  function resolutionButtonsHtml(card) {
    return `<div class="slot-pos slot-pos-bottom">${iconButton({ type: "move", uid: card.uid, to: "hand" }, "✋", "To hand")}</div>
      <div class="slot-pos slot-pos-right slot-pos-bottom">${iconButton({ type: "move", uid: card.uid, to: "waiting" }, "🪦", "Waiting room")}</div>`;
  }

  function pileHtml(side, owner, zone) {
    const pile = side.zones[zone];
    const hidden = !Array.isArray(pile);
    const count = hidden ? pile.count : pile.length;
    const top = hidden ? (count ? backHtml() : "") : cardHtml(pile[pile.length - 1], owner, zone);
    return `<div class="zone pile zone-${zone}" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${cxHtml(LABELS[zone])} <b>${count}</b></span>
      ${searchHtml(owner, zone, count)}
      ${zone === "deck" && owner === "me" ? `<div class="slot-pos slot-pos-right">${zoneMenuButton("deck")}</div>` : ""}
      ${zone === "deck" && owner === "me" && count ? `<div class="slot-pos slot-pos-center">${
        iconButton({ type: "move_top", from: "deck", to: "hand" }, "✋", "Draw")}</div>` : ""}
      ${zone === "resolution" && owner === "me" && count ? resolutionButtonsHtml(pile[pile.length - 1]) : ""}
      <div class="pile-top">${top || '<span class="zone-empty"></span>'}</div>
      ${zone === "waiting" && !hidden && count ? waitingClimaxHtml(pile, owner) : ""}
    </div>`;
  }

  // Whether a card on the board is a face-up climax.
  const isClimaxCard = (card) => Boolean(card && card.card && !card.face_down && ((cards[card.card] || {}).type || "").toLowerCase() === "climax");

  // How many climaxes are in a waiting room: public, and the thing to know about it, as it tells how many are still
  // in the deck (to cancel damage) until the next refresh. A badge over the pile's top card.
  function waitingClimaxHtml(pile, owner) {
    const n = pile.filter(isClimaxCard).length;
    const whose = owner === "me" ? "your" : `${board.opponent.name}'s`;
    const label = `${n} climax${n === 1 ? "" : "es"} in ${whose} waiting room`;
    return `<span class="pile-cx${n ? "" : " none"}" title="${esc(label)}" aria-label="${esc(label)}">${CX_HTML}<b>${n}</b></span>`;
  }

  function pileCards(side, zone) {
    if (isMarkerPile(zone)) return (side.markers || {})[zone.slice("marker:".length)] || [];
    return side.zones[zone] || [];
  }

  // A character's markers: a small badge under it (top marker's picture, or a card back if it's
  // face down, plus the count). Click it like any pile; drop a card on it to add a marker.
  function markerHtml(side, owner, slot) {
    const markers = pileCards(side, `marker:${slot}`);
    if (!markers.length) return "";
    const top = markers[markers.length - 1];
    const info = top.card && !top.face_down ? cards[top.card] : null;
    const face = info ? `<img src="${esc(info.image)}" alt="" draggable="false">` : '<span class="pcard-back"></span>';
    return `<div class="marker-pile" data-pile="marker:${slot}" data-owner="${owner}" data-drop="${owner === "me" ? `marker:${slot}` : ""}"
        title="${markers.length} marker${markers.length === 1 ? "" : "s"} — click for options">
      <span class="marker-face">${face}</span><span>${markers.length} marker${markers.length === 1 ? "" : "s"}</span>
    </div>`;
  }

  // A small button showing just a symbol, with its name as the tooltip.
  function iconButton(action, symbol, label) {
    return `<button type="button" class="icon-button" title="${label}" aria-label="${label}"
      data-act='${esc(JSON.stringify(action))}'>${symbol}</button>`;
  }

  // Quick actions shown on one of our characters while hovering it: attack (⚔) for a standing
  // center-stage character on our turn, and, with turn rules off, the waiting room (🪦). With them on,
  // the encore step asks what happens to reversed characters (renderEncorePrompt); anything else is in
  // the full menu that opens beside the slot.
  // With turn rules on, a standing center character in our attack's declare step offers the
  // attacks the rules allow: front or side against the character facing it, direct if there's none.
  function slotActionsHtml(card, slot) {
    let quick = "";
    if (slot.startsWith("C") && card.pos === "stand") {
      if (!board.rules) {
        quick = iconButton({ type: "attack", uid: card.uid }, "⚔", "Attack");
      } else if (inPhase("attack") && board.attack && board.attack.step === "declare"
          && !(board.turn_number === 1 && board.attacks >= 1)) { // only one attack on turn 1
        const attack = (kind, label) => `<button type="button" class="attack-choice" data-act='${esc(JSON.stringify({ type: "attack", uid: card.uid, kind }))}'
          title="${esc(attackPreviewTitle(card.uid, kind))}">⚔ ${label}${attackPreviewHtml(card.uid, kind)}</button>`;
        const bans = (board.attack_bans || {})[card.uid] || [];
        const allowed = (kind, label) => (bans.includes("all") || bans.includes(kind) ? "" : attack(kind, label));
        quick = board.opponent && board.opponent.stage[OPPOSITE[slot]]
          ? allowed("front", "Front") + allowed("side", "Side") : allowed("direct", "Direct");
      }
    }
    const waiting = board.rules ? "" : iconButton({ type: "move", uid: card.uid, to: "waiting" }, "🪦", "Waiting room");
    return quick || waiting ? `<div class="slot-actions">${quick}${waiting}</div>` : "";
  }

  // What an attack would do, from the server's numbers (game.attack_previews): the battle's outcome for a front
  // attack, and the damage. Triggers, counters and abilities can still change it.
  const BATTLE_OUTCOMES = { win: "Wins", tie: "Both reversed", lose: "Loses" };
  function attackPreview(uid, kind) {
    const preview = ((board.attack_previews || {})[uid] || {})[kind];
    if (!preview) return null;
    const [mine, theirs] = preview.power || [];
    const outcome = preview.power ? (mine > theirs ? "win" : mine === theirs ? "tie" : "lose") : null;
    return { ...preview, outcome };
  }

  function attackPreviewHtml(uid, kind) {
    const p = attackPreview(uid, kind);
    if (!p) return "";
    const battle = p.outcome ? `<span class="attack-outcome ${p.outcome}">${p.power[0]} vs ${p.power[1]} · ${BATTLE_OUTCOMES[p.outcome]}</span>` : "";
    return `<span class="attack-preview">${battle}<span class="attack-damage">${p.damage} damage</span></span>`;
  }

  function attackPreviewTitle(uid, kind) {
    const p = attackPreview(uid, kind);
    if (!p) return "";
    const battle = p.outcome ? `${p.power[0]} power against ${p.power[1]}: ${BATTLE_OUTCOMES[p.outcome].toLowerCase()} the battle. ` : "";
    return `${battle}${p.damage} damage. Before trigger checks, counters and abilities.`;
  }

  // Quick moves shown on a hand card while hovering it: where characters and climaxes usually go
  // (events go to the resolution zone to be played), then "More" for the full menu. A character's
  // stage slots are rows of boxes: L / M / R for the center stage, L / R under it for the back stage.
  // The clock (🕒) and waiting room (🪦) are symbol buttons side by side.
  // Where a hand card can be played right now, and if it's the kind of card this phase plays but something is
  // stopping it, what (the first thing to fix): {to: [zones], blocked: text or null, kind}.
  function handPlays(card) {
    const info = card.card ? cards[card.card] : null;
    const type = info && info.type ? info.type.toLowerCase() : "";
    const phase = type === "character" ? inPhase("main") : type === "climax" ? inPhase("main", "climax") : inPhase("main");
    if (!phase) return { to: [], blocked: null, type };
    const cost = info ? Number(handStat(card, info, "cost")) || 0 : 0;
    const short = canPay(card, info) ? 0 : cost - board.me.zones.stock.count;
    const blocked = levelMissing(card, info) ? `Needs level ${handStat(card, info, "level")}`
      : colorMissing(card) ? `Needs ${colorMissing(card)}`
      : (board.play_banned || []).includes(card.uid) ? "Can't be played yet" // its own text says so
      : short > 0 ? `${short} more stock` : null;
    if (blocked) return { to: [], blocked, type, short };
    const to = type === "character" ? STAGE : type === "climax" ? ["climax"] : ["resolution"];
    return { to, blocked: null, type, short: 0 };
  }

  function handActionsHtml(card) {
    const move = (to, symbol) => iconButton({ type: "move", uid: card.uid, to }, symbol, LABELS[to]);
    const moveText = (to) => `<button type="button" data-act='${esc(JSON.stringify({ type: "move", uid: card.uid, to }))}'>→ ${cxHtml(LABELS[to])}</button>`;
    const info = card.card ? cards[card.card] : null;
    const clockDraw = inPhase("clock") ? iconButton({ type: "clock_draw", uid: card.uid }, "🕒+2", "Clock and draw 2") : "";
    const clock = inPhase("clock") ? move("clock", "🕒") : "";
    const reveal = board.reveal ? "" : iconButton({ type: "reveal", uid: card.uid }, "👁", "Reveal to your opponent");
    const piles = `<div class="hand-center">${clock}${move("waiting", "🪦")}${clockDraw}${reveal}</div>`;
    const held = (board.play_banned || []).includes(card.uid); // its own text says it can't be played yet
    const plays = handPlays(card);
    let rows = "";
    if (plays.type === "character" && plays.to.length) {
      rows = `<div class="hand-center">${move("C1", "L")}${move("C2", "M")}${move("C3", "R")}</div>
        <div class="hand-center hand-back">${move("B1", "L")}${move("B2", "R")}</div>`;
    } else if (plays.type === "climax" && plays.to.length && inPhase("climax")) {
      rows = moveText("climax");
    } else if (plays.type === "climax" && plays.to.length && board.rules) {
      // Playing a climax from the main phase ends it: asks first (see renderClimaxConfirm).
      rows = `<button type="button" data-confirm-climax="${esc(card.uid)}">→ ${CX_HTML}</button>`;
    } else if (plays.to.length) {
      rows = moveText("resolution"); // events in our main phase
    }
    // Our counter step (the opponent is attacking): the counters we can play right now.
    const attack = board.attack;
    if (attack && attack.step === "counter" && (attack.counters || []).includes(card.uid)) {
      rows = `<button type="button" class="counter-button" data-act='${esc(JSON.stringify({ type: "counter", uid: card.uid }))}'>Counter</button>` + rows;
    }
    const needs = inPhase("main", "climax") ? colorMissing(card) : null;
    if (needs) rows = `<span class="hand-needs">Needs ${esc(needs)}</span>` + rows;
    if (inPhase("main", "climax") && held) rows = `<span class="hand-needs">Can't be played yet</span>` + rows;
    if (inPhase("main", "climax") && levelMissing(card, info)) rows = `<span class="hand-needs">Needs level ${esc(handStat(card, info, "level"))}</span>` + rows;
    if (plays.short > 0) rows = `<span class="hand-needs">Costs ${esc(handStat(card, info, "cost"))}: ${plays.short} more stock needed</span>` + rows;
    rows += piles;
    return `<div class="hand-actions">
      ${rows}
      <button type="button" data-more>More…</button>
    </div>`;
  }

  // A card in our hand, marked for what it can do now: a glow if it can be played (or played as a counter), a chip
  // on it saying what's stopping it if it's this phase's kind of card, and a combo chip on a climax that would start one.
  function handCardHtml(card) {
    const plays = handPlays(card);
    const attack = board.attack;
    const counter = Boolean(attack && attack.step === "counter" && !board.my_turn && (attack.counters || []).includes(card.uid));
    const combos = (board.hand_combos || {})[card.uid] || [];
    const classes = ["hand-card"];
    if (board.rules && !SPECTATING && (plays.to.length || counter)) classes.push("playable"); // with the rules off everything is
    if (plays.short > 0) classes.push("cost-short");
    let chip = "";
    if (SPECTATING) chip = "";
    else if (plays.blocked) chip = `<span class="hand-chip blocked">${esc(plays.blocked)}</span>`;
    else if (counter) chip = '<span class="hand-chip ready">Counter</span>';
    else if (combos.length && plays.to.length) {
      const names = combos.map((uid) => { const c = Object.values(board.me.stage).find((s) => s && s.uid === uid); return c ? stageNameOf(c) : ""; }).filter(Boolean);
      chip = `<span class="hand-chip combo" title="${esc(`Climax combo with ${names.join(", ")}`)}">${CX_HTML} Combo</span>`;
    }
    return `<div class="${classes.join(" ")}">${cardHtml(card, "me", "hand")}${chip}${handActionsHtml(card)}</div>`;
  }

  const canEncore = () => board.me.zones.stock.count >= ENCORE_COST;
  // Our turn, in one of these phases.
  // With turn rules off every shortcut is offered, in any phase.
  const inPhase = (...phases) => !board.rules || (board.my_turn && phases.includes(board.phase));
  // Whether our stock covers a card's cost (cards with no cost are free; so is everything with the rules off).
  const canPay = (card, info) => (board.free_plays || {})[card.uid] || !board.rules || !info || !handStat(card, info, "cost") || board.me.zones.stock.count >= handStat(card, info, "cost");
  // What the server says a hand card counts as, if an ability has lowered it; or what's printed.
  const handMod = (card) => (board.hand_mods || {})[card.uid] || null;
  const handStat = (card, info, stat) => (handMod(card) ? handMod(card)[stat] : info[stat]);
  const levelMissing = (card, info) => Boolean(board.rules && info && handStat(card, info, "level") > board.me.zones.level.length);

  // The color the server says the color rule is holding this hand card back for, or null.
  const colorMissing = (card) => (board.needs_color || {})[card.uid] || null;

  // The colors in a side's clock and level zones (how many cards doesn't matter). The side's outline glows
  // with them (site.css, .table-side .mat::after), so the style is a list of colors set on the side.
  const GLOW_COLORS = { yellow: "#e3c33b", green: "#4fae5b", red: "#d9534f", blue: "#4a8fd9", purple: "#9b6cd1" };
  function glowStyle(side) {
    const present = new Set([...side.zones.clock, ...side.zones.level]
      .map((c) => (c.card && cards[c.card] ? cards[c.card].color : "")).filter(Boolean));
    const colors = COLORS.filter((c) => present.has(c)).map((c) => GLOW_COLORS[c.toLowerCase()]).filter(Boolean);
    return colors.length ? ` style="--glow-colors: ${colors.join(", ")}"` : "";
  }

  // Any reversed character on either side (the encore step waits for them).
  const reversedLeft = () => [board.me, board.opponent].some((side) => side && Object.values(side.stage).some((c) => c && c.pos === "reverse"));

  const zoneMenuButton = (zone) => `<button type="button" class="zone-menu" title="More actions" aria-label="More actions" data-zone-menu="${zone}">[…]</button>`;

  // Small always-visible buttons in the corners of our occupied slots: stand (|) and rest (—) top
  // left and reverse (↷, center stage only) top right, with turn rules off (with them on, the game
  // turns cards itself; the […] menu still can); the menu top right, and back to hand (✋) bottom left.
  function slotPosHtml(card, slot) {
    const button = (action, symbol, label, pressed = false) => `<button type="button" title="${label}" aria-label="${label}"
      aria-pressed="${pressed}" data-act='${esc(JSON.stringify(action))}'>${symbol}</button>`;
    const pos = (p, symbol, label) => (board.rules ? "" : button({ type: "position", uid: card.uid, pos: p }, symbol, label, card.pos === p));
    return `${board.rules ? "" : `<div class="slot-pos">${pos("stand", "|", "Stand")}${pos("rest", "—", "Rest")}</div>`}
      <div class="slot-pos slot-pos-right">${slot.startsWith("C") ? pos("reverse", "↷", "Reverse") : ""}${zoneMenuButton(slot)}</div>
      <div class="slot-pos slot-pos-bottom">${button({ type: "move", uid: card.uid, to: "hand" }, "✋", "To hand")}</div>`;
  }

  // The ! button, on any card of ours with an ability that can be activated. It opens the list of
  // those abilities (see renderAbilityList); it's dimmed when none of them can be used right now.
  function activateButtonHtml(card) {
    const rows = (board.acts || {})[card.uid];
    if (!rows) return "";
    const ready = rows.some((row) => !row.why);
    const label = ready ? "Activate an ability" : `Ability: ${rows[0].why}`;
    return `<button type="button" class="ability-button${ready ? " ready" : ""}" title="${esc(label)}" aria-label="${esc(label)}" data-abilities="${esc(card.uid)}">!</button>`;
  }

  // Buttons between neighbouring slots of ours (in the main phase, with turn rules on): swap the two
  // characters, or an arrow moving one into the empty slot beside it.
  function slotLinksHtml(side, slot) {
    if (!inPhase("main")) return "";
    return SLOT_LINKS.filter(([first]) => first === slot).map(([first, second, direction]) => {
      const a = side.stage[first];
      const b = side.stage[second];
      if (!a && !b) return "";
      const [swap, forward, back] = LINK_SYMBOLS[direction];
      const [symbol, uid, to, label] = a && b ? [swap, a.uid, second, `Swap with ${LABELS[second].toLowerCase()}`]
        : a ? [forward, a.uid, second, `Move to ${LABELS[second].toLowerCase()}`]
        : [back, b.uid, first, `Move to ${LABELS[first].toLowerCase()}`];
      return `<button type="button" class="slot-link link-${direction}" title="${label}" aria-label="${label}"
        data-act='${esc(JSON.stringify({ type: "move", uid, to }))}'>${symbol}</button>`;
    }).join("");
  }

  // A stage slot's name sits outside it: above the center row, below the back row.
  function slotHtml(side, owner, slot) {
    const card = side.stage[slot];
    const center = slot.startsWith("C");
    const label = `<span class="zone-label slot-label">${LABELS[slot]}</span>`;
    // Glows: an ability of ours that can be activated now, and a climax combo that's live (either side's).
    const ready = card && owner === "me" && !SPECTATING && ((board.acts || {})[card.uid] || []).some((row) => !row.why);
    const combo = card && (board.combos || {})[card.uid];
    const comboInfo = combo ? cards[combo] : null;
    const glow = `${ready ? " can-act" : ""}${combo ? " combo-live" : ""}`;
    const comboTag = combo ? `<span class="combo-tag" title="${esc(`Climax combo live with ${comboInfo ? comboInfo.name : "the climax"}`)}">${CX_HTML} Combo</span>` : "";
    return `<div class="slot-wrap ${center ? "slot-wrap-center" : "slot-wrap-back"}">
      ${center ? label : ""}
      <div class="zone slot${glow}" data-slot="${slot}" data-drop="${owner === "me" ? slot : ""}" data-owner="${owner}">${comboTag}
        ${cardHtml(card, owner, slot) || '<span class="zone-empty"></span>'}
        ${card && owner === "me" ? slotPosHtml(card, slot) + slotActionsHtml(card, slot) : ""}
        ${card && owner === "me" && board.acts && board.acts[card.uid] ? `<div class="slot-pos slot-pos-right slot-pos-bottom">${activateButtonHtml(card)}</div>` : ""}
        ${markerHtml(side, owner, slot)}
        ${owner === "me" ? slotLinksHtml(side, slot) : ""}
      </div>
      ${center ? "" : label}
    </div>`;
  }

  // The level zone: a narrow column, its (at most 4) cards stacked closely top to bottom so each
  // one's level and cost corner still shows.
  function levelHtml(side, owner) {
    const pile = side.zones.level;
    return `<div class="zone spread zone-level" data-pile="level" data-owner="${owner}" data-drop="${owner === "me" ? "level" : ""}">
      <span class="zone-label">${LABELS.level} <b>${pile.length}</b></span>
      ${searchHtml(owner, "level", pile.length)}
      <div class="level-stack">${pile.map((c) => cardHtml(c, owner, "level")).join("") || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  function spreadHtml(side, owner, zone) {
    const pile = side.zones[zone];
    return `<div class="zone spread zone-${zone}" data-pile="${zone}" data-owner="${owner}" data-drop="${owner === "me" ? zone : ""}">
      <span class="zone-label">${LABELS[zone]} <b>${pile.length}</b>${zone === "clock" && !board.game_over && atBrink(owner) ? ' <span class="match-point-tag" title="Level 3 with 4 or more in the clock: one big attack from losing">Match point</span>' : ""}</span>
      ${searchHtml(owner, zone, pile.length)}
      <div class="spread-cards">${pile.map((c) => cardHtml(c, owner, zone)).join("") || '<span class="zone-empty"></span>'}</div>
    </div>`;
  }

  // A compact screen always has the focused board: site.css lays it out for a phone.
  function matHtml(side, owner) {
    return layout === "classic" && !compact ? classicMatHtml(side, owner) : focusMatHtml(side, owner);
  }

  // Compact: the buttons that switch between our side of the table and the opponent's, each with what
  // matters most on it. A dot shows the opponent's side has changed since we last looked.
  function boardSwitchHtml(me, opp) {
    const summary = (side, hand) => `✋ ${hand} · Lv ${side.zones.level.length} · Clock ${side.zones.clock.length}`;
    const button = (view, label, sub, dot = false) => `<button type="button" data-board-view="${view}" aria-pressed="${boardView === view}">
      <span>${label}${dot ? '<span class="board-switch-dot" aria-hidden="true"></span><span class="sr-only"> (changed)</span>' : ""}</span>
      <span class="board-switch-sub">${sub}</span></button>`;
    return `<div class="board-switch" role="group" aria-label="Side of the table to show">
      ${button("me", SPECTATING ? `${esc(me.name)}'s board` : "Your board", summary(me, me.zones.hand.length))}
      ${button("opponent", `${esc(opp.name)}'s board`, summary(opp, opp.zones.hand.count), oppMoved)}</div>`;
  }

  function classicMatHtml(side, owner) {
    // Rows from the middle of the table outwards; the opponent's side is mirrored by CSS.
    return `<div class="mat mat-${owner}">
      <div class="mat-row">${pileHtml(side, owner, "climax")}
        <div class="stage">${["C1", "C2", "C3"].map((s) => slotHtml(side, owner, s)).join("")}</div>
        ${pileHtml(side, owner, "resolution")}</div>
      <div class="mat-row">${pileHtml(side, owner, "stock")}
        <div class="stage">${["B1", "B2"].map((s) => slotHtml(side, owner, s)).join("")}</div>
        ${pileHtml(side, owner, "deck")}</div>
      <div class="mat-row">${levelHtml(side, owner)}${spreadHtml(side, owner, "clock")}
        ${pileHtml(side, owner, "memory")}${pileHtml(side, owner, "waiting")}</div>
    </div>`;
  }

  function focusMatHtml(side, owner) {
    // From the middle of the table outwards: the stage (center row, then back row) with stock and
    // memory above the climax zone on the left (the climax level with the middle of the stage),
    // level beneath that, and the clock under the stage (centered on the board). Resolution, deck
    // and waiting room run down the right edge.
    // The opponent's side is the same turned around by CSS.
    return `<div class="mat mat-${owner}">
      <div class="mat-left">
        <div class="mat-left-piles">${pileHtml(side, owner, "stock")}${pileHtml(side, owner, "memory")}</div>
        ${pileHtml(side, owner, "climax")}
      </div>
      <div class="mat-stage">
        <div class="stage">${["C1", "C2", "C3"].map((s) => slotHtml(side, owner, s)).join("")}</div>
        <div class="stage">${["B1", "B2"].map((s) => slotHtml(side, owner, s)).join("")}</div>
      </div>
      <div class="mat-right">${pileHtml(side, owner, "resolution")}${pileHtml(side, owner, "deck")}${pileHtml(side, owner, "waiting")}</div>
      ${levelHtml(side, owner)}${spreadHtml(side, owner, "clock")}
    </div>`;
  }

  // A climax in play fills its side's background: its picture, faint, washed in its colour and slowly glowing. It
  // sits under the table's mood (the warmth as levels climb, match point's red), which shows over it. Each redraw
  // makes it anew, so its fade-in carries on from where it was (a negative delay) rather than starting again.
  const CX_BACKDROP_FADE_MS = 1400;
  const backdropSeen = {}; // per side: {uid, at} of the climax whose backdrop is showing
  function climaxBackdropHtml(side, owner) {
    const zone = side.zones.climax;
    const top = !board.game_over && Array.isArray(zone) && zone.length ? zone[zone.length - 1] : null;
    const info = top && top.card ? cards[top.card] : null;
    if (!info) {
      delete backdropSeen[owner];
      return "";
    }
    const now = performance.now();
    if (!backdropSeen[owner] || backdropSeen[owner].uid !== top.uid) {
      // A climax already down when the page opens is simply there; one played now fades in as its takeover (shown
      // just after this redraw, in announce) fades out.
      const lead = animations && !reducedMotion ? CLIMAX_SHOW_MS * 0.7 : 0;
      backdropSeen[owner] = { uid: top.uid, at: heard ? now + lead : now - CX_BACKDROP_FADE_MS };
    }
    const delay = backdropSeen[owner].at - now; // positive: still waiting for the takeover; negative: part-way in
    const style = `--cx-art: url('${esc(info.image)}'); --cx-color: ${prizeScreen.climaxColor(info)}; animation-delay: ${Math.round(delay)}ms`;
    return `<div class="cx-backdrop" style="${style}" aria-hidden="true"></div>`;
  }

  function render() {
    if (!board) return;
    // Redrawing replaces the card being hovered: the zoom carries over to whatever card is under the pointer then.
    if (art.hasZoom()) queueMicrotask(art.keepZoom);
    const me = board.me;
    const opp = board.opponent;
    const oppHand = opp ? opp.zones.hand.count : 0;
    const split = compact && opp;
    if (!split) boardView = "me";
    if (split) boardEl.dataset.view = boardView; else delete boardEl.dataset.view;
    // Widescreen puts each hand under its own side (the portraits sit at the outer edges); everything else keeps the hands in their sides.
    const wideBoard = layout === "wide" && !compact;
    const handOpp = opp ? `<div class="hand hand-opponent${avatars[opp.name] ? " has-portrait" : ""}">${handPortrait(opp.name)}<span class="zone-label">${avatars[opp.name] ? "Hand" : `${whose(opp.name)} hand`} <b>${oppHand}</b></span>
          <div class="hand-cards">${Array.from({ length: oppHand }, backHtml).join("")}</div></div>` : "";
    const handMe = `<div class="hand hand-me zone${avatars[me.name] ? " has-portrait" : ""}" data-drop="hand" data-owner="me">${handPortrait(me.name)}<span class="zone-label">Your hand <b>${me.zones.hand.length}</b></span>
          <div class="hand-cards">${me.zones.hand.map(handCardHtml).join("")}</div></div>`;
    boardEl.innerHTML = `
      ${split ? boardSwitchHtml(me, opp) : ""}
      ${opp ? `<div class="table-side side-opponent"${glowStyle(opp)}>${climaxBackdropHtml(opp, "opponent")}
        ${wideBoard ? "" : handOpp}
        ${matHtml(opp, "opponent")}</div>` : ""}
      ${wideBoard ? handOpp : ""}
      <div class="table-divider">${matchStarsHtml(0)}<span class="table-turn">${board.rps ? `Game ${gameNumber()} · rock, paper, scissors` : `${board.my_turn ? "Your turn" : `${opp ? whose(opp.name) : "Opponent's"} turn`} · game ${gameNumber()} · turn ${board.turn_number} · ${cxHtml(PHASES[board.phase])} phase`}</span>${matchStarsHtml(1)}</div>
      <div class="table-side side-me"${glowStyle(me)}>${climaxBackdropHtml(me, "me")}
        ${matHtml(me, "me")}
        ${wideBoard ? "" : handMe}
      </div>
      ${wideBoard ? handMe : ""}`;

    fx.setTableMood();
    renderControls();
    announcePhase();

    const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 20;
    logEl.innerHTML = board.log.map((entry) => entry.chat
      ? `<p class="log-chat"><b>${who(entry.who)}:</b> ${esc(entry.text)}</p>`
      : `<p>${entry.who ? `<b>${who(entry.who)}</b> ` : ""}${logHtml(entry)}</p>`).join("") + reactions.logHtml();
    if (atBottom) logEl.scrollTop = logEl.scrollHeight;

    renderModal();
    renderGameOver();
    renderIntro();
    touchScreen.renderTray();
  }

  const gameNumber = () => board.game_number || 1;

  // The controls are built once and then only updated, so the damage amount being typed survives
  // the board redrawing on every opponent move.
  function renderControls() {
    if (!controlsEl.dataset.built) {
      controlsEl.dataset.built = "1";
      controlsEl.innerHTML = `
        <p class="panel-error" role="alert" data-error hidden></p>
        <div class="ability-dock" data-ability-dock role="alertdialog" aria-live="assertive" hidden></div>
        <section class="turn-recap" data-recap aria-label="The opponent's last turn" hidden></section>
        <p class="play-turn" data-turn></p>
        <div class="phase-area">
          <div class="phase-bar" role="group" aria-label="Turn phase" data-phase-bar>
            ${PHASE_NAMES.map((p) => `<button type="button" data-phase="${p}">${cxHtml(PHASES[p])}</button>`).join("")}
          </div>
          <div class="attack-panel" data-attack-panel hidden></div>
        </div>
        <div class="undo-bar" data-undo-bar hidden>
          <button type="button" data-act='{"type":"undo"}' aria-keyshortcuts="Control+Z" title="Take back your last move (Ctrl+Z)">↶ Undo</button>
          <span class="undo-what" data-undo-what></span>
        </div>
        <p class="muted small phase-note"></p>
        <details class="play-tools" data-tools${compact ? "" : " open"}>
        <summary>Damage, sound and settings</summary>
        <div class="play-buttons">
          <button type="button" data-act='{"type":"move_top","from":"deck","to":"resolution"}'>Trigger</button>
        </div>
        <form class="damage-form" data-damage>
          <label>Damage <input type="number" name="count" min="1" max="20" value="1" required></label>
          <button type="submit">Take damage</button>
        </form>
        <p class="muted small damage-note">Cards go to your clock one at a time; a climax cancels it all.</p>
        <div class="view-options">
          <div class="layout-switch layout-switch-board" role="group" aria-label="Board view">
            ${Object.entries(LAYOUTS).map(([name, label]) => `<button type="button" data-layout="${name}">${label}</button>`).join("")}
          </div>
          <div class="layout-switch">
            <button type="button" data-animations title="Turn animations on or off">Animations</button>
          </div>
          <div class="layout-switch sound-switch">
            <button type="button" data-sound title="Turn sound on or off">Sound</button>
            <input type="range" min="0" max="100" step="5" data-sound-volume aria-label="Sound volume" title="Sound volume">
          </div>
          ${window.WeissScore ? `<div class="layout-switch sound-switch">
            <button type="button" data-music aria-keyshortcuts="M" title="Battle music: the game's moments play as part of it, in time and in key, instead of as sound effects (M)">Music</button>
            <input type="range" min="0" max="100" step="5" data-music-volume aria-label="Music volume, under the game's moments" title="Music volume, under the game's moments">
          </div>` : ""}
          <label class="song-pick" title="The battle music, or one of the songs. Kept on this browser, and the town's song too.">
            <span>Song</span><select data-song>${songOptionsHtml()}</select>
          </label>
          <p class="sr-only" data-sound-status role="status"></p>
          <div class="layout-switch">
            <button type="button" data-rules title="Turn the turn rules on or off (both players have to agree)">Turn rules</button>
          </div>
        </div>
        </details>
        <div class="rules-prompt" data-rules-prompt role="alertdialog" aria-live="assertive" hidden></div>`;
    }
    controlsEl.querySelectorAll("[data-layout]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.layout === layout));
    });
    recap.render();
    // Our last move, while we can still take it back (game.take_back): what it was, beside the button.
    const undo = !SPECTATING && board.undo;
    const undoBar = controlsEl.querySelector("[data-undo-bar]");
    undoBar.hidden = !undo;
    if (undo) controlsEl.querySelector("[data-undo-what]").textContent = undo.what ? undo.what.charAt(0).toUpperCase() + undo.what.slice(1) : "Your last move";
    controlsEl.querySelector("[data-animations]").setAttribute("aria-pressed", String(animations));
    controlsEl.querySelector("[data-sound]").setAttribute("aria-pressed", String(soundOn));
    const musicEl = controlsEl.querySelector("[data-music]");
    if (musicEl) {
      musicEl.setAttribute("aria-pressed", String(musicOn));
      musicEl.disabled = !soundOn;
      const musicVolumeEl = controlsEl.querySelector("[data-music-volume]");
      musicVolumeEl.disabled = !soundOn || !musicOn;
      if (document.activeElement !== musicVolumeEl) musicVolumeEl.value = String(musicVolume);
    }
    const songEl = controlsEl.querySelector("[data-song]");
    if (songEl) {
      if (document.activeElement !== songEl) songEl.value = song || "";
      songEl.disabled = !soundOn;
    }
    const volumeEl = controlsEl.querySelector("[data-sound-volume]");
    volumeEl.disabled = !soundOn;
    if (document.activeElement !== volumeEl) volumeEl.value = String(soundVolume);
    const errorEl = controlsEl.querySelector("[data-error]");
    errorEl.textContent = error;
    errorEl.hidden = !error;
    renderRules();
    renderAbilityDock();
    const turn = controlsEl.querySelector("[data-turn]");
    turn.textContent = board.rps ? `Game ${gameNumber()} · rock, paper, scissors`
      : `${board.my_turn ? "Your turn" : "Opponent's turn"} · game ${gameNumber()} · turn ${board.turn_number} · ${PHASES[board.phase]} phase`;
    turn.classList.toggle("mine", board.my_turn);
    // Only the turn player moves the phase on, and only forwards.
    const at = PHASE_NAMES.indexOf(board.phase);
    controlsEl.querySelectorAll("[data-phase]").forEach((button) => {
      const index = PHASE_NAMES.indexOf(button.dataset.phase);
      button.classList.toggle("current", index === at);
      button.classList.toggle("past", index < at);
      if (index === at) button.setAttribute("aria-current", "step"); else button.removeAttribute("aria-current");
      button.disabled = !board.my_turn || index <= at || Boolean(board.ability || board.rps) || (board.rules && board.phase === "encore" && reversedLeft());
      if (button.dataset.phase === "mulligan" && button.closest("[data-phase-bar]")) button.hidden = board.phase !== "mulligan";
    });
    renderAttackPanel();
    const note = controlsEl.querySelector(".phase-note");
    const ability = board.ability;
    note.innerHTML = board.ability_show && board.ability_show.check ? `${esc(board.ability_show.label || "Trigger check")}…`
      : ability && !ability.mine ? `Waiting for ${who(ability.by)} to resolve ${ability.resolving ? "an ability" : "their abilities"}…`
      : ability && ability.resolving && !ability.prompt ? "Finishing the ability…"
      : board.reveal && board.reveal.mine ? `Waiting for ${opponentWho()} to close the card you revealed.`
      : board.discard ? (board.discard.mine ? `End phase: discard ${board.discard.count} to get down to 7.`
        : `Waiting for ${opponentWho()} to discard down to 7…`)
      : board.flash && board.flash.deck ? `Flash battle: choose ${board.flash.need} cards for your level zone.`
      : board.mulligan ? (board.mulligan.me ? `Waiting for ${opponentWho()} to finish their mulligan…` : "Mulligan: choose cards to swap.")
      : !board.rules ? "Turn rules are off: anything goes."
      : board.attack ? ""
      : board.phase === "encore" && reversedLeft() ? (myReversed().length ? "Encore step: encore your reversed characters or send them to the waiting room."
        : `Encore step: waiting for ${opponentWho()} to encore their reversed characters…`)
      : inPhase("draw") ? "Draw phase: draw a card (✋ on your deck) to move on."
      : "End clears your climax zone and passes the turn.";
    note.hidden = !note.textContent;
  }

  // During the attack phase (turn rules on) the phase bar gives way to the attack's steps, with a
  // randomly picked transition each time one takes over from the other.
  let panelMode = null;

  function renderAttackPanel() {
    const bar = controlsEl.querySelector("[data-phase-bar]");
    const panel = controlsEl.querySelector("[data-attack-panel]");
    const attack = board.rules && board.phase === "attack" ? board.attack : null;
    const mode = attack ? "attack" : "phases";
    if (attack) {
      const oppName = opponentWho("Your opponent");
      const kinds = { front: "Front attack", side: "Side attack", direct: "Direct attack" };
      const steps = Object.entries(ATTACK_STEPS).map(([step, label]) =>
        `<span class="attack-step${step === attack.step ? " current" : ""}"${step === attack.step ? ' aria-current="step"' : ""}>${label}</span>`).join("");
      let status = "";
      let buttons = "";
      if (attack.step === "declare") {
        status = board.my_turn ? `Choose an attacker: ${touch ? "tap" : "hover"} a standing center-stage character.` : `Waiting for ${oppName} to attack…`;
        if (board.my_turn) buttons = '<button type="button" data-phase="encore">End attack phase</button>';
      } else {
        status = `${kinds[attack.kind]} · ${attack.soul} damage${attack.backup ? ` · backup +${attack.backup}` : ""}`;
        if (attack.step === "trigger" && attack.prompt) {
          status += board.my_turn ? ` — resolve the ${attack.prompt.kind} trigger.` : ` — waiting for ${oppName} to resolve a ${attack.prompt.kind} trigger…`;
        }
        if (attack.step === "counter") {
          status += board.my_turn ? ` — waiting for ${oppName} to counter…` : " — play a counter from your hand, or:";
          if (!board.my_turn) buttons = `${counterHidden === counterKey() ? '<button type="button" data-counter-show>Show counters</button>' : ""}<button type="button" data-act='{"type":"no_counter"}'>No counter</button>`;
        }
      }
      panel.innerHTML = `<p class="attack-title">⚔ Attack phase</p>
        <div class="attack-steps" role="list">${steps}</div>
        <p class="small attack-status">${status}</p>${buttons ? `<div class="attack-buttons">${buttons}</div>` : ""}`;
    }
    bar.hidden = Boolean(attack);
    panel.hidden = !attack;
    if (panelMode && panelMode !== mode && animations) {
      const shown = attack ? panel : bar;
      const effect = PANEL_SWAPS[Math.floor(Math.random() * PANEL_SWAPS.length)];
      shown.classList.remove(...PANEL_SWAPS);
      void shown.offsetWidth; // restart the animation
      shown.classList.add(effect);
      shown.addEventListener("animationend", () => shown.classList.remove(effect), { once: true });
    }
    panelMode = mode;
  }

  // A step of an ability the page can't do for us: it goes here, beside the board, so the cards can
  // still be moved by hand. The ability carries on once we say it's done.
  function renderAbilityDock() {
    const dock = controlsEl.querySelector("[data-ability-dock]");
    const ability = board.ability;
    const prompt = ability && ability.mine && ability.resolving ? ability.prompt : null;
    const manual = prompt && prompt.kind === "manual";
    dock.hidden = !manual;
    if (manual) {
      dock.innerHTML = `<p><b>Do this by hand</b>, then press Done:</p>
        <p class="small">${abilityText(prompt.text)}</p>
        <div class="attack-buttons">
          <button type="button" data-act='{"type":"ability_answer"}'>Done</button>
          <button type="button" data-act='{"type":"ability_stop"}' title="Leave the rest of this ability undone">Stop</button>
        </div>`;
    }
  }

  // The turn rules toggle: asking sends the other player a prompt; the rules change only if they agree.
  function renderRules() {
    const button = controlsEl.querySelector("[data-rules]");
    const request = board.rules_request;
    button.setAttribute("aria-pressed", String(board.rules));
    button.textContent = request && request.mine ? "Turn rules: asked…" : `Turn rules: ${board.rules ? "on" : "off"}`;
    button.title = request && request.mine ? "Waiting for your opponent. Click to take the request back."
      : `Ask your opponent to turn the turn rules ${board.rules ? "off" : "on"}`;
    const prompt = controlsEl.querySelector("[data-rules-prompt]");
    const asked = request && !request.mine;
    prompt.hidden = !asked;
    if (asked) {
      prompt.innerHTML = `<p><b>${opponentWho("Your opponent")}</b> wants to turn the turn rules
        <b>${request.on ? "on" : "off"}</b>. ${request.on ? "Phases and attacks will follow the rules again." : "Phases, attacks and costs will no longer be enforced."}</p>
        <div class="attack-buttons">
          <button type="button" data-act='{"type":"rules_answer","accept":true}'>Agree</button>
          <button type="button" data-act='{"type":"rules_answer","accept":false}'>Keep them ${board.rules ? "on" : "off"}</button>
        </div>`;
    }
  }

  // Game 1 starts with rock, paper, scissors for who goes first: picks stay secret until both are
  // in, a tie goes again, and the result shows for a moment before the mulligan.
  const RPS_HANDS = { rock: ["✊", "Rock"], paper: ["✋", "Paper"], scissors: ["✌️", "Scissors"] };

  function renderRps() {
    const rps = board.rps;
    const name = opponentWho("Your opponent");
    const hand = (choice, label, extra = "") => `<div class="rps-hand ${extra}"><span class="rps-symbol" role="img" aria-label="${RPS_HANDS[choice][1]}">${RPS_HANDS[choice][0]}</span><span class="small muted">${label}</span></div>`;
    const faceOff = rps.last ? `<div class="rps-faceoff">${hand(rps.last.me, "You", rps.won === false ? "rps-lost" : "")}<span class="rps-vs">vs</span>${hand(rps.last.opponent, name, rps.won ? "rps-lost" : "")}</div>` : "";
    let body;
    if (rps.won !== null) {
      // The banner's words are Barry's copy (docs/duel-presentation-plan.md).
      body = `<p class="rps-result ${rps.won ? "rps-won" : "rps-beaten"}">${rps.won ? "You go first" : `${esc(name)} goes first`}</p>`;
    } else if (rps.mine) {
      body = `<p>You chose ${RPS_HANDS[rps.mine][1].toLowerCase()}. Waiting for ${name}…</p>`;
    } else {
      body = `<p>${rps.last ? "A tie! Choose again." : "The winner goes first."}${rps.opponent_chose ? ` ${name} has chosen.` : ""}</p>
        <div class="rps-choices">${Object.entries(RPS_HANDS).map(([choice, [symbol, label]]) => `<button type="button" data-act='${esc(JSON.stringify({ type: "rps", choice }))}'>
          <span class="rps-symbol" aria-hidden="true">${symbol}</span>${label}</button>`).join("")}</div>`;
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box confirm-box rps-box" role="dialog" aria-label="Rock, paper, scissors">
      <h2>Rock, paper, scissors</h2>${faceOff}${body}</div>`;
    // Once both have picked: the hands shake, then the banner (play_versus.js). Once per result, not on each redraw.
    const revealKey = rps.won !== null ? JSON.stringify(rps.last) : null;
    if (revealKey && revealKey !== rpsRevealedFor && window.WeissVersus) {
      rpsRevealedFor = revealKey;
      window.WeissVersus.rpsReveal(modalEl.querySelector(".rps-box"), { animations });
    }
  }
  let rpsRevealedFor = null; // the result whose hands have been revealed

  // Games won in this series of rematches, either side of the turn counter: the first player on the
  // left and the second on the right, on both players' screens.
  const MAX_STARS = 8;
  function matchStarsHtml(index) {
    const { name, wins } = (board.match_wins || [])[index] || { name: "", wins: 0 };
    const stars = wins > MAX_STARS ? `★ ×${wins}` : "★".repeat(wins);
    const label = wins ? `${esc(name)}: ${wins} win${wins === 1 ? "" : "s"}` : "";
    return `<span class="match-stars match-stars-${index ? "right" : "left"}"${wins ? ` title="${label}" aria-label="${label}"` : ""}>${stars}</span>`;
  }

  // Victory or Defeat, over everything, until both players ask for a rematch or either ends the match.
  // Built once per game so its entrance plays once; only the buttons change as the other player answers.
  const CREST = `<svg class="game-over-crest" viewBox="0 0 240 150" aria-hidden="true">
    <defs><linearGradient id="crest-metal" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="var(--crest-light)"/><stop offset=".5" stop-color="var(--crest-mid)"/><stop offset="1" stop-color="var(--crest-dark)"/>
    </linearGradient></defs>
    <path fill="url(#crest-metal)" d="M96 60 L14 22 L30 58 L6 56 L34 86 L16 92 L62 108 L96 96 Z"/>
    <path fill="url(#crest-metal)" d="M144 60 L226 22 L210 58 L234 56 L206 86 L224 92 L178 108 L144 96 Z"/>
    <path fill="url(#crest-metal)" d="M120 6 L164 32 L164 84 L120 144 L76 84 L76 32 Z"/>
    <path fill="var(--crest-core)" d="M120 24 L150 42 L150 80 L120 122 L90 80 L90 42 Z"/>
    <path fill="var(--crest-gem)" d="M120 44 L136 58 L120 92 L104 58 Z"/>
  </svg>`;
  let gameOverEl = null;

  // "fight 2 of 5", or just "fight 2" in a run with no end (an infinite challenge's).
  const fightOf = () => `fight ${arcade.fight}${arcade.total ? ` of ${arcade.total}` : ""}`;
  const fightLabel = () => `${esc(arcade.scenario)} · ${fightOf()}`;

  // A CPU's image, or else its picture, for the screens either side of a match.
  const cpuImage = (screen) => (cpuInfo.images || {})[screen] || cpuInfo.image;
  function cpuPortrait(imageClass, screen) {
    if (cpuImage(screen)) return `<img class="${imageClass}" src="${esc(cpuImage(screen))}" alt="${esc(cpuInfo.name)}">`;
    const picture = cpuInfo.picture;
    return picture ? `<span class="avatar cpu-intro-picture" role="img" aria-label="${esc(cpuInfo.name)}"><img src="${esc(picture.image)}" alt="" style="width:${picture.width}%;left:${picture.left}%;top:${picture.top}%"></span>` : "";
  }

  // The CPU's screen before a match. Built once, as the board underneath keeps redrawing.
  let introEl = null;

  function renderIntro() {
    if (!intro || !cpuInfo) {
      if (introEl && window.WeissVersus) window.WeissVersus.close(introEl);
      else if (introEl) introEl.remove();
      introEl = null;
      return;
    }
    if (introEl) return;
    // The versus intro (play_versus.js) when it's loaded; the plain screen below otherwise.
    if (window.WeissVersus) {
      const ribbon = (versus && versus.ribbon && versus.ribbon.text) || (arcade ? `${arcade.scenario} · ${fightOf()}` : null);
      introEl = window.WeissVersus.intro({ cpu: cpuInfo, versus, ribbon, animations, onImpact: () => playSound("versus") });
      root.appendChild(introEl);
      return;
    }
    introEl = document.createElement("div");
    introEl.className = "cpu-intro";
    introEl.setAttribute("role", "dialog");
    introEl.setAttribute("aria-label", `${cpuInfo.name} challenges you`);
    introEl.innerHTML = `<div class="cpu-intro-box">
      ${arcade ? `<p class="cpu-intro-stage">${fightLabel()}</p>` : ""}
      ${cpuPortrait("cpu-intro-image", "intro")}
      <h2 class="cpu-intro-name">${esc(cpuInfo.name)}</h2>
      ${cpuInfo.intro ? `<p class="cpu-speech">${esc(cpuInfo.intro)}</p>` : ""}
      <button type="button" class="button-small" data-act='{"type":"intro_done"}'>Begin</button></div>`;
    root.appendChild(introEl);
  }

  // A world duel's results ceremony (play_ceremony.js), once the game-over screen is built. Its end shows the way back.
  function startCeremony(over) {
    const box = gameOverEl.querySelector("[data-ceremony]");
    if (!box) return;
    window.WeissCeremony.play(box, world.result, {
      won: over.won, cpuName: cpuInfo ? cpuInfo.name : world.result.cpu || "", animations, skipTarget: gameOverEl,
      onTick: () => playSound("tick"),
      onDone: () => {
        if (!gameOverEl) return;
        gameOverEl.dataset.ceremonyState = "done";
        const link = gameOverEl.querySelector("[data-town-link]");
        // Focus scrolls the button into view, inside the banner, on a window too short to show it.
        const summary = gameOverEl.querySelector("[data-summary-open]");
        if (summary) summary.hidden = false;
        if (link) { link.hidden = false; link.focus(); }
      },
    });
  }

  function gameOverButtons(over) {
    if (SPECTATING) return `<a class="button" href="${esc(root.dataset.challengeUrl)}">Back to the challenge</a>`;
    if (world) {
      const result = world.result;
      // With a result, the ceremony (play_ceremony.js) plays out the rewards, and this link waits for it to end.
      const waiting = Boolean(result && gameOverEl && gameOverEl.dataset.ceremonyState !== "done");
      if (result && !window.WeissCeremony) { // no ceremony file: the old one-line payout
        const paid = result.coins ? `<p class="game-over-world">+${result.coins} coins${result.first ? " (the day's first win)" : ""}${result.stake ? ", the stakes won" : ""}.</p>`
          : result.stake ? `<p class="game-over-world">The ${result.stake}-coin entry fee is gone.</p>` : "";
        return `${paid}<a class="button" href="${esc(world.town)}">Back to the town</a>`;
      }
      return `<a class="button" href="${esc(world.town)}" data-town-link${waiting ? " hidden" : ""}>Back to the town</a>`;
    }
    if (duel) return `<a class="button" href="${esc(duel.url)}">On to the augments &amp; curses</a>`;
    if (!arcade) {
      return `<button type="button" data-act='{"type":"rematch"}'${over.rematch ? " disabled" : ""}>Rematch</button>
      <button type="button" class="game-over-end" data-act='{"type":"end_match"}'>End match</button>`;
    }
    if (arcade.challenge) {
      const trial = arcade.challenge;
      if (!trial.going) return `<button type="button" data-act='{"type":"challenge_leave"}'>See how it ended</button>`;
      const deck = `<button type="button" class="game-over-end" data-act='{"type":"challenge_leave"}' title="Open packs, claim rewards and change your deck, then come back for the fight">${trial.rewards ? "Rewards, packs &amp; deck" : "Packs &amp; deck"}</button>`;
      // In co-op the path goes on, win or lose: back to it, to vote on the next floor with your partner.
      if (arcade.coop) return `<button type="button" data-act='{"type":"challenge_leave"}' title="Open packs, claim rewards and change your deck, and vote on where to go next">Back to the path</button>`;
      if (!over.won) return `<button type="button" data-act='{"type":"arcade_retry"}'>Fight again</button>${deck}`; // a second chance
      // An infinite challenge's next fight is chosen on its path, with the packs and rewards there too.
      if (arcade.defeated) return `<button type="button" data-act='{"type":"challenge_leave"}' title="Open packs, claim rewards and change your deck, then choose who to fight next">Choose your next fight</button>`;
      return `<button type="button" data-act='{"type":"arcade_continue"}'>Next fight</button>${deck}`;
    }
    if (arcade.cleared) return `<button type="button" data-act='{"type":"arcade_quit"}'>Finish</button>`;
    return `<button type="button" data-act='{"type":"${over.won ? "arcade_continue" : "arcade_retry"}"}'>${over.won ? "Continue" : "Retry"}</button>
      <button type="button" class="game-over-end" data-act='{"type":"arcade_edit_deck"}' title="Change your deck, then come back for the next fight">Edit deck</button>
      <button type="button" class="game-over-end" data-act='{"type":"arcade_quit"}'>End run</button>`;
  }

  // --- The game's summary (play_summary.js), opened from the game-over screen ---------------------------------------

  const hasSummary = (over) => Boolean(over.timeline && window.WeissSummary);

  // In a world duel the button waits for the results ceremony to finish (or be skipped), as the town's Back button does.
  function summaryButtonHtml(over) {
    if (!hasSummary(over)) return "";
    const waiting = Boolean(world && world.result && gameOverEl && gameOverEl.dataset.ceremonyState !== "done");
    return `<button type="button" class="game-over-summary-open" data-summary-open aria-haspopup="dialog"${waiting ? " hidden" : ""}>📈 How the game went</button>`;
  }

  // The panel: the game's moments (the duel recap's, from this player's seat) at the top, then the graph and the numbers.
  function summaryPanelHtml(over) {
    if (!hasSummary(over)) return "";
    const names = { me: "You", them: board.opponent ? board.opponent.name : "Your opponent" };
    const moments = over.recap && (over.recap.moments || []).length
      ? `<ul class="game-summary-moments">${over.recap.moments.map((text) => `<li>${esc(text)}</li>`).join("")}</ul>` : "";
    return `<div class="game-summary" role="dialog" aria-modal="true" aria-labelledby="game-summary-title" data-summary hidden>
      <div class="game-summary-head"><h2 id="game-summary-title">How the game went</h2>
        <button type="button" class="game-over-summary-open game-summary-close" data-summary-close>Close</button></div>
      ${moments}
      ${window.WeissSummary.html(over.timeline, names)}
    </div>`;
  }

  function wireSummary(el) {
    const panel = el.querySelector("[data-summary]");
    if (!panel) return;
    el.addEventListener("click", (event) => {
      if (event.target.closest("[data-summary-open]")) {
        panel.hidden = false;
        el.classList.add("summary-open");
        panel.querySelector("[data-summary-close]").focus();
      } else if (event.target.closest("[data-summary-close]")) {
        closeSummary();
      }
    });
  }

  // Closes the summary if it's open (Esc, or its Close button), back to the game-over screen. Whether it was.
  function closeSummary() {
    const panel = gameOverEl && gameOverEl.querySelector("[data-summary]");
    if (!panel || panel.hidden) return false;
    panel.hidden = true;
    gameOverEl.classList.remove("summary-open");
    const opener = gameOverEl.querySelector("[data-summary-open]");
    if (opener) opener.focus();
    return true;
  }

  // How a game against a boss left it: beaten, or in co-op how much is left of it.
  function bossLine(over) {
    const boss = arcade.boss;
    if (boss.down) return `The boss is down! ${arcade.coop ? `You and ${esc(arcade.coop.partner)} both get` : "You get"} ${esc(boss.reward)}.`;
    if (!boss.max) return over.won ? `Boss beaten: ${esc(boss.reward)}.` : "The boss beat you.";
    return `The boss has ${boss.health} of ${boss.max} health left${over.won ? "" : `, and the damage you dealt it stays off`}. Fight it again from the path, or let ${esc(arcade.coop.partner)} finish it.`;
  }

  // A win's score, and what made it up.
  function scoreLines(score) {
    const parts = score.parts.filter((part) => part.count).map((part) => `${part.count} ${esc(part.label)}: ${part.points}`);
    return `<p class="game-over-score">Score ${score.total}</p>${parts.length ? `<p class="game-over-score-parts">${parts.join(" · ")}</p>` : ""}`;
  }

  // The card sleeves a game unlocked: each one's back, and where to put it on.
  function sleevesUnlockedHtml(sleeves) {
    const backs = sleeves.map((s) => `<span class="pcard-back" style="--sleeve: ${esc(s.css)}"></span>`).join("");
    const names = sleeves.map((s) => esc(s.name)).join(", ");
    return `<p class="game-over-sleeves">${backs}<span>New card sleeve${sleeves.length === 1 ? "" : "s"} unlocked: ${names}! Put ${sleeves.length === 1 ? "it" : "them"} on from your profile.</span></p>`;
  }

  // The game-over screen (and its music) can wait for the damage that ended the game to turn over (play_fx.js).
  function holdGameOver(ms) {
    gameOverHeldUntil = performance.now() + ms;
    if (gameOverEl) {
      gameOverEl.remove(); // only just drawn, in this same render: unseen, so its prize slot still spins when it's back
      gameOverEl = null;
      prizeScreen.slotSpun = null;
    }
    if (score && score.running) tellScore();
    setTimeout(() => {
      if (!board || !board.game_over || gameOverHeld()) return;
      renderGameOver();
      if (score && score.running) tellScore();
    }, ms + 20);
  }

  function renderGameOver() {
    const over = board.game_over;
    if (!over) {
      if (gameOverEl) gameOverEl.remove();
      gameOverEl = null;
      return;
    }
    if (!gameOverEl && gameOverHeld()) return;
    if (!gameOverEl) {
      menus.hideMenu();
      art.hideZoom();
      gameOverEl = document.createElement("div");
      const outcome = over.won ? "win" : "lose"; // for the player
      const custom = cpuInfo && cpuImage(outcome); // a CPU with an avatar has its own screen, and its own words
      // In a town duel the CPU's game-over words are the after-win or after-loss line (world.result.cpu_line).
      const said = world && world.result ? world.result.cpu_line : custom && (over.won ? cpuInfo.win : cpuInfo.lose);
      gameOverEl.className = `game-over ${over.won ? "game-over-victory" : "game-over-defeat"}${custom ? " game-over-custom" : ""}${animations ? " animated" : ""}`;
      gameOverEl.setAttribute("role", "alertdialog");
      gameOverEl.setAttribute("aria-label", over.won ? "Victory" : "Defeat");
      const loser = over.won ? opponentWho("Your opponent") : "You";
      const reason = over.reason === "deck" ? `${loser} can't refresh ${over.won ? "their" : "your"} deck.`
        : over.reason === "boss" ? "The boss's health bar is empty."
        : over.reason === "concede" ? `${loser} conceded.` : `${loser} reached level 4.`;
      gameOverEl.innerHTML = `<div class="game-over-rays"></div>
        <div class="game-over-banner">${CREST}${custom ? `<div class="game-over-cpu">${cpuPortrait("game-over-cpu-image", outcome)}</div>` : ""}
          <h2 class="game-over-word">${over.won ? "Victory" : "Defeat"}</h2>
          <p class="game-over-reason">${reason}</p>
          ${said ? `<figure class="game-over-quote"><p class="game-over-quote-line">“${esc(said)}”</p><figcaption class="game-over-quote-name">${esc(cpuInfo ? cpuInfo.name : "")}</figcaption></figure>` : ""}
          ${over.score ? scoreLines(over.score) : ""}
          ${arcade && arcade.challenge && over.won ? `<p class="game-over-arcade">${prize ? "" : `Won: ${esc(arcade.challenge.won)} · `}${arcade.challenge.packs} packs to open</p>` : ""}
          ${arcade && arcade.challenge && !over.won && !arcade.coop ? `<p class="game-over-arcade">${arcade.challenge.going ? `A second chance: you can fight again${arcade.challenge.lives ? ` (${arcade.challenge.lives} more left)` : ""}.` : "The challenge is over."}</p>` : ""}
          ${arcade && arcade.coop && !over.won ? `<p class="game-over-arcade">${arcade.challenge && arcade.challenge.going ? `Lost games: ${arcade.coop.losses} of ${arcade.coop.limit}, yours and ${esc(arcade.coop.partner)}'s together.` : `That was the last loss: the co-op challenge is over.`}</p>` : ""}
          ${arcade && arcade.boss ? `<p class="game-over-arcade">${bossLine(over)}</p>` : ""}
          ${duel ? `<p class="game-over-arcade">${over.won ? "You pick your augment and curse first." : `${esc(duel.partner)} picks their augment and curse first.`} Rivalry: you ${duel.mine} – ${duel.theirs} ${esc(duel.partner)}</p>` : ""}
          ${arcade ? `<p class="game-over-arcade">${arcade.cleared ? `🏆 ${esc(arcade.scenario)} cleared!` : over.won ? `Up next: ${fightOf()}` : `${esc(arcade.scenario)}: ${fightOf()}`}${arcade.score ? ` · run score ${arcade.score}` : ""}</p>` : ""}
          ${over.won && prize ? prizeScreen.prizeSlotHtml(prize) : ""}
          ${unlocked ? sleevesUnlockedHtml(unlocked) : ""}
          <p class="game-over-status" data-game-over-status></p>
          ${world && world.result ? `<div class="ceremony" data-ceremony></div>` : ""}
          <div class="game-over-buttons" data-game-over-buttons></div>
          ${summaryButtonHtml(over)}</div>
        ${summaryPanelHtml(over)}`;
      root.appendChild(gameOverEl);
      wireSummary(gameOverEl);
      if (world && world.result && window.WeissCeremony) startCeremony(over);
      if (over.won && prize) prizeScreen.spinPrizeSlot(gameOverEl.querySelector(".slot"), prize);
    }
    const name = opponentWho("Your opponent");
    gameOverEl.querySelector("[data-game-over-status]").innerHTML = (error && esc(error))
      || (over.rematch ? `Waiting for ${name} to accept the rematch…` : over.opponent_rematch ? `${name} wants a rematch.` : "");
    gameOverEl.querySelector("[data-game-over-buttons]").innerHTML = gameOverButtons(over);
  }

  // A decision's pop-up (one without a Close button) can be put aside to look at the board, until we go back to it
  // or there's a different decision to make: peekKey is the pop-up being put aside, shownKey the one showing.
  // While it's aside, a pile can be looked through (its Close goes back to the board, or straight back to the
  // choice when the pile was opened from the choice's own button).
  let peekKey = null;
  let shownKey = null;
  const peekEl = document.createElement("button");
  peekEl.type = "button";
  peekEl.className = "play-peek-back";
  peekEl.dataset.peekBack = "";
  peekEl.textContent = "Back to the choice";
  peekEl.hidden = true;
  root.appendChild(peekEl);

  // A pop-up hides the tray of buttons for a picked card (touch), and closing it brings the tray back.
  function renderModal() {
    renderModalBox();
    touchScreen.renderTray();
  }

  function renderModalBox() {
    drawModal();
    peekEl.hidden = true;
    const box = modalEl.hidden ? null : modalEl.querySelector(".play-modal-box");
    if (!box || SPECTATING || box.querySelector("[data-close], [data-counter-hide]")) {
      peekKey = shownKey = null;
      return;
    }
    const key = modalEl.innerHTML;
    if (peekKey === key) {
      if (modal && modal.zone) return renderPileModal(); // looking through a pile while the choice is aside
      modalEl.hidden = true;
      peekEl.hidden = false;
      return;
    }
    peekKey = null;
    shownKey = key;
    // A choice that talks about the waiting room gets a way to look through all of it first.
    const waiting = /waiting room/i.test(box.textContent) && board.me
      ? `<button type="button" class="button-cancel play-peek" data-peek-pile="waiting">Your waiting room (${pileCards(board.me, "waiting").length})</button>`
      : "";
    box.insertAdjacentHTML("afterbegin", `<button type="button" class="button-cancel play-peek" data-peek>Look at the board</button>${waiting}`);
  }

  function drawModal() {
    if (board.game_over) {
      modalEl.hidden = true;
      return;
    }
    if (SPECTATING) {
      if (board.reveal && board.reveal.card) return renderReveal();
      if (modal && (modal.zone || modal.revealed)) return renderPileModal();
      modalEl.hidden = true;
      return;
    }
    if (board.rps) return renderRps();
    if (board.reveal && board.reveal.card) return renderReveal();
    if (modal && modal.confirmClimax) return renderClimaxConfirm();
    if (modal && modal.confirmFree) return renderFreeConfirm();
    if (board.flash && board.flash.deck) return renderFlashLevel();
    if (board.mulligan && !board.mulligan.me) return renderMulligan();
    if (board.discard && board.discard.mine) return renderDiscard();
    if (board.level_up_pending) return renderLevelUp();
    if (board.ability && board.ability.mine && !board.ability.resolving) return renderAbilityQueue();
    if (board.ability && board.ability.mine && board.ability.prompt && board.ability.prompt.kind !== "manual") return renderAbilityPrompt();
    if (modal && modal.abilities) return renderAbilityList();
    if (board.my_turn && board.attack && board.attack.step === "trigger" && board.attack.prompt && !board.ability_show) return renderTriggerPrompt();
    if (counterDue()) return renderCounterPrompt();
    if (encoreDue()) return renderEncorePrompt();
    if (!modal) {
      modalEl.hidden = true;
      return;
    }
    renderPileModal();
  }

  // A pile (or the cards an action revealed) to look through.
  function renderPileModal() {
    let list;
    let owner = "me";
    if (modal.revealed) {
      list = modal.revealed.map((c) => cardHtml(c, "me", "deck"));
    } else {
      owner = modal.owner;
      const side = owner === "me" ? board.me : board.opponent;
      list = pileCards(side, modal.zone).slice().reverse().map((c) => {
        const button = owner === "me" ? activateButtonHtml(c) : "";
        return button ? `<div class="trigger-option">${cardHtml(c, owner, modal.zone)}${button}</div>` : cardHtml(c, owner, modal.zone);
      });
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="${esc(modal.title)}">
      <div class="play-modal-head"><h2>${modal.owner && modal.owner !== "me" && board.opponent ? `${whose(board.opponent.name)} ${LABELS[modal.zone].toLowerCase()}` : esc(modal.title)}</h2><button type="button" data-close>Close</button></div>
      <p class="muted small">${owner === "me" && !SPECTATING ? `${touch ? "Tap" : "Click"} a card to move it. Top of the pile first.` : "Top of the pile first."}</p>
      <div class="play-modal-cards">${list.join("") || '<p class="empty">Empty.</p>'}</div>
    </div>`;
  }

  // Ability text, with CX marks and line breaks.
  const abilityText = (text) => cxHtml(text).replace(/\n/g, "<br>");

  // A small picture of the card an ability belongs to.
  function abilitySourceHtml(pk) {
    const info = pk ? cards[pk] : null;
    return info ? `<img class="ability-source" src="${esc(info.image)}" alt="${esc(info.name)}" data-card="${pk}">` : "";
  }

  // Abilities of ours that have triggered: each can be triggered or skipped, in any order.
  function renderAbilityQueue() {
    const queue = board.ability.queue;
    const send = (entry, accept, label, extra = "") => `<button type="button" ${extra} data-act='${esc(JSON.stringify({ type: "ability_trigger", id: entry.id, accept }))}'>${label}</button>`;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box ability-box" role="alertdialog" aria-label="Ability triggered">
      <div class="play-modal-head"><h2>Ability triggered${queue.length > 1 ? `: ${queue.length} to resolve` : ""}</h2></div>
      ${queue.length > 1 ? '<p class="muted small">Resolve them in any order.</p>' : ""}
      ${queue.map((entry) => {
        const info = cards[entry.card];
        return `<div class="ability-row">${abilitySourceHtml(entry.card)}
          <div><p class="play-preview-name">${esc(info ? info.name : "Card")}</p>
            <div class="card-peek-text">${abilityText(entry.text)}</div>
            <div class="trigger-buttons">${send(entry, true, entry.event ? "Play it" : "Trigger")}${send(entry, false, "Skip", 'class="button-cancel"')}</div>
          </div></div>`;
      }).join("")}
    </div>`;
  }

  // Putting a card on a stage: that stage as it stands, each position the card may go to a button. The
  // picked position shows the stage as it will be: the card there (as it will stand), the character it
  // replaces named on its way to the waiting room, and the position it leaves if it's moving within the stage.
  // A stage drawn small in a prompt, as it sits on the board: the opponent's faces us, back row furthest
  // away and their left on our right. `cell` draws each position (stageSlotHtml).
  // Either stage comes with the other side's center stage across from it (`facing`, read only), each character
  // opposite the one it faces, as on the board: what they're up against is part of the choice, and it tells apart
  // two of the same card. Ours has theirs above it; theirs has ours below it.
  function stageBoardHtml(owner, cell, facing = null) {
    const theirs = owner === "opponent";
    const facingWhose = theirs ? "Your" : `${board.opponent.name}'s`;
    const facingCell = (slot) => {
      const card = facing.stage[slot];
      const note = card ? stageNameOf(card) : "Empty";
      return `<div class="place-slot place-slot-facing" aria-label="${esc(`${facingWhose} ${LABELS[slot].toLowerCase()}: ${note}`)}">
        <span class="place-slot-card">${card ? cardHtml(card, "view", slot).replace('tabindex="0"', 'tabindex="-1"') : '<span class="zone-empty"></span>'}</span>
        <span class="place-slot-note" title="${esc(note)}">${esc(note)}</span></div>`;
    };
    const row = facing ? `<div class="place-row place-row-facing">${["C1", "C2", "C3"].map(facingCell).join("")}</div>` : "";
    const caption = facing ? `<p class="place-facing-caption muted small">${theirs ? "Your center stage, facing theirs" : `${esc(board.opponent.name)}'s center stage, facing yours`}</p>` : "";
    // Their board is drawn bottom to top (column-reverse), so ours goes first to come out under it.
    const across = theirs ? row + caption : caption + row;
    return `<div class="place-board${owner === "opponent" ? " place-board-opponent" : ""}" role="group" aria-label="${owner === "opponent" ? "Their" : "Your"} stage">
      ${across}
      <div class="place-row">${["C1", "C2", "C3"].map(cell).join("")}</div>
      <div class="place-row">${["B1", "B2"].map(cell).join("")}</div></div>`;
  }

  const stageNameOf = (c) => (c.card && cards[c.card] ? cards[c.card].name : "a face-down card");

  function stageSlotHtml(slot, { card, can, picked, note, noteHtml = esc(note), out = false, attrs, badge = "" }) {
    return `<div class="place-slot${picked ? " picked" : ""}${can ? "" : " unpickable"}" ${can ? attrs : 'aria-disabled="true"'} aria-label="${esc(`${LABELS[slot]}: ${note}`)}">
      <span class="place-slot-label">${LABELS[slot]}</span>
      <span class="place-slot-card">${card ? cardHtml(card, "view", slot).replace('tabindex="0"', 'tabindex="-1"') : '<span class="zone-empty"></span>'}${badge}</span>
      <span class="place-slot-note${out ? " out" : ""}" title="${esc(note)}">${noteHtml}</span></div>`;
  }

  // An ability choosing characters on the stage (a target, or a cost): each stage they're on, drawn as on
  // the board, each one that may be chosen a button. The usual picks (abilityPicks) and Confirm apply.
  function choiceBoardsHtml(prompt, options, ordered) {
    // Their stage first (it's across the table), then ours. Each has the other side's center stage across from it.
    const owners = ["opponent", "me"].filter((owner) => prompt.cards.some((c) => c.side === owner));
    return owners.map((owner) => {
      const side = owner === "me" ? board.me : board.opponent;
      const across = owner === "me" ? board.opponent : board.me;
      const cell = (slot) => {
        const card = side.stage[slot];
        const can = Boolean(card) && options.has(card.uid);
        const at = can ? abilityPicks.indexOf(card.uid) : -1;
        // Which character it's facing, said too, for two of the same card (and for a screen reader).
        const faced = slot.startsWith("C") && across ? across.stage[OPPOSITE[slot]] : null;
        const facesNote = faced ? ` · facing ${owner === "me" ? "their" : "your"} ${stageNameOf(faced)}` : "";
        const note = !card ? "Empty" : (at >= 0 ? `${stageNameOf(card)} · chosen` : can ? stageNameOf(card) : `${stageNameOf(card)} · can't be chosen`) + facesNote;
        return stageSlotHtml(slot, {
          card, can, picked: at >= 0, note, noteHtml: esc(card ? stageNameOf(card) : "Empty"),
          attrs: can ? `role="button" tabindex="0" aria-pressed="${at >= 0}" data-ability-pick="${esc(card.uid)}"` : "",
          badge: at >= 0 ? `<span class="ability-order">${ordered ? at + 1 : "✓"}</span>` : "",
        });
      };
      return `<div><p class="muted small place-caption">${owner === "me" ? "Your stage" : `${esc(board.opponent.name)}'s stage`}</p>${stageBoardHtml(owner, cell, across)}</div>`;
    }).join("");
  }

  function placeBoardHtml({ side, owner, slots, card, pos, picked }) {
    const nameOf = stageNameOf;
    const cell = (slot) => {
      const can = slots.includes(slot);
      const here = side.stage[slot];
      const moving = card && here && here.uid === card.uid; // the card being placed is on this position now
      let shown = here;
      let note = !here ? "Empty" : moving ? "Here now" : `Replaces ${nameOf(here)}`;
      let out = false;
      if (picked === slot) {
        shown = card ? { ...card, pos } : here;
        if (here && !moving) [note, out] = [`${nameOf(here)} → waiting room`, true];
        else note = card ? `${nameOf(card)} goes here` : "Your character goes here";
      } else if (moving && picked) {
        [shown, note] = [null, "Moves from here"];
      } else if (!can) {
        note = "Can't go here";
      }
      return stageSlotHtml(slot, {
        card: shown, can, picked: picked === slot, note, out,
        // A long name is cut short, but never the "→ waiting room" after it: that's the part that matters.
        noteHtml: out ? `<span class="place-slot-name">${esc(nameOf(here))}</span>→ waiting room` : esc(note),
        attrs: `role="button" tabindex="0" aria-pressed="${picked === slot}" data-place-pick="${slot}"`,
      });
    };
    return stageBoardHtml(owner, cell, owner === "me" ? board.opponent : board.me);
  }

  const placeButtonLabel = (slot) => (slot ? `Put it on ${LABELS[slot].toLowerCase()}` : "Choose a position");

  // An ability being resolved needs an answer: cards to pick, or one choice from a list.
  function renderAbilityPrompt() {
    const ability = board.ability;
    const prompt = ability.prompt;
    const info = cards[ability.card];
    const options = new Set(prompt.options && prompt.kind === "cards" ? prompt.options : []);
    abilityPicks = abilityPicks.filter((uid) => options.has(uid));
    // The other player's ability can't be stopped from here, though it may be asking us to choose.
    const stopButton = ability.can_stop ? '<button type="button" class="button-cancel" data-act=\'{"type":"ability_stop"}\' title="Leave the rest of this ability undone">Stop</button>' : "";
    // Where a card is, and on whose side: "Their center stage (left)", "Your waiting room".
    const label = (card) => {
      if (!card.where || !LABELS[card.where]) return "";
      const whose = card.side === "opponent" ? "Their" : card.side === "me" ? "Your" : "";
      return `<span class="muted small">${esc(whose ? `${whose} ${LABELS[card.where].toLowerCase()}` : LABELS[card.where])}</span>`;
    };
    let body;
    if (prompt.kind === "cards") {
      const count = abilityPicks.length;
      const need = prompt.min === prompt.max ? `${prompt.max}` : `${prompt.min}–${prompt.max}`;
      const ready = count >= prompt.min && count <= prompt.max;
      const ordered = prompt.for === "order";
      // All on the stage (and the board we hold agrees): chosen there, among the characters around them.
      const stageOf = (c) => (c.side === "me" ? board.me : board.opponent || { stage: {} }).stage;
      const onStage = prompt.for !== "look" && prompt.cards.length > 0
        && prompt.cards.every((c) => STAGE.includes(c.where) && c.side && (stageOf(c)[c.where] || {}).uid === c.uid);
      body = `<p class="small"><b>${esc(prompt.title)}</b>${prompt.for === "look" ? "" : ` (${count} of ${need} chosen)`}</p>
        ${onStage ? `<div class="place-layout">${choiceBoardsHtml(prompt, options, ordered)}</div>` : `<div class="play-modal-cards">${prompt.cards.map((c) => {
          const can = options.has(c.uid);
          const picked = abilityPicks.indexOf(c.uid);
          return `<div class="trigger-option"><div class="level-pick${picked >= 0 ? " picked" : ""}${can ? "" : " unpickable"}"${can ? ` role="button" tabindex="0" aria-pressed="${picked >= 0}" data-ability-pick="${esc(c.uid)}"` : ""}>
            ${cardHtml(c, "view", "ability")}${ordered && picked >= 0 ? `<span class="ability-order">${picked + 1}</span>` : ""}</div>${label(c)}</div>`;
        }).join("")}</div>`}
        <div class="trigger-buttons"><button type="button" data-ability-submit${ready ? "" : " disabled"}>${prompt.for === "look" ? "OK" : count || prompt.min ? "Confirm" : "Choose none"}</button>${stopButton}</div>`;
    } else if (prompt.for === "place" && (prompt.cards || []).length) {
      const card = prompt.cards[0]; // the one this answer places (an ability placing several asks again for each)
      const slots = prompt.options.map((option) => option.value);
      const kind = `ability:${card.uid}`;
      if (placePick.kind !== kind || !slots.includes(placePick.slot)) placePick = { kind, uid: card.uid, slot: slots.length === 1 ? slots[0] : null };
      const theirs = prompt.side === "opponent";
      const pos = prompt.rest ? "rest" : prompt.keep_pos ? card.pos : "stand";
      body = `<p class="small"><b>${abilityText(prompt.title)}</b></p>
        <div class="place-layout">
          <div class="play-modal-cards">${prompt.cards.map((c) => `<div class="trigger-option">${cardHtml(c, "view", "ability")}${label(c)}</div>`).join("")}</div>
          <div><p class="muted small place-caption">${theirs ? `${esc(board.opponent.name)}'s stage` : "Your stage"}${pos === "rest" ? " · it goes in rested" : ""}</p>
            ${placeBoardHtml({ side: theirs ? board.opponent : board.me, owner: theirs ? "opponent" : "me", slots, card, pos, picked: placePick.slot })}</div>
        </div>
        <div class="trigger-buttons"><button type="button" data-place-submit${placePick.slot ? "" : " disabled"}>${placeButtonLabel(placePick.slot)}</button>${stopButton}</div>`;
    } else {
      const shown = prompt.cards || [];
      body = `<p class="small"><b>${abilityText(prompt.title)}</b></p>
        ${shown.length ? `<div class="play-modal-cards">${shown.map((c) => `<div class="trigger-option">${cardHtml(c, "view", "ability")}${label(c)}</div>`).join("")}</div>` : ""}
        <div class="trigger-buttons ability-choices">${prompt.options.map((option) => `<button type="button" data-act='${esc(JSON.stringify({ type: "ability_answer", value: option.value }))}'>${abilityText(option.label)}</button>`).join("")}${stopButton}</div>`;
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box ability-box" role="dialog" aria-label="Resolve ability">
      <div class="ability-row">${abilitySourceHtml(ability.card)}
        <div><p class="play-preview-name">${esc(info ? info.name : "Ability")}</p>
          <div class="card-peek-text">${abilityText(ability.text)}</div></div></div>
      ${body}
    </div>`;
  }

  // The ! button's list: this card's activated abilities, each with what's stopping it, if anything.
  // Asks first because activating pays the cost straight away.
  function renderAbilityList() {
    const rows = (board.acts || {})[modal.abilities];
    if (!rows) {
      modal = null;
      return drawModal();
    }
    const pk = rows[0].card;
    const info = cards[pk];
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box ability-box" role="dialog" aria-label="Activate an ability">
      <div class="play-modal-head"><h2>${esc(info ? info.name : "Abilities")}</h2><button type="button" data-close>Close</button></div>
      ${rows.map((row) => `<div class="ability-row">${abilitySourceHtml(pk)}
        <div><div class="card-peek-text">${abilityText(row.text)}</div>
          <div class="trigger-buttons">${row.why
            ? `<button type="button" disabled>Activate</button> <span class="muted small">Can't now: ${esc(row.why)}</span>`
            : `<button type="button" data-act='${esc(JSON.stringify({ type: "activate", uid: modal.abilities, index: row.index }))}' data-close-after>Activate</button>`}</div></div></div>`).join("")}
    </div>`;
  }

  // A card the opponent revealed from their hand: shown large with its text until we close it
  // (their turn waits for that).
  function renderReveal() {
    const info = cards[board.reveal.card];
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box reveal-box" role="dialog" aria-label="Revealed card">
      <div class="play-modal-head"><h2>${who(board.reveal.by)} reveals</h2>
        <button type="button" data-act='{"type":"close_reveal"}'>Close</button></div>
      ${info ? `<div class="reveal-card"><img src="${esc(info.image)}" alt="${esc(info.name)}">
        <div><p class="play-preview-name">${esc(info.name)}</p>
          <p class="small muted">${esc([info.type, info.color, info.level != null ? `Level ${info.level}` : "", info.cost != null ? `Cost ${info.cost}` : "",
            info.power != null ? `Power ${info.power}` : "", info.soul != null ? `Soul ${info.soul}` : ""].filter(Boolean).join(" · "))}</p>
          ${info.text ? `<div class="card-peek-text">${esc(info.text).replace(/\n/g, "<br>")}</div>` : ""}</div></div>` : ""}
    </div>`;
  }

  // How to pay for a card that can be played with 0 cost by giving up a character.
  function renderFreeConfirm() {
    const action = modal.confirmFree;
    const card = board.me.zones.hand.find((c) => c.uid === action.uid);
    const options = (board.free_plays || {})[action.uid];
    if (!card || !options) {
      modal = null;
      return drawModal();
    }
    const info = cards[card.card];
    const stage = Object.values(board.me.stage).filter(Boolean);
    const give = options.map((uid) => {
      const given = stage.find((c) => c.uid === uid);
      const name = given && cards[given.card] ? cards[given.card].name : "that character";
      return `<button type="button" data-act='${esc(JSON.stringify({ ...action, free_with: uid }))}'>Send ${esc(name)} to the waiting room, pay 0</button>`;
    }).join("");
    const cost = handStat(card, info, "cost") || 0;
    const enough = board.me.zones.stock.count >= cost;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box confirm-box" role="alertdialog" aria-label="Choose how to pay">
      <div class="play-modal-head"><h2>Play ${info ? esc(info.name) : "this card"}</h2></div>
      <div class="trigger-buttons">
        ${give}
        <button type="button" data-act='${esc(JSON.stringify({ ...action, pay_full: true }))}'${enough ? "" : " disabled"}>Pay ${cost} stock</button>
        <button type="button" class="button-cancel" data-close>Cancel</button>
      </div>
    </div>`;
  }

  // Playing a climax from the main phase ends the main phase: confirm first.
  function renderClimaxConfirm() {
    const card = board.me.zones.hand.find((c) => c.uid === modal.confirmClimax);
    const info = card && cards[card.card];
    if (!card || !inPhase("main")) {
      modal = null;
      return drawModal();
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box confirm-box" role="alertdialog" aria-label="Play a climax">
      <div class="play-modal-head"><h2>Play ${CX_HTML}${info ? ` ${esc(info.name)}` : ""}?</h2></div>
      <p>Playing a climax card ends your main phase: it goes into your ${CX_HTML} zone, and your attack phase follows.</p>
      <div class="trigger-buttons">
        <button type="button" data-act='${esc(JSON.stringify({ type: "move", uid: card.uid, to: "climax", end_main: true }))}'>Play it</button>
        <button type="button" class="button-cancel" data-close>Cancel</button>
      </div>
    </div>`;
  }

  // The end phase's discard: pick exactly enough cards to bring the hand down to 7.
  function renderDiscard() {
    const hand = board.me.zones.hand;
    const need = board.discard.count;
    for (const uid of [...discardPicks]) if (!hand.some((c) => c.uid === uid)) discardPicks.delete(uid);
    const picked = discardPicks.size;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="Discard">
      <div class="play-modal-head"><h2>Discard ${need} card${need === 1 ? "" : "s"}</h2></div>
      <p class="muted small">Your hand is over 7 at the end of your turn. Choose ${need} card${need === 1 ? "" : "s"} for your waiting room (${picked} of ${need} chosen).</p>
      <div class="play-modal-cards">${hand.map((c) => `<div class="level-pick${discardPicks.has(c.uid) ? " picked" : ""}" role="button"
        tabindex="0" aria-pressed="${discardPicks.has(c.uid)}" data-discard-pick="${esc(c.uid)}">${cardHtml(c, "me", "discard")}</div>`).join("")}</div>
      <div class="trigger-buttons"><button type="button" data-discard-submit${picked === need ? "" : " disabled"}>Discard ${picked === need ? "them" : `${need}`}</button></div>
    </div>`;
  }

  // A flash battle, before the mulligan: pick cards from the deck for the level zone (see flash_start in game.py).
  function renderFlashLevel() {
    const need = board.flash.need;
    const deck = [...board.flash.deck].sort((a, b) => (Number((cards[b.card] || {}).level) || 0) - (Number((cards[a.card] || {}).level) || 0)
      || String((cards[a.card] || {}).name || "").localeCompare(String((cards[b.card] || {}).name || "")));
    for (const uid of [...flashPicks]) if (!deck.some((c) => c.uid === uid)) flashPicks.delete(uid);
    const picked = flashPicks.size;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="Flash battle">
      <div class="play-modal-head"><h2>Flash battle</h2></div>
      <p class="muted small">You start at level ${need}. Choose ${need} cards from your deck for your level zone; then your deck is shuffled and you draw your hand.
        After the mulligan, the top 3 cards of your deck go to your stock.</p>
      <div class="play-modal-cards">${deck.map((c) => {
        const on = flashPicks.has(c.uid);
        const can = on || picked < need;
        return `<div class="level-pick${on ? " picked" : ""}${can ? "" : " unpickable"}"${can ? ` role="button" tabindex="0" aria-pressed="${on}" data-flash-pick="${esc(c.uid)}"` : ""}>${cardHtml(c, "me", "flash")}</div>`;
      }).join("")}</div>
      <div class="trigger-buttons"><button type="button" data-flash-submit${picked === need ? "" : " disabled"}>${picked === need ? "Put them in my level zone" : `Choose ${need - picked} more`}</button></div>
    </div>`;
  }

  // Turn 1's mulligan: pick any cards in the hand to swap for new ones (or keep it as it is).
  function renderMulligan() {
    const hand = board.me.zones.hand;
    for (const uid of [...mulliganPicks]) if (!hand.some((c) => c.uid === uid)) mulliganPicks.delete(uid);
    const count = mulliganPicks.size;
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="Mulligan">
      <div class="play-modal-head"><h2>Mulligan</h2></div>
      <p class="muted small">Pick any cards to put into your waiting room; you'll draw as many new ones.</p>
      <div class="play-modal-cards">${hand.map((c) => `<div class="level-pick${mulliganPicks.has(c.uid) ? " picked" : ""}" role="button"
        tabindex="0" aria-pressed="${mulliganPicks.has(c.uid)}" data-mulligan-pick="${esc(c.uid)}">${cardHtml(c, "me", "mulligan")}</div>`).join("")}</div>
      <div class="trigger-buttons"><button type="button" data-mulligan-submit>${count ? `Mulligan ${count} card${count === 1 ? "" : "s"}` : "Keep my hand"}</button></div>
    </div>`;
  }

  // A trigger with a choice in it, for the attacker (see trigger_prompt in game.py).
  const TRIGGERS = {
    comeback: { title: "Comeback trigger", text: "You may return a character from your waiting room to your hand.", to: { hand: "→ Hand" } },
    gate: { title: "Gate trigger", text: "You may return a climax from your waiting room to your hand.", to: { hand: "→ Hand" } },
    choice: { title: "Choice trigger", text: "You may put a character with a soul trigger from your waiting room into your hand or your stock.", to: { hand: "→ Hand", stock: "→ Stock" } },
    standby: { title: "Standby trigger", text: "You may put a character of up to your level + 1 from your waiting room onto your stage, rested.", to: { C1: "Center L", C2: "Center M", C3: "Center R", B1: "Back L", B2: "Back R" } },
    treasure: { title: "Treasure trigger", text: "The treasure went to your hand. Put the top card of your deck into your stock?" },
    draw: { title: "Draw trigger", text: "You may draw a card." },
    pool: { title: "Pool trigger", text: "You may put the top card of your deck into your stock." },
    bounce: { title: "Bounce trigger", text: "You may return one of your opponent's characters to their hand." },
  };
  const YES_NO = { treasure: ["Yes, to my stock", "No"], draw: ["Draw a card", "No"], pool: ["Yes, to my stock", "No"] };

  function renderTriggerPrompt() {
    const prompt = board.attack.prompt;
    const trigger = TRIGGERS[prompt.kind];
    const choice = (action, label) => `<button type="button" data-act='${esc(JSON.stringify({ type: "trigger_choice", ...action }))}'>${label}</button>`;
    let body;
    if (YES_NO[prompt.kind]) {
      const [yes, no] = YES_NO[prompt.kind];
      body = `<div class="trigger-buttons">${choice({ accept: true }, yes)}${choice({ accept: false }, no)}</div>`;
    } else if (prompt.kind === "bounce") {
      const theirs = Object.values(board.opponent.stage).filter((c) => c && prompt.options.includes(c.uid));
      body = `<div class="play-modal-cards">${theirs.map((c) => `<div class="trigger-option">${cardHtml(c, "view", "bounce")}
          <div class="trigger-buttons">${choice({ uid: c.uid }, "→ Their hand")}</div>
        </div>`).join("")}</div>
        <div class="trigger-buttons">${choice({}, "Choose nothing")}</div>`;
    } else if (prompt.kind === "standby") {
      // Pick the character, then where it goes (in either order): the stage shows the result before it's done.
      const options = board.me.zones.waiting.filter((c) => prompt.options.includes(c.uid));
      const kind = `standby:${board.turn_number}:${board.attacks}`; // a fresh choice for each attack's trigger
      if (placePick.kind !== kind) placePick = { kind, uid: null, slot: null };
      if (!options.some((c) => c.uid === placePick.uid)) placePick.uid = options.length === 1 ? options[0].uid : null;
      const card = options.find((c) => c.uid === placePick.uid) || null;
      const ready = card && placePick.slot;
      body = `<p class="small"><b>Choose a character</b></p>
        <div class="play-modal-cards">${options.map((c) => `<div class="level-pick${c === card ? " picked-place" : ""}" role="button" tabindex="0"
          aria-pressed="${c === card}" data-standby-pick="${esc(c.uid)}">${cardHtml(c, "view", "waiting").replace('tabindex="0"', 'tabindex="-1"')}</div>`).join("")}</div>
        <p class="small place-caption"><b>Choose where it goes</b> <span class="muted">· it goes in rested</span></p>
        ${placeBoardHtml({ side: board.me, owner: "me", slots: STAGE, card, pos: "rest", picked: placePick.slot })}
        <div class="trigger-buttons"><button type="button" data-standby-submit${ready ? "" : " disabled"}>${card ? placeButtonLabel(placePick.slot) : "Choose a character"}</button>${choice({}, "Choose nothing")}</div>`;
    } else {
      const options = board.me.zones.waiting.filter((c) => prompt.options.includes(c.uid));
      body = `<div class="play-modal-cards">${options.map((c) => `<div class="trigger-option">${cardHtml(c, "me", "waiting")}
          <div class="trigger-buttons">${Object.entries(trigger.to).map(([to, label]) => choice({ uid: c.uid, to }, label)).join("")}</div>
        </div>`).join("")}</div>
        <div class="trigger-buttons">${choice({}, "Choose nothing")}</div>`;
    }
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="${trigger.title}">
      <div class="play-modal-head"><h2>${trigger.title}</h2></div>
      <p class="muted small">${trigger.text}</p>${body}
    </div>`;
  }

  // Our counter step, when we hold a counter we can play right now (the server lists them in
  // attack.counters): it pops up with each of them and the battle as it stands. "Look at the board"
  // puts it aside for this attack; the attack panel's "Show counters" brings it back.
  let counterHidden = null;
  const counterKey = () => board.attack ? `${board.turn_number}:${board.attacks}:${board.attack.uid}` : null;
  const counterDue = () => !board.my_turn && board.attack && board.attack.step === "counter" && (board.attack.counters || []).length > 0
    && !board.ability && !board.ability_show && counterHidden !== counterKey();
  const BACKUP_POWER = /Backup\s*(\d+)/i;

  function renderCounterPrompt() {
    const attack = board.attack;
    const options = board.me.zones.hand.filter((c) => attack.counters.includes(c.uid));
    const power = (card) => card && ((board.stats || {})[card.uid] || {}).power;
    const attacker = Object.values(board.opponent.stage).find((c) => c && c.uid === attack.uid);
    const defender = attack.kind === "front" ? board.me.stage[attack.target] : null;
    const nameOf = (card, fallback) => (card && (cards[card.card] || {}).name) || fallback;
    const powerOf = (card) => Number(power(card) ?? (cards[card.card] || {}).power);
    // The battle as it stands: their attacker opposite the character it's attacking (a front attack), with the
    // power each has now (ours includes any backup already played) and how it would end.
    const theirs = attacker ? powerOf(attacker) : NaN;
    const mine = defender ? powerOf(defender) + (attack.backup || 0) : NaN;
    const battling = Number.isFinite(theirs) && Number.isFinite(mine);
    const outcome = (yours) => yours > theirs ? ["win", "Yours survives, theirs is reversed"]
      : yours === theirs ? ["tie", "Both are reversed"] : ["lose", "Yours is reversed"];
    const side = (card, owner, label, value, extra = "") => `<div class="counter-side">
        <span class="muted small">${label}</span>${cardHtml(card, owner, "battle")}
        <span class="small">${esc(nameOf(card, ""))}</span>
        ${Number.isFinite(value) ? `<span class="counter-power">${esc(value)}</span>` : ""}${extra}</div>`;
    let battle = "";
    if (attacker) {
      const [now, nowText] = battling ? outcome(mine) : [];
      battle = `<div class="counter-battle">
          ${side(attacker, "view", "Attacking", theirs)}
          ${defender ? `<span class="counter-vs" aria-hidden="true">vs</span>
            ${side(defender, "view", "Your defender", mine, attack.backup ? `<span class="muted small">incl. backup +${esc(attack.backup)}</span>` : "")}`
            : `<span class="muted small counter-direct">${attack.kind === "side" ? "Side attack: no battle" : "Direct attack: no defender"}</span>`}
        </div>
        ${battling ? `<p class="small counter-now">Without a counter: <b class="outcome-${now}">${nowText}</b>.</p>` : ""}`;
    }
    const rows = options.map((c) => {
      const backup = ((cards[c.card] || {}).text || "").match(BACKUP_POWER);
      const plus = backup ? Number(backup[1]) : 0;
      let after = "";
      if (plus && battling) {
        const [kind, text] = outcome(mine + plus);
        after = `<span class="counter-after small">${esc(nameOf(defender, "Yours"))}: ${esc(mine)} → <b>${esc(mine + plus)}</b>
          <span class="outcome-${kind}">${text}</span></span>`;
      }
      return `<div class="trigger-option">${cardHtml(c, "me", "counter")}
        ${backup ? `<span class="muted small">Backup +${esc(backup[1])}</span>` : ""}${after}
        <div class="trigger-buttons"><button type="button" data-act='${esc(JSON.stringify({ type: "counter", uid: c.uid }))}'>Counter</button></div>
      </div>`;
    });
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="alertdialog" aria-label="Counter step">
      <div class="play-modal-head"><h2>Counter step</h2></div>
      <p class="muted small">${opponentWho("Your opponent")} is attacking (${esc(attack.soul)} damage). You can play ${options.length === 1 ? "this counter" : "one of these counters"} from your hand.</p>
      ${battle}
      <div class="play-modal-cards">${rows.join("")}</div>
      <div class="trigger-buttons">
        <button type="button" data-act='{"type":"no_counter"}'>No counter</button>
        <button type="button" class="button-cancel" data-counter-hide>Look at the board</button>
      </div>
    </div>`;
  }

  // The encore step, with turn rules on: each reversed character of ours, on either player's turn, is
  // encored (3 stock, stays rested) or goes to the waiting room, here, one at a time. The turn waits for
  // every reversed character on the table (see reversedLeft); anything they trigger is resolved first.
  const myReversed = () => STAGE.map((slot) => [slot, board.me.stage[slot]]).filter(([, c]) => c && c.pos === "reverse");
  const encoreDue = () => board.rules && board.phase === "encore" && !board.ability && !board.ability_show && myReversed().length > 0;

  function renderEncorePrompt() {
    const enough = canEncore();
    const stock = board.me.zones.stock.count;
    const rows = myReversed().map(([slot, card]) => {
      const blocked = (board.no_encore || []).includes(card.uid);
      const why = blocked ? "It can't be encored this turn." : enough ? "" : `Encore needs ${ENCORE_COST} stock; you have ${stock}.`;
      return `<div class="encore-option">${cardHtml(card, "view", "encore")}
        <span class="muted small">${esc(LABELS[slot])}</span>
        <div class="trigger-buttons">
          <button type="button" data-act='${esc(JSON.stringify({ type: "encore", uid: card.uid }))}'${why ? ` disabled title="${esc(why)}"` : ""}>Encore (${ENCORE_COST} stock)</button>
          <button type="button" class="button-cancel" data-act='${esc(JSON.stringify({ type: "move", uid: card.uid, to: "waiting" }))}'>🪦 Waiting room</button>
        </div>
        ${why ? `<span class="muted small">${esc(why)}</span>` : ""}</div>`;
    });
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="alertdialog" aria-label="Encore step">
      <div class="play-modal-head"><h2>Encore step</h2></div>
      <p class="muted small">Your reversed character${rows.length === 1 ? "" : "s"}: pay ${ENCORE_COST} stock to encore (it stays on the stage, rested), or send ${rows.length === 1 ? "it" : "each"} to the waiting room. You have ${stock} stock.</p>
      <div class="play-modal-cards">${rows.join("")}</div>
    </div>`;
  }

  // 7 or more cards in our clock: choose which of the first 7 goes to the level zone (the rest go to
  // the waiting room). This stays up until a card is chosen.
  function renderLevelUp() {
    const first = board.me.zones.clock.slice(0, LEVEL_UP_AT);
    modalEl.hidden = false;
    modalEl.innerHTML = `<div class="play-modal-box" role="dialog" aria-label="Level up">
      <div class="play-modal-head"><h2>Level up to level ${board.me.zones.level.length + 1}</h2></div>
      <p class="muted small">Choose a card from your clock for your level zone. The other ${LEVEL_UP_AT - 1} go to the waiting room.</p>
      <div class="play-modal-cards">${first.map((c) => `<div class="level-pick" role="button" tabindex="0"
        data-level-up="${esc(c.uid)}" aria-label="Level up with this card">${cardHtml(c, "me", "clock")}</div>`).join("")}</div>
    </div>`;
  }

  // A new phase's name (in the side panel, on the board and on the phase bar) comes in with a
  // randomly picked little animation.
  let phaseKey = null;
  let phaseWas = null;

  // The phase that's ending in the middle of the screen, replaced by the new one.
  const PHASE_ICONS = { mulligan: "🔄", stand: "⬆", draw: "🃏", clock: "🕒", main: "🎯", climax: "⚡", attack: "⚔", encore: "♻", end: "🏁" };
  const phaseCard = (phase, which) => `<div class="phase-show-card ${which}"><span class="phase-show-icon" aria-hidden="true">${PHASE_ICONS[phase] || ""}</span>
    <span class="phase-show-name">${cxHtml(PHASES[phase] || phase)}</span><span class="phase-show-word">phase</span></div>`;

  function showPhaseChange(from, to) {
    document.querySelectorAll(".phase-show").forEach((el) => el.remove());
    const el = document.createElement("div");
    el.className = "phase-show";
    el.style.setProperty("--phase-ms", `${PHASE_PAUSE_MS}ms`);
    el.setAttribute("aria-live", "polite");
    el.innerHTML = phaseCard(from, "phase-show-out") + phaseCard(to, "phase-show-in");
    document.body.appendChild(el);
    el.querySelector(".phase-show-in").addEventListener("animationend", () => el.remove());
  }

  function announcePhase() {
    const key = `${board.turn_number}:${board.phase}`;
    if (phaseKey && key !== phaseKey && animations && phaseWas && phaseWas !== board.phase && !board.game_over && !board.rps) {
      showPhaseChange(phaseWas, board.phase);
    }
    phaseWas = board.phase;
    if (phaseKey && key !== phaseKey && animations) {
      const effect = PHASE_NAME_FX[Math.floor(Math.random() * PHASE_NAME_FX.length)];
      const names = [controlsEl.querySelector("[data-turn]"), boardEl.querySelector(".table-turn"),
        controlsEl.querySelector("[data-phase].current")];
      for (const el of names.filter(Boolean)) {
        el.classList.remove(...PHASE_NAME_FX);
        void el.offsetWidth; // restart the animation
        el.classList.add(effect);
        el.addEventListener("animationend", () => el.classList.remove(effect), { once: true });
      }
    }
    phaseKey = key;
  }

  // --- Card preview ----------------------------------------------------------------------------

  // A card's serial, name, stats, traits and text: beside the board, and in the full-screen view.
  function cardTextHtml(info) {
    const stats = [
      info.type, info.rarity, info.color,
      info.level != null ? `Level ${info.level}` : "", info.cost != null ? `Cost ${info.cost}` : "",
      info.power != null ? `Power ${info.power}` : "", info.soul != null ? `Soul ${info.soul}` : "",
      info.trigger ? `Trigger: ${info.trigger}` : "",
    ].filter(Boolean).join(" · ");
    return `<p class="muted small">${esc(info.serial)}</p><p class="play-preview-name">${esc(info.name)}</p>
      <p class="small">${esc(stats)}</p>${info.traits ? `<p class="small muted">${esc(info.traits)}</p>` : ""}
      ${info.text ? `<div class="card-peek-text">${esc(info.text).replace(/\n/g, "<br>")}</div>` : ""}`;
  }

  function showPreview(pk) {
    const info = cards[pk];
    if (!info) return;
    previewEl.innerHTML = `<img src="${esc(info.image)}" alt="">${cardTextHtml(info)}`;
  }

  root.addEventListener("mouseover", (event) => {
    const el = event.target.closest(".pcard[data-card]");
    if (el) showPreview(el.dataset.card);
  });

  // --- Enlarged card art: play_art.js (WeissArt), made here once what it reads is defined ---
  const art = window.WeissArt.create({
    LABELS: () => LABELS,
    SPECTATING: () => SPECTATING,
    STAGE: () => STAGE,
    board: () => board,
    cards: () => cards,
    esc: () => esc,
    root: () => root,
    touch: () => touch,
  });

  // --- Touch screens: play_touch.js (WeissTouch), made here once what it reads is defined ---
  const touchScreen = window.WeissTouch.create({
    LABELS: () => LABELS,
    SPECTATING: () => SPECTATING,
    STAGE: () => STAGE,
    art: () => art,
    board: () => board,
    boardEl: () => boardEl,
    cardTextHtml: (...args) => cardTextHtml(...args),
    cards: () => cards,
    clearDropHints: (...args) => clearDropHints(...args),
    dragUid: () => dragUid,
    esc: () => esc,
    hideMenu: (...args) => menus.hideMenu(...args),
    modalEl: () => modalEl,
    prizeScreen: () => prizeScreen,
    root: () => root,
    selected: () => selected,
    showDropHints: (...args) => showDropHints(...args),
    touch: () => touch,
    setSelected: (value) => { selected = value; },
  });

  // --- Menus: play_menus.js (WeissMenus), made here once what it reads is defined ---
  const menus = window.WeissMenus.create({
    ENCORE_COST: () => ENCORE_COST,
    LABELS: () => LABELS,
    MOVE_TARGETS: () => MOVE_TARGETS,
    PLAY_ZONES: () => PLAY_ZONES,
    PUBLIC_PILES: () => PUBLIC_PILES,
    SPECTATING: () => SPECTATING,
    STAGE: () => STAGE,
    abilityPicks: () => abilityPicks,
    animations: () => animations,
    art: () => art,
    board: () => board,
    boardEl: () => boardEl,
    boardView: () => boardView,
    busy: () => busy,
    canEncore: () => canEncore,
    canPay: () => canPay,
    cards: () => cards,
    closeSummary: (...args) => closeSummary(...args),
    colorMissing: () => colorMissing,
    counterHidden: () => counterHidden,
    counterKey: () => counterKey,
    discardPicks: () => discardPicks,
    esc: () => esc,
    flashPicks: () => flashPicks,
    isMarkerPile: () => isMarkerPile,
    menuEl: () => menuEl,
    modal: () => modal,
    modalEl: () => modalEl,
    movement: () => movement,
    mulliganPicks: () => mulliganPicks,
    musicOn: () => musicOn,
    oppMoved: () => oppMoved,
    peekKey: () => peekKey,
    placePick: () => placePick,
    playTo: (...args) => playTo(...args),
    recap: () => recap,
    render: (...args) => render(...args),
    renderAttackPanel: (...args) => renderAttackPanel(...args),
    renderModal: (...args) => renderModal(...args),
    root: () => root,
    selected: () => selected,
    setAnimations: (...args) => setAnimations(...args),
    setLayout: (...args) => setLayout(...args),
    setMusic: (...args) => setMusic(...args),
    setSound: (...args) => setSound(...args),
    showAugment: (...args) => showAugment(...args),
    shownKey: () => shownKey,
    soundOn: () => soundOn,
    toggleMusicKey: (...args) => toggleMusicKey(...args),
    touch: () => touch,
    touchScreen: () => touchScreen,
    setAbilityPicks: (value) => { abilityPicks = value; },
    setBoardView: (value) => { boardView = value; },
    setCounterHidden: (value) => { counterHidden = value; },
    setModal: (value) => { modal = value; },
    setPeekKey: (value) => { peekKey = value; },
    setPlacePick: (value) => { placePick = value; },
    setSelected: (value) => { selected = value; },
    setOppMoved: (value) => { oppMoved = value; },
  });

  // --- Drag and drop ---------------------------------------------------------------------------

  // Where the rules let a card of ours go right now (with them on; with them off it's anywhere): a hand card to
  // where it can be played (handPlays), a character on the stage to another position in the main phase.
  function dropTargets(uid) {
    if (!board || !board.rules || SPECTATING) return [];
    const inHand = board.me.zones.hand.find((c) => c.uid === uid);
    if (inHand) return handPlays(inHand).to;
    const slot = STAGE.find((s) => board.me.stage[s] && board.me.stage[s].uid === uid);
    return slot && inPhase("main") ? STAGE.filter((s) => s !== slot) : [];
  }

  // The places a card can go, lit up on our side of the board (a stage position with a character on it says what
  // happens to that character); the rest of our stage dims. Cleared once it's dropped, or put down.
  function showDropHints(uid) {
    clearDropHints();
    const targets = dropTargets(uid);
    if (!targets.length) return;
    const fromHand = board.me.zones.hand.some((c) => c.uid === uid);
    root.classList.add("drop-hinting");
    for (const to of targets) {
      const zone = boardEl.querySelector(`.mat-me [data-drop="${to}"]`);
      if (!zone) continue;
      zone.classList.add("drop-hint");
      const here = STAGE.includes(to) ? board.me.stage[to] : null;
      if (here) {
        zone.classList.add("drop-replace");
        zone.insertAdjacentHTML("beforeend", `<span class="drop-note"><b>${fromHand ? "Replaces" : "Swaps with"}</b> <span class="drop-note-name">${esc(stageNameOf(here))}</span></span>`);
      }
    }
  }

  function clearDropHints() {
    root.classList.remove("drop-hinting");
    boardEl.querySelectorAll(".drop-hint").forEach((el) => el.classList.remove("drop-hint", "drop-replace"));
    boardEl.querySelectorAll(".drop-note").forEach((el) => el.remove());
  }

  root.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".pcard[data-uid][draggable]");
    if (SPECTATING) event.preventDefault();
    if (!card || SPECTATING) return;
    event.dataTransfer.setData("text/plain", card.dataset.uid);
    event.dataTransfer.effectAllowed = "move";
    menus.hideMenu();
    dragUid = card.dataset.uid;
    // Painted after the browser has taken its picture of the card being dragged.
    requestAnimationFrame(() => { if (dragUid) showDropHints(dragUid); });
  });
  root.addEventListener("dragend", () => {
    dragUid = null;
    clearDropHints();
  });
  // A redraw mid-drag can take the dragged card away before its dragend: the first move after the drop tidies up.
  root.addEventListener("pointermove", (event) => {
    if (dragUid && event.buttons === 0) {
      dragUid = null;
      clearDropHints();
    }
  });
  root.addEventListener("dragover", (event) => {
    const zone = event.target.closest("[data-drop]");
    if (zone && zone.dataset.drop) {
      event.preventDefault();
      zone.classList.add("drop-over");
    }
  });
  root.addEventListener("dragleave", (event) => {
    const zone = event.target.closest("[data-drop]");
    if (zone) zone.classList.remove("drop-over");
  });
  root.addEventListener("drop", (event) => {
    const zone = event.target.closest("[data-drop]");
    if (!zone || !zone.dataset.drop) return;
    event.preventDefault();
    zone.classList.remove("drop-over");
    clearDropHints();
    dragUid = null;
    const uid = event.dataTransfer.getData("text/plain");
    if (uid) playTo(uid, zone.dataset.drop);
  });

  // A card of ours sent somewhere by dropping or tapping: a climax played in the main phase ends it, so that asks first,
  // as its button does (renderClimaxConfirm).
  function playTo(uid, to) {
    const climax = to === "climax" && board.rules && board.phase === "main" && board.me.zones.hand.some((c) => c.uid === uid && isClimaxCard(c));
    if (climax) {
      modal = { confirmClimax: uid };
      renderModal();
      return;
    }
    movement.act({ type: "move", uid, to });
  }

  // --- Chat ------------------------------------------------------------------------------------

  controlsEl.addEventListener("submit", (event) => {
    if (!event.target.matches("[data-damage]")) return;
    event.preventDefault();
    const count = Number(event.target.elements.count.value);
    if (count >= 1) movement.act({ type: "damage", count });
  });

  // No chat form for a co-op partner watching (play_room.html).
  const chatEl = $("[data-chat]");
  if (chatEl) chatEl.addEventListener("submit", (event) => {
    event.preventDefault();
    const input = event.target.elements.text;
    if (input.value.trim()) movement.act({ type: "chat", text: input.value });
    input.value = "";
  });

  // The volume slider: heard as it moves, saved once it stops.
  root.addEventListener("input", (event) => {
    if (event.target.matches("[data-sound-volume]")) setSoundVolume(Number(event.target.value), true);
    if (event.target.matches("[data-music-volume]")) setMusicVolume(Number(event.target.value), true);
  });
  root.addEventListener("change", (event) => {
    if (event.target.matches("[data-sound-volume]")) playSound("draw");
    if (event.target.matches("[data-song]")) chooseSong(event.target.value);
  });
  // Browsers only let a page make sound after it's been clicked: start the audio on the first click.
  root.addEventListener("pointerdown", () => {
    if (!soundOn) return;
    audioContext();
    syncMusic();
  }, { once: true });

  // The pieces in files of their own (see each one's header), now that all they use is defined. If one didn't load,
  // the board goes on without it.
  fx = window.WeissTableFx ? window.WeissTableFx.create({
    boardEl, cards, STAGE, CLIMAX_SHOW_MS, SPECTATING, reducedMotion, esc, who, outOfSight: prizeScreen.outOfSight, pileCount, musicTheme, atBrink,
    board: () => board, avatars: () => avatars, animations: () => animations, score: () => score, holdGameOver, climaxColor: prizeScreen.climaxColor,
    damageLead: (owner) => battle.damageLead(owner), battleClaim: (id) => battle.battleClaim(id),
  }) : { tableFx() {}, setTableMood() {}, negatedWait: () => 0, noteOwnDamage() {}, climaxSurge() {} };
  if (window.WeissBattle) {
    battle = window.WeissBattle.create({ root, cards, esc, climaxColor: prizeScreen.climaxColor, reducedMotion, SOUL_ICON, board: () => board, animations: () => animations,
      pinnacle: { power: PINNACLE_POWER, aura: pinnacleAura, layers: pinnacleLayers } });
  }
  recap = window.WeissRecap ? window.WeissRecap.create({
    controlsEl, esc, who, logHtml, gameNumber, board: () => board, avatars: () => avatars,
  }) : { render() {}, dismiss() {} };

  movement.pollLoop();
  if (song) syncMusic(); // the chosen song starts with the duel (once a click has unlocked the sound)
  // Back from another tab or app (a phone woken up): catch up at once rather than on the next tick. While
  // the page is hidden its sound is paused (the music too, mid-bar, to carry on where it was).
  document.addEventListener("visibilitychange", () => {
    if (audio) {
      if (document.hidden) audio.suspend().catch(() => {});
      else if (soundOn) audio.resume().catch(() => {});
    }
    if (!document.hidden) movement.wakePoll(); // back in view: ask now rather than at the end of the pause
  });
  // Leaving the duel: the chosen song stops with the page (its own context goes with it, but say so now).
  window.addEventListener("pagehide", () => { if (window.MinigameAudio) window.MinigameAudio.stop(); });
})();
