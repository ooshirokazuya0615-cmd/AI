#!/usr/bin/env python3
"""Jaw Drop / アゴで語る -- ROUND split-circle heads on stick bodies.

ONE head rig  head(P):
    a true circle of diameter D split by the mouth SEAM (0.60 D down for the master, 0.55 D for Snap)
    into a cranium CAP (eyes, cloud/bar brows, nose bulb, ears, hair) and a rigid jaw BOWL on a spring:
        drop  (total mouth gap, x D)      lift (how much of that gap the cap rises, x D: the head pops on the neck)
        jut   (forward, x D: underbite)   shift (sideways, x D)   tuck (up, x D)   jaw_tilt (deg, chin up)
    at rest the two parts close into one circle with two tiny cheek notches; opened, a dark mouth with a cinnamon
    tongue is held by two stretched cheek lines.  Mouth library a-f, dot eyes / sagging U-arcs, beard riding the jaw
    with a one-frame lag (beard_swing).  Tinted outlines only, never black, never a gloss highlight.
ONE body rig  body(P, pose, S):
    skin neck stub (0.18 D wide, 0.14 D visible, chin shadow) -> costume anchor whose corners ARE the shoulders
    (neckerchief / sweat towel) -> tapered C/S spine -> two-bone arms (0.68 + 0.70 D, skin mittens 0.20 x 0.13 D
    with thumb nubs) and legs (0.74 + 0.70 D, bare feet 0.30 D) -> hip sash ring with tails.
Every figure in scene.svg, poses.svg and lineup.svg is figure() = body() + head().
"""
import math, os, random, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
ESP = '#3B2A20'
LATTE = '#C9A27E'
MILK = '#F5EDE0'
CINN = '#A0522D'
PIST = '#A7B57E'
CREMA = '#D9B26F'
SKY = '#BFD6DC'
VERM = '#C8452F'
GROUND_SH = '#B48D69'
SAND = '#E3D2B4'
WHITE = '#F7F3EA'
WHITE_LINE = '#C9C2B2'
MOUTH = '#5A3324'
CREAM = '#FBF1DA'
STONE = '#8F7B68'
HAIR = '#2B211C'
WALL = '#F2E8D6'

SKIN_M, LINE_M, TINT_M = '#E7BC95', '#A9805C', '#4A3326'
SKIN_S, LINE_S, TINT_S, STUB_S = '#A06E4C', '#6E4A33', '#3E281C', '#8C5E40'

UID = [0]
REG = dict(limbs=[])


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


def smooth(p, closed=True):
    n = len(p)
    d = 'M%s,%s' % (f(p[0][0]), f(p[0][1]))
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = p[(i - 1) % n] if (closed or i > 0) else p[i]
        p1 = p[i]
        p2 = p[(i + 1) % n]
        p3 = p[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += ' C%s,%s %s,%s %s,%s' % (f(c1[0]), f(c1[1]), f(c2[0]), f(c2[1]), f(p2[0]), f(p2[1]))
    return d + (' Z' if closed else '')


def ell_d(x, y, rx, ry):
    return 'M%s,%s a%s,%s 0 1 0 %s,0 a%s,%s 0 1 0 %s,0 Z' % (f(x - rx), f(y), f(rx), f(ry), f(2 * rx), f(rx), f(ry), f(-2 * rx))


def shape(d, fill, line=None, lw=6, extra=''):
    line = line or dark(fill)
    return ('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round" '
            'stroke-linecap="round" paint-order="stroke" %s/>' % (d, fill, line, f(2 * lw), extra))


def stroke(d, color, w, extra=''):
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
            'stroke-linejoin="round" %s/>' % (d, color, f(w), extra))


def circle(x, y, r, fill, line=None, lw=6, extra=''):
    return shape(ell_d(x, y, r, r), fill, line, lw, extra)


def union(parts, fill, line=None, lw=6, extra=''):
    line = line or dark(fill)
    s = ''.join('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>'
                % (d, line, line, f(2 * lw)) for d in parts)
    s += ''.join('<path d="%s" fill="%s"/>' % (d, fill) for d in parts)
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


def Q(a, b, c):
    return 'M%s,%s Q%s,%s %s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1]), f(c[0]), f(c[1]))


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


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay or 1.0
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return pdist(p, (a[0] + ax * t, a[1] + ay * t))


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
    return '<g transform="rotate(%s %s %s)">%s</g>' % (f(ang), f(x), f(y), shape(d, CREAM, dark(CREAM, 0.3), lw=4))


def star4(x, y, r, fill=CREAM, line=None):
    pts = []
    for k in range(8):
        a = math.radians(-90 + k * 45)
        rr = r if k % 2 == 0 else r * 0.30
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return shape(poly(pts), fill, line or dark(CREMA, 0.35), 2.5)


def ting(bx, by, s=1.0):
    """Bell 'ting': a small four-point glint plus radiating ticks (no glyphs)."""
    out = star4(bx + 44 * s, by - 30 * s, 17 * s)
    for a in (-150, -112, -74, -36):
        t = math.radians(a)
        p0 = (bx + 30 * s * math.cos(t), by - 6 * s + 30 * s * math.sin(t))
        p1 = (bx + 50 * s * math.cos(t), by - 6 * s + 50 * s * math.sin(t))
        out += stroke('M%s,%s L%s,%s' % (f(p0[0]), f(p0[1]), f(p1[0]), f(p1[1])), dark(CREMA, 0.4), max(3.5, 5 * s))
    return out


def dotted(d, color=None, w=8, gap=19):
    return stroke(d, color or dark(LATTE, 0.3), w, 'stroke-dasharray="0.1 %s"' % gap)


def ticks(x, y, r0, r1, angs, color, w=6):
    out = ''
    for a in angs:
        t = math.radians(a)
        out += stroke('M%s,%s L%s,%s' % (f(x + r0 * math.cos(t)), f(y + r0 * math.sin(t)),
                                         f(x + r1 * math.cos(t)), f(y + r1 * math.sin(t))), color, w)
    return out


def temari(x, y, r=40, op=1.0):
    lwk = max(2.5, r * 0.16)
    out = [circle(x, y, r, CREAM, dark(VERM, 0.35), lwk)]
    for k in range(0, 6, 2):
        a0 = math.radians(-90 + k * 60 + 20)
        a1 = math.radians(-90 + (k + 1) * 60 + 20)
        out.append('<path d="M%s,%s L%s,%s A%s,%s 0 0 1 %s,%s Z" fill="%s"/>' % (
            f(x), f(y), f(x + r * math.cos(a0)), f(y + r * math.sin(a0)), f(r), f(r),
            f(x + r * math.cos(a1)), f(y + r * math.sin(a1)), VERM))
    out.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
        f(x), f(y), f(r * 0.55), CREMA, f(r * 0.12)))
    out.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(x), f(y), f(r * 0.16), CREMA))
    bx, by = x + r * 0.38, y - r * 1.08
    out.append(stroke(Q((x + r * 0.1, y - r * 0.95), (x + r * 0.22, y - r * 1.2), (bx, by)), VERM, max(3, r * 0.1)))
    out.append(circle(bx, by - r * 0.1, r * 0.24, CREMA, dark(CREMA), max(2, r * 0.07)))
    out.append(stroke('M%s,%s L%s,%s' % (f(bx - r * 0.12), f(by - r * 0.03), f(bx + r * 0.12), f(by - r * 0.03)),
                      dark(CREMA, 0.45), max(2, r * 0.07)))
    g = ''.join(out)
    return g if op >= 1 else '<g opacity="%s">%s</g>' % (f(op), g)


def ghost_ball(x, y, r, op=0.6):
    """Dashed outline where the ball just was (cause/contact/result in a still)."""
    return ('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="0.35" stroke="%s" stroke-width="%s" '
            'stroke-dasharray="%s %s" opacity="%s"/>' % (f(x), f(y), f(r), CREAM, dark(VERM, 0.2), f(max(3, r * 0.13)),
                                                         f(r * 0.32), f(r * 0.22), f(op)))


# ================================================================ HEAD RIG (split circle)
HDEF = dict(cx=0.0, cy=0.0, D=200.0, face=1, turn=0.12, seam=0.60, tilt=0.0,
            skin=SKIN_M, line=LINE_M, lw=None, jaw_tint=0.06,
            lift=0.0, drop=0.0, jut=0.0, shift=0.0, tuck=0.0, jaw_tilt=0.0,
            eyes='open', eye_d=0.075, eye_y=0.42, eye_gap=0.25, gaze=(0.0, 0.0), closed_w=0.13, closed_t=0.045,
            eye_color=ESP,
            brow='cloud', brow_w=0.30, brow_h=0.13, brow_gap=0.105, brow_raise=(0.0, 0.0), brow_in=0.0,
            brow_top=False, brow_color=WHITE, brow_line=WHITE_LINE, tuft=True, brow_out=0.055, brow_jump=0.12, tuft_max=0.13,
            nose='bulb', nose_s=1.0,
            ears=True, ear_p=0.12, ear_pf=0.07, ear_y=0.05, lobes=True, ear_s=1.0,
            hair='flicks', hair_color=WHITE, hair_line=WHITE_LINE,
            beard=0.0, beard_w=0.38, beard_swing=0.0,
            mouth='a', mouth_w=0.26, mouth_x=0.85, teeth_up=0, teeth_low=0, stubble=False, wrinkles=False,
            marks=(), tongue=CINN, cheek_bow=0.30, mouth_color=MOUTH, jaw_front=False, buzz_rise=0.08)


def head(P):
    d = dict(HDEF)
    d.update(P)
    D = float(d['D'])
    R = D / 2
    face = d['face']
    cx, cy = d['cx'], d['cy']
    lw = d['lw'] or 0.027 * D
    skin, line = d['skin'], d['line']
    lift = d['lift'] * D
    ccx, ccy = cx, cy - lift
    sy = (d['seam'] - 0.5) * D
    hw = math.sqrt(R * R - sy * sy)
    ths = math.atan2(sy, hw)
    fs = face * d['turn'] * D
    tx = face * d['jut'] * D + d['shift'] * D
    ty = (d['drop'] - d['lift'] - d['tuck']) * D
    rot = -face * d['jaw_tilt']
    hinge = (-face * hw, sy)

    def J(u, v):          # jaw-local (rest-centre origin) -> world
        p = rot_pt((u, v), rot, hinge)
        return (cx + p[0] + tx, cy + p[1] + ty)

    def C(u, v):          # cap-local -> world
        return (ccx + u, ccy + v)
    N = 96
    jaw_loc = [(R * math.cos(t), R * math.sin(t)) for t in (ths + (math.pi - 2 * ths) * k / N for k in range(N + 1))]
    cap_loc = [(R * math.cos(t), R * math.sin(t)) for t in (math.pi - ths + (math.pi + 2 * ths) * k / N for k in range(N + 1))]
    jaw_w = [J(*p) for p in jaw_loc]
    cap_w = [C(*p) for p in cap_loc]
    jaw_d, cap_d = poly(jaw_w), poly(cap_w)
    gap = d['drop'] > 0.004
    UID[0] += 1
    uid = 'h%d' % UID[0]
    out = []
    tops = [ccy - R - lw]
    hc = d['hair_color']

    # ---- bun / topknot behind the crown
    if d['hair'] in ('topknot', 'bun'):
        rr = (0.13 if d['hair'] == 'topknot' else 0.15) * D
        a = math.radians(-90 - face * (28 if d['hair'] == 'topknot' else 40))
        k = C(math.cos(a) * (R + rr * 0.30), math.sin(a) * (R + rr * 0.30))
        out.append(circle(k[0], k[1], rr, hc, dark(hc, 0.35), lw))
        if d['hair'] == 'topknot':
            out.append(stroke(Q((k[0] - rr * 0.6, k[1] + rr * 0.35), (k[0], k[1] + rr * 0.6), (k[0] + rr * 0.6, k[1] + rr * 0.35)),
                              dark(hc, 0.4), lw * 0.8))
        tops.append(k[1] - rr - lw)

    # ---- ears (ride the cap; near ear protrudes more in 3/4)
    if d['ears']:
        for sg in (-1, 1):
            far = (sg == face) and d['turn'] > 0.02
            p = (d['ear_pf'] if far else d['ear_p']) * D
            s = (0.86 if far else 1.0) * d['ear_s']
            ew, eh = 0.085 * D * s, 0.125 * D * s
            ox, oy = sg * (R + p - ew), d['ear_y'] * D
            if d['lobes']:
                q = [(ox - sg * ew * 0.6, oy - eh * 0.95), (ox + sg * ew * 0.5, oy - eh * 1.02), (ox + sg * ew, oy - eh * 0.35),
                     (ox + sg * ew * 0.86, oy + eh * 0.55), (ox + sg * ew * 0.32, oy + eh * 1.28), (ox - sg * ew * 0.45, oy + eh * 1.18),
                     (ox - sg * ew * 1.2, oy + eh * 0.2)]
            else:
                q = [(ox - sg * ew * 0.6, oy - eh * 0.95), (ox + sg * ew * 0.5, oy - eh), (ox + sg * ew, oy - eh * 0.2),
                     (ox + sg * ew * 0.7, oy + eh * 0.8), (ox - sg * ew * 0.2, oy + eh), (ox - sg * ew * 1.2, oy + eh * 0.2)]
            out.append(shape(smooth([C(*v) for v in q]), skin, line, lw))
            out.append(stroke(Q(C(ox + sg * ew * 0.0, oy - eh * 0.55), C(ox + sg * ew * 0.85, oy - eh * 0.05),
                                C(ox + sg * ew * 0.05, oy + eh * 0.62)), line, lw * 0.75))

    # ---- mouth gap + tongue (behind both parts)
    Lc, Rc = C(-hw, sy), C(hw, sy)
    Jl, Jr = J(-hw, sy), J(hw, sy)
    cb = d['cheek_bow'] * D
    ctr_r = ((Rc[0] + Jr[0]) / 2 - cb, (Rc[1] + Jr[1]) / 2)
    ctr_l = ((Lc[0] + Jl[0]) / 2 + cb, (Lc[1] + Jl[1]) / 2)
    if gap:
        mp = 'M%s,%s L%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s Z' % (
            f(Lc[0]), f(Lc[1]), f(Rc[0]), f(Rc[1]), f(ctr_r[0]), f(ctr_r[1]), f(Jr[0]), f(Jr[1]),
            f(Jl[0]), f(Jl[1]), f(ctr_l[0]), f(ctr_l[1]), f(Lc[0]), f(Lc[1]))
        out.append('<path d="%s" fill="%s"/>' % (mp, d['mouth_color']))
        gsz = pdist(C(0, sy), J(0, sy))
        tc = J(fs * 0.55, sy - 0.01 * D)
        trx, try_ = 0.21 * D, min(0.075 * D, gsz * 0.32)
        out.append('<g transform="rotate(%s %s %s)">%s</g>' % (
            f(rot), f(tc[0]), f(tc[1]), shape(ell_d(tc[0], tc[1], trx, try_), d['tongue'], dark(d['tongue'], 0.3), lw * 0.6)))

    # ---- outline passes (both parts) then fills: one silhouette, tinted rim
    out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (jaw_d, line, line, f(2 * lw)))
    out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (cap_d, line, line, f(2 * lw)))
    out.append('<defs><clipPath id="%s-j"><path d="%s"/></clipPath><clipPath id="%s-c"><path d="%s"/></clipPath></defs>'
               % (uid, jaw_d, uid, cap_d))
    jf = d['jaw_front'] and not gap
    if jf:
        out.append('<path d="%s" fill="%s"/>' % (cap_d, skin))
    out.append('<path d="%s" fill="%s"/>' % (jaw_d, dark(skin, d['jaw_tint'])))

    # ---- stubble: flat shadow + stipple on the bowl (chin weight)
    if d['stubble']:
        sc = d['stubble'] if isinstance(d['stubble'], str) else STUB_S
        band = [J(-R * 1.1, sy + 0.10 * D), J(fs * 0.4, sy + 0.07 * D), J(R * 1.1, sy + 0.10 * D), J(R * 1.1, R * 1.2), J(-R * 1.1, R * 1.2)]
        out.append('<path d="%s" fill="%s" opacity="0.55" clip-path="url(#%s-j)"/>' % (smooth(band), sc, uid))
        rnd = random.Random(int(D * 7 + face))
        dots = []
        for _ in range(int(150 * (D / 250) ** 0.5)):
            u = rnd.uniform(-R, R)
            v = rnd.uniform(sy + 0.08 * D, R)
            if u * u + v * v > (R * 0.97) ** 2:
                continue
            if rnd.random() > 0.35 + 0.65 * (v - sy) / (R - sy):
                continue
            p = J(u, v)
            dots.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(p[0]), f(p[1]), f(rnd.uniform(0.008, 0.013) * D)))
        out.append('<g fill="%s" clip-path="url(#%s-j)">%s</g>' % (dark(sc, 0.18), uid, ''.join(dots)))

    # ---- beard (rides the jaw, bent by beard_swing = the one-frame lag)
    binfo = {}
    if d['beard'] > 0:
        L = d['beard'] * D
        bw = d['beard_w'] * D / 2
        bc = fs * 0.85
        top = sy + 0.10 * D
        piv = (bc, R * 0.72)
        right = [(1.05, R * 0.55), (1.03, R + 0.14 * L), (0.92, R + 0.40 * L), (0.72, R + 0.63 * L), (0.46, R + 0.83 * L)]
        left = [(-1.03, R + 0.12 * L), (-0.92, R + 0.36 * L), (-0.72, R + 0.60 * L), (-0.42, R + 0.82 * L)]
        topl = [(-0.9, top + 0.035 * D), (-0.45, top + 0.004 * D), (0.0, top - 0.006 * D), (0.45, top + 0.004 * D),
                (0.9, top + 0.035 * D)]
        curl = (face * 0.62, R + 0.93 * L)
        tip = (face * 0.12, R + 1.0 * L)
        hook = (face * 0.40, R + 0.80 * L)
        seq = [(bc + a * bw, b) for a, b in topl] + [(bc + a * bw, b) for a, b in right]
        if face > 0:
            seq += [(bc + hook[0] * bw, hook[1]), (bc + curl[0] * bw, curl[1]), (bc + tip[0] * bw, tip[1])]
        else:
            seq += [(bc + tip[0] * bw, tip[1]), (bc + curl[0] * bw, curl[1]), (bc + hook[0] * bw, hook[1])]
        seq += [(bc + a * bw, b) for a, b in left[::-1]] + [(bc - 1.05 * bw, R * 0.55)]
        if face < 0:
            # keep the right side going down / left side going up order valid for the mirrored curl
            pass

        def bend(q):
            u, v = q
            t = max(0.0, min(1.0, (v - piv[1]) / (R + L - piv[1])))
            return rot_pt((u, v), -face * d['beard_swing'] * (t ** 0.8), piv)
        wp = [J(*bend(q)) for q in seq]
        out.append(shape(smooth(wp), WHITE, WHITE_LINE, lw * 0.8))
        for su in (-0.45, 0.05, 0.5):
            s0 = J(*bend((bc + su * bw, R * 0.62)))
            s1 = J(*bend((bc + su * 0.8 * bw, R + L * 0.40)))
            s2 = J(*bend((bc + su * 0.4 * bw, R + L * 0.70)))
            out.append(stroke(Q(s0, s1, s2), WHITE_LINE, max(2.5, 0.016 * D)))
        binfo = dict(tip=J(*bend((bc + tip[0] * bw, tip[1]))), curl=J(*bend((bc + curl[0] * bw, curl[1]))),
                     hook=J(*bend((bc + hook[0] * bw, hook[1]))), root=J(*bend((bc, R * 0.6))),
                     mid=J(*bend((bc, R + 0.5 * L))))

    # ---- cap fill + hair on the cap
    if not jf:
        out.append('<path d="%s" fill="%s"/>' % (cap_d, skin))
    if d['hair'] == 'buzz':
        rz = 1.0 + 2 * d['buzz_rise']
        pts = [(-1.04, -0.18), (-1.06, -0.46), (-0.95, -0.76), (-0.66, -1.03), (-0.30, -rz + 0.03), (0.25, -rz),
               (0.56, -rz + 0.09), (0.80, -0.86), (0.88, -0.58), (0.72, -0.50), (0.50, -0.42), (0.26, -0.48),
               (-0.02, -0.44), (-0.36, -0.38), (-0.66, -0.30), (-0.90, -0.12)]
        hp = [C(face * x * R, y * R) for x, y in pts]
        out.append(shape(smooth(hp), hc, line, lw))
        rnd = random.Random(5)
        tk = []
        for _ in range(16):
            x, y = rnd.uniform(-0.8, 0.6), rnd.uniform(-1.12, -0.6)
            if x * x + y * y > 1.25:
                continue
            p = C(face * x * R, y * R)
            tk.append('M%s,%s l%s,%s' % (f(p[0]), f(p[1]), f(face * 0.02 * D), f(-0.025 * D)))
        out.append(stroke(' '.join(tk), mix(hc, skin, 0.35), max(2, 0.012 * D)))
        tops.append(ccy - rz * R - lw)
    elif d['hair'] in ('topknot', 'bun'):
        lowy = -0.34 if d['hair'] == 'topknot' else -0.28
        hp = [(-1.2, -1.3), (1.2, -1.3), (1.2, lowy - 0.05), (0.75, lowy - 0.12), (0.35, lowy - 0.02), (0.0, lowy - 0.08),
              (-0.4, lowy + 0.04), (-0.8, lowy + 0.12), (-1.2, lowy + 0.2)]
        hp = [C(face * x * R, y * R) for x, y in hp]
        out.append('<path d="%s" fill="%s" clip-path="url(#%s-c)"/>' % (smooth(hp), hc, uid))
        if d['hair'] == 'bun':
            out.append(stroke(Q(C(face * 0.15 * R, -R * 0.99), C(face * 0.1 * R, -R * 0.7), C(face * 0.18 * R, (lowy - 0.02) * R)),
                              dark(hc, 0.3), lw * 0.7, 'clip-path="url(#%s-c)"' % uid))
    elif d['hair'] == 'flicks':
        # three white flicks at the BACK of the bald crown (top break), same cloud language as the brows
        parts = []
        # one scalloped cloud tuft hugging the upper back of the bald crown + a wisp curling back (top break)
        a0, a1 = 196.0, 258.0
        outer, inner = [], []
        for k in range(41):
            t = k / 40.0
            ang = a0 + (a1 - a0) * t
            th = 0.068 * math.sin(math.pi * t) ** 0.7 + 0.036 * abs(math.sin(3 * math.pi * t)) * math.sin(math.pi * t) ** 0.3
            aa = math.radians(ang if face > 0 else 180 - ang)
            outer.append(C(math.cos(aa) * (R + th * D), math.sin(aa) * (R + th * D)))
            inner.append(C(math.cos(aa) * (R - 0.035 * D), math.sin(aa) * (R - 0.035 * D)))
            tops.append(outer[-1][1] - 3)
        parts.append(poly(outer + inner[::-1]))
        a = math.radians(246 if face > 0 else -66)
        n = (math.cos(a), math.sin(a))
        r0 = C(n[0] * (R + 0.06 * D), n[1] * (R + 0.06 * D))
        w1 = (r0[0] - face * 0.045 * D, r0[1] - 0.065 * D)
        w2 = (r0[0] - face * 0.115 * D, r0[1] - 0.05 * D)
        parts.append(smooth(limb([r0, w1, w2], 0.055 * D, 0.012 * D), True))
        tops.append(w1[1] - 0.03 * D)
        out.append(union(parts, WHITE, WHITE_LINE, max(2.5, lw * 0.6)))

    # ---- seam + notches (closed) or stretched cheek lines (open)
    SP = J if jf else C          # the seam follows the jaw's top edge when the jaw is pushed in front
    if not gap:
        a0, a1 = SP(-hw, sy), SP(hw, sy)
        out.append(stroke('M%s,%s L%s,%s' % (f(a0[0]), f(a0[1]), f(a1[0]), f(a1[1])), line, lw * (1.0 if jf else 0.72)))
        for sg in (-1, 1):
            a = SP(sg * (hw + lw * 0.7), sy - 0.006 * D)
            b = SP(sg * (hw - 0.05 * D), sy + 0.014 * D)
            out.append(stroke('M%s,%s L%s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1])), line, lw * 0.95))
    else:
        cw = max(4.0, 0.023 * D)
        out.append(stroke(Q(Rc, ctr_r, Jr), line, cw))
        out.append(stroke(Q(Lc, ctr_l, Jl), line, cw))

    # ---- teeth
    if gap and d['teeth_up']:
        n = d['teeth_up']
        w, h = 0.065 * D, 0.075 * D
        for k in range(n):
            u = fs * 0.75 + (k - (n - 1) / 2) * w * 1.6
            a = C(u - w / 2, sy - 0.004 * D)
            out.append(shape('M%s,%s l%s,0 l0,%s q%s,%s %s,0 Z' % (f(a[0]), f(a[1]), f(w), f(h * 0.7), f(-w / 2), f(h * 0.45), f(-w)),
                             CREAM, dark(CREAM, 0.35), max(2, 0.012 * D)))
    if d['teeth_low']:
        n = d['teeth_low']
        w, h = 0.072 * D, (0.075 if gap else 0.058) * D
        for k in range(n):
            u = fs * 0.65 + (k - (n - 1) / 2) * w * 1.18
            q = [J(u - w / 2, sy + 0.004 * D), J(u + w / 2, sy + 0.004 * D), J(u + w / 2 - 0.008 * D, sy - h), J(u - w / 2 + 0.008 * D, sy - h)]
            out.append(shape(poly(q), CREAM, dark(CREAM, 0.38), max(2, 0.012 * D)))

    # ---- mouth library on the seam
    m = d['mouth']
    mw = d['mouth_w'] * D
    mu = fs * d['mouth_x']

    def M(x, y):
        return SP(mu + x, sy + y)
    if m == 'a':
        out.append(stroke(Q(M(-mw / 2, -0.004 * D), M(0, 0.02 * D), M(mw / 2, -0.006 * D)), line, lw * 1.1))
    elif m == 'b':
        s = -face
        p = [M(-s * 0.42 * mw, 0.0), M(-s * 0.05 * mw, 0.014 * D), M(s * 0.36 * mw, 0.006 * D), M(s * 0.55 * mw, -0.035 * D),
             M(s * 0.60 * mw, -0.085 * D)]
        out.append(stroke(smooth(p, False), line, lw * 1.25))
        out.append(stroke(Q(M(s * 0.74 * mw, -0.125 * D), M(s * 0.86 * mw, -0.075 * D), M(s * 0.76 * mw, -0.025 * D)), line, lw * 0.85))
    elif m == 'c':
        w, h = 0.5 * D, 0.15 * D
        corners = [M(-w / 2, -h / 2), M(w / 2, -h / 2), M(w / 2, h / 2), M(-w / 2, h / 2)]
        out.append(shape(poly(corners), CREAM, dark(skin, 0.45), lw * 0.7))
        out.append(stroke('M%s,%s L%s,%s' % (M(-w / 2, 0) + M(w / 2, 0)), dark(CREAM, 0.4), max(2, lw * 0.4)))
        for k in range(1, 6):
            a, b = M(-w / 2 + k * w / 6, -h / 2), M(-w / 2 + k * w / 6, h / 2)
            out.append(stroke('M%s,%s L%s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1])), dark(CREAM, 0.4), max(2, lw * 0.4)))
    elif m == 'd' and not gap:
        a = M(0, 0.02 * D)
        out.append(shape(ell_d(a[0], a[1], 0.11 * D, 0.06 * D), MOUTH, line, lw * 0.6))
    elif m == 'e':
        w, h = 0.36 * D, 0.13 * D
        out.append(shape(poly([M(-w / 2, -h / 2), M(w / 2, -h / 2), M(w / 2, h / 2), M(-w / 2, h / 2)]), MOUTH, line, lw * 0.6))
        zz = [(-w / 2 + k * w / 8, (-0.016 if k % 2 else 0.02) * D) for k in range(9)]
        top = [(-w / 2, -h / 2)] + zz + [(w / 2, -h / 2)]
        out.append('<path d="%s" fill="%s"/>' % (poly([M(*q) for q in top]), CREAM))
        bot = [(-w / 2, h / 2)] + [(x, y + 0.03 * D) for x, y in zz] + [(w / 2, h / 2)]
        out.append('<path d="%s" fill="%s"/>' % (poly([M(*q) for q in bot]), CREAM))
    elif m == 'f':
        out.append(stroke(smooth([M(-mw * 0.5, 0.05 * D), M(-mw * 0.32, 0.004 * D), M(mw * 0.3, 0.004 * D), M(mw * 0.5, 0.05 * D)], False),
                          line, lw * 1.1))

    # ---- nose (rides the cap, sits on the seam)
    ns = d['nose_s']
    if d['nose'] == 'bulb':
        nc = C(fs * 1.75, sy - 0.02 * D)
        out.append(shape(ell_d(nc[0], nc[1], 0.082 * D * ns, 0.07 * D * ns), skin, line, lw * 0.8))
        out.append(stroke(Q((nc[0] - face * 0.035 * D * ns, nc[1] + 0.022 * D * ns), (nc[0] - face * 0.06 * D * ns, nc[1] + 0.05 * D * ns),
                            (nc[0] - face * 0.01 * D * ns, nc[1] + 0.05 * D * ns)), line, lw * 0.6))
    elif d['nose'] == 'broad':
        nc = C(face * 0.33 * D, sy - 0.004 * D)
        u = 0.105 * D * ns
        p = [(nc[0] - face * u * 0.95, nc[1] + u * 0.45), (nc[0] - face * u * 0.45, nc[1] - u * 0.7), (nc[0] + face * u * 0.4, nc[1] - u * 0.72),
             (nc[0] + face * u * 1.05, nc[1] + u * 0.2), (nc[0] + face * u * 0.55, nc[1] + u * 0.68), (nc[0] - face * u * 0.4, nc[1] + u * 0.7)]
        out.append(shape(smooth(p), skin, line, lw * 0.8))
        out.append(stroke(Q((nc[0] - face * u * 0.45, nc[1] + u * 0.32), (nc[0] - face * u * 0.05, nc[1] + u * 0.62),
                            (nc[0] + face * u * 0.4, nc[1] + u * 0.42)), line, lw * 0.6))

    # ---- eyes
    ey = ccy - R + d['eye_y'] * D
    g = d['eye_gap'] * D
    exs = [ccx + fs - g / 2, ccx + fs + g / 2]
    gx, gy = d['gaze'][0] * D, d['gaze'][1] * D
    if d['wrinkles']:
        for i, ex in enumerate(exs):
            sg = -1 if i == 0 else 1
            ox = ex + sg * (d['closed_w'] * D * 0.5 + 0.035 * D)
            for dy in (-0.026, 0.02):
                out.append(stroke('M%s,%s L%s,%s' % (f(ox), f(ey + dy * 0.3 * D), f(ox + sg * 0.05 * D), f(ey + dy * D)),
                                  line, max(2.5, 0.016 * D), 'opacity="0.8"'))
        for k in range(2):
            y = ccy - R + (0.17 + 0.065 * k) * D
            x0 = ccx + fs * 0.8
            w = (0.12 - 0.03 * k) * D
            out.append(stroke(Q((x0 - w, y + 0.012 * D), (x0, y - 0.02 * D), (x0 + w, y + 0.012 * D)), line, max(2.5, 0.016 * D),
                              'opacity="0.6"'))
    for ex in exs:
        if d['eyes'] == 'closed':
            w = d['closed_w'] * D
            out.append(stroke(Q((ex - w / 2, ey - 0.012 * D), (ex, ey + 0.06 * D), (ex + w / 2, ey - 0.012 * D)),
                              d['eye_color'], d['closed_t'] * D))
        else:
            out.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(ex + gx), f(ey + gy), f(d['eye_d'] * D / 2), d['eye_color']))

    # ---- brows
    bw, bh = d['brow_w'] * D, d['brow_h'] * D
    for i, ex in enumerate(exs):
        sg = -1 if i == 0 else 1
        bx = ex + sg * d['brow_out'] * D
        if d['brow_top']:
            hair_top = ccy - ((1.0 + 2 * d['buzz_rise']) * R if d['hair'] == 'buzz' else R)
            by = hair_top - d['brow_jump'] * D - bh * 0.5
        else:
            by = ey - d['brow_gap'] * D
        by -= d['brow_raise'][i] * D
        ang = d['brow_in'] * (1 if i == 0 else -1)
        if d['brow'] == 'cloud':
            parts = []
            for (u, v, r) in ((-0.38, 0.06, 0.40), (-0.13, -0.10, 0.50), (0.13, -0.08, 0.50), (0.36, 0.05, 0.42)):
                px, py = rot_pt((bx + sg * u * bw, by + v * bh), ang, (bx, by))
                parts.append(ell_d(px, py, r * bh, r * bh))
            base = [rot_pt((bx + sg * bw * x, by + bh * y), ang, (bx, by)) for x, y in
                    [(-0.46, 0.30), (0.42, 0.34), (0.46, 0.0), (-0.46, -0.05)]]
            parts.append(poly(base))
            if d['tuft']:
                # outer tuft sweeps out past the rim (a circle break), drooping a little
                t0 = rot_pt((bx + sg * bw * 0.40, by + bh * 0.05), ang, (bx, by))
                if d['brow_top']:
                    tip = (t0[0] + sg * 0.09 * D, t0[1] - 0.04 * D)
                else:
                    ty_ = t0[1] - 0.01 * D
                    dyc = ty_ - ccy
                    rim = math.sqrt(max(0.0, R * R - dyc * dyc))
                    tx_ = ccx + sg * (rim + 0.035 * D)
                    reach = sg * (tx_ - t0[0])
                    reach = max(0.06 * D, min(d['tuft_max'] * D, reach))
                    tip = (t0[0] + sg * reach, ty_ - 0.02 * D)
                midp = (lerp(t0, tip, 0.5)[0], lerp(t0, tip, 0.5)[1] + 0.012 * D)
                parts.append(smooth(limb([t0, midp, tip], bh * 0.62, bh * 0.10), True))
                tops.append(min(midp[1], tip[1]) - bh)
            out.append(union(parts, d['brow_color'], d['brow_line'], max(2.5, lw * 0.6)))
            tops.append(by - bh * 0.6 - lw)
        else:
            q = [rot_pt((bx + sg * bw * x, by + bh * y), ang, (bx, by)) for x, y in
                 [(-0.5, -0.45), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.45)]]
            out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                poly(q), d['brow_color'], d['brow_color'], f(bh * 0.5)))
            tops.append(by - bh)

    # ---- marks
    mk = d['marks']
    if 'crease' in mk:
        y = ccy - R * 0.42
        x0 = ccx + fs
        out.append(stroke(Q((x0 - 0.09 * D, y + 0.02 * D), (x0, y - 0.03 * D), (x0 + 0.09 * D, y + 0.02 * D)), line, lw))
    if 'sweat' in mk:
        out.append(sweat(ccx + face * R * 1.32, ccy - R * 0.38, D / 220, 62 * face))
    if 'dust' in mk:
        for sgn in (-1, 1):
            b = J(sgn * R * 0.6, R * 0.86)
            out.append(dust(b[0] + sgn * 0.12 * D, b[1], D / 430, sgn))

    hang = -face * d['tilt']
    piv = (ccx, ccy)
    body = ''.join(out)
    if hang:
        body = '<g transform="rotate(%s %s %s)">%s</g>' % (f(hang), f(piv[0]), f(piv[1]), body)
    T = lambda p: rot_pt(p, hang, piv)
    info = dict(cap=(ccx, ccy), R=R, D=D, lw=lw, face=face, J=lambda u, v: T(J(u, v)), C=lambda u, v: T(C(u, v)),
                jaw_bottom=T(J(fs * 0.3, R)), chin_corner=T(J(face * hw, sy)), seam_y=ccy + sy,
                top=min(tops), eyes=[T((x, ey)) for x in exs])
    info.update({k: T(v) for k, v in binfo.items()})
    return body, info


# ================================================================ BODY RIG
def V(a, face):
    """Direction from an angle: 0 = straight down, +90 = toward the facing side, 180 = up, -90 = backward."""
    r = math.radians(a)
    return (face * math.sin(r), math.cos(r))


def ik2(root, target, L1, L2, hint, straight=False):
    D_ = pdist(root, target)
    u = unit(root, target)
    maxD = (L1 + L2) * (0.99995 if straight else 0.9965)
    Dc = max(abs(L1 - L2) + 1.0, min(D_, maxD))
    a = (L1 * L1 - L2 * L2 + Dc * Dc) / (2 * Dc)
    h = math.sqrt(max(0.0, L1 * L1 - a * a))
    n = (-u[1], u[0])
    m = padd(root, u, a)
    j1, j2 = padd(m, n, h), padd(m, n, -h)
    hp = padd(m, hint, 1000)
    joint = j1 if pdist(j1, hp) < pdist(j2, hp) else j2
    return joint, padd(root, u, Dc)


def solve_limb(root, spec, L1, L2, face):
    k = spec.get('k', 1.0)
    L1, L2 = L1 * k, L2 * k
    if 'ang' in spec:
        a1, a2 = spec['ang']
        Jn = padd(root, V(a1, face), L1)
        return Jn, padd(Jn, V(a2, face), L2)
    if 'pts' in spec:
        (jx, jy), (ex, ey) = spec['pts']
        return (root[0] + jx, root[1] + jy), (root[0] + ex, root[1] + ey)
    tgt = spec['to'] if 'to' in spec else padd(root, spec['rel'])
    return ik2(root, tgt, L1, L2, spec.get('hint', (0, 1)), spec.get('straight', False))


def tube(pts, widths, color, tag=None):
    out = []
    for i in range(len(pts) - 1):
        out.append('<path d="%s"/>' % poly(limb([pts[i], pts[i + 1]], widths[i], widths[i + 1])))
    for p, w in zip(pts, widths):
        out.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(p[0]), f(p[1]), f(w / 2)))
    if tag:
        REG['limbs'].append((tag, [tuple(p) for p in pts], list(widths), color))
    return '<g fill="%s">%s</g>' % (color, ''.join(out))


def body_spec(D, skin, line, tint, spine=0.97, legs=(0.74, 0.70), lw=None, minw=12.0):
    lw = lw or 0.027 * D
    mw = lambda v: max(minw, v)
    return dict(D=D, skin=skin, line=line, tint=tint, lw=lw,
                spine=spine * D, upper=0.68 * D, fore=0.70 * D, thigh=legs[0] * D, shin=legs[1] * D,
                arm_w=(mw(0.075 * D), mw(0.062 * D), mw(0.05 * D)), leg_w=(mw(0.078 * D), mw(0.064 * D), mw(0.052 * D)),
                spine_w=(mw(0.085 * D), mw(0.06 * D)), sh=0.27 * D,
                hand_L=0.20 * D, hand_W=0.13 * D, hand_lw=max(2.5, 0.022 * D),
                foot_L=0.30 * D, foot_fill=dark(skin, 0.15), foot_line=dark(skin, 0.5), foot_lw=max(2.5, 0.02 * D),
                neck_w=0.18 * D)


def mitten(W, u, S, thumb_side=-1, scale=1.0):
    L, Wd = S['hand_L'] * scale, S['hand_W'] * scale
    n = (-u[1], u[0])

    def P(a, b):
        return (W[0] + u[0] * a + n[0] * b, W[1] + u[1] * a + n[1] * b)
    pts = [P(-0.03 * L, -0.38 * Wd), P(0.40 * L, -0.52 * Wd), P(0.82 * L, -0.46 * Wd), P(1.0 * L, -0.06 * Wd),
           P(0.93 * L, 0.32 * Wd), P(0.60 * L, 0.52 * Wd), P(0.15 * L, 0.48 * Wd), P(-0.03 * L, 0.36 * Wd)]
    paddle = shape(smooth(pts), S['skin'], S['line'], S['hand_lw'])
    s = thumb_side
    c = [P(0.14 * L, s * 0.30 * Wd), P(0.34 * L, s * 0.66 * Wd), P(0.52 * L, s * 0.84 * Wd)]
    thumb = shape(smooth(limb(c, 0.46 * Wd, 0.38 * Wd), True), S['skin'], S['line'], S['hand_lw'] * 0.85)
    return paddle, thumb


def foot(An, toe, S, rot=0.0):
    """Bare foot: rounded wedge 0.30 D, flat sole, two toe ticks, one tint darker than the skin."""
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
        out += stroke('M%s,%s L%s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1])), S['foot_line'], max(2.5, 0.013 * S['D']))
    sole_y = max(p[1] for p in pts) + S['foot_lw']
    return out, sole_y


def sole_drop(S):
    return S['foot_L'] * 0.38 * 0.55 + 1 + S['foot_lw']


def ribbon(pts, w0, w1, color, lw=3):
    return shape(smooth(limb(pts, w0, w1), True), color, dark(color, 0.35), lw)


def sash(Hp, up, face, D, color, tails):
    """Sash ring around the hip (back arc, front arc, knot, tails). Returns (back, front)."""
    rx, ry, band = 0.17 * D, 0.05 * D, 0.05 * D
    c = padd(Hp, up, 0.06 * D)
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
    front += circle(k[0], k[1], 0.038 * D, color, line, max(2, 0.012 * D))
    return back, front


def wraps(E, W, D, color, ts=(0.60, 0.80)):
    u = unit(E, W)
    n = (-u[1], u[0])
    line = dark(color, 0.38)
    out = ''
    for t in ts:
        c = lerp(E, W, t)
        hw_, ht = 0.058 * D, 0.02 * D
        q = [padd(padd(c, n, hw_), u, -ht), padd(padd(c, n, hw_), u, ht), padd(padd(c, n, -hw_), u, ht), padd(padd(c, n, -hw_), u, -ht)]
        out += shape(poly(q), color, line, max(2, 0.01 * D))
    return out


def body(P, pose, S, tag=None):
    """Stick body hanging from head params P (rest centre cx, cy). Returns (layers, joints)."""
    d = dict(HDEF)
    d.update(P)
    D = S['D']
    face = d['face']
    cx, cy = d['cx'], d['cy']
    lift = d['lift'] * D
    turnk = min(1.0, d['turn'] / 0.12)
    yo = pose.get('yoke', (0.0, 0.0))
    Y = (cx - face * 0.13 * D * turnk + face * yo[0] * D, cy + 0.71 * D + yo[1] * D - pose.get('shrug', 0.0) * D)
    lean = math.radians(pose.get('lean', 0.0))
    t = (-face * math.sin(lean), math.cos(lean))
    Hh = padd(Y, t, S['spine'] * pose.get('spine_k', 1.0))
    back = (-face * math.cos(lean), -math.sin(lean))
    mid = lerp(Y, Hh, 0.5)
    ctrl = padd(mid, back, 2 * pose.get('curve', 0.0) * D)
    spine_pts = [bez(Y, ctrl, Hh, k / 14.0) for k in range(15)]
    t0 = unit(Y, ctrl)
    side = (-t0[1], t0[0]) if False else (t0[1], -t0[0])
    if side[0] < 0:
        side = (-side[0], -side[1])
    sh = S['sh'] * pose.get('sh_k', 1.0)
    tilt = math.radians(pose.get('sh_tilt', 0.0))
    side = rot_pt(side, pose.get('sh_tilt', 0.0), (0, 0))
    Sn = padd(Y, side, -face * sh)       # near shoulder = back side of a 3/4 figure
    Sf = padd(Y, side, face * sh)        # far shoulder = facing side
    Nb = padd(Y, t0, -0.06 * D)
    Nt = (cx - face * 0.07 * D * turnk, cy - lift + 0.26 * D)
    Jt = dict(Y=Y, H=Hh, Sn=Sn, Sf=Sf, Nb=Nb, Nt=Nt, spine=spine_pts)
    L = {k: '' for k in ('back', 'far_leg', 'far_arm', 'spine', 'neck', 'anchor', 'near_leg', 'front', 'near_arm', 'over')}
    tint = S['tint']

    # ---- spine: slim tapered wedge on a C/S line
    sw0, sw1 = S['spine_w']
    L['spine'] = ('<path d="%s" fill="%s"/>' % (poly(limb(spine_pts, sw0, sw1)), tint) +
                  '<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(Hh[0]), f(Hh[1]), f(sw1 / 2), tint))
    if tag:
        REG['limbs'].append((tag + ' spine', spine_pts[::3] + [spine_pts[-1]], [sw0] * 6, tint))

    # ---- neck stub: skin, tinted outline, flat chin shadow; head is drawn after it
    nw = S['neck_w']
    nq = limb([Nb, Nt], nw, nw * 0.92)
    L['neck'] = shape(poly(nq), S['skin'], S['line'], S['lw'] * 0.8)
    jb = cy + 0.5 * D + max(0.0, (d['drop'] - d['lift']) * D)
    shp = [(Nb[0] - nw, jb - 0.04 * D), (Nb[0] + nw, jb - 0.04 * D), (Nb[0] + nw, jb + 0.055 * D), (Nb[0] - nw, jb + 0.055 * D)]
    UID[0] += 1
    L['neck'] += ('<defs><clipPath id="nk%d"><path d="%s"/></clipPath></defs><path d="%s" fill="%s" clip-path="url(#nk%d)"/>'
                  % (UID[0], poly(nq), poly(shp), dark(S['skin'], 0.12), UID[0]))

    # ---- costume anchor: its corners ARE the shoulder points
    anc = pose.get('anchor')
    if anc and anc[0] == 'kerchief':
        col = anc[1]
        ln = dark(col, 0.4)
        K = (Nb[0] + face * 0.05 * D, Y[1] + 0.065 * D)
        band = [padd(Sn, (0, -0.032 * D)), (Nb[0] - face * 0.10 * D, Nb[1] - 0.03 * D), (Nb[0] + face * 0.11 * D, Nb[1] - 0.025 * D),
                padd(Sf, (0, -0.032 * D)), padd(Sf, (face * 0.012 * D, 0.03 * D)), (K[0] + face * 0.06 * D, K[1] - 0.012 * D),
                (K[0] - face * 0.07 * D, K[1] - 0.012 * D), padd(Sn, (-face * 0.012 * D, 0.03 * D))]
        a = shape(smooth(band), col, ln, max(2.5, 0.018 * D))
        sw = pose.get('tail_swing', 0.0)
        for dx, L1_, L2_ in ((0.035, 0.10, 0.19), (-0.03, 0.09, 0.17)):
            p1 = (K[0] + face * (dx + sw * 0.4) * D, K[1] + L1_ * D)
            p2 = (K[0] + face * (dx * 1.6 + sw) * D, K[1] + L2_ * D)
            a += ribbon([K, p1, p2], 0.07 * D, 0.045 * D, col, max(2, 0.014 * D))
        a += shape(ell_d(K[0], K[1], 0.05 * D, 0.042 * D), col, ln, max(2, 0.014 * D))
        L['anchor'] = a
        Jt['knot'] = K
    elif anc and anc[0] == 'towel':
        col = anc[1]
        ln = dark(col, 0.4)
        loop = [padd(Sn, (0, -0.025 * D)), (Nb[0] - face * 0.12 * D, Nb[1] - 0.075 * D), (Nb[0] + face * 0.12 * D, Nb[1] - 0.075 * D),
                padd(Sf, (0, -0.025 * D)), padd(Sf, (0, 0.05 * D)), (Nb[0], Nb[1] + 0.01 * D), padd(Sn, (0, 0.05 * D))]
        L['back'] += shape(smooth(loop), col, ln, max(2.5, 0.018 * D))
        ends = ''
        for S0, inward, ln_ in ((Sn, face, 0.40), (Sf, -face, 0.34)):
            top = padd(S0, (inward * 0.035 * D, -0.03 * D))
            bot = padd(top, rot_pt((0, 1), -inward * 6 + pose.get('towel_swing', 0) * face, (0, 0)), ln_ * D)
            q = limb([top, bot], 0.13 * D, 0.12 * D)
            ends += shape(poly(q), col, ln, max(2.5, 0.018 * D))
            for tt in (0.78, 0.86):
                c = lerp(top, bot, tt)
                u = unit(top, bot)
                n = (-u[1], u[0])
                ends += stroke('M%s,%s L%s,%s' % (f(c[0] + n[0] * 0.05 * D), f(c[1] + n[1] * 0.05 * D),
                                                  f(c[0] - n[0] * 0.05 * D), f(c[1] - n[1] * 0.05 * D)), CREAM, max(2.5, 0.016 * D))
        L['anchor'] = ends

    # ---- legs
    sole = []
    for side_ in ('far', 'near'):
        gspec = pose['legs'][side_]
        K, An = solve_limb(Hh, gspec, S['thigh'], S['shin'], face)
        Jt[side_ + '_knee'], Jt[side_ + '_ankle'] = K, An
        s = tube([Hh, K, An], S['leg_w'], tint, tag and (tag + ' ' + side_ + ' leg'))
        ft = gspec.get('foot', {})
        if ft is not None:
            fs_, sy_ = foot(An, ft.get('toe', face), S, ft.get('rot', 0))
            s += fs_
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
            E, W = ik2(root, tgt, S['upper'] * gspec.get('k', 1.0), S['fore'] * gspec.get('k', 1.0), hint)
        else:
            E, W = solve_limb(root, gspec, S['upper'], S['fore'], face)
        Jt[side_ + '_elbow'], Jt[side_ + '_wrist'], Jt[side_ + '_sh'] = E, W, root
        s = tube([root, E, W], S['arm_w'], tint, tag and (tag + ' ' + side_ + ' arm'))
        if gspec.get('wraps'):
            s += wraps(E, W, D, gspec['wraps'])
        hd = gspec.get('hand', True)
        u = unit(E, W)
        if 'hand_dir' in gspec:
            u = unit((0, 0), gspec['hand_dir'])
        if gspec.get('hand_rot'):
            u = rot_pt(u, gspec['hand_rot'], (0, 0))
        tip = padd(W, u, S['hand_L'])
        Jt[side_ + '_tip'] = tip
        if gspec.get('clasp'):
            clasp_hands.append((W, u, gspec.get('thumb', -1)))
        elif hd:
            pad, th = mitten(W, u, S, gspec.get('thumb', -1), gspec.get('hand_scale', 1.0))
            s += pad + th
        L[pose.get('arm_layer', {}).get(side_, side_ + '_arm')] += s
    if clasp_hands:
        # the two clasped mittens show just behind the lower back
        for W, u, th in clasp_hands:
            pad, thb = mitten(W, u, S, th, 0.95)
            L['far_arm'] += pad + thb

    # ---- hip prop
    hp = pose.get('hip')
    if hp:
        up = unit(Hh, spine_pts[-4])
        b, fr = sash(Hh, up, face, D, hp[0], hp[1])
        L['back'] += b
        L['front'] += fr
    return L, Jt


def figure(P, pose, S, tag=None, over=''):
    L, Jt = body(P, pose, S, tag)
    g, info = head(P)
    seq = [L['back'], L['far_leg'], L['far_arm'], L['spine'], L['neck'], L['anchor'], L['near_leg'], L['front'],
           L['near_arm'], g, L['over'], over]
    return ''.join(seq), Jt, info


def report(name, P, Jt, info, S):
    D = S['D']
    skull_top = info['cap'][1] - D / 2
    Hs = Jt['sole'] - skull_top
    cap = info['cap']
    msg = ['%-12s D=%d H=%.0f (%.2f D, head %.1f%%)' % (name, D, Hs, Hs / D, 100 * D / Hs)]
    for side_ in ('near', 'far'):
        if side_ + '_wrist' not in Jt:
            continue
        pts = [Jt[side_ + '_sh'], Jt[side_ + '_elbow'], Jt[side_ + '_wrist'], Jt[side_ + '_tip']]
        dm = min(seg_dist(cap, a, b) for a, b in zip(pts, pts[1:])) - D / 2 - S['arm_w'][0] / 2
        msg.append('%s arm clear %.2fD tip-above-skull %.2fD' % (side_, dm / D, (skull_top - Jt[side_ + '_tip'][1]) / D))
    xs = [Jt['near_ankle'][0], Jt['far_ankle'][0], Jt['near_elbow'][0], Jt['far_elbow'][0], Jt['near_tip'][0], Jt['far_tip'][0]]
    msg.append('base span %.2fD' % ((max(xs) - min(xs)) / D))
    msg.append('head-hip offset %.2fD' % ((cap[0] - Jt['H'][0]) * P.get('face', 1) / D))
    print(' | '.join(msg), file=sys.stderr)


# ---------------------------------------------------------------- paper + doc
PAPER = ('<filter id="paper" x="0" y="0" width="100%" height="100%">'
         '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="11"/>'
         '<feColorMatrix type="matrix" values="1.2 1.2 1.2 0 -1.3  1.2 1.2 1.2 0 -1.3  1.2 1.2 1.2 0 -1.3  0 0 0 0 1"/>'
         '</filter>'
         '<filter id="black" x="-10%" y="-10%" width="120%" height="120%">'
         '<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>')


def paper(w, h, op=0.025):
    """Soft paper grain: contrast-stretched noise at <= 3 % opacity (no cut-paper texture)."""
    return '<rect width="%d" height="%d" filter="url(#paper)" opacity="%s"/>' % (w, h, op)


def svg_doc(w, h, body_, grain=0.05):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<defs>%s</defs>%s%s</svg>' % (w, h, w, h, PAPER, body_, paper(w, h, grain) if grain else ''))


def sil_doc(w, h, figs):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d"><defs>%s</defs>'
            '<rect width="%d" height="%d" fill="#FFFFFF"/><g filter="url(#black)">%s</g></svg>' % (w, h, w, h, PAPER, w, h, ''.join(figs)))


# ================================================================ cast
def master_head(**kw):
    p = dict(skin=SKIN_M, line=LINE_M, seam=0.60, face=1, turn=0.12, jaw_tint=0.06,
             brow='cloud', hair='flicks', beard=0.55, beard_w=0.38, nose='bulb', wrinkles=True, lobes=True,
             ear_p=0.12, ear_pf=0.07, teeth_up=2, eyes='closed')
    p.update(kw)
    return p


def snap_head(**kw):
    p = dict(skin=SKIN_S, line=LINE_S, seam=0.55, face=-1, turn=0.12, jaw_tint=0.0, jut=0.04,
             brow='bar', brow_w=0.27, brow_h=0.065, brow_color=HAIR, brow_gap=0.10, hair='buzz', hair_color=HAIR,
             stubble=True, teeth_low=4, nose='broad', lobes=False, ear_p=0.10, ear_pf=0.06, eye_d=0.07,
             eye_color='#2A1C14', wrinkles=False, mouth='a', tuft=False)
    p.update(kw)
    return p


def auto_lift(drop, shrug=0.0, margin=0.02):
    """Cap lift so a dropped jaw ends at the shoulder yoke (0.71 D below the rest centre) instead of the chest."""
    return max(0.0, drop - 0.21 + shrug + margin)


def master_spec(D):
    return body_spec(D, SKIN_M, LINE_M, TINT_M, spine=0.97, legs=(0.74, 0.70))


def snap_spec(D):
    return body_spec(D, SKIN_S, LINE_S, TINT_S, spine=0.95, legs=(0.73, 0.69))


M_ANCHOR = ('kerchief', PIST)
M_HIP = (PIST, [[(0.04, 0.10), (0.07, 0.20)], [(-0.03, 0.10), (-0.04, 0.19)]])


def clasp_arms(cx=0.15, cy=0.27, kf=0.86, kn=1.0):
    return dict(far=dict(clasp=True, cx=cx, cy=cy, k=kf, thumb=1), near=dict(clasp=True, cx=cx, cy=cy, k=kn, thumb=-1))


def stone(x0, x1, top, bottom, top_col=None, body_col=None):
    """Flat garden stone: pale top face over a darker body (feet read on the face)."""
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
    """Shift the figure vertically so the lowest sole lands on sole_y."""
    P = dict(P)
    _, Jt = body(P, pose, S)
    P['cy'] += sole_y - Jt['sole']
    return P


# ================================================================ scene
def build_scene():
    W, H = 1080, 1920
    bg, fg, sil = [], [], []
    REG['limbs'] = []
    bg.append('<rect width="1080" height="1920" fill="%s"/>' % WALL)
    bg.append('<rect width="1080" height="232" fill="%s"/>' % SKY)
    # distant pines on the sky line (flat, muted)
    for x, w_, h_ in ((120, 120, 70), (300, 90, 48), (760, 140, 80), (960, 100, 56)):
        bg.append('<path d="%s" fill="%s"/>' % (smooth([(x - w_ / 2, 232), (x - w_ * 0.3, 232 - h_ * 0.7), (x, 232 - h_),
                                                        (x + w_ * 0.35, 232 - h_ * 0.6), (x + w_ / 2, 232)]), mix(SKY, PIST, 0.45)))
    # cream dojo wall + morning light bands
    bg.append('<rect x="0" y="260" width="1080" height="710" fill="%s"/>' % WALL)
    for x0, w_ in ((150, 130), (560, 90), (820, 120)):
        bg.append('<path d="%s" fill="%s" opacity="0.32"/>' % (poly([(x0, 262), (x0 + w_, 262), (x0 + w_ - 230, 970), (x0 - 230, 970)]),
                                                               '#FFF8EA'))
    bg.append('<rect x="0" y="900" width="1080" height="70" fill="%s"/>' % mix(WALL, LATTE, 0.35))
    bg.append(stroke('M0,900 L1080,900', mix(WALL, LATTE, 0.6), 4))
    for x0 in (14, 1024):
        bg.append(shape(poly([(x0, 262), (x0 + 42, 262), (x0 + 42, 975), (x0, 975)]), '#B8977A', dark('#B8977A', 0.3), 3))
    # roof eave: dark edge under the sky
    bg.append(shape(poly([(-10, 226), (1090, 226), (1090, 262), (-10, 262)]), ESP, dark(ESP, 0.3), 3))
    for x in range(20, 1080, 64):
        bg.append('<rect x="%d" y="262" width="26" height="12" fill="%s"/>' % (x, mix(ESP, LATTE, 0.3)))

    # ---- witnesses behind the hedge (hazed 20%): tea lady at the left post, two disciples
    back_figs = []
    Ssm = 175
    for (x, y, skin, hair, hcol, face, gz) in ((738, 440, '#6B4430', 'buzz', HAIR, -1, (-0.06, 0.05)),
                                               (948, 462, '#E6B48E', 'topknot', '#8E877C', -1, (-0.06, 0.04))):
        S = body_spec(Ssm, skin, dark(skin, 0.38), dark(skin, 0.62) if skin != '#6B4430' else '#2C1C14', spine=0.95)
        Pd = dict(cx=x, cy=y, D=Ssm, face=face, turn=0.10, seam=0.58, skin=skin, line=dark(skin, 0.35),
                  brow='bar', brow_w=0.26, brow_h=0.075, brow_color=dark(hcol, 0.1) if hair == 'buzz' else '#6E675D',
                  brow_top=False, brow_raise=(0.0, 0.0), brow_gap=0.058, eye_y=0.45, hair=hair, hair_color=hcol, nose='broad', nose_s=0.85, lobes=False, tuft=False,
                  eye_d=0.07, gaze=gz, drop=0.26, lift=auto_lift(0.26), teeth_low=3, stubble=(hair == 'buzz') and '#4E301F',
                  ear_p=0.09, ear_pf=0.05, mouth='d', jaw_tint=0.05, buzz_rise=0.05)
        pose = dict(lean=-4, curve=0.03, anchor=('towel', mix(CINN, MILK, 0.15)) if hair == 'buzz' else ('kerchief', '#8C9AA6'),
                    hip=(CINN, [[(0.03, 0.12), (0.05, 0.22)]]),
                    arms=dict(far=dict(ang=(20, 6), thumb=1), near=dict(ang=(-16, -4), thumb=-1)),
                    legs=dict(far=dict(ang=(6, 2), foot=None), near=dict(ang=(-6, -2), foot=None)))
        g, _, _ = figure(Pd, pose, S)
        back_figs.append(g)
    # tea lady (witness): moves one brow and one corner of her jaw
    St = body_spec(170, '#D6A27C', dark('#D6A27C', 0.38), '#4A3A44', spine=0.95)
    Pt = dict(cx=128, cy=440, D=170, face=1, turn=0.10, seam=0.60, skin='#D6A27C', line=dark('#D6A27C', 0.36),
              brow='bar', brow_w=0.22, brow_h=0.06, brow_color='#8F8A82', brow_raise=(0.0, 0.07), hair='bun',
              hair_color='#A9A49B', nose='button' if False else 'bulb', nose_s=0.7, lobes=True, tuft=False, eye_d=0.07,
              gaze=(0.05, 0.02), drop=0.0, jaw_tilt=-7, mouth='f', mouth_w=0.18, ear_p=0.08, ear_pf=0.05)
    pose_t = dict(lean=2, curve=0.03, anchor=('kerchief', '#C9B8D0'), hip=('#7D6A86', [[(0.03, 0.1), (0.04, 0.2)]]),
                  arms=dict(far=dict(to=(200, 700), hint=(1, 1), hand_dir=(1, -0.2), thumb=-1),
                            near=dict(to=(196, 716), hint=(-0.2, 1), hand_dir=(1, 0.1), thumb=1)),
                  legs=dict(far=dict(ang=(4, 2), foot=None), near=dict(ang=(-4, -2), foot=None)))
    gt, Jtl, _ = figure(Pt, pose_t, St)
    cup = Jtl['far_wrist']
    cupsvg = (shape(ell_d(cup[0] + 30, cup[1] - 2, 34, 8), CREAM, dark(CREAM, 0.4), 3) +
              shape(poly([(cup[0] + 14, cup[1] - 30), (cup[0] + 46, cup[1] - 30), (cup[0] + 40, cup[1] - 6), (cup[0] + 20, cup[1] - 6)]),
                    PIST, dark(PIST, 0.4), 3))
    back_figs.append(gt + cupsvg)
    bg.extend(back_figs)
    sil.extend(back_figs)
    bg.append('<rect x="0" y="262" width="1080" height="710" fill="%s" opacity="0.20"/>' % MILK)

    # pistachio hedge line
    hp = [(-30, 1090), (-30, 965)]
    for i in range(24):
        hp.append((-20 + i * 49, 955 + (12 if i % 2 else -8)))
    hp += [(1110, 965), (1110, 1090)]
    hedge = mix(PIST, ESP, 0.10)
    bg.append(shape(smooth(hp), hedge, dark(hedge, 0.3), 4))
    for x, y in ((60, 1010), (230, 1040), (420, 1000), (600, 1036), (800, 1004), (980, 1040)):
        bg.append(stroke('M%d,%d q22,-24 46,-10' % (x, y), dark(hedge, 0.2), 5))
    # latte sand, pebbles, flat shadow band
    bg.append('<rect x="0" y="1062" width="1080" height="520" fill="%s"/>' % SAND)
    for k, y in enumerate(range(1110, 1560, 62)):
        bg.append(stroke('M-10,%d C260,%d 620,%d 1090,%d' % (y, y - 8 + k % 2 * 6, y + 10, y - 2), dark(SAND, 0.05), 4))
    bg.append('<rect x="0" y="1575" width="1080" height="345" fill="%s"/>' % GROUND_SH)
    for x, y, r in ((610, 1462, 11), (640, 1478, 7), (930, 1420, 10), (120, 1180, 9), (860, 1130, 8), (180, 1700, 14),
                    (216, 1716, 9), (560, 1790, 12), (900, 1690, 15), (940, 1712, 8)):
        bg.append(shape(ell_d(x, y, r * 1.4, r), mix(SAND, STONE, 0.45) if y < 1575 else dark(GROUND_SH, 0.12), None, 3))

    # ---- MASTER: crane stance on his stone, hands clasped behind, ball resting on the jutted chin
    Dm = 260
    Sm = master_spec(Dm)
    Pm = master_head(cx=320, cy=700, D=Dm, eyes='closed', mouth='b', brow_raise=(0.0, 0.05), jut=0.12, jaw_tilt=9,
                     beard_swing=-28, closed_t=0.046, tilt=10, jaw_front=True)
    pose_m = dict(lean=-14, curve=-0.035, anchor=M_ANCHOR, hip=M_HIP, tail_swing=-0.03,
                  arms=clasp_arms(0.15, 0.30, 0.84),
                  legs=dict(far=dict(ang=(2, 0), straight=True, foot=dict(toe=1)),
                            near=dict(to=None, rel=(0, 0), foot=dict(toe=1, rot=62))))
    # standing leg first, then the raised knee folds out to the near side (screen-left) with the foot at the standing knee
    _, J0 = body(Pm, dict(pose_m, legs=dict(far=pose_m['legs']['far'], near=dict(ang=(0, 0), foot=None))), Sm)
    hip = J0['H']
    kn = J0['far_knee']
    pose_m['legs']['near'] = dict(pts=((-0.52 * Dm, 0.30 * Dm), (kn[0] - hip[0] - 0.05 * Dm, kn[1] - hip[1] + 0.02 * Dm)),
                                  foot=dict(toe=1, rot=58))
    _, Jm = body(Pm, pose_m, Sm)
    st_top = Jm['sole'] - 16
    bg.append(cast_shadow(Jm['H'][0] + 10, 1572, 230, 14, dark(GROUND_SH, 0.1)))
    bg.append(stone(Jm['H'][0] - 190, Jm['H'][0] + 180, st_top, 1568))
    gm, Jm, mi = figure(Pm, pose_m, Sm, tag='master')
    fg.append(gm)
    sil.append(gm)
    report('scene master', Pm, Jm, mi, Sm)

    # the bell temari rests on the jutted chin shelf
    r_ball = 0.15 * Dm
    cc = mi['chin_corner']
    capc, R = mi['cap'], Dm / 2
    # the ball sits on the jutted, tilted jaw shelf (its lower-left touching the shelf corner)
    ball = (cc[0] + r_ball * 0.30, cc[1] - r_ball * 0.95)

    # ---- SNAP: long lunge, both mittens clapped on the air where the ball was a beat ago, jaw dropped
    Ds = 250
    Ss = snap_spec(Ds)
    clap = (500, 1290)
    Ps = snap_head(cx=678, cy=902, D=Ds, drop=0.50, lift=auto_lift(0.50, 0.0, -0.03), jut=0.04, mouth='d', eye_d=0.056,
                   brow_top=True, brow_jump=0.07, brow_in=-14, brow_out=0.06, gaze=(-0.045, 0.05), teeth_low=4)
    _Y = (Ps['cx'] + 0.13 * Ds, Ps['cy'] + 0.71 * Ds)
    adir = unit((_Y[0] + 0.27 * Ds, _Y[1]), clap)          # pointing direction of the locked near arm
    nrm = (adir[1], -adir[0]) if adir[1] * 0 + (-adir[0]) > 0 else (-adir[1], adir[0])
    nrm = (abs(adir[1]), -abs(adir[0]) * (1 if adir[0] < 0 else -1))
    w_near = padd(clap, nrm, 0.058 * Ds)
    w_far = padd(clap, nrm, -0.058 * Ds)
    sd = sole_drop(Ss)
    pose_s = dict(lean=8, curve=0.04, anchor=('towel', CINN), hip=(CINN, [[(0.16, -0.10), (0.36, -0.16), (0.58, -0.10)],
                                                                         [(0.15, -0.02), (0.34, -0.02), (0.54, 0.06)]]),
                  towel_swing=8,
                  arms=dict(near=dict(to=w_near, straight=True, hint=(0, 1), thumb=1, wraps=CINN, hand_dir=adir, hand_scale=1.08),
                            far=dict(to=w_far, hint=(0.2, 1), thumb=-1, wraps=CINN, hand_dir=adir, hand_scale=1.08)),
                  arm_layer=dict(near='over'),
                  legs=dict(near=dict(to=(1049, 1555 - sd - 52), straight=True, hint=(1, -1), foot=dict(toe=-1, rot=52)),
                            far=dict(to=(588, 1555 - sd), hint=(-1, -0.6), foot=dict(toe=-1))))
    _, Js = body(Ps, pose_s, Ss)
    fg.append(cast_shadow(780, 1566, 260, 13, mix(SAND, GROUND_SH, 0.6)))
    fg.append(dust(Js['far_ankle'][0] - 40, 1546, 0.85, -1))
    fg.append(dust(Js['near_ankle'][0] - 30, 1546, 0.7, 1))
    gs, Js, si = figure(Ps, pose_s, Ss, tag='snap')
    fg.append(gs)
    sil.append(gs)
    report('scene snap', Ps, Js, si, Ss)

    # ---- marks: dotted arc from the empty clap up to the chin, ghost balls, ting, clap ticks
    cw = lerp(Js['near_tip'], Js['far_tip'], 0.5)
    start = (cw[0] - 6, cw[1] - 46)
    end = (ball[0] + 6, ball[1] + r_ball + 8)
    ctrl = (start[0] + 70, (start[1] + end[1]) / 2 + 20)
    fg.append(dotted('M%s,%s Q%s,%s %s,%s' % (f(start[0]), f(start[1]), f(ctrl[0]), f(ctrl[1]), f(end[0]), f(end[1])), w=12, gap=26))
    gm1 = bez(start, ctrl, end, 0.5)
    fg.append(ghost_ball(cw[0] - 4, cw[1] - 8, r_ball, 0.6))
    fg.append(ghost_ball(gm1[0], gm1[1], r_ball * 0.92, 0.5))
    fg.append(ticks(cw[0] - 4, cw[1] - 8, r_ball + 14, r_ball + 46, (-162, -128, 162, 128, -94), dark(LATTE, 0.55), 8))
    fg.append(puff(cw[0] - 56, cw[1] + 14, 0.9, -1))
    fg.append(puff(cw[0] + 34, cw[1] + 30, 0.7, 1))
    fg.append(temari(ball[0], ball[1], r_ball))
    fg.append(ting(ball[0] + 14, ball[1] - r_ball - 2, 1.0))

    full = svg_doc(W, H, ''.join(bg + fg), 0.025)
    open(os.path.join(HERE, 'scene.svg'), 'w').write(full)
    open(os.path.join(HERE, 'scene_bg.svg'), 'w').write(svg_doc(W, H, ''.join(bg), 0))
    open(os.path.join(HERE, 'scene_sil.svg'), 'w').write(sil_doc(W, H, sil))
    return dict(master=Jm, snap=Js)


# ================================================================ poses sheet
def build_poses():
    W = H = 1080
    b, sil = [], []
    b.append('<rect width="1080" height="1080" fill="%s"/>' % MILK)
    b.append('<rect x="0" y="990" width="1080" height="90" fill="%s"/>' % SAND)
    b.append(stroke('M0,990 L1080,990', mix(SAND, GROUND_SH, 0.4), 4))
    D = 200
    S = master_spec(D)
    ST = 962

    def base(x, w=150):
        b.append(cast_shadow(x, 992, w + 10, 9, mix(SAND, GROUND_SH, 0.6)))
        b.append(stone(x - w, x + w, ST, 990, mix(STONE, MILK, 0.66), mix(STONE, MILK, 0.36)))

    # (1) READY: feet together on the stone, hands clasped behind, elbows out like wings, slight bow
    P1 = master_head(cx=190, cy=340, D=D, face=1, eyes='closed', mouth='a', beard_swing=6)
    pose1 = dict(lean=7, curve=0.05, anchor=M_ANCHOR, hip=M_HIP, arms=clasp_arms(0.20, 0.17, 0.80, 0.86),
                 legs=dict(far=dict(rel=(0.13 * D, 1.40 * D), hint=(1, 0), foot=dict(toe=1)),
                           near=dict(rel=(-0.08 * D, 1.42 * D), hint=(1, 0), foot=dict(toe=1))))
    P1 = place(P1, pose1, S, ST + 14)
    base(190)
    g, J1, i1 = figure(P1, pose1, S)
    b.append(g)
    sil.append(g)
    cu = i1['curl']
    b.append(temari(cu[0] + 0.02 * D, cu[1] - 0.15 * D - 4, 0.15 * D))
    report('pose1', P1, J1, i1, S)

    # (2) SIGNATURE 'CHIN VOLLEY': lean back on one straight leg, knee up, one arm straight overhead after the ball
    P2 = master_head(cx=540, cy=340, D=D, face=1, eyes='closed', mouth='b', brow_raise=(0.0, 0.05), jut=0.10, jaw_tilt=12,
                     tilt=8, beard_swing=-34, jaw_front=True)
    pose2 = dict(lean=-14, curve=-0.04, anchor=M_ANCHOR, hip=M_HIP, tail_swing=-0.04,
                 arms=dict(near=dict(ang=(-153, -153), straight=True, thumb=1),
                           far=dict(clasp=True, cx=0.18, cy=0.22, k=0.82, thumb=1)),
                 legs=dict(far=dict(ang=(-3, 0), straight=True, foot=dict(toe=1)),
                           near=dict(ang=(78, -6), foot=dict(toe=1, rot=55))))
    P2 = place(P2, pose2, S, ST + 14)
    base(540)
    g, J2, i2 = figure(P2, pose2, S)
    b.append(g)
    sil.append(g)
    report('pose2', P2, J2, i2, S)
    tip = i2['chin_corner']
    mt = J2['near_tip']
    ballp = (mt[0] + 10, mt[1] - 70)
    start = (tip[0] + 8, tip[1] - 34)
    ctrl = (start[0] + 20, ballp[1] - 60)
    b.append(dotted('M%s,%s Q%s,%s %s,%s' % (f(start[0]), f(start[1]), f(ctrl[0]), f(ctrl[1]), f(ballp[0] + 34), f(ballp[1] - 6)), w=8, gap=18))
    b.append(ghost_ball(tip[0] + 6, tip[1] - 0.15 * D - 4, 0.15 * D, 0.55))
    b.append(temari(ballp[0], ballp[1], 0.15 * D))
    b.append(ting(ballp[0] + 8, ballp[1] - 32, 0.75))

    # (3) BIG REACTION 'JAW-DROP HOP': 60 px up, knees tucked, arms flung overhead, jaw dropped to the yoke
    shrug3 = 0.04
    P3 = master_head(cx=880, cy=340, D=D, face=-1, turn=0.0, eyes='open', eye_d=0.07, mouth='d', drop=0.40,
                     lift=auto_lift(0.40, shrug3, 0.0), brow_top=True, beard_swing=30, ear_p=0.10)
    pose3 = dict(lean=0, curve=0.0, shrug=shrug3, sh_k=1.24, anchor=M_ANCHOR, hip=M_HIP, tail_swing=0.05,
                 arms=dict(far=dict(ang=(159, 159), straight=True, thumb=1),
                           near=dict(ang=(-159, -159), straight=True, thumb=-1)),
                 legs=dict(far=dict(ang=(42, -22), foot=dict(toe=-1, rot=30)),
                           near=dict(ang=(-36, 22), foot=dict(toe=1, rot=30))))
    P3 = place(P3, pose3, S, ST + 14 - 60)
    base(880)
    for x in (820, 880, 940):
        b.append(stroke('M%d,%d L%d,%d' % (x, ST - 30, x, ST - 8), dark(LATTE, 0.5), 5))
    b.append(dust(880 - 150, ST + 4, 0.8, -1))
    b.append(dust(880 + 150, ST + 4, 0.8, 1))
    g, J3, i3 = figure(P3, pose3, S)
    b.append(g)
    sil.append(g)
    report('pose3', P3, J3, i3, S)
    open(os.path.join(HERE, 'poses.svg'), 'w').write(svg_doc(W, H, ''.join(b), 0.025))
    open(os.path.join(HERE, 'poses_sil.svg'), 'w').write(sil_doc(W, H, sil))
    return dict(p1=J1, p2=J2, p3=J3)


# ================================================================ lineup (540 x 1080, hero 900 px tall)
def build_lineup():
    W, H = 540, 1080
    D = 250
    S = master_spec(D)
    P = master_head(cx=0, cy=0, D=D, face=-1, eyes='open', mouth='b', beard_swing=4)
    pose = dict(lean=4, curve=0.04, anchor=M_ANCHOR, hip=M_HIP, arms=clasp_arms(0.20, 0.17, 0.80, 0.86),
                legs=dict(far=dict(rel=(-0.15 * D, 1.40 * D), hint=(-1, 0), foot=dict(toe=-1)),
                          near=dict(rel=(0.10 * D, 1.42 * D), hint=(-1, 0), foot=dict(toe=-1))))
    g, Jt, info = figure(P, pose, S)
    top, sole = info['top'], Jt['sole']
    k = 900.0 / (sole - top)
    xs = [Jt['near_elbow'][0], Jt['far_elbow'][0], info['cap'][0] - D / 2, info['cap'][0] + D / 2]
    xc = (min(xs) + max(xs)) / 2
    tr = 'translate(%s %s) scale(%s) translate(%s %s)' % (f(270), f(1010), '%.5f' % k, f(-xc), f(-sole))
    cu = info['curl']
    ball = temari(cu[0] - 0.02 * D, cu[1] - 0.15 * D - 4, 0.15 * D)
    body_ = '<rect width="540" height="1080" fill="#EDEAE4"/><g transform="%s">%s%s</g>' % (tr, g, ball)
    open(os.path.join(HERE, 'lineup.svg'), 'w').write(svg_doc(W, H, body_, 0))
    open(os.path.join(HERE, 'lineup_sil.svg'), 'w').write(sil_doc(W, H, ['<g transform="%s">%s</g>' % (tr, g)]))
    print('lineup: top %.1f sole %.1f scale %.4f -> %.1f px tall, D %.1f px' % (top, sole, k, (sole - top) * k, D * k), file=sys.stderr)
    report('lineup', P, Jt, info, S)


if __name__ == '__main__':
    js = build_scene()
    jp = build_poses()
    build_lineup()
    rnd = lambda v: [round(v[0]), round(v[1])] if isinstance(v, tuple) else v
    out = {}
    for k, v in dict(js, **jp).items():
        out[k] = {kk: rnd(vv) for kk, vv in v.items() if isinstance(vv, tuple)}
    json.dump(out, open(os.path.join(HERE, 'joints.json'), 'w'))
    json.dump(REG['limbs'], open(os.path.join(HERE, 'probes.json'), 'w'))
