#!/usr/bin/env python3
"""Squint House / 糸目の茶屋 -- one face rig, two images.

The rig (Face) draws a tall-bean head from parameters:
  head shape + tilt + facing + feature turn, eye-stroke swap library,
  mouth swap library, hair (topknot / headband), beard, ear, marks.
There are no brows and no pupils by design: the angle of the eye stroke
does the brow's job, and the only "open" eye is the empty shock circle.
scene.svg and faces.svg are both built from this same rig.
"""
import math, random, os

HERE = os.path.dirname(os.path.abspath(__file__))

INK = '#191621'
PLUM = '#3A2340'
PLUM_D = '#2B1931'
PLUM_L = '#54365A'
AMBER = '#F0B44C'
WOOD = '#8C5A3A'
WOOD_D = '#6E4429'
MOON = '#E9E4D4'
MATCHA = '#7A8F4E'
MATCHA_D = '#5E7038'
VERM = '#C8452F'
EYEW = '#FBF6EA'
CREAM = '#F3EEE2'
BRASS = '#D2A44A'
TATAMI = '#66763F'
TATAMI_D = '#4F5A33'
SKIN_M = '#A87452'
SKIN_M_D = '#8A5C3E'
SKIN_H = '#E6B48E'
SKIN_H_D = '#C99470'

_uid = [0]


def uid():
    _uid[0] += 1
    return _uid[0]


def f1(v):
    return f'{v:.1f}'


# ---------------------------------------------------------------- geometry
class Noise:
    """Smooth 1-D noise (sum of sines) used for the brush 'boil'."""

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
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(P[-1])
    return out


def qbez(p0, p1, p2, n=20):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


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
    count = n if closed else n
    for k in range(count):
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


def ring(P, wmin, wmax, color=INK, seed=3, wob=1.0, heavy=(0.6, 0.8), resamp=True):
    """Closed brush outline of polygon P with varying width (heavier toward `heavy` dir)."""
    if resamp:
        P, L = resample(P, 3.0, closed=True)
    Nn = normals(P, closed=True)
    # ensure outward normals: polygon orientation
    area = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))
    sgn = -1 if area > 0 else 1
    cx = sum(p[0] for p in P) / len(P)
    cy = sum(p[1] for p in P) / len(P)
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
            f'<g clip-path="url(#{cid})"><path d="{d}" fill="{fill}" transform="translate({shift[0]} {shift[1]})"/></g>')


def union(shapes, fill, wmin=18, wmax=26, seed=9, heavy=(0.6, 0.8)):
    """Several shapes merged under one outline: rings first, fills on top."""
    out = [ring(P, wmin, wmax, seed=seed + i, heavy=heavy) for i, P in enumerate(shapes)]
    out += [f'<path d="{d_of(P)}" fill="{fill}"/>' for P in shapes]
    return ''.join(out)


def tube(P, w0, w1, cap=True):
    """Closed polygon of a thick tapering limb along centreline P."""
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


# ---------------------------------------------------------------- face rig
BEAN = [(0.02, -0.50), (0.27, -0.46), (0.44, -0.30), (0.50, -0.06), (0.47, 0.18), (0.36, 0.38),
        (0.14, 0.495), (-0.12, 0.48), (-0.30, 0.38), (-0.36, 0.22), (-0.40, 0.06), (-0.48, -0.14),
        (-0.42, -0.36), (-0.22, -0.48)]


def bean_pts(W, H):
    return catmull([(x * W, y * H) for x, y in BEAN], closed=True, n=10)


DEFAULT = dict(
    W=220, H=350, skin=SKIN_M, skin_d=SKIN_M_D, tilt=12, facing=1, lift=0, turn=10, fdy=0,
    eyes='flat', eye_dx=0, eye_sp=92, eye_len=66, eye_th=14, eye_y=-0.06,
    mouth='flat', m_w=60, m_dx=0, m_dy=0, m_rot=0, m_y=0.215,
    hair='topknot', beard='rest', ear=True, wrinkles=True, nose=True,
    rim=6, rim_col=AMBER, marks=(), mark_col=MOON, ghost=False, seed=11,
    outline=(10, 14),
)


class Face:
    def __init__(self, **kw):
        self.p = dict(DEFAULT)
        self.p.update(kw)

    # -- parts (all in head-local coords; +x = toward the face side)
    def head_shape(self):
        p = self.p
        return bean_pts(p['W'], p['H'])

    def ear(self):
        p = self.p
        W, H = p['W'], p['H']
        ex, ey = -0.40 * W, 0.10 * H
        P = catmull([(ex + 10, ey - 52), (ex - 16, ey - 46), (ex - 26, ey - 10), (ex - 22, ey + 30), (ex - 26, ey + 58),
                     (ex - 8, ey + 76), (ex + 12, ey + 60), (ex + 14, ey + 20)], closed=True, n=8)
        s = filled(P, p['skin'], 8, 11, seed=p['seed'] + 4, heavy=(-0.4, 0.9))
        s += brush([(ex - 2, ey - 30), (ex - 12, ey - 8), (ex - 8, ey + 22)], 6, color=INK, seed=p['seed'] + 5, taper=(0.3, 0.5))
        return s

    def eye_one(self, kind, x, y, side):
        """side = -1 back eye, +1 front eye. 'inner' end points toward the face centre."""
        p = self.p
        L, T, sd = p['eye_len'], p['eye_th'], p['seed'] + (3 if side > 0 else 7)
        inner = -side  # direction (x) of the inner end
        h = L / 2
        if kind == 'flat':
            return brush([(x - h, y + 1), (x, y + 3), (x + h, y + 1)], T, seed=sd)
        if kind == 'slant':
            a = math.radians(30)
            dx, dy = h * math.cos(a), h * math.sin(a)
            # inner end low
            p_in = (x + inner * dx, y + dy)
            p_out = (x - inner * dx, y - dy)
            return brush([p_out, p_in], T + 1, seed=sd, taper=(0.15, 0.3))
        if kind == 'u':
            return brush([(x - h, y - 8), (x - h * 0.45, y + 8), (x, y + 12), (x + h * 0.45, y + 8), (x + h, y - 8)], T, seed=sd)
        if kind == 'chev':
            ax = x + inner * h * 0.55
            o1 = (x - inner * h * 0.75, y - 22)
            o2 = (x - inner * h * 0.75, y + 22)
            s = brush([o1, ((o1[0] + ax) / 2, y - 11), (ax, y)], T, seed=sd, taper=(0.35, 0.0), wmin=2, smooth=False)
            s += brush([(ax, y), ((o2[0] + ax) / 2, y + 11), o2], T, seed=sd + 1, taper=(0.0, 0.35), wmin=2, smooth=False)
            s += f'<circle cx="{f1(ax)}" cy="{f1(y)}" r="{f1(T / 2)}" fill="{INK}"/>'
            return s
        if kind == 'wavy':
            pts = [(x - h + L * i / 24, y + 7 * math.sin(i / 24 * 2 * math.pi * 1.5)) for i in range(25)]
            return brush(pts, T, seed=sd)
        if kind == 'double':
            return (brush([(x - h, y - 11), (x + h, y - 10)], T, seed=sd) +
                    brush([(x - h + 4, y + 13), (x + h - 2, y + 14)], T, seed=sd + 2))
        if kind == 'sag':  # witness: ︶ sleepy-sag
            return brush([(x - h, y - 4), (x, y + 8), (x + h, y - 4)], T, seed=sd)
        if kind == 'circle':
            r = p.get('circ_r', 48) * (1.06 if side > 0 else 0.94)
            yy = y - (5 if side > 0 else 0) - r * 0.12
            P = ellipse(x, yy, r * 0.92, r * 1.12, rot=side * 6, n=64)
            return f'<path d="{d_of(P)}" fill="{EYEW}"/>' + ring(P, 8, 17, seed=sd, heavy=(-side * 0.5, 0.9))
        return ''

    def eyes(self):
        p = self.p
        fc = p['turn'] + p['eye_dx']
        y = p['eye_y'] * p['H'] + p['fdy']
        sp = p.get('circ_sp', p['eye_sp']) if p['eyes'] == 'circle' else p['eye_sp']
        return self.eye_one(p['eyes'], fc - sp / 2, y, -1) + self.eye_one(p['eyes'], fc + sp / 2, y, +1)

    def lids(self):
        return ''  # this design has no lids: the eye *is* a single stroke

    def pupils(self):
        return ''  # no pupils, ever (even the shock circles stay empty)

    def brows(self):
        return ''  # no brows: eye-stroke angle does the job

    def nose(self):
        p = self.p
        if not p['nose']:
            return ''
        x = p['turn'] + 18 + p.get('nose_dx', 0)
        y = (0.115 if p['eyes'] == 'circle' else 0.07) * p['H'] + p['fdy']
        return brush([(x - 2, y - 18), (x + 12, y + 4), (x - 4, y + 10)], 8, seed=p['seed'] + 21, taper=(0.4, 0.4), color=INK)

    def wrinkles(self):
        p = self.p
        if not p['wrinkles']:
            return ''
        x = p['turn'] + p['eye_dx'] * 0.5
        y = -0.27 * p['H'] + p['fdy'] * 0.6
        c = p['skin_d']
        return (brush([(x - 34, y + 2), (x - 6, y - 3), (x + 22, y + 2)], 5, color=c, seed=p['seed'] + 41) +
                brush([(x - 22, y + 18), (x + 2, y + 14), (x + 26, y + 18)], 5, color=c, seed=p['seed'] + 42))

    def mouth(self):
        p = self.p
        k = p['mouth']
        x = p['turn'] + p['m_dx']
        y = p['m_y'] * p['H'] + p['m_dy'] + p['fdy']
        w = p['m_w']
        sd = p['seed'] + 13
        rot = p['m_rot']
        def R(P):
            return xform(P, rot=rot, ox=x, oy=y)
        if k == 'flat':
            return brush(R([(x - w / 2, y), (x, y + 2), (x + w / 2, y + 1)]), 14.5, seed=sd)
        if k == 'dot':
            return f'<ellipse cx="{f1(x)}" cy="{f1(y)}" rx="8.5" ry="8" fill="{INK}"/>'
        if k == 'o':
            P = ellipse(x, y, 12, 14, n=40)
            return f'<path d="{d_of(P)}" fill="{INK}"/>' + ring(P, 6, 8, seed=sd)
        if k == 'grimace':
            mw, mh = 150, 60
            P = catmull([(x - mw / 2, y - mh / 2 + 4), (x, y - mh / 2), (x + mw / 2, y - mh / 2 + 4), (x + mw / 2 + 2, y + mh / 2 - 4),
                         (x, y + mh / 2), (x - mw / 2 - 2, y + mh / 2 - 4)], closed=True, n=6)
            s = f'<path d="{d_of(P)}" fill="{CREAM}"/>'
            s += brush([(x - mw / 2 + 4, y + 1), (x, y + 3), (x + mw / 2 - 4, y + 1)], 6, seed=sd + 1, taper=(0.05, 0.05))
            for i in range(1, 5):
                tx = x - mw / 2 + mw * i / 5
                s += brush([(tx + 1, y - mh / 2 + 3), (tx, y + mh / 2 - 3)], 6, seed=sd + 2 + i, taper=(0.1, 0.1))
            s += ring(P, 11, 15, seed=sd)
            return s
        if k == 'grin':
            mw = w if w > 100 else 140
            P = catmull([(x - mw / 2, y - 14), (x, y - 6), (x + mw / 2, y - 14), (x + mw * 0.3, y + 30), (x, y + 44), (x - mw * 0.3, y + 30)], closed=True, n=8)
            s = f'<path d="{d_of(P)}" fill="{INK}"/>'
            T = catmull([(x - mw / 2 + 12, y - 11), (x, y - 4), (x + mw / 2 - 12, y - 11), (x + mw * 0.3, y + 6), (x - mw * 0.3, y + 6)], closed=True, n=6)
            s += f'<path d="{d_of(T)}" fill="{CREAM}"/>' + ring(P, 10, 14, seed=sd)
            return s
        if k == 'wavy':
            mw = w if w > 100 else 130
            pts = [(x - mw / 2 + mw * i / 40, y + 10 * math.sin(i / 40 * 2 * math.pi * 2.5)) for i in range(41)]
            return brush(R(pts), 14, seed=sd, taper=(0.12, 0.12))
        if k == 'smirk':
            mw = 70
            s = brush(R([(x - mw / 2, y + 4), (x - 4, y + 6), (x + mw / 2 - 6, y - 6), (x + mw / 2 + 4, y - 18)]), 14.5, seed=sd, taper=(0.25, 0.2))
            s += brush(R([(x + mw / 2 + 12, y - 26), (x + mw / 2 + 16, y - 12)]), 6, seed=sd + 3, taper=(0.3, 0.3))
            return s
        return ''

    def hair(self):
        p = self.p
        W, H = p['W'], p['H']
        kind = p['hair']
        sd = p['seed'] + 51
        if kind in ('topknot', 'topknot_spiky'):
            x, y = -0.08 * W, -0.5 * H + 2
            if kind == 'topknot':
                P = catmull([(x - 24, y - 6), (x - 20, y - 30), (x + 2, y - 40), (x + 22, y - 28), (x + 24, y - 6), (x, y + 2)], closed=True, n=8)
                s = filled(P, CREAM, 8, 11, seed=sd)
                s += brush([(x - 10, y - 26), (x + 4, y - 32), (x + 14, y - 22)], 5, seed=sd + 1)
            else:
                s = ''
                for k, (bx, tip) in enumerate([(-10, (x - 34, y - 62)), (0, (x + 2, y - 72)), (10, (x + 36, y - 62))]):
                    P = catmull([(x + bx - 10, y - 22), (((x + bx) + tip[0]) / 2 - 8, ((y - 22) + tip[1]) / 2), tip, (((x + bx) + tip[0]) / 2 + 8, ((y - 22) + tip[1]) / 2 + 2), (x + bx + 10, y - 22)], closed=True, n=5)
                    s += filled(P, CREAM, 6, 9, seed=sd + 5 + k)
                P = catmull([(x - 24, y - 6), (x - 20, y - 30), (x + 2, y - 40), (x + 22, y - 28), (x + 24, y - 6), (x, y + 2)], closed=True, n=8)
                s += filled(P, CREAM, 8, 11, seed=sd)
            band = [(x - 22, y - 2), (x + 22, y - 2), (x + 20, y + 10), (x - 20, y + 10)]
            s += filled(band, INK, 4, 5, seed=sd + 2)
            return s
        if kind == 'headband':
            return ''  # drawn after outline (needs clip)
        return ''

    def headband(self, clip):
        p = self.p
        W, H = p['W'], p['H']
        y0, y1 = -0.30 * H, -0.205 * H
        band = [(-W, y0 + 14), (0, y0 - 4), (W, y0 + 6), (W, y1 + 10), (0, y1 - 2), (-W, y1 + 18)]
        s = f'<g clip-path="url(#{clip})"><path d="{d_of(catmull(band, closed=True, n=6))}" fill="{INK}"/>'
        s += brush([(-W * 0.6, y0 + 14), (0, y0 + 4), (W * 0.6, y0 + 10)], 4, color='#4A4054', seed=p['seed'] + 61) + '</g>'
        # knot + tails at the back
        kx, ky = -0.47 * W, (y0 + y1) / 2 + 6
        tails = p.get('tails', 'back')
        s += f'<ellipse cx="{f1(kx)}" cy="{f1(ky)}" rx="15" ry="13" fill="{INK}"/>'
        if tails == 'back':
            for i, (dy, ln) in enumerate([(-10, 150), (14, 120)]):
                pts = [(kx, ky), (kx - ln * 0.4, ky + dy * 0.6 - 4), (kx - ln * 0.75, ky + dy + 4), (kx - ln, ky + dy * 1.6)]
                s += brush(pts, 22, seed=p['seed'] + 70 + i, taper=(0.0, 0.25), wmin=6)
        return s

    def hiko_hair(self):
        """Short hair hugging the skull, tufts swept back (he is flying head-first)."""
        p = self.p
        W, H = p['W'], p['H']
        yb = -0.235 * H
        P = self.head_shape()
        top = [q for q in P if q[1] < yb]
        top.sort(key=lambda q: -math.atan2(q[1] + 0.1 * H, q[0]))  # front -> back
        n = len(top)
        N = 6
        hair = [(top[0][0] - 4, yb)]
        for j in range(2 * N + 1):
            i = int(round(j * (n - 1) / (2 * N)))
            x, y = top[i]
            cx, cy = x, y + 0.12 * H
            l = math.hypot(cx, cy) or 1
            ux, uy = cx / l, cy / l
            if j % 2 == 0:
                hair.append((x + ux * 3, y + uy * 3))
            else:
                ln = 40 + 9 * math.sin(j * 1.7)
                hair.append((x + ux * ln - 26, y + uy * ln - 2))
        hair.append((top[-1][0] - 2, yb))
        return filled(hair, '#4B3030', 10, 13, seed=p['seed'] + 81)

    def beard(self):
        p = self.p
        kind = p['beard']
        if not kind:
            return ''
        W, H = p['W'], p['H']
        cx, cy = p['turn'] * 0.7 + 0.10 * W, 0.47 * H
        out = []
        # (start dx, start dy, tip dx, tip dy, mid bulge dx, mid dy) relative to the chin anchor
        if kind == 'rest':      # a thin wisp: three strokes gathering to one point
            spec = [(-16, 0, 0, 82, -10, 40), (16, 0, 12, 80, 12, 38), (0, 2, 6, 100, -4, 50)]
        elif kind == 'flick':   # flung outward by the shock
            spec = [(-14, 0, -76, 36, -36, 34), (14, 0, 80, 34, 40, 32), (0, 2, 4, 92, -6, 48)]
        else:                   # swept forward (smug stroke)
            spec = [(-14, 0, 40, 74, 2, 44), (14, 0, 66, 66, 34, 36), (0, 2, 54, 86, 14, 48)]
        for i, (sx, sy, tx, ty, mx, my) in enumerate(spec):
            pts = catmull([(cx + sx, cy - 10 + sy), (cx + (sx + tx) / 2 + mx * 0.6, cy + my), (cx + tx, cy + ty)], n=10)
            out.append(brush(pts, 10.5, color=INK, seed=p['seed'] + 90 + i, taper=(0.1, 0.8), wmin=3.5, wob=0.5))
            out.append(brush(pts, 6.5, color=CREAM, seed=p['seed'] + 90 + i, taper=(0.1, 0.8), wmin=1.0, wob=0.5))
        return ''.join(out)

    def marks(self):
        p = self.p
        W, H = p['W'], p['H']
        c = p['mark_col']
        out = []

        def mb(pts, w, color=None, seed=0, taper=(0.3, 0.3)):
            r = ''
            if p.get('mark_outline'):
                r += brush(pts, w + 7, color=INK, seed=seed, taper=taper, wmin=4)
            return r + brush(pts, w, color=c, seed=seed, taper=taper)
        for m in p['marks']:
            kind = m[0]
            if kind == 'emanata':  # 3 short lines radiating, at each side or above
                where = m[1]
                if where == 'above':
                    ca = m[2] if len(m) > 2 else 0
                    for i, a in enumerate((ca - 18, ca, ca + 18)):
                        r0, r1 = H * 0.66, H * 0.78
                        aa = math.radians(a - 90)
                        cx = -0.03 * W
                        out.append(mb([(cx + r0 * math.cos(aa), r0 * math.sin(aa) + 0.0), (cx + r1 * math.cos(aa), r1 * math.sin(aa))], 9, color=c, seed=p['seed'] + 100 + i, taper=(0.12, 0.2)))
                else:
                    for sgn in (-1, 1):
                        for i, a in enumerate((-28, 0, 28)):
                            aa = math.radians(a)
                            x0 = sgn * (W * 0.62)
                            y0 = -0.05 * H
                            dx, dy = math.cos(aa) * 40 * sgn, math.sin(aa) * 40
                            out.append(mb([(x0 + dx * 0.0 + sgn * 0, y0 + math.sin(aa) * 60), (x0 + dx, y0 + math.sin(aa) * 60 + dy)], 9, color=c, seed=p['seed'] + 110 + i, taper=(0.3, 0.3)))
            elif kind == 'vein':
                vx, vy, sz = m[1], m[2], m[3]
                for k in range(4):
                    a = math.radians(45 + 90 * k)
                    pa = (vx + sz * math.cos(a - 0.62), vy + sz * math.sin(a - 0.62))
                    pb = (vx + sz * math.cos(a + 0.62), vy + sz * math.sin(a + 0.62))
                    pc = (vx + sz * 0.28 * math.cos(a), vy + sz * 0.28 * math.sin(a))
                    pts = qbez(pa, pc, pb, 12)
                    out.append(brush(pts, 15, color=INK, seed=p['seed'] + 120 + k, taper=(0.12, 0.12), wmin=6, wob=0.4))
                    out.append(brush(pts, 9, color=VERM, seed=p['seed'] + 120 + k, taper=(0.12, 0.12), wmin=3, wob=0.4))
            elif kind == 'sweat':
                sx, sy, sz, ang = m[1], m[2], m[3], m[4]
                P = [(0, -sz * 1.25)] + [(sz * 0.62 * math.cos(t), sz * 0.15 + sz * 0.62 * math.sin(t)) for t in [math.radians(d) for d in range(-35, 216, 15)]]
                P = xform(P, dx=sx, dy=sy, rot=ang)
                out.append(filled(P, CREAM, 5, 7, seed=p['seed'] + 130))
            elif kind == 'gloom':
                for i in range(4):
                    x = -0.02 * W + (i - 1.5) * 0.30 * W
                    y0 = -0.60 * H - (0 if i in (0, 3) else 14)
                    out.append(mb([(x, y0), (x + 1, y0 + 60 + (i % 2) * 12)], 8, color=c, seed=p['seed'] + 140 + i, taper=(0.15, 0.4)))
            elif kind == 'shake':
                for sgn in (-1, 1):
                    for i in range(2):
                        x = sgn * (W * 0.58 + i * 22)
                        y0 = -0.10 * H
                        bow = sgn * 8
                        out.append(mb([(x, y0 - 34 + i * 6), (x + bow, y0), (x, y0 + 34 - i * 6)], 8, color=c, seed=p['seed'] + 150 + i, taper=(0.3, 0.3)))
        return ''.join(out)

    # -- assembly
    def head_group(self, ghost=False):
        p = self.p
        W, H = p['W'], p['H']
        P = self.head_shape()
        d = d_of(P)
        cid = f'hc{uid()}'
        # rim light: light from world-left -> local shift away from light
        ang = p['tilt'] * p['facing'] if not ghost else (p['tilt'] + 4) * p['facing']
        sh = p['rim'] + 6
        a = math.radians(-ang)
        lx = sh * math.cos(a)
        ly = sh * math.sin(a)
        lx *= p['facing']
        s = [f'<clipPath id="{cid}"><path d="{d}"/></clipPath>']
        if p['ear']:
            s.append(self.ear())
        s.append(f'<path d="{d}" fill="{p["rim_col"]}"/>')
        s.append(f'<g clip-path="url(#{cid})"><path d="{d}" fill="{p["skin"]}" transform="translate({f1(lx)} {f1(ly)})"/></g>')
        if p['hair'] == 'scarf':
            cloth = catmull([(-W, -H), (W, -H), (W, -0.16 * H), (0.3 * W, -0.20 * H), (-0.1 * W, -0.14 * H), (-0.5 * W, -0.04 * H), (-W, 0.1 * H)], closed=True, n=6)
            s.append(f'<g clip-path="url(#{cid})"><path d="{d_of(cloth)}" fill="{CREAM}"/>')
            for yy in (-0.40, -0.30):
                s.append(brush([(-W, yy * H + 30), (0, yy * H - 6), (W, yy * H)], 9, color=PLUM_L, seed=p['seed'] + 160, taper=(0, 0)))
            s.append('</g>')
        s.append(ring(P, p['outline'][0], p['outline'][1], seed=p['seed'], heavy=(0.5, 0.86)))
        if p['hair'] == 'scarf':
            s.append(brush([(0.5 * W, -0.16 * H), (0.3 * W, -0.20 * H), (-0.1 * W, -0.14 * H), (-0.46 * W, -0.04 * H)], 12, seed=p['seed'] + 161, taper=(0.05, 0.1)))
            knot = catmull([(-0.30 * W, -0.47 * H), (-0.50 * W, -0.66 * H), (-0.30 * W, -0.62 * H), (-0.16 * W, -0.70 * H), (-0.10 * W, -0.50 * H)], closed=True, n=6)
            s.append(filled(knot, CREAM, 9, 12, seed=p['seed'] + 162))
        if p['hair'] == 'hiko':
            s.append(self.hiko_hair())
            s.append(self.headband(cid))
        s.append(self.hair())
        s.append(self.wrinkles())
        s.append(self.eyes())
        s.append(self.lids() + self.pupils() + self.brows())
        s.append(self.nose())
        s.append(self.mouth())
        s.append(self.beard())
        return ''.join(s)

    def transform(self, cx, cy, tilt_extra=0):
        p = self.p
        H = p['H']
        piv = 0.42 * H
        ang = (p['tilt'] + tilt_extra) * p['facing']
        k = p.get('scale', 1.0)
        return f'translate({f1(cx)} {f1(cy - p["lift"])}) scale({k}) translate(0 {f1(piv)}) rotate({f1(ang)}) translate(0 {f1(-piv)}) scale({p["facing"]} 1)'

    def svg(self, cx, cy):
        p = self.p
        out = []
        if p['ghost']:
            gp = d_of(self.head_shape())
            out.append(f'<g opacity="0.3" transform="{self.transform(cx, cy, 4)}"><path d="{gp}" fill="{p["skin"]}"/>{ring(self.head_shape(), 9, 12, color=CREAM, seed=p["seed"] + 7)}</g>')
        out.append(f'<g transform="{self.transform(cx, cy)}">{self.head_group()}{self.marks()}</g>')
        return ''.join(out)


# ---------------------------------------------------------------- expressions (the master)
EXPR = {
    'neutral': dict(eyes='flat', mouth='flat', m_w=60, tilt=12),
    'surprised': dict(eyes='circle', mouth='o', tilt=0, lift=15, beard='flick', turn=0, circ_sp=112, circ_r=47,
                      marks=(('emanata', 'sides'),), wrinkles=True),
    'angry': dict(eyes='slant', mouth='grimace', tilt=20, hair='topknot_spiky', marks=(('vein', -50, -118, 22),), m_dy=4),
    'smug': dict(eyes='u', mouth='smirk', tilt=-13, beard='forward', m_dx=8, fdy=-10, lift=6),
    'panic': dict(eyes='wavy', mouth='wavy', m_w=130, ghost=True,
                  marks=(('sweat', -128, -70, 18, -30), ('sweat', 136, -96, 15, 30), ('shake',))),
    'side': dict(eyes='double', eye_dx=22, mouth='flat', m_w=40, m_dx=34, m_rot=14, tilt=-8, marks=(('gloom',),)),
}


def faces_svg():
    W, H = 1080, 1080
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{PLUM}"/>']
    order = ['neutral', 'surprised', 'angry', 'smug', 'panic', 'side']
    for i, k in enumerate(order):
        col, row = i % 3, i // 3
        ox, oy = col * 360, row * 540
        out.append(f'<g transform="translate({ox} {oy})">')
        out.append(f'<circle cx="180" cy="262" r="172" fill="{AMBER}" opacity="0.13"/>')
        out.append(f'<circle cx="180" cy="262" r="128" fill="{AMBER}" opacity="0.12"/>')
        # neck + collar
        out.append(collar(180, 540, SKIN_M, seed=200 + i))
        f = Face(seed=11 + i * 0, **EXPR[k])
        out.append(f.svg(180, 270))
        out.append('</g>')
    # faint cell separators
    for x in (360, 720):
        out.append(f'<rect x="{x - 1}" y="0" width="2" height="{H}" fill="{PLUM_D}"/>')
    out.append(f'<rect x="0" y="539" width="{W}" height="2" fill="{PLUM_D}"/>')
    out.append('</svg>')
    return '\n'.join(out)


def collar(cx, base, skin, seed=0):
    neck = [(cx - 34, 410), (cx + 40, 410), (cx + 44, 500), (cx - 38, 500)]
    robe = catmull([(cx - 180, base + 4), (cx - 150, 478), (cx - 70, 462), (cx, 470), (cx + 80, 460), (cx + 160, 476), (cx + 184, base + 4)], closed=False, n=6)
    robe = robe + [(cx + 184, base + 30), (cx - 184, base + 30)]
    s = filled(neck, skin, 9, 12, seed=seed)
    s += filled(robe, WOOD, 10, 14, seed=seed + 1)
    # crossed collar (wearer's left over right)
    s += brush([(cx - 64, 466), (cx - 10, 520), (cx + 4, base + 10)], 26, color=INK, seed=seed + 2, taper=(0.0, 0.0), wmin=26, wob=0.6)
    s += brush([(cx - 64, 466), (cx - 10, 520), (cx + 4, base + 10)], 15, color=CREAM, seed=seed + 2, taper=(0.0, 0.0), wmin=15, wob=0.6)
    s += brush([(cx + 70, 462), (cx + 20, 512), (cx - 14, base + 10)], 28, color=INK, seed=seed + 3, taper=(0.0, 0.0), wmin=28, wob=0.6)
    s += brush([(cx + 70, 462), (cx + 20, 512), (cx - 14, base + 10)], 17, color=CREAM, seed=seed + 3, taper=(0.0, 0.0), wmin=17, wob=0.6)
    return s


# ---------------------------------------------------------------- scene
def hand_open(wx, wy, ang, size=1.0, spread=1.0, seed=0):
    """Open grabbing hand: palm + 4 spread fingers + thumb. ang = pointing direction (deg)."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -uy, ux
    def P(u, v):
        return (wx + (ux * u + vx * v) * size, wy + (uy * u + vy * v) * size)
    palm = catmull([P(-4, -20), P(28, -24), P(42, -12), P(42, 14), P(26, 22), P(-4, 18)], closed=True, n=6)
    shapes = [palm]
    for v, ln, sp in [(-18, 36, -30), (-7, 44, -11), (5, 42, 8), (16, 34, 26)]:
        b = math.radians(sp * spread)
        shapes.append(capsule(P(36, v), P(36 + math.cos(b) * ln, v + math.sin(b) * ln), 6.5 * size))
    shapes.append(capsule(P(14, -18), P(30, -46), 7 * size))
    return shapes


def scene_svg():
    W, H = 1080, 1920
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    o.append(f'<defs><clipPath id="wall"><rect x="0" y="230" width="{W}" height="1345"/></clipPath></defs>')
    # --- wall
    o.append(f'<rect width="{W}" height="{H}" fill="{PLUM}"/>')
    FLOOR = 1250
    # shoji bay x 250..1080
    sx0, sx1, sy0, sy1 = 262, 1080, 300, 1176
    o.append(f'<rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}" fill="{MOON}"/>')
    # lattice
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
    # kick panel under shoji
    o.append(f'<rect x="{sx0 - 10}" y="{sy1 + 14}" width="{sx1 - sx0 + 20}" height="{FLOOR - sy1 - 14}" fill="{PLUM_L}"/>')
    # post at the left edge of the shoji bay
    o.append(f'<rect x="{sx0 - 40}" y="230" width="40" height="{FLOOR - 230}" fill="{PLUM_D}"/>')
    # lintel / beam
    o.append(f'<rect x="0" y="230" width="{W}" height="36" fill="{PLUM_D}"/>')
    # lantern glow pool (stepped, flat)
    gx, gy = 170, 780
    o.append('<g clip-path="url(#wall)">')
    for r, op in ((470, 0.10), (350, 0.12), (230, 0.15)):
        o.append(f'<circle cx="{gx}" cy="{gy}" r="{r}" fill="{AMBER}" opacity="{op}"/>')
    o.append('</g>')
    # --- floor
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="{1575 - FLOOR}" fill="{TATAMI}"/>')
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="10" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M0 1400 L{W} 1388 L{W} 1400 L0 1413 Z" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M700 {FLOOR} L712 {FLOOR} L780 1575 L766 1575 Z" fill="{TATAMI_D}"/>')
    o.append(f'<ellipse cx="200" cy="1470" rx="300" ry="70" fill="{AMBER}" opacity="0.12"/>')
    # ceiling band (flat, nothing else)
    o.append(f'<rect x="0" y="0" width="{W}" height="230" fill="{PLUM_D}"/>')
    # lantern (hanging, no lettering)
    lx, ly = 120, 610
    o.append(brush([(lx, 266), (lx + 1, ly - 100)], 6, seed=301, taper=(0, 0)))
    lant = ellipse(lx, ly, 70, 96, n=60)
    o.append(filled(lant, AMBER, 8, 11, seed=302))
    for k in (-60, -30, 0, 30, 60):
        hw = 70 * math.sqrt(max(0, 1 - (k / 96) ** 2))
        o.append(brush([(lx - hw + 6, ly + k), (lx, ly + k + 8), (lx + hw - 6, ly + k)], 4, color='#C98A2E', seed=310 + k, taper=(0.2, 0.2)))
    o.append(filled([(lx - 40, ly - 112), (lx + 40, ly - 112), (lx + 44, ly - 88), (lx - 44, ly - 88)], INK, 4, 6, seed=303))
    o.append(filled([(lx - 40, ly + 88), (lx + 40, ly + 88), (lx + 36, ly + 110), (lx - 36, ly + 110)], INK, 4, 6, seed=304))
    # low table + teapot at far left
    o.append(filled([(-30, 1300), (150, 1300), (162, 1334), (-30, 1334)], WOOD, 7, 9, seed=320))
    o.append(filled([(110, 1334), (134, 1334), (134, 1430), (110, 1430)], WOOD_D, 6, 8, seed=321))
    pot = catmull([(14, 1300), (4, 1262), (34, 1230), (76, 1232), (96, 1264), (88, 1300)], closed=True, n=8)
    o.append(filled([(10, 1266), (-26, 1236), (-20, 1228), (14, 1250)], PLUM_L, 6, 8, seed=322))
    o.append(filled(pot, PLUM_L, 7, 9, seed=323))
    o.append(filled(ellipse(52, 1226, 18, 7, n=24), PLUM_L, 5, 6, seed=324))
    o.append(f'<circle cx="52" cy="1214" r="7" fill="{INK}"/>')
    o.append(brush([(24, 1262), (52, 1270), (80, 1262)], 4, color=BRASS, seed=325, taper=(0.1, 0.1)))
    # bottom band
    o.append(f'<rect x="0" y="1575" width="{W}" height="{H - 1575}" fill="{TATAMI_D}"/>')

    # --- speed lines behind Hiko
    for i, (y, x0, x1) in enumerate([(700, 930, 1080), (760, 900, 1080), (470, 960, 1080)]):
        o.append(brush([(x0, y), (x1, y - 40)], 7, color=PLUM, seed=330 + i, taper=(0.6, 0.0), op=0.55))

    # --- MASTER (seiza, lower left)
    mx, my = 330, 845
    o.append(filled(catmull([(30, 1512), (330, 1500), (630, 1512), (646, 1566), (330, 1578), (14, 1566)], closed=True, n=6), '#5E3E62', 9, 12, seed=400))
    # neck
    o.append(filled([(298, 950), (368, 950), (372, 1060), (296, 1060)], SKIN_M, 9, 12, seed=401))
    # knees / lap + torso under one outline
    lap = catmull([(70, 1540), (62, 1430), (150, 1350), (330, 1336), (520, 1350), (604, 1432), (598, 1540), (330, 1552)], closed=True, n=8)
    torso = catmull([(190, 1062), (330, 1036), (470, 1062), (512, 1150), (508, 1330), (330, 1360), (156, 1330), (150, 1150)], closed=True, n=8)
    o.append(ring(lap, 18, 26, seed=410) + ring(torso, 18, 26, seed=411) + rimlit(lap, WOOD, (14, -2)) + rimlit(torso, WOOD, (14, -2)))
    o.append(brush([(150, 1476), (330, 1492), (530, 1476)], 7, color=WOOD_D, seed=413))
    o.append(brush([(330, 1372), (338, 1450), (332, 1536)], 7, color=WOOD_D, seed=414))
    # sash
    o.append(filled([(162, 1296), (502, 1296), (506, 1344), (158, 1344)], PLUM_L, 8, 10, seed=415))
    # collar V (wearer's left over right)
    for pts, sd in (([(282, 1040), (330, 1130), (372, 1296)], 416), ([(392, 1040), (352, 1118), (318, 1214)], 417)):
        o.append(brush(pts, 32, color=INK, taper=(0, 0), wmin=32, seed=sd, wob=0.6))
        o.append(brush(pts, 19, color=CREAM, taper=(0, 0), wmin=19, seed=sd, wob=0.6))
    # left arm (viewer left): big hanging sleeve, forearm across to the teacup
    sleeve_l = catmull([(196, 1070), (138, 1130), (112, 1240), (106, 1352), (150, 1372), (236, 1352), (262, 1262), (250, 1214), (214, 1150)], closed=True, n=8)
    o.append(rimlit(sleeve_l, WOOD, (13, -3)) + ring(sleeve_l, 11, 15, seed=420))
    o.append(brush([(150, 1170), (142, 1280), (160, 1350)], 6, color=WOOD_D, seed=421))
    o.append(filled(ellipse(244, 1238, 22, 30, rot=-20, n=30), WOOD_D, 7, 9, seed=425))  # cuff opening
    hand_l = catmull([(226, 1204), (268, 1192), (304, 1200), (302, 1226), (256, 1240), (224, 1230)], closed=True, n=6)
    o.append(filled(hand_l, SKIN_M, 8, 11, seed=422))
    cup = catmull([(230, 1150), (296, 1150), (290, 1188), (262, 1202), (236, 1188)], closed=True, n=6)
    o.append(filled(cup, CREAM, 8, 10, seed=423))
    o.append(f'<ellipse cx="263" cy="1152" rx="31" ry="7" fill="{MATCHA}"/>')
    o.append(brush([(238, 1168), (290, 1168)], 5, color=VERM, seed=424, taper=(0.1, 0.1)))
    o.append(brush([(262, 1206), (298, 1206)], 5, color=INK, seed=426))  # fingers
    # right arm (viewer right): raised high, sleeve slid down to the elbow, fan up
    fore_r = tube([(604, 996), (566, 920), (530, 868)], 46, 38)
    o.append(filled(fore_r, SKIN_M, 9, 12, seed=430))
    sleeve_r = catmull([(456, 1066), (540, 1010), (600, 968), (640, 992), (640, 1060), (612, 1150), (574, 1150), (540, 1120), (494, 1140)], closed=True, n=8)
    o.append(filled(sleeve_r, WOOD, 11, 15, seed=431))
    o.append(filled(ellipse(612, 982, 30, 18, rot=-35, n=30), WOOD_D, 7, 9, seed=437))
    o.append(brush([(604, 1036), (608, 1090), (596, 1130)], 6, color=WOOD_D, seed=438))
    # fan (closed sensu): base at the fist, tip under the ball
    ftx, fty = 474, 704
    fan = [(520, 880), (542, 888), (ftx + 20, fty + 4), (ftx - 18, fty - 6)]
    o.append(filled(fan, '#3B2B3F', 7, 9, seed=432))
    o.append(brush([(528, 878), (ftx - 2, fty + 8)], 3, color=BRASS, seed=433, taper=(0.1, 0.1)))
    o.append(brush([(538, 884), (ftx + 9, fty + 8)], 3, color=BRASS, seed=439, taper=(0.1, 0.1)))
    fist = catmull([(506, 852), (546, 842), (566, 870), (556, 902), (516, 904), (500, 880)], closed=True, n=6)
    o.append(filled(fist, SKIN_M, 8, 11, seed=434))
    o.append(brush([(512, 868), (548, 862)], 5, seed=435))
    o.append(brush([(512, 886), (550, 882)], 5, seed=436))
    # impact splatter at the fan tip
    spl = [(ftx + 18 * math.cos(math.radians(a)) * (1.0 if k % 2 else 0.55), fty - 6 + 18 * math.sin(math.radians(a)) * (1.0 if k % 2 else 0.55)) for k, a in enumerate(range(180, 361, 20))]
    for k, (a, r, sz) in enumerate([(200, 34, 6), (235, 40, 5), (300, 38, 5), (335, 32, 6), (260, 46, 4), (160, 30, 3.5), (20, 30, 3.5)]):
        o.append(f'<circle cx="{f1(ftx + r * math.cos(math.radians(a)))}" cy="{f1(fty - 4 + r * math.sin(math.radians(a)))}" r="{sz}" fill="{INK}"/>')
    # head (eyes snap open, aimed up-right at Hiko)
    master = Face(seed=11, eyes='circle', circ_sp=112, circ_r=48, mouth='dot', tilt=-4, turn=18, fdy=-8, beard='flick',
                  marks=(('emanata', 'above', 2),), mark_col=CREAM, mark_outline=True)
    o.append(master.svg(mx, my))

    # --- BALL
    bx, by, br = ftx - 4, fty - 60 - 35, 35
    o.append(f'<ellipse cx="{bx}" cy="{by + br + 24}" rx="30" ry="8" fill="none" stroke="{INK}" stroke-width="5"/>')
    ball = ellipse(bx, by, br, br, n=48)
    o.append(f'<path d="{d_of(ball)}" fill="{VERM}"/>')
    for k in range(6):
        a0 = math.radians(k * 60 + 10)
        a1 = math.radians(k * 60 + 34)
        o.append(f'<path d="M{bx} {by} L{f1(bx + br * math.cos(a0))} {f1(by + br * math.sin(a0))} L{f1(bx + br * math.cos(a1))} {f1(by + br * math.sin(a1))} Z" fill="{CREAM}"/>')
    o.append(f'<circle cx="{bx}" cy="{by}" r="9" fill="{VERM}"/>')
    o.append(ring(ball, 8, 11, seed=500))
    bell = ellipse(bx + br + 6, by + 18, 12, 11, n=30)
    o.append(filled(bell, BRASS, 5, 7, seed=501))
    o.append(brush([(bx + br + 1, by + 22), (bx + br + 12, by + 22)], 3, seed=502, taper=(0, 0)))


    # --- WITNESS (cleaning lady, kneeling at the back wall: "here we go again")
    wx, wy = 968, 944
    broom = [(1046, 760), (1056, 760), (1062, 1180), (1052, 1180)]
    o.append(filled(broom, BRASS, 5, 7, seed=700))
    straw = catmull([(1036, 1170), (1080, 1170), (1096, 1262), (1018, 1262)], closed=True, n=4)
    o.append(filled(straw, '#C9A65A', 6, 8, seed=701))
    for k in range(4):
        o.append(brush([(1040 + k * 12, 1186), (1034 + k * 18, 1252)], 3, color='#8E6E2E', seed=702 + k, taper=(0.1, 0.3)))
    wbody = catmull([(968, 1022), (1020, 1036), (1048, 1080), (1060, 1170), (1074, 1270), (968, 1282), (862, 1270), (876, 1170), (888, 1080), (916, 1036)], closed=True, n=8)
    o.append(filled(wbody, PLUM_L, 9, 12, seed=703))
    apron = catmull([(936, 1060), (968, 1074), (1000, 1060), (1012, 1160), (1010, 1262), (968, 1268), (926, 1262), (924, 1160)], closed=True, n=6)
    o.append(filled(apron, CREAM, 6, 8, seed=704))
    o.append(brush([(940, 1034), (968, 1076), (996, 1034)], 8, color=CREAM, seed=706, taper=(0, 0)))
    o.append(brush([(926, 1150), (968, 1156), (1012, 1150)], 5, color=INK, seed=707, taper=(0.1, 0.1)))
    o.append(filled(catmull([(1012, 1120), (1050, 1110), (1062, 1134), (1030, 1150)], closed=True, n=4), SKIN_H, 6, 8, seed=705))
    puff = [ellipse(890, 990, 16, 13, n=24), ellipse(870, 982, 13, 11, n=24), ellipse(876, 1000, 12, 10, n=24)]
    o.append(union(puff, CREAM, 8, 10, seed=708))
    witness = Face(seed=51, scale=0.44, skin='#D49C76', skin_d='#B9825E', facing=-1, tilt=4, turn=6, hair='scarf', beard=None,
                   wrinkles=False, eyes='sag', mouth='flat', m_w=62, m_rot=-6, m_dy=-4, outline=(20, 24), rim=8)
    o.append(witness.svg(wx, wy))

    # --- HIKO (frozen mid-leap, upper right; diving down-left at the ball)
    hx, hy = 818, 462
    # torso trailing up-right off canvas
    torso_h = tube([(870, 650), (1000, 600), (1140, 556)], 172, 150, cap=False)
    o.append(filled(torso_h, MATCHA, 12, 16, seed=620))
    o.append(brush([(870, 600), (930, 650), (1010, 662)], 20, color=CREAM, seed=622, taper=(0, 0.3), wmin=20))
    o.append(brush([(1020, 530), (1060, 600), (1080, 640)], 7, color=MATCHA_D, seed=623))
    # far arm (behind head)
    o.append(filled(tube([(900, 600), (810, 600), (750, 606)], 66, 56), MATCHA_D, 11, 14, seed=610))
    o.append(filled(tube([(770, 606), (676, 618)], 40, 34), SKIN_H, 9, 12, seed=613))
    o.append(union(hand_open(672, 618, 176, 1.12, seed=611), SKIN_H, 14, 18, seed=612))
    # head
    hiko = Face(seed=31, W=205, H=326, skin=SKIN_H, skin_d=SKIN_H_D, facing=-1, tilt=12, turn=8, hair='hiko', beard=None,
                wrinkles=False, nose=True, eyes='chev', mouth='wavy', m_w=118, eye_sp=86, eye_len=62,
                marks=(('sweat', -196, -150, 24, -40), ('sweat', 150, -150, 22, 30), ('shake',)), mark_col=INK)
    o.append(hiko.svg(hx, hy))
    # near arm (in front)
    o.append(filled(tube([(920, 690), (830, 700), (770, 704)], 70, 58), MATCHA, 11, 14, seed=630))
    o.append(filled(tube([(790, 704), (680, 700)], 42, 36), SKIN_H, 9, 12, seed=633))
    o.append(union(hand_open(676, 700, 186, 1.16, seed=631), SKIN_H, 14, 18, seed=632))

    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    with open(os.path.join(HERE, 'faces.svg'), 'w') as fh:
        fh.write(faces_svg())
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(scene_svg())
    print('ok')
