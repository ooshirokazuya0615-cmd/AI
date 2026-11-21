#!/usr/bin/env python3
"""Nose to Nose / 横顔のにらみ合い -- one profile-face rig, two images.

The rig draws a strict side-view head from parameters (local coords, facing right,
skull box 0..W x 0..H; mirrored with scale(-1,1) for left-facing characters):

  head    : D-shaped silhouette -- semicircular back of skull, flat top, nearly
            vertical front edge, softly rounded chin. jaw = drop (px) for open mouth.
  nose    : wedge cut out of the front edge. type tri / ski / square / button,
            state neutral / flare (extra notch + nostril) / up (tipped up N deg).
  eye     : ONE eye. almond (open 0..1.1, >1 scales it up), circle, or closed arc.
            lid = skin mask from the top (coverage = 1-open) with tilt (+ = front end low).
            pupil = round, gaze px/py (fraction of eye size), ghost copies for vibration.
  brow    : ink wedge, thick end at the front; raise (px), tilt (+ = front end low).
  mouth   : notch cut into the front edge at 80% height:
            a flat / b open wedge / c pursed bump / d teeth / e wavy / f downturned.
  ear     : ink C-curve.   hair: flat ink cap (topknot / sweep).
  marks   : emanata, sweat, gloom, shake.
  rot     : whole-head rotation about the neck (+ = forward/down, - = tipped back).

Both scene.svg and faces.svg are built only from this rig.
"""
import math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
INK = '#23201C'
EYEW = '#FFFBF2'
MOUTHC = '#3A2420'
SAND = '#E8D5B0'
TERRA = '#C0643F'
TERRA_D = '#A3502F'
DUSK = '#3F5873'
DUSK_D = '#33485F'
SAGE = '#8FA58A'
PALE = '#F6F0E4'
MOON = '#EBD9B4'
HAZE = '#5C7088'
ROOF = '#2E4258'
FLOOR_D = '#B89E78'
PLANK = '#D6BF97'
BRASS = '#C9A24B'
WOOD = '#A5703F'
WOOD_D = '#8C5C33'
SKIN_SOL = '#9A6243'
SKIN_SNOOT = '#D6A27C'
SKIN_DARK = '#5C3B2A'


def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith('.0') else s


def pt(p):
    return f"{n(p[0])},{n(p[1])}"


def rot(p, c, deg):
    a = math.radians(deg)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))


# ---------------------------------------------------------------- path segments
def segs_str(segs):
    out = []
    for s in segs:
        if s[0] == 'L':
            out.append('L' + pt(s[1]))
        elif s[0] == 'Q':
            out.append('Q' + pt(s[1]) + ' ' + pt(s[2]))
        elif s[0] == 'C':
            out.append('C' + pt(s[1]) + ' ' + pt(s[2]) + ' ' + pt(s[3]))
    return ' '.join(out)


def segs_map(segs, f):
    return [(s[0],) + tuple(f(q) for q in s[1:]) for s in segs]


def segs_pts(segs):
    out = []
    for s in segs:
        out.append(s[-1])
    return out


def rounded(verts, radii):
    """Polyline through verts with quadratic-rounded interior corners."""
    segs = [('L', verts[0])]
    for i in range(1, len(verts) - 1):
        v, r = verts[i], radii[i]
        if r <= 0:
            segs.append(('L', v))
            continue
        a, b = verts[i - 1], verts[i + 1]
        da, db = math.dist(a, v), math.dist(b, v)
        r = min(r, da * 0.48, db * 0.48)
        pa = (v[0] + (a[0] - v[0]) * r / da, v[1] + (a[1] - v[1]) * r / da)
        pb = (v[0] + (b[0] - v[0]) * r / db, v[1] + (b[1] - v[1]) * r / db)
        segs += [('L', pa), ('Q', v, pb)]
    segs.append(('L', verts[-1]))
    return segs


def closed_rounded(verts, r):
    """Closed polygon with all corners rounded by r -> path d."""
    m = len(verts)
    rr = r if isinstance(r, (list, tuple)) else [r] * m
    parts = []
    for i in range(m):
        a, v, b = verts[i - 1], verts[i], verts[(i + 1) % m]
        da, db = math.dist(a, v), math.dist(b, v)
        ri = min(rr[i], da * 0.48, db * 0.48)
        pa = (v[0] + (a[0] - v[0]) * ri / da, v[1] + (a[1] - v[1]) * ri / da)
        pb = (v[0] + (b[0] - v[0]) * ri / db, v[1] + (b[1] - v[1]) * ri / db)
        parts.append(('M' if i == 0 else 'L') + pt(pa) + ' Q' + pt(v) + ' ' + pt(pb))
    return ' '.join(parts) + ' Z'


# ---------------------------------------------------------------- face params
def make_face(**kw):
    """Defaults = SOL neutral at sheet size (240 x 290)."""
    p = dict(W=240, H=290, skin=SKIN_SOL, hair='topknot', tie=BRASS,
             nose='tri', nl=76, nh=64, nose_state='neutral', nose_up=8,
             eye=dict(kind='almond', w=100, h=64, open=0.7, tilt=0, px=0.16, py=0.0,
                      pr=12, ghosts=False, d=104),
             brow=dict(len=80, th=16, raise_=0, tilt=0, dx=0, arch=0),
             mouth='a', jaw=0, marks=[], front=36)
    for k, v in kw.items():
        if k in ('eye', 'brow'):
            p[k] = dict(p[k], **v)
        else:
            p[k] = v
    return p


def geo(p):
    W, H = p['W'], p['H']
    k = W / 240.0
    e = p['eye']
    g = dict(W=W, H=H, k=k)
    g['ex'] = W - p['front'] * k - e['w'] / 2
    g['ey'] = 0.42 * H
    g['ny'] = 0.55 * H
    g['my'] = 0.80 * H
    g['rx'] = 0.5 * W
    g['rc'] = 0.17 * W
    g['rch'] = 0.16 * W
    return g


# ---------------------------------------------------------------- nose
def nose_segs(p, g):
    W, k = g['W'], g['k']
    nl, nh = p['nl'], p['nh']
    ny = g['ny']
    y0, y1 = ny - nh / 2, ny + nh / 2
    t = p['nose']
    st = p['nose_state']
    base = (W, y1)
    if t == 'tri':
        tip = (W + nl, y1 - nh * 0.10)
        if st == 'flare':
            verts = [(W, y0), tip,
                     (W + nl - 12 * k, y1 - 1 * k),
                     (W + nl - 19 * k, y1 - 13 * k),
                     (W + nl * 0.50, y1 + 11 * k),
                     (W + nl * 0.16, y1 + 8 * k),
                     (W, y1)]
            segs = rounded(verts, [0, 9 * k, 2 * k, 3 * k, 14 * k, 8 * k, 0])
        else:
            verts = [(W, y0), tip, (W, y1)]
            segs = rounded(verts, [0, 9 * k, 0])
    elif t == 'ski':
        # long concave bridge from the brow, small tip flipped up, straight underside
        segs = [('L', (W, y0 - 0.26 * nh)),
                ('C', (W + 0.30 * nl, y0 + 0.36 * nh), (W + 0.62 * nl, y0 + 0.64 * nh), (W + 0.88 * nl, y0 + 0.50 * nh)),
                ('Q', (W + 0.97 * nl, y0 + 0.45 * nh), (W + 1.0 * nl, y0 + 0.34 * nh)),
                ('Q', (W + 1.05 * nl, y0 + 0.58 * nh), (W + 0.90 * nl, y0 + 0.70 * nh))]
        if st == 'flare':
            segs += [('L', (W + 0.74 * nl, y0 + 0.78 * nh)),
                     ('Q', (W + 0.58 * nl, y1 + 12 * k), (W + 0.40 * nl, y1 + 4 * k)),
                     ('Q', (W + 0.18 * nl, y1 + 1 * k), (W, y1))]
        else:
            segs += [('L', (W + 0.45 * nl, y1 - 0.04 * nh)),
                     ('Q', (W + 0.20 * nl, y1 + 0.02 * nh), (W, y1))]
    elif t == 'square':
        verts = [(W, y0), (W + nl, y0 + 6 * k), (W + nl, y1), (W, y1)]
        segs = rounded(verts, [0, 8 * k, 8 * k, 0])
    else:  # button
        segs = [('L', (W, y0 + nh * 0.2)),
                ('C', (W + nl * 0.9, y0 + nh * 0.05), (W + nl * 0.9, y1 + nh * 0.05), (W, y1))]
    if st == 'up' or p.get('nose_always_up'):
        ang = -p['nose_up']
        segs = [segs[0]] + segs_map(segs[1:-1], lambda q: rot(q, base, ang)) + [segs[-1]]
    return segs


def seg_sample(segs, start):
    pts, cur = [], start
    for s in segs:
        if s[0] == 'L':
            pts.append(s[1])
        elif s[0] == 'Q':
            c, e = s[1], s[2]
            for i in range(1, 21):
                t = i / 20
                pts.append(((1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * c[0] + t * t * e[0],
                            (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * c[1] + t * t * e[1]))
        elif s[0] == 'C':
            c1, c2, e = s[1], s[2], s[3]
            for i in range(1, 21):
                t = i / 20
                pts.append(tuple((1 - t) ** 3 * cur[j] + 3 * (1 - t) ** 2 * t * c1[j] + 3 * (1 - t) * t * t * c2[j] + t ** 3 * e[j]
                                 for j in range(2)))
        cur = s[-1]
    return pts


def nose_tip(p):
    g = geo(p)
    pts = seg_sample(nose_segs(p, g), (g['W'], 0))
    return max(pts, key=lambda q: q[0])


def nostril_svg(p, g):
    """Visible dark nostril: always on an upturned (ski) nose, grows when flared;
    on other noses only when flared. Plus the wing crease when flared."""
    W, k = g['W'], g['k']
    nl, nh = p['nl'], p['nh']
    y0, y1 = g['ny'] - nh / 2, g['ny'] + nh / 2
    flare = p['nose_state'] == 'flare'
    out = ''
    if p['nose'] == 'ski':
        rx, ry = (14 * k, 8 * k) if flare else (9 * k, 5 * k)
        cx, cy = W + 0.60 * nl, y0 + 0.86 * nh
        out += (f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{MOUTHC}" '
                f'transform="rotate(-24,{n(cx)},{n(cy)})"/>')
        if flare:
            d = f"M{pt((W + 0.40 * nl, y0 + 0.62 * nh))} Q{pt((W + 0.32 * nl, y0 + 0.84 * nh))} {pt((W + 0.42 * nl, y1 + 1 * k))}"
            out += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
    elif flare:
        cx, cy = W + nl * 0.52, y1 + 2 * k
        out += (f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(14 * k)}" ry="{n(7 * k)}" fill="{MOUTHC}" '
                f'transform="rotate(-6,{n(cx)},{n(cy)})"/>')
        d = f"M{pt((W + nl * 0.30, y1 - 22 * k))} Q{pt((W + nl * 0.18, y1 - 6 * k))} {pt((W + nl * 0.30, y1 + 6 * k))}"
        out += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
    if out and (p['nose_state'] == 'up' or p.get('nose_always_up')):
        return f'<g transform="rotate({-p["nose_up"]},{n(W)},{n(y1)})">{out}</g>'
    return out


# ---------------------------------------------------------------- mouth
def mouth_parts(p, g):
    W, k, my = g['W'], g['k'], g['my']
    m = p['mouth']
    det = ''
    if m == 'a':
        segs = [('L', (W, my - 3.5 * k)), ('L', (W - 24 * k, my)), ('L', (W, my + 3.5 * k))]
        det = (f'<path d="M{pt((W - 3, my))} L{pt((W - 30 * k, my))}" stroke="{INK}" '
               f'stroke-width="6" stroke-linecap="round"/>')
    elif m == 'b':
        jaw = p['jaw']
        a, b, c = (W, my - 14 * k), (W - 50 * k, my + 2 * k), (W + 3 * k, my + 30 * k + jaw)
        segs = [('L', a), ('L', b), ('L', c)]
        det = (f'<path d="M{pt(a)} L{pt(b)} L{pt(c)} Z" fill="{MOUTHC}" stroke="{MOUTHC}" '
               f'stroke-width="2" stroke-linejoin="round"/>'
               f'<path d="M{pt((c[0] - 24 * k, c[1] - 6 * k))} Q{pt((c[0] - 12 * k, c[1] - 22 * k))} '
               f'{pt((c[0] + 1, c[1] - 14 * k))} L{pt(c)} Z" fill="{TERRA}"/>')
    elif m == 'c':
        segs = [('L', (W, my - 14 * k)),
                ('C', (W + 22 * k, my - 16 * k), (W + 22 * k, my + 14 * k), (W, my + 14 * k))]
        det = (f'<path d="M{pt((W + 13 * k, my))} L{pt((W - 4 * k, my))}" stroke="{INK}" '
               f'stroke-width="6" stroke-linecap="round"/>')
    elif m == 'd':
        a, b, c = (W, my - 17 * k), (W - 40 * k, my), (W, my + 19 * k)
        segs = [('L', a), ('L', b), ('L', c)]
        zz = [(W + 1, my + 1)]
        steps = 5
        for i in range(1, steps + 1):
            x = W - 36 * k * i / steps
            y = my + (6 * k if i % 2 else -5 * k) * (1 - i / (steps + 2))
            zz.append((x, y))
        det = (f'<path d="M{pt(a)} L{pt(b)} L{pt(c)} Z" fill="{EYEW}"/>'
               f'<path d="M{" L".join(pt(q) for q in zz)}" fill="none" stroke="{INK}" stroke-width="4" '
               f'stroke-linejoin="round" stroke-linecap="round"/>'
               f'<path d="M{pt(a)} L{pt(b)} L{pt(c)}" fill="none" stroke="{INK}" stroke-width="4" '
               f'stroke-linejoin="round" stroke-linecap="round"/>')
    elif m == 'e':
        segs = [('L', (W, my - 6 * k)), ('L', (W - 12 * k, my)), ('L', (W, my + 6 * k))]
        d = f"M{pt((W + 2, my))}"
        L = 46 * k
        for i in range(4):
            x0 = W - L * i / 4
            x1 = W - L * (i + 1) / 4
            amp = (6 if i % 2 == 0 else -6) * k
            d += f" Q{pt(((x0 + x1) / 2, my + amp))} {pt((x1, my))}"
        det = f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    else:  # f downturned
        segs = [('L', (W, my - 5 * k)), ('L', (W - 10 * k, my)), ('L', (W, my + 5 * k))]
        d = f"M{pt((W + 2, my - 1))} Q{pt((W - 22 * k, my - 6 * k))} {pt((W - 34 * k, my + 14 * k))}"
        det = f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    return segs, det


# ---------------------------------------------------------------- head silhouette
def head_d(p, g):
    W, H = g['W'], g['H']
    rx, rc, rch = g['rx'], g['rc'], g['rch']
    jaw = p['jaw'] if p['mouth'] == 'b' else 0
    d = f"M{n(rx)},0 L{n(W - rc)},0 Q{n(W)},0 {n(W)},{n(rc)} "
    d += segs_str(nose_segs(p, g)) + ' '
    ms, _ = mouth_parts(p, g)
    d += segs_str(ms) + ' '
    d += (f"L{n(W)},{n(H + jaw - rch)} Q{n(W)},{n(H + jaw)} {n(W - rch)},{n(H + jaw)} "
          f"L{n(rx)},{n(H)} A{n(rx)},{n(H / 2)} 0 0 1 {n(rx)},0 Z")
    return d


# ---------------------------------------------------------------- eye
def bez_y_at(x, w, c, a):
    """Symmetric cubic from (-w/2,0) to (w/2,0) with controls (-a,c),(a,c): y at x."""
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


def eye_svg(p, g, uid):
    e = p['eye']
    ex, ey = g['ex'], g['ey']
    kind = e['kind']
    skin = p['skin']
    if kind == 'arc':
        w, h = e['w'], e['h']
        d = f"M{pt((ex - w / 2, ey + h * 0.16))} Q{pt((ex, ey - h * 0.78))} {pt((ex + w / 2, ey + h * 0.16))}"
        return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>', ey - h * 0.3)
    if kind == 'circle':
        r = e['d'] / 2
        shape = f'<circle cx="{n(ex)}" cy="{n(ey)}" r="{n(r)}"/>'
        top = ey - r
        cov = 0.0
        hh = 2 * r
        w = 2 * r

        def upper(x):
            dx = max(-r, min(r, x - ex))
            return ey - math.sqrt(max(0, r * r - dx * dx))

        def lower(x):
            dx = max(-r, min(r, x - ex))
            return ey + math.sqrt(max(0, r * r - dx * dx))
        upper_d = f"M{pt((ex - r, ey))} A{n(r)},{n(r)} 0 0 1 {pt((ex + r, ey))}"
        lower_d = f"M{pt((ex - r, ey))} A{n(r)},{n(r)} 0 0 0 {pt((ex + r, ey))}"
    else:
        s = max(1.0, e['open'])
        w, hh = e['w'] * s, e['h'] * s
        cov = max(0.0, 1.0 - e['open'])
        hu, hl = hh * 0.54, hh * 0.46
        cu, cl = -hu / 0.75, hl / 0.75
        a = w * 0.22
        top = ey - hu
        upper_d = (f"M{pt((ex - w / 2, ey))} C{pt((ex - a, ey + cu))} {pt((ex + a, ey + cu))} {pt((ex + w / 2, ey))}")
        lower_d = (f"M{pt((ex - w / 2, ey))} C{pt((ex - a, ey + cl))} {pt((ex + a, ey + cl))} {pt((ex + w / 2, ey))}")
        shape = (f'<path d="M{pt((ex - w / 2, ey))} C{pt((ex - a, ey + cu))} {pt((ex + a, ey + cu))} {pt((ex + w / 2, ey))} '
                 f'C{pt((ex + a, ey + cl))} {pt((ex - a, ey + cl))} {pt((ex - w / 2, ey))} Z"/>')

        def upper(x):
            return ey + bez_y_at(x - ex, w, cu, a)

        def lower(x):
            return ey + bez_y_at(x - ex, w, cl, a)
    tilt = math.tan(math.radians(e['tilt']))

    def lid_y(x):
        return top + cov * hh + tilt * (x - ex)

    cid = f'eye{uid}'
    out = [f'<defs><clipPath id="{cid}">{shape}</clipPath></defs>']
    out.append(shape.replace('/>', f' fill="{EYEW}"/>'))
    pr = e['pr']
    px = ex + e['px'] * w
    py = ey + e['py'] * hh
    if cov > 0:
        tv, bv = lid_y(px), lower(px)
        lo, hi = tv + pr * 0.75, bv - pr * 0.75
        py = min(max(py, lo), hi) if lo <= hi else (tv + bv) / 2 + 3
    g_in = []
    if e.get('ghosts'):
        for gx in (-11, 11):
            g_in.append(f'<circle cx="{n(px + gx)}" cy="{n(py)}" r="{n(pr)}" fill="{INK}" opacity="0.4"/>')
    g_in.append(f'<circle cx="{n(px)}" cy="{n(py)}" r="{n(pr)}" fill="{INK}"/>')
    if pr >= 9:
        g_in.append(f'<circle cx="{n(px + pr * 0.38)}" cy="{n(py - pr * 0.38)}" r="{n(pr * 0.3)}" fill="{EYEW}"/>')
    if cov > 0:
        x0, x1 = ex - w, ex + w
        g_in.append(f'<path d="M{pt((x0, lid_y(x0)))} L{pt((x1, lid_y(x1)))} L{pt((x1, top - hh))} L{pt((x0, top - hh))} Z" fill="{skin}"/>')
        g_in.append(f'<path d="M{pt((x0, lid_y(x0)))} L{pt((x1, lid_y(x1)))}" stroke="{INK}" stroke-width="9"/>')
    out.append(f'<g clip-path="url(#{cid})">' + ''.join(g_in) + '</g>')
    up_w = 8 if cov < 0.02 else 4
    out.append(f'<path d="{upper_d}" fill="none" stroke="{INK}" stroke-width="{up_w}" stroke-linecap="round"/>')
    out.append(f'<path d="{lower_d}" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>')
    return ''.join(out), top


# ---------------------------------------------------------------- brow
def brow_svg(p, g, eye_top):
    b = p['brow']
    L, tf = b['len'], b['th']
    tb = max(4.0, tf * 0.32)
    cx = g['ex'] + b['dx']
    cy = eye_top - 18 * g['k'] - tf / 2 - b['raise_']
    arch = b.get('arch', 0)
    d = (f"M{pt((-L / 2, -tb / 2))} Q{pt((0, -tf / 2 - arch))} {pt((L / 2, -tf / 2))} "
         f"L{pt((L / 2, tf / 2))} Q{pt((0, tf / 2 - arch))} {pt((-L / 2, tb / 2))} Z")
    return (f'<path transform="translate({n(cx)},{n(cy)}) rotate({n(b["tilt"])})" d="{d}" fill="{INK}" '
            f'stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>')


# ---------------------------------------------------------------- ear, hair
def ear_svg(p, g):
    W, H, k = g['W'], g['H'], g['k']
    cx, cy = 0.40 * W, 0.57 * H
    h = 50 * k
    d = (f"M{pt((cx + 12 * k, cy - h / 2))} C{pt((cx - 20 * k, cy - h / 2 - 4 * k))} "
         f"{pt((cx - 22 * k, cy + h / 2 + 2 * k))} {pt((cx + 10 * k, cy + h / 2))}")
    d2 = f"M{pt((cx + 6 * k, cy - 8 * k))} Q{pt((cx - 6 * k, cy))} {pt((cx + 4 * k, cy + 10 * k))}"
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
            f'<path d="{d2}" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>')


def hair_svg(p, g, uid, sil_d):
    W, H, k = g['W'], g['H'], g['k']
    cid = f'hd{uid}'
    out = [f'<defs><clipPath id="{cid}"><path d="{sil_d}"/></clipPath></defs>']
    if p['hair'] == 'topknot':
        cap = (f"M-40,-40 L{n(0.56 * W)},-40 L{n(0.56 * W)},{n(0.02 * H)} "
               f"C{n(0.50 * W)},{n(0.14 * H)} {n(0.34 * W)},{n(0.22 * H)} {n(0.29 * W)},{n(0.42 * H)} "
               f"C{n(0.26 * W)},{n(0.58 * H)} {n(0.22 * W)},{n(0.74 * H)} {n(0.15 * W)},{n(0.88 * H)} "
               f"L-40,{n(0.96 * H)} Z")
        out.append(f'<path clip-path="url(#{cid})" d="{cap}" fill="{INK}"/>')
        # folded queue (chonmage) lying forward on the crown
        q0, q1 = (0.30 * W, 0.0), (0.64 * W, -2 * k)
        th = 17 * k
        qd = closed_rounded([(q0[0], -th + 3 * k), (q1[0], -th * 0.75), (q1[0] + 4 * k, 2 * k), (q0[0], 6 * k)], 8 * k)
        out.append(f'<path d="{qd}" fill="{INK}"/>')
        out.append(f'<rect x="{n(0.33 * W)}" y="{n(-th + 1 * k)}" width="{n(9 * k)}" height="{n(th + 4 * k)}" rx="{n(2 * k)}" fill="{p["tie"]}"/>')
    else:  # sweep: slicked full cap, glossy sheen, stiff brush tail jutting back
        cap = (f"M-40,-40 L{n(0.84 * W)},-40 L{n(0.84 * W)},{n(0.0)} "
               f"C{n(0.74 * W)},{n(0.09 * H)} {n(0.50 * W)},{n(0.10 * H)} {n(0.36 * W)},{n(0.28 * H)} "
               f"C{n(0.29 * W)},{n(0.40 * H)} {n(0.27 * W)},{n(0.64 * H)} {n(0.17 * W)},{n(0.86 * H)} "
               f"L-40,{n(0.96 * H)} Z")
        out.append(f'<path clip-path="url(#{cid})" d="{cap}" fill="{INK}"/>')
        sheen = (f"M{n(0.70 * W)},{n(0.035 * H)} C{n(0.52 * W)},{n(0.05 * H)} {n(0.32 * W)},{n(0.10 * H)} {n(0.20 * W)},{n(0.24 * H)}")
        out.append(f'<path clip-path="url(#{cid})" d="{sheen}" fill="none" stroke="#4A4239" stroke-width="{n(7 * k)}" stroke-linecap="round"/>')
        # neat round bun at the back of the crown, brass pin through it (vain)
        bc = (0.13 * W, 0.03 * H)
        r = 36 * k
        out.append(f'<line x1="{n(bc[0] - 46 * k)}" y1="{n(bc[1] + 30 * k)}" x2="{n(bc[0] + 54 * k)}" y2="{n(bc[1] - 34 * k)}" '
                   f'stroke="{BRASS}" stroke-width="{n(7 * k)}" stroke-linecap="round"/>')
        out.append(f'<circle cx="{n(bc[0])}" cy="{n(bc[1])}" r="{n(r)}" fill="{INK}"/>')
        out.append(f'<path d="M{n(bc[0] - r * 0.55)},{n(bc[1] - r * 0.35)} Q{n(bc[0])},{n(bc[1] - r * 0.95)} {n(bc[0] + r * 0.6)},{n(bc[1] - r * 0.4)}" '
                   f'fill="none" stroke="#4A4239" stroke-width="{n(5 * k)}" stroke-linecap="round"/>')
        out.append(f'<path d="M{n(bc[0] + r * 0.55)},{n(bc[1] + r * 0.95)} Q{n(bc[0] + r * 0.95)},{n(bc[1] + r * 0.5)} {n(bc[0] + r * 1.05)},{n(bc[1] + r * 0.05)}" '
                   f'fill="none" stroke="{p["tie"]}" stroke-width="{n(10 * k)}" stroke-linecap="round"/>')
        out.append(f'<circle cx="{n(bc[0] + 54 * k)}" cy="{n(bc[1] - 34 * k)}" r="{n(7 * k)}" fill="{BRASS}"/>')
        # kiss curl at the front hairline
        cx0, cy0 = 0.80 * W, 0.02 * H
        d = (f"M{n(cx0)},{n(cy0)} C{n(cx0 + 10 * k)},{n(cy0 + 16 * k)} {n(cx0 + 4 * k)},{n(cy0 + 34 * k)} {n(cx0 - 10 * k)},{n(cy0 + 32 * k)} "
             f"C{n(cx0 - 22 * k)},{n(cy0 + 30 * k)} {n(cx0 - 20 * k)},{n(cy0 + 14 * k)} {n(cx0 - 8 * k)},{n(cy0 + 16 * k)}")
        out.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{n(7 * k)}" stroke-linecap="round"/>')
    return ''.join(out)


# ---------------------------------------------------------------- marks
def marks_svg(p, g):
    W, H, k = g['W'], g['H'], g['k']
    out = []
    st = f'fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"'
    for m in p['marks']:
        if m == 'emanata':
            ox, oy = W + 14 * k, 0.24 * H
            for ang in (-38, -8, 22):
                a = math.radians(ang)
                p0 = (ox + 18 * k * math.cos(a), oy + 18 * k * math.sin(a))
                p1 = (ox + 50 * k * math.cos(a), oy + 50 * k * math.sin(a))
                out.append(f'<path d="M{pt(p0)} L{pt(p1)}" {st}/>')
        elif m == 'sweat':
            # drop flying off the back-top of the head: tip toward the head, round end away
            cx, cy = 0.04 * W, -0.10 * H
            d = "M0,-26 C9,-10 16,2 0,16 C-16,2 -9,-10 0,-26 Z"
            out.append(f'<path transform="translate({n(cx)},{n(cy)}) rotate(135) scale({n(1.3 * k)})" d="{d}" '
                       f'fill="{PALE}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>')
            for off in (-9, 9):
                p0 = (cx + 30 * k + off * 0.7 * k, cy + 26 * k - off * 0.7 * k)
                p1 = (cx + 44 * k + off * 0.7 * k, cy + 40 * k - off * 0.7 * k)
                out.append(f'<path d="M{pt(p0)} L{pt(p1)}" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>')
        elif m == 'gloom':
            for i, fx in enumerate((0.26, 0.48, 0.70)):
                x = fx * W
                y0 = -0.36 * H + (i % 2) * 8 * k
                y1 = -0.13 * H
                d = f"M{pt((x, y0))} Q{pt((x + 7 * k, (y0 + y1) / 2))} {pt((x, y1))}"
                out.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round" stroke-dasharray="{n(14 * k)} {n(9 * k)}"/>')
        elif m == 'snort':
            nl, nh = p['nl'], p['nh']
            y1 = g['ny'] + nh / 2
            bx, by = W + 0.70 * nl, y1 - 2 * k
            for ang in (18, 38, 58):
                a = math.radians(ang)
                p0 = (bx + 22 * k * math.cos(a), by + 22 * k * math.sin(a))
                p1 = (bx + 40 * k * math.cos(a), by + 40 * k * math.sin(a))
                out.append(f'<path d="M{pt(p0)} L{pt(p1)}" fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>')
        elif m == 'shake':
            for i, off in enumerate((12, 27)):
                x = -off * k
                d = f"M{pt((x + 8 * k, 0.30 * H))} Q{pt((x - 6 * k, 0.42 * H))} {pt((x + 8 * k, 0.54 * H))}"
                out.append(f'<path d="{d}" {st}/>')
    return ''.join(out)


# ---------------------------------------------------------------- head assembly
def head_local(p, uid):
    g = geo(p)
    sil = head_d(p, g)
    out = [f'<path d="{sil}" fill="{p["skin"]}"/>']
    out.append(hair_svg(p, g, uid, sil))
    out.append(ear_svg(p, g))
    eye, eye_top = eye_svg(p, g, uid)
    out.append(eye)
    out.append(brow_svg(p, g, eye_top))
    _, mdet = mouth_parts(p, g)
    out.append(mdet)
    out.append(nostril_svg(p, g))
    out.append(marks_svg(p, g))
    return ''.join(out)


def head_transform(p, cx, cy, facing=1, rot_deg=0):
    W, H = p['W'], p['H']
    return (f"translate({n(cx)},{n(cy)}) scale({facing},1) rotate({n(rot_deg)},0,{n(H / 2)}) "
            f"translate({n(-W / 2)},{n(-H / 2)})")


def head(p, cx, cy, facing=1, rot_deg=0, uid='a'):
    return f'<g transform="{head_transform(p, cx, cy, facing, rot_deg)}">{head_local(p, uid)}</g>'


def local_to_world(p, q, cx, cy, facing=1, rot_deg=0):
    W, H = p['W'], p['H']
    x, y = q[0] - W / 2, q[1] - H / 2
    x, y = rot((x, y), (0, H / 2), rot_deg)
    return (cx + facing * x, cy + y)


# ---------------------------------------------------------------- scene
def star4(cx, cy, R, r, rot_deg=0):
    pts = []
    for i in range(8):
        a = math.radians(rot_deg + i * 45 - 90)
        rr = R if i % 2 == 0 else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return 'M' + ' L'.join(pt(q) for q in pts) + ' Z'


def sol_body(cx, floor, broom_x):
    """Sol, local x relative to head center (forward = +x), facing right."""
    o = []
    # broom (behind him, held upright like a spear)
    bx = broom_x
    o.append(f'<rect x="{n(bx - 8)}" y="640" width="16" height="820" rx="8" fill="{WOOD}"/>')
    o.append(f'<rect x="{n(bx - 10)}" y="632" width="20" height="22" rx="6" fill="{INK}"/>')
    brist = closed_rounded([(bx - 16, 1428), (bx + 16, 1428), (bx + 46, floor), (bx - 46, floor)], [6, 6, 3, 3])
    o.append(f'<path d="{brist}" fill="{BRASS}"/>')
    for yy in (1446, 1470):
        w = 18 + (yy - 1428) * 0.32
        o.append(f'<rect x="{n(bx - w)}" y="{yy}" width="{n(2 * w)}" height="9" fill="{INK}"/>')
    for i in range(-3, 4):
        x0 = bx + i * 5
        x1 = bx + i * 12
        o.append(f'<path d="M{n(x0)},1484 L{n(x1)},{floor - 6}" stroke="#A88536" stroke-width="3"/>')
    # legs + feet
    o.append(f'<path d="{closed_rounded([(-78, 1380), (-24, 1380), (-30, 1534), (-74, 1534)], 6)}" fill="{INK}"/>')
    o.append(f'<path d="{closed_rounded([(18, 1380), (72, 1380), (66, 1534), (22, 1534)], 6)}" fill="{INK}"/>')
    o.append(f'<path d="{closed_rounded([(-84, 1526), (-22, 1526), (2, 1542), (2, floor), (-84, floor)], [4, 6, 8, 2, 4])}" fill="{INK}"/>')
    o.append(f'<path d="{closed_rounded([(14, 1526), (74, 1526), (104, 1542), (104, floor), (14, floor)], [4, 6, 8, 2, 4])}" fill="{INK}"/>')
    o.append(f'<rect x="-82" y="1512" width="58" height="16" rx="5" fill="{PALE}"/>')
    o.append(f'<rect x="16" y="1512" width="58" height="16" rx="5" fill="{PALE}"/>')
    # neck
    o.append(f'<rect x="-36" y="980" width="70" height="80" fill="{SKIN_SOL}"/>')
    # coat
    coat = (f"M-70,1034 Q10,1012 74,1034 Q112,1050 114,1104 L132,1400 Q132,1408 124,1408 L-128,1408 "
            f"Q-136,1408 -135,1400 L-114,1094 Q-110,1046 -70,1034 Z")
    o.append(f'<path d="{coat}" fill="{DUSK}"/>')
    # collar
    o.append(f'<path d="M-30,1026 L44,1022 L70,1100 L48,1104 L22,1048 L-26,1050 Z" fill="{DUSK_D}"/>')
    # apron
    apron = closed_rounded([(24, 1104), (104, 1098), (140, 1424), (8, 1424)], [8, 8, 6, 6])
    o.append(f'<path d="{apron}" fill="{SAGE}"/>')
    o.append(f'<path d="M30,1106 L-6,1040" stroke="{SAGE}" stroke-width="14" stroke-linecap="round"/>')
    o.append(f'<rect x="-120" y="1206" width="246" height="14" fill="{INK}"/>')
    o.append(f'<path d="M-118,1214 Q-150,1196 -158,1222 Q-146,1240 -118,1216 Z" fill="{INK}"/>')
    o.append(f'<path d="M-120,1216 L-150,1270" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>')
    # near arm: hangs, bends at the elbow, hand back on the broom
    o.append(f'<path d="M6,1080 L-30,1204 L{bx + 34},1258" fill="none" stroke="{DUSK_D}" stroke-width="58" '
             f'stroke-linecap="round" stroke-linejoin="round"/>')
    o.append(f'<path d="{closed_rounded([(bx - 22, 1230), (bx + 30, 1226), (bx + 34, 1286), (bx - 20, 1290)], 18)}" fill="{SKIN_SOL}"/>')
    return f'<g transform="translate({n(cx)},0)">' + ''.join(o) + '</g>'


def snoot_body(cx, cy, floor, lean):
    """Snoot, local x relative to head center (forward = +x), mirrored to face left.
    Upright body built around foot x = fx, then leaned forward from the feet."""
    o = []
    fx = -60
    # hakama
    hak = closed_rounded([(fx - 84, 1262), (fx + 84, 1262), (fx + 112, floor - 18), (fx - 108, floor - 18)], [10, 10, 4, 4])
    o.append(f'<path d="{hak}" fill="{INK}"/>')
    o.append(f'<path d="M{fx + 4},1300 L{fx + 8},{floor - 22}" stroke="#3A342D" stroke-width="5"/>')
    # feet (tabi)
    o.append(f'<path d="{closed_rounded([(fx + 24, floor - 24), (fx + 100, floor - 24), (fx + 134, floor - 8), (fx + 134, floor), (fx + 24, floor)], [4, 8, 8, 2, 3])}" fill="{PALE}"/>')
    o.append(f'<path d="{closed_rounded([(fx - 104, floor - 24), (fx - 34, floor - 24), (fx - 6, floor - 8), (fx - 6, floor), (fx - 104, floor)], [4, 8, 8, 2, 3])}" fill="#DCCFB8"/>')
    # gi jacket (hunched: back bulges high behind the neck)
    gi = (f"M{fx - 6},1046 Q{fx + 64},1022 {fx + 112},1056 Q{fx + 134},1086 {fx + 124},1146 "
          f"L{fx + 108},1300 L{fx - 102},1300 Q{fx - 128},1200 {fx - 120},1110 Q{fx - 110},1020 {fx - 56},1004 "
          f"Q{fx - 22},998 {fx - 6},1046 Z")
    o.append(f'<path d="{gi}" fill="{TERRA}"/>')
    # cross collar
    o.append(f'<path d="M{fx + 58},1036 L{fx + 116},1214" stroke="{PALE}" stroke-width="18" stroke-linecap="round"/>')
    # belt + knot tails
    o.append(f'<path d="{closed_rounded([(fx - 112, 1236), (fx + 116, 1236), (fx + 114, 1268), (fx - 108, 1268)], 4)}" fill="{INK}"/>')
    o.append(f'<path d="M{fx + 102},1260 L{fx + 122},1336" stroke="{INK}" stroke-width="13" stroke-linecap="round"/>')
    o.append(f'<path d="M{fx + 90},1262 L{fx + 96},1340" stroke="{INK}" stroke-width="13" stroke-linecap="round"/>')
    # arm: hands clasped behind the back (drill-sergeant lean)
    arm = closed_rounded([(fx + 24, 1056), (fx + 66, 1084), (fx + 6, 1172), (fx - 104, 1214), (fx - 120, 1170), (fx - 36, 1122)], [26, 22, 16, 14, 14, 20])
    o.append(f'<path d="{arm}" fill="{TERRA_D}"/>')
    o.append(f'<circle cx="{fx - 124}" cy="1198" r="25" fill="{SKIN_SNOOT}"/>')
    body = ''.join(o)
    neck = f'<path d="M-34,{n(cy + 120)} L36,{n(cy + 120)} L52,{n(cy + 220)} L-30,{n(cy + 220)} Z" fill="{SKIN_SNOOT}"/>'
    return (f'<g transform="translate({n(cx)},0) scale(-1,1)">{neck}'
            f'<g transform="rotate({n(lean)},{fx},{floor})">{body}</g></g>')


def scene_svg():
    Wc, Hc = 1080, 1920
    floor = 1550
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hc}" viewBox="0 0 {Wc} {Hc}">']
    # sky, haze, moon, roofs, floor
    o.append(f'<rect width="{Wc}" height="{Hc}" fill="{DUSK}"/>')
    o.append(f'<rect y="975" width="{Wc}" height="230" fill="{HAZE}"/>')
    o.append(f'<circle cx="540" cy="860" r="310" fill="{MOON}"/>')
    roofs = ("M0,1205 L0,1132 L70,1132 L58,1118 Q120,1112 180,1096 Q240,1112 300,1118 L288,1132 L330,1132 L330,1150 "
             "L392,1150 L392,1110 L420,1110 L420,1150 L470,1150 Q520,1136 560,1112 Q600,1136 650,1150 L700,1150 "
             "L700,1124 L760,1124 L748,1110 Q810,1104 862,1086 Q914,1104 976,1110 L964,1124 L1080,1124 L1080,1205 Z")
    o.append(f'<path d="{roofs}" fill="{ROOF}"/>')
    o.append(f'<rect y="1196" width="{Wc}" height="380" fill="{SAND}"/>')
    for y in (1222, 1256, 1302, 1364, 1446):
        o.append(f'<rect y="{y}" width="{Wc}" height="4" fill="{PLANK}"/>')
    o.append(f'<rect y="1196" width="{Wc}" height="12" fill="{PLANK}"/>')
    o.append(f'<rect y="1575" width="{Wc}" height="345" fill="{FLOOR_D}"/>')
    # frame: eave beam + posts
    o.append(f'<rect y="230" width="{Wc}" height="34" fill="{INK}"/>')
    o.append(f'<path d="M44,264 L110,264 Q60,290 44,330 Z" fill="{INK}"/>')
    o.append(f'<path d="M1036,264 L970,264 Q1020,290 1036,330 Z" fill="{INK}"/>')
    # rail + rings
    RY = 330
    o.append(f'<rect x="44" y="{RY - 11}" width="992" height="22" fill="{INK}"/>')
    for rx in (160, 300, 780, 920):
        o.append(f'<circle cx="{rx}" cy="{RY + 32}" r="19" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    o.append(f'<circle cx="540" cy="{RY + 32}" r="19" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    # dummy swinging back up to its ring (and back over Snoot's head)
    piv = (540, RY + 51)
    ang = -47
    for r, a0, a1 in ((150, 8, 34), (215, 10, 36), (280, 13, 37)):
        p0 = (piv[0] + r * math.sin(math.radians(a0)), piv[1] + r * math.cos(math.radians(a0)))
        p1 = (piv[0] + r * math.sin(math.radians(a1)), piv[1] + r * math.cos(math.radians(a1)))
        o.append(f'<path d="M{pt(p0)} A{r},{r} 0 0 0 {pt(p1)}" fill="none" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>')
    dm = []
    dm.append(f'<path d="M0,0 L0,30" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
    dm.append(f'<rect x="-104" y="118" width="64" height="26" rx="13" fill="{WOOD_D}" transform="rotate(-18,-44,131)"/>')
    dm.append(f'<rect x="40" y="118" width="64" height="26" rx="13" fill="{WOOD_D}" transform="rotate(18,44,131)"/>')
    dm.append(f'<rect x="-65" y="28" width="130" height="300" rx="65" fill="{WOOD}"/>')
    dm.append(f'<rect x="-65" y="92" width="130" height="13" fill="{WOOD_D}"/>')
    dm.append(f'<rect x="-65" y="250" width="130" height="10" fill="{WOOD_D}"/>')
    for gx, y0, y1 in ((-30, 122, 230), (8, 140, 238), (34, 116, 200)):
        dm.append(f'<path d="M{gx},{y0} Q{gx + 8},{(y0 + y1) / 2} {gx},{y1}" fill="none" stroke="#B9844F" stroke-width="5" stroke-linecap="round"/>')
    dm.append(f'<circle cx="0" cy="40" r="7" fill="{INK}"/>')
    o.append(f'<g transform="translate({piv[0]},{piv[1]}) rotate({ang})">' + ''.join(dm) + '</g>')
    o.append(f'<path d="{star4(540, RY + 32, 46, 11, 0)}" fill="{PALE}"/>')
    o.append(f'<path d="{star4(540, RY + 32, 24, 6, 45)}" fill="{PALE}"/>')

    # heads
    sol = make_face(W=300, H=340, skin=SKIN_SOL, hair='topknot', nl=90, nh=76,
                    eye=dict(w=110, h=70, open=0.55, px=0.18, pr=12),
                    brow=dict(len=92, th=14, raise_=-4, tilt=0, dx=4),
                    mouth='a', front=40)
    snoot = make_face(W=300, H=340, skin=SKIN_SNOOT, hair='sweep', tie=TERRA, nose='ski', nl=104, nh=76,
                      nose_state='flare', nose_up=8, nose_always_up=True,
                      eye=dict(w=110, h=70, open=0.25, tilt=8, px=0.10, pr=12),
                      brow=dict(len=96, th=18, raise_=-30, tilt=25, dx=8),
                      mouth='c', marks=['shake', 'snort'], front=40)
    tip_y = 882
    st = nose_tip(sol)
    sol_cx = 533 - (st[0] - sol['W'] / 2)
    sol_cy = tip_y - (st[1] - sol['H'] / 2)
    nt = nose_tip(snoot)
    sn_rot = 4
    # solve for snoot center with rotation
    wx, wy = local_to_world(snoot, nt, 0, 0, -1, sn_rot)
    sn_cx = 547 - wx
    sn_cy = tip_y - 6 - wy

    # floor shadows
    o.append(f'<ellipse cx="{n(sol_cx - 30)}" cy="{floor}" rx="170" ry="14" fill="{PLANK}"/>')
    o.append(f'<ellipse cx="{n(sn_cx + 84)}" cy="{floor}" rx="150" ry="14" fill="{PLANK}"/>')
    o.append(sol_body(sol_cx, floor, -186))
    o.append(head(sol, sol_cx, sol_cy, 1, 0, 'sol'))
    o.append(snoot_body(sn_cx, sn_cy, floor, 4))
    o.append(head(snoot, sn_cx, sn_cy, -1, sn_rot, 'snoot'))
    o.append(f'<rect x="0" y="230" width="44" height="1345" fill="{INK}"/>')
    o.append(f'<rect x="1036" y="230" width="44" height="1345" fill="{INK}"/>')
    o.append('</svg>')
    return '\n'.join(o), (sol_cx, sol_cy, sn_cx, sn_cy)


# ---------------------------------------------------------------- face sheet
def sheet_faces():
    """Six states of SOL; each is just a parameter set on the same rig."""
    F = []
    F.append((make_face(), 0))                                                       # 1 neutral
    F.append((make_face(eye=dict(kind='circle', d=104, px=0.0, py=0.0, pr=7),
                        brow=dict(raise_=40, tilt=-12), mouth='b', jaw=26, marks=['emanata']), -6))  # 2 surprised
    F.append((make_face(eye=dict(open=0.5, tilt=25, px=0.2, pr=12),
                        brow=dict(raise_=-24, tilt=25, dx=6, th=18), nose_state='flare', mouth='d'), 4))  # 3 angry
    F.append((make_face(eye=dict(kind='arc'), brow=dict(raise_=14, tilt=-8, arch=6),
                        nose_state='up', mouth='c'), -10))                                  # 4 smug
    F.append((make_face(eye=dict(open=1.1, px=0.0, py=0.0, pr=11, ghosts=True),
                        brow=dict(raise_=26, tilt=-22), mouth='e', marks=['sweat', 'shake']), 0))  # 5 panic
    F.append((make_face(eye=dict(open=0.4, tilt=0, px=-0.36, py=0.1, pr=12),
                        brow=dict(raise_=-12, tilt=0), mouth='f', marks=['gloom']), 4))      # 6 side-eye
    return F


def bust(p, cx, cy):
    """Neck + coat shoulders under the head (not rotated)."""
    W, H = p['W'], p['H']
    top = cy + H / 2
    o = []
    o.append(f'<rect x="{n(cx - 34)}" y="{n(top - 40)}" width="66" height="80" fill="{p["skin"]}"/>')
    coat = (f"M{n(cx - 120)},{n(top + 120)} Q{n(cx - 116)},{n(top + 30)} {n(cx - 50)},{n(top + 22)} "
            f"Q{n(cx + 20)},{n(top + 8)} {n(cx + 84)},{n(top + 28)} Q{n(cx + 120)},{n(top + 46)} {n(cx + 124)},{n(top + 120)} Z")
    o.append(f'<path d="{coat}" fill="{DUSK}"/>')
    o.append(f'<path d="M{n(cx - 26)},{n(top + 14)} L{n(cx + 40)},{n(top + 10)} L{n(cx + 66)},{n(top + 80)} '
             f'L{n(cx + 46)},{n(top + 84)} L{n(cx + 20)},{n(top + 34)} L{n(cx - 22)},{n(top + 36)} Z" fill="{DUSK_D}"/>')
    o.append(f'<path d="{closed_rounded([(cx + 30, top + 84), (cx + 106, top + 78), (cx + 124, top + 140), (cx + 20, top + 140)], 8)}" fill="{SAGE}"/>')
    o.append(f'<path d="M{n(cx + 34)},{n(top + 86)} L{n(cx - 6)},{n(top + 24)}" stroke="{SAGE}" stroke-width="12" stroke-linecap="round"/>')
    return ''.join(o)


def faces_svg():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">']
    o.append(f'<rect width="1080" height="1080" fill="{SAND}"/>')
    faces = sheet_faces()
    for i, (p, r) in enumerate(faces):
        col, row = i % 3, i // 3
        ox, oy = col * 360, row * 540
        cid = f'cell{i}'
        o.append(f'<defs><clipPath id="{cid}"><rect x="{ox}" y="{oy}" width="360" height="540"/></clipPath></defs>')
        o.append(f'<g clip-path="url(#{cid})">')
        o.append(f'<circle cx="{ox + 214}" cy="{oy + 250}" r="140" fill="{PALE}"/>')
        hcx, hcy = ox + 158, oy + 266
        o.append(bust(p, hcx, hcy))
        o.append(head(p, hcx, hcy, 1, r, f'f{i}'))
        o.append('</g>')
    # gutters
    for x in (360, 720):
        o.append(f'<rect x="{x - 2}" y="0" width="4" height="1080" fill="{PLANK}"/>')
    o.append(f'<rect x="0" y="538" width="1080" height="4" fill="{PLANK}"/>')
    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    s, info = scene_svg()
    with open(os.path.join(HERE, 'scene.svg'), 'w') as f:
        f.write(s)
    with open(os.path.join(HERE, 'faces.svg'), 'w') as f:
        f.write(faces_svg())
    print('heads', [round(v, 1) for v in info])
