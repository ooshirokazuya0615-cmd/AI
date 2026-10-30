#!/usr/bin/env python3
"""INK & VERMILION / 墨と朱 -- NEVER DROP still (1080x1920 SVG).
Everything is code-drawn: brush strokes are generated polygons with seeded edge noise, a static per-stroke
ink-bleed filter (seeded wobble -> blur 1.2 -> alpha table threshold ~0.5) and crisp kasure (dry-brush) masks.
Usage: python3 make.py [out.svg]
"""
import math
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from pose2d import POSE, GROUND_Y  # noqa: E402,F401

W, H = 1080, 1920
PAPER = '#F1EADB'
INK0, INK1, INK2, INK3, MIST = '#141210', '#3A3733', '#6B6863', '#A6A29A', '#D8D2C4'
VERM = '#C7372F'
FIBRE = '#CFC6B2'

P = dict(
    hero_opacity=0.93,
    bleed_disp=3.0,
    bleed_halo=0.08,
    mook_x=(904, 1014, 1074),
    mook_lean=(-14, -8, -4),
    seal_x=960, seal_y=150,
    breath=False,
    glow=0.38,
)


def f(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def pts_d(pts, close=True):
    s = 'M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in pts)
    return s + (' Z' if close else '')


class Doc:
    def __init__(self):
        self.defs = []
        self.n = 0

    def uid(self, p):
        self.n += 1
        return f'{p}{self.n}'

    def bleed(self, seed, disp=None, freq=0.07, halo=None, region=0.25):
        """static per-stroke ink bleed: seeded edge wobble -> blur 1.2 -> alpha table threshold ~0.5 (+ faint nijimi)."""
        disp = P['bleed_disp'] if disp is None else disp
        halo = P['bleed_halo'] if halo is None else halo
        fid = self.uid('bl')
        r = region
        halo_xml = ''
        if halo > 0:
            halo_xml = (f'<feGaussianBlur in="d" stdDeviation="2.6" result="h"/>'
                        f'<feComponentTransfer in="h" result="h2"><feFuncA type="linear" slope="{halo}"/></feComponentTransfer>'
                        f'<feMerge><feMergeNode in="h2"/><feMergeNode in="t"/></feMerge>')
        self.defs.append(
            f'<filter id="{fid}" x="{-r*100:.0f}%" y="{-r*100:.0f}%" width="{100+2*r*100:.0f}%" height="{100+2*r*100:.0f}%" '
            f'color-interpolation-filters="sRGB">'
            f'<feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="4" seed="{seed % 100000}" result="n"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="n" scale="{disp}" xChannelSelector="R" yChannelSelector="G" result="d"/>'
            f'<feGaussianBlur in="d" stdDeviation="1.2" result="b"/>'
            f'<feComponentTransfer in="b" result="t"><feFuncA type="table" tableValues="0 0 0 0 0 1 1 1 1 1"/></feComponentTransfer>'
            f'{halo_xml}</filter>')
        return fid


D = Doc()


# ----------------------------------------------------------------------------- geometry helpers
def bez(ctrl, t):
    p = [np.asarray(q, float) for q in ctrl]
    while len(p) > 1:
        p = [p[i] * (1 - t) + p[i + 1] * t for i in range(len(p) - 1)]
    return p[0]


def catmull(pts, n, alpha=0.5):
    """centripetal Catmull-Rom through pts (no loops at sharp knees)."""
    pts = [np.asarray(p, float) for p in pts]
    pts = [2 * pts[0] - pts[1]] + pts + [2 * pts[-1] - pts[-2]]
    seg = len(pts) - 3
    lens = [np.linalg.norm(pts[i + 2] - pts[i + 1]) for i in range(seg)]
    tot = sum(lens)
    out = []
    for i in range(seg):
        p0, p1, p2, p3 = pts[i:i + 4]

        def tj(ti, a, b):
            return ti + max(np.linalg.norm(b - a), 1e-6) ** alpha
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        m = max(3, int(n * lens[i] / tot))
        for k in range(m):
            t = t1 + (t2 - t1) * k / m
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(pts[-2])
    return np.array(out)


def sample(ctrl, n=64, kind='bez'):
    if kind == 'bez':
        return np.array([bez(ctrl, t) for t in np.linspace(0, 1, n)])
    if kind == 'cat':
        return catmull(ctrl, n)
    return np.asarray(ctrl, float)


def prof_w(prof, s):
    if s <= prof[0][0]:
        return prof[0][1]
    for (s0, w0), (s1, w1) in zip(prof, prof[1:]):
        if s <= s1:
            t = (s - s0) / (s1 - s0) if s1 > s0 else 1.0
            t = t * t * (3 - 2 * t)
            return w0 + (w1 - w0) * t
    return prof[-1][1]


def smooth_noise(rng, x, amp, freqs=(0.011, 0.023, 0.051, 0.11)):
    out = np.zeros_like(x)
    for k, fr in enumerate(freqs):
        out += amp / (1 + k * 0.8) * np.sin(2 * math.pi * fr * x + rng.uniform(0, 2 * math.pi))
    return out


def stroke(ctrl, prof, seed, kind='bez', n=72, flick=14, flick_bend=0.0, edge=0.07, blob=1.06, cap_skew=0.18,
           kasure=None, dry_from=0.6, streak_w=(0.9, 2.2), side_bias=0.0):
    """Brush stroke geometry. prof: [(s, width)] with s in [0,1] over the main path; a harai flick of `flick` px
    continues past the end along the end tangent. Returns dict(poly, streaks, bb, a, b)."""
    rng = np.random.default_rng(seed)
    C = sample(ctrl, n, kind)
    n_main = len(C)
    d = C[-1] - C[-3]
    d = d / (np.linalg.norm(d) + 1e-9)
    nd = np.array([-d[1], d[0]])
    if flick > 0:
        m = max(3, int(flick / 3))
        ext = [C[-1] + d * flick * (k / m) + nd * flick_bend * (k / m) ** 2 for k in range(1, m + 1)]
        C = np.vstack([C, ext])
    seg = np.linalg.norm(np.diff(C, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    Lm = cum[n_main - 1]
    nn = max(8, int(cum[-1] / 2.5))
    us = np.linspace(0, cum[-1], nn)
    C = np.stack([np.interp(us, cum, C[:, 0]), np.interp(us, cum, C[:, 1])], axis=1)
    cum = us
    s = cum / max(Lm, 1e-6)
    s_end = s[-1]
    w_end = prof[-1][1]
    w = np.array([prof_w(prof, si) if si <= 1 else w_end + (0.8 - w_end) * ((si - 1) / max(s_end - 1, 1e-6)) ** 0.8
                  for si in s])
    T = np.gradient(C, axis=0)
    T = T / (np.linalg.norm(T, axis=1, keepdims=True) + 1e-9)
    N = np.stack([-T[:, 1], T[:, 0]], axis=1)
    nl = smooth_noise(rng, cum, edge)
    nr = smooth_noise(rng, cum, edge)
    left = C + N * (w / 2 * (1 + nl))[:, None]
    right = C - N * (w / 2 * (1 + nr))[:, None]
    cap = []
    r0 = w[0] / 2 * blob
    ctr = C[0] + N[0] * w[0] * cap_skew * 0.5  # brush lands slightly to one side (entry press)
    for a in np.linspace(math.pi, 0, 13)[1:-1]:
        dv = N[0] * math.cos(a) - T[0] * math.sin(a) * 1.2
        cap.append(ctr + dv * r0)
    poly = list(left) + list(right[::-1]) + cap
    streaks = []
    if kasure is None:
        kasure = int(np.clip(w.max() / 2.2, 3, 16))
    span = max(s_end - dry_from, 1e-3)
    for k in range(kasure):
        v = float(np.clip(rng.normal(side_bias, 0.55), -0.95, 0.95))
        sw = rng.uniform(*streak_w)
        sc = dry_from + rng.uniform(0, 0.3) * span
        while sc < s_end + 0.02:
            u = (sc - dry_from) / span
            dash_px = rng.uniform(5, 18) * (1 + 1.6 * u)
            gap_px = rng.uniform(4, 15) * (1.5 - u)
            if u > 0.8 and rng.random() < 0.75:
                dash_px = 1e4          # tail: bristles separate and run off the end
            s1 = sc + dash_px / Lm
            if rng.random() < 0.3 + 0.65 * u:
                idx = np.where((s >= sc) & (s <= s1))[0]
                if len(idx) >= 2:
                    vv = v + rng.normal(0, 0.05)
                    sp = C[idx] + N[idx] * (w[idx] / 2 * vv)[:, None]
                    if s1 > s_end:
                        sp = np.vstack([sp, sp[-1] + d * 8])
                    streaks.append((sp, sw * rng.uniform(0.7, 1.25)))
            sc = s1 + gap_px / Lm
    allp = np.array(poly)
    bb = (allp[:, 0].min() - 14, allp[:, 1].min() - 14, allp[:, 0].max() + 14, allp[:, 1].max() + 14)
    return dict(poly=poly, streaks=streaks, bb=bb, a=C[0], b=C[-1])


def stroke_svg(g, color, seed, opacity=1.0, extra_mask=None, disp=None, halo=None, tone=None):
    """<g opacity mask=kasure><g filter=bleed><path fill=color|gradient/></g></g>"""
    fid = D.bleed(seed, disp=disp, halo=halo)
    fill = color
    if tone:  # ink drying along the stroke: wet core -> slightly paler dry tail
        gid = D.uid('g')
        a, b = g['a'], g['b']
        D.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}">'
                      f'<stop offset="0" stop-color="{color}"/><stop offset="0.62" stop-color="{color}"/>'
                      f'<stop offset="1" stop-color="{tone}"/></linearGradient>')
        fill = f'url(#{gid})'
    mask_attr = ''
    if g['streaks']:
        mid = D.uid('m')
        x0, y0, x1, y1 = g['bb']
        lines = '<g filter="url(#kr)">' + ''.join(
            f'<path d="{pts_d(sp, False)}" stroke="#000" stroke-width="{sw:.2f}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
            for sp, sw in g['streaks']) + '</g>'
        D.defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="{f(x0)}" y="{f(y0)}" width="{f(x1-x0)}" height="{f(y1-y0)}">'
                      f'<rect x="{f(x0)}" y="{f(y0)}" width="{f(x1-x0)}" height="{f(y1-y0)}" fill="#fff"/>{lines}</mask>')
        mask_attr = f' mask="url(#{mid})"'
    inner = f'<g filter="url(#{fid})"><path d="{pts_d(g["poly"])}" fill="{fill}"/></g>'
    out = f'<g opacity="{opacity}"{mask_attr}>{inner}</g>'
    if extra_mask:
        out = f'<g mask="url(#{extra_mask})">{out}</g>'
    return out


def rot(p, ang, c):
    a = math.radians(ang)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))


SEED = [100]


def nseed():
    SEED[0] += 7
    return SEED[0]


# ----------------------------------------------------------------------------- 1. paper
def layer_paper():
    D.defs.append(
        '<filter id="drift" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.0025" numOctaves="2" seed="11"/>'
        '<feColorMatrix values="3 0 0 0 -1  3 0 0 0 -1  3 0 0 0 -1  0 0 0 0 0.06"/></filter>')
    D.defs.append('<radialGradient id="glow" gradientUnits="userSpaceOnUse" cx="600" cy="430" r="560">'
                  '<stop offset="0" stop-color="#FFFDF7" stop-opacity="1"/><stop offset="1" stop-color="#FFFDF7" stop-opacity="0"/></radialGradient>')
    D.defs.append(f'<linearGradient id="groundtone" gradientUnits="userSpaceOnUse" x1="0" y1="1380" x2="0" y2="{H}">'
                  f'<stop offset="0" stop-color="{MIST}" stop-opacity="0"/><stop offset="0.45" stop-color="{MIST}" stop-opacity="0.22"/>'
                  f'<stop offset="1" stop-color="{MIST}" stop-opacity="0.32"/></linearGradient>')
    return (f'<rect width="{W}" height="{H}" fill="{PAPER}"/>'
            f'<rect width="{W}" height="{H}" fill="#fff" filter="url(#drift)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#glow)" opacity="{P["glow"]}"/>'
            f'<rect y="1380" width="{W}" height="{H-1380}" fill="url(#groundtone)"/>')


# ----------------------------------------------------------------------------- 2. far temple + pines in mist
def pine_crown(cx, cy, s, rng):
    parts = []
    pads = [(0, 0, 1.0), (-0.38, 0.45, 0.8), (0.42, 0.6, 0.72), (-0.08, 1.0, 0.92), (0.12, -0.42, 0.55)]
    for dx, dy, sc in pads:
        x, y = cx + dx * 80 * s, cy + dy * 60 * s
        rx, ry = 70 * s * sc, 18 * s * sc
        pts = []
        for a in np.linspace(0, 2 * math.pi, 28, endpoint=False):
            rr = 1 + 0.12 * math.sin(3 * a + rng.uniform(0, 6)) + rng.uniform(-0.05, 0.05)
            yy = math.sin(a) * ry * rr
            if yy > 0:
                yy *= 0.55
            pts.append((x + math.cos(a) * rx * rr, y + yy))
        parts.append(f'<path d="{pts_d(pts)}"/>')
    tr = [(cx + 6 * s, cy + 160 * s), (cx - 16 * s, cy + 95 * s), (cx + 10 * s, cy + 40 * s), (cx, cy)]
    parts.append(f'<path d="M{f(tr[0][0]-7*s)},{f(tr[0][1])} C{f(tr[1][0]-6*s)},{f(tr[1][1])} {f(tr[2][0]-4*s)},{f(tr[2][1])} {f(tr[3][0]-2*s)},{f(tr[3][1])} '
                 f'L{f(tr[3][0]+2*s)},{f(tr[3][1])} C{f(tr[2][0]+4*s)},{f(tr[2][1])} {f(tr[1][0]+6*s)},{f(tr[1][1])} {f(tr[0][0]+7*s)},{f(tr[0][1])} Z"/>')
    return ''.join(parts)


def layer_far():
    rng = np.random.default_rng(5)
    D.defs.append(
        '<filter id="farwob" x="-10%" y="-20%" width="120%" height="140%" color-interpolation-filters="sRGB">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="21" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="12" xChannelSelector="R" yChannelSelector="G" result="d"/>'
        '<feGaussianBlur in="d" stdDeviation="5"/></filter>')
    D.defs.append('<linearGradient id="mistfade" gradientUnits="userSpaceOnUse" x1="0" y1="560" x2="0" y2="780">'
                  '<stop offset="0" stop-color="#fff"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.42"/>'
                  '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    D.defs.append(f'<mask id="farmask" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                  f'<rect x="0" y="300" width="{W}" height="520" fill="url(#mistfade)"/></mask>')
    L, R = 716, 1160
    rl, rr = 826, 1050
    ry, ey = 508, 622
    roof = (f'M{rl},{ry} L{rr},{ry} Q{rr+40},{ey-30} {R},{ey-18} Q{R-30},{ey+4} {R-60},{ey+8} L{L+60},{ey+8} '
            f'Q{L+30},{ey+4} {L},{ey-18} Q{rl-40},{ey-30} {rl},{ry} Z')
    ridge = (f'M{rl-14},{ry-4} Q{rl-18},{ry-24} {rl-6},{ry-26} L{rl+4},{ry-10} L{rr-4},{ry-10} L{rr+6},{ry-26} '
             f'Q{rr+18},{ry-24} {rr+14},{ry-4} Z')
    eave_shadow = f'<rect x="{L+50}" y="{ey+8}" width="{R-L-100}" height="16" fill="{INK3}" opacity="0.5"/>'
    body = ''.join(f'<rect x="{x}" y="{ey+20}" width="9" height="120" fill="{INK3}" opacity="0.4"/>'
                   for x in range(L + 84, R - 60, 70))
    lower = f'<path d="M{L+30},{ey+92} L{R},{ey+92} L{R},{ey+106} L{L+30},{ey+106} Z" fill="{MIST}"/>'
    pines = pine_crown(806, 432, 0.85, rng) + pine_crown(1046, 468, 0.75, rng)
    return (f'<g mask="url(#farmask)" opacity="0.92"><g filter="url(#farwob)" fill="{MIST}">'
            f'<g opacity="0.8">{pines}</g>'
            f'<path d="{roof}"/><path d="{ridge}"/>{eave_shadow}{body}{lower}'
            f'</g></g>')


# ----------------------------------------------------------------------------- 3. mid distance
def defs_wash():
    # sumi wash: dry, ragged edges + soft granulation (no stripes)
    D.defs.append(
        '<filter id="drywash" x="-15%" y="-15%" width="130%" height="130%" color-interpolation-filters="sRGB">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.07" numOctaves="3" seed="31" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="6" xChannelSelector="R" yChannelSelector="G" result="d"/>'
        '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="4" seed="33" result="g"/>'
        '<feColorMatrix in="g" result="ga" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  1.5 0 0 0 0.05"/>'
        '<feComposite in="d" in2="ga" operator="in" result="mott"/>'
        '<feGaussianBlur in="mott" stdDeviation="0.6"/></filter>')


def layer_lantern():
    D.defs.append('<linearGradient id="lanfade" gradientUnits="userSpaceOnUse" x1="0" y1="1410" x2="0" y2="1540">'
                  '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    D.defs.append(f'<mask id="lanmask" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                  f'<rect x="0" y="1000" width="400" height="600" fill="url(#lanfade)"/></mask>')
    cx = 170
    shapes = [
        f'M{cx-10},1110 Q{cx-16},1094 {cx},1080 Q{cx+16},1094 {cx+10},1110 Z',
        f'M{cx-22},1122 Q{cx},1106 {cx+22},1122 L{cx+18},1130 L{cx-18},1130 Z',
        f'M{cx-30},1132 L{cx+30},1132 Q{cx+60},1160 {cx+82},1170 Q{cx+92},1166 {cx+86},1158 '
        f'Q{cx+90},1178 {cx+76},1188 L{cx-76},1188 Q{cx-90},1178 {cx-86},1158 Q{cx-92},1166 {cx-82},1170 Q{cx-60},1160 {cx-30},1132 Z',
        f'M{cx-46},1196 L{cx+46},1196 L{cx+42},1284 L{cx-42},1284 Z',
        f'M{cx-64},1288 L{cx+64},1288 L{cx+56},1316 L{cx-56},1316 Z',
        f'M{cx-21},1318 L{cx+21},1318 L{cx+24},1468 L{cx-24},1468 Z',
        f'M{cx-27},1384 L{cx+27},1384 L{cx+27},1396 L{cx-27},1396 Z',
        f'M{cx-52},1470 L{cx+52},1470 L{cx+58},1520 L{cx-58},1520 Z',
    ]
    fill = ''.join(f'<path d="{d}"/>' for d in shapes)
    rim = ''.join(f'<path d="{d}"/>' for d in shapes[2:6])
    window = f'<path d="M{cx-17},1214 L{cx+17},1214 L{cx+15},1266 L{cx-15},1266 Z" fill="{PAPER}" opacity="0.95"/>'
    # shadow side (light from upper left): a second, darker wash on the right faces
    shade = (f'<path d="M{cx+10},1196 L{cx+46},1196 L{cx+42},1284 L{cx+8},1284 Z"/>'
             f'<path d="M{cx+4},1318 L{cx+21},1318 L{cx+24},1468 L{cx+6},1468 Z"/>'
             f'<path d="M{cx+10},1176 L{cx+76},1188 L{cx-20},1188 Z"/>')
    rng = np.random.default_rng(41)
    moss = ''
    for (x, y) in [(cx - 60, 1166), (cx - 38, 1160), (cx + 52, 1166), (cx - 6, 1150), (cx - 46, 1478), (cx + 40, 1488), (cx - 22, 1302)]:
        for _ in range(2):
            xx, yy = x + rng.uniform(-8, 8), y + rng.uniform(-4, 4)
            moss += f'<ellipse cx="{f(xx)}" cy="{f(yy)}" rx="{f(rng.uniform(2.5,5))}" ry="{f(rng.uniform(2,3.5))}"/>'
    return (f'<g mask="url(#lanmask)">'
            f'<g filter="url(#drywash)"><g fill="{INK3}" opacity="0.8">{fill}</g>'
            f'<g fill="{INK2}" opacity="0.28">{shade}</g>'
            f'<g fill="none" stroke="{INK2}" stroke-width="2.2" opacity="0.5">{rim}</g></g>'
            f'{window}<g fill="{INK2}" opacity="0.75" filter="url(#{D.bleed(43, disp=2, halo=0)})">{moss}</g>'
            f'</g>')


def needle_fan(hub, ang, rng, length=(72, 98), spread=128, k=7):
    out = []
    for i in range(k):
        a = math.radians(ang + (i / (k - 1) - 0.5) * spread + rng.uniform(-5, 5))
        Ln = rng.uniform(*length) * (0.82 if i in (0, k - 1) else 1.0)
        st = (hub[0] + math.cos(a) * 5, hub[1] + math.sin(a) * 5)
        en = (hub[0] + math.cos(a) * Ln, hub[1] + math.sin(a) * Ln)
        bend = rng.uniform(4, 10) * (1 if rng.random() < 0.5 else -1)
        mid = ((st[0] + en[0]) / 2 - math.sin(a) * bend, (st[1] + en[1]) / 2 + math.cos(a) * bend)
        g = stroke([st, mid, en], [(0, 3.6), (0.35, 3.2), (1, 0.9)], int(rng.integers(1e6)), flick=0, edge=0.05,
                   blob=0.9, kasure=0, cap_skew=0)
        out.append(g['poly'])
    return out


def layer_pine():
    rng = np.random.default_rng(51)
    out = []
    trunk_pts = [(-50, 92), (40, 128), (128, 116), (210, 160), (300, 176), (380, 222), (470, 246), (540, 288), (590, 310)]
    g = stroke(trunk_pts, [(0, 46), (0.25, 36), (0.6, 22), (0.9, 13), (1, 10)], 61, kind='cat', n=110, flick=18,
               edge=0.14, kasure=12, dry_from=0.12, streak_w=(1.2, 3.0), side_bias=0.3)
    out.append(stroke_svg(g, INK1, 61, opacity=0.96, halo=0.1))
    # bark scales (dry dark ticks)
    tp = catmull(trunk_pts, 110)
    sc = ''
    for i in range(5, 85, 6):
        x, y = tp[i]
        dy = rng.uniform(-6, 4)
        sc += f'<path d="M{f(x-9)},{f(y+dy)} q6,-6 15,-1" stroke-width="{rng.uniform(2,3.4):.1f}"/>'
    out.append(f'<g stroke="{INK0}" fill="none" stroke-linecap="round" opacity="0.75" '
               f'filter="url(#{D.bleed(62, disp=2, halo=0)})">{sc}</g>')
    # 9 needle tufts; root on the branch -> short twig -> hub -> fan of 7 needles
    tufts = [((70, 96), -100, 0.10, INK0), ((150, 176), 100, 0.18, INK1), ((226, 104), -75, 0.25, INK0),
             ((318, 132), -95, 0.36, INK0), ((356, 238), 95, 0.42, INK1), ((452, 182), -80, 0.55, INK0),
             ((486, 300), 105, 0.62, INK1), ((556, 236), -60, 0.73, INK0), ((612, 330), 25, 0.97, INK0)]
    nt = len(tp)
    for hub, ang, sfrac, col in tufts:
        root = tp[min(nt - 1, int(sfrac * (nt - 1)))]
        dx, dy = hub[0] - root[0], hub[1] - root[1]
        mid = (root[0] + dx * 0.5 + dy * 0.18, root[1] + dy * 0.5 - dx * 0.18)  # bent twig
        tw = stroke([tuple(root), mid, hub], [(0, 12), (0.6, 7), (1, 4)], int(rng.integers(1e6)), flick=0, kasure=3,
                    edge=0.08, dry_from=0.2)
        out.append(stroke_svg(tw, INK1, int(rng.integers(1e6)), opacity=0.95, halo=0))
        polys = needle_fan(hub, ang, rng)
        sd = int(rng.integers(1e6))
        fid = D.bleed(sd, disp=1.6, halo=0.07)
        paths = ''.join(f'<path d="{pts_d(p)}"/>' for p in polys)
        out.append(f'<g filter="url(#{fid})" opacity="{0.95 if col == INK0 else 0.85}"><g fill="{col}">{paths}</g></g>')
    return ''.join(out)


# ----------------------------------------------------------------------------- 4. contact shadows
def dry_shadow(cx, y, width, thick, seed, opacity):
    g = stroke([(cx - width / 2, y + 1), (cx, y - 1), (cx + width / 2, y + 1)],
               [(0, thick * 0.5), (0.25, thick), (0.7, thick * 0.8), (1, 2)], seed, flick=10, edge=0.15,
               kasure=6, dry_from=0.1, streak_w=(1.0, 2.2))
    return stroke_svg(g, INK3, seed, opacity=opacity, halo=0)


def layer_shadows():
    out = [dry_shadow(560, 1562, 420, 13, 71, 0.4)]
    for bx, sc in zip(P['mook_x'], (1, 1, 0.85)):
        out.append(dry_shadow(bx + 4, 1562, 120 * sc, 9 * sc, nseed(), 0.32))
    out.append(f'<ellipse cx="796" cy="1562" rx="28" ry="5" fill="{INK3}" opacity="0.3" filter="url(#{D.bleed(77, disp=2, halo=0)})"/>')
    return ''.join(out)


# ----------------------------------------------------------------------------- 5. makiwara disciples
def mook(bx, lean, scale=1.0, pale=False, reach=False, arm_tilt=0.0, arm_h=292, exts=(116, 116)):
    rng = np.random.default_rng(int(bx) + 3)
    base = (bx, GROUND_Y + 2)
    c_post = MIST if pale else INK2
    c_light = MIST if pale else INK3
    c_rope = INK3 if pale else INK1
    op = 0.95

    def T(p):
        x = bx + (p[0] - bx) * scale
        y = GROUND_Y + (p[1] - GROUND_Y) * scale
        return rot((x, y), lean, base)

    top = GROUND_Y - 440
    out = []
    # bamboo cross-arm right under the straw; A's ball-side end reaches further
    ay = GROUND_Y - arm_h
    l_ext, r_ext = exts

    def TA(p):  # arm points: extra tilt about the post centre at arm height
        return T(rot(p, arm_tilt, (bx, ay)))
    arm = stroke([TA((bx - l_ext, ay + 5)), TA((bx, ay - 3)), TA((bx + r_ext, ay + 4))], [(0, 10), (0.5, 12), (1, 9)],
                 nseed(), flick=6, edge=0.08, kasure=4, dry_from=0.0, streak_w=(0.8, 1.6))
    out.append(stroke_svg(arm, c_post, nseed(), opacity=op, halo=0))
    ticks = ''
    for xo in (-l_ext * 0.78, -l_ext * 0.4, r_ext * 0.4, r_ext * 0.8):
        p1, p2 = TA((bx + xo, ay - 9)), TA((bx + xo, ay + 9))
        ticks += f'<path d="M{f(p1[0])},{f(p1[1])} L{f(p2[0])},{f(p2[1])}"/>'
    out.append(f'<g stroke="{c_rope}" stroke-width="3.2" stroke-linecap="round" opacity="0.8" '
               f'filter="url(#{D.bleed(nseed(), disp=1.5, halo=0)})">{ticks}</g>')
    # post
    post = stroke([T((bx, GROUND_Y + 2)), T((bx + 2, GROUND_Y - 220)), T((bx, top + 10))],
                  [(0, 46 * scale), (0.6, 42 * scale), (1, 38 * scale)], nseed(), flick=0, edge=0.05, blob=0.55,
                  kasure=9, dry_from=0.0, streak_w=(0.8, 1.8), cap_skew=0)
    out.append(stroke_svg(post, c_post, nseed(), opacity=op, halo=0.05))
    # straw sheath (wash) wider than the post, cinched at the ropes
    r1, r2 = top + 42, top + 104
    sh = [(-40, top - 4), (-46, top + 20), (-38, r1), (-46, top + 72), (-38, r2), (-44, top + 128), (-30, top + 146),
          (30, top + 146), (44, top + 128), (38, r2), (46, top + 72), (38, r1), (46, top + 20), (40, top - 4)]
    shp = [T((bx + x, y)) for x, y in sh]
    out.append(f'<g filter="url(#drywash)"><path d="{pts_d(shp)}" fill="{c_light}" opacity="0.9"/></g>')
    # straw strands: short diagonal dry strokes
    nst = int(rng.integers(16, 21))
    for i in range(nst):
        y0 = top + rng.uniform(-8, 96)
        x0 = bx + rng.uniform(-38, 32)
        dx = rng.uniform(6, 18) * (1 if i % 2 else -1)
        L_ = rng.uniform(40, 70)
        col = c_post if rng.random() < 0.55 else (INK1 if (not pale and rng.random() < 0.15) else c_light)
        g = stroke([T((x0, y0)), T((x0 + dx * 0.5, y0 + L_ * 0.5)), T((x0 + dx, y0 + L_))],
                   [(0, rng.uniform(4.5, 7)), (1, 1.6)], nseed(), flick=6, edge=0.1, kasure=1, dry_from=0.3,
                   streak_w=(0.8, 1.2))
        out.append(stroke_svg(g, col, nseed(), opacity=0.9, halo=0))
    # frayed ends poking out under the sheath
    for i in range(6):
        x0 = bx + rng.uniform(-30, 30)
        g = stroke([T((x0, top + 136)), T((x0 + rng.uniform(-16, 16), top + 168))], [(0, 3.4), (1, 1)], nseed(),
                   flick=0, kasure=0)
        out.append(stroke_svg(g, c_post, nseed(), opacity=0.8, halo=0))
    # rope rings
    for ry in (r1, r2):
        a, b, c = T((bx - 42, ry - 3)), T((bx, ry + 6)), T((bx + 42, ry - 3))
        g = stroke([a, b, c], [(0, 4.5), (0.5, 5.2), (1, 4)], nseed(), flick=0, kasure=0, edge=0.04, blob=0.8)
        out.append(stroke_svg(g, c_rope, nseed(), opacity=0.95, halo=0))
    # straw kasa: low wide triangle wash, darker rim
    k = [T((bx - 78, top + 2)), T((bx - 30, top - 26)), T((bx + 2, top - 46)),
         T((bx + 34, top - 26)), T((bx + 78, top + 2)), T((bx, top + 8))]
    kd = (f'M{f(k[0][0])},{f(k[0][1])} Q{f(k[1][0])},{f(k[1][1])} {f(k[2][0])},{f(k[2][1])} '
          f'Q{f(k[3][0])},{f(k[3][1])} {f(k[4][0])},{f(k[4][1])} Q{f(k[5][0])},{f(k[5][1])} {f(k[0][0])},{f(k[0][1])} Z')
    out.append(f'<g filter="url(#drywash)"><path d="{kd}" fill="{c_light}" opacity="0.95"/>'
               f'<path d="{kd}" fill="none" stroke="{c_post}" stroke-width="2.4" opacity="0.6"/></g>')
    rim = stroke([k[0], k[5], k[4]], [(0, 3), (0.5, 6), (1, 2)], nseed(), flick=4, kasure=1)
    out.append(stroke_svg(rim, c_post, nseed(), opacity=0.9, halo=0))
    return ''.join(out)


def layer_mooks():
    xs, leans = P['mook_x'], P['mook_lean']
    return ('<g opacity="0.88">' + mook(xs[2], leans[2], 0.85, pale=True, arm_tilt=6, arm_h=300, exts=(100, 110)) +
            mook(xs[1], leans[1], arm_tilt=18, arm_h=262, exts=(92, 112)) +
            mook(xs[0], leans[0], reach=True, arm_tilt=-12, arm_h=300, exts=(126, 84)) + '</g>')


# ----------------------------------------------------------------------------- 6. hero: the old master
HERO = dict(
    hip=(538, 1100), sp_c=((522, 1000), (406, 846)), neck=(602, 806), head=(644, 714), head_r=62,
    sh_l=(612, 822), el_l=(680, 896), ha_l=(718, 760),
    sh_r=(590, 828), el_r=(428, 936), ha_r=(506, 1040),
    kn_l=(664, 1334), an_l=(740, 1540), toe=(792, 1536),
    kn_r=(494, 1334), an_r=(450, 1548), ft_r=(482, 1560),
)


def layer_hero():
    h = HERO
    op = P['hero_opacity']
    P['bleed_halo'] = 0.15
    out = []
    # rear (far) arm first, lighter ink: one sweep shoulder -> elbow (behind the back) -> hand
    g = stroke([h['sh_r'], h['el_r'], h['ha_r']], [(0, 20), (0.5, 16), (0.58, 17), (1, 9)], 201, kind='cat', n=70,
               flick=10, kasure=6, dry_from=0.6)
    out.append(stroke_svg(g, INK1, 201, opacity=0.96))
    # rear leg: one sweep hip -> knee -> ankle, small hane into the foot
    g = stroke([(h['hip'][0] - 8, h['hip'][1] + 14), h['kn_r'], h['an_r'], h['ft_r']], [(0, 36), (0.45, 28), (0.5, 29), (0.9, 14), (1, 9)],
               211, kind='cat', n=90, flick=8, kasure=9, dry_from=0.6)
    out.append(stroke_svg(g, INK0, 211, opacity=op, tone=INK1))
    # spine (hunched) continuing into the neck: one sweep
    hip, c, neck = h['hip'], h['sp_c'], h['neck']
    sp = [bez([hip, c[0], c[1], neck], t) for t in np.linspace(0, 1, 80)]
    sp += [np.array(neck) + (np.array((h['head'][0] - 20, h['head'][1] + 56)) - np.array(neck)) * t for t in np.linspace(0.1, 1, 8)]
    g = stroke(sp, [(0, 38), (0.12, 41), (0.3, 38), (0.75, 29), (0.9, 21), (1, 14)], 221, kind='raw', flick=6, kasure=7,
               dry_from=0.55, side_bias=-0.4, blob=0.85)
    out.append(stroke_svg(g, INK0, 221, opacity=op))
    # lead leg: one sweep hip -> knee -> ankle -> toe, the harai flicks up under the ball (dry-brush speed mask)
    sh = math.degrees(math.atan2(h['an_l'][1] - h['kn_l'][1], h['an_l'][0] - h['kn_l'][0]))
    D.defs.append(
        '<filter id="speedturb" filterUnits="userSpaceOnUse" x="-600" y="-600" width="2400" height="2400" color-interpolation-filters="sRGB">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.002 0.25" numOctaves="2" seed="231"/>'
        '<feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  -14 0 0 0 8.9"/></filter>')
    # streaks run along the shin; only the trailing (back) half of the leg is allowed to dry out
    kx, ky = h['kn_l']
    D.defs.append(f'<linearGradient id="speedside" gradientUnits="userSpaceOnUse" x1="{kx-40}" y1="{ky+10}" x2="{kx+4}" y2="{ky-6}">'
                  '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>')
    D.defs.append(f'<mask id="speedm" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                  f'<g transform="rotate({sh:.1f} {kx} {ky})"><rect x="{kx-500}" y="{ky-500}" width="1000" height="1000" fill="#fff" filter="url(#speedturb)"/></g>'
                  f'<g transform="rotate({sh-90:.1f} {kx} {ky})"><rect x="{kx-600}" y="{ky-600}" width="1200" height="1200" fill="url(#speedside)"/></g>'
                  f'<rect x="0" y="0" width="{W}" height="{ky-120}" fill="#fff"/></mask>')
    g = stroke([(h['hip'][0] + 10, h['hip'][1] + 16), h['kn_l'], h['an_l'], h['toe']], [(0, 37), (0.42, 29), (0.47, 30), (0.86, 16), (1, 8)],
               231, kind='cat', n=100, flick=4, flick_bend=-1, kasure=8, dry_from=0.62)
    out.append(stroke_svg(g, INK0, 231, opacity=op, extra_mask='speedm', tone=INK1))
    ax, ay = h['an_l']
    tx, ty = h['toe']
    g = stroke([(ax - 6, ay - 4), (ax + 24, ay + 6), (tx, ty)], [(0, 17), (0.55, 14), (1, 8)], 234, flick=6,
               flick_bend=-1, kasure=3, dry_from=0.7, blob=1.0)
    out.append(stroke_svg(g, INK0, 234, opacity=op))
    # lead arm: one sweep shoulder -> elbow -> hand at the mouth (yawn)
    g = stroke([h['sh_l'], h['el_l'], h['ha_l']], [(0, 27), (0.38, 20), (0.44, 21), (0.86, 11), (0.95, 15), (1, 13)], 241,
               kind='cat', n=70, flick=5, kasure=5, dry_from=0.55)
    out.append(stroke_svg(g, INK0, 241, opacity=op))
    # head: enso, 45-deg gap facing down-right toward the ball
    cx, cy = h['head']
    r = h['head_r']
    a0, a1 = 67.5, 360 + 22.5
    angs = np.radians(np.linspace(a0, a1, 100))
    arc = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angs]
    g = stroke(arc, [(0, 11), (0.12, 17), (0.4, 27), (0.62, 23), (0.85, 13), (1, 8)], 251, kind='raw', flick=12,
               flick_bend=3, kasure=9, dry_from=0.62, blob=1.15, side_bias=0.3)
    out.append(stroke_svg(g, INK0, 251, opacity=op))
    # topknot: small comma loop
    hx, hy = h['head']
    bun = (hx - 34, hy - 70)
    g = stroke([(bun[0] + 14, bun[1] + 16), (bun[0] + 2, bun[1] - 6), (bun[0] - 10, bun[1] + 2)], [(0, 16), (0.4, 26), (1, 14)],
               252, flick=0, kasure=3, dry_from=0.5, blob=1.2, edge=0.06)
    out.append(stroke_svg(g, INK0, 252, opacity=op))
    g = stroke([(bun[0] - 8, bun[1] + 4), (bun[0] - 24, bun[1] + 8), (bun[0] - 36, bun[1] + 22)], [(0, 7), (1, 2)],
               254, flick=6, kasure=1, dry_from=0.4)
    out.append(stroke_svg(g, INK0, 254, opacity=op))
    if P['breath']:
        # yawn: two small pale breath curls drifting up-right out of the open side of the enso
        D.defs.append('<filter id="puff" x="-50%" y="-50%" width="200%" height="200%">'
                      '<feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" seed="257" result="n"/>'
                      '<feDisplacementMap in="SourceGraphic" in2="n" scale="10" xChannelSelector="R" yChannelSelector="G"/>'
                      '<feGaussianBlur stdDeviation="3.5"/></filter>')
        hx, hy = h['head']
        out.append(f'<g filter="url(#puff)" fill="{INK3}" opacity="0.5">'
                   f'<ellipse cx="{hx+108}" cy="{hy+18}" rx="22" ry="14"/><ellipse cx="{hx+138}" cy="{hy+2}" rx="14" ry="10"/>'
                   f'<ellipse cx="{hx+158}" cy="{hy-12}" rx="8" ry="6"/></g>')
    P['bleed_halo'] = 0.08
    return ''.join(out)


# ----------------------------------------------------------------------------- 7. temari
def layer_temari():
    cx, cy, r = 796, 1482, 40
    fid = D.bleed(301, disp=2.4, halo=0.12)
    D.defs.append(f'<clipPath id="ballclip"><circle cx="{cx}" cy="{cy}" r="{r-1.5}"/></clipPath>')
    pole = (cx - 6, cy - 18)
    petals = ''
    for i in range(8):
        a = math.radians(i * 45 + 12)
        tip = (pole[0] + math.cos(a) * 34, pole[1] + 2 + math.sin(a) * 16)
        c1 = (pole[0] + math.cos(a + 0.42) * 20, pole[1] + math.sin(a + 0.42) * 9)
        c2 = (pole[0] + math.cos(a - 0.42) * 20, pole[1] + math.sin(a - 0.42) * 9)
        petals += (f'<path d="M{f(pole[0])},{f(pole[1])} Q{f(c1[0])},{f(c1[1])} {f(tip[0])},{f(tip[1])} '
                   f'Q{f(c2[0])},{f(c2[1])} {f(pole[0])},{f(pole[1])} Z"/>')
    band = (f'<path d="M{cx-44},{cy+6} Q{cx},{cy+30} {cx+44},{cy+6}" stroke="{INK0}" stroke-width="2.6" fill="none" opacity="0.85"/>'
            f'<path d="M{cx-44},{cy+12} Q{cx},{cy+36} {cx+44},{cy+12}" stroke="{PAPER}" stroke-width="1.5" fill="none" opacity="0.75"/>'
            f'<path d="M{cx-44},{cy+1} Q{cx},{cy+25} {cx+44},{cy+1}" stroke="{PAPER}" stroke-width="1.5" fill="none" opacity="0.75"/>')
    hl = f'<path d="M{cx-30},{cy-6} Q{cx-30},{cy-28} {cx-12},{cy-34} Q{cx-24},{cy-22} {cx-30},{cy-6} Z" fill="{PAPER}" opacity="0.7"/>'
    ball = (f'<g filter="url(#{fid})"><circle cx="{cx}" cy="{cy}" r="{r}" fill="{VERM}"/></g>'
            f'<g clip-path="url(#ballclip)"><g fill="none" stroke="{PAPER}" stroke-width="2" opacity="0.9">{petals}</g>'
            f'{band}{hl}</g>')
    arcs = ''
    for i, (p0, p1, p2) in enumerate([((706, 1350), (740, 1386), (756, 1428)), ((738, 1334), (768, 1366), (782, 1404))]):
        g = stroke([p0, p1, p2], [(0, 2), (0.4, 6), (1, 1.2)], 310 + i, flick=0, kasure=3, dry_from=0.0,
                   streak_w=(0.8, 1.4))
        arcs += stroke_svg(g, INK3, 310 + i, opacity=0.85, halo=0)
    return arcs + ball


# ----------------------------------------------------------------------------- 8. seals
GLYPHS = [
    lambda x, y: f'<rect x="{x+12}" y="{y+12}" width="32" height="32" rx="2" fill="none" stroke="{PAPER}" stroke-width="5"/>'
                 f'<rect x="{x+23}" y="{y+23}" width="10" height="10" fill="{PAPER}" transform="rotate(45 {x+28} {y+28})"/>',
    lambda x, y: f'<g transform="rotate(-35 {x+28} {y+28})"><rect x="{x+10}" y="{y+16}" width="36" height="7" fill="{PAPER}"/>'
                 f'<rect x="{x+14}" y="{y+33}" width="28" height="7" fill="{PAPER}"/></g>',
    lambda x, y: f'<circle cx="{x+28}" cy="{y+28}" r="15" fill="none" stroke="{PAPER}" stroke-width="5"/>'
                 f'<circle cx="{x+28}" cy="{y+28}" r="4.5" fill="{PAPER}"/>',
]


def layer_seals():
    D.defs.append(
        '<filter id="sealtex" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="sRGB">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.13" numOctaves="2" seed="401" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G" result="d"/>'
        '<feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves="3" seed="402" result="m"/>'
        '<feColorMatrix in="m" result="ma" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -16 0 0 0 10.2"/>'
        '<feComposite in="d" in2="ma" operator="in" result="c"/>'
        '<feGaussianBlur in="c" stdDeviation="0.5"/></filter>')
    out = []
    x0, y0 = P['seal_x'] - 28, P['seal_y']
    rots = [-3, 2.5, -1.5]
    for i in range(3):
        y = y0 + i * 76
        out.append(f'<g transform="rotate({rots[i]} {x0+28} {y+28})" filter="url(#sealtex)">'
                   f'<rect x="{x0}" y="{y}" width="56" height="56" rx="6" fill="{VERM}"/>{GLYPHS[i](x0, y)}</g>')
    for i in range(2):
        y = y0 + (3 + i) * 76
        out.append(f'<rect x="{x0+1}" y="{y+1}" width="54" height="54" rx="6" fill="none" stroke="{MIST}" stroke-width="2.4" '
                   f'transform="rotate({1.5 if i else -2} {x0+28} {y+28})" opacity="0.9"/>')
    return ''.join(out)


# ----------------------------------------------------------------------------- 9. overlay
def layer_overlay():
    rng = np.random.default_rng(901)
    D.defs.append(
        '<filter id="washi" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="902"/>'
        '<feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.42  0 0 0 0 0.36  -1 0 0 0 1"/>'
        '<feComponentTransfer><feFuncA type="linear" slope="0.1"/></feComponentTransfer></filter>')
    D.defs.append('<radialGradient id="vig" gradientUnits="userSpaceOnUse" cx="540" cy="900" r="1150">'
                  f'<stop offset="0.55" stop-color="{MIST}" stop-opacity="0"/><stop offset="1" stop-color="{MIST}" stop-opacity="0.18"/></radialGradient>')
    fib = []
    for _ in range(180):
        x, y = rng.uniform(-40, W + 40), rng.uniform(-40, H + 40)
        L_ = rng.uniform(40, 170)
        a = rng.uniform(0, 2 * math.pi)
        x1, y1 = x + math.cos(a) * L_, y + math.sin(a) * L_
        c1 = (x + math.cos(a + rng.uniform(-1, 1)) * L_ * 0.35, y + math.sin(a + rng.uniform(-1, 1)) * L_ * 0.35)
        c2 = (x1 - math.cos(a + rng.uniform(-1, 1)) * L_ * 0.35, y1 - math.sin(a + rng.uniform(-1, 1)) * L_ * 0.35)
        fib.append(f'<path d="M{f(x)},{f(y)} C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(x1)},{f(y1)}" stroke-width="{rng.uniform(0.5,1.2):.2f}"/>')
    return (f'<rect width="{W}" height="{H}" fill="#fff" filter="url(#washi)" style="mix-blend-mode:multiply"/>'
            f'<g stroke="{FIBRE}" fill="none" opacity="0.25" stroke-linecap="round">{"".join(fib)}</g>'
            f'<rect width="{W}" height="{H}" fill="url(#vig)" style="mix-blend-mode:multiply"/>')


def build():
    defs_wash()
    D.defs.append('<filter id="kr" x="-10%" y="-10%" width="120%" height="120%">'
                  '<feTurbulence type="fractalNoise" baseFrequency="0.22" numOctaves="2" seed="7"/>'
                  '<feDisplacementMap in="SourceGraphic" scale="3.2" xChannelSelector="R" yChannelSelector="G"/></filter>')
    layers = [layer_paper(), layer_far(), layer_lantern(), layer_pine(), layer_shadows(), layer_mooks(),
              layer_hero(), layer_temari(), layer_seals(), layer_overlay()]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<defs>{"".join(D.defs)}</defs>{"".join(layers)}</svg>')


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'still.svg')
    svg = build()
    with open(out, 'w') as fh:
        fh.write(svg)
    print('wrote', out, len(svg) // 1024, 'KB')
