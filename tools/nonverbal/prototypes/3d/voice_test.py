"""Formant 'creature voice' prototype in pure numpy (no samples): pitch-contoured glottal
source -> 3 time-varying resonators. Emotions are pitch contours + vowel paths."""
import time, wave
import numpy as np
SR = 48000

def resonate(x, f, bw):
    """time-varying 2-pole resonator; f, bw arrays (Hz) per sample."""
    r = np.exp(-np.pi * bw / SR); c = 2 * r * np.cos(2 * np.pi * f / SR); d = -r * r
    y = np.zeros_like(x); y1 = y2 = 0.0
    g = (1 - r)
    for i in range(len(x)):
        y0 = g[i] * x[i] + c[i] * y1 + d[i] * y2
        y[i] = y0; y2 = y1; y1 = y0
    return y

VOW = {'a': (800, 1200, 2600), 'o': (500, 850, 2500), 'u': (350, 700, 2400),
       'i': (300, 2300, 3000), 'e': (500, 1900, 2600)}

def creature(syll, f0_path, dur, size=1.35, breath=0.08, seed=0):
    """syll: vowel sequence e.g. 'uwa' -> 'u','a'; f0_path: (t_rel, hz) keypoints; size scales formants up (small cute)."""
    n = int(dur * SR); t = np.arange(n) / SR
    kt, kf = zip(*f0_path); f0 = np.interp(t / dur, kt, kf)
    f0 *= 1 + 0.012 * np.sin(2 * np.pi * 5.5 * t)            # vibrato
    ph = np.cumsum(f0) / SR
    src = (2 * (ph % 1.0) - 1.0)                              # saw
    src = src - np.concatenate([[0], src[:-1]]) * 0.6        # tilt
    src += breath * np.random.default_rng(seed).standard_normal(n)
    vs = [VOW[v] for v in syll]
    pos = np.linspace(0, len(vs) - 1, n)
    out = np.zeros(n)
    for k, bw0 in zip(range(3), (90, 110, 160)):
        fk = np.interp(pos, range(len(vs)), [v[k] * size for v in vs])
        out += resonate(src, fk, np.full(n, bw0 * size)) * (1.0, 0.6, 0.25)[k]
    env = np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.08)
    return out * env / (np.abs(out).max() + 1e-9)

t0 = time.time()
clips = {
  'happy_puwa':  creature('ua', [(0, 420), (0.3, 620), (1, 700)], 0.45),
  'sad_uuu':     creature('uo', [(0, 380), (0.6, 300), (1, 220)], 0.9, breath=0.15),
  'angry_villain': creature('ao', [(0, 140), (0.5, 120), (1, 100)], 0.6, size=0.8, breath=0.25),
  'surprise_i':  creature('ei', [(0, 500), (0.2, 900), (1, 950)], 0.3),
}
el = time.time() - t0
total = sum(len(c) for c in clips.values()) / SR
print(f'synth {total:.2f} s of voice in {el:.2f} s ({el/total:.2f} s per s)')
buf = np.concatenate([np.concatenate([c, np.zeros(int(0.3*SR))]) for c in clips.values()])
for name, c in clips.items():
    spec = np.abs(np.fft.rfft(c * np.hanning(len(c)))); fr = np.fft.rfftfreq(len(c), 1/SR)
    band = (fr > 200) & (fr < 4000)
    print(name, 'spectral centroid %.0f Hz' % (np.sum(fr[band]*spec[band])/np.sum(spec[band])))
pcm = (np.clip(buf * 0.8, -1, 1) * 32767).astype('<i2')
with wave.open('voice/creature_voice_test.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('wrote voice/creature_voice_test.wav', len(buf)/SR, 's')
