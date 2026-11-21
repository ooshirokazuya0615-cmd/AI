import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, time, json
LIB = _ROOT + '/lib'
OUT = _ROOT + '/out'
SAD = _ROOT + '/dl/resonance/repo/third_party/SADIE_hrtf_database/WAV/Subject_002/DFC/48K_24bit'
sys.path.insert(0, LIB)
import numpy as np
from dsp import SR, read_wav, write_wav24, fftconv, normalize, filt
import binaural as bn
from binaural import HRIRSet, render_moving, brown_duda_H, _unit
res = {}
t0 = time.time(); H = HRIRSet(SAD); res['load_s'] = round(time.time() - t0, 2)
print('loaded', len(H.dirs), 'dirs in', res['load_s'], 's')

def itd_ild(y):
    L, R = y[:, 0], y[:, 1]
    n = 1 << int(np.ceil(np.log2(2 * len(L))))
    XL, XR = np.fft.rfft(L, n), np.fft.rfft(R, n)
    f = np.fft.rfftfreq(n, 1 / SR)
    lp = 1 / (1 + (f / 1500) ** 4)  # ITD from < 1.5 kHz (interaural phase region)
    G = XL * np.conj(XR) * lp
    cc = np.fft.irfft(G / (np.abs(G) + 1e-12) * lp, n)
    lag = np.r_[cc[-60:], cc[:61]]
    k = int(np.argmax(lag)) - 60  # >0: L lags R (source on the right)
    ild = {}
    for fc in (500, 1000, 2000, 4000, 8000):
        a, b = filt(L, ('bp', fc, 1.4)), filt(R, ('bp', fc, 1.4))
        ild[fc] = round(10 * np.log10(np.sum(a ** 2) / np.sum(b ** 2)), 1)
    return round(k / SR * 1e3, 3), ild

noise = np.random.default_rng(0).standard_normal(SR)
static = {}
for az, el in [(0, 0), (30, 0), (90, 0), (135, 0), (270, 0), (45, 30), (60, -30)]:
    p = _unit(az, el) * 1.0
    y = render_moving(noise, lambda t: p, H, nearfield=False, air=False)
    ref, _ = read_wav(f'{SAD}/azi_{az}_ele_{el}_DFC.wav')
    yr = np.stack([fftconv(noise, ref[:, 0]), fftconv(noise, ref[:, 1])], -1)
    yb = render_moving(noise, lambda t: p, None, model='sphere', nearfield=False, air=False)
    static[f'{az}/{el}'] = {'renderer': itd_ild(y), 'direct_conv': itd_ild(yr), 'brown_duda': itd_ild(yb)}
    print(az, el, static[f'{az}/{el}'])
res['static'] = static

# spectral distortion: leave-one-out interpolation error and Brown-Duda error vs SADIE (magnitudes)
f = np.fft.rfftfreq(H.nfft, 1 / SR)
band = (f > 200) & (f < 16000)
def sd(Ha, Hb):
    a = 20 * np.log10(np.abs(Ha[..., band]) + 1e-9); b = 20 * np.log10(np.abs(Hb[..., band]) + 1e-9)
    d = a - b
    d = d - d.mean(-1, keepdims=True) * 0  # absolute level kept
    return np.sqrt(np.mean(d ** 2, -1))
rng = np.random.default_rng(1)
sel = rng.choice(len(H.dirs), 300, replace=False)
loo = []
for i in sel:
    v = H.vec[i:i + 1]
    dots = v @ H.vec.T; dots[0, i] = -9
    idx = np.argpartition(-dots, 3, axis=1)[:, :3]
    ang = np.arccos(np.take_along_axis(dots, idx, 1).clip(-1, 1)) + 1e-4
    w = (1 / ang); w /= w.sum()
    Hi = np.einsum('nk,nkef->nef', w, H.H_aligned[idx])
    loo.append(sd(Hi[0], H.H_aligned[i]).mean())
    # neighbour spacing
spacing = []
for i in sel:
    dots = H.vec[i] @ H.vec.T; dots[i] = -9
    spacing.append(np.degrees(np.arccos(dots.max())))
Hbd = brown_duda_H(H.vec[sel], H.nfft)
# normalise overall level of the model to SADIE (fair: compare shape only)
g = np.median(np.abs(H.H_aligned[sel][..., band])) / np.median(np.abs(Hbd[..., band]))
bd = sd(Hbd * g, H.H_aligned[sel]).mean(-1)
res['spectral_distortion_db'] = {'loo_interp_mean': round(float(np.mean(loo)), 2), 'loo_interp_p90': round(float(np.percentile(loo, 90)), 2),
                                 'brown_duda_mean': round(float(np.mean(bd)), 2), 'brown_duda_p90': round(float(np.percentile(bd, 90)), 2),
                                 'nn_spacing_deg_median': round(float(np.median(spacing)), 1)}
print('SD', res['spectral_distortion_db'])

# ---------- moving sources
import sounds
taps, _ = sounds.wood_tap(seconds=8.0, seed=11)
orbit = lambda t: np.array([0.35 * np.cos(2 * np.pi * t / 8.0), 0.35 * np.sin(2 * np.pi * t / 8.0), 0.0])
t1 = time.time(); yo = render_moving(taps, orbit, H); dt = time.time() - t1
res['cpu_hrir_s_per_s'] = round(dt / 8.0, 4)
write_wav24(f'{OUT}/binaural_wood_orbit.wav', normalize(yo, 0.5))
t1 = time.time(); yb = render_moving(taps, orbit, None, model='sphere'); dts = time.time() - t1
res['cpu_sphere_s_per_s'] = round(dts / 8.0, 4)
write_wav24(f'{OUT}/binaural_wood_orbit_spherehead.wav', normalize(yb, 0.5))
# ITD per tap along the orbit vs expected
from analysis import onsets
pk = onsets(taps, SR)
traj = []
for p in pk:
    seg = yo[p - 200:p + 2400]
    itd, ild = itd_ild(seg)
    tt = p / SR
    az = (360 * tt / 8.0) % 360
    exp_itd = -HEAD_ITD if False else None
    traj.append((round(tt, 2), round(az), itd, ild[4000]))
res['orbit_taps_itd_ms_ild4k'] = traj
print('orbit (t, az, ITD ms, ILD4k dB):', traj)

# fly-by with doppler: crackle passing 0.3 m in front, left->right at 1.5 m/s
fire, _ = sounds.fire_crackle(seconds=4.0, seed=3)
fly = lambda t: np.array([0.3, 3.0 - 1.5 * t, 0.0])
yf = render_moving(fire, fly, H)
write_wav24(f'{OUT}/binaural_fire_flyby.wav', normalize(yf, 0.5))

# zipper / modulation-artifact test: 2 kHz sine orbiting at 1 rev/s, r = 0.5 m, no doppler
s = np.sin(2 * np.pi * 2000 * np.arange(4 * SR) / SR)
fast = lambda t: np.array([0.5 * np.cos(2 * np.pi * t), 0.5 * np.sin(2 * np.pi * t), 0.0])
yz = render_moving(s, fast, H, doppler=False, nearfield=False, air=False)
def artifact_db(y):
    seg = y[SR:3 * SR, 0]
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    fr = np.fft.rfftfreq(len(seg), 1 / SR)
    main = X[(fr > 1900) & (fr < 2100)].sum()  # carrier + slow AM sidebands from the true motion
    far = X[(fr > 2300) | (fr < 1700)].sum()   # anything else = switching/zipper products
    return round(10 * np.log10(far / main), 1)
res['zipper_db_crossfade'] = artifact_db(yz)
# same without crossfade (nearest HRIR, hard switch) for contrast
class NN(HRIRSet):
    pass
Hn = H
orig = H.lookup
H.lookup = lambda u, k=3: orig(u, k=1)
yn = render_moving(s, fast, H, doppler=False, nearfield=False, air=False, block=128)
res['zipper_db_nearest_neighbour_k1'] = artifact_db(yn)
H.lookup = orig
print('zipper', res['zipper_db_crossfade'], res['zipper_db_nearest_neighbour_k1'])

# CPU scaling: N sources of 10 s each
for N in (1, 8):
    xs = [np.random.default_rng(k).standard_normal(10 * SR) * 0.1 for k in range(N)]
    t1 = time.time()
    for k, xk in enumerate(xs):
        ph = k * 0.7
        render_moving(xk, lambda t, ph=ph: np.array([0.5 * np.cos(t + ph), 0.5 * np.sin(t + ph), 0.1]), H)
    res[f'cpu_{N}src_10s_s'] = round(time.time() - t1, 2)
print(json.dumps({k: v for k, v in res.items() if k.startswith('cpu') or k.startswith('zip') or k == 'load_s'}))
json.dump(res, open(OUT + '/binaural_metrics.json', 'w'), indent=1, default=str)
