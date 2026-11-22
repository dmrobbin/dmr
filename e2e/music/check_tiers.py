"""Measure how much each tier changes each CC0 song: the mix's loudness at each tier, how loud the new part is against
the mix it joins (about -5 dB or louder is clearly heard), the climax's lift, and the loudest peak.
Run: python e2e/music/check_tiers.py
"""
import pathlib

import numpy as np
import soundfile as sf

DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "weiss" / "static" / "weiss" / "sounds" / "music" / "cc0"
TIERS = [["core", "bass"], ["top"], ["chords"], ["lead"], ["extra"], ["drive"]]
SONGS = ["cc0_1", "cc0_3", "cc0_4", "cc0_5", "cc0_6", "cc0_7", "cc0_8"]


def rms(x):
    return 20 * np.log10(max(float(np.sqrt(np.mean(x ** 2))), 1e-9))


for key in SONGS:
    layers = {name: sf.read(DIR / f"{key}_{name}.wav")[0] for name in
              ["core", "top", "bass", "chords", "lead", "extra", "drive", "climax"]}
    mix = np.zeros_like(layers["core"])
    out = []
    for tier, added in enumerate(TIERS):
        before = mix.copy()
        for name in added:
            mix = mix + layers[name]
        part = sum(layers[name] for name in added)
        out.append(f"t{tier} {rms(mix):.1f}" + (f" (new part {rms(part) - rms(before):+.0f} dB)" if tier else ""))
    lift = rms(mix + layers["climax"]) - rms(mix)
    peak = 20 * np.log10(np.max(np.abs(mix + layers["climax"])))
    print(f"{key}: " + " | ".join(out) + f" | climax +{lift:.1f} dB | peak {peak:.1f} dBFS")
