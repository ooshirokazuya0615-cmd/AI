import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, json, subprocess, shutil
LIB = _ROOT + '/lib'
OUT = _ROOT + '/out'
SAD = _ROOT + '/dl/resonance/repo/third_party/SADIE_hrtf_database/WAV/Subject_002/DFC/48K_24bit'
sys.path.insert(0, LIB)
sys.path.insert(0, '/home/user/AI/tools/nonverbal')  # read-only import of the user's pipeline
import numpy as np
from dsp import SR, write_wav24, read_wav, normalize, filt
from binaural import HRIRSet, render_moving, _unit
from analysis import measure, onsets, rise_times
import sounds
res = {}
H = HRIRSet(SAD)
noise = np.random.default_rng(0).standard_normal(SR // 2)
nf = {}
for r in (1.0, 0.5, 0.25, 0.15, 0.1):
    p = _unit(90, 0) * r
    y = render_moving(noise, lambda t: p, H)
    L, R = y[:, 0], y[:, 1]
    nf[r] = {fc: round(10 * np.log10(np.sum(filt(L, ('bp', fc, 1.4)) ** 2) / np.sum(filt(R, ('bp', fc, 1.4)) ** 2)), 1)
             for fc in (250, 500, 1000, 4000)}
print('near-field ILD at 90 deg vs distance:', nf)
res['nearfield_ild_90deg'] = nf

# ---------- a 40 s ASMR-style mix, binaural
mix_len = 40
buf = np.zeros((mix_len * SR + SR, 2))
def put(sig, at, pos, gain=1.0):
    y = render_moving(sig, pos, H)
    i = int(at * SR); m = min(len(y), len(buf) - i)
    buf[i:i + m] += gain * y[:m]
wt, _ = sounds.wood_tap(seconds=10, seed=21)
put(wt, 0.5, lambda t: np.array([0.3 * np.cos(0.6 * t), 0.3 * np.sin(0.6 * t), -0.05]), 1.0)
cr, _ = sounds.crunch(seconds=6, seed=22)
put(cr, 11, lambda t: np.array([0.12, 0.08, -0.02]), 0.7)        # right at the mouth / left ear
wd, _ = sounds.water_drops(seconds=10, seed=23)
put(wd, 18, lambda t: np.array([0.4, -0.25, -0.2]), 1.2)
gt, _ = sounds.glass_tap(seconds=7, seed=24)
put(gt, 28, lambda t: np.array([0.5, 0.3 - 0.1 * t, 0.0]), 0.5)
fc, _ = sounds.fire_crackle(seconds=mix_len, seed=25)
put(fc, 0, lambda t: np.array([1.5, 0.6, -0.3]), 0.4)
buf = buf[:mix_len * SR]
buf = normalize(buf, 0.5)
dry = f'{OUT}/asmr_mix_binaural_dry24.wav'
write_wav24(dry, buf)
res['mix_dry'] = measure(buf, SR, dry)
print('dry mix:', res['mix_dry'])

# ---------- current pipeline: synth.write_wav (tanh) + render.master_audio (loudnorm -14)
import render, synth
cur = f'{OUT}/asmr_mix_current_pipeline.wav'
raw = f'{OUT}/asmr_mix_current_pipeline.raw.wav'
synth.write_wav(raw, buf)  # 16-bit + tanh saturation (what master_audio does first)
sat, _ = read_wav(raw)
res['after_write_wav_tanh16'] = measure(sat, SR)
# replicate master_audio but keep the loudnorm JSON (normalization_type)
probe = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', raw, '-af',
                        'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
m = json.loads(probe[probe.rindex('{'):probe.rindex('}') + 1])
af = (f'loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={m["input_i"]}:measured_TP={m["input_tp"]}'
      f':measured_LRA={m["input_lra"]}:measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:print_format=json')
p2 = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-y', '-i', raw, '-af', af, '-ar', '48000', cur],
                    capture_output=True, text=True).stderr
m2 = json.loads(p2[p2.rindex('{'):p2.rindex('}') + 1])
res['loudnorm_pass1'] = {k: m[k] for k in ('input_i', 'input_tp', 'input_lra')}
res['loudnorm_pass2'] = {k: m2[k] for k in ('output_i', 'output_tp', 'normalization_type')}
x, _ = read_wav(cur)
res['after_master_audio'] = measure(x, SR, cur)
print('loudnorm:', res['loudnorm_pass1'], res['loudnorm_pass2'])
print('after master_audio:', res['after_master_audio'])
# transient preservation: per-onset rise and peak-to-local-RMS before/after
def transient_stats(y):
    mono = y.mean(1)
    pk = onsets(mono, SR)
    rt = rise_times(mono, SR, pk)
    # peak vs 50 ms RMS around it
    ratios = []
    for p in pk:
        seg = mono[max(0, p - 1200):p + 1200]
        ratios.append(20 * np.log10(np.abs(mono[p]) / (np.sqrt(np.mean(seg ** 2)) + 1e-12)))
    return {'n': int(len(pk)), 'rise_ms_med': round(float(np.median(rt)), 3), 'local_crest_db_med': round(float(np.median(ratios)), 1)}
res['transients_dry'] = transient_stats(buf)
res['transients_current_pipeline'] = transient_stats(x)
# ---------- alternative: 24-bit, no saturation, linear gain to -20 LUFS (no limiter needed?)
for target in (-18, -20, -23):
    alt = f'{OUT}/asmr_mix_linear_{-target}lufs.wav'
    I = res['mix_dry']['lufs_I']; g = 10 ** ((target - I) / 20)
    y = buf * g
    tp = 20 * np.log10(np.abs(y).max())
    write_wav24(alt, np.clip(y, -1, 1))
    res[f'linear_{target}'] = {'gain_db': round(target - I, 1), 'sample_peak_dbfs': round(tp, 1), 'needs_limiting_for_-1dBTP': bool(tp > -1.0)}
print(json.dumps({k: v for k, v in res.items() if k.startswith('linear') or k.startswith('trans')}, indent=0))
json.dump(res, open(OUT + '/master_test.json', 'w'), indent=1, default=str)
import os; os.remove(raw)
