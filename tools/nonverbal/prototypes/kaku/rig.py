"""Tiny stickman rig shared by the prototypes: key poses in the sagittal plane (facing +z)."""
import math

import numpy as np

L_THIGH, L_SHIN, L_TORSO, L_UP, L_FORE = 0.27, 0.27, 0.33, 0.20, 0.20
SEGS = [('hip', 'neck'), ('hip_l', 'knee_l'), ('knee_l', 'foot_l'), ('hip_r', 'knee_r'), ('knee_r', 'foot_r'),
        ('sh_l', 'elbow_l'), ('elbow_l', 'hand_l'), ('sh_r', 'elbow_r'), ('elbow_r', 'hand_r'), ('hip_l', 'hip_r'),
        ('sh_l', 'sh_r')]
# pose = (hip_z, hip_y, torso, Lhip, Lknee, Rhip, Rknee, Lsh, Lel, Rsh, Rel)
# legs/arms from straight down, + = forward (+z); knee bends the shin back, elbow bends the forearm forward;
# an arm angle above ~1.8 rad (raised) also spreads the arm sideways a little.


def interp(keys, t):
    if t <= keys[0][0]:
        return np.array(keys[0][1:], float)
    if t >= keys[-1][0]:
        return np.array(keys[-1][1:], float)
    i = max(j for j in range(len(keys) - 1) if keys[j][0] <= t)
    a, b = np.array(keys[i][1:], float), np.array(keys[i + 1][1:], float)
    u = (t - keys[i][0]) / (keys[i + 1][0] - keys[i][0])
    u = u * u * (3 - 2 * u)
    return a + (b - a) * u


def joints(pose, x0=0.0):
    hz, hy, tor, lh, lk, rh, rk, ls, le, rs, re = pose
    up = lambda a: np.array([0.0, math.cos(a), math.sin(a)])
    down = lambda a: np.array([0.0, -math.cos(a), math.sin(a)])
    hip = np.array([x0, hy, hz])
    j = {}
    for side, xo, a, k in (('l', -0.07, lh, lk), ('r', 0.07, rh, rk)):
        h = hip + np.array([xo, 0, 0])
        kn = h + L_THIGH * down(a)
        ft = kn + L_SHIN * down(a - k)
        j['hip_' + side], j['knee_' + side], j['foot_' + side] = h, kn, ft
    low = min(j['foot_l'][1], j['foot_r'][1]) - 0.035
    if low < 0:
        for key in list(j):
            j[key] = j[key] - np.array([0, low, 0])
        hip = hip - np.array([0, low, 0])
    neck = hip + L_TORSO * up(tor)
    j['hip'], j['neck'] = hip, neck
    j['head'] = neck + 0.115 * up(tor * 0.7)
    for side, xo, s, e in (('l', -0.12, ls, le), ('r', 0.12, rs, re)):
        sh = neck - 0.03 * up(tor) + np.array([xo, 0, 0])
        spread = min(max((s - 1.8) / 1.0, 0.0), 1.0) * 0.45
        out = np.array([math.copysign(1.0, xo), 0.0, 0.0])
        du = down(s) * math.cos(spread) + out * math.sin(spread)
        el = sh + L_UP * du
        df = down(s + e) * math.cos(spread) + out * math.sin(spread)
        ha = el + L_FORE * df
        j['sh_' + side], j['elbow_' + side], j['hand_' + side] = sh, el, ha
    return j


def capsules(j):
    a = np.array([j[s[0]] for s in SEGS])
    b = np.array([j[s[1]] for s in SEGS])
    return a, b, j['head']
