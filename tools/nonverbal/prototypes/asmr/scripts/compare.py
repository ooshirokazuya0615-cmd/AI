import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
"""Render all prototypes dry + 'recorded', measure, compare with ESC-50 class quartiles."""
import sys, json, time
LIB = _ROOT + '/lib'
OUT = _ROOT + '/out'
sys.path.insert(0, LIB)
import numpy as np
import sounds
from dsp import write_wav24, normalize, SR
from analysis import measure
ref = json.load(open(OUT + '/esc50_ref.json'))
pairs = {'wood_tap': 'door_wood_knock', 'fire_crackle': 'crackling_fire', 'water_drops': 'water_drops',
         'bubbling': 'pouring_water', 'glass_shatter': 'glass_breaking', 'glass_tap': None, 'crunch': None,
         'slime_squish': None, 'sand_cut': None}
names = sys.argv[1:] or list(pairs)
keys = ['rise_ms_p10', 'crest_db', 'centroid_hz', 'rolloff95_hz', 'flatness']
def q(v):
    v = [a for a in v if a is not None]
    return [round(float(np.percentile(v, p)), 2) for p in (25, 50, 75)]
res = {}
for nm in names:
    t0 = time.time(); y, info = getattr(sounds, nm)(); dt = time.time() - t0
    y = normalize(y, 0.5)
    write_wav24(f'{OUT}/{nm}.wav', y)
    yr = sounds.record(y, seed=1)
    write_wav24(f'{OUT}/{nm}_recorded.wav', yr)
    md = measure(y, SR, f'{OUT}/{nm}.wav'); mr = measure(yr, SR)
    res[nm] = {'dry': md, 'recorded': mr, 'info': info, 'render_x_realtime': round(len(y) / SR / dt, 1)}
    print(f'== {nm}  ({len(y)/SR:.1f}s, {len(y)/SR/dt:.0f}x realtime) info={info}')
    print(f'   PLR(dry) {md.get("plr_db")} dB, LUFS {md.get("lufs_I")} at -6 dBFS peak')
    r = pairs.get(nm)
    for k in keys:
        line = f'   {k:13s} dry {md[k]!s:>8}  rec {mr[k]!s:>8}'
        if r:
            line += f'   ESC50[{r}] q25/50/75 {q([m[k] for m in ref[r]])}'
        print(line)
    line = f'   bands%       dry {md["bands_pct"]}  rec {mr["bands_pct"]}'
    if r:
        line += f'  ESC50 med {np.median([m["bands_pct"] for m in ref[r]], axis=0).round(1).tolist()}'
    print(line)
json.dump(res, open(OUT + '/compare.json', 'w'), indent=1, default=str)
