"""Check each instrument bank's naming against its real pitch: some libraries name octaves differently.

For a few recordings per bank, estimate the fundamental (autocorrelation over a steady stretch) and compare it with the
note in the file name. Prints the offset in semitones (a multiple of 12 means an octave naming difference).
Run: python e2e/music/calibrate.py
"""
import math
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0])
import instruments as I  # noqa: E402


def fundamental(data, rate, low=30.0, high=2000.0):
    """The fundamental frequency of a steady stretch (from 20% to 50% of the note), by autocorrelation."""
    start, end = int(len(data) * 0.2), int(len(data) * 0.5)
    chunk = data[start:end]
    chunk = chunk - chunk.mean()
    if len(chunk) < rate * 0.05:
        chunk = data[: int(rate * 0.3)] - data[: int(rate * 0.3)].mean()
    corr = np.correlate(chunk[: rate // 4], chunk[: rate // 4], mode="full")[len(chunk[: rate // 4]) - 1:]
    lo, hi = int(rate / high), int(rate / low)
    lag = lo + int(np.argmax(corr[lo:hi]))
    return rate / lag


def offset(bank_name, samples=4):
    notes = I.bank(bank_name)
    keys = sorted(notes)
    picks = [keys[i * (len(keys) - 1) // max(1, samples - 1)] for i in range(samples)]
    found = []
    for named in picks:
        data, rate = I.recording(notes[named])
        f = fundamental(data, rate)
        measured = 69 + 12 * math.log2(f / 440.0)
        found.append(round(measured - named))
    return found


if __name__ == "__main__":
    for name in I.BANKS:
        try:
            print(f"{name:14s} offsets (semitones): {offset(name)}")
        except AssertionError as error:
            print(name, "EMPTY", error)
