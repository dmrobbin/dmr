"""Render the stems and kit sounds for the CC0 tracks.

Stems: cc0_N_drums.wav, cc0_N_bass.wav and cc0_N_melody.wav beside each loop, the same length as the loop, so they line up.
A part a track doesn't have is silent. Kit sounds (music/cc0/kit/): hit, block, play, win, lose, draw and damage.
Run: python e2e/render_stems.py
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


def bank(paths, pattern):
    out = {}
    for path in paths:
        found = re.match(pattern, pathlib.Path(path).name)
        if found:
            out.setdefault(midi(found.group(1)), path)
    return out


def note(b, target, gain):
    source = min(b, key=lambda n: abs(n - target))
    data = load(b[source])
    ratio = 2 ** ((target - source) / 12)
    positions = np.linspace(0, len(data) - 1, int(len(data) / ratio))
    return np.interp(positions, np.arange(len(data)), data).astype(np.float32) * gain


def place(buffer, sample, start, gain):
    index = (start + np.arange(len(sample))) % len(buffer)  # wraps, so the loop is seamless
    np.add.at(buffer, index, gain * sample)


def scaled(buffer, peak):
    return buffer * (peak / max(float(np.max(np.abs(buffer))), 1e-9))


def step_len(bpm):
    return int(round(SR * 60 / bpm / 4))


def make(name, bpm, build):
    """build(drums, bass, melody, step) fills the three parts for a 32-step (two-bar) loop."""
    step = step_len(bpm)
    length = 32 * step
    drums, bass, melody = (np.zeros(length, dtype=np.float32) for _ in range(3))
    build(drums, bass, melody, step)
    for part, buf in (("drums", drums), ("bass", bass), ("melody", melody)):
        if np.any(buf):
            buf = scaled(buf, 0.89)
        sf.write(OUT / f"{name}_{part}.wav", buf.astype(np.float32), SR, subtype="PCM_16")
    print(f"{name}: stems written ({length / SR:.2f} s)")


KICK_BR = find("k_vl3_rr1.flac")
SNARE_FR = find("14a_basic/btm/sn_vl10_rr1.flac")
HAT_SW = find("hh_closed_vl10_rr1.wav")
OPEN_SW = find("hh_open_vl10_rr1.wav")
CRASH_SW = find("Swirly_Drums_1104/Samples/crash/*rr1.wav")
RIDE_SW = find("Swirly_Drums_1104/Samples/ride/*rr1.wav")
COWBELL = find("cowbell*rr1.wav")
GK, GS, GH = find("ks_vl3_rr1.wav"), find("ss_vl4_rr1.wav"), find("hc_vl2_rr1.wav")
BRUSH = find("14d_brush/btm/sb_vl1_rr1.flac")

DB = bank(glob.glob(str(SCRATCH / "DSmolken_double_bass" / "**" / "pizz_*_m*.wav"), recursive=True), r"pizz_([a-g]b?\d)_")
VIO = bank(glob.glob(str(SCRATCH / "Caveman_Cosmonaut" / "**" / "violin_*.wav"), recursive=True), r"violin_([a-g]b?\d)\.wav")


def hits(buffer, path, steps, step, gain):
    sample = load(path)
    for s in steps:
        place(buffer, sample, s * step, gain)


# cc0_1 to cc0_3, cc0_5: drum loops (drums stem only)
def rock(bpm, parts):
    def build(drums, bass, melody, step):
        for path, steps, gain in parts(step):
            hits(drums, path, steps, step, gain)
    return build


make("cc0_1", 118, rock(118, lambda s: [(KICK_BR, [0, 8, 16, 24], 0.9), (SNARE_FR, [4, 12, 20, 28], 0.7),
                                         (HAT_SW, list(range(0, 32, 2)), 0.35), (OPEN_SW, [6, 22], 0.3),
                                         (CRASH_SW, [0], 0.3)]))
make("cc0_2", 84, rock(84, lambda s: [(KICK_BR, [0, 18], 0.9), (SNARE_FR, [8, 24], 0.7),
                                       (HAT_SW, [0, 4, 12, 16, 20, 28], 0.35), (OPEN_SW, [30], 0.3),
                                       (CRASH_SW, [0, 16], 0.3)]))
make("cc0_3", 160, rock(160, lambda s: [(KICK_BR, list(range(0, 32, 2)), 0.9), (SNARE_FR, [4, 12, 20, 28], 0.7),
                                         (HAT_SW, list(range(32)), 0.35)]))
make("cc0_5", 90, rock(90, lambda s: [(GK, [0, 6, 8, 14, 16, 22, 24, 30], 0.9), (GS, [4, 12, 20, 28], 0.7),
                                       (GH, list(range(32)), 0.3)]))


def jazz(drums, bass, melody, step):
    beat = step * 4
    for i, n in enumerate(["d2", "f2", "a2", "c3", "g1", "b1", "d2", "db2"]):
        place(bass, note(DB, midi(n), 0.8), i * beat, 1.0)
    ride = load(RIDE_SW)
    for b in range(8):
        place(drums, ride, b * beat, 0.25 if b % 2 else 0.35)
    brush = load(BRUSH)
    for b in (1, 5):
        place(drums, brush, b * beat, 0.5)
    kick = load(KICK_BR)
    for b in (0, 4):
        place(drums, kick, b * beat, 0.35)


make("cc0_4", 120, jazz)


def funk(drums, bass, melody, step):
    riff = [(0, "e2"), (3, "e2"), (6, "g2"), (7, "e2"), (10, "a2"), (12, "b2"), (14, "d3"), (15, "b2"),
            (16, "e2"), (19, "e2"), (22, "g2"), (23, "e2"), (26, "a2"), (28, "b2"), (30, "d3"), (31, "b2")]
    for s, n in riff:
        place(bass, note(DB, midi(n), 0.75), s * step, 1.0)
    for s in (0, 10, 16, 26):
        place(drums, load(GK), s * step, 0.8)
    for s in (4, 12, 20, 28):
        place(drums, load(GS), s * step, 0.65)
    for s in range(0, 32, 2):
        place(drums, load(GH), s * step, 0.2 if s % 4 else 0.3)
    for s in (2, 14, 18, 30):
        place(drums, load(COWBELL), s * step, 0.25)


make("cc0_6", 100, funk)


def emo(drums, bass, melody, step):
    for s, n in [(0, "a4"), (4, "c5"), (8, "e5"), (12, "d5"), (16, "c5"), (20, "a4"), (24, "g4"), (28, "a4")]:
        place(melody, note(VIO, midi(n), 0.55), s * step, 1.0)
    for s, n in [(0, "a2"), (8, "f2"), (16, "c2"), (24, "e2")]:
        place(bass, note(DB, midi(n), 0.7), s * step, 0.9)
    for s in (0, 16):
        place(drums, load(KICK_BR), s * step, 0.7)
    for s in (8, 24):
        place(drums, load(SNARE_FR), s * step, 0.6)
    for s in range(0, 32, 2):
        place(drums, load(HAT_SW), s * step, 0.2)


make("cc0_7", 130, emo)


def metal(drums, bass, melody, step):
    riff = [(0, "e1"), (2, "e1"), (4, "e1"), (6, "g1"), (8, "e1"), (10, "e1"), (12, "e1"), (14, "b1"),
            (16, "e1"), (18, "e1"), (20, "e1"), (22, "g1"), (24, "e1"), (26, "e1"), (28, "eb1"), (30, "b1")]
    for s, n in riff:
        place(bass, note(DB, midi(n), 0.8), s * step, 1.0)
    for s in range(0, 32, 2):
        place(drums, load(KICK_BR), s * step, 0.55)
    for s in (4, 12, 20, 28):
        place(drums, load(SNARE_FR), s * step, 0.6)
    for s in range(32):
        place(drums, load(HAT_SW), s * step, 0.12)


make("cc0_8", 160, metal)

# The kit sounds for the sound-effect banks: one sample each, up to 1.5 seconds.
KIT = OUT / "kit"
KIT.mkdir(parents=True, exist_ok=True)
for name, source in {"hit": SNARE_FR, "block": HAT_SW, "play": HAT_SW, "win": CRASH_SW, "lose": KICK_BR,
                     "draw": COWBELL, "damage": KICK_BR}.items():
    data = load(source)
    sf.write(KIT / f"{name}.wav", scaled(data[: int(SR * 1.5)], 0.7), SR, subtype="PCM_16")
    print(f"kit {name}: written")
