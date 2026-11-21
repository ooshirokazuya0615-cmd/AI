"""Five procedural non-verbal voices (numpy only, no samples).

A  babble   : formant-synthesis gibberish (Animalese/Simlish-like) with emotional prosody
B  suikin   : 'instrument voice' - the heroine speaks in glass/music-box/water tones (melodic intonation)
C  robot    : R2-D2-style chirps/trills/buzz, with a faint organic 'coo' layer (Burtt's human input)
D  creature : soft breathy creature (noise-excited formants, purr, whimper, growl, gasp)
E  iron     : rusty-iron villain (inharmonic bar partials, tritone dyads, creak, scrape)
"""
import numpy as np

from dsp import SR, TAU, smooth, formant_mag, shaped_noise, band_noise, bpf, hpf
from prosody import controls, plan_utterance, make_lexicon, EMO

VOWELS = {  # adult male averages (Peterson & Barney style), scaled per character
    'a': ([730, 1090, 2440, 3400], [90, 110, 160, 250]),
    'i': ([270, 2290, 3010, 3700], [60, 100, 170, 250]),
    'u': ([300, 870, 2240, 3300], [60, 90, 150, 250]),
    'e': ([530, 1840, 2480, 3500], [70, 100, 160, 250]),
    'o': ([570, 840, 2410, 3300], [80, 90, 160, 250]),
}
NASAL = {'m': ([280, 1100, 2300, 3300], [60, 150, 200, 300]),
         'n': ([280, 1500, 2500, 3400], [60, 150, 200, 300])}
LOCUS_F2 = {'p': 900, 'b': 900, 't': 1800, 'd': 1800, 'k': 2300, 'g': 2300}
BURST = {'p': (500, 1600), 'b': (400, 1400), 't': (3000, 7500), 'd': (2500, 6000),
         'k': (1500, 3300), 'g': (1400, 3000)}


def _fill_rows(M, mask):
    """interpolate rows of M where mask is False"""
    idx = np.arange(len(M))
    if not mask.any():
        return M
    for j in range(M.shape[1]):
        M[:, j] = np.interp(idx, idx[mask], M[mask, j])
    return M


def _rms(x):
    return np.sqrt(np.mean(x ** 2) + 1e-20)


def additive(f0, amp_fn, fmax=11000.0, phase0=None, rng=None, ratios=None):
    """band-limited additive synthesis. amp_fn(k, fk) -> per-sample amplitude of harmonic k
    (ratios: optional list of partial ratios instead of 1..K)"""
    ph = TAU * np.cumsum(f0) / SR
    out = np.zeros(len(f0))
    rng = rng or np.random.default_rng(0)
    ks = ratios if ratios is not None else range(1, int(fmax / max(f0.min(), 30)) + 1)
    for k in ks:
        fk = k * f0
        if fk.min() >= fmax:
            break
        taper = np.clip((fmax - fk) / (0.15 * fmax), 0, 1)
        a = amp_fn(k, fk) * taper
        out += a * np.sin(k * ph + rng.uniform(0, TAU))
    return out


def adsr(n, a, d_tau, sr=SR):
    t = np.arange(n) / sr
    e = np.exp(-t / d_tau)
    na = max(1, int(a * sr))
    e[:na] *= np.linspace(0, 1, na)
    return e


# =================================================================== A. formant babble
class Babble:
    name = 'babble'
    base_hz = 340.0
    fscale = 1.42
    cons = ['p', 'b', 'm', 'n', 't', 'w', 'y', 'h', '', '', 'k']
    vowels = ['a', 'i', 'u', 'e', 'o']
    interj = {'happy': [('y', 'a'), ('', 'i')], 'sad': [('', 'u'), ('', 'u')],
              'angry': [('m', 'u'), ('n', 'a')], 'surprised': [('h', 'e')]}

    def __init__(self, seed=7):
        self.lex = make_lexicon(np.random.default_rng(seed), self.cons, self.vowels, 10)

    def plan(self, emotion, rng):
        return plan_utterance(emotion, rng, self.lex, self.interj)

    def render(self, plan, rng):
        P = plan.params
        C = controls(plan, self.base_hz, rng)
        n = C['n']
        F = np.zeros((n, 4))
        Bw = np.zeros((n, 4))
        setm = np.zeros(n, bool)
        vamp = C['amp'].copy()
        events = []   # (start_sample, kind, args)
        fs = self.fscale * P['fshift']
        for s in plan.syls:
            a, b = int(s.t * SR), min(n, int((s.t + s.d) * SR))
            VF, VB = VOWELS[s.vowel]
            VF = np.array(VF) * fs
            VB = np.array(VB) * np.sqrt(self.fscale)
            F[a:b] = VF
            Bw[a:b] = VB
            setm[a:b] = True
            c = s.cons
            L = b - a
            if c in NASAL:
                m = min(L // 2, int(0.045 * SR))
                F[a:a + m] = np.array(NASAL[c][0]) * fs
                Bw[a:a + m] = np.array(NASAL[c][1]) * np.sqrt(self.fscale)
                vamp[a:a + m] *= 0.4
            elif c in BURST:
                voiced = c in 'bdg'
                cl = int((0.012 if voiced else 0.022) * SR)
                cl = min(cl, L // 3)
                vamp[a:a + cl] *= 0.06 if voiced else 0.0
                asp = 0 if voiced else int(0.014 * SR)
                vamp[a + cl:a + cl + asp] *= 0.15
                events.append((a + cl, 'burst', (BURST[c], 0.010, 10 ** (s.amp_db / 20) * (0.35 if voiced else 0.6))))
                if asp:
                    events.append((a + cl + int(0.008 * SR), 'asp', (0.018, 10 ** (s.amp_db / 20) * 0.25)))
                m = min(L // 2, int(0.04 * SR))
                ramp = np.linspace(0, 1, m)[:, None]
                start = np.array([VF[0] * 0.55, LOCUS_F2[c] * fs, VF[2], VF[3]])
                F[a:a + m] = start + (VF - start) * ramp
            elif c in ('w', 'y'):
                g = VOWELS['u' if c == 'w' else 'i'][0]
                m = min(L // 2, int(0.06 * SR))
                ramp = np.linspace(0, 1, m)[:, None]
                start = np.array(g) * fs
                F[a:a + m] = start + (VF - start) * ramp
            elif c == 'h':
                m = min(L // 3, int(0.035 * SR))
                vamp[a:a + m] *= 0.12
                events.append((a, 'asp', (0.035, 10 ** (s.amp_db / 20) * 0.35)))
        F = _fill_rows(F, setm)
        Bw = _fill_rows(Bw, setm)
        sm = int(0.012 * SR)
        for j in range(4):
            F[:, j] = smooth(F[:, j], sm)
        f0 = C['f0']
        tilt = 1.0 + P['tilt']
        rough = P['rough']
        jit = 1 + 0.012 * rough * smooth(rng.standard_normal(n), 24)  # cycle-level jitter when angry
        f0j = f0 * jit
        voiced = additive(f0j, lambda k, fk: k ** -tilt * formant_mag(fk, F, Bw), 10000, rng=rng)
        if rough > 0:
            # period-doubling (subharmonics) + 55 Hz amplitude roughness
            sub = additive(f0j * 0.5, lambda k, fk: (k % 2) * (k ** -tilt) * formant_mag(fk, F, Bw), 10000, rng=rng)
            voiced = voiced + 0.35 * rough * sub
            voiced *= 1 - 0.5 * rough * (0.5 + 0.5 * np.sin(TAU * 55 * C['t'] + 2 * np.sin(TAU * 3 * C['t'])))
        voiced *= vamp
        r_v = _rms(voiced)
        # aspiration noise through the same formants
        def env(times, freqs):
            ii = np.clip((times * SR).astype(int), 0, n - 1)
            g = formant_mag(freqs[None, :], F[ii][:, None, :], Bw[ii][:, None, :])
            return g * (vamp[ii] + 1e-4)[:, None] * (1 / np.sqrt(1 + (400 / np.maximum(freqs, 1)) ** 2))[None, :]
        asp = shaped_noise(n, env, rng)
        out = voiced + P['breath'] * r_v / (_rms(asp) + 1e-12) * asp
        # consonant noise events
        for (i0, kind, args) in events:
            if kind == 'burst':
                (lo, hi), dur, g = args
                m = int(dur * SR)
                x = band_noise(m, lo * fs / 1.2, hi * fs / 1.2, rng) * np.exp(-np.arange(m) / (0.003 * SR))
                x = x / (_rms(x) + 1e-12) * r_v * g * 2.0
            else:
                dur, g = args
                m = int(dur * SR)
                x = band_noise(m, 1200, 6000, rng) * np.hanning(m)
                x = x / (_rms(x) + 1e-12) * r_v * g
            m = min(len(x), n - i0)
            out[i0:i0 + m] += x[:m]
        if plan.gasp:
            g0, gd = plan.gasp
            m = int(gd * SR)
            u = np.linspace(0, 1, m)
            def genv(times, freqs, m=m):
                uu = np.clip(times / gd, 0, 1)[:, None]
                cf = 1800 + 2200 * uu
                return np.exp(-((freqs[None, :] - cf) / 1400) ** 2)
            x = shaped_noise(m, genv, rng) * u ** 1.5 * np.exp(-((u - 0.85) / 0.4) ** 2)
            out[:m] += x / (_rms(x) + 1e-12) * r_v * 0.9
        if plan.sigh:
            s0, sd = plan.sigh
            i0, m = int(s0 * SR), int(sd * SR)
            m = min(m, n - i0)
            def senv(times, freqs, sd=sd):
                uu = np.clip(times / sd, 0, 1)[:, None]
                g = formant_mag(freqs[None, :], (np.array(VOWELS['a'][0]) * fs * (1 - 0.25 * uu))[:, None, :],
                                np.array(VOWELS['a'][1])[None, None, :] * 2.0)
                return g * (1 / np.sqrt(1 + (500 / np.maximum(freqs, 1)) ** 2))[None, :]
            x = shaped_noise(m, senv, rng)
            u = np.linspace(0, 1, m)
            x *= np.sin(np.pi * u) ** 1.2 * (1 - u) ** 0.5
            out[i0:i0 + m] += x / (_rms(x) + 1e-12) * r_v * 0.45
        return out


# =================================================================== B. SUIKIN instrument voice
MAJ_PENT = [0, 2, 4, 7, 9]
MIN_PENT = [0, 3, 5, 7, 10]
TINE = (1.0, 6.267, 17.55)        # music-box comb (cantilever) partial ratios


def tine(f, dur, strike=1.0, decay=0.45, rng=None):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for r, a, tau in zip(TINE, (0.8, 0.30, 0.10), (decay, 0.06, 0.015)):
        if f * r < 18000:
            x += a * np.sin(TAU * f * r * t) * np.exp(-t / tau)
    na = int(0.0015 * SR)
    x[:na] *= np.linspace(0, 1, na)
    return x * strike


def bubble(f, rise=0.5, tau=0.025, dur=None):
    """water-drop / bubble: damped sine with rising (or falling, rise<0) pitch glide"""
    dur = dur or tau * 6
    n = int(dur * SR)
    t = np.arange(n) / SR
    ff = f * (1 + rise * (1 - np.exp(-t / (tau * 1.5))))
    x = np.sin(TAU * np.cumsum(ff) / SR) * np.exp(-t / tau)
    na = int(0.001 * SR)
    x[:na] *= np.linspace(0, 1, na)
    return x


class Suikin:
    name = 'suikin'
    base_hz = 784.0           # G5 - heroine glass bead; whole voice lives above the phone cut
    cons = ['', '']
    vowels = ['a', 'o', 'i']
    interj = {'happy': [('', 'a'), ('', 'i')], 'sad': [('', 'o')], 'angry': [('', 'a')], 'surprised': [('', 'o')]}
    CALL = [0, 2, 7, 4, 9]   # 5-note pentatonic sound-logo / name call (G A D B E)

    def __init__(self, seed=11):
        self.lex = make_lexicon(np.random.default_rng(seed), self.cons, self.vowels, 8)

    def plan(self, emotion, rng):
        return plan_utterance(emotion, rng, self.lex, self.interj)

    def render(self, plan, rng):
        P = plan.params
        emo = plan.emotion
        scale = MAJ_PENT if emo in ('happy', 'surprised') else MIN_PENT
        cands = np.array([o * 12 + d for o in range(-3, 4) for d in scale], float)
        off = -3.0 if emo == 'angry' else 0.0
        last = len(plan.syls) - 1

        def q(p):
            return float(cands[np.argmin(np.abs(cands - (p + off)))])

        notes = []

        def pitch_fn(i, s, p0, p1):
            n0 = q(p0)
            if i == last:
                r = (n0, n0 + (p1 - p0))
            elif emo == 'surprised' and i == 0:
                r = (n0, q(p1 + off))
            else:
                r = (n0, n0 + 0.2 * (p1 - p0))
            notes.append(r[0])
            return r

        C = controls(plan, self.base_hz, rng, pitch_fn=pitch_fn)
        n = C['n']
        f0 = C['f0']
        amp = C['amp']
        bright = 1.0 - P['tilt']                 # happy 1.35, sad 0.45, angry 1.75
        base_h = np.array([1.0, 0.30, 0.13, 0.06, 0.03])
        opening = 0.55 + 0.45 * np.sin(np.pi * C['sph']) ** 0.8   # 'wah' vowel inside each syllable
        def hamp(k, fk):
            return base_h[k - 1] * bright ** (k - 1) * (opening ** (k - 1) if k > 1 else 1.0)
        sus = additive(f0, hamp, 16000, rng=rng, ratios=[1, 2, 3, 4, 5])
        sus += 0.5 * additive(f0 * 2 ** (2.5 / 1200), hamp, 16000, rng=rng, ratios=[1, 2, 3])  # glass shimmer
        if P['rough'] > 0:   # heroine's anger: minor-second cluster -> ~45-50 Hz beating (roughness)
            sus += 0.55 * P['rough'] * additive(f0 * 2 ** (1 / 12), hamp, 16000, rng=rng, ratios=[1, 2, 3])
            sus *= 1 - 0.25 * (0.5 + 0.5 * np.sin(TAU * 13 * C['t']))   # tremolo
        out = sus * amp
        r_v = _rms(out)
        strike = {'happy': 0.9, 'sad': 0.30, 'angry': 1.6, 'surprised': 1.0}[emo]
        decay = {'happy': 0.35, 'sad': 0.9, 'angry': 0.25, 'surprised': 0.4}[emo]
        for i, s in enumerate(plan.syls):
            i0 = int(s.t * SR)
            f_on = self.base_hz * 2 ** (notes[i] / 12) if i < len(notes) else f0[i0]
            x = tine(f_on, decay * 4, strike * 10 ** (s.amp_db / 20), decay)
            m = min(len(x), n - i0)
            out[i0:i0 + m] += x[:m] * r_v * 1.2
            i1 = int((s.t + s.d) * SR)
            fe = f0[min(i1, n - 1)]
            if emo == 'happy' and (rng.random() < 0.35 or i == last):
                x = bubble(fe * 2, rise=0.6, tau=0.022) * r_v * 1.4
            elif emo == 'surprised' and (i == 0 or i == last):
                x = bubble(fe * 2, rise=0.9, tau=0.03) * r_v * 1.6
                i1 = int((s.t + 0.6 * s.d) * SR) if i == 0 else i1
            elif emo == 'sad' and i % 2 == 1:
                x = bubble(fe * 1.5, rise=-0.25, tau=0.05) * r_v * 0.8       # falling 'tear drop'
            elif emo == 'angry' and s.stress:
                m2 = int(0.004 * SR)
                x = band_noise(m2 * 4, 3000, 9000, rng)[:m2 * 4] * np.exp(-np.arange(m2 * 4) / m2)
                x = x / (_rms(x) + 1e-12) * r_v * 1.5                         # glass 'crack' tick
                i1 = i0
            else:
                continue
            m = min(len(x), n - i1)
            if m > 0:
                out[i1:i1 + m] += x[:m]
        if plan.gasp:   # surprised: rising grace-note arpeggio + air through glass
            gd = plan.gasp[1]
            n0 = notes[0] if notes else 0
            for j, dn in enumerate((-9, -5, -2)):
                i0 = int(j * gd / 3 * SR)
                x = tine(self.base_hz * 2 ** ((n0 + dn) / 12), 0.5, 0.6, 0.12)
                m = min(len(x), n - i0)
                out[i0:i0 + m] += x[:m] * r_v
            m = int(gd * SR)
            u = np.linspace(0, 1, m)
            x = band_noise(m, 2500, 8000, rng) * u ** 2
            out[:m] += x / (_rms(x) + 1e-12) * r_v * 0.25
        if plan.sigh:   # sad: soft breath across a bottle mouth, falling
            s0, sd = plan.sigh
            i0, m = int(s0 * SR), int(sd * SR)
            m = min(m, n - i0)
            u = np.linspace(0, 1, m)
            def senv(times, freqs):
                uu = np.clip(times / sd, 0, 1)[:, None]
                cf = self.base_hz * 2 ** (-5 / 12) * (1 - 0.2 * uu)
                return 1 / (1 + ((freqs[None, :] - cf) / 40) ** 2)
            x = shaped_noise(m, senv, rng) * np.sin(np.pi * u) ** 1.5
            out[i0:i0 + m] += x / (_rms(x) + 1e-12) * r_v * 0.35
        return out

    def call(self, rng, tempo=0.16, harmonize=False):
        """the 5-note sound logo, spoken in the heroine's voice"""
        n = int((tempo * len(self.CALL) + 1.6) * SR)
        out = np.zeros(n)
        for i, d in enumerate(self.CALL):
            f = self.base_hz * 2 ** (d / 12)
            i0 = int(i * tempo * SR)
            dur = 1.4 if i == len(self.CALL) - 1 else tempo * 1.6
            m = int(dur * SR)
            t = np.arange(m) / SR
            env = np.minimum(1, t / 0.01) * np.exp(-t / (0.5 if i == len(self.CALL) - 1 else 0.12))
            ff = f * (1 + 0.004 * np.sin(TAU * 5.5 * t) * np.clip(t / 0.3, 0, 1))
            x = additive(ff, lambda k, fk: [1, .3, .12, .05][k - 1], 16000, rng=rng, ratios=[1, 2, 3, 4]) * env
            x += tine(f, dur, 0.9, 0.5)[:m]
            if harmonize and i == len(self.CALL) - 1:
                for h in (-12, -5, 4):
                    x += 0.5 * tine(f * 2 ** (h / 12), dur, 0.8, 0.9)[:m]
            out[i0:i0 + m] += x[:n - i0]
        b = bubble(self.base_hz * 2 ** (9 / 12) * 2, 0.7, 0.03)
        i0 = int((len(self.CALL) - 1) * tempo * SR + 0.05 * SR)
        out[i0:i0 + len(b)] += 0.6 * b
        return out


# =================================================================== C. robot
def wavetable(f, kind, fmax=12000.0, rng=None):
    if kind == 'sine':
        return additive(f, lambda k, fk: 1.0, fmax, rng=rng, ratios=[1])
    if kind == 'tri':
        return additive(f, lambda k, fk: (k % 2) / k ** 2, fmax, rng=rng)
    if kind == 'square':
        return additive(f, lambda k, fk: (k % 2) / k, fmax, rng=rng)
    if kind == 'saw':
        return additive(f, lambda k, fk: 1 / k, fmax, rng=rng)
    if kind == 'softsaw':
        return additive(f, lambda k, fk: 1 / k ** 1.5, fmax, rng=rng)
    raise ValueError(kind)


class Robot:
    name = 'robot'
    base_hz = 1250.0
    cons = ['', 'b', 'd']
    vowels = ['u', 'o', 'i']
    interj = {}

    def __init__(self, seed=5):
        self.lex = make_lexicon(np.random.default_rng(seed), self.cons, self.vowels, 8)
        self.coo = Babble(seed=3)
        self.coo.base_hz = 560.0
        self.coo.fscale = 1.6

    def plan(self, emotion, rng):
        return plan_utterance(emotion, rng, self.lex, self.interj)

    def _seg(self, n, i0, x, gain):
        m = min(len(x), n - i0)
        if m > 0:
            return slice(i0, i0 + m), x[:m] * gain
        return None, None

    def render(self, plan, rng):
        P = plan.params
        emo = plan.emotion
        n = int(plan.length * SR)
        out = np.zeros(n)
        B = self.base_hz
        last = len(plan.syls) - 1
        def env(m, a=0.004, r=0.02):
            t = np.arange(m) / SR
            return np.minimum(1, t / a) * np.minimum(1, (m / SR - t) / r)
        for i, s in enumerate(plan.syls):
            m = int(s.d * SR)
            t = np.arange(m) / SR
            u = t / s.d
            g = 10 ** (s.amp_db / 20)
            p0, p1 = s.p0, s.p0 + 2.0 * (s.p1 - s.p0)
            if emo == 'happy':
                if rng.random() < 0.3 and i != last:
                    steps = int(s.d * 22) + 1
                    notes = p0 + rng.uniform(-4, 4, steps)
                    st_ = np.repeat(notes, int(np.ceil(m / steps)))[:m]
                    f = B * 2 ** (smooth(st_, int(0.003 * SR)) / 12)
                else:
                    f = B * 2 ** ((p0 + (p1 - p0) * (1 - (1 - u) ** 2)) / 12)
                f *= 2 ** (0.15 * np.sin(TAU * 9 * t) / 12)
                x = wavetable(f, 'tri', rng=rng) * env(m, 0.003, 0.015)
            elif emo == 'sad':
                f = 0.5 * B * 2 ** ((p0 + (p1 - p0) * u ** 1.5) / 12) * 2 ** (0.5 * np.sin(TAU * 5 * t) / 12)
                x = wavetable(f, 'softsaw', rng=rng) * env(m, 0.05, 0.12)
                x = bpf(x, 400, 3000, 1)
            elif emo == 'angry':
                if s.stress or i == last:
                    f = 150 * 2 ** ((s.p0 - s.p1) * u * 0.1 / 12) * np.ones(m)
                    x = additive(f, lambda k, fk: k ** -0.8 * formant_mag(fk, [1100, 2300, 3600], [250, 300, 400]),
                                 9000, rng=rng)
                    x *= 1 - 0.7 * (0.5 + 0.5 * np.sin(TAU * 45 * t))
                    x += 0.25 * np.std(x) * band_noise(m, 1000, 4000, rng)
                    x *= env(m, 0.002, 0.01)
                else:
                    f = 0.7 * B * 2 ** ((p0 + (p1 - p0) * u ** 2) / 12)
                    x = wavetable(f, 'square', 9000, rng=rng) * env(m, 0.002, 0.01)
                g *= 1.4
            else:  # surprised
                if i == 0:
                    sweep = np.clip(u / 0.6, 0, 1)
                    f = 700 * (3200 / 700) ** (sweep ** 1.3)
                    f *= 2 ** (0.6 * np.sin(TAU * 11 * t) * (u > 0.6) / 12)
                    x = wavetable(f, 'tri', rng=rng) * env(m, 0.004, 0.04)
                else:
                    f = B * 2 ** ((p0 + (p1 - p0) * (1 - (1 - u) ** 2)) / 12)
                    x = wavetable(f, 'tri', rng=rng) * env(m)
            x = x / (np.abs(x).max() + 1e-9)
            sl, y = self._seg(n, int(s.t * SR), x, g)
            if sl is not None:
                out[sl] += y
        if plan.gasp:   # double bleep
            for j in range(2):
                m = int(0.045 * SR)
                x = wavetable(np.full(m, 2400.0), 'tri', rng=rng) * env(m, 0.002, 0.008)
                sl, y = self._seg(n, int(j * 0.07 * SR), x / np.abs(x).max(), 0.6)
                out[sl] += y
        if plan.sigh:   # long low 'bwoooo'
            s0, sd = plan.sigh
            m = int(sd * 1.3 * SR)
            t = np.arange(m) / SR
            f = 620 * (0.5 ** (t / (sd * 1.3))) * 2 ** (0.6 * np.sin(TAU * 4.5 * t) / 12)
            x = bpf(wavetable(f, 'softsaw', rng=rng), 350, 3000, 1) * env(m, 0.08, 0.3)
            sl, y = self._seg(n, int(s0 * SR), x / np.abs(x).max(), 0.35)
            if sl is not None:
                out[sl] += y
        # organic layer: Burtt mixed his own baby-talk under the synth tones
        coo = self.coo.render(plan, rng)
        out[:len(coo)] += coo[:n] / (_rms(coo) + 1e-12) * _rms(out) * 0.22
        return out


# =================================================================== D. soft creature
class Creature(Babble):
    name = 'creature'
    base_hz = 560.0
    fscale = 1.65
    cons = ['', '', 'h', 'm']
    vowels = ['u', 'o', 'a', 'u']
    interj = {'happy': [('h', 'u'), ('h', 'u'), ('h', 'u')], 'sad': [('', 'u')],
              'angry': [('h', 'a')], 'surprised': [('h', 'o')]}

    def __init__(self, seed=21):
        self.lex = make_lexicon(np.random.default_rng(seed), self.cons, self.vowels, 8)

    def render(self, plan, rng):
        P = dict(plan.params)
        emo = plan.emotion
        n = int(plan.length * SR)
        C = controls(plan, self.base_hz, rng)
        t = C['t']
        f0 = C['f0']
        amp = C['amp'].copy()
        fs = self.fscale * P['fshift']
        if emo == 'angry':
            # growl: low compressed-contour f0, bigger (lower) formants - Morton's harsh/low hostile call
            f0 = 150 * 2 ** ((C['st'] - P['base']) * 0.4 / 12)
            fs = 1.15
        F = np.zeros((n, 4))
        Bw = np.zeros((n, 4))
        setm = np.zeros(n, bool)
        last = len(plan.syls) - 1
        for i, s in enumerate(plan.syls):
            a, b = int(s.t * SR), min(n, int((s.t + s.d) * SR))
            VF, VB = VOWELS[s.vowel]
            F[a:b] = np.array(VF) * fs
            Bw[a:b] = np.array(VB) * 1.6
            setm[a:b] = True
            if s.cons == 'm':
                m = min((b - a) // 2, int(0.05 * SR))
                F[a:a + m] = np.array(NASAL['m'][0]) * fs
                amp[a:a + m] *= 0.5
            u = np.linspace(0, 1, b - a)
            if emo == 'happy' and i >= last - 2 and s.cons == 'h':    # giggle pulses 'hu-hu-hu'
                amp[a:b] *= 0.35 + 0.65 * (0.5 + 0.5 * np.cos(TAU * 7 * u * s.d))
            if emo == 'sad' and i % 2 == 1:                           # sob tremor
                amp[a:b] *= 1 - 0.6 * (0.5 + 0.5 * np.sin(TAU * 6 * u * s.d))
        F = _fill_rows(F, setm)
        Bw = _fill_rows(Bw, setm)
        for j in range(4):
            F[:, j] = smooth(F[:, j], int(0.02 * SR))
        vratio = {'happy': 0.65, 'sad': 0.45, 'angry': 0.6, 'surprised': 0.55}[emo]
        tilt = 1.5 + 0.6 * P['tilt']
        voiced = additive(f0, lambda k, fk: k ** -tilt * formant_mag(fk, F, Bw), 9000, rng=rng)
        if emo == 'angry':
            sub = additive(f0 * 0.5, lambda k, fk: (k % 2) * k ** -tilt * formant_mag(fk, F, Bw), 9000, rng=rng)
            voiced = voiced + 0.6 * sub
            voiced *= 1 - 0.7 * (0.5 + 0.5 * np.sin(TAU * 42 * t + 3 * np.sin(TAU * 2 * t)))
        if emo == 'happy':   # purr on the long final syllable: 24 Hz flutter (contentment, below alarm band)
            s = plan.syls[last]
            a, b = int(s.t * SR), min(n, int((s.t + s.d) * SR))
            voiced[a:b] *= 1 - 0.45 * (0.5 + 0.5 * np.sin(TAU * 24 * t[a:b]))
        voiced *= amp
        r_v = _rms(voiced)
        def env(times, freqs):
            ii = np.clip((times * SR).astype(int), 0, n - 1)
            g = formant_mag(freqs[None, :], F[ii][:, None, :], Bw[ii][:, None, :])
            return g * (amp[ii] + 1e-4)[:, None] * (1 / np.sqrt(1 + (350 / np.maximum(freqs, 1)) ** 2))[None, :]
        breath = shaped_noise(n, env, rng)
        out = vratio * voiced / (r_v + 1e-12) + (1 - vratio) * breath / (_rms(breath) + 1e-12)
        out *= r_v
        if emo == 'angry':   # hiss bursts at word onsets (cat-like 'khhh')
            for wi in plan.words:
                if wi < len(plan.syls):
                    s = plan.syls[wi]
                    m = int(0.09 * SR)
                    x = band_noise(m, 3000, 10000, rng) * np.exp(-np.arange(m) / (0.03 * SR))
                    i0 = max(0, int(s.t * SR) - m // 2)
                    mm = min(m, n - i0)
                    out[i0:i0 + mm] += x[:mm] / (_rms(x) + 1e-12) * r_v * 0.9
        if plan.gasp:
            gd = plan.gasp[1]
            m = int(gd * SR)
            u = np.linspace(0, 1, m)
            def genv(times, freqs):
                uu = np.clip(times / gd, 0, 1)[:, None]
                FF = (np.array(VOWELS['a'][0]) * fs * (0.8 + 0.5 * uu))[:, None, :]
                return formant_mag(freqs[None, :], FF, np.array([200, 250, 300, 400])[None, None, :])
            x = shaped_noise(m, genv, rng) * u ** 2
            out[:m] += x / (_rms(x) + 1e-12) * r_v * 1.1
        if plan.sigh:
            s0, sd = plan.sigh
            i0, m = int(s0 * SR), int(sd * SR)
            m = min(m, n - i0)
            def senv(times, freqs):
                uu = np.clip(times / sd, 0, 1)[:, None]
                FF = (np.array(VOWELS['o'][0]) * fs * (1 - 0.3 * uu))[:, None, :]
                return formant_mag(freqs[None, :], FF, np.array([150, 200, 300, 400])[None, None, :])
            u = np.linspace(0, 1, m)
            x = shaped_noise(m, senv, rng) * np.sin(np.pi * u) ** 1.3
            out[i0:i0 + m] += x / (_rms(x) + 1e-12) * r_v * 0.7
        return out


# =================================================================== E. rusty-iron villain
BAR = (1.0, 2.756, 5.404, 8.933, 13.34)     # free-free bar mode ratios (inharmonic, 'metal')


def iron_strike(f, dur, rng, decay=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for r, a, tau in zip(BAR, (1, .7, .5, .35, .2), (1.2, .6, .35, .2, .1)):
        for det in (1.0, 1.003):     # detuned pairs -> slow wobble ('rust')
            x += a * np.sin(TAU * f * r * det * t + rng.uniform(0, TAU)) * np.exp(-t / (tau * decay))
    na = int(0.001 * SR)
    x[:na] *= np.linspace(0, 1, na)
    return x


class Iron(Babble):
    name = 'iron'
    base_hz = 147.0      # D3; tritone partner G#3
    fscale = 0.85
    cons = ['h', 'k', 'g', '']
    vowels = ['o', 'a', 'e']
    interj = {'happy': [('h', 'e'), ('h', 'e'), ('h', 'e')], 'angry': [('g', 'a')],
              'surprised': [('', 'a')], 'sad': [('', 'o')]}

    def __init__(self, seed=31):
        self.lex = make_lexicon(np.random.default_rng(seed), self.cons, self.vowels, 8)

    def render(self, plan, rng):
        emo = plan.emotion
        P = dict(plan.params)
        n = int(plan.length * SR)
        # creaky voice: jittery low pulses through big formants (formant voice reused, rougher)
        plan.params = dict(P, tilt=-0.4, rough=max(P['rough'], 0.35), breath=0.15, jitter=0.4)
        voice = Babble.render(self, plan, rng)
        plan.params = P
        r_v = _rms(voice)
        out = voice.copy()
        t = np.arange(n) / SR
        last = len(plan.syls) - 1
        for i, s in enumerate(plan.syls):
            i0 = int(s.t * SR)
            if emo in ('happy', 'angry') and (s.stress or i == last):
                for f in (self.base_hz * 2, self.base_hz * 2 * np.sqrt(2)):   # tritone dyad
                    x = iron_strike(f, 1.5, rng, 0.6 if emo == 'happy' else 1.0)
                    m = min(len(x), n - i0)
                    out[i0:i0 + m] += x[:m] / np.abs(x).max() * r_v * (1.2 if emo == 'angry' else 0.6)
            if emo == 'angry':   # stick-slip scrape under the syllable
                m = int(s.d * SR)
                pulses = (np.sin(TAU * np.cumsum(rng.uniform(30, 60, m)) / SR) > 0.6).astype(float)
                x = band_noise(m, 900, 2600, rng) * smooth(pulses, 48)
                mm = min(m, n - i0)
                out[i0:i0 + mm] += x[:mm] / (_rms(x) + 1e-12) * r_v * 0.6
        if emo == 'surprised':
            s = plan.syls[0]
            i0 = int(s.t * SR)
            m = int(0.45 * SR)
            u = np.linspace(0, 1, m)
            def senv(times, freqs):
                cf = 1000 * 4 ** np.clip(times / 0.45, 0, 1)[:, None]
                return 1 / (1 + ((freqs[None, :] - cf) / 120) ** 2)
            x = shaped_noise(m, senv, rng) * np.sin(np.pi * u) ** 0.5   # screech
            mm = min(m, n - i0)
            out[i0:i0 + mm] += x[:mm] / (_rms(x) + 1e-12) * r_v * 1.2
            for j in range(6):                                       # clatter
                k0 = i0 + int(rng.uniform(0.2, 0.9) * SR)
                x = iron_strike(self.base_hz * rng.uniform(2, 6), 0.4, rng, 0.15)
                mm = min(len(x), n - k0)
                if mm > 0:
                    out[k0:k0 + mm] += x[:mm] / np.abs(x).max() * r_v * 0.5
        if emo == 'sad':   # defeated: sagging, wobbling metal
            for i, s in enumerate(plan.syls):
                i0 = int(s.t * SR)
                m = int(s.d * 1.6 * SR)
                tt = np.arange(m) / SR
                f = self.base_hz * 2 * 2 ** ((-i - 2.0 * tt / s.d) / 12) * (1 + 0.01 * np.sin(TAU * 5 * tt))
                x = additive(f, lambda k, fk: 1.0 / k, 8000, rng=rng, ratios=[1, 2.756, 5.404]) * np.exp(-tt / (s.d * 1.2))
                mm = min(m, n - i0)
                out[i0:i0 + mm] += x[:mm] / (np.abs(x).max() + 1e-9) * r_v * 0.6
        return out


VOICES = {'babble': Babble, 'suikin': Suikin, 'robot': Robot, 'creature': Creature, 'iron': Iron}
