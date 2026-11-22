"""Render the CC0 songs in layers, for the duel music (docs/duel-music-plan.md, version 2).

Each song is four bars, written on a sixteenth-note grid, and rendered as nine layers: core, top, bass, chords, lead,
extra, drive and climax (loops, all the same length) and splash (a one-bar one-shot). The engine (audio.js) turns layers
on by tier. All layers share one gain structure and are scaled together, so a layer sounds the same on its own as it
does in the full mix. Also written: cc0_N.wav, the full loop at tier 6 without the climax (the engine's fallback).

Run: python e2e/music/songs.py [key ...]   (no keys: every song)
"""
import pathlib
import sys

import numpy as np
import scipy.signal as signal
import soundfile as sf

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from instruments import SR, drum, midi, note  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "weiss" / "static" / "weiss" / "sounds" / "music" / "cc0"
LOOP_LAYERS = ["core", "top", "bass", "chords", "lead", "extra", "drive", "climax", "tension"]
FULL_MIX = ["core", "top", "bass", "chords", "lead", "extra", "drive"]  # tier 6, without the climax or match point
SPLASH_TAIL = 1.5  # seconds a splash may ring past its bar
# Each layer's loudness (dB RMS, relative to the others; the whole song is scaled afterwards). The backbeat and bass lead;
# each added part sits a few dB under them, loud enough to be heard coming in, not so loud it swamps the rest.
# Each later part joins a fuller mix, so it sits higher: each comes in about 3 to 5 dB under the mix it joins, which is
# clearly heard (measured with the tier check in e2e/music/check_tiers.py).
LAYER_LOUDNESS = {"core": -18, "top": -21, "bass": -19, "chords": -19, "lead": -17, "extra": -16.5, "drive": -15.5,
                  "climax": -12.5, "tension": -15}
SONG_LOUDNESS = -20  # every song's tier-5 mix at the same loudness (dBFS RMS), unless its peaks need it quieter
SPLASH_LOUDNESS = -18


def notes(names):
    """'E2 B2 E3' -> [40, 47, 52]."""
    return [midi(n) for n in names.split()]


class Song:
    def __init__(self, key, name, bpm, bars=4, swing8=0.0, swing16=0.0, seed=7):
        self.key, self.name, self.bpm = key, name, bpm
        self.step = SR * 60 / bpm / 4  # a sixteenth, in samples (fractional)
        self.steps = bars * 16
        self.length = int(round(self.steps * self.step))
        self.layers = {name: np.zeros(self.length, dtype=np.float32) for name in LOOP_LAYERS}
        self.splash = np.zeros(int(round(16 * self.step + SR * SPLASH_TAIL)), dtype=np.float32)
        self.swing8, self.swing16 = swing8, swing16
        self.rng = np.random.default_rng(seed)

    # ---- placing sound

    def position(self, step):
        """A step's start in samples: swing delays the off-beats, and a little random timing keeps it human."""
        offset = 0.0
        whole = int(step)
        if self.swing8 and whole % 4 == 2:
            offset += self.swing8 * self.step
        if self.swing16 and whole % 2 == 1:
            offset += self.swing16 * self.step
        return step * self.step + offset + self.rng.normal(0, 0.002 * SR)

    def _put(self, target, sample, start, gain, loop):
        start = int(round(start))
        if loop:
            index = (start + np.arange(len(sample))) % len(target)  # wraps: the loop is seamless
            np.add.at(target, index, gain * sample)
        else:
            start = max(0, start)  # a one-shot can't start before its own beginning
            end = min(len(target), start + len(sample))
            if start < len(target):
                target[start:end] += gain * sample[: end - start]

    def _cut(self, sample, steps):
        """A note held for `steps` sixteenths, with a 40 ms release so it doesn't click."""
        if steps is None:
            return sample
        length = min(len(sample), int(steps * self.step))
        cut = sample[:length].copy()
        fade = min(int(0.04 * SR), length)
        cut[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        return cut

    def _human(self, gain):
        return gain * float(np.clip(1 + self.rng.normal(0, 0.06), 0.8, 1.2))

    def hit(self, layer, name, step, gain=1.0):
        target, loop = (self.splash, False) if layer == "splash" else (self.layers[layer], True)
        self._put(target, drum(name), self.position(step), self._human(gain), loop)

    def play(self, layer, instrument, pitches, step, steps=None, gain=1.0, strum=0.0):
        """One note or a chord (a list of pitches); strum spreads a chord's notes by that many milliseconds each."""
        target, loop = (self.splash, False) if layer == "splash" else (self.layers[layer], True)
        pitches = [pitches] if isinstance(pitches, int) else pitches
        for i, pitch in enumerate(pitches):
            sample = self._cut(note(instrument, pitch), steps)
            start = self.position(step) + i * strum * SR / 1000
            self._put(target, sample, start, self._human(gain) / max(1, len(pitches)) ** 0.5, loop)

    def swell(self, layer, instrument, pitches, step, steps, gain=1.0):
        """Held notes that rise from quiet to full over `steps` sixteenths: a crescendo."""
        target = self.layers[layer]
        length = int(steps * self.step)
        ramp = np.linspace(0.15, 1.0, length, dtype=np.float32) ** 2
        for pitch in ([pitches] if isinstance(pitches, int) else pitches):
            sample = note(instrument, pitch)
            if len(sample) < length:  # a short recording: hold it by looping its middle
                middle = sample[len(sample) // 4: 3 * len(sample) // 4]
                sample = np.concatenate([sample] + [middle] * (length // max(1, len(middle)) + 1))
            held = sample[:length] * ramp
            fade = int(0.05 * SR)
            held[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
            self._put(target, held, self.position(step), gain / max(1, len(pitches) if isinstance(pitches, list) else 1) ** 0.5, True)

    def heartbeat(self, layer, gain=0.8):
        """Match point's pulse: two kicks close together, once a bar, like a heartbeat."""
        for bar in range(self.steps // 16):
            self.hit(layer, "kick", 16 * bar, gain)
            self.hit(layer, "kick", 16 * bar + 2, gain * 0.7)

    # ---- effects (applied to a whole layer; loop layers are filtered as a loop, so the seam stays clean)

    def _looped(self, layer, fn):
        buf = self.layers[layer]
        tiled = np.concatenate([buf, buf, buf])
        self.layers[layer] = fn(tiled)[len(buf): 2 * len(buf)].astype(np.float32)

    def lowpass(self, layer, cutoff):
        sos = signal.butter(2, cutoff, "lowpass", fs=SR, output="sos")
        if layer == "splash":
            self.splash = signal.sosfilt(sos, self.splash).astype(np.float32)
        else:
            self._looped(layer, lambda x: signal.sosfiltfilt(sos, x))

    def highpass(self, layer, cutoff):
        sos = signal.butter(2, cutoff, "highpass", fs=SR, output="sos")
        self._looped(layer, lambda x: signal.sosfiltfilt(sos, x))

    def drive(self, layer, amount):
        """A soft clip: grit for guitars and bass."""
        def clip(x):
            peak = np.max(np.abs(x)) or 1.0
            return np.tanh(amount * x / peak) / np.tanh(amount) * peak
        if layer == "splash":
            self.splash = clip(self.splash).astype(np.float32)
        else:
            self.layers[layer] = clip(self.layers[layer]).astype(np.float32)

    def reverb(self, layer, seconds=1.4, mix=0.25):
        """A simple room: exponentially decaying noise, convolved around the loop (circular, so the tail wraps)."""
        n = int(SR * seconds)
        rng = np.random.default_rng(11)
        ir = rng.normal(0, 1, n) * np.exp(-6.0 * np.arange(n) / n)
        ir = signal.sosfilt(signal.butter(2, 5000, "lowpass", fs=SR, output="sos"), ir)
        ir /= np.sqrt(np.sum(ir ** 2))
        if layer == "splash":
            wet = signal.fftconvolve(self.splash, ir)[: len(self.splash)]
            self.splash = ((1 - mix) * self.splash + mix * wet).astype(np.float32)
            return
        buf = self.layers[layer]
        size = len(buf)
        conv = signal.fftconvolve(buf, ir)
        wet = conv[:size].copy()
        for start in range(size, len(conv), size):  # the tail past the loop's end wraps onto its start
            chunk = conv[start: start + size]
            wet[: len(chunk)] += chunk
        self.layers[layer] = ((1 - mix) * buf + mix * wet).astype(np.float32)

    # ---- writing

    def balance(self):
        """Set each layer to its role's loudness (RMS, relative), so every tier's new part is clearly heard. The
        splash is matched to the core, so a stinger lands as hard as the backbeat."""
        for name, target in LAYER_LOUDNESS.items():
            buf = self.layers[name]
            rms = float(np.sqrt(np.mean(buf ** 2)))
            if rms > 1e-9:
                self.layers[name] = (buf * (10 ** (target / 20) / rms)).astype(np.float32)
        splash_rms = float(np.sqrt(np.mean(self.splash[: int(16 * self.step)] ** 2)))
        if splash_rms > 1e-9:
            self.splash = (self.splash * (10 ** (SPLASH_LOUDNESS / 20) / splash_rms)).astype(np.float32)

    def write(self):
        self.balance()
        full = sum(self.layers[name] for name in LOOP_LAYERS)  # everything at once, the climax included
        peak = max(float(np.max(np.abs(full))), 1e-9)
        tier5 = sum(self.layers[name] for name in FULL_MIX)
        tier5_rms = max(float(np.sqrt(np.mean(tier5 ** 2))), 1e-9)
        # The same loudness for every song, but the loudest moment (everything and the climax) no higher than -1 dBFS.
        scale = min(10 ** (SONG_LOUDNESS / 20) / tier5_rms, 0.89 / peak)
        OUT.mkdir(parents=True, exist_ok=True)
        for name in LOOP_LAYERS:
            sf.write(OUT / f"{self.key}_{name}.wav", np.clip(self.layers[name] * scale, -1, 1), SR, subtype="PCM_16")
        sf.write(OUT / f"{self.key}_splash.wav", np.clip(self.splash * scale, -1, 1), SR, subtype="PCM_16")
        tier6 = sum(self.layers[name] for name in FULL_MIX) * scale
        sf.write(OUT / f"{self.key}.wav", np.clip(tier6, -1, 1), SR, subtype="PCM_16")
        rms = {name: 20 * np.log10(max(float(np.sqrt(np.mean((self.layers[name] * scale) ** 2))), 1e-9))
               for name in LOOP_LAYERS}
        print(f"{self.key} ({self.name}): {self.bpm} bpm, {self.length / SR:.2f} s; layer loudness (dBFS RMS): "
              + ", ".join(f"{k} {v:.0f}" for k, v in rms.items()))


def bars(chords):
    """Repeat a per-bar list across the song's four bars (a list of four is used as is)."""
    return [chords[i % len(chords)] for i in range(4)]
