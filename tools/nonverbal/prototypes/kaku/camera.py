"""Shots for #2 Square Track. Cuts only on bar heads; inside a shot the camera moves on a Hermite curve."""
import math

import numpy as np

import timeline as T

B = T.BEAT


def V(*a):
    return np.array(a, float)


def kc(t):
    return T.kaku(t)[0]


def rp(t):
    return T.rondo(t)[0]


# each shot: (t0, t1, function(t) -> pos, look, tanH)
def _keys(keys):
    ts = [k[0] for k in keys]

    def f(t):
        if t <= ts[0]:
            k = keys[0]
            return V(*k[1]), V(*k[2]), k[3]
        if t >= ts[-1]:
            k = keys[-1]
            return V(*k[1]), V(*k[2]), k[3]
        i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        out = []
        for idx in (1, 2, 3):
            P = [np.atleast_1d(np.array(k[idx], float)) for k in keys]

            def m(j):
                if j == 0 or j == len(ts) - 1:
                    return np.zeros_like(P[j])
                return (P[j + 1] - P[j - 1]) / (ts[j + 1] - ts[j - 1])
            h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
            out.append(h00 * P[i] + h10 * h * m(i) + h01 * P[i + 1] + h11 * h * m(i + 1))
        return out[0], out[1], float(out[2][0])
    return f


def ks(t):
    """Kaku's position averaged over one beat, so following shots glide instead of stop-go."""
    s = np.mean([kc(t - B / 2 + B * i / 15) for i in range(16)], axis=0)
    s[1] = 0.9
    return s


A_POS, A_LOOK, A_FOV = (-0.6, 2.4, -6.6), (-9.0, 0.8, -9.2), 0.78
A_DIR = (V(*A_LOOK) - V(*A_POS)) / np.linalg.norm(V(*A_LOOK) - V(*A_POS))
BOARD_LOOK = tuple(T.BOARD)

SHOTS = [
    # bar 0: start - both racers, the starter and the start fork; they come toward us
    (0.0, 4 * B, _keys([(0.0, A_POS, A_LOOK, A_FOV), (4 * B, (2.6, 3.4, -4.4), (-5.0, 0.7, -9.0), 0.74)])),
    # bar 1: high reveal - the whole track is SQUARE, then down toward corner 1
    (4 * B, 8 * B, _keys([(4 * B, (0.0, 30.0, 8.0), (0.0, 0.0, -1.0), 0.66), (8 * B, (1.5, 15.0, 1.5), (6.0, 0.0, -6.6), 0.66)])),
    # bar 2: corner 1 from above the infield: Kaku turns square while the stand turns to watch Rondo
    (8 * B, 12 * B, _keys([(8 * B, (2.0, 4.5, 5.0), (9.5, 0.8, -7.0), 0.70), (12 * B, (3.0, 3.6, 3.5), (9.5, 0.8, -7.0), 0.70)])),
    # bar 3: gliding beside the second straight, Rondo recovering wide behind
    (12 * B, 16 * B, lambda t: (ks(t) + V(-7.5, 4.9, 4.5), ks(t) + V(4.5, 0.3, -3.1), 0.56)),
    # bar 4: corner 2 from outside, a little high
    (16 * B, 20 * B, _keys([(16 * B, (15.5, 5.2, 14.0), (6.4, -1.2, 5.2), 0.50), (20 * B, (13.5, 4.4, 15.8), (4.8, -1.2, 7.0), 0.50)])),
    # bar 5: gliding along the third straight, Rondo swinging wide in front of the corner-2 stands
    (20 * B, 24 * B, lambda t: (ks(t) + V(-4.6, 3.7, -3.45), ks(t) + V(1.4, 0.3, 1.8), 0.56)),
    # bar 6: from behind and above, down the last straight: two ways on the ground; the hesitation
    (24 * B, 28 * B, _keys([(24 * B, (-2.0, 11.0, 15.5), (-4.2, 0.0, 1.0), 0.70), (28 * B, (-2.2, 10.4, 14.4), (-4.4, 0.0, 0.2), 0.70)])),
    # bar 7: straight down from above - the footprints become the melody
    (28 * B, 32 * B, lambda t: (V(-5.6, 15.0, ks(t)[2] - 2.6), V(-6.0, 0.0, ks(t)[2] - 1.6), 0.55)),
    # bar 8: gliding behind the finish side, Rondo growing on the outside
    (32 * B, 36 * B, lambda t: (ks(t) + V(3.45, 3.7, -4.6), ks(t) + V(-2.0, 0.3, 3.0), 0.62)),
    # bar 9: photo finish from straight above
    (36 * B, 40 * B, _keys([(36 * B, (-7.3, 11.5, -8.6), (-7.3, 0.0, -7.6), 0.62), (40 * B, (-7.3, 11.5, -8.6), (-7.3, 0.0, -7.6), 0.62)])),
    # bar 10: cut on Kaku's last landing: the gold stand behind him, then TI in the foreground as the knot turns
    (40 * B, 44 * B, _keys([(40 * B, (-13.0, 3.6, 0.8), (-6.0, 3.4, -9.5), 0.80),
                            (42.0 * B, (-12.6, 1.2, -2.0), (-7.0, 1.0, -7.4), 0.50),
                            (44 * B, (-12.2, 1.1, -2.6), (-7.0, 1.0, -7.4), 0.46)])),
    # bar 11: tilt up to the scoreboard (same camera position as frame 0), then back down to frame 0
    (44 * B, 46.9 * B, _keys([(44 * B, A_POS, BOARD_LOOK, 0.19), (46.9 * B, A_POS, BOARD_LOOK, 0.19)])),
    (46.9 * B, 48 * B, _keys([(46.9 * B, A_POS, BOARD_LOOK, 0.19), (48 * B, A_POS, tuple(V(*A_POS) + 30.0 * A_DIR), A_FOV)])),
]


def camera(t):
    t = t % T.DURATION
    for t0, t1, f in SHOTS:
        if t0 <= t < t1 or t1 >= T.DURATION - 1e-9 and t0 <= t:
            pos, look, fov = f(t)
            break
    pos = np.array(pos, float)
    # a tiny heavy shake when Kaku lands close to the camera
    for tl, _, c1, _ in T.landings():
        dt = t - tl
        if 0 <= dt < 0.25:
            near = math.exp(-np.linalg.norm(c1 - pos) / 4.0)
            pos = pos + V(0.0, 1.0, 0.0) * (-0.02 * near * math.exp(-dt / 0.05) * math.cos(dt * 60))
    f = np.array(look, float) - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, V(0, 1, 0))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return pos, np.stack([r, u, f], axis=1), fov
