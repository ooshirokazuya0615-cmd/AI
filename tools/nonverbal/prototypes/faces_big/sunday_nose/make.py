#!/usr/bin/env python3
"""Sunday Nose / 日曜版の鼻 -- BIG-EYE round heads on stick bodies.

ONE face rig (BigFace: true-circle skull; a fixed eye-white shape per character -- Bix teardrop, Gus droopy --
resting on the nose top with a 0.03 D overlap; expression only from the upper-lid mask + heavy lid line, an
optional lower lid, solid pupils that clip against the rim and converge on a look target, brows, and a mouth
that stays hidden under the nose / mustache until a take) and
ONE stick-body rig (Body: neck stub + collar anchor + tapered spine + hip, ink limbs over an off-register
colour plate) plus one torso costume surface per character (Bix waistcoat, Gus knit vest + napkin bib).
scene.svg, faces.svg, hero.svg and partner.svg are all built from these.
All face / body sizes are fractions of D = skull diameter (ears, hair, nose excluded).
"""
import math, random, os

HERE = os.path.dirname(os.path.abspath(__file__))

INK = '#1A1A1A'; CREAM = '#EFE6D2'; CYAN = '#2C8FB8'; ROSE = '#C8457C'
MUSTARD = '#E8C547'; PINKNOSE = '#E49A8C'; GREEN = '#6C9A6A'
WHITE = '#FFFDF5'; CLOTH = '#F3ECDA'; MOUTH = '#3A1A22'; FLUSH = '#C8574B'
OFF = (4, 4)  # print misregistration of every colour plate (4 px down-right)

_uid = [0]
def uid(p='u'):
    _uid[0] += 1
    return f'{p}{_uid[0]}'

def f1(v):
    return f'{v:.1f}'

def P(pts, close=True):
    return 'M' + ' L'.join(f'{f1(x)} {f1(y)}' for x, y in pts) + (' Z' if close else '')

# ---------------------------------------------------------------- geometry
def rot(pt, ang, c=(0, 0)):
    a = math.radians(ang); x, y = pt[0] - c[0], pt[1] - c[1]
    return (c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))

def xf(pts, dx=0, dy=0, ang=0, sx=1, sy=1, c=(0, 0)):
    out = []
    for x, y in pts:
        x = c[0] + (x - c[0]) * sx; y = c[1] + (y - c[1]) * sy
        if ang:
            x, y = rot((x, y), ang, c)
        out.append((x + dx, y + dy))
    return out

def ellipse_pts(cx, cy, rx, ry, n=120, a0=0.0):
    return [(cx + rx * math.cos(a0 + 2 * math.pi * i / n), cy + ry * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]

def egg_pts(cx, cy, w, h, k=0.13, n=180):
    raw = []
    for i in range(n):
        t = 2 * math.pi * i / n
        y = math.sin(t)
        raw.append((math.cos(t) * (1 - k * y), y))
    mx = max(abs(p[0]) for p in raw)
    return [(cx + w / 2 * x / mx, cy + h / 2 * y) for x, y in raw]

def blob_pts(cx, cy, w, h, harm, n=140, ang=0):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        r = 1 + sum(a * math.sin(k * t + ph) for k, a, ph in harm)
        pts.append((cx + w / 2 * r * math.cos(t), cy + h / 2 * r * math.sin(t)))
    return xf(pts, ang=ang, c=(cx, cy)) if ang else pts

def area(pts):
    n = len(pts)
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))

def hull(points):
    pts = sorted(set((round(x, 3), round(y, 3)) for x, y in points))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo = []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]

def resample(pts, step, closed=True):
    Q = list(pts) + ([pts[0]] if closed else [])
    d = [0.0]
    for i in range(1, len(Q)):
        d.append(d[-1] + math.dist(Q[i - 1], Q[i]))
    L = d[-1]
    if L == 0:
        return list(pts)
    n = max(int(L / step), 8)
    out = []; j = 0
    for i in range(n if closed else n + 1):
        s = L * i / n
        while j < len(d) - 2 and d[j + 1] < s:
            j += 1
        seg = (d[j + 1] - d[j]) or 1
        t = (s - d[j]) / seg
        out.append((Q[j][0] + (Q[j + 1][0] - Q[j][0]) * t, Q[j][1] + (Q[j + 1][1] - Q[j][1]) * t))
    return out

def spline(ctrl, closed=True, n=12):
    out = []; N = len(ctrl)
    for i in (range(N) if closed else range(N - 1)):
        p0 = ctrl[(i - 1) % N] if closed else ctrl[max(i - 1, 0)]
        p1 = ctrl[i]; p2 = ctrl[(i + 1) % N]
        p3 = ctrl[(i + 2) % N] if closed else ctrl[min(i + 2, N - 1)]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(tuple(0.5 * ((2 * p1[a]) + (-p0[a] + p2[a]) * t + (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t2
                                    + (-p0[a] + 3 * p1[a] - 3 * p2[a] + p3[a]) * t3) for a in (0, 1)))
    if not closed:
        out.append(ctrl[-1])
    return out

def qbez(p0, p1, p2, n=30):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]

def cbez(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n; u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out

def clip_half(poly, f):
    """keep part of polygon where linear f(p) <= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        fa = f(a); fb = f(b)
        if fa <= 0:
            out.append(a)
        if (fa <= 0) != (fb <= 0):
            t = fa / (fa - fb)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out

def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy or 1e-9
    t = max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)

def inside(p, poly):
    c = False; n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x > p[0]:
                c = not c
    return c

def inner_dist(p, poly):
    d = min(seg_dist(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))
    return d if inside(p, poly) else -d

def centroid(poly):
    return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))

def clip_below(poly, c):
    """keep part of polygon with y <= c (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        ina = a[1] <= c; inb = b[1] <= c
        if ina:
            out.append(a)
        if ina != inb:
            t = (c - a[1]) / (b[1] - a[1])
            out.append((a[0] + (b[0] - a[0]) * t, c))
    return out

# ---------------------------------------------------------------- brush ink
def ring_d(pts, wmin=7, wmax=11, bias=0.85, seed=1, step=3.0):
    """closed brush outline: thick on the lower-right (shadow) side, thin top-left."""
    pts = resample(pts, step, True); n = len(pts)
    sgn = 1 if area(pts) > 0 else -1
    rnd = random.Random(seed); ph = rnd.random() * 6.28; ph2 = rnd.random() * 6.28
    outer = []; inner = []
    for i in range(n):
        p0 = pts[i - 1]; p2 = pts[(i + 1) % n]
        tx, ty = p2[0] - p0[0], p2[1] - p0[1]; L = math.hypot(tx, ty) or 1
        nx, ny = sgn * ty / L, -sgn * tx / L
        d = (nx + ny) * 0.7071
        u = 0.5 + 0.5 * d
        s = i / n
        wob = 0.5 + 0.5 * math.sin(s * 2 * math.pi * 3 + ph) * math.cos(s * 2 * math.pi * 2 + ph2)
        w = wmin + (wmax - wmin) * (0.72 * u + 0.28 * wob)
        outer.append((pts[i][0] + nx * w * (1 - bias), pts[i][1] + ny * w * (1 - bias)))
        inner.append((pts[i][0] - nx * w * bias, pts[i][1] - ny * w * bias))
    return P(outer) + ' ' + P(inner[::-1])

def stroke_d(pts, w, taper=(0.2, 0.2), step=2.0, wmin=0.18, swell=0.0, seed=0):
    pts = resample(pts, step, False); n = len(pts)
    rnd = random.Random(seed); ph = rnd.random() * 6.28
    Lft = []; Rgt = []
    for i in range(n):
        p0 = pts[max(i - 1, 0)]; p2 = pts[min(i + 1, n - 1)]
        tx, ty = p2[0] - p0[0], p2[1] - p0[1]; L = math.hypot(tx, ty) or 1
        nx, ny = -ty / L, tx / L
        s = i / (n - 1)
        a = min(1, s / taper[0]) if taper[0] > 0 else 1
        b = min(1, (1 - s) / taper[1]) if taper[1] > 0 else 1
        k = max(wmin, math.sin(min(a, b) * math.pi / 2))
        k *= 1 + swell * math.sin(s * 9 + ph)
        ww = w * k
        Lft.append((pts[i][0] + nx * ww / 2, pts[i][1] + ny * ww / 2))
        Rgt.append((pts[i][0] - nx * ww / 2, pts[i][1] - ny * ww / 2))
    return P(Lft + Rgt[::-1])

def stroke(pts, w, color=INK, **kw):
    return f'<path d="{stroke_d(pts, w, **kw)}" fill="{color}"/>'

def bbox(pts, pad=4):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad

def clipped(pts, content, off=(0, 0)):
    c = uid('c')
    return f'<clipPath id="{c}"><path d="{P(xf(pts, *off))}"/></clipPath><g clip-path="url(#{c})">{content}</g>'

def crescent(pts, pattern, dx, dy, opacity=1.0, off=OFF):
    """halftone shadow on the side away from the light (light = upper left)."""
    x, y, w, h = bbox(pts, 20)
    m = uid('m')
    mask = (f'<mask id="{m}" maskUnits="userSpaceOnUse" x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}">'
            f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}" fill="white"/>'
            f'<path d="{P(xf(pts, dx + off[0], dy + off[1]))}" fill="black"/></mask>')
    rect = f'<rect x="{f1(x)}" y="{f1(y)}" width="{f1(w)}" height="{f1(h)}" fill="url(#{pattern})" opacity="{opacity}" mask="url(#{m})"/>'
    return mask + clipped(pts, rect, off)

def inked(pts, fill, w=(7, 11), seed=0, bias=0.85, inner='', off=OFF, fill_op=1.0):
    out = []
    if fill:
        out.append(f'<path d="{P(xf(pts, *off))}" fill="{fill}" fill-opacity="{fill_op}"/>')
    out.append(inner)
    out.append(f'<path d="{ring_d(pts, w[0], w[1], bias, seed)}" fill="{INK}" fill-rule="evenodd"/>')
    return ''.join(out)

def ht_pattern(pid, color, pitch=10, r=3.6, ang=15, op=1.0):
    return (f'<pattern id="{pid}" width="{pitch}" height="{pitch}" patternUnits="userSpaceOnUse" patternTransform="rotate({ang})">'
            f'<circle cx="{pitch / 2}" cy="{pitch / 2}" r="{r}" fill="{color}" fill-opacity="{op}"/></pattern>')

def check_pattern(pid, color, tile=64, band=18, pitch=8, r=2.3):
    dots = []
    for yy in range(0, tile, pitch):
        for xx in range(0, tile, pitch):
            inv = xx < band; inh = yy < band
            if inv or inh:
                rr = r * (1.25 if (inv and inh) else 1)
                dots.append(f'<circle cx="{xx + pitch / 2}" cy="{yy + pitch / 2}" r="{rr:.2f}" fill="{color}"/>')
    return f'<pattern id="{pid}" width="{tile}" height="{tile}" patternUnits="userSpaceOnUse" patternTransform="rotate(-4)">{"".join(dots)}</pattern>'

def ht_fade(x0, y0, x1, y1, color, pitch=10, rmax=4.0, rmin=0.4, power=1.3, rev=False):
    out = []; row = 0; y = y0 + pitch / 2
    while y < y1:
        t = (y - y0) / (y1 - y0)
        if rev:
            t = 1 - t
        r = rmin + (rmax - rmin) * (t ** power)
        x = x0 + (pitch / 2 if row % 2 else 0)
        while x < x1 + pitch:
            out.append(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{r:.2f}"/>')
            x += pitch
        y += pitch * 0.866; row += 1
    return f'<g fill="{color}">{"".join(out)}</g>'

def ht_ellipse(cx, cy, rx, ry, color, pitch=10, rmax=4.0):
    """halftone cast shadow: dots shrink toward the rim."""
    out = []; row = 0; y = cy - ry
    while y <= cy + ry:
        x = cx - rx + (pitch / 2 if row % 2 else 0)
        while x <= cx + rx:
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d < 1:
                r = rmax * (1 - d) ** 0.6
                if r > 0.6:
                    out.append(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{r:.2f}"/>')
            x += pitch
        y += pitch * 0.866; row += 1
    return f'<g fill="{color}">{"".join(out)}</g>'

def common_defs():
    return ''.join([
        ht_pattern('htC', CYAN, 10, 3.6, 15),
        ht_pattern('htCs', CYAN, 10, 2.4, 15),
        ht_pattern('htR', ROSE, 10, 3.6, 75),
        ht_pattern('htRs', ROSE, 10, 2.6, 75),
        ht_pattern('htK', INK, 10, 3.2, 45),
        ht_pattern('htKs', INK, 10, 2.2, 45),
        ht_pattern('htG', '#3F6B44', 10, 3.4, 30),
        ht_pattern('htM', '#B08A1E', 10, 3.2, 15),
        check_pattern('chk', CYAN),
        '<filter id="grain" x="0" y="0" width="100%" height="100%">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="11" stitchTiles="stitch"/>'
        '<feColorMatrix type="matrix" values="0 0 0 0 0.10  0 0 0 0 0.08  0 0 0 0 0.06  2.6 0 0 0 -1.15"/></filter>',
    ])

def grain(w, h, op=0.16):
    return f'<rect x="0" y="0" width="{w}" height="{h}" filter="url(#grain)" opacity="{op}"/>'

def drop_pts(x, y, size, ang=0):
    """teardrop pointing up (ang rotates), (x,y) = centre of the bulb."""
    r = size / 2
    loc = hull(ellipse_pts(0, 0, r, r, 40) + [(0, -size * 1.25)])
    return xf(loc, x, y, ang)

def shrub():
    out = []
    pot = [(18, 744), (132, 744), (120, 838), (30, 838)]
    leaves = []
    for k, (x, y, r) in enumerate([(30, 690, 42), (78, 650, 52), (122, 690, 40), (60, 714, 40), (104, 720, 36), (50, 610, 34), (104, 600, 36)]):
        leaves.append(ellipse_pts(x, y, r, r * 0.9, 40))
    blob = hull([p for l in leaves for p in l])
    # bumpy outline from circles union approximated by hull + scallops
    bumpy = []
    n = len(resample(blob, 6))
    rb = resample(blob, 6)
    cxs = sum(p[0] for p in rb) / n; cys = sum(p[1] for p in rb) / n
    for j, p in enumerate(rb):
        k = 1 + 0.05 * abs(math.sin(j * math.pi / 6))
        bumpy.append((cxs + (p[0] - cxs) * k, cys + (p[1] - cys) * k))
    out.append(inked(bumpy, GREEN, (6, 9), 71, inner=crescent(bumpy, 'htG', -18, -16, 0.7)))
    for j in range(5):
        a = 0.7 + j * 1.1
        x = cxs + math.cos(a) * 30; y = cys + math.sin(a) * 30
        out.append(stroke(qbez((x - 10, y + 6), (x, y - 4), (x + 12, y + 2), 10), 4, taper=(0.3, 0.3)))
    out.append(inked(pot, ROSE, (6, 9), 72, inner=crescent(pot, 'htK', -20, 0, 0.25)))
    out.append(inked([(10, 740), (140, 740), (140, 760), (10, 760)], ROSE, (5, 7), 73))
    return ''.join(out)

def small_table(cx, ty, r=58, cloth=CLOTH, seed=80):
    out = []
    out.append(stroke([(cx, ty + 8), (cx, ty + 66)], 10, taper=(0, 0)))
    out.append(stroke([(cx - 30, ty + 70), (cx + 30, ty + 70)], 9, taper=(0.2, 0.2)))
    top = ellipse_pts(cx, ty, r, r * 0.2, 60)
    out.append(inked(top, cloth, (5, 7), seed))
    return ''.join(out)

def floor():
    out = []
    out.append(f'<rect x="0" y="800" width="1080" height="1120" fill="#E5DBC5"/>')
    out.append(stroke([(-10, 800), (1090, 801)], 8, taper=(0, 0)))
    # far floor gets a faint cyan wash of tiny dots, near band a coarse fade
    out.append(ht_fade(0, 1575, 1080, 1920, CYAN, pitch=10, rmax=4.0, rmin=0.3, power=1.1))
    return ''.join(out)

def teacup(cx, cy):
    """brim-full cup on a saucer; returns (svg, rim_y, rh)."""
    out = []
    rw, rh = 86, 19
    rim_y = cy - 46
    sau = ellipse_pts(cx, cy + 50, 124, 23, 80)
    out.append(inked(sau, CLOTH, (6, 9), 91, inner=crescent(sau, 'htC', 0, -9, 0.6)))
    out.append(stroke(qbez((cx - 82, cy + 50), (cx, cy + 66), (cx + 82, cy + 50)), 4, taper=(0.3, 0.3)))
    # handle (toward Bix = left)
    hd = spline([(cx - 70, rim_y + 20), (cx - 122, rim_y + 18), (cx - 124, rim_y + 60), (cx - 58, rim_y + 72)], False, 10)
    out.append(stroke(hd, 24))
    out.append(stroke(hd, 10, color=CLOTH, taper=(0.15, 0.15)))
    body = [(cx - rw, rim_y), (cx - rw + 4, rim_y + 40), (cx - 58, rim_y + 80), (cx, rim_y + 92), (cx + 58, rim_y + 80), (cx + rw - 4, rim_y + 40), (cx + rw, rim_y)]
    body = spline(body, True, 10)
    band = [(cx - 100, rim_y + 26), (cx + 100, rim_y + 26), (cx + 100, rim_y + 44), (cx - 100, rim_y + 44)]
    inner = clipped(body, f'<path d="{P(band)}" fill="{ROSE}"/>', OFF) + crescent(body, 'htC', -18, 0, 0.7)
    out.append(inked(body, CLOTH, (6, 10), 92, inner=inner))
    # rim + brim-full tea, exactly level with the rim
    rim = ellipse_pts(cx, rim_y, rw, rh, 90)
    tea = ellipse_pts(cx, rim_y + 1, rw - 7, rh - 5, 90)
    out.append(f'<path d="{P(rim)}" fill="{CLOTH}"/>')
    out.append(f'<path d="{P(tea)}" fill="#A9682F"/>')
    out.append(clipped(tea, f'<path d="{P(ellipse_pts(cx - 10, rim_y - 7, rw - 20, rh - 9, 60))}" fill="#C98A4A"/>'))
    out.append(stroke(qbez((cx - 40, rim_y - 5), (cx, rim_y - 11), (cx + 34, rim_y - 6)), 4, color=CLOTH, taper=(0.3, 0.3)))
    out.append(f'<path d="{ring_d(rim, 5, 8, 0.5, 93)}" fill="{INK}" fill-rule="evenodd"/>')
    return ''.join(out), rim_y, rh

def steam(cx, rim_y):
    out = []
    for k, (dx, h, ph) in enumerate([(-44, 170, 0.0), (0, 215, 1.7), (44, 180, 3.1)]):
        pts = []
        for j in range(41):
            t = j / 40
            pts.append((cx + dx + 18 * math.sin(t * 2.4 * math.pi + ph) * (0.4 + t), rim_y - 8 - h * t))
        out.append(stroke(pts, 13, color=INK, taper=(0.25, 0.5), wmin=0.25))
        out.append(stroke(pts, 7, color=CLOTH, taper=(0.25, 0.5), wmin=0.2))
    return ''.join(out)

def doughnut(cx, cy, ow=78, oh=34):
    out = []
    hole = ellipse_pts(cx + 2, cy - 5, ow * 0.30, oh * 0.28, 40)
    side = ellipse_pts(cx, cy + 9, ow, oh, 90)
    out.append(inked(side, '#D9A066', (6, 9), 101, inner=crescent(side, 'htM', 0, -10, 0.6)))
    g = [(cx + ow * 0.98 * math.cos(t) + 3 * math.sin(7 * t), cy - 2 + oh * 0.92 * math.sin(t) + (6 * abs(math.sin(5 * t)) if math.sin(t) > 0.2 else 0)) for t in (2 * math.pi * k / 90 for k in range(90))]
    d = P(xf(g, *OFF)) + ' ' + P(hole[::-1])
    out.append(f'<path d="{d}" fill="{ROSE}" fill-rule="evenodd"/>')
    out.append(f'<path d="{ring_d(g, 5, 8, 0.6, 102)}" fill="{INK}" fill-rule="evenodd"/>')
    out.append(f'<path d="{P(hole)}" fill="{CREAM}"/>')
    out.append(clipped(hole, f'<path d="{P(ellipse_pts(cx + 2, cy + 2, ow * 0.30, oh * 0.28, 40))}" fill="#D9A066"/>'))
    out.append(f'<path d="{P(hole)}" fill="none" stroke="{INK}" stroke-width="5"/>')
    rnd = random.Random(4)
    for k in range(12):
        a = rnd.random() * 2 * math.pi; rr = 0.55 + 0.3 * rnd.random()
        x = cx + math.cos(a) * ow * rr; y = cy - 3 + math.sin(a) * oh * rr * 0.9
        if abs(x - cx) < ow * 0.38 and abs(y - cy + 4) < oh * 0.4:
            continue
        b = rnd.random() * 3
        out.append(stroke([(x - 6 * math.cos(b), y - 6 * math.sin(b)), (x + 6 * math.cos(b), y + 6 * math.sin(b))], 5, color=CLOTH if k % 3 else MUSTARD, taper=(0.1, 0.1), wmin=0.7))
    out.append(stroke(qbez((cx - ow * 0.62, cy - oh * 0.3), (cx - ow * 0.38, cy - oh * 0.75), (cx - ow * 0.05, cy - oh * 0.8)), 6, color=CLOTH, taper=(0.3, 0.3)))
    return ''.join(out)

def glaze_drip(x, y, ln):
    """one fat rose drop of glaze hanging off the doughnut, about to fall in."""
    out = []
    neck = [(x - 7, y - 6), (x + 7, y - 6), (x + 4, y + ln * 0.6), (x - 4, y + ln * 0.6)]
    out.append(f'<path d="{P(neck)}" fill="{ROSE}"/>')
    bulb = ellipse_pts(x, y + ln * 0.75, 10, 12, 30)
    shape = hull(bulb + [(x - 6, y - 4), (x + 6, y - 4)])
    out.append(inked(shape, ROSE, (3.5, 5), 104, bias=0.6))
    out.append(f'<circle cx="{f1(x - 3)}" cy="{f1(y + ln * 0.72)}" r="3" fill="{CLOTH}"/>')
    return ''.join(out)

def newspaper(x0, y0, x1, y1):
    out = []
    pts = [(x0, y0), (x1, y0 + 6), (x1 - 4, y1), (x0 + 6, y1 + 4)]
    out.append(inked(pts, CLOTH, (5, 8), 160))
    mid = (x0 + x1) / 2
    bars = []
    for col in range(4):
        cx0 = x0 + 14 + col * (x1 - x0 - 24) / 4
        for r in range(9):
            yy = y0 + 18 + r * 15
            if yy > y1 - 12:
                break
            wbar = (x1 - x0 - 24) / 4 - 14 - (18 if (r * 7 + col * 3) % 5 == 0 else 0)
            bars.append(f'<rect x="{f1(cx0)}" y="{f1(yy)}" width="{f1(wbar)}" height="7" fill="url(#htKs)"/>')
    out.append(clipped(pts, ''.join(bars)))
    out.append(stroke([(mid, y0 + 4), (mid + 2, y1)], 4, taper=(0.1, 0.1)))
    return ''.join(out)


# ======================================================================== palette (round-head round)
SKIN_B = '#B07A55'; SKIN_G = '#E8C3A0'; SKIN_W = '#8C5A3C'
NOSE_B = '#9E6A49'; NOSE_G = '#D98A80'; NOSE_W = '#71462E'
TEA = '#A9682F'; TEA_HI = '#C98A4A'; FLOOR = '#E5DBC5'; LOAFER = '#6E4526'
BELT = '#5B3A24'; BRASS = '#C9A23A'; HAIR_GREY = '#D2CBBD'; GLASS = '#DCE7E6'; WALL = CREAM


def shade_hex(h, k):
    """k > 0 darkens, k < 0 lightens toward white."""
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if k >= 0:
        v = [c * (1 - k) for c in (r, g, b)]
    else:
        v = [c + (255 - c) * (-k) for c in (r, g, b)]
    return '#%02X%02X%02X' % tuple(max(0, min(255, round(c))) for c in v)


def padd(p, v, k=1.0):
    return (p[0] + v[0] * k, p[1] + v[1] * k)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def DIR(a):
    """unit direction for an angle measured from straight DOWN: 0 down, 90 screen-right, -90 left, 180 up."""
    r = math.radians(a)
    return (math.sin(r), math.cos(r))


def ang_of(v):
    return math.degrees(math.atan2(v[0], v[1]))

# ======================================================================== STICK BODY RIG
def ink_poly(pts, w0, w1, swell=0.10, seed=0, step=2.5, wmin=9.0, capn=10):
    """variable-width ink stroke with ROUND caps at both ends."""
    pts = resample(pts, step, False)
    n = len(pts)
    ph = random.Random(seed).random() * 6.28
    Lp, Rp, W = [], [], []
    for i in range(n):
        p0 = pts[max(i - 1, 0)]; p2 = pts[min(i + 1, n - 1)]
        tx, ty = p2[0] - p0[0], p2[1] - p0[1]; l = math.hypot(tx, ty) or 1
        nx, ny = -ty / l, tx / l
        s_ = i / (n - 1)
        w = (w0 + (w1 - w0) * s_) * (1 + swell * (0.6 * math.sin(math.pi * s_) + 0.4 * math.sin(s_ * 7.0 + ph)))
        w = max(wmin, w); W.append(w)
        Lp.append((pts[i][0] + nx * w / 2, pts[i][1] + ny * w / 2))
        Rp.append((pts[i][0] - nx * w / 2, pts[i][1] - ny * w / 2))

    def tangent(i, j):
        tx, ty = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]; l = math.hypot(tx, ty) or 1
        return tx / l, ty / l
    te = tangent(n - 2, n - 1); ts = tangent(0, 1)
    an_e = math.atan2(te[0], -te[1]); an_s = math.atan2(ts[0], -ts[1])
    end = [(pts[-1][0] + W[-1] / 2 * math.cos(an_e - math.pi * k / capn), pts[-1][1] + W[-1] / 2 * math.sin(an_e - math.pi * k / capn)) for k in range(1, capn)]
    beg = [(pts[0][0] + W[0] / 2 * math.cos(an_s + math.pi - math.pi * k / capn), pts[0][1] + W[0] / 2 * math.sin(an_s + math.pi - math.pi * k / capn)) for k in range(1, capn)]
    return Lp + end + Rp[::-1] + beg


def ik(S, T, a, b, bend=1):
    """two-bone IK; bend +1 / -1 picks the elbow (knee) side.  Clamped just short of fully straight."""
    dx, dy = T[0] - S[0], T[1] - S[1]
    d = math.hypot(dx, dy) or 1
    d = max(abs(a - b) + 1, min(a + b - 0.5, d))
    ang = math.atan2(dy, dx)
    al = math.acos(max(-1, min(1, (a * a + d * d - b * b) / (2 * a * d))))
    ea = ang + bend * al
    E = (S[0] + a * math.cos(ea), S[1] + a * math.sin(ea))
    W = (S[0] + d * math.cos(ang), S[1] + d * math.sin(ang))
    return E, W


# shoe outline in D units: u along the toe, v toward the sole (flat sole at v = 0.07)
SHOE = [(-0.06, -0.045), (-0.10, -0.005), (-0.095, 0.07), (0.05, 0.07), (0.185, 0.07), (0.232, 0.045),
        (0.228, 0.002), (0.17, -0.032), (0.06, -0.058)]


class Body:
    """neck stub + collar anchor + tapered spine + hip prop, limbs as tapered ink over an off-register plate."""

    def __init__(s, D, facing, plate, glove, shoe='brogue', seed=400, L=None, knuckle=False, glove_skin=False):
        s.D, s.f, s.plate, s.glove, s.shoe_kind, s.seed, s.knuckle = D, facing, plate, glove, shoe, seed, knuckle
        s.L = dict(neck_x=0.10, neck_top=0.30, neck_vis=0.12, neck_w=0.18, yoke=0.065, sh=0.27, sh_drop=0.035,
                   spine=0.97, up=0.68, fore=0.70, thigh=0.78, shin=0.72, hand=0.20, hand_w=0.13, sole=0.07)
        s.L.update(L or {})
        s.wl = (max(0.067 * D, 15.0), max(0.045 * D, 12.0))
        s.ws = (max(0.075 * D, s.wl[0] + 2), max(0.06 * D, s.wl[1] + 1.5))
        s.POFF = (4, 4.5)

    # ------------------------------------------------------------------ joints
    def joints(s, face, p):
        D, f, L = s.D, s.f, s.L
        C = (face.cx, face.cy)
        tilt = p.get('tilt', 0)
        ndir = DIR(-f * p.get('neck', 10))
        Nt = rot((C[0] - f * L['neck_x'] * D, C[1] + L['neck_top'] * D), tilt, C)
        v = (Nt[0] - C[0], Nt[1] - C[1])
        b = v[0] * ndir[0] + v[1] * ndir[1]; c = v[0] ** 2 + v[1] ** 2 - face.R ** 2
        se = -b + math.sqrt(max(0.0, b * b - c))
        Ne = padd(Nt, ndir, se)
        Nb = padd(Ne, ndir, L['neck_vis'] * D)
        a_top = p.get('spine_top', p.get('spine', 0)); sd = DIR(a_top); rt = (sd[1], -sd[0])
        Y = padd(Nb, sd, L['yoke'] * D)
        yk = p.get('yoke_k', 0.92 if abs(face.turn) >= 0.3 else 1.0)
        Sn = padd(padd(Y, rt, f * L['sh'] * D * yk * p.get('sh_nk', 1.0)), sd, L['sh_drop'] * D)
        Sf = padd(padd(Y, rt, -f * L['sh'] * D * yk * p.get('sh_fk', 1.0)), sd, L['sh_drop'] * D)
        a_sp = p.get('spine', 0); d2 = DIR(a_sp); rt2 = (d2[1], -d2[0])
        H = padd(Y, d2, L['spine'] * D)
        M = padd(lerp(Y, H, 0.5), rt2, f * p.get('bow', 0) * D)
        J = dict(C=C, Nt=Nt, Ne=Ne, Nb=Nb, Y=Y, Sn=Sn, Sf=Sf, H=H, M=M, sd=sd, rt=rt, ndir=ndir, pose=p, a_sp=a_sp)
        J['spine_pts'] = spline([Nb, Y, M, H], False, 14)
        for k, S in (('n', Sn), ('f', Sf)):
            up, fo = L['up'] * D * p.get(k + 'up_k', 1.0), L['fore'] * D * p.get(k + 'lo_k', 1.0)
            if k + 'str' in p:
                d = DIR(p[k + 'str']); E = padd(S, d, up); W = padd(E, d, fo)
            elif k + 'Wr' in p:
                T = (S[0] + p[k + 'Wr'][0] * D, S[1] + p[k + 'Wr'][1] * D)
                E, W = ik(S, T, up, fo, p.get(k + 'bend', 1))
            elif k + 'Wt' in p:
                E, W = ik(S, p[k + 'Wt'], up, fo, p.get(k + 'bend', 1))
            else:
                E = padd(S, DIR(p[k + 'up']), up); W = padd(E, DIR(p[k + 'lo']), fo)
            J[k + 'E'], J[k + 'W'] = E, W
            J[k + 'hand_ang'] = p.get(k + 'hand', ang_of((W[0] - E[0], W[1] - E[1])))
            lk = p.get(k + 'leg_k', 1.0)
            th, sh = L['thigh'] * D * lk, L['shin'] * D * lk
            if k + 'Ft' in p:
                K, A = ik(H, p[k + 'Ft'], th, sh, p.get(k + 'kbend', -f))
            elif k + 'Fr' in p:
                T = (H[0] + p[k + 'Fr'][0] * D, H[1] + p[k + 'Fr'][1] * D)
                K, A = ik(H, T, th, sh, p.get(k + 'kbend', -f))
            else:
                K = padd(H, DIR(p[k + 'th']), th); A = padd(K, DIR(p[k + 'sh']), sh)
            J[k + 'K'], J[k + 'F'] = K, A
            J[k + 'shoe'], J[k + 'td'], J[k + 'sn'] = s.shoe_poly(A, p.get(k + 'toe', 90 * f), p.get(k + 'sole', 0))
        return J

    def shoe_poly(s, A, toe_ang, sole=0):
        td = DIR(toe_ang)
        n1 = (-td[1], td[0]); n2 = (td[1], -td[0])
        sn = n1 if (sole > 0 or (sole == 0 and n1[1] >= n2[1])) else n2
        loc = spline(SHOE, True, 8)
        return [(A[0] + (td[0] * u + sn[0] * v) * s.D, A[1] + (td[1] * u + sn[1] * v) * s.D) for u, v in loc], td, sn

    # ------------------------------------------------------------------ parts
    def limb_svg(s, p0, p1, p2, seed):
        w0, w2 = s.wl; w1 = (w0 + w2) / 2
        a = ink_poly([p0, p1], w0, w1, seed=seed); b = ink_poly([p1, p2], w1, w2, seed=seed + 1)
        ap = ink_poly([p0, p1], w0 + 4, w1 + 4, seed=seed); bp = ink_poly([p1, p2], w1 + 4, w2 + 4, seed=seed + 1)
        return (f'<path d="{P(xf(ap, *s.POFF))}" fill="{s.plate}"/><path d="{P(xf(bp, *s.POFF))}" fill="{s.plate}"/>'
                f'<path d="{P(a)}" fill="{INK}"/><path d="{P(b)}" fill="{INK}"/>')

    def spine_svg(s, J):
        pts = J['spine_pts']
        a = ink_poly(pts, s.ws[0], s.ws[1], swell=0.06, seed=s.seed + 5)
        ap = ink_poly(pts, s.ws[0] + 4, s.ws[1] + 4, swell=0.06, seed=s.seed + 5)
        return f'<path d="{P(xf(ap, *s.POFF))}" fill="{s.plate}"/><path d="{P(a)}" fill="{INK}"/>'

    def yoke_svg(s, J):
        Sf, Sn, Y, sd = J['Sf'], J['Sn'], J['Y'], J['sd']
        pts = qbez(Sf, padd(Y, sd, -0.03 * s.D), Sn, 16)
        a = ink_poly(pts, s.wl[0], s.wl[0], swell=0.0, seed=s.seed + 6)
        return f'<path d="{P(a)}" fill="{INK}"/>'

    def neck_svg(s, J, skin):
        D = s.D; nd = J['ndir']; nn = (-nd[1], nd[0])
        hw0, hw1 = s.L['neck_w'] / 2 * D, (s.L['neck_w'] / 2 + 0.012) * D
        top = J['Nt']; base = padd(J['Nb'], nd, 0.03 * D)
        poly = [padd(top, nn, hw0), padd(base, nn, hw1), padd(base, nn, -hw1), padd(top, nn, -hw0)]
        c0 = padd(J['Ne'], nd, -0.05 * D); c1 = padd(J['Ne'], nd, 0.045 * D)
        band = [padd(c0, nn, hw1 + 8), padd(c1, nn, hw1 + 8), padd(c1, nn, -hw1 - 8), padd(c0, nn, -hw1 - 8)]
        inner = clipped(poly, f'<path d="{P(xf(band, *OFF))}" fill="{shade_hex(skin, 0.12)}"/>'
                              f'<path d="{P(xf(band, *OFF))}" fill="url(#htKs)" opacity="0.45"/>', OFF)
        out = f'<path d="{P(xf(poly, *OFF))}" fill="{skin}"/>' + inner
        for sg in (1, -1):
            out += stroke([padd(top, nn, sg * hw0), padd(base, nn, sg * hw1)], 0.02 * D, taper=(0.05, 0.05))
        return out

    def mitten_pts(s, Wp, ang, flat=1.0):
        Lh = s.L['hand'] * s.D; Wd = s.L['hand_w'] * s.D
        d = DIR(ang); n = (-d[1], d[0])
        pts = []
        for i in range(48):
            t = 2 * math.pi * i / 48
            u = Lh * 0.40 + Lh * 0.60 * math.cos(t)
            v = Wd / 2 * flat * math.sin(t) * (1 + 0.14 * math.cos(t))
            pts.append((Wp[0] + d[0] * u + n[0] * v, Wp[1] + d[1] * u + n[1] * v))
        return pts

    def thumb_pts(s, Wp, ang, side, flat=1.0, along=0.36, spread=50):
        Lh = s.L['hand'] * s.D; Wd = s.L['hand_w'] * s.D
        d = DIR(ang); n = (-d[1], d[0])
        c = (Wp[0] + d[0] * Lh * along + n[0] * side * Wd * 0.48 * flat, Wp[1] + d[1] * Lh * along + n[1] * side * Wd * 0.48 * flat)
        td = DIR(ang - side * spread); tn = (-td[1], td[0])
        pts = []
        for i in range(30):
            t = 2 * math.pi * i / 30
            u = Lh * 0.24 * math.cos(t) + Lh * 0.12; v = Wd * 0.27 * math.sin(t)
            pts.append((c[0] + td[0] * u + tn[0] * v, c[1] + td[1] * u + tn[1] * v))
        return pts

    def hand_svg(s, J, k):
        p = J['pose']; grip = p.get(k + 'grip', 'mitt')
        if grip == 'hidden':
            return ''
        flat = 0.72 if grip == 'flat' else 1.0
        pts = s.mitten_pts(J[k + 'W'], J[k + 'hand_ang'], flat)
        inner = ''
        if s.knuckle:
            Lh = s.L['hand'] * s.D; d = DIR(J[k + 'hand_ang']); W0 = J[k + 'W']
            kc = (W0[0] + d[0] * Lh * 0.74, W0[1] + d[1] * Lh * 0.74)
            inner = clipped(pts, f'<circle cx="{f1(kc[0] + OFF[0])}" cy="{f1(kc[1] + OFF[1])}" r="{f1(Lh * 0.45)}" fill="url(#htRs)"/>', OFF)
        return inked(pts, s.glove, (0.016 * s.D, 0.026 * s.D), s.seed + (11 if k == 'n' else 17), inner=inner)

    def thumb_svg(s, J, k):
        p = J['pose']; grip = p.get(k + 'grip', 'mitt')
        if grip == 'hidden' or p.get(k + 'nothumb'):
            return ''
        flat = 0.72 if grip == 'flat' else 1.0
        pts = s.thumb_pts(J[k + 'W'], J[k + 'hand_ang'], p.get(k + 'thumb', 1), flat, p.get(k + 'thumb_at', 0.36), p.get(k + 'thumb_sp', 50))
        return inked(pts, s.glove, (0.012 * s.D, 0.02 * s.D), s.seed + (21 if k == 'n' else 27))

    def shoe_svg(s, J, k):
        pts = J[k + 'shoe']; td = J[k + 'td']; sn = J[k + 'sn']; A = J[k + 'F']; D = s.D
        Wf = lambda u, v: (A[0] + (td[0] * u + sn[0] * v) * D, A[1] + (td[1] * u + sn[1] * v) * D)
        out = []
        if s.shoe_kind == 'brogue':
            out.append(f'<path d="{P(xf(pts, *s.POFF))}" fill="{s.plate}"/>')
            out.append(f'<path d="{P(pts)}" fill="{INK}"/>')
            out.append(stroke(qbez(Wf(0.10, -0.035), Wf(0.17, -0.025), Wf(0.205, 0.0), 10), 0.022 * D, color=WHITE, taper=(0.3, 0.3)))
            for j in range(4):
                q = Wf(0.075 - 0.004 * j, -0.04 + 0.024 * j)
                out.append(f'<circle cx="{f1(q[0])}" cy="{f1(q[1])}" r="{f1(0.0075 * D)}" fill="{CLOTH}"/>')
            out.append(stroke([Wf(-0.085, 0.052), Wf(0.18, 0.052)], 0.01 * D, color='#5A5A5A', taper=(0.1, 0.1)))
        else:
            Kn = J[k + 'K']
            dv = (A[0] - Kn[0], A[1] - Kn[1]); dl = math.hypot(*dv) or 1; dv = (dv[0] / dl, dv[1] / dl)
            sock = ink_poly([padd(A, dv, -0.10 * D), padd(A, dv, 0.0)], 0.10 * D, 0.10 * D, swell=0, wmin=1)
            out.append(inked(sock, MUSTARD, (0.012 * D, 0.018 * D), s.seed + 60))
            out.append(inked(pts, LOAFER, (0.014 * D, 0.022 * D), s.seed + 61))
            out.append(stroke(qbez(Wf(0.05, -0.05), Wf(0.11, -0.03), Wf(0.16, -0.04), 10), 0.014 * D, taper=(0.2, 0.2)))
            out.append(stroke(qbez(Wf(0.16, -0.02), Wf(0.20, -0.012), Wf(0.215, 0.012), 8), 0.014 * D, color='#C79A6B', taper=(0.3, 0.3)))
        return ''.join(out)

    def layers(s, J, skin):
        out = {}
        for k, sd in (('f', 40), ('n', 50)):
            out[k + '_leg'] = s.limb_svg(J['H'], J[k + 'K'], J[k + 'F'], s.seed + sd) + s.shoe_svg(J, k)
            out[k + '_arm'] = s.limb_svg(J['S' + k], J[k + 'E'], J[k + 'W'], s.seed + sd + 5)
            out[k + '_hand'] = s.hand_svg(J, k)
            out[k + '_thumb'] = s.thumb_svg(J, k)
        out['spine'] = s.spine_svg(J)
        out['yoke'] = s.yoke_svg(J)
        out['neck'] = s.neck_svg(J, skin)
        return out

    def halo(s, J, color=CREAM, op=0.4, pad=16):
        """knock the background texture back under the limbs (tile seams / glass halftone -40 %)."""
        segs = [(J['H'], J['nK'], J['nF']), (J['H'], J['fK'], J['fF']), (J['Sn'], J['nE'], J['nW']), (J['Sf'], J['fE'], J['fW'])]
        out = []
        for a, b, c in segs:
            out.append(stroke([a, b, c], s.wl[0] + pad, color=color, taper=(0.02, 0.02)))
        out.append(stroke(J['spine_pts'], s.ws[0] + pad, color=color, taper=(0.02, 0.02)))
        return f'<g opacity="{op}">{"".join(out)}</g>'

    # ------------------------------------------------------------------ checks
    def arm_clearance(s, J, face, k):
        R = face.R; C = (face.cx, face.cy)
        d = min(seg_dist(C, J['S' + k], J[k + 'E']), seg_dist(C, J[k + 'E'], J[k + 'W']))
        return (d - R - s.wl[0] / 2) / s.D


def figure(face, E, body, J, order, **parts):
    L = body.layers(J, face.skin)
    L.update(parts)
    L['head'] = face.draw(E)
    return ''.join(L.get(k, '') for k in order)


ORDER = ['shadow', 'halo', 'f_leg', 'f_arm', 'f_hand', 'spine', 'yoke', 'hip_back', 'n_leg', 'hip', 'neck', 'collar',
         'head', 'n_arm', 'n_hand', 'prop', 'f_thumb', 'n_thumb', 'marks']


def place(face_fn, body, pose, head_x, floor_y, stand='n'):
    """build the head at head_x, then slide everything so the standing shoe sits on the floor."""
    f0 = face_fn(head_x, 0.0)
    J0 = body.joints(f0, pose)
    low = max(q[1] for q in J0[stand + 'shoe'])
    f = face_fn(head_x, floor_y - low)
    return f, body.joints(f, pose)


# ======================================================================== costume props
def collar_points(J, D, fill, seed, f, open_=0.0, drop=0.17):
    """two brush-outlined collar points; their outer corners ARE the shoulder points."""
    sd, rt, Nb = J['sd'], J['rt'], J['Nb']
    out = []
    for sg in (-1, 1):
        S = J['Sn'] if sg * f > 0 else J['Sf']
        inner = padd(padd(Nb, rt, sg * (0.045 + open_) * D), sd, -0.02 * D)
        outer = padd(S, sd, -0.012 * D)
        tip = padd(padd(Nb, rt, sg * (0.10 + open_) * D), sd, drop * D)
        tri = spline([inner, lerp(inner, outer, 0.5), outer, lerp(outer, tip, 0.5), tip, lerp(tip, inner, 0.5)], True, 5)
        out.append(inked(tri, fill, (0.013 * D, 0.022 * D), seed + sg))
    return ''.join(out)


def bow_tie(c, ang, D, seed, squash=1.0, width=0.40):
    size = width / 1.06 * D
    bl = [(0, -0.05), (-0.48, -0.25), (-0.53, 0.23), (0, 0.07)]
    out = []
    for sd in (-1, 1):
        loc = spline([(x * size * sd * squash, y * size * 0.78) for x, y in bl], True, 6)
        w = xf(loc, c[0], c[1], ang)
        out.append(inked(w, ROSE, (0.013 * D, 0.02 * D), seed + sd,
                         inner=clipped(w, f'<rect x="{f1(c[0] - size)}" y="{f1(c[1])}" width="{f1(2 * size)}" height="{f1(size)}" fill="url(#htRs)" opacity="0.7"/>', OFF)))
        crease = xf([(sd * size * 0.16 * squash, -0.02 * size), (sd * size * 0.34 * squash, -0.09 * size)], c[0], c[1], ang)
        out.append(stroke(crease, 0.012 * D, taper=(0.2, 0.3), wmin=0.5))
    out.append(inked(xf(ellipse_pts(0, 0.01 * size, size * 0.12 * max(squash, 0.8), size * 0.13, 30), c[0], c[1], ang), ROSE, (0.011 * D, 0.017 * D), seed + 5))
    return ''.join(out)


def apron(H, spine_ang, D, hang, spread, seed, facing, length=1.05, wb=0.30, flutter=0.0, tails=None):
    t = DIR(spine_ang); n = (-t[1], t[0])
    R = length * D
    tl = padd(H, n, wb * D / 2); tr = padd(H, n, -wb * D / 2)
    a0 = hang - spread / 2; a1 = hang + spread / 2
    N = 30
    rr = lambda i: R * (1 + flutter * math.sin(i * math.pi * 6 / N) * (0.3 + 0.7 * i / N))
    arc = [padd(H, DIR(a0 + (a1 - a0) * i / N), rr(i)) for i in range(N + 1)]
    if math.dist(tl, arc[0]) + math.dist(tr, arc[-1]) > math.dist(tl, arc[-1]) + math.dist(tr, arc[0]):
        arc = arc[::-1]
    poly = [tl] + arc + [tr]
    npl = 5
    inner = []
    for j in range(npl):
        if j % 2 == 1:
            w = [lerp(tl, tr, j / npl), lerp(tl, tr, (j + 1) / npl)] + arc[int(N * (j + 1) / npl)::-1][:int(N / npl) + 1]
            inner.append(f'<path d="{P(xf(w, *OFF))}" fill="url(#htCs)" opacity="0.9"/>')
    inner.append(crescent(poly, 'htC', -0.05 * D * facing, -0.03 * D, 0.35))
    band_o = [padd(H, DIR(a0 + (a1 - a0) * i / N), rr(i) * 0.94) for i in range(N + 1)]
    band_i = [padd(H, DIR(a0 + (a1 - a0) * i / N), rr(i) * 0.88) for i in range(N + 1)]
    inner.append(f'<path d="{P(xf(band_o + band_i[::-1], *OFF))}" fill="{CYAN}"/>')
    body = clipped(poly, ''.join(inner), (0, 0))
    out = [inked(poly, CLOTH, (0.018 * D, 0.028 * D), seed, inner=body)]
    for j in range(1, npl):
        a = lerp(tl, tr, j / npl); b = arc[int(N * j / npl)]
        out.append(stroke([lerp(a, b, 0.08), lerp(a, b, 0.86)], 0.012 * D, taper=(0.3, 0.3), wmin=0.4))
    out.append(stroke([padd(tl, t, 3), padd(tr, t, 3)], 0.034 * D, taper=(0.05, 0.05)))
    if tails is not None:
        back = tl if (tl[0] - H[0]) * facing < 0 else tr
        for k, (da, ln) in enumerate(((-9, 0.22), (11, 0.17))):
            d = DIR(tails + da); nn = (-d[1], d[0])
            q = [padd(back, nn, -0.022 * D), padd(back, nn, 0.022 * D), padd(padd(back, d, ln * D), nn, 0.018 * D), padd(padd(back, d, ln * D), nn, -0.018 * D)]
            out.append(inked(q, CLOTH, (0.011 * D, 0.015 * D), seed + 9 + k))
    return ''.join(out)


def necktie(c, ang, L, w, seed, D, bend=0.0):
    def B(p):
        x, y = p
        return (x + bend * L * (max(y, 0) / L) ** 2, y)
    blade = [B(p) for p in spline([(-0.17 * w, 0.10 * w), (0.17 * w, 0.10 * w), (0.36 * w, 0.45 * L), (0.50 * w, 0.84 * L),
                                   (0.0, L), (-0.50 * w, 0.84 * L), (-0.36 * w, 0.45 * L)], True, 6)]
    knot = spline([(-0.30 * w, -0.17 * w), (0.30 * w, -0.17 * w), (0.19 * w, 0.20 * w), (-0.19 * w, 0.20 * w)], True, 5)
    bw = xf(blade, c[0], c[1], -ang); kn = xf(knot, c[0], c[1], -ang)
    out = []
    for poly, sd in ((bw, 0), (kn, 3)):
        x, y = min(q[0] for q in poly) - 40, min(q[1] for q in poly) - 40
        inner = clipped(poly, f'<rect x="{f1(x)}" y="{f1(y)}" width="400" height="400" fill="url(#chk)"/>', OFF) + crescent(poly, 'htM', -10, -6, 0.6)
        out.append(inked(poly, MUSTARD, (0.014 * D, 0.021 * D), seed + sd, inner=inner))
    return ''.join(out)


def belt(H, spine_ang, D, seed):
    t = DIR(spine_ang); n = (t[1], -t[0])
    hw, hh = 0.17 * D, 0.04 * D
    pts = [padd(padd(H, n, -hw), t, -hh), padd(padd(H, n, hw), t, -hh), padd(padd(H, n, hw), t, hh), padd(padd(H, n, -hw), t, hh)]
    out = [inked(spline(pts, True, 4), BELT, (0.012 * D, 0.018 * D), seed)]
    bw, bh = 0.055 * D, 0.05 * D
    bk = [padd(padd(H, n, -bw), t, -bh), padd(padd(H, n, bw), t, -bh), padd(padd(H, n, bw), t, bh), padd(padd(H, n, -bw), t, bh)]
    out.append(inked(bk, BRASS, (0.01 * D, 0.015 * D), seed + 1))
    ik_ = [padd(padd(H, n, -bw * 0.45), t, -bh * 0.4), padd(padd(H, n, bw * 0.45), t, -bh * 0.4), padd(padd(H, n, bw * 0.45), t, bh * 0.4), padd(padd(H, n, -bw * 0.45), t, bh * 0.4)]
    out.append(f'<path d="{P(ik_)}" fill="{BELT}"/>')
    return ''.join(out)


CUP_BODY = [(-86, -46), (-82, -6), (-58, 34), (0, 46), (58, 34), (82, -6), (86, -46)]


def cup(bx, by, s=0.75, tip=0.0, bulge=False, drop_up=0.0, flip=False):
    """teacup on its saucer, positioned by the saucer bottom (bx, by)."""
    svg, rim_y, rh = teacup(0, 0)
    extra = []
    if bulge:
        dome = [(22 + 15 * math.cos(t), -59 - 13 * math.sin(t)) for t in (math.pi * j / 24 for j in range(25))]
        extra.append(f'<path d="{P(dome)}" fill="{TEA}"/>')
        extra.append(stroke(dome, 5, taper=(0.12, 0.12), wmin=0.4))
        extra.append(f'<circle cx="17" cy="-65" r="2.6" fill="{WHITE}"/>')
    if drop_up:
        dp = drop_pts(24, -66 - drop_up, 30, 0)
        extra.append(inked(dp, TEA, (4, 6), 77, bias=0.5, off=(2, 2)))
        extra.append(f'<circle cx="19" cy="{f1(-70 - drop_up)}" r="4" fill="{WHITE}"/>')
        for dx in (-24, 72):
            extra.append(stroke([(dx, -70 - drop_up * 0.6), (dx + (9 if dx > 0 else -9), -90 - drop_up * 0.6)], 7, taper=(0.1, 0.6)))
    sx = -s if flip else s
    return (f'<g transform="translate({f1(bx)} {f1(by)}) rotate({f1(tip)}) scale({f1(sx)} {f1(s)}) translate(0 -73)">'
            f'{svg}{"".join(extra)}</g>')


def cup_ghost(bx, by, s, op, flip=False):
    sx = -s if flip else s
    T = lambda pts: [(bx + x * sx, by + (y - 73) * s) for x, y in pts]
    body = T(spline(CUP_BODY, True, 10))
    sau = T(ellipse_pts(0, 50, 124, 23, 70))
    rim = T(ellipse_pts(0, -46, 86, 19, 60))
    hd = T(spline([(-70, -26), (-122, -28), (-124, 14), (-58, 26)], False, 10))
    dash = f'fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round" stroke-dasharray="0.1 10"'
    shapes = (f'<path d="{P(sau)}" fill="{CLOTH}" fill-opacity="0.5"/><path d="{P(sau)}" fill="url(#htCs)"/>'
              f'<path d="{P(body)}" fill="{CLOTH}" fill-opacity="0.5"/><path d="{P(body)}" fill="url(#htC)" opacity="0.8"/>'
              f'<path d="{P(rim)}" fill="{CLOTH}" fill-opacity="0.8"/>'
              f'<path d="{P(sau)}" {dash}/><path d="{P(body)}" {dash}/><path d="{P(rim)}" {dash}/><path d="{P(hd, False)}" {dash}/>')
    return f'<g opacity="{op}">{shapes}</g>'


def held_doughnut(cx, cy, s, tip, drip=True):
    ow, oh = 78, 34
    inner = doughnut(0, 0, ow, oh)
    if drip:
        inner += glaze_drip(6, oh + 6, 30)
    return f'<g transform="translate({f1(cx)} {f1(cy)}) rotate({f1(tip)}) scale({f1(s)})">{inner}</g>'


def steam_small(cx, rim_y, s):
    return f'<g transform="translate({f1(cx)} {f1(rim_y)}) scale({f1(s)})">{steam(0, 0)}</g>'


def dotted(pts, D=270, op=0.9, r=None):
    pts = resample(pts, max(10.0, 0.05 * D), False)
    r = r or max(3.2, 0.013 * D)
    return f'<g fill="{INK}" opacity="{op}">' + ''.join(f'<circle cx="{f1(x)}" cy="{f1(y)}" r="{f1(r)}"/>' for x, y in pts[1:-1]) + '</g>'


def black_defs():
    return '<filter id="blk"><feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>'
# ======================================================================== SCENE: café terrace
def awning2(y0=236, y1=316, yv=350):
    out = []
    sw = 60
    x = -20; k = 0
    while x < 1100:
        col = CYAN if k % 2 == 0 else CREAM
        sc = [(x + sw / 2 + sw / 2 * math.cos(t), y1 + (yv - y1) * math.sin(t)) for t in (math.pi * j / 20 for j in range(21))]
        pts = [(x, y0), (x + sw, y0), (x + sw, y1)] + sc + [(x, y1)]
        out.append(f'<path d="{P(xf(pts, *OFF))}" fill="{col}"/>')
        out.append(stroke([(x, y0 + 4), (x, y1 + 2)], 4, taper=(0.05, 0.05)))
        out.append(stroke(sc, 8, taper=(0.1, 0.1), wmin=0.5))
        x += sw; k += 1
    out.append(clipped([(0, y0), (1080, y0), (1080, y0 + 30), (0, y0 + 30)], f'<rect x="0" y="{y0}" width="1080" height="34" fill="url(#htCs)" opacity="0.6"/>'))
    out.append(f'<rect x="-10" y="{y0 - 14}" width="1100" height="16" fill="{ROSE}"/>')
    out.append(stroke([(-10, y0 - 15), (1090, y0 - 15)], 7, taper=(0, 0)))
    out.append(stroke([(-10, y0 + 2), (1090, y0 + 2)], 9, taper=(0, 0)))
    return ''.join(out)


GLASS_BOX = (600, 382, 1100, 950)


def window2():
    x0, y0, x1, y1 = GLASS_BOX
    glass = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    out = [f'<path d="{P(glass)}" fill="{GLASS}"/>',
           f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#htCs)" opacity="0.45"/>']
    for a, b in ((640, 70), (742, 26)):
        st = [(a, y1), (a + b, y1), (a + b + 220, y0), (a + 220, y0)]
        out.append(clipped(glass, f'<path d="{P(st)}" fill="#EEF2EC"/>'))
    out.append(clipped(glass, f'<rect x="{x0}" y="{y1 - 70}" width="{x1 - x0}" height="70" fill="#C9D6D4"/>'
                              f'<rect x="{x0}" y="{y1 - 70}" width="{x1 - x0}" height="70" fill="url(#htKs)" opacity="0.2"/>'))
    return ''.join(out), glass


def window_frame():
    x0, y0, x1, y1 = GLASS_BOX
    glass = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    out = [inked(glass, None, (8, 12), 61)]
    sill = [(x0 - 16, y1 - 2), (x1, y1 - 2), (x1, y1 + 18), (x0 - 16, y1 + 18)]
    out.append(inked(sill, CREAM, (6, 8), 62))
    return ''.join(out)


def floor2(y0=950):
    seam = '#DCD2BC'
    out = [f'<rect x="0" y="{y0}" width="1080" height="{1920 - y0 + 2}" fill="{FLOOR}"/>',
           stroke([(-10, y0), (1090, y0 + 1)], 8, taper=(0, 0))]
    vx, vy = 540, 360
    for k in range(-9, 10):
        xb = 540 + k * 170
        t0 = (y0 - vy) / (1920 - vy)
        xa = vx + (xb - vx) * t0
        out.append(stroke([(xa, y0), (xb, 1920)], 2.5, color=seam, taper=(0, 0)))
    for y in (978, 1022, 1086, 1176, 1300, 1470):
        out.append(stroke([(-10, y), (1090, y)], 2.5, color=seam, taper=(0, 0)))
    out.append(f'<rect x="0" y="1575" width="1080" height="350" fill="#EDE6D6"/>')
    out.append(stroke([(-10, 1575), (1090, 1575)], 3, color=seam, taper=(0, 0)))
    out.append(ht_fade(0, 1600, 1080, 1920, CYAN, pitch=10, rmax=4.0, rmin=0.2, power=1.2))
    return ''.join(out)


def back_table(cx, ty, s=0.8):
    out = []
    out.append(stroke([(cx, ty + 6), (cx, ty + 120 * s)], 9 * s, taper=(0, 0)))
    out.append(stroke([(cx - 34 * s, ty + 124 * s), (cx + 34 * s, ty + 124 * s)], 8 * s, taper=(0.2, 0.2)))
    top = ellipse_pts(cx, ty, 70 * s, 15 * s, 60)
    out.append(inked(top, CLOTH, (5, 7), 81, inner=crescent(top, 'htCs', 0, -6, 0.6)))
    return ''.join(out)


def shrub_at(dx, dy, s=1.0):
    return f'<g transform="translate({dx} {dy}) scale({s})">{shrub()}</g>'



# ======================================================================== BIG-EYE ROUND HEAD RIG
EYEW = '#FDF8EE'                       # warm off-white eye whites (never #FFFFFF)
BIX_HAIR = '#2E2420'; BIX_GREY = '#D3CCC0'; BIX_COMB = '#62514A'; BIX_SHEEN = '#4A3B35'
VEST = '#36323B'; SHIRT = '#FBF6EA'; NOSE_RED = '#D65A4A'; BLUSH = '#EE9C88'
GUS_SKIN = '#EAC6A2'; GUS_GREY = '#D9D3C8'; KNIT = '#E2B93C'


def poly_centroid(poly):
    A = cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        A += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    if abs(A) < 1e-9:
        return centroid(poly)
    return (cx / (3 * A), cy / (3 * A))


def ray_hit(c, d, poly):
    """distance from c along unit d to the first polygon edge it crosses."""
    best = None
    n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-12:
            continue
        t = ((a[0] - c[0]) * ey - (a[1] - c[1]) * ex) / den
        u = ((a[0] - c[0]) * d[1] - (a[1] - c[1]) * d[0]) / den
        if t > 1e-9 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return best or 0.0


def interp_tab(tab, a):
    a = abs(a)
    if a <= tab[0][0]:
        return tab[0][1]
    for (a0, y0), (a1, y1) in zip(tab, tab[1:]):
        if a <= a1:
            return y0 + (y1 - y0) * (a - a0) / (a1 - a0)
    return tab[-1][1]


_SHAPES = {}


def eye_shape(kind, W, H):
    """eye-white shape in local px: +x = OUTWARD (away from the nose), y down, origin = bbox centre."""
    key = (kind, round(W, 2), round(H, 2))
    if key in _SHAPES:
        return _SHAPES[key]
    core = None
    if kind == 'teardrop':          # Bix: round bulb, point resting down-inward on the nose
        raw = hull(ellipse_pts(0, 0, 1, 1, 120) + ellipse_pts(-0.60, 1.52, 0.17, 0.17, 24))
        core = (0.0, 0.0)
    elif kind == 'droopy':          # Gus: top slopes down outward, outer corner hangs lowest
        ctrl = [(-1.0, -0.28), (-0.66, -0.96), (0.02, -0.98), (0.66, -0.55), (1.0, 0.30), (0.80, 0.90),
                (0.10, 1.0), (-0.62, 0.76), (-1.0, 0.22)]
        raw = spline(ctrl, True, 12)
    else:                           # cameo: generic oval (always 70 % lidded)
        raw = ellipse_pts(0, 0, 1, 1.18, 80)
        core = (0.0, 0.0)
    xs = [p[0] for p in raw]; ys = [p[1] for p in raw]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    N = lambda p: ((p[0] - (x0 + x1) / 2) / (x1 - x0) * W, (p[1] - (y0 + y1) / 2) / (y1 - y0) * H)
    loc = resample([N(p) for p in raw], 1.4)
    c = N(core) if core else poly_centroid(loc)
    _SHAPES[key] = (loc, c)
    return loc, c


FD = dict(tilt=0, lid=None, lid_tilt=(0, 0), lid_bow=(0.0, 0.0), low=(0.0, 0.0), low_tilt=(0, 0), low_bow=(0.0, 0.0),
          eye_scale=(1.0, 1.0), gaze=(0.0, 0.0), gaze_lr=None, look=None, gaze_k=1.0, pupil=None,
          brow_raise=(0.0, 0.0), brow_tilt=(0.0, 0.0), brow_arch=None, brow_dx=(0.0, 0.0),
          nose_tilt=0, flush=False, tip_flush=False, mouth='none', mouth_dx=0.0, stache=0.0, stache_dy=0.0,
          strand=0.0, marks=(), closed=(False, False), sweat_k=1.0)


class BigFace:
    """True-circle skull of diameter D; every size is a fraction of D.
    BIG eyes with a fixed white shape per character (Bix teardrop, Gus droopy).  Expression comes only from
    the upper-lid mask + its heavy ink line, an optional lower lid, solid pupils that clip against the rim,
    the brows and the mouth (hidden under the nose / mustache until a take).  Eyes rest on the nose top
    (0.03 D overlap).  In 3/4 the cluster shifts toward the facing side and the far eye compresses."""

    def __init__(s, cx, cy, D, turn, C, seed=1):
        s.cx, s.cy, s.D, s.R = cx, cy, D, D / 2.0
        s.turn, s.C, s.seed = turn, C, seed
        s.skin = C['skin']
        s.f = 1 if turn >= 0 else -1
        s.top = cy - s.R
        s.fx = cx + max(-0.15, min(0.15, turn * C.get('kx_eye', 0.28))) * D
        s.ncx = cx + turn * C.get('kx_nose', 0.32) * D
        s.nw = C['nose']['w'] * D * (1 + 0.06 * abs(turn))
        s.nh = C['nose']['h'] * D
        s.lay = {sd: s.eye_layout(sd) for sd in (-1, 1)}
        s.ny = s.solve_nose_y()
        s.head = s.silhouette()

    # ------------------------------------------------------------------ layout
    def eye_layout(s, side):
        C, D = s.C, s.D
        W, H = C['eye_w'] * D, C['eye_h'] * D
        far = abs(s.turn) > 0.05 and side == s.f
        wk = 1 - 0.24 * min(1.0, abs(s.turn) / 0.32) if far else 1.0
        gap = C['eye_gap'] * D
        loc, core = eye_shape(C['eye'], W, H)
        ex = s.fx + side * (gap / 2 + wk * W / 2)
        ey = s.top + C['eye_cy'] * D
        return dict(ex=ex, ey=ey, wk=wk, W=W, H=H, far=far, side=side, loc=loc, core=core)

    def L2W(s, g, q, sc=1.0):
        return (g['ex'] + g['side'] * g['wk'] * sc * q[0], g['ey'] + sc * q[1])

    def nose_top_at(s, x):
        u = (x - s.ncx) / (s.nw / 2)
        if abs(u) >= 1:
            return None
        return s.ny - s.nh / 2 * math.sqrt(1 - u * u)

    def solve_nose_y(s):
        best = None
        for sd in (-1, 1):
            g = s.lay[sd]
            pts = [s.L2W(g, q) for q in g['loc']]
            bx, by = max(pts, key=lambda q: q[1])
            u = (bx - s.ncx) / (s.nw / 2)
            k = math.sqrt(max(0.3 ** 2, 1 - u * u)) if abs(u) < 1 else 0.3
            ny = by - s.C.get('nose_over', 0.03) * s.D + s.nh / 2 * k
            best = ny if best is None else min(best, ny)
        return best

    def silhouette(s):
        pts = []
        jw = s.C.get('jowls', 0.0)
        for i in range(240):
            th = 2 * math.pi * i / 240
            r = s.R
            if jw:
                for c in (36, 144):
                    d = math.atan2(math.sin(th - math.radians(c)), math.cos(th - math.radians(c)))
                    r += s.D * jw * math.exp(-(d / math.radians(16)) ** 2)
            pts.append((s.cx + r * math.cos(th), s.cy + r * math.sin(th)))
        return pts

    # ------------------------------------------------------------------ eyes
    def curve_in(s, loc, fy, W, T, ext=0.0):
        xs = [-0.62 * W + 1.24 * W * k / 240 for k in range(241)]
        ins = [k for k, x in enumerate(xs) if inside((x, fy(x)), loc)]
        if len(ins) < 2:
            return None
        a, b = ins[0], ins[-1]
        pts = [(xs[k], fy(xs[k])) for k in range(a, b + 1)]
        if ext:
            pts = [(xs[a] - ext, fy(xs[a] - ext))] + pts + [(xs[b] + ext, fy(xs[b] + ext))]
        return [T(q) for q in pts]

    def eye_geom(s, side, e):
        i = 0 if side < 0 else 1
        g = dict(s.lay[side]); C = s.C; D = s.D
        W, H = g['W'], g['H']; loc = g['loc']
        sc = e['eye_scale'][i]; g['sc'] = sc
        cov = (e['lid'] if e['lid'] is not None else (C['lid'], C['lid']))[i]
        closed = e['closed'][i] or cov >= 0.98
        T = lambda q: s.L2W(g, q, sc)
        tl = math.tan(math.radians(e['lid_tilt'][i])); bw = e['lid_bow'][i]
        lidy = lambda x: -H / 2 + cov * H + tl * x + bw * H * (1 - min(1.0, (2 * x / W) ** 2))
        lowc = e['low'][i]; tlo = math.tan(math.radians(e['low_tilt'][i])); bwl = e['low_bow'][i]
        lowy = lambda x: H / 2 - lowc * H + tlo * x - bwl * H * (1 - min(1.0, (2 * x / W) ** 2))
        vis = loc
        ext = 0.016 * D / (g['wk'] * sc)
        if cov > 0 and not closed:
            vis = clip_half(vis, lambda q: lidy(q[0]) - q[1])
            g['lidpoly'] = [T(q) for q in clip_half(loc, lambda q: q[1] - lidy(q[0]))]
            g['lidline'] = s.curve_in(loc, lidy, W, T, ext)
        if lowc > 0 and not closed:
            vis = clip_half(vis, lambda q: q[1] - lowy(q[0]))
            g['lowpoly'] = [T(q) for q in clip_half(loc, lambda q: lowy(q[0]) - q[1])]
            g['lowline'] = s.curve_in(loc, lowy, W, T, ext * 0.4)
        if closed:
            cl = lambda x: -H / 2 + 0.56 * H + 0.10 * H * (1 - min(1.0, (2 * x / W) ** 2))
            cr = lambda x: -H / 2 + 0.30 * H + 0.06 * H * (1 - min(1.0, (2 * x / W) ** 2))
            g['closedline'] = s.curve_in(loc, cl, W, T, ext)
            g['crease'] = s.curve_in(loc, cr, W * 0.8, T, 0)
        g['poly'] = [T(q) for q in loc]
        g['closed'] = closed
        g['top'] = min(g['poly'], key=lambda q: q[1])
        g['core_w'] = T(g['core'])
        g['T'] = T
        visw = [T(q) for q in vis] if len(vis) >= 3 else []
        pr = (e['pupil'] or C['pupil']) * D / 2 * (0.95 if g['far'] else 1.0)
        g['pr'] = pr
        if not closed and len(visw) >= 3:
            def nose_f(q):
                t = s.nose_top_at(q[0])
                return -1.0 if t is None else q[1] - (t + 0.015 * D)
            visn = clip_half(visw, nose_f)
            if len(visn) < 3 or abs(area(visn)) < (pr * pr):
                visn = visw
            c = poly_centroid(visn)
            if e['look'] is not None:
                tx, ty = rot(e['look'], -e['tilt'], (s.cx, s.cy))
                ec = poly_centroid(g['poly'])
                v = (tx - ec[0], ty - ec[1]); m = math.hypot(*v) or 1
                d = (v[0] / m, v[1] / m); mag = e['gaze_k']
            else:
                gx, gy = e['gaze_lr'][i] if e['gaze_lr'] else e['gaze']
                m = math.hypot(gx, gy)
                d = (gx / m, gy / m) if m > 1e-6 else (0.0, 0.0); mag = min(1.0, m)
            if mag > 0:
                dist = ray_hit(c, d, visn)
                k = max(0.0, dist - 0.58 * pr) * mag
                c = (c[0] + d[0] * k, c[1] + d[1] * k)
            g['pupil'] = c
        return g

    def draw_eye(s, g, e):
        D = s.D; out = []
        poly = g['poly']
        c = uid('c')
        out.append(f'<clipPath id="{c}"><path d="{P(poly)}"/></clipPath>')
        lidc = shade_hex(s.skin, 0.08)
        if g['closed']:
            inner = f'<path d="{P(poly)}" fill="{lidc}"/>'
        else:
            inner = f'<path d="{P(xf(poly, 1.5, 1.5))}" fill="{EYEW}"/>'
            if 'pupil' in g:
                px, py = g['pupil']
                inner += f'<circle cx="{f1(px)}" cy="{f1(py)}" r="{f1(g["pr"])}" fill="{INK}"/>'
            if len(g.get('lidpoly', [])) > 2:
                inner += f'<path d="{P(g["lidpoly"])}" fill="{lidc}"/>'
            if len(g.get('lowpoly', [])) > 2:
                inner += f'<path d="{P(g["lowpoly"])}" fill="{s.skin}"/>'
        out.append(f'<g clip-path="url(#{c})">{inner}</g>')
        rim = s.C.get('rim', 0.021) * D * (0.8 if g['closed'] else 1.0)
        out.append(f'<path d="{P(poly)}" fill="none" stroke="{INK}" stroke-width="{f1(rim)}" stroke-linejoin="round"/>')
        lw = s.C.get('lid_w', 0.032) * D
        if g['closed']:
            if g.get('closedline'):
                L = g['closedline']
                out.append(stroke(L, lw, taper=(0.08, 0.14), wmin=0.5))
                end = L[-1] if (L[-1][0] - L[0][0]) * g['side'] > 0 else L[0]
                out.append(stroke([end, (end[0] + g['side'] * 0.05 * D, end[1] + 0.035 * D)], 0.022 * D, taper=(0.0, 0.7)))
            if g.get('crease'):
                out.append(stroke(g['crease'], 0.016 * D, taper=(0.3, 0.3), wmin=0.3))
        if g.get('lowline'):
            out.append(stroke(g['lowline'], 0.019 * D, taper=(0.3, 0.3), wmin=0.3))
        if g.get('lidline'):
            out.append(stroke(g['lidline'], lw, taper=(0.07, 0.12), wmin=0.55))
        return ''.join(out)

    def ray_arc(s, g, a0, a1, gap, n=16, center=None):
        """points just outside the eye rim between local angles a0..a1 (0 = outward, 90 = down)."""
        cw = center or g['core_w']
        out = []
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            dl = (math.cos(a) * g['side'], math.sin(a))
            dist = ray_hit(cw, dl, g['poly'])
            out.append((cw[0] + dl[0] * (dist + gap), cw[1] + dl[1] * (dist + gap)))
        return out

    def draw_under(s, geoms, e):
        """adult marks under the eyes: Bix's crease + crow's feet, Gus's bags (drawn before the eyes)."""
        D = s.D; out = []
        for g in geoms:
            if g['closed']:
                continue
            if s.C.get('bags'):
                if g['far'] and abs(s.turn) > 0.3:
                    a0, a1 = 70, 140
                else:
                    a0, a1 = 20, 150
                inner_arc = s.ray_arc(g, a0, a1, 0.0, 24)
                outer_arc = s.ray_arc(g, a0, a1, 0.05 * D, 24)
                poly = inner_arc + outer_arc[::-1]
                out.append(f'<path d="{P(poly)}" fill="{shade_hex(s.skin, 0.12)}"/>')
                out.append(stroke(outer_arc, 0.02 * D, taper=(0.3, 0.3), wmin=0.3))
                sec = s.ray_arc(g, a0 + 25, a1 - 35, 0.088 * D, 14)
                out.append(stroke(sec, 0.015 * D, taper=(0.35, 0.35), wmin=0.2))
            if s.C.get('crease') and not (g['far'] and abs(s.turn) > 0.3):
                arc = s.ray_arc(g, 18, 78, 0.036 * D, 16)
                out.append(stroke(arc, 0.017 * D, taper=(0.3, 0.45), wmin=0.25))
                for a in (-14, 6):
                    p0 = s.ray_arc(g, a, a, 0.034 * D, 1)[0]
                    p1 = s.ray_arc(g, a + 6, a + 6, 0.082 * D, 1)[0]
                    out.append(stroke([p0, p1], 0.015 * D, taper=(0.1, 0.6), wmin=0.3))
        return ''.join(out)

    # ------------------------------------------------------------------ brows
    def draw_brows(s, e, geoms):
        C, D = s.C, s.D
        out = []
        for side, i in ((-1, 0), (1, 1)):
            g = geoms[i]
            L = C['brow_len'] * D * (0.80 if g['far'] else 1.0)
            cxb = g['ex'] + side * (C.get('brow_dx', 0.0) + e['brow_dx'][i]) * D * g['wk']
            topy = g['ey'] - g['sc'] * g['H'] / 2
            th = C['brow_th'] * D
            yb = topy - (C['brow_gap'] + e['brow_raise'][i]) * D - th * 0.5
            ang = -side * (e['brow_tilt'][i] + C.get('brow_tilt0', 0.0))
            arch = (e['brow_arch'] or (C['brow_arch'], C['brow_arch']))[i]
            a = (cxb - side * L / 2, yb); b = (cxb + side * L / 2, yb)
            cc = (cxb - side * L * 0.08, yb - arch * L * 2)
            kind = C['brow']
            if kind == 'comma':
                pts = xf(qbez(a, cc, b, 30), ang=ang, c=(cxb, yb))
                hr = th * 0.58
                halo = (stroke(pts, th + 0.03 * D, color=s.skin, taper=(0.0, 0.9), wmin=0.3)
                        + f'<circle cx="{f1(pts[0][0])}" cy="{f1(pts[0][1])}" r="{f1(hr + 0.015 * D)}" fill="{s.skin}"/>')
                out.append(halo + stroke(pts, th, taper=(0.0, 0.92), wmin=0.14)
                           + f'<circle cx="{f1(pts[0][0])}" cy="{f1(pts[0][1])}" r="{f1(hr)}" fill="{INK}"/>')
            elif kind == 'scallop':
                N = 44
                base = xf(qbez(a, cc, b, N), ang=ang, c=(cxb, yb))
                droop = C.get('brow_droop', 0.0) * th          # outer end hangs down toward the eye corner
                base = [(q[0], q[1] + droop * max(0.0, (j / N - 0.62) / 0.38) ** 2) for j, q in enumerate(base)]
                top_p, bot_p = [], []
                for j, q in enumerate(base):
                    t = j / N
                    p0 = base[max(j - 1, 0)]; p2 = base[min(j + 1, N)]
                    tx, ty = p2[0] - p0[0], p2[1] - p0[1]; l = math.hypot(tx, ty) or 1
                    nx, ny = ty / l, -tx / l
                    if ny > 0:
                        nx, ny = -nx, -ny
                    env = math.sin(math.pi * min(1.0, 0.13 + 0.87 * t)) ** 0.5
                    hump = 0.62 + 0.38 * (1 - abs(math.cos(t * math.pi * 5.0 + 0.3))) ** 1.4
                    up = th * 0.64 * env * hump; dn = th * 0.36 * env
                    top_p.append((q[0] + nx * up, q[1] + ny * up)); bot_p.append((q[0] - nx * dn, q[1] - ny * dn))
                poly = top_p + bot_p[::-1]
                inner = clipped(poly, f'<path d="{P(xf(bot_p + [(q[0], q[1] + th) for q in bot_p[::-1]], 0, -th * 0.25))}" fill="{shade_hex(C.get("brow_fill", GUS_GREY), 0.18)}"/>')
                out.append(inked(poly, C.get('brow_fill', GUS_GREY), (0.012 * D, 0.02 * D), s.seed + 70 + i, bias=0.7, inner=inner, off=(2, 2)))
                for j in (9, 19, 29):
                    q = base[j]
                    out.append(stroke([lerp(q, top_p[j], 0.1), lerp(q, top_p[j + 3], 0.75)], 0.012 * D, taper=(0.2, 0.6), wmin=0.3))
            else:
                pts = xf(qbez(a, cc, b, 24), ang=ang, c=(cxb, yb))
                out.append(stroke(pts, th, taper=(0.3, 0.45), wmin=0.3))
        return ''.join(out)

    # ------------------------------------------------------------------ nose / mouth / mustache
    def nose_geom(s, e):
        n = s.C['nose']
        cx, cy = s.ncx, s.ny
        tilt = e['nose_tilt']; ang = -s.f * tilt
        if n['kind'] == 'button':
            loc = ellipse_pts(cx, cy, s.nw / 2, s.nh / 2, 100)
        else:
            if 'harm' in n:                       # authored for a face turned left; mirrored when it faces right
                loc = blob_pts(cx, cy, s.nw, s.nh, n['harm'], 160)
                if s.f > 0:
                    loc = [(2 * cx - x, y) for x, y in loc][::-1]
            else:
                harm = [(3, 0.06, 0.5 if s.f > 0 else 2.6), (2, 0.035, 1.4), (5, 0.02, 0.2)]
                loc = blob_pts(cx, cy, s.nw, s.nh, harm, 160)
        pts = xf(loc, ang=ang, c=(cx, cy))
        return dict(pts=pts, c=(cx, cy), ang=ang, w=s.nw, h=s.nh, tilt=tilt)

    def draw_nose(s, e):
        ng = s.nose_geom(e)
        pts = ng['pts']; cx, cy = ng['c']; w, h = ng['w'], ng['h']; ang = ng['ang']
        base = s.C['nose']['fill']
        fill = FLUSH if e['flush'] else base
        inner = crescent(pts, 'htR' if e['flush'] else s.C['nose'].get('shade', 'htC'), -w * 0.16, -h * 0.18, 0.55)
        if e['tip_flush']:
            blot = xf(ellipse_pts(cx + s.f * w * 0.18, cy + h * 0.10, w * 0.36, h * 0.34, 50), ang=ang, c=(cx, cy))
            inner += clipped(pts, f'<path d="{P(blot)}" fill="{FLUSH}"/>', OFF)
        for px_, py_, pr_ in s.C['nose'].get('pores', ()):
            q = rot((cx + s.f * px_ * w, cy + py_ * h), ang, (cx, cy))
            inner += f'<ellipse cx="{f1(q[0])}" cy="{f1(q[1])}" rx="{f1(pr_ * s.D)}" ry="{f1(pr_ * s.D * 0.8)}" fill="{shade_hex(base, 0.28)}"/>'
        hl = xf(ellipse_pts(cx - w * 0.17 + s.turn * w * 0.08, cy - h * 0.22, w * 0.11, h * 0.08, 30), ang=ang - 20, c=(cx, cy))
        inner += f'<path d="{P(hl)}" fill="{EYEW}" fill-opacity="0.8"/>'
        lw = s.C.get('line', (0.021, 0.035))
        out = [inked(pts, fill, (lw[0] * s.D * 0.85, lw[1] * s.D * 0.85), s.seed + 7, inner=inner)]
        if ng['tilt'] > 4:
            nos = [(-w * 0.17, h * 0.26), (w * 0.17, h * 0.26)] if abs(s.turn) < 0.3 else [(s.f * w * 0.12, h * 0.27), (-s.f * w * 0.18, h * 0.29)]
            for k, (dx, dy) in enumerate(nos):
                q = rot((cx + dx, cy + dy), ang, (cx, cy))
                rr = w * (0.085 if k == 0 else 0.065)
                out.append(f'<ellipse cx="{f1(q[0])}" cy="{f1(q[1])}" rx="{f1(rr)}" ry="{f1(rr * 0.62)}" transform="rotate({f1(ang)} {f1(q[0])} {f1(q[1])})" fill="{MOUTH}"/>')
        return ''.join(out)

    def mouth_anchor(s, e):
        x = s.ncx - s.turn * 0.05 * s.D + e['mouth_dx'] * s.D
        nb = s.ny + s.nh / 2
        return x, nb

    def draw_mouth(s, e):
        m = e['mouth']
        if m == 'none':
            return ''
        D = s.D; x, nb = s.mouth_anchor(e)
        k = s.C.get('mouth_k', 1.0)
        out = []
        bs = -s.f if abs(s.turn) > 0.1 else 1          # back side of the face
        if m == 'o':
            rx, ry = 0.15 * D * k, 0.105 * D * k
            cy = nb + s.C.get('o_dy', 0.075) * D
            pts = ellipse_pts(x, cy, rx, ry, 50)
            inner = f'<path d="{P(ellipse_pts(x + 0.02 * D, cy + ry * 0.55, rx * 0.62, ry * 0.42, 30))}" fill="{ROSE}"/>'
            out.append(inked(pts, MOUTH, (0.016 * D, 0.024 * D), 3, off=(0, 0), inner=clipped(pts, inner)))
        elif m == 'grit':
            w, hh = 0.34 * D, 0.12 * D; t0 = nb + 0.0 * D
            ctrl = [(x - w / 2, t0 + 0.035 * D), (x, t0 - 0.004 * D), (x + w / 2, t0 + 0.035 * D),
                    (x + w / 2 - 0.02 * D, t0 + hh + 0.01 * D), (x, t0 + hh - 0.012 * D), (x - w / 2 + 0.02 * D, t0 + hh + 0.01 * D)]
            pts = spline(ctrl, True, 8)
            lines = ''
            mid = spline([(x - w / 2, t0 + hh * 0.62), (x, t0 + hh * 0.48), (x + w / 2, t0 + hh * 0.62)], False, 10)
            lines += stroke(mid, 0.014 * D, taper=(0.05, 0.05))
            for j in range(1, 5):
                xx = x - w / 2 + w * j / 5
                lines += stroke([(xx, t0), (xx + 0.004 * D, t0 + hh + 0.02 * D)], 0.013 * D, taper=(0.05, 0.05))
            out.append(inked(pts, EYEW, (0.016 * D, 0.024 * D), 4, off=(0, 0), inner=clipped(pts, lines)))
        elif m == 'gape':
            w, dd = 0.38 * D, 0.17 * D; t0 = nb - 0.01 * D
            top = [(x - w / 2 + w * j / 30, t0 + 0.012 * D * math.sin(j / 30 * math.pi * 5)) for j in range(31)]
            bot = [(x + w / 2 * math.cos(math.pi * j / 30), t0 + dd * math.sin(math.pi * j / 30) + 0.01 * D) for j in range(31)]
            pts = top + bot[1:-1]
            teeth = [(x - w * 0.4, t0 - 0.02 * D), (x + w * 0.4, t0 - 0.02 * D), (x + w * 0.38, t0 + 0.045 * D), (x - w * 0.38, t0 + 0.045 * D)]
            tongue = ellipse_pts(x + 0.03 * D, t0 + dd * 0.88, w * 0.28, dd * 0.28, 40)
            inner = f'<path d="{P(tongue)}" fill="{ROSE}"/><path d="{P(teeth)}" fill="{EYEW}"/>'
            out.append(inked(pts, MOUTH, (0.016 * D, 0.024 * D), 5, off=(0, 0), inner=clipped(pts, inner)))
        elif m == 'curl':
            p0 = (x + bs * 0.05 * D, nb + 0.045 * D)
            p1 = (x + bs * 0.15 * D, nb + 0.09 * D)
            p2 = (x + bs * 0.215 * D, nb + 0.02 * D)
            out.append(stroke(qbez(p0, p1, p2), 0.034 * D, taper=(0.1, 0.4)))
            out.append(stroke(qbez(p2, (p2[0] + bs * 0.03 * D, p2[1] - 0.005 * D), (p2[0] + bs * 0.022 * D, p2[1] - 0.04 * D), 8), 0.024 * D, taper=(0.0, 0.9)))
        elif m == 'flat':
            y = nb + 0.07 * D
            a = (x - 0.02 * D, y + 0.004 * D); b = (x + 0.14 * D, y - 0.004 * D)
            out.append(stroke([a, b], 0.032 * D, taper=(0.15, 0.15)))
            out.append(stroke([b, (b[0] + 0.03 * D, b[1] + 0.022 * D)], 0.022 * D, taper=(0.0, 0.8)))
        elif m == 'wobble':
            y = nb + 0.06 * D
            pts = [(x - 0.15 * D + 0.30 * D * t, y + 0.02 * D * math.sin(t * math.pi * 3) + 0.03 * D * (2 * t - 1) ** 2) for t in (j / 40 for j in range(41))]
            out.append(stroke(pts, 0.032 * D, taper=(0.15, 0.15)))
        return ''.join(out)

    def draw_stache(s, e):
        if not s.C.get('stache'):
            return ''
        D = s.D; x, nb = s.mouth_anchor(e)
        x -= e['mouth_dx'] * D * 0.5
        y0 = nb + 0.012 * D + e['stache_dy'] * D
        out = []
        for side in (-1, 1):
            front = abs(s.turn) > 0.1 and side == s.f
            Ls = (0.125 if front else 0.175) * D
            lift = e['stache'] * D
            p0 = (x + side * 0.014 * D, y0 - 0.004 * D)
            p1 = (x + side * Ls * 0.55, y0 + 0.024 * D + lift * 0.35)
            p2 = (x + side * Ls, y0 - 0.008 * D + lift)
            pts = qbez(p0, p1, p2, 24)
            tip = (p2[0] + side * 0.022 * D, p2[1] - 0.026 * D - lift * 0.3)
            out.append(stroke(pts + [tip], 0.038 * D, taper=(0.12, 0.7), wmin=0.2))
        return ''.join(out)

    # ------------------------------------------------------------------ ears / cheeks / folds
    def ear_sides(s):
        return (-1, 1) if abs(s.turn) < 0.3 else (-s.f,)

    def ear_svg(s, side):
        rx, ry, pr = (k * s.D for k in s.C['ear'])
        ex = s.cx + side * (s.R + pr - rx)
        ey = s.cy + (s.C.get('ear_y', 0.52) - 0.5) * s.D
        pts = ellipse_pts(ex, ey, rx, ry, 50)
        out = inked(pts, s.skin, (0.021 * s.D * 0.8, 0.035 * s.D * 0.8), s.seed + 40 + side,
                    inner=crescent(pts, 'htRs', -rx * 0.3 * side, -ry * 0.2, 0.6))
        a = (ex + side * rx * 0.30, ey - ry * 0.48)
        m = (ex + side * rx * 1.05, ey - ry * 0.05)
        b = (ex + side * rx * 0.30, ey + ry * 0.52)
        out += stroke(qbez(a, m, b), 0.022 * s.D, taper=(0.25, 0.3))
        return out

    def cheeks_svg(s):
        out = []
        D = s.D
        for side in (-1, 1):
            far = abs(s.turn) > 0.3 and side == s.f
            if far:
                continue
            x = s.ncx + side * (s.nw * 0.5 + 0.03 * D)
            y = s.ny + 0.05 * D
            pts = ellipse_pts(x, y, 0.105 * D, 0.072 * D, 40)
            out.append(f'<path d="{P(pts)}" fill="{BLUSH}"/>')
        return clipped(s.head, ''.join(out))

    def draw_folds(s, e):
        D = s.D; out = []
        kind = s.C.get('fold')
        if kind == 'jowl1':                       # Bix: one sag line under the cheek, back side
            bs = -s.f if abs(s.turn) > 0.1 else 1
            nx = s.ncx + bs * (s.nw / 2)
            p0 = (nx + bs * 0.18 * D, s.ny + 0.13 * D)
            p1 = (nx + bs * 0.22 * D, s.ny + 0.21 * D)
            p2 = (nx + bs * 0.16 * D, s.ny + 0.29 * D)
            out.append(stroke(qbez(p0, p1, p2, 20), 0.022 * D, taper=(0.3, 0.55), wmin=0.25))
        elif kind == 'jowl2':                     # Gus: folds both sides of the potato nose
            for side in (-1, 1):
                if abs(s.turn) > 0.3 and side == s.f:
                    continue
                nx = s.ncx + side * (s.nw / 2)
                p0 = (nx - side * 0.01 * D, s.ny + 0.04 * D)
                p1 = (nx + side * 0.07 * D, s.ny + 0.14 * D)
                p2 = (nx + side * 0.04 * D, s.ny + 0.22 * D)
                out.append(stroke(qbez(p0, p1, p2, 20), 0.022 * D, taper=(0.3, 0.5), wmin=0.25))
        return ''.join(out)

    # ------------------------------------------------------------------ hair
    def slick_parts(s, e):
        """slicked-back hair modelled on a sphere: hairline table h(alpha); computed for a face turned to the
        LEFT and mirrored when it faces right.  Returns world points (before the head tilt)."""
        C, R, D = s.C, s.R, s.D
        tab = C['hairline']
        h = lambda a: interp_tab(tab, a)
        phid = -abs(s.turn) * C.get('yaw', 42)
        phi = math.radians(phid)
        mir = -1 if s.turn > 0 else 1
        W = lambda x, y: (s.cx + mir * R * x, s.cy + R * y)
        line = []
        for k in range(121):
            a = -90 - phid + 180 * k / 120
            y = h(a); r = math.sqrt(max(0.0, 1 - y * y))
            line.append((r * math.sin(math.radians(a + phid)), y))
        xa, ya = line[0]; xb, yb = line[-1]
        tha = math.atan2(ya, xa); thb = math.atan2(yb, xb)
        if tha > thb:
            tha -= 2 * math.pi
        vol = C.get('hair_vol', 0.035) * 2
        flicks = []
        if abs(s.turn) >= 0.25:
            for dth, Lf in ((-0.10, 0.10), (-0.36, 0.08), (-0.60, 0.055)):
                flicks.append((thb + dth, Lf * 2))
        M = 220; arc = []
        for k in range(M + 1):
            th = thb + (tha - thb) * k / M
            u = min(k, M - k) / M
            rr = 1 + vol * min(1.0, u / 0.16)
            for th0, Lf in flicks:
                w = 0.30
                dd = th0 - th                      # th decreases along the arc away from the nape
                if 0 <= dd <= w:
                    rr += Lf * (1 - dd / w) ** 1.6
            arc.append((rr * math.cos(th), rr * math.sin(th)))
        poly = [W(*q) for q in line + arc]
        # grey temples
        temples = []
        tac, tyc, taw, tyw = C.get('temple', (76, -0.16, 17, 0.30))
        for ac in (tac, -tac):
            pts = []; vis = False
            for k in range(60):
                t = 2 * math.pi * k / 60
                a = ac + taw * math.cos(t); y = tyc + tyw * math.sin(t)
                ae = a + phid
                if -90 < ae < 90:
                    vis = True
                ae = max(-90, min(90, ae))
                r = math.sqrt(max(0.0, 1 - y * y))
                pts.append(W(r * math.sin(math.radians(ae)) * 1.04, y))
            if vis:
                temples.append(pts)
        # comb grooves running front-to-back over the crown
        combs = []
        cp, sp = math.cos(phi), math.sin(phi)
        for u in C.get('combs', (-0.55, -0.25, 0.05, 0.35, 0.62)):
            seg = []; segs = []
            rr = math.sqrt(1 - u * u)
            for k in range(60):
                th = math.radians(8 + 165 * k / 59)
                x0 = u; y0 = -rr * math.sin(th); z0 = rr * math.cos(th)
                X = x0 * cp + z0 * sp; Z = -x0 * sp + z0 * cp
                a = math.degrees(math.atan2(x0, z0))
                if Z > 0.05 and y0 < h(a) - 0.07:
                    seg.append(W(X * 1.01, y0 * 1.01))
                elif len(seg) > 3:
                    segs.append(seg); seg = []
                else:
                    seg = []
            if len(seg) > 3:
                segs.append(seg)
            combs += segs
        return dict(poly=poly, temples=temples, combs=combs)

    def draw_slick(s, e):
        D = s.D
        hp = s.slick_parts(e)
        poly = hp['poly']
        out = [f'<path d="{P(xf(poly, 2, 2))}" fill="{BIX_HAIR}"/>']
        inner = ''
        for tp in hp['temples']:
            inner += f'<path d="{P(tp)}" fill="{BIX_GREY}"/>'
            inner += f'<path d="{P(tp)}" fill="url(#htKs)" opacity="0.35"/>'
        for k, cb in enumerate(hp['combs']):
            col = BIX_COMB
            inner += stroke(cb, 0.016 * D, color=col, taper=(0.25, 0.35), wmin=0.2)
        out.append(clipped(poly, inner))
        out.append(f'<path d="{ring_d(poly, 0.018 * D, 0.03 * D, 0.8, s.seed + 90)}" fill="{INK}" fill-rule="evenodd"/>')
        s._hair_poly = poly
        return ''.join(out)

    def draw_strand(s, e):
        if e['strand'] <= 0:
            return ''
        D = s.D
        mir = -1 if s.turn > 0 else 1
        x0 = s.cx + mir * 0.10 * D; y0 = s.top_y_at(x0) + 0.02 * D
        L = 0.24 * D * e['strand']
        pts = []
        for j in range(31):
            t = j / 30
            pts.append((x0 + mir * 0.05 * D * math.sin(t * math.pi * 1.6) - mir * 0.06 * D * t, y0 - L * t))
        return stroke(pts, 0.04 * D, color=INK, taper=(0.05, 0.9), wmin=0.15)

    def top_y_at(s, x):
        dx = x - s.cx
        if abs(dx) >= s.R:
            return s.cy
        return s.cy - math.sqrt(s.R ** 2 - dx * dx)

    def draw_fringe(s, e):
        """grey horseshoe fringe round the back of a bald dome, tufts poking past the rim."""
        out = []
        D = s.D
        sides = [-s.f] if abs(s.turn) >= 0.3 else [-1, 1]
        poke = s.C.get('fringe_poke', 0.07)
        for side in sides:
            a0 = math.asin((0.24 - 0.5) * 2); a1 = math.asin((0.76 - 0.5) * 2)
            N = 52
            outer, inner = [], []
            for j in range(N + 1):
                t = j / N
                a = a0 + (a1 - a0) * t
                bump = abs(math.sin(t * math.pi * 6.5))
                env = math.sin(math.pi * t) ** 0.4
                ro = s.R + D * poke * (0.35 + 0.65 * bump) * env
                ri = s.R - D * 0.10 * math.sin(math.pi * t) ** 0.7
                x = math.cos(a) * side; y = math.sin(a)
                outer.append((s.cx + x * ro, s.cy + y * ro)); inner.append((s.cx + x * ri, s.cy + y * ri))
            poly = outer + inner[::-1]
            out.append(f'<path d="{P(xf(poly, *OFF))}" fill="{GUS_GREY}"/>')
            out.append(clipped(poly, f'<rect x="{f1(s.cx - s.D)}" y="{f1(s.cy - s.D)}" width="{f1(2 * s.D)}" height="{f1(2 * s.D)}" fill="url(#htKs)" opacity="0.45"/>', OFF))
            out.append(f'<path d="{ring_d(poly, 0.012 * D, 0.02 * D, 0.7, s.seed + 95 + side)}" fill="{INK}" fill-rule="evenodd"/>')
            for j in range(2, N - 2, 5):
                q0 = inner[N - j]; q1 = outer[j]
                out.append(stroke([lerp(q1, q0, 0.15), lerp(q1, q0, 0.7)], 0.012 * D, taper=(0.3, 0.5), wmin=0.2))
        return ''.join(out)

    def draw_comb(s, e):
        """grey comb-over strands lifted off the crown (cameo)."""
        out = []
        f = s.f
        for k, (h0, h1, lift) in enumerate([(0.30, 0.14, 0.05), (0.24, 0.10, 0.075), (0.20, 0.13, 0.06), (0.34, 0.18, 0.035)]):
            xb = s.cx - f * s.R * math.sqrt(max(0, 1 - (1 - 2 * h0) ** 2))
            yb = s.cy - s.R + h0 * s.D
            xe = s.cx + f * s.R * 0.62 * math.sqrt(max(0, 1 - (1 - 2 * h1) ** 2))
            ye = s.cy - s.R + h1 * s.D
            mid = ((xb + xe) / 2 - f * 0.05 * s.D, s.cy - s.R - lift * s.D * 1.6)
            pts = qbez((xb, yb), mid, (xe, ye), 30)
            out.append(stroke(pts, 0.032 * s.D, taper=(0.1, 0.6), wmin=0.2))
            out.append(stroke(pts, 0.016 * s.D, color=HAIR_GREY, taper=(0.15, 0.7), wmin=0.2))
        return ''.join(out)

    def draw_marks(s, e):
        out = []
        D = s.D
        for mk in e['marks']:
            if mk[0] == 'sweat':
                x, y, size, ang = s.cx + mk[1] * D, s.cy + mk[2] * D, mk[3] * D, mk[4]
                dp = drop_pts(x, y, size, ang)
                out.append(inked(dp, CYAN, (3, 4.5), 9, bias=0.5, off=(2, 2)))
                hl = rot((x - size * 0.15, y - size * 0.05), ang, (x, y))
                out.append(f'<circle cx="{f1(hl[0])}" cy="{f1(hl[1])}" r="{f1(size * 0.12)}" fill="{EYEW}"/>')
            elif mk[0] == 'emanata':
                cx, cy, R = s.cx, s.cy - 0.1 * D, mk[1] * D
                for a in (-150, -128, -52, -30):
                    ar = math.radians(a)
                    p0 = (cx + math.cos(ar) * R, cy + math.sin(ar) * R)
                    p1 = (cx + math.cos(ar) * (R + 0.14 * D), cy + math.sin(ar) * (R + 0.14 * D))
                    out.append(stroke([p0, p1], 0.035 * D, taper=(0.1, 0.6)))
            elif mk[0] == 'vein':
                x, y, r = s.cx + mk[1] * D, s.cy + mk[2] * D, mk[3] * D
                for a in (45, 135, 225, 315):
                    ar = math.radians(a)
                    c0 = (x + math.cos(ar) * r * 0.25, y + math.sin(ar) * r * 0.25)
                    c1 = (x + math.cos(ar) * r, y + math.sin(ar) * r)
                    m = (x + math.cos(ar + 0.6) * r * 0.75, y + math.sin(ar + 0.6) * r * 0.75)
                    out.append(stroke(qbez(c0, m, c1, 10), 0.03 * D, color=FLUSH, taper=(0.1, 0.1)))
        return ''.join(out)

    # ------------------------------------------------------------------ assemble
    def draw(s, E):
        e = dict(FD); e.update(E)
        D = s.D; C = s.C
        out = [f'<g transform="rotate({f1(e["tilt"])} {f1(s.cx)} {f1(s.cy)})">']
        ear_front = C.get('ear_front', False)
        if not ear_front:
            for side in s.ear_sides():
                out.append(s.ear_svg(side))
        inner = crescent(s.head, C.get('shade', 'htC'), -0.11 * D, -0.085 * D, C.get('shade_op', 0.45))
        if C.get('cheeks'):
            inner += s.cheeks_svg()
        out.append(inked(s.head, s.skin, (0.021 * D, 0.035 * D), s.seed, inner=inner))
        hair = C.get('hair')
        if hair == 'slick':
            out.append(s.draw_slick(e))
        elif hair == 'fringe':
            out.append(s.draw_fringe(e))
        elif hair == 'comb':
            out.append(s.draw_comb(e))
        if ear_front:
            for side in s.ear_sides():
                out.append(s.ear_svg(side))
        out.append(s.draw_folds(e))
        geoms = [s.eye_geom(-1, e), s.eye_geom(1, e)]
        out.append(s.draw_under(geoms, e))
        out.append(s.draw_mouth(e))
        for g in geoms:
            out.append(s.draw_eye(g, e))
        out.append(s.draw_nose(e))
        out.append(s.draw_stache(e))
        out.append(s.draw_brows(e, geoms))
        out.append(s.draw_strand(e))
        out.append(s.draw_marks(e))
        out.append('</g>')
        s.last_geoms = geoms
        return ''.join(out)

    def top_with_hair(s, E=None):
        e = dict(FD); e.update(E or {})
        ys = [s.cy - s.R]
        if s.C.get('hair') == 'slick':
            poly = s.slick_parts(e)['poly']
            ys += [rot(q, e['tilt'], (s.cx, s.cy))[1] for q in poly]
        return min(ys)

    # ------------------------------------------------------------------ measurements (fractions of D)
    def measure(s, E=None):
        e = dict(FD); e.update(E or {})
        g = [s.eye_geom(-1, e), s.eye_geom(1, e)]
        D = s.D
        res = {}
        for k, gg in zip(('L', 'R'), g):
            ys = [q[1] for q in gg['poly']]; xs = [q[0] for q in gg['poly']]
            res[k] = dict(h=(max(ys) - min(ys)) / D, w=(max(xs) - min(xs)) / D,
                          top=(min(ys) - s.top) / D, ctr=((max(ys) + min(ys)) / 2 - s.top) / D,
                          pupil=2 * gg['pr'] / D, pupil_frac=2 * gg['pr'] / (max(xs) - min(xs)))
        xl = [q[0] for q in g[0]['poly']]; xr = [q[0] for q in g[1]['poly']]
        res['gap'] = (min(xr) - max(xl)) / D
        res['span'] = (max(xr) - min(xl)) / D
        nt = s.nose_top_at(max(g[1]['poly'], key=lambda q: q[1])[0])
        res['nose_w'] = s.nw / D
        res['lid_w'] = s.C.get('lid_w', 0.032); res['rim'] = s.C.get('rim', 0.021)
        return res


# ======================================================================== CAST SPECS
BIX = dict(skin=SKIN_B, eye='teardrop', eye_w=0.27, eye_h=0.32, eye_gap=0.10, eye_cy=0.43, lid=0.25, pupil=0.11,
           rim=0.021, lid_w=0.036, kx_eye=0.28, kx_nose=0.32, nose_over=0.03,
           nose=dict(kind='button', w=0.27, h=0.20, fill=NOSE_B, shade='htR'),
           brow='comma', brow_th=0.062, brow_len=0.22, brow_gap=0.045, brow_arch=0.10, brow_dx=-0.01,
           ear=(0.09, 0.115, 0.07), ear_y=0.53, ear_front=True, hair='slick', stache=True, fold='jowl1', crease=True,
           hairline=[(0, -0.71), (12, -0.79), (28, -0.87), (46, -0.76), (54, -0.56), (60, 0.06), (72, 0.14), (82, -0.12),
                     (98, -0.14), (110, 0.0), (130, 0.32), (154, 0.55), (180, 0.64)],
           hair_vol=0.035, temple=(66, -0.16, 15, 0.34), shade='htC', shade_op=0.5, o_dy=0.07)

GUS = dict(skin=GUS_SKIN, eye='droopy', eye_w=0.30, eye_h=0.34, eye_gap=0.10, eye_cy=0.44, lid=0.30, pupil=0.12,
           rim=0.021, lid_w=0.036, kx_eye=0.26, kx_nose=0.30, nose_over=0.03,
           nose=dict(kind='potato', w=0.48, h=0.28, fill=NOSE_RED, shade='htR',
                     harm=[(3, 0.07, 2.6), (2, 0.045, 1.4), (5, 0.035, 0.2), (7, 0.018, 1.1)],
                     pores=((0.10, 0.10, 0.011), (0.26, -0.08, 0.009), (-0.05, 0.28, 0.01), (0.30, 0.22, 0.008))),
           brow='scallop', brow_th=0.09, brow_len=0.31, brow_gap=0.04, brow_arch=0.05, brow_tilt0=-4, brow_dx=0.015,
           brow_fill='#ADA69B', brow_droop=1.1,
           ear=(0.10, 0.125, 0.085), ear_y=0.54, ear_front=True, hair='fringe', fringe_poke=0.075, jowls=0.07,
           cheeks=True, fold='jowl2', bags=True, shade='htR', shade_op=0.4, o_dy=0.03, mouth_k=1.0)

WIT = dict(skin=SKIN_W, eye='generic', eye_w=0.20, eye_h=0.27, eye_gap=0.12, eye_cy=0.42, lid=0.70, pupil=0.10,
           rim=0.02, lid_w=0.03, kx_eye=0.26, kx_nose=0.36, nose_over=0.03,
           nose=dict(kind='button', w=0.25, h=0.19, fill=NOSE_W, shade='htC'),
           brow='generic', brow_th=0.05, brow_len=0.20, brow_gap=0.05, brow_arch=0.06,
           ear=(0.075, 0.09, 0.065), ear_y=0.53, hair='comb', shade='htC', shade_op=0.45)


# ======================================================================== COSTUMES (one torso surface each)
def torso_frame(J):
    Y, H = J['Y'], J['H']
    v = (H[0] - Y[0], H[1] - Y[1]); L = math.hypot(*v) or 1
    d = (v[0] / L, v[1] / L)
    return Y, H, d, (d[1], -d[0]), L


def waistcoat(J, D, f, seed, fill=VEST):
    """Bix: black waistcoat with a deep V over a white shirt; pointed hem; brass buttons."""
    Y, H, d, r, L = torso_frame(J)
    Nb = J['Nb']
    at = lambda b, lat, al: (b[0] + r[0] * f * lat * D + d[0] * al * D, b[1] + r[1] * f * lat * D + d[1] * al * D)
    W0 = lerp(Y, H, 0.86)
    c_b = at(Nb, -0.075, 0.0); c_f = at(Nb, 0.075, 0.0)
    v = at(Y, 0.035, 0.44 * L / D)
    shirt = [at(Nb, -0.11, -0.03), at(Nb, 0.11, -0.03), at(v, 0.0, 0.05)]
    vest = [c_b, J['Sf'], at(Y, -0.21, 0.30), at(W0, -0.17, 0), at(H, -0.17, 0.05), at(H, 0.03, 0.15),
            at(H, 0.21, 0.06), at(W0, 0.19, 0), at(Y, 0.235, 0.30), J['Sn'], c_f, v]
    out = [inked(shirt, SHIRT, (0.01 * D, 0.016 * D), seed + 1)]
    inner = crescent(vest, 'htC', 0.07 * D * f, -0.02 * D, 0.55)
    out.append(inked(vest, fill, (0.016 * D, 0.026 * D), seed, inner=inner))
    for t in (0.18, 0.42, 0.66):
        q = lerp(at(v, 0.012, 0.03), at(H, 0.05, 0.06), t)
        out.append(inked(ellipse_pts(q[0], q[1], 0.022 * D, 0.022 * D, 20), BRASS, (0.007 * D, 0.011 * D), seed + 5))
    # pocket welt on the back-side chest
    p = at(Y, -0.12, 0.40)
    out.append(stroke([p, at(p, 0.09, -0.01)], 0.016 * D, color=CLOTH, taper=(0.1, 0.1)))
    return ''.join(out)


def armband(S, E, D, seed, frac=0.42, color=ROSE):
    c = lerp(S, E, frac)
    v = (E[0] - S[0], E[1] - S[1]); l = math.hypot(*v) or 1; d = (v[0] / l, v[1] / l); n = (-d[1], d[0])
    a, b = 0.068 * D, 0.034 * D
    pts = [padd(padd(c, n, a), d, -b), padd(padd(c, n, -a), d, -b), padd(padd(c, n, -a), d, b), padd(padd(c, n, a), d, b)]
    return inked(spline(pts, True, 4), color, (0.01 * D, 0.015 * D), seed)


def sweater_vest(J, D, f, seed):
    """Gus: mustard knit vest with a paunch and a ribbed hem."""
    Y, H, d, r, L = torso_frame(J)
    Nb = J['Nb']
    at = lambda b, lat, al: (b[0] + r[0] * f * lat * D + d[0] * al * D, b[1] + r[1] * f * lat * D + d[1] * al * D)
    hem = lerp(Y, H, 0.94)
    belly = lerp(Y, H, 0.66)
    front = spline([at(Y, 0.25, 0.28), at(belly, 0.33, -0.05), at(belly, 0.31, 0.12), at(hem, 0.25, 0.0)], False, 8)
    back = spline([at(hem, -0.21, 0.0), at(belly, -0.22, 0.0), at(Y, -0.22, 0.28)], False, 8)
    vest = [at(Nb, -0.085, 0.0), J['Sf']] + back[::-1] + [at(hem, 0.04, 0.012)] + front[::-1] + [J['Sn'], at(Nb, 0.085, 0.0), at(Y, 0.04, 0.24)]
    inner = crescent(vest, 'htM', 0.07 * D * f, -0.03 * D, 0.55)
    band_top = [at(hem, -0.21, -0.075), at(hem, 0.26, -0.075)]
    rib = [band_top[0], band_top[1], at(hem, 0.26, 0.012), at(hem, -0.21, 0.012)]
    lines = ''
    for j in range(1, 14):
        t = j / 14
        a = lerp(band_top[0], band_top[1], t); b = lerp(rib[3], rib[2], t)
        lines += stroke([a, b], 0.01 * D, color=shade_hex(MUSTARD, 0.35), taper=(0.05, 0.05))
    inner += clipped(vest, f'<path d="{P(rib)}" fill="{shade_hex(MUSTARD, 0.12)}"/>' + lines)
    out = [inked(vest, MUSTARD, (0.016 * D, 0.026 * D), seed, inner=inner)]
    out.append(stroke(band_top, 0.014 * D, taper=(0.05, 0.05)))
    return ''.join(out)


def napkin(J, D, f, seed):
    """Gus: a rose-check napkin tucked into his collar like a bib, corners sticking up."""
    Y, H, d, r, L = torso_frame(J)
    Nb = J['Nb']
    at = lambda b, lat, al: (b[0] + r[0] * f * lat * D + d[0] * al * D, b[1] + r[1] * f * lat * D + d[1] * al * D)
    pts = spline([at(Nb, -0.20, -0.07), at(Nb, -0.06, 0.03), at(Nb, 0.08, 0.03), at(Nb, 0.23, -0.07),
                  at(Y, 0.25, 0.26), at(Y, 0.17, 0.46), at(Y, 0.05, 0.60), at(Y, -0.08, 0.46), at(Y, -0.17, 0.24)], True, 6)
    x0 = min(q[0] for q in pts) - 60; y0 = min(q[1] for q in pts) - 60
    inner = clipped(pts, f'<rect x="{f1(x0)}" y="{f1(y0)}" width="600" height="600" fill="url(#chkR)"/>', OFF)
    inner += crescent(pts, 'htKs', 0.05 * D * f, -0.03 * D, 0.25)
    out = [inked(pts, CLOTH, (0.013 * D, 0.021 * D), seed, inner=inner)]
    for a, b in ((at(Nb, 0.0, 0.06), at(Y, 0.02, 0.40)), (at(Nb, 0.12, 0.05), at(Y, 0.14, 0.30))):
        out.append(stroke([a, b], 0.011 * D, taper=(0.2, 0.5), wmin=0.3))
    return ''.join(out)


def check_rose(pid='chkR'):
    return check_pattern(pid, ROSE, tile=56, band=16, pitch=8, r=2.2)


# ======================================================================== BODIES
def bix_body(D, facing):
    return Body(D, facing, plate=CYAN, glove=WHITE, shoe='brogue', seed=400,
                L=dict(neck_vis=0.10, spine=0.97, thigh=0.80, shin=0.74))


def gus_body(D, facing):
    return Body(D, facing, plate=MUSTARD, glove=GUS_SKIN, shoe='loafer', seed=500, knuckle=True,
                L=dict(spine=0.90, thigh=0.78, shin=0.74, neck_vis=0.07, neck_x=0.10, neck_w=0.20, up=0.80, fore=0.80,
                       sh=0.29))


def bix_figure(f, E, b, p, J, prop='', order=None, extra=None):
    D = b.D; fc = b.f
    vest = waistcoat(J, D, fc, 460)
    ap = apron(J['H'], p['spine'], D, p.get('ap_hang', 2 * fc), p.get('ap_spread', 18), 431, fc, length=p.get('ap_len', 1.02),
               wb=0.32, flutter=p.get('ap_flutter', 0.0), tails=p.get('ap_tails', -14 * fc))
    bt = bow_tie(padd(J['Nb'], J['sd'], 0.035 * D), -p.get('spine', 0) * 0.5, D, 441, squash=0.90, width=0.36)
    col = collar_points(J, D, WHITE, 451, fc, open_=0.0, drop=0.14)
    bands = dict(n_band=armband(J['Sn'], J['nE'], D, 470), f_band=armband(J['Sf'], J['fE'], D, 471))
    parts = dict(vest=vest, hip=ap, collar=col + bt, prop=prop, **bands)
    if extra:
        parts.update(extra)
    order = order or ['shadow', 'f_arm', 'f_band', 'f_hand', 'f_leg', 'spine', 'yoke', 'n_leg', 'vest', 'hip', 'neck',
                      'collar', 'head', 'n_arm', 'n_band', 'n_hand', 'prop', 'f_thumb', 'n_thumb', 'marks']
    return figure(f, E, b, J, order, **parts)


def gus_figure(f, E, b, p, J, prop='', order=None, extra=None):
    D = b.D; fc = b.f
    vest = sweater_vest(J, D, fc, 560)
    nap = napkin(J, D, fc, 570)
    col = collar_points(J, D, CLOTH, 530, fc, open_=0.02, drop=0.12)
    bl = belt(J['H'], p.get('spine', 0), D, 540)
    parts = dict(vest=vest, hip=bl, collar=nap + col, prop=prop)
    if extra:
        parts.update(extra)
    order = order or ['shadow', 'f_arm', 'f_hand', 'f_thumb', 'f_leg', 'spine', 'yoke', 'n_leg', 'hip', 'vest', 'neck',
                      'collar', 'head', 'n_arm', 'n_hand', 'prop', 'n_thumb', 'marks']
    return figure(f, E, b, J, order, **parts)


def defs_all():
    return common_defs() + check_rose() + black_defs()


# ======================================================================== FACES SHEET (hero head, 3 x 2)
BIX_EXPR = [
    ('neutral', dict(tilt=0, gaze=(-0.35, 0.12))),
    ('surprised', dict(tilt=-3, lid=(0.0, 0.0), eye_scale=(1.12, 1.12), gaze=(0.0, -0.05), brow_raise=(0.10, 0.10),
                       brow_arch=(0.17, 0.17), mouth='o', stache=-0.012, strand=0.85)),
    ('angry', dict(tilt=4, lid=(0.38, 0.38), lid_tilt=(-24, -24), low=(0.12, 0.12), low_bow=(0.05, 0.05), gaze=(-0.25, 0.25),
                   brow_raise=(-0.035, -0.035), brow_tilt=(26, 26), brow_arch=(0.02, 0.02), mouth='grit', stache=0.03,
                   tip_flush=True, marks=[('vein', 0.25, -0.33, 0.075)])),
    ('smug', dict(tilt=7, lid=(0.50, 0.50), lid_tilt=(5, 5), low=(0.10, 0.10), low_bow=(0.06, 0.06), gaze=(-0.95, 0.35),
                  brow_raise=(0.0, 0.085), brow_tilt=(6, -10), brow_arch=(0.04, 0.2), mouth='curl', stache=-0.035, nose_tilt=8)),
    ('panic', dict(tilt=-4, lid=(0.12, 0.12), lid_tilt=(24, 24), eye_scale=(1.08, 1.08), pupil=0.106,
                   gaze_lr=((-0.6, 0.8), (-0.6, 0.8)), brow_raise=(0.07, 0.07), brow_tilt=(-24, -24), brow_arch=(0.12, 0.12),
                   mouth='gape', stache=-0.02, strand=1.0,
                   marks=[('sweat', -0.64, -0.22, 0.12, -30), ('sweat', 0.66, -0.34, 0.13, 35)])),
    ('side-eye', dict(tilt=-3, lid=(0.56, 0.56), lid_tilt=(-4, -4), gaze=(1.0, 0.08), brow_raise=(-0.02, 0.025),
                      brow_tilt=(4, -3), brow_arch=(0.02, 0.05), mouth='flat', mouth_dx=0.03, stache=0.025)),
]


def bust(face, E, D, facing, body_fn, fig_fn, clip_rect):
    b = body_fn(D, facing)
    p = dict(neck=8 if facing < 0 else 8, tilt=E.get('tilt', 0), spine=0, nup=-10 * facing, nlo=-6 * facing,
             fup=8 * facing, flo=4 * facing, nFr=(0.0, 1.45), fFr=(0.0, 1.45), ngrip='hidden', fgrip='hidden')
    J = b.joints(face, p)
    svg = fig_fn(face, E, b, p, J, order=['vest', 'neck', 'collar', 'head'])
    x, y, w, h = clip_rect
    return clipped([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], svg)


def build_faces():
    W = H = 1080
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{defs_all()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    D = 226
    info = []
    for k, (name, E) in enumerate(BIX_EXPR):
        col, row = k % 3, k // 3
        x0, y0 = col * 360, row * 540
        cx, cy = x0 + 186, y0 + 222
        f = BigFace(cx, cy, D, -0.35, BIX, 11)
        out.append(bust(f, E, D, -1, bix_body, bix_figure, (x0 + 4, y0 + 4, 352, 532)))
        if k == 0:
            info = f.measure(E)
    for k in (1, 2):
        out.append(stroke([(360 * k, 30), (360 * k, 1050)], 3, color='#D8CDB6', taper=(0, 0)))
    out.append(stroke([(30, 540), (1050, 540)], 3, color='#D8CDB6', taper=(0, 0)))
    out.append(grain(W, H, 0.10))
    out.append('</svg>')
    return ''.join(out), info


# ======================================================================== LINEUP POSES (540 x 1080)
E_BIX_STAND = dict(tilt=3, gaze=(-0.5, 0.15), brow_raise=(0.0, 0.03), brow_arch=(0.10, 0.13), lid=(0.27, 0.27),
                   mouth='none', stache=-0.01)
E_GUS_STAND = dict(tilt=-5, gaze=(-0.75, 0.55), lid=(0.30, 0.30), lid_tilt=(12, 12), brow_raise=(0.01, 0.01),
                   brow_tilt=(-4, -4), mouth='none')


def bix_stand(D, x, FL, E):
    facing = -1
    fn = lambda cx, cy: BigFace(cx, cy, D, -0.45, BIX, 11)
    b = bix_body(D, facing)
    p = dict(neck=8, tilt=E.get('tilt', 0), spine=-3, bow=0.03,
             nWr=(-0.46, -0.30), nbend=-1, nhand=-92, ngrip='flat', nthumb=1, nthumb_at=0.52, nthumb_sp=40,
             fup=24, flo=-70, flo_k=0.42, fgrip='hidden',
             nFr=(-0.04, 1.54), ntoe=-96, nkbend=1,
             fFr=(0.16, 1.42), ftoe=-35, fkbend=1, fsole=-1,
             ap_hang=-3, ap_spread=18, ap_tails=14)
    f, J = place(fn, b, p, x, FL, 'n')
    return f, b, p, J


def bix_stand_svg(D, x, FL, E):
    f, b, p, J = bix_stand(D, x, FL, E)
    s = 0.42 * D / 172
    palm = padd(J['nW'], DIR(p['nhand']), 0.10 * D)
    cb = (palm[0] - 0.02 * D, palm[1] - 0.035 * D)
    c = cup(cb[0], cb[1], s, 0) + steam_small(cb[0], cb[1] - 138 * s, s * 0.55)
    sh = ht_ellipse((J['nF'][0] + J['fF'][0]) / 2, FL + 6, 0.50 * D, 10, INK, 9, 3.0)
    svg = bix_figure(f, E, b, p, J, prop=c, extra=dict(shadow=sh))
    return svg, f, J


def gus_stand(D, x, FL, E):
    facing = -1
    fn = lambda cx, cy: BigFace(cx, cy, D, -0.5, GUS, 21)
    b = gus_body(D, facing)
    p = dict(neck=26, tilt=E.get('tilt', 0), spine=15, bow=0.08, sh_nk=0.95, sh_fk=0.80,
             nWr=(-0.12, 1.50), nbend=1, nhand=-20, ngrip='mitt', nthumb=1, nthumb_at=0.6, nthumb_sp=55,
             fWr=(0.10, 1.52), fbend=-1, fgrip='mitt', fthumb=-1,
             nFr=(-0.16, 1.42), ntoe=-100, nkbend=1,
             fFr=(0.22, 1.42), ftoe=-62, fkbend=-1)
    f, J = place(fn, b, p, x, FL, 'n')
    return f, b, p, J


def gus_stand_svg(D, x, FL, E):
    f, b, p, J = gus_stand(D, x, FL, E)
    dc = padd(J['nW'], DIR(p['nhand']), 0.14 * D)
    dn = held_doughnut(dc[0], dc[1] - 0.02 * D, 0.30 * D / 160, -14, drip=False)
    lo = min(q[1] for q in J['nshoe'] + J['fshoe'])
    sh = ht_ellipse((J['nF'][0] + J['fF'][0]) / 2, FL + 6, 0.60 * D, 10, INK, 9, 3.0)
    svg = gus_figure(f, E, b, p, J, prop=dn, extra=dict(shadow=sh))
    return svg, f, J


def build_single(kind, sil=False):
    W, H = 540, 1080
    FLOOR_Y = 1010
    target = 900.0 if kind == 'hero' else 780.0
    E = E_BIX_STAND if kind == 'hero' else E_GUS_STAND
    fn = bix_stand_svg if kind == 'hero' else gus_stand_svg
    D = 230.0 if kind == 'hero' else 225.0
    x = 292 if kind == 'hero' else 290
    fl = FLOOR_Y
    for _ in range(7):
        svg, f, J = fn(D, x, fl, E)
        sole = max(max(q[1] for q in J['nshoe']), max(q[1] for q in J['fshoe']))
        fl += FLOOR_Y - sole
        D = D * target / (sole - f.top_with_hair(E))
    svg, f, J = fn(D, x, fl, E)
    sole = max(max(q[1] for q in J['nshoe']), max(q[1] for q in J['fshoe']))
    top = f.top_with_hair(E)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{defs_all()}</defs>', f'<rect width="{W}" height="{H}" fill="#EDEAE4"/>',
           f'<g filter="url(#blk)">{svg}</g>' if sil else svg, '</svg>']
    return ''.join(out), dict(D=D, sole=sole, top=top, height=sole - top, head_frac=D / (sole - top), head=(f.cx, f.cy),
                              meas=f.measure(E))


# ======================================================================== SCENE: café terrace, the cup is gone
BIX_SCENE_E = dict(tilt=-6, lid=(0.50, 0.50), lid_tilt=(5, 5), low=(0.10, 0.10), low_bow=(0.06, 0.06),
                   brow_raise=(0.085, 0.0), brow_tilt=(-10, 6), brow_arch=(0.2, 0.04), mouth='curl', stache=-0.035, nose_tilt=8)
GUS_SCENE_E = dict(tilt=-6, lid=(0.0, 0.0), eye_scale=(1.08, 1.08), brow_raise=(0.05, 0.05), brow_tilt=(-14, -14),
                   brow_arch=(0.12, 0.12), mouth='o', flush=False)
WIT_SCENE_E = dict(lid=(0.70, 0.70), brow_raise=(0.05, 0.0), brow_tilt=(-8, 4), brow_arch=(0.12, 0.02))


def bix_scene(head=(350, 690), D=262, FL=1540):
    fn = lambda x, y: BigFace(x, y, D, 0.55, BIX, 11)
    b = bix_body(D, 1)
    p = dict(neck=8, tilt=-6, spine=12, bow=0.035, yoke_k=1.07,
             fstr=199, fhand=199, fgrip='mitt', fthumb=-1, fthumb_at=0.66, fthumb_sp=46,
             nup=-40, nlo=80, nlo_k=0.42, ngrip='hidden',
             nFr=(0.06, 1.56), ntoe=90, nkbend=-1,
             fFr=(-0.46, 1.48), ftoe=-62, fkbend=-1,
             ap_hang=5, ap_spread=20, ap_flutter=0.02, ap_tails=-52, ap_len=1.05)
    f, J = place(fn, b, p, head[0], FL, 'n')
    return f, b, p, J


def gus_scene(head=(880, 800), D=268, FL=1540, target=None):
    fn = lambda x, y: BigFace(x, y, D, -0.60, GUS, 21)
    b = gus_body(D, -1)
    p = dict(neck=22, tilt=-6, spine=6, bow=0.07, yoke_k=1.0, sh_nk=0.92, sh_fk=0.80,
             nstr=-84, ngrip='mitt', nthumb=1, nthumb_at=0.70, nthumb_sp=62,
             fup=-2, flo=-10, fgrip='mitt', fthumb=-1,
             nFr=(-0.50, 1.36), ntoe=-90, nkbend=1,
             fFr=(0.26, 1.42), ftoe=-48, fkbend=-1)
    f, J = place(fn, b, p, head[0], FL, 'n')
    if target is not None:
        for _ in range(3):
            v = (target[0] - J['Sn'][0], target[1] - J['Sn'][1])
            p['nstr'] = ang_of(v)
            f, J = place(fn, b, p, head[0], FL, 'n')
    return f, b, p, J


def build_scene(sil=False):
    W, H = 1080, 1920
    FL = 1540
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{defs_all()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    bix, bb, bp, bJ = bix_scene(FL=FL)
    S = bix.D
    cs = 0.45 * S / 172
    cup_b = padd(bJ['fW'], DIR(bp['fhand']), 0.205 * S)
    dn_target = (482, 980)
    gus, gb, gp, gJ = gus_scene(target=dn_target, FL=FL)
    G = gus.D
    hdg = DIR(gp['nstr'])
    ds = 0.30 * G / 160
    dn_c = padd(padd(gJ['nW'], hdg, 0.16 * G), (0, 1), 0.035 * G)
    ghost_b = (dn_c[0] - 4, dn_c[1] + 50 * ds + 138 * cs)
    cup_top = (cup_b[0], cup_b[1] - 120 * cs)
    gE = dict(GUS_SCENE_E); gE['look'] = cup_top
    gE['marks'] = [('sweat', -0.52, -0.50, 0.11, -30)]
    bE = dict(BIX_SCENE_E); bE['look'] = (gus.cx - 0.15 * G, gus.cy - 0.05 * G)
    if not sil:
        out.append(floor2())
        gsvg, glass = window2()
        out.append(gsvg)
        wit = BigFace(965, 512, 230, -0.55, WIT, 31)
        wE = dict(WIT_SCENE_E); wE['look'] = dn_c
        wsvg = wit.draw(wE) + newspaper(852, 545, 1072, 668)
        wb = Body(230, -1, plate=CYAN, glove=SKIN_W, seed=600)
        for k, (x, y, a, sd) in enumerate(((868, 589, 180, 1), (1056, 593, 180, -1))):
            wsvg += inked(wb.mitten_pts((x, y), a, 1.0), SKIN_W, (4, 6), 610 + k)
            wsvg += inked(wb.thumb_pts((x, y), a, sd, 1.0, 0.62, 78), SKIN_W, (3, 4.5), 620 + k)
        out.append(clipped(glass, wsvg))
        out.append(window_frame())
        out.append(awning2())
        out.append(back_table(150, 1150, 0.85))
        out.append(shrub_at(-6, 790, 1.0))
        out.append(ht_ellipse((bJ['nF'][0] + bJ['fF'][0]) / 2 + 20, FL + 8, 170, 16, INK, 10, 3.4))
        out.append(ht_ellipse((gJ['nF'][0] + gJ['fF'][0]) / 2, FL + 8, 180, 16, INK, 10, 3.4))
        trail = cup_ghost(ghost_b[0], ghost_b[1], cs, 0.6)
        for k, dx in enumerate((-0.13, -0.015, 0.10)):
            x = dn_c[0] + dx * S
            y0 = dn_c[1] - 0.20 * S - 0.02 * S * (k == 1)
            trail += stroke([(x, y0), (x - 0.01 * S, y0 - 0.30 * S - 0.05 * S * (k == 1))], 6, taper=(0.85, 0.1), wmin=0.2)
        path = cbez((bix.cx + 0.70 * S, bix.cy - 0.05 * S), (bix.cx + 0.72 * S, bix.cy - 0.95 * S),
                    (bix.cx - 0.05 * S, bix.cy - 1.12 * S), (cup_b[0] + 0.42 * S, cup_b[1] - 0.30 * S), 60)
        trail += dotted(path, S, 0.75)
        out.append(trail)
    dn = held_doughnut(dn_c[0], dn_c[1], ds, -10)
    gsil = gus_figure(gus, gE, gb, gp, gJ, prop=dn,
                      order=['halo', 'f_arm', 'f_hand', 'f_thumb', 'f_leg', 'spine', 'yoke', 'n_leg', 'hip', 'vest',
                             'neck', 'collar', 'head', 'n_arm', 'n_hand', 'prop', 'n_thumb', 'marks'],
                      extra=dict(halo='' if sil else gb.halo(gJ, CREAM, 0.4)))
    cp = cup(cup_b[0], cup_b[1], cs, 0) + steam_small(cup_b[0], cup_b[1] - 138 * cs, cs * 0.62)
    bsil = bix_figure(bix, bE, bb, bp, bJ, prop=cp,
                      order=['halo', 'n_arm', 'n_band', 'f_leg', 'spine', 'yoke', 'n_leg', 'vest', 'hip', 'f_arm', 'f_band',
                             'f_hand', 'neck', 'collar', 'head', 'prop', 'f_thumb', 'marks'],
                      extra=dict(halo='' if sil else bb.halo(bJ, CREAM, 0.4)))
    if sil:
        out.append(f'<g filter="url(#blk)">{gsil}</g><g filter="url(#blk)">{bsil}</g>')
    else:
        out.append(gsil); out.append(bsil)
        out.append(grain(W, H, 0.12))
    out.append('</svg>')
    info = dict(bix=(bix.cx, bix.cy, bix.D), gus=(gus.cx, gus.cy, gus.D), cup=cup_b, dn=dn_c,
                bix_H=(max(q[1] for q in bJ['nshoe']) - bix.top_with_hair(bE)) / bix.D,
                gus_H=(max(q[1] for q in gJ['nshoe'] + gJ['fshoe']) - (gus.cy - gus.R)) / gus.D)
    return ''.join(out), info


if __name__ == '__main__':
    import json, sys
    svg, info = build_scene()
    open(os.path.join(HERE, 'scene.svg'), 'w').write(svg)
    open(os.path.join(HERE, 'scene_sil.svg'), 'w').write(build_scene(sil=True)[0])
    svg2, info2 = build_faces()
    open(os.path.join(HERE, 'faces.svg'), 'w').write(svg2)
    svg3, info3 = build_single('hero')
    open(os.path.join(HERE, 'hero.svg'), 'w').write(svg3)
    svg4, info4 = build_single('partner')
    open(os.path.join(HERE, 'partner.svg'), 'w').write(svg4)
    open(os.path.join(HERE, 'hero_sil.svg'), 'w').write(build_single('hero', True)[0])
    open(os.path.join(HERE, 'partner_sil.svg'), 'w').write(build_single('partner', True)[0])
    r = lambda v: [round(c, 3) for c in v] if isinstance(v, (tuple, list)) else (round(v, 3) if isinstance(v, float) else v)
    def rr(d):
        return {k: (rr(v) if isinstance(v, dict) else r(v)) for k, v in d.items()}
    print('scene', rr(info))
    print('faces', rr(info2))
    print('hero', rr(info3))
    print('partner', rr(info4))
