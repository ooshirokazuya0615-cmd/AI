"""KAKU & RONDO #2 Square Track: every time and position is decided here, score first.

World: y up, ground y=0. Square track, centre line at |x| or |z| = H. Kaku moves one 1.8 m cell per tip,
one tip per beat (112.5 BPM = 32 frames). Lap: C0 -> C1 (+x) -> C2 (+z) -> C3 (-x) -> C0 (-z).
"""
import math

import numpy as np

import rig

BPM = 112.5
BEAT = 60.0 / BPM            # 0.5333 s = 32 frames at 60 fps
BAR = 4 * BEAT
NBEATS = 48
DURATION = NBEATS * BEAT     # 25.6 s, loops
CELL = 1.8
HALF = 0.9
NC = 4
H = NC * CELL                # 7.2
UP = np.array([0.0, 1.0, 0.0])
X3, Z3 = np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])
TIP = 0.46                   # seconds a tip takes; it lands exactly on the beat

# local face -> note (D major).  The chipped corner is local (-1,+1,+1): faces F#, D', A = the signature.
FACE_NOTE = {(1, 0, 0): 71, (-1, 0, 0): 66, (0, 1, 0): 74, (0, -1, 0): 62, (0, 0, 1): 69, (0, 0, -1): 64}
FACE_IDX = {(1, 0, 0): 0, (-1, 0, 0): 1, (0, 1, 0): 2, (0, -1, 0): 3, (0, 0, 1): 4, (0, 0, -1): 5}
NOTE_SECTION = {62: 0, 64: 1, 66: 2, 69: 3, 71: 4, 74: 5}
R0 = np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]], float)
ZIGZAG = 'SFFFFSSFSFSSF'      # tips 28..40 on the last straight: S = sideways (in/out), F = forward (-z)
T_START = 1 * BEAT           # start fork + first tip
B_HES = 26                   # Kaku lands the first cell of the last straight on beat 26, holds beat 27
T_HES0, T_HES1 = 26 * BEAT + 0.10, 28 * BEAT - TIP - 0.02
B_FINISH_K = 40
B_FINISH_R = 39
T_FINISH_K = B_FINISH_K * BEAT
T_FINISH_R = B_FINISH_R * BEAT
T_LOOK_TI = 42.2 * BEAT       # knot turns toward TI, TI does not ring
T_RESET = 45.5 * BEAT         # racers go back to the start while the camera looks at the board
FINISH_Z = -H + HALF          # finish line across the last straight
START_X = -H + HALF           # start line across the first straight
TI_POS = np.array([-10.6, 0.0, -4.6])


def tb(b):
    return b * BEAT


def rodrigues(axis, ang):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


def bottom_face(R):
    loc = R.T @ np.array([0.0, -1.0, 0.0])
    return tuple(int(v) for v in np.rint(loc))


# ---------------------------------------------------------------- Kaku's tips
def _build_tips():
    moves = [(b, X3) for b in range(2, 10)] + [(b, Z3) for b in range(10, 18)] + \
            [(b, -X3) for b in range(18, 26)] + [(26, -Z3)]
    lat = 0
    b = 28
    for m in ZIGZAG:
        if m == 'F':
            d = -Z3
        else:
            d = X3 if lat == 0 else -X3      # inward on the last straight is +x
            lat = 1 - lat
        moves.append((b, d))
        b += 1
    tips = []
    c = np.array([-H, HALF, -H])
    R = R0.copy()
    for beat, d in moves:
        Rn = np.rint(rodrigues(np.cross(UP, d), math.pi / 2) @ R)
        cn = c + d * CELL
        face = bottom_face(Rn)
        tips.append(dict(beat=beat, t=tb(beat), d=d, c0=c.copy(), c1=cn.copy(), R0=R.copy(), R1=Rn,
                         note=FACE_NOTE[face], face=FACE_IDX[face]))
        c, R = cn, Rn
    return tips


TIPS = _build_tips()
assert TIPS[-1]['beat'] == B_FINISH_K and abs(TIPS[-1]['c1'][2] + H) < 1e-6
assert [tp['note'] for tp in TIPS[-3:]] == [66, 69, 74]


def _ease_tip(u):
    """Returns the fraction of 90 deg: a slow lift that hangs near balance, then a fall that speeds up."""
    if u < 0.5:
        return 0.5 * math.sin((math.pi / 2) * u / 0.5)
    return 0.5 + 0.5 * ((u - 0.5) / 0.5) ** 2.2


def kaku(t):
    """Centre (3,), rotation local->world (3x3), travel dir."""
    if t >= T_RESET:
        return np.array([-H, HALF, -H]), R0.copy(), X3
    prev = None
    for tp in TIPS:
        dur = tp['t'] - T_START if tp is TIPS[0] else TIP     # the first tip starts on the start strike
        if t < tp['t'] - dur:
            break
        if t < tp['t']:
            u = (t - (tp['t'] - dur)) / dur
            ang = math.pi / 2 * _ease_tip(u)
            piv = tp['c0'] + tp['d'] * HALF - UP * HALF
            Rt = rodrigues(np.cross(UP, tp['d']), ang)
            return piv + Rt @ (tp['c0'] - piv), Rt @ tp['R0'], tp['d']
        prev = tp
    if prev is None:
        return np.array([-H, HALF, -H]), R0.copy(), X3
    c, R, d = prev['c1'].copy(), prev['R1'].copy(), prev['d']
    tau = t - prev['t']
    # small rock forward on the leading edge right after landing (heavy settle)
    amp = 0.02 + 0.03 * min(max((prev['beat'] - 2) / 38.0, 0.0), 1.0)      # the settle grows through the race
    rock = amp * (tau / 0.05) * math.exp(1 - tau / 0.05) if tau < 0.4 else 0.0
    # habit 1: after the last note, one small rock-back onto the same face, just to be sure (lands on b42)
    if prev is TIPS[-1] and tb(41) <= t < tb(42):
        u = (t - tb(41)) / BEAT
        rock = max(rock, 0.52 * (math.sin(u * math.pi) if u < 0.5 else (1 - ((u - 0.5) / 0.5) ** 2.0)))
    # hesitation: lean toward the straight way, hold, lean back
    if prev['beat'] == B_HES and T_HES0 <= t <= T_HES1:
        a0, a1 = T_HES0, T_HES1
        if t < a0 + 0.16:
            lean = 0.34 * smooth((t - a0) / 0.16)
        elif t > a1 - 0.13:
            lean = 0.34 * (1 - smooth((t - (a1 - 0.13)) / 0.13))
        else:
            lean = 0.34
        rock = max(rock, lean)
        d = -Z3
    if rock > 1e-5:
        piv = c + d * HALF - UP * HALF
        Rt = rodrigues(np.cross(UP, d), rock)
        c = piv + Rt @ (c - piv)
        R = Rt @ R
    return c, R, d


def landings():
    return [(tp['t'], tp['note'], tp['c1'], tp['face']) for tp in TIPS]


def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def kaku_look(t):
    """Direction the headband knot faces (horizontal unit vector)."""
    c, R, d = kaku(t)
    if t >= T_RESET:
        return X3
    if T_LOOK_TI <= t < T_RESET:
        to = TI_POS - c
        to[1] = 0
        to /= np.linalg.norm(to)
        u = smooth((t - T_LOOK_TI) / 0.35)
        base = -Z3
        v = base * (1 - u) + to * u
        return v / np.linalg.norm(v)
    # during the hesitation the knot glances 50 deg toward the score path (+x), then back
    if T_HES0 + 0.15 <= t <= T_HES1 - 0.10:
        u = min(smooth((t - (T_HES0 + 0.15)) / 0.1), smooth(((T_HES1 - 0.10) - t) / 0.1))
        a = math.radians(50) * u
        v = -Z3 * math.cos(a) + X3 * math.sin(a)
        return v / np.linalg.norm(v)
    # look where it travels; on the last straight it looks down the straight (-z)
    if t > tb(26) - TIP:
        return -Z3
    return d


def box_exit(c, R, dirw, y):
    """Distance from the centre axis at height y to the cube surface along horizontal dirw."""
    p0 = np.array([c[0], y, c[2]])
    lo, hi = 0.0, 1.6
    for _ in range(30):
        mid = (lo + hi) / 2
        q = R.T @ (p0 + dirw * mid - c)
        inside = np.all(np.abs(q) <= HALF)
        lo, hi = (mid, hi) if inside else (lo, mid)
    return p0 + dirw * lo


def knot(t):
    c, R, _ = kaku(t)
    lk = kaku_look(t)
    k = box_exit(c, R, lk, c[1]) + lk * 0.035
    side = np.cross(UP, lk)
    # tails hang from the knot; they swing after each landing
    sw = 0.0
    for tp in TIPS:
        if 0 <= t - tp['t'] < 0.8:
            sw = 0.10 * math.exp(-(t - tp['t']) / 0.25) * math.sin((t - tp['t']) * 16)
    t1 = k + lk * (0.10 + sw) + UP * -0.42 + side * 0.09
    t2 = k + lk * (0.07 - sw * 0.7) + UP * -0.38 - side * 0.08
    return k, t1, t2


# ---------------------------------------------------------------- Rondo
R_BALL = 0.30
V_R = math.pi * R_BALL / (BEAT / 3)     # brass line touches the ground on every triplet eighth
LANE_O = 1.6


def _arc(c, r, a0, a1, n):
    return [c + r * np.array([math.cos(a), 0.0, math.sin(a)]) for a in np.linspace(a0, a1, n)]


def _bez(p0, p1, p2, p3, n):
    return [(1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u * u * p2 + u ** 3 * p3
            for u in np.linspace(0, 1, n)]


def _corner(lc, din, dout, over, rad, merge):
    """Swing a little wide past the lane corner lc, round with radius rad, merge back onto the new lane."""
    q = lc + din * over
    cen = q + dout * rad
    a0 = math.atan2((q - cen)[2], (q - cen)[0])
    tgt = q + din * rad + dout * rad
    a1 = math.atan2((tgt - cen)[2], (tgt - cen)[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    pts = _arc(cen, rad, a0, a0 + da, 24)
    q2 = pts[-1]
    end = lc + dout * merge
    pts += _bez(q2, q2 + dout * merge * 0.45, end - dout * merge * 0.35, end, 30)[1:]
    return pts, cen


OVER = [(2.4, 2.0, 7.5), (2.1, 1.9, 7.0), (1.9, 1.8, 6.5)]


def build_rondo_path():
    o = LANE_O
    start = np.array([-H, 0.0, -H - o])
    lcs = [(np.array([H + o, 0.0, -H - o]), X3, Z3), (np.array([H + o, 0.0, H + o]), Z3, -X3),
           (np.array([-H - o, 0.0, H + o]), -X3, -Z3)]
    pts = [start]
    apex_pts = []
    for (lc, din, dout), ov in zip(lcs, OVER):
        cp, cen = _corner(lc, din, dout, *ov)
        apex_pts.append(cp[len(cp) // 4])
        pts += cp
    pts.append(np.array([-H - o, 0.0, FINISH_Z]))
    pts.append(np.array([-H - o, 0.0, FINISH_Z - 30.0]))
    P = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(np.linalg.norm(b - a) / 0.02))
        for k in range(1, n + 1):
            P.append(a + (b - a) * k / n)
    P = np.array(P)
    S = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    apex_s = [float(S[np.argmin(np.linalg.norm(P - a, axis=1))]) for a in apex_pts]
    on_side4 = (np.abs(P[:, 0] - (-H - o)) < 0.02) & (S > apex_s[2])
    s_fin = float(S[on_side4][np.argmin(np.abs(P[on_side4, 2] - FINISH_Z))])
    return P, S, apex_s, s_fin


R_PATH, R_S, R_APEX, R_SFIN = build_rondo_path()
TICK = BEAT / 3
T_ACC = 2 * TICK                   # accelerates over two triplet eighths
S_ACC = 0.5 * V_R * T_ACC          # = one brass-line spacing
ZONE_B, ZONE_A = 5.0, 5.5          # braking before / speeding up after the apex (m)


def _speed(S, vmins):
    v = np.full_like(S, V_R)
    for ap, vm in zip(R_APEX, vmins):
        u = (S - ap) / np.where(S < ap, ZONE_B, ZONE_A)
        w = np.where(np.abs(u) < 1, np.cos(np.clip(u, -1, 1) * math.pi / 2) ** 2, 0.0)
        v = np.minimum(v, V_R - (V_R - vm) * w)
    return v


def _loss(ap, vm):
    s = np.linspace(ap - ZONE_B, ap + ZONE_A, 4000)
    u = (s - ap) / np.where(s < ap, ZONE_B, ZONE_A)
    v = V_R - (V_R - vm) * np.cos(u * math.pi / 2) ** 2
    return float(np.trapezoid(1 / v - 1 / V_R, s))


def _solve_vmin(ap, target):
    lo, hi = 0.05, V_R
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if _loss(ap, m) > target else (lo, m)
    return (lo + hi) / 2


# total time Rondo must lose so it crosses about one beat before Kaku; split into whole ticks
_t_free = T_START + T_ACC + (R_SFIN - S_ACC) / V_R
_need = T_FINISH_R - _t_free
_split = [0.40, 0.33, 0.27]
LOSS_TICKS = [int(round(_need * f / TICK)) for f in _split]
R_VMIN = [_solve_vmin(ap, n * TICK) for ap, n in zip(R_APEX, LOSS_TICKS)]
_S = np.arange(0.0, R_S[-1], 0.005)
_V = _speed(_S, R_VMIN)
_T = np.empty_like(_S)
_acc = _S < S_ACC
_T[_acc] = T_START + np.sqrt(2 * _S[_acc] / (V_R / T_ACC))
_i0 = int(np.argmax(~_acc))
_T[_i0:] = T_START + T_ACC + np.concatenate([[0.0], np.cumsum(0.005 / _V[_i0 + 1:])]) * 1.0 + (_S[_i0] - S_ACC) / V_R
T_FIN_R_ACTUAL = float(np.interp(R_SFIN, _S, _T))
T_STOP = T_FIN_R_ACTUAL + 2.4


def rondo_s(t):
    if t >= T_RESET or t <= T_START:
        return 0.0
    if t <= T_FIN_R_ACTUAL:
        return float(np.interp(t, _T, _S))
    dt = min(t, T_STOP) - T_FIN_R_ACTUAL
    dec = V_R / (T_STOP - T_FIN_R_ACTUAL)
    return R_SFIN + V_R * dt - 0.5 * dec * dt * dt


def rondo(t):
    s = rondo_s(t)
    i = int(np.clip(np.searchsorted(R_S, s), 1, len(R_S) - 1))
    a, b = R_PATH[i - 1], R_PATH[i]
    f = (s - R_S[i - 1]) / max(R_S[i] - R_S[i - 1], 1e-9)
    p = a + (b - a) * f
    j = int(np.clip(np.searchsorted(R_S, s + 0.25), 1, len(R_S) - 1))
    d = R_PATH[j] - p
    d = d / (np.linalg.norm(d) + 1e-9)
    if s <= 0.0:
        d = X3
    return np.array([p[0], R_BALL, p[2]]), d, s / R_BALL


def rondo_ticks():
    """Times when the brass line touches the ground (every pi*r of travel)."""
    out = []
    k = 1
    ts = np.arange(0, DURATION, 1 / 1200)
    ss = np.array([rondo_s(t) for t in ts])
    for t, s0, s1 in zip(ts[1:], ss[:-1], ss[1:]):
        while s1 >= k * math.pi * R_BALL > s0:
            out.append(t)
            k += 1
    return out


def rondo_offtrack(t):
    p, _, _ = rondo(t)
    m = max(abs(p[0]), abs(p[2]))
    return max(0.0, m - (H + LANE_O + 0.3))


# ---------------------------------------------------------------- lap progress (for checking who leads)
def lap_progress_point(p):
    """Lap position in metres: nearest point on the centre square, measured from C0 going +x."""
    x, z = p[0], p[2]
    segs = [(np.array([-H, -H]), np.array([H, -H])), (np.array([H, -H]), np.array([H, H])),
            (np.array([H, H]), np.array([-H, H])), (np.array([-H, H]), np.array([-H, -H]))]
    best = (1e9, 0.0)
    q = np.array([x, z])
    for k, (a, b) in enumerate(segs):
        ab = b - a
        u = float(np.clip(np.dot(q - a, ab) / np.dot(ab, ab), 0, 1))
        d = np.linalg.norm(a + ab * u - q)
        if d < best[0] - 1e-9:
            best = (d, k * 2 * H + u * 2 * H)
    return best[1]


# ---------------------------------------------------------------- stands, glow, look
def section_glow(t):
    g = np.zeros(6)
    for tl, note, _, _ in landings():
        if 0 <= t - tl < 3.0:
            g[NOTE_SECTION[note]] += math.exp(-(t - tl) / 0.45)
    fin = finale(t)
    return np.minimum(g, 1.0), fin


def finale(t):
    tau = t - T_FINISH_K
    if tau < 0:
        return 0.0
    if t > T_RESET:
        return 0.0
    return min(1.0, tau / 0.12) * (0.55 + 0.45 * math.exp(-tau / 1.6)) * (1 - smooth((t - 44.2 * BEAT) / (1.2 * BEAT)))


def fork_look(t):
    """(target x, target z, blend) — the stands turn to watch Rondo when it wanders off the track."""
    p, _, _ = rondo(t)
    off = rondo_offtrack(t)
    # smooth the blend with a short look-back so heads turn together and settle
    acc = 0.0
    for k in range(10):
        tk = t - k * 0.04
        acc = max(acc, min(1.0, rondo_offtrack(tk) / 0.6) * (1 - k * 0.06))
    blend = smooth(acc)
    gate = smooth((t - tb(8.5)) / 0.4) if t < tb(17) else smooth((t - tb(20.5)) / 0.4)
    blend *= gate
    # only the first two corners: on the third the stands keep listening to Kaku's melody
    if t > tb(25):
        blend *= 1 - smooth((t - tb(25)) / (0.75 * BEAT))
    return float(p[0]), float(p[2]), float(blend)


# ---------------------------------------------------------------- the starter (ceramic stickman) and fork
START_FORK = np.array([-H + 0.2, 0.0, -H - 4.0])
STARTER_ORIGIN = np.array([-H - 0.62, 0.0, -H - 4.0])
STARTER_SCALE = 1.72
_REST = (0.0, 0.55, 0.0, 0.05, 0.10, -0.05, 0.10, 0.10, 0.25, 0.15, 0.30)
_RAISE = (-0.04, 0.55, -0.12, 0.05, 0.12, -0.15, 0.25, 0.20, 0.30, 2.75, 0.85)
_HIT = (0.06, 0.53, 0.18, 0.25, 0.30, -0.20, 0.25, 0.10, 0.25, 1.05, 0.10)
_FOLLOW = (0.04, 0.54, 0.10, 0.18, 0.22, -0.15, 0.20, 0.10, 0.25, 0.70, 0.25)
STARTER_KEYS = [(-0.40, *_REST), (0.10, *_RAISE), (0.30, *_RAISE), (T_START, *_HIT), (T_START + 0.25, *_FOLLOW),
                (T_START + 1.1, *_REST), (DURATION - 0.40, *_REST), (DURATION + 0.10, *_RAISE)]


def starter(t):
    tt = t if t >= -0.4 else t + DURATION
    pose = rig.interp(STARTER_KEYS, tt if tt < DURATION - 0.4 else tt)
    if t < 0.10 and t >= 0:
        pose = rig.interp(STARTER_KEYS, t)
    j = rig.joints(pose)
    out = {}
    for k, v in j.items():
        w = v * STARTER_SCALE
        out[k] = STARTER_ORIGIN + np.array([w[2], w[1], -w[0]])   # rig faces +z; the starter faces +x
    return out


def mallet(j):
    a = j['elbow_r']
    b = j['hand_r']
    d = (b - a) / (np.linalg.norm(b - a) + 1e-9)
    tip = b + d * 0.42
    return b, tip


# ---------------------------------------------------------------- metronome (the referee)
METRO = np.array([-2.5, 0.0, 2.5])


def metronome(t):
    return 0.33 * math.cos(math.pi * t / BEAT)


# ---------------------------------------------------------------- scoreboard
BOARD = np.array([-29.9, 12.1, -21.2])
BOARD_N = np.array([0.895, 0.0, 0.446])     # the face looks toward the first frame's camera


def board(t):
    """(cube state, ball state, cube flip age, ball flip age): state 0 = '0', 1 = '1', 2 = note."""
    cube, ball, fc, fb = 0.0, 0.0, -1.0, -1.0
    t_back = T_BOARD_BACK
    if T_FINISH_R <= t < t_back:
        ball, fb = 1.0, t - T_FINISH_R
    if T_BOARD_NOTE <= t < t_back:
        cube, fc = 2.0, t - T_BOARD_NOTE
    if t >= t_back:
        fc = fb = t - t_back
    return cube, ball, fc, fb


T_BOARD_NOTE = 44.25 * BEAT     # the cube panel flips to the note on camera
T_BOARD_BACK = 46.5 * BEAT      # both panels flip back to 0-0


def fp_fade(t):
    return 1.0 - smooth((t - 44.0 * BEAT) / (1.6 * BEAT))


# ---------------------------------------------------------------- grid data (score path + footprints)
GRID = 16
GOFF = 8


def cell_index(p):
    return int(round(p[0] / CELL)) + GOFF, int(round(p[2] / CELL)) + GOFF


def score_cells():
    cells = set()
    side_dir = [X3, Z3, -X3, -Z3]
    side_in = [Z3, -X3, -Z3, X3]
    corners = [np.array([-H, 0, -H]), np.array([H, 0, -H]), np.array([H, 0, H]), np.array([-H, 0, H])]
    for k in range(4):
        p = corners[k] + side_dir[k] * CELL
        cells.add(cell_index(p))
        lat = 0
        for m in ZIGZAG:
            if m == 'F':
                p = p + side_dir[k] * CELL
            else:
                p = p + side_in[k] * CELL * (1 if lat == 0 else -1)
                lat = 1 - lat
            cells.add(cell_index(p))
    return cells


SCORE = score_cells()


def _side4_order():
    order = {}
    p = np.array([-H, 0, -H]) + np.array([0, 0, H]) * 0 + np.array([-H * 0, 0, 0])
    p = np.array([-H, 0, H]) + (-Z3) * CELL
    order[cell_index(p)] = 1
    lat = 0
    k = 2
    for m in ZIGZAG:
        if m == 'F':
            p = p + (-Z3) * CELL
        else:
            p = p + X3 * CELL * (1 if lat == 0 else -1)
            lat = 1 - lat
        order[cell_index(p)] = k
        k += 1
    return order


SIDE4_ORDER = _side4_order()


def grid_data(t):
    g = np.zeros((GRID, GRID, 4), 'f4')
    g[..., 1] = -1.0
    for (i, j) in SCORE:
        g[j, i, 0] = 1.0 + SIDE4_ORDER.get((i, j), 0) / 100.0
    for tp in TIPS:
        if tp['t'] <= t and t < T_RESET + 0.5:
            i, j = cell_index(tp['c1'])
            g[j, i, 1] = tp['t']
            g[j, i, 2] = 1.0 if (i, j) in SCORE else 0.0
            g[j, i, 3] = tp['face']
    return g


# ---------------------------------------------------------------- report
if __name__ == '__main__':
    print('V_R', round(V_R, 3), 'loss ticks', LOSS_TICKS, 'vmin', [round(v, 2) for v in R_VMIN], 'rondo finish', round(T_FIN_R_ACTUAL, 3), 'beat', round(T_FIN_R_ACTUAL / BEAT, 2))
    print('notes', ' '.join(str(tp['note']) for tp in TIPS))
    for b in range(0, 48, 2):
        t = tb(b)
        kc, _, _ = kaku(t)
        rp, _, _ = rondo(t)
        print(f'beat {b:2d} t={t:5.2f}  kaku lap {lap_progress_point(kc):5.1f}  rondo lap {lap_progress_point(rp):5.1f} off {rondo_offtrack(t):4.1f} look {fork_look(t)[2]:.2f}')
    ticks = rondo_ticks()
    print('ticks', len(ticks), [round((x / (BEAT / 3)) % 1, 3) for x in ticks[:12]])
