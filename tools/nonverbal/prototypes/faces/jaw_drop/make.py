#!/usr/bin/env python3
"""Jaw Drop / アゴで語るピーナツ頭 -- one face rig, two images.

The rig (`head()`) draws a two-lobe "peanut" head from parameters:
  cranium : ellipse (eyes, brows, nose, ears, hair live here)
  jaw     : rigid ellipse/superellipse lobe on a spring:
            drop (x jaw height), jut (forward px, scales into an underbite),
            shift (sideways px), tuck (up px), jaw_tilt (deg, chin up)
            attached  -> union outline + two cheekbone notches
            dropped   -> dark mouth gap held by two stretched cheek lines (+ tongue, teeth)
  eyes    : solid dots (size, gaze offset, ghost copies) or sagging U-arcs
  brows   : 'cloud' (bushy puffs with a drooping tail) or 'bar'; lift / V / tent / per-side raise / jump
  mouth   : swap set on the jaw's top edge  a seam, b one-sided grin, c clenched teeth,
            d dark open, e chattering zigzag, f flat downturn
  beard   : white tapered shape riding the jaw, bent by beard_swing (the one-beat lag)
  marks   : crease, dust, sweat, gloom, puff
Both scene.svg and faces.svg are built only from this rig.
"""
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
ESP = '#3B2A20'      # espresso
LATTE = '#C9A27E'
MILK = '#F5EDE0'
CINN = '#A0522D'
PIST = '#A7B57E'
CREMA = '#D9B26F'
SKY = '#BFD6DC'
VERM = '#C8452F'
GROUND_SH = '#B48D69'
WHITE = '#F7F3EA'
WHITE_LINE = '#C9C2B2'
MOUTH = '#5A3324'
CREAM = '#FBF1DA'
STONE = '#8F7B68'
HAIR = '#2E231D'

SKIN_MASTER = '#E7BC95'
SKIN_SNAP = '#A06E4C'
SKIN_D1 = '#5D3B2B'
SKIN_D2 = '#E7BC95'

LW = 8
UID = [0]


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
    """Catmull-Rom -> cubic bezier."""
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


def shape(d, fill, line=None, lw=LW, extra=''):
    """Flat fill, outline OUTSIDE the shape in a darker shade of its own fill."""
    line = line or dark(fill)
    return ('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round" '
            'stroke-linecap="round" paint-order="stroke" %s/>' % (d, fill, line, f(2 * lw), extra))


def stroke(d, color, w, extra=''):
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
            'stroke-linejoin="round" %s/>' % (d, color, f(w), extra))


def circle(x, y, r, fill, line=None, lw=LW, extra=''):
    return shape(ell_d(x, y, r, r), fill, line, lw, extra)


def union(parts, fill, line=None, lw=LW, extra=''):
    """Several closed paths drawn as one silhouette: outline only around the union."""
    line = line or dark(fill)
    s = ''.join('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>'
                % (d, line, line, f(2 * lw)) for d in parts)
    s += ''.join('<path d="%s" fill="%s"/>' % (d, fill) for d in parts)
    return '<g %s>%s</g>' % (extra, s)


def ell_pts(cx, cy, rx, ry, n=240, sq=2.0):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        out.append(se_pt(cx, cy, rx, ry, t, sq))
    return out


def se_pt(cx, cy, rx, ry, t, sq=2.0):
    c, s = math.cos(t), math.sin(t)
    return (cx + rx * math.copysign(abs(c) ** (2.0 / sq), c), cy + ry * math.copysign(abs(s) ** (2.0 / sq), s))


def limb(center, w0, w1=None):
    """Thick limb polygon along a polyline centre."""
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


# ---------------------------------------------------------------- marks
def dust(x, y, s=1.0, flip=1):
    puffs = [(-26, 8, 17), (0, -6, 22), (28, 6, 16)]
    parts = [ell_d(x + dx * s * flip, y + dy * s, r * s, r * s) for dx, dy, r in puffs]
    return union(parts, MILK, dark(MILK, 0.3), lw=6)


def sweat(x, y, s=1.0, ang=0):
    d = 'M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z' % (
        f(x), f(y - 26 * s),
        f(x + 8 * s), f(y - 12 * s), f(x + 17 * s), f(y + 2 * s), f(x + 15 * s), f(y + 10 * s),
        f(x + 10 * s), f(y + 22 * s), f(x - 10 * s), f(y + 22 * s), f(x - 15 * s), f(y + 10 * s))
    d += ' C%s,%s %s,%s %s,%s Z' % (f(x - 17 * s), f(y + 2 * s), f(x - 8 * s), f(y - 12 * s), f(x), f(y - 26 * s))
    return '<g transform="rotate(%s %s %s)">%s</g>' % (f(ang), f(x), f(y), shape(d, CREAM, dark(CREAM, 0.3), lw=5))


def puff(x, y, s=1.0, flip=-1):
    parts = [ell_d(x + dx * s * flip, y + dy * s, r * s, r * s) for dx, dy, r in [(0, 0, 9), (17, -6, 12), (36, -14, 8)]]
    return union(parts, MILK, dark(MILK, 0.3), lw=4)


def gloom(x, y, h=40, gap=16, color=None):
    color = color or dark(LATTE, 0.2)
    return ''.join(stroke('M%s,%s L%s,%s' % (f(x + i * gap), f(y), f(x + i * gap), f(y + h - abs(i) * 8)), color, 5)
                   for i in (-1, 0, 1))


# ---------------------------------------------------------------- the rig
DEF = dict(
    cx=0, cy=0, cw=200, ch=140, jw=230, jh=160, ov=28, face=1, turn=0.18,
    skin=SKIN_MASTER, line=None, jaw_sq=2.0, lw=LW,
    drop=0.0, jut=0, shift=0, tuck=0, jaw_tilt=0.0, jaw_ghosts=(),
    eye_y=0.62, eye_gap=66, eye_d=20, eyes='open', gaze=(0, 0), eye_ghosts=(), closed_w=34, closed_t=7,
    brow='cloud', brow_w=76, brow_h=32, brow_lift=0, brow_in=0.0, brow_raise=(0, 0), brow_top=False,
    brow_color=HAIR, brow_gap=28, brow_tail=True,
    mouth='a', mouth_w=80, hair='bald', hair_color=HAIR, ears=True, ear_scale=1.0, lobes=False,
    nose=None, nose_s=1.0, wrinkles=False,
    beard=0, beard_swing=0.0, upper_teeth=0, lower_teeth=0, shadow=False, redtop=0.0,
    marks=(), tongue=CINN, attach=0.8, mouth_color=MOUTH, cheek_bow=0.16, upper_w=0.085, head_tilt=0.0, beard_gap=0.11,
)


def jaw_frame(d, gx=0.0):
    """Return (J, info): J maps jaw-local offsets (u, v) from the jaw centre to world coords."""
    crx, cry = d['cw'] / 2, d['ch'] / 2
    jrx, jry = d['jw'] / 2, d['jh'] / 2
    face = d['face']
    fx = face * d['turn'] * crx
    jx0 = d['cx'] + fx * 0.5
    jy0 = d['cy'] + cry - d['ov'] + jry
    sx = 1 + d['jut'] / 600.0
    jx = jx0 + face * d['jut'] + d['shift'] + gx
    jy = jy0 + d['drop'] * d['jh'] - d['tuck']
    piv = (jx - face * jrx * 0.75, jy - jry * 0.55)
    rot = -face * d['jaw_tilt']

    def J(u, v):
        return rot_pt((jx + u * sx, jy + v), rot, piv)
    return J, dict(jx=jx, jy=jy, jrx=jrx, jry=jry, fx=fx, sx=sx, rot=rot)


def inside_cran(p, d):
    return ((p[0] - d['cx']) / (d['cw'] / 2)) ** 2 + ((p[1] - d['cy']) / (d['ch'] / 2)) ** 2 - 1


def crossings(world_pts, d):
    n = len(world_pts)
    out = []
    for i in range(n):
        a = inside_cran(world_pts[i], d)
        b = inside_cran(world_pts[(i + 1) % n], d)
        if (a < 0) != (b < 0):
            t = a / (a - b)
            p0, p1 = world_pts[i], world_pts[(i + 1) % n]
            out.append((i, (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)))
    return out


def head(P):
    d = dict(DEF)
    d.update(P)
    lw = d['lw']
    cx, cy = d['cx'], d['cy']
    crx, cry = d['cw'] / 2, d['ch'] / 2
    face = d['face']
    skin = d['skin']
    line = d['line'] or dark(skin)
    J, ji = jaw_frame(d)
    fx = ji['fx']
    jrx, jry = ji['jrx'], ji['jry']
    sq = d['jaw_sq']
    N = 240
    unit = ell_pts(0, 0, jrx, jry, N, sq)
    cran = ell_pts(cx, cy, crx, cry, N)
    cran_d = poly(cran)
    jaw_world = [J(u, v) for u, v in unit]
    jaw_d = poly(jaw_world)
    UID[0] += 1
    uid = 'h%d' % UID[0]
    out = []

    cur = crossings(jaw_world, d)
    gap = len(cur) < 2 or d['drop'] * d['jh'] > d['ov'] + 4

    # attachment: cheek points on the cranium's lower sides and the jaw's upper sides
    th = math.acos(d['attach'])
    cran_arc = [(cx + crx * math.cos(t), cy + cry * math.sin(t))
                for t in [th + (math.pi - 2 * th) * k / 30 for k in range(31)]]          # right -> bottom -> left
    jaw_arc = [J(*se_pt(0, 0, jrx, jry, t, sq))
               for t in [math.pi + th + (math.pi - 2 * th) * k / 30 for k in range(31)]]  # left -> top -> right

    def top_v(u):
        """jaw-local v of the top contour above u."""
        a = min(abs(u) / jrx, 0.999)
        return -jry * (1 - a ** sq) ** (1.0 / sq)

    # ---- ghost jaws (chatter)
    for gx in d['jaw_ghosts']:
        Jg, _ = jaw_frame(d, gx=gx)
        g = poly([Jg(u, v) for u, v in unit])
        out.append('<g opacity="0.3">%s</g>' % shape(g, skin, line, lw))

    # ---- ears (behind)
    if d['ears']:
        es = d['ear_scale']
        for sg in (-1, 1):
            ex = cx + sg * crx * 0.93 - fx * 0.35
            ey = cy + cry * 0.30
            ew, eh = 0.10 * d['cw'] * es, 0.20 * d['ch'] * es
            if sg == face:      # far-side ear slightly smaller (3/4 turn)
                ew *= 0.8
                eh *= 0.9
            ox = ex + sg * ew * 0.45
            if d['lobes']:
                ep = [(ox, ey - eh), (ox + sg * ew * 1.0, ey - eh * 0.55), (ox + sg * ew * 0.9, ey + eh * 0.5),
                      (ox + sg * ew * 0.55, ey + eh * 1.35), (ox - sg * ew * 0.1, ey + eh * 1.3), (ox - sg * ew * 0.6, ey)]
                out.append(shape(smooth(ep), skin, line, lw))
            else:
                out.append(shape(ell_d(ox, ey, ew, eh), skin, line, lw))
            out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(ox), f(ey - eh * 0.45), f(ox + sg * ew * 0.75), f(ey + eh * 0.1),
                                                     f(ox + sg * ew * 0.05), f(ey + eh * 0.55)), line, lw * 0.6))

    # ---- hair behind the head (topknot)
    if d['hair'] == 'topknot':
        kx, ky = cx - fx * 0.5, cy - cry - d['ch'] * 0.08
        out.append(circle(kx, ky, d['cw'] * 0.12, d['hair_color'], dark(d['hair_color'], 0.4), lw))

    # ---- mouth gap (behind the lobes) + tongue
    if gap:
        out.append('<path d="%s" fill="%s"/>' % (poly(cran_arc + jaw_arc), d['mouth_color']))
        tu = fx * 0.5
        tc = J(tu, -jry + 4)
        tw = jrx * 0.42
        tth = min(26, 0.17 * d['jh'])
        out.append('<g transform="rotate(%s %s %s)">%s</g>' % (
            f(ji['rot']), f(tc[0]), f(tc[1]), shape(ell_d(tc[0], tc[1], tw, tth), d['tongue'], dark(d['tongue']), lw * 0.6)))

    # ---- lobes: outline pass then fill pass -> one silhouette
    out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (cran_d, line, line, f(2 * lw)))
    out.append('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (jaw_d, line, line, f(2 * lw)))
    out.append('<path d="%s" fill="%s"/>' % (cran_d, skin))
    out.append('<path d="%s" fill="%s"/>' % (jaw_d, skin))
    out.append('<defs><clipPath id="%s-c"><path d="%s"/></clipPath><clipPath id="%s-j"><path d="%s"/></clipPath></defs>'
               % (uid, cran_d, uid, jaw_d))

    # ---- five-o'clock shadow on the jaw
    if d['shadow']:
        sp = [J(-jrx * 1.2, -jry * 0.05), J(-jrx * 0.5, -jry * 0.32 + 0), J(fx * 0.5, -jry * 0.38),
              J(jrx * 0.5, -jry * 0.32), J(jrx * 1.2, -jry * 0.05), J(jrx * 1.2, jry * 1.3), J(-jrx * 1.2, jry * 1.3)]
        out.append('<path d="%s" fill="%s" clip-path="url(#%s-j)"/>' % (smooth(sp), mix(skin, '#2A1A12', 0.22), uid))

    # ---- flush on the crown (anger)
    if d['redtop']:
        red = mix(skin, '#D0402A', d['redtop'])
        y0 = cy - cry * 0.2
        wav = [(cx - crx * 1.1 + i * crx * 2.2 / 12, y0 + (7 if i % 2 else -5)) for i in range(13)]
        rp = [(cx - crx * 1.2, cy - cry - 20), (cx + crx * 1.2, cy - cry - 20)] + wav[::-1]
        out.append('<path d="%s" fill="%s" clip-path="url(#%s-c)"/>' % (smooth(rp), red, uid))

    # ---- hair
    hc = d['hair_color']
    if d['hair'] == 'buzz':
        # flat-top crew cut: rises above the crown, hairline recedes at the temple
        pts = [(-1.02, -0.12), (-0.98, -0.58), (-0.62, -1.02), (-0.45, -1.09), (0.50, -1.09), (0.84, -0.80),
               (0.93, -0.50), (0.66, -0.56), (0.36, -0.72), (0.06, -0.62), (-0.36, -0.54), (-0.70, -0.34), (-0.90, -0.08)]
        hp = [(cx + face * x * crx, cy + y * cry) for x, y in pts]
        out.append(shape(smooth(hp), hc, '#160F0B', lw))
    elif d['hair'] == 'bowl':
        hp = [(-1.08, 0.05), (-1.02, -0.6), (-0.6, -1.08), (0.4, -1.1), (0.95, -0.7), (1.06, -0.1), (0.85, -0.18),
              (0.55, -0.42), (0.25, -0.36), (-0.05, -0.44), (-0.4, -0.3), (-0.75, -0.2)]
        hp = [(cx + face * x * crx, cy + y * cry) for x, y in hp]
        out.append(shape(smooth(hp), hc, dark(hc, 0.4), lw))
    elif d['hair'] == 'topknot':
        hp = [(-1.04, -0.15), (-0.8, -0.85), (0, -1.08), (0.8, -0.85), (1.0, -0.4), (0.4, -0.6), (-0.3, -0.62), (-0.8, -0.35)]
        hp = [(cx + face * x * crx, cy + y * cry) for x, y in hp]
        out.append('<path d="%s" fill="%s" clip-path="url(#%s-c)"/>' % (smooth(hp), hc, uid))
    elif d['hair'] == 'bald':
        # a white tuft behind the ear: three small flicks of hair, same cloud edge as the brows
        sc = d['cw'] / 200
        parts = []
        for k, (a, r, L) in enumerate(((186, 10, 6), (202, 10, 10), (218, 8, 5))):
            a2 = a if face > 0 else 180 - a
            t = math.radians(a2)
            bx, by = cx + crx * math.cos(t), cy + cry * math.sin(t)
            nx, ny = math.cos(t), math.sin(t)
            px, py = bx + nx * L * sc * 0.3, by + ny * L * sc * 0.3
            parts.append(ell_d(px, py, r * sc, r * sc))
            tip = (bx + nx * (L + r + 6) * sc, by + ny * (L + r + 6) * sc + 3 * sc)
            parts.append(smooth(limb([(px - ny * 0, py), (bx + nx * (r + L * 0.6) * sc, by + ny * (r + L * 0.6) * sc - 4 * sc), tip],
                                     r * 1.2 * sc, 2), True))
        out.append(union(parts, WHITE, WHITE_LINE, 3))

    # ---- notches (attached) or stretched cheek lines (dropped)
    if not gap:
        for i, p in sorted(cur, key=lambda t: t[1][0])[:1] + sorted(cur, key=lambda t: t[1][0])[-1:]:
            step = 1 if inside_cran(jaw_world[(i + 1) % N], d) < 0 else -1
            k = i if step > 0 else (i + 1) % N
            run, acc, prev = [p], 0, p
            while acc < 0.08 * d['cw']:
                k = (k + step) % N
                q = jaw_world[k]
                acc += math.hypot(q[0] - prev[0], q[1] - prev[1])
                run.append(q)
                prev = q
            out.append(stroke(poly(run, False), line, lw * 0.8))
    else:
        for c0, j0 in ((cran_arc[-1], jaw_arc[0]), (cran_arc[0], jaw_arc[-1])):
            mxp, myp = (c0[0] + j0[0]) / 2, (c0[1] + j0[1]) / 2
            inward = (cx + fx * 0.5 - mxp) * d['cheek_bow']
            out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(c0[0]), f(c0[1]), f(mxp + inward), f(myp), f(j0[0]), f(j0[1])),
                              line, 6))

    # ---- teeth
    if gap and d['upper_teeth']:
        n = d['upper_teeth']
        w, h = d['upper_w'] * d['cw'], d['upper_w'] * 1.5 * d['ch']
        for k in range(n):
            if n == 2:
                tx = cx + fx * 0.7 + (k - 0.5) * 0.17 * d['cw'] + (8 if k else 0)
            else:
                tx = cx + fx * 0.5 + (k - (n - 1) / 2) * w * 1.18
            ty = cy + cry * math.sqrt(max(0, 1 - ((tx - cx) / crx) ** 2)) + 2
            out.append(shape('M%s,%s L%s,%s L%s,%s Q%s,%s %s,%s Z' % (
                f(tx - w / 2), f(ty - 4), f(tx + w / 2), f(ty - 4), f(tx + w / 2), f(ty + h * 0.75),
                f(tx), f(ty + h * 1.05), f(tx - w / 2), f(ty + h * 0.75)), CREAM, dark(CREAM, 0.35), 3))
    if d['lower_teeth']:
        n = d['lower_teeth']
        tw = 0.085 * d['jw']
        tht = 0.13 * d['jh']
        for k in range(n):
            u = fx * 0.5 + (k - (n - 1) / 2) * tw * 1.25
            if gap:
                v = top_v(u) + 3
            else:
                v = -jry + d['ov'] * 0.55 + 4
            a, b = J(u - tw / 2, v), J(u + tw / 2, v)
            c_, e = J(u + tw / 2 - 2, v - tht), J(u - tw / 2 + 2, v - tht)
            out.append(shape(poly([a, b, c_, e]), CREAM, dark(CREAM, 0.35), 3))

    # ---- mouth (attached shapes ride the jaw)
    m = d['mouth']
    # the lips stay under the nose while the chin juts (underbite): pull the mouth back by most of the jut
    mu, mv = fx * 0.5 - face * d['jut'] * 0.7 / ji['sx'], -jry + d['ov'] * 0.55
    mw = d['mouth_w']

    def M(x, y):           # mouth-local -> world
        return J(mu + x, mv + y)

    if m == 'a':
        a, b, c_ = M(-mw / 2, 0), M(0, 3), M(mw / 2, -1)
        out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1]), f(c_[0]), f(c_[1])), line, lw * 0.85))
    elif m == 'b':
        s = -face          # character's right cheek = near side in a 3/4 view
        p = [M(s * mw * 0.60, -24), M(s * mw * 0.52, -8), M(s * mw * 0.26, 3), M(-s * mw * 0.1, 6), M(-s * mw * 0.42, 2)]
        out.append(stroke(smooth(p, False), line, lw * 1.0))
        # the cheek bunches up above the hooked corner
        c1, c2, c3 = M(s * mw * 0.76, -40), M(s * mw * 0.90, -22), M(s * mw * 0.78, -4)
        out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(c1[0]), f(c1[1]), f(c2[0]), f(c2[1]), f(c3[0]), f(c3[1])), line, lw * 0.7))
    elif m == 'c':
        w, h = 130 * d['cw'] / 200, 38 * d['cw'] / 200
        mv += 8
        corners = [M(-w / 2, -h / 2), M(w / 2, -h / 2), M(w / 2, h / 2), M(-w / 2, h / 2)]
        out.append(shape(poly(corners), CREAM, dark(skin, 0.45), lw * 0.7))
        mid0, mid1 = M(-w / 2, 0), M(w / 2, 0)
        out.append(stroke('M%s,%s L%s,%s' % (f(mid0[0]), f(mid0[1]), f(mid1[0]), f(mid1[1])), dark(CREAM, 0.4), 3))
        for k in range(1, 6):
            x = -w / 2 + k * w / 6
            a, b = M(x, -h / 2), M(x, h / 2)
            out.append(stroke('M%s,%s L%s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1])), dark(CREAM, 0.4), 3))
    elif m == 'd' and not gap:
        a = M(0, 6)
        out.append(shape(ell_d(a[0], a[1], mw * 0.35, 16), MOUTH, line, lw * 0.6))
    elif m == 'e':
        w, h = mw * 1.2, 34 * d['cw'] / 200
        out.append(shape(poly([M(-w / 2, -h / 2), M(w / 2, -h / 2), M(w / 2, h / 2), M(-w / 2, h / 2)]), MOUTH, line, lw * 0.6))
        zz = [(-w / 2 + k * w / 8, (-4 if k % 2 else 5)) for k in range(9)]
        top = [(-w / 2, -h / 2)] + zz + [(w / 2, -h / 2)]
        out.append('<path d="%s" fill="%s"/>' % (poly([M(*q) for q in top]), CREAM))
        bot = [(-w / 2, h / 2)] + [(x, y + 8) for x, y in zz] + [(w / 2, h / 2)]
        out.append('<path d="%s" fill="%s"/>' % (poly([M(*q) for q in bot]), CREAM))
        out.append(stroke(poly([M(*q) for q in zz], False), dark(CREAM, 0.4), 3))
        out.append(stroke(poly([M(x, y + 8) for x, y in zz], False), dark(CREAM, 0.4), 3))
    elif m == 'f':
        p = [M(-mw * 0.5, 14), M(-mw * 0.34, 2), M(mw * 0.3, 2), M(mw * 0.5, 14)]
        out.append(stroke(smooth(p, False), line, lw * 0.85))

    # ---- beard (rides the jaw, bent by beard_swing = the one-beat lag)
    bu = fx * 0.5
    if d['beard']:
        L = d['beard']
        top = mv + d['beard_gap'] * d['jh']
        piv = (bu, jry * 0.7)
        bw = jrx * 0.46
        pts = [(bu - bw * 0.95, top + 10), (bu - bw * 0.5, top), (bu, top - 3), (bu + bw * 0.5, top), (bu + bw * 0.95, top + 10)]
        prof = [(1.08, top / jry * 0.3 + 0.35), (1.12, 0.85), (1.02, 1.0 + 0.16 * L / jry), (1.06, 1.0 + 0.28 * L / jry),
                (0.80, 1.0 + 0.44 * L / jry), (0.82, 1.0 + 0.56 * L / jry), (0.54, 1.0 + 0.72 * L / jry),
                (0.32, 1.0 + 0.86 * L / jry)]
        right = [(bu + a * bw, b * jry) for a, b in prof]
        left = [(bu - a * bw, b * jry) for a, b in prof]
        tip = (bu + face * bw * 0.25, jry + L)
        curl = (bu + face * bw * 0.6, jry + L * 0.93)
        seq = pts + right + [curl, tip] + left[::-1]

        def bend(q):
            u, v = q
            t = max(0.0, min(1.0, (v - piv[1]) / (jry * 0.3 + L)))
            return rot_pt((u, v), -face * d['beard_swing'] * (t ** 0.8), piv)
        wpts = [J(*bend(q)) for q in seq]
        out.append(shape(smooth(wpts), WHITE, WHITE_LINE, lw * 0.75))
        for su in (-0.4, 0.05, 0.42):
            s0 = J(*bend((bu + su * bw, jry * 0.55)))
            s1 = J(*bend((bu + su * 0.75 * bw, jry + L * 0.4)))
            s2 = J(*bend((bu + su * 0.35 * bw, jry + L * 0.68)))
            out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(s0[0]), f(s0[1]), f(s1[0]), f(s1[1]), f(s2[0]), f(s2[1])),
                              WHITE_LINE, 4))

    # ---- eyes
    ey = cy - cry + d['eye_y'] * d['ch']
    exs = [cx + fx - d['eye_gap'] / 2, cx + fx + d['eye_gap'] / 2]
    gzx, gzy = d['gaze']
    if d['wrinkles']:
        for i, ex in enumerate(exs):
            sg = -1 if i == 0 else 1
            ox = ex + sg * (d['closed_w'] * 0.5 + 10)
            for k, dy in enumerate((-7, 5)):
                out.append(stroke('M%s,%s L%s,%s' % (f(ox), f(ey + dy * 0.4), f(ox + sg * 13), f(ey + dy)), line, 4,
                                  'opacity="0.75"'))
    for ex in exs:
        if d['eyes'] == 'closed':
            w = d['closed_w']
            out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(ex - w / 2), f(ey - 4), f(ex), f(ey + 14), f(ex + w / 2), f(ey - 4)),
                              ESP, d['closed_t']))
        else:
            for gdx, gdy in d['eye_ghosts']:
                out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="0.4"/>' % (
                    f(ex + gzx + gdx), f(ey + gzy + gdy), f(d['eye_d'] / 2), ESP))
            out.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(ex + gzx), f(ey + gzy), f(d['eye_d'] / 2), ESP))

    # ---- nose (between the eyes and the seam, turned with the face)
    ns = d['nose_s'] * d['cw'] / 200
    nx, ny = cx + fx * 1.45, cy + cry * 0.46
    if d['nose'] == 'bulb':
        out.append(shape(ell_d(nx, ny, 16 * ns, 13 * ns), skin, line, lw * 0.7))
        out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(nx - face * 8 * ns), f(ny + 5 * ns), f(nx - face * 13 * ns), f(ny + 11 * ns),
                                                 f(nx - face * 3 * ns), f(ny + 11 * ns)), line, 3.5))
    elif d['nose'] == 'broad':
        p = [(nx - face * 18 * ns, ny + 10 * ns), (nx - face * 8 * ns, ny - 14 * ns), (nx + face * 10 * ns, ny - 12 * ns),
             (nx + face * 24 * ns, ny + 6 * ns), (nx + face * 10 * ns, ny + 16 * ns)]
        out.append(shape(smooth(p), skin, line, lw * 0.7))
        out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(nx - face * 10 * ns), f(ny + 6 * ns), f(nx - face * 2 * ns), f(ny + 14 * ns),
                                                 f(nx + face * 8 * ns), f(ny + 10 * ns)), line, 3.5))
    elif d['nose'] == 'button':
        out.append(shape(ell_d(nx, ny, 10 * ns, 8 * ns), skin, line, lw * 0.6))

    # ---- brows
    bw, bh = d['brow_w'], d['brow_h']
    for i, ex in enumerate(exs):
        sg = -1 if i == 0 else 1            # outer side direction (screen)
        bx = ex + sg * bw * 0.06
        if d['brow_top']:
            by = cy - cry - 30 - bh * 0.5
        else:
            by = ey - d['brow_gap'] - d['brow_lift']
        by -= d['brow_raise'][i]
        ang = d['brow_in'] * (1 if i == 0 else -1)
        if d['brow'] == 'cloud':
            puffs = [(-0.40, 0.05, 0.30), (-0.15, -0.10, 0.38), (0.13, -0.08, 0.38), (0.36, 0.06, 0.30)]
            parts = []
            for (u, v, r) in puffs:
                px, py = rot_pt((bx + sg * u * bw, by + v * bh * 1.4), ang, (bx, by))
                rr = r * bh * 1.1
                parts.append(ell_d(px, py, rr, rr))
            if d['brow_tail']:
                droop = 0.35 if d['brow_top'] else 1.0
                tl = [(0.40, 0.15), (0.56, 0.45 + 0.2 * droop), (0.60, 0.7 + 0.9 * droop)]
                tl = [rot_pt((bx + sg * bw * x, by + bh * y), ang, (bx, by)) for x, y in tl]
                parts.append(smooth(limb(tl, bh * 0.55, 3), True))
            base = [rot_pt((bx + sg * bw * x, by + bh * y), ang, (bx, by)) for x, y in
                    [(-0.45, 0.28), (0.40, 0.32), (0.45, 0.0), (-0.45, -0.05)]]
            parts.append(poly(base))
            out.append(union(parts, WHITE, WHITE_LINE, 4))
        else:
            pts = [(-0.5, 0.2), (-0.25, -0.45), (0.25, -0.5), (0.52, -0.05), (0.45, 0.42), (0.05, 0.25), (-0.45, 0.5)]
            q = [rot_pt((bx + sg * bw * x, by + bh * y), ang, (bx, by)) for x, y in pts]
            out.append('<path d="%s" fill="%s"/>' % (smooth(q), d['brow_color']))

    if d['wrinkles']:
        for k in range(2):
            y = cy - cry * (0.50 + 0.17 * k)
            x0 = cx + fx * 0.8
            w = 34 - 8 * k
            out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(x0 - w), f(y + 3), f(x0), f(y - 5), f(x0 + w), f(y + 3)), line, 4,
                              'opacity="0.55"'))

    # ---- marks
    mk = d['marks']
    if 'crease' in mk:
        y = cy - cry * 0.42
        x0 = cx + fx
        out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(x0 - 24), f(y + 5), f(x0), f(y - 7), f(x0 + 24), f(y + 5)), line, 6))
    if 'sweat' in mk:
        out.append(sweat(cx + face * crx * 1.32, cy - cry * 0.38, d['cw'] / 220, 62 * face))
        out.append(sweat(cx - face * crx * 1.36, cy - cry * 0.22, d['cw'] / 210, -62 * face))
    if 'dust' in mk:
        sc = d['cw'] / 200
        for sgn in d.get('dust_sides', (-1, 1)):
            b = J(sgn * jrx * 0.80, jry * 0.62)
            out.append(dust(b[0] + sgn * 30 * sc, b[1] + 4 * sc, sc * 0.55, sgn))
    if 'puff' in mk:
        p = M(-mw * 0.55, 10)
        out.append(puff(p[0] - 6, p[1] + 2, d['cw'] / 200, -1))
    if 'gloom' in mk:
        out.append(gloom(cx + crx * 1.15, cy - cry * 0.9))

    # whole-head tilt about the neck (chin up = positive)
    hang = -face * d['head_tilt']
    neck = (cx + fx * 0.3, cy + cry - d['ov'] + 2 * jry)
    info = dict(J=J, ji=ji, ey=ey, exs=exs, cran=cran,
                jaw_world=[rot_pt(p, hang, neck) for p in jaw_world],
                to_local=lambda p: rot_pt(p, -hang, neck), to_world=lambda p: rot_pt(p, hang, neck))
    tr = ' transform="rotate(%s %s %s)"' % (f(hang), f(neck[0]), f(neck[1])) if hang else ''
    return '<g%s>%s</g>' % (tr, ''.join(out)), info


def jaw_top_at(info, x, tol=4):
    ys = [p[1] for p in info['jaw_world'] if abs(p[0] - x) < tol]
    return min(ys)


# ---------------------------------------------------------------- props
def temari(x, y, r=40):
    out = [circle(x, y, r, CREAM, dark(VERM, 0.35), LW * 0.8)]
    for k in range(0, 6, 2):
        a0 = math.radians(-90 + k * 60 + 20)
        a1 = math.radians(-90 + (k + 1) * 60 + 20)
        out.append('<path d="M%s,%s L%s,%s A%s,%s 0 0 1 %s,%s Z" fill="%s"/>' % (
            f(x), f(y), f(x + r * math.cos(a0)), f(y + r * math.sin(a0)), f(r), f(r),
            f(x + r * math.cos(a1)), f(y + r * math.sin(a1)), VERM))
    out.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="5"/>' % (f(x), f(y), f(r * 0.55), CREMA))
    out.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(x), f(y), f(r * 0.16), CREMA))
    bx, by = x + r * 0.38, y - r * 1.08
    out.append(stroke('M%s,%s Q%s,%s %s,%s' % (f(x + r * 0.1), f(y - r * 0.95), f(x + r * 0.22), f(y - r * 1.2), f(bx), f(by)), VERM, 4))
    out.append(circle(bx, by - 4, r * 0.24, CREMA, dark(CREMA), 3))
    out.append(stroke('M%s,%s L%s,%s' % (f(bx - r * 0.12), f(by - 1), f(bx + r * 0.12), f(by - 1)), dark(CREMA, 0.45), 3))
    return ''.join(out)


PAPER = ('<filter id="paper" x="0" y="0" width="100%" height="100%">'
         '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed="11"/>'
         '<feColorMatrix type="matrix" values="0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0 0 0 0 1"/>'
         '</filter>'
         '<filter id="fiber" x="0" y="0" width="100%" height="100%">'
         '<feTurbulence type="fractalNoise" baseFrequency="0.012 0.05" numOctaves="2" seed="4"/>'
         '<feColorMatrix type="matrix" values="0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0 0 0 0 1"/>'
         '</filter>')


def paper(w, h):
    return ('<rect width="%d" height="%d" filter="url(#paper)" opacity="0.16" style="mix-blend-mode:overlay"/>'
            '<rect width="%d" height="%d" filter="url(#fiber)" opacity="0.10" style="mix-blend-mode:overlay"/>' % (w, h, w, h))


def svg_doc(w, h, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<defs>%s</defs>%s%s</svg>' % (w, h, w, h, PAPER, body, paper(w, h)))


# ---------------------------------------------------------------- characters
def master_params(**kw):
    p = dict(skin=SKIN_MASTER, line='#A9805C', cw=200, ch=140, jw=230, jh=160, ov=28, face=1, turn=0.18,
             brow='cloud', brow_w=76, brow_h=32, hair='bald', beard=120, upper_teeth=2, ear_scale=1.1, lobes=True,
             nose='bulb', wrinkles=True)
    p.update(kw)
    return p


def snap_params(**kw):
    p = dict(skin=SKIN_SNAP, cw=230, ch=165, jw=300, jh=205, ov=30, face=-1, turn=0.22, jaw_sq=2.6,
             brow='bar', brow_w=74, brow_h=26, brow_color=HAIR, hair='buzz', hair_color=HAIR, shadow=True,
             lower_teeth=4, eye_d=16, eye_gap=70, nose='broad')
    p.update(kw)
    return p


# ---------------------------------------------------------------- sheet
SHEET = [
    dict(),                                                                                   # 1 neutral
    dict(eye_d=14, brow_top=True, drop=1.0, mouth='d', beard_swing=82, marks=('dust',)),     # 2 surprised
    dict(brow_in=24, brow_lift=-8, jut=30, mouth='c', redtop=0.16, marks=('crease',)),       # 3 angry
    dict(eyes='closed', tuck=14, jaw_tilt=6, mouth='b', brow_raise=(0, 12), brow_lift=-2),   # 4 smug
    dict(eye_d=14, eye_ghosts=((-9, 0), (9, 0)), brow_in=-20, brow_lift=8, jaw_ghosts=(-20, 20),
         mouth='e', marks=('sweat',), beard_swing=-12),                                       # 5 panic
    dict(gaze=(17, 2), brow_lift=-16, brow_in=-6, shift=-25, jaw_tilt=-4, mouth='f',
         marks=('crease', 'puff'), beard_swing=-12),                                         # 6 side-eye
]


def build_faces():
    W = H = 1080
    body = ['<rect width="1080" height="1080" fill="%s"/>' % MILK]
    for i, ex in enumerate(SHEET):
        col, row = i % 3, i // 3
        ox, oy = col * 360, row * 540
        pass  # cell panel removed: the jaw-drop head overflows any fixed panel
        p = master_params(cx=ox + 180, cy=oy + 146)
        p.update(ex)
        g, _ = head(p)
        body.append(g)
    open(os.path.join(HERE, 'faces.svg'), 'w').write(svg_doc(W, H, ''.join(body)))


# ---------------------------------------------------------------- scene
def place_ball(info, d, r=40, ang=62):
    """Perch the ball on the front-upper curve of the jutting chin: pick the contour point whose outward
    normal points `ang` degrees above horizontal (toward the face direction), clear of the cranium."""
    pts = info['jaw_world']
    n = len(pts)
    cxw = sum(p[0] for p in pts) / n
    cyw = sum(p[1] for p in pts) / n
    want = (d['face'] * math.cos(math.radians(ang)), -math.sin(math.radians(ang)))
    best = None
    for i in range(n):
        a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1
        nx, ny = ty / L, -tx / L
        if (pts[i][0] - cxw) * nx + (pts[i][1] - cyw) * ny < 0:
            nx, ny = -nx, -ny
        score = nx * want[0] + ny * want[1]
        c = (pts[i][0] + nx * (r + 7), pts[i][1] + ny * (r + 7))
        clear = all(inside_cran(info['to_local']((c[0] + (r + 4) * math.cos(t), c[1] + (r + 4) * math.sin(t))), d) > 0
                    for t in [2 * math.pi * k / 24 for k in range(24)])
        if clear and (best is None or score > best[0]):
            best = (score, c, pts[i])
    return best[1], best[2]


def build_scene():
    W, H = 1080, 1920
    b = []
    b.append('<rect width="1080" height="1920" fill="%s"/>' % MILK)
    b.append('<rect width="1080" height="240" fill="%s"/>' % SKY)
    # plaster wall with timber frame
    b.append('<rect x="0" y="236" width="1080" height="660" fill="%s"/>' % MILK)
    for x0, w in ((110, 120), (770, 95)):
        b.append('<path d="%s" fill="%s" opacity="0.55"/>' % (
            poly([(x0, 250), (x0 + w, 250), (x0 + w + 160, 880), (x0 + 160, 880)]), CREMA))
    for x0 in (36, 1004):
        b.append(shape(poly([(x0, 236), (x0 + 40, 236), (x0 + 40, 890), (x0, 890)]), ESP, '#22170F', 4))
    b.append(shape(poly([(-10, 200), (1090, 200), (1090, 236), (-10, 236)]), ESP, '#22170F', 4))
    # moss along the wall base
    mp = [(-20, 920), (-20, 880)] + [(i * 50, 872 + (10 if i % 2 else -2)) for i in range(23)] + [(1100, 880), (1100, 920)]
    b.append(shape(smooth(mp), PIST, None, 6))
    # gravel ground
    b.append('<rect x="0" y="900" width="1080" height="680" fill="%s"/>' % LATTE)
    for y in (985, 1045, 1105):
        b.append(stroke('M-10,%d C300,%d 700,%d 1090,%d' % (y, y - 10, y + 12, y), dark(LATTE, 0.1), 4))
    b.append('<path d="%s" fill="%s" opacity="0.6"/>' % (poly([(0, 1150), (420, 1130), (520, 1200), (0, 1230)]), CREMA))
    b.append('<path d="%s" fill="%s" opacity="0.6"/>' % (poly([(560, 1420), (1080, 1395), (1080, 1470), (640, 1490)]), CREMA))

    # ---- disciples (mid-ground) behind the shrub: the domino
    common = dict(face=1, turn=0.22, brow='bar', ears=True, mouth='d', lw=7, nose='button', jaw_sq=2.2, attach=0.82,
                  cheek_bow=0.12)
    d2 = dict(common, skin=SKIN_D2, cw=104, ch=76, jw=118, jh=84, ov=14, brow_w=30, brow_h=10, brow_color='#4A3326',
              hair='bowl', hair_color='#4A3326', eye_d=10, eye_gap=34, mouth_w=40, drop=0.6, brow_lift=12, gaze=(3, 3),
              upper_teeth=3, upper_w=0.09)
    d1 = dict(common, skin=SKIN_D1, cw=118, ch=84, jw=134, jh=94, ov=15, brow_w=34, brow_h=11, brow_color='#1E1410',
              hair='topknot', hair_color='#1E1410', eye_d=11, eye_gap=38, mouth_w=44, drop=1.05, brow_top=True, gaze=(4, 4),
              mouth_color='#24130E', upper_teeth=3, upper_w=0.09, tongue='#B0603A')
    b.append(shape(smooth([(395, 800), (430, 712), (520, 712), (555, 800)]), MILK, None, 7))
    b.append(stroke('M450,716 L475,770 L500,716', dark(MILK, 0.35), 6))
    b.append(shape(smooth([(520, 810), (556, 740), (664, 740), (700, 810)]), MILK, None, 7))
    g, _ = head(dict(d2, cx=474, cy=530))
    b.append(g)
    g, _ = head(dict(d1, cx=600, cy=540))
    b.append(g)
    # round shrub
    sp = []
    for i in range(36):
        t = 2 * math.pi * i / 36
        r = 150 + (9 if i % 3 == 0 else 0)
        sp.append((540 + r * math.cos(t) * 1.15, 900 + r * math.sin(t) * 0.92))
    b.append(shape(smooth(sp), PIST, None, LW))
    b.append(stroke('M440,850 Q462,822 492,832', dark(PIST, 0.2), 5))
    b.append(stroke('M612,880 Q637,855 662,870', dark(PIST, 0.2), 5))

    # ---- long shadows falling right
    shade = dark(LATTE, 0.14)
    b.append('<path d="%s" fill="%s"/>' % (poly([(520, 1500), (590, 1490), (900, 1540), (820, 1556), (560, 1556)]), shade))
    b.append('<path d="%s" fill="%s"/>' % (poly([(660, 1546), (1080, 1525), (1080, 1560), (700, 1562)]), shade))

    # ---- MASTER (left, seated on a stone, arms folded in his sleeves)
    b.append(shape(smooth([(150, 1500), (170, 1462), (330, 1450), (540, 1458), (585, 1500), (560, 1540), (180, 1544)]),
                   STONE, None, LW))
    b.append(shape(smooth([(170, 1420), (230, 1362), (355, 1352), (480, 1362), (545, 1420), (500, 1468), (355, 1476),
                           (210, 1468)]), MILK, None, LW))
    b.append(stroke('M262,1424 Q355,1444 448,1416', dark(MILK, 0.2), 5))
    b.append(shape(smooth([(266, 1096), (446, 1096), (492, 1190), (498, 1370), (214, 1370), (220, 1190)]), MILK, None, LW))
    b.append('<path d="%s" fill="%s"/>' % (poly([(216, 1306), (497, 1306), (498, 1346), (215, 1346)]), ESP))
    b.append(stroke('M300,1100 L356,1200 L412,1100', ESP, 12))
    for sg in (-1, 1):
        x0 = 356
        dp = [(x0 + sg * 95, 1120), (x0 + sg * 150, 1190), (x0 + sg * 160, 1320), (x0 + sg * 120, 1345),
              (x0 + sg * 70, 1280), (x0 + sg * 10, 1262), (x0 + sg * 10, 1196)]
        b.append(shape(smooth(dp), MILK, None, LW))
    b.append(shape(smooth([(232, 1196), (356, 1184), (480, 1196), (486, 1262), (356, 1276), (226, 1262)]), MILK, None, LW))
    b.append(stroke('M336,1192 L338,1270', ESP, 9))
    b.append(stroke('M376,1192 L374,1270', ESP, 9))
    mp_ = master_params(cx=330, cy=880, cw=250, ch=175, jw=290, jh=195, ov=35, turn=0.24, jut=60, jaw_tilt=8, jaw_sq=2.3, head_tilt=3,
                        eyes='closed', closed_w=42, closed_t=8, mouth='b', brow_w=92, brow_h=38,
                        brow_gap=34, eye_gap=84, eye_d=24, brow_raise=(0, 14), beard=150, beard_gap=0.15, mouth_w=88)
    mh, mi = head(mp_)
    b.append(mh)
    dm = dict(DEF)
    dm.update(mp_)
    (bx, by), (tx, ty) = place_ball(mi, dm, ang=50)
    b.append('<defs><clipPath id="mjaw"><path d="%s"/></clipPath></defs>' % poly(mi['jaw_world']))
    b.append('<ellipse cx="%s" cy="%s" rx="30" ry="14" fill="%s" clip-path="url(#mjaw)"/>' % (
        f(tx + 6), f(ty + 8), mix(SKIN_MASTER, '#6B3F22', 0.3)))
    b.append(temari(bx, by, 40))

    # ---- SNAP (right, low lunge, empty hands)
    b.append(shape(smooth(limb([(905, 1300), (985, 1420), (1010, 1510)], 96, 80), True), CINN, None, LW))
    b.append(shape(smooth([(975, 1505), (1045, 1500), (1056, 1546), (975, 1548)]), SKIN_SNAP, None, LW))
    # far arm (behind torso) to the right hand
    b.append(shape(smooth(limb([(900, 1080), (800, 1225), (690, 1270)], 62, 50), True), dark(CINN, 0.12), None, LW))
    # torso, leaning forward
    b.append(shape(smooth([(965, 1330), (850, 1338), (700, 1150), (640, 1040), (720, 990), (900, 985), (985, 1100)]),
                   CINN, None, LW))
    lap = dark(CINN, 0.3)
    b.append(stroke('M700,1010 Q800,1120 900,1240', lap, 16))
    b.append(stroke('M890,1000 Q840,1100 790,1170', lap, 16))
    b.append('<path d="%s" fill="%s"/>' % (poly([(846, 1290), (968, 1282), (970, 1322), (850, 1330)]), ESP))
    # front leg
    b.append(shape(smooth(limb([(880, 1305), (735, 1370), (715, 1500)], 100, 84), True), CINN, None, LW))
    b.append(shape(smooth([(650, 1512), (742, 1500), (752, 1546), (646, 1548)]), SKIN_SNAP, None, LW))
    # near arm to the left hand
    b.append(shape(smooth(limb([(660, 1050), (622, 1180), (672, 1258)], 66, 54), True), CINN, None, LW))
    sh, si = head(snap_params(cx=790, cy=800, drop=0.62, mouth='d', jut=18, eye_d=14, gaze=(-8, 9), brow_top=True,
                              marks=('dust',), dust_sides=(1,), upper_teeth=5, upper_w=0.062, shadow=False))
    b.append(sh)
    # hands clapped shut around nothing (the ball is on the master's chin)
    hx0, hy0 = 0, 0
    sk = SKIN_SNAP
    b.append('<g transform="translate(612 1262) scale(1.25)">')
    # lower hand: palm up, fingertips curled at the front
    bot = [(hx0 + 58, hy0 + 2), (hx0 - 30, hy0 + 2), (hx0 - 58, hy0 + 4), (hx0 - 66, hy0 + 14), (hx0 - 50, hy0 + 28),
           (hx0 + 10, hy0 + 30), (hx0 + 50, hy0 + 22)]
    b.append(shape(smooth(bot), sk, None, LW))
    # upper hand: back of the hand, four fingertips scalloped at the front
    top = [(hx0 + 58, hy0 - 2), (hx0 + 40, hy0 - 26), (hx0 - 10, hy0 - 32), (hx0 - 40, hy0 - 26)]
    for k in range(4):
        y = hy0 - 22 + k * 7
        top += [(hx0 - 56 - (6 if k in (1, 2) else 0), y), (hx0 - 62 - (6 if k in (1, 2) else 0), y + 3.5)]
    top += [(hx0 - 50, hy0 + 2), (hx0 + 40, hy0 + 2)]
    b.append(shape(smooth(top), mix(sk, '#FFFFFF', 0.07), dark(sk), LW))
    for k in range(3):
        y = hy0 - 15 + k * 7
        b.append(stroke('M%s,%s L%s,%s' % (f(hx0 - 52), f(y), f(hx0 - 28), f(y)), dark(sk), 3.5))
    # thumb along the top
    b.append(shape(smooth(limb([(hx0 + 28, hy0 - 24), (hx0 + 2, hy0 - 36), (hx0 - 24, hy0 - 34)], 17, 12), True), sk, None, 6))
    # sleeve cuffs at the wrists
    b.append(shape(smooth(limb([(hx0 + 50, hy0 - 26), (hx0 + 62, hy0 + 26)], 30, 30), True), CINN, None, 6))
    b.append('</g>')
    hx0, hy0 = 612, 1262
    # clap ticks above the shut hands
    for a in (-120, -90, -60):
        t = math.radians(a)
        p0 = (hx0 - 20 + 56 * math.cos(t), hy0 - 30 + 56 * math.sin(t))
        p1 = (hx0 - 20 + 80 * math.cos(t), hy0 - 30 + 80 * math.sin(t))
        b.append(stroke('M%s,%s L%s,%s' % (f(p0[0]), f(p0[1]), f(p1[0]), f(p1[1])), ESP, 6))
    # skid marks in the gravel behind the front foot
    for k, y in enumerate((1528, 1548)):
        b.append(stroke('M%d,%d L%d,%d' % (760 + k * 20, y, 900 + k * 30, y + 4), dark(LATTE, 0.25), 6))

    b.append('<rect x="0" y="1575" width="1080" height="345" fill="%s"/>' % GROUND_SH)
    open(os.path.join(HERE, 'scene.svg'), 'w').write(svg_doc(W, H, ''.join(b)))


if __name__ == '__main__':
    build_faces()
    build_scene()
