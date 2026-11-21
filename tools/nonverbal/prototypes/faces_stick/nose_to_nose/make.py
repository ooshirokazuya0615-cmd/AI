#!/usr/bin/env python3
"""Nose to Nose / 横顔のにらみ合い -- STICK-BODY version.

Head: the ORIGINAL profile-face rig, copied unchanged from make_face_original.py
(D-shaped strict-profile skull, wedge nose, one eye with lid mask, ink wedge brow,
notch mouths, flat ink hair cap, marks).  head(p, cx, cy, facing, rot_deg, uid).

Body: one shared stick-body builder (stick_body / character) that takes the head's neck
pivot in world space (q_local = (0.38 W, 0.95 H) through local_to_world) plus a pose
dict (hip, spine curve, wrist / ankle targets with bend hints, prop states).  Flat
tapered strokes with no outline (like the heads), far limbs shade(c, 0.12), skin
mittens with thumb nubs, profile tabi / zori, 1-2 small costume props per character.

Both scene.svg (1080x1920) and poses.svg (1080x1080) are drawn only by these two rigs.
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


# =====================================================================================
# STICK-BODY RIG (shared by scene.svg and poses.svg)
# -------------------------------------------------------------------------------------
# Everything below the head is built from one pose dict in LOCAL body coordinates:
#   origin = the head's neck pivot (q_local = (0.38 W, 0.95 H) of the D head, taken to
#   world space with local_to_world, so head nods keep the neck attached),
#   +x = the direction the character faces, +y = down.
# Strict profile: near limbs use the base tone, far limbs shade(c, 0.12) behind the spine.
# Flat strokes with NO outline (the D heads have no outline), round caps / joins,
# tapered 18 px at the root -> 12 px at wrist and ankle.  Joints are bends only.
# =====================================================================================

def shade(c, a):
    c = c.lstrip('#')
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    f = 1 - a
    return '#%02X%02X%02X' % (round(r * f), round(g * f), round(b * f))


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


def ang_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


def tube(pts, ws, color):
    """Tapered flat stroke through pts (one trapezoid per segment + round caps/joins)."""
    o = [f'<g fill="{color}">']
    for i in range(len(pts) - 1):
        p0, p1 = pts[i], pts[i + 1]
        w0, w1 = ws[i], ws[i + 1]
        nx, ny = unit((-(p1[1] - p0[1]), p1[0] - p0[0]))
        poly = [(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
                (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)]
        o.append('<path d="M' + ' L'.join(pt(q) for q in poly) + ' Z"/>')
    for p, w in zip(pts, ws):
        o.append(f'<circle cx="{n(p[0])}" cy="{n(p[1])}" r="{n(w / 2)}"/>')
    o.append('</g>')
    return ''.join(o)


def ik2(root, target, a, b, hint, straight=False, max_ext=0.996):
    """Two-bone IK.  Not straight -> keeps at least ~10 deg of bend so the joint reads."""
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


def bez3(p0, p1, p2, p3, t):
    return tuple((1 - t) ** 3 * p0[i] + 3 * (1 - t) ** 2 * t * p1[i] + 3 * (1 - t) * t * t * p2[i] + t ** 3 * p3[i]
                 for i in range(2))


# ---------------------------------------------------------------- body parts
def mitten(wrist, ang, L, Wd, color, thumb_side=-1, grip=False):
    """Rounded paddle in skin colour (no outline).  Returns (mitten_svg, thumb_svg).
    The thumb nub is returned separately so it can be drawn in front of a gripped prop."""
    body = (f'<g transform="translate({pt(wrist)}) rotate({n(ang)})">'
            f'<rect x="{n(-Wd * 0.18)}" y="{n(-Wd / 2)}" width="{n(L + Wd * 0.18)}" height="{n(Wd)}" '
            f'rx="{n(Wd / 2)}" fill="{color}"/></g>')
    if grip:
        cx, cy = L * 0.50, thumb_side * Wd * 0.34
        rx, ry = Wd * 0.40, Wd * 0.32
    else:
        cx, cy = L * 0.30, thumb_side * Wd * 0.50
        rx, ry = Wd * 0.34, Wd * 0.26
    thumb = (f'<g transform="translate({pt(wrist)}) rotate({n(ang)})">'
             f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{color}" '
             f'transform="rotate({n(-20 * thumb_side)},{n(cx)},{n(cy)})"/></g>')
    return body, thumb


def foot_shape(ankle, ang, fl, ah, color):
    """Profile foot: heel behind the ankle, rounded toe forward, flat sole at +ah."""
    verts = [(-0.30 * fl, -7), (0.14 * fl, -7), (0.60 * fl, ah * 0.30), (0.72 * fl, ah), (-0.30 * fl, ah)]
    d = closed_rounded(verts, [7, 9, 12, 4, 6])
    return f'<path transform="translate({pt(ankle)}) rotate({n(ang)})" d="{d}" fill="{color}"/>'


def foot_svg(kind, ankle, ang, fl, ah, limb, shin_dir, leg_w):
    o = []
    if kind == 'tabi':      # Sol: INK sole wedge + PALE sock band (as in the original sol_body)
        o.append(foot_shape(ankle, ang, fl, ah, INK))
        a = ang_of(shin_dir) - 90
        c = add(ankle, mul(shin_dir, -9))
        o.append(f'<rect transform="translate({pt(c)}) rotate({n(a)})" x="{n(-(leg_w + 12) / 2)}" y="-7" '
                 f'width="{n(leg_w + 12)}" height="14" rx="6" fill="{PALE}"/>')
    else:                   # Snoot: black tabi on a cream zori with a terracotta thong
        zd = closed_rounded([(-0.36 * fl, ah - 1), (0.80 * fl, ah - 1), (0.80 * fl, ah + 11), (-0.36 * fl, ah + 11)], 5)
        o.append(f'<path transform="translate({pt(ankle)}) rotate({n(ang)})" d="{zd}" fill="{WOOD_D}"/>')
        zd2 = closed_rounded([(-0.36 * fl, ah - 1), (0.80 * fl, ah - 1), (0.80 * fl, ah + 5), (-0.36 * fl, ah + 5)], 3)
        o.append(f'<path transform="translate({pt(ankle)}) rotate({n(ang)})" d="{zd2}" fill="{ZORI}"/>')
        o.append(foot_shape(ankle, ang, fl, ah, INK))
        th = f"M{n(0.50 * fl)},{n(ah * 0.25)} L{n(0.12 * fl)},{n(ah - 2)}"
        o.append(f'<path transform="translate({pt(ankle)}) rotate({n(ang)})" d="{th}" stroke="{TERRA}" '
                 f'stroke-width="6" stroke-linecap="round" fill="none"/>')
    return ''.join(o)


def broom_svg(a, b, fan_len, k=1.0):
    """Broom from handle end a to bristle tip b: 16 px WOOD handle, BRASS fan, INK bands."""
    L = math.dist(a, b)
    ang = ang_of(sub(b, a))
    Ls = L - fan_len
    w0, w1 = 30 * k, 86 * k
    o = [f'<g transform="translate({pt(a)}) rotate({n(ang)})">']
    o.append(f'<rect x="0" y="{n(-8 * k)}" width="{n(Ls + 10)}" height="{n(16 * k)}" rx="{n(8 * k)}" fill="{WOOD}"/>')
    o.append(f'<rect x="-3" y="{n(-10 * k)}" width="{n(22 * k)}" height="{n(20 * k)}" rx="{n(6 * k)}" fill="{INK}"/>')
    fan = closed_rounded([(Ls, -w0 / 2), (L, -w1 / 2), (L, w1 / 2), (Ls, w0 / 2)], [6, 3, 3, 6])
    o.append(f'<path d="{fan}" fill="{BRASS}"/>')
    for f in (0.16, 0.36):
        x = Ls + fan_len * f
        w = w0 + (w1 - w0) * f
        o.append(f'<rect x="{n(x)}" y="{n(-w / 2 - 1)}" width="{n(9 * k)}" height="{n(w + 2)}" fill="{INK}"/>')
    for i in range(-3, 4):
        o.append(f'<path d="M{n(Ls + fan_len * 0.50)},{n(i * 4.5 * k)} L{n(L - 5)},{n(i * 11 * k)}" '
                 f'stroke="#A88536" stroke-width="3" stroke-linecap="round"/>')
    o.append('</g>')
    return ''.join(o)


def body_dims(HU):
    return dict(HU=HU, neck=0.06 * HU, sh=0.15 * HU, thigh=0.64 * HU, shin=0.61 * HU,
                uarm=0.55 * HU, farm=0.52 * HU, mit=0.12 * HU, mitw=0.072 * HU, foot=0.185 * HU, ah=0.05 * HU)


LOOK_SOL = dict(limb=DUSK_D, skin=SKIN_SOL, feet='tabi', props=('apron', 'collar'))
LOOK_SNOOT = dict(limb=INK, skin=SKIN_SNOOT, feet='zori', props=('tasuki', 'belt'))


def stick_body(anchor, facing, pose, look, HU, hidden=12, w_root=18, w_tip=12, w_spine=17):
    """Returns (layers, joints).  layers: dict of SVG strings already placed in world space.
    pose (local coords, +x = facing):
      hip=(x,y); c1, c2 = spine control x-offsets (c1<0: rounded upper back / hunch)
      arm_n / arm_f: dict(w=(x,y) wrist target | grip=t on the broom, bend=(hx,hy) hint,
                          straight=bool, hand=deg override, thumb=+-1)
      leg_n / leg_f: dict(a=(x,y) ankle target, bend=(hx,hy), straight=bool, foot=deg)
      broom: dict(a=handle end, b=bristle tip, layer='front'|'behind')
      apron=deg swing, apron_len=fraction of HU, tails=deg lag, tie=deg lag
    """
    D = body_dims(HU)
    limb = look['limb']
    far = shade(limb, 0.12)
    skin = look['skin']
    T = f'translate({n(anchor[0])},{n(anchor[1])}) scale({facing},1)'
    A = (0.0, 0.0)
    H = pose['hip']
    c1 = (pose.get('c1', 0), H[1] * 0.30)
    c2 = (H[0] + pose.get('c2', 0), H[1] * 0.68)
    # sample spine, arc length from the anchor
    samp = [bez3(A, c1, c2, H, i / 200) for i in range(201)]
    acc = [0.0]
    for i in range(1, len(samp)):
        acc.append(acc[-1] + math.dist(samp[i - 1], samp[i]))

    def at_len(s):
        for i in range(1, len(acc)):
            if acc[i] >= s:
                t = (s - acc[i - 1]) / max(1e-6, acc[i] - acc[i - 1])
                return lerp(samp[i - 1], samp[i], t), i
        return samp[-1], len(samp) - 1

    neck_base, i_nb = at_len(hidden + D['neck'])
    S, i_sh = at_len(hidden + D['neck'] + D['sh'])
    spine_len = acc[-1] - (hidden + D['neck'])
    joints = dict(A=A, H=H, S=S, NB=neck_base, spine_len=spine_len, D=D)

    # broom geometry first (grips hang off it)
    br = pose.get('broom')

    def shaft_pt(t):
        return lerp(br['a'], br['b'], t)

    L = {}
    # ------------------------------------------------ arms
    def arm(spec):
        if 'grip' in spec:
            g = shaft_pt(spec['grip'])
            j, w = ik2(S, g, D['uarm'], D['farm'], spec.get('bend', (-1, 0)), spec.get('straight', False))
            fd = unit(sub(w, j))
            g2 = add(g, mul(fd, -D['mit'] * 0.42))
            j, w = ik2(S, g2, D['uarm'], D['farm'], spec.get('bend', (-1, 0)), spec.get('straight', False))
            return j, w, g
        j, w = ik2(S, spec['w'], D['uarm'], D['farm'], spec.get('bend', (-1, 0)), spec.get('straight', False))
        return j, w, None

    arms = {}
    for key in ('arm_f', 'arm_n'):
        spec = pose[key]
        j, w, g = arm(spec)
        col = far if key == 'arm_f' else limb
        wm = (w_root + w_tip) / 2
        s = tube([S, j, w], [w_root, wm, w_tip], col)
        hang = spec.get('hand', ang_of(sub(w, j)))
        gripping = 'grip' in spec or spec.get('fist')
        mb, mt = mitten(w, hang, D['mit'] * (1.08 if gripping else 1.0), D['mitw'] * (1.22 if gripping else 0.95),
                        shade(skin, 0.12) if key == 'arm_f' else skin,
                        spec.get('thumb', -1), grip=('grip' in spec) or spec.get('fist', False))
        arms[key] = (s, mb, mt)
        joints[key] = (j, w)
    # ------------------------------------------------ legs
    legs = {}
    for key in ('leg_f', 'leg_n'):
        spec = pose[key]
        j, a = ik2(H, spec['a'], D['thigh'], D['shin'], spec.get('bend', (1, 0)), spec.get('straight', False))
        col = far if key == 'leg_f' else limb
        wm = (w_root + w_tip) / 2
        s = tube([H, j, a], [w_root, wm, w_tip], col)
        shin_dir = unit(sub(a, j))
        f = foot_svg(look['feet'], a, spec.get('foot', 0), D['foot'], D['ah'], col, shin_dir, w_tip)
        legs[key] = s + f
        joints[key] = (j, a)
    # ------------------------------------------------ spine + neck
    sd = f"M{pt(H)} C{pt(c2)} {pt(c1)} {pt(A)}"
    spine = f'<path d="{sd}" fill="none" stroke="{limb}" stroke-width="{w_spine}" stroke-linecap="round" stroke-linejoin="round"/>'
    neck_pts = samp[:i_nb + 1]
    nd = 'M' + ' L'.join(pt(q) for q in neck_pts)
    spine += f'<path d="{nd}" fill="none" stroke="{skin}" stroke-width="{w_spine}" stroke-linecap="round" stroke-linejoin="round"/>'

    # spine tangent near shoulder / hip
    def tangent(i):
        i0, i1 = max(0, i - 3), min(len(samp) - 1, i + 3)
        return unit(sub(samp[i1], samp[i0]))   # pointing down the spine

    back = []
    front = []
    props = look['props']
    if 'apron' in props:
        # narrow trapezoid flag hung from the front of the hip point; swings as a whole
        sw = pose.get('apron', 0)
        Lp = pose.get('apron_len', 0.60) * HU
        root = add(H, (16, -28))
        wt, wb = 46, 70

        def ap(x, y):
            return add(root, rotv((x, y), -sw))
        t0, t1 = ap(-wt / 2, 0), ap(wt / 2, 0)
        b0, b1 = ap(-wt / 2 - 6, Lp), ap(wb - wt / 2 - 6, Lp)
        ad = closed_rounded([t0, t1, b1, b0], [4, 6, 8, 8])
        tie = pose.get('tie', 0)
        bk = add(H, (-16, -30))
        bow = []
        bow.append(f'<path d="M{pt(add(H, (-2, -30)))} L{pt(bk)}" stroke="{SAGE}" stroke-width="8" stroke-linecap="round"/>')
        for dl, ln in ((-8, 0.17), (10, 0.14)):
            e = add(bk, rotv((-6, ln * HU), -tie + dl))
            bow.append(f'<path d="M{pt(bk)} L{pt(e)}" stroke="{SAGE_D}" stroke-width="8" stroke-linecap="round"/>')
        bow.append(f'<ellipse cx="{n(bk[0] - 10)}" cy="{n(bk[1] - 2)}" rx="12" ry="8" fill="{SAGE}" transform="rotate(-20,{n(bk[0] - 10)},{n(bk[1] - 2)})"/>')
        back.append(''.join(bow))
        front.append(f'<path d="{ad}" fill="{SAGE}"/>')
        m0 = lerp(t0, b0, 0.42)
        m1 = lerp(t1, b1, 0.42)
        front.append(f'<path d="M{pt(lerp(m0, m1, 0.18))} L{pt(lerp(m0, m1, 0.82))}" stroke="{SAGE_D}" stroke-width="5" stroke-linecap="round"/>')
    if 'collar' in props:
        tg = tangent(i_nb)
        nrm = (-tg[1], tg[0])
        if nrm[0] < 0:
            nrm = (-nrm[0], -nrm[1])
        vb = add(neck_base, add(mul(nrm, -15), mul(tg, -4)))     # back of the neck
        vf = add(neck_base, add(mul(nrm, 15), mul(tg, -2)))      # front of the neck
        vt = add(S, add(mul(nrm, 12), mul(tg, 6)))               # V point on the chest
        front.append(f'<path d="M{pt(add(vf, mul(nrm, 3)))} L{pt(add(vt, mul(nrm, 2)))}" stroke="{PALE}" stroke-width="15" stroke-linecap="round"/>')
        front.append(f'<path d="M{pt(vb)} L{pt(vt)} L{pt(vf)}" fill="none" stroke="{DUSK}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>')
    if 'tasuki' in props:
        p_mid, _ = at_len(hidden + D['neck'] + D['sh'] + 0.36 * HU)
        # cord crossed on the spine: back strand (behind, shaded) + front strand
        q, _ = at_len(hidden + D['neck'] + D['sh'] + 0.13 * HU)
        back.append(f'<path d="M{pt(add(q, (30, -30)))} L{pt(add(q, (-30, 30)))}" stroke="{shade(PALE, 0.22)}" '
                    f'stroke-width="8" stroke-linecap="round"/>')
        front.append(f'<path d="M{pt(add(q, (-32, -26)))} L{pt(add(q, (34, 32)))}" stroke="{PALE}" stroke-width="9" stroke-linecap="round"/>')
    if 'belt' in props:
        kn = add(H, (16, -22))
        lag = pose.get('tails', 0)
        for dl, ln in ((0, 0.34), (16, 0.28)):
            e = add(kn, rotv((0, ln * HU), -lag - dl))
            m = lerp(kn, e, 0.55)
            m = add(m, rotv((7, 0), -lag))
            front.append(tube([kn, m, e], [14, 13, 10], INK))
        front.append(f'<path d="M{pt(add(H, (-22, -30)))} L{pt(add(H, (24, -28)))}" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>')
        front.append(f'<rect x="{n(kn[0] - 13)}" y="{n(kn[1] - 11)}" width="26" height="22" rx="7" fill="{INK}"/>')
        front.append(f'<path d="M{pt(add(kn, (-7, -3)))} L{pt(add(kn, (7, 3)))}" stroke="#3A342D" stroke-width="3" stroke-linecap="round"/>')

    # broom
    prop_svg = ''
    if br:
        prop_svg = broom_svg(br['a'], br['b'], br.get('fan', 0.20 * HU), br.get('k', 1.0))

    def g(s):
        return f'<g transform="{T}">{s}</g>' if s else ''

    L['far_leg'] = g(legs['leg_f'])
    L['far_arm'] = g(arms['arm_f'][0] + arms['arm_f'][1])
    L['far_thumb'] = g(arms['arm_f'][2])
    L['spine'] = g(spine)
    L['back_props'] = g(''.join(back))
    L['front_props'] = g(''.join(front))
    L['near_leg'] = g(legs['leg_n'])
    L['near_arm'] = g(arms['arm_n'][0] + arms['arm_n'][1])
    L['near_thumb'] = g(arms['arm_n'][2])
    L['prop'] = g(prop_svg)
    L['T'] = T
    joints['world'] = lambda q: (anchor[0] + facing * q[0], anchor[1] + q[1])
    return L, joints


def neck_anchor(p, cx, cy, facing, rot_deg):
    return local_to_world(p, (0.38 * p['W'], 0.95 * p['H']), cx, cy, facing, rot_deg)


def character(p, cx, cy, facing, rot_deg, uid, pose, look, HU, shadow=None, marks='', **kw):
    """Layer order: cast shadow, far leg, far arm, spine/neck, back props, head (rig),
    front props, near leg, near arm, hand prop with thumb nubs, marks."""
    anc = neck_anchor(p, cx, cy, facing, rot_deg)
    L, J = stick_body(anc, facing, pose, look, HU, **kw)
    behind = pose.get('broom', {}).get('layer', 'front') == 'behind'
    o = []
    if shadow:
        o.append(shadow)
    o.append(L['far_leg'])
    o.append(L['far_arm'])
    if behind:
        o.append(L['prop'])
        o.append(L['far_thumb'])
    o.append(L['spine'])
    o.append(L['back_props'])
    o.append(head(p, cx, cy, facing, rot_deg, uid))
    o.append(L['front_props'])
    o.append(L['near_leg'])
    o.append(L['near_arm'])
    if not behind:
        o.append(L['prop'])
        o.append(L['far_thumb'])
    o.append(L['near_thumb'])
    o.append(marks)
    return ''.join(o), J


# ---------------------------------------------------------------- mooks: wooden dummy
def dummy_svg(piv, ang, s=1.0, cord=26, arms=((-1, 208, 96), (1, -28, 96))):
    """Faceless capsule log on a cord from a brass ring.  piv = bottom of the ring.
    ang = swing angle (0 hangs straight down, + swings the log to the right)."""
    o = [f'<g transform="translate({pt(piv)}) rotate({n(-ang)}) scale({n(s)})">']
    o.append(f'<path d="M0,-4 L0,{cord + 8}" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>')
    y0 = cord
    # dowel peg arms (22 px), behind the log
    for sx, phi, ry in arms:
        r0 = (sx * 50, y0 + ry)
        e = add(r0, (74 * math.cos(math.radians(phi)), 74 * math.sin(math.radians(phi))))
        o.append(f'<path d="M{pt(r0)} L{pt(e)}" stroke="{WOOD_D}" stroke-width="{n(max(24, 22.5 / s))}" stroke-linecap="round"/>')
    o.append(f'<rect x="-70" y="{y0}" width="140" height="300" rx="70" fill="{WOOD}"/>')
    o.append(f'<rect x="-70" y="{y0 + 70}" width="140" height="12" fill="{WOOD_D}"/>')
    o.append(f'<rect x="-70" y="{y0 + 236}" width="140" height="10" fill="{WOOD_D}"/>')
    for gx, a0, a1 in ((-34, 104, 214), (6, 120, 226), (34, 98, 182)):
        o.append(f'<path d="M{gx},{y0 + a0} Q{gx + 9},{y0 + (a0 + a1) / 2} {gx},{y0 + a1}" fill="none" '
                 f'stroke="{WOOD_D}" stroke-width="5" stroke-linecap="round"/>')
    o.append(f'<circle cx="0" cy="{y0 + 4}" r="10" fill="none" stroke="{BRASS}" stroke-width="6"/>')
    o.append('</g>')
    return ''.join(o)


def arcs(cx, cy, radii, a0, a1, color, w=5):
    """Concentric motion arcs around (cx,cy); angles in degrees, 0 = straight down, + = to the right."""
    o = []
    for r in radii:
        p0 = (cx + r * math.sin(math.radians(a0)), cy + r * math.cos(math.radians(a0)))
        p1 = (cx + r * math.sin(math.radians(a1)), cy + r * math.cos(math.radians(a1)))
        sweep = 0 if a1 > a0 else 1
        large = 1 if abs(a1 - a0) > 180 else 0
        o.append(f'<path d="M{pt(p0)} A{n(r)},{n(r)} 0 {large} {sweep} {pt(p1)}" fill="none" stroke="{color}" '
                 f'stroke-width="{w}" stroke-linecap="round"/>')
    return ''.join(o)


def whoosh(pts_list, color, w=5):
    o = []
    for pts in pts_list:
        if len(pts) == 3:
            o.append(f'<path d="M{pt(pts[0])} Q{pt(pts[1])} {pt(pts[2])}" fill="none" stroke="{color}" '
                     f'stroke-width="{w}" stroke-linecap="round"/>')
        else:
            o.append(f'<path d="M{pt(pts[0])} L{pt(pts[1])}" fill="none" stroke="{color}" '
                     f'stroke-width="{w}" stroke-linecap="round"/>')
    return ''.join(o)


SAGE_D = '#748B70'
ZORI = '#E9DCC1'


# =====================================================================================
# SCENE (1080 x 1920): rooftop training deck at night, "faces glare, bodies fight"
# =====================================================================================
FLOOR = 1605          # sole line
TIP_Y = 742           # nose tips (10 px apart at x 535 / 545)


def sol_scene_face():
    return make_face(W=300, H=340, skin=SKIN_SOL, hair='topknot', nl=90, nh=76,
                     eye=dict(w=110, h=70, open=0.42, tilt=0, px=0.22, py=0.05, pr=12),
                     brow=dict(len=92, th=18, raise_=-10, tilt=-4, dx=4),
                     mouth='a', front=40)


def snoot_scene_face():
    return make_face(W=300, H=340, skin=SKIN_SNOOT, hair='sweep', tie=TERRA, nose='ski', nl=104, nh=76,
                     nose_state='flare', nose_up=8, nose_always_up=True,
                     eye=dict(w=110, h=70, open=0.25, tilt=8, px=0.10, pr=12),
                     brow=dict(len=96, th=18, raise_=-30, tilt=25, dx=8),
                     mouth='d', marks=['shake', 'snort'], front=40)


def scene_svg():
    Wc, Hc = 1080, 1920
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wc}" height="{Hc}" viewBox="0 0 {Wc} {Hc}">']
    o.append(f'<rect width="{Wc}" height="{Hc}" fill="{DUSK}"/>')
    o.append(f'<rect y="975" width="{Wc}" height="230" fill="{HAZE}"/>')
    # distant roofs only at the sides (never behind the bodies: value fix)
    roofs = ("M0,1205 L0,1112 L40,1112 L30,1098 Q78,1090 118,1072 Q150,1086 176,1094 L168,1104 L188,1104 L188,1205 Z "
             "M1080,1205 L1080,1108 L1046,1108 L1054,1096 Q1004,1088 964,1070 Q930,1086 900,1094 L908,1104 L890,1104 L890,1205 Z")
    o.append(f'<path d="{roofs}" fill="{ROOF}"/>')
    MOON_C, MOON_R = (540, 1150), 450
    o.append(f'<circle cx="{MOON_C[0]}" cy="{MOON_C[1]}" r="{MOON_R}" fill="{MOON}"/>')
    # deck floor
    o.append(f'<rect y="1196" width="{Wc}" height="430" fill="{SAND}"/>')
    for y in (1222, 1258, 1306, 1370, 1452, 1556):
        o.append(f'<rect y="{y}" width="{Wc}" height="4" fill="{PLANK}"/>')
    o.append(f'<rect y="1196" width="{Wc}" height="12" fill="{PLANK}"/>')
    o.append(f'<rect y="1626" width="{Wc}" height="{Hc - 1626}" fill="{FLOOR_D}"/>')
    o.append(f'<rect y="1626" width="{Wc}" height="10" fill="{shade(FLOOR_D, 0.12)}"/>')
    # frame: eave beam + brackets
    o.append(f'<rect y="230" width="{Wc}" height="34" fill="{INK}"/>')
    o.append(f'<path d="M44,264 L110,264 Q60,290 44,330 Z" fill="{INK}"/>')
    o.append(f'<path d="M1036,264 L970,264 Q1020,290 1036,330 Z" fill="{INK}"/>')
    RY = 330
    o.append(f'<rect x="44" y="{RY - 11}" width="992" height="22" fill="{INK}"/>')
    o.append(f'<circle cx="300" cy="{RY + 32}" r="19" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    for rx in (150, 780, 920):
        o.append(f'<circle cx="{rx}" cy="{RY + 32}" r="19" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    # ---- heads (fixed, nose to nose)
    sol = sol_scene_face()
    snoot = snoot_scene_face()
    st = nose_tip(sol)
    sol_cx = 535 - (st[0] - sol['W'] / 2)
    sol_cy = TIP_Y - (st[1] - sol['H'] / 2)
    sn_rot = 4
    nt = nose_tip(snoot)
    wx, wy = local_to_world(snoot, nt, 0, 0, -1, sn_rot)
    sn_cx = 545 - wx
    sn_cy = TIP_Y + 4 - wy
    HU = 340

    # ---- the dummy: kicked by Snoot, parried by Sol, flipped up and clicked back into its
    #      ring at top centre -- it now hangs right above the glare, still settling
    RY = 330
    piv = (540, RY + 51)
    dang = 4
    o.append(dummy_svg(piv, dang, 0.94, cord=22))
    o.append(f'<circle cx="540" cy="{RY + 32}" r="19" fill="none" stroke="{BRASS}" stroke-width="7"/>')
    for sgn in (-1, 1):
        o.append(arcs(piv[0], piv[1], (150, 178), sgn * 22, sgn * 40, PALE, 5))
    o.append(f'<path d="{star4(540, RY + 32, 52, 12, 0)}" fill="{PALE}"/>')
    o.append(f'<path d="{star4(540, RY + 32, 27, 6, 45)}" fill="{PALE}"/>')

    # ---- SOL: hunched, feet planted, both mittens behind his back swing the broom round;
    #      its bristles come out under the glare where the dummy was
    a_s = neck_anchor(sol, sol_cx, sol_cy, 1, 0)
    Fy = FLOOR - a_s[1]
    ah = 0.05 * HU

    def Ls(w):            # world -> Sol local
        return (w[0] - a_s[0], w[1] - a_s[1])
    sol_pose = dict(
        hip=(-22, 324), c1=-50, c2=-10,
        leg_f=dict(a=(-80, Fy - ah), bend=(1, 0), foot=0),
        leg_n=dict(a=(22, Fy - ah), bend=(1, 0), foot=0),
        broom=dict(a=Ls((112, 1266)), b=Ls((516, 1090)), fan=96, layer='behind'),
        arm_n=dict(grip=0.26, bend=(-1, 0.3), thumb=-1),
        arm_f=dict(grip=0.17, bend=(-1, 0.3), thumb=-1),
        apron=10, tie=-20,
    )
    sol_shadow = f'<ellipse cx="{n(a_s[0] - 30)}" cy="{FLOOR + 4}" rx="150" ry="13" fill="{PLANK}"/>'
    s_svg, sJ = character(sol, sol_cx, sol_cy, 1, 0, 'sol', sol_pose, LOOK_SOL, HU, shadow=sol_shadow)

    # ---- SNOOT: torso leaning back, hands clasped low behind his back, rear leg dead
    #      straight in a high side kick under the glare
    a_n = neck_anchor(snoot, sn_cx, sn_cy, -1, sn_rot)
    Fy2 = FLOOR - a_n[1]

    def Ln(w):            # world -> Snoot local (facing left)
        return (a_n[0] - w[0], w[1] - a_n[1])
    hip_n = Ln((936, 1180))
    kick_dir = unit(sub(Ln((580, 990)), hip_n))
    sn_pose = dict(
        hip=hip_n, c1=-34, c2=-14,
        leg_f=dict(a=Ln((912, FLOOR - ah)), bend=(1, 0), foot=0),
        leg_n=dict(a=add(hip_n, mul(kick_dir, 500)), straight=True, foot=ang_of(kick_dir) - 90),
        arm_f=dict(w=add(hip_n, (-14, 104)), bend=(-1, 0), hand=120, thumb=1, fist=True),
        arm_n=dict(w=add(hip_n, (-24, 98)), bend=(-1, 0), hand=110, thumb=1, fist=True),
        tails=-46,
    )
    sn_shadow = f'<ellipse cx="{n(a_n[0] - 70)}" cy="{FLOOR + 4}" rx="100" ry="12" fill="{PLANK}"/>'
    n_svg, nJ = character(snoot, sn_cx, sn_cy, -1, sn_rot, 'snoot', sn_pose, LOOK_SNOOT, HU, shadow=sn_shadow)

    # motion arcs: the kick swept up from below (arcs trail under the straight leg);
    # the broom swung up from behind (arcs trail under the bristles)
    mk = []
    # kick: straight thrust lines parallel to the leg, on its upper side, behind the foot
    hipw = nJ['world'](hip_n)
    footw = nJ['world'](nJ['leg_n'][1])
    u = unit(sub(footw, hipw))
    nv = (u[1], -u[0])
    if nv[1] > 0:
        nv = (-nv[0], -nv[1])
    for off, d0, d1 in ((30, 70, 190), (58, 110, 200)):
        p0 = add(footw, add(mul(u, -d0), mul(nv, off)))
        p1 = add(footw, add(mul(u, -d1), mul(nv, off)))
        mk.append(f'<path d="M{pt(p0)} L{pt(p1)}" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>')
    # broom: the bristles swung up from behind -> two short arcs trailing under the fan
    gw = sJ['world'](sJ['arm_n'][1])
    tipw = sJ['world'](sol_pose['broom']['b'])
    R2 = math.dist(gw, tipw)
    ba = math.degrees(math.atan2(tipw[1] - gw[1], tipw[0] - gw[0]))
    for r, s0, s1 in ((R2 - 10, 7, 19), (R2 - 44, 8, 17)):
        a0, a1 = math.radians(ba + s0), math.radians(ba + s1)
        p0 = (gw[0] + r * math.cos(a0), gw[1] + r * math.sin(a0))
        p1 = (gw[0] + r * math.cos(a1), gw[1] + r * math.sin(a1))
        mk.append(f'<path d="M{pt(p0)} A{n(r)},{n(r)} 0 0 1 {pt(p1)}" fill="none" stroke="{DUSK_D}" stroke-width="5" stroke-linecap="round"/>')

    o.append(s_svg)
    o.append(n_svg)
    o.append(''.join(mk))
    o.append(f'<rect x="0" y="230" width="44" height="1396" fill="{INK}"/>')
    o.append(f'<rect x="1036" y="230" width="44" height="1396" fill="{INK}"/>')
    o.append('</svg>')
    for nm, JJ in (('sol', sJ), ('snoot', nJ)):
        for k in ('arm_n', 'arm_f', 'leg_n', 'leg_f'):
            e = JJ['world'](JJ[k][0])
            dm = math.dist(e, MOON_C) - MOON_R
            print(nm, k, 'joint', tuple(round(v) for v in e), 'outside moon by' if dm > 0 else 'inside moon', round(abs(dm)))
    info = dict(sol=(round(sol_cx), round(sol_cy)), snoot=(round(sn_cx), round(sn_cy)),
                sol_spine=round(sJ['spine_len']), snoot_spine=round(nJ['spine_len']),
                sol_anchor=tuple(round(v) for v in a_s), snoot_anchor=tuple(round(v) for v in a_n))
    return '\n'.join(o), info


# =====================================================================================
# POSES SHEET (1080 x 1080): Sol x3 -- ready stance, behind-the-back parry, back leap
# =====================================================================================
def sol_sheet_face(**kw):
    s = 0.95
    base = dict(W=228, H=276, skin=SKIN_SOL, hair='topknot', nl=72, nh=61,
                eye=dict(kind='almond', w=95, h=61, open=0.7, tilt=0, px=0.16, py=0.0, pr=11, ghosts=False, d=99),
                brow=dict(len=76, th=16, raise_=0, tilt=0, dx=0, arch=0), mouth='a', jaw=0, marks=[], front=34)
    for k, v in kw.items():
        if k in ('eye', 'brow'):
            base[k] = dict(base[k], **v)
        else:
            base[k] = v
    return make_face(**base)


def poses_svg():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">']
    o.append(f'<rect width="1080" height="1080" fill="{SAND}"/>')
    FL = 978
    HU = 276
    ah = 0.05 * HU
    for cx, cy, r in ((220, 430, 170), (620, 430, 170), (912, 400, 156)):
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PALE}"/>')
    o.append(f'<rect y="{FL - 2}" width="1080" height="{1080 - FL + 2}" fill="{PLANK}"/>')
    for y in (FL + 30, FL + 66):
        o.append(f'<rect y="{y}" width="1080" height="4" fill="{FLOOR_D}"/>')
    o.append(f'<rect y="{FL - 2}" width="1080" height="8" fill="{FLOOR_D}"/>')
    kw = dict(w_root=17, w_tip=11, w_spine=16, hidden=10)

    # (1) READY STANCE: broom upright like a staff, other mitten on the hip
    p1 = sol_sheet_face()
    c1 = (194, 240)
    a1 = neck_anchor(p1, c1[0], c1[1], 1, 0)
    Fy = FL - a1[1]
    pose1 = dict(
        hip=(-12, 262), c1=-24, c2=-4,
        leg_f=dict(a=(-30, Fy - ah), bend=(1, 0), foot=0),
        leg_n=dict(a=(22, Fy - ah), bend=(1, 0), foot=0),
        broom=dict(a=(126, 128), b=(126, Fy + 2), fan=86, layer='front', k=0.9),
        arm_n=dict(grip=0.30, bend=(0.2, 1), thumb=-1),
        arm_f=dict(w=(-34, 266), bend=(-1, -0.2), hand=40, thumb=1, fist=True),
        apron=0, tie=0,
    )
    sh1 = f'<ellipse cx="{n(a1[0] + 20)}" cy="{FL + 2}" rx="120" ry="10" fill="{FLOOR_D}"/>'
    s1, J1 = character(p1, c1[0], c1[1], 1, 0, 'p1', pose1, LOOK_SOL, HU, shadow=sh1, **kw)

    # (2) SIGNATURE: BEHIND-THE-BACK PARRY (smug wink).  Head forward and still; both
    #     mittens swing the broom round behind his back into a dummy's peg arm.
    p2 = sol_sheet_face(eye=dict(kind='arc'), brow=dict(raise_=14, tilt=-8, arch=6), nose_state='up', mouth='c')
    c2 = (616, 240)
    r2 = -10
    a2 = neck_anchor(p2, c2[0], c2[1], 1, r2)
    Fy = FL - a2[1]

    def L2(w):
        return (w[0] - a2[0], w[1] - a2[1])
    tip2 = (424, 424)
    hands = (518, 662)
    bdir = unit(sub(tip2, hands))
    hand_end = add(hands, mul(bdir, -150))
    pose2 = dict(
        hip=(-26, 258), c1=-4, c2=14,
        leg_f=dict(a=(-6, Fy - ah), bend=(1, 0), foot=0),
        leg_n=dict(a=(-188, 318), bend=(1, 0.5), foot=-76),
        broom=dict(a=L2(hand_end), b=L2(tip2), fan=86, layer='behind', k=0.9),
        arm_n=dict(grip=150 / 440, bend=(-1, 0.4), thumb=-1),
        arm_f=dict(grip=196 / 440, bend=(-1, 0.4), thumb=-1),
        apron=54, tie=-56,
    )
    sh2 = f'<ellipse cx="{n(a2[0] + 10)}" cy="{FL + 2}" rx="90" ry="10" fill="{FLOOR_D}"/>'
    s2, J2 = character(p2, c2[0], c2[1], 1, r2, 'p2', pose2, LOOK_SOL, HU, shadow=sh2, **kw)
    # the dummy hanging behind him; its peg arm meets the bristles (glint)
    dpiv = (444, -12)
    o.append(dummy_svg(dpiv, -4, 0.58, cord=330, arms=((-1, 200, 100), (1, 112, 262))))

    # (3) BIG REACTION: BACK LEAP (surprised).  Both feet off the floor, knees up,
    #     broom clutched upright to the chest, apron flipped up.
    p3 = sol_sheet_face(eye=dict(kind='circle', d=99, px=0.0, py=0.0, pr=7), brow=dict(raise_=38, tilt=-12),
                        mouth='b', jaw=25, marks=['emanata'])
    c3 = (876, 184)
    r3 = -6
    a3 = neck_anchor(p3, c3[0], c3[1], 1, r3)
    pose3 = dict(
        hip=(14, 246), c1=-58, c2=-40,
        leg_f=dict(a=(56, 400), bend=(1, -1), foot=30),
        leg_n=dict(a=(100, 414), bend=(1, -1), foot=22),
        broom=dict(a=(104, 118), b=(124, 568), fan=86, layer='front', k=0.9),
        arm_n=dict(grip=0.17, bend=(0.3, 1), thumb=-1),
        arm_f=dict(grip=0.05, bend=(0.3, 1), thumb=-1),
        apron=114, apron_len=0.42, tie=-80,
    )
    sh3 = f'<ellipse cx="{n(a3[0] + 30)}" cy="{FL + 2}" rx="64" ry="8" fill="{FLOOR_D}"/>'
    s3, J3 = character(p3, c3[0], c3[1], 1, r3, 'p3', pose3, LOOK_SOL, HU, shadow=sh3, **kw)
    # speed lines on the side he is leaving (front), plus a dust puff where he took off
    sp = []
    for y, x0, x1 in ((790, 1010, 1064), (840, 1020, 1070), (890, 1006, 1056)):
        sp.append(f'<path d="M{x0},{y} L{x1},{y}" stroke="{DUSK_D}" stroke-width="5" stroke-linecap="round"/>')
    for cx, cy, r in ((956, 962, 16), (982, 968, 11), (932, 968, 10)):
        sp.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{FLOOR_D}"/>')

    o.append(s1)
    o.append(s2)
    gl = add(tip2, (2, -12))
    o.append(f'<path d="{star4(gl[0], gl[1], 40, 9, 0)}" fill="{PALE}"/>')
    o.append(f'<path d="{star4(gl[0], gl[1], 21, 5, 45)}" fill="{INK}"/>')
    o.append(s3)
    o.append(''.join(sp))
    o.append('</svg>')
    info = dict(p1=round(J1['spine_len']), p2=round(J2['spine_len']), p3=round(J3['spine_len']),
                a1=tuple(round(v) for v in a1), a2=tuple(round(v) for v in a2))
    return '\n'.join(o), info


if __name__ == '__main__':
    s, info = scene_svg()
    with open(os.path.join(HERE, 'scene.svg'), 'w') as f:
        f.write(s)
    s2, info2 = poses_svg()
    with open(os.path.join(HERE, 'poses.svg'), 'w') as f:
        f.write(s2)
    print('scene', info)
    print('poses', info2)
