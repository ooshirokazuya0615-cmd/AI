import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json, time
LIB = _ROOT + '/lib'
OUT = _ROOT + '/out'
sys.path.insert(0, LIB)
import numpy as np
import sounds
from dsp import write_wav24, normalize, SR
from analysis import measure, partials, band_t60
names = sys.argv[1:] or ['wood_tap', 'glass_tap', 'crunch', 'fire_crackle', 'slime_squish',
                         'water_drops', 'bubbling', 'glass_shatter', 'sand_cut']
allres = {}
try:
    allres = json.load(open(OUT + '/synth_metrics.json'))
except Exception:
    pass
for nm in names:
    t0 = time.time()
    y, info = getattr(sounds, nm)()
    dt = time.time() - t0
    y = normalize(y, 0.5)  # -6 dBFS peak, no saturation
    path = f'{OUT}/{nm}.wav'
    write_wav24(path, y)
    m = measure(y, SR, path)
    m['render_s'] = round(dt, 2); m['dur_s'] = round(len(y) / SR, 2)
    m['x_realtime'] = round(m['dur_s'] / dt, 1)
    m['info'] = info
    if nm in ('wood_tap', 'glass_tap'):
        m['partials'] = partials(y, SR)
        m['band_t60_ms'] = band_t60(y[:int(1.2 * SR)] if nm == 'wood_tap' else y[int(0.29*SR):int(1.55*SR)], SR)
    allres[nm] = m
    print(nm, json.dumps(m, default=str))
json.dump(allres, open(OUT + '/synth_metrics.json', 'w'), indent=1, default=str)
