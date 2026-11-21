"""Render the soundtrack: a soft marimba/bell for each hit, a deep drum on the last note, light reverb.

    python audio.py out.wav
"""
import sys
import wave

import numpy as np

from score import hits, total_seconds

SR = 48000


def tone(midi, dur, last=False):
    f = 440.0 * 2 ** ((midi - 69) / 12)
    n = int(SR * (dur + 1.6))
    t = np.arange(n) / SR
    # marimba-like: fundamental + 4th and 10th partials, fast decay on the upper ones
    s = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.2)
         + 0.35 * np.sin(2 * np.pi * f * 3.99 * t) * np.exp(-t * 11)
         + 0.12 * np.sin(2 * np.pi * f * 9.9 * t) * np.exp(-t * 30))
    # glassy bell shimmer to match the neon look
    s += 0.18 * np.sin(2 * np.pi * f * 2.0 * t + 0.3) * np.exp(-t * 2.0)
    attack = np.minimum(1, t / 0.003)
    s *= attack
    if last:
        # deep drum under the final note
        fd = 70 * np.exp(-t * 6) + 45
        s += 1.4 * np.sin(2 * np.pi * np.cumsum(fd) / SR) * np.exp(-t * 4.5)
        s += 0.25 * np.random.default_rng(1).standard_normal(n) * np.exp(-t * 25)
    return s


def main(out):
    T = total_seconds()
    mix = np.zeros(int(SR * (T + 2)))
    hs = hits()
    for i, h in enumerate(hs):
        s = tone(h['midi'], h['dur'], last=(i == len(hs) - 1))
        a = int(h['t'] * SR)
        mix[a:a + len(s)] += s[:len(mix) - a] * 0.32
    # tiny "tick" of the ball touching the bar
    rng = np.random.default_rng(0)
    for h in hs:
        a = int(h['t'] * SR)
        k = np.exp(-np.arange(400) / 60) * rng.standard_normal(400) * 0.05
        mix[a:a + 400] += k
    # simple reverb: a few decaying echoes, then a diffuse noise tail via FFT convolution
    ir_len = int(SR * 1.8)
    ir = rng.standard_normal(ir_len) * np.exp(-np.arange(ir_len) / (SR * 0.45)) * 0.012
    ir[0] = 1.0
    wet = np.fft.irfft(np.fft.rfft(mix, len(mix) + ir_len) * np.fft.rfft(ir, len(mix) + ir_len))[:len(mix)]
    mix = 0.75 * mix + 0.25 * wet
    mix = mix[:int(SR * T)]
    fade = int(SR * 0.6)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.max(np.abs(mix)) / 0.89
    st = np.stack([mix, mix], 1)
    with wave.open(out, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print('wrote', out, round(T, 2), 's')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav')
