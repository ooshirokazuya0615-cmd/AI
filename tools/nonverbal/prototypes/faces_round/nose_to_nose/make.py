#!/usr/bin/env python3
"""Nose to Nose / 横顔のにらみ合い -- ROUND-HEAD stick version.

ONE round-head face rig + ONE stick-body rig draw every output:
  scene.svg  (1080x1920)  proxy war under the moon
  poses.svg  (1080x1080)  Sol: ready stance / behind-the-back parry / back leap
  lineup.svg (540x1080)   Sol alone, 3/4 toward viewer's left, 900 px tall incl. topknot
  heads.svg  (1080x1080)  extra: the face system on the circle (profile states, 3/4, front,
                          Snoot, window grandma) -- reference only
plus *_sil.svg black silhouettes for the lollipop test.

FACE RIG  head(p, C, D, facing, tilt, uid)
  The skull is a TRUE CIRCLE of diameter D (no outline; ink only on features).
  view 'profile' : wedge nose 0.30 D past the front rim (tri) or a concave ski-slope (ski),
                   mouth = notch cut into the front rim under the nose (a-f), chin bump at
                   0.88 D, ONE almond eye at 0.42 D with a skin lid mask, ink wedge brow,
                   ink C ear, flat ink hair cap over the back half, topknot / bun break,
                   flat 12%-darker jaw crescent on the lower disc (+ stubble flecks).
  view '34'      : features shifted to the facing side, near + compressed far almond,
                   wedge nose with a shadow plane breaking the rim, ear breaking the back rim.
  view 'front'   : two almonds under lids, nose = vertical shadow wedge, ears on both sides.
  Head local coords: origin = circle centre, +x = facing direction, +y = down, px.

BODY RIG  body(look, NB, f, D, pose)
  NB = neck base (from the head: neck axis 0.10 D behind centre, 0.12 D visible, 10 deg lean).
  Lengths in D: yoke 0.065 below NB, spine 1.0, thigh 0.76 + shin 0.72 + ankle 0.07 = 1.55,
  upper arm 0.68 + forearm 0.70 + mitten 0.20.  Flat tapered strokes, no outline, round caps,
  near limbs base tone, far limbs shade(c, .12) behind the spine.
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
INK = '#23201C'
EYEW = '#FFFBF2'
MOUTHC = '#3A2420'
SAND = '#E8D5B0'
TERRA = '#C0643F'
DUSK = '#3F5873'
DUSK_D = '#33485F'
NAVY_C = '#22314A'      # hanten collar / cuffs / apron waistband (costume navy)
SAGE = '#8FA58A'
SAGE_D = '#748B70'
PALE = '#F6F0E4'
MOON = '#EBD9B4'
HAZE = '#566B84'
ROOF = '#2E4258'
FLOOR_D = '#B89E78'
PLANK = '#D6BF97'
BRASS = '#C9A24B'
BRASS_D = '#A88536'
WOOD = '#A5703F'
WOOD_D = '#8C5C33'
ASH = '#D8B98A'         # pale ash broom handle
SKIN_SOL = '#9A6243'
SKIN_SNOOT = '#D6A27C'
SKIN_GRAN = '#B57A55'
GREY_H = '#B9B4AC'      # grandma's grey hair
GREY_HD = '#8E8981'
SNOOT_L = '#4A3F38'     # Snoot near limbs
SNOOT_F = '#3A322C'     # Snoot far limbs
ZORI = '#E9DCC1'
PLUM = '#6E4A5E'
LAMP = '#F2CF8A'


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith('.0') else s


def pt(p):
    return f"{n(p[0])},{n(p[1])}"


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, s):
    return (a[0] * s, a[1] * s)


def unit(v):
    d = math.hypot(v[0], v[1]) or 1.0
    return (v[0] / d, v[1] / d)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def rotv(v, deg):
    a = math.radians(deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def rot(p, c, deg):
    return add(c, rotv(sub(p, c), deg))


def ang_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


def shade(c, a):
    c = c.lstrip('#')
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    f = 1 - a
    return '#%02X%02X%02X' % (round(r * f), round(g * f), round(b * f))


def closed_rounded(verts, r):
    m = len(verts)
    rr = r if isinstance(r, (list, tuple)) else [r] * m
    parts = []
    for i in range(m):
        a, v, b = verts[i - 1], verts[i], verts[(i + 1) % m]
        da, db = math.dist(a, v), math.dist(b, v)
        ri = min(rr[i], da * 0.48, db * 0.48)
        if ri <= 0.01:
            parts.append(('M' if i == 0 else 'L') + pt(v))
            continue
        pa = (v[0] + (a[0] - v[0]) * ri / da, v[1] + (a[1] - v[1]) * ri / da)
        pb = (v[0] + (b[0] - v[0]) * ri / db, v[1] + (b[1] - v[1]) * ri / db)
        parts.append(('M' if i == 0 else 'L') + pt(pa) + ' Q' + pt(v) + ' ' + pt(pb))
    return ' '.join(parts) + ' Z'


def poly(verts):
    return 'M' + ' L'.join(pt(q) for q in verts) + ' Z'


def star4(cx, cy, R, r, rot_deg=0):
    pts = []
    for i in range(8):
        a = math.radians(rot_deg + i * 45 - 90)
        rr = R if i % 2 == 0 else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly(pts)


def tube(pts, ws, color, extra=''):
    """Tapered flat stroke through pts (trapezoid per segment + round caps/joins)."""
    o = [f'<g fill="{color}"{extra}>']
    for i in range(len(pts) - 1):
        p0, p1 = pts[i], pts[i + 1]
        w0, w1 = ws[i], ws[i + 1]
        nx, ny = unit((-(p1[1] - p0[1]), p1[0] - p0[0]))
        q = [(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
             (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)]
        o.append(f'<path d="{poly(q)}"/>')
    for p, w in zip(pts, ws):
        o.append(f'<circle cx="{n(p[0])}" cy="{n(p[1])}" r="{n(w / 2)}"/>')
    o.append('</g>')
    return ''.join(o)


def bez3(p0, p1, p2, p3, t):
    return tuple((1 - t) ** 3 * p0[i] + 3 * (1 - t) ** 2 * t * p1[i] + 3 * (1 - t) * t * t * p2[i] + t ** 3 * p3[i]
                 for i in range(2))


def ik2(root, target, a, b, hint, straight=False, max_ext=0.995):
    v = sub(target, root)
    d = math.hypot(*v) or 1.0
    u = (v[0] / d, v[1] / d)
    if straight:
        return add(root, mul(u, a)), add(root, mul(u, a + b))
    d = min(d, (a + b) * max_ext)
    d = max(d, abs(a - b) + 2)
    cosA = (a * a + d * d - b * b) / (2 * a * d)
    A = math.acos(max(-1, min(1, cosA)))
    base = math.atan2(u[1], u[0])
    tip = add(root, mul(u, d))
    mid = lerp(root, tip, 0.5)
    best = None
    for s in (1, -1):
        j = (root[0] + a * math.cos(base + s * A), root[1] + a * math.sin(base + s * A))
        score = (j[0] - mid[0]) * hint[0] + (j[1] - mid[1]) * hint[1]
        if best is None or score > best[0]:
            best = (score, j)
    return best[1], tip


# registry for checks (limb polylines in world space, head boxes)
REG = dict(limbs=[], heads=[])

# =====================================================================================
# FACE RIG
# =====================================================================================


def face(**kw):
    """Defaults = SOL neutral, profile."""
    p = dict(view='profile', skin=SKIN_SOL, hair='chasen', tie=BRASS,
             nose='tri', nose_state='neutral', nose_up=0.0,
             eye=dict(kind='almond', open=0.7, tilt=0.0, px=0.16, py=0.0, ghosts=False, d=0.39),
             brow=dict(raise_=0.0, tilt=0.0, dx=0.0, arch=0.0),
             mouth='a', my=0.765, jaw=0.0, marks=[], crow=False, stubble=True,
             smirk=0.0, far_eye=None, wrinkles=False)
    for k, v in kw.items():
        if k in ('eye', 'brow'):
            p[k] = dict(p[k], **v)
        else:
            p[k] = v
    return p


def rim(D, h, side=1):
    """Point on the circle at height fraction h (0 top .. 1 bottom), front side if side=1."""
    R = D / 2
    y = (h - 0.5) * D
    return (side * math.sqrt(max(0.0, R * R - y * y)), y)


def polar(D, deg, r_extra=0.0):
    R = D / 2 + r_extra
    a = math.radians(deg)
    return (R * math.cos(a), R * math.sin(a))


# ---------------------------------------------------------------- eye (shared by all views)
def bez_y_at(x, w, c, a):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        t = (lo + hi) / 2
        xt = (1 - t) ** 3 * (-w / 2) + 3 * (1 - t) ** 2 * t * (-a) + 3 * (1 - t) * t * t * a + t ** 3 * (w / 2)
        if xt < x:
            lo = t
        else:
            hi = t
    t = (lo + hi) / 2
    return 3 * t * (1 - t) * c


def eye_svg(e, ex, ey, w0, h0, D, skin, uid, lidw, upw, low, pr):
    """Almond / circle / arc eye with skin lid mask.  e: eye dict.  Returns (svg, top_y)."""
    kind = e['kind']
    if kind == 'arc':        # closed, smug: arc bowed upward
        w, h = w0, h0
        d = f"M{pt((ex - w / 2, ey + h * 0.12))} Q{pt((ex, ey - h * 0.80))} {pt((ex + w / 2, ey + h * 0.12))}"
        return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(lidw)}" stroke-linecap="round"/>', ey - h * 0.4)
    if kind == 'circle':
        r = e['d'] * D / 2
        shape = f'<circle cx="{n(ex)}" cy="{n(ey)}" r="{n(r)}"/>'
        top, cov, hh, w = ey - r, 0.0, 2 * r, 2 * r

        def lower(x):
            dx = max(-r, min(r, x - ex))
            return ey + math.sqrt(max(0, r * r - dx * dx))
        upper_d = f"M{pt((ex - r, ey))} A{n(r)},{n(r)} 0 0 1 {pt((ex + r, ey))}"
        lower_d = f"M{pt((ex - r, ey))} A{n(r)},{n(r)} 0 0 0 {pt((ex + r, ey))}"
    else:
        s = max(1.0, e['open'])
        w, hh = w0 * s, h0 * s
        cov = max(0.0, 1.0 - e['open'])
        hu, hl = hh * 0.54, hh * 0.46
        cu, cl = -hu / 0.75, hl / 0.75
        a = w * 0.22
        top = ey - hu
        upper_d = f"M{pt((ex - w / 2, ey))} C{pt((ex - a, ey + cu))} {pt((ex + a, ey + cu))} {pt((ex + w / 2, ey))}"
        lower_d = f"M{pt((ex - w / 2, ey))} C{pt((ex - a, ey + cl))} {pt((ex + a, ey + cl))} {pt((ex + w / 2, ey))}"
        shape = (f'<path d="M{pt((ex - w / 2, ey))} C{pt((ex - a, ey + cu))} {pt((ex + a, ey + cu))} {pt((ex + w / 2, ey))} '
                 f'C{pt((ex + a, ey + cl))} {pt((ex - a, ey + cl))} {pt((ex - w / 2, ey))} Z"/>')

        def lower(x):
            return ey + bez_y_at(x - ex, w, cl, a)
    tilt = math.tan(math.radians(e['tilt']))

    def lid_y(x):
        return top + cov * hh + tilt * (x - ex)

    cid = f'eye{uid}'
    out = [f'<defs><clipPath id="{cid}">{shape}</clipPath></defs>']
    out.append(shape.replace('/>', f' fill="{EYEW}"/>'))
    px = ex + e['px'] * w
    py = ey + e['py'] * hh
    if cov > 0:
        tv, bv = lid_y(px), lower(px)
        lo, hi = tv + pr * 0.70, bv - pr * 0.75
        py = min(max(py, lo), hi) if lo <= hi else (tv + bv) / 2 + 2
    g_in = []
    if e.get('ghosts'):
        for gx in (-0.04 * D, 0.04 * D):
            g_in.append(f'<circle cx="{n(px + gx)}" cy="{n(py)}" r="{n(pr)}" fill="{INK}" opacity="0.4"/>')
    g_in.append(f'<circle cx="{n(px)}" cy="{n(py)}" r="{n(pr)}" fill="{INK}"/>')
    if pr >= 8:
        g_in.append(f'<circle cx="{n(px + pr * 0.36)}" cy="{n(py - pr * 0.36)}" r="{n(pr * 0.28)}" fill="{EYEW}"/>')
    if cov > 0:
        x0, x1 = ex - w, ex + w
        g_in.append(f'<path d="M{pt((x0, lid_y(x0)))} L{pt((x1, lid_y(x1)))} L{pt((x1, top - hh))} L{pt((x0, top - hh))} Z" fill="{skin}"/>')
        g_in.append(f'<path d="M{pt((x0, lid_y(x0)))} L{pt((x1, lid_y(x1)))}" stroke="{INK}" stroke-width="{n(lidw)}"/>')
    out.append(f'<g clip-path="url(#{cid})">' + ''.join(g_in) + '</g>')
    uw = upw if cov < 0.02 else max(4, upw * 0.6)
    out.append(f'<path d="{upper_d}" fill="none" stroke="{INK}" stroke-width="{n(uw)}" stroke-linecap="round"/>')
    out.append(f'<path d="{lower_d}" fill="none" stroke="{INK}" stroke-width="{n(low)}" stroke-linecap="round"/>')
    return ''.join(out), top


def brow_svg(cx, cy, L, tf, tilt, arch=0.0, flip=False):
    """Ink wedge, thick end forward (+x); flip=True puts the thick end at -x."""
    tb = max(4.0, tf * 0.34)
    d = (f"M{pt((-L / 2, -tb / 2))} Q{pt((0, -tf / 2 - arch))} {pt((L / 2, -tf / 2))} "
         f"L{pt((L / 2, tf / 2))} Q{pt((0, tf / 2 - arch))} {pt((-L / 2, tb / 2))} Z")
    sc = ' scale(-1,1)' if flip else ''
    return (f'<path transform="translate({n(cx)},{n(cy)}){sc} rotate({n(tilt)})" d="{d}" fill="{INK}" '
            f'stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>')


# ---------------------------------------------------------------- profile nose
def nose_profile(p, D):
    """Returns (skin path d, details svg, tip point).  Local coords, facing +x."""
    k = D / 270.0
    st = p['nose_state']
    if p['nose'] == 'tri':
        B0 = (0.500 * D, -0.004 * D)
        B1 = rim(D, 0.72)
        T = (0.800 * D, 0.130 * D)
        if st == 'flare':
            verts = [(0.30 * D, -0.02 * D), B0, (0.815 * D, 0.122 * D), (0.782 * D, 0.178 * D),
                     (0.748 * D, 0.166 * D), (0.672 * D, 0.250 * D), (0.540 * D, 0.240 * D), B1, (0.30 * D, 0.22 * D)]
            rr = [0, 0, 9 * k, 3 * k, 4 * k, 16 * k, 10 * k, 0, 0]
        else:
            verts = [(0.30 * D, -0.02 * D), B0, T, B1, (0.30 * D, 0.22 * D)]
            rr = [0, 0, 10 * k, 0, 0]
        base = B1
        nost = None
        det = ''
        if st == 'flare':
            nost = (0.664 * D, 0.214 * D, 0.050 * D, 0.025 * D, -8)
            det += (f'<path d="M{pt((0.585 * D, 0.135 * D))} Q{pt((0.555 * D, 0.185 * D))} {pt((0.592 * D, 0.235 * D))}" '
                    f'fill="none" stroke="{INK}" stroke-width="{n(6 * k)}" stroke-linecap="round"/>')
    else:  # ski
        W = 0.47 * D
        nl, nh = 0.37 * D, 0.24 * D
        y0, y1 = 0.0, nh
        segs = [(W - 0.05 * D, y0 - 0.26 * nh), (W, y0 - 0.26 * nh)]
        # sample the bezier bridge for a polygon
        b = [bez3((W, y0 - 0.26 * nh), (W + 0.30 * nl, y0 + 0.36 * nh), (W + 0.62 * nl, y0 + 0.64 * nh),
                  (W + 0.88 * nl, y0 + 0.50 * nh), t / 14) for t in range(1, 15)]
        q1 = [bez3((W + 0.88 * nl, y0 + 0.50 * nh), (W + 0.95 * nl, y0 + 0.46 * nh), (W + 0.97 * nl, y0 + 0.42 * nh),
                   (W + 1.0 * nl, y0 + 0.34 * nh), t / 5) for t in range(1, 6)]
        q2 = [bez3((W + 1.0 * nl, y0 + 0.34 * nh), (W + 1.05 * nl, y0 + 0.50 * nh), (W + 1.02 * nl, y0 + 0.62 * nh),
                   (W + 0.90 * nl, y0 + 0.70 * nh), t / 6) for t in range(1, 7)]
        if st == 'flare':
            under = [(W + 0.74 * nl, y0 + 0.80 * nh), (W + 0.60 * nl, y1 + 0.06 * nh), (W + 0.42 * nl, y1 + 0.03 * nh),
                     (W + 0.16 * nl, y1 + 0.01 * nh), (W - 0.02 * D, y1)]
        else:
            under = [(W + 0.45 * nl, y1 - 0.04 * nh), (W + 0.18 * nl, y1 + 0.01 * nh), (W - 0.02 * D, y1)]
        verts = [(0.25 * D, y0 - 0.26 * nh)] + segs[1:] + b + q1 + q2 + under + [(0.25 * D, y1)]
        rr = 0
        base = (W, y1)
        T = (W + 1.0 * nl, y0 + 0.34 * nh)
        rx, ry = (0.052 * D, 0.030 * D) if st == 'flare' else (0.034 * D, 0.019 * D)
        nost = (W + 0.62 * nl, y0 + 0.86 * nh, rx, ry, -24)
        det = ''
        if st == 'flare':
            det += (f'<path d="M{pt((W + 0.40 * nl, y0 + 0.60 * nh))} Q{pt((W + 0.31 * nl, y0 + 0.84 * nh))} '
                    f'{pt((W + 0.42 * nl, y1 + 0.02 * nh))}" fill="none" stroke="{INK}" stroke-width="{n(5 * k)}" stroke-linecap="round"/>')
    ang = -p['nose_up'] if (st == 'up' or p.get('nose_always_up')) else 0.0
    if ang:
        verts = [rot(v, base, ang) for v in verts]
        T = rot(T, base, ang)
    d = closed_rounded(verts, rr)
    if nost:
        cx, cy, rx, ry, a = nost
        det = (f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{MOUTHC}" '
               f'transform="rotate({a},{n(cx)},{n(cy)})"/>') + det
    if ang and det:
        det = f'<g transform="rotate({n(ang)},{n(base[0])},{n(base[1])})">{det}</g>'
    return d, det, T, base


# ---------------------------------------------------------------- profile mouth
def mouth_profile(p, D):
    """Returns (skin_extra svg, notch polys (masked out), detail svg, chin_moves)."""
    k = D / 270.0
    m = p['mouth']
    hm = p['my']
    M = rim(D, hm)
    xm, ym = M
    lw = max(6.0, 8 * k)
    skin_x, notch, det = '', [], ''
    jaw_drop = False
    if m == 'a':
        notch.append([(xm + 8, ym - 5 * k), (xm - 0.10 * D, ym), (xm + 8, ym + 5 * k)])
        det = (f'<path d="M{pt((xm - 1, ym))} L{pt((xm - 0.10 * D, ym))}" stroke="{INK}" '
               f'stroke-width="{n(lw)}" stroke-linecap="round"/>')
    elif m == 'b':
        jaw_drop = True
        U = rim(D, hm - 0.02)
        I = (U[0] - 0.20 * D, U[1] + 0.06 * D)
        J = (U[0] - 0.02 * D, U[1] + 0.22 * D + p['jaw'] * D)
        # jaw piece hanging below the circle (skin), chin at J
        jawv = [I, (J[0] - 0.02 * D, J[1] - 0.02 * D), (J[0] + 0.01 * D, J[1] + 0.035 * D),
                (J[0] - 0.10 * D, J[1] + 0.085 * D), (J[0] - 0.28 * D, J[1] + 0.03 * D), (0.0, 0.40 * D)]
        skin_x = f'<path d="{closed_rounded(jawv, [0, 4 * k, 14 * k, 20 * k, 20 * k, 0])}" fill="{p["skin"]}"/>'
        det = (f'<path d="{poly([U, I, J])}" fill="{MOUTHC}" stroke="{MOUTHC}" stroke-width="2" stroke-linejoin="round"/>'
               f'<path d="M{pt(lerp(I, J, 0.55))} Q{pt(lerp(lerp(I, J, 0.8), U, 0.18))} {pt(lerp(J, U, 0.10))} L{pt(J)} Z" fill="{TERRA}"/>')
    elif m == 'c':
        cx, cy = xm - 0.01 * D, ym
        skin_x = f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(0.075 * D)}" ry="{n(0.052 * D)}" fill="{p["skin"]}"/>'
        det = (f'<path d="M{pt((cx + 0.05 * D, cy))} L{pt((cx - 0.025 * D, cy))}" stroke="{INK}" '
               f'stroke-width="{n(lw)}" stroke-linecap="round"/>')
    elif m == 'd':
        U = rim(D, hm - 0.055)
        L = rim(D, hm + 0.075)
        I = (xm - 0.16 * D, ym + 0.005 * D)
        U2 = (U[0] + 0.012 * D, U[1])
        L2 = (L[0] + 0.012 * D, L[1])
        zz = [lerp(U2, L2, 0.5)]
        steps = 5
        for i in range(1, steps + 1):
            t = i / steps
            x = zz[0][0] + (I[0] - zz[0][0]) * t
            y = zz[0][1] + (I[1] - zz[0][1]) * t + (0.024 * D if i % 2 else -0.020 * D) * (1 - t * 0.6)
            zz.append((x, y))
        det = (f'<path d="{poly([U2, I, L2])}" fill="{EYEW}"/>'
               f'<path d="M{" L".join(pt(q) for q in zz)}" fill="none" stroke="{INK}" stroke-width="{n(4.5 * k + 1)}" '
               f'stroke-linejoin="round" stroke-linecap="round"/>'
               f'<path d="M{pt(U2)} L{pt(I)} L{pt(L2)}" fill="none" stroke="{INK}" stroke-width="{n(5 * k + 1)}" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')
    elif m == 'e':
        notch.append([(xm + 8, ym - 6 * k), (xm - 0.05 * D, ym), (xm + 8, ym + 6 * k)])
        d = f"M{pt((xm + 1, ym))}"
        Lw = 0.17 * D
        for i in range(4):
            x0 = xm - Lw * i / 4
            x1 = xm - Lw * (i + 1) / 4
            amp = (0.022 if i % 2 == 0 else -0.022) * D
            d += f" Q{pt(((x0 + x1) / 2, ym + amp))} {pt((x1, ym))}"
        det = f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(lw)}" stroke-linecap="round"/>'
    else:  # f downturned
        notch.append([(xm + 8, ym - 5 * k), (xm - 0.04 * D, ym), (xm + 8, ym + 5 * k)])
        d = f"M{pt((xm + 1, ym - 1))} Q{pt((xm - 0.08 * D, ym - 0.025 * D))} {pt((xm - 0.125 * D, ym + 0.05 * D))}"
        det = f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(lw)}" stroke-linecap="round"/>'
    return skin_x, notch, det, jaw_drop


# ---------------------------------------------------------------- hair / topknot / ear
def chasen_svg(D, base_deg, lean, k, tie, sil=False):
    """Sol's tea-whisk topknot: tied stub flaring into a short brush tuft. base on the rim."""
    B = polar(D, base_deg, -0.03 * D)
    out_dir = unit(polar(1, base_deg + lean))
    side = (-out_dir[1], out_dir[0])
    L = 0.22 * D
    w0, w1 = 0.085 * D, 0.135 * D

    def P(a, s):
        return add(B, add(mul(out_dir, a), mul(side, s)))
    verts = [P(0, -w0 / 2), P(0.30 * L, -w0 * 0.45), P(0.62 * L, -w1 * 0.40), P(1.0 * L, -w1 * 0.55),
             P(0.90 * L, -w1 * 0.12), P(1.04 * L, w1 * 0.08), P(0.92 * L, w1 * 0.30), P(0.98 * L, w1 * 0.56),
             P(0.60 * L, w1 * 0.44), P(0.30 * L, w0 * 0.45), P(0, w0 / 2)]
    d = closed_rounded(verts, [2, 6 * k, 6 * k, 3 * k, 3 * k, 3 * k, 3 * k, 3 * k, 6 * k, 6 * k, 2])
    o = f'<path d="{d}" fill="{INK}"/>'
    if not sil:
        t0, t1 = 0.22 * L, 0.36 * L
        band = [P(t0, -w0 * 0.60), P(t1, -w0 * 0.62), P(t1, w0 * 0.62), P(t0, w0 * 0.60)]
        o += f'<path d="{closed_rounded(band, 2)}" fill="{tie}"/>'
    tip = P(1.04 * L, 0)
    return o, tip


def ear_c(cx, cy, h, k, sw=6.5):
    d = (f"M{pt((cx + 0.23 * h, cy - 0.50 * h))} C{pt((cx - 0.40 * h, cy - 0.58 * h))} "
         f"{pt((cx - 0.42 * h, cy + 0.54 * h))} {pt((cx + 0.18 * h, cy + 0.50 * h))}")
    d2 = f"M{pt((cx + 0.12 * h, cy - 0.16 * h))} Q{pt((cx - 0.12 * h, cy))} {pt((cx + 0.08 * h, cy + 0.20 * h))}"
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(sw * k + 0.5)}" stroke-linecap="round"/>'
            f'<path d="{d2}" fill="none" stroke="{INK}" stroke-width="{n(5 * k + 0.5)}" stroke-linecap="round"/>')


def stubble(D, pts_fn, k, col, seed=3):
    """Short flecks at deterministic pseudo-random spots returned by pts_fn."""
    o = []
    import random
    rnd = random.Random(seed)
    for (x, y) in pts_fn(rnd):
        a = rnd.uniform(-30, 30) + 70
        L = 2.2 * k + 1.0
        dx, dy = L * math.cos(math.radians(a)), L * math.sin(math.radians(a))
        o.append(f'<path d="M{pt((x - dx / 2, y - dy / 2))} L{pt((x + dx / 2, y + dy / 2))}" stroke="{col}" '
                 f'stroke-width="{n(2.6 * k + 0.8)}" stroke-linecap="round"/>')
    return ''.join(o)


# ---------------------------------------------------------------- PROFILE HEAD
def head_profile_local(p, D, uid, sil=False):
    R = D / 2
    k = D / 270.0
    skin = p['skin']
    skd = shade(skin, 0.12)
    o = []
    nose_d, nose_det, tip, nbase = nose_profile(p, D)
    mskin, notches, mdet, jaw_drop = mouth_profile(p, D)
    # chin bump (moves away when the jaw drops)
    chin = rim(D, 0.88)
    chin_svg = ''
    if not jaw_drop:
        a = ang_of(chin)
        chin_svg = (f'<ellipse cx="{n(chin[0] - 0.012 * D)}" cy="{n(chin[1])}" rx="{n(0.055 * D)}" ry="{n(0.06 * D)}" '
                    f'fill="{skin}" transform="rotate({n(a)},{n(chin[0] - 0.012 * D)},{n(chin[1])})"/>')
    skull = f'<circle r="{n(R)}" fill="{skin}"/>'
    if sil:
        o.append(f'<g fill="{INK}">{skull}<path d="{nose_d}"/>{mskin}{chin_svg}</g>')
        if p['hair'] == 'chasen':
            o.append(chasen_svg(D, -118, -22, k, p['tie'], sil=True)[0])
        elif p['hair'] == 'bun':
            o.append(bun_svg(D, k, p['tie'], sil=True))
        elif p['hair'] == 'grey_bun':
            o.append(grey_bun_profile(D, k, sil=True))
        return ''.join(o).replace(skin, INK)
    mid = f'nm{uid}'
    cid = f'sk{uid}'
    o.append(f'<defs><mask id="{mid}" maskUnits="userSpaceOnUse" x="{n(-2 * D)}" y="{n(-2 * D)}" width="{n(4 * D)}" height="{n(4 * D)}">'
             f'<rect x="{n(-2 * D)}" y="{n(-2 * D)}" width="{n(4 * D)}" height="{n(4 * D)}" fill="#fff"/>'
             + ''.join(f'<path d="{poly(q)}" fill="#000"/>' for q in notches) +
             f'</mask><clipPath id="{cid}"><circle r="{n(R)}"/>{mskin.replace(" fill=", " data-f=")}</clipPath></defs>')
    g = [skull, f'<path d="{nose_d}" fill="{skin}"/>', mskin, chin_svg]
    # jaw crescent: everything below the jaw line (chin -> under the ear), clipped to skull (+ jaw piece)
    jf = rim(D, 0.815)
    jaw_line = (f"M{pt((jf[0] + 0.1 * D, jf[1]))} L{pt(jf)} C{pt((0.18 * D, 0.31 * D))} {pt((0.02 * D, 0.22 * D))} "
                f"{pt((-0.07 * D, 0.115 * D))} L{pt((-0.30 * D, 0.06 * D))} L{pt((-0.8 * D, 0.06 * D))} "
                f"L{pt((-0.8 * D, 1.2 * D))} L{pt((0.8 * D, 1.2 * D))} Z")
    g.append(f'<path clip-path="url(#{cid})" d="{jaw_line}" fill="{skd}"/>')
    if jaw_drop:
        g.append(f'<path d="{jaw_line}" fill="{skd}" clip-path="url(#{cid})"/>')
    if p.get('stubble'):
        def spots(rnd):
            out = []
            for _ in range(70):
                x = rnd.uniform(-0.10, 0.36) * D
                y = rnd.uniform(0.16, 0.47) * D
                # inside skull and below jaw line roughly
                if x * x + y * y > (R - 6 * k) ** 2:
                    continue
                yl = 0.115 * D + (x + 0.07 * D) / (0.39 * D) * (0.315 - 0.115) * D
                if y < yl + 5 * k:
                    continue
                out.append((x, y))
            return out[:13]
        g.append(stubble(D, spots, k, shade(skin, 0.26)))
    # hair cap
    if p['hair'] == 'chasen':
        a0, a1 = polar(D, -112, 2), polar(D, 122, 2)
        cap = (f"M{pt(a0)} C{pt((-0.14 * D, -0.30 * D))} {pt((-0.25 * D, -0.10 * D))} {pt((-0.215 * D, 0.10 * D))} "
               f"C{pt((-0.20 * D, 0.22 * D))} {pt((-0.22 * D, 0.36 * D))} {pt(a1)} "
               f"L{pt((-0.9 * D, 0.6 * D))} L{pt((-0.9 * D, -0.9 * D))} Z")
        g.append(f'<path clip-path="url(#{cid})" d="{cap}" fill="{INK}"/>')
    elif p['hair'] == 'bun':      # Snoot: slicked cap from the front of the crown
        a0, a1 = polar(D, -76, 2), polar(D, 124, 2)
        cap = (f"M{pt(a0)} C{pt((-0.02 * D, -0.40 * D))} {pt((-0.20 * D, -0.30 * D))} {pt((-0.235 * D, -0.10 * D))} "
               f"C{pt((-0.25 * D, 0.04 * D))} {pt((-0.21 * D, 0.24 * D))} {pt(a1)} "
               f"L{pt((-0.9 * D, 0.6 * D))} L{pt((-0.9 * D, -0.9 * D))} Z")
        g.append(f'<path clip-path="url(#{cid})" d="{cap}" fill="{INK}"/>')
    elif p['hair'] == 'grey_bun':
        a0, a1 = polar(D, -70, 2), polar(D, 125, 2)
        cap = (f"M{pt(a0)} C{pt((0.02 * D, -0.38 * D))} {pt((-0.18 * D, -0.30 * D))} {pt((-0.22 * D, -0.10 * D))} "
               f"C{pt((-0.24 * D, 0.04 * D))} {pt((-0.20 * D, 0.26 * D))} {pt(a1)} "
               f"L{pt((-0.9 * D, 0.6 * D))} L{pt((-0.9 * D, -0.9 * D))} Z")
        g.append(f'<path clip-path="url(#{cid})" d="{cap}" fill="{GREY_H}"/>')
    o.append(f'<g mask="url(#{mid})">' + ''.join(g) + '</g>')
    # topknot / bun (outside the circle = the top break)
    if p['hair'] == 'chasen':
        o.append(chasen_svg(D, -118, -22, k, p['tie'])[0])
    elif p['hair'] == 'bun':
        o.append(bun_svg(D, k, p['tie']))
    elif p['hair'] == 'grey_bun':
        o.append(grey_bun_profile(D, k))
    # ear
    o.append(ear_c(-0.08 * D, 0.0, 0.19 * D, k))
    # eye
    e = p['eye']
    ew, eh = 0.37 * D, 0.24 * D
    ey = (0.42 - 0.5) * D
    front = rim(D, 0.42)[0]
    if e['kind'] == 'circle':
        ex = front - 0.12 * D - e['d'] * D / 2
    else:
        ex = front - 0.12 * D - ew / 2
    lidw = max(9.0, 11.5 * k)
    eye, etop = eye_svg(e, ex, ey, ew, eh, D, skin, uid, lidw, max(6.0, 8 * k), max(3.5, 4.5 * k), 0.045 * D)
    o.append(eye)
    if p.get('crow'):
        bx, by = ex - ew / 2 - 0.012 * D, ey + 0.012 * D
        for a in (-30, 0, 30):
            p0 = add((bx, by), rotv((-0.008 * D, 0), a))
            p1 = add((bx, by), rotv((-0.050 * D, 0), a))
            o.append(f'<path d="M{pt(p0)} L{pt(p1)}" stroke="{INK}" stroke-width="{n(4.5 * k + 0.5)}" stroke-linecap="round"/>')
    b = p['brow']
    bl, bt = 0.30 * D, 0.06 * D
    bcx = ex + b['dx'] * D + 0.01 * D
    bcy = etop - 0.07 * D - bt / 2 - b['raise_'] * D
    o.append(brow_svg(bcx, bcy, bl, bt, b['tilt'], b.get('arch', 0) * D))
    o.append(mdet)
    o.append(nose_det)
    o.append(marks_svg(p, D, tip, nbase, ex, ey))
    return ''.join(o)


def bun_svg(D, k, tie, sil=False):
    """Snoot: black bun on the top-back rim, gold hairpin through it, terracotta tie at its base."""
    c = polar(D, -134, 0.015 * D)
    r = 0.125 * D
    o = []
    if not sil:
        a = math.radians(-20)
        L0, L1 = 0.21 * D, 0.21 * D
        p0 = (c[0] - L0 * math.cos(a), c[1] - L0 * math.sin(a) + 0.04 * D)
        p1 = (c[0] + L1 * math.cos(a), c[1] + L1 * math.sin(a) - 0.06 * D)
        o.append(f'<path d="M{pt(p0)} L{pt(p1)}" stroke="{BRASS}" stroke-width="{n(0.026 * D)}" stroke-linecap="round"/>')
        o.append(f'<circle cx="{n(p1[0])}" cy="{n(p1[1])}" r="{n(0.026 * D)}" fill="{BRASS}"/>')
    o.append(f'<circle cx="{n(c[0])}" cy="{n(c[1])}" r="{n(r)}" fill="{INK}"/>')
    if not sil:
        # tie wrapped round the base of the bun (towards the skull)
        tb = polar(D, -134, -0.06 * D)
        a0 = math.radians(-134 + 90)
        q0 = add(c, mul((math.cos(a0), math.sin(a0)), r * 0.98))
        q1 = add(c, mul((math.cos(a0 + math.pi), math.sin(a0 + math.pi)), r * 0.98))
        o.append(f'<path d="M{pt(q0)} Q{pt(lerp(tb, c, 0.15))} {pt(q1)}" fill="none" stroke="{TERRA}" '
                 f'stroke-width="{n(0.045 * D)}" stroke-linecap="round"/>')
    return ''.join(o)


def grey_bun_profile(D, k, sil=False):
    c = polar(D, -128, 0.02 * D)
    r = 0.11 * D
    o = [f'<circle cx="{n(c[0])}" cy="{n(c[1])}" r="{n(r)}" fill="{INK if sil else GREY_H}"/>']
    if not sil:
        o.append(f'<path d="M{pt((c[0] - r * 0.55, c[1] - r * 0.1))} Q{pt((c[0], c[1] - r * 0.85))} {pt((c[0] + r * 0.6, c[1] - r * 0.2))}" '
                 f'fill="none" stroke="{GREY_HD}" stroke-width="{n(3.5 * k + 0.5)}" stroke-linecap="round"/>')
    return ''.join(o)


def marks_svg(p, D, tip, nbase, ex, ey):
    k = D / 270.0
    out = []
    st = f'fill="none" stroke="{INK}" stroke-width="{n(max(5, 7 * k))}" stroke-linecap="round"'
    for m in p['marks']:
        if m == 'emanata':
            ox, oy = 0.50 * D, -0.40 * D
            for ang in (-40, -12, 16):
                a = math.radians(ang)
                p0 = (ox + 0.05 * D * math.cos(a), oy + 0.05 * D * math.sin(a))
                p1 = (ox + 0.17 * D * math.cos(a), oy + 0.17 * D * math.sin(a))
                out.append(f'<path d="M{pt(p0)} L{pt(p1)}" {st}/>')
        elif m == 'snort':
            bx, by = tip[0] - 0.05 * D, tip[1] + 0.07 * D
            if p['nose'] == 'ski':
                bx, by = tip[0] - 0.09 * D, tip[1] + 0.13 * D
            for ang in (40, 64, 88):
                a = math.radians(ang)
                p0 = (bx + 0.05 * D * math.cos(a), by + 0.05 * D * math.sin(a))
                p1 = (bx + 0.12 * D * math.cos(a), by + 0.12 * D * math.sin(a))
                out.append(f'<path d="M{pt(p0)} L{pt(p1)}" fill="none" stroke="{INK}" stroke-width="{n(max(5, 6.5 * k))}" stroke-linecap="round"/>')
        elif m == 'shake':
            for off in (0.62, 0.70):
                x = -off * D
                d = f"M{pt((x + 0.03 * D, -0.20 * D))} Q{pt((x - 0.03 * D, -0.06 * D))} {pt((x + 0.03 * D, 0.08 * D))}"
                out.append(f'<path d="{d}" {st}/>')
        elif m == 'sweat':
            cx, cy = -0.30 * D, -0.58 * D
            d = "M0,-26 C9,-10 16,2 0,16 C-16,2 -9,-10 0,-26 Z"
            out.append(f'<path transform="translate({n(cx)},{n(cy)}) rotate(140) scale({n(1.2 * k)})" d="{d}" '
                       f'fill="{PALE}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
    return ''.join(out)


# ---------------------------------------------------------------- FRONT HEAD
def head_front_local(p, D, uid, sil=False):
    R = D / 2
    k = D / 270.0
    skin = p['skin']
    skd = shade(skin, 0.12)
    o = []
    cid = f'skf{uid}'
    ear_r = (0.066 * D, 0.105 * D)
    ears = ''.join(f'<ellipse cx="{n(s * (R + 0.005 * D))}" cy="{n(0.02 * D)}" rx="{n(ear_r[0])}" ry="{n(ear_r[1])}" fill="{skin}"/>'
                   for s in (-1, 1))
    jawp = ''
    if p['mouth'] == 'o':
        jawp = f'<ellipse cx="0" cy="{n(0.44 * D)}" rx="{n(0.19 * D)}" ry="{n(0.12 * D)}" fill="{INK if sil else skd}"/>'
    if sil:
        o.append(f'<g fill="{INK}">{ears}<circle r="{n(R)}"/>{jawp}</g>')
        if p['hair'] == 'chasen':
            o.append(chasen_svg(D, -90, 0, k, p['tie'], sil=True)[0])
        else:
            o.append(f'<circle cx="0" cy="{n(-R - 0.02 * D)}" r="{n(0.12 * D)}" fill="{INK}"/>')
        return ''.join(o).replace(skin, INK)
    o.append(f'<defs><clipPath id="{cid}"><circle r="{n(R)}"/></clipPath></defs>')
    o.append(ears)
    o.append(jawp)
    o.append(f'<circle r="{n(R)}" fill="{skin}"/>')
    # jaw crescent (smile-shaped band on the lower disc)
    jd = (f"M{pt((-0.6 * D, 0.10 * D))} L{pt((-0.47 * D, 0.10 * D))} C{pt((-0.30 * D, 0.40 * D))} {pt((0.30 * D, 0.40 * D))} "
          f"{pt((0.47 * D, 0.10 * D))} L{pt((0.6 * D, 0.10 * D))} L{pt((0.6 * D, 0.8 * D))} L{pt((-0.6 * D, 0.8 * D))} Z")
    if p.get('jowls'):
        jd = (f"M{pt((-0.6 * D, 0.06 * D))} L{pt((-0.47 * D, 0.06 * D))} C{pt((-0.36 * D, 0.32 * D))} {pt((-0.20 * D, 0.30 * D))} "
              f"{pt((0, 0.38 * D))} C{pt((0.20 * D, 0.30 * D))} {pt((0.36 * D, 0.32 * D))} {pt((0.47 * D, 0.06 * D))} "
              f"L{pt((0.6 * D, 0.06 * D))} L{pt((0.6 * D, 0.8 * D))} L{pt((-0.6 * D, 0.8 * D))} Z")
    o.append(f'<path clip-path="url(#{cid})" d="{jd}" fill="{skd}"/>')
    if p.get('stubble'):
        def spots(rnd):
            out = []
            for _ in range(90):
                x = rnd.uniform(-0.40, 0.40) * D
                y = rnd.uniform(0.18, 0.47) * D
                if x * x + y * y > (R - 6 * k) ** 2:
                    continue
                if y < 0.10 * D + 0.30 * D * (1 - (abs(x) / (0.47 * D)) ** 2) * 0.75 + 6 * k:
                    continue
                out.append((x, y))
            return out[:14]
        o.append(stubble(D, spots, k, shade(skin, 0.26)))
    # hair
    if p['hair'] == 'chasen':
        # back-of-head hair peeks out at both sides (shaved pate in front)
        for s in (-1, 1):
            d = (f"M{pt(polar(D, -90 + s * 50, 1))} C{pt((s * 0.34 * D, -0.24 * D))} {pt((s * 0.40 * D, 0.08 * D))} "
                 f"{pt((s * 0.38 * D, 0.30 * D))} L{pt((s * 0.7 * D, 0.3 * D))} L{pt((s * 0.7 * D, -0.7 * D))} Z")
            o.append(f'<path clip-path="url(#{cid})" d="{d}" fill="{INK}"/>')
    elif p['hair'] == 'grey_bun':
        d = (f"M{pt((-0.7 * D, 0.10 * D))} L{pt((-0.47 * D, 0.10 * D))} C{pt((-0.44 * D, -0.12 * D))} {pt((-0.28 * D, -0.24 * D))} "
             f"{pt((0, -0.25 * D))} C{pt((0.28 * D, -0.24 * D))} {pt((0.44 * D, -0.12 * D))} {pt((0.47 * D, 0.10 * D))} "
             f"L{pt((0.7 * D, 0.10 * D))} L{pt((0.7 * D, -0.8 * D))} L{pt((-0.7 * D, -0.8 * D))} Z")
        o.append(f'<path clip-path="url(#{cid})" d="{d}" fill="{GREY_H}"/>')
        o.append(f'<path clip-path="url(#{cid})" d="M{pt((0, -0.25 * D))} L{pt((0, -0.6 * D))}" stroke="{GREY_HD}" stroke-width="{n(4 * k + 0.5)}"/>')
    # re-draw ears' inner C on top of hair
    for s in (-1, 1):
        cx = s * (R + 0.012 * D)
        h = 0.12 * D
        d = (f"M{pt((cx - s * 0.10 * h, 0.02 * D - 0.30 * h))} Q{pt((cx + s * 0.30 * h, 0.02 * D))} {pt((cx - s * 0.05 * h, 0.02 * D + 0.32 * h))}")
        o.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(5 * k + 0.5)}" stroke-linecap="round"/>')
    # top break
    if p['hair'] == 'chasen':
        o.append(chasen_svg(D, -96, -8, k, p['tie'])[0])
    else:
        bc = (0, -R - 0.03 * D)
        o.append(f'<circle cx="{n(bc[0])}" cy="{n(bc[1])}" r="{n(0.12 * D)}" fill="{GREY_H}"/>')
        o.append(f'<path d="M{pt((bc[0] - 0.07 * D, bc[1] + 0.02 * D))} Q{pt((bc[0], bc[1] - 0.08 * D))} {pt((bc[0] + 0.07 * D, bc[1] + 0.01 * D))}" '
                 f'fill="none" stroke="{GREY_HD}" stroke-width="{n(4 * k + 0.5)}" stroke-linecap="round"/>')
        o.append(f'<path d="M{pt((bc[0] - 0.17 * D, bc[1] + 0.03 * D))} L{pt((bc[0] + 0.17 * D, bc[1] - 0.05 * D))}" stroke="{PLUM}" '
                 f'stroke-width="{n(0.022 * D)}" stroke-linecap="round"/>')
    # eyes
    e = p['eye']
    ew, eh = 0.29 * D, 0.185 * D
    ey = (0.43 - 0.5) * D
    lidw = max(7.0, 10 * k)
    tops = []
    for s in (-1, 1):
        ex = s * 0.195 * D
        es = dict(e)
        es['tilt'] = e['tilt'] * s
        eye, top = eye_svg(es, ex, ey, ew, eh, D, skin, f'{uid}{s}', lidw, max(5.0, 7 * k), max(3.0, 4 * k), 0.036 * D)
        o.append(eye)
        tops.append(top)
    b = p['brow']
    for s in (-1, 1):
        o.append(brow_svg(s * 0.185 * D, min(tops) - 0.06 * D - b['raise_'] * D, 0.24 * D, 0.05 * D, -s * b['tilt'],
                          b.get('arch', 0) * D, flip=(s > 0)))
    # nose: vertical shadow wedge (light from the left)
    nd = poly([(0.004 * D, -0.04 * D), (0.07 * D, 0.175 * D), (-0.02 * D, 0.19 * D)])
    o.append(f'<path d="{nd}" fill="{shade(skin, 0.22)}"/>')
    # mouth
    my = (0.78 - 0.5) * D
    if p['mouth'] == 'o':
        md = closed_rounded([(-0.10 * D, my - 0.07 * D), (0.10 * D, my - 0.07 * D), (0.085 * D, my + 0.17 * D), (-0.085 * D, my + 0.17 * D)],
                            [0.04 * D, 0.04 * D, 0.07 * D, 0.07 * D])
        o.append(f'<path d="{md}" fill="{MOUTHC}"/>')
        o.append(f'<ellipse cx="0" cy="{n(my + 0.13 * D)}" rx="{n(0.065 * D)}" ry="{n(0.035 * D)}" fill="{TERRA}"/>')
    elif p['mouth'] == 'f':
        o.append(f'<path d="M{pt((-0.10 * D, my + 0.02 * D))} Q{pt((0, my - 0.03 * D))} {pt((0.10 * D, my + 0.02 * D))}" fill="none" '
                 f'stroke="{INK}" stroke-width="{n(max(5, 7 * k))}" stroke-linecap="round"/>')
    else:
        o.append(f'<path d="M{pt((-0.10 * D, my))} L{pt((0.10 * D, my + p.get("smirk", 0) * D))}" stroke="{INK}" '
                 f'stroke-width="{n(max(5, 7 * k))}" stroke-linecap="round"/>')
    if p.get('wrinkles'):
        for s in (-1, 1):
            d = f"M{pt((s * 0.20 * D, my - 0.09 * D))} Q{pt((s * 0.25 * D, my - 0.02 * D))} {pt((s * 0.21 * D, my + 0.05 * D))}"
            o.append(f'<path d="{d}" fill="none" stroke="{shade(skin, 0.45)}" stroke-width="{n(4 * k + 0.6)}" stroke-linecap="round"/>')
            d2 = f"M{pt((s * 0.12 * D, ey + 0.115 * D))} Q{pt((s * 0.20 * D, ey + 0.14 * D))} {pt((s * 0.28 * D, ey + 0.11 * D))}"
            o.append(f'<path d="{d2}" fill="none" stroke="{shade(skin, 0.40)}" stroke-width="{n(3.5 * k + 0.6)}" stroke-linecap="round"/>')
    return ''.join(o)


# ---------------------------------------------------------------- 3/4 HEAD (facing +x)
def head_34_local(p, D, uid, sil=False):
    R = D / 2
    k = D / 270.0
    skin = p['skin']
    skd = shade(skin, 0.12)
    o = []
    cid = f'sk3{uid}'
    # nose wedge (breaks the front rim)
    N0 = (0.300 * D, -0.035 * D)
    T = (0.590 * D, 0.135 * D)
    NB = (0.385 * D, 0.205 * D)
    nose = closed_rounded([N0, T, NB, (0.27 * D, 0.20 * D)], [3, 9 * k, 6 * k, 0])
    ear = (f'<ellipse cx="{n(-R + 0.005 * D)}" cy="{n(0.025 * D)}" rx="{n(0.07 * D)}" ry="{n(0.105 * D)}" fill="{skin}" '
           f'transform="rotate(8,{n(-R)},{n(0.025 * D)})"/>')
    chin = rim(D, 0.885)
    chin_svg = (f'<ellipse cx="{n(chin[0] - 0.015 * D)}" cy="{n(chin[1])}" rx="{n(0.06 * D)}" ry="{n(0.055 * D)}" fill="{skin}" '
                f'transform="rotate({n(ang_of(chin))},{n(chin[0] - 0.015 * D)},{n(chin[1])})"/>')
    if sil:
        o.append(f'<g fill="{INK}"><circle r="{n(R)}"/><path d="{nose}"/>{ear}{chin_svg}</g>')
        o.append(chasen_svg(D, -104, -16, k, p['tie'], sil=True)[0])
        return ''.join(o).replace(skin, INK)
    o.append(f'<defs><clipPath id="{cid}"><circle r="{n(R)}"/></clipPath></defs>')
    o.append(f'<circle r="{n(R)}" fill="{skin}"/>')
    o.append(chin_svg)
    # jaw crescent: chin (front-bottom) -> under the ear (back)
    jd = (f"M{pt((0.7 * D, 0.30 * D))} L{pt((0.36 * D, 0.31 * D))} C{pt((0.16 * D, 0.36 * D))} {pt((-0.14 * D, 0.27 * D))} "
          f"{pt((-0.36 * D, 0.13 * D))} L{pt((-0.7 * D, 0.10 * D))} L{pt((-0.7 * D, 0.9 * D))} L{pt((0.7 * D, 0.9 * D))} Z")
    o.append(f'<g clip-path="url(#{cid})"><path d="{jd}" fill="{skd}"/></g>')
    # chin bump shading continues
    o.append(chin_svg.replace(f'fill="{skin}"', f'fill="{skd}"'))
    if p.get('stubble'):
        def spots(rnd):
            out = []
            for _ in range(90):
                x = rnd.uniform(-0.34, 0.42) * D
                y = rnd.uniform(0.16, 0.47) * D
                if x * x + y * y > (R - 6 * k) ** 2:
                    continue
                yl = 0.13 * D + (x + 0.36 * D) / (0.72 * D) * 0.18 * D + 0.06 * D * math.sin(math.pi * (x + 0.36 * D) / (0.72 * D))
                if y < yl + 5 * k:
                    continue
                out.append((x, y))
            return out[:14]
        o.append(stubble(D, spots, k, shade(skin, 0.26)))
    # hair cap over the back quarter (behind the ear)
    a0, a1 = polar(D, -100, 2), polar(D, 128, 2)
    cap = (f"M{pt(a0)} C{pt((-0.16 * D, -0.40 * D))} {pt((-0.30 * D, -0.22 * D))} {pt((-0.33 * D, -0.04 * D))} "
           f"C{pt((-0.35 * D, 0.10 * D))} {pt((-0.33 * D, 0.28 * D))} {pt(a1)} "
           f"L{pt((-0.9 * D, 0.6 * D))} L{pt((-0.9 * D, -0.9 * D))} Z")
    o.append(f'<path clip-path="url(#{cid})" d="{cap}" fill="{INK}"/>')
    o.append(chasen_svg(D, -104, -16, k, p['tie'])[0])
    o.append(ear)
    o.append(ear_c(-R + 0.01 * D, 0.025 * D, 0.12 * D, k, 5))
    # eyes: near (bigger, nearer centre) + far (compressed, near the front rim)
    e = p['eye']
    ey = (0.43 - 0.5) * D
    lidw = max(8.0, 11 * k)
    near_eye, top_n = eye_svg(e, 0.085 * D, ey, 0.30 * D, 0.20 * D, D, skin, f'{uid}n', lidw, max(5.0, 7.5 * k), max(3.0, 4 * k), 0.040 * D)
    fe = dict(e)
    fe['px'] = e['px'] * 0.6
    far_eye, top_f = eye_svg(fe, 0.385 * D, ey + 0.005 * D, 0.155 * D, 0.185 * D, D, skin, f'{uid}f', lidw * 0.9, max(5.0, 7 * k), max(3.0, 4 * k), 0.034 * D)
    o.append(f'<g clip-path="url(#{cid})">{far_eye}</g>')
    o.append(near_eye)
    b = p['brow']
    o.append(brow_svg(0.10 * D, top_n - 0.065 * D - b['raise_'] * D, 0.25 * D, 0.055 * D, b['tilt'], b.get('arch', 0) * D))
    o.append(brow_svg(0.395 * D, top_f - 0.06 * D - b['raise_'] * D, 0.12 * D, 0.048 * D, b['tilt'] - 6, b.get('arch', 0) * D, flip=False))
    # nose on top of the far eye
    o.append(f'<path d="{nose}" fill="{skin}"/>')
    shadow = closed_rounded([N0, NB, (0.27 * D, 0.20 * D), (0.255 * D, 0.06 * D)], [3, 5 * k, 6 * k, 6 * k])
    o.append(f'<path d="{shadow}" fill="{shade(skin, 0.16)}"/>')
    o.append(f'<path d="M{pt((0.395 * D, 0.175 * D))} Q{pt((0.43 * D, 0.21 * D))} {pt((0.47 * D, 0.195 * D))}" fill="none" stroke="{MOUTHC}" '
             f'stroke-width="{n(5 * k + 0.5)}" stroke-linecap="round"/>')
    # mouth: short line, confident corner up at the near end
    my = (0.775 - 0.5) * D
    sm = p.get('smirk', 0) * D
    o.append(f'<path d="M{pt((0.16 * D, my - sm))} Q{pt((0.28 * D, my + 0.012 * D))} {pt((0.42 * D, my + 0.004 * D))}" fill="none" '
             f'stroke="{INK}" stroke-width="{n(max(5, 7.5 * k))}" stroke-linecap="round"/>')
    return ''.join(o)


def head_local(p, D, uid, sil=False):
    v = p['view']
    if v == 'front':
        return head_front_local(p, D, uid, sil)
    if v == '34':
        return head_34_local(p, D, uid, sil)
    return head_profile_local(p, D, uid, sil)


def head(p, C, D, facing=1, tilt=0.0, uid='a', sil=False):
    REG['heads'].append((C, D))
    return (f'<g transform="translate({pt(C)}) scale({facing},1) rotate({n(tilt)})">'
            f'{head_local(p, D, uid, sil)}</g>')


def to_world(q, C, facing, tilt):
    x, y = rotv(q, tilt)
    return (C[0] + facing * x, C[1] + y)


def topknot_top(p, C, D, facing, tilt):
    """World y of the highest point of the head (topknot / bun) -- for the lineup size."""
    k = D / 270.0
    if p['view'] == '34':
        _, tip = chasen_svg(D, -104, -16, k, BRASS)
    elif p['view'] == 'front':
        _, tip = chasen_svg(D, -96, -8, k, BRASS)
    else:
        _, tip = chasen_svg(D, -118, -22, k, BRASS)
    pts = [to_world(tip, C, facing, tilt), (C[0], C[1] - D / 2)]
    # tuft corners can sit a little higher than the axis tip
    return min(q[1] for q in pts) - 0.035 * D




# =====================================================================================
# STICK-BODY RIG
# =====================================================================================
LOOK_SOL = dict(name='sol', limb=DUSK_D, far=shade(DUSK_D, 0.12), skin=SKIN_SOL, feet='tabi',
                anchor='eri', hip='apron', cuff=NAVY_C, edge=None)
LOOK_SNOOT = dict(name='snoot', limb=SNOOT_L, far=SNOOT_F, skin=SKIN_SNOOT, feet='zori',
                  anchor='tenugui', hip='belt', cuff=None, edge=PALE)

SHOULDERS = dict(profile=(0.10, -0.10), twist=(0.035, -0.17), front=(0.30, -0.30), **{'34': (-0.27, 0.15)})
HIPS = dict(profile=(0.02, -0.02), twist=(0.02, -0.04), front=(0.095, -0.095), **{'34': (-0.09, 0.05)})


def neck_geom(C, D, f, tilt, view, neck_lean=10.0, hidden=None):
    """NT = neck top inside the skull (rotates with the head), NB = neck base (body side),
    ndir = unit vector down the neck."""
    k = D / 270.0
    hid = 15 * k if hidden is None else hidden
    ax = {'profile': -0.10, 'twist': -0.10, '34': -0.09, 'front': 0.0}[view] * D
    lean = 0.0 if view == 'front' else neck_lean
    ysb = math.sqrt((D / 2) ** 2 - ax * ax)
    NT = to_world((ax, ysb - hid), C, f, tilt)
    sb0 = to_world((ax, ysb), C, f, tilt if view == 'front' else 0.0)
    ndir = (f * -math.sin(math.radians(lean)), math.cos(math.radians(lean)))
    if view == 'front':
        ndir = rotv((0.0, 1.0), tilt)
    NB = add(sb0, mul(ndir, 0.12 * D))
    return NT, NB, ndir


def offset_poly(pts, d):
    out = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        t = unit(sub(b, a))
        nrm = (-t[1], t[0])
        out.append(add(p, mul(nrm, d)))
    return out


def mitten(wrist, ang, D, f, color, thumb=-1, grip=False, cuff=None, limb_w=13):
    """Flat skin paddle 0.20 x 0.13 D with a thumb nub. Returns (body_svg, thumb_svg)."""
    L, W = 0.20 * D, 0.13 * D
    if grip:
        W *= 1.08
    tf = f'translate({pt(wrist)}) rotate({n(ang)})'
    body = (f'<g transform="{tf}"><rect x="{n(-W * 0.22)}" y="{n(-W / 2)}" width="{n(L + W * 0.22)}" height="{n(W)}" '
            f'rx="{n(W / 2)}" fill="{color}"/>')
    if cuff:
        cw = max(limb_w + 7, W * 0.92)
        body += f'<rect x="{n(-0.055 * D)}" y="{n(-cw / 2)}" width="{n(0.05 * D)}" height="{n(cw)}" rx="{n(0.015 * D)}" fill="{cuff}"/>'
    body += '</g>'
    if grip:
        cx, cy, rx, ry = L * 0.46, thumb * W * 0.36, W * 0.42, W * 0.33
    else:
        cx, cy, rx, ry = L * 0.26, thumb * W * 0.50, W * 0.34, W * 0.26
    th = (f'<g transform="{tf}"><ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{color}" '
          f'transform="rotate({n(-22 * thumb)},{n(cx)},{n(cy)})"/></g>')
    return body, th


def foot_svg(kind, ankle, f, ang, D, shin_dir, leg_w, view='profile', far=False):
    """Profile foot (tabi: INK sole wedge + PALE sock band; zori: INK tabi on a cream zori)."""
    fl, ah = 0.30 * D, 0.07 * D
    if view == 'front':
        fl *= 0.62
    elif view == '34':
        fl *= 0.84
    verts = [(-0.28 * fl, -0.03 * D), (0.16 * fl, -0.03 * D), (0.62 * fl, ah * 0.28), (0.74 * fl, ah), (-0.30 * fl, ah)]
    dsh = closed_rounded(verts, [0.03 * D, 0.035 * D, 0.045 * D, 0.012 * D, 0.02 * D])
    tf = f'translate({pt(ankle)}) scale({f},1) rotate({n(ang)})'
    o = []
    if kind == 'zori':
        zd = closed_rounded([(-0.36 * fl, ah - 1), (0.82 * fl, ah - 1), (0.82 * fl, ah + 0.04 * D), (-0.36 * fl, ah + 0.04 * D)], 0.018 * D)
        o.append(f'<path transform="{tf}" d="{zd}" fill="{WOOD_D}"/>')
        zd2 = closed_rounded([(-0.36 * fl, ah - 1), (0.82 * fl, ah - 1), (0.82 * fl, ah + 0.022 * D), (-0.36 * fl, ah + 0.022 * D)], 0.01 * D)
        o.append(f'<path transform="{tf}" d="{zd2}" fill="{ZORI}"/>')
        o.append(f'<path transform="{tf}" d="{dsh}" fill="{INK}"/>')
        o.append(f'<path transform="{tf}" d="M{n(0.52 * fl)},{n(ah * 0.22)} L{n(0.12 * fl)},{n(ah - 2)}" stroke="{TERRA}" '
                 f'stroke-width="{n(0.022 * D)}" stroke-linecap="round" fill="none"/>')
    else:
        o.append(f'<path transform="{tf}" d="{dsh}" fill="{shade(INK, 0.0) if not far else "#1A1815"}"/>')
        a = ang_of(shin_dir) - 90
        c = add(ankle, mul(shin_dir, -0.035 * D))
        bw = leg_w + 0.04 * D
        o.append(f'<rect transform="translate({pt(c)}) rotate({n(a)})" x="{n(-bw / 2)}" y="{n(-0.028 * D)}" '
                 f'width="{n(bw)}" height="{n(0.056 * D)}" rx="{n(0.02 * D)}" fill="{PALE if not far else shade(PALE, 0.12)}"/>')
    return ''.join(o)


def broom_svg(a, b, D, fan=0.40, sil=False):
    """Handle end a -> bristle tip b.  Pale ash handle, BRASS fan with INK bands."""
    L = math.dist(a, b)
    ang = ang_of(sub(b, a))
    fl = fan * D
    Ls = L - fl
    hw = 0.06 * D
    w0, w1 = 0.11 * D, 0.33 * D
    o = [f'<g transform="translate({pt(a)}) rotate({n(ang)})">']
    o.append(f'<rect x="0" y="{n(-hw / 2)}" width="{n(Ls + 6)}" height="{n(hw)}" rx="{n(hw / 2)}" fill="{INK if sil else ASH}"/>')
    if not sil:
        o.append(f'<rect x="-2" y="{n(-hw / 2 - 2)}" width="{n(0.07 * D)}" height="{n(hw + 4)}" rx="{n(0.02 * D)}" fill="{INK}"/>')
    fanp = closed_rounded([(Ls, -w0 / 2), (L, -w1 / 2), (L, w1 / 2), (Ls, w0 / 2)], [0.02 * D, 0.01 * D, 0.01 * D, 0.02 * D])
    o.append(f'<path d="{fanp}" fill="{INK if sil else BRASS}"/>')
    if not sil:
        for fr in (0.14, 0.32):
            x = Ls + fl * fr
            w = w0 + (w1 - w0) * fr
            o.append(f'<rect x="{n(x)}" y="{n(-w / 2 - 1)}" width="{n(0.034 * D)}" height="{n(w + 2)}" fill="{INK}"/>')
        for i in range(-3, 4):
            o.append(f'<path d="M{n(Ls + fl * 0.48)},{n(i * 0.016 * D)} L{n(L - 4)},{n(i * 0.042 * D)}" '
                     f'stroke="{BRASS_D}" stroke-width="{n(max(2.5, 0.011 * D))}" stroke-linecap="round"/>')
    o.append('</g>')
    return ''.join(o)


def body(look, C, D, f, tilt, pose, view='profile', ws=None, sil=False, reg=True):
    """Stick body under a head at C.  pose (world coords):
       spine=(lean_deg, bulge_D)  lean +: hip behind (towards -f); bulge +: C-curve bulges backwards
       arm_n/arm_f: dict(w=wrist target | grip=point on prop, bend=(hx,hy), straight, hand=deg, thumb, fist)
       leg_n/leg_f: dict(a=ankle target, bend=(hx,hy), straight, foot=deg)
       broom: dict(a, b, layer='behind'|'front'), apron=deg swing, apron_len, tails=deg, neck_lean
    Returns (layers dict, joints dict)."""
    k = D / 270.0
    ws = ws or dict(root=0.07 * D, tip=0.048 * D, sp0=0.08 * D, sp1=0.06 * D)
    limb, farc, skin = look['limb'], look['far'], look['skin']
    if sil:
        limb = farc = skin = INK
    NT, NB, ndir = neck_geom(C, D, f, tilt, view, pose.get('neck_lean', 10.0))
    Y = add(NB, mul(ndir, 0.075 * D))
    lean, bulge = pose.get('spine', (4.0, 0.06))
    Lc = 0.975 * D
    H = pose.get('hip') or add(Y, (-f * math.sin(math.radians(lean)) * Lc, math.cos(math.radians(lean)) * Lc))
    sd = unit(sub(H, Y))
    perp = (-sd[1], sd[0])           # rotate +90: for f=1 and a vertical spine this points to -x (back)
    if perp[0] * f > 0:
        perp = mul(perp, -1)          # perp now points BACK (towards -f)
    c1 = add(lerp(Y, H, 0.33), mul(perp, bulge * D * 1.3))
    c2 = add(lerp(Y, H, 0.70), mul(perp, bulge * D * 0.6))
    samp = [bez3(Y, c1, c2, H, i / 120) for i in range(121)]
    spine_len = sum(math.dist(samp[i], samp[i + 1]) for i in range(120))
    fwd = mul(perp, -1)
    sn, sf = SHOULDERS[view]
    hn, hf = HIPS[view]
    # shoulders along the yoke (perpendicular to the upper spine)
    up_dir = unit(sub(samp[6], samp[0]))
    yoke = (-up_dir[1], up_dir[0])
    if yoke[0] * f < 0:
        yoke = mul(yoke, -1)          # yoke points FORWARD
    if view == 'front':
        yoke = (up_dir[1] * f if f > 0 else up_dir[1], -up_dir[0]) if False else (up_dir[1], -up_dir[0])
        if yoke[0] * f < 0:
            yoke = mul(yoke, -1)
    S = {'arm_n': add(Y, mul(yoke, sn * D)), 'arm_f': add(add(Y, mul(yoke, sf * D)), (0, -0.01 * D))}
    HP = {'leg_n': add(H, (f * hn * D, 0)), 'leg_f': add(H, (f * hf * D, -0.005 * D))}
    J = dict(NT=NT, NB=NB, Y=Y, H=H, S=S, HP=HP, spine_len=spine_len, ndir=ndir, fwd=fwd, yoke=yoke)
    br = pose.get('broom')
    L = {}
    # -------------------------------- arms
    arms = {}
    for key in ('arm_f', 'arm_n'):
        spec = pose[key]
        Sx = S[key]
        a_len, b_len = 0.68 * D, 0.70 * D
        if 'grip' in spec:
            g = spec['grip']
            j, w = ik2(Sx, g, a_len, b_len, spec.get('bend', (-f, 0)), spec.get('straight', False))
            fd = unit(sub(w, j))
            g2 = add(g, mul(fd, -0.20 * D * 0.46))
            j, w = ik2(Sx, g2, a_len, b_len, spec.get('bend', (-f, 0)), spec.get('straight', False))
        elif 'dir' in spec:
            dv = (math.sin(math.radians(spec['dir'])), -math.cos(math.radians(spec['dir'])))
            j = add(Sx, mul(dv, a_len))
            d2 = spec['dir'] + spec.get('bend_deg', 0)
            dv2 = (math.sin(math.radians(d2)), -math.cos(math.radians(d2)))
            w = add(j, mul(dv2, b_len))
        else:
            j, w = ik2(Sx, spec['w'], a_len, b_len, spec.get('bend', (-f, 0)), spec.get('straight', False))
        col = farc if (key == 'arm_f' and view != 'front') else limb
        mcol = shade(skin, 0.12) if (key == 'arm_f' and view != 'front' and not sil) else skin
        wr, wt = ws['root'], ws['tip']
        wm = (wr + wt) / 2
        upper = tube([Sx, j], [wr, wm], col)
        fore = tube([j, w], [wm, wt], col)
        edge = ''
        if look.get('edge') and key == 'arm_n' and not sil:
            off = pose.get('edge_off', (-3 * f, -1))
            edge = tube([add(Sx, off), add(j, off), add(w, off)], [wr, wm, wt], look['edge'])
        hang = spec.get('hand', ang_of(sub(w, j)))
        grip = 'grip' in spec or spec.get('fist', False) or spec.get('grip_auto', False)
        mb, mt = mitten(w, hang, D, f, mcol, spec.get('thumb', -1), grip,
                        None if sil else (shade(look['cuff'], 0.12 if key == 'arm_f' else 0) if look.get('cuff') else None), wt)
        arms[key] = dict(upper=upper, fore=fore, edge=edge, mit=mb, thumb=mt)
        J[key] = (j, w)
        if reg:
            REG['limbs'].append((look['name'] + ':' + key, [Sx, j, w], [wr, wm, wt], col))
    # -------------------------------- legs
    legs = {}
    for key in ('leg_f', 'leg_n'):
        spec = pose[key]
        Hx = HP[key]
        j, a = ik2(Hx, spec['a'], 0.76 * D, 0.72 * D, spec.get('bend', (f, 0)), spec.get('straight', False))
        col = farc if (key == 'leg_f' and view != 'front') else limb
        wr, wt = ws['root'], ws['tip']
        wm = (wr + wt) / 2
        s = ''
        if look.get('edge') and key == 'leg_n' and not sil:
            off = pose.get('edge_off', (-3 * f, -1))
            s += tube([add(Hx, off), add(j, off), add(a, off)], [wr, wm, wt], look['edge'])
        s += tube([Hx, j, a], [wr, wm, wt], col)
        shin_dir = unit(sub(a, j))
        fs = foot_svg(look['feet'], a, f, spec.get('foot', 0), D, shin_dir, wt, view, far=(key == 'leg_f' and view != 'front'))
        if sil:
            fs = fs.replace(PALE, INK).replace(ZORI, INK).replace(WOOD_D, INK).replace(TERRA, INK).replace(shade(PALE, 0.12), INK).replace('#1A1815', INK)
        legs[key] = s + fs
        J[key] = (j, a)
        if reg:
            REG['limbs'].append((look['name'] + ':' + key, [Hx, j, a], [wr, wm, wt], col))
    # -------------------------------- spine + neck
    nseg = 12
    sp_pts = [samp[int(i * 120 / nseg)] for i in range(nseg + 1)]
    sp_w = [ws['sp0'] + (ws['sp1'] - ws['sp0']) * i / nseg for i in range(nseg + 1)]
    spine = tube([NB] + sp_pts, [ws['sp0']] + sp_w, limb)
    if reg:
        REG['limbs'].append((look['name'] + ':spine', sp_pts, sp_w, limb))
    nw = 0.17 * D
    neck = tube([NT, NB], [nw, nw], skin)
    if not sil:
        # flat 12%-darker chin shadow across the top of the visible neck
        top = lerp(NT, NB, 0.30)
        mid = lerp(NT, NB, 0.62)
        neck += tube([NT, mid], [nw, nw], shade(skin, 0.12)).replace('<circle', '<circle data-x="1"', 0)
        neck += f'<path d="M{pt(add(mid, mul((ndir[1], -ndir[0]), nw / 2)))} L{pt(add(mid, mul((-ndir[1], ndir[0]), nw / 2)))}" stroke="{shade(skin, 0.12)}" stroke-width="2"/>'
        neck = tube([NT, NB], [nw, nw], skin) + tube([NT, mid], [nw, nw * 0.98], shade(skin, 0.12))
    back, front, anchor = [], [], []
    # -------------------------------- hip prop
    if look['hip'] == 'apron':
        sw = pose.get('apron', 0)
        Lp = pose.get('apron_len', 0.62) * D
        if view == 'front':
            root = add(H, (0, -0.07 * D))
            wt_, wb_ = 0.30 * D, 0.40 * D
            ox = 0.0
        elif view == '34':
            root = add(H, (f * -0.02 * D, -0.07 * D))
            wt_, wb_ = 0.26 * D, 0.34 * D
            ox = 0.0
        else:
            root = add(H, (f * 0.06 * D, -0.075 * D))
            wt_, wb_ = 0.20 * D, 0.28 * D
            ox = 0.0

        def ap(x, y):
            return add(root, rotv((f * x, y), -f * sw))
        t0, t1 = ap(-wt_ / 2 + ox, 0), ap(wt_ / 2 + ox, 0)
        b0, b1 = ap(-wb_ / 2 + ox - 0.01 * D, Lp), ap(wb_ / 2 + ox - 0.01 * D, Lp)
        apron = f'<path d="{closed_rounded([t0, t1, b1, b0], [0.01 * D, 0.02 * D, 0.03 * D, 0.03 * D])}" fill="{INK if sil else SAGE}"/>'
        if not sil:
            m0, m1 = lerp(t0, b0, 0.45), lerp(t1, b1, 0.45)
            apron += f'<path d="M{pt(lerp(m0, m1, 0.2))} L{pt(lerp(m0, m1, 0.8))}" stroke="{SAGE_D}" stroke-width="{n(0.02 * D)}" stroke-linecap="round"/>'
        # navy waistband (costume colour at the hip) + back ties
        wb0 = add(H, (f * -0.13 * D, -0.085 * D)) if view != 'front' else add(H, (-0.17 * D, -0.08 * D))
        wb1 = add(H, (f * 0.15 * D, -0.072 * D)) if view != 'front' else add(H, (0.17 * D, -0.08 * D))
        band = f'<path d="M{pt(wb0)} L{pt(wb1)}" stroke="{INK if sil else NAVY_C}" stroke-width="{n(0.05 * D)}" stroke-linecap="round"/>'
        if view in ('profile', 'twist'):
            tie = pose.get('tie', 0)
            bk = add(wb0, (f * -0.01 * D, 0))
            bow = []
            for dl, ln in ((-10, 0.22), (14, 0.17)):
                e = add(bk, rotv((f * -0.02 * D, ln * D), f * (tie + dl)))
                bow.append(tube([bk, lerp(bk, e, 0.5), e], [0.03 * D, 0.03 * D, 0.026 * D], INK if sil else SAGE_D))
            bow.append(f'<ellipse cx="{n(bk[0] - f * 0.03 * D)}" cy="{n(bk[1])}" rx="{n(0.045 * D)}" ry="{n(0.028 * D)}" '
                       f'fill="{INK if sil else SAGE}" transform="rotate({n(-20 * f)},{n(bk[0] - f * 0.03 * D)},{n(bk[1])})"/>')
            back.append(''.join(bow))
        front.append(apron + band)
    elif look['hip'] == 'belt':
        lag = pose.get('tails', 0)
        kn = add(H, (f * 0.07 * D, -0.06 * D))
        fr = []
        fr.append(f'<path d="M{pt(add(H, (f * -0.10 * D, -0.085 * D)))} L{pt(add(H, (f * 0.10 * D, -0.075 * D)))}" stroke="{INK}" '
                  f'stroke-width="{n(0.055 * D)}" stroke-linecap="round"/>')
        for dl, ln in ((0, 0.42), (18, 0.34)):
            e = add(kn, rotv((0, ln * D), f * (lag + dl)))
            m = add(lerp(kn, e, 0.55), rotv((f * 0.025 * D, 0), f * lag))
            fr.append(tube([kn, m, e], [0.05 * D, 0.046 * D, 0.04 * D], INK))
            if not sil:
                s0 = lerp(m, e, 0.40)
                s1 = lerp(m, e, 0.56)
                td = unit(sub(e, m))
                nn = (-td[1] * 0.026 * D, td[0] * 0.026 * D)
                fr.append(f'<path d="{poly([add(s0, nn), add(s1, nn), sub(s1, nn), sub(s0, nn)])}" fill="{TERRA}"/>')
        fr.append(f'<rect x="{n(kn[0] - 0.05 * D)}" y="{n(kn[1] - 0.04 * D)}" width="{n(0.10 * D)}" height="{n(0.08 * D)}" rx="{n(0.025 * D)}" fill="{INK}"/>')
        front.append(''.join(fr))
    # -------------------------------- neck anchor (its corners = shoulder points)
    if look['anchor'] == 'eri':
        navy = INK if sil else NAVY_C
        pale = INK if sil else PALE
        rr = 0.012 * D
        if view in ('profile', 'twist'):
            # hanten collar seen from the side: a flat flap from the nape over the shoulder to a point on
            # the chest (squared, not a limb), juban strip along the open front edge
            def P(x, y):
                return add(NB, (f * x * D, y * D))
            nape, throat, chest, backb = P(-0.20, -0.06), P(0.075, -0.02), P(0.215, 0.36), P(-0.09, 0.16)
            anchor.append(f'<path d="{closed_rounded([add(throat, (f * 0.04 * D, -0.012 * D)), add(chest, (f * 0.035 * D, 0.01 * D)), chest, throat], rr)}" fill="{pale}"/>')
            anchor.append(f'<path d="{closed_rounded([nape, throat, chest, backb], [rr * 2, rr, rr * 0.5, rr * 2])}" fill="{navy}"/>')
        else:
            # front / 3/4: navy bands from the two shoulder points to the neck, crossing at the chest
            # over a pale juban triangle (reads as a jacket neckline, outer corners = shoulder points)
            shift = 0.0 if view == 'front' else f * 0.06 * D
            sx = {'front': (0.27, 0.27), '34': (0.27, 0.17)}[view]
            yk = J['yoke']

            def Q(x, y):
                return add(add(NB, (shift, 0)), add(mul(yk, x * D), (0, y * D)))
            xp = Q(0.0, 0.40)
            tri = [Q(-0.085, 0.0), Q(0.085, 0.0), xp]
            anchor.append(f'<path d="{closed_rounded(tri, rr)}" fill="{pale}"/>')
            # back of the collar (behind the neck)
            anchor.append(f'<path d="{closed_rounded([Q(-0.13, 0.01), Q(-0.10, -0.06), Q(0.10, -0.06), Q(0.13, 0.01)], rr)}" fill="{shade(navy, 0.15) if not sil else INK}"/>')
            for side in (-1, 1):       # side +1 band drawn last (on top)
                so = sx[0] if side < 0 else sx[1]
                outer = Q(side * so, 0.075)
                neck_o = Q(side * 0.20, 0.0)
                neck_i = Q(side * 0.085, -0.02)
                inner_b = add(xp, mul(yk, -side * 0.035 * D))
                outer_b = add(Q(side * 0.075, 0.47), (0, 0))
                band = [outer, neck_o, neck_i, inner_b, outer_b]
                anchor.append(f'<path d="{closed_rounded(band, [rr * 2, rr * 3, rr, rr * 0.5, rr])}" fill="{navy}"/>')
                if not sil:
                    anchor.append(f'<path d="M{pt(lerp(neck_i, inner_b, 0.06))} L{pt(lerp(neck_i, inner_b, 0.94))}" stroke="{PALE}" '
                                  f'stroke-width="{n(0.022 * D)}" stroke-linecap="round"/>')
    elif look['anchor'] == 'tenugui':
        tw = 0.10 * D
        b0 = add(NB, (f * -0.18 * D, -0.03 * D))
        b1 = add(NB, (f * 0.13 * D, 0.035 * D))
        col = INK if sil else PALE
        anchor.append(tube([b0, lerp(b0, b1, 0.5), b1], [tw, tw, tw * 0.9], col))
        kn = add(b1, (f * 0.01 * D, 0.01 * D))
        lag = pose.get('tie_lag', 0)
        for dl, ln in ((-4, 0.15), (14, 0.12)):
            e = add(kn, rotv((f * 0.0 * D, ln * D), f * (dl + lag)))
            anchor.append(tube([kn, e], [0.055 * D, 0.05 * D], col))
        anchor.append(f'<circle cx="{n(kn[0])}" cy="{n(kn[1])}" r="{n(0.045 * D)}" fill="{col}"/>')
        if not sil:
            anchor.append(f'<circle cx="{n(kn[0])}" cy="{n(kn[1])}" r="{n(0.022 * D)}" fill="{TERRA}"/>')
        # tasuki cord: X across the spine below the yoke
        q = samp[34]
        cc = INK if sil else PALE
        back.append(f'<path d="M{pt(add(q, (f * 0.11 * D, -0.12 * D)))} L{pt(add(q, (f * -0.11 * D, 0.12 * D)))}" stroke="{shade(cc, 0.2) if not sil else INK}" '
                    f'stroke-width="{n(0.026 * D)}" stroke-linecap="round"/>')
        front.append(f'<path d="M{pt(add(q, (f * -0.12 * D, -0.11 * D)))} L{pt(add(q, (f * 0.12 * D, 0.12 * D)))}" stroke="{cc}" '
                     f'stroke-width="{n(0.03 * D)}" stroke-linecap="round"/>')
    prop = ''
    if pose.get('broom_auto'):
        key, t = pose['broom_auto'][:2]
        jj, ww = J[key]
        hd = pose[key].get('hand')
        mdir = (math.cos(math.radians(hd)), math.sin(math.radians(hd))) if hd is not None else unit(sub(ww, jj))
        mc = add(ww, mul(mdir, 0.10 * D))
        Lb = 2.78 * D
        if t == 'down':
            fl = pose['broom_auto'][2]
            br = dict(a=(mc[0], fl - Lb), b=(mc[0], fl), layer='front')
        else:
            br = dict(a=add(mc, (0, t * Lb)), b=add(mc, (0, -(1 - t) * Lb)), layer='front')
        pose['broom'] = br
    if br:
        prop = broom_svg(br['a'], br['b'], D, br.get('fan', 0.40), sil)
    L.update(far_leg=legs['leg_f'], far_arm=arms['arm_f']['upper'] + arms['arm_f']['fore'] + arms['arm_f']['mit'],
             far_thumb=arms['arm_f']['thumb'], spine=spine, neck=neck, back=''.join(back), front=''.join(front),
             anchor=''.join(anchor), near_leg=legs['leg_n'], near_upper=arms['arm_n']['edge'] + arms['arm_n']['upper'],
             near_fore=arms['arm_n']['fore'] + arms['arm_n']['mit'], near_thumb=arms['arm_n']['thumb'], prop=prop)
    J['broom'] = br
    return L, J


def character(p, look, C, D, f, tilt, uid, pose, view='profile', ws=None, shadow='', marks='', sil=False, head_view=None):
    L, J = body(look, C, D, f, tilt, pose, view, ws, sil)
    layer = pose.get('broom', {}).get('layer', 'front') if pose.get('broom') else None
    o = [shadow]
    o.append(L['far_leg'])
    o.append(L['back'])
    o.append(L['far_arm'])
    if layer == 'behind':
        o.append(L['prop'])
        o.append(L['far_thumb'])
    o.append(L['spine'])
    o.append(L['neck'])
    o.append(L['near_leg'])
    o.append(L['front'])
    o.append(L['near_upper'])
    o.append(L['anchor'])
    o.append(L['near_fore'])
    hp = dict(p)
    o.append(head(hp, C, D, f, tilt, uid, sil))
    if layer == 'front':
        o.append(L['prop'])
        o.append(L['far_thumb'])
    elif layer is None:
        o.append(L['far_thumb'])
    o.append(L['near_thumb'])
    o.append(marks)
    return ''.join(o), J


def dummy_svg(piv, ang, s=1.0, cord=26, arms=((-1, 208, 96), (1, -28, 96)), opacity=1.0, sil=False):
    """Faceless wooden capsule on a cord from a brass ring. piv = bottom of the ring; ang + swings right."""
    op = f' opacity="{opacity}"' if opacity < 1 else ''
    o = [f'<g transform="translate({pt(piv)}) rotate({n(-ang)}) scale({n(s)})"{op}>']
    o.append(f'<path d="M0,-4 L0,{cord + 8}" stroke="{INK}" stroke-width="{n(7 / s)}" stroke-linecap="round"/>')
    y0 = cord
    for sx, phi, ry in arms:
        r0 = (sx * 50, y0 + ry)
        e = add(r0, (74 * math.cos(math.radians(phi)), 74 * math.sin(math.radians(phi))))
        o.append(f'<path d="M{pt(r0)} L{pt(e)}" stroke="{WOOD_D}" stroke-width="{n(22 / s)}" stroke-linecap="round"/>')
    o.append(f'<rect x="-70" y="{y0}" width="140" height="300" rx="70" fill="{WOOD}"/>')
    o.append(f'<rect x="-70" y="{y0 + 70}" width="140" height="12" fill="{WOOD_D}"/>')
    o.append(f'<rect x="-70" y="{y0 + 236}" width="140" height="10" fill="{WOOD_D}"/>')
    for gx, a0, a1 in ((-34, 104, 214), (6, 120, 226), (34, 98, 182)):
        o.append(f'<path d="M{gx},{y0 + a0} Q{gx + 9},{y0 + (a0 + a1) / 2} {gx},{y0 + a1}" fill="none" '
                 f'stroke="{WOOD_D}" stroke-width="5" stroke-linecap="round"/>')
    o.append(f'<circle cx="0" cy="{y0 + 4}" r="10" fill="none" stroke="{BRASS}" stroke-width="6"/>')
    o.append('</g>')
    return ''.join(o)


def dummy_arm_tip(piv, ang, s, cord, arm):
    sx, phi, ry = arm
    r0 = (sx * 50, cord + ry)
    e = add(r0, (74 * math.cos(math.radians(phi)), 74 * math.sin(math.radians(phi))))
    q = rotv(mul(e, s), -ang)
    return add(piv, q)


def dotted(d, color, w=6, dash=(2, 14), extra=''):
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" '
            f'stroke-dasharray="{dash[0]} {dash[1]}"{extra}/>')


def arc_d(c, r, a0, a1):
    """Arc around c from angle a0 to a1 (deg, screen coords)."""
    p0 = add(c, (r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0))))
    p1 = add(c, (r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1))))
    sweep = 1 if a1 > a0 else 0
    large = 1 if abs(a1 - a0) > 180 else 0
    return f"M{pt(p0)} A{n(r)},{n(r)} 0 {large} {sweep} {pt(p1)}"



# =====================================================================================
# SCENE (1080 x 1920): rooftop dojo at dusk -- "proxy war under the moon"
# =====================================================================================
SC_FLOOR = 1532        # sole line
SC_D = 270
RAIL_Y = 330


def sol_scene_face():
    return face(eye=dict(open=0.45, tilt=0, px=0.30, py=0.05), brow=dict(raise_=-0.015, tilt=0), mouth='a')


def snoot_scene_face():
    return face(skin=SKIN_SNOOT, hair='bun', tie=TERRA, nose='ski', nose_state='flare', nose_up=8, nose_always_up=True,
                my=0.79, eye=dict(open=0.50, tilt=16, px=0.12), brow=dict(raise_=-0.07, tilt=25), mouth='d',
                marks=['snort'], crow=True, stubble=False)


def gran_front_face():
    return face(view='front', skin=SKIN_GRAN, hair='grey_bun', eye=dict(open=0.40, px=0.0, tilt=0), brow=dict(raise_=-0.01),
                stubble=False, jowls=True, wrinkles=True)


def nose_tip_world(p, C, D, f, tilt):
    _, _, T, _ = nose_profile(p, D)
    return to_world(T, C, f, tilt)


def scene_svg(sil=False, bg_only=False):
    REG['limbs'].clear()
    REG['heads'].clear()
    Wc, Hc = 1080, 1920
    D = SC_D
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hc}" viewBox="0 0 {Wc} {Hc}">']
    if sil:
        o.append(f'<rect width="{Wc}" height="{Hc}" fill="#FFFFFF"/>')
    else:
        o.append(f'<rect width="{Wc}" height="{Hc}" fill="{DUSK}"/>')
        for y0, col in ((560, '#4C6580'), (720, '#62778F'), (860, '#8192A7'), (1010, '#93A0B0')):
            o.append(f'<rect y="{y0}" width="{Wc}" height="{1210 - y0}" fill="{col}"/>')
        roofs = "M0,1205 L0,1118 L46,1118 L36,1104 Q84,1096 124,1078 Q156,1092 182,1100 L174,1110 L194,1110 L194,1205 Z"
        o.append(f'<path d="{roofs}" fill="{ROOF}"/>')
        o.append(f'<circle cx="540" cy="1050" r="410" fill="{MOON}"/>')
        # plank floor + front band
        o.append(f'<rect y="1200" width="{Wc}" height="375" fill="{SAND}"/>')
        o.append(f'<rect y="1200" width="{Wc}" height="12" fill="{PLANK}"/>')
        for y in (1236, 1278, 1330, 1394, 1472):
            o.append(f'<rect y="{y}" width="{Wc}" height="4" fill="{PLANK}"/>')
        for x, y0, y1 in ((214, 1212, 1278), (640, 1278, 1394), (420, 1394, 1575), (900, 1212, 1330), (760, 1472, 1575)):
            o.append(f'<rect x="{x}" y="{y0}" width="4" height="{y1 - y0}" fill="{PLANK}"/>')
        o.append(f'<rect y="1575" width="{Wc}" height="{Hc - 1575}" fill="{FLOOR_D}"/>')
        o.append(f'<rect y="1575" width="{Wc}" height="10" fill="{shade(FLOOR_D, 0.10)}"/>')
        # neighbour's tea-house wall + lit window (witness) above the dojo eave
        o.append(f'<path d="M780,0 L1080,0 L1080,230 L780,230 Z" fill="{ROOF}"/>')
        o.append(f'<path d="M760,0 L1080,0 L1080,18 L760,18 Z" fill="{INK}"/>')
        o.append(f'<rect x="812" y="34" width="196" height="196" fill="{LAMP}"/>')
        for x in (861, 959):
            o.append(f'<rect x="{x}" y="34" width="4" height="196" fill="{shade(LAMP, 0.10)}"/>')
        o.append(f'<rect x="812" y="112" width="196" height="4" fill="{shade(LAMP, 0.10)}"/>')
        # eave beam + rail with sliding brass rings
        o.append(f'<rect y="226" width="{Wc}" height="34" fill="{INK}"/>')
        o.append(f'<rect y="{RAIL_Y - 11}" width="{Wc}" height="22" fill="{INK}"/>')
        o.append(f'<rect x="36" y="{RAIL_Y - 22}" width="20" height="44" rx="4" fill="{INK}"/>')   # ring stop
        for hx in (300, 1044):
            o.append(f'<rect x="{hx - 5}" y="260" width="10" height="{RAIL_Y - 270}" fill="{INK}"/>')
        for rx in (300, 560, 780):
            o.append(f'<circle cx="{rx}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    if not sil:
        # grandma in the window: frontal, deadpan (head D 170)
        gC = (910, 128)
        gD = 170
        gneck = tube([(gC[0], gC[1] + 70), (gC[0], gC[1] + 100)], [0.17 * gD, 0.17 * gD], SKIN_GRAN)
        o.append(f'<g>')
        o.append(f'<path d="M{gC[0] - 92},230 Q{gC[0] - 80},{gC[1] + 96} {gC[0]},{gC[1] + 92} Q{gC[0] + 80},{gC[1] + 96} {gC[0] + 92},230 Z" fill="{PLUM}"/>')
        o.append(gneck)
        o.append(f'<path d="M{gC[0] - 44},{gC[1] + 94} L{gC[0]},230 L{gC[0] + 44},{gC[1] + 94}" fill="none" stroke="{PALE}" stroke-width="12" stroke-linejoin="round"/>')
        o.append(head(gran_front_face(), gC, gD, 1, 0, 'gran'))
        o.append('</g>')
        o.append(f'<rect x="800" y="222" width="220" height="10" fill="{INK}"/>')
    if bg_only:
        o.append('</svg>')
        return '\n'.join(o), {}

    # ---------------- heads (fixed, nose to nose)
    sol = sol_scene_face()
    snoot = snoot_scene_face()
    Cs = (360, 680)
    tip_s = nose_tip_world(sol, Cs, D, 1, 0)
    sn_tilt = 4
    _, _, Tn, _ = nose_profile(snoot, D)
    tw = to_world(Tn, (0, 0), -1, sn_tilt)
    gap = 11
    Cn = (tip_s[0] + gap - tw[0], tip_s[1] - 6 - tw[1])
    FL = SC_FLOOR
    ah = 0.07 * D

    # ---------------- ring path along the rail (zip from the right ring to the left ring)
    marks = []
    zc = PALE
    if not sil:
        marks.append(dotted(f"M990,{RAIL_Y + 30} L150,{RAIL_Y + 30}", zc, 6, (2, 16)))
        for gx in (760, 470):
            marks.append(f'<circle cx="{gx}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7" opacity="0.5"/>')
        for dy, x0, x1 in ((-12, 124, 176), (0, 130, 196), (12, 124, 170)):
            marks.append(f'<path d="M{x0},{RAIL_Y + 30 + dy} L{x1},{RAIL_Y + 30 + dy}" stroke="{zc}" stroke-width="5" stroke-linecap="round"/>')
    # ---------------- ghost dummy at the kick point (right) + its empty ring
    gpiv = (1030, RAIL_Y + 46)
    if not sil:
        o.append(f'<circle cx="{gpiv[0]}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7" opacity="0.5"/>')
        o.append(dummy_svg(gpiv, 0, 0.78, cord=(738 - gpiv[1]) / 0.78, arms=((-1, 200, 96), (1, -20, 96)), opacity=0.5))

    # ---------------- SOL: twisted 12 deg away, broom behind his back, bristles up past the rear shoulder
    bro_b = (160, 498)
    u = unit(sub((295, 1225), bro_b))
    bro_a = add(bro_b, mul(u, 2.78 * D))
    sol_pose = dict(
        spine=(4.0, 0.09),
        leg_n=dict(a=(452, FL - ah), bend=(1, 0), foot=0),
        leg_f=dict(a=(214, FL - ah), bend=(1, 0), foot=0),
        broom=dict(a=bro_a, b=bro_b, layer='behind'),
        arm_n=dict(grip=lerp(bro_a, bro_b, 0.012), bend=(-1, 0.35), thumb=-1),
        arm_f=dict(grip=lerp(bro_a, bro_b, 0.075), bend=(-1, -0.15), thumb=-1),
        apron=9, tie=-18,
    )
    sh_s = '' if sil else f'<ellipse cx="335" cy="{FL + 3}" rx="170" ry="13" fill="{PLANK}"/>'
    s_svg, sJ = character(sol, LOOK_SOL, Cs, D, 1, 0, 'sol', sol_pose, view='twist', shadow=sh_s, sil=sil)

    # ---------------- the solid dummy behind Sol: peg arm meets the bristles (ting)
    dpiv = (64, RAIL_Y + 46)
    dang = 3
    ds = 0.62
    dcord = 18
    contact = (bro_b[0] - 34, bro_b[1] - 2)
    q = mul(rotv(sub(contact, dpiv), dang), 1 / ds)
    ry = q[1] - dcord - 40
    r0 = (50, dcord + ry)
    phi = math.degrees(math.atan2(q[1] - r0[1], q[0] - r0[0]))
    dm = dummy_svg(dpiv, dang, ds, cord=dcord, arms=((-1, 200, 120), (1, phi, ry)), sil=sil)

    # ---------------- SNOOT: upright, leaning in, rear hook kick away from Sol into the hanging dummy
    sn_pose = dict(
        spine=(2.0, 0.03),
        leg_f=dict(a=(Cn[0] + 32, FL - ah), bend=(-1, 0), foot=0),
        leg_n=dict(a=(990, 872), bend=(1, 0.25), foot=-118),
        arm_n=dict(w=(Cn[0] - 8, 1222), bend=(1, 0), hand=92, thumb=1, fist=True),
        arm_f=dict(w=(Cn[0] + 22, 1212), bend=(1, 0), hand=94, thumb=1, fist=True),
        tails=-14, tie_lag=-6, edge_off=(-4, -2),
    )
    sh_n = '' if sil else f'<ellipse cx="{n(Cn[0] + 40)}" cy="{FL + 3}" rx="96" ry="12" fill="{PLANK}"/>'
    n_svg, nJ = character(snoot, LOOK_SNOOT, Cn, D, -1, sn_tilt, 'snoot', sn_pose, view='profile', shadow=sh_n, sil=sil)

    if not sil:
        o.append(dm)
    o.append(s_svg)
    o.append(n_svg)
    if not sil:
        # kick path: dotted arc up the right edge + thrust ticks behind the heel
        foot = nJ['leg_n'][1]
        knee = nJ['leg_n'][0]
        marks.append(dotted(f"M1012,1180 Q1074,1040 {n(foot[0] + 30)},{n(foot[1] + 16)}", PALE, 7, (2, 17)))
        # ting where the bristles meet the peg arm
        marks.append(f'<path d="{star4(contact[0], contact[1] - 6, 50, 11, 0)}" fill="{PALE}"/>')
        marks.append(f'<path d="{star4(contact[0], contact[1] - 6, 22, 5, 45)}" fill="{INK}"/>')
        # bristle swing path (came up from behind/below)
        hands = sJ['arm_n'][1]
        R2 = math.dist(hands, bro_b)
        a1 = ang_of(sub(bro_b, hands))
        marks.append(dotted(arc_d(hands, R2 + 8, a1 + 4, a1 + 13), PALE, 7, (2, 17)))
        # dummy snapping back to its ring stop: motion arcs on the trailing side
        for r, a0_, a1_ in ((212, 64, 80), (238, 66, 80)):
            marks.append(f'<path d="{arc_d(dpiv, r, a0_, a1_)}" fill="none" stroke="{PALE}" stroke-width="6" stroke-linecap="round"/>')
        o.append(f'<circle cx="{dpiv[0]}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    o.append(''.join(marks))
    o.append('</svg>')
    info = dict(Cs=Cs, Cn=tuple(round(v) for v in Cn), sol_spine=round(sJ['spine_len'] / D, 3), sn_spine=round(nJ['spine_len'] / D, 3),
                sol_hip=tuple(round(v) for v in sJ['H']), sn_hip=tuple(round(v) for v in nJ['H']),
                sn_knee=tuple(round(v) for v in nJ['leg_n'][0]), sn_foot=tuple(round(v) for v in nJ['leg_n'][1]),
                sol_ankles=[tuple(round(v) for v in sJ[k][1]) for k in ('leg_n', 'leg_f')],
                sn_ankle=tuple(round(v) for v in nJ['leg_f'][1]), tip_s=tuple(round(v) for v in tip_s),
                tip_n=tuple(round(v) for v in nose_tip_world(snoot, Cn, D, -1, sn_tilt)))
    return '\n'.join(o), info


# =====================================================================================
# POSES SHEET (1080 x 1080): Sol x3
# =====================================================================================
PS_D = 200
PS_FLOOR = 990


def poses_svg(sil=False, color_sil=False):
    REG['limbs'].clear()
    D = PS_D
    FL = PS_FLOOR
    ah = 0.07 * D
    ws = dict(root=15, tip=13, sp0=16, sp1=13)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">']
    if sil:
        o.append('<rect width="1080" height="1080" fill="#FFFFFF"/>')
    else:
        o.append(f'<rect width="1080" height="1080" fill="{SAND}"/>')
        for cx, cy, r in ((190, 520, 168), (540, 520, 168), (878, 430, 168)):
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PALE}"/>')
        o.append(f'<rect y="{FL}" width="1080" height="{1080 - FL}" fill="{PLANK}"/>')
        o.append(f'<rect y="{FL}" width="1080" height="6" fill="{FLOOR_D}"/>')
        for y in (FL + 34, FL + 64):
            o.append(f'<rect y="{y}" width="1080" height="4" fill="{FLOOR_D}"/>')
    figs = []

    def wrap(svg, idx):
        if color_sil:
            col = ['#E01010', '#10A010', '#1010E0'][idx]
            return f'<g filter="url(#solid{idx})">{svg}</g>', col
        return svg, None

    # (1) READY STANCE -- strict profile, broom upright like a staff in the front mitten, rear mitten on the hip
    p1 = face(eye=dict(open=0.70, px=0.18), mouth='a')
    C1 = (175, 350)
    b1a, b1b = (268, 434), (268, FL + 1)
    pose1 = dict(
        spine=(5.0, 0.10),
        leg_f=dict(a=(146, FL - ah), bend=(1, 0), foot=0),
        leg_n=dict(a=(186, FL - ah), bend=(1, 0), foot=0),
        broom=dict(a=b1a, b=b1b, layer='front'),
        arm_n=dict(grip=(268, 668), bend=(0.2, 1), thumb=-1),
        arm_f=dict(w=(118, 704), bend=(-1, -0.6), hand=70, thumb=1, fist=True),
        apron=0, tie=0,
    )
    sh1 = '' if sil else f'<ellipse cx="200" cy="{FL + 3}" rx="110" ry="9" fill="{FLOOR_D}"/>'
    s1, J1 = character(p1, LOOK_SOL, C1, D, 1, 0, 'p1', pose1, 'profile', ws, sh1, sil=sil)

    # (2) SIGNATURE: BEHIND-THE-BACK PARRY -- head forward and still, torso twisted 12 deg away,
    #     broom behind the back, bristles above the rear shoulder and higher than the topknot.
    p2 = face(eye=dict(kind='arc'), brow=dict(raise_=0.05, tilt=-8, arch=0.02), nose_state='up', nose_up=8, mouth='c')
    C2 = (540, 352)
    b2b = (366, 200)
    u2 = unit(sub((476, 770), b2b))
    b2a = add(b2b, mul(u2, 2.78 * D))
    pose2 = dict(
        spine=(9.0, 0.06),
        leg_f=dict(a=(522, FL - ah), bend=(1, 0), foot=0),
        leg_n=dict(a=(346, 806), bend=(0.1, 1), foot=-70),
        broom=dict(a=b2a, b=b2b, layer='behind'),
        arm_n=dict(grip=lerp(b2a, b2b, 0.015), bend=(-1, 0.35), thumb=-1),
        arm_f=dict(grip=lerp(b2a, b2b, 0.085), bend=(-1, -0.15), thumb=-1),
        apron=48, apron_len=0.58, tie=-60,
    )
    sh2 = '' if sil else f'<ellipse cx="520" cy="{FL + 3}" rx="70" ry="8" fill="{FLOOR_D}"/>'
    s2, J2 = character(p2, LOOK_SOL, C2, D, 1, 0, 'p2', pose2, 'twist', ws, sh2, sil=sil)

    # (3) BIG REACTION: BACK LEAP -- turns to camera mid-leap: front view, arms flung straight up in a V,
    #     broom gripped high and vertical in one fist, knees up, apron flipped.
    p3 = face(view='front', eye=dict(kind='circle', d=0.30, px=0.0, py=0.0), brow=dict(raise_=0.07, tilt=-10), mouth='o')
    C3 = (846, 286)
    t3 = -8
    pose3 = dict(
        spine=(-8.0, 0.0), neck_lean=0,
        leg_f=dict(a=(878, 818), bend=(-1, -0.25), foot=-14),
        leg_n=dict(a=(954, 808), bend=(1, -0.25), foot=12),
        arm_f=dict(dir=-38, thumb=1, fist=True, hand=-128),
        arm_n=dict(dir=22, thumb=-1, fist=True, hand=-68),
        broom_auto=('arm_n', 0.80),
        apron=-8, apron_len=0.40,
    )
    sh3 = '' if sil else f'<ellipse cx="884" cy="{FL + 3}" rx="64" ry="7" fill="{FLOOR_D}"/>'
    s3, J3 = character(p3, LOOK_SOL, C3, D, 1, t3, 'p3', pose3, 'front', ws, sh3, sil=sil)

    defs = ''
    if color_sil:
        defs = '<defs>' + ''.join(
            f'<filter id="solid{i}"><feFlood flood-color="{c}"/><feComposite in2="SourceAlpha" operator="in"/></filter>'
            for i, c in enumerate(['#E01010', '#10A010', '#1010E0'])) + '</defs>'
        o.insert(1, defs)
        s1 = f'<g filter="url(#solid0)">{s1}</g>'
        s2 = f'<g filter="url(#solid1)">{s2}</g>'
        s3 = f'<g filter="url(#solid2)">{s3}</g>'
    o.append(s1)
    o.append(s2)
    if not sil:
        gl = (b2b[0] - 4, b2b[1] - 6)
        o.append(f'<path d="{star4(gl[0], gl[1], 42, 10, 0)}" fill="{PALE}"/>')
        o.append(f'<path d="{star4(gl[0], gl[1], 20, 5, 45)}" fill="{INK}"/>')
        hands = J2['arm_n'][1]
        R2 = math.dist(hands, b2b)
        a1 = ang_of(sub(b2b, hands))
        o.append(dotted(arc_d(hands, R2 + 6, a1 + 4, a1 + 13), DUSK_D, 6, (2, 14)))
    o.append(s3)
    if not sil:
        # emanata round the head (3), dust puff + speed lines where he took off
        for ang in (-150 + t3, -90 + t3, -30 + t3):
            a = math.radians(ang)
            c = (C3[0], C3[1] - 0.05 * D)
            p0 = add(c, (0.66 * D * math.cos(a), 0.66 * D * math.sin(a)))
            p1 = add(c, (0.80 * D * math.cos(a), 0.80 * D * math.sin(a)))
            o.append(f'<path d="M{pt(p0)} L{pt(p1)}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>')
        for cx, cy, r in ((868, 974, 15), (896, 979, 11), (842, 979, 10), (922, 982, 8)):
            o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{FLOOR_D}"/>')
        for y, x0, x1 in ((900, 820, 836), (930, 860, 868), (900, 1000, 984)):
            o.append(f'<path d="M{x0},{y} L{x1},{y + 40}" stroke="{DUSK_D}" stroke-width="5" stroke-linecap="round"/>')
    o.append('</svg>')
    def seg_dist(p, a, b):
        ab = sub(b, a)
        t = max(0, min(1, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / (ab[0] ** 2 + ab[1] ** 2)))
        return math.dist(p, add(a, mul(ab, t)))
    clr = {}
    for key in ('arm_n', 'arm_f'):
        S_ = J3['S'][key]
        w_ = J3[key][1]
        d_skull = seg_dist(C3, S_, w_) - D / 2 - ws['root'] / 2
        side = 1 if key == 'arm_n' else -1
        ear = to_world((side * (D / 2 + 0.005 * D), 0.02 * D), C3, 1, t3)
        d_ear = seg_dist(ear, S_, w_) - 0.066 * D - ws['root'] / 2
        clr[key] = (round(d_skull / D, 3), round(d_ear / D, 3), round(math.degrees(math.atan2(w_[0] - S_[0], S_[1] - w_[1])), 1))
    info = dict(clear=clr, sp1=round(J1['spine_len'] / D, 3), sp2=round(J2['spine_len'] / D, 3), sp3=round(J3['spine_len'] / D, 3),
                ank1=[tuple(round(v) for v in J1[k][1]) for k in ('leg_n', 'leg_f')],
                ank2=tuple(round(v) for v in J2['leg_f'][1]))
    return '\n'.join(o), info


# =====================================================================================
# LINEUP (540 x 1080): Sol alone, relaxed ready stance, 3/4 toward the viewer's left,
# feet on y=1010, exactly 900 px from soles to the top of the head (topknot included)
# =====================================================================================
def lineup_svg(sil=False):
    REG['limbs'].clear()
    D = 240.0
    f = -1
    C = (290.0, 300.0)
    tilt = -3
    p = face(view='34', eye=dict(open=0.56, px=-0.04, py=0.05), brow=dict(raise_=-0.01, tilt=-3), smirk=0.022)
    FL0 = C[1] + 3.16 * D
    ah = 0.07 * D
    pose = dict(
        spine=(3.0, 0.05),
        leg_f=dict(a=(C[0] - 0.22 * D, FL0 - ah), bend=(-1, 0.1), foot=-6),
        leg_n=dict(a=(C[0] + 0.20 * D, FL0 - ah), bend=(-0.6, 0), foot=8),
        broom_auto=('arm_f', 'down', FL0 + 1),
        arm_f=dict(dir=219, bend_deg=-12, thumb=1, grip_auto=True, hand=180),
        arm_n=dict(w=(C[0] + 0.10 * D, C[1] + 1.78 * D), bend=(1, -0.3), hand=-110, thumb=-1, fist=True),
        apron=-3,
    )
    fig, J = character(p, LOOK_SOL, C, D, f, tilt, 'lu', pose, '34', None,
                       '' if sil else f'<ellipse cx="{n(C[0] - 0.2 * D)}" cy="{n(FL0 + 3)}" rx="{n(0.9 * D)}" ry="{n(0.06 * D)}" fill="#D9D4CB"/>', sil=sil)
    top = topknot_top(p, C, D, f, tilt)
    sole = max(J['leg_n'][1][1], J['leg_f'][1][1]) + ah
    h = sole - top
    sc = 900.0 / h
    tx = 270 - sc * C[0] + 0.14 * D * sc
    ty = 1010 - sc * sole
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="1080" viewBox="0 0 540 1080">']
    o.append(f'<rect width="540" height="1080" fill="{"#FFFFFF" if sil else "#EDEAE4"}"/>')
    o.append(f'<g transform="translate({n(tx)},{n(ty)}) scale({sc:.5f})">{fig}</g>')
    o.append('</svg>')
    return '\n'.join(o), dict(scale=round(sc, 4), D_eff=round(D * sc, 1), top=round(ty + sc * top, 1), sole=round(ty + sc * sole, 1),
                              spine=round(J['spine_len'] / D, 3))


# =====================================================================================
# HEADS SHEET (reference): the face system on the circle
# =====================================================================================
def heads_svg():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">']
    o.append(f'<rect width="1080" height="1080" fill="{SAND}"/>')
    D = 200
    cells = [
        (face(), 'neutral'),
        (face(eye=dict(open=0.45, px=0.30), brow=dict(raise_=-0.02)), 'cool'),
        (face(eye=dict(kind='arc'), brow=dict(raise_=0.05, tilt=-8, arch=0.02), nose_state='up', nose_up=8, mouth='c'), 'wink'),
        (face(eye=dict(kind='circle', d=0.39, px=0.0, py=0.0), brow=dict(raise_=0.12, tilt=-10), mouth='b', jaw=0.03, marks=['emanata']), 'surprise'),
        (face(eye=dict(open=0.5, tilt=18, px=0.12), brow=dict(raise_=-0.06, tilt=25), mouth='d', nose_state='flare', marks=['snort']), 'furious'),
        (face(eye=dict(open=1.0, ghosts=True, px=0.0), brow=dict(raise_=0.06, tilt=-14), mouth='e', marks=['sweat']), 'nervous'),
        (face(eye=dict(open=0.4, tilt=-6, px=0.05, py=0.2), brow=dict(raise_=-0.01, tilt=-6), mouth='f'), 'sulk'),
        (face(skin=SKIN_SNOOT, hair='bun', tie=TERRA, nose='ski', nose_state='flare', nose_up=8, nose_always_up=True, my=0.79,
              eye=dict(open=0.5, tilt=16, px=0.10), brow=dict(raise_=-0.07, tilt=25), mouth='d', marks=['snort'], crow=True, stubble=False), 'snoot'),
        (face(view='34', eye=dict(open=0.58, px=-0.05), brow=dict(raise_=-0.01, tilt=-3), smirk=0.025), '34'),
        (face(view='front', eye=dict(open=0.55, px=0.0), smirk=0.0), 'front'),
        (face(view='front', skin=SKIN_GRAN, hair='grey_bun', eye=dict(open=0.42, px=0.0, tilt=0), brow=dict(raise_=-0.01), stubble=False,
              jowls=True, wrinkles=True), 'gran'),
        (face(skin=SKIN_GRAN, hair='grey_bun', nose='tri', eye=dict(open=0.45, px=0.2), stubble=False, mouth='f'), 'granP'),
    ]
    for i, (p, nm) in enumerate(cells):
        cx = 135 + (i % 4) * 270
        cy = 160 + (i // 4) * 340
        Dd = D if nm not in ('gran', 'granP') else 170
        o.append(head(p, (cx, cy), Dd, 1, 0, f'h{i}'))
        o.append(head(p, (cx, cy + 0), Dd, 1, 0, f'hs{i}', sil=True).replace('<g transform="translate(', '<g opacity="1" transform="translate(%s,' % 0 if False else '<g transform="translate(', 1) if False else '')
    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    with open(os.path.join(HERE, 'heads.svg'), 'w') as f:
        f.write(heads_svg())
    if 'heads' in sys.argv:
        sys.exit()
    sv, info = scene_svg()
    open(os.path.join(HERE, 'scene.svg'), 'w').write(sv)
    print('scene', info)
    open(os.path.join(HERE, 'scene_sil.svg'), 'w').write(scene_svg(sil=True)[0])
    open(os.path.join(HERE, 'scene_bg.svg'), 'w').write(scene_svg(bg_only=True)[0])
    pv, pinfo = poses_svg()
    open(os.path.join(HERE, 'poses.svg'), 'w').write(pv)
    print('poses', pinfo)
    open(os.path.join(HERE, 'poses_sil.svg'), 'w').write(poses_svg(sil=True)[0])
    open(os.path.join(HERE, 'poses_silc.svg'), 'w').write(poses_svg(color_sil=True)[0])
    lv, linfo = lineup_svg()
    open(os.path.join(HERE, 'lineup.svg'), 'w').write(lv)
    open(os.path.join(HERE, 'lineup_sil.svg'), 'w').write(lineup_svg(sil=True)[0])
    print('lineup', linfo)
