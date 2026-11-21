import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json, csv
sys.path.insert(0, _ROOT + '/lib')
import numpy as np
from dsp import read_wav
from analysis import measure, band_t60
root = sys.argv[1]
rows = list(csv.DictReader(open(root + '/meta/esc50.csv')))
want = {'door_wood_knock', 'crackling_fire', 'water_drops', 'pouring_water', 'glass_breaking'}
res = {}
for r in rows:
    if r['category'] not in want:
        continue
    x, sr = read_wav(root + '/audio/' + r['filename'])
    m = measure(x[:, 0], sr)
    res.setdefault(r['category'], []).append(m)
json.dump(res, open(sys.argv[2], 'w'))
def q(v):
    v = [a for a in v if a is not None]
    return [round(float(np.percentile(v, p)), 2) for p in (25, 50, 75)] if v else None
for c, ms in res.items():
    print(c, len(ms))
    for k in ['ev_rate', 'rise_ms_med', 'rise_ms_p10', 'crest_db', 'centroid_hz', 'rolloff95_hz', 'flatness', 't60_ms', 'edt_ms']:
        print('   ', k, q([m[k] for m in ms]))
    b = np.array([m['bands_pct'] for m in ms])
    print('    bands_med', np.median(b, axis=0).round(1).tolist())
