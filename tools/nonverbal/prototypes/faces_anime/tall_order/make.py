#!/usr/bin/env python3
"""Tall Order -- ANIME BIG-EYE round heads on stick bodies (Mr. Level + Hasty).

ONE face rig (class Head, driven by a per-character parameter dict, with ONE
anime-eye construction shared by every eye) and ONE stick-body rig (class Body).
Char = Body + Head.  scene.svg, faces.svg, hero.svg and partner.svg are all
built from these two rigs.

Units: fractions of D = skull diameter (no ears / hair / nose).
Line language: flat fills + ink outlines (per-layer dilate outline), the
upper lash line is the darkest, thickest line on every face.

Anime-eye construction, back to front:
  (1) sclera #FBF6EA  (2) lid shadow band #DCD3C3 (iris-shadow over the iris)
  (3) iris: base + darker top third + lighter bottom crescent + limbal ring
  (4) pupil disc  (5) catchlights #FFFFFF  (6) upper lash line
  (7) lower lash / lid line, creases, bags, crow's-feet  (8) brow
"""
import math, os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
EMERALD = '#1F5C4A'
EMERALD_D = '#12302B'
FLOOR_D = '#163F34'
SAGE = '#9FB8A6'
BRASS = '#A88A48'
GOLD = '#C9A24B'
IVORY = '#F3EDE0'
INK = '#1C1714'
SALMON = '#E59A7E'
MOUTH_IN = '#3A1E1A'
TONGUE = '#B9655A'
LINE_BG = '#EDEAE4'
SHEET_BG = '#E4DED2'
SHEET_CELL = '#EFEAE1'
SHEET_HALO = '#F8F5EF'

SCLERA = '#FBF6EA'        # warm off-white, never #FFFFFF
LIDBAND = '#DCD3C3'       # lid shadow band over the white
HILITE = '#FFFFFF'        # catchlights: the only pure white on a face

# Mr. Level
SKIN_L, SHAD_L = '#7A4E34', '#66402B'
HAIR_L, HAIR_L_TOP, HAIR_L_D = '#4B4845', '#8E8A85', '#3B3936'
JACKET, JACKET_D = '#F1EADB', '#D8CDB8'
LAPEL = '#1E1C1B'
TROUSER, TROUSER_D = '#1E1C1B', '#151413'
SATIN = '#4C4744'
SHIRT_W = '#FBF8F1'
GLOVE = '#FAF7F1'
PATENT = '#121212'
DOME, DOME_D, DOME_L = '#C8CCD1', '#9AA0A7', '#E7EAED'
LV_IRIS = dict(base='#BCCD25', shadow='#879514', light='#E2ED86', ring='#5B650C', pupil='#2A3005')

# Hasty
SKIN_H, SHAD_H = '#E6B590', '#CD9C78'
HAIR_H, HAIR_H_D, HAIR_H_L = '#7A4A2C', '#5A341F', '#9C6744'   # chestnut side part
GREY_H = '#B4AEA6'                                               # grey at the temples
BROW_H = '#3E2618'
ENJI, ENJI_D = '#93343A', '#76282E'
SHIRT, SHIRT_D = '#A3A9CC', '#8B91B5'
TIE = '#22304A'
RUDDY = '#D47E6A'
HS_IRIS = dict(base='#2463C8', shadow='#173F8E', light='#7EA7EC', ring='#0F2C66', pupil='#06122C')

# clerk cameo (generic eye)
SKIN_C, SHAD_C = '#C38A63', '#AA7451'
HAIR_C = '#8F8984'
CARDI = '#3E4E5E'
CL_IRIS = dict(base='#7A5236', shadow='#7A5236', light='#7A5236', ring='#5A3B26', pupil='#2A1A10')

_uid = [0]


def uid(p='id'):
    _uid[0] += 1
    return f'{p}{_uid[0]}'


def shade(hx, k):
    hx = hx.lstrip('#')
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    m = 1 - k
    return '#%02X%02X%02X' % (round(r * m), round(g * m), round(b * m))


def mix(a, b, t):
    a = a.lstrip('#'); b = b.lstrip('#')
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def f(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def dirv(deg):
    """unit direction: 0 = down, 90 = screen right, 180 = up, -90 = left."""
    a = math.radians(deg)
    return math.sin(a), math.cos(a)


def add(p, v, k=1.0):
    return (p[0] + v[0] * k, p[1] + v[1] * k)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def norm(v):
    L = math.hypot(*v) or 1e-9
    return (v[0] / L, v[1] / L)


def ang_of(a, b):
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))


def pstr(pts):
    return ' '.join(f'{f(x)},{f(y)}' for x, y in pts)


def clamp(v, a, b):
    return max(a, min(b, v))


def interp(prof, t):
    if t <= prof[0][0]:
        return prof[0][1]
    for (t0, w0), (t1, w1) in zip(prof, prof[1:]):
        if t <= t1:
            return w0 + (w1 - w0) * (t - t0) / (t1 - t0)
    return prof[-1][1]


def capsule_pts(p1, r1, p2, r2, n=10):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = max(math.hypot(dx, dy), 1e-4)
    ux, uy = dx / L, dy / L
    s = max(-0.98, min(0.98, (r1 - r2) / L))
    c = math.sqrt(1 - s * s)
    phi = math.atan2(c, s)
    au = math.atan2(uy, ux)
    pts = []
    for i in range(n + 1):
        t = au + phi - 2 * phi * i / n
        pts.append((p2[0] + r2 * math.cos(t), p2[1] + r2 * math.sin(t)))
    m = n + 6
    for i in range(m + 1):
        t = au - phi - (2 * math.pi - 2 * phi) * i / m
        pts.append((p1[0] + r1 * math.cos(t), p1[1] + r1 * math.sin(t)))
    return pts


def capsule(p1, r1, p2, r2, fill, extra=''):
    return f'<polygon points="{pstr(capsule_pts(p1, r1, p2, r2))}" fill="{fill}"{extra}/>'


def ik(root, target, a, b, bend):
    dx, dy = target[0] - root[0], target[1] - root[1]
    d0 = max(math.hypot(dx, dy), 1e-4)
    ux, uy = dx / d0, dy / d0
    d = max(min(d0, (a + b) * 0.9995), abs(a - b) + 1e-3)
    x = (a * a - b * b + d * d) / (2 * d)
    h = math.sqrt(max(a * a - x * x, 0))
    px, py = uy * bend, -ux * bend
    j = (root[0] + ux * x + px * h, root[1] + uy * x + py * h)
    e = (root[0] + ux * d, root[1] + uy * d)
    return j, e


def bez2(p0, c, p1, t):
    return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])


def bez3(p0, c1, c2, p1, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p1[0],
            u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p1[1])


def ticks(x, y, r0, r1, angs, w=5, color=INK, op=0.6):
    o = []
    for a in angs:
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        o.append(f'<line x1="{f(x+ca*r0)}" y1="{f(y+sa*r0)}" x2="{f(x+ca*r1)}" y2="{f(y+sa*r1)}" '
                 f'stroke="{color}" stroke-width="{f(w)}" stroke-linecap="round" opacity="{op}"/>')
    return ''.join(o)


def pill(p0, p1, w, fill, extra=''):
    return (f'<line x1="{f(p0[0])}" y1="{f(p0[1])}" x2="{f(p1[0])}" y2="{f(p1[1])}" stroke="{fill}" '
            f'stroke-width="{f(w)}" stroke-linecap="round"{extra}/>')


def drop(x, y, r, col=IVORY, op=1.0):
    return (f'<path d="M{f(x)},{f(y-r*2.4)} Q{f(x+r*1.1)},{f(y-r*0.4)} {f(x+r)},{f(y+r*0.2)} '
            f'A{f(r)},{f(r)} 0 1 1 {f(x-r)},{f(y+r*0.2)} Q{f(x-r*1.1)},{f(y-r*0.4)} {f(x)},{f(y-r*2.4)} Z" '
            f'fill="{col}" opacity="{op}"/>')


def line_hits(pts, x0, y0, m):
    """x of the intersections of y = y0 + m (x - x0) with polygon pts."""
    xs = []
    n = len(pts)
    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        fa = ay - (y0 + m * (ax - x0))
        fb = by - (y0 + m * (bx - x0))
        if fa == 0:
            xs.append(ax)
        if fa * fb < 0:
            t = fa / (fa - fb)
            xs.append(ax + (bx - ax) * t)
    return (min(xs), max(xs)) if xs else None


# ---------------------------------------------------------------- ink outline filters
_INK_DEFS = {}


def ink_filter(r):
    r = round(r * 2) / 2
    key = f'{r:.1f}'
    if key not in _INK_DEFS:
        fid = 'ink' + key.replace('.', '_')
        _INK_DEFS[key] = (fid, f'<filter id="{fid}" x="-35%" y="-35%" width="170%" height="170%" color-interpolation-filters="sRGB">'
                               f'<feMorphology in="SourceAlpha" operator="dilate" radius="{key}" result="d"/>'
                               f'<feFlood flood-color="{INK}" result="c"/><feComposite in="c" in2="d" operator="in" result="o"/>'
                               f'<feMerge><feMergeNode in="o"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    return _INK_DEFS[key][0]


def inked(svg, r):
    if not svg or not svg.strip():
        return ''
    return f'<g filter="url(#{ink_filter(r)})">{svg}</g>'


# =====================================================================
# EYE GEOMETRY
# =====================================================================
def rrect_pts(cx, cy, w, h, rt, rb, n=10):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    pts = []
    for i in range(n + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / n
        pts.append((x1 - rt + rt * math.cos(a), y0 + rt + rt * math.sin(a)))
    for i in range(n + 1):
        a = (math.pi / 2) * i / n
        pts.append((x1 - rb + rb * math.cos(a), y1 - rb + rb * math.sin(a)))
    for i in range(n + 1):
        a = math.pi / 2 + (math.pi / 2) * i / n
        pts.append((x0 + rb + rb * math.cos(a), y1 - rb + rb * math.sin(a)))
    for i in range(n + 1):
        a = math.pi + (math.pi / 2) * i / n
        pts.append((x0 + rt + rt * math.cos(a), y0 + rt + rt * math.sin(a)))
    return pts


class EyeGeo:
    def __init__(self, kind, cx, cy, w, h, rt=0.0, rb=0.0):
        self.kind, self.cx, self.cy, self.w, self.h = kind, cx, cy, w, h
        if kind == 'capsule':
            self.rt = min(rt, w / 2, h / 2)
            self.rb = min(rb, w / 2, h / 2)
            self.pts = rrect_pts(cx, cy, w, h, self.rt, self.rb)
        else:
            self.pts = [(cx + w / 2 * math.cos(2 * math.pi * i / 96), cy + h / 2 * math.sin(2 * math.pi * i / 96)) for i in range(96)]

    def span(self, x):
        dx = abs(x - self.cx)
        hw, hh = self.w / 2, self.h / 2
        if dx > hw:
            return None
        if self.kind == 'capsule':
            rt, rb = self.rt, self.rb
            if dx <= hw - rt:
                yt = self.cy - hh
            else:
                d = dx - (hw - rt)
                yt = self.cy - hh + rt - math.sqrt(max(rt * rt - d * d, 0))
            if dx <= hw - rb:
                yb = self.cy + hh
            else:
                d = dx - (hw - rb)
                yb = self.cy + hh - rb + math.sqrt(max(rb * rb - d * d, 0))
            return yt, yb
        u = dx / hw
        q = hh * math.sqrt(max(1 - u * u, 0))
        return self.cy - q, self.cy + q

    def hits_y(self, y):
        return line_hits(self.pts, self.cx, y, 0.0)


# =====================================================================
# FACE RIG
# =====================================================================
class Head:
    def __init__(self, D, P):
        self.D, self.R, self.P = D, D / 2, P
        self.skin, self.shad = P['skin'], P['shad']
        self.stats = {}

    def k(self, v):
        return v * self.D

    def rim_y(self, x):
        return -math.sqrt(max(self.R ** 2 - x * x, 0))

    def top_extent(self, face=None):
        return self.k(self.P.get('top_ext', self.P.get('hair_rise', 0)))

    # ------------------------------------------------------------ ears
    def ears(self, t):
        D, R = self.D, self.R
        sc = self.P.get('ear', 1.0)
        out = []
        for s in (-1, 1):
            front = s * t > 0.15
            kx = 1 - 0.45 * abs(t) if front else 1.0
            rx, ry = 0.06 * D * kx * sc, 0.085 * D * sc
            prot = 0.065 * D * kx * sc
            cx = s * (R + prot - rx)
            cy = self.k(self.P.get('ear_y', -0.01))
            col, inner = (self.skin, self.shad) if s < 0 else (self.shad, shade(self.shad, 0.16))
            out.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{col}"/>')
            out.append(f'<ellipse cx="{f(cx + s*rx*0.25)}" cy="{f(cy + ry*0.08)}" rx="{f(rx*0.48)}" ry="{f(ry*0.55)}" fill="{inner}"/>')
        return out

    def ear_point(self, s):
        """attachment point at the bottom of ear s (local coords)."""
        return (s * (self.R + 0.01 * self.D), self.k(self.P.get('ear_y', -0.01) + 0.07))

    # ------------------------------------------------------------ hair
    def hair_flattop(self, face):
        """charcoal salt-and-pepper flat-top: flat deck 0.085 D above the skull,
        narrower than the head, buzzed sides flowing out of the rim, level
        hairline joined to the skin, level sideburn cut.  No grooves, no zigzag."""
        k, R = self.k, self.R
        P = self.P
        t = face.get('turn', 0.0)
        a = min(abs(t) / 0.7, 1.0)
        sh = k(-0.035 * t)
        rise = k(P['hair_rise'])
        yt = -R - rise
        xd = k(P.get('deck_w', 0.37))
        xl, xr = -xd + sh, xd + sh
        cr = k(0.085)
        yb = k(-0.07)
        yh = k(P.get('hairline', -0.425))
        c2 = k(0.06)
        ro = R + k(0.014)
        yj = k(-0.25)

        def bw(sd):
            back = sd * t < -0.1
            return k(0.06 + (0.05 * a if back else -0.02 * a))

        def rim_pt(y, sd, r):
            return (sd * math.sqrt(max(r * r - y * y, 0)), y)
        pts = []
        n = 10
        for i in range(n + 1):
            pts.append(rim_pt(yb + (yj - yb) * i / n, -1, ro))
        p0 = rim_pt(yj, -1, ro)
        pts += [bez3(p0, (p0[0] - k(0.008), p0[1] - k(0.11)), (xl, yt + cr + k(0.10)), (xl, yt + cr), u / 10) for u in range(1, 11)]
        pts += [(xl + cr - cr * math.cos(q), yt + cr - cr * math.sin(q)) for q in [i * math.pi / 16 for i in range(1, 9)]]
        pts += [(xr - cr + cr * math.sin(q), yt + cr - cr * math.cos(q)) for q in [i * math.pi / 16 for i in range(0, 9)]]
        p0r = rim_pt(yj, 1, ro)
        pts += [bez3((xr, yt + cr), (xr, yt + cr + k(0.10)), (p0r[0] + k(0.008), p0r[1] - k(0.11)), p0r, u / 10) for u in range(1, 11)]
        for i in range(1, n + 1):
            pts.append(rim_pt(yj + (yb - yj) * i / n, 1, ro))
        for sd in (1, -1):
            ri = R - bw(sd)
            yc = yh + c2
            col = [rim_pt(yb + (yc - yb) * i / 12, sd, ri) for i in range(13)]
            xc = col[-1][0]
            corner = [bez2((xc, yc), (xc, yh), (xc - sd * c2, yh), u / 6) for u in range(1, 7)]
            seg = col + corner
            pts += seg if sd == 1 else seg[::-1]
        return pts, (xl, xr, yt)

    def hair_slick(self, face):
        """center-parted slicked hair with a receding M hairline.  At the back it
        ends in three long, narrow, back-swept points (0.28 D past the skull,
        tips curling slightly up -- always running into the wind).
        Drawn canonically facing screen-left and mirrored for t > 0.
        Returns (cap polygon, [tail polygons], hairline polyline, marks)."""
        k, R = self.k, self.R
        t = face.get('turn', 0.0)
        a = min(abs(t) / 0.7, 1.0)
        fl = 1 if t <= 0 else -1
        px = -0.13 * abs(t)
        rise = self.P['hair_rise']
        Rd = 0.5
        cap = []
        th0 = math.atan2(-0.22, -math.sqrt(0.51 ** 2 - 0.22 ** 2))
        thE = math.atan2(-0.05, 0.49)
        n = 48
        for i in range(n + 1):
            u = i / n
            th = th0 + (thE - th0) * u
            up = math.sin(math.pi * min(1.0, u * 1.15)) ** 0.6
            r = Rd + 0.012 + rise * up
            cap.append((r * math.cos(th), r * math.sin(th)))
        bwb = 0.065 + 0.04 * a
        bwf = 0.045 - 0.012 * a
        Bi = (math.sqrt((Rd - bwb) ** 2 - 0.10 ** 2), -0.10)
        B = (px + 0.37, -0.32)
        BR = (px + 0.20, -0.485)
        WP = (px, -0.395)
        FR = (px - 0.18 * (1 - 0.3 * a), -0.485)
        F = (px - 0.27 * (1 - 0.25 * a), -0.35)
        Fi = (-math.sqrt((Rd - bwf) ** 2 - 0.22 ** 2), -0.22)
        inner = [(Bi, (Bi[0] - 0.01, B[1] + 0.08), B), (B, (B[0] - 0.01, BR[1] + 0.07), BR), (BR, (px + 0.08, -0.47), WP),
                 (WP, (px - 0.08, -0.47), FR), (FR, (F[0] + 0.01, FR[1] + 0.07), F), (F, (Fi[0] + 0.01, F[1] + 0.06), Fi)]
        hl = [Bi]
        for p0, c, p1 in inner:
            hl += [bez2(p0, c, p1, u / 8) for u in range(1, 9)]
        cap = cap + [(0.47, -0.05), Bi] + hl[1:]
        # three narrow swept tails
        tails = []
        for base, c, tip, w in (((0.28, -0.44), (0.58, -0.50), (0.70, -0.61), 0.12),
                                ((0.38, -0.26), (0.66, -0.30), (0.78, -0.43), 0.11),
                                ((0.40, -0.08), (0.63, -0.11), (0.74, -0.24), 0.09)):
            left, right = [], []
            m = 18
            for i in range(m + 1):
                u = i / m
                p = bez2(base, c, tip, u)
                q = bez2(base, c, tip, min(u + 0.01, 1))
                r_ = bez2(base, c, tip, max(u - 0.01, 0))
                tx, ty = q[0] - r_[0], q[1] - r_[1]
                L = math.hypot(tx, ty) or 1e-6
                nx_, ny_ = -ty / L, tx / L
                ww = w * (1 - u) ** 0.85 / 2
                left.append((p[0] + nx_ * ww, p[1] + ny_ * ww))
                right.append((p[0] - nx_ * ww, p[1] - ny_ * ww))
            tails.append(left + right[::-1])
        S = lambda pts: [(fl * x * self.D, y * self.D) for x, y in pts]
        o = []
        o.append(f'<line x1="{f(fl*k(px))}" y1="{f(k(-0.372))}" x2="{f(fl*k(px*1.05))}" y2="{f(k(-0.5 - rise*0.75))}" '
                 f'stroke="{self.skin}" stroke-width="{f(k(0.016))}" stroke-linecap="round"/>')
        gc = '#46413D'
        for p0, c, p1, w in (((px + 0.05, -0.49), (0.30, -0.53), (0.52, -0.50), 0.018),
                             ((px + 0.10, -0.43), (0.36, -0.40), (0.55, -0.31), 0.018),
                             ((px - 0.05, -0.49), (-0.27, -0.50), (-0.42, -0.30), 0.016)):
            o.append(f'<path d="M{f(fl*k(p0[0]))},{f(k(p0[1]))} Q{f(fl*k(c[0]))},{f(k(c[1]))} {f(fl*k(p1[0]))},{f(k(p1[1]))}" '
                     f'stroke="{gc}" stroke-width="{f(k(w))}" stroke-linecap="round" fill="none"/>')
        return S(cap), [S(tp) for tp in tails], S(hl), ''.join(o)

    def hair_part(self, face):
        """neat chestnut SIDE PART lying close to the skull (soft swept fringe,
        slightly receding temples, grey at the temples) and ONE big cowlick curl
        springing up from the crown and rolling forward.  No spikes, nothing
        swept backward.  Drawn canonically facing screen-left, mirrored for t > 0.
        Returns (cap, curl, hairline, marks-inside-cap)."""
        k, R = self.k, self.R
        P = self.P
        t = face.get('turn', 0.0)
        a = min(abs(t) / 0.7, 1.0)
        fl = 1 if t <= 0 else -1
        px = -0.13 * abs(t)
        rise = P['hair_rise']
        Rd = 0.5
        # outer contour: front temple -> over the top -> back, above the ear
        th0 = math.atan2(-0.24, -math.sqrt(0.512 ** 2 - 0.24 ** 2))
        thE = math.atan2(-0.06, 0.49)
        cap = []
        n = 48
        for i in range(n + 1):
            u = i / n
            th = th0 + (thE - th0) * u
            up = math.sin(math.pi * min(1.0, u * 1.08)) ** 0.7
            r = Rd + 0.012 + rise * up * (0.70 + 0.45 * u)
            cap.append((r * math.cos(th), r * math.sin(th)))
        bwb = 0.06 + 0.04 * a
        bwf = 0.045 - 0.012 * a
        Bi = (math.sqrt((Rd - bwb) ** 2 - 0.12 ** 2), -0.12)
        B = (px + 0.35, -0.315)            # back temple, a little receded
        W1 = (px + 0.15, -0.392)           # swept fringe
        W2 = (px - 0.03, -0.372)           # lowest point of the sweep
        Pp = (px - 0.12, -0.428)           # the part (notch)
        F = (px - 0.27 * (1 - 0.25 * a), -0.372)
        Fi = (-math.sqrt((Rd - bwf) ** 2 - 0.24 ** 2), -0.24)
        Ft = (F[0] - 0.06 * (1 - 0.3 * a), -0.405)    # receding front temple
        segs = [(Bi, (Bi[0] - 0.01, B[1] + 0.08), B), (B, (px + 0.27, -0.395), W1), (W1, (px + 0.06, -0.372), W2),
                (W2, (px - 0.10, -0.372), Pp), (Pp, (px - 0.20, -0.42), F), (F, (F[0] - 0.02, -0.40), Ft),
                (Ft, (Fi[0] + 0.005, Ft[1] + 0.03), Fi)]
        hl = [Bi]
        for p0, c, p1 in segs:
            hl += [bez2(p0, c, p1, u / 10) for u in range(1, 11)]
        cap = cap + [(0.47, -0.05), Bi] + hl[1:]
        # the cowlick: a tapered spiral springing up at the crown, rolling forward
        ph0, ph1 = math.radians(P.get('curl_a0', 62)), math.radians(P.get('curl_a1', -205))
        r0, r1 = P.get('curl_r', (0.11, 0.05))
        w0, w1 = P.get('curl_w', (0.12, 0.03))
        bx, by = P.get('curl_base', (0.12, -0.525))
        C = (bx - r0 * math.cos(ph0), by - r0 * math.sin(ph0))
        m = 64
        cl = []
        for i in range(m + 1):
            u = i / m
            ph = ph0 + (ph1 - ph0) * u
            rr = r0 + (r1 - r0) * u
            cl.append((C[0] + rr * math.cos(ph), C[1] + rr * math.sin(ph)))
        left, right = [], []
        for i in range(m + 1):
            u = i / m
            p_ = cl[i]
            q = cl[min(i + 1, m)]
            r_ = cl[max(i - 1, 0)]
            tx, ty = q[0] - r_[0], q[1] - r_[1]
            L = math.hypot(tx, ty) or 1e-6
            nx_, ny_ = -ty / L, tx / L
            ww = (w1 + (w0 - w1) * (1 - u) ** 0.8) / 2
            left.append((p_[0] + nx_ * ww, p_[1] + ny_ * ww))
            right.append((p_[0] - nx_ * ww, p_[1] - ny_ * ww))
        # anchor the base down into the cap
        curl = left + right[::-1] + [(cl[0][0] - 0.03, cl[0][1] + 0.08), (cl[0][0] + 0.03, cl[0][1] + 0.08)]
        S = lambda pts: [(fl * x * self.D, y * self.D) for x, y in pts]
        o = []
        hc, hd, hlc, gr = P['hair_col'], P['hair_shad'], P['hair_light'], P['hair_grey']
        # grey at the temples (both sides when visible)
        for gx, gy, rx_, ry_ in ((0.43, -0.16, 0.10, 0.13), (-0.44, -0.27, 0.075 * (1 - 0.3 * a), 0.085)):
            o.append(f'<ellipse cx="{f(fl*k(gx))}" cy="{f(k(gy))}" rx="{f(k(rx_*1.35))}" ry="{f(k(ry_*1.3))}" fill="{mix(hc, gr, 0.45)}"/>')
            o.append(f'<ellipse cx="{f(fl*k(gx + 0.01))}" cy="{f(k(gy + 0.02))}" rx="{f(k(rx_))}" ry="{f(k(ry_))}" fill="{gr}"/>')
        # comb lines following the sweep away from the part
        for p0, c, p1, w in (((px - 0.07, -0.47), (0.14, -0.57), (0.40, -0.40), 0.016),
                             ((px - 0.01, -0.425), (0.19, -0.48), (0.42, -0.29), 0.016),
                             ((px - 0.16, -0.46), (-0.27, -0.45), (-0.38, -0.33), 0.014)):
            o.append(f'<path d="M{f(fl*k(p0[0]))},{f(k(p0[1]))} Q{f(fl*k(c[0]))},{f(k(c[1]))} {f(fl*k(p1[0]))},{f(k(p1[1]))}" '
                     f'stroke="{hlc}" stroke-width="{f(k(w))}" stroke-linecap="round" fill="none"/>')
        # the part line: a short skin-coloured parting running back from the notch
        o.append(f'<path d="M{f(fl*k(Pp[0]))},{f(k(Pp[1] + 0.004))} Q{f(fl*k(Pp[0] + 0.01))},{f(k(-0.52))} {f(fl*k(Pp[0] + 0.06))},{f(k(-0.60))}" '
                 f'stroke="{self.skin}" stroke-width="{f(k(0.02))}" stroke-linecap="round" fill="none"/>')
        # curl: inner highlight stroke along the spiral
        hlp = cl[6:int(m * 0.62)]
        curl_mark = (f'<polyline points="{pstr(S(hlp))}" stroke="{hlc}" stroke-width="{f(k(0.014))}" fill="none" '
                     f'stroke-linecap="round" stroke-linejoin="round"/>')
        return S(cap), S(curl), S(hl), ''.join(o), curl_mark

    def hair_bun(self, face):
        k, R = self.k, self.R
        yh = k(-0.30)
        xh = math.sqrt(R * R - yh * yh)
        a0 = math.atan2(yh, -xh)
        a1 = math.atan2(yh, xh)
        if a0 > a1:
            a0 -= 2 * math.pi
        pts = [((R + k(0.02)) * math.cos(a0 + (a1 - a0) * i / 30), (R + k(0.02)) * math.sin(a0 + (a1 - a0) * i / 30)) for i in range(31)]
        poly = pts + [(xh * 0.9, yh + k(0.02)), (0, k(-0.36)), (-xh * 0.9, yh + k(0.02))]
        return [poly], f'<circle cx="0" cy="{f(-R - k(0.08))}" r="{f(k(0.14))}" fill="{self.P["hair_col"]}" stroke="{INK}" stroke-width="{f(k(0.012))}"/>'

    # ------------------------------------------------------------ eye layout
    def eye_layout(self, face):
        E = self.P['eye']
        e = face.get('eyes', {})
        t = face.get('turn', 0.0)
        a = min(abs(t) / 0.7, 1.0)
        W = E['W']
        g = e.get('gap', E['gap'])
        fx = face.get('fx', 0.115 * t)
        if abs(t) < 1e-6:
            xs = {'L': -(g / 2 + W / 2), 'R': g / 2 + W / 2}
            ws = {'L': W, 'R': W}
            nx = 0.0
        else:
            wf = 1 - 0.38 * a
            span = W * wf + g + W
            if t < 0:
                left = fx - span / 2
                xs = {'L': left + W * wf / 2, 'R': left + W * wf + g + W / 2}
                ws = {'L': W * wf, 'R': W}
                nx = left + W * wf + g / 2
            else:
                right = fx + span / 2
                xs = {'R': right - W * wf / 2, 'L': right - W * wf - g - W / 2}
                ws = {'R': W * wf, 'L': W}
                nx = right - W * wf - g / 2
        y = E['y'] + face.get('ey', 0)
        return xs, ws, y, fx, nx

    def eyes_svg(self, face, clip_id):
        k = self.k
        E = self.P['eye']
        e = face.get('eyes', {})
        xs, ws, ey, fx, nx = self.eye_layout(face)
        h = e.get('H', E['H'])
        out = []
        self.stats['eyes'] = {}
        for side in ('L', 'R'):
            o = -1 if side == 'L' else 1
            out.append(self._eye(side, o, k(xs[side]), k(ey), k(ws[side]), k(h), e, face, ws[side] / E['W']))
        return f'<g clip-path="url(#{clip_id})">' + '\n'.join(out) + '</g>'

    def _eye(self, side, o, cx, cy, w, h, e, face, wfrac):
        k = self.k
        E = self.P['eye']
        I = self.P['iris']

        def pick(key, default):
            v = e.get(key, E.get(key, default))
            return v[side] if isinstance(v, dict) else v
        g = EyeGeo(E['shape'], cx, cy, w, h, k(pick('rt', 0.14)), k(pick('rb', 0.12)))
        hr = k(E['H'])
        lid = pick('lid', 0.2)
        low = pick('low', 0.0)
        tilt = pick('tilt', 0.0)                 # + = inner end UP (worry slant)
        m = o * math.tan(math.radians(tilt))
        arc = k(pick('arc', 0.0))
        larc = k(pick('larc', 0.0))
        top, bot = cy - h / 2, cy + h / 2
        hw = w / 2
        ly = top + lid * h
        lowy = bot - low * h

        def lid_y(x):
            u = (x - cx) / hw
            return ly + m * (x - cx) - arc * (1 - u * u)

        def low_y(x):
            u = (x - cx) / hw
            return lowy - larc * (1 - u * u)
        N = 60
        xs = [cx - hw - 4 + (w + 8) * i / N for i in range(N + 1)]
        has_low = low > 0 or larc != 0
        open_poly = [(x, lid_y(x)) for x in xs] + [(x, low_y(x) if has_low else cy + 3 * h) for x in xs[::-1]]
        open_r = pick('open_r', 0.0)
        if open_r and has_low and not larc and abs(tilt) < 1e-6 and not arc:
            # level capsule: the visible white is a horizontal stadium between the two flat lids
            ym = (ly + lowy) / 2
            hit = g.hits_y(ym)
            if hit:
                sh_ = lowy - ly
                rr = min(k(open_r), sh_ / 2, (hit[1] - hit[0]) / 2)
                open_poly = rrect_pts((hit[0] + hit[1]) / 2, ym, hit[1] - hit[0], sh_ + 1, rr, rr)
        fpid, opid, irid = uid('fp'), uid('op'), uid('ir')
        G = [f'<clipPath id="{fpid}"><polygon points="{pstr(g.pts)}"/></clipPath>',
             f'<clipPath id="{opid}"><polygon points="{pstr(open_poly)}"/></clipPath>']
        lidtone = E.get('lidtone') or mix(self.skin, self.shad, 0.7)
        G.append(f'<polygon points="{pstr(g.pts)}" fill="{lidtone}"/>')
        inner = [f'<rect x="{f(cx-hw-6)}" y="{f(top-6)}" width="{f(w+12)}" height="{f(h+12)}" fill="{SCLERA}"/>']
        band = k(E.get('band', 0.04))
        band_poly = [(x, lid_y(x) - 3) for x in xs] + [(x, lid_y(x) + band) for x in xs[::-1]]
        inner.append(f'<polygon points="{pstr(band_poly)}" fill="{LIDBAND}"/>')
        # ---- iris
        ihr = k(E['ih'])
        if 'ih' in e:
            ih = k(e['ih'])
        elif 'ik' in e:
            ih = e['ik'] * h
        else:
            ih = ihr
        iw = ih * E.get('iw_ratio', 0.88) * wfrac * pick('iwk', 1.0)
        cut = k(E.get('cut', 0.04))
        if 'icy' in e:
            icy = cy + k(e['icy'])
        else:
            icy = (cy - hr / 2) + E['lid'] * hr + ihr / 2 - cut
        look = e.get('look')
        if look is not None:
            vx, vy = k(look[0]) - cx, k(look[1]) - cy
            L = math.hypot(vx, vy) or 1
            lk = e.get('look_k', 1.0)
            gx, gy = clamp(vx / L * lk * 1.25, -1, 1), clamp(vy / L * lk, -1, 1)
        else:
            gx, gy = pick('gaze', (0.0, 0.0))
        icy += gy * k(e.get('gy_k', 0.05))
        ix = cx + gx * (max(hw - iw / 2, 0) + k(E.get('over', 0.0)))
        ell = f'cx="{f(ix)}" cy="{f(icy)}" rx="{f(iw/2)}" ry="{f(ih/2)}"'
        inner.append(f'<clipPath id="{irid}"><ellipse {ell}/></clipPath>')
        inner.append(f'<ellipse {ell} fill="{I["light"]}"/>')
        y3 = icy - ih / 2 + ih / 3
        inner.append(f'<g clip-path="url(#{irid})">'
                     f'<ellipse cx="{f(ix)}" cy="{f(icy - ih*0.10)}" rx="{f(iw*0.56)}" ry="{f(ih*0.50)}" fill="{I["base"]}"/>'
                     f'<path d="M{f(ix-iw)},{f(icy-ih)} L{f(ix+iw)},{f(icy-ih)} L{f(ix+iw)},{f(y3 - ih*0.05)} '
                     f'Q{f(ix)},{f(y3 + ih*0.09)} {f(ix-iw)},{f(y3 - ih*0.05)} Z" fill="{I["shadow"]}"/>'
                     f'<polygon points="{pstr(band_poly)}" fill="{I["shadow"]}"/></g>')
        rw = k(E.get('ring_w', 0.018))
        inner.append(f'<ellipse cx="{f(ix)}" cy="{f(icy)}" rx="{f(max(iw/2 - rw/2, 1))}" ry="{f(max(ih/2 - rw/2, 1))}" fill="none" '
                     f'stroke="{I["ring"]}" stroke-width="{f(rw)}"/>')
        pr = k(e.get('pupil', E['pupil'])) / 2 * (ih / ihr)
        prx = pr * wfrac * pick('iwk', 1.0)
        inner.append(f'<ellipse cx="{f(ix)}" cy="{f(icy + ih*0.02)}" rx="{f(prx)}" ry="{f(pr)}" fill="{I["pupil"]}"/>')
        # ---- catchlights
        hl = E.get('hl')
        sc = ih / ihr
        if hl and not e.get('hl_off'):
            if hl == 'bubble':
                slide = e.get('slide', 0.0)
                bw, bh = k(E.get('hl_w', 0.12)) * max(sc, 0.75) * wfrac, k(E.get('hl_h', 0.045)) * max(sc, 0.75)
                bx = ix + slide * max(iw / 2 - bw / 2 - k(0.012), 0)
                by = icy - ih * 0.21 + abs(slide) * ih * 0.08
                inner.append(f'<rect x="{f(bx-bw/2)}" y="{f(by-bh/2)}" width="{f(bw)}" height="{f(bh)}" rx="{f(bh/2)}" fill="{HILITE}"/>')
            elif hl == 'dot_tear':
                r = k(E.get('hl_r', 0.045)) * max(sc, 0.85)
                inner.append(f'<ellipse cx="{f(ix - iw*0.22)}" cy="{f(icy - ih*0.21)}" rx="{f(r*min(1, wfrac*1.1))}" ry="{f(r)}" fill="{HILITE}"/>')
            elif hl == 'dot':
                r = k(E.get('hl_r', 0.03))
                inner.append(f'<circle cx="{f(ix - iw*0.22)}" cy="{f(icy - ih*0.20)}" r="{f(r)}" fill="{HILITE}"/>')
            r2 = E.get('hl2')
            if r2:
                rr2 = k(r2) * max(sc, 0.75)
                inner.append(f'<ellipse cx="{f(ix + iw*0.22)}" cy="{f(icy + ih*0.25)}" rx="{f(rr2*min(1, wfrac*1.1))}" ry="{f(rr2)}" fill="{HILITE}"/>')
        # tear shine along the inside of the lower lid
        tear = e.get('tear', E.get('tear', 0.0))
        if tear and not e.get('hl_off'):
            ins = k(0.032)
            pts = []
            for i in range(25):
                th = math.radians(38 + (142 - 38) * i / 24)
                pts.append((cx + (hw - ins) * math.cos(th), cy + (h / 2 - ins) * math.sin(th)))
            d = 'M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in pts)
            inner.append(f'<path d="{d}" stroke="{mix(SCLERA, I["light"], 0.75)}" stroke-width="{f(k(0.03*tear))}" fill="none" stroke-linecap="round"/>')
            inner.append(f'<path d="{d}" stroke="{HILITE}" stroke-width="{f(k(0.018*tear))}" fill="none" stroke-linecap="round"/>')
        G.append(f'<g clip-path="url(#{fpid})"><g clip-path="url(#{opid})">' + ''.join(inner) + '</g></g>')

        # ---- lines on top
        lines = []
        lash = k(pick('lash', 0.055))
        lowt = k(E.get('low_th', 0.02))
        lash_c = E.get('lash_col', INK)

        def inside(x):
            sp = g.span(x)
            if not sp:
                return False
            yl = lid_y(x)
            return sp[0] - 0.6 <= yl <= sp[1]
        step = max(w / 300, 0.3)
        xl_ = cx
        while xl_ - step > cx - hw and inside(xl_ - step):
            xl_ -= step
        xr_ = cx
        while xr_ + step < cx + hw and inside(xr_ + step):
            xr_ += step
        # crease above the lid (follows the footprint top) -- adult cue
        if E.get('crease'):
            ccol = shade(self.skin, 0.38)
            if lid >= 0.12:
                cp = []
                for i in range(41):
                    x = cx - hw * 0.92 + 2 * hw * 0.92 * i / 40
                    sp = g.span(x)
                    if sp and sp[0] < lid_y(x) - lash * 0.9:
                        cp.append((x, sp[0]))
                if len(cp) > 2:
                    lines.append(f'<polyline points="{pstr(cp)}" stroke="{ccol}" stroke-width="{f(k(0.018))}" fill="none" stroke-linecap="round"/>')
            else:
                lines.append(f'<path d="M{f(cx - hw*0.80)},{f(top - k(0.02))} Q{f(cx)},{f(top - k(0.075))} {f(cx + hw*0.80)},{f(top - k(0.02))}" '
                             f'stroke="{ccol}" stroke-width="{f(k(0.018))}" fill="none" stroke-linecap="round"/>')
        # lower line
        lowstyle = E.get('lower', 'flat')
        if lowstyle in ('flat', 'contour') and has_low:
            hit = g.hits_y(lowy)
            if hit:
                x0, x1 = hit
                if open_r and E.get('low_short') and abs(open_r - E.get('open_r', 0)) < 1e-6:
                    # level capsule: the lower lid line covers only the flat floor of the vial
                    rr_ = min(k(open_r), (lowy - ly) / 2) * 0.85
                    x0, x1 = x0 + rr_, x1 - rr_
                yy = lowy + lowt * 0.3
                pts = [(x, low_y(x) + lowt * 0.3) for x in [x0 + (x1 - x0) * i / 20 for i in range(21)]]
                lines.append(f'<polyline points="{pstr(pts)}" stroke="{lash_c}" stroke-width="{f(lowt)}" fill="none" stroke-linecap="butt"/>')
        elif lowstyle == 'contour':
            # thin lower lid line hugging the rounded bottom of the eye (no heavy bar)
            spk = E.get('low_span', 0.80)
            pts = []
            for i in range(41):
                x = cx - hw * spk + 2 * hw * spk * i / 40
                sp = g.span(x)
                if sp:
                    pts.append((x, sp[1] - lowt * 0.3))
            if len(pts) > 2:
                lines.append(f'<polyline points="{pstr(pts)}" stroke="{lash_c}" stroke-width="{f(lowt)}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        elif lowstyle == 'full':
            def ang(x, y):
                return math.atan2((y - cy) / (h / 2), (x - cx) / hw)
            ar = ang(xr_, lid_y(xr_))
            al = ang(xl_, lid_y(xl_))
            if al < 0:
                al += 2 * math.pi
            pts = []
            for i in range(41):
                th = ar + (al - ar) * i / 40
                pts.append((cx + (hw - lowt * 0.3) * math.cos(th), cy + (h / 2 - lowt * 0.3) * math.sin(th)))
            lines.append(f'<polyline points="{pstr(pts)}" stroke="{lash_c}" stroke-width="{f(lowt)}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        # upper lash line
        style = E.get('lash_style', 'square')
        if style == 'square':
            ov = k(0.008)
            pts = [(x, lid_y(x) - lash * 0.3) for x in [xl_ - ov + (xr_ - xl_ + 2 * ov) * i / 24 for i in range(25)]]
            lines.append(f'<polyline points="{pstr(pts)}" stroke="{lash_c}" stroke-width="{f(lash)}" fill="none" stroke-linecap="butt"/>')
        else:
            xin, xout = (xr_, xl_) if o < 0 else (xl_, xr_)
            topp, botp = [], []
            for i in range(31):
                u = i / 30
                x = xin + (xout - xin) * u
                tw = lash * (0.45 + 0.55 * u ** 0.8)
                yc = lid_y(x) - lash * 0.3
                topp.append((x, yc - tw / 2))
                botp.append((x, yc + tw / 2))
            lines.append(f'<polygon points="{pstr(topp + botp[::-1])}" fill="{lash_c}"/>')
            lines.append(f'<circle cx="{f(xout)}" cy="{f(lid_y(xout) - lash*0.3)}" r="{f(lash/2)}" fill="{lash_c}"/>')
            lines.append(f'<circle cx="{f(xin)}" cy="{f(lid_y(xin) - lash*0.3)}" r="{f(lash*0.45/2)}" fill="{lash_c}"/>')
        wob = e.get('wobble')
        if wob:
            base = ''.join(lines)
            G.append(f'<g opacity="0.28" transform="translate({f(-k(wob))},{f(k(wob*0.4))})">{base}</g>')
            G.append(f'<g opacity="0.28" transform="translate({f(k(wob))},{f(-k(wob*0.3))})">{base}</g>')
        G += lines
        # ---- age marks
        ac = shade(self.skin, 0.3)
        aw = k(0.016)
        if E.get('lowcrease'):
            yb = bot + k(0.032)
            G.append(f'<path d="M{f(cx - o*w*0.05)},{f(yb)} Q{f(cx + o*w*0.18)},{f(yb + k(0.02))} {f(cx + o*w*0.36)},{f(yb - k(0.012))}" '
                     f'stroke="{ac}" stroke-width="{f(aw)}" fill="none" stroke-linecap="round"/>')
        if E.get('crow') and e.get('crow', True) and wfrac > 0.8:
            x0 = cx + o * (hw * 0.80)
            y0 = bot + k(0.005)
            for dx_, dy_, L_ in ((0.035, 0.045, 0.045), (0.0, 0.065, 0.04)):
                xa, ya = x0 + o * k(dx_), y0 + k(dy_)
                G.append(f'<line x1="{f(xa)}" y1="{f(ya)}" x2="{f(xa + o*k(L_*0.75))}" y2="{f(ya + k(L_*0.55))}" '
                         f'stroke="{ac}" stroke-width="{f(aw)}" stroke-linecap="round"/>')
        if E.get('bag') and e.get('bag', True):
            yb = bot + k(0.022)
            G.append(f'<path d="M{f(cx + o*w*0.16)},{f(yb)} Q{f(cx + o*w*0.30)},{f(yb + k(0.022))} {f(cx + o*w*0.45)},{f(yb - k(0.012))}" '
                     f'stroke="{ac}" stroke-width="{f(aw)}" fill="none" stroke-linecap="round"/>')
        open_h = (low_y(cx) if has_low else bot) - lid_y(cx)
        self.stats['eyes'][side] = dict(w=w / self.D, h=h / self.D, cx=cx / self.D, cy=cy / self.D,
                                       top_below_skull=(top + self.R) / self.D, lid=lid, low=low,
                                       open=open_h / self.D, ih=ih / self.D, ih_frac=ih / h, lash=lash / self.D,
                                       ix=ix / self.D, icy=icy / self.D)
        return '\n'.join(G)

    # ------------------------------------------------------------ brows
    def brows_svg(self, face):
        out = []
        xs, ws, ey, fx, nx = self.eye_layout(face)
        for side in ('L', 'R'):
            out.append(self._brow(side, xs[side], ws[side], ey, face.get('brow' + side, {})))
        return '\n'.join(out)

    def _brow(self, side, ex, ew, ey, b):
        if b is None:
            return ''
        k = self.k
        B = self.P['brow']
        E = self.P['eye']
        s = -1 if side == 'L' else 1
        W = k(B['W'] * ew / E['W'] * b.get('wk', 1.0))
        H = k(b.get('h', B['H']))
        bx = k(ex) + s * k(B.get('out', 0.0)) + k(b.get('dx', 0))
        if B.get('ref') == 'lash':
            ref = k(ey - E['H'] / 2 + E['lid'] * E['H'] - E.get('lash', 0.05) * 0.3)
        else:
            ref = k(ey - E['H'] / 2)
        by = ref - k(B['gap']) - H / 2 + k(b.get('dy', 0))
        tilt = b.get('tilt', B.get('tilt', 0))          # + = inner end down
        r = tilt if side == 'L' else -tilt
        col = b.get('col', B.get('col', INK))
        out = []
        if b.get('trail') is not None:
            y_top = by + H / 2 + k(0.05)
            y_bot = k(b['trail'])
            n = b.get('trail_n', 3)
            seg = (y_bot - y_top) / n
            tw = max(k(0.024), 4)
            for i in range(n):
                y0 = y_top + i * seg + seg * 0.15
                y1 = y0 + seg * 0.55
                out.append(f'<line x1="{f(bx)}" y1="{f(y0)}" x2="{f(bx)}" y2="{f(y1)}" stroke="{col}" '
                           f'stroke-width="{f(tw)}" stroke-linecap="round" opacity="{f(0.85-0.2*i)}"/>')
        shp = self._brow_shape(B['shape'], side, W, H)
        for gdx, gdy, *gt in b.get('ghosts', []):
            gr = r + ((gt[0] if gt else 0) * (1 if side == 'L' else -1))
            out.append(f'<g transform="translate({f(bx + k(gdx))},{f(by + k(gdy))}) rotate({f(gr)})" opacity="0.3">{shp(col)}</g>')
        out.append(f'<g transform="translate({f(bx)},{f(by)}) rotate({f(r)})">{shp(col)}</g>')
        return '\n'.join(out)

    def _brow_shape(self, kind, side, W, H):
        if kind == 'pill':
            return lambda col: f'<rect x="{f(-W/2)}" y="{f(-H/2)}" width="{f(W)}" height="{f(H)}" rx="{f(H/2)}" fill="{col}"/>'
        s = 1 if side == 'L' else -1
        top, bot = [], []
        n = 14
        for i in range(n + 1):
            u = i / n
            x = s * (W / 2 - u * W)
            yc = -H * 0.35 * math.sin(math.pi * u) + H * 0.25 * u
            th = H * (1 - 0.62 * u ** 0.9) / 2
            top.append((x, yc - th))
            bot.append((x, yc + th))
        hx, hr = s * (W / 2), H / 2
        path = pstr(top + [(top[-1][0] - s * H * 0.12, (top[-1][1] + bot[-1][1]) / 2)] + bot[::-1])
        return lambda col: (f'<polygon points="{path}" fill="{col}"/>'
                            f'<circle cx="{f(hx)}" cy="0" r="{f(hr)}" fill="{col}"/>')

    # ------------------------------------------------------------ nose
    def nose_svg(self, face):
        k = self.k
        t = face.get('turn', 0)
        a = min(abs(t) / 0.7, 1)
        s = 1 if t >= 0 else -1
        xs, ws, ey, fx, nx = self.eye_layout(face)
        nxp = k(nx)
        kind = self.P['nose']
        lw = k(0.013)
        o = []
        if kind == 'long':
            yt, yb = k(-0.125), k(0.265)
            if abs(t) < 0.05:
                pts = [(nxp - k(0.022), yt), (nxp + k(0.022), yt), (nxp + k(0.072), yb - k(0.03)),
                       (nxp + k(0.068), yb), (nxp - k(0.068), yb), (nxp - k(0.072), yb - k(0.03))]
            else:
                tip = nxp + s * k(0.085 + 0.05 * a)
                back = nxp - s * k(0.055 - 0.01 * a)
                pts = [(nxp - s * k(0.018), yt), (nxp + s * k(0.022), yt), (tip, yb - k(0.035)),
                       (tip - s * k(0.01), yb), (back, yb), (back - s * k(0.008), yb - k(0.025))]
            o.append(f'<polygon points="{pstr(pts)}" fill="{self.shad}" stroke="{INK}" stroke-width="{f(lw)}" stroke-linejoin="round"/>')
            nxx = nxp + (s * k(0.025 + 0.02 * a) if abs(t) >= 0.05 else -k(0.03))
            o.append(f'<ellipse cx="{f(nxx)}" cy="{f(yb - k(0.018))}" rx="{f(k(0.03))}" ry="{f(k(0.013))}" fill="{shade(self.shad, 0.35)}"/>')
            if abs(t) < 0.05:
                o.append(f'<ellipse cx="{f(nxp + k(0.03))}" cy="{f(yb - k(0.018))}" rx="{f(k(0.03))}" ry="{f(k(0.013))}" fill="{shade(self.shad, 0.35)}"/>')
        elif kind == 'pointy':
            red = face.get('red', 0.0)
            ncol = mix(self.shad, RUDDY, red)
            yt, yb = k(-0.075), k(0.245)
            # thin bridge in the eye gap, then a small pointed tip (0.10 D)
            if abs(t) < 0.05:
                bridge = [(nxp - k(0.012), yt), (nxp + k(0.012), yt), (nxp + k(0.022), k(0.13)), (nxp - k(0.022), k(0.13))]
                tipp = [(nxp, k(0.12)), (nxp + k(0.055), yb - k(0.008)), (nxp - k(0.055), yb - k(0.008))]
            else:
                bridge = [(nxp - s * k(0.01), yt), (nxp + s * k(0.016), yt), (nxp + s * k(0.04), k(0.14)), (nxp - s * k(0.012), k(0.14))]
                tipx = nxp + s * k(0.075 + 0.03 * a)
                tipp = [(nxp + s * k(0.0), k(0.115)), (tipx, yb - k(0.012)), (nxp - s * k(0.045), yb)]
            o.append(f'<polygon points="{pstr(bridge)}" fill="{mix(self.skin, ncol, 0.7)}"/>')
            o.append(f'<polygon points="{pstr(tipp)}" fill="{ncol}" stroke="{INK}" stroke-width="{f(lw)}" stroke-linejoin="round"/>')
        elif kind == 'button':
            o.append(f'<ellipse cx="{f(nxp + s*k(0.02))}" cy="{f(k(0.17))}" rx="{f(k(0.065))}" ry="{f(k(0.05))}" fill="{self.shad}" '
                     f'stroke="{INK}" stroke-width="{f(lw)}"/>')
            o.append(f'<rect x="{f(nxp - k(0.012))}" y="{f(k(-0.02))}" width="{f(k(0.024))}" height="{f(k(0.15))}" rx="{f(k(0.012))}" fill="{mix(self.skin, self.shad, 0.6)}"/>')
        return '\n'.join(o)

    # ------------------------------------------------------------ glasses
    def glasses_svg(self, face):
        g = self.P.get('glasses')
        if not g:
            return ''
        k = self.k
        gl = face.get('glasses', {})
        xs, ws, ey, fx, nx = self.eye_layout(face)
        E = self.P['eye']
        t = face.get('turn', 0)
        s = 1 if t >= 0 else -1
        y0 = k(g['y'] + gl.get('dy', 0))
        lh = k(g['h'])
        rim = k(0.017)
        parts = []
        inner_pts = {}
        for side in ('L', 'R'):
            cx = k(xs[side] * g.get('xk', 0.92) + gl.get('dx', 0))
            lw = k(g['w'] * ws[side] / E['W'])
            pts = [(cx - lw / 2, y0)]
            for i in range(1, 20):
                aa = math.pi * i / 20
                pts.append((cx - lw / 2 * math.cos(aa), y0 + lh * math.sin(aa)))
            pts.append((cx + lw / 2, y0))
            o_sign = -1 if side == 'L' else 1
            inner_pts[side] = (cx - o_sign * lw / 2, y0)
            parts.append(f'<polygon points="{pstr(pts)}" fill="{IVORY}" fill-opacity="0.30" stroke="{GOLD}" stroke-width="{f(rim)}" stroke-linejoin="round"/>')
            parts.append(f'<line x1="{f(cx - lw/2 + rim*1.5)}" y1="{f(y0 + lh*0.3)}" x2="{f(cx - lw*0.12)}" y2="{f(y0 + lh*0.72)}" stroke="#FFFFFF" stroke-opacity="0.55" stroke-width="{f(k(0.011))}" stroke-linecap="round"/>')
            if s * o_sign < 0 or abs(t) < 0.05:
                ex = o_sign * (self.R + k(0.01))
                parts.append(f'<line x1="{f(cx + o_sign*lw/2)}" y1="{f(y0)}" x2="{f(ex)}" y2="{f(k(0.0))}" stroke="{GOLD}" stroke-width="{f(rim*0.8)}" stroke-linecap="round"/>')
        a, b = inner_pts['L'], inner_pts['R']
        mid = ((a[0] + b[0]) / 2, y0 + k(0.012))
        parts.append(f'<path d="M{f(a[0])},{f(a[1])} Q{f(mid[0])},{f(mid[1])} {f(b[0])},{f(b[1])}" stroke="{GOLD}" stroke-width="{f(rim)}" fill="none" stroke-linecap="round"/>')
        rotg = gl.get('rot', 0)
        return f'<g transform="rotate({f(rotg)} {f(k(nx))} {f(y0)})">' + ''.join(parts) + '</g>'

    # ------------------------------------------------------------ mouth (kept modest)
    def mouth_svg(self, face):
        k = self.k
        m = face.get('mouth', {})
        xs, ws, ey, fx, nx = self.eye_layout(face)
        tp = m.get('type', 'flat')
        x = k(nx + m.get('dx', 0) + 0.02 * face.get('turn', 0))
        y = k(self.P['mouth_y'] + m.get('dy', 0))
        w = k(m.get('w', 0.18))
        th = k(m.get('th', 0.026))
        st = f'stroke="{INK}" stroke-width="{f(th)}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
        if tp == 'flat':
            tl = m.get('tilt', 0)
            return f'<line x1="{f(x-w/2)}" y1="{f(y + k(tl))}" x2="{f(x+w/2)}" y2="{f(y - k(tl))}" {st}/>'
        if tp == 'curl':
            c = k(m.get('curl', 0.05))
            s = 1 if m.get('side', 'R') == 'R' else -1
            a_, b_ = x - s * w / 2, x + s * w / 2
            kx = x + s * w * 0.15
            return f'<path d="M{f(a_)},{f(y + k(0.006))} L{f(kx)},{f(y)} Q{f(b_)},{f(y)} {f(b_ + s*k(0.01))},{f(y-c)}" {st}/>'
        if tp == 'frown':
            a_ = k(m.get('amp', 0.03))
            return f'<path d="M{f(x-w/2)},{f(y+a_*0.6)} Q{f(x)},{f(y-a_*1.2)} {f(x+w/2)},{f(y+a_*0.6)}" {st}/>'
        if tp == 'zig':
            a_ = k(m.get('amp', 0.018))
            n = m.get('n', 4)
            pts = [(x - w / 2 + w * i / n, y + (a_ if i % 2 else -a_) * (0 if i in (0, n) else 1)) for i in range(n + 1)]
            return f'<polyline points="{pstr(pts)}" {st}/>'
        if tp == 'o':
            hh = k(m.get('h', 0.09))
            return f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(w/2)}" ry="{f(hh/2)}" fill="{MOUTH_IN}" stroke="{INK}" stroke-width="{f(th*0.9)}"/>'
        if tp == 'aah':
            H = k(m.get('h', 0.13))
            cid = uid('mo')
            pts = []
            n = 6
            for i in range(n + 1):
                xx = x - w / 2 + w * i / n
                pts.append((xx, y - H * 0.35 + (k(0.016) if i % 2 else -k(0.008)) * (0 if i in (0, n) else 1)))
            d = 'M' + ' L'.join(f'{f(px)},{f(py)}' for px, py in pts)
            d += f' Q{f(x+w/2)},{f(y+H*0.65)} {f(x)},{f(y+H*0.6)} Q{f(x-w/2)},{f(y+H*0.65)} {f(x-w/2)},{f(y-H*0.35)} Z'
            return (f'<clipPath id="{cid}"><path d="{d}"/></clipPath>'
                    f'<path d="{d}" fill="{MOUTH_IN}" stroke="{INK}" stroke-width="{f(th)}" stroke-linejoin="round"/>'
                    f'<g clip-path="url(#{cid})"><ellipse cx="{f(x + w*0.08)}" cy="{f(y+H*0.62)}" rx="{f(w*0.3)}" ry="{f(H*0.3)}" fill="{TONGUE}"/></g>')
        return ''

    # ------------------------------------------------------------ lower face
    def lowerface_svg(self, face):
        k = self.k
        xs, ws, ey, fx, nx = self.eye_layout(face)
        t = face.get('turn', 0)
        a = min(abs(t) / 0.7, 1)
        col = shade(self.skin, 0.24)
        lw = k(0.017)
        o = []
        kind = self.P.get('lower')
        nxp = k(nx)
        my = k(self.P['mouth_y'])
        if kind == 'level':
            for s in (-1, 1):
                sq = 1 - 0.45 * a if s * t > 0 else 1
                x0 = nxp + s * k(0.10) * sq
                x1 = nxp + s * k(0.165) * sq
                o.append(f'<path d="M{f(x0)},{f(k(0.262))} Q{f(x1)},{f(k(0.29))} {f(x1 - s*k(0.008))},{f(my + k(0.035))}" '
                         f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
            o.append(f'<line x1="{f(nxp - k(0.055))}" y1="{f(k(0.435))}" x2="{f(nxp + k(0.055))}" y2="{f(k(0.435))}" '
                     f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round"/>')
        elif kind == 'laugh':
            # adult cues: laugh lines from the nose wings around the mouth corners + soft chin line
            col = shade(self.skin, 0.30)
            lw = k(0.019)
            for s in (-1, 1):
                sq = 1 - 0.45 * a if s * t > 0 else 1
                x0 = nxp + s * k(0.10) * sq
                o.append(f'<path d="M{f(x0)},{f(k(0.262))} Q{f(x0 + s*k(0.062)*sq)},{f(my - k(0.01))} {f(x0 + s*k(0.042)*sq)},{f(my + k(0.075))}" '
                         f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
            o.append(f'<path d="M{f(nxp - k(0.08))},{f(k(0.455))} Q{f(nxp)},{f(k(0.482))} {f(nxp + k(0.08))},{f(k(0.455))}" '
                     f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
        elif kind == 'jowl':
            for s in (-1, 1):
                sq = 1 - 0.45 * a if s * t > 0 else 1
                x0 = nxp + s * k(0.15) * sq
                o.append(f'<path d="M{f(x0)},{f(my - k(0.04))} Q{f(x0 + s*k(0.03))},{f(my + k(0.02))} {f(x0 + s*k(0.005))},{f(my + k(0.075))}" '
                         f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
            o.append(f'<path d="M{f(nxp - k(0.09))},{f(k(0.45))} Q{f(nxp)},{f(k(0.48))} {f(nxp + k(0.09))},{f(k(0.45))}" '
                     f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
        return '\n'.join(o)

    def creases_svg(self, face):
        c = face.get('crease')
        if not c:
            return ''
        k = self.k
        xs, ws, ey, fx, nx = self.eye_layout(face)
        col = shade(self.skin, 0.32)
        E = self.P['eye']
        y0 = k(ey - E['H'] / 2 - 0.07)
        o = []
        for s in (-1, 1):
            x = k(nx) + s * k(0.022)
            if c == 'anger':
                o.append(f'<line x1="{f(x)}" y1="{f(y0 - k(0.05))}" x2="{f(x - s*k(0.006))}" y2="{f(y0 + k(0.03))}" stroke="{col}" stroke-width="{f(k(0.016))}" stroke-linecap="round"/>')
            else:
                o.append(f'<path d="M{f(x)},{f(y0 - k(0.05))} Q{f(x + s*k(0.018))},{f(y0 - k(0.02))} {f(x)},{f(y0 + k(0.01))}" stroke="{col}" stroke-width="{f(k(0.015))}" stroke-linecap="round" fill="none"/>')
        return ''.join(o)

    def extras(self, face):
        k = self.k
        o = []
        for sw in face.get('sweat', []):
            sx, sy = sw[0], sw[1]
            sc = sw[2] if len(sw) > 2 else 1.0
            o.append(drop(k(sx), k(sy), k(0.04) * sc, col='#DCEAF2'))
        return '\n'.join(o)

    # ------------------------------------------------------------ whole head
    def draw(self, cx, cy, face):
        k, R, D = self.k, self.R, self.D
        P = self.P
        t = face.get('turn', 0.0)
        clip, msk = uid('hc'), uid('hm')
        o = []
        o.append(f'<clipPath id="{clip}"><circle r="{f(R)}"/></clipPath>')
        o.append(f'<mask id="{msk}" maskUnits="userSpaceOnUse" x="{f(-3*R)}" y="{f(-3*R)}" width="{f(6*R)}" height="{f(6*R)}">'
                 f'<rect x="{f(-3*R)}" y="{f(-3*R)}" width="{f(6*R)}" height="{f(6*R)}" fill="#fff"/>'
                 f'<circle cx="{f(k(-0.12))}" cy="{f(k(-0.08))}" r="{f(R)}" fill="#000"/></mask>')
        hmsk = uid('hhm')
        o.append(f'<mask id="{hmsk}" maskUnits="userSpaceOnUse" x="{f(-3*R)}" y="{f(-3*R)}" width="{f(6*R)}" height="{f(6*R)}">'
                 f'<rect x="{f(-3*R)}" y="{f(-3*R)}" width="{f(6*R)}" height="{f(6*R)}" fill="#fff"/>'
                 f'<circle cx="{f(k(-0.12))}" cy="{f(k(-0.20))}" r="{f(k(0.60))}" fill="#000"/></mask>')
        o += self.ears(t)
        o.append(f'<circle r="{f(R)}" fill="{self.skin}"/>')
        o.append(f'<circle r="{f(R)}" fill="{self.shad}" mask="url(#{msk})"/>')
        hk = P['hair']
        hs = f'stroke="{INK}" stroke-width="{f(k(0.012))}" stroke-linejoin="round"'
        if hk == 'flattop':
            pts, deck = self.hair_flattop(face)
            hid = uid('hp')
            o.append(f'<clipPath id="{hid}"><polygon points="{pstr(pts)}"/></clipPath>')
            o.append(f'<polygon points="{pstr(pts)}" fill="{P["hair_col"]}"/>')
            o.append(f'<polygon points="{pstr(pts)}" fill="{P["hair_shad"]}" mask="url(#{hmsk})"/>')
            xl, xr, yt = deck
            o.append(f'<rect clip-path="url(#{hid})" x="{f(xl - k(0.05))}" y="{f(yt - 2)}" width="{f(xr - xl + k(0.1))}" height="{f(k(0.045))}" fill="{P["hair_top"]}"/>')
            o.append(f'<rect clip-path="url(#{hid})" x="{f(-R*1.2)}" y="{f(k(-0.30))}" width="{f(R*2.4)}" height="{f(k(0.30))}" fill="{mix(P["hair_col"], P["hair_top"], 0.45)}"/>')
            o.append(f'<polygon points="{pstr(pts)}" fill="none" {hs}/>')
        elif hk == 'slick':
            poly, tails, hline, marks = self.hair_slick(face)
            for tp in tails:
                o.append(f'<polygon points="{pstr(tp)}" fill="{P["hair_col"]}"/>')
            o.append(f'<polygon points="{pstr(poly)}" fill="{P["hair_col"]}"/>')
            o.append(f'<polygon points="{pstr(poly)}" fill="{P["hair_shad"]}" mask="url(#{msk})" opacity="0.8"/>')
            o.append(marks)
            o.append(f'<polyline points="{pstr(hline)}" fill="none" {hs}/>')
        elif hk == 'part':
            cap, curl, hline, marks, curl_mark = self.hair_part(face)
            hid = uid('hp')
            o.append(f'<polygon points="{pstr(curl)}" fill="{P["hair_col"]}" stroke="{INK}" stroke-width="{f(k(0.012))}" stroke-linejoin="round"/>')
            o.append(curl_mark)
            o.append(f'<clipPath id="{hid}"><polygon points="{pstr(cap)}"/></clipPath>')
            o.append(f'<polygon points="{pstr(cap)}" fill="{P["hair_col"]}"/>')
            o.append(f'<polygon points="{pstr(cap)}" fill="{P["hair_shad"]}" mask="url(#{msk})" opacity="0.75"/>')
            o.append(f'<g clip-path="url(#{hid})">{marks}</g>')
            o.append(f'<polyline points="{pstr(hline)}" fill="none" {hs}/>')
        elif hk == 'bun':
            polys, bun = self.hair_bun(face)
            o.append(bun)
            for p in polys:
                o.append(f'<polygon points="{pstr(p)}" fill="{P["hair_col"]}" {hs}/>')
        feats = [self.eyes_svg(face, clip), self.nose_svg(face), self.lowerface_svg(face), self.mouth_svg(face),
                 self.glasses_svg(face), self.creases_svg(face), self.brows_svg(face)]
        o += feats
        o.append(self.extras(face))
        tr = f'translate({f(cx)},{f(cy)})'
        tl = face.get('tilt', 0)
        if tl:
            tr += f' rotate({f(tl)})'
        return f'<g transform="{tr}">\n' + '\n'.join(o) + '\n</g>'


# =====================================================================
# PROPS
# =====================================================================
def cloche(cx, bottom, w, steam=True):
    """silver cloche tray (dome over the brim-full tea), w = tray width."""
    o = []
    ty = bottom - 0.05 * w
    o.append(f'<ellipse cx="{f(cx)}" cy="{f(ty + 0.03*w)}" rx="{f(0.5*w)}" ry="{f(0.075*w)}" fill="{DOME_D}"/>')
    o.append(f'<ellipse cx="{f(cx)}" cy="{f(ty)}" rx="{f(0.5*w)}" ry="{f(0.075*w)}" fill="{DOME}"/>')
    o.append(f'<ellipse cx="{f(cx)}" cy="{f(ty - 0.004*w)}" rx="{f(0.43*w)}" ry="{f(0.052*w)}" fill="{DOME_L}"/>')
    dw, dh = 0.40 * w, 0.44 * w
    by = ty + 0.012 * w
    dome = f'M{f(cx-dw)},{f(by)} A{f(dw)},{f(dh)} 0 0 1 {f(cx+dw)},{f(by)} Z'
    did = uid('dm')
    o.append(f'<clipPath id="{did}"><path d="{dome}"/></clipPath>')
    o.append(f'<path d="{dome}" fill="{DOME_D}"/>')
    o.append(f'<g clip-path="url(#{did})"><ellipse cx="{f(cx - 0.07*w)}" cy="{f(by + 0.02*w)}" rx="{f(dw*0.93)}" ry="{f(dh*0.98)}" fill="{DOME}"/>'
             f'<path d="M{f(cx - dw*0.72)},{f(by - dh*0.12)} Q{f(cx - dw*0.70)},{f(by - dh*0.78)} {f(cx - dw*0.12)},{f(by - dh*0.93)}" '
             f'stroke="{DOME_L}" stroke-width="{f(0.045*w)}" fill="none" stroke-linecap="round"/></g>')
    o.append(f'<ellipse cx="{f(cx)}" cy="{f(by)}" rx="{f(dw*1.03)}" ry="{f(0.032*w)}" fill="{DOME_D}"/>')
    hy = by - dh
    o.append(f'<rect x="{f(cx - 0.025*w)}" y="{f(hy - 0.035*w)}" width="{f(0.05*w)}" height="{f(0.05*w)}" fill="{DOME_D}"/>')
    o.append(f'<circle cx="{f(cx)}" cy="{f(hy - 0.085*w)}" r="{f(0.055*w)}" fill="none" stroke="{DOME}" stroke-width="{f(0.032*w)}"/>')
    if steam:
        for sx, sg in ((-0.43, -1), (0.43, 1)):
            x0 = cx + sx * w
            y0 = by - 0.01 * w
            o.append(f'<path d="M{f(x0)},{f(y0)} q{f(sg*0.06*w)},{f(-0.05*w)} {f(0)},{f(-0.10*w)} t{f(0)},{f(-0.10*w)}" '
                     f'stroke="{IVORY}" stroke-width="{f(0.022*w)}" fill="none" stroke-linecap="round" opacity="0.85"/>')
    return '\n'.join(o)


def cloche_ghost(cx, bottom, w, op=0.42, col=IVORY):
    ty = bottom - 0.05 * w
    dw, dh = 0.40 * w, 0.44 * w
    by = ty + 0.012 * w
    return (f'<g opacity="{op}" fill="{col}">'
            f'<ellipse cx="{f(cx)}" cy="{f(ty + 0.015*w)}" rx="{f(0.5*w)}" ry="{f(0.08*w)}"/>'
            f'<path d="M{f(cx-dw)},{f(by)} A{f(dw)},{f(dh)} 0 0 1 {f(cx+dw)},{f(by)} Z"/>'
            f'<circle cx="{f(cx)}" cy="{f(by - dh - 0.085*w)}" r="{f(0.055*w)}" fill="none" stroke="{col}" stroke-width="{f(0.032*w)}"/>'
            f'</g>')


# =====================================================================
# STICK-BODY RIG
# =====================================================================
class Body:
    def __init__(self, D, neck=0.15, yoke=0.06, spine=1.0, leg=1.55, uarm=0.68, farm=0.70, sh=0.27,
                 torso=JACKET, arm_col=JACKET, leg_col=TROUSER, skin=SKIN_L, hand=GLOVE, hand_edge=None,
                 w0=0.072, w1=0.052, neck_w=0.17, mit_l=0.20, mit_w=0.13, shoe_l=0.30, ankle=0.07,
                 kind='mess', shoe='oxford', min_w=10, stripe=None):
        self.D = D
        self.neck, self.yoke, self.spine = neck, yoke, spine
        self.ankle = ankle * D
        self.thigh = self.shin = (leg * D - self.ankle) / 2
        self.uarm, self.farm = uarm * D, farm * D
        self.sh = sh
        self.torso = torso
        self.arm_col, self.arm_far = arm_col, shade(arm_col, 0.10)
        self.leg_col, self.leg_far = leg_col, shade(leg_col, 0.14)
        self.skin = skin
        self.hand, self.hand_edge = hand, hand_edge
        self.r0 = max(w0 * D, min_w) / 2
        self.r2 = max(w1 * D, min_w) / 2
        self.r1 = (self.r0 + self.r2) / 2
        self.neck_w = neck_w * D
        self.mit_l, self.mit_w = mit_l * D, mit_w * D
        self.shoe_l = shoe_l * D
        self.kind, self.shoe = kind, shoe
        self.stripe = stripe

    def joints(self, C, face, pose):
        D, R = self.D, self.D / 2
        t = face.get('turn', 0)
        na = pose.get('neck', 0.0)
        u = (math.sin(math.radians(na)), -math.cos(math.radians(na)))
        n = (-u[1], u[0])
        o = pose.get('neck_off', -0.10 * t) * D
        Q = add(C, n, o)
        se = math.sqrt(max(R * R - o * o, 1))
        E = add(Q, u, -se)
        B = add(E, u, -self.neck * D)
        top = add(E, u, 0.07 * D)
        sa = pose.get('spine', 0.0)
        ch = pose.get('chest', sa)
        Y = add(B, dirv(ch), self.yoke * D)
        Hp = add(Y, dirv(sa), self.spine * D)
        dv = dirv(sa)
        perp = (dv[1], -dv[0])
        Cc = add(lerp(Y, Hp, 0.5), perp, pose.get('curve', 0) * D)
        tg = norm(sub(Cc, Y))
        sp = (tg[1], -tg[0])
        sw = self.sh * D * pose.get('sh_k', 1 - 0.18 * min(abs(t) / 0.7, 1))
        J = dict(C=C, u=u, E=E, B=B, top=top, Y=Y, H=Hp, Cc=Cc, tg=tg, sp=sp, sw=sw)
        J['SL'], J['SR'] = add(Y, sp, -sw), add(Y, sp, sw)
        tgh = norm(sub(Hp, Cc))
        sph = (tgh[1], -tgh[0])
        J['tgh'], J['sph'] = tgh, sph
        J['HL'], J['HR'] = add(Hp, sph, -0.035 * D), add(Hp, sph, 0.035 * D)
        tg2 = norm(sub(Hp, B))
        J['tg2'], J['sp2'], J['Lbh'] = tg2, (tg2[1], -tg2[0]), dist(B, Hp)
        for side in 'LR':
            a = pose.get('arm' + side, {})
            S = J['S' + side]
            if 'hand' in a:
                Ej, W = ik(S, a['hand'], self.uarm, self.farm, a.get('bend', 1))
            else:
                Ej = add(S, dirv(a.get('a1', 0)), self.uarm * a.get('upper', 1))
                W = add(Ej, dirv(a.get('a2', a.get('a1', 0))), self.farm * a.get('fore', 1))
            J['E' + side], J['W' + side] = Ej, W
            l = pose.get('leg' + side, {})
            Hs = J['H' + side]
            if 'foot' in l:
                K, F = ik(Hs, l['foot'], self.thigh, self.shin, l.get('bend', 1))
            else:
                K = add(Hs, dirv(l.get('a1', 0)), self.thigh)
                F = add(K, dirv(l.get('a2', l.get('a1', 0))), self.shin)
            J['K' + side], J['F' + side] = K, F
        return J

    def local(self, J, x, t):
        return add(add(J['B'], J['sp2'], x * self.D), J['tg2'], t * J['Lbh'])

    def tmat(self, J):
        sp, tg, B = J['sp2'], J['tg2'], J['B']
        return f'matrix({sp[0]:.4f},{sp[1]:.4f},{tg[0]:.4f},{tg[1]:.4f},{B[0]:.2f},{B[1]:.2f})'

    def limb(self, p0, p1, p2, col):
        return capsule(p0, self.r0, p1, self.r1, col) + capsule(p1, self.r1, p2, self.r2, col)

    def leg_stripe(self, p0, p1, p2):
        if not self.stripe:
            return ''
        w = self.r1 * 0.42
        return (f'<polyline points="{pstr([p0, p1, p2])}" stroke="{self.stripe}" stroke-width="{f(w)}" fill="none" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')

    def hand_svg(self, W, h, far):
        kind = h.get('kind', 'mitten')
        if kind == 'none':
            return '', ''
        col = shade(self.hand, 0.06) if far else self.hand
        edge = self.hand_edge
        a = h['ang']
        u = dirv(a)
        p = (u[1], -u[0])
        Lm, Wm = self.mit_l, self.mit_w
        th = h.get('thumb', 1)
        if kind == 'flat':
            Wm *= 0.8
        b = add(W, u, Wm / 2 - 0.02 * self.D)
        e = add(W, u, Lm - Wm / 2 - 0.02 * self.D)
        o = []
        ew = max(0.016 * self.D, 3)
        if edge:
            o.append(pill(b, e, Wm + ew, edge))
        o.append(pill(b, e, Wm, col))
        cid = uid('mc')
        o.append(f'<clipPath id="{cid}"><polygon points="{pstr(capsule_pts(b, Wm/2, e, Wm/2))}"/></clipPath>')
        cxm = (b[0] + e[0]) / 2
        o.append(f'<rect clip-path="url(#{cid})" x="{f(cxm + Wm*0.22)}" y="{f(min(b[1],e[1])-Wm)}" width="{f(Lm+Wm)}" height="{f(Lm+2*Wm)}" fill="{shade(col,0.07)}"/>')
        thumb = ''
        if th:
            ta = h.get('thumb_ang', a + th * 55)
            tb = add(add(W, u, 0.06 * self.D), p, th * Wm * 0.38)
            te = add(tb, dirv(ta), 0.075 * self.D)
            tw = 0.058 * self.D
            if edge:
                thumb += pill(tb, te, tw + ew, edge)
            thumb += pill(tb, te, tw, col)
        return '\n'.join(o), thumb

    def shoe_svg(self, F, ft, far=False):
        d = ft.get('dir', 1)
        tilt = ft.get('tilt', 0)
        L = self.shoe_l
        hg = L * 0.34
        s = self.ankle
        o = []
        if self.shoe == 'oxford':
            path = (f'M{f(-0.24*L)},{f(s)} L{f(0.66*L)},{f(s)} Q{f(0.78*L)},{f(s)} {f(0.78*L)},{f(s-hg*0.45)} '
                    f'Q{f(0.76*L)},{f(s-hg*0.9)} {f(0.44*L)},{f(s-hg*0.92)} L{f(0.1*L)},{f(s-hg*1.08)} '
                    f'Q{f(-0.24*L)},{f(s-hg*1.12)} {f(-0.24*L)},{f(s-hg*0.5)} Z')
            o.append(f'<path d="{path}" fill="{PATENT}"/>')
            o.append(f'<ellipse cx="{f(0.54*L)}" cy="{f(s-hg*0.66)}" rx="{f(L*0.12)}" ry="{f(hg*0.13)}" fill="{IVORY}" opacity="0.85"/>')
        else:
            cid = uid('sp')
            path = (f'M{f(-0.22*L)},{f(s)} L{f(0.6*L)},{f(s)} Q{f(0.76*L)},{f(s-hg*0.05)} {f(0.86*L)},{f(s-hg*0.3)} '
                    f'Q{f(0.62*L)},{f(s-hg*0.86)} {f(0.32*L)},{f(s-hg*0.95)} L{f(0.08*L)},{f(s-hg*1.08)} '
                    f'Q{f(-0.22*L)},{f(s-hg*1.1)} {f(-0.22*L)},{f(s-hg*0.5)} Z')
            base = IVORY if not far else shade(IVORY, 0.1)
            o.append(f'<clipPath id="{cid}"><path d="{path}"/></clipPath>')
            o.append(f'<path d="{path}" fill="{base}"/>')
            o.append(f'<path clip-path="url(#{cid})" d="M{f(0.48*L)},{f(s+5)} Q{f(0.44*L)},{f(s-hg*0.6)} {f(0.56*L)},{f(s-hg*1.3)} L{f(L)},{f(s-hg*1.3)} L{f(L)},{f(s+5)} Z" fill="#7A4A32"/>')
            o.append(f'<path clip-path="url(#{cid})" d="M{f(-0.3*L)},{f(s+5)} L{f(-0.3*L)},{f(s-hg*1.3)} L{f(-0.04*L)},{f(s-hg*1.3)} Q{f(-0.1*L)},{f(s-hg*0.5)} {f(0.0*L)},{f(s+5)} Z" fill="#7A4A32"/>')
        tr = f'translate({f(F[0])},{f(F[1])}) rotate({f(tilt*d)}) scale({d},1)'
        return f'<g transform="{tr}">' + ''.join(o) + '</g>'

    def neck_svg(self, J):
        B, top, E, u = J['B'], J['top'], J['E'], J['u']
        w = self.neck_w
        n = (-u[1], u[0])
        b0 = add(B, u, -0.03 * self.D)
        quad = [add(b0, n, -w / 2), add(top, n, -w / 2), add(top, n, w / 2), add(b0, n, w / 2)]
        sh = [add(b0, n, w * 0.18), add(top, n, w * 0.18), add(top, n, w / 2), add(b0, n, w / 2)]
        cb = add(E, u, -0.055 * self.D)
        chin = [add(cb, n, -w / 2), add(top, n, -w / 2), add(top, n, w / 2), add(cb, n, w / 2)]
        d = shade(self.skin, 0.12)
        return (f'<polygon points="{pstr(quad)}" fill="{self.skin}"/>'
                f'<polygon points="{pstr(sh)}" fill="{mix(self.skin, d, 0.6)}"/>'
                f'<polygon points="{pstr(chin)}" fill="{d}"/>')

    def torso_svg(self, J, face, pose):
        D = self.D
        t = face.get('turn', 0)
        a = min(abs(t) / 0.7, 1)
        s = 1 if t >= 0 else -1
        xk = 1 - 0.14 * a
        xs = 0.07 * t
        Lbh = J['Lbh']
        yk = self.yoke * D / Lbh
        o = []
        P = lambda pts: pstr([(x * D, y * Lbh) for x, y in pts])
        lw = f'stroke="{INK}" stroke-width="{f(max(0.011*D, 2))}" stroke-linejoin="round"'
        if self.kind == 'mess':
            # black trouser top (hips) under a SHORT ivory mess jacket cut at the waist
            hip = [(0.17, 0.50), (0.15, 0.85), (0.11, 1.0), (-0.11, 1.0), (-0.15, 0.85), (-0.17, 0.50)]
            o.append(f'<polygon points="{P([(x*xk, y) for x, y in hip])}" fill="{TROUSER}"/>')
            # cummerbund + shirt front show between the open fronts
            o.append(f'<polygon points="{P([(xs-0.11, 0.0), (xs+0.11, 0.0), (xs+0.115, 0.64), (xs-0.115, 0.64)])}" fill="{SHIRT_W}"/>')
            o.append(f'<polygon points="{P([(xs-0.12, 0.50), (xs+0.12, 0.50), (xs+0.125, 0.64), (xs-0.125, 0.64)])}" fill="{LAPEL}"/>')
            for yy in (0.545, 0.595):
                o.append(f'<line x1="{f((xs-0.12)*D)}" y1="{f(yy*Lbh)}" x2="{f((xs+0.12)*D)}" y2="{f(yy*Lbh)}" stroke="{SATIN}" stroke-width="{f(0.012*D)}"/>')
            for ty in (0.20, 0.31, 0.42):
                o.append(f'<circle cx="{f(xs*D)}" cy="{f(ty*Lbh)}" r="{f(0.014*D)}" fill="{INK}"/>')
            prof = [(0, 0.10), (yk * 0.4, 0.22), (yk, 0.285), (yk + 0.08, 0.28), (0.30, 0.245), (0.50, 0.205), (0.60, 0.195)]
            for sg in (-1, 1):
                side = [(sg * interp(prof, tt) * xk, tt) for tt in [i / 30 * 0.60 for i in range(31)]]
                front = [(xs + sg * 0.17, 0.66), (xs + sg * 0.115, 0.50), (xs + sg * 0.09, 0.0)]
                panel = side + front
                fill = JACKET if (sg < 0) else mix(JACKET, JACKET_D, 0.55)
                o.append(f'<polygon points="{P(panel)}" fill="{fill}"/>')
                # black shawl lapel: rolls from the neck down to the waist button
                lap = [(xs + sg * 0.09, 0.0), (xs + sg * 0.205 * xk, yk * 0.75), (xs + sg * 0.20 * xk, 0.16),
                       (xs + sg * 0.15, 0.38), (xs + sg * 0.118, 0.49), (xs + sg * 0.112, 0.40), (xs + sg * 0.10, 0.12)]
                o.append(f'<polygon points="{P(lap)}" fill="{LAPEL}"/>')
                o.append(f'<polygon points="{P(panel)}" fill="none" {lw}/>')
                for ty, bx in ((0.25, 0.20), (0.36, 0.185), (0.47, 0.165)):
                    o.append(f'<circle cx="{f((xs + sg*bx*(xk if sg*s < 0 else 1))*D)}" cy="{f(ty*Lbh)}" r="{f(0.022*D)}" fill="{GOLD}" {lw}/>')
        elif self.kind == 'hasty':
            prof = [(0, 0.10), (yk * 0.4, 0.19), (yk, 0.235), (yk + 0.07, 0.225), (0.25, 0.205), (0.55, 0.20), (0.85, 0.21), (1.0, 0.215)]
            pts = [(interp(prof, tt) * xk, tt) for tt in [i / 40 for i in range(41)]]
            right = pts
            left = [(-x, y) for x, y in pts]
            bottom = [(xs + 0.07, 1.12), (xs, 1.03), (xs - 0.07, 1.12)]
            poly = right + bottom + left[::-1]
            o.append(f'<polygon points="{P(poly)}" fill="{self.torso}"/>')
            shp = [(xs + 0.0, 0.38)] + [(x, y) for x, y in right if y >= 0.38] + [(xs + 0.07, 1.12), (xs, 1.03)]
            o.append(f'<polygon points="{P(shp)}" fill="{ENJI_D}" opacity="0.6"/>')
            vw = 0.10 * (1 - 0.1 * a)
            o.append(f'<polygon points="{P([(xs - vw, 0.0), (xs + vw, 0.0), (xs, 0.40)])}" fill="{SHIRT}"/>')
            o.append(f'<polygon points="{P([(xs - 0.022, 0.03), (xs + 0.022, 0.03), (xs + 0.03, 0.30), (xs, 0.36), (xs - 0.03, 0.30)])}" fill="{TIE}"/>')
            for ty in (0.47, 0.61, 0.75, 0.89):
                o.append(f'<circle cx="{f(xs*D)}" cy="{f(ty*Lbh)}" r="{f(0.022*D)}" fill="{GOLD}"/>')
            for sg in (-1, 1):
                wx = xs + sg * 0.12 * xk
                o.append(f'<line x1="{f((wx-0.045)*D)}" y1="{f(0.70*Lbh)}" x2="{f((wx+0.045)*D)}" y2="{f(0.70*Lbh)}" stroke="{ENJI_D}" stroke-width="{f(0.022*D)}" stroke-linecap="round"/>')
        elif self.kind == 'clerk':
            prof = [(0, 0.10), (yk, 0.26), (0.5, 0.22), (1.0, 0.2)]
            pts = [(interp(prof, tt), tt) for tt in [i / 30 for i in range(31)]]
            poly = pts + [(-x, y) for x, y in pts[::-1]]
            o.append(f'<polygon points="{P(poly)}" fill="{self.torso}"/>')
            o.append(f'<polygon points="{P([(-0.09, 0), (0.09, 0), (0, 0.3)])}" fill="{IVORY}"/>')
        return f'<g transform="{self.tmat(J)}">' + ''.join(o) + '</g>'

    def anchor_svg(self, J, face, pose):
        D = self.D
        k = lambda v: v * D
        yk = self.yoke * D
        o = []
        if self.kind == 'mess':
            wing = [(-k(0.13), yk * 0.45), (-k(0.085), -k(0.035)), (k(0.085), -k(0.035)), (k(0.13), yk * 0.45),
                    (k(0.035), k(0.09)), (0, k(0.10)), (-k(0.035), k(0.09))]
            o.append(f'<polygon points="{pstr(wing)}" fill="{SHIRT_W}"/>')
            by = k(0.035)
            bw, bh = k(0.11), k(0.048)
            o.append(f'<polygon points="{f(0)},{f(by)} {f(-bw)},{f(by-bh)} {f(-bw)},{f(by+bh)}" fill="{LAPEL}"/>')
            o.append(f'<polygon points="{f(0)},{f(by)} {f(bw)},{f(by-bh)} {f(bw)},{f(by+bh)}" fill="{LAPEL}"/>')
            o.append(f'<rect x="{f(-k(0.028))}" y="{f(by-k(0.03))}" width="{f(k(0.056))}" height="{f(k(0.06))}" rx="{f(k(0.012))}" fill="{LAPEL}"/>')
        elif self.kind == 'hasty':
            for s in (-1, 1):
                pt = [(s * k(0.02), -k(0.03)), (s * k(0.14), -k(0.01)), (s * k(0.13), k(0.07)), (s * k(0.03), k(0.10))]
                o.append(f'<polygon points="{pstr(pt)}" fill="{SHIRT if s < 0 else SHIRT_D}"/>')
            o.append(f'<polygon points="{pstr([(-k(0.032), -k(0.01)), (k(0.032), -k(0.01)), (k(0.024), k(0.05)), (-k(0.024), k(0.05))])}" fill="{TIE}"/>')
        elif self.kind == 'clerk':
            for s in (-1, 1):
                pt = [(s * k(0.02), -k(0.02)), (s * k(0.15), 0), (s * k(0.04), k(0.12))]
                o.append(f'<polygon points="{pstr(pt)}" fill="{IVORY}"/>')
        sp, tg, B = J['sp'], J['tg'], J['B']
        mat = f'matrix({sp[0]:.4f},{sp[1]:.4f},{tg[0]:.4f},{tg[1]:.4f},{B[0]:.2f},{B[1]:.2f})'
        return f'<g transform="{mat}">' + ''.join(o) + '</g>'

    def watch_svg(self, J, pose):
        w = pose.get('watch')
        if not w or self.kind != 'hasty':
            return '', ''
        D = self.D
        btn = self.local(J, w.get('btn_x', 0.0), 0.61)
        if 'hand' in w:
            side = w['hand']
            W = J['W' + side]
            u = dirv(w.get('ang', ang_of(J['E' + side], W)))
            pos = add(W, u, self.mit_l * 0.55)
        else:
            pos = self.local(J, w.get('pocket_x', 0.13), 0.70)
        if 'pos' in w:
            pos = w['pos']
        sag = w.get('sag', 0.12) * D
        c = (lerp(btn, pos, 0.5)[0] + w.get('cx', 0) * D, max(btn[1], pos[1]) + sag)
        chain = (f'<path d="M{f(btn[0])},{f(btn[1])} Q{f(c[0])},{f(c[1])} {f(pos[0])},{f(pos[1])}" stroke="{GOLD}" '
                 f'stroke-width="{f(0.03*D)}" fill="none" stroke-linecap="round" stroke-dasharray="0.1 {f(0.042*D)}"/>'
                 f'<path d="M{f(btn[0])},{f(btn[1])} Q{f(c[0])},{f(c[1])} {f(pos[0])},{f(pos[1])}" stroke="{GOLD}" '
                 f'stroke-width="{f(0.014*D)}" fill="none" stroke-linecap="round"/>')
        o = []
        if w.get('watch', True):
            r = 0.075 * D
            o.append(f'<circle cx="{f(pos[0])}" cy="{f(pos[1])}" r="{f(r)}" fill="{GOLD}"/>')
            o.append(f'<circle cx="{f(pos[0])}" cy="{f(pos[1] - r - 0.02*D)}" r="{f(0.022*D)}" fill="{GOLD}"/>')
            o.append(f'<circle cx="{f(pos[0]-0.006*D)}" cy="{f(pos[1]+0.004*D)}" r="{f(r*0.72)}" fill="{IVORY}"/>')
            o.append(f'<line x1="{f(pos[0])}" y1="{f(pos[1])}" x2="{f(pos[0])}" y2="{f(pos[1]-r*0.5)}" stroke="{INK}" stroke-width="{f(0.014*D)}" stroke-linecap="round"/>')
            o.append(f'<line x1="{f(pos[0])}" y1="{f(pos[1])}" x2="{f(pos[0]+r*0.38)}" y2="{f(pos[1]+r*0.12)}" stroke="{INK}" stroke-width="{f(0.014*D)}" stroke-linecap="round"/>')
        return chain, '\n'.join(o)

    def layers(self, J, face, pose):
        L = {k: '' for k in ('shadow', 'legF', 'armF', 'torso', 'neck', 'anchor', 'legN',
                             'armN', 'prop', 'thumbs', 'front', 'wchain')}
        far_side = pose.get('far', 'R' if face.get('turn', 0) >= 0 else 'L')
        sh = pose.get('shadow')
        if sh:
            x0, x1, y, op = sh[:4]
            col = sh[4] if len(sh) > 4 else EMERALD_D
            L['shadow'] = (f'<ellipse cx="{f((x0+x1)/2)}" cy="{f(y)}" rx="{f((x1-x0)/2)}" ry="{f(0.06*self.D)}" '
                           f'fill="{col}" opacity="{op}"/>')
        tray = pose.get('tray')
        for side in 'LR':
            arm = pose.get('arm' + side, {})
            far = arm.get('far', side == far_side)
            col = self.arm_far if far else self.arm_col
            h = dict(pose.get('hand' + side, {}))
            h.setdefault('ang', ang_of(J['E' + side], J['W' + side]))
            hs, th = self.hand_svg(J['W' + side], h, far)
            seg = self.limb(J['S' + side], J['E' + side], J['W' + side], col)
            key = 'armF' if far else 'armN'
            L[key] += seg + hs
            if tray and tray.get('hand') == side or not far:
                L['thumbs'] += th
            else:
                L[key] += th
            if tray and tray.get('hand') == side:
                u = dirv(h['ang'])
                Wm = self.mit_w * (0.8 if h.get('kind') == 'flat' else 1)
                if tray.get('at') == 'tip':
                    tip = add(J['W' + side], u, self.mit_l - 0.02 * self.D)
                    cx, bottom = tip[0] + tray.get('dx', 0), tip[1] + 3
                else:
                    mid = add(J['W' + side], u, self.mit_l * tray.get('at', 0.55))
                    cx = mid[0] + tray.get('dx', 0)
                    bottom = mid[1] - Wm / 2 + 2
                w = tray.get('w', 0.55) * self.D
                if not tray.get('hidden'):
                    L['prop'] += cloche(cx, bottom, w, steam=tray.get('steam', True))
                J['tray'] = (cx, bottom, w)
            leg = pose.get('leg' + side, {})
            lfar = leg.get('far', side == far_side)
            lcol = self.leg_far if lfar else self.leg_col
            sv = self.limb(J['H' + side], J['K' + side], J['F' + side], lcol)
            sv += self.leg_stripe(J['H' + side], J['K' + side], J['F' + side])
            sv += self.shoe_svg(J['F' + side], pose.get('foot' + side, {}), far=lfar)
            L['legF' if lfar else 'legN'] += sv
        L['torso'] = self.torso_svg(J, face, pose)
        L['neck'] = self.neck_svg(J)
        L['anchor'] = self.anchor_svg(J, face, pose)
        ch, wt = self.watch_svg(J, pose)
        L['wchain'] = ch
        L['prop'] = wt + L['prop']
        return L


def shoe_drop(body, tilt, d):
    L = body.shoe_l
    hg = L * 0.34
    sa = body.ankle
    best = -1e9
    for x, y in ((-0.24 * L, sa), (0.66 * L, sa), (0.78 * L, sa - hg * 0.45), (0.86 * L, sa - hg * 0.3)):
        x *= d
        xr, yr = rot(x, y, tilt * d)
        best = max(best, yr)
    return best


class Char:
    def __init__(self, head, body):
        self.head, self.body = head, body

    def joints(self, cx, cy, face, pose):
        return self.body.joints((cx, cy), face, pose)

    def place(self, cx, floor, face, pose, plant='L', foot_dx=0.0, bend=6, lift=0.0):
        b = self.body
        J = b.joints((cx, 0), face, dict(pose, legL={}, legR={}))
        Hs = J['H' + plant]
        chord = math.sqrt(b.thigh ** 2 + b.shin ** 2 - 2 * b.thigh * b.shin * math.cos(math.radians(180 - bend)))
        fx = Hs[0] + foot_dx * b.D
        reach = math.sqrt(max(chord ** 2 - (fx - Hs[0]) ** 2, 0))
        cy = floor - lift - b.ankle - reach - Hs[1]
        return cy, (fx, floor - lift - b.ankle)

    def glasses_chain(self, cx, cy, face, J):
        P = self.head.P
        if not P.get('glasses'):
            return ''
        D = self.head.D
        t = face.get('turn', 0)
        o = []
        for s in (-1, 1):
            if t < -0.2 and s < 0 or t > 0.2 and s > 0:
                continue
            ex, ey = self.head.ear_point(s)
            p0 = (cx + ex, cy + ey)
            p1 = add(J['B'], J['sp'], s * 0.10 * D)
            p1 = add(p1, J['tg'], 0.02 * D)
            c = (p0[0] + s * 0.06 * D, (p0[1] + p1[1]) / 2 + 0.12 * D)
            o.append(f'<path d="M{f(p0[0])},{f(p0[1])} Q{f(c[0])},{f(c[1])} {f(p1[0])},{f(p1[1])}" stroke="{GOLD}" '
                     f'stroke-width="{f(max(0.012*D, 2))}" fill="none" stroke-linecap="round"/>')
        return ''.join(o)

    def draw(self, cx, cy, face, pose, marks='', ink=True):
        J = self.body.joints((cx, cy), face, pose)
        L = self.body.layers(J, face, pose)
        self.J = J
        head = self.head.draw(cx, cy, face)
        r = max(2.0, 0.015 * self.head.D)
        O = (lambda s: inked(s, r)) if ink else (lambda s: s)
        gch = self.glasses_chain(cx, cy, face, J)
        return '\n'.join([L['shadow'], O(L['armF']), O(L['legF']), O(L['legN']), O(L['torso']), O(L['neck']),
                          O(L['anchor']), gch, O(head), L['wchain'], O(L['armN']), O(L['prop']), O(L['thumbs']),
                          L['front'], marks])


# =====================================================================
# CAST
# =====================================================================
LEVEL_P = dict(
    name='Mr. Level', skin=SKIN_L, shad=SHAD_L,
    hair='flattop', hair_col=HAIR_L, hair_top=HAIR_L_TOP, hair_shad=HAIR_L_D, hair_rise=0.085, deck_w=0.37, hairline=-0.445,
    # TALL rounded-rectangle eyes (portrait, not a goggle strip): flat level lid on top,
    # thin lower lid line hugging the round bottom, no heavy bar
    eye=dict(shape='capsule', W=0.38, H=0.52, rt=0.13, rb=0.17, gap=0.09, y=-0.025, lid=0.20, low=0.0,
             band=0.035, ih=0.39, iw_ratio=0.86, cut=0.04, pupil=0.15, ring_w=0.02, over=0.03,
             hl='bubble', hl_w=0.135, hl_h=0.088, hl2=0.024, lash=0.055, low_th=0.016, lash_style='square',
             lower='contour', low_span=0.82,
             crease=True, crow=True, lowcrease=True, lidtone=mix(SKIN_L, SHAD_L, 0.5)),
    iris=LV_IRIS,
    brow=dict(shape='pill', W=0.24, H=0.07, gap=0.025, out=-0.015, ref='fp'),
    nose='long', mouth_y=0.36, lower='level', ear=1.0)

HASTY_P = dict(
    name='Hasty', skin=SKIN_H, shad=SHAD_H,
    hair='part', hair_col=HAIR_H, hair_shad=HAIR_H_D, hair_light=HAIR_H_L, hair_grey=GREY_H,
    hair_rise=0.07, top_ext=0.25, curl_base=(0.10, -0.535), curl_r=(0.125, 0.085), curl_w=(0.12, 0.022),
    curl_a0=58, curl_a1=-165,
    eye=dict(shape='round', W=0.43, H=0.53, gap=0.07, y=-0.035, lid=0.12, tilt=12, arc=0.012, low=0.0,
             band=0.04, ih=0.40, iw_ratio=0.87, cut=0.035, pupil=0.15, ring_w=0.018, over=0.02,
             hl='dot_tear', hl_r=0.056, hl2=0.022, tear=1.0, lash=0.05, low_th=0.02, lash_style='taper', lower='full',
             bag=True, crow=True, lidtone=mix(SKIN_H, SHAD_H, 0.55)),
    iris=HS_IRIS,
    brow=dict(shape='comma', W=0.26, H=0.05, gap=0.05, tilt=-14, out=0.01, ref='lash', col=BROW_H),
    nose='pointy', mouth_y=0.375, lower='laugh', ear=0.92,
    glasses=dict(y=0.24, w=0.22, h=0.08, xk=0.9))

CLERK_P = dict(
    name='clerk', skin=SKIN_C, shad=SHAD_C,
    hair='bun', hair_col=HAIR_C, hair_shad=shade(HAIR_C, 0.15), hair_rise=0.22,
    eye=dict(shape='round', W=0.31, H=0.42, gap=0.10, y=-0.03, lid=0.30, low=0.0, band=0.03,
             ih=0.31, iw_ratio=0.88, cut=0.03, pupil=0.12, hl='dot', hl_r=0.042, hl2=0.018, lash=0.045, low_th=0.016,
             lash_style='square', lower='flat', lidtone=mix(SKIN_C, SHAD_C, 0.6)),
    iris=CL_IRIS,
    brow=dict(shape='pill', W=0.18, H=0.045, gap=0.03, ref='fp'),
    nose='button', mouth_y=0.31, lower=None, ear=0.9)


def level_char(D):
    hd = Head(D, LEVEL_P)
    bd = Body(D, neck=0.20, yoke=0.06, spine=1.05, leg=1.65, uarm=0.71, farm=0.74, sh=0.27,
              torso=JACKET, arm_col=JACKET, leg_col=TROUSER, skin=SKIN_L, hand=GLOVE, hand_edge=INK,
              kind='mess', shoe='oxford', stripe=SATIN)
    return Char(hd, bd)


def hasty_char(D):
    hd = Head(D, HASTY_P)
    bd = Body(D, neck=0.08, yoke=0.05, spine=1.0, leg=1.56, uarm=0.66, farm=0.69, sh=0.25,
              torso=ENJI, arm_col=SHIRT, leg_col=ENJI, skin=SKIN_H, hand=SKIN_H, kind='hasty', shoe='spectator')
    return Char(hd, bd)


def clerk_char(D):
    hd = Head(D, CLERK_P)
    bd = Body(D, neck=0.12, yoke=0.06, spine=1.0, leg=1.5, uarm=0.68, farm=0.70, sh=0.27,
              torso=CARDI, arm_col=CARDI, leg_col=CARDI, skin=SKIN_C, hand=SKIN_C, kind='clerk')
    return Char(hd, bd)


# ---------------------------------------------------------------- expressions (Mr. Level)
def _float_dy(extra):
    E, B = LEVEL_P['eye'], LEVEL_P['brow']
    crest = -0.5 - LEVEL_P['hair_rise']
    base = E['y'] - E['H'] / 2 - B['gap'] - B['H'] / 2
    target = crest - extra - B['H'] / 2
    return target - base, crest


def L_NEUTRAL(turn=0.0):
    return dict(turn=turn, eyes=dict(gaze=(0.0, 0.0)), browL={}, browR={}, mouth=dict(type='flat', w=0.17))


def L_SURPRISED(turn=0.0):
    dy, crest = _float_dy(0.10)
    return dict(turn=turn, eyes=dict(H=0.56, lid=0.03, low=0.0, ik=0.55, icy=0.0, lash=0.045, gaze=(0, 0),
                                       rt=0.19, rb=0.19),
                browL=dict(dy=dy, trail=crest + 0.01), browR=dict(dy=dy, trail=crest + 0.01),
                mouth=dict(type='o', w=0.085, h=0.10, dy=0.01))


def L_ANGRY(turn=0.0):
    return dict(turn=turn, eyes=dict(lid=0.40, low=0.10, gaze=(0.0, 0.2)),
                browL=dict(dy=0.035, tilt=24), browR=dict(dy=0.035, tilt=24), crease='anger',
                mouth=dict(type='frown', w=0.17, amp=0.022))


def L_SMUG(turn=0.0, side=1):
    d = dict(turn=turn, eyes=dict(lid=0.33, low=0.12, gaze=(0.85 * side, 0.5)),
             mouth=dict(type='curl', w=0.18, side='R' if side > 0 else 'L', curl=0.045, dx=0.02 * side))
    dy, crest = _float_dy(0.06)
    d['browR' if side > 0 else 'browL'] = dict(dy=dy, tilt=-6, trail=crest + 0.005, trail_n=2)
    d['browL' if side > 0 else 'browR'] = dict(dy=0.01, tilt=4)
    return d


def L_PANIC(turn=0.0, slide=0.9):
    return dict(turn=turn, eyes=dict(H=0.55, lid=0.05, low=0.0, ik=0.52, icy=0.0, gaze=(0, 0), slide=slide, wobble=0.022,
                                     rt=0.19, rb=0.19),
                browL=dict(dy=-0.06, tilt=-18, ghosts=[(-0.02, 0, -4), (0.02, 0, 4)]),
                browR=dict(dy=-0.06, tilt=-18, ghosts=[(-0.02, 0, 4), (0.02, 0, -4)]),
                mouth=dict(type='zig', w=0.16, amp=0.016, n=4), sweat=[(0.47, -0.30), (-0.47, -0.22, 0.8)])


def L_SIDEEYE(turn=0.0, side=-1):
    d = dict(turn=turn, eyes=dict(lid=0.42, low=0.08, gaze=(1.0 * side, 0.1), iwk=0.72, hl_off=True),
             mouth=dict(type='flat', w=0.15, dx=0.03 * side, tilt=0.01 * side))
    d['browL'] = dict(dy=0.02, tilt=0)
    d['browR'] = dict(dy=-0.09, tilt=-3)
    if side > 0:
        d['browL'], d['browR'] = d['browR'], d['browL']
    return d


# =====================================================================
# DIAGNOSTICS
# =====================================================================
def eye_report(ch, label, H_stand=None):
    hd = ch.head
    st = hd.stats.get('eyes', {})
    parts = []
    for s in ('L', 'R'):
        e = st.get(s)
        if not e:
            continue
        parts.append(f"{s}: fp {e['w']:.3f}x{e['h']:.3f} top{e['top_below_skull']:.3f} open{e['open']:.3f} "
                     f"iris{e['ih']:.3f}({e['ih_frac']*100:.0f}%) lash{e['lash']:.3f}")
    if 'L' in st and 'R' in st:
        a, b = st['L'], st['R']
        x0 = min(a['cx'] - a['w'] / 2, b['cx'] - b['w'] / 2)
        x1 = max(a['cx'] + a['w'] / 2, b['cx'] + b['w'] / 2)
        gap = (b['cx'] - b['w'] / 2) - (a['cx'] + a['w'] / 2)
        parts.append(f'span {x1-x0:.3f} gap {gap:.3f} outer [{x0:+.3f},{x1:+.3f}]')
    extra = ''
    if H_stand:
        extra = f' | head {hd.D/H_stand*100:.1f}% of H, rest eye {hd.P["eye"]["H"]*hd.D/H_stand*100:.1f}% of H'
    print(f'  [{label}] D={hd.D:.0f} ' + ' | '.join(parts) + extra)


def svg_doc(w, h, body):
    defs = ''.join(v[1] for v in _INK_DEFS.values())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'<defs><filter id="blk" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" '
            f'values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>{defs}</defs>\n'
            f'{body}\n</svg>\n')


def lamp(cx, cy, rx, ry, op, col=IVORY):
    gid = uid('lp')
    return (f'<radialGradient id="{gid}"><stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
            f'<stop offset="0.5" stop-color="{col}" stop-opacity="{op*0.78}"/>'
            f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
            f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="url(#{gid})"/>')


def floor_tiles(y0, y1, vp=(540, 700), tile=170, off=0, parity=0, light=None, dark=FLOOR_D, fade=(0.0, 0.3), width=1080):
    out = [f'<rect x="0" y="{f(y0)}" width="{width}" height="{f(y1-y0)}" fill="{dark}"/>']
    vx, vy = vp
    rows = []
    y = y0
    h = (y1 - y0) * 0.11
    while y < y1:
        rows.append((y, min(y + h, y1)))
        y += h
        h *= 1.3
    cols = [c + off for c in range(-2400 - tile * 4, 3600, tile)]
    tl = light or SAGE

    def X(x, yy):
        return vx + (x - vx) * (yy - vy) / (y1 - vy)
    for ri, (ya, yb) in enumerate(rows):
        for ci in range(len(cols) - 1):
            if (ri + ci + parity) % 2:
                continue
            xa0, xa1 = X(cols[ci], ya), X(cols[ci + 1], ya)
            xb0, xb1 = X(cols[ci], yb), X(cols[ci + 1], yb)
            out.append(f'<polygon points="{f(xa0)},{f(ya)} {f(xa1)},{f(ya)} {f(xb1)},{f(yb)} {f(xb0)},{f(yb)}" fill="{tl}"/>')
    gid = uid('fl')
    out.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{FLOOR_D}" stop-opacity="{fade[0]}"/>'
               f'<stop offset="1" stop-color="{FLOOR_D}" stop-opacity="{fade[1]}"/></linearGradient>')
    out.append(f'<rect x="0" y="{f(y0)}" width="{width}" height="{f(y1-y0)}" fill="url(#{gid})"/>')
    return '\n'.join(out)


def arch(cx, top, w, bottom, stroke=6):
    r = w / 2
    return (f'<path d="M{f(cx-r)},{f(bottom)} L{f(cx-r)},{f(top+r)} A{f(r)},{f(r)} 0 0 1 {f(cx+r)},{f(top+r)} L{f(cx+r)},{f(bottom)}" '
            f'stroke="{GOLD}" stroke-width="{stroke}" fill="none"/>')


def dotted_arc(p0, c, p1, col=IVORY, w=7, op=0.75, gap=16):
    return (f'<path d="M{f(p0[0])},{f(p0[1])} Q{f(c[0])},{f(c[1])} {f(p1[0])},{f(p1[1])}" stroke="{col}" stroke-width="{w}" '
            f'stroke-linecap="round" stroke-dasharray="0.1 {gap}" fill="none" opacity="{op}"/>')


# =====================================================================
# FACES SHEET  1080 x 1080  (hero head, 3 x 2)
# =====================================================================
def build_faces():
    W, H = 1080, 1080
    D = 250
    o = [f'<rect width="{W}" height="{H}" fill="{SHEET_BG}"/>']
    exprs = [('neutral', L_NEUTRAL(turn=0.0)),
             ('surprised', L_SURPRISED(turn=0.0)),
             ('angry', L_ANGRY(turn=0.0)),
             ('smug', L_SMUG(turn=0.3, side=1)),
             ('panic', L_PANIC(turn=0.0)),
             ('side-eye', L_SIDEEYE(turn=0.25, side=-1))]
    print('faces:')
    for i, (name, face) in enumerate(exprs):
        col, row = i % 3, i // 3
        cx = 180 + col * 360
        cy = 270 + row * 540
        ch = level_char(D)
        cell = uid('cell')
        o.append(f'<clipPath id="{cell}"><rect x="{col*360+6}" y="{row*540+6}" width="348" height="528" rx="18"/></clipPath>')
        g = [f'<rect x="{col*360+6}" y="{row*540+6}" width="348" height="528" rx="18" fill="{SHEET_CELL}"/>',
             f'<circle cx="{cx}" cy="{cy + 20}" r="165" fill="{SHEET_HALO}"/>']
        pose = dict(neck=0, neck_off=-0.05 * face.get('turn', 0), spine=0, sh_k=1.0,
                    armL=dict(a1=10, a2=4, far=False), armR=dict(a1=-10, a2=-4, far=False),
                    handL=dict(kind='none'), handR=dict(kind='none'), legL=dict(a1=0), legR=dict(a1=0))
        hy = cy + 12
        g.append(ch.draw(cx, hy, face, pose))
        o.append(f'<g clip-path="url(#{cell})">' + '\n'.join(g) + '</g>')
        eye_report(ch, name)
    return svg_doc(W, H, '\n'.join(o))


# =====================================================================
# LINEUP FIGURES  540 x 1080
# =====================================================================
def fit_lineup(make, face, pose, target, plant, cx=270, floor=1010, bend=4, foot_dx=0.0):
    D = 220.0
    for _ in range(40):
        ch = make(D)
        cy, F = ch.place(cx, floor, face, pose, plant=plant, foot_dx=foot_dx, bend=bend)
        top = cy - ch.head.R - ch.head.top_extent(face)
        D *= target / (floor - top)
    ch = make(D)
    cy, F = ch.place(cx, floor, face, pose, plant=plant, foot_dx=foot_dx, bend=bend)
    return ch, D, cy, F


def _calib(name):
    try:
        with open(os.path.join(HERE, 'calib.json')) as fh:
            return json.load(fh).get(name)
    except Exception:
        return None


def _fit_group(fig, name, cx, target, floor=1010, raw=False):
    c = None if raw else _calib(name)
    if not c:
        return fig
    top, bot = c['top'], c['bottom'] + 1
    k = target / (bot - top)
    return f'<g transform="translate({f(cx)},{floor}) scale({k:.5f}) translate({f(-cx)},{-bot})">{fig}</g>'


def build_hero(sil=False, raw=False):
    W, H, floor = 540, 1080, 1010
    face = dict(turn=-0.62, eyes=dict(gaze=(-0.75, 0.1)), browL=dict(dy=0.0), browR=dict(dy=0.0),
                mouth=dict(type='flat', w=0.15))
    pose = dict(neck=-3, neck_off=0.07, spine=0, chest=0, curve=0.0, far='R',
                armL=dict(a1=18, a2=-150, far=False), handL=dict(kind='flat', ang=-160, thumb=-1, thumb_ang=-120),
                armR=dict(a1=10, a2=-70, fore=0.35, far=True), handR=dict(kind='none'),
                tray=dict(hand='L', w=0.55, at='tip', dx=-6, steam=False),
                footL=dict(dir=-1), footR=dict(dir=-1))
    ch, D, cy, F = fit_lineup(level_char, face, pose, 960, 'R', cx=300)
    cx = 300
    pose['legR'] = dict(foot=(F[0] + 0.03 * D, floor - ch.body.ankle), bend=1, far=True)
    pose['legL'] = dict(foot=(F[0] - 0.03 * D, floor - ch.body.ankle), bend=1, far=False)
    pose['footR'] = dict(dir=1, tilt=0)
    pose['footL'] = dict(dir=-1, tilt=0)
    J = ch.joints(cx, cy, face, pose)
    S = J['SL']
    pose['armL'] = dict(hand=(S[0] - 0.50 * D, S[1] + 0.06 * D), bend=1, far=False)
    pose['handL'] = dict(kind='flat', ang=-172, thumb=-1, thumb_ang=-125)
    o = [f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else LINE_BG}"/>']
    if not sil:
        o.append(f'<ellipse cx="{cx-10}" cy="{floor+3}" rx="110" ry="9" fill="#000" opacity="0.12"/>')
    fig = _fit_group(ch.draw(cx, cy, face, pose), 'hero', cx, 960, raw=raw)
    if sil:
        fig = f'<g filter="url(#blk)">{fig}</g>'
    o.append(fig)
    top = cy - ch.head.R - ch.head.top_extent(face)
    Hs = floor - (cy - ch.head.R)
    if not sil:
        print(f'hero: D={D:.1f} soles {floor} hair top {top:.1f} total {floor-top:.1f}')
        eye_report(ch, 'hero', Hs)
    return svg_doc(W, H, '\n'.join(o))


def H_NEUTRAL(turn=-0.55):
    return dict(turn=turn, tilt=-3, red=0.2,
                eyes=dict(gaze=(-0.65, 0.0)),
                browL=dict(tilt=-14), browR=dict(tilt=-14),
                mouth=dict(type='zig', w=0.15, amp=0.014, n=4),
                glasses=dict(dy=0.0))


def build_partner(sil=False, raw=False):
    W, H, floor = 540, 1080, 1010
    face = H_NEUTRAL()
    TILT = 26
    pose = dict(neck=-12, neck_off=0.06, spine=15, chest=13, curve=0.0, far='R',
                armL=dict(a1=-30, a2=-150, far=False), handL=dict(ang=-150, thumb=-1, thumb_ang=150),
                armR=dict(a1=60, a2=-40, far=True), handR=dict(ang=-30, thumb=1),
                footL=dict(dir=-1, tilt=TILT), footR=dict(dir=-1, tilt=TILT - 4))
    cx = 270
    D = 240.0
    for _ in range(40):
        ch = hasty_char(D)
        lift = shoe_drop(ch.body, TILT, -1) - ch.body.ankle
        cy, F = ch.place(cx, floor, face, pose, plant='R', foot_dx=0.02, bend=10, lift=lift)
        top = cy - ch.head.R - ch.head.top_extent(face)
        D *= 900 / (floor - top)
    ch = hasty_char(D)
    lift = shoe_drop(ch.body, TILT, -1) - ch.body.ankle
    cy, F = ch.place(cx, floor, face, pose, plant='R', foot_dx=0.02, bend=10, lift=lift)
    J = ch.joints(cx, cy, face, pose)
    liftL = shoe_drop(ch.body, TILT, -1) - ch.body.ankle
    pose['legR'] = dict(foot=F, bend=1, far=True)
    pose['legL'] = dict(foot=(J['HL'][0] - 0.20 * D, floor - ch.body.ankle - liftL), bend=1, far=False)
    S = J['SL']
    pose['armL'] = dict(hand=(S[0] - 0.50 * D, S[1] + 0.12 * D), bend=1, far=False)
    pose['handL'] = dict(ang=-150, thumb=1, thumb_ang=-100)
    pose['armR'] = dict(hand=(J['H'][0] + 0.16 * D, J['H'][1] - 0.10 * D), bend=1, far=True)
    pose['handR'] = dict(ang=-120, thumb=0)
    pose['watch'] = dict(hand='L', sag=0.06, cx=0.0)
    o = [f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else LINE_BG}"/>']
    if not sil:
        o.append(f'<ellipse cx="{cx-25}" cy="{floor+3}" rx="105" ry="9" fill="#000" opacity="0.12"/>')
    fig = _fit_group(ch.draw(cx, cy, face, pose), 'partner', cx, 900, raw=raw)
    if sil:
        fig = f'<g filter="url(#blk)">{fig}</g>'
    o.append(fig)
    top = cy - ch.head.R - ch.head.top_extent(face)
    Hs = floor - (cy - ch.head.R)
    if not sil:
        print(f'partner: D={D:.1f} soles {floor} hair top {top:.1f} total {floor-top:.1f}')
        eye_report(ch, 'partner', Hs)
    return svg_doc(W, H, '\n'.join(o))


# =====================================================================
# SCENE  1080 x 1920  'the swap'
# =====================================================================
def clerk_booth(cxa, top, w, ledge, horizon, look, sil=False):
    o = []
    r = w / 2
    x0, x1 = cxa - r, cxa + r
    cid = uid('ar')
    o.append(f'<clipPath id="{cid}"><path d="M{f(x0)},{f(ledge)} L{f(x0)},{f(top+r)} A{f(r)},{f(r)} 0 0 1 {f(x1)},{f(top+r)} L{f(x1)},{f(ledge)} Z"/></clipPath>')
    if not sil:
        o.append(f'<g clip-path="url(#{cid})">')
        o.append(f'<rect x="{f(x0)}" y="{f(top)}" width="{f(w)}" height="{f(ledge-top)}" fill="{EMERALD_D}"/>')
        for i, hx in enumerate(range(int(x0) + 16, int(x1) - 6, 34)):
            o.append(f'<path d="M{hx-13},{f(top+r+26)} L{hx+13},{f(top+r+26)} L{hx+18},{f(ledge-10)} L{hx-18},{f(ledge-10)} Z" '
                     f'fill="{mix(EMERALD_D, EMERALD, 0.5 if i % 2 else 0.25)}"/>')
        o.append(lamp(cxa, ledge - 150, 150, 190, 0.5))
        o.append('</g>')
    Dc = 150
    ch = clerk_char(Dc)
    ccx = cxa + 2
    ccy = ledge - 0.95 * Dc
    lk = ((look[0] - ccx) / Dc, (look[1] - ccy) / Dc)
    face = dict(turn=-0.35, eyes=dict(look=lk, hl_off=False), browL=dict(dy=-0.0, tilt=-6), browR=dict(dy=0.0),
                mouth=dict(type='flat', w=0.15))
    pose = dict(neck=-2, armL=dict(a1=-10, a2=90, upper=0.6, fore=0.6), armR=dict(a1=10, a2=-90, upper=0.6, fore=0.6),
                handL=dict(kind='none'), handR=dict(kind='none'), legL=dict(a1=0), legR=dict(a1=0))
    J = ch.joints(ccx, ccy, face, pose)
    L = ch.body.layers(J, face, pose)
    sc = uid('cs')
    r_ = 0.015 * Dc
    g = [f'<clipPath id="{sc}"><rect x="0" y="0" width="1080" height="{f(ledge+2)}"/></clipPath>'
         f'<g clip-path="url(#{sc})">' + inked(L['torso'], r_) + inked(L['neck'], r_) + inked(L['anchor'], r_)
         + inked(ch.head.draw(ccx, ccy, face), r_) + '</g>']
    if not sil:
        g.append(f'<rect x="{f(x0-20)}" y="{f(ledge)}" width="{f(w+40)}" height="22" rx="5" fill="{IVORY}"/>'
                 f'<rect x="{f(x0-20)}" y="{f(ledge+17)}" width="{f(w+40)}" height="6" fill="{shade(IVORY,0.25)}"/>'
                 f'<rect x="{f(x0+18)}" y="{f(ledge+50)}" width="{f(w-36)}" height="{f(horizon-ledge-94)}" fill="none" '
                 f'stroke="{shade(GOLD,0.15)}" stroke-width="3" opacity="0.55"/>')
        for dx in (-0.32, 0.30):
            g.append(inked(f'<ellipse cx="{f(ccx + dx*Dc)}" cy="{f(ledge - 4)}" rx="{f(0.1*Dc)}" ry="{f(0.06*Dc)}" fill="{SKIN_C}"/>', r_))
    body = '\n'.join(g)
    if sil:
        body = f'<g filter="url(#blk)">{body}</g>'
    o.append(body)
    eye_report(ch, 'clerk')
    return '\n'.join(o)


SC = dict(lcx=335, DL=288, DH=264, hx=782, hy=756, floor=1600, booth_ledge=520)


def build_scene(sil=False):
    W, H = 1080, 1920
    horizon, floor_y, band = 1300, SC['floor'], 1640
    o = [f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else EMERALD}"/>']
    if not sil:
        o.append(f'<rect width="{W}" height="230" fill="{shade(EMERALD, 0.18)}"/>')
        o.append(f'<clipPath id="wall"><rect x="0" y="232" width="{W}" height="{horizon-232}"/></clipPath><g clip-path="url(#wall)">'
                 + lamp(330, 760, 470, 720, 0.50) + lamp(790, 900, 380, 600, 0.50) + '</g>')
        o.append(arch(320, 262, 500, horizon, 7))
        o.append(arch(890, 262, 300, horizon, 7))
        o.append(f'<rect x="0" y="228" width="{W}" height="4" fill="{GOLD}"/>')

    DL, DH = SC['DL'], SC['DH']
    LV = level_char(DL)
    HS = hasty_char(DH)
    lcx = SC['lcx']
    hx, hy = SC['hx'], SC['hy']

    lv_face = L_SMUG(turn=0.55, side=1)
    lv_face['mouth'] = dict(type='curl', w=0.17, side='R', curl=0.045, dx=0.02)
    lv_pose = dict(neck=0, neck_off=-0.07, spine=-1, chest=-1, curve=0.0, far='L',
                   armL=dict(a1=-141, a2=-177, far=True), handL=dict(kind='mitten', ang=180, thumb=1, thumb_ang=140),
                   armR=dict(a1=30, a2=-170, far=False), handR=dict(kind='flat', ang=86, thumb=-1, thumb_ang=-150),
                   tray=dict(hand='L', w=0.55, at='tip', steam=False))
    lcy, plantF = LV.place(lcx, floor_y, lv_face, lv_pose, plant='L', foot_dx=0.03, bend=2)
    J0 = LV.joints(lcx, lcy, lv_face, lv_pose)
    SR = J0['SR']
    palm = (SR[0] + 0.50 * DL, SR[1] - 0.10 * DL)
    lv_pose['armR'] = dict(hand=palm, bend=-1, far=False)
    lv_pose['legL'] = dict(foot=(plantF[0] - 0.035 * DL, plantF[1]), bend=1, far=True)
    lv_pose['legR'] = dict(foot=(plantF[0] + 0.035 * DL, plantF[1]), bend=1, far=False)
    lv_pose['footL'] = dict(dir=-1)
    lv_pose['footR'] = dict(dir=1)
    lv_pose['shadow'] = (plantF[0] - 130, plantF[0] + 140, floor_y + 4, 0.45)
    J1 = LV.joints(lcx, lcy, lv_face, lv_pose)
    WR = J1['WR']
    hand_mid = add(WR, dirv(86), LV.body.mit_l * 0.55)
    ghost_c = (hand_mid[0], hand_mid[1] - LV.body.mit_w * 0.4 + 2)
    tray_top = add(J1['WL'], dirv(180), LV.body.mit_l)
    tw = 0.55 * DL
    dome_y = tray_top[1] - 0.25 * tw
    lv_face['eyes'] = dict(lid=0.27, low=0.05, look=((hx - lcx) / DL, (hy - lcy) / DL), look_k=1.0)

    hs_face = dict(turn=-0.5, tilt=7, red=0.55,
                   eyes=dict(H=0.56, lid=0.04, ik=0.58, icy=-0.01, tear=1.6,
                             look=((tray_top[0] - hx) / DH, (dome_y - hy) / DH), look_k=1.0, gy_k=0.06),
                   browL=dict(dy=-0.05, tilt=-22), browR=dict(dy=-0.05, tilt=-22),
                   mouth=dict(type='o', w=0.11, h=0.12, dy=0.0),
                   glasses=dict(dy=0.022, rot=-7),
                   sweat=[(0.55, -0.32), (0.64, -0.10, 0.75)])
    grab = (ghost_c[0] + 0.10 * DL, ghost_c[1] - 0.16 * DL)
    hs_pose = dict(neck=-14, neck_off=0.05, spine=22, chest=19, curve=0.0, far='R', sh_k=1.05,
                   armL=dict(hand=grab, bend=1, far=False), handL=dict(ang=-118, thumb=1, thumb_ang=-60),
                   armR=dict(a1=45, a2=-28, far=True), handR=dict(ang=-28, thumb=-1),
                   footL=dict(dir=-1, tilt=60), footR=dict(dir=-1, tilt=50))
    Jh = HS.joints(hx, hy, hs_face, hs_pose)
    hs_pose['legL'] = dict(a1=-62, a2=8, far=False)
    hs_pose['legR'] = dict(a1=-22, a2=40, far=True)
    hs_pose['footL'] = dict(dir=-1, tilt=62)
    hs_pose['footR'] = dict(dir=-1, tilt=70)
    hs_pose['watch'] = dict(pos=(Jh['H'][0] + 0.26 * DH, Jh['H'][1] - 0.50 * DH), sag=0.0, cx=0.08)
    Jh = HS.joints(hx, hy, hs_face, hs_pose)
    sole = max(Jh['FL'][1], Jh['FR'][1]) + HS.body.ankle
    hs_pose['shadow'] = (Jh['H'][0] - 110, Jh['H'][0] + 90, floor_y + 4, 0.28)

    if not sil:
        o.append(f'<rect x="0" y="{horizon-22}" width="{W}" height="22" fill="{BRASS}"/>')
        o.append(f'<rect x="0" y="{horizon-22}" width="{W}" height="4" fill="{GOLD}"/>')
        o.append(floor_tiles(horizon, band, vp=(540, 680), tile=150, off=52, parity=1, light=SAGE, dark=EMERALD, fade=(0.0, 0.3)))
        o.append(f'<clipPath id="flr"><rect x="0" y="{horizon}" width="{W}" height="{band-horizon}"/></clipPath><g clip-path="url(#flr)">'
                 + lamp(330, horizon + 60, 210, 330, 0.42) + lamp(800, horizon + 40, 190, 300, 0.40) + '</g>')
        o.append(f'<rect x="0" y="{band}" width="{W}" height="{H-band}" fill="{FLOOR_D}"/>')
        o.append(f'<rect x="0" y="{band}" width="{W}" height="3" fill="{shade(GOLD,0.35)}"/>')
        o.append(lamp(340, floor_y - 30, 300, 110, 0.45))
        o.append(lamp(800, floor_y - 40, 240, 120, 0.4))

    o.append(clerk_booth(890, 262, 300, SC['booth_ledge'], horizon, look=(tray_top[0], dome_y), sil=sil))

    marks = ''
    if not sil:
        marks += cloche_ghost(ghost_c[0], ghost_c[1], tw, op=0.40)
        S0 = (ghost_c[0] + 0.10 * tw, ghost_c[1] - 0.70 * tw)
        E0 = (tray_top[0] + 0.55 * tw, dome_y - 0.05 * DL)
        C0 = (S0[0] + 0.15 * DL, min(S0[1], E0[1]) - 0.95 * DL)
        marks += dotted_arc(S0, C0, E0, w=8, op=0.8, gap=17)
        marks += ticks(grab[0], grab[1], 0.15 * DH, 0.25 * DH, (-150, -195, -110), w=6, color=IVORY, op=0.8)
        for dx in (-34, 0, 34):
            x = Jh['H'][0] + dx - 40
            marks += (f'<line x1="{f(x)}" y1="{f(sole + 30)}" x2="{f(x)}" y2="{f(sole + 56)}" stroke="{IVORY}" '
                      f'stroke-width="6" stroke-linecap="round" opacity="0.5"/>')
    lv_svg = LV.draw(lcx, lcy, lv_face, lv_pose)
    hs_svg = HS.draw(hx, hy, hs_face, hs_pose)
    fg = '\n'.join([lv_svg, marks, hs_svg])
    if sil:
        fg = f'<g filter="url(#blk)">{fg}</g>'
    o.append(fg)
    if not sil:
        print('scene:')
        Hs = floor_y - (lcy - DL / 2)
        eye_report(LV, 'level', Hs)
        eye_report(HS, 'hasty')
        print(f'  level skull top {lcy-DL/2:.0f} tray top ({tray_top[0]:.0f},{tray_top[1]:.0f}) | hasty soles {sole:.0f} '
              f'hair top {hy - DH/2 - HS.head.top_extent():.0f}')
    return svg_doc(W, H, '\n'.join(o))


if __name__ == '__main__':
    outs = {
        'faces.svg': build_faces(),
        'hero.svg': build_hero(),
        'partner.svg': build_partner(),
        'scene.svg': build_scene(),
        'hero_sil.svg': build_hero(sil=True),
        'partner_sil.svg': build_partner(sil=True),
        'scene_sil.svg': build_scene(sil=True),
        'hero_raw_sil.svg': build_hero(sil=True, raw=True),
        'partner_raw_sil.svg': build_partner(sil=True, raw=True),
    }
    for k_, v in outs.items():
        with open(os.path.join(HERE, k_), 'w') as fh:
            fh.write(v)
    print('ok')
