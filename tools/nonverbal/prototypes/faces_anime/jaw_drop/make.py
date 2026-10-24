#!/usr/bin/env python3
"""Jaw Drop / アゴで語る -- HUGE anime-style eyes on round heads over costume stick bodies.  Hero GEN, partner SNAP.

ONE head rig  head(P):
    one clean skull circle; only Gen's lower face stretches like taffy on a drop (the rubber jaw is his alone).
    anime_eye(): the shared cast construction, back to front -- sclera #FBF6EA, lid shadow band, three-tone iris +
    limbal ring, same-hue pupil, pure-white catchlights (light from screen upper-left), upper lash line (darkest,
    thickest mark, per-character ending), lower lid line, creases / bags / crow's-feet, then the brows.
    Identity per character (GEN_EYE nemuri dome, SNAP_EYE tsurime point, CAMEO_EYE generic), state per expression.
ONE body rig  body(P, pose, S): unchanged proportions from the big-eye round (the eyes grew, the heads did not).
"""
import math, os, random, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
ESP = '#3B2A20'
LATTE = '#C9A27E'
MILK = '#F5EDE0'
CINN = '#A0522D'
PIST = '#A9B87E'
GREEN = '#5E7F49'
CREMA = '#D9B26F'
SKY = '#BFD6DC'
SKYB = '#8EC3D6'          # Snap's sleeveless shirt
VERM = '#C8452F'
GROUND_SH = '#B48D69'
SAND = '#E3D2B4'
WHITE = '#F7F3EA'
WHITE_LINE = '#BDB5A4'
MOUTH = '#5A3324'
CREAM = '#FBF1DA'
STONE = '#8F7B68'
HAIR = '#231A15'
WALL = '#F2E8D6'
ROSE = '#C9675A'
GOLD = '#E0B13C'
WOOD = '#9A6A3C'
INDIGO = '#2F3B57'
INK = '#22150E'
EYE_W = '#FDF8EE'

SKIN_G, LINE_G, RIM_G, TINT_G = '#E9C29C', '#A67C58', '#6E4C34', '#3E2C22'
SKIN_S, LINE_S, RIM_S, TINT_S = '#A06E4C', '#6A4430', '#3F2618', '#2E2420'
STUB_S = '#583D2F'

UID = [0]


def uid(p='u'):
    UID[0] += 1
    return '%s%d' % (p, UID[0])


def hx(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def tohex(t):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v)))) for v in t)


def dark(c, k=0.35):
    r, g, b = hx(c)
    return tohex((r * (1 - k), g * (1 - k), b * (1 - k)))


def mix(a, b, t):
    A, B = hx(a), hx(b)
    return tohex(tuple(A[i] + (B[i] - A[i]) * t for i in range(3)))


def f(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def rot_pt(p, ang, piv):
    if not ang:
        return p
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    x, y = p[0] - piv[0], p[1] - piv[1]
    return (piv[0] + x * c - y * s, piv[1] + x * s + y * c)


def poly(points, closed=True):
    d = 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in points)
    return d + (' Z' if closed else '')


def _cr(p, closed):
    n = len(p)
    segs = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = p[(i - 1) % n] if (closed or i > 0) else p[i]
        p1 = p[i]
        p2 = p[(i + 1) % n]
        p3 = p[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, c1, c2, p2))
    return segs


def smooth(p, closed=True):
    d = 'M%s,%s' % (f(p[0][0]), f(p[0][1]))
    for p1, c1, c2, p2 in _cr(p, closed):
        d += ' C%s,%s %s,%s %s,%s' % (f(c1[0]), f(c1[1]), f(c2[0]), f(c2[1]), f(p2[0]), f(p2[1]))
    return d + (' Z' if closed else '')


def sample_smooth(p, m=8, closed=True):
    out = []
    for p1, c1, c2, p2 in _cr(p, closed):
        for k in range(m):
            t = k / m
            a = (1 - t) ** 3
            b = 3 * (1 - t) ** 2 * t
            c = 3 * (1 - t) * t * t
            e = t ** 3
            out.append((a * p1[0] + b * c1[0] + c * c2[0] + e * p2[0], a * p1[1] + b * c1[1] + c * c2[1] + e * p2[1]))
    if not closed:
        out.append(p[-1])
    return out


def ell_d(x, y, rx, ry):
    return 'M%s,%s a%s,%s 0 1 0 %s,0 a%s,%s 0 1 0 %s,0 Z' % (f(x - rx), f(y), f(rx), f(ry), f(2 * rx), f(rx), f(ry), f(-2 * rx))


def shape(d, fill, line=None, lw=6, extra=''):
    line = line or dark(fill)
    return ('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round" '
            'stroke-linecap="round" paint-order="stroke" %s/>' % (d, fill, line, f(2 * lw), extra))


def stroke(d, color, w, extra=''):
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
            'stroke-linejoin="round" %s/>' % (d, color, f(w), extra))


def fill(d, color, extra=''):
    return '<path d="%s" fill="%s" %s/>' % (d, color, extra)


def circle(x, y, r, fillc, line=None, lw=6, extra=''):
    return shape(ell_d(x, y, r, r), fillc, line, lw, extra)


def union(parts, fillc, line=None, lw=6, extra=''):
    line = line or dark(fillc)
    s = ''.join('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>'
                % (d, line, line, f(2 * lw)) for d in parts)
    s += ''.join('<path d="%s" fill="%s"/>' % (d, fillc) for d in parts)
    return '<g %s>%s</g>' % (extra, s)


def limb(center, w0, w1=None):
    w1 = w0 if w1 is None else w1
    pts = center
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = w0 + (w1 - w0) * i / (n - 1)
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    return left + right[::-1]


def limb_prof(center, wfun):
    pts = center
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w = wfun(i / (n - 1))
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    return left + right[::-1]


def Q(a, b, c):
    return 'M%s,%s Q%s,%s %s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1]), f(c[0]), f(c[1]))


def L2(a, b):
    return 'M%s,%s L%s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1]))


def padd(p, v, s=1.0):
    return (p[0] + v[0] * s, p[1] + v[1] * s)


def pdist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    return (dx / L, dy / L)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def bez(a, c, b, t):
    return ((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1])


def inside(pt, pg):
    x, y = pt
    c = False
    n = len(pg)
    for i in range(n):
        x1, y1 = pg[i]
        x2, y2 = pg[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                c = not c
    return c


def col_span(pg, x):
    """min / max y of polygon pg along the vertical line x (None if it misses)."""
    ys = []
    n = len(pg)
    for i in range(n):
        x1, y1 = pg[i]
        x2, y2 = pg[(i + 1) % n]
        if (x1 - x) * (x2 - x) <= 0 and x1 != x2:
            ys.append(y1 + (x - x1) * (y2 - y1) / (x2 - x1))
    return (min(ys), max(ys)) if ys else None


# ---------------------------------------------------------------- marks
def dust(x, y, s=1.0, flip=1):
    puffs = [(-26, 8, 17), (0, -6, 22), (28, 6, 16)]
    parts = [ell_d(x + dx * s * flip, y + dy * s, r * s, r * s) for dx, dy, r in puffs]
    return union(parts, MILK, dark(MILK, 0.32), lw=max(3, 5 * s))


def puff(x, y, s=1.0, flip=-1):
    parts = [ell_d(x + dx * s * flip, y + dy * s, r * s, r * s) for dx, dy, r in [(0, 0, 9), (17, -6, 12), (36, -14, 8)]]
    return union(parts, MILK, dark(MILK, 0.32), lw=max(2.5, 4 * s))


def sweat(x, y, s=1.0, ang=0):
    d = 'M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z' % (
        f(x), f(y - 26 * s),
        f(x + 8 * s), f(y - 12 * s), f(x + 17 * s), f(y + 2 * s), f(x + 15 * s), f(y + 10 * s),
        f(x + 10 * s), f(y + 22 * s), f(x - 10 * s), f(y + 22 * s), f(x - 15 * s), f(y + 10 * s))
    d += ' C%s,%s %s,%s %s,%s Z' % (f(x - 17 * s), f(y + 2 * s), f(x - 8 * s), f(y - 12 * s), f(x), f(y - 26 * s))
    return '<g transform="rotate(%s %s %s)">%s</g>' % (f(ang), f(x), f(y), shape(d, '#DDEFF3', '#7FA9B5', lw=3.5 * s))


def star4(x, y, r, fillc=CREAM, line=None):
    pts = []
    for k in range(8):
        a = math.radians(-90 + k * 45)
        rr = r if k % 2 == 0 else r * 0.30
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return shape(poly(pts), fillc, line or dark(CREMA, 0.35), 2.5)


def ting(bx, by, s=1.0):
    out = star4(bx + 44 * s, by - 30 * s, 17 * s)
    for a in (-150, -112, -74, -36):
        t = math.radians(a)
        p0 = (bx + 30 * s * math.cos(t), by - 6 * s + 30 * s * math.sin(t))
        p1 = (bx + 50 * s * math.cos(t), by - 6 * s + 50 * s * math.sin(t))
        out += stroke(L2(p0, p1), dark(CREMA, 0.4), max(3.5, 5 * s))
    return out


def dotted(d, color=None, w=8, gap=19):
    return stroke(d, color or dark(LATTE, 0.3), w, 'stroke-dasharray="0.1 %s"' % gap)


def ticks(x, y, r0, r1, angs, color, w=6):
    out = ''
    for a in angs:
        t = math.radians(a)
        out += stroke(L2((x + r0 * math.cos(t), y + r0 * math.sin(t)), (x + r1 * math.cos(t), y + r1 * math.sin(t))), color, w)
    return out


def temari(x, y, r, rot=8.0, bell=True):
    """Kiku temari: indigo base thread, eight nested-kite petals of wound thread, gold jiwari lines, obi ring."""
    i = uid('tm')
    lw = max(2.0, r * 0.06)
    out = []
    if bell:
        bx, by = x + r * 0.30, y - r * 1.12
        out.append(stroke(Q((x + r * 0.05, y - r * 0.92), (x + r * 0.10, y - r * 1.25), (bx, by)), VERM, max(3, r * 0.10)))
    out.append(circle(x, y, r, INDIGO, dark(INDIGO, 0.5), lw))
    out.append('<defs><clipPath id="%s"><circle cx="%s" cy="%s" r="%s"/></clipPath></defs>' % (i, f(x), f(y), f(r * 0.97)))
    g = []
    pc = (x - r * 0.06, y - r * 0.08)        # pole slightly off-centre: the ball reads as a sphere
    N = 8
    tw = max(1.6, r * 0.075)
    # obi ring (equator band) first, under the petals
    g.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(x), f(y), f(r * 0.90), VERM, f(r * 0.10)))
    g.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(x), f(y), f(r * 0.84), GOLD, f(max(1.2, r * 0.03))))
    # jiwari: gold division lines from the pole
    for k in range(N):
        a = math.radians(rot + (k + 0.5) * 360 / N)
        g.append(stroke(L2(pc, (x + 1.2 * r * math.cos(a), y + 1.2 * r * math.sin(a))), GOLD, max(1.2, r * 0.03)))
    # nested-kite petals (each kite = wound thread, three colours deep)
    cols_a = [VERM, CREAM, CREMA]
    cols_b = [PIST, CREAM, VERM]
    for k in range(N):
        a = math.radians(rot + k * 360 / N)
        ax_, ay_ = math.cos(a), math.sin(a)
        nx_, ny_ = -ay_, ax_
        L = r * 0.80
        cols = cols_a if k % 2 == 0 else cols_b
        for j, c in enumerate(cols):
            s = 1.0 - j * 0.28
            tip = (pc[0] + ax_ * L * (0.12 + 0.88 * s), pc[1] + ay_ * L * (0.12 + 0.88 * s))
            base = (pc[0] + ax_ * L * 0.10, pc[1] + ay_ * L * 0.10)
            mid = (pc[0] + ax_ * L * (0.12 + 0.46 * s), pc[1] + ay_ * L * (0.12 + 0.46 * s))
            hw_ = L * 0.205 * s
            kite = [base, (mid[0] + nx_ * hw_, mid[1] + ny_ * hw_), tip, (mid[0] - nx_ * hw_, mid[1] - ny_ * hw_)]
            g.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="miter"/>' % (poly(kite), c, f(tw)))
    g.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        f(pc[0]), f(pc[1]), f(r * 0.11), GOLD, dark(GOLD, 0.4), f(max(1.2, r * 0.03))))
    out.append('<g clip-path="url(#%s)">%s</g>' % (i, ''.join(g)))
    out.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(x), f(y), f(r), dark(INDIGO, 0.5), f(lw * 1.4)))
    if bell:
        out.append(circle(bx, by - r * 0.08, r * 0.20, GOLD, dark(GOLD, 0.45), max(1.5, r * 0.05)))
        out.append(stroke(L2((bx - r * 0.10, by - r * 0.02), (bx + r * 0.10, by - r * 0.02)), dark(GOLD, 0.5), max(1.5, r * 0.05)))
    return ''.join(out)


def ghost_ball(x, y, r, op=0.6):
    return ('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.30" stroke="%s" stroke-width="%s" '
            'stroke-dasharray="%s %s" opacity="%s"/>' % (f(x), f(y), f(r), mix(INDIGO, MILK, 0.6), INDIGO, f(max(3, r * 0.12)),
                                                         f(r * 0.32), f(r * 0.22), f(op)))


# ================================================================ ANIME EYES (one construction for the cast)
SCLERA = '#FBF6EA'        # warm off-white, never #FFFFFF
LIDSH = '#DCD3C3'         # lid shadow band over the white
HL = '#FFFFFF'            # catchlights: the only pure white on a face

# per-character eye identity (sizes in D)
GEN_EYE = dict(shape='nemuri', w=0.42, h=0.52, gap=0.10, cy=0.48,
               iris=('#3D42A8', '#282C7A', '#8E92E2', '#1B1D54'), pupil_c='#0C0D27', iris_k=0.75, pupil_k=0.44,
               hl='dot', hl_size=0.10, lash_w=0.058, lash_end='taper', lash_c='#2B1A10', low_line='full', low_w=0.016, low_c='#8A6344',
               edge_c='#8A6344', dome=True, creases=0, crows=True, bags=True, lid_follow=0.10, lid_bow=0.09, cut=0.065)
SNAP_EYE = dict(shape='tsurime', w=0.42, h=0.52, gap=0.08, cy=0.48,
                iris=('#C98227', '#8C4E14', '#F2BC63', '#4E2A0A'), pupil_c='#241004', iris_k=0.78, pupil_k=0.42,
                hl='shard', shard=(0.10, 0.08), hl_second=0.035, lash_w=0.056, lash_end='hook', hook_len=0.04, lash_c='#140C07',
                low_line='outer', low_w=0.018, low_c='#140C07',
                edge_c='#4A2C1C', dome=False, creases=1, crows=False, bags=False, lid_follow=0.35, lid_bow=0.0, cut=0.035)
CAMEO_EYE = dict(shape='generic', w=0.31, h=0.48, gap=0.09, cy=0.52,
                 iris=('#7A5A3A', '#5A3F26', '#A88560', '#3A2816'), pupil_c='#24170C', iris_k=0.76, pupil_k=0.45,
                 hl='dot', hl_size=0.10, lash_w=0.036, lash_end='none', lash_c='#2A1C12', low_line='none', low_w=0.015, low_c='#5A3F26',
                 edge_c='#6B4B33', dome=False, creases=0, crows=False, bags=False, lid_follow=0.0, lid_bow=0.0, cut=0.03)


def foot_shape(kind, w, h):
    """Closed polygon of the fully opened eye footprint, centred on 0; +x = OUTER corner, +y down; bbox exactly w x h."""
    if kind == 'nemuri':
        pts = []
        for k in range(96):
            t = 2 * math.pi * k / 96
            c, s = math.cos(t), math.sin(t)
            pts.append((c * (1 + 0.07 * s), s * (0.92 if s < 0 else 1.0)))
    elif kind in ('generic', 'round'):
        pts = [(math.cos(2 * math.pi * k / 72), math.sin(2 * math.pi * k / 72)) for k in range(72)]
    elif kind == 'tsurime':
        up = [(-0.50, 0.14), (-0.39, -0.15), (-0.19, -0.35), (0.06, -0.45), (0.30, -0.485), (0.50, -0.50)]
        lo = [(0.50, -0.50), (0.455, -0.27), (0.37, 0.02), (0.21, 0.32), (-0.02, 0.50), (-0.26, 0.47), (-0.43, 0.35), (-0.50, 0.14)]
        pts = sample_smooth(up, 10, closed=False)[:-1] + sample_smooth(lo, 10, closed=False)[:-1]
    else:
        raise ValueError(kind)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return [((p[0] - (x0 + x1) / 2) / (x1 - x0) * w, (p[1] - (y0 + y1) / 2) / (y1 - y0) * h) for p in pts]


def var_line(cl, widths, up_frac=0.8):
    """Filled variable-width line along centreline cl (local coords); thickness grows mostly 'up' (away from the opening)."""
    n = len(cl)
    U, Lo = [], []
    for i, p in enumerate(cl):
        a = cl[max(i - 1, 0)]
        b = cl[min(i + 1, n - 1)]
        t = unit(a, b)
        nu = (t[1], -t[0])
        w = widths[i]
        U.append((p[0] + nu[0] * w * up_frac, p[1] + nu[1] * w * up_frac))
        Lo.append((p[0] - nu[0] * w * (1 - up_frac), p[1] - nu[1] * w * (1 - up_frac)))
    return U, Lo


def anime_eye(ex, ey, o, EY, st, D, wk=1.0):
    """One anime eye.  o = world sign of the OUTER corner.  EY = identity, st = state.  Returns (svg, info)."""
    popk = st.get('pop', 1.0)
    h = EY['h'] * D * popk
    w = EY['w'] * D * (1 + 0.35 * (popk - 1)) * wk
    loc = foot_shape(st.get('shape') or EY['shape'], w, h)
    Wp = lambda x, y: (ex + o * x, ey + y)
    out = []

    def ytop(x):
        s_ = col_span(loc, x)
        return s_[0] if s_ else None

    def ybot(x):
        s_ = col_span(loc, x)
        return s_[1] if s_ else None
    c = st.get('lid', 0.3)
    lf = st.get('lid_follow', EY['lid_follow'])
    lt = math.tan(math.radians(st.get('lid_tilt', 0.0)))
    bow = st.get('lid_bow', EY['lid_bow'])
    cl = st.get('low', 0.0)
    lb = st.get('low_bow', 0.0)
    wob = st.get('wobble', 0.0)

    def ylid(x):
        flat = -h / 2 + c * h
        yt = ytop(x)
        fol = (yt if yt is not None else -h / 2) + c * h
        return (1 - lf) * flat + lf * fol - lt * x / wk + bow * h * (2 * x / w) ** 2

    def ylow(x):
        return h / 2 - cl * h - lb * h * (1 - (2 * x / w) ** 2)
    N = 141
    xs = [(-0.5 + (k + 0.5) / N) * w for k in range(N)]
    top, bot = [], []
    for x in xs:
        yt, yb = ytop(x), ybot(x)
        if yt is None:
            continue
        t_ = max(ylid(x), yt)
        b_ = min(ylow(x), yb) if cl > 0.005 else yb
        if t_ < b_ - 0.002 * D:
            top.append((x, t_))
            bot.append((x, b_))
    if len(top) < 3:
        return '', dict(pg=[Wp(*p) for p in loc], top=[], top_y=ey - h / 2, inner=(ex, ey), corner=(ex, ey), foot_top=ey - h / 2, h=h)
    opening = top + bot[::-1]
    op_w = [Wp(*p) for p in opening]
    oid = uid('eo')
    out.append('<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (oid, poly(op_w)))
    lidc = st['lidc']
    # ---- (0) the lid dome: the whole footprint in lid tone, socket line on top (reads as a big, heavy-lidded eye)
    if EY['dome']:
        out.append(fill(poly([Wp(*p) for p in loc]), lidc))
    # ---- (1) sclera
    out.append(fill(poly(op_w), SCLERA))
    # ---- (2) lid shadow band under the upper lash line
    bandh = 0.045 * D
    band = [Wp(x, y) for x, y in top] + [Wp(x, y + bandh) for x, y in top[::-1]]
    out.append('<path d="%s" fill="%s" clip-path="url(#%s)"/>' % (poly(band), LIDSH, oid))
    # ---- (3) iris: three flat tones + limbal ring
    base, shad, light, ring = EY['iris']
    ih = (st['iris_s'] if st.get('iris_s') else EY['iris_k']) * h
    gx, gy = st.get('gaze', (0.0, 0.0))
    iw = 0.87 * ih * wk * (1 - 0.22 * min(1.0, abs(gx)) ** 2)
    t0 = max(ylid(0.0), ytop(0.0))
    b0 = min(ylow(0.0), ybot(0.0)) if cl > 0.005 else ybot(0.0)
    if st.get('float'):
        yc = (t0 + b0) / 2 - 0.01 * D
    else:
        yc = t0 - EY['cut'] * D + ih / 2
        yc = min(yc, b0 + 0.012 * D - ih / 2) if ih < (b0 - t0) + EY['cut'] * D else yc
    # horizontal travel: at |gx| = 1 the iris touches the corner
    half_open = (max(p[0] for p in top) - min(p[0] for p in top)) / 2
    ax = max(0.0, half_open - iw / 2) + 0.01 * D
    icx = ex + gx * ax
    icy = ey + yc + gy * 0.045 * D
    rx, ry = iw / 2, ih / 2
    iid = uid('ei')
    g = ['<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (iid, ell_d(icx, icy, rx, ry))]
    g.append(fill(ell_d(icx, icy, rx, ry), light))
    g.append('<path d="%s" fill="%s" clip-path="url(#%s)"/>' % (ell_d(icx, icy - 0.17 * ih, rx * 1.02, ry), base, iid))
    # darker top third (lower edge bows down a little)
    ytt = icy - ry + ih / 3
    tt = [(icx - rx * 1.1, icy - ry * 1.2), (icx + rx * 1.1, icy - ry * 1.2)] + \
         [(icx + rx * 1.1 - 2.2 * rx * k / 12, ytt + 0.05 * ih * (1 - ((k - 6) / 6) ** 2)) for k in range(13)]
    g.append('<path d="%s" fill="%s" clip-path="url(#%s)"/>' % (poly(tt), shad, iid))
    # lid shadow band over the iris
    g.append('<path d="%s" fill="%s" clip-path="url(#%s)"/>' % (poly(band), shad, iid))
    # ---- (4) pupil
    ph = EY['pupil_k'] * ih
    pw = ph * iw / ih
    g.append(fill(ell_d(icx, icy + 0.02 * ih, pw / 2, ph / 2), EY['pupil_c']))
    # limbal ring
    rw = 0.018 * D
    g.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (ell_d(icx, icy, rx - rw / 2, ry - rw / 2), ring, f(rw)))
    out.append('<g clip-path="url(#%s)">%s</g>' % (oid, ''.join(g)))
    # ---- (5) catchlights -- light from screen upper-left for the whole shot
    def edge_w(xw):
        xl = (xw - ex) * o
        yt = ytop(xl)
        if yt is None:
            return ey - h
        return ey + max(ylid(xl), yt)

    def bot_w(xw):
        xl = (xw - ex) * o
        yb = ybot(xl)
        if yb is None:
            return ey + h
        return ey + (min(ylow(xl), yb) if cl > 0.005 else yb)

    def below_band(x, y, r):
        return max(y, edge_w(x) + 0.045 * D + r * 0.6)
    hls = []
    if st.get('hl_on', True):
        kind = EY['hl']
        if st.get('hl_top'):
            r_ = st.get('hl_top_size', 0.08) * D / 2
            hx_ = icx - 0.30 * iw
            hls.append(fill(ell_d(hx_, below_band(hx_, icy - 0.26 * ih, r_), r_, r_), HL))
        if kind == 'lower_arc':
            # thin arc of light bouncing up from the ball, inside the bottom of the iris
            ra, rb = rx * 0.76, ry * 0.78
            pts = []
            for k in range(13):
                a = math.radians(22 + 56 * k / 12)
                pts.append((icx + 0.02 * iw + ra * math.cos(a), icy + 0.02 * ih + rb * math.sin(a)))
            lim = min(bot_w(p[0]) for p in pts) - 0.034 * D
            sh_ = max(0.0, max(p[1] for p in pts) - lim)
            pts = [(p[0], p[1] - sh_) for p in pts]
            hls.append(stroke(poly(pts, False), HL, 0.026 * D))
        elif kind == 'shard':
            sl_, sw_ = EY.get('shard', (0.085, 0.056))
            L_ = sl_ * D * st.get('hl_k', 1.0)
            bx_ = icx - 0.22 * iw
            bc = (bx_, below_band(bx_, icy - 0.22 * ih, 0.03 * D))
            dv = unit((0, 0), (-o * 0.62, 1.0))
            pv = (-dv[1], dv[0])
            tip = padd(bc, dv, L_ * 0.72)
            b0_ = padd(bc, dv, -L_ * 0.28)
            tri = [tip, padd(b0_, pv, sw_ * D / 2 * st.get('hl_k', 1.0)), padd(b0_, pv, -sw_ * D / 2 * st.get('hl_k', 1.0))]
            hls.append(fill(poly(tri), HL))
        elif kind == 'dot':
            r_ = EY.get('hl_size', 0.07) * D / 2
            hx_ = icx - 0.24 * iw
            hls.append(fill(ell_d(hx_, below_band(hx_, icy - 0.22 * ih, r_), r_, r_), HL))
        if st.get('tear'):
            tp = [(x, y - 0.022 * D) for x, y in bot if -0.34 * w < x < 0.30 * w]
            if len(tp) > 3:
                hls.append(stroke(smooth([Wp(*p) for p in tp[::4]], False), HL, 0.013 * D))
        if st.get('hl_second') or EY.get('hl_second'):
            r2 = (EY.get('hl_second') or 0.032) * D / 2
            hls.append(fill(ell_d(icx + 0.26 * iw, icy + 0.24 * ih, r2, r2), HL))
    if hls:
        out.append('<g clip-path="url(#%s)">%s</g>' % (oid, ''.join(hls)))
    # ---- thin edge where no lash line sits
    out.append(stroke(poly(op_w), EY['edge_c'], 0.011 * D))
    if wob:
        out.append(stroke(poly([(x + o * 0.014 * D, y - 0.006 * D) for x, y in op_w]), EY['edge_c'], 0.009 * D, 'opacity="0.45"'))
    # ---- socket line + creases + age marks (under the lash line)
    sl = st['skin_line']
    sl_soft = mix(sl, lidc, 0.30)
    if EY['dome']:
        sock = [(x, ytop(x)) for x in xs if ytop(x) is not None and abs(x) < 0.46 * w]
        out.append(stroke(smooth([Wp(*p) for p in sock], False), sl_soft, 0.015 * D))
    if EY['creases'] >= 1:
        cr = [(x, y - 0.058 * D) for x, y in top if -0.36 * w < x < 0.40 * w]
        if EY['dome']:
            cr = [(x, y) for x, y in cr if y > ytop(x) + 0.03 * D]
        if len(cr) > 3:
            out.append(stroke(smooth([Wp(*p) for p in cr[::3]], False), sl_soft if EY['dome'] else sl, 0.014 * D))
    # ---- (6) upper lash line: darkest, thickest mark; tapers to the inner corner, ends in the character's ending
    lw_ = EY['lash_w'] * D
    cl_pts = list(top)
    if wob:
        cl_pts = [(x, y + 0.007 * D * math.sin(x / w * 18)) for x, y in cl_pts]
    n = len(cl_pts)
    widths = []
    for i in range(n):
        tt_ = i / (n - 1)
        k_ = 0.38 + 0.62 * min(1.0, tt_ / 0.38) ** 0.8
        if EY['lash_end'] == 'hook':
            k_ *= 1.0 + 0.30 * max(0.0, (tt_ - 0.70) / 0.30)
        if EY['lash_end'] == 'none':
            k_ *= 1.0 - 0.45 * max(0.0, (tt_ - 0.80) / 0.20)
        if EY['lash_end'] == 'taper':
            k_ *= 1.0 - 0.62 * max(0.0, (tt_ - 0.72) / 0.28) ** 1.3
        widths.append(lw_ * k_)
    U, Lo = var_line(cl_pts, widths, 0.78)
    # inner cap
    a0, a1 = cl_pts[0], cl_pts[1]
    ti = unit(a1, a0)
    cap_in = padd(a0, ti, 0.012 * D)
    # outer ending
    e0, e1 = cl_pts[-1], cl_pts[-2]
    te = unit(e1, e0)
    if EY['lash_end'] == 'hook':
        dv = rot_pt(te, -38, (0, 0))
        tip = padd(e0, dv, EY.get('hook_len', 0.075) * D)
        lash = U + [tip] + Lo[::-1] + [cap_in]
        out.append(fill(poly([Wp(*p) for p in lash]), EY['lash_c']))
    elif EY['lash_end'] == 'droop':
        dv = rot_pt(te, 32, (0, 0))
        tip = padd(e0, dv, 0.026 * D)
        lash = U + [padd(U[-1], dv, 0.018 * D), tip] + Lo[::-1] + [cap_in]
        out.append(fill(poly([Wp(*p) for p in lash]), EY['lash_c']))
    else:
        lash = U + [padd(e0, te, 0.012 * D)] + Lo[::-1] + [cap_in]
        out.append(fill(poly([Wp(*p) for p in lash]), EY['lash_c']))
    # ---- (7) lower lash / lid line
    if EY['low_line'] != 'none':
        lo_pts = [(x, y) for x, y in bot]
        if EY['low_line'] == 'outer':
            lo_pts = [(x, y) for x, y in lo_pts if x > -0.08 * w]
            if lo_pts:
                lo_pts = lo_pts + [top[-1]]
        else:
            lo_pts = lo_pts[2:-2]
        if wob:
            lo_pts = [(x, y + 0.006 * D * math.sin(x / w * 16 + 1)) for x, y in lo_pts]
        if len(lo_pts) > 2:
            out.append(stroke(smooth([Wp(*p) for p in lo_pts[::3]] + ([Wp(*lo_pts[-1])] if (len(lo_pts) - 1) % 3 else []), False),
                              EY['low_c'], EY['low_w'] * D))
    if EY.get('crows'):
        cx_, cy_ = top[-1]
        x0 = cx_ + 0.035 * D
        for dy, dx2, dy2 in ((-0.03, 0.065, -0.035), (0.005, 0.07, 0.006), (0.04, 0.055, 0.045)):
            out.append(stroke(L2(Wp(x0, cy_ + dy * D), Wp(x0 + dx2 * D, cy_ + dy * D + dy2 * D)), sl, 0.015 * D))
    if EY.get('bags'):
        bb = [(x, y + 0.04 * D) for x, y in bot if -0.30 * w < x < 0.38 * w]
        if len(bb) > 3:
            out.append(stroke(smooth([Wp(*p) for p in bb[::4]], False), sl, 0.015 * D))
    info = dict(pg=[Wp(*p) for p in loc], top=[Wp(*p) for p in top], top_y=ey + min(y for _, y in top),
                inner=Wp(*top[min(len(top) - 1, int(len(top) * 0.10))]), corner=Wp(*top[-1]),
                foot_top=ey - h / 2, h=h, w=w, iris=(icx, icy, rx, ry), open_h=max(b - t for (_, t), (_, b) in zip(top, bot)),
                open_c=min(ylow(0.0), ybot(0.0)) - max(ylid(0.0), ytop(0.0)) if cl > 0.005 else ybot(0.0) - max(ylid(0.0), ytop(0.0)),
                lid_cov=(max(ylid(0.0), ytop(0.0)) - ytop(0.0)) / h,
                iris_vis=min(icy + ry, bot_w(icx)) - max(icy - ry, edge_w(icx)),
                open_at_iris=bot_w(icx) - edge_w(icx))
    return ''.join(out), info


# ================================================================ HEAD RIG
HDEF = dict(cx=0.0, cy=0.0, D=200.0, face=1, turn=0.10, tilt=0.0,
            skin=SKIN_G, line=LINE_G, rim=RIM_G, lidc=None, ink=INK, lw=None,
            drop=0.0, va=0.20, vm=0.33, pinch=None, jaw_shift=0.0,
            EYE=None, far_k=0.62, pop=1.0, iris_s=None, float=False, hl_on=True, hl_top=False, hl_top_size=0.08, hl_second=False,
            wobble_eye=0.0, hl_k=1.0,
            lid=(0.45, 0.45), lid_tilt=(0.0, 0.0), lid_bow=None, lid_follow=None, low=(0.0, 0.0), low_bow=0.0,
            gaze=(0.0, 0.0), look_at=None, nose_dy=0.0, stache_dy=0.0, beard_dy=0.0,
            brow='cloud', brow_w=0.36, brow_h=0.11, brow_gap=0.055, brow_raise=(0.0, 0.0), brow_tilt=(0.0, 0.0), brow_out=0.02,
            brow_color=WHITE, brow_line=WHITE_LINE, tuft=True,
            nose='aquiline', nose_s=1.0,
            ears=True, ear_s=1.0, ear_p=0.11, ear_pf=0.06, ear_y=0.02, cauli=False,
            hair='waves', hair_color=WHITE, hair_line=WHITE_LINE, hair_wind=0.0,
            beard=0.0, beard_swing=0.0, stache=None,
            mouth='none', mouth_w=0.22, open_w=0.28, corner=0.0, wobble=0.0, teeth_up=0, teeth_low=0, gold=None, tongue=CINN,
            stubble=None, marks=(), crease=False, scar=False, wing=1.0, cleft=False, lid_w=0.036, crease_eye=False)


def head(P):
    """Returns (back_svg, main_svg, info)."""
    d = dict(HDEF)
    d.update(P)
    D = float(d['D'])
    R = D / 2
    face = d['face']
    cx, cy = d['cx'], d['cy']
    lw = d['lw'] or 0.027 * D
    skin, line, rim, ink = d['skin'], d['line'], d['rim'], d['ink']
    lidc = d['lidc'] or mix(skin, line, 0.10)
    turn = d['turn']
    fs = face * turn * D
    s = d['drop'] * D
    va, vm = d['va'] * D, d['vm'] * D
    pinch = d['pinch'] if d['pinch'] is not None else 0.12 * min(1.0, d['drop'] / 0.5)
    shift = d['jaw_shift'] * D
    tops = []
    back, out = [], []

    def frac(v):
        if v <= va:
            return 0.0, 0.0
        if v >= vm:
            return 1.0, 1.0
        t = (v - va) / (vm - va)
        return t * t * (3 - 2 * t), t

    def DSP(u, v):
        fr, t = frac(v)
        k = 1 - pinch * math.sin(math.pi * t) if 0 < t < 1 else 1.0
        return (cx + u * k + shift * fr, cy + v + s * fr)

    def W(u, v):
        return (cx + u, cy + v)

    def CH(u, v):            # rides the chin bulb (full drop)
        return (cx + u + shift, cy + v + s)

    # ---------------------------------------------------- head outline (seamless; stretched below 0.60 D)
    N = 720
    outline = [DSP(R * math.cos(t), R * math.sin(t)) for t in (2 * math.pi * k / N for k in range(N))]
    hd = poly(outline)
    hid = uid('hd')
    tops.append(cy - R - lw)

    # ---------------------------------------------------- back hair (behind the ears and skull)
    hc, hl = d['hair_color'], d['hair_line']
    if d['hair'] == 'waves':
        # white wavy hair streaming back off the rear of the crown: three crests, thin band inside the circle
        a0, a1 = 12.0, 122.0                     # degrees from straight up toward the BACK of the head
        parts = []
        outer, inner = [], []
        for k in range(31):
            aa = math.radians(a0 + (a1 - a0) * k / 30)
            ux, uy = -face * math.sin(aa), -math.cos(aa)
            env = math.sin(math.pi * k / 30) ** 0.7
            ro = R + (0.04 + 0.09 * env) * D
            outer.append(W(ux * ro - face * 0.05 * D * env, uy * ro))
            inner.append(W(ux * (R - 0.04 * D), uy * (R - 0.04 * D)))
        parts.append(smooth(outer + inner[::-1]))
        wind = 1 + d['hair_wind']
        locks = []
        for ang, Ll, wd, lift in ((24, 0.24, 0.20, -0.12), (54, 0.29, 0.22, -0.01), (84, 0.26, 0.21, 0.11), (112, 0.19, 0.17, 0.25)):
            aa = math.radians(ang)
            ux, uy = -face * math.sin(aa), -math.cos(aa)
            root = W(ux * (R - 0.02 * D), uy * (R - 0.02 * D))
            dv = unit((0, 0), (ux * 0.30 - face * 1.0, uy * 0.30 + lift))
            pv = (-dv[1], dv[0])
            cl = []
            for j in range(9):
                t = j / 8
                amp = 0.028 * D * math.sin(2 * math.pi * 1.0 * t) * (0.3 + t)
                cl.append((root[0] + dv[0] * Ll * D * wind * t + pv[0] * amp, root[1] + dv[1] * Ll * D * wind * t + pv[1] * amp - 0.05 * D * t ** 3))
            parts.append(smooth(limb_prof(cl, lambda t, wd=wd: wd * D * (1 - t ** 1.7) + 0.014 * D), True))
            locks.append(cl)
            tops += [p[1] - wd * D / 2 for p in cl]
        back.append(union(parts, hc, hl, max(2.5, lw * 0.7)))
        for cl in locks:
            back.append(stroke(smooth(cl[2:8], False), hl, max(2, 0.012 * D)))
        tops += [p[1] for p in outer]
    elif d['hair'] == 'mullet':
        # long nape tail behind the neck (the top crop is drawn on the head later)
        tl = [(-0.66, -0.30), (-1.06, -0.12), (-1.15, 0.30), (-1.17, 0.66), (-1.30, 0.94), (-1.46, 1.02), (-1.22, 1.07),
              (-1.06, 1.18), (-0.98, 1.01), (-0.84, 1.12), (-0.74, 0.86), (-0.62, 0.40), (-0.58, 0.0)]
        tail = [W(face * x * R, y * R) for x, y in tl]
        back.append(shape(smooth(tail), hc, '#000000', max(2.5, lw * 0.6)))
    elif d['hair'] == 'bun':
        k = W(-face * 0.30 * D, -0.46 * D)
        back.append(circle(k[0], k[1], 0.16 * D, hc, dark(hc, 0.3), lw * 0.8))
        tops.append(k[1] - 0.16 * D - lw)

    # ---------------------------------------------------- ears (skull, never move with the jaw)
    if d['ears']:
        for sg in (-1, 1):
            far = (sg == face) and turn > 0.02
            p = (d['ear_pf'] if far else d['ear_p']) * D
            sc = (0.86 if far else 1.0) * d['ear_s']
            ew, eh = 0.085 * D * sc, 0.13 * D * sc
            ox, oy = sg * (R + p - ew), d['ear_y'] * D
            q = [(ox - sg * ew * 0.6, oy - eh * 0.95), (ox + sg * ew * 0.5, oy - eh * 1.02), (ox + sg * ew, oy - eh * 0.30),
                 (ox + sg * ew * 0.80, oy + eh * 0.60), (ox + sg * ew * 0.20, oy + eh * 1.05), (ox - sg * ew * 0.55, oy + eh * 0.95),
                 (ox - sg * ew * 1.2, oy + eh * 0.2)]
            cauli = d['cauli'] and not far
            if cauli:   # boxer's cauliflower ear: lumpy outer rim
                q = [(ox - sg * ew * 0.6, oy - eh * 0.95), (ox + sg * ew * 0.35, oy - eh * 1.10), (ox + sg * ew * 1.05, oy - eh * 0.62),
                     (ox + sg * ew * 0.92, oy - eh * 0.18), (ox + sg * ew * 1.12, oy + eh * 0.30), (ox + sg * ew * 0.72, oy + eh * 0.82),
                     (ox + sg * ew * 0.15, oy + eh * 1.02), (ox - sg * ew * 0.55, oy + eh * 0.92), (ox - sg * ew * 1.2, oy + eh * 0.2)]
            back.append(shape(smooth([W(*v) for v in q]), skin, line, lw))
            back.append(stroke(Q(W(ox, oy - eh * 0.55), W(ox + sg * ew * 0.85, oy - eh * 0.05), W(ox + sg * ew * 0.05, oy + eh * 0.62)),
                               line, lw * 0.75))
            if cauli:
                back.append(stroke(Q(W(ox + sg * ew * 0.45, oy - eh * 0.45), W(ox + sg * ew * 0.70, oy - eh * 0.25), W(ox + sg * ew * 0.48, oy - eh * 0.05)),
                                   line, lw * 0.6))

    # ---------------------------------------------------- skull
    out.append('<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (hid, hd))
    out.append(shape(hd, skin, line, lw))
    clip = 'clip-path="url(#%s)"' % hid
    mu = fs * 0.85

    # short beard (adult): flat tone hugging the jaw from sideburn to sideburn, its upper edge kept clear of the mouth by an
    # ellipse, a fine hair-tuft edge and a scatter of stubble specks just above it.  Rides the stretch (DSP).
    if d['stubble']:
        sc_ = d['stubble']
        m_ = d['mouth']
        mw_ = d['mouth_w'] * D
        if m_ == 'o':
            mcy, mrx, mry = d['vm'] * D + 0.01 * D, mw_ / 2 + 0.05 * D, mw_ * 1.15 / 2 + 0.032 * D
        elif m_ == 'smirk':
            mcy, mrx, mry = d['vm'] * D - 0.02 * D, mw_ * 0.62 + 0.05 * D, 0.075 * D
        else:
            mcy, mrx, mry = d['vm'] * D, mw_ / 2 + 0.05 * D, 0.06 * D
        mcx = fs * 0.85
        cang = 90 - face * 12
        sb = d.get('beard_band', (0.075, 0.10))          # (sideburn / jaw width, chin width) in D
        outer_, inner = [], []
        a0, a1 = -2.0, 182.0
        nk = 104
        rnd = random.Random(7)
        for k in range(nk + 1):
            ad = a0 + (a1 - a0) * k / nk
            a_ = math.radians(ad)
            dd = min(1.0, abs(ad - cang) / 70.0)
            bw_ = (sb[1] + (sb[0] - sb[1]) * dd ** 1.6) * D
            # sideburns narrow to a soft point toward the top of the ear (no hard horizontal cut)
            e_ = min(ad - a0, a1 - ad)
            if e_ < 24:
                bw_ *= 0.12 + 0.88 * (e_ / 24.0) ** 0.8
            tuft = 0.010 * D * (1 if k % 2 else -0.4) * min(1.0, e_ / 12.0)
            r_in = R - bw_ + tuft
            ux, uy = math.cos(a_), math.sin(a_)
            # clear the mouth: walk the inner point outward until it leaves the clearance ellipse
            while ((ux * r_in - mcx) / mrx) ** 2 + ((uy * r_in - mcy) / mry) ** 2 < 1.0 and r_in < R - 0.035 * D:
                r_in += 0.004 * D
            outer_.append(DSP(ux * (R + 0.03 * D), uy * (R + 0.03 * D)))
            inner.append(DSP(ux * r_in, uy * r_in))
        out.append('<path d="%s" fill="%s" %s/>' % (poly(outer_ + inner[::-1]), sc_, clip))
        specks = []
        for k in range(3, nk - 2, 4):
            p_ = inner[k]
            q_ = DSP(0, 0)
            v_ = unit(p_, q_)
            for j in range(2):
                off = (0.016 + 0.018 * j + 0.006 * rnd.random()) * D
                c_ = padd(p_, v_, off)
                c_ = (c_[0] + (rnd.random() - 0.5) * 0.02 * D, c_[1])
                if ((c_[0] - cx - mcx) / mrx) ** 2 + ((c_[1] - cy - mcy) / mry) ** 2 < 1.0:
                    continue
                specks.append(ell_d(c_[0], c_[1], 0.0085 * D * (1 - 0.35 * j), 0.0085 * D * (1 - 0.35 * j)))
        out.append('<path d="%s" fill="%s" opacity="0.75" %s/>' % (' '.join(specks), sc_, clip))

    # ---------------------------------------------------- mouth
    opened = s > 0.02 * D
    mouth_info = {}
    if opened:
        y0 = cy + vm - 0.014 * D
        y1 = cy + vm + s - 0.012 * D
        hh = y1 - y0
        w = min(d['open_w'] * D, 0.20 * D + 0.55 * s)
        cn = d['corner'] * D
        bul = 0.025 * D
        x0 = cx + mu

        def mp(u, t, extra=0.0):
            return (x0 + u + shift * t, y0 + t * hh + extra)
        hole = [mp(-w / 2, 0.0, cn), mp(-w / 4, 0.0, -0.012 * D), mp(0, 0.0, -0.015 * D), mp(w / 4, 0.0, -0.012 * D), mp(w / 2, 0.0, cn),
                mp(w / 2 + bul, 0.38), mp(w / 2 * 0.86, 0.80), mp(w / 4, 0.98), mp(0, 1.0), mp(-w / 4, 0.98), mp(-w / 2 * 0.86, 0.80),
                mp(-w / 2 - bul, 0.38)]
        if d['wobble']:
            hole2 = []
            for k, p in enumerate(hole):
                hole2.append(p)
            # wavy lower lip (panic): insert a zigzag along the bottom
            hole = hole2[:6] + [mp(w * (0.40 - 0.16 * j), 0.86 + (0.06 if j % 2 else -0.02) + 0.06 * math.sin(j)) for j in range(6)] + hole2[11:]
        hp_ = smooth(hole)
        mid = uid('mh')
        out.append('<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (mid, hp_))
        out.append(shape(hp_, MOUTH, rim, 0.016 * D))
        tc = mp(0, 1.0, -0.055 * D)
        out.append('<path d="%s" fill="%s" clip-path="url(#%s)"/>' % (ell_d(tc[0], tc[1] + 0.02 * D, w * 0.36, min(0.08 * D, 0.40 * hh)), d['tongue'], mid))
        tw_, th_ = 0.068 * D, 0.062 * D
        n = d['teeth_up']
        for k in range(n):
            u = (k - (n - 1) / 2) * tw_ * 1.12
            a = mp(u - tw_ / 2, 0.0, -0.02 * D)
            col = GOLD if d['gold'] == k else CREAM
            out.append('<path d="M%s,%s l%s,0 l0,%s q%s,%s %s,0 Z" fill="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>' % (
                f(a[0]), f(a[1]), f(tw_), f(th_ + 0.02 * D), f(-tw_ / 2), f(th_ * 0.5), f(-tw_), col, dark(col, 0.4), f(max(1.5, 0.008 * D)), mid))
        n = d['teeth_low']
        for k in range(n):
            u = (k - (n - 1) / 2) * tw_ * 1.12
            a = mp(u - tw_ / 2, 1.0, 0.02 * D)
            out.append('<path d="M%s,%s l%s,0 l0,%s q%s,%s %s,0 Z" fill="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>' % (
                f(a[0]), f(a[1]), f(tw_), f(-th_ - 0.02 * D), f(-tw_ / 2), f(-th_ * 0.5), f(-tw_), CREAM, dark(CREAM, 0.4), f(max(1.5, 0.008 * D)), mid))
        # stretch creases (only while open): taffy pull lines in the cheek band, both sides of the mouth
        if s > 0.06 * D:
            for sg in (-1, 1):
                for j in range(2):
                    u = mu + sg * (w / 2 + 0.05 * D + j * 0.055 * D)
                    pts = [DSP(u, va + (vm - va) * k / 10.0) for k in range(1, 10)]
                    out.append(stroke(smooth(pts, False), line, 0.013 * D, 'opacity="%s" %s' % ('0.75' if j == 0 else '0.5', clip)))
        mouth_info = dict(top=(x0, y0), bottom=mp(0, 1.0))
    else:
        m = d['mouth']
        mw = d['mouth_w'] * D
        M = lambda x, y: W(mu + x, vm + y)
        if m == 'line':
            out.append(stroke(Q(M(-mw / 2, -0.004 * D), M(0, 0.014 * D), M(mw / 2, -0.006 * D)), ink, lw * 1.05))
        elif m == 'smirk':
            sg = -face
            out.append(stroke(smooth([M(-sg * 0.45 * mw, 0.004 * D), M(-sg * 0.05 * mw, 0.014 * D), M(sg * 0.32 * mw, 0.0),
                                      M(sg * 0.52 * mw, -0.04 * D)], False), ink, lw * 1.1))
            out.append(stroke(Q(M(sg * 0.60 * mw, -0.075 * D), M(sg * 0.68 * mw, -0.04 * D), M(sg * 0.60 * mw, -0.012 * D)), line, lw * 0.7))
        elif m == 'frown':
            out.append(stroke(Q(M(-mw / 2, 0.03 * D), M(0, -0.03 * D), M(mw / 2, 0.03 * D)), ink, lw * 1.1))
        elif m == 'grit':
            w, h = 0.30 * D, 0.10 * D
            rr = [M(-w / 2, -h / 2), M(w / 2, -h / 2), M(w / 2, h / 2), M(-w / 2, h / 2)]
            out.append(shape(poly(rr), CREAM, ink, lw * 0.55))
            out.append(stroke(L2(M(-w / 2, 0), M(w / 2, 0)), dark(CREAM, 0.45), max(1.5, lw * 0.35)))
            for k in range(1, 5):
                out.append(stroke(L2(M(-w / 2 + k * w / 5, -h / 2), M(-w / 2 + k * w / 5, h / 2)), dark(CREAM, 0.45), max(1.5, lw * 0.35)))
        elif m == 'flat':
            out.append(stroke(L2(M(-mw / 2, 0), M(mw / 2, 0.004 * D)), ink, lw * 1.05))
        elif m == 'o':
            ow, oh = mw, mw * 1.15
            out.append(shape(ell_d(mu + cx, cy + vm + 0.01 * D, ow / 2, oh / 2), MOUTH, ink, lw * 0.45))
        elif m == 'grin':
            sg = -face
            a, b = M(-sg * 0.50 * mw, 0.012 * D), M(sg * 0.50 * mw, -0.045 * D)
            low = M(sg * 0.05 * mw, 0.075 * D)
            gp = 'M%s,%s Q%s,%s %s,%s Q%s,%s %s,%s Z' % (f(a[0]), f(a[1]), f(lerp(a, b, 0.5)[0]), f(lerp(a, b, 0.5)[1] - 0.012 * D),
                                                     f(b[0]), f(b[1]), f(low[0]), f(low[1] + 0.02 * D), f(a[0]), f(a[1]))
            gid = uid('gr')
            out.append('<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (gid, gp))
            out.append(fill(gp, MOUTH))
            t0, t1 = M(-sg * 0.6 * mw, -0.06 * D), M(sg * 0.6 * mw, -0.10 * D)
            out.append('<path d="%s" fill="%s" clip-path="url(#%s)"/>' % (poly([t0, t1, (t1[0], t1[1] + 0.105 * D), (t0[0], t0[1] + 0.105 * D)]), CREAM, gid))
            out.append(stroke(gp, ink, lw * 0.9))
            out.append(stroke(Q(M(sg * 0.56 * mw, -0.085 * D), M(sg * 0.64 * mw, -0.05 * D), M(sg * 0.56 * mw, -0.02 * D)), line, lw * 0.7))

    if d['cleft']:
        a = CH(mu * 0.7, R - 0.085 * D)
        out.append(stroke(Q(a, (a[0] - face * 0.012 * D, a[1] + 0.03 * D), (a[0], a[1] + 0.055 * D)), line, lw * 0.6, clip))

    # ---------------------------------------------------- beard (rides the chin, lags by beard_swing)
    binfo = {}
    if d['beard'] > 0:
        Lb = d['beard']
        bc = fs * 0.75
        prof = [(-0.25, 0.245), (-0.12, 0.262), (0.0, 0.266), (0.12, 0.262), (0.25, 0.245),
                (0.32, 0.30), (0.34, 0.42), (0.29, 0.50 + 0.25 * Lb), (0.17, 0.50 + 0.58 * Lb), (0.075, 0.50 + 0.80 * Lb),
                (0.10, 0.50 + 0.92 * Lb), (0.02, 0.50 + 1.0 * Lb), (-0.07, 0.50 + 0.93 * Lb), (-0.075, 0.50 + 0.80 * Lb),
                (-0.17, 0.50 + 0.58 * Lb), (-0.29, 0.50 + 0.25 * Lb), (-0.34, 0.42), (-0.32, 0.30)]
        piv = (bc, (0.42 + d['beard_dy']) * D)

        bdy = d['beard_dy']

        def BP(u, v):
            v = v + bdy
            uu, vv = bc + u * D * (0.80 if (u * face > 0 and turn > 0.02) else 1.0), v * D
            if vv > piv[1]:
                t = min(1.0, (vv - piv[1]) / ((0.08 + Lb) * D))
                uu, vv = rot_pt((uu, vv), -face * d['beard_swing'] * t ** 0.8, piv)
            return CH(uu, vv)
        bp = [BP(u, v) for u, v in prof]
        out.append(shape(smooth(bp), WHITE, WHITE_LINE, lw * 0.75))
        for su in (-0.16, 0.0, 0.16):
            a = BP(su, 0.34)
            b = BP(su * 0.6, 0.50 + 0.40 * Lb)
            c = BP(su * 0.25, 0.50 + 0.70 * Lb)
            out.append(stroke(Q(a, b, c), WHITE_LINE, max(2, 0.014 * D)))
        # green cord wraps + wooden bead
        for vv in (0.50 + 0.80 * Lb, 0.50 + 0.86 * Lb):
            a, b = BP(-0.10, vv), BP(0.10, vv)
            out.append(stroke(L2(a, b), GREEN, 0.034 * D))
        bead = BP(0.0, 0.50 + 0.83 * Lb)
        out.append(circle(bead[0] + face * 0.01 * D, bead[1], 0.045 * D, WOOD, dark(WOOD, 0.45), max(1.5, 0.012 * D)))
        out.append(stroke(L2((bead[0] - 0.02 * D, bead[1] - 0.015 * D), (bead[0] + 0.0 * D, bead[1] - 0.03 * D)), mix(WOOD, CREAM, 0.6),
                          max(1.5, 0.01 * D)))
        binfo = dict(tip=BP(0.02, 0.50 + 1.0 * Lb), bead=bead)

    # ---------------------------------------------------- top hair on the skull
    if d['hair'] == 'mullet':
        # short crop on top + sides (hairline at 0.17 D, short sideburn), drawn over the skull
        # faded sides (short, skin shows through) behind the crop
        fade = [(-0.56, -0.74), (-0.84, -0.50), (-0.97, -0.30), (-1.0, 0.0), (-0.80, -0.02), (-0.66, -0.32), (-0.45, -0.62)]
        out.append('<path d="%s" fill="%s" opacity="0.45" %s/>' % (smooth([W(face * x * R, y * R) for x, y in fade]), hc, clip))
        # short spiky crew top: high straight hairline, crisp spikes
        pts = []
        hts = [0.02, 0.09, 0.03, 0.12, 0.04, 0.14, 0.04, 0.12, 0.05, 0.13, 0.04, 0.10, 0.03, 0.08, 0.02, 0.05, 0.01]
        for k, hh in enumerate(hts):
            ph = math.radians(60 + k * 6.2 + (3.5 if k % 2 else 0.0))
            r = 1.02 + hh
            pts.append((r * math.cos(ph), -r * math.sin(ph)))
        pts += [(-0.96, -0.30), (-0.84, -0.50), (-0.56, -0.74), (-0.30, -0.82), (-0.12, -0.94), (0.06, -0.86), (0.28, -0.96), (0.47, -0.91)]
        hp = [W(face * x * R, y * R) for x, y in pts]
        out.append(shape(poly(hp), hc, '#000000', max(2.5, lw * 0.55)))
        tops += [p[1] for p in hp]
    elif d['hair'] == 'crop':
        pts = [(-1.04, -0.20), (-0.96, -0.62), (-0.60, -0.96), (0.0, -1.07), (0.60, -0.96), (0.90, -0.62), (0.70, -0.66),
               (0.30, -0.74), (-0.20, -0.72), (-0.70, -0.52)]
        out.append(shape(smooth([W(face * x * R, y * R) for x, y in pts]), hc, dark(hc, 0.3), max(2, lw * 0.6)))
    elif d['hair'] == 'bun':
        pts = [(-1.04, -0.10), (-0.98, -0.55), (-0.62, -0.92), (0.0, -1.06), (0.62, -0.92), (0.95, -0.55), (0.70, -0.62),
               (0.30, -0.70), (0.0, -0.60), (-0.40, -0.55), (-0.80, -0.25)]
        out.append(shape(smooth([W(face * x * R, y * R) for x, y in pts]), hc, dark(hc, 0.3), max(2, lw * 0.6)))

    # ---------------------------------------------------- eyes (anime construction, identity from d['EYE'])
    EY = d['EYE']
    ey = cy - R + EY['cy'] * D
    popk = d['pop']
    w_ = EY['w'] * D * (1 + 0.35 * (popk - 1))
    h_ = EY['h'] * D * popk
    fk = d['far_k'] if turn > 0.02 else 1.0
    wf = w_ * fk
    gap = EY['gap'] * D
    exs = [cx + fs - face * (gap / 2 + w_ / 2), cx + fs + face * (gap / 2 + wf / 2)]   # near, far
    ws = [w_, wf]
    outs = [-face, face]
    eye_pgs, eye_info = [], []
    for i in range(2):
        g = d['gaze']
        if d['look_at'] is not None:
            tx, ty = d['look_at']
            dx, dy = tx - exs[i], ty - ey
            Lg = math.hypot(dx, dy) or 1.0
            k = min(1.0, Lg / (0.8 * D))
            g = (dx / Lg * k * 1.05, dy / Lg * k * 1.05)
        st = dict(lid=d['lid'][i], lid_tilt=d['lid_tilt'][i], low=d['low'][i], low_bow=d['low_bow'], gaze=g, pop=popk,
                  iris_s=d['iris_s'], float=d['float'], shape=d.get('shape'), hl_on=d['hl_on'], hl_top=d['hl_top'], hl_top_size=d['hl_top_size'],
                  hl_second=d['hl_second'], wobble=d['wobble_eye'], tear=d.get('tear', False), lidc=lidc, skin_line=line, hl_k=d['hl_k'])
        if d['lid_bow'] is not None:
            st['lid_bow'] = d['lid_bow']
        if d['lid_follow'] is not None:
            st['lid_follow'] = d['lid_follow']
        svg, inf = anime_eye(exs[i], ey, outs[i], EY, st, D, fk if i == 1 else 1.0)
        out.append(svg)
        eye_pgs.append(inf['pg'])
        eye_info.append(inf)

    # ---------------------------------------------------- nose (skull; fills the eye gap)
    ns = d['nose_s']
    N_ = lambda u, v: W(fs + face * u * D * ns, (v + d['nose_dy']) * D)
    if d['nose'] == 'aquiline':
        p = [(-0.040, -0.085), (0.010, -0.090), (0.052, -0.030), (0.078, 0.030), (0.118, 0.105), (0.125, 0.140), (0.100, 0.170),
             (0.055, 0.176), (0.018, 0.160), (-0.040, 0.180), (-0.098, 0.155), (-0.100, 0.105), (-0.066, 0.075), (-0.052, 0.010),
             (-0.050, -0.050)]
        out.append(shape(smooth([N_(*q) for q in p]), skin, line, lw * 0.8))
        shade = [N_(-0.040, -0.06), N_(-0.050, 0.010), N_(-0.064, 0.075), N_(-0.098, 0.110), N_(-0.090, 0.150), N_(-0.050, 0.150),
                 N_(-0.022, 0.060), N_(-0.020, -0.050)]
        out.append('<path d="%s" fill="%s" opacity="0.35"/>' % (smooth(shade), line))
        out.append(stroke(Q(N_(-0.070, 0.128), N_(-0.046, 0.108), N_(-0.024, 0.140)), line, lw * 0.6))
    elif d['nose'] == 'hook':
        p = [(-0.030, -0.092), (0.012, -0.094), (0.030, -0.030), (0.046, 0.060), (0.080, 0.148), (0.106, 0.200), (0.102, 0.240),
             (0.072, 0.260), (0.030, 0.252), (-0.010, 0.270), (-0.058, 0.266), (-0.088, 0.238), (-0.082, 0.204), (-0.046, 0.184),
             (-0.036, 0.090), (-0.034, 0.000)]
        out.append(shape(smooth([N_(*q) for q in p]), skin, line, lw * 0.8))
        shade = [N_(-0.028, -0.07), N_(-0.034, 0.010), N_(-0.038, 0.090), N_(-0.050, 0.180), N_(-0.080, 0.215), N_(-0.070, 0.245),
                 N_(-0.030, 0.240), N_(-0.012, 0.120), N_(-0.010, -0.050)]
        out.append('<path d="%s" fill="%s" opacity="0.32"/>' % (smooth(shade), line))
        out.append(stroke(Q(N_(-0.062, 0.226), N_(-0.040, 0.206), N_(-0.020, 0.236)), line, lw * 0.6))
    elif d['nose'] == 'boxer2':
        p = [(-0.030, -0.075), (0.020, -0.077), (0.034, -0.022), (0.012, 0.030), (0.042, 0.090), (0.086, 0.150), (0.100, 0.205),
             (0.082, 0.245), (0.036, 0.262), (-0.030, 0.262), (-0.080, 0.248), (-0.098, 0.205), (-0.076, 0.160), (-0.036, 0.110),
             (-0.014, 0.040), (-0.040, -0.012)]
        out.append(shape(smooth([N_(*q) for q in p]), skin, line, lw * 0.8))
        out.append(stroke(Q(N_(-0.070, 0.218), N_(-0.046, 0.198), N_(-0.026, 0.230)), line, lw * 0.6))
        out.append(stroke(Q(N_(0.072, 0.218), N_(0.050, 0.198), N_(0.034, 0.230)), line, lw * 0.6))
        out.append(stroke(Q(N_(0.020, 0.004), N_(0.002, 0.030), N_(0.024, 0.056)), line, lw * 0.55))
    elif d['nose'] == 'boxer':
        p = [(-0.035, -0.12), (0.022, -0.12), (0.045, -0.055), (0.018, -0.005), (0.060, 0.045), (0.105, 0.095), (0.092, 0.150),
             (0.040, 0.168), (-0.030, 0.168), (-0.092, 0.152), (-0.108, 0.098), (-0.060, 0.050), (-0.025, 0.000), (-0.048, -0.055)]
        out.append(shape(smooth([N_(*q) for q in p]), skin, line, lw * 0.8))
        out.append(stroke(Q(N_(-0.075, 0.118), N_(-0.050, 0.100), N_(-0.030, 0.132)), line, lw * 0.6))
        out.append(stroke(Q(N_(0.075, 0.118), N_(0.055, 0.100), N_(0.040, 0.132)), line, lw * 0.6))
        out.append(stroke(Q(N_(0.020, -0.04), N_(0.000, -0.012), N_(0.022, 0.012)), line, lw * 0.55))
    elif d['nose'] == 'button':
        c = N_(0.0, 0.10)
        out.append(shape(ell_d(c[0], c[1], 0.07 * D, 0.06 * D), skin, line, lw * 0.8))

    # ---------------------------------------------------- mustache (upper lip; never moves with the jaw)
    if d['stache']:
        mood = d['stache']
        lift = dict(droop=(0.0, 0.0), lift=(-0.06, -0.06), smug=(0.02, -0.07), bristle=(0.05, 0.05), flat=(-0.02, -0.02),
                    blow=(-0.03, -0.03), sag=(0.06, 0.06))[mood]
        parts = []
        for i, sg in enumerate((-face, face)):
            k = 1.0 if sg == -face or turn < 0.02 else 0.78
            ly = lift[i]
            q = [(0.0, 0.165), (0.10, 0.160), (0.20, 0.175), (0.27, 0.215 + ly), (0.30, 0.265 + ly * 1.6),
                 (0.25, 0.250 + ly * 1.2), (0.16, 0.232), (0.06, 0.236), (0.0, 0.222)]
            if mood == 'bristle':
                q = [(0.0, 0.165), (0.12, 0.155), (0.22, 0.17), (0.31, 0.235), (0.26, 0.232), (0.29, 0.275), (0.20, 0.250),
                     (0.18, 0.272), (0.10, 0.245), (0.0, 0.232)]
            sdy = d['stache_dy']
            parts.append(smooth([W(mu + sg * u * D * k, (v + sdy) * D) for u, v in q]))
        out.append(union(parts, WHITE, WHITE_LINE, max(2, lw * 0.6)))
        sdy = d['stache_dy']
        out.append(stroke(Q(W(mu - 0.012 * D, (0.175 + sdy) * D), W(mu, (0.20 + sdy) * D), W(mu + 0.012 * D, (0.175 + sdy) * D)), WHITE_LINE, max(2, 0.012 * D)))

    # ---------------------------------------------------- brows
    bw, bh = d['brow_w'] * D, d['brow_h'] * D
    eye_top = ey - h_ / 2
    for i in range(2):
        o = outs[i]
        k = ws[i] / w_
        bx = exs[i] + o * d['brow_out'] * D
        by = eye_top - d['brow_gap'] * D - bh / 2 - d['brow_raise'][i] * D
        ang = d['brow_tilt'][i] * o            # + tilt => inner end lower
        bwk = bw * (0.85 + 0.15 * k)
        if d['brow'] == 'cloud':
            parts = []
            for (u, v, r) in ((-0.40, 0.10, 0.36), (-0.16, -0.08, 0.50), (0.10, -0.10, 0.52), (0.34, 0.02, 0.46)):
                px, py = rot_pt((bx + o * u * bwk, by + v * bh), ang, (bx, by))
                parts.append(ell_d(px, py, r * bh, r * bh))
            base = [rot_pt((bx + o * bwk * x, by + bh * y), ang, (bx, by)) for x, y in [(-0.48, 0.30), (0.44, 0.34), (0.46, 0.0), (-0.48, 0.0)]]
            parts.append(poly(base))
            if d['tuft']:
                t0 = rot_pt((bx + o * bwk * 0.42, by + bh * 0.05), ang, (bx, by))
                tip = (t0[0] + o * 0.13 * D, t0[1] - 0.035 * D - 0.4 * d['brow_raise'][i] * D)
                midp = (lerp(t0, tip, 0.5)[0], lerp(t0, tip, 0.5)[1] + 0.02 * D)
                parts.append(smooth(limb([t0, midp, tip], bh * 0.70, bh * 0.12), True))
                tops.append(tip[1] - 3)
            out.append(union(parts, d['brow_color'], d['brow_line'], max(2.5, lw * 0.6)))
            tops.append(by - bh * 0.62 - lw)
        elif d['brow'] == 'bar':
            # thick straight ink bar; its inner end sits ON the upper lash line (pulled-in scowl) unless raised
            inf = eye_info[i]
            a0 = inf['inner']
            lift = EY['lash_w'] * D * 0.70 + d['brow_gap'] * D + d['brow_raise'][i] * D
            Pi = (a0[0] - o * 0.035 * D, a0[1] - lift)
            an = math.radians(d['brow_tilt'][i])
            dv = (o * math.cos(an), -math.sin(an))
            nv = (-math.sin(an) * o, -math.cos(an))
            Lb = bwk
            Po = padd(Pi, dv, Lb)
            q = [Pi, Po, padd(Po, nv, bh * 0.80), padd(Pi, nv, bh)]
            out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                poly(q), d['brow_color'], d['brow_color'], f(0.012 * D)))
            if d.get('scar') and i == 0:
                m0 = padd(Pi, dv, Lb * 0.62)
                out.append(stroke(L2(padd(m0, nv, bh * 1.15), padd(padd(m0, nv, -bh * 0.15), dv, -0.02 * D)), skin, 0.026 * D))
            tops.append(min(p[1] for p in q))
        elif d['brow'] == 'short':
            q = [rot_pt((bx + o * bwk * x * 0.7, by + bh * y), ang, (bx, by)) for x, y in [(-0.5, -0.4), (0.5, -0.4), (0.5, 0.4), (-0.5, 0.4)]]
            out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                poly(q), d['brow_color'], d['brow_color'], f(bh * 0.5)))

    # ---------------------------------------------------- marks
    mk = d['marks']
    if d['crease']:
        x0 = cx + fs
        y = eye_top - 0.06 * D
        out.append(stroke(L2((x0 - 0.02 * D, y - 0.05 * D), (x0 - 0.008 * D, y + 0.01 * D)), line, lw * 0.6))
        out.append(stroke(L2((x0 + 0.02 * D, y - 0.05 * D), (x0 + 0.008 * D, y + 0.01 * D)), line, lw * 0.6))
    if 'sweat' in mk:
        out.append(sweat(cx - face * R * 1.05, cy - R * 0.55, D / 230, -40 * face))
        out.append(sweat(cx + face * R * 1.08, cy - R * 0.25, D / 300, 40 * face))
    if 'pop' in mk:
        for a in (-150, -120, -60, -30):
            t = math.radians(a)
            out.append(stroke(L2((cx + 0.62 * D * math.cos(t), cy + 0.62 * D * math.sin(t)),
                                 (cx + 0.80 * D * math.cos(t), cy + 0.80 * D * math.sin(t))), ink, 0.025 * D))
    if 'shake' in mk:
        for sgn in (-1, 1):
            for j in range(2):
                x0 = cx + sgn * (0.60 + 0.07 * j) * D
                y0 = ey - 0.06 * D + 0.03 * j * D
                ln = (0.16 - 0.04 * j) * D
                out.append(stroke(Q((x0, y0), (x0 + sgn * 0.025 * D, y0 + ln / 2), (x0, y0 + ln)), ink, 0.018 * D))
    if 'sigh' in mk:
        b = W(mu + face * 0.30 * D, vm + 0.05 * D)
        out.append(puff(b[0], b[1], D / 200, face))
    if 'anger' in mk:
        c = W(-face * 0.30 * D, -0.36 * D)
        for a in (0, 90, 180, 270):
            p0 = rot_pt((c[0] + 0.03 * D, c[1] - 0.03 * D), a, c)
            p1 = rot_pt((c[0] + 0.075 * D, c[1] - 0.075 * D), a, c)
            out.append(stroke(Q(p0, rot_pt((c[0] + 0.03 * D, c[1] - 0.075 * D), a, c), p1), VERM, 0.022 * D))

    hang = -face * d['tilt']
    piv = (cx, cy)
    T = lambda p: rot_pt(p, hang, piv)
    bsvg, msvg = ''.join(back), ''.join(out)
    if hang:
        bsvg = '<g transform="rotate(%s %s %s)">%s</g>' % (f(hang), f(piv[0]), f(piv[1]), bsvg)
        msvg = '<g transform="rotate(%s %s %s)">%s</g>' % (f(hang), f(piv[0]), f(piv[1]), msvg)
    crown = T((cx, cy - R))
    info = dict(center=(cx, cy), R=R, D=D, face=face, lw=lw, top=min(tops) if not hang else min(T((cx, t))[1] for t in tops),
                crown=crown, chin=T(CH(fs * 0.3, R)), eyes=[T((x, ey)) for x in exs], mouth=mouth_info, eye_pgs=eye_pgs, eye_info=eye_info,
                eye_cy=EY['cy'], eye_gap=EY['gap'],
                T=T)
    info.update({k: T(v) for k, v in binfo.items()})
    return bsvg, msvg, info


# ================================================================ BODY RIG
def V(a, face):
    """Direction from an angle: 0 = straight down, +90 = toward the facing side, 180 = up, -90 = backward."""
    r = math.radians(a)
    return (face * math.sin(r), math.cos(r))


def ik2(root, target, L1, L2_, hint, straight=False):
    D_ = pdist(root, target)
    u = unit(root, target)
    maxD = (L1 + L2_) * (0.99995 if straight else 0.9965)
    Dc = max(abs(L1 - L2_) + 1.0, min(D_, maxD))
    a = (L1 * L1 - L2_ * L2_ + Dc * Dc) / (2 * Dc)
    h = math.sqrt(max(0.0, L1 * L1 - a * a))
    n = (-u[1], u[0])
    m = padd(root, u, a)
    j1, j2 = padd(m, n, h), padd(m, n, -h)
    hp = padd(m, hint, 1000)
    joint = j1 if pdist(j1, hp) < pdist(j2, hp) else j2
    return joint, padd(root, u, Dc)


def solve_limb(root, spec, L1, L2_, face):
    k = spec.get('k', 1.0)
    L1, L2_ = L1 * k, L2_ * k
    if 'ang' in spec:
        a1, a2 = spec['ang']
        Jn = padd(root, V(a1, face), L1)
        return Jn, padd(Jn, V(a2, face), L2_)
    if 'pts' in spec:
        (jx, jy), (ex, ey) = spec['pts']
        return (root[0] + jx, root[1] + jy), (root[0] + ex, root[1] + ey)
    tgt = spec['to'] if 'to' in spec else padd(root, spec['rel'])
    return ik2(root, tgt, L1, L2_, spec.get('hint', (0, 1)), spec.get('straight', False))


def tube(pts, widths, color, outline=None, olw=0.0):
    out = []
    if outline:
        o = []
        for i in range(len(pts) - 1):
            o.append('<path d="%s"/>' % poly(limb([pts[i], pts[i + 1]], widths[i] + 2 * olw, widths[i + 1] + 2 * olw)))
        for p, w in zip(pts, widths):
            o.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(p[0]), f(p[1]), f(w / 2 + olw)))
        out.append('<g fill="%s">%s</g>' % (outline, ''.join(o)))
    s = []
    for i in range(len(pts) - 1):
        s.append('<path d="%s"/>' % poly(limb([pts[i], pts[i + 1]], widths[i], widths[i + 1])))
    for p, w in zip(pts, widths):
        s.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(p[0]), f(p[1]), f(w / 2)))
    out.append('<g fill="%s">%s</g>' % (color, ''.join(s)))
    return ''.join(out)


def body_spec(D, skin, line, tint, spine=0.97, upper=0.68, fore=0.70, legs=(0.74, 0.70), sh=0.27,
              arm_w=(0.075, 0.062, 0.05), leg_w=(0.078, 0.064, 0.052), arm_col=None, arm_line=None, leg_col=None,
              neck_w=0.18, neck_y=0.71, torso=None, foot_fill=None):
    lw = 0.027 * D
    return dict(D=D, skin=skin, line=line, tint=tint, lw=lw,
                spine=spine * D, upper=upper * D, fore=fore * D, thigh=legs[0] * D, shin=legs[1] * D,
                arm_w=tuple(v * D for v in arm_w), leg_w=tuple(v * D for v in leg_w), spine_w=(0.085 * D, 0.06 * D), sh=sh * D,
                arm_col=arm_col or tint, arm_line=arm_line, leg_col=leg_col or tint,
                hand_L=0.20 * D, hand_W=0.13 * D, hand_lw=max(2.0, 0.022 * D),
                foot_L=0.30 * D, foot_fill=foot_fill or dark(skin, 0.12), foot_line=dark(skin, 0.5), foot_lw=max(2.0, 0.02 * D),
                neck_w=neck_w * D, neck_y=neck_y, torso=torso or {})


def mitten(W_, u, S, thumb_side=-1, scale=1.0, fist=False):
    L, Wd = S['hand_L'] * scale, S['hand_W'] * scale
    n = (-u[1], u[0])

    def P(a, b):
        return (W_[0] + u[0] * a + n[0] * b, W_[1] + u[1] * a + n[1] * b)
    if fist:
        pts = [P(-0.02 * L, -0.45 * Wd), P(0.35 * L, -0.62 * Wd), P(0.72 * L, -0.55 * Wd), P(0.82 * L, -0.05 * Wd),
               P(0.72 * L, 0.48 * Wd), P(0.35 * L, 0.60 * Wd), P(-0.02 * L, 0.45 * Wd)]
    else:
        pts = [P(-0.03 * L, -0.38 * Wd), P(0.40 * L, -0.52 * Wd), P(0.82 * L, -0.46 * Wd), P(1.0 * L, -0.06 * Wd),
               P(0.93 * L, 0.32 * Wd), P(0.60 * L, 0.52 * Wd), P(0.15 * L, 0.48 * Wd), P(-0.03 * L, 0.36 * Wd)]
    paddle = shape(smooth(pts), S['skin'], S['line'], S['hand_lw'])
    s = thumb_side
    c = [P(0.14 * L, s * 0.30 * Wd), P(0.34 * L, s * 0.62 * Wd), P(0.50 * L, s * 0.74 * Wd)] if not fist else \
        [P(0.20 * L, s * 0.40 * Wd), P(0.42 * L, s * 0.55 * Wd), P(0.58 * L, s * 0.40 * Wd)]
    thumb = shape(smooth(limb(c, 0.46 * Wd, 0.38 * Wd), True), S['skin'], S['line'], S['hand_lw'] * 0.85)
    if fist:
        for t in (0.42, 0.62):
            paddle += stroke(L2(P(0.80 * L, (t - 0.5) * Wd * 1.6), P(0.62 * L, (t - 0.5) * Wd * 1.6)), S['line'], S['hand_lw'] * 0.6)
    return paddle, thumb


def foot(An, toe, S, rot=0.0):
    L = S['foot_L']
    h = L * 0.38
    sole = 0.55 * h

    def P(a, b):
        return rot_pt((An[0] + toe * a, An[1] + b), rot * toe, An)
    pts = [P(-0.14 * L, -0.46 * h), P(-0.25 * L, 0.04 * h), P(-0.19 * L, sole), P(0.06 * L, sole + 1), P(0.40 * L, sole + 1),
           P(0.66 * L, sole), P(0.80 * L, 0.36 * h), P(0.80 * L, 0.0), P(0.60 * L, -0.24 * h), P(0.22 * L, -0.42 * h)]
    out = shape(smooth(pts), S['foot_fill'], S['foot_line'], S['foot_lw'])
    for x in (0.56, 0.68):
        a, b = P(x * L, -0.04 * h), P((x + 0.04) * L, 0.30 * h)
        out += stroke(L2(a, b), S['foot_line'], max(2.0, 0.013 * S['D']))
    sole_y = max(p[1] for p in pts) + S['foot_lw']
    return out, sole_y


def ribbon(pts, w0, w1, color, lw=3):
    return shape(smooth(limb(pts, w0, w1), True), color, dark(color, 0.35), lw)


def sash(Hp, up, face, D, color, tails, rx=0.17, band=0.06):
    rx, ry, band = rx * D, 0.05 * D, band * D
    c = padd(Hp, up, 0.03 * D)
    px = (-up[1], up[0])
    if px[0] < 0:
        px = (-px[0], -px[1])
    dn = (-up[0], -up[1])

    def E(t):
        return (c[0] + px[0] * rx * math.cos(t) + dn[0] * ry * math.sin(t),
                c[1] + px[1] * rx * math.cos(t) + dn[1] * ry * math.sin(t))
    line = dark(color, 0.38)

    def arc(pts):
        dd = poly(pts, False)
        return stroke(dd, line, band + 0.024 * D) + stroke(dd, color, band)
    back = arc([E(math.pi + math.pi * k / 16) for k in range(17)])
    front = arc([E(math.pi * k / 16) for k in range(17)])
    k = E(math.pi / 2 - face * 0.55)
    for t in tails:
        front += ribbon([k] + [padd(k, (q[0] * D, q[1] * D)) for q in t], 0.055 * D, 0.03 * D, color, max(2, 0.012 * D))
    front += circle(k[0], k[1], 0.04 * D, color, line, max(2, 0.012 * D))
    return back, front


def wraps(E, W_, D, color, ts=(0.62, 0.80), hw=0.058):
    u = unit(E, W_)
    n = (-u[1], u[0])
    line = dark(color, 0.38)
    out = ''
    for t in ts:
        c = lerp(E, W_, t)
        hw_, ht = hw * D, 0.022 * D
        q = [padd(padd(c, n, hw_), u, -ht), padd(padd(c, n, hw_), u, ht), padd(padd(c, n, -hw_), u, ht), padd(padd(c, n, -hw_), u, -ht)]
        out += shape(poly(q), color, line, max(1.5, 0.01 * D))
    return out


def torso_panel(spine_pts, face, D, tor, lean_pts=None):
    """Costume surface following the spine: polygon left + right edges (world)."""
    pts = list(spine_pts)
    up = tor.get('up', 0.04) * D
    ext = tor.get('ext', 0.06) * D
    t0 = unit(pts[1], pts[0])
    t1 = unit(pts[-2], pts[-1])
    pts = [padd(pts[0], t0, up)] + pts + [padd(pts[-1], t1, ext)]
    knots = tor['w']           # [(t, half-width D), ...]

    def wid(t):
        for (ta, wa), (tb, wb) in zip(knots, knots[1:]):
            if ta <= t <= tb:
                u = (t - ta) / (tb - ta)
                u = u * u * (3 - 2 * u)
                return wa + (wb - wa) * u
        return knots[-1][1]
    off = tor.get('off', 0.0) * D * face
    n = len(pts)
    left, right = [], []
    for i, p in enumerate(pts):
        t = i / (n - 1)
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tg = unit(a, b)
        nr = (-tg[1], tg[0])
        if nr[0] < 0:
            nr = (-nr[0], -nr[1])
        w = wid(t) * D
        left.append((p[0] - nr[0] * w + off, p[1] - nr[1] * w))
        right.append((p[0] + nr[0] * w + off, p[1] + nr[1] * w))
    return left, right, pts


def body(P, pose, S):
    d = dict(HDEF)
    d.update(P)
    D = S['D']
    face = d['face']
    cx, cy = d['cx'], d['cy']
    turnk = min(1.0, d['turn'] / 0.12)
    yo = pose.get('yoke', (0.0, 0.0))
    Y = (cx - face * 0.10 * D * turnk + face * yo[0] * D, cy + S['neck_y'] * D + yo[1] * D - pose.get('shrug', 0.0) * D)
    lean = math.radians(pose.get('lean', 0.0))
    t = (-face * math.sin(lean), math.cos(lean))
    Hh = padd(Y, t, S['spine'] * pose.get('spine_k', 1.0))
    backv = (-face * math.cos(lean), -math.sin(lean))
    mid = lerp(Y, Hh, 0.5)
    ctrl = padd(mid, backv, 2 * pose.get('curve', 0.0) * D)
    spine_pts = [bez(Y, ctrl, Hh, k / 14.0) for k in range(15)]
    t0 = unit(Y, ctrl)
    side = (t0[1], -t0[0])
    if side[0] < 0:
        side = (-side[0], -side[1])
    sh = S['sh'] * pose.get('sh_k', 1.0)
    side = rot_pt(side, pose.get('sh_tilt', 0.0), (0, 0))
    Sn = padd(padd(Y, side, -face * sh), t0, 0.04 * D)
    Sf = padd(padd(Y, side, face * sh * 0.92), t0, 0.04 * D)
    Nb = padd(Y, t0, 0.02 * D)
    Nt = (cx - face * 0.05 * D * turnk, cy + 0.30 * D)
    Jt = dict(Y=Y, H=Hh, Sn=Sn, Sf=Sf, Nb=Nb, Nt=Nt, spine=spine_pts)
    L = {k: '' for k in ('back', 'far_leg', 'far_arm', 'spine', 'neck', 'anchor', 'near_leg', 'front', 'near_arm', 'over')}
    tint = S['tint']
    tor = S['torso']

    # ---- neck stub (skin) with chin shadow
    nw = S['neck_w']
    nq = limb([Nb, Nt], nw, nw * 0.92)
    L['neck'] = shape(poly(nq), S['skin'], S['line'], S['lw'] * 0.8)
    jb = cy + 0.5 * D + max(0.0, d['drop'] * D)
    shp = [(Nb[0] - nw, jb - 0.05 * D), (Nb[0] + nw, jb - 0.05 * D), (Nb[0] + nw, jb + 0.05 * D), (Nb[0] - nw, jb + 0.05 * D)]
    i = uid('nk')
    L['neck'] += ('<defs><clipPath id="%s"><path d="%s"/></clipPath></defs><path d="%s" fill="%s" clip-path="url(#%s)"/>'
                  % (i, poly(nq), poly(shp), dark(S['skin'], 0.14), i))

    # ---- torso costume surface
    if tor and tor['kind'] == 'tank':
        yk = [padd(Sn, (0, -0.06 * D)), padd(Nb, (-face * 0.10 * D, -0.10 * D)), padd(Nb, (face * 0.10 * D, -0.10 * D)), padd(Sf, (0, -0.06 * D)),
              padd(Sf, (0, 0.12 * D)), padd(Sn, (0, 0.12 * D))]
        L['spine'] += shape(smooth(yk), S['skin'], S['line'], S['lw'] * 0.8)
    if tor:
        left, right, tp = torso_panel(spine_pts, face, D, tor)
        col = tor['color']
        ln = dark(col, 0.42)
        pg = left + right[::-1]
        L['spine'] += shape(smooth(pg), col, ln, max(2.5, 0.02 * D))
        tid = uid('to')
        L['spine'] += '<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (tid, smooth(pg))
        cl = 'clip-path="url(#%s)"' % tid
        n = len(tp)
        if tor['kind'] == 'vest':
            # layered collars (重ね襟): espresso under-kimono V, cream + green collar bands
            apex = padd(tp[int(n * 0.42)], (face * 0.05 * D, 0))
            a = padd(padd(Y, side, -face * 0.13 * D), t0, -0.05 * D)
            b = padd(padd(Y, side, face * 0.11 * D), t0, -0.05 * D)
            L['spine'] += '<path d="%s" fill="%s" %s/>' % (poly([a, b, apex]), tor.get('under', ESP), cl)
            for (p0, sgn) in ((a, 1), (b, -1)):
                for k, (c2, wd) in enumerate(((CREAM, 0.040), (GREEN, 0.030))):
                    off = (0.016 + 0.036 * k) * D
                    u = unit(p0, apex)
                    nr = (-u[1] * sgn * (-face), u[0] * sgn * (-face))
                    q0 = padd(p0, nr, off)
                    q1 = padd(apex, nr, off * 0.4)
                    L['spine'] += stroke(L2(q0, lerp(q0, q1, 0.97)), c2, wd * D, cl)
            # vest hem line + front edge
            L['spine'] += stroke(L2(apex, padd(tp[-1], (face * 0.05 * D, 0))), ln, 0.014 * D, cl)
            pk = padd(tp[int(n * 0.66)], (face * 0.14 * D, 0))
            L['spine'] += stroke(L2((pk[0] - 0.06 * D, pk[1]), (pk[0] + 0.06 * D, pk[1])), ln, 0.014 * D, cl)
        elif tor['kind'] == 'tank':
            # scoop neck (skin) + armhole trim; a darker side panel gives the 3/4 turn
            sc = [padd(padd(Y, side, -face * 0.17 * D), t0, -0.06 * D), padd(padd(Y, side, face * 0.15 * D), t0, -0.06 * D),
                  padd(tp[int(n * 0.24)], (face * 0.03 * D, 0))]
            L['spine'] += '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" %s/>' % (smooth(sc), S['skin'], ln, f(0.02 * D), cl)
            side_pg = [padd(q, (0, 0)) for q in (right if face < 0 else left)]
            inner = [lerp(p, q, 0.22) for p, q in zip((right if face < 0 else left), (left if face < 0 else right))]
            L['spine'] += '<path d="%s" fill="%s" opacity="0.55" %s/>' % (poly(side_pg + inner[::-1]), dark(col, 0.18), cl)
            L['spine'] += stroke(poly([lerp(p, q, 0.5) for p, q in zip(left[-4:], right[-4:])], False), ln, 0.012 * D, cl)
        Jt['torso_l'], Jt['torso_r'] = left, right
    else:
        sw0, sw1 = S['spine_w']
        L['spine'] = ('<path d="%s" fill="%s"/>' % (poly(limb(spine_pts, sw0, sw1)), tint))

    # ---- costume anchor at the neck
    anc = pose.get('anchor')
    if anc and anc[0] == 'towel':
        col = anc[1]
        ln = dark(col, 0.4)
        loop = [padd(Sn, (face * 0.06 * D, -0.03 * D)), (Nb[0] - face * 0.12 * D, Nb[1] - 0.10 * D), (Nb[0] + face * 0.13 * D, Nb[1] - 0.10 * D),
                padd(Sf, (-face * 0.05 * D, -0.03 * D)), padd(Sf, (-face * 0.05 * D, 0.05 * D)), (Nb[0], Nb[1] - 0.01 * D),
                padd(Sn, (face * 0.06 * D, 0.05 * D))]
        L['anchor'] += shape(smooth(loop), col, ln, max(2.5, 0.018 * D))
        ends = ''
        for S0, inward, ln_ in ((Sn, face, 0.46), (Sf, -face, 0.40)):
            top = padd(S0, (inward * 0.09 * D, -0.03 * D))
            bot = padd(top, rot_pt((0, 1), -inward * 4 + pose.get('towel_swing', 0) * face, (0, 0)), ln_ * D)
            q = limb([top, bot], 0.13 * D, 0.12 * D)
            ends += shape(poly(q), col, ln, max(2.5, 0.018 * D))
            for tt in (0.80, 0.88):
                c = lerp(top, bot, tt)
                u = unit(top, bot)
                nn = (-u[1], u[0])
                ends += stroke(L2((c[0] + nn[0] * 0.05 * D, c[1] + nn[1] * 0.05 * D), (c[0] - nn[0] * 0.05 * D, c[1] - nn[1] * 0.05 * D)),
                               CREAM, max(2.0, 0.016 * D))
        L['anchor'] += ends

    # ---- legs
    sole = []
    for side_ in ('far', 'near'):
        gspec = pose['legs'][side_]
        K, An = solve_limb(Hh, gspec, S['thigh'], S['shin'], face)
        Jt[side_ + '_knee'], Jt[side_ + '_ankle'] = K, An
        s = tube([Hh, K, An], S['leg_w'], S['leg_col'])
        if gspec.get('wraps'):
            s += wraps(K, An, D, gspec['wraps'], (0.74, 0.86), hw=0.05)
        ft = gspec.get('foot', {})
        if ft is not None:
            fs_, sy_ = foot(An, ft.get('toe', face), S, ft.get('rot', 0))
            s += fs_
            if ft.get('ground', True):
                sole.append(sy_)
        L[gspec.get('layer', side_ + '_leg')] += s
    Jt['sole'] = max(sole) if sole else Hh[1]

    # ---- arms
    sh_pts = dict(near=Sn, far=Sf)
    clasp_hands = []
    for side_ in ('far', 'near'):
        gspec = pose['arms'][side_]
        root = sh_pts[side_]
        if gspec.get('clasp'):
            tgt = padd(Hh, (-face * gspec.get('cx', 0.15) * D, -gspec.get('cy', 0.27) * D))
            hint = (face * (1 if side_ == 'far' else -1), 0.25)
            E, W_ = ik2(root, tgt, S['upper'] * gspec.get('k', 1.0), S['fore'] * gspec.get('k', 1.0), hint)
        else:
            E, W_ = solve_limb(root, gspec, S['upper'], S['fore'], face)
        Jt[side_ + '_elbow'], Jt[side_ + '_wrist'], Jt[side_ + '_sh'] = E, W_, root
        s = tube([root, E, W_], S['arm_w'], S['arm_col'], S['arm_line'], 0.016 * D if S['arm_line'] else 0)
        if gspec.get('wraps'):
            s += wraps(E, W_, D, gspec['wraps'], (0.78, 0.92), hw=0.048)
        u = unit(E, W_)
        if 'hand_dir' in gspec:
            u = unit((0, 0), gspec['hand_dir'])
        if gspec.get('hand_rot'):
            u = rot_pt(u, gspec['hand_rot'], (0, 0))
        tip = padd(W_, u, S['hand_L'])
        Jt[side_ + '_tip'] = tip
        if gspec.get('clasp'):
            clasp_hands.append((W_, u, gspec.get('thumb', -1)))
        elif gspec.get('hand', True):
            pad, th = mitten(W_, u, S, gspec.get('thumb', -1), gspec.get('hand_scale', 1.0), gspec.get('fist', False))
            s += pad + th
        L[pose.get('arm_layer', {}).get(side_, side_ + '_arm')] += s
    for W_, u, th in clasp_hands:
        pad, thb = mitten(W_, u, S, th, 0.95)
        L['far_arm'] += pad + thb

    # ---- hip sash
    hp = pose.get('hip')
    if hp:
        upv = unit(Hh, spine_pts[-4])
        b, fr = sash(Hh, upv, face, D, hp[0], hp[1], hp[2] if len(hp) > 2 else 0.17, hp[3] if len(hp) > 3 else 0.06)
        L['back'] += b
        L['front'] += fr
    return L, Jt


def figure(P, pose, S, over=''):
    L, Jt = body(P, pose, S)
    hb, hm, info = head(P)
    seq = [L['back'], hb, L['far_leg'], L['far_arm'], L['spine'], L['neck'], L['anchor'], L['near_leg'], L['front'],
           L['near_arm'], hm, L['over'], over]
    return ''.join(seq), Jt, info


def report(name, P, Jt, info, S):
    D = S['D']
    Hs = Jt['sole'] - info['top']
    skull = Jt['sole'] - (info['center'][1] - D / 2)
    print('%-14s D=%d H(top incl hair)=%.0f  skull-to-sole %.2f D  head %.1f%%' % (name, D, Hs, skull / D, 100 * D / skull), file=sys.stderr)
    ei = info.get('eye_info') or []
    if ei:
        n_ = ei[0]
        print('   eye footprint %.3f D tall x %.3f D wide (%.1f%% of standing H)  open max %.3f D  centre %.3f D  at iris %.3f D  lid cover %.0f%%'
              % (n_['h'] / D, n_['w'] / D, 100 * n_['h'] / skull, n_['open_h'] / D, n_['open_c'] / D, n_['open_at_iris'] / D, 100 * n_['lid_cov']),
              file=sys.stderr)
        print('   iris %.3f D = %.0f%% of footprint;  visible iris %.3f D = %.0f%% of the open eye at the iris column'
              % (2 * n_['iris'][3] / D, 100 * 2 * n_['iris'][3] / n_['h'], n_['iris_vis'] / D, 100 * n_['iris_vis'] / n_['open_at_iris']), file=sys.stderr)


# ---------------------------------------------------------------- paper + doc
PAPER = ('<filter id="paper" x="0" y="0" width="100%" height="100%">'
         '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="11"/>'
         '<feColorMatrix type="matrix" values="1.2 1.2 1.2 0 -1.3  1.2 1.2 1.2 0 -1.3  1.2 1.2 1.2 0 -1.3  0 0 0 0 1"/>'
         '</filter>'
         '<filter id="black" x="-10%" y="-10%" width="120%" height="120%">'
         '<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>')


def svg_doc(w, h, body_, grain=0.025):
    g = '<rect width="%d" height="%d" filter="url(#paper)" opacity="%s"/>' % (w, h, grain) if grain else ''
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<defs>%s</defs>%s%s</svg>' % (w, h, w, h, PAPER, body_, g))


def sil_doc(w, h, figs):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d"><defs>%s</defs>'
            '<rect width="%d" height="%d" fill="#FFFFFF"/><g filter="url(#black)">%s</g></svg>' % (w, h, w, h, PAPER, w, h, ''.join(figs)))


# ================================================================ cast
def gen_head(**kw):
    """GEN, the master: big sleepy-but-open nemuri eyes (0.52 x 0.42 D) -- a 26 % skin lid with drooping ends, ONE crease
    (the dome edge), indigo irises 75 % of the eye with one clean catchlight, a plain tapered lash line (no wing), white
    cloud brows breaking the rim, white hair streaming back, hook nose in the eye gap, long white beard tied with a green
    cord and a wooden bead, mustache over the rubber jaw (the jaw gag is his alone)."""
    p = dict(skin=SKIN_G, line=LINE_G, rim=RIM_G, EYE=GEN_EYE, lid=(0.26, 0.26), lid_tilt=(-8.0, -8.0),
             brow='cloud', brow_w=0.44, brow_h=0.115, brow_gap=0.012, brow_out=0.05, brow_color=WHITE, brow_line=WHITE_LINE,
             nose='hook', nose_dy=0.0, hair='waves', hair_color=WHITE, hair_line=WHITE_LINE, beard=0.62, beard_dy=0.10,
             stache='droop', stache_dy=0.112, mouth='none', open_w=0.28, teeth_up=0, ear_p=0.10, ear_pf=0.05, va=0.24, vm=0.37,
             lidc=mix(SKIN_G, LINE_G, 0.30))
    p.update(kw)
    return p


def snap_head(**kw):
    """SNAP, the disciple: big tsurime eyes (0.52 x 0.42 D) whose outer corners lift into a point, warm amber/copper irises
    78 % of the eye with an enlarged triangle glint + a small second dot, lids only 17 %, thick straight ink brows sitting
    relaxed and a little raised (eager -- anger only when he is angry), mullet, crooked boxer nose, short adult beard along
    the jaw (mouth area kept clear), cauliflower ear.  No jaw stretch, no teeth (the rubber jaw is Gen's)."""
    p = dict(skin=SKIN_S, line=LINE_S, rim=RIM_S, EYE=SNAP_EYE, lid=(0.21, 0.21), lid_tilt=(2.0, 2.0), scar=True,
             brow='bar', brow_w=0.33, brow_h=0.068, brow_gap=0.035, brow_raise=(0.05, 0.05), brow_tilt=(2.0, 2.0), brow_color=HAIR, cleft=False,
             nose='boxer2', nose_dy=0.0, hair='mullet', hair_color=HAIR, stubble=STUB_S, beard_band=(0.062, 0.095), cauli=True,
             mouth='line', mouth_w=0.18, ear_s=1.12, ear_p=0.10, ear_pf=0.05, va=0.24, vm=0.36, ink='#1B110B', open_w=0.20)
    p.update(kw)
    return p


def gen_spec(D):
    return body_spec(D, SKIN_G, LINE_G, TINT_G, spine=1.0, upper=0.74, fore=0.74, legs=(0.87, 0.83), sh=0.23,
                     arm_w=(0.062, 0.054, 0.046), leg_w=(0.066, 0.056, 0.048), arm_col=ESP, leg_col=ESP, neck_w=0.16, neck_y=0.70,
                     torso=dict(kind='vest', color=PIST, under=ESP, w=[(0.0, 0.17), (0.22, 0.25), (0.70, 0.21), (1.0, 0.23)],
                                up=0.05, ext=0.10, off=0.0))


def snap_spec(D):
    return body_spec(D, SKIN_S, LINE_S, TINT_S, spine=0.86, upper=0.64, fore=0.64, legs=(0.70, 0.66), sh=0.50,
                     arm_w=(0.125, 0.092, 0.072), leg_w=(0.088, 0.072, 0.058), arm_col=SKIN_S, arm_line=LINE_S, leg_col='#2E2A33',
                     neck_w=0.24, neck_y=0.66,
                     torso=dict(kind='tank', color=SKYB, w=[(0.0, 0.22), (0.20, 0.42), (0.72, 0.32), (1.0, 0.30)],
                                up=0.03, ext=0.08, off=0.0))


GEN_HIP = (GREEN, [[(0.04, 0.10), (0.07, 0.22)], [(-0.03, 0.10), (-0.04, 0.20)]], 0.25, 0.065)
SNAP_HIP = (VERM, [[(0.05, 0.12), (0.10, 0.24)], [(-0.02, 0.12), (-0.03, 0.22)]], 0.32, 0.075)


def clasp_arms(cx=0.15, cy=0.27, kf=0.86, kn=1.0):
    return dict(far=dict(clasp=True, cx=cx, cy=cy, k=kf, thumb=1), near=dict(clasp=True, cx=cx, cy=cy, k=kn, thumb=-1))


def stone(x0, x1, top, bottom, top_col=None, body_col=None):
    body_col = body_col or mix(STONE, MILK, 0.30)
    topc = top_col or mix(STONE, MILK, 0.62)
    w = x1 - x0
    bodyp = [(x0 + 10, top + 12), (x0 + w * 0.5, top + 24), (x1 - 8, top + 10), (x1 + 6, (top + bottom) / 2),
             (x1 - 14, bottom), (x0 + w * 0.5, bottom + 6), (x0 + 12, bottom), (x0 - 8, (top + bottom) / 2 + 6)]
    out = shape(smooth(bodyp), body_col, dark(body_col, 0.3), 5)
    tp = [(x0, top + 10), (x0 + w * 0.2, top - 6), (x0 + w * 0.55, top - 10), (x1 - 4, top), (x1 - 10, top + 14),
          (x0 + w * 0.5, top + 24), (x0 + 16, top + 20)]
    out += shape(smooth(tp), topc, dark(body_col, 0.3), 5)
    return out


def cast_shadow(x, y, rx, ry=16, color=None, op=1.0):
    return '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" opacity="%s"/>' % (
        f(x), f(y), f(rx), f(ry), color or mix(SAND, GROUND_SH, 0.55), f(op))


def place(P, pose, S, sole_y):
    P = dict(P)
    _, Jt = body(P, pose, S)
    P['cy'] += sole_y - Jt['sole']
    return P


# ---------------------------------------------------------------- poses
def gen_crane(D, face):
    """Crane stance: far leg straight, near knee up with the foot resting at the standing knee, hands clasped behind."""
    return dict(lean=-3, curve=0.03, hip=GEN_HIP, arms=clasp_arms(0.20, 0.20, 0.82, 0.90),
                legs=dict(far=dict(ang=(2, 0), straight=True, foot=dict(toe=face)),
                          near=dict(ang=(0, 0), foot=None)))


def finish_crane(P, pose, S, raise_k=1.0):
    D = S['D']
    _, J0 = body(P, pose, S)
    hip, kn = J0['H'], J0['far_knee']
    face = P['face']
    pose = dict(pose)
    pose['legs'] = dict(pose['legs'])
    pose['legs']['near'] = dict(pts=((face * 0.46 * D * raise_k, 0.07 * D), (kn[0] - hip[0] + face * 0.05 * D, kn[1] - hip[1] - 0.14 * D)),
                                foot=dict(toe=face, rot=62, ground=False))
    return pose


# ================================================================ scene
def build_scene():
    W, H = 1080, 1920
    bg, fg, sil = [], [], []
    bg.append('<rect width="1080" height="1920" fill="%s"/>' % WALL)
    bg.append('<rect width="1080" height="232" fill="%s"/>' % SKY)
    for x, w_, h_ in ((120, 120, 70), (300, 90, 48), (760, 140, 80), (960, 100, 56)):
        bg.append('<path d="%s" fill="%s"/>' % (smooth([(x - w_ / 2, 232), (x - w_ * 0.3, 232 - h_ * 0.7), (x, 232 - h_),
                                                        (x + w_ * 0.35, 232 - h_ * 0.6), (x + w_ / 2, 232)]), mix(SKY, PIST, 0.45)))
    bg.append('<rect x="0" y="260" width="1080" height="710" fill="%s"/>' % WALL)
    for x0, w_ in ((150, 130), (560, 90), (820, 120)):
        bg.append('<path d="%s" fill="%s" opacity="0.32"/>' % (poly([(x0, 262), (x0 + w_, 262), (x0 + w_ - 230, 970), (x0 - 230, 970)]),
                                                               '#FFF8EA'))
    bg.append('<rect x="0" y="900" width="1080" height="70" fill="%s"/>' % mix(WALL, LATTE, 0.35))
    bg.append(stroke('M0,900 L1080,900', mix(WALL, LATTE, 0.6), 4))
    for x0 in (14, 1024):
        bg.append(shape(poly([(x0, 262), (x0 + 42, 262), (x0 + 42, 975), (x0, 975)]), '#B8977A', dark('#B8977A', 0.3), 3))
    bg.append(shape(poly([(-10, 226), (1090, 226), (1090, 262), (-10, 262)]), ESP, dark(ESP, 0.3), 3))
    for x in range(20, 1080, 64):
        bg.append('<rect x="%d" y="262" width="26" height="12" fill="%s"/>' % (x, mix(ESP, LATTE, 0.3)))

    # ---- cameo witnesses behind the hedge (one generic eye: 0.32 D, 60 % lid, brown iris, single dot; never compete)
    back_figs = []
    cams = [
        dict(x=118, y=470, D=150, face=1, skin='#D8A47E', hair='bun', hcol='#A9A49B', drop=0.30, look=(470, 700), coat='#B8A6C2', sash_c='#7D6A86'),
        dict(x=800, y=488, D=150, face=-1, skin='#7A4E36', hair='crop', hcol='#8E877C', drop=0.36, look=(420, 640), coat='#C9B98E', sash_c=CINN),
        dict(x=968, y=470, D=146, face=-1, skin='#E3B48F', hair='bun', hcol='#2F2620', drop=0.22, look=(420, 640), coat='#9FB3BF', sash_c='#55707E'),
    ]
    for c in cams:
        Dd = c['D']
        S = body_spec(Dd, c['skin'], dark(c['skin'], 0.36), '#4A3C36', spine=0.92, sh=0.24,
                      torso=dict(kind='vest', color=c['coat'], under=dark(c['coat'], 0.5), w=[(0.0, 0.17), (0.25, 0.24), (0.7, 0.21), (1.0, 0.23)]))
        Pd = dict(cx=c['x'], cy=c['y'], D=Dd, face=c['face'], turn=0.10, skin=c['skin'], line=dark(c['skin'], 0.35), rim=dark(c['skin'], 0.6),
                  EYE=CAMEO_EYE, lid=(0.20, 0.20), look_at=c['look'],
                  brow='short', brow_w=0.22, brow_h=0.05, brow_gap=-0.05, brow_raise=(0.0, 0.0), brow_color=dark(c['hcol'], 0.45),
                  hair=c['hair'], hair_color=c['hcol'], hair_line=dark(c['hcol'], 0.3), nose='button', nose_dy=0.03, drop=0.0,
                  mouth='o', mouth_w=0.09, vm=0.33, ear_p=0.09, ear_pf=0.05, stache=None, beard=0)
        pose = dict(lean=-3, curve=0.02, hip=(c['sash_c'], [[(0.03, 0.12), (0.05, 0.22)]], 0.24, 0.05),
                    arms=dict(far=dict(ang=(16, 6), thumb=1), near=dict(ang=(-14, -4), thumb=-1)),
                    legs=dict(far=dict(ang=(5, 2), foot=None), near=dict(ang=(-5, -2), foot=None)))
        g, _, _ = figure(Pd, pose, S)
        back_figs.append(g)
    bg.extend(back_figs)
    sil.extend(back_figs)
    bg.append('<rect x="0" y="262" width="1080" height="710" fill="%s" opacity="0.22"/>' % MILK)

    # pistachio hedge
    hp = [(-30, 1090), (-30, 965)]
    for i in range(24):
        hp.append((-20 + i * 49, 955 + (12 if i % 2 else -8)))
    hp += [(1110, 965), (1110, 1090)]
    hedge = mix(PIST, ESP, 0.12)
    bg.append(shape(smooth(hp), hedge, dark(hedge, 0.3), 4))
    for x, y in ((60, 1010), (230, 1040), (420, 1000), (600, 1036), (800, 1004), (980, 1040)):
        bg.append(stroke('M%d,%d q22,-24 46,-10' % (x, y), dark(hedge, 0.2), 5))
    bg.append('<rect x="0" y="1062" width="1080" height="570" fill="%s"/>' % SAND)
    for k, y in enumerate(range(1110, 1610, 62)):
        bg.append(stroke('M-10,%d C260,%d 620,%d 1090,%d' % (y, y - 8 + k % 2 * 6, y + 10, y - 2), dark(SAND, 0.05), 4))
    bg.append('<rect x="0" y="1622" width="1080" height="298" fill="%s"/>' % GROUND_SH)
    for x, y, r in ((610, 1462, 11), (640, 1478, 7), (930, 1420, 10), (120, 1180, 9), (860, 1130, 8), (180, 1700, 14),
                    (216, 1716, 9), (560, 1790, 12), (900, 1690, 15), (940, 1712, 8)):
        bg.append(shape(ell_d(x, y, r * 1.4, r), mix(SAND, STONE, 0.45) if y < 1622 else dark(GROUND_SH, 0.12), None, 3))

    # ---- GEN: crane stance on his stone; he just flicked the ball off his knee up onto his crown
    Dm = 240
    Sm = gen_spec(Dm)
    snap_hands = (530, 1150)
    Pm = gen_head(cx=300, cy=0, D=Dm, face=1, tilt=8, lid=(0.25, 0.26), lid_tilt=(-8, -8), low=(0.0, 0.0), low_bow=0.0,
                  look_at=snap_hands, brow_raise=(0.0, 0.07), brow_tilt=(-4, 8), stache='smug', beard_swing=-10)
    pose_m = gen_crane(Dm, 1)
    pose_m['lean'] = -6
    Pm = place(Pm, pose_m, Sm, 1588)
    pose_m = finish_crane(Pm, pose_m, Sm, 1.0)
    _, Jm = body(Pm, pose_m, Sm)
    st_top = Jm['sole'] - 16
    bg.append(cast_shadow(Jm['H'][0] + 10, 1619, 210, 14, dark(GROUND_SH, 0.1)))
    bg.append(stone(Jm['H'][0] - 170, Jm['H'][0] + 165, st_top, 1615))
    knee = Jm['near_knee']
    snap_hands = (knee[0] + 0.30 * Dm, knee[1] - 0.10 * Dm)
    Pm['look_at'] = snap_hands
    gm, Jm, mi = figure(Pm, pose_m, Sm)
    fg.append(gm)
    sil.append(gm)
    report('scene gen', Pm, Jm, mi, Sm)
    r_ball = 0.17 * Dm
    crown = mi['crown']
    ball = (crown[0] + 6, crown[1] - r_ball + 4)

    # ---- SNAP: long lunge, both fists clapped on the empty air at Gen's knee; rubber jaw dropped to his chest
    Ds = 240
    Ss = snap_spec(Ds)
    Ps = snap_head(cx=700, cy=0, D=Ds, face=-1, pop=0.56 / 0.52, shape='generic', lid=(0.03, 0.03), lid_tilt=(-4, -4), lid_follow=1.0, iris_s=0.54,
                   float=True, hl_k=1.0, look_at=ball, brow_raise=(0.10, 0.10), brow_tilt=(-9, -9), mouth='o', mouth_w=0.10, vm=0.34, marks=('pop',))
    sd = 0.0
    pose_s = dict(lean=10, curve=0.05, anchor=('towel', CINN), hip=SNAP_HIP, towel_swing=10,
                  arms=dict(near=dict(to=(snap_hands[0] + 6, snap_hands[1] + 12), straight=False, hint=(0, 1), thumb=1, hand_dir=(-1, 0.15), fist=False,
                                      wraps=CREAM),
                            far=dict(to=(snap_hands[0] + 10, snap_hands[1] - 14), hint=(0.2, -1), thumb=-1, hand_dir=(-1, -0.1), wraps=CREAM)),
                  legs=dict(near=dict(rel=(0.95 * Ds, 1.18 * Ds), straight=True, hint=(1, -1), foot=dict(toe=-1, rot=40), wraps=CINN),
                            far=dict(rel=(-0.62 * Ds, 1.05 * Ds), hint=(-1, -0.4), foot=dict(toe=-1), wraps=CINN)))
    Ps['cy'] = 900
    Ps = place(Ps, pose_s, Ss, 1606)
    _, Js = body(Ps, pose_s, Ss)
    fg.append(cast_shadow(Js['H'][0] + 40, 1614, 250, 13, mix(SAND, GROUND_SH, 0.6)))
    fg.append(dust(Js['far_ankle'][0] - 40, 1596, 0.85, -1))
    fg.append(dust(Js['near_ankle'][0] - 30, 1596, 0.7, 1))
    gs, Js, si = figure(Ps, pose_s, Ss)
    fg.append(gs)
    sil.append(gs)
    report('scene snap', Ps, Js, si, Ss)

    # ---- marks: ghost ball at the clap, dotted arc up to the crown, ting
    cw = lerp(Js['near_tip'], Js['far_tip'], 0.5)
    gb = (cw[0] - 16, cw[1] - 4)
    start = (gb[0] + 4, gb[1] - r_ball - 8)
    end = (ball[0] + r_ball + 10, ball[1] - 4)
    ctrl = (start[0] + 110, end[1] - 10)
    fg.append(dotted('M%s,%s Q%s,%s %s,%s' % (f(start[0]), f(start[1]), f(ctrl[0]), f(ctrl[1]), f(end[0]), f(end[1])), w=12, gap=26))
    gm1 = bez(start, ctrl, end, 0.45)
    fg.append(ghost_ball(gb[0], gb[1], r_ball, 0.55))
    fg.append(ghost_ball(gm1[0], gm1[1], r_ball * 0.92, 0.45))
    fg.append(ticks(gb[0], gb[1], r_ball + 12, r_ball + 42, (-160, -125, 160, 125, -92), dark(LATTE, 0.55), 8))
    fg.append(temari(ball[0], ball[1], r_ball, rot=12))
    fg.append(ting(ball[0] + 10, ball[1] - r_ball - 4, 1.0))

    open(os.path.join(HERE, 'scene.svg'), 'w').write(svg_doc(W, H, ''.join(bg + fg), 0.025))
    open(os.path.join(HERE, 'scene_sil.svg'), 'w').write(sil_doc(W, H, sil))
    return dict(gen=(Pm, Jm, mi), snap=(Ps, Js, si))


# ================================================================ faces sheet (hero head, 3 x 2)
GEN_FACES = [
    # neutral: 26 % lid with drooping ends, irises tracking the ball low-left, one clean catchlight
    dict(gaze=(-0.35, 0.45)),
    # surprised (the jaw-drop take): lids snap up to 4 %, eye grows to 0.56 D, iris shrinks to 55 %, the top dot pops in,
    # brows jump 0.08 D, and the rubber jaw drops (Gen only)
    dict(pop=0.56 / 0.52, lid=(0.04, 0.04), lid_follow=1.0, iris_s=0.55, float=True, hl_top=True, hl_top_size=0.09, gaze=(0.0, 0.0),
         brow_raise=(0.08, 0.08), brow_tilt=(-6, -6), drop=0.30, open_w=0.26, stache='lift', beard_swing=8, marks=('pop',)),
    # angry: the lid straightens and slants 20 deg down toward the nose, inner brow drops onto the lash line
    dict(lid=(0.44, 0.44), lid_follow=0.0, lid_bow=0.0, lid_tilt=(20, 20), gaze=(-0.30, 0.15),
         brow_raise=(-0.13, -0.13), brow_tilt=(28, 28), stache='bristle', crease=True, marks=('anger',)),
    # smug: the cheek pushes the lower lid up in an upward curve, upper lid a touch lower, irises slid to the side,
    # one brow up, mustache hitched
    dict(lid=(0.36, 0.38), lid_tilt=(-6, -6), low=(0.07, 0.07), low_bow=0.07, gaze=(-0.75, 0.05),
         brow_raise=(-0.04, 0.12), brow_tilt=(8, -10), stache='smug', beard_swing=-8),
    # panic: wide-open lids with the inner ends lifted, iris shrunk to 48 %, wobbling outline, sweat, jaw at full stretch
    dict(pop=0.55 / 0.52, lid=(0.10, 0.10), lid_follow=0.6, lid_bow=0.0, lid_tilt=(-17, -17), iris_s=0.48, float=True, hl_top=True,
         hl_top_size=0.07, tear=True, wobble_eye=1.0, gaze=(0.15, 0.10), brow_raise=(0.06, 0.06), brow_tilt=(-28, -28),
         drop=0.50, open_w=0.28, wobble=1, stache='sag', marks=('sweat', 'shake'), beard_swing=12),
    # exasperated side-eye: one dome drops further than the other, irises jammed into the back corners,
    # highlights OFF (the shared 'dead inside' beat), slack jaw, a sigh
    dict(lid=(0.48, 0.56), lid_follow=0.25, lid_bow=0.03, low=(0.06, 0.06), gaze=(1.0, 0.10), hl_on=False,
         brow_raise=(-0.02, -0.04), brow_tilt=(-3, 8), drop=0.10, jaw_shift=0.05, open_w=0.18, stache='flat', marks=('sigh',)),
]


def build_faces():
    W = H = 1080
    b = ['<rect width="1080" height="1080" fill="#E9E0D0"/>']
    sil = []
    D = 222
    for i, ex in enumerate(GEN_FACES):
        col, row = i % 3, i // 3
        x0, y0 = col * 360, row * 540
        cid = uid('cell')
        b.append('<defs><clipPath id="%s"><rect x="%d" y="%d" width="360" height="540"/></clipPath></defs>' % (cid, x0, y0))
        g = ['<rect x="%d" y="%d" width="340" height="520" rx="26" fill="%s"/>' % (x0 + 10, y0 + 10, '#F4EEE3')]
        P = gen_head(cx=x0 + 186, cy=y0 + 175, D=D, face=-1)
        P.update(ex)
        S = gen_spec(D)
        pose = dict(lean=0, curve=0.0, hip=None, arm_layer=dict(near='far_arm'),
                    arms=dict(far=dict(ang=(2, 0), hand=False), near=dict(ang=(-2, 0), hand=False)),
                    legs=dict(far=dict(ang=(3, 0), foot=None), near=dict(ang=(-3, 0), foot=None)))
        fig, _, _ = figure(P, pose, S)
        g.append(fig)
        b.append('<g clip-path="url(#%s)">%s</g>' % (cid, ''.join(g)))
    open(os.path.join(HERE, 'faces.svg'), 'w').write(svg_doc(W, H, ''.join(b), 0.02))


# ================================================================ solo figures (540 x 1080)
def solo(name, g, Jt, info, target, extra_top=None):
    top = info['top'] if extra_top is None else min(info['top'], extra_top)
    sole = Jt['sole']
    k = target / (sole - top)
    return k, top, sole


def write_solo(name, g, Jt, info, target, xs, extra=''):
    top, sole = info['top'], Jt['sole']
    k = target / (sole - top)
    dy = 0.0
    try:
        cal = json.load(open(os.path.join(HERE, 'calib.json')))
        k *= cal.get(name, 1.0)
        dy = cal.get(name + '_dy', 0.0)
    except Exception:
        pass
    xc = (min(xs) + max(xs)) / 2
    tr = 'translate(270 %.2f) scale(%.5f) translate(%s %s)' % (1010 + dy, k, f(-xc), f(-sole))
    sh = '<ellipse cx="270" cy="1012" rx="150" ry="11" fill="#D9D4CB"/>'
    body_ = '<rect width="540" height="1080" fill="#EDEAE4"/>%s<g transform="%s">%s%s</g>' % (sh, tr, g, extra)
    open(os.path.join(HERE, name + '.svg'), 'w').write(svg_doc(540, 1080, body_, 0))
    open(os.path.join(HERE, name + '_sil.svg'), 'w').write(sil_doc(540, 1080, ['<g transform="%s">%s%s</g>' % (tr, g, extra)]))
    json.dump(dict(k=k, top=top, sole=sole, xc=xc), open(os.path.join(HERE, name + '_tf.json'), 'w'))
    print('%s: top %.1f sole %.1f scale %.4f -> %.1f px, D %.1f px' % (name, top, sole, k, (sole - top) * k, info['D'] * k), file=sys.stderr)


def build_hero():
    D = 250
    S = gen_spec(D)
    P = gen_head(cx=0, cy=0, D=D, face=-1, gaze=(-0.55, 0.85), beard_swing=3)
    pose = gen_crane(D, -1)
    pose = finish_crane(P, pose, S, 0.95)
    g, Jt, info = figure(P, pose, S)
    # the temari rests on the raised thigh, just behind the knee
    kn = Jt['near_knee']
    r = 0.17 * D
    ball = (kn[0] - 0.01 * D, kn[1] - r - 0.035 * D)
    xs = [info['center'][0] - D * 0.62, info['center'][0] + D * 0.62, Jt['near_knee'][0], Jt['far_elbow'][0], Jt['near_elbow'][0]]
    write_solo('hero', g, Jt, info, 960, xs, temari(ball[0], ball[1], r, rot=10))
    report('hero', P, Jt, info, S)


def build_partner():
    D = 250
    S = snap_spec(D)
    P = snap_head(cx=0, cy=0, D=D, face=-1, gaze=(-0.55, 0.05), mouth='smirk', mouth_w=0.20)
    pose = dict(lean=11, curve=0.07, anchor=('towel', CINN), hip=SNAP_HIP, sh_tilt=0,
                arms=dict(near=dict(rel=(-0.55 * D, 0.10 * D), hint=(0.3, 1), thumb=1, fist=True, hand_dir=(-0.5, -1), wraps=CREAM),
                          far=dict(rel=(-0.28 * D, -0.06 * D), hint=(0.2, 1), thumb=-1, fist=True, hand_dir=(-0.6, -1), wraps=CREAM)),
                legs=dict(far=dict(rel=(-0.16 * D, 1.30 * D), hint=(-1, 0.1), foot=dict(toe=-1, rot=26), wraps=CINN),
                          near=dict(rel=(0.24 * D, 1.30 * D), hint=(1, 0.1), foot=dict(toe=-1, rot=26), wraps=CINN)))
    g, Jt, info = figure(P, pose, S)
    xs = [info['center'][0] - D * 0.62, info['center'][0] + D * 0.62, Jt['near_elbow'][0], Jt['far_elbow'][0],
          Jt['near_ankle'][0], Jt['far_ankle'][0]]
    write_solo('partner', g, Jt, info, 900, xs)
    report('partner', P, Jt, info, S)


if __name__ == '__main__':
    build_scene()
    build_faces()
    build_hero()
    build_partner()
