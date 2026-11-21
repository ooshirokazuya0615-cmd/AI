#!/usr/bin/env python3
"""Squint House / 糸目の茶屋 -- BIG-EYE version (Tama = hero, Hiko = partner).

One face rig  : BigFace(D, who, facing, rot, turn, far_k, expr)  -> head SVG; the same eye routine draws
                Tama's closed arcs / pop circles, Hiko's wide ovals and the cameo eye.
One body rig  : skeleton() + Body (stick limbs, neck stub, mittens) + costume panels (haori / samue).
Outputs       : scene.svg, faces.svg, hero.svg, partner.svg (+ silhouettes for the phone test).
Run           : python3 make.py raw  (writes the silhouettes used to measure the lineup height), render them,
                then python3 make.py.
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


# =====================================================================
# BIG-EYE PALETTE ADDITIONS
# =====================================================================
HAORI = '#6E3A63'
HAORI_D = '#4E2547'
HAORI_L = '#8C5583'
OBI_P = '#5B3E95'
KIMONO = '#8A7B69'
TENUGUI = '#3F5F8F'
TENUGUI_D = '#2E4870'
PERS = '#D9692D'
PERS_D = '#A1461A'
PERS_L = '#F08A4A'
JIKA = '#2C3352'
BUZZ = '#4B3B35'
HAIR_K = '#2A1E1A'
BROW_W = '#F4F0E6'
MOUTH_IN = '#4A1D26'
TONGUE = '#C55E58'
TEETH = '#FBF6EA'
CUP = '#EDE6D3'
CUP_BAND = '#34507E'
TEA = '#9DAF5E'


def blend(c1, c2, t):
    a = [int(c1.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(c2.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def P_(P, fill, extra=''):
    return f'<path d="{d_of(P)}" fill="{fill}"{extra}/>'


# =====================================================================
# BIG-EYE FACE RIG
# =====================================================================
# Character constants (all in D = skull diameter). Eye height = white shape at widest resting opening.
CHAR = {
    'tama': dict(skin=SKIN_M, lidtone=blend(SKIN_M, '#F2CFA8', 0.30), eye_h=0.36, eye_w=0.36, eye_h_pop=0.38, eye_w_pop=0.36,
                 gap=0.11, eye_y=-0.04, pupil=0.12, rim=0.021, lidw=0.033, ear='long', brow='tuft', nose='round', hair='tenugui',
                 jaw=0.21, age=True, stubble=False, mouth_y=0.285),
    'hiko': dict(skin=SKIN_H, lidtone=blend(SKIN_H, '#C98A68', 0.35), eye_h=0.30, eye_w=0.36, eye_h_pop=0.30, eye_w_pop=0.36,
                 gap=0.10, eye_y=-0.035, pupil=0.115, rim=0.021, lidw=0.032, ear='std', brow='kink', nose='tri', hair='buzz',
                 jaw=0.0, age=False, stubble=True, mouth_y=0.29),
    'cameo': dict(skin=SKIN_W, lidtone=blend(SKIN_W, '#F0C8A0', 0.25), eye_h=0.27, eye_w=0.25, eye_h_pop=0.27, eye_w_pop=0.25,
                  gap=0.12, eye_y=-0.04, pupil=0.10, rim=0.02, lidw=0.03, ear='small', brow='thin', nose='button', hair='bun',
                  jaw=0.16, age=True, stubble=False, mouth_y=0.27),
}

EXPR_DEF = dict(
    mode=('open', 'open'),          # per eye (near, far): 'open' | 'closed' | 'pop'
    lid=(None, None),               # upper-lid coverage at the eye centre (0 = none, 1 = shut); None = character rest
    tilt=(0.0, 0.0),                # lid tilt, deg; + = inner corner down (cross), - = inner corner up (worried)
    arch=(0.14, 0.14),              # upper-lid arch (0 = flat visor)
    low=(0.0, 0.0),                 # lower-lid coverage
    lowarch=(0.0, 0.0),
    closed=('u', 'u'),              # closed-arc kind: 'u' = contented sleep curve, 'n' = bliss/smile curve
    gaze=(0.0, 0.0), look=None, gmag=1.0,
    pupil=None,                     # pupil diameter in D (None = character default)
    brow_dy=(0.0, 0.0), brow_ang=(0.0, 0.0), brow_bend=(0.0, 0.0),
    mouth='rest', m_dx=0.0, m_dy=0.0, m_rot=0.0, m_w=None,
    marks=(), mark_col=INK, cheek_push=(0.0, 0.0), squash=0.0,
)

REST_LID = {'tama': 1.0, 'hiko': 0.15, 'cameo': 0.70}


class BigFace:
    """One rig for every big-eyed round head. Local frame: origin = skull centre, +x = facing side,
    y down, units px (D = skull diameter). Group transform: translate(cx cy) rotate(rot) scale(facing 1)."""

    def __init__(self, D, who, facing=1, rot=0.0, turn=0.12, far_k=0.76, light=(-0.8, -0.6), expr=None,
                 front_ear=False, seed=11, world=None):
        self.D, self.who, self.facing, self.rot, self.turn, self.far_k = D, who, facing, rot, turn, far_k
        self.c = dict(CHAR[who])
        self.e = dict(EXPR_DEF)
        if expr:
            self.e.update(expr)
        self.front_ear = front_ear
        self.seed = seed
        self.skin = self.c['skin']
        self.skin_d = shade(self.skin, 0.13)
        self.skin_dd = shade(self.skin, 0.30)
        self.world_c = world   # (cx, cy) world position, needed for look-at
        lx, ly = light
        lx, ly = rot2((lx, ly), -rot)
        lx *= facing
        l = math.hypot(lx, ly) or 1
        self.L = (lx / l, ly / l)

    # ---------------------------------------------------------- helpers
    def per(self, key, i):
        v = self.e[key]
        if isinstance(v, (tuple, list)):
            return v[i]
        return v

    def to_local(self, wp):
        cx, cy = self.world_c
        x, y = wp[0] - cx, wp[1] - cy
        x, y = rot2((x, y), -self.rot)
        return (x * self.facing, y)

    def eye_layout(self):
        """Centres from the widest (pop) sizes so the inner gap never drops under the minimum."""
        c, D = self.c, self.D
        cx = self.turn * D
        Wn = c['eye_w_pop'] * D
        Wf = Wn * self.far_k
        g = c['gap'] * D
        ey = c['eye_y'] * D
        return [(cx - g / 2 - Wn / 2, ey, 1.0), (cx + g / 2 + Wf / 2, ey, self.far_k)]

    # ---------------------------------------------------------- eye
    def eye(self, i):
        """i = 0 near eye (full width, toward the back of the head), 1 far eye (compressed, toward the facing rim)."""
        c, e, D = self.c, self.e, self.D
        ex, ey, k = self.eye_layout()[i]
        inner = 1 if i == 0 else -1          # +x points toward the nose for the near eye
        mode = self.per('mode', i)
        if mode == 'pop':
            w, h = c['eye_w_pop'] * D * k, c['eye_h_pop'] * D
        else:
            w, h = c['eye_w'] * D * k, c['eye_h'] * D
        rx, ry = w / 2, h / 2
        lid = self.per('lid', i)
        if lid is None:
            lid = REST_LID[self.who]
        if mode == 'pop':
            lid = min(lid, 0.02)
        tilt = self.per('tilt', i)
        arch = self.per('arch', i)
        low, lowarch = self.per('low', i), self.per('lowarch', i)
        tt = math.tan(math.radians(tilt))
        if mode == 'closed':
            kind = self.per('closed', i)
            if kind == 'u':
                def ylid(x):
                    return ry * (0.06 + 0.34 * (1 - (x / rx) ** 2)) + tt * x * inner
            else:
                def ylid(x):
                    return ry * (0.42 - 0.36 * (1 - (x / rx) ** 2)) + tt * x * inner
        else:
            y0 = -ry + 2 * ry * lid + arch * ry

            def ylid(x):
                return y0 - arch * ry * (1 - (x / rx) ** 2) + tt * x * inner
        yl0 = ry - 2 * ry * low + lowarch * ry

        def ylow(x):
            return yl0 - lowarch * ry * (1 - (x / rx) ** 2)
        N = 90
        xs = [-rx * math.cos(math.pi * j / N) for j in range(N + 1)]
        cov, vis, top_line = [], [], []
        for x in xs:
            s = math.sqrt(max(0.0, 1 - (x / rx) ** 2))
            et, eb = -ry * s, ry * s
            lt, lb = ylid(x), ylow(x)
            if min(lt, eb) > et:
                cov.append((x, et, min(lt, eb)))
            a2, b2 = max(et, lt), min(eb, lb)
            if b2 > a2:
                vis.append((x, a2, b2))
            top_line.append((x, min(max(lt, et), min(eb, lb)) if mode != 'closed' else min(max(lt, et), eb)))
        out = []
        W = lambda x, y: (ex + x, ey + y)
        # 1 lid-tone footprint (covered part of the socket)
        if cov:
            Pc = [W(x, a) for x, a, b in cov] + [W(x, b) for x, a, b in cov[::-1]]
            out.append(P_(Pc, c['lidtone']))
        # 2 white + pupil
        if vis and mode != 'closed':
            Pv = [W(x, a) for x, a, b in vis] + [W(x, b) for x, a, b in vis[::-1]]
            out.append(P_(Pv, EYEW))
            pr = (self.e['pupil'] or c['pupil']) * D / 2
            if isinstance(self.e['pupil'], (tuple, list)):
                pr = self.e['pupil'][i] * D / 2
            gx, gy = self.gaze_for(i, ex, ey)
            a, b = rx - 0.42 * pr, ry - 0.42 * pr
            m = math.hypot(gx, gy)
            if m > 1e-6:
                t = 1.0 / math.sqrt((gx / m / a) ** 2 + (gy / m / b) ** 2)
                px, py = ex + gx / m * t * min(1.0, m), ey + gy / m * t * min(1.0, m)
            else:
                px, py = ex, ey
            cid = f'ev{uid()}'
            out.append(f'<clipPath id="{cid}"><path d="{d_of(Pv)}"/></clipPath>')
            out.append(f'<g clip-path="url(#{cid})"><circle cx="{f1(px)}" cy="{f1(py)}" r="{f1(pr)}" fill="{INK}"/></g>')
            # lower rim (thin) along the visible bottom, inner -> outer
            bot = [W(x, b) for x, a, b in vis]
            if inner < 0:
                bot = bot[::-1]
            rw = c['rim'] * D * (1.15 if low > 0.05 else 1.0)
            out.append(brush(bot, rw, seed=self.seed + 30 + i, taper=(0.12, 0.12), wmin=rw * 0.45, wob=0.4))
        # 3 crease along the covered socket top / lid-jump crease on a pop
        cr = 0.016 * D
        if mode == 'pop':
            arc = [W(rx * 1.05 * math.cos(a), -ry * 1.05 * math.sin(a) - 0.045 * D) for a in [math.radians(d) for d in range(150, 29, -12)]]
            out.append(brush(arc, cr, color=self.skin_dd, seed=self.seed + 40 + i, taper=(0.3, 0.3), wmin=1.0, wob=0.3))
        elif cov:
            arc = [W(x * 1.03, a - 0.012 * D) for x, a, b in cov if abs(x) < rx * 0.93]
            if len(arc) > 3:
                out.append(brush(arc, cr, color=self.skin_dd, seed=self.seed + 40 + i, taper=(0.25, 0.25), wmin=1.0, wob=0.3))
        # 4 the upper lid line: thickest, darkest mark on the face; inner end tapers, outer end carries the lash tick
        TL = [W(x, y) for x, y in top_line]
        if inner < 0:
            TL = TL[::-1]
        lw = c['lidw'] * D
        out.append(brush(TL, lw, seed=self.seed + 50 + i, taper=(0.16, 0.04), wmin=lw * 0.35, wob=0.4))
        oc = TL[-1]
        out_dir = -inner
        if mode == 'closed':
            tick = [oc, (oc[0] + out_dir * 0.035 * D, oc[1] + 0.03 * D)]
        else:
            tick = [oc, (oc[0] + out_dir * 0.04 * D, oc[1] - 0.022 * D)]
        out.append(brush(tick, lw * 0.85, seed=self.seed + 55 + i, taper=(0.0, 0.7), wmin=1.2, smooth=False))
        # 5 age marks: crow's feet at the outer corner, lower-lid bag arc
        if c['age']:
            cf = (ex - inner * (rx + 0.02 * D), ey + 0.005 * D)
            base_a = 0 if out_dir > 0 else 180
            for j, (a, st, ln) in enumerate(((-34, 0.030, 0.050), (0, 0.016, 0.062), (30, 0.030, 0.048))):
                aa = base_a + (a if out_dir > 0 else -a)
                q0 = pol(cf, aa, st * D)
                q1 = pol(cf, aa, (st + ln) * D)
                out.append(brush([q0, q1], 0.017 * D, color=self.skin_dd, seed=self.seed + 60 + j + 5 * i, taper=(0.35, 0.45), wmin=1.0, smooth=False))
            bag_y = ry + 0.035 * D if mode != 'closed' else ry * 0.72 + 0.03 * D
            bag = [W(x, bag_y + 0.015 * D * (1 - (x / rx) ** 2) - 0.015 * D) for x in [rx * t for t in (-0.6, -0.3, 0.0, 0.3, 0.6)]]
            if inner < 0:
                bag = bag[::-1]
            out.append(brush(bag, 0.016 * D, color=self.skin_dd, seed=self.seed + 70 + i, taper=(0.4, 0.4), wmin=1.0, wob=0.3))
        return ''.join(out), dict(ex=ex, ey=ey, rx=rx, ry=ry, top=ey - ry, inner=inner)

    def gaze_for(self, i, ex, ey):
        e = self.e
        if e['look'] is not None and self.world_c is not None:
            tx, ty = self.to_local(e['look'])
            dx, dy = tx - ex, ty - ey
            m = math.hypot(dx, dy) or 1
            return dx / m * e['gmag'], dy / m * e['gmag']
        g = e['gaze']
        if isinstance(g[0], (tuple, list)):
            return g[i]
        return g

    # ---------------------------------------------------------- brows
    def brow(self, i, info):
        c, e, D = self.c, self.e, self.D
        k = 1.0 if i == 0 else self.far_k
        inner = info['inner']
        out_dir = -inner
        ex, ey = info['ex'], info['ey']
        rest_top = ey - c['eye_h'] * D / 2
        dy = self.per('brow_dy', i) * D
        ang = self.per('brow_ang', i)
        bend = self.per('brow_bend', i)
        kind = c['brow']
        if kind == 'tuft':
            L, T = 0.175 * D * (0.85 + 0.15 * k), 0.074 * D
            by = rest_top - 0.05 * D - T / 2 + dy
            bx = ex + out_dir * 0.015 * D
            # centreline from inner (u=0) to outer (u=L) end
            def C(u):
                t = u / L
                return (bx + inner * (L / 2 - u), by - (0.018 * D + bend * D) * math.sin(math.pi * t))
            up, lo = [], []
            n = 10
            for j in range(n + 1):
                u = L * j / n
                th = T * (0.62 + 0.38 * math.sin(math.pi * min(1.0, 0.25 + 0.75 * j / n)))
                p = C(u)
                up.append((p[0], p[1] - th / 2))
                lo.append((p[0], p[1] + th / 2))
            o = C(L)
            flick = [(o[0] + out_dir * 0.03 * D, o[1] - 0.03 * D), (o[0] + out_dir * 0.006 * D, o[1] - 0.004 * D),
                     (o[0] + out_dir * 0.034 * D, o[1] + 0.012 * D)]
            P = catmull(up + flick + lo[::-1], closed=True, n=4)
            P = xform(P, rot=ang * inner, ox=bx, oy=by)
            return P_(P, BROW_W) + ring(P, 0.016 * D, 0.02 * D, seed=self.seed + 80 + i, heavy=(0.3, 0.9))
        if kind == 'kink':
            L, T = 0.21 * D * (0.8 + 0.2 * k), 0.066 * D
            by = rest_top - 0.045 * D - T / 2 + dy
            bx = ex + out_dir * 0.01 * D
            def C(u, v):
                return (bx + inner * (L / 2 - u), by + v)
            pts = [C(0, 0.010 * D), C(0.55 * L, -0.026 * D - bend * D), C(L, 0.002 * D + bend * 0.5 * D)]
            pts = xform(pts, rot=ang * inner, ox=bx, oy=by)
            return brush(pts, T, color=HAIR_K, seed=self.seed + 80 + i, taper=(0.04, 0.5), wmin=T * 0.3, wob=0.5, smooth=False)
        if kind == 'thin':
            L = 0.16 * D * k
            by = rest_top - 0.06 * D + dy
            bx = ex + out_dir * 0.01 * D
            pts = [(bx + inner * L / 2, by + 0.01 * D), (bx, by - 0.012 * D), (bx - inner * L / 2, by + 0.008 * D)]
            pts = xform(pts, rot=ang * inner, ox=bx, oy=by)
            return brush(pts, 0.04 * D, color='#8E8A88', seed=self.seed + 80 + i, taper=(0.2, 0.4), wmin=2)
        return ''

    # ---------------------------------------------------------- skull, ears, hair
    def skull(self):
        c, D = self.c, self.D
        R = D / 2
        P = ellipse(0, 0, R, R, n=200)
        d = d_of(P)
        cid = f'sk{uid()}'
        lx, ly = self.L
        sh = 0.035 * D
        s = [f'<clipPath id="{cid}"><path d="{d}"/></clipPath>', f'<path d="{d}" fill="{AMBER}"/>',
             f'<g clip-path="url(#{cid})"><path d="{d}" fill="{self.skin}" transform="translate({f1(-lx * sh)} {f1(-ly * sh)})"/>']
        if c['jaw']:
            cx = 0.07 * D * lx + self.turn * D * 0.4
            e = ellipse(cx, -0.21 * D, 0.64 * D, (0.71 - c['jaw']) * D, n=96)
            big = [(-D, -D), (D, -D), (D, D), (-D, D)]
            s.append(f'<path d="{d_of(big)} {d_of(e[::-1])}" fill="{self.skin_d}" fill-rule="evenodd"/>')
        s.append('</g>')
        return ''.join(s), cid, P

    def ear(self, side=-1, sx=1.0):
        c, D = self.c, self.D
        kind = c['ear']
        if kind == 'long':
            loc = [(-0.47, -0.13), (-0.535, -0.135), (-0.585, -0.095), (-0.595, -0.01), (-0.59, 0.08), (-0.575, 0.165),
                   (-0.53, 0.20), (-0.48, 0.18), (-0.458, 0.10), (-0.452, -0.04)]
            mark = [(-0.515, -0.09), (-0.553, -0.04), (-0.548, 0.035), (-0.525, 0.075)]
        elif kind == 'std':
            loc = [(-0.465, -0.10), (-0.535, -0.11), (-0.585, -0.065), (-0.592, 0.01), (-0.575, 0.075), (-0.53, 0.105),
                   (-0.48, 0.095), (-0.46, 0.03), (-0.455, -0.045)]
            mark = [(-0.51, -0.065), (-0.55, -0.02), (-0.542, 0.035), (-0.515, 0.06)]
        else:
            loc = [(-0.465, -0.06), (-0.525, -0.075), (-0.572, -0.035), (-0.575, 0.03), (-0.55, 0.085), (-0.50, 0.095),
                   (-0.465, 0.06), (-0.455, 0.0)]
            mark = [(-0.51, -0.035), (-0.542, 0.0), (-0.53, 0.05)]
        def T(x, y):
            xx = -0.455 + (x + 0.455) * sx
            return ((xx if side < 0 else -xx) * D, y * D)
        P = catmull([T(x, y) for x, y in loc], closed=True, n=6)
        lx, ly = self.L
        rw = 0.021 * D
        s = rimlit(P, self.skin, (-lx * 5, -ly * 5)) + ring(P, rw * 0.8, rw * 1.1, seed=self.seed + 4 + side, heavy=(-lx, -ly))
        s += brush([T(x, y) for x, y in mark], 0.02 * D, color=INK, seed=self.seed + 5 + side, taper=(0.3, 0.5), wmin=1.5)
        if kind == 'long':   # plump long lobe: a second fold line
            s += brush([T(-0.555, 0.11), T(-0.52, 0.16)], 0.016 * D, color=self.skin_dd, seed=self.seed + 7, taper=(0.3, 0.3), wmin=1.0)
        return s

    def tenugui(self):
        """Folded indigo tenugui perched on the crown (small, flat, follows the skull curve)."""
        D = self.D
        R = D / 2
        a_c, span = -104, 23
        th = 0.075 * D
        inner, outer = [], []
        for j in range(13):
            a = a_c - span + 2 * span * j / 12
            inner.append(pol((0, 0), a, R - 0.012 * D))
            outer.append(pol((0, 0), a, R + th * (1 - 0.25 * abs(j - 6) / 6)))
        # drooping ends: the cloth hangs a little past the curve
        e1 = pol((0, 0), a_c - span - 3, R - 0.04 * D)
        e2 = pol((0, 0), a_c + span + 3, R - 0.035 * D)
        P = catmull([e1] + outer + [e2] + inner[::-1], closed=True, n=3)
        lx, ly = self.L
        s = rimlit(P, TENUGUI, (-lx * 4, -ly * 4), col=blend(TENUGUI, AMBER, 0.45))
        cid = f'tg{uid()}'
        s += f'<clipPath id="{cid}"><path d="{d_of(P)}"/></clipPath><g clip-path="url(#{cid})">'
        for f in (0.38, 0.70):
            st = [pol((0, 0), a_c - span - 6 + 2 * (span + 6) * j / 12, R - 0.012 * D + f * th) for j in range(13)]
            s += brush(st, 0.016 * D, color=CREAM, seed=self.seed + 120 + int(f * 10), taper=(0, 0), wob=0.2)
        s += '</g>'
        s += ring(P, 0.02 * D, 0.026 * D, seed=self.seed + 125, heavy=(-lx, -ly))
        # fold edge at the front end
        s += brush([pol((0, 0), a_c + span - 4, R + 0.005 * D), pol((0, 0), a_c + span - 6, R + th * 0.8)], 0.014 * D,
                   color=TENUGUI_D, seed=self.seed + 127, taper=(0.2, 0.2))
        return s

    def buzz(self, cid):
        """Short crop: flat dark tone behind a hairline (front hidden by the band), sideburn in front of the ear."""
        D = self.D
        cx = self.turn * D
        hl = [(cx + 0.55 * D, -0.38 * D), (cx + 0.10 * D, -0.39 * D), (-0.12 * D, -0.37 * D), (-0.25 * D, -0.25 * D),
              (-0.285 * D, -0.08 * D), (-0.285 * D, 0.07 * D), (-0.34 * D, 0.09 * D), (-0.42 * D, 0.03 * D),
              (-0.48 * D, 0.16 * D), (-0.50 * D, 0.34 * D), (-0.8 * D, 0.4 * D), (-0.8 * D, -0.8 * D), (0.8 * D, -0.8 * D)]
        P = catmull(hl, closed=True, n=6)
        s = f'<g clip-path="url(#{cid})"><path d="{d_of(P)}" fill="{BUZZ}"/>'
        # a few short bristle ticks along the temple
        edge = catmull(hl[2:6], n=6)
        for j in range(2, len(edge) - 2, 4):
            p = edge[j]
            q = edge[j + 1]
            nx, ny = q[1] - p[1], -(q[0] - p[0])
            l = math.hypot(nx, ny) or 1
            nx, ny = nx / l, ny / l
            s += brush([(p[0] + nx * 0.004 * D, p[1] + ny * 0.004 * D), (p[0] - nx * 0.02 * D, p[1] - ny * 0.02 * D)], 0.011 * D, color=BUZZ,
                       seed=self.seed + 310 + j, taper=(0.0, 0.8), wmin=1.0, smooth=False)
        # a soft crown sheen band (flat, lighter)
        s += brush([(-0.36 * D, -0.30 * D), (-0.22 * D, -0.42 * D), (-0.02 * D, -0.47 * D)], 0.03 * D, color=blend(BUZZ, '#8A7A70', 0.5),
                   seed=self.seed + 330, taper=(0.3, 0.3))
        s += '</g>'
        return s

    def band(self, cid):
        """Twisted hachimaki: cream rope band with diagonal twist marks, knot at the front with two ends up."""
        D = self.D
        R = D / 2
        cx = self.turn * D
        def yu(x):
            return -0.472 * D + 0.05 * D * (1 - ((x - cx) / (0.70 * D)) ** 2)
        th = 0.085 * D
        xs = [-0.62 * D + 1.24 * D * j / 40 for j in range(41)]
        top = [(x, yu(x)) for x in xs]
        bot = [(x, yu(x) + th) for x in xs]
        P = top + bot[::-1]
        lx, ly = self.L
        s = f'<g clip-path="url(#{cid})"><path d="{d_of(P)}" fill="{CREAM}"/>'
        # twist: alternating shaded lozenges + diagonal ink ticks
        for j in range(-11, 12):
            x0 = cx + j * 0.075 * D
            q = [(x0, yu(x0)), (x0 + 0.038 * D, yu(x0 + 0.038 * D)), (x0 + 0.075 * D, yu(x0 + 0.075 * D) + th), (x0 + 0.037 * D, yu(x0 + 0.037 * D) + th)]
            s += P_(q, '#D9D2C2')
            s += brush([(x0, yu(x0) + 0.006 * D), (x0 + 0.038 * D, yu(x0) + th - 0.006 * D)], 0.012 * D, color=INK, seed=self.seed + 200 + j, taper=(0.2, 0.2), smooth=False)
        s += brush([(x, yu(x) + 0.004 * D) for x in xs], 0.016 * D, color=INK, seed=self.seed + 230, taper=(0, 0), wob=0.3)
        s += brush([(x, yu(x) + th - 0.004 * D) for x in xs], 0.016 * D, color=INK, seed=self.seed + 231, taper=(0, 0), wob=0.3)
        s += '</g>'
        # band proud of the rim at both sides
        for sx in (-1, 1):
            yc = yu(sx * 0.46 * D) + th / 2
            xx = sx * math.sqrt(max(0.0, R * R - yc * yc))
            E = ellipse(xx + sx * 0.006 * D, yc, 0.024 * D, th * 0.56, n=24)
            s += filled(E, CREAM, 0.012 * D, 0.016 * D, seed=self.seed + 240 + sx)
        # knot at the front (above the forehead centre) with two ends sticking up past the crown
        kx = cx + 0.10 * D
        ky = yu(kx) + 0.01 * D
        for j, (a, ln, bend) in enumerate(((-126, 0.20, -10), (-58, 0.18, 10))):
            base = (kx, ky - 0.01 * D)
            mid = pol(base, a, ln * D * 0.55)
            tip = pol(mid, a + bend, ln * D * 0.45)
            nrm = a + 90
            cut = 0.018 * D * (1 if j == 0 else -1)
            q = [pol(base, nrm, 0.026 * D), pol(mid, nrm + bend * 0.5, 0.034 * D), pol(pol(tip, a + bend, cut), nrm + bend, 0.046 * D),
                 pol(pol(tip, a + bend, -cut), nrm + bend, -0.040 * D), pol(mid, nrm + bend * 0.5, -0.030 * D), pol(base, nrm, -0.024 * D)]
            s += filled(q, CREAM, 0.016 * D, 0.021 * D, seed=self.seed + 250 + j)
            s += brush([lerp(base, mid, 0.5), lerp(mid, tip, 0.8)], 0.012 * D, color='#BDB4A2', seed=self.seed + 255 + j, taper=(0.2, 0.4))
        K = ellipse(kx, ky, 0.058 * D, 0.05 * D, rot=-8, n=30)
        s += filled(K, CREAM, 0.016 * D, 0.021 * D, seed=self.seed + 260)
        s += brush([(kx - 0.03 * D, ky - 0.015 * D), (kx + 0.025 * D, ky + 0.02 * D)], 0.012 * D, color=INK, seed=self.seed + 261, taper=(0.2, 0.2))
        return s

    def bun(self):
        D = self.D
        R = D / 2
        c = pol((0, 0), -118, R + 0.02 * D)
        E = ellipse(c[0], c[1], 0.13 * D, 0.11 * D, n=40)
        s = filled(E, '#A9A39C', 0.02 * D, 0.026 * D, seed=self.seed + 400)
        s += brush([(c[0] - 0.07 * D, c[1]), (c[0], c[1] - 0.04 * D), (c[0] + 0.07 * D, c[1] - 0.01 * D)], 0.014 * D, color='#7E7872', seed=self.seed + 401, taper=(0.2, 0.2))
        return s

    def bun_cap(self, cid):
        D = self.D
        P = catmull([(-0.8 * D, -0.10 * D), (-0.42 * D, -0.12 * D), (-0.10 * D, -0.34 * D), (0.30 * D, -0.36 * D), (0.8 * D, -0.30 * D),
                     (0.8 * D, -0.8 * D), (-0.8 * D, -0.8 * D)], closed=True, n=6)
        return f'<g clip-path="url(#{cid})"><path d="{d_of(P)}" fill="#A9A39C"/></g>'

    # ---------------------------------------------------------- lower face
    def stubble(self, cid):
        D = self.D
        cx = self.turn * D
        band = catmull([(-D, 0.16 * D), (-0.36 * D, 0.20 * D), (cx - 0.16 * D, 0.22 * D), (cx - 0.06 * D, 0.175 * D),
                        (cx + 0.10 * D, 0.17 * D), (cx + 0.24 * D, 0.21 * D), (D, 0.16 * D), (D, D), (-D, D)], closed=True, n=6)
        col = blend(self.skin, '#4E3A34', 0.30)
        return f'<g clip-path="url(#{cid})"><path d="{d_of(band)}" fill="{col}"/></g>'

    def chin_tuft(self):
        D = self.D
        cx = self.turn * D
        b = pol((0, 0), 90 - 18 * (self.turn / 0.12), D / 2 - 0.03 * D)
        P = catmull([(b[0] - 0.05 * D, b[1] - 0.01 * D), (b[0] + 0.05 * D, b[1] - 0.015 * D), (b[0] + 0.025 * D, b[1] + 0.07 * D),
                     (b[0] - 0.005 * D, b[1] + 0.115 * D), (b[0] - 0.03 * D, b[1] + 0.06 * D)], closed=True, n=5)
        return filled(P, HAIR_K, 0.012 * D, 0.016 * D, seed=self.seed + 90)

    def nose(self, cid=None):
        c, D = self.c, self.D
        cx = self.turn * D
        kind = c['nose']
        lx, ly = self.L
        if kind == 'round':     # wide round nose, 0.22 D wide, fills the gap below the eyes
            nx, ny = cx + 0.04 * D, 0.095 * D
            P = catmull([(nx - 0.10 * D, ny + 0.02 * D), (nx - 0.075 * D, ny - 0.045 * D), (nx - 0.01 * D, ny - 0.075 * D),
                         (nx + 0.07 * D, ny - 0.06 * D), (nx + 0.115 * D, ny + 0.0 * D), (nx + 0.10 * D, ny + 0.055 * D),
                         (nx + 0.02 * D, ny + 0.075 * D), (nx - 0.07 * D, ny + 0.065 * D)], closed=True, n=6)
            s = rimlit(P, blend(self.skin, '#F2CFA8', 0.12), (-lx * 4, -ly * 4), col=blend(self.skin, AMBER, 0.6))
            s += ring(P, 0.02 * D, 0.026 * D, seed=self.seed + 20, heavy=(0.2, 0.9))
            s += brush([(nx - 0.055 * D, ny + 0.035 * D), (nx - 0.035 * D, ny + 0.05 * D), (nx - 0.01 * D, ny + 0.045 * D)], 0.02 * D, seed=self.seed + 21, taper=(0.3, 0.3))
            s += brush([(nx + 0.045 * D, ny + 0.045 * D), (nx + 0.065 * D, ny + 0.04 * D)], 0.016 * D, seed=self.seed + 22, taper=(0.3, 0.3))
            return s
        if kind == 'tri':       # pointed triangle: top in the gap, tip forward and down, 0.24 D wide
            top = (cx + 0.0 * D, -0.02 * D)
            tip = (cx + 0.19 * D, 0.15 * D)
            back = (cx - 0.06 * D, 0.155 * D)
            P = catmull([top, (cx + 0.09 * D, 0.065 * D), tip, (cx + 0.07 * D, 0.172 * D), back, (cx - 0.04 * D, 0.07 * D)], closed=True, n=5)
            s = P_(P, shade(self.skin, 0.12))
            s += brush([top, (cx + 0.09 * D, 0.065 * D), tip], 0.026 * D, seed=self.seed + 20, taper=(0.55, 0.05), wmin=1.5, smooth=False)
            s += brush([tip, (cx + 0.07 * D, 0.175 * D), back], 0.028 * D, seed=self.seed + 23, taper=(0.05, 0.35), wmin=1.5)
            s += brush([(cx + 0.03 * D, 0.13 * D), (cx + 0.06 * D, 0.148 * D)], 0.018 * D, seed=self.seed + 21, taper=(0.3, 0.3))
            return s
        if kind == 'button':
            nx, ny = cx + 0.05 * D, 0.10 * D
            P = ellipse(nx, ny, 0.07 * D, 0.05 * D, n=30)
            return P_(P, shade(self.skin, 0.05)) + ring(P, 0.016 * D, 0.02 * D, seed=self.seed + 20, heavy=(0.2, 0.9))
        return ''

    def folds(self):
        """Tama: forehead wrinkles, cheek folds (nasolabial), jowl crease."""
        D = self.D
        cx = self.turn * D
        c = self.skin_dd
        s = ''
        lift = self.e['brow_dy'][0] if isinstance(self.e['brow_dy'], (tuple, list)) else self.e['brow_dy']
        for j, (w, y) in enumerate(((0.26, -0.425), (0.22, -0.385), (0.15, -0.348))):
            yy = y * D + min(0.0, lift) * D * 0.25
            x0 = cx - 0.02 * D
            pts = [(x0 - w / 2 * D, yy + 0.012 * D), (x0, yy - 0.008 * D), (x0 + w / 2 * D, yy + 0.012 * D)]
            s += brush(pts, 0.018 * D, color=c, seed=self.seed + 141 + j, taper=(0.3, 0.3), wmin=1.0)
        for j, (sx, sgn) in enumerate(((-0.10, -1), (0.19, 1))):
            x0 = cx + sx * D
            pts = [(x0, 0.13 * D), (x0 + sgn * 0.03 * D, 0.21 * D), (x0 + sgn * 0.02 * D, 0.30 * D)]
            s += brush(pts, 0.02 * D, color=c, seed=self.seed + 148 + j, taper=(0.3, 0.4), wmin=1.2)
        return s

    # ---------------------------------------------------------- mouth
    def mouth(self):
        c, e, D = self.c, self.e, self.D
        k = e['mouth']
        cx = self.turn * D
        x = cx + 0.035 * D + e['m_dx'] * D
        y = c['mouth_y'] * D + e['m_dy'] * D
        sd = self.seed + 13
        T = 0.05 * D
        def R(P):
            return xform(P, rot=e['m_rot'], ox=x, oy=y)
        def openm(w, h, topcurve=0.0, botcurve=1.0, teeth_top=0.0, teeth_bot=0.0, tongue=True, wavy=0, cornerdown=0.0):
            top = []
            n = 24
            for j in range(n + 1):
                t = j / n
                xx = x - w / 2 + w * t
                yy = y - h * 0.35 - topcurve * h * math.sin(math.pi * t) + cornerdown * h * (abs(2 * t - 1) ** 3)
                if wavy:
                    yy += 0.018 * D * math.sin(t * math.pi * 2 * wavy)
                top.append((xx, yy))
            bot = []
            for j in range(n, -1, -1):
                t = j / n
                xx = x - w / 2 + w * t
                yy = y - h * 0.35 + h * botcurve * math.sin(math.pi * t) ** 0.8 + cornerdown * h * (abs(2 * t - 1) ** 3)
                bot.append((xx, yy))
            P = R(top + bot)
            cid = f'mo{uid()}'
            s = P_(P, MOUTH_IN) + f'<clipPath id="{cid}"><path d="{d_of(P)}"/></clipPath><g clip-path="url(#{cid})">'
            if tongue:
                s += P_(R(ellipse(x + 0.03 * D, y + h * 0.62, w * 0.30, h * 0.36, n=30)), TONGUE)
            if teeth_top:
                s += P_(R([(x - w, y - h), (x + w, y - h), (x + w, y - h * 0.35 + teeth_top * h), (x - w, y - h * 0.35 + teeth_top * h)]), TEETH)
            if teeth_bot:
                s += P_(R([(x - w, y + h * 2), (x + w, y + h * 2), (x + w, y + h * 0.65 - teeth_bot * h), (x - w, y + h * 0.65 - teeth_bot * h)]), TEETH)
            s += '</g>' + ring(P, 0.022 * D, 0.028 * D, seed=sd, heavy=(0.2, 0.9))
            return s
        if k == 'rest':          # contented closed smile with cheek ticks
            w = 0.27 * D
            s = brush(R([(x - w / 2, y - 0.012 * D), (x - w * 0.2, y + 0.016 * D), (x + w * 0.2, y + 0.016 * D), (x + w / 2, y - 0.016 * D)]), T, seed=sd, taper=(0.25, 0.25))
            s += brush(R([(x + w / 2 + 0.005 * D, y - 0.05 * D), (x + w / 2 + 0.022 * D, y - 0.005 * D)]), 0.018 * D, color=self.skin_dd, seed=sd + 3, taper=(0.3, 0.3))
            s += brush(R([(x - w / 2 - 0.005 * D, y - 0.05 * D), (x - w / 2 - 0.022 * D, y - 0.005 * D)]), 0.018 * D, color=self.skin_dd, seed=sd + 4, taper=(0.3, 0.3))
            return s
        if k == 'o':
            return openm(e['m_w'] or 0.30 * D, 0.24 * D, topcurve=0.25, botcurve=0.95, teeth_top=0.12)
        if k == 'grit':
            w, h = e['m_w'] or 0.36 * D, 0.13 * D
            P = R(catmull([(x - w / 2, y - h / 2 + 0.02 * D), (x, y - h / 2 + 0.01 * D), (x + w / 2, y - h / 2 + 0.025 * D),
                           (x + w / 2 - 0.01 * D, y + h / 2 + 0.01 * D), (x, y + h / 2 - 0.005 * D), (x - w / 2 + 0.01 * D, y + h / 2 + 0.015 * D)], closed=True, n=6))
            s = P_(P, TEETH)
            s += brush(R([(x - w / 2 + 0.01 * D, y + 0.005 * D), (x, y), (x + w / 2 - 0.01 * D, y + 0.008 * D)]), 0.02 * D, seed=sd + 1, taper=(0.05, 0.05))
            for j in range(1, 5):
                tx = x - w / 2 + w * j / 5
                s += brush(R([(tx, y - h / 2 + 0.01 * D), (tx + 0.004 * D, y + h / 2 - 0.01 * D)]), 0.016 * D, seed=sd + 2 + j, taper=(0.1, 0.1))
            s += ring(P, 0.024 * D, 0.03 * D, seed=sd, heavy=(0.2, 0.9))
            # down-turned corner ticks
            s += brush(R([(x - w / 2 - 0.005 * D, y), (x - w / 2 - 0.03 * D, y + 0.045 * D)]), 0.02 * D, seed=sd + 9, taper=(0.1, 0.5))
            s += brush(R([(x + w / 2 + 0.005 * D, y), (x + w / 2 + 0.03 * D, y + 0.045 * D)]), 0.02 * D, seed=sd + 10, taper=(0.1, 0.5))
            return s
        if k == 'smirk':
            w = e['m_w'] or 0.28 * D
            s = brush(R([(x - w / 2, y + 0.01 * D), (x - 0.02 * D, y + 0.022 * D), (x + w / 2 - 0.035 * D, y + 0.0 * D), (x + w / 2 + 0.005 * D, y - 0.045 * D)]), T, seed=sd, taper=(0.3, 0.2))
            s += brush(R([(x + w / 2 + 0.03 * D, y - 0.085 * D), (x + w / 2 + 0.045 * D, y - 0.035 * D)]), 0.02 * D, color=self.skin_dd, seed=sd + 3, taper=(0.3, 0.3))
            return s
        if k == 'panic':
            return openm(e['m_w'] or 0.42 * D, 0.21 * D, topcurve=-0.05, botcurve=1.0, teeth_top=0.18, wavy=2)
        if k == 'flat':         # pressed, pushed to one side, downturned end
            w = e['m_w'] or 0.24 * D
            xx = x - 0.04 * D
            s = brush(R([(xx - w / 2, y + 0.0 * D), (xx + w * 0.1, y - 0.004 * D), (xx + w / 2, y + 0.01 * D), (xx + w / 2 + 0.02 * D, y + 0.035 * D)]), T, seed=sd, taper=(0.2, 0.15))
            return s
        if k == 'grin':
            return openm(e['m_w'] or 0.38 * D, 0.17 * D, topcurve=-0.12, botcurve=1.0, teeth_top=0.30, tongue=True)
        if k == 'shout':
            return openm(e['m_w'] or 0.34 * D, 0.25 * D, topcurve=0.15, botcurve=1.0, teeth_top=0.16, teeth_bot=0.0)
        if k == 'sip':          # lips pursed onto the cup rim (hidden mostly by the cup)
            s = brush(R([(x - 0.06 * D, y - 0.01 * D), (x + 0.02 * D, y + 0.01 * D)]), T, seed=sd, taper=(0.3, 0.3))
            return s
        if k == 'tight':
            w = e['m_w'] or 0.22 * D
            return brush(R([(x - w / 2, y + 0.012 * D), (x, y - 0.006 * D), (x + w / 2, y + 0.014 * D)]), T, seed=sd, taper=(0.25, 0.25))
        return ''

    # ---------------------------------------------------------- marks
    def marks(self):
        D = self.D
        R = D / 2
        col = self.e['mark_col']
        out = []
        for m in self.e['marks']:
            kind = m[0]
            if kind == 'pop_lines':
                for j, a in enumerate((-150, -122, -90, -58, -30)):
                    out.append(brush([pol((0, 0), a, R + 0.17 * D), pol((0, 0), a, R + 0.30 * D)], 0.036 * D, color=col, seed=self.seed + 100 + j, taper=(0.12, 0.25)))
            elif kind == 'sweat':
                sx, sy, sz, ang = m[1] * D, m[2] * D, m[3] * D, m[4]
                P = [(0, -sz * 1.25)] + [(sz * 0.62 * math.cos(t), sz * 0.15 + sz * 0.62 * math.sin(t)) for t in [math.radians(d) for d in range(-35, 216, 15)]]
                P = xform(P, dx=sx, dy=sy, rot=ang)
                out.append(filled(P, '#DCEBF2', 0.016 * D, 0.022 * D, seed=self.seed + 130))
            elif kind == 'vein':
                vx, vy, sz = m[1] * D, m[2] * D, m[3] * D
                for j, a in enumerate((45, 135, 225, 315)):
                    c0 = pol((vx, vy), a, sz * 0.25)
                    out.append(brush([pol(c0, a - 50, sz * 0.35), c0, pol(c0, a + 50, sz * 0.35)], 0.024 * D, color=VERM, seed=self.seed + 135 + j, taper=(0.2, 0.2)))
            elif kind == 'puff':
                px, py, sz = m[1] * D, m[2] * D, m[3] * D
                ps = [ellipse(px, py, sz, sz * 0.8, n=24), ellipse(px + sz * 0.9, py - sz * 0.3, sz * 0.8, sz * 0.66, n=24), ellipse(px + sz * 1.6, py + sz * 0.1, sz * 0.6, sz * 0.5, n=24)]
                out.append(union(ps, CREAM, 0.014 * D, 0.018 * D, seed=self.seed + 138))
            elif kind == 'shake':
                for sgn in (-1, 1):
                    for j, dy in enumerate((-0.12, 0.0, 0.12)):
                        x0 = sgn * (R + 0.08 * D)
                        out.append(brush([(x0, dy * D - 0.04 * D), (x0 + sgn * 0.03 * D, dy * D), (x0, dy * D + 0.04 * D)], 0.022 * D, color=col, seed=self.seed + 150 + j, taper=(0.2, 0.2)))
        return ''.join(out)

    # ---------------------------------------------------------- assembly
    def svg(self, cx, cy):
        c, D = self.c, self.D
        if self.world_c is None:
            self.world_c = (cx, cy)
        skull, cid, P = self.skull()
        lx, ly = self.L
        s = []
        if c['hair'] == 'bun':
            s.append(self.bun())
        if self.front_ear:
            s.append(self.ear(side=+1, sx=0.7))
        s.append(skull)
        if c['stubble']:
            s.append(self.stubble(cid))
        if c['hair'] == 'buzz':
            s.append(self.buzz(cid))
        if c['hair'] == 'bun':
            s.append(self.bun_cap(cid))
        s.append(ring(P, 0.028 * D, 0.038 * D, seed=self.seed, heavy=(-lx, -ly)))
        s.append(self.ear(side=-1))
        if c['age'] and self.who == 'tama':
            s.append(f'<g clip-path="url(#{cid})">' + self.folds() + '</g>')
        eyes, infos = [], []
        for i in (0, 1):
            es, info = self.eye(i)
            eyes.append(es)
            infos.append(info)
        s.append(f'<g clip-path="url(#{cid})">' + ''.join(eyes) + '</g>')
        if c['hair'] == 'buzz':
            s.append(self.band(cid))
        s.append(self.brow(0, infos[0]))
        s.append(self.brow(1, infos[1]))
        s.append(self.nose())
        s.append(self.mouth())
        if c['stubble']:
            s.append(self.chin_tuft())
        if c['hair'] == 'tenugui':
            s.append(self.tenugui())
        s.append(self.marks())
        T = f'translate({f1(cx)} {f1(cy)}) rotate({f1(self.rot)}) scale({self.facing} 1)'
        self.infos = infos
        return f'<g transform="{T}">{"".join(s)}</g>'

    def world(self, cx, cy, lp):
        x, y = lp[0] * self.facing, lp[1]
        x, y = rot2((x, y), self.rot)
        return (cx + x, cy + y)

# =====================================================================
# PROPS
# =====================================================================
def temari(bx, by, r, seed=500, tilt=30, spin=8, bell_side=1, bell=True):
    """Temari with real thread geometry: vermilion ground, gold jiwari meridians, a cream/green
    uroko zigzag band on the equator and a small kiku on the top pole (sphere-projected)."""
    t = math.radians(tilt)

    def proj(lat, lon):
        x = math.cos(lat) * math.sin(lon)
        y0 = math.sin(lat)
        z0 = math.cos(lat) * math.cos(lon)
        y = y0 * math.cos(t) - z0 * math.sin(t)
        z = y0 * math.sin(t) + z0 * math.cos(t)
        return (bx + r * x, by - r * y), z
    o = []
    ball = ellipse(bx, by, r, r, n=64)
    o.append(P_(ball, VERM))
    cid = f'tm{uid()}'
    o.append(f'<clipPath id="{cid}"><path d="{d_of(ball)}"/></clipPath><g clip-path="url(#{cid})">')
    sp = math.radians(spin)
    # gold meridians (8 divisions), visible segments only
    for k in range(8):
        lon = sp + k * math.pi / 4
        seg = []
        for j in range(41):
            lat = math.radians(88 - 176 * j / 40)
            p, z = proj(lat, lon)
            if z > 0.02:
                seg.append(p)
            elif len(seg) > 1:
                o.append(brush(seg, r * 0.075, color=BRASS, seed=seed + k, taper=(0.0, 0.0), wmin=1.2, wob=0.2))
                seg = []
            else:
                seg = []
        if len(seg) > 1:
            o.append(brush(seg, r * 0.075, color=BRASS, seed=seed + k, taper=(0.0, 0.0), wmin=1.2, wob=0.2))
    # equator band: uroko triangles between two cream latitude threads
    bw = math.radians(13)
    n = 16
    for k in range(n):
        l0 = sp + 2 * math.pi * k / n
        l1 = sp + 2 * math.pi * (k + 1) / n
        lm = (l0 + l1) / 2
        for up, col in ((True, CREAM), (False, MATCHA)):
            if up:
                tri = [proj(-bw, l0), proj(-bw, l1), proj(bw, lm)]
            else:
                tri = [proj(bw, lm), proj(bw, lm + 2 * math.pi / n), proj(-bw, l1)]
            if all(z > 0.05 for _, z in tri):
                o.append(P_([p for p, _ in tri], col))
    for lat in (-bw, bw):
        pts = [proj(lat, sp + 2 * math.pi * j / 72) for j in range(73)]
        seg = [p for p, z in pts if z > 0.02]
        # keep the front arc only, in order
        front = []
        for p, z in pts:
            if z > 0.02:
                front.append(p)
        if len(front) > 2:
            front.sort(key=lambda q: q[0])
            o.append(brush(front, r * 0.07, color=INK, seed=seed + 20 + int(lat * 10), taper=(0, 0), wmin=1.0, wob=0.2))
    # kiku on the top pole
    pole, zp = proj(math.radians(90), 0)
    if zp > 0:
        for k in range(8):
            lon = sp + math.pi / 8 + k * math.pi / 4
            pts = [proj(math.radians(a), lon)[0] for a in (88, 78, 66, 56)]
            if proj(math.radians(60), lon)[1] > 0.02:
                o.append(brush(pts, r * 0.13, color=CREAM, seed=seed + 40 + k, taper=(0.1, 0.5), wmin=1.2, wob=0.2))
        o.append(f'<circle cx="{f1(pole[0])}" cy="{f1(pole[1])}" r="{f1(r * 0.10)}" fill="{MATCHA_D}"/>')
    o.append('</g>')
    o.append(ring(ball, r * 0.14, r * 0.19, seed=seed + 9))
    if bell:
        cord0 = (bx + bell_side * r * 0.75, by + r * 0.62)
        bxx, byy = bx + bell_side * (r * 1.12), by + r * 0.98
        o.append(brush([cord0, (bxx, byy - r * 0.3)], r * 0.07, color=VERM, seed=seed + 50, taper=(0, 0)))
        bellp = ellipse(bxx, byy, r * 0.30, r * 0.28, n=30)
        o.append(filled(bellp, BRASS, r * 0.10, r * 0.13, seed=seed + 11))
        o.append(brush([(bxx - r * 0.18, byy + r * 0.07), (bxx + r * 0.18, byy + r * 0.07)], r * 0.07, seed=seed + 12, taper=(0, 0)))
    return ''.join(o)


def yunomi(cx, cy, D, rot=0.0, seed=0, steam=True):
    """Tall handle-less tea cup: cream body, broad indigo band with a cream wave line, tea surface."""
    wt, wb, h = 0.21 * D, 0.175 * D, 0.24 * D
    top, bot = cy - h / 2, cy + h / 2
    body = [(cx - wt / 2, top), (cx + wt / 2, top), (cx + wb / 2, bot - 0.01 * D), (cx + wb / 2 - 0.015 * D, bot),
            (cx - wb / 2 + 0.015 * D, bot), (cx - wb / 2, bot - 0.01 * D)]
    R = lambda P: xform(P, rot=rot, ox=cx, oy=cy)
    s = ''
    if steam:
        for i, dx in enumerate((-0.035, 0.04)):
            x0 = cx + dx * D
            pts = [(x0, top - 0.04 * D), (x0 + 0.03 * D, top - 0.10 * D), (x0 - 0.02 * D, top - 0.17 * D), (x0 + 0.02 * D, top - 0.24 * D)]
            s += brush(pts, 0.022 * D, color=CREAM, seed=seed + 5 + i, taper=(0.3, 0.6), op=0.85)
    B = R(body)
    cid = f'yn{uid()}'
    s += P_(B, CUP) + f'<clipPath id="{cid}"><path d="{d_of(B)}"/></clipPath><g clip-path="url(#{cid})">'
    s += P_(R([(cx - D, cy - 0.055 * D), (cx + D, cy - 0.055 * D), (cx + D, cy + 0.06 * D), (cx - D, cy + 0.06 * D)]), CUP_BAND)
    wv = [(cx - wt / 2 + wt * j / 16, cy + 0.004 * D + 0.016 * D * math.sin(j / 16 * math.pi * 4)) for j in range(17)]
    s += brush(R(wv), 0.014 * D, color=CREAM, seed=seed + 2, taper=(0, 0), wob=0.2)
    s += P_(R([(cx - D, bot - 0.03 * D), (cx + D, bot - 0.03 * D), (cx + D, bot + D), (cx - D, bot + D)]), shade(CUP, 0.18))
    s += '</g>'
    s += ring(B, 0.016 * D, 0.022 * D, seed=seed + 1)
    rim = ellipse(cx, top + 0.004 * D, wt / 2 - 0.006 * D, 0.03 * D, n=36)
    s += P_(R(rim), TEA) + ring(R(rim), 0.012 * D, 0.016 * D, seed=seed + 3)
    return s


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


def swoosh(base, r, a0, a1, n=2, gap=16, w=6, col=PLUM_L, seed=0, op=0.8):
    out = []
    for i in range(n):
        rr = r - i * gap
        pts = [pol(base, a0 + (a1 - a0) * t / 12, rr) for t in range(13)]
        out.append(brush(pts, w, color=col, seed=seed + i, taper=(0.7, 0.1), wmin=1.5, op=op))
    return ''.join(out)


def ghost_ball(bx, by, br, op=0.55, col=CREAM):
    P = ellipse(bx, by, br, br, n=40)
    return f'<g opacity="{op}">' + ring(P, br * 0.12, br * 0.16, color=col, seed=777) + '</g>'


# =====================================================================
# SKELETON + COSTUME
# =====================================================================
class Frame:
    """Facing-right local frame, origin = head centre, units of D -> world."""

    def __init__(self, hc, D, facing):
        self.hc, self.D, self.f = hc, D, facing

    def w(self, p):
        return (self.hc[0] + self.f * p[0] * self.D, self.hc[1] + p[1] * self.D)

    def a(self, deg):
        return deg if self.f == 1 else 180 - deg


def skeleton(F, P):
    nt, nb, hip = P['nt'], P['nb'], P['hip']
    mid = lerp(nb, hip, 0.5)
    dsp = ang_of(nb, hip)
    ctrl = pol(mid, dsp + 90, P.get('bow', 0.1))
    curve = qbez(nb, ctrl, hip, 30)
    tan0 = ang_of(curve[0], curve[3])
    yk = pol(nb, tan0, P.get('yoke', 0.06))
    fwd = tan0 - 90
    sh_f = pol(yk, fwd, P['sh'])
    sh_n = pol(yk, fwd, -P['sh'] * P.get('sh_nk', 1.0))
    el_f, wr_f = ik(sh_f, P['wr_f'], P['ua'], P['fa'], P.get('el_f', 1), P.get('straight_f', False))
    el_n, wr_n = ik(sh_n, P['wr_n'], P['ua'], P['fa'], P.get('el_n', 1), P.get('straight_n', False))
    tanh = ang_of(curve[-4], curve[-1])
    fwdh = tanh - 90
    hw = P.get('hipw', 0.04)
    hip_f = pol(hip, fwdh, hw)
    hip_n = pol(hip, fwdh, -hw)
    kn_f, an_f = ik(hip_f, P['an_f'], P['th'], P['sn'], P.get('kn_f', -1), P.get('straightleg_f', False))
    kn_n, an_n = ik(hip_n, P['an_n'], P['th'], P['sn'], P.get('kn_n', -1), P.get('straightleg_n', False))
    if 'knee_f' in P:          # explicit joints (knock-knee stance)
        kn_f, an_f = P['knee_f'], P['an_f']
    if 'knee_n' in P:
        kn_n, an_n = P['knee_n'], P['an_n']
    L = dict(nt=nt, nb=nb, hip=hip, yk=yk, sh_f=sh_f, sh_n=sh_n, el_f=el_f, wr_f=wr_f, el_n=el_n, wr_n=wr_n,
             hip_f=hip_f, hip_n=hip_n, kn_f=kn_f, an_f=an_f, kn_n=kn_n, an_n=an_n)
    J = {k: F.w(v) for k, v in L.items()}
    J['curve'] = [F.w(q) for q in curve]
    L['curve'] = curve
    L['fwd'], L['tan0'], L['tanh'] = fwd, tan0, tanh
    return L, J


def offset_curve(C, dist, side=1):
    """Offset a local polyline; side=+1 = toward the back (left normal of a downward tangent = -x)."""
    out = []
    N = len(C)
    for i, p in enumerate(C):
        a, b = C[max(0, i - 1)], C[min(N - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, ty) or 1
        nx, ny = -ty / l, tx / l
        d = dist(i / (N - 1)) if callable(dist) else dist
        out.append((p[0] + side * nx * d, p[1] + side * ny * d))
    return out


def shoe(B, an, ang, facing, kind='tabi', seed=0, L=0.30):
    """Footwear: 'tabi' = cream split-toe sock on a thin zori sole; 'jika' = navy jika-tabi boot with a grey rubber sole."""
    D = B.D
    L = L * D
    dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    ux, uy = facing * dy, -facing * dx
    def W(u, v):
        return (an[0] + dx * u * L + ux * v * L, an[1] + dy * u * L + uy * v * L)
    if kind == 'tabi':
        loc = [(-0.26, 0.0), (0.74, 0.0), (0.84, 0.07), (0.80, 0.19), (0.58, 0.27), (0.30, 0.32), (0.08, 0.44), (-0.18, 0.40), (-0.30, 0.17)]
        P = catmull([W(u, v) for u, v in loc], closed=True, n=6)
        sole = [W(-0.30, -0.02), W(0.86, -0.02), W(0.86, -0.10), W(-0.30, -0.10)]
        s = filled(sole, WOOD, 0.012 * D, 0.016 * D, seed=B.seed + 350 + seed)
        rv = B.rimv(P, 3.5)
        s += rimlit(P, CREAM, (-rv[0], -rv[1])) + ring(P, 0.016 * D, 0.022 * D, seed=B.seed + 360 + seed)
        s += brush([W(0.58, 0.25), W(0.66, 0.12), W(0.68, 0.02)], 0.013 * D, seed=B.seed + 370 + seed, taper=(0.1, 0.3))
        return s
    loc = [(-0.28, 0.0), (0.78, 0.0), (0.90, 0.08), (0.84, 0.22), (0.56, 0.30), (0.22, 0.36), (0.10, 0.70), (-0.16, 0.70), (-0.30, 0.20)]
    P = catmull([W(u, v) for u, v in loc], closed=True, n=6)
    rv = B.rimv(P, 3.5)
    s = rimlit(P, JIKA, (-rv[0], -rv[1])) + ring(P, 0.016 * D, 0.022 * D, seed=B.seed + 360 + seed)
    sole = [W(-0.31, 0.0), W(0.90, 0.0), W(0.92, -0.07), W(-0.31, -0.07)]
    s += filled(sole, '#8A8D99', 0.012 * D, 0.016 * D, seed=B.seed + 350 + seed)
    s += brush([W(0.60, 0.27), W(0.68, 0.14), W(0.70, 0.04)], 0.013 * D, color='#6E7690', seed=B.seed + 370 + seed, taper=(0.1, 0.3))
    for j in range(3):   # kohaze clasps
        s += brush([W(-0.12 + 0.0 * j, 0.40 + 0.1 * j), W(0.02, 0.40 + 0.1 * j)], 0.012 * D, color=BRASS, seed=B.seed + 380 + j, taper=(0, 0))
    return s


def sleeve(B, sh, el, wr, D, col, col_d, hang=0.26, seed=0, wide=True, upn=None):
    """Haori tamoto (wide) or samue short sleeve (wide=False), in world coords."""
    u = ang_of(sh, el)
    nrm = u - 90
    nv = (math.cos(math.radians(nrm)), math.sin(math.radians(nrm)))
    if nv[1] > 0:
        nv = (-nv[0], -nv[1])
    if wide:
        c = lerp(el, wr, 0.10)
        p1 = (sh[0] + nv[0] * 0.07 * D, sh[1] + nv[1] * 0.07 * D)
        p2 = (c[0] + nv[0] * 0.08 * D, c[1] + nv[1] * 0.08 * D)
        p3 = (c[0] - nv[0] * 0.08 * D, c[1] - nv[1] * 0.08 * D)
        low = max(p3[1], sh[1] + 0.05 * D) + hang * D
        p4 = (p3[0], low)
        p5 = (lerp(sh, c, 0.30)[0], low + 0.01 * D)
        p6 = (sh[0] - nv[0] * 0.09 * D, sh[1] - nv[1] * 0.09 * D + 0.06 * D)
        P = catmull([p1, lerp(p1, p2, 0.5), p2, p3, lerp(p3, p4, 0.6), p4, lerp(p4, p5, 0.5), p5, p6], closed=True, n=4)
        rv = B.rimv(P, 4.0)
        s = rimlit(P, col, (-rv[0], -rv[1])) + ring(P, 0.02 * D, 0.026 * D, seed=B.seed + 500 + seed)
        s += brush([lerp(p2, p3, 0.1), lerp(p2, p3, 0.9)], 0.03 * D, color=col_d, seed=B.seed + 505 + seed, taper=(0.1, 0.1))
        s += brush([lerp(p1, p6, 0.5), lerp(p5, p4, 0.4)], 0.014 * D, color=col_d, seed=B.seed + 506 + seed, taper=(0.4, 0.4))
        return s
    c = lerp(sh, el, 0.55)
    P = tube([pol(sh, u + 180, 0.03 * D), c], 0.19 * D, 0.165 * D, cap=False)
    P = catmull(P, closed=True, n=2)
    rv = B.rimv(P, 4.0)
    s = rimlit(P, col, (-rv[0], -rv[1])) + ring(P, 0.02 * D, 0.026 * D, seed=B.seed + 500 + seed)
    cuff = tube([lerp(sh, el, 0.44), c], 0.175 * D, 0.168 * D, cap=False)
    s += P_(cuff, col_d)
    return s


def tama_costume(B, L, F, D, seed=0):
    """Plum haori panel over a taupe kimono, purple obi in the front opening, cream under-collar, himo tie."""
    C = L['curve']
    back = offset_curve(C, lambda t: 0.10 + 0.09 * t, side=1)
    front = offset_curve(C, lambda t: 0.20 + 0.09 * t, side=-1)
    tanh = math.radians(L['tanh'])
    dv = (math.cos(tanh), math.sin(tanh))
    hem = 0.47
    hb = (back[-1][0] + dv[0] * hem - 0.03, back[-1][1] + dv[1] * hem)
    hf = (front[-1][0] + dv[0] * hem + 0.06, front[-1][1] + dv[1] * hem)
    sh_n, sh_f, nb = L['sh_n'], L['sh_f'], L['nb']
    top_b = (sh_n[0] - 0.03, sh_n[1] - 0.03)
    top_f = (sh_f[0] + 0.02, sh_f[1] - 0.02)
    Pl = [top_b] + back[4:] + [hb, hf] + front[::-1][:-5] + [top_f, (nb[0] + 0.05, nb[1] - 0.04), (nb[0] - 0.10, nb[1] - 0.03)]
    Pl = catmull(Pl, closed=True, n=3)
    Pw = [F.w(p) for p in Pl]
    rv = B.rimv(Pw, 5.0)
    s = rimlit(Pw, HAORI, (-rv[0], -rv[1])) + ring(Pw, 0.024 * D, 0.03 * D, seed=B.seed + 600 + seed)
    cid = f'hr{uid()}'
    s += f'<clipPath id="{cid}"><path d="{d_of(Pw)}"/></clipPath><g clip-path="url(#{cid})">'
    # kimono strip in the front opening, between the two haori fronts
    e1 = offset_curve(C, lambda t: 0.05 + 0.05 * t, side=-1)
    e2 = offset_curve(C, lambda t: 0.15 + 0.07 * t, side=-1)
    ext = lambda p, d: (p[0] + dv[0] * d, p[1] + dv[1] * d)
    strip = [(nb[0] + 0.03, nb[1] + 0.02)] + e1[3:] + [ext(e1[-1], 0.6), ext(e2[-1], 0.6)] + e2[::-1][:-3] + [(nb[0] + 0.14, nb[1] + 0.0)]
    Sw = [F.w(p) for p in strip]
    s += P_(Sw, KIMONO)
    sid = f'ks{uid()}'
    s += f'<clipPath id="{sid}"><path d="{d_of(Sw)}"/></clipPath><g clip-path="url(#{sid})">'
    oc = lerp(L['hip'], nb, 0.10)
    ob = [(oc[0] - 0.4, oc[1] - 0.075), (oc[0] + 0.6, oc[1] - 0.085), (oc[0] + 0.6, oc[1] + 0.065), (oc[0] - 0.4, oc[1] + 0.075)]
    s += P_([F.w(p) for p in ob], OBI_P)
    s += brush([F.w((oc[0] - 0.3, oc[1] - 0.005)), F.w((oc[0] + 0.6, oc[1] - 0.012))], 0.016 * D, color=blend(OBI_P, CREAM, 0.55), seed=B.seed + 610, taper=(0, 0))
    s += '</g></g>'
    # haori lapel bands along both opening edges
    for k, e in enumerate((e1, e2)):
        lap = [F.w(p) for p in [(nb[0] + (0.03 if k == 0 else 0.14), nb[1] + 0.0)] + e[3::3] + [ext(e[-1], hem)]]
        s += brush(lap, 0.055 * D, color=HAORI_D, seed=B.seed + 615 + k, taper=(0.0, 0.0), wob=0.4)
    # cream under-collar V
    v0 = F.w((nb[0] - 0.07, nb[1] - 0.02))
    v1 = F.w((nb[0] + 0.09, nb[1] + 0.20))
    v2 = F.w((nb[0] + 0.15, nb[1] - 0.03))
    for k, (a, b) in enumerate(((v0, v1), (v2, v1))):
        s += brush([a, lerp(a, b, 0.5), b], 0.06 * D + 6, color=INK, taper=(0.0, 0.3), wmin=0.03 * D + 4, seed=B.seed + 620 + k, wob=0.5)
        s += brush([a, lerp(a, b, 0.5), b], 0.06 * D, color=CREAM, taper=(0.0, 0.3), wmin=0.03 * D, seed=B.seed + 620 + k, wob=0.5)
    # himo tie bridging the opening at chest height
    ha = F.w(e1[10])
    hb2 = F.w(e2[10])
    hp = lerp(ha, hb2, 0.5)
    s += brush([ha, hp, hb2], 0.02 * D + 4, color=INK, seed=B.seed + 629, taper=(0, 0))
    s += brush([ha, hp, hb2], 0.02 * D, color=CREAM, seed=B.seed + 629, taper=(0, 0))
    s += filled(ellipse(hp[0], hp[1] + 0.005 * D, 0.034 * D, 0.03 * D, n=20), CREAM, 0.012 * D, 0.016 * D, seed=B.seed + 630)
    for k, dxy in enumerate(((-0.02, 0.085), (0.025, 0.08))):
        q = (hp[0] + F.f * dxy[0] * D, hp[1] + dxy[1] * D)
        s += brush([hp, q], 0.02 * D + 4, color=INK, seed=B.seed + 632 + k, taper=(0, 0.3))
        s += brush([hp, q], 0.02 * D, color=CREAM, seed=B.seed + 632 + k, taper=(0, 0.3))
    return s


def hiko_costume(B, L, F, D, seed=0):
    """Persimmon samue jacket: crossed collar band, side tie."""
    C = L['curve']
    back = offset_curve(C, lambda t: 0.11 + 0.03 * t, side=1)
    front = offset_curve(C, lambda t: 0.19 + 0.05 * t, side=-1)
    tanh = math.radians(L['tanh'])
    dv = (math.cos(tanh), math.sin(tanh))
    hem = 0.14
    hb = (back[-1][0] + dv[0] * hem, back[-1][1] + dv[1] * hem)
    hf = (front[-1][0] + dv[0] * hem, front[-1][1] + dv[1] * hem)
    sh_n, sh_f, nb = L['sh_n'], L['sh_f'], L['nb']
    top_b = (sh_n[0] - 0.02, sh_n[1] - 0.04)
    top_f = (sh_f[0] + 0.03, sh_f[1] - 0.03)
    Pl = [top_b] + back[3:] + [hb, hf] + front[::-1][:-4] + [top_f, (nb[0] + 0.06, nb[1] - 0.05), (nb[0] - 0.10, nb[1] - 0.04)]
    Pl = catmull(Pl, closed=True, n=3)
    Pw = [F.w(p) for p in Pl]
    rv = B.rimv(Pw, 5.0)
    s = rimlit(Pw, PERS, (-rv[0], -rv[1])) + ring(Pw, 0.024 * D, 0.03 * D, seed=B.seed + 700 + seed)
    # crossed collar: two bands from each side of the neck meet in a V at the chest, the overlap edge runs on down to the hem
    ed = offset_curve(C, lambda t: 0.05 + 0.03 * t, side=-1)
    vp = ed[11]
    a0 = (nb[0] - 0.10, nb[1] - 0.03)
    a1 = (ed[-1][0] + dv[0] * hem, ed[-1][1] + dv[1] * hem)
    cl = [F.w(p) for p in [a0, lerp(a0, vp, 0.5), vp] + ed[14::4] + [a1]]
    s += brush(cl, 0.072 * D + 6, color=INK, seed=B.seed + 710, taper=(0, 0), wob=0.4)
    s += brush(cl, 0.072 * D, color=PERS_D, seed=B.seed + 710, taper=(0, 0), wob=0.4)
    b0 = (nb[0] + 0.12, nb[1] - 0.04)
    cl2 = [F.w(p) for p in (b0, lerp(b0, vp, 0.5), vp)]
    s += brush(cl2, 0.066 * D + 6, color=INK, seed=B.seed + 712, taper=(0, 0.15), wob=0.3)
    s += brush(cl2, 0.066 * D, color=PERS_D, seed=B.seed + 712, taper=(0, 0.15), wob=0.3)
    a0, a1 = vp, ed[22]
    # neck V skin under the collar
    # side tie
    tp = F.w(a1)
    for k, dxy in enumerate(((0.07, 0.09), (0.02, 0.12))):
        q = (tp[0] + F.f * dxy[0] * D, tp[1] + dxy[1] * D)
        s += brush([tp, q], 0.02 * D + 4, color=INK, seed=B.seed + 720 + k, taper=(0, 0.3))
        s += brush([tp, q], 0.02 * D, color=PERS_D, seed=B.seed + 720 + k, taper=(0, 0.3))
    s += filled(ellipse(tp[0], tp[1], 0.03 * D, 0.026 * D, n=18), PERS_D, 0.012 * D, 0.016 * D, seed=B.seed + 725)
    return s


def cuff(B, kn, an, D, col, col_d, seed=0):
    """Samue trouser hem tied at the ankle: a short persimmon tube on the shin."""
    a = lerp(kn, an, 0.62)
    b = lerp(kn, an, 0.90)
    P = tube([a, b], 0.13 * D, 0.11 * D, cap=False)
    P = catmull(P, closed=True, n=2)
    s = P_(P, col) + ring(P, 0.016 * D, 0.02 * D, seed=B.seed + 800 + seed)
    s += brush([lerp(a, b, 0.75), lerp(a, b, 0.76)], 0.12 * D, color=col_d, seed=B.seed + 805 + seed, taper=(0, 0))
    return s


# =====================================================================
# FIGURES
# =====================================================================
def light_vec(light, hc):
    if light[0] == 'dir':
        lv = light[1]
    else:
        lv = (light[0] - hc[0], light[1] - hc[1])
    ll = math.hypot(*lv) or 1
    return (lv[0] / ll, lv[1] / ll)


def tama_fig(hc, D, facing, expr, P, light, seed=0, front_ear=False, cup_order='front'):
    F = Frame(hc, D, facing)
    face = BigFace(D, 'tama', facing=facing, rot=P.get('head_rot', 0.0) * facing, turn=P.get('turn', 0.12), far_k=P.get('far_k', 0.76),
                   light=light_vec(light, hc), expr=expr, front_ear=front_ear, seed=11 + seed, world=hc)
    B = Body(D, light, skin=SKIN_M, seed=seed, tag='tama', limb=(0.068, 0.046), spine=(0.07, 0.06))
    L, J = skeleton(F, P)
    o = {}
    o['far_leg'] = B.limb([J['hip_f'], J['kn_f'], J['an_f']], seed=1) + shoe(B, J['an_f'], F.a(P.get('toe_f', 0)), facing, 'tabi', seed=1, L=0.27)
    o['near_leg'] = B.limb([J['hip_n'], J['kn_n'], J['an_n']], seed=2) + shoe(B, J['an_n'], F.a(P.get('toe_n', 0)), facing, 'tabi', seed=2, L=0.27)
    o['spine'] = B.spine(J['curve'], seed=4)
    o['costume'] = tama_costume(B, L, F, D, seed=seed)
    hf = F.a(P.get('hand_f', ang_of(L['el_f'], L['wr_f'])))
    hn = F.a(P.get('hand_n', ang_of(L['el_n'], L['wr_n'])))
    o['far_arm'] = B.limb([J['sh_f'], J['el_f'], J['wr_f']], seed=3) + B.mitten(J['wr_f'], hf, L=0.18, W=0.12, seed=3)
    o['far_sleeve'] = sleeve(B, J['sh_f'], J['el_f'], J['wr_f'], D, HAORI, HAORI_D, hang=P.get('hang_f', 0.24), seed=1)
    o['near_arm'] = B.limb([J['sh_n'], J['el_n'], J['wr_n']], seed=5) + B.mitten(J['wr_n'], hn, L=0.18, W=0.12, seed=5)
    o['near_sleeve'] = sleeve(B, J['sh_n'], J['el_n'], J['wr_n'], D, HAORI, HAORI_D, hang=P.get('hang_n', 0.24), seed=2)
    vis_from = F.w((L['nt'][0], L['nt'][1] + 0.06))
    o['neck'] = B.neck(J['nt'], J['nb'], w=0.17, vis_from=vis_from)
    o['head'] = face.svg(hc[0], hc[1])
    info = dict(face=face)
    # cup in the far hand
    cp = B.hand_pt(J['wr_f'], hf, 0.62, 0.0, L=0.18, W=0.12)
    cup_c = (cp[0] + P.get('cup_dx', 0.0) * D * facing, cp[1] - 0.06 * D + P.get('cup_dy', 0.0) * D)
    o['cup'] = yunomi(cup_c[0], cup_c[1], D, rot=P.get('cup_rot', 0) * facing, seed=90 + seed, steam=P.get('steam', True)) + \
        B.thumb(B.hand_pt(J['wr_f'], hf, 0.70, -0.55 * facing, L=0.18, W=0.12), F.a(-70), ln=0.05, r=0.028, seed=9)
    info['cup'] = cup_c
    order = P.get('order', ('far_leg', 'near_leg', 'far_sleeve', 'far_arm', 'spine', 'costume', 'neck', 'head', 'cup', 'near_sleeve', 'near_arm'))
    fig = ''.join(o[k] for k in order)
    top = hc[1] - (0.5 + 0.075) * D
    sole = max(J['an_f'][1], J['an_n'][1]) + 0.04 * D
    return dict(svg=fig, J=J, L=L, info=info, face=face, F=F, B=B, ext=(top, sole))


def hiko_fig(hc, D, facing, expr, P, light, seed=0, front_ear=False):
    F = Frame(hc, D, facing)
    face = BigFace(D, 'hiko', facing=facing, rot=P.get('head_rot', 0.0) * facing, turn=P.get('turn', 0.12), far_k=P.get('far_k', 0.76),
                   light=light_vec(light, hc), expr=expr, front_ear=front_ear, seed=31 + seed, world=hc)
    B = Body(D, light, skin=SKIN_H, seed=600 + seed, tag='hiko', limb=(0.066, 0.046), spine=(0.07, 0.058))
    L, J = skeleton(F, P)
    o = {}
    o['far_leg'] = B.limb([J['hip_f'], J['kn_f'], J['an_f']], seed=1) + cuff(B, J['kn_f'], J['an_f'], D, PERS, PERS_D, seed=1) + \
        shoe(B, J['an_f'], F.a(P.get('toe_f', 0)), facing, 'jika', seed=1, L=0.30)
    o['near_leg'] = B.limb([J['hip_n'], J['kn_n'], J['an_n']], seed=2) + cuff(B, J['kn_n'], J['an_n'], D, PERS, PERS_D, seed=2) + \
        shoe(B, J['an_n'], F.a(P.get('toe_n', 0)), facing, 'jika', seed=2, L=0.30)
    o['spine'] = B.spine(J['curve'], seed=4)
    o['costume'] = hiko_costume(B, L, F, D, seed=seed)
    hf = F.a(P.get('hand_f', ang_of(L['el_f'], L['wr_f'])))
    hn = F.a(P.get('hand_n', ang_of(L['el_n'], L['wr_n'])))
    o['far_arm'] = B.limb([J['sh_f'], J['el_f'], J['wr_f']], seed=3) + B.mitten(J['wr_f'], hf, L=0.21, W=0.14, skin=SKIN_H, seed=3)
    o['far_sleeve'] = sleeve(B, J['sh_f'], J['el_f'], J['wr_f'], D, PERS, PERS_D, wide=False, seed=1)
    o['near_arm'] = B.limb([J['sh_n'], J['el_n'], J['wr_n']], seed=5) + B.mitten(J['wr_n'], hn, L=0.21, W=0.14, skin=SKIN_H, seed=5)
    o['near_sleeve'] = sleeve(B, J['sh_n'], J['el_n'], J['wr_n'], D, PERS, PERS_D, wide=False, seed=2)
    vis_from = F.w((L['nt'][0], L['nt'][1] + 0.06))
    o['neck'] = B.neck(J['nt'], J['nb'], w=0.17, vis_from=vis_from, skin=SKIN_H)
    o['head'] = face.svg(hc[0], hc[1])
    order = P.get('order', ('far_leg', 'far_arm', 'far_sleeve', 'near_leg', 'spine', 'costume', 'neck', 'head', 'near_arm', 'near_sleeve'))
    fig = ''.join(o[k] for k in order)
    top = hc[1] - (0.5 + 0.17) * D
    sole = max(J['an_f'][1], J['an_n'][1]) + 0.05 * D
    return dict(svg=fig, J=J, L=L, face=face, F=F, B=B, ext=(top, sole), hand=(J['wr_f'], J['wr_n'], hf, hn))
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
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="{1760 - FLOOR}" fill="{TATAMI}"/>')
    o.append(f'<rect x="0" y="{FLOOR}" width="{W}" height="10" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M0 1418 L{W} 1406 L{W} 1418 L0 1431 Z" fill="{TATAMI_D}"/>')
    o.append(f'<path d="M640 {FLOOR} L652 {FLOOR} L740 1760 L726 1760 Z" fill="{TATAMI_D}"/>')
    o.append(f'<ellipse cx="250" cy="1560" rx="360" ry="90" fill="{AMBER}" opacity="0.10"/>')
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
    o.append(f'<rect x="0" y="1760" width="{W}" height="{H - 1760}" fill="{TATAMI_D}"/>')


# =====================================================================
# EXPRESSIONS (Tama)
# =====================================================================
TAMA_EXPR = [
    ('neutral', dict(mode=('closed', 'closed'), closed=('u', 'u'), mouth='rest'), 0),
    ('surprised', dict(mode=('pop', 'pop'), gaze=(0.0, 0.05), brow_dy=(-0.05, -0.05), brow_bend=(0.01, 0.01), mouth='o',
                       marks=(('pop_lines',),)), -4),
    ('angry', dict(mode=('open', 'open'), lid=(0.46, 0.46), tilt=(22, 22), arch=(0.0, 0.0), gaze=(0.15, 0.1), brow_dy=(0.04, 0.04),
                   brow_ang=(26, 26), mouth='grit', marks=(('vein', -0.30, -0.33, 0.15),)), 5),
    ('smug', dict(mode=('closed', 'open'), closed=('n', 'n'), lid=(None, 0.52), low=(0.0, 0.16), lowarch=(0.0, 0.25),
                  arch=(0.14, 0.04), gaze=(1.0, 0.15), brow_dy=(0.025, -0.045), brow_ang=(-4, -12), mouth='smirk'), -6),
    ('panic', dict(mode=('open', 'open'), lid=(0.10, 0.10), tilt=(-15, -15), arch=(0.24, 0.24), gaze=(0.25, 1.0), pupil=0.105, brow_dy=(-0.04, -0.04), brow_ang=(-24, -24),
                   mouth='panic', marks=(('sweat', 0.52, -0.34, 0.07, 18), ('sweat', -0.60, -0.16, 0.06, -20), ('shake',))), 0),
    ('side-eye', dict(mode=('open', 'open'), lid=(0.56, 0.56), arch=(0.02, 0.02), low=(0.10, 0.10), gaze=(1.0, 0.08),
                      brow_dy=(0.035, 0.0), brow_ang=(8, -6), mouth='flat', marks=(('puff', 0.50, 0.36, 0.055),)), 3),
]


def bust(hc, D, facing, light):
    """Neck stub + haori shoulders with lapels, cream under-collar and kimono V: the costume anchor."""
    f = facing
    s = ''
    x0, y0 = hc
    nt = (x0 - f * 0.06 * D, y0 + 0.38 * D)
    nb = (x0 - f * 0.10 * D, y0 + 0.70 * D)
    B = Body(D, light, skin=SKIN_M, seed=900)
    sh = catmull([(x0 - f * 0.78 * D, y0 + 1.4 * D), (x0 - f * 0.70 * D, y0 + 0.86 * D), (x0 - f * 0.40 * D, y0 + 0.66 * D),
                  (x0 + f * 0.10 * D, y0 + 0.64 * D), (x0 + f * 0.48 * D, y0 + 0.74 * D), (x0 + f * 0.62 * D, y0 + 1.0 * D),
                  (x0 + f * 0.66 * D, y0 + 1.4 * D)], closed=True, n=6)
    s += B.neck(nt, nb, w=0.17, vis_from=(nt[0], nt[1] + 0.06 * D))
    rv = B.rimv(sh, 5.0)
    s += rimlit(sh, HAORI, (-rv[0], -rv[1])) + ring(sh, 0.024 * D, 0.03 * D, seed=901)
    cid = f'bs{uid()}'
    s += f'<clipPath id="{cid}"><path d="{d_of(sh)}"/></clipPath><g clip-path="url(#{cid})">'
    wedge = [(x0 - f * 0.12 * D, y0 + 0.62 * D), (x0 + f * 0.16 * D, y0 + 0.62 * D), (x0 + f * 0.10 * D, y0 + 1.5 * D), (x0 - f * 0.05 * D, y0 + 1.5 * D)]
    s += P_(wedge, KIMONO)
    s += '</g>'
    for k, (a, b) in enumerate((((x0 - f * 0.20 * D, y0 + 0.64 * D), (x0 + f * 0.02 * D, y0 + 1.4 * D)),
                                ((x0 + f * 0.22 * D, y0 + 0.66 * D), (x0 + f * 0.16 * D, y0 + 1.4 * D)))):
        s += brush([a, lerp(a, b, 0.5), b], 0.075 * D, color=HAORI_D, seed=910 + k, taper=(0, 0), wob=0.4)
    v0 = (x0 - f * 0.16 * D, y0 + 0.63 * D)
    v1 = (x0 + f * 0.04 * D, y0 + 0.98 * D)
    v2 = (x0 + f * 0.17 * D, y0 + 0.64 * D)
    for k, (a, b) in enumerate(((v0, v1), (v2, v1))):
        s += brush([a, lerp(a, b, 0.5), b], 0.06 * D + 6, color=INK, taper=(0.0, 0.3), wmin=0.03 * D + 4, seed=920 + k, wob=0.5)
        s += brush([a, lerp(a, b, 0.5), b], 0.06 * D, color=CREAM, taper=(0.0, 0.3), wmin=0.03 * D, seed=920 + k, wob=0.5)
    return s


def faces_svg():
    W, H = 1080, 1080
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{MOON}"/>']
    D = 236.0
    for idx, (name, ex, rot) in enumerate(TAMA_EXPR):
        col, row = idx % 3, idx // 3
        cx, cy = 180 + col * 360, 222 + row * 540
        o.append(f'<circle cx="{cx}" cy="{cy + 20}" r="200" fill="#DDD5C2"/>')
        light = (cx - 600, cy - 400)
        o.append(bust((cx, cy), D, -1, light))
        face = BigFace(D, 'tama', facing=-1, rot=-rot, turn=0.09, far_k=0.80, light=light_vec(light, (cx, cy)), expr=ex,
                       front_ear=True, seed=11 + idx, world=(cx, cy))
        o.append(face.svg(cx, cy))
    o.append('</svg>')
    return '\n'.join(o)


# =====================================================================
# SCENE
# =====================================================================
def tama_scene_pose():
    return dict(nt=(-0.10, 0.42), nb=(-0.27, 0.63), hip=(-0.42, 1.62), bow=0.17, sh=0.20, yoke=0.07,
                ua=0.52, fa=0.50, th=0.66, sn=0.63, hipw=0.04,
                wr_f=(0.18, 1.06), el_f=1, hand_f=-14,
                wr_n=(-0.70, 1.40), el_n=1, hand_n=10,
                an_n=(-0.52, 2.90), kn_n=-1, toe_n=4,
                an_f=(0.42, 2.06), kn_f=-1, toe_f=-30,
                head_rot=-3, turn=0.13, cup_dy=0.0, steam=True, hang_f=0.22, hang_n=0.22)


def hiko_scene_pose(hand_local=(0.72, 1.54)):
    hx, hy = hand_local
    return dict(nt=(-0.10, 0.42), nb=(-0.30, 0.60), hip=(-0.92, 1.30), bow=0.05, sh=0.26, yoke=0.07,
                ua=0.74, fa=0.72, th=0.84, sn=0.80, hipw=0.05,
                wr_f=(hx + 0.05, hy - 0.10), el_f=1, hand_f=150, wr_n=(hx - 0.12, hy + 0.04), el_n=1, hand_n=160,
                an_f=(-0.28, 2.56), kn_f=-1, toe_f=0, an_n=(-1.60, 2.52), kn_n=-1, toe_n=-20,
                head_rot=-9, turn=0.13)


def scene_svg():
    W, H = 1080, 1920
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    scene_bg(o)
    FLOOR = 1690
    Dt, Dh = 256.0, 262.0
    tp = tama_scene_pose()
    hct = (262.0, FLOOR - (tp['an_n'][1] + 0.04) * Dt)
    hch = (574.0, FLOOR - (2.56 + 0.05) * Dh)
    # Hiko's mittens close on the air where the ball just was (above Tama's flicked tabi)
    foot_w = (hct[0] + tp['an_f'][0] * Dt, hct[1] + tp['an_f'][1] * Dt)
    grab = (foot_w[0] + 0.10 * Dt, foot_w[1] - 0.30 * Dt)
    hp = hiko_scene_pose(((hch[0] - grab[0]) / Dh, (grab[1] - hch[1]) / Dh))
    ball = (404.0, 600.0)
    br = 0.32 * Dt / 2
    tex = dict(mode=('open', 'closed'), closed=('n', 'n'), lid=(0.42, None), low=(0.10, 0.0), lowarch=(0.25, 0.0), arch=(0.04, 0.14),
               look=(hch[0], hch[1] - 10), brow_dy=(-0.045, 0.02), brow_ang=(-12, -4), mouth='smirk')
    hex_ = dict(mode=('open', 'open'), lid=(0.15, 0.15), arch=(0.06, 0.06), look=ball, brow_dy=(-0.05, -0.05), brow_ang=(-16, -16), brow_bend=(0.01, 0.01),
                mouth='o', m_w=0.33 * Dh, m_dy=0.01)
    mt = tama_fig(hct, Dt, 1, tex, tp, LANTERN, seed=0)
    mh = hiko_fig(hch, Dh, -1, hex_, hp, LANTERN, seed=0)
    o.append(f'<ellipse cx="{f1(mt["J"]["an_n"][0] + 10)}" cy="{FLOOR + 2}" rx="120" ry="12" fill="{INK}" opacity="0.30"/>')
    o.append(f'<ellipse cx="{f1((mh["J"]["an_n"][0] + mh["J"]["an_f"][0]) / 2)}" cy="{FLOOR + 2}" rx="280" ry="14" fill="{INK}" opacity="0.26"/>')
    o.append(mh['svg'])
    o.append(mt['svg'])
    wf, wn, hf, hn = mh['hand']
    for i, w in enumerate((wf, wn)):
        o.append(swoosh(w, 0.30 * Dh, 120, 220, n=2, gap=14, w=5, col=INK, seed=540 + i * 3, op=0.6))
    foot = mt['J']['an_f']
    o.append(ghost_ball(grab[0], grab[1], br, op=0.40, col=INK))
    pf = [ellipse(grab[0] - 0.02 * Dt, grab[1] - 0.06 * Dt, 15, 12, n=24), ellipse(grab[0] + 0.07 * Dt, grab[1] - 0.10 * Dt, 12, 10, n=24),
          ellipse(grab[0] + 0.12 * Dt, grab[1] - 0.03 * Dt, 10, 8, n=24)]
    o.append(union(pf, CREAM, 5, 7, seed=545))
    o.append(dotted(qbez((grab[0] + 4, grab[1] - br - 22), ((grab[0] + ball[0]) / 2 + 30, (grab[1] + ball[1]) / 2), (ball[0] + 4, ball[1] + br + 26), 20),
                    3.5, 7.0, gap=32))
    o.append(temari(ball[0], ball[1], br, seed=500, bell_side=1))
    o.append(ting(ball[0] - br - 34, ball[1] - br + 4, 0.95, seed=560, base=-150))
    o.append('</svg>')
    print('scene: tama hc=(%.0f,%.0f) hiko hc=(%.0f,%.0f) grab=(%.0f,%.0f)' % (hct[0], hct[1], hch[0], hch[1], grab[0], grab[1]))
    return '\n'.join(o), mt, mh


# =====================================================================
# LINEUP FIGURES (hero / partner)
# =====================================================================
def tama_lineup_pose():
    return dict(nt=(-0.10, 0.42), nb=(-0.27, 0.63), hip=(-0.40, 1.62), bow=0.18, sh=0.20, yoke=0.07,
                ua=0.52, fa=0.50, th=0.66, sn=0.64, hipw=0.04,
                wr_f=(0.14, 1.12), el_f=1, hand_f=-12,
                wr_n=(-0.70, 1.42), el_n=1, hand_n=10,
                an_n=(-0.62, 2.90), kn_n=-1, toe_n=-4, an_f=(-0.18, 2.92), kn_f=-1, toe_f=6,
                head_rot=4, turn=0.12, steam=True, hang_f=0.22, hang_n=0.22)


def hiko_lineup_pose():
    return dict(nt=(-0.10, 0.42), nb=(-0.24, 0.64), hip=(-0.56, 1.68), bow=0.07, sh=0.26, yoke=0.07,
                ua=0.76, fa=0.74, th=0.80, sn=0.78, hipw=0.06,
                wr_f=(0.06, 1.90), el_f=1, hand_f=96, wr_n=(-0.28, 1.96), el_n=1, hand_n=92,
                knee_f=(-0.36, 2.45), an_f=(0.00, 3.16), toe_f=22, knee_n=(-0.48, 2.48), an_n=(-0.86, 3.16), toe_n=-6,
                head_rot=4, turn=0.12, order=('far_leg', 'far_arm', 'far_sleeve', 'near_leg', 'spine', 'costume', 'neck', 'head', 'near_arm', 'near_sleeve'))


TAMA_LINEUP_EXPR = dict(mode=('closed', 'closed'), closed=('u', 'u'), mouth='rest')
HIKO_LINEUP_EXPR = dict(mode=('open', 'open'), arch=(0.06, 0.06), gaze=(0.85, 0.05), brow_dy=(-0.01, -0.01), brow_ang=(-4, -4), mouth='grin')


def lineup_fig(who, D0=240.0):
    hc = (700.0, 500.0)
    light = ('dir', (-0.6, -0.8))
    if who == 'tama':
        m = tama_fig(hc, D0, -1, TAMA_LINEUP_EXPR, tama_lineup_pose(), light, seed=0)
    else:
        m = hiko_fig(hc, D0, -1, HIKO_LINEUP_EXPR, hiko_lineup_pose(), light, seed=0)
    return m


def raw_svg(who):
    m = lineup_fig(who)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="2400" viewBox="0 0 1400 2400">'
            f'<defs><filter id="blk"><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></defs>'
            f'<rect width="1400" height="2400" fill="#FFFFFF"/><g filter="url(#blk)">{m["svg"]}</g></svg>')


def bbox_of(png):
    from PIL import Image
    im = Image.open(png).convert('L')
    px = im.load()
    w, h = im.size
    ys = [y for y in range(h) if any(px[x, y] < 128 for x in range(0, w, 2))]
    xs = [x for x in range(w) if any(px[x, y] < 128 for y in range(ys[0], ys[-1] + 1, 2))]
    return xs[0], ys[0], xs[-1], ys[-1]


def lineup_svg(who, target, sil=False):
    W, H = 540, 1080
    D0 = 240.0
    m = lineup_fig(who, D0)
    x0, y0, x1, y1 = bbox_of(os.path.join(HERE, f'_{who}_raw.png'))
    k = target / (y1 + 1 - y0)
    sole_y = 1010.0
    ty = sole_y - (y1 + 1) * k
    cx_fig = (x0 + x1) / 2
    tx = 270 - cx_fig * k
    T = f'translate({tx:.2f} {ty:.2f}) scale({k:.5f})'
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    if sil:
        o.append(f'<defs><filter id="blk"><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></defs>')
        o.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/><g transform="{T}" filter="url(#blk)">{m["svg"]}</g>')
    else:
        o.append(f'<rect width="{W}" height="{H}" fill="{LINEUP_BG}"/>')
        o.append(f'<ellipse cx="270" cy="{sole_y + 4}" rx="170" ry="12" fill="{INK}" opacity="0.16"/>')
        o.append(f'<g transform="{T}">{m["svg"]}</g>')
    o.append('</svg>')
    Deff = D0 * k
    print(f'{who}: k={k:.4f} D_eff={Deff:.1f}px top={y0 * k + ty:.1f} sole={(y1 + 1) * k + ty:.1f} H={target} head/H={Deff / target:.3f} '
          f'x-range={x0 * k + tx:.0f}..{x1 * k + tx:.0f}')
    return '\n'.join(o)


def write(name, s):
    with open(os.path.join(HERE, name), 'w') as fh:
        fh.write(s)


def rule_report():
    for who in ('tama', 'hiko'):
        c = CHAR[who]
        f = BigFace(240.0, who, turn=0.12, far_k=0.76)
        lay = f.eye_layout()
        wn, wf = c['eye_w_pop'], c['eye_w_pop'] * 0.76
        span = wn + c['gap'] + wf
        print(f"{who}: eye_h={c['eye_h']:.2f}D (pop {c['eye_h_pop']:.2f}) w={c['eye_w']:.2f}/{c['eye_w_pop']:.2f}D centre={0.5 + c['eye_y']:.3f}D below top "
              f"top={0.5 + c['eye_y'] - c['eye_h_pop'] / 2:.3f}D gap={c['gap']:.2f}D span3/4={span:.2f}D pupil={c['pupil']:.3f}D "
              f"({c['pupil'] / (c['eye_w'] * 0.76):.0%} of far-eye width) lid={c['lidw']:.3f}D rim={c['rim']:.3f}D")


if __name__ == '__main__':
    rule_report()
    if len(sys.argv) > 1 and sys.argv[1] == 'raw':
        write('_tama_raw.svg', raw_svg('tama'))
        write('_hiko_raw.svg', raw_svg('hiko'))
        print('raw ok')
        sys.exit(0)
    sc, mt, mh = scene_svg()
    write('scene.svg', sc)
    sil = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">'
           f'<defs><filter id="blk"><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></defs>'
           f'<rect width="1080" height="1920" fill="#FFFFFF"/><g filter="url(#blk)">{mh["svg"]}</g>'
           f'<g filter="url(#blk)" opacity="0.55">{mt["svg"]}</g></svg>')
    write('_scene_sil.svg', sil)
    write('faces.svg', faces_svg())
    write('hero.svg', lineup_svg('tama', 780.0))
    write('partner.svg', lineup_svg('hiko', 900.0))
    write('_hero_sil.svg', lineup_svg('tama', 780.0, sil=True))
    write('_partner_sil.svg', lineup_svg('hiko', 900.0, sil=True))
    print('ok')
