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
