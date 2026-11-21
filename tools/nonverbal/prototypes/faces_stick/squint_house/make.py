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


# =====================================================================
# STICK-BODY RIG (new). The head above is the original Squint House rig,
# unchanged. Every figure = Stick body(pose) + Face(expression).
# Body line language copies the head: wobbly INK brush, fat at the root,
# thin and ragged at the wrist, amber lantern rim offset toward the light.
# =====================================================================
def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def pol(p, ang, L):
    a = math.radians(ang)
    return (p[0] + L * math.cos(a), p[1] + L * math.sin(a))


def ang_of(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def seg_pts(a, b, step=4.0):
    n = max(1, int(math.dist(a, b) / step))
    return [lerp(a, b, i / n) for i in range(1, n + 1)]


def joint_path(J, r=9):
    """Straight segments between joints, tiny round fillet at each inner joint
    (a bend, never a node, never one rubber-hose curve)."""
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


def ik(root, tgt, L1, L2, side=1, straight=False, minbend=8):
    """2-bone IK. Keeps a small bend unless `straight` (extension beats)."""
    d = math.dist(root, tgt)
    mb = 0.5 if straight else minbend
    dmax = math.sqrt(L1 * L1 + L2 * L2 + 2 * L1 * L2 * math.cos(math.radians(mb)))
    d = max(abs(L1 - L2) + 1, min(d, dmax - 0.01))
    a = math.atan2(tgt[1] - root[1], tgt[0] - root[0])
    cA = (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)
    A = math.acos(max(-1.0, min(1.0, cA)))
    e = (root[0] + L1 * math.cos(a + side * A), root[1] + L1 * math.sin(a + side * A))
    w = (root[0] + d * math.cos(a), root[1] + d * math.sin(a))
    return e, w


def anchor_of(face, cx, cy):
    """World position of the rig's own neck/tilt pivot (Face.transform rotates about it)."""
    p = face.p
    return (cx, cy - p['lift'] + 0.42 * p['H'] * p.get('scale', 1.0))


class Stick:
    """Stick body builder. Pose dict -> joints -> brush strokes.

    pose keys (lengths in HU = head height * scale):
      neck_ang  direction anchor->neck base (deg, 90 = down)
      neck      visible neck length            (0.05-0.12)
      spine_ang / spine   chord neck base->hip  (0.85-1.05)
      bow       spine bulge (HU, + = left of travel dir rotated -90)
      sh        shoulder drop below neck base along the spine (0.12-0.18)
      hand_f / hand_n     wrist target, HU offset from the shoulder
      elb_f / elb_n       elbow bend side (+1 / -1); straight_f/_n for snaps
      foot_f / foot_n     ankle target, HU offset from the hip; kn_f / kn_n knee side
    """

    def __init__(self, hu, light, skin=SKIN_M, w=(17, 12), ws=17, rimd=5.5, seed=0, facing=1, ink=INK,
                 ua=0.55, fa=0.50, th=0.68, sn=0.62):
        self.hu, self.light, self.skin, self.w, self.ws = hu, light, skin, w, ws
        self.rimd, self.seed, self.facing, self.ink = rimd, seed, facing, ink
        self.L = dict(ua=ua, fa=fa, th=th, sn=sn)

    # ---- geometry
    def solve(self, anchor, P):
        hu = self.hu
        J = {'anchor': anchor}
        nb = pol(anchor, P.get('neck_ang', 90), (0.07 + P.get('neck', 0.07)) * hu)
        hip = P['hip'] if 'hip' in P else pol(nb, P.get('spine_ang', 90), P.get('spine', 0.88) * hu)
        d = ang_of(nb, hip)
        ctrl = P['ctrl'] if 'ctrl' in P else pol(lerp(nb, hip, 0.5), d - 90, P.get('bow', 0.0) * hu)
        curve = qbez(nb, ctrl, hip, 30)
        tgt, acc, sh = P.get('sh', 0.14) * hu, 0.0, curve[-1]
        for a, b in zip(curve, curve[1:]):
            l = math.dist(a, b)
            if acc + l >= tgt:
                sh = lerp(a, b, (tgt - acc) / l)
                break
            acc += l
        J.update(nb=nb, hip=hip, sh=sh, curve=curve)
        L = {k: P.get(k, v) * hu for k, v in self.L.items()}
        for s in ('f', 'n'):
            if 'handw_' + s in P:
                T = P['handw_' + s]
            else:
                hx, hy = P['hand_' + s]
                T = (sh[0] + hx * hu, sh[1] + hy * hu)
            e, w = ik(sh, T, L['ua'], L['fa'], P.get('elb_' + s, 1), P.get('straight_' + s, False))
            J['el_' + s], J['wr_' + s] = e, w
            fx, fy = P['foot_' + s]
            k, a = ik(hip, (hip[0] + fx * hu, hip[1] + fy * hu), L['th'], L['sn'], P.get('kn_' + s, -1), P.get('straightleg_' + s, False))
            J['kn_' + s], J['an_' + s] = k, a
        for s_ in ('f', 'n'):  # direct joint overrides (world coords) for off-frame limbs
            if 'kneew_' + s_ in P:
                J['kn_' + s_] = P['kneew_' + s_]
                J['an_' + s_] = pol(J['kn_' + s_], P['shin_ang_' + s_], L['sn'])
        if 'far_leg_off' in P:  # seiza: far leg hides behind the near one, peeking up/back
            ox, oy = P['far_leg_off']
            J['kn_f'] = (J['kn_n'][0] + ox * hu, J['kn_n'][1] + oy * hu)
            J['an_f'] = (J['an_n'][0] + ox * hu * 0.6, J['an_n'][1] + oy * hu * 0.6)
        return J

    def rimv(self, pts, d=None):
        d = self.rimd if d is None else d
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        dx, dy = self.light[0] - mx, self.light[1] - my
        l = math.hypot(dx, dy) or 1
        return (dx / l * d, dy / l * d)

    # ---- strokes
    def stroke(self, J, w0=None, w1=None, seed=0, rim=True, taper=(0.08, 0.38), color=None, r=9):
        w0 = w0 or self.w[0]
        w1 = w1 or self.w[1]
        color = color or self.ink
        P = joint_path(J, r)
        out = []

        def one(Q, col):
            s = brush(Q, w0, color=col, taper=taper, wmin=w1, wob=1.1, seed=self.seed + seed, smooth=False)
            for q in (Q[0], Q[-1]):
                s += f'<circle cx="{f1(q[0])}" cy="{f1(q[1])}" r="{f1(w1 / 2)}" fill="{col}"/>'
            return s
        if rim:
            rv = self.rimv(J)
            out.append(one([(x + rv[0], y + rv[1]) for x, y in P], AMBER))
        out.append(one(P, color))
        return ''.join(out)

    def spine(self, J, seed=0):
        """One continuous stroke: hip -> shoulder -> neck base -> into the head pivot."""
        pts = J['curve'][::-1] + [J['anchor']]
        pts = catmull([pts[0]] + pts[3:-4:3] + [pts[-2], pts[-1]], n=6)
        w = self.ws
        rv = self.rimv(pts)
        s = brush([(x + rv[0], y + rv[1]) for x, y in pts], w, color=AMBER, taper=(0.04, 0.0), wmin=w - 3, wob=1.0, seed=self.seed + 900 + seed, smooth=False)
        s += brush(pts, w, color=self.ink, taper=(0.04, 0.0), wmin=w - 3, wob=1.0, seed=self.seed + 900 + seed, smooth=False)
        q = pts[0]
        s += f'<circle cx="{f1(q[0])}" cy="{f1(q[1])}" r="{f1((w - 3) / 2)}" fill="{self.ink}"/>'
        return s

    def arm(self, J, s, seed=0, rim=True):
        return self.stroke([J['sh'], J['el_' + s], J['wr_' + s]], seed=seed, rim=rim)

    def leg(self, J, s, seed=0, rim=True):
        return self.stroke([J['hip'], J['kn_' + s], J['an_' + s]], seed=seed + 40, rim=rim)

    # ---- hands & feet (same edge treatment as the head: amber rim fill + brush ring)
    def mitten(self, wr, ang, seed=0, L=None, Wd=None, skin=None, ring_w=(4.0, 5.5)):
        hu = self.hu
        L = L or 0.125 * hu
        Wd = Wd or 2.1 * self.w[1]
        loc = [(-5, -0.36), (0.22 * L, -0.50), (0.60 * L, -0.53), (0.90 * L, -0.40), (L + 1, 0), (0.90 * L, 0.40),
               (0.60 * L, 0.53), (0.22 * L, 0.50), (-5, 0.36)]
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        P = catmull([(wr[0] + ux * u - uy * v * Wd, wr[1] + uy * u + ux * v * Wd) for u, v in loc], closed=True, n=6)
        rv = self.rimv(P, 4.0)
        return rimlit(P, skin or self.skin, (-rv[0], -rv[1])) + ring(P, ring_w[0], ring_w[1], seed=self.seed + 300 + seed, heavy=(0.5, 0.86))

    def hand_pt(self, wr, ang, u, v=0.0, L=None):
        """Point in mitten-local coords (u along the hand, v across, in fractions)."""
        L = L or 0.125 * self.hu
        a = math.radians(ang)
        Wd = 2.1 * self.w[1]
        return (wr[0] + math.cos(a) * u * L - math.sin(a) * v * Wd, wr[1] + math.sin(a) * u * L + math.cos(a) * v * Wd)

    def thumb(self, base, ang, ln=None, r=None, seed=0, skin=None):
        ln = ln or 0.05 * self.hu
        r = r or max(4.5, 0.42 * self.w[1])
        P = capsule(base, pol(base, ang, ln), r)
        return f'<path d="{d_of(P)}" fill="{skin or self.skin}"/>' + ring(P, 3.2, 4.2, seed=self.seed + 330 + seed)

    def foot(self, an, ang, kind='bare', facing=1, seed=0, L=None):
        """Flat-soled foot. ang = toe direction. kind: 'bare' or 'tabi'."""
        hu = self.hu
        L = L or 0.19 * hu
        dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        ux, uy = facing * dy, -facing * dx  # 'up' (instep side)

        def W(u, v):
            return (an[0] + dx * u * L + ux * v * L, an[1] + dy * u * L + uy * v * L)
        loc = [(-0.24, 0.0), (0.80, 0.0), (0.88, 0.08), (0.84, 0.20), (0.62, 0.27), (0.30, 0.34), (0.06, 0.46), (-0.20, 0.40), (-0.30, 0.18)]
        P = catmull([W(u, v) for u, v in loc], closed=True, n=6)
        fill = CREAM if kind == 'tabi' else self.skin
        rv = self.rimv(P, 3.5)
        s = rimlit(P, fill, (-rv[0], -rv[1])) + ring(P, 3.6, 5.0, seed=self.seed + 360 + seed)
        if kind == 'tabi':  # split-toe seam
            s += brush([W(0.62, 0.25), W(0.70, 0.12), W(0.72, 0.02)], 3.2, seed=self.seed + 370 + seed, taper=(0.1, 0.3))
        else:  # sole pad + toe bumps
            pad = catmull([W(-0.16, 0.05), W(0.30, 0.07), W(0.74, 0.06), W(0.74, 0.16), W(0.30, 0.17), W(-0.12, 0.20)], closed=True, n=5)
            s += f'<path d="{d_of(pad)}" fill="{SKIN_H}"/>'
            for tu in (0.80, 0.70):
                s += brush([W(tu, 0.01), W(tu + 0.03, 0.12)], 3.2, seed=self.seed + 372 + seed, taper=(0.2, 0.3))
        return s


# ---------------------------------------------------------------- Face + adult signals
class FaceS(Face):
    """Same head rig, plus the brief's added adult signals for Hiko and stick mooks:
    a light stubble band and a sideburn (drawn inside the head clip, under eyes/mouth)."""

    def wrinkles(self):
        s = Face.wrinkles(self)
        p = self.p
        if not p.get('stubble'):
            return s
        W, H = p['W'], p['H']
        cid = f'sb{uid()}'
        s += f'<clipPath id="{cid}"><path d="{d_of(self.head_shape())}"/></clipPath><g clip-path="url(#{cid})">'
        t = p['turn']
        band = catmull([(-W, 0.30 * H), (-0.30 * W, 0.24 * H), (t - 0.05 * W, 0.15 * H), (t + 0.28 * W, 0.14 * H),
                        (W, 0.10 * H), (W, H), (-W, H)], closed=True, n=6)
        s += f'<path d="{d_of(band)}" fill="#8E7470" opacity="0.22"/>'
        r = random.Random(p['seed'] + 900)
        for _ in range(34):
            x, y = r.uniform(-0.36 * W, 0.46 * W), r.uniform(0.24 * H, 0.47 * H)
            s += f'<circle cx="{f1(x)}" cy="{f1(y)}" r="1.9" fill="#6E5552" opacity="0.6"/>'
        sb = catmull([(-0.52 * W, -0.21 * H), (-0.40 * W, -0.21 * H), (-0.385 * W, -0.10 * H), (-0.41 * W, -0.03 * H),
                      (-0.50 * W, -0.05 * H)], closed=True, n=6)
        s += f'<path d="{d_of(sb)}" fill="#4B3030"/>'
        s += '</g>'
        return s


# ---------------------------------------------------------------- props
def temari(bx, by, br, seed=500, bell_side=1):
    """Red-and-white bell temari: VERM ball, CREAM spiral bands, brass bell."""
    o = []
    ball = ellipse(bx, by, br, br, n=56)
    o.append(f'<path d="{d_of(ball)}" fill="{VERM}"/>')
    for k in range(5):
        a0 = k * 72
        pts = []
        for i in range(13):  # spiral arm from centre outward
            t = i / 12
            a = math.radians(a0 + 110 * t)
            pts.append((bx + br * t * math.cos(a), by + br * t * math.sin(a)))
        o.append(brush(pts, br * 0.34, color=CREAM, taper=(0.35, 0.0), wmin=1.5, wob=0.3, seed=seed + k))
    cid = f'tm{uid()}'
    o.insert(1, f'<clipPath id="{cid}"><path d="{d_of(ball)}"/></clipPath><g clip-path="url(#{cid})">')
    o.append('</g>')
    o.append(f'<circle cx="{f1(bx)}" cy="{f1(by)}" r="{f1(br * 0.2)}" fill="{VERM}"/>')
    o.append(ring(ball, br * 0.2, br * 0.28, seed=seed + 9))
    bxx, byy = bx + bell_side * (br + 4), by + br * 0.55
    bell = ellipse(bxx, byy, br * 0.34, br * 0.31, n=30)
    o.append(filled(bell, BRASS, 4.5, 6, seed=seed + 11))
    o.append(brush([(bxx - br * 0.2, byy + 3), (bxx + br * 0.2, byy + 3)], 3, seed=seed + 12, taper=(0, 0)))
    return ''.join(o)


def star4(x, y, r, col=BRASS, seed=0):
    P = []
    for i in range(16):
        a = math.radians(i * 22.5 - 90)
        rr = r if i % 4 == 0 else (r * 0.42 if i % 2 == 0 else r * 0.36)
        P.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return filled(P, col, 3.5, 4.5, seed=seed)


def ting(x, y, s=1.0, seed=0, col=INK):
    """Bell 'ting': star glint + three short brush rays."""
    o = [star4(x, y, 15 * s, seed=seed)]
    for i, a in enumerate((-50, -15, 20)):
        p0 = pol((x, y), a - 20, 22 * s)
        p1 = pol((x, y), a - 20, 40 * s)
        o.append(brush([p0, p1], 6 * s, color=col, seed=seed + 3 + i, taper=(0.2, 0.3)))
    return ''.join(o)


def dotted(P, r0, r1, col=INK, gap=26):
    Q, L = resample(P, gap)
    out = []
    for i, q in enumerate(Q):
        t = i / max(1, len(Q) - 1)
        out.append(f'<circle cx="{f1(q[0])}" cy="{f1(q[1])}" r="{f1(r0 + (r1 - r0) * t)}" fill="{col}"/>')
    return ''.join(out)


def sensu(base, ang, ln, seed=0, wb=13, wt=24):
    """Closed folding fan: WOOD_D slat bundle, brush edge, brass rivet."""
    tip = pol(base, ang, ln)
    a = math.radians(ang)
    nx, ny = -math.sin(a), math.cos(a)
    P = [(base[0] + nx * wb / 2, base[1] + ny * wb / 2), (tip[0] + nx * wt / 2, tip[1] + ny * wt / 2),
         (tip[0] - nx * wt / 2, tip[1] - ny * wt / 2), (base[0] - nx * wb / 2, base[1] - ny * wb / 2)]
    s = filled(P, WOOD_D, 4.5, 6, seed=seed)
    for k in (-0.22, 0.18):
        s += brush([(base[0] + nx * wb * k, base[1] + ny * wb * k), (tip[0] + nx * wt * k * 1.3, tip[1] + ny * wt * k * 1.3)], 2.6,
                   color=INK, seed=seed + 2, taper=(0.1, 0.1))
    tp = [(tip[0] + nx * wt / 2, tip[1] + ny * wt / 2), pol(tip, ang, 6), (tip[0] - nx * wt / 2, tip[1] - ny * wt / 2)]
    s += brush(tp, 5, color=PLUM_L, seed=seed + 4, taper=(0.1, 0.1))
    r = pol(base, ang, 7)
    s += f'<circle cx="{f1(r[0])}" cy="{f1(r[1])}" r="5" fill="{BRASS}"/>'
    return s, tip


def chawan(cx, top, w=62, h=40, seed=0, steam=True, level=True):
    """Matcha bowl, rim exactly level, a wisp of steam."""
    P = catmull([(cx - w / 2, top), (cx + w / 2, top), (cx + w * 0.44, top + h * 0.55), (cx + w * 0.26, top + h * 0.92),
                 (cx - w * 0.26, top + h * 0.92), (cx - w * 0.44, top + h * 0.55)], closed=True, n=6)
    s = filled(P, CREAM, 5, 6.5, seed=seed)
    s += f'<ellipse cx="{f1(cx)}" cy="{f1(top + 1)}" rx="{f1(w / 2 - 6)}" ry="{f1(5)}" fill="{MATCHA}"/>'
    s += brush([(cx - w * 0.42, top + h * 0.40), (cx + w * 0.42, top + h * 0.40)], 4.5, color=VERM, seed=seed + 1, taper=(0.1, 0.1))
    if steam:
        for i, dx in enumerate((-9, 10)):
            pts = [(cx + dx, top - 10), (cx + dx + 9, top - 30), (cx + dx - 6, top - 52), (cx + dx + 5, top - 74)]
            s += brush(pts, 6, color=CREAM, seed=seed + 5 + i, taper=(0.3, 0.6), op=0.75)
    return s


def zabuton(cx, top, w, h, seed=0):
    P = catmull([(cx - w / 2, top + 8), (cx, top), (cx + w / 2, top + 8), (cx + w / 2 + 6, top + h - 8), (cx, top + h),
                 (cx - w / 2 - 6, top + h - 8)], closed=True, n=6)
    s = f'<ellipse cx="{f1(cx)}" cy="{f1(top + h + 6)}" rx="{f1(w * 0.56)}" ry="{f1(h * 0.42)}" fill="{INK}" opacity="0.35"/>'
    s += rimlit(P, '#5E3E62', (8, 3)) + ring(P, 7, 10, seed=seed)
    s += brush([(cx - w * 0.38, top + h * 0.55), (cx, top + h * 0.62), (cx + w * 0.38, top + h * 0.55)], 4, color=PLUM_D, seed=seed + 1)
    for tx in (cx - w / 2 + 4, cx + w / 2 - 4):  # corner tassels
        s += brush([(tx, top + 8), (tx + (8 if tx > cx else -8), top - 6)], 6, color=PLUM_L, seed=seed + 2)
    return s


def eri(nb, sh, hu, seed=0, twist=0.0):
    """White eri collar cross: two CREAM brush strokes in a V at the neck (twist shifts the crossing)."""
    s = ''
    wd = 0.11 * hu
    for k, (x0, side) in enumerate(((-wd * (1 - twist * 3), 1), (wd * (1 + twist * 2), -1))):
        p0 = (nb[0] + x0, nb[1] - 0.012 * hu)
        p1 = (sh[0] + side * 0.012 * hu + twist * hu, sh[1] + 0.05 * hu)
        ln = [p0, lerp(p0, p1, 0.5), p1]
        s += brush(ln, 0.062 * hu + 7, color=INK, taper=(0.0, 0.25), wmin=0.03 * hu + 5, seed=seed + k, wob=0.6)
        s += brush(ln, 0.062 * hu, color=CREAM, taper=(0.0, 0.25), wmin=0.03 * hu, seed=seed + k, wob=0.6)
    return s


def obi(J, hu, col=PLUM_L, bow_side=-1, seed=0, tails_swing=0.0, h_up=0.09, w=0.24, th=0.08):
    """Sash as a ring around the spine just above the hip; flat butterfly bow + two short tails at the back."""
    c = lerp(J['hip'], J['nb'], h_up / 0.9)
    d = ang_of(J['nb'], J['hip'])  # spine direction (down the body)
    a = d - 90                      # across the body
    hw, hh = w * hu / 2, th * hu / 2
    P = tube([pol(c, a, -hw), pol(c, a, hw)], 2 * hh, 2 * hh)
    bc = pol(c, a, bow_side * hw * 0.80)
    back = bow_side * 1.0
    s_back = ''
    t0 = bc
    t2 = pol(pol(bc, d, 0.13 * hu), a, bow_side * (0.025 + tails_swing) * hu)
    t1 = pol(lerp(t0, t2, 0.5), a, bow_side * 0.012 * hu)
    s_back += brush([t0, t1, t2], 0.05 * hu + 7, color=INK, seed=seed + 6, taper=(0.0, 0.12), wmin=0.035 * hu + 6, wob=0.5)
    s_back += brush([t0, t1, t2], 0.05 * hu, color=col, seed=seed + 6, taper=(0.0, 0.12), wmin=0.035 * hu, wob=0.5)
    for k, sg in enumerate((-1, 1)):
        q0 = pol(bc, d, sg * 0.006 * hu)
        q1 = pol(pol(bc, a, back * 0.11 * hu), d, sg * 0.062 * hu)
        q2 = pol(pol(bc, a, back * 0.145 * hu), d, sg * 0.018 * hu)
        q3 = pol(pol(bc, a, back * 0.05 * hu), d, sg * 0.012 * hu)
        lobe = catmull([q0, q1, q2, q3], closed=True, n=8)
        s_back += filled(lobe, col, 3.5, 4.5, seed=seed + 2 + k)
    s_front = f'<path d="{d_of(P)}" fill="{col}"/>' + ring(P, 4, 5.5, seed=seed + 1)
    s_front += brush([pol(c, a, -hw * 0.75), pol(c, a, hw * 0.75)], 3, color=PLUM_D, seed=seed + 9, taper=(0.1, 0.1))
    kq = [pol(pol(bc, a, u * 0.03 * hu), d, v * 0.042 * hu) for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    s_front += filled(catmull(kq, closed=True, n=4), col, 3.5, 4.5, seed=seed + 11)
    return s_back, s_front


def sash_tails(J, hu, col, trail_ang, seed=0, w=0.26, th=0.075):
    """Hiko's MATCHA_D sash: ring at the hip with two long tails streaming behind."""
    c = lerp(J['hip'], J['nb'], 0.07)
    d = ang_of(J['nb'], J['hip'])
    a = d - 90
    hw, hh = w * hu / 2, th * hu / 2
    P = tube([pol(c, a, -hw), pol(c, a, hw)], 2 * hh, 2 * hh)
    back = ''
    for k, (ln, off) in enumerate(((0.55, 10), (0.42, -12))):
        p0 = c
        p1 = pol(pol(c, trail_ang, ln * hu * 0.5), trail_ang + 90, off + 10)
        p2 = pol(pol(c, trail_ang, ln * hu), trail_ang + 90, off - 6)
        back += brush([p0, p1, p2], 0.055 * hu + 7, color=INK, seed=seed + k, taper=(0.0, 0.3), wmin=6)
        back += brush([p0, p1, p2], 0.055 * hu, color=col, seed=seed + k, taper=(0.0, 0.3), wmin=2)
    front = f'<path d="{d_of(P)}" fill="{col}"/>' + ring(P, 4, 5.5, seed=seed + 5)
    return back, front


def apron_flag(J, hu, facing=-1, seed=0):
    """Witness: small white apron flag hanging from the waist over the lap."""
    c = lerp(J['hip'], J['nb'], 0.10)
    f = facing
    P = catmull([(c[0] - f * 0.02 * hu, c[1] - 0.02 * hu), (c[0] + f * 0.20 * hu, c[1] - 0.01 * hu),
                 (c[0] + f * 0.34 * hu, c[1] + 0.13 * hu), (c[0] + f * 0.30 * hu, c[1] + 0.20 * hu),
                 (c[0] + f * 0.02 * hu, c[1] + 0.16 * hu)], closed=True, n=6)
    return filled(P, CREAM, 3.5, 4.5, seed=seed) + brush([(c[0] - f * 0.03 * hu, c[1]), (c[0] + f * 0.22 * hu, c[1] + 0.01 * hu)], 4, color=INK, seed=seed + 1, taper=(0.1, 0.1))


def broom(x, y0, y1, seed=0):
    s = filled([(x - 5, y0), (x + 5, y0), (x + 6, y1), (x - 6, y1)], BRASS, 4, 5, seed=seed)
    straw = catmull([(x - 20, y1 - 6), (x + 20, y1 - 6), (x + 36, y1 + 80), (x - 36, y1 + 80)], closed=True, n=4)
    s += filled(straw, '#C9A65A', 5, 6.5, seed=seed + 1)
    for k in range(4):
        s += brush([(x - 12 + k * 8, y1 + 8), (x - 20 + k * 14, y1 + 72)], 3, color='#8E6E2E', seed=seed + 2 + k, taper=(0.1, 0.3))
    s += brush([(x - 22, y1 + 10), (x + 22, y1 + 10)], 5, color=VERM, seed=seed + 8, taper=(0, 0))
    return s


def swoosh(base, ang, r, a0, a1, n=2, gap=16, w=6, col=PLUM_L, seed=0, op=0.8):
    """Short parallel motion arcs (an arc of radius r about `base` from angle a0 to a1)."""
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
    return filled(P, col, 3, 4, seed=seed)


# ---------------------------------------------------------------- the master (shared by scene + sheet)
def master_figure(cx, cy, face_kw, pose, k=1.0, light=(120, 610), seed=0, fan=None, cup=True, extra_marks=''):
    """Returns (svg, J, info). The head is the original rig; the body is the stick rig.
    face_kw: expression dict. pose: Stick pose dict (+ prop states). k: figure scale."""
    face = Face(seed=11, scale=k, eye_th=16, **face_kw)
    anchor = anchor_of(face, cx, cy)
    hu = 350 * k
    st = Stick(hu, light, skin=SKIN_M, w=(16, 12), ws=17, seed=seed, ua=0.57, fa=0.53, th=0.66, sn=0.60)
    lift = face.p['lift']
    J = st.solve((anchor[0], anchor[1] + lift), pose)
    J['anchor'] = anchor  # spine/neck stroke reaches the lifted pivot: neck stretches by `lift`
    o = {key: '' for key in ('far_leg', 'far_arm', 'spine', 'back', 'head', 'front', 'near_leg', 'near_arm', 'hand', 'marks')}
    # legs (seiza fold): far leg slightly up/back so two legs read
    o['far_leg'] = st.leg(J, 'f', seed=1) + st.foot(J['an_f'], pose.get('toe_f', 186), 'bare', facing=1, seed=1)
    o['near_leg'] = st.leg(J, 'n', seed=2) + st.foot(J['an_n'], pose.get('toe_n', 180), 'bare', facing=1, seed=2)
    # far arm = cup arm (lantern side)
    cup_ang = pose.get('cup_hand_ang', -90)
    o['far_arm'] = st.arm(J, 'f', seed=3) + st.mitten(J['wr_f'], cup_ang, seed=3)
    o['spine'] = st.spine(J, seed=4)
    tw = pose.get('twist', 0.0)
    ob_back, ob_front = obi(J, hu, bow_side=-1, seed=40 + seed, tails_swing=pose.get('obi_swing', 0.0), w=0.24 * (1 - 1.4 * abs(tw)))
    o['back'] = ob_back + eri(J['nb'], J['sh'], hu, seed=60 + seed, twist=tw) + ob_front
    o['head'] = face.svg(cx, cy)
    # near arm = fan arm
    fan_hand_ang = pose.get('fan_hand_ang', ang_of(J['el_n'], J['wr_n']))
    o['near_arm'] = st.arm(J, 'n', seed=5) + st.mitten(J['wr_n'], fan_hand_ang, seed=5)
    info = {'anchor': anchor, 'face': face}
    # hand props
    if fan is not None:
        fb = st.hand_pt(J['wr_n'], fan_hand_ang, 0.55, 0.0)
        fs, tip = sensu(fb, fan, 0.40 * hu, seed=80 + seed, wb=0.036 * hu + 2, wt=0.066 * hu + 2)
        o['hand'] += fs
        o['hand'] += st.thumb(st.hand_pt(J['wr_n'], fan_hand_ang, 0.45, -0.45), fan_hand_ang + 160 * (1 if pose.get('thumb_n', 1) > 0 else -1) - 70, seed=7)
        info['fan_tip'] = tip
        info['fan_base'] = fb
    if cup:
        hp = st.hand_pt(J['wr_f'], cup_ang, 0.62, 0.0)
        cw = 0.19 * hu
        top = hp[1] - 0.115 * hu
        o['hand'] += chawan(hp[0], top, w=cw, h=0.12 * hu, seed=90 + seed, steam=pose.get('steam', True))
        o['hand'] += st.thumb(st.hand_pt(J['wr_f'], cup_ang, 0.70, 0.55), cup_ang - 35, ln=0.045 * hu, seed=9)
        info['cup'] = (hp[0], top)
    o['marks'] = extra_marks
    order = ('far_leg', 'far_arm', 'spine', 'back', 'head', 'front', 'near_leg', 'near_arm', 'hand', 'marks')
    return ''.join(o[kk] for kk in order), J, info


# ---------------------------------------------------------------- scene background (from the original design)
LANTERN = (112, 545)


def scene_bg(o, W=1080, H=1920):
    o.append(f'<defs><clipPath id="wall"><rect x="0" y="230" width="{W}" height="1345"/></clipPath></defs>')
    o.append(f'<rect width="{W}" height="{H}" fill="{PLUM}"/>')
    FLOOR = 1250
    sx0, sx1, sy0, sy1 = 262, 1080, 300, 1176
    o.append(f'<rect x="{sx0}" y="{sy0}" width="{sx1 - sx0}" height="{sy1 - sy0}" fill="{MOON}"/>')
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
    o.append(f'<rect x="{sx0 - 10}" y="{sy1 + 14}" width="{sx1 - sx0 + 20}" height="{FLOOR - sy1 - 14}" fill="{PLUM_L}"/>')
    o.append(f'<rect x="{sx0 - 40}" y="230" width="40" height="{FLOOR - 230}" fill="{PLUM_D}"/>')
    o.append(f'<rect x="0" y="230" width="{W}" height="36" fill="{PLUM_D}"/>')
    gx, gy = 170, 780
    o.append('<g clip-path="url(#wall)">')
    for r, op in ((470, 0.10), (350, 0.12), (230, 0.15)):
        o.append(f'<circle cx="{gx}" cy="{gy}" r="{r}" fill="{AMBER}" opacity="{op}"/>')
    o.append('</g>')
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="{1575 - FLOOR}" fill="{TATAMI}"/>')
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="10" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M0 1400 L{W} 1388 L{W} 1400 L0 1413 Z" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M700 {FLOOR} L712 {FLOOR} L780 1575 L766 1575 Z" fill="{TATAMI_D}"/>')
    o.append(f'<ellipse cx="220" cy="1440" rx="320" ry="80" fill="{AMBER}" opacity="0.12"/>')
    o.append(f'<rect x="0" y="0" width="{W}" height="230" fill="{PLUM_D}"/>')
    lx, ly = LANTERN
    o.append(brush([(lx, 266), (lx + 1, ly - 100)], 6, seed=301, taper=(0, 0)))
    lant = ellipse(lx, ly, 70, 96, n=60)
    o.append(filled(lant, AMBER, 8, 11, seed=302))
    for kk in (-60, -30, 0, 30, 60):
        hw = 70 * math.sqrt(max(0, 1 - (kk / 96) ** 2))
        o.append(brush([(lx - hw + 6, ly + kk), (lx, ly + kk + 8), (lx + hw - 6, ly + kk)], 4, color='#C98A2E', seed=310 + kk, taper=(0.2, 0.2)))
    o.append(filled([(lx - 40, ly - 112), (lx + 40, ly - 112), (lx + 44, ly - 88), (lx - 44, ly - 88)], INK, 4, 6, seed=303))
    o.append(filled([(lx - 40, ly + 88), (lx + 40, ly + 88), (lx + 36, ly + 110), (lx - 36, ly + 110)], INK, 4, 6, seed=304))
    # low shelf + teapot at far left
    o.append(filled([(-30, 1300), (150, 1300), (162, 1334), (-30, 1334)], WOOD, 7, 9, seed=320))
    o.append(filled([(110, 1334), (134, 1334), (134, 1430), (110, 1430)], WOOD_D, 6, 8, seed=321))
    pot = catmull([(14, 1300), (4, 1262), (34, 1230), (76, 1232), (96, 1264), (88, 1300)], closed=True, n=8)
    o.append(filled([(10, 1266), (-26, 1236), (-20, 1228), (14, 1250)], PLUM_L, 6, 8, seed=322))
    o.append(filled(pot, PLUM_L, 7, 9, seed=323))
    o.append(filled(ellipse(52, 1226, 18, 7, n=24), PLUM_L, 5, 6, seed=324))
    o.append(f'<circle cx="52" cy="1214" r="7" fill="{INK}"/>')
    o.append(brush([(24, 1262), (52, 1270), (80, 1262)], 4, color=BRASS, seed=325, taper=(0.1, 0.1)))
    o.append(f'<rect x="0" y="1575" width="{W}" height="{H - 1575}" fill="{TATAMI_D}"/>')


# ---------------------------------------------------------------- SCENE
SCENE_LIGHT = LANTERN


def scene_svg():
    W, H = 1080, 1920
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    scene_bg(o)

    # ---------------- MASTER: seiza on the zabuton, smug head-dodge
    mcx, mcy = 326, 816
    o.append(zabuton(338, 1352, 380, 54, seed=400))
    smug = dict(eyes='u', mouth='smirk', tilt=-20, beard='forward', m_dx=8, fdy=-10, lift=6)
    pose = dict(neck_ang=70, neck=0.07, spine_ang=92, spine=0.87, bow=-0.06, sh=0.14,
                hand_f=(-0.45, -0.04), elb_f=-1,          # cup held out level on the lantern side
                hand_n=(0.36, -0.62), elb_n=1,            # fan arm: just flicked up
                foot_f=(0.0, 0.2), kn_f=-1, foot_n=(0.02, 0.20), kn_n=-1, far_leg_off=(-0.05, -0.035),
                cup_hand_ang=-12, fan_hand_ang=-100, thumb_n=1)
    msvg, MJ, minfo = master_figure(mcx, mcy, smug, pose, k=1.0, light=SCENE_LIGHT, fan=-97)
    o.append(msvg)

    # ---------------- BALL + flick story: fan-tip whip arc, dotted ball trail, bell ting
    clap = (634, 890)
    ft = minfo['fan_tip']
    fb = minfo['fan_base']
    o.append(swoosh(fb, 0, 0.40 * 350 + 2, -8, -74, n=2, gap=22, w=8, col=PLUM_L, seed=520, op=0.8))
    bx, by, br = 520, 520, 36
    o.append(dotted(qbez((clap[0] - 4, clap[1] - 92), (clap[0] + 22, by + 60), (bx + 44, by + 30), 30), 3.5, 6.5, gap=30))
    o.append(temari(bx, by, br, seed=500, bell_side=1))
    o.append(ting(bx + br + 34, by + 4, 0.95, seed=540))

    # ---------------- WITNESS: tea-house woman kneeling by the shoji, deadpan sigh
    wcx, wcy = 880, 1046
    wk = 0.50
    wface = Face(seed=51, scale=wk, skin='#D49C76', skin_d='#B9825E', facing=-1, tilt=4, turn=6, hair='scarf', beard=None,
                 wrinkles=False, eyes='sag', eye_th=24, mouth='flat', m_w=66, m_rot=-6, m_dy=-4, outline=(20, 24), rim=8)
    wanc = anchor_of(wface, wcx, wcy)
    whu = 350 * wk
    wst = Stick(whu, SCENE_LIGHT, skin='#D49C76', w=(12, 9.5), ws=12, rimd=4.0, seed=700, facing=-1, ua=0.56, fa=0.52, th=0.66, sn=0.60)
    wpose = dict(neck_ang=94, neck=0.07, spine_ang=88, spine=0.86, bow=0.05, sh=0.14,
                 hand_f=(0.50, -0.20), elb_f=1,            # far hand on the broom handle
                 hand_n=(-0.50, 0.52), elb_n=1,            # near hand resting on the knee
                 foot_f=(-0.01, 0.15), kn_f=1, foot_n=(-0.03, 0.17), kn_n=1)
    WJ = wst.solve(wanc, wpose)
    o.append(f'<ellipse cx="{f1(WJ["hip"][0] - 30)}" cy="{f1(WJ["hip"][1] + 40)}" rx="95" ry="11" fill="{INK}" opacity="0.30"/>')
    bxw = WJ['wr_f'][0] + 4
    o.append(broom(bxw, 830, 1250, seed=760))
    o.append(wst.leg(WJ, 'f', seed=1) + wst.foot(WJ['an_f'], 0, 'tabi', facing=-1, seed=1))
    o.append(wst.spine(WJ, seed=2))
    o.append(wface.svg(wcx, wcy))
    o.append(wst.leg(WJ, 'n', seed=3) + wst.foot(WJ['an_n'], 0, 'tabi', facing=-1, seed=3))
    o.append(apron_flag(WJ, whu, facing=-1, seed=720))
    o.append(wst.arm(WJ, 'f', seed=4) + wst.mitten(WJ['wr_f'], -90, seed=4))
    o.append(wst.thumb(wst.hand_pt(WJ['wr_f'], -90, 0.5, -0.5), 180, seed=4))
    o.append(wst.arm(WJ, 'n', seed=5) + wst.mitten(WJ['wr_n'], 175, seed=5))
    puff = [ellipse(786, 1082, 18, 15, n=24), ellipse(764, 1072, 15, 12, n=24), ellipse(770, 1096, 13, 11, n=24)]
    o.append(union(puff, CREAM, 7, 9, seed=708))

    # ---------------- HIKO: frozen mid-dive, claps on empty air where the ball was
    hcx, hcy = 826, 450
    hface = FaceS(seed=31, W=205, H=326, skin=SKIN_H, skin_d=SKIN_H_D, facing=-1, tilt=12, turn=8, hair='hiko', beard=None,
                  wrinkles=False, nose=True, eyes='chev', mouth='wavy', m_w=118, eye_sp=86, eye_len=62, eye_th=16, stubble=True,
                  marks=(('sweat', -196, -150, 24, -40), ('sweat', 150, -150, 22, 30)), mark_col=INK)
    hanc = anchor_of(hface, hcx, hcy)
    hhu = 326
    hst = Stick(hhu, SCENE_LIGHT, skin=SKIN_H, w=(16, 12), ws=17, rimd=4.5, seed=600, facing=-1, ua=0.54, fa=0.52, th=0.65, sn=0.60)
    hnb = pol(hanc, 58, 0.17 * hhu)
    hpose = dict(neck_ang=58, neck=0.10, hip=(1012, 462), ctrl=pol(hnb, 58, 112), sh=0.15,
                 handw_n=(clap[0] + 24, clap[1] + 14), elb_n=-1,
                 handw_f=(clap[0] + 34, clap[1] - 12), elb_f=-1,
                 foot_n=(1.25, -0.40), kn_n=1, foot_f=(0.70, -1.02), kn_f=1,
                 kneew_f=(1050, 262), shin_ang_f=-12)
    HJ = hst.solve(hanc, hpose)
    da = ang_of(HJ['nb'], HJ['hip'])
    o.append(f'<ellipse cx="800" cy="1468" rx="170" ry="15" fill="{INK}" opacity="0.22"/>')
    # speed lines along the dive
    for i, (off, x0, ln) in enumerate(((-120, 880, 260), (95, 930, 240), (180, 820, 200))):
        p0 = pol(pol(HJ['hip'], da + 90, off), da + 180, 1080 - x0 - 120)
        o.append(brush([p0, pol(p0, da, ln)], 7, color=PLUM, seed=330 + i, taper=(0.7, 0.0), op=0.45))
    sb, sf = sash_tails(HJ, hhu, MATCHA_D, trail_ang=da + 12, seed=650)
    o.append(hst.leg(HJ, 'f', seed=1))
    o.append(hst.arm(HJ, 'f', seed=2))
    fa_ang = ang_of(HJ['el_f'], HJ['wr_f'])
    o.append(union(hand_open(HJ['wr_f'][0], HJ['wr_f'][1], fa_ang, 0.80, spread=0.30, seed=611), SKIN_H, 6, 7.5, seed=612))
    o.append(hst.spine(HJ, seed=3))
    o.append(sb)
    o.append(hface.svg(hcx, hcy))
    o.append(sf)
    o.append(hst.leg(HJ, 'n', seed=4))
    o.append(hst.arm(HJ, 'n', seed=5))
    na_ang = ang_of(HJ['el_n'], HJ['wr_n'])
    o.append(union(hand_open(HJ['wr_n'][0], HJ['wr_n'][1], na_ang, 0.82, spread=0.30, seed=631), SKIN_H, 6, 7.5, seed=632))
    # clap emanata just past the fingertips
    tip = pol(HJ['wr_n'], na_ang, 70)
    o.append(emanata_at(tip[0], tip[1], na_ang, 1.0, col=INK, seed=680, n=5, spread=32, r0=16, r1=44, w=7))

    o.append('</svg>')
    return '\n'.join(o)


# ---------------------------------------------------------------- POSES SHEET
def poses_svg():
    W, H = 1080, 1080
    k = 0.78
    hu = 350 * k
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{PLUM}"/>']
    FL = 900
    o.append(f'<rect x="0" y="{FL}" width="{W}" height="{H - FL}" fill="{TATAMI}"/>')
    o.append(f'<rect x="0" y="{FL}" width="{W}" height="8" fill="{TATAMI_D}"/>')
    o.append(f'<rect x="0" y="1012" width="{W}" height="10" fill="{TATAMI_D}"/>')

    def halo(cx, cy):
        return (f'<circle cx="{cx}" cy="{cy}" r="176" fill="{AMBER}" opacity="0.13"/>'
                f'<circle cx="{cx}" cy="{cy}" r="126" fill="{AMBER}" opacity="0.12"/>')

    cush_top = 930

    def seat_cy(lift, neck_ang=90, extra=0, spine=0.87):
        hip_y = cush_top - 0.20 * hu - extra
        nb_y = hip_y - spine * hu
        anc_y = nb_y - 0.14 * hu * math.sin(math.radians(neck_ang))
        return anc_y - 0.42 * 350 * k

    # (1) READY STANCE ------------------------------------------------
    cx1 = 150
    o.append(halo(176, 520))
    o.append(zabuton(cx1 + 40, cush_top, 290, 46, seed=410))
    neutral = dict(eyes='flat', mouth='flat', m_w=60, tilt=12)
    p1 = dict(neck_ang=100, spine_ang=89, spine=0.87, bow=0.03, sh=0.14,
              hand_f=(-0.32, -0.10), elb_f=-1, hand_n=(0.62, -0.16), elb_n=1,
              foot_f=(0.0, 0.2), foot_n=(0.02, 0.20), far_leg_off=(-0.05, -0.035), cup_hand_ang=-15, fan_hand_ang=-95)
    cy1 = seat_cy(0, 100)
    s1, J1, i1 = master_figure(cx1, cy1, neutral, p1, k=k, light=(cx1 - 600, cy1 - 300), seed=0, fan=-91)
    o.append(s1)
    ftp = i1['fan_tip']
    o.append(temari(ftp[0] + 1, ftp[1] - 25, 25, seed=560, bell_side=1))

    # (2) SIGNATURE: FAN FLICK ----------------------------------------
    cx2 = 482
    o.append(halo(532, 520))
    o.append(zabuton(cx2 + 48, cush_top, 290, 46, seed=420))
    smug = dict(eyes='u', mouth='smirk', tilt=-13, beard='forward', m_dx=8, fdy=-10, lift=6)
    p2 = dict(neck_ang=76, spine_ang=77, spine=0.87, bow=-0.15, sh=0.14,
              hand_f=(-0.32, -0.10), elb_f=-1,
              hand_n=(0.58, -0.84), elb_n=1,
              foot_f=(-0.02, 0.2), foot_n=(-0.01, 0.20), far_leg_off=(-0.05, -0.035), cup_hand_ang=-15, fan_hand_ang=-66, obi_swing=0.05,
              twist=0.05)
    cy2 = seat_cy(6, 78)
    s2, J2, i2 = master_figure(cx2, cy2, smug, p2, k=k, light=(cx2 - 600, cy2 - 300), seed=10, fan=-64)
    ft2 = i2['fan_tip']
    o.append(swoosh(J2['sh'], -10, 0.78 * hu, 2, -40, n=2, gap=20, w=7, col=CREAM, seed=570, op=0.7))
    o.append(s2)
    bx2, by2 = ft2[0] - 22, ft2[1] - 196
    o.append(dotted(qbez((ft2[0] + 2, ft2[1] - 28), (ft2[0] + 22, (ft2[1] + by2) / 2), (bx2 + 12, by2 + 36), 20), 3, 5.5, col=CREAM, gap=24))
    o.append(temari(bx2, by2, 25, seed=580, bell_side=-1))
    o.append(ting(bx2 + 44, by2 - 4, 0.72, seed=590, col=CREAM))

    # (3) BIG REACTION: SEIZA HOP -------------------------------------
    cx3 = 892
    o.append(halo(900, 470))
    o.append(zabuton(cx3 + 30, cush_top, 290, 46, seed=430))
    hop = 90
    surprised = dict(eyes='circle', mouth='o', tilt=0, lift=15, beard='flick', turn=0, circ_sp=112, circ_r=47,
                     marks=(('emanata', 'sides'),), wrinkles=True, mark_col=CREAM)
    p3 = dict(neck_ang=90, spine_ang=90, spine=0.87, bow=0.0, sh=0.14,
              hand_f=(-0.57, -0.30), elb_f=-1, hand_n=(0.52, -0.62), elb_n=1,
              foot_f=(0.0, 0.2), kn_f=-1, foot_n=(0.02, 0.20), kn_n=-1, far_leg_off=(-0.05, -0.035),
              cup_hand_ang=-100, fan_hand_ang=-80, steam=False)
    cy3 = seat_cy(15, 90, extra=hop)
    o.append(f'<ellipse cx="{cx3 + 30}" cy="{cush_top + 8}" rx="100" ry="10" fill="{INK}" opacity="0.45"/>')
    for i, dx in enumerate((-30, 40, 110)):
        o.append(brush([(cx3 + dx, cush_top - 16), (cx3 + dx, cush_top - 54)], 6, color=CREAM, seed=595 + i, taper=(0.2, 0.3), op=0.8))
    s3, J3, i3 = master_figure(cx3, cy3, surprised, p3, k=k, light=(cx3 - 600, cy3 - 300), seed=20, fan=-98)
    o.append(s3)
    cpx, cpy = i3['cup']
    o.append(dotted(qbez((cpx - 8, cpy - 8), (cpx - 40, cpy - 120), (cpx - 2, cpy - 30), 12), 2.4, 2.4, col=CREAM, gap=15))
    for i, (dx, dy, sz) in enumerate(((-30, -88, 9), (-17, -62, 8.5), (-5, -34, 8))):
        o.append(drop(cpx + dx, cpy + dy, sz, ang=180, seed=600 + i))
    o.append(temari(cx3 + 6, 118, 25, seed=610, bell_side=1))
    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(scene_svg())
    with open(os.path.join(HERE, 'poses.svg'), 'w') as fh:
        fh.write(poses_svg())
    print('ok')
