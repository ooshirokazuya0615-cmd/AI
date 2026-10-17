#!/usr/bin/env python3
"""Sunday Nose -- one face rig, two images.

The Face class is a tiny animation rig: head, ears, hair, eyes (teardrops that
rotate around their point), lids, pupils, brows, nose (tilt / flush / bead) and
swap mouths are all driven by an expression dict.  scene.svg and faces.svg are
both built from this same rig.
"""
import math, random, os

HERE = os.path.dirname(os.path.abspath(__file__))

INK = '#1A1A1A'; CREAM = '#EFE6D2'; CYAN = '#2C8FB8'; ROSE = '#C8457C'
MUSTARD = '#E8C547'; PINKNOSE = '#E49A8C'; GREEN = '#6C9A6A'
WHITE = '#FFFDF5'; CLOTH = '#F3ECDA'; MOUTH = '#3A1A22'; FLUSH = '#C8574B'
OFF = (3, 3)  # print misregistration of every colour plate

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

# ---------------------------------------------------------------- the rig
DEF = dict(head_tilt=0, pupil_vis=0.40, brow_follow=False, eye_rot=(0, 0), eye_scale=(1, 1), eye_push=0, lid=(0, 0), lid_tilt=(0, 0), gaze=(0, 0), pupil_r=None,
           brow_raise=(0, 0), brow_tilt=(0, 0), brow_arch=(0.10, 0.10), brow_gap=None, brow_dx=(0, 0),
           nose_tilt=0, nose_dx=0, nose_dy=0, flush=False, tip_flush=False, bead=False, mouth='none',
           marks=(), hair_up=0.0, cheek_flush=False, mouth_dx=0)


class Face:
    def __init__(s, cx, cy, hw, hh, skin, nose, eye_w, eye_h, eye_gap, brow_len, brow_th, brow_gap,
                 pupil_r=8, turn=0.0, hair='flicks', seed=1, line=(7, 11), shade='htR', shade_op=0.55,
                 ears=True, egg_k=0.13, rim=6, tuck=6, eye_lift=0, eye_ox=1.08, far_shift=0, jowls=False):
        s.cx, s.cy, s.hw, s.hh, s.skin = cx, cy, hw, hh, skin
        s.nose = nose; s.eye_w, s.eye_h, s.eye_gap = eye_w, eye_h, eye_gap
        s.brow_len, s.brow_th, s.brow_gap = brow_len, brow_th, brow_gap
        s.pupil_r = pupil_r; s.turn = turn; s.hair = hair; s.seed = seed; s.line = line
        s.shade, s.shade_op, s.ears, s.rim, s.tuck = shade, shade_op, ears, rim, tuck
        s.head = egg_pts(cx, cy, hw, hh, egg_k)
        s.fx = cx + turn * hw * 0.25                      # centre line of the features
        s.ny = cy - hh / 2 + hh * nose['y']               # nose centre y
        s.ncx = s.fx + turn * nose['w'] * 0.16
        s.eye_lift = eye_lift; s.eye_ox = eye_ox; s.far_shift = far_shift; s.jowls = jowls

    # -- helpers
    def top_y_at(s, x):
        best = None
        for (x0, y0), (x1, y1) in zip(s.head, s.head[1:] + s.head[:1]):
            if (x0 - x) * (x1 - x) <= 0 and x0 != x1 and min(y0, y1) < s.cy:
                y = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
                best = y if best is None else min(best, y)
        return best if best is not None else s.cy - s.hh / 2

    def nose_geom(s, e):
        n = s.nose; w, h = n['w'], n['h']
        tilt = e['nose_tilt']
        cx = s.ncx + e['nose_dx']; cy = s.ny + e['nose_dy'] - abs(tilt) * 0.5
        # tipping the nose up rotates it toward the facing side
        sgn = -1 if s.turn >= 0 else 1
        if s.turn == 0:
            sgn = -1
        ang = sgn * tilt if not n.get('turned') else tilt
        if n['kind'] == 'button':
            loc = ellipse_pts(cx, cy, w / 2, h / 2, 100)
        else:
            loc = blob_pts(cx, cy, w, h, [(2, 0.06, 0.6), (3, 0.05, 1.9), (5, 0.025, 0.4)], 160)
        pts = xf(loc, ang=ang, c=(cx, cy))
        return dict(pts=pts, c=(cx, cy), ang=ang, w=w, h=h, tilt=tilt)

    def eye_geom(s, side, e):
        i = 0 if side < 0 else 1
        W, H = s.eye_w, s.eye_h
        rx = W / 2; ry = H * 0.375; ox = rx * s.eye_ox
        bcx, bcy = ox, -(H - ry)
        loc = hull(ellipse_pts(bcx, bcy, rx, ry, 80) + [(0, 0)])
        loc = resample(loc, 2.0)
        sc = e['eye_scale'][i]
        far = (s.turn != 0 and side == (1 if s.turn > 0 else -1))
        sxf = 1 - 0.24 * abs(s.turn) if far else 1.0
        ang = side * e['eye_rot'][i]
        tipx = s.fx + side * (s.eye_gap / 2 + e['eye_push'] / 2) + (s.far_shift * side if far else 0)
        tipy = s.ny - s.nose['h'] / 2 + s.tuck - s.eye_lift

        def T(p):
            x, y = p
            x = x * side * sc * sxf; y = y * sc
            x, y = rot((x, y), ang)
            return (x + tipx, y + tipy)

        poly = [T(p) for p in loc]
        out = dict(poly=poly, far=far, sc=sc * (sxf if far else 1))
        lid = e['lid'][i]
        vis = loc
        if lid > 0:
            ly = -H + lid * H
            tt = math.tan(math.radians(e['lid_tilt'][i]))
            fl = lambda p: p[1] - ly - (bcx - p[0]) * tt          # <=0 : covered by lid
            lp = clip_half(loc, fl)
            vis = clip_half(loc, lambda p: -fl(p))
            ch = [p for p in lp if abs(fl(p)) < 1e-6]
            out['lid'] = [T(p) for p in lp]
            if len(ch) >= 2:
                ch = sorted(ch)
                out['chord'] = [T(ch[0]), T(ch[-1])]
        # pupil: gaze is world space -> local; then slide it until it fits the visible white
        pr = e['pupil_r'] or s.pupil_r
        gx, gy = e['gaze']
        gl = rot((gx, gy), -ang); glx, gly = gl[0] * side, gl[1]
        m = math.hypot(glx, gly)
        if m > 1:
            glx, gly = glx / m, gly / m
        prl = pr / (sc * (sxf if far else 1))
        px = bcx + glx * rx; py = bcy + gly * ry
        need = prl + 2.5 / sc
        if lid > 0:
            ly = -H + lid * H
            tt = math.tan(math.radians(e['lid_tilt'][i]))
            py = min(py, ly + (bcx - px) * tt + prl * 0.45) if gly <= 0.2 else py
            need = prl * e['pupil_vis']
        # choose the feasible spot: furthest along the gaze, near the wanted spot
        vis_c = resample(vis, 3.0) if len(vis) > 3 else vis
        xs = [p[0] for p in vis_c]; ys = [p[1] for p in vis_c]
        gm = math.hypot(glx, gly)
        best = None; bscore = -1e9
        stp = 1.5
        yy = min(ys)
        while yy <= max(ys):
            xx = min(xs)
            while xx <= max(xs):
                p = (xx, yy)
                if inner_dist(p, vis_c) >= need:
                    dd = math.hypot(xx - px, yy - py)
                    if gm > 0.5:
                        sc_ = (xx * glx + yy * gly) / gm - 0.25 * dd
                    else:
                        sc_ = -dd
                    if sc_ > bscore:
                        bscore = sc_; best = p
                xx += stp
            yy += stp
        if best is None:
            best = centroid(vis)
        out['pupil'] = T(best); out['pr'] = pr
        out['top'] = min(poly, key=lambda p: p[1])
        out['bc'] = T((bcx, bcy))
        if 'chord' in out:
            out['lidtop'] = min(out['chord'], key=lambda p: p[1])
        return out

    # -- parts
    def draw_ears(s, e, behind=True):
        out = []
        r = s.hh * 0.085
        y = s.cy
        if abs(s.turn) < 0.3:
            if not behind:
                return ''
            for side in (-1, 1):
                x = s.cx + side * (s.hw / 2 - r * 0.25)
                pts = ellipse_pts(x, y, r, r * 1.15, 50)
                inner = stroke(qbez((x + side * r * 0.1, y - r * 0.5), (x + side * r * 0.8, y), (x + side * r * 0.1, y + r * 0.5)), 5, taper=(0.2, 0.2))
                out.append(inked(pts, s.skin, (5, 7), s.seed + 40 + side, inner=''))
                out.append(inner)
        else:
            if behind:
                return ''
            side = -1 if s.turn > 0 else 1
            x = s.cx + side * s.hw * 0.31
            pts = ellipse_pts(x, y + 4, r * 0.95, r * 1.25, 50)
            out.append(inked(pts, s.skin, (5, 8), s.seed + 44))
            out.append(stroke(qbez((x + side * 0.2 * r, y - r * 0.55), (x - side * r * 0.75, y), (x + side * 0.2 * r, y + r * 0.6)), 5, taper=(0.25, 0.25)))
        return ''.join(out)

    def draw_hair(s, e):
        out = []
        if s.hair == 'flicks':
            up = e['hair_up']
            hx = s.cx - s.turn * s.hw * 0.08
            for k, (dx, ln, a) in enumerate([(-0.075, 0.13, -24), (0.0, 0.155, -6), (0.075, 0.125, 14)]):
                x = hx + dx * s.hw
                y = s.top_y_at(x) + 5
                a2 = a * (1 - up) - s.turn * 12 * (1 - up)
                ln2 = ln * s.hh * (1 + 0.35 * up)
                tip = rot((0, -ln2), a2)
                ctl = rot((0, -ln2 * 0.55), a2 * 0.3 + (8 if a >= 0 else -8))
                pts = qbez((x, y), (x + ctl[0], y + ctl[1]), (x + tip[0], y + tip[1]))
                out.append(stroke(pts, s.line[1] * 1.15, taper=(0.02, 0.85), wmin=0.12))
        return ''.join(out)

    def draw_fringe(s, e):
        """gray fringe = ink halftone, on the back of a bald head."""
        out = []
        sides = [(-1 if s.turn > 0 else 1, 1.0)]
        if abs(s.turn) < 0.3:
            sides = [(-1, 1.0), (1, 1.0)]
        else:
            sides.append((-sides[0][0], 0.45))
        for side, amt in sides:
            # outer = contour points on this side between 33% and 72% height
            seg = [p for p in s.head if (p[0] - s.cx) * side > 0 and s.cy - s.hh * 0.17 < p[1] < s.cy + s.hh * 0.22]
            seg.sort(key=lambda p: p[1])
            if len(seg) < 3:
                continue
            outer = [(p[0] + side * 6, p[1]) for p in seg]
            depth = s.hw * 0.13 * amt
            inner = []
            for j, p in enumerate(seg[::-1]):
                t = j / (len(seg) - 1)
                bump = 1 + 0.45 * math.sin(t * math.pi * 5)
                inner.append((p[0] - side * depth * bump * math.sin(t * math.pi) ** 0.5, p[1]))
            poly = outer + inner
            out.append(f'<path d="{P(xf(poly, *OFF))}" fill="#DCD3C2"/>')
            out.append(clipped(poly, f'<rect x="{f1(s.cx - s.hw)}" y="{f1(s.cy - s.hh)}" width="{f1(s.hw * 2)}" height="{f1(s.hh * 2)}" fill="url(#htKs)"/>', OFF))
            nt = max(3, int(len(inner) / 7))
            for j in range(nt):
                a = inner[int(j * (len(inner) - 1) / nt)]
                b = inner[int((j + 1) * (len(inner) - 1) / nt)]
                mid = ((a[0] + b[0]) / 2 - side * 7, (a[1] + b[1]) / 2)
                out.append(stroke(qbez(a, mid, b, 10), 4.5, taper=(0.35, 0.35)))
        return ''.join(out)

    def draw_mouth(s, e):
        m = e['mouth']
        ng = s.nose_geom(e)
        x = ng['c'][0] + e['mouth_dx']; nb = ng['c'][1] + ng['h'] / 2
        sc = s.hw / 230.0
        out = []
        if m == 'o':
            pts = ellipse_pts(x, nb + 16 * sc, 11 * sc, 13 * sc, 40)
            out.append(inked(pts, MOUTH, (4, 6), 3, off=(0, 0)))
        elif m == 'gape':
            w = 150 * sc; d = 120 * sc; top = nb - 6 * sc
            pts = [(x - w / 2, top)] + [(x + w / 2 * math.cos(t), top + d * math.sin(t)) for t in [math.pi * k / 40 for k in range(0, 41)]][::-1]
            pts = [(x + w / 2, top)] + [(x + w / 2 * math.cos(t), top + d * math.sin(t)) for t in [math.pi * k / 40 for k in range(0, 41)]]
            tongue = ellipse_pts(x + 8 * sc, top + d * 0.86, w * 0.30, d * 0.24, 50)
            teeth = [(x - w * 0.42, top), (x + w * 0.42, top), (x + w * 0.40, top + 14 * sc), (x - w * 0.40, top + 14 * sc)]
            inner = clipped(pts, f'<path d="{P(tongue)}" fill="{ROSE}"/><path d="{P(teeth)}" fill="{WHITE}"/>')
            out.append(f'<path d="{P(pts)}" fill="{MOUTH}"/>')
            out.append(inner)
            out.append(f'<path d="{ring_d(pts, 6, 9, 0.6, 7)}" fill="{INK}" fill-rule="evenodd"/>')
        elif m == 'grit':
            w = 130 * sc; h = 40 * sc; top = nb + 2 * sc
            rr = 10 * sc
            pts = []
            for cxr, cyr, a0 in [(x + w / 2 - rr, top + rr, -90), (x + w / 2 - rr, top + h - rr, 0), (x - w / 2 + rr, top + h - rr, 90), (x - w / 2 + rr, top + rr, 180)]:
                for k in range(10):
                    a = math.radians(a0 + 9 * k)
                    pts.append((cxr + rr * math.cos(a), cyr + rr * math.sin(a)))
            out.append(f'<path d="{P(xf(pts, *OFF))}" fill="{WHITE}"/>')
            lines = [stroke([(x - w / 2 + 4, top + h / 2), (x + w / 2 - 4, top + h / 2)], 4, taper=(0.05, 0.05))]
            for k in range(1, 6):
                xx = x - w / 2 + w * k / 6
                lines.append(stroke([(xx, top + 3), (xx + 1, top + h - 3)], 4, taper=(0.1, 0.1)))
            out.append(''.join(lines))
            out.append(f'<path d="{ring_d(pts, 5, 8, 0.6, 9)}" fill="{INK}" fill-rule="evenodd"/>')
        elif m == 'curl':
            sd = 1
            p0 = (x + sd * ng['w'] * 0.10, nb - 6 * sc)
            p1 = (x + sd * ng['w'] * 0.62, nb + 22 * sc)
            p2 = (x + sd * ng['w'] * 0.92, nb - 16 * sc)
            out.append(stroke(qbez(p0, p1, p2), 10 * sc, taper=(0.0, 0.45)))
            out.append(stroke(qbez(p2, (p2[0] + 8 * sc, p2[1] - 2 * sc), (p2[0] + 6 * sc, p2[1] - 10 * sc), 8), 6 * sc, taper=(0.0, 0.9)))
        elif m == 'wavy':
            y = nb + 24 * sc
            pts = [(x - 34 * sc + 68 * sc * t, y + 6 * sc * math.sin(t * math.pi * 4)) for t in (k / 40 for k in range(41))]
            out.append(stroke(pts, 7 * sc, taper=(0.15, 0.15)))
        elif m == 'flat':
            y = nb + 20 * sc
            out.append(stroke([(x - 22 * sc, y), (x + 22 * sc, y + 1)], 7 * sc, taper=(0.2, 0.2)))
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
            out.append(stroke([a, b], s.rim * 1.25, taper=(0.04, 0.04), wmin=0.6))
        out.append(f'<path d="{P(g["poly"])}" fill="none" stroke="{INK}" stroke-width="{s.rim}" stroke-linejoin="round"/>')
        return ''.join(out), g

    def draw_nose(s, e):
        ng = s.nose_geom(e)
        pts = ng['pts']; cx, cy = ng['c']; w, h = ng['w'], ng['h']; ang = ng['ang']
        base = s.nose['fill']
        fill = FLUSH if e['flush'] else base
        inner = crescent(pts, 'htR' if e['flush'] else s.nose.get('shade', 'htR'), -w * 0.16, -h * 0.18, 0.75 if e['flush'] else 0.55)
        if e['tip_flush']:
            front = -1 if s.turn < 0 else 1
            blot = ellipse_pts(cx + front * w * 0.18, cy + h * 0.10, w * 0.36, h * 0.34, 50)
            blot = xf(blot, ang=ang, c=(cx, cy))
            inner += clipped(pts, f'<path d="{P(blot)}" fill="{FLUSH}"/>', OFF)
            inner += clipped(blot, f'<rect x="{f1(cx - w)}" y="{f1(cy - h)}" width="{f1(2 * w)}" height="{f1(2 * h)}" fill="url(#htR)"/>')
        # shine
        hl = xf(ellipse_pts(cx - w * 0.17, cy - h * 0.2, w * 0.13, h * 0.09, 30), ang=ang - 20, c=(cx, cy))
        inner += f'<path d="{P(hl)}" fill="{WHITE}" fill-opacity="0.9"/>'
        out = [inked(pts, fill, (s.line[0] - 1, s.line[1] - 2), s.seed + 7, inner=inner)]
        if ng['tilt'] > 4:
            nos = []
            if abs(s.turn) < 0.3:
                nos = [(-w * 0.17, h * 0.26), (w * 0.17, h * 0.26)]
            else:
                front = 1 if s.turn > 0 else -1
                nos = [(front * w * 0.12, h * 0.27), (-front * w * 0.16, h * 0.29)]
            for k, (dx, dy) in enumerate(nos):
                p = rot((cx + dx, cy + dy), ang, (cx, cy))
                rr = w * (0.085 if k == 0 else 0.065)
                out.append(f'<ellipse cx="{f1(p[0])}" cy="{f1(p[1])}" rx="{f1(rr)}" ry="{f1(rr * 0.62)}" transform="rotate({f1(ang)} {f1(p[0])} {f1(p[1])})" fill="{MOUTH}"/>')
        if e['bead']:
            tip = rot((cx + w * 0.05, cy + h / 2 + 2), ang, (cx, cy))
            dp = drop_pts(tip[0], tip[1] + h * 0.42, h * 0.38)
            out.append(inked(dp, CYAN, (3, 4.5), 5, bias=0.5, off=(2, 2)))
            out.append(f'<ellipse cx="{f1(tip[0] - h * 0.06)}" cy="{f1(tip[1] + h * 0.36)}" rx="{f1(h * 0.05)}" ry="{f1(h * 0.08)}" fill="{WHITE}"/>')
        return ''.join(out)

    def draw_brows(s, e, geoms):
        out = []
        gap = s.brow_gap if e['brow_gap'] is None else e['brow_gap']
        for side, i in ((-1, 0), (1, 1)):
            g = geoms[i]
            L = s.brow_len * (0.78 if g['far'] else 1)
            cxb = g['bc'][0] + side * e['brow_dx'][i]
            basey = g['lidtop'][1] if (e['brow_follow'] and 'lidtop' in g) else g['top'][1]
            cyb = basey - gap - e['brow_raise'][i]
            ang = -side * e['brow_tilt'][i]
            arch = e['brow_arch'][i]
            a = (cxb - side * L / 2, cyb); b = (cxb + side * L / 2, cyb); cc = (cxb, cyb - arch * L * 2)
            pts = xf(qbez(a, cc, b, 30), ang=ang, c=(cxb, cyb))
            # never let a brow cross the centre line of the face
            lim = s.fx + side * 4
            over = max(0.0, max((lim - p[0]) * side for p in pts))
            pts = [(p[0] + side * over, p[1]) for p in pts]
            # a brow either sits inside the head or clearly floats above it - never on the outline
            band_in = s.brow_th / 2 + 6; band_out = s.brow_th / 2 + 9
            dn = 0.0; upv = 0.0; hit = False
            for p in pts:
                ty = s.top_y_at(p[0])
                if ty - band_out < p[1] < ty + band_in:
                    hit = True
                dn = max(dn, ty + band_in - p[1])
                upv = max(upv, p[1] - (ty - band_out))
            if hit:
                shift = dn if dn <= 34 * s.hw / 230.0 else -upv
                pts = [(p[0], p[1] + shift) for p in pts]
            out.append(stroke(pts, s.brow_th, taper=(0.18, 0.4), wmin=0.3))
        return ''.join(out)

    def draw_jowls(s, e):
        if not s.jowls:
            return ''
        ng = s.nose_geom(e)
        cx, cy = ng['c']; w, h = ng['w'], ng['h']
        back = 1 if s.turn < 0 else -1
        out = []
        # cheek fold behind the nose
        p0 = (cx + back * w * 0.72, cy - h * 0.05)
        p1 = (cx + back * w * 0.98, cy + h * 0.55)
        p2 = (cx + back * w * 0.80, cy + h * 1.0)
        out.append(stroke(qbez(p0, p1, p2), 6, taper=(0.35, 0.5)))
        return ''.join(out)

    def draw_marks(s, e):
        out = []
        sc = s.hw / 230.0
        for mk in e['marks']:
            kind = mk[0]
            if kind == 'excl':
                x, y, k = mk[1], mk[2], mk[3]
                bar = [(x - 13 * k, y - 50 * k), (x + 15 * k, y - 52 * k), (x + 5 * k, y + 14 * k), (x - 3 * k, y + 14 * k)]
                bar = spline(bar, True, 6)
                out.append(inked(bar, INK, (2, 3), 1, off=(0, 0)))
                out.append(inked(ellipse_pts(x + 0.5 * k, y + 32 * k, 9 * k, 9 * k, 30), INK, (2, 3), 2, off=(0, 0)))
            elif kind == 'emanata':
                cx, cy, R, n0 = s.cx, s.cy - s.hh * 0.18, mk[1], mk[2] if len(mk) > 2 else 0
                for a in (-150, -128, -52, -30):
                    ar = math.radians(a)
                    p0 = (cx + math.cos(ar) * R, cy + math.sin(ar) * R * 1.05)
                    p1 = (cx + math.cos(ar) * (R + 46 * sc), cy + math.sin(ar) * (R + 46 * sc) * 1.05)
                    out.append(stroke([p0, p1], 9 * sc, taper=(0.1, 0.6)))
            elif kind == 'vein':
                x, y, r = mk[1], mk[2], mk[3]
                for q in range(4):
                    a0 = q * 90 + 45
                    ca = math.radians(a0)
                    qc = (x + math.cos(ca) * r * 0.95, y + math.sin(ca) * r * 0.95)
                    arc = []
                    for t in range(13):
                        aa = math.radians(a0 + 180 - 55 + 110 * t / 12)
                        arc.append((qc[0] + math.cos(aa) * r * 0.62, qc[1] + math.sin(aa) * r * 0.62))
                    out.append(stroke(arc, r * 0.42, color=INK, taper=(0.15, 0.15), wmin=0.5))
                    out.append(stroke(arc, r * 0.24, color=ROSE, taper=(0.2, 0.2), wmin=0.4))
            elif kind == 'sweat':
                x, y, size, ang = mk[1], mk[2], mk[3], mk[4]
                dp = drop_pts(x, y, size, ang)
                out.append(inked(dp, CYAN, (3, 4.5), 9, bias=0.5, off=(2, 2)))
                hl = rot((x - size * 0.15, y - size * 0.05), ang, (x, y))
                out.append(f'<circle cx="{f1(hl[0])}" cy="{f1(hl[1])}" r="{f1(size * 0.12)}" fill="{WHITE}"/>')
            elif kind == 'speed':
                x, y, ln = mk[1], mk[2], mk[3]
                out.append(stroke([(x, y), (x + ln, y)], 5, taper=(0.1, 0.8)))
        return ''.join(out)

    def draw_cheeks(s, e):
        if not e['cheek_flush']:
            return ''
        out = []
        for side in (-1, 1):
            if s.turn != 0 and side == (1 if s.turn > 0 else -1):
                continue
            x = s.ncx + side * (s.nose['w'] * 0.5 + s.hw * 0.1)
            y = s.ny + s.nose['h'] * 0.15
            pts = ellipse_pts(x, y, s.hw * 0.11, s.hh * 0.06, 40)
            out.append(clipped(pts, f'<rect x="{f1(x - 60)}" y="{f1(y - 60)}" width="120" height="120" fill="url(#htR)"/>'))
        return ''.join(out)

    def draw(s, E):
        e = dict(DEF); e.update(E)
        out = [f'<g transform="rotate({e["head_tilt"]} {f1(s.cx)} {f1(s.cy)})">', s.draw_ears(e, behind=True)]
        # head
        head = s.head
        inner = crescent(head, s.shade, -s.hw * 0.10, -s.hh * 0.07, s.shade_op)
        if s.hair == 'fringe':
            inner += s.draw_fringe(e)
            # bald shine
            sh = ellipse_pts(s.cx - s.hw * 0.12 - s.turn * s.hw * 0.08, s.cy - s.hh * 0.36, s.hw * 0.16, s.hh * 0.05, 40)
            inner += f'<path d="{P(xf(sh, ang=-14, c=(s.cx, s.cy - s.hh * 0.36)))}" fill="{WHITE}" fill-opacity="0.85"/>'
        out.append(inked(head, s.skin, s.line, s.seed, inner=inner))
        out.append(s.draw_ears(e, behind=False))
        out.append(s.draw_hair(e))
        out.append(s.draw_cheeks(e))
        out.append(s.draw_jowls(e))
        out.append(s.draw_mouth(e))
        geoms = []
        for side in (-1, 1):
            svg, g = s.draw_eye(side, e)
            out.append(svg); geoms.append(g)
        out.append(s.draw_nose(e))
        out.append(s.draw_brows(e, geoms))
        out.append(s.draw_marks(e))
        out.append('</g>')
        return ''.join(out)


# ---------------------------------------------------------------- BIX in the expression sheet
def bix_sheet_rig(cx, cy):
    return Face(cx, cy, 230, 300, '#B07A55',
                dict(kind='button', w=70, h=54, y=0.55, fill='#9E6A49'),
                64, 96, 12, 60, 10, 26, pupil_r=8, turn=0.0, hair='flicks', seed=3)

SHEET = [
    ('neutral', dict(gaze=(0, 0.15))),
    ('surprised', dict(eye_scale=(1.4, 1.4), eye_push=8, pupil_r=6, gaze=(0, 0.1), brow_raise=(40, 40), brow_arch=(0.16, 0.16),
                       mouth='gape', hair_up=1.0, marks=[('excl', 300, 70, 1.0), ('emanata', 150)])),
    ('angry', dict(eye_rot=(-14, -14), eye_push=8, lid=(0.30, 0.30), lid_tilt=(30, 30), gaze=(0, 0.25),
                   brow_gap=-6, brow_tilt=(30, 30), brow_arch=(0.02, 0.02), brow_dx=(-4, -4),
                   flush=True, mouth='grit', marks=[('vein', 268, 150, 22)])),
    ('smug', dict(nose_tilt=12, lid=(0.45, 0.45), lid_tilt=(-6, -6), gaze=(0, 0), brow_raise=(10, -16), brow_arch=(0.2, 0.0), brow_tilt=(-8, 10),
                  mouth='curl')),
    ('panic', dict(eye_rot=(18, 18), pupil_r=6, gaze=(0, -0.1), brow_tilt=(-26, -26), brow_raise=(16, 16), brow_arch=(0.12, 0.12),
                   bead=True, mouth='wavy', marks=[('sweat', 66, 120, 26, -40), ('sweat', 300, 110, 30, 38), ('sweat', 312, 200, 20, 60)])),
    ('side-eye', dict(lid=(0.55, 0.55), gaze=(1, 0.0), pupil_vis=0.85, nose_dx=7, brow_gap=4, brow_arch=(0.0, 0.0), brow_tilt=(-3, 3),
                      marks=[('sweat', 74, 168, 22, -25)])),
]

def collar(cx, top):
    """neck + shirt collar + vest + rose bow tie under a sheet head."""
    out = []
    neck = [(cx - 26, top - 40), (cx + 26, top - 40), (cx + 30, top + 26), (cx - 30, top + 26)]
    out.append(inked(neck, '#B07A55', (6, 8), 21))
    vest = spline([(cx - 150, 545), (cx - 128, top + 52), (cx - 60, top + 26), (cx, top + 98), (cx + 60, top + 26), (cx + 128, top + 52), (cx + 150, 545)], False, 10)
    vest = vest + [(cx + 160, 560), (cx - 160, 560)]
    shirt = [(cx - 60, top + 22), (cx + 60, top + 22), (cx, top + 100)]
    out.append(f'<path d="{P(xf(shirt, *OFF))}" fill="{CLOTH}"/>')
    out.append(inked(vest, INK, (6, 9), 22, off=(0, 0)))
    for k in (0, 1):
        sd = -1 if k == 0 else 1
        cp = [(cx + sd * 4, top + 22), (cx + sd * 52, top + 16), (cx + sd * 40, top + 50)]
        out.append(inked(spline(cp, True, 6), CLOTH, (4, 6), 23 + k))
    bow_l = spline([(cx, top + 34), (cx - 40, top + 18), (cx - 44, top + 50), (cx, top + 40)], True, 6)
    bow_r = xf(bow_l, sx=-1, c=(cx, 0))
    out.append(inked(bow_l, ROSE, (4, 6), 25))
    out.append(inked(bow_r, ROSE, (4, 6), 26))
    out.append(inked(ellipse_pts(cx, top + 37, 11, 12, 30), ROSE, (4, 5), 27))
    for k in range(3):
        out.append(f'<circle cx="{cx + 2}" cy="{top + 116 + 26 * k}" r="5" fill="{CREAM}"/>')
    return ''.join(out)

def build_faces():
    W = H = 1080
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{common_defs()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    for k, (name, E) in enumerate(SHEET):
        col, row = k % 3, k // 3
        ox, oy = col * 360, row * 540
        g = [f'<g transform="translate({ox},{oy})">']
        cid = uid('cell')
        g.append(f'<clipPath id="{cid}"><rect x="0" y="0" width="360" height="540"/></clipPath><g clip-path="url(#{cid})">')
        g.append(collar(180, 430))
        rig = bix_sheet_rig(180, 260)
        g.append(rig.draw(E))
        g.append('</g></g>')
        out.append(''.join(g))
    # thin cyan rules between cells
    for x in (360, 720):
        out.append(f'<rect x="{x - 1}" y="18" width="2" height="1044" fill="{CYAN}" opacity="0.35"/>')
    out.append(f'<rect x="18" y="539" width="1044" height="2" fill="{CYAN}" opacity="0.35"/>')
    out.append(grain(W, H))
    out.append('</svg>')
    return ''.join(out)


# ---------------------------------------------------------------- SCENE
def awning():
    out = []
    y0, y1, yv = 236, 384, 420
    sw = 60
    x = -20; k = 0
    while x < 1100:
        col = CYAN if k % 2 == 0 else CREAM
        # stripe + scallop
        pts = [(x, y0), (x + sw, y0), (x + sw, y1)] + [(x + sw / 2 + sw / 2 * math.cos(t), y1 + (yv - y1) * math.sin(t)) for t in (math.pi * j / 20 for j in range(21))] + [(x, y1)]
        out.append(f'<path d="{P(xf(pts, *OFF))}" fill="{col}"/>')
        out.append(stroke([(x, y0 + 4), (x, y1 + 2)], 4, taper=(0.05, 0.05)))
        sc = [(x + sw / 2 + sw / 2 * math.cos(t), y1 + (yv - y1) * math.sin(t)) for t in (math.pi * j / 20 for j in range(21))]
        out.append(stroke(sc, 8, taper=(0.1, 0.1), wmin=0.5))
        x += sw; k += 1
    # shading band under the bar
    out.append(clipped([(0, y0), (1080, y0), (1080, y0 + 34), (0, y0 + 34)], f'<rect x="0" y="{y0}" width="1080" height="40" fill="url(#htCs)" opacity="0.6"/>'))
    out.append(f'<rect x="-10" y="{y0 - 14}" width="1100" height="16" fill="{ROSE}"/>')
    out.append(stroke([(-10, y0 - 15), (1090, y0 - 15)], 7, taper=(0, 0)))
    out.append(stroke([(-10, y0 + 2), (1090, y0 + 2)], 9, taper=(0, 0)))
    return ''.join(out)

def window():
    out = []
    x0, y0, x1, y1 = 590, 452, 1100, 792
    glass = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    out.append(f'<path d="{P(glass)}" fill="#DCE7E6"/>')
    out.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#htCs)" opacity="0.75"/>')
    # reflection streaks
    for a, b in ((660, 70), (760, 26)):
        st = [(a, y1), (a + b, y1), (a + b + 200, y0), (a + 200, y0)]
        out.append(clipped(glass, f'<path d="{P(st)}" fill="#EEF2EC"/>'))
    out.append(inked(glass, None, (8, 12), 61))
    out.append(stroke([(x0 + 255, y0), (x0 + 255, y1)], 9, taper=(0, 0)))
    # sill
    sill = [(x0 - 16, y1 - 2), (x1, y1 - 2), (x1, y1 + 18), (x0 - 16, y1 + 18)]
    out.append(inked(sill, CREAM, (6, 8), 62))
    return ''.join(out)

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

SKIN_B = '#B07A55'
SKIN_G = '#E8C3A0'

def bix_body():
    out = []
    # legs + shoes
    for k, (x0, x1) in enumerate([(252, 300), (334, 384)]):
        leg = [(x0, 1500), (x1, 1500), (x1 + 2, 1716), (x0 - 2, 1716)]
        out.append(inked(leg, INK, (6, 8), 110 + k, off=(0, 0)))
        shoe = spline([(x0 - 6, 1712), (x1 + 34, 1708), (x1 + 44, 1736), (x0 - 8, 1742)], True, 8)
        out.append(inked(shoe, INK, (6, 8), 112 + k, off=(0, 0)))
        out.append(stroke(qbez((x1 + 4, 1716), (x1 + 20, 1712), (x1 + 32, 1718), 8), 4, color=CLOTH, taper=(0.3, 0.3)))
    # far arm: tucked behind the back (waiter stance) - only the shoulder/elbow shows
    farm = spline([(214, 960), (184, 1010), (176, 1110), (196, 1180), (232, 1160), (236, 1040)], True, 8)
    out.append(inked(farm, CLOTH, (6, 10), 114, inner=crescent(farm, 'htC', 14, -10, 0.45)))
    # neck
    neck = [(296, 846), (356, 846), (362, 950), (290, 950)]
    out.append(inked(neck, SKIN_B, (6, 8), 117, inner=crescent(neck, 'htR', 18, 0, 0.5)))
    # shirt torso
    torso = spline([(214, 958), (300, 926), (360, 922), (436, 952), (448, 1060), (432, 1270), (226, 1272), (204, 1060)], True, 10)
    out.append(inked(torso, CLOTH, (7, 11), 118))
    # vest
    vest = spline([(214, 958), (300, 936), (330, 1010), (366, 936), (436, 954), (446, 1060), (430, 1268), (384, 1300), (346, 1270), (226, 1272), (206, 1060)], True, 10)
    out.append(inked(vest, INK, (7, 11), 119, off=(0, 0)))
    out.append(clipped(vest, '<rect x="200" y="920" width="70" height="400" fill="url(#htCs)" opacity="0.5"/>'))
    for k in range(4):
        out.append(f'<circle cx="{352 - k * 2}" cy="{1060 + k * 52}" r="7" fill="{CREAM}"/>')
    out.append(stroke([(250, 1150), (300, 1146)], 5, color=CREAM, taper=(0.2, 0.2)))
    # collar + bow tie
    for sd in (-1, 1):
        cp = spline([(330 + sd * 4, 938), (330 + sd * 50, 926), (330 + sd * 38, 966)], True, 6)
        out.append(inked(cp, CLOTH, (4, 6), 120 + sd))
    bl = spline([(332, 948), (288, 928), (284, 972), (332, 958)], True, 6)
    br = spline([(336, 948), (384, 926), (390, 974), (336, 958)], True, 6)
    out.append(inked(bl, ROSE, (5, 7), 122)); out.append(inked(br, ROSE, (5, 7), 123))
    out.append(inked(ellipse_pts(334, 952, 13, 14, 30), ROSE, (4, 6), 124))
    # apron
    apron = spline([(220, 1262), (440, 1262), (452, 1430), (458, 1592), (206, 1596), (210, 1430)], True, 10)
    ain = crescent(apron, 'htC', 30, 0, 0.55) + ''.join(
        clipped(apron, f'<path d="{P([(x, 1300), (x + 14, 1300), (x + 22, 1600), (x + 6, 1600)])}" fill="url(#htCs)"/>') for x in (262, 360))
    out.append(inked(apron, CLOTH, (7, 11), 125, inner=ain))
    out.append(stroke([(214, 1270), (446, 1270)], 9, taper=(0.05, 0.05)))
    # near arm: upper arm down, forearm forward to the saucer, towel over the forearm
    upper = spline([(404, 958), (452, 978), (472, 1080), (474, 1150), (430, 1162), (414, 1060)], True, 8)
    out.append(inked(upper, CLOTH, (7, 10), 126, inner=crescent(upper, 'htC', -12, -10, 0.45)))
    fore = spline([(436, 1124), (480, 1108), (540, 1080), (556, 1108), (492, 1160), (448, 1170)], True, 8)
    out.append(inked(fore, CLOTH, (6, 9), 127, inner=crescent(fore, 'htC', 0, -12, 0.45)))
    towel = spline([(452, 1116), (512, 1096), (530, 1170), (532, 1268), (516, 1290), (470, 1292), (458, 1262), (452, 1170)], True, 8)
    tin = clipped(towel, ''.join(f'<rect x="440" y="{y}" width="110" height="9" fill="{CYAN}"/>' for y in (1246, 1264))) + crescent(towel, 'htC', 16, 0, 0.5)
    out.append(inked(towel, CLOTH, (6, 9), 116, inner=tin))
    out.append(stroke(qbez((452, 1122), (486, 1140), (516, 1104)), 6, taper=(0.1, 0.1)))
    out.append(stroke(qbez((490, 1150), (494, 1210), (488, 1270)), 4, taper=(0.3, 0.3)))
    return ''.join(out)

def bix_hand_front():
    out = []
    # palm peeking under the saucer, fingers fanned to the right
    palm = spline([(486, 1096), (540, 1106), (600, 1100), (626, 1092), (614, 1112), (560, 1124), (500, 1116)], True, 8)
    out.append(inked(palm, SKIN_B, (4, 6), 128))
    for k in range(3):
        x = 572 + k * 14
        out.append(stroke(qbez((x, 1104), (x + 4, 1110), (x + 1, 1117), 6), 3, taper=(0.2, 0.2)))
    return ''.join(out)

def gus_body():
    """legs, torso, far arm (drawn before the head)."""
    out = []
    for k, (xa, xb, xc, xd) in enumerate([(790, 856, 772, 836), (872, 936, 884, 948)]):
        leg = [(xa, 1390), (xb, 1390), (xd, 1716), (xc, 1716)]
        out.append(inked(leg, CYAN, (7, 10), 140 + k, inner=crescent(leg, 'htK', -14, 0, 0.3)))
        shoe = spline([(xc - 46, 1716), (xd + 6, 1708), (xd + 8, 1742), (xc - 52, 1742)], True, 8)
        out.append(inked(shoe, INK, (6, 8), 142 + k, off=(0, 0)))
        out.append(stroke(qbez((xc - 34, 1716), (xc - 18, 1711), (xc - 2, 1714), 8), 4, color=CLOTH, taper=(0.3, 0.3)))
    farm = spline([(866, 1046), (946, 1110), (980, 1212), (940, 1250), (900, 1190), (850, 1120)], True, 8)
    out.append(inked(farm, MUSTARD, (7, 10), 144, inner=clipped(farm, '<rect x="840" y="1030" width="160" height="240" fill="url(#chk)"/>', OFF) + crescent(farm, 'htM', -14, -8, 0.5)))
    neck = [(728, 940), (812, 940), (818, 1030), (722, 1030)]
    out.append(inked(neck, SKIN_G, (6, 8), 145))
    jk = spline([(716, 1010), (800, 984), (880, 1010), (948, 1100), (960, 1250), (950, 1420), (790, 1428), (726, 1330), (688, 1200), (690, 1080)], True, 10)
    jin = clipped(jk, '<rect x="640" y="960" width="360" height="500" fill="url(#chk)"/>', OFF) + crescent(jk, 'htM', -26, -12, 0.55)
    out.append(inked(jk, MUSTARD, (7, 11), 146, inner=jin))
    sv = [(738, 1000), (800, 990), (774, 1110)]
    out.append(inked(sv, CLOTH, (5, 7), 147))
    tie = spline([(770, 1004), (784, 1006), (790, 1090), (776, 1112), (764, 1090)], True, 6)
    out.append(inked(tie, CYAN, (4, 6), 148))
    out.append(stroke(qbez((738, 1002), (760, 1070), (778, 1130)), 7, taper=(0.1, 0.2)))
    out.append(stroke(qbez((806, 992), (800, 1060), (780, 1128)), 7, taper=(0.1, 0.2)))
    for k in range(2):
        out.append(inked(ellipse_pts(796 - k * 6, 1190 + k * 70, 9, 9, 24), CLOTH, (3, 4), 149 + k))
    out.append(stroke(qbez((820, 1300), (860, 1296), (900, 1304)), 6, taper=(0.1, 0.1)))
    return ''.join(out)

def limb(p0, p1, w0, w1, n=10):
    """capsule from p0 (width w0) to p1 (width w1) with round ends."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1
    a = math.atan2(dy, dx)
    pts = []
    for k in range(n + 1):        # round cap at p1
        t = a - math.pi / 2 + math.pi * k / n
        pts.append((p1[0] + math.cos(t) * w1 / 2, p1[1] + math.sin(t) * w1 / 2))
    for k in range(n + 1):        # round cap at p0
        t = a + math.pi / 2 + math.pi * k / n
        pts.append((p0[0] + math.cos(t) * w0 / 2, p0[1] + math.sin(t) * w0 / 2))
    return pts

def gus_arm():
    """near arm: elbow tucked at his side, forearm up to the pinch (drawn after the head)."""
    out = []
    sh, el, wr = (742, 1036), (716, 1150), (650, 980)
    up = limb(sh, el, 58, 52)
    out.append(inked(up, MUSTARD, (7, 10), 151, inner=clipped(up, '<rect x="660" y="990" width="140" height="220" fill="url(#chk)"/>', OFF) + crescent(up, 'htM', -12, -10, 0.5)))
    fore = limb(el, wr, 52, 42)
    out.append(inked(fore, MUSTARD, (7, 10), 152, inner=clipped(fore, '<rect x="620" y="960" width="160" height="230" fill="url(#chk)"/>', OFF) + crescent(fore, 'htM', -10, -6, 0.5)))
    out.append(stroke(qbez((700, 1132), (716, 1160), (738, 1150), 10), 5, taper=(0.3, 0.3)))
    cuff = limb((656, 990), (648, 976), 46, 46, 6)
    out.append(inked(cuff, CLOTH, (5, 7), 153))
    return ''.join(out)

def gus_pinch_back(dcx, dcy, ow):
    """palm + index finger tucked under the right rim, pinky raised."""
    rx = dcx + ow
    out = []
    palm = spline([(rx - 6, dcy + 4), (rx + 30, dcy - 14), (rx + 62, dcy + 18), (rx + 56, dcy + 64), (rx + 40, dcy + 80), (rx + 14, dcy + 76), (rx - 2, dcy + 40)], True, 8)
    out.append(inked(palm, SKIN_G, (5, 8), 154, inner=crescent(palm, 'htR', -8, -8, 0.5)))
    finger = spline([(rx + 6, dcy + 26), (rx - 26, dcy + 30), (rx - 30, dcy + 44), (rx + 8, dcy + 46)], True, 6)
    out.append(inked(finger, SKIN_G, (4, 6), 155))
    return ''.join(out)

def gus_pinch_front(dcx, dcy, ow):
    rx = dcx + ow
    thumb = spline([(rx + 22, dcy - 6), (rx - 6, dcy - 22), (rx - 30, dcy - 18), (rx - 30, dcy - 4), (rx + 6, dcy + 10)], True, 6)
    return inked(thumb, SKIN_G, (4, 7), 156) + stroke(qbez((rx - 26, dcy - 17), (rx - 32, dcy - 11), (rx - 26, dcy - 6), 6), 3, taper=(0.2, 0.2))

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

BIX_SCENE = dict(head_tilt=-4, gaze=(0.35, 1.0), brow_raise=(0, 40), brow_arch=(0.02, 0.24), brow_tilt=(0, -6), lid=(0.2, 0.2))
GUS_SCENE = dict(head_tilt=-8, eye_rot=(-4, -4), lid=(0.30, 0.26), lid_tilt=(22, 22), gaze=(-0.8, 0.7), brow_raise=(-4, 34), brow_tilt=(18, -10),
                 brow_arch=(0.03, 0.22), nose_tilt=18, tip_flush=True, brow_gap=10)
WIT_SCENE = dict(gaze=(-1, 0.2), lid=(0.34, 0.34), brow_gap=6, brow_raise=(6, 0), brow_arch=(0.14, 0.05))

def build_scene(bix_E=None, gus_E=None, wit_E=None):
    W, H = 1080, 1920
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{common_defs()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    out.append(floor())
    out.append(window())
    out.append(awning())
    out.append(shrub())
    out.append(small_table(150, 772, 56, CLOTH, 81))
    wit = Face(966, 560, 150, 180, '#C99A72', dict(kind='button', w=46, h=34, y=0.56, fill='#AD7F5A'),
               34, 50, 7, 30, 6, 12, pupil_r=5, turn=-0.4, hair='fringe', seed=31, line=(5, 7), shade_op=0.45)
    out.append(small_table(966, 742, 112, CLOTH, 82))
    out.append(wit.draw(wit_E or WIT_SCENE))
    out.append(newspaper(862, 556, 1084, 724))
    for x in (872, 1066):
        out.append(inked(ellipse_pts(x, 566, 13, 15, 30), '#C99A72', (4, 6), 165))
    # cast shadows (under everybody)
    out.append(ht_ellipse(330, 1744, 160, 18, INK, 10, 3.6))
    out.append(ht_ellipse(860, 1744, 175, 18, INK, 10, 3.6))
    # GUS
    out.append(gus_body())
    gus = Face(770, 760, 360, 430, SKIN_G, dict(kind='potato', w=150, h=120, y=0.57, fill=PINKNOSE, shade='htR'),
               78, 112, 28, 72, 13, 22, pupil_r=9, turn=-0.85, hair='fringe', seed=21, shade_op=0.5, egg_k=0.15, eye_ox=1.0,
               far_shift=4, jowls=True)
    out.append(gus.draw(gus_E or GUS_SCENE))
    out.append(gus_arm())
    # BIX
    out.append(bix_body())
    bix = Face(320, 690, 300, 390, SKIN_B, dict(kind='button', w=80, h=60, y=0.55, fill='#9E6A49'),
               72, 108, 14, 72, 13, 28, pupil_r=9, turn=0.8, hair='flicks', seed=11)
    out.append(bix.draw(bix_E or BIX_SCENE))
    # the stand-off props
    cup, rim_y, rh = teacup(540, 1030)
    out.append(cup)
    out.append(bix_hand_front())
    out.append(steam(540, rim_y))
    ow, oh = 78, 34
    dcy = rim_y - rh - 20 - (oh + 9)
    out.append(gus_pinch_back(540, dcy, ow))
    out.append(doughnut(540, dcy, ow, oh))
    out.append(gus_pinch_front(540, dcy, ow))
    out.append(glaze_drip(548, dcy + oh + 4, 16))
    out.append(grain(W, H))
    out.append('</svg>')
    return ''.join(out)


if __name__ == '__main__':
    with open(os.path.join(HERE, 'faces.svg'), 'w') as f:
        f.write(build_faces())
    with open(os.path.join(HERE, 'scene.svg'), 'w') as f:
        f.write(build_scene())
    print('ok')
