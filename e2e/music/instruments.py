"""Sampled instruments for the CC0 songs: each is a bank of recorded notes, played at any pitch by shifting the nearest.

Every library here is CC0-1.0 (see weiss/static/weiss/sounds/music/cc0/LICENSES.md). The samples live in e2e/scratch
(downloaded, not in git). A note is resampled from the nearest recorded note, which also converts its sample rate.
"""
import functools
import glob
import pathlib
import re

import numpy as np
import soundfile as sf

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRATCH = ROOT / "e2e" / "scratch"
KIT_DIR = ROOT / "weiss" / "static" / "weiss" / "sounds" / "music" / "kit"
SR = 44100

NOTE = re.compile(r"([A-Ga-g])(#|s|b(?=-?\d))?(-?\d)")
PITCH = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def midi(name):
    """'C4' -> 60, 'bb1' -> 34, 'Eb3' -> 51, 'A-1' -> 9, 'f#2' -> 42."""
    found = NOTE.fullmatch(name)
    assert found, f"not a note: {name}"
    letter, accidental, octave = found.groups()
    shift = {"#": 1, "s": 1, "b": -1}.get(accidental or "", 0)
    return (int(octave) + 1) * 12 + PITCH[letter.lower()] + shift


def read(path):
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    return data.mean(axis=1), rate


# Each bank: a glob under e2e/scratch, a regex on the file name whose first group is the note, and the naming offset in
# semitones (real pitch = named pitch + offset). The offsets were measured with e2e/music/calibrate.py: libraries name
# octaves differently (the piano, saxes, strings and cello sound an octave above their names; the guitars and the
# electric bass an octave below).
BANKS = {
    "piano": ("inst/Osiris_Piano/**/UC/A/Piano_UC_MicA_*_vl2.flac", r"MicA_([A-G]-?\d)_vl2", 12),
    "guitar_dist": ("inst/karoryfer.black-and-green-guitars/Samples/black/ord/twang_*_f_rr1.wav", r"twang_([a-g]b?\d)_f_rr1", -12),
    "guitar_mute": ("inst/karoryfer.black-and-green-guitars/Samples/black/stac/*_rr1.wav", r"_([a-g]b?\d)_(?:f|mf)?_?rr1", -12),
    "guitar_lead": ("inst/karoryfer.black-and-green-guitars/Samples/green/ord/*_f_rr1.wav", r"_([a-g]b?\d)_f_rr1", -12),
    "guitar_clean": ("inst/karoryfer.emilyguitar/Emilyguitar/notes/*_mf_rr1.wav", r"^([a-g]b?\d)_mf_rr1", 0),
    "bass_electric": ("inst/karoryfer.growlybass/Growlybass/sustain/*_f_rr1.wav", r"^([a-g]b?\d)_f_rr1", -12),
    "bass_slap": ("inst/karoryfer.fashionbass/Fashionbass/notes/*_f_rr1.wav", r"^([a-g]b?\d)_f_rr1", 0),
    "bass_upright": ("cc0/DSmolken_double_bass/**/pizz_*_m*.wav", r"pizz_([a-g]b?\d)_", 0),
    "sax_bari": ("inst/karoryfer.bear-sax/Bear_Sax/Samples/*_vl3*.wav", r"^([a-g]b?\d)_vl3", 12),
    "sax_alto": ("inst/karoryfer.weresax/Weresax/Samples/alto/*_f_rr1_dnm.wav", r"^([a-g]b?\d)_f_rr1_dnm", 12),
    "strings": ("inst/karoryfer.string-cyborgs/String_Cyborgs/Samples/blackheart/*.wav", r"^([A-G]b?\d)", 12),
    "cello": ("inst/karoryfer-bigcat.cello/Karoryfer_Bigcat_cello/Samples/sus/*_mf_d.wav", r"^([A-G]b?\d)_mf_d", 12),
    "violin": ("cc0/Caveman_Cosmonaut/**/violin_*.wav", r"violin_([a-g]b?\d)\.wav", 0),
}


@functools.lru_cache(maxsize=None)
def bank(name):
    """{real midi pitch: path} for an instrument: one recording per note (the first take found)."""
    pattern, regex, offset = BANKS[name]
    out = {}
    for path in sorted(glob.glob(str(SCRATCH / pattern), recursive=True)):
        found = re.search(regex, pathlib.Path(path).name)
        if found:
            out.setdefault(midi(found.group(1)) + offset, path)
    assert out, f"the {name} bank is empty: {pattern}"
    return out


@functools.lru_cache(maxsize=None)
def recording(path):
    return read(path)


@functools.lru_cache(maxsize=4096)
def note(instrument, pitch):
    """A note at any pitch (midi): the nearest recording, resampled. Returns a float32 array at SR."""
    notes = bank(instrument)
    source = min(notes, key=lambda n: abs(n - pitch))
    data, rate = recording(notes[source])
    ratio = (2 ** ((pitch - source) / 12)) * (rate / SR)  # the pitch shift, and the sample rate's
    length = int(len(data) / ratio)
    positions = np.arange(length) * ratio
    return np.interp(positions, np.arange(len(data)), data).astype(np.float32)


@functools.lru_cache(maxsize=None)
def drum(name):
    """A one-shot from the exported kit (weiss/static/weiss/sounds/music/kit/, from the CC0 drum kits)."""
    data, rate = read(KIT_DIR / f"{name}.wav")
    assert rate == SR
    return data
