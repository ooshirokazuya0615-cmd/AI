#!/usr/bin/env python3
"""Nose to Nose / 横顔のにらみ合い -- BIG-EYE version.  Hero SOL, rival SNOOT.

ONE face rig + ONE stick-body rig draw every output:
  scene.svg   (1080x1920)  nose-to-nose stare-down; both parry wooden dummies behind them blind
  faces.svg   (1080x1080)  Sol's head 3x2: neutral, surprised, angry, smug, panic, exasperated side-eye
  hero.svg    (540x1080)   Sol alone, 3/4 toward viewer's left, 900 px soles -> top of topknot
  partner.svg (540x1080)   Snoot alone, same rules, 900 px soles -> top of pompadour
  *_sil.svg   black silhouettes for the silhouette test

FACE RIG
  Skull = true circle, diameter D, no outline.  Head local coords: origin = skull centre, +x = facing,
  +y = down.  Each character owns ONE eye-white shape (Sol almond, Snoot gumdrop) that never morphs;
  expression = upper-lid mask (skin) + thick ink lid line, lower-lid mask, pupil position/size, brow,
  mouth, nose.  Eye footprint rim is always drawn so the eye stays BIG under heavy lids.
BODY RIG
  PURE stick figure (owner: "体は棒人間のままにして。顔は今の感じで"): skin neck stub, one curved ink spine,
  a short shoulder bar, two arms (upper + forearm), two legs (thigh + shin), mitten hands, small shoes.
  No torso shape, no clothing.  Every limb uses the same ink family (near INK, far a lighter ink) --
  never colour-coded per character.  Identity lives in the heads; Snoot keeps ONE tiny neck-level
  accessory (small terracotta neckerchief knot), Sol keeps none.  Props (broom) stay.
"""
import math, os, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
INK = '#23201C'
EYEW = '#FFFBF2'          # warm off-white, never #FFFFFF
TEETH = '#FBF6EA'
MOUTHC = '#3A2420'
TONGUE = '#B9573A'
SAND = '#E8D5B0'
TERRA = '#C0643F'
DUSK = '#3F5873'
PALE = '#F6F0E4'
MOON = '#EBD9B4'
ROOF = '#2E4258'
FLOOR_D = '#B89E78'
PLANK = '#D6BF97'
BRASS = '#C9A24B'
BRASS_D = '#A88536'
GOLD = '#D9A93A'
WOOD = '#A5703F'
WOOD_D = '#8C5C33'
ASH = '#D8B98A'
SAGE = '#8FA58A'
SAGE_D = '#728A6E'
PLUM = '#6E4A5E'
LAMP = '#F2CF8A'
ZORI = '#E9DCC1'
GREY_H = '#B9B4AC'
GREY_HD = '#8E8981'
LINEUP_BG = '#EDEAE4'

SKIN_SOL = '#9A6243'
SKIN_SNOOT = '#DDA982'
SKIN_GRAN = '#B57A55'


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


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return '#%02X%02X%02X' % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def closed_rounded(verts, r):
    m = len(verts)
    rr = r if isinstance(r, (list, tuple)) else [r] * m
    parts = []
    for i in range(m):
        a, v, b = verts[i - 1], verts[i], verts[(i + 1) % m]
        da, db = math.dist(a, v), math.dist(b, v)
        if da < 1e-6 or db < 1e-6:
            parts.append(('M' if i == 0 else 'L') + pt(v))
            continue
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


def pline(verts):
    return 'M' + ' L'.join(pt(q) for q in verts)


def star4(cx, cy, R, r, rot_deg=0):
    pts = []
    for i in range(8):
        a = math.radians(rot_deg + i * 45 - 90)
        rr = R if i % 2 == 0 else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly(pts)


def tube(pts, ws, color, extra=''):
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


def bez2(p0, p1, p2, t):
    return tuple((1 - t) ** 2 * p0[i] + 2 * (1 - t) * t * p1[i] + t * t * p2[i] for i in range(2))


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


def offset_poly(pts, d):
    out = []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        t = unit(sub(b, a))
        nrm = (-t[1], t[0])
        out.append(add(p, mul(nrm, d)))
    return out


def dotted(d, color, w=6, dash=(2, 14), extra=''):
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" '
            f'stroke-dasharray="{dash[0]} {dash[1]}"{extra}/>')


def arc_d(c, r, a0, a1):
    p0 = add(c, (r * math.cos(math.radians(a0)), r * math.sin(math.radians(a0))))
    p1 = add(c, (r * math.cos(math.radians(a1)), r * math.sin(math.radians(a1))))
    sweep = 1 if a1 > a0 else 0
    large = 1 if abs(a1 - a0) > 180 else 0
    return f"M{pt(p0)} A{n(r)},{n(r)} 0 {large} {sweep} {pt(p1)}"


def rimy(D, y, side=1):
    R = D / 2
    return (side * math.sqrt(max(0.0, R * R - y * y)), y)


def polar(D, deg, r_extra=0.0):
    R = D / 2 + r_extra
    a = math.radians(deg)
    return (R * math.cos(a), R * math.sin(a))


REG = dict(heads=[], head_pts=[], foot_pts=[], metrics=[])

# =====================================================================================
# CHARACTERS
# =====================================================================================
SCLERA = '#FBF6EA'        # warm off-white sclera, never #FFFFFF
LIDBAND = '#DCD3C3'       # lid shadow band over the white
HILITE = '#FFFFFF'        # catchlights: the ONLY pure white on a face

SOL = dict(
    name='sol', skin=SKIN_SOL, hair=INK, jaw='#85533A',
    eye=dict(kind='kirenaga', H=0.53, W=0.41, Wp=0.29, tail=0.0, gap=0.07, depth=0.48, front=0.09,
             lid=0.17, lid_tilt=5.0, low=0.0, band=0.040, crease=0.016,
             iris=dict(base='#179C6E', sh='#0E6B4B', li='#63CDA2', ring='#094832', pupil='#05241A'),
             ih=0.40, iw=0.32, ph=0.17, cut=0.03, ring=0.020, park='lid',
             hl='blade', lash=0.05, lash_end='taper', lower='outer3', lower_t=0.022, far_w=0.65, marks=('crows',)),
    brow=dict(kind='wedge', t=0.075, L=0.30, gap=0.035, dx=0.0, arch=0.012),
    nose='wedge', mouth_y=0.265, chin=0.885, chin_r=(0.055, 0.058),
)
SNOOT = dict(
    name='snoot', skin=SKIN_SNOOT, hair='#33241D', hair_hi='#56402F', jaw=None,
    eye=dict(kind='gumdrop', H=0.54, W=0.41, Wp=0.27, tail=0.0, gap=0.08, depth=0.47, front=0.09,
             lid=0.15, lid_tilt=0.0, lcurve=0.10, low=0.03, band=0.040, crease=0.014,
             iris=dict(base='#9150D6', sh='#6331A0', li='#C49DF1', ring='#432070', pupil='#1E0E36'),
             ih=0.41, iw=0.33, ph=0.17, cut=0.03, ring=0.018, park='low',
             hl='streaks', lash=0.04, lash_end='taper', lower='flat', lower_t=0.032, far_w=0.62, marks=('undereye',)),
    brow=dict(kind='arch', t=0.035, L=0.29, gap=0.045, dx=0.0, arch=0.055),
    nose='ski', mouth_y=0.285, chin=0.88, chin_r=(0.07, 0.066),
)


def X(**kw):
    """Expression state with defaults.  Eye fields:
       cov / tilt / lcurve   upper lid coverage (fraction of white height), slant in deg (+ = down toward the nose),
                             arch (+ = centre higher, ends sag)
       low / low_tilt / low_curve   lower lid rise (fraction), slant, upward curve
       gaze (gx, gy)         canonical: gx +1 = toward the nose / front corner, gy +1 = down
       iris_s, pupil_s       scale of iris / pupil vs rest;  fp_s  footprint height scale (pop <= 0.56/0.46)
       park                  'lid' (top cut by the lid), 'low' (bottom cut by the lower lid), 'free' (floating)
       hl                    'on' | 'off' (deadpan) | 'flash'
       wobble, tear, sweat   panic / worry extras"""
    d = dict(cov=None, tilt=None, lcurve=None, low=None, low_tilt=0.0, low_curve=0.0, gaze=(1.0, 0.0),
             iris_s=1.0, pupil_s=1.0, fp_s=1.0, park=None, hl='on', wobble=False, tear=False,
             brow_raise=0.0, brow_tilt=0.0, brow_arch=None, brow2_raise=0.0, brow2_arch=None, brow_drop_in=0.0,
             mouth='line', jaw=0.0, nose_up=0.0, flare=False, marks=[], far_cov=None)
    d.update(kw)
    return d


# =====================================================================================
# ANIME EYE SYSTEM  (one construction for every eye)
#   canonical frame: origin = footprint centre, +x = inner / front corner (toward the nose), +y = down.
#   footprint = white shape + the upper lash line on top of it.
# =====================================================================================
def smax(a, b, k):
    return (a + b + math.sqrt((a - b) ** 2 + k * k)) / 2


def smin(a, b, k):
    return (a + b - math.sqrt((a - b) ** 2 + k * k)) / 2


def _solve_amp(base, f, target, upper=True):
    """amplitude A with  min(base - A f) = target (upper) or max(base + A f) = target (lower)."""
    lo_, hi_ = 0.0, 1e5
    for _ in range(60):
        A = (lo_ + hi_) / 2
        if upper:
            v = min(b - A * g for b, g in zip(base, f))
            if v > target:
                lo_ = A
            else:
                hi_ = A
        else:
            v = max(b + A * g for b, g in zip(base, f))
            if v < target:
                lo_ = A
            else:
                hi_ = A
    return (lo_ + hi_) / 2


def eye_geom(E, view, D, wscale=1.0, fp_s=1.0):
    """Returns dict: xs, top (white top), bot (white bottom), fp_top (footprint top incl. lash), hw, Hs, lash."""
    lash = E['lash'] * D
    Hf = E['H'] * D * fp_s
    Hs = Hf - lash
    yc = lash / 2
    if view == 'front':
        W = E['W'] * D * wscale * (1 + (fp_s - 1) * 0.5)
    else:
        W = E['Wp'] * D * (1 + (fp_s - 1) * 0.4)
    hw = W / 2
    N = 120
    xs = [-hw + W * i / N for i in range(N + 1)]
    kind = E['kind']
    top, bot = [], []
    if view == 'front' and kind == 'kirenaga':
        yi, yo = 0.10 * Hs, -0.07 * Hs
        us = [x / hw for x in xs]
        yl = [yo + (yi - yo) * (u + 1) / 2 for u in us]
        ft = [max(0.0, 1 - u * u) ** (0.62 + 0.25 * max(0.0, u)) * (1 - 0.14 * u) for u in us]
        fb = [max(0.0, 1 - u * u) ** (0.95 + 0.35 * max(0.0, u)) * (1 - 0.05 * u) for u in us]
        A = _solve_amp(yl, ft, -Hs / 2, True)
        B = _solve_amp(yl, fb, Hs / 2, False)
        top = [b - A * g for b, g in zip(yl, ft)]
        bot = [b + B * g for b, g in zip(yl, fb)]
    elif view == 'front' and kind == 'gumdrop':
        r = 0.055 * D
        for x in xs:
            u = min(1.0, abs(x) / hw)
            v_ = max(0.0, 1 - u * u)
            top.append((Hs / 2 - r) - (Hs - r) * (0.55 * v_ ** 0.5 + 0.45 * v_ ** 1.5))
            ax = abs(x)
            if ax <= hw - r:
                bot.append(Hs / 2)
            else:
                dx = min(1.0, (ax - (hw - r)) / r)
                bot.append(Hs / 2 - r * (1 - math.sqrt(max(0.0, 1 - dx * dx))))
    elif kind == 'generic':
        for x in xs:
            u = min(1.0, abs(x) / hw)
            top.append(-Hs / 2 * max(0.0, 1 - u ** 2) ** 0.62)
            bot.append(Hs / 2 * max(0.0, 1 - u ** 2) ** 0.75)
    elif view == 'profile' and kind == 'kirenaga':
        yb = -0.06 * Hs
        for x in xs:
            t = (x + hw) / W
            tt = (1 - (1 - t) ** 2.1)
            yt = yb - (Hs / 2 + yb) * tt + 0.035 * Hs * max(0.0, (t - 0.80) / 0.20) ** 2
            yb_ = yb + (Hs / 2 - yb) * (1 - (1 - t) ** 1.6) - 0.06 * Hs * max(0.0, (t - 0.84) / 0.16) ** 2
            top.append(yt)
            bot.append(yb_)
    else:   # profile gumdrop: domed top, flat bottom, back corner low
        yb = Hs / 2 - 0.05 * Hs
        for x in xs:
            t = (x + hw) / W
            yt = yb - (Hs - 0.05 * Hs) * max(0.0, 1 - (1 - t) ** 2.0) ** 0.75 + 0.03 * Hs * max(0.0, (t - 0.82) / 0.18) ** 2
            top.append(yt)
            bot.append(Hs / 2 - 0.05 * Hs * max(0.0, 1 - t / 0.10))
    if view == 'profile':      # normalise the white to exactly Hs tall (the footprint keeps the front-view height)
        y0_, y1_ = min(top), max(bot)
        k_ = Hs / (y1_ - y0_)
        cm = (y0_ + y1_) / 2
        top = [(y - cm) * k_ for y in top]
        bot = [(y - cm) * k_ for y in bot]
    top = [y + yc for y in top]
    bot = [y + yc for y in bot]
    # footprint top = white top lifted by the lash (tapered to zero at the corners)
    fp = []
    for x, y in zip(xs, top):
        u = abs(x) / hw
        if view == 'profile':
            tap = min(1.0, (x + hw) / (0.35 * W))
        else:
            tap = min(1.0, (1 - u) / 0.30)
        fp.append(y - lash * max(0.0, tap))
    return dict(xs=xs, top=top, bot=bot, fp=fp, hw=hw, W=W, Hs=Hs, Hf=Hf, lash=lash, yc=yc, view=view)


def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    fi = (x - xs[0]) / (xs[-1] - xs[0]) * (len(xs) - 1)
    i = int(fi)
    i = min(i, len(xs) - 2)
    return ys[i] + (ys[i + 1] - ys[i]) * (fi - i)


def band_poly(pts_top, widths, up=True, center=None):
    """polygon edge from a polyline (ordered) offset along its normal by widths.
    center given: the normal points away from it (outward); else toward -y (up=True) / +y."""
    out = []
    m = len(pts_top)
    for i, p in enumerate(pts_top):
        a = pts_top[max(0, i - 2)]
        b = pts_top[min(m - 1, i + 2)]
        t = unit(sub(b, a))
        nrm = (t[1], -t[0])
        if center is not None:
            v = sub(p, center)
            if nrm[0] * v[0] + nrm[1] * v[1] < 0:
                nrm = mul(nrm, -1)
        elif up and nrm[1] > 0:
            nrm = mul(nrm, -1)
        elif not up and nrm[1] < 0:
            nrm = mul(nrm, -1)
        out.append(add(p, mul(nrm, widths[i])))
    return out


def centered_poly(pts, widths):
    a = band_poly(pts, [w / 2 for w in widths], up=True)
    b = band_poly(pts, [w / 2 for w in widths], up=False)
    return a + b[::-1]


def sm(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def anime_eye(ch, st, ex, ey, view, D, uid, m=1, flip=1, wscale=1.0, lash_s=1.0, show_crease=True, sil=False):
    """Draw one anime eye.  (ex,ey) footprint centre in head-local coords.  view 'front' (also 3/4) or 'profile'.
    m = +1: inner corner at +x local; m = -1 mirrored (far eye in 3/4).  flip = m * world facing (for light).
    Returns (svg, info)."""
    E = ch['eye']
    skin = ch['skin']
    I = E['iris']
    G = eye_geom(E, view, D, wscale, st['fp_s'])
    xs, top, bot, hw, Hs, lash = G['xs'], G['top'], G['bot'], G['hw'], G['Hs'], G['lash']
    cov = E['lid'] if st['cov'] is None else st['cov']
    tilt = E['lid_tilt'] if st['tilt'] is None else st['tilt']
    lowc = E['low'] if st['low'] is None else st['low']
    ymin = min(top)
    ymax = max(bot)
    tl = math.tan(math.radians(tilt))
    lcv = E.get('lcurve', 0.0) if st['lcurve'] is None else st['lcurve']
    k = 0.012 * D

    def lid(x):
        u = x / hw
        return ymin + cov * Hs + tl * x + lcv * Hs * u * u

    def lowl(x):
        u = x / hw
        return ymax - lowc * Hs + math.tan(math.radians(st['low_tilt'])) * x - st['low_curve'] * Hs * (1 - u * u)
    T = [smax(t, lid(x), k) if cov > 0.001 else t for x, t in zip(xs, top)]
    B = [smin(b, lowl(x), k) if lowc > 0.001 else b for x, b in zip(xs, bot)]
    ok = [i for i in range(len(xs)) if B[i] - T[i] > 0.6]
    if not ok:
        ok = [len(xs) // 2]
    i0, i1 = ok[0], ok[-1]
    oxs = xs[i0:i1 + 1]
    oT = T[i0:i1 + 1]
    oB = B[i0:i1 + 1]
    opening = [(x, y) for x, y in zip(oxs, oT)] + [(x, y) for x, y in zip(oxs[::-1], oB[::-1])]
    open_d = poly(opening)
    white_d = poly([(x, y) for x, y in zip(xs, top)] + [(x, y) for x, y in zip(xs[::-1], bot[::-1])])
    fp_d = poly([(x, y) for x, y in zip(xs, G['fp'])] + [(x, y) for x, y in zip(xs[::-1], bot[::-1])])
    tf = f'translate({n(ex)},{n(ey)})' + (' scale(-1,1)' if m < 0 else '')
    o = [f'<g transform="{tf}">']
    if sil:
        o.append(f'<path d="{fp_d}" fill="{INK}"/></g>')
        return ''.join(o), {}
    # ---- (0) eyelid tone over the whole footprint (shows the big eye even under a heavy lid)
    lidtone = mix(skin, '#3A2418', 0.10)
    U = [min(t_, b_) for t_, b_ in zip(T, bot)]
    lid_d = poly([(x, y) for x, y in zip(xs, G['fp'])] + [(x, y) for x, y in zip(xs[::-1], U[::-1])])
    o.append(f'<path d="{lid_d}" fill="{lidtone}"/>')
    # ---- iris geometry
    ih = E['ih'] * D * st['iris_s'] * (st['fp_s'] if st['fp_s'] > 1 else 1.0) ** 0
    if view == 'front':
        iw = E['iw'] * D * st['iris_s'] * (0.92 if wscale >= 0.99 else wscale * 1.05)
    else:
        iw = E['iw'] * D * st['iris_s'] * 0.58
    gx, gy = st['gaze']
    x_in, x_out = oxs[-1], oxs[0]
    if view == 'profile':
        xmax = hw - iw / 2 + 0.022 * D
        xmin = x_out + iw * 0.45
    else:
        xmax = x_in - iw * 0.40
        xmin = x_out + iw * 0.40
    xc = (xmin + xmax) / 2
    icx = xc + gx * ((xmax - xc) if gx > 0 else (xc - xmin))
    Ti = interp(xs, T, icx)
    Bi = interp(xs, B, icx)
    park = st['park'] or E['park']
    cut = E['cut'] * D
    if park == 'lid':
        icy = Ti - cut + ih / 2
        if icy + ih / 2 > Bi + 0.01 * D and lowc <= 0.001:
            icy = Bi + 0.01 * D - ih / 2
    elif park == 'low':
        icy = Bi + cut - ih / 2
        if icy - ih / 2 < Ti - cut * 1.6:
            icy = Ti - cut * 1.6 + ih / 2
    else:
        icy = (Ti + Bi) / 2
    icy += gy * 0.035 * D
    lx = -flip          # light side (screen upper-left) in canonical x
    cid_o, cid_i = f'eo{uid}', f'ei{uid}'
    o.append(f'<defs><clipPath id="{cid_o}"><path d="{open_d}"/></clipPath>'
             f'<clipPath id="{cid_i}"><ellipse cx="{n(icx)}" cy="{n(icy)}" rx="{n(iw / 2)}" ry="{n(ih / 2)}"/></clipPath></defs>')
    g = []
    # (1) sclera
    g.append(f'<path d="{open_d}" fill="{SCLERA}"/>')
    # (2) lid shadow band over the white
    bw = E['band'] * D
    bpts = [(x, y) for x, y in zip(oxs, oT)]
    band = bpts + [(x, y + bw) for x, y in bpts[::-1]]
    band_d = poly(band)
    g.append(f'<path d="{band_d}" fill="{LIDBAND}"/>')
    # (3) iris: light base, base shifted up (light crescent stays at the bottom), darker top third
    ir = [f'<ellipse cx="{n(icx)}" cy="{n(icy)}" rx="{n(iw / 2)}" ry="{n(ih / 2)}" fill="{I["li"]}"/>',
          f'<ellipse cx="{n(icx)}" cy="{n(icy - 0.15 * ih)}" rx="{n(iw / 2)}" ry="{n(ih / 2)}" fill="{I["base"]}"/>',
          f'<ellipse cx="{n(icx)}" cy="{n(icy - ih / 2 - 0.02 * ih)}" rx="{n(iw * 0.72)}" ry="{n(ih * 0.355)}" fill="{I["sh"]}"/>',
          f'<path d="{band_d}" fill="{I["sh"]}"/>']
    # (4) pupil
    ph = E['ph'] * D * st['pupil_s']
    pw = ph * (iw / ih)
    pcx, pcy = icx + gx * 0.04 * iw, icy - 0.03 * ih
    ir.append(f'<ellipse cx="{n(pcx)}" cy="{n(pcy)}" rx="{n(pw / 2)}" ry="{n(ph / 2)}" fill="{I["pupil"]}"/>')
    # limbal ring
    rw = E['ring'] * D
    ir.append(f'<ellipse cx="{n(icx)}" cy="{n(icy)}" rx="{n(iw / 2)}" ry="{n(ih / 2)}" fill="none" stroke="{I["ring"]}" stroke-width="{n(2 * rw)}"/>')
    g.append(f'<g clip-path="url(#{cid_i})">' + ''.join(ir) + '</g>')
    # (5) catchlights (pure white), light from screen upper-left
    hl = st['hl']
    if hl != 'off':
        if E['hl'] == 'blade':
            # Sol: one fat upright blade at the pupil's light-side edge + a small round secondary low on the other side
            big = hl == 'flash'
            bwid, blen = (0.056 if big else 0.046) * D, (0.140 if big else 0.112) * D
            bx = pcx + lx * (pw / 2 - 0.006 * D)
            by = pcy - ph * 0.28
            g.append(f'<rect x="{n(bx - bwid / 2)}" y="{n(by - blen / 2)}" width="{n(bwid)}" height="{n(blen)}" rx="{n(bwid / 2)}" fill="{HILITE}" '
                     f'transform="rotate({n(-8 * lx)},{n(bx)},{n(by)})"/>')
            g.append(f'<circle cx="{n(pcx - lx * pw * 0.62)}" cy="{n(pcy + ph * 0.62)}" r="{n(0.019 * D)}" fill="{HILITE}"/>')
            if big:
                g.append(f'<circle cx="{n(bx - lx * 0.05 * D)}" cy="{n(by - 0.055 * D)}" r="{n(0.012 * D)}" fill="{HILITE}"/>')
        elif E['hl'] == 'dot':
            r_ = 0.035 * D
            g.append(f'<circle cx="{n(pcx + lx * pw * 0.30)}" cy="{n(pcy - ph * 0.30)}" r="{n(r_)}" fill="{HILITE}"/>')
        elif E['hl'] == 'streaks':
            # Snoot: two parallel diagonal streaks, the main one fat
            wob = 0.004 * D if st['wobble'] else 0.0
            for (L_, W_, ox, oy) in ((0.112, 0.044, 0.0, 0.0), (0.062, 0.030, 0.050, 0.050)):
                cx_ = pcx + lx * (pw * 0.30) - lx * ox * D * 0.9 + wob
                cy_ = pcy - ph * 0.36 + oy * D - wob
                ang = -45 * flip
                g.append(f'<rect x="{n(cx_ - L_ * D / 2)}" y="{n(cy_ - W_ * D / 2)}" width="{n(L_ * D)}" height="{n(W_ * D)}" rx="{n(W_ * D / 2)}" '
                         f'fill="{HILITE}" transform="rotate({n(ang)},{n(cx_)},{n(cy_)})"/>')
    if st['tear']:
        tp = [(x, y - 0.012 * D) for x, y in zip(oxs, oB)][len(oxs) // 6: -len(oxs) // 6]
        g.append(f'<path d="{pline(tp)}" fill="none" stroke="{HILITE}" stroke-width="{n(0.012 * D)}" stroke-linecap="round"/>')
    o.append(f'<g clip-path="url(#{cid_o})">' + ''.join(g) + '</g>')
    # (6) upper lash line along the top of the opening: inner end tapered, outer end = character ending
    pts = [(x, y) for x, y in zip(oxs[::-1], oT[::-1])]      # inner -> outer
    Np = len(pts)
    L0 = E['lash'] * D * lash_s
    arc = [0.0]
    for i in range(1, Np):
        arc.append(arc[-1] + math.dist(pts[i], pts[i - 1]))
    tot = arc[-1] or 1.0
    ws = []
    for i in range(Np):
        s = arc[i] / tot
        if view == 'profile' and E['lash_end'] == 'taper':
            w = L0 * (0.40 + 0.60 * sm(s / 0.22)) * (1 - 0.62 * sm((s - 0.70) / 0.30))
        elif view == 'profile':
            w = L0 * (0.42 + 0.58 * sm(s / 0.22))
        elif E['lash_end'] == 'taper':
            # plain lash line: thin at the inner corner, full across the top, thinning again at the outer corner (no wing)
            w = L0 * (0.18 + 0.82 * sm((s - 0.04) / 0.36)) * (1 - 0.60 * sm((s - 0.72) / 0.28))
        elif E['lash_end'] == 'tail':
            w = L0 * (0.22 + 0.78 * sm(s / 0.40)) * (1 - 0.12 * sm((s - 0.80) / 0.20))
        else:
            w = L0 * (0.12 + 0.88 * sm((s - 0.06) / 0.34) ** 1.3)
        ws.append(w)
    ecen = (0.0, (ymin + ymax) / 2 + 0.06 * Hs)
    outer = band_poly(pts, ws, center=ecen)
    inner_edge = band_poly(pts, [-0.15 * w for w in ws], center=ecen)
    lash_poly = inner_edge + outer[::-1]
    o.append(f'<path d="{poly(lash_poly)}" fill="{INK}" stroke="{INK}" stroke-width="{n(0.004 * D)}" stroke-linejoin="round"/>')
    pe = pts[-1]
    oe = outer[-1]
    if E['lash_end'] == 'tail':
        # winged tail: the lash top line carries straight on past the outer corner, then returns to the corner
        tail = E['tail'] * D * lash_s
        ksw = Np - 1
        for i in range(Np - 1, -1, -1):          # last point (from the outer end) still riding on the lid line
            x_ = pts[i][0]
            if lid(x_) >= interp(xs, top, x_) - 0.004 * D:
                ksw = i
                break
        if ksw == Np - 1 or ksw < int(Np * 0.45):
            ksw = int(Np * 0.80)
        ksw = max(0, min(Np - 2, ksw - 2))
        q = outer[ksw]
        slope = (outer[max(0, ksw - 6)][1] - q[1]) / ((outer[max(0, ksw - 6)][0] - q[0]) or -1e-6)
        xt = min(pe[0], q[0]) - tail
        ty_ = q[1] + slope * (xt - q[0]) + 0.30 * ws[ksw]
        ty_ = max(q[1] - 0.01 * D, min(pe[1] - 0.02 * D, ty_))
        tip = (xt, ty_)
        wing = [q, tip, add(lerp(tip, pe, 0.45), (0.004 * D, 0.002 * D)), pe, pts[ksw]]
        o.append(f'<path d="{closed_rounded(wing, [0.0, 0.003 * D, 0.03 * D, 0.004 * D, 0.0])}" fill="{INK}"/>')
    elif E['lash_end'] in ('none', 'taper'):
        pass
    elif E['lash_end'] == 'flicks':
        # two neat groomed flicks at the outer corner, pointing out (-x) and up
        for ang, ln, sfr in ((32, 0.048, 0.86), (8, 0.040, 0.95)):
            d1 = (-math.cos(math.radians(ang)), -math.sin(math.radians(ang)))
            k_ = min(Np - 2, int((Np - 1) * sfr))
            k2 = min(Np - 1, k_ + max(2, Np // 16))
            base_mid = lerp(outer[k_], outer[k2], 0.5)
            tipf = add(base_mid, mul(d1, ln * D))
            o.append(f'<path d="{closed_rounded([outer[k_], tipf, outer[k2], pts[k2], pts[k_]], [0.004 * D, 0.003 * D, 0.004 * D, 0.0, 0.0])}" fill="{INK}"/>')
    # wobble ghost (panic): the outline shivers for 2 frames
    if st['wobble']:
        gp = [add(p, (0.016 * D, -0.012 * D)) for p in outer]
        o.append(f'<path d="{pline(gp)}" fill="none" stroke="{INK}" stroke-width="{n(0.012 * D)}" stroke-linecap="round" opacity="0.55"/>')
        gp2 = [add(p, (-0.014 * D, 0.012 * D)) for p in [(x, y) for x, y in zip(oxs, oB)]]
        o.append(f'<path d="{pline(gp2)}" fill="none" stroke="{INK}" stroke-width="{n(0.010 * D)}" stroke-linecap="round" opacity="0.55"/>')
    # (7) lower lash / lid line
    lw0 = E['lower_t'] * D
    lp = [(x, y) for x, y in zip(oxs[::-1], oB[::-1])]       # inner -> outer
    if E['lower'] == 'outer3':
        a0 = int(len(lp) * 0.60)
        seg = lp[a0:]
        wl = [lw0 * (0.25 + 0.75 * sm(i / max(1, len(seg) - 1) / 0.5)) for i in range(len(seg))]
        o.append(f'<path d="{poly(centered_poly(seg, wl))}" fill="{INK}"/>')
    elif E['lower'] == 'flat':
        flat = True
        nl = len(lp)
        seg = lp[int(nl * 0.05): nl - int(nl * 0.03)]
        ns = max(2, len(seg))
        wl = [(lw0 if flat else 0.022 * D) * (0.35 + 0.65 * sm(i / (ns - 1) / 0.20)) * (0.55 + 0.45 * sm((1 - i / (ns - 1)) / 0.12)) for i in range(len(seg))]
        o.append(f'<path d="{poly(centered_poly(seg, wl))}" fill="{INK}"/>')
    # creases, bags, crow's-feet (adult cues)
    cc = shade(skin, 0.42)
    if show_crease:
        cr = []
        for x, fpy, ty in zip(xs, G['fp'], T):
            s = (hw - x) / (2 * hw)
            if view == 'front' and not (0.10 <= s <= 0.90):
                continue
            if view == 'profile' and not (0.04 <= s <= 0.86):
                continue
            cr.append((x, smin(fpy + 0.004 * D, ty - L0 - 0.05 * D, 0.03 * D)))
        if len(cr) > 3:
            wc = [E['crease'] * D * (0.35 + 0.65 * math.sin(math.pi * i / (len(cr) - 1)) ** 0.5) for i in range(len(cr))]
            o.append(f'<path d="{poly(centered_poly(cr, wc))}" fill="{cc}"/>')
    if 'crows' in E.get('marks', ()):
        # two fine crow's-feet fanning out from the outer corner (short, below the tail)
        xo, yo = oxs[0], oB[0]
        for ang, r0, r1 in ((10, 0.035, 0.080), (32, 0.040, 0.078)):
            d1 = (-math.cos(math.radians(ang)), math.sin(math.radians(ang)))
            p0 = add((xo, yo), mul(d1, r0 * D))
            p1 = add((xo, yo), mul(d1, r1 * D))
            o.append(f'<path d="M{pt(p0)} L{pt(p1)}" fill="none" stroke="{cc}" stroke-width="{n(0.011 * D)}" stroke-linecap="round"/>')
    if 'undereye' in E.get('marks', ()):
        # under-eye line (age) under the footprint bottom
        ub, wu = [], []
        for j in range(21):
            x = -hw * 0.62 + hw * 1.10 * j / 20
            ub.append((x, interp(xs, bot, x) + 0.045 * D + 0.010 * D * math.sin(math.pi * j / 20)))
            wu.append(0.014 * D * (0.3 + 0.7 * math.sin(math.pi * j / 20)))
        o.append(f'<path d="{poly(centered_poly(ub, wu))}" fill="{shade(skin, 0.30)}"/>')
    o.append('</g>')
    vis = max(b - t for t, b in zip(oT, oB))
    fp_top = min(G['fp'])
    info = dict(fp_h=(ymax - fp_top) / D, white_h=(ymax - ymin) / D, open_h=vis / D, w=G['W'] / D,
                iris_h=ih / D, iris_w=iw / D, pupil=ph / D, cov=cov,
                top=ey + fp_top, white_top=ey + ymin, lash_top=ey + min(y for _, y in outer),
                icx=icx, icy=icy, lid_center=ey + interp(xs, T, 0.0))
    return ''.join(o), info


def brow_svg(kind, cx, cy, L, t, tilt, arch, mirror=False, color=INK, D=270):
    N = 22
    top, bot = [], []
    for i in range(N + 1):
        s = i / N
        x = -L / 2 + L * s
        y = -arch * 4 * s * (1 - s)
        if kind == 'wedge':
            th = t * (0.30 + 0.70 * s ** 0.85)
        else:
            th = t * (0.32 + 0.68 * math.sin(math.pi * s) ** 0.6)
        top.append((x, y - th / 2))
        bot.append((x, y + th / 2))
    if kind == 'wedge':      # blunt, slightly hooked thick end
        top[-1] = (top[-1][0] + 0.004 * D, top[-1][1] - 0.006 * D)
    d = poly(top + bot[::-1])
    sc = ' scale(-1,1)' if mirror else ''
    return (f'<path transform="translate({n(cx)},{n(cy)}){sc} rotate({n(tilt)})" d="{d}" fill="{color}" '
            f'stroke="{color}" stroke-width="{n(0.008 * D)}" stroke-linejoin="round"/>')


# =====================================================================================
# NOSES
# =====================================================================================
def nose_profile(ch, x, D):
    """Returns (skin path d, detail svg, tip, base, outline pts)."""
    st_flare = x['flare']
    if ch['nose'] == 'wedge':
        B0 = rimy(D, -0.03 * D)
        B1 = rimy(D, 0.205 * D)
        T = (0.835 * D, 0.150 * D)
        verts = [(0.30 * D, -0.04 * D), B0, T, B1, (0.30 * D, 0.215 * D)]
        rr = [0, 0, 0.035 * D, 0, 0]
        base = B1
        nc = lerp(T, B1, 0.60)
        nc = (nc[0], nc[1] - 0.022 * D)
        rx, ry = (0.050 * D, 0.024 * D) if st_flare else (0.034 * D, 0.015 * D)
        det = (f'<ellipse cx="{n(nc[0])}" cy="{n(nc[1])}" rx="{n(rx)}" ry="{n(ry)}" fill="{MOUTHC}" '
               f'transform="rotate(-9,{n(nc[0])},{n(nc[1])})"/>')
        wing_c = (nc[0] - 0.045 * D, nc[1] - 0.012 * D)
        wr = 0.07 * D if st_flare else 0.055 * D
        det += (f'<path d="M{pt((wing_c[0] + 0.02 * D, wing_c[1] - wr * 0.85))} Q{pt((wing_c[0] - wr * 0.75, wing_c[1]))} '
                f'{pt((wing_c[0] + 0.015 * D, wing_c[1] + wr * 0.75))}" fill="none" stroke="{shade(ch["skin"], 0.45)}" '
                f'stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    else:   # ski jump
        W = 0.47 * D
        nl, nh = 0.37 * D, 0.24 * D
        y0, y1 = 0.0, nh
        b = [bez3((W, y0 - 0.26 * nh), (W + 0.30 * nl, y0 + 0.36 * nh), (W + 0.62 * nl, y0 + 0.64 * nh),
                  (W + 0.88 * nl, y0 + 0.50 * nh), t / 14) for t in range(1, 15)]
        q1 = [bez3((W + 0.88 * nl, y0 + 0.50 * nh), (W + 0.95 * nl, y0 + 0.46 * nh), (W + 0.97 * nl, y0 + 0.42 * nh),
                   (W + 1.0 * nl, y0 + 0.34 * nh), t / 5) for t in range(1, 6)]
        q2 = [bez3((W + 1.0 * nl, y0 + 0.34 * nh), (W + 1.06 * nl, y0 + 0.50 * nh), (W + 1.03 * nl, y0 + 0.64 * nh),
                   (W + 0.90 * nl, y0 + 0.72 * nh), t / 6) for t in range(1, 7)]
        under = [(W + 0.74 * nl, y0 + 0.84 * nh), (W + 0.55 * nl, y1 + 0.04 * nh), (W + 0.30 * nl, y1 + 0.02 * nh),
                 (W - 0.02 * D, y1)]
        verts = [(0.25 * D, y0 - 0.26 * nh), (W, y0 - 0.26 * nh)] + b + q1 + q2 + under + [(0.25 * D, y1)]
        rr = 0
        base = (W, y1)
        T = (W + 1.0 * nl, y0 + 0.34 * nh)
        rx, ry = (0.050 * D, 0.028 * D) if st_flare else (0.036 * D, 0.019 * D)
        nc = (W + 0.66 * nl, y0 + 0.86 * nh)
        det = (f'<ellipse cx="{n(nc[0])}" cy="{n(nc[1])}" rx="{n(rx)}" ry="{n(ry)}" fill="{MOUTHC}" '
               f'transform="rotate(-24,{n(nc[0])},{n(nc[1])})"/>')
        wr = 0.06 * D if st_flare else 0.048 * D
        wc = (W + 0.42 * nl, y0 + 0.74 * nh)
        det += (f'<path d="M{pt((wc[0] + 0.01 * D, wc[1] - wr))} Q{pt((wc[0] - wr * 0.8, wc[1] + 0.01 * D))} '
                f'{pt((wc[0] + 0.02 * D, wc[1] + wr * 0.8))}" fill="none" stroke="{shade(ch["skin"], 0.40)}" '
                f'stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    ang = -x['nose_up']
    if ang:
        verts = [rot(v, base, ang) for v in verts]
        T = rot(T, base, ang)
        det = f'<g transform="rotate({n(ang)},{n(base[0])},{n(base[1])})">{det}</g>'
    d = closed_rounded(verts, rr)
    return d, det, T, base, verts


# =====================================================================================
# MOUTHS (profile)  -- modest: a line, a small 'o', a short wavy line.  No teeth, no lips, no stretched jaw.
# =====================================================================================
def mouth_profile(ch, x, D):
    """Returns (skin svg drawn with the skull, detail svg, chin drop)."""
    m = x['mouth']
    skin = ch['skin']
    ym = ch['mouth_y'] * D
    xm = rimy(D, ym)[0]
    lw = 0.024 * D
    S = f'fill="none" stroke="{INK}" stroke-width="{n(lw)}" stroke-linecap="round" stroke-linejoin="round"'
    crease = shade(skin, 0.36)
    sk, det = [], []
    if m in ('line', 'notch'):
        L_ = 0.075 if m == 'notch' else 0.11
        det.append(f'<path d="M{pt((xm + 0.008 * D, ym))} Q{pt((xm - L_ * 0.45 * D, ym + 0.004 * D))} {pt((xm - L_ * D, ym + 0.014 * D))}" {S}/>')
    elif m == 'pout':       # Snoot at rest: pressed, corner down
        det.append(f'<path d="M{pt((xm + 0.012 * D, ym))} Q{pt((xm - 0.05 * D, ym - 0.006 * D))} {pt((xm - 0.115 * D, ym + 0.026 * D))}" {S}/>')
    elif m in ('smirk', 'smug'):
        e_ = (xm - 0.115 * D, ym - (0.035 if m == 'smug' else 0.022) * D)
        det.append(f'<path d="M{pt((xm + 0.008 * D, ym + 0.006 * D))} Q{pt((xm - 0.06 * D, ym + 0.016 * D))} {pt(e_)}" {S}/>')
        det.append(f'<path d="M{pt((e_[0] - 0.012 * D, e_[1] - 0.05 * D))} Q{pt((e_[0] - 0.04 * D, e_[1] - 0.005 * D))} {pt((e_[0] - 0.018 * D, e_[1] + 0.04 * D))}" '
                   f'fill="none" stroke="{crease}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    elif m == 'flat':       # exasperated: dead flat
        det.append(f'<path d="M{pt((xm + 0.01 * D, ym + 0.004 * D))} L{pt((xm - 0.10 * D, ym + 0.004 * D))}" {S}/>')
    elif m == 'tight':      # anger: short pressed line, corner pulled down
        det.append(f'<path d="M{pt((xm + 0.01 * D, ym - 0.004 * D))} L{pt((xm - 0.075 * D, ym - 0.002 * D))} L{pt((xm - 0.10 * D, ym + 0.024 * D))}" {S}/>')
    elif m == 'o':          # small 'o'
        c = (xm - 0.035 * D, ym + 0.01 * D)
        det.append(f'<ellipse cx="{n(c[0])}" cy="{n(c[1])}" rx="{n(0.028 * D)}" ry="{n(0.036 * D)}" fill="{MOUTHC}" stroke="{INK}" stroke-width="{n(0.014 * D)}"/>')
    elif m == 'wavy':       # short wavy line
        pts_ = [(xm + 0.01 * D - 0.11 * D * i / 6, ym + (0.012 * D if i % 2 else -0.004 * D)) for i in range(7)]
        det.append(f'<path d="{pline(pts_)}" {S}/>')
    elif m == 'sneer':      # Snoot: upper lip line curled at the front, corner pulled down (no teeth)
        P0 = (xm + 0.012 * D, ym - 0.004 * D)
        P1 = (xm - 0.035 * D, ym - 0.03 * D)
        P2 = (xm - 0.065 * D, ym + 0.002 * D)
        P3 = (xm - 0.125 * D, ym + 0.035 * D)
        det.append(f'<path d="M{pt(P0)} Q{pt(P1)} {pt(P2)} Q{pt((xm - 0.095 * D, ym + 0.014 * D))} {pt(P3)}" {S}/>')
    return ''.join(sk), ''.join(det), 0.0


# =====================================================================================
# HAIR PIECES
# =====================================================================================
MAGE_PIVOT = (-0.165, -0.445)
MAGE_SCALE = 1.5
MAGE_TILT = 12.0          # degrees forward (toward the face)


def mage_tf(p, D):
    piv = (MAGE_PIVOT[0] * D, MAGE_PIVOT[1] * D)
    return add(piv, rotv(mul(sub(p, piv), MAGE_SCALE), MAGE_TILT))


def mage_pts(D):
    """Sol's chonmage, ~1.5x the old knot: tall tied stem from the crown, club folded FORWARD and drooping,
    its tip stopping well behind the brow line."""
    s = D
    c = [(-0.205 * s, -0.430 * s), (-0.175 * s, -0.585 * s), (-0.055 * s, -0.660 * s), (0.085 * s, -0.630 * s),
         (0.205 * s, -0.568 * s)]
    ws = [0.200 * s, 0.186 * s, 0.168 * s, 0.150 * s, 0.132 * s]
    L, Rr = [], []
    for i, p in enumerate(c):
        a = c[max(0, i - 1)]
        b = c[min(len(c) - 1, i + 1)]
        t = unit(sub(b, a))
        nrm = (-t[1], t[0])
        L.append(add(p, mul(nrm, ws[i] / 2)))
        Rr.append(add(p, mul(nrm, -ws[i] / 2)))
    td = unit(sub(c[-1], c[-2]))
    tn = (-td[1], td[0])
    k = 1.3
    fan = [add(add(c[-1], mul(td, 0.065 * s * k)), mul(tn, -0.068 * s * k)), add(add(c[-1], mul(td, 0.040 * s * k)), mul(tn, -0.022 * s * k)),
           add(add(c[-1], mul(td, 0.075 * s * k)), mul(tn, 0.0)), add(add(c[-1], mul(td, 0.040 * s * k)), mul(tn, 0.026 * s * k)),
           add(add(c[-1], mul(td, 0.060 * s * k)), mul(tn, 0.066 * s * k))]
    outline = Rr + fan + L[::-1]
    return outline, c, ws


def mage_svg(D, tie, sil=False):
    outline, c, ws = mage_pts(D)
    rr = [0.045 * D] * len(outline)
    for i in range(5, 10):
        rr[i] = 0.008 * D
    o = [f'<path d="{closed_rounded(outline, rr)}" fill="{INK}"/>']
    if not sil:
        p = c[1]
        t = unit(sub(c[2], c[0]))
        nr = (-t[1], t[0])
        band = [add(add(p, mul(t, -0.030 * D)), mul(nr, 0.090 * D)), add(add(p, mul(t, 0.030 * D)), mul(nr, 0.084 * D)),
                add(add(p, mul(t, 0.030 * D)), mul(nr, -0.084 * D)), add(add(p, mul(t, -0.030 * D)), mul(nr, -0.090 * D))]
        o.append(f'<path d="{closed_rounded(band, 0.014 * D)}" fill="{tie}"/>')
    k0 = add(c[1], (-0.07 * D, 0.02 * D))
    col = INK if sil else tie
    for e, w0 in (((-0.33 * D, -0.50 * D), 0.030), ((-0.29 * D, -0.44 * D), 0.027)):
        o.append(tube([k0, lerp(k0, e, 0.5), e], [w0 * D, w0 * D, w0 * D * 0.8], col))
    return ''.join(o), outline


def pomp_pts(D, view='profile'):
    """Snoot's quiff: puffs UP (not forward) and splits at the front into three locks -- never a hat brim."""
    s = D
    if view == '34':
        crest = [(0.32 * s, -0.43 * s),
                 (0.47 * s, -0.50 * s), (0.405 * s, -0.535 * s),
                 (0.51 * s, -0.605 * s), (0.43 * s, -0.635 * s),
                 (0.485 * s, -0.705 * s),
                 (0.36 * s, -0.745 * s), (0.17 * s, -0.752 * s), (-0.04 * s, -0.72 * s),
                 (-0.24 * s, -0.64 * s), (-0.39 * s, -0.51 * s), (-0.48 * s, -0.34 * s), (-0.52 * s, -0.18 * s),
                 (-0.52 * s, -0.06 * s)]
        lower = [(-0.50 * s, -0.02 * s), (-0.44 * s, -0.17 * s), (-0.33 * s, -0.355 * s), (-0.13 * s, -0.445 * s),
                 (0.10 * s, -0.465 * s)]
        return crest + lower
    crest = [(0.30 * s, -0.375 * s),                     # front hairline
             (0.455 * s, -0.455 * s), (0.395 * s, -0.495 * s),   # lock 1 tip + notch
             (0.505 * s, -0.575 * s), (0.425 * s, -0.605 * s),   # lock 2 tip + notch
             (0.485 * s, -0.690 * s),                    # lock 3 tip
             (0.36 * s, -0.735 * s), (0.17 * s, -0.745 * s), (-0.04 * s, -0.715 * s),
             (-0.24 * s, -0.635 * s), (-0.39 * s, -0.505 * s), (-0.48 * s, -0.34 * s), (-0.52 * s, -0.18 * s),
             (-0.52 * s, -0.06 * s)]
    lower = [(-0.50 * s, -0.02 * s), (-0.37 * s, -0.12 * s), (-0.19 * s, -0.20 * s), (0.0 * s, -0.27 * s),
             (0.16 * s, -0.335 * s)]
    return crest + lower


POMP_R = None


def pomp_round(D, view='profile'):
    pp = pomp_pts(D, view)
    rr = [0.03 * D] * len(pp)
    for i in (1, 3, 5):
        rr[i] = 0.012 * D          # crisp lock tips
    for i in (2, 4):
        rr[i] = 0.01 * D
    return closed_rounded(pp, rr)


def pomp_detail(ch, D, view='profile'):
    hi = ch['hair_hi']
    o = []
    if view == '34':
        for a, b, c_, w in (((0.44, -0.68), (0.18, -0.72), (-0.28, -0.58), 0.020),
                            ((0.45, -0.58), (0.12, -0.63), (-0.37, -0.42), 0.018),
                            ((0.40, -0.50), (0.12, -0.53), (-0.30, -0.36), 0.015)):
            o.append(f'<path d="M{pt(mul(a, D))} Q{pt(mul(b, D))} {pt(mul(c_, D))}" fill="none" stroke="{hi}" stroke-width="{n(w * D)}" stroke-linecap="round"/>')
        return ''.join(o)
    # comb grooves sweeping from each front lock back over the crown
    for a, b, c_, w in (((0.44, -0.66), (0.18, -0.70), (-0.28, -0.56), 0.020),
                        ((0.45, -0.56), (0.12, -0.61), (-0.37, -0.40), 0.018),
                        ((0.39, -0.47), (0.10, -0.50), (-0.30, -0.30), 0.015)):
        o.append(f'<path d="M{pt(mul(a, D))} Q{pt(mul(b, D))} {pt(mul(c_, D))}" fill="none" stroke="{hi}" stroke-width="{n(w * D)}" stroke-linecap="round"/>')
    return ''.join(o)


def ear_c(cx, cy, h, D, col=INK):
    d = (f"M{pt((cx + 0.23 * h, cy - 0.50 * h))} C{pt((cx - 0.42 * h, cy - 0.60 * h))} "
         f"{pt((cx - 0.44 * h, cy + 0.56 * h))} {pt((cx + 0.18 * h, cy + 0.50 * h))}")
    d2 = f"M{pt((cx + 0.12 * h, cy - 0.16 * h))} Q{pt((cx - 0.12 * h, cy))} {pt((cx + 0.08 * h, cy + 0.20 * h))}"
    return (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{n(0.021 * D)}" stroke-linecap="round"/>'
            f'<path d="{d2}" fill="none" stroke="{col}" stroke-width="{n(0.017 * D)}" stroke-linecap="round"/>')


def drop_svg(cx, cy, s, a, D):
    d = "M0,-26 C9,-10 16,2 0,16 C-16,2 -9,-10 0,-26 Z"
    return (f'<path transform="translate({n(cx)},{n(cy)}) rotate({a}) scale({n(s * D / 220)})" d="{d}" '
            f'fill="{PALE}" stroke="{INK}" stroke-width="{n(4.5 * 220 / D / s * D / 270)}" stroke-linejoin="round"/>')


def marks_svg(x, D, tip, ch, view='profile'):
    out = []
    st = f'fill="none" stroke="{INK}" stroke-width="{n(0.024 * D)}" stroke-linecap="round"'
    for m in x['marks']:
        if m == 'emanata':
            ox, oy = 0.05 * D, -0.25 * D
            for ang in (-130, -95, -60):
                a = math.radians(ang)
                p0 = (ox + 0.56 * D * math.cos(a), oy + 0.56 * D * math.sin(a))
                p1 = (ox + 0.70 * D * math.cos(a), oy + 0.70 * D * math.sin(a))
                out.append(f'<path d="M{pt(p0)} L{pt(p1)}" {st}/>')
        elif m == 'snort':
            bx, by = tip[0] - 0.06 * D, tip[1] + 0.07 * D
            if ch['nose'] == 'ski':
                bx, by = tip[0] - 0.10 * D, tip[1] + 0.12 * D
            for ang in (35, 60, 85):
                a = math.radians(ang)
                p0 = (bx + 0.05 * D * math.cos(a), by + 0.05 * D * math.sin(a))
                p1 = (bx + 0.13 * D * math.cos(a), by + 0.13 * D * math.sin(a))
                out.append(f'<path d="M{pt(p0)} L{pt(p1)}" {st}/>')
        elif m == 'huff':      # small exhale puff from the nostril
            bx, by = tip[0] - 0.03 * D, tip[1] + 0.10 * D
            for i, (dx, dy, r) in enumerate(((0.05, 0.04, 0.035), (0.11, 0.07, 0.028), (0.16, 0.08, 0.02))):
                out.append(f'<circle cx="{n(bx + dx * D)}" cy="{n(by + dy * D)}" r="{n(r * D)}" fill="{PALE}" stroke="{INK}" stroke-width="{n(0.012 * D)}"/>')
        elif m == 'shake':
            for off in ((0.62, 0.71) if view == '34' else (0.66, 0.76)):
                xx = -off * D
                d = f"M{pt((xx + 0.03 * D, -0.22 * D))} Q{pt((xx - 0.03 * D, -0.08 * D))} {pt((xx + 0.03 * D, 0.06 * D))}"
                out.append(f'<path d="{d}" {st}/>')
        elif m == 'sweat':
            out.append(drop_svg(-0.36 * D, -0.52 * D, 1.0, 150, D))
            out.append(drop_svg(0.50 * D, -0.36 * D, 0.75, 210, D))
        elif m == 'sweat1':
            out.append(drop_svg(0.50 * D, -0.30 * D, 0.55, 200, D))
    return ''.join(out)


def gaze_from(tgt, ex, ey, st, m=1, gain=2.6):
    """canonical gaze (gx, gy) toward a head-local target point."""
    if tgt is None:
        return st['gaze']
    v = (tgt[0] - ex, tgt[1] - ey)
    L = math.hypot(*v) or 1.0
    gx = max(-1.0, min(1.0, v[0] / L * gain)) * m
    gy = max(-1.0, min(1.0, v[1] / L * 2.2))
    return (gx, gy)


# =====================================================================================
# PROFILE HEAD
# =====================================================================================
def head_profile(ch, x, D, uid, tgt=None, sil=False, facing=1):
    R = D / 2
    skin = ch['skin']
    E = ch['eye']
    Bw = ch['brow']
    x = dict(x)
    x['_uid'] = uid
    nose_d, nose_det, tip, nbase, nverts = nose_profile(ch, x, D)
    msk, mdet, chin_dy = mouth_profile(ch, x, D)
    cy_ = (ch['chin'] - 0.5) * D
    chin = rimy(D, cy_)
    chin = (chin[0] - 0.012 * D, chin[1] + chin_dy)
    crx, cry = ch['chin_r']
    chin_svg = (f'<ellipse cx="{n(chin[0])}" cy="{n(chin[1])}" rx="{n(crx * D)}" ry="{n(cry * D)}" fill="{skin}" '
                f'transform="rotate({n(ang_of(chin))},{n(chin[0])},{n(chin[1])})"/>')
    pts = [polar(D, a) for a in range(0, 360, 10)] + nverts
    o = []
    sol = ch['name'] == 'sol'
    if sol:
        m_svg, m_out = mage_svg(D, BRASS, sil)
        pts += m_out
    else:
        pp = pomp_pts(D)
        pts += pp
    if sil:
        o.append(f'<g fill="{INK}"><circle r="{n(R)}"/><path d="{nose_d}"/>{chin_svg.replace(skin, INK)}</g>')
        if sol:
            o.append(m_svg)
            o.append(f'<path d="{sol_tuft(chin, D)}" fill="{INK}"/>')
        else:
            o.append(f'<path d="{pomp_round(D)}" fill="{INK}"/>')
            o.append(f'<circle cx="{n(-0.155 * D)}" cy="{n(0.145 * D)}" r="{n(0.048 * D)}" fill="none" stroke="{INK}" stroke-width="{n(0.022 * D)}"/>')
        return ''.join(o), pts
    cid = f'sk{uid}'
    o.append(f'<defs><clipPath id="{cid}"><circle r="{n(R)}"/>{chin_svg.replace(" fill=", " data-f=")}</clipPath></defs>')
    o.append(f'<circle r="{n(R)}" fill="{skin}"/>')
    o.append(f'<path d="{nose_d}" fill="{skin}"/>')
    o.append(chin_svg)
    inner = []
    if sol:
        jd = (f"M{pt((0.7 * D, 0.215 * D))} L{pt((0.42 * D, 0.215 * D))} C{pt((0.30 * D, 0.215 * D))} {pt((0.13 * D, 0.235 * D))} "
              f"{pt((0.02 * D, 0.20 * D))} C{pt((-0.04 * D, 0.175 * D))} {pt((-0.075 * D, 0.15 * D))} {pt((-0.10 * D, 0.13 * D))} "
              f"C{pt((-0.12 * D, 0.24 * D))} {pt((-0.10 * D, 0.36 * D))} {pt((-0.04 * D, 0.62 * D))} L{pt((0.7 * D, 0.9 * D))} Z")
        inner.append(f'<path d="{jd}" fill="{ch["jaw"]}"/>')
        band = []
        a0, a1 = 112, 172
        for i in range(25):
            a = a0 + (a1 - a0) * i / 24
            band.append(polar(D, a, 0.01 * D))
        for i in range(25):
            a = a1 - (a1 - a0) * i / 24
            s_ = math.sin(math.pi * (a - a0) / (a1 - a0)) ** 0.5
            band.append(polar(D, a, -0.075 * D * s_ - 0.004 * D))
        inner.append(f'<path d="{poly(band)}" fill="{INK}"/>')
    else:
        jd = (f"M{pt((0.7 * D, 0.335 * D))} L{pt((0.36 * D, 0.335 * D))} C{pt((0.22 * D, 0.335 * D))} {pt((0.07 * D, 0.30 * D))} "
              f"{pt((-0.02 * D, 0.235 * D))} C{pt((-0.08 * D, 0.19 * D))} {pt((-0.12 * D, 0.13 * D))} {pt((-0.22 * D, 0.11 * D))} "
              f"L{pt((-0.7 * D, 0.11 * D))} L{pt((-0.7 * D, 0.9 * D))} L{pt((0.7 * D, 0.9 * D))} Z")
        inner.append(f'<path d="{jd}" fill="{shade(skin, 0.10)}"/>')
        sb = [(-0.15 * D, -0.185 * D), (-0.065 * D, -0.262 * D), (-0.048 * D, -0.05 * D), (-0.045 * D, 0.16 * D), (-0.062 * D, 0.262 * D),
              (-0.092 * D, 0.17 * D), (-0.108 * D, -0.06 * D)]
        inner.append(f'<path d="{closed_rounded(sb, [0, 0.02 * D, 0.03 * D, 0.03 * D, 0.004 * D, 0.03 * D, 0.03 * D])}" fill="{ch["hair"]}"/>')
    o.append(f'<g clip-path="url(#{cid})">' + ''.join(inner) + '</g>')
    o.append(msk)
    if sol:
        o.append(m_svg)
    else:
        o.append(f'<path d="{pomp_round(D)}" fill="{ch["hair"]}"/>')
        o.append(pomp_detail(ch, D))
    ex_ear, ey_ear = (-0.13 if sol else -0.17) * D, 0.01 * D
    o.append(f'<ellipse cx="{n(ex_ear - 0.005 * D)}" cy="{n(ey_ear)}" rx="{n(0.058 * D)}" ry="{n(0.088 * D)}" fill="{skin}"/>')
    o.append(ear_c(ex_ear, ey_ear, 0.175 * D, D))
    if not sol:
        o.append(f'<circle cx="{n(-0.155 * D)}" cy="{n(0.145 * D)}" r="{n(0.048 * D)}" fill="none" stroke="{GOLD}" stroke-width="{n(0.022 * D)}"/>')
        # nasolabial line (adult cue) from behind the nose wing toward the mouth corner
        o.append(f'<path d="M{pt((0.40 * D, 0.085 * D))} Q{pt((0.33 * D, 0.17 * D))} {pt((0.335 * D, 0.255 * D))}" fill="none" '
                 f'stroke="{shade(skin, 0.30)}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    # ---- eye: one front-open wedge, front corner E['front'] behind the face rim
    st = dict(x)
    ey = (E['depth'] - 0.5) * D
    W = E['Wp'] * D * (1 + (st['fp_s'] - 1) * 0.4)
    rimx = math.sqrt(max(0.0, R * R - ey * ey))
    ex = rimx - E['front'] * D - W / 2
    st['gaze'] = gaze_from(tgt, ex, ey, st)
    eye, info = anime_eye(ch, st, ex, ey, 'profile', D, uid, m=1, flip=facing)
    o.append(eye)
    # ---- brow: close above the footprint top
    arch = Bw['arch'] if x['brow_arch'] is None else x['brow_arch']
    bcx = ex + 0.035 * D + Bw['dx'] * D
    bcy = info['top'] - Bw['gap'] * D - Bw['t'] * D / 2 - x['brow_raise'] * D
    bclip = f'bc{uid}'
    o.append(f'<defs><clipPath id="{bclip}"><circle r="{n(R + 0.012 * D)}"/></clipPath></defs>')
    o.append(f'<g clip-path="url(#{bclip})">' + brow_svg(Bw['kind'], bcx, bcy, Bw['L'] * D, Bw['t'] * D, x['brow_tilt'], arch * D, D=D) + '</g>')
    o.append(mdet)
    o.append(nose_det)
    if sol:
        o.append(f'<path d="{sol_tuft(chin, D)}" fill="{INK}"/>')
    o.append(marks_svg(x, D, tip, ch))
    REG['metrics'].append(dict(uid=uid, name=ch['name'], view='profile', fp_h=round(info['fp_h'], 3), white_h=round(info['white_h'], 3),
                               open_h=round(info['open_h'], 3), eye_w=round(info['w'], 3), iris_h=round(info['iris_h'], 3),
                               iris_frac=round(info['iris_h'] / info['fp_h'], 2), pupil=round(info['pupil'], 3),
                               eye_c_depth=round(E['depth'], 3), fp_top_depth=round((info['top'] + R) / D, 3),
                               front_gap=round((rimx - (ex + W / 2)) / D, 3)))
    return ''.join(o), pts


def sol_tuft(chin, D):
    c = (chin[0] - 0.005 * D, chin[1] + 0.035 * D)
    v = [(c[0] - 0.045 * D, c[1] - 0.012 * D), (c[0] + 0.035 * D, c[1] - 0.004 * D), (c[0] + 0.03 * D, c[1] + 0.06 * D),
         (c[0] + 0.012 * D, c[1] + 0.13 * D), (c[0] - 0.02 * D, c[1] + 0.06 * D)]
    return closed_rounded(v, [0.02 * D, 0.02 * D, 0.03 * D, 0.006 * D, 0.03 * D])


# =====================================================================================
# 3/4 HEAD (facing +x)
# =====================================================================================
def head_34(ch, x, D, uid, tgt=None, sil=False, facing=1):
    R = D / 2
    skin = ch['skin']
    E = ch['eye']
    Bw = ch['brow']
    sol = ch['name'] == 'sol'
    o = []
    # nose: bridge sits in the gap between the eyes up to their mid-height, tip juts toward the facing side
    ey = (E['depth'] - 0.5) * D
    if sol:
        N0 = (0.150 * D, ey - 0.012 * D)
        N1 = (0.198 * D, ey - 0.012 * D)
        K = (0.262 * D, 0.118 * D)
        T = (0.700 * D, 0.236 * D)
        NB = (0.43 * D, 0.274 * D)
        NBk = (0.140 * D, 0.252 * D)
        nose_v = [N0, N1, K, T, NB, NBk]
        nose = closed_rounded(nose_v, [0.02 * D, 0.02 * D, 0.05 * D, 0.03 * D, 0.025 * D, 0.03 * D])
        nshadow = closed_rounded([(0.15 * D, 0.12 * D), (0.22 * D, 0.17 * D), (0.36 * D, 0.262 * D), NBk], [0.03 * D, 0.03 * D, 0.02 * D, 0.03 * D])
    else:
        N0 = (0.168 * D, ey - 0.012 * D)
        pts_b = [bez3((0.218 * D, ey - 0.012 * D), (0.25 * D, 0.10 * D), (0.45 * D, 0.175 * D), (0.615 * D, 0.080 * D), t / 12) for t in range(0, 13)]
        T = (0.665 * D, 0.034 * D)
        nose_v = [N0] + pts_b + [T, (0.684 * D, 0.084 * D), (0.635 * D, 0.158 * D), (0.50 * D, 0.198 * D), (0.33 * D, 0.212 * D),
                                 (0.15 * D, 0.198 * D)]
        nose = closed_rounded(nose_v, 0.014 * D)
        nshadow = closed_rounded([(0.15 * D, 0.10 * D), (0.24 * D, 0.15 * D), (0.33 * D, 0.212 * D), (0.15 * D, 0.198 * D)], 0.02 * D)
    ear_c_ = (-R + 0.01 * D, 0.025 * D)
    ear = (f'<ellipse cx="{n(ear_c_[0])}" cy="{n(ear_c_[1])}" rx="{n(0.072 * D)}" ry="{n(0.105 * D)}" fill="{skin}" '
           f'transform="rotate(8,{n(ear_c_[0])},{n(ear_c_[1])})"/>')
    chin_c = polar(D, 68 if sol else 64)
    crx, cry = ch['chin_r']
    chin_svg = (f'<ellipse cx="{n(chin_c[0])}" cy="{n(chin_c[1] - 0.004 * D)}" rx="{n((crx + 0.01) * D)}" ry="{n(cry * D)}" fill="{skin}"/>')
    pts = [polar(D, a) for a in range(0, 360, 10)] + nose_v + [(ear_c_[0] - 0.072 * D, ear_c_[1])]
    if sol:
        m_svg, m_out = mage_svg(D, BRASS, sil)
        pts += m_out
    else:
        pp = pomp_pts(D, '34')
        pts += pp
    ring = (-R + 0.03 * D, 0.175 * D)
    if sil:
        o.append(f'<g fill="{INK}"><circle r="{n(R)}"/><path d="{nose}"/>{ear.replace(skin, INK)}{chin_svg.replace(skin, INK)}</g>')
        if sol:
            o.append(m_svg)
            o.append(f'<path d="{sol_tuft(chin_c, D)}" fill="{INK}"/>')
        else:
            o.append(f'<path d="{pomp_round(D, '34')}" fill="{INK}"/>')
            o.append(f'<circle cx="{n(ring[0])}" cy="{n(ring[1])}" r="{n(0.05 * D)}" fill="none" stroke="{INK}" stroke-width="{n(0.022 * D)}"/>')
        return ''.join(o), pts
    cid = f'sk3{uid}'
    o.append(f'<defs><clipPath id="{cid}"><circle r="{n(R)}"/>{chin_svg.replace(" fill=", " data-f=")}</clipPath></defs>')
    o.append(ear)
    o.append(f'<circle r="{n(R)}" fill="{skin}"/>')
    o.append(chin_svg)
    inner = []
    if sol:
        jd = (f"M{pt((-0.43 * D, 0.13 * D))} C{pt((-0.33 * D, 0.26 * D))} {pt((-0.08 * D, 0.27 * D))} "
              f"{pt((0.12 * D, 0.262 * D))} L{pt((0.50 * D, 0.262 * D))} L{pt((0.7 * D, 0.262 * D))} L{pt((0.7 * D, 0.9 * D))} "
              f"L{pt((-0.30 * D, 0.9 * D))} C{pt((-0.36 * D, 0.40 * D))} {pt((-0.40 * D, 0.24 * D))} {pt((-0.43 * D, 0.13 * D))} Z")
        inner.append(f'<path d="{jd}" fill="{ch["jaw"]}"/>')
        band = []
        a0, a1 = 118, 168
        for i in range(25):
            a = a0 + (a1 - a0) * i / 24
            band.append(polar(D, a, 0.01 * D))
        for i in range(25):
            a = a1 - (a1 - a0) * i / 24
            s_ = math.sin(math.pi * (a - a0) / (a1 - a0)) ** 0.5
            band.append(polar(D, a, -0.07 * D * s_ - 0.004 * D))
        inner.append(f'<path d="{poly(band)}" fill="{INK}"/>')
    else:
        jd = (f"M{pt((-0.7 * D, 0.10 * D))} L{pt((-0.42 * D, 0.11 * D))} C{pt((-0.30 * D, 0.33 * D))} {pt((0.0, 0.345 * D))} "
              f"{pt((0.18 * D, 0.345 * D))} L{pt((0.7 * D, 0.345 * D))} L{pt((0.7 * D, 0.9 * D))} L{pt((-0.7 * D, 0.9 * D))} Z")
        inner.append(f'<path d="{jd}" fill="{shade(skin, 0.10)}"/>')
        sb = [(-0.43 * D, -0.15 * D), (-0.35 * D, -0.24 * D), (-0.335 * D, 0.0), (-0.335 * D, 0.17 * D), (-0.36 * D, 0.262 * D),
              (-0.39 * D, 0.17 * D), (-0.41 * D, -0.02 * D)]
        inner.append(f'<path d="{closed_rounded(sb, [0, 0.02 * D, 0.03 * D, 0.03 * D, 0.004 * D, 0.03 * D, 0.03 * D])}" fill="{ch["hair"]}"/>')
    o.append(f'<g clip-path="url(#{cid})">' + ''.join(inner) + '</g>')
    if sol:
        o.append(m_svg)
    else:
        o.append(f'<path d="{pomp_round(D, '34')}" fill="{ch["hair"]}"/>')
        o.append(pomp_detail(ch, D, '34'))
    o.append(ear_c(ear_c_[0] + 0.012 * D, ear_c_[1], 0.13 * D, D))
    if not sol:
        o.append(f'<circle cx="{n(ring[0])}" cy="{n(ring[1])}" r="{n(0.05 * D)}" fill="none" stroke="{GOLD}" stroke-width="{n(0.022 * D)}"/>')
    # ---- eyes: near full width, far eye compressed, beyond the nose bridge; the pair shifts toward the facing side
    st = dict(x)
    fp_s = st['fp_s']
    w_n = E['W'] * D * (1 + (fp_s - 1) * 0.5)
    w_f = w_n * E['far_w']
    gap = E['gap'] * D
    shift = 0.10 * D
    span = w_n + gap + w_f
    xl = shift - span / 2
    cxn = xl + w_n / 2
    cxf = xl + w_n + gap + w_f / 2
    eyf = ey - (0.03 * D if not sol else 0.015 * D)
    stn = dict(st)
    stf = dict(st)
    if x.get('far_cov') is not None:
        stf['cov'] = x['far_cov']
    if tgt is not None:
        stn['gaze'] = gaze_from(tgt, cxn, ey, st, m=1, gain=2.0)
        stf['gaze'] = gaze_from(tgt, cxf, eyf, st, m=-1, gain=2.0)
    else:
        stf['gaze'] = (-st['gaze'][0], st['gaze'][1])
    eye_n, info_n = anime_eye(ch, stn, cxn, ey, 'front', D, uid + 'n', m=1, flip=facing)
    eye_f, info_f = anime_eye(ch, stf, cxf, eyf, 'front', D, uid + 'f', m=-1, flip=-facing, wscale=E['far_w'])
    o.append(f'<g clip-path="url(#{cid})">{eye_f}</g>')
    o.append(eye_n)
    arch = Bw['arch'] if x['brow_arch'] is None else x['brow_arch']
    arch2 = arch if x['brow2_arch'] is None else x['brow2_arch']
    bclip = f'bc3{uid}'
    o.append(f'<defs><clipPath id="{bclip}"><circle r="{n(R + 0.02 * D)}"/></clipPath></defs>')
    by_n = info_n['top'] - Bw['gap'] * D - Bw['t'] * D / 2 - x['brow_raise'] * D
    by_f = info_f['top'] - Bw['gap'] * D - Bw['t'] * D / 2 - (x['brow_raise'] + x['brow2_raise']) * D
    o.append(f'<g clip-path="url(#{bclip})">'
             + brow_svg(Bw['kind'], cxn + Bw['dx'] * D + 0.01 * D, by_n, Bw['L'] * D * 1.05, Bw['t'] * D, x['brow_tilt'], arch * D, D=D)
             + brow_svg(Bw['kind'], cxf + 0.0 * D, by_f, Bw['L'] * D * 0.70, Bw['t'] * D * 0.9, x['brow_tilt'], arch2 * D, mirror=True, D=D)
             + '</g>')
    # nose over the far eye's lower inner corner; its bridge is shaded inside the gap up past the eyes' mid-height
    o.append(f'<path d="{nose}" fill="{skin}"/>')
    o.append(f'<path d="{nshadow}" fill="{shade(skin, 0.13)}"/>')
    b0 = (N0[0] + 0.004 * D, N0[1] - 0.012 * D)
    bridge = [b0, (b0[0] + 0.030 * D, b0[1] + 0.01 * D), (0.205 * D, 0.13 * D), (0.15 * D, 0.13 * D), (0.142 * D, 0.03 * D)]
    o.append(f'<path d="{closed_rounded(bridge, [0.012 * D, 0.01 * D, 0.03 * D, 0.03 * D, 0.02 * D])}" fill="{shade(skin, 0.13)}"/>')
    if sol:
        o.append(f'<path d="M{pt((0.43 * D, 0.238 * D))} Q{pt((0.47 * D, 0.27 * D))} {pt((0.515 * D, 0.254 * D))}" fill="none" stroke="{MOUTHC}" '
                 f'stroke-width="{n(0.02 * D)}" stroke-linecap="round"/>')
    else:
        cx, cy = 0.608 * D, 0.170 * D
        o.append(f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(0.028 * D)}" ry="{n(0.013 * D)}" fill="{MOUTHC}" transform="rotate(-14,{n(cx)},{n(cy)})"/>')
        o.append(f'<path d="M{pt((0.54 * D, 0.11 * D))} Q{pt((0.50 * D, 0.15 * D))} {pt((0.535 * D, 0.193 * D))}" fill="none" stroke="{shade(skin, 0.40)}" '
                 f'stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    # mouth (modest)
    my = (0.835 if sol else 0.825) * D - R
    lw = 0.024 * D
    S = f'fill="none" stroke="{INK}" stroke-width="{n(lw)}" stroke-linecap="round" stroke-linejoin="round"'
    mm = x['mouth']
    mx0, mx1 = 0.15 * D, 0.36 * D
    if mm in ('smirk', 'smug'):
        o.append(f'<path d="M{pt((mx0, my + 0.004 * D))} Q{pt((0.26 * D, my + 0.02 * D))} {pt((mx1, my - 0.025 * D))}" {S}/>')
        o.append(f'<path d="M{pt((mx1 + 0.02 * D, my - 0.07 * D))} Q{pt((mx1 + 0.04 * D, my - 0.03 * D))} {pt((mx1 + 0.015 * D, my + 0.005 * D))}" fill="none" '
                 f'stroke="{shade(skin, 0.36)}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    elif mm == 'pout':
        o.append(f'<path d="M{pt((mx0, my + 0.02 * D))} Q{pt((0.25 * D, my - 0.01 * D))} {pt((mx1, my + 0.018 * D))}" {S}/>')
    elif mm == 'o':
        o.append(f'<ellipse cx="{n(0.26 * D)}" cy="{n(my + 0.01 * D)}" rx="{n(0.032 * D)}" ry="{n(0.04 * D)}" fill="{MOUTHC}" stroke="{INK}" stroke-width="{n(0.014 * D)}"/>')
    elif mm == 'wavy':
        pts_ = [(0.17 * D + 0.18 * D * i / 6, my + (0.012 * D if i % 2 else -0.006 * D)) for i in range(7)]
        o.append(f'<path d="{pline(pts_)}" {S}/>')
    elif mm == 'tight':
        o.append(f'<path d="M{pt((0.17 * D, my + 0.022 * D))} Q{pt((0.26 * D, my - 0.008 * D))} {pt((0.35 * D, my + 0.02 * D))}" {S}/>')
    elif mm == 'flat':
        o.append(f'<path d="M{pt((0.17 * D, my + 0.006 * D))} L{pt((0.34 * D, my + 0.006 * D))}" {S}/>')
    else:
        o.append(f'<path d="M{pt((0.18 * D, my + 0.008 * D))} Q{pt((0.26 * D, my + 0.014 * D))} {pt((0.34 * D, my + 0.004 * D))}" {S}/>')
    if sol:
        o.append(f'<path d="{sol_tuft(chin_c, D)}" fill="{INK}"/>')
    else:
        o.append(f'<path d="M{pt((0.30 * D, 0.175 * D))} Q{pt((0.215 * D, 0.215 * D))} {pt((0.19 * D, 0.275 * D))}" fill="none" '
                 f'stroke="{shade(skin, 0.30)}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    o.append(marks_svg(x, D, T, ch, '34'))
    for nm_, inf, w_ in (('near', info_n, w_n), ('far', info_f, w_f)):
        REG['metrics'].append(dict(uid=uid + nm_, name=ch['name'], view='34', fp_h=round(inf['fp_h'], 3), open_h=round(inf['open_h'], 3),
                                   eye_w=round(w_ / D, 3), iris_h=round(inf['iris_h'], 3), iris_frac=round(inf['iris_h'] / inf['fp_h'], 2),
                                   fp_top_depth=round((inf['top'] + R) / D, 3), pupil=round(inf['pupil'], 3),
                                   cluster_shift=round((xl + span / 2) / D, 3), gap=round(gap / D, 3), span=round(span / D, 3),
                                   far_outer_in=round((math.sqrt(R * R - eyf * eyf) - (cxf + w_f / 2)) / D, 3)))
    return ''.join(o), pts


def head_local(ch, x, D, uid, view, tgt=None, sil=False, facing=1):
    if view == '34':
        return head_34(ch, x, D, uid, tgt, sil, facing)
    return head_profile(ch, x, D, uid, tgt, sil, facing)


def to_world(q, C, facing, tilt):
    x_, y_ = rotv(q, tilt)
    return (C[0] + facing * x_, C[1] + y_)


def to_local(w, C, facing, tilt):
    v = sub(w, C)
    v = (v[0] * facing, v[1])
    return rotv(v, -tilt)


def head(ch, x, C, D, facing=1, tilt=0.0, uid='a', view='profile', tgt_world=None, sil=False):
    tgt = to_local(tgt_world, C, facing, tilt) if tgt_world is not None else None
    svg, pts = head_local(ch, x, D, uid, view, tgt, sil, facing)
    REG['heads'].append((C, D))
    REG['head_pts'].extend(to_world(p, C, facing, tilt) for p in pts)
    return f'<g transform="translate({pt(C)}) scale({facing},1) rotate({n(tilt)})">{svg}</g>'


def eye_world(ch, C, D, facing, tilt, view='profile'):
    E = ch['eye']
    ey = (E['depth'] - 0.5) * D
    if view == 'profile':
        R = D / 2
        W = E['Wp'] * D
        loc = (math.sqrt(R * R - ey * ey) - E['front'] * D - W * 0.25, ey)
    else:
        loc = (0.0, ey)
    return to_world(loc, C, facing, tilt)


# ---------------------------------------------------------------- cameo (window grandma)
GRAN = dict(name='gran', skin=SKIN_GRAN,
            eye=dict(kind='generic', H=0.32, W=0.24, Wp=0.18, tail=0.0, gap=0.10, depth=0.47, front=0.1,
                     lid=0.60, lid_tilt=0.0, low=0.0, band=0.03, crease=0.012,
                     iris=dict(base='#7A5236', sh='#5E3E28', li='#9C7354', ring='#4A3020', pupil='#2A1A10'),
                     ih=0.17, iw=0.15, ph=0.08, cut=0.03, ring=0.012, park='lid',
                     hl='dot', lash=0.035, lash_end='none', lower='none', lower_t=0.0, far_w=1.0, marks=('undereye',)))


def cameo_gran(C, D, uid, tgt_world=None):
    """Front view, generic cameo eye: 0.32 D, 60% lid, plain brown iris, single dot -- smaller and plainer than the 12."""
    R = D / 2
    skin = SKIN_GRAN
    o = [f'<g transform="translate({pt(C)})">']
    for s in (-1, 1):
        o.append(f'<ellipse cx="{n(s * (R + 0.005 * D))}" cy="{n(0.03 * D)}" rx="{n(0.065 * D)}" ry="{n(0.10 * D)}" fill="{skin}"/>')
    bc = (0, -R - 0.02 * D)
    o.append(f'<circle cx="{n(bc[0])}" cy="{n(bc[1])}" r="{n(0.13 * D)}" fill="{GREY_H}"/>')
    o.append(f'<path d="M{pt((bc[0] - 0.19 * D, bc[1] + 0.03 * D))} L{pt((bc[0] + 0.19 * D, bc[1] - 0.06 * D))}" stroke="{PLUM}" stroke-width="{n(0.026 * D)}" stroke-linecap="round"/>')
    o.append(f'<circle r="{n(R)}" fill="{skin}"/>')
    cid = f'gr{uid}'
    o.append(f'<defs><clipPath id="{cid}"><circle r="{n(R)}"/></clipPath></defs>')
    hd = (f"M{pt((-0.7 * D, 0.0 * D))} L{pt((-0.47 * D, 0.0 * D))} C{pt((-0.44 * D, -0.22 * D))} {pt((-0.26 * D, -0.33 * D))} "
          f"{pt((0, -0.34 * D))} C{pt((0.26 * D, -0.33 * D))} {pt((0.44 * D, -0.22 * D))} {pt((0.47 * D, 0.0 * D))} "
          f"L{pt((0.7 * D, 0.0 * D))} L{pt((0.7 * D, -0.8 * D))} L{pt((-0.7 * D, -0.8 * D))} Z")
    jw = (f"M{pt((-0.6 * D, 0.14 * D))} L{pt((-0.46 * D, 0.14 * D))} C{pt((-0.36 * D, 0.36 * D))} {pt((-0.18 * D, 0.32 * D))} "
          f"{pt((0, 0.40 * D))} C{pt((0.18 * D, 0.32 * D))} {pt((0.36 * D, 0.36 * D))} {pt((0.46 * D, 0.14 * D))} "
          f"L{pt((0.6 * D, 0.14 * D))} L{pt((0.6 * D, 0.8 * D))} L{pt((-0.6 * D, 0.8 * D))} Z")
    o.append(f'<g clip-path="url(#{cid})"><path d="{jw}" fill="{shade(skin, 0.10)}"/><path d="{hd}" fill="{GREY_H}"/>'
             f'<path d="M{pt((0, -0.34 * D))} L{pt((0, -0.6 * D))}" stroke="{GREY_HD}" stroke-width="{n(0.02 * D)}"/></g>')
    ey = -0.03 * D
    tl = to_local(tgt_world, C, 1, 0) if tgt_world else None
    for s in (-1, 1):
        ex = s * 0.17 * D
        st = X(cov=None, gaze=gaze_from(tl, ex, ey, X(), m=(1 if s < 0 else -1), gain=1.2) if tl else (0, 0.3))
        e, inf = anime_eye(GRAN, st, ex, ey, 'front', D, f'{uid}{s}', m=(1 if s < 0 else -1), flip=(1 if s < 0 else -1), show_crease=True)
        o.append(e)
        o.append(f'<path d="M{pt((ex - 0.08 * D, inf["top"] - 0.04 * D))} L{pt((ex + 0.08 * D, inf["top"] - 0.045 * D))}" stroke="{GREY_HD}" '
                 f'stroke-width="{n(0.045 * D)}" stroke-linecap="round"/>')
    o.append(f'<path d="{poly([(0.004 * D, -0.0 * D), (0.07 * D, 0.21 * D), (-0.03 * D, 0.22 * D)])}" fill="{shade(skin, 0.22)}"/>')
    my = 0.31 * D
    o.append(f'<path d="M{pt((-0.10 * D, my))} L{pt((0.10 * D, my))}" stroke="{INK}" stroke-width="{n(0.026 * D)}" stroke-linecap="round"/>')
    for s in (-1, 1):
        d = f"M{pt((s * 0.21 * D, my - 0.10 * D))} Q{pt((s * 0.26 * D, my - 0.02 * D))} {pt((s * 0.22 * D, my + 0.06 * D))}"
        o.append(f'<path d="{d}" fill="none" stroke="{shade(skin, 0.42)}" stroke-width="{n(0.02 * D)}" stroke-linecap="round"/>')
    o.append('</g>')
    return ''.join(o)


# =====================================================================================
# STICK-BODY RIG  (pure stick figure: neck stub, spine, shoulder bar, 2 arms, 2 legs; no clothing)
# =====================================================================================
# Both characters share the SAME ink family for every limb (no colour-coding by character).
# Near limbs = INK; far limbs = a slightly lighter ink so overlaps stay readable.
FAR_INK = mix(INK, '#8A8178', 0.22)
LOOK_SOL = dict(name='sol', limb=INK, far=FAR_INK, skin=SKIN_SOL, feet='tabi', acc=None,
                spine=0.95, thigh=0.74, shin=0.72, ua=0.64, fa=0.66, lw=0.064)
LOOK_SNOOT = dict(name='snoot', limb=INK, far=FAR_INK, skin=SKIN_SNOOT, feet='zori', acc='neckerchief', acc_col=TERRA,
                  spine=0.84, thigh=0.84, shin=0.80, ua=0.64, fa=0.66, lw=0.060)

SHOULDERS = dict(profile=(0.10, -0.10), twist=(0.035, -0.17), **{'34': (-0.25, 0.16)})
# stick hips: both legs leave (almost) the same point at the bottom of the spine
HIPS = dict(profile=(0.012, -0.012), twist=(0.012, -0.02), **{'34': (-0.03, 0.02)})


def stick(pts, w, color):
    """single-stroke ink line, round caps + round joins."""
    return (f'<path d="{pline(pts)}" fill="none" stroke="{color}" stroke-width="{n(w)}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def neck_geom(C, D, f, tilt, view, neck_lean=10.0):
    hid = 0.055 * D
    ax = {'profile': -0.10, 'twist': -0.10, '34': -0.07}[view] * D
    lean = neck_lean
    ysb = math.sqrt((D / 2) ** 2 - ax * ax)
    NT = to_world((ax, ysb - hid), C, f, tilt)
    sb0 = to_world((ax, ysb), C, f, 0.0)
    ndir = (f * -math.sin(math.radians(lean)), math.cos(math.radians(lean)))
    NB = add(sb0, mul(ndir, 0.12 * D))
    return NT, NB, ndir


def mitten(wrist, ang, D, f, color, thumb=-1, grip=False):
    L, W = 0.19 * D, 0.125 * D
    if grip:
        W *= 1.08
    tf = f'translate({pt(wrist)}) rotate({n(ang)})'
    body = (f'<g transform="{tf}"><rect x="{n(-W * 0.22)}" y="{n(-W / 2)}" width="{n(L + W * 0.22)}" height="{n(W)}" '
            f'rx="{n(W / 2)}" fill="{color}"/></g>')
    if grip:
        cx, cy, rx, ry = L * 0.46, thumb * W * 0.36, W * 0.42, W * 0.33
    else:
        cx, cy, rx, ry = L * 0.26, thumb * W * 0.50, W * 0.34, W * 0.26
    th = (f'<g transform="{tf}"><ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{color}" '
          f'transform="rotate({n(-22 * thumb)},{n(cx)},{n(cy)})"/></g>')
    return body, th


def foot_svg(kind, ankle, f, ang, D, shin_dir, leg_w, view='profile', far=False, sil=False):
    fl, ah = 0.30 * D, 0.07 * D
    if view == '34':
        fl *= 0.80
    verts = [(-0.28 * fl, -0.03 * D), (0.16 * fl, -0.03 * D), (0.62 * fl, ah * 0.28), (0.74 * fl, ah), (-0.30 * fl, ah)]
    dsh = closed_rounded(verts, [0.03 * D, 0.035 * D, 0.045 * D, 0.012 * D, 0.02 * D])
    tf = f'translate({pt(ankle)}) scale({f},1) rotate({n(ang)})'
    o = []

    def W(p):
        return add(ankle, (f * rotv(p, ang)[0], rotv(p, ang)[1]))
    sole_pts = [(-0.30 * fl, ah), (0.74 * fl, ah)]
    dark = INK if not far else '#1A1815'
    if kind == 'zori':
        zd = closed_rounded([(-0.36 * fl, ah - 1), (0.84 * fl, ah - 1), (0.84 * fl, ah + 0.045 * D), (-0.36 * fl, ah + 0.045 * D)], 0.018 * D)
        o.append(f'<path transform="{tf}" d="{zd}" fill="{INK if sil else WOOD_D}"/>')
        zd2 = closed_rounded([(-0.36 * fl, ah - 1), (0.84 * fl, ah - 1), (0.84 * fl, ah + 0.024 * D), (-0.36 * fl, ah + 0.024 * D)], 0.01 * D)
        o.append(f'<path transform="{tf}" d="{zd2}" fill="{INK if sil else ZORI}"/>')
        o.append(f'<path transform="{tf}" d="{dsh}" fill="{dark if not sil else INK}"/>')
        if not sil:
            o.append(f'<path transform="{tf}" d="M{n(0.52 * fl)},{n(ah * 0.22)} L{n(0.12 * fl)},{n(ah - 2)}" stroke="{TERRA}" '
                     f'stroke-width="{n(0.024 * D)}" stroke-linecap="round" fill="none"/>')
        sole_pts = [(-0.36 * fl, ah + 0.045 * D), (0.84 * fl, ah + 0.045 * D)]
    else:
        o.append(f'<path transform="{tf}" d="{dsh}" fill="{dark if not sil else INK}"/>')
        a = ang_of(shin_dir) - 90
        c = add(ankle, mul(shin_dir, -0.035 * D))
        bw = leg_w + 0.035 * D
        col = INK if sil else (PALE if not far else shade(PALE, 0.15))
        o.append(f'<rect transform="translate({pt(c)}) rotate({n(a)})" x="{n(-bw / 2)}" y="{n(-0.028 * D)}" '
                 f'width="{n(bw)}" height="{n(0.056 * D)}" rx="{n(0.02 * D)}" fill="{col}"/>')
    REG['foot_pts'].extend(W(p) for p in sole_pts)
    return ''.join(o)


def broom_svg(a, b, D, fan=0.40, sil=False):
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


def spine_point(samp, H, Lsp, t):
    """Point + unit tangent (down the spine) at parameter t (can exceed [0,1])."""
    if t <= 0:
        tg = unit(sub(samp[3], samp[0]))
        return add(samp[0], mul(tg, t * Lsp)), tg
    if t >= 1:
        tg = unit(sub(samp[-1], samp[-4]))
        return add(samp[-1], mul(tg, (t - 1) * Lsp)), tg
    fi = t * (len(samp) - 1)
    i = int(fi)
    p = lerp(samp[i], samp[min(i + 1, len(samp) - 1)], fi - i)
    tg = unit(sub(samp[min(i + 2, len(samp) - 1)], samp[max(i - 2, 0)]))
    return p, tg


def body(look, C, D, f, tilt, pose, view='profile', sil=False):
    lw = look['lw'] * D
    limb, farc, skin = look['limb'], look['far'], look['skin']
    if sil:
        limb = farc = skin = INK
    NT, NB, ndir = neck_geom(C, D, f, tilt, view, pose.get('neck_lean', 10.0))
    Y = add(NB, mul(ndir, 0.075 * D))
    lean, bulge = pose.get('spine', (4.0, 0.05))
    Lc = look['spine'] * D
    H = pose.get('hip') or add(Y, (-f * math.sin(math.radians(lean)) * Lc, math.cos(math.radians(lean)) * Lc))
    sd = unit(sub(H, Y))
    perp = (-sd[1], sd[0])
    if perp[0] * f > 0:
        perp = mul(perp, -1)          # perp points BACK
    c1 = add(lerp(Y, H, 0.33), mul(perp, bulge * D * 1.3))
    c2 = add(lerp(Y, H, 0.70), mul(perp, bulge * D * 0.6))
    samp = [bez3(Y, c1, c2, H, i / 120) for i in range(121)]
    Lsp = sum(math.dist(samp[i], samp[i + 1]) for i in range(120))
    fwd = mul(perp, -1)
    sn, sf = SHOULDERS[view]
    hn, hf = HIPS[view]
    down = unit(sub(samp[6], samp[0]))
    yoke = (-down[1], down[0])
    if yoke[0] * f < 0:
        yoke = mul(yoke, -1)          # forward
    S = {'arm_n': add(Y, mul(yoke, sn * D)), 'arm_f': add(add(Y, mul(yoke, sf * D)), (0, -0.01 * D))}
    HP = {'leg_n': add(H, (f * hn * D, 0)), 'leg_f': add(H, (f * hf * D, -0.005 * D))}
    J = dict(NT=NT, NB=NB, Y=Y, H=H, S=S, HP=HP, spine_len=Lsp, ndir=ndir, fwd=fwd, yoke=yoke, samp=samp, down=down)
    Lyr = {}
    arms = {}
    for key in ('arm_f', 'arm_n'):
        spec = pose[key]
        Sx = S[key]
        a_len, b_len = look['ua'] * D, look['fa'] * D
        if 'grip' in spec:
            g = spec['grip']
            j, w = ik2(Sx, g, a_len, b_len, spec.get('bend', (-f, 0)), spec.get('straight', False))
            fd = unit(sub(w, j))
            g2 = add(g, mul(fd, -0.19 * D * 0.46))
            j, w = ik2(Sx, g2, a_len, b_len, spec.get('bend', (-f, 0)), spec.get('straight', False))
        elif 'dir' in spec:
            dv = (math.sin(math.radians(spec['dir'])), -math.cos(math.radians(spec['dir'])))
            j = add(Sx, mul(dv, a_len))
            d2 = spec['dir'] + spec.get('bend_deg', 0)
            dv2 = (math.sin(math.radians(d2)), -math.cos(math.radians(d2)))
            w = add(j, mul(dv2, b_len))
        else:
            j, w = ik2(Sx, spec['w'], a_len, b_len, spec.get('bend', (-f, 0)), spec.get('straight', False))
        col = farc if key == 'arm_f' else limb
        mcol = shade(skin, 0.12) if (key == 'arm_f' and not sil) else skin
        line = stick([Sx, j, w], lw, col)
        hang = spec.get('hand', ang_of(sub(w, j)))
        grip = 'grip' in spec or spec.get('fist', False) or spec.get('grip_auto', False)
        mb, mt = mitten(w, hang, D, f, mcol, spec.get('thumb', -1), grip)
        arms[key] = dict(line=line, mit=mb, thumb=mt)
        J[key] = (j, w)
    legs = {}
    for key in ('leg_f', 'leg_n'):
        spec = pose[key]
        Hx = HP[key]
        j, a = ik2(Hx, spec['a'], look['thigh'] * D, look['shin'] * D, spec.get('bend', (f, 0)), spec.get('straight', False))
        col = farc if key == 'leg_f' else limb
        s = stick([H, Hx, j, a], lw * 1.03, col)
        shin_dir = unit(sub(a, j))
        fs = foot_svg(look['feet'], a, f, spec.get('foot', 0), D, shin_dir, lw, view, far=(key == 'leg_f'), sil=sil)
        legs[key] = s + fs
        J[key] = (j, a)
    # spine: one curved ink stroke from the shoulder line down to the hip; shoulder bar through Y
    spine = stick(samp[::4] + [samp[-1]], lw * 1.04, limb)
    shoulders = stick([S['arm_f'], Y, S['arm_n']], lw, limb)
    nw = 0.17 * D
    neck = tube([NT, NB], [nw, nw], skin)
    if not sil:
        mid = lerp(NT, NB, 0.55)
        neck += tube([NT, mid], [nw, nw * 0.98], shade(skin, 0.12))
    acc = neckerchief(look, J, D, f, view, pose, sil) if look.get('acc') == 'neckerchief' else ''
    prop = ''
    br = pose.get('broom')
    if pose.get('broom_auto'):
        key, t = pose['broom_auto'][:2]
        jj, ww = J[key]
        hd = pose[key].get('hand')
        mdir = (math.cos(math.radians(hd)), math.sin(math.radians(hd))) if hd is not None else unit(sub(ww, jj))
        mc = add(ww, mul(mdir, 0.10 * D))
        Lb = 2.78 * D
        if t == 'down':
            fl_ = pose['broom_auto'][2]
            br = dict(a=(mc[0], fl_ - Lb), b=(mc[0], fl_), layer='front')
        else:
            br = dict(a=add(mc, (0, t * Lb)), b=add(mc, (0, -(1 - t) * Lb)), layer='front')
        pose['broom'] = br
    if br:
        prop = broom_svg(br['a'], br['b'], D, br.get('fan', 0.40), sil)
    Lyr.update(far_leg=legs['leg_f'], far_arm=arms['arm_f']['line'] + arms['arm_f']['mit'],
               far_thumb=arms['arm_f']['thumb'], spine=spine, neck=neck, shoulders=shoulders, acc=acc,
               near_leg=legs['leg_n'], near_arm=arms['arm_n']['line'] + arms['arm_n']['mit'],
               near_thumb=arms['arm_n']['thumb'], prop=prop)
    J['broom'] = br
    return Lyr, J


def neckerchief(look, J, D, f, view, pose, sil):
    """the ONE neck-level accessory: Snoot's small terracotta neckerchief knot (shrunk from the old tenugui)."""
    NB, yoke = J['NB'], J['yoke']
    col = INK if sil else look['acc_col']
    dk = INK if sil else shade(look['acc_col'], 0.18)
    tw = 0.066 * D
    o = []
    if view == '34':
        b0 = add(NB, add(mul(yoke, -0.095 * D), (0, -0.005 * D)))
        b1 = add(NB, add(mul(yoke, 0.085 * D), (0, 0.0)))
        mid = add(lerp(b0, b1, 0.5), (0, 0.03 * D))
        o.append(tube([b0, mid, b1], [tw, tw * 1.05, tw * 0.95], col))
        kn = add(lerp(b0, mid, 0.55), (0.0, 0.025 * D))
        tails = ((-5, 0.12), (12, 0.095))
    else:
        b0 = add(NB, (f * -0.11 * D, -0.03 * D))
        b1 = add(NB, (f * 0.09 * D, 0.025 * D))
        o.append(tube([b0, lerp(b0, b1, 0.5), b1], [tw, tw, tw * 0.95], col))
        kn = add(b1, (f * 0.005 * D, 0.01 * D))
        tails = ((-6, 0.11), (16, 0.085))
    lag = pose.get('tie_lag', 0)
    for dl, ln in tails:
        e = add(kn, rotv((0, ln * D), f * (dl + lag)))
        o.append(tube([kn, e], [0.044 * D, 0.038 * D], dk if dl > 0 else col))
    o.append(f'<circle cx="{n(kn[0])}" cy="{n(kn[1])}" r="{n(0.036 * D)}" fill="{col}"/>')
    return ''.join(o)


def character(ch, x, look, C, D, f, tilt, uid, pose, view='profile', head_view=None, shadow='', marks='', sil=False, tgt_world=None):
    Lyr, J = body(look, C, D, f, tilt, pose, view, sil)
    layer = pose.get('broom', {}).get('layer', 'front') if pose.get('broom') else None
    o = [shadow]
    o.append(Lyr['far_leg'])
    o.append(Lyr['far_arm'])
    if layer == 'behind':
        o.append(Lyr['prop'])
        o.append(Lyr['far_thumb'])
    o.append(Lyr['spine'])
    o.append(Lyr['near_leg'])
    o.append(Lyr['neck'])
    o.append(Lyr['shoulders'])
    o.append(Lyr['acc'])
    over = pose.get('near_over_head', False)
    if not over:
        o.append(Lyr['near_arm'])
    hv = head_view or ('34' if view == '34' else 'profile')
    o.append(head(ch, x, C, D, f, tilt, uid, hv, tgt_world, sil))
    if over:
        o.append(Lyr['near_arm'])
    if layer == 'front':
        o.append(Lyr['prop'])
        o.append(Lyr['far_thumb'])
    elif layer is None:
        o.append(Lyr['far_thumb'])
    o.append(Lyr['near_thumb'])
    o.append(marks)
    return ''.join(o), J



def dummy_svg(piv, ang, s=1.0, cord=26, arms=((-1, 208, 96), (1, -28, 96)), opacity=1.0, sil=False):
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


# =====================================================================================
# SCENE (1080 x 1920): rooftop dojo at dusk -- nose-to-nose under the moon
# =====================================================================================
SC_FLOOR = 1745
RAIL_Y = 330
D_SOL = 300
D_SNO = 292
SOL_TILT = -17
SNO_TILT = -6


def sol_scene_x():
    # stare-down: big open eye, lid only 12 % with a slight slant, iris locked on Snoot's eye, blade glint
    return X(cov=0.12, tilt=6, brow_raise=-0.005, brow_tilt=10, mouth='smirk')


def snoot_scene_x():
    # haughty: big domed gumdrop eye (lid 16 %) on its flat lower lid, looking down his nose; near brow cocked
    return X(cov=0.16, low=0.04, brow_raise=0.05, brow_tilt=-10, brow_arch=0.075, mouth='sneer', nose_up=6,
             flare=True, marks=['snort', 'sweat1'])


def scene_svg(sil=False):
    for k in ('heads', 'head_pts', 'foot_pts'):
        REG[k].clear()
    Wc, Hc = 1080, 1920
    FL = SC_FLOOR
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hc}" viewBox="0 0 {Wc} {Hc}">']
    if sil:
        o.append(f'<rect width="{Wc}" height="{Hc}" fill="#FFFFFF"/>')
    else:
        o.append(f'<rect width="{Wc}" height="{Hc}" fill="{DUSK}"/>')
        for y0, col in ((560, '#4C6580'), (720, '#62778F'), (860, '#8192A7'), (1010, '#93A0B0')):
            o.append(f'<rect y="{y0}" width="{Wc}" height="{1290 - y0}" fill="{col}"/>')
        roofs = "M0,1285 L0,1198 L46,1198 L36,1184 Q84,1176 124,1158 Q156,1172 182,1180 L174,1190 L194,1190 L194,1285 Z"
        o.append(f'<path d="{roofs}" fill="{ROOF}"/>')
        o.append(f'<circle cx="560" cy="1060" r="430" fill="{MOON}"/>')
        o.append(f'<rect y="1280" width="{Wc}" height="{FL + 45 - 1280}" fill="{SAND}"/>')
        o.append(f'<rect y="1280" width="{Wc}" height="12" fill="{PLANK}"/>')
        for y in (1318, 1362, 1416, 1482, 1560):
            o.append(f'<rect y="{y}" width="{Wc}" height="4" fill="{PLANK}"/>')
        for x_, y0, y1 in ((214, 1292, 1362), (640, 1362, 1482), (420, 1482, FL + 45), (900, 1292, 1416), (760, 1560, FL + 45)):
            o.append(f'<rect x="{x_}" y="{y0}" width="4" height="{y1 - y0}" fill="{PLANK}"/>')
        o.append(f'<rect y="{FL + 45}" width="{Wc}" height="{Hc - FL - 45}" fill="{FLOOR_D}"/>')
        o.append(f'<rect y="{FL + 45}" width="{Wc}" height="10" fill="{shade(FLOOR_D, 0.10)}"/>')
        # neighbour's tea-house wall + lit window (the witness)
        o.append(f'<path d="M780,0 L1080,0 L1080,230 L780,230 Z" fill="{ROOF}"/>')
        o.append(f'<path d="M760,0 L1080,0 L1080,18 L760,18 Z" fill="{INK}"/>')
        o.append(f'<rect x="812" y="34" width="196" height="196" fill="{LAMP}"/>')
        for x_ in (861, 959):
            o.append(f'<rect x="{x_}" y="34" width="4" height="196" fill="{shade(LAMP, 0.10)}"/>')
        o.append(f'<rect x="812" y="112" width="196" height="4" fill="{shade(LAMP, 0.10)}"/>')
        o.append(f'<rect y="226" width="{Wc}" height="34" fill="{INK}"/>')
        o.append(f'<rect y="{RAIL_Y - 11}" width="{Wc}" height="22" fill="{INK}"/>')
        o.append(f'<rect x="36" y="{RAIL_Y - 22}" width="20" height="44" rx="4" fill="{INK}"/>')
        for hx in (300, 1044):
            o.append(f'<rect x="{hx - 5}" y="260" width="10" height="{RAIL_Y - 270}" fill="{INK}"/>')
        for rx in (300, 560, 780):
            o.append(f'<circle cx="{rx}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7"/>')

    # ---------------- heads, nose to nose
    sx, nx = sol_scene_x(), snoot_scene_x()
    Cs = (309, 862)
    tip_s = to_world(nose_profile(SOL, sx, D_SOL)[2], Cs, 1, SOL_TILT)
    tn_loc = nose_profile(SNOOT, nx, D_SNO)[2]
    tw = to_world(tn_loc, (0, 0), -1, SNO_TILT)
    Cn = (tip_s[0] + 12 - tw[0], tip_s[1] - 10 - tw[1])
    eye_s = eye_world(SOL, Cs, D_SOL, 1, SOL_TILT)
    eye_n = eye_world(SNOOT, Cn, D_SNO, -1, SNO_TILT)
    if not sil:
        gC = (910, 128)
        gD = 170
        o.append(f'<path d="M{gC[0] - 92},230 Q{gC[0] - 80},{gC[1] + 96} {gC[0]},{gC[1] + 92} Q{gC[0] + 80},{gC[1] + 96} {gC[0] + 92},230 Z" fill="{PLUM}"/>')
        o.append(tube([(gC[0], gC[1] + 70), (gC[0], gC[1] + 100)], [0.17 * gD, 0.17 * gD], SKIN_GRAN))
        o.append(f'<path d="M{gC[0] - 44},{gC[1] + 94} L{gC[0]},230 L{gC[0] + 44},{gC[1] + 94}" fill="none" stroke="{PALE}" stroke-width="12" stroke-linejoin="round"/>')
        o.append(cameo_gran(gC, gD, 'gran', tgt_world=lerp(eye_s, eye_n, 0.5)))
        o.append(f'<rect x="800" y="222" width="220" height="10" fill="{INK}"/>')
    ah = 0.07
    marks = []
    if not sil:
        marks.append(dotted(f"M990,{RAIL_Y + 30} L150,{RAIL_Y + 30}", PALE, 6, (2, 16)))
        for gx in (760, 470):
            marks.append(f'<circle cx="{gx}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7" opacity="0.5"/>')
        for dy, x0, x1 in ((-12, 124, 176), (0, 130, 196), (12, 124, 170)):
            marks.append(f'<path d="M{x0},{RAIL_Y + 30 + dy} L{x1},{RAIL_Y + 30 + dy}" stroke="{PALE}" stroke-width="5" stroke-linecap="round"/>')
    gpiv = (1030, RAIL_Y + 46)
    if not sil:
        o.append(f'<circle cx="{gpiv[0]}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7" opacity="0.5"/>')
        o.append(dummy_svg(gpiv, 0, 0.80, cord=(880 - gpiv[1]) / 0.80, arms=((-1, 200, 96), (1, -20, 96)), opacity=0.5))

    # ---------------- SOL: low bow-legged stance, broom behind his back, bristles up past the rear shoulder
    D = D_SOL
    bro_b = (104, 640)
    u = unit(sub((262, 1480), bro_b))
    bro_a = add(bro_b, mul(u, 2.78 * D))
    sol_pose = dict(
        spine=(7.0, 0.08), neck_lean=4,
        leg_n=dict(a=(Cs[0] + 0.62 * D, FL - ah * D), bend=(1, 0.0), foot=0),
        leg_f=dict(a=(Cs[0] - 0.52 * D, FL - ah * D), bend=(1, 0), foot=0),
        broom=dict(a=bro_a, b=bro_b, layer='behind'),
        # near elbow forward, far elbow back: two clearly separate sticks meeting on the broom handle
        arm_n=dict(grip=lerp(bro_a, bro_b, 0.02), bend=(1, 0.15), thumb=-1),
        arm_f=dict(grip=lerp(bro_a, bro_b, 0.085), bend=(-1, -0.15), thumb=-1),
    )
    sh_s = '' if sil else f'<ellipse cx="{n(Cs[0] + 20)}" cy="{FL + 3}" rx="200" ry="14" fill="{PLANK}"/>'
    s_svg, sJ = character(SOL, sx, LOOK_SOL, Cs, D, 1, SOL_TILT, 'sol', sol_pose, view='twist', head_view='profile',
                          shadow=sh_s, sil=sil, tgt_world=eye_n)
    # dummy behind Sol: its peg arm meets the bristles
    dpiv = (64, RAIL_Y + 46)
    dang, ds, dcord = 3, 0.64, 22
    contact = (bro_b[0] - 36, bro_b[1] - 4)
    q = mul(rotv(sub(contact, dpiv), dang), 1 / ds)
    ry = q[1] - dcord - 40
    r0 = (50, dcord + ry)
    phi = math.degrees(math.atan2(q[1] - r0[1], q[0] - r0[0]))
    dm = dummy_svg(dpiv, dang, ds, cord=dcord, arms=((-1, 200, 120), (1, phi, ry)), sil=sil)

    # ---------------- SNOOT: chest out, leaning in, rear hook kick into the hanging dummy, preening his quiff
    D = D_SNO
    sn_pose = dict(
        spine=(-11.0, -0.06), neck_lean=16,
        leg_f=dict(a=(Cn[0] - 0.42 * D, FL - ah * D - 0.045 * D), bend=(-1, 0), foot=0),
        leg_n=dict(a=(992, 1050), bend=(1, 0.5), foot=-150),
        # akimbo: both fists ON the hip joint; near elbow juts forward (toward Sol), far elbow back behind the kick
        arm_n=dict(w=(Cn[0] - 0.15 * D, Cn[1] + 1.40 * D), bend=(-1, -0.1), hand=15, thumb=1, fist=True),
        arm_f=dict(w=(Cn[0] - 0.06 * D, Cn[1] + 1.48 * D), bend=(1, -0.2), hand=160, thumb=1, fist=True),
        tie_lag=-8,
    )
    sh_n = '' if sil else f'<ellipse cx="{n(Cn[0] + 10)}" cy="{FL + 3}" rx="96" ry="12" fill="{PLANK}"/>'
    n_svg, nJ = character(SNOOT, nx, LOOK_SNOOT, Cn, D, -1, SNO_TILT, 'snoot', sn_pose, view='profile', shadow=sh_n,
                          sil=sil, tgt_world=eye_s)
    if not sil:
        o.append(dm)
    o.append(s_svg)
    o.append(n_svg)
    if not sil:
        foot = nJ['leg_n'][1]
        knee = nJ['leg_n'][0]
        marks.append(dotted(f"M{n(knee[0] - 10)},{n(knee[1] + 120)} Q{n(knee[0] + 40)},{n(knee[1] + 10)} {n(foot[0] + 34)},{n(foot[1] + 30)}", PALE, 7, (2, 17)))
        marks.append(f'<path d="{star4(contact[0], contact[1] - 6, 52, 11, 0)}" fill="{PALE}"/>')
        marks.append(f'<path d="{star4(contact[0], contact[1] - 6, 23, 5, 45)}" fill="{INK}"/>')
        hands = sJ['arm_n'][1]
        R2 = math.dist(hands, bro_b)
        a1 = ang_of(sub(bro_b, hands))
        marks.append(dotted(arc_d(hands, R2 + 8, a1 + 4, a1 + 13), PALE, 7, (2, 17)))
        for r, a0_, a1_ in ((222, 64, 80), (250, 66, 80)):
            marks.append(f'<path d="{arc_d(dpiv, r, a0_, a1_)}" fill="none" stroke="{PALE}" stroke-width="6" stroke-linecap="round"/>')
        o.append(f'<circle cx="{dpiv[0]}" cy="{RAIL_Y + 30}" r="18" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    o.append(''.join(marks))
    o.append('</svg>')
    sol_top = min(p[1] for p in REG['head_pts'][:0] or [(0, 0)])
    info = dict(Cs=Cs, Cn=tuple(round(v) for v in Cn), eye_s=tuple(round(v) for v in eye_s), eye_n=tuple(round(v) for v in eye_n),
                tip_s=tuple(round(v) for v in tip_s), sn_knee=tuple(round(v) for v in nJ['leg_n'][0]),
                sn_foot=tuple(round(v) for v in nJ['leg_n'][1]), sol_hip=tuple(round(v) for v in sJ['H']),
                sn_hip=tuple(round(v) for v in nJ['H']))
    return '\n'.join(o), info


# =====================================================================================
# FACES (1080 x 1080): Sol's head, 3 x 2
# =====================================================================================
FACE_SET = [
    # 1 neutral: wide-open rest eye (lid 17 %, 5 deg toward the nose), iris toward the facing side, blade glint
    ('neutral', X(gaze=(1.0, 0.1), mouth='line')),
    # 2 surprised (pop, <= 8 frames): no lid, footprint 0.58 D, round iris shrinks to ~54 % of the eye, brows jump
    ('surprised', X(cov=0.0, tilt=0, fp_s=0.58 / 0.53, iris_s=0.78, pupil_s=0.62, park='free', gaze=(0.2, 0.0),
                    brow_raise=0.05, brow_tilt=-6, brow_arch=0.03, mouth='o', marks=['emanata'])),
    # 3 angry glare: OPEN eye, lid slants hard (28 deg) so only the inner corner is cut; pinned pupil; brows crush down
    ('angry', X(cov=0.10, tilt=36, low=0.12, low_tilt=-10, iris_s=0.95, pupil_s=0.58, gaze=(0.55, 0.05), brow_raise=-0.035, brow_tilt=28,
                brow_arch=0.0, mouth='tight', flare=True, marks=['snort'])),
    # 4 smug win (half-lid #1): upper lid 42 %, lower lid up in an upward curve, glint flashes
    ('smug', X(cov=0.42, tilt=4, low=0.16, low_curve=0.06, hl='flash', gaze=(1.0, -0.15), brow_raise=0.02, brow2_raise=0.05,
               brow_tilt=-6, brow_arch=0.03, brow2_arch=0.05, mouth='smirk', nose_up=6)),
    # 5 panic: lids fly open, outer ends droop (worry slant), iris shrinks to ~51 %, eyes dart back, outline wobble, sweat
    ('panic', X(cov=0.07, tilt=-24, fp_s=0.56 / 0.53, iris_s=0.72, pupil_s=0.50, park='free', wobble=True, gaze=(-0.45, 0.25),
                brow_raise=0.05, brow_tilt=-16, brow_arch=0.02, mouth='wavy', marks=['sweat', 'shake'])),
    # 6 exasperated side-eye (half-lid #2): dead flat lid 46 %, highlights off, irises slide to the back corners
    ('side_eye', X(cov=0.46, tilt=0, low=0.04, hl='off', gaze=(-1.0, 0.1), brow_raise=-0.01, brow_tilt=-3, brow_arch=0.0,
                   brow2_raise=0.03, mouth='flat', marks=['huff'])),
]


def faces_svg(sil=False):
    """Sol's head in 3/4 (facing viewer's left, like hero.svg) so both huge eyes act."""
    for k in ('heads', 'head_pts', 'foot_pts'):
        REG[k].clear()
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">']
    o.append(f'<rect width="1080" height="1080" fill="{"#FFFFFF" if sil else SAND}"/>')
    D = 240
    f = -1
    look = LOOK_SOL
    for i, (nm, x) in enumerate(FACE_SET):
        cx0 = (i % 3) * 360
        cy0 = (i // 3) * 540
        C = (cx0 + 184, cy0 + 278)
        if not sil:
            o.append(f'<circle cx="{n(C[0])}" cy="{n(C[1] + 6)}" r="170" fill="{PALE}"/>')
        NT = (C[0] - f * 0.06 * D, C[1] + 0.40 * D)
        NB = (C[0] - f * 0.08 * D, C[1] + 0.68 * D)
        o.append(tube([NT, NB], [0.17 * D, 0.17 * D], INK if sil else look['skin']))
        if not sil:
            o.append(tube([NT, lerp(NT, NB, 0.5)], [0.17 * D, 0.17 * D], shade(look['skin'], 0.12)))
        def P(dx, dy):
            return (NB[0] + f * dx * D, NB[1] + dy * D)
        # stick body cut-off: just the shoulder bar under the neck stub (same 3/4 offsets as the body rig)
        sn, sf = SHOULDERS['34']
        Ysh = P(0.0, 0.075)
        o.append(stick([(Ysh[0] + f * sf * D, Ysh[1] - 0.01 * D), Ysh, (Ysh[0] + f * sn * D, Ysh[1])], look['lw'] * D, INK))
        o.append(head(SOL, x, C, D, f, 0, f'f{i}', '34', None, sil))
    o.append('</svg>')
    return '\n'.join(o), dict(n=len(FACE_SET))


# =====================================================================================
# SOLO (540 x 1080): character alone, 3/4 toward viewer's left, soles on y=1010, 900 px tall
# =====================================================================================
def solo_pose(which, C, D):
    ah = 0.07 * D
    if which == 'hero':
        FL0 = C[1] + 3.02 * D
        pose = dict(
            spine=(6.0, 0.06), neck_lean=8,
            leg_f=dict(a=(C[0] - 0.40 * D, FL0 - ah), bend=(-1, 0.05), foot=-4),
            leg_n=dict(a=(C[0] + 0.36 * D, FL0 - ah), bend=(1, 0.05), foot=10),
            broom_auto=('arm_f', 'down', FL0 + 1),
            arm_f=dict(dir=214, bend_deg=-16, thumb=1, grip_auto=True, hand=180),
            # free fist planted ON the hip joint, elbow out
            arm_n=dict(w=(C[0] + 0.31 * D, C[1] + 1.60 * D), bend=(1, -0.2), hand=172, thumb=-1, fist=True),
        )
        x = X(brow_raise=0.0, brow_tilt=5, mouth='smirk')
        return pose, x, 4.0, (C[0] - 900, C[1] + 20)
    FL0 = C[1] + 3.16 * D
    pose = dict(
        spine=(-4.0, -0.07), neck_lean=14,
        leg_f=dict(a=(C[0] - 0.42 * D, FL0 - ah - 0.045 * D), bend=(-1, 0.1), foot=-8),
        leg_n=dict(a=(C[0] + 0.16 * D, FL0 - ah - 0.045 * D), bend=(-0.3, 0), foot=6),
        # hands on hips: near hand flat on the hip joint, elbow out wide; far fist on the hip
        arm_n=dict(w=(C[0] + 0.24 * D, C[1] + 1.36 * D), bend=(1, -0.2), hand=128, thumb=-1),
        arm_f=dict(w=(C[0] - 0.15 * D, C[1] + 1.58 * D), bend=(-1, -0.5), hand=-18, thumb=-1, fist=True),
        tie_lag=4,
    )
    x = X(gaze=(1.0, 0.45), brow_raise=0.05, brow2_raise=-0.045, brow_arch=0.075, mouth='pout')
    return pose, x, -8.0, (C[0] - 380, C[1] + 520)


SOLO_TF = {}


def solo_svg(which, sil=False):
    for k in ('heads', 'head_pts', 'foot_pts'):
        REG[k].clear()
    ch, look = (SOL, LOOK_SOL) if which == 'hero' else (SNOOT, LOOK_SNOOT)
    D = 240.0
    f = -1
    C = (290.0, 300.0)
    pose, x, tilt, tgt = solo_pose(which, C, D)
    fig, J = character(ch, x, look, C, D, f, tilt, which[:2], pose, '34', None, '', sil=sil, tgt_world=tgt)
    top = min(p[1] for p in REG['head_pts'])
    sole = max(p[1] for p in REG['foot_pts'])
    target = 900.0
    xs_all = [p[0] for p in REG['head_pts']] + [p[0] for p in REG['foot_pts']]
    cxm = (min(xs_all) + max(xs_all)) / 2
    # pixel calibration: a previous render's measured top/bottom (sub-pixel) replaces the analytic extremes
    cal = {}
    try:
        import json
        cal = json.load(open(os.path.join(HERE, 'calib.json'))).get(which, {})
    except Exception:
        cal = {}
    if cal:
        sc0, tx0, ty0 = cal['sc'], cal['tx'], cal['ty']
        top = (cal['top_px'] - ty0) / sc0
        sole = (cal['bot_px'] - ty0) / sc0
    h = sole - top
    sc = target / h
    tx = 270 - sc * cxm
    ty = 1010 - sc * sole
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="1080" viewBox="0 0 540 1080">']
    o.append(f'<rect width="540" height="1080" fill="{"#FFFFFF" if sil else LINEUP_BG}"/>')
    if not sil:
        o.append(f'<ellipse cx="270" cy="1013" rx="190" ry="14" fill="#D9D4CB"/>')
    o.append(f'<g transform="translate({n(tx)},{n(ty)}) scale({sc:.5f})">{fig}</g>')
    o.append('</svg>')
    SOLO_TF[which] = dict(sc=sc, tx=tx, ty=ty)
    return '\n'.join(o), dict(scale=round(sc, 4), D_eff=round(D * sc, 1), head_ratio=round(D / h, 3),
                              top=round(ty + sc * top, 1), sole=round(ty + sc * sole, 1), spine=round(J['spine_len'] / D, 3),
                              eye_over_H=round(ch['eye']['H'] * D / h, 3))

if __name__ == '__main__':
    for nm, fn in (('scene', lambda s: scene_svg(sil=s)), ('faces', lambda s: faces_svg(sil=s)),
                   ('hero', lambda s: solo_svg('hero', sil=s)), ('partner', lambda s: solo_svg('partner', sil=s))):
        REG['metrics'].clear()
        sv, info = fn(False)
        open(os.path.join(HERE, f'{nm}.svg'), 'w').write(sv)
        print(nm, info)
        if nm in ('faces', 'scene'):
            for mtr in REG['metrics']:
                print('   ', mtr)
        open(os.path.join(HERE, f'{nm}_sil.svg'), 'w').write(fn(True)[0])
    import json
    json.dump(SOLO_TF, open(os.path.join(HERE, 'solo_tf.json'), 'w'))
