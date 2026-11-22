"""Render the CC0 jazz loop (cc0_4): a walking double bass over ride and brushes, two bars at 120 bpm.

Sources (CC0-1.0): the DSmolken double bass (plucked notes, pitch-shifted to the chord tones), Swirly Drums (ride), and
Frankensnare (brush snare). Kick from Big Rusty Drums. Run: python e2e/render_jazz.py
"""
import glob
import pathlib
import re
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parent.parent
KITS = ROOT / "e2e" / "scratch" / "cc0"
OUT = ROOT / "weiss" / "static" / "weiss" / "sounds" / "music" / "cc0"
SR = 44100
BPM = 120
BEAT = int(round(SR * 60 / BPM))
LOOP = 8 * BEAT  # two bars of four beats


def load(pattern):
    found = sorted(glob.glob(str(KITS / pattern), recursive=True))
    assert found, f"no file matches {pattern}"
    data, rate = sf.read(found[0], dtype="float32")
    assert rate == SR, found[0]
    return data.mean(axis=1) if data.ndim > 1 else data


def midi(name):
    """'bb1' -> 34 (B-flat 1), 'eb1' -> 27, 'a2' -> 45."""
    m = re.fullmatch(r"([a-g])(b?)(\d)", name)
    base = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[m.group(1)]
    return (int(m.group(3)) + 1) * 12 + base - (1 if m.group(2) else 0)


# The plucked samples: midi note -> file (mezzo-forte, one per note)
PIZZ = {}
for path in glob.glob(str(KITS / "DSmolken_double_bass" / "**" / "pizz_*_m*.wav"), recursive=True):
    name = pathlib.Path(path).name
    found = re.match(r"pizz_([a-g]b?\d)_", name)
    if found:  # skips the noise samples that share the pattern
        PIZZ.setdefault(midi(found.group(1)), path)


def bass_note(target):
    """The nearest plucked sample, shifted to the target pitch."""
    source = min(PIZZ, key=lambda n: abs(n - target))
    data, rate = sf.read(PIZZ[source], dtype="float32")
    data = data.mean(axis=1) if data.ndim > 1 else data
    ratio = 2 ** ((target - source) / 12)
    new_length = int(len(data) / ratio)
    positions = np.linspace(0, len(data) - 1, new_length)
    return np.interp(positions, np.arange(len(data)), data).astype(np.float32) * 0.9


def place(buffer, sample, start, gain):
    index = (start + np.arange(len(sample))) % len(buffer)  # wraps, so the loop is seamless
    np.add.at(buffer, index, gain * sample)


ride = load("Swirly_Drums_1104/Samples/ride/*rr1.wav")
brush = load("Frankensnare_2100/Samples/14d_brush/btm/sb_vl1_rr1.flac")
kick = load("Big_Rusty_Drums_1100/Samples/kick_24/kick/kick/k_vl3_rr1.flac")

# Walking line: chord tones, one per beat. Dm7 (bar 1) then G7 (bar 2), as a ii-V.
LINE = [midi(n) for n in ["d2", "f2", "a2", "c3", "g1", "b1", "d2", "db2"]]

buffer = np.zeros(LOOP, dtype=np.float32)
for i, note in enumerate(LINE):
    place(buffer, bass_note(note), i * BEAT, 0.8)
for beat in range(8):  # the ride on each beat, a touch softer on the off-beats
    place(buffer, ride, beat * BEAT, 0.25 if beat % 2 else 0.35)
for beat in (1, 5):  # brushes on 2 and 4 of each bar
    place(buffer, brush, beat * BEAT, 0.5)
for beat in (0, 4):  # a soft kick on 1 of each bar
    place(buffer, kick, beat * BEAT, 0.35)

buffer *= 0.89 / np.max(np.abs(buffer))  # about -1 dBFS, as the other loops
OUT.mkdir(parents=True, exist_ok=True)
path = OUT / "cc0_4.wav"
sf.write(path, buffer, SR, subtype="PCM_16")
print(f"cc0_4 (jazz): {BPM} bpm, {LOOP / SR:.2f} s, {path}")
