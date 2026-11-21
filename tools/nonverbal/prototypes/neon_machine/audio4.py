"""v4 soundtrack on the score4.py clock: each contact has the timbre of its mechanism, a soft accompaniment
under each song, and real silence in the gaps (only the rolling of the ball, the switch click and a soft whoosh).

    python audio4.py out.wav
"""
import sys
import wave

import numpy as np

import score4 as S

SR = 48000
rng = np.random.default_rng(5)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(sec):
    return np.arange(int(SR * sec)) / SR


def marimba(m, L=1.5):
    f, t = hz(m), tt(L)
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.4) + 0.35 * np.sin(2 * np.pi * f * 3.99 * t) * np.exp(-t * 12)
         + 0.1 * np.sin(2 * np.pi * f * 9.9 * t) * np.exp(-t * 30))
    return s * np.minimum(1, t / 0.003)


def synth_pluck(m, L=1.2):
    """bright neon pluck for the LED tiles"""
    f, t = hz(m), tt(L)
    saw = sum(np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (2.5 + k * 1.8)) for k in range(1, 9))
    return saw * 0.9 * np.minimum(1, t / 0.002)


def block_tone(m, L=1.4):
    """hollow wooden synth block"""
    f, t = hz(m), tt(L)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 4.5) + 0.5 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t * 9)
    s += 0.25 * np.sin(2 * np.pi * f * 0.5 * t) * np.exp(-t * 3)
    return s * np.minimum(1, t / 0.002)


def piano(m, L=1.6):
    f, t = hz(m), tt(L)
    s = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in ((1, 1.0), (2, 0.35), (3, 0.15), (4, 0.06)))
    return s * np.exp(-t * 2.2) * np.minimum(1, t / 0.005)


def bass(m, L=1.0):
    f, t = hz(m), tt(L)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return s * np.exp(-t * 1.6) * np.minimum(1, t / 0.01) * np.minimum(1, (L - t) / 0.05)


def pad(m, L):
    f, t = hz(m), tt(L)
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.003 * t) + 0.2 * np.sin(2 * np.pi * f * 0.998 * t)
    return s * np.minimum(1, t / 0.15) * np.minimum(1, (L - t) / 0.2)


def click(L=0.05, tone=2600, decay=90):
    t = tt(L)
    return (rng.standard_normal(len(t)) * 0.5 + np.sin(2 * np.pi * tone * t)) * np.exp(-t * decay)


def drum(L=1.6):
    t = tt(L)
    fd = 80 * np.exp(-t * 7) + 44
    return 1.3 * np.sin(2 * np.pi * np.cumsum(fd) / SR) * np.exp(-t * 3.6) + 0.35 * rng.standard_normal(len(t)) * np.exp(-t * 20)


def roll(L):
    """quiet rolling rumble of the ball on the rail"""
    n = int(SR * L)
    x = rng.standard_normal(n)
    k = int(SR / 900)
    x = np.convolve(x, np.ones(k) / k, mode='same')
    x *= 0.6 + 0.4 * np.sin(2 * np.pi * 7 * np.arange(n) / SR)
    env = np.minimum(1, np.arange(n) / (0.1 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.1 * SR))
    return x * env


def whoosh(L=1.0):
    n = int(SR * L)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for j, k in enumerate((40, 30, 22, 16)):
        seg = slice(j * n // 4, (j + 1) * n // 4)
        out[seg] = np.convolve(x, np.ones(k) / k, mode='same')[seg]
    return out * np.sin(np.pi * np.arange(n) / n) ** 2


def place(mix, s, t, g):
    a = int(t * SR)
    if 0 <= a < len(mix):
        s = s[: len(mix) - a]
        mix[a:a + len(s)] += s * g


def main(out):
    T = S.total_seconds()
    mix = np.zeros(int(SR * (T + 0.5)))
    n = S.notes()
    for h in n:
        m = h['mech']
        if m == 'tile':
            place(mix, synth_pluck(h['midi']), h['t'], 0.26)
        elif m == 'block':
            place(mix, block_tone(h['midi']), h['t'], 0.34)
        elif m == 'bigdrum':
            place(mix, marimba(h['midi'], 2.5), h['t'], 0.34)
            place(mix, drum(), h['t'], 0.55)
            for c in (48, 55, 60, 64, 67, 72):
                place(mix, pad(c, 3.2), h['t'], 0.06)
        else:
            place(mix, marimba(h['midi']), h['t'], 0.33)
        place(mix, click(0.02, 3200), h['t'], 0.06)
    for t0, midi, dur, voice in S.accompaniment():
        if voice == 'piano':
            place(mix, piano(midi), t0, 0.13)
        elif voice == 'bass':
            place(mix, bass(midi, dur), t0, 0.16)
        else:
            place(mix, pad(midi, dur), t0, 0.035)
    g = S.gap1()
    place(mix, roll(g['switch'] - g['t0'] - 0.35), g['t0'] + 0.38, 0.05)
    place(mix, click(0.07, 1500, 60), g['switch'], 0.5)
    place(mix, click(0.03, 4000, 120), g['switch'] + 0.05, 0.2)
    spring = n[-2]
    place(mix, click(0.06, 700, 50), spring['t'], 0.35)
    place(mix, whoosh(S.FERMATA + 0.1), spring['t'] + 0.05, 0.05)
    ir_len = int(SR * 1.8)
    ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / (SR * 0.42)) * 0.010
    ir[0] = 1.0
    L = len(mix) + ir_len
    wet = np.fft.irfft(np.fft.rfft(mix, L) * np.fft.rfft(ir, L))[: len(mix)]
    mix = (0.74 * mix + 0.26 * wet)[: int(SR * T)]
    fade = int(SR * 0.8)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.max(np.abs(mix)) / 0.89
    d = int(SR * 0.004)
    right = np.concatenate([np.zeros(d), mix[:-d]])
    st = np.stack([mix, 0.85 * mix + 0.15 * right], 1)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print('wrote', out, round(T, 2), 's')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio4.wav')
