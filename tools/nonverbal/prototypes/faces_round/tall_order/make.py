#!/usr/bin/env python3
"""Tall Order -- ROUND heads on stick bodies.

One round-head face rig (Head: pill brows over dash eyes, sliding mouth,
static nose wedge) and one stick-body rig (Body: neck stub, wing-collar
anchor, tapered spine, pill limbs, mittens, shoes).  Char = Body + Head.
scene.svg, poses.svg and lineup.svg are all built from the same rigs.

Units: proportions are fractions of D = skull diameter (no ears / hair).
Line language: flat fills, NO outlines, round pill ends, light from the
left, so every head has a flat shadow crescent on its right/lower rim.
"""
import math, os, sys

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
SKIN_L, SHAD_L = '#B07A55', '#9B6A4A'      # Mr. Level
SKIN_H, SHAD_H = '#E8B996', '#CF9F7D'      # Hasty
SKIN_C = '#6B4430'                          # Clerk
SHAD_C = '#5A3828'
SILVER, SILVER_D = '#B9B4AC', '#A29D95'
COAT = '#24211F'
BRICK = '#5E2A20'        # deep oxblood brick, HSL lightness 25 % (contrast on emerald)
TRAY = '#C9C4B8'
TEA = '#8A4B2A'
MOUTH_IN = '#3A1E1A'
GLOVE, GLOVE_EDGE = IVORY, '#CFC6B4'
PATENT = '#121212'
EYE_WHITE = '#FBF8F1'

_uid = [0]
PROBES = []          # (label, colour, p0, p1, half width) for the contrast check


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
    """two-bone IK.  bend=+1 puts the joint on the screen-right of a downward limb."""
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


def star4(x, y, r, fill=IVORY, op=1.0):
    k = r * 0.22
    pts = [(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)]
    return f'<polygon points="{pstr(pts)}" fill="{fill}" opacity="{op}"/>'


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


# =====================================================================
# ROUND HEAD RIG
# =====================================================================
class Head:
    """A true circle of diameter D, flat skin, flat shadow crescent on the
    right/lower rim (light from the left), ears, hair break, nose wedge.
    Face system (unchanged from Tall Order): pill-slab brows that move on
    their own over vertical dash eyes, one sliding mouth stroke."""

    def __init__(self, D, skin, shad, hair='level', hair_col=SILVER, hair_shad=SILVER_D,
                 brow_col=INK, mustache=False, eye_min=12.0, ear_col=None):
        self.D, self.R = D, D / 2
        self.skin, self.shad = skin, shad
        self.hair, self.hair_col, self.hair_shad = hair, hair_col, hair_shad
        self.brow_col = brow_col
        self.mustache = mustache
        self.eye_min = eye_min

    # ---- geometry helpers (head-local, origin = skull centre)
    def k(self, v):
        return v * self.D

    def rim_y(self, x):
        R = self.R
        return -math.sqrt(max(R * R - x * x, 0))

    def top_extent(self, face):
        """how far the hair rises above the skull top (px)."""
        if self.hair == 'level':
            return self.k(0.12)
        if self.hair == 'slick':
            return self.k(0.035)
        return 0

    # ---- pieces
    def ears(self, t):
        D, R = self.D, self.R
        out = []
        for s in (-1, 1):
            front = s * t > 0.15
            kx = 1 - 0.5 * abs(t) if front else 1.0
            rx, ry = 0.06 * D * kx, 0.08 * D
            prot = 0.065 * D * kx
            cx = s * (R + prot - rx)
            cy = -0.02 * D
            if s < 0:
                col, inner = self.skin, self.shad
            else:
                col, inner = self.shad, shade(self.shad, 0.16)
            out.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{col}"/>')
            out.append(f'<ellipse cx="{f(cx + s*rx*0.25)}" cy="{f(cy + ry*0.08)}" rx="{f(rx*0.48)}" ry="{f(ry*0.55)}" fill="{inner}"/>')
        return out

    def hair_level(self, t, clip):
        """silver cap over the top 24 %, sharp side-part notch at the left,
        a short wave/crest rising above the rim at the part, silver temples
        down to the ears."""
        k, R = self.k, self.R
        xp = k(-0.20 + 0.05 * t)
        eyt = k(-0.10)                       # ear top
        ri = R - k(0.065)                    # inner edge of temple strip
        yh = k(-0.265)
        xa = -math.sqrt(ri * ri - eyt * eyt)
        xb = -math.sqrt(ri * ri - yh * yh)
        xo = math.sqrt(R * R - eyt * eyt)
        inner = (f'M{f(-R-20)},{f(eyt)} L{f(-xo)},{f(eyt)} L{f(xa)},{f(eyt)} '
                 f'A{f(ri)},{f(ri)} 0 0 1 {f(xb)},{f(yh)} '
                 f'Q{f((xb+xp)/2)},{f(yh-k(0.005))} {f(xp-k(0.03))},{f(yh-k(0.01))} '
                 f'L{f(xp-k(0.004))},{f(k(-0.40))} L{f(xp+k(0.035))},{f(yh-k(0.015))} '
                 f'Q{f(k(0.12))},{f(yh+k(0.03))} {f(-xb)},{f(yh)} '
                 f'A{f(ri)},{f(ri)} 0 0 1 {f(-xa)},{f(eyt)} L{f(xo)},{f(eyt)} L{f(R+20)},{f(eyt)} '
                 f'L{f(R+20)},{f(-R-40)} L{f(-R-20)},{f(-R-40)} Z')
        # crest / wave above the rim (unclipped), sharp at the part, sloping right
        ytip = self.rim_y(xp) - k(0.12)
        xr = k(0.33)
        crest = (f'M{f(xp-k(0.012))},{f(self.rim_y(xp-k(0.012))+k(0.03))} L{f(xp-k(0.012))},{f(self.rim_y(xp-k(0.012))+k(0.01))} '
                 f'L{f(xp+k(0.004))},{f(ytip)} '
                 f'C{f(xp+k(0.09))},{f(ytip-k(0.005))} {f(k(0.14))},{f(-R-k(0.06))} {f(xr)},{f(self.rim_y(xr)+k(0.012))} '
                 f'L{f(xr-k(0.05))},{f(self.rim_y(xr-k(0.05))+k(0.05))} L{f(xp+k(0.03))},{f(self.rim_y(xp+k(0.03))+k(0.045))} Z')
        # two flat comb grooves sweeping back from the part (hair, not a cap)
        grooves = ''
        for j, (y0, y1, y2) in enumerate(((-0.36, -0.47, -0.30), (-0.30, -0.38, -0.24))):
            gx0 = xp + k(0.06 + 0.02 * j)
            grooves += (f'<path clip-path="url(#{clip})" d="M{f(gx0)},{f(k(y0))} Q{f(k(0.12))},{f(k(y1))} {f(k(0.40))},{f(k(y2))}" '
                        f'stroke="{shade(self.hair_col, 0.14)}" stroke-width="{f(k(0.018))}" stroke-linecap="round" fill="none"/>')
        return [f'<path clip-path="url(#{clip})" d="{inner}"/>', f'<path d="{crest}"/>', grooves]

    def hair_slick(self, t, clip):
        """slick black cap, sideburns to the ears, a forward wave jutting
        0.06 D at the front-top (front = facing side)."""
        k, R = self.k, self.R
        s = -1 if t < 0 else 1               # facing side
        eyt = k(-0.10)
        ri = R - k(0.055)
        yh = k(-0.335)
        xa = math.sqrt(ri * ri - eyt * eyt)
        xb = math.sqrt(ri * ri - yh * yh)
        xo = math.sqrt(R * R - eyt * eyt)
        inner = (f'M{f(-R-20)},{f(eyt)} L{f(-xa)},{f(eyt)} '
                 f'A{f(ri)},{f(ri)} 0 0 1 {f(-xb)},{f(yh)} '
                 f'Q0,{f(yh+k(0.035))} {f(xb)},{f(yh)} '
                 f'A{f(ri)},{f(ri)} 0 0 1 {f(xa)},{f(eyt)} L{f(R+20)},{f(eyt)} '
                 f'L{f(R+20)},{f(-R-40)} L{f(-R-20)},{f(-R-40)} Z')
        # forward wave: a rolled lobe outside the rim at about 125 deg (front side)
        pts = []
        a0, a1 = math.radians(-165), math.radians(-98)
        for i in range(13):
            a = a0 + (a1 - a0) * i / 12
            bump = math.sin(math.pi * i / 12) ** 0.7
            r = R + k(0.062) * bump
            pts.append((r * math.cos(a), r * math.sin(a)))
        for i in range(12, -1, -1):
            a = a0 + (a1 - a0) * i / 12
            r = R - k(0.07)
            pts.append((r * math.cos(a), r * math.sin(a)))
        if s > 0:
            pts = [(-x, y) for x, y in pts]
        wave = f'<polygon points="{pstr(pts)}"/>'
        # one combed-back groove line (flat, not a gloss band)
        g0 = (s * -0.30 * self.D, -0.36 * self.D)
        g1 = (s * 0.10 * self.D, -0.47 * self.D)
        g2 = (s * 0.38 * self.D, -0.27 * self.D)
        groove = (f'<path clip-path="url(#{clip})" d="M{f(g0[0])},{f(g0[1])} Q{f(g1[0])},{f(g1[1])} {f(g2[0])},{f(g2[1])}" '
                  f'stroke="#3A3532" stroke-width="{f(0.02*self.D)}" stroke-linecap="round" fill="none"/>')
        return [f'<path clip-path="url(#{clip})" d="{inner}"/>', wave, groove]

    def hair_tufts(self, t, clip):
        """bald top; ivory side tufts protruding 0.08 D above the ears."""
        k, R = self.k, self.R
        out = []
        for s in (-1, 1):
            pts = []
            a0, a1 = math.radians(-148), math.radians(-192)
            n = 18
            for i in range(n + 1):
                a = a0 + (a1 - a0) * i / n
                bump = math.sin(math.pi * i / n) ** 0.6
                scal = 0.62 + 0.38 * abs(math.cos(math.pi * i * 3 / n))
                r = R + k(0.085) * bump * scal
                pts.append((r * math.cos(a), r * math.sin(a)))
            for i in range(n, -1, -1):
                a = a0 + (a1 - a0) * i / n
                r = R - k(0.05)
                pts.append((r * math.cos(a), r * math.sin(a)))
            if s > 0:
                pts = [(-x, y) for x, y in pts]
            out.append(f'<polygon points="{pstr(pts)}"/>')
        return out

    def brow(self, side, b, fx, fy):
        if b is None:
            return ''
        k = self.k
        s = -1 if side == 'L' else 1
        w = k(b.get('w', 0.34))
        h = k(b.get('h', 0.09))
        bx = fx + s * k(0.19) + k(b.get('dx', 0))
        by = k(-0.215) + fy + k(b.get('dy', 0))
        tilt = b.get('tilt', 0)          # + = inner end down
        r = tilt if side == 'L' else -tilt
        col = b.get('col', self.brow_col)
        out = []
        if b.get('trail'):               # dashed ticks below a floating brow
            y_top = by + h / 2 + k(0.05)
            y_bot = b['trail']           # absolute head-local y where the trail ends
            n = b.get('trail_n', 3)
            seg = (y_bot - y_top) / n
            tw = max(k(0.024), 5)
            for i in range(n):
                y0 = y_top + i * seg + seg * 0.15
                y1 = y0 + seg * 0.55
                out.append(f'<line x1="{f(bx)}" y1="{f(y0)}" x2="{f(bx)}" y2="{f(y1)}" stroke="{col}" '
                           f'stroke-width="{f(tw)}" stroke-linecap="round" opacity="{f(0.85-0.18*i)}"/>')
        for g in b.get('ghosts', []):
            gx, gy, gt = (list(g) + [0])[:3]
            gr = (tilt + gt) if side == 'L' else -(tilt + gt)
            out.append(f'<rect x="{f(-w/2)}" y="{f(-h/2)}" width="{f(w)}" height="{f(h)}" rx="{f(h/2)}" fill="{col}" opacity="0.3" '
                       f'transform="translate({f(bx+k(gx))},{f(by+k(gy))}) rotate({f(gr)})"/>')
        out.append(f'<rect x="{f(-w/2)}" y="{f(-h/2)}" width="{f(w)}" height="{f(h)}" rx="{f(h/2)}" fill="{col}" '
                   f'transform="translate({f(bx)},{f(by)}) rotate({f(r)})"/>')
        nt = b.get('ticks', 0)
        if nt:
            tx, ty = rot(s * w / 2, 0, r)
            tx += bx; ty += by
            base = 0 if s > 0 else 180
            angs = [-20, -55, 15][:nt]
            angs = [(base + a if s > 0 else base - a) + r for a in angs]
            for i, a in enumerate(angs):
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                out.append(f'<line x1="{f(tx+ca*k(0.05))}" y1="{f(ty+sa*k(0.05))}" x2="{f(tx+ca*k(0.12))}" y2="{f(ty+sa*k(0.12))}" '
                           f'stroke="{col}" stroke-width="{f(max(k(0.022),4))}" stroke-linecap="round" opacity="{f(1-0.3*i)}"/>')
        return '\n'.join(out)

    def eyes(self, e, fx, fy):
        k = self.k
        st = e.get('state', 'dash')
        sep = k(e.get('sep', 0.24))
        dx, dy = k(e.get('dx', 0)), k(e.get('dy', 0))
        out = []
        for s in (-1, 1):
            x = fx + s * sep / 2 + dx
            y = k(-0.02) + fy + dy
            for g in e.get('ghosts', []):
                out.append(self._eye(st, x + k(g[0]), y + k(g[1]), e, op=0.3))
            out.append(self._eye(st, x, y, e))
        return '\n'.join(out)

    def _eye(self, st, x, y, e, op=1.0):
        k = self.k
        o = '' if op == 1 else f' opacity="{op}"'
        if st == 'dash':
            w = max(k(e.get('w', 0.048)), self.eye_min)
            h = k(e.get('h', 0.16))
            lid = e.get('lid', 0)
            if lid:
                y0 = y - h / 2 + lid * h
                r = w / 2
                d = (f'M{f(x-w/2)},{f(y0)} L{f(x+w/2)},{f(y0)} L{f(x+w/2)},{f(y+h/2-r)} '
                     f'A{f(r)},{f(r)} 0 0 1 {f(x-w/2)},{f(y+h/2-r)} Z')
                return f'<path d="{d}" fill="{INK}"{o}/>'
            return f'<rect x="{f(x-w/2)}" y="{f(y-h/2)}" width="{f(w)}" height="{f(h)}" rx="{f(w/2)}" fill="{INK}"{o}/>'
        if st == 'dot':
            r = max(k(e.get('size', 0.07)) / 2, self.eye_min * 0.6)
            return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{INK}"{o}/>'
        if st == 'open':
            R = k(0.09)
            px, py = e.get('pupil', (0, 0))
            return (f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(R)}" fill="{EYE_WHITE}"{o}/>'
                    f'<circle cx="{f(x+k(px))}" cy="{f(y+k(py))}" r="{f(k(0.0275))}" fill="{INK}"{o}/>')
        return ''

    def mouth(self, m, fx, fy):
        k = self.k
        t = m.get('type', 'flat')
        x = fx + k(m.get('dx', 0))
        y = k(0.26) + fy + k(m.get('dy', 0))
        w = k(m.get('w', 0.22))
        th = max(k(m.get('th', 0.04)), 6)
        st = f'stroke="{INK}" stroke-width="{f(th)}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
        if t == 'flat':
            return f'<line x1="{f(x-w/2)}" y1="{f(y)}" x2="{f(x+w/2)}" y2="{f(y)}" {st}/>'
        if t == 'curl':
            c = k(m.get('curl', 0.06))
            s = 1 if m.get('side', 'R') == 'R' else -1
            a, b = x - s * w / 2, x + s * w / 2
            kx = x + s * w * 0.18
            return f'<path d="M{f(a)},{f(y)} L{f(kx)},{f(y)} Q{f(b)},{f(y)} {f(b + s*k(0.008))},{f(y-c)}" {st}/>'
        if t in ('o', 'tall_o'):
            rx = k(m.get('rx', 0.045 if t == 'o' else 0.052))
            ry = k(m.get('ry', 0.05 if t == 'o' else 0.085))
            return (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rx)}" ry="{f(ry)}" fill="{INK}"/>'
                    f'<ellipse cx="{f(x)}" cy="{f(y+ry*0.12)}" rx="{f(rx-th*0.55)}" ry="{f(ry-th*0.6)}" fill="{MOUTH_IN}"/>')
        if t == 'zig':
            a = k(m.get('amp', 0.035))
            pts = [(x - w / 2, y), (x - w / 4, y - a), (x, y + a), (x + w / 4, y - a), (x + w / 2, y)]
            return f'<polyline points="{pstr(pts)}" {st}/>'
        if t == 'frown':
            a = k(m.get('amp', 0.05))
            return f'<path d="M{f(x-w/2)},{f(y+a*0.5)} Q{f(x)},{f(y-a*1.3)} {f(x+w/2)},{f(y+a*0.5)}" {st}/>'
        if t == 'take':
            W2, H2 = k(0.4), k(0.16)
            return (f'<rect x="{f(x-W2/2)}" y="{f(y-H2/2)}" width="{f(W2)}" height="{f(H2)}" rx="{f(k(0.03))}" fill="{MOUTH_IN}"/>'
                    f'<rect x="{f(x-W2/2+k(0.02))}" y="{f(y-H2/2+k(0.015))}" width="{f(W2-k(0.04))}" height="{f(H2*0.28)}" rx="{f(k(0.01))}" fill="{IVORY}"/>')
        return ''

    def nose(self, fx, fy):
        k = self.k
        x = fx + k(0.03)
        y = k(0.10) + fy
        return (f'<polygon points="{f(x)},{f(y-k(0.06))} {f(x+k(0.07))},{f(y+k(0.06))} {f(x)},{f(y+k(0.06))}" '
                f'fill="{self.shad}"/>')

    def stache(self, fx, fy):
        k = self.k
        y = k(0.19) + fy
        th = max(k(0.035), 7)
        o = []
        for s in (-1, 1):
            o.append(f'<path d="M{f(fx+s*k(0.012))},{f(y)} Q{f(fx+s*k(0.08))},{f(y+k(0.014))} {f(fx+s*k(0.145))},{f(y-k(0.018))}" '
                     f'stroke="{INK}" stroke-width="{f(th)}" stroke-linecap="round" fill="none"/>')
        return ''.join(o)

    def extras(self, face):
        k = self.k
        o = []
        if face.get('sweat'):
            sx, sy = (k(v) for v in face['sweat'])
            r = k(0.04)
            o.append(f'<path d="M{f(sx)},{f(sy-r*2.4)} Q{f(sx+r*1.1)},{f(sy-r*0.4)} {f(sx+r)},{f(sy+r*0.2)} '
                     f'A{f(r)},{f(r)} 0 1 1 {f(sx-r)},{f(sy+r*0.2)} Q{f(sx-r*1.1)},{f(sy-r*0.4)} {f(sx)},{f(sy-r*2.4)} Z" fill="{IVORY}"/>')
        return '\n'.join(o)

    # ---- whole head
    def draw(self, cx, cy, face):
        k, R, D = self.k, self.R, self.D
        t = face.get('turn', 0.0)
        fx = k(face.get('fx', t * 0.13))
        fy = k(face.get('fy', 0.0))
        sq = face.get('squash', 0.0)
        clip, msk = uid('hc'), uid('hm')
        o = []
        o.append(f'<clipPath id="{clip}"><circle r="{f(R)}"/></clipPath>')
        o.append(f'<mask id="{msk}" maskUnits="userSpaceOnUse" x="{f(-2*R)}" y="{f(-3*R)}" width="{f(4*R)}" height="{f(5*R)}">'
                 f'<rect x="{f(-2*R)}" y="{f(-3*R)}" width="{f(4*R)}" height="{f(5*R)}" fill="#fff"/>'
                 f'<circle cx="{f(k(-0.13))}" cy="{f(k(-0.085))}" r="{f(R)}" fill="#000"/></mask>')
        o += self.ears(t)
        o.append(f'<circle r="{f(R)}" fill="{self.skin}"/>')
        o.append(f'<circle r="{f(R)}" fill="{self.shad}" mask="url(#{msk})"/>')
        hp = {'level': self.hair_level, 'slick': self.hair_slick, 'tufts': self.hair_tufts}[self.hair](t, clip)
        o.append(f'<g fill="{self.hair_col}">' + ''.join(hp) + '</g>')
        o.append(f'<g fill="{self.hair_shad}" mask="url(#{msk})">' + ''.join(hp) + '</g>')
        feats = [self.nose(fx, fy),
                 self.eyes(face.get('eyes', {}), fx, fy),
                 self.stache(fx, fy) if self.mustache else '',
                 self.mouth(face.get('mouth', {}), fx, fy),
                 self.brow('L', face.get('browL', {}), fx, fy),
                 self.brow('R', face.get('browR', {}), fx, fy)]
        tl = face.get('tilt', 0)
        o.append(f'<g transform="rotate({f(tl)})">' + '\n'.join(feats) + '</g>')
        o.append(self.extras(face))
        tr = f'translate({f(cx)},{f(cy)})'
        if sq:
            tr += f' scale({f(1+sq)},{f(1-sq)})'
        return f'<g transform="{tr}">\n' + '\n'.join(o) + '\n</g>'


# =====================================================================
# STICK BODY RIG
# =====================================================================
def tray_cup(cx, bottom, w):
    """silver tray + saucer + brim-full cup.  bottom = y of tray underside."""
    s = w / 216
    ty = bottom - 25 * s + 4 * s
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
    """flat one-colour silhouette of tray + cup (motion ghost)."""
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


class Body:
    def __init__(self, D, neck=0.15, yoke=0.06, spine=1.0, leg=1.55, uarm=0.68, farm=0.70, sh=0.27,
                 col=COAT, skin=SKIN_L, hand=GLOVE, hand_edge=None, w0=0.072, w1=0.052,
                 sp0=0.08, sp1=0.06, neck_w=0.17, mit_l=0.20, mit_w=0.13, shoe_l=0.30, ankle=0.07,
                 kind='level', shoe='oxford', ring=False, min_w=12):
        self.D = D
        self.neck, self.yoke, self.spine = neck, yoke, spine
        self.ankle = ankle * D
        self.thigh = self.shin = (leg * D - self.ankle) / 2
        self.uarm, self.farm = uarm * D, farm * D
        self.sh = sh
        self.col, self.far_col = col, shade(col, 0.12)
        self.skin = skin
        self.hand, self.hand_edge = hand, hand_edge
        self.r0 = max(w0 * D, min_w) / 2
        self.r2 = max(w1 * D, min_w) / 2
        self.r1 = (self.r0 + self.r2) / 2
        self.sp0, self.sp1 = max(sp0 * D, min_w + 2), max(sp1 * D, min_w)
        self.neck_w = neck_w * D
        self.mit_l, self.mit_w = mit_l * D, mit_w * D
        self.shoe_l = shoe_l * D
        self.kind, self.shoe, self.ring = kind, shoe, ring

    # ---- skeleton
    def joints(self, C, face, pose):
        D, R = self.D, self.D / 2
        t = face.get('turn', 0)
        na = pose.get('neck', 0.0)
        u = (math.sin(math.radians(na)), -math.cos(math.radians(na)))      # up the neck
        n = (-u[1], u[0])
        o = pose.get('neck_off', -0.10 * t) * D
        Q = add(C, n, o)
        se = math.sqrt(max(R * R - o * o, 1))
        E = add(Q, u, -se)                     # where the neck enters the skull
        B = add(E, u, -self.neck * D)          # neck base (collar top)
        top = add(E, u, 0.07 * D)              # tucked inside the head
        sa = pose.get('spine', 0.0)
        ch = pose.get('chest', sa)
        Y = add(B, dirv(ch), self.yoke * D)
        Hp = add(Y, dirv(sa), self.spine * D)
        dv = dirv(sa)
        perp = (dv[1], -dv[0])
        Cc = add(lerp(Y, Hp, 0.5), perp, pose.get('curve', 0) * D)
        tg = norm(sub(Cc, Y))
        sp = (tg[1], -tg[0])
        sw = self.sh * D * pose.get('sh_k', 1 - 0.22 * abs(t))
        J = dict(C=C, u=u, E=E, B=B, top=top, Y=Y, H=Hp, Cc=Cc, tg=tg, sp=sp, sw=sw)
        J['SL'], J['SR'] = add(Y, sp, -sw), add(Y, sp, sw)
        tgh = norm(sub(Hp, Cc))
        sph = (tgh[1], -tgh[0])
        J['tgh'], J['sph'] = tgh, sph
        J['HL'], J['HR'] = add(Hp, sph, -0.03 * D), add(Hp, sph, 0.03 * D)
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

    # ---- pieces
    def limb(self, p0, p1, p2, col, label):
        if self.kind != 'clerk':
            PROBES.append((self.kind + ' ' + label, col, p0, p1, self.r0))
            PROBES.append((self.kind + ' ' + label, col, p1, p2, self.r2))
        return capsule(p0, self.r0, p1, self.r1, col) + capsule(p1, self.r1, p2, self.r2, col)

    def hand_svg(self, W, h, far):
        """returns (hand svg, thumb svg).  kinds: mitten | flat | none."""
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
            o.append(pill(b, e, Wm + 6, edge))
        o.append(pill(b, e, Wm, col))
        # shadow-side tone on the right half (light from the left)
        cid = uid('mc')
        o.append(f'<clipPath id="{cid}"><polygon points="{pstr(capsule_pts(b, Wm/2, e, Wm/2))}"/></clipPath>')
        cxm = (b[0] + e[0]) / 2
        o.append(f'<rect clip-path="url(#{cid})" x="{f(cxm + Wm*0.22)}" y="{f(min(b[1],e[1])-Wm)}" width="{f(Lm+Wm)}" height="{f(Lm+2*Wm)}" fill="{shade(col,0.08)}"/>')
        if self.ring:
            rp = add(add(e, p, -th * Wm * 0.32), u, -Wm * 0.15)
            o.append(f'<circle cx="{f(rp[0])}" cy="{f(rp[1])}" r="{f(max(Wm*0.14, 4))}" fill="{GOLD}"/>')
        thumb = ''
        if th:
            ta = h.get('thumb_ang', a + th * 55)
            tb = add(add(W, u, 0.06 * self.D), p, th * Wm * 0.38)
            te = add(tb, dirv(ta), 0.075 * self.D)
            tw = 0.058 * self.D
            if edge:
                thumb += pill(tb, te, tw + 6, edge)
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
        else:   # spectator: pointed, ivory body, black heel + saddle, salmon toe cap
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

    def spine_svg(self, J):
        B, Y, Cc, H = J['B'], J['Y'], J['Cc'], J['H']
        left, right = ribbon_pts(B, lerp(B, Cc, 0.6), H, self.sp0, self.sp1)
        o = [f'<polygon points="{pstr(left + right[::-1])}" fill="{self.col}"/>',
             f'<circle cx="{f(H[0])}" cy="{f(H[1])}" r="{f(self.sp1/2)}" fill="{self.col}"/>']
        return ''.join(o)

    def neck_svg(self, J):
        B, top, E, u = J['B'], J['top'], J['E'], J['u']
        w = self.neck_w
        n = (-u[1], u[0])
        b0 = add(B, u, -0.02 * self.D)
        quad = [add(b0, n, -w / 2), add(top, n, -w / 2), add(top, n, w / 2), add(b0, n, w / 2)]
        sh = [add(b0, n, w * 0.18), add(top, n, w * 0.18), add(top, n, w / 2), add(b0, n, w / 2)]
        cb = add(E, u, -0.055 * self.D)
        chin = [add(cb, n, -w / 2), add(top, n, -w / 2), add(top, n, w / 2), add(cb, n, w / 2)]
        d = shade(self.skin, 0.12)
        return (f'<polygon points="{pstr(quad)}" fill="{self.skin}"/>'
                f'<polygon points="{pstr(sh)}" fill="{mix(self.skin, d, 0.6)}"/>'
                f'<polygon points="{pstr(chin)}" fill="{d}"/>')

    def frame(self, J):
        """matrix mapping local (x along shoulders, y down the spine) at B."""
        sp, tg, B = J['sp'], J['tg'], J['B']
        return f'matrix({sp[0]:.4f},{sp[1]:.4f},{tg[0]:.4f},{tg[1]:.4f},{B[0]:.2f},{B[1]:.2f})'

    def anchor_svg(self, J, pose):
        D = self.D
        k = lambda v: v * D
        sw = J['sw']
        yk = self.yoke * D
        o = []
        if self.kind in ('level', 'clerk'):
            # ivory wing collar: wing tips ARE the shoulder points
            wing = [(-sw - k(0.012), yk - k(0.004)), (-k(0.09), -k(0.035)), (k(0.09), -k(0.035)), (sw + k(0.012), yk - k(0.004)),
                    (sw - k(0.035), yk + k(0.055)), (k(0.035), k(0.20)), (0, k(0.235)), (-k(0.035), k(0.20)),
                    (-sw + k(0.035), yk + k(0.055))]
            o.append(f'<polygon points="{pstr(wing)}" fill="{IVORY}"/>')
            # shadow side (right) of the collar + wing folds
            o.append(f'<polygon points="{pstr([(k(0.02), -k(0.035)), (k(0.09), -k(0.035)), (sw + k(0.012), yk - k(0.004)), (sw - k(0.035), yk + k(0.055)), (k(0.035), k(0.20)), (0, k(0.235))])}" fill="{shade(IVORY,0.1)}"/>')
            for s in (-1, 1):
                fold = [(s * k(0.07), -k(0.02)), (s * k(0.15), k(0.045)), (s * k(0.06), k(0.06))]
                o.append(f'<polygon points="{pstr(fold)}" fill="{shade(IVORY,0.2)}"/>')
            # bow tie
            by = k(0.035)
            bw, bh = k(0.115), k(0.05)
            o.append(f'<polygon points="{f(0)},{f(by)} {f(-bw)},{f(by-bh)} {f(-bw)},{f(by+bh)}" fill="{INK}"/>')
            o.append(f'<polygon points="{f(0)},{f(by)} {f(bw)},{f(by-bh)} {f(bw)},{f(by+bh)}" fill="{INK}"/>')
            o.append(f'<rect x="{f(-k(0.03))}" y="{f(by-k(0.032))}" width="{f(k(0.06))}" height="{f(k(0.064))}" rx="{f(k(0.012))}" fill="{INK}"/>')
        elif self.kind == 'hasty':
            # salmon-edged open collar points; ivory shirt V; thin black tie
            o.append(f'<polygon points="{pstr([(-k(0.08), -k(0.02)), (k(0.08), -k(0.02)), (0, k(0.2))])}" fill="{IVORY}"/>')
            for s in (-1, 1):
                pt = [(s * k(0.075), -k(0.035)), (s * (sw + k(0.015)), yk - k(0.01)), (s * k(0.05), k(0.2))]
                pe = [(s * k(0.06), -k(0.05)), (s * (sw + k(0.04)), yk - k(0.02)), (s * k(0.04), k(0.235))]
                o.append(f'<polygon points="{pstr(pe)}" fill="{SALMON if s < 0 else shade(SALMON,0.12)}"/>')
                o.append(f'<polygon points="{pstr(pt)}" fill="{IVORY if s < 0 else shade(IVORY,0.1)}"/>')
            o.append(f'<rect x="{f(-k(0.03))}" y="{f(-k(0.03))}" width="{f(k(0.06))}" height="{f(k(0.06))}" rx="{f(k(0.012))}" fill="{INK}"/>')
        return f'<g transform="{self.frame(J)}">' + ''.join(o) + '</g>'

    def tie_svg(self, J, pose):
        if self.kind != 'hasty':
            return ''
        D = self.D
        t0 = add(J['B'], J['tg'], 0.02 * D)
        a = ang_of(J['B'], J['Cc']) + pose.get('tie', 0)
        t1 = add(t0, dirv(a), 0.42 * D)
        c = add(lerp(t0, t1, 0.5), dirv(a + 90), -pose.get('tie', 0) * 0.4)
        o = ribbon(t0, c, t1, 0.04 * D, 0.075 * D, INK, tip='point')
        bar = add(t0, dirv(a), 0.16 * D)
        o += pill(add(bar, dirv(a + 90), -0.05 * D), add(bar, dirv(a + 90), 0.05 * D), 0.022 * D, GOLD)
        return o

    def pocket_svg(self, J, pose):
        if self.kind != 'hasty':
            return ''
        D = self.D
        side = pose.get('pocket', 1)
        p = add(add(J['Y'], J['sp'], side * 0.11 * D), J['tg'], 0.17 * D)
        tri = [add(p, J['sp'], -0.05 * D), add(add(p, J['sp'], -0.01 * D), J['tg'], -0.075 * D), add(p, J['sp'], 0.035 * D),
               add(add(p, J['sp'], 0.045 * D), J['tg'], -0.04 * D), add(p, J['sp'], 0.06 * D)]
        return f'<polygon points="{pstr(tri)}" fill="{SALMON}"/>'

    def tails_svg(self, J, pose):
        t = pose.get('tails')
        if t is None or self.kind != 'level':
            return ''
        D = self.D
        H, tgh = J['H'], J['tgh']
        p0 = add(H, tgh, -0.12 * D)
        sw_ = t.get('swing', 0)
        Lt = t.get('len', 0.82) * D
        p1 = add(p0, dirv(sw_), Lt)
        c = add(lerp(p0, p1, 0.5), dirv(sw_ + 90), t.get('lag', 0) * D)
        w0 = t.get('w', 0.2) * D
        left, right = ribbon_pts(p0, c, p1, w0, w0 * 0.25)
        notch = lerp(p1, lerp(p0, p1, 0.5), 0.18)
        pts = left + [add(left[-1], dirv(sw_), 0.04 * D), notch, add(right[-1], dirv(sw_), 0.04 * D)] + right[::-1]
        col = mix(COAT, EMERALD_D, 0.25)
        return f'<polygon points="{pstr(pts)}" fill="{col}"/>'

    def waist_svg(self, J, pose):
        """small ivory waistcoat point at the hip (repeats the collar ivory)."""
        if self.kind != 'level':
            return ''
        D = self.D
        k = lambda v: v * D
        H, tgh, sph = J['H'], J['tgh'], J['sph']
        c = add(add(H, tgh, -0.17 * D), sph, pose.get('waist_dx', 0.0) * D)
        pts = [(-k(0.075), -k(0.03)), (k(0.075), -k(0.03)), (k(0.06), k(0.03)), (0, k(0.085)), (-k(0.06), k(0.03))]
        g = [add(add(c, sph, x), tgh, y) for x, y in pts]
        return f'<polygon points="{pstr(g)}" fill="{IVORY}"/>'

    def chain_svg(self, J, pose):
        c = pose.get('chain')
        if c is None or self.kind != 'hasty':
            return ''
        D = self.D
        H = J['H']
        up = norm(sub(J['Cc'], H))
        e1 = add(add(H, up, 0.05 * D), J['sph'], 0.02 * D)
        e2 = add(add(H, up, 0.17 * D), J['sph'], 0.03 * D)
        sw = c.get('swing', 0)
        L = c.get('len', 0.32) * D
        d = dirv(sw)
        c1, c2 = add(e1, d, L), add(e2, d, L * 0.85)
        belly = (0.125 * e1[0] + 0.375 * c1[0] + 0.375 * c2[0] + 0.125 * e2[0],
                 0.125 * e1[1] + 0.375 * c1[1] + 0.375 * c2[1] + 0.125 * e2[1])
        o = [f'<path d="M{f(e1[0])},{f(e1[1])} C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(e2[0])},{f(e2[1])}" '
             f'stroke="{GOLD}" stroke-width="{f(0.028*D)}" fill="none" stroke-linecap="round" stroke-dasharray="0.1 {f(0.04*D)}"/>',
             f'<path d="M{f(e1[0])},{f(e1[1])} C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(e2[0])},{f(e2[1])}" '
             f'stroke="{GOLD}" stroke-width="{f(0.016*D)}" fill="none" stroke-linecap="round"/>']
        fob = add(belly, d, 0.04 * D)
        o.append(f'<circle cx="{f(fob[0])}" cy="{f(fob[1])}" r="{f(0.05*D)}" fill="{GOLD}"/>')
        o.append(f'<circle cx="{f(fob[0]-0.008*D)}" cy="{f(fob[1]-0.004*D)}" r="{f(0.03*D)}" fill="{IVORY}"/>')
        if c.get('glint'):
            o.append(star4(fob[0] + 0.07 * D, fob[1] - 0.07 * D, 0.065 * D))
        return '\n'.join(o)

    # ---- layers
    def layers(self, J, face, pose):
        L = {k: '' for k in ('shadow', 'tails', 'legF', 'armF', 'spine', 'neck', 'anchor', 'legN',
                             'armN', 'prop', 'thumbs', 'front')}
        far_side = pose.get('far', 'R' if face.get('turn', 0) >= 0 else 'L')
        sh = pose.get('shadow')
        if sh:
            x0, x1, y, op = sh
            L['shadow'] = (f'<ellipse cx="{f((x0+x1)/2)}" cy="{f(y)}" rx="{f((x1-x0)/2)}" ry="{f(0.06*self.D)}" '
                           f'fill="{EMERALD_D}" opacity="{op}"/>')
        tray = pose.get('tray')
        for side in 'LR':
            arm = pose.get('arm' + side, {})
            far = arm.get('far', side == far_side)
            col = self.far_col if far else self.col
            h = dict(pose.get('hand' + side, {}))
            h.setdefault('ang', ang_of(J['E' + side], J['W' + side]))
            hs, th = self.hand_svg(J['W' + side], h, far)
            seg = self.limb(J['S' + side], J['E' + side], J['W' + side], col, 'arm' + side)
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
                L['prop'] += tray_cup(cx, bottom, w)
                J['tray'] = (cx, bottom, w)
            leg = pose.get('leg' + side, {})
            lfar = leg.get('far', side == far_side)
            lcol = self.far_col if lfar else self.col
            sv = self.limb(J['H' + side], J['K' + side], J['F' + side], lcol, 'leg' + side)
            sv += self.shoe_svg(J['F' + side], pose.get('foot' + side, {}), far=lfar)
            L['legF' if lfar else 'legN'] += sv
        L['tails'] = self.tails_svg(J, pose)
        L['spine'] = self.spine_svg(J) + self.waist_svg(J, pose) + self.chain_svg(J, pose) + self.pocket_svg(J, pose)
        L['neck'] = self.neck_svg(J)
        L['anchor'] = self.anchor_svg(J, pose) + self.tie_svg(J, pose)
        return L


class Char:
    def __init__(self, head, body):
        self.head, self.body = head, body

    def joints(self, cx, cy, face, pose):
        return self.body.joints((cx, cy), face, pose)

    def place(self, cx, floor, face, pose, plant='L', foot_dx=0.0, bend=6, lift=0.0):
        """head centre y so the planted leg (knee bent `bend` deg) stands on
        `floor` (sole) with its ankle at x = hip.x + foot_dx*D."""
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
        return '\n'.join([L['shadow'], L['armF'], L['tails'], L['legF'], L['spine'], L['neck'], L['anchor'],
                          L['legN'], head, L['armN'], L['prop'], L['thumbs'], L['front'], marks])


# ---------------------------------------------------------------- diagnostics
def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1e-9
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def head_clear(ch, cx, cy, face, label):
    """gap (in D) between each arm's centre line and the head outline incl. ears."""
    J, hd, b = ch.J, ch.head, ch.body
    R = hd.R
    pts = [(cx + R * math.cos(a), cy + R * math.sin(a)) for a in [i * math.pi / 60 for i in range(120)]]
    for s in (-1, 1):
        pts.append((cx + s * (R + 0.065 * hd.D), cy - 0.02 * hd.D))
    res = []
    for side in 'LR':
        segs = [(J['S' + side], J['E' + side]), (J['E' + side], J['W' + side])]
        g = min(_seg_dist(p, a, c) for p in pts for a, c in segs) - b.r0
        res.append(f'arm{side} {g / hd.D:+.2f}D')
    print(f'  [{label}] clearance', ', '.join(res))


def report(ch, cx, cy, face, floor, label):
    hd = ch.head
    H = floor - (cy - hd.R)
    print(f'  [{label}] D={hd.D:.0f} H={H:.0f} = {H/hd.D:.2f} D, head {hd.D/H*100:.1f}% '
          f'| hair top y={cy-hd.R-hd.top_extent(face):.0f}')


# ---------------------------------------------------------------- shared svg bits
def lamp(cx, cy, rx, ry, op, col=IVORY):
    gid = uid('lp')
    return (f'<radialGradient id="{gid}"><stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
            f'<stop offset="0.5" stop-color="{col}" stop-opacity="{op*0.78}"/>'
            f'<stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient>'
            f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="url(#{gid})"/>')


def svg_doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'<defs><filter id="blk" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" '
            f'values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter></defs>\n'
            f'{body}\n</svg>\n')


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
# CAST
# =====================================================================
D_L = 250
LEVEL_HEAD = Head(D_L, SKIN_L, SHAD_L, 'level')
LEVEL_BODY = Body(D_L, neck=0.20, yoke=0.06, spine=1.05, leg=1.65, uarm=0.71, farm=0.74, sh=0.26,
                  col=COAT, skin=SKIN_L, hand=GLOVE, hand_edge=GLOVE_EDGE, kind='level', shoe='oxford')
LEVEL = Char(LEVEL_HEAD, LEVEL_BODY)

D_H = 230
HASTY_HEAD = Head(D_H, SKIN_H, SHAD_H, 'slick', hair_col=INK, hair_shad='#0E0E0E', mustache=True)
HASTY_BODY = Body(D_H, neck=0.08, yoke=0.05, spine=0.95, leg=1.40, uarm=0.66, farm=0.69, sh=0.27,
                  col=BRICK, skin=SKIN_H, hand=SKIN_H, kind='hasty', shoe='spectator', ring=True)
HASTY = Char(HASTY_HEAD, HASTY_BODY)

D_C = 180
CLERK_HEAD = Head(D_C, SKIN_C, SHAD_C, 'tufts', hair_col=IVORY, hair_shad=shade(IVORY, 0.12), brow_col=IVORY)
CLERK_BODY = Body(D_C, neck=0.12, yoke=0.06, spine=1.0, leg=1.5, uarm=0.68, farm=0.70, sh=0.27,
                  col=COAT, skin=SKIN_C, hand=SKIN_C, kind='clerk')
CLERK = Char(CLERK_HEAD, CLERK_BODY)


def level_sheet(D):
    hd = Head(D, SKIN_L, SHAD_L, 'level')
    bd = Body(D, neck=0.20, yoke=0.06, spine=1.05, leg=1.65, uarm=0.71, farm=0.74, sh=0.26,
              col=COAT, skin=SKIN_L, hand=GLOVE, hand_edge=GLOVE_EDGE, kind='level', shoe='oxford',
              min_w=11)
    return Char(hd, bd)


# expressions for Mr. Level (face dicts; turn/fx set per shot)
NEUTRAL = dict()
SMUG = dict(browL=dict(dy=-0.16, tilt=-10), browR=dict(), mouth=dict(type='curl', dx=0.06, side='R'))


def SURPRISED(head):
    # both brows hover 0.15 D above the hair crest
    crest = -head.R - head.top_extent({})
    yb = (crest - 0.15 * head.D - 0.045 * head.D)
    dy = (yb - (-0.215 * head.D)) / head.D
    trail = -0.27 * head.D
    return dict(eyes=dict(state='dot'),
                browL=dict(dy=dy, trail=trail),
                browR=dict(dy=dy, trail=trail),
                mouth=dict(type='tall_o', dy=0.01))


# =====================================================================
# SCENE  1080 x 1920  'out of reach'
# =====================================================================
def clerk_booth(cxa, top, w, ledge, horizon, sil=False):
    o = []
    r = w / 2
    x0, x1 = cxa - r, cxa + r
    cid = uid('ar')
    o.append(f'<clipPath id="{cid}"><path d="M{f(x0)},{f(ledge)} L{f(x0)},{f(top+r)} A{f(r)},{f(r)} 0 0 1 {f(x1)},{f(top+r)} L{f(x1)},{f(ledge)} Z"/></clipPath>')
    if not sil:
        o.append(f'<g clip-path="url(#{cid})">')
        o.append(f'<rect x="{f(x0)}" y="{f(top)}" width="{f(w)}" height="{f(ledge-top)}" fill="{EMERALD_D}"/>')
        o.append(f'<line x1="{f(x0)}" y1="{f(top+r+20)}" x2="{f(x1)}" y2="{f(top+r+20)}" stroke="{shade(GOLD,0.3)}" stroke-width="5"/>')
        for i, hx in enumerate(range(int(x0) + 16, int(x1) - 6, 34)):
            o.append(f'<path d="M{hx-13},{f(top+r+26)} L{hx+13},{f(top+r+26)} L{hx+18},{f(ledge-10)} L{hx-18},{f(ledge-10)} Z" '
                     f'fill="{mix(EMERALD_D, EMERALD, 0.5 if i % 2 else 0.25)}"/>')
        o.append(lamp(cxa, ledge - 190, 170, 210, 0.62))
        o.append('</g>')
    ch = CLERK
    face = dict(turn=-0.35, eyes=dict(dx=-0.06, dy=0.01, lid=0.3),
                browL=dict(dy=-0.2, tilt=-8), browR=dict(dy=0.015),
                mouth=dict(type='flat', dx=-0.03, w=0.18))
    pose = dict(neck=-3, armL=dict(a1=-12, a2=90, upper=0.72, fore=0.72, far=False),
                armR=dict(a1=12, a2=-90, upper=0.72, fore=0.72, far=True),
                handL=dict(ang=90, thumb=-1), handR=dict(ang=-90, thumb=1), legL=dict(a1=0), legR=dict(a1=0))
    ccx = cxa + 4
    J0 = ch.joints(ccx, 0, face, pose)
    ccy = ledge - 9 - J0['WL'][1]
    J = ch.joints(ccx, ccy, face, pose)
    L = ch.body.layers(J, face, pose)
    sc = uid('cs')
    g = []
    g.append(f'<clipPath id="{sc}"><rect x="0" y="0" width="1080" height="{f(ledge+4)}"/></clipPath>'
             f'<g clip-path="url(#{sc})">' + L['armF'] + L['spine'] + L['neck'] + L['anchor'] + '</g>')
    if not sil:
        g.append(f'<rect x="{f(x0-24)}" y="{f(ledge)}" width="{f(w+48)}" height="24" rx="5" fill="{IVORY}"/>'
                 f'<rect x="{f(x0-24)}" y="{f(ledge+19)}" width="{f(w+48)}" height="6" fill="{shade(IVORY,0.25)}"/>'
                 f'<rect x="{f(x0+18)}" y="{f(ledge+52)}" width="{f(w-36)}" height="{f(horizon-ledge-96)}" fill="none" '
                 f'stroke="{shade(GOLD,0.15)}" stroke-width="3" opacity="0.55"/>')
    g.append(ch.head.draw(ccx, ccy, face))
    g.append(L['armN'] + L['thumbs'])
    body = '\n'.join(g)
    if sil:
        body = f'<g filter="url(#blk)">{body}</g>'
    o.append(body)
    return '\n'.join(o), (ccx, ccy)


def build_scene(sil=False, bg_only=False):
    PROBES.clear()
    W, H = 1080, 1920
    horizon, floor_y, band = 1265, 1545, 1575
    o = []
    o.append(f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else EMERALD}"/>')
    if not sil:
        o.append(f'<clipPath id="wall"><rect x="0" y="232" width="{W}" height="{horizon-232}"/></clipPath><g clip-path="url(#wall)">'
                 + lamp(320, 820, 440, 660, 0.44) + lamp(840, 900, 360, 560, 0.52) + '</g>')
        o.append(arch(330, 262, 470, horizon, 7))
        o.append(arch(925, 262, 290, horizon, 7))
        o.append(f'<rect x="0" y="228" width="{W}" height="4" fill="{GOLD}"/>')
    booth, (ccx, ccy) = clerk_booth(925, 262, 290, 628, horizon, sil=sil)
    o.append(booth)

    # ---------------- Mr. Level: 3/4 right, tray up on his fingertips, far brow afloat
    hd = LEVEL.head
    lv_face = dict(turn=0.7, tilt=-4,
                   eyes=dict(dx=0.04, dy=0.035),
                   browL=dict(),
                   mouth=dict(type='curl', dx=0.075, side='R', curl=0.065))
    yb = -hd.R - 0.6 * hd.D
    lv_face['browR'] = dict(dy=(yb - (-0.215 * hd.D)) / hd.D, dx=0.02, tilt=-4,
                            trail=-hd.R - hd.top_extent({}) - 0.01 * hd.D)
    lcx = 360
    lv_pose = dict(neck=6, neck_off=-0.08, spine=-9, chest=-2, curve=0.07, far='L',
                   armL=dict(a1=-157, a2=-157, far=True), handL=dict(kind='mitten', ang=180, thumb=1, thumb_ang=140),
                   armR=dict(a1=-38, a2=95, fore=0.2, far=True), handR=dict(kind='none'),
                   tails=dict(swing=-34, lag=0.07, len=0.8),
                   tray=dict(hand='L', w=0.6, at='tip'),
                   waist_dx=0.03)
    lcy, plantF = LEVEL.place(lcx, floor_y, lv_face, lv_pose, plant='L', foot_dx=0.02, bend=4)
    lv_pose['legL'] = dict(foot=plantF, bend=1, far=True)
    lv_pose['footL'] = dict(dir=1)
    lv_pose['legR'] = dict(foot=(plantF[0] + 0.36 * D_L, floor_y - LEVEL.body.ankle - 0.07 * D_L), bend=1, far=False)
    lv_pose['footR'] = dict(dir=1, tilt=26)
    lv_pose['shadow'] = (plantF[0] - 90, plantF[0] + 170, floor_y + 4, 0.45)

    # ---------------- Hasty, apex of a leap: one arm stretched for the tray
    hx, hy = HX, HY
    hs_face = dict(turn=-0.5, tilt=7, fy=-0.01,
                   eyes=dict(dx=-0.04, dy=-0.02, ghosts=[(-0.03, -0.015), (0.03, 0.015)]),
                   browL=dict(dy=0.05, dx=0.03, w=0.3, tilt=-22, ghosts=[(-0.025, -0.03, -6), (0.025, 0.03, 6)]),
                   browR=dict(dy=0.05, dx=-0.005, w=0.3, tilt=-22, ghosts=[(0.025, -0.03, -6), (-0.025, 0.03, 6)]),
                   mouth=dict(type='zig', w=0.22, dy=0.025),
                   sweat=(0.55, -0.2))
    hs_pose = dict(neck=14, neck_off=0.03, spine=4, chest=2, curve=-0.05, far='L', sh_k=1.08,
                   armL=dict(a1=FRONT, a2=FRONT, far=True), handL=dict(ang=FRONT, thumb=1),
                   armR=dict(a1=BACK1, a2=BACK2, far=False), handR=dict(ang=BACK2 - 10, thumb=-1),
                   footL=dict(dir=-1, tilt=62), footR=dict(dir=-1, tilt=40),
                   chain=dict(swing=62, len=0.36, glint=True), tie=-35, pocket=1)
    Jh = HASTY.joints(hx, hy, hs_face, hs_pose)
    sole = floor_y - 120
    hs_pose['legL'] = dict(foot=(Jh['HL'][0] - 0.05 * D_H, sole - HASTY.body.ankle), bend=1, far=True)
    hs_pose['legR'] = dict(foot=(Jh['HR'][0] + 0.42 * D_H, sole - HASTY.body.ankle - 0.30 * D_H), bend=-1, far=False)
    hs_pose['shadow'] = (Jh['H'][0] - 90, Jh['H'][0] + 100, floor_y + 4, 0.28)

    # ---------------- floor
    if not sil:
        o.append(f'<rect x="0" y="{horizon-22}" width="{W}" height="22" fill="{BRASS}"/>')
        o.append(f'<rect x="0" y="{horizon-22}" width="{W}" height="4" fill="{GOLD}"/>')
        o.append(floor_tiles(horizon, band, vp=(540, 640), tile=150, off=52, parity=1, light=SAGE, dark=EMERALD, fade=(0.0, 0.3)))
        o.append(f'<clipPath id="flr"><rect x="0" y="{horizon}" width="{W}" height="{band-horizon}"/></clipPath><g clip-path="url(#flr)">'
                 + lamp(330, horizon + 60, 210, 330, 0.42) + lamp(840, horizon + 40, 190, 300, 0.40) + '</g>')
        o.append(f'<rect x="0" y="{band}" width="{W}" height="{H-band}" fill="{FLOOR_D}"/>')
        o.append(f'<rect x="0" y="{band}" width="{W}" height="3" fill="{shade(GOLD,0.35)}"/>')
        o.append(lamp(380, floor_y - 40, 300, 120, 0.45))
        o.append(lamp(820, floor_y - 60, 240, 130, 0.45))

    if bg_only:
        return svg_doc(W, H, '\n'.join(o))

    figs = []
    hs_svg = HASTY.draw(hx, hy, hs_face, hs_pose)
    Jh = HASTY.J
    lv_svg = LEVEL.draw(lcx, lcy, lv_face, lv_pose)
    Jl = LEVEL.J
    tcx, tb, tw = Jl['tray']
    tipL = add(Jh['WL'], dirv(FRONT), HASTY.body.mit_l)
    # ghost of where the tray was a beat ago, just past Hasty's fingertips
    gdir = dirv(FRONT)
    gx, gy = add(tipL, gdir, GHOST_K * D_H)
    gbottom = gy + 0.02 * D_L
    marks = ''
    if not sil:
        marks += tray_ghost(gx, gbottom, tw, op=GHOST_OP)
        S0 = (gx - 0.05 * tw, gbottom - 0.62 * D_L)
        E0 = (tcx + 0.42 * tw, tb - 0.5 * D_L)
        C0 = (S0[0] - ARC_KX * (S0[0] - E0[0]), min(S0[1], E0[1]) - ARC_UP)
        marks += dotted_arc(S0, C0, E0, w=8, op=0.8, gap=17)
        # distance from the arc to the floating brow (diagnostic)
        bx = lcx + hd.k(0.7 * 0.13 + 0.19 + 0.02)
        by = lcy + hd.k(-0.215) + hd.k(lv_face['browR']['dy'])
        dmin = min(dist(bez2(S0, C0, E0, i / 100), (bx, by)) for i in range(101))
        print(f'  arc to brow centre: {dmin:.0f}px; brow at ({bx:.0f},{by:.0f}); arc peak y {min(bez2(S0, C0, E0, i/100)[1] for i in range(101)):.0f}')
        marks += ticks(tipL[0], tipL[1], 0.14 * D_H, 0.24 * D_H, (FRONT_T - 40, FRONT_T, FRONT_T + 40), w=6, color=IVORY, op=0.75)
        toe = sole + 40
        for dx in (-34, 0, 34):
            x = Jh['H'][0] + dx - 20
            marks += (f'<line x1="{f(x)}" y1="{f(toe)}" x2="{f(x)}" y2="{f(toe+26)}" stroke="{IVORY}" '
                      f'stroke-width="6" stroke-linecap="round" opacity="0.5"/>')
    figs.append(marks)
    figs.append(hs_svg)
    figs.append(lv_svg)
    fg = '\n'.join(figs)
    if sil:
        fg = f'<g filter="url(#blk)">{fg}</g>'
    o.append(fg)
    print('scene:')
    report(LEVEL, lcx, lcy, lv_face, floor_y, 'level')
    head_clear(LEVEL, lcx, lcy, lv_face, 'level')
    head_clear(HASTY, hx, hy, hs_face, 'hasty')
    print(f'  level head ({lcx},{lcy:.0f}) tray ({tcx:.0f},{tb:.0f}) skull top {lcy-D_L/2:.0f} '
          f'tray above skull {(lcy-D_L/2-tb)/D_L:.2f}D | hasty tipL ({tipL[0]:.0f},{tipL[1]:.0f}) ghost ({gx:.0f},{gy:.0f}) '
          f'| tip->tray rim {(dist(tipL, (tcx + tw/2, tb)))/D_L:.2f}D | tip->level head rim {(dist(tipL,(lcx,lcy))-D_L/2)/D_L:.2f}D '
          f'| soles {max(Jh["FL"][1], Jh["FR"][1]) + HASTY.body.ankle:.0f} | back hand {tuple(round(v) for v in Jh["WR"])}')
    return svg_doc(W, H, '\n'.join(o))


HX, HY = 815, 745
FRONT = -152          # Hasty's reaching arm (28 deg left of vertical)
FRONT_T = -118        # screen angle (deg) for the whiff ticks
BACK1, BACK2 = 38, 18
GHOST_OP = 0.5
GHOST_K = 0.16
ARC_KX = 0.42
ARC_UP = 95


# =====================================================================
# POSES  1080 x 1080
# =====================================================================
def build_poses(sil=False):
    W, H = 1080, 1080
    floor = 990
    D = 200
    ch = level_sheet(D)
    o = [f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else EMERALD}"/>']
    cxs = (190, 540, 880)
    if not sil:
        for cx in cxs:
            o.append(lamp(cx, 600, 230, 520, 0.42))
        o.append(f'<rect x="0" y="978" width="{W}" height="3" fill="{GOLD}"/>')
        o.append(floor_tiles(981, H, vp=(540, 600), tile=130, off=20, parity=0, fade=(0.0, 0.2)))
        for cx in cxs:
            o.append(lamp(cx, floor, 190, 40, 0.45))
    figs = []

    # (1) READY: front view, ramrod, heels together, tray at shoulder height
    f1 = dict(turn=0, browL=dict(), browR=dict())
    p1 = dict(neck=-3, neck_off=0, spine=4, chest=2, curve=-0.035,
              armR=dict(a1=14, a2=160, far=False), handR=dict(kind='flat', ang=-92, thumb=-1, thumb_ang=-170),
              armL=dict(a1=-18, a2=75, fore=0.72, far=True), handL=dict(kind='none'),
              footL=dict(dir=-1, tilt=0), footR=dict(dir=1, tilt=0),
              tray=dict(hand='R', w=0.6, at=0.6))
    cy1, F1 = ch.place(cxs[0], floor, f1, p1, plant='L', foot_dx=0.0, bend=3)
    p1['legL'] = dict(foot=(cxs[0] - 0.035 * D, floor - ch.body.ankle), bend=-1)
    p1['legR'] = dict(foot=(cxs[0] + 0.035 * D, floor - ch.body.ankle), bend=1)
    p1['shadow'] = (cxs[0] - 80, cxs[0] + 80, floor + 2, 0.4)
    figs.append(ch.draw(cxs[0], cy1, f1, p1))
    print('poses:')
    report(ch, cxs[0], cy1, f1, floor, 'pose1')
    head_clear(ch, cxs[0], cy1, f1, 'pose1')
    J1 = ch.J
    print('   pose1 tray', tuple(round(v) for v in J1['tray']))

    # (2) TALL LIFT: 3/4 right, one straight leg, knee to hip height, tray straight overhead
    f2 = dict(SMUG, turn=0.7, tilt=-4, eyes=dict(dx=0.03, dy=0.02))
    p2 = dict(neck=8, neck_off=-0.09, spine=-6, chest=0, curve=0.06, far='L',
              armL=dict(a1=-157, a2=-157, far=True), handL=dict(kind='mitten', ang=180, thumb=1, thumb_ang=140),
              armR=dict(a1=42, a2=42, far=False), handR=dict(ang=42, thumb=1),
              tails=dict(swing=-42, lag=0.08, len=0.8),
              tray=dict(hand='L', w=0.6, at='tip'),
              footL=dict(dir=1), footR=dict(dir=1, tilt=10), waist_dx=0.03)
    cy2, F2 = ch.place(cxs[1], floor, f2, p2, plant='L', foot_dx=0.0, bend=3)
    p2['legL'] = dict(foot=F2, bend=1, far=True)
    J2 = ch.joints(cxs[1], cy2, f2, p2)
    p2['legR'] = dict(a1=95, a2=6, far=False)
    p2['shadow'] = (cxs[1] - 70, cxs[1] + 110, floor + 2, 0.4)
    figs.append(ch.draw(cxs[1], cy2, f2, p2))
    report(ch, cxs[1], cy2, f2, floor, 'pose2')
    head_clear(ch, cxs[1], cy2, f2, 'pose2')
    J2 = ch.J
    print('   pose2 tray', tuple(round(v) for v in J2['tray']), 'skull top', round(cy2 - D / 2),
          'gap', round((cy2 - D / 2 - J2['tray'][1]) / D, 2), 'D')

    # (3) BROWS TAKE OFF: 3/4 left, stiff board, sprung 40 px, forearm forward with tray
    f3 = dict(SURPRISED(ch.head), turn=-0.7)
    p3 = dict(neck=0, neck_off=0.08, spine=0, curve=0.0, far='L',
              armL=dict(a1=4, a2=-90, far=True), handL=dict(kind='flat', ang=-90, thumb=-1, thumb_ang=-160),
              armR=dict(a1=-4, a2=-2, far=False), handR=dict(ang=-2, thumb=1),
              tails=dict(swing=40, lag=0.0, len=0.62),
              tray=dict(hand='L', w=0.6, at=0.6),
              footL=dict(dir=-1, tilt=16), footR=dict(dir=-1, tilt=16), waist_dx=-0.03)
    cy3, F3 = ch.place(cxs[2], floor, f3, p3, plant='L', foot_dx=0.0, bend=0.5, lift=40)
    p3['legL'] = dict(foot=(F3[0] - 0.02 * D, F3[1]), bend=1, far=True)
    p3['legR'] = dict(foot=(F3[0] + 0.03 * D, F3[1]), bend=1, far=False)
    p3['shadow'] = (cxs[2] - 50, cxs[2] + 60, floor + 2, 0.28)
    marks = ''
    if not sil:
        for dx in (-30, 0, 30):
            marks += (f'<line x1="{cxs[2]+dx}" y1="{floor-30}" x2="{cxs[2]+dx}" y2="{floor-12}" stroke="{IVORY}" stroke-width="5" '
                      f'stroke-linecap="round" opacity="0.6"/>')
    figs.append(ch.draw(cxs[2], cy3, f3, p3, marks=marks))
    report(ch, cxs[2], cy3, f3, floor - 40, 'pose3')
    head_clear(ch, cxs[2], cy3, f3, 'pose3')
    print('   pose3 tray', tuple(round(v) for v in ch.J['tray']))
    fg = '\n'.join(figs)
    if sil:
        fg = f'<g filter="url(#blk)">{fg}</g>'
    o.append(fg)
    return svg_doc(W, H, '\n'.join(o))


# =====================================================================
# LINEUP  540 x 1080, hero alone, exactly 900 px soles -> hair top
# =====================================================================
def build_lineup(sil=False):
    W, H = 540, 1080
    floor = 1010
    # total = (stand height 4.0 D nominal) + hair; solve D by iteration
    D = 215.0
    face = dict(turn=-0.65, tilt=2, eyes=dict(dx=-0.02), browL=dict(dy=-0.05, tilt=-4), browR=dict(),
                mouth=dict(type='curl', dx=-0.03, side='L', curl=0.035, w=0.2))
    pose = dict(neck=-6, neck_off=0.08, spine=7, chest=2, curve=-0.06, far='R',
                armL=dict(a1=10, a2=-150, far=False), handL=dict(kind='flat', ang=-92, thumb=-1, thumb_ang=175),
                armR=dict(a1=22, a2=-80, fore=0.42, far=True), handR=dict(kind='none'),
                tails=dict(swing=26, lag=-0.05, len=0.8),
                tray=dict(hand='L', w=0.6, at=0.6),
                footL=dict(dir=-1), footR=dict(dir=-1), waist_dx=-0.03)
    for _ in range(30):
        ch = level_sheet(D)
        cy, F = ch.place(270, floor, face, pose, plant='R', foot_dx=0.0, bend=4)
        top = cy - ch.head.R - ch.head.top_extent(face)
        tot = floor - top
        D *= 900 / tot
    ch = level_sheet(D)
    cy, F = ch.place(270, floor, face, pose, plant='R', foot_dx=0.0, bend=4)
    cx = 270
    pose['legR'] = dict(foot=F, bend=1, far=True)
    pose['legL'] = dict(foot=(F[0] - 0.3 * D, floor - ch.body.ankle - 0.02 * D), bend=-1, far=False)
    pose['footL'] = dict(dir=-1, tilt=8)
    o = [f'<rect width="{W}" height="{H}" fill="{"#FFFFFF" if sil else "#EDEAE4"}"/>']
    pose['shadow'] = (cx - 120, cx + 90, floor + 2, 0.0)
    if not sil:
        o.append(f'<ellipse cx="{cx-20}" cy="{floor+3}" rx="120" ry="9" fill="#000" opacity="0.12"/>')
    fig = ch.draw(cx, cy, face, pose)
    if sil:
        fig = f'<g filter="url(#blk)">{fig}</g>'
    o.append(fig)
    top = cy - ch.head.R - ch.head.top_extent(face)
    print(f'lineup: D={D:.1f} soles {floor} hair top {top:.1f} total {floor-top:.1f}')
    report(ch, cx, cy, face, floor, 'lineup')
    head_clear(ch, cx, cy, face, 'lineup')
    return svg_doc(W, H, '\n'.join(o))


if __name__ == '__main__':
    outs = {
        'scene.svg': build_scene(),
        'poses.svg': build_poses(),
        'lineup.svg': build_lineup(),
        'scene_sil.svg': build_scene(sil=True),
        'poses_sil.svg': build_poses(sil=True),
        'lineup_sil.svg': build_lineup(sil=True),
        'scene_bg.svg': build_scene(bg_only=True),
    }
    build_scene()   # refill PROBES for the contrast check
    import json
    with open(os.path.join(HERE, 'probes.json'), 'w') as fh:
        json.dump(PROBES, fh)
    for k, v in outs.items():
        with open(os.path.join(HERE, k), 'w') as fh:
            fh.write(v)
    print('ok')
