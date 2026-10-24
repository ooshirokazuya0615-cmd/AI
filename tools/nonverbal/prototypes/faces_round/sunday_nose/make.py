#!/usr/bin/env python3
"""Sunday Nose / 日曜版の鼻 -- ROUND heads on stick bodies.

ONE round-head face rig (RoundFace: true circle skull, ears / hair / nose / jowls break it,
teardrop eyes resting on a big nose, lids, pupils, brows, swap mouths) and
ONE stick-body rig (Body: neck stub + costume anchor + tapered spine + hip prop,
ink limbs over an off-register cyan / mustard colour plate, mittens with thumbs, shoes).
scene.svg, poses.svg and lineup.svg are all built from these two rigs.
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


# ======================================================================== ROUND HEAD RIG
FDEF = dict(tilt=0, pupil_vis=0.40, brow_follow=False, eye_rot=(0, 0), eye_scale=(1, 1), eye_push=0.0, lid=(0, 0),
            lid_tilt=(0, 0), gaze=(0, 0), gaze_lr=None, pupil_r=None, brow_raise=(0, 0), brow_tilt=(0, 0),
            brow_arch=(0.10, 0.10), brow_gap=None, brow_dx=(0, 0), nose_tilt=0, nose_dx=0, nose_dy=0, flush=False,
            tip_flush=False, bead=False, mouth='none', marks=(), hair_up=0.0, cheek_flush=False, mouth_dx=0.0)


class RoundFace:
    """True-circle skull of diameter D.  Every size below is a fraction of D.
    Emotion machine (unchanged from the original Sunday Nose rig): white teardrop eyes whose points rest on a
    big nose, each rotating about its point, scaling and taking a flat lid cut; floating brush brows; the
    mouth hides under the nose and drops out below it for big takes.  Turn is carried by the features, the
    ear(s), the crown flicks and the neck moving together (a circle shows no rotation by itself)."""

    def __init__(s, cx, cy, D, skin, turn=0.0, nose=None, seed=1, **kw):
        p = dict(eye_w=0.24, eye_h=0.36, eye_gap=0.05, eye_tip=0.56, eye_ox=1.08,
                 brow_len=0.22, brow_th=0.04, brow_gap=0.08, pupil=0.03, rim=0.022, lid_w=0.04,
                 hair='flicks', ears=1, ear=(0.10, 0.12, 0.08), ear_y=0.52, ear_front=False, sideburn=True,
                 jowls=0.0, fringe=False, comb=False, line=(0.021, 0.035), shade='htC', shade_op=0.55,
                 jaw=None, jaw_from=0.68, kx_eye=0.37, kx_nose=0.54, far_sq=0.5, squash=0.0, nose_wk=0.10,
                 mouth_k=1.0, cheeks=False, hair_k=1.0)
        p.update(kw)
        s.p = p
        s.cx, s.cy, s.D, s.R = cx, cy, D, D / 2.0
        s.skin, s.turn, s.seed, s.nose = skin, turn, seed, nose
        s.f = 1 if turn >= 0 else -1
        s.fx = cx + turn * p['kx_eye'] * D
        s.ny = cy + (nose['y'] - 0.5) * D
        s.ncx = cx + turn * p['kx_nose'] * D
        s.nw = nose['w'] * D * (1 + p['nose_wk'] * abs(turn))
        s.nh = nose['h'] * D
        s.head = s.silhouette()

    # ------------------------------------------------------------------ geometry
    def silhouette(s):
        pts = []
        N = 240
        for i in range(N):
            th = 2 * math.pi * i / N
            r = s.R
            if s.p['jowls']:
                for c in (34, 146):
                    d = math.atan2(math.sin(th - math.radians(c)), math.cos(th - math.radians(c)))
                    r += s.D * s.p['jowls'] * math.exp(-(d / math.radians(15)) ** 2)
            pts.append((s.cx + r * math.cos(th) * (1 + s.p['squash']), s.cy + r * math.sin(th) * (1 - s.p['squash'])))
        return pts

    def top_y_at(s, x):
        dx = x - s.cx
        if abs(dx) >= s.R:
            return s.cy
        return s.cy - math.sqrt(s.R ** 2 - dx * dx)

    def nose_geom(s, e):
        n = s.nose
        w, h = s.nw, s.nh
        tilt = e['nose_tilt']
        cx = s.ncx + e['nose_dx'] * s.D
        cy = s.ny + e['nose_dy'] * s.D - abs(tilt) * 0.0015 * s.D
        ang = -s.f * tilt                     # tipping up rotates the tip toward the facing side
        if n['kind'] == 'button':
            loc = ellipse_pts(cx, cy, w / 2, h / 2, 100)
        else:
            harm = n.get('harm', [(3, 0.075, 0.5 if s.f > 0 else 2.6), (2, 0.04, 1.4), (5, 0.022, 0.2)])
            loc = blob_pts(cx, cy, w, h, harm, 160)
        pts = xf(loc, ang=ang, c=(cx, cy))
        return dict(pts=pts, c=(cx, cy), ang=ang, w=w, h=h, tilt=tilt)

    def eye_geom(s, side, e):
        i = 0 if side < 0 else 1
        W, H = s.p['eye_w'] * s.D, s.p['eye_h'] * s.D
        rx = W / 2; ry = H * 0.375; ox = rx * s.p['eye_ox']
        bcx, bcy = ox, -(H - ry)
        loc = resample(hull(ellipse_pts(bcx, bcy, rx, ry, 80) + [(0, 0)]), 2.0)
        sc = e['eye_scale'][i]
        far = abs(s.turn) > 0.05 and side == s.f
        sxf = 1 - s.p['far_sq'] * abs(s.turn) if far else 1.0
        ang = side * e['eye_rot'][i]
        tipx = s.fx + side * (s.p['eye_gap'] / 2 + e['eye_push'] / 2) * s.D
        tipy = s.cy + (s.p['eye_tip'] - 0.5) * s.D

        def T(pt):
            x, y = pt
            x = x * side * sc * sxf; y = y * sc
            x, y = rot((x, y), ang)
            return (x + tipx, y + tipy)

        poly = [T(pt) for pt in loc]
        out = dict(poly=poly, far=far, sc=sc * (sxf if far else 1))
        lid = e['lid'][i]
        vis = loc
        if lid > 0:
            ly = -H + lid * H
            tt = math.tan(math.radians(e['lid_tilt'][i]))
            fl = lambda q: q[1] - ly - (bcx - q[0]) * tt
            lp = clip_half(loc, fl)
            vis = clip_half(loc, lambda q: -fl(q))
            ch = [q for q in lp if abs(fl(q)) < 1e-6]
            out['lid'] = [T(q) for q in lp]
            if len(ch) >= 2:
                ch = sorted(ch)
                out['chord'] = [T(ch[0]), T(ch[-1])]
        pr = (e['pupil_r'] or s.p['pupil']) * s.D
        gx, gy = e['gaze_lr'][i] if e['gaze_lr'] else e['gaze']
        gl = rot((gx, gy), -ang); glx, gly = gl[0] * side, gl[1]
        m = math.hypot(glx, gly)
        if m > 1:
            glx, gly = glx / m, gly / m
        sxe = sc * (sxf if far else 1)
        prl = pr / sxe
        px = bcx + glx * rx; py = bcy + gly * ry
        need = prl + 2.5 / sc
        if lid > 0:
            ly = -H + lid * H
            tt = math.tan(math.radians(e['lid_tilt'][i]))
            py = min(py, ly + (bcx - px) * tt + prl * 0.45) if gly <= 0.2 else py
            need = prl * e['pupil_vis']
        vis_c = resample(vis, 3.0) if len(vis) > 3 else vis
        xs = [q[0] for q in vis_c]; ys = [q[1] for q in vis_c]
        gm = math.hypot(glx, gly)
        best = None; bscore = -1e9
        stp = 1.5
        yy = min(ys)
        while yy <= max(ys):
            xx = min(xs)
            while xx <= max(xs):
                q = (xx, yy)
                if inner_dist(q, vis_c) >= need:
                    dd = math.hypot(xx - px, yy - py)
                    sc_ = (xx * glx + yy * gly) / gm - 0.25 * dd if gm > 0.5 else -dd
                    if sc_ > bscore:
                        bscore = sc_; best = q
                xx += stp
            yy += stp
        if best is None:
            best = centroid(vis)
        out['pupil'] = T(best); out['pr'] = pr
        out['top'] = min(poly, key=lambda q: q[1])
        out['bc'] = T((bcx, bcy))
        if 'chord' in out:
            out['lidtop'] = min(out['chord'], key=lambda q: q[1])
        return out

    # ------------------------------------------------------------------ parts
    def lw(s, k=1.0):
        return (s.p['line'][0] * s.D * k, s.p['line'][1] * s.D * k)

    def ear_sides(s):
        if not s.p['ears']:
            return ()
        if abs(s.turn) < 0.3:
            return (-1, 1)
        return (-s.f,)

    def ear_svg(s, side):
        rx, ry, pr = (k * s.D for k in s.p['ear'])
        ex = s.cx + side * (s.R + pr - rx)
        ey = s.cy + (s.p['ear_y'] - 0.5) * s.D
        pts = ellipse_pts(ex, ey, rx, ry, 50)
        out = inked(pts, s.skin, s.lw(0.8), s.seed + 40 + side,
                    inner=crescent(pts, 'htRs', -rx * 0.3 * side, -ry * 0.2, 0.6))
        a = (ex + side * rx * 0.30, ey - ry * 0.48)
        m = (ex + side * rx * 1.05, ey - ry * 0.05)
        b = (ex + side * rx * 0.30, ey + ry * 0.52)
        out += stroke(qbez(a, m, b), 0.022 * s.D, taper=(0.25, 0.3))
        return out

    def draw_sideburns(s):
        out = []
        for side in s.ear_sides():
            x0 = s.cx + side * (s.R - 0.075 * s.D)
            pts = qbez((x0, s.cy - 0.13 * s.D), (x0 - side * 0.035 * s.D, s.cy - 0.04 * s.D), (x0 - side * 0.02 * s.D, s.cy + 0.035 * s.D), 12)
            out.append(stroke(pts, 0.042 * s.D, taper=(0.15, 0.8), wmin=0.15))
        return ''.join(out)

    def draw_flicks(s, e):
        out = []
        up = e['hair_up']
        f = s.f
        hx = s.cx - s.turn * 0.12 * s.D
        for dx, ln, a in [(-0.075, 0.125, 18), (0.0, 0.15, 30), (0.075, 0.12, 42)]:
            x = hx + dx * s.D * f
            y = s.top_y_at(x) + 0.035 * s.D
            a2 = f * a * (1 - up) + (dx * 120 * up)
            L = ln * s.D * (1 + 0.35 * up) * s.p['hair_k']
            tip = rot((0, -L), a2)
            ctl = rot((0, -L * 0.55), a2 * 0.3)
            pts = qbez((x, y), (x + ctl[0], y + ctl[1]), (x + tip[0], y + tip[1]), 24)
            out.append(stroke(pts, 0.058 * s.D, taper=(0.02, 0.92), wmin=0.08))
        return ''.join(out)

    def draw_fringe(s, e):
        """grey brush fringe ring round the back of a bald dome, poking 0.05 D past the rim."""
        out = []
        sides = [-s.f] if abs(s.turn) >= 0.3 else [-1, 1]
        for side in sides:
            a0 = math.asin((0.26 - 0.5) * 2); a1 = math.asin((0.74 - 0.5) * 2)
            N = 44
            outer, inner = [], []
            for j in range(N + 1):
                t = j / N
                a = a0 + (a1 - a0) * t
                bump = abs(math.sin(t * math.pi * 5.5))
                env = math.sin(math.pi * t) ** 0.4
                ro = s.R + s.D * 0.052 * (0.45 + 0.55 * bump) * env
                ri = s.R - s.D * 0.095 * math.sin(math.pi * t) ** 0.7
                x = math.cos(a) * side; y = math.sin(a)
                outer.append((s.cx + x * ro, s.cy + y * ro)); inner.append((s.cx + x * ri, s.cy + y * ri))
            poly = outer + inner[::-1]
            out.append(f'<path d="{P(xf(poly, *OFF))}" fill="{HAIR_GREY}"/>')
            out.append(clipped(poly, f'<rect x="{f1(s.cx - s.D)}" y="{f1(s.cy - s.D)}" width="{f1(2 * s.D)}" height="{f1(2 * s.D)}" fill="url(#htKs)" opacity="0.8"/>', OFF))
            for j in range(0, N - 3, 4):
                out.append(stroke(outer[j:j + 6], 0.02 * s.D, taper=(0.3, 0.3), wmin=0.2))
            for j in range(2, N - 2, 5):
                q0 = inner[N - j]; q1 = outer[j]
                out.append(stroke([lerp(q1, q0, 0.15), lerp(q1, q0, 0.75)], 0.012 * s.D, taper=(0.3, 0.5), wmin=0.2))
        return ''.join(out)

    def draw_comb(s, e):
        """grey comb-over strands lifted off the crown (witness)."""
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

    def cheeks_svg(s, e):
        out = []
        for side in (-1, 1):
            if abs(s.turn) > 0.3 and side == s.f:
                continue
            x = s.ncx + side * (s.nw * 0.5 + s.D * 0.08) - s.f * (0.04 * s.D if side != s.f else 0)
            y = s.ny + s.nh * 0.12
            pts = ellipse_pts(x, y, s.D * 0.12, s.D * 0.075, 40)
            out.append(clipped(pts, f'<rect x="{f1(x - s.D * 0.2)}" y="{f1(y - s.D * 0.2)}" width="{f1(s.D * 0.4)}" height="{f1(s.D * 0.4)}" fill="url(#htR)"/>', OFF))
        return ''.join(out)

    def draw_jowl_fold(s, e):
        if not s.p['jowls']:
            return ''
        ng = s.nose_geom(e)
        cx, cy = ng['c']; w, h = ng['w'], ng['h']
        back = -s.f
        p0 = (cx + back * w * 0.62, cy - h * 0.05)
        p1 = (cx + back * w * 0.86, cy + h * 0.55)
        p2 = (cx + back * w * 0.66, cy + h * 0.98)
        return stroke(qbez(p0, p1, p2), 0.022 * s.D, taper=(0.35, 0.5))

    def draw_mouth(s, e):
        m = e['mouth']
        if m == 'none':
            return ''
        ng = s.nose_geom(e); D = s.D; k = s.p['mouth_k']
        x = ng['c'][0] + e['mouth_dx'] * D
        nb = ng['c'][1] + ng['h'] / 2
        out = []
        if m == 'o':
            pts = ellipse_pts(x - s.f * 0.04 * D, nb + 0.075 * D * k, 0.05 * D * k, 0.066 * D * k, 40)
            inner = f'<path d="{P(ellipse_pts(x - s.f * 0.04 * D, nb + 0.10 * D * k, 0.03 * D * k, 0.025 * D * k, 30))}" fill="{ROSE}"/>'
            out.append(inked(pts, MOUTH, (0.013 * D, 0.02 * D), 3, off=(0, 0), inner=clipped(pts, inner)))
        elif m == 'gape':
            w = 0.55 * D; d = 0.45 * D; top = nb - 0.02 * D
            pts = [(x + w / 2, top)] + [(x + w / 2 * math.cos(t), top + d * math.sin(t)) for t in [math.pi * j / 40 for j in range(41)]]
            tongue = ellipse_pts(x + 0.03 * D, top + d * 0.86, w * 0.30, d * 0.24, 50)
            teeth = [(x - w * 0.42, top), (x + w * 0.42, top), (x + w * 0.40, top + 0.05 * D), (x - w * 0.40, top + 0.05 * D)]
            out.append(f'<path d="{P(pts)}" fill="{MOUTH}"/>')
            out.append(clipped(pts, f'<path d="{P(tongue)}" fill="{ROSE}"/><path d="{P(teeth)}" fill="{WHITE}"/>'))
            out.append(f'<path d="{ring_d(pts, 0.02 * D, 0.03 * D, 0.6, 7)}" fill="{INK}" fill-rule="evenodd"/>')
        elif m == 'curl':
            sd = -s.f if abs(s.turn) >= 0.3 else 1
            p0 = (x + sd * ng['w'] * 0.15, nb - 0.035 * D)
            p1 = (x + sd * ng['w'] * 0.66, nb + 0.075 * D)
            p2 = (x + sd * ng['w'] * 0.98, nb - 0.045 * D)
            out.append(stroke(qbez(p0, p1, p2), 0.042 * D, taper=(0.0, 0.45)))
            out.append(stroke(qbez(p2, (p2[0] + sd * 0.03 * D, p2[1] - 0.004 * D), (p2[0] + sd * 0.024 * D, p2[1] - 0.04 * D), 8), 0.026 * D, taper=(0.0, 0.9)))
        elif m == 'wavy':
            y = nb + 0.085 * D
            pts = [(x - 0.13 * D + 0.26 * D * t, y + 0.022 * D * math.sin(t * math.pi * 4)) for t in (j / 40 for j in range(41))]
            out.append(stroke(pts, 0.034 * D, taper=(0.15, 0.15)))
        elif m == 'flat':
            y = nb + 0.07 * D
            out.append(stroke([(x - 0.08 * D, y), (x + 0.08 * D, y + 1)], 0.03 * D, taper=(0.2, 0.2)))
        return ''.join(out)

    def draw_eye(s, side, e):
        g = s.eye_geom(side, e)
        c = uid('c')
        out = [f'<clipPath id="{c}"><path d="{P(g["poly"])}"/></clipPath>']
        out.append(f'<path d="{P(xf(g["poly"], *OFF))}" fill="{WHITE}"/>')
        px, py = g['pupil']
        inner = f'<circle cx="{f1(px)}" cy="{f1(py)}" r="{f1(g["pr"])}" fill="{INK}"/>'
        if 'lid' in g:
            inner += f'<path d="{P(g["lid"])}" fill="{s.skin}"/>'
        out.append(f'<g clip-path="url(#{c})">{inner}</g>')
        if 'chord' in g:
            a, b = g['chord']
            out.append(stroke([a, b], s.p['lid_w'] * s.D, taper=(0.04, 0.04), wmin=0.6))
        out.append(f'<path d="{P(g["poly"])}" fill="none" stroke="{INK}" stroke-width="{f1(s.p["rim"] * s.D)}" stroke-linejoin="round"/>')
        return ''.join(out), g

    def draw_nose(s, e):
        ng = s.nose_geom(e)
        pts = ng['pts']; cx, cy = ng['c']; w, h = ng['w'], ng['h']; ang = ng['ang']
        base = s.nose['fill']
        fill = FLUSH if e['flush'] else base
        inner = crescent(pts, 'htR' if e['flush'] else s.nose.get('shade', 'htC'), -w * 0.16, -h * 0.18, 0.75 if e['flush'] else 0.55)
        if e['tip_flush']:
            blot = xf(ellipse_pts(cx + s.f * w * 0.18, cy + h * 0.10, w * 0.36, h * 0.34, 50), ang=ang, c=(cx, cy))
            inner += clipped(pts, f'<path d="{P(blot)}" fill="{FLUSH}"/>', OFF)
        hl = xf(ellipse_pts(cx - w * 0.17, cy - h * 0.22, w * 0.12, h * 0.085, 30), ang=ang - 20, c=(cx, cy))
        inner += f'<path d="{P(hl)}" fill="{WHITE}" fill-opacity="0.85"/>'
        out = [inked(pts, fill, (s.p['line'][0] * s.D * 0.85, s.p['line'][1] * s.D * 0.85), s.seed + 7, inner=inner)]
        if ng['tilt'] > 4:
            nos = [(-w * 0.17, h * 0.26), (w * 0.17, h * 0.26)] if abs(s.turn) < 0.3 else [(s.f * w * 0.12, h * 0.27), (-s.f * w * 0.18, h * 0.29)]
            for k, (dx, dy) in enumerate(nos):
                q = rot((cx + dx, cy + dy), ang, (cx, cy))
                rr = w * (0.085 if k == 0 else 0.065)
                out.append(f'<ellipse cx="{f1(q[0])}" cy="{f1(q[1])}" rx="{f1(rr)}" ry="{f1(rr * 0.62)}" transform="rotate({f1(ang)} {f1(q[0])} {f1(q[1])})" fill="{MOUTH}"/>')
        if e['bead']:
            tip = rot((cx + s.f * w * 0.10, cy + h / 2 + 2), ang, (cx, cy))
            dp = drop_pts(tip[0], tip[1] + h * 0.42, h * 0.38)
            out.append(inked(dp, CYAN, (3, 4.5), 5, bias=0.5, off=(2, 2)))
            out.append(f'<ellipse cx="{f1(tip[0] - h * 0.06)}" cy="{f1(tip[1] + h * 0.36)}" rx="{f1(h * 0.05)}" ry="{f1(h * 0.08)}" fill="{WHITE}"/>')
        return ''.join(out)

    def draw_brows(s, e, geoms):
        out = []
        D = s.D
        gap = (s.p['brow_gap'] if e['brow_gap'] is None else e['brow_gap']) * D
        th = s.p['brow_th'] * D
        for side, i in ((-1, 0), (1, 1)):
            g = geoms[i]
            L = s.p['brow_len'] * D * (0.80 if g['far'] else 1)
            cxb = g['bc'][0] + side * e['brow_dx'][i] * D
            basey = g['lidtop'][1] if (e['brow_follow'] and 'lidtop' in g) else g['top'][1]
            cyb = basey - gap - e['brow_raise'][i] * D
            ang = -side * e['brow_tilt'][i]
            arch = e['brow_arch'][i]
            a = (cxb - side * L / 2, cyb); b = (cxb + side * L / 2, cyb); cc = (cxb, cyb - arch * L * 2)
            pts = xf(qbez(a, cc, b, 30), ang=ang, c=(cxb, cyb))
            lim = s.fx + side * 4
            over = max(0.0, max((lim - q[0]) * side for q in pts))
            pts = [(q[0] + side * over, q[1]) for q in pts]
            band_in = th / 2 + 5; band_out = th / 2 + 8
            dn = 0.0; upv = 0.0; hit = False
            for q in pts:
                ty = s.top_y_at(q[0])
                if ty - band_out < q[1] < ty + band_in:
                    hit = True
                dn = max(dn, ty + band_in - q[1])
                upv = max(upv, q[1] - (ty - band_out))
            clip = False
            if hit:
                if e['brow_raise'][i] >= 0.05 and dn > 0.12 * D:
                    shift = -upv                                     # a raised brow floats clear of the skull
                else:
                    low = max(q[1] for q in pts) + dn + th / 2
                    if low > g['top'][1] - 0.012 * D:                # pushing it fully in would sit on the eye:
                        shift = (g['top'][1] - 0.014 * D - th / 2) - max(q[1] for q in pts)
                        clip = True                                  # tuck it just above the eye, wrap it round the rim
                    else:
                        shift = dn
                pts = [(q[0], q[1] + shift) for q in pts]
            svg = stroke(pts, th, taper=(0.18, 0.4), wmin=0.3)
            out.append(clipped(s.head, svg) if clip else svg)
        return ''.join(out)

    def draw_marks(s, e):
        out = []
        D = s.D
        for mk in e['marks']:
            kind = mk[0]
            if kind == 'sweat':
                x, y, size, ang = s.cx + mk[1] * D, s.cy + mk[2] * D, mk[3] * D, mk[4]
                dp = drop_pts(x, y, size, ang)
                out.append(inked(dp, CYAN, (3, 4.5), 9, bias=0.5, off=(2, 2)))
                hl = rot((x - size * 0.15, y - size * 0.05), ang, (x, y))
                out.append(f'<circle cx="{f1(hl[0])}" cy="{f1(hl[1])}" r="{f1(size * 0.12)}" fill="{WHITE}"/>')
            elif kind == 'emanata':
                cx, cy, R = s.cx, s.cy - 0.1 * D, mk[1] * D
                for a in (-150, -128, -52, -30):
                    ar = math.radians(a)
                    p0 = (cx + math.cos(ar) * R, cy + math.sin(ar) * R)
                    p1 = (cx + math.cos(ar) * (R + 0.14 * D), cy + math.sin(ar) * (R + 0.14 * D))
                    out.append(stroke([p0, p1], 0.035 * D, taper=(0.1, 0.6)))
        return ''.join(out)

    def draw(s, E):
        e = dict(FDEF); e.update(E)
        D = s.D
        out = [f'<g transform="rotate({f1(e["tilt"])} {f1(s.cx)} {f1(s.cy)})">']
        if not s.p['ear_front']:
            for side in s.ear_sides():
                out.append(s.ear_svg(side))
        inner = crescent(s.head, s.p['shade'], -0.11 * D, -0.085 * D, s.p['shade_op'])
        if s.p['jaw']:
            y0 = s.cy + (s.p['jaw_from'] - 0.5) * D
            pitch = max(7.0, 0.034 * D)
            fade = ht_fade(s.cx - s.R - 12, y0, s.cx + s.R + 12, s.cy + s.R + 0.06 * D, s.p['jaw'], pitch=pitch,
                           rmax=pitch * 0.44, rmin=pitch * 0.06, power=0.9)
            inner += clipped(s.head, fade, OFF)
        if s.p['cheeks'] or e['cheek_flush']:
            inner += s.cheeks_svg(e)
        out.append(inked(s.head, s.skin, s.lw(), s.seed, inner=inner))
        if s.p['fringe']:
            out.append(s.draw_fringe(e))
        if s.p['ear_front']:
            for side in s.ear_sides():
                out.append(s.ear_svg(side))
        if s.p['comb']:
            out.append(s.draw_comb(e))
        if s.p['sideburn']:
            out.append(s.draw_sideburns())
        if s.p['hair'] == 'flicks':
            out.append(s.draw_flicks(e))
        out.append(s.draw_jowl_fold(e))
        out.append(s.draw_mouth(e))
        geoms = []
        for side in (-1, 1):
            svg, g = s.draw_eye(side, e)
            out.append(svg); geoms.append(g)
        out.append(s.draw_nose(e))
        out.append(s.draw_brows(e, geoms))
        out.append(s.draw_marks(e))
        out.append('</g>')
        s.last_geoms = geoms
        return ''.join(out)

    def top_with_hair(s, e=None):
        """lowest y reached by the crown flicks / comb (for exact lineup sizing)."""
        e2 = dict(FDEF); e2.update(e or {})
        ys = [s.cy - s.R]
        if s.p['hair'] == 'flicks':
            up = e2['hair_up']; f = s.f
            hx = s.cx - s.turn * 0.12 * s.D
            for dx, ln, a in [(-0.075, 0.125, 18), (0.0, 0.15, 30), (0.075, 0.12, 42)]:
                x = hx + dx * s.D * f
                y = s.top_y_at(x) + 0.035 * s.D
                a2 = f * a * (1 - up) + (dx * 120 * up)
                L = ln * s.D * (1 + 0.35 * up) * s.p['hair_k']
                t = rot((0, -L), a2)
                ys.append(rot((x + t[0], y + t[1]), e2['tilt'], (s.cx, s.cy))[1])
        return min(ys)


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


# ======================================================================== cast
def bix_head(cx, cy, D=270, turn=0.7):
    return RoundFace(cx, cy, D, SKIN_B, turn, dict(kind='button', w=0.28, h=0.21, y=0.585, fill=NOSE_B, shade='htR'),
                     seed=11, jaw=shade_hex(SKIN_B, 0.32), shade='htC', shade_op=0.62)


def gus_head(cx, cy, D=290, turn=-0.8):
    return RoundFace(cx, cy, D, SKIN_G, turn, dict(kind='potato', w=0.50, h=0.38, y=0.62, fill=NOSE_G, shade='htR'),
                     seed=21, eye_w=0.20, eye_h=0.285, eye_tip=0.50, hair=None, fringe=True, jowls=0.075,
                     ear_front=True, sideburn=False, kx_eye=0.30, kx_nose=0.44, far_sq=0.45, nose_wk=0.08,
                     cheeks=True, shade='htR', shade_op=0.42, jaw=shade_hex(SKIN_G, 0.22), jaw_from=0.72,
                     brow_th=0.042, mouth_k=1.25)


def wit_head(cx, cy, D=230, turn=-0.5):
    return RoundFace(cx, cy, D, SKIN_W, turn, dict(kind='button', w=0.27, h=0.20, y=0.60, fill=NOSE_W, shade='htC'),
                     seed=31, eye_w=0.22, eye_h=0.32, hair=None, comb=True, brow_th=0.047, lid_w=0.047, ear=(0.075, 0.09, 0.065), sideburn=False,
                     shade='htC', shade_op=0.5, kx_eye=0.30, kx_nose=0.45)


def bix_body(D, facing):
    return Body(D, facing, plate=CYAN, glove=WHITE, shoe='brogue', seed=400)


def gus_body(D, facing):
    return Body(D, facing, plate=MUSTARD, glove=SKIN_G, shoe='loafer', seed=500, knuckle=True,
                L=dict(spine=0.88, thigh=0.75, shin=0.69, neck_vis=0.06, neck_x=0.12, neck_w=0.20, up=0.66, fore=0.69))


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


BIX_SCENE_E = dict(tilt=-7, lid=(0.45, 0.45), lid_tilt=(-6, -6), gaze=(0.85, 0.55), pupil_vis=0.62,
                   brow_raise=(0.0, 0.10), brow_arch=(0.04, 0.22), brow_tilt=(3, -8), nose_tilt=10, mouth='curl')
GUS_SCENE_E = dict(tilt=-7, eye_scale=(1.06, 1.06), eye_rot=(6, -4), gaze_lr=((0.6, 0.75), (-0.85, 0.6)), pupil_r=0.027,
                   brow_raise=(0.02, 0.04), brow_arch=(0.18, 0.18), brow_tilt=(-6, -14), flush=True, mouth='o',
                   cheek_flush=True)
WIT_SCENE_E = dict(gaze=(-1, 0.35), lid=(0.5, 0.5), pupil_vis=0.8, brow_gap=0.03, brow_raise=(0.03, 0.0),
                   brow_arch=(0.12, 0.02), brow_tilt=(-6, 4))


def bix_scene(head=(350, 675), D=270, FL=1540):
    E = dict(BIX_SCENE_E)
    fn = lambda x, y: bix_head(x, y, D, 0.62)
    b = bix_body(D, 1)
    p = dict(neck=8, tilt=-7, spine=13, bow=0.035, yoke_k=1.07,
             fstr=199, fhand=199, fgrip='mitt', fthumb=-1, fthumb_at=0.66, fthumb_sp=46,
             nup=-42, nlo=78, nlo_k=0.42, ngrip='hidden',
             nFr=(0.06, 1.49), ntoe=90, nkbend=-1,
             fFr=(-0.46, 1.42), ftoe=-62, fkbend=-1)
    f, J = place(fn, b, p, head[0], FL, 'n')
    return f, b, p, J, E


def gus_scene(head=(906, 752), D=290, FL=1540, target=None):
    E = dict(GUS_SCENE_E)
    fn = lambda x, y: gus_head(x, y, D, -0.80)
    b = gus_body(D, -1)
    p = dict(neck=20, tilt=-7, spine=4, bow=0.08, yoke_k=1.0, sh_nk=0.90, sh_fk=0.78,
             nstr=-84, ngrip='mitt', nthumb=1, nthumb_at=0.70, nthumb_sp=62,
             fup=-3, flo=-12, fgrip='mitt', fthumb=-1,
             nFr=(-0.74, 1.19), ntoe=-90, nkbend=1,
             fFr=(0.10, 1.26), ftoe=-42, fkbend=1)
    f, J = place(fn, b, p, head[0], FL, 'n')
    if target is not None:                                    # aim the locked-straight arm at the doughnut spot
        for _ in range(3):
            v = (target[0] - J['Sn'][0], target[1] - J['Sn'][1])
            p['nstr'] = ang_of(v)
            f, J = place(fn, b, p, head[0], FL, 'n')
    return f, b, p, J, E


def build_scene(sil=False):
    W, H = 1080, 1920
    FL = 1540
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{common_defs()}{black_defs()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    if not sil:
        out.append(floor2())
        gsvg, glass = window2()
        out.append(gsvg)
        # witness behind the glass: crown, eyes and the top of his nose over a newspaper of dot rows
        wit = wit_head(960, 510, 230, -0.55)
        wsvg = wit.draw(WIT_SCENE_E) + newspaper(852, 538, 1072, 662)
        wb = Body(230, -1, plate=CYAN, glove=SKIN_W, seed=600)
        for k, (x, y, a, sd) in enumerate(((868, 582, 180, 1), (1056, 586, 180, -1))):
            wsvg += inked(wb.mitten_pts((x, y), a, 1.0), SKIN_W, (4, 6), 610 + k)
            wsvg += inked(wb.thumb_pts((x, y), a, sd, 1.0, 0.62, 78), SKIN_W, (3, 4.5), 620 + k)
        out.append(clipped(glass, wsvg))
        out.append(window_frame())
        out.append(awning2())
        out.append(back_table(150, 1150, 0.85))
        out.append(shrub_at(-6, 790, 1.0))
    # ---- BIX: saucer balanced on the tip of the far glove, fully overhead
    bix, bb, bp, bJ, bE = bix_scene(FL=FL)
    S = bix.D
    cs = 0.45 * S / 172
    tipd = DIR(bp['fhand'])
    cup_b = padd(bJ['fW'], tipd, 0.205 * S)
    # ---- GUS: locked-straight doughnut arm aimed at the spot in front of Bix's chest
    dn_target = (478, 960)
    gus, gb, gp, gJ, gE = gus_scene(target=dn_target, FL=FL)
    G = gus.D
    gE['marks'] = [('sweat', -0.40, -0.55, 0.11, -30)]
    hdg = DIR(gp['nstr'])
    ds = 0.30 * G / 160
    dn_c = padd(padd(gJ['nW'], hdg, 0.16 * G), (0, 1), 0.035 * G)
    ghost_b = (dn_c[0] - 4, dn_c[1] + 50 * ds + 138 * cs)     # ghost saucer bottom: its rim just under the doughnut
    if not sil:
        out.append(ht_ellipse((bJ['nF'][0] + bJ['fF'][0]) / 2 + 20, FL + 8, 170, 16, INK, 10, 3.4))
        out.append(ht_ellipse((gJ['nF'][0] + gJ['fF'][0]) / 2, FL + 8, 190, 16, INK, 10, 3.4))
        trail = cup_ghost(ghost_b[0], ghost_b[1], cs, 0.65)
        for k, dx in enumerate((-0.13, -0.015, 0.10)):            # three rising speed lines over the doughnut
            x = dn_c[0] + dx * S
            y0 = dn_c[1] - 0.20 * S - 0.02 * S * (k == 1)
            trail += stroke([(x, y0), (x - 0.01 * S, y0 - 0.34 * S - 0.05 * S * (k == 1))], 6, taper=(0.85, 0.1), wmin=0.2)
        # dotted path over Bix's crown to where the cup is now
        path = cbez((bix.cx + 0.66 * S, bix.cy - 0.12 * S), (bix.cx + 0.66 * S, bix.cy - 0.92 * S),
                    (bix.cx - 0.05 * S, bix.cy - 1.10 * S), (cup_b[0] + 0.42 * S, cup_b[1] - 0.30 * S), 60)
        trail += dotted(path, S, 0.75)
        out.append(trail)
    # GUS figure
    tie = necktie(padd(gJ['Nb'], gJ['sd'], 0.01 * G), -40, 0.55 * G, 0.22 * G, 520, G, bend=0.10)
    col = collar_points(gJ, G, MUSTARD, 530, -1, open_=0.03, drop=0.15)
    dn = held_doughnut(dn_c[0], dn_c[1], ds, -10)
    gspeed = ''.join(stroke([(gJ['H'][0] + 0.10 * G + 14 * k, gJ['H'][1] - 0.66 * G + 0.15 * G * k), (gJ['H'][0] + 0.34 * G + 14 * k, gJ['H'][1] - 0.66 * G + 0.15 * G * k)], 6, taper=(0.1, 0.8)) for k in range(3))
    gsil = figure(gus, gE, gb, gJ, ['shadow', 'halo', 'f_leg', 'f_arm', 'f_hand', 'f_thumb', 'spine', 'yoke', 'n_leg', 'hip',
                                    'neck', 'collar', 'head', 'n_arm', 'n_hand', 'prop', 'n_thumb', 'marks'],
                  hip=belt(gJ['H'], gp['spine'], G, 540), collar=col + tie, prop=dn,
                  marks='', halo='' if sil else gb.halo(gJ, CREAM, 0.4))
    # BIX figure
    ap = apron(bJ['H'], bp['spine'], S, 5, 20, 430, 1, length=1.05, wb=0.30, flutter=0.02, tails=-52)
    bt = bow_tie(padd(bJ['Nb'], bJ['sd'], 0.03 * S), -bp['spine'] * 0.5, S, 440, squash=0.88)
    bc = collar_points(bJ, S, WHITE, 450, 1)
    cp = cup(cup_b[0], cup_b[1], cs, 0, bulge=False) + steam_small(cup_b[0], cup_b[1] - 138 * cs, cs * 0.62)
    bsil = figure(bix, bE, bb, bJ, ['shadow', 'halo', 'n_arm', 'f_leg', 'f_arm', 'f_hand', 'spine', 'yoke', 'n_leg', 'hip',
                                    'neck', 'collar', 'head', 'prop', 'f_thumb', 'marks'],
                  hip=ap, collar=bc + bt, prop=cp, halo='' if sil else bb.halo(bJ, CREAM, 0.4))
    if sil:
        out.append(f'<g filter="url(#blk)">{gsil}</g><g filter="url(#blk)">{bsil}</g>')
    else:
        out.append(gsil); out.append(bsil)
        out.append(grain(W, H, 0.12))
    out.append('</svg>')
    xs_g = [q[0] for k in ('nshoe', 'fshoe') for q in gJ[k]] + [gJ['fW'][0], gus.cx + gus.R * 1.1]
    info = dict(bix=(bix.cx, bix.cy, bix.D), gus=(gus.cx, gus.cy, gus.D), cup=cup_b, dn=dn_c, ghost=ghost_b,
                bix_H=(max(q[1] for q in bJ['nshoe']) - (bix.cy - bix.R)) / bix.D,
                gus_H=(max(q[1] for q in gJ['nshoe']) - (gus.cy - gus.R)) / gus.D,
                bix_clear=bb.arm_clearance(bJ, bix, 'f'), saucer_above=(bix.cy - bix.R - cup_b[1]) / bix.D,
                bix_off=(bix.cx - bJ['H'][0]) / bix.D, gus_off=(gus.cx - gJ['H'][0]) / gus.D,
                gfeet=(gJ['nF'][0], gJ['fF'][0]), bfeet=(bJ['nF'][0], bJ['fF'][0]), gS=gJ['Sn'], gstr=gp['nstr'],
                gus_maxx=max(xs_g), saucer_x=(cup_b[0] - 124 * cs, cup_b[0] + 124 * cs))
    return ''.join(out), info


# ======================================================================== POSES SHEET
E_READY = dict(tilt=-2, gaze=(0.15, 0.15))
E_SMUG = dict(tilt=4, lid=(0.30, 0.30), lid_tilt=(-5, -5), gaze=(-0.5, 0.15), pupil_vis=0.55,
              brow_raise=(0.10, 0.0), brow_arch=(0.22, 0.04), brow_tilt=(-8, 3), nose_tilt=10, mouth='curl')
E_PANIC = dict(tilt=-3, eye_scale=(1.2, 1.2), eye_push=0.01, pupil_r=0.026, gaze_lr=((0.35, 0.95), (-0.75, 0.7)),
               brow_raise=(0.06, 0.06), brow_arch=(0.14, 0.14), brow_tilt=(-22, -22), hair_up=1.0, mouth='wavy')


def pose_ready(D, x, FL, facing=1, turn=0.45, E=None, build=True):
    E = dict(E or E_READY)
    fn = lambda cx, cy: bix_head(cx, cy, D, turn * facing)
    b = bix_body(D, facing)
    p = dict(neck=9, tilt=-2 * facing, spine=2 * facing, bow=0.04,
             nWr=(0.40 * facing, -0.03), nbend=facing, nhand=90 * facing, ngrip='flat', nthumb=-facing, nthumb_at=0.52, nthumb_sp=40,
             fup=-26 * facing, flo=72 * facing, flo_k=0.42, fgrip='hidden',
             nFr=(0.05 * facing, 1.47), ntoe=96 * facing, nkbend=-facing,
             fFr=(-0.02 * facing, 1.47), ftoe=-104 * facing, fkbend=-facing)
    f, J = place(fn, b, p, x, FL, 'n')
    s = 0.45 * D / 172
    palm = padd(J['nW'], DIR(p['nhand']), 0.10 * D)
    cb = (palm[0], palm[1] - 0.04 * D)
    if not build:
        return f, J
    ap = apron(J['H'], p['spine'], D, 2 * facing, 20, 431, facing, length=1.05, wb=0.30, tails=-14 * facing)
    bt = bow_tie(padd(J['Nb'], J['sd'], 0.03 * D), 0, D, 441, squash=0.92)
    col = collar_points(J, D, WHITE, 451, facing)
    c = cup(cb[0], cb[1], s, 0) + steam_small(cb[0], cb[1] - 138 * s, s * 0.55)
    sh = ht_ellipse(J['nF'][0] + 0.05 * D * facing, FL + 6, 0.48 * D, 10, INK, 9, 3.0)
    svg = figure(f, E, b, J, ['shadow', 'f_arm', 'f_leg', 'spine', 'yoke', 'n_leg', 'hip', 'neck', 'collar', 'head',
                              'n_arm', 'n_hand', 'prop', 'n_thumb'], shadow=sh, hip=ap, collar=col + bt, prop=c)
    return svg, f, J


def pose_skylift(D, x, FL, build=True):
    E = dict(E_SMUG)
    fn = lambda cx, cy: bix_head(cx, cy, D, -0.42)
    b = bix_body(D, -1)
    p = dict(neck=7, tilt=4, spine=4, bow=0.03,
             fstr=154, fhand=154, fgrip='mitt', fthumb=1, fthumb_at=0.66, fthumb_sp=46,
             nstr=-45, nhand=-45, ngrip='mitt', nthumb=1,
             fFr=(0.06, 1.49), ftoe=-30, fkbend=1,
             nFr=(-0.3, 0.9), ntoe=18, nkbend=1)
    f, J = place(fn, b, p, x, FL, 'f')
    for _ in range(2):                     # passé: lifted foot rests against the standing knee
        p.pop('nFr', None)
        p['nFt'] = padd(J['fK'], (-0.06 * D, 0.03 * D))
        f, J = place(fn, b, p, x, FL, 'f')
        p['nFt'] = padd(J['fK'], (-0.06 * D, 0.03 * D))
    s = 0.45 * D / 172
    cb = padd(J['fW'], DIR(p['fhand']), 0.205 * D)
    if not build:
        return f, J, cb
    ap = apron(J['H'], p['spine'], D, 30, 26, 432, -1, length=1.02, wb=0.30, flutter=0.04, tails=-60)
    bt = bow_tie(padd(J['Nb'], J['sd'], 0.03 * D), -p['spine'] * 0.5, D, 442, squash=0.86)
    col = collar_points(J, D, WHITE, 452, -1)
    c = cup(cb[0], cb[1], s, 0) + steam_small(cb[0], cb[1] - 138 * s, s * 0.55)
    sh = ht_ellipse(J['fF'][0], FL + 6, 0.40 * D, 10, INK, 9, 3.0)
    svg = figure(f, E, b, J, ['shadow', 'f_leg', 'f_arm', 'f_hand', 'spine', 'yoke', 'hip', 'n_leg', 'neck', 'collar',
                              'head', 'n_arm', 'n_hand', 'prop', 'f_thumb', 'n_thumb'],
                 shadow=sh, hip=ap, collar=col + bt, prop=c)
    return svg, f, J, cb


def pose_panic(D, x, FL, build=True):
    E = dict(E_PANIC)
    fn = lambda cx, cy: bix_head(cx, cy, D, -0.2)
    b = bix_body(D, -1)
    p = dict(neck=10, tilt=-3, spine=5, bow=-0.06,
             nWr=(-0.26, 0.34), nbend=-1, nhand=-92, ngrip='flat', nthumb=1, nthumb_at=0.5, nthumb_sp=38,
             fWr=(-0.50, 0.30), fbend=-1, fhand=-88, fgrip='flat', fthumb=1, fthumb_at=0.5, fthumb_sp=38,
             nFr=(-0.50, 1.10), ntoe=84, nkbend=-1,
             fFr=(0.50, 1.10), ftoe=-84, fkbend=1)
    f, J = place(fn, b, p, x, FL, 'n')
    s = 0.45 * D / 172
    mid = lerp(J['nW'], J['fW'], 0.5)
    cb = (mid[0] - 0.12 * D, mid[1] - 0.05 * D)
    if not build:
        return f, J, cb
    E['marks'] = [('sweat', -0.62, -0.30, 0.11, -35), ('sweat', 0.64, -0.40, 0.12, 40)]
    ap = apron(J['H'], p['spine'], D, 4, 26, 433, -1, length=0.46, wb=0.30, tails=40)
    bt = bow_tie(padd(J['Nb'], J['sd'], 0.03 * D), -p['spine'] * 0.6, D, 443, squash=0.94)
    col = collar_points(J, D, WHITE, 453, -1)
    c = cup(cb[0], cb[1], s, -12, drop_up=26)
    sh = ht_ellipse((J['nF'][0] + J['fF'][0]) / 2, FL + 6, 0.62 * D, 10, INK, 9, 3.0)
    svg = figure(f, E, b, J, ['shadow', 'f_leg', 'n_leg', 'spine', 'yoke', 'hip', 'f_arm', 'neck', 'collar', 'head',
                              'n_arm', 'f_hand', 'n_hand', 'prop', 'f_thumb', 'n_thumb'],
                 shadow=sh, hip=ap, collar=col + bt, prop=c)
    return svg, f, J, cb


def build_poses(sil=False):
    W = H = 1080
    FL = 990
    D = 200
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{common_defs()}{black_defs()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    if not sil:
        out.append(ht_fade(0, 990, 1080, 1080, CYAN, pitch=10, rmax=3.0, rmin=0.3, power=1.0))
        out.append(stroke([(20, 990), (1060, 990)], 4, color=CYAN, taper=(0.02, 0.02)))
    s1, f1_, J1 = pose_ready(D, 190, FL)
    s2, f2_, J2, cb2 = pose_skylift(D, 540, FL)
    s3, f3_, J3, cb3 = pose_panic(D, 880, FL)
    for sv in (s1, s2, s3):
        out.append(f'<g filter="url(#blk)">{sv}</g>' if sil else sv)
    if not sil:
        out.append(grain(W, H, 0.12))
    out.append('</svg>')
    b = bix_body(D, 1)
    info = dict(heads=[(round(f.cx), round(f.cy)) for f in (f1_, f2_, f3_)],
                H1=(max(q[1] for q in J1['nshoe']) - (f1_.cy - f1_.R)) / D,
                clear2=b.arm_clearance(J2, f2_, 'f'), saucer2=(f2_.cy - f2_.R - cb2[1]) / D,
                off=[round((f.cx - J['H'][0]) / D, 2) for f, J in ((f1_, J1), (f2_, J2), (f3_, J3))],
                feet3=(J3['nF'][0] - J3['fF'][0]) / D)
    return ''.join(out), info


# ======================================================================== LINEUP (540 x 1080, 900 px tall)
def build_lineup():
    """hero alone, relaxed ready stance, 3/4 toward the viewer's left; exactly 900 px from soles to hair tip."""
    W, H = 540, 1080
    FLOOR_Y = 1010
    D = 234.0; fl = FLOOR_Y
    E = dict(tilt=2, gaze=(-0.25, 0.1), brow_raise=(0.03, 0.0), brow_arch=(0.14, 0.08), lid=(0.12, 0.12))
    for _ in range(6):
        svg, f, J = pose_ready(D, 300, fl, facing=-1, turn=0.45, E=E)
        sole = max(max(q[1] for q in J['nshoe']), max(q[1] for q in J['fshoe']))
        fl += FLOOR_Y - sole                     # the lower of the two shoes sits on the line
        D = D * 900.0 / (sole - f.top_with_hair(E))
    svg, f, J = pose_ready(D, 300, fl, facing=-1, turn=0.45, E=E)
    sole = max(max(q[1] for q in J['nshoe']), max(q[1] for q in J['fshoe']))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{common_defs()}</defs>', f'<rect width="{W}" height="{H}" fill="#EDEAE4"/>', svg, '</svg>']
    return ''.join(out), dict(D=D, sole=sole, top=f.top_with_hair(E), height=sole - f.top_with_hair(E), head=(f.cx, f.cy))


if __name__ == '__main__':
    import json, sys
    svg, info = build_scene()
    open(os.path.join(HERE, 'scene.svg'), 'w').write(svg)
    open(os.path.join(HERE, 'scene_sil.svg'), 'w').write(build_scene(sil=True)[0])
    svg2, info2 = build_poses()
    open(os.path.join(HERE, 'poses.svg'), 'w').write(svg2)
    open(os.path.join(HERE, 'poses_sil.svg'), 'w').write(build_poses(sil=True)[0])
    svg3, info3 = build_lineup()
    open(os.path.join(HERE, 'lineup.svg'), 'w').write(svg3)
    r = lambda v: [round(c, 2) for c in v] if isinstance(v, (tuple, list)) else round(v, 3)
    print('scene', {k: r(v) for k, v in info.items()})
    print('poses', info2)
    print('lineup', {k: r(v) for k, v in info3.items()})
