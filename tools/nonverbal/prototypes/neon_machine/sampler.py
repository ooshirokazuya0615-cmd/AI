"""Pitched one-shot sampler over the CC0 VSCO-2 Community Edition recordings (https://github.com/sgossner/VSCO-2-CE).

Only the needed files are fetched (sparse checkout) into a local folder; nothing is committed to this repository.
Each note picks the nearest recorded pitch and is resampled to the exact pitch.

    VSCO_DIR=/path/to/vsco python audio6.py out.wav
"""
import os
import re
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

SR = 48000
NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
ROOT = Path(os.environ.get('VSCO_DIR', ''))
FAMILIES = {
    'marimba': ('Percussion/Marimba', r'_([A-G]#?)(\d)_'),
    'glock': ('Percussion/Glock', r'_([A-G]#?)(\d)\.wav'),
    'piano': ('Keys/Upright Nr1', r'UR1_([A-G]#?)(\d)_mf'),
}


def available():
    return ROOT.is_dir() and (ROOT / 'Percussion' / 'Marimba').is_dir()


def read_wav(path):
    with wave.open(str(path), 'rb') as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        x = np.where(x & 0x800000, x - 0x1000000, x) / 8388608.0
    elif sw == 2:
        x = np.frombuffer(raw, dtype=np.int16) / 32768.0
    else:
        x = np.frombuffer(raw, dtype=np.int32) / 2147483648.0
    x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)
    return x


@lru_cache(maxsize=None)
def bank(family):
    folder, pat = FAMILIES[family]
    out = []
    for p in sorted((ROOT / folder).glob('*.wav')):
        m = re.search(pat, p.name)
        if m:
            out.append((12 * (int(m.group(2)) + 1) + NOTE[m.group(1)], p))
    return out


@lru_cache(maxsize=None)
def _load(path):
    x = read_wav(path)
    peak = np.max(np.abs(x)) or 1.0
    return x / peak


def note(family, midi, length=None):
    roots = bank(family)
    root, path = min(roots, key=lambda rp: abs(rp[0] - midi))
    x = _load(path)
    ratio = 2 ** ((midi - root) / 12)
    n = int(len(x) / ratio)
    y = np.interp(np.arange(n) * ratio, np.arange(len(x)), x)
    if length:
        y = y[: int(SR * length)]
        fade = min(len(y), int(SR * 0.05))
        y[-fade:] *= np.linspace(1, 0, fade)
    return y


def one(path_rel, length=None):
    y = _load(ROOT / path_rel)
    if length:
        y = y[: int(SR * length)]
    return y


# ---------------------------------------------------------------- the upright piano, at three dynamics
# VS Upright Nr. 1 was recorded pp, mf and f, twice each (two round-robin takes), every minor third or so.
# A note picks the recording of its dynamic (soft notes sound darker as well as quieter, as on a real piano),
# alternates the two takes so repeated notes never sound copied, and is resampled to the exact pitch. The
# recordings keep their natural levels (one gain for the whole set), so pp is really quieter than f.
PIANO_DIR = 'Keys/Upright Nr1'
PIANO_LAYERS = (('pp', 0.2), ('mf', 0.55), ('f', 0.9))      # the velocity each recording stands for


def piano_layers_available():
    return (ROOT / PIANO_DIR).is_dir() and any((ROOT / PIANO_DIR).glob('UR1_*_pp_RR1.wav'))


@lru_cache(maxsize=None)
def piano_bank():
    out = {}
    for p in sorted((ROOT / PIANO_DIR).glob('UR1_*.wav')):
        m = re.search(r'UR1_([A-G]#?)(\d)_(pp|mf|f)_RR(\d)', p.name)
        if m:
            out.setdefault(m.group(3), []).append((12 * (int(m.group(2)) + 1) + NOTE[m.group(1)], int(m.group(4)), p))
    return out


@lru_cache(maxsize=None)
def _raw(path):
    return read_wav(path)


@lru_cache(maxsize=None)
def piano_gain():
    return 1.0 / float(np.median([np.max(np.abs(_raw(p))) for _, _, p in piano_bank()['mf']]))


@lru_cache(maxsize=None)
def piano_layer_db(name):
    """How much louder this recorded dynamic is than mf (median over the keyboard, first half second)."""
    def lvl(n):
        return np.median([10 * np.log10(np.mean(_raw(p)[: SR // 2] ** 2) + 1e-12) for _, _, p in piano_bank()[n]])
    return float(lvl(name) - lvl('mf'))


def piano(midi, vel, length=None, take=0, release=0.14):
    """One piano note at velocity 0..1: the tone of the nearest recorded dynamic, at a level that follows the
    velocity smoothly, with the damper's quick fade at `length` (None = let it ring out)."""
    name, v_layer = min(PIANO_LAYERS, key=lambda lv: abs(lv[1] - vel))
    if not piano_layers_available():
        name, v_layer = 'mf', 0.55
    cands = piano_bank()[name]
    dist = min(abs(r - midi) for r, _, _ in cands)
    near = [c for c in cands if abs(c[0] - midi) == dist]
    root, _, path = next((c for c in near if c[1] == 1 + take % 2), near[0])
    x = _raw(path) * piano_gain()
    ratio = 2 ** ((midi - root) / 12)
    n = int(len(x) / ratio)
    if length:
        n = min(n, int(SR * (length + release)))
    y = np.interp(np.arange(n) * ratio, np.arange(len(x)), x)
    if length and len(y) > int(SR * length):
        k = int(SR * length)
        y[k:] *= np.exp(-np.arange(len(y) - k) / (SR * release / 4))
    fade = min(len(y), 64)
    y[-fade:] *= np.linspace(1, 0, fade)
    # loudness follows the velocity smoothly (about 14 dB from pp to f); the layer only sets the tone
    return y * 10 ** ((20.0 * (vel - 0.55) - piano_layer_db(name)) / 20)
