import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json, os
LIB = _ROOT + '/lib'
OUT = _ROOT + '/out'
sys.path.insert(0, LIB)
import numpy as np
from dsp import SR, read_wav, write_wav24
from analysis import measure, onsets
from master import master
res = json.load(open(OUT + '/master_test.json'))
buf, _ = read_wav(OUT + '/asmr_mix_binaural_dry24.wav')
pk = onsets(buf.mean(1), SR)
I0 = res['mix_dry']['lufs_I']
for target in (-14, -18, -20, -23, -26):
    y, g, info = master(buf, target, f'{OUT}/tmp_m.wav')
    gdb = 20 * np.log10(g[pk] + 1e-12)
    me = measure(y, SR)
    # g only holds the limiter part of the last passes; recompute effective limiting from the signal
    lin = buf * 10 ** ((info['lufs'] - I0) / 20)
    eff = np.abs(y).max(1)[pk] / (np.abs(lin).max(1)[pk] + 1e-12)
    edb = 20 * np.log10(eff + 1e-12)
    res[f'master_{target}'] = {**info, 'crest_db': me['crest_db'], 'onsets': int(len(pk)),
                               'pct_onsets_reduced_gt1dB': round(100 * float(np.mean(edb < -1)), 1),
                               'pct_onsets_reduced_gt3dB': round(100 * float(np.mean(edb < -3)), 1),
                               'max_onset_reduction_db': round(float(-edb.min()), 1)}
    write_wav24(f'{OUT}/asmr_mix_master_{-target}lufs.wav', y)
    print(target, res[f'master_{target}'])
os.remove(f'{OUT}/tmp_m.wav')
json.dump(res, open(OUT + '/master_test.json', 'w'), indent=1, default=str)
