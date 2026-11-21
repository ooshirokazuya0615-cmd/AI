"""
Binaural rendering of moving point sources (numpy only).

HRIR source: SADIE (University of York) Subject 002 = Neumann KU100 dummy head,
1550 directions, 48 kHz, 256 taps, diffuse-field compensated — as redistributed under
Apache-2.0 in google/resonance-audio third_party/SADIE_hrtf_database.

Coordinates: listener at origin, +x front, +y left, +z up (SADIE azimuth 90 = left).

Pipeline per source (block size B, default 128 samples = 2.7 ms):
  1. per-ear delay line (cubic Lagrange, per-sample): distance/c + per-ear onset delay
     -> ITD, propagation delay and Doppler all come out of one variable delay.
  2. ITD-free ("time-aligned") HRTF, interpolated between the 3 nearest measured
     directions (inverse angular distance weights) at every block.
  3. block FFT convolution with INPUT-side crossfade between the previous and current
     block's filter (no zipper noise), overlap-add.
  4. near-field: per-ear 1/r_ear gain from a rigid-sphere path model, applied only below
     ~2 kHz (the far-field HRIR already has the high-frequency head shadow).
  5. optional air absorption (ISO 9613-1-like, ~0.1 dB/m at 10 kHz).
Alternative: parametric spherical-head model (Brown & Duda 1998) when no HRIR set is usable.
"""
import glob
import os
import re

import numpy as np

from dsp import SR, read_wav

C = 343.0
HEAD_A = 0.0875
SADIE_DIR = None


def _unit(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)


def _onset(h, thr=0.15, up=8):
    """sub-sample onset (first crossing of thr*max) via FFT upsampling"""
    n = len(h)
    H = np.fft.rfft(h, n)
    hu = np.fft.irfft(H, n * up) * up
    a = np.abs(hu)
    i = int(np.argmax(a > thr * a.max()))
    return i / up


class HRIRSet:
    def __init__(self, folder, pre=12, n_taps=256):
        files = sorted(glob.glob(os.path.join(folder, 'azi_*_ele_*_DFC.wav')))
        dirs, irs = [], []
        for f in files:
            m = re.search(r'azi_([\d.]+)_ele_(-?[\d.]+)_DFC', f)
            az, el = float(m.group(1)), float(m.group(2))
            x, sr = read_wav(f)
            assert sr == SR and x.shape[0] == n_taps
            dirs.append((az, el)); irs.append(x.T)  # (2, taps)
        self.dirs = np.array(dirs)
        self.vec = _unit(self.dirs[:, 0], self.dirs[:, 1])
        irs = np.array(irs)  # (D, 2, taps)
        self.n_taps = n_taps
        # time-align: remove each ear's onset delay (fractional) so interpolation is ITD-free
        delays = np.array([[_onset(irs[d, e]) for e in range(2)] for d in range(len(irs))])
        self.delays = delays - delays.min() + 0.0  # relative per-ear delays (samples)
        self.nfft = 2 * n_taps
        f = np.fft.rfftfreq(self.nfft)  # cycles/sample
        H = np.fft.rfft(irs, self.nfft, axis=-1)
        shift = delays - pre  # move onset to `pre`
        H = H * np.exp(2j * np.pi * f[None, None, :] * shift[:, :, None])
        self.H_aligned = H  # (D, 2, nfft/2+1)
        self.pre = pre

    def lookup(self, dirs_unit, k=3):
        """inverse-angle-weighted interpolation of time-aligned HRTFs + per-ear delays"""
        dots = dirs_unit @ self.vec.T  # (N, D)
        idx = np.argpartition(-dots, k, axis=1)[:, :k]
        d = np.take_along_axis(dots, idx, 1).clip(-1, 1)
        ang = np.arccos(d) + 1e-4
        w = 1 / ang
        w /= w.sum(1, keepdims=True)
        H = np.einsum('nk,nkef->nef', w, self.H_aligned[idx])
        dl = np.einsum('nk,nke->ne', w, self.delays[idx])
        return H, dl


# ------------------------------------------------------------------ geometry

def ear_paths(src, a=HEAD_A):
    """Path length from a point source to each ear of a rigid sphere (ears at +-y).
    Visible ear: straight line. Shadowed ear: tangent + arc (Woodworth/Schwarz)."""
    r = np.linalg.norm(src, axis=-1).clip(a * 1.05, None)
    u = src / r[..., None]
    out = []
    for side in (+1, -1):  # left ear (+y), right ear (-y)
        cos_t = (u[..., 1] * side).clip(-1, 1)
        theta = np.arccos(cos_t)
        th_t = np.arccos(a / r)
        straight = np.sqrt(r ** 2 + a ** 2 - 2 * a * r * cos_t)
        wrap = np.sqrt(r ** 2 - a ** 2) + a * (theta - th_t)
        out.append(np.where(theta < th_t, straight, wrap))
    return np.stack(out, -1), r  # (..., 2), (...)


def cubic_delay(x, d):
    """y[n] = x(n - d[n]) with 4-point Lagrange interpolation; d in samples (float, >= 1)."""
    n = np.arange(len(d))
    pos = n - d
    i = np.floor(pos).astype(int)
    f = pos - i
    xp = np.concatenate([np.zeros(4), x, np.zeros(4)])
    i = i + 4
    valid = (i - 1 >= 0) & (i + 2 < len(xp))
    i = np.clip(i, 1, len(xp) - 3)
    xm1, x0, x1, x2 = xp[i - 1], xp[i], xp[i + 1], xp[i + 2]
    c_m1 = -f * (f - 1) * (f - 2) / 6
    c0 = (f + 1) * (f - 1) * (f - 2) / 2
    c1 = -(f + 1) * f * (f - 2) / 2
    c2 = (f + 1) * f * (f - 1) / 6
    return np.where(valid, c_m1 * xm1 + c0 * x0 + c1 * x1 + c2 * x2, 0.0)


# ------------------------------------------------------------------ renderer

def render_moving(x, positions, hrirs=None, block=128, nearfield=True, air=True, model='hrir',
                  doppler=True):
    """
    x: mono signal (n,)
    positions: callable t->(3,) or array (n_blocks+1, 3) of source positions (metres) at block edges
    Returns stereo (n + tail, 2).
    """
    n = len(x)
    nb = int(np.ceil(n / block))
    tb = (np.arange(nb + 1) * block) / SR
    P = np.array([positions(t) for t in tb]) if callable(positions) else np.asarray(positions)
    # per-sample positions (linear between block edges) for the delay lines
    tt = np.arange(nb * block) / block
    Ps = np.stack([np.interp(tt, np.arange(nb + 1), P[:, k]) for k in range(3)], -1)
    paths, r = ear_paths(Ps)
    # block-centre directions for filters
    Pc = 0.5 * (P[:-1] + P[1:])
    rc = np.linalg.norm(Pc, axis=-1).clip(1e-3, None)
    uc = Pc / rc[:, None]
    if model == 'hrir':
        H, dl = hrirs.lookup(uc)
        nfft = hrirs.nfft
        pre = hrirs.pre
        # per-ear delay: propagation of the *centre* path + measured onset offset (far-field ITD)
        # then the near-field part of the ITD from the sphere model replaces nothing (kept far-field)
        dl_s = np.stack([np.interp(tt, np.arange(nb) + 0.5, dl[:, e]) for e in range(2)], -1)
        base = (r / C * SR) if doppler else np.full_like(r, rc.mean() / C * SR)
        delays = base[:, None] + dl_s
    else:  # spherical head: ITD from the path model
        nfft = 512
        pre = 0
        H = brown_duda_H(uc, nfft)
        base = paths / C * SR if doppler else (paths - r[:, None] + rc.mean()) / C * SR
        delays = base
    delays = delays - delays.min() + 2.0  # keep causal (relative timing is what matters)
    f = np.fft.rfftfreq(nfft, 1 / SR)
    # near-field ILD (low-frequency only) + 1/r distance law
    pc, rcc = ear_paths(Pc)
    g_dist = 1 / rc.clip(0.05, None)
    if nearfield:
        ratio = (rc[:, None] / pc.clip(0.03, None))  # (nb, 2), >1 for the near ear; 3 cm ~ pinna size
        lp = 1 / (1 + (f / 2000.0) ** 2)  # apply only below ~2 kHz
        G = 1 + (ratio[:, :, None] - 1) * lp[None, None, :]
    else:
        G = np.ones((nb, 2, len(f)))
    if air:
        alpha_db_m = 1.0e-5 * f ** 1.25  # ~0.1 dB/m at 10 kHz (20 C, 50 % RH, rough)
        A = 10 ** (-alpha_db_m[None, :] * rc[:, None] / 20)
        G = G * A[:, None, :]
    Hb = H * G * g_dist[:, None, None]
    out = np.zeros((nb * block + nfft, 2))
    w = (np.arange(block) + 0.5) / block
    for e in range(2):
        y = cubic_delay(np.r_[x, np.zeros(nb * block - n)], delays[:, e])
        Y = y.reshape(nb, block)
        X_new = np.fft.rfft(Y * w, nfft, axis=1)
        X_old = np.fft.rfft(Y * (1 - w), nfft, axis=1)
        Hprev = np.vstack([Hb[:1, e], Hb[:-1, e]])
        Z = np.fft.irfft(X_new * Hb[:, e] + X_old * Hprev, nfft, axis=1)  # (nb, nfft)
        k = nfft // block
        for j in range(k):
            seg = Z[:, j * block:(j + 1) * block].reshape(-1)
            out[j * block:j * block + len(seg), e] += seg
    return out[pre:pre + n + 256]


# ------------------------------------------------------------------ parametric head

def brown_duda_H(u, nfft, a=HEAD_A, sr=SR):
    """Brown & Duda (1998) structural model: one-pole/one-zero head shadow per ear +
    5 pinna echoes (elevation/azimuth dependent delays) — returns (N, 2, nfft/2+1)."""
    f = np.fft.rfftfreq(nfft, 1 / sr)
    w = 2 * np.pi * f
    w0 = C / a
    az = np.degrees(np.arctan2(u[:, 1], u[:, 0]))
    el = np.degrees(np.arcsin(u[:, 2].clip(-1, 1)))
    out = np.zeros((len(u), 2, len(f)), complex)
    rho = [0.5, -1.0, 0.5, -0.25, 0.25]
    A = [1, 5, 5, 5, 5]
    B = [2, 4, 7, 11, 13]
    D = [1.0, 0.5, 0.5, 0.5, 0.5]
    for e, side in enumerate((+1, -1)):
        cos_t = (u[:, 1] * side).clip(-1, 1)
        theta = np.degrees(np.arccos(cos_t))  # 0 = source on this ear's axis
        amin, tmin = 0.1, 150.0
        alpha = (1 + amin / 2) + (1 - amin / 2) * np.cos(theta / tmin * np.pi)
        Hs = (1 + 1j * alpha[:, None] * w[None] / (2 * w0)) / (1 + 1j * w[None] / (2 * w0))
        # pinna: azimuth measured from this ear's frontal plane
        th_p = np.radians(az * side)
        Hp = np.ones((len(u), len(f)), complex)
        for k in range(5):
            tau = A[k] * np.cos(th_p / 2) * np.sin(np.radians(D[k] * (90 - el))) + B[k]  # samples @44.1k
            tau = tau * sr / 44100
            Hp = Hp + rho[k] * np.exp(-1j * w[None] * tau[:, None] / sr)
        out[:, e] = Hs * Hp / 2.0
    return out


def load_sadie(folder):
    return HRIRSet(folder)
