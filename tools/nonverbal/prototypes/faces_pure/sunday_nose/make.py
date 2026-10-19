#!/usr/bin/env python3
"""Sunday Nose / 日曜版の鼻 -- BIG-EYE round heads on stick bodies.

ONE face rig (BigFace: true-circle skull; a fixed eye-white shape per character -- Bix teardrop, Gus droopy --
resting on the nose top with a 0.03 D overlap; expression only from the upper-lid mask + heavy lid line, an
optional lower lid, solid pupils that clip against the rim and converge on a look target, brows, and a mouth
that stays hidden under the nose / mustache until a take) and
ONE stick-body rig (Body: skin neck stub + short shoulder bar + slightly curved spine, single-stroke ink limbs with
round caps, small skin mitten hands, small plain shoes).  PURE STICK BODIES: no torso surface, no clothing.  The
only body-side extra is Bix's small bow tie at the throat.  Every limb is the same INK; no colour plate under limbs.
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
SHOE_K = 0.86   # pure-stick pass: smaller, plainer shoes
SHOE = [(u * SHOE_K, v * SHOE_K) for u, v in
        [(-0.06, -0.045), (-0.10, -0.005), (-0.095, 0.07), (0.05, 0.07), (0.185, 0.07), (0.232, 0.045),
         (0.228, 0.002), (0.17, -0.032), (0.06, -0.058)]]
LIMB_W = (0.056, 0.050)    # limb stroke width, shoulder/hip end -> wrist/ankle end, in D
SPINE_W = (0.062, 0.056)   # spine stroke width, neck end -> hip end, in D


class Body:
    """neck stub + collar anchor + tapered spine + hip prop, limbs as tapered ink over an off-register plate."""

    def __init__(s, D, facing, plate, glove, shoe='brogue', seed=400, L=None, knuckle=False, glove_skin=False):
        s.D, s.f, s.plate, s.glove, s.shoe_kind, s.seed, s.knuckle = D, facing, plate, glove, shoe, seed, knuckle
        s.L = dict(neck_x=0.10, neck_top=0.30, neck_vis=0.12, neck_w=0.18, yoke=0.065, sh=0.27, sh_drop=0.035,
                   spine=0.97, up=0.68, fore=0.70, thigh=0.78, shin=0.72, hand=0.20, hand_w=0.13, sole=0.07)
        s.L.update(L or {})
        # pure-stick line weights: limbs a little heavier than the head outline (0.021-0.035 D), never under 12.5 px
        s.wl = (max(LIMB_W[0] * D, 13.0), max(LIMB_W[1] * D, 12.5))
        s.ws = (max(SPINE_W[0] * D, s.wl[0] + 1.0), max(SPINE_W[1] * D, s.wl[1] + 0.5))
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
        """one single ink stroke per bone, round caps; the two caps overlap into a round elbow / knee join."""
        w0, w2 = s.wl; w1 = (w0 + w2) / 2
        a = ink_poly([p0, p1], w0, w1, swell=0.05, seed=seed, wmin=12.0)
        b = ink_poly([p1, p2], w1, w2, swell=0.05, seed=seed + 1, wmin=12.0)
        return f'<path d="{P(a)}" fill="{INK}"/><path d="{P(b)}" fill="{INK}"/>'

    def spine_svg(s, J):
        pts = J['spine_pts']
        a = ink_poly(pts, s.ws[0], s.ws[1], swell=0.04, seed=s.seed + 5, wmin=12.0)
        return f'<path d="{P(a)}" fill="{INK}"/>'

    def yoke_svg(s, J):
        """the tiny shoulder bar (<= 0.6 D wide) where the neck meets the spine."""
        Sf, Sn, Y, sd = J['Sf'], J['Sn'], J['Y'], J['sd']
        pts = qbez(Sf, padd(Y, sd, -0.025 * s.D), Sn, 16)
        a = ink_poly(pts, s.wl[0], s.wl[0], swell=0.0, seed=s.seed + 6, wmin=12.0)
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
        K = SHOE_K
        if s.shoe_kind == 'brogue':
            # plain solid-ink shoe with one shine stroke (no broguing, no sole line, no colour plate)
            out.append(f'<path d="{P(pts)}" fill="{INK}"/>')
            out.append(stroke(qbez(Wf(0.10 * K, -0.033 * K), Wf(0.165 * K, -0.024 * K), Wf(0.198 * K, -0.002 * K), 10),
                              0.019 * D, color=WHITE, taper=(0.3, 0.3)))
        else:
            # plain brown loafer, no sock
            out.append(inked(pts, LOAFER, (0.013 * D, 0.02 * D), s.seed + 61))
            out.append(stroke(qbez(Wf(0.16 * K, -0.02 * K), Wf(0.20 * K, -0.012 * K), Wf(0.215 * K, 0.012 * K), 8), 0.013 * D,
                              color='#C79A6B', taper=(0.3, 0.3)))
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



# ======================================================================== ANIME-EYE ROUND HEAD RIG
SCLERA = '#FBF6EA'                     # warm off-white sclera (never #FFFFFF)
LIDBAND = '#DCD3C3'                    # lid shadow band over the white
HILITE = '#FFFFFF'                     # catchlights: the ONLY pure white on a face
EYEW = SCLERA
BIX_HAIR = '#2E2420'; BIX_GREY = '#D2CBBD'; BIX_COMB = '#62514A'; BIX_GREY_LN = '#A9A195'
VEST = '#36323B'; SHIRT = '#FBF6EA'
GUS_SKIN = '#EAC6A2'; GUS_GREY = '#D9D3C8'; KNIT = '#E2B93C'
GUS_NOSE = '#D99A84'; GUS_TIP = '#CC7F6A'; RUDDY = '#E0907C'

IRIS_BIX = dict(base='#17707A', sh='#0B4650', li='#43A7A6', ring='#07323A', pupil='#041A1E')
IRIS_GUS = dict(base='#B9853F', sh='#86592A', li='#E2B97E', ring='#5E3E1A', pupil='#22160A')
IRIS_CAMEO = dict(base='#7A5233', sh='#7A5233', li='#7A5233', ring='#4A311E', pupil='#24170D')


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


def vcross(poly, x):
    """(top, bottom) where the vertical line at x crosses the polygon, or None."""
    ys = []
    n = len(poly)
    for k in range(n):
        a = poly[k]; b = poly[(k + 1) % n]
        if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            ys.append(a[1] + (b[1] - a[1]) * t)
    if len(ys) < 2:
        return None
    return min(ys), max(ys)


def hcross(poly, y):
    xs = []
    n = len(poly)
    for k in range(n):
        a = poly[k]; b = poly[(k + 1) % n]
        if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]:
            t = (y - a[1]) / (b[1] - a[1])
            xs.append(a[0] + (b[0] - a[0]) * t)
    if len(xs) < 2:
        return None
    return min(xs), max(xs)


_SHAPES = {}


def eye_shape(kind, W, H):
    """eye FOOTPRINT (fully opened eye incl. the upper lash line) in local px:
    +x = OUTWARD (away from the nose), y down, origin = bbox centre."""
    key = (kind, round(W, 2), round(H, 2))
    if key in _SHAPES:
        return _SHAPES[key]
    if kind == 'shizuku':           # Bix: round bulb at the bottom, rounded point up and IN toward the brow
        ang = math.radians(26)
        L = 1.50
        tip = (-L * math.sin(ang), -L * math.cos(ang))
        raw = hull(ellipse_pts(0, 0, 1, 1, 180) + ellipse_pts(tip[0], tip[1], 0.20, 0.20, 30))
    elif kind == 'tareme':          # Gus: big rounded eye, outer corner sags ~20 deg below the inner corner
        ctrl = [(-1.0, -0.22), (-0.82, -0.78), (-0.30, -1.0), (0.32, -0.90), (0.80, -0.42), (1.0, 0.36),
                (0.80, 0.86), (0.16, 1.0), (-0.52, 0.86), (-0.92, 0.40)]
        raw = spline(ctrl, True, 14)
    else:                           # cameo: plain oval
        raw = ellipse_pts(0, 0, 1, 1.25, 100)
    xs = [p[0] for p in raw]; ys = [p[1] for p in raw]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    N = lambda p: ((p[0] - (x0 + x1) / 2) / (x1 - x0) * W, (p[1] - (y0 + y1) / 2) / (y1 - y0) * H)
    loc = resample([N(p) for p in raw], 1.1)
    if area(loc) < 0:
        loc = loc[::-1]
    _SHAPES[key] = loc
    return loc


def eye_opening(loc, W, lidy, lowy, N=220):
    """visible opening = footprint below the upper lid curve and above the lower lid curve (column scan)."""
    def gap_at(x):
        tb = vcross(loc, x)
        if tb is None:
            return None
        return max(lidy(x), tb[0]), min(lowy(x), tb[1]), tb
    cols = []
    for k in range(N + 1):
        x = -W / 2 + W * k / N
        r = gap_at(x)
        cols.append((x, r[0], r[1]) if (r and r[0] < r[1] - 1e-6) else None)
    best, cur = [], []
    for c in cols:
        if c is None:
            if len(cur) > len(best):
                best = cur
            cur = []
        else:
            cur.append(c)
    if len(cur) > len(best):
        best = cur
    if len(best) < 3:
        return None
    step = W / N

    def corner(xin, xout):
        for _ in range(28):
            xm = (xin + xout) / 2
            r = gap_at(xm)
            if r and r[0] < r[1]:
                xin = xm
            else:
                xout = xm
        r = gap_at(xin)
        return (xin, (r[0] + r[1]) / 2)
    c0 = corner(best[0][0], best[0][0] - step)
    c1 = corner(best[-1][0], best[-1][0] + step)
    upper = [c0] + [(x, u) for x, u, l in best] + [c1]
    lower = [c0] + [(x, l) for x, u, l in best] + [c1]
    return dict(upper=upper, lower=lower, poly=upper + lower[::-1][1:-1])


FD = dict(tilt=0, lid=None, lid_tilt=None, lid_bow=None, low=(0.0, 0.0), low_tilt=(0, 0), low_bow=(0.0, 0.0),
          eye_scale=(1.0, 1.0), gaze=(0.0, 0.0), gaze_lr=None, look=None, gaze_k=1.0,
          iris_h=None, free=False, hl='on', wobble=False, closed=(False, False), closed_arc=0.10,
          brow_raise=(0.0, 0.0), brow_tilt=(0.0, 0.0), brow_arch=None, brow_dx=(0.0, 0.0),
          nose_tilt=0, flush=False, tip_flush=False, mouth='none', mouth_dx=0.0, stache=0.0, stache_dy=0.0,
          strand=0.0, marks=(), sweat_k=1.0)


class BigFace:
    """True-circle skull of diameter D; every size is a fraction of D.
    HUGE anime eyes (footprint 0.50 D tall) built back to front the same way for every character:
    sclera, lid shadow band, three-tone iris + limbal ring, pupil, catchlights (pure white), upper lash line,
    lower lid line + creases / bags / crow's-feet, brow.  Lids cut across the big footprint (never a small eye).
    In 3/4 the pair shifts toward the facing side and the far eye compresses to ~62 % width."""

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
        wk = 1 - (1 - C.get('far_w', 0.62)) * min(1.0, abs(s.turn) / 0.35) if far else 1.0
        gap = C['eye_gap'] * D
        loc = eye_shape(C['eye'], W, H)
        ex = s.fx + side * (gap / 2 + wk * W / 2)
        ey = s.top + C['eye_cy'] * D
        return dict(ex=ex, ey=ey, wk=wk, W=W, H=H, far=far, side=side, loc=loc)

    def L2W(s, g, q, sc=1.0):
        """local -> world.  A pop grows the eye outward from its inner edge and upward from its bottom,
        so the gap and the nose contact never change."""
        W, H = g['W'], g['H']
        return (g['ex'] + g['side'] * g['wk'] * (sc * (q[0] + W / 2) - W / 2), g['ey'] + sc * (q[1] - H / 2) + H / 2)

    def nose_local(s):
        """nose outline relative to its centre (world px, before the tilt)."""
        n = s.C['nose']
        if n['kind'] == 'button':
            return ellipse_pts(0, 0, s.nw / 2, s.nh / 2, 100)
        # bell / pear: narrow top, wide drooping bottom; authored facing LEFT, mirrored for right
        ctrl = [(0.0, -1.0), (0.44, -0.88), (0.78, -0.30), (0.98, 0.34), (0.74, 0.90), (0.02, 1.0), (-0.70, 0.98),
                (-1.0, 0.46), (-0.86, -0.22), (-0.46, -0.88)]
        pts = [(x * s.nw / 2, y * s.nh / 2) for x, y in spline(ctrl, True, 14)]
        if s.f > 0:
            pts = [(-x, y) for x, y in pts][::-1]
        return pts

    def solve_nose_y(s):
        """the eyes REST on the nose: pick the nose centre so the footprints overlap its top by nose_over."""
        nl = s.nose_local()
        ov = s.C.get('nose_over', 0.03) * s.D
        best = None
        for sd in (-1, 1):
            g = s.lay[sd]
            pts = [s.L2W(g, q) for q in g['loc']]
            for k in range(41):
                x = s.ncx - s.nw / 2 + s.nw * k / 40
                eb = vcross(pts, x)
                nt = vcross(nl, x - s.ncx)
                if eb is None or nt is None:
                    continue
                v = eb[1] - nt[0] - ov          # nose centre y that gives exactly ov overlap at this x
                best = v if best is None else max(best, v)
        if best is None:
            best = s.top + 0.78 * s.D
        return min(best, s.top + s.C.get('nose_max', 0.80) * s.D)

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
    def eye_geom(s, side, e):
        i = 0 if side < 0 else 1
        g = dict(s.lay[side]); C = s.C; D = s.D
        W, H = g['W'], g['H']; loc = g['loc']
        sc = e['eye_scale'][i]; g['sc'] = sc
        if e['wobble']:
            ph = 0.7 * side
            loc = [(x * (1 + 0.022 * math.sin(7 * math.atan2(y, x) + ph)), y * (1 + 0.022 * math.sin(7 * math.atan2(y, x) + ph)))
                   for x, y in loc]
        T = lambda q: s.L2W(g, q, sc)
        g['T'] = T
        cov = (e['lid'] or (C['lid'], C['lid']))[i]
        tilt = (e['lid_tilt'] or (C['lid_tilt'], C['lid_tilt']))[i]
        bow = (e['lid_bow'] or (C['lid_bow'], C['lid_bow']))[i]
        closed = e['closed'][i] or cov >= 0.97
        tl = math.tan(math.radians(tilt))
        lidy = lambda x: -H / 2 + cov * H + tl * x + bow * H * (2 * x / W) ** 2
        lowc = e['low'][i]; tlo = math.tan(math.radians(e['low_tilt'][i])); bwl = e['low_bow'][i]
        lowy = (lambda x: H / 2 - lowc * H + tlo * x - bwl * H * (1 - min(1.0, (2 * x / W) ** 2))) if (lowc > 0 or bwl > 0) \
            else (lambda x: H)
        g['foot'] = [T(q) for q in loc]
        xs = [q[0] for q in g['foot']]; ys = [q[1] for q in g['foot']]
        g['cx_w'] = (min(xs) + max(xs)) / 2; g['top_w'] = min(ys); g['bot_w'] = max(ys)
        g['core_w'] = poly_centroid(g['foot'])
        g['closed'] = closed
        g['lowc'] = lowc
        oc = max(g['foot'], key=lambda q: side * q[0] - 0.25 * q[1])
        g['outer'] = oc
        if closed:
            arc = e['closed_arc']
            cl = lambda x: -H / 2 + 0.60 * H - arc * H * (1 - (2 * x / W) ** 2)
            xs_l = [-0.47 * W + 0.94 * W * k / 40 for k in range(41)]
            g['closedline'] = [T((x, cl(x))) for x in xs_l]
            g['crease'] = [T((x, cl(x) - 0.06 * D - 0.03 * H * (1 - (2 * x / W) ** 2))) for x in xs_l[4:-4]]
            return g
        op = eye_opening(loc, W, lidy, lowy)
        if op is None:
            g['closed'] = True
            return s.eye_geom(side, dict(e, closed=tuple(True if k == i else e['closed'][k] for k in (0, 1))))
        g['upper'] = [T(q) for q in op['upper']]
        g['lower'] = [T(q) for q in op['lower']]
        g['open'] = [T(q) for q in op['poly']]
        g['lower_loc'] = op['lower']
        # lower-lid skin (smug / kime): footprint area under the raised lower lid
        if lowc > 0 or bwl > 0:
            bot = []
            for x, l in op['lower']:
                tb = vcross(loc, x)
                bot.append((x, tb[1] if tb else l))
            g['lowskin'] = [T(q) for q in op['lower'] + bot[::-1]]
            x0_, x1_ = bot[0][0], bot[-1][0]
            g['bagline'] = [T(q) for q in bot if 0.22 < (q[0] - x0_) / ((x1_ - x0_) or 1) < 0.80]
        # floating crease: the footprint top (socket) where it sits >= 0.045 D above the lash line, middle 80 % only
        ups = op['upper']; x0_, x1_ = ups[0][0], ups[-1][0]
        cr = []
        for x, u in ups:
            t = (x - x0_) / ((x1_ - x0_) or 1)
            if C.get('crease_span', (0.12, 0.88))[0] < t < C.get('crease_span', (0.12, 0.88))[1]:
                tb = vcross(loc, x)
                ft = tb[0] if tb else u
                cr.append((x, max(u - C.get('crease_max', 0.10) * D / sc, min(ft, u - C.get('crease_gap', 0.045) * D / sc))))
        g['crease_up'] = [T(q) for q in cr]
        # ---------------- iris placement
        opw = g['open']
        far = g['far']
        ihf = e['iris_h'] if e['iris_h'] is not None else C['ih'] / C['eye_h']
        ry = ihf * H * sc / 2
        if e['look'] is not None:
            tx, ty = rot(e['look'], -e['tilt'], (s.cx, s.cy))
            c0 = poly_centroid(opw)
            v = (tx - c0[0], ty - c0[1]); m = math.hypot(*v) or 1
            gx, gy = v[0] / m * e['gaze_k'], v[1] / m * e['gaze_k']
        else:
            gx, gy = e['gaze_lr'][i] if e['gaze_lr'] else e['gaze']
        gx = max(-1.0, min(1.0, gx)); gy = max(-1.0, min(1.0, gy))
        narrow = 1 - 0.30 * max(0.0, min(1.0, (abs(gx) - 0.55) / 0.45))
        rx = ry * C.get('iw_k', 0.87) * (0.80 if far else 1.0) * narrow
        cut = C.get('cut', 0.04) * D
        ix0 = poly_centroid(opw)[0]
        iy = poly_centroid(opw)[1]
        ix = ix0
        for _ in range(4):
            he = hcross(opw, iy) or (ix0 - rx, ix0 + rx)
            lo, hi = he[0] + rx * 0.90, he[1] - rx * 0.90
            if lo > hi:
                lo = hi = (he[0] + he[1]) / 2
            base = max(lo, min(hi, ix0))
            ix = base + gx * (hi - base) if gx > 0 else base + gx * (base - lo)
            ve = vcross(opw, ix) or (iy - ry, iy + ry)
            if e['free']:
                iy = ve[0] + (ve[1] - ve[0]) * 0.47
            else:
                iy = ve[0] - cut + ry
            iy += gy * 0.03 * D * sc
        g['iris'] = (ix, iy, rx, ry)
        g['gx'] = gx
        g['lid_y_at_iris'] = (vcross(opw, ix) or (iy - ry, 0))[0]
        return g

    def catchlights(s, g, e):
        D = s.D; out = []
        mode = e['hl']
        if mode == 'off':
            return ''
        ix, iy, rx, ry = g['iris']
        style = s.C['hl']
        k0 = max(0.90, (ry / (s.C['ih'] * D / 2)) ** 0.5)
        yt = g['lid_y_at_iris']
        if style == 'square':
            k = k0 * (1.35 if mode == 'flash' else 1.0)
            a = 0.100 * D * k * (0.92 if g['far'] else 1.0)
            cx_, cy_ = ix - 0.50 * rx, iy - 0.24 * ry
            cy_ = max(cy_, yt + 0.034 * D + a * 0.62)
            sq = xf([(-a / 2, -a / 2), (a / 2, -a / 2), (a / 2, a / 2), (-a / 2, a / 2)], cx_, cy_, 15)
            out.append(f'<path d="{P(sq)}" fill="{HILITE}"/>')
            if mode == 'flash':                 # the 2-frame kime glint: four short ticks round the square
                for ang in (-135, 45):
                    d = DIR(ang)
                    p0 = (cx_ + d[0] * a * 0.85, cy_ + d[1] * a * 0.85); p1 = (cx_ + d[0] * a * 1.25, cy_ + d[1] * a * 1.25)
                    out.append(stroke([p0, p1], 0.014 * D, color=HILITE, taper=(0.2, 0.6)))
            if mode != 'single':
                r2 = 0.022 * D * min(1.0, k0)
                out.append(f'<circle cx="{f1(ix + 0.50 * rx)}" cy="{f1(iy + 0.46 * ry)}" r="{f1(r2)}" fill="{HILITE}"/>')
        elif style == 'wetoval':
            k = k0 * (1.3 if mode == 'tempted' else 1.0)
            a, b = 0.056 * D * k * (0.88 if g['far'] else 1.0), 0.040 * D * k
            cx_, cy_ = ix - 0.40 * rx, iy - 0.22 * ry
            cy_ = max(cy_, yt + 0.034 * D + b)
            out.append(f'<ellipse cx="{f1(cx_)}" cy="{f1(cy_)}" rx="{f1(a)}" ry="{f1(b)}" transform="rotate(-12 {f1(cx_)} {f1(cy_)})" fill="{HILITE}"/>')
            if mode != 'single':
                out.append(f'<circle cx="{f1(ix + 0.46 * rx)}" cy="{f1(iy + 0.44 * ry)}" r="{f1(0.021 * D)}" fill="{HILITE}"/>')
            if mode == 'tempted':
                out.append(f'<circle cx="{f1(ix + 0.14 * rx)}" cy="{f1(iy + 0.64 * ry)}" r="{f1(0.011 * D)}" fill="{HILITE}"/>')
        else:                                   # cameo: a single plain dot
            out.append(f'<circle cx="{f1(ix - 0.36 * rx)}" cy="{f1(max(iy - 0.28 * ry, yt + 0.04 * D))}" r="{f1(0.036 * D)}" fill="{HILITE}"/>')
        return ''.join(out)

    def iris_svg(s, g):
        D = s.D
        ix, iy, rx, ry = g['iris']
        col = s.C['iris']
        out = [f'<ellipse cx="{f1(ix)}" cy="{f1(iy)}" rx="{f1(rx)}" ry="{f1(ry)}" fill="{col["base"]}"/>']
        if not s.C.get('plain_iris'):
            ip = ellipse_pts(ix, iy, rx, ry, 90)
            inner = (f'<ellipse cx="{f1(ix)}" cy="{f1(iy + 0.33 * ry)}" rx="{f1(0.80 * rx)}" ry="{f1(0.60 * ry)}" fill="{col["li"]}"/>'
                     f'<ellipse cx="{f1(ix)}" cy="{f1(iy + 0.02 * ry)}" rx="{f1(0.86 * rx)}" ry="{f1(0.64 * ry)}" fill="{col["base"]}"/>')
            top3 = clip_half(ip, lambda q: q[1] - (iy - ry / 3))
            if len(top3) > 2:
                inner += f'<path d="{P(top3)}" fill="{col["sh"]}"/>'
            out.append(clipped(ip, inner))
        rw = 0.018 * D * (0.85 if g['far'] else 1.0)
        out.append(f'<ellipse cx="{f1(ix)}" cy="{f1(iy)}" rx="{f1(max(1, rx - rw / 2))}" ry="{f1(max(1, ry - rw / 2))}" fill="none" '
                   f'stroke="{col["ring"]}" stroke-width="{f1(rw)}"/>')
        return out

    def draw_eye(s, g, e):
        D = s.D; C = s.C; out = []
        side = g['side']
        lidc = C.get('lid_tone') or shade_hex(s.skin, 0.10)
        lash = C['lash'] * D * (0.92 if g['far'] else 1.0)
        if g['closed']:
            L = g['closedline']
            if (L[-1][0] - L[0][0]) * side < 0:
                L = L[::-1]
            out.append(stroke(L, lash, taper=(0.30, 0.05), wmin=0.35))
            out.append(s.lash_end(L, lash))
            out.append(stroke(g['crease'], C.get('crease_t', 0.016) * D, taper=(0.3, 0.3), wmin=0.3))
            return ''.join(out)
        foot = g['foot']
        out.append(f'<path d="{P(foot)}" fill="{lidc}"/>')
        if g.get('lowskin'):
            out.append(f'<path d="{P(g["lowskin"])}" fill="{s.skin}"/>')
        opw = g['open']
        c = uid('c')
        out.append(f'<clipPath id="{c}"><path d="{P(opw)}"/></clipPath>')
        ix, iy, rx, ry = g['iris']
        col = C['iris']
        bw = C.get('band', 0.045) * D
        band = list(g['upper']) + [(x, y + bw) for x, y in g['upper'][::-1]]
        inner = [f'<path d="{P(opw)}" fill="{SCLERA}"/>', f'<path d="{P(band)}" fill="{LIDBAND}"/>']
        inner += s.iris_svg(g)
        ic = uid('c')
        inner.append(f'<clipPath id="{ic}"><ellipse cx="{f1(ix)}" cy="{f1(iy)}" rx="{f1(rx)}" ry="{f1(ry)}"/></clipPath>'
                     f'<g clip-path="url(#{ic})"><path d="{P(band)}" fill="{col["sh"]}"/></g>')
        pk = C.get('pupil_k', 0.42)
        pry = pk * ry; prx = pry * rx / ry
        px = ix + 0.08 * rx * g['gx']; py = iy + 0.03 * ry
        inner.append(f'<ellipse cx="{f1(px)}" cy="{f1(py)}" rx="{f1(prx)}" ry="{f1(pry)}" fill="{col["pupil"]}"/>')
        inner.append(s.catchlights(g, e))
        out.append(f'<g clip-path="url(#{c})">{"".join(inner)}</g>')
        # floating crease above the lash line + soft bag line under a raised lower lid (never a closed ring)
        crc = C.get('crease_col') or shade_hex(s.skin, 0.62)
        if len(g.get('crease_up', [])) > 3 and e.get('crease', True):
            out.append(stroke(g['crease_up'], C.get('crease_t', 0.016) * D, color=crc, taper=(0.35, 0.35), wmin=0.2))
        if len(g.get('bagline', [])) > 3:
            out.append(stroke(g['bagline'], 0.013 * D, color=crc, taper=(0.4, 0.4), wmin=0.2))
        if e['wobble']:
            out.append(f'<path d="{P(xf(g["open"], 0.014 * D, -0.008 * D))}" fill="none" stroke="{INK}" stroke-opacity="0.30" '
                       f'stroke-width="{f1(0.012 * D)}" stroke-linejoin="round"/>')
        # lower lid line
        low = g['lower']
        if (low[-1][0] - low[0][0]) * side < 0:
            low = low[::-1]                     # inner -> outer
        lt = C.get('lower_t', 0.02) * D
        if C.get('lower', 'full') == 'outer' and not g['lowc']:
            n = len(low)
            out.append(stroke(low[: n // 2 + 2], lt * 0.55, taper=(0.3, 0.0), wmin=0.3))
            out.append(stroke(low[n // 2:], lt, taper=(0.0, 0.25), wmin=0.3))
        else:
            out.append(stroke(low, lt, taper=(0.18, 0.18), wmin=0.35))
        # upper lash line: tapers toward the inner corner, character ending at the outer corner
        up = g['upper']
        if (up[-1][0] - up[0][0]) * side < 0:
            up = up[::-1]
        out.append(stroke(up, lash, taper=(0.42, C.get('lash_out_taper', 0.0)), wmin=0.32))
        out.append(s.lash_end(up, lash))
        return ''.join(out)

    def lash_end(s, L, lash):
        D = s.D; E = L[-1]; side = 1 if L[-1][0] > L[0][0] else -1
        kind = s.C.get('lash_end', 'flick')
        if kind == 'flick':                     # Bix: one upturned flick
            pts = qbez(E, (E[0] + side * 0.045 * D, E[1] - 0.004 * D), (E[0] + side * 0.070 * D, E[1] - 0.050 * D), 14)
            return stroke(pts, lash * 0.80, taper=(0.0, 0.85), wmin=0.12)
        if kind == 'droop':                     # Gus: soft rounded droop, no flick
            pts = qbez(E, (E[0] + side * 0.030 * D, E[1] + 0.006 * D), (E[0] + side * 0.040 * D, E[1] + 0.040 * D), 14)
            return stroke(pts, lash * 0.82, taper=(0.0, 0.7), wmin=0.35)
        return ''

    def ray_arc(s, g, a0, a1, gap, n=16, center=None):
        """points just outside the footprint between local angles a0..a1 (0 = outward, 90 = down)."""
        cw = center or g['core_w']
        out = []
        for k in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * k / n)
            dl = (math.cos(a) * g['side'], math.sin(a))
            dist = ray_hit(cw, dl, g['foot'])
            out.append((cw[0] + dl[0] * (dist + gap), cw[1] + dl[1] * (dist + gap)))
        return out

    def draw_under(s, geoms, e):
        """adult marks round the eyes: Bix's lower-lid crease, Gus's double bags, crow's-feet on both."""
        D = s.D; out = []
        for g in geoms:
            hide_far = g['far'] and abs(s.turn) > 0.3
            if s.C.get('bags') and not g['closed']:
                a0, a1 = (60, 145) if hide_far else (15, 150)
                inner_arc = s.ray_arc(g, a0, a1, -0.004 * D, 24)
                outer_arc = s.ray_arc(g, a0, a1, 0.052 * D, 24)
                out.append(f'<path d="{P(inner_arc + outer_arc[::-1])}" fill="{shade_hex(s.skin, 0.11)}"/>')
                out.append(stroke(outer_arc, 0.019 * D, taper=(0.3, 0.3), wmin=0.3))
                sec = s.ray_arc(g, a0 + 22, a1 - 32, 0.092 * D, 14)
                out.append(stroke(sec, 0.015 * D, taper=(0.35, 0.35), wmin=0.2))
            if s.C.get('crease') and not g['closed'] and not g.get('lowskin'):
                us = s.C.get('under_span', (22, 112))
                a0, a1 = (max(55, us[0]), min(115, us[1])) if hide_far else us
                arc = s.ray_arc(g, a0, a1, 0.038 * D, 16)
                out.append(stroke(arc, s.C.get('under_t', 0.017) * D, color=s.C.get('under_col', INK), taper=(0.3, 0.4), wmin=0.25))
            if s.C.get('crow') and not hide_far:
                oc = g['outer']
                for da, ln in ((-16, 0.060), (14, 0.052)):
                    d = (g['side'] * math.cos(math.radians(da)), math.sin(math.radians(da)))
                    p0 = (oc[0] + d[0] * 0.035 * D, oc[1] + d[1] * 0.035 * D + 0.01 * D)
                    p1 = (p0[0] + d[0] * ln * D, p0[1] + d[1] * ln * D)
                    out.append(stroke([p0, p1], s.C.get('crow_t', 0.015) * D, color=s.C.get('crow_col', INK), taper=(0.1, 0.6), wmin=0.3))
        return ''.join(out)

    # ------------------------------------------------------------------ brows
    def draw_brows(s, e, geoms):
        C, D = s.C, s.D
        out = []
        for side, i in ((-1, 0), (1, 1)):
            g = geoms[i]
            L = C['brow_len'] * D * (0.78 if g['far'] else 1.0)
            cxb = g['cx_w'] + side * (C.get('brow_dx', 0.0) + e['brow_dx'][i]) * D * g['wk']
            topy = g['top_w']
            th = C['brow_th'] * D
            yb = topy - (C['brow_gap'] + e['brow_raise'][i]) * D - th * 0.5
            ang = -side * (e['brow_tilt'][i] + C.get('brow_tilt0', 0.0))
            arch = (e['brow_arch'] or (C['brow_arch'], C['brow_arch']))[i]
            a = (cxb - side * L / 2, yb); b = (cxb + side * L / 2, yb)
            cc = (cxb - side * L * 0.08, yb - arch * L * 2)
            kind = C['brow']
            if kind == 'comma':
                pts = xf(qbez(a, cc, b, 30), ang=ang, c=(cxb, yb))
                hr = th * 0.62
                hc = C.get('brow_halo')
                if hc:
                    out.append(stroke(pts, th + 0.026 * D, color=hc, taper=(0.0, 0.85), wmin=0.3)
                               + f'<circle cx="{f1(pts[0][0])}" cy="{f1(pts[0][1])}" r="{f1(hr + 0.013 * D)}" fill="{hc}"/>')
                out.append(stroke(pts, th, taper=(0.0, 0.92), wmin=0.14)
                           + f'<circle cx="{f1(pts[0][0])}" cy="{f1(pts[0][1])}" r="{f1(hr)}" fill="{INK}"/>')
            elif kind == 'scallop':
                N = 44
                base = xf(qbez(a, cc, b, N), ang=ang, c=(cxb, yb))
                droop = C.get('brow_droop', 0.0) * th
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
                fill = C.get('brow_fill', GUS_GREY)
                inner = clipped(poly, f'<path d="{P(xf(bot_p + [(q[0], q[1] + th) for q in bot_p[::-1]], 0, -th * 0.25))}" fill="{shade_hex(fill, 0.18)}"/>')
                out.append(inked(poly, fill, (0.012 * D, 0.02 * D), s.seed + 70 + i, bias=0.7, inner=inner, off=(2, 2)))
                for j in (9, 19, 29):
                    q = base[j]
                    out.append(stroke([lerp(q, top_p[j], 0.1), lerp(q, top_p[j + 3], 0.75)], 0.012 * D, taper=(0.2, 0.6), wmin=0.3))
            else:
                pts = xf(qbez(a, cc, b, 24), ang=ang, c=(cxb, yb))
                out.append(stroke(pts, th, taper=(0.3, 0.45), wmin=0.3))
        return ''.join(out)

    # ------------------------------------------------------------------ nose / mouth / mustache
    def nose_geom(s, e):
        cx, cy = s.ncx, s.ny
        tilt = e['nose_tilt']; ang = -s.f * tilt
        pts = xf([(cx + x, cy + y) for x, y in s.nose_local()], ang=ang, c=(cx, cy))
        return dict(pts=pts, c=(cx, cy), ang=ang, w=s.nw, h=s.nh, tilt=tilt)

    def draw_bridge(s, e, geoms):
        """nose bridge drawn inside the eye gap up past the eyes' mid-height (the gap is never an empty strip)."""
        D = s.D; C = s.C
        n = C['nose']
        ytop = s.top + (C['eye_cy'] - 0.035) * D
        ybot = s.ny - s.nh * 0.25
        xt = s.fx + s.f * 0.004 * D; xb = s.ncx
        wt, wb = n.get('bridge_w', (0.050, 0.085))
        wt *= D; wb *= D
        L = [(xt - wt / 2, ytop + wt * 0.3), (xb - wb / 2, ybot), (xb + wb / 2, ybot), (xt + wt / 2, ytop + wt * 0.3)]
        cap = [(xt + wt / 2 * math.cos(math.pi * k / 12), ytop + wt * 0.3 - wt / 2 * math.sin(math.pi * k / 12)) for k in range(13)]
        poly = [L[1], L[2], L[3]] + cap[1:-1] + [L[0]]
        fill = n.get('bridge_fill', shade_hex(s.skin, 0.10))
        out = [f'<path d="{P(poly)}" fill="{fill}"/>']
        if n.get('bridge_ink', True):
            sd = s.f if abs(s.turn) > 0.05 else 1
            a = (xt + sd * wt / 2, ytop + wt * 0.4); b = (xb + sd * wb / 2 * 0.8, ybot + 0.02 * D)
            out.append(stroke(qbez(a, lerp(a, b, 0.5), b, 12), 0.017 * D, taper=(0.35, 0.2), wmin=0.25))
        return ''.join(out)

    def draw_nose(s, e):
        ng = s.nose_geom(e)
        pts = ng['pts']; cx, cy = ng['c']; w, h = ng['w'], ng['h']; ang = ng['ang']
        n = s.C['nose']
        base = n['fill']
        D = s.D
        if n['kind'] == 'bell':
            fill = GUS_TIP if e['flush'] else base
            inner = ''
            sh = xf(ellipse_pts(cx - s.f * w * 0.30, cy + h * 0.18, w * 0.30, h * 0.42, 50), ang=ang, c=(cx, cy))
            inner += f'<path d="{P(sh)}" fill="{shade_hex(fill, 0.06)}"/>'
            tip = xf(ellipse_pts(cx + s.f * w * 0.10, cy + h * 0.52, w * 0.52, h * 0.40, 50), ang=ang, c=(cx, cy))
            inner += f'<path d="{P(tip)}" fill="{shade_hex(GUS_TIP, 0.06) if e["flush"] else GUS_TIP}"/>'
            out = [f'<path d="{P(pts)}" fill="{fill}"/>', clipped(pts, inner),
                   f'<path d="{P(pts)}" fill="none" stroke="{shade_hex(base, 0.22)}" stroke-width="{f1(0.012 * D)}"/>']
            # ink only along the lower edge
            lo = [q for q in pts if q[1] > cy + h * 0.10]
            if lo:
                k0 = pts.index(lo[0])
                ring = pts[k0:] + pts[:k0]
                run = [q for q in ring if q[1] > cy + h * 0.10]
                run.sort(key=lambda q: q[0])
                out.append(stroke(run, 0.030 * D, taper=(0.3, 0.3), wmin=0.2))
            if ng['tilt'] > 4 or e.get('nostril'):
                q = (cx - s.f * w * 0.12, cy + h * 0.30)
                out.append(stroke(qbez((q[0] - 0.03 * D, q[1]), (q[0], q[1] + 0.02 * D), (q[0] + 0.03 * D, q[1]), 8), 0.014 * D,
                                  color=shade_hex(base, 0.45), taper=(0.3, 0.3)))
            return ''.join(out)
        fill = FLUSH if e['flush'] else base
        inner = crescent(pts, 'htR' if e['flush'] else n.get('shade', 'htC'), -w * 0.16, -h * 0.18, 0.55)
        if e['tip_flush']:
            blot = xf(ellipse_pts(cx + s.f * w * 0.18, cy + h * 0.10, w * 0.36, h * 0.34, 50), ang=ang, c=(cx, cy))
            inner += clipped(pts, f'<path d="{P(blot)}" fill="{n.get("flush_col", FLUSH)}"/>', OFF)
        hl = xf(ellipse_pts(cx - w * 0.17 + s.turn * w * 0.08, cy - h * 0.22, w * 0.11, h * 0.08, 30), ang=ang - 20, c=(cx, cy))
        inner += f'<path d="{P(hl)}" fill="{SCLERA}" fill-opacity="0.75"/>'
        lw = s.C.get('line', (0.021, 0.035))
        out = [inked(pts, fill, (lw[0] * D * 0.85, lw[1] * D * 0.85), s.seed + 7, inner=inner)]
        if ng['tilt'] > 4:
            nos = [(-w * 0.17, h * 0.26), (w * 0.17, h * 0.26)] if abs(s.turn) < 0.3 else [(s.f * w * 0.12, h * 0.27), (-s.f * w * 0.18, h * 0.29)]
            for k, (dx, dy) in enumerate(nos):
                q = rot((cx + dx, cy + dy), ang, (cx, cy))
                rr = w * (0.085 if k == 0 else 0.065)
                out.append(f'<ellipse cx="{f1(q[0])}" cy="{f1(q[1])}" rx="{f1(rr)}" ry="{f1(rr * 0.62)}" transform="rotate({f1(ang)} {f1(q[0])} {f1(q[1])})" fill="{MOUTH}"/>')
        return ''.join(out)

    def mouth_anchor(s, e):
        x = s.ncx - s.turn * 0.05 * s.D + e['mouth_dx'] * s.D
        nb = s.ny + s.nh / 2 * s.C.get('nb_k', 1.0)
        return x, nb

    def draw_mouth(s, e):
        """mouths stay small and modest; the eyes do the acting."""
        m = e['mouth']
        if m == 'none':
            return ''
        D = s.D; x, nb = s.mouth_anchor(e)
        k = s.C.get('mouth_k', 1.0)
        out = []
        bs = -s.f if abs(s.turn) > 0.1 else 1          # back side of the face
        if m == 'o':
            rx, ry = s.C.get('o_r', (0.065, 0.052))
            rx *= D * k; ry *= D * k
            cy = nb + s.C.get('o_dy', 0.075) * D
            pts = ellipse_pts(x, cy, rx, ry, 50)
            inner = f'<path d="{P(ellipse_pts(x + 0.01 * D, cy + ry * 0.6, rx * 0.6, ry * 0.42, 30))}" fill="{s.C.get("tongue", "#8E3B4A")}"/>'
            out.append(inked(pts, MOUTH, (0.014 * D, 0.02 * D), 3, off=(0, 0), inner=clipped(pts, inner)))
        elif m == 'tight':                              # angry: a short, slightly downturned line
            y = nb + 0.085 * D
            pts = qbez((x - 0.07 * D, y + 0.018 * D), (x, y - 0.012 * D), (x + 0.07 * D, y + 0.018 * D), 16)
            out.append(stroke(pts, 0.028 * D, taper=(0.2, 0.2)))
        elif m == 'curl':
            p0 = (x + bs * 0.03 * D, nb + 0.075 * D)
            p1 = (x + bs * 0.10 * D, nb + 0.10 * D)
            p2 = (x + bs * 0.16 * D, nb + 0.06 * D)
            out.append(stroke(qbez(p0, p1, p2), 0.028 * D, taper=(0.15, 0.4)))
            out.append(stroke(qbez(p2, (p2[0] + bs * 0.02 * D, p2[1] - 0.004 * D), (p2[0] + bs * 0.016 * D, p2[1] - 0.03 * D), 8), 0.02 * D, taper=(0.0, 0.9)))
        elif m == 'smile':                              # neutral: an easy, amused half-smile under the mustache
            p0 = (x - bs * 0.035 * D, nb + 0.080 * D)
            p1 = (x + bs * 0.040 * D, nb + 0.112 * D)
            p2 = (x + bs * 0.115 * D, nb + 0.072 * D)
            out.append(stroke(qbez(p0, p1, p2, 20), 0.030 * D, taper=(0.3, 0.25)))
            out.append(stroke(qbez(p2, (p2[0] + bs * 0.016 * D, p2[1] - 0.002 * D), (p2[0] + bs * 0.014 * D, p2[1] - 0.026 * D), 8),
                              0.018 * D, taper=(0.0, 0.9)))
        elif m == 'flat':
            y = nb + 0.085 * D
            a = (x - 0.04 * D, y + 0.004 * D); b = (x + 0.10 * D, y - 0.004 * D)
            out.append(stroke([a, b], 0.028 * D, taper=(0.15, 0.15)))
            out.append(stroke([b, (b[0] + 0.024 * D, b[1] + 0.018 * D)], 0.02 * D, taper=(0.0, 0.8)))
        elif m == 'wobble':
            y = nb + 0.085 * D
            pts = [(x - 0.09 * D + 0.18 * D * t, y + 0.014 * D * math.sin(t * math.pi * 4)) for t in (j / 40 for j in range(41))]
            out.append(stroke(pts, 0.026 * D, taper=(0.15, 0.15)))
        return ''.join(out)

    def draw_stache(s, e):
        if not s.C.get('stache'):
            return ''
        D = s.D; x, nb = s.mouth_anchor(e)
        x -= e['mouth_dx'] * D * 0.5
        y0 = nb + 0.016 * D + e['stache_dy'] * D
        out = []
        for side in (-1, 1):
            front = abs(s.turn) > 0.1 and side == s.f
            Ls = (0.115 if front else 0.160) * D
            lift = e['stache'] * D
            p0 = (x + side * 0.014 * D, y0 - 0.004 * D)
            p1 = (x + side * Ls * 0.55, y0 + 0.022 * D + lift * 0.35)
            p2 = (x + side * Ls, y0 - 0.006 * D + lift)
            pts = qbez(p0, p1, p2, 24)
            tip = (p2[0] + side * 0.020 * D, p2[1] - 0.024 * D - lift * 0.3)
            out.append(stroke(pts + [tip], 0.032 * D, taper=(0.12, 0.7), wmin=0.2))
        return ''.join(out)

    # ------------------------------------------------------------------ ears / flush / folds
    def ear_sides(s):
        return (-1, 1) if abs(s.turn) < 0.3 else (-s.f,)

    def ear_svg(s, side):
        rx, ry, pr = (k * s.D for k in s.C['ear'])
        ex = s.cx + side * (s.R + pr - rx)
        ey = s.cy + (s.C.get('ear_y', 0.52) - 0.5) * s.D
        pts = ellipse_pts(ex, ey, rx, ry, 50)
        out = inked(pts, s.skin, (0.021 * s.D * 0.8, 0.035 * s.D * 0.8), s.seed + 40 + side,
                    inner=crescent(pts, s.C.get('ear_shade', 'htRs'), -rx * 0.3 * side, -ry * 0.2, 0.6))
        a = (ex + side * rx * 0.30, ey - ry * 0.48)
        m = (ex + side * rx * 1.05, ey - ry * 0.05)
        b = (ex + side * rx * 0.30, ey + ry * 0.52)
        out += stroke(qbez(a, m, b), 0.022 * s.D, taper=(0.25, 0.3))
        return out

    def flush_band(s):
        """caught: a flat ruddy band across the nose and cheeks (never pink cheek stickers)."""
        D = s.D
        y = s.ny - 0.01 * D
        band = [(s.cx - s.R * 1.2 + k * s.R * 2.4 / 40, y - 0.075 * D + 0.012 * D * math.sin(k / 40 * math.pi)) for k in range(41)]
        band += [(s.cx + s.R * 1.2 - k * s.R * 2.4 / 40, y + 0.075 * D + 0.016 * D * math.sin(k / 40 * math.pi)) for k in range(41)]
        return clipped(s.head, f'<path d="{P(band)}" fill="{RUDDY}"/>')

    def draw_folds(s, e):
        D = s.D; out = []
        kind = s.C.get('fold')
        if kind == 'jowl1':                       # Bix: one sag line under the cheek, back side
            bs = -s.f if abs(s.turn) > 0.1 else 1
            nx = s.ncx + bs * (s.nw / 2)
            p0 = (nx + bs * 0.12 * D, s.ny + 0.10 * D)
            p1 = (nx + bs * 0.16 * D, s.ny + 0.15 * D)
            p2 = (nx + bs * 0.13 * D, s.ny + 0.20 * D)
            out.append(stroke(qbez(p0, p1, p2, 20), 0.02 * D, taper=(0.3, 0.55), wmin=0.25))
        elif kind == 'jowl2':                     # Gus: nasolabial folds beside the bell nose
            for side in (-1, 1):
                if abs(s.turn) > 0.3 and side == s.f:
                    continue
                nx = s.ncx + side * (s.nw / 2)
                p0 = (nx + side * 0.005 * D, s.ny + 0.02 * D)
                p1 = (nx + side * 0.05 * D, s.ny + 0.10 * D)
                p2 = (nx + side * 0.02 * D, s.ny + 0.17 * D)
                out.append(stroke(qbez(p0, p1, p2, 20), 0.02 * D, taper=(0.3, 0.5), wmin=0.25))
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
        for k, cb in enumerate(hp['combs']):
            col = BIX_COMB
            inner += stroke(cb, 0.016 * D, color=col, taper=(0.25, 0.35), wmin=0.2)
        for tp in hp['temples']:            # flat grey temples, no halftone (the dots read as earmuffs)
            inner += f'<path d="{P(tp)}" fill="{BIX_GREY}"/>'
            xs_ = [q[0] for q in tp]; ys_ = [q[1] for q in tp]
            cxm, h_ = (min(xs_) + max(xs_)) / 2, max(ys_) - min(ys_)
            for j in (-1, 1):
                x_ = cxm + j * (max(xs_) - min(xs_)) * 0.18
                inner += stroke([(x_ - 0.01 * D, min(ys_) + h_ * 0.12), (x_ + 0.012 * D, min(ys_) + h_ * 0.80)], 0.012 * D,
                                color=BIX_GREY_LN, taper=(0.3, 0.3), wmin=0.2)
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
        if e['flush']:
            out.append(s.flush_band())
        out.append(s.draw_folds(e))
        geoms = [s.eye_geom(-1, e), s.eye_geom(1, e)]
        out.append(s.draw_mouth(e))
        nose_under = C['nose'].get('under', False)
        out.append(s.draw_bridge(e, geoms))
        if nose_under:
            out.append(s.draw_nose(e))
        out.append(s.draw_under(geoms, e))
        for g in geoms:
            out.append(s.draw_eye(g, e))
        if not nose_under:
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
            ys = [q[1] for q in gg['foot']]; xs = [q[0] for q in gg['foot']]
            d = dict(h=(max(ys) - min(ys)) / D, w=(max(xs) - min(xs)) / D,
                     top=(min(ys) - s.top) / D, ctr=((max(ys) + min(ys)) / 2 - s.top) / D, far=gg['far'])
            if 'iris' in gg:
                ix, iy, rx, ry = gg['iris']
                oy = [q[1] for q in gg['open']]
                d.update(iris_h=2 * ry / D, iris_w=2 * rx / D, iris_frac=2 * ry / (max(ys) - min(ys)),
                         lid_cov=(min(oy) - min(ys)) / (max(ys) - min(ys)),
                         lid_cut=(gg['lid_y_at_iris'] - (iy - ry)) / D, pupil_h=2 * s.C.get('pupil_k', 0.42) * ry / D)
            res[k] = d
        xl = [q[0] for q in g[0]['foot']]; xr = [q[0] for q in g[1]['foot']]
        res['gap'] = (min(xr) - max(xl)) / D
        res['span'] = (max(xr) - min(xl)) / D
        res['nose_w'] = s.nw / D
        res['nose_top'] = (s.ny - s.nh / 2 - s.top) / D
        res['nose_bot'] = (s.ny + s.nh / 2 - s.top) / D
        res['lash'] = s.C['lash']
        return res


# ======================================================================== CAST SPECS
BIX = dict(skin=SKIN_B, eye='shizuku', eye_w=0.38, eye_h=0.54, eye_gap=0.08, eye_cy=0.475, far_w=0.62,
           lid=0.20, lid_tilt=-3, lid_bow=0.03, kx_eye=0.28, kx_nose=0.30, nose_over=0.03, nose_max=0.80,
           iris=IRIS_BIX, ih=0.41, iw_k=0.80, pupil_k=0.42, cut=0.04, band=0.045, hl='square',
           lash=0.06, lash_end='none', lash_out_taper=0.22, lower='full', lower_t=0.02, crease_t=0.017, crease=True, crow=True,
           under_col=shade_hex(SKIN_B, 0.42), under_t=0.013, under_span=(38, 100), crow_col=shade_hex(SKIN_B, 0.45), crow_t=0.013,
           nose=dict(kind='button', w=0.27, h=0.20, fill=NOSE_B, shade='htC', bridge_w=(0.048, 0.08), flush_col='#8A5340'),
           ear_shade='htCs',
           brow='comma', brow_th=0.05, brow_len=0.22, brow_gap=-0.035, brow_arch=0.06, brow_dx=-0.01, brow_tilt0=5,
           lid_tone=shade_hex(SKIN_B, 0.03), crease_max=0.052, crease_span=(0.30, 0.94),
           ear=(0.09, 0.115, 0.07), ear_y=0.53, ear_front=True, hair='slick', stache=True, fold='jowl1',
           hairline=[(0, -0.93), (14, -0.93), (30, -0.92), (44, -0.88), (54, -0.74), (62, -0.30), (70, 0.06), (80, 0.12),
                     (90, -0.10), (100, -0.12), (112, 0.0), (130, 0.32), (154, 0.55), (180, 0.64)],
           hair_vol=0.075, temple=(70, -0.10, 12, 0.30), brow_halo=SKIN_B, shade='htC', shade_op=0.5, o_dy=0.08, o_r=(0.06, 0.05))

GUS = dict(skin=GUS_SKIN, eye='tareme', eye_w=0.40, eye_h=0.54, eye_gap=0.09, eye_cy=0.47, far_w=0.62,
           lid=0.225, lid_tilt=10, lid_bow=0.06, kx_eye=0.26, kx_nose=0.22, nose_over=0.06, nose_max=0.76,
           iris=IRIS_GUS, ih=0.405, iw_k=0.82, pupil_k=0.42, cut=0.04, band=0.045, hl='wetoval',
           lash=0.055, lash_end='none', lash_out_taper=0.30, lower='outer', lower_t=0.022, crease_t=0.016, bags=True, crow=True,
           nose=dict(kind='bell', w=0.36, h=0.30, fill=GUS_NOSE, bridge_w=(0.07, 0.10), bridge_fill=GUS_NOSE, bridge_ink=False),
           brow='scallop', brow_th=0.08, brow_len=0.30, brow_gap=-0.035, brow_arch=0.04, brow_tilt0=-8, brow_dx=0.02,
           brow_fill=HAIR_GREY, brow_droop=1.3,
           ear=(0.10, 0.125, 0.085), ear_y=0.54, ear_front=True, hair='fringe', fringe_poke=0.075, jowls=0.07,
           fold='jowl2', shade='htR', shade_op=0.4, o_dy=0.05, o_r=(0.09, 0.07), mouth_k=1.0, nb_k=0.92)

WIT = dict(skin=SKIN_W, eye='generic', eye_w=0.29, eye_h=0.46, eye_gap=0.09, eye_cy=0.45, far_w=0.70,
           lid=0.22, lid_tilt=0, lid_bow=0.0, kx_eye=0.26, kx_nose=0.36, nose_over=0.03, nose_max=0.82,
           iris=IRIS_CAMEO, plain_iris=True, ih=0.35, iw_k=0.88, pupil_k=0.42, cut=0.03, band=0.035, hl='dot',
           lash=0.042, lash_end='none', lower='full', lower_t=0.015, crease_t=0.012,
           nose=dict(kind='button', w=0.25, h=0.19, fill=NOSE_W, shade='htC', bridge_w=(0.04, 0.07)),
           brow='generic', brow_th=0.05, brow_len=0.20, brow_gap=0.04, brow_arch=0.06,
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
    return Body(D, facing, plate=None, glove=SKIN_B, shoe='brogue', seed=400,
                L=dict(neck_vis=0.10, spine=0.97, thigh=0.80, shin=0.74))


def gus_body(D, facing):
    return Body(D, facing, plate=None, glove=GUS_SKIN, shoe='loafer', seed=500, knuckle=True,
                L=dict(spine=0.90, thigh=0.78, shin=0.74, neck_vis=0.07, neck_x=0.10, neck_w=0.20, up=0.80, fore=0.80,
                       sh=0.29))


BOWTIE_W = 0.30   # Bix's one kept accessory, a small rose bow tie at the throat (was 0.36 D with the costume)


def bix_bow(J, p, D):
    return bow_tie(padd(J['Nb'], J['sd'], 0.03 * D), -p.get('spine', 0) * 0.5, D, 441, squash=0.90, width=BOWTIE_W)


def bix_figure(f, E, b, p, J, prop='', order=None, extra=None):
    """pure stick body; the only body-side extra is the bow tie."""
    D = b.D
    parts = dict(collar=bix_bow(J, p, D), prop=prop)
    if extra:
        parts.update(extra)
    order = order or ['shadow', 'f_arm', 'f_hand', 'f_leg', 'spine', 'yoke', 'n_leg', 'neck',
                      'collar', 'head', 'n_arm', 'n_hand', 'prop', 'f_thumb', 'n_thumb', 'marks']
    return figure(f, E, b, J, order, **parts)


def gus_figure(f, E, b, p, J, prop='', order=None, extra=None):
    """pure stick body, no accessory at all."""
    parts = dict(prop=prop)
    if extra:
        parts.update(extra)
    order = order or ['shadow', 'f_arm', 'f_hand', 'f_thumb', 'f_leg', 'spine', 'yoke', 'n_leg', 'neck',
                      'head', 'n_arm', 'n_hand', 'prop', 'n_thumb', 'marks']
    return figure(f, E, b, J, order, **parts)


def defs_all():
    return common_defs() + check_rose() + black_defs()


# ======================================================================== FACES SHEET (hero head, 3 x 2)
BIX_EXPR = [
    ('neutral', dict(tilt=2, gaze=(-0.35, 0.05), low_bow=(0.05, 0.05), brow_raise=(0.0, 0.035), brow_arch=(0.05, 0.11), brow_tilt=(2, -3),
                     mouth='smile', stache=-0.018)),
    ('surprised', dict(tilt=-3, lid=(0.02, 0.02), lid_tilt=(0, 0), lid_bow=(0.10, 0.10), eye_scale=(1.10, 1.10),
                       iris_h=0.58, free=True, gaze=(0.0, -0.10), brow_raise=(0.08, 0.08), brow_arch=(0.16, 0.16),
                       mouth='o', stache=-0.012, strand=0.85)),
    ('angry', dict(tilt=4, lid=(0.36, 0.36), lid_tilt=(-20, -20), lid_bow=(0.0, 0.0), low=(0.06, 0.06), gaze=(-0.30, 0.15),
                   hl='single', crease=False, brow_raise=(-0.12, -0.12), brow_tilt=(26, 26), brow_arch=(0.02, 0.02), mouth='tight',
                   stache=0.02, tip_flush=True, marks=[('vein', 0.25, -0.36, 0.07)])),
    ('smug', dict(tilt=7, lid=(0.30, 0.30), lid_tilt=(0, 0), low=(0.12, 0.12), low_bow=(0.08, 0.08), gaze=(-0.85, 0.25),
                  brow_raise=(0.0, 0.07), brow_tilt=(6, -10), brow_arch=(0.04, 0.18), mouth='curl', stache=-0.03, nose_tilt=8)),
    ('panic', dict(tilt=-4, lid=(0.02, 0.02), lid_tilt=(0, 0), lid_bow=(0.10, 0.10), eye_scale=(1.08, 1.08), iris_h=0.55,
                   free=True, wobble=True, gaze=(-0.5, 0.35), brow_raise=(0.08, 0.08), brow_tilt=(-22, -22),
                   brow_arch=(0.10, 0.10), mouth='wobble', stache=-0.02, strand=1.0,
                   marks=[('sweat', -0.64, -0.22, 0.12, -30), ('sweat', 0.66, -0.34, 0.13, 35)])),
    ('side-eye', dict(tilt=-3, lid=(0.44, 0.44), lid_tilt=(0, 0), lid_bow=(0.10, 0.10), gaze=(1.0, 0.05), hl='off',
                      brow_raise=(-0.02, 0.03), brow_tilt=(4, -4), brow_arch=(0.02, 0.06), mouth='flat', mouth_dx=0.03,
                      stache=0.02)),
]


def bust(face, E, D, facing, body_fn, fig_fn, clip_rect):
    b = body_fn(D, facing)
    p = dict(neck=8 if facing < 0 else 8, tilt=E.get('tilt', 0), spine=-3 * facing, bow=0.03, nup=-10 * facing, nlo=-6 * facing,
             fup=8 * facing, flo=4 * facing, nFr=(0.0, 1.45), fFr=(0.0, 1.45), ngrip='hidden', fgrip='hidden')
    J = b.joints(face, p)
    # head-reference sheet: neck stub + shoulder bar and the bow tie, nothing else (no spine running out of the
    # cell -- a long stick under a round head in a cell reads as a lollipop)
    svg = fig_fn(face, E, b, p, J, order=['yoke', 'neck', 'collar', 'head'])
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
E_BIX_STAND = dict(tilt=3, gaze=(-0.45, 0.08), low_bow=(0.05, 0.05), brow_raise=(0.0, 0.035), brow_arch=(0.05, 0.11), brow_tilt=(2, -3), mouth='smile', stache=-0.018)
AKIMBO_OFF = (0.12, -0.10)   # hero far wrist relative to the hip point, in D (screen x, y)
AKIMBO_BEND = -1
GUS_BACK = (0.10, -0.12, -1, 0.62, 0.52, -100)   # Gus far wrist vs hip (D), elbow side, upper/fore scale, hand angle
E_GUS_STAND = dict(tilt=-5, gaze=(-0.70, 0.60), brow_raise=(0.0, 0.0), mouth='none', nostril=True)


def bix_stand(D, x, FL, E):
    facing = -1
    fn = lambda cx, cy: BigFace(cx, cy, D, -0.45, BIX, 11)
    b = bix_body(D, facing)
    p = dict(neck=8, tilt=E.get('tilt', 0), spine=-3, bow=0.03,
             nWr=(-0.46, -0.30), nbend=-1, nhand=-92, ngrip='flat', nthumb=1, nthumb_at=0.52, nthumb_sp=40,
             fWr=(0.0, 1.0), fbend=AKIMBO_BEND, fhand=-62, fgrip='mitt', fthumb=1, fthumb_at=0.40, fnothumb=True,
             nFr=(-0.04, 1.54), ntoe=-96, nkbend=1,
             fFr=(0.16, 1.42), ftoe=-35, fkbend=1, fsole=-1)
    f, J = place(fn, b, p, x, FL, 'n')
    # far hand on the far hip (akimbo): wrist just behind the spine end, elbow out to the back
    tgt = padd(padd(J['H'], (1, 0), AKIMBO_OFF[0] * D), (0, 1), AKIMBO_OFF[1] * D)
    p['fWr'] = ((tgt[0] - J['Sf'][0]) / D, (tgt[1] - J['Sf'][1]) / D)
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
             fWr=(0.10, 1.52), fbend=GUS_BACK[2], fup_k=GUS_BACK[3], flo_k=GUS_BACK[4], fhand=GUS_BACK[5], fgrip='mitt', fthumb=-1,
             nFr=(-0.16, 1.42), ntoe=-100, nkbend=1,
             fFr=(0.22, 1.42), ftoe=-62, fkbend=-1)
    f, J = place(fn, b, p, x, FL, 'n')
    # same old-man habit as in the scene: far hand pressed to the small of his back
    tgt = (J['H'][0] + GUS_BACK[0] * D, J['H'][1] + GUS_BACK[1] * D)
    p['fWr'] = ((tgt[0] - J['Sf'][0]) / D, (tgt[1] - J['Sf'][1]) / D)
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
BIX_SCENE_E = dict(tilt=-6, lid=(0.19, 0.19), lid_tilt=(-2, -2), lid_bow=(0.06, 0.06), low=(0.05, 0.05), low_bow=(0.08, 0.08), hl='on',
                   brow_raise=(0.0, 0.07), brow_tilt=(4, -8), brow_arch=(0.06, 0.20), mouth='curl', stache=-0.03, nose_tilt=6)
GUS_SCENE_E = dict(tilt=-6, lid=(0.02, 0.02), lid_tilt=(4, 4), lid_bow=(0.10, 0.10), eye_scale=(1.10, 1.10), iris_h=0.57,
                   free=True, brow_raise=(0.08, 0.08), brow_tilt=(-14, -14), brow_arch=(0.12, 0.12), mouth='o', flush=True)
GUS_BACK_SC = (0.07, -0.13, -1, 0.56, 0.50, -100)   # scene version, elbow kept inside the frame
STOP = (74, 186, 0.80, 184, 0.92)   # scene: Bix near upper arm / forearm angle, forearm scale, hand angle (0 = down, 180 = up)
WIT_SCENE_E = dict(brow_raise=(0.04, 0.0), brow_tilt=(-8, 4), brow_arch=(0.12, 0.02))


def bix_scene(head=(350, 690), D=262, FL=1540):
    fn = lambda x, y: BigFace(x, y, D, 0.55, BIX, 11)
    b = bix_body(D, 1)
    p = dict(neck=8, tilt=-6, spine=12, bow=0.035, yoke_k=1.07,
             fstr=199, fhand=199, fgrip='mitt', fthumb=-1, fthumb_at=0.66, fthumb_sp=46,
             nup=STOP[0], nlo=STOP[1], nlo_k=STOP[2], nhand=STOP[3], nup_k=STOP[4], ngrip='flat', nthumb=-1, nthumb_at=0.42, nthumb_sp=40,
             nFr=(0.06, 1.56), ntoe=90, nkbend=-1,
             fFr=(-0.46, 1.48), ftoe=-62, fkbend=-1)
    # the other hand up, palm out at Gus: 'uh-uh. No dunking.'
    f, J = place(fn, b, p, head[0], FL, 'n')
    return f, b, p, J


def gus_scene(head=(880, 800), D=268, FL=1540, target=None):
    fn = lambda x, y: BigFace(x, y, D, -0.60, GUS, 21)
    b = gus_body(D, -1)
    p = dict(neck=22, tilt=-6, spine=6, bow=0.07, yoke_k=1.0, sh_nk=0.92, sh_fk=0.80,
             nstr=-84, ngrip='mitt', nthumb=1, nthumb_at=0.70, nthumb_sp=62,
             fWr=(0.0, 1.0), fbend=GUS_BACK[2], fup_k=GUS_BACK[3], flo_k=GUS_BACK[4], fhand=GUS_BACK[5], fgrip='mitt', fthumb=-1,
             nFr=(-0.50, 1.36), ntoe=-90, nkbend=1,
             fFr=(0.26, 1.42), ftoe=-48, fkbend=-1)
    f, J = place(fn, b, p, head[0], FL, 'n')
    # old-man move: far hand pressed to the small of his back while he lunges for the dunk
    p.update(fbend=GUS_BACK_SC[2], fup_k=GUS_BACK_SC[3], flo_k=GUS_BACK_SC[4], fhand=GUS_BACK_SC[5])
    tgt = (J['H'][0] + GUS_BACK_SC[0] * D, J['H'][1] + GUS_BACK_SC[1] * D)
    p['fWr'] = ((tgt[0] - J['Sf'][0]) / D, (tgt[1] - J['Sf'][1]) / D)
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
        # dunk speed lines: two short ones, kept clear of Bix's spine and shoulder bar
        for k, dx in enumerate((0.0, 0.11)):
            x = dn_c[0] + dx * S
            y0 = dn_c[1] - 0.17 * S - 0.015 * S * (k == 0)
            trail += stroke([(x, y0), (x - 0.008 * S, y0 - 0.16 * S - 0.03 * S * (k == 0))], 6, taper=(0.85, 0.1), wmin=0.2)
        path = cbez((bix.cx + 0.70 * S, bix.cy - 0.05 * S), (bix.cx + 0.72 * S, bix.cy - 0.95 * S),
                    (bix.cx - 0.05 * S, bix.cy - 1.12 * S), (cup_b[0] + 0.42 * S, cup_b[1] - 0.30 * S), 60)
        trail += dotted(path, S, 0.75)
        out.append(trail)
    dn = held_doughnut(dn_c[0], dn_c[1], ds, -10)
    gsil = gus_figure(gus, gE, gb, gp, gJ, prop=dn,
                      order=['halo', 'f_arm', 'f_hand', 'f_thumb', 'f_leg', 'spine', 'yoke', 'n_leg',
                             'neck', 'head', 'n_arm', 'n_hand', 'prop', 'n_thumb', 'marks'],
                      extra=dict(halo='' if sil else gb.halo(gJ, CREAM, 0.4)))
    cp = cup(cup_b[0], cup_b[1], cs, 0) + steam_small(cup_b[0], cup_b[1] - 138 * cs, cs * 0.62)
    bsil = bix_figure(bix, bE, bb, bp, bJ, prop=cp,
                      order=['halo', 'f_leg', 'spine', 'yoke', 'n_leg', 'f_arm',
                             'f_hand', 'neck', 'collar', 'head', 'n_arm', 'n_hand', 'prop', 'f_thumb', 'n_thumb', 'marks'],
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
    hx = info3['head']; px = info4['head']
    json.dump(dict(hero=[hx[0], hx[1], info3['D']], partner=[px[0], px[1], info4['D']]), open(os.path.join(HERE, '_info.json'), 'w'))
