#!/usr/bin/env python3
"""Tall Order -- BIG-EYE round heads on stick bodies (Mr. Level + Hasty).

ONE face rig (class Head, driven by a per-character parameter dict) and ONE
stick-body rig (class Body: neck stub, collar anchor, costume torso surface,
pill limbs, mittens, shoes).  Char = Body + Head.  scene.svg, faces.svg,
hero.svg and partner.svg are all built from these two rigs.

Units: fractions of D = skull diameter (no ears / hair / nose).
Line language (Tall Order): flat fills, NO outlines, NO eye rims -- the ink
lid line is the edge of every eye.  Light from the left, so every head has a
flat shadow crescent on its right/lower rim.
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
INK = '#161616'
SALMON = '#E59A7E'
MOUTH_IN = '#3A1E1A'
TONGUE = '#C46A5A'
EYE_W = '#FFFBF2'
LINE_BG = '#EDEAE4'

SKIN_L, SHAD_L = '#B07A55', '#966545'      # Mr. Level
SILVER, SILVER_D = '#CFCAC2', '#ABA59C'
COAT, COAT_T, SATIN = '#24211F', '#1B1918', '#45403C'
GLOVE, GLOVE_EDGE = IVORY, '#CFC6B4'
PATENT = '#121212'

SKIN_H, SHAD_H = '#E6B590', '#CD9C78'      # Hasty
HAIR_H = '#1A1716'
ENJI, ENJI_D = '#A8363F', '#86292F'
SHIRT, SHIRT_D = '#A9C3D8', '#8EAAC0'
TIE = '#22304A'
NOSE_RED = '#E0645A'

SKIN_C, SHAD_C = '#7A4E37', '#68412D'      # clerk cameo
HAIR_C = '#5B5550'
CARDI = '#3E4E5E'

TRAY = '#C9C4B8'
TEA = '#8A4B2A'

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


def ribbon_pts(p0, c, p1, w0, w1, n=16):
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        p = bez2(p0, c, p1, t)
        q = bez2(p0, c, p1, min(t + 0.01, 1.0))
        r = bez2(p0, c, p1, max(t - 0.01, 0.0))
        tx, ty = q[0] - r[0], q[1] - r[1]
        L = max(math.hypot(tx, ty), 1e-6)
        nx, ny = -ty / L, tx / L
        w = (w0 + (w1 - w0) * t) / 2
        left.append((p[0] + nx * w, p[1] + ny * w))
        right.append((p[0] - nx * w, p[1] - ny * w))
    return left, right


def ribbon(p0, c, p1, w0, w1, fill, tip='point', extra=''):
    left, right = ribbon_pts(p0, c, p1, w0, w1)
    end = []
    if tip == 'point':
        q = bez2(p0, c, p1, 0.98)
        d = norm(sub(p1, q))
        end = [add(p1, d, max(w1, 2) * 0.8)]
    return f'<polygon points="{pstr(left + end + right[::-1])}" fill="{fill}"{extra}/>'


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


# =====================================================================
# EYE SHAPES  (pixel polygons)
# =====================================================================
def shape_pts(kind, cx, cy, w, h, n=36):
    pts = []
    if kind == 'capsule':
        # horizontal capsule: straight top + bottom, full-height rounded ends
        rx = min(h / 2, w / 2)
        ry = h / 2
        c = w / 2 - rx
        for i in range(n + 1):
            a = -math.pi / 2 + math.pi * i / n
            pts.append((cx + c + rx * math.cos(a), cy + ry * math.sin(a)))
        for i in range(n + 1):
            a = math.pi / 2 + math.pi * i / n
            pts.append((cx - c + rx * math.cos(a), cy + ry * math.sin(a)))
    else:   # round / oval / generic
        for i in range(2 * n):
            a = 2 * math.pi * i / (2 * n)
            pts.append((cx + w / 2 * math.cos(a), cy + h / 2 * math.sin(a)))
    return pts


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


# =====================================================================
# FACE RIG
# =====================================================================
class Head:
    """True circle of diameter D, flat skin, shadow crescent, two ears,
    hair break, nose, BIG eyes (white footprint + lid-tone mask + ink lid
    line + solid pupils), brows, mouth, lower-face age marks."""

    def __init__(self, D, P):
        self.D, self.R, self.P = D, D / 2, P
        self.skin, self.shad = P['skin'], P['shad']
        self.stats = {}

    def k(self, v):
        return v * self.D

    def rim_y(self, x):
        return -math.sqrt(max(self.R ** 2 - x * x, 0))

    def top_extent(self, face=None):
        return self.k(self.P.get('hair_rise', 0))

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

    # ------------------------------------------------------------ hair
    def _rim_arc(self, a0, a1, r, n=24):
        return [(r * math.cos(a0 + (a1 - a0) * i / n), r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

    def _band(self, s, y_a, y_b, bw):
        """hair band hugging the rim on side s between y_a (top) and y_b (bottom),
        both ends cut LEVEL."""
        R = self.R
        ri = R - bw
        xo_a = s * math.sqrt(max(R * R - y_a * y_a, 0))
        xo_b = s * math.sqrt(max(R * R - y_b * y_b, 0))
        a_top = math.atan2(y_a, xo_a)
        a_bot = math.atan2(y_b, xo_b)
        if s < 0 and a_bot > a_top:
            a_bot -= 2 * math.pi
        outer = self._rim_arc(a_top, a_bot, R, 16)
        xi_b = s * math.sqrt(max(ri * ri - y_b * y_b, 0))
        xi_a = s * math.sqrt(max(ri * ri - y_a * y_a, 0))
        a_ib = math.atan2(y_b, xi_b)
        a_ia = math.atan2(y_a, xi_a)
        if s < 0 and a_ib > a_ia:
            a_ib -= 2 * math.pi
        inner = self._rim_arc(a_ib, a_ia, ri, 14)
        return f'<polygon points="{pstr(outer + inner)}"/>'

    def hair_flattop(self, face):
        """silver flat-top: ruler-flat deck rising above the skull, a crisp
        barber's line-up (straight hairline with squared temple corners)
        running down the temples into sideburns that are cut LEVEL."""
        k, R = self.k, self.R
        t = face.get('turn', 0)
        a = min(abs(t) / 0.7, 1)
        sh = k(-0.03 * t)
        yt = k(-0.5 - self.P['hair_rise'])
        xd = k(self.P.get('deck_w', 0.40))
        xl, xr = -xd + sh, xd + sh
        cr = k(0.055)
        yh = k(-0.405)                                  # level hairline
        yb = k(0.03)                                    # level sideburn cut
        c2 = k(0.05)                                    # line-up corner radius

        def bw(sd):
            back = (sd * t < -0.1)
            return k(0.075 + (0.04 * a if back else -0.03 * a))

        def rim_x(y, sd, r=R):
            return sd * math.sqrt(max(r * r - y * y, 0))
        pts = []
        # outer: left sideburn bottom -> up the rim -> deck -> down the rim -> right sideburn bottom
        aLb = math.atan2(yb, rim_x(yb, -1))
        aLd = math.atan2(self.rim_y(xl), xl)
        if aLb > aLd:
            aLb -= 2 * math.pi
        aLb, aLd = aLb, aLd
        # left side goes from angle ~ +176 (as -184) up to ~ -135
        pts += self._rim_arc(aLb + 2 * math.pi if aLb < -math.pi else aLb, aLd, R, 18) if False else []
        n = 18
        a0 = math.atan2(yb, rim_x(yb, -1))            # ~ +176 deg
        a1 = math.atan2(self.rim_y(xl), xl) + 2 * math.pi   # ~ +225 deg
        pts += [(R * math.cos(a0 + (a1 - a0) * i / n), R * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
        pts += [(xl + cr - cr * math.cos(q), yt + cr - cr * math.sin(q)) for q in [i * math.pi / 16 for i in range(9)]]
        pts += [(xr - cr + cr * math.cos(q), yt + cr - cr * math.sin(q)) for q in [math.pi / 2 - i * math.pi / 16 for i in range(9)]]
        b0 = math.atan2(self.rim_y(xr), xr)            # ~ -45 deg
        b1 = math.atan2(yb, rim_x(yb, 1))              # ~ +4 deg
        pts += [(R * math.cos(b0 + (b1 - b0) * i / n), R * math.sin(b0 + (b1 - b0) * i / n)) for i in range(n + 1)]
        # inner: right sideburn cut -> up the right temple -> corner -> level hairline -> corner -> down left temple
        for sd in (1, -1):
            ri = R - bw(sd)
            yc = yh + c2
            col = []
            m = 12
            for i in range(m + 1):
                y = yb + (yc - yb) * i / m
                col.append((rim_x(y, sd, ri), y))
            xc = rim_x(yc, sd, ri)
            corner = [bez2((xc, yc), (xc, yh), (xc - sd * c2, yh), u / 6) for u in range(1, 7)]
            seg = col + corner
            if sd == 1:
                pts += seg
            else:
                pts += seg[::-1]
        main = [f'<polygon points="{pstr(pts)}"/>']
        return main, [], [], (xl, xr, yt)

    def hair_flattop_marks(self, face, deck):
        """flat top plane (lighter) whose lower edge is a row of bristle tips,
        plus vertical comb lines on the front face."""
        k = self.k
        xl, xr, yt = deck
        top = mix(self.P['hair_col'], '#FFFFFF', 0.5)
        n = 16
        pts = [(xl + k(0.012), yt + k(0.012)), (xr - k(0.012), yt + k(0.012))]
        y1 = yt + k(0.045)
        tips = []
        for i in range(n + 1):
            x = xr - k(0.012) - (xr - xl - k(0.024)) * i / n
            tips.append((x, y1 + (k(0.018) if i % 2 else 0)))
        o = [f'<polygon points="{pstr(pts + tips)}" fill="{top}"/>']
        m = 9
        R = self.R
        for i in range(m):
            x = xl + k(0.03) + (xr - xl - k(0.06)) * (i + 0.5) / m
            ybot = min(k(-0.425), self.rim_y(x) + k(0.02)) if abs(x) < R else yt + k(0.2)
            ytop = yt + k(0.075 + 0.025 * ((i * 7) % 3) / 2)
            if ybot - ytop > k(0.04):
                o.append(f'<line x1="{f(x)}" y1="{f(ytop)}" x2="{f(x)}" y2="{f(ytop + (ybot - ytop) * (0.55 + 0.25 * (i % 2)))}" '
                         f'stroke="{shade(self.P["hair_col"], 0.13)}" stroke-width="{f(k(0.016))}" stroke-linecap="round"/>')
        return ''.join(o)

    def hair_part(self, face):
        """slick black hair hugging the skull, centre part with a small notch."""
        k, R = self.k, self.R
        t = face.get('turn', 0)
        a = min(abs(t) / 0.7, 1)
        px = k(0.13 * t)
        rise = k(self.P['hair_rise'])
        ap = math.atan2(-math.sqrt(max(R * R - px * px, 0)), px)
        ylt = k(-0.10)          # ear top
        aL = math.atan2(ylt, -math.sqrt(R * R - ylt * ylt))
        aR = math.atan2(ylt, math.sqrt(R * R - ylt * ylt))
        outer = []
        n = 60
        for i in range(n + 1):
            ang = aL + (aR - aL) * i / n
            # rise fades in from the ears, notch at the part
            up = math.sin(math.pi * i / n) ** 0.5
            da = math.degrees(((ang - ap + math.pi) % (2 * math.pi)) - math.pi)
            notch = math.exp(-(da / 4.5) ** 2)
            lobes = math.exp(-((abs(da) - 30) / 24) ** 2)
            r = R + rise * 0.45 * up + rise * lobes * up - k(0.085) * notch
            outer.append((r * math.cos(ang), r * math.sin(ang)))
        # inner edge: temple bands + double-arc hairline meeting at the part
        def band(s):
            back = (s * t < -0.1)
            return k(0.05 + (0.07 * a if back else -0.015 * a))
        yhl = k(-0.29)
        pts_in = []
        for s in (1, -1):
            ri = R - band(s)
            xb = s * math.sqrt(max(ri * ri - ylt * ylt, 0))
            xt = s * math.sqrt(max(ri * ri - yhl * yhl, 0))
            seg = [(xb, ylt), (xt, yhl)]
            if s == 1:
                pts_in += seg
                # hairline arc to the part (right branch)
                for j in range(1, 11):
                    u = j / 10
                    pts_in.append(bez2((xt, yhl), (px + k(0.20), k(-0.44)), (px, k(-0.415)), u))
            else:
                left = []
                for j in range(0, 10):
                    u = j / 10
                    left.append(bez2((px, k(-0.415)), (px - k(0.20), k(-0.44)), (xt, yhl), u))
                pts_in += left + [(xt, yhl), (xb, ylt)]
        poly = outer + pts_in
        out = [f'<polygon points="{pstr(poly)}"/>']
        return out, (px, rise)

    def hair_part_marks(self, face, info):
        k, R = self.k, self.R
        px, rise = info
        t = face.get('turn', 0)
        o = []
        # part line (skin) from hairline to crown
        o.append(f'<line x1="{f(px)}" y1="{f(k(-0.42))}" x2="{f(px*1.04)}" y2="{f(self.rim_y(px) - rise*0.2)}" '
                 f'stroke="{self.skin}" stroke-width="{f(k(0.016))}" stroke-linecap="round"/>')
        # one combed groove each side
        for s in (-1, 1):
            g0 = (px + s * k(0.07), k(-0.47))
            g1 = (px + s * k(0.28), k(-0.43))
            g2 = (s * k(0.43) + k(0.03 * t), k(-0.20))
            o.append(f'<path d="M{f(g0[0])},{f(g0[1])} Q{f(g1[0])},{f(g1[1])} {f(g2[0])},{f(g2[1])}" stroke="#3E3936" '
                     f'stroke-width="{f(k(0.02))}" stroke-linecap="round" fill="none"/>')
        return ''.join(o)

    def hair_bun(self, face):
        k, R = self.k, self.R
        yh = k(-0.30)
        xh = math.sqrt(R * R - yh * yh)
        pts = self._rim_arc(math.atan2(yh, -xh), math.atan2(yh, xh) + 0, R + k(0.02), 30)
        # go over the top: from left (angle ~ -143deg) to right (~ -37deg) through -90
        a0 = math.atan2(yh, -xh)
        a1 = math.atan2(yh, xh)
        if a0 > a1:
            a0 -= 2 * math.pi
        pts = self._rim_arc(a0, a1, R + k(0.02), 30)
        poly = pts + [(xh * 0.9, yh + k(0.02)), (0, k(-0.36)), (-xh * 0.9, yh + k(0.02))]
        return [f'<polygon points="{pstr(poly)}"/>',
                f'<circle cx="0" cy="{f(-R - k(0.08))}" r="{f(k(0.14))}"/>'], None

    # ------------------------------------------------------------ eyes
    def eye_layout(self, face):
        E = self.P['eye']
        t = face.get('turn', 0.0)
        a = min(abs(t) / 0.7, 1.0)
        s = 1 if t > 0 else -1
        W, g = E['W'], E['gap']
        fx = face.get('fx', 0.23 * t)
        wf = 1 - 0.25 * a
        if abs(t) < 1e-6:
            xs = {'L': -(g / 2 + W / 2), 'R': g / 2 + W / 2}
            ws = {'L': W, 'R': W}
        else:
            far, near = ('R', 'L') if s > 0 else ('L', 'R')
            xs = {far: fx + s * (g / 2 + W * wf / 2), near: fx - s * (g / 2 + W / 2)}
            ws = {far: W * wf, near: W}
        y = E['y'] + face.get('ey', 0)
        return xs, ws, y, fx

    def eyes_svg(self, face):
        k = self.k
        E = self.P['eye']
        e = face.get('eyes', {})
        xs, ws, ey, fx = self.eye_layout(face)
        h = E['H']
        out = []
        self.stats['eyes'] = {}
        for side in ('L', 'R'):
            o_sign = -1 if side == 'L' else 1
            cx, cy, w = k(xs[side]), k(ey), k(ws[side])
            out.append(self._eye(side, o_sign, cx, cy, w, k(h), e, face))
        return '\n'.join(out)

    def _pupil_pos(self, cx, cy, w, h, ly_at, r, e, side):
        look = e.get('look')
        if look is not None:
            vx, vy = look[0] * self.D - cx, look[1] * self.D - cy
            L = math.hypot(vx, vy) or 1
            gx, gy = vx / L * e.get('look_k', 1.0), vy / L * e.get('look_k', 1.0)
        else:
            gx, gy = e.get('gaze', (0.0, -0.4))
            if isinstance(gx, dict):
                gx = gx[side]
        x = cx + gx * (w / 2 - 0.45 * r)
        ly = ly_at(x)
        ytop = ly + r * 0.55
        ybot = cy + h / 2 - r * 0.62
        if ytop > ybot:
            y = ytop
        else:
            y = ytop + (ybot - ytop) * (gy + 1) / 2
        return x, y

    def _eye(self, side, o, cx, cy, w, h, e, face):
        k = self.k
        E = self.P['eye']
        kind = E['shape']
        lid = e.get('lid', E['lid'])
        if isinstance(lid, dict):
            lid = lid[side]
        tilt = e.get('lid_tilt', 0.0)            # + = outer end lower
        m = o * math.tan(math.radians(tilt))
        top = cy - h / 2
        ly = top + lid * h
        pts = shape_pts(kind, cx, cy, w, h)
        cid, lidc = uid('ec'), uid('el')
        ly_at = lambda x: ly + m * (x - cx)
        big = 3 * w + 3 * h
        half = [(cx - big, ly_at(cx - big)), (cx + big, ly_at(cx + big)), (cx + big, cy + big), (cx - big, cy + big)]
        g = [f'<clipPath id="{cid}"><polygon points="{pstr(pts)}"/></clipPath>',
             f'<clipPath id="{lidc}"><polygon points="{pstr(half)}"/></clipPath>']
        # socket tone (keeps the white readable on light skin)
        if E.get('socket'):
            sp = shape_pts(kind, cx, cy + k(0.012), w + k(0.04), h + k(0.035))
            g.append(f'<polygon points="{pstr(sp)}" fill="{mix(self.skin, self.shad, E["socket"])}"/>')
        # lid-tone footprint, then the white below the lid line
        lidtone = E.get('lidtone') or mix(self.skin, self.shad, 0.75)
        g.append(f'<polygon points="{pstr(pts)}" fill="{lidtone}"/>')
        g.append(f'<g clip-path="url(#{cid})"><polygon clip-path="url(#{lidc})" points="{pstr(half)}" fill="{EYE_W}"/></g>')
        # pupils
        pr = k(e.get('pupil', E['pupil'])) / 2
        px, py = self._pupil_pos(cx, cy, w, h, ly_at, pr, e, side)
        pg = []
        for gx, gy in e.get('ghosts', []):
            pg.append(f'<circle cx="{f(px + k(gx))}" cy="{f(py + k(gy))}" r="{f(pr)}" fill="{INK}" opacity="0.32"/>')
        pg.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="{f(pr)}" fill="{INK}"/>')
        g.append(f'<g clip-path="url(#{cid})"><g clip-path="url(#{lidc})">' + ''.join(pg) + '</g></g>')
        # ink lid line
        th = k(E.get('lid_th', 0.034))
        if lid > 0.005:
            hit = line_hits(pts, cx, ly, m)
            if hit:
                x0, x1 = hit
                ov = k(0.012)
                g.append(f'<line x1="{f(x0-ov)}" y1="{f(ly_at(x0-ov))}" x2="{f(x1+ov)}" y2="{f(ly_at(x1+ov))}" '
                         f'stroke="{INK}" stroke-width="{f(th)}" stroke-linecap="round"/>')
        elif e.get('crease_up', True):
            # shock take: lid snapped up into the socket -> thin crease arc above
            g.append(f'<path d="M{f(cx - w*0.42)},{f(top - k(0.025))} Q{f(cx)},{f(top - k(0.075))} {f(cx + w*0.42)},{f(top - k(0.025))}" '
                     f'stroke="{shade(self.skin, 0.3)}" stroke-width="{f(k(0.018))}" stroke-linecap="round" fill="none"/>')
        # age marks under the eye
        if E.get('bag'):
            bc = shade(self.skin, 0.24)
            bw = k(0.017)
            yb = cy + h / 2 + k(0.04)
            g.append(f'<path d="M{f(cx - w*0.34)},{f(yb - k(0.004))} Q{f(cx + o*w*0.05)},{f(yb + k(0.018))} {f(cx + o*w*0.36)},{f(yb - k(0.01))}" '
                     f'stroke="{bc}" stroke-width="{f(bw)}" stroke-linecap="round" fill="none"/>')
            room = self.R - k(0.085) - abs(cx + o * w / 2)
            if E.get('crow') and e.get('crow', True) and room > k(0.08):
                xo = cx + o * (w / 2 + k(0.025))
                for j, ang in enumerate((-18, 14)):
                    d = rot(o * k(0.055), 0, o * ang)
                    g.append(f'<line x1="{f(xo)}" y1="{f(cy + k(0.02) + j*k(0.035))}" x2="{f(xo + d[0])}" y2="{f(cy + k(0.02) + j*k(0.035) + d[1])}" '
                             f'stroke="{bc}" stroke-width="{f(bw)}" stroke-linecap="round"/>')
        self.stats['eyes'][side] = dict(w=w / self.D, h=h / self.D, cx=cx / self.D, cy=cy / self.D,
                                       top_below_skull=(top + self.R) / self.D, lid=lid, pupil=2 * pr / self.D)
        return '\n'.join(g)

    # ------------------------------------------------------------ brows
    def brows_svg(self, face):
        out = []
        xs, ws, ey, fx = self.eye_layout(face)
        for side in ('L', 'R'):
            out.append(self._brow(side, xs[side], ws[side], ey, face.get('brow' + side, {})))
        return '\n'.join(out)

    def _brow(self, side, ex, ew, ey, b):
        if b is None:
            return ''
        k = self.k
        B = self.P['brow']
        E = self.P['eye']
        s = -1 if side == 'L' else 1           # outer direction
        W = k(B['W'] * ew / E['W'] * b.get('wk', 1.0))
        H = k(b.get('h', B['H']))
        bx = k(ex) + s * k(B.get('out', 0.0)) + k(b.get('dx', 0))
        eye_top = k(ey - E['H'] / 2)
        by = eye_top - k(B['gap']) - H / 2 + k(b.get('dy', 0))
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
        if b.get('lines'):     # worry / anger creases between the brows
            pass
        return '\n'.join(out)

    def _brow_shape(self, kind, side, W, H):
        if kind == 'pill':
            return lambda col: f'<rect x="{f(-W/2)}" y="{f(-H/2)}" width="{f(W)}" height="{f(H)}" rx="{f(H/2)}" fill="{col}"/>'
        # worried comma: round head at the INNER end, tapering tail outward,
        # gently arched
        s = 1 if side == 'L' else -1        # inner end at +x for the left brow
        top, bot = [], []
        n = 14
        for i in range(n + 1):
            u = i / n                        # 0 = inner head, 1 = outer tail
            x = s * (W / 2 - u * W)
            yc = -H * 0.35 * math.sin(math.pi * u) + H * 0.25 * u
            th = H * (1 - 0.72 * u ** 0.9) / 2
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
        xs, ws, ey, fx = self.eye_layout(face)
        fxp = k(fx)
        kind = self.P['nose']
        o = []
        if kind == 'long':
            # long straight nose: narrow bridge between the eyes, straight
            # ridge, flat underside 0.14 D wide, one nostril
            yt, yb = k(-0.11), k(0.20)
            if abs(t) < 0.05:
                pts = [(fxp - k(0.02), yt), (fxp + k(0.02), yt), (fxp + k(0.07), yb - k(0.025)),
                       (fxp + k(0.065), yb), (fxp - k(0.065), yb), (fxp - k(0.07), yb - k(0.025))]
            else:
                tip = fxp + s * k(0.075 + 0.05 * a)
                back = fxp - s * k(0.06 - 0.01 * a)
                pts = [(fxp - s * k(0.015), yt), (fxp + s * k(0.02), yt), (tip, yb - k(0.03)),
                       (tip - s * k(0.008), yb), (back, yb), (back - s * k(0.008), yb - k(0.02))]
            o.append(f'<polygon points="{pstr(pts)}" fill="{self.shad}" stroke="{self.shad}" stroke-width="{f(k(0.02))}" stroke-linejoin="round"/>')
            nx = fxp + (s * k(0.02 + 0.02 * a) if abs(t) >= 0.05 else -k(0.025))
            o.append(f'<ellipse cx="{f(nx)}" cy="{f(yb - k(0.015))}" rx="{f(k(0.03))}" ry="{f(k(0.014))}" fill="{shade(self.shad, 0.3)}"/>')
            if abs(t) < 0.05:
                o.append(f'<ellipse cx="{f(fxp + k(0.03))}" cy="{f(yb - k(0.015))}" rx="{f(k(0.026))}" ry="{f(k(0.013))}" fill="{shade(self.shad, 0.3)}"/>')
        elif kind == 'pointy':
            red = face.get('red', 0.0)
            yt, yb = k(0.0), k(0.115)
            if abs(t) < 0.05:
                pts = [(fxp, yt), (fxp + k(0.062), yb), (fxp - k(0.062), yb)]
                tip = (fxp, yb - k(0.01))
            else:
                tipx = fxp + s * k(0.07 + 0.03 * a)
                pts = [(fxp + s * k(0.005), yt), (tipx, yb - k(0.005)), (fxp - s * k(0.05), yb)]
                tip = (tipx - s * k(0.035), yb - k(0.02))
            ncol = mix(self.shad, NOSE_RED, red)
            o.append(f'<polygon points="{pstr(pts)}" fill="{ncol}" stroke="{ncol}" stroke-width="{f(k(0.022))}" stroke-linejoin="round"/>')
            if red > 0:
                o.append(f'<ellipse cx="{f(tip[0])}" cy="{f(tip[1])}" rx="{f(k(0.05))}" ry="{f(k(0.035))}" fill="{NOSE_RED}" opacity="{f(min(1, red))}"/>')
        elif kind == 'button':
            o.append(f'<ellipse cx="{f(fxp + s*k(0.02))}" cy="{f(k(0.09))}" rx="{f(k(0.065))}" ry="{f(k(0.05))}" fill="{self.shad}"/>')
        return '\n'.join(o)

    # ------------------------------------------------------------ glasses
    def glasses_svg(self, face):
        g = self.P.get('glasses')
        if not g:
            return ''
        k = self.k
        gl = face.get('glasses', {})
        xs, ws, ey, fx = self.eye_layout(face)
        E = self.P['eye']
        t = face.get('turn', 0)
        s = 1 if t >= 0 else -1
        y0 = k(g['y'] + gl.get('dy', 0))
        lw_full = g['w']
        lh = k(g['h'])
        rim = k(0.019)
        parts = []
        inner_pts = {}
        for side in ('L', 'R'):
            cx = k(xs[side] * g.get('xk', 0.92) + gl.get('dx', 0))
            lw = k(lw_full * ws[side] / E['W'])
            # half-moon: flat top edge, round bottom
            pts = [(cx - lw / 2, y0)]
            for i in range(1, 20):
                aa = math.pi * i / 20
                pts.append((cx - lw / 2 * math.cos(aa), y0 + lh * math.sin(aa)))
            pts.append((cx + lw / 2, y0))
            o_sign = -1 if side == 'L' else 1
            inner_pts[side] = (cx - o_sign * lw / 2, y0)
            parts.append(f'<polygon points="{pstr(pts)}" fill="{IVORY}" fill-opacity="0.28" stroke="{GOLD}" stroke-width="{f(rim)}" stroke-linejoin="round"/>')
            parts.append(f'<line x1="{f(cx - lw/2 + rim)}" y1="{f(y0 + lh*0.35)}" x2="{f(cx - lw*0.1)}" y2="{f(y0 + lh*0.75)}" stroke="#FFFFFF" stroke-opacity="0.5" stroke-width="{f(k(0.012))}" stroke-linecap="round"/>')
            # temple arm toward the ear on the back (visible) side
            if s * o_sign < 0 or abs(t) < 0.05:
                ex = o_sign * (self.R + k(0.01))
                parts.append(f'<line x1="{f(cx + o_sign*lw/2)}" y1="{f(y0)}" x2="{f(ex)}" y2="{f(k(-0.04))}" stroke="{GOLD}" stroke-width="{f(rim*0.8)}" stroke-linecap="round"/>')
        a, b = inner_pts['L'], inner_pts['R']
        mid = ((a[0] + b[0]) / 2, y0 - k(0.03))
        parts.append(f'<path d="M{f(a[0])},{f(a[1])} Q{f(mid[0])},{f(mid[1])} {f(b[0])},{f(b[1])}" stroke="{GOLD}" stroke-width="{f(rim)}" fill="none" stroke-linecap="round"/>')
        rotg = gl.get('rot', 0)
        return f'<g transform="rotate({f(rotg)} {f(k(fx))} {f(y0)})">' + ''.join(parts) + '</g>'

    # ------------------------------------------------------------ mouth
    def mouth_svg(self, face):
        k = self.k
        m = face.get('mouth', {})
        xs, ws, ey, fx = self.eye_layout(face)
        tp = m.get('type', 'flat')
        x = k(fx + m.get('dx', 0))
        y = k(self.P['mouth_y'] + m.get('dy', 0))
        w = k(m.get('w', 0.22))
        th = k(m.get('th', 0.028))
        st = f'stroke="{INK}" stroke-width="{f(th)}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
        if tp == 'flat':
            tl = m.get('tilt', 0)
            return f'<line x1="{f(x-w/2)}" y1="{f(y + k(tl))}" x2="{f(x+w/2)}" y2="{f(y - k(tl))}" {st}/>'
        if tp == 'curl':
            c = k(m.get('curl', 0.06))
            s = 1 if m.get('side', 'R') == 'R' else -1
            a_, b_ = x - s * w / 2, x + s * w / 2
            kx = x + s * w * 0.15
            return f'<path d="M{f(a_)},{f(y + k(0.008))} L{f(kx)},{f(y)} Q{f(b_)},{f(y)} {f(b_ + s*k(0.012))},{f(y-c)}" {st}/>'
        if tp == 'frown':
            a_ = k(m.get('amp', 0.04))
            return f'<path d="M{f(x-w/2)},{f(y+a_*0.6)} Q{f(x)},{f(y-a_*1.2)} {f(x+w/2)},{f(y+a_*0.6)}" {st}/>'
        if tp == 'zig':
            a_ = k(m.get('amp', 0.025))
            n = m.get('n', 4)
            pts = [(x - w / 2 + w * i / n, y + (a_ if i % 2 else -a_) * (0 if i in (0, n) else 1)) for i in range(n + 1)]
            return f'<polyline points="{pstr(pts)}" {st}/>'
        if tp in ('gasp', 'aah'):
            H = k(m.get('h', 0.17))
            cid = uid('mo')
            if tp == 'gasp':
                d = (f'M{f(x-w/2)},{f(y-H*0.25)} Q{f(x-w/2)},{f(y-H/2)} {f(x)},{f(y-H/2)} Q{f(x+w/2)},{f(y-H/2)} {f(x+w/2)},{f(y-H*0.25)} '
                     f'Q{f(x+w/2)},{f(y+H/2)} {f(x)},{f(y+H/2)} Q{f(x-w/2)},{f(y+H/2)} {f(x-w/2)},{f(y-H*0.25)} Z')
            else:   # wobbly open "aah": wavy top lip
                pts = []
                n = 6
                for i in range(n + 1):
                    xx = x - w / 2 + w * i / n
                    pts.append((xx, y - H * 0.35 + (k(0.022) if i % 2 else -k(0.012)) * (0 if i in (0, n) else 1)))
                d = 'M' + ' L'.join(f'{f(px)},{f(py)}' for px, py in pts)
                d += f' Q{f(x+w/2)},{f(y+H*0.65)} {f(x)},{f(y+H*0.6)} Q{f(x-w/2)},{f(y+H*0.65)} {f(x-w/2)},{f(y-H*0.35)} Z'
            return (f'<clipPath id="{cid}"><path d="{d}"/></clipPath>'
                    f'<path d="{d}" fill="{MOUTH_IN}" stroke="{INK}" stroke-width="{f(th)}" stroke-linejoin="round"/>'
                    f'<g clip-path="url(#{cid})"><rect x="{f(x-w/2)}" y="{f(y-H)}" width="{f(w)}" height="{f(H*0.62 if tp=="gasp" else H*0.66)}" fill="{IVORY}"/>'
                    f'<ellipse cx="{f(x + w*0.08)}" cy="{f(y+H*0.62)}" rx="{f(w*0.3)}" ry="{f(H*0.3)}" fill="{TONGUE}"/></g>')
        if tp in ('grit', 'grimace'):
            H = k(m.get('h', 0.11))
            tl = k(m.get('tilt', 0))
            cid = uid('mt')
            r = H * 0.35
            d = f'M{f(x-w/2+r)},{f(y-H/2+tl)} L{f(x+w/2-r)},{f(y-H/2-tl)} Q{f(x+w/2)},{f(y-H/2-tl)} {f(x+w/2)},{f(y-tl)} Q{f(x+w/2)},{f(y+H/2-tl)} {f(x+w/2-r)},{f(y+H/2-tl)} L{f(x-w/2+r)},{f(y+H/2+tl)} Q{f(x-w/2)},{f(y+H/2+tl)} {f(x-w/2)},{f(y+tl)} Q{f(x-w/2)},{f(y-H/2+tl)} {f(x-w/2+r)},{f(y-H/2+tl)} Z'
            o = [f'<clipPath id="{cid}"><path d="{d}"/></clipPath>', f'<path d="{d}" fill="{IVORY}"/>', f'<g clip-path="url(#{cid})">']
            if tp == 'grit':
                o.append(f'<line x1="{f(x-w/2)}" y1="{f(y)}" x2="{f(x+w/2)}" y2="{f(y)}" stroke="{INK}" stroke-width="{f(th*0.6)}"/>')
            else:
                pts = [(x - w / 2 + w * i / 8, y + (k(0.018) if i % 2 else -k(0.018))) for i in range(9)]
                o.append(f'<polyline points="{pstr(pts)}" stroke="{INK}" stroke-width="{f(th*0.6)}" fill="none"/>')
            for i in range(1, 5):
                xx = x - w / 2 + w * i / 5
                o.append(f'<line x1="{f(xx)}" y1="{f(y-H)}" x2="{f(xx)}" y2="{f(y+H)}" stroke="{INK}" stroke-width="{f(th*0.45)}"/>')
            o.append('</g>')
            o.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(th)}" stroke-linejoin="round"/>')
            return ''.join(o)
        return ''

    # ------------------------------------------------------------ lower face
    def lowerface_svg(self, face):
        k = self.k
        xs, ws, ey, fx = self.eye_layout(face)
        t = face.get('turn', 0)
        a = min(abs(t) / 0.7, 1)
        col = shade(self.skin, 0.2)
        lw = k(0.017)
        o = []
        kind = self.P.get('lower')
        fxp = k(fx)
        my = k(self.P['mouth_y'])
        if kind == 'level':
            # nasolabial folds + a LEVEL chin crease
            for s in (-1, 1):
                sq = 1 - 0.45 * a if s * t > 0 else 1
                x0 = fxp + s * k(0.10) * sq
                x1 = fxp + s * k(0.17) * sq
                o.append(f'<path d="M{f(x0)},{f(k(0.17))} Q{f(x1)},{f(k(0.22))} {f(x1 - s*k(0.01))},{f(my + k(0.03))}" '
                         f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
            o.append(f'<line x1="{f(fxp - k(0.06))}" y1="{f(k(0.415))}" x2="{f(fxp + k(0.06))}" y2="{f(k(0.415))}" '
                     f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round"/>')
        elif kind == 'jowl':
            # jowl creases at the mouth corners + a soft double-chin arc
            for s in (-1, 1):
                sq = 1 - 0.45 * a if s * t > 0 else 1
                x0 = fxp + s * k(0.17) * sq
                o.append(f'<path d="M{f(x0)},{f(my - k(0.035))} Q{f(x0 + s*k(0.035))},{f(my + k(0.03))} {f(x0 + s*k(0.0))},{f(my + k(0.085))}" '
                         f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
            o.append(f'<path d="M{f(fxp - k(0.11))},{f(k(0.425))} Q{f(fxp)},{f(k(0.465))} {f(fxp + k(0.11))},{f(k(0.425))}" '
                     f'stroke="{col}" stroke-width="{f(lw)}" stroke-linecap="round" fill="none"/>')
        return '\n'.join(o)

    def creases_svg(self, face):
        """frown / worry creases between the brows."""
        c = face.get('crease')
        if not c:
            return ''
        k = self.k
        xs, ws, ey, fx = self.eye_layout(face)
        col = shade(self.skin, 0.25)
        y0 = k(ey - self.P['eye']['H'] / 2 - 0.10)
        o = []
        for s in (-1, 1):
            x = k(fx) + s * k(0.028)
            if c == 'anger':
                o.append(f'<line x1="{f(x)}" y1="{f(y0 - k(0.02))}" x2="{f(x - s*k(0.008))}" y2="{f(y0 + k(0.06))}" stroke="{col}" stroke-width="{f(k(0.016))}" stroke-linecap="round"/>')
            else:
                o.append(f'<path d="M{f(x + s*k(0.0))},{f(y0 - k(0.03))} Q{f(x + s*k(0.02))},{f(y0 + k(0.0))} {f(x)},{f(y0 + k(0.03))}" stroke="{col}" stroke-width="{f(k(0.015))}" stroke-linecap="round" fill="none"/>')
        return ''.join(o)

    def extras(self, face):
        k = self.k
        o = []
        for sw in face.get('sweat', []):
            sx, sy = sw[0], sw[1]
            sc = sw[2] if len(sw) > 2 else 1.0
            o.append(drop(k(sx), k(sy), k(0.042) * sc, col=IVORY))
        return '\n'.join(o)

    # ------------------------------------------------------------ whole head
    def draw(self, cx, cy, face):
        k, R, D = self.k, self.R, self.D
        P = self.P
        t = face.get('turn', 0.0)
        clip, msk = uid('hc'), uid('hm')
        o = []
        o.append(f'<clipPath id="{clip}"><circle r="{f(R)}"/></clipPath>')
        o.append(f'<mask id="{msk}" maskUnits="userSpaceOnUse" x="{f(-2*R)}" y="{f(-3*R)}" width="{f(4*R)}" height="{f(5*R)}">'
                 f'<rect x="{f(-2*R)}" y="{f(-3*R)}" width="{f(4*R)}" height="{f(5*R)}" fill="#fff"/>'
                 f'<circle cx="{f(k(-0.12))}" cy="{f(k(-0.08))}" r="{f(R)}" fill="#000"/></mask>')
        hmsk = uid('hhm')
        o.append(f'<mask id="{hmsk}" maskUnits="userSpaceOnUse" x="{f(-2*R)}" y="{f(-3*R)}" width="{f(4*R)}" height="{f(5*R)}">'
                 f'<rect x="{f(-2*R)}" y="{f(-3*R)}" width="{f(4*R)}" height="{f(5*R)}" fill="#fff"/>'
                 f'<circle cx="{f(k(-0.10))}" cy="{f(k(-0.20))}" r="{f(k(0.575))}" fill="#000"/></mask>')
        o += self.ears(t)
        o.append(f'<circle r="{f(R)}" fill="{self.skin}"/>')
        o.append(f'<circle r="{f(R)}" fill="{self.shad}" mask="url(#{msk})"/>')
        hk = P['hair']
        marks = ''
        if hk == 'flattop':
            hp, fade, burns, deck = self.hair_flattop(face)
            fc = mix(self.skin, P['hair_col'], 0.42)
            o.append(f'<g fill="{fc}">' + ''.join(fade) + '</g>')
            o.append(f'<g fill="{mix(self.shad, P["hair_shad"], 0.42)}" mask="url(#{hmsk})">' + ''.join(fade) + '</g>')
            hp = hp + burns
            marks = self.hair_flattop_marks(face, deck)
        elif hk == 'part':
            hp, info = self.hair_part(face)
            marks = self.hair_part_marks(face, info)
        elif hk == 'bun':
            hp, _ = self.hair_bun(face)
        else:
            hp = []
        o.append(f'<g fill="{P["hair_col"]}">' + ''.join(hp) + '</g>')
        o.append(f'<g fill="{P["hair_shad"]}" mask="url(#{hmsk if hk == "flattop" else msk})">' + ''.join(hp) + '</g>')
        o.append(marks)
        feats = [self.eyes_svg(face), self.nose_svg(face), self.lowerface_svg(face), self.mouth_svg(face),
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
def tray_cup(cx, bottom, w):
    s = w / 216
    ty = bottom - 21 * s
    tx = cx
    o = []
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty+6*s)}" rx="{f(108*s)}" ry="{f(19*s)}" fill="{shade(TRAY,0.3)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty)}" rx="{f(108*s)}" ry="{f(18*s)}" fill="{TRAY}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty)}" rx="{f(92*s)}" ry="{f(12*s)}" fill="{mix(TRAY,IVORY,0.35)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty-4*s)}" rx="{f(52*s)}" ry="{f(10*s)}" fill="{shade(IVORY,0.12)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty-6*s)}" rx="{f(48*s)}" ry="{f(8*s)}" fill="{IVORY}"/>')
    cw, ch = 46 * s, 58 * s
    top = ty - 6 * s - ch
    o.append(f'<path d="M{f(tx+cw+2*s)},{f(top+12*s)} a{f(15*s)},{f(15*s)} 0 1 1 {f(-3*s)},{f(32*s)}" stroke="{IVORY}" stroke-width="{f(10*s)}" fill="none"/>')
    o.append(f'<path d="M{f(tx-cw)},{f(top)} L{f(tx+cw)},{f(top)} Q{f(tx+cw)},{f(top+ch-6*s)} {f(tx+14*s)},{f(top+ch)} '
             f'L{f(tx-14*s)},{f(top+ch)} Q{f(tx-cw)},{f(top+ch-6*s)} {f(tx-cw)},{f(top)} Z" fill="{IVORY}"/>')
    o.append(f'<path d="M{f(tx+20*s)},{f(top)} L{f(tx+cw)},{f(top)} Q{f(tx+cw)},{f(top+ch-6*s)} {f(tx+14*s)},{f(top+ch)} '
             f'L{f(tx+6*s)},{f(top+ch)} Q{f(tx+28*s)},{f(top+ch-12*s)} {f(tx+20*s)},{f(top)} Z" fill="{shade(IVORY,0.12)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(top)}" rx="{f(cw)}" ry="{f(10*s)}" fill="{shade(IVORY,0.06)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(top)}" rx="{f(cw-3*s)}" ry="{f(8*s)}" fill="{TEA}"/>')
    o.append(f'<ellipse cx="{f(tx-13*s)}" cy="{f(top-1*s)}" rx="{f(9*s)}" ry="{f(2.6*s)}" fill="{IVORY}" opacity="0.8"/>')
    return '\n'.join(o)


def tray_ghost(cx, bottom, w, op=0.5, col=IVORY):
    s = w / 216
    ty = bottom - 21 * s
    cw, ch = 46 * s, 58 * s
    top = ty - 6 * s - ch
    return (f'<g opacity="{op}" fill="{col}">'
            f'<ellipse cx="{f(cx)}" cy="{f(ty+3*s)}" rx="{f(108*s)}" ry="{f(19*s)}"/>'
            f'<path d="M{f(cx-cw)},{f(top)} L{f(cx+cw)},{f(top)} Q{f(cx+cw)},{f(top+ch-6*s)} {f(cx+14*s)},{f(top+ch)} '
            f'L{f(cx-14*s)},{f(top+ch)} Q{f(cx-cw)},{f(top+ch-6*s)} {f(cx-cw)},{f(top)} Z"/>'
            f'<path d="M{f(cx+cw+2*s)},{f(top+12*s)} a{f(15*s)},{f(15*s)} 0 1 1 {f(-3*s)},{f(32*s)}" stroke="{col}" stroke-width="{f(10*s)}" fill="none"/>'
            f'</g>')


# =====================================================================
# STICK-BODY RIG
# =====================================================================
class Body:
    def __init__(self, D, neck=0.15, yoke=0.06, spine=1.0, leg=1.55, uarm=0.68, farm=0.70, sh=0.27,
                 torso=COAT, arm_col=COAT, leg_col=COAT, skin=SKIN_L, hand=GLOVE, hand_edge=None,
                 w0=0.072, w1=0.052, neck_w=0.17, mit_l=0.20, mit_w=0.13, shoe_l=0.30, ankle=0.07,
                 kind='level', shoe='oxford', min_w=10):
        self.D = D
        self.neck, self.yoke, self.spine = neck, yoke, spine
        self.ankle = ankle * D
        self.thigh = self.shin = (leg * D - self.ankle) / 2
        self.uarm, self.farm = uarm * D, farm * D
        self.sh = sh
        self.torso = torso
        self.arm_col, self.arm_far = arm_col, shade(arm_col, 0.14)
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

    # ---- skeleton
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
        """torso-local point: x in D across the shoulders, t along B->H (0..1)."""
        return add(add(J['B'], J['sp2'], x * self.D), J['tg2'], t * J['Lbh'])

    def tmat(self, J):
        sp, tg, B = J['sp2'], J['tg2'], J['B']
        return f'matrix({sp[0]:.4f},{sp[1]:.4f},{tg[0]:.4f},{tg[1]:.4f},{B[0]:.2f},{B[1]:.2f})'

    # ---- pieces
    def limb(self, p0, p1, p2, col):
        return capsule(p0, self.r0, p1, self.r1, col) + capsule(p1, self.r1, p2, self.r2, col)

    def hand_svg(self, W, h, far):
        kind = h.get('kind', 'mitten')
        if kind == 'none':
            return '', ''
        col = shade(self.hand, 0.08) if far else self.hand
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
        if edge:
            o.append(pill(b, e, Wm + 5, edge))
        o.append(pill(b, e, Wm, col))
        cid = uid('mc')
        o.append(f'<clipPath id="{cid}"><polygon points="{pstr(capsule_pts(b, Wm/2, e, Wm/2))}"/></clipPath>')
        cxm = (b[0] + e[0]) / 2
        o.append(f'<rect clip-path="url(#{cid})" x="{f(cxm + Wm*0.22)}" y="{f(min(b[1],e[1])-Wm)}" width="{f(Lm+Wm)}" height="{f(Lm+2*Wm)}" fill="{shade(col,0.08)}"/>')
        thumb = ''
        if th:
            ta = h.get('thumb_ang', a + th * 55)
            tb = add(add(W, u, 0.06 * self.D), p, th * Wm * 0.38)
            te = add(tb, dirv(ta), 0.075 * self.D)
            tw = 0.058 * self.D
            if edge:
                thumb += pill(tb, te, tw + 5, edge)
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
            o.append(f'<rect x="{f(-0.24*L)}" y="{f(s-hg*0.2)}" width="{f(1.0*L)}" height="{f(hg*0.2)}" fill="#000"/>')
            o.append(f'<ellipse cx="{f(0.54*L)}" cy="{f(s-hg*0.66)}" rx="{f(L*0.12)}" ry="{f(hg*0.13)}" fill="{IVORY}" opacity="0.85"/>')
        else:
            cid = uid('sp')
            path = (f'M{f(-0.22*L)},{f(s)} L{f(0.6*L)},{f(s)} Q{f(0.76*L)},{f(s-hg*0.05)} {f(0.86*L)},{f(s-hg*0.3)} '
                    f'Q{f(0.62*L)},{f(s-hg*0.86)} {f(0.32*L)},{f(s-hg*0.95)} L{f(0.08*L)},{f(s-hg*1.08)} '
                    f'Q{f(-0.22*L)},{f(s-hg*1.1)} {f(-0.22*L)},{f(s-hg*0.5)} Z')
            base = IVORY if not far else shade(IVORY, 0.1)
            o.append(f'<clipPath id="{cid}"><path d="{path}"/></clipPath>')
            o.append(f'<path d="{path}" fill="{base}"/>')
            o.append(f'<path clip-path="url(#{cid})" d="M{f(0.48*L)},{f(s+5)} Q{f(0.44*L)},{f(s-hg*0.6)} {f(0.56*L)},{f(s-hg*1.3)} L{f(L)},{f(s-hg*1.3)} L{f(L)},{f(s+5)} Z" fill="{SALMON}"/>')
            o.append(f'<path clip-path="url(#{cid})" d="M{f(0.1*L)},{f(s-hg*1.3)} L{f(0.36*L)},{f(s-hg*1.3)} L{f(0.32*L)},{f(s-hg*0.45)} L{f(0.12*L)},{f(s-hg*0.5)} Z" fill="{INK}"/>')
            o.append(f'<path clip-path="url(#{cid})" d="M{f(-0.3*L)},{f(s+5)} L{f(-0.3*L)},{f(s-hg*1.3)} L{f(-0.04*L)},{f(s-hg*1.3)} Q{f(-0.1*L)},{f(s-hg*0.5)} {f(0.0*L)},{f(s+5)} Z" fill="{INK}"/>')
            o.append(f'<rect x="{f(-0.22*L)}" y="{f(s-3)}" width="{f(1.0*L)}" height="3" fill="{INK}" opacity="0.6"/>')
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

    # ---- costume surface
    def torso_svg(self, J, face, pose):
        D = self.D
        t = face.get('turn', 0)
        a = min(abs(t) / 0.7, 1)
        s = 1 if t >= 0 else -1
        xk = 1 - 0.14 * a
        xs = 0.07 * t                      # front details shift toward the facing side
        Lbh = J['Lbh']
        yk = self.yoke * D / Lbh            # shoulder line as a fraction of B->H
        o = []
        if self.kind == 'level':
            prof = [(0, 0.10), (yk * 0.4, 0.22), (yk, 0.285), (yk + 0.08, 0.28), (0.30, 0.245), (0.50, 0.19), (0.60, 0.17)]
            pts = [(interp(prof, tt) * xk, tt) for tt in [i / 40 * 0.60 for i in range(41)]]
            poly = [(x, y) for x, y in pts] + [(-x, y) for x, y in pts[::-1]]
            coat = pstr([(x * D, y * Lbh) for x, y in poly])
            hip = [(0.15, 0.56), (0.11, 0.85), (0.085, 1.0), (-0.085, 1.0), (-0.11, 0.85), (-0.15, 0.56)]
            o.append(f'<polygon points="{pstr([(x*xk*D, y*Lbh) for x, y in hip])}" fill="{COAT_T}"/>')
            o.append(f'<polygon points="{coat}" fill="{self.torso}"/>')
            # satin lapels framing the white shirt front, which runs to a point at the waist
            bw = 0.085 * (1 - 0.15 * a)
            bib = [(xs - bw, 0.0), (xs + bw, 0.0), (xs + bw * 0.95, 0.40), (xs, 0.56), (xs - bw * 0.95, 0.40)]
            for sg in (-1, 1):
                lap = [(xs + sg * bw, 0.0), (xs + sg * 0.215 * xk, yk * 0.9), (xs + sg * 0.17 * xk, 0.22), (xs + sg * bw * 0.4, 0.58), (xs, 0.585)]
                o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in lap])}" fill="{SATIN}"/>')
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in bib])}" fill="{IVORY}"/>')
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in [(xs + bw*0.15, 0.0), (xs + bw, 0.0), (xs + bw*0.95, 0.40), (xs, 0.56), (xs + bw*0.2, 0.40)]])}" fill="{shade(IVORY, 0.08)}"/>')
            for ty in (0.17, 0.29, 0.41):
                o.append(f'<circle cx="{f(xs*D)}" cy="{f(ty*Lbh)}" r="{f(0.017*D)}" fill="{INK}"/>')
            # triangle pocket square on the wearer's left chest (+x)
            px = xs + 0.165 * xk - 0.03 * a * (1 if s < 0 else 0)
            py = 0.20
            sq = [(px - 0.05, py + 0.035), (px - 0.03, py - 0.04), (px - 0.005, py + 0.01), (px + 0.02, py - 0.045), (px + 0.05, py + 0.035)]
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in sq])}" fill="{IVORY}"/>')
            o.append(f'<line x1="{f((px-0.06)*D)}" y1="{f((py+0.035)*Lbh)}" x2="{f((px+0.06)*D)}" y2="{f((py+0.035)*Lbh)}" stroke="{SATIN}" stroke-width="{f(0.02*D)}" stroke-linecap="round"/>')
        elif self.kind == 'hasty':
            prof = [(0, 0.10), (yk * 0.4, 0.19), (yk, 0.235), (yk + 0.07, 0.225), (0.25, 0.205), (0.55, 0.20), (0.85, 0.21), (1.0, 0.215)]
            pts = [(interp(prof, tt) * xk, tt) for tt in [i / 40 for i in range(41)]]
            right = pts
            left = [(-x, y) for x, y in pts]
            bottom = [(xs + 0.07, 1.12), (xs, 1.03), (xs - 0.07, 1.12)]
            poly = right + bottom + left[::-1]
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in poly])}" fill="{self.torso}"/>')
            # shadow side of the vest (light from the left)
            shp = [(xs + 0.02, 0.38), (xs + 0.02, 1.04)] + [(x, y) for x, y in right[::-1] if y >= 0.38][::-1]
            shp = [(xs + 0.0, 0.38)] + [(x, y) for x, y in right if y >= 0.38] + [(xs + 0.07, 1.12), (xs, 1.03)]
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in shp])}" fill="{ENJI_D}" opacity="0.55"/>')
            # shirt V, tie
            vw = 0.10 * (1 - 0.1 * a)
            v = [(xs - vw, 0.0), (xs + vw, 0.0), (xs, 0.40)]
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in v])}" fill="{SHIRT}"/>')
            tie = [(xs - 0.022, 0.03), (xs + 0.022, 0.03), (xs + 0.03, 0.30), (xs, 0.36), (xs - 0.03, 0.30)]
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in tie])}" fill="{TIE}"/>')
            for ty in (0.47, 0.61, 0.75, 0.89):
                o.append(f'<circle cx="{f(xs*D)}" cy="{f(ty*Lbh)}" r="{f(0.022*D)}" fill="{GOLD}"/>')
            for sg in (-1, 1):
                wx = xs + sg * 0.12 * xk
                o.append(f'<line x1="{f((wx-0.045)*D)}" y1="{f(0.70*Lbh)}" x2="{f((wx+0.045)*D)}" y2="{f(0.70*Lbh)}" stroke="{ENJI_D}" stroke-width="{f(0.022*D)}" stroke-linecap="round"/>')
        elif self.kind == 'clerk':
            prof = [(0, 0.10), (yk, 0.26), (0.5, 0.22), (1.0, 0.2)]
            pts = [(interp(prof, tt), tt) for tt in [i / 30 for i in range(31)]]
            poly = pts + [(-x, y) for x, y in pts[::-1]]
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in poly])}" fill="{self.torso}"/>')
            o.append(f'<polygon points="{pstr([(x*D, y*Lbh) for x, y in [(-0.09, 0), (0.09, 0), (0, 0.3)]])}" fill="{IVORY}"/>')
        return f'<g transform="{self.tmat(J)}">' + ''.join(o) + '</g>'

    def anchor_svg(self, J, face, pose):
        D = self.D
        k = lambda v: v * D
        sw = J['sw']
        yk = self.yoke * D
        o = []
        if self.kind == 'level':
            wing = [(-k(0.15), yk * 0.5), (-k(0.09), -k(0.035)), (k(0.09), -k(0.035)), (k(0.15), yk * 0.5),
                    (k(0.035), k(0.10)), (0, k(0.12)), (-k(0.035), k(0.10))]
            o.append(f'<polygon points="{pstr(wing)}" fill="{IVORY}"/>')
            o.append(f'<polygon points="{pstr([(k(0.02), -k(0.035)), (k(0.09), -k(0.035)), (k(0.15), yk*0.5), (k(0.035), k(0.10)), (0, k(0.12))])}" fill="{shade(IVORY,0.1)}"/>')
            for s in (-1, 1):
                fold = [(s * k(0.06), -k(0.01)), (s * k(0.14), k(0.035)), (s * k(0.05), k(0.05))]
                o.append(f'<polygon points="{pstr(fold)}" fill="{shade(IVORY,0.2)}"/>')
            by = k(0.035)
            bw, bh = k(0.115), k(0.05)
            o.append(f'<polygon points="{f(0)},{f(by)} {f(-bw)},{f(by-bh)} {f(-bw)},{f(by+bh)}" fill="{INK}"/>')
            o.append(f'<polygon points="{f(0)},{f(by)} {f(bw)},{f(by-bh)} {f(bw)},{f(by+bh)}" fill="{INK}"/>')
            o.append(f'<rect x="{f(-k(0.03))}" y="{f(by-k(0.032))}" width="{f(k(0.06))}" height="{f(k(0.064))}" rx="{f(k(0.012))}" fill="{INK}"/>')
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

    def tails_svg(self, J, pose):
        t = pose.get('tails')
        if t is None or self.kind != 'level':
            return ''
        D = self.D
        p0 = self.local(J, t.get('x', 0.0), 0.56)
        sw_ = t.get('swing', 0)
        Lt = t.get('len', 0.85) * D
        p1 = add(p0, dirv(sw_), Lt)
        c = add(lerp(p0, p1, 0.5), dirv(sw_ + 90), t.get('lag', 0) * D)
        w0 = t.get('w', 0.26) * D
        left, right = ribbon_pts(p0, c, p1, w0, w0 * 0.3)
        notch = lerp(p1, lerp(p0, p1, 0.5), 0.2)
        pts = left + [add(left[-1], dirv(sw_), 0.05 * D), notch, add(right[-1], dirv(sw_), 0.05 * D)] + right[::-1]
        col = t.get('col', mix(COAT, '#000000', 0.25))
        return f'<polygon points="{pstr(pts)}" fill="{col}"/>'

    def watch_svg(self, J, pose):
        w = pose.get('watch')
        if not w or self.kind != 'hasty':
            return ''
        D = self.D
        t = 0.0
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
        o = [f'<path d="M{f(btn[0])},{f(btn[1])} Q{f(c[0])},{f(c[1])} {f(pos[0])},{f(pos[1])}" stroke="{GOLD}" '
             f'stroke-width="{f(0.03*D)}" fill="none" stroke-linecap="round" stroke-dasharray="0.1 {f(0.042*D)}"/>',
             f'<path d="M{f(btn[0])},{f(btn[1])} Q{f(c[0])},{f(c[1])} {f(pos[0])},{f(pos[1])}" stroke="{GOLD}" '
             f'stroke-width="{f(0.014*D)}" fill="none" stroke-linecap="round"/>']
        if w.get('watch', True):
            r = 0.075 * D
            o.append(f'<circle cx="{f(pos[0])}" cy="{f(pos[1])}" r="{f(r)}" fill="{GOLD}"/>')
            o.append(f'<circle cx="{f(pos[0])}" cy="{f(pos[1] - r - 0.02*D)}" r="{f(0.022*D)}" fill="{GOLD}"/>')
            o.append(f'<circle cx="{f(pos[0]-0.006*D)}" cy="{f(pos[1]+0.004*D)}" r="{f(r*0.72)}" fill="{IVORY}"/>')
            o.append(f'<line x1="{f(pos[0])}" y1="{f(pos[1])}" x2="{f(pos[0])}" y2="{f(pos[1]-r*0.5)}" stroke="{INK}" stroke-width="{f(0.014*D)}" stroke-linecap="round"/>')
            o.append(f'<line x1="{f(pos[0])}" y1="{f(pos[1])}" x2="{f(pos[0]+r*0.38)}" y2="{f(pos[1]+r*0.12)}" stroke="{INK}" stroke-width="{f(0.014*D)}" stroke-linecap="round"/>')
        return '\n'.join(o)

    # ---- layers
    def layers(self, J, face, pose):
        L = {k: '' for k in ('shadow', 'tails', 'legF', 'armF', 'torso', 'neck', 'anchor', 'legN',
                             'armN', 'prop', 'thumbs', 'front')}
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
                w = tray.get('w', 0.6) * self.D
                if not tray.get('hidden'):
                    L['prop'] += tray_cup(cx, bottom, w)
                J['tray'] = (cx, bottom, w)
            leg = pose.get('leg' + side, {})
            lfar = leg.get('far', side == far_side)
            lcol = self.leg_far if lfar else self.leg_col
            sv = self.limb(J['H' + side], J['K' + side], J['F' + side], lcol)
            sv += self.shoe_svg(J['F' + side], pose.get('foot' + side, {}), far=lfar)
            L['legF' if lfar else 'legN'] += sv
        L['tails'] = self.tails_svg(J, pose)
        L['torso'] = self.torso_svg(J, face, pose)
        L['neck'] = self.neck_svg(J)
        L['anchor'] = self.anchor_svg(J, face, pose)
        L['prop'] = self.watch_svg(J, pose) + L['prop']
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

    def draw(self, cx, cy, face, pose, marks=''):
        J = self.body.joints((cx, cy), face, pose)
        L = self.body.layers(J, face, pose)
        self.J = J
        head = self.head.draw(cx, cy, face)
        return '\n'.join([L['shadow'], L['armF'], L['tails'], L['legF'], L['legN'], L['torso'], L['neck'], L['anchor'],
                          head, L['armN'], L['prop'], L['thumbs'], L['front'], marks])


# =====================================================================
# CAST
# =====================================================================
LEVEL_P = dict(
    name='Mr. Level', skin=SKIN_L, shad=SHAD_L,
    hair='flattop', hair_col=SILVER, hair_shad=SILVER_D, hair_rise=0.12, deck_w=0.40,
    eye=dict(shape='capsule', W=0.36, H=0.30, gap=0.10, y=-0.04, lid=0.35, pupil=0.12,
             lid_th=0.036, bag=True, crow=True, lidtone=mix(SKIN_L, SHAD_L, 0.85)),
    brow=dict(shape='pill', W=0.30, H=0.095, gap=0.06, out=0.005),
    nose='long', mouth_y=0.315, lower='level', ear=1.0)

HASTY_P = dict(
    name='Hasty', skin=SKIN_H, shad=SHAD_H,
    hair='part', hair_col=HAIR_H, hair_shad='#0C0B0A', hair_rise=0.055,
    eye=dict(shape='round', W=0.32, H=0.32, gap=0.11, y=-0.035, lid=0.20, pupil=0.12,
             lid_th=0.036, socket=0.55, lidtone=mix(SKIN_H, SHAD_H, 0.8)),
    brow=dict(shape='comma', W=0.27, H=0.085, gap=0.06, tilt=-16, out=0.01),
    nose='pointy', mouth_y=0.315, lower='jowl', ear=0.92,
    glasses=dict(y=0.135, w=0.25, h=0.105, xk=0.9))

CLERK_P = dict(
    name='clerk', skin=SKIN_C, shad=SHAD_C,
    hair='bun', hair_col=HAIR_C, hair_shad=shade(HAIR_C, 0.15), hair_rise=0.22,
    eye=dict(shape='round', W=0.22, H=0.27, gap=0.14, y=-0.03, lid=0.70, pupil=0.10, lid_th=0.03,
             lidtone=mix(SKIN_C, SHAD_C, 0.8)),
    brow=dict(shape='pill', W=0.16, H=0.045, gap=0.05),
    nose='button', mouth_y=0.27, lower=None, ear=0.9)


def level_char(D):
    hd = Head(D, LEVEL_P)
    bd = Body(D, neck=0.20, yoke=0.06, spine=1.05, leg=1.65, uarm=0.71, farm=0.74, sh=0.27,
              torso=COAT, arm_col=COAT, leg_col=COAT_T, skin=SKIN_L, hand=GLOVE, hand_edge=GLOVE_EDGE,
              kind='level', shoe='oxford')
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
def L_NEUTRAL(turn=0.0):
    return dict(turn=turn, eyes=dict(lid=0.35, gaze=(0.0, -0.3)), browL={}, browR={},
                mouth=dict(type='flat', w=0.19))


def L_SURPRISED(head, turn=0.0):
    crest = -0.5 - LEVEL_P['hair_rise']
    eye_top = LEVEL_P['eye']['y'] - LEVEL_P['eye']['H'] / 2
    base = eye_top - LEVEL_P['brow']['gap'] - LEVEL_P['brow']['H'] / 2
    target = crest - 0.10 - LEVEL_P['brow']['H'] / 2
    dy = target - base
    return dict(turn=turn, eyes=dict(lid=0.0, pupil=0.10, gaze=(0.0, 0.0)),
                browL=dict(dy=dy, trail=crest + 0.01), browR=dict(dy=dy, trail=crest + 0.01),
                mouth=dict(type='gasp', w=0.30, h=0.20, dy=0.01))


def L_ANGRY(turn=0.0):
    return dict(turn=turn, eyes=dict(lid=0.56, gaze=(0.0, -1.0)),
                browL=dict(dy=0.035, tilt=16), browR=dict(dy=0.035, tilt=16), crease='anger',
                mouth=dict(type='grit', w=0.32, h=0.10, dy=0.0))


def L_SMUG(turn=0.0, side=1):
    # side: +1 = far brow on screen right lifts off
    d = dict(turn=turn, eyes=dict(lid=0.50, gaze=(0.75 * side, 0.6)),
             mouth=dict(type='curl', w=0.20, side='R' if side > 0 else 'L', curl=0.055, dx=0.03 * side))
    crest = -0.5 - LEVEL_P['hair_rise']
    eye_top = LEVEL_P['eye']['y'] - LEVEL_P['eye']['H'] / 2
    base = eye_top - LEVEL_P['brow']['gap'] - LEVEL_P['brow']['H'] / 2
    up = dict(dy=(crest - 0.07 - LEVEL_P['brow']['H'] / 2) - base, tilt=-5, trail=crest + 0.005, trail_n=2)
    d['browR' if side > 0 else 'browL'] = up
    d['browL' if side > 0 else 'browR'] = dict(dy=0.0, tilt=3)
    return d


def L_PANIC(turn=0.0):
    return dict(turn=turn, eyes=dict(lid=0.07, pupil=0.10, gaze=(0.0, 0.0),
                                     ghosts=[(-0.025, 0.0), (0.025, 0.0)]),
                browL=dict(dy=-0.05, tilt=-17, ghosts=[(-0.02, 0, -4), (0.02, 0, 4)]),
                browR=dict(dy=-0.05, tilt=-17, ghosts=[(-0.02, 0, 4), (0.02, 0, -4)]),
                mouth=dict(type='grimace', w=0.40, h=0.12), sweat=[(0.47, -0.25), (-0.45, -0.18, 0.8)])


def L_SIDEEYE(turn=0.0, side=-1):
    d = dict(turn=turn, eyes=dict(lid=0.56, gaze=(1.0 * side, -0.2)),
             mouth=dict(type='flat', w=0.17, dx=0.05 * side, tilt=0.012 * side))
    d['browL'] = dict(dy=0.012, tilt=0)
    d['browR'] = dict(dy=-0.075, tilt=-2)
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
        parts.append(f"{s}: w{e['w']:.3f} h{e['h']:.3f} top{e['top_below_skull']:.3f} ctr{e['cy']+0.5:.3f} lid{e['lid']:.2f} pup{e['pupil']:.3f}")
    if 'L' in st and 'R' in st:
        a, b = st['L'], st['R']
        x0 = min(a['cx'] - a['w'] / 2, b['cx'] - b['w'] / 2)
        x1 = max(a['cx'] + a['w'] / 2, b['cx'] + b['w'] / 2)
        gap = (b['cx'] - b['w'] / 2) - (a['cx'] + a['w'] / 2)
        parts.append(f'span {x1-x0:.3f} gap {gap:.3f} cluster ctr {(x0+x1)/2:+.3f}')
    extra = ''
    if H_stand:
        extra = f' | head {hd.D/H_stand*100:.1f}% of H, eye {hd.P["eye"]["H"]*hd.D/H_stand*100:.1f}% of H'
    print(f'  [{label}] D={hd.D:.0f} ' + ' | '.join(parts) + extra)


def svg_doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'<defs><filter id="blk" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" '
            f'values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></defs>\n'
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
    o = [f'<rect width="{W}" height="{H}" fill="{EMERALD}"/>']
    exprs = [('neutral', L_NEUTRAL(turn=-0.2)),
             ('surprised', None),
             ('angry', L_ANGRY(turn=0.0)),
             ('smug', L_SMUG(turn=0.35, side=1)),
             ('panic', L_PANIC(turn=0.0)),
             ('side-eye', L_SIDEEYE(turn=0.25, side=-1))]
    print('faces:')
    for i, (name, face) in enumerate(exprs):
        col, row = i % 3, i // 3
        cx = 180 + col * 360
        cy = 270 + row * 540
        ch = level_char(D)
        if face is None:
            face = L_SURPRISED(ch.head, turn=0.0)
        cell = uid('cell')
        o.append(f'<clipPath id="{cell}"><rect x="{col*360+6}" y="{row*540+6}" width="348" height="528" rx="18"/></clipPath>')
        g = [f'<rect x="{col*360+6}" y="{row*540+6}" width="348" height="528" rx="18" fill="{shade(EMERALD, 0.1)}"/>',
             lamp(cx, cy - 10, 200, 260, 0.42)]
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
    """map the measured raw extent [top, bottom] onto [floor - target, floor]."""
    c = None if raw else _calib(name)
    if not c:
        return fig
    top, bot = c['top'], c['bottom'] + 1
    k = target / (bot - top)
    return f'<g transform="translate({f(cx)},{floor}) scale({k:.5f}) translate({f(-cx)},{-bot})">{fig}</g>'


def build_hero(sil=False, raw=False):
    W, H, floor = 540, 1080, 1010
    face = dict(turn=-0.62, eyes=dict(lid=0.35, gaze=(-0.55, -0.2)), browL=dict(dy=-0.0), browR=dict(dy=-0.0),
                mouth=dict(type='flat', w=0.17))
    pose = dict(neck=-4, neck_off=0.07, spine=0, chest=0, curve=0.0, far='R',
                armL=dict(a1=14, a2=-152, far=False), handL=dict(kind='flat', ang=-94, thumb=-1, thumb_ang=175),
                armR=dict(a1=10, a2=-70, fore=0.35, far=True), handR=dict(kind='none'),
                tails=dict(swing=14, lag=-0.04, len=0.85, x=0.06),
                tray=dict(hand='L', w=0.6, at=0.6),
                footL=dict(dir=-1), footR=dict(dir=-1))
    ch, D, cy, F = fit_lineup(level_char, face, pose, 960, 'R', cx=290)
    cx = 290
    pose['legR'] = dict(foot=(F[0] + 0.03 * D, floor - ch.body.ankle), bend=1, far=True)
    pose['legL'] = dict(foot=(F[0] - 0.03 * D, floor - ch.body.ankle), bend=1, far=False)
    pose['footR'] = dict(dir=1, tilt=0)
    pose['footL'] = dict(dir=-1, tilt=0)
    o = [f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else LINE_BG}"/>']
    if not sil:
        o.append(f'<ellipse cx="{cx-10}" cy="{floor+3}" rx="110" ry="9" fill="#000" opacity="0.12"/>')
    fig = _fit_group(ch.draw(cx, cy, face, pose), 'hero', cx, 960, raw=raw)
    if sil:
        fig = f'<g filter="url(#blk)">{fig}</g>'
    o.append(fig)
    top = cy - ch.head.R - ch.head.top_extent(face)
    Hs = floor - (cy - ch.head.R)
    print(f'hero: D={D:.1f} soles {floor} hair top {top:.1f} total {floor-top:.1f}')
    eye_report(ch, 'hero', Hs)
    return svg_doc(W, H, '\n'.join(o))


def H_NEUTRAL(turn=-0.55):
    return dict(turn=turn, tilt=-3, red=0.35,
                eyes=dict(lid=0.20, lid_tilt=10, gaze=(-0.6, -0.5)),
                browL=dict(tilt=-16), browR=dict(tilt=-16),
                mouth=dict(type='zig', w=0.19, amp=0.016, n=4, dx=-0.01),
                glasses=dict(dy=0.0))


def build_partner(sil=False, raw=False):
    W, H, floor = 540, 1080, 1010
    face = H_NEUTRAL()
    TILT = 26
    pose = dict(neck=-12, neck_off=0.06, spine=15, chest=13, curve=0.0, far='R',
                armL=dict(a1=-30, a2=-150, far=False), handL=dict(ang=-150, thumb=-1, thumb_ang=150),
                armR=dict(a1=60, a2=-40, far=True), handR=dict(ang=-30, thumb=1),
                footL=dict(dir=-1, tilt=TILT), footR=dict(dir=-1, tilt=TILT - 4))
    cx = 290
    for it in range(2):
        hb = hasty_char(250)
        lift = shoe_drop(hb.body, TILT, -1) - hb.body.ankle
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
    # near hand holds the watch up at chin height, elbow out to the left
    S = J['SL']
    pose['armL'] = dict(hand=(S[0] - 0.50 * D, S[1] + 0.12 * D), bend=1, far=False)
    pose['handL'] = dict(ang=-150, thumb=1, thumb_ang=-100)
    # far hand on the hip, elbow out behind
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
    Jd = ch.J
    print(f'partner: D={D:.1f} soles {floor} hair top {top:.1f} total {floor-top:.1f} | elbowR x {Jd["ER"][0]:.0f} elbowL x {Jd["EL"][0]:.0f}')
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
    face = dict(turn=-0.35, eyes=dict(look=lk, lid=0.70), browL=dict(dy=-0.03, tilt=-6), browR=dict(dy=0.0),
                mouth=dict(type='flat', w=0.16))
    pose = dict(neck=-2, armL=dict(a1=-10, a2=90, upper=0.6, fore=0.6), armR=dict(a1=10, a2=-90, upper=0.6, fore=0.6),
                handL=dict(kind='none'), handR=dict(kind='none'), legL=dict(a1=0), legR=dict(a1=0))
    J = ch.joints(ccx, ccy, face, pose)
    L = ch.body.layers(J, face, pose)
    sc = uid('cs')
    g = [f'<clipPath id="{sc}"><rect x="0" y="0" width="1080" height="{f(ledge+2)}"/></clipPath>'
         f'<g clip-path="url(#{sc})">' + L['torso'] + L['neck'] + L['anchor'] + ch.head.draw(ccx, ccy, face) + '</g>']
    if not sil:
        g.append(f'<rect x="{f(x0-20)}" y="{f(ledge)}" width="{f(w+40)}" height="22" rx="5" fill="{IVORY}"/>'
                 f'<rect x="{f(x0-20)}" y="{f(ledge+17)}" width="{f(w+40)}" height="6" fill="{shade(IVORY,0.25)}"/>'
                 f'<rect x="{f(x0+18)}" y="{f(ledge+50)}" width="{f(w-36)}" height="{f(horizon-ledge-94)}" fill="none" '
                 f'stroke="{shade(GOLD,0.15)}" stroke-width="3" opacity="0.55"/>')
        # two clerk hands resting on the ledge
        for dx in (-0.32, 0.30):
            g.append(f'<ellipse cx="{f(ccx + dx*Dc)}" cy="{f(ledge - 4)}" rx="{f(0.1*Dc)}" ry="{f(0.06*Dc)}" fill="{SKIN_C}"/>')
    body = '\n'.join(g)
    if sil:
        body = f'<g filter="url(#blk)">{body}</g>'
    o.append(body)
    eye_report(ch, 'clerk')
    return '\n'.join(o)


SC = dict(lcx=335, DL=288, DH=264, hx=782, hy=718, floor=1600, booth_ledge=520)


def build_scene(sil=False):
    W, H = 1080, 1920
    horizon, floor_y, band = 1300, SC['floor'], 1640
    o = [f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else EMERALD}"/>']
    if not sil:
        o.append(f'<rect width="{W}" height="230" fill="{shade(EMERALD, 0.18)}"/>')
        o.append(f'<clipPath id="wall"><rect x="0" y="232" width="{W}" height="{horizon-232}"/></clipPath><g clip-path="url(#wall)">'
                 + lamp(330, 820, 460, 720, 0.42) + lamp(800, 950, 380, 600, 0.46) + '</g>')
        o.append(arch(320, 262, 500, horizon, 7))
        o.append(arch(890, 262, 300, horizon, 7))
        o.append(f'<rect x="0" y="228" width="{W}" height="4" fill="{GOLD}"/>')

    DL, DH = SC['DL'], SC['DH']
    LV = level_char(DL)
    HS = hasty_char(DH)
    lcx = SC['lcx']
    hx, hy = SC['hx'], SC['hy']

    # ---- Mr. Level: ramrod, heels together; tray flicked overhead on the far
    #      hand, near palm still up and EMPTY where the tray was.
    lv_face = L_SMUG(turn=0.55, side=1)
    lv_face['mouth'] = dict(type='curl', w=0.2, side='R', curl=0.05, dx=0.02)
    lv_pose = dict(neck=0, neck_off=-0.07, spine=-1, chest=-1, curve=0.0, far='L',
                   armL=dict(a1=-141, a2=-177, far=True), handL=dict(kind='mitten', ang=180, thumb=1, thumb_ang=140),
                   armR=dict(a1=30, a2=-170, far=False), handR=dict(kind='flat', ang=86, thumb=-1, thumb_ang=-150),
                   tails=dict(swing=-12, lag=0.03, len=0.86, x=-0.05),
                   tray=dict(hand='L', w=0.6, at='tip'))
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
    tw = 0.6 * DL
    cup_y = tray_top[1] - 0.25 * DL                       # the cup itself
    lv_face['eyes'] = dict(lid=0.46, look=((hx - lcx) / DL, (hy - lcy) / DL))

    # ---- Hasty: lunging leap; hand closes on the ghost, eyes already on the real cup
    hs_face = dict(turn=-0.5, tilt=7, red=1.0,
                   eyes=dict(lid=0.08, look=((tray_top[0] - hx) / DH, (cup_y - hy) / DH)),
                   browL=dict(dy=-0.04, tilt=-26), browR=dict(dy=-0.04, tilt=-26),
                   mouth=dict(type='aah', w=0.32, h=0.15, dy=0.0),
                   glasses=dict(dy=-0.03, rot=-7),
                   sweat=[(0.52, -0.30), (0.62, -0.08, 0.75)])
    grab = (ghost_c[0] + 0.10 * DL, ghost_c[1] - 0.16 * DL)
    hs_pose = dict(neck=-14, neck_off=0.05, spine=22, chest=19, curve=0.0, far='R', sh_k=1.05,
                   armL=dict(hand=grab, bend=1, far=False), handL=dict(ang=-118, thumb=1, thumb_ang=-60),
                   armR=dict(a1=45, a2=-28, far=True), handR=dict(ang=-28, thumb=-1),
                   footL=dict(dir=-1, tilt=60), footR=dict(dir=-1, tilt=50))
    Jh = HS.joints(hx, hy, hs_face, hs_pose)
    sole = floor_y - 150
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

    o.append(clerk_booth(890, 262, 300, SC['booth_ledge'], horizon, look=(tray_top[0], cup_y), sil=sil))

    marks = ''
    if not sil:
        marks += tray_ghost(ghost_c[0], ghost_c[1], tw, op=0.42)
        S0 = (ghost_c[0] + 0.15 * tw, ghost_c[1] - 0.62 * DL)
        E0 = (tray_top[0] + 0.52 * tw, cup_y - 0.12 * DL)
        C0 = (S0[0] + 0.25 * DL, min(S0[1], E0[1]) - 0.95 * DL)
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
    print('scene:')
    Hs = floor_y - (lcy - DL / 2)
    eye_report(LV, 'level', Hs)
    eye_report(HS, 'hasty')
    print(f'  level head ({lcx},{lcy:.0f}) skull top {lcy-DL/2:.0f} hair top {lcy-DL/2-LV.head.top_extent():.0f} tray top ({tray_top[0]:.0f},{tray_top[1]:.0f}) '
          f'elbowL ({J1["EL"][0]:.0f},{J1["EL"][1]:.0f}) palm {tuple(round(v) for v in palm)} | hasty soles {max(HS.J["FL"][1], HS.J["FR"][1]) + HS.body.ankle:.0f} '
          f'hair top {hy - DH/2 - HS.head.top_extent():.0f} elbowR x {HS.J["ER"][0]:.0f} handR x {HS.J["WR"][0]:.0f} kneeR x {HS.J["KR"][0]:.0f} footR x {HS.J["FR"][0]:.0f}')
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
