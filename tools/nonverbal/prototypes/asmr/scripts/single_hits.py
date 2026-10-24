import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json
LIB = _ROOT + '/lib'
OUT = _ROOT + '/out'
sys.path.insert(0, LIB)
import numpy as np
import sounds
from dsp import SR, write_wav24, normalize
from analysis import band_t60, partials, measure, rise_times, onsets
res = {}
for nm, kw, dur in [('wood_tap', dict(seconds=1.0, pattern=[0.05]), 1.0), ('glass_tap', dict(seconds=6.0, taps=[0.05]), 6.0)]:
    y, info = getattr(sounds, nm)(**kw)
    y = normalize(y, 0.5)
    write_wav24(f'{OUT}/{nm}_single.wav', y)
    m = measure(y, SR)
    res[nm] = {'band_t60_ms': band_t60(y, SR), 'partials': partials(y, SR, n=10), 'rise_ms': m['rise_ms_med'],
               'bands_pct': m['bands_pct'], 'centroid_hz': m['centroid_hz'], 'info': info}
    # attack-only spectrum (first 5 ms) shows the click content
    st = int(np.argmax(np.abs(y) > 0.05 * np.abs(y).max()))
    seg = y[st:st + int(0.005 * SR)]
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 8192)) ** 2
    f = np.fft.rfftfreq(8192, 1 / SR)
    res[nm]['attack5ms_pct_above_5k'] = round(100 * X[f > 5000].sum() / X.sum(), 1)
    print(nm, json.dumps(res[nm], default=str))
json.dump(res, open(OUT + '/single_hits.json', 'w'), indent=1, default=str)
