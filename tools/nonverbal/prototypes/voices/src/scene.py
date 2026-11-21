"""~20 s leitmotif demo: Peter-and-the-Wolf style, one timbre family per character.
heroine = SUIKIN glass bead (pentatonic call), friend = soft creature, villain = rusty iron (tritone).
Story beat: greeting -> villain bullies friend -> heroine surprised, then angry -> villain gets his
comeuppance (screech, clatter, sag) -> tritone resolves into the heroine's pentatonic -> joy + logo."""
from pathlib import Path

import numpy as np

from dsp import SR, write_wav, phone_sim, lpf
from voices import Suikin, Creature, Iron, iron_strike, tine, bubble
from make_all import limiter, spectrogram_png

ROOT = Path(__file__).resolve().parent.parent


def utt(cls, emo, seed, max_s=None):
    v = cls()
    rng = np.random.default_rng(seed)
    p = v.plan(emo, rng)
    x = v.render(p, rng)
    if max_s and len(x) > max_s * SR:
        m = int(max_s * SR)
        x = x[:m] * np.concatenate([np.ones(m - 2400), np.linspace(1, 0, 2400)])
    return x / (np.sqrt(np.mean(x[np.abs(x) > 1e-4 * np.abs(x).max()] ** 2)) + 1e-12)


LEVEL = {'happy': 0.0, 'sad': -8.0, 'angry': 2.0, 'surprised': 1.0}


def reverb(st, seconds=1.4, wet=0.16, seed=3):
    rng = np.random.default_rng(seed)
    n_ir = int(seconds * SR)
    t = np.arange(n_ir) / SR
    out = st.copy()
    N = 1 << int(np.ceil(np.log2(len(st) + n_ir)))
    for ch in (0, 1):
        ir = lpf(rng.standard_normal(n_ir), 6000) * np.exp(-t * 6.9 / seconds)
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, ch] += wet * np.fft.irfft(np.fft.rfft(st[:, ch], N) * np.fft.rfft(ir, N), N)[:len(st)]
    return out


def main():
    rng = np.random.default_rng(9)
    T = 21.5
    mix = np.zeros((int(T * SR), 2))
    marks = []

    def put(at, x, pan=0.0, db=0.0, label=None):
        i = int(at * SR)
        m = min(len(x), len(mix) - i)
        a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        g = 10 ** (db / 20) * 0.08
        mix[i:i + m, 0] += x[:m] * np.cos(a) * g
        mix[i:i + m, 1] += x[:m] * np.sin(a) * g
        if label:
            marks.append((at, label))

    S = Suikin()
    call = S.call(rng)
    put(0.0, call / np.sqrt(np.mean(call ** 2)), -0.1, -2, 'logo')
    put(1.3, utt(Suikin, 'happy', 104), -0.15, LEVEL['happy'], 'hero:happy')
    put(3.3, utt(Creature, 'happy', 103), 0.4, LEVEL['happy'] - 1, 'friend:happy')
    # villain entrance: tritone clang (D4 + G#4 bar partials)
    clang = sum(iron_strike(f, 2.0, rng, 1.0) for f in (293.7, 415.3))
    put(5.3, clang / np.sqrt(np.mean(clang[:SR] ** 2)), -0.5, 0, 'villain:clang')
    put(5.7, utt(Iron, 'happy', 101), -0.5, LEVEL['happy'], 'villain:smug')
    put(8.0, utt(Creature, 'sad', 103, max_s=2.6), 0.4, LEVEL['sad'] + 3, 'friend:sad')
    put(10.7, utt(Suikin, 'surprised', 104), -0.1, LEVEL['surprised'], 'hero:surprised')
    put(12.1, utt(Suikin, 'angry', 104), -0.1, LEVEL['angry'], 'hero:angry')
    put(13.7, utt(Iron, 'surprised', 101), -0.5, LEVEL['surprised'], 'villain:surprised')
    put(15.0, utt(Iron, 'sad', 101, max_s=1.8), -0.5, LEVEL['sad'] + 4, 'villain:defeat')
    # payoff: tritone D-G# resolves (G# -> A): rust becomes glass, then pentatonic bloom
    t0 = 16.9
    d1 = sum(iron_strike(f, 0.6, rng, 0.3) for f in (293.7, 415.3))
    put(t0, d1 / np.sqrt(np.mean(d1[:SR // 4] ** 2)), -0.3, -4, 'resolve')
    fifth = tine(587.3, 2.5, 1.0, 1.2) + tine(880.0, 2.5, 1.0, 1.2)
    put(t0 + 0.28, fifth / np.sqrt(np.mean(fifth[:SR // 2] ** 2)), 0.0, -3)
    for j, semi in enumerate((0, 4, 7, 9, 12, 16)):
        x = tine(784.0 * 2 ** (semi / 12), 2.0, 0.8, 0.9)
        put(t0 + 0.5 + 0.07 * j, x / np.sqrt(np.mean(x[:SR // 4] ** 2)), -0.4 + 0.16 * j, -9)
        b = bubble(1568 * 2 ** (semi / 12), 0.6, 0.025)
        put(t0 + 0.53 + 0.07 * j, b / np.sqrt(np.mean(b ** 2)), 0.4 - 0.16 * j, -16)
    put(18.0, utt(Creature, 'happy', 7), 0.4, LEVEL['happy'] - 1, 'friend:joy')
    callh = S.call(rng, tempo=0.2, harmonize=True)
    put(19.4, callh / np.sqrt(np.mean(callh ** 2)), 0.0, -1, 'logo(harmonized)')
    mix = reverb(mix)
    peak = np.abs(mix).max()
    mix = np.stack([limiter(mix[:, 0] / peak * 0.95), limiter(mix[:, 1] / peak * 0.95)], axis=1)
    write_wav(ROOT / 'wav' / 'scene_leitmotif_demo.wav', mix)
    mono = mix.mean(axis=1)
    write_wav(ROOT / 'wav' / 'scene_leitmotif_demo_phone450.wav', limiter(phone_sim(mono) * 1.5))
    spectrogram_png(mono, ROOT / 'img' / 'scene_leitmotif_demo.png', marks, None, 'leitmotif scene demo')
    print('scene ok', len(mix) / SR, 's', marks)


if __name__ == '__main__':
    main()
