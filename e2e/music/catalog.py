"""The seven CC0 songs, written out layer by layer. Steps are sixteenths: bar b, sixteenth s is step 16*b + s.

Tier map (the engine's): 0 core+bass, 1 +top, 2 +chords, 3 +lead, 4 +extra, 5 +drive, 6 all louder. Climax and splash
are separate. Each layer is its own part, so each tier brings in something you can hear.
Run: python e2e/music/catalog.py [key ...]
"""
import sys

from songs import Song, notes


def per_bar(song, fn):
    for bar in range(4):
        fn(bar, 16 * bar)


# ------------------------------------------------------------------------------------------------ cc0_1: Rock, 118
def rock():
    s = Song("cc0_1", "Rock", 118)
    roots = notes("E1 C2 G1 D2")
    power = [notes("E2 B2 E3"), notes("C3 G3 C4"), notes("G2 D3 G3"), notes("D3 A3 D4")]
    piano = [notes("E4 G4 B4"), notes("E4 G4 C5"), notes("D4 G4 B4"), notes("D4 F#4 A4")]
    lead = [[(0, "B4", 3), (4, "G4", 2), (6, "A4", 2), (8, "B4", 4), (12, "D5", 4)],
            [(0, "C5", 3), (4, "B4", 2), (6, "G4", 2), (8, "E4", 6), (14, "G4", 2)],
            [(0, "D5", 3), (4, "B4", 2), (6, "D5", 2), (8, "G5", 4), (12, "F#5", 4)],
            [(0, "F#5", 3), (4, "E5", 2), (6, "D5", 2), (8, "A4", 6), (14, "B4", 2)]]

    def bar(b, o):
        for k in (0, 8, 10):
            s.hit("core", "kick", o + k, 1.0)
        for k in (4, 12):
            s.hit("core", "snare", o + k, 0.9)
        for k in range(0, 16, 2):
            s.hit("top", "hat", o + k, 0.55 if k % 4 else 0.7)
        for k in range(0, 16, 2):
            s.play("bass", "bass_electric", roots[b] + (12 if k == 14 else 0), o + k, 1.8, 0.9)
        for k in range(0, 16, 2):
            s.play("chords", "guitar_dist", power[b], o + k, 4 if k == 0 else 1.5, 0.8 if k == 0 else 0.55)
        for k, n, d in lead[b]:
            s.play("lead", "guitar_lead", notes(n), o + k, d, 0.7)
        s.play("extra", "piano", piano[b], o, 16, 0.55, strum=12)
        s.hit("drive", "crash", o, 0.55)
        for k in range(1, 16, 2):
            s.hit("drive", "hat", o + k, 0.35)
        for k in (7, 15):
            s.hit("drive", "snare", o + k, 0.25)
        for k in range(0, 16, 2):
            s.play("drive", "bass_electric", roots[b] + 12, o + k, 1.6, 0.4)
        for k in range(0, 16, 2):
            s.hit("climax", "kick", o + k, 0.6)
        for k in range(0, 16):
            s.hit("climax", "hat", o + k, 0.35)
        for k, n, d in lead[b]:
            s.play("climax", "guitar_lead", [midi_up(n)], o + k, d, 0.5)
    per_bar(s, bar)
    s.hit("climax", "crash", 0, 0.7)
    s.hit("climax", "crash", 32, 0.7)
    s.drive("chords", 4.0)
    s.lowpass("chords", 5500)
    s.drive("lead", 2.0)
    for layer in ("lead", "extra", "climax"):
        s.reverb(layer, 1.6, 0.3)
    splash_fill(s, power[0], "guitar_dist")
    s.drive("splash", 2.5)
    return s


# ------------------------------------------------------------------------------------------------ cc0_3: Punk, 160
def punk():
    s = Song("cc0_3", "Punk", 160)
    roots = notes("G1 D2 E1 C2")
    power = [notes("G2 D3 G3"), notes("D3 A3 D4"), notes("E2 B2 E3"), notes("C3 G3 C4")]
    lead = [[(0, "D5", 4), (4, "B4", 4), (8, "G4", 4), (12, "B4", 4)],
            [(0, "A4", 4), (4, "F#4", 4), (8, "D5", 8)],
            [(0, "B4", 4), (4, "G4", 4), (8, "E4", 4), (12, "G4", 4)],
            [(0, "E5", 4), (4, "D5", 4), (8, "C5", 6), (14, "D5", 2)]]
    strings = [notes("G3 B3 D4"), notes("F#3 A3 D4"), notes("E3 G3 B3"), notes("E3 G3 C4")]

    def bar(b, o):
        for k in (0, 6, 8):
            s.hit("core", "kick", o + k, 1.0)
        for k in (4, 12):
            s.hit("core", "snare", o + k, 1.0)
        for k in range(0, 16, 2):
            s.hit("top", "ride", o + k, 0.45)
        for k in range(0, 16, 2):
            s.play("bass", "bass_electric", roots[b], o + k, 1.6, 0.9)
        for k in range(0, 16, 2):
            s.play("chords", "guitar_dist", power[b], o + k, 1.8, 0.65)
        for k, n, d in lead[b]:
            s.play("lead", "guitar_lead", notes(n), o + k, d, 0.7)
        s.play("extra", "strings", strings[b], o, 16, 0.6)
        s.hit("drive", "crash", o, 0.6)
        for k in range(0, 16, 2):
            s.hit("drive", "kick", o + k + 1 if k % 4 == 2 else o + k, 0.45)
        for k in (11, 15):
            s.hit("drive", "snare", o + k, 0.3)
        for k in range(0, 16):
            s.hit("climax", "kick", o + k, 0.45)
            s.hit("climax", "hat", o + k, 0.3)
        for k, n, d in lead[b]:
            s.play("climax", "guitar_lead", [midi_up(n)], o + k, d, 0.5)
    per_bar(s, bar)
    s.drive("chords", 3.0)
    s.lowpass("chords", 6000)
    s.drive("lead", 2.0)
    for layer in ("lead", "extra", "climax"):
        s.reverb(layer, 1.2, 0.25)
    for k in range(8, 16):  # a snare roll into the next bar
        s.hit("splash", "snare", k, 0.4 + 0.05 * (k - 8))
    s.hit("splash", "crash", 0, 0.9)
    s.play("splash", "guitar_dist", power[0], 0, 8, 0.8)
    s.drive("splash", 2.5)
    return s


# ------------------------------------------------------------------------------------------------ cc0_4: Jazz, 120 swing
def jazz():
    s = Song("cc0_4", "Jazz", 120, swing8=0.66)
    walk = [notes("D2 E2 F2 A2"), notes("G1 B1 D2 F2"), notes("C2 E2 G2 B2"), notes("A1 C#2 E2 G2")]
    shells = [notes("F3 A3 C4 E4"), notes("F3 B3 E4"), notes("E3 G3 B3 D4"), notes("C#3 G3 B3")]
    melody = [[(0, "A4", 3), (6, "F4", 2), (8, "E4", 2), (12, "D4", 4)],
              [(0, "D4", 2), (2, "F4", 2), (4, "A4", 2), (6, "G4", 6), (14, "F4", 2)],
              [(0, "E4", 6), (8, "G4", 4), (12, "B4", 4)],
              [(0, "C#5", 4), (6, "A4", 2), (8, "G4", 4), (12, "E4", 4)]]
    counter = [notes("D3 C3"), notes("B2 D3"), notes("E3 G3"), notes("C#3 E3")]

    def bar(b, o):
        s.hit("core", "kick", o, 0.45)
        s.hit("core", "kick", o + 10, 0.3)
        for k in (4, 12):
            s.hit("core", "rim", o + k, 0.6)
        for k in (0, 4, 6, 8, 12, 14):
            s.hit("top", "ride", o + k, 0.55 if k in (6, 14) else 0.45)
        for i, n in enumerate(walk[b]):
            s.play("bass", "bass_upright", n, o + 4 * i, 3.8, 1.0)
        for k in (6, 12):
            s.play("chords", "piano", shells[b], o + k, 3, 0.6, strum=8)
        for k, n, d in melody[b]:
            s.play("lead", "sax_alto", notes(n), o + k, d, 0.75)
        for i, n in enumerate(counter[b]):
            s.play("extra", "cello", n, o + 8 * i, 7.5, 0.6)
        for k in (4, 12):
            s.hit("drive", "hat", o + k, 0.4)
        for k in (3, 7, 11, 15):
            s.hit("drive", "snare", o + k, 0.15)
        for k in (2, 10):
            s.hit("drive", "ride", o + k, 0.3)
        for k in range(0, 16, 2):
            s.hit("climax", "ride", o + k, 0.5)
        for k, n, d in melody[b]:
            s.play("climax", "sax_alto", [midi_up(n)], o + k, d, 0.5)
    per_bar(s, bar)
    s.hit("climax", "crash", 0, 0.6)
    s.hit("climax", "crash", 32, 0.6)
    for layer in ("chords", "lead", "extra", "climax"):
        s.reverb(layer, 1.8, 0.3)
    s.hit("splash", "ride", 0, 0.8)
    s.hit("splash", "crash", 0, 0.7)
    s.play("splash", "piano", notes("D3 F3 A3 C4 E4"), 0, 8, 0.8, strum=10)
    for k in (12, 13, 14, 15):
        s.hit("splash", "snare", k, 0.35)
    s.reverb("splash", 1.8, 0.3)
    return s


# ------------------------------------------------------------------------------------------------ cc0_5: Hip hop, 90 swing
def hiphop():
    s = Song("cc0_5", "Hip hop", 90, swing16=0.33)
    roots = notes("A1 F1 D1 E1")
    keys = [notes("A3 C4 E4 G4"), notes("F3 A3 C4 E4"), notes("F3 A3 C4 D4"), notes("E3 G#3 B3 D4")]
    pads = [notes("E4 A4"), notes("C4 F4"), notes("D4 F4"), notes("D4 G#4")]
    hook = [[(2, "E5", 2), (4, "D5", 2), (6, "C5", 4), (12, "A4", 4)],
            [(2, "C5", 2), (4, "A4", 6)],
            [(2, "D5", 2), (4, "C5", 2), (6, "A4", 4), (12, "F4", 4)],
            [(2, "B4", 2), (4, "G#4", 6), (12, "E4", 4)]]

    def bar(b, o):
        for k in (0, 7, 8, 14 if b % 2 else 10):
            s.hit("core", "kick", o + k, 1.0)
        for k in (4, 12):
            s.hit("core", "snare", o + k, 0.95)
        for k in range(0, 16, 2):
            s.hit("top", "hat", o + k, 0.55 if k % 4 else 0.7)
        s.play("bass", "bass_electric", roots[b], o, 6, 1.0)
        s.play("bass", "bass_electric", roots[b], o + 8, 4, 0.9)
        s.play("bass", "bass_electric", roots[b] + 12, o + 14, 2, 0.6)
        s.play("chords", "piano", keys[b], o, 7, 0.65, strum=15)
        s.play("chords", "piano", keys[b], o + 10, 5, 0.5, strum=15)
        for k, n, d in hook[b]:
            s.play("lead", "sax_alto", notes(n), o + k, d, 0.65)
        s.play("extra", "strings", pads[b], o, 16, 0.5)
        for k in range(1, 16, 2):
            s.hit("drive", "hat", o + k, 0.35)
        for k in (3, 11):
            s.hit("drive", "snare", o + k, 0.2)
        s.hit("drive", "open", o + 14, 0.35)
        s.play("drive", "bass_electric", roots[b] + 12, o + 6, 2, 0.45)
        if b % 2 == 0:
            s.hit("drive", "crash", o, 0.4)
        for k in range(0, 16):
            s.hit("climax", "hat", o + k, 0.4)
        s.play("climax", "strings", [p + 12 for p in pads[b]], o, 16, 0.55)
        for k, n, d in hook[b]:
            s.play("climax", "sax_alto", [midi_up(n)], o + k, d, 0.45)
    per_bar(s, bar)
    s.lowpass("chords", 2400)  # the dusty, filtered keys
    s.lowpass("bass", 400)
    s.lowpass("lead", 3500)
    for layer in ("chords", "lead", "extra", "climax"):
        s.reverb(layer, 1.5, 0.3)
    s.hit("splash", "crash", 0, 0.8)
    s.hit("splash", "kick", 0, 1.0)
    s.play("splash", "piano", keys[0], 0, 6, 0.8, strum=20)
    s.play("splash", "sax_alto", notes("E5"), 4, 4, 0.6)
    s.lowpass("splash", 4000)
    s.reverb("splash", 1.5, 0.3)
    return s


# ------------------------------------------------------------------------------------------------ cc0_6: Funk, 100
def funk():
    s = Song("cc0_6", "Funk", 100)
    shift = [0, 0, 5, 0]  # E9, E9, A9, E9
    riff = [(0, "E1", 2), (3, "E2", 1), (4, "D2", 1), (6, "E1", 2), (8, "E1", 1), (10, "G1", 1), (11, "A1", 1),
            (13, "B1", 1), (14, "E2", 2)]
    chank = notes("G#3 D4 F#4")
    horn = [[(0, "B4", 1), (2, "D5", 1), (3, "E5", 3), (10, "D5", 1), (11, "B4", 2)],
            [(4, "G4", 1), (6, "A4", 1), (7, "B4", 4)],
            [(0, "E5", 1), (2, "G5", 1), (3, "A5", 3), (10, "G5", 1), (11, "E5", 2)],
            [(4, "D5", 1), (6, "B4", 1), (7, "E5", 6)]]

    def bar(b, o):
        t = shift[b]
        for k in (0, 3, 10):
            s.hit("core", "kick", o + k, 1.0)
        for k in (4, 12):
            s.hit("core", "snare", o + k, 0.95)
        for k in range(16):
            s.hit("top", "hat", o + k, 0.5 if k % 2 == 0 else 0.3)
        for k, n, d in riff:
            s.play("bass", "bass_slap", notes(n)[0] + t, o + k, d, 1.0)
        for k in (2, 6, 10, 14):
            s.play("chords", "guitar_mute", [p + t for p in chank], o + k, 0.7, 0.7)
        for k, n, d in horn[b]:
            s.play("lead", "sax_alto", notes(n), o + k, d, 0.7)
        for k in (0, 6, 8, 14):
            s.hit("extra", "cowbell", o + k, 0.45)
        s.play("extra", "piano", [p + t for p in notes("E4 G#4 D5")], o + 7, 1, 0.45)
        for k in (7, 15):
            s.hit("drive", "snare", o + k, 0.25)
        s.hit("drive", "open", o + 14, 0.4)
        for k, n, d in riff[::2]:
            s.play("drive", "bass_slap", notes(n)[0] + t + 12, o + k, d, 0.4)
        for k in range(0, 16, 2):
            s.hit("climax", "cowbell", o + k, 0.35)
        s.hit("climax", "crash", o, 0.5)
        for k, n, d in horn[b]:
            s.play("climax", "sax_alto", [midi_up(n)], o + k, d, 0.45)
    per_bar(s, bar)
    for layer in ("lead", "climax"):
        s.reverb(layer, 1.2, 0.25)
    s.hit("splash", "crash", 0, 0.8)
    s.play("splash", "sax_alto", notes("E5"), 0, 2, 0.7)
    s.play("splash", "guitar_mute", chank, 0, 1, 0.8)
    s.play("splash", "guitar_mute", chank, 3, 1, 0.8)
    for k in (12, 13, 14, 15):
        s.hit("splash", "snare", k, 0.35)
    return s


# ------------------------------------------------------------------------------------------------ cc0_7: Emo, 130
def emo():
    s = Song("cc0_7", "Emo", 130)
    roots = notes("A1 F1 C2 G1")
    arps = [notes("A2 E3 A3 C4 E4 C4 A3 E3"), notes("F2 C3 F3 A3 C4 A3 F3 C3"),
            notes("C3 G3 C4 E4 G4 E4 C4 G3"), notes("G2 D3 G3 B3 D4 B3 G3 D3")]
    melody = [[(0, "E5", 6), (6, "D5", 2), (8, "C5", 8)],
              [(0, "C5", 6), (6, "A4", 2), (8, "A4", 8)],
              [(0, "G4", 4), (4, "C5", 4), (8, "E5", 8)],
              [(0, "D5", 6), (6, "B4", 2), (8, "G4", 8)]]
    cello = [notes("A2"), notes("F2"), notes("C3"), notes("G2")]

    def bar(b, o):
        for k in (0, 10):
            s.hit("core", "kick", o + k, 1.0)
        s.hit("core", "snare", o + 8, 1.0)  # half-time
        for k in range(0, 16, 2):
            s.hit("top", "hat", o + k, 0.55)
        for k in range(0, 16, 2):
            s.play("bass", "bass_electric", roots[b], o + k, 1.8, 0.85)
        for i, n in enumerate(arps[b]):
            s.play("chords", "guitar_clean", n, o + 2 * i, 3, 0.6)
        for k, n, d in melody[b]:
            s.play("lead", "violin", notes(n), o + k, d, 0.6)
        s.play("extra", "cello", cello[b], o, 16, 0.6)
        for k in (4, 12):
            s.hit("drive", "snare", o + k, 0.8)  # full-time snare
        s.hit("drive", "crash", o, 0.5)
        for k in range(1, 16, 2):
            s.hit("drive", "hat", o + k, 0.3)
        for k in range(0, 16, 2):
            s.hit("climax", "kick", o + k, 0.55)
        for k in (2, 6, 10, 14):
            s.hit("climax", "snare", o + k, 0.45)
        for k, n, d in melody[b]:
            s.play("climax", "violin", [midi_up(n)], o + k, d, 0.45)
    per_bar(s, bar)
    for layer in ("chords", "lead", "extra", "climax"):
        s.reverb(layer, 2.0, 0.3)
    s.hit("splash", "crash", 0, 0.8)
    s.play("splash", "guitar_clean", notes("A2 E3 A3 C4 E4"), 0, 12, 0.8, strum=25)
    for k, drum_name in ((10, "tom_high"), (12, "tom_high"), (13, "tom_low"), (14, "tom_low")):
        s.hit("splash", drum_name, k, 0.6)
    s.reverb("splash", 2.0, 0.3)
    return s


# ------------------------------------------------------------------------------------------------ cc0_8: Metal, 160
def metal():
    s = Song("cc0_8", "Metal", 160)
    riff = [notes("E1")[0]] * 12 + [notes("F1")[0]] * 4  # the root under each sixteenth: E, then F at the bar's end
    chug = notes("E2 B2 E3")
    lead = [[(0, "E5", 4), (4, "B4", 4), (8, "C5", 4), (12, "B4", 4)],
            [(0, "G4", 4), (4, "A4", 4), (8, "B4", 8)],
            [(0, "E5", 4), (4, "F5", 4), (8, "E5", 4), (12, "D5", 4)],
            [(0, "C5", 4), (4, "B4", 4), (8, "A4", 4), (12, "B4", 4)]]

    def bar(b, o):
        for k in range(0, 16, 2):
            s.hit("core", "kick", o + k, 0.9)
        for k in (4, 12):
            s.hit("core", "snare", o + k, 1.0)
        for k in range(0, 16, 2):
            s.hit("top", "hat", o + k, 0.5)
        for k in range(0, 16, 2):
            s.play("bass", "bass_electric", riff[k], o + k, 1.6, 0.9)
        for k in range(16):
            root = riff[k]
            chord = [p + (root - notes("E1")[0]) for p in chug]
            s.play("chords", "guitar_dist", chord, o + k, 0.8, 0.6 if k % 4 else 0.8)
        for k, n, d in lead[b]:
            s.play("lead", "guitar_lead", notes(n), o + k, d, 0.6)
        if b >= 2:
            for k in range(16):
                s.hit("extra", "kick", o + k, 0.45)  # double kick, bars three and four
        else:
            for k in (2, 6, 10, 14):
                s.hit("extra", "tom_low", o + k, 0.4)
        for k in (0, 8):
            s.hit("drive", "crash", o + k, 0.45)
        for k in range(16):
            s.hit("drive", "hat", o + k, 0.25)
        for k in range(0, 16, 2):
            s.play("drive", "bass_electric", riff[k] + 12, o + k, 1.6, 0.35)
        for k in range(16):  # the blast beat
            s.hit("climax", "kick" if k % 2 == 0 else "snare", o + k, 0.45)
        for k, n, d in lead[b]:
            s.play("climax", "guitar_lead", [midi_up(n)], o + k, d, 0.4)
    per_bar(s, bar)
    s.drive("bass", 3.0)
    s.drive("chords", 7.0)
    s.lowpass("chords", 6500)
    s.drive("lead", 3.0)
    for layer in ("lead", "climax"):
        s.reverb(layer, 1.4, 0.25)
    s.hit("splash", "crash", 0, 0.9)
    s.hit("splash", "kick", 0, 1.0)
    s.play("splash", "guitar_dist", chug, 0, 10, 0.9)
    for k, drum_name in ((12, "tom_high"), (13, "tom_high"), (14, "tom_low"), (15, "tom_low")):
        s.hit("splash", drum_name, k, 0.6)
    s.drive("splash", 4.0)
    return s


# ------------------------------------------------------------------------------------------------ helpers

def midi_up(name):
    """A note name an octave up, as a midi pitch."""
    return notes(name)[0] + 12


def splash_fill(s, chord, instrument):
    """The rock splash: a crash and a chord stab, then a tom fill back into the bar."""
    s.hit("splash", "crash", 0, 0.9)
    s.hit("splash", "kick", 0, 1.0)
    s.play("splash", instrument, chord, 0, 6, 0.8)
    for k, drum_name in ((10, "tom_high"), (12, "tom_high"), (13, "tom_low"), (14, "tom_low"), (15, "snare")):
        s.hit("splash", drum_name, k, 0.6)


def add_tension(s, root_and_fifth):
    """Match point's layer: a heartbeat pulse, and the song's root and fifth on strings, swelling over each two bars."""
    s.heartbeat("tension", 0.8)
    for start in (0, 32):
        s.swell("tension", "strings", notes(root_and_fifth), start, 32, 1.0)
    s.reverb("tension", 1.8, 0.3)


SONGS = {"cc0_1": rock, "cc0_3": punk, "cc0_4": jazz, "cc0_5": hiphop, "cc0_6": funk, "cc0_7": emo, "cc0_8": metal}
TENSION = {"cc0_1": "E3 B3", "cc0_3": "G3 D4", "cc0_4": "D3 A3", "cc0_5": "A3 E4", "cc0_6": "E3 B3",
           "cc0_7": "A3 E4", "cc0_8": "E3 B3"}  # each song's root and fifth

if __name__ == "__main__":
    for key in sys.argv[1:] or SONGS:
        song = SONGS[key]()
        add_tension(song, TENSION[key])
        song.write()
