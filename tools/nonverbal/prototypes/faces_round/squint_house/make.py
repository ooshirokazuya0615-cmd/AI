#!/usr/bin/env python3
"""Squint House / 糸目の茶屋 -- ROUND-HEAD stick version.

One round-head face rig : RoundFace(D, **expression)  -> head SVG at (cx, cy)
One stick-body rig      : Body(D, light, ...)          -> neck stub, yoke, collar, spine, limbs,
                                                          mittens, tabi (all sizes in D)
The master is assembled by master(...) from a pose dict (D units, facing-right frame);
Hiko and the tea-house woman are assembled from the same Body + RoundFace parts.
scene.svg, poses.svg, lineup.svg and the silhouette sheets are all built from these.

Face system (unchanged from the original Squint House): no brows, no pupils. The eye is a
single wobbly brush stroke swapped from a library; the mouth is the main actor. The only
"open" eye is the empty shock circle. Head = true circle; breaks = white topknot, long-lobed
ear, nose tip, thin white chin beard.
"""
import math, random, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

INK = '#191621'
PLUM = '#3A2340'
PLUM_D = '#2B1931'
PLUM_L = '#54365A'
AMBER = '#F0B44C'
AMBER_D = '#C98A2E'
WOOD = '#8C5A3A'
WOOD_D = '#6E4429'
MOON = '#E9E4D4'
MATCHA = '#7A8F4E'
MATCHA_D = '#5E7038'
GI_COLLAR = '#5E6E3A'
VERM = '#C8452F'
EYEW = '#FBF6EA'
CREAM = '#F3EEE2'
BRASS = '#D2A44A'
TATAMI = '#6B7A3E'
TATAMI_D = '#4F5A33'
STRAW = '#C9A65A'
SKIN_M = '#A87452'
SKIN_H = '#E6B48E'
SKIN_W = '#C48A62'
HAIR_H = '#3A2A24'
LINEUP_BG = '#EDEAE4'

REG = {'limbs': []}
_uid = [0]


def uid():
    _uid[0] += 1
    return _uid[0]


def f1(v):
    return f'{v:.1f}'


def shade(c, k):
    c = c.lstrip('#')
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v * (1 - k))))) for v in (r, g, b))


# ---------------------------------------------------------------- geometry
class Noise:
    def __init__(self, seed, n=4):
        r = random.Random(seed)
        self.t = [(1.0 / (k + 1), (k + 1) * r.uniform(0.8, 1.3), r.uniform(0, 6.283)) for k in range(n)]
        self.s = sum(a for a, _, _ in self.t)

    def __call__(self, x):
        return sum(a * math.sin(f * x + p) for a, f, p in self.t) / self.s


def catmull(P, closed=False, n=10):
    out = []
    N = len(P)
    rng = range(N) if closed else range(N - 1)
    for i in rng:
        p0 = P[(i - 1) % N] if closed else P[max(i - 1, 0)]
        p1 = P[i]
        p2 = P[(i + 1) % N]
        p3 = P[(i + 2) % N] if closed else P[min(i + 2, N - 1)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(P[-1])
    return out


def qbez(p0, p1, p2, n=20):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


def ellipse(cx, cy, rx, ry, rot=0.0, n=72, a0=0.0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    pts = []
    for i in range(n):
        a = a0 + 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def resample(P, step=3.0, closed=False):
    Q = list(P) + ([P[0]] if closed else [])
    cum = [0.0]
    for i in range(1, len(Q)):
        cum.append(cum[-1] + math.dist(Q[i - 1], Q[i]))
    L = cum[-1] or 1e-6
    n = max(3, int(L / step) + 1)
    out, j = [], 0
    for k in range(n):
        s = L * k / (n if closed else n - 1)
        while j < len(cum) - 2 and cum[j + 1] < s:
            j += 1
        seg = (cum[j + 1] - cum[j]) or 1e-9
        t = (s - cum[j]) / seg
        out.append((Q[j][0] + (Q[j + 1][0] - Q[j][0]) * t, Q[j][1] + (Q[j + 1][1] - Q[j][1]) * t))
    return out, L


def normals(P, closed=False):
    N = len(P)
    out = []
    for i in range(N):
        if closed:
            a, b = P[(i - 1) % N], P[(i + 1) % N]
        else:
            a, b = P[max(i - 1, 0)], P[min(i + 1, N - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1e-9
        out.append((-ty / l, tx / l))
    return out


def d_of(P, closed=True):
    s = 'M' + ' L'.join(f'{f1(x)} {f1(y)}' for x, y in P)
    return s + (' Z' if closed else '')


def xform(P, dx=0, dy=0, rot=0, sx=1, sy=1, ox=0, oy=0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    out = []
    for x, y in P:
        x, y = (x - ox) * sx, (y - oy) * sy
        out.append((ox + x * c - y * s + dx, oy + x * s + y * c + dy))
    return out


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def pol(p, ang, L):
    a = math.radians(ang)
    return (p[0] + L * math.cos(a), p[1] + L * math.sin(a))


def ang_of(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def rot2(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay or 1e-9
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return math.dist(p, (a[0] + ax * t, a[1] + ay * t))


def poly_dist(p, P):
    return min(seg_dist(p, P[i], P[i + 1]) for i in range(len(P) - 1))


# ---------------------------------------------------------------- brushes
def brush(P, w, color=INK, taper=(0.22, 0.32), wmin=1.6, wob=1.1, seed=1, smooth=True, op=None):
    """Tapered brush stroke along centreline P -> filled polygon."""
    if smooth and len(P) > 2:
        P = catmull(P, n=8)
    P, L = resample(P, 2.5)
    nz, nw = Noise(seed), Noise(seed + 77)
    Nn = normals(P)
    left, right = [], []
    s = 0.0
    for i, (p, n) in enumerate(zip(P, Nn)):
        if i:
            s += math.dist(P[i - 1], p)
        t = s / L
        a = t / taper[0] if taper[0] > 0 else 1
        b = (1 - t) / taper[1] if taper[1] > 0 else 1
        fct = max(0.0, min(1.0, a, b))
        fct = math.sin(fct * math.pi / 2) ** 0.7
        ww = (wmin + (w - wmin) * fct) * (1 + 0.10 * nw(s / 22))
        off = wob * nz(s / 38)
        cx, cy = p[0] + n[0] * off, p[1] + n[1] * off
        left.append((cx + n[0] * ww / 2, cy + n[1] * ww / 2))
        right.append((cx - n[0] * ww / 2, cy - n[1] * ww / 2))
    o = f' opacity="{op}"' if op is not None else ''
    return f'<path d="{d_of(left + right[::-1])}" fill="{color}"{o}/>'


def taper_stroke(P, w0, w1, color=INK, seed=0, wob=1.0, smooth=True, op=None, caps=True):
    """Limb stroke: width w0 at the root -> w1 at the tip, wobbly brush edge, round caps."""
    if smooth and len(P) > 2:
        P = catmull(P, n=8)
    P, L = resample(P, 2.5)
    nz, nw = Noise(seed), Noise(seed + 77)
    Nn = normals(P)
    left, right = [], []
    s = 0.0
    ends = []
    for i, (p, n) in enumerate(zip(P, Nn)):
        if i:
            s += math.dist(P[i - 1], p)
        t = s / L
        ww = (w0 + (w1 - w0) * t) * (1 + 0.07 * nw(s / 24))
        off = wob * nz(s / 40)
        cx, cy = p[0] + n[0] * off, p[1] + n[1] * off
        if i == 0 or i == len(P) - 1:
            ends.append((cx, cy, ww / 2))
        left.append((cx + n[0] * ww / 2, cy + n[1] * ww / 2))
        right.append((cx - n[0] * ww / 2, cy - n[1] * ww / 2))
    o = f' opacity="{op}"' if op is not None else ''
    s = f'<path d="{d_of(left + right[::-1])}" fill="{color}"{o}/>'
    if caps:
        for cx, cy, r in ends:
            s += f'<circle cx="{f1(cx)}" cy="{f1(cy)}" r="{f1(r)}" fill="{color}"{o}/>'
    return s


def ring(P, wmin, wmax, color=INK, seed=3, wob=1.0, heavy=(0.6, 0.8), resamp=True):
    """Closed brush outline of polygon P with varying width (heavier toward `heavy`)."""
    if resamp:
        P, L = resample(P, 3.0, closed=True)
    Nn = normals(P, closed=True)
    area = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
    sgn = -1 if area > 0 else 1
    nz, nw = Noise(seed), Noise(seed + 31)
    hx, hy = heavy
    hl = math.hypot(hx, hy) or 1
    outer, inner = [], []
    s = 0.0
    for i, (p, n) in enumerate(zip(P, Nn)):
        if i:
            s += math.dist(P[i - 1], p)
        nx, ny = n[0] * sgn, n[1] * sgn
        dirdot = (nx * hx + ny * hy) / hl
        ww = wmin + (wmax - wmin) * (0.5 + 0.5 * dirdot)
        ww *= 1 + 0.12 * nw(s / 26)
        off = wob * nz(s / 45)
        px, py = p[0] + nx * off, p[1] + ny * off
        outer.append((px + nx * ww / 2, py + ny * ww / 2))
        inner.append((px - nx * ww / 2, py - ny * ww / 2))
    return f'<path d="{d_of(outer)} {d_of(inner[::-1])}" fill="{color}" fill-rule="evenodd"/>'


def filled(P, fill, wmin=10, wmax=14, seed=5, heavy=(0.6, 0.8), extra=''):
    return f'<path d="{d_of(P)}" fill="{fill}"{extra}/>' + ring(P, wmin, wmax, seed=seed, heavy=heavy)


def rimlit(P, fill, shift=(12, -3), col=AMBER):
    """Flat fill with a lantern-side amber rim (fill amber, then shifted fill clipped to P)."""
    cid = f'rl{uid()}'
    d = d_of(P)
    return (f'<clipPath id="{cid}"><path d="{d}"/></clipPath><path d="{d}" fill="{col}"/>'
            f'<g clip-path="url(#{cid})"><path d="{d}" fill="{fill}" transform="translate({f1(shift[0])} {f1(shift[1])})"/></g>')


def union(shapes, fill, wmin=18, wmax=26, seed=9, heavy=(0.6, 0.8)):
    out = [ring(P, wmin, wmax, seed=seed + i, heavy=heavy) for i, P in enumerate(shapes)]
    out += [f'<path d="{d_of(P)}" fill="{fill}"/>' for P in shapes]
    return ''.join(out)


def tube(P, w0, w1, cap=True):
    P = catmull(P, n=8) if len(P) > 2 else P
    P, L = resample(P, 4.0)
    Nn = normals(P)
    left, right = [], []
    s = 0.0
    for i, (p, n) in enumerate(zip(P, Nn)):
        if i:
            s += math.dist(P[i - 1], p)
        w = w0 + (w1 - w0) * s / L
        left.append((p[0] + n[0] * w / 2, p[1] + n[1] * w / 2))
        right.append((p[0] - n[0] * w / 2, p[1] - n[1] * w / 2))
    if cap:
        def arc(c, n, r, flip):
            a0 = math.atan2(n[1], n[0])
            return [(c[0] + r * math.cos(a0 + flip * math.pi * k / 8), c[1] + r * math.sin(a0 + flip * math.pi * k / 8)) for k in range(1, 8)]
        end = arc(P[-1], Nn[-1], w1 / 2, -1)
        start = arc(P[0], (-Nn[0][0], -Nn[0][1]), w0 / 2, -1)
        return left + end + right[::-1] + start
    return left + right[::-1]


def capsule(p0, p1, r):
    return tube([p0, p1], 2 * r, 2 * r)


def seg_pts(a, b, step=4.0):
    n = max(1, int(math.dist(a, b) / step))
    return [lerp(a, b, i / n) for i in range(1, n + 1)]


def joint_path(J, r=9):
    """Straight segments between joints, small round fillet at each inner joint."""
    out = [J[0]]
    for i in range(1, len(J) - 1):
        a, b, c = J[i - 1], J[i], J[i + 1]
        la, lc = math.dist(a, b) or 1, math.dist(b, c) or 1
        p1 = lerp(b, a, min(r, la * 0.3) / la)
        p2 = lerp(b, c, min(r, lc * 0.3) / lc)
        out += seg_pts(out[-1], p1)
        out += qbez(p1, b, p2, 6)[1:]
    out += seg_pts(out[-1], J[-1])
    return out


def ik(root, tgt, L1, L2, side=1, straight=False, minbend=7):
    d = math.dist(root, tgt)
    mb = 0.4 if straight else minbend
    dmax = math.sqrt(L1 * L1 + L2 * L2 + 2 * L1 * L2 * math.cos(math.radians(mb)))
    d = max(abs(L1 - L2) + 0.01 * (L1 + L2), min(d, dmax - 1e-4 * (L1 + L2)))
    a = math.atan2(tgt[1] - root[1], tgt[0] - root[0])
    cA = (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)
    A = math.acos(max(-1.0, min(1.0, cA)))
    e = (root[0] + L1 * math.cos(a + side * A), root[1] + L1 * math.sin(a + side * A))
    w = (root[0] + d * math.cos(a), root[1] + d * math.sin(a))
    return e, w


# =====================================================================
# ROUND FACE RIG
# =====================================================================
FACE_DEF = dict(
    skin=SKIN_M, skin_d=None, skin_dd=None, facing=1, rot=0.0, tilt=0.0, turn=0.10,
    eyes='flat', eye_len=0.26, eye_th=0.055, eye_sp=0.36, eye_y=-0.05, fore=0.86,
    mouth='flat', m_dx=0.0, m_dy=0.0, m_rot=0.0, mouth_y=0.22, m_th=0.058,
    hair='topknot', beard=None, ear='long', nose=True, nose_ang=8.0, nose_r=(0.085, 0.07),
    wrinkles=False, crows=False, cheekfolds=False, stubble=False,
    jaw=0.13, ring=(0.028, 0.038), rim=5.0, light=(-0.8, -0.6),
    circ_d=0.30, circ_sp=0.40, marks=(), mark_col=INK, seed=11, tails='back', knot_tips=True,
    tuft_scale=1.0,
)


class RoundFace:
    """Round-head rig. All geometry in head-local px: origin = skull centre, +x = facing side,
    y down. Group transform = translate(cx cy) rotate(rot) scale(facing 1)."""

    def __init__(self, D, **kw):
        self.D = D
        self.p = dict(FACE_DEF)
        self.p.update(kw)
        p = self.p
        if p['skin_d'] is None:
            p['skin_d'] = shade(p['skin'], 0.13)
        if p['skin_dd'] is None:
            p['skin_dd'] = shade(p['skin'], 0.28)

    # ---- helpers
    def light_local(self):
        p = self.p
        lx, ly = p['light']
        lx, ly = rot2((lx, ly), -p['rot'])
        lx *= p['facing']
        l = math.hypot(lx, ly) or 1
        return lx / l, ly / l

    def cluster(self):
        """Feature-cluster centre (px): turn + tilt cue (0.005 D per degree, down and forward)."""
        p, D = self.p, self.D
        return (p['turn'] + 0.005 * p['tilt']) * D, 0.005 * p['tilt'] * D

    def tilt_pt(self, x, y):
        return rot2((x, y), self.p['tilt'])

    def nose_bump(self):
        p, D = self.p, self.D
        R = D / 2
        a = p['nose_ang'] + 0.9 * p['tilt']
        rx, ry = p['nose_r']
        c = pol((0, 0), a, R * 0.975)
        return c, rx * D, ry * D, a

    def outline(self):
        D = self.D
        R = D / 2
        bumps = []
        if self.p['nose']:
            bumps.append(self.nose_bump())
        N = 240
        rs = []
        for i in range(N):
            th = 2 * math.pi * i / N
            ux, uy = math.cos(th), math.sin(th)
            r = R
            for (bc, rx, ry, rot) in bumps:
                c, s = math.cos(math.radians(-rot)), math.sin(math.radians(-rot))
                ox, oy = -bc[0], -bc[1]
                oxr, oyr = ox * c - oy * s, ox * s + oy * c
                uxr, uyr = ux * c - uy * s, ux * s + uy * c
                A = (uxr / rx) ** 2 + (uyr / ry) ** 2
                B = 2 * (oxr * uxr / rx ** 2 + oyr * uyr / ry ** 2)
                C = (oxr / rx) ** 2 + (oyr / ry) ** 2 - 1
                disc = B * B - 4 * A * C
                if disc > 0:
                    r = max(r, (-B + math.sqrt(disc)) / (2 * A))
            rs.append(r)
        k = 5
        wts = [math.exp(-(j / 2.4) ** 2) for j in range(-k, k + 1)]
        sm = []
        for i in range(N):
            v = sum(rs[(i + j) % N] * w for j, w in zip(range(-k, k + 1), wts)) / sum(wts)
            sm.append(max(rs[i], v))
        return [(sm[i] * math.cos(2 * math.pi * i / N), sm[i] * math.sin(2 * math.pi * i / N)) for i in range(N)]

    # ---- parts
    def skull(self, P):
        p, D = self.p, self.D
        d = d_of(P)
        cid = f'sk{uid()}'
        lx, ly = self.light_local()
        rw = (p['ring'][0] + p['ring'][1]) / 2 * D
        sh = p['rim'] + rw * 0.5
        s = [f'<clipPath id="{cid}"><path d="{d}"/></clipPath>']
        s.append(f'<path d="{d}" fill="{AMBER}"/>')
        s.append(f'<g clip-path="url(#{cid})"><path d="{d}" fill="{p["skin"]}" transform="translate({f1(-lx * sh)} {f1(-ly * sh)})"/>')
        # flat jaw-weight crescent on the lower disc (shadow side heavier); no gloss anywhere
        if p['jaw']:
            cx, cy = 0.07 * D * lx, -0.21 * D + p['jaw'] * 0.0
            e = ellipse(cx, cy, 0.63 * D, (0.71 - p['jaw']) * D, n=96)
            big = [(-D, -D), (D, -D), (D, D), (-D, D)]
            s.append(f'<path d="{d_of(big)} {d_of(e[::-1])}" fill="{p["skin_d"]}" fill-rule="evenodd"/>')
        s.append('</g>')
        return ''.join(s), cid

    def ear(self):
        p, D = self.p, self.D
        kind = p['ear']
        if not kind:
            return ''
        if kind == 'long':      # master: 0.14 x 0.26 D, lobe to 0.64 D from the top, 0.09 D past the rim
            loc = [(-0.47, -0.125), (-0.535, -0.13), (-0.585, -0.09), (-0.592, -0.01), (-0.585, 0.07), (-0.565, 0.13),
                   (-0.52, 0.145), (-0.475, 0.125), (-0.455, 0.06), (-0.452, -0.04)]
            c_mark = [(-0.515, -0.085), (-0.553, -0.035), (-0.548, 0.035), (-0.525, 0.07)]
        elif kind == 'std':     # Hiko: 0.11 x 0.19 D, 0.085 D past the rim
            loc = [(-0.465, -0.09), (-0.53, -0.10), (-0.578, -0.06), (-0.586, 0.01), (-0.57, 0.07), (-0.53, 0.10),
                   (-0.48, 0.09), (-0.46, 0.03), (-0.455, -0.04)]
            c_mark = [(-0.51, -0.06), (-0.548, -0.02), (-0.54, 0.035), (-0.515, 0.055)]
        else:                   # woman: small 0.10 x 0.16 D
            loc = [(-0.465, -0.06), (-0.525, -0.075), (-0.572, -0.035), (-0.575, 0.03), (-0.55, 0.085), (-0.50, 0.095),
                   (-0.465, 0.06), (-0.455, 0.0)]
            c_mark = [(-0.51, -0.035), (-0.542, 0.0), (-0.53, 0.05)]
        dy = p.get('ear_dy', 0.0)
        P = catmull([self.tilt_pt(x * D, (y + dy) * D) for x, y in loc], closed=True, n=6)
        lx, ly = self.light_local()
        rw = p['ring'][0] * D * 0.75
        s = rimlit(P, p['skin'], (-lx * (4 + rw / 2), -ly * (4 + rw / 2)))
        s += ring(P, rw * 0.8, rw * 1.1, seed=p['seed'] + 4, heavy=(-lx, -ly))
        s += brush([self.tilt_pt(x * D, (y + dy) * D) for x, y in c_mark], 0.022 * D, color=INK, seed=p['seed'] + 5, taper=(0.3, 0.5), wmin=1.5)
        return s

    def eye_one(self, kind, x, y, side, L, T):
        """side = -1 back eye, +1 front eye. 'inner' = toward the face centre."""
        p, D = self.p, self.D
        sd = p['seed'] + (3 if side > 0 else 7)
        inner = -side
        h = L / 2
        tl = p['tilt'] * 0.4
        def R(P):
            return xform(P, rot=tl, ox=x, oy=y)
        if kind == 'flat':
            return brush(R([(x - h, y + 0.004 * D), (x, y + 0.012 * D), (x + h, y + 0.004 * D)]), T, seed=sd, taper=(0.25, 0.3))
        if kind == 'slant':
            a = math.radians(30)
            dx, dy = h * math.cos(a), h * math.sin(a)
            return brush(R([(x - inner * dx, y - dy), (x + inner * dx, y + dy)]), T * 1.05, seed=sd, taper=(0.15, 0.3))
        if kind == 'u':
            return brush(R([(x - h, y - 0.03 * D), (x - h * 0.45, y + 0.025 * D), (x, y + 0.04 * D), (x + h * 0.45, y + 0.025 * D), (x + h, y - 0.03 * D)]), T, seed=sd)
        if kind == 'chev':
            ax = x + inner * h * 0.55
            o1 = (x - inner * h * 0.8, y - 0.075 * D)
            o2 = (x - inner * h * 0.8, y + 0.075 * D)
            s = brush(R([o1, lerp(o1, (ax, y), 0.5), (ax, y)]), T, seed=sd, taper=(0.35, 0.0), wmin=2, smooth=False)
            s += brush(R([(ax, y), lerp((ax, y), o2, 0.5), o2]), T, seed=sd + 1, taper=(0.0, 0.35), wmin=2, smooth=False)
            c = R([(ax, y)])[0]
            s += f'<circle cx="{f1(c[0])}" cy="{f1(c[1])}" r="{f1(T / 2)}" fill="{INK}"/>'
            return s
        if kind == 'wavy':
            pts = [(x - h + L * i / 24, y + 0.025 * D * math.sin(i / 24 * 2 * math.pi * 1.5)) for i in range(25)]
            return brush(R(pts), T, seed=sd)
        if kind == 'double':
            return (brush(R([(x - h, y - 0.04 * D), (x + h, y - 0.036 * D)]), T * 0.9, seed=sd) +
                    brush(R([(x - h + 4, y + 0.045 * D), (x + h - 2, y + 0.05 * D)]), T * 0.9, seed=sd + 2))
        if kind == 'sag':
            return brush(R([(x - h, y - 0.012 * D), (x - h * 0.4, y + 0.03 * D), (x + h * 0.35, y + 0.032 * D), (x + h, y - 0.004 * D)]), T, seed=sd, taper=(0.2, 0.3))
        if kind == 'circle':
            r = p['circ_d'] * D / 2 * (1.0 if side < 0 else 0.94)
            P = ellipse(x, y - 0.02 * D, r * (0.97 if side < 0 else 0.86), r, n=64)
            rw = 0.045 * D
            return f'<path d="{d_of(P)}" fill="{EYEW}"/>' + ring(P, rw * 0.85, rw * 1.15, seed=sd, heavy=(0.3, 0.9))
        return ''

    def eyes(self):
        p, D = self.p, self.D
        fx, fy = self.cluster()
        y = p['eye_y'] * D + fy
        L, T = p['eye_len'] * D, p['eye_th'] * D
        if p['eyes'] == 'circle':
            sp = p['circ_sp'] * D
            return (self.eye_one('circle', fx - sp * 0.5, y, -1, L, T) + self.eye_one('circle', fx + sp * 0.47, y, +1, L, T))
        sp = p['eye_sp'] * D
        return (self.eye_one(p['eyes'], fx - sp / 2, y, -1, L, T) +
                self.eye_one(p['eyes'], fx + sp / 2 * 0.94, y, +1, L * p['fore'], T))

    def age_marks(self):
        p, D = self.p, self.D
        fx, fy = self.cluster()
        c = p['skin_dd']
        s = ''
        if p['wrinkles']:   # three forehead brush arcs
            y0 = -0.30 * D + fy * 0.5
            for i, (w, dy) in enumerate(((0.30, 0.0), (0.24, 0.05), (0.16, 0.10))):
                x0 = fx - 0.03 * D
                pts = [(x0 - w / 2 * D, y0 + dy * D + 0.012 * D), (x0, y0 + dy * D - 0.01 * D), (x0 + w / 2 * D, y0 + dy * D + 0.012 * D)]
                s += brush(pts, 0.02 * D, color=c, seed=p['seed'] + 41 + i, taper=(0.3, 0.3), wmin=1.2)
        if p['crows'] and p['eyes'] != 'circle':   # crow's-foot ticks at the back eye's outer end
            ex = fx - p['eye_sp'] / 2 * D - p['eye_len'] / 2 * D - 0.03 * D
            ey = p['eye_y'] * D + fy
            for i, a in enumerate((-28, 0, 26)):
                q0 = pol((ex, ey), 180 + a, 0.0)
                q1 = pol((ex, ey), 180 + a, 0.07 * D)
                s += brush([q0, q1], 0.018 * D, color=c, seed=p['seed'] + 45 + i, taper=(0.1, 0.5), wmin=1.0)
        if p['cheekfolds']:   # two brush cheek folds on the lower third
            for i, (sx, sgn) in enumerate(((0.20, 1), (-0.20, -1))):
                x0 = fx + sx * D
                pts = [(x0, 0.10 * D + fy), (x0 + sgn * 0.035 * D, 0.20 * D + fy), (x0 + sgn * 0.02 * D, 0.30 * D + fy)]
                s += brush(pts, 0.022 * D, color=c, seed=p['seed'] + 48 + i, taper=(0.3, 0.4), wmin=1.2)
        return s

    def stubble_band(self, cid):
        p, D = self.p, self.D
        if not p['stubble']:
            return ''
        fx, fy = self.cluster()
        s = f'<g clip-path="url(#{cid})">'
        band = catmull([(-D, 0.20 * D), (-0.30 * D, 0.17 * D), (fx - 0.05 * D, 0.13 * D + fy), (fx + 0.30 * D, 0.12 * D + fy),
                        (D, 0.08 * D), (D, D), (-D, D)], closed=True, n=6)
        s += f'<path d="{d_of(band)}" fill="#7E6258" opacity="0.30"/>'
        r = random.Random(p['seed'] + 900)
        for _ in range(int(60 * (D / 240) ** 0.5)):
            x, y = r.uniform(-0.42 * D, 0.48 * D), r.uniform(0.20 * D, 0.47 * D)
            if x * x + y * y < (0.47 * D) ** 2:
                s += f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{f1(0.008 * D + 0.4)}" fill="#5E4540" opacity="0.7"/>'
        # sideburn in front of the ear
        sb = catmull([(-0.50 * D, -0.20 * D), (-0.40 * D, -0.20 * D), (-0.37 * D, -0.02 * D), (-0.40 * D, 0.10 * D), (-0.49 * D, 0.06 * D)], closed=True, n=6)
        s += f'<path d="{d_of(xform(sb, rot=p["tilt"]))}" fill="{HAIR_H}"/>'
        s += '</g>'
        return s

    def nose_mark(self):
        p, D = self.p, self.D
        if not p['nose']:
            return ''
        c, rx, ry, a = self.nose_bump()
        # the nostril wing: a short brush hook just inside the bump
        b = pol(c, a + 180, rx * 0.95)
        pts = [pol(b, a - 70, 0.05 * D), b, pol(b, a + 60, 0.05 * D)]
        return brush(pts, 0.022 * D, color=INK, seed=p['seed'] + 21, taper=(0.4, 0.4), wmin=1.5)

    def mouth(self):
        p, D = self.p, self.D
        k = p['mouth']
        fx, fy = self.cluster()
        x = fx + p['m_dx'] * D + 0.02 * D
        y = p['mouth_y'] * D + p['m_dy'] * D + fy
        T = p['m_th'] * D
        sd = p['seed'] + 13
        def R(P):
            return xform(P, rot=p['m_rot'] + p['tilt'] * 0.4, ox=x, oy=y)
        if k == 'flat':
            w = 0.23 * D
            return brush(R([(x - w / 2, y), (x, y + 0.008 * D), (x + w / 2, y + 0.004 * D)]), T, seed=sd, taper=(0.2, 0.25))
        if k == 'smallflat':
            w = 0.20 * D
            return brush(R([(x - w / 2, y), (x, y + 0.006 * D), (x + w / 2, y)]), T, seed=sd, taper=(0.2, 0.25))
        if k == 'dot':
            return f'<ellipse cx="{f1(x)}" cy="{f1(y)}" rx="{f1(0.045 * D)}" ry="{f1(0.04 * D)}" fill="{INK}"/>'
        if k == 'o':
            P = ellipse(x, y, 0.045 * D, 0.055 * D, n=40)
            return f'<path d="{d_of(P)}" fill="{INK}"/>' + ring(P, 0.02 * D, 0.026 * D, seed=sd)
        if k == 'grimace':
            mw, mh = 0.55 * D, 0.22 * D
            P = catmull(R([(x - mw / 2, y - mh / 2 + 4), (x, y - mh / 2), (x + mw / 2, y - mh / 2 + 4), (x + mw / 2 + 2, y + mh / 2 - 4),
                           (x, y + mh / 2), (x - mw / 2 - 2, y + mh / 2 - 4)]), closed=True, n=6)
            s = f'<path d="{d_of(P)}" fill="{CREAM}"/>'
            s += brush(R([(x - mw / 2 + 4, y + 1), (x, y + 3), (x + mw / 2 - 4, y + 1)]), 0.022 * D, seed=sd + 1, taper=(0.05, 0.05))
            for i in range(1, 5):
                tx = x - mw / 2 + mw * i / 5
                s += brush(R([(tx + 1, y - mh / 2 + 3), (tx, y + mh / 2 - 3)]), 0.022 * D, seed=sd + 2 + i, taper=(0.1, 0.1))
            s += ring(P, 0.035 * D, 0.045 * D, seed=sd)
            return s
        if k == 'grin':
            mw = 0.52 * D
            P = catmull(R([(x - mw / 2, y - 0.05 * D), (x, y - 0.02 * D), (x + mw / 2, y - 0.05 * D), (x + mw * 0.3, y + 0.11 * D),
                           (x, y + 0.16 * D), (x - mw * 0.3, y + 0.11 * D)]), closed=True, n=8)
            s = f'<path d="{d_of(P)}" fill="{INK}"/>'
            Tt = catmull(R([(x - mw / 2 + 0.05 * D, y - 0.04 * D), (x, y - 0.015 * D), (x + mw / 2 - 0.05 * D, y - 0.04 * D),
                            (x + mw * 0.3, y + 0.025 * D), (x - mw * 0.3, y + 0.025 * D)]), closed=True, n=6)
            s += f'<path d="{d_of(Tt)}" fill="{CREAM}"/>' + ring(P, 0.035 * D, 0.045 * D, seed=sd)
            return s
        if k == 'wavy':
            mw = 0.48 * D
            pts = [(x - mw / 2 + mw * i / 40, y + 0.035 * D * math.sin(i / 40 * 2 * math.pi * 2.5)) for i in range(41)]
            return brush(R(pts), T, seed=sd, taper=(0.12, 0.12))
        if k == 'smirk':
            mw = 0.27 * D
            s = brush(R([(x - mw / 2, y + 0.012 * D), (x - 0.01 * D, y + 0.018 * D), (x + mw / 2 - 0.03 * D, y - 0.008 * D),
                         (x + mw / 2 + 0.01 * D, y - 0.05 * D)]), T * 0.85, seed=sd, taper=(0.3, 0.3))
            s += brush(R([(x + mw / 2 + 0.045 * D, y - 0.095 * D), (x + mw / 2 + 0.06 * D, y - 0.045 * D)]), 0.022 * D, seed=sd + 3, taper=(0.3, 0.3))
            return s
        return ''

    def topknot(self):
        p, D = self.p, self.D
        R = D / 2
        a = -90 - 8 + p['tilt']
        base = pol((0, 0), a, R - 0.012 * D)
        up = (math.cos(math.radians(a)), math.sin(math.radians(a)))
        side = (-up[1], up[0])
        def W(u, v):
            return (base[0] + up[0] * u * D + side[0] * v * D, base[1] + up[1] * u * D + side[1] * v * D)
        bun = catmull([W(0.03, -0.065), W(0.09, -0.075), W(0.15, -0.045), W(0.165, 0.0), W(0.15, 0.045), W(0.09, 0.075), W(0.03, 0.065)], closed=True, n=8)
        lx, ly = self.light_local()
        s = rimlit(bun, CREAM, (-lx * 6, -ly * 6), col=AMBER)
        s += ring(bun, 0.016 * D, 0.022 * D, seed=p['seed'] + 51, heavy=(-lx, -ly))
        s += brush([W(0.11, -0.03), W(0.13, 0.0), W(0.115, 0.03)], 0.014 * D, color=INK, seed=p['seed'] + 52, taper=(0.3, 0.3))
        band = [W(-0.01, -0.05), W(0.045, -0.055), W(0.045, 0.055), W(-0.01, 0.05)]
        s += filled(band, INK, 0.008 * D, 0.01 * D, seed=p['seed'] + 53)
        return s

    def hiko_hair(self):
        """Dark cap above the headband + five swept-back clumped wedge tufts (0.20 D past the rim)."""
        p, D = self.p, self.D
        R = D / 2
        ts = p['tuft_scale']
        # outer profile from the front hairline (local angle -38) over the crown to the back (-205)
        prof = []
        a0, a1 = -36, -208
        n = 120
        tufts = [(-62, 0.12), (-92, 0.18), (-122, 0.20), (-152, 0.17), (-182, 0.12)]
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            r = R + 0.012 * D
            for (ta, th) in tufts:
                # clumped wedge swept back: long concave leading edge, short steep trailing edge
                da = (ta + 14) - a          # >0 in front of the tip (local angles run front -> back as they decrease)
                span_f, span_b = 34.0, 9.0
                if -span_b <= da <= span_f:
                    if da >= 0:
                        t = 1 - da / span_f
                        h = th * t ** 1.9
                    else:
                        t = 1 + da / span_b
                        h = th * t ** 0.6
                    r = max(r, R + h * D * ts)
            prof.append(pol((0, 0), a, r))
        # close inside the skull along the headband line (hidden under the band)
        yb = -0.20 * D
        inner = [(-0.62 * D, yb + 0.02 * D), (0.62 * D, yb - 0.02 * D)]
        P = xform(prof + inner[::-1] if False else prof + [(-0.55 * D, yb), (0.40 * D, yb)], rot=0)
        cid = f'hh{uid()}'
        lx, ly = self.light_local()
        s = rimlit(P, HAIR_H, (-lx * 6, -ly * 6), col=AMBER_D)
        s += ring(P, 0.026 * D, 0.036 * D, seed=p['seed'] + 81, heavy=(-lx, -ly))
        # two brush flick lines inside the hair for direction
        for i, a in enumerate((-80, -115)):
            q0 = pol((0, 0), a + 10, R * 0.75)
            q1 = pol((0, 0), a - 18, R * 1.02)
            s += brush([q0, q1], 0.016 * D, color='#5A463D', seed=p['seed'] + 85 + i, taper=(0.3, 0.6), wmin=1.2)
        return s

    def headband(self, cid):
        p, D = self.p, self.D
        y0, y1 = -0.255 * D, -0.155 * D
        W = D
        band = catmull([(-W, y0 + 0.02 * D), (0, y0 - 0.012 * D), (W, y0 + 0.01 * D), (W, y1 + 0.03 * D), (0, y1 - 0.006 * D), (-W, y1 + 0.04 * D)], closed=True, n=6)
        s = f'<g clip-path="url(#{cid})"><path d="{d_of(band)}" fill="{INK}"/>'
        s += brush([(-W * 0.5, y0 + 0.03 * D), (0, y0 + 0.015 * D), (W * 0.5, y0 + 0.025 * D)], 0.012 * D, color='#4A4054', seed=p['seed'] + 61) + '</g>'
        # band edge proud of the rim at the front and the back (it wraps the skull)
        for sx in (-1, 1):
            xx = sx * math.sqrt(max(0.0, (D / 2) ** 2 - ((y0 + y1) / 2) ** 2))
            P = ellipse(xx + sx * 0.008 * D, (y0 + y1) / 2 + 0.008 * D, 0.03 * D, 0.052 * D, n=24)
            s += f'<path d="{d_of(P)}" fill="{INK}"/>'
        kx, ky = -0.50 * D, (y0 + y1) / 2 + 0.01 * D
        s += f'<ellipse cx="{f1(kx)}" cy="{f1(ky)}" rx="{f1(0.06 * D)}" ry="{f1(0.052 * D)}" fill="{INK}"/>'
        if p['tails']:
            ta = p.get('tail_ang', 0.0)  # local extra angle (deg) for streaming
            for i, (dy, ln, wv) in enumerate(((-0.05, 0.62, 1.0), (0.05, 0.50, -1.0))):
                pts = []
                for k in range(9):
                    t = k / 8
                    xx = kx - ln * D * t
                    yy = ky + dy * D * t * 1.6 + 0.04 * D * wv * math.sin(t * math.pi * 1.6)
                    pts.append(rot2((xx - kx, yy - ky), ta))
                pts = [(kx + a, ky + b) for a, b in pts]
                s += brush(pts, 0.085 * D, seed=p['seed'] + 70 + i, taper=(0.0, 0.3), wmin=0.025 * D)
        return s

    def tenugui(self, cid):
        """Woman: cream tenugui over the crown with a knot and two short tips at the top-front."""
        p, D = self.p, self.D
        R = D / 2
        yl = -0.16 * D
        cap = []
        for i in range(61):
            a = -10 - 160 * i / 60
            cap.append(pol((0, 0), a, R + 0.022 * D))
        cap += [(-0.47 * D, yl + 0.08 * D), (-0.1 * D, yl + 0.02 * D), (0.35 * D, yl - 0.02 * D), (0.49 * D, yl - 0.06 * D)]
        lx, ly = self.light_local()
        s = rimlit(cap, CREAM, (-lx * 6, -ly * 6))
        s += ring(cap, 0.026 * D, 0.034 * D, seed=p['seed'] + 160, heavy=(-lx, -ly))
        for i, yy in enumerate((-0.33, -0.25)):
            s += brush([(-0.42 * D, yy * D + 0.03 * D), (0, yy * D - 0.01 * D), (0.40 * D, yy * D)], 0.016 * D, color=PLUM_L, seed=p['seed'] + 165 + i, taper=(0.1, 0.1))
        if p['knot_tips']:
            kb = pol((0, 0), -62, R + 0.01 * D)
            for i, (a, ln) in enumerate(((-104, 0.18), (-34, 0.16))):
                tip = pol(kb, a, ln * D)
                q = catmull([pol(kb, a - 90, 0.04 * D), lerp(pol(kb, a - 90, 0.04 * D), tip, 0.55), tip, lerp(pol(kb, a + 90, 0.04 * D), tip, 0.55), pol(kb, a + 90, 0.04 * D)], closed=True, n=5)
                s += filled(q, CREAM, 0.016 * D, 0.022 * D, seed=p['seed'] + 170 + i)
            s += filled(ellipse(kb[0], kb[1], 0.055 * D, 0.045 * D, rot=-60, n=24), CREAM, 0.016 * D, 0.02 * D, seed=p['seed'] + 175)
        return s

    def beard(self):
        p, D = self.p, self.D
        kind = p['beard']
        if not kind:
            return ''
        fx, fy = self.cluster()
        cx, cy = fx + 0.05 * D + p.get('beard_dx', 0) * D, 0.455 * D
        R = D / 2
        L = 0.35 * D
        out = []
        if kind == 'rest':
            spec = [(-0.055, 0.0, -0.01, 1.0, -0.03), (0.055, 0.0, 0.04, 0.95, 0.03), (0.0, 0.01, 0.02, 1.13, -0.01)]
        elif kind == 'flick':
            spec = [(-0.05, 0.0, -0.30, 0.55, -0.1), (0.05, 0.0, 0.32, 0.50, 0.1), (0.0, 0.01, 0.02, 1.0, -0.02)]
        else:  # forward
            spec = [(-0.05, 0.0, 0.16, 0.92, 0.02), (0.05, 0.0, 0.28, 0.80, 0.08), (0.0, 0.01, 0.23, 1.02, 0.04)]
        for i, (sx, sy, tx, ty, mx) in enumerate(spec):
            a = (cx + sx * D, cy + sy * D - 0.04 * D)
            tip = (cx + tx * D * (L / (0.35 * D)) * 1.0 + 0.0, R + (ty * L) - 0.0)
            tip = (cx + tx * D, R + ty * L)
            mid = ((a[0] + tip[0]) / 2 + mx * D, (a[1] + tip[1]) / 2)
            pts = catmull([a, mid, tip], n=10)
            out.append(brush(pts, 0.044 * D, color=INK, seed=p['seed'] + 90 + i, taper=(0.1, 0.8), wmin=0.014 * D, wob=0.5))
            out.append(brush(pts, 0.026 * D, color=CREAM, seed=p['seed'] + 90 + i, taper=(0.1, 0.8), wmin=0.004 * D, wob=0.5))
        # beard root: short cream ticks sitting on the chin (part of the jaw weight)
        for i, dx in enumerate((-0.06, 0.06)):
            q0 = (cx + dx * D, cy - 0.06 * D)
            q1 = (cx + dx * D * 1.1, cy + 0.0 * D)
            out.append(brush([q0, q1], 0.018 * D, color=CREAM, seed=p['seed'] + 95 + i, taper=(0.3, 0.3), wmin=1.0))
        return ''.join(out)

    def marks(self):
        p, D = self.p, self.D
        R = D / 2
        c = p['mark_col']
        out = []
        for m in p['marks']:
            kind = m[0]
            if kind == 'emanata_above':
                ca = m[1] if len(m) > 1 else 0
                for i, a in enumerate((ca - 22, ca, ca + 22)):
                    aa = a - 90
                    out.append(brush([pol((0, 0), aa, R + 0.20 * D), pol((0, 0), aa, R + 0.36 * D)], 0.04 * D, color=c, seed=p['seed'] + 100 + i, taper=(0.12, 0.25)))
            elif kind == 'emanata_side':
                side, ca = m[1], m[2]
                for i, a in enumerate((ca - 24, ca, ca + 24)):
                    aa = a if side > 0 else 180 - a
                    out.append(brush([pol((0, 0), aa, R + 0.17 * D), pol((0, 0), aa, R + 0.32 * D)], 0.038 * D, color=c, seed=p['seed'] + 110 + i, taper=(0.15, 0.3)))
            elif kind == 'sweat':
                sx, sy, sz, ang = m[1] * D, m[2] * D, m[3] * D, m[4]
                P = [(0, -sz * 1.25)] + [(sz * 0.62 * math.cos(t), sz * 0.15 + sz * 0.62 * math.sin(t)) for t in [math.radians(d) for d in range(-35, 216, 15)]]
                P = xform(P, dx=sx, dy=sy, rot=ang)
                out.append(filled(P, CREAM, 0.018 * D, 0.024 * D, seed=p['seed'] + 130))
        return ''.join(out)

    # ---- assembly
    def svg(self, cx, cy, parts=None):
        p, D = self.p, self.D
        P = self.outline()
        skull, cid = self.skull(P)
        lx, ly = self.light_local()
        s = [skull]
        s.append(self.stubble_band(cid))
        s.append(ring(P, p['ring'][0] * D, p['ring'][1] * D, seed=p['seed'], heavy=(-lx, -ly)))
        s.append(self.ear())
        if p['hair'] == 'hiko':
            s.append(self.hiko_hair())
            s.append(self.headband(cid))
        elif p['hair'] == 'tenugui':
            s.append(self.tenugui(cid))
        s.append(self.age_marks())
        s.append(self.nose_mark())
        s.append(self.eyes())
        s.append(self.mouth())
        if p['hair'] == 'topknot':
            s.append(self.topknot())
        s.append(self.beard())
        s.append(self.marks())
        T = f'translate({f1(cx)} {f1(cy)}) rotate({f1(p["rot"])}) scale({p["facing"]} 1)'
        return f'<g transform="{T}">{"".join(s)}</g>'

    def world(self, cx, cy, lp):
        """Map a head-local point (px) to world."""
        p = self.p
        x, y = lp[0] * p['facing'], lp[1]
        x, y = rot2((x, y), p['rot'])
        return (cx + x, cy + y)


# =====================================================================
# STICK BODY RIG
# =====================================================================
class Body:
    """Stick body parts in the Squint House line language: wobbly INK brush, fat at the root,
    thinner at the wrist, a full-width AMBER copy offset toward the lantern under every limb."""

    def __init__(self, D, light, skin=SKIN_M, ink=INK, seed=0, limb=(0.075, 0.050), spine=(0.08, 0.06),
                 rimd=5.0, tag='fig', minw=12.0):
        self.D, self.light, self.skin, self.ink, self.seed = D, light, skin, ink, seed
        self.lw = (max(minw, limb[0] * D), max(minw, limb[1] * D))
        self.sw = (max(minw + 2, spine[0] * D), max(minw, spine[1] * D))
        self.rimd = rimd
        self.tag = tag

    def rimv(self, pts, d=None):
        d = self.rimd if d is None else d
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        if self.light[0] == 'dir':
            dx, dy = self.light[1]
        else:
            dx, dy = self.light[0] - mx, self.light[1] - my
        l = math.hypot(dx, dy) or 1
        return (dx / l * d, dy / l * d)

    def limb(self, J, w0=None, w1=None, seed=0, rim=True, r=None, tag=None):
        w0 = w0 or self.lw[0]
        w1 = w1 or self.lw[1]
        P = joint_path(J, r or 0.04 * self.D)
        out = []
        if rim:
            rv = self.rimv(P)
            out.append(taper_stroke([(x + rv[0], y + rv[1]) for x, y in P], w0, w1, AMBER, seed=self.seed + seed, smooth=False))
        out.append(taper_stroke(P, w0, w1, self.ink, seed=self.seed + seed, smooth=False))
        REG['limbs'].append((tag or self.tag, J, (w0, w1)))
        return ''.join(out)

    def spine(self, pts, seed=0, rim=True):
        w0, w1 = self.sw
        out = []
        if rim:
            rv = self.rimv(pts)
            out.append(taper_stroke([(x + rv[0], y + rv[1]) for x, y in pts], w0, w1, AMBER, seed=self.seed + 900 + seed))
        out.append(taper_stroke(pts, w0, w1, self.ink, seed=self.seed + 900 + seed))
        REG['limbs'].append((self.tag + ':spine', pts[::4] + [pts[-1]], (w0, w1)))
        return ''.join(out)

    def neck(self, top, base, w=0.17, skin=None, chin_frac=0.42, vis_from=None):
        """Skin stub, wider than the spine stroke; flat 12%-darker chin shadow across its top."""
        D = self.D
        skin = skin or self.skin
        P = capsule(top, base, w * D / 2)
        s = f'<path d="{d_of(P)}" fill="{skin}"/>'
        a = ang_of(top, base)
        nx, ny = math.cos(math.radians(a + 90)), math.sin(math.radians(a + 90))
        # side brush edges
        for sg in (-1, 1):
            q0 = (top[0] + sg * nx * w * D / 2, top[1] + sg * ny * w * D / 2)
            q1 = (base[0] + sg * nx * w * D / 2, base[1] + sg * ny * w * D / 2)
            s += brush([q0, q1], 0.022 * D, color=self.ink, seed=self.seed + 950 + sg, taper=(0.0, 0.0), wmin=0.02 * D, smooth=False)
        # chin shadow band: from the hidden top down to (vis_from + chin_frac of the visible part)
        vf = vis_from if vis_from is not None else top
        cut = lerp(vf, base, chin_frac)
        Q = capsule(top, cut, w * D / 2 - 0.006 * D)
        s += f'<path d="{d_of(Q)}" fill="{shade(skin, 0.12)}"/>'
        return s

    def yoke(self, sh_n, nb, sh_f, seed=0):
        mid = (nb[0], nb[1] - 0.012 * self.D)
        P = [sh_n, lerp(sh_n, mid, 0.55), mid, lerp(mid, sh_f, 0.45), sh_f]
        w = self.lw[0] * 1.0
        out = []
        rv = self.rimv(P)
        out.append(taper_stroke([(x + rv[0], y + rv[1]) for x, y in P], w, w, AMBER, seed=self.seed + 960 + seed))
        out.append(taper_stroke(P, w, w, self.ink, seed=self.seed + 960 + seed))
        return ''.join(out)

    def mitten(self, wr, ang, L=0.20, W=0.13, skin=None, seed=0):
        D = self.D
        L, W = L * D, W * D
        loc = [(-0.04, -0.36), (0.22, -0.50), (0.60, -0.53), (0.90, -0.40), (1.0, 0), (0.90, 0.40), (0.60, 0.53), (0.22, 0.50), (-0.04, 0.36)]
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        P = catmull([(wr[0] + ux * u * L - uy * v * W, wr[1] + uy * u * L + ux * v * W) for u, v in loc], closed=True, n=6)
        rv = self.rimv(P, 4.0)
        return rimlit(P, skin or self.skin, (-rv[0], -rv[1])) + ring(P, 0.016 * D, 0.022 * D, seed=self.seed + 300 + seed, heavy=(-rv[0], -rv[1]))

    def hand_pt(self, wr, ang, u, v=0.0, L=0.20, W=0.13):
        D = self.D
        a = math.radians(ang)
        return (wr[0] + math.cos(a) * u * L * D - math.sin(a) * v * W * D, wr[1] + math.sin(a) * u * L * D + math.cos(a) * v * W * D)

    def thumb(self, base, ang, ln=0.065, r=0.032, seed=0, skin=None):
        D = self.D
        P = capsule(base, pol(base, ang, ln * D), r * D)
        return f'<path d="{d_of(P)}" fill="{skin or self.skin}"/>' + ring(P, 0.013 * D, 0.017 * D, seed=self.seed + 330 + seed)

    def tabi(self, an, ang, facing=1, seed=0, L=0.30):
        """Cream tabi, flat sole, split-toe seam, brush edge. ang = toe direction."""
        D = self.D
        L = L * D
        dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        ux, uy = facing * dy, -facing * dx
        def W(u, v):
            return (an[0] + dx * u * L + ux * v * L, an[1] + dy * u * L + uy * v * L)
        loc = [(-0.26, 0.0), (0.74, 0.0), (0.84, 0.07), (0.80, 0.19), (0.58, 0.27), (0.30, 0.32), (0.08, 0.44), (-0.18, 0.40), (-0.30, 0.17)]
        P = catmull([W(u, v) for u, v in loc], closed=True, n=6)
        rv = self.rimv(P, 3.5)
        s = rimlit(P, CREAM, (-rv[0], -rv[1])) + ring(P, 0.016 * D, 0.022 * D, seed=self.seed + 360 + seed)
        s += brush([W(0.58, 0.25), W(0.66, 0.12), W(0.68, 0.02)], 0.013 * D, seed=self.seed + 370 + seed, taper=(0.1, 0.3))
        return s


# ---------------------------------------------------------------- costume pieces
def eri(sh_n, nb, sh_f, D, cross=0.24, seed=0, col=CREAM):
    """Collar V: two cream brush strokes from each shoulder point down to a crossing below the neck base."""
    vb = (nb[0] + 0.03 * D * (1 if sh_f[0] > sh_n[0] else -1), nb[1] + cross * D)
    s = ''
    for k, (a, b) in enumerate(((sh_n, vb), (sh_f, (vb[0], vb[1] + 0.03 * D)))):
        ln = [a, lerp(a, b, 0.5), b]
        s += brush(ln, 0.075 * D + 7, color=INK, taper=(0.0, 0.28), wmin=0.03 * D + 5, seed=seed + k, wob=0.6)
        s += brush(ln, 0.075 * D, color=col, taper=(0.0, 0.28), wmin=0.03 * D, seed=seed + k, wob=0.6)
    return s


def obi(c, d_ang, D, facing=1, col=PLUM_L, seed=0, w=0.32, th=0.13, tails_swing=0.0, cord=CREAM, bow=True):
    """Obi wrapped round the waist (centre c, spine direction d_ang): a curved band 0.32 D wide,
    a flat butterfly bow standing off the back end, two short tails. Big enough never to read as a propeller."""
    a = d_ang - 90
    hw, hh = w * D / 2, th * D / 2
    def B(u, v):   # u across the body (px), v down the spine (px)
        q = pol(c, a, u)
        return pol(q, d_ang, v)
    band = []
    for i in range(13):
        u = -hw + 2 * hw * i / 12
        band.append(B(u, -hh - 0.012 * D * (1 - (u / hw) ** 2)))
    for i in range(13):
        u = hw - 2 * hw * i / 12
        band.append(B(u, hh + 0.022 * D * (1 - (u / hw) ** 2)))
    band = catmull(band, closed=True, n=3)
    back = -facing
    e1, e2 = B(-hw, 0), B(hw, 0)
    sgn = -1 if (e1[0] - c[0]) * back > 0 else 1      # u-sign of the back end
    sb, sf = '', ''
    if bow:
        kc = B(sgn * hw * 0.95, 0.0)
        bdir = ang_of(c, kc)
        t0 = pol(kc, d_ang, 0.03 * D)
        t2 = pol(pol(t0, d_ang, (0.17 + tails_swing) * D), bdir, 0.05 * D)
        t1 = pol(lerp(t0, t2, 0.5), bdir, 0.012 * D)
        sb += brush([t0, t1, t2], 0.075 * D + 7, color=INK, seed=seed + 6, taper=(0.0, 0.1), wmin=0.06 * D + 6, wob=0.4)
        sb += brush([t0, t1, t2], 0.075 * D, color=col, seed=seed + 6, taper=(0.0, 0.1), wmin=0.06 * D, wob=0.4)
        for k, sv in enumerate((-1, 1)):
            ax = bdir + sv * 38
            q0 = pol(kc, ax + 90, 0.03 * D)
            q1 = pol(pol(kc, ax, 0.15 * D), ax + 90, 0.05 * D)
            q2 = pol(kc, ax, 0.19 * D)
            q3 = pol(pol(kc, ax, 0.15 * D), ax - 90, 0.05 * D)
            q4 = pol(kc, ax - 90, 0.03 * D)
            lobe = catmull([q0, q1, q2, q3, q4], closed=True, n=8)
            sf += filled(lobe, col, 0.016 * D, 0.022 * D, seed=seed + 2 + k)
            sf += brush([pol(kc, ax, 0.05 * D), pol(kc, ax, 0.13 * D)], 0.016 * D, color=PLUM_D, seed=seed + 4 + k, taper=(0.2, 0.3))
    body = f'<path d="{d_of(band)}" fill="{col}"/>' + ring(band, 0.018 * D, 0.024 * D, seed=seed + 1)
    body += brush([B(-hw * 0.82, 0.004 * D), B(0, 0.012 * D), B(hw * 0.82, 0.004 * D)], 0.022 * D, color=cord, seed=seed + 9, taper=(0.05, 0.05))
    sf = body + sf
    if bow:
        kq = [pol(pol(kc, a, u * 0.04 * D), d_ang, v * 0.045 * D) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        sf += filled(catmull(kq, closed=True, n=4), col, 0.016 * D, 0.022 * D, seed=seed + 11)
    return sb, sf


def sash_tails(c, d_ang, D, col, trail_ang, seed=0, w=0.32, th=0.09):
    a = d_ang - 90
    hw, hh = w * D / 2, th * D / 2
    P = tube([pol(c, a, -hw), pol(c, a, hw)], 2 * hh, 2 * hh)
    back = ''
    for k, (ln, off) in enumerate(((0.62, 0.05), (0.48, -0.06))):
        p0 = c
        p1 = pol(pol(c, trail_ang, ln * D * 0.5), trail_ang + 90, (off + 0.05) * D)
        p2 = pol(pol(c, trail_ang, ln * D), trail_ang + 90, (off - 0.03) * D)
        back += brush([p0, p1, p2], 0.075 * D + 7, color=INK, seed=seed + k, taper=(0.0, 0.3), wmin=6)
        back += brush([p0, p1, p2], 0.075 * D, color=col, seed=seed + k, taper=(0.0, 0.3), wmin=2)
    front = f'<path d="{d_of(P)}" fill="{col}"/>' + ring(P, 0.018 * D, 0.024 * D, seed=seed + 5)
    return back, front


def collar_band(sh_n, nb, sh_f, D, col, seed=0, down=90.0):
    """Hiko's gi collar: a matcha band from each shoulder down (along the spine) into a V."""
    vb = pol(nb, down, 0.22 * D)
    s = ''
    for k, (a, b) in enumerate(((sh_n, vb), (sh_f, vb))):
        ln = [a, lerp(a, b, 0.5), b]
        s += brush(ln, 0.085 * D + 7, color=INK, taper=(0.0, 0.25), wmin=0.04 * D + 5, seed=seed + k, wob=0.6)
        s += brush(ln, 0.085 * D, color=col, taper=(0.0, 0.25), wmin=0.04 * D, seed=seed + k, wob=0.6)
    return s


# ---------------------------------------------------------------- props
def temari(bx, by, br, seed=500, bell_side=1):
    o = []
    ball = ellipse(bx, by, br, br, n=56)
    o.append(f'<path d="{d_of(ball)}" fill="{VERM}"/>')
    cid = f'tm{uid()}'
    o.append(f'<clipPath id="{cid}"><path d="{d_of(ball)}"/></clipPath><g clip-path="url(#{cid})">')
    for k in range(5):
        a0 = k * 72
        pts = []
        for i in range(13):
            t = i / 12
            a = math.radians(a0 + 110 * t)
            pts.append((bx + br * t * math.cos(a), by + br * t * math.sin(a)))
        o.append(brush(pts, br * 0.34, color=CREAM, taper=(0.35, 0.0), wmin=1.5, wob=0.3, seed=seed + k))
    o.append('</g>')
    o.append(f'<circle cx="{f1(bx)}" cy="{f1(by)}" r="{f1(br * 0.2)}" fill="{VERM}"/>')
    o.append(ring(ball, br * 0.17, br * 0.24, seed=seed + 9))
    bxx, byy = bx + bell_side * (br + br * 0.12), by + br * 0.55
    bell = ellipse(bxx, byy, br * 0.34, br * 0.31, n=30)
    o.append(filled(bell, BRASS, br * 0.12, br * 0.16, seed=seed + 11))
    o.append(brush([(bxx - br * 0.2, byy + br * 0.08), (bxx + br * 0.2, byy + br * 0.08)], br * 0.08, seed=seed + 12, taper=(0, 0)))
    return ''.join(o)


def star4(x, y, r, col=BRASS, seed=0):
    P = []
    for i in range(16):
        a = math.radians(i * 22.5 - 90)
        rr = r if i % 4 == 0 else (r * 0.42 if i % 2 == 0 else r * 0.36)
        P.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return filled(P, col, max(2.5, r * 0.22), max(3.0, r * 0.3), seed=seed)


def ting(x, y, s=1.0, seed=0, col=INK, base=-20):
    o = [star4(x, y, 15 * s, seed=seed)]
    for i, a in enumerate((-50, -15, 20)):
        p0 = pol((x, y), a + base, 22 * s)
        p1 = pol((x, y), a + base, 42 * s)
        o.append(brush([p0, p1], 6 * s, color=col, seed=seed + 3 + i, taper=(0.2, 0.3)))
    return ''.join(o)


def dotted(P, r0, r1, col=INK, gap=26):
    Q, L = resample(P, gap)
    out = []
    for i, q in enumerate(Q):
        t = i / max(1, len(Q) - 1)
        out.append(f'<circle cx="{f1(q[0])}" cy="{f1(q[1])}" r="{f1(r0 + (r1 - r0) * t)}" fill="{col}"/>')
    return ''.join(out)


def sensu(base, ang, ln, D, seed=0):
    """Closed folding fan: WOOD_D slat bundle widening to the tip, brush edge, plum paper edge, brass rivet."""
    wb, wt = 0.065 * D, 0.11 * D
    tip = pol(base, ang, ln)
    a = math.radians(ang)
    nx, ny = -math.sin(a), math.cos(a)
    P = [(base[0] + nx * wb / 2, base[1] + ny * wb / 2), (tip[0] + nx * wt / 2, tip[1] + ny * wt / 2),
         (tip[0] - nx * wt / 2, tip[1] - ny * wt / 2), (base[0] - nx * wb / 2, base[1] - ny * wb / 2)]
    s = filled(P, WOOD_D, 0.016 * D, 0.022 * D, seed=seed)
    for k in (-0.22, 0.18):
        s += brush([(base[0] + nx * wb * k, base[1] + ny * wb * k), (tip[0] + nx * wt * k * 1.3, tip[1] + ny * wt * k * 1.3)], 0.01 * D,
                   color=INK, seed=seed + 2, taper=(0.1, 0.1))
    tp = [(tip[0] + nx * wt / 2, tip[1] + ny * wt / 2), pol(tip, ang, 0.02 * D), (tip[0] - nx * wt / 2, tip[1] - ny * wt / 2)]
    s += brush(tp, 0.03 * D, color=PLUM_L, seed=seed + 4, taper=(0.1, 0.1))
    r = pol(base, ang, 0.03 * D)
    s += f'<circle cx="{f1(r[0])}" cy="{f1(r[1])}" r="{f1(0.022 * D)}" fill="{BRASS}"/>'
    return s, tip


def chawan(cx, top, D, seed=0, steam=True, tilt=0.0):
    """Matcha bowl 0.32 D wide, rim level."""
    w, h = 0.32 * D, 0.19 * D
    P = catmull([(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.44, top + h * 0.55), (cx + w * 0.26, top + h * 0.92),
                 (cx - w * 0.26, top + h * 0.92), (cx - w * 0.44, top + h * 0.55)], closed=True, n=6)
    P = xform(P, rot=tilt, ox=cx, oy=top + h / 2)
    s = filled(P, CREAM, 0.018 * D, 0.024 * D, seed=seed)
    e = ellipse(cx, top + 0.006 * D, w / 2 - 0.03 * D, 0.022 * D, n=30)
    s += f'<path d="{d_of(xform(e, rot=tilt, ox=cx, oy=top + h / 2))}" fill="{MATCHA}"/>'
    s += brush(xform([(cx - w * 0.42, top + h * 0.42), (cx + w * 0.42, top + h * 0.42)], rot=tilt, ox=cx, oy=top + h / 2), 0.02 * D, color=VERM, seed=seed + 1, taper=(0.1, 0.1))
    if steam:
        for i, dx in enumerate((-0.04, 0.045)):
            x0 = cx + dx * D
            pts = [(x0, top - 0.04 * D), (x0 + 0.035 * D, top - 0.11 * D), (x0 - 0.02 * D, top - 0.19 * D), (x0 + 0.02 * D, top - 0.27 * D)]
            s += brush(pts, 0.024 * D, color=CREAM, seed=seed + 5 + i, taper=(0.3, 0.6), op=0.8)
    return s


def broom(x, y0, y1, D, seed=0):
    hw = 0.022 * D
    s = filled([(x - hw, y0), (x + hw, y0), (x + hw * 1.1, y1), (x - hw * 1.1, y1)], BRASS, 0.016 * D, 0.02 * D, seed=seed)
    sw = 0.10 * D
    straw = catmull([(x - sw, y1 - 0.02 * D), (x + sw, y1 - 0.02 * D), (x + sw * 1.8, y1 + 0.42 * D), (x - sw * 1.8, y1 + 0.42 * D)], closed=True, n=4)
    s += filled(straw, STRAW, 0.022 * D, 0.03 * D, seed=seed + 1)
    for k in range(4):
        s += brush([(x - 0.06 * D + k * 0.04 * D, y1 + 0.04 * D), (x - 0.10 * D + k * 0.07 * D, y1 + 0.38 * D)], 0.014 * D, color='#8E6E2E', seed=seed + 2 + k, taper=(0.1, 0.3))
    s += brush([(x - sw * 1.1, y1 + 0.05 * D), (x + sw * 1.1, y1 + 0.05 * D)], 0.025 * D, color=VERM, seed=seed + 8, taper=(0, 0))
    return s


def swoosh(base, r, a0, a1, n=2, gap=16, w=6, col=PLUM_L, seed=0, op=0.8):
    out = []
    for i in range(n):
        rr = r - i * gap
        pts = [pol(base, a0 + (a1 - a0) * t / 12, rr) for t in range(13)]
        out.append(brush(pts, w, color=col, seed=seed + i, taper=(0.7, 0.1), wmin=1.5, op=op))
    return ''.join(out)


def emanata_at(x, y, ang, s=1.0, col=INK, seed=0, n=3, spread=26, r0=20, r1=46, w=7):
    out = []
    for i in range(n):
        a = ang + (i - (n - 1) / 2) * spread
        out.append(brush([pol((x, y), a, r0 * s), pol((x, y), a, r1 * s)], w * s, color=col, seed=seed + i, taper=(0.15, 0.3)))
    return ''.join(out)


def drop(x, y, sz, ang=0, col=MATCHA, seed=0):
    P = [(0, -sz * 1.25)] + [(sz * 0.62 * math.cos(t), sz * 0.15 + sz * 0.62 * math.sin(t)) for t in [math.radians(d) for d in range(-35, 216, 15)]]
    P = xform(P, dx=x, dy=y, rot=ang)
    return filled(P, col, max(2.5, sz * 0.25), max(3.0, sz * 0.32), seed=seed)


def ghost_ball(bx, by, br, op=0.55, col=CREAM):
    P = ellipse(bx, by, br, br, n=40)
    return f'<g opacity="{op}">' + ring(P, br * 0.14, br * 0.18, color=col, seed=777) + '</g>'


# =====================================================================
# THE MASTER (scene, sheet and lineup all use this)
# =====================================================================
class Frame:
    """Facing-right local frame, origin = head centre, units of D -> world."""

    def __init__(self, hc, D, facing):
        self.hc, self.D, self.f = hc, D, facing

    def w(self, p):
        return (self.hc[0] + self.f * p[0] * self.D, self.hc[1] + p[1] * self.D)

    def a(self, deg):
        return deg if self.f == 1 else 180 - deg


def master(hc, D, facing, face_kw, pose, light, seed=0, ring_w=(0.028, 0.038), want=None):
    """Old tea-house master. pose values are in D, facing-right frame, relative to the head centre.
    Returns dict(fig=..., props=..., marks=..., J=joints, ext=(top_y_hair, top_y_skull, sole_y))."""
    F = Frame(hc, D, facing)
    if light[0] == 'dir':
        lv = light[1]
    else:
        lv = (light[0] - hc[0], light[1] - hc[1])
    ll = math.hypot(*lv) or 1
    fk = dict(skin=SKIN_M, facing=facing, light=(lv[0] / ll, lv[1] / ll), hair='topknot', beard='rest', ear='long',
              wrinkles=True, crows=True, cheekfolds=True, ring=ring_w, seed=11 + seed)
    fk.update(face_kw)
    face = RoundFace(D, **fk)
    B = Body(D, light, skin=SKIN_M, seed=seed, tag='master')
    p = pose
    # ---- neck stub: axis 0.10 D behind centre, leaning forward (head rides ahead of the shoulders)
    lean = p.get('neck_lean', 12)
    vis = p.get('neck_vis', 0.13)
    tuck = 0.07
    nx0 = -0.10 + p.get('neck_dx', 0.0)
    top = (nx0, math.sqrt(0.25 - nx0 ** 2) - tuck)
    ldir = (-math.sin(math.radians(lean)), math.cos(math.radians(lean)))
    skull_y = math.sqrt(0.25 - nx0 ** 2)
    nb = (top[0] + ldir[0] * (tuck + vis), top[1] + ldir[1] * (tuck + vis))
    # ---- spine (C curve) neck base -> hip
    hip = p['hip']
    mid = lerp(nb, hip, 0.5)
    dsp = ang_of(nb, hip)
    ctrl = pol(mid, dsp + 90, p.get('bow', 0.10))   # +bow bulges toward the back (local -x)
    curve = qbez(nb, ctrl, hip, 30)
    # yoke: 0.07 D down the spine, shoulders +-0.26 D
    tan0 = ang_of(curve[0], curve[3])
    yk = pol(nb, tan0, p.get('yoke', 0.07))
    fwd = tan0 - 90
    sh_f = pol(yk, fwd, p.get('sh_f', 0.26))
    sh_n = pol(yk, fwd, -p.get('sh_n', 0.26))
    ua, fa = p.get('ua', 0.69), p.get('fa', 0.71)
    th, sn = p.get('th', 0.80), p.get('sn', 0.72)
    if 'arm_f' in p:
        p['wr_f'] = pol(sh_f, p['arm_f'][0], p['arm_f'][1]); p['straight_f'] = True
    if 'arm_n' in p:
        p['wr_n'] = pol(sh_n, p['arm_n'][0], p['arm_n'][1]); p['straight_n'] = True
    el_f, wr_f = ik(sh_f, p['wr_f'], ua, fa, p.get('el_f', 1), p.get('straight_f', False))
    el_n, wr_n = ik(sh_n, p['wr_n'], ua, fa, p.get('el_n', -1), p.get('straight_n', False))
    hip_n = pol(hip, fwd, -0.035)
    hip_f = pol(hip, fwd, 0.035)
    kn_f, an_f = ik(hip_f, p['an_f'], th, sn, p.get('kn_f', -1), p.get('straightleg_f', False))
    kn_n, an_n = ik(hip_n, p['an_n'], th, sn, p.get('kn_n', -1), p.get('straightleg_n', False))
    W = F.w
    J = dict(top=W(top), nb=W(nb), yk=W(yk), sh_f=W(sh_f), sh_n=W(sh_n), el_f=W(el_f), wr_f=W(wr_f), el_n=W(el_n), wr_n=W(wr_n),
             hip=W(hip), hip_f=W(hip_f), hip_n=W(hip_n), kn_f=W(kn_f), an_f=W(an_f), kn_n=W(kn_n), an_n=W(an_n),
             curve=[W(q) for q in curve], vis_from=W((top[0] + ldir[0] * tuck, top[1] + ldir[1] * tuck)))
    o = {k: '' for k in ('far_leg', 'far_arm', 'far_prop', 'spine', 'obi_b', 'near_leg', 'obi_f', 'neck', 'collar', 'head', 'near_arm', 'near_prop')}
    # legs
    o['far_leg'] = B.limb([J['hip_f'], J['kn_f'], J['an_f']], seed=1, tag='master:leg_f') + B.tabi(J['an_f'], F.a(p.get('toe_f', 0)), facing, seed=1)
    o['near_leg'] = B.limb([J['hip_n'], J['kn_n'], J['an_n']], seed=2, tag='master:leg_n') + B.tabi(J['an_n'], F.a(p.get('toe_n', 0)), facing, seed=2)
    # arms
    hf = F.a(p.get('hand_f', ang_of(el_f, wr_f)))
    hn = F.a(p.get('hand_n', ang_of(el_n, wr_n)))
    o['far_arm'] = B.limb([J['sh_f'], J['el_f'], J['wr_f']], seed=3, tag='master:arm_f') + B.mitten(J['wr_f'], hf, seed=3)
    o['near_arm'] = B.limb([J['sh_n'], J['el_n'], J['wr_n']], seed=5, tag='master:arm_n') + B.mitten(J['wr_n'], hn, seed=5)
    # spine + obi + neck + collar
    o['spine'] = B.spine(J['curve'], seed=4)
    oc = lerp(J['hip'], J['nb'], 0.07)
    ob, of = obi(oc, ang_of(J['nb'], J['hip']), D, facing=facing, seed=40 + seed, tails_swing=p.get('obi_swing', 0.0))
    o['obi_b'], o['obi_f'] = ob, of
    o['neck'] = B.neck(J['top'], J['nb'], w=0.17, vis_from=J['vis_from'])
    o['collar'] = B.yoke(J['sh_n'], J['nb'], J['sh_f']) + eri(J['sh_n'], J['nb'], J['sh_f'], D, seed=60 + seed)
    o['head'] = face.svg(hc[0], hc[1])
    info = dict(face=face)
    # props
    props = ''
    if p.get('fan') is not None:
        fb = B.hand_pt(J['wr_n'], hn, 0.55, 0.0)
        fs, tip = sensu(fb, F.a(p['fan']), 0.60 * D, D, seed=80 + seed)
        thumb_a = hn + (150 if facing == 1 else -150) * p.get('thumb_sign', 1)
        o['near_prop'] = fs + B.thumb(B.hand_pt(J['wr_n'], hn, 0.42, -0.42 * facing * p.get('thumb_sign', 1)), hn - 60 * facing * p.get('thumb_sign', 1), seed=7)
        info['fan_tip'], info['fan_base'] = tip, fb
    if p.get('fan_obi'):
        ocl = lerp(hip, nb, 0.07)
        fb = W((ocl[0] + 0.07, ocl[1] + 0.11))
        fs, tip = sensu(fb, F.a(-72), 0.60 * D, D, seed=80 + seed)
        o['obi_b'] = fs + o['obi_b']
    if p.get('bowl', True):
        hp = B.hand_pt(J['wr_f'], hf, 0.55, 0.0)
        top_y = hp[1] - 0.20 * D
        o['far_prop'] = chawan(hp[0], top_y, D, seed=90 + seed, steam=p.get('steam', True)) + \
            B.thumb(B.hand_pt(J['wr_f'], hf, 0.75, -0.5 * facing), F.a(-60), ln=0.06, seed=9)
        info['bowl'] = (hp[0], top_y)
    order = p.get('order', ('far_leg', 'far_arm', 'far_prop', 'spine', 'obi_b', 'near_leg', 'obi_f', 'neck', 'collar', 'head', 'near_arm', 'near_prop'))
    fig = ''.join(o[k] for k in order if k not in ('far_prop', 'near_prop'))
    full = ''.join(o[k] for k in order)
    # extents
    tk_top = hc[1] - (0.5 + 0.163) * D
    sole = max(J['an_f'][1], J['an_n'][1]) + 0.039 * D
    return dict(svg=full, fig=fig, J=J, info=info, ext=(tk_top, hc[1] - 0.5 * D, sole), face=face, body=B, F=F)


def clear_check(label, hc, D, pts_list, need=0.06):
    """Report the minimum distance from limb centrelines to the skull circle (in D, minus half limb)."""
    res = []
    for name, P, half in pts_list:
        dmin = min(math.dist(q, hc) for q in resample(P, 2.0)[0])
        res.append((name, (dmin - D / 2 - half) / D))
    print(label, ' '.join(f'{n}:{v:+.3f}D' for n, v in res))


# =====================================================================
# SCENE
# =====================================================================
LANTERN = (78, 372)


def scene_bg(o, W=1080, H=1920, figure_free=False):
    o.append(f'<rect width="{W}" height="{H}" fill="{PLUM}"/>')
    sx0, sx1, sy0, sy1 = 40, 1080, 262, 1180
    o.append(f'<rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}" fill="{MOON}"/>')
    # lantern glow on the paper (flat radial pool)
    o.append(f'<clipPath id="paper"><rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}"/></clipPath><g clip-path="url(#paper)">')
    for r, op in ((520, 0.10), (380, 0.12), (250, 0.16)):
        o.append(f'<circle cx="{LANTERN[0] + 60}" cy="{LANTERN[1] + 90}" r="{r}" fill="{AMBER}" opacity="{op}"/>')
    o.append('</g>')
    panels = 4
    pw = (sx1 - sx0) / panels
    for i in range(panels):
        x0 = sx0 + i * pw
        for c in range(1, 3):
            x = x0 + pw * c / 3
            o.append(f'<rect x="{f1(x - 3.5)}" y="{sy0}" width="7" height="{sy1 - sy0}" fill="{WOOD}"/>')
        for r in range(1, 5):
            y = sy0 + (sy1 - sy0) * r / 5
            o.append(f'<rect x="{f1(x0)}" y="{f1(y - 3.5)}" width="{f1(pw)}" height="7" fill="{WOOD}"/>')
        o.append(f'<rect x="{f1(x0 - 9)}" y="{sy0}" width="18" height="{sy1 - sy0}" fill="{WOOD}"/>')
    o.append(f'<rect x="{sx0 - 10}" y="{sy0 - 14}" width="{sx1 - sx0 + 20}" height="22" fill="{WOOD}"/>')
    o.append(f'<rect x="{sx0 - 10}" y="{sy1 - 6}" width="{sx1 - sx0 + 20}" height="20" fill="{WOOD}"/>')
    FLOOR = 1260
    o.append(f'<rect x="0" y="{sy1 + 14}" width="{W}" height="{FLOOR - sy1 - 14}" fill="#9C6B45"/>')
    o.append(f'<rect x="0" y="{FLOOR - 16}" width="{W}" height="16" fill="{WOOD_D}"/>')
    o.append(f'<rect x="0" y="230" width="{sx0}" height="{FLOOR - 230}" fill="{PLUM_D}"/>')
    o.append(f'<rect x="0" y="230" width="{W}" height="{sy0 - 14 - 230}" fill="{PLUM_D}"/>')
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="{1575 - FLOOR}" fill="{TATAMI}"/>')
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="10" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M0 1418 L{W} 1406 L{W} 1418 L0 1431 Z" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M640 {FLOOR} L652 {FLOOR} L700 1575 L686 1575 Z" fill="{TATAMI_D}"/>')
    o.append(f'<ellipse cx="250" cy="1470" rx="330" ry="80" fill="{AMBER}" opacity="0.10"/>')
    o.append(f'<rect x="0" y="0" width="{W}" height="230" fill="{PLUM}"/>')
    lx, ly = LANTERN
    o.append(brush([(lx, 230), (lx + 1, ly - 96)], 6, seed=301, taper=(0, 0)))
    lant = ellipse(lx, ly, 56, 80, n=60)
    o.append(filled(lant, AMBER, 7, 10, seed=302))
    for kk in (-50, -25, 0, 25, 50):
        hw = 56 * math.sqrt(max(0, 1 - (kk / 80) ** 2))
        o.append(brush([(lx - hw + 5, ly + kk), (lx, ly + kk + 7), (lx + hw - 5, ly + kk)], 3.5, color=AMBER_D, seed=310 + kk, taper=(0.2, 0.2)))
    o.append(filled([(lx - 32, ly - 94), (lx + 32, ly - 94), (lx + 36, ly - 74), (lx - 36, ly - 74)], INK, 4, 6, seed=303))
    o.append(filled([(lx - 32, ly + 74), (lx + 32, ly + 74), (lx + 29, ly + 92), (lx - 29, ly + 92)], INK, 4, 6, seed=304))
    # low table + plum teapot (lower left)
    o.append(filled([(-30, 1318), (138, 1318), (148, 1350), (-30, 1350)], WOOD, 7, 9, seed=320))
    o.append(filled([(100, 1350), (122, 1350), (122, 1440), (100, 1440)], WOOD_D, 6, 8, seed=321))
    pot = catmull([(10, 1318), (0, 1282), (28, 1252), (68, 1254), (86, 1284), (80, 1318)], closed=True, n=8)
    o.append(filled([(8, 1286), (-24, 1258), (-18, 1250), (12, 1270)], PLUM_L, 6, 8, seed=322))
    o.append(filled(pot, PLUM_L, 7, 9, seed=323))
    o.append(filled(ellipse(46, 1248, 16, 6, n=24), PLUM_L, 5, 6, seed=324))
    o.append(f'<circle cx="46" cy="1237" r="6" fill="{INK}"/>')
    o.append(brush([(20, 1282), (46, 1290), (72, 1282)], 4, color=BRASS, seed=325, taper=(0.1, 0.1)))
    o.append(f'<rect x="0" y="1575" width="{W}" height="{H - 1575}" fill="{TATAMI_D}"/>')


def master_scene_pose():
    return dict(
        hip=(-0.25, 1.70), bow=0.12, neck_lean=12, neck_vis=0.13,
        wr_f=(0.25, 1.08), el_f=1, hand_f=-12,          # far (front) hand: bowl level at chest height, close in
        wr_n=(-0.44, -0.46), el_n=-1, hand_n=-84,        # near (back) hand: fan up beside the head
        an_n=(-0.30, 3.04), kn_n=-1, toe_n=4,            # standing leg, soft knee
        an_f=(0.50, 1.70), kn_f=-1, toe_f=-28,           # front foot flicked up, instep at hip height, toe up
        fan=-80, bowl=True, steam=True,
    )


def hiko_scene(o, sil=False, Bc=(470.0, 640.0), a=166.0):
    """Hiko frozen mid-dive: both arms ring his head, mittens 0.3 D either side of the ball."""
    D = 240.0
    av = (math.cos(math.radians(a)), math.sin(math.radians(a)))
    pu = (-av[1], av[0])            # +v = av rotated +90 deg on screen
    if pu[1] > 0:
        raise ValueError('expected upper side')
    Y = (Bc[0] - 1.45 * D * av[0], Bc[1] - 1.45 * D * av[1])
    def U(u, v):
        return (Y[0] + u * D * av[0] + v * D * pu[0], Y[1] + u * D * av[1] + v * D * pu[1])
    HC = U(0.70, 0.0)
    NB = U(0.06, 0.0)
    NT = U(0.30, 0.0)
    light = LANTERN
    lv = (light[0] - HC[0], light[1] - HC[1])
    ll = math.hypot(*lv)
    att = math.degrees(math.atan2(0.14, 0.48))
    rot = (a - 180) - att
    face = RoundFace(D, skin=SKIN_H, facing=-1, rot=rot, light=(lv[0] / ll, lv[1] / ll), hair='hiko', beard=None, ear='std',
                     stubble=True, wrinkles=False, crows=False, cheekfolds=False, eyes='chev', mouth='wavy', turn=0.08,
                     eye_th=0.06, seed=31, nose_r=(0.07, 0.058), tails='back', tail_ang=14, jaw=0.0,
                     marks=(('sweat', 0.66, -0.46, 0.075, -25), ('sweat', 0.60, 0.30, 0.07, 15)), mark_col=INK)
    B = Body(D, light, skin=SKIN_H, seed=600, tag='hiko')
    sh_u, sh_l = U(0.0, 0.29), U(0.0, -0.29)
    ua, fa = 0.71 * D, 0.74 * D
    wu, wl = U(1.30, 0.63), U(1.30, -0.63)
    el_u, wr_u = ik(sh_u, wu, ua, fa, 1)
    el_l, wr_l = ik(sh_l, wl, ua, fa, -1)
    clear_check('hiko arms', HC, D, [('up_ua', [sh_u, el_u], B.lw[0] / 2), ('up_fa', [el_u, wr_u], B.lw[1] / 2),
                                     ('lo_ua', [sh_l, el_l], B.lw[0] / 2), ('lo_fa', [el_l, wr_l], B.lw[1] / 2)])
    hip = U(-0.97, 0.30)
    ctrl = U(-0.5, 0.06)
    curve = qbez(NB, ctrl, hip, 30)
    # legs tucked under (frozen pounce): knees down, tabi folded back up toward the corner
    hip_n, hip_f = hip, (hip[0] + 5, hip[1] - 3)
    # legs dangle (cartoon mid-air freeze): knees soft, feet trailing back
    kn_n = pol(hip_n, 104, 0.80 * D)
    an_n = pol(kn_n, 84, 0.72 * D)
    kn_f = pol(hip_f, 81, 0.80 * D)
    an_f = pol(kn_f, 74, 0.72 * D)
    parts = []
    if not sil:
        for i, (off, ln, du) in enumerate(((0.62, 260, -0.4), (-0.55, 230, -0.2), (1.05, 170, -0.9))):
            p0 = U(du - 0.2, off)
            parts.append(brush([p0, pol(p0, a + 180, ln)], 7, color=PLUM_L, seed=330 + i, taper=(0.0, 0.7), op=0.55))
    sb, sf = sash_tails(lerp(hip, NB, 0.06), ang_of(NB, hip), D, MATCHA_D, trail_ang=a + 180 - 28, seed=650)
    parts.append(B.limb([hip_f, kn_f, an_f], seed=1, tag='hiko:leg_f') + B.tabi(an_f, 112, -1, seed=1))
    mu_ang = ang_of(wr_u, U(1.47, 0.42))
    ml_ang = ang_of(wr_l, U(1.47, -0.42))
    parts.append(B.limb([sh_u, el_u, wr_u], seed=2, tag='hiko:arm_u'))
    parts.append(B.mitten(wr_u, mu_ang, seed=2))
    parts.append(B.spine(curve, seed=3))
    parts.append(sb)
    parts.append(B.limb([hip_n, kn_n, an_n], seed=4, tag='hiko:leg_n') + B.tabi(an_n, 122, -1, seed=4))
    parts.append(sf)
    parts.append(B.neck(NT, NB, w=0.17, vis_from=U(0.20, 0.0), chin_frac=0.5))
    parts.append(B.yoke(sh_u, NB, sh_l) + collar_band(sh_u, NB, sh_l, D, GI_COLLAR, seed=670, down=a + 180 + 8))
    parts.append(face.svg(HC[0], HC[1]))
    parts.append(B.limb([sh_l, el_l, wr_l], seed=5, tag='hiko:arm_l'))
    parts.append(B.mitten(wr_l, ml_ang, seed=5))
    tips = (B.hand_pt(wr_u, mu_ang, 1.0), B.hand_pt(wr_l, ml_ang, 1.0))
    br = 0.27 * 260 / 2
    gaps = [(math.dist(t, Bc) - br) / D for t in tips]
    print('hiko: HC=(%.0f,%.0f) rot=%.0f hip=(%.0f,%.0f) tabi=(%.0f,%.0f),(%.0f,%.0f) mitten gaps %.2fD %.2fD' % (
        HC[0], HC[1], rot, hip[0], hip[1], an_n[0], an_n[1], an_f[0], an_f[1], gaps[0], gaps[1]))
    info = dict(HC=HC, D=D, ball=Bc, tips=tips, Y=Y, av=av, pu=pu, U=U)
    return ''.join(parts), info


def woman_scene(o):
    D = 200.0
    HC = (880.0, 1168.0)
    light = LANTERN
    lv = (light[0] - HC[0], light[1] - HC[1])
    ll = math.hypot(*lv)
    face = RoundFace(D, skin=SKIN_W, facing=-1, light=(lv[0] / ll, lv[1] / ll), hair='tenugui', beard=None, ear='small',
                     eyes='sag', eye_th=0.066, eye_len=0.25, crows=True, mouth='smallflat', m_th=0.06, turn=0.10, tilt=6,
                     seed=51, nose_r=(0.07, 0.058), ear_dy=0.03, jaw=0.15)
    F = Frame(HC, D, -1)
    B = Body(D, light, skin=SKIN_W, seed=700, tag='woman')
    W = F.w
    top = W((-0.10, 0.42))
    nb = W((-0.13, 0.62))
    hip = W((-0.10, 1.70))
    curve = qbez(nb, W((-0.03, 1.15)), hip, 30)
    sh_f, sh_n = W((0.13, 0.70)), W((-0.39, 0.70))
    br_x = HC[0] - 0.66 * D
    el_n, wr_n = ik(sh_n, (br_x + 0.10 * D, HC[1] + 1.02 * D), 0.69 * D, 0.71 * D, 1)
    el_f, wr_f = ik(sh_f, W((0.58, 1.66)), 0.69 * D, 0.71 * D, 1)
    # seiza: thighs forward, shins folded back along the floor, tabi soles up behind
    kn, an = W((0.66, 1.90)), W((-0.22, 2.00))
    kn2, an2 = W((0.58, 1.86)), W((-0.32, 1.97))
    parts = []
    parts.append(f'<ellipse cx="{f1(HC[0] - 20)}" cy="{f1(HC[1] + 2.10 * D)}" rx="150" ry="13" fill="{INK}" opacity="0.30"/>')
    parts.append(broom(br_x, HC[1] - 0.95 * D, HC[1] + 1.70 * D, D, seed=760))
    parts.append(B.limb([hip, kn2, an2], seed=1, tag='woman:leg_f') + B.tabi(an2, F.a(196), -1, seed=1))
    parts.append(B.spine(curve, seed=3))
    parts.append(B.limb([hip, kn, an], seed=4, tag='woman:leg_n') + B.tabi(an, F.a(192), -1, seed=4))
    # white apron flag hanging from the waist over the lap (hip prop)
    ap = catmull([W((-0.02, 1.55)), W((0.26, 1.56)), W((0.34, 1.62)), W((0.30, 1.78)), W((0.04, 1.76)), W((-0.03, 1.66))], closed=True, n=6)
    parts.append(filled(ap, CREAM, 0.016 * D, 0.022 * D, seed=720))
    parts.append(brush([W((-0.16, 1.55)), W((0.30, 1.565))], 0.04 * D, color=PLUM_L, seed=721, taper=(0.1, 0.1)))
    parts.append(brush([W((-0.16, 1.55)), W((0.30, 1.565))], 0.012 * D, color=CREAM, seed=722, taper=(0.1, 0.1)))
    parts.append(B.limb([sh_f, el_f, wr_f], seed=2, tag='woman:arm_f') + B.mitten(wr_f, F.a(8), seed=2))
    parts.append(B.neck(top, nb, w=0.17, vis_from=W((-0.105, 0.49))))
    parts.append(B.yoke(sh_n, nb, sh_f) + eri(sh_n, nb, sh_f, D, seed=730))
    parts.append(face.svg(HC[0], HC[1]))
    parts.append(B.limb([sh_n, el_n, wr_n], seed=5, tag='woman:arm_n') + B.mitten(wr_n, -90, seed=5))
    parts.append(B.thumb(B.hand_pt(wr_n, -90, 0.45, 0.55), 180, seed=4))
    puff = [ellipse(HC[0] - 0.80 * D, HC[1] + 0.20 * D, 18, 15, n=24), ellipse(HC[0] - 0.92 * D, HC[1] + 0.12 * D, 15, 12, n=24),
            ellipse(HC[0] - 0.90 * D, HC[1] + 0.29 * D, 13, 11, n=24)]
    parts.append(union(puff, CREAM, 6, 8, seed=708))
    return ''.join(parts)


def scene_svg(bg_only=False):
    W, H = 1080, 1920
    REG['limbs'].clear()
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    scene_bg(o)
    if bg_only:
        o.append('</svg>')
        return '\n'.join(o)
    D = 260.0
    hc = (288.0, 752.0)
    stare = dict(eyes='circle', mouth='dot', tilt=-6, turn=0.12, beard='flick', mark_col=INK,
                 marks=(('emanata_above', -14),))
    m = master(hc, D, 1, stare, master_scene_pose(), LANTERN, seed=0)
    J = m['J']
    # woman first (she is further right/lower; no overlap)
    o.append(woman_scene(o))
    # ball story: motion ring at the instep, dotted rise, ball, ting
    br = 0.27 * D / 2
    # instep point of the flicked tabi (same geometry as Body.tabi)
    ta = math.radians(master_scene_pose()['toe_f'])
    dx, dy = math.cos(ta), math.sin(ta)
    ux, uy = dy, -dx
    Lt = 0.30 * D
    inst = (J['an_f'][0] + dx * 0.45 * Lt + ux * 0.33 * Lt, J['an_f'][1] + dy * 0.45 * Lt + uy * 0.33 * Lt)
    hs, hinfo = hiko_scene(o, Bc=(inst[0], 640.0))
    bx, by = hinfo['ball']
    o.append(f'<ellipse cx="{f1(m["J"]["hip"][0] + 30)}" cy="1566" rx="150" ry="14" fill="{INK}" opacity="0.32"/>')
    o.append(m['svg'])
    # pop: ghost ball just off the instep, motion ring, dotted line straight up
    gy = inst[1] - br - 6
    o.append(ghost_ball(bx, gy, br, op=0.55, col=INK))
    for i, r in enumerate((br + 16, br + 32)):
        o.append(swoosh((bx, gy), r, 205 + i * 12, 335 - i * 12, n=1, w=6 - i, col=INK, seed=530 + i, op=0.75))
    o.append(dotted([(bx, gy - br - 26), (bx, by + br + 24)], 3.5, 6.5, gap=30))
    print('scene: instep=(%.0f,%.0f) bowl=%s' % (inst[0], inst[1], m['info'].get('bowl')))
    o.append(hs)
    o.append(temari(bx, by, br, seed=500, bell_side=-1))
    o.append(ting(bx - br - 30, by - br - 10, 0.95, seed=540, base=-150))
    o.append('</svg>')
    return '\n'.join(o)


# =====================================================================
# POSES SHEET
# =====================================================================
def poses_svg(sil=False):
    W, H = 1080, 1080
    D = 200.0
    REG['limbs'].clear()
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    if sil:
        o.append(f'<defs><filter id="blk"><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></defs>')
        o.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
    else:
        o.append(f'<rect width="{W}" height="{H}" fill="{PLUM}"/>')
    FL = 990
    if not sil:
        for cx, cy in ((190, 520), (540, 470), (880, 470)):
            o.append(f'<circle cx="{cx}" cy="{cy}" r="190" fill="{AMBER}" opacity="0.12"/>')
            o.append(f'<circle cx="{cx}" cy="{cy}" r="132" fill="{AMBER}" opacity="0.12"/>')
        o.append(f'<rect x="0" y="{FL}" width="{W}" height="{H - FL}" fill="{TATAMI}"/>')
        o.append(f'<rect x="0" y="{FL}" width="{W}" height="8" fill="{TATAMI_D}"/>')
        o.append(f'<rect x="0" y="1046" width="{W}" height="8" fill="{TATAMI_D}"/>')
    figs = []
    # ---- (1) READY STANCE
    hc1 = (190.0, FL - 3.6 * D + 0.5 * D)
    neutral = dict(eyes='flat', mouth='flat', tilt=12, turn=0.10)
    p1 = dict(hip=(-0.24, 1.70), bow=0.12, wr_f=(0.62, 1.02), el_f=1, hand_f=-8,
              wr_n=(-0.62, 1.95), el_n=1, hand_n=-90, fan=-90,
              an_n=(-0.47, 3.04), kn_n=-1, toe_n=-8, an_f=(0.12, 3.04), kn_f=-1, toe_f=6, steam=True)
    m1 = master(hc1, D, 1, neutral, p1, (hc1[0] - 600, hc1[1] - 300), seed=0)
    figs.append(m1)
    # ---- (2) SIGNATURE: FAN FLICK + HEEL KICK (near arm straight overhead, 26 deg out)
    hc2 = (540.0, FL - 3.6 * D + 0.5 * D)
    smug = dict(eyes='u', mouth='smirk', tilt=-6, turn=0.10, beard='forward')
    shy = 0.69
    p2 = dict(hip=(-0.20, 1.70), bow=0.10, wr_f=(0.64, 1.02), el_f=1, hand_f=-8,
              arm_n=(-116, 1.40), el_n=-1, fan=-110, hand_n=-114,
              an_f=(-0.12, 3.04), kn_f=-1, toe_f=2,
              an_n=(-0.80, 2.30), kn_n=-1, toe_n=-150, obi_swing=0.04, steam=False)
    m2 = master(hc2, D, 1, smug, p2, (hc2[0] - 600, hc2[1] - 300), seed=10)
    figs.append(m2)
    # ---- (3) BIG REACTION: SHOCK HOP (Y arms 28 deg, feet 80 px up, knees tucked)
    hop = 80.0
    hc3 = (880.0, FL - hop - 2.80 * D)
    shock = dict(eyes='circle', mouth='o', tilt=0, turn=0.06, beard='flick', mark_col=CREAM,
                 marks=(('emanata_side', 1, -40), ('emanata_side', -1, -40)))
    p3 = dict(hip=(0.11, 1.66), bow=-0.04, neck_lean=-4, neck_dx=0.10, neck_vis=0.12, yoke=0.05, sh_f=0.25, sh_n=0.25,
              arm_f=(-63, 1.38), hand_f=-63, arm_n=(-117, 1.38), hand_n=-100, fan=-92, el_f=1, el_n=-1,
              an_f=(0.22, 2.66), kn_f=-1, toe_f=40, an_n=(-0.16, 2.74), kn_n=-1, toe_n=52, steam=False)
    m3 = master(hc3, D, -1, shock, p3, (hc3[0] - 600, hc3[1] - 300), seed=20)
    figs.append(m3)
    for k, m in enumerate(figs):
        if sil:
            o.append(f'<g filter="url(#blk)">{m["fig"]}</g>')
        else:
            sh = m['J']['an_n'][0]
            o.append(f'<ellipse cx="{f1((m["J"]["an_n"][0] + m["J"]["an_f"][0]) / 2)}" cy="{FL + 6}" rx="{110 if k < 2 else 80}" ry="9" fill="{INK}" opacity="0.4"/>')
            o.append(m['svg'])
    if not sil:
        # (1) temari resting on the fan tip
        ft = figs[0]['info']['fan_tip']
        br = 0.27 * D / 2
        o.append(temari(ft[0], ft[1] - br - 2, br, seed=560, bell_side=1))
        # (2) whip arc + ball popped 0.9 D above along a dotted arc + ting
        ft2 = figs[1]['info']['fan_tip']
        fb2 = figs[1]['info']['fan_base']
        o.append(swoosh(figs[1]['J']['sh_n'], 1.55 * D, -150, -112, n=2, gap=18, w=7, col=CREAM, seed=570, op=0.7))
        skull_top2 = hc2[1] - 0.5 * D
        bx2, by2 = hc2[0] - 0.02 * D, skull_top2 - 0.9 * D
        o.append(dotted(qbez((ft2[0] + 10, ft2[1] - 16), (ft2[0] + 30, by2 - 40), (bx2 - br - 14, by2 + 6), 24), 3, 5.5, col=CREAM, gap=24))
        o.append(temari(bx2, by2, br, seed=580, bell_side=1))
        o.append(ting(bx2 + br + 30, by2 + 4, 0.75, seed=590, col=CREAM))
        # (3) hop marks, tea droplet arcing back into the bowl, ball hanging above
        for i, dx in enumerate((-50, 0, 50)):
            o.append(brush([(hc3[0] + dx, FL - 14), (hc3[0] + dx, FL - 52)], 6, color=CREAM, seed=595 + i, taper=(0.2, 0.3), op=0.8))
        cpx, cpy = figs[2]['info']['bowl']
        o.append(dotted(qbez((cpx + 6, cpy - 10), (cpx + 30, cpy - 110), (cpx + 4, cpy - 28), 14), 2.4, 2.4, col=CREAM, gap=13))
        o.append(drop(cpx + 16, cpy - 74, 8.5, ang=180, seed=600))
        o.append(temari(hc3[0] + 10, 84, br, seed=610, bell_side=1))
    o.append('</svg>')
    for k, m in enumerate(figs):
        J = m['J']
        hc = (hc1, hc2, hc3)[k]
        clear_check(f'pose{k + 1}', hc, D, [('arm_n', [J['sh_n'], J['el_n'], J['wr_n']], 7), ('arm_f', [J['sh_f'], J['el_f'], J['wr_f']], 7)])
    return '\n'.join(o), figs


# =====================================================================
# LINEUP (540 x 1080, hero alone, 3/4 facing viewer's left, exactly 900 px tall incl. topknot)
# =====================================================================
def lineup_svg(sil=False):
    W, H = 540, 1080
    D0 = 240.0
    sole_y = 1010.0
    pose = dict(hip=(-0.22, 1.70), bow=0.11, wr_f=(0.62, 1.02), el_f=1, hand_f=-8,
                wr_n=(-0.40, 1.74), el_n=1, hand_n=20, fan=None, fan_obi=True,
                order=('far_leg', 'far_arm', 'far_prop', 'near_arm', 'spine', 'obi_b', 'near_leg', 'obi_f', 'neck', 'collar', 'head', 'near_prop'),
                an_n=(-0.50, 3.04), kn_n=-1, toe_n=-6, an_f=(0.14, 3.04), kn_f=-1, toe_f=8, steam=True)
    face = dict(eyes='flat', mouth='smirk', tilt=8, turn=0.10)
    hc = (286.0, 0.0)
    m = master(hc, D0, -1, face, pose, ('dir', (-0.6, -0.8)), seed=0)
    top, skull_top, sole = m['ext']
    k = 900.0 / (sole - top)
    # translate/scale so that sole -> 1010 and topknot top -> 110
    ty = sole_y - sole * k
    cxw = 286.0
    T = f'translate({f1(cxw - hc[0] * k)} {f1(ty)}) scale({k:.5f})'
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    if sil:
        o.append(f'<defs><filter id="blk"><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></defs>')
        o.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/><g transform="{T}" filter="url(#blk)">{m["fig"]}</g>')
    else:
        o.append(f'<rect width="{W}" height="{H}" fill="{LINEUP_BG}"/>')
        o.append(f'<ellipse cx="{f1(cxw)}" cy="{sole_y + 4}" rx="180" ry="12" fill="{INK}" opacity="0.18"/>')
        o.append(f'<g transform="{T}">{m["svg"]}</g>')
    o.append('</svg>')
    print(f'lineup: D_eff={D0 * k:.1f}px  top={top * k + ty:.1f}  skull_top={skull_top * k + ty:.1f}  sole={sole * k + ty:.1f}  H_skull/D={(sole - skull_top) / D0:.2f}')
    return '\n'.join(o)


if __name__ == '__main__':
    sc = scene_svg()
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(sc)
    with open(os.path.join(HERE, 'scene_bg.svg'), 'w') as fh:
        fh.write(scene_svg(bg_only=True))
    ps, figs = poses_svg()
    with open(os.path.join(HERE, 'poses.svg'), 'w') as fh:
        fh.write(ps)
    with open(os.path.join(HERE, 'poses_sil.svg'), 'w') as fh:
        fh.write(poses_svg(sil=True)[0])
    with open(os.path.join(HERE, 'lineup.svg'), 'w') as fh:
        fh.write(lineup_svg())
    with open(os.path.join(HERE, 'lineup_sil.svg'), 'w') as fh:
        fh.write(lineup_svg(sil=True))
    print('ok')
