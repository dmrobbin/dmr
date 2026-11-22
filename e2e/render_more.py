"""Render three more CC0 loops: cc0_6 funk, cc0_7 emo, cc0_8 metal. All from CC0-1.0 kits:

- Double bass (DSmolken): plucked notes for the funk and metal bass lines, the violin melody for emo.
- Caveman Cosmonaut (Karoryfer): violin samples for the emo melody, named by note and octave.
- Big Rusty (kick), Frankensnare (snare), Gogodze Phu II (kick, snare, hats), Swirly (hats, ride, crash, cowbell).

Run: python e2e/render_more.py
"""
import glob
import pathlib
import re
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "e2e" / "scratch" / "cc0"
OUT = ROOT / "weiss" / "static" / "weiss" / "sounds" / "music" / "cc0"
SR = 44100


def find(pattern):
    found = sorted(glob.glob(str(SCRATCH / "**" / pattern), recursive=True))
    assert found, f"no file matches {pattern}"
    return found[0]


def load(path):
    data, rate = sf.read(path, dtype="float32")
    assert rate == SR, path
    return data.mean(axis=1) if data.ndim > 1 else data


def midi(name):
    m = re.fullmatch(r"([a-g])(b?)(\d)", name)
    base = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}[m.group(1)]
    return (int(m.group(3)) + 1) * 12 + base - (1 if m.group(2) else 0)


def pitched_bank(paths, pattern):
    """{midi: file} for files named like pattern (its first group is the note)."""
    bank = {}
    for path in paths:
        found = re.match(pattern, pathlib.Path(path).name)
        if found:
            bank.setdefault(midi(found.group(1)), path)
    return bank


def note(bank, target, gain=0.9):
    source = min(bank, key=lambda n: abs(n - target))
    data = load(bank[source])
    ratio = 2 ** ((target - source) / 12)
    positions = np.linspace(0, len(data) - 1, int(len(data) / ratio))
    return np.interp(positions, np.arange(len(data)), data).astype(np.float32) * gain


def place(buffer, sample, start, gain):
    index = (start + np.arange(len(sample))) % len(buffer)  # wraps, so the loop is seamless
    np.add.at(buffer, index, gain * sample)


def finish(buffer):
    return buffer * (0.89 / np.max(np.abs(buffer)))  # about -1 dBFS, as the others


def save(name, buffer, bpm, label):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.wav"
    sf.write(path, finish(buffer), SR, subtype="PCM_16")
    print(f"{name} ({label}): {bpm} bpm, {len(buffer) / SR:.2f} s, {path}")


DOUBLE_BASS = glob.glob(str(SCRATCH / "DSmolken_double_bass" / "**" / "pizz_*_m*.wav"), recursive=True)
BASS = pitched_bank(DOUBLE_BASS, r"pizz_([a-g]b?\d)_")
VIOLIN = pitched_bank(glob.glob(str(SCRATCH / "Caveman_Cosmonaut" / "**" / "violin_*.wav"), recursive=True),
                      r"violin_([a-g]b?\d)\.wav")

# cc0_6 funk, 100 bpm: a syncopated sixteenth-note bass in E minor, kick and snare on 2 and 4, a cowbell and sixteenth hats.
STEP = int(round(SR * 60 / 100 / 4))
funk = np.zeros(32 * STEP, dtype=np.float32)
bass_riff = [(0, "e2"), (3, "e2"), (6, "g2"), (7, "e2"), (10, "a2"), (12, "b2"), (14, "d3"), (15, "b2"),
             (16, "e2"), (19, "e2"), (22, "g2"), (23, "e2"), (26, "a2"), (28, "b2"), (30, "d3"), (31, "b2")]
for step, name in bass_riff:
    place(funk, note(BASS, midi(name), 0.75), step * STEP, 1.0)
kick_g = load(find("ks_vl3_rr1.wav"))
snare_g = load(find("ss_vl4_rr1.wav"))
hat_g = load(find("hc_vl2_rr1.wav"))
cowbell = load(find("cowbell*rr1.wav"))
for step in (0, 10, 16, 26):
    place(funk, kick_g, step * STEP, 0.8)
for step in (4, 12, 20, 28):
    place(funk, snare_g, step * STEP, 0.65)
for step in range(0, 32, 2):
    place(funk, hat_g, step * STEP, 0.2 if step % 4 else 0.3)
for step in (2, 14, 18, 30):
    place(funk, cowbell, step * STEP, 0.25)
save("cc0_6", funk, 100, "funk")

# cc0_7 emo, 130 bpm: a violin melody over a minor chord loop, a half-time beat (snare on 3), eighth hats, a double bass root.
STEP = int(round(SR * 60 / 130 / 4))
emo = np.zeros(32 * STEP, dtype=np.float32)
melody = [(0, "a4"), (4, "c5"), (8, "e5"), (12, "d5"), (16, "c5"), (20, "a4"), (24, "g4"), (28, "a4")]
for step, name in melody:
    place(emo, note(VIOLIN, midi(name), 0.55), step * STEP, 1.0)
roots = [(0, "a2"), (8, "f2"), (16, "c2"), (24, "e2")]
for step, name in roots:
    place(emo, note(BASS, midi(name), 0.7), step * STEP, 0.9)
kick_b = load(find("k_vl3_rr1.flac", ))
snare_c = load(find("sn_vl10_rr1.flac"))
hat_s = load(find("hh_closed_vl10_rr1.wav"))
for step in (0, 16):
    place(emo, kick_b, step * STEP, 0.7)
for step in (8, 24):
    place(emo, snare_c, step * STEP, 0.6)
for step in range(0, 32, 2):
    place(emo, hat_s, step * STEP, 0.2)
save("cc0_7", emo, 130, "emo")

# cc0_8 metal, 160 bpm: a driving low riff in E, distorted with a hard clip, a fast kick on every eighth, snare on 2 and 4,
# a crash at the top of each bar, and sixteenth hats.
STEP = int(round(SR * 60 / 160 / 4))
metal = np.zeros(32 * STEP, dtype=np.float32)
riff = [(0, "e1"), (2, "e1"), (4, "e1"), (6, "g1"), (8, "e1"), (10, "e1"), (12, "e1"), (14, "b1"),
        (16, "e1"), (18, "e1"), (20, "e1"), (22, "g1"), (24, "e1"), (26, "e1"), (28, "eb1"), (30, "b1")]
for step, name in riff:
    place(metal, note(BASS, midi(name), 0.8), step * STEP, 1.0)
for step in range(0, 32, 2):
    place(metal, kick_b, step * STEP, 0.55)
for step in (4, 12, 20, 28):
    place(metal, snare_c, step * STEP, 0.6)
for step in range(32):
    place(metal, hat_s, step * STEP, 0.12)
metal = np.tanh(metal * 3.0) / np.tanh(3.0)  # the hard clip: the riff's grit
save("cc0_8", metal, 160, "metal")
