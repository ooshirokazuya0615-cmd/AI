"""v2 soundtrack, on the same clock as short2.py (score2.py):
marimba melody, warm bass for the dominoes (plus a wooden click), a "pok" for the paddle,
the drum, four glass bells, a confetti sparkle and a soft A-minor pad under the reveal.

    python audio2.py out.wav
"""
import sys
import wave

import numpy as np

import score2 as S

SR = 48000
rng = np.random.default_rng(3)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_t(n):
    return np.arange(n) / SR


def marimba(m, length=1.6):
    f, t = hz(m), env_t(int(SR * length))
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2) + 0.35 * np.sin(2 * np.pi * f * 3.99 * t) * np.exp(-t * 11)
         + 0.12 * np.sin(2 * np.pi * f * 9.9 * t) * np.exp(-t * 30) + 0.18 * np.sin(2 * np.pi * f * 2 * t + 0.3) * np.exp(-t * 2))
    return s * np.minimum(1, t / 0.003)


def bass(m, length=1.8):
    f, t = hz(m), env_t(int(SR * length))
    s = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3) + 0.2 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 6)
    return s * np.exp(-t * 2.2) * np.minimum(1, t / 0.006)


def click(length=0.06, tone=2400):
    t = env_t(int(SR * length))
    return (rng.standard_normal(len(t)) * 0.5 + np.sin(2 * np.pi * tone * t)) * np.exp(-t * 90)


def bell(m, length=2.6):
    f, t = hz(m), env_t(int(SR * length))
    parts = [(1.0, 1.0, 1.4), (2.76, 0.45, 2.6), (5.40, 0.25, 4.5), (8.93, 0.12, 7.0)]
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for r, a, d in parts)
    return s * np.minimum(1, t / 0.002)


def drum(length=1.6):
    t = env_t(int(SR * length))
    fd = 75 * np.exp(-t * 7) + 42
    s = 1.3 * np.sin(2 * np.pi * np.cumsum(fd) / SR) * np.exp(-t * 4)
    s += 0.35 * rng.standard_normal(len(t)) * np.exp(-t * 22)
    return s


def pad(midis, length):
    t = env_t(int(SR * length))
    s = sum(np.sin(2 * np.pi * hz(m) * t) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.003 * t) for m in midis)
    a = np.minimum(1, t / 0.9) * np.minimum(1, (length - t) / 1.2)
    return s * a / len(midis)


def sparkle(length=1.8):
    n = int(SR * length)
    s = np.zeros(n)
    for _ in range(40):
        a = int(rng.uniform(0, 0.75) * n)
        g = bell(int(rng.choice([88, 91, 93, 96, 100])), 0.4)[: n - a] * 0.12 * rng.uniform(0.3, 1)
        s[a:a + len(g)] += g
    return s


def place(mix, s, t, gain):
    a = int(t * SR)
    if a >= len(mix):
        return
    s = s[: len(mix) - a]
    mix[a:a + len(s)] += s * gain


def main(out):
    T = S.total_seconds()
    mix = np.zeros(int(SR * (T + 0.5)))
    mel = S.melody()
    for h in mel:
        if h['kind'] == 'drum':
            place(mix, marimba(h['midi'], 2.4), h['t'], 0.34)
            place(mix, drum(), h['t'], 0.55)
            place(mix, bass(45, 2.4), h['t'], 0.30)
        elif h['kind'] == 'paddle':
            place(mix, marimba(h['midi']), h['t'], 0.36)
            place(mix, click(0.09, 900), h['t'], 0.35)
        else:
            place(mix, marimba(h['midi']), h['t'], 0.32)
        place(mix, click(0.02, 3000), h['t'], 0.05)
    for b in S.bass():
        place(mix, bass(b['midi']), b['t'], 0.26)
        place(mix, click(0.04, 1600), b['t'] + S.UNIT * 0.95, 0.10)
    for g in S.tag():
        place(mix, bell(g['midi']), g['t'], 0.22)
    tl = S.t_last()
    place(mix, sparkle(), tl + S.CONFETTI_AT, 1.0)
    place(mix, pad([57, 60, 64, 69], T - tl - 0.9), tl + 0.9, 0.16)
    # reverb
    ir_len = int(SR * 2.0)
    ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / (SR * 0.5)) * 0.011
    ir[0] = 1.0
    n = len(mix) + ir_len
    wet = np.fft.irfft(np.fft.rfft(mix, n) * np.fft.rfft(ir, n))[: len(mix)]
    mix = 0.72 * mix + 0.28 * wet
    mix = mix[: int(SR * T)]
    fade = int(SR * 0.8)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.max(np.abs(mix)) / 0.89
    # slight stereo: bells and sparkle feel wider via a tiny delay on the right channel
    right = np.concatenate([np.zeros(int(SR * 0.004)), mix[:-int(SR * 0.004)]])
    st = np.stack([mix, 0.85 * mix + 0.15 * right], 1)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print('wrote', out, round(T, 2), 's')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio2.wav')
