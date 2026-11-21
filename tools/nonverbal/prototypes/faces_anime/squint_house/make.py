#!/usr/bin/env python3
"""Squint House / 糸目の茶屋 -- ANIME-EYE version (Tama = hero, Hiko = partner).

One face rig  : BigFace(D, who, facing, rot, turn, far_k, expr)  -> head SVG; one shared anime-eye construction
                (sclera, lid band, 3-tone iris + limbal ring, pupil, catchlights, lash line, lower line, creases, brow)
                draws Tama's closed arcs / peek / pop ovals and Hiko's nekketsu U-eyes.
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
# ANIME-EYE FACE RIG
# =====================================================================
SCLERA = '#FBF6EA'      # warm off-white, never #FFFFFF
LIDBAND = '#DCD3C3'     # lid shadow band over the white
HLW = '#FFFFFF'         # catchlights: the only pure white on a face

# Character constants, all in D (skull diameter). Eye footprint = fully opened eye incl. the upper lash line.
CHAR = {
    'tama': dict(skin=SKIN_M, ear='long', brow='tuft', nose='round', hair='tenugui', jaw=0.15, age=True, stubble=False,
                 mouth_y=0.345, nose_y=0.170, goatee=True,
                 eye=dict(shape='oval', w=0.43, h=0.58, pop_w=0.44, pop_h=0.60, gap=0.09, gap_pop=0.085, cy=-0.025,
                          iris=('#F0B01A', '#B37C08', '#FFD978', '#7A5305'), pupil='#3A2702',
                          iris_h=0.45, iris_pop=0.46, iris_shock=0.31, aspect=0.82, pupil_k=0.40,
                          hl='star', lash=0.055, end='taper', low=0.020, rest='closed', follow=0.55,
                          closed_w=0.44, sag=0.08, socket=(0.48, 0.32), socket_col='#96643F',
                          crow=True, bag=True, crease=True, under=False)),
    'hiko': dict(skin=SKIN_H, ear='std', brow='ink', nose='tri', hair='buzz', jaw=0.0, age=False, stubble=True,
                 mouth_y=0.345, mouth_dx=-0.02,
                 eye=dict(shape='nekketsu', w=0.42, h=0.54, pop_w=0.43, pop_h=0.58, gap=0.085, gap_pop=0.08, cy=-0.015,
                          slant=10.0, iris=('#B8323A', '#7A1A24', '#E25A5E', '#4A0C14'), pupil='#1E0609',
                          iris_h=0.43, iris_pop=0.44, iris_shock=0.30, aspect=0.84, pupil_k=0.40,
                          hl='two_dots', lash=0.060, end='square', low=0.022, rest=0.12, follow=1.0,
                          closed_w=0.40, sag=0.05, crow=False, bag=False, crease=False, under=True)),
}

EXPR_DEF = dict(
    mode=('open', 'open'),          # per eye (near, far): 'open' | 'closed' | 'pop'
    cov=(None, None),               # upper-lid coverage of the footprint height at the centre (None = rest)
    slant=(0.0, 0.0),               # lid slant, deg: + = lid runs down toward the nose (anger), - = inner end up (worry)
    sag=(0.0, 0.0),                 # both lid ends sag (sleepy)
    low=(0.0, 0.0),                 # lower-lid rise (fraction of footprint height)
    lowarch=(0.0, 0.0),             # + = lower lid bulges up in the middle (smug)
    closed=('u', 'u'),              # 'u' content arc, 'n' joy ^, 'flat' sipping, 'wedge' > <
    iris=(None, None),              # iris height override (D)
    gaze=(0.0, 0.0), look=None, gmag=1.0,
    hl=(1.0, 1.0),                  # catchlight scale, 0 = off (deadpan)
    wobble=0.0, tear=(False, False),
    brow_dy=(0.0, 0.0), brow_ang=(0.0, 0.0), brow_bend=(0.0, 0.0),
    mouth='rest', m_dx=0.0, m_dy=0.0, m_rot=0.0, m_w=None,
    marks=(), mark_col=INK,
    fp=None,                        # (w, h) footprint override in D for an 'open' eye (panic: wider than tall)
)


def poly_vspan(P, x):
    ys = []
    n = len(P)
    for j in range(n):
        x0, y0 = P[j]
        x1, y1 = P[(j + 1) % n]
        if (x0 <= x < x1) or (x1 <= x < x0):
            t = (x - x0) / (x1 - x0)
            ys.append(y0 + (y1 - y0) * t)
    if len(ys) < 2:
        return None
    return min(ys), max(ys)


def fp_poly(shape, w, h, slant=0.0, wob=0.0, seed=0):
    """Eye footprint outline in eye space: origin = footprint centre, +x toward the nose, y down."""
    if shape == 'oval':
        P = ellipse(0, 0, w / 2, h / 2, n=140)
    else:   # nekketsu: straight lash bar angled down toward the nose over a round U bottom
        s = w * math.tan(math.radians(slant))

        def tp(xf):
            return -0.5 * h + s * (xf + 0.5)
        C = [(-0.50 * w, tp(-0.5) + 0.075 * h), (-0.46 * w, tp(-0.46) + 0.008 * h), (-0.30 * w, tp(-0.30)), (0.0, tp(0.0)),
             (0.25 * w, tp(0.25)), (0.42 * w, tp(0.42) + 0.006 * h), (0.50 * w, tp(0.50) + 0.075 * h),
             (0.49 * w, 0.10 * h), (0.40 * w, 0.33 * h), (0.20 * w, 0.47 * h), (0.0, 0.50 * h), (-0.20 * w, 0.47 * h),
             (-0.40 * w, 0.33 * h), (-0.49 * w, 0.10 * h)]
        P = catmull(C, closed=True, n=12)
        ys = [p[1] for p in P]
        dy = -(max(ys) + min(ys)) / 2
        P = [(x, y + dy) for x, y in P]
    if wob:
        nz = Noise(seed + 900, 3)
        Q = []
        for x, y in P:
            a = math.atan2(y, x)
            r = 1 + wob * nz(a * 3.0) / max(w, h) * 2
            Q.append((x * r, y * r))
        P = Q
    return P


def star_arms(x, y, L, hb, rot=0.0):
    """Four-arm catchlight star: each arm L long from the centre, half-width hb at the root, concave taper to a point."""
    out = []
    for k in range(4):
        a = math.radians(rot - 90 + 90 * k)
        ca, sa = math.cos(a), math.sin(a)
        side_a, side_b = [], []
        n = 14
        for j in range(n + 1):
            u = j / n
            sdist = L * u
            hwid = hb * (1 - u) ** 1.35 + 0.004 * L * (1 - u)
            side_a.append((x + ca * sdist - sa * hwid, y + sa * sdist + ca * hwid))
            side_b.append((x + ca * sdist + sa * hwid, y + sa * sdist - ca * hwid))
        out.append(side_a + side_b[::-1])
    return out


def star_pts(x, y, r, waist=0.24, rot=0.0):
    P = []
    for j in range(16):
        a = math.radians(j * 22.5 - 90 + rot)
        rr = r if j % 4 == 0 else (r * waist if j % 2 == 0 else r * waist * 0.85)
        P.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return P


class BigFace:
    """One rig for both round heads, with the shared anime-eye construction.
    Local frame: origin = skull centre, +x = facing side, y down, units px (D = skull diameter).
    Group transform: translate(cx cy) rotate(rot) scale(facing 1)."""

    def __init__(self, D, who, facing=1, rot=0.0, turn=0.12, far_k=0.62, light=(-0.8, -0.6), expr=None,
                 front_ear=False, seed=11, world=None):
        self.D, self.who, self.facing, self.rot, self.turn = D, who, facing, rot, turn
        self.far_k = far_k
        self.c = dict(CHAR[who])
        self.E = dict(self.c['eye'])
        self.e = dict(EXPR_DEF)
        if expr:
            self.e.update(expr)
        self.front_ear = front_ear
        self.seed = seed
        self.skin = self.c['skin']
        self.skin_d = shade(self.skin, 0.13)
        self.skin_dd = shade(self.skin, 0.30)
        self.lidtone = shade(self.skin, 0.07)
        self.world_c = world
        lx, ly = light
        lx, ly = rot2((lx, ly), -rot)
        lx *= facing
        l = math.hypot(lx, ly) or 1
        self.L = (lx / l, ly / l)
        # catchlight side: screen upper-left, expressed in the local frame
        hx, hy = rot2((-1.0, -1.0), -rot)
        hx *= facing
        self.hl_side = 1 if hx > 0 else -1
        self.gx = 1.36 * turn * D          # centre of the gap between the eyes (nose bridge)

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

    def eye_layout(self, pop=False):
        """(ex, ey, k, inner) for near (i=0) and far (i=1) eye. Near eye full width, far eye far_k, the pair shifted
        toward the facing side by the turn; the nose bridge sits in the gap."""
        E, D = self.E, self.D
        Wn = (E['pop_w'] if pop else E['w']) * D
        g = (E['gap_pop'] if pop else E['gap']) * D
        kf = self.far_k
        Wf = Wn * kf
        ey = E['cy'] * D
        return [(self.gx - g / 2 - Wn / 2, ey, 1.0, 1), (self.gx + g / 2 + Wf / 2, ey, kf, -1)]

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

    # ---------------------------------------------------------- eye
    def eye(self, i):
        E, e, D = self.E, self.e, self.D
        mode = self.per('mode', i)
        pop = mode == 'pop'
        ex, ey, k, inner = self.eye_layout(pop)[i]
        if mode == 'closed':
            return self.closed_eye(i, ex, ey, k, inner)
        W = lambda x, y: (ex + inner * x, ey + y)
        w = (E['pop_w'] if pop else E['w']) * D * k
        h = (E['pop_h'] if pop else E['h']) * D
        if e.get('fp') and not pop:
            w, h = e['fp'][0] * D * k, e['fp'][1] * D
        hw = w / 2
        wob = e['wobble'] * D
        P = fp_poly(E['shape'], w, h, E.get('slant', 0.0), wob, self.seed + i)
        cov = self.per('cov', i)
        if cov is None:
            cov = E['rest'] if isinstance(E['rest'], float) else 0.25
        if pop:
            cov = min(cov, 0.03)
        slant_e = math.tan(math.radians(self.per('slant', i)))
        sag_e = self.per('sag', i)
        lowc, lowa = self.per('low', i), self.per('lowarch', i)
        t0, b0 = poly_vspan(P, 0.0)
        shape_slope = math.tan(math.radians(E.get('slant', 0.0))) if E['shape'] == 'nekketsu' else 0.0
        fol = E['follow']

        def lid(x, top):
            return fol * top + (1 - fol) * (t0 + shape_slope * x) + cov * h + slant_e * x + sag_e * h * (x / hw) ** 2

        def lowl(x):
            return b0 - lowc * h - lowa * h * (1 - (x / hw) ** 2)
        N = 90
        xs = [-hw * math.cos(math.pi * j / N) for j in range(N + 1)]
        xs[0] += 0.004 * hw
        xs[-1] -= 0.004 * hw
        vis, covr, fp = [], [], []
        Rin = (0.47 if pop else 0.46) * D      # outer corners stay >= 0.02 D inside the rim (incl. its ink); a pop may come closer
        for x in xs:
            sp = poly_vspan(P, x)
            if sp is None:
                continue
            top, bot = sp
            X = ex + inner * x
            if abs(X) >= Rin:
                continue
            yy = math.sqrt(Rin * Rin - X * X)
            top, bot = max(top, -yy - ey), min(bot, yy - ey)
            if bot <= top + 0.5:
                continue
            fp.append((x, top, bot))
            Lw = lid(x, top)
            a = max(top, Lw)
            b = min(bot, lowl(x)) if (lowc > 0 or lowa > 0) else bot
            if b > a + 0.4:
                vis.append((x, a, b))
            if Lw > top:
                covr.append((x, top, min(Lw, bot)))
        out = []
        info = dict(ex=ex, ey=ey, k=k, inner=inner, top=ey + t0, bot=ey + b0, hw=hw, h=h)
        # 1 lid tone over the covered part of the footprint (shows the big footprint even when the lid is down)
        if covr:
            Pc = [W(x, a) for x, a, b in covr] + [W(x, b) for x, a, b in covr[::-1]]
            out.append(P_(Pc, self.lidtone))
        if not vis:
            return ''.join(out), info
        Pv = [W(x, a) for x, a, b in vis] + [W(x, b) for x, a, b in vis[::-1]]
        cid = f'ev{uid()}'
        out.append(f'<clipPath id="{cid}"><path d="{d_of(Pv)}"/></clipPath>')
        g = [f'<g clip-path="url(#{cid})">', P_(Pv, SCLERA)]
        band_w = 0.045 * D
        band = [W(x, a - 2) for x, a, b in vis] + [W(x, a + band_w) for x, a, b in vis[::-1]]
        g.append(P_(band, LIDBAND))
        # ---- iris
        ih = self.per('iris', i)
        if ih is None:
            ih = E['iris_pop'] if pop else E['iris_h']
        ih *= D
        kc = 1.0 if i == 0 else max(0.68, k)
        gxl, gyl = self.gaze_for(i, ex, ey)
        gu = max(-1.0, min(1.0, gxl * inner))
        iw = ih * E['aspect'] * kc * (1 - 0.30 * abs(gu) ** 1.5)
        # visible top at the centre
        a_c = min(vis, key=lambda v: abs(v[0]))[1]
        b_c = min(vis, key=lambda v: abs(v[0]))[2]
        if pop or cov < 0.04:
            icy = (t0 + b0) / 2 + 0.01 * D
        else:
            icy = a_c - 0.04 * D + ih / 2
        icx = gu * max(0.0, (hw - iw / 2)) * 0.97
        vr = max(0.05 * D, ((b0 - t0) / 2 - ih / 2) * 0.85) if cov < 0.15 else 0.06 * D
        icy += gyl * vr
        icy = min(icy, b_c - ih / 2 + 0.03 * D) if not pop else icy
        IX, IY = ex + inner * icx, ey + icy
        Ei = ellipse(IX, IY, iw / 2, ih / 2, n=72)
        iid = f'ir{uid()}'
        base, sh, lt, rg = E['iris']
        g.append(f'<clipPath id="{iid}"><path d="{d_of(Ei)}"/></clipPath><g clip-path="url(#{iid})">')
        g.append(P_(Ei, base))
        Es = ellipse(IX, IY - 0.10 * ih, iw / 2 * 0.97, ih / 2 * 0.96, n=72)
        g.append(f'<path d="{d_of(Ei)} {d_of(Es)}" fill="{lt}" fill-rule="evenodd"/>')
        cut = IY - ih / 2 + 0.34 * ih
        shp = [(IX - iw, IY - ih)] + [(IX - iw + 2 * iw * j / 16, cut + 0.06 * ih * (1 - ((j - 8) / 8) ** 2)) for j in range(17)] + [(IX + iw, IY - ih)]
        g.append(P_(shp, sh))
        bandi = [W(x, a - 2) for x, a, b in vis] + [W(x, a + band_w) for x, a, b in vis[::-1]]
        g.append(P_(bandi, sh))
        ph = E['pupil_k'] * ih
        pw = ph * 0.86 * kc * (1 - 0.30 * abs(gu) ** 1.5)
        g.append(P_(ellipse(IX + inner * gu * 0.06 * iw, IY + 0.02 * ih, pw / 2, ph / 2, n=48), E['pupil']))
        rw = 0.018 * D
        Ein = ellipse(IX, IY, max(1, iw / 2 - rw), max(1, ih / 2 - rw), n=72)
        g.append(f'<path d="{d_of(Ei)} {d_of(Ein)}" fill="{rg}" fill-rule="evenodd"/>')
        g.append('</g>')
        # ---- catchlights (one light direction: screen upper-left)
        hs = self.per('hl', i)
        if hs > 0:
            side = self.hl_side
            def clamp_vis(px, py, r):
                # keep the catchlight below the lid line
                xu = (px - ex) * inner
                vv = min(vis, key=lambda v: abs(v[0] - xu))
                return px, max(py, ey + vv[1] + r * 0.95)
            if E['hl'] == 'star':
                L = 0.112 * D * hs
                px, py = IX + side * 0.06 * iw, IY - 0.16 * ih      # kept inside the iris so all four arms read (over the pupil)
                px, py = clamp_vis(px, py, L * 0.45)
                for arm in star_arms(px, py, L, 0.034 * D * hs, rot=8):
                    g.append(P_(arm, HLW))
                g.append(f'<circle cx="{f1(px)}" cy="{f1(py)}" r="{f1(0.030 * D * hs)}" fill="{HLW}"/>')
                r2 = 0.024 * D * max(0.7, hs)
                g.append(f'<circle cx="{f1(IX - side * 0.26 * iw)}" cy="{f1(IY + 0.27 * ih)}" r="{f1(r2)}" fill="{HLW}"/>')
            elif E['hl'] == 'two_dots':
                r = 0.052 * D * hs
                px, py = IX + side * 0.22 * iw, IY - 0.20 * ih
                px, py = clamp_vis(px, py, r)
                g.append(f'<circle cx="{f1(px)}" cy="{f1(py)}" r="{f1(r)}" fill="{HLW}"/>')
                r2 = 0.026 * D * max(0.8, hs)
                g.append(f'<circle cx="{f1(IX - side * 0.24 * iw)}" cy="{f1(IY + 0.24 * ih)}" r="{f1(r2)}" fill="{HLW}"/>')
        if self.per('tear', i):
            tl = [W(x, b - 0.022 * D) for x, a, b in vis if abs(x) < hw * 0.75]
            if len(tl) > 3:
                g.append(brush(tl, 0.016 * D, color=HLW, seed=self.seed + 77 + i, taper=(0.3, 0.3), wmin=1.0, wob=0.2))
        g.append('</g>')
        out += g
        # ---- upper lash line: darkest, thickest line on the face; tapers to the nose, character ending outside
        TL = [W(x, a) for x, a, b in vis]
        lw = E['lash'] * D
        o0, o1 = TL[0], TL[min(4, len(TL) - 1)]
        dxy = (o0[0] - o1[0], o0[1] - o1[1])
        dl = math.hypot(*dxy) or 1
        dxy = (dxy[0] / dl, dxy[1] / dl)
        wobl = 0.4 + (1.6 if e['wobble'] else 0)
        if E['end'] == 'square':
            ext = (o0[0] + dxy[0] * 0.03 * D * k, o0[1] + dxy[1] * 0.03 * D * k - 0.004 * D)
            out.append(brush([ext] + TL, lw, seed=self.seed + 50 + i, taper=(0.0, 0.30), wmin=lw * 0.30, wob=wobl))
        elif E['end'] == 'taper':
            ext = (o0[0] + dxy[0] * 0.012 * D, o0[1] + dxy[1] * 0.012 * D)
            out.append(brush([ext] + TL, lw, seed=self.seed + 50 + i, taper=(0.16, 0.34), wmin=lw * 0.22, wob=wobl))
        else:
            ext = (o0[0] + dxy[0] * 0.02 * D, o0[1] + dxy[1] * 0.02 * D)
            out.append(brush([ext] + TL, lw, seed=self.seed + 50 + i, taper=(0.06, 0.34), wmin=lw * 0.30, wob=wobl))
            od = -inner
            tick = [(ext[0] - od * 0.012 * D, ext[1] + 0.004 * D), (ext[0] + od * 0.035 * D, ext[1] - 0.030 * D)]
            out.append(brush(tick, lw * 0.80, seed=self.seed + 55 + i, taper=(0.0, 0.75), wmin=1.2, smooth=False))
        # ---- lower lash / lid line
        BL = [W(x, b + E['low'] * D * 0.25) for x, a, b in vis]
        if len(BL) > 3:
            lwl = E['low'] * D * (1.25 if (lowc > 0 or lowa > 0) else 1.0)
            out.append(brush(BL, lwl, seed=self.seed + 30 + i, taper=(0.18, 0.12), wmin=lwl * 0.4, wob=0.3 + (1.2 if e['wobble'] else 0)))
        # ---- creases / bags / crow's-feet (adult cues)
        cr = 0.016 * D
        if pop:
            arc = [W(x, top - 0.055 * D) for x, top, bot in fp if abs(x) < hw * 0.72]
            if len(arc) > 3:
                out.append(brush(arc, cr, color=self.skin_dd, seed=self.seed + 40 + i, taper=(0.3, 0.3), wmin=1.0, wob=0.3))
        elif E['crease']:
            arc = [W(x, a - 0.06 * D) for x, a, b in vis if abs(x) < hw * 0.70]
            if len(arc) > 3:
                out.append(brush(arc, cr, color=self.skin_dd, seed=self.seed + 40 + i, taper=(0.3, 0.3), wmin=1.0, wob=0.3))
        od = -inner
        if E['crow']:
            ocx = min(vis, key=lambda v: v[0])
            cf = W(ocx[0] - 0.035 * D, (ocx[1] + ocx[2]) / 2)
            base_a = 0 if od > 0 else 180
            for j, (aa, st, ln) in enumerate(((-30, 0.00, 0.055), (0, 0.00, 0.065), (30, 0.00, 0.050))):
                ang = base_a + (aa if od > 0 else -aa)
                q0 = pol(cf, ang, st * D)
                q1 = pol(cf, ang, (st + ln) * D)
                out.append(brush([q0, q1], 0.016 * D, color=self.skin_dd, seed=self.seed + 60 + j + 5 * i, taper=(0.3, 0.5), wmin=1.0, smooth=False))
        if E['bag']:
            bag = [W(x, b0 + 0.045 * D + 0.015 * D * (1 - (x / hw) ** 2) - 0.015 * D) for x in [hw * t for t in (-0.65, -0.35, 0.0, 0.3, 0.55)]]
            out.append(brush(bag, 0.016 * D, color=self.skin_dd, seed=self.seed + 70 + i, taper=(0.4, 0.4), wmin=1.0, wob=0.3))
        if E['under']:
            un = [W(x, b0 + 0.05 * D - 0.012 * D * (x / hw) ** 2) for x in [hw * t for t in (-0.45, -0.15, 0.15, 0.40)]]
            out.append(brush(un, 0.015 * D, color=self.skin_dd, seed=self.seed + 72 + i, taper=(0.4, 0.4), wmin=1.0, wob=0.3))
        info.update(iris=(IX, IY, iw, ih), vis_top=ey + a_c, vis_bot=ey + b_c, cov=cov)
        return ''.join(out), info

    def closed_eye(self, i, ex, ey, k, inner):
        """Closed eye stays big: a lid line as thick as the lash line, >= 90% of the footprint width,
        at ~58% of the footprint height, with the corner flick, a crease above and crow's-feet."""
        E, D = self.E, self.D
        W = lambda x, y: (ex + inner * x, ey + y)
        kind = self.per('closed', i)
        H = E['h'] * D
        cw = E['closed_w'] * D * k
        hw = cw / 2
        yc = -H / 2 + 0.58 * H
        sag = E['sag'] * D
        lw = E['lash'] * D * 1.05
        out = []
        if E.get('socket'):
            sw, shh = E['socket']
            S = ellipse(ex, ey + yc - 0.045 * D, sw * D * k / 2, shh * D / 2, n=72)
            Rin = 0.455 * D
            S2 = []
            for x, y in S:
                r = math.hypot(x, y)
                S2.append((x * Rin / r, y * Rin / r) if r > Rin else (x, y))
            out.append(P_(S2, blend(self.skin, E['socket_col'], 0.38)))
        N = 24
        pts = []
        for j in range(N + 1):
            t = -1 + 2 * j / N        # outer -> inner
            if kind == 'u':
                y = yc - sag / 2 + sag * (1 - t * t)
            elif kind == 'n':
                y = yc + sag * 0.55 - sag * 1.25 * (1 - t * t)
            elif kind == 'flat':
                y = yc + 0.018 * D * (1 - t * t)
            else:   # wedge > <
                y = yc - 0.10 * D * (1 - (t + 1) / 2) if t < 0.9 else yc
            pts.append((t * hw, y))
        if kind == 'wedge':
            pts = [(-hw, yc - 0.10 * D), (hw * 0.9, yc), (-hw, yc + 0.10 * D)]
            out.append(brush([W(*p) for p in pts], lw, seed=self.seed + 50 + i, taper=(0.1, 0.1), wmin=lw * 0.5, smooth=False))
            return ''.join(out), dict(ex=ex, ey=ey, k=k, inner=inner, top=ey - H / 2, bot=ey + H / 2, hw=hw, h=H)
        P = [W(*p) for p in pts]
        out.append(brush(P, lw, seed=self.seed + 50 + i, taper=(0.06, 0.30), wmin=lw * 0.35, wob=0.4))
        od = -inner
        o = P[0]
        ticks = [((o[0], o[1]), (o[0] + od * 0.024 * D, o[1] + 0.024 * D))]     # one short tick, pointing down (a closed lid, not a lash)
        for j, (q0, q1) in enumerate(ticks):
            out.append(brush([q0, q1], lw * 0.55, seed=self.seed + 55 + j + 3 * i, taper=(0.0, 0.70), wmin=1.2, smooth=False))
        # crease above, following the arc
        cr = [W(x * 0.80, y - 0.062 * D - (0.012 * D if kind == 'n' else 0)) for x, y in pts[3:-3]]
        out.append(brush(cr, 0.017 * D, color=self.skin_dd, seed=self.seed + 40 + i, taper=(0.3, 0.3), wmin=1.0, wob=0.3))
        if E['crow']:
            cf = W(-hw - 0.03 * D, pts[0][1] + 0.012 * D)
            base_a = 0 if od > 0 else 180
            deep = 1.35 if kind == 'n' else 1.0
            for j, (aa, ln) in enumerate(((-28, 0.050), (2, 0.062), (32, 0.048))):
                ang = base_a + (aa if od > 0 else -aa)
                q1 = pol(cf, ang, ln * D * deep)
                out.append(brush([cf, q1], 0.017 * D * (1.15 if kind == 'n' else 1.0), color=self.skin_dd, seed=self.seed + 60 + j + 5 * i,
                                 taper=(0.3, 0.5), wmin=1.0, smooth=False))
        if E['bag']:
            by = yc + sag * 0.5 + 0.075 * D
            bag = [W(x, by + 0.012 * D * (1 - (x / hw) ** 2)) for x in [hw * t for t in (-0.6, -0.3, 0.0, 0.3, 0.55)]]
            out.append(brush(bag, 0.016 * D, color=self.skin_dd, seed=self.seed + 70 + i, taper=(0.4, 0.4), wmin=1.0, wob=0.3))
        return ''.join(out), dict(ex=ex, ey=ey, k=k, inner=inner, top=ey - H / 2, bot=ey + H / 2, hw=hw, h=H, closed_y=ey + yc)

    # ---------------------------------------------------------- brows
    def brow(self, i, info):
        E, e, D = self.E, self.e, self.D
        k = info['k']
        inner = info['inner']
        od = -inner
        ex, ey = info['ex'], info['ey']
        Hr = E['h'] * D
        dy = self.per('brow_dy', i) * D
        ang = self.per('brow_ang', i)
        bend = self.per('brow_bend', i)
        kind = self.c['brow']
        if kind == 'tuft':
            L, T = 0.17 * D * (0.80 + 0.20 * k), 0.056 * D
            by = ey - Hr / 2 + 0.005 * D + dy
            bx = ex + od * 0.02 * D

            def C(u):
                t = u / L
                return (bx + inner * (L / 2 - u), by - (0.016 * D + bend * D) * math.sin(math.pi * t))
            up, lo = [], []
            n = 10
            for j in range(n + 1):
                u = L * j / n
                th = T * (0.60 + 0.40 * math.sin(math.pi * min(1.0, 0.25 + 0.75 * j / n)))
                p = C(u)
                up.append((p[0], p[1] - th / 2))
                lo.append((p[0], p[1] + th / 2))
            o = C(L)
            flick = [(o[0] + od * 0.028 * D, o[1] - 0.026 * D), (o[0] + od * 0.006 * D, o[1] - 0.004 * D),
                     (o[0] + od * 0.032 * D, o[1] + 0.010 * D)]
            P = catmull(up + flick + lo[::-1], closed=True, n=4)
            P = xform(P, rot=ang * inner, ox=bx, oy=by)
            return P_(P, BROW_W) + ring(P, 0.015 * D, 0.019 * D, seed=self.seed + 80 + i, heavy=(0.3, 0.9))
        if kind == 'ink':
            # thick ink bar 0.07 D, 0.03 D above the resting lash bar, angled in (inner end lower)
            w = E['w'] * D * k
            T = 0.070 * D
            s = math.tan(math.radians(E.get('slant', 0.0)))
            rest_top = ey - Hr / 2 + E['rest'] * Hr
            pts = []
            for u in (-0.56, -0.25, 0.10, 0.46):
                x = u * w
                y = rest_top + s * (x + 0.5 * w) - 0.035 * D - 0.03 * D - T / 2 + 0.035 * D * (u + 0.56) - 0.012 * D * math.sin(math.pi * (u + 0.56) / 1.02)
                pts.append((ex + inner * x, y + dy))
            bc = lerp(pts[0], pts[-1], 0.5)
            pts = xform(pts, rot=ang * inner, ox=bc[0], oy=bc[1])
            if bend:
                pts = [(p[0], p[1] - bend * D * math.sin(math.pi * j / 3)) for j, p in enumerate(pts)]
            s_ = brush(pts, T, color=HAIR_K, seed=self.seed + 80 + i, taper=(0.30, 0.06), wmin=T * 0.35, wob=0.5)
            if i == 0:   # the nick in his left brow
                q = lerp(pts[1], pts[2], 0.25)
                aa = ang_of(pts[1], pts[2]) + 72
                n0, n1 = pol(q, aa, -T * 0.9), pol(q, aa, T * 0.9)
                s_ += brush([n0, n1], 0.020 * D, color=self.skin, seed=self.seed + 85, taper=(0.0, 0.0), smooth=False, wob=0.1)
            return s_
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
            cx = 0.07 * D * lx + self.gx * 0.3
            e = ellipse(cx, -0.21 * D, 0.64 * D, (0.71 - c['jaw']) * D, n=96)
            big = [(-D, -D), (D, -D), (D, D), (-D, D)]
            s.append(f'<path d="{d_of(big)} {d_of(e[::-1])}" fill="{self.skin_d}" fill-rule="evenodd"/>')
        s.append('</g>')
        return ''.join(s), cid, P

    def scalp(self, cid):
        """Tama: shaved head, a flat grey stubble tone over the crown (hairline above the forehead)."""
        D = self.D
        gx = self.gx
        hl = [(-0.8 * D, 0.10 * D), (-0.47 * D, 0.06 * D), (-0.43 * D, -0.14 * D), (-0.33 * D, -0.33 * D), (gx - 0.12 * D, -0.425 * D),
              (gx + 0.14 * D, -0.43 * D), (0.36 * D, -0.37 * D), (0.8 * D, -0.30 * D), (0.8 * D, -0.8 * D), (-0.8 * D, -0.8 * D)]
        P = catmull(hl, closed=True, n=6)
        col = blend(self.skin, '#9A938C', 0.42)
        return f'<g clip-path="url(#{cid})"><path d="{d_of(P)}" fill="{col}"/></g>'

    def ear(self, side=-1, sx=1.0):
        c, D = self.c, self.D
        kind = c['ear']
        if kind == 'long':
            loc = [(-0.47, -0.13), (-0.535, -0.135), (-0.585, -0.095), (-0.595, -0.01), (-0.59, 0.08), (-0.575, 0.165),
                   (-0.53, 0.20), (-0.48, 0.18), (-0.458, 0.10), (-0.452, -0.04)]
            mark = [(-0.515, -0.09), (-0.553, -0.04), (-0.548, 0.035), (-0.525, 0.075)]
        else:
            loc = [(-0.465, -0.10), (-0.535, -0.11), (-0.585, -0.065), (-0.592, 0.01), (-0.575, 0.075), (-0.53, 0.105),
                   (-0.48, 0.095), (-0.46, 0.03), (-0.455, -0.045)]
            mark = [(-0.51, -0.065), (-0.55, -0.02), (-0.542, 0.035), (-0.515, 0.06)]

        def T(x, y):
            xx = -0.455 + (x + 0.455) * sx
            return ((xx if side < 0 else -xx) * D, y * D)
        P = catmull([T(x, y) for x, y in loc], closed=True, n=6)
        lx, ly = self.L
        rw = 0.021 * D
        s = rimlit(P, self.skin, (-lx * 5, -ly * 5)) + ring(P, rw * 0.8, rw * 1.1, seed=self.seed + 4 + side, heavy=(-lx, -ly))
        s += brush([T(x, y) for x, y in mark], 0.02 * D, color=INK, seed=self.seed + 5 + side, taper=(0.3, 0.5), wmin=1.5)
        if kind == 'long':
            s += brush([T(-0.555, 0.11), T(-0.52, 0.16)], 0.016 * D, color=self.skin_dd, seed=self.seed + 7, taper=(0.3, 0.3), wmin=1.0)
        return s

    def tenugui(self):
        """Folded cream tenugui lying on the crown like a towel: soft wavy top edge, a rounded fold at the front end
        (fold-edge line), one indigo stripe, and a short corner flap draping down over the dome at the back end.
        0.32 D wide x 0.08 D thick, narrower than the head so the dome shows on both sides."""
        D = self.D
        R = D / 2
        a_c, span = -95, 17.5
        th = 0.078 * D
        base_r = R - 0.012 * D
        a0, a1 = a_c - span, a_c + span          # a0 = back end, a1 = front (facing side) end
        n = 16
        inner = [pol((0, 0), a0 + (a1 - a0) * j / n, base_r) for j in range(n + 1)]
        nz = Noise(self.seed + 401, 3)
        outer = [pol((0, 0), a1 - (a1 - a0) * j / n, base_r + th * (1 + 0.06 * nz(j * 0.9))) for j in range(n + 1)]
        # rounded fold at the front end
        mid1 = pol((0, 0), a1, base_r + th / 2)
        tang = a1 + 90
        cap = [pol(mid1, tang + 90 - 180 * j / 8, th / 2 * (1.0 if j not in (0, 8) else 1.0)) for j in range(9)]
        cap = [(p[0] + math.cos(math.radians(tang)) * 0.01 * D, p[1] + math.sin(math.radians(tang)) * 0.01 * D) for p in cap]
        P = catmull(inner + cap[::-1][1:-1] + outer, closed=True, n=3)
        # the outer list runs a1 -> a0; close at the back end with a straight free edge
        lx, ly = self.L
        s = rimlit(P, CREAM, (-lx * 3, -ly * 3), col=blend(CREAM, AMBER, 0.40))
        cid = f'tg{uid()}'
        s += f'<clipPath id="{cid}"><path d="{d_of(P)}"/></clipPath><g clip-path="url(#{cid})">'
        st = [pol((0, 0), a0 - 2 + (a1 - a0 + 4) * j / n, base_r + th * 0.70) for j in range(n + 1)]
        s += brush(st, 0.019 * D, color='#2E3A5C', seed=self.seed + 120, taper=(0, 0), wob=0.2)
        s += '</g>'
        s += ring(P, 0.016 * D, 0.021 * D, seed=self.seed + 125, heavy=(-lx, -ly))
        # fold-edge line: the top layer folds round the front end
        fe = [pol(mid1, tang + 70 - 140 * j / 6, th * 0.26) for j in range(7)]
        fe = [pol((0, 0), a1 - 9, base_r + th * 0.30)] + fe
        s += brush(fe, 0.012 * D, color=INK, seed=self.seed + 122, taper=(0.4, 0.3), wob=0.2)
        # corner flap at the back end: one corner drapes down over the dome
        c_out = outer[-1]
        c_in = pol((0, 0), a0 + 3, base_r + th * 0.30)
        tip = pol((0, 0), a0 - 6, base_r - 0.085 * D)
        side = pol((0, 0), a0 - 3.5, base_r + 0.004 * D)
        F = catmull([c_in, c_out, side, tip, pol((0, 0), a0 + 1.5, base_r - 0.05 * D)], closed=True, n=4)
        s += rimlit(F, '#E4DCCB', (-lx * 3, -ly * 3), col=blend(CREAM, AMBER, 0.40)) + ring(F, 0.014 * D, 0.018 * D, seed=self.seed + 127)
        s += brush([lerp(c_in, c_out, 0.45), lerp(side, tip, 0.55)], 0.010 * D, color='#B8AE9C', seed=self.seed + 128, taper=(0.3, 0.5))
        return s

    def buzz(self, cid):
        """Short crop: flat dark tone behind a hairline (front hidden by the band), sideburn in front of the ear."""
        D = self.D
        gx = self.gx
        hl = [(gx + 0.55 * D, -0.40 * D), (gx + 0.05 * D, -0.415 * D), (-0.20 * D, -0.40 * D), (-0.33 * D, -0.32 * D),
              (-0.395 * D, -0.20 * D), (-0.405 * D, -0.06 * D), (-0.40 * D, 0.08 * D), (-0.415 * D, 0.15 * D), (-0.45 * D, 0.10 * D),
              (-0.49 * D, 0.20 * D), (-0.50 * D, 0.34 * D), (-0.8 * D, 0.4 * D), (-0.8 * D, -0.8 * D), (0.8 * D, -0.8 * D)]
        P = catmull(hl, closed=True, n=6)
        s = f'<g clip-path="url(#{cid})"><path d="{d_of(P)}" fill="{BUZZ}"/>'
        edge = catmull(hl[2:7], n=6)
        for j in range(2, len(edge) - 2, 4):
            p = edge[j]
            q = edge[j + 1]
            nx, ny = q[1] - p[1], -(q[0] - p[0])
            l = math.hypot(nx, ny) or 1
            nx, ny = nx / l, ny / l
            s += brush([(p[0] + nx * 0.004 * D, p[1] + ny * 0.004 * D), (p[0] - nx * 0.02 * D, p[1] - ny * 0.02 * D)], 0.011 * D, color=BUZZ,
                       seed=self.seed + 310 + j, taper=(0.0, 0.8), wmin=1.0, smooth=False)
        s += brush([(-0.40 * D, -0.28 * D), (-0.26 * D, -0.42 * D), (-0.04 * D, -0.475 * D)], 0.03 * D, color=blend(BUZZ, '#8A7A70', 0.5),
                   seed=self.seed + 330, taper=(0.3, 0.3))
        s += '</g>'
        return s

    def band(self, cid):
        """Twisted hachimaki: cream rope band with twist marks; compact knot at the front, two short stubby ends, no tails."""
        D = self.D
        R = D / 2
        cx = self.gx * 0.7

        def yu(x):
            return -0.472 * D + 0.05 * D * (1 - ((x - cx) / (0.70 * D)) ** 2)
        th = 0.085 * D
        xs = [-0.62 * D + 1.24 * D * j / 40 for j in range(41)]
        top = [(x, yu(x)) for x in xs]
        bot = [(x, yu(x) + th) for x in xs]
        P = top + bot[::-1]
        s = f'<g clip-path="url(#{cid})"><path d="{d_of(P)}" fill="{CREAM}"/>'
        for j in range(-11, 12):
            x0 = cx + j * 0.075 * D
            q = [(x0, yu(x0)), (x0 + 0.038 * D, yu(x0 + 0.038 * D)), (x0 + 0.075 * D, yu(x0 + 0.075 * D) + th), (x0 + 0.037 * D, yu(x0 + 0.037 * D) + th)]
            s += P_(q, '#E3B48F')
            s += brush([(x0, yu(x0) + 0.006 * D), (x0 + 0.038 * D, yu(x0) + th - 0.006 * D)], 0.012 * D, color=INK, seed=self.seed + 200 + j, taper=(0.2, 0.2), smooth=False)
        s += brush([(x, yu(x) + 0.004 * D) for x in xs], 0.016 * D, color=INK, seed=self.seed + 230, taper=(0, 0), wob=0.3)
        s += brush([(x, yu(x) + th - 0.004 * D) for x in xs], 0.016 * D, color=INK, seed=self.seed + 231, taper=(0, 0), wob=0.3)
        s += '</g>'
        for sx in (-1, 1):
            yc = yu(sx * 0.46 * D) + th / 2
            xx = sx * math.sqrt(max(0.0, R * R - yc * yc))
            E = ellipse(xx + sx * 0.006 * D, yc, 0.024 * D, th * 0.56, n=24)
            s += filled(E, CREAM, 0.012 * D, 0.016 * D, seed=self.seed + 240 + sx)
        kx = cx + 0.06 * D
        ky = yu(kx) + 0.01 * D
        for j, (a, ln, bend) in enumerate(((-128, 0.13, -10), (-56, 0.12, 10))):
            base = (kx, ky - 0.01 * D)
            mid = pol(base, a, ln * D * 0.55)
            tip = pol(mid, a + bend, ln * D * 0.45)
            nrm = a + 90
            cut = 0.014 * D * (1 if j == 0 else -1)
            q = [pol(base, nrm, 0.026 * D), pol(mid, nrm + bend * 0.5, 0.032 * D), pol(pol(tip, a + bend, cut), nrm + bend, 0.040 * D),
                 pol(pol(tip, a + bend, -cut), nrm + bend, -0.034 * D), pol(mid, nrm + bend * 0.5, -0.028 * D), pol(base, nrm, -0.024 * D)]
            s += filled(q, CREAM, 0.016 * D, 0.021 * D, seed=self.seed + 250 + j)
        K = ellipse(kx, ky, 0.058 * D, 0.05 * D, rot=-8, n=30)
        s += filled(K, CREAM, 0.016 * D, 0.021 * D, seed=self.seed + 260)
        s += brush([(kx - 0.03 * D, ky - 0.015 * D), (kx + 0.025 * D, ky + 0.02 * D)], 0.012 * D, color=INK, seed=self.seed + 261, taper=(0.2, 0.2))
        return s

    # ---------------------------------------------------------- lower face
    def stubble(self, cid):
        D = self.D
        gx = self.gx
        band = catmull([(-D, 0.20 * D), (-0.40 * D, 0.24 * D), (gx - 0.20 * D, 0.285 * D), (gx - 0.06 * D, 0.262 * D),
                        (gx + 0.12 * D, 0.262 * D), (gx + 0.26 * D, 0.29 * D), (D, 0.22 * D), (D, D), (-D, D)], closed=True, n=6)
        return f'<g clip-path="url(#{cid})"><path d="{d_of(band)}" fill="#C9966E"/></g>'

    def chin_tuft(self):
        D = self.D
        b = pol((0, 0), 90 - 30 * (self.gx / (0.17 * D)), D / 2 - 0.03 * D)
        P = catmull([(b[0] - 0.05 * D, b[1] - 0.01 * D), (b[0] + 0.05 * D, b[1] - 0.015 * D), (b[0] + 0.025 * D, b[1] + 0.07 * D),
                     (b[0] - 0.005 * D, b[1] + 0.115 * D), (b[0] - 0.03 * D, b[1] + 0.06 * D)], closed=True, n=5)
        return filled(P, HAIR_K, 0.012 * D, 0.016 * D, seed=self.seed + 90)

    def chin_stubble(self, cid):
        """Tama: short white chin stubble -- scattered flecks round the chin and jaw (no tone patch), drawn under the mouth line."""
        c, D = self.c, self.D
        x = self.gx + c.get('mouth_dx', 0.035) * D + 0.010 * D
        my = c['mouth_y'] * D
        zone = catmull([(x - 0.22 * D, my - 0.02 * D), (x - 0.08 * D, my - 0.045 * D), (x + 0.10 * D, my - 0.045 * D), (x + 0.23 * D, my - 0.015 * D),
                        (x + 0.26 * D, my + 0.10 * D), (x, my + 0.24 * D), (x - 0.26 * D, my + 0.10 * D)], closed=True, n=6)
        rng = random.Random(self.seed + 333)
        s = f'<g clip-path="url(#{cid})">'
        n = tries = 0
        while n < 40 and tries < 600:
            tries += 1
            px = x + rng.uniform(-0.26, 0.27) * D
            py = my + rng.uniform(-0.05, 0.22) * D
            sp = poly_vspan(zone, px)
            if not sp or not (sp[0] < py < sp[1]):
                continue
            if abs(px - x) < 0.14 * D and abs(py - my) < 0.035 * D:
                continue        # keep the mouth line clean
            ang = rng.uniform(60, 120)
            q = pol((px, py), ang, 0.015 * D)
            s += brush([(px, py), q], 0.011 * D, color='#F1ECE2', seed=self.seed + 340 + n, taper=(0.3, 0.3), wmin=1.0, smooth=False, wob=0.05, op=0.9)
            n += 1
        return s + '</g>'

    def goatee(self):
        """Tama: a small soft white goat beard hanging from the chin line (mostly below the jaw outline, so it reads as
        hair, never as a tooth), a wavy tufted outline, grey strands and a slight forward curl."""
        c, D = self.c, self.D
        x = self.gx + c.get('mouth_dx', 0.035) * D + 0.008 * D
        R = D / 2
        yc = math.sqrt(max(0.0, (R - 0.01 * D) ** 2 - x * x))      # the jaw outline under the mouth
        y0 = yc - 0.040 * D
        pts = [(x - 0.060 * D, y0 + 0.010 * D), (x - 0.020 * D, y0 - 0.006 * D), (x + 0.030 * D, y0 - 0.010 * D), (x + 0.064 * D, y0 - 0.002 * D),
               (x + 0.066 * D, y0 + 0.040 * D), (x + 0.052 * D, y0 + 0.074 * D), (x + 0.060 * D, y0 + 0.104 * D), (x + 0.030 * D, y0 + 0.098 * D),
               (x + 0.020 * D, y0 + 0.124 * D), (x - 0.004 * D, y0 + 0.102 * D), (x - 0.026 * D, y0 + 0.110 * D), (x - 0.034 * D, y0 + 0.082 * D),
               (x - 0.056 * D, y0 + 0.060 * D)]
        P = catmull(pts, closed=True, n=6)
        lx, ly = self.L
        col = '#ECE7DE'
        s = rimlit(P, col, (-lx * 3, -ly * 3), col=blend(col, '#A89E8E', 0.55))
        s += ring(P, 0.013 * D, 0.017 * D, seed=self.seed + 360, heavy=(0.2, 0.9))
        for j, (p0, p1, p2) in enumerate((((x - 0.032 * D, y0 + 0.020 * D), (x - 0.030 * D, y0 + 0.050 * D), (x - 0.024 * D, y0 + 0.074 * D)),
                                          ((x + 0.006 * D, y0 + 0.018 * D), (x + 0.010 * D, y0 + 0.056 * D), (x + 0.016 * D, y0 + 0.090 * D)),
                                          ((x + 0.040 * D, y0 + 0.020 * D), (x + 0.042 * D, y0 + 0.048 * D), (x + 0.044 * D, y0 + 0.070 * D)))):
            s += brush([p0, p1, p2], 0.009 * D, color='#A99F8F', seed=self.seed + 365 + j, taper=(0.3, 0.4), wmin=1.0)
        return s

    def nose(self):
        c, D = self.c, self.D
        gx = self.gx
        ey = self.E['cy'] * D
        kind = c['nose']
        lx, ly = self.L
        if kind == 'round':     # bridge line in the gap from eye mid-height, then a wide round nose 0.20 D
            br = [(gx - 0.012 * D, ey - 0.035 * D), (gx - 0.004 * D, ey + 0.045 * D), (gx + 0.006 * D, ey + 0.105 * D)]
            s = brush(br, 0.022 * D, seed=self.seed + 19, taper=(0.6, 0.15), wmin=1.2)
            nx, ny = gx + 0.035 * D, c.get('nose_y', 0.155) * D
            P = catmull([(nx - 0.10 * D, ny + 0.02 * D), (nx - 0.075 * D, ny - 0.040 * D), (nx - 0.01 * D, ny - 0.068 * D),
                         (nx + 0.07 * D, ny - 0.055 * D), (nx + 0.108 * D, ny + 0.0 * D), (nx + 0.095 * D, ny + 0.050 * D),
                         (nx + 0.02 * D, ny + 0.068 * D), (nx - 0.07 * D, ny + 0.060 * D)], closed=True, n=6)
            s += rimlit(P, blend(self.skin, '#F2CFA8', 0.12), (-lx * 4, -ly * 4), col=blend(self.skin, AMBER, 0.6))
            s += ring(P, 0.02 * D, 0.026 * D, seed=self.seed + 20, heavy=(0.2, 0.9))
            s += brush([(nx - 0.055 * D, ny + 0.032 * D), (nx - 0.035 * D, ny + 0.046 * D), (nx - 0.01 * D, ny + 0.042 * D)], 0.02 * D, seed=self.seed + 21, taper=(0.3, 0.3))
            s += brush([(nx + 0.045 * D, ny + 0.042 * D), (nx + 0.065 * D, ny + 0.037 * D)], 0.016 * D, seed=self.seed + 22, taper=(0.3, 0.3))
            return s
        if kind == 'tri':       # sharp triangle: top in the gap at eye mid-height, tip forward and down
            top = (gx - 0.005 * D, ey - 0.01 * D)
            tip = (gx + 0.13 * D, 0.185 * D)
            back = (gx - 0.06 * D, 0.200 * D)
            P = catmull([top, (gx + 0.065 * D, 0.09 * D), tip, (gx + 0.05 * D, 0.212 * D), back, (gx - 0.04 * D, 0.10 * D)], closed=True, n=5)
            s = P_(P, shade(self.skin, 0.10))
            s += brush([top, (gx + 0.065 * D, 0.09 * D), tip], 0.026 * D, seed=self.seed + 20, taper=(0.55, 0.05), wmin=1.5, smooth=False)
            s += brush([tip, (gx + 0.05 * D, 0.214 * D), back], 0.028 * D, seed=self.seed + 23, taper=(0.05, 0.35), wmin=1.5)
            s += brush([(gx + 0.01 * D, 0.17 * D), (gx + 0.04 * D, 0.188 * D)], 0.018 * D, seed=self.seed + 21, taper=(0.3, 0.3))
            return s
        return ''

    def folds(self):
        """Tama: forehead wrinkles, nasolabial folds."""
        D = self.D
        gx = self.gx
        c = self.skin_dd
        s = ''
        lift = self.e['brow_dy'][0] if isinstance(self.e['brow_dy'], (tuple, list)) else self.e['brow_dy']
        for j, (w, y) in enumerate(((0.24, -0.395), (0.20, -0.362), (0.13, -0.331))):
            yy = y * D + min(0.0, lift) * D * 0.35
            x0 = gx - 0.03 * D
            pts = [(x0 - w / 2 * D, yy + 0.010 * D), (x0, yy - 0.007 * D), (x0 + w / 2 * D, yy + 0.010 * D)]
            s += brush(pts, 0.017 * D, color=c, seed=self.seed + 141 + j, taper=(0.3, 0.3), wmin=1.0)
        for j, (sx, sgn) in enumerate(((-0.13, -1), (0.21, 1))):
            x0 = gx + sx * D
            pts = [(x0, 0.215 * D), (x0 + sgn * 0.022 * D, 0.28 * D), (x0 + sgn * 0.012 * D, 0.345 * D)]
            s += brush(pts, 0.019 * D, color=c, seed=self.seed + 148 + j, taper=(0.3, 0.4), wmin=1.2)
        return s

    # ---------------------------------------------------------- mouth (modest: the eyes do the acting)
    def mouth(self):
        c, e, D = self.c, self.e, self.D
        k = e['mouth']
        x = self.gx + c.get('mouth_dx', 0.035) * D + e['m_dx'] * D
        y = c['mouth_y'] * D + e['m_dy'] * D
        sd = self.seed + 13
        T = 0.045 * D

        def R(P):
            return xform(P, rot=e['m_rot'], ox=x, oy=y)

        def openm(w, h, topcurve=0.0, botcurve=1.0, teeth_top=0.0, tongue=True):
            top = []
            n = 24
            for j in range(n + 1):
                t = j / n
                top.append((x - w / 2 + w * t, y - h * 0.35 - topcurve * h * math.sin(math.pi * t)))
            bot = []
            for j in range(n, -1, -1):
                t = j / n
                bot.append((x - w / 2 + w * t, y - h * 0.35 + h * botcurve * math.sin(math.pi * t) ** 0.8))
            P = R(top + bot)
            cid = f'mo{uid()}'
            s = P_(P, MOUTH_IN) + f'<clipPath id="{cid}"><path d="{d_of(P)}"/></clipPath><g clip-path="url(#{cid})">'
            if tongue:
                s += P_(R(ellipse(x + 0.02 * D, y + h * 0.62, w * 0.30, h * 0.36, n=30)), TONGUE)
            if teeth_top:
                s += P_(R([(x - w, y - h), (x + w, y - h), (x + w, y - h * 0.35 + teeth_top * h), (x - w, y - h * 0.35 + teeth_top * h)]), TEETH)
            s += '</g>' + ring(P, 0.020 * D, 0.026 * D, seed=sd, heavy=(0.2, 0.9))
            return s
        if k == 'rest':          # contented closed smile
            w = 0.22 * D
            s = brush(R([(x - w / 2, y - 0.012 * D), (x - w * 0.2, y + 0.014 * D), (x + w * 0.2, y + 0.014 * D), (x + w / 2, y - 0.014 * D)]), T, seed=sd, taper=(0.25, 0.25))
            s += brush(R([(x + w / 2 + 0.006 * D, y - 0.045 * D), (x + w / 2 + 0.020 * D, y - 0.006 * D)]), 0.016 * D, color=self.skin_dd, seed=sd + 3, taper=(0.3, 0.3))
            s += brush(R([(x - w / 2 - 0.006 * D, y - 0.045 * D), (x - w / 2 - 0.020 * D, y - 0.006 * D)]), 0.016 * D, color=self.skin_dd, seed=sd + 4, taper=(0.3, 0.3))
            return s
        if k == 'o':             # small round 'o', no teeth
            w = e['m_w'] or 0.10 * D
            P = R(ellipse(x, y, w / 2, w * 0.58, n=36))
            return P_(P, MOUTH_IN) + ring(P, 0.019 * D, 0.024 * D, seed=sd, heavy=(0.2, 0.9))
        if k == 'smirk':
            w = e['m_w'] or 0.22 * D
            s = brush(R([(x - w / 2, y + 0.01 * D), (x - 0.02 * D, y + 0.02 * D), (x + w / 2 - 0.03 * D, y + 0.0 * D), (x + w / 2 + 0.005 * D, y - 0.038 * D)]), T, seed=sd, taper=(0.3, 0.2))
            s += brush(R([(x + w / 2 + 0.028 * D, y - 0.075 * D), (x + w / 2 + 0.040 * D, y - 0.030 * D)]), 0.018 * D, color=self.skin_dd, seed=sd + 3, taper=(0.3, 0.3))
            return s
        if k == 'tight':         # pressed, corners down (anger) -- no teeth
            w = e['m_w'] or 0.20 * D
            return brush(R([(x - w / 2, y + 0.022 * D), (x - w * 0.2, y - 0.002 * D), (x + w * 0.2, y - 0.002 * D), (x + w / 2, y + 0.024 * D)]), T, seed=sd, taper=(0.2, 0.2))
        if k == 'wavy':          # panic: short wavy line
            w = e['m_w'] or 0.22 * D
            pts = [(x - w / 2 + w * j / 12, y + 0.014 * D * math.sin(j / 12 * math.pi * 4)) for j in range(13)]
            return brush(R(pts), T * 0.9, seed=sd, taper=(0.2, 0.2), smooth=True)
        if k == 'flat':
            w = e['m_w'] or 0.20 * D
            xx = x - 0.03 * D
            return brush(R([(xx - w / 2, y), (xx + w * 0.1, y - 0.004 * D), (xx + w / 2, y + 0.01 * D), (xx + w / 2 + 0.018 * D, y + 0.030 * D)]), T, seed=sd, taper=(0.2, 0.15))
        if k == 'sip':
            return brush(R([(x - 0.05 * D, y - 0.008 * D), (x + 0.02 * D, y + 0.008 * D)]), T, seed=sd, taper=(0.3, 0.3))
        if k == 'grin':          # Hiko only (light skin): modest open grin, <= 0.28 D wide
            return openm(e['m_w'] or 0.27 * D, 0.14 * D, topcurve=-0.12, botcurve=1.0, teeth_top=0.30, tongue=True)
        if k == 'oh':            # Hiko: small open 'oh'
            w = e['m_w'] or 0.15 * D
            return openm(w, 0.17 * D, topcurve=0.25, botcurve=0.95, teeth_top=0.0, tongue=True)
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
        if self.front_ear:
            s.append(self.ear(side=+1, sx=0.7))
        s.append(skull)
        if c['stubble']:
            s.append(self.stubble(cid))
        if c['hair'] == 'tenugui':
            s.append(self.scalp(cid))
        if c['hair'] == 'buzz':
            s.append(self.buzz(cid))
        s.append(ring(P, 0.028 * D, 0.038 * D, seed=self.seed, heavy=(-lx, -ly)))
        s.append(self.ear(side=-1))
        if c['age']:
            s.append(f'<g clip-path="url(#{cid})">' + self.folds() + '</g>')
        if c.get('goatee'):
            s.append(self.chin_stubble(cid))
        eyes, infos = [], []
        for i in (1, 0):        # far eye first, near eye on top
            es, info = self.eye(i)
            eyes.append(es)
            infos.append(info)
        infos = infos[::-1]
        s.append(f'<g clip-path="url(#{cid})">' + ''.join(eyes) + '</g>')
        if c['hair'] == 'buzz':
            s.append(self.band(cid))
        s.append(self.brow(1, infos[1]))
        s.append(self.brow(0, infos[0]))
        s.append(self.nose())
        s.append(self.mouth())
        if c['stubble']:
            s.append(self.chin_tuft())
        if c.get('goatee'):
            s.append(self.goatee())
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
    face = BigFace(D, 'tama', facing=facing, rot=P.get('head_rot', 0.0) * facing, turn=P.get('turn', 0.12), far_k=P.get('far_k', 0.62),
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


def adams_apple(nt, nb, facing, D, skin, hc):
    """Small bump on the front edge of the neck stub, just below the jaw (adult cue)."""
    a = ang_of(nt, nb)
    ax = (math.cos(math.radians(a)), math.sin(math.radians(a)))
    n = None
    for s in (90, -90):
        v = (math.cos(math.radians(a + s)), math.sin(math.radians(a + s)))
        if v[0] * facing > 0:
            n = v
    t = max(0.0, min(1.0, ((hc[1] + 0.545 * D) - nt[1]) / ((nb[1] - nt[1]) or 1)))
    p = lerp(nt, nb, t)
    e = (p[0] + n[0] * 0.083 * D, p[1] + n[1] * 0.083 * D)
    curve = []
    for j in range(11):
        u = -1 + 2 * j / 10
        bump = 0.024 * D * (1 - u * u) ** 0.8
        curve.append((e[0] + ax[0] * u * 0.040 * D + n[0] * bump, e[1] + ax[1] * u * 0.040 * D + n[1] * bump))
    base = [(e[0] - n[0] * 0.012 * D + ax[0] * 0.04 * D, e[1] - n[1] * 0.012 * D + ax[1] * 0.04 * D),
            (e[0] - n[0] * 0.012 * D - ax[0] * 0.04 * D, e[1] - n[1] * 0.012 * D - ax[1] * 0.04 * D)]
    s = P_(curve + base, skin)
    s += brush(curve, 0.020 * D, seed=777, taper=(0.15, 0.15), wmin=2.0)
    s += brush([lerp(curve[3], e, 0.6), lerp(curve[7], e, 0.6)], 0.012 * D, color=shade(skin, 0.25), seed=778, taper=(0.3, 0.3), wmin=1.0)
    return s

def hiko_fig(hc, D, facing, expr, P, light, seed=0, front_ear=False):
    F = Frame(hc, D, facing)
    face = BigFace(D, 'hiko', facing=facing, rot=P.get('head_rot', 0.0) * facing, turn=P.get('turn', 0.12), far_k=P.get('far_k', 0.62),
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
    o['neck'] += adams_apple(J['nt'], J['nb'], facing, D, SKIN_H, hc)
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
# EXPRESSIONS (Tama) -- the huge eyes carry every beat; mouths stay modest (dark-skin rule: no teeth, no big mouth)
# =====================================================================
TAMA_EXPR = [
    ('neutral', dict(mode=('closed', 'closed'), closed=('u', 'u'), mouth='rest'), 0),
    ('surprised', dict(mode=('pop', 'pop'), iris=(0.31, 0.31), gaze=(0.0, 0.0), brow_dy=(-0.085, -0.085), brow_bend=(0.012, 0.012),
                       mouth='o', marks=(('pop_lines',),)), -4),
    ('angry', dict(mode=('open', 'open'), cov=(0.30, 0.30), slant=(22, 22), gaze=(-0.25, 0.15), brow_dy=(0.10, 0.10),
                   brow_ang=(24, 24), mouth='tight', hl=(0.55, 0.55), marks=(('vein', -0.32, -0.36, 0.15),)), 5),
    ('smug', dict(mode=('open', 'open'), cov=(0.27, 0.27), low=(0.12, 0.12), lowarch=(0.10, 0.10), gaze=(0.95, 0.05),
                  brow_dy=(-0.03, 0.04), brow_ang=(-8, 8), hl=(0.75, 0.75), mouth='smirk'), -6),
    ('panic', dict(mode=('open', 'open'), fp=(0.47, 0.37), cov=(0.08, 0.08), slant=(-30, -30), iris=(0.22, 0.22), gaze=(-0.4, 0.9), hl=(0.6, 0.6),
                   wobble=0.016, tear=(True, True), brow_dy=(-0.02, -0.02), brow_ang=(-26, -26), mouth='wavy', turn=0.04, far_k=0.86,
                   marks=(('sweat', 0.53, -0.36, 0.07, 18), ('sweat', -0.62, -0.18, 0.06, -20), ('shake',))), 0),
    ('side-eye', dict(mode=('open', 'open'), cov=(0.38, 0.38), sag=(0.04, 0.04), low=(0.06, 0.06), gaze=(-1.0, 0.08), hl=(0.0, 0.0),
                      brow_dy=(0.035, 0.0), brow_ang=(6, -8), mouth='flat', marks=(('puff', -0.30, 0.42, 0.055),)), 3),
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


FACES_D = 240.0


def faces_svg():
    W, H = 1080, 1080
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="{MOON}"/>']
    D = FACES_D
    for idx, (name, ex, rot) in enumerate(TAMA_EXPR):
        col, row = idx % 3, idx // 3
        cx, cy = 180 + col * 360, 226 + row * 540
        o.append(f'<circle cx="{cx}" cy="{cy + 20}" r="200" fill="#DDD5C2"/>')
        light = (cx - 600, cy - 400)
        o.append(bust((cx, cy), D, -1, light))
        face = BigFace(D, 'tama', facing=-1, rot=-rot, turn=ex.get('turn', 0.09), far_k=ex.get('far_k', 0.66), light=light_vec(light, (cx, cy)), expr=ex,
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
                head_rot=-3, turn=0.12, cup_dy=0.0, steam=True, hang_f=0.22, hang_n=0.22)


def hiko_scene_pose(hand_local=(0.72, 1.54)):
    hx, hy = hand_local
    return dict(nt=(-0.10, 0.42), nb=(-0.30, 0.60), hip=(-0.92, 1.30), bow=0.05, sh=0.26, yoke=0.07,
                ua=0.74, fa=0.72, th=0.84, sn=0.80, hipw=0.05,
                wr_f=(hx + 0.05, hy - 0.10), el_f=1, hand_f=150, wr_n=(hx - 0.12, hy + 0.04), el_n=1, hand_n=160,
                an_f=(-0.28, 2.56), kn_f=-1, toe_f=0, an_n=(-1.60, 2.52), kn_n=-1, toe_n=-20,
                head_rot=-9, turn=0.12)


def ring_burst(x, y, s=1.0, seed=0, col=INK, base=-150):
    """Bell 'ting': a small ring + three ticks (no star: the star belongs to Tama's eyes)."""
    o = [ring(ellipse(x, y, 9 * s, 9 * s, n=24), 4 * s, 5 * s, color=BRASS, seed=seed)]
    for i, a in enumerate((-45, -10, 25)):
        p0 = pol((x, y), a + base, 20 * s)
        p1 = pol((x, y), a + base, 40 * s)
        o.append(brush([p0, p1], 6 * s, color=col, seed=seed + 3 + i, taper=(0.2, 0.3)))
    return ''.join(o)


def scene_svg():
    W, H = 1080, 1920
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    scene_bg(o)
    FLOOR = 1690
    Dt, Dh = 256.0, 262.0
    tp = tama_scene_pose()
    hct = (262.0, FLOOR - (tp['an_n'][1] + 0.04) * Dt)
    hch = (574.0, FLOOR - (2.56 + 0.05) * Dh)
    foot_w = (hct[0] + tp['an_f'][0] * Dt, hct[1] + tp['an_f'][1] * Dt)
    grab = (foot_w[0] + 0.10 * Dt, foot_w[1] - 0.30 * Dt)
    hp = hiko_scene_pose(((hch[0] - grab[0]) / Dh, (grab[1] - hch[1]) / Dh))
    ball = (404.0, 600.0)
    br = 0.32 * Dt / 2
    # Tama: PEEK -- the near eye opens to a gold sliver aimed at Hiko (star glint), the far eye stays a content arc
    hiko_eye = (hch[0] - 0.10 * Dh, hch[1] - 0.04 * Dh)
    tex = dict(mode=('open', 'closed'), closed=('u', 'u'), cov=(0.15, None), slant=(6, 0), low=(0.03, 0.0), lowarch=(0.05, 0.0),
               look=hiko_eye, brow_dy=(-0.03, 0.03), brow_ang=(-6, 4), mouth='smirk')
    # Hiko: awe -- lids at 0 %, iris shrunk to 55 %, both irises on the flying ball
    hex_ = dict(mode=('pop', 'pop'), cov=(0.0, 0.0), iris=(0.40, 0.40), look=ball, brow_dy=(-0.06, -0.06), brow_ang=(-12, -12),
                brow_bend=(0.01, 0.01), mouth='oh', m_w=0.13 * Dh, m_dy=-0.025)
    mt = tama_fig(hct, Dt, 1, tex, tp, LANTERN, seed=0)
    mh = hiko_fig(hch, Dh, -1, hex_, hp, LANTERN, seed=0)
    o.append(f'<ellipse cx="{f1(mt["J"]["an_n"][0] + 10)}" cy="{FLOOR + 2}" rx="120" ry="12" fill="{INK}" opacity="0.30"/>')
    o.append(f'<ellipse cx="{f1((mh["J"]["an_n"][0] + mh["J"]["an_f"][0]) / 2)}" cy="{FLOOR + 2}" rx="280" ry="14" fill="{INK}" opacity="0.26"/>')
    o.append(mh['svg'])
    o.append(mt['svg'])
    wf, wn, hf, hn = mh['hand']
    for i, w in enumerate((wf, wn)):
        o.append(swoosh(w, 0.30 * Dh, 120, 220, n=2, gap=14, w=5, col=INK, seed=540 + i * 3, op=0.6))
    o.append(ghost_ball(grab[0], grab[1], br, op=0.40, col=INK))
    pf = [ellipse(grab[0] - 0.02 * Dt, grab[1] - 0.06 * Dt, 15, 12, n=24), ellipse(grab[0] + 0.07 * Dt, grab[1] - 0.10 * Dt, 12, 10, n=24),
          ellipse(grab[0] + 0.12 * Dt, grab[1] - 0.03 * Dt, 10, 8, n=24)]
    o.append(union(pf, CREAM, 5, 7, seed=545))
    o.append(dotted(qbez((grab[0] + 4, grab[1] - br - 22), ((grab[0] + ball[0]) / 2 + 30, (grab[1] + ball[1]) / 2), (ball[0] + 4, ball[1] + br + 26), 20),
                    3.5, 7.0, gap=32))
    o.append(temari(ball[0], ball[1], br, seed=500, bell_side=1))
    o.append(ring_burst(ball[0] - br - 34, ball[1] - br + 4, 0.95, seed=560, base=-150))
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


# Tama in the lineup: the PEEK (one gold eye with the star glint, one content arc) shows both halves of his eye identity
TAMA_LINEUP_EXPR = dict(mode=('open', 'closed'), closed=('u', 'u'), cov=(0.14, None), slant=(5, 0), low=(0.0, 0.0), lowarch=(0.04, 0.0),
                        gaze=(0.9, 0.05), brow_dy=(-0.03, 0.02), brow_ang=(-5, 3), mouth='smirk')
HIKO_LINEUP_EXPR = dict(mode=('open', 'open'), gaze=(0.85, 0.05), brow_dy=(0.0, 0.0), brow_ang=(0, 0), mouth='grin')


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


LINEUP_INFO = {}


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
    E = CHAR[who]['eye']
    LINEUP_INFO[who] = dict(k=k, D=Deff, H=target)
    if not sil:
        print(f'{who}: k={k:.4f} D_eff={Deff:.1f}px top={y0 * k + ty:.1f} sole={(y1 + 1) * k + ty:.1f} H={target} head/H={Deff / target:.3f} '
              f'H/D={target / Deff:.2f} eye_h(rest footprint)/H={E["h"] * Deff / target:.3f} x-range={x0 * k + tx:.0f}..{x1 * k + tx:.0f}')
    return '\n'.join(o)


def write(name, s):
    with open(os.path.join(HERE, name), 'w') as fh:
        fh.write(s)


def rule_report():
    """Numeric check of the anime-eye rules on a 3/4 head (turn 0.12, far_k 0.62) and the front view."""
    for who in ('tama', 'hiko'):
        E = CHAR[who]['eye']
        for pop in (False, True):
            f = BigFace(1000.0, who, turn=0.12, far_k=0.62)
            lay = f.eye_layout(pop)
            w = (E['pop_w'] if pop else E['w'])
            h = (E['pop_h'] if pop else E['h'])
            g = (E['gap_pop'] if pop else E['gap'])
            # outer-corner distance to the rim (3/4)
            worst = 1.0
            for (ex, ey, k, inner) in lay:
                P = fp_poly(E['shape'], w * 1000 * k, h * 1000, E.get('slant', 0.0))
                Rin = (0.47 if pop else 0.46) * 1000
                for x, y in P:
                    X, Y = ex + inner * x, ey + y
                    r = math.hypot(X, Y)
                    if r > Rin:      # clamped to the inner rim circle in eye()
                        r = Rin
                    worst = min(worst, 0.5 - r / 1000)
            fr = BigFace(1000.0, who, turn=0.0, far_k=1.0)
            span_front = 2 * w + g
            ih = (E['iris_pop'] if pop else E['iris_h'])
            print(f"{who} {'POP ' if pop else 'rest'}: eye_h={h:.2f}D w={w:.2f}D gap={g:.2f}D centre={0.5 + E['cy']:.3f}D below top "
                  f"top={0.5 + E['cy'] - h / 2:.3f}D | front span={span_front:.2f}D | 3/4: near x={lay[0][0] / 1000:+.3f} far x={lay[1][0] / 1000:+.3f} "
                  f"gap centre={f.gx / 1000:+.3f}D far_k={lay[1][2]:.2f} min rim clearance={worst:+.3f}D | iris={ih:.3f}D ({ih / h:.0%}) "
                  f"pupil={E['pupil_k'] * ih:.3f}D ({E['pupil_k']:.0%} of iris) lash={E['lash']:.3f}D low={E['low']:.3f}D")
        if E['rest'] == 'closed':
            print(f"   tama closed: arc {E['closed_w']:.2f}D wide x {E['lash'] * 1.05:.3f}D thick, sag {E['sag']:.2f}D, at 58% of footprint; socket {E['socket']}")
        else:
            print(f"   {who} rest lid {E['rest']:.0%} -> visible opening {E['h'] * (1 - E['rest']):.3f}D")


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
