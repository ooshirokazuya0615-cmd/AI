"""
Bowling strike -> domino wave, score-first.

The score is the master clock. The strike lands on bar 0 beat 1; the pins land on
16th-note steps; the ball taps the first domino on bar 1; the domino wave runs at a
constant speed (3 dominoes per 16th note, a physically plausible ~2.9 m/s for 0.30 m
dominoes spaced 0.12 m), so a "note domino" placed at index 3*s sounds exactly on
16th step s. The last small domino hands over to a big slab that falls for one
beat and lands on bar 4 beat 3.
"""
import math

import numpy as np

BPM = 120.0
BEAT = 60.0 / BPM
S16 = BEAT / 4
OFFSET = 0.5                      # bar 0 downbeat = strike (inside the first 0.5 s)
DT = S16 / 3                      # time between two domino impacts
DURATION = 11.3
T_RELEASE = 0.0                   # frame 0 = the ball leaving the hand

T_STRIKE = OFFSET
T_DOM0 = OFFSET + 2 * BEAT        # bar 0 beat 3
T_BIG = T_DOM0 + 12 * BEAT        # last small domino hits the slab
T_BOOM = T_BIG + 2 * BEAT         # bar 4 beat 3: slab lands

G = 9.81

# lane / pins / ball
BALL_R = 0.109
LANE_HALF = 0.533
DECK_END = 4.0
HEAD_PIN_Z = 3.0 + BALL_R + 0.0605
ROW_DZ = 0.264
PIN_DX = 0.305
PIN_COM = 0.15                    # COM height of a standing pin
PIN_LYING = 0.0605                # COM height of a pin lying on its side

# dominoes
DOM_H, DOM_W, DOM_T, DOM_D = 0.30, 0.15, 0.04, 0.12
DOM_Z0 = 4.6
N_DOM = 144                       # 3 bars x 16 steps x 3
BIG_H, BIG_W, BIG_T = 0.90, 0.45, 0.12
BIG_Z = DOM_Z0 + (N_DOM - 1) * DOM_D + 0.10 + BIG_T / 2   # slab centre (upright)


def tm(bar, step=0.0):
    return OFFSET + (bar * 16 + step) * S16


# ---------------- music ----------------
# melody played by the note dominoes: (bar, 16th step, midi). Bars 1-3 over F | C | G.
MELODY = [
    (1, 0, 69), (1, 2, 72), (1, 4, 77), (1, 6, 76), (1, 8, 72), (1, 10, 69), (1, 12, 72), (1, 14, 76),
    (2, 0, 79), (2, 2, 76), (2, 4, 72), (2, 6, 74), (2, 8, 76), (2, 10, 79), (2, 12, 81), (2, 14, 79),
    (3, 0, 71), (3, 2, 74), (3, 4, 79), (3, 6, 74),
    (3, 8, 74), (3, 9, 76), (3, 10, 79), (3, 11, 81), (3, 12, 83), (3, 13, 84), (3, 14, 86), (3, 15, 88),
]
CHORDS = [(57, 60, 64), (53, 57, 60), (55, 60, 64), (55, 59, 62)]   # Am F C G
ROOTS = [33, 29, 36, 31]
FINAL = (45, 57, 60, 64, 71, 76)                                       # Am add9, wide


def note_dominoes():
    out = []
    for bar, st, m in MELODY:
        s = (bar - 1) * 16 + st
        k = 3 * s
        out.append(dict(k=k, midi=m, t=T_DOM0 + k * DT))
    return out


def note_colour(m):
    # low notes cool, high notes warm
    u = np.clip((m - 69) / (88 - 69), 0, 1)
    stops = np.array([[0.20, 0.55, 1.00], [0.45, 0.35, 1.00], [0.95, 0.35, 0.85], [1.00, 0.62, 0.25]])
    x = u * (len(stops) - 1)
    i = min(int(x), len(stops) - 2)
    f = x - i
    return tuple(stops[i] * (1 - f) + stops[i + 1] * f)


# ---------------- ball ----------------
V_IN = None   # set after the stickman is defined
V0_OUT = 2.692
A_OUT = 2.442
Z_TAP = DOM_Z0 - DOM_T / 2 - BALL_R      # ball centre when it touches domino 0


def ball(t):
    """centre (x, y, z) and travelled distance (for the rolling rotation)."""
    if t < T_RELEASE:
        j = stick_joints(t)
        h, e = j['hand_r'], j['elbow_r']
        d = h - e
        d /= np.linalg.norm(d)
        c = h + d * 0.05 + np.array([0.04, 0.0, 0.0])
        c[1] = max(c[1], BALL_R)
        return c, 0.0
    if t < T_STRIKE:
        z = 3.0 - V_IN * (T_STRIKE - t)
        tau = t - T_RELEASE
        y = BALL_R + max(0.0, REL_H - BALL_R) * max(0.0, 1 - tau / 0.09) ** 2
        x = REL_X * max(0.0, 1 - tau / 0.6)
        return np.array([x, y, z]), z + 1.2
    elif t < T_DOM0:
        tau = t - T_STRIKE
        z = 3.0 + V0_OUT * tau - 0.5 * A_OUT * tau * tau
    else:
        tau = t - T_DOM0
        z = Z_TAP - 0.02 * (1 - math.exp(-tau / 0.12))      # tiny recoil after the tap
    return np.array([0.0, BALL_R, z]), z + 1.2


def ball_rot(dist):
    a = dist / BALL_R
    c, s = math.cos(a), math.sin(a)
    # rolling toward +z spins about +x
    return np.array([[1, 0, 0], [0, c, s], [0, -s, c]])


# ---------------- pins ----------------
LANDINGS = [2, 2, 3, 3, 4, 4, 5, 6, 6, 7]          # 16th steps after the strike


def _axis_angle(axis, a):
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s, C = math.cos(a), math.sin(a), 1 - math.cos(a)
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def _rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


class Pins:
    def __init__(self, seed=3):
        rng = np.random.default_rng(seed)
        spots = []
        for r in range(4):
            for i in range(r + 1):
                spots.append((r, (i - r / 2) * PIN_DX, HEAD_PIN_Z + r * ROW_DZ))
        order = rng.permutation(10)
        self.p = []
        for n, (r, x, z) in enumerate(spots):
            t_launch = T_STRIKE + 0.012 * r + rng.uniform(0, 0.012)
            t_land = T_STRIKE + LANDINGS[order[n]] * S16 + rng.uniform(-0.004, 0.004)
            tau = t_land - t_launch
            vy = (G * tau * tau / 2 - (PIN_COM - PIN_LYING)) / tau
            # outward from the impact point, mostly sideways so nothing lands on the domino line
            d = np.array([x, z - 3.0]) + rng.normal(0, 0.05, 2)
            if abs(d[0]) < 0.05:
                d[0] = rng.choice([-1, 1]) * 0.15
            d = d / np.linalg.norm(d)
            side = np.sign(d[0])
            d = np.array([side * max(abs(d[0]), 0.75), d[1] * 0.6])
            d /= np.linalg.norm(d)
            speed = rng.uniform(1.1, 2.0)
            v = d * speed
            land = np.array([x, z]) + v * tau
            if abs(land[0]) > 1.8:
                v *= 1.8 / abs(land[0])
            spins = rng.integers(0, 2)
            yaw0 = math.atan2(v[0], v[1])
            self.p.append(dict(x=x, z=z, t0=t_launch, t1=t_land, tau=tau, vy=vy, v=v,
                               spins=int(spins), yaw_rate=rng.uniform(-6, 6), yaw0=yaw0,
                               roll=rng.uniform(0, 6.28)))

    def state(self, t):
        pos = np.zeros((10, 3))
        rot = np.zeros((10, 3, 3))
        for i, q in enumerate(self.p):
            if t < q['t0']:
                pos[i] = (q['x'], PIN_COM, q['z'])
                rot[i] = np.eye(3)
                continue
            dirh = np.array([q['v'][0], 0, q['v'][1]])
            dirh /= np.linalg.norm(dirh)
            axis = np.cross(np.array([0, 1.0, 0]), dirh)
            total = math.pi / 2 + 2 * math.pi * q['spins']
            if t < q['t1']:
                tau = t - q['t0']
                xz = np.array([q['x'], q['z']]) + q['v'] * tau
                y = PIN_COM + q['vy'] * tau - G * tau * tau / 2
                a = total * (tau / q['tau']) ** 0.9
                R = _axis_angle(axis, a)
            else:
                tau = t - q['t1']
                xz0 = np.array([q['x'], q['z']]) + q['v'] * q['tau']
                k = 0.22
                xz = xz0 + q['v'] * 0.45 * k * (1 - math.exp(-tau / k))
                # one small hop, then rest
                hop = 0.035 * max(0.0, math.sin(math.pi * min(tau / 0.16, 1.0))) if tau < 0.16 else 0.0
                y = PIN_LYING + hop
                yaw = q['yaw_rate'] * 0.25 * (1 - math.exp(-tau / 0.25))
                R = _rot_y(yaw) @ _axis_angle(axis, total)
            pos[i] = (xz[0], y, xz[1])
            rot[i] = R
        return pos, rot

    def events(self):
        """(time, kind, x) for the audio."""
        ev = []
        for q in self.p:
            ev.append((q['t0'], 'pin_hit', q['x']))
            ev.append((q['t1'], 'pin_land', q['x'] + q['v'][0] * q['tau']))
            ev.append((q['t1'] + 0.16, 'pin_tick', q['x'] + q['v'][0] * q['tau']))
        return ev


# ---------------- dominoes ----------------
THETA_C = math.asin((DOM_D - DOM_T) / DOM_H)
THETA_R = math.acos(DOM_T / DOM_D)


def domino_angle(k, t):
    tau = t - (T_DOM0 + k * DT)
    if tau <= 0:
        return 0.0
    if tau < DT:
        u = tau / DT
        return THETA_C * (0.45 * u + 0.55 * u * u)
    u = min((tau - DT) / 0.40, 1.0)
    return THETA_C + (THETA_R - THETA_C) * (1 - (1 - u) ** 3)


def big_angle(t):
    if t <= T_BIG:
        return 0.0
    u = min((t - T_BIG) / (T_BOOM - T_BIG), 1.0)
    a = (math.pi / 2) * u ** 2.6
    if t > T_BOOM:   # one small bounce on landing
        tau = t - T_BOOM
        a = math.pi / 2 - 0.05 * math.exp(-tau / 0.12) * abs(math.sin(tau * 26))
    return a


def wave_front(t):
    return DOM_Z0 + max(0.0, t - T_DOM0) / DT * DOM_D


# ---------------- stickman ----------------
L_THIGH, L_SHIN, L_TORSO, L_UP, L_FORE = 0.27, 0.27, 0.33, 0.20, 0.20
# (t, hip_z, hip_y, torso, Lhip, Lknee, Rhip, Rknee, Lsh, Lel, Rsh, Rel)   angles in radians,
# legs/arms measured from straight down, + = forward (+z); knee bends the shin back, elbow bends the forearm forward
POSES = [
    (0.00, -1.62, 0.40, 0.50, 0.85, 1.20, -0.90, 0.25, 1.40, 0.10, 0.35, 0.00),
    (0.45, -1.53, 0.41, 0.40, 0.85, 1.20, -0.95, 0.25, 1.50, 0.10, 2.55, 0.40),
    (1.20, -1.50, 0.50, 0.15, 0.40, 0.55, -0.40, 0.30, 0.60, 0.40, 1.20, 0.60),
    (2.00, -1.48, 0.53, 0.05, 0.15, 0.10, -0.15, 0.10, 0.20, 0.30, 0.25, 0.30),
]
T_CUT = 0.0   # set below (victory shot)


def _victory_poses(t0):
    # crouch -> jump with arms up (lands on the beat) -> two happy bounces on the next beats
    up = (2.75, 0.10, 2.75, 0.10)
    return [
        (t0 - 0.30, -1.48, 0.53, 0.05, 0.15, 0.10, -0.15, 0.10, 0.20, 0.30, 0.25, 0.30),
        (t0 - 0.05, -1.48, 0.40, 0.30, 0.55, 1.10, 0.45, 1.05, -0.60, 0.20, -0.60, 0.20),
        (t0 + 0.22, -1.48, 0.80, -0.05, 0.10, 0.15, -0.05, 0.25) + up,
        (t0 + 0.50, -1.48, 0.47, 0.10, 0.30, 0.65, 0.25, 0.60) + up,
        (t0 + 0.75, -1.48, 0.60, 0.00, 0.10, 0.20, -0.05, 0.20) + up,
        (t0 + 1.00, -1.48, 0.48, 0.08, 0.28, 0.60, 0.24, 0.58) + up,
        (t0 + 1.25, -1.48, 0.58, 0.00, 0.10, 0.20, -0.05, 0.20) + up,
        (t0 + 1.50, -1.48, 0.50, 0.05, 0.20, 0.40, 0.15, 0.40) + up,
    ]


def _pose_at(t):
    keys = POSES + (_victory_poses(T_JUMP) if t > POSES[-1][0] else [])
    if t <= keys[0][0]:
        return np.array(keys[0][1:])
    if t >= keys[-1][0]:
        return np.array(keys[-1][1:])
    i = max(j for j in range(len(keys) - 1) if keys[j][0] <= t)
    a, b = np.array(keys[i][1:]), np.array(keys[i + 1][1:])
    u = (t - keys[i][0]) / (keys[i + 1][0] - keys[i][0])
    u = u * u * (3 - 2 * u)
    return a + (b - a) * u


def stick_joints(t):
    hz, hy, tor, lh, lk, rh, rk, ls, le, rs, re = _pose_at(t)
    up = lambda a: np.array([0.0, math.cos(a), math.sin(a)])
    down = lambda a: np.array([0.0, -math.cos(a), math.sin(a)])
    hip = np.array([0.0, hy, hz])
    j = {}
    for side, xo, a, k in (('l', -0.07, lh, lk), ('r', 0.07, rh, rk)):
        h = hip + np.array([xo, 0, 0])
        kn = h + L_THIGH * down(a)
        ft = kn + L_SHIN * down(a - k)
        j['hip_' + side], j['knee_' + side], j['foot_' + side] = h, kn, ft
    low = min(j['foot_l'][1], j['foot_r'][1]) - 0.035
    if low < 0:                      # never sink into the floor
        for key in list(j):
            j[key] = j[key] - np.array([0, low, 0])
        hip = hip - np.array([0, low, 0])
    neck = hip + L_TORSO * up(tor)
    j['hip'], j['neck'] = hip, neck
    j['head'] = neck + 0.115 * up(tor * 0.7)
    for side, xo, s, e in (('l', -0.12, ls, le), ('r', 0.12, rs, re)):
        sh = neck - 0.03 * up(tor) + np.array([xo, 0, 0])
        spread = min(max((s - 1.8) / 1.0, 0.0), 1.0) * 0.55
        out = np.array([math.copysign(1.0, xo), 0.0, 0.0])
        du = down(s) * math.cos(spread) + out * math.sin(spread)
        el = sh + L_UP * du
        df = down(s + e) * math.cos(spread) + out * math.sin(spread)
        ha = el + L_FORE * df
        j['sh_' + side], j['elbow_' + side], j['hand_' + side] = sh, el, ha
    return j


STICK_SEGS = [('hip', 'neck'), ('hip_l', 'knee_l'), ('knee_l', 'foot_l'), ('hip_r', 'knee_r'), ('knee_r', 'foot_r'),
              ('sh_l', 'elbow_l'), ('elbow_l', 'hand_l'), ('sh_r', 'elbow_r'), ('elbow_r', 'hand_r'), ('hip_l', 'hip_r'),
              ('sh_l', 'sh_r')]


def stick_capsules(t):
    j = stick_joints(t)
    a = np.array([j[s[0]] for s in STICK_SEGS])
    b = np.array([j[s[1]] for s in STICK_SEGS])
    return a, b, j['head']


# ---------------- camera ----------------
def _keys():
    zb = BIG_Z
    k = [
        (0.00, (0.62, 0.98, -3.05), (0.00, 0.34, 0.20)),
        (0.45, (0.36, 0.29, 2.00), (0.00, 0.17, 3.35)),
        (1.00, (0.85, 0.60, 2.45), (0.00, 0.20, 3.85)),
        (1.40, (0.62, 0.58, 3.55), (0.00, 0.08, 4.75)),
    ]
    for t in (T_DOM0, T_DOM0 + 1.0, T_DOM0 + 2.0):
        zw = wave_front(t)
        k.append((float(t), (0.48, 0.62, zw - 1.15), (0.0, 0.06, zw + 0.40)))
    k += [
        (T_BIG + 0.50, (1.05, 0.70, zb - 1.55), (0.0, 0.30, zb + 0.35)),
        (T_BOOM, (1.20, 0.86, zb - 1.85), (0.0, 0.16, zb + 0.60)),
        (T_CUT, (2.10, 2.30, zb - 3.80), (0.0, 0.00, zb - 1.60)),
    ]
    return k


def _victory_keys():
    return [
        (T_CUT, (1.75, 0.95, -0.05), (-0.05, 0.78, -1.50)),
        (DURATION, (1.45, 0.88, -0.35), (-0.05, 0.80, -1.50)),
    ]


T_CUT = None
KEYS = None
VKEYS = None


def _hermite(keys, t, idx):
    ts = [k[0] for k in keys]
    P = [np.array(k[idx], float) for k in keys]
    if t <= ts[0]:
        return P[0]
    if t >= ts[-1]:
        return P[-1]
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)

    def m(j):
        a, b = max(j - 1, 0), min(j + 1, len(ts) - 1)
        return (P[b] - P[a]) / (ts[b] - ts[a])

    h = ts[i + 1] - ts[i]
    s = (t - ts[i]) / h
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * P[i] + h10 * h * m(i) + h01 * P[i + 1] + h11 * h * m(i + 1)


def shake(t):
    out = np.zeros(3)
    for t0, amp, tau in ((T_STRIKE, 0.010, 0.25), (T_BOOM, 0.030, 0.45)):
        if t >= t0:
            e = amp * math.exp(-(t - t0) / tau)
            out += e * np.array([math.sin(t * 61.0), math.sin(t * 47.0 + 1.3), math.sin(t * 53.0 + 2.1)])
    return out


def camera(t):
    seg2, seg3 = T_DOM0 + 4 * BEAT, T_DOM0 + 8 * BEAT
    if seg2 <= t < seg3:            # head-on: the wave runs at the camera
        zw = wave_front(t)
        pos, look = np.array([0.30, 0.30, zw + 1.35]), np.array([0.0, 0.10, zw - 0.30])
    elif seg3 <= t < T_BIG:         # low side view for the fast run
        zw = wave_front(t)
        pos, look = np.array([1.60, 0.32, zw - 0.05]), np.array([0.0, 0.13, zw + 0.05])
    elif t >= T_CUT:
        pos, look = _hermite(VKEYS, t, 1), _hermite(VKEYS, t, 2)
    else:
        pos = _hermite(KEYS, t, 1) + shake(t)
        look = _hermite(KEYS, t, 2)
    f = look - pos
    f /= np.linalg.norm(f)
    r = np.cross(np.array([0, 1.0, 0]), f)
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    return pos, np.stack([r, u, f], axis=1)


T_CUT = T_BOOM + 4 * S16          # cut to the bowler half a beat after the landing
T_JUMP = T_BOOM + 2 * BEAT        # jump lands on bar 4 beat 4... (lift-off just before)
KEYS = _keys()
VKEYS = _victory_keys()
_j = stick_joints(T_RELEASE)
_h, _e = _j['hand_r'], _j['elbow_r']
_d = (_h - _e) / np.linalg.norm(_h - _e)
_c = _h + _d * 0.05 + np.array([0.04, 0.0, 0.0])
REL_X, REL_H, REL_Z = float(_c[0]), float(max(_c[1], BALL_R)), float(_c[2])
V_IN = (3.0 - REL_Z) / (T_STRIKE - T_RELEASE)


def env(times, t, tau):
    v = 0.0
    for t0 in times:
        if 0 <= t - t0 < 8 * tau:
            v = max(v, math.exp(-(t - t0) / tau))
    return v
