"""Soundtrack for film6.py, on the same clock (songs6.timeline or another SONGS_MODULE).

Each contact has the timbre of its instrument; under each song a soft drone (or, when the module sets
DRUMS, a rock beat with bass on the bar chords); the gaps are silent except for the machine's own sounds,
which fall on the counted beats.

    SONGS_MODULE=songs_kimetsu python audio6.py out.wav
"""
import importlib
import os
import sys
import wave

import numpy as np

S = importlib.import_module(os.environ.get('SONGS_MODULE', 'songs6'))
SR = 48000
rng = np.random.default_rng(9)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(sec):
    return np.arange(int(SR * sec)) / SR


def env(t, a, d):
    return np.minimum(1, t / a) * np.exp(-t * d)


def marimba(m, L=1.4):
    f, t = hz(m), tt(L)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.4) + 0.35 * np.sin(2 * np.pi * f * 3.99 * t) * np.exp(-t * 12)) * np.minimum(1, t / 0.003)


def pluck(m, L=1.1):
    f, t = hz(m), tt(L)
    return sum(np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (2.5 + k * 1.8)) for k in range(1, 9)) * np.minimum(1, t / 0.002)


def bellv(m, L=2.2):
    f, t = hz(m), tt(L)
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in
               ((1, 1, 1.6), (2.76, .45, 2.8), (5.4, .25, 4.5), (8.93, .12, 7))) * np.minimum(1, t / 0.002)


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


def whoosh(L):
    n = int(SR * L)
    x = np.convolve(rng.standard_normal(n), np.ones(30) / 30, mode='same')
    return x * np.sin(np.pi * np.arange(n) / n) ** 2


VOICE = dict(tile=(pluck, 0.24), pad=(marimba, 0.32), again=(marimba, 0.32), block=(wood, 0.34), cup=(marimba, 0.32),
             xylo=(marimba, 0.30), bell=(bellv, 0.22), cymbal=(marimba, 0.28), flask=(glass, 0.24), pipe=(organ, 0.20),
             bumper=(pluck, 0.26))
CHORD = {'Dm': (38, [62, 65, 69]), 'C': (36, [60, 64, 67]), 'Bb': (34, [58, 62, 65]), 'A': (33, [61, 64, 69]),
         'Am': (33, [60, 64, 69]), 'G': (31, [59, 62, 67])}


def place(mix, s, t, g):
    a = int(t * SR)
    if 0 <= a < len(mix):
        s = s[: len(mix) - a]
        mix[a:a + len(s)] += s * g


def main(out):
    T = S.total_seconds()
    mix = np.zeros(int(SR * (T + 0.5)))
    C, GAPS = S.timeline()
    for h in C:
        if h['mech'] == 'bigdrum':
            place(mix, drum(), h['t'], 0.55)
            place(mix, marimba(h['midi'], 2.5), h['t'], 0.34)
            for c in (h['midi'] - 24, h['midi'] - 17, h['midi'] - 12, h['midi'] - 9, h['midi'] - 5, h['midi']):
                place(mix, pad(c, 3.2), h['t'], 0.06)
            continue
        fn, g = VOICE[h['mech']]
        place(mix, fn(h['midi']), h['t'], g)
        if h['mech'] == 'cymbal':
            place(mix, cymbal_hit(), h['t'], 0.18)
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
        else:
            r, f5 = song['drone']
            for m in (S.midi(r), S.midi(f5)):
                place(mix, pad(m, t1 - t0), t0, 0.05)
    for g in GAPS:
        if g['kind'] == 'rail':
            place(mix, roll(g['beats'][3] - g['t0']), g['t0'], 0.035)
            for tb in g['beats'][:3]:
                place(mix, click(0.04, 1100, 80), tb, 0.22)
            place(mix, click(0.07, 1500, 60), g['beats'][3], 0.55)
        elif g['kind'] == 'chute':
            for j, tb in enumerate(g['beats']):
                place(mix, click(0.05, 1800 + 200 * j, 70), tb, 0.2)
        else:
            for tb in g['beats'][:2]:
                place(mix, click(0.05, 700, 45), tb, 0.25)
            place(mix, click(0.08, 400, 35), g['beats'][2], 0.5)
            place(mix, whoosh(g['t1'] - g['beats'][2]), g['beats'][2], 0.05)
    fin = C[-1]
    b = S.SONGS[-1]['beat']
    for j in (2, 3):
        place(mix, click(0.05, 600 + 150 * j, 45), C[-2]['t'] + j * b, 0.25)
    place(mix, click(0.08, 400, 35), fin['launch'], 0.5)
    place(mix, whoosh(fin['t'] - fin['launch']), fin['launch'], 0.05)
    ir_len = int(SR * 1.6)
    ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / (SR * 0.4)) * 0.010
    ir[0] = 1.0
    L = len(mix) + ir_len
    wet = np.fft.irfft(np.fft.rfft(mix, L) * np.fft.rfft(ir, L))[: len(mix)]
    mix = (0.76 * mix + 0.24 * wet)[: int(SR * T)]
    fade = int(SR * 0.8)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.max(np.abs(mix)) / 0.89
    d = int(SR * 0.004)
    st = np.stack([mix, 0.85 * mix + 0.15 * np.concatenate([np.zeros(d), mix[:-d]])], 1)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print('wrote', out, round(T, 2), 's')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio6.wav')
