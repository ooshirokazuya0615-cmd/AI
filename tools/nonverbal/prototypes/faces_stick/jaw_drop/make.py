#!/usr/bin/env python3
"""Jaw Drop / アゴで語るピーナツ頭 -- STICK-BODY version. One head rig + one stick-body rig, two images.

HEAD: the original peanut-head face rig, copied unchanged from make_face_original.py
      (head(), jaw_frame(), master_params(), snap_params(), SHEET, marks, temari, paper filter).
BODY: a stick-body rig (new, below the copied rig) driven by a pose dict:
      neck anchor on the CRANIUM (cx - face*0.12*cw, cy + 0.30*ch), shoulder point below the jaw's resting bottom,
      spine lean/hunch, two-bone arms and legs (IK targets, angles or explicit joints), skin mittens with thumb
      nubs, bare dojo feet, sash ring with tails, wrist wraps.  Limbs use this file's limb() polygon in each
      character's tint dark(SKIN, 0.5) with round caps/joins -- no black anywhere on bodies.
Every figure is  body(pose) + head(expression).  scene.svg and poses.svg are built only from these two rigs.
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


# ================================================================ STICK-BODY RIG (new)
SAND = '#E3CFAE'
TICK = dark(LATTE, 0.5)          # emanata / clap ticks: coffee tint, never black


def padd(p, v, s=1.0):
    return (p[0] + v[0] * s, p[1] + v[1] * s)


def pdist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    return (dx / L, dy / L)


def V(a, face):
    """Direction from an angle: 0 = straight down, +90 = toward the facing side, 180 = up, -90 = backward."""
    r = math.radians(a)
    return (face * math.sin(r), math.cos(r))


def ik2(root, target, L1, L2, hint, straight=False):
    """Two-bone IK. hint = (dx, dy) direction the joint should bulge toward."""
    D = pdist(root, target)
    u = unit(root, target)
    # keep a readable 5-8 degree bend unless this is an extension beat
    maxD = (L1 + L2) * (0.99995 if straight else 0.9975)
    Dc = max(abs(L1 - L2) + 1.0, min(D, maxD))
    a = (L1 * L1 - L2 * L2 + Dc * Dc) / (2 * Dc)
    h = math.sqrt(max(0.0, L1 * L1 - a * a))
    n = (-u[1], u[0])
    m = padd(root, u, a)
    j1, j2 = padd(m, n, h), padd(m, n, -h)
    hp = padd(m, hint, 1000)
    joint = j1 if pdist(j1, hp) < pdist(j2, hp) else j2
    return joint, padd(root, u, Dc)


def tube(pts, widths, color):
    """Tapered stick through joints: limb() polygon per segment + round caps / round joins."""
    out = []
    for i in range(len(pts) - 1):
        out.append('<path d="%s"/>' % poly(limb([pts[i], pts[i + 1]], widths[i], widths[i + 1])))
    for p, w in zip(pts, widths):
        out.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(p[0]), f(p[1]), f(w / 2)))
    return '<g fill="%s">%s</g>' % (color, ''.join(out))


def neck_anchor(d):
    """Spine top: on the CRANIUM, hidden behind the jaw lobe; follows the rig's whole-head tilt."""
    a = (d['cx'] - d['face'] * 0.12 * d['cw'], d['cy'] + 0.30 * d['ch'])
    hang = -d['face'] * d['head_tilt']
    fx = d['face'] * d['turn'] * d['cw'] / 2
    piv = (d['cx'] + fx * 0.3, d['cy'] + d['ch'] / 2 - d['ov'] + d['jh'])
    return rot_pt(a, hang, piv)


def jaw_rest_bottom(d):
    return d['cy'] + d['ch'] / 2 - d['ov'] + d['jh']


def body_spec(hu, skin, line, tint):
    return dict(hu=hu, skin=skin, line=line, tint=tint,
                neck_vis=0.14 * hu,                # jaw's resting bottom -> shoulder point (0.14 HU)
                torso=0.72 * hu,                   # shoulder -> hip  (visible neck base -> hip = 0.86 HU)
                upper=0.55 * hu, fore=0.51 * hu,   # shoulder -> wrist 1.06 HU
                thigh=0.66 * hu, shin=0.62 * hu,   # hip -> ankle 1.28 HU (+ foot = ~1.33 HU to the sole)
                arm_w=(17, 14, 11), leg_w=(18, 15, 12), spine_w=17,
                hand_L=0.12 * hu, hand_W=24, hand_lw=5,
                foot_L=0.185 * hu, foot_lw=5)


# ---------------------------------------------------------------- hands, feet, props
def mitten(W, u, S, thumb_side=-1, kind='mitten', scale=1.0):
    """Skin mitten paddle along direction u from the wrist W. Returns (paddle, thumb) so the thumb can sit in
    front of whatever the hand grips. kind: 'mitten' | 'point' (index finger out, a gesture beat)."""
    L, Wd = S['hand_L'] * scale, S['hand_W'] * scale
    n = (-u[1], u[0])

    def P(a, b):
        return (W[0] + u[0] * a + n[0] * b, W[1] + u[1] * a + n[1] * b)
    if kind == 'point':
        L *= 0.78
    pts = [P(-4, -0.36 * Wd), P(0.40 * L, -0.50 * Wd), P(0.82 * L, -0.44 * Wd), P(1.0 * L, -0.06 * Wd),
           P(0.93 * L, 0.30 * Wd), P(0.60 * L, 0.50 * Wd), P(0.15 * L, 0.46 * Wd), P(-4, 0.34 * Wd)]
    paddle = shape(smooth(pts), S['skin'], S['line'], S['hand_lw'])
    if kind == 'point':
        fc = [P(0.7 * L, thumb_side * 0.18 * Wd), P(1.25 * L, thumb_side * 0.22 * Wd), P(1.75 * L, thumb_side * 0.22 * Wd)]
        paddle += shape(smooth(limb(fc, 0.40 * Wd, 0.34 * Wd), True), S['skin'], S['line'], S['hand_lw'] * 0.8)
    s = thumb_side
    c = [P(0.16 * L, s * 0.28 * Wd), P(0.34 * L, s * 0.62 * Wd), P(0.50 * L, s * 0.80 * Wd)]
    thumb = shape(smooth(limb(c, 0.46 * Wd, 0.36 * Wd), True), S['skin'], S['line'], S['hand_lw'] * 0.8)
    return paddle, thumb


def foot(An, toe, S, rot=0.0):
    """Bare dojo foot: rounded skin wedge, flat sole, two toe ticks. toe = +1 toes right / -1 left;
    rot > 0 points the toes down (tiptoe)."""
    L = S['foot_L']
    h = L * 0.40
    sole = 0.55 * h

    def P(a, b):
        return rot_pt((An[0] + toe * a, An[1] + b), rot * toe, An)
    pts = [P(-0.14 * L, -0.48 * h), P(-0.26 * L, 0.02 * h), P(-0.21 * L, sole), P(0.05 * L, sole + 1), P(0.35 * L, sole + 1),
           P(0.64 * L, sole), P(0.84 * L, 0.40 * h), P(0.87 * L, 0.04 * h), P(0.64 * L, -0.22 * h), P(0.24 * L, -0.40 * h)]
    out = shape(smooth(pts), S['skin'], S['line'], S['foot_lw'])
    for x in (0.60, 0.72):
        a, b = P(x * L, -0.06 * h), P((x + 0.04) * L, 0.30 * h)
        out += stroke('M%s,%s L%s,%s' % (f(a[0]), f(a[1]), f(b[0]), f(b[1])), S['line'], 3.5)
    return out


def sole_drop(S):
    """Ankle-centre height above the floor so the sole sits flat on the floor line."""
    return S['foot_L'] * 0.40 * 0.55 + S['foot_lw'] * 0.6


def ribbon(pts, w0, w1, color, lw=3):
    return shape(smooth(limb(pts, w0, w1), True), color, dark(color, 0.35), lw)


def sash(H, up, face, color, tails, rx=33, ry=10, band=11):
    """Sash ring around the hip (back arc / front arc + knot + tails). tails: list of point lists relative to
    the knot. Returns (back, front)."""
    c = padd(H, up, 16)
    px = (-up[1], up[0])
    if px[0] < 0:
        px = (-px[0], -px[1])
    dn = (-up[0], -up[1])

    def E(t):
        return (c[0] + px[0] * rx * math.cos(t) + dn[0] * ry * math.sin(t),
                c[1] + px[1] * rx * math.cos(t) + dn[1] * ry * math.sin(t))
    line = dark(color, 0.35)
    back_pts = [E(math.pi + math.pi * k / 16) for k in range(17)]
    front_pts = [E(math.pi * k / 16) for k in range(17)]

    def arc(pts):
        d = poly(pts, False)
        return stroke(d, line, band + 6) + stroke(d, color, band)
    back = arc(back_pts)
    front = arc(front_pts)
    k = E(math.pi / 2 - face * 0.55)
    for t in tails:
        front += ribbon([k] + [padd(k, q) for q in t], 13, 7, color)
    front += circle(k[0], k[1], 9, color, line, 3)
    return back, front


def wraps(E, W, S, color, flutter=None, ts=(0.62, 0.80)):
    """Cloth wrist wraps: two short bands on the forearm (+ an optional loose end streaming toward `flutter`)."""
    u = unit(E, W)
    n = (-u[1], u[0])
    line = dark(color, 0.35)
    out = ''
    for t in ts:
        c = (E[0] + (W[0] - E[0]) * t, E[1] + (W[1] - E[1]) * t)
        hw, ht = 15, 5
        q = [padd(padd(c, n, hw), u, -ht), padd(padd(c, n, hw), u, ht), padd(padd(c, n, -hw), u, ht), padd(padd(c, n, -hw), u, -ht)]
        out += shape(poly(q), color, line, 2.5)
    if flutter:
        c = (E[0] + (W[0] - E[0]) * ts[1], E[1] + (W[1] - E[1]) * ts[1])
        a = padd(c, n, 12)
        out = ribbon([a, padd(a, flutter, 0.5), padd(padd(a, flutter, 1.0), n, 6)], 9, 4, color, 2) + out
    return out


# ---------------------------------------------------------------- the body
def solve_limb(root, spec, L1, L2, face):
    if 'ang' in spec:
        a1, a2 = spec['ang']
        J = padd(root, V(a1, face), L1)
        return J, padd(J, V(a2, face), L2)
    if 'pts' in spec:
        (jx, jy), (ex, ey) = spec['pts']
        return (root[0] + jx, root[1] + jy), (root[0] + ex, root[1] + ey)
    tgt = spec['to'] if 'to' in spec else padd(root, spec['rel'])
    return ik2(root, tgt, L1 * spec.get('k', 1.0), L2 * spec.get('k', 1.0), spec.get('hint', (0, 1)),
               spec.get('straight', False))


def body(P, pose, S):
    """Stick body for head params P (world coords). Returns (layers, joints)."""
    d = dict(DEF)
    d.update(P)
    face = d['face']
    A = neck_anchor(d)
    Sh = (A[0] + pose.get('neck_dx', 0), jaw_rest_bottom(d) + S['neck_vis'] + pose.get('neck_extra', 0))
    lean = math.radians(pose.get('lean', 0))
    t = (-face * math.sin(lean), math.cos(lean))
    H = padd(Sh, t, S['torso'] * pose.get('torso_k', 1.0))
    back = (-face * math.cos(lean), -math.sin(lean))
    M = padd(((Sh[0] + H[0]) / 2, (Sh[1] + H[1]) / 2), back, pose.get('hunch', 0))
    J = dict(A=A, Sh=Sh, H=H, M=M)
    L = {k: '' for k in ('shadow', 'far_leg', 'far_arm', 'spine', 'back_props', 'mid', 'front_props', 'near_leg',
                         'near_arm', 'hand_prop', 'marks')}
    L['spine'] = stroke(smooth([A, Sh, M, H], False), S['tint'], S['spine_w'])

    # legs
    for side in ('far', 'near'):
        g = pose['legs'][side]
        K, An = solve_limb(H, g, S['thigh'], S['shin'], face)
        J[side + '_knee'], J[side + '_ankle'] = K, An
        s = tube([H, K, An], S['leg_w'], S['tint'])
        ft = g.get('foot', {})
        if ft is not None:
            s += foot(An, ft.get('toe', face), S, ft.get('rot', 0))
        layer = g.get('layer', side + '_leg')
        L[layer] += s

    # arms
    arm_layer = pose.get('arm_layer', {})
    for side in ('far', 'near'):
        g = pose['arms'][side]
        E, W = solve_limb(Sh, g, S['upper'], S['fore'], face)
        J[side + '_elbow'], J[side + '_wrist'] = E, W
        s = tube([Sh, E, W], S['arm_w'], S['tint'])
        if g.get('wraps'):
            s += wraps(E, W, S, g['wraps'], g.get('flutter'))
        hd = g.get('hand', 'mitten')
        if hd:
            u = unit(E, W)
            if 'hand_dir' in g:
                u = g['hand_dir']
            if g.get('hand_rot'):
                u = rot_pt(u, g['hand_rot'], (0, 0))
            pad, th = mitten(W, u, S, g.get('thumb', -1), hd, g.get('hand_scale', 1.0))
            s += pad + th
        layer = arm_layer.get(side, {'far': 'far_arm', 'near': 'near_arm'}[side])
        L[layer] += s

    # props on the spine
    for kind, kw in pose.get('props', ()):
        if kind == 'sash':
            up = unit(H, M)
            b, fr = sash(H, up, face, kw['color'], kw.get('tails', ()))
            L['back_props'] += b
            L['front_props'] += fr
    return L, J


def figure(P, pose, S, under='', over=''):
    """Assemble one character in the fixed layer order: cast shadow, far leg, far arm, spine, back props,
    head (rig), front props, near leg, near arm, hand prop, marks.  Returns (svg, joints, head_info)."""
    L, J = body(P, pose, S)
    g, info = head(P)
    seq = [L['shadow'], under, L['far_leg'], L['far_arm'], L['spine'], L['back_props'], L['mid'], g,
           L['front_props'], L['near_leg'], L['near_arm'], L['hand_prop'], over, L['marks']]
    return ''.join(seq), J, info


# ---------------------------------------------------------------- helpers on the copied rig (read-only)
def beard_points(P):
    """World positions of the beard root, curl and tip, using the same geometry as head() (no drawing)."""
    d = dict(DEF)
    d.update(P)
    J, ji = jaw_frame(d)
    jrx, jry, fx = ji['jrx'], ji['jry'], ji['fx']
    face = d['face']
    bu = fx * 0.5
    L = d['beard']
    piv = (bu, jry * 0.7)
    bw = jrx * 0.46

    def bend(q):
        u, v = q
        t = max(0.0, min(1.0, (v - piv[1]) / (jry * 0.3 + L)))
        return rot_pt((u, v), -face * d['beard_swing'] * (t ** 0.8), piv)
    hang = -face * d['head_tilt']
    neck = (d['cx'] + fx * 0.3, d['cy'] + d['ch'] / 2 - d['ov'] + 2 * jry)

    def W(q):
        return rot_pt(J(*bend(q)), hang, neck)
    return dict(root=W((bu, jry * 0.6)), mid=W((bu, jry + L * 0.5)), pre=W((bu + face * bw * 0.1, jry + L * 0.8)),
                curl=W((bu + face * bw * 0.6, jry + L * 0.93)), tip=W((bu + face * bw * 0.25, jry + L)))


def star4(x, y, r, fill=CREAM, line=None):
    pts = []
    for k in range(8):
        a = math.radians(-90 + k * 45)
        rr = r if k % 2 == 0 else r * 0.30
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return shape(poly(pts), fill, line or dark(CREMA, 0.35), 2.5)


def ting(bx, by, s=1.0):
    """Bell 'ting': a small four-point glint plus three radiating ticks (no glyphs)."""
    out = star4(bx + 44 * s, by - 30 * s, 17 * s)
    for a in (-150, -112, -74, -36):
        t = math.radians(a)
        p0 = (bx + 30 * s * math.cos(t), by - 6 * s + 30 * s * math.sin(t))
        p1 = (bx + 50 * s * math.cos(t), by - 6 * s + 50 * s * math.sin(t))
        out += stroke('M%s,%s L%s,%s' % (f(p0[0]), f(p0[1]), f(p1[0]), f(p1[1])), dark(CREMA, 0.4), 5)
    return out


def dotted(d, color=None, w=8, gap=19):
    return stroke(d, color or dark(LATTE, 0.3), w, 'stroke-dasharray="0.1 %s"' % gap)


def clap_ticks(x, y, r0=34, r1=58, angs=(-150, -120, -90, 150, 180)):
    out = ''
    for a in angs:
        t = math.radians(a)
        out += stroke('M%s,%s L%s,%s' % (f(x + r0 * math.cos(t)), f(y + r0 * math.sin(t)),
                                         f(x + r1 * math.cos(t)), f(y + r1 * math.sin(t))), TICK, 6)
    return out


def stone(x0, x1, top, bottom, fill=None):
    """Flat sitting stone: pale top face (so the tinted legs read on it) over a darker body."""
    fill = fill or mix(STONE, MILK, 0.35)
    topc = mix(STONE, MILK, 0.62)
    w = x1 - x0
    bodyp = [(x0 + 10, top + 14), (x0 + w * 0.5, top + 26), (x1 - 8, top + 12), (x1 + 6, (top + bottom) / 2),
             (x1 - 14, bottom), (x0 + w * 0.5, bottom + 6), (x0 + 12, bottom), (x0 - 8, (top + bottom) / 2 + 6)]
    out = shape(smooth(bodyp), fill, dark(fill, 0.3), 6)
    tp = [(x0, top + 12), (x0 + w * 0.2, top - 6), (x0 + w * 0.55, top - 10), (x1 - 4, top), (x1 - 10, top + 16),
          (x0 + w * 0.5, top + 26), (x0 + 16, top + 22)]
    out += shape(smooth(tp), topc, dark(fill, 0.3), 6)
    out += stroke('M%s,%s Q%s,%s %s,%s' % (f(x0 + w * 0.62), f(top + 44), f(x0 + w * 0.7), f(top + 60),
                                         f(x0 + w * 0.82), f(top + 58)), dark(fill, 0.22), 5)
    return out


def cast_shadow(x, y, rx, ry=16, color=None):
    return '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"/>' % (f(x), f(y), f(rx), f(ry),
                                                                     color or mix(SAND, GROUND_SH, 0.55))

# ================================================================ cast
def master_spec(hu):
    return body_spec(hu, SKIN_MASTER, '#A9805C', dark(SKIN_MASTER, 0.5))


def snap_spec(hu=340):
    return body_spec(hu, SKIN_SNAP, dark(SKIN_SNAP), dark(SKIN_SNAP, 0.5))


def mook_spec(skin, hu=238):
    S = body_spec(hu, skin, dark(skin), dark(skin, 0.5))
    S.update(arm_w=(14, 12, 10), leg_w=(15, 13, 11), spine_w=14, hand_W=20, foot_lw=4, hand_lw=4)
    return S


def place(P, pose, S, hip):
    """Move the head so the body's hip lands on `hip` (the body hangs from the head's neck anchor)."""
    P = dict(P)
    q = dict(pose)
    q['arms'] = dict(far=dict(ang=(0, 0), hand=None), near=dict(ang=(0, 0), hand=None))
    q['legs'] = dict(far=dict(ang=(0, 0), foot=None), near=dict(ang=(0, 0), foot=None))
    q['props'] = ()
    P.update(cx=0, cy=0)
    _, J = body(P, q, S)
    P.update(cx=hip[0] - J['H'][0], cy=hip[1] - J['H'][1])
    return P


def crossed_legs(spread, s=1.0):
    """Cross-legged seat (pts relative to the hip): knees out to both sides, shins crossing in front."""
    return dict(far=dict(pts=((-spread, 26 * s), (22 * s, 52 * s)), foot=dict(toe=1, rot=-16)),
                near=dict(pts=((spread, 32 * s), (-22 * s, 60 * s)), foot=dict(toe=-1, rot=-16)))


def folded_arms(hu):
    """Arms folded across the chest. Upper arms come toward the viewer, so they are drawn foreshortened
    (explicit joints); the forearms cross in front of the spine and each mitten grips the other upper arm."""
    k = hu / 335.0
    return dict(far=dict(pts=((-70 * k, 128 * k), (64 * k, 112 * k)), hand_rot=-62, thumb=-1),
                near=dict(pts=((72 * k, 136 * k), (-66 * k, 124 * k)), hand_rot=62, thumb=1))


MASTER_SASH = ('sash', dict(color=PIST, tails=[[(10, 28), (16, 60)], [(-6, 30), (-6, 64)]]))


# ================================================================ scene
FLOOR = 1562


def build_scene():
    W, H = 1080, 1920
    b = ['<rect width="1080" height="1920" fill="%s"/>' % MILK]
    b.append('<rect width="1080" height="250" fill="%s"/>' % SKY)
    # cream back wall with crema light shafts, espresso beam and posts
    b.append('<rect x="0" y="236" width="1080" height="700" fill="%s"/>' % MILK)
    for x0, w in ((96, 120), (752, 100)):
        b.append('<path d="%s" fill="%s" opacity="0.5"/>' % (
            poly([(x0, 240), (x0 + w, 240), (x0 + w + 170, 930), (x0 + 170, 930)]), CREMA))
    for x0 in (26, 1012):
        b.append(shape(poly([(x0, 236), (x0 + 42, 236), (x0 + 42, 940), (x0, 940)]), ESP, dark(ESP, 0.3), 4))
    b.append(shape(poly([(-10, 196), (1090, 196), (1090, 236), (-10, 236)]), ESP, dark(ESP, 0.3), 4))
    b.append(shape(poly([(-10, 236), (1090, 236), (1090, 250), (-10, 250)]), mix(ESP, LATTE, 0.35), dark(ESP, 0.3), 3))

    # ---- two disciples behind the hedge (stick mooks, peanut heads at 0.7x): jaws drop in unison
    ball = (560, 540)
    mk = dict(cw=161, ch=115, jw=210, jh=143, ov=21, turn=0.22, jaw_sq=2.4, lw=7, brow='bar', brow_w=50, brow_h=18,
              eye_d=13, eye_gap=50, mouth='d', mouth_w=56, drop=0.8, shadow=True, lower_teeth=3, nose='broad',
              nose_s=0.8, brow_lift=12, attach=0.82, cheek_bow=0.12)
    D1 = dict(mk, skin='#8A5A3E', hair='buzz', hair_color=HAIR, brow_color=HAIR, face=1, cx=168, cy=448, gaze=(6, -5))
    D2 = dict(mk, skin='#D2A07A', hair='topknot', hair_color='#8E877C', brow_color='#6E675D', face=-1, cx=898, cy=424,
              gaze=(-6, -5))
    for Dp in (D1, D2):
        S = mook_spec(Dp['skin'])
        dd = dict(DEF)
        dd.update(Dp)
        sh = (neck_anchor(dd)[0], jaw_rest_bottom(dd) + S['neck_vis'])
        u = unit(sh, ball)
        reach = (S['upper'] + S['fore']) * 0.995
        pose = dict(lean=0, hunch=4,
                    arms=dict(far=dict(to=(sh[0] - Dp['face'] * 70, 878), hint=(-Dp['face'], 0), hand_dir=(Dp['face'] * 0.2, 1), thumb=Dp['face']),
                              near=dict(to=padd(sh, u, reach), straight=True, hint=(0, 1), hand='point',
                                        thumb=-Dp['face'])),
                    arm_layer=dict(near='mid'),
                    legs=dict(far=dict(ang=(-4, -2), foot=None), near=dict(ang=(6, 2), foot=None)),
                    props=[('sash', dict(color=CINN, tails=[[(4, 26), (8, 52)], [(-8, 26), (-12, 50)]]))])
        g, _, _ = figure(Dp, pose, S)
        b.append(g)

    b.append('<rect x="0" y="250" width="1080" height="690" fill="%s" opacity="0.24"/>' % MILK)
    # PIST hedge in front of the disciples' legs
    hp = [(-30, 1100), (-30, 900)]
    for i in range(24):
        x = -20 + i * 49
        hp.append((x, 886 + (12 if i % 2 else -6)))
    hp += [(1110, 900), (1110, 1100)]
    b.append(shape(smooth(hp), PIST, None, 6))
    for x, y in ((120, 960), (300, 1000), (470, 950), (650, 990), (840, 955), (990, 1005)):
        b.append(stroke('M%d,%d q22,-24 46,-10' % (x, y), dark(PIST, 0.2), 5))

    # raked sand floor (lightened so the tinted limbs read)
    b.append('<rect x="0" y="1060" width="1080" height="860" fill="%s"/>' % SAND)
    for k, y in enumerate(range(1110, 1540, 54)):
        b.append(stroke('M-10,%d C260,%d 620,%d 1090,%d' % (y, y - 8 + k % 2 * 6, y + 10, y - 2), dark(SAND, 0.06), 4))
    b.append('<rect x="0" y="1606" width="1080" height="314" fill="%s"/>' % mix(SAND, GROUND_SH, 0.3))
    b.append(stroke('M0,1606 L1080,1606', mix(SAND, GROUND_SH, 0.45), 4))
    for x, y, r in ((140, 1700, 14), (176, 1716, 9), (520, 1770, 12), (860, 1690, 15), (900, 1712, 8), (660, 1850, 10)):
        b.append(shape(ell_d(x, y, r * 1.4, r), mix(SAND, STONE, 0.35), None, 4))

    # ---- MASTER: seated cross-legged on his flat stone, arms folded, head rocked back -> beard volley
    Sm = master_spec(335)
    Pm = master_params(cx=330, cy=820, cw=250, ch=175, jw=290, jh=195, ov=35, turn=0.24, jut=40, jaw_tilt=8, tuck=10,
                       jaw_sq=2.3, head_tilt=12, eyes='closed', closed_w=44, closed_t=12, mouth='b', brow_w=92,
                       brow_h=38, brow_gap=34, eye_gap=84, eye_d=24, brow_raise=(0, 12), beard=150, beard_gap=0.15,
                       mouth_w=88, beard_swing=82)
    pose_m = dict(lean=-6, hunch=16, arms=folded_arms(335), arm_layer=dict(far='mid', near='mid'),
                  legs=crossed_legs(150), props=[MASTER_SASH])
    _, Jm = body(Pm, pose_m, Sm)
    hip = Jm['H']
    st_top = hip[1] + 72
    b.append(cast_shadow(hip[0] + 30, FLOOR + 8, 250, 20))
    b.append(stone(hip[0] - 215, hip[0] + 225, st_top, FLOOR))
    gm, Jm, mi = figure(Pm, pose_m, Sm)
    b.append(gm)
    bp = beard_points(Pm)

    # ---- SNAP: deep forward lunge, mittens clapping shut on the air where the ball was, jaw on his chest
    Ss = snap_spec(340)
    Ps = snap_params(cx=790, cy=800, drop=1.0, mouth='d', eye_d=14, brow_top=True, gaze=(-7, -8))
    sd = sole_drop(Ss)
    clap = (532, 1222)
    pose_s = dict(lean=14, hunch=-6,
                  arms=dict(far=dict(to=(clap[0] + 12, clap[1] - 13), hint=(0.35, 1), thumb=1, hand_scale=1.08, wraps=CINN,
                                     flutter=(44, -18)),
                            near=dict(to=(clap[0] + 16, clap[1] + 13), hint=(0.35, 1), thumb=-1, hand_scale=1.08, wraps=CINN,
                                      flutter=(46, -4))),
                  arm_layer=dict(near='mid'),
                  legs=dict(near=dict(to=(624, FLOOR - sd), hint=(-1, -1.2), foot=dict(toe=-1)),
                            far=dict(to=(1004, FLOOR - sd - 18), hint=(-1, 0.9), foot=dict(toe=-1, rot=58))),
                  props=[('sash', dict(color=CINN, tails=[[(46, -22), (100, -40), (156, -30)],
                                                          [(44, -4), (96, -8), (146, 8)]]))])
    _, Js = body(Ps, pose_s, Ss)
    b.append(cast_shadow(800, FLOOR + 6, 230, 16))
    b.append(dust(Js['near_ankle'][0] + 52, FLOOR - 16, 0.85, 1))
    b.append(dust(Js['far_ankle'][0] + 40, FLOOR - 24, 0.75, 1))
    gs, Js, si = figure(Ps, pose_s, Ss)
    b.append(gs)
    b.append(clap_ticks(clap[0] - 6, clap[1], 44, 74, angs=(-165, -130, -95, 165, 130)))
    b.append(puff(clap[0] - 44, clap[1] + 6, 0.8, -1))

    # ---- the temari: volleyed high off the beard tip, dotted arc + bell ting, clear sky of cream wall
    tip, pre = bp['tip'], bp['pre']
    u = unit(pre, tip)
    c1 = padd(tip, u, 160)
    b.append(dotted('M%s,%s Q%s,%s %s,%s' % (f(tip[0] + u[0] * 30), f(tip[1] + u[1] * 30), f(c1[0]), f(c1[1]),
                                           f(ball[0] + 8), f(ball[1] + 48))))
    b.append(temari(ball[0], ball[1], 40))
    b.append(ting(ball[0] + 15, ball[1] - 43, 1.0))
    open(os.path.join(HERE, 'scene.svg'), 'w').write(svg_doc(W, H, ''.join(b)))
    return dict(master=Jm, snap=Js, beard=bp)


# ================================================================ poses sheet
def build_poses():
    W = H = 1080
    b = ['<rect width="1080" height="1080" fill="%s"/>' % MILK]
    b.append('<rect x="0" y="920" width="1080" height="160" fill="%s"/>' % SAND)
    b.append(stroke('M0,920 L1080,920', mix(SAND, GROUND_SH, 0.4), 4))
    S = master_spec(272)
    ST_TOP = 880
    spread = 124

    # (1) READY: cross-legged, arms folded, beard calm, temari resting in the beard's curled tip
    P1 = master_params(eyes='closed', mouth='a', closed_t=10)
    pose1 = dict(lean=0, hunch=14, arms=folded_arms(272), arm_layer=dict(far='mid', near='mid'),
                 legs=crossed_legs(spread), props=[MASTER_SASH])
    P1 = place(P1, pose1, S, (172, ST_TOP - 68))
    b.append(cast_shadow(180, 968, 170, 14))
    b.append(stone(180 - 150, 180 + 150, ST_TOP, 966))
    g, J1, _ = figure(P1, pose1, S)
    b.append(g)
    bp = beard_points(P1)
    cu = bp['curl']
    b.append(temari(cu[0] + 6, cu[1] - 34, 32))

    # (2) SIGNATURE 'BEARD VOLLEY': leaning back on one planted mitten, head tipped back, beard whips the ball up
    P2 = master_params(eyes='closed', closed_t=10, tuck=14, jaw_tilt=6, mouth='b', brow_raise=(0, 12), brow_lift=-2,
                       beard_swing=82, head_tilt=12)
    pose2 = dict(lean=-22, hunch=-6, legs=crossed_legs(spread), props=[MASTER_SASH],
                 arms=dict(far=dict(ang=(0, 0)), near=dict(ang=(0, 0))))
    P2 = place(P2, pose2, S, (528, ST_TOP - 68))
    _, J2 = body(P2, pose2, S)
    hp2 = J2['H']
    pose2['arms'] = dict(far=dict(to=(hp2[0] - 128, ST_TOP - 8 - 12), hint=(-1, -0.4), hand_dir=(-1, 0.05), thumb=-1),
                         near=dict(to=(hp2[0] + spread - 22, hp2[1] + 22), hint=(1, 0.1), hand_dir=(0.6, 0.8),
                                   thumb=-1))
    b.append(cast_shadow(540, 968, 170, 14))
    b.append(stone(540 - 150, 540 + 150, ST_TOP, 966))
    g, J2, _ = figure(P2, pose2, S)
    b.append(g)
    bp = beard_points(P2)
    tip, pre = bp['tip'], bp['pre']
    u = unit(pre, tip)
    ballp = (626, 132)
    c1 = padd(tip, u, 150)
    b.append(dotted('M%s,%s Q%s,%s %s,%s' % (f(tip[0] + u[0] * 24), f(tip[1] + u[1] * 24), f(c1[0]), f(c1[1]),
                                           f(ballp[0] - 4), f(ballp[1] + 40)), w=7, gap=17))
    b.append(temari(ballp[0], ballp[1], 32))
    b.append(ting(ballp[0] + 12, ballp[1] - 35, 0.8))

    # (3) BIG REACTION 'JAW-DROP HOP': 60 px up off the stone, legs still crossed, arms out, jaw below the chest
    P3 = master_params(eye_d=14, brow_top=True, drop=1.0, mouth='d', beard_swing=60)
    pose3 = dict(lean=2, hunch=0, legs=crossed_legs(spread * 0.92), props=[MASTER_SASH],
                 arms=dict(far=dict(ang=(-124, -172), thumb=-1),
                           near=dict(ang=(124, 172), thumb=1)),
                 arm_layer=dict(far='far_arm', near='mid'))
    P3 = place(P3, pose3, S, (872, ST_TOP - 68 - 60))
    b.append(cast_shadow(880, 968, 150, 12))
    b.append(stone(880 - 150, 880 + 150, ST_TOP, 966))
    b.append('<ellipse cx="880" cy="%d" rx="110" ry="12" fill="%s"/>' % (ST_TOP + 6, mix(STONE, MILK, 0.45)))
    for x in (816, 880, 944):
        b.append(stroke('M%d,%d L%d,%d' % (x, ST_TOP - 26, x, ST_TOP - 4), TICK, 5))
    b.append(dust(880 - 150, ST_TOP + 4, 0.8, -1))
    b.append(dust(880 + 150, ST_TOP + 4, 0.8, 1))
    g, J3, _ = figure(P3, pose3, S)
    b.append(g)
    open(os.path.join(HERE, 'poses.svg'), 'w').write(svg_doc(W, H, ''.join(b)))
    return dict(p1=J1, p2=J2, p3=J3)


if __name__ == '__main__':
    import json
    js = build_scene()
    jp = build_poses()
    rnd = lambda v: [round(v[0]), round(v[1])] if isinstance(v, tuple) else v
    print(json.dumps({k: {kk: rnd(vv) for kk, vv in v.items()} for k, v in dict(js, **jp).items()}))
