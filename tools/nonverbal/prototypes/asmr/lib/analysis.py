"""
Objective measurements used to judge synthetic foley without listening.

  rise_ms      10%->90% rise of the Hilbert envelope at each detected onset (median)
  crest_db     peak / RMS over the active part of the clip
  plr_db       true-peak minus integrated loudness (ffmpeg ebur128), the number that
               decides whether a -14 LUFS master must be limited
  centroid     power-weighted spectral centroid of the active part
  rolloff95    frequency below which 95 % of the power lies
  bands        % of power in <500, 0.5-2k, 2-5k, 5-10k, >10k Hz
  flatness     spectral flatness 100 Hz-16 kHz (0 = tonal, 1 = white)
  t60_ms       decay time of the strongest isolated event (Schroeder backward integral, T20*3)
  ev_rate      onsets per second (texture density)
"""
import json
import subprocess

import numpy as np

from dsp import filt


def to_mono(x):
    return x if x.ndim == 1 else x.mean(axis=1)


def hilbert_env(x):
    n = len(x)
    X = np.fft.fft(x, n)
    h = np.zeros(n)
    h[0] = 1
    if n % 2 == 0:
        h[n // 2] = 1; h[1:n // 2] = 2
    else:
        h[1:(n + 1) // 2] = 2
    return np.abs(np.fft.ifft(X * h))


def smooth(x, n):
    if n <= 1:
        return x
    k = np.ones(n) / n
    return np.convolve(x, k, mode='same')


def frame_db(x, sr, hop_ms=0.5):
    hop = max(1, int(sr * hop_ms / 1000))
    m = len(x) // hop
    fr = np.abs(x[:m * hop]).reshape(m, hop).max(axis=1)
    return 20 * np.log10(fr + 1e-9), hop


def onsets(x, sr, rise_db=12.0, floor_db=-30.0, look_ms=20.0, min_gap_ms=20.0, win_ms=1.0):
    """Sample indices of onsets: the 1 ms RMS envelope jumps >= rise_db above its minimum
    over the previous look_ms, is within floor_db of the loudest frame, and is a local
    maximum within +-3 ms.  Robust to steady noise beds (field recordings)."""
    w = max(1, int(sr * win_ms / 1000))
    m = len(x) // w
    rms = np.sqrt((x[:m * w].reshape(m, w) ** 2).mean(axis=1) + 1e-20)
    db = 20 * np.log10(rms)
    top = db.max()
    look = max(1, int(look_ms / win_ms)); gap = int(min_gap_ms / win_ms); loc = max(1, int(3 / win_ms))
    peaks, last = [], -10 ** 9
    for i in range(look, m):
        if db[i] < top + floor_db:
            continue
        if db[i] < db[max(0, i - loc):i + loc + 1].max():
            continue
        if db[i] - db[i - look:i].min() >= rise_db and i - last >= gap:
            seg = np.abs(x[i * w:(i + 1) * w])
            peaks.append(i * w + int(np.argmax(seg)))
            last = i
    return np.array(peaks, int)


def rise_times(x, sr, peaks, max_ms=30.0):
    env = smooth(hilbert_env(x), max(1, int(sr * 0.00005)))
    out = []
    for p in peaks:
        lo = max(0, p - int(max_ms * sr / 1000))
        seg = env[lo:p + int(0.003 * sr)]
        if len(seg) < 4:
            continue
        pk_i = int(np.argmax(seg)); pk = seg[pk_i]
        pre = seg[:pk_i + 1]
        i90 = np.where(pre >= 0.9 * pk)[0]
        i10 = np.where(pre <= 0.1 * pk)[0]
        if len(i90) == 0 or len(i10) == 0:
            continue
        i90 = i90[0]
        i10 = i10[i10 < i90]
        if len(i10) == 0:
            continue
        out.append((i90 - i10[-1]) / sr * 1000)
    return np.array(out)


def active_mask(x, sr, rel_db=-40.0, win_ms=10.0):
    w = max(1, int(sr * win_ms / 1000))
    m = len(x) // w
    rms = np.sqrt((x[:m * w].reshape(m, w) ** 2).mean(axis=1) + 1e-20)
    db = 20 * np.log10(rms)
    keep = db > db.max() + rel_db
    return np.repeat(keep, w), w


def spectrum(x, sr, nfft=4096):
    hop = nfft // 2
    win = np.hanning(nfft)
    if len(x) < nfft:
        x = np.pad(x, (0, nfft - len(x)))
    frames = [x[i:i + nfft] * win for i in range(0, len(x) - nfft + 1, hop)]
    P = np.mean([np.abs(np.fft.rfft(f)) ** 2 for f in frames], axis=0)
    f = np.fft.rfftfreq(nfft, 1 / sr)
    return f, P


def schroeder_t60(seg, sr):
    e = seg ** 2
    edc = np.cumsum(e[::-1])[::-1]
    edc_db = 10 * np.log10(edc / (edc[0] + 1e-30) + 1e-30)
    t = np.arange(len(seg)) / sr
    def fit(a, b):
        idx = np.where((edc_db <= a) & (edc_db >= b))[0]
        if len(idx) < 8:
            return None
        slope = np.polyfit(t[idx], edc_db[idx], 1)[0]
        return -60.0 / slope if slope < 0 else None
    t20 = fit(-5, -25)
    edt = fit(0, -10)
    return t20, edt


def lufs(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af',
                          'ebur128=peak=true:framelog=quiet', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    I = tp = None
    for line in out.splitlines()[::-1]:
        s = line.strip()
        if s.startswith('I:') and I is None:
            try: I = float(s.split()[1])
            except ValueError: pass
        if s.startswith('Peak:') and tp is None:
            try: tp = float(s.split()[1])
            except ValueError: pass
    return I, tp


def measure(x, sr, path=None, isolate=True):
    x = to_mono(np.asarray(x, float))
    x = x - x.mean()
    mask, _ = active_mask(x, sr)
    mask = mask[:len(x)]
    xa = x[:len(mask)][mask] if mask.any() else x
    peak = np.max(np.abs(x)) + 1e-12
    rms_a = np.sqrt(np.mean(xa ** 2)) + 1e-12
    pk = onsets(x, sr)
    rt = rise_times(x, sr, pk)
    # band energies / centroid / rolloff from ONE rectangular periodogram of the whole clip:
    # exact by Parseval, no window bias (a Hann frame starting at an onset hides fast decays)
    Pfull = np.abs(np.fft.rfft(x)) ** 2
    ffull = np.fft.rfftfreq(len(x), 1 / sr)
    f, P = ffull, Pfull
    tot = P.sum() + 1e-30
    cen = float((f * P).sum() / tot)
    cum = np.cumsum(P) / tot
    roll95 = float(f[np.searchsorted(cum, 0.95)])
    edges = [0, 500, 2000, 5000, 10000, sr / 2]
    bands = [round(100 * P[(f >= a) & (f < b)].sum() / tot, 1) for a, b in zip(edges[:-1], edges[1:])]
    f, P = spectrum(xa, sr)
    sel = (f >= 100) & (f <= min(16000, sr / 2 - 1))
    flat = float(np.exp(np.mean(np.log(P[sel] + 1e-30))) / (np.mean(P[sel]) + 1e-30))
    # decay of the strongest event, up to the next onset (or 1.5 s)
    t60 = edt = None
    if len(pk):
        j = int(np.argmax(np.abs(x[pk])))
        start = pk[j]
        nxt = pk[j + 1] if j + 1 < len(pk) else len(x)
        end = min(nxt - int(0.002 * sr), start + int(1.5 * sr), len(x))
        if end - start > int(0.005 * sr):
            t60, edt = schroeder_t60(x[start:end], sr)
    dur_active = mask.sum() / sr
    res = {
        'n_onsets': int(len(pk)),
        'ev_rate': round(len(pk) / max(dur_active, 1e-3), 1),
        'rise_ms_med': round(float(np.median(rt)), 3) if len(rt) else None,
        'rise_ms_p10': round(float(np.percentile(rt, 10)), 3) if len(rt) else None,
        'crest_db': round(20 * np.log10(peak / rms_a), 1),
        'centroid_hz': round(cen),
        'rolloff95_hz': round(roll95),
        'bands_pct': bands,
        'flatness': round(flat, 3),
        't60_ms': round(t60 * 1000, 1) if t60 else None,
        'edt_ms': round(edt * 1000, 1) if edt else None,
    }
    if path is not None:
        I, tp = lufs(path)
        res['lufs_I'] = I
        res['true_peak_dbfs'] = tp
        res['plr_db'] = round(tp - I, 1) if (I is not None and tp is not None and I > -70) else None
    return res


def partials(x, sr, n=8, fmin=80, nfft=1 << 16):
    """Strongest spectral peaks of the first 200 ms (for modal sounds)."""
    x = to_mono(x)
    st = int(np.argmax(np.abs(x) > 0.3 * np.max(np.abs(x))))
    seg = x[st:min(len(x), st + int(0.2 * sr))]
    win = np.hanning(2 * len(seg))[len(seg):]  # fade-out only: keeps the fast-decaying start
    X = np.abs(np.fft.rfft(seg * win, nfft))
    f = np.fft.rfftfreq(nfft, 1 / sr)
    db = 20 * np.log10(X + 1e-12)
    idx = [i for i in range(2, len(X) - 2) if f[i] > fmin and X[i] > X[i - 1] and X[i] >= X[i + 1]
           and X[i] > X[i - 2] and X[i] >= X[i + 2]]
    idx = sorted(idx, key=lambda i: -X[i])[:n]
    top = db.max()
    return [(round(float(f[i])), round(float(db[i] - top), 1)) for i in sorted(idx)]


def band_t60(x, sr, centers=(500, 1000, 2000, 4000, 8000)):
    x = to_mono(x)
    pk = int(np.argmax(np.abs(x)))
    out = {}
    for fc in centers:
        if fc > sr / 2.5:
            continue
        y = filt(x, ('bp', fc, 1.4))[pk:]
        t20, edt = schroeder_t60(y, sr)
        out[fc] = round((t20 or edt or 0) * 1000, 1)
    return out


if __name__ == '__main__':
    import sys
    from dsp import read_wav
    for p in sys.argv[1:]:
        x, sr = read_wav(p)
        print(p, json.dumps(measure(x, sr, p)))
