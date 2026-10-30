"""Cue ablations + cross-voice transfer of the emotional code, from saved feature sets."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
NAMES = ['babble', 'suikin', 'robot', 'creature', 'iron']
FEAT = ['f0_med_st', 'f0_range_st', 'slope_end', 'rate', 'rms_db', 'log2_centroid', 'roughness', 'periodicity']
SUBSETS = {
    'all': [0, 1, 2, 3, 4, 5, 6, 7],
    'pitch_only(f0 level,range,end slope)': [0, 1, 2],
    'no_level(all but rms)': [0, 1, 2, 3, 5, 6, 7],
    'timbre_only(centroid,roughness,periodicity)': [5, 6, 7],
    'tempo+level_only(rate,rms)': [3, 4],
}


def fill(X):
    X = X.copy()
    m = np.nanmean(X, axis=0)
    for j in range(X.shape[1]):
        X[np.isnan(X[:, j]), j] = m[j] if not np.isnan(m[j]) else 0.0
    return X


def loo(X, y):
    X = fill(X)
    labs = sorted(set(y))
    ok = 0
    for i in range(len(X)):
        tr = np.arange(len(X)) != i
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        Z = (X[tr] - mu) / sd
        c = {l: Z[y[tr] == l].mean(0) for l in labs}
        q = (X[i] - mu) / sd
        ok += min(labs, key=lambda l: np.sum((q - c[l]) ** 2)) == y[i]
    return ok / len(X)


def speaker_norm(X):
    X = fill(X)
    return (X - X.mean(0)) / (X.std(0) + 1e-9)


def transfer(Xa, ya, Xb, yb):
    A, B = speaker_norm(Xa), speaker_norm(Xb)
    labs = sorted(set(ya))
    c = {l: A[ya == l].mean(0) for l in labs}
    pred = np.array([min(labs, key=lambda l: np.sum((q - c[l]) ** 2)) for q in B])
    return float(np.mean(pred == yb))


def main():
    data = {n: np.load(ROOT / f'features_{n}.npz') for n in NAMES}
    abl = {}
    for n in NAMES:
        d = data[n]
        y = d['y']
        abl[n] = {s: dict(full=round(loo(d['Xf'][:, idx], y), 3), phone=round(loo(d['Xp'][:, idx], y), 3))
                  for s, idx in SUBSETS.items()}
    xfer = {}
    for cond in ('Xf', 'Xp'):
        M = {}
        for a in NAMES:
            M[a] = {b: round(transfer(data[a][cond], data[a]['y'], data[b][cond], data[b]['y']), 3)
                    for b in NAMES if b != a}
        xfer['full' if cond == 'Xf' else 'phone'] = M
    # which single cue separates happy from angry (valence at matched high arousal)?
    val = {}
    for n in NAMES:
        d = data[n]
        X = fill(d['Xf'])
        y = d['y']
        h, a = X[y == 'happy'], X[y == 'angry']
        val[n] = {f: round(float((h[:, j].mean() - a[:, j].mean()) / (np.sqrt((h[:, j].var() + a[:, j].var()) / 2) + 1e-9)), 2)
                  for j, f in enumerate(FEAT)}
    out = dict(ablation_loo_accuracy=abl, cross_voice_transfer_accuracy=xfer, happy_vs_angry_cohens_d=val)
    json.dump(out, open(ROOT / 'analysis2.json', 'w'), indent=1)
    for n in NAMES:
        print(n, {s[:14]: (v['full'], v['phone']) for s, v in abl[n].items()})
    for c, M in xfer.items():
        print('transfer', c)
        for a in NAMES:
            print('  train', a, M[a])
    for n in NAMES:
        print('happy-vs-angry d', n, val[n])


if __name__ == '__main__':
    main()
