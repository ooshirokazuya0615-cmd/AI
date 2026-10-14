"""ASMR-aware mastering: linear gain to a loudness target + transparent lookahead peak limiter
(4x oversampled peak detection ~ true peak), with a report of how many transients were touched."""
import subprocess
import numpy as np
from dsp import SR, write_wav24, resample


def _sliding_min(g, w):
    """min over [n, n+w) using doubling (w rounded up to a power of two)"""
    out = g.copy(); span = 1
    while span < w:
        sh = np.r_[out[span:], np.full(span, 1.0)]
        out = np.minimum(out, sh); span *= 2
    return out


def limiter(x, ceiling_db=-1.0, lookahead_ms=1.5, release_ms=60.0, os=4):
    x = np.asarray(x, float)
    st = x if x.ndim == 2 else x[:, None]
    up = resample(st, SR, SR * os)
    pk = np.abs(up).max(axis=1)
    pk = pk[:len(st) * os].reshape(len(st), os).max(axis=1)  # inter-sample peak per output sample
    ceil = 10 ** (ceiling_db / 20)
    g_req = np.minimum(1.0, ceil / np.maximum(pk, 1e-12))
    L = max(2, int(lookahead_ms * 1e-3 * SR))
    g = _sliding_min(np.r_[np.ones(L), g_req], 2 * L)[:len(g_req) + L]  # look ahead / behind
    # smooth attack: moving average (length L) of the windowed min stays <= g_req at peaks
    k = np.ones(L) / L
    g = np.convolve(g, k, mode='full')[L:L + len(g_req)]
    g = np.minimum(g, g_req)  # hard guarantee
    # release: one-pole return towards 1
    a = np.exp(-1.0 / (release_ms * 1e-3 * SR))
    out = np.empty_like(g)
    prev = 1.0
    for i, gi in enumerate(g):  # python loop: ~1 s per minute of audio
        prev = gi if gi < prev else gi + (prev - gi) * a
        out[i] = prev
    y = st * out[:, None]
    return (y if x.ndim == 2 else y[:, 0]), out


def lufs_of(y, tmp):
    write_wav24(tmp, np.clip(y, -1, 1 - 1e-7))
    o = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', tmp, '-af', 'ebur128=peak=true:framelog=quiet',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = tp = None
    for line in o.splitlines()[::-1]:
        s = line.strip()
        if s.startswith('I:') and I is None: I = float(s.split()[1])
        if s.startswith('Peak:') and tp is None: tp = float(s.split()[1])
    return I, tp


def master(x, target_lufs, tmp, ceiling_db=-1.0):
    I, tp = lufs_of(x, tmp)
    y = x * 10 ** ((target_lufs - I) / 20)
    gtot = np.ones(len(y))
    for it in range(6):  # limiting lowers loudness a little: iterate, always ending on the limiter
        y, g = limiter(y, ceiling_db - 0.3)
        gtot *= g
        I2, tp2 = lufs_of(y, tmp)
        if abs(I2 - target_lufs) < 0.25 or it == 5:
            break
        y = y * 10 ** ((target_lufs - I2) / 20)
        gtot *= 1.0
    return y, gtot, {'lufs': I2, 'true_peak': tp2}
