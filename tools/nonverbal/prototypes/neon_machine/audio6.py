"""Soundtrack for film6.py, on the same clock (songs6.timeline or another SONGS_MODULE).

Each contact has the timbre of its instrument; under each song a soft drone (or, when the module sets
DRUMS, a rock beat with bass on the bar chords); the gaps are silent except for the machine's own sounds,
which fall on the counted beats.

    SONGS_MODULE=songs_kimetsu python audio6.py out.wav
"""
import importlib
import math
import os
import sys
import wave

import numpy as np

import perform
import sampler

S = importlib.import_module(os.environ.get('SONGS_MODULE', 'songs6'))
SR = 48000
rng = np.random.default_rng(9)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(sec):
    return np.arange(int(SR * sec)) / SR


def env(t, a, d):
    return np.minimum(1, t / a) * np.exp(-t * d)


def marimba(m, L=1.6):
    """modal marimba: partials near 1 : 3.93 : 9.2 with their own decays, a soft mallet click"""
    f, t = hz(m), tt(L)
    dec = 2.6 + (m - 60) * 0.05
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * dec) + 0.32 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * dec * 3.5)
         + 0.08 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * dec * 9))
    click_ = rng.standard_normal(len(t)) * np.exp(-t * 900) * 0.25
    return (s + click_) * np.minimum(1, t / 0.0015)


def pluck(m, L=1.2):
    """Karplus-Strong plucked string: a bright, natural decay for the LED tiles"""
    f = hz(m)
    n, period = int(SR * L), max(2, int(round(SR / f)))
    buf = rng.uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.996 * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out * 0.9


def bellv(m, L=2.4):
    """FM bell (carrier : modulator 1 : 1.4, decaying index)"""
    f, t = hz(m), tt(L)
    idx = 3.5 * np.exp(-t * 2.2)
    s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 1.4 * t)) * np.exp(-t * 1.5)
    s += 0.25 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 3)
    return s * np.minimum(1, t / 0.0015)


def glass(m, L=2.0):
    f, t = hz(m), tt(L)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.0 * t)) * env(t, 0.004, 1.5)


def wood(m, L=1.2):
    f, t = hz(m), tt(L)
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t * 6)) * env(t, 0.002, 4.5)


def organ(m, L=1.4):
    f, t = hz(m), tt(L)
    return sum(a * np.sin(2 * np.pi * f * k * t) for k, a in ((1, 1), (2, .5), (4, .25), (8, .1))) * np.minimum(1, t / 0.02) * np.exp(-t * 1.6)


def cymbal_hit(L=1.5):
    t = tt(L)
    n = rng.standard_normal(len(t))
    n = n - np.concatenate([[0], n[:-1]]) * 0.9
    return n * env(t, 0.001, 3.0) * 0.5


def click(L=0.05, tone=2600, decay=90):
    t = tt(L)
    return (rng.standard_normal(len(t)) * 0.5 + np.sin(2 * np.pi * tone * t)) * np.exp(-t * decay)


def drum(L=1.6):
    t = tt(L)
    fd = 80 * np.exp(-t * 7) + 44
    return 1.3 * np.sin(2 * np.pi * np.cumsum(fd) / SR) * np.exp(-t * 3.6) + 0.35 * rng.standard_normal(len(t)) * np.exp(-t * 20)


def kick(L=0.35):
    t = tt(L)
    fd = 110 * np.exp(-t * 30) + 48
    return np.sin(2 * np.pi * np.cumsum(fd) / SR) * np.exp(-t * 9)


def snare(L=0.25):
    t = tt(L)
    return (0.7 * rng.standard_normal(len(t)) * np.exp(-t * 18) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25))


def hat(L=0.06):
    t = tt(L)
    n = rng.standard_normal(len(t))
    return (n - np.concatenate([[0], n[:-1]])) * np.exp(-t * 70) * 0.4


def bassn(m, L):
    f, t = hz(m), tt(L)
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) + 0.15 * np.sign(np.sin(2 * np.pi * f * t))
    return s * np.minimum(1, t / 0.005) * np.minimum(1, (L - t) / 0.03) * np.exp(-t * 1.2)


def pad(m, L):
    f, t = hz(m), tt(L)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.003 * t)) * np.minimum(1, t / 0.2) * np.minimum(1, (L - t) / 0.3)


def roll(L):
    n = int(SR * L)
    x = np.convolve(rng.standard_normal(n), np.ones(50) / 50, mode='same')
    return x * np.minimum(1, np.arange(n) / (0.1 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.1 * SR))


def boing(L=0.35):
    """The spring letting go: a falling tone with a quick wobble."""
    t = tt(L)
    f = 520 * np.exp(-t * 5) + 160
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * (1 + 0.3 * np.sin(2 * np.pi * 22 * t))


def whirr(L):
    """A marble circling a metal funnel: rolling noise that rises in pitch and level as it speeds up."""
    n = int(SR * L)
    t = np.arange(n) / SR
    k = t / L
    x = np.convolve(rng.standard_normal(n), np.ones(24) / 24, mode='same') * (0.4 + 0.9 * k)
    f = 180 + 700 * k ** 2
    x += 0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.3 + k)
    return x * np.minimum(1, t / 0.1) * np.minimum(1, (L - t) / 0.05)


def whoosh(L):
    n = int(SR * L)
    x = np.convolve(rng.standard_normal(n), np.ones(30) / 30, mode='same')
    return x * np.sin(np.pi * np.arange(n) / n) ** 2


if sampler.available():
    def s_marimba(m):
        return sampler.note('marimba', m, 1.8)

    def s_glock(m):
        return sampler.note('glock', max(m, 67), 2.2)

    def s_piano(m, L=1.6):
        return sampler.note('piano', m, L)
else:
    s_marimba, s_glock, s_piano = marimba, bellv, None

VOICE = dict(tile=(pluck, 0.24), pad=(marimba, 0.32), again=(marimba, 0.32), block=(wood, 0.34), cup=(marimba, 0.32),
             xylo=(marimba, 0.30), bell=(bellv, 0.22), cymbal=(marimba, 0.28), flask=(glass, 0.24), pipe=(organ, 0.20),
             bumper=(pluck, 0.26))
if sampler.available() and os.environ.get('VOICE_SET') == 'piano':
    VOICE = {k: ((lambda m: sampler.note('piano', m, 1.9)), 0.36) for k in VOICE}
elif sampler.available():
    VOICE.update(pad=(s_marimba, 0.36), again=(s_marimba, 0.36), cup=(s_marimba, 0.36), xylo=(s_marimba, 0.34),
                 cymbal=(s_marimba, 0.30), block=(s_marimba, 0.38), bell=(s_glock, 0.20), flask=(s_glock, 0.16),
                 tile=(s_glock, 0.18), bumper=(s_glock, 0.20))
CHORD = {'Dm': (38, [62, 65, 69]), 'C': (36, [60, 64, 67]), 'Bb': (34, [58, 62, 65]), 'A': (33, [61, 64, 69]),
         'Am': (33, [60, 64, 69]), 'G': (31, [59, 62, 67])}


def place(mix, s, t, g, pan=0.0):
    a = int(t * SR)
    if 0 <= a < len(mix):
        s = s[: len(mix) - a]
        mix[a:a + len(s), 0] += s * g * np.sqrt(0.5 * (1 - pan))
        mix[a:a + len(s), 1] += s * g * np.sqrt(0.5 * (1 + pan))


MACHINE_GAIN = 2.0     # machine sounds about 6 dB up: rides read as near-silence on phone speakers
# the room each era is heard in: reverberation time (s) and how much of it
HALL = {'baroque': (2.4, 0.34), 'classical': (1.5, 0.24), 'beethoven': (1.9, 0.28), 'romantic': (2.1, 0.30)}


def hall_ir(rt, seed):
    """A stereo hall: a dozen early reflections, then a diffuse tail that dies faster in the treble than in
    the bass (as air and walls absorb highs), each channel decorrelated. Unit energy."""
    r = np.random.default_rng(seed)
    n = int(SR * rt * 1.2)
    t = np.arange(n) / SR
    fq = np.fft.rfftfreq(n, 1 / SR)
    chans = []
    for _ in range(2):
        X = np.fft.rfft(r.standard_normal(n))
        tail = np.zeros(n)
        for lo, hi, k in ((0, 250, 1.3), (250, 2500, 1.0), (2500, 6000, 0.6), (6000, SR, 0.3)):
            tail += np.fft.irfft(X * ((fq >= lo) & (fq < hi)), n) * 10 ** (-3 * t / (rt * k))
        pre = int(SR * 0.022)
        tail = np.concatenate([np.zeros(pre), tail[:-pre]]) * np.minimum(1, np.arange(n) / (SR * 0.05))
        er = np.zeros(n)
        for d, g in zip(np.sort(r.uniform(0.006, 0.075, 14)), np.linspace(0.6, 0.12, 14)):
            er[int(SR * d)] += g * r.choice((-1, 1))
        ir = 0.5 * er / np.sqrt(np.sum(er ** 2)) + tail / np.sqrt(np.sum(tail ** 2))
        chans.append(ir / np.sqrt(np.sum(ir ** 2)))
    return np.stack(chans, 1)


def halls(mix, C):
    """Each piece in the hall of its era; machines before a piece still sound in the previous one."""
    T, xf = len(mix), int(SR * 0.4)
    starts = [min(h['t'] for h in C if h['s'] == s) for s in range(len(S.SONGS))]
    bounds = [0] + [int(SR * (t - 0.6)) for t in starts[1:]] + [T]
    out = mix.copy()
    for s, song in enumerate(S.SONGS):
        rt, wet = HALL.get(song.get('era'), (1.8, 0.28))
        a, b = max(0, bounds[s] - xf // 2), min(T, bounds[s + 1] + xf // 2)
        w = np.ones(b - a)
        if s > 0:
            w[:xf] = np.linspace(0, 1, xf)
        if s < len(S.SONGS) - 1:
            w[-xf:] = np.linspace(1, 0, xf)
        ir = hall_ir(rt, 11 + s)
        n = 1 << int(np.ceil(np.log2(b - a + len(ir))))
        for c in range(2):
            y = np.fft.irfft(np.fft.rfft(mix[a:b, c] * w, n) * np.fft.rfft(ir[:, c], n), n)
            e = min(T, a + n)
            out[a:e, c] += wet * y[: e - a]
    return out


# ITU-R BS.1770 K-weighting at 48 kHz (high shelf, then the RLB high-pass), as magnitude responses
_KW = (([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]),
       ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]))


def lufs(st):
    """Integrated loudness (LUFS) with K-weighting and the two gates of BS.1770."""
    n = len(st)
    z = np.exp(-1j * 2 * np.pi * np.fft.rfftfreq(n, 1 / SR) / SR)
    H = np.ones(len(z))
    for b, a in _KW:
        H *= np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))
    y = np.stack([np.fft.irfft(np.fft.rfft(st[:, c]) * H, n) for c in range(st.shape[1])], 1)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.sum(np.mean(y[k:k + blk] ** 2, axis=0)) for k in range(0, n - blk, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[lk > -70]
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 10
    return float(-0.691 + 10 * np.log10(np.mean(ms[(lk > -70) & (lk > rel)])))


def level_up(st, floor_db=-27.0, most_db=7.0, win=1.5):
    """Lift stretches quieter than floor_db (RMS over win seconds) by up to most_db, slowly, so the gaps
    between pieces keep up with the music on small speakers without touching the pieces' own dynamics."""
    hop = SR // 10
    m = st.mean(axis=1)
    n = len(m) // hop
    rms = np.sqrt(np.convolve(np.mean(m[: n * hop].reshape(n, hop) ** 2, axis=1),
                              np.ones(int(win * 10)) / int(win * 10), mode='same') + 1e-12)
    g_db = np.clip(floor_db - 20 * np.log10(rms), 0.0, most_db)
    g_db = np.convolve(g_db, np.ones(15) / 15, mode='same')          # glide, no pumping
    g = 10 ** (np.interp(np.arange(len(st)), np.arange(n) * hop + hop / 2, g_db) / 20)
    return st * g[:, None]


def _interp_taps(os_=4, half=12):
    """Windowed-sinc filters for the in-between samples of a 4x oversampled signal (one per phase)."""
    n = np.arange(-half, half)
    out = []
    for ph in range(1, os_):
        x = n + ph / os_
        h = np.sinc(x) * (0.42 + 0.5 * np.cos(np.pi * x / half) + 0.08 * np.cos(2 * np.pi * x / half))
        out.append(h / h.sum())
    return out, half


def true_peak(st, os_=4):
    """Sample-wise peak of the signal as a DAC would draw it (4x oversampled, BS.1770 style), both channels."""
    taps, half = _interp_taps(os_)
    pk = np.abs(st).max(axis=1)
    for h in taps:
        for c in range(st.shape[1]):
            y = np.convolve(st[:, c], h[::-1], mode='full')[half - 1: half - 1 + len(st)]
            pk = np.maximum(pk, np.abs(y))
    return pk


def limit(st, ceil_db=-1.5, look=3, release=0.08):
    """A look-ahead true-peak limiter on 1 ms blocks: no peak above the ceiling, even between samples (so
    no overs once YouTube re-encodes it), and the gain recovers in about 80 ms."""
    ceil, blk = 10 ** (ceil_db / 20), SR // 1000
    nb = len(st) // blk + 1
    pk = np.zeros(nb)
    a = true_peak(st)
    pk[: len(a) // blk] = a[: len(a) // blk * blk].reshape(-1, blk).max(axis=1)
    pk[len(a) // blk] = a[len(a) // blk * blk:].max(initial=0.0)
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    g, cur, k_rel = np.ones(nb), 1.0, 1 - np.exp(-1 / (release * 1000))
    need = np.min([np.concatenate([need[k:], np.ones(k)]) for k in range(look + 1)], axis=0)   # look-ahead
    for i in range(nb):
        cur = min(need[i], cur + (1 - cur) * k_rel)
        g[i] = cur
    gs = np.interp(np.arange(len(st)), np.arange(nb) * blk + blk / 2, g)
    return st * gs[:, None]


def main(out):
    T = S.total_seconds()
    mix = np.zeros((int(SR * (T + 0.5)), 2))
    C, GAPS = S.timeline()
    # the piano played: three recorded dynamics, a velocity and a ring length for every note (perform.py)
    PIANO = os.environ.get('VOICE_SET') == 'piano' and sampler.available() and sampler.piano_layers_available()
    VEL, RINGS, ARCS = perform.plan(S, C) if PIANO else ({}, {}, {})

    def acc_note(m, L, t, s, k=0):
        if PIANO:
            return sampler.piano(m, 0.85 * perform.level_at(ARCS, s, t), L, take=k)
        return s_piano(m, L)
    for h in C:
        if h['mech'] == 'bigdrum':
            if sampler.available():
                place(mix, sampler.one('Percussion/BDrumNewhit_v5_rr1_Sum.wav', 3.0), h['t'], 0.6)
                place(mix, sampler.one('Percussion/Timpani/Timpani3_Hit_v3_rr1_Sum.wav', 3.0), h['t'], 0.45)
            else:
                place(mix, drum(), h['t'], 0.55)
            place(mix, marimba(h['midi'], 2.5), h['t'], 0.34)
            for c in (h['midi'] - 24, h['midi'] - 17, h['midi'] - 12, h['midi'] - 9, h['midi'] - 5, h['midi']):
                place(mix, pad(c, 3.2), h['t'], 0.06)
            continue
        fn, g = VOICE[h['mech']]
        pan = max(-0.4, min(0.4, (h['midi'] - 67) / 30))
        if PIANO:
            place(mix, sampler.piano(h['midi'], VEL[h['i']], RINGS[h['i']], take=h['i']), h['t'], g, pan)
        else:
            place(mix, fn(h['midi']), h['t'], g, pan)
        if h['mech'] == 'cymbal':
            place(mix, cymbal_hit(), h['t'], 0.18)
        if sampler.available():
            place(mix, sampler.one(['Percussion/Claves1_Hit_v1_rr1_Sum.wav', 'Percussion/Claves1_Hit_v1_rr2_Sum.wav',
                                    'Percussion/Claves1_Hit_v2_rr1_Sum.wav'][h['i'] % 3], 0.25), h['t'], 0.035, pan)
        else:
            place(mix, click(0.02, 3200), h['t'], 0.05)
    drums = getattr(S, 'DRUMS', False)
    for s, song in enumerate(S.SONGS):
        hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
        t0, t1 = hs[0]['t'], hs[-1]['t'] + hs[-1]['dur']
        if drums and song.get('chords'):
            beat = song['beat']
            for b, ch in enumerate(song['chords']):
                tb = t0 + b * 4 * beat
                root, tri = CHORD[ch]
                for q in range(4):
                    place(mix, kick() if q in (0, 2) else snare(), tb + q * beat, 0.30 if q in (0, 2) else 0.22)
                    for e in range(2):
                        place(mix, hat(), tb + q * beat + e * beat / 2, 0.12)
                    place(mix, bassn(root + 12 * (q == 3), beat * 0.9), tb + q * beat, 0.16)
                for m in tri:
                    place(mix, pad(m, 4 * beat), tb, 0.025)
        elif song.get('accomp') and sampler.available():
            acc = song['accomp']
            if 'bass' in acc:
                tb = t0 - acc.get('lead', 0) * song['unit']     # (the Canon's bass leads in alone)
                for n_, u_ in acc['bass']:          # None = rest, 'C4+E4' = chord
                    ring = u_ * song['unit'] * 0.85 + 0.10 if acc.get('staccato') else u_ * song['unit'] + acc.get('ring', 0.5)
                    parts = n_.split('+') if n_ else []
                    for m_ in parts:
                        place(mix, acc_note(S.midi(m_), ring, tb, s, int(tb * 10)), tb, 0.16 / len(parts) ** 0.5, -0.25)
                    tb += u_ * song['unit']
            if acc.get('arpeggio'):
                lh = {69: ['A2', 'E3', 'A3'], 71: ['E2', 'E3', 'G#3'], 72: ['A2', 'E3', 'A3']}
                for h in hs:
                    if h['dur'] >= 3 * song['unit'] - 1e-6 and h['midi'] in lh:
                        for j, n_ in enumerate(lh[h['midi']]):
                            place(mix, acc_note(S.midi(n_), 1.2, h['t'], s, j), h['t'] + j * song['unit'], 0.14, -0.25)
            if acc.get('octave'):
                for h in hs:
                    if h['mech'] != 'again' or True:
                        place(mix, acc_note(h['midi'] - 12, RINGS.get(h['i'], max(0.4, h['dur'] + 0.3)), h['t'], s, h['i'] + 1),
                              h['t'], 0.14, -0.2)
        else:
            r, f5 = song['drone']
            if sampler.available():
                beat = song['beat']
                k = 0
                while t0 + k * 2 * beat < t1:
                    for m in (S.midi(r) + 12, S.midi(f5) + 12):
                        place(mix, acc_note(m, 2 * beat + 0.4, t0 + k * 2 * beat, s, k), t0 + k * 2 * beat, 0.07)
                    k += 1
            else:
                for m in (S.midi(r), S.midi(f5)):
                    place(mix, pad(m, t1 - t0), t0, 0.05)
    for g in ([] if os.environ.get('EVENTS_IN') else GAPS):     # the score film has its own tube events
        if g['kind'] == 'rail':
            place(mix, roll(g['t_sw'] - g['t_rail0']), g['t_rail0'], 0.035)
            place(mix, click(0.07, 1500, 60), g['t_sw'], 0.55)          # the switch
            place(mix, click(0.03, 4000, 120), g['t_sw'] + 0.05, 0.2)
        elif g['kind'] == 'chute':
            place(mix, click(0.05, 900, 60), g['t_in'], 0.3)            # into the funnel
            place(mix, roll(g['t_out'] - g['t_in']), g['t_in'], 0.02)
            place(mix, click(0.06, 600, 50), g['t_out'], 0.35)          # out of the tube
        else:
            place(mix, click(0.05, 700, 45), g['t_launch'] - 0.28, 0.18)   # the cup winds once
            place(mix, click(0.08, 400, 35), g['t_launch'], 0.5)           # and fires
            place(mix, whoosh(g['t1'] - g['t_launch']), g['t_launch'], 0.05)
    ev = os.environ.get('EVENTS_IN')
    music, mix = mix, np.zeros_like(mix)          # machine sounds go on their own bus (lifted below)
    if ev and os.path.exists(ev):
        import json
        E = json.load(open(ev))
        for r in E['returns'] + E['gaps']:
            place(mix, click(0.04, 900, 60), r['t0'], 0.22)                  # into the funnel
            place(mix, whoosh(max(0.2, r['t1'] - r['t0'])), r['t0'], 0.07)  # through the tube
            place(mix, click(0.04, 1300, 70), r['t1'], 0.18)                 # out at the next row
        # the machines between pieces
        clv = ['Percussion/Claves1_Hit_v1_rr1_Sum.wav', 'Percussion/Claves1_Hit_v1_rr2_Sum.wav',
               'Percussion/Claves1_Hit_v2_rr1_Sum.wav']
        for k, hh in enumerate(E.get('mhits', [])):
            kind, g_ = hh['kind'], hh['g']
            if kind == 'glock' and sampler.available():
                place(mix, sampler.note('glock', hh['midi'], 1.8), hh['t'], 0.30 * g_, (hh['midi'] - 78) / 30)
            elif kind in ('wood', 'land', 'wall', 'clack'):
                tap = sampler.one(clv[k % 3], 0.25) if sampler.available() else click(0.02, 2400)
                place(mix, tap, hh['t'], {'wood': 0.13, 'land': 0.07, 'wall': 0.09, 'clack': 0.16}[kind] * g_)
                if kind in ('land', 'clack'):
                    place(mix, click(0.05, 420, 45), hh['t'], 0.10 * g_)
            elif kind == 'domino':
                place(mix, click(0.012, 4200, 260), hh['t'], 0.125 * g_)        # the chain is heard, not lost
            elif kind == 'spring':
                place(mix, click(0.03, 900, 80), hh['t'], 0.10 * g_)
            elif kind == 'boing':
                place(mix, boing(), hh['t'], 0.10 * g_)
            elif kind == 'clunk':
                place(mix, click(0.06, 300, 30), hh['t'], 0.18 * g_)
            elif kind == 'ratchet':
                place(mix, click(0.012, 3600, 220), hh['t'], 0.07 * g_)
                place(mix, click(0.01, 1800, 300), hh['t'] + 0.012, 0.04 * g_)
            elif kind == 'thunder':
                if sampler.available():
                    place(mix, sampler.one('Percussion/Timpani/Timpani3_Hit_v3_rr1_Sum.wav', 3.0), hh['t'], 0.32 * g_)
                    place(mix, sampler.one('Percussion/BDrumNewhit_v5_rr1_Sum.wav', 2.0), hh['t'], 0.22 * g_)
                n_ = int(SR * 1.8)
                rum = np.convolve(rng.standard_normal(n_), np.ones(400) / 400, mode='same')
                rum *= np.exp(-np.arange(n_) / (SR * 0.6)) * np.minimum(1, np.arange(n_) / (SR * 0.03))
                place(mix, rum / (np.abs(rum).max() + 1e-9), hh['t'] + 0.05, 0.10 * g_)
            elif kind == 'davul':
                if sampler.available():
                    place(mix, sampler.one('Percussion/BDrumNewhit_v5_rr1_Sum.wav', 1.2), hh['t'], 0.10 * g_)
                place(mix, click(0.03, 160, 40), hh['t'], 0.06 * g_)
            elif kind == 'sparkle':
                if sampler.available():
                    for d_, m_ in ((0.0, 96), (0.06, 100), (0.12, 103)):
                        place(mix, sampler.note('glock', m_, 1.4), hh['t'] + d_, 0.10 * g_, 0.3)
            elif kind == 'chase' and sampler.available() and hh.get('midi'):
                place(mix, sampler.note('glock', hh['midi'], 1.4), hh['t'], 0.16 * g_, 0.2)
            elif kind == 'bell' and sampler.available():
                place(mix, sampler.note('glock', hh['midi'], 2.4), hh['t'], 0.22 * g_, 0.15)
            elif kind == 'peg':
                if sampler.available():
                    place(mix, sampler.note('glock', hh['midi'], 0.9), hh['t'], 0.09 * g_, -0.1)
                place(mix, click(0.008, 5200, 300), hh['t'], 0.05 * g_)
            elif kind == 'rattle':
                place(mix, click(0.01, 2900, 220), hh['t'], 0.12 * g_)        # it was lost under the music
            elif kind == 'catch':
                place(mix, click(0.06, 520, 40), hh['t'], 0.16 * g_)
                place(mix, click(0.03, 2400, 90), hh['t'], 0.06 * g_)
            elif kind == 'whoosh':
                place(mix, whoosh(hh.get('L', 0.6)), hh['t'], 0.07 * g_)
            elif kind == 'clang':                  # the marble clips the funnel's rim and misses
                if sampler.available():
                    place(mix, sampler.note('glock', 79, 1.4), hh['t'], 0.22 * g_, 0.2)
                place(mix, click(0.02, 3100, 140), hh['t'], 0.14 * g_)
            elif kind == 'timp_roll':              # through the pause: a soft roll that swells into the return
                L_ = hh.get('L', 2.0)
                n_r = max(2, int(L_ / 0.065))
                for k_r in range(n_r):
                    u_r = k_r / (n_r - 1)
                    if sampler.available():
                        place(mix, sampler.one('Percussion/Timpani/Timpani3_Hit_v3_rr1_Sum.wav', 0.5),
                              hh['t'] + k_r * 0.065, (0.012 + 0.07 * u_r ** 1.6) * g_, 0.1 * math.sin(k_r))
                    else:
                        place(mix, click(0.05, 90, 20), hh['t'] + k_r * 0.065, (0.01 + 0.05 * u_r ** 1.6) * g_)
            elif kind == 'net':
                place(mix, click(0.09, 180, 22), hh['t'], 0.16 * g_)
                place(mix, roll(0.25), hh['t'], 0.02 * g_)
        for rr in E.get('mrolls', []):
            L_ = rr['t1'] - rr['t0']
            if L_ < 0.05:
                continue
            if rr['style'] == 'funnel':
                place(mix, whirr(L_), rr['t0'], 0.05)
            else:
                v_ = min(2.5, max(0.2, (rr['v0'] + rr['v1']) / 2))
                place(mix, roll(L_), rr['t0'], 0.02 + 0.02 * v_)
        it = E.get('intro')
        if it:
            # the opening: the spark's soft rising shimmer, the flame catching (a breath of air and a bell),
            # the gate's latch and the roll (on the music bus: already balanced; the bass counts in)
            if 'ignite' in it:
                sp_ = it['ignite'] - it['spark']
                w_ = whoosh(sp_ + 0.1)
                place(music, w_ * np.linspace(0.2, 1.0, len(w_)), it['spark'], 0.025)
                place(music, whoosh(0.45), it['ignite'] - 0.04, 0.05)
                if sampler.available():
                    for d_, m_ in ((0.0, 86), (0.07, 93)):                       # D and A, high and soft
                        place(music, sampler.note('glock', m_, 2.2), it['ignite'] + d_, 0.07, -0.3)
            place(music, click(0.04, 900, 60), it['gate'] - 0.33, 0.025)          # the marble presses on the gate
            place(music, click(0.05, 1500, 70), it['gate'], 0.055)
            place(music, click(0.02, 4200, 150), it['gate'] + 0.004, 0.02)
            r0_, r1_, v_ = it['roll']
            place(music, roll(r1_ - r0_) * np.linspace(0.3, 1.0, int(SR * (r1_ - r0_))), r0_, 0.012 + 0.012 * v_)
        for k, tp in enumerate(E.get('taps', [])):                          # the held ball settling on its note
            tap = (sampler.one('Percussion/Claves1_Hit_v1_rr2_Sum.wav', 0.2) if sampler.available()
                   else click(0.015, 3400))
            place(mix, tap, tp['t'], 0.012 * tp['g'])
    mix = music + MACHINE_GAIN * mix
    fin = C[-1]
    place(mix, click(0.05, 700, 45), fin['launch'] - 0.28, 0.18)
    place(mix, click(0.08, 400, 35), fin['launch'], 0.5)
    place(mix, whoosh(fin['t'] - fin['launch']), fin['launch'], 0.05)
    # the close: under the whole wall and the closing card, the Canon's ground bass once more, slow and soft,
    # so the film ends where it began (D A B F# G D G A, then D)
    FIN_ = getattr(S, 'FINALE', None)
    if FIN_:
        t_o = fin['t'] + FIN_['rise1'] + 0.4
        for k_o, nm_ in enumerate(('D3', 'A2', 'B2', 'F#2', 'G2', 'D2', 'G2', 'A2', 'D2')):
            last_ = k_o == 8
            L_o = 4.5 if last_ else 1.9
            tone = (sampler.piano(S.midi(nm_), 0.34, L_o, take=k_o) if PIANO else s_piano(S.midi(nm_), L_o))
            place(mix, tone, t_o + 0.78 * k_o + (0.25 if last_ else 0.0), 0.5, -0.15)
            if last_:                                  # and the D an octave up, to end open
                tone = sampler.piano(S.midi('D4'), 0.28, 4.5, take=3) if PIANO else s_piano(S.midi('D4'), 4.5)
                place(mix, tone, t_o + 0.78 * k_o + 0.25, 0.4, 0.15)
    it = E.get('intro') if ev and os.path.exists(ev) else None
    if it:          # the bass alone rises softly from the first frame; with the melody the music grows to its
        tt_ = np.arange(len(mix)) / SR                  # full level over the first phrase
        s0_ = S.SONGS[0]
        tb_ = it['first'] - s0_['accomp'].get('lead', 0) * s0_['unit']
        k0_ = np.clip((tt_ - tb_) / max(0.1, it['first'] - tb_), 0, 1)
        k_ = np.clip((tt_ - it['first']) / 5.0, 0, 1)
        mix *= np.where(tt_ < it['first'], 0.20 + 0.30 * k0_ * k0_ * (3 - 2 * k0_),
                        0.5 + 0.5 * k_ * k_ * (3 - 2 * k_))[:, None]
    st = halls(mix, C)[: int(SR * T)]
    fq = np.fft.rfftfreq(len(st), 1 / SR)
    hp = 1 / np.sqrt(1 + (25.0 / np.maximum(fq, 1e-3)) ** 4)          # 25 Hz high-pass: no rumble or offset
    st = np.stack([np.fft.irfft(np.fft.rfft(st[:, c]) * hp, len(st)) for c in range(2)], 1)
    fade = int(SR * 0.8)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    integ = lufs(st)
    st *= 10 ** ((-14.0 - integ) / 20)
    st = level_up(st)
    # room tone under everything (a warm, quiet hall), so no moment is digital silence; it fades in from the
    # first frame and out with the music
    fq = np.fft.rfftfreq(len(st), 1 / SR)
    shape = (fq > 45) / np.sqrt(np.maximum(fq, 45.0)) * np.exp(-fq / 2500)      # pinkish, low and soft
    bed = np.stack([np.fft.irfft(np.fft.rfft(rng.standard_normal(len(st))) * shape, len(st)) for _ in range(2)], 1)
    bed *= 10 ** (-52 / 20) / (np.sqrt(np.mean(bed ** 2)) + 1e-12)
    fi_, fo_ = int(SR * 0.8), int(SR * 0.8)
    bed[:fi_] *= np.linspace(0, 1, fi_)[:, None]
    bed[-fo_:] *= np.linspace(1, 0, fo_)[:, None]
    st += bed
    if os.environ.get('PEAKS'):                  # where the loudest peaks are, before the limiter
        b_ = SR // 20
        pk_ = np.abs(st[: len(st) // b_ * b_]).max(axis=1).reshape(-1, b_).max(axis=1)
        for k_ in np.argsort(pk_)[::-1][:12]:
            print(f'  peak {20 * np.log10(pk_[k_]):+.1f} dBFS at {k_ / 20:.2f} s')
        print('  blocks over 0 dBFS:', int(np.sum(pk_ > 1)), 'of', len(pk_))
    st = limit(st)
    post = lufs(st)
    if post < -14.3:                              # the limiter took a little off the loudest climax: make it up once
        st = limit(st * 10 ** ((-14.0 - post) / 20))
    print(f'loudness {integ:.1f} LUFS before gain, {lufs(st):.1f} LUFS after; peak {20 * np.log10(np.abs(st).max()):.2f} dBFS, '
          f'true peak {20 * np.log10(true_peak(st).max()):.2f} dBTP')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print('wrote', out, round(T, 2), 's')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio6.wav')
