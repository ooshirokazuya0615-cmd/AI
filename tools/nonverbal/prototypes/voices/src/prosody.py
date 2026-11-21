"""Shared emotional prosody planner.

One prosodic 'code' drives every voice type, following the cue directions summarized in
Juslin & Laukka (2003) / Banse & Scherer (1996) / Scherer (2003):
  happy     : high F0, wide F0 range, rising/arched contours, fast, medium-loud, bright, fast attacks
  sad       : low F0, narrow range, falling contours, slow, quiet, dark/breathy, slow attacks, pauses
  angry     : high-ish F0, wide range, sharp falling accents, fast, loud, bright+rough, abrupt onsets
  surprised : short gasp, very large fast F0 rise (+10..14 st), then hold / small fall
Valence (happy vs angry, both high arousal) is separated by contour shape (rise vs accented fall),
roughness (Arnal et al. 2015: 30-150 Hz amplitude modulation) and harmonic consonance.
"""
from dataclasses import dataclass, field
import numpy as np

from dsp import SR, smooth

EMOTIONS = ('happy', 'sad', 'angry', 'surprised')

# all pitch values in semitones relative to the character's neutral base
EMO = {
    'happy': dict(n_syl=(6, 9), dur=(0.10, 0.15), gap=(0.015, 0.05), word_gap=(0.06, 0.10),
                  base=4.0, span=6.0, glide=2.5, final=6.0, decl=-1.0, amp_db=0.0, amp_var=2.5,
                  tilt=-0.35, fshift=1.07, breath=0.08, rough=0.0, vib=(5.5, 0.12), jitter=0.08,
                  attack=0.008, release=0.03, smooth_ms=25, bounce=True),
    'sad': dict(n_syl=(3, 4), dur=(0.26, 0.40), gap=(0.06, 0.12), word_gap=(0.18, 0.32),
                base=-4.0, span=2.0, glide=-2.5, final=-6.0, decl=-4.0, amp_db=-9.0, amp_var=1.0,
                tilt=0.55, fshift=0.94, breath=0.35, rough=0.0, vib=(4.5, 0.30), jitter=0.15,
                attack=0.07, release=0.10, smooth_ms=60, bounce=False),
    'angry': dict(n_syl=(5, 8), dur=(0.09, 0.15), gap=(0.01, 0.03), word_gap=(0.04, 0.07),
                  base=1.5, span=5.0, glide=-3.5, final=-6.0, decl=-1.5, amp_db=3.0, amp_var=4.0,
                  tilt=-0.75, fshift=1.03, breath=0.05, rough=0.55, vib=(0, 0), jitter=0.25,
                  attack=0.003, release=0.02, smooth_ms=12, bounce=False),
    'surprised': dict(n_syl=(1, 3), dur=(0.11, 0.16), gap=(0.02, 0.05), word_gap=(0.10, 0.16),
                      base=2.0, span=3.0, glide=3.0, final=4.0, decl=0.0, amp_db=1.5, amp_var=2.0,
                      tilt=-0.45, fshift=1.06, breath=0.12, rough=0.0, vib=(6.0, 0.10), jitter=0.08,
                      attack=0.006, release=0.05, smooth_ms=20, bounce=True,
                      gasp=(0.12, 0.17), peak_rise=12.0),
}


@dataclass
class Syl:
    t: float          # onset (s)
    d: float          # duration (s)
    p0: float         # pitch at start (st)
    p1: float         # pitch at end (st)
    amp_db: float
    vowel: str
    cons: str
    stress: bool = False
    shape: str = 'lin'   # lin | rise_early | arch | fall_late


@dataclass
class Plan:
    emotion: str
    syls: list
    length: float
    params: dict
    gasp: tuple = None          # (t, d) inhaled gasp before speech
    sigh: tuple = None          # (t, d) exhale at end
    words: list = field(default_factory=list)


def make_lexicon(rng, cons, vowels, n_words=10):
    lex = []
    for _ in range(n_words):
        k = rng.choice([1, 2, 2, 2, 3])
        lex.append([(rng.choice(cons), rng.choice(vowels)) for _ in range(k)])
    return lex


def plan_utterance(emotion, rng, lexicon, interj=None, n_syl=None):
    P = EMO[emotion]
    target = n_syl if n_syl else int(rng.integers(P['n_syl'][0], P['n_syl'][1] + 1))
    # pick words (Zipf-ish) until enough syllables
    sylspecs, words = [], []
    zipf = 1 / np.arange(1, len(lexicon) + 1)
    zipf /= zipf.sum()
    while len(sylspecs) < target:
        w = lexicon[rng.choice(len(lexicon), p=zipf)]
        words.append(len(sylspecs))
        sylspecs.extend(w)
    sylspecs = sylspecs[:max(target, 1)]
    if interj and emotion in interj:
        words.append(len(sylspecs))
        sylspecs.extend(interj[emotion])
    n = len(sylspecs)
    t = 0.0
    gasp = None
    if emotion == 'surprised':
        gd = rng.uniform(*P['gasp'])
        gasp = (0.0, gd)
        t = gd + 0.03
    syls = []
    for i, (c, v) in enumerate(sylspecs):
        pos = i / max(1, n - 1)
        d = rng.uniform(*P['dur'])
        base = P['base'] + P['decl'] * pos
        acc = rng.uniform(0, P['span'])
        stress = (i in words) or (rng.random() < 0.25)
        if P['bounce']:
            acc = P['span'] * (0.55 + 0.45 * rng.random()) if i % 2 == 0 else P['span'] * 0.25 * rng.random()
        p0 = base + acc
        glide = P['glide'] * (0.6 + 0.8 * rng.random())
        shape = 'lin'
        amp = P['amp_db'] + (P['amp_var'] if stress else 0) * rng.uniform(0.5, 1.0) - P['amp_var'] * 0.5
        if emotion == 'angry':
            shape = 'fall_late' if not stress else 'lin'
            if stress:
                p0 += 2.0
                glide = P['glide'] * 1.3
        if emotion == 'happy':
            shape = 'arch' if rng.random() < 0.4 else 'rise_early'
        if emotion == 'sad':
            shape = 'fall_late'
            d *= 1.0 + 0.6 * pos  # slowing down
        if emotion == 'surprised' and i == 0:
            d = rng.uniform(0.26, 0.34)
            p0 = P['base'] - 1.0
            glide = P['peak_rise'] * rng.uniform(0.9, 1.15)
            shape = 'rise_early'
            amp = P['amp_db'] + 2
        if i == n - 1:
            glide = P['final'] * (0.8 + 0.4 * rng.random())
            if emotion == 'sad':
                d *= 1.4
            if emotion == 'happy':
                d *= 1.3
                shape = 'rise_early'
            if emotion == 'angry':
                d *= 1.1
                shape = 'fall_late'
                amp += 1.5
            if emotion == 'surprised' and n > 1:
                shape = 'rise_early'
                d *= 1.3
        syls.append(Syl(t, d, p0, p0 + glide, amp, v, c, stress, shape))
        gap = rng.uniform(*P['gap'])
        if (i + 1) in words:
            gap = rng.uniform(*P['word_gap'])
        if emotion == 'surprised' and i == 0:
            gap = rng.uniform(0.12, 0.2)
        t += d + gap
    sigh = None
    if emotion == 'sad':
        sigh = (t + 0.05, rng.uniform(0.45, 0.6))
        t = sigh[0] + sigh[1]
    length = t + 0.25
    return Plan(emotion, syls, length, P, gasp, sigh, words)


def shape_curve(u, shape):
    if shape == 'rise_early':
        return 1 - (1 - u) ** 2.2
    if shape == 'fall_late':
        return u ** 2.0
    if shape == 'arch':
        return np.sin(np.pi * u * 0.75) / np.sin(np.pi * 0.75)
    return u


def controls(plan, base_hz, rng, attack=None, release=None, glide_scale=1.0, pitch_fn=None):
    """per-sample controls: f0 (Hz), amp (lin), syllable index (-1 = none), syllable phase 0..1"""
    P = plan.params
    n = int(plan.length * SR)
    t = np.arange(n) / SR
    st_curve = np.full(n, np.nan)
    amp = np.zeros(n)
    sidx = np.full(n, -1)
    sph = np.zeros(n)
    att = attack if attack is not None else P['attack']
    rel = release if release is not None else P['release']
    for i, s in enumerate(plan.syls):
        a, b = int(s.t * SR), min(n, int((s.t + s.d) * SR))
        if b <= a:
            continue
        u = np.linspace(0, 1, b - a, endpoint=False)
        p0, p1 = s.p0, s.p0 + (s.p1 - s.p0) * glide_scale
        if pitch_fn is not None:
            p0, p1 = pitch_fn(i, s, p0, p1)
        st_curve[a:b] = p0 + (p1 - p0) * shape_curve(u, s.shape)
        ta = np.minimum(1, (u * s.d) / max(att, 1e-4))
        tr = np.minimum(1, ((1 - u) * s.d) / max(rel, 1e-4))
        env = np.minimum(ta, tr) ** 1.5
        if plan.emotion == 'angry':
            env *= 1.0 - 0.35 * u          # accent: loud start
        if plan.emotion == 'sad':
            env *= np.sin(np.pi * np.clip(u * 1.05, 0, 1)) ** 0.4  # swell
        amp[a:b] = np.maximum(amp[a:b], env * 10 ** (s.amp_db / 20))
        sidx[a:b] = i
        sph[a:b] = u
    # fill pitch through gaps (glottis keeps 'intending' a pitch) then smooth = coarticulation
    v = ~np.isnan(st_curve)
    if v.any():
        idx = np.arange(n)
        st_curve = np.interp(idx, idx[v], st_curve[v])
    else:
        st_curve = np.zeros(n)
    st_curve = smooth(st_curve, int(P['smooth_ms'] * SR / 1000))
    # vibrato + jitter (slow random walk)
    vr, vd = P['vib']
    if vd > 0:
        st_curve += vd * np.sin(2 * np.pi * vr * t + rng.uniform(0, 6.28)) * np.clip(t / 0.2, 0, 1)
    jit = smooth(rng.standard_normal(n), int(SR / 25))
    jit /= np.abs(jit).max() + 1e-9
    st_curve += P['jitter'] * jit
    f0 = base_hz * 2 ** (st_curve / 12)
    return dict(n=n, t=t, f0=f0, st=st_curve, amp=amp, sidx=sidx, sph=sph)
