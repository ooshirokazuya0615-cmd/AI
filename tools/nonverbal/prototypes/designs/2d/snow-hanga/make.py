#!/usr/bin/env python3
"""WOODBLOCK SNOW / 雪夜の版画 — one 1080x1920 SVG still, code-drawn only.
Usage: python3 make.py [out.svg]"""
import math, random, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from pose2d import POSE, GROUND_Y  # noqa: E402

W, H = 1080, 1920
PAPER = '#F2F0E8'; BERO = '#22385A'; INK = '#141B2B'; DUSK = '#5E6488'; PLASTER = '#E6E1D3'
PERS = '#D9682F'; INNER = '#F3A953'; POOL = '#F6D7B8'; OCHRE = '#A8824E'; STRAW = '#CDB27E'
BRASS = '#C9993F'; SHADOW = '#C3CAD8'; CREAM = '#EFE5CF'

KW = 4.5          # key-block line width
MIS = (2, -1)     # warm plate misregistration
HEADROT = 10
UDY = 30
BROOM_TOP = (505, 690 + UDY)
CFG = dict(halo=3.0, carve=3.0, washi=0.09, grain=0.04)


def P(x, y):
    return f"{x:.1f},{y:.1f}"


def cr(ps, closed=True):
    """Catmull-Rom spline through points -> cubic Bezier path."""
    n = len(ps)
    out = [f"M{P(*ps[0])}"]
    segs = n if closed else n - 1
    for i in range(segs):
        p0 = ps[(i - 1) % n] if closed else ps[max(i - 1, 0)]
        p1 = ps[i % n]
        p2 = ps[(i + 1) % n] if closed else ps[i + 1]
        p3 = ps[(i + 2) % n] if closed else ps[min(i + 2, n - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{P(*c1)} {P(*c2)} {P(*p2)}")
    if closed:
        out.append("Z")
    return " ".join(out)


def poly(ps):
    return "M" + " L".join(P(*p) for p in ps) + " Z"


def blob(cx, cy, rx, ry, rng, n=9, jit=0.12, rot=0.0):
    ps = []
    ca, sa = math.cos(rot), math.sin(rot)
    for i in range(n):
        a = 2 * math.pi * i / n + rng.uniform(-0.15, 0.15)
        r = 1 + rng.uniform(-jit, jit)
        x, y = rx * r * math.cos(a), ry * r * math.sin(a)
        ps.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return cr(ps)


def kp(d, fill, sw=KW, key=BERO, extra=''):
    st = f' stroke="{key}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"' if sw > 0 else ''
    return f'<path d="{d}" fill="{fill}"{st} {extra}/>'


def warm(d, fill, sw=KW, key=BERO, extra=''):
    """Warm plate printed slightly off-register, key block on top."""
    s = f'<path d="{d}" fill="{fill}" transform="translate({MIS[0]},{MIS[1]})" {extra}/>'
    if sw > 0:
        s += f'<path d="{d}" fill="none" stroke="{key}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>'
    return s


def line(p1, p2, col, w, extra=''):
    return (f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" '
            f'stroke="{col}" stroke-width="{w}" stroke-linecap="round" {extra}/>')


def snowcap(x0, x1, yb, h, rng, droop=5, step=20):
    """Lumpy snow cushion sitting on a horizontal edge x0..x1 at yb."""
    w = x1 - x0
    n = max(3, int(w / step))
    top = []
    for i in range(n + 1):
        t = i / n
        x = x0 - 4 + (w + 8) * t
        bump = (math.sin(math.pi * t) ** 0.45) * (0.7 + 0.3 * rng.random())
        top.append((x, yb - 1 - h * bump))
    m = max(2, int(w / 26))
    bot = []
    for i in range(1, m):
        t = 1 - i / m
        bot.append((x0 - 4 + (w + 8) * t + rng.uniform(-3, 3), yb + rng.uniform(1, droop)))
    return cr(top + bot)


def ik(s, h, a, b, hint):
    dx, dy = h[0] - s[0], h[1] - s[1]
    d = min(math.hypot(dx, dy), a + b - 0.01)
    base = math.atan2(dy, dx)
    c = max(-1, min(1, (a * a + d * d - b * b) / (2 * a * d)))
    off = math.acos(c)
    cands = [(s[0] + a * math.cos(base + sg * off), s[1] + a * math.sin(base + sg * off)) for sg in (1, -1)]
    return min(cands, key=lambda e: (e[0] - hint[0]) ** 2 + (e[1] - hint[1]) ** 2)


def capsule(p1, p2, r1, r2):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1) or 1e-3
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy, ux
    pg = poly([(x1 + nx * r1, y1 + ny * r1), (x2 + nx * r2, y2 + ny * r2),
               (x2 - nx * r2, y2 - ny * r2), (x1 - nx * r1, y1 - ny * r1)])
    return [('path', pg), ('circle', (x1, y1, r1)), ('circle', (x2, y2, r2))]


def shapes_svg(shs, fill, stroke=None, sw=0):
    st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ''
    o = []
    for kind, v in shs:
        if kind == 'path':
            o.append(f'<path d="{v}" fill="{fill}"{st}/>')
        elif kind == 'circle':
            o.append(f'<circle cx="{v[0]:.1f}" cy="{v[1]:.1f}" r="{v[2]:.1f}" fill="{fill}"{st}/>')
        elif kind == 'ellipse':
            o.append(f'<ellipse cx="{v[0]:.1f}" cy="{v[1]:.1f}" rx="{v[2]:.1f}" ry="{v[3]:.1f}" fill="{fill}"{st}/>')
    return "".join(o)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def qbez(p0, p1, p2, t):
    return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])


def cbez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


# ----------------------------------------------------------------------------------------------
def defs():
    return f'''<defs>
<linearGradient id="sky" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="470">
 <stop offset="0" stop-color="{INK}"/><stop offset="0.638" stop-color="{BERO}"/><stop offset="1" stop-color="{DUSK}"/></linearGradient>
<linearGradient id="sine" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#000"/><stop offset="0.25" stop-color="#7f7f7f"/><stop offset="0.5" stop-color="#fff"/>
 <stop offset="0.75" stop-color="#7f7f7f"/><stop offset="1" stop-color="#000"/></linearGradient>
<pattern id="grainpat" width="22" height="64" patternUnits="userSpaceOnUse"><rect width="22" height="64" fill="url(#sine)"/></pattern>
<linearGradient id="snowg" gradientUnits="userSpaceOnUse" x1="0" y1="1440" x2="0" y2="1920">
 <stop offset="0" stop-color="{PAPER}"/><stop offset="0.45" stop-color="{PAPER}"/><stop offset="1" stop-color="{SHADOW}"/></linearGradient>
<linearGradient id="shoji" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{INNER}"/><stop offset="1" stop-color="{PERS}"/></linearGradient>
<radialGradient id="lanpaper" cx="0.5" cy="0.52" r="0.62">
 <stop offset="0.2" stop-color="{INNER}"/><stop offset="0.7" stop-color="{INNER}"/><stop offset="1" stop-color="{PERS}"/></radialGradient>
<linearGradient id="eaveshade" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{DUSK}" stop-opacity="0.8"/><stop offset="0.5" stop-color="{DUSK}" stop-opacity="0.35"/><stop offset="1" stop-color="{DUSK}" stop-opacity="0"/></linearGradient>
<linearGradient id="eaveshade2" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{BERO}" stop-opacity="0.55"/><stop offset="1" stop-color="{BERO}" stop-opacity="0"/></linearGradient>
<linearGradient id="wallright" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="{DUSK}" stop-opacity="0"/><stop offset="1" stop-color="{DUSK}" stop-opacity="0.55"/></linearGradient>
<linearGradient id="snownight" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{DUSK}" stop-opacity="0"/><stop offset="1" stop-color="{DUSK}" stop-opacity="0.42"/></linearGradient>
<radialGradient id="shojicore" cx="0.5" cy="0.42" r="0.6">
 <stop offset="0" stop-color="{POOL}" stop-opacity="0.55"/><stop offset="1" stop-color="{POOL}" stop-opacity="0"/></radialGradient>
<linearGradient id="wallfoot" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{DUSK}" stop-opacity="0"/><stop offset="1" stop-color="{DUSK}" stop-opacity="0.6"/></linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="{INNER}" stop-opacity="0.7"/>
 <stop offset="0.4" stop-color="{INNER}" stop-opacity="0.28"/><stop offset="1" stop-color="{INNER}" stop-opacity="0"/></radialGradient>
<radialGradient id="poolg"><stop offset="0" stop-color="{POOL}" stop-opacity="1"/>
 <stop offset="0.6" stop-color="{POOL}" stop-opacity="0.85"/><stop offset="1" stop-color="{POOL}" stop-opacity="0"/></radialGradient>
<linearGradient id="spillg" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{POOL}" stop-opacity="0.95"/><stop offset="1" stop-color="{POOL}" stop-opacity="0"/></linearGradient>
<radialGradient id="flake"><stop offset="0" stop-color="{PAPER}" stop-opacity="1"/>
 <stop offset="0.5" stop-color="{PAPER}" stop-opacity="0.95"/><stop offset="1" stop-color="{PAPER}" stop-opacity="0"/></radialGradient>
<linearGradient id="roofshade" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{SHADOW}" stop-opacity="0"/><stop offset="0.55" stop-color="{SHADOW}" stop-opacity="0"/>
 <stop offset="1" stop-color="{SHADOW}" stop-opacity="0.75"/></linearGradient>
<filter id="woodwarp" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">
 <feTurbulence type="fractalNoise" baseFrequency="0.01" numOctaves="2" seed="11" result="t"/>
 <feDisplacementMap in="SourceGraphic" in2="t" scale="30" xChannelSelector="R" yChannelSelector="G"/></filter>
<filter id="baren" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
 <feTurbulence type="fractalNoise" baseFrequency="0.006" numOctaves="3" seed="4" result="n"/>
 <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.25 0 0 0 0.825" result="a"/>
 <feComposite in="SourceGraphic" in2="a" operator="in"/></filter>
<filter id="carve" x="-3%" y="-3%" width="106%" height="106%" color-interpolation-filters="sRGB">
 <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="9" result="t"/>
 <feDisplacementMap in="SourceGraphic" in2="t" scale="{CFG['carve']}" xChannelSelector="R" yChannelSelector="G" result="d1"/>
 <feTurbulence type="fractalNoise" baseFrequency="0.11" numOctaves="1" seed="21" result="t2"/>
 <feDisplacementMap in="d1" in2="t2" scale="1.8" xChannelSelector="G" yChannelSelector="R"/></filter>
<filter id="washi" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
 <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" seed="2"/>
 <feColorMatrix type="matrix" values="2 0 0 0 -0.5  2 0 0 0 -0.5  2 0 0 0 -0.5  0 0 0 0 1"/></filter>
<filter id="soft" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="9"/></filter>
<filter id="soft4" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="4"/></filter>
<filter id="soft16" x="-40%" y="-60%" width="180%" height="220%"><feGaussianBlur stdDeviation="16"/></filter>
<linearGradient id="cushion" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0.45" stop-color="{SHADOW}" stop-opacity="0"/><stop offset="1" stop-color="{SHADOW}" stop-opacity="0.9"/></linearGradient>
<clipPath id="skyclip"><rect x="0" y="0" width="{W}" height="480"/></clipPath>
<clipPath id="headclip"><ellipse cx="566" cy="630" rx="52.5" ry="66.5" transform="rotate({HEADROT} 566 630)"/></clipPath>
<filter id="goma" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
 <feTurbulence type="fractalNoise" baseFrequency="0.38" numOctaves="2" seed="8" result="n"/>
 <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -16 0 0 0 5.15" result="h"/>
 <feComposite in="SourceGraphic" in2="h" operator="out" result="holed"/>
 <feComponentTransfer in="SourceGraphic" result="faint"><feFuncA type="linear" slope="0.5"/></feComponentTransfer>
 <feMerge><feMergeNode in="faint"/><feMergeNode in="holed"/></feMerge></filter>
</defs>'''


# ----------------------------------------------------------------------------------------------
def sky():
    o = [f'<g filter="url(#goma)"><rect x="-20" y="-20" width="{W+40}" height="500" fill="url(#sky)" filter="url(#baren)"/></g>']
    o.append(f'<g clip-path="url(#skyclip)"><g style="mix-blend-mode:multiply" opacity="{CFG["grain"]}">'
             f'<rect x="-60" y="-60" width="{W+120}" height="600" fill="url(#grainpat)" filter="url(#woodwarp)"/></g></g>')
    return "".join(o)


def ridge(rng):
    o = []
    ps = [(-20, 470)]
    for x in range(-20, W + 41, 40):
        y = 330 + 20 * math.sin(x * 0.011 + 1.3) + 9 * math.sin(x * 0.031) + rng.uniform(-3, 3)
        ps.append((x, y))
    ps.append((W + 40, 470))
    o.append(f'<path d="{cr(ps)}" fill="{DUSK}" opacity="0.8"/>')
    pts = []
    for x in range(-20, W + 41, 30):
        y = 352 + 16 * math.sin(x * 0.008 + 2.0) + 9 * math.sin(x * 0.027 + 0.5) + rng.uniform(-2, 2)
        pts.append((x, y))
    shape = cr([(-20, 480)] + pts + [(W + 40, 480)])
    crest = cr(pts, closed=False)
    o.append(f'<clipPath id="ridgeclip"><path d="{shape}"/></clipPath>')
    o.append(f'<path d="{shape}" fill="{BERO}"/>')
    o.append(f'<g clip-path="url(#ridgeclip)"><path d="{crest}" fill="none" stroke="{PAPER}" stroke-width="40" '
             f'filter="url(#soft)" opacity="0.9"/><path d="{crest}" fill="none" stroke="{PAPER}" stroke-width="7"/></g>')
    return "".join(o)


def wall(rng):
    o = [f'<rect x="-20" y="530" width="{W+40}" height="855" fill="{PLASTER}" filter="url(#baren)"/>']
    # night bokashi: dark under the eave, cool at the foot and on the far right
    o.append(f'<rect x="-20" y="530" width="{W+40}" height="855" fill="{DUSK}" opacity="0.16"/>')
    o.append(f'<rect x="-20" y="530" width="{W+40}" height="420" fill="url(#eaveshade)"/>')
    o.append(f'<rect x="-20" y="1080" width="{W+40}" height="305" fill="url(#wallfoot)"/>')
    o.append(f'<rect x="880" y="530" width="220" height="855" fill="url(#wallright)"/>')
    # warm glow on plaster from lantern and window
    o.append('<ellipse cx="163" cy="1010" rx="380" ry="420" fill="url(#glow)"/>')
    o.append('<ellipse cx="163" cy="1010" rx="200" ry="230" fill="url(#glow)" opacity="0.6"/>')
    o.append('<ellipse cx="750" cy="850" rx="360" ry="380" fill="url(#glow)" opacity="0.9"/>')
    for x in (70, 330, 880):
        d = poly([(x - 19, 528), (x + 19, 528), (x + 19, 1384), (x - 19, 1384)])
        o.append(warm(d, OCHRE))
        for k in (-7, 6):
            o.append(line((x + k, 580), (x + k + rng.uniform(-2, 2), 1340), BERO, 1.6, 'opacity="0.45"'))
    o.append(f'<rect x="-20" y="530" width="{W+40}" height="230" fill="url(#eaveshade2)"/>')
    o.append(warm(poly([(626, 626), (874, 626), (874, 1074), (626, 1074)]), OCHRE))
    o.append(kp(poly([(640, 640), (860, 640), (860, 1060), (640, 1060)]), 'url(#shoji)', 7))
    o.append(f'<rect x="644" y="644" width="212" height="412" fill="url(#shojicore)"/>')
    for i in (1, 2):
        x = 640 + 220 * i / 3
        o.append(line((x, 642), (x, 1058), BERO, 4))
    for j in range(1, 5):
        y = 640 + 420 * j / 5
        o.append(line((642, y), (858, y), BERO, 4))
    o.append(warm(poly([(612, 1074), (888, 1074), (888, 1092), (612, 1092)]), OCHRE))
    o.append(kp(snowcap(612, 888, 1074, 13, rng, 4), PAPER, 3.5))
    return "".join(o)


def roof(rng):
    o = []
    o.append(f'<rect x="-20" y="466" width="{W+40}" height="76" fill="{INK}" filter="url(#baren)"/>')
    for x in range(-6, W + 20, 34):
        o.append(f'<rect x="{x}" y="502" width="12" height="14" fill="{BERO}"/>')
    o.append(line((-20, 524), (W + 20, 524), BERO, 5))
    o.append(line((-20, 538), (W + 20, 538), BERO, 6))
    top = []
    for i in range(0, 47):
        x = -30 + i * 25
        y = 392 + 7 * math.sin(i * 1.7) + 5 * math.sin(i * 0.6 + 1) + rng.uniform(-3, 3)
        top.append((x, y))
    bot = []
    for i in range(46, -1, -1):
        x = -30 + i * 25 + rng.uniform(-4, 4)
        y = 474 + (11 if i % 3 == 0 else 3) + rng.uniform(-2, 4)
        bot.append((x, y))
    d = cr(top + bot)
    o.append(kp(d, PAPER, 5))
    o.append(f'<path d="{d}" fill="url(#roofshade)"/>')
    o.append(f'<path d="{d}" fill="none" stroke="{BERO}" stroke-width="5" stroke-linejoin="round"/>')
    for x in (120, 245, 268, 470, 700, 735, 940, 1010):
        L = rng.uniform(18, 40)
        o.append(kp(poly([(x - 6, 480), (x + 6, 480), (x + 1, 480 + L)]), PAPER, 2.5))
    return "".join(o)


def foundation(rng):
    o = [f'<g filter="url(#goma)"><rect x="-20" y="1378" width="{W+40}" height="70" fill="{BERO}" filter="url(#baren)"/></g>']
    o.append(line((-20, 1411), (W + 20, 1411), DUSK, 3))
    for i, x in enumerate(range(10, W + 20, 96)):
        o.append(line((x, 1381), (x, 1409), DUSK, 3))
        o.append(line((x + 48, 1413), (x + 48, 1446), DUSK, 3))
    o.append(kp(snowcap(-20, W + 20, 1380, 9, rng, 3, 30), PAPER, 3.5))
    return "".join(o)


def ground(rng):
    o = []
    top = []
    for i in range(0, 25):
        x = -30 + i * 48
        top.append((x, 1440 + 6 * math.sin(i * 1.3) + rng.uniform(-3, 3)))
    d = cr(top + [(W + 40, 1960), (-40, 1960)])
    o.append(f'<path d="{d}" fill="url(#snowg)" filter="url(#baren)"/>')
    o.append(f'<path d="{cr(top, closed=False)}" fill="none" stroke="{SHADOW}" stroke-width="22" filter="url(#soft4)" '
             f'transform="translate(0,14)" opacity="0.8"/>')
    o.append(f'<path d="{cr(top, closed=False)}" fill="none" stroke="{BERO}" stroke-width="3.5"/>')
    return "".join(o)


def path_stones(rng):
    o = []
    p0, p1, p2, p3 = (-40, 1905), (230, 1885), (400, 1660), (552, 1600)
    gp = [cbez(p0, p1, p2, p3, t / 20) for t in range(21)]
    o.append(f'<path d="{cr(gp, closed=False)}" fill="none" stroke="{SHADOW}" stroke-width="170" '
             f'stroke-linecap="round" opacity="0.6" filter="url(#soft)"/>')
    stones = []
    t = 0.0
    side = 1
    while t < 0.9:
        c = cbez(p0, p1, p2, p3, t)
        s = 1.0 - 0.45 * t
        rx, ry = 78 * s, 32 * s
        nxt = cbez(p0, p1, p2, p3, min(1, t + 0.01))
        ang = math.atan2(nxt[1] - c[1], nxt[0] - c[0])
        off = side * 14 * s
        cx = c[0] - math.sin(ang) * off
        cy = c[1] + math.cos(ang) * off * 0.5
        stones.append((cx, cy, rx, ry, ang * 0.25))
        side = -side
        t += 0.135 * s + 0.02
    # stones under each foot
    stones += [(412, 1566, 82, 19, 0.02), (734, 1566, 80, 18, -0.02), (574, 1592, 58, 16, 0.05)]
    for (cx, cy, rx, ry, rot) in stones:
        o.append(f'<ellipse cx="{cx+4:.1f}" cy="{cy+ry*0.55:.1f}" rx="{rx*1.02:.1f}" ry="{ry*0.8:.1f}" '
                 f'fill="{SHADOW}" filter="url(#soft4)"/>')
        o.append(kp(blob(cx, cy, rx, ry, rng, 10, 0.08, rot), DUSK, 4))
        k = max(3, int(rx / 14))
        for _ in range(k):
            a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 0.75)
            x = cx + rx * r * math.cos(a); y = cy + ry * r * math.sin(a) * 0.8
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(2.8, 6.0):.1f}" fill="{PAPER}"/>')
    return "".join(o)


def lantern(rng):
    o = []
    o.append('<ellipse cx="190" cy="1566" rx="44" ry="10" fill="#C3CAD8" filter="url(#soft4)"/>')
    o.append(kp(poly([(150, 1078), (176, 1078), (178, 1562), (148, 1562)]), BERO, 3))
    o.append(kp(poly([(128, 1532), (198, 1532), (204, 1562), (122, 1562)]), BERO, 3))
    # box
    o.append(warm(poly([(100, 940), (226, 940), (226, 1080), (100, 1080)]), 'url(#lanpaper)', 0))
    o.append(f'<rect x="100" y="940" width="126" height="140" fill="none" stroke="{BERO}" stroke-width="7"/>')
    o.append(line((163, 944), (163, 1076), BERO, 4))
    o.append(line((104, 1010), (222, 1010), BERO, 3))
    o.append(kp(poly([(92, 1080), (234, 1080), (226, 1094), (100, 1094)]), BERO, 3))
    # little roof with snow
    o.append(kp(poly([(84, 942), (242, 942), (214, 914), (112, 914)]), BERO, 3))
    o.append(kp(snowcap(84, 242, 916, 22, rng, 6, 16), PAPER, 4))
    # glow halo
    o.append('<ellipse cx="163" cy="1010" rx="190" ry="190" fill="url(#glow)" opacity="0.85"/>')
    return "".join(o)


def fence(rng):
    o = []
    o.append(f'<path d="{poly([(700, 1496), (1100, 1496), (1100, 1512), (700, 1512)])}" fill="{SHADOW}" filter="url(#soft4)"/>')
    thin = [774, 900, 1040]
    for x in thin:
        o.append(warm(poly([(x - 7, 1312), (x + 7, 1312), (x + 7, 1502), (x - 7, 1502)]), OCHRE, 3))
        for y in (1380, 1466):
            o.append(line((x - 6, y), (x + 6, y), BERO, 2.5))
        o.append(kp(snowcap(x - 8, x + 8, 1312, 9, rng, 3, 8), PAPER, 3))
    for y in (1336, 1432):
        o.append(warm(poly([(712, y - 6), (1100, y - 6), (1100, y + 6), (712, y + 6)]), OCHRE, 3))
        o.append(kp(snowcap(712, 1100, y - 6, 8, rng, 3, 26), PAPER, 3))
    for x in (728, 820, 980):
        o.append(warm(poly([(x - 13, 1290), (x + 13, 1290), (x + 13, 1504), (x - 13, 1504)]), OCHRE))
        o.append(line((x - 4, 1300), (x - 4, 1495), BERO, 1.5, 'opacity="0.5"'))
        o.append(kp(snowcap(x - 15, x + 15, 1290, 16, rng, 4, 10), PAPER, 3.5))
    o.append(ring(820, 1360))
    # drift along the fence foot
    pts = [(700 + i * 30, 1500 + rng.uniform(-6, 2) - 6 * math.sin(i)) for i in range(15)]
    o.append(kp(cr(pts + [(1110, 1530), (700, 1530)]), PAPER, 0))
    o.append(f'<path d="{cr(pts, closed=False)}" fill="none" stroke="{BERO}" stroke-width="3"/>')
    return "".join(o)


def ring(x, y):
    return (f'<circle cx="{x}" cy="{y}" r="18" fill="none" stroke="{BERO}" stroke-width="11"/>'
            f'<circle cx="{x+2}" cy="{y-1}" r="18" fill="none" stroke="{BRASS}" stroke-width="6"/>'
            f'<path d="M{x-12},{y-9} A15,15 0 0 1 {x+3},{y-15}" fill="none" stroke="{PAPER}" stroke-width="2.5" stroke-linecap="round"/>')


# ---------------- scarecrow (kakashi) ----------------
def kakashi(rng, arm_l=95, arm_r=95, mound=True):
    o = []
    o.append(warm(poly([(-7, 12), (7, 12), (6, -236), (-6, -236)]), OCHRE, 4))
    o.append(warm(poly([(-arm_l, -186), (arm_r, -186), (arm_r, -174), (-arm_l, -174)]), OCHRE, 4))
    for sx, L in ((-1, arm_l), (1, arm_r)):
        for k in range(6):
            a = (-0.6 + k * 0.24)
            ex = sx * (L + 20 * math.cos(a)); ey = -180 + 20 * math.sin(a)
            o.append(line((sx * (L - 4), -180), (ex, ey), STRAW, 4))
            o.append(line((sx * (L - 4), -180), (ex, ey), BERO, 1.4, 'opacity="0.8"'))
    # mino straw cape: 3 tiers, finely fringed, bottom tier first
    tiers = [(-162, -98, 46, 64), (-198, -142, 38, 54), (-228, -180, 26, 42)]
    for ti, (yt, yb, wt, wb) in enumerate(tiers):
        pts = [(-wt, yt), (wt, yt)]
        n = int(wb * 2 / 6)
        for i in range(n + 1):
            x = wb - i * (2 * wb / n)
            y = yb + rng.uniform(0, 12) * (1 if i % 2 == 0 else 0.35)
            pts.append((x + rng.uniform(-1.5, 1.5), y))
        d = poly(pts)
        cid = f"mino{rng.randint(0, 10**8)}"
        o.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
        o.append(warm(d, STRAW, 0))
        hatch = []
        for i in range(-12, 13):
            x0 = i * wt / 12 * 0.95
            x1 = i * wb / 12 * 1.05 + rng.uniform(-2, 2)
            hatch.append(line((x0, yt), (x1, yb + 14), BERO, 1.6, f'opacity="{rng.uniform(0.45, 0.85):.2f}"'))
        hatch.append(f'<path d="M{-wb},{yb-4} L{wb},{yb-4} L{wb},{yb+16} L{-wb},{yb+16} Z" fill="{OCHRE}" opacity="0.35"/>')
        o.append(f'<g clip-path="url(#{cid})">{"".join(hatch)}</g>')
        o.append(f'<path d="{d}" fill="none" stroke="{BERO}" stroke-width="3.5" stroke-linejoin="round"/>')
    # head: round straw bundle tied off at the neck with a rope (no face)
    hc = (0, -262)
    o.append(warm(f"M{hc[0]-42},{hc[1]} a42,42 0 1 0 84,0 a42,42 0 1 0 -84,0 Z", STRAW, 4))
    hid = f"hd{rng.randint(0, 10**8)}"
    o.append(f'<clipPath id="{hid}"><circle cx="{hc[0]}" cy="{hc[1]}" r="40"/></clipPath>')
    st = []
    for i in range(-6, 7):
        st.append(f'<path d="M{i*3},{hc[1]-44} Q{i*12},{hc[1]-4} {i*5},{hc[1]+44}" fill="none" stroke="{BERO}" '
                  f'stroke-width="1.7" opacity="0.55"/>')
    o.append(f'<g clip-path="url(#{hid})">{"".join(st)}</g>')
    # rope tie under the head (twisted)
    o.append(kp(f"M-22,{hc[1]+34} Q0,{hc[1]+44} 22,{hc[1]+34} L22,{hc[1]+46} Q0,{hc[1]+56} -22,{hc[1]+46} Z", OCHRE, 3))
    for i in range(-3, 4):
        o.append(line((i * 6 - 3, hc[1] + 37 + abs(i) * 0.6), (i * 6 + 3, hc[1] + 51 - abs(i) * 0.6), BERO, 1.8))
    kd = "M-92,-292 Q0,-284 92,-292 L8,-348 Q0,-352 -8,-348 Z"
    o.append(warm(kd, OCHRE, 4.5))
    for i in (-62, -31, 31, 62):
        o.append(line((0, -346), (i, -290), BERO, 1.6, 'opacity="0.7"'))
    sp = [(-68, -304), (-52, -322), (-32, -334), (-12, -354), (6, -359), (26, -345), (46, -330), (64, -316), (74, -303),
          (56, -299), (36, -305), (14, -299), (-8, -305), (-30, -298), (-52, -303)]
    sp = [(x + rng.uniform(-2, 2), y + rng.uniform(-2, 2)) for x, y in sp]
    o.append(kp(cr(sp), PAPER, 3.5))
    if mound:
        o.append(f'<ellipse cx="8" cy="10" rx="56" ry="10" fill="{SHADOW}" filter="url(#soft4)"/>')
        o.append(kp(blob(0, 2, 36, 13, rng, 8, 0.12), PAPER, 3.5))
    return "".join(o)


def mooks(rng):
    o = []
    o.append(f'<g transform="translate(1082,1530)">{kakashi(rng, 95, 95)}</g>')
    ax, ay, tilt, armr = 905, 1533, 6, 57
    o.append(f'<g transform="translate({ax},{ay}) rotate({tilt})">{kakashi(rng, 80, armr)}</g>')
    o.append(ring(980, 1360))
    # click sparks at the ring
    for k in range(5):
        a = math.radians(-165 + k * 37)
        o.append(line((980 + 30 * math.cos(a), 1360 + 30 * math.sin(a)), (980 + 52 * math.cos(a), 1360 + 52 * math.sin(a)),
                      BERO, 6))
        o.append(line((980 + 30 * math.cos(a), 1360 + 30 * math.sin(a)), (980 + 52 * math.cos(a), 1360 + 52 * math.sin(a)),
                      BRASS, 2.5))
    hx, hy = ax + 262 * math.sin(math.radians(tilt)), ay - 262 * math.cos(math.radians(tilt))
    for sgn in (-1, 1):
        for k, r in enumerate((64, 80)):
            c0 = 0 if sgn > 0 else 180
            a0, a1 = math.radians(c0 - 24), math.radians(c0 + 24)
            p0 = (hx + r * math.cos(a0), hy + 6 + r * math.sin(a0)); p1 = (hx + r * math.cos(a1), hy + 6 + r * math.sin(a1))
            o.append(f'<path d="M{P(*p0)} A{r},{r} 0 0 1 {P(*p1)}" fill="none" stroke="{BERO}" '
                     f'stroke-width="{4.5 - k}" stroke-linecap="round"/>')
    kx, ky = ax + 352 * math.sin(math.radians(tilt)), ay - 352 * math.cos(math.radians(tilt))
    for i in range(14):
        ang = math.radians(-90 + (-76 + 152 * i / 13) + rng.uniform(-5, 5))
        dist = rng.uniform(42, 125)
        sz = rng.uniform(10, 16) * (1.2 - dist / 260)
        cx, cy = kx + dist * math.cos(ang), ky + dist * math.sin(ang) * 0.85
        ux, uy = math.cos(ang), math.sin(ang)
        nx, ny = -uy, ux
        tail = (cx - ux * sz * 2.1, cy - uy * sz * 2.1)
        d = (f"M{P(*tail)} C{P(cx - ux * sz * 0.6 + nx * sz * 0.9, cy - uy * sz * 0.6 + ny * sz * 0.9)} "
             f"{P(cx + ux * sz * 1.0 + nx * sz * 1.05, cy + uy * sz * 1.0 + ny * sz * 1.05)} {P(cx + ux * sz, cy + uy * sz)} "
             f"C{P(cx + ux * sz * 1.0 - nx * sz * 1.05, cy + uy * sz * 1.0 - ny * sz * 1.05)} "
             f"{P(cx - ux * sz * 0.6 - nx * sz * 0.9, cy - uy * sz * 0.6 - ny * sz * 0.9)} {P(*tail)} Z")
        o.append(kp(d, PAPER, 3))
    cx_, cy_, lean = 805, 1484, -18
    o.append(f'<g transform="translate({cx_},{cy_}) rotate({lean})">{kakashi(rng, 74, 92, mound=False)}</g>')
    for k, (y, L) in enumerate(((1206, 60), (1238, 84), (1272, 54))):
        x0 = 836 + k * 8
        o.append(f'<path d="M{x0},{y} q{L*0.5},{-7} {L},{-3}" fill="none" stroke="{BERO}" stroke-width="3.5" stroke-linecap="round"/>')
    for i in range(7):
        a = math.radians(200 + i * 18)
        o.append(f'<circle cx="{805 + 40 * math.cos(a) + 30:.1f}" cy="{1520 + 18 * math.sin(a):.1f}" r="{rng.uniform(4, 7):.1f}" '
                 f'fill="{PAPER}" stroke="{BERO}" stroke-width="2.2"/>')
    return "".join(o)


def hero_geom():
    p = dict(POSE)
    p.update(hip=(530, 1100), kn_l=(668, 1305), ft_l=(716, 1556), kn_r=(478, 1325), ft_r=(392, 1556))
    p['neck'] = (556, 736 + UDY)
    p['sh_l'] = (560, 748 + UDY)
    p['sh_r'] = (536, 748 + UDY)
    (ax, ay), (bx, by) = BROOM_TOP, (850, 1470)

    def on_shaft(y):
        return (ax + (bx - ax) * (y - ay) / (by - ay), y)
    ha_r, ha_l = on_shaft(843 + UDY), on_shaft(996 + UDY)
    el_r = (524, 886 + UDY)   # far arm foreshortened: elbow tucked down-back
    el_l = ik(p['sh_l'], ha_l, 134, 137, (630, 870 + UDY))
    p.update(el_r=el_r, ha_r=ha_r, el_l=el_l, ha_l=ha_l)
    return p


def hero_shapes(p):
    R1, R2 = 15, 11
    sh = []
    sh += capsule(p['hip'], p['neck'], 19, 15)
    sh += capsule(p['neck'], (560, 684 + UDY), 11, 11)
    for a, b in (('hip', 'kn_l'), ('kn_l', 'ft_l'), ('hip', 'kn_r'), ('kn_r', 'ft_r')):
        sh += capsule(p[a], p[b], R1 if a == 'hip' else 13, 12.5 if a == 'hip' else R2)
    sh += capsule(p['ft_l'], (p['ft_l'][0] + 36, p['ft_l'][1] + 5), 11, 8.5)
    sh += capsule(p['ft_r'], (p['ft_r'][0] + 32, p['ft_r'][1] + 5), 11, 8.5)
    for s, e, h in (('neck', 'el_r', 'ha_r'), ('neck', 'el_l', 'ha_l')):
        shp = p['sh_r'] if e == 'el_r' else p['sh_l']
        sh += capsule(p['neck'], shp, 14, 14)
        sh += capsule(shp, p[e], 14, 12)
        sh += capsule(p[e], p[h], 12, 10.5)
    sh.append(('path', ell_path(566, 630 + UDY, 50, 64, HEADROT)))
    return sh


def hero(rng):
    p = hero_geom()
    o = []
    o.append(f'<ellipse cx="560" cy="1570" rx="215" ry="13" fill="{SHADOW}" filter="url(#soft4)"/>')
    shs = hero_shapes(p)
    o.append(f'<clipPath id="haloclip"><rect x="0" y="1368" width="{W}" height="90"/></clipPath>')
    o.append(f'<g clip-path="url(#haloclip)">{shapes_svg(shs, PAPER, PAPER, 6)}</g>')
    o.append(f'<clipPath id="rimclip"><rect x="0" y="780" width="{W}" height="800"/></clipPath>')
    o.append(f'<g clip-path="url(#rimclip)" transform="translate(-3.5,-1)" opacity="0.9">{shapes_svg(shs, INNER)}</g>')
    o.append(f'<clipPath id="rimclip2"><rect x="560" y="560" width="200" height="420"/></clipPath>')
    o.append(f'<g clip-path="url(#rimclip2)" transform="translate(3,-1)" opacity="0.8">{shapes_svg(shs, INNER)}</g>')
    o.append(f'<g filter="url(#goma)">{shapes_svg(shs, BERO)}</g>')
    return "".join(o), p


def hero_head(rng):
    """Tenugui (hachimaki) tails, knot, band, head snow, drawn after the broom shaft; head tilted forward."""
    o = [f'<g transform="translate(0,{UDY})"><g transform="rotate({HEADROT} 566 630)">']
    knot = (506, 610)
    for tip, bend in (((456, 586), (-2, -9)), ((452, 628), (-6, 5))):
        mx, my = (knot[0] + tip[0]) / 2 + bend[0], (knot[1] + tip[1]) / 2 + bend[1]
        ang = math.atan2(tip[1] - knot[1], tip[0] - knot[0])
        nx, ny = -math.sin(ang), math.cos(ang)
        d = (f"M{P(knot[0] + nx * 8, knot[1] + ny * 8)} Q{P(mx + nx * 8, my + ny * 8)} {P(tip[0] + nx * 7, tip[1] + ny * 7)} "
             f"L{P(tip[0] - math.cos(ang) * 8, tip[1] - math.sin(ang) * 8)} "
             f"L{P(tip[0] - nx * 7, tip[1] - ny * 7)} Q{P(mx - nx * 8, my - ny * 8)} {P(knot[0] - nx * 8, knot[1] - ny * 8)} Z")
        o.append(warm(d, CREAM, 3.5))
    band = cr([(508, 598), (536, 593), (570, 588), (604, 585), (624, 586), (624, 608), (604, 607), (570, 611),
               (536, 616), (508, 622), (502, 610)])
    o.append(f'<g clip-path="url(#headclip)">{kp(band, CREAM, 0)}'
             f'<path d="{band}" fill="none" stroke="{BERO}" stroke-width="2.5"/>'
             f'{line((552, 600), (574, 597), BERO, 1.6, "opacity=\"0.45\"")}'
             f'{line((584, 600), (604, 597), BERO, 1.6, "opacity=\"0.45\"")}</g>')
    o.append(kp(blob(knot[0], knot[1], 13, 11, rng, 7, 0.1), CREAM, 3.5))
    o.append(kp(cr([(540, 575), (552, 569), (570, 567), (586, 570), (594, 576), (580, 577), (562, 575), (548, 578)]),
                PAPER, 3))
    o.append('</g>')
    for (cx, cy, w) in ((540, 735, 11), (568, 736, 10)):
        o.append(kp(cr([(cx - w, cy + 2), (cx - w * 0.2, cy - 4), (cx + w * 0.6, cy - 3), (cx + w, cy + 2), (cx, cy + 3)]),
                    PAPER, 2.0))
    o.append('</g>')
    return "".join(o)


def broom_shaft(p):
    a, b = BROOM_TOP, (850, 1470)
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    o = [line(a, b, BERO, 21),
         f'<g transform="translate({MIS[0]},{MIS[1]})">{line(a, b, OCHRE, 12)}</g>',
         line((a[0] + 3 + ux * 12, a[1] + uy * 12), (a[0] + 3 + ux * L * 0.5, a[1] + uy * L * 0.5), PAPER, 2, 'opacity="0.35"')]
    for h in (p['ha_r'], p['ha_l']):
        o.append(f'<circle cx="{h[0]:.1f}" cy="{h[1]:.1f}" r="16" fill="{BERO}"/>')
    return "".join(o)


def bristles(rng):
    o = []
    collar = (850, 1470)
    ang = math.atan2(970, 430)
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    o.append(f'<ellipse cx="900" cy="1566" rx="160" ry="12" fill="{SHADOW}" filter="url(#soft4)"/>')
    tips = []
    for i in range(22):
        t = i / 21
        x = 760 + 270 * t + rng.uniform(-4, 4)
        y = 1548 + 18 * math.sin(math.pi * t) + rng.uniform(-2, 2)
        tips.append((x, y))
    # fan mass behind the twigs
    fan = [(collar[0] - 10, collar[1] + 2)] + tips[::3] + [tips[-1], (collar[0] + 12, collar[1] - 2)]
    o.append(warm(cr(fan), STRAW, 0, extra='opacity="0.9"'))
    for i, (x, y) in enumerate(tips):
        s = (collar[0] + rng.uniform(-8, 8), collar[1] + rng.uniform(-2, 6))
        m = ((s[0] + x) / 2 - 10 + rng.uniform(-6, 6), (s[1] + y) / 2 - 8)
        col = OCHRE if i % 2 == 0 else BERO
        w = 4.2 if col == BERO else 5
        o.append(f'<path d="M{P(*s)} Q{P(*m)} {P(x, y)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round"/>')
    o.append(f'<path d="{cr(fan)}" fill="none" stroke="{BERO}" stroke-width="3.5" stroke-linejoin="round"/>')
    # binding collar
    c0 = (collar[0] - ux * 26, collar[1] - uy * 26)
    cd = poly([(c0[0] + nx * 11, c0[1] + ny * 11), (collar[0] + nx * 13, collar[1] + ny * 13),
               (collar[0] - nx * 13, collar[1] - ny * 13), (c0[0] - nx * 11, c0[1] - ny * 11)])
    o.append(kp(cd, BERO, 3))
    for k in (0.3, 0.65):
        q = (c0[0] + (collar[0] - c0[0]) * k, c0[1] + (collar[1] - c0[1]) * k)
        o.append(line((q[0] + nx * 11, q[1] + ny * 11), (q[0] - nx * 11, q[1] - ny * 11), CREAM, 2.5))
    # swept-snow spray arcing up-right
    a, c, b = (940, 1545), (1000, 1380), (1090, 1420)
    for i in range(30):
        t = rng.uniform(0.05, 1.0) ** 0.8
        q = qbez(a, c, b, t)
        spread = 10 + 34 * t
        r = 9 - 4.5 * t + rng.uniform(-1.2, 1.2)
        o.append(f'<circle cx="{q[0]+rng.uniform(-spread, spread):.1f}" cy="{q[1]+rng.uniform(-spread, spread)*0.8:.1f}" '
                 f'r="{max(3.5, r):.1f}" fill="{PAPER}" stroke="{BERO}" stroke-width="2.4"/>')
    # sweep swoosh just above the bristle tips
    for k, (y0, L) in enumerate(((1528, 120), (1508, 90))):
        o.append(f'<path d="M{1040 - L},{y0 + 10} q{L*0.55},{-22 - k * 6} {L},{-4}" fill="none" stroke="{BERO}" '
                 f'stroke-width="{3.5 - k * 0.8}" stroke-linecap="round" opacity="0.85"/>')
    return "".join(o)


def breath():
    o = [f'<g transform="translate(0,{UDY})">'] + [f'<ellipse cx="678" cy="676" rx="70" ry="30" fill="{PAPER}" opacity="0.35" filter="url(#soft)"/>']
    cs = [(624, 690, 10), (650, 682, 16), (682, 670, 22), (714, 676, 14)]
    o += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{BERO}" stroke="{BERO}" stroke-width="6"/>' for x, y, r in cs]
    o += [f'<circle cx="{x}" cy="{y}" r="{r}" fill="{PAPER}"/>' for x, y, r in cs]
    o.append(f'<path d="M668,660 q10,-8 24,-4" fill="none" stroke="{SHADOW}" stroke-width="3" stroke-linecap="round"/>')
    o.append('</g>')
    return "".join(o)


def pine(rng):
    o = []
    limb = [(-40, 150), (40, 168), (130, 190), (220, 214), (300, 238), (380, 262), (450, 288), (515, 310)]
    up, dn = [], []
    for i, (x, y) in enumerate(limb):
        w = 32 - 22 * i / (len(limb) - 1)
        up.append((x, y - w / 2 + rng.uniform(-2, 2)))
        dn.append((x, y + w / 2 + rng.uniform(-2, 2)))
    twigs = [((130, 190), (176, 120)), ((220, 214), (214, 300)), ((300, 238), (356, 190)), ((380, 262), (410, 350)),
             ((40, 168), (36, 250)), ((450, 288), (500, 360)), ((80, 178), (100, 120))]
    o.append(kp(cr(up + dn[::-1]), INK, 4))
    for s_, e in twigs:
        o.append(line(s_, e, BERO, 12))
        o.append(line(s_, e, INK, 6))
    # needle clusters: several overlapping tufts each, so they read as masses rather than stamps
    clusters = [((40, 262), 1.05, 4), ((140, 118), 0.85, 3), ((220, 306), 1.1, 5), ((356, 196), 0.95, 4),
                ((420, 350), 0.95, 4), ((505, 330), 0.75, 3)]
    tufts = []
    for (cx, cy), s, n in clusters:
        for k in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            r = 0 if k == 0 else rng.uniform(28, 52) * s
            ss = s * (1.0 if k == 0 else rng.uniform(0.6, 0.85))
            tufts.append((cx + r * math.cos(ang), cy + r * math.sin(ang) * 0.55 - (6 if k else 0), ss, rng.uniform(-14, 14)))
    tufts.sort(key=lambda t: t[1])
    for (cx, cy, s, rot) in tufts:
        o.append(f'<g transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})">{tuft(rng, cx, cy, s, snow=True)}</g>')
    o.append(kp(cr([(140, 184), (190, 193), (250, 206), (310, 228), (296, 238), (236, 220), (176, 204)]), PAPER, 3.5))
    return "".join(o)


def snowfall(rng):
    o = []

    def blocked(x, y, r):
        if ((x - 600) / 140) ** 2 + ((y - 630 - UDY) / 110) ** 2 < 1:
            return True
        if 740 < x < 1060 and 1450 < y < 1590:
            return True
        return False

    far = 0
    while far < 120:
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(3, 5)
        if blocked(x, y, r):
            continue
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{PAPER}" opacity="0.8"/>')
        far += 1
    near = 0
    while near < 34:
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(9, 13)
        if blocked(x, y, r):
            continue
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r*1.5:.1f}" fill="url(#flake)"/>')
        near += 1
    return "".join(o)


def texture(rng):
    o = [f'<rect width="{W}" height="{H}" fill="#fff" filter="url(#washi)" style="mix-blend-mode:multiply" opacity="{CFG["washi"]}"/>']
    fib = []
    for i in range(420):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        L = rng.uniform(14, 70); a = rng.uniform(0, math.pi)
        c = (x + L * math.cos(a) * 0.5 + rng.uniform(-9, 9), y + L * math.sin(a) * 0.5 + rng.uniform(-9, 9))
        e = (x + L * math.cos(a), y + L * math.sin(a))
        col, op = (PAPER, rng.uniform(0.10, 0.22)) if i % 2 else (BERO, rng.uniform(0.05, 0.09))
        fib.append(f'<path d="M{P(x, y)} Q{P(*c)} {P(*e)}" fill="none" stroke="{col}" stroke-width="{rng.uniform(0.6, 1.4):.1f}" opacity="{op:.2f}"/>')
    o.append("".join(fib))
    return "".join(o)


def ground_light(rng):
    o = [f'<rect x="-20" y="1600" width="{W+40}" height="340" fill="url(#snownight)"/>',
         f'<ellipse cx="1000" cy="1660" rx="420" ry="200" fill="{DUSK}" opacity="0.14" filter="url(#soft16)"/>']
    o.append('<g transform="translate(2,-1)"><ellipse cx="163" cy="1580" rx="260" ry="70" fill="url(#poolg)" opacity="0.85"/>')
    o.append(f'<path d="{poly([(628, 1452), (872, 1452), (1010, 1640), (520, 1640)])}" fill="url(#spillg)" '
             f'opacity="0.6" filter="url(#soft)"/></g>')
    return "".join(o)


def ell_path(cx, cy, rx, ry, rot):
    t = math.radians(rot)
    x0, y0 = cx + rx * math.cos(t), cy + rx * math.sin(t)
    x1, y1 = cx - rx * math.cos(t), cy - rx * math.sin(t)
    return f"M{P(x0, y0)} A{rx},{ry} {rot} 1 1 {P(x1, y1)} A{rx},{ry} {rot} 1 1 {P(x0, y0)} Z"


def tuft(rng, cx, cy, s, snow=True):
    o = []
    L0 = 70 * s
    rim = []
    n = 26
    for k in range(n + 1):
        a = math.radians(-6 + 192 * k / n)
        L = L0 * (1.0 if k % 2 == 0 else 0.78) * rng.uniform(0.92, 1.06)
        rim.append((cx + L * math.cos(a), cy + L * math.sin(a) * 0.7))
    d = poly([(cx, cy - 6)] + rim)
    o.append(f'<path d="{d}" fill="{INK}" stroke="{BERO}" stroke-width="2" stroke-linejoin="round"/>')
    if not snow:
        return "".join(o)
    for k in range(14):
        a = math.radians(4 + 172 * k / 13 + rng.uniform(-4, 4))
        L = L0 * rng.uniform(0.7, 0.95)
        o.append(line((cx, cy), (cx + L * math.cos(a), cy + L * math.sin(a) * 0.7), BERO, 3.2))
    w = L0 * rng.uniform(0.8, 0.92)
    hh = rng.uniform(0.85, 1.15)
    sp = [(cx - w, cy + 5), (cx - w * 0.75, cy - 9 * s * hh), (cx - w * 0.35, cy - 20 * s * hh), (cx + w * 0.05, cy - 23 * s * hh),
          (cx + w * 0.45, cy - 17 * s * hh), (cx + w * 0.82, cy - 6 * s * hh), (cx + w, cy + 6), (cx + w * 0.55, cy + 10),
          (cx + w * 0.3, cy + 16), (cx, cy + 9), (cx - w * 0.35, cy + 14), (cx - w * 0.7, cy + 9)]
    sp = [(x + rng.uniform(-3, 3), y + rng.uniform(-2, 2)) for x, y in sp]
    o.append(kp(cr(sp), PAPER, 4))
    o.append(f'<path d="{cr(sp)}" fill="url(#cushion)"/>')
    return "".join(o)


def build():
    rng = random.Random(7)
    hero_svg, p = hero(random.Random(3))
    body = [
        sky(), ridge(random.Random(5)), wall(random.Random(11)), roof(random.Random(13)), foundation(random.Random(17)),
        ground(random.Random(19)), path_stones(random.Random(23)), ground_light(random.Random(20)), lantern(random.Random(29)), fence(random.Random(31)),
        mooks(random.Random(37)), hero_svg, broom_shaft(p), hero_head(random.Random(3)), bristles(random.Random(41)),
        breath(), pine(random.Random(43)),
    ]
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', defs(),
           f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
           f'<g filter="url(#carve)">{"".join(body)}</g>',
           snowfall(random.Random(47)), texture(random.Random(53)), '</svg>']
    return "\n".join(svg)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'still.svg')
    for kv in sys.argv[2:]:
        k, v = kv.split('=')
        CFG[k] = float(v)
    with open(out, 'w') as f:
        f.write(build())
    print('wrote', out)
