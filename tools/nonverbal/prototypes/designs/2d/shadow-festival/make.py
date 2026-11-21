#!/usr/bin/env python3
"""SUMMER SHADOW THEATRE / 夏夜の影絵芝居 -- NEVER DROP 'three heads' still (1080x1920 SVG).
Everything is code-drawn: backlit washi screen (gradient + mottling + generated fibres), black cut-paper puppets
with SVG-mask perforations, gel inserts, per-depth blur, festival lanterns and an audience silhouette band.
Usage: python3 make.py [out.svg]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from pose2d import POSE, GROUND_Y  # noqa: E402,F401

W, H = 1080, 1920
HOT, AMBER, EDGE, FALL = '#FFE6A6', '#F5C66B', '#C8792E', '#6B3418'
TEAL, AUD, WOOD, BLK = '#12313A', '#0A161A', '#2A1A10', '#151110'
VERM, INDIGO, JADE, LANT, TGLOW = '#D1452C', '#33508F', '#3E8E6E', '#F2A541', '#FF8A5A'

SX0, SY0, SX1, SY1 = 50, 236, 1030, 1704          # screen opening
GCX, GCY, GRX, GRY = 540, 980, 660, 900            # lamp gradient ellipse

P = dict(
    b_opacity=0.55, b_blur=14,
    asa_a=66, asa_w=2.8, robe_border=30, beard_w=2.7,
    gel_light='#7393DA', gel_mid='#3A579C', gel_dark='#1A2A58',
    fibres=420,
    vignette=0.55,
    grain=0.07,
    future_dots=False,
    moth=True,
    bubble=True,
    smoke=True,
)


def f(v):
    s = f'{v:.1f}'
    return s[:-2] if s.endswith('.0') else s


def hx(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def rgbhex(t):
    return '#' + ''.join(f'{max(0, min(255, int(round(v)))):02X}' for v in t)


def mix(a, b, t):
    a, b = hx(a), hx(b)
    return rgbhex([a[i] + (b[i] - a[i]) * t for i in range(3)])


STOPS = [(0, HOT), (0.45, AMBER), (0.8, EDGE), (1.0, FALL)]


def scr_col(x, y):
    t = math.hypot((x - GCX) / GRX, (y - GCY) / GRY)
    if t >= 1:
        return FALL
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t <= t1:
            return mix(c0, c1, (t - t0) / (t1 - t0))
    return FALL


def pts(p):
    return ' '.join(f'{f(x)},{f(y)}' for x, y in p)


def poly_d(p, close=True):
    return 'M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in p) + (' Z' if close else '')


def smooth_d(p, closed=True, k=0.5):
    """Catmull-Rom -> cubic Bezier."""
    n = len(p)
    if closed:
        seq = [p[-1]] + p + [p[0], p[1]]
        rng = range(1, n + 1)
    else:
        seq = [p[0]] + p + [p[-1]]
        rng = range(1, n)
    d = f'M{f(seq[1][0])},{f(seq[1][1])}'
    for i in rng:
        p0, p1, p2, p3 = seq[i - 1], seq[i], seq[i + 1], seq[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) * k / 3, p1[1] + (p2[1] - p0[1]) * k / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * k / 3, p2[1] - (p3[1] - p1[1]) * k / 3)
        d += f' C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}'
    return d + (' Z' if closed else '')


def peg(a, b, w, r=None, ext=None, fill=BLK, extra=''):
    """rounded rectangle plate from joint a to joint b."""
    r = w * 0.35 if r is None else r
    ext = w * 0.45 if ext is None else ext
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) - 90
    return (f'<rect x="{f(-w / 2)}" y="{f(-ext)}" width="{f(w)}" height="{f(L + 2 * ext)}" rx="{f(r)}" '
            f'transform="translate({f(a[0])},{f(a[1])}) rotate({f(ang)})" fill="{fill}" {extra}/>')


def taper(a, b, w1, w2, fill=BLK):
    """tapered plate with round ends."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    q = [(a[0] + nx * w1 / 2, a[1] + ny * w1 / 2), (b[0] + nx * w2 / 2, b[1] + ny * w2 / 2),
         (b[0] - nx * w2 / 2, b[1] - ny * w2 / 2), (a[0] - nx * w1 / 2, a[1] - ny * w1 / 2)]
    return (f'<path d="{poly_d(q)}" fill="{fill}"/><circle cx="{f(a[0])}" cy="{f(a[1])}" r="{f(w1 / 2)}" fill="{fill}"/>'
            f'<circle cx="{f(b[0])}" cy="{f(b[1])}" r="{f(w2 / 2)}" fill="{fill}"/>')


def rivet(x, y, r=6, ring=2):
    c = scr_col(x, y)
    return (f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r + ring / 2 + 0.5)}" fill="none" stroke="{c}" stroke-width="{f(ring)}"/>'
            f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{BLK}"/>')


def asanoha(x0, y0, x1, y1, a):
    h = a * math.sqrt(3) / 2
    rows = int((y1 - y0) / h) + 3
    cols = int((x1 - x0) / a) + 3

    def row(j):
        return [(x0 - a + i * a + (j % 2) * a / 2, y0 - h + j * h) for i in range(cols)]
    segs = set()

    def add(p, q):
        key = tuple(sorted([(round(p[0], 1), round(p[1], 1)), (round(q[0], 1), round(q[1], 1))]))
        segs.add(key)
    for j in range(rows):
        merged = sorted(row(j) + row(j + 1), key=lambda p: p[0])
        for k in range(len(merged) - 2):
            A, B, Cc = merged[k], merged[k + 1], merged[k + 2]
            g = ((A[0] + B[0] + Cc[0]) / 3, (A[1] + B[1] + Cc[1]) / 3)
            add(A, B), add(B, Cc), add(A, Cc)
            add(g, A), add(g, B), add(g, Cc)
    return ' '.join(f'M{f(p[0])},{f(p[1])} L{f(q[0])},{f(q[1])}' for p, q in segs)


def rot(p, c, deg):
    a = math.radians(deg)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))


# ----------------------------------------------------------------------------------------------------------------
defs = []
body = []


def D(s):
    defs.append(s)


def A(s):
    body.append(s)


def blur_filter(fid, sd):
    D(f'<filter id="{fid}" filterUnits="userSpaceOnUse" x="-200" y="-200" width="1480" height="2320">'
      f'<feGaussianBlur stdDeviation="{sd}"/></filter>')


for fid, sd in [('b06', 0.6), ('b08', 0.8), ('b10', 1.0), ('b14', P['b_blur']), ('b2', 2.2), ('b3', 3), ('b5', 5),
                ('b9', 9), ('b20', 20), ('b40', 40), ('rodb', 1.1)]:
    blur_filter(fid, sd)

# screen gradient
D(f'<radialGradient id="gScr" gradientUnits="userSpaceOnUse" cx="{GCX}" cy="{GCY}" r="{GRY}" '
  f'gradientTransform="translate({GCX},{GCY}) scale({GRX / GRY:.4f},1) translate({-GCX},{-GCY})">'
  + ''.join(f'<stop offset="{t}" stop-color="{c}"/>' for t, c in STOPS) + '</radialGradient>')
D('<radialGradient id="gCore" gradientUnits="userSpaceOnUse" cx="540" cy="960" r="300">'
  '<stop offset="0" stop-color="#FFF6D8" stop-opacity=".55"/><stop offset=".5" stop-color="#FFEFC0" stop-opacity=".18"/>'
  '<stop offset="1" stop-color="#FFE6A6" stop-opacity="0"/></radialGradient>')
D(f'<clipPath id="cScr"><rect x="{SX0}" y="{SY0}" width="{SX1 - SX0}" height="{SY1 - SY0}"/></clipPath>')
# paper
D('<filter id="fFib" filterUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">'
  '<feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="3" seed="11"/>'
  '<feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  -1.6 0 0 0 1.05"/></filter>')
D('<filter id="fMot" filterUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">'
  '<feTurbulence type="fractalNoise" baseFrequency="0.0045 0.0065" numOctaves="4" seed="4"/>'
  '<feColorMatrix values="0 0 0 0 0.42  0 0 0 0 0.2  0 0 0 0 0.09  1.9 0 0 0 -0.75"/></filter>')
D('<filter id="fGrain" filterUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">'
  '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7"/>'
  '<feColorMatrix values="0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0 0 0 0 1"/></filter>')
D('<radialGradient id="gVig" cx="540" cy="900" r="1150" gradientUnits="userSpaceOnUse">'
  '<stop offset=".45" stop-color="#05090B" stop-opacity="0"/><stop offset=".8" stop-color="#05090B" stop-opacity=".45"/>'
  '<stop offset="1" stop-color="#05090B" stop-opacity=".9"/></radialGradient>')
D(f'<radialGradient id="gLant"><stop offset="0" stop-color="{HOT}"/><stop offset=".3" stop-color="#F7BE5E"/>'
  f'<stop offset=".7" stop-color="{LANT}"/><stop offset="1" stop-color="{VERM}"/></radialGradient>')
D(f'<radialGradient id="gHalo"><stop offset="0" stop-color="{LANT}" stop-opacity=".9"/>'
  f'<stop offset=".45" stop-color="{LANT}" stop-opacity=".35"/><stop offset="1" stop-color="{LANT}" stop-opacity="0"/></radialGradient>')
D(f'<radialGradient id="gTGlow"><stop offset="0" stop-color="{TGLOW}" stop-opacity="1"/>'
  f'<stop offset=".35" stop-color="{TGLOW}" stop-opacity=".55"/><stop offset="1" stop-color="{TGLOW}" stop-opacity="0"/></radialGradient>')
D('<radialGradient id="gBall" cx=".42" cy=".38" r=".7"><stop offset="0" stop-color="#FFC08A"/>'
  f'<stop offset=".45" stop-color="#EE6440"/><stop offset="1" stop-color="{VERM}"/></radialGradient>')
D(f'<radialGradient id="gJade" cx=".4" cy=".4" r=".7"><stop offset="0" stop-color="#9BE0B8"/>'
  f'<stop offset=".5" stop-color="#5DB08A"/><stop offset="1" stop-color="{JADE}"/></radialGradient>')
D(f'<linearGradient id="gTeal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0B2229"/>'
  f'<stop offset=".11" stop-color="{TEAL}"/><stop offset=".9" stop-color="{TEAL}"/><stop offset="1" stop-color="#0A1D23"/></linearGradient>')

# ------------------------------------------------------------------ 1-2 night + festival band
A('<rect width="1080" height="1920" fill="url(#gTeal)"/>')
rnd = random.Random(5)
# distant bokeh lanterns + far roofline
bok = []
for i in range(16):
    x = rnd.uniform(-20, 1100)
    y = rnd.uniform(150, 205)
    r = rnd.uniform(6, 15)
    c = rnd.choice([LANT, LANT, VERM, '#F7C873'])
    bok.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{c}" opacity="{rnd.uniform(.18, .4):.2f}"/>')
roof = smooth_d([(-10, 212), (-10, 190), (90, 186), (150, 172), (200, 176), (260, 160), (330, 168), (420, 182),
                 (520, 178), (600, 168), (690, 176), (760, 158), (830, 150), (900, 166), (980, 178), (1090, 172),
                 (1090, 212)], closed=True)
A(f'<path d="{roof}" fill="#0C252B" opacity=".9"/>')
A(f'<g filter="url(#b5)">{"".join(bok)}</g>')


def str_y(x):
    t = x / 1080
    return 70 + 20 * t + 240 * t * (1 - t)


A(f'<path d="{poly_d([(x, str_y(x)) for x in range(-10, 1095, 15)], close=False)}" fill="none" stroke="#071418" '
  f'stroke-width="2.2"/>')
lantern_x = [80 + i * 153.33 for i in range(7)]
halos, lants = [], []
lr = random.Random(12)
for i, x in enumerate(lantern_x):
    sy = str_y(x)
    rx_, ry_ = 26 * lr.uniform(.94, 1.06), 27 * lr.uniform(.95, 1.05)
    cy = sy + 9 + ry_
    sway = lr.uniform(-6, 6)
    halos.append(f'<circle cx="{f(x)}" cy="{f(cy)}" r="160" fill="url(#gHalo)" opacity="{lr.uniform(.1, .16):.2f}"/>')
    halos.append(f'<circle cx="{f(x)}" cy="{f(cy)}" r="62" fill="url(#gHalo)" opacity="{lr.uniform(.38, .5):.2f}"/>')
    g = [f'<line x1="{f(x)}" y1="{f(sy)}" x2="{f(x)}" y2="{f(cy - ry_ - 3)}" stroke="#071418" stroke-width="1.6"/>',
         f'<ellipse cx="{f(x)}" cy="{f(cy)}" rx="{f(rx_)}" ry="{f(ry_)}" fill="url(#gLant)"/>']
    for k in range(-3, 4):
        yy = cy + k * ry_ / 3.4
        hw = rx_ * math.sqrt(max(0, 1 - ((yy - cy) / ry_) ** 2))
        g.append(f'<path d="M{f(x - hw)},{f(yy)} Q{f(x)},{f(yy + 3)} {f(x + hw)},{f(yy)}" fill="none" '
                 f'stroke="{VERM}" stroke-width="1.1" opacity=".55"/>')
    g.append(f'<rect x="{f(x - 12)}" y="{f(cy - ry_ - 4)}" width="24" height="7" rx="2" fill="#140C08"/>')
    g.append(f'<rect x="{f(x - 12)}" y="{f(cy + ry_ - 3)}" width="24" height="7" rx="2" fill="#140C08"/>')
    g.append(f'<path d="M{f(x)},{f(cy + ry_ + 4)} l-3,10 l6,0 Z" fill="#140C08"/>')
    lants.append(f'<g transform="rotate({f(sway)} {f(x)} {f(sy)})">' + ''.join(g) + '</g>')
A(f'<g style="mix-blend-mode:screen">{"".join(halos)}</g>')
A(''.join(lants))

# ------------------------------------------------------------------ 4 screen
A(f'<g clip-path="url(#cScr)">')
A(f'<rect x="{SX0}" y="{SY0}" width="{SX1 - SX0}" height="{SY1 - SY0}" fill="url(#gScr)"/>')
A(f'<rect x="{SX0}" y="{SY0}" width="{SX1 - SX0}" height="{SY1 - SY0}" fill="url(#gCore)"/>')

# ---- a moth fluttering near the lamp: its shadow is big and soft
if P['moth']:
    mw = [smooth_d([(0, 0), (-30, -40), (-78, -52), (-92, -30), (-60, 6), (-14, 10)], k=0.45),
          smooth_d([(-6, 8), (-50, 18), (-58, 46), (-30, 56), (-8, 30)], k=0.45)]
    moth = ''.join(f'<path d="{d}"/><path d="{d}" transform="scale(-1,1)"/>' for d in mw)
    moth += '<ellipse cx="0" cy="10" rx="7" ry="28"/><path d="M-3,-14 Q-16,-44 -30,-52 M3,-14 Q16,-44 30,-52" stroke="#151110" stroke-width="3" fill="none"/>'
    A(f'<g transform="translate(250,430) rotate(-24) scale(1.1)" fill="{BLK}" opacity=".26" filter="url(#b9)">{moth}</g>')

# ---- 6 far disciple B (big, soft)


def dummy(J, s=1.0, ring=True, rods=None):
    """wooden dummy puppet. J holds joints; returns svg (all black) + rivet rings."""
    g = []
    # far limbs
    for a, b, w in [('sh_f', 'el_f', 27), ('el_f', 'ha_f', 25), ('hip_f', 'kn_f', 34), ('kn_f', 'ft_f', 30)]:
        g.append(peg(J[a], J[b], w * s))
    g.append(f'<circle cx="{f(J["ha_f"][0])}" cy="{f(J["ha_f"][1])}" r="{f(16 * s)}" fill="{BLK}"/>')
    # torso blocks
    g.append(peg(J['neck'], J['waist'], 98 * s, r=18 * s, ext=6 * s))
    g.append(peg(J['waist'], J['pelvis'], 84 * s, r=14 * s, ext=22 * s))
    g.append(f'<circle cx="{f(J["waist"][0])}" cy="{f(J["waist"][1])}" r="{f(30 * s)}" fill="{BLK}"/>')
    # neck + head knob
    g.append(peg(J['neck'], J['head'], 26 * s, ext=4 * s))
    hc, ha = J['head'], J.get('head_ang', 0)
    g.append(f'<g transform="translate({f(hc[0])},{f(hc[1])}) rotate({f(ha)})">'
             f'<ellipse cx="0" cy="0" rx="{f(41 * s)}" ry="{f(45 * s)}" fill="{BLK}"/>'
             f'<rect x="{f(-9 * s)}" y="{f(-56 * s)}" width="{f(18 * s)}" height="{f(16 * s)}" rx="{f(4 * s)}" fill="{BLK}"/></g>')
    # near limbs
    for a, b, w in [('hip_n', 'kn_n', 35), ('kn_n', 'ft_n', 31), ('sh_n', 'el_n', 28), ('el_n', 'ha_n', 26)]:
        g.append(peg(J[a], J[b], w * s))
    g.append(f'<circle cx="{f(J["ha_n"][0])}" cy="{f(J["ha_n"][1])}" r="{f(17 * s)}" fill="{BLK}"/>')
    for k in ('ft_n', 'ft_f'):
        x, y = J[k]
        d = J.get('foot_dir', -1)
        g.append(f'<rect x="{f(min(x, x + d * 58 * s) - 6 * s)}" y="{f(y - 22 * s)}" width="{f(70 * s)}" '
                 f'height="{f(24 * s)}" rx="{f(6 * s)}" fill="{BLK}"/>')
    if ring:
        for k in ('neck', 'sh_n', 'el_n', 'hip_n', 'kn_n', 'waist'):
            g.append(rivet(*J[k], r=5.5 * s, ring=2))
    return ''.join(g)


JB = dict(head=(905, 470), head_ang=24, neck=(880, 560), waist=(860, 820), pelvis=(855, 930),
          sh_n=(885, 600), el_n=(985, 760), ha_n=(1035, 900), sh_f=(870, 600), el_f=(790, 800), ha_f=(770, 1010),
          hip_n=(870, 950), kn_n=(930, 1230), ft_n=(990, 1530), hip_f=(845, 950), kn_f=(790, 1240), ft_f=(760, 1530),
          foot_dir=-1)
A(f'<g filter="url(#b14)" opacity="{P["b_opacity"]}">{dummy(JB, s=1.5, ring=False)}'
  f'<line x1="860" y1="760" x2="900" y2="1720" stroke="{BLK}" stroke-width="7" opacity=".7"/></g>')

# ---- 5 scenery: torii-ish gate post, pine, ground strip, wind bell
masks = []
scen = []
# gate post + beams
post = [(66, 700), (112, 700), (118, 1560), (60, 1560)]
kasagi = smooth_d([(40, 690), (150, 700), (250, 698), (300, 672), (306, 686), (262, 716), (150, 722), (40, 716)])
nuki = [(40, 800), (268, 800), (268, 828), (40, 828)]
scen.append(f'<path d="{poly_d(post)}" fill="{BLK}"/><path d="{kasagi}" fill="{BLK}"/>'
            f'<path d="{poly_d(nuki)}" fill="{BLK}"/><rect x="40" y="722" width="250" height="16" fill="{BLK}"/>'
            f'<rect x="200" y="738" width="22" height="62" fill="{BLK}"/>')
cut = []
for k in range(14):
    y = 880 + k * 46
    if 880 <= y <= 990 or 1170 <= y <= 1262:
        continue
    cut.append(f'<path d="M89,{y - 12} l8,12 l-8,12 l-8,-12 Z" fill="black"/>')
for k in range(9):
    x = 66 + k * 24
    cut.append(f'<circle cx="{x}" cy="814" r="4" fill="black"/>')
for k in range(10):
    x = 60 + k * 22
    cut.append(f'<circle cx="{x}" cy="730" r="2.6" fill="black"/>')
# pine trunk + pads
trunk = smooth_d([(194, 1560), (204, 1460), (192, 1360), (206, 1250), (238, 1160), (230, 1080), (196, 1014),
                  (172, 986), (184, 972), (220, 996), (262, 1060), (274, 1150), (246, 1260), (232, 1360),
                  (242, 1460), (262, 1560)], k=0.45)
scen.append(f'<path d="{trunk}" fill="{BLK}"/>')
branches = [((236, 1040), (150, 960)), ((262, 1150), (330, 1100)), ((214, 1290), (128, 1236)), ((246, 1100), (262, 1078))]
for a_, b_ in branches:
    scen.append(taper(a_, b_, 18, 9))


def pine_pad(cx, cy, w, h, seed):
    """flat cloud of needles: scalloped dome top, gently convex bottom, fan of needle cuts."""
    rr = random.Random(seed)
    n = max(6, int(w / 24))
    top = []
    for i in range(n + 1):
        t = i / n
        x = cx - w / 2 + w * t
        y = cy - h * (1 - abs(2 * t - 1) ** 1.6) ** 0.8
        top.append((x, y))
    d = f'M{f(top[0][0])},{f(cy)}'
    for (x0, y0), (x1, y1) in zip(top, top[1:]):
        r = math.hypot(x1 - x0, y1 - y0) / 2 * rr.uniform(1.0, 1.15)
        d += f' L{f(x0)},{f(y0)} A{f(r)},{f(r)} 0 0 1 {f(x1)},{f(y1)}'
    d += f' L{f(cx + w / 2)},{f(cy)} Q{f(cx)},{f(cy + h * 0.45)} {f(cx - w / 2)},{f(cy)} Z'
    cuts = []
    ox, oy = cx, cy + h * 0.9
    for k in range(-9, 10):
        ang = math.radians(-90 + k * 8.5)
        L0, L1 = h * 0.95, h * 1.75
        x0, y0 = ox + math.cos(ang) * L0 * (w / h) * 0.32, oy + math.sin(ang) * L0
        x1, y1 = ox + math.cos(ang) * L1 * (w / h) * 0.32, oy + math.sin(ang) * L1
        cuts.append(f'M{f(x0)},{f(y0)} L{f(x1)},{f(y1)}')
    return d, ' '.join(cuts)


pads = [(160, 948, 210, 58, 1), (282, 1082, 150, 44, 2), (122, 1226, 150, 42, 3), (334, 1106, 70, 26, 4),
        (226, 870, 96, 30, 5)]
pad_cuts = []
for (cx, cy, w, h, sd) in pads:
    d, c = pine_pad(cx, cy, w, h, sd)
    scen.append(f'<path d="{d}" fill="{BLK}"/>')
    pad_cuts.append((d, c))
for i, (d, c) in enumerate(pad_cuts):
    D(f'<clipPath id="cPad{i}"><path d="{d}"/></clipPath>')
    cut.append(f'<g clip-path="url(#cPad{i})"><path d="{c}" stroke="black" stroke-width="2" stroke-linecap="round"/></g>')
    cut.append(f'<path d="{d}" fill="none" stroke="white" stroke-width="8"/>')
# ground strip with seigaiha cuts
scen.append(f'<rect x="{SX0}" y="1558" width="{SX1 - SX0}" height="84" fill="{BLK}"/>')
scen.append(f'<path d="M{SX0},1560 ' + ' '.join(f'Q{x + 30},1552 {x + 60},1560' for x in range(SX0, SX1, 60)) +
            f' L{SX1},1570 L{SX0},1570 Z" fill="{BLK}"/>')
for row in range(2):
    for x in range(SX0 - 30, SX1 + 30, 56):
        cx = x + row * 28
        cy = 1606 + row * 22
        for rr in (20, 13, 6):
            cut.append(f'<path d="M{f(cx - rr)},{f(cy)} A{rr},{rr} 0 0 1 {f(cx + rr)},{f(cy)}" fill="none" stroke="black" stroke-width="2.4"/>')
# keep a solid top edge of the ground
cut.append(f'<rect x="{SX0}" y="1556" width="{SX1 - SX0}" height="20" fill="white"/>')
# wind bell (furin) hanging top-right
fx = 930
scen.append(f'<line x1="{fx}" y1="236" x2="{fx}" y2="318" stroke="{BLK}" stroke-width="2.5"/>')
scen.append(f'<path d="{smooth_d([(fx, 316), (fx + 22, 322), (fx + 32, 350), (fx + 34, 366), (fx - 34, 366), (fx - 32, 350), (fx - 22, 322)])}" fill="{BLK}"/>')
scen.append(f'<line x1="{fx}" y1="360" x2="{fx}" y2="410" stroke="{BLK}" stroke-width="2"/>')
scen.append(f'<rect x="{fx - 5}" y="370" width="10" height="16" rx="3" fill="{BLK}"/>')
for k in range(5):
    cut.append(f'<circle cx="{fx - 20 + k * 10}" cy="350" r="2.6" fill="black"/>')
D('<mask id="mScen" maskUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">'
  '<rect width="1080" height="1920" fill="white"/>' + ''.join(cut) + '</mask>')
# tanzaku (jade gel strip) on the bell
tz = [(fx - 18, 408), (fx + 18, 408), (fx + 20, 540), (fx - 16, 540)]
A(f'<g filter="url(#b06)"><g mask="url(#mScen)">{"".join(scen)}</g>'
  f'<path d="{poly_d(tz)}" fill="{BLK}"/><path d="{poly_d([(fx - 11, 415), (fx + 11, 415), (fx + 13, 533), (fx - 9, 533)])}" '
  f'fill="url(#gJade)" opacity=".92"/><path d="M{fx - 9},470 L{fx + 12},478" stroke="{BLK}" stroke-width="4"/></g>')

# ---- control rods (behind the puppets)
D('<linearGradient id="gRod" gradientUnits="userSpaceOnUse" x1="0" y1="800" x2="0" y2="1704">'
  f'<stop offset="0" stop-color="{BLK}" stop-opacity=".8"/><stop offset="1" stop-color="{BLK}" stop-opacity=".45"/></linearGradient>')
rods = [((590, 772), (612, 1704)), ((520, 880), (560, 1704)), ((684, 1296), (664, 1704)),
        ((900, 1170), (880, 1704)), ((1046, 1290), (1010, 1704))]
A('<g filter="url(#rodb)">' + ''.join(
    f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="url(#gRod)" stroke-width="4" stroke-linecap="round"/>'
    for a, b in rods) + '</g>')

# ---- ball ghosts (behind the disciples)
ball = (858, 850)
ghosts = [((782, 1330), 30, .24), ((814, 1132), 32, .38), ((900, 944), 36, .55)]
gh = []
for (x, y), r, al in ghosts:
    gh.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{VERM}" opacity="{al}"/>')
D('<linearGradient id="gStreak" gradientUnits="userSpaceOnUse" x1="0" y1="1500" x2="0" y2="940">'
  f'<stop offset="0" stop-color="{VERM}" stop-opacity="0"/><stop offset="1" stop-color="{TGLOW}" stop-opacity=".5"/></linearGradient>')
A(f'<path d="M776,1480 Q776,1210 900,944" stroke="url(#gStreak)" stroke-width="30" fill="none" stroke-linecap="round" filter="url(#b9)"/>')
A(f'<path d="M900,944 Q874,880 858,850" stroke="{TGLOW}" stroke-opacity=".35" stroke-width="40" fill="none" stroke-linecap="round" filter="url(#b9)"/>')
A(f'<g filter="url(#b2)">{"".join(gh)}</g>')

# ---- 7 disciples (sharp)
JA = dict(head=(925, 1004), head_ang=40, neck=(902, 1068), waist=(906, 1196), pelvis=(902, 1276),
          sh_n=(906, 1100), el_n=(962, 1168), ha_n=(1012, 1196), sh_f=(898, 1098), el_f=(966, 1080), ha_f=(1008, 1028),
          hip_n=(906, 1296), kn_n=(866, 1420), ft_n=(856, 1546), hip_f=(896, 1296), kn_f=(944, 1424), ft_f=(980, 1546),
          foot_dir=-1)
JC = dict(head=(1050, 1330), head_ang=-24, neck=(1070, 1380), waist=(1110, 1470), pelvis=(1120, 1520),
          sh_n=(1066, 1408), el_n=(1026, 1428), ha_n=(998, 1396), sh_f=(1072, 1408), el_f=(1090, 1450), ha_f=(1070, 1480),
          hip_n=(1110, 1520), kn_n=(1040, 1500), ft_n=(1010, 1546), hip_f=(1120, 1520), kn_f=(1150, 1540), ft_f=(1160, 1546),
          foot_dir=-1)
A(f'<g filter="url(#b10)">{dummy(JC)}{dummy(JA)}</g>')

# ---- 8 hero: the old master
H_ = []
hero_cut = []
robe = [(574, 766), (548, 772), (512, 792), (482, 826), (462, 870), (454, 920), (458, 970), (470, 1024),
        (468, 1100), (452, 1200), (430, 1300), (476, 1292), (522, 1302), (570, 1292), (620, 1302), (666, 1292),
        (706, 1300), (686, 1206), (658, 1110), (636, 1040), (642, 974), (636, 900),
        (626, 846), (614, 802), (602, 780)]
robe_d = smooth_d(robe, k=0.3)

# wide kung-fu trousers, bloused at the ankle, cloth shoes
lead_tr = [(620, 1250), (688, 1250), (700, 1330), (712, 1420), (720, 1476), (716, 1500), (704, 1512), (676, 1512),
           (666, 1494), (662, 1440), (646, 1350)]
rear_tr = [(440, 1250), (506, 1252), (488, 1340), (446, 1430), (434, 1478), (430, 1502), (420, 1512), (392, 1510),
           (384, 1494), (392, 1440), (418, 1340)]
H_.append(f'<path d="{smooth_d(lead_tr, k=0.35)}" fill="{BLK}"/><path d="{smooth_d(rear_tr, k=0.35)}" fill="{BLK}"/>')
lead_foot = [(676, 1506), (712, 1504), (738, 1512), (764, 1502), (788, 1494), (794, 1506), (772, 1532), (730, 1550),
             (716, 1560), (668, 1560), (666, 1530)]
rear_foot = [(390, 1506), (424, 1506), (448, 1528), (474, 1546), (478, 1560), (380, 1560), (380, 1530)]
H_.append(f'<path d="{smooth_d(lead_foot, k=0.3)}" fill="{BLK}"/><path d="{smooth_d(rear_foot, k=0.3)}" fill="{BLK}"/>')

# ---- cuts (mask): robe asanoha, obi, lapel, trouser wraps, face, glowing beard
asa = asanoha(420, 1060, 720, 1300, P['asa_a'])
D(f'<clipPath id="cRobeLow"><path d="{robe_d}"/></clipPath>')
hero_cut.append(f'<g clip-path="url(#cRobeLow)"><path d="{asa}" stroke="black" stroke-width="{P["asa_w"]}" '
                f'stroke-linecap="round" fill="none"/></g>')
hero_cut.append(f'<path d="{robe_d}" fill="none" stroke="white" stroke-width="{P["robe_border"]}"/>')
hero_cut.append('<rect x="400" y="1004" width="320" height="70" fill="white"/>')
hero_cut.append('<rect x="400" y="600" width="320" height="404" fill="white"/>')
hero_cut.append('<path d="M470,1014 Q552,1022 638,1010" stroke="black" stroke-width="2.6" fill="none"/>')
hero_cut.append('<path d="M474,1066 Q560,1074 646,1060" stroke="black" stroke-width="2.6" fill="none"/>')
hero_cut.append('<path d="M606,792 Q616,860 604,1004" stroke="black" stroke-width="3" fill="none"/>')
hero_cut.append('<path d="M622,812 Q606,890 580,1004" stroke="black" stroke-width="2.4" fill="none"/>')
for (a0, a1) in [((666, 1478), (718, 1474)), ((664, 1492), (718, 1488)), ((388, 1476), (436, 1480)), ((386, 1490), (432, 1494))]:
    hero_cut.append(f'<path d="M{a0[0]},{a0[1]} L{a1[0]},{a1[1]}" stroke="black" stroke-width="2.4"/>')
hero_cut.append('<path d="M664,1310 Q680,1390 690,1450" stroke="black" stroke-width="2.2" fill="none"/>')
hero_cut.append('<path d="M470,1310 Q440,1390 420,1450" stroke="black" stroke-width="2.2" fill="none"/>')
# sleepy closed eye, ear
hero_cut.append('<path d="M652,694 Q665,705 680,697" stroke="black" stroke-width="3.6" fill="none" stroke-linecap="round"/>')
hero_cut.append('<path d="M612,684 q-8,10 0,22" stroke="black" stroke-width="2.6" fill="none" stroke-linecap="round"/>')
# long droopy eyebrow (fine cut wisps)
for k in range(3):
    hero_cut.append(f'<path d="M{640 + k * 3},{662 + k * 4} Q{668},{652 + k * 4} {686 + k},{666 + k * 4} T{694 - k * 2},{690 + k * 3}" '
                    f'stroke="black" stroke-width="2" fill="none" stroke-linecap="round"/>')
# beard as a glowing mesh of strands
beard = smooth_d([(640, 730), (668, 728), (696, 714), (712, 744), (708, 772), (716, 800), (706, 826), (708, 856),
                  (692, 872), (686, 898), (672, 878), (656, 892), (652, 860), (640, 836), (644, 806), (634, 776)], k=0.5)
D(f'<clipPath id="cBeard"><path d="{beard}"/></clipPath>')
br = random.Random(17)
strand_svg = []
NS = 17
for k in range(NS):
    x0 = 637 + k * 4.6 + br.uniform(-0.8, 0.8)
    y0 = 716 + abs(k - 11) * 1.4
    tip = (656, 900) if k < 6 else ((686, 904) if k < 12 else (702, 880))
    w = P['beard_w'] + br.uniform(-0.4, 0.5)
    sway = 7 + br.uniform(-2, 2)
    x3, y3 = tip[0] + br.uniform(-3, 3), tip[1] - br.uniform(0, 30)
    c1 = (x0 + sway, y0 + (y3 - y0) * 0.35)
    c2 = (x3 - sway * 1.1, y0 + (y3 - y0) * 0.7)
    strand_svg.append(f'<path d="M{f(x0)},{f(y0)} C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(x3)},{f(y3)}" '
                      f'stroke-width="{w:.2f}"/>')
hero_cut.append(f'<g clip-path="url(#cBeard)" stroke="black" fill="none" stroke-linecap="round">{"".join(strand_svg)}</g>')
hero_cut.append(f'<path d="{beard}" fill="none" stroke="white" stroke-width="7"/>')
hero_cut.append('<ellipse cx="634" cy="690" rx="58" ry="57" fill="none" stroke="white" stroke-width="0"/>')
D('<mask id="mHero" maskUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">'
  '<rect width="1080" height="1920" fill="white"/>' + ''.join(hero_cut) + '</mask>')
head = (f'<ellipse cx="634" cy="690" rx="58" ry="57" fill="{BLK}"/>'
        f'<path d="{smooth_d([(566, 762), (600, 734), (636, 740), (626, 786), (586, 798)])}" fill="{BLK}"/>')
H_.append(f'<g mask="url(#mHero)"><path d="{robe_d}" fill="{BLK}"/>{head}<path d="{beard}" fill="{BLK}"/></g>')
# topknot bun on the back-top with a jade-gel pin
H_.append(f'<circle cx="590" cy="630" r="21" fill="{BLK}"/><rect x="590" y="638" width="22" height="14" '
          f'transform="rotate(-40 600 645)" fill="{BLK}"/>')
H_.append(f'<g transform="rotate(-22 590 630)"><rect x="548" y="624" width="86" height="12" rx="6" fill="{BLK}"/>'
          f'<rect x="604" y="626.5" width="26" height="7" rx="3.5" fill="url(#gJade)"/>'
          f'<circle cx="590" cy="630" r="7" fill="url(#gJade)"/></g>')

# ---- clasped hands peeking out behind the back
H_.append(f'<path d="{smooth_d([(474, 948), (452, 946), (432, 952), (424, 966), (434, 980), (456, 982), (474, 976)], k=0.4)}" fill="{BLK}"/>')
H_.append(f'<path d="{smooth_d([(440, 950), (432, 938), (440, 932), (450, 944)], k=0.4)}" fill="{BLK}"/>')

# ---- near sleeve: indigo stained glass, hanging from the bent arm
sleeve = [(556, 800), (590, 804), (598, 870), (598, 950), (592, 1010), (578, 1036), (536, 1050), (494, 1060),
          (466, 1052), (456, 1016), (462, 978), (472, 952), (500, 922), (530, 898), (548, 852)]
sleeve_d = smooth_d(sleeve, k=0.35)
D(f'<clipPath id="cSleeve"><path d="{sleeve_d}"/></clipPath>')
cols = [(400, 400), (497, 479), (535, 517), (573, 555), (660, 660)]
rows_y = [(700, 700), (1100, 1100), (1100, 1100)]
panel = []
shade = [[0.7, 1.0, 0.8, 0.6], [0.55, 0.7, 0.6, 0.5]]
gi = 0
for r in range(1):
    for c in range(4):
        (xt0, xb0), (xt1, xb1) = cols[c], cols[c + 1]
        (yl0, yr0), (yl1, yr1) = rows_y[r], rows_y[r + 1]

        def X(xt, xb, y):
            return xt + (xb - xt) * (y - 780) / 300
        q = [(X(xt0, xb0, yl0), yl0), (X(xt1, xb1, yr0), yr0), (X(xt1, xb1, yr1), yr1), (X(xt0, xb0, yl1), yl1)]
        sh = shade[r][c]
        gid = f'gGel{gi}'
        gi += 1
        D(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{GCX - 10}" cy="{GCY - 50}" r="200">'
          f'<stop offset="0" stop-color="{mix(P["gel_mid"], P["gel_light"], sh)}"/>'
          f'<stop offset=".6" stop-color="{mix(P["gel_dark"], P["gel_mid"], sh)}"/>'
          f'<stop offset="1" stop-color="{P["gel_dark"]}"/></radialGradient>')
        panel.append(f'<path d="{poly_d(q)}" fill="url(#{gid})"/>')
leading = []
for x0 in (496, 534, 572):
    pth = f'M{x0},800'
    for k in range(6):
        y = 800 + k * 48
        dx = 10 if k % 2 == 0 else -10
        pth += f' Q{x0 + dx - (y - 800) * 0.06},{y + 24} {x0 - (y + 48 - 800) * 0.06},{y + 48}'
    leading.append(f'<path d="{pth}" stroke="{BLK}" stroke-width="6" fill="none"/>')
cr = random.Random(31)
crease = []
for i in range(14):
    x0, y0 = cr.uniform(450, 600), cr.uniform(800, 1060)
    a = math.radians(cr.uniform(-70, -20) if i % 2 else cr.uniform(20, 70))
    L = cr.uniform(30, 90)
    x1, y1 = x0 + L * math.cos(a), y0 + L * math.sin(a)
    x2, y2 = x1 + cr.uniform(-20, 20), y1 + cr.uniform(10, 30)
    col, op = ('#D8E4FF', cr.uniform(.18, .34)) if i % 3 else ('#0E1838', cr.uniform(.2, .35))
    crease.append(f'<path d="M{f(x0)},{f(y0)} L{f(x1)},{f(y1)} L{f(x2)},{f(y2)}" stroke="{col}" stroke-opacity="{op:.2f}" '
                  f'stroke-width="{cr.uniform(.8, 1.6):.2f}" fill="none" stroke-linejoin="bevel"/>')
H_.append(f'<g clip-path="url(#cSleeve)">{"".join(panel)}{"".join(crease)}{"".join(leading)}</g>')
H_.append(f'<path d="{sleeve_d}" fill="none" stroke="{BLK}" stroke-width="13" stroke-linejoin="round"/>')
# cuff band at the sleeve opening
H_.append(f'<path d="M464,952 L470,986" stroke="{BLK}" stroke-width="12" stroke-linecap="round"/>')
# sleepy nose bubble (hana-chochin): a pale gel disc in a thin black ring
if P['bubble']:
    H_.append(f'<path d="M694,700 Q700,706 702,712" stroke="{BLK}" stroke-width="5" fill="none" stroke-linecap="round"/>')
    H_.append(f'<circle cx="716" cy="712" r="17" fill="#FFF3D2" fill-opacity=".55"/>'
              f'<circle cx="716" cy="712" r="17" fill="none" stroke="{BLK}" stroke-width="3"/>'
              f'<path d="M707,704 Q711,699 717,698" stroke="#FFFFFF" stroke-opacity=".9" stroke-width="2.4" fill="none" stroke-linecap="round"/>')
# rivets
for (x, y, r) in [(590, 772, 7), (568, 806, 7), (532, 898, 7), (540, 1040, 7), (654, 1272, 7), (472, 1274, 7)]:
    H_.append(rivet(x, y, r=r))
HERO_SVG = f'<g filter="url(#b08)">{"".join(H_)}</g>'
A(HERO_SVG)

# ---- 9 temari, ghosts, pon burst
if P['future_dots']:
    # the path home: quadratic from ball to the master's raised toe
    p0, c, p1 = ball, (790, 720), (770, 1500)
    dots = []
    n = 16
    for i in range(2, n):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * c[0] + t * t * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * c[1] + t * t * p1[1]
        dots.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="3" fill="{BLK}" opacity="{0.42 - 0.22 * t:.2f}"/>')
    A(''.join(dots))
# pon burst at contact (8 tapered light rays)
cx, cy = 902, 948
rays = []
for k in range(8):
    a = math.radians(-90 + k * 45 + 22.5)
    r0, r1, w = 50, 80, 7
    nx, ny = -math.sin(a), math.cos(a)
    q = [(cx + math.cos(a) * r0 + nx * w / 2, cy + math.sin(a) * r0 + ny * w / 2),
         (cx + math.cos(a) * r1, cy + math.sin(a) * r1),
         (cx + math.cos(a) * r0 - nx * w / 2, cy + math.sin(a) * r0 - ny * w / 2)]
    rays.append(f'<path d="{poly_d(q)}" fill="#FFF4D6" stroke="{BLK}" stroke-width="1.2" stroke-opacity=".5"/>')
A(f'<g filter="url(#b06)">{"".join(rays)}</g>')
# halo + ball
A(f'<circle cx="{ball[0]}" cy="{ball[1]}" r="135" fill="url(#gTGlow)" opacity=".55" style="mix-blend-mode:screen"/>')
bx, by = ball
tb = [f'<circle cx="{bx}" cy="{by}" r="45" fill="url(#gBall)" opacity=".95"/>']
for k in range(4):
    a = math.radians(k * 45 + 10)
    tb.append(f'<line x1="{f(bx + 41 * math.cos(a))}" y1="{f(by + 41 * math.sin(a))}" x2="{f(bx - 41 * math.cos(a))}" '
              f'y2="{f(by - 41 * math.sin(a))}" stroke="{BLK}" stroke-width="2.6"/>')
tb.append(f'<circle cx="{bx}" cy="{by}" r="7" fill="{BLK}"/>')
for k in range(16):
    a = math.radians(k * 22.5)
    tb.append(f'<circle cx="{f(bx + 34 * math.cos(a))}" cy="{f(by + 34 * math.sin(a))}" r="2.7" fill="{HOT}"/>')
tb.append(f'<circle cx="{bx}" cy="{by}" r="45" fill="none" stroke="{BLK}" stroke-width="4.5"/>')
A(f'<g filter="url(#b08)">{"".join(tb)}</g>')

# ---- paper texture over everything on the screen
A(f'<rect x="{SX0}" y="{SY0}" width="{SX1 - SX0}" height="{SY1 - SY0}" filter="url(#fMot)" '
  f'style="mix-blend-mode:multiply" opacity=".15"/>')
A(f'<rect x="{SX0}" y="{SY0}" width="{SX1 - SX0}" height="{SY1 - SY0}" filter="url(#fFib)" '
  f'style="mix-blend-mode:multiply" opacity=".07"/>')
fr = random.Random(9)
fib = []
for i in range(P['fibres']):
    x = fr.uniform(SX0, SX1)
    y = fr.uniform(SY0, SY1)
    L = fr.uniform(20, 90)
    a = fr.uniform(0, math.pi)
    bend = fr.uniform(-12, 12)
    x2, y2 = x + L * math.cos(a), y + L * math.sin(a)
    mx, my = (x + x2) / 2 - bend * math.sin(a), (y + y2) / 2 + bend * math.cos(a)
    col = EDGE if fr.random() < 0.75 else '#FFF3D0'
    fib.append(f'<path d="M{f(x)},{f(y)} Q{f(mx)},{f(my)} {f(x2)},{f(y2)}" stroke="{col}" '
               f'stroke-width="{fr.uniform(.5, 1.2):.2f}" opacity="{fr.uniform(.08, .22):.2f}" fill="none"/>')
A(f'<g style="mix-blend-mode:multiply">{"".join(fib)}</g>')
for sx in (380, 700):
    A(f'<rect x="{sx - 6}" y="{SY0}" width="12" height="{SY1 - SY0}" fill="{EDGE}" opacity=".07"/>'
      f'<line x1="{sx}" y1="{SY0}" x2="{sx}" y2="{SY1}" stroke="{EDGE}" stroke-width="2" opacity=".3"/>')
A('</g>')  # end screen clip

# ------------------------------------------------------------------ 3 frame (drawn over the screen edge)
A(f'<path d="M24,210 H1056 V1730 H24 Z M{SX0},{SY0} V{SY1} H{SX1} V{SY0} Z" fill="{WOOD}" fill-rule="evenodd"/>')
gr = random.Random(3)
grain = []
for i in range(60):
    side = gr.choice(['t', 'b', 'l', 'r'])
    if side in 'tb':
        y = (gr.uniform(212, 234) if side == 't' else gr.uniform(1706, 1728))
        x = gr.uniform(24, 900)
        grain.append(f'<line x1="{f(x)}" y1="{f(y)}" x2="{f(x + gr.uniform(60, 220))}" y2="{f(y + gr.uniform(-1, 1))}"/>')
    else:
        x = (gr.uniform(26, 48) if side == 'l' else gr.uniform(1032, 1054))
        y = gr.uniform(210, 1600)
        grain.append(f'<line x1="{f(x)}" y1="{f(y)}" x2="{f(x + gr.uniform(-1, 1))}" y2="{f(y + gr.uniform(80, 300))}"/>')
A(f'<g stroke="#3D2817" stroke-width="1.2" opacity=".7">{"".join(grain)}</g>')
A(f'<rect x="{SX0 - 1}" y="{SY0 - 1}" width="{SX1 - SX0 + 2}" height="{SY1 - SY0 + 2}" fill="none" stroke="{EDGE}" '
  f'stroke-width="2" opacity=".45"/>')
A('<rect x="24" y="210" width="1032" height="3" fill="#F2A541" opacity=".22"/>')
for (x, y) in [(24, 210), (1030, 210), (24, 1704), (1030, 1704)]:
    A(f'<rect x="{x + 7}" y="{y + 7}" width="12" height="12" fill="#1A0F08"/>')
# light spill from the screen into the night
# screen bloom over the inner frame edge
A(f'<rect x="{SX0}" y="{SY0}" width="{SX1 - SX0}" height="{SY1 - SY0}" fill="none" stroke="#E7A04F" stroke-width="10" '
  f'opacity=".22" filter="url(#b9)"/>')
if P['smoke']:
    sm = random.Random(21)
    wisps = []
    for i in range(9):
        x = sm.uniform(-100, 1100)
        y = sm.uniform(1600, 1800)
        wisps.append(f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(sm.uniform(140, 300))}" ry="{f(sm.uniform(18, 40))}" '
                     f'transform="rotate({f(sm.uniform(-8, 8))} {f(x)} {f(y)})" fill="#F0C27A" opacity="{sm.uniform(.07, .14):.2f}"/>')
    A(f'<g filter="url(#b20)">{"".join(wisps)}</g>')
D('<linearGradient id="gSpill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E39A4A" stop-opacity=".22"/>'
  '<stop offset="1" stop-color="#E39A4A" stop-opacity="0"/></linearGradient>')
A('<rect x="0" y="1730" width="1080" height="170" fill="url(#gSpill)"/>')

# ------------------------------------------------------------------ 11 audience
def person(cx, cy, r, sw, extra=''):
    sy = cy + r * 1.05
    d = (f'M{f(cx - sw)},1930 L{f(cx - sw)},{f(sy + 70)} '
         f'Q{f(cx - sw)},{f(sy + 8)} {f(cx - r * 0.55)},{f(sy)} '
         f'L{f(cx - r * 0.42)},{f(cy + r * 0.7)} '
         f'A{f(r)},{f(r * 1.05)} 0 1 1 {f(cx + r * 0.42)},{f(cy + r * 0.7)} '
         f'L{f(cx + r * 0.55)},{f(sy)} Q{f(cx + sw)},{f(sy + 8)} {f(cx + sw)},{f(sy + 70)} L{f(cx + sw)},1930 Z')
    return d, extra


people = [
    (96, 1786, 60, 120, 'man'), (276, 1826, 48, 92, 'fox'), (452, 1762, 54, 112, 'bun'),
    (650, 1842, 46, 90, 'fan'), (838, 1768, 60, 124, 'man2'), (1018, 1830, 50, 98, 'kid'),
]
aud = []
for (cx, cy, r, sw, kind) in people:
    d, _ = person(cx, cy, r, sw)
    parts = [f'<path d="{d}"/>']
    if kind == 'bun':
        parts.append(f'<circle cx="{cx - 18}" cy="{cy - r - 6}" r="22"/>')
        parts.append(f'<rect x="{cx - 62}" y="{cy - r - 14}" width="54" height="4" rx="2" transform="rotate(-18 {cx - 30} {cy - r - 12})"/>')
    if kind == 'fox':
        fxx, fyy = cx + r * 0.75, cy - r * 0.35
        parts.append(f'<path d="M{f(fxx - 26)},{f(fyy + 10)} L{f(fxx - 22)},{f(fyy - 34)} L{f(fxx - 6)},{f(fyy - 12)} '
                     f'L{f(fxx + 8)},{f(fyy - 30)} L{f(fxx + 18)},{f(fyy + 6)} Q{f(fxx + 10)},{f(fyy + 40)} {f(fxx - 10)},{f(fyy + 36)} Z"/>')
    if kind == 'fan':
        parts.append(f'<path d="M{cx + 32},{cy + 24} L{cx + 57},{cy - 60}" stroke="{AUD}" stroke-width="9" stroke-linecap="round"/>')
        fan = [(-12, -2), (-40, -16), (-54, -46), (-46, -80), (-14, -100), (14, -100), (46, -80), (54, -46), (40, -16), (12, -2)]
        parts.append(f'<path d="{smooth_d(fan, k=0.5)}" transform="translate({cx + 56},{cy - 64}) rotate(16)"/>')
        parts.append(f'<path d="{smooth_d([(cx + 10, cy + 70), (cx + 22, cy + 30), (cx + 34, cy + 16), (cx + 46, cy + 36), (cx + 40, cy + 80)])}"/>')
    if kind == 'kid':
        parts.append(f'<path d="M{cx - 8},{cy - r - 2} q8,-22 22,-18 q-8,6 -6,18 Z"/>')
    if kind == 'man2':
        parts.append(f'<path d="M{cx - r * 0.9},{cy - 8} Q{cx},{cy - 26} {cx + r * 0.95},{cy - 10} L{cx + r + 14},{cy - 4} '
                     f'L{cx + r + 18},{cy + 14} L{cx + r * 0.9},{cy + 2} Z"/>')
    aud.append(''.join(parts))
aud_svg = ''.join(aud)
A(f'<g filter="url(#b06)"><g fill="#E9B062" opacity=".75">{aud_svg}</g></g>')
A(f'<g transform="translate(0,2.6)" fill="{AUD}">{aud_svg}</g>')

# ------------------------------------------------------------------ 12 vignette + grain
A(f'<rect width="1080" height="1920" fill="url(#gVig)" opacity="{P["vignette"]}"/>')
A(f'<rect width="1080" height="1920" filter="url(#fGrain)" style="mix-blend-mode:overlay" opacity="{P["grain"]}"/>')

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
       f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>')
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'still.svg')
with open(out, 'w') as fh:
    fh.write(svg)
print('wrote', out, len(svg) // 1024, 'KB')
