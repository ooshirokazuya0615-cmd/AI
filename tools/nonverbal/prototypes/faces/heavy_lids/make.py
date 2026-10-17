#!/usr/bin/env python3
"""Heavy Lids / 半目の夜勤 -- one face rig, two images.

The rig (`face()`) draws a head from parameters:
  head    : horizontal ellipse, separate top/bottom radii (jaw drop), cheek puff, tilt, lift
  eyes    : two flat-topped semi-ellipse bowls (never touching)
  lids    : skin masks from above (coverage 0..1, tilt deg) and below (coverage, curve)
            -- the lids reuse the head's own skin/stubble/flush layer, so they always match
  pupils  : solid ink discs placed by (u, v) inside the visible part of each bowl, + ghost pupils
  mouth   : swap set a..g
  cowlick : one tapered brush flick, several poses (or a hair bun with one loose strand)
  marks   : sweat bead, surprise emanata, gloom lines
Both scene.svg and faces.svg are built only from this rig.
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


def collar(cx, top, bottom, jacket=LOU['jacket'], w=212, neck_w=44, neck_top=None, skin=LOU['skin']):
    o = []
    nt = neck_top if neck_top is not None else top - 50
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="5"/>'
             % (f(cx - neck_w / 2), f(nt), f(neck_w), f(top - nt + 14), skin, INK))
    hw = w / 2
    body = 'M%s,%s L%s,%s Q%s,%s %s,%s L%s,%s Q%s,%s %s,%s L%s,%s Z' % (
        f(cx - hw - 8), f(bottom + 10), f(cx - hw), f(top + 50), f(cx - hw + 4), f(top + 6), f(cx - 40), f(top),
        f(cx + 40), f(top), f(cx + hw - 4), f(top + 6), f(cx + hw), f(top + 50), f(cx + hw + 8), f(bottom + 10))
    o.append('<path d="%s" fill="%s" stroke="%s" stroke-width="6" stroke-linejoin="round"/>' % (body, jacket, INK))
    # tee in the V + collar flaps
    o.append('<path d="M%s,%s L%s,%s L%s,%s Z" fill="#3A2A22" stroke="%s" stroke-width="4" stroke-linejoin="round"/>'
             % (f(cx - 30), f(top + 1), f(cx), f(top + 46), f(cx + 30), f(top + 1), INK))
    for sgn in (-1, 1):
        o.append('<path d="M%s,%s L%s,%s L%s,%s L%s,%s Z" fill="#6F9284" stroke="%s" stroke-width="4" stroke-linejoin="round"/>'
                 % (f(cx + sgn * 30), f(top), f(cx + sgn * 2), f(top + 48), f(cx + sgn * 30), f(top + 40), f(cx + sgn * 58), f(top + 2), INK))
    return '\n'.join(o)


def build_faces():
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">',
         '<defs><radialGradient id="pool"><stop offset="0" stop-color="%s" stop-opacity="0.25"/>'
         '<stop offset="0.55" stop-color="%s" stop-opacity="0.16"/><stop offset="1" stop-color="%s" stop-opacity="0"/>'
         '</radialGradient></defs>' % (AMBER, AMBER, AMBER),
         '<rect width="1080" height="1080" fill="%s"/>' % COFFEE]
    for k, ex in enumerate(EXPRESSIONS):
        col, row = k % 3, k // 3
        cx, cy = col * 360 + 180, row * 540 + 260
        S.append('<g>')
        S.append('<ellipse cx="%d" cy="%d" rx="200" ry="230" fill="url(#pool)"/>' % (cx, cy - 20))
        S.append(collar(cx, cy + 98, row * 540 + 540, neck_top=cy + 40))
        S.append(face('f%d' % k, cx, cy, **ex))
        S.append('</g>')
    S.append('</svg>')
    return '\n'.join(S)


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


def build_scene():
    Wd, Hd = 1080, 1920
    CEIL, FLOOR = 232, 1318
    S = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">']
    S.append('''<defs>
<radialGradient id="lamp"><stop offset="0" stop-color="#F2C46D" stop-opacity="0.34"/>
 <stop offset="0.5" stop-color="#F2C46D" stop-opacity="0.2"/><stop offset="1" stop-color="#F2C46D" stop-opacity="0"/></radialGradient>
<radialGradient id="vig" cx="50%" cy="46%" r="75%">
 <stop offset="0.62" stop-color="#0E0907" stop-opacity="0"/>
 <stop offset="1" stop-color="#0E0907" stop-opacity="0.72"/>
</radialGradient>
</defs>''')
    S.append('<rect width="1080" height="1920" fill="%s"/>' % COFFEE)
    # ---- back wall: burgundy lacquer boards
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#6E1F2B"/>' % (CEIL, FLOOR - CEIL))
    for k, x in enumerate(range(0, 1080, 96)):
        if k % 2:
            S.append('<rect x="%d" y="%d" width="96" height="%d" fill="#641B27"/>' % (x, CEIL, FLOOR - CEIL))
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#4C1420" stroke-width="3"/>' % (x, CEIL, x, FLOOR))
    # wainscot rail + baseboard
    S.append('<rect x="0" y="1150" width="1080" height="14" fill="#4C1420"/>')
    S.append('<rect x="0" y="%d" width="1080" height="34" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (FLOOR - 34, INK))
    # ---- high window (upper left), shoji grid, moonlit
    wx, wy, ww, wh = 400, 300, 210, 170
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#7FAF9A"/>' % (wx, wy, ww, wh))
    for k in range(1, 3):
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#3A2620" stroke-width="6"/>' % (wx + ww * k // 3, wy, wx + ww * k // 3, wy + wh))
    S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#3A2620" stroke-width="6"/>' % (wx, wy + wh // 2, wx + ww, wy + wh // 2))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="#3A2620" stroke-width="14"/>' % (wx, wy, ww, wh))
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" stroke="%s" stroke-width="4"/>' % (wx - 7, wy - 7, ww + 14, wh + 14, INK))
    # ---- floor
    S.append('<rect x="0" y="%d" width="1080" height="%d" fill="#4A2E24"/>' % (FLOOR, Hd - FLOOR))
    for y in (1352, 1398, 1456, 1528):
        S.append('<line x1="0" y1="%d" x2="1080" y2="%d" stroke="#3A231C" stroke-width="3"/>' % (y, y))
    # moonlight on the floor behind Lou
    S.append('<polygon points="%s" fill="%s" opacity="0.30"/>' % (pts([(420, FLOOR + 4), (640, FLOOR + 4), (820, 1500), (560, 1500)]), MINT))
    # ---- lamp pool behind Dot
    S.append('<circle cx="800" cy="620" r="340" fill="url(#lamp)"/>')
    # ---- witness: the caretaker behind a sliding door, only one heavy lid in the gap
    S.append('<rect x="-10" y="660" width="114" height="%d" fill="#3A2620" stroke="%s" stroke-width="6"/>' % (FLOOR - 34 - 660, INK))
    S.append('<rect x="50" y="680" width="46" height="%d" fill="#100A08"/>' % (FLOOR - 34 - 700))
    S.append('<defs><clipPath id="gap"><rect x="50" y="680" width="46" height="%d"/></clipPath></defs>' % (FLOOR - 34 - 700))
    S.append('<g clip-path="url(#gap)">')
    S.append(face('gramps', 34, 1040, W=170, H=96, skin='#B98B70', stubble=None, stubble_dots=False, ears=False, cowlick=None,
                  eye_w=48, eye_d=30, eye_top=0.32, eye_gap=16, lid=(0.66, 0.66), lid_tilt=-16, rim=4, lid_w=4,
                  pupil_d=10, pupils=((1, .5), (1, .5)), mouth=None, outline=5))
    S.append('<path d="M60,1012 q18,-8 34,-2 M62,1000 q16,-7 30,-2" fill="none" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % INK)
    S.append('</g>')
    for yy in range(700, FLOOR - 40, 120):
        S.append('<line x1="0" y1="%d" x2="44" y2="%d" stroke="%s" stroke-width="4"/>' % (yy, yy, INK))
    S.append('<line x1="46" y1="660" x2="46" y2="%d" stroke="%s" stroke-width="6"/>' % (FLOOR - 34, INK))
    S.append('<line x1="96" y1="660" x2="96" y2="%d" stroke="%s" stroke-width="6"/>' % (FLOOR - 34, INK))
    # ---- dummy rig: wall post, dummy, brass ring, cord over pulleys
    post_x = 130
    S.append('<rect x="%d" y="%d" width="54" height="%d" fill="#5A3A28" stroke="%s" stroke-width="6"/>' % (post_x - 27, CEIL - 6, FLOOR - CEIL - 28, INK))
    dcx, dtop = 150, 300
    # static left peg arm
    S.append(limb([(dcx - 60, dtop + 120), (dcx - 120, dtop + 108)], 20, '#8A5A3A'))
    # swinging right arm: pivot, current angle up-right toward ring
    pvx, pvy = dcx + 58, dtop + 170
    ring = (318, 372)
    ang = math.atan2(ring[1] + 18 - pvy, ring[0] - 10 - pvx)
    L = 128
    tip = (pvx + L * math.cos(ang), pvy + L * math.sin(ang))
    # motion arcs (path it took swinging back up from Lou's head)
    for k, r in enumerate((150, 172, 194)):
        a0 = math.radians(78 - k * 6)
        a1 = ang + math.radians(22)
        x0, y0 = pvx + r * math.cos(a0), pvy + r * math.sin(a0)
        x1, y1 = pvx + r * math.cos(a1), pvy + r * math.sin(a1)
        S.append('<path d="M%s,%s A%d,%d 0 0 0 %s,%s" fill="none" stroke="%s" stroke-width="5" stroke-linecap="round" opacity="0.9"/>'
                 % (f(x0), f(y0), r, r, f(x1), f(y1), WHITE))
    S.append('<rect x="%d" y="%d" width="140" height="320" rx="70" fill="#8A5A3A" stroke="%s" stroke-width="6"/>' % (dcx - 70, dtop, INK))
    S.append('<path d="M%d,%d Q%d,%d %d,%d" fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" opacity="0.6"/>'
             % (dcx - 36, dtop + 60, dcx - 46, dtop + 160, dcx - 34, dtop + 262, INK))
    S.append('<rect x="%d" y="%d" width="140" height="18" fill="#6E4630" stroke="%s" stroke-width="4"/>' % (dcx - 70, dtop + 230, INK))
    S.append(limb([(pvx, pvy), tip], 20, '#8A5A3A'))
    S.append('<circle cx="%s" cy="%s" r="9" fill="%s" stroke="%s" stroke-width="4"/>' % (f(pvx), f(pvy), '#B8893A', INK))
    # cord: hands -> pulley -> along ceiling -> pulley -> ring
    S.append(rope([(318, 256), (318, ring[1] - 30)]))
    S.append(rope([(318, 252), (630, 252)]))
    S.append('<circle cx="%d" cy="%d" r="28" fill="none" stroke="%s" stroke-width="14"/>' % (ring[0], ring[1], INK))
    S.append('<circle cx="%d" cy="%d" r="28" fill="none" stroke="#B8893A" stroke-width="8"/>' % ring)
    for (px, py) in ((318, 252), (630, 252)):
        S.append('<circle cx="%d" cy="%d" r="13" fill="#B8893A" stroke="%s" stroke-width="5"/>' % (px, py, INK))
    # ting star on the ring
    sx, sy = ring[0] - 52, ring[1] - 40
    star = []
    for k in range(8):
        a = math.radians(k * 45 - 90)
        r = 34 if k % 2 == 0 else 8
        star.append((sx + r * math.cos(a), sy + r * math.sin(a)))
    S.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (pts(star), '#FFE7A8', INK))

    # ---- lamp (upper right) and its cord
    lx, ly = 860, 340
    S.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="#0E0907" stroke-width="4"/>' % (lx, lx, ly - 62))
    S.append('<ellipse cx="%d" cy="%d" rx="58" ry="70" fill="%s" stroke="%s" stroke-width="6"/>' % (lx, ly, AMBER, INK))
    for k in (-34, 0, 34):
        S.append('<path d="M%d,%d Q%d,%d %d,%d" fill="none" stroke="#C9963E" stroke-width="3"/>' % (lx - 56, ly + k, lx, ly + k + 10, lx + 56, ly + k))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly - 76, INK))
    S.append('<rect x="%d" y="%d" width="50" height="14" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (lx - 25, ly + 64, INK))

    # ---- Dot: cast shadow on the wall (light from the lamp, upper right)
    S.append('<g opacity="0.55"><ellipse cx="748" cy="700" rx="150" ry="100" fill="#3E0F18"/>'
             '<path d="M700,780 L880,770 L960,1180 L790,1180 Z" fill="#3E0F18"/></g>')
    # Dot torso (leaning out from behind the pillar)
    tor = 'M%d,%d Q%d,%d %d,%d L%d,%d L%d,%d L%d,%d Q%d,%d %d,%d Z' % (
        718, 830, 730, 782, 800, 776, 900, 772, 1010, 1220, 820, 1240, 752, 1000, 718, 830)
    S.append('<path d="%s" fill="%s" stroke="%s" stroke-width="6" stroke-linejoin="round"/>' % (tor, DOT['cardigan'], INK))
    S.append('<path d="M796,780 L840,900 L870,778" fill="#5A1A26" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % INK)
    S.append('<path d="M840,900 L900,1220" fill="none" stroke="%s" stroke-width="4"/>' % INK)
    for k in range(3):
        S.append('<circle cx="%s" cy="%s" r="6" fill="#B8893A" stroke="%s" stroke-width="3"/>' % (f(850 + k * 13), f(960 + k * 70), INK))
    # lanyard + badge
    S.append('<path d="M812,786 L838,930 L866,784" fill="none" stroke="#9FCFB8" stroke-width="5"/>')
    S.append('<rect x="818" y="926" width="42" height="54" rx="5" fill="%s" stroke="%s" stroke-width="4" transform="rotate(-12 839 953)"/>' % (MINT, INK))
    S.append('<rect x="828" y="938" width="22" height="14" fill="#5E7F73" transform="rotate(-12 839 953)"/>')
    # neck
    S.append('<rect x="784" y="738" width="40" height="52" fill="%s" stroke="%s" stroke-width="5"/>' % (DOT['skin'], INK))
    # rope (the release cord) from pulley down through her fists
    ropex = 630
    S.append(rope([(ropex, 252), (ropex, 1060), (ropex + 6, 1100)]))
    S.append('<path d="M%d,1092 l-12,46 l30,0 Z" fill="#8E2A35" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (ropex - 6, INK))
    # arms to the rope
    S.append(limb([(744, 822), (700, 860), (ropex + 24, 868)], 30, DOT['cardigan']))
    S.append(limb([(880, 800), (820, 960), (ropex + 24, 950)], 30, DOT['cardigan']))
    for (cx0, cy0) in ((ropex + 40, 868), (ropex + 40, 950)):
        S.append('<rect x="%d" y="%d" width="18" height="42" rx="4" fill="#CDBFA6" stroke="%s" stroke-width="4"/>' % (cx0 - 9, cy0 - 21, INK))
    S.append('<path d="M872,1040 L924,1030 L934,1080 L882,1090 Z" fill="#DCCDB3" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % INK)
    for (hx, hy) in ((ropex + 4, 868), (ropex + 4, 950)):
        S.append('<rect x="%d" y="%d" width="48" height="40" rx="16" fill="%s" stroke="%s" stroke-width="5"/>' % (hx - 24, hy - 20, DOT['skin'], INK))
        for kk in (-7, 5):
            S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % (hx - 14, hy + kk, hx + 4, hy + kk, INK))
    # low shoe cabinet in front of her waist, five paper cups on it (the fifth still steaming)
    S.append('<rect x="660" y="1150" width="440" height="%d" fill="#4A2E24" stroke="%s" stroke-width="6"/>' % (FLOOR - 1150 + 4, INK))
    S.append('<rect x="648" y="1132" width="460" height="24" fill="#6B4630" stroke="%s" stroke-width="5"/>' % INK)
    for k in range(3):
        S.append('<rect x="%d" y="1180" width="96" height="110" fill="#3E261E" stroke="%s" stroke-width="4"/>' % (684 + k * 110, INK))
    for k in range(5):
        cxp = 690 + k * 46
        cup = 'M%d,1084 L%d,1084 L%d,1132 L%d,1132 Z' % (cxp - 17, cxp + 17, cxp + 12, cxp - 12)
        S.append('<path d="%s" fill="%s" stroke="%s" stroke-width="4" stroke-linejoin="round"/>' % (cup, WHITE if k == 4 else '#E9DCC6', INK))
        S.append('<rect x="%d" y="1098" width="%d" height="12" fill="#8E2A35"/>' % (cxp - 15, 30))
        S.append('<line x1="%d" y1="1084" x2="%d" y2="1084" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (cxp - 19, cxp + 19, INK))
    S.append('<path d="M874,1072 q-10,-12 0,-24 q10,-12 0,-24" fill="none" stroke="%s" stroke-width="4" stroke-linecap="round" opacity="0.7"/>' % WHITE)
    # pillar in front of her lower body
    px0 = 950
    S.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#55141F" stroke="%s" stroke-width="6"/>' % (px0, CEIL - 10, 140, FLOOR - CEIL + 20, INK))
    S.append('<rect x="%d" y="%d" width="16" height="%d" fill="#8A2E3A"/>' % (px0 + 18, CEIL, FLOOR - CEIL - 10))
    S.append('<rect x="%d" y="%d" width="150" height="40" fill="#3A2620" stroke="%s" stroke-width="5"/>' % (px0 - 10, FLOOR - 60, INK))
    # Dot's head (same rig)
    S.append(face('dot', 800, 660, W=300, H=200, skin=DOT['skin'], stubble=None, eye_w=120, eye_d=75, eye_scale=1.08,
                  eye_top=0.34, eye_gap=18, lid=(0, 0), pupil_d=14, pupils=((-0.5, 0.22), (-0.5, 0.22)), stubble_dots=False,
                  mouth='g', mouth_dx=-10, cowlick=None, hair='bun', hair_frac=0.15, sweat='right', tilt=0,
                  emanata=True, emanata_sides=(1,), mark_color=WHITE, bowl_tilt=9))

    # ---- Lou: cast shadow on the floor (moonlight from the upper-left window)
    S.append('<path d="M290,1540 L470,1540 L700,1566 L450,1572 Z" fill="#24150F" opacity="0.85"/>')
    # legs
    S.append(limb([(330, 1240), (322, 1516)], 54, '#2F3B38'))
    S.append(limb([(412, 1240), (424, 1516)], 54, '#2F3B38'))
    for (sx0, sgn) in ((322, -1), (424, 1)):
        S.append('<path d="M%d,1508 L%d,1508 Q%d,1546 %d,1546 L%d,1546 Q%d,1528 %d,1508 Z" fill="#2A1D18" stroke="%s" stroke-width="6" stroke-linejoin="round"/>'
                 % (sx0 - 32, sx0 + 32, sx0 + 32 + sgn * 18, sx0 + 20 + sgn * 26, sx0 - 20 + sgn * 6, sx0 - 34, sx0 - 32, INK))
    # raised arm (flick) behind
    S.append(limb([(262, 980), (100, 890), (198, 668)], 40, LOU['jacket']))
    # jacket body
    jk = 'M%d,%d Q%d,%d %d,%d L%d,%d Q%d,%d %d,%d L%d,%d Q%d,%d %d,%d Z' % (
        238, 1262, 226, 960, 300, 920, 440, 920, 514, 960, 502, 1262, 400, 1270, 300, 1272, 238, 1262)
    S.append('<path d="%s" fill="%s" stroke="%s" stroke-width="6" stroke-linejoin="round"/>' % (jk, LOU['jacket'], INK))
    S.append('<line x1="372" y1="960" x2="374" y2="1262" stroke="%s" stroke-width="4"/>' % INK)
    S.append('<path d="M286,1120 L344,1120 L344,1176 L286,1176 Z" fill="#557368" stroke="%s" stroke-width="4"/>' % INK)
    S.append('<rect x="238" y="1222" width="264" height="18" fill="#4D6A5F" stroke="%s" stroke-width="4"/>' % INK)
    # broom (angled down-left) -- handle behind his right hand
    S.append('<line x1="592" y1="1010" x2="210" y2="1440" stroke="%s" stroke-width="20" stroke-linecap="round"/>' % INK)
    S.append('<line x1="592" y1="1010" x2="210" y2="1440" stroke="#A9773F" stroke-width="10" stroke-linecap="round"/>')
    br = 'M196,1420 L238,1452 Q270,1500 254,1546 L130,1546 Q96,1520 92,1500 Q150,1470 196,1420 Z'
    S.append('<path d="%s" fill="#D9B25E" stroke="%s" stroke-width="6" stroke-linejoin="round"/>' % (br, INK))
    for (a, b) in (((180, 1462), (150, 1540)), ((210, 1470), (200, 1540)), ((150, 1480), (110, 1530))):
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#A9823A" stroke-width="4" stroke-linecap="round"/>' % (a[0], a[1], b[0], b[1]))
    S.append('<path d="M180,1420 L232,1462" stroke="%s" stroke-width="18" stroke-linecap="round"/>' % INK)
    S.append('<path d="M180,1420 L232,1462" stroke="#8E2A35" stroke-width="10" stroke-linecap="round"/>')
    # broom arm (left of screen-right shoulder down to the handle)
    S.append(limb([(486, 975), (540, 1080), (520, 1090)], 40, LOU['jacket']))
    S.append('<circle cx="514" cy="1098" r="24" fill="%s" stroke="%s" stroke-width="5"/>' % (LOU['skin'], INK))
    # flick hand: fist with index finger flicked up-right
    S.append(limb([(204, 640), (224, 606)], 12, LOU['skin'], outline=5))
    S.append('<circle cx="198" cy="660" r="24" fill="%s" stroke="%s" stroke-width="5"/>' % (LOU['skin'], INK))
    for (a, b) in (((236, 590), (250, 572)), ((246, 604), (268, 598)), ((222, 584), (224, 562))):
        S.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="5" stroke-linecap="round"/>' % (a[0], a[1], b[0], b[1], WHITE))
    # neck + head (same rig)
    S.append('<rect x="346" y="880" width="48" height="56" fill="%s" stroke="%s" stroke-width="5"/>' % (LOU['skin'], INK))
    S.append(face('lou', 370, 800, W=420, H=210, eye_w=160, eye_d=90, eye_top=0.32, eye_gap=24, lid=(0.60, 0.60),
                  pupil_d=24, pupils=((1, 0), (1, 0)), mouth='a', mouth_w=50 / 1.4, mouth_dx=-18 / 1.4,
                  cowlick='flat', lid_w=7))

    # ---- ceiling band (only the lamp cord crosses it) -- re-drawn on top to keep it clean
    S.append('<rect x="0" y="0" width="1080" height="%d" fill="%s"/>' % (CEIL, COFFEE))
    S.append('<rect x="0" y="%d" width="1080" height="10" fill="#3A2620" stroke="%s" stroke-width="4"/>' % (CEIL - 6, INK))
    S.append('<line x1="%d" y1="0" x2="%d" y2="%d" stroke="#5A3A28" stroke-width="4"/>' % (lx, lx, ly - 76))
    # vignette
    S.append('<rect width="1080" height="1920" fill="url(#vig)"/>')
    S.append('</svg>')
    return '\n'.join(S)


if __name__ == '__main__':
    with open(os.path.join(HERE, 'faces.svg'), 'w') as fh:
        fh.write(build_faces())
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(build_scene())
    print('wrote faces.svg, scene.svg')
