"""DSP + analysis helpers (numpy only). 48 kHz."""
import wave
import numpy as np

SR = 48000
TAU = 2 * np.pi


# ---------------------------------------------------------------- io
def write_wav(path, x, sr=SR):
    x = np.asarray(x, dtype=float)
    ch = 1 if x.ndim == 1 else x.shape[1]
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- basic filters
def smooth(x, n):
    """moving average (zero-phase, same length) via cumsum"""
    n = int(max(1, n))
    if n <= 1:
        return np.asarray(x, float)
    pad = n // 2
    xp = np.concatenate([np.full(pad, x[0]), x, np.full(n - pad, x[-1])])
    c = np.cumsum(np.concatenate([[0.0], xp]))
    return (c[n:] - c[:-n])[:len(x)] / n


def fft_filter(x, mag_fn):
    """zero-phase filter; mag_fn(freqs)->gain"""
    n = len(x)
    N = 1 << int(np.ceil(np.log2(n + 1)))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1 / SR)
    y = np.fft.irfft(X * mag_fn(f), N)[:n]
    return y


def hpf(x, fc=450.0, order=4):
    return fft_filter(x, lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order)))


def lpf(x, fc, order=2):
    return fft_filter(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))


def bpf(x, lo, hi, order=2):
    return fft_filter(x, lambda f: 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order)) /
                      np.sqrt(1 + (f / hi) ** (2 * order)))


def phone_sim(x):
    """small phone speaker: 4th-order HP at 450 Hz (task spec) + gentle LP above 9 kHz"""
    return fft_filter(x, lambda f: 1 / np.sqrt(1 + (450 / np.maximum(f, 1e-3)) ** 8) /
                      np.sqrt(1 + (f / 9000) ** 4))


def band_noise(n, lo, hi, rng, order=2):
    return bpf(rng.standard_normal(n), lo, hi, order)


# ---------------------------------------------------------------- stft
def stft(x, n=1024, hop=256):
    w = np.hanning(n + 1)[:-1]
    pad = n
    xp = np.concatenate([np.zeros(pad), x, np.zeros(pad + n)])
    nf = 1 + (len(xp) - n) // hop
    idx = np.arange(n)[None, :] + hop * np.arange(nf)[:, None]
    return np.fft.rfft(xp[idx] * w, axis=1), pad


def istft(X, length, n=1024, hop=256, pad=1024):
    w = np.hanning(n + 1)[:-1]
    frames = np.fft.irfft(X, n, axis=1) * w
    nf = frames.shape[0]
    out = np.zeros(hop * (nf - 1) + n)
    norm = np.zeros_like(out)
    for i in range(nf):
        out[i * hop:i * hop + n] += frames[i]
        norm[i * hop:i * hop + n] += w ** 2
    out /= np.maximum(norm, 1e-8)
    return out[pad:pad + length]


def shaped_noise(length, env_fn, rng, n=1024, hop=256):
    """white noise filtered by a time-varying magnitude envelope.
    env_fn(times[nf], freqs[nb]) -> (nf, nb) gains"""
    X, pad = stft(rng.standard_normal(length), n, hop)
    nf = X.shape[0]
    times = (np.arange(nf) * hop + n / 2 - pad) / SR
    freqs = np.fft.rfftfreq(n, 1 / SR)
    X *= env_fn(times, freqs)
    return istft(X, length, n, hop, pad)


# ---------------------------------------------------------------- formants
def formant_mag(f, F, B):
    """cascade of 2-pole resonators (unity DC gain), magnitude at freq f.
    f: (...), F,B: (..., nform) broadcastable with f[..., None]"""
    f = np.asarray(f)[..., None]
    F = np.asarray(F)
    B = np.asarray(B)
    m = F ** 2 / np.sqrt((F ** 2 - f ** 2) ** 2 + (f * B) ** 2)
    return np.prod(m, axis=-1)


# ---------------------------------------------------------------- analysis
def yin(x, fmin=70.0, fmax=3200.0, hop=480, thresh=0.15, gate_db=-40.0):
    """YIN pitch tracker. returns times, f0 (nan = unvoiced), aperiodicity"""
    maxlag = int(SR / fmin) + 2
    minlag = max(2, int(SR / fmax))
    W = 1024
    L = W + maxlag
    xp = np.concatenate([np.zeros(L), x, np.zeros(L)])
    starts = np.arange(L - W // 2, L + len(x) - W // 2, hop)
    starts = starts[starts + L <= len(xp)]
    nfr = len(starts)
    idx = starts[:, None] + np.arange(L)[None, :]
    B = xp[idx]                      # (nfr, L)
    A = B[:, :W]
    N = 1 << int(np.ceil(np.log2(L + W)))
    r = np.fft.irfft(np.conj(np.fft.rfft(A, N, axis=1)) * np.fft.rfft(B, N, axis=1), N, axis=1)[:, :maxlag + 1]
    c2 = np.concatenate([np.zeros((nfr, 1)), np.cumsum(B ** 2, axis=1)], axis=1)
    E0 = c2[:, W][:, None]
    taus = np.arange(maxlag + 1)
    Et = c2[:, taus + W] - c2[:, taus]
    d = np.maximum(E0 + Et - 2 * r, 0)
    cum = np.cumsum(d[:, 1:], axis=1)
    dn = np.ones_like(d)
    dn[:, 1:] = d[:, 1:] * taus[1:] / np.maximum(cum, 1e-12)
    rms = np.sqrt(E0[:, 0] / W)
    ref = np.max(rms) + 1e-12
    f0 = np.full(nfr, np.nan)
    ap = np.ones(nfr)
    for i in range(nfr):
        if 20 * np.log10(rms[i] / ref + 1e-12) < gate_db:
            continue
        seg = dn[i]
        below = np.where(seg[minlag:maxlag] < thresh)[0]
        if len(below):
            t = below[0] + minlag
            while t + 1 < maxlag and seg[t + 1] < seg[t]:
                t += 1
        else:
            t = int(np.argmin(seg[minlag:maxlag])) + minlag
            if seg[t] > 0.35:
                ap[i] = seg[t]
                continue
        ap[i] = seg[t]
        if 1 <= t < maxlag:
            a, b, c = seg[t - 1], seg[t], seg[t + 1]
            den = a - 2 * b + c
            off = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
            off = np.clip(off, -1, 1)
        else:
            off = 0.0
        f0[i] = SR / (t + off)
    times = (starts - L + W // 2) / SR
    return times, f0, ap


def st(f, ref):
    return 12 * np.log2(np.asarray(f) / ref)


def envelope(x, ms=2.0, out_sr=1000):
    e = smooth(np.abs(x), int(SR * ms / 1000))
    step = SR // out_sr
    return e[::step]


def roughness_index(x):
    """share of envelope modulation energy in 30-150 Hz (Arnal et al. 2015 'roughness' band)
    relative to 2-150 Hz, active parts only"""
    e = envelope(x, 1.5, 2000)
    act = e > 0.05 * e.max()
    if act.sum() < 64:
        return 0.0
    e = e[act]
    e = e - smooth(e, 2000 // 2)  # remove < ~2 Hz trend
    E = np.abs(np.fft.rfft(e * np.hanning(len(e)))) ** 2
    f = np.fft.rfftfreq(len(e), 1 / 2000)
    tot = E[(f >= 2) & (f <= 150)].sum() + 1e-12
    return float(E[(f >= 30) & (f <= 150)].sum() / tot)


def syllable_rate(x):
    """syllable-nucleus count: peaks of the 30 ms-smoothed dB envelope with >= 6 dB
    topographic prominence, >= 70 ms apart, above -30 dB re max"""
    e = envelope(x, 30.0, 1000)
    db = 20 * np.log10(e / (e.max() + 1e-12) + 1e-6)
    active = db > -35
    if active.sum() == 0:
        return 0.0, 0
    cand = [i for i in range(1, len(db) - 1) if db[i] >= db[i - 1] and db[i] > db[i + 1] and db[i] > -30]
    peaks = []
    for i in cand:
        l = i
        while l > max(0, i - 400) and db[l - 1] <= db[i]:
            l -= 1
        r = i
        while r < min(len(db) - 1, i + 400) and db[r + 1] <= db[i]:
            r += 1
        prom = db[i] - max(db[l:i + 1].min(), db[i:r + 1].min())
        if prom >= 6:
            if peaks and i - peaks[-1] < 70:
                if db[i] > db[peaks[-1]]:
                    peaks[-1] = i
                continue
            peaks.append(i)
    on = np.where(active)[0]
    dur = (on[-1] - on[0]) / 1000 + 1e-3
    return len(peaks) / dur, len(peaks)


def periodicity(x):
    """mean (1 - YIN aperiodicity) over frames above -30 dB: ~harmonicity of the voice"""
    t, f0, ap = yin(x, gate_db=-30)
    act = ap < 1
    return float(np.mean(1 - ap[act])) if act.any() else 0.0


def spectral_stats(x):
    X, _ = stft(x, 2048, 512)
    P = np.abs(X) ** 2
    fe = P.sum(axis=1)
    act = fe > 1e-4 * fe.max()
    P = P[act].sum(axis=0)
    f = np.fft.rfftfreq(2048, 1 / SR)
    tot = P.sum() + 1e-20
    cen = float((P * f).sum() / tot)
    cum = np.cumsum(P) / tot
    roll = float(f[np.searchsorted(cum, 0.85)])
    return dict(centroid_hz=round(cen), rolloff85_hz=round(roll),
                frac_above_450=round(float(P[f >= 450].sum() / tot), 3),
                frac_300_5k=round(float(P[(f >= 300) & (f <= 5000)].sum() / tot), 3),
                frac_above_1k=round(float(P[f >= 1000].sum() / tot), 3))


def rms_db(x):
    e = envelope(x, 25, 1000)
    act = e > 0.1 * e.max()
    full = smooth(x ** 2, 480)[::48]
    return float(10 * np.log10(full[act[:len(full)]].mean() + 1e-12)) if act.any() else -120.0


def contour_summary(times, f0, ref):
    v = ~np.isnan(f0)
    if v.sum() < 3:
        return dict(voiced_frac=round(float(v.mean()), 3))
    s = st(f0[v], ref)
    tv = times[v]
    n = len(s)
    k = max(3, n // 4)
    slope_end = np.polyfit(tv[-k:], s[-k:], 1)[0]
    slope_all = np.polyfit(tv, s, 1)[0]
    return dict(voiced_frac=round(float(v.mean()), 3),
                f0_median_hz=round(float(np.median(f0[v])), 1),
                f0_p10_hz=round(float(np.percentile(f0[v], 10)), 1),
                f0_p90_hz=round(float(np.percentile(f0[v], 90)), 1),
                f0_range_st=round(float(np.percentile(s, 90) - np.percentile(s, 10)), 2),
                f0_sd_st=round(float(np.std(s)), 2),
                slope_all_st_s=round(float(slope_all), 1),
                slope_end_st_s=round(float(slope_end), 1))


def contour_string(times, f0, step=0.05, t_end=None):
    """compact contour: Hz every `step` s ('.' = unvoiced)"""
    t_end = t_end if t_end is not None else times[-1]
    out = []
    for t in np.arange(0, t_end, step):
        m = (times >= t) & (times < t + step) & ~np.isnan(f0)
        out.append(str(int(round(np.median(f0[m])))) if m.any() else '.')
    # compress runs of '.'
    s, run = [], 0
    for o in out:
        if o == '.':
            run += 1
        else:
            if run:
                s.append('_' if run == 1 else f'_{run}')
                run = 0
            s.append(o)
    if run:
        s.append(f'_{run}')
    return ' '.join(s)


def pitch_survival(x, y, ref):
    """compare tracks of original x and phone-filtered y"""
    t1, f1, _ = yin(x)
    t2, f2, _ = yin(y)
    n = min(len(f1), len(f2))
    f1, f2 = f1[:n], f2[:n]
    v1 = ~np.isnan(f1)
    both = v1 & ~np.isnan(f2)
    if v1.sum() == 0:
        return dict(pitch_frames=0)
    d = np.abs(st(f2[both], 1) - st(f1[both], 1))
    ok = d < 1.0
    octv = np.abs(d - 12) < 1.0
    res = dict(voiced_kept=round(float(both.sum() / v1.sum()), 3),
               pitch_match_1st=round(float(ok.sum() / v1.sum()), 3),
               octave_err=round(float(octv.sum() / v1.sum()), 3))
    if both.sum() > 5:
        a, b = st(f1[both], ref), st(f2[both], ref)
        if np.std(a) > 1e-6 and np.std(b) > 1e-6:
            res['contour_corr'] = round(float(np.corrcoef(a, b)[0, 1]), 3)
    return res
