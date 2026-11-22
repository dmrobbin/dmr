"""Render the CC0 hip hop loop (cc0_5): a boom-bap groove, two bars at 90 bpm, from the Gogodze Phu Vol II kit (CC0-1.0).

Kick: ks, snare: ss, closed hat: hc, open hat: ho (front mic). Run: python e2e/render_hiphop.py
"""
import glob
import pathlib
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parent.parent
KITS = ROOT / "e2e" / "scratch" / "cc0" / "Gogodze_Phu_II" / "Gogodze_Phu_vol_II" / "Samples"
OUT = ROOT / "weiss" / "static" / "weiss" / "sounds" / "music" / "cc0"
SR = 44100
BPM = 90
STEP = int(round(SR * 60 / BPM / 4))  # a sixteenth
STEPS = 32  # two bars
LOOP = STEPS * STEP


def load(pattern):
    found = sorted(glob.glob(str(KITS / "**" / pattern), recursive=True))
    assert found, f"no file matches {pattern}"
    data, rate = sf.read(found[0], dtype="float32")
    assert rate == SR, found[0]
    return data.mean(axis=1) if data.ndim > 1 else data


def place(buffer, sample, start, gain):
    index = (start + np.arange(len(sample))) % len(buffer)  # wraps, so the loop is seamless
    np.add.at(buffer, index, gain * sample)


kick = load("ks_vl3_rr1.wav")
snare = load("ss_vl4_rr1.wav")
ghost = load("ss_vl1_rr1.wav")
hat = load("hc_vl2_rr1.wav")
open_hat = load("ho_vl2_rr1.wav")

buffer = np.zeros(LOOP, dtype=np.float32)
# Kick: on 1, the and of 2, the 'a' of 3, and the and of 4; the second bar varies on the 'a' of 4.
for step in (0, 6, 8, 14, 16, 22, 24, 30):
    place(buffer, kick, step * STEP, 0.9 if step % 16 == 0 else 0.75)
# Snare: on 2 and 4 of each bar, with a ghost before the 4 in the second bar.
for step in (4, 12, 20, 28):
    place(buffer, snare, step * STEP, 0.7)
place(buffer, ghost, 27 * STEP, 0.2)
# Hats: sixteenths, the off-sixteenths quieter, with the open hat on the and of 4 in bar two.
for step in range(STEPS):
    place(buffer, hat, step * STEP, 0.22 if step % 2 else 0.3)
place(buffer, open_hat, 30 * STEP, 0.25)

buffer *= 0.89 / np.max(np.abs(buffer))  # about -1 dBFS, as the other loops
OUT.mkdir(parents=True, exist_ok=True)
path = OUT / "cc0_5.wav"
sf.write(path, buffer, SR, subtype="PCM_16")
print(f"cc0_5 (hip hop): {BPM} bpm, {LOOP / SR:.2f} s, {path}")
