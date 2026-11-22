"""Export the one-shot drum kit the synth songs play (weiss/static/weiss/sounds/music/kit/), from the CC0 kits.

Each file is one hit: 44.1 kHz mono, 16-bit, trimmed to its sound (at most 2 seconds, with a short fade at the end) and
peaking at about -3 dBFS, so the engine's gains set the balance. Sources are CC0-1.0 (see music/cc0/LICENSES.md).
Run: python e2e/export_kit.py
"""
import pathlib
import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parent.parent
KITS = ROOT / "e2e" / "scratch" / "cc0"
OUT = ROOT / "weiss" / "static" / "weiss" / "sounds" / "music" / "kit"
SR = 44100

# name: [(file, gain)], mixed together (the snare blends its top and bottom microphones)
KIT = {
    "kick": [("Big_Rusty_Drums_1100/Samples/kick_24/kick/kick/k_vl11_rr1.flac", 1.0)],
    "snare": [("Frankensnare_2100/Samples/14a_basic/top/sn_vl10_rr1.flac", 1.0),
              ("Frankensnare_2100/Samples/14a_basic/btm/sn_vl10_rr1.flac", 0.6)],
    "hat": [("Swirly_Drums_1104/Samples/hat_closed/hh_closed_vl10_rr1.wav", 1.0)],
    "open": [("Swirly_Drums_1104/Samples/hat_open/hh_open_vl10_rr1.wav", 1.0)],
    "ride": [("Swirly_Drums_1104/Samples/ride/ride_vl11_rr1.wav", 1.0)],
    "crash": [("Swirly_Drums_1104/Samples/crash/crash_vl10_rr1.wav", 1.0)],
    "tom_low": [("Swirly_Drums_1104/Samples/tom_floor/tom_floor_vl10_rr1.wav", 1.0)],
    "tom_high": [("Swirly_Drums_1104/Samples/tom_mhi/tom_mhi_vl8_rr1.wav", 1.0)],
    "clap": [("Frankensnare_2100/Samples/xtra_claps/clap_stack_rr1.flac", 1.0)],
    "cowbell": [("Swirly_Drums_1104/Samples/cowbell/cowbell_vl8_rr1.wav", 1.0)],
    "rim": [("Frankensnare_2100/Samples/14a_rimshot/top/sr_vl3_rr1.flac", 1.0)],
}
MAX_SECONDS = 2.0
FADE_SECONDS = 0.05


def load(relative):
    data, rate = sf.read(KITS / relative, dtype="float32")
    assert rate == SR, relative
    return data.mean(axis=1) if data.ndim > 1 else data


def trim(data):
    """Cut the tail once it's below -60 dB, at most MAX_SECONDS, with a short fade so it doesn't click."""
    loud = np.nonzero(np.abs(data) > np.max(np.abs(data)) * 0.001)[0]
    end = min(len(data), (loud[-1] + 1) if len(loud) else len(data), int(SR * MAX_SECONDS))
    data = data[:end].copy()
    fade = min(int(SR * FADE_SECONDS), len(data))
    data[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    return data


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, parts in KIT.items():
        sounds = [gain * load(path) for path, gain in parts]
        length = max(len(s) for s in sounds)
        mixed = np.zeros(length, dtype=np.float32)
        for s in sounds:
            mixed[: len(s)] += s
        mixed = trim(mixed)
        mixed *= 0.7 / np.max(np.abs(mixed))  # about -3 dBFS
        sf.write(OUT / f"{name}.wav", mixed, SR, subtype="PCM_16")
        print(f"{name}: {len(mixed) / SR:.2f} s")
