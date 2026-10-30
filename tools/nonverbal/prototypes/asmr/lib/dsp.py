"""
Small numpy-only DSP toolkit for ASMR-grade procedural foley prototypes.

Design rules (because ASMR lives on transients):
  * every filter here is CAUSAL (no zero-phase FFT masks that pre-ring before a click)
  * IIR filters are applied exactly in the frequency domain: the complex response
    H(e^jw) of the biquad is sampled on a zero-padded FFT grid, which equals
    lfilter() up to the (padded-away) circular tail.
  * modal resonators are closed-form damped sinusoids, so there is no
    per-sample Python loop except inside a contact (a few hundred samples).
"""
import wave

import numpy as np

SR = 48000
TAU = 2 * np.pi


def t_axis(seconds, sr=SR):
    return np.arange(int(round(seconds * sr))) / sr


def rng_of(seed):
    return seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)


# ---------------------------------------------------------------- filters

def _next_pow2(n):
    return 1 << int(np.ceil(np.log2(max(2, n))))


def biquad_coefs(kind, f0, q=0.707, gain_db=0.0, sr=SR):
    """RBJ audio-EQ-cookbook biquads. Returns (b, a) with a[0] == 1."""
    w0 = TAU * min(f0, 0.49 * sr) / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2 * q)
    A = 10 ** (gain_db / 40)
    if kind == 'lp':
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'hp':
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'bp':  # constant 0 dB peak gain
        b = [alpha, 0, -alpha]; a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == 'peak':
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]; a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == 'lowshelf':
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sq), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sq)]
        a = [(A + 1) + (A - 1) * cw + sq, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sq]
    elif kind == 'highshelf':
        sq = 2 * np.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sq), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sq)]
        a = [(A + 1) - (A - 1) * cw + sq, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sq]
    else:
        raise ValueError(kind)
    b, a = np.array(b, float), np.array(a, float)
    return b / a[0], a / a[0]


def _H(b, a, n_fft, sr=SR):
    z = np.exp(-1j * TAU * np.fft.rfftfreq(n_fft, 1 / sr) / sr)
    num = b[0] + b[1] * z + b[2] * z * z
    den = a[0] + a[1] * z + a[2] * z * z
    return num / den


def filt(x, *stages, tail=0.25, sr=SR):
    """Apply a cascade of biquads, e.g. filt(x, ('hp', 200), ('peak', 3000, 2, 6)).
    Exact causal IIR response (frequency-sampled with zero padding)."""
    x = np.asarray(x, float)
    n = len(x)
    n_fft = _next_pow2(n + int(tail * sr))
    X = np.fft.rfft(x, n_fft)
    for st in stages:
        kind, f0 = st[0], st[1]
        q = st[2] if len(st) > 2 else 0.707
        g = st[3] if len(st) > 3 else 0.0
        X *= _H(*biquad_coefs(kind, f0, q, g, sr), n_fft, sr)
    return np.fft.irfft(X, n_fft)[:n]


def onepole_lp(x, fc, sr=SR):
    """First-order causal low-pass (exact, frequency domain)."""
    n_fft = _next_pow2(len(x) + int(0.05 * sr))
    p = np.exp(-TAU * fc / sr)
    z = np.exp(-1j * TAU * np.fft.rfftfreq(n_fft, 1 / sr) / sr)
    return np.fft.irfft(np.fft.rfft(x, n_fft) * (1 - p) / (1 - p * z), n_fft)[:len(x)]


def lfilter(b, a, x):
    """Direct-form II transposed, pure python loop (only for short, time-varying use)."""
    b = np.asarray(b, float); a = np.asarray(a, float)
    y = np.zeros_like(x)
    z1 = z2 = 0.0
    b0, b1, b2 = b; a1, a2 = a[1], a[2]
    for i, xi in enumerate(x):
        yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        y[i] = yi
    return y


def fftconv(x, h):
    n = len(x) + len(h) - 1
    n_fft = _next_pow2(n)
    return np.fft.irfft(np.fft.rfft(x, n_fft) * np.fft.rfft(h, n_fft), n_fft)[:n]


# ---------------------------------------------------------------- sources

def white(n, seed=0):
    return rng_of(seed).standard_normal(n)


def colored(n, slope_db_oct=-3.0, seed=0):
    """Noise with a power slope in dB/octave (-3 = pink, -6 = brown)."""
    X = np.fft.rfft(white(n, seed))
    f = np.maximum(np.fft.rfftfreq(n, 1 / SR), 20.0)
    X *= (f / 1000.0) ** (slope_db_oct / 6.02)
    y = np.fft.irfft(X, n)
    return y / (np.std(y) + 1e-12)


def damped_sines(freqs, decays, amps, seconds, phases=None, onset=0, chirp=None, sr=SR):
    """Sum of exponentially decaying sinusoids (a modal resonator bank's impulse response).
    decays are amplitude decay RATES in 1/s (T60 = 6.91/decay).
    chirp: optional per-mode relative frequency slope sigma (f(t)=f0*(1+sigma*t))."""
    t = np.arange(int(seconds * sr)) / sr
    freqs, decays, amps = map(np.atleast_1d, (freqs, decays, amps))
    ph = np.zeros(len(freqs)) if phases is None else np.atleast_1d(phases)
    out = np.zeros(len(t))
    for k in range(len(freqs)):
        if freqs[k] >= 0.47 * sr or amps[k] == 0:
            continue
        if chirp is None:
            phase = TAU * freqs[k] * t
        else:
            s = np.atleast_1d(chirp)[k] if np.ndim(chirp) else chirp
            phase = TAU * freqs[k] * (t + 0.5 * s * t * t)
        out += amps[k] * np.exp(-decays[k] * t) * np.sin(phase + ph[k])
    return out


# ---------------------------------------------------------------- physical contact

def modal_impact(freqs, decays, gains, v0=1.0, m_hammer=0.005, k=2e7, alpha=1.5, lam=0.2,
                 seconds=1.0, rad=None, mode_mass=0.01, os=8, hammer_click=0.0, sr=SR):
    """
    Hunt-Crossley nonlinear contact between a point hammer (mass m_hammer, speed v0)
    and a modal object.  F = k*x^alpha + lam*k*x^alpha*xdot   (x = penetration)
    Contact is integrated sample-by-sample at os*sr only while the hammer touches;
    afterwards each mode rings freely in closed form.
    gains: mode shape value at the contact point (also used as pickup weight).
    rad: radiation weight per mode (default: proportional to frequency, i.e. velocity->pressure
         for a small baffled source).
    Returns (signal, info) with contact duration and peak force.
    """
    freqs = np.asarray(freqs, float); decays = np.asarray(decays, float); gains = np.asarray(gains, float)
    ok = freqs < 0.47 * sr
    freqs, decays, gains = freqs[ok], decays[ok], gains[ok]
    fs = sr * os
    dt = 1.0 / fs
    w = TAU * freqs
    # complex modal state c: q = Im(c) / w  ; exact zero-order-hold impulse invariant update
    zstep = np.exp((-decays + 1j * w) * dt)
    c = np.zeros(len(freqs), complex)
    xh, vh = 0.0, abs(v0)  # hammer displacement (positive = into the object) and velocity
    forces = []
    max_steps = int(0.05 * fs)
    started = False
    for i in range(max_steps):
        q = np.sum(gains * c.imag / w) / mode_mass  # object surface displacement under hammer
        x = xh - q
        if x > 0:
            started = True
            # velocity of surface (approx from complex state derivative)
            qd = np.sum(gains * (c * (-decays + 1j * w)).imag / w) / mode_mass
            xd = vh - qd
            F = k * x ** alpha * (1 + lam * xd)
            F = max(F, 0.0)
        else:
            F = 0.0
            if started and vh < 0:
                break
        forces.append(F)
        vh -= F / m_hammer * dt
        xh += vh * dt
        c = c * zstep + gains * F * dt
    forces = np.array(forces)
    n_contact = len(forces)
    # downsample contact force to sr for the click component
    # free ringing from the post-contact state
    n = int(seconds * sr)
    t = np.arange(n) / sr
    t0 = n_contact * dt
    if rad is None:
        rad = freqs / 1000.0
    # contributions during contact: re-simulate output at audio rate by integrating force
    # (convolve the force with each mode's impulse response) — done exactly via FFT below.
    f_audio = np.add.reduceat(forces, np.arange(0, n_contact, os)) * dt if n_contact else np.zeros(1)
    h = np.zeros(n)
    for kk in range(len(freqs)):
        h += rad[kk] * gains[kk] * np.exp(-decays[kk] * t) * np.sin(w[kk] * t)
    y = fftconv(f_audio, h)[:n] / mode_mass
    if hammer_click:
        # pressure radiated by the hammer's own acceleration (~ dF/dt for a small rigid body)
        dF = np.diff(np.concatenate([[0], f_audio, [0]]))
        click = np.zeros(n)
        click[:len(dF)] = dF
        y = y + hammer_click * click * np.max(np.abs(y)) / (np.max(np.abs(dF)) + 1e-12)
    info = {'contact_ms': n_contact * dt * 1e3, 'peak_force': float(forces.max()) if n_contact else 0.0}
    return y, info


# ---------------------------------------------------------------- helpers

def env_adsr(n, a=0.002, d=0.05, s=0.0, r=0.0, sr=SR):
    e = np.zeros(n)
    na = max(1, int(a * sr)); nd = max(1, int(d * sr))
    e[:na] = np.linspace(0, 1, na, endpoint=False)
    m = min(n - na, nd)
    if m > 0:
        e[na:na + m] = s + (1 - s) * np.exp(-np.arange(m) / (nd / 5))
    if na + nd < n:
        e[na + nd:] = s
    return e


def place(buf, at, x, gain=1.0, sr=SR):
    """Add mono x into mono buf at time `at` (seconds), sub-sample accurate (linear fractional)."""
    pos = at * sr
    i = int(np.floor(pos))
    frac = pos - i
    if frac > 1e-6:  # fractional delay via 2-tap linear interp: y[n] = (1-f) x[n] + f x[n-1]
        x = np.concatenate([x, [0.0]])
        x = x * (1 - frac) + np.concatenate([[0.0], x[:-1]]) * frac
    if i < 0:
        x = x[-i:]; i = 0
    m = min(len(x), len(buf) - i)
    if m > 0:
        buf[i:i + m] += gain * x[:m]
    return buf


def fade(x, fin=0.0005, fout=0.01, sr=SR):
    x = x.copy()
    a, b = int(fin * sr), int(fout * sr)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def normalize(x, peak=0.89):
    return x * peak / (np.max(np.abs(x)) + 1e-12)


def write_wav24(path, x, sr=SR):
    """Write mono or stereo float audio as 24-bit PCM WAV WITHOUT saturation (peak-normalize only)."""
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    x = np.clip(x, -1, 1 - 2 ** -23)
    pcm = np.round(x * (2 ** 23 - 1)).astype('<i4')
    b = pcm.astype('<i4').view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(3); w.setframerate(sr)
        w.writeframes(b)


def read_wav(path):
    """Read 16/24/32-bit PCM WAV -> float array (n, ch), sr."""
    with wave.open(str(path), 'rb') as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, '<i2').astype(float) / 32768
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(float) / (1 << 23)
    elif sw == 4:
        x = np.frombuffer(raw, '<i4').astype(float) / 2 ** 31
    else:
        raise ValueError(sw)
    return x.reshape(-1, ch), sr


def resample(x, sr_in, sr_out):
    """Band-limited FFT resampling (fine for analysis and HRIRs)."""
    if sr_in == sr_out:
        return x
    n_out = int(round(len(x) * sr_out / sr_in))
    X = np.fft.rfft(x, axis=0)
    m = n_out // 2 + 1
    Y = np.zeros((m,) + X.shape[1:], complex)
    k = min(m, X.shape[0])
    Y[:k] = X[:k]
    return np.fft.irfft(Y, n_out, axis=0) * (n_out / len(x))
