import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json, subprocess, os
LIB = _ROOT + '/lib'
OUT = _ROOT + '/out'
SAD = _ROOT + '/dl/resonance/repo/third_party/SADIE_hrtf_database/WAV/Subject_002/DFC/48K_24bit'
sys.path.insert(0, LIB); sys.path.insert(0, '/home/user/AI/tools/nonverbal')
import numpy as np
from dsp import SR, write_wav24, read_wav, normalize, filt
from binaural import HRIRSet, render_moving, _unit
from analysis import measure, onsets
from master import master, lufs_of
import sounds
res = {}
H = HRIRSet(SAD)
nf = {}
for r in (1.0, 0.5, 0.25, 0.15, 0.1):
    p = _unit(90, 0) * r
    y = render_moving(np.random.default_rng(0).standard_normal(SR // 2), lambda t: p, H)
    nf[r] = {fc: round(10 * np.log10(np.sum(filt(y[:, 0], ('bp', fc, 1.4)) ** 2) / np.sum(filt(y[:, 1], ('bp', fc, 1.4)) ** 2)), 1) for fc in (250, 500, 1000, 4000)}
res['nearfield_ild_90deg'] = nf
print('near-field ILD:', nf)
mix_len = 40
buf = np.zeros((mix_len * SR + SR, 2))
def put(sig, at, pos, gain_db):
    sig = sig / np.abs(sig).max()
    y = render_moving(sig, pos, H)
    y = y / np.sqrt(np.mean(y[np.abs(y).max(1) > 1e-4] ** 2))  # equal active RMS before gain
    i = int(at * SR); m = min(len(y), len(buf) - i)
    buf[i:i + m] += 10 ** (gain_db / 20) * y[:m]
wt, _ = sounds.wood_tap(seconds=10, seed=21)
put(wt, 0.5, lambda t: np.array([0.3 * np.cos(0.6 * t), 0.3 * np.sin(0.6 * t), -0.05]), 0)
cr, _ = sounds.crunch(seconds=6, seed=22)
put(cr, 11, lambda t: np.array([0.15, 0.12, -0.02]), 0)
wd, _ = sounds.water_drops(seconds=10, seed=23)
put(wd, 18, lambda t: np.array([0.4, -0.25, -0.2]), 0)
gt, _ = sounds.glass_tap(seconds=7, seed=24)
put(gt, 28, lambda t: np.array([0.5, 0.3 - 0.1 * t, 0.0]), -4)
fc, _ = sounds.fire_crackle(seconds=mix_len, seed=25)
put(fc, 0, lambda t: np.array([1.5, 0.6, -0.3]), -14)
buf = normalize(buf[:mix_len * SR], 0.5)
dry = f'{OUT}/asmr_mix_binaural_dry24.wav'
write_wav24(dry, buf)
md = measure(buf, SR, dry); res['mix_dry'] = md
print('dry mix: LUFS', md['lufs_I'], 'TP', md['true_peak_dbfs'], 'PLR', md['plr_db'], 'crest', md['crest_db'], 'onsets', md['n_onsets'])
# current pipeline
import render, synth
raw = f'{OUT}/tmp_raw.wav'; cur = f'{OUT}/asmr_mix_current_pipeline.wav'
render.master_audio(buf, cur)
x, _ = read_wav(cur)
mc = measure(x, SR, cur)
probe = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', dry, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
mj = json.loads(probe[probe.rindex('{'):probe.rindex('}') + 1])
res['current_pipeline'] = {'lufs': mc['lufs_I'], 'tp': mc['true_peak_dbfs'], 'crest_db': mc['crest_db'], 'input_lra': mj['input_lra'],
                           'loudnorm_first_pass_type': mj['normalization_type']}
print('current master_audio ->', res['current_pipeline'])
pk = onsets(buf.mean(1), SR)
for target in (-14, -18, -20, -23):
    y, g, info = master(buf, target, f'{OUT}/tmp_m.wav')
    gdb = 20 * np.log10(g[pk] + 1e-12)
    me = measure(y, SR)
    res[f'master_{target}'] = {**info, 'crest_db': me['crest_db'], 'onsets': int(len(pk)),
                               'pct_onsets_limited_gt1dB': round(100 * float(np.mean(gdb < -1)), 1),
                               'pct_onsets_limited_gt3dB': round(100 * float(np.mean(gdb < -3)), 1),
                               'max_gain_reduction_db': round(float(-20 * np.log10(g.min())), 1),
                               'pct_time_limited_gt1dB': round(100 * float(np.mean(g < 10 ** (-1 / 20))), 2)}
    write_wav24(f'{OUT}/asmr_mix_master_{-target}lufs.wav', y)
    print(target, res[f'master_{target}'])
os.remove(f'{OUT}/tmp_m.wav')
json.dump(res, open(OUT + '/master_test.json', 'w'), indent=1, default=str)
