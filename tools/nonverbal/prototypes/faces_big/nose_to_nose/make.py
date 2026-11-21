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
  Stick limbs (flat tapered strokes) + ONE costume surface on the torso (Sol: navy hanten + sage
  apron, Snoot: striped vest + terracotta tenugui) so the round heads never read as lollipops.
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
SOL = dict(
    name='sol', skin=SKIN_SOL, hair=INK,
    eye=dict(shape='almond', w=0.36, h=0.32, lid=0.35, depth=0.42, x_prof=0.195, pr=0.060),
    brow=dict(kind='wedge', t=0.085, L=0.30, gap=0.06, dx=-0.005, arch=0.012),
    nose='wedge', mouth_y=0.265, chin=0.885, chin_r=(0.055, 0.058),
    rim=0.021, lidw=0.035,
)
SNOOT = dict(
    name='snoot', skin=SKIN_SNOOT, hair='#33241D', hair_hi='#56402F',
    eye=dict(shape='gumdrop', w=0.30, h=0.30, lid=0.20, depth=0.43, x_prof=0.19, pr=0.056),
    brow=dict(kind='arch', t=0.046, L=0.29, gap=0.065, dx=0.0, arch=0.055),
    nose='ski', mouth_y=0.285, chin=0.88, chin_r=(0.07, 0.066),
    rim=0.020, lidw=0.036,
)


def X(**kw):
    """Expression state with defaults."""
    d = dict(cov=None, tilt=0.0, curve=0.0, low=0.0, low_tilt=0.0, low_curve=0.0, gaze=(1.0, 0.0), amt=1.0,
             pr=None, ghost=False, closed=None, brow_raise=0.0, brow_tilt=0.0, brow_arch=None, brow2_raise=0.0,
             brow2_arch=None, mouth='line', jaw=0.0, nose_up=0.0, flare=False, marks=[], far_cov=None)
    d.update(kw)
    return d


# =====================================================================================
# EYE SYSTEM
# =====================================================================================
def eye_fns(shape, w, h, D):
    hw = w / 2
    if shape == 'almond':
        k = 0.55

        def up(x):
            u = max(-1.0, min(1.0, x / hw))
            v = max(0.0, 1 - u * u)
            sk = 1 + 0.10 * u
            return -0.54 * h * v * (1 + k * v) / (1 + k) * sk / 1.012

        def lo(x):
            u = max(-1.0, min(1.0, x / hw))
            v = max(0.0, 1 - u * u)
            return 0.46 * h * v ** 1.05 * (1 + 0.3 * v) / 1.3
    elif shape == 'gumdrop':
        r = 0.05 * D

        def up(x):
            u = min(1.0, abs(x) / hw)
            return h / 2 - h * max(0.0, 1 - u ** 2.5) ** 0.5

        def lo(x):
            ax = abs(x)
            xr = hw - r
            if ax <= xr:
                return h / 2
            dx = min(1.0, (ax - xr) / r)
            return h / 2 - r * (1 - math.sqrt(max(0.0, 1 - dx * dx)))
    else:   # 'generic' cameo ellipse
        def up(x):
            u = min(1.0, abs(x) / hw)
            return -h / 2 * math.sqrt(max(0.0, 1 - u * u))

        def lo(x):
            u = min(1.0, abs(x) / hw)
            return h / 2 * math.sqrt(max(0.0, 1 - u * u))
    return up, lo


def eye_outline(up, lo, hw, N=80):
    xs = [-hw * math.cos(math.pi * i / N) for i in range(N + 1)]
    top, bot = [], []
    for x in xs:
        t, b = up(x), lo(x)
        if t > b:
            t = b
        top.append((x, t))
        bot.append((x, b))
    return top + bot[::-1]


def eye_svg(E, st, ex, ey, w, h, D, skin, uid, mirror=False, tgt=None, rim=0.021, lidw=0.034, extras='', socket=True):
    """Draw one eye.  E: char eye spec, st: expression state.  (ex,ey) centre in head-local coords.
    mirror=True: the eye's 'front/inner' side is -x (far eye in 3/4).  tgt: gaze point in head-local.
    Returns (svg, info)."""
    shape = E['shape']
    hw = w / 2
    up, lo = eye_fns(shape, w, h, D)
    outline = eye_outline(up, lo, hw)
    yT = min(p[1] for p in outline)
    yB = max(p[1] for p in outline)
    HH = yB - yT
    m = -1 if mirror else 1
    cov = st['cov']
    tl = math.tan(math.radians(st['tilt']))
    curve = st['curve']

    def lid(x):
        u = x / hw
        return yT + cov * HH + tl * x + curve * HH * (1 - u * u)
    lc = st['low']
    ltl = math.tan(math.radians(st['low_tilt']))
    lcur = st['low_curve']

    def low(x):
        u = x / hw
        return yB - lc * HH + ltl * x - lcur * HH * (1 - u * u)

    def top(x):
        return max(up(x), lid(x)) if cov > 0 else up(x)

    def bot(x):
        return min(lo(x), low(x)) if lc > 0 else lo(x)
    pr = (st['pr'] or E['pr']) * D
    lidc = mix(skin, '#2A1D18', 0.10) if socket else skin
    cid = f'ec{uid}'
    shape_d = poly(outline)
    tf = f'translate({n(ex)},{n(ey)})' + (' scale(-1,1)' if mirror else '')
    o = [f'<g transform="{tf}">']
    info = dict(w=w / D, h=HH / D, top=(ey + yT), pupil=2 * pr / D)
    if st.get('closed'):
        kind = st['closed']
        cr = [(x, up(x) * 0.78 - 0.01 * D) for x, _ in outline[:81:4]]
        o.append(f'<path d="{pline(cr)}" fill="none" stroke="{shade(skin, 0.38)}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
        if kind == 'down':
            ln = [(x, (lo(x) * 0.55)) for x, _ in outline[:81:2]]
        else:
            ln = [(x, -(lo(x) * 0.55) + 0.06 * D) for x, _ in outline[:81:2]]
        o.append(f'<path d="{pline(ln)}" fill="none" stroke="{INK}" stroke-width="{n(lidw * D)}" stroke-linecap="round"/>')
        e0 = ln[0]
        o.append(f'<path d="M{pt(e0)} L{pt(add(e0, (-0.045 * D, 0.03 * D)))}" stroke="{INK}" stroke-width="{n(0.022 * D)}" stroke-linecap="round"/>')
        o.append(extras)
        o.append('</g>')
        info['top'] = ey + yT
        return ''.join(o), info
    # ---- pupil position
    if tgt is not None:
        g = ((tgt[0] - ex) * m, tgt[1] - ey)
        gl = math.hypot(*g) or 1
        g = (g[0] / gl, g[1] / gl)
        amt = st['amt']
    else:
        g = unit(st['gaze']) if st['amt'] > 0 else (0.0, 0.0)
        amt = st['amt']
    xs = [-hw + 2 * hw * i / 240 for i in range(241)]
    ops = [(x, top(x), bot(x)) for x in xs]
    maxop = max(b - t for _, t, b in ops)
    need = min(1.40 * pr, 0.80 * maxop)
    valid = [x for x, t, b in ops if b - t >= need]
    if not valid:
        valid = [0.0]
    xmin, xmax = valid[0], valid[-1]
    xc = (xmin + xmax) / 2
    px = xc + g[0] * amt * ((xmax - xc) if g[0] > 0 else (xc - xmin))
    tt, bb = top(px), bot(px)
    mid = (tt + bb) / 2
    room = max(0.0, (bb - tt) / 2 - pr * 0.40)
    py = mid + g[1] * amt * room * 1.0
    if st.get('py_bias'):
        py += st['py_bias'] * D
    o.append(f'<defs><clipPath id="{cid}"><path d="{shape_d}"/></clipPath></defs>')
    o.append(f'<path d="{shape_d}" fill="{EYEW}"/>')
    g_in = []
    if st['ghost']:
        for gx in (-0.045 * D, 0.045 * D):
            g_in.append(f'<circle cx="{n(px + gx)}" cy="{n(py)}" r="{n(pr)}" fill="{INK}" opacity="0.30"/>')
    g_in.append(f'<circle cx="{n(px)}" cy="{n(py)}" r="{n(pr)}" fill="{INK}"/>')
    x0, x1 = -hw - 0.05 * D, hw + 0.05 * D
    xs2 = [x0 + (x1 - x0) * i / 40 for i in range(41)]
    if cov > 0:
        mask = [(x, lid(x)) for x in xs2] + [(x1, yT - HH), (x0, yT - HH)]
        g_in.append(f'<path d="{poly(mask)}" fill="{lidc}"/>')
    if lc > 0:
        maskl = [(x, low(x)) for x in xs2] + [(x1, yB + HH), (x0, yB + HH)]
        g_in.append(f'<path d="{poly(maskl)}" fill="{skin}"/>')
        g_in.append(f'<path d="{pline([(x, low(x)) for x in xs2])}" fill="none" stroke="{INK}" stroke-width="{n(rim * D)}"/>')
    if cov > 0:
        g_in.append(f'<path d="{pline([(x, lid(x)) for x in xs2])}" fill="none" stroke="{INK}" stroke-width="{n(lidw * D)}"/>')
    o.append(f'<g clip-path="url(#{cid})">' + ''.join(g_in) + '</g>')
    rw = rim if cov > 0 else rim * 1.15
    if socket or cov <= 0:
        o.append(f'<path d="{shape_d}" fill="none" stroke="{INK}" stroke-width="{n(rw * D)}" stroke-linejoin="round"/>')
    else:
        rc = f'rc{uid}'
        below = [(x, lid(x)) for x in xs2] + [(x1, yB + HH), (x0, yB + HH)]
        o.append(f'<defs><clipPath id="{rc}"><path d="{poly(below)}"/></clipPath></defs>')
        o.append(f'<path clip-path="url(#{rc})" d="{shape_d}" fill="none" stroke="{INK}" stroke-width="{n(rw * D)}" stroke-linejoin="round"/>')
    o.append(extras)
    o.append('</g>')
    info.update(px=px, py=py, cov=cov, lid_y=(ey + lid(0)) if cov > 0 else None)
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
# MOUTHS (profile)
# =====================================================================================
def mouth_profile(ch, x, D):
    """Returns (skin svg drawn with the skull, detail svg, chin drop)."""
    m = x['mouth']
    skin = ch['skin']
    ym = ch['mouth_y'] * D
    xm = rimy(D, ym)[0]
    lw = 0.026 * D
    S = f'fill="none" stroke="{INK}" stroke-width="{n(lw)}" stroke-linecap="round" stroke-linejoin="round"'
    crease = shade(skin, 0.36)
    sk, det = [], []
    chin_dy = 0.0
    if m == 'line':
        det.append(f'<path d="M{pt((xm + 0.012 * D, ym))} Q{pt((xm - 0.07 * D, ym + 0.004 * D))} {pt((xm - 0.150 * D, ym + 0.022 * D))}" {S}/>')
    elif m == 'pout':       # Snoot at rest: pressed, corner down, lower lip pushed out
        sk.append(f'<ellipse cx="{n(xm - 0.005 * D)}" cy="{n(ym + 0.035 * D)}" rx="{n(0.04 * D)}" ry="{n(0.03 * D)}" fill="{skin}"/>')
        det.append(f'<path d="M{pt((xm + 0.02 * D, ym))} Q{pt((xm - 0.06 * D, ym - 0.006 * D))} {pt((xm - 0.140 * D, ym + 0.035 * D))}" {S}/>')
    elif m in ('smirk', 'smug'):
        big = m == 'smug'
        e_ = (xm - (0.20 if big else 0.175) * D, ym - (0.06 if big else 0.035) * D)
        det.append(f'<path d="M{pt((xm + 0.012 * D, ym + 0.008 * D))} Q{pt((xm - 0.10 * D, ym + (0.03 if big else 0.018) * D))} {pt(e_)}" {S}/>')
        det.append(f'<path d="M{pt(add(e_, (0.006 * D, -0.02 * D)))} L{pt(add(e_, (-0.022 * D, 0.004 * D)))}" {S}/>')
        det.append(f'<path d="M{pt((e_[0] - 0.02 * D, e_[1] - 0.075 * D))} Q{pt((e_[0] - 0.06 * D, e_[1] - 0.01 * D))} {pt((e_[0] - 0.025 * D, e_[1] + 0.05 * D))}" '
                   f'fill="none" stroke="{crease}" stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    elif m == 'flat':       # exasperated: dead flat, pushed forward
        sk.append(f'<ellipse cx="{n(xm + 0.005 * D)}" cy="{n(ym + 0.004 * D)}" rx="{n(0.035 * D)}" ry="{n(0.04 * D)}" fill="{skin}"/>')
        det.append(f'<path d="M{pt((xm + 0.035 * D, ym + 0.004 * D))} L{pt((xm - 0.13 * D, ym + 0.004 * D))}" {S}/>')
        det.append(f'<path d="M{pt((xm - 0.13 * D, ym + 0.004 * D))} L{pt((xm - 0.155 * D, ym + 0.03 * D))}" {S}/>')
    elif m in ('open', 'wavy'):
        j = (x['jaw'] or 0.035) * D
        chin_dy = j
        U = add(rimy(D, ym - 0.035 * D), (-0.004 * D, 0))
        L = add(rimy(D, ym + 0.115 * D + j * 0.6), (0.01 * D, 0))
        I = (U[0] - 0.31 * D, ym + 0.045 * D)
        cav = (f"M{pt(U)} Q{pt((U[0] - 0.15 * D, ym - 0.075 * D))} {pt(I)} Q{pt((U[0] - 0.12 * D, ym + 0.19 * D + j))} {pt(L)} "
               f"Q{pt((L[0] + 0.035 * D, (U[1] + L[1]) / 2))} {pt(U)} Z")
        cid = f'mc{x.get("_uid", "")}'
        det.append(f'<defs><clipPath id="{cid}"><path d="{cav}"/></clipPath></defs>')
        det.append(f'<path d="{cav}" fill="{MOUTHC}"/>')
        inner = [f'<ellipse cx="{n(U[0] - 0.11 * D)}" cy="{n(L[1] + 0.01 * D)}" rx="{n(0.11 * D)}" ry="{n(0.06 * D)}" fill="{TONGUE}"/>']
        if m == 'wavy':
            wv = [(U[0] + 0.02 * D, U[1] - 0.04 * D), (U[0] + 0.02 * D, U[1] + 0.035 * D)]
            for i in range(1, 7):
                xx = U[0] + 0.02 * D - 0.30 * D * i / 6
                yy = U[1] + 0.035 * D + (0.018 * D if i % 2 else -0.012 * D) + 0.006 * D * i
                wv.append((xx, yy))
            wv += [(U[0] - 0.30 * D, U[1] - 0.06 * D)]
            inner.append(f'<path d="{poly(wv)}" fill="{TEETH}"/>')
        det.append(f'<g clip-path="url(#{cid})">' + ''.join(inner) + '</g>')
        det.append(f'<path d="{cav}" fill="none" stroke="{INK}" stroke-width="{n(0.016 * D)}" stroke-linejoin="round"/>')
        sk.append(f'<ellipse cx="{n(U[0] + 0.006 * D)}" cy="{n(U[1] - 0.012 * D)}" rx="{n(0.042 * D)}" ry="{n(0.024 * D)}" fill="{skin}"/>')
        sk.append(f'<ellipse cx="{n(L[0] - 0.005 * D)}" cy="{n(L[1] + 0.016 * D)}" rx="{n(0.05 * D)}" ry="{n(0.03 * D)}" fill="{skin}"/>')
    elif m == 'teeth':      # angry clench, lips pulled back
        U = add(rimy(D, ym - 0.03 * D), (0.002 * D, 0))
        L = add(rimy(D, ym + 0.075 * D), (0.006 * D, 0))
        I = (U[0] - 0.31 * D, ym + 0.028 * D)
        cav = (f"M{pt(U)} Q{pt((U[0] - 0.15 * D, ym - 0.060 * D))} {pt(I)} Q{pt((U[0] - 0.14 * D, ym + 0.115 * D))} {pt(L)} "
               f"Q{pt((L[0] + 0.02 * D, (U[1] + L[1]) / 2))} {pt(U)} Z")
        cid = f'mt{x.get("_uid", "")}'
        det.append(f'<defs><clipPath id="{cid}"><path d="{cav}"/></clipPath></defs>')
        det.append(f'<path d="{cav}" fill="{TEETH}"/>')
        g = [f'<path d="M{pt((U[0] + 0.03 * D, ym + 0.022 * D))} Q{pt((U[0] - 0.15 * D, ym + 0.036 * D))} {pt((I[0] - 0.02 * D, ym + 0.028 * D))}" '
             f'fill="none" stroke="{INK}" stroke-width="{n(0.016 * D)}"/>']
        for fx in (0.07, 0.15, 0.23):
            g.append(f'<path d="M{pt((U[0] - fx * D, ym - 0.08 * D))} L{pt((U[0] - fx * D - 0.004 * D, ym + 0.12 * D))}" '
                     f'stroke="{INK}" stroke-width="{n(0.013 * D)}"/>')
        det.append(f'<g clip-path="url(#{cid})">' + ''.join(g) + '</g>')
        det.append(f'<path d="{cav}" fill="none" stroke="{INK}" stroke-width="{n(0.020 * D)}" stroke-linejoin="round"/>')
        det.append(f'<path d="M{pt(add(I, (0.01 * D, -0.03 * D)))} L{pt(add(I, (-0.03 * D, 0.0)))} L{pt(add(I, (0.01 * D, 0.03 * D)))}" '
                   f'fill="none" stroke="{crease}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    elif m == 'sneer':      # Snoot: upper lip curled at the front over a teeth sliver, corner pulled down
        P0 = (xm + 0.02 * D, ym - 0.012 * D)
        P1 = (xm - 0.05 * D, ym - 0.045 * D)
        P2 = (xm - 0.10 * D, ym + 0.002 * D)
        P3 = (xm - 0.17 * D, ym + 0.05 * D)
        tooth = [P0, (xm - 0.04 * D, ym - 0.036 * D), P2, (xm - 0.02 * D, ym + 0.012 * D), (xm + 0.02 * D, ym + 0.008 * D)]
        det.append(f'<path d="{closed_rounded(tooth, 0.008 * D)}" fill="{TEETH}" stroke="{INK}" stroke-width="{n(0.012 * D)}"/>')
        det.append(f'<path d="M{pt(P0)} Q{pt(P1)} {pt(P2)} Q{pt((xm - 0.13 * D, ym + 0.02 * D))} {pt(P3)}" {S}/>')
        det.append(f'<path d="M{pt((xm - 0.06 * D, ym - 0.105 * D))} Q{pt((xm - 0.12 * D, ym - 0.05 * D))} {pt((xm - 0.12 * D, ym + 0.01 * D))}" '
                   f'fill="none" stroke="{crease}" stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    return ''.join(sk), ''.join(det), chin_dy


# =====================================================================================
# HAIR PIECES
# =====================================================================================
def mage_pts(D, base_deg=-103):
    """Sol's chonmage: tied stem rising from the crown, club folded FORWARD lying on the pate."""
    s = D
    c = [(-0.175 * s, -0.445 * s), (-0.148 * s, -0.552 * s), (-0.045 * s, -0.595 * s), (0.075 * s, -0.557 * s),
         (0.185 * s, -0.505 * s)]
    ws = [0.150 * s, 0.140 * s, 0.125 * s, 0.112 * s, 0.100 * s]
    # build outline from centreline + widths
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
    fan = [add(add(c[-1], mul(td, 0.065 * s)), mul(tn, -0.068 * s)), add(add(c[-1], mul(td, 0.045 * s)), mul(tn, -0.02 * s)),
           add(add(c[-1], mul(td, 0.075 * s)), mul(tn, 0.0)), add(add(c[-1], mul(td, 0.045 * s)), mul(tn, 0.025 * s)),
           add(add(c[-1], mul(td, 0.060 * s)), mul(tn, 0.066 * s))]
    outline = Rr + fan + L[::-1]
    return outline, c, ws


def mage_svg(D, tie, sil=False):
    outline, c, ws = mage_pts(D)
    rr = [0.03 * D] * len(outline)
    for i in range(5, 10):
        rr[i] = 0.006 * D
    o = [f'<path d="{closed_rounded(outline, rr)}" fill="{INK}"/>']
    # brush-end notch (two short splits at the folded tip)
    tipd = unit(sub(c[-1], c[-2]))
    nrm = (-tipd[1], tipd[0])
    tb = add(c[-1], mul(tipd, 0.03 * D))
    if not sil:
        # brass cord: band round the stem + two tails trailing back
        p = c[1]
        t = unit(sub(c[2], c[0]))
        nr = (-t[1], t[0])
        band = [add(add(p, mul(t, -0.020 * D)), mul(nr, 0.060 * D)), add(add(p, mul(t, 0.020 * D)), mul(nr, 0.055 * D)),
                add(add(p, mul(t, 0.020 * D)), mul(nr, -0.055 * D)), add(add(p, mul(t, -0.020 * D)), mul(nr, -0.060 * D))]
        o.append(f'<path d="{closed_rounded(band, 0.01 * D)}" fill="{tie}"/>')
    k0 = add(c[1], (-0.045 * D, 0.012 * D))
    col = INK if sil else tie
    for e, w0 in (((-0.265 * D, -0.475 * D), 0.024), ((-0.235 * D, -0.425 * D), 0.022)):
        o.append(tube([k0, lerp(k0, e, 0.5), e], [w0 * D, w0 * D, w0 * D * 0.8], col))
    return ''.join(o), outline


def pomp_pts(D):
    """Snoot's short pompadour (profile/3-4 share): one closed shape overlapping the skull top."""
    s = D
    crest = [(0.285 * s, -0.405 * s), (0.39 * s, -0.47 * s), (0.50 * s, -0.565 * s), (0.565 * s, -0.655 * s),
             (0.53 * s, -0.705 * s), (0.42 * s, -0.735 * s), (0.25 * s, -0.725 * s), (0.06 * s, -0.675 * s),
             (-0.14 * s, -0.615 * s), (-0.32 * s, -0.51 * s), (-0.45 * s, -0.36 * s), (-0.515 * s, -0.19 * s),
             (-0.52 * s, -0.06 * s)]
    lower = [(-0.50 * s, -0.02 * s), (-0.37 * s, -0.12 * s), (-0.19 * s, -0.20 * s), (0.0 * s, -0.285 * s),
             (0.16 * s, -0.365 * s)]
    return crest + lower


def pomp_detail(ch, D):
    hi = ch['hair_hi']
    o = []
    # sweep lines following the wave from the front curl back over the crown
    for a, b, c_, w in (((0.47, -0.60), (0.20, -0.68), (-0.30, -0.52), 0.022), ((0.40, -0.52), (0.10, -0.59), (-0.38, -0.36), 0.018)):
        o.append(f'<path d="M{pt(mul(a, D))} Q{pt(mul(b, D))} {pt(mul(c_, D))}" fill="none" stroke="{hi}" stroke-width="{n(w * D)}" stroke-linecap="round"/>')
    # curl tucked under the front of the quiff
    o.append(f'<path d="M{pt((0.545 * D, -0.645 * D))} Q{pt((0.50 * D, -0.59 * D))} {pt((0.455 * D, -0.625 * D))} Q{pt((0.44 * D, -0.665 * D))} {pt((0.49 * D, -0.675 * D))}" '
             f'fill="none" stroke="{hi}" stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    return ''.join(o)


def ear_c(cx, cy, h, D, col=INK):
    d = (f"M{pt((cx + 0.23 * h, cy - 0.50 * h))} C{pt((cx - 0.42 * h, cy - 0.60 * h))} "
         f"{pt((cx - 0.44 * h, cy + 0.56 * h))} {pt((cx + 0.18 * h, cy + 0.50 * h))}")
    d2 = f"M{pt((cx + 0.12 * h, cy - 0.16 * h))} Q{pt((cx - 0.12 * h, cy))} {pt((cx + 0.08 * h, cy + 0.20 * h))}"
    return (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{n(0.021 * D)}" stroke-linecap="round"/>'
            f'<path d="{d2}" fill="none" stroke="{col}" stroke-width="{n(0.017 * D)}" stroke-linecap="round"/>')


def marks_svg(x, D, tip, ch, flip_snort=False):
    out = []
    st = f'fill="none" stroke="{INK}" stroke-width="{n(0.024 * D)}" stroke-linecap="round"'
    for m in x['marks']:
        if m == 'emanata':
            ox, oy = 0.18 * D, -0.30 * D
            for ang in (-110, -75, -40):
                a = math.radians(ang)
                p0 = (ox + 0.42 * D * math.cos(a), oy + 0.42 * D * math.sin(a))
                p1 = (ox + 0.56 * D * math.cos(a), oy + 0.56 * D * math.sin(a))
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
            for off in (0.62, 0.72):
                xx = -off * D
                d = f"M{pt((xx + 0.03 * D, -0.22 * D))} Q{pt((xx - 0.03 * D, -0.08 * D))} {pt((xx + 0.03 * D, 0.06 * D))}"
                out.append(f'<path d="{d}" {st}/>')
        elif m == 'sweat':
            for (cx, cy, s, a) in ((-0.30 * D, -0.56 * D, 1.0, 150), (0.44 * D, -0.44 * D, 0.75, 210)):
                d = "M0,-26 C9,-10 16,2 0,16 C-16,2 -9,-10 0,-26 Z"
                out.append(f'<path transform="translate({n(cx)},{n(cy)}) rotate({a}) scale({n(s * D / 220)})" d="{d}" '
                           f'fill="{PALE}" stroke="{INK}" stroke-width="{n(4.5 * 220 / D / s * D / 270)}" stroke-linejoin="round"/>')
        elif m == 'steam':
            for (cx, cy, a) in ((-0.42 * D, -0.50 * D, -30), (-0.28 * D, -0.66 * D, -10)):
                d = "M0,0 q-8,-10 0,-20 q8,-10 0,-20"
                out.append(f'<path transform="translate({n(cx)},{n(cy)}) rotate({a}) scale({n(D / 200)})" d="{d}" {st}/>')
    return ''.join(out)


# =====================================================================================
# PROFILE HEAD
# =====================================================================================
def head_profile(ch, x, D, uid, tgt=None, sil=False):
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
    hair_shapes = []
    if ch['name'] == 'sol':
        m_svg, m_out = mage_svg(D, BRASS, sil)
        pts += m_out
    else:
        pp = pomp_pts(D)
        pts += pp
    if sil:
        o.append(f'<g fill="{INK}"><circle r="{n(R)}"/><path d="{nose_d}"/>{chin_svg.replace(skin, INK)}{msk.replace(skin, INK)}</g>')
        if ch['name'] == 'sol':
            o.append(m_svg)
            tuft = sol_tuft(chin, D)
            o.append(f'<path d="{tuft}" fill="{INK}"/>')
        else:
            o.append(f'<path d="{closed_rounded(pp, 0.03 * D)}" fill="{INK}"/>')
            o.append(f'<circle cx="{n(-0.155 * D)}" cy="{n(0.145 * D)}" r="{n(0.048 * D)}" fill="none" stroke="{INK}" stroke-width="{n(0.022 * D)}"/>')
        return ''.join(o), pts
    cid = f'sk{uid}'
    o.append(f'<defs><clipPath id="{cid}"><circle r="{n(R)}"/>{chin_svg.replace(" fill=", " data-f=")}</clipPath></defs>')
    o.append(f'<circle r="{n(R)}" fill="{skin}"/>')
    o.append(f'<path d="{nose_d}" fill="{skin}"/>')
    o.append(chin_svg)
    inner = []
    if ch['name'] == 'sol':
        stub = mix(skin, '#3B4150', 0.22)
        jd = (f"M{pt((0.7 * D, 0.215 * D))} L{pt((0.42 * D, 0.215 * D))} C{pt((0.30 * D, 0.215 * D))} {pt((0.13 * D, 0.235 * D))} "
              f"{pt((0.02 * D, 0.185 * D))} C{pt((-0.04 * D, 0.155 * D))} {pt((-0.075 * D, 0.12 * D))} {pt((-0.10 * D, 0.10 * D))} "
              f"C{pt((-0.12 * D, 0.22 * D))} {pt((-0.10 * D, 0.36 * D))} {pt((-0.04 * D, 0.62 * D))} L{pt((0.7 * D, 0.9 * D))} Z")
        inner.append(f'<path d="{jd}" fill="{stub}"/>')
        # nape band: thin black strip along the back-lower rim only (head round stays visible)
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
        # long sideburn in front of the ear
        sb = [(-0.15 * D, -0.185 * D), (-0.065 * D, -0.262 * D), (-0.048 * D, -0.05 * D), (-0.045 * D, 0.16 * D), (-0.062 * D, 0.262 * D),
              (-0.092 * D, 0.17 * D), (-0.108 * D, -0.06 * D)]
        inner.append(f'<path d="{closed_rounded(sb, [0, 0.02 * D, 0.03 * D, 0.03 * D, 0.004 * D, 0.03 * D, 0.03 * D])}" fill="{ch["hair"]}"/>')
    o.append(f'<g clip-path="url(#{cid})">' + ''.join(inner) + '</g>')
    o.append(msk)
    # hair outside / on top
    if ch['name'] == 'sol':
        o.append(m_svg)
    else:
        pp = pomp_pts(D)
        o.append(f'<path d="{closed_rounded(pp, 0.03 * D)}" fill="{ch["hair"]}"/>')
        # comb grooves + curl of the quiff
        o.append(pomp_detail(ch, D))
    # ear
    ex_ear, ey_ear = (-0.13 if ch['name'] == 'sol' else -0.17) * D, 0.01 * D
    o.append(f'<ellipse cx="{n(ex_ear - 0.005 * D)}" cy="{n(ey_ear)}" rx="{n(0.058 * D)}" ry="{n(0.088 * D)}" fill="{skin}"/>')
    o.append(ear_c(ex_ear, ey_ear, 0.175 * D, D))
    if ch['name'] == 'snoot':
        o.append(f'<circle cx="{n(-0.155 * D)}" cy="{n(0.145 * D)}" r="{n(0.048 * D)}" fill="none" stroke="{GOLD}" stroke-width="{n(0.022 * D)}"/>')
    # eye
    st = dict(x)
    st['cov'] = E['lid'] if x['cov'] is None else x['cov']
    ex = E['x_prof'] * D
    ey = (E['depth'] - 0.5) * D
    extras = ''
    if ch['name'] == 'snoot':       # lower-lid bag arc (age), the pair's wrinkle signal
        hw = E['w'] * D / 2
        extras += (f'<path d="M{pt((-hw * 0.70, E["h"] * D / 2 + 0.035 * D))} Q{pt((0, E["h"] * D / 2 + 0.075 * D))} '
                   f'{pt((hw * 0.75, E["h"] * D / 2 + 0.03 * D))}" fill="none" stroke="{shade(skin, 0.30)}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    eye, info = eye_svg(E, st, ex, ey, E['w'] * D, E['h'] * D, D, skin, uid, False, tgt, ch['rim'], ch['lidw'], extras)
    o.append(eye)
    # brow
    arch = Bw['arch'] if x['brow_arch'] is None else x['brow_arch']
    bcx = ex + Bw['dx'] * D
    bcy = info['top'] - Bw['gap'] * D - Bw['t'] * D / 2 - x['brow_raise'] * D
    bclip = f'bc{uid}'
    o.append(f'<defs><clipPath id="{bclip}"><circle r="{n(R + 0.012 * D)}"/></clipPath></defs>')
    o.append(f'<g clip-path="url(#{bclip})">' + brow_svg(Bw['kind'], bcx, bcy, Bw['L'] * D, Bw['t'] * D, x['brow_tilt'], arch * D, D=D) + '</g>')
    o.append(mdet)
    o.append(nose_det)
    if ch['name'] == 'sol':
        o.append(f'<path d="{sol_tuft(chin, D)}" fill="{INK}"/>')
    o.append(marks_svg(x, D, tip, ch))
    REG['metrics'].append(dict(uid=uid, name=ch['name'], view='profile', eye_h=round(info['h'], 3), eye_w=round(info['w'], 3),
                               eye_c_depth=round(E['depth'], 3), eye_top_depth=round((info['top'] + R) / D, 3),
                               pupil=round(info['pupil'], 3), lidw=ch['lidw'], rim=ch['rim'],
                               brow_t=Bw['t'], brow_gap=round((info['top'] - (bcy + Bw['t'] * D / 2)) / D, 3)))
    return ''.join(o), pts


def sol_tuft(chin, D):
    c = (chin[0] - 0.005 * D, chin[1] + 0.035 * D)
    v = [(c[0] - 0.045 * D, c[1] - 0.012 * D), (c[0] + 0.035 * D, c[1] - 0.004 * D), (c[0] + 0.03 * D, c[1] + 0.06 * D),
         (c[0] + 0.012 * D, c[1] + 0.13 * D), (c[0] - 0.02 * D, c[1] + 0.06 * D)]
    return closed_rounded(v, [0.02 * D, 0.02 * D, 0.03 * D, 0.006 * D, 0.03 * D])


# =====================================================================================
# 3/4 HEAD (facing +x)
# =====================================================================================
def head_34(ch, x, D, uid, tgt=None, sil=False):
    R = D / 2
    skin = ch['skin']
    E = ch['eye']
    Bw = ch['brow']
    sol = ch['name'] == 'sol'
    o = []
    # nose
    if sol:
        N0 = (0.150 * D, -0.085 * D)
        T = (0.655 * D, 0.155 * D)
        NB = (0.400 * D, 0.225 * D)
        NBk = (0.140 * D, 0.205 * D)
        nose_v = [N0, (0.215 * D, -0.09 * D), T, NB, NBk]
        nose = closed_rounded(nose_v, [0.02 * D, 0.02 * D, 0.03 * D, 0.025 * D, 0.03 * D])
        nshadow = closed_rounded([N0, (0.20 * D, 0.0), NB, NBk, (0.115 * D, 0.05 * D)], [0.02 * D, 0.03 * D, 0.025 * D, 0.03 * D, 0.03 * D])
    else:
        N0 = (0.165 * D, -0.105 * D)
        pts_b = [bez3((0.225 * D, -0.105 * D), (0.30 * D, 0.03 * D), (0.50 * D, 0.10 * D), (0.66 * D, 0.035 * D), t / 12) for t in range(0, 13)]
        T = (0.715 * D, -0.005 * D)
        nose_v = [N0] + pts_b + [T, (0.73 * D, 0.045 * D), (0.68 * D, 0.125 * D), (0.54 * D, 0.175 * D), (0.36 * D, 0.195 * D),
                                 (0.15 * D, 0.180 * D)]
        nose = closed_rounded(nose_v, 0.014 * D)
        nshadow = closed_rounded([N0, (0.22 * D, 0.0), (0.36 * D, 0.195 * D), (0.15 * D, 0.180 * D), (0.12 * D, 0.03 * D)], 0.02 * D)
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
        pp = pomp_pts(D)
        pts += pp
    ring = (-R + 0.03 * D, 0.175 * D)
    if sil:
        o.append(f'<g fill="{INK}"><circle r="{n(R)}"/><path d="{nose}"/>{ear.replace(skin, INK)}{chin_svg.replace(skin, INK)}</g>')
        if sol:
            o.append(m_svg)
            o.append(f'<path d="{sol_tuft(chin_c, D)}" fill="{INK}"/>')
        else:
            o.append(f'<path d="{closed_rounded(pp, 0.03 * D)}" fill="{INK}"/>')
            o.append(f'<circle cx="{n(ring[0])}" cy="{n(ring[1])}" r="{n(0.05 * D)}" fill="none" stroke="{INK}" stroke-width="{n(0.022 * D)}"/>')
        return ''.join(o), pts
    cid = f'sk3{uid}'
    o.append(f'<defs><clipPath id="{cid}"><circle r="{n(R)}"/>{chin_svg.replace(" fill=", " data-f=")}</clipPath></defs>')
    o.append(ear)
    o.append(f'<circle r="{n(R)}" fill="{skin}"/>')
    o.append(chin_svg)
    inner = []
    if sol:
        stub = mix(skin, '#3B4150', 0.22)
        jd = (f"M{pt((-0.43 * D, 0.10 * D))} C{pt((-0.33 * D, 0.24 * D))} {pt((-0.08 * D, 0.24 * D))} "
              f"{pt((0.12 * D, 0.235 * D))} L{pt((0.50 * D, 0.235 * D))} L{pt((0.7 * D, 0.235 * D))} L{pt((0.7 * D, 0.9 * D))} "
              f"L{pt((-0.30 * D, 0.9 * D))} C{pt((-0.36 * D, 0.40 * D))} {pt((-0.40 * D, 0.22 * D))} {pt((-0.43 * D, 0.10 * D))} Z")
        inner.append(f'<path d="{jd}" fill="{stub}"/>')
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
        sb = [(-0.43 * D, -0.15 * D), (-0.33 * D, -0.24 * D), (-0.315 * D, 0.0), (-0.315 * D, 0.17 * D), (-0.345 * D, 0.262 * D),
              (-0.375 * D, 0.17 * D), (-0.40 * D, -0.02 * D)]
        inner.append(f'<path d="{closed_rounded(sb, [0, 0.02 * D, 0.03 * D, 0.03 * D, 0.004 * D, 0.03 * D, 0.03 * D])}" fill="{ch["hair"]}"/>')
    o.append(f'<g clip-path="url(#{cid})">' + ''.join(inner) + '</g>')
    if sol:
        o.append(m_svg)
    else:
        o.append(f'<path d="{closed_rounded(pp, 0.03 * D)}" fill="{ch["hair"]}"/>')
        o.append(pomp_detail(ch, D))
    o.append(ear_c(ear_c_[0] + 0.012 * D, ear_c_[1], 0.13 * D, D))
    if not sol:
        o.append(f'<circle cx="{n(ring[0])}" cy="{n(ring[1])}" r="{n(0.05 * D)}" fill="none" stroke="{GOLD}" stroke-width="{n(0.022 * D)}"/>')
    # eyes: near + far (compressed 75 %), cluster shifted toward the facing side
    w_n = E['w'] * D
    w_f = E['w'] * D * 0.75
    gap = (0.09 if sol else 0.10) * D
    shift = 0.10 * D
    span = w_n + gap + w_f
    xl = shift - span / 2
    cxn = xl + w_n / 2
    cxf = xl + w_n + gap + w_f / 2
    ey = (E['depth'] - 0.5) * D
    st = dict(x)
    st['cov'] = E['lid'] if x['cov'] is None else x['cov']
    stf = dict(st)
    if x.get('far_cov') is not None:
        stf['cov'] = x['far_cov']
    ext_n = ''
    if not sol:
        hw = w_n / 2
        ext_n = (f'<path d="M{pt((-hw * 0.70, E["h"] * D / 2 + 0.035 * D))} Q{pt((0, E["h"] * D / 2 + 0.075 * D))} '
                 f'{pt((hw * 0.75, E["h"] * D / 2 + 0.03 * D))}" fill="none" stroke="{shade(skin, 0.30)}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    eye_n, info_n = eye_svg(E, st, cxn, ey, w_n, E['h'] * D, D, skin, uid + 'n', False, tgt, ch['rim'], ch['lidw'], ext_n)
    eye_f, info_f = eye_svg(E, stf, cxf, ey + 0.004 * D, w_f, E['h'] * D, D, skin, uid + 'f', True, tgt, ch['rim'], ch['lidw'])
    o.append(f'<g clip-path="url(#{cid})">{eye_f}</g>')
    o.append(eye_n)
    arch = Bw['arch'] if x['brow_arch'] is None else x['brow_arch']
    arch2 = arch if x['brow2_arch'] is None else x['brow2_arch']
    bclip = f'bc3{uid}'
    o.append(f'<defs><clipPath id="{bclip}"><circle r="{n(R + 0.035 * D)}"/></clipPath></defs>')
    by_n = info_n['top'] - Bw['gap'] * D - Bw['t'] * D / 2 - x['brow_raise'] * D
    by_f = info_f['top'] - Bw['gap'] * D - Bw['t'] * D / 2 - (x['brow_raise'] + x['brow2_raise']) * D
    o.append(f'<g clip-path="url(#{bclip})">'
             + brow_svg(Bw['kind'], cxn + Bw['dx'] * D, by_n, Bw['L'] * D, Bw['t'] * D, x['brow_tilt'], arch * D, D=D)
             + brow_svg(Bw['kind'], cxf + 0.01 * D, by_f, Bw['L'] * D * 0.72, Bw['t'] * D * 0.9, x['brow_tilt'], arch2 * D, mirror=True, D=D)
             + '</g>')
    # nose on top of the far eye
    o.append(f'<path d="{nose}" fill="{skin}"/>')
    o.append(f'<path d="{nshadow}" fill="{shade(skin, 0.13)}"/>')
    if sol:
        o.append(f'<path d="M{pt((0.385 * D, 0.180 * D))} Q{pt((0.425 * D, 0.218 * D))} {pt((0.47 * D, 0.200 * D))}" fill="none" stroke="{MOUTHC}" '
                 f'stroke-width="{n(0.02 * D)}" stroke-linecap="round"/>')
    else:
        cx, cy = 0.585 * D, 0.142 * D
        o.append(f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(0.03 * D)}" ry="{n(0.014 * D)}" fill="{MOUTHC}" transform="rotate(-14,{n(cx)},{n(cy)})"/>')
        o.append(f'<path d="M{pt((0.535 * D, 0.075 * D))} Q{pt((0.49 * D, 0.12 * D))} {pt((0.53 * D, 0.165 * D))}" fill="none" stroke="{shade(skin, 0.40)}" '
                 f'stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    # mouth
    my = (0.80 if sol else 0.815) * D - R
    lw = 0.026 * D
    S = f'fill="none" stroke="{INK}" stroke-width="{n(lw)}" stroke-linecap="round"'
    mm = x['mouth']
    if mm == 'smirk':
        o.append(f'<path d="M{pt((0.08 * D, my - 0.03 * D))} Q{pt((0.20 * D, my + 0.02 * D))} {pt((0.40 * D, my + 0.004 * D))}" {S}/>')
        o.append(f'<path d="M{pt((0.055 * D, my - 0.075 * D))} Q{pt((0.03 * D, my - 0.03 * D))} {pt((0.065 * D, my + 0.005 * D))}" fill="none" '
                 f'stroke="{shade(skin, 0.36)}" stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    elif mm == 'pout':
        o.append(f'<path d="M{pt((0.10 * D, my + 0.025 * D))} Q{pt((0.24 * D, my - 0.012 * D))} {pt((0.40 * D, my + 0.02 * D))}" {S}/>')
        o.append(f'<path d="M{pt((0.18 * D, my + 0.05 * D))} Q{pt((0.25 * D, my + 0.075 * D))} {pt((0.33 * D, my + 0.05 * D))}" fill="none" '
                 f'stroke="{shade(skin, 0.30)}" stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
    else:
        o.append(f'<path d="M{pt((0.10 * D, my + 0.01 * D))} Q{pt((0.24 * D, my + 0.004 * D))} {pt((0.40 * D, my + 0.016 * D))}" {S}/>')
    if sol:
        o.append(f'<path d="{sol_tuft(chin_c, D)}" fill="{INK}"/>')
    else:
        o.append(f'<path d="M{pt((0.33 * D, 0.06 * D))} Q{pt((0.20 * D, 0.16 * D))} {pt((0.155 * D, 0.25 * D))}" fill="none" '
                 f'stroke="{shade(skin, 0.30)}" stroke-width="{n(0.016 * D)}" stroke-linecap="round"/>')
    for nm_, inf, w_ in (('near', info_n, w_n), ('far', info_f, w_f)):
        REG['metrics'].append(dict(uid=uid + nm_, name=ch['name'], view='34', eye_h=round(inf['h'], 3), eye_w=round(inf['w'], 3),
                                   eye_top_depth=round((inf['top'] + R) / D, 3), pupil=round(inf['pupil'], 3),
                                   cluster_shift=round((xl + span / 2) / D, 3), gap=round(gap / D, 3), span=round(span / D, 3)))
    return ''.join(o), pts


def head_local(ch, x, D, uid, view, tgt=None, sil=False):
    if view == '34':
        return head_34(ch, x, D, uid, tgt, sil)
    return head_profile(ch, x, D, uid, tgt, sil)


def to_world(q, C, facing, tilt):
    x_, y_ = rotv(q, tilt)
    return (C[0] + facing * x_, C[1] + y_)


def to_local(w, C, facing, tilt):
    v = sub(w, C)
    v = (v[0] * facing, v[1])
    return rotv(v, -tilt)


def head(ch, x, C, D, facing=1, tilt=0.0, uid='a', view='profile', tgt_world=None, sil=False):
    tgt = to_local(tgt_world, C, facing, tilt) if tgt_world is not None else None
    svg, pts = head_local(ch, x, D, uid, view, tgt, sil)
    REG['heads'].append((C, D))
    REG['head_pts'].extend(to_world(p, C, facing, tilt) for p in pts)
    return f'<g transform="translate({pt(C)}) scale({facing},1) rotate({n(tilt)})">{svg}</g>'


def eye_world(ch, C, D, facing, tilt, view='profile'):
    E = ch['eye']
    if view == 'profile':
        loc = (E['x_prof'] * D, (E['depth'] - 0.5) * D)
    else:
        loc = (0.0, (E['depth'] - 0.5) * D)
    return to_world(loc, C, facing, tilt)


# ---------------------------------------------------------------- cameo (window grandma)
def cameo_gran(C, D, uid, tgt_world=None):
    """Front view, generic 70%-lidded eye at 0.27 D (below the 0.30 D floor of the 12)."""
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
    hd = (f"M{pt((-0.7 * D, 0.06 * D))} L{pt((-0.47 * D, 0.06 * D))} C{pt((-0.44 * D, -0.16 * D))} {pt((-0.26 * D, -0.27 * D))} "
          f"{pt((0, -0.28 * D))} C{pt((0.26 * D, -0.27 * D))} {pt((0.44 * D, -0.16 * D))} {pt((0.47 * D, 0.06 * D))} "
          f"L{pt((0.7 * D, 0.06 * D))} L{pt((0.7 * D, -0.8 * D))} L{pt((-0.7 * D, -0.8 * D))} Z")
    jw = (f"M{pt((-0.6 * D, 0.10 * D))} L{pt((-0.46 * D, 0.10 * D))} C{pt((-0.36 * D, 0.34 * D))} {pt((-0.18 * D, 0.30 * D))} "
          f"{pt((0, 0.38 * D))} C{pt((0.18 * D, 0.30 * D))} {pt((0.36 * D, 0.34 * D))} {pt((0.46 * D, 0.10 * D))} "
          f"L{pt((0.6 * D, 0.10 * D))} L{pt((0.6 * D, 0.8 * D))} L{pt((-0.6 * D, 0.8 * D))} Z")
    o.append(f'<g clip-path="url(#{cid})"><path d="{jw}" fill="{shade(skin, 0.10)}"/><path d="{hd}" fill="{GREY_H}"/>'
             f'<path d="M{pt((0, -0.28 * D))} L{pt((0, -0.6 * D))}" stroke="{GREY_HD}" stroke-width="{n(0.02 * D)}"/></g>')
    E = dict(shape='generic', w=0.22, h=0.27, pr=0.050)
    ey = -0.05 * D
    tops = []
    for s in (-1, 1):
        ex = s * 0.17 * D
        tl = to_local(tgt_world, C, 1, 0) if tgt_world else None
        st = X(cov=0.70, amt=0.55)
        bag = (f'<path d="M{pt((-0.10 * D, 0.16 * D))} Q{pt((0, 0.20 * D))} {pt((0.10 * D, 0.16 * D))}" fill="none" '
               f'stroke="{shade(skin, 0.38)}" stroke-width="{n(0.018 * D)}" stroke-linecap="round"/>')
        e, inf = eye_svg(E, st, ex, ey, 0.22 * D, 0.27 * D, D, skin, f'{uid}{s}', s < 0, tl, 0.022, 0.034, bag, socket=False)
        o.append(e)
        tops.append(inf['top'])
        o.append(f'<path d="M{pt((ex - 0.08 * D, min(tops) - 0.06 * D))} L{pt((ex + 0.08 * D, min(tops) - 0.065 * D))}" stroke="{GREY_HD}" '
                 f'stroke-width="{n(0.045 * D)}" stroke-linecap="round"/>')
    o.append(f'<path d="{poly([(0.004 * D, -0.02 * D), (0.07 * D, 0.19 * D), (-0.03 * D, 0.20 * D)])}" fill="{shade(skin, 0.22)}"/>')
    my = 0.30 * D
    o.append(f'<path d="M{pt((-0.11 * D, my))} L{pt((0.11 * D, my))}" stroke="{INK}" stroke-width="{n(0.026 * D)}" stroke-linecap="round"/>')
    for s in (-1, 1):
        d = f"M{pt((s * 0.21 * D, my - 0.10 * D))} Q{pt((s * 0.26 * D, my - 0.02 * D))} {pt((s * 0.22 * D, my + 0.06 * D))}"
        o.append(f'<path d="{d}" fill="none" stroke="{shade(skin, 0.42)}" stroke-width="{n(0.02 * D)}" stroke-linecap="round"/>')
    o.append('</g>')
    return ''.join(o)


# =====================================================================================
# STICK-BODY RIG
# =====================================================================================
LOOK_SOL = dict(name='sol', limb='#232A38', skin=SKIN_SOL, feet='tabi', costume='hanten',
                coat='#2A4268', eri='#15161B', apron=SAGE, spine=0.95, thigh=0.74, shin=0.72, ua=0.64, fa=0.66,
                ws=dict(root=0.066, tip=0.050, sp0=0.07, sp1=0.06))
LOOK_SNOOT = dict(name='snoot', limb='#3A2F2B', skin=SKIN_SNOOT, feet='zori', costume='vest',
                  vest_a='#5E3D2A', vest_b='#E7D9BD', tenugui=TERRA, spine=0.84, thigh=0.84, shin=0.80, ua=0.64, fa=0.66,
                  ws=dict(root=0.062, tip=0.047, sp0=0.066, sp1=0.056))
for L_ in (LOOK_SOL, LOOK_SNOOT):
    L_['far'] = shade(L_['limb'], 0.18) if L_['name'] == 'snoot' else shade(L_['limb'], 0.20)

SHOULDERS = dict(profile=(0.10, -0.10), twist=(0.035, -0.17), **{'34': (-0.25, 0.16)})
HIPS = dict(profile=(0.02, -0.02), twist=(0.02, -0.04), **{'34': (-0.09, 0.05)})


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
    ws = {k: v * D for k, v in look['ws'].items()}
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
        wr, wt = ws['root'], ws['tip']
        wm = (wr + wt) / 2
        upper = tube([Sx, j], [wr, wm], col)
        fore = tube([j, w], [wm, wt], col)
        hang = spec.get('hand', ang_of(sub(w, j)))
        grip = 'grip' in spec or spec.get('fist', False) or spec.get('grip_auto', False)
        mb, mt = mitten(w, hang, D, f, mcol, spec.get('thumb', -1), grip)
        arms[key] = dict(upper=upper, fore=fore, mit=mb, thumb=mt)
        J[key] = (j, w)
    legs = {}
    for key in ('leg_f', 'leg_n'):
        spec = pose[key]
        Hx = HP[key]
        j, a = ik2(Hx, spec['a'], look['thigh'] * D, look['shin'] * D, spec.get('bend', (f, 0)), spec.get('straight', False))
        col = farc if key == 'leg_f' else limb
        wr, wt = ws['root'] * 1.04, ws['tip']
        wm = (wr + wt) / 2
        s = tube([Hx, j, a], [wr, wm, wt], col)
        shin_dir = unit(sub(a, j))
        fs = foot_svg(look['feet'], a, f, spec.get('foot', 0), D, shin_dir, wt, view, far=(key == 'leg_f'), sil=sil)
        legs[key] = s + fs
        J[key] = (j, a)
    nw = 0.17 * D
    neck = tube([NT, NB], [nw, nw], skin)
    if not sil:
        mid = lerp(NT, NB, 0.55)
        neck += tube([NT, mid], [nw, nw * 0.98], shade(skin, 0.12))
    back, panel, front, anchor = [], [], [], []
    costume(look, J, D, f, view, pose, sil, back, panel, front, anchor)
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
    Lyr.update(far_leg=legs['leg_f'], far_arm=arms['arm_f']['upper'] + arms['arm_f']['fore'] + arms['arm_f']['mit'],
               far_thumb=arms['arm_f']['thumb'], neck=neck, back=''.join(back), panel=''.join(panel), front=''.join(front),
               anchor=''.join(anchor), near_leg=legs['leg_n'], near_upper=arms['arm_n']['upper'],
               near_fore=arms['arm_n']['fore'] + arms['arm_n']['mit'], near_thumb=arms['arm_n']['thumb'], prop=prop)
    J['broom'] = br
    return Lyr, J


def costume(look, J, D, f, view, pose, sil, back, panel, front, anchor):
    samp, H, Y, NB = J['samp'], J['H'], J['Y'], J['NB']
    Lsp = J['spine_len']
    S, HP, yoke, down = J['S'], J['HP'], J['yoke'], J['down']

    def fw_of(tg):
        nrm = (-tg[1], tg[0])
        if nrm[0] * f < 0:
            nrm = mul(nrm, -1)
        return nrm
    if view in ('profile', 'twist'):
        if look['costume'] == 'hanten':
            ts = [-0.05 + i * (1.17 / 24) for i in range(25)]

            def wf(t):
                return (0.125 + 0.04 * t) * D

            def wb(t):
                return (0.115 + 0.05 * t) * D
        else:
            ts = [-0.03 + i * (1.06 / 24) for i in range(25)]

            def wf(t):
                tt = max(0.0, min(1.0, t / 0.80))
                return (0.10 + 0.075 * math.sin(math.pi * tt) ** 0.8) * D

            def wb(t):
                return (0.085 - 0.022 * math.sin(math.pi * max(0, min(1, t)))) * D
        fr, bk = [], []
        for t in ts:
            p, tg = spine_point(samp, H, Lsp, t)
            nr = fw_of(tg)
            fr.append(add(p, mul(nr, wf(t))))
            bk.append(add(p, mul(nr, -wb(t))))
        if look['costume'] == 'vest':
            # pointed front tip of the waistcoat
            p, tg = spine_point(samp, H, Lsp, 1.10)
            nr = fw_of(tg)
            fr.append(add(p, mul(nr, 0.06 * D)))
        outline = fr + bk[::-1]
        rr = [0.04 * D if i in (0, len(outline) - 1) else 0.012 * D for i in range(len(outline))]
        pd = closed_rounded(outline, rr)
        if look['costume'] == 'hanten':
            panel.append(f'<path d="{pd}" fill="{INK if sil else look["coat"]}"/>')
            if not sil:
                # black eri down the front edge + standing collar round the neck
                inner = []
                for t in ts:
                    p, tg = spine_point(samp, H, Lsp, t)
                    nr = fw_of(tg)
                    inner.append(add(p, mul(nr, wf(t) - 0.055 * D)))
                strip = fr + inner[::-1]
                panel.append(f'<path d="{closed_rounded(strip, 0.01 * D)}" fill="{look["eri"]}"/>')
                p0, tg0 = spine_point(samp, H, Lsp, -0.05)
                nr0 = fw_of(tg0)
                col = [add(p0, mul(nr0, -0.12 * D)), add(NB, mul(nr0, -0.10 * D)), add(NB, mul(nr0, 0.07 * D)),
                       add(p0, mul(nr0, 0.13 * D))]
                col = [add(q, mul(tg0, -0.03 * D)) for q in col]
                anchor.append(f'<path d="{closed_rounded(col, 0.02 * D)}" fill="{look["eri"]}"/>')
                anchor.append(f'<path d="M{pt(add(NB, mul(nr0, 0.06 * D)))} L{pt(add(fr[3], mul(nr0, -0.03 * D)))}" stroke="{PALE}" '
                              f'stroke-width="{n(0.022 * D)}" stroke-linecap="round"/>')
            # sleeve caps (short wide hanten sleeves) on both arms
            for key, lay in (('arm_f', back), ('arm_n', front)):
                Sx = S[key]
                j, w = J[key]
                u = unit(sub(j, Sx))
                e = add(Sx, mul(u, 0.23 * D))
                cap = tube([add(Sx, mul(u, -0.01 * D)), e], [0.135 * D, 0.15 * D], INK if sil else (look['coat'] if key == 'arm_n' else shade(look['coat'], 0.18)))
                lay.append(cap)
                if not sil:
                    cu = (-u[1], u[0])
                    lay.append(f'<path d="M{pt(add(e, mul(cu, 0.078 * D)))} L{pt(add(e, mul(cu, -0.078 * D)))}" stroke="{look["eri"]}" '
                               f'stroke-width="{n(0.035 * D)}" stroke-linecap="butt"/>')
        else:   # vest: brown base, cream vertical stripes, brass buttons
            cid = f'vest{look["name"]}{int(H[0])}{int(H[1])}'
            panel.append(f'<defs><clipPath id="{cid}"><path d="{pd}"/></clipPath></defs>')
            panel.append(f'<path d="{pd}" fill="{INK if sil else look["vest_a"]}"/>')
            if not sil:
                cl = [spine_point(samp, H, Lsp, -0.1 + i * 0.06)[0] for i in range(23)]
                st = []
                for k in range(-4, 6):
                    off = k * 0.064 * D * f
                    st.append(f'<path d="{pline(offset_poly(cl, -off))}" fill="none" stroke="{look["vest_b"]}" stroke-width="{n(0.030 * D)}"/>')
                panel.append(f'<g clip-path="url(#{cid})">' + ''.join(st) + '</g>')
                for t in (0.32, 0.52, 0.72):
                    p, tg = spine_point(samp, H, Lsp, t)
                    nr = fw_of(tg)
                    q = add(p, mul(nr, wf(t) - 0.035 * D))
                    panel.append(f'<circle cx="{n(q[0])}" cy="{n(q[1])}" r="{n(0.022 * D)}" fill="{BRASS}"/>')
            tenugui(look, J, D, f, view, pose, sil, back, anchor)
        if look['costume'] == 'hanten':
            apron(look, J, D, f, view, pose, sil, back, front)
        return
    # ---------------- 3/4 view: panel from the shoulders to the hem
    up = mul(down, -1)
    Sn, Sf = S['arm_n'], S['arm_f']
    on = unit(sub(Sn, Y))
    of = unit(sub(Sf, Y))
    hemv = 0.16 * D if look['costume'] == 'hanten' else 0.06 * D
    if look['costume'] == 'hanten':
        tn = add(add(Sn, mul(up, 0.035 * D)), mul(on, 0.045 * D))
        tf_ = add(add(Sf, mul(up, 0.035 * D)), mul(of, 0.035 * D))
        hn = add(add(HP['leg_n'], mul(on, 0.11 * D)), mul(down, hemv))
        hf = add(add(HP['leg_f'], mul(of, 0.10 * D)), mul(down, hemv))
    else:
        tn = add(add(Sn, mul(up, 0.02 * D)), mul(on, -0.01 * D))
        tf_ = add(add(Sf, mul(up, 0.02 * D)), mul(of, -0.01 * D))
        hn = add(add(HP['leg_n'], mul(on, 0.07 * D)), mul(down, hemv))
        hf = add(add(HP['leg_f'], mul(of, 0.06 * D)), mul(down, hemv))
    nn = add(NB, mul(yoke, -0.085 * D))
    nf = add(NB, mul(yoke, 0.075 * D))
    cf_top = add(NB, mul(yoke, 0.03 * D))
    cf_bot = add(lerp(hn, hf, 0.62), (0, 0))
    if look['costume'] == 'hanten':
        outline = [nn, tn, add(lerp(tn, hn, 0.5), mul(on, 0.01 * D)), hn, hf, add(lerp(tf_, hf, 0.5), mul(of, 0.01 * D)), tf_, nf]
        pd = closed_rounded(outline, [0.02 * D, 0.05 * D, 0.02 * D, 0.02 * D, 0.02 * D, 0.02 * D, 0.05 * D, 0.02 * D])
        panel.append(f'<path d="{pd}" fill="{INK if sil else look["coat"]}"/>')
        if not sil:
            # open front showing the dark under-layer, black eri down both front edges
            xp = add(lerp(cf_top, cf_bot, 0.46), mul(yoke, 0.02 * D))
            nn2 = add(nn, mul(yoke, -0.03 * D))
            nf2 = add(nf, mul(yoke, 0.03 * D))
            panel.append(f'<path d="{closed_rounded([add(nn2, mul(yoke, 0.04 * D)), add(nf2, mul(yoke, -0.03 * D)), xp], 0.01 * D)}" fill="{PALE}"/>')
            # far collar band (under), then the near band crossing over it and slanting down the front edge
            panel.append(tube([nf2, xp], [0.06 * D, 0.065 * D], look['eri']))
            hem_cf = add(hf, mul(yoke, -0.10 * D))
            panel.append(tube([nn2, xp, hem_cf], [0.085 * D, 0.08 * D, 0.075 * D], look['eri']))
            anchor.append(f'<path d="{closed_rounded([add(nn, mul(up, 0.05 * D)), add(nf, mul(up, 0.05 * D)), nf, nn], 0.02 * D)}" fill="{look["eri"]}"/>')
        for key, lay in (('arm_f', back), ('arm_n', front)):
            Sx = S[key]
            j, w = J[key]
            u = unit(sub(j, Sx))
            e = add(Sx, mul(u, 0.23 * D))
            cap = tube([add(Sx, mul(u, -0.01 * D)), e], [0.135 * D, 0.15 * D], INK if sil else (look['coat'] if key == 'arm_n' else shade(look['coat'], 0.18)))
            lay.append(cap)
            if not sil:
                cu = (-u[1], u[0])
                lay.append(f'<path d="M{pt(add(e, mul(cu, 0.078 * D)))} L{pt(add(e, mul(cu, -0.078 * D)))}" stroke="{look["eri"]}" '
                           f'stroke-width="{n(0.035 * D)}" stroke-linecap="butt"/>')
        apron(look, J, D, f, view, pose, sil, back, front)
    else:
        tip_n = add(lerp(hn, hf, 0.55), mul(down, 0.09 * D))
        tip_f = add(lerp(hn, hf, 0.72), mul(down, 0.08 * D))
        vpt = add(lerp(Y, J['H'], 0.42), mul(yoke, 0.05 * D))
        outline = [nn, tn, add(lerp(tn, hn, 0.45), mul(on, 0.045 * D)), hn, tip_n, add(lerp(tip_n, tip_f, 0.5), mul(up, 0.03 * D)), tip_f, hf,
                   add(lerp(tf_, hf, 0.45), mul(of, 0.04 * D)), tf_, nf, vpt]
        pd = closed_rounded(outline, [0.01 * D, 0.03 * D, 0.03 * D, 0.02 * D, 0.01 * D, 0.01 * D, 0.01 * D, 0.02 * D, 0.03 * D, 0.03 * D, 0.01 * D, 0.01 * D])
        cid = f'vest3{look["name"]}{int(J["H"][0])}'
        # shirt under the V-neck
        panel.append(f'<path d="{poly([nn, nf, vpt])}" fill="{INK if sil else look["limb"]}"/>')
        panel.append(f'<defs><clipPath id="{cid}"><path d="{pd}"/></clipPath></defs>')
        panel.append(f'<path d="{pd}" fill="{INK if sil else look["vest_a"]}"/>')
        if not sil:
            st = []
            base = lerp(tn, tf_, 0.5)
            ax_ = unit(sub(J['H'], Y))
            sx_ = (-ax_[1], ax_[0])
            for k in range(-7, 8):
                q0 = add(add(base, mul(sx_, k * 0.062 * D)), mul(ax_, -0.3 * D))
                q1 = add(q0, mul(ax_, 1.6 * D))
                st.append(f'<path d="M{pt(q0)} L{pt(q1)}" stroke="{look["vest_b"]}" stroke-width="{n(0.030 * D)}"/>')
            panel.append(f'<g clip-path="url(#{cid})">' + ''.join(st) + '</g>')
            for t in (0.25, 0.48, 0.70):
                q = lerp(vpt, lerp(tip_n, tip_f, 0.5), t)
                panel.append(f'<circle cx="{n(q[0])}" cy="{n(q[1])}" r="{n(0.022 * D)}" fill="{BRASS}"/>')
        tenugui(look, J, D, f, view, pose, sil, back, anchor)


def apron(look, J, D, f, view, pose, sil, back, front):
    H = J['H']
    sw = pose.get('apron', 0)
    Lp = pose.get('apron_len', 0.62) * D
    if view == '34':
        root = add(H, (f * 0.04 * D, -0.02 * D))
        wt_, wb_ = 0.34 * D, 0.42 * D
    else:
        root = add(H, (f * 0.07 * D, -0.03 * D))
        wt_, wb_ = 0.20 * D, 0.28 * D

    def ap(x_, y_):
        return add(root, rotv((f * x_, y_), -f * sw))
    t0, t1 = ap(-wt_ / 2, 0), ap(wt_ / 2, 0)
    b0, b1 = ap(-wb_ / 2 - 0.01 * D, Lp), ap(wb_ / 2 - 0.01 * D, Lp)
    a_ = f'<path d="{closed_rounded([t0, t1, b1, b0], [0.01 * D, 0.02 * D, 0.03 * D, 0.03 * D])}" fill="{INK if sil else SAGE}"/>'
    if not sil:
        m0, m1 = lerp(t0, b0, 0.48), lerp(t1, b1, 0.48)
        a_ += f'<path d="M{pt(lerp(m0, m1, 0.2))} L{pt(lerp(m0, m1, 0.8))}" stroke="{SAGE_D}" stroke-width="{n(0.02 * D)}" stroke-linecap="round"/>'
    if view == '34':
        wb0 = add(J['HP']['leg_n'], (f * -0.12 * D, -0.03 * D))
        wb1 = add(J['HP']['leg_f'], (f * 0.10 * D, -0.035 * D))
    else:
        wb0 = add(H, (f * -0.15 * D, -0.04 * D))
        wb1 = add(H, (f * 0.17 * D, -0.03 * D))
    band = f'<path d="M{pt(wb0)} L{pt(wb1)}" stroke="{INK if sil else look["eri"]}" stroke-width="{n(0.05 * D)}" stroke-linecap="round"/>'
    if view in ('profile', 'twist'):
        tie = pose.get('tie', 0)
        bk = add(wb0, (f * -0.01 * D, 0))
        bow = []
        for dl, ln in ((-10, 0.20), (14, 0.15)):
            e = add(bk, rotv((f * -0.02 * D, ln * D), f * (tie + dl)))
            bow.append(tube([bk, lerp(bk, e, 0.5), e], [0.03 * D, 0.03 * D, 0.026 * D], INK if sil else SAGE_D))
        back.append(''.join(bow))
    front.append(a_ + band)


def tenugui(look, J, D, f, view, pose, sil, back, anchor):
    NB, yoke = J['NB'], J['yoke']
    col = INK if sil else look['tenugui']
    dk = INK if sil else shade(look['tenugui'], 0.18)
    tw = 0.085 * D
    if view == '34':
        b0 = add(NB, add(mul(yoke, -0.13 * D), (0, -0.01 * D)))
        b1 = add(NB, add(mul(yoke, 0.12 * D), (0, -0.005 * D)))
        mid = add(lerp(b0, b1, 0.5), (0, 0.045 * D))
        anchor.append(tube([b0, mid, b1], [tw * 1.05, tw * 1.1, tw], col))
        kn = add(b0, (0.0, 0.02 * D))
    else:
        b0 = add(NB, (f * -0.17 * D, -0.035 * D))
        b1 = add(NB, (f * 0.12 * D, 0.03 * D))
        anchor.append(tube([b0, lerp(b0, b1, 0.5), b1], [tw, tw, tw * 0.95], col))
        kn = add(b1, (f * 0.01 * D, 0.012 * D))
    lag = pose.get('tie_lag', 0)
    for dl, ln in (((-6, 0.17), (16, 0.13)) if view != '34' else ((-4, 0.26), (12, 0.21))):
        e = add(kn, rotv((0, ln * D), f * (dl + lag)))
        anchor.append(tube([kn, e], [0.055 * D, 0.048 * D], dk if dl > 0 else col))
    anchor.append(f'<circle cx="{n(kn[0])}" cy="{n(kn[1])}" r="{n(0.045 * D)}" fill="{col}"/>')


def character(ch, x, look, C, D, f, tilt, uid, pose, view='profile', head_view=None, shadow='', marks='', sil=False, tgt_world=None):
    Lyr, J = body(look, C, D, f, tilt, pose, view, sil)
    layer = pose.get('broom', {}).get('layer', 'front') if pose.get('broom') else None
    o = [shadow]
    o.append(Lyr['far_leg'])
    o.append(Lyr['back'])
    o.append(Lyr['far_arm'])
    if layer == 'behind':
        o.append(Lyr['prop'])
        o.append(Lyr['far_thumb'])
    o.append(Lyr['near_leg'])
    o.append(Lyr['neck'])
    o.append(Lyr['panel'])
    o.append(Lyr['front'])
    o.append(Lyr['anchor'])
    o.append(Lyr['near_upper'])
    o.append(Lyr['near_fore'])
    hv = head_view or ('34' if view == '34' else 'profile')
    o.append(head(ch, x, C, D, f, tilt, uid, hv, tgt_world, sil))
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
    return X(cov=0.47, tilt=4, curve=0.03, low=0.06, brow_raise=-0.012, brow_tilt=7, mouth='smirk')


def snoot_scene_x():
    return X(cov=0.36, tilt=-6, low=0.0, brow_raise=0.025, brow_tilt=-14, brow_arch=0.08, mouth='sneer', nose_up=6,
             flare=True, marks=['snort'], py_bias=0.02)


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
        arm_n=dict(grip=lerp(bro_a, bro_b, 0.02), bend=(-1, 0.35), thumb=-1),
        arm_f=dict(grip=lerp(bro_a, bro_b, 0.085), bend=(-1, -0.15), thumb=-1),
        apron=10, tie=-18, apron_len=0.60,
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
        arm_n=dict(w=(Cn[0] - 0.02 * D, Cn[1] + 2.05 * D), bend=(1, 0.1), hand=96, thumb=1, fist=True),
        arm_f=dict(w=(Cn[0] - 0.24 * D, Cn[1] + 2.0 * D), bend=(1, 0.1), hand=98, thumb=1, fist=True),
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
    ('neutral', X(gaze=(1, 0.05))),
    ('surprised', X(cov=0.0, pr=0.055, gaze=(0.6, -0.2), amt=0.45, brow_raise=0.035, brow_tilt=-8, brow_arch=0.03,
                    mouth='open', jaw=0.04, marks=['emanata'])),
    ('angry', X(cov=0.40, tilt=22, low=0.14, low_tilt=-6, gaze=(1, 0.1), brow_raise=-0.018, brow_tilt=20, mouth='teeth',
                flare=True, marks=['snort'])),
    ('smug', X(cov=0.52, tilt=-4, curve=0.03, low=0.18, low_curve=0.09, gaze=(1, -0.4), brow_raise=0.03, brow_tilt=-12,
               brow_arch=0.035, mouth='smug', nose_up=8)),
    ('panic', X(cov=0.07, tilt=-16, pr=0.055, ghost=True, gaze=(0, 0), amt=0.0, brow_raise=0.03, brow_tilt=-18,
                mouth='wavy', jaw=0.02, marks=['sweat', 'shake'])),
    ('side_eye', X(cov=0.58, tilt=-3, low=0.10, gaze=(-1, 0.15), brow_raise=-0.012, brow_tilt=-5, brow_arch=0.0,
                   mouth='flat', marks=['huff'])),
]


def faces_svg(sil=False):
    for k in ('heads', 'head_pts', 'foot_pts'):
        REG[k].clear()
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">']
    o.append(f'<rect width="1080" height="1080" fill="{"#FFFFFF" if sil else SAND}"/>')
    D = 232
    look = LOOK_SOL
    for i, (nm, x) in enumerate(FACE_SET):
        cx0 = (i % 3) * 360
        cy0 = (i // 3) * 540
        C = (cx0 + 128, cy0 + 262)
        if not sil:
            o.append(f'<circle cx="{n(C[0] + 40)}" cy="{n(C[1] + 10)}" r="168" fill="{PALE}"/>')
        # neck stub + hanten collar anchor
        NT = (C[0] - 0.10 * D, C[1] + 0.40 * D)
        NB = (C[0] - 0.13 * D, C[1] + 0.70 * D)
        o.append(tube([NT, NB], [0.17 * D, 0.17 * D], INK if sil else look['skin']))
        if not sil:
            o.append(tube([NT, lerp(NT, NB, 0.5)], [0.17 * D, 0.17 * D], shade(look['skin'], 0.12)))
        coat = [(NB[0] - 0.36 * D, NB[1] + 0.40 * D), (NB[0] - 0.24 * D, NB[1] - 0.02 * D), (NB[0] + 0.20 * D, NB[1] - 0.02 * D),
                (NB[0] + 0.36 * D, NB[1] + 0.40 * D)]
        o.append(f'<path d="{closed_rounded(coat, 0.05 * D)}" fill="{INK if sil else look["coat"]}"/>')
        if not sil:
            col = [(NB[0] - 0.20 * D, NB[1] + 0.03 * D), (NB[0] - 0.17 * D, NB[1] - 0.09 * D), (NB[0] + 0.11 * D, NB[1] - 0.06 * D),
                   (NB[0] + 0.22 * D, NB[1] + 0.40 * D), (NB[0] + 0.10 * D, NB[1] + 0.40 * D), (NB[0] + 0.03 * D, NB[1] + 0.03 * D)]
            o.append(f'<path d="{closed_rounded(col, 0.02 * D)}" fill="{look["eri"]}"/>')
            o.append(f'<path d="M{pt((NB[0] + 0.05 * D, NB[1] + 0.0 * D))} L{pt((NB[0] + 0.13 * D, NB[1] + 0.36 * D))}" stroke="{PALE}" '
                     f'stroke-width="{n(0.022 * D)}" stroke-linecap="round"/>')
        o.append(head(SOL, x, C, D, 1, 0, f'f{i}', 'profile', None, sil))
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
            arm_n=dict(w=(C[0] + 0.40 * D, C[1] + 1.72 * D), bend=(1, -0.2), hand=-100, thumb=-1, fist=True),
            apron=-3,
        )
        x = X(cov=0.38, gaze=(-1, 0.0), brow_raise=-0.005, brow_tilt=4, mouth='smirk')
        return pose, x, 4.0, (C[0] - 900, C[1] + 20)
    FL0 = C[1] + 3.16 * D
    pose = dict(
        spine=(-4.0, -0.07), neck_lean=14,
        leg_f=dict(a=(C[0] - 0.42 * D, FL0 - ah - 0.045 * D), bend=(-1, 0.1), foot=-8),
        leg_n=dict(a=(C[0] + 0.16 * D, FL0 - ah - 0.045 * D), bend=(-0.3, 0), foot=6),
        arm_n=dict(w=(C[0] + 0.42 * D, C[1] + 1.62 * D), bend=(1, -0.5), hand=-150, thumb=1, fist=True),
        arm_f=dict(w=(C[0] - 0.28 * D, C[1] + 1.64 * D), bend=(-1, -0.5), hand=-40, thumb=-1, fist=True),
        tie_lag=4,
    )
    x = X(cov=0.22, gaze=(-0.5, 1.0), brow_raise=0.0, brow2_raise=0.03, brow2_arch=0.085, mouth='pout', py_bias=0.0)
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
                              eye_over_H=round(ch['eye']['h'] * D / h, 3))

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
