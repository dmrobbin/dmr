"""Render the CC0 drum loops: 2-bar, 16 steps a bar, from one hit per drum in the Karoryfer CC0 kits.

Sources (CC0-1.0, from the kits' GitHub releases): Big Rusty Drums (kick), Frankensnare (snare), Swirly Drums (hats,
crash). Output: weiss/static/weiss/sounds/music/cc0/cc0_1..3.wav, 44.1 kHz mono, 16-bit. Run: python e2e/render_cc0.py
"""
import glob
import pathlib
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parent.parent
KITS = ROOT / "e2e" / "scratch" / "cc0"
OUT = ROOT / "weiss" / "static" / "weiss" / "sounds" / "music" / "cc0"
SR = 44100
STEPS = 32  # two bars of sixteenths


def hit(pattern):
    found = sorted(glob.glob(str(KITS / pattern)))
    assert found, f"no file matches {pattern}"
    data, rate = sf.read(found[0], dtype="float32")
    assert rate == SR, (found[0], rate)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data


SAMPLES = {
    "kick": (hit("Big_Rusty_Drums_1100/Samples/kick_24/kick/kick/k_vl8_rr1.flac"), 0.9),
    "snare": (hit("Frankensnare_2100/Samples/14a_basic/btm/sn_vl10_rr1.flac"), 0.7),
    "hat": (hit("Swirly_Drums_1104/Samples/hat_closed/hh_closed_vl10_rr1.wav"), 0.35),
    "open": (hit("Swirly_Drums_1104/Samples/hat_open/hh_open_vl10_rr1.wav"), 0.3),
    "crash": (hit("Swirly_Drums_1104/Samples/crash/*vl8_rr1.wav") if glob.glob(str(KITS / "Swirly_Drums_1104/Samples/crash/*vl8_rr1.wav"))
              else hit("Swirly_Drums_1104/Samples/crash/*rr1.wav"), 0.3),
}


def render(bpm, pattern):
    """pattern: {drum: [steps]}. Hits wrap around the loop, so the loop is seamless."""
    step = int(round(SR * 60 / bpm / 4))
    length = STEPS * step
    buffer = np.zeros(length, dtype=np.float32)
    for drum, steps in pattern.items():
        sample, gain = SAMPLES[drum]
        for s in steps:
            start = (s % STEPS) * step
            index = (start + np.arange(len(sample))) % length  # wraps past the end of the loop
            np.add.at(buffer, index, gain * sample)
    peak = np.max(np.abs(buffer))
    return buffer * (0.89 / peak)  # about -1 dBFS


LOOPS = {
    # 118 bpm straight rock: kick on 1 and 3, snare on 2 and 4, eighth hats, an open hat on the and of 2.
    "cc0_1": (118, {"kick": [0, 8, 16, 24], "snare": [4, 12, 20, 28],
                    "hat": list(range(0, STEPS, 2)), "open": [6, 22], "crash": [0]}),
    # 84 bpm half-time: a slow kick on 1 and the and of 3, snare on 3 only, quarter hats, a crash at each bar.
    "cc0_2": (84, {"kick": [0, 18], "snare": [8, 24], "hat": [0, 4, 12, 16, 20, 28],
                   "open": [30], "crash": [0, 16]}),
    # 160 bpm fast punk: kick on every eighth, snare on 2 and 4, sixteenth hats.
    "cc0_3": (160, {"kick": list(range(0, STEPS, 2)), "snare": [4, 12, 20, 28],
                    "hat": list(range(STEPS))}),
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (bpm, pattern) in LOOPS.items():
        audio = render(bpm, pattern)
        path = OUT / f"{name}.wav"
        sf.write(path, audio, SR, subtype="PCM_16")
        print(f"{name}: {bpm} bpm, {len(audio) / SR:.2f} s, {path}")
