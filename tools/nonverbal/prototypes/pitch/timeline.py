"""
Pitch -> gong -> hopping plates -> xylophone track -> seesaw catapult -> catch.  Score-first.

112.5 BPM (a 16th note = 8 frames at 60 fps). The pitcher winds up on a 3-beat count-in and the
ball hits the gong on bar 0 beat 1. Every later contact is placed on a note: the ball's flight
between two contacts is solved backwards from the two note times (real gravity, no cheating),
the xylophone bars are spaced so a ball rolling at constant speed crosses one per 16th note, and
the catapult's weight is hung exactly high enough that its free fall takes one beat.
The ball lands in the pitcher's glove on bar 4 beat 1, and the last frame matches the first.
"""
import math

import numpy as np

import rig

BPM = 112.5
BEAT = 60.0 / BPM
S16 = BEAT / 4
G = 9.81
GV = np.array([0.0, -G, 0.0])

T_GONG = BEAT                     # bar 0: the gong lands one beat in (hook inside 0.6 s)
T_REL = T_GONG - 0.20


def tm(bar, step=0.0):
    return T_GONG + (bar * 16 + step) * S16


T_TRACK = tm(2)
T_CUP = tm(3)
T_SLAM = tm(3, 4)
T_CATCH = tm(4)
LOOP_TAIL = 1.25                   # after the catch he winds up again; the last frame = frame 0
DURATION = T_CATCH + LOOP_TAIL

BALL_R = 0.045

# gong
GONG_C = np.array([0.0, 1.25, 4.60])
GONG_R, GONG_T = 0.36, 0.03
GONG_HIT = np.array([0.0, 1.29, GONG_C[2] - GONG_T / 2 - BALL_R])

# plates (contact = ball centre when it sits on the plate)
PLATE_R, PLATE_T = 0.085, 0.014
PLATE_TIMES = [tm(0, 4), tm(0, 8), tm(0, 12)] + [tm(1, 2 * j) for j in range(8)]
PLATE_MIDI = [81, 78, 74, 76, 78, 81, 83, 81, 78, 76, 74]
N_PLATE = len(PLATE_TIMES)
_ys = np.linspace(1.05, 0.34, N_PLATE)
_zs = np.linspace(4.25, 3.97, N_PLATE)
PLATES = np.array([[(-0.30 if i % 2 == 0 else 0.30), _ys[i], _zs[i]] for i in range(N_PLATE)])

# xylophone track (runs back toward the pitcher along -z)
TRACK_X = -0.75
N_BAR = 16
BAR_DZ = 0.18
BAR_Z0 = 3.85
TRACK_V = BAR_DZ / S16                 # rolling speed along z
BAR_MIDI = [74, 76, 78, 81, 83, 86, 88, 90, 88, 86, 83, 81, 78, 76, 74, 69]


def track_top(z):
    # bar-top height: slopes down from 0.28 m (far end) to 0.10 m (near end)
    u = (BAR_Z0 - z) / (BAR_Z0 - (BAR_Z0 - (N_BAR - 1) * BAR_DZ))
    return 0.28 + (0.10 - 0.28) * u


BARS = [dict(z=BAR_Z0 - i * BAR_DZ, t=T_TRACK + i * S16, midi=BAR_MIDI[i]) for i in range(N_BAR)]

# seesaw catapult
SEE_PIVOT = np.array([TRACK_X, 0.14, 0.72])
SEE_HALF = 0.28
A_REST, A_FLIP = -0.18, 0.32
CUP_Z = SEE_PIVOT[2] + SEE_HALF * math.cos(A_REST)
WEIGHT_R = 0.085


def seesaw_angle(t):
    if t < T_SLAM:
        return A_REST
    u = min((t - T_SLAM) / 0.06, 1.0)
    a = A_REST + (A_FLIP - A_REST) * (1 - (1 - u) ** 2)
    if t > T_SLAM + 0.06:
        tau = t - T_SLAM - 0.06
        a = A_FLIP - 0.04 * math.exp(-tau / 0.15) * math.sin(tau * 30)
    return a


def plank_end(sign, a):
    """sign=+1: end A (cup, +z side), -1: end B (weight side)."""
    return SEE_PIVOT + sign * SEE_HALF * np.array([0.0, math.sin(a) * sign * sign, math.cos(a)]) * np.array([1, sign, 1])


def end_a(a):
    return SEE_PIVOT + SEE_HALF * np.array([0.0, math.sin(a), math.cos(a)])


def end_b(a):
    return SEE_PIVOT - SEE_HALF * np.array([0.0, math.sin(a), math.cos(a)])


_B_REST = end_b(A_REST)
WEIGHT_Y0 = _B_REST[1] + 0.022 + WEIGHT_R + 0.5 * G * (T_SLAM - T_CUP) ** 2


def weight_pos(t):
    b = end_b(seesaw_angle(t))
    if t < T_CUP:
        return np.array([TRACK_X, WEIGHT_Y0, _B_REST[2]])
    if t < T_SLAM:
        tau = t - T_CUP
        return np.array([TRACK_X, WEIGHT_Y0 - 0.5 * G * tau * tau, _B_REST[2]])
    return np.array([TRACK_X, b[1] + 0.022 + WEIGHT_R, b[2]])


# ---------------- pitcher ----------------
TAU2 = 2 * math.pi
START_POSE = (0.10, 0.55, 0.05, 1.35, 1.55, -0.05, 0.08, 1.40, 0.35, -2.20, 0.70)
POSES = [
    (0.00,) + START_POSE,
    (0.17, 0.38, 0.46, 0.30, 0.65, 0.45, -0.55, 0.35, 1.60, 0.20, -2.60, 0.90),
    (T_REL, 0.45, 0.44, 0.60, 0.70, 0.55, -0.70, 0.40, 0.60, 0.50, 2.30 - TAU2, 0.20),
    (T_REL + 0.35, 0.50, 0.46, 0.75, 0.75, 0.65, -0.20, 0.80, 0.20, 0.60, 0.50 - TAU2, 0.30),
    (T_REL + 1.20, 0.42, 0.53, 0.10, 0.15, 0.10, -0.10, 0.15, 0.40, 0.50, 0.30 - TAU2, 0.40),
    (T_CUP - 0.1, 0.42, 0.53, 0.05, 0.10, 0.10, -0.10, 0.10, 0.40, 0.50, 0.30 - TAU2, 0.40),
    (T_SLAM + 0.10, 0.36, 0.52, -0.15, 0.10, 0.15, -0.10, 0.15, 2.00, 0.60, 0.40 - TAU2, 0.40),
    (T_CATCH - 0.50, 0.20, 0.53, -0.20, 0.30, 0.20, -0.20, 0.10, 2.70, 0.30, 0.60 - TAU2, 0.50),
    (T_CATCH, 0.18, 0.51, -0.18, 0.25, 0.25, -0.15, 0.20, 2.80, 0.25, 0.80 - TAU2, 0.60),
    (T_CATCH + 0.25, 0.16, 0.48, 0.05, 0.40, 0.45, 0.10, 0.45, 2.10, 0.60, 0.80 - TAU2, 0.60),
    (T_CATCH + 0.55, 0.12, 0.54, 0.05, 0.05, 0.05, -0.05, 0.05, 0.90, 1.60, 0.80 - TAU2, 1.70),
    (T_CATCH + 0.90, 0.11, 0.56, -0.05, 0.60, 0.90, -0.05, 0.08, 1.10, 0.90, -1.40 - TAU2, 0.50),
    (DURATION,) + START_POSE[:9] + (START_POSE[9] - TAU2, START_POSE[10]),
]


def pitcher(t):
    return rig.joints(rig.interp(POSES, t))


def glove_point(j):
    d = j['hand_l'] - j['elbow_l']
    d /= np.linalg.norm(d)
    return j['hand_l'] + d * 0.035


# ---------------- ball path ----------------
def _solve(p0, p1, dt):
    return (p1 - p0 - 0.5 * GV * dt * dt) / dt


def _rel_point():
    j = pitcher(T_REL)
    return j['hand_r'] + (j['hand_r'] - j['elbow_r']) / np.linalg.norm(j['hand_r'] - j['elbow_r']) * 0.04


P_REL = _rel_point()
PLATE_TOPS = PLATES + np.array([0.0, PLATE_T / 2 + BALL_R, 0.0])
TRACK_START = np.array([TRACK_X, track_top(BAR_Z0) + BALL_R, BAR_Z0])
CUP_POS = end_a(A_REST) + np.array([0.0, 0.03 + BALL_R, 0.0])
T_LAUNCH = T_SLAM + 0.05
LAUNCH_POS = end_a(A_FLIP) + np.array([0.0, 0.03 + BALL_R, 0.0])
CATCH_POS = glove_point(pitcher(T_CATCH))

# flights: (t0, p0, t1, p1)
FLIGHTS = [(T_REL, P_REL, T_GONG, GONG_HIT), (T_GONG, GONG_HIT, PLATE_TIMES[0], PLATE_TOPS[0])]
for i in range(N_PLATE - 1):
    FLIGHTS.append((PLATE_TIMES[i], PLATE_TOPS[i], PLATE_TIMES[i + 1], PLATE_TOPS[i + 1]))
FLIGHTS.append((PLATE_TIMES[-1], PLATE_TOPS[-1], T_TRACK, TRACK_START))
FLIGHTS.append((T_LAUNCH, LAUNCH_POS, T_CATCH, CATCH_POS))
FLIGHTS = [(a, p, b, q, _solve(p, q, b - a)) for a, p, b, q in FLIGHTS]
LAST_BAR_T = BARS[-1]['t']


def ball(t):
    """(centre, held_by): held_by in {'set', 'right', None, 'glove'}"""
    if t >= T_CATCH + 0.55:
        j = pitcher(t)
        d = (j['hand_r'] - j['elbow_r']) / np.linalg.norm(j['hand_r'] - j['elbow_r'])
        return j['hand_r'] + d * 0.04, 'right'
    if t < T_REL:
        j = pitcher(t)
        d = (j['hand_r'] - j['elbow_r']) / np.linalg.norm(j['hand_r'] - j['elbow_r'])
        return j['hand_r'] + d * 0.04, 'right'
    for a, p, b, q, v in FLIGHTS:
        if a <= t < b:
            tau = t - a
            return p + v * tau + 0.5 * GV * tau * tau, None
    if T_TRACK <= t < T_CUP:
        z = BAR_Z0 - TRACK_V * (t - T_TRACK)
        if z >= BARS[-1]['z']:
            return np.array([TRACK_X, track_top(z) + BALL_R, z]), None
        # last stretch: from the last bar into the cup
        u = (t - LAST_BAR_T) / (T_CUP - LAST_BAR_T)
        p0 = np.array([TRACK_X, track_top(BARS[-1]['z']) + BALL_R, BARS[-1]['z']])
        return p0 + (CUP_POS - p0) * u, None
    if T_CUP <= t < T_LAUNCH:
        a = seesaw_angle(t)
        return end_a(a) + np.array([0.0, 0.03 + BALL_R, 0.0]), None
    j = pitcher(t)
    return glove_point(j), 'glove'


def ball_spin(t):
    # rough spin angle for the stitches: fast in flight, rolling on the track
    if t < T_REL:
        return 0.0
    if t < T_TRACK:
        return (t - T_REL) * 40.0
    if t < T_CUP:
        return (T_TRACK - T_REL) * 40.0 + (t - T_TRACK) * TRACK_V / BALL_R
    return (T_TRACK - T_REL) * 40.0 + (T_CUP - T_TRACK) * TRACK_V / BALL_R + max(0.0, t - T_LAUNCH) * 12.0


def contacts():
    """every sounding contact: (time, kind, midi or None, x)"""
    ev = [(T_GONG, 'gong', None, 0.0)]
    for i, tt in enumerate(PLATE_TIMES):
        ev.append((tt, 'plate', PLATE_MIDI[i], PLATES[i][0]))
    for b in BARS:
        ev.append((b['t'], 'bar', b['midi'], TRACK_X))
    ev.append((T_CUP, 'cup', None, TRACK_X))
    ev.append((T_SLAM, 'slam', None, TRACK_X))
    ev.append((T_CATCH, 'catch', None, -0.2))
    return ev


def note_colour(m):
    u = np.clip((m - 69) / (90 - 69), 0, 1)
    stops = np.array([[0.25, 0.75, 1.00], [0.45, 1.00, 0.70], [1.00, 0.85, 0.30], [1.00, 0.45, 0.35]])
    x = u * (len(stops) - 1)
    i = min(int(x), len(stops) - 2)
    f = x - i
    return tuple(stops[i] * (1 - f) + stops[i + 1] * f)


# ---------------- camera ----------------
def _keys():
    k = [
        (0.00, (0.62, 1.72, -2.05), (0.00, 0.92, 3.00)),
        (T_REL, (0.50, 1.50, -0.10), (0.00, 1.08, 4.60)),
        (T_GONG, (0.40, 1.30, 2.85), (0.00, 1.22, 4.60)),
        (tm(0, 6), (0.00, 1.22, 2.70), (0.00, 0.98, 4.30)),
        (tm(1, 0), (0.00, 0.95, 2.65), (0.00, 0.74, 4.20)),
        (tm(1, 14), (-0.10, 0.62, 2.55), (-0.20, 0.40, 4.00)),
        (T_TRACK, (-0.20, 0.55, 2.50), (-0.75, 0.25, 3.70)),
    ]
    for t in (T_TRACK + 0.6, T_TRACK + 1.2, T_TRACK + 1.8):
        zb = BAR_Z0 - TRACK_V * (t - T_TRACK)
        k.append((t, (-0.22, 0.44, zb - 0.80), (-0.75, 0.20, zb + 0.25)))
    k += [
        (T_CUP - 0.05, (0.75, 0.70, 2.20), (-0.75, 0.40, 0.85)),
        (T_SLAM, (1.10, 0.95, 2.05), (-0.55, 0.65, 0.60)),
        (T_SLAM + 0.30, (2.10, 1.25, 1.45), (-0.45, 1.40, 0.50)),
        (T_SLAM + 0.85, (2.90, 1.55, 1.10), (-0.35, 2.20, 0.40)),
        (T_CATCH, (2.20, 1.35, 0.20), (-0.15, 1.10, 0.25)),
        (T_CATCH + 0.55, (1.80, 1.35, -0.90), (0.00, 0.88, 0.40)),
        (DURATION, (0.62, 1.72, -2.05), (0.00, 0.92, 3.00)),
    ]
    return k


KEYS = _keys()


def _hermite(keys, t, idx):
    ts = [k[0] for k in keys]
    P = [np.array(k[idx], float) for k in keys]
    if t <= ts[0]:
        return P[0]
    if t >= ts[-1]:
        return P[-1]
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)

    def m(j):
        if j == 0 or j == len(ts) - 1:
            return np.zeros(3)
        return (P[j + 1] - P[j - 1]) / (ts[j + 1] - ts[j - 1])

    h = ts[i + 1] - ts[i]
    s = (t - ts[i]) / h
    h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
    return h00 * P[i] + h10 * h * m(i) + h01 * P[i + 1] + h11 * h * m(i + 1)


def shake(t):
    out = np.zeros(3)
    for t0, amp, tau in ((T_GONG, 0.012, 0.25), (T_SLAM, 0.020, 0.30)):
        if t >= t0:
            e = amp * math.exp(-(t - t0) / tau)
            out += e * np.array([math.sin(t * 61.0), math.sin(t * 47.0 + 1.3), math.sin(t * 53.0 + 2.1)])
    return out


def camera(t):
    pos = _hermite(KEYS, t, 1) + shake(t)
    look = _hermite(KEYS, t, 2)
    f = look - pos
    f /= np.linalg.norm(f)
    r = np.cross(np.array([0, 1.0, 0]), f)
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    return pos, np.stack([r, u, f], axis=1)


def env(times, t, tau):
    v = 0.0
    for t0 in times:
        if 0 <= t - t0 < 8 * tau:
            v = max(v, math.exp(-(t - t0) / tau))
    return v
