"""
Score-first audio engine prototype (numpy only, no samples).

What the repo's synth.py lacks for 音ハメ tracks, and what this file adds:
  TempoMap      bars/steps -> seconds (piecewise tempo), the single source of truth
  step()        step-sequencer strings ("x..x" / velocity digits) -> events
  kick/snare/clap/hat/crash    drum synthesis
  saw/pulse additive voices with a time-varying low-pass (bass, lead, pad)
  adsr()        amplitude envelopes with gate length
  pingpong()    tempo-synced delay
  duck()        kick-keyed sidechain gain curve
  Bus / master  per-track gain+pan, sends, glue saturation, look-ahead limiter
"""
import wave

import numpy as np

SR = 48000
TAU = 2 * np.pi


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


def _t(sec):
    return np.arange(int(round(sec * SR))) / SR


# ---------------------------------------------------------------- tempo map
class TempoMap:
    """segments: [(start_beat, bpm), ...]; offset = seconds of beat 0."""

    def __init__(self, bpm, offset=0.0, beats_per_bar=4, steps_per_beat=4, segments=None):
        self.segments = segments or [(0.0, float(bpm))]
        self.offset = offset
        self.bpb = beats_per_bar
        self.spb = steps_per_beat

    def beat_to_sec(self, beat):
        t, prev_b, prev_bpm = self.offset, 0.0, self.segments[0][1]
        for b0, bpm in self.segments[1:]:
            if beat <= b0:
                break
            t += (b0 - prev_b) * 60.0 / prev_bpm
            prev_b, prev_bpm = b0, bpm
        return t + (beat - prev_b) * 60.0 / prev_bpm

    def t(self, bar, step=0.0):
        return self.beat_to_sec(bar * self.bpb + step / self.spb)

    def step_sec(self, bar=0):
        return 60.0 / self.segments[0][1] / self.spb


def step(pattern, tm, bar):
    """'x' = 1.0, digits 1-9 = velocity/9, 'o' = flag (open hat), '.' = rest."""
    ev = []
    for i, ch in enumerate(pattern.replace(' ', '').replace('|', '')):
        if ch == '.':
            continue
        vel = 1.0 if ch in 'xo' else int(ch) / 9.0
        ev.append((tm.t(bar, i), vel, ch))
    return ev


# ---------------------------------------------------------------- helpers
def fft_filter(x, lo=None, hi=None, order=2):
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = np.ones_like(f)
    if lo:
        g /= np.sqrt(1 + (lo / np.maximum(f, 1)) ** (2 * order))
    if hi:
        g /= np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(spec * g, n)


def bandnoise(sec, lo, hi, seed=0, order=2):
    x = np.random.default_rng(seed).standard_normal(int(round(sec * SR)))
    x = fft_filter(x, lo, hi, order)
    return x / (np.abs(x).max() + 1e-9)


def fade_edges(x, a=0.001, r=0.004):
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    x = x.copy()
    x[:na] *= np.linspace(0, 1, na)
    x[-nr:] *= np.linspace(1, 0, nr)
    return x


def adsr(n, gate, a=0.005, d=0.1, s=0.7, r=0.08):
    """n samples; gate = seconds the key is held."""
    t = np.arange(n) / SR
    env = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    held = t <= gate
    g_val = np.interp(gate, t, env) if n else 0
    rel = g_val * np.exp(-(t - gate) / max(r, 1e-6))
    return np.where(held, env, rel)


# ---------------------------------------------------------------- drums
def kick(vel=1.0, sec=0.42, tone=48.0):
    t = _t(sec)
    f = tone + 115 * np.exp(-t / 0.030) + 520 * np.exp(-t / 0.0022)
    body = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.15)
    click = bandnoise(sec, 1500, 9000, seed=3) * np.exp(-t / 0.0030) * 0.75
    x = np.tanh(2.2 * (body + click)) * vel
    return fade_edges(x, 0.0005, 0.01)


def snare(vel=1.0, sec=0.32, seed=5):
    t = _t(sec)
    f = 182 * (1 + 0.25 * np.exp(-t / 0.01))
    tone = 0.55 * np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.05)
    tone += 0.25 * np.sin(TAU * 331 * t) * np.exp(-t / 0.03)
    nz = bandnoise(sec, 1400, 9500, seed) * np.exp(-t / 0.10)
    return fade_edges(np.tanh(1.6 * (tone + 0.85 * nz)) * vel, 0.0005, 0.01)


def clap(vel=1.0, sec=0.32, seed=9):
    t = _t(sec)
    nz = bandnoise(sec, 900, 6000, seed)
    env = np.zeros_like(t)
    for k, d in enumerate((0.0, 0.009, 0.018)):
        env += np.where(t >= d, np.exp(-(t - d) / 0.004), 0) * (0.8 + 0.1 * k)
    env += np.where(t >= 0.024, np.exp(-(t - 0.024) / 0.09), 0) * 0.7
    return fade_edges(nz * env * vel * 0.8, 0.0005, 0.01)


_METAL = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0])


def hat(vel=1.0, open_=False, seed=0):
    sec = 0.45 if open_ else 0.09
    t = _t(sec)
    x = sum(np.sign(np.sin(TAU * f * 1.42 * t + k)) for k, f in enumerate(_METAL))
    x = fft_filter(x, 7000, 15000, 3) + 0.4 * bandnoise(sec, 8000, 16000, seed)
    x /= np.abs(x).max() + 1e-9
    env = np.exp(-t / (0.19 if open_ else 0.016))
    return fade_edges(x * env * vel, 0.0005, 0.006)


def crash(vel=1.0, sec=2.4, seed=11):
    t = _t(sec)
    m = sum(np.sign(np.sin(TAU * f * 2.17 * t + k)) for k, f in enumerate(_METAL))
    x = 0.6 * fft_filter(m, 4500, 14000, 2) / 6 + bandnoise(sec, 3000, 15000, seed)
    x /= np.abs(x).max() + 1e-9
    env = np.exp(-t / 0.9) * (1 - np.exp(-t / 0.002))
    return fade_edges(x * env * vel, 0.0005, 0.05)


# ---------------------------------------------------------------- tonal voices
def additive(freq, sec, amp_k, cutoff, res=0.0, kmax=200, vib=None, seed=0):
    """Band-limited additive oscillator. freq: Hz (scalar); cutoff: array or scalar (Hz),
    a 12 dB/oct low-pass evaluated per harmonic, plus a resonant bump at the cutoff."""
    t = _t(sec)
    inst = np.full_like(t, freq) if vib is None else freq * vib(t)
    phase = TAU * np.cumsum(inst) / SR + np.random.default_rng(seed).uniform(0, TAU)
    cutoff = np.broadcast_to(np.asarray(cutoff, float), t.shape)
    out = np.zeros_like(t)
    for k in range(1, kmax + 1):
        fk = k * freq
        if fk > 17000:
            break
        a = amp_k(k)
        if a == 0:
            continue
        g = 1 / (1 + (fk / cutoff) ** 2)
        if res:
            g = g + res * np.exp(-((fk - cutoff) / (0.18 * cutoff)) ** 2)
        out += a * g * np.sin(k * phase)
    return out


saw_k = lambda k: 1.0 / k  # noqa: E731


def pulse_k(width):
    return lambda k: np.sin(np.pi * k * width) / k


def bass(midi, gate, vel=1.0):
    sec = gate + 0.12
    f0 = float(hz(midi))
    t = _t(sec)
    cut = 160 + 1500 * vel * np.exp(-t / 0.075)
    x = additive(f0, sec, saw_k, cut, res=0.35, kmax=160)
    x = 0.65 * x / (np.abs(x).max() + 1e-9) + 0.55 * np.sin(TAU * f0 * t)
    x = np.tanh(2.6 * x)  # harmonics so it survives phone speakers
    return x * adsr(len(t), gate, a=0.002, d=0.25, s=0.75, r=0.035) * vel


def lead(midi, gate, vel=1.0, seed=0):
    sec = gate + 0.35
    f0 = float(hz(midi))
    t = _t(sec)
    vib = lambda tt: 1 + 0.0065 * np.sin(TAU * 5.6 * tt) * np.clip((tt - 0.22) / 0.2, 0, 1)  # noqa
    cut = 1100 + 5200 * vel * np.exp(-t / 0.11)
    x = additive(f0, sec, pulse_k(0.28), cut, res=0.2, kmax=60, vib=vib, seed=seed)
    x /= np.abs(x).max() + 1e-9
    glass = np.sin(TAU * 2 * f0 * t) * np.exp(-t / 0.07) * 0.35  # transient "tick" = sync anchor
    return (x + glass) * adsr(len(t), gate, a=0.003, d=0.16, s=0.5, r=0.12) * vel


def pad(midis, sec, attack=0.3, release=0.5, cutoff=1300):
    t = _t(sec + release)
    out = np.zeros_like(t)
    for i, m in enumerate(midis):
        for j, cents in enumerate((-9, 0, 9)):
            f = float(hz(m)) * 2 ** (cents / 1200)
            out += additive(f, sec + release, saw_k, cutoff * (1 + 0.15 * np.sin(TAU * 0.3 * t + i)),
                            kmax=40, seed=i * 3 + j)
    out /= np.abs(out).max() + 1e-9
    return out * adsr(len(t), sec, a=attack, d=0.5, s=0.85, r=release)


def pop(vel=1.0, f0=900, f1=260, sec=0.09, seed=21):
    """ASMR-ish foley: wet 'pop/squish' of the blob landing."""
    t = _t(sec)
    f = f1 + (f0 - f1) * np.exp(-t / 0.012)
    x = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.025)
    x += 0.35 * bandnoise(sec, 1500, 6000, seed) * np.exp(-t / 0.008)
    return fade_edges(x * vel, 0.0003, 0.01)


def whoosh(sec, rise=True, seed=31):
    t = np.linspace(0, 1, int(sec * SR))
    lo, hi = bandnoise(sec, 300, 2500, seed), bandnoise(sec, 2500, 12000, seed + 1)
    w = t if rise else 1 - t
    return (lo * (1 - w) + hi * w) * (w ** 2.2 if rise else (1 - t) ** 3)


def boing(sec=0.5, f=320):
    t = _t(sec)
    inst = f * (1 + 0.35 * np.exp(-t / 0.18) * np.sin(TAU * 11 * t)) * (1 + 0.6 * t)
    return fade_edges(np.sin(TAU * np.cumsum(inst) / SR) * np.exp(-t / 0.2), 0.002, 0.02)


# ---------------------------------------------------------------- fx
def pingpong(mono, delay, fb=0.38, taps=6, damp=4500):
    n = len(mono)
    out = np.zeros((n, 2))
    d = int(round(delay * SR))
    x = mono
    for k in range(1, taps + 1):
        x = fft_filter(x, 250, damp, 1)
        s = k * d
        if s >= n:
            break
        out[s:, k % 2] += x[:n - s] * fb ** k
    return out


def duck(n, kick_times, depth=0.7, attack=0.004, release=0.17):
    """Sidechain gain curve keyed on kick onsets (min over all kicks)."""
    t = np.arange(n) / SR
    g = np.ones(n)
    for tk in kick_times:
        i0 = int(tk * SR - attack * SR)
        i1 = min(n, int((tk + 6 * release) * SR))
        if i1 <= max(i0, 0):
            continue
        tt = t[max(i0, 0):i1] - tk
        e = np.where(tt < 0, 1 + tt / attack, np.exp(-tt / release))
        g[max(i0, 0):i1] = np.minimum(g[max(i0, 0):i1], 1 - depth * np.clip(e, 0, 1))
    return g


class Bus:
    def __init__(self, n):
        self.buf = np.zeros((n, 2))

    def add(self, at, mono, pan=0.0, gain=1.0):
        i = int(round(at * SR))
        if i < 0:
            mono, i = mono[-i:], 0
        m = min(len(mono), len(self.buf) - i)
        if m <= 0:
            return
        a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        self.buf[i:i + m, 0] += mono[:m] * np.cos(a) * gain
        self.buf[i:i + m, 1] += mono[:m] * np.sin(a) * gain


def sliding_min_forward(g, w):
    """out[n] = min(g[n : n+w]) via doubling."""
    out = g.copy()
    span = 1
    while span < w:
        s = min(span, w - span)
        sh = np.concatenate([out[s:], np.full(s, out[-1])])
        out = np.minimum(out, sh)
        span += s
    return out


def limiter(x, ceiling_db=-1.0, lookahead=0.003, release=0.08):
    """Look-ahead brickwall: forward min-filter + release + backward box (gain <= needed)."""
    ceil = 10 ** (ceiling_db / 20)
    peak = np.abs(x).max(axis=1)
    g = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    w = max(1, int(lookahead * SR))
    g = sliding_min_forward(g, w)
    a = np.exp(-1 / (release * SR))
    out = np.empty_like(g)
    y = 1.0
    for i, v in enumerate(g):  # release (python loop; ~0.3 s for 10 s of audio)
        y = v if v < y else v + (y - v) * a
        out[i] = y
    k = np.ones(w) / w
    sm = np.convolve(out, k)[:len(out)]
    sm[:w] = out[:w]
    return x * sm[:, None], 1 - sm.min()


def write_wav16(path, buf):
    rng = np.random.default_rng(0)
    d = (rng.random(buf.shape) - rng.random(buf.shape)) / 32768  # TPDF dither
    pcm = (np.clip(buf + d, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
