"""Render all prototype voices, measure them, run a phone-speaker + discriminability check,
draw spectrograms, and build a short leitmotif scene."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from dsp import (SR, write_wav, phone_sim, yin, contour_summary, contour_string, spectral_stats,
                 rms_db, roughness_index, syllable_rate, pitch_survival, st, stft, smooth, periodicity)
from prosody import EMOTIONS
from voices import VOICES, Suikin, Babble, Robot, Creature, Iron, iron_strike, tine, bubble, additive

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'wav'
IMG = ROOT / 'img'
OUT.mkdir(exist_ok=True)
IMG.mkdir(exist_ok=True)
SHOW_SEED = {'babble': 100, 'suikin': 104, 'robot': 102, 'creature': 103, 'iron': 101}
N_SEEDS = 0 if '--quick' in sys.argv else 12


def limiter(x, thr=0.89, release=0.05):
    blk = 48
    nb = int(np.ceil(len(x) / blk))
    xp = np.zeros(nb * blk)
    xp[:len(x)] = np.abs(x)
    pk = xp.reshape(nb, blk).max(axis=1)
    pk = np.maximum(pk, np.concatenate([pk[1:], [0]]))  # 1 ms look-ahead
    g = np.ones(nb)
    cur = 1.0
    a = np.exp(-blk / (release * SR))
    for i in range(nb):
        target = min(1.0, thr / (pk[i] + 1e-12))
        cur = target if target < cur else target + (cur - target) * a
        g[i] = cur
    gs = np.repeat(g, blk)[:len(x)]
    gs = smooth(gs, 24)
    return np.tanh(x * gs / 0.95) * 0.95


def render(name, emotion, seed):
    v = VOICES[name]()
    rng = np.random.default_rng(seed)
    p = v.plan(emotion, rng)
    x = v.render(p, rng)
    return x, p


def window_end(p):
    end = p.syls[-1].t + p.syls[-1].d
    if p.sigh:
        end = max(end, p.sigh[0] + p.sigh[1])
    return int((end + 0.08) * SR)


def features(x, base):
    t, f0, _ = yin(x)
    cs = contour_summary(t, f0, base)
    rate, _ = syllable_rate(x)
    sp = spectral_stats(x)
    return np.array([
        st(cs.get('f0_median_hz', base), base) if 'f0_median_hz' in cs else np.nan,
        cs.get('f0_range_st', np.nan), cs.get('slope_end_st_s', np.nan),
        rate, rms_db(x), np.log2(sp['centroid_hz'] + 1), roughness_index(x), periodicity(x)])


FEAT_NAMES = ['f0_med_st', 'f0_range_st', 'slope_end', 'rate', 'rms_db', 'log2_centroid', 'roughness', 'periodicity']


def nearest_centroid_loo(X, y, Xtest=None):
    """leave-one-out nearest-centroid on z-scored features. Xtest: optional parallel set
    (e.g. phone-filtered) to classify with the model trained on X."""
    X = X.copy()
    col_mean = np.nanmean(X, axis=0)
    for j in range(X.shape[1]):
        X[np.isnan(X[:, j]), j] = col_mean[j]
    if Xtest is not None:
        Xtest = Xtest.copy()
        for j in range(Xtest.shape[1]):
            Xtest[np.isnan(Xtest[:, j]), j] = col_mean[j]
    labs = sorted(set(y))
    conf = np.zeros((len(labs), len(labs)), int)
    for i in range(len(X)):
        tr = np.arange(len(X)) != i
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        Z = (X[tr] - mu) / sd
        cents = {l: Z[np.array(y)[tr] == l].mean(0) for l in labs}
        q = ((Xtest[i] if Xtest is not None else X[i]) - mu) / sd
        pred = min(labs, key=lambda l: np.sum((q - cents[l]) ** 2))
        conf[labs.index(y[i]), labs.index(pred)] += 1
    return conf.trace() / conf.sum(), conf, labs


# ------------------------------------------------------------------ spectrogram png
def colormap(v):
    v = np.clip(v, 0, 1)[..., None]
    stops = np.array([[8, 8, 16], [30, 40, 120], [140, 40, 150], [240, 120, 40], [255, 245, 170]], float)
    pos = np.linspace(0, 1, len(stops))
    out = np.zeros(v.shape[:-1] + (3,))
    for c in range(3):
        out[..., c] = np.interp(v[..., 0], pos, stops[:, c])
    return out.astype(np.uint8)


def spectrogram_png(x, path, labels=None, base=None, title=''):
    X, pad = stft(x, 2048, 256)
    P = 20 * np.log10(np.abs(X) + 1e-9)
    P -= P.max()
    f = np.fft.rfftfreq(2048, 1 / SR)
    H, fmin, fmax = 320, 100.0, 12000.0
    rows = fmin * (fmax / fmin) ** (np.arange(H)[::-1] / (H - 1))
    img = np.empty((H, P.shape[0]))
    for i in range(P.shape[0]):
        img[:, i] = np.interp(rows, f, P[i])
    W = min(1600, P.shape[0])
    cols = np.linspace(0, P.shape[0] - 1, W).astype(int)
    img = img[:, cols]
    rgb = colormap((img + 70) / 70)
    top, left = 22, 46
    canvas = Image.new('RGB', (W + left + 4, H + top + 18), (250, 250, 248))
    canvas.paste(Image.fromarray(rgb), (left, top))
    d = ImageDraw.Draw(canvas)
    def yof(fr):
        return top + (H - 1) * (1 - np.log(fr / fmin) / np.log(fmax / fmin))
    for fr, lab in ((250, '250'), (450, '450'), (1000, '1k'), (2000, '2k'), (5000, '5k'), (10000, '10k')):
        yy = yof(fr)
        d.text((4, yy - 6), lab, fill=(40, 40, 40))
        d.line([(left - 4, yy), (left, yy)], fill=(40, 40, 40))
    yy = yof(450)
    for xx in range(left, left + W, 8):
        d.line([(xx, yy), (xx + 4, yy)], fill=(255, 60, 60))
    t, f0, _ = yin(x)
    sec_per_px = (len(x) / SR) / W
    for ti, fi in zip(t, f0):
        if not np.isnan(fi) and fmin < fi < fmax:
            px = left + ti / sec_per_px
            d.ellipse([px - 1, yof(fi) - 1, px + 1, yof(fi) + 1], fill=(80, 255, 255))
    if labels:
        for (t0, lab) in labels:
            d.text((left + t0 / sec_per_px + 3, top + H + 3), lab, fill=(20, 20, 20))
            d.line([(left + t0 / sec_per_px, top), (left + t0 / sec_per_px, top + H)], fill=(255, 255, 255))
    d.text((left, 4), title + '   (cyan = YIN f0, red dashes = 450 Hz phone cut)', fill=(20, 20, 20))
    canvas.save(path)


# ------------------------------------------------------------------ main
def main():
    results = {}
    clf = {}
    for name in VOICES:
        cls = VOICES[name]
        base = cls.base_hz
        raw = {e: render(name, e, SHOW_SEED[name]) for e in EMOTIONS}
        gain = 0.7 / max(np.percentile(np.abs(x), 99.9) for x, _ in raw.values())
        medley, labels, tpos = [], [], 0.0
        for e in EMOTIONS:
            x, p = raw[e]
            y = limiter(x * gain)
            write_wav(OUT / f'{name}_{e}.wav', y)
            yp = phone_sim(y)
            W = window_end(p)
            ya, ypa = y[:W], yp[:W]
            t, f0, _ = yin(ya)
            tp, f0p, _ = yin(ypa)
            e_full = np.sum(y ** 2)
            r = dict(file=str(OUT / f'{name}_{e}.wav'), dur_s=round(len(y) / SR, 2),
                     n_syl_planned=len(p.syls),
                     planned_rate_syl_s=round(len(p.syls) / (p.syls[-1].t + p.syls[-1].d - p.syls[0].t), 2),
                     peak_dbfs=round(20 * np.log10(np.abs(y).max() + 1e-12), 1),
                     rms_active_dbfs=round(rms_db(ya), 1), periodicity=round(periodicity(ya), 3))
            r.update(contour_summary(t, f0, base))
            r['contour_hz_50ms'] = contour_string(t, f0)
            r['measured_rate_peaks_s'] = round(syllable_rate(ya)[0], 2)
            r['roughness_30_150'] = round(roughness_index(ya), 3)
            r.update(spectral_stats(ya))
            ph = dict(energy_kept_db=round(10 * np.log10(np.sum(yp ** 2) / e_full), 1),
                      rms_active_dbfs=round(rms_db(ypa), 1), periodicity=round(periodicity(ypa), 3))
            ph.update({k: v for k, v in spectral_stats(ypa).items() if k == 'centroid_hz'})
            ph.update(pitch_survival(ya, ypa, base))
            cp = contour_summary(tp, f0p, base)
            ph['f0_median_hz'] = cp.get('f0_median_hz')
            ph['f0_range_st'] = cp.get('f0_range_st')
            r['phone450'] = ph
            results[f'{name}_{e}'] = r
            labels.append((tpos, e))
            medley.append(y)
            medley.append(np.zeros(int(0.6 * SR)))
            tpos += len(y) / SR + 0.6
        med = np.concatenate(medley)
        write_wav(OUT / f'{name}_medley.wav', med)
        write_wav(OUT / f'{name}_medley_phone450.wav', limiter(phone_sim(med) * 1.6))
        spectrogram_png(med, IMG / f'{name}_medley.png', labels, base, f'{name}: happy / sad / angry / surprised')
        # discriminability check on fresh utterances (same per-voice gain, so loudness cues are kept)
        Xf, Xp, ylab = [], [], []
        for e in EMOTIONS:
            for s in range(N_SEEDS):
                x, p = render(name, e, 1000 + s)
                y = limiter(x * gain)[:window_end(p)]
                Xf.append(features(y, base))
                Xp.append(features(phone_sim(y), base))
                ylab.append(e)
        if not N_SEEDS:
            continue
        Xf, Xp = np.array(Xf), np.array(Xp)
        np.savez(ROOT / f'features_{name}.npz', Xf=Xf, Xp=Xp, y=np.array(ylab))
        acc_f, conf_f, labs = nearest_centroid_loo(Xf, ylab)
        acc_p, conf_p, _ = nearest_centroid_loo(Xp, ylab)
        acc_x, conf_x, _ = nearest_centroid_loo(Xf, ylab, Xp)
        means = {e: {fn: round(float(np.nanmean(Xf[np.array(ylab) == e][:, j])), 2)
                     for j, fn in enumerate(FEAT_NAMES)} for e in EMOTIONS}
        clf[name] = dict(labels=labs, acc_full=round(acc_f, 3), acc_phone=round(acc_p, 3),
                         acc_train_full_test_phone=round(acc_x, 3),
                         conf_full=conf_f.tolist(), conf_phone=conf_p.tolist(), conf_cross=conf_x.tolist(),
                         feature_means_full=means)
        print(name, 'acc full', round(acc_f, 3), 'phone', round(acc_p, 3), 'cross', round(acc_x, 3), flush=True)
    json.dump(dict(per_file=results, discriminability=clf), open(ROOT / 'measurements.json', 'w'), indent=1)
    return results, clf


if __name__ == '__main__':
    main()
