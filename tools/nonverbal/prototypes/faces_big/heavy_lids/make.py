#!/usr/bin/env python3
"""Heavy Lids / 半目の夜勤 -- BIG-EYE round-head stick version.

One face rig     : head(uid, cx, cy, D, H, E, turn, look)
One stick rig    : figure(F, P)  (+ one costume surface on the torso)
Outputs          : scene.svg, faces.svg, hero.svg (Lou), partner.svg (Dot).
All sizes are fractions of D = the skull-disc diameter (ears, hair and nose excluded).
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
#  BIG-EYE ROUND-HEAD FACE RIG
#  head(uid, cx, cy, D, H, E, turn)
#    H = character head spec, E = expression.  Every size is a fraction of D
#    (skull-disc diameter without ears, hair or nose).
#  Eye pipeline per eye:  white shape -> pupil (placed inside the visible opening,
#  clipped by rim and lids) -> upper-lid mask (lid tone) -> lower-lid mask (skin)
#  -> rim -> thick ink lid line (the darkest, thickest mark on the face).
# =====================================================================
EYE_WHITE = '#FDF8EE'


def pip(x, y, poly):
    """point-in-polygon (ray casting)"""
    ins = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi):
            ins = not ins
        j = i
    return ins


def eye_poly(shape, ex, ey, w, h, n=40):
    """closed polygon of the eye white; (ex, ey) = centre of its bounding box."""
    P = []
    if shape == 'bowl':                      # Lou: flat top, broad superelliptic bottom
        top = ey - h / 2
        k = 2.7
        for i in range(n + 1):
            th = math.pi * i / n
            c, s = math.cos(th), math.sin(th)
            P.append((ex + (w / 2) * math.copysign(abs(c) ** (2 / k), c), top + h * (abs(s) ** (2 / k))))
    elif shape == 'rsq':                     # Dot: rounded square, TV screen
        k = 4.6
        for i in range(2 * n):
            th = 2 * math.pi * i / (2 * n)
            c, s = math.cos(th), math.sin(th)
            P.append((ex + (w / 2) * math.copysign(abs(c) ** (2 / k), c), ey + (h / 2) * math.copysign(abs(s) ** (2 / k), s)))
    else:                                    # cameo: plain ellipse
        for i in range(2 * n):
            th = 2 * math.pi * i / (2 * n)
            P.append((ex + w / 2 * math.cos(th), ey + h / 2 * math.sin(th)))
    return P


def poly_d(P):
    return 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in P) + ' Z'


def x_range_on_line(P, fy, x0, x1, steps=160):
    """x-extent where the line y = fy(x) is inside polygon P"""
    xs = [x0 + (x1 - x0) * i / steps for i in range(steps + 1)]
    ins = [x for x in xs if pip(x, fy(x), P)]
    if not ins:
        return None
    return min(ins), max(ins)


def place_pupil(vis, ex, ey, w, h, r, dirv, allow=0.0):
    """centroid of the visible opening, then slide along dirv until the (shrunk) disc touches the edge."""
    pts_in = []
    st = max(min(w, h) / 22.0, 1.0)
    yy = ey - h / 2
    while yy <= ey + h / 2:
        xx = ex - w / 2
        while xx <= ex + w / 2:
            if vis(xx, yy):
                pts_in.append((xx, yy))
            xx += st
        yy += st
    if not pts_in:
        return (ex, ey)
    c0 = (sum(p[0] for p in pts_in) / len(pts_in), sum(p[1] for p in pts_in) / len(pts_in))
    angs = [2 * math.pi * k / 20 for k in range(20)]
    rr = r * (1 - allow)

    def fits(c, rad):
        return all(vis(c[0] + rad * math.cos(a), c[1] + rad * math.sin(a)) for a in angs)
    while rr > 0.25 * r and not fits(c0, rr):
        rr *= 0.92
    if dirv is None or (abs(dirv[0]) < 1e-6 and abs(dirv[1]) < 1e-6):
        return c0
    d = norm(dirv)
    best = c0
    stp = max(w, h) / 90.0
    for k in range(1, 120):
        c = (c0[0] + d[0] * stp * k, c0[1] + d[1] * stp * k)
        if fits(c, rr):
            best = c
        else:
            break
    return best


def toothpick(p, a_deg, D, fs):
    """light wood pick from the mouth corner p; a_deg up from the facing direction."""
    a = math.radians(a_deg)
    u = (fs * math.cos(a), -math.sin(a))
    L = 0.27 * D
    q = add(p, u, L)
    p0 = add(p, u, -0.03 * D)
    o = ['<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(p0[0]), f(p0[1]), f(q[0]), f(q[1]), INK, f(max(0.040 * D, 6))),
        '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(p0[0]), f(p0[1]), f(q[0] - u[0] * 0.01 * D), f(q[1] - u[1] * 0.01 * D), '#E9CD94', f(max(0.020 * D, 3)))]
    return ''.join(o), q


def head(uid, cx, cy, D, H, E, turn=0.0, mark_color=WHITE, look=None):
    """One round head.  turn: -1 = 3/4 facing screen-left, +1 = 3/4 facing right, 0 = front.
    look = absolute target point both pupils converge on (overrides E['gaze'])."""
    R = D / 2.0
    t = max(-1.0, min(1.0, turn))
    at = abs(t)
    bs = -1 if t >= 0 else 1                       # screen-x direction of the back of the head
    fs = -bs                                       # facing side
    OL = max(H.get('outline', 0.022) * D, 3.0)
    skin = H['skin']
    o = []
    info = dict(top=cy - R, D=D, cx=cx, cy=cy)
    top = cy - R
    o.append('<g id="%s">' % uid)
    o.append('<defs><clipPath id="%s-hc"><circle cx="%s" cy="%s" r="%s"/></clipPath></defs>' % (uid, f(cx), f(cy), f(R)))

    # ---------------------------------------------------------------- ears (behind the skull)
    erx, ery = H.get('ear_rx', 0.075) * D, H.get('ear_ry', 0.10) * D
    for side in (-1, 1):
        if E.get('hide_ear') == side:
            continue
        prot = H.get('ear_prot', 0.07)
        if at > 0.05:
            prot = prot + 0.02 * at if side == bs else prot - 0.05 * at
        ecx = cx + side * (R + prot * D - erx)
        ecy = cy + H.get('ear_dy', 0.0) * D
        o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
            f(ecx), f(ecy), f(erx), f(ery), skin, INK, f(OL)))
        o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(ecx + side * 0.01 * D), f(ecy - ery * 0.5), f(ecx + side * erx * 0.85), f(ecy),
            f(ecx + side * 0.01 * D), f(ecy + ery * 0.5), INK, f(max(0.015 * D, 2.5))))
        if H.get('ear_lobe_tone'):
            o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" opacity="0.5"/>' % (
                f(ecx + side * erx * 0.25), f(ecy + ery * 0.15), f(erx * 0.35), f(ery * 0.45), H['ear_lobe_tone']))

    # ---------------------------------------------------------------- grey side tufts (cameo gramps)
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

    # ---------------------------------------------------------------- curl cap: outline pass behind the skull
    curls = None
    if H.get('hair') == 'curls':
        curls = curl_geometry(cx, cy, D, t, H)
        o.append('<g fill="%s" stroke="%s" stroke-width="%s">%s</g>' % (
            H['hair_color'], INK, f(OL * 2), ''.join('<circle cx="%s" cy="%s" r="%s"/>' % (f(x), f(y), f(r)) for x, y, r in curls['rim'])))
        info['top'] = min(info['top'], min(y - r for x, y, r in curls['rim']) - OL)

    # ---------------------------------------------------------------- skin layer (re-used inside the lids)
    xc = cx + 0.12 * t * D                         # feature cluster centre shifts toward the facing side
    sk = ['<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(cx), f(cy), f(R), skin)]
    if H.get('jaw'):                               # flat jaw value (stubble or shade) on the lower ~30%
        yt = cy + R - H['jaw_frac'] * D
        sag = H.get('jaw_sag', 0.05) * D
        band = 'M%s,%s Q%s,%s %s,%s L%s,%s L%s,%s Z' % (
            f(cx - 1.25 * R), f(yt - sag), f(xc + fs * 0.03 * D * at), f(yt + sag * 1.6), f(cx + 1.25 * R), f(yt - sag),
            f(cx + 1.25 * R), f(cy + R + 5), f(cx - 1.25 * R), f(cy + R + 5))
        sk.append('<path d="%s" fill="%s" clip-path="url(#%s-hc)"/>' % (band, H['jaw'], uid))
    o.append('<g id="%s-skin">%s</g>' % (uid, ''.join(sk)))

    # ---------------------------------------------------------------- skull outline (curls are laid over it)
    o.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(cx), f(cy), f(R), INK, f(OL)))

    # ---------------------------------------------------------------- curl cap fill (inside + bumps), texture
    if curls:
        hc = H['hair_color']
        o.append('<g fill="%s">%s</g>' % (hc, ''.join('<circle cx="%s" cy="%s" r="%s"/>' % (f(x), f(y), f(r)) for x, y, r in curls['rim'])))
        o.append('<path d="%s" fill="%s" clip-path="url(#%s-hc)"/>' % (curls['cap'], hc, uid))
        # scalloped hairline: ink bumps then fill
        o.append('<g clip-path="url(#%s-hc)">' % uid)
        o.append('<g fill="%s" stroke="%s" stroke-width="%s">%s</g>' % (
            hc, INK, f(OL * 1.6), ''.join('<circle cx="%s" cy="%s" r="%s"/>' % (f(x), f(y), f(r)) for x, y, r in curls['line'])))
        o.append('<g fill="%s">%s</g>' % (hc, ''.join('<circle cx="%s" cy="%s" r="%s"/>' % (f(x), f(y), f(r * 0.98)) for x, y, r in curls['line'])))
        o.append('<path d="%s" fill="%s"/>' % (curls['cap_inner'], hc))
        o.append('</g>')
        for (x, y, r, a0) in curls['tex']:
            o.append('<path d="M%s A%s,%s 0 1 1 %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                pts([(x + r * math.cos(math.radians(a0)), y + r * math.sin(math.radians(a0)))]), f(r), f(r),
                pts([(x + r * math.cos(math.radians(a0 + 250)), y + r * math.sin(math.radians(a0 + 250)))]),
                H.get('hair_hi', '#6A4A3E'), f(max(0.012 * D, 2))))


    # ---------------------------------------------------------------- forehead creases (gramps)
    if H.get('creases'):
        for k in range(3):
            yy = cy - 0.36 * D + k * 0.06 * D
            o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.8"/>' % (
                pts([(xc - 0.20 * D + k * 0.02 * D, yy + 0.02 * D)]), pts([(xc, yy - 0.025 * D)]),
                pts([(xc + 0.20 * D - k * 0.02 * D, yy + 0.02 * D)]), INK, f(0.02 * D)))

    # ---------------------------------------------------------------- grey sideburns (flat patches in front of the ears)
    if H.get('sideburns'):
        for side in (-1, 1):
            if E.get('hide_ear') == side:
                continue
            y0, y1 = cy - 0.20 * D, cy - 0.01 * D
            xo = lambda yy: cx + side * math.sqrt(max(R * R - (yy - cy) ** 2, 0))
            pa = (xo(y0), y0)
            pb = (xo(y1), y1)
            inset = 0.075 * D if not (at > 0.05 and side == fs) else 0.05 * D
            poly = [pa, pb, (pb[0] - side * inset * 0.7, pb[1]), (pa[0] - side * inset, pa[1] + 0.03 * D)]
            o.append('<polygon points="%s" fill="%s" clip-path="url(#%s-hc)"/>' % (pts(poly), H['sideburns'], uid))

    # ---------------------------------------------------------------- barcode comb-over (Lou): 3 strands, tips spring off the far side
    if H.get('hair') == 'barcode':
        o.append(barcode(cx, cy, D, t, E.get('strands', 'combed'), H['hair_color'], uid, info))

    # ---------------------------------------------------------------- forehead frown lines (angry)
    if E.get('frown'):
        for k in (-1, 1):
            x0 = xc + k * 0.03 * D
            o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                pts([(x0 + k * 0.01 * D, top + 0.17 * D)]), pts([(x0 - k * 0.012 * D, top + 0.215 * D)]),
                pts([(x0, top + 0.26 * D)]), INK, f(0.018 * D)))

    # ================================================================ EYES
    es = E.get('eye_scale', 1.0)
    shape = H['eye_shape']
    ewn = H['eye_w'] * D * es
    ewf = ewn * (1 - 0.25 * at)                    # far eye compresses to 75 %
    eh = H['eye_h'] * D * es
    gap = H['eye_gap'] * D * E.get('gap_scale', 1.0) * (1 - 0.15 * at)
    if t > 0.05:                                   # facing right -> right-screen eye is the far eye
        wl, wr = ewn, ewf
    elif t < -0.05:
        wl, wr = ewf, ewn
    else:
        wl = wr = ewn
    ey = top + H['eye_c'] * D + E.get('eye_dy', 0.0) * D
    centers = [(xc - gap / 2 - wl / 2, wl), (xc + gap / 2 + wr / 2, wr)]
    info['eyes'] = [(x, ey) for x, _ in centers]
    pr = H['pupil'] * D * E.get('pupil_scale', 1.0) / 2
    lid = E.get('lid', (H['lid_rest'], H['lid_rest']))
    low = E.get('low', (0.0, 0.0))
    low_curve = E.get('low_curve', 0.06)
    tilt = E.get('lid_tilt', (0.0, 0.0))
    if not isinstance(tilt, (tuple, list)):
        tilt = (tilt, tilt)
    lid_w = max(H['lid_w'] * D, 3.5)
    rim = max(H['rim'] * D, 2.0)
    lidc = shade(skin, H.get('lid_shade', 0.10))
    eye_set = E.get('eyes', (0, 1))
    gaze = E.get('gaze', H.get('gaze_rest', (0.0, 0.0)))
    allow = E.get('pin', 0.0)
    for i, (ex, ew) in enumerate(centers):
        if i not in eye_set:
            continue
        eid = '%s-e%d' % (uid, i)
        P = eye_poly(shape, ex, ey, ew, eh)
        etop = ey - eh / 2
        inner = 1 if i == 0 else -1                # +x direction toward the nose for this eye
        c_up = lid[i]
        tn = math.tan(math.radians(tilt[i]))

        def lidy(x, c_up=c_up, ex=ex, inner=inner, tn=tn, etop=etop):
            return etop + c_up * eh + inner * tn * (x - ex)
        c_lo = low[i]

        def lowy(x, c_lo=c_lo, ex=ex, ew=ew):
            if c_lo <= 0:
                return 1e9
            k = max(0.0, 1 - ((x - ex) / (ew / 2)) ** 2)
            return ey + eh / 2 - c_lo * eh - low_curve * D * k

        def vis(x, y, P=P, lidy=lidy, lowy=lowy, c_up=c_up):
            return pip(x, y, P) and (c_up <= 0 or y > lidy(x) + lid_w * 0.35) and y < lowy(x) - 1
        o.append('<defs><clipPath id="%s-c"><path d="%s"/></clipPath></defs>' % (eid, poly_d(P)))
        closed = c_up >= 0.999
        o.append('<g clip-path="url(#%s-c)">' % eid)
        o.append('<path d="%s" fill="%s"/>' % (poly_d(P), EYE_WHITE))
        if not closed:
            # ---- gaze direction
            if look is not None:
                dv = (look[0] - ex, look[1] - ey)
                dv = norm(dv)
                park = E.get('park', H.get('park', 0.0))
                dv = (dv[0], dv[1] + park)
            else:
                g = gaze[i] if isinstance(gaze[0], (tuple, list)) else gaze
                dv = g
            pc = place_pupil(vis, ex, ey, ew, eh, pr, dv, allow)
            for gx, gy, gop in E.get('ghosts', ()):
                o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="%s"/>' % (
                    f(pc[0] + gx * D), f(pc[1] + gy * D), f(pr), INK, gop))
            o.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(pc[0]), f(pc[1]), f(pr), INK))
        if c_up > 0:
            xa, xb = ex - ew, ex + ew
            poly = [(xa, ey - D), (xb, ey - D), (xb, lidy(xb)), (xa, lidy(xa))]
            o.append('<polygon points="%s" fill="%s"/>' % (pts(poly), lidc))
        if c_lo > 0 and not closed:
            xa, xb = ex - ew / 2 - 4, ex + ew / 2 + 4
            lp = 'M%s,%s L%s,%s Q%s,%s %s,%s L%s,%s Z' % (
                f(xa), f(ey + D), f(xa), f(lowy(xa + 4) + 0), f(ex), f(lowy(ex) - low_curve * D), f(xb), f(lowy(xb - 4)), f(xb), f(ey + D))
            o.append('<path d="%s" fill="%s"/>' % (lp, skin))
            o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(xa), f(lowy(xa + 4)), f(ex), f(lowy(ex) - low_curve * D), f(xb), f(lowy(xb - 4)), INK, f(lid_w * 0.55)))
        o.append('</g>')
        dome = H.get('rim_mode') == 'below_lid' and 0 < c_up < 0.999
        if dome:
            # heavy lid: a soft lid-tone dome over the eye (no ink across the top, so it never reads as glasses);
            # the ink rim only runs where the white shows, below the lid line
            xr0 = x_range_on_line(P, lidy, ex - ew / 2 - 2, ex + ew / 2 + 2) if H.get('lid_dome') else None
            if xr0:
                pa, pb = (xr0[0], lidy(xr0[0])), (xr0[1], lidy(xr0[1]))
                peak = etop - 0.012 * D
                y0 = (pa[1] + pb[1]) / 2
                yc = y0 + (peak - y0) / 0.75
                spread = 0.035 * D
                dd = 'M%s C%s %s %s Z' % (pts([(pa[0] - 2, pa[1] + 1)]), pts([(pa[0] - spread, yc)]), pts([(pb[0] + spread, yc)]),
                                         pts([(pb[0] + 2, pb[1] + 1)]))
                o.append('<path d="%s" fill="%s"/>' % (dd, lidc))
                o.append('<path d="M%s C%s %s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                    pts([pa]), pts([(pa[0] - spread, yc)]), pts([(pb[0] + spread, yc)]), pts([pb]), shade(skin, 0.32),
                    f(max(0.012 * D, 2))))
            # cover the anti-aliased white fringe above the lid line with lid skin
            pa_ = [(ex - ew, lidy(ex - ew) + 1), (ex + ew, lidy(ex + ew) + 1), (ex + ew, ey - D), (ex - ew, ey - D)]
            o.append('<defs><clipPath id="%s-a"><polygon points="%s"/></clipPath></defs>' % (eid, pts(pa_)))
            o.append('<path d="%s" fill="%s" stroke="%s" stroke-width="4" clip-path="url(#%s-a)"/>' % (poly_d(P), lidc, lidc, eid))
            poly = [(ex - ew, lidy(ex - ew)), (ex + ew, lidy(ex + ew)), (ex + ew, ey + D), (ex - ew, ey + D)]
            o.append('<defs><clipPath id="%s-b"><polygon points="%s"/></clipPath></defs>' % (eid, pts(poly)))
            o.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" clip-path="url(#%s-b)"/>' % (
                poly_d(P), INK, f(rim), eid))
        else:
            o.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (poly_d(P), INK, f(rim)))
        if closed:
            # closed eye stays big: lid line across the full footprint + crease + lash tick
            yl = ey + eh * 0.15
            xr = (ex - ew / 2, ex + ew / 2)
            o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(xr[0]), f(yl - 0.02 * D), f(ex), f(yl + 0.07 * D), f(xr[1]), f(yl - 0.02 * D), INK, f(lid_w)))
            xo = xr[0] if inner == 1 else xr[1]
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(xo), f(yl - 0.02 * D), f(xo - inner * 0.035 * D), f(yl + 0.015 * D), INK, f(lid_w * 0.7)))
        elif c_up > 0:
            ext_o = H.get('lid_ext', 0.02) * D
            xr = x_range_on_line(P, lidy, ex - ew / 2 - 2, ex + ew / 2 + 2)
            if xr:
                xa = xr[0] - (ext_o if inner == 1 else 0.004 * D)
                xb = xr[1] + (ext_o if inner == -1 else 0.004 * D)
                o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                    f(xa), f(lidy(xa)), f(xb), f(lidy(xb)), INK, f(lid_w)))
        # ---- retracted upper lid: a thin crease arc above the eye (shock takes)
        if E.get('fold') and c_up <= 0:
            o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                pts([(ex - ew * 0.42, etop - 0.012 * D)]), pts([(ex, etop - 0.085 * D)]), pts([(ex + ew * 0.42, etop - 0.012 * D)]),
                INK, f(max(0.016 * D, 2.5))))
        # ---- bags / creases under the eye (adult signals)
        bo = 0.0 if H.get('bag_centred') else inner * 0.02 * D
        bc = 0.02 * D if H.get('bag_centred') else 0.012 * D
        for (dy, wf, op) in H.get('bags', ()):
            yb = ey + eh / 2 + dy * D
            o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="%s"/>' % (
                pts([(ex - ew * wf / 2 + bo, yb - bc)]), pts([(ex + bo * 0.5, yb + 0.03 * D)]),
                pts([(ex + ew * wf / 2 + bo, yb - bc)]), INK, f(max(0.016 * D, 2.4)), op))
        # ---- brow (Dot: short thick straight bar)
        if H.get('brow') and not E.get('no_brow'):
            bh = E.get('brow_up', H.get('brow_gap', 0.07)) * D
            bt = E.get('brow_tilt', (0.0, 0.0))
            if not isinstance(bt, (tuple, list)):
                bt = (bt, bt)
            bw = H['brow_len'] * D * (ew / ewn)
            bth = H['brow_th'] * D
            bxc = ex + inner * 0.01 * D
            byc = etop - bh - bth / 2
            ang_b = inner * bt[i]
            o.append('<g transform="rotate(%s %s %s)"><rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/></g>' % (
                f(ang_b), f(bxc), f(byc), f(bxc - bw / 2), f(byc - bth / 2), f(bw), f(bth), f(bth * 0.3), H['brow'], INK,
                f(max(0.012 * D, 2))))

    # ================================================================ NOSE
    nose = H.get('nose')
    ny0 = top + H.get('nose_top', 0.38) * D + E.get('eye_dy', 0.0) * D * 0.3
    if nose == 'drip':                              # Lou: long, heavy, drooping pear
        o.append(nose_drip(xc, ny0, D, t, fs, skin, H.get('nose_tint', skin), OL))
    elif nose == 'button':                          # Dot: small upturned button, nostrils showing
        o.append(nose_button(xc, ny0, D, t, fs, skin, OL))
    elif nose == 'hook':                            # cameo: simple J hook
        nl = 0.08 * D
        nx = xc + 0.03 * t * D
        o.append('<path d="M%s,%s L%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(nx), f(ny0), f(nx), f(ny0 + nl), f(nx), f(ny0 + nl * 1.4), f(nx + bs * nl * 0.6), f(ny0 + nl * 1.3), INK, f(0.02 * D)))

    # ================================================================ MOUTH
    m = E.get('mouth')
    lw = max(0.024 * D, 3)
    mx = xc + E.get('mouth_dx', H.get('mouth_dx', 0.0) * fs) * D
    my = top + H.get('mouth_y', 0.80) * D + E.get('mouth_dy', 0.0) * D
    mt = E.get('mouth_turn', 0.0) * D
    corner = None
    if m == 'flat':
        mw = E.get('mouth_w', 0.15) * D
        o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(mx - mw / 2), f(my + mt), f(mx), f(my - mt * 0.5), f(mx + mw / 2), f(my + mt * 0.3), INK, f(lw)))
        corner = (mx + fs * mw / 2, my + mt * (1 if fs < 0 else 0.3))
    elif m == 'smirk':
        mw = E.get('mouth_w', 0.20) * D
        sgn = fs
        p0 = (mx - sgn * mw / 2, my + 0.01 * D)
        p1 = (mx + sgn * mw / 2, my - 0.045 * D)
        o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            pts([p0]), pts([(mx + sgn * 0.02 * D, my + 0.03 * D)]), pts([p1]), INK, f(lw)))
        o.append('<path d="M%s q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            pts([(p1[0] - sgn * 0.005 * D, p1[1] - 0.03 * D)]), f(sgn * 0.02 * D), f(0.015 * D), f(sgn * 0.012 * D), f(0.05 * D), INK, f(lw * 0.7)))
        corner = p1
    elif m in ('shout', 'gasp'):
        mw = E.get('mouth_w', 0.32) * D
        mh = E.get('mouth_h', 0.17) * D
        mid = '%s-m' % uid
        if m == 'gasp':
            d = 'M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z' % (
                f(mx - mw / 2), f(my), f(mx - mw / 2), f(my - mh * 0.7), f(mx + mw / 2), f(my - mh * 0.7), f(mx + mw / 2), f(my),
                f(mx + mw / 2), f(my + mh * 0.9), f(mx - mw / 2), f(my + mh * 0.9), f(mx - mw / 2), f(my))
        else:
            d = 'M%s,%s L%s,%s Q%s,%s %s,%s Z' % (
                f(mx - mw / 2), f(my - mh * 0.35), f(mx + mw / 2), f(my - mh * 0.35), f(mx), f(my + mh * 1.0), f(mx - mw / 2), f(my - mh * 0.35))
        o.append('<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (mid, d))
        o.append('<path d="%s" fill="%s"/>' % (d, MOUTH_DARK))
        o.append('<g clip-path="url(#%s)"><ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#B5554A"/>' % (
            mid, f(mx + fs * 0.03 * D), f(my + mh * 0.75), f(mw * 0.32), f(mh * 0.35)))
        if m == 'shout':
            o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (f(mx - mw / 2), f(my - mh * 0.4), f(mw), f(mh * 0.28), EYE_WHITE))
        o.append('</g>')
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (d, INK, f(lw)))
        corner = (mx + fs * mw / 2, my - mh * 0.3)
    elif m in ('teeth', 'eek'):
        mw = E.get('mouth_w', 0.34) * D
        mh = E.get('mouth_h', 0.12) * D
        mid = '%s-m' % uid
        sag = (0.035 if m == 'eek' else -0.01) * D
        d = 'M%s,%s Q%s,%s %s,%s Q%s,%s %s,%s Q%s,%s %s,%s Z' % (
            f(mx - mw / 2), f(my + sag), f(mx), f(my - mh / 2 - 0.01 * D), f(mx + mw / 2), f(my + sag),
            f(mx + mw / 2 + 0.01 * D), f(my + mh / 2 + sag * 0.5), f(mx), f(my + mh / 2 + 0.01 * D),
            f(mx - mw / 2 - 0.01 * D), f(my + mh / 2 + sag * 0.5), f(mx - mw / 2), f(my + sag))
        o.append('<defs><clipPath id="%s"><path d="%s"/></clipPath></defs>' % (mid, d))
        o.append('<path d="%s" fill="%s"/>' % (d, EYE_WHITE))
        o.append('<g clip-path="url(#%s)">' % mid)
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>' % (
            f(mx - mw / 2), f(my + sag * 0.3), f(mx + mw / 2), f(my + sag * 0.3), INK, f(lw * 0.6)))
        for k in range(1, 6):
            xx = mx - mw / 2 + mw * k / 6
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>' % (
                f(xx), f(my - mh), f(xx), f(my + mh), INK, f(lw * 0.5)))
        o.append('</g>')
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (d, INK, f(lw)))
        corner = (mx + fs * mw / 2, my + sag)
    elif m == 'wobble':
        mw = E.get('mouth_w', 0.32) * D
        amp = 0.026 * D
        p = [(mx - mw / 2 + mw * k / 48, my + amp * math.sin(k / 48 * 3 * 2 * math.pi)) for k in range(49)]
        o.append('<path d="M%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>' % (
            ' L'.join('%s,%s' % (f(x), f(y)) for x, y in p), INK, f(lw)))
        corner = p[-1] if fs > 0 else p[0]
    elif m == 'o':
        o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
            f(mx), f(my), f(0.045 * D), f(0.055 * D), MOUTH_DARK, INK, f(lw * 0.85)))
        corner = (mx + fs * 0.04 * D, my)
    # ---- smile-line creases framing the mouth (adult counterweight)
    if H.get('creases_mouth') and m:
        mwh = E.get('mouth_w', 0.16) * D / 2
        for side in (-1, 1):
            k = 0.8 if (at > 0.5 and side == fs) else 1.0
            x0 = mx + side * (mwh + 0.04 * D) * k
            o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.8"/>' % (
                pts([(x0 - side * 0.01 * D, my - 0.06 * D)]), pts([(x0 + side * 0.022 * D, my - 0.005 * D)]),
                pts([(x0 - side * 0.004 * D, my + 0.05 * D)]), INK, f(0.016 * D)))
    # ---- toothpick (Lou)
    tp = E.get('toothpick')
    if H.get('toothpick') and tp is not None and corner is not None:
        if tp == 'fall':
            p = (corner[0] + fs * 0.10 * D, corner[1] + 0.16 * D)
            svg, _ = toothpick(p, 70, D, fs)
            o.append(svg)
            o.append(arcs((p[0] - fs * 0.05 * D, p[1] - 0.08 * D), (0.07 * D,), -160 if fs < 0 else -20, -100 if fs < 0 else -80,
                          w=max(0.012 * D, 2.5), op=0.9, color=INK))
        else:
            a = tp
            if E.get('tp_shake'):
                for da in (-14, 14):
                    s2, _ = toothpick(corner, a + da, D, fs)
                    o.append('<g opacity="0.3">%s</g>' % s2)
            svg, _ = toothpick(corner, a, D, fs)
            o.append(svg)

    # ================================================================ pen above the ear (Dot) - on top of curls
    if H.get('pen'):
        o.append(pen(cx, cy, D, t, bs))

    # ================================================================ marks
    sw = E.get('sweat')
    if sw:
        side = sw
        a = math.radians(-40 if side > 0 else 220)
        sx, sy = cx + (R + 0.03 * D) * math.cos(a), cy + (R + 0.03 * D) * math.sin(a)
        sz = 0.13 * D
        o.append('<path d="M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            f(sx), f(sy - sz / 2), f(sx + sz * .38), f(sy - sz * .05), f(sx + sz * .38), f(sy + sz / 2), f(sx), f(sy + sz / 2),
            f(sx - sz * .38), f(sy + sz / 2), f(sx - sz * .38), f(sy - sz * .05), f(sx), f(sy - sz / 2), '#CFE8F2', INK, f(0.014 * D)))
    if E.get('emanata'):
        for side in E['emanata']:
            for a0 in (-32, 0, 32):
                a = math.radians(a0)
                r0, r1 = R + 0.12 * D, R + 0.24 * D
                x0 = cx + side * r0 * math.cos(a)
                y0 = cy - 0.08 * D + r0 * math.sin(a)
                x1 = cx + side * r1 * math.cos(a)
                y1 = cy - 0.08 * D + r1 * math.sin(a)
                o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                    f(x0), f(y0), f(x1), f(y1), mark_color, f(max(0.024 * D, 4))))
    if E.get('gloom'):
        for k in range(4):
            gx = xc - 0.24 * D + k * 0.16 * D
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.55"/>' % (
                f(gx), f(top + 0.03 * D + (k % 2) * 0.03 * D), f(gx), f(top + 0.20 * D + (k % 2) * 0.02 * D),
                E.get('gloom_color', '#7A8FA0'), f(max(0.02 * D, 3.5))))
    if E.get('vein'):
        vx, vy = cx + bs * 0.25 * D, top + 0.14 * D
        for a0 in (0, 90, 180, 270):
            a = math.radians(a0 + 45)
            o.append('<path d="M%s Q%s %s" fill="none" stroke="#B0303A" stroke-width="%s" stroke-linecap="round"/>' % (
                pts([(vx + 0.02 * D * math.cos(a), vy + 0.02 * D * math.sin(a))]), pts([(vx + 0.06 * D * math.cos(a + 0.5), vy + 0.06 * D * math.sin(a + 0.5))]),
                pts([(vx + 0.07 * D * math.cos(a - 0.3), vy + 0.07 * D * math.sin(a - 0.3))]), f(0.022 * D)))
    o.append('</g>')
    return '\n'.join(o), info


# ---------------------------------------------------------------- hair pieces
STRANDS = {
    #   per strand: lift of the tip (D), curl of the tip (deg), sag of the whole strand (D)
    'combed': dict(lift=0.13, curl=45, wave=0.0, stand=0.0),
    'stand':  dict(lift=0.0, curl=0, wave=0.0, stand=1.0),
    'bristle': dict(lift=0.16, curl=75, wave=0.0, stand=0.25),
    'flail':  dict(lift=0.12, curl=60, wave=0.035, stand=0.5),
    'wilt':   dict(lift=0.05, curl=-55, wave=0.0, stand=0.0),
    'smooth': dict(lift=0.11, curl=60, wave=0.0, stand=0.0),
}


def barcode(cx, cy, D, t, mode, color, uid, info):
    """three comb-over strands rooted above the back ear, lying across the scalp,
    the tips springing up off the skull on the facing side."""
    R = D / 2.0
    bs = -1 if t >= 0 else 1
    fs = -bs
    S = STRANDS[mode]
    o = []
    for k in range(3):
        r_k = R - (0.045 + 0.055 * k) * D
        a_root = math.radians(62 - 6 * k)          # from vertical, on the back side
        a_end = math.radians(-(38 + 4 * k))        # on the facing side
        n = 18
        pts_ = []
        for j in range(n + 1):
            u = j / n
            a = a_root + (a_end - a_root) * u
            rr = r_k + S['wave'] * D * math.sin(u * math.pi * 3 + k)
            pts_.append((cx + bs * rr * math.sin(a), cy - rr * math.cos(a)))
        if S['stand'] >= 0.99:
            # surprised: each strand shoots straight up from its root
            root = pts_[0]
            rx = root[0] + fs * (0.08 + 0.09 * k) * D
            base = (rx, cy - R * 0.95 + (0.02 * k) * D)
            tipp = (rx + fs * 0.03 * D * (k - 1), base[1] - (0.24 - 0.03 * k) * D)
            curve = bezier(base, (base[0], base[1] - 0.08 * D), (tipp[0] - fs * 0.02 * D, tipp[1] + 0.08 * D), tipp, 16)
        else:
            end = pts_[-1]
            tang = norm((pts_[-1][0] - pts_[-2][0], pts_[-1][1] - pts_[-2][1]))
            # the tip leaves the scalp: pushed outward from the skull centre and upward
            outv = norm((end[0] - cx, end[1] - cy))
            L = (0.17 + 0.025 * k) * D
            c1 = add(end, tang, L * 0.5)
            lift = S['lift'] + 0.02 * k
            tipp = add(add(end, tang, L), outv, lift * D)
            cr = math.radians(S['curl'])
            c2 = add(tipp, (-(tang[0] * math.cos(cr) - tang[1] * math.sin(cr) * fs),
                            -(tang[1] * math.cos(cr) + tang[0] * math.sin(cr) * fs)), L * 0.35)
            if S['stand'] > 0:
                pts_ = [(x, y - S['stand'] * 0.05 * D * math.sin(math.pi * j / n)) for j, (x, y) in enumerate(pts_)]
            curve = pts_ + bezier(end, c1, c2, tipp, 12)[1:]
        o.append('<path d="%s" fill="%s"/>' % (taper(curve, 0.046 * D, 0.024 * D), INK))
        o.append('<path d="%s" fill="%s"/>' % (taper(curve, 0.024 * D, 0.008 * D), color))
        info['top'] = min(info['top'], min(p[1] for p in curve) - 0.02 * D)
    return ''.join(o)


def curl_geometry(cx, cy, D, t, H):
    """short tight curls: scalloped bumps on the rim + a cap down to a scalloped hairline."""
    R = D / 2.0
    at = abs(t)
    bs = -1 if t >= 0 else 1
    fs = -bs
    top = cy - R
    rb = 0.062 * D
    # angles measured from straight up, + toward the back side
    a_face = -(64 - 8 * at)
    a_back = 98 + 26 * at
    rim = []
    n = 13
    for j in range(n + 1):
        a = math.radians(a_face + (a_back - a_face) * j / n)
        rr = R + 0.012 * D
        rim.append((cx + bs * rr * math.sin(a), cy - rr * math.cos(a), rb * (0.85 if j in (0, n) else 1.0)))
    # hairline: from the facing temple across the forehead to the back ear top
    xc = cx + 0.12 * t * D
    hl = [
        (cx + bs * R * math.sin(math.radians(a_face)), cy - R * math.cos(math.radians(a_face))),
        (xc + fs * 0.20 * D, top + 0.10 * D),
        (xc - fs * 0.02 * D, top + 0.08 * D),
        (xc - fs * 0.22 * D, top + 0.095 * D),
        (cx + bs * (R - 0.035 * D), cy - 0.15 * D),
        (cx + bs * R * math.sin(math.radians(a_back)), cy - R * math.cos(math.radians(a_back))),
    ]
    line_pts = []
    for j in range(len(hl) - 1):
        for s in (0.0, 0.5):
            p = (hl[j][0] + (hl[j + 1][0] - hl[j][0]) * s, hl[j][1] + (hl[j + 1][1] - hl[j][1]) * s)
            line_pts.append((p[0], p[1], 0.038 * D))
    line_pts.append((hl[-1][0], hl[-1][1], 0.038 * D))
    big = R * 1.4
    cap = 'M%s L%s L%s L%s L%s L%s L%s L%s Z' % (
        pts([hl[0]]), pts([hl[1]]), pts([hl[2]]), pts([hl[3]]), pts([hl[4]]), pts([hl[5]]),
        pts([(cx + bs * big, cy + 0.6 * R)]), pts([(cx + bs * big, cy - big)]))
    cap += ' M%s L%s L%s Z' % (pts([hl[0]]), pts([(cx - bs * big, cy - big)]), pts([(cx + bs * big, cy - big)]))
    # inner cap (no stroke) slightly above the hairline so the bumps keep their ink edge
    up = [(x, y - 0.03 * D) for x, y in hl]
    cap_inner = 'M%s L%s L%s L%s L%s L%s L%s L%s Z' % (
        pts([up[0]]), pts([up[1]]), pts([up[2]]), pts([up[3]]), pts([up[4]]), pts([up[5]]),
        pts([(cx + bs * big, cy + 0.6 * R)]), pts([(cx + bs * big, cy - big)]))
    cap_inner += ' M%s L%s L%s Z' % (pts([up[0]]), pts([(cx - bs * big, cy - big)]), pts([(cx + bs * big, cy - big)]))
    tex = []
    for (u, v, a0) in ((-0.22, 0.06, 200), (0.0, 0.035, 160), (0.20, 0.06, 220), (-0.10, 0.10, 120),
                       (0.12, 0.10, 100), (0.32, 0.14, 150), (0.36, 0.26, 200)):
        x = cx + bs * u * D * 0.95 + 0.06 * t * D * (1 if u < 0.3 else 0)
        y = top + v * D
        if math.hypot(x - cx, y - cy) < R - 0.04 * D:
            tex.append((x, y, 0.024 * D, a0))
    return dict(rim=rim, line=line_pts, cap=cap, cap_inner=cap_inner, tex=tex)


def pen(cx, cy, D, t, bs):
    """mint ballpoint tucked above the back ear, poking out behind the head."""
    R = D / 2.0
    p0 = (cx + bs * (R - 0.16 * D), cy - 0.075 * D)     # writing tip end (forward, above the ear)
    a = math.radians(-24)
    u = (bs * math.cos(a), math.sin(a))
    L = 0.34 * D
    p1 = add(p0, u, L)
    w = 0.05 * D
    o = []
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(p0[0]), f(p0[1]), f(p1[0]), f(p1[1]), INK, f(w + 0.026 * D)))
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#6CC3A2" stroke-width="%s" stroke-linecap="round"/>' % (
        f(p0[0] + u[0] * 0.05 * D), f(p0[1] + u[1] * 0.05 * D), f(p1[0]), f(p1[1]), f(w)))
    tipc = add(p0, u, 0.02 * D)
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(p0[0]), f(p0[1]), f(tipc[0] + u[0] * 0.03 * D), f(tipc[1] + u[1] * 0.03 * D), '#E8E2D4', f(w * 0.7)))
    # clip on the barrel
    c0 = add(p1, u, -0.02 * D)
    c1 = add(p1, u, -0.13 * D)
    nrm = (-u[1], u[0])
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(c0[0] - nrm[0] * w * 0.55), f(c0[1] - nrm[1] * w * 0.55), f(c1[0] - nrm[0] * w * 0.55), f(c1[1] - nrm[1] * w * 0.55),
        INK, f(0.024 * D)))
    o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(c0[0] - nrm[0] * w * 0.55), f(c0[1] - nrm[1] * w * 0.55), f(c1[0] - nrm[0] * w * 0.55), f(c1[1] - nrm[1] * w * 0.55),
        '#C9D3CC', f(0.010 * D)))
    return ''.join(o)


def nose_drip(xc, ny0, D, t, fs, skin, tint, OL):
    """Lou's nose: narrow bridge from the eye gap, heavy drooping bulb (0.15 D wide)."""
    at = abs(t)
    sh = fs * 0.30 * at                       # shear: the bulb drifts toward the facing side
    prof = [(0.0, 0.0), (0.028, 0.06), (0.040, 0.13), (0.060, 0.19), (0.078, 0.245), (0.074, 0.29), (0.045, 0.32),
            (0.0, 0.33)]
    back_k = 1.0 - 0.35 * at                  # far half compresses
    right = [(u, v) for u, v in prof]
    left = [(-u, v) for u, v in prof[::-1]]
    P = []
    for (u, v) in right + left:
        side = 1 if u > 0 else -1
        k = 1.0 if (side == fs or at < 0.05) else back_k
        if at > 0.05 and side == fs:
            k = 1.0 + 0.15 * at
        P.append((xc + u * k * D + sh * v * D, ny0 + v * D))
    d = 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in P) + ' Z'
    o = ['<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
        d, tint, INK, f(max(0.02 * D, 3)))]
    # nostril wing on the back side + nostril
    bx = xc + sh * 0.27 * D - fs * 0.06 * D * (1 - 0.3 * at)
    by = ny0 + 0.27 * D
    o.append('<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        pts([(bx - fs * 0.005 * D, by - 0.045 * D)]), pts([(bx - fs * 0.04 * D, by + 0.0 * D)]),
        pts([(bx + fs * 0.01 * D, by + 0.045 * D)]), INK, f(max(0.016 * D, 2.5))))
    o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>' % (
        f(xc + sh * 0.31 * D + fs * 0.01 * D), f(ny0 + 0.305 * D), f(0.022 * D), f(0.010 * D), MOUTH_DARK))
    return ''.join(o)


def nose_button(xc, ny0, D, t, fs, skin, OL):
    """Dot's nose: small, upturned, rounded button -- 0.13 D wide, nostrils visible."""
    at = abs(t)
    cxn = xc + fs * 0.03 * at * D
    cyn = ny0 + 0.21 * D
    w, h = 0.135 * D, 0.10 * D
    tipx = cxn + fs * 0.045 * at * D
    d = 'M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z' % (
        f(cxn - w / 2), f(cyn + h * 0.15),
        f(cxn - w / 2), f(cyn - h * 0.5), f(tipx - w * 0.1), f(cyn - h * 0.62), f(tipx + fs * 0.0), f(cyn - h * 0.55),
        f(cxn + w / 2 + 0.01 * D), f(cyn - h * 0.45), f(cxn + w / 2), f(cyn + h * 0.45), f(cxn), f(cyn + h * 0.42),
        f(cxn - w * 0.3), f(cyn + h * 0.45), f(cxn - w / 2), f(cyn + h * 0.45), f(cxn - w / 2), f(cyn + h * 0.15))
    o = ['<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
        d, shade(skin, -0.06), INK, f(max(0.02 * D, 3)))]
    for k in (-1, 1):
        nxp = cxn + k * w * 0.20 + fs * 0.012 * D * at
        if at > 0.5 and k == fs:
            nxp = cxn + k * w * 0.16 + fs * 0.012 * D
        o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>' % (
            f(nxp), f(cyn + h * 0.2), f(0.017 * D * (0.75 if (at > 0.5 and k == fs) else 1)), f(0.012 * D), MOUTH_DARK))
    return ''.join(o)

# =====================================================================
#  CHARACTER SPECS
# =====================================================================
# LOU -- night sweeper.  Flat-top bowl eyes 0.30 D tall, 55 % lidded, lid lines level = one-line visor,
# no brows, bald with a 3-strand comb-over whose tips spring off the far side, jug ears,
# toothpick, flat stubble on the lower third, teal bib overalls, hunched.
LOU_H = dict(skin='#E0A887', jaw='#B99583', jaw_frac=0.33, jaw_sag=0.035,
             eye_shape='bowl', eye_w=0.34, eye_h=0.30, eye_c=0.44, eye_gap=0.11, lid_rest=0.55, lid_shade=0.0,
             pupil=0.11, rim=0.022, lid_w=0.036, lid_ext=0.03, park=0.9,
             bags=((0.035, 0.62, 0.85),),
             outline=0.022, ear_rx=0.105, ear_ry=0.15, ear_prot=0.14, ear_dy=0.02, ear_lobe_tone='#C9846A',
             hair='barcode', hair_color='#7C756F', rim_mode='below_lid',
             nose='drip', nose_top=0.37, nose_tint='#D99D80', mouth_y=0.815, mouth_dx=0.01, toothpick=True)

# DOT -- night caretaker who works the dummy ropes.  Rounded-square "TV" eyes 0.34 D, 10 % lidded,
# double coffee bags, short thick straight brows parked high, short tight curls, mint pen above the ear,
# small upturned button nose, cream cardigan, mint key strap, small, leans back.
DOT_H = dict(skin='#8A5A43', jaw='#82543F', jaw_frac=0.25, jaw_sag=0.03,
             eye_shape='rsq', eye_w=0.33, eye_h=0.34, eye_c=0.47, eye_gap=0.105, lid_rest=0.10, lid_shade=0.14,
             pupil=0.115, rim=0.022, lid_w=0.032, lid_ext=0.012, park=0.0,
             bags=((0.028, 0.50, 0.95), (0.064, 0.36, 0.8)),
             bag_centred=True,
             brow='#22130F', brow_len=0.19, brow_th=0.06, brow_gap=0.045,
             outline=0.022, ear_rx=0.07, ear_ry=0.095, ear_prot=0.055, ear_dy=0.03,
             hair='curls', hair_color='#2A1A16', hair_hi='#6B4A3C', pen=True,
             nose='button', nose_top=0.44, mouth_y=0.82, creases_mouth=True)

# cameo: the caretaker gramps peeking through the door -- generic 70 %-lidded eye at 0.27 D
GRAMPS_H = dict(skin='#B98260', jaw='#A08371', jaw_frac=0.30, jaw_sag=0.03,
                eye_shape='ellipse', eye_w=0.27, eye_h=0.27, eye_c=0.45, eye_gap=0.10, lid_rest=0.70, lid_shade=0.12,
                pupil=0.10, rim=0.02, lid_w=0.03, lid_ext=0.01,
                bags=((0.03, 0.6, 0.8),), outline=0.024, ear_rx=0.075, ear_ry=0.10, ear_prot=0.075,
                tufts='#BDB6AA', creases=True, nose='hook', nose_top=0.56, mouth_y=0.80)

# ---------------------------------------------------------------- Lou's six faces
LOU_E = {
    'neutral':   dict(lid=(0.55, 0.55), gaze=(0.25, 1.0), mouth='flat', mouth_turn=0.006, toothpick=-24, strands='combed'),
    'surprised': dict(lid=(0.0, 0.0), eye_scale=1.10, eye_dy=-0.02, gaze=(0.0, 0.0), pupil_scale=0.95, fold=True,
                      mouth='gasp', mouth_w=0.30, mouth_h=0.20, toothpick='fall', strands='stand', emanata=(-1, 1)),
    'angry':     dict(lid=(0.50, 0.50), lid_tilt=(24, 24), low=(0.12, 0.12), low_curve=0.03, gaze=(0.0, 1.0), frown=True,
                      mouth='teeth', mouth_w=0.34, mouth_h=0.11, toothpick=58, strands='bristle', vein=True),
    'smug':      dict(lid=(0.68, 0.68), lid_tilt=(-6, -6), low=(0.10, 0.10), low_curve=0.05, gaze=(-1.0, 0.6), pin=0.15,
                      mouth='smirk', mouth_w=0.22, toothpick=32, strands='smooth'),
    'panic':     dict(lid=(0.14, 0.14), lid_tilt=(-22, -22), gaze=(0.0, -0.2), pupil_scale=0.92,
                      ghosts=((-0.035, 0, 0.3), (0.035, 0, 0.3)), mouth='wobble', mouth_w=0.34, toothpick=-10, tp_shake=True,
                      strands='flail', sweat=1),
    'sideeye':   dict(lid=(0.64, 0.64), gaze=(1.0, 0.55), pin=0.3, mouth='flat', mouth_w=0.15, mouth_turn=0.014,
                      mouth_dx=-0.03, toothpick=-38, strands='wilt', gloom=True),
}
DOT_E = {
    'neutral':  dict(lid=(0.10, 0.10), gaze=(-0.3, 0.1), mouth='flat', mouth_w=0.21, mouth_turn=0.008, brow_up=0.045),
    'caught':   dict(lid=(0.04, 0.04), gaze=(-1, 0), pin=0.1, mouth='eek', mouth_w=0.36, mouth_h=0.13, brow_up=0.075,
                     brow_tilt=(-10, -10), sweat=1),
}
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


# =====================================================================
#  STICK-BODY RIG  (ink-cased coloured sticks + ONE costume surface on the torso)
# =====================================================================
TEAL = '#3E8378'
TEAL_D = '#2F675E'
SHIRT = '#A99A8B'
CARDI = '#EADFC8'
CARDI_D = '#D3C5A8'
PLUM = '#3B2430'
KEY_MINT = '#6CC3A2'

LOU_F = dict(name='Lou', skin=LOU_H['skin'], chin=LOU_H['jaw'], arm=SHIRT, spine=SHIRT, leg=TEAL_D,
             shoe='#3A2A22', hand=LOU_H['skin'], cuff=None, torso='bib', hip='rag',
             neck_vis=0.12, yoke=0.07, spine_len=1.0, upper=0.68, fore=0.70, thigh=0.74, shin=0.71,
             shoe_h=0.10, shoe_L=0.32, mit_L=0.20, mit_W=0.13, sh=(0.28, 0.25), neck_w=0.18)
DOT_F = dict(name='Dot', skin=DOT_H['skin'], chin=DOT_H['jaw'], arm=CARDI, spine=CARDI, leg=PLUM,
             shoe='#17110F', hand=DOT_H['skin'], cuff=CARDI_D, torso='cardigan', hip='keys',
             neck_vis=0.12, yoke=0.07, spine_len=0.92, upper=0.62, fore=0.64, thigh=0.64, shin=0.62,
             shoe_h=0.10, shoe_L=0.27, mit_L=0.19, mit_W=0.13, sh=(0.27, 0.24), neck_w=0.17)


def spine_point(sp, s):
    """point + unit tangent at arc length s along polyline sp (extrapolates past the end)."""
    acc = 0.0
    for i in range(1, len(sp)):
        seg = math.hypot(sp[i][0] - sp[i - 1][0], sp[i][1] - sp[i - 1][1])
        if acc + seg >= s or i == len(sp) - 1:
            tng = norm((sp[i][0] - sp[i - 1][0], sp[i][1] - sp[i - 1][1]))
            k = s - acc
            return (sp[i - 1][0] + tng[0] * k, sp[i - 1][1] + tng[1] * k), tng
        acc += seg
    return sp[-1], (0, 1)


def poly_len(sp):
    return sum(math.hypot(sp[i][0] - sp[i - 1][0], sp[i][1] - sp[i - 1][1]) for i in range(1, len(sp)))


def panel_poly(sp, s0, s1, w0, w1, shift=0.0, n=14, flare=0.0):
    L, R_ = [], []
    for j in range(n + 1):
        u = j / n
        s = s0 + (s1 - s0) * u
        p, tg = spine_point(sp, s)
        nrm = (-tg[1], tg[0])
        w = w0 + (w1 - w0) * u + flare * (u ** 3)
        c = add(p, nrm, shift)
        L.append(add(c, nrm, w))
        R_.append(add(c, nrm, -w))
    return L, R_


def figure(F, P, rim=None):
    """Build one stick body under a round head.  Returns (layers, J)."""
    D = P['D']
    R = D / 2.0
    t = P.get('turn', 0.0)
    fs = (t > 0) - (t < 0)
    at = abs(t)
    hx, hy = P['head']
    alpha = math.radians(P.get('neck_ang', 10 * fs))
    nvis = P.get('neck_vis', F['neck_vis'])
    nx0 = hx - fs * 0.10 * min(at, 1.0) * D + P.get('neck_dx', 0.0) * D
    yb = hy + math.sqrt(max(R * R - (nx0 - hx) ** 2, 0))
    dn = (-math.sin(alpha), math.cos(alpha))
    Q = (nx0, yb)
    T = add(Q, dn, -0.07 * D)
    B = add(Q, dn, nvis * D)
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
    cas0, cas1 = max(0.018 * D, 3.5), max(0.015 * D, 3.5)
    tot0, tot1 = max(0.071 * D, 12.5), max(0.050 * D, 12.0)
    sp0, sp1 = max(0.08 * D, 14.0), max(0.06 * D, 12.0)
    tag = F['name']
    Ly['spine'] = sticks([(spine, F['spine'], sp0 - 2 * cas0, sp1 - 2 * cas0, cas0, cas0)], rim=rim, tag=tag + ':spine')
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
        J[side + '_fa'] = fa
        J[side + '_tip'] = add(wr, (math.cos(fa), math.sin(fa)), F['mit_L'] * D * 0.88) if mode != 'grip' else wr
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
    # ---- neck stub
    nw = F['neck_w'] * D
    nperp = (dn[1], -dn[0])
    Bx = add(B, dn, 0.06 * D)
    poly = [add(T, nperp, -nw / 2), add(T, nperp, nw / 2), add(Bx, nperp, nw / 2), add(Bx, nperp, -nw / 2)]
    Q2 = add(Q, dn, 0.035 * D)
    shadow = [add(T, nperp, -nw / 2), add(T, nperp, nw / 2), add(Q2, nperp, nw / 2), add(Q2, nperp, -nw / 2)]
    Ly['neck'] = ('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
        pts(poly), F['skin'], INK, f(max(0.018 * D, 3.5))) + '<polygon points="%s" fill="%s"/>' % (pts(shadow), shade(F['skin'], 0.14)))
    J['dn'] = dn
    # ---- torso: shoulder yoke + ONE costume surface (Lou: bib overalls, Dot: cardigan)
    ex = perp_s
    ey_ = ub

    def Tf(x, y):
        return (B[0] + (ex[0] * x + ey_[0] * y) * D, B[1] + (ex[1] * x + ey_[1] * y) * D)
    olw = max(0.018 * D, 3.0)
    sp_full = spine_curve
    Lsp = poly_len(sp_full)
    yk = P.get('yoke', F['yoke'])
    back, yoke_l, panel, front = [], [], [], []
    shift = 0.02 * D * (1 if fs >= 0 else -1) * min(at, 1.0)
    if F['torso'] == 'bib':
        sc = F['spine']
        back.append('<path d="M%s Q%s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([Tf(-0.14, 0.05)]), pts([Tf(-0.11, -0.07)]), pts([Tf(0, -0.08)]), pts([Tf(0.11, -0.07)]),
            pts([Tf(0.14, 0.05)]), shade(sc, 0.22), INK, f(olw)))
        # shirt yoke spanning the shoulders
        sL = add(SL, ex, -0.01 * D)
        sR = add(SR, ex, 0.01 * D)
        yp = [sL, Tf(-0.10, -0.03), Tf(0.10, -0.03), sR, add(sR, ey_, 0.13 * D), Tf(0, yk + 0.30), add(sL, ey_, 0.13 * D)]
        yoke_l.append('<path d="M%s Q%s %s L%s Q%s %s Q%s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([yp[0]]), pts([add(yp[0], ey_, -0.04 * D)]), pts([yp[1]]), pts([yp[2]]), pts([add(yp[3], ey_, -0.04 * D)]), pts([yp[3]]),
            pts([add(yp[3], ey_, 0.10 * D)]), pts([yp[5]]), pts([add(yp[0], ey_, 0.10 * D)]), pts([yp[0]]), sc, INK, f(olw)))
        s0, s1 = 0.30 * Lsp, Lsp + 0.07 * D
        Lp, Rp = panel_poly(sp_full, s0, s1, 0.15 * D * (1 - 0.08 * at), 0.185 * D * (1 - 0.08 * at), shift)
        bib = Lp + Rp[::-1]
        panel.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (pts(bib), TEAL, INK, f(olw)))
        # pocket + stitch + waist seam
        pc, tg = spine_point(sp_full, s0 + 0.16 * D)
        nrm = (-tg[1], tg[0])
        pc = add(pc, nrm, shift)
        pk = [add(add(pc, nrm, -0.075 * D), tg, -0.05 * D), add(add(pc, nrm, 0.075 * D), tg, -0.05 * D),
              add(add(pc, nrm, 0.07 * D), tg, 0.08 * D), add(add(pc, nrm, -0.07 * D), tg, 0.08 * D)]
        panel.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (pts(pk), TEAL_D, INK, f(olw * 0.8)))
        wc, tg2 = spine_point(sp_full, Lsp - 0.06 * D)
        n2 = (-tg2[1], tg2[0])
        wc = add(wc, n2, shift)
        panel.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>' % (
            *map(f, add(wc, n2, -0.18 * D)), *map(f, add(wc, n2, 0.18 * D)), INK, f(olw * 0.8)))
        # straps from the bib corners over the shoulders, brass buttons
        for corner, S, sg in ((Lp[0], SL, -1), (Rp[0], SR, 1)):
            top_pt = add(add(S, ex, -sg * 0.07 * D), ey_, -0.005 * D)
            for col, wd in ((INK, 0.075 * D), (TEAL, 0.075 * D - 2 * olw)):
                panel.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                    f(corner[0] - sg * 0.035 * D), f(corner[1]), f(top_pt[0]), f(top_pt[1]), col, f(wd)))
            panel.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                f(corner[0] - sg * 0.035 * D), f(corner[1] + 0.025 * D), f(0.03 * D), BRASS, INK, f(olw * 0.7)))
        # shirt collar points
        for sg in (-1, 1):
            front.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                pts([Tf(sg * 0.012, -0.03), Tf(sg * 0.105, -0.045), Tf(sg * 0.07, 0.10)]), shade(sc, -0.12), INK, f(olw)))
    elif F['torso'] == 'cardigan':
        back.append('<path d="M%s Q%s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([Tf(-0.14, 0.05)]), pts([Tf(-0.11, -0.07)]), pts([Tf(0, -0.08)]), pts([Tf(0.11, -0.07)]),
            pts([Tf(0.14, 0.05)]), CARDI_D, INK, f(olw)))
        s0, s1 = 0.0, Lsp + 0.22 * D
        Lp, Rp = panel_poly(sp_full, s0, s1, 0.165 * D * (1 - 0.06 * at), 0.205 * D * (1 - 0.06 * at), shift, flare=0.02 * D)
        sL = add(SL, ex, -0.015 * D)
        sR = add(SR, ex, 0.015 * D)
        body = [sL, Tf(-0.09, -0.04), Tf(0.09, -0.04), sR] + Rp[1:] + Lp[::-1][:-1]
        panel.append('<path d="M%s Q%s %s L%s Q%s %s L%s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([sL]), pts([add(sL, ey_, -0.05 * D)]), pts([Tf(-0.09, -0.04)]), pts([Tf(0.09, -0.04)]),
            pts([add(sR, ey_, -0.05 * D)]), pts([sR]), ' L'.join(pts([p]) for p in Rp[1:] + Lp[::-1][:-1]), CARDI, INK, f(olw)))
        # ribbed hem band
        hb_L, hb_R = panel_poly(sp_full, s1 - 0.07 * D, s1, 0.20 * D * (1 - 0.06 * at), 0.205 * D * (1 - 0.06 * at), shift, n=4,
                                flare=0.02 * D)
        panel.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts(hb_L + hb_R[::-1]), CARDI_D, INK, f(olw * 0.8)))
        # V opening with the blouse
        vp, vt = spine_point(sp_full, 0.42 * Lsp)
        vn = (-vt[1], vt[0])
        vp = add(vp, vn, shift)
        vee = [Tf(-0.085, -0.035), Tf(0.085, -0.035), vp]
        panel.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (pts(vee), '#F7F1E6', INK, f(olw)))
        # front edge + buttons + pockets
        hp_, ht = spine_point(sp_full, s1)
        hn_ = (-ht[1], ht[0])
        hp_ = add(hp_, hn_, shift)
        panel.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"/>' % (
            f(vp[0]), f(vp[1]), f(hp_[0]), f(hp_[1]), INK, f(olw * 0.8)))
        for kk in range(3):
            bp, bt_ = spine_point(sp_full, 0.42 * Lsp + (0.16 + 0.17 * kk) * D)
            bn = (-bt_[1], bt_[0])
            bp = add(bp, bn, shift + 0.03 * D)
            panel.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                f(bp[0]), f(bp[1]), f(0.022 * D), '#B98F5A', INK, f(olw * 0.6)))
        for sg in (-1, 1):
            pc, tg = spine_point(sp_full, Lsp - 0.02 * D)
            nrm = (-tg[1], tg[0])
            pc = add(pc, nrm, shift + sg * 0.11 * D)
            pk = [add(add(pc, nrm, -0.06 * D), tg, -0.04 * D), add(add(pc, nrm, 0.06 * D), tg, -0.04 * D),
                  add(add(pc, nrm, 0.06 * D), tg, 0.09 * D), add(add(pc, nrm, -0.06 * D), tg, 0.09 * D)]
            panel.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                pts(pk), CARDI_D, INK, f(olw * 0.7)))
        # blouse collar points
        for sg in (-1, 1):
            front.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
                pts([Tf(sg * 0.01, -0.03), Tf(sg * 0.10, -0.05), Tf(sg * 0.075, 0.095)]), '#FFFDF6', INK, f(olw)))
        J['cardi_hem'] = hp_
    Ly['collar_back'] = ''.join(back)
    Ly['yoke'] = ''.join(yoke_l)
    Ly['panel'] = ''.join(panel)
    Ly['collar'] = ''.join(front)
    bsx = -fs if fs else -1
    if F['hip'] == 'rag':
        Ly['hip'] = rag(add(hip, (0, 0.04 * D)), side=P.get('rag_side', bsx), swing=P.get('swing', 0.0) * D, s=D / 270.0)
    elif F['hip'] == 'keys':
        Ly['hip'] = keys(add(hip, (P.get('keys_side', 1) * 0.17 * D, 0.02 * D)), D, P.get('keys_swing', 12))
    REG['figs'].append(J)
    return Ly, J


def figure_fit(F, P, rim=None, tol=0.5):
    for _ in range(12):
        Ly, J = figure(F, P, rim=rim)
        short = max(J.get('L_legshort', 0), J.get('R_legshort', 0))
        if short <= tol:
            return Ly, J
        REG['figs'].pop()
        REG['limbs'][:] = [x for x in REG['limbs'] if not x[0].startswith(F['name'] + ':')]
        P['head'] = (P['head'][0], P['head'][1] + short * 0.9)
    return figure(F, P, rim=rim)


def rag(hip, side=1, swing=0.0, s=1.0):
    x0, y0 = hip
    sx = side * s
    p0 = (x0 + sx * 2, y0 - 10 * s)
    p1 = (x0 + sx * 40, y0 - 6 * s)
    p2 = (x0 + sx * 50 + swing, y0 + 84 * s)
    p3 = (x0 + sx * 10 + swing * 0.7, y0 + 78 * s)
    m = ((p2[0] + p3[0]) / 2 + sx * 2, (p2[1] + p3[1]) / 2 + 12 * s)
    d = 'M%s L%s Q%s %s Q%s %s Q%s %s Z' % (
        pts([p0]), pts([p1]), pts([((p1[0] + p2[0]) / 2 + sx * 6, (p1[1] + p2[1]) / 2)]), pts([p2]),
        pts([m]), pts([p3]), pts([((p0[0] + p3[0]) / 2 - sx * 4, (p0[1] + p3[1]) / 2)]), pts([p0]))
    folds = '<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.55"/>' % (
        pts([(x0 + sx * 18, y0 + 2 * s)]), pts([(x0 + sx * 20 + swing * .4, y0 + 34 * s)]),
        pts([(x0 + sx * 24 + swing * 0.8, y0 + 70 * s)]), INK, f(3 * s))
    stripe = '<path d="M%s L%s" fill="none" stroke="#B0303A" stroke-width="%s" opacity="0.8"/>' % (
        pts([(x0 + sx * 6 + swing * 0.5, y0 + 56 * s)]), pts([(x0 + sx * 46 + swing * 0.9, y0 + 62 * s)]), f(5 * s))
    return '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>%s%s' % (d, '#EFE6D6', INK, f(4.5 * s), stripe, folds)


def keys(p, D, swing=12):
    """mint strap clipped at the hip + brass ring with three keys."""
    x, y = p
    r = 0.05 * D
    o = ['<g transform="rotate(%s %s %s)">' % (f(swing), f(x), f(y))]
    sl = 0.16 * D
    for col, wd in ((INK, 0.075 * D), (KEY_MINT, 0.075 * D - 2 * max(0.016 * D, 3))):
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(x), f(y), f(x), f(y + sl), col, f(wd)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        f(x - 0.045 * D), f(y - 0.03 * D), f(0.09 * D), f(0.05 * D), f(0.012 * D), '#C9D3CC', INK, f(0.014 * D)))
    cy = y + sl + r
    for a in (-38, 0, 34):
        kx = x + math.sin(math.radians(a)) * r * 2.3
        ky = cy + math.cos(math.radians(a)) * r * 2.3
        x0_, y0_ = x + math.sin(math.radians(a)) * r, cy + math.cos(math.radians(a)) * r
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(x0_), f(y0_), f(kx), f(ky), INK, f(0.045 * D)))
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
            f(x0_), f(y0_), f(kx), f(ky), '#D9B25E', f(0.022 * D)))
    o.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (f(x), f(cy), f(r), INK, f(0.042 * D)))
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
#  SCENE 1080x1920  --  "caught": Lou blocks the wall dummy without looking at it,
#  his flat stare already parked on Dot, who freezes mid-pull with the next dummy dropping.
# =====================================================================
def coil(c, D, a=-20):
    """rope coil hanging from a fist"""
    o = ['<g transform="rotate(%s %s %s)">' % (f(a), f(c[0]), f(c[1]))]
    for k, (dx, rx, ry) in enumerate(((-0.02, 0.15, 0.22), (0.0, 0.14, 0.21), (0.02, 0.15, 0.22))):
        cx, cy = c[0] + dx * D, c[1] + 0.20 * D
        o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
            f(cx), f(cy), f(rx * D), f(ry * D), INK, f(0.06 * D)))
        o.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (
            f(cx), f(cy), f(rx * D), f(ry * D), ROPE, f(0.03 * D)))
    o.append('</g>')
    return ''.join(o)


def build_scene(sil=False):
    REG['limbs'].clear()
    REG['figs'].clear()
    CEIL, FLOOR, FL = 230, 1318, 1545
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">', defs_common()]
    if sil:
        S.append('<style>.fig *{fill:#000 !important;stroke:#000 !important;opacity:1 !important}</style>')
    S.append('<rect width="1080" height="1920" fill="%s"/>' % COFFEE)
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#6E1F2B"/>' % (CEIL, FLOOR - CEIL))
    for k, x in enumerate(range(0, 1080, 96)):
        if k % 2:
            S.append('<rect x="%d" y="%d" width="96" height="%d" fill="#641B27"/>' % (x, CEIL, FLOOR - CEIL))
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#4C1420" stroke-width="3"/>' % (x, CEIL, x, FLOOR))
    S.append('<rect x="0" y="1150" width="1080" height="14" fill="#4C1420"/>')
    S.append('<rect x="0" y="%d" width="1080" height="34" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (FLOOR - 34, INK))
    wx, wy, ww, wh = 404, 262, 116, 136
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#7FAF9A"/>' % (wx, wy, ww, wh))
    for k in (1, 2):
        S.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#3A2620" stroke-width="6"/>' % (f(wx + ww * k / 3), wy, f(wx + ww * k / 3), wy + wh))
        S.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="#3A2620" stroke-width="6"/>' % (wx, f(wy + wh * k / 3), wx + ww, f(wy + wh * k / 3)))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#3A2620" stroke-width="14"/>' % (wx, wy, ww, wh))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="4"/>' % (wx - 7, wy - 7, ww + 14, wh + 14, INK))
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#4A2E24"/>' % (FLOOR, 1920 - FLOOR))
    for y in (1352, 1394, 1446, 1508, 1575, 1690, 1830):
        S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#3A231C" stroke-width="3"/>' % (y, y))
    S.append('<rect x="0" y="1575" width="1080" height="345" fill="#3A241C"/>')
    for y in (1690, 1830):
        S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#2E1C16" stroke-width="3"/>' % (y, y))
    S.append('<polygon points="%s" fill="%s" opacity="0.40"/>' % (pts([(250, FLOOR + 4), (520, FLOOR + 4), (640, 1575), (190, 1575)]), MINT))
    S.append('<circle cx="905" cy="690" r="420" fill="url(#lamp)"/>')
    S.append('<ellipse cx="300" cy="800" rx="470" ry="660" fill="url(#pool2)"/>')
    S.append('<ellipse cx="800" cy="1340" rx="250" ry="330" fill="url(#pool2)"/>')
    S.append('<ellipse cx="380" cy="1290" rx="230" ry="200" fill="url(#pool)"/>')
    # ---- cameo witness: gramps peeking past the sliding door (generic 70 %-lidded eye, 0.27 D)
    S.append('<rect x="-10" y="660" width="128" height="%d" fill="#3A2620" stroke="%s" stroke-width="6"/>' % (FLOOR - 34 - 660, INK))
    S.append('<rect x="28" y="680" width="82" height="%d" fill="#100A08"/>' % (FLOOR - 34 - 700))
    gh, gi = head('gramps', 52, 1010, 190, GRAMPS_H,
                  dict(lid=(0.70, 0.70), gaze=(1, 0.2), pin=0.2, mouth='flat', mouth_dx=0.06, mouth_w=0.12,
                       hide_ear=-1, eyes=(1,)), turn=0.55)
    S.append(gh)
    S.append('<rect x="-10" y="660" width="40" height="%d" fill="#4A3026" stroke="%s" stroke-width="6"/>' % (FLOOR - 34 - 660, INK))
    for yy in range(720, FLOOR - 40, 120):
        S.append('<line x1="-10" y1="%d" x2="28" y2="%d" stroke="%s" stroke-width="4"/>' % (yy, yy, INK))

    # ---- dummy 1: wall-post dummy (faceless) above-left; its peg arm just struck the dustpan
    S.append('<rect x="-6" y="%d" width="44" height="%d" fill="#5A3A28" stroke="%s" stroke-width="6"/>' % (CEIL - 6, 640 - CEIL, INK))
    d1x, d1top = 22, 240
    S.append(dummy_body(d1x, d1top, uid='d1'))
    pv = (d1x + 76, d1top + 64)
    L_arm = 124
    a_rest = 0.0
    ring = (pv[0] + L_arm * math.cos(math.radians(a_rest)) + 4, pv[1] + L_arm * math.sin(math.radians(a_rest)))
    S.append('<rect x="%s" y="%s" width="16" height="44" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (f(ring[0] + 20), f(ring[1] - 22), INK))

    # ---- dummy 2: released from its ceiling latch right of the window, dropping (the next note)
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

    # ---- paper lantern
    lx, ly = 962, 330
    S.append('<ellipse cx="%d" cy="%d" rx="56" ry="66" fill="%s" stroke="%s" stroke-width="6"/>' % (lx, ly, AMBER, INK))
    for k in (-32, 0, 32):
        S.append('<path d="M%d,%d Q%d,%d %d,%d" fill="none" stroke="#C9963E" stroke-width="3"/>' % (lx - 54, ly + k, lx, ly + k + 10, lx + 54, ly + k))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly - 72, INK))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly + 60, INK))

    # ---- shoe cabinet with five paper cups (the fifth steaming = Dot's coffee)
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

    # ================================================================ geometry of both heads first (gaze targets)
    D = 280
    hd = (420, 650)
    Dd = 246
    dhead = (858, 820)
    pB = (812, 250)
    # ---------------------------------------------------------------- DOT
    dturn = -1.0
    dpose = dict(D=Dd, head=dhead, turn=dturn, neck_ang=8, neck_dx=-0.02, spine=-17, bow=0.05, sh=(0.29, 0.22),
                 arms=dict(L=dict(ang=-30, straight=True, mode='grip', thumb=1),
                           R=dict(ang=-136, straight=True, mode='grip', thumb=-1)),
                 legs=dict(L=dict(sole=(736, 1540), rot=-26, bend=-1), R=dict(sole=(846, 1540), bend=-1, rot=-6)),
                 toe_rim=AMBER, keys_side=1, keys_swing=26)
    DL, DJ = figure_fit(DOT_F, dpose, rim=(AMBER, 3.5, (0.8, -0.6)))
    up_f, lo_f = DJ['L_wr'], DJ['R_wr']
    dpose['arms']['L']['pole'] = ang(pB, up_f)
    dpose['arms']['R']['pole'] = ang(up_f, lo_f)
    REG['figs'].pop()
    DL, DJ = figure(DOT_F, dpose, rim=(AMBER, 3.5, (0.8, -0.6)))
    dhead = DJ['head']
    # ---------------------------------------------------------------- LOU
    turn = 1.0
    Htot = 3.7 * D
    bfloor = (536, FL)
    base, tip = broom_line(D, Htot, bfloor, -17)
    pan_ang = -62
    lpose = dict(D=D, head=hd, turn=turn, neck_ang=12, spine=-4, bow=-0.10, spine_len=0.97,
                 arms=dict(L=dict(ang=-30, straight=True, mode='grip', thumb=1, pole=math.radians(pan_ang)),
                           R=dict(hand=on_line(base, tip, 1150), bend=-1, thumb=1, pole=ang(base, tip))),
                 legs=dict(L=dict(sole=(296, FL), bend=1), R=dict(sole=(446, FL), bend=1)),
                 toe_rim=AMBER, swing=0.05)
    L, J = figure_fit(LOU_F, lpose, rim=(AMBER, 3.5, (0.7, -0.7)))
    hd = lpose['head']
    grip = J['L_wr']
    pan_c = dustpan_center(grip, pan_ang, D)
    # eye targets: each locks on the other's eyes
    lou_eyes = (hd[0] + 0.12 * D, hd[1] - 0.06 * D)
    dot_eyes = (dhead[0] - 0.12 * Dd, dhead[1] - 0.05 * Dd)

    # ---------------------------------------------------------------- draw DOT
    S.append(cast_shadow(800, 1546, 130, 15, 0.45))
    S.append(rope([latch, (latch[0] + 30, 246), pB]))
    tail_end = (lo_f[0] - 56, lo_f[1] + 190)
    g = ['<g class="fig">']
    g.append(DL['L_leg'] + DL['R_leg'])
    g.append(DL['L_arm'] + DL['L_pad'])
    g.append(rope([pB, up_f, lo_f]))
    g.append(rope_path('M%s Q%s %s' % (pts([lo_f]), pts([(lo_f[0] + 10, lo_f[1] + 120)]), pts([tail_end]))))
    g.append('<path d="M%s l-14,44 l30,0 Z" fill="#8E2A35" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (pts([(tail_end[0] + 2, tail_end[1] - 4)]), INK))
    g.append(DL['spine'] + DL['collar_back'] + DL['neck'] + DL['panel'] + DL['hip'] + DL['collar'])
    dh, dinfo = head('dot', dhead[0], dhead[1], Dd, DOT_H, dict(DOT_E['caught'], sweat=1, emanata=(1,)), turn=dturn, look=lou_eyes)
    g.append(dh)
    g.append(DL['R_arm'] + DL['R_pad'])
    g.append(rope([along(up_f, lo_f, -6), along(up_f, lo_f, 70)]))
    g.append(rope([along(lo_f, up_f, 40), along(lo_f, tail_end, 30)]))
    g.append(DL['L_thumb'] + DL['R_thumb'])
    g.append('</g>')
    S.append(''.join(g))

    # ---------------------------------------------------------------- draw LOU
    S.append(cast_shadow(395, FL + 4, 175, 16, 0.42))
    g = ['<g class="fig">']
    g.append(L['R_leg'] + L['R_arm'] + L['R_pad'])
    g.append(L['spine'])
    fan, handle = broom(base, tip, D, floor=FL, skew=-8)
    g.append(fan + handle)
    g.append(L['L_leg'])
    g.append(L['collar_back'] + L['neck'] + L['yoke'] + L['panel'] + L['hip'] + L['collar'])
    g.append(L['L_arm'])
    lh, linfo = head('lou', hd[0], hd[1], D, LOU_H, dict(LOU_E['sideeye'], gloom=False, pin=0.3, lid=(0.62, 0.62), strands='combed'),
                     turn=turn, look=dot_eyes)
    g.append(lh)
    g.append(L['L_pad'])
    g.append(dustpan(grip, pan_ang, D))
    g.append(L['L_thumb'] + L['R_thumb'])
    g.append('</g>')
    S.append(''.join(g))
    S.append(puffs(bfloor[0] + 96, FL - 40, 0.9, 1))
    # ---- the strike: peg arm swung down onto the dustpan, already bouncing back to its ring
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
    # ---- ceiling band, pulleys, lantern cord
    S.append('<rect x="0" y="0" width="1080" height="%d" fill="%s"/>' % (CEIL, COFFEE))
    S.append('<rect x="0" y="%d" width="1080" height="10" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (CEIL - 6, INK))
    S.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="#5A3A28" stroke-width="4"/>' % (lx, lx, ly - 72))
    S.append('<rect x="%s" y="%s" width="40" height="16" fill="%s" stroke="%s" stroke-width="4"/>' % (f(latch[0] - 20), f(latch[1] - 8), BRASS, INK))
    S.append(pulley(*pB))
    S.append('<rect width="1080" height="1920" fill="url(#vig)"/>')
    S.append('</svg>')
    return '\n'.join(S)


# =====================================================================
#  FACES 1080x1080 -- Lou's head, 3x2: neutral, surprised, angry, smug, panic, exasperated side-eye
# =====================================================================
def bust(cx, cy, D, turn):
    """neck stub + shirt collar + bib top under a sheet head"""
    R = D / 2
    fs = (turn > 0) - (turn < 0)
    nx = cx - fs * 0.08 * abs(turn) * D
    yb = cy + math.sqrt(max(R * R - (nx - cx) ** 2, 0))
    o = []
    lw = 0.018 * D
    sh_y = yb + 0.20 * D
    yoke = 'M%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s L%s,%s L%s,%s Z' % (
        f(nx - 0.62 * D), f(sh_y + 0.30 * D), f(nx - 0.60 * D), f(sh_y), f(nx - 0.12 * D), f(yb + 0.06 * D),
        f(nx + 0.12 * D), f(yb + 0.06 * D), f(nx + 0.60 * D), f(sh_y), f(nx + 0.62 * D), f(sh_y + 0.30 * D),
        f(nx + 0.62 * D), f(sh_y + 0.34 * D), f(nx - 0.62 * D), f(sh_y + 0.34 * D))
    o.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (yoke, SHIRT, INK, f(lw)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        f(nx - 0.09 * D), f(yb - 0.08 * D), f(0.18 * D), f(0.20 * D), LOU_H['skin'], INK, f(lw)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>' % (
        f(nx - 0.09 * D + lw / 2), f(yb - 0.08 * D), f(0.18 * D - lw), f(0.07 * D), shade(LOU_H['skin'], 0.14)))
    bib = [(nx - 0.30 * D, sh_y + 0.16 * D), (nx + 0.30 * D, sh_y + 0.16 * D), (nx + 0.32 * D, sh_y + 0.34 * D), (nx - 0.32 * D, sh_y + 0.34 * D)]
    o.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (pts(bib), TEAL, INK, f(lw)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        f(nx - 0.12 * D), f(sh_y + 0.22 * D), f(0.24 * D), f(0.12 * D), TEAL_D, INK, f(lw * 0.8)))
    for sg in (-1, 1):
        a = (nx + sg * 0.24 * D, sh_y + 0.17 * D)
        b = (nx + sg * 0.45 * D, sh_y - 0.02 * D)
        for col, wd in ((INK, 0.075 * D), (TEAL, 0.075 * D - 2 * lw)):
            o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(a[0]), f(a[1]), f(b[0]), f(b[1]), col, f(wd)))
        o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
            f(a[0]), f(a[1] + 0.02 * D), f(0.03 * D), BRASS, INK, f(lw * 0.7)))
        o.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
            pts([(nx + sg * 0.01 * D, yb + 0.07 * D), (nx + sg * 0.15 * D, yb + 0.04 * D), (nx + sg * 0.10 * D, yb + 0.20 * D)]),
            shade(SHIRT, -0.12), INK, f(lw)))
    return ''.join(o)


def build_faces():
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">']
    S.append('<rect width="1080" height="1080" fill="#E9E1D3"/>')
    order = ['neutral', 'surprised', 'angry', 'smug', 'panic', 'sideeye']
    turns = {'neutral': -0.55, 'surprised': -0.25, 'angry': -0.45, 'smug': -0.6, 'panic': -0.3, 'sideeye': -0.5}
    D = 252
    for k, name in enumerate(order):
        col, row = k % 3, k // 3
        cx = 180 + col * 360
        cy = 252 + row * 540
        S.append('<circle cx="%s" cy="%s" r="%s" fill="#F4EEE3"/>' % (f(cx), f(cy + 10), f(168)))
        S.append(bust(cx, cy, D, turns[name]))
        h, _ = head('f%d' % k, cx, cy, D, LOU_H, LOU_E[name], turn=turns[name], mark_color=INK)
        S.append(h)
    S.append('</svg>')
    return '\n'.join(S)


# =====================================================================
#  LINEUP CARDS 540x1080 -- 3/4 facing the viewer's left, soles on y = 1010
# =====================================================================
def card_open(sil):
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="1080" viewBox="0 0 540 1080">']
    if sil:
        S.append('<style>.fig *{fill:#000 !important;stroke:#000 !important;opacity:1 !important}</style>')
        S.append('<rect width="540" height="1080" fill="#fff"/>')
    else:
        S.append('<rect width="540" height="1080" fill="#EDEAE4"/>')
    return S


def hero_figure(D, FLy):
    """Lou relaxed: hunched, broom planted in the near... far hand, toothpick drooping."""
    REG['limbs'].clear()
    REG['figs'].clear()
    Htot = 3.7 * D
    hx = 300
    hy = FLy - 3.6 * D
    bfl = (hx - 0.95 * D, FLy)
    base, tip = broom_line(D, Htot, bfl, 6)
    P = dict(D=D, head=(hx, hy), turn=-1, neck_ang=-16, spine=8, bow=0.10,
             arms=dict(L=dict(hand=on_line(base, tip, hy + 1.70 * D), bend=1, thumb=-1, pole=ang(base, tip)),
                       R=dict(a=10, b=-6, thumb=1, wrist=4)),
             legs=dict(L=dict(sole=(hx - 0.42 * D, FLy), bend=-1), R=dict(sole=(hx + 0.30 * D, FLy), bend=-1, rot=-6)),
             swing=0.0, rag_side=1)
    L, J = figure_fit(LOU_F, P)
    hx, hy = P['head']
    hsvg, hinfo = head('lu', hx, hy, D, LOU_H, dict(LOU_E['neutral'], gaze=(-0.7, 1.0)), turn=-1)
    g = ['<g class="fig">']
    g.append(L['L_leg'] + L['L_arm'] + L['L_pad'] + L['spine'])
    fan, handle = broom(base, tip, D, floor=FLy, skew=0)
    g.append(fan + handle)
    g.append(L['R_leg'])
    g.append(L['collar_back'] + L['neck'] + L['yoke'] + L['panel'] + L['hip'] + L['collar'])
    g.append(L['R_arm'] + L['R_pad'])
    g.append(hsvg)
    g.append(L['L_thumb'] + L['R_thumb'])
    g.append('</g>')
    return ''.join(g), (hx - 0.1 * D, D)


def partner_figure(D, FLy):
    """Dot relaxed: small, leaning back, near hand on the key strap, far hand holding a rope coil."""
    REG['limbs'].clear()
    REG['figs'].clear()
    hx = 290
    hy = FLy - 3.4 * D
    P = dict(D=D, head=(hx, hy), turn=-1, neck_ang=10, spine=-13, bow=-0.03,
             arms=dict(L=dict(a=-22, b=-34, thumb=-1, wrist=-10, mode='grip', pole=math.radians(90)),
                       R=dict(hand=(hx + 0.22 * D, hy + 1.66 * D), bend=1, thumb=-1, wrist=-30)),
             legs=dict(L=dict(sole=(hx - 0.40 * D, FLy), bend=-1, rot=-4), R=dict(sole=(hx + 0.22 * D, FLy), bend=-1)),
             keys_side=1, keys_swing=8)
    L, J = figure_fit(DOT_F, P)
    hx, hy = P['head']
    hsvg, hinfo = head('do', hx, hy, D, DOT_H, DOT_E['neutral'], turn=-1)
    g = ['<g class="fig">']
    g.append(L['L_leg'] + L['R_leg'])
    g.append(L['L_arm'] + L['L_pad'])
    g.append(coil(J['L_wr'], D, a=-8))
    g.append(L['spine'] + L['collar_back'] + L['neck'] + L['panel'] + L['hip'] + L['collar'])
    g.append(L['R_arm'] + L['R_pad'])
    g.append(hsvg)
    g.append(L['L_thumb'] + L['R_thumb'])
    g.append('</g>')
    return ''.join(g), (hx, D)


def build_card(which, sil=False, xf=None):
    """xf = (scale, x0, y_src_bottom): scale the figure about its measured sole so it is exactly
    the target height with the soles on y = 1010."""
    FLy = 1010.0
    if which == 'hero':
        D = 240.0
        body, (sx, Dk) = hero_figure(D, FLy)
    else:
        D = 214.0
        body, (sx, Dk) = partner_figure(D, FLy)
    S = card_open(sil)
    if xf:
        s, xcen, ybot = xf
        tr = 'translate(%s %s) scale(%s) translate(%s %s)' % (f(270), f(1010), '%.5f' % s, f(-xcen), '%.3f' % (-ybot))
    else:
        tr = ''
    if not sil:
        if xf:
            S.append('<ellipse cx="270" cy="1012" rx="%s" ry="12" fill="#2A211C" opacity="0.16"/>' % f(0.95 * Dk * xf[0]))
    S.append('<g transform="%s">%s</g>' % (tr, body) if tr else body)
    S.append('</svg>')
    return '\n'.join(S)


# =====================================================================
#  MAIN
# =====================================================================
if __name__ == '__main__':
    import json
    xfp = os.path.join(HERE, 'card_xf.json')
    xf = json.load(open(xfp)) if os.path.exists(xfp) else {}
    out = {
        'scene.svg': build_scene(),
        'scene_sil.svg': build_scene(sil=True),
        'faces.svg': build_faces(),
        'hero_raw_sil.svg': build_card('hero', sil=True),
        'partner_raw_sil.svg': build_card('partner', sil=True),
    }
    if 'hero' in xf:
        out['hero.svg'] = build_card('hero', xf=xf['hero'])
        out['hero_sil.svg'] = build_card('hero', sil=True, xf=xf['hero'])
    if 'partner' in xf:
        out['partner.svg'] = build_card('partner', xf=xf['partner'])
        out['partner_sil.svg'] = build_card('partner', sil=True, xf=xf['partner'])
    for k, v in out.items():
        with open(os.path.join(HERE, k), 'w') as fh:
            fh.write(v)
    print('wrote', ' '.join(sorted(out)))
