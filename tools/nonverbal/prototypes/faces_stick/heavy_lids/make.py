#!/usr/bin/env python3
"""Heavy Lids / 半目の夜勤 -- STICK-BODY version.

One head rig (face(), copied unchanged from make_face_original.py) + one stick-body rig (body()).
Every figure = body(pose) + face(expression).  Both scene.svg and poses.svg are built from these two rigs.
"""
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))

INK = '#1B1411'
WHITE = '#FFF8EC'
COFFEE = '#241A15'
AMBER = '#F2C46D'
MINT = '#9FCFB8'
MOUTH_DARK = '#3A1E18'

LOU = dict(skin='#D9A383', stubble='#C08E70', jacket='#5E7F73')
DOT = dict(skin='#7B4F3A', cardigan='#E9DCC6', hair='#3A1C1E')


def f(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def pts(points):
    return ' '.join('%s,%s' % (f(x), f(y)) for x, y in points)


# ---------------------------------------------------------------- geometry
def head_points(cx, cy, rx, ryt, ryb, puff=0.0, n=160):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        ry = ryb if s > 0 else ryt
        bulge = 1.0
        if puff and s > 0:
            # bulge at the lower sides (peaks ~40 deg below the equator)
            bulge += puff * (math.sin(2 * t) ** 2) * (1 if s > 0 else 0)
        out.append((cx + rx * c * bulge, cy + ry * s))
    return out


def smooth_path(p, closed=True):
    """Catmull-Rom -> cubic bezier."""
    n = len(p)
    d = 'M%s,%s' % (f(p[0][0]), f(p[0][1]))
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = p[(i - 1) % n] if closed or i > 0 else p[i]
        p1 = p[i]
        p2 = p[(i + 1) % n]
        p3 = p[(i + 2) % n] if closed or i + 2 < n else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += ' C%s,%s %s,%s %s,%s' % (f(c1[0]), f(c1[1]), f(c2[0]), f(c2[1]), f(p2[0]), f(p2[1]))
    return d + (' Z' if closed else '')


def bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t ** 2
        e = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return out


def taper(center, w0, w1=1.2):
    """Tapered brush stroke polygon along a centre line."""
    n = len(center)
    left, right = [], []
    for i, (x, y) in enumerate(center):
        a = center[max(i - 1, 0)]
        b = center[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        t = i / (n - 1)
        w = w0 + (w1 - w0) * (t ** 0.9)
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    poly = left + right[::-1]
    return 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in poly) + ' Z'


COWLICK = {
    # centre lines relative to the base point, unit = px at sheet scale (head W=300)
    'soft':    [(0, 0), (-3, -28), (16, -56), (26, -40)],
    'stiff':   [(0, 0), (1, -20), (-1, -38), (0, -56)],
    'hook':    [(0, 0), (6, -40), (-14, -58), (-28, -40)],
    'wilt':    [(0, 0), (6, -20), (26, -24), (44, -6)],
    'jaunty':  [(0, 0), (12, -34), (-20, -62), (-12, -40)],
    'flat':    [(0, 0), (8, -18), (32, -20), (50, -6)],
}


# ---------------------------------------------------------------- the rig
def face(uid, cx, cy, W=300, H=150, skin=LOU['skin'], stubble=LOU['stubble'], stubble_frac=0.35,
         flush=None, flush_frac=0.30,
         eye_w=104, eye_d=62, eye_top=0.30, eye_gap=20, eye_scale=1.0, eye_dy=0, rim=5,
         lid=(0.55, 0.55), lid_tilt=0.0, lid_w=6, low=(0.0, 0.0), low_curve=0.0,
         pupil_d=20, pupils=((0, 1), (0, 1)), ghosts=(),
         mouth='a', mouth_w=None, mouth_dx=-18, mouth_dy=0, mouth_turn=0,
         cowlick='soft', cowlick_tremble=False, cowlick_scale=1.0, hair=None, hair_color=None, hair_frac=0.17, ears=True, stubble_dots=True, emanata_sides=(-1, 1), bowl_tilt=0.0,
         jaw=0, puff=0.0, tilt=0.0, lift=0,
         sweat=None, emanata=False, gloom=False, mark_color=WHITE, gloom_color=MINT,
         outline=6, line=4):
    """Return an SVG <g> for one head. All face parts are parameters."""
    s = W / 300.0                      # line/feature scale relative to the sheet head
    rx, ryt, ryb = W / 2, H / 2, H / 2 + jaw
    top_y, bot_y = cy - ryt, cy + ryb
    neck = (cx, bot_y)
    out = []
    tr = []
    if lift:
        tr.append('translate(0,%s)' % f(-lift))
    if tilt:
        tr.append('rotate(%s %s %s)' % (f(tilt), f(neck[0]), f(neck[1])))
    out.append('<g id="%s"%s>' % (uid, (' transform="%s"' % ' '.join(tr)) if tr else ''))

    hp = head_points(cx, cy, rx, ryt, ryb, puff)
    hd = smooth_path(hp)
    out.append('<defs><clipPath id="%s-hc"><path d="%s"/></clipPath></defs>' % (uid, hd))

    # ---- ears (behind the head)
    if ears:
        for sg in (-1, 1):
            exx = cx + sg * (rx - 6 * s)
            eyy = cy + 4 * s
            out.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/>'
                       % (f(exx + sg * 8 * s), f(eyy), f(18 * s), f(24 * s), skin, INK, f(outline)))
            out.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                       % (f(exx + sg * 6 * s), f(eyy - 10 * s), f(exx + sg * 20 * s), f(eyy), f(exx + sg * 6 * s), f(eyy + 10 * s), INK, f(line * .8)))
    # ---- hair behind the head (bun)
    if hair == 'bun':
        bx, by, br = cx + 34 * s, top_y - 22 * s, 44 * s
        hc = hair_color or DOT['hair']
        # messy flicks out of the bun
        # a pencil stuck through the bun (night-shift paperwork)
        pa, pb = (bx - br * 1.5, by + br * .55), (bx + br * 1.45, by - br * .75)
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                   % (f(pa[0]), f(pa[1]), f(pb[0]), f(pb[1]), INK, f(16 * s)))
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#E0A23A" stroke-width="%s" stroke-linecap="butt"/>'
                   % (f(pa[0] + 8 * s), f(pa[1] - 3.5 * s), f(pb[0]), f(pb[1]), f(8 * s)))
        out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>'
                   % (f(bx), f(by), f(br), hc, INK, f(outline)))
        out.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.7"/>'
                   % (f(bx - br * .5), f(by - br * .1), f(bx), f(by - br * .7), f(bx + br * .55), f(by + br * .05), INK, f(line * .8)))
        # one loose strand standing straight up (same brush as Lou's cowlick)
        base = (bx + 6 * s, by - br + 4)
        cl = [(base[0] + x * s * 1.15, base[1] + y * s * 1.15) for x, y in COWLICK['stiff']]
        out.append('<path d="%s" fill="%s"/>' % (taper(bezier(*cl), 8 * s, 1.2), INK))

    # ---- skin layer (re-used inside the lids)
    skin_layer = ['<path d="%s" fill="%s"/>' % (hd, skin)]
    if flush:
        fy = top_y + flush_frac * (ryt + ryb)
        skin_layer.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" clip-path="url(#%s-hc)"/>'
                          % (f(cx - rx * 1.2), f(top_y - 5), f(rx * 2.4), f(fy - top_y + 5), flush, uid))
    if stubble:
        sy = bot_y - stubble_frac * (ryt + ryb)
        # band top edge rises slightly toward the sides (jaw line)
        sp = 'M%s,%s Q%s,%s %s,%s L%s,%s L%s,%s Z' % (
            f(cx - rx * 1.2), f(sy - 10 * s), f(cx), f(sy + 12 * s), f(cx + rx * 1.2), f(sy - 10 * s),
            f(cx + rx * 1.2), f(bot_y + 20), f(cx - rx * 1.2), f(bot_y + 20))
        skin_layer.append('<path d="%s" fill="%s" clip-path="url(#%s-hc)"/>' % (sp, stubble, uid))
        if stubble_dots:
            dots = []
            step = 13 * s
            row = 0
            yy = sy + 2 * s
            while yy < bot_y:
                xx = cx - rx + (row % 2) * step / 2
                while xx < cx + rx:
                    # skip near the band top edge so the edge stays clean
                    edge = sy - 10 * s + (22 * s) * (1 - ((xx - cx) / (rx * 1.2)) ** 2)
                    if yy > edge + 5 * s:
                        j = ((int(xx * 7 + yy * 13) % 7) - 3) * 0.6 * s
                        dots.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(xx + j), f(yy - j * .5), f(1.9 * s)))
                    xx += step
                yy += step * 0.8
                row += 1
            skin_layer.append('<g fill="#A97A5D" clip-path="url(#%s-hc)">%s</g>' % (uid, ''.join(dots)))
    if hair == 'bun':
        hc = hair_color or DOT['hair']
        hy = top_y + hair_frac * (ryt + ryb)
        hpth = 'M%s,%s L%s,%s Q%s,%s %s,%s Q%s,%s %s,%s Z' % (
            f(cx - rx * 1.2), f(top_y - 10), f(cx + rx * 1.2), f(top_y - 10),
            f(cx + rx * 0.9), f(hy + 14 * s), f(cx + 10 * s), f(hy - 2 * s),
            f(cx - rx * 0.6), f(hy + 18 * s), f(cx - rx * 1.2), f(hy + 26 * s))
        skin_layer.append('<path d="%s" fill="%s" clip-path="url(#%s-hc)"/>' % (hpth, hc, uid))
        hline = 'M%s,%s Q%s,%s %s,%s Q%s,%s %s,%s' % (
            f(cx + rx * 1.0), f(hy - 8 * s), f(cx + rx * 0.9), f(hy + 14 * s), f(cx + 10 * s), f(hy - 2 * s),
            f(cx - rx * 0.6), f(hy + 18 * s), f(cx - rx * 1.05), f(hy + 24 * s))
        skin_layer.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" clip-path="url(#%s-hc)" stroke-linecap="round"/>'
                          % (hline, INK, f(line), uid))
    out.append('<g id="%s-skin">%s</g>' % (uid, ''.join(skin_layer)))
    out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>'
               % (hd, INK, f(outline)))

    # ---- cowlick (Lou)
    if cowlick and hair is None:
        base = (cx, top_y + 2)
        cl = [(base[0] + x * s * cowlick_scale, base[1] + y * s * cowlick_scale) for x, y in COWLICK[cowlick]]
        if cowlick_tremble:
            for dx, op in ((-9 * s, .3), (9 * s, .3)):
                c2 = [(x + dx, y) for x, y in cl]
                c2[0] = cl[0]
                out.append('<path d="%s" fill="%s" opacity="%s"/>' % (taper(bezier(*c2), 8 * s), INK, op))
        out.append('<path d="%s" fill="%s"/>' % (taper(bezier(*cl), 8 * s), INK))

    # ---- eyes
    ew, ed = eye_w * eye_scale, eye_d * eye_scale
    ey = top_y + eye_top * (2 * ryt) + eye_dy
    centers = [cx - (eye_gap / 2 + ew / 2), cx + (eye_gap / 2 + ew / 2)]
    pr = pupil_d / 2
    tan_t = math.tan(math.radians(lid_tilt))
    for i, ex in enumerate(centers):
        eid = '%s-e%d' % (uid, i)
        bowl = 'M%s,%s L%s,%s A%s,%s 0 0 1 %s,%s Z' % (
            f(ex - ew / 2), f(ey), f(ex + ew / 2), f(ey), f(ew / 2), f(ed), f(ex - ew / 2), f(ey))
        sign = 1 if i == 0 else -1           # inner side: +x for left eye, -x for right eye
        c_up = lid[i]
        y0 = ey + c_up * ed

        def lidy(x, y0=y0, sign=sign, ex=ex):
            return y0 + sign * tan_t * (x - ex)
        c_lo = low[i]
        yb = ey + ed - c_lo * ed

        def lowy(x, yb=yb, ex=ex):
            if c_lo <= 0:
                return 1e9
            k = 1 - ((x - ex) / (ew / 2)) ** 2
            return yb - low_curve * max(k, 0)

        out.append('<defs><clipPath id="%s-c"><path d="%s"/></clipPath></defs>' % (eid, bowl))
        # bowl_tilt > 0 lifts the inner end of the flat top ("uh-oh" brows)
        out.append('<g transform="rotate(%s %s %s)">' % (f(sign * -bowl_tilt), f(ex), f(ey + ed / 2)))
        out.append('<g clip-path="url(#%s-c)">' % eid)
        out.append('<path d="%s" fill="%s"/>' % (bowl, WHITE))

        def place(u, v, r):
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

        for (gi, gu, gv, gop) in ghosts:
            if gi == i:
                gx, gy = place(gu, gv, pr)
                out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" opacity="%s"/>' % (f(gx), f(gy), f(pr), INK, gop))
        pp = pupils[i]
        u, v = pp[0], pp[1]
        px, py = place(u, v, pr)
        if len(pp) > 2:
            py += pp[2]
        out.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (f(px), f(py), f(pr), INK))
        # upper lid: the head's own skin layer, masked
        if c_up > 0:
            xa, xb = ex - ew, ex + ew
            poly = [(xa, ey - 80), (xb, ey - 80), (xb, lidy(xb)), (xa, lidy(xa))]
            out.append('<defs><clipPath id="%s-u"><polygon points="%s"/></clipPath></defs>' % (eid, pts(poly)))
            out.append('<g clip-path="url(#%s-u)"><use href="#%s-skin"/></g>' % (eid, uid))
            if c_up < 0.999:
                out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                           % (f(xa), f(lidy(xa)), f(xb), f(lidy(xb)), INK, f(lid_w)))
        if c_lo > 0:
            xa, xb = ex - ew / 2 - 4, ex + ew / 2 + 4
            lp = 'M%s,%s L%s,%s Q%s,%s %s,%s L%s,%s Z' % (
                f(xa), f(ey + ed + 40), f(xa), f(yb), f(ex), f(yb - 2 * low_curve), f(xb), f(yb), f(xb), f(ey + ed + 40))
            out.append('<defs><clipPath id="%s-l"><path d="%s"/></clipPath></defs>' % (eid, lp))
            out.append('<g clip-path="url(#%s-l)"><use href="#%s-skin"/></g>' % (eid, uid))
            out.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                       % (f(xa), f(yb), f(ex), f(yb - 2 * low_curve), f(xb), f(yb), INK, f(line)))
        out.append('</g>')
        out.append('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>'
                   % (bowl, INK, f(rim)))
        out.append('</g>')

    # ---- mouth
    mouth_types = {'a': 46, 'b': 20, 'c': 120, 'd': 90, 'e': 50, 'f': 100, 'g': 38}
    mw = 0 if not mouth else (mouth_w if mouth_w is not None else mouth_types[mouth]) * s
    eye_bot = ey + ed
    mx = cx + mouth_dx * s
    my = (eye_bot + bot_y) / 2 + 2 * s + mouth_dy
    lw = 5 * s
    if mouth == 'a':
        out.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                   % (f(mx - mw / 2), f(my + mouth_turn), f(mx), f(my - mouth_turn), f(mx + mw / 2), f(my + mouth_turn), INK, f(lw)))
    elif mouth == 'b':
        out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"/>'
                   % (f(mx), f(my), f(mw / 2), MOUTH_DARK, INK, f(lw)))
    elif mouth == 'c':
        mh = 46 * s
        mid = '%s-m' % uid
        x0, y0 = mx - mw / 2, my - mh / 2
        out.append('<defs><clipPath id="%s"><rect x="%s" y="%s" width="%s" height="%s" rx="%s"/></clipPath></defs>'
                   % (mid, f(x0), f(y0), f(mw), f(mh), f(12 * s)))
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>' % (f(x0), f(y0), f(mw), f(mh), f(12 * s), MOUTH_DARK))
        out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" clip-path="url(#%s)"/>' % (f(x0), f(y0), f(mw), f(12 * s), WHITE, mid))
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>'
                   % (f(x0), f(y0 + 12 * s), f(x0 + mw), f(y0 + 12 * s), INK, f(3 * s), mid))
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="%s"/>'
                   % (f(x0), f(y0), f(mw), f(mh), f(12 * s), INK, f(lw)))
    elif mouth in ('d', 'g'):
        humps = 3
        amp = (7 if mouth == 'd' else 3.2) * s
        n = 48
        p = []
        for k in range(n + 1):
            t = k / n
            p.append((mx - mw / 2 + mw * t, my + amp * math.sin(t * humps * 2 * math.pi)))
        out.append('<path d="M%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>'
                   % (' L'.join('%s,%s' % (f(x), f(y)) for x, y in p), INK, f(lw if mouth == 'd' else lw * .9)))
    elif mouth == 'e':
        x0, x1 = mx - mw / 2, mx + mw / 2
        out.append('<path d="M%s,%s L%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                   % (f(x0), f(my + 5 * s), f(x1 - 18 * s), f(my - 1 * s), f(x1 + 4 * s), f(my - 3 * s), f(x1 + 8 * s), f(my - 24 * s), INK, f(lw * 1.15)))
        out.append('<path d="M%s,%s q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                   % (f(x1 + 18 * s), f(my - 31 * s), f(5 * s), f(5 * s), f(3 * s), f(15 * s), INK, f(line * .9)))
    elif mouth == 'f':
        mh = 34 * s
        mid = '%s-m' % uid
        x0, y0 = mx - mw / 2, my - mh / 2
        out.append('<defs><clipPath id="%s"><rect x="%s" y="%s" width="%s" height="%s" rx="%s"/></clipPath></defs>'
                   % (mid, f(x0), f(y0), f(mw), f(mh), f(7 * s)))
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>' % (f(x0), f(y0), f(mw), f(mh), f(7 * s), WHITE))
        out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>'
                   % (f(x0), f(my), f(x0 + mw), f(my), INK, f(4 * s), mid))
        for k in range(1, 5):
            xx = x0 + mw * k / 5
            out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" clip-path="url(#%s)"/>'
                       % (f(xx), f(y0), f(xx), f(y0 + mh), INK, f(3 * s), mid))
        out.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="%s"/>'
                   % (f(x0), f(y0), f(mw), f(mh), f(7 * s), INK, f(lw)))

    # ---- marks
    if sweat:
        side = -1 if sweat == 'left' else 1
        ang = math.radians(180 + 28 if side < 0 else -28)
        sx = cx + rx * math.cos(ang) * 1.0
        sy = cy + ryt * math.sin(ang) * 1.0
        sz = 26 * s
        # trail running down the rim toward the bead
        a0 = ang + (-side) * math.radians(-26)
        tx, ty = cx + (rx + 2) * math.cos(a0), cy + (ryt + 2) * math.sin(a0)
        out.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                   % (f(tx), f(ty), f((tx + sx) / 2 + side * 8 * s), f((ty + sy) / 2), f(sx + side * 2 * s), f(sy - sz * .55),
                      WHITE, f(3.5 * s)))
        out.append('<path d="M%s,%s C%s,%s %s,%s %s,%s C%s,%s %s,%s %s,%s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>'
                   % (f(sx), f(sy - sz / 2), f(sx + sz * .38), f(sy - sz * .05), f(sx + sz * .38), f(sy + sz / 2), f(sx), f(sy + sz / 2),
                      f(sx - sz * .38), f(sy + sz / 2), f(sx - sz * .38), f(sy - sz * .05), f(sx), f(sy - sz / 2), WHITE, INK, f(3.5 * s)))
    if emanata:
        for side in emanata_sides:
            for ang in (-28, 0, 28):
                a = math.radians(ang)
                r0, r1 = 14 * s, 42 * s
                x0 = cx + side * (rx + r0 * math.cos(a))
                y0 = cy - 10 * s + r0 * math.sin(a) * 1.0 + ang * 1.4 * s
                x1 = cx + side * (rx + r1 * math.cos(a))
                y1 = cy - 10 * s + r1 * math.sin(a) * 1.0 + ang * 1.4 * s + (r1 - r0) * math.sin(a) * .6
                out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
                           % (f(x0), f(y0), f(x1), f(y1), mark_color, f(5 * s)))
    if gloom:
        for k in range(4):
            gx = cx - 54 * s + k * 36 * s
            out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="0.55"/>'
                       % (f(gx), f(top_y - 92 * s + (k % 2) * 10 * s), f(gx), f(top_y - 34 * s + (k % 2) * 6 * s), gloom_color, f(5 * s)))
    out.append('</g>')
    return '\n'.join(out)


# ---------------------------------------------------------------- expression sheet
EXPRESSIONS = [
    # 1 neutral
    dict(lid=(0.55, 0.55), pupils=((0, 1), (0, 1)), mouth='a', cowlick='soft'),
    # 2 surprised
    dict(lid=(0, 0), eye_scale=1.18, eye_gap=16, eye_dy=-12, pupil_d=12, pupils=((0, .5), (0, .5)), cowlick='stiff',
         mouth='c', mouth_dy=-8, jaw=24, lift=12, emanata=True, mouth_dx=0),
    # 3 angry
    dict(lid=(0.45, 0.45), lid_tilt=22, low=(0.30, 0.30), low_curve=0, pupils=((0, .55), (0, .55)), puff=0.08,
         flush='#D98C70', mouth='f', mouth_dx=-6, cowlick='hook'),
    # 4 smug
    dict(lid=(0.70, 0.70), low=(0.08, 0.08), low_curve=0, pupils=((0.3, 1, 5), (0.3, 1, 5)), tilt=-5, mouth='e', mouth_w=70,
         mouth_dx=14, cowlick='jaunty'),
    # 5 panic
    dict(lid=(0.05, 0.20), pupil_d=14, pupils=((-1, .45), (1, .45)), ghosts=((0, 0.2, .5, .4), (1, -0.2, .5, .4)),
         mouth='d', mouth_w=96, mouth_dx=-4, sweat='left', cowlick='stiff', cowlick_tremble=True, bowl_tilt=7),
    # 6 exasperated side-eye
    dict(lid=(0.68, 0.68), pupils=((1, .5), (1, .5)), mouth='a', mouth_dx=-30, mouth_turn=4,
         cowlick='wilt', gloom=True),
]
# ---------------------------------------------------------------- scene
def rope(points, w=7):
    d = 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in points)
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="%s" fill="none" stroke="#D8C49A" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>'
            % (d, INK, f(w + 5), d, f(w)))


def limb(points, w, fill, outline=6):
    d = 'M' + ' L'.join('%s,%s' % (f(x), f(y)) for x, y in points)
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"/>'
            % (d, INK, f(w + 2 * outline), d, fill, f(w)))



# =====================================================================
#  STICK-BODY RIG (new).  Every frame = body(pose) + face(expression).
#  The head code above is copied unchanged from make_face_original.py.
#  Line language = the head's: uniform INK casing over a flat colour core
#  (the file's own cased limb()), round caps and round joins everywhere.
# =====================================================================
PEG = '#8A5A3A'
BRASS = '#B8893A'
STAR = '#FFE7A8'
CREAM = '#E9DCC6'
HANDLE = '#A9773F'
BRISTLE = '#D9B25E'


def shade(c, k):
    """darken a hex colour by fraction k (far limbs: k=0.12)"""
    c = c.lstrip('#')
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return '#%02X%02X%02X' % tuple(max(0, int(round(v * (1 - k)))) for v in (r, g, b))


def ang(p, q):
    return math.atan2(q[1] - p[1], q[0] - p[0])


def ik(root, target, l1, l2, bend=1, straight=False, min_bend=7):
    """Two-bone IK. bend=+1/-1 picks the side of the middle joint.
    Unless `straight`, the joint keeps at least `min_bend` degrees so it stays readable."""
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
    return mid, end


def fk(root, a1, l1, a2, l2):
    """angles in degrees from straight down, + toward screen right; a2 is relative to a1"""
    t1 = math.radians(a1)
    mid = (root[0] + l1 * math.sin(t1), root[1] + l1 * math.cos(t1))
    t2 = math.radians(a1 + a2)
    end = (mid[0] + l2 * math.sin(t2), mid[1] + l2 * math.cos(t2))
    return mid, end


def _caps(points, radii):
    out = []
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        r0, r1 = radii[i], radii[i + 1]
        L = math.hypot(x1 - x0, y1 - y0) or 1e-6
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        out.append('<polygon points="%s"/>' % pts([(x0 + nx * r0, y0 + ny * r0), (x1 + nx * r1, y1 + ny * r1),
                                                   (x1 - nx * r1, y1 - ny * r1), (x0 - nx * r0, y0 - ny * r0)]))
    for (x, y), r in zip(points, radii):
        out.append('<circle cx="%s" cy="%s" r="%s"/>' % (f(x), f(y), f(r)))
    return ''.join(out)


def sticks(items):
    """items: list of (points, core, w0, w1, cas0, cas1).  All INK casings first, then all cores,
    so strokes that meet (neck->spine) join seamlessly.  Round caps + round joins."""
    cas, core = [], []
    for (p, col, w0, w1, c0, c1) in items:
        cum = [0.0]
        for i in range(1, len(p)):
            cum.append(cum[-1] + math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]))
        T = cum[-1] or 1.0
        w = [w0 + (w1 - w0) * c / T for c in cum]
        cs = [c0 + (c1 - c0) * c / T for c in cum]
        cas.append(_caps(p, [a / 2 + b for a, b in zip(w, cs)]))
        core.append('<g fill="%s">%s</g>' % (col, _caps(p, [a / 2 for a in w])))
    return '<g fill="%s">%s</g>%s' % (INK, ''.join(cas), ''.join(core))


def qbez(p0, c, p1, n=14):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in [i / n for i in range(n + 1)]]


def point_at(poly, dist):
    acc = 0.0
    for i in range(1, len(poly)):
        seg = math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1])
        if acc + seg >= dist:
            t = (dist - acc) / (seg or 1)
            return (poly[i - 1][0] + (poly[i][0] - poly[i - 1][0]) * t, poly[i - 1][1] + (poly[i][1] - poly[i - 1][1]) * t)
        acc += seg
    return poly[-1]


# ---------------------------------------------------------------- hands, feet
def mitten(wrist, a, skin, L=48, Wd=30, thumb_side=1, mode='grip', sw=5, pole=None):
    """Mitten paddle.  Returns (paddle, thumb): the paddle goes behind the gripped object,
    the thumb nub is drawn in front of it.
    mode 'grip' + pole angle: a fist wrapped across the pole (paddle perpendicular to it,
    centred on the grip point); 'rest': paddle continues the forearm; 'open': splayed thumb."""
    if mode == 'grip' and pole is not None:
        c1 = pole + math.pi / 2
        if math.cos(c1 - a) < 0:          # point the fist away from the elbow
            c1 += math.pi
        deg = math.degrees(c1)
        g = '<g transform="translate(%s %s) rotate(%s)">' % (f(wrist[0]), f(wrist[1]), f(deg))
        paddle = g + '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/></g>' % (
            f(-L * 0.42), f(-Wd / 2), f(L), f(Wd), f(Wd / 2), skin, INK, f(sw))
        ts = thumb_side
        thumb = g + ('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/>'
                     '<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round"/></g>') % (
            f(-L * 0.10), f(ts * Wd * 0.20), f(L * 0.24), f(Wd * 0.30), skin, INK, f(sw - 1),
            f(L * 0.22), f(-Wd * 0.22), f(L * 0.30), f(0), f(L * 0.22), f(Wd * 0.22), INK)
        return paddle, thumb
    deg = math.degrees(a)
    g = '<g transform="translate(%s %s) rotate(%s)">' % (f(wrist[0]), f(wrist[1]), f(deg))
    paddle = g + '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/></g>' % (
        f(-8), f(-Wd / 2), f(L), f(Wd), f(Wd / 2), skin, INK, f(sw))
    if mode == 'open':      # splayed thumb (gesture beat)
        thumb = g + '<g transform="translate(%s %s) rotate(%s)"><rect x="-4" y="-7" width="%s" height="14" rx="7" fill="%s" stroke="%s" stroke-width="%s"/></g></g>' % (
            f(L * 0.18), f(thumb_side * Wd * 0.35), f(thumb_side * 55), f(L * 0.42), skin, INK, f(sw - 1))
    else:
        thumb = g + '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" stroke="%s" stroke-width="%s"/></g>' % (
            f(L * 0.40), f(thumb_side * Wd * 0.30), f(L * 0.22), f(Wd * 0.27), skin, INK, f(sw - 1))
    return paddle, thumb


def shoe(ankle, dirx, color, L=72, H=30, rot=0, sw=6, sole='#4A3328'):
    """Slip-on wedge with a flat sole at ankle.y + H (when rot=0)."""
    def P(x, y):
        return '%s,%s' % (f(x * L), f(y * H))
    d = ('M%s C%s %s %s L%s C%s %s %s C%s %s %s L%s C%s %s %s Z' % (
        P(-0.30, 0.22), P(-0.36, 0.62), P(-0.34, 1.0), P(-0.22, 1.0), P(0.60, 1.0),
        P(0.76, 1.0), P(0.78, 0.50), P(0.56, 0.40), P(0.40, 0.30), P(0.22, 0.12), P(0.10, -0.04),
        P(-0.14, -0.10), P(-0.24, -0.08), P(-0.30, 0.04), P(-0.30, 0.22)))
    w = ('M%s L%s L%s Q%s %s Z' % (P(-0.33, 0.70), P(-0.22, 1.0), P(0.60, 1.0), P(0.20, 0.84), P(-0.33, 0.70)))
    return ('<g transform="translate(%s %s) scale(%s 1) rotate(%s)">'
            '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>'
            '<path d="%s" fill="%s"/>'
            '<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round"/></g>'
            % (f(ankle[0]), f(ankle[1]), dirx, f(rot), d, color, INK, f(sw), w, sole, d, INK, f(sw)))


# ---------------------------------------------------------------- the body builder
def body(N, pose, C):
    """N = the head rig's own neck/tilt pivot in world coords (cx, cy + H/2 + jaw).
    pose: lift, neck(dx,len), hip(x,y), curve(px bow of the spine), arms{far,near}, legs{far,near}.
    C: character constants (lengths in px, colours).  Returns layers + joints."""
    lift = pose.get('lift', 0)
    ndx, nlen = pose.get('neck', (0, C['neck']))
    B = (N[0] + ndx, N[1] + nlen)                          # visible neck base
    top = (N[0], N[1] - lift - C.get('hide', 12))           # hidden 12 px inside the head
    hip = pose['hip']
    mid = ((B[0] + hip[0]) / 2 + pose.get('curve', 0), (B[1] + hip[1]) / 2)
    spine = qbez(B, mid, hip)
    S = point_at(spine, C['sh_drop'])                      # single shoulder point
    L = {}
    J = dict(B=B, S=S, hip=hip, top=top, spine=spine)
    # spine + neck as one continuous cased stroke (neck core = skin, spine core = garment)
    neck_pts = [top, ((top[0] + B[0]) / 2, (top[1] + B[1]) / 2), B]
    L['spine'] = sticks([(neck_pts, C['skin'], 8, 8, 5, 5), (spine, C['spine'], 8, 8, 5, 5)])
    # arms
    for side in ('far', 'near'):
        a = pose['arms'][side]
        if 'hand' in a:
            el, wr = ik(S, a['hand'], C['upper'], C['fore'], a.get('bend', 1), a.get('straight', False))
        else:
            el, wr = fk(S, a['a'], C['upper'], a['b'], C['fore'])
        core = C['arm'] if side == 'near' else shade(C['arm'], 0.12)
        stroke = sticks([([S, el, wr], core, 9, 5, 5, 4)])
        fa = ang(el, wr) + math.radians(a.get('wrist', 0))
        pad, th = mitten(wr, fa, C['hand'], L=C['mit_L'], Wd=C['mit_W'], thumb_side=a.get('thumb', 1),
                         mode=a.get('mode', 'grip' if 'pole' in a else 'rest'), pole=a.get('pole'))
        L[side + '_arm'] = stroke
        L[side + '_hand'] = pad
        L[side + '_thumb'] = th
        J[side + '_elbow'], J[side + '_wrist'] = el, wr
    # legs
    for side in ('far', 'near'):
        g = pose['legs'][side]
        if 'ankle' in g:
            kn, an = ik(hip, g['ankle'], C['thigh'], C['shin'], g.get('bend', 1), g.get('straight', False))
        else:
            kn, an = fk(hip, g['a'], C['thigh'], g['b'], C['shin'])
        core = C['leg'] if side == 'near' else shade(C['leg'], 0.12)
        L[side + '_leg'] = (sticks([([hip, kn, an], core, 9, 6, 5, 4)]) +
                            shoe(an, g.get('foot', -1), C['shoe'] if side == 'near' else shade(C['shoe'], 0.12),
                                 L=C['shoe_L'], H=C['shoe_H'], rot=g.get('rot', 0)))
        J[side + '_knee'], J[side + '_ankle'] = kn, an
    return L, J


def cast_shadow(cx, y, rx, ry=None, op=0.55):
    return '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#0E0907" opacity="%s"/>' % (f(cx), f(y), f(rx), f(ry or rx * 0.16), op)


# ---------------------------------------------------------------- costume props (head treatment: flat fill + INK)
def collar_v(B, a=0.0, s=1.0, jacket=LOU['jacket']):
    """Lou's work-jacket collar V hung at the neck base, about 62 px wide (s=1)."""
    def T(x, y):
        c, sn = math.cos(a), math.sin(a)
        return (B[0] + (x * c - y * sn) * s, B[1] + (x * sn + y * c) * s)
    o = []
    band = [T(-31, 2), T(-24, -10), T(0, -14), T(24, -10), T(31, 2)]
    o.append('<path d="M%s Q%s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (
        pts([band[0]]), pts([band[1]]), pts([band[2]]), pts([band[3]]), pts([band[4]]), shade(jacket, 0.12), INK))
    o.append('<polygon points="%s" fill="#3A2A22" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (
        pts([T(-16, -3), T(0, 30), T(16, -3)]), INK))
    for sg in (-1, 1):
        o.append('<polygon points="%s" fill="#6F9284" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (
            pts([T(sg * 15, -5), T(sg * 1, 34), T(sg * 16, 30), T(sg * 32, -1)]), INK))
    return ''.join(o)


def rag(hip, side=1, swing=0.0, s=1.0):
    """Cream dust rag tucked at the hip point; `swing` (px) is its lagging flap."""
    x0, y0 = hip
    sx = side * s
    p0 = (x0 + sx * 2, y0 - 8 * s)
    p1 = (x0 + sx * 34, y0 - 4 * s)
    p2 = (x0 + sx * 44 + swing, y0 + 76 * s)
    p3 = (x0 + sx * 10 + swing * 0.7, y0 + 70 * s)
    m = ((p2[0] + p3[0]) / 2 + sx * 2, (p2[1] + p3[1]) / 2 + 12 * s)
    d = 'M%s L%s Q%s %s Q%s %s Q%s %s Z' % (
        pts([p0]), pts([p1]), pts([((p1[0] + p2[0]) / 2 + sx * 6, (p1[1] + p2[1]) / 2)]), pts([p2]),
        pts([m]), pts([p3]), pts([((p0[0] + p3[0]) / 2 - sx * 4, (p0[1] + p3[1]) / 2)]), pts([p0]))
    folds = '<path d="M%s Q%s %s" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round" opacity="0.55"/>' % (
        pts([(x0 + sx * 18, y0 + 2 * s)]), pts([(x0 + sx * 20 + swing * .4, y0 + 34 * s)]),
        pts([(x0 + sx * 24 + swing * 0.8, y0 + 64 * s)]), INK)
    return '<path d="%s" fill="%s" stroke="%s" stroke-width="5" stroke-linejoin="round"/>%s' % (d, CREAM, INK, folds)


def lanyard(B, badge, s=1.0):
    """Dot's mint lanyard as a V from the neck to a small blank badge on the spine."""
    o = ['<path d="M%s L%s L%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>' % (
        pts([(B[0] - 20 * s, B[1] - 4)]), pts([(badge[0], badge[1] - 22 * s)]), pts([(B[0] + 20 * s, B[1] - 4)]), INK, f(11 * s)),
        '<path d="M%s L%s L%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>' % (
        pts([(B[0] - 20 * s, B[1] - 4)]), pts([(badge[0], badge[1] - 22 * s)]), pts([(B[0] + 20 * s, B[1] - 4)]), MINT, f(5 * s))]
    bx, by = badge
    o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="4" transform="rotate(-8 %s %s)"/>' % (
        f(bx - 22 * s), f(by - 22 * s), f(44 * s), f(54 * s), f(6 * s), WHITE, INK, f(bx), f(by)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" transform="rotate(-8 %s %s)"/>' % (
        f(bx - 16 * s), f(by - 14 * s), f(32 * s), f(12 * s), MINT, f(bx), f(by)))
    o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" transform="rotate(-8 %s %s)"/>' % (
        f(bx - 6 * s), f(by + 14 * s), f(7 * s), '#7B4F3A', f(bx), f(by)))
    return ''.join(o)


# ---------------------------------------------------------------- broom (hand prop)
def broom(base, tip, fan_len=120, fan_w=150, floor=None, skew=0.0, s=1.0):
    """Returns (fan, handle).  base = where the handle meets the bristles.
    On the floor the bristle edge is flat on the floor line and splays by `skew`."""
    a = ang(base, tip)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    hw = 17 * s
    tl = (base[0] + nx * hw, base[1] + ny * hw)
    tr = (base[0] - nx * hw, base[1] - ny * hw)
    bc = (base[0] - ux * fan_len, base[1] - uy * fan_len)
    if floor is not None:
        bc = (bc[0] + skew, floor)
        bl, br = (bc[0] + fan_w / 2, floor), (bc[0] - fan_w / 2, floor)
        if tl[0] < tr[0]:
            bl, br = br, bl
    else:
        bl = (bc[0] + nx * fan_w / 2, bc[1] + ny * fan_w / 2)
        br = (bc[0] - nx * fan_w / 2, bc[1] - ny * fan_w / 2)
    def mix(p, q, t, push=0.0):
        return (p[0] + (q[0] - p[0]) * t + nx * push, p[1] + (q[1] - p[1]) * t + ny * push)
    c1 = mix(tl, bl, 0.45, 14 * s)
    c2 = mix(tr, br, 0.45, -14 * s)
    if floor is not None:
        bottom = 'L%s' % pts([br])
    else:
        bottom = 'Q%s %s' % (pts([(bc[0] - ux * 14 * s, bc[1] - uy * 14 * s)]), pts([br]))
    fan = ['<path d="M%s Q%s %s %s Q%s %s Z" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
        pts([tl]), pts([c1]), pts([bl]), bottom, pts([c2]), pts([tr]), BRISTLE, INK, f(6 * s))]
    for t in (0.22, 0.45, 0.68):
        p = mix(tl, tr, t)
        q = mix(bl, br, t)
        q = (q[0] + (p[0] - q[0]) * 0.08, q[1] + (p[1] - q[1]) * 0.08)
        p = (p[0] - ux * 18 * s, p[1] - uy * 18 * s)
        fan.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#A9823A" stroke-width="%s" stroke-linecap="round"/>' % (
            f(p[0]), f(p[1]), f(q[0]), f(q[1]), f(4 * s)))
    # binding band
    b0 = (base[0] - ux * 6 * s + nx * 20 * s, base[1] - uy * 6 * s + ny * 20 * s)
    b1 = (base[0] - ux * 6 * s - nx * 20 * s, base[1] - uy * 6 * s - ny * 20 * s)
    fan.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
        f(b0[0]), f(b0[1]), f(b1[0]), f(b1[1]), INK, f(20 * s)))
    fan.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#8E2A35" stroke-width="%s" stroke-linecap="round"/>' % (
        f(b0[0]), f(b0[1]), f(b1[0]), f(b1[1]), f(10 * s)))
    handle = handle_seg(base, tip, s)
    return ''.join(fan), handle


def handle_seg(p, q, s=1.0):
    return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>'
            '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"/>' % (
                f(p[0]), f(p[1]), f(q[0]), f(q[1]), INK, f(20 * s), f(p[0]), f(p[1]), f(q[0]), f(q[1]), HANDLE, f(10 * s)))


def on_line(p, q, y):
    t = (y - p[1]) / ((q[1] - p[1]) or 1e-6)
    return (p[0] + (q[0] - p[0]) * t, y)


def grip_seg(p, q, at, half=40, s=1.0):
    """short piece of handle redrawn over a mitten, exactly on the handle line"""
    a = ang(p, q)
    c, sn = math.cos(a), math.sin(a)
    return handle_seg((at[0] - c * half, at[1] - sn * half), (at[0] + c * half, at[1] + sn * half), s)


def rope_seg(p, q, at, half=40, w=7):
    a = ang(p, q)
    c, sn = math.cos(a), math.sin(a)
    return rope([(at[0] - c * half, at[1] - sn * half), (at[0] + c * half, at[1] + sn * half)], w)


# ---------------------------------------------------------------- marks
def star8(x, y, r=34, ri=8, fill=STAR):
    p = []
    for k in range(8):
        a = math.radians(k * 45 - 90)
        rr = r if k % 2 == 0 else ri
        p.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (pts(p), fill, INK)


def ting(x, y, r=40, glow=True):
    o = []
    if glow:
        o.append('<circle cx="%s" cy="%s" r="%s" fill="url(#tingglow)"/>' % (f(x), f(y), f(r * 1.9)))
    o.append(star8(x, y, r, r * 0.24))
    for k, a in enumerate((-78, -128, 178, 128)):
        t = math.radians(a)
        r0, r1 = r * 0.95, r * 1.45
        o.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (
            f(x + r0 * math.cos(t)), f(y + r0 * math.sin(t)), f(x + r1 * math.cos(t)), f(y + r1 * math.sin(t)), WHITE))
    return ''.join(o)


def arcs(c, radii, a0, a1, w=5, op=0.9, color=WHITE):
    """concentric motion arcs around pivot c, from angle a0 to a1 (degrees, screen)"""
    o = []
    for r in radii:
        p0 = (c[0] + r * math.cos(math.radians(a0)), c[1] + r * math.sin(math.radians(a0)))
        p1 = (c[0] + r * math.cos(math.radians(a1)), c[1] + r * math.sin(math.radians(a1)))
        sweep = 1 if a1 > a0 else 0
        large = 1 if abs(a1 - a0) > 180 else 0
        o.append('<path d="M%s A%s,%s 0 %d %d %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" opacity="%s"/>' % (
            pts([p0]), f(r), f(r), large, sweep, pts([p1]), color, f(w), op))
    return ''.join(o)


def puffs(x, y, s=1.0, side=1):
    o = []
    for (dx, dy, r, op) in ((0, 0, 16, .5), (side * 26, -10, 12, .42), (side * 46, -2, 9, .34), (-side * 20, -6, 10, .35)):
        o.append('<circle cx="%s" cy="%s" r="%s" fill="#CDB99A" opacity="%s"/>' % (f(x + dx * s), f(y + dy * s), f(r * s), op))
    return ''.join(o)


# ---------------------------------------------------------------- mook A: wooden training dummy (faceless)
def dummy_body(cx, top, w=140, h=300, uid='dm'):
    o = []
    x0 = cx - w / 2
    o.append('<defs><clipPath id="%s-c"><rect x="%s" y="%s" width="%s" height="%s" rx="%s"/></clipPath></defs>' % (
        uid, f(x0), f(top), f(w), f(h), f(w / 2)))
    o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="6"/>' % (
        f(x0), f(top), f(w), f(h), f(w / 2), PEG, INK))
    o.append('<g clip-path="url(#%s-c)">' % uid)
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#7A4D31"/>' % (f(cx + w * 0.18), f(top), f(w * 0.4), f(h)))
    for (gx, bend) in ((-0.22, -10), (0.06, 8), (0.30, -6)):
        o.append('<path d="M%s,%s Q%s,%s %s,%s" fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" opacity="0.5"/>' % (
            f(cx + gx * w), f(top + 0.16 * h), f(cx + gx * w + bend), f(top + 0.5 * h), f(cx + gx * w - bend * 0.3), f(top + 0.86 * h), INK))
    o.append('<rect x="%s" y="%s" width="%s" height="18" fill="#6E4630" stroke="%s" stroke-width="4"/>' % (
        f(x0 - 4), f(top + 0.72 * h), f(w + 8), INK))
    o.append('</g>')
    o.append('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="none" stroke="%s" stroke-width="6"/>' % (
        f(x0), f(top), f(w), f(h), f(w / 2), INK))
    return ''.join(o)


def peg(p, q):
    return limb([p, q], 16, PEG, outline=5)


def bolt(x, y, r=10):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="4"/>' % (f(x), f(y), f(r), BRASS, INK)


def brass_ring(x, y, r=28):
    return ('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="14"/>'
            '<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="8"/>' % (f(x), f(y), f(r), INK, f(x), f(y), f(r), BRASS))


def pulley(x, y, r=13):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="5"/>' % (f(x), f(y), f(r), BRASS, INK)


# ---------------------------------------------------------------- characters
def lou_C(HU=400.0):
    k = HU / 400.0
    return dict(neck=20 * k, sh_drop=0.15 * HU, upper=0.57 * HU, fore=0.55 * HU, thigh=0.605 * HU, shin=0.59 * HU,
                skin=LOU['skin'], hand=LOU['skin'], spine=LOU['jacket'], arm=LOU['jacket'], leg='#2F3B38',
                shoe='#2A1D18', shoe_L=0.19 * HU, shoe_H=30 * k, mit_L=0.13 * HU, mit_W=34 * k)


def dot_C(HU=280.0):
    return dict(neck=20, sh_drop=0.15 * HU, upper=0.57 * HU, fore=0.55 * HU, thigh=0.64 * HU, shin=0.62 * HU,
                skin=DOT['skin'], hand=DOT['skin'], spine=CREAM, arm=CREAM, leg='#3A1C1E',
                shoe='#141010', shoe_L=0.18 * HU, shoe_H=24, mit_L=0.17 * HU, mit_W=33)


LOU_EYES_400 = dict(eye_w=152, eye_d=86, eye_gap=24, pupil_d=24, lid_w=8, rim=6, outline=6)


# ---------------------------------------------------------------- head helper (same rig, scaled sizes)
def lou_head(uid, cx, cy, W, H, expr, eye_boost=1.0, **over):
    """face() with the expression-sheet parameters; absolute-px sizes scaled by W/300."""
    k = W / 300.0
    p = dict(expr)
    for key, base in (('eye_w', 104), ('eye_d', 62), ('eye_gap', 20), ('pupil_d', 20)):
        p[key] = p.get(key, base) * k * (eye_boost if key in ('eye_w', 'eye_d') else 1.0)
    for key in ('eye_dy', 'mouth_dy', 'jaw', 'lift'):
        if key in p:
            p[key] = p[key] * k
    p.update(over)
    return face(uid, cx, cy, W=W, H=H, **p)


def defs_common():
    return ('<defs>'
            '<radialGradient id="pool"><stop offset="0" stop-color="%s" stop-opacity="0.30"/>'
            '<stop offset="0.55" stop-color="%s" stop-opacity="0.16"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="lamp"><stop offset="0" stop-color="%s" stop-opacity="0.36"/>'
            '<stop offset="0.5" stop-color="%s" stop-opacity="0.2"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="vig" cx="50%%" cy="46%%" r="75%%"><stop offset="0.62" stop-color="#0E0907" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#0E0907" stop-opacity="0.72"/></radialGradient>'
            '<radialGradient id="pool2"><stop offset="0" stop-color="%s" stop-opacity="0.44"/>'
            '<stop offset="0.55" stop-color="%s" stop-opacity="0.30"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="tingglow"><stop offset="0" stop-color="#FFE7A8" stop-opacity="0.75"/>'
            '<stop offset="0.45" stop-color="#F2C46D" stop-opacity="0.35"/><stop offset="1" stop-color="#F2C46D" stop-opacity="0"/></radialGradient>'
            '</defs>' % ((AMBER,) * 9))


# ---------------------------------------------------------------- SCENE 1080x1920
def build_scene():
    CEIL, FLOOR, FL = 232, 1318, 1530
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
    # ---- moonlit shoji window (upper middle)
    wx, wy, ww, wh = 502, 286, 116, 156
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#7FAF9A"/>' % (wx, wy, ww, wh))
    for k in (1, 2):
        S.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#3A2620" stroke-width="6"/>' % (f(wx + ww * k / 3), wy, f(wx + ww * k / 3), wy + wh))
    for k in (1, 2):
        S.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="#3A2620" stroke-width="6"/>' % (wx, f(wy + wh * k / 3), wx + ww, f(wy + wh * k / 3)))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#3A2620" stroke-width="14"/>' % (wx, wy, ww, wh))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="4"/>' % (wx - 7, wy - 7, ww + 14, wh + 14, INK))
    # ---- floor
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#4A2E24"/>' % (FLOOR, 1920 - FLOOR))
    for y in (1352, 1394, 1446, 1508, 1590, 1700, 1840):
        S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#3A231C" stroke-width="3"/>' % (y, y))
    S.append('<polygon points="%s" fill="%s" opacity="0.36"/>' % (pts([(296, FLOOR + 4), (560, FLOOR + 4), (700, 1560), (250, 1560)]), MINT))
    # ---- light pools: lamp behind Dot, soft amber behind Lou (separates the cased sticks from the wall)
    S.append('<circle cx="812" cy="700" r="360" fill="url(#lamp)"/>')
    S.append('<ellipse cx="400" cy="980" rx="430" ry="640" fill="url(#pool2)"/>')
    # ---- witness: caretaker behind the sliding door, one heavy lid in the gap
    S.append('<rect x="-10" y="660" width="114" height="%d" fill="#3A2620" stroke="%s" stroke-width="6"/>' % (FLOOR - 34 - 660, INK))
    S.append('<rect x="50" y="680" width="46" height="%d" fill="#100A08"/>' % (FLOOR - 34 - 700))
    S.append('<defs><clipPath id="gap"><rect x="50" y="680" width="46" height="%d"/></clipPath></defs>' % (FLOOR - 34 - 700))
    S.append('<g clip-path="url(#gap)">')
    S.append(face('gramps', 34, 1040, W=170, H=96, skin='#B98B70', stubble=None, stubble_dots=False, ears=False, cowlick=None,
                  eye_w=48, eye_d=30, eye_top=0.32, eye_gap=16, lid=(0.66, 0.66), lid_tilt=-16, rim=4, lid_w=4,
                  pupil_d=13, pupils=((1, .5), (1, .5)), mouth=None, outline=5))
    S.append('<path d="M60,1012 q18,-8 34,-2 M62,1000 q16,-7 30,-2" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % INK)
    S.append('</g>')
    for yy in range(700, FLOOR - 40, 120):
        S.append('<line x1="0" y1="%d" x2="44" y2="%d" stroke="%s" stroke-width="4"/>' % (yy, yy, INK))
    S.append('<line x1="46" y1="660" x2="46" y2="%d" stroke="%s" stroke-width="6"/>' % (FLOOR - 34, INK))
    S.append('<line x1="96" y1="660" x2="96" y2="%d" stroke="%s" stroke-width="6"/>' % (FLOOR - 34, INK))

    # ---- mook 1: wall-post wooden dummy (faceless).  Its right peg arm was swinging at Lou's head.
    S.append('<rect x="103" y="%d" width="54" height="%d" fill="#5A3A28" stroke="%s" stroke-width="6"/>' % (CEIL - 6, FLOOR - CEIL - 28, INK))
    dcx, dtop = 130, 262
    S.append(peg((dcx - 62, dtop + 150), (dcx - 116, dtop + 112)))
    S.append(dummy_body(dcx, dtop, uid='d1'))
    pv = (dcx + 62, dtop + 183)                         # pivot bolt on the right side
    a_now, L_arm = -40.0, 125
    tipA = (pv[0] + L_arm * math.cos(math.radians(a_now)), pv[1] + L_arm * math.sin(math.radians(a_now)))
    contact = (pv[0] + 96 * math.cos(math.radians(a_now)), pv[1] + 96 * math.sin(math.radians(a_now)))
    a_rest = -72.0
    ring = (pv[0] + L_arm * math.cos(math.radians(a_rest)), pv[1] + L_arm * math.sin(math.radians(a_rest)))
    S.append(arcs(pv, (100, 120, 140), a_now + 5, a_now + 17))          # where it came from
    S.append(peg(pv, tipA))
    S.append(bolt(*pv))
    # ---- cord system: ring -> pulley A -> ceiling -> pulley B -> Dot's fists
    pA, pB = (ring[0], 252), (648, 252)
    hand_top, hand_low = 700, 1060
    cord_end = (656, 1100)
    def cord_x(y):
        return pB[0] + (cord_end[0] - pB[0]) * (y - pB[1]) / (cord_end[1] - pB[1])
    S.append(rope([(ring[0], ring[1] - 26), pA]))
    S.append(rope([pA, pB]))
    S.append(rope([pB, cord_end, (cord_end[0] + 4, cord_end[1] + 30)]))
    S.append('<path d="M%s l-12,40 l28,0 Z" fill="#8E2A35" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (
        pts([(cord_end[0] + 8, cord_end[1] + 26)]), INK))
    S.append(brass_ring(*ring))

    # ---- mook 2: already dropping on its own pulley cord right of the window (the next note)
    d2 = (744, 172)
    S.append(rope([(d2[0], 252), (d2[0], d2[1] + 4)]))
    S.append('<g transform="rotate(7 %s %s)">' % (f(d2[0]), f(d2[1])))
    S.append(peg((d2[0] - 60, d2[1] + 196), (d2[0] - 112, d2[1] + 226)))
    S.append(peg((d2[0] + 60, d2[1] + 196), (d2[0] + 110, d2[1] + 222)))
    S.append(dummy_body(d2[0], d2[1], uid='d2'))
    S.append('</g>')
    for (x0, y0, y1) in ((668, 250, 330), (826, 262, 350), (846, 300, 360)):
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="5" stroke-linecap="round" opacity="0.8"/>' % (x0, y0, x0, y1, WHITE))

    # ---- paper lantern (upper right)
    lx, ly = 898, 318
    S.append('<ellipse cx="%d" cy="%d" rx="56" ry="66" fill="%s" stroke="%s" stroke-width="6"/>' % (lx, ly, AMBER, INK))
    for k in (-32, 0, 32):
        S.append('<path d="M%d,%d Q%d,%d %d,%d" fill="none" stroke="#C9963E" stroke-width="3"/>' % (lx - 54, ly + k, lx, ly + k + 10, lx + 54, ly + k))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly - 72, INK))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly + 60, INK))

    # ================================================================ DOT (night-desk clerk)
    DC = dot_C(280.0)
    dcx_, dcy_, DW, DH = 822, 632, 280, 190
    dN = (dcx_, dcy_ + DH / 2)
    # hauling hand over hand: far mitten high on the cord, near arm long and low
    dpose = dict(neck=(2, 30), hip=(806, 1050), curve=-8,
                 arms=dict(far=dict(hand=(cord_x(hand_top), hand_top), bend=1, thumb=-1, pole=ang(pB, cord_end)),
                           near=dict(hand=(cord_x(hand_low), hand_low), bend=-1, thumb=-1, pole=ang(pB, cord_end))),
                 legs=dict(far=dict(ankle=(786, 1290), bend=-1), near=dict(ankle=(828, 1290), bend=-1)))
    DL, DJ = body(dN, dpose, DC)
    S.append(DL['far_arm'])
    S.append(DL['far_hand'])
    S.append(rope_seg(pB, cord_end, DJ['far_wrist'], 34))
    S.append(DL['spine'])
    S.append(face('dot', dcx_, dcy_, W=DW, H=DH, skin=DOT['skin'], stubble=None, stubble_dots=False,
                  eye_w=116, eye_d=74, eye_top=0.33, eye_gap=22, lid=(0.04, 0.10), pupil_d=15,
                  pupils=((-1, .45), (1, .45)), ghosts=((0, 0.2, .5, .35), (1, -0.2, .5, .35)),
                  mouth='d', mouth_w=92, mouth_dx=-6, cowlick=None, hair='bun', hair_frac=0.15,
                  sweat='right', emanata=True, emanata_sides=(1,), mark_color=WHITE, bowl_tilt=7))
    S.append(lanyard(DJ['B'], point_at(DJ['spine'], 128)))
    S.append(DL['near_arm'])
    S.append(DL['near_hand'])
    S.append(rope_seg(pB, cord_end, DJ['near_wrist'], 34))
    S.append(DL['far_thumb'])
    S.append(DL['near_thumb'])
    # ---- shoe cabinet (in front of her waist) with five paper cups, the fifth steaming
    ctop = 1052
    S.append('<rect x="704" y="%d" width="400" height="%d" fill="#4A2E24" stroke="%s" stroke-width="6"/>' % (ctop, FLOOR - ctop + 4, INK))
    S.append('<rect x="694" y="%d" width="420" height="24" fill="#6B4630" stroke="%s" stroke-width="5"/>' % (ctop - 18, INK))
    for k in range(3):
        S.append('<rect x="%d" y="%d" width="80" height="150" fill="#3E261E" stroke="%s" stroke-width="4"/>' % (724 + k * 92, ctop + 34, INK))
        S.append('<rect x="%d" y="%d" width="30" height="8" rx="4" fill="%s" stroke="%s" stroke-width="3"/>' % (749 + k * 92, ctop + 52, BRASS, INK))
    for k in range(5):
        cxp = 740 + k * 44
        y1 = ctop - 18
        cup = 'M%d,%d L%d,%d L%d,%d L%d,%d Z' % (cxp - 17, y1 - 48, cxp + 17, y1 - 48, cxp + 12, y1, cxp - 12, y1)
        S.append('<path d="%s" fill="%s" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (cup, WHITE if k == 4 else CREAM, INK))
        S.append('<rect x="%d" y="%d" width="30" height="12" fill="#8E2A35"/>' % (cxp - 15, y1 - 34))
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (cxp - 19, y1 - 48, cxp + 19, y1 - 48, INK))
    sx_ = 740 + 4 * 44
    S.append('<path d="M%d,%d q-10,-12 0,-24 q10,-12 0,-24 q-10,-12 0,-24" fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" opacity="0.75"/>' % (sx_, ctop - 74, WHITE))
    # pillar at the far right
    px0 = 986
    S.append('<rect x="%d" y="%d" width="120" height="%d" fill="#55141F" stroke="%s" stroke-width="6"/>' % (px0, CEIL - 10, FLOOR - CEIL + 20, INK))
    S.append('<rect x="%d" y="%d" width="14" height="%d" fill="#8A2E3A"/>' % (px0 + 16, CEIL, FLOOR - CEIL - 10))
    S.append('<rect x="%d" y="%d" width="130" height="40" fill="#3A2620" stroke="%s" stroke-width="5"/>' % (px0 - 10, FLOOR - 60, INK))

    # ================================================================ LOU (night sweeper)
    C = lou_C(400.0)
    hx, hy, W, H = 410, 558, 400, 200
    N = (hx, hy + H / 2)
    base, tip = (214, 1422), (contact[0], contact[1])
    def hl(y):
        return on_line(base, tip, y)
    # body turned 3/4 to screen-left, hunched forward (head 30 px ahead of the hips).
    # far (right) arm holds the broom low at mid-thigh and has just flicked it up over the
    # right shoulder; near (left) arm rests on the hip: he never even turned around.
    pose = dict(neck=(2, 32), hip=(440, 1030), curve=22,
                arms=dict(far=dict(hand=hl(1150), bend=-1, thumb=1, pole=ang(base, tip)),
                          near=dict(hand=(484, 1010), bend=1, thumb=-1, wrist=-28)),
                legs=dict(far=dict(ankle=(512, FL - C['shoe_H']), bend=-1, foot=-1),
                          near=dict(ankle=(352, FL - C['shoe_H']), bend=-1, foot=-1)))
    L, J = body(N, pose, C)
    S.append(cast_shadow(410, FL + 4, 170, 16, 0.42))
    S.append(L['far_leg'])
    S.append(L['far_arm'])
    S.append(L['far_hand'])
    S.append(L['spine'])
    S.append(rag(J['hip'], side=1, swing=12))
    fan, handle = broom(base, tip, fan_len=118, fan_w=150, floor=FL, skew=-14)
    S.append(fan)
    S.append(handle)
    S.append(lou_head('lou', hx, hy, W, H, EXPRESSIONS[5], eye_boost=1.06, lid_w=11, rim=6))
    a_sp = ang(J['spine'][0], J['spine'][2]) - math.pi / 2
    S.append(collar_v(J['B'], a_sp, 1.0))
    S.append(L['near_leg'])
    S.append(L['near_arm'])
    S.append(L['near_hand'])
    S.append(L['far_thumb'])
    S.append(L['near_thumb'])
    S.append(puffs(150, FL - 10, 1.0, -1))
    S.append(arcs(J['far_wrist'], (716, 748), math.degrees(ang(J['far_wrist'], tip)) + 1.2, math.degrees(ang(J['far_wrist'], tip)) + 4.6, w=5))
    S.append(ting(contact[0], contact[1], 50))

    # ---- ceiling band on top (keeps the top clean), rail, pulleys, lantern cord
    S.append('<rect x="0" y="0" width="1080" height="%d" fill="%s"/>' % (CEIL, COFFEE))
    S.append('<rect x="0" y="%d" width="1080" height="10" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (CEIL - 6, INK))
    S.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="#5A3A28" stroke-width="4"/>' % (lx, lx, ly - 72))
    for p in (pA, pB, (d2[0], 252)):
        S.append(pulley(*p))
    S.append('<rect width="1080" height="1920" fill="url(#vig)"/>')
    S.append('</svg>')
    return '\n'.join(S)


# ---------------------------------------------------------------- POSES SHEET 1080x1080
def build_poses():
    FLp = 980
    HU = 300.0
    W, H = 300, 150
    C = lou_C(HU)
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">', defs_common()]
    S.append('<rect width="1080" height="1080" fill="%s"/>' % COFFEE)
    for cx in (180, 540, 900):
        S.append('<ellipse cx="%d" cy="560" rx="200" ry="470" fill="url(#pool)"/>' % cx)
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#1C1410"/>' % (FLp, 1080 - FLp))
    S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#3A2A22" stroke-width="4"/>' % (FLp, FLp))
    sh = C['shoe_H']

    # ---------- (1) READY STANCE
    BS = 0.78                     # broom scale on the sheet (handle = 0.98 x standing height, as in the scene)
    cx, cy = 180, 249
    N = (cx, cy + H / 2)
    base = (70, 890)
    tip = (base[0] + 780 * math.sin(math.radians(17)), base[1] - 780 * math.cos(math.radians(17)))
    pose = dict(neck=(1, 26), hip=(204, 605), curve=14,
                arms=dict(far=dict(hand=on_line(base, tip, 548), bend=1, thumb=1, pole=ang(base, tip)),
                          near=dict(hand=on_line(base, tip, 716), bend=1, thumb=1, pole=ang(base, tip))),
                legs=dict(far=dict(ankle=(250, FLp - sh), bend=-1, foot=-1), near=dict(ankle=(128, FLp - sh), bend=-1, foot=-1)))
    L, J = body(N, pose, C)
    S.append(cast_shadow(186, FLp + 4, 150, 16, 0.6))
    S.append(L['far_leg'] + L['far_arm'] + L['far_hand'] + L['spine'])
    S.append(rag(J['hip'], 1, 0, 0.8))
    fan, handle = broom(base, tip, fan_len=92, fan_w=118, floor=FLp, skew=-6, s=BS)
    S.append(fan + handle)
    S.append(lou_head('p1', cx, cy, W, H, EXPRESSIONS[0], lid_w=9))
    S.append(collar_v(J['B'], ang(J['spine'][0], J['spine'][2]) - math.pi / 2, 0.8))
    S.append(L['near_leg'] + L['near_arm'] + L['near_hand'])
    S.append(grip_seg(base, tip, J['near_wrist'], 30, BS))
    S.append(L['far_thumb'] + L['near_thumb'])
    S.append(puffs(40, FLp - 8, 0.8, -1))

    # ---------- (2) SIGNATURE: BLIND BACK-FLICK
    cx, cy = 540, 249
    N = (cx, cy + H / 2)
    base, tip = (468, 892), (404, 118)
    hip = (566, 605)
    pose = dict(neck=(-2, 26), hip=hip, curve=-16,
                arms=dict(far=dict(hand=on_line(base, tip, 186), bend=1, thumb=-1, pole=ang(base, tip)),
                          near=dict(hand=(592, 596), bend=1, thumb=1, wrist=-28)),
                legs=dict(far=dict(ankle=(556, FLp - sh), bend=-1, foot=-1),
                          near=dict(a=26, b=116, foot=-1, rot=-70)))
    L, J = body(N, pose, C)
    S.append(cast_shadow(540, FLp + 4, 140, 16, 0.6))
    S.append(L['far_leg'] + L['far_arm'] + L['far_hand'] + L['spine'])
    S.append(rag(J['hip'], 1, 16, 0.8))
    fan, handle = broom(base, tip, fan_len=92, fan_w=118, floor=FLp, skew=-10, s=BS)
    S.append(fan + handle)
    S.append(lou_head('p2', cx, cy, W, H, dict(EXPRESSIONS[3], pupils=((0.9, 1, 5), (0.9, 1, 5)), mouth_dy=8), lid_w=9))
    S.append(collar_v(J['B'], ang(J['spine'][0], J['spine'][2]) - math.pi / 2, 0.8))
    S.append(L['near_leg'] + L['near_arm'] + L['near_hand'])
    S.append(L['far_thumb'] + L['near_thumb'])
    S.append(puffs(430, FLp - 8, 0.8, -1))
    S.append(ting(tip[0], tip[1], 32))

    # ---------- (3) BIG REACTION: SURPRISE JUMP
    cx, cy = 900, 194
    ex = dict(EXPRESSIONS[1], emanata_sides=(-1,))
    jaw, lift = ex['jaw'], ex['lift']
    N = (cx, cy + H / 2)
    up = 70
    bt, bb = (1046, 44), (1036, 822)            # broom flipping end over end beside him
    grip = on_line(bt, bb, 352)
    pose = dict(neck=(0, 24 + jaw), lift=lift, hip=(900, 572), curve=6,
                arms=dict(far=dict(hand=(764, 300), bend=1, thumb=1, mode='open'),
                          near=dict(hand=grip, bend=-1, thumb=-1, pole=ang(bt, bb))),
                legs=dict(far=dict(ankle=(858, FLp - up - sh), bend=-1, foot=-1, rot=16),
                          near=dict(ankle=(930, FLp - up - sh), bend=1, foot=1, rot=16)))
    L, J = body(N, pose, C)
    S.append(cast_shadow(900, FLp + 4, 100, 11, 0.4))
    mid = ((bt[0] + bb[0]) / 2, (bt[1] + bb[1] + 80) / 2)
    S.append(arcs(grip, (292, 316), -100, -86, w=5))
    fan, handle = broom(bb, bt, fan_len=92, fan_w=104, s=BS)
    for gdeg, gop in ((17, 0.16), (9, 0.30)):
        S.append('<g opacity="%s" transform="rotate(%s %s %s)">%s%s</g>' % (gop, gdeg, f(grip[0]), f(grip[1]), fan, handle))
    S.append(arcs(grip, (520, 548), 92, 104, w=5))
    S.append(L['far_leg'] + L['far_arm'] + L['far_hand'] + L['spine'])
    S.append(rag(J['hip'], -1, -14, 0.8))
    S.append(fan + handle)
    S.append(lou_head('p3', cx, cy, W, H, ex))
    S.append(collar_v(J['B'], 0, 0.8))
    S.append(L['near_leg'] + L['near_arm'] + L['near_hand'])
    S.append(grip_seg(bt, bb, J['near_wrist'], 30, BS))
    S.append(L['far_thumb'] + L['near_thumb'])
    S.append('</svg>')
    return '\n'.join(S)


if __name__ == '__main__':
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(build_scene())
    with open(os.path.join(HERE, 'poses.svg'), 'w') as fh:
        fh.write(build_poses())
    print('wrote scene.svg, poses.svg')
