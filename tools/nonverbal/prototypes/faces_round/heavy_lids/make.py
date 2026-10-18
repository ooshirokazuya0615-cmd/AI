#!/usr/bin/env python3
"""Heavy Lids / 半目の夜勤 -- ROUND-HEAD stick version.

One round-head face rig  : head(uid, cx, cy, D, H, E, turn)
    H = character head spec (skin, chin weight, eye geometry, ears, hair break...)
    E = expression parameters (lids, pupils, mouth, cowlick state, marks)
One stick-body rig       : figure(F, P)
    F = character body spec (proportions in D, colours), P = pose
Every figure in scene.svg, poses.svg and lineup.svg is figure(...) + head(...).
All sizes are fractions of D = the skull-circle diameter (ears, hair, nose excluded).
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

INK = '#1B1411'
WHITE = '#FFF8EC'
COFFEE = '#241A15'
AMBER = '#F2C46D'
MINT = '#9FCFB8'
MOUTH_DARK = '#3A1E18'
PEG = '#8A5A3A'
BRASS = '#B8893A'
STAR = '#FFE7A8'
CREAM = '#E9DCC6'
WALNUT = '#6B4526'
BRISTLE = '#D9B25E'
TIN = '#9AA39A'
ROPE = '#D8C49A'

REG = {'limbs': [], 'figs': []}      # registry for the automatic checks


def f(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def pts(points):
    return ' '.join('%s,%s' % (f(x), f(y)) for x, y in points)


def shade(c, k):
    c = c.lstrip('#')
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v * (1 - k))))) for v in (r, g, b))


def ang(p, q):
    return math.atan2(q[1] - p[1], q[0] - p[0])


def norm(v):
    L = math.hypot(v[0], v[1]) or 1e-9
    return (v[0] / L, v[1] / L)


def add(p, v, k=1.0):
    return (p[0] + v[0] * k, p[1] + v[1] * k)


def bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return out


def qbez(p0, c, p1, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in [i / n for i in range(n + 1)]]


def taper(center, w0, w1=1.2):
    n = len(center)
    left, right = [], []
    for i, (x, y) in enumerate(center):
        a = center[max(i - 1, 0)]
        b = center[min(i + 1, n - 1)]
        nx, ny = norm((-(b[1] - a[1]), b[0] - a[0]))
        w = w0 + (w1 - w0) * ((i / (n - 1)) ** 0.9)
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    poly = left + right[::-1]
    return 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in poly) + ' Z'


def point_at(poly, dist):
    acc = 0.0
    for i in range(1, len(poly)):
        seg = math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1])
        if acc + seg >= dist:
            t = (dist - acc) / (seg or 1)
            return (poly[i - 1][0] + (poly[i][0] - poly[i - 1][0]) * t, poly[i - 1][1] + (poly[i][1] - poly[i - 1][1]) * t)
        acc += seg
    return poly[-1]


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay or 1e-9
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def ik(root, target, l1, l2, bend=1, straight=False, min_bend=7):
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(dx, dy) or 1e-6
    if straight:
        dmax = (l1 + l2) * 0.9999
    else:
        dmax = math.sqrt(l1 * l1 + l2 * l2 + 2 * l1 * l2 * math.cos(math.radians(min_bend)))
    d2 = max(min(d, dmax), abs(l1 - l2) + 1)
    base = math.atan2(dy, dx)
    a = math.acos(max(-1.0, min(1.0, (l1 * l1 + d2 * d2 - l2 * l2) / (2 * l1 * d2))))
    a2 = base - bend * a
    mid = (root[0] + l1 * math.cos(a2), root[1] + l1 * math.sin(a2))
    end = (root[0] + d2 * math.cos(base), root[1] + d2 * math.sin(base))
    return mid, end, d - d2


def fk(root, a1, l1, a2, l2):
    """angles in degrees from straight down, + toward screen right; a2 relative to a1"""
    t1 = math.radians(a1)
    mid = (root[0] + l1 * math.sin(t1), root[1] + l1 * math.cos(t1))
    t2 = math.radians(a1 + a2)
    end = (mid[0] + l2 * math.sin(t2), mid[1] + l2 * math.cos(t2))
    return mid, end


# =====================================================================
#  ROUND-HEAD FACE RIG
# =====================================================================
COWLICK = {     # (u, v) in D; +u = toward the BACK of the head, -v = up.  Root on the rim at 11 o'clock.
    'soft':  [(0, 0), (0.0, -0.11), (0.10, -0.22), (0.14, -0.13)],
    'stiff': [(0, 0), (0.004, -0.07), (-0.006, -0.14), (0.0, -0.215)],
    'hook':  [(0, 0), (0.03, -0.15), (-0.08, -0.23), (-0.12, -0.14)],
    'wilt':  [(0, 0), (0.03, -0.075), (0.11, -0.085), (0.17, -0.01)],
}

LOU_H = dict(skin='#D9A383', chin='#C08E70', chin_dots='#A8785E', chin_frac=0.33, chin_sag=0.04,
             eye_w=0.34, eye_d=0.20, eye_top=0.40, eye_gap=0.08, pupil=0.075, rim=0.018, lid_w=0.038,
             outline=0.0215, ears=True, ear_prot=0.07, cowlick=True, sideburns=True, nose=0.06,
             mouth_back=0.06)
DOT_H = dict(skin='#7B4F3A', chin='#683F2E', chin_dots=None, chin_frac=0.30, chin_sag=0.11,
             eye_w=0.36, eye_d=0.24, eye_top=0.405, eye_gap=0.08, pupil=0.05, rim=0.018, lid_w=0.036,
             outline=0.0215, ears=True, ear_prot=0.065, ear_stud=MINT, cowlick=False, sideburns=False, nose=0.05,
             hair='bun', hair_color='#3A1C1E', bags=True, mouth_back=0.04)
GRAMPS_H = dict(skin='#B98260', chin='#A08371', chin_dots='#8A6E5E', chin_frac=0.32, chin_sag=0.04,
                eye_w=0.30, eye_d=0.17, eye_top=0.43, eye_gap=0.09, pupil=0.07, rim=0.02, lid_w=0.04,
                outline=0.024, ears=True, ear_prot=0.075, cowlick=False, sideburns=False, nose=0.06,
                tufts='#BDB6AA', creases=True, bags=True, mouth_back=0.05)

EXPR = {
    'neutral':  dict(lid=(0.55, 0.55), pupils=((0, 1), (0, 1)), mouth='a', cowlick='soft'),
    'surprised': dict(lid=(0, 0), eye_scale=1.18, eye_dy=-0.045, gap_scale=0.7, pupil_scale=0.72,
                      pupils=((0, .42), (0, .42)), mouth='c', mouth_dx=0, cowlick='stiff', emanata=(-1, 1)),
    'angry':    dict(lid=(0.45, 0.45), lid_tilt=22, low=(0.30, 0.30), pupils=((0, .55), (0, .55)),
                     mouth='f', mouth_dx=0, cowlick='hook'),
    'smug':     dict(lid=(0.85, 0.85), low=(0.0, 0.0), pupils=((0.6, 1), (0.6, 1)), mouth='e', cowlick='soft'),
    'panic':    dict(lid=(0.05, 0.18), pupil_scale=0.75, pupils=((-1, .45), (1, .45)),
                     ghosts=((0, 0.2, .5, .4), (1, -0.2, .5, .4)), mouth='d', sweat=1, cowlick='stiff',
                     tremble=True, bowl_tilt=7),
    'sideeye':  dict(lid=(0.70, 0.70), pupils=((1, .5), (1, .5)), mouth='a', mouth_turn=0.012,
                     cowlick='wilt', gloom=True),
}


def head(uid, cx, cy, D, H, E, turn=0.0, mark_color=WHITE):
    """One round head.  Returns (svg, info).  turn: -1 = 3/4 facing screen-left, +1 = 3/4 facing right."""
    R = D / 2.0
    t = max(-1.2, min(1.2, turn))
    at = abs(t)
    bs = -1 if t >= 0 else 1                       # screen-x direction of the back of the head
    OL = max(H.get('outline', 0.0215) * D, 3.0)
    sq = E.get('squash', 0.0)
    skin = H['skin']
    o = []
    info = dict(top=cy - R, D=D, cx=cx, cy=cy)
    tr = ''
    if sq:
        tr = ' transform="translate(%s %s) scale(%s %s) translate(%s %s)"' % (
            f(cx), f(cy + R), f(1 + sq), f(1 - sq), f(-cx), f(-(cy + R)))
    o.append('<g id="%s"%s>' % (uid, tr))
    o.append('<defs><clipPath id="%s-hc"><circle cx="%s" cy="%s" r="%s"/></clipPath></defs>' % (uid, f(cx), f(cy), f(R)))

    # ---------- ears: ink-ringed half discs, 0.15 x 0.20 D, at 0.50 D height (behind the skull)
    if H.get('ears', True):
        for side in (-1, 1):
            prot = H.get('ear_prot', 0.07)
            if at > 0.05:
                prot = prot + 0.015 if side == bs else prot - 0.01
            if E.get('hide_ear') == side:
                continue
            ew, eh = 0.075 * D, 0.10 * D
            ecx = cx + side * (R + prot * D - ew)
            ecy = cy
            o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                f(ecx), f(ecy), f(ew), f(eh), skin, INK, f(OL)))
            o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(ecx + side * 0.012 * D), f(ecy - 0.048 * D), f(ecx + side * 0.06 * D), f(ecy),
                f(ecx + side * 0.012 * D), f(ecy + 0.048 * D), INK, f(max(0.014 * D, 2.5))))
            if H.get('ear_stud'):
                o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                    f(ecx + side * 0.03 * D), f(ecy + 0.068 * D), f(0.024 * D), H['ear_stud'], INK, f(max(0.01 * D, 2))))
    # ---------- grey side tufts (gramps): break the circle above the ears
    if H.get('tufts'):
        for side in (-1, 1):
            if E.get('hide_ear') == side:
                continue
            bx = cx + side * R * 0.93
            by = cy - 0.20 * D
            tuft = [(bx - side * 0.04 * D, by + 0.12 * D), (bx + side * 0.06 * D, by + 0.06 * D),
                    (bx + side * 0.10 * D, by - 0.01 * D), (bx + side * 0.03 * D, by - 0.06 * D),
                    (bx + side * 0.07 * D, by - 0.12 * D), (bx - side * 0.05 * D, by - 0.10 * D)]
            o.append('<path d="M%s Q%s %s Q%s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                pts([tuft[0]]), pts([tuft[1]]), pts([tuft[2]]), pts([tuft[3]]), pts([tuft[4]]), pts([tuft[5]]), pts([tuft[0]]),
                H['tufts'], INK, f(OL * 0.8)))

    # ---------- bun behind / on the head (Dot) -- pencil goes behind the bun disc
    bun = None
    if H.get('hair') == 'bun':
        a = math.radians(42)
        br = 0.14 * D
        bx, by = cx + bs * (R + 0.03 * D) * math.sin(a), cy - (R + 0.03 * D) * math.cos(a)
        bun = (bx, by, br)
        info['top'] = min(info['top'], by - br)

    # ---------- skin layer (re-used inside the lids)
    sk = ['<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(cx), f(cy), f(R), skin)]
    xc = cx + 0.09 * t * D                        # feature cluster centre (shifts toward the facing side)
    if H.get('chin'):
        yt = cy + R - H['chin_frac'] * D
        sag = H.get('chin_sag', 0.04) * D
        band = 'M%s,%s Q%s,%s %s,%s L%s,%s L%s,%s Z' % (
            f(cx - 1.25 * R), f(yt - sag * 0.6), f(xc), f(yt + sag * 1.4), f(cx + 1.25 * R), f(yt - sag * 0.6),
            f(cx + 1.25 * R), f(cy + R + 5), f(cx - 1.25 * R), f(cy + R + 5))
        sk.append('<path d="%s" fill="%s" clip-path="url(#%s-hc)"/>' % (band, H['chin'], uid))
        if H.get('chin_dots'):
            dots = []
            step = 0.047 * D
            row = 0
            yy = yt + 0.03 * D
            while yy < cy + R:
                xx = cx - R + (row % 2) * step / 2
                while xx < cx + R:
                    u = (xx - xc) / (1.25 * R)
                    edge = (yt - sag * 0.6) + 2 * sag * (1 - u * u) * 1.0
                    if yy > edge + 0.025 * D:
                        j = ((int(xx * 7 + yy * 13) % 7) - 3) * 0.0022 * D
                        dots.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(xx + j), f(yy - j * .5), f(max(0.0068 * D, 1.2))))
                    xx += step
                yy += step * 0.8
                row += 1
            sk.append('<g fill="%s" clip-path="url(#%s-hc)">%s</g>' % (H['chin_dots'], uid, ''.join(dots)))
    if H.get('hair') == 'bun':
        hc = H['hair_color']
        fr = -bs                                   # screen-x direction of the face side
        p0 = (cx + bs * 1.3 * R, cy - 0.02 * D)
        p1 = (cx + bs * 0.12 * D, cy - 0.15 * D)
        p2 = (cx + fr * 0.08 * D, cy - 0.255 * D)
        p3 = (cx + fr * 0.30 * D, cy - 0.21 * D)
        p4 = (cx + fr * 1.3 * R, cy - 0.10 * D)
        cap = 'M%s Q%s %s Q%s %s L%s L%s Z' % (pts([p0]), pts([p1]), pts([p2]), pts([p3]), pts([p4]),
                                                 pts([(p4[0], cy - R - 10)]), pts([(p0[0], cy - R - 10)]))
        sk.append('<path d="%s" fill="%s" clip-path="url(#%s-hc)"/>' % (cap, hc, uid))
        sk.append('<path d="M%s Q%s %s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" clip-path="url(#%s-hc)"/>' % (
            pts([p0]), pts([p1]), pts([p2]), pts([p3]), pts([p4]), INK, f(0.016 * D), uid))
        # a few comb strokes
        for k in (0.3, 0.55):
            q0 = (cx + bs * 0.05 * D - fr * 0.0, cy - R * 0.98)
            sk.append('<path d="M%s Q%s %s" fill="none" stroke="#5A2E33" stroke-width="%s" stroke-linecap="round" clip-path="url(#%s-hc)"/>' % (
                pts([(cx + fr * (k - 0.1) * D, cy - 0.30 * D - k * 0.05 * D)]), pts([(cx + bs * 0.05 * D, cy - 0.42 * D)]),
                pts([(cx + bs * (0.10 + k * 0.2) * D, cy - 0.47 * D)]), f(0.012 * D), uid))
    o.append('<g id="%s-skin">%s</g>' % (uid, ''.join(sk)))
    o.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(cx), f(cy), f(R), INK, f(OL)))

    # ---------- bun disc on the outline, pencil behind it, one loose strand
    if bun:
        bx, by, br = bun
        hc = H['hair_color']
        pa = (bx - bs * br * 1.55, by + br * 0.40)
        pb = (bx + bs * br * 1.45, by - br * 0.85)
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(pa[0]), f(pa[1]), f(pb[0]), f(pb[1]), INK, f(0.05 * D)))
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#E0A23A" stroke-width="%s" stroke-linecap="butt"/>' % (
            f(pa[0] + bs * 0.02 * D), f(pa[1] - 0.008 * D), f(pb[0]), f(pb[1]), f(0.026 * D)))
        o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (f(bx), f(by), f(br), hc, INK, f(OL)))
        o.append('<path d="M%s Q%s %s" fill="none" stroke="#5A2E33" stroke-width="%s" stroke-linecap="round"/>' % (
            pts([(bx - br * .55, by + br * .05)]), pts([(bx, by - br * .75)]), pts([(bx + br * .55, by + br * .1)]), f(0.014 * D)))
        base = (bx - bs * br * 0.15, by - br * 0.9)
        cl = [(base[0] + bs * u * D * 0.7, base[1] + v * D * 0.7) for u, v in COWLICK['stiff']]
        o.append('<path d="%s" fill="%s"/>' % (taper(bezier(*cl), 0.03 * D, 1.0), INK))
        info['top'] = min(info['top'], min(p[1] for p in cl))

    # ---------- forehead creases (gramps)
    if H.get('creases'):
        for k in range(3):
            yy = cy - 0.36 * D + k * 0.06 * D
            o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.8"/>' % (
                pts([(xc - 0.20 * D + k * 0.02 * D, yy + 0.02 * D)]), pts([(xc, yy - 0.025 * D)]),
                pts([(xc + 0.20 * D - k * 0.02 * D, yy + 0.02 * D)]), INK, f(0.02 * D)))

    # ---------- sideburn ticks above each ear
    if H.get('sideburns'):
        for side in (-1, 1):
            yy = cy - 0.15 * D
            xr = cx + side * math.sqrt(R * R - (yy - cy) ** 2)
            c0 = (xr - side * 0.008 * D, yy)
            c1 = (xr - side * 0.035 * D, yy + 0.05 * D)
            c2 = (xr - side * 0.04 * D, yy + 0.10 * D)
            o.append('<path d="%s" fill="%s"/>' % (taper(qbez(c0, c1, c2, 8), 0.034 * D, 0.006 * D), INK))

    # ---------- cowlick: one thick tapered brush flick rooted at 11 o'clock, curling backward
    cw = E.get('cowlick') if H.get('cowlick') else None
    if cw:
        ra = math.radians(30)
        root = (cx + bs * R * math.sin(ra) * 0.95, cy - R * math.cos(ra) * 0.95)
        th = math.radians(12)
        cs = E.get('cowlick_scale', 1.0)

        def place(shape, dx=0.0):
            out = []
            for u, v in shape:
                u2 = u * math.cos(th) - v * math.sin(th)
                v2 = u * math.sin(th) + v * math.cos(th)
                out.append((root[0] + bs * u2 * D * cs + dx, root[1] + v2 * D * cs))
            return out
        cl = place(COWLICK[cw])
        if E.get('tremble'):
            for dx in (-0.035 * D, 0.035 * D):
                c2 = place(COWLICK[cw], dx)
                c2[0] = cl[0]
                o.append('<path d="%s" fill="%s" opacity="0.3"/>' % (taper(bezier(*c2), 0.065 * D, 0.01 * D), INK))
        curve = bezier(*cl)
        o.append('<path d="%s" fill="%s"/>' % (taper(curve, 0.065 * D, 0.01 * D), INK))
        info['top'] = min(info['top'], min(p[1] for p in curve) - 0.01 * D)

    # ---------- eyes: flat-topped bowls, lids are skin masks from above
    es = E.get('eye_scale', 1.0)
    ewn = H['eye_w'] * D * es
    ewf = ewn * (1 - 0.18 * at)
    ed = H['eye_d'] * D * es
    gap = H['eye_gap'] * D * E.get('gap_scale', 1.0) * (1 - 0.1 * at)
    if t > 0.05:
        wl, wr = ewn, ewf
    elif t < -0.05:
        wl, wr = ewf, ewn
    else:
        wl = wr = ewn
    ey = cy - R + H['eye_top'] * D + E.get('eye_dy', 0.0) * D
    centers = [(xc - gap / 2 - wl / 2, wl), (xc + gap / 2 + wr / 2, wr)]
    info['eyes'] = centers
    pr = H['pupil'] * D * E.get('pupil_scale', 1.0) / 2
    lid = E.get('lid', (0.55, 0.55))
    low = E.get('low', (0.0, 0.0))
    low_curve = E.get('low_curve', 0.0) * D
    tan_t = math.tan(math.radians(E.get('lid_tilt', 0.0)))
    rim = max(H['rim'] * D, 2.5)
    lid_w = max(H['lid_w'] * D, 4)
    eye_set = E.get('eyes', (0, 1))
    for i, (ex, ew) in enumerate(centers):
        if i not in eye_set:
            continue
        eid = '%s-e%d' % (uid, i)
        bowl = 'M%s,%s L%s,%s A%s,%s 0 0 1 %s,%s Z' % (
            f(ex - ew / 2), f(ey), f(ex + ew / 2), f(ey), f(ew / 2), f(ed), f(ex - ew / 2), f(ey))
        sign = 1 if i == 0 else -1
        c_up = lid[i]
        y0 = ey + c_up * ed

        def lidy(x, y0=y0, sign=sign, ex=ex):
            return y0 + sign * tan_t * (x - ex)
        c_lo = low[i]
        yb = ey + ed - c_lo * ed

        def lowy(x, yb=yb, ex=ex, ew=ew, c_lo=c_lo):
            if c_lo <= 0:
                return 1e9
            k = 1 - ((x - ex) / (ew / 2)) ** 2
            return yb - low_curve * max(k, 0)
        o.append('<defs><clipPath id="%s-c"><path d="%s"/></clipPath></defs>' % (eid, bowl))
        o.append('<g transform="rotate(%s %s %s)">' % (f(sign * -E.get('bowl_tilt', 0.0)), f(ex), f(ey + ed / 2)))
        o.append('<g clip-path="url(#%s-c)">' % eid)
        o.append('<path d="%s" fill="%s"/>' % (bowl, WHITE))

        def place(u, v, r, ex=ex, ew=ew, lidy=lidy, lowy=lowy, c_up=c_up):
            x = ex + u * (ew / 2 - r)
            y = ey + ed / 2
            for _ in range(6):
                yt = max(ey, lidy(x) if c_up > 0 else ey)
                kk = max(0.0, 1 - ((x - ex) / (ew / 2)) ** 2)
                ybb = min(ey + ed * math.sqrt(kk), lowy(x))
                if ybb - yt >= 2 * r + 4:
                    y = yt + r + 2 + v * (ybb - yt - 2 * r - 4)
                else:
                    y = (yt + ybb) / 2
                yy = min(y + r * 0.8, ey + ed - 0.5)
                hw = (ew / 2) * math.sqrt(max(0.0, 1 - ((yy - ey) / ed) ** 2)) - r - 3
                x = ex + u * max(hw, 0)
            return x, y
        for (gi, gu, gv, gop) in E.get('ghosts', ()):
            if gi == i:
                gx, gy = place(gu, gv, pr)
                o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="%s"/>' % (f(gx), f(gy), f(pr), INK, gop))
        pp = E.get('pupils', ((0, 1), (0, 1)))[i]
        px, py = place(pp[0], pp[1], pr)
        if len(pp) > 2:
            py += pp[2] * D
        o.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(px), f(py), f(pr), INK))
        if c_up > 0:
            xa, xb = ex - ew, ex + ew
            poly = [(xa, ey - D), (xb, ey - D), (xb, lidy(xb)), (xa, lidy(xa))]
            o.append('<defs><clipPath id="%s-u"><polygon points="%s"/></clipPath></defs>' % (eid, pts(poly)))
            o.append('<g clip-path="url(#%s-u)"><use href="#%s-skin"/></g>' % (eid, uid))
            if c_up < 0.999:
                o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                    f(xa), f(lidy(xa)), f(xb), f(lidy(xb)), INK, f(lid_w)))
        if c_lo > 0:
            xa, xb = ex - ew / 2 - 4, ex + ew / 2 + 4
            lp = 'M%s,%s L%s,%s Q%s,%s %s,%s L%s,%s Z' % (
                f(xa), f(ey + ed + 40), f(xa), f(yb), f(ex), f(yb - 2 * low_curve), f(xb), f(yb), f(xb), f(ey + ed + 40))
            o.append('<defs><clipPath id="%s-l"><path d="%s"/></clipPath></defs>' % (eid, lp))
            o.append('<g clip-path="url(#%s-l)"><use href="#%s-skin"/></g>' % (eid, uid))
            o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(xa), f(yb), f(ex), f(yb - 2 * low_curve), f(xb), f(yb), INK, f(lid_w * 0.6)))
        o.append('</g>')
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (bowl, INK, f(rim)))
        o.append('</g>')
        if H.get('bags'):
            o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.85"/>' % (
                pts([(ex - ew * 0.30, ey + ed + 0.035 * D)]), pts([(ex, ey + ed + 0.075 * D)]),
                pts([(ex + ew * 0.30, ey + ed + 0.035 * D)]), INK, f(max(0.014 * D, 2.5))))

    # ---------- nose: small ink J-hook under the inner bowl corners (non-emotive)
    if H.get('nose'):
        nl = H['nose'] * D
        nx = xc + 0.035 * t * D
        ny = cy - R + 0.62 * D + E.get('eye_dy', 0.0) * D * 0.3
        o.append('<path d="M%s,%s L%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>' % (
            f(nx), f(ny - nl * 0.55), f(nx), f(ny + nl * 0.15), f(nx), f(ny + nl * 0.5), f(nx + bs * nl * 0.5), f(ny + nl * 0.42),
            INK, f(max(0.017 * D, 2.5))))

    # ---------- mouth library a-f (scaled to D)
    m = E.get('mouth')
    if m:
        lw = max(0.022 * D, 3)
        mdx = E['mouth_dx'] if 'mouth_dx' in E else H.get('mouth_back', 0.06) * bs
        mx = xc + mdx * D
        my = cy - R + 0.76 * D + E.get('mouth_dy', 0.0) * D
        mt = E.get('mouth_turn', 0.0) * D
        if m == 'a':
            mw = E.get('mouth_w', 0.16) * D
            o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(mx - mw / 2), f(my + mt), f(mx), f(my - mt), f(mx + mw / 2), f(my + mt), INK, f(lw)))
        elif m == 'b':
            o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                f(mx), f(my), f(0.035 * D), MOUTH_DARK, INK, f(lw * 0.8)))
        elif m == 'c':
            mw, mh = E.get('mouth_w', 0.42) * D, 0.16 * D
            mid = '%s-m' % uid
            x0, y0 = mx - mw / 2, my - mh / 2
            rr = 0.045 * D
            o.append('<defs><clipPath id="%s"><rect x="%s" y="%s" width="%s" height="%s" rx="%s"/></clipPath></defs>' % (
                mid, f(x0), f(y0), f(mw), f(mh), f(rr)))
            o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>' % (f(x0), f(y0), f(mw), f(mh), f(rr), MOUTH_DARK))
            o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" clip-path="url(#%s)"/>' % (
                f(x0), f(y0), f(mw), f(0.045 * D), WHITE, mid))
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>' % (
                f(x0), f(y0 + 0.045 * D), f(x0 + mw), f(y0 + 0.045 * D), INK, f(lw * 0.6), mid))
            o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
                f(x0), f(y0), f(mw), f(mh), f(rr), INK, f(lw)))
        elif m == 'd':
            mw = E.get('mouth_w', 0.30) * D
            amp = 0.024 * D
            p = [(mx - mw / 2 + mw * k / 48, my + amp * math.sin(k / 48 * 3 * 2 * math.pi)) for k in range(49)]
            o.append('<path d="M%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>' % (
                ' L'.join('%s,%s' % (f(x), f(y)) for x, y in p), INK, f(lw)))
        elif m == 'e':
            mw = E.get('mouth_w', 0.22) * D
            fl = -1 if E.get('mouth_flip') else 1
            x0, x1 = mx - fl * mw / 2, mx + fl * mw / 2
            o.append('<path d="M%s,%s L%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(x0), f(my + 0.018 * D), f(x1 - fl * 0.06 * D), f(my - 0.004 * D), f(x1 + fl * 0.02 * D), f(my - 0.012 * D),
                f(x1 + fl * 0.03 * D), f(my - 0.085 * D), INK, f(lw * 1.1)))
            o.append('<path d="M%s,%s q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(x1 + fl * 0.065 * D), f(my - 0.11 * D), f(fl * 0.016 * D), f(0.018 * D), f(fl * 0.01 * D), f(0.05 * D), INK, f(lw * 0.8)))
        elif m == 'f':
            mw, mh = E.get('mouth_w', 0.32) * D, 0.11 * D
            mid = '%s-m' % uid
            x0, y0 = mx - mw / 2, my - mh / 2
            o.append('<defs><clipPath id="%s"><rect x="%s" y="%s" width="%s" height="%s" rx="%s"/></clipPath></defs>' % (
                mid, f(x0), f(y0), f(mw), f(mh), f(0.025 * D)))
            o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>' % (f(x0), f(y0), f(mw), f(mh), f(0.025 * D), WHITE))
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>' % (
                f(x0), f(my), f(x0 + mw), f(my), INK, f(lw * 0.7), mid))
            for k in range(1, 5):
                xx = x0 + mw * k / 5
                o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>' % (
                    f(xx), f(y0), f(xx), f(y0 + mh), INK, f(lw * 0.55), mid))
            o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
                f(x0), f(y0), f(mw), f(mh), f(0.025 * D), INK, f(lw)))

    # ---------- marks
    sw = E.get('sweat')
    if sw:
        side = sw
        a = math.radians(-35 if side > 0 else 215)
        sx, sy = cx + (R + 0.02 * D) * math.cos(a), cy + (R + 0.02 * D) * math.sin(a)
        sz = 0.12 * D
        o.append('<path d="M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            f(sx), f(sy - sz / 2), f(sx + sz * .38), f(sy - sz * .05), f(sx + sz * .38), f(sy + sz / 2), f(sx), f(sy + sz / 2),
            f(sx - sz * .38), f(sy + sz / 2), f(sx - sz * .38), f(sy - sz * .05), f(sx), f(sy - sz / 2), WHITE, INK, f(0.013 * D)))
    if E.get('emanata'):
        for side in E['emanata']:
            for k, a0 in enumerate((-30, 0, 30)):
                a = math.radians(a0)
                r0, r1 = R + 0.10 * D, R + 0.22 * D
                ccx = cx + side * 0.0
                x0 = ccx + side * r0 * math.cos(a)
                y0 = cy - 0.06 * D + r0 * math.sin(a)
                x1 = ccx + side * r1 * math.cos(a)
                y1 = cy - 0.06 * D + r1 * math.sin(a)
                o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                    f(x0), f(y0), f(x1), f(y1), mark_color, f(max(0.022 * D, 4))))
    if E.get('gloom'):
        for k in range(4):
            gx = xc - 0.21 * D + k * 0.14 * D
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.4"/>' % (
                f(gx), f(cy - R - 0.30 * D + (k % 2) * 0.03 * D), f(gx), f(cy - R - 0.10 * D + (k % 2) * 0.02 * D),
                MINT, f(max(0.022 * D, 4))))
    o.append('</g>')
    return '\n'.join(o), info


# =====================================================================
#  STICK-BODY RIG
#  Ink-cased coloured sticks (a flat core + INK casing), round caps/joins.
# =====================================================================
def _caps(points, radii):
    out = []
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        r0, r1 = radii[i], radii[i + 1]
        nx, ny = norm((-(y1 - y0), x1 - x0))
        out.append('<polygon points="%s"/>' % pts([(x0 + nx * r0, y0 + ny * r0), (x1 + nx * r1, y1 + ny * r1),
                                                   (x1 - nx * r1, y1 - ny * r1), (x0 - nx * r0, y0 - ny * r0)]))
    for (x, y), r in zip(points, radii):
        out.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(x), f(y), f(r)))
    return ''.join(out)


def sticks(items, rim=None, tag=None):
    """items: (points, core_colour, core_w0, core_w1, casing0, casing1).  rim = (colour, px, light_dir)."""
    cas, core, rims = [], [], []
    for (p, col, w0, w1, c0, c1) in items:
        cum = [0.0]
        for i in range(1, len(p)):
            cum.append(cum[-1] + math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]))
        T = cum[-1] or 1.0
        w = [w0 + (w1 - w0) * c / T for c in cum]
        cs = [c0 + (c1 - c0) * c / T for c in cum]
        cas.append(_caps(p, [a / 2 + b for a, b in zip(w, cs)]))
        core.append('<g fill="%s">%s</g>' % (col, _caps(p, [a / 2 for a in w])))
        if tag:
            REG['limbs'].append((tag, p, [a + 2 * b for a, b in zip(w, cs)], col))
        if rim:
            rc, rpx, L = rim
            off = []
            for i in range(len(p)):
                a = p[max(i - 1, 0)]
                b = p[min(i + 1, len(p) - 1)]
                n = norm((-(b[1] - a[1]), b[0] - a[0]))
                if n[0] * L[0] + n[1] * L[1] < 0:
                    n = (-n[0], -n[1])
                h = w[i] / 2 + cs[i] - rpx / 2 - 0.4
                off.append((p[i][0] + n[0] * h, p[i][1] + n[1] * h))
            rims.append('<path d="M%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>' % (
                ' L'.join('%s,%s' % (f(x), f(y)) for x, y in off), rc, f(rpx)))
    return '<g fill="%s">%s</g>%s%s' % (INK, ''.join(cas), ''.join(core), ''.join(rims))


def mitten(wrist, a, skin, L, Wd, sw, thumb_side=1, mode='rest', pole=None, cuff=None):
    """Mitten paddle (behind a gripped prop) + thumb nub (in front).  Returns (paddle, thumb)."""
    if mode == 'grip' and pole is not None:
        c1 = pole + math.pi / 2
        if math.cos(c1 - a) < 0:
            c1 += math.pi
        g = '<g transform="translate(%s %s) rotate(%s)">' % (f(wrist[0]), f(wrist[1]), f(math.degrees(c1)))
        x0 = -L * 0.40
        paddle = g + '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
            f(x0), f(-Wd / 2), f(L), f(Wd), f(Wd / 2), skin, INK, f(sw))
        if cuff:
            paddle += '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                f(x0 - L * 0.12), f(-Wd * 0.58), f(L * 0.26), f(Wd * 1.16), f(L * 0.06), cuff, INK, f(sw * 0.8))
        paddle += '</g>'
        ts = thumb_side
        thumb = g + ('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/></g>') % (
            f(-L * 0.02), f(ts * Wd * 0.18), f(L * 0.25), f(Wd * 0.33), skin, INK, f(sw * 0.85))
        return paddle, thumb
    g = '<g transform="translate(%s %s) rotate(%s)">' % (f(wrist[0]), f(wrist[1]), f(math.degrees(a)))
    paddle = g + '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        f(-L * 0.12), f(-Wd / 2), f(L), f(Wd), f(Wd / 2), skin, INK, f(sw))
    if cuff:
        paddle += '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
            f(-L * 0.22), f(-Wd * 0.58), f(L * 0.26), f(Wd * 1.16), f(L * 0.06), cuff, INK, f(sw * 0.8))
    paddle += '</g>'
    if mode == 'open':
        thumb = g + '<g transform="translate(%s %s) rotate(%s)"><rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/></g></g>' % (
            f(L * 0.22), f(thumb_side * Wd * 0.36), f(thumb_side * 55), f(-Wd * 0.12), f(-Wd * 0.26), f(L * 0.46), f(Wd * 0.52),
            f(Wd * 0.26), skin, INK, f(sw * 0.85))
    else:
        thumb = g + '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/></g>' % (
            f(L * 0.42), f(thumb_side * Wd * 0.30), f(L * 0.22), f(Wd * 0.28), skin, INK, f(sw * 0.85))
    return paddle, thumb


def shoe(ankle, dirx, color, Ltot, Htot, rot=0, sw=5, sole='#4A3328', toe_rim=None):
    """Slip-on with a flat sole at ankle.y + Htot (rot=0).  Ltot = total length."""
    L, Hh = Ltot / 1.12, Htot

    def P(x, y):
        return '%s,%s' % (f(x * L), f(y * Hh))
    d = ('M%s C%s %s %s L%s C%s %s %s C%s %s %s L%s C%s %s %s Z' % (
        P(-0.30, 0.22), P(-0.36, 0.62), P(-0.34, 1.0), P(-0.22, 1.0), P(0.62, 1.0),
        P(0.78, 1.0), P(0.80, 0.50), P(0.58, 0.40), P(0.42, 0.30), P(0.22, 0.12), P(0.10, -0.04),
        P(-0.14, -0.10), P(-0.24, -0.08), P(-0.30, 0.04), P(-0.30, 0.22)))
    w = 'M%s L%s L%s Q%s %s Z' % (P(-0.35, 0.72), P(-0.22, 1.0), P(0.62, 1.0), P(0.20, 0.86), P(-0.35, 0.72))
    out = ['<g transform="translate(%s %s) scale(%s 1) rotate(%s)">' % (f(ankle[0]), f(ankle[1]), dirx, f(rot)),
           '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (d, color, INK, f(sw)),
           '<path d="%s" fill="%s"/>' % (w, sole)]
    if toe_rim:
        out.append('<path d="M%s C%s %s %s" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % (
            P(0.40, 0.36), P(0.60, 0.44), P(0.76, 0.52), P(0.74, 0.80), toe_rim))
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/></g>' % (d, INK, f(sw)))
    return ''.join(out)


LOU_F = dict(name='Lou', skin='#D9A383', chin='#C08E70', arm='#5E7F73', spine='#5E7F73', leg='#2F3B38',
             shoe='#2A1D18', hand='#D9A383', cuff=None, collar='lou', hip='rag',
             neck_vis=0.12, yoke=0.07, spine_len=1.0, upper=0.68, fore=0.70, thigh=0.74, shin=0.71,
             shoe_h=0.10, shoe_L=0.30, mit_L=0.20, mit_W=0.13, sh=(0.28, 0.25), neck_w=0.18)
DOT_F = dict(name='Dot', skin='#7B4F3A', chin='#683F2E', arm=CREAM, spine=CREAM, leg='#3A1C1E',
             shoe='#141010', hand='#7B4F3A', cuff=CREAM, collar='dot', hip='keys',
             neck_vis=0.13, yoke=0.07, spine_len=0.95, upper=0.67, fore=0.69, thigh=0.70, shin=0.68,
             shoe_h=0.10, shoe_L=0.28, mit_L=0.20, mit_W=0.13, sh=(0.27, 0.24), neck_w=0.17)


def figure(F, P, rim=None):
    """Build one stick body under a round head.  Returns (layers, J)."""
    D = P['D']
    R = D / 2.0
    t = P.get('turn', 0.0)
    fs = (t > 0) - (t < 0)
    at = abs(t)
    hx, hy = P['head']
    alpha = math.radians(P.get('neck_ang', 10 * fs))      # lean of the neck top toward screen-right
    nvis = P.get('neck_vis', F['neck_vis'])
    nx0 = hx - fs * 0.10 * min(at, 1.0) * D + P.get('neck_dx', 0.0) * D
    yb = hy + math.sqrt(max(R * R - (nx0 - hx) ** 2, 0))
    dn = (-math.sin(alpha), math.cos(alpha))
    Q = (nx0, yb)
    T = add(Q, dn, -0.07 * D)                              # tucked 0.07 D (~20 px) inside the head
    B = add(Q, dn, nvis * D)                               # visible neck base
    sa = math.radians(P.get('spine', 0.0))
    bow = P.get('bow', 0.0) * D
    Ls = P.get('spine_len', F['spine_len']) * D
    yoke = P.get('yoke', F['yoke']) * D
    Y = (B[0], B[1] + yoke)
    ctrl = hip = None
    for _ in range(4):
        c = Ls
        for _ in range(8):
            c = Ls / (1 + 8.0 / 3.0 * (bow / c) ** 2)
        hip = (Y[0] + c * math.sin(sa), Y[1] + c * math.cos(sa))
        mid = ((Y[0] + hip[0]) / 2, (Y[1] + hip[1]) / 2)
        perp = (math.cos(sa), -math.sin(sa))
        ctrl = (mid[0] + perp[0] * 2 * bow, mid[1] + perp[1] * 2 * bow)
        u = norm((ctrl[0] - B[0], ctrl[1] - B[1]))
        Y = add(B, u, yoke)
    spine_curve = qbez(Y, ctrl, hip, 16)
    spine = [B] + spine_curve
    ub = norm((0.5 * u[0], 0.5 * u[1] + 0.5))
    ub = norm((ub[0] + P.get('yoke_tilt', 0.0), ub[1]))
    perp_s = (ub[1], -ub[0])
    near = 'L' if t > 0.05 else ('R' if t < -0.05 else P.get('near', 'L'))
    hn, hf = F['sh'] if at > 0.05 else (F['sh'][0], F['sh'][0])
    hwL = hn if near == 'L' else hf
    hwR = hn if near == 'R' else hf
    if 'sh' in P:
        hwL, hwR = P['sh']
    shrug = P.get('shrug', 0.0) * D
    SL = add(add(Y, perp_s, -hwL * D), ub, -shrug)
    SR = add(add(Y, perp_s, hwR * D), ub, -shrug)
    J = dict(T=T, Q=Q, B=B, Y=Y, hip=hip, spine=spine, SL=SL, SR=SR, perp=perp_s, ub=ub, near=near, D=D,
             head=(hx, hy), turn=t)
    Ly = {}
    # ---- widths (total incl. casing), never under 12 px for limbs
    cas0, cas1 = max(0.018 * D, 3.5), max(0.015 * D, 3.5)
    tot0, tot1 = max(0.071 * D, 12.5), max(0.050 * D, 12.0)
    sp0, sp1 = max(0.08 * D, 14.0), max(0.06 * D, 12.0)
    tag = F['name']
    # ---- spine: tapered cased wedge from the neck base to the hip
    Ly['spine'] = sticks([(spine, F['spine'], sp0 - 2 * cas0, sp1 - 2 * cas0, cas0, cas0)], rim=rim, tag=tag + ':spine')
    # ---- arms
    upper, fore = F['upper'] * D, F['fore'] * D
    for side, S in (('L', SL), ('R', SR)):
        a = P['arms'][side]
        if 'ang' in a:
            th = math.radians(a['ang'])
            dv = (math.sin(th), -math.cos(th))
            tgt = add(S, dv, upper + fore)
            el, wr, _ = ik(S, tgt, upper, fore, a.get('bend', 1), a.get('straight', True))
        elif 'hand' in a:
            el, wr, short = ik(S, a['hand'], upper, fore, a.get('bend', 1), a.get('straight', False))
            J[side + '_short'] = short
        else:
            el, wr = fk(S, a['a'], upper, a['b'], fore)
        isnear = side == near
        core = F['arm'] if isnear else shade(F['arm'], 0.12)
        Ly[side + '_arm'] = sticks([([S, el, wr], core, tot0 - 2 * cas0, tot1 - 2 * cas1, cas0, cas1)],
                                   rim=rim, tag=tag + ':arm' + side)
        fa = ang(el, wr) + math.radians(a.get('wrist', 0))
        hand = F['hand'] if isnear else shade(F['hand'], 0.06)
        mode = a.get('mode', 'grip' if 'pole' in a else 'rest')
        pad, th_ = mitten(wr, fa, hand, F['mit_L'] * D, F['mit_W'] * D, max(0.018 * D, 3.5),
                          thumb_side=a.get('thumb', 1), mode=mode, pole=a.get('pole'), cuff=F.get('cuff'))
        Ly[side + '_pad'] = pad
        Ly[side + '_thumb'] = th_
        J[side + '_el'], J[side + '_wr'] = el, wr
        J[side + '_tip'] = add(wr, (math.cos(fa), math.sin(fa)), F['mit_L'] * D * 0.88) if mode != 'grip' else wr
    # ---- legs
    thigh, shin = F['thigh'] * D, F['shin'] * D
    sh_h = F['shoe_h'] * D
    for side in ('L', 'R'):
        g = P['legs'][side]
        if 'sole' in g:
            an_t = (g['sole'][0], g['sole'][1] - sh_h)
            kn, an, short = ik(hip, an_t, thigh, shin, g.get('bend', fs if fs else (1 if side == 'R' else -1)),
                               g.get('straight', False))
            J[side + '_legshort'] = short
        else:
            kn, an = fk(hip, g['a'], thigh, g['b'], shin)
        isnear = side == near
        core = F['leg'] if isnear else shade(F['leg'], 0.12)
        toe = g.get('toe', fs if fs else (1 if side == 'R' else -1))
        Ly[side + '_leg'] = (sticks([([hip, kn, an], core, tot0 - 2 * cas0, tot1 - 2 * cas1, cas0, cas1)], rim=rim,
                                    tag=tag + ':leg' + side) +
                             shoe(an, toe, F['shoe'] if isnear else shade(F['shoe'], 0.12), F['shoe_L'] * D, sh_h,
                                  rot=g.get('rot', 0), sw=max(0.018 * D, 3.5), toe_rim=P.get('toe_rim')))
        J[side + '_kn'], J[side + '_an'] = kn, an
    # ---- neck stub: skin, 0.18 D wide, chin shadow on top, ink sides
    nw = F['neck_w'] * D
    nperp = (dn[1], -dn[0])
    Bx = add(B, dn, 0.06 * D)
    poly = [add(T, nperp, -nw / 2), add(T, nperp, nw / 2), add(Bx, nperp, nw / 2), add(Bx, nperp, -nw / 2)]
    Q2 = add(Q, dn, 0.035 * D)
    shadow = [add(T, nperp, -nw / 2), add(T, nperp, nw / 2), add(Q2, nperp, nw / 2), add(Q2, nperp, -nw / 2)]
    neck = ['<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
        pts(poly), F['skin'], INK, f(max(0.018 * D, 3.5))),
        '<polygon points="%s" fill="%s"/>' % (pts(shadow), F['chin'])]
    Ly['neck'] = ''.join(neck)
    J['dn'] = dn
    # ---- neck anchor (collar) -- outer corners ARE the shoulder points
    ex = perp_s
    ey_ = ub

    def Tf(x, y):
        return (B[0] + (ex[0] * x + ey_[0] * y) * D, B[1] + (ex[1] * x + ey_[1] * y) * D)
    olw = max(0.016 * D, 3.0)
    back, front = [], []
    if F['collar'] == 'lou':
        jk = F['spine']
        back.append('<path d="M%s Q%s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([Tf(-0.15, 0.04)]), pts([Tf(-0.12, -0.075)]), pts([Tf(0, -0.085)]), pts([Tf(0.12, -0.075)]),
            pts([Tf(0.15, 0.04)]), shade(jk, 0.18), INK, f(olw)))
        front.append('<polygon points="%s" fill="#3A2A22" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([Tf(-0.095, -0.02), Tf(0, 0.25), Tf(0.095, -0.02)]), INK, f(olw)))
        for sg, S, hw in ((-1, SL, hwL), (1, SR, hwR)):
            oc = add(S, ex, sg * 0.012 * D)
            fl = [Tf(sg * 0.088, -0.04), oc, Tf(sg * (hw - 0.07), P.get('yoke', F['yoke']) + 0.10), Tf(sg * 0.012, 0.29)]
            front.append('<polygon points="%s" fill="#6F9284" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                pts(fl), INK, f(olw)))
    elif F['collar'] == 'dot':
        back.append('<path d="M%s Q%s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([Tf(-0.14, 0.04)]), pts([Tf(-0.11, -0.07)]), pts([Tf(0, -0.08)]), pts([Tf(0.11, -0.07)]),
            pts([Tf(0.14, 0.04)]), shade(CREAM, 0.10), INK, f(olw)))
        front.append('<polygon points="%s" fill="#4A2530" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([Tf(-0.09, -0.02), Tf(0, 0.23), Tf(0.09, -0.02)]), INK, f(olw)))
        for sg, S, hw in ((-1, SL, hwL), (1, SR, hwR)):
            oc = add(S, ex, sg * 0.02 * D)
            p0, p2, p3 = Tf(sg * 0.085, -0.04), Tf(sg * (hw - 0.05), F['yoke'] + 0.11), Tf(sg * 0.01, 0.27)
            front.append('<path d="M%s L%s Q%s %s Q%s %s Z" fill="#F4ECDF" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                pts([p0]), pts([oc]), pts([add(oc, ey_, 0.10 * D)]), pts([p2]), pts([Tf(sg * 0.10, 0.20)]), pts([p3]), INK, f(olw)))
        # mint lanyard V to a blank badge on the spine
        bd = point_at(spine, 0.46 * D)
        J['badge'] = bd
        for colr, wd in ((INK, 0.04 * D), (MINT, 0.018 * D)):
            front.append('<path d="M%s L%s L%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>' % (
                pts([Tf(-0.075, -0.01)]), pts([(bd[0], bd[1] - 0.07 * D)]), pts([Tf(0.075, -0.01)]), colr, f(wd)))
    Ly['collar_back'] = ''.join(back)
    Ly['collar'] = ''.join(front)
    if F['collar'] == 'dot':
        bd = J['badge']
        Ly['badge'] = ('<g transform="rotate(%s %s %s)"><rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>'
                       '<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/></g>') % (
            f(P.get('badge_rot', -8)), f(bd[0]), f(bd[1]), f(bd[0] - 0.08 * D), f(bd[1] - 0.075 * D), f(0.16 * D), f(0.19 * D),
            f(0.02 * D), WHITE, INK, f(olw), f(bd[0] - 0.055 * D), f(bd[1] - 0.045 * D), f(0.11 * D), f(0.04 * D), MINT)
    # ---- hip prop
    bsx = -fs if fs else -1
    if F['hip'] == 'rag':
        Ly['hip'] = rag(hip, side=P.get('rag_side', bsx), swing=P.get('swing', 0.0) * D, s=D / 270.0)
    elif F['hip'] == 'keys':
        Ly['hip'] = keys(add(hip, (P.get('keys_side', 1) * 0.05 * D, -0.02 * D)), D, P.get('keys_swing', 18))
    REG['figs'].append(J)
    return Ly, J


def figure_fit(F, P, rim=None, tol=0.5):
    """figure() that lowers the head (whole body) until both planted feet reach their soles."""
    for _ in range(12):
        Ly, J = figure(F, P, rim=rim)
        short = max(J.get('L_legshort', 0), J.get('R_legshort', 0))
        if short <= tol:
            return Ly, J
        REG['figs'].pop()
        for k in ('L', 'R'):
            REG['limbs'][:] = [x for x in REG['limbs'] if not x[0].startswith(F['name'] + ':')]
        P['head'] = (P['head'][0], P['head'][1] + short * 0.9)
    return figure(F, P, rim=rim)


def rag(hip, side=1, swing=0.0, s=1.0):
    x0, y0 = hip
    sx = side * s
    p0 = (x0 + sx * 2, y0 - 10 * s)
    p1 = (x0 + sx * 36, y0 - 6 * s)
    p2 = (x0 + sx * 46 + swing, y0 + 78 * s)
    p3 = (x0 + sx * 10 + swing * 0.7, y0 + 72 * s)
    m = ((p2[0] + p3[0]) / 2 + sx * 2, (p2[1] + p3[1]) / 2 + 12 * s)
    d = 'M%s L%s Q%s %s Q%s %s Q%s %s Z' % (
        pts([p0]), pts([p1]), pts([((p1[0] + p2[0]) / 2 + sx * 6, (p1[1] + p2[1]) / 2)]), pts([p2]),
        pts([m]), pts([p3]), pts([((p0[0] + p3[0]) / 2 - sx * 4, (p0[1] + p3[1]) / 2)]), pts([p0]))
    folds = '<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.55"/>' % (
        pts([(x0 + sx * 18, y0 + 2 * s)]), pts([(x0 + sx * 20 + swing * .4, y0 + 34 * s)]),
        pts([(x0 + sx * 24 + swing * 0.8, y0 + 66 * s)]), INK, f(3 * s))
    return '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>%s' % (d, CREAM, INK, f(4.5 * s), d and folds)


def keys(p, D, swing=18):
    x, y = p
    r = 0.055 * D
    o = ['<g transform="rotate(%s %s %s)">' % (f(swing), f(x), f(y))]
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(x), f(y), f(x), f(y + 0.08 * D), INK, f(0.02 * D)))
    cy = y + 0.08 * D + r
    for k, a in enumerate((-30, 10)):
        kx = x + math.sin(math.radians(a)) * r * 1.6
        ky = cy + math.cos(math.radians(a)) * r * 1.6
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(x + math.sin(math.radians(a)) * r), f(cy + math.cos(math.radians(a)) * r), f(kx), f(ky), INK, f(0.035 * D)))
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(x + math.sin(math.radians(a)) * r), f(cy + math.cos(math.radians(a)) * r), f(kx), f(ky), '#D9B25E', f(0.016 * D)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s" transform="rotate(14 %s %s)"/>' % (
        f(x + 0.01 * D), f(cy + 0.02 * D), f(0.085 * D), f(0.20 * D), f(0.02 * D), MINT, INK, f(0.014 * D), f(x), f(cy)))
    o.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(x), f(cy), f(r), INK, f(0.04 * D)))
    o.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(x), f(cy), f(r), BRASS, f(0.02 * D)))
    o.append('</g>')
    return ''.join(o)


# =====================================================================
#  PROPS
# =====================================================================
def handle_seg(p, q, D):
    return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
            '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(p[0]), f(p[1]), f(q[0]), f(q[1]), INK, f(max(0.064 * D, 12)), f(p[0]), f(p[1]), f(q[0]), f(q[1]), WALNUT,
                f(max(0.034 * D, 5.5))))


def broom(base, tip, D, floor=None, skew=0.0, fan_len=0.45, fan_w=0.55):
    """Returns (fan, handle).  base = handle/bristle junction, tip = top of the handle."""
    s = D / 280.0
    a = ang(base, tip)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    FL, FW = fan_len * D, fan_w * D
    hw = 0.06 * D
    tl = (base[0] + nx * hw, base[1] + ny * hw)
    tr = (base[0] - nx * hw, base[1] - ny * hw)
    bc = (base[0] - ux * FL, base[1] - uy * FL)
    if floor is not None:
        bc = (bc[0] + skew, floor)
        bl, br = (bc[0] + FW / 2, floor), (bc[0] - FW / 2, floor)
        if tl[0] < tr[0]:
            bl, br = br, bl
    else:
        bl = (bc[0] + nx * FW / 2, bc[1] + ny * FW / 2)
        br = (bc[0] - nx * FW / 2, bc[1] - ny * FW / 2)

    def mix(p, q, t, push=0.0):
        return (p[0] + (q[0] - p[0]) * t + nx * push, p[1] + (q[1] - p[1]) * t + ny * push)
    c1 = mix(tl, bl, 0.45, 0.05 * D)
    c2 = mix(tr, br, 0.45, -0.05 * D)
    bottom = ('L%s' % pts([br])) if floor is not None else ('Q%s %s' % (pts([(bc[0] - ux * 0.05 * D, bc[1] - uy * 0.05 * D)]), pts([br])))
    fan = ['<path d="M%s Q%s %s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
        pts([tl]), pts([c1]), pts([bl]), bottom, pts([c2]), pts([tr]), BRISTLE, INK, f(max(0.02 * D, 3.5)))]
    for tt in (0.22, 0.45, 0.68):
        p = mix(tl, tr, tt)
        q = mix(bl, br, tt)
        q = (q[0] + (p[0] - q[0]) * 0.08, q[1] + (p[1] - q[1]) * 0.08)
        p = (p[0] - ux * 0.065 * D, p[1] - uy * 0.065 * D)
        fan.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#A9823A" stroke-width="%s" stroke-linecap="round"/>' % (
            f(p[0]), f(p[1]), f(q[0]), f(q[1]), f(max(0.014 * D, 2.5))))
    b0 = (base[0] - ux * 0.02 * D + nx * 0.07 * D, base[1] - uy * 0.02 * D + ny * 0.07 * D)
    b1 = (base[0] - ux * 0.02 * D - nx * 0.07 * D, base[1] - uy * 0.02 * D - ny * 0.07 * D)
    fan.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(b0[0]), f(b0[1]), f(b1[0]), f(b1[1]), INK, f(0.072 * D)))
    fan.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#8E2A35" stroke-width="%s" stroke-linecap="round"/>' % (
        f(b0[0]), f(b0[1]), f(b1[0]), f(b1[1]), f(0.036 * D)))
    return ''.join(fan), handle_seg(base, tip, D)


def broom_line(D, Htot, base_floor, angle_deg, fan_len=0.45):
    """bristle-floor centre + angle from vertical (deg, + = top leans right) -> (base, tip)."""
    a = math.radians(angle_deg)
    u = (math.sin(a), -math.cos(a))
    base = add(base_floor, u, fan_len * D * 0.92)
    tip = add(base_floor, u, 0.78 * Htot)
    return base, tip


def on_line(p, q, y):
    t = (y - p[1]) / ((q[1] - p[1]) or 1e-6)
    return (p[0] + (q[0] - p[0]) * t, y)


def along(p, q, d):
    u = norm((q[0] - p[0], q[1] - p[1]))
    return add(p, u, d)


def dustpan(grip, a_deg, D, ghost=False):
    """Tin dustpan, 0.55 D wide.  grip = point in the fist, a_deg = direction handle->lip (screen deg)."""
    a = math.radians(a_deg)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux

    def T(x, y):
        return (grip[0] + (ux * x + nx * y) * D, grip[1] + (uy * x + ny * y) * D)
    lw = max(0.018 * D, 3.5)
    o = []
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        *map(f, T(-0.07, 0)), *map(f, T(0.20, 0)), INK, f(0.075 * D)))
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        *map(f, T(-0.07, 0)), *map(f, T(0.20, 0)), '#7D867E', f(0.075 * D - 2 * lw)))
    face = [T(0.17, -0.20), T(0.17, 0.20), T(0.53, 0.275), T(0.53, -0.275)]
    o.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (pts(face), TIN, INK, f(lw)))
    o.append('<polygon points="%s" fill="#7D867E"/>' % pts([T(0.17, -0.20), T(0.17, 0.20), T(0.24, 0.205), T(0.24, -0.205)]))
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#C9D0C8" stroke-width="%s" stroke-linecap="round"/>' % (
        *map(f, T(0.49, -0.23)), *map(f, T(0.49, 0.23)), f(0.022 * D)))
    o.append('<polygon points="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (pts(face), INK, f(lw)))
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>' % (
        *map(f, T(0.24, -0.205)), *map(f, T(0.24, 0.205)), INK, f(lw * 0.7)))
    o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        *map(f, T(0.205, 0)), f(0.022 * D), BRASS, INK, f(lw * 0.6)))
    return ''.join(o)


def dustpan_center(grip, a_deg, D):
    a = math.radians(a_deg)
    return (grip[0] + math.cos(a) * 0.40 * D, grip[1] + math.sin(a) * 0.40 * D)


def rope(points, w=7):
    d = 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in points)
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>' % (
                d, INK, f(w + 6), d, ROPE, f(w)))


def rope_path(d, w=7):
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (d, INK, f(w + 6), d, ROPE, f(w)))


def star8(x, y, r=34, ri=8, fill=STAR):
    p = []
    for k in range(8):
        a = math.radians(k * 45 - 90)
        rr = r if k % 2 == 0 else ri
        p.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (pts(p), fill, INK)


def ting(x, y, r=40, glow=True, rays=(-78, -128, 178, 128, -30)):
    o = []
    if glow:
        o.append('<circle cx="%s" cy="%s" r="%s" fill="url(#tingglow)"/>' % (f(x), f(y), f(r * 2.0)))
    o.append(star8(x, y, r, r * 0.24))
    for a in rays:
        tt = math.radians(a)
        r0, r1 = r * 1.0, r * 1.5
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (
            f(x + r0 * math.cos(tt)), f(y + r0 * math.sin(tt)), f(x + r1 * math.cos(tt)), f(y + r1 * math.sin(tt)), WHITE))
    return ''.join(o)


def arcs(c, radii, a0, a1, w=5, op=0.9, color=WHITE, dash=None, arrow=False):
    o = []
    for r in radii:
        p0 = (c[0] + r * math.cos(math.radians(a0)), c[1] + r * math.sin(math.radians(a0)))
        p1 = (c[0] + r * math.cos(math.radians(a1)), c[1] + r * math.sin(math.radians(a1)))
        sweep = 1 if a1 > a0 else 0
        large = 1 if abs(a1 - a0) > 180 else 0
        o.append('<path d="M%s A%s,%s 0 %d %d %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="%s"%s/>' % (
            pts([p0]), f(r), f(r), large, sweep, pts([p1]), color, f(w), op,
            (' stroke-dasharray="%s"' % dash) if dash else ''))
        if arrow:
            ta = math.radians(a1)
            tdir = (-math.sin(ta), math.cos(ta)) if a1 > a0 else (math.sin(ta), -math.cos(ta))
            nrm = (math.cos(ta), math.sin(ta))
            hl = 16
            q1 = (p1[0] - tdir[0] * hl + nrm[0] * hl * 0.6, p1[1] - tdir[1] * hl + nrm[1] * hl * 0.6)
            q2 = (p1[0] - tdir[0] * hl - nrm[0] * hl * 0.6, p1[1] - tdir[1] * hl - nrm[1] * hl * 0.6)
            o.append('<path d="M%s L%s L%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" opacity="%s"/>' % (
                pts([q1]), pts([p1]), pts([q2]), color, f(w), op))
    return ''.join(o)


def puffs(x, y, s=1.0, side=1):
    o = []
    for (dx, dy, r, op) in ((0, 0, 17, .55), (side * 28, -12, 13, .45), (side * 50, -2, 10, .38), (-side * 20, -8, 11, .4)):
        o.append('<circle cx="%s" cy="%s" r="%s" fill="#D9C7A6" opacity="%s"/>' % (f(x + dx * s), f(y + dy * s), f(r * s), op))
    return ''.join(o)


def dummy_body(cx, top, w=140, h=300, uid='dm', ghost=False):
    o = []
    x0 = cx - w / 2
    if ghost:
        return ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="4" stroke-dasharray="10 9" opacity="0.6"/>' % (
            f(x0), f(top), f(w), f(h), f(w / 2), STAR))
    o.append('<defs><clipPath id="%s-c"><rect x="%s" y="%s" width="%s" height="%s" rx="%s"/></clipPath></defs>' % (
        uid, f(x0), f(top), f(w), f(h), f(w / 2)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>' % (f(x0), f(top), f(w), f(h), f(w / 2), PEG))
    o.append('<g clip-path="url(#%s-c)">' % uid)
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#7A4D31"/>' % (f(cx + w * 0.18), f(top), f(w * 0.4), f(h)))
    for (gx, bend) in ((-0.22, -10), (0.06, 8), (0.30, -6)):
        o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" opacity="0.5"/>' % (
            f(cx + gx * w), f(top + 0.16 * h), f(cx + gx * w + bend), f(top + 0.5 * h), f(cx + gx * w - bend * 0.3), f(top + 0.86 * h), INK))
    o.append('<rect x="%s" y="%s" width="%s" height="18" fill="#6E4630" stroke="%s" stroke-width="4"/>' % (f(x0 - 4), f(top + 0.72 * h), f(w + 8), INK))
    o.append('</g>')
    o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="6"/>' % (f(x0), f(top), f(w), f(h), f(w / 2), INK))
    return ''.join(o)


def peg(p, q, ghost=False):
    if ghost:
        return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="16" stroke-linecap="round" opacity="0.32"/>'
                '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="4" stroke-linecap="round" stroke-dasharray="9 8" opacity="0.65"/>' % (
                    f(p[0]), f(p[1]), f(q[0]), f(q[1]), STAR, f(p[0]), f(p[1]), f(q[0]), f(q[1]), STAR))
    return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="20" stroke-linecap="round"/>'
            '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="11" stroke-linecap="round"/>' % (
                f(p[0]), f(p[1]), f(q[0]), f(q[1]), INK, f(p[0]), f(p[1]), f(q[0]), f(q[1]), PEG))


def bolt(x, y, r=11):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="4"/>' % (f(x), f(y), f(r), BRASS, INK)


def brass_ring(x, y, r=26):
    return ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="15"/>'
            '<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="8"/>' % (f(x), f(y), f(r), INK, f(x), f(y), f(r), BRASS))


def pulley(x, y, r=14):
    return ('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="5"/>'
            '<circle cx="%s" cy="%s" r="4" fill="%s"/>' % (f(x), f(y), f(r), BRASS, INK, f(x), f(y), INK))


def cast_shadow(cx, y, rx, ry=None, op=0.5):
    return '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#0E0907" opacity="%s"/>' % (f(cx), f(y), f(rx), f(ry or rx * 0.12), op)


def defs_common():
    return ('<defs>'
            '<radialGradient id="pool"><stop offset="0" stop-color="%s" stop-opacity="0.52"/>'
            '<stop offset="0.6" stop-color="%s" stop-opacity="0.30"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="lamp"><stop offset="0" stop-color="%s" stop-opacity="0.50"/>'
            '<stop offset="0.5" stop-color="%s" stop-opacity="0.26"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="vig" cx="50%%" cy="46%%" r="75%%"><stop offset="0.66" stop-color="#0E0907" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#0E0907" stop-opacity="0.66"/></radialGradient>'
            '<radialGradient id="pool2"><stop offset="0" stop-color="%s" stop-opacity="0.58"/>'
            '<stop offset="0.55" stop-color="%s" stop-opacity="0.38"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="tingglow"><stop offset="0" stop-color="#FFE7A8" stop-opacity="0.8"/>'
            '<stop offset="0.45" stop-color="#F2C46D" stop-opacity="0.38"/><stop offset="1" stop-color="#F2C46D" stop-opacity="0"/></radialGradient>'
            '</defs>' % ((AMBER,) * 9))


def assemble(L, order):
    return ''.join(L.get(k, '') for k in order)


# =====================================================================
#  SCENE 1080x1920  --  'didn't even look'
# =====================================================================
def build_scene(bg_only=False):
    REG['limbs'].clear()
    REG['figs'].clear()
    CEIL, FLOOR, FL = 230, 1318, 1545
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">', defs_common()]
    S.append('<rect width="1080" height="1920" fill="%s"/>' % COFFEE)
    # ---- burgundy lacquer board wall
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#6E1F2B"/>' % (CEIL, FLOOR - CEIL))
    for k, x in enumerate(range(0, 1080, 96)):
        if k % 2:
            S.append('<rect x="%d" y="%d" width="96" height="%d" fill="#641B27"/>' % (x, CEIL, FLOOR - CEIL))
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#4C1420" stroke-width="3"/>' % (x, CEIL, x, FLOOR))
    S.append('<rect x="0" y="1150" width="1080" height="14" fill="#4C1420"/>')
    S.append('<rect x="0" y="%d" width="1080" height="34" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (FLOOR - 34, INK))
    # ---- moonlit window (upper middle)
    wx, wy, ww, wh = 404, 262, 116, 136
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#7FAF9A"/>' % (wx, wy, ww, wh))
    for k in (1, 2):
        S.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#3A2620" stroke-width="6"/>' % (f(wx + ww * k / 3), wy, f(wx + ww * k / 3), wy + wh))
        S.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="#3A2620" stroke-width="6"/>' % (wx, f(wy + wh * k / 3), wx + ww, f(wy + wh * k / 3)))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#3A2620" stroke-width="14"/>' % (wx, wy, ww, wh))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="4"/>' % (wx - 7, wy - 7, ww + 14, wh + 14, INK))
    # ---- floor
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#4A2E24"/>' % (FLOOR, 1920 - FLOOR))
    for y in (1352, 1394, 1446, 1508, 1575, 1690, 1830):
        S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#3A231C" stroke-width="3"/>' % (y, y))
    S.append('<rect x="0" y="1575" width="1080" height="345" fill="#3A241C"/>')
    for y in (1690, 1830):
        S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#2E1C16" stroke-width="3"/>' % (y, y))
    S.append('<polygon points="%s" fill="%s" opacity="0.40"/>' % (pts([(250, FLOOR + 4), (520, FLOOR + 4), (640, 1575), (190, 1575)]), MINT))
    # ---- light pools
    S.append('<circle cx="905" cy="690" r="420" fill="url(#lamp)"/>')
    S.append('<ellipse cx="300" cy="800" rx="470" ry="660" fill="url(#pool2)"/>')
    S.append('<ellipse cx="800" cy="1340" rx="250" ry="330" fill="url(#pool2)"/>')
    S.append('<ellipse cx="380" cy="1290" rx="230" ry="200" fill="url(#pool)"/>')
    # ---- witness: caretaker peeking past the sliding door (one heavy lid, grey tuft, ear)
    S.append('<rect x="-10" y="660" width="128" height="%d" fill="#3A2620" stroke="%s" stroke-width="6"/>' % (FLOOR - 34 - 660, INK))
    S.append('<rect x="28" y="680" width="82" height="%d" fill="#100A08"/>' % (FLOOR - 34 - 700))
    gh, gi = head('gramps', 52, 1010, 190, GRAMPS_H,
                  dict(lid=(0.85, 0.85), pupils=((1, .5), (1, .5)), mouth='a', mouth_dx=0.10, mouth_w=0.12,
                       hide_ear=-1, eyes=(1,)), turn=0.55)
    S.append(gh)
    S.append('<rect x="-10" y="660" width="40" height="%d" fill="#4A3026" stroke="%s" stroke-width="6"/>' % (FLOOR - 34 - 660, INK))
    for yy in range(720, FLOOR - 40, 120):
        S.append('<line x1="-10" y1="%d" x2="28" y2="%d" stroke="%s" stroke-width="4"/>' % (yy, yy, INK))

    # ---- mook 1: wall-post dummy (faceless) above-left; its left peg arm just struck the dustpan
    S.append('<rect x="-6" y="%d" width="44" height="%d" fill="#5A3A28" stroke="%s" stroke-width="6"/>' % (CEIL - 6, 640 - CEIL, INK))
    d1x, d1top = 22, 240
    S.append(dummy_body(d1x, d1top, uid='d1'))
    pv = (d1x + 76, d1top + 64)                           # pivot on its right side
    L_arm = 124
    a_rest = 0.0                                           # rest: pointing right, tip in a brass wall ring
    ring = (pv[0] + L_arm * math.cos(math.radians(a_rest)) + 4, pv[1] + L_arm * math.sin(math.radians(a_rest)))
    S.append('<rect x="%s" y="%s" width="16" height="44" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (f(ring[0] + 20), f(ring[1] - 22), INK))

    # ---- mook 2: released from its ceiling latch right of the window, dropping (the next note)
    latch = (622, 238)
    d2x, d2top = 622, 246 + 62
    S.append(dummy_body(d2x, 246, uid='d2g', ghost=True))
    S.append('<g transform="rotate(-6 %s %s)">' % (f(d2x), f(d2top + 150)))
    S.append(peg((d2x - 60, d2top + 120), (d2x - 108, d2top + 70)))
    S.append(peg((d2x + 60, d2top + 120), (d2x + 104, d2top + 64)))
    S.append(dummy_body(d2x, d2top, uid='d2'))
    S.append('</g>')
    for (x0, y0, y1) in ((560, 250, 318), (684, 252, 324), (622, 248, 296)):
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="5" stroke-linecap="round" opacity="0.85"/>' % (x0, y0, x0, y1, WHITE))

    # ---- paper lantern (upper right)
    lx, ly = 962, 330
    S.append('<ellipse cx="%d" cy="%d" rx="56" ry="66" fill="%s" stroke="%s" stroke-width="6"/>' % (lx, ly, AMBER, INK))
    for k in (-32, 0, 32):
        S.append('<path d="M%d,%d Q%d,%d %d,%d" fill="none" stroke="#C9963E" stroke-width="3"/>' % (lx - 54, ly + k, lx, ly + k + 10, lx + 54, ly + k))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly - 72, INK))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly + 60, INK))

    # ---- shoe cabinet at the far right with five paper cups (the fifth steaming)
    ctop = 1040
    S.append('<rect x="900" y="%d" width="190" height="%d" fill="#4A2E24" stroke="%s" stroke-width="6"/>' % (ctop, FLOOR - ctop, INK))
    S.append('<rect x="892" y="%d" width="200" height="22" fill="#6B4630" stroke="%s" stroke-width="5"/>' % (ctop - 16, INK))
    for k in range(2):
        S.append('<rect x="%d" y="%d" width="74" height="150" fill="#3E261E" stroke="%s" stroke-width="4"/>' % (918 + k * 86, ctop + 30, INK))
        S.append('<rect x="%d" y="%d" width="28" height="8" rx="4" fill="%s" stroke="%s" stroke-width="3"/>' % (941 + k * 86, ctop + 48, BRASS, INK))
    for k in range(5):
        cxp = 920 + k * 35
        y1 = ctop - 16
        cup = 'M%d,%d L%d,%d L%d,%d L%d,%d Z' % (cxp - 14, y1 - 42, cxp + 14, y1 - 42, cxp + 10, y1, cxp - 10, y1)
        S.append('<path d="%s" fill="%s" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (cup, WHITE if k == 4 else CREAM, INK))
        S.append('<rect x="%d" y="%d" width="24" height="10" fill="#8E2A35"/>' % (cxp - 12, y1 - 30))
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (cxp - 16, y1 - 42, cxp + 16, y1 - 42, INK))
    sx_ = 920 + 4 * 35
    S.append('<path d="M%d,%d q-10,-12 0,-24 q10,-12 0,-24 q-10,-12 0,-24" fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" opacity="0.8"/>' % (sx_, ctop - 66, WHITE))

    # ================================================================ DOT (night guard)
    Dd = 250
    dturn = -1.0
    dhead = (874, 790)
    pB = (812, 250)
    dpose = dict(D=Dd, head=dhead, turn=dturn, neck_ang=6, neck_dx=-0.02, spine=-15, bow=0.05, sh=(0.30, 0.22),
                 arms=dict(L=dict(ang=-34, straight=True, pole=None, mode='grip', thumb=1),
                           R=dict(ang=-139, straight=True, mode='grip', thumb=-1)),
                 legs=dict(L=dict(sole=(744, 1540), rot=-26, bend=-1), R=dict(sole=(850, 1540), bend=-1, rot=-6)),
                 toe_rim=AMBER, keys_side=1, keys_swing=24)
    # rope geometry first (the fists are on it)
    DL, DJ = figure_fit(DOT_F, dpose, rim=(AMBER, 3.5, (0.8, -0.6)))
    up_f, lo_f = DJ['L_wr'], DJ['R_wr']
    pole_up = ang(pB, up_f)
    pole_lo = ang(up_f, lo_f)
    dpose['arms']['L']['pole'] = pole_up
    dpose['arms']['R']['pole'] = pole_lo
    REG['figs'].pop()
    DL, DJ = figure(DOT_F, dpose, rim=(AMBER, 3.5, (0.8, -0.6)))
    tail_end = (lo_f[0] - 56, lo_f[1] + 190)
    S.append(cast_shadow(800, 1546, 130, 15, 0.45))
    S.append(rope([latch, (latch[0] + 30, 246), pB]))
    if not bg_only:
        S.append(DL['L_leg'])
        S.append(DL['L_arm'] + DL['L_pad'])
        S.append(rope([pB, up_f, lo_f]))
        S.append(rope_path('M%s Q%s %s' % (pts([lo_f]), pts([(lo_f[0] + 10, lo_f[1] + 120)]), pts([tail_end]))))
        S.append('<path d="M%s l-14,44 l30,0 Z" fill="#8E2A35" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (pts([(tail_end[0] + 2, tail_end[1] - 4)]), INK))
        S.append(DL['spine'] + DL['hip'] + DL['R_leg'])
        S.append(DL['collar_back'] + DL['neck'] + DL['collar'] + DL['badge'])
        dh, dinfo = head('dot', dhead[0], dhead[1] + (DJ['head'][1] - dhead[1]), Dd, DOT_H,
                         dict(EXPR['panic'], sweat=-1, emanata=(1,), lid=(0.0, 0.0), mouth_w=0.30), turn=dturn)
        S.append(dh)
        S.append(DL['R_arm'] + DL['R_pad'])
        S.append(rope([along(up_f, lo_f, -6), along(up_f, lo_f, 70)]))
        S.append(rope([along(lo_f, up_f, 40), along(lo_f, tail_end, 30)]))
        S.append(DL['L_thumb'] + DL['R_thumb'])
    else:
        S.append(rope([pB, up_f, lo_f]))

    # ================================================================ LOU (night sweeper)
    D = 280
    turn = 1.0
    hd = (420, 650)
    Htot = 3.7 * D
    bfloor = (536, FL)
    base, tip = broom_line(D, Htot, bfloor, -17)
    pan_ang = -62                                       # handle->lip direction: up-right, face toward the dummy arm
    lpose = dict(D=D, head=hd, turn=turn, neck_ang=10, spine=-5, bow=-0.085, spine_len=0.97,
                 arms=dict(L=dict(ang=-30, straight=True, mode='grip', thumb=1, pole=math.radians(pan_ang)),
                           R=dict(hand=on_line(base, tip, 1150), bend=-1, thumb=1, pole=ang(base, tip))),
                 legs=dict(L=dict(sole=(296, FL), bend=1), R=dict(sole=(446, FL), bend=1)),
                 toe_rim=AMBER, swing=0.05)
    L, J = figure_fit(LOU_F, lpose, rim=(AMBER, 3.5, (0.7, -0.7)))
    hd = lpose['head']
    grip = J['L_wr']
    pan_c = dustpan_center(grip, pan_ang, D)
    if not bg_only:
        S.append(cast_shadow(395, FL + 4, 175, 16, 0.42))
        S.append(L['R_leg'] + L['R_arm'] + L['R_pad'])
        S.append(L['spine'] + L['hip'])
        fan, handle = broom(base, tip, D, floor=FL, skew=-8)
        S.append(fan + handle)
        S.append(L['L_leg'])
        S.append(L['L_arm'])
        S.append(L['collar_back'] + L['neck'] + L['collar'])
        lh, linfo = head('lou', hd[0], hd[1], D, LOU_H, EXPR['sideeye'], turn=turn)
        S.append(lh)
        S.append(L['L_pad'])
        S.append(dustpan(grip, pan_ang, D))
        S.append(L['L_thumb'] + L['R_thumb'])
        S.append(puffs(bfloor[0] + 96, FL - 40, 0.9, 1))
    # ---- the strike: dummy arm swung down from its ring onto the dustpan and is already bouncing back
    contact = (pan_c[0] - 0.02 * D, pan_c[1] - 0.05 * D)
    a_hit = math.degrees(ang(pv, contact))
    for ga in (a_rest + 0.33 * (a_hit - a_rest), a_rest + 0.66 * (a_hit - a_rest)):
        gt = (pv[0] + L_arm * math.cos(math.radians(ga)), pv[1] + L_arm * math.sin(math.radians(ga)))
        S.append(peg(pv, gt, ghost=True))
    S.append(arcs(pv, (L_arm + 26,), a_rest + 4, a_hit - 6, w=5, op=0.85, color=STAR, dash='2 12'))
    S.append(brass_ring(*ring))
    S.append('<circle cx="%s" cy="%s" r="%s" fill="url(#tingglow)"/>' % (f(contact[0]), f(contact[1]), f(80)))
    tipA = (pv[0] + (L_arm + 8) * math.cos(math.radians(a_hit - 9)), pv[1] + (L_arm + 8) * math.sin(math.radians(a_hit - 9)))
    S.append(peg(pv, tipA))
    S.append(bolt(*pv))
    S.append(arcs(pv, (L_arm - 44,), a_hit - 20, a_rest + 10, w=5, op=0.95, color=WHITE, dash='3 10', arrow=True))
    S.append(ting(contact[0] + 6, contact[1] + 22, 38, glow=False, rays=(-20, 20, 60, 160, 120)))

    # ---- ceiling band on top, rail, pulleys, lantern cord
    S.append('<rect x="0" y="0" width="1080" height="%d" fill="%s"/>' % (CEIL, COFFEE))
    S.append('<rect x="0" y="%d" width="1080" height="10" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (CEIL - 6, INK))
    S.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="#5A3A28" stroke-width="4"/>' % (lx, lx, ly - 72))
    S.append('<rect x="%s" y="%s" width="40" height="16" fill="%s" stroke="%s" stroke-width="4"/>' % (f(latch[0] - 20), f(latch[1] - 8), BRASS, INK))
    S.append(pulley(*pB))
    S.append('<rect width="1080" height="1920" fill="url(#vig)"/>')
    S.append('</svg>')
    return '\n'.join(S)


# =====================================================================
#  POSES SHEET 1080x1080
# =====================================================================
def build_poses(sil=False):
    REG['limbs'].clear()
    REG['figs'].clear()
    FLp = 990
    D = 200
    Htot = 3.7 * D
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">', defs_common()]
    if sil:
        S.append('<style>.fig *{fill:#000 !important;stroke:#000 !important;opacity:1 !important}'
                 '.c1 *{fill:#F00 !important;stroke:#F00 !important}.c2 *{fill:#0A0 !important;stroke:#0A0 !important}'
                 '.c3 *{fill:#00F !important;stroke:#00F !important}</style>')
        S.append('<rect width="1080" height="1080" fill="#fff"/>')
    else:
        S.append('<rect width="1080" height="1080" fill="%s"/>' % COFFEE)
        for cx in (190, 540, 880):
            S.append('<ellipse cx="%d" cy="600" rx="230" ry="520" fill="url(#pool)"/>' % cx)
        S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#1C1410"/>' % (FLp, 1080 - FLp))
        S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#4A382C" stroke-width="4"/>' % (FLp, FLp))
    rim = (AMBER, 3.0, (-0.6, -0.8))

    # ---------- (1) READY STANCE: facing left, broom across the body, bristles down-left
    hd = (190, 366)
    bfl = (72, FLp)
    base, tip = broom_line(D, Htot, bfl, 22)
    p1 = dict(D=D, head=hd, turn=-1, neck_ang=-10, spine=7, bow=0.07,
              arms=dict(L=dict(hand=on_line(base, tip, 772), bend=-1, thumb=-1, pole=ang(base, tip)),
                        R=dict(hand=on_line(base, tip, 690), bend=1, thumb=-1, pole=ang(base, tip))),
              legs=dict(L=dict(sole=(150, FLp), bend=-1), R=dict(sole=(330, FLp), bend=-1)), swing=0.0, toe_rim=AMBER)
    L, J = figure_fit(LOU_F, p1, rim=rim)
    hd = p1['head']
    hp = J['hip']
    pan_grip = (hp[0] + 52, hp[1] + 20)
    g = ['<g class="fig%s">' % (' c1' if sil == 'color' else '')]
    if not sil:
        S.append(cast_shadow(232, FLp + 4, 150, 15, 0.6))
    g.append(L['L_leg'] + L['L_arm'] + L['L_pad'] + L['spine'])
    g.append(dustpan(pan_grip, 78, D))
    g.append(L['hip'])
    fan, handle = broom(base, tip, D, floor=FLp, skew=-4)
    g.append(fan + handle + L['R_leg'] + L['R_arm'] + L['R_pad'])
    g.append(L['collar_back'] + L['neck'] + L['collar'])
    g.append(head('p1', hd[0], hd[1], D, LOU_H, EXPR['neutral'], turn=-1)[0])
    g.append(L['L_thumb'] + L['R_thumb'])
    g.append('</g>')
    S.append(''.join(g))
    if not sil:
        S.append(puffs(26, FLp - 10, 0.7, -1))

    # ---------- (2) SIGNATURE 'DUSTPAN OVERHEAD': facing right, near arm straight up 27 deg
    hd = (540, 366)
    bfl = (652, FLp)
    base, tip = broom_line(D, Htot, bfl, 3)
    p2 = dict(D=D, head=hd, turn=1, neck_ang=10, spine=-8, bow=-0.06,
              arms=dict(L=dict(ang=-27, straight=True, mode='grip', thumb=1, pole=math.radians(-90 + 8)),
                        R=dict(hand=on_line(base, tip, 762), bend=-1, thumb=1, pole=ang(base, tip))),
              legs=dict(L=dict(sole=(466, FLp - 15), bend=1, rot=24), R=dict(sole=(586, FLp), bend=1)), swing=-0.06,
              rag_side=-1, toe_rim=AMBER)
    L, J = figure_fit(LOU_F, p2, rim=rim)
    hd = p2['head']
    grip = J['L_wr']
    g = ['<g class="fig%s">' % (' c2' if sil == 'color' else '')]
    if not sil:
        S.append(cast_shadow(560, FLp + 4, 140, 15, 0.6))
    g.append(L['R_leg'] + L['R_arm'] + L['R_pad'] + L['spine'] + L['hip'])
    fan, handle = broom(base, tip, D, floor=FLp, skew=10)
    g.append(fan + handle + L['L_leg'] + L['L_arm'])
    g.append(L['collar_back'] + L['neck'] + L['collar'])
    g.append(head('p2', hd[0], hd[1], D, LOU_H, dict(EXPR['smug'], pupils=((0.9, 1), (0.9, 1))), turn=1)[0])
    g.append(L['L_pad'])
    pan_a = -90 + 8
    g.append(dustpan(grip, pan_a, D))
    g.append(L['L_thumb'] + L['R_thumb'])
    g.append('</g>')
    S.append(''.join(g))
    if not sil:
        pc = dustpan_center(grip, pan_a, D)
        S.append(arcs((pc[0] + 40, pc[1] + 10), (70,), -150, -110, w=4, op=0.85, color=STAR, dash='3 10'))
        S.append(ting(pc[0] - 6, pc[1] - 22, 30))
        S.append(puffs(bfl[0] + 50, FLp - 10, 0.75, 1))

    # ---------- (3) BIG REACTION 'SURPRISE JUMP': front view, both arms straight up in a narrow V
    up = 70
    hd = (872, 300)
    p3 = dict(D=D, head=hd, turn=0, neck_ang=-4, neck_vis=0.15, yoke=0.08, spine=7, bow=0.06, sh=(0.31, 0.31), toe_rim=AMBER,
              arms=dict(L=dict(ang=-25, straight=True, mode='open', thumb=1, wrist=26),
                        R=dict(ang=25, straight=True, mode='open', thumb=-1, wrist=-26)),
              legs=dict(L=dict(a=-30, b=84, toe=-1, rot=26), R=dict(a=28, b=-86, toe=1, rot=-26)), swing=0.05, rag_side=1)
    L, J = figure(LOU_F, p3, rim=rim)
    sole_y = max(J['L_an'][1], J['R_an'][1]) + LOU_F['shoe_h'] * D
    dy = (FLp - up) - sole_y
    p3['head'] = (hd[0], hd[1] + dy)
    REG['figs'].pop()
    L, J = figure(LOU_F, p3, rim=rim)
    hd = p3['head']
    g = ['<g class="fig%s">' % (' c3' if sil == 'color' else '')]
    if not sil:
        S.append(cast_shadow(875, FLp + 4, 95, 11, 0.38))
    # broom tumbling behind him (bristles up beside the right forearm), dustpan flying up inside the V
    bt = (972, 500)
    bang = 24
    bb = (bt[0] - 492 * math.sin(math.radians(bang)), bt[1] + 492 * math.cos(math.radians(bang)))
    bc = ((bt[0] + bb[0]) / 2, (bt[1] + bb[1]) / 2)
    fan, handle = broom(bt, bb, D)
    if not sil:
        for gdeg, gop in ((-16, 0.18), (-8, 0.32)):
            S.append('<g opacity="%s" transform="rotate(%s %s %s)">%s%s</g>' % (gop, gdeg, f(bc[0]), f(bc[1]), fan, handle))
    g.append(fan + handle)
    g.append(L['L_leg'] + L['R_leg'] + L['spine'] + L['hip'])
    g.append(L['L_arm'] + L['R_arm'] + L['L_pad'] + L['R_pad'] + L['L_thumb'] + L['R_thumb'])
    g.append(L['collar_back'] + L['neck'] + L['collar'])
    g.append(head('p3', hd[0], hd[1], D, LOU_H, dict(EXPR['surprised'], emanata=(-1,)), turn=0)[0])
    pg = (hd[0] - 30, 150)
    g.append(dustpan(pg, -62, D))
    g.append('</g>')
    S.append(''.join(g))
    if not sil:
        S.append(arcs(bc, (316,), -74, -52, w=4, op=0.85, color=STAR, dash='3 10'))
        S.append(arcs(bc, (262,), 112, 132, w=4, op=0.85, color=STAR, dash='3 10'))
        S.append(arcs((pg[0] + 34, pg[1] - 40), (92,), 150, 215, w=4, op=0.85, color=STAR, dash='3 10'))
    S.append('</svg>')
    return '\n'.join(S)


# =====================================================================
#  LINEUP 540x1080 -- hero alone, 3/4 facing viewer's left, exactly 900 px tall incl. hair
# =====================================================================
def lineup_svg(D, sil=False, sole_y=1010.0):
    REG['limbs'].clear()
    REG['figs'].clear()
    FLy = sole_y                       # geometric sole line (outline stroke hangs ~2 px below it)
    Htot = 3.7 * D
    hx = 286
    hy = FLy - 3.7 * D + D / 2 - 10
    bfl = (hx - 0.86 * D, FLy)
    base, tip = broom_line(D, Htot, bfl, 5)
    P = dict(D=D, head=(hx, hy), turn=-1, neck_ang=-10, spine=6, bow=0.07,
             arms=dict(L=dict(hand=on_line(base, tip, hy + 1.75 * D), bend=1, thumb=-1, pole=ang(base, tip)),
                       R=dict(a=-8, b=10, thumb=1, wrist=4)),
             legs=dict(L=dict(sole=(hx - 0.30 * D, FLy), bend=-1), R=dict(sole=(hx + 0.42 * D, FLy), bend=-1)),
             swing=0.0)
    L, J = figure_fit(LOU_F, P)
    hx, hy = P['head']
    hsvg, hinfo = head('lu', hx, hy, D, LOU_H, dict(EXPR['neutral'], pupils=((-0.5, 1), (-0.5, 1)), mouth='a', mouth_turn=-0.008), turn=-1)
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="1080" viewBox="0 0 540 1080">']
    if sil:
        S.append('<style>.fig *{fill:#000 !important;stroke:#000 !important;opacity:1 !important}</style>')
        S.append('<rect width="540" height="1080" fill="#fff"/>')
    else:
        S.append('<rect width="540" height="1080" fill="#EDEAE4"/>')
        S.append('<line x1="0" y1="1011.5" x2="540" y2="1011.5" stroke="#CFC9C0" stroke-width="3"/>')
        S.append('<ellipse cx="%s" cy="1012" rx="%s" ry="12" fill="#2A211C" opacity="0.16"/>' % (f(hx - 0.1 * D), f(1.05 * D)))
    g = ['<g class="fig">']
    g.append(L['L_leg'] + L['L_arm'] + L['L_pad'] + L['spine'] + L['hip'])
    fan, handle = broom(base, tip, D, floor=FLy, skew=0)
    g.append(fan + handle + L['R_leg'] + L['R_arm'] + L['R_pad'])
    g.append(L['collar_back'] + L['neck'] + L['collar'])
    g.append(hsvg)
    g.append(L['L_thumb'] + L['R_thumb'])
    g.append('</g>')
    S += g
    S.append('</svg>')
    return '\n'.join(S), hinfo['top'], FLy


def build_lineup(sil=False):
    """Visible figure = exactly 900 px: geometric height 896.8 + ~1 px brush edge on top + ~2.2 px sole stroke below,
    with the shoe outlines touching y = 1010."""
    D = 232.0
    sole_y = 1010.0 - 2.2
    for _ in range(5):
        svg, top, fl = lineup_svg(D, sil, sole_y)
        D = D * 896.8 / (fl - top)
    svg, top, fl = lineup_svg(D, sil, sole_y)
    return svg, D, fl - top


# =====================================================================
#  CHECKS
# =====================================================================
def check_figs(label):
    for J in REG['figs']:
        D = J['D']
        R = D / 2
        hx, hy = J['head']
        soles = [J[s + '_an'][1] + 0.10 * D for s in ('L', 'R')]
        H = max(soles) - (hy - R)
        msg = ['%s D=%.0f H=%.0f (%.2f D, head %.1f%%)' % (label, D, H, H / D, 100 * D / H)]
        msg.append('hip-off=%.2fD' % ((hx - J['hip'][0]) / D))
        spine_len = sum(math.hypot(J['spine'][i][0] - J['spine'][i - 1][0], J['spine'][i][1] - J['spine'][i - 1][1])
                        for i in range(2, len(J['spine'])))
        msg.append('spine=%.2fD' % (spine_len / D))
        for s in ('L', 'R'):
            S, el, wr = J['S' + s], J[s + '_el'], J[s + '_wr']
            tipp = J[s + '_tip']
            dmin = min(seg_dist((hx, hy), S, el), seg_dist((hx, hy), el, wr), seg_dist((hx, hy), wr, tipp))
            clear = (dmin - R - 0.036 * D) / D
            ear = (hx + (-1 if s == 'L' else 1) * (R + 0.08 * D), hy)
            de = min(seg_dist(ear, S, el), seg_dist(ear, el, wr), seg_dist(ear, wr, tipp)) - 0.036 * D
            msg.append('arm%s skull%+.2fD ear%+.2fD' % (s, clear, de / D))
            if (s + '_legshort') in J and J[s + '_legshort'] > 0.5:
                msg.append('LEG%s SHORT %.0fpx' % (s, J[s + '_legshort']))
            if (s + '_short') in J and J[s + '_short'] > 0.5:
                msg.append('arm%s short %.0fpx' % (s, J[s + '_short']))
        xs = [J['L_an'][0], J['R_an'][0], J['L_wr'][0], J['R_wr'][0]]
        msg.append('base=%.2fD' % ((max(J['L_an'][0], J['R_an'][0]) - min(J['L_an'][0], J['R_an'][0]) + 0.3 * D) / D))
        print('  ' + ' | '.join(msg))


if __name__ == '__main__':
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(build_scene())
    check_figs('scene')
    with open(os.path.join(HERE, 'scene_bg.svg'), 'w') as fh:
        fh.write(build_scene(bg_only=True))
    with open(os.path.join(HERE, 'poses.svg'), 'w') as fh:
        fh.write(build_poses())
    check_figs('poses')
    with open(os.path.join(HERE, 'poses_sil.svg'), 'w') as fh:
        fh.write(build_poses(sil=True))
    with open(os.path.join(HERE, 'poses_silc.svg'), 'w') as fh:
        fh.write(build_poses(sil='color'))
    svg, D, h = build_lineup()
    with open(os.path.join(HERE, 'lineup.svg'), 'w') as fh:
        fh.write(svg)
    check_figs('lineup')
    print('  lineup D=%.1f total height incl. hair = %.1f px' % (D, h))
    svg, D, h = build_lineup(sil=True)
    with open(os.path.join(HERE, 'lineup_sil.svg'), 'w') as fh:
        fh.write(svg)
    print('wrote scene.svg poses.svg lineup.svg (+ silhouettes, bg)')
