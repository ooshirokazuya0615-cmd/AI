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


def main(out):
    T = S.total_seconds()
    mix = np.zeros((int(SR * (T + 0.5)), 2))
    C, GAPS = S.timeline()
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
                tb = t0
                for n_, u_ in acc['bass']:
                    place(mix, s_piano(S.midi(n_), u_ * song['unit'] + 0.5), tb, 0.16, -0.25)
                    tb += u_ * song['unit']
            if acc.get('arpeggio'):
                lh = {69: ['A2', 'E3', 'A3'], 71: ['E2', 'E3', 'G#3'], 72: ['A2', 'E3', 'A3']}
                for h in hs:
                    if h['dur'] >= 3 * song['unit'] - 1e-6 and h['midi'] in lh:
                        for j, n_ in enumerate(lh[h['midi']]):
                            place(mix, s_piano(S.midi(n_), 1.2), h['t'] + j * song['unit'], 0.14, -0.25)
            if acc.get('octave'):
                for h in hs:
                    if h['mech'] != 'again' or True:
                        place(mix, s_piano(h['midi'] - 12, max(0.4, h['dur'] + 0.3)), h['t'], 0.14, -0.2)
        else:
            r, f5 = song['drone']
            if sampler.available():
                beat = song['beat']
                k = 0
                while t0 + k * 2 * beat < t1:
                    for m in (S.midi(r) + 12, S.midi(f5) + 12):
                        place(mix, s_piano(m, 2 * beat + 0.4), t0 + k * 2 * beat, 0.07)
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
    if ev and os.path.exists(ev):
        import json
        E = json.load(open(ev))
        for r in E['returns'] + E['gaps']:
            place(mix, click(0.04, 900, 60), r['t0'], 0.22)                  # into the funnel
            place(mix, whoosh(max(0.2, r['t1'] - r['t0'])), r['t0'], 0.07)  # through the tube
            place(mix, click(0.04, 1300, 70), r['t1'], 0.18)                 # out at the next row
    fin = C[-1]
    place(mix, click(0.05, 700, 45), fin['launch'] - 0.28, 0.18)
    place(mix, click(0.08, 400, 35), fin['launch'], 0.5)
    place(mix, whoosh(fin['t'] - fin['launch']), fin['launch'], 0.05)
    ir_len = int(SR * 1.8)
    outs = []
    for ch in range(2):
        ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / (SR * 0.45)) * 0.010
        ir[0] = 1.0
        L = len(mix) + ir_len
        wet = np.fft.irfft(np.fft.rfft(mix[:, ch], L) * np.fft.rfft(ir, L))[: len(mix)]
        outs.append(0.74 * mix[:, ch] + 0.26 * wet)
    st = np.stack(outs, 1)[: int(SR * T)]
    fade = int(SR * 0.8)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    blk = int(SR * 0.4)
    ms = np.array([np.mean(st[k:k + blk] ** 2) for k in range(0, len(st) - blk, blk // 4)])
    lufs = -0.691 + 10 * np.log10(ms + 1e-12)
    gated = ms[lufs > -70]
    rel = -0.691 + 10 * np.log10(np.mean(gated)) - 10
    gated = ms[(lufs > -70) & (lufs > rel)]
    integ = -0.691 + 10 * np.log10(np.mean(gated))
    st *= 10 ** ((-14.0 - integ) / 20)
    ceil = 10 ** (-1.0 / 20)
    st = np.where(np.abs(st) > ceil * 0.8, np.sign(st) * (ceil * 0.8 + (ceil * 0.2) * np.tanh((np.abs(st) - ceil * 0.8) / (ceil * 0.2))), st)
    print('integrated loudness before gain (approx LUFS):', round(float(integ), 1))
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print('wrote', out, round(T, 2), 's')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio6.wav')
