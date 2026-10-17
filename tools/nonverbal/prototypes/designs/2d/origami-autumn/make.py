"""ORIGAMI AUTUMN - one flat-2D still (1080x1920 SVG).
Everything is code-drawn flat polygons. Run: python3 make.py [out.svg]"""
import math, random, sys

W, H = 1080, 1920
G = 1560                      # hero ground line
OUT = sys.argv[1] if len(sys.argv) > 1 else 'still.svg'

# ---------------------------------------------------------------- palette
IVORY = '#F1EBDD'; SKY_T = '#CFD6D8'; SKY_B = '#F2D49A'
GOLD = ('#E2B13C', '#CE9D33', '#B98A2A')          # lit, mid, shade
GOLD_FAR = ('#EDCB78', '#E2BC66', '#D2AA58')      # gold mixed into haze (distance)
RUST = ('#B4472B', '#993B24', '#7E2F1E')
MOSS = ('#7C8A55', '#6B7A4B', '#4C5835')
SLATE = '#4A4E5A'; TREAD = '#E9D6A8'
KON = ('#5A6E9C', '#2D3A5C', '#1C2440')
RIDGE = '#F7E6BE'
KRAFT = ('#C99B66', '#A47A4F', '#6E4F33')
BRASS = '#C9993F'; FENCE = ('#9A7350', '#7E5B3A', '#5C4129')
TENU = ('#F6F0E2', '#E4DAC4', '#C9BC9E')
FAN = ('#F1EBDD', '#CFC3A6')
ROD = ('#C99B66', '#8C6A44')
BARK = ('#5A4A44', '#45383A', '#33292C')

# ---------------------------------------------------------------- light model
_L = (-0.75, -0.45); _n = math.hypot(*_L)
LS = (_L[0] / _n, _L[1] / _n)        # unit vector pointing TOWARD the low sun (back-left)


def tone_idx(n):
    m = math.hypot(*n) or 1
    d = (n[0] * LS[0] + n[1] * LS[1]) / m
    return 0 if d > 0.2 else (2 if d < -0.2 else 1)


def tone(n, pal):
    return pal[tone_idx(n)]


K_SH, S_SH = 1.8, 0.42               # cast-shadow shear (x) and ground squash (y)


def proj(p, g=G):
    h = g - p[1]
    return (p[0] + K_SH * h, g + S_SH * h)


# ---------------------------------------------------------------- svg helpers
out = []
shadow_polys = []


def f(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def pts(P):
    return ' '.join(f'{f(x)},{f(y)}' for x, y in P)


def poly(P, fill, extra=''):
    out.append(f'<polygon points="{pts(P)}" fill="{fill}" {extra}/>')


def spoly(P, fill, extra=''):           # polygon with same-colour hairline stroke to hide AA seams
    out.append(f'<polygon points="{pts(P)}" fill="{fill}" stroke="{fill}" stroke-width=".7" stroke-linejoin="round" {extra}/>')


def line(a, b, col, w, extra=''):
    out.append(f'<line x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}" stroke="{col}" '
               f'stroke-width="{w}" stroke-linecap="round" {extra}/>')


def pline(P, col, w, extra=''):
    out.append(f'<polyline points="{pts(P)}" fill="none" stroke="{col}" stroke-width="{w}" '
               f'stroke-linecap="round" stroke-linejoin="round" {extra}/>')


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def plus(a, b):
    return (a[0] + b[0], a[1] + b[1])


def mul(a, s):
    return (a[0] * s, a[1] * s)


def norm(v):
    m = math.hypot(*v) or 1
    return (v[0] / m, v[1] / m)


def perp(v):
    return (-v[1], v[0])


def centroid(P):
    return (sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P))


def rot(p, c, a):
    s, co = math.sin(a), math.cos(a)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * co - y * s, c[1] + x * s + y * co)


def catmull(P, n=24):
    Q = [P[0]] + P + [P[-1]]
    R = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            R.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                  + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    R.append(P[-1])
    return R


def resample(C, k):
    L = [0]
    for i in range(1, len(C)):
        L.append(L[-1] + math.dist(C[i - 1], C[i]))
    tot = L[-1]
    res = []
    j = 0
    for i in range(k):
        s = tot * i / (k - 1)
        while j < len(L) - 2 and L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-6, L[j + 1] - L[j])
        res.append((lerp(C[j], C[j + 1], t), norm(sub(C[j + 1], C[j]))))
    return res


def offset_line(C, widths, side):
    """offset polyline C by +-width/2 (side=+1 left normal, -1 right)."""
    R = []
    for i, p in enumerate(C):
        a = C[max(0, i - 1)]; b = C[min(len(C) - 1, i + 1)]
        n = perp(norm(sub(b, a)))
        R.append(plus(p, mul(n, side * widths[i] / 2)))
    return R


# ---------------------------------------------------------------- generic paper parts
def strip(A, B, wA, wB, pal, ridge=True, curl=True, shadow=False, g=G, lit_frac=0.5):
    """Folded strip A->B split lengthwise by a crease into two facets with opposite normals.
    lit_frac moves the crease toward the lit edge (backlit paper: narrow lit facet)."""
    d = norm(sub(B, A)); p = perp(d)
    t1, t2 = tone_idx(p), tone_idx(mul(p, -1))
    # crease offset: toward whichever side is lit
    off = 0.0
    if t1 == 0: off = (0.5 - lit_frac)
    if t2 == 0: off = -(0.5 - lit_frac)
    cA, cB = plus(A, mul(p, off * wA)), plus(B, mul(p, off * wB))
    a1, b1 = plus(A, mul(p, wA / 2)), plus(B, mul(p, wB / 2))
    a2, b2 = plus(A, mul(p, -wA / 2)), plus(B, mul(p, -wB / 2))
    spoly([cA, cB, b1, a1], pal[t1])
    spoly([cA, cB, b2, a2], pal[t2])
    if curl:
        if t1 == 0: line(a1, b1, '#8FA2CF', 1.2, 'opacity=".8"')
        if t2 == 0: line(a2, b2, '#8FA2CF', 1.2, 'opacity=".8"')
    if ridge and (t1 == 0 or t2 == 0):
        line(cA, cB, RIDGE, 2)
    if shadow:
        shadow_polys.append([proj(q, g) for q in (a1, b1, b2, a2)])
    return (a1, b1, b2, a2)


def ring_mesh(c, radii_x, radii_y, counts, rnd, jit=0.16, spike=0.0):
    rings = []
    for ri_, (rx, ry, k) in enumerate(zip(radii_x, radii_y, counts)):
        if k == 1:
            rings.append([(c[0] + rnd.uniform(-rx, rx), c[1] + rnd.uniform(-ry, ry), 0.0)])
            continue
        R = []
        off = rnd.uniform(0, 2 * math.pi)
        for i in range(k):
            a = off + 2 * math.pi * i / k + rnd.uniform(-0.22, 0.22) * 2 * math.pi / k
            r = 1 + rnd.uniform(-jit, jit)
            if ri_ == 0 and spike:
                r *= (1 + spike) if i % 2 else (1 - spike * 0.6)
            R.append((c[0] + math.cos(a) * rx * r, c[1] + math.sin(a) * ry * r, a % (2 * math.pi)))
        R.sort(key=lambda q: q[2])
        rings.append(R)
    tris = []
    for ri in range(len(rings) - 1):
        outer, inner = rings[ri], rings[ri + 1]
        if len(inner) == 1:
            ctr = inner[0]
            for i in range(len(outer)):
                tris.append([outer[i][:2], outer[(i + 1) % len(outer)][:2], ctr[:2]])
            continue
        no, ni = len(outer), len(inner)
        start = min(range(ni), key=lambda q: (inner[q][2] - outer[0][2]) % (2 * math.pi))
        inner = inner[start:] + inner[:start]
        base = outer[0][2]
        ang = lambda q: (q[2] - base) % (2 * math.pi)
        i = j = 0
        while i < no or j < ni:
            o0, o1 = outer[i % no], outer[(i + 1) % no]
            i0, i1 = inner[j % ni], inner[(j + 1) % ni]
            ao = ang(o1) if i + 1 < no else 2 * math.pi
            ai = ang(i1) if j + 1 < ni else 2 * math.pi + ang(inner[0])
            if (ao <= ai and i < no) or j >= ni:
                tris.append([o0[:2], o1[:2], i0[:2]]); i += 1
            else:
                tris.append([o0[:2], i1[:2], i0[:2]]); j += 1
    return tris


def crumple(c, rx, ry, rnd, counts=(9, 5, 1), pal=KRAFT, shadow=False, g=G, jitn=0.8, jit=0.16, spike=0.0):
    tris = ring_mesh(c, (rx, rx * 0.55, rx * 0.12), (ry, ry * 0.55, ry * 0.12), counts, rnd, jit=jit, spike=spike)
    for T in tris:
        cc = centroid(T)
        v = sub(cc, c)
        n = (v[0] / rx + rnd.uniform(-jitn, jitn), v[1] / ry + rnd.uniform(-jitn, jitn))
        spoly(T, tone(n, pal))
        if shadow:
            shadow_polys.append([proj(q, g) for q in T])
    # random crease lines
    for T in tris:
        if rnd.random() < 0.6:
            a, b = rnd.sample(T, 2)
            line(lerp(a, b, 0.05), lerp(a, b, 0.95), pal[2], 1.5, 'opacity=".9"')
        if rnd.random() < 0.25:
            a, b = rnd.sample(T, 2)
            line(lerp(a, b, 0.15), lerp(a, b, 0.75), '#E6C38F', 1.2, 'opacity=".85"')
    return tris


def twisted(P, w, rnd, pal=KRAFT, twists=2.2, shadow=False, g=G, taper=0.25):
    C = catmull(P, 10)
    S = resample(C, 14)
    ph = rnd.uniform(0, math.pi)
    prev = None
    for i, (p, tg) in enumerate(S):
        t = i / (len(S) - 1)
        c = math.cos(ph + t * math.pi * twists)
        ww = w * (0.3 + 0.7 * abs(c)) * (1 - taper * t)
        n = perp(tg)
        a, b = plus(p, mul(n, ww / 2)), plus(p, mul(n, -ww / 2))
        if prev:
            pa, pb, pc = prev
            cm = (c + pc) / 2
            col = pal[1] if abs(cm) < 0.25 else tone(n if cm > 0 else mul(n, -1), pal)
            Q = [pa, a, b, pb]
            spoly(Q, col)
            if shadow:
                shadow_polys.append([proj(q, g) for q in Q])
        prev = (a, b, c)
    return S[-1][0]


def rope(P, w, rnd, pal=KRAFT, shadow=False, g=G, taper=0.35, pitch=13):
    """twisted paper rope: two-tone lengthwise + diagonal twist creases."""
    C = catmull(P, 10)
    S = resample(C, 18)
    cen = [q[0] for q in S]
    wd = [w * (1 - taper * i / (len(S) - 1)) * (1 + 0.12 * math.sin(i * 1.7)) for i in range(len(S))]
    Lh, Rh = offset_line(cen, wd, +1), offset_line(cen, wd, -1)
    Lm = offset_line(cen, [x * 0.2 for x in wd], +1)
    nL = perp(norm(sub(cen[-1], cen[0])))
    tL, tR = tone_idx(nL), tone_idx(mul(nL, -1))
    if tL == tR: tR = 2
    spoly(Lh + Lm[::-1], pal[tL]); spoly(Lm + Rh[::-1], pal[tR])
    if shadow:
        shadow_polys.append([proj(q, g) for q in Lh + Rh[::-1]])
    # twist creases
    L = sum(math.dist(cen[i], cen[i + 1]) for i in range(len(cen) - 1))
    n = int(L / pitch)
    D = resample(cen, max(3, n + 1))
    for i in range(1, len(D) - 1):
        p_, tg = D[i]
        k = i / (len(D) - 1)
        ww = w * (1 - taper * k) / 2
        a = plus(p_, mul(perp(tg), ww)); b = plus(plus(p_, mul(perp(tg), -ww)), mul(tg, pitch * 0.8))
        line(a, b, pal[2], 1.4, 'opacity=".9"')
    return cen[-1]


# ---------------------------------------------------------------- leaves
def _place(P, c, size, ang, squash):
    return [rot((c[0] + x * size, c[1] + y * size * squash), c, ang) for x, y in P]


def two_tone(right_half, c, size, ang, pal, squash=1.0, op=1.0, stem=None):
    """right_half: points (x>=0) from top tip (0,-a) to bottom (0,b); mirrored for left."""
    left_half = [(-x, y) for x, y in right_half]
    R = _place(right_half, c, size, ang, squash)
    Lh = _place(left_half, c, size, ang, squash)
    ax = norm(sub(R[-1], R[0]))
    nR = mul(perp(ax), -1)          # points to the right half in local frame
    e = f'opacity="{op:.2f}"' if op < 1 else ''
    tR, tL = tone_idx(nR), tone_idx(mul(nR, -1))
    if tR == tL:
        tR = min(2, tR + 1)
    spoly(R, pal[tR], e); spoly(Lh, pal[tL], e)
    if stem:
        b = _place([(0, stem[0]), (0, stem[1])], c, size, ang, squash)
        line(b[0], b[1], pal[2], max(1.0, size / 26), e)


MAPLE_R = [(0, -0.5), (0.07, -0.22), (0.36, -0.29), (0.16, -0.05), (0.27, 0.09), (0.07, 0.07), (0, 0.13)]
DIAM_R = [(0, -0.5), (0.31, -0.04), (0, 0.5)]
GINKGO_R = [(0, -0.30), (0.12, -0.42), (0.28, -0.40), (0.42, -0.28), (0.09, 0.22), (0, 0.32)]


def leaf(kind, c, size, ang, squash=1.0, op=1.0):
    if kind == 'm':
        two_tone(MAPLE_R, c, size, ang, RUST, squash, op, stem=(0.13, 0.36))
    elif kind == 'f':
        two_tone(GINKGO_R, c, size, ang, GOLD, squash, op, stem=(0.3, 0.5))
    else:
        two_tone(DIAM_R, c, size, ang, GOLD, squash, op)


# ===================================================================================== BUILD
rnd = random.Random(7)
defs = f'''<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1150" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{SKY_T}"/><stop offset=".5" stop-color="#E2DCC4"/><stop offset="1" stop-color="{SKY_B}"/></linearGradient>
<radialGradient id="sun" cx="120" cy="960" r="380" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#FFF1C8" stop-opacity="1"/><stop offset=".3" stop-color="#FFF1C8" stop-opacity=".6"/>
<stop offset="1" stop-color="#FFF1C8" stop-opacity="0"/></radialGradient>
<radialGradient id="grade" cx="120" cy="960" r="1500" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#FFC66A" stop-opacity=".55"/><stop offset=".6" stop-color="#E9A65A" stop-opacity=".25"/>
<stop offset="1" stop-color="#B98A5A" stop-opacity=".18"/></radialGradient>
<radialGradient id="sunwide" cx="120" cy="960" r="1000" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#FFE2A0" stop-opacity=".6"/><stop offset="1" stop-color="#FFE2A0" stop-opacity="0"/></radialGradient>
<linearGradient id="haze" x1="0" y1="760" x2="0" y2="1470" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#F6DDA6" stop-opacity="0"/><stop offset=".5" stop-color="#F6DDA6" stop-opacity=".26"/>
<stop offset="1" stop-color="#F6DDA6" stop-opacity="0"/></linearGradient>
<linearGradient id="vig" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/>
<stop offset="1" stop-color="#6E4A3A" stop-opacity=".26"/></linearGradient>
<filter id="fibre" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.9 0.2" numOctaves="3" seed="11"/>
<feColorMatrix values="0 0 0 0 .32  0 0 0 0 .24  0 0 0 0 .16  0 0 0 -1.4 1.1"/></filter>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4"/>
<feColorMatrix values="0 0 0 0 .5  0 0 0 0 .45  0 0 0 0 .4  0 0 0 2.4 -1.1"/></filter>
'''

# ---------------------------------------------------------------- 1 sky + sun
out.append('<rect width="1080" height="1920" fill="url(#sky)"/>')
out.append('<rect width="1080" height="1920" fill="url(#sunwide)" style="mix-blend-mode:screen"/>')
out.append('<circle cx="120" cy="960" r="380" fill="url(#sun)" opacity=".75" style="mix-blend-mode:screen"/>')
out.append('<circle cx="120" cy="958" r="50" fill="#FFF8E6"/>')

# very far hills / tree line (haze)
P = [(0, 930)]
x = 0
while x < 1100:
    x += rnd.uniform(30, 70)
    P.append((x, 905 + rnd.uniform(-22, 18)))
P += [(1080, 1100), (0, 1100)]
poly(P, '#E2D2A8', 'opacity=".75"')

# ---------------------------------------------------------------- 3 far temple: pyramidal hall roof with a finial
ROOF = '#9DA1A3'; ROOF_D = '#92979A'
apx, apy = 330, 878
roof = [(-30, 1000), (20, 994), (80, 976), (160, 944), (apx, apy), (500, 944), (580, 976), (640, 994), (690, 1000),
        (640, 1008), (20, 1008)]
poly(roof, ROOF)
poly([(apx, apy), (500, 944), (580, 976), (640, 994), (690, 1000), (640, 1008), (apx, 1008)], ROOF_D)  # shade side
poly([(60, 1008), (600, 1008), (600, 1066), (60, 1066)], '#8E9295')
for xx in range(96, 600, 58):
    poly([(xx, 1012), (xx + 7, 1012), (xx + 7, 1066), (xx, 1066)], '#85898C')
# finial (hoju + rings)
poly([(apx - 5, apy + 2), (apx + 5, apy + 2), (apx + 3, 800), (apx - 3, 800)], ROOF)
for k in range(6):
    yy = 812 + k * 10
    w = 15 - k * 0.8
    poly([(apx - w, yy), (apx + w, yy), (apx + w - 2, yy + 4), (apx - w + 2, yy + 4)], ROOF)
poly([(apx, 772), (apx + 9, 790), (apx, 800), (apx - 9, 790)], ROOF)
# right: earthen wall with tile cap
poly([(640, 1006), (1080, 996), (1080, 1010), (640, 1018)], '#9A9C9A')
poly([(650, 1016), (1080, 1008), (1080, 1080), (650, 1084)], '#CDC3AB')
for k in range(5):
    yy = 1032 + k * 9
    out.append(f'<line x1="650" y1="{yy}" x2="1080" y2="{yy - 8}" stroke="#BCB29A" stroke-width="2.4"/>')


# ---------------------------------------------------------------- 4 ginkgo trees
def ginkgo(cx, cy, rx, ry, spacing, trunk, rnd, pal=GOLD_FAR, branches=()):
    tx, ty0, ty1, tw = trunk
    poly([(tx - tw, ty1), (tx - tw * 0.5, ty0), (tx, ty0), (tx, ty1)], '#6A6C72')
    poly([(tx, ty1), (tx, ty0), (tx + tw * 0.5, ty0), (tx + tw, ty1)], '#55585F')
    for (a, b, w) in branches:
        strip(a, b, w, w * 0.4, ('#6A6C72', '#5F6168', '#55585F'), ridge=False, curl=False)
    grid = {}
    rows = int(2 * ry / (spacing * 0.87)) + 3
    cols = int(2 * rx / spacing) + 3
    for r in range(rows):
        for q in range(cols):
            x = cx - rx - spacing + q * spacing + (spacing / 2 if r % 2 else 0) + rnd.uniform(-0.28, 0.28) * spacing
            y = cy - ry - spacing * 0.5 + r * spacing * 0.87 + rnd.uniform(-0.28, 0.28) * spacing
            grid[(r, q)] = (x, y)

    def inside(p):
        dx, dy = (p[0] - cx) / rx, (p[1] - cy) / ry
        # upright ginkgo: narrower towards top
        k = 1 + 0.35 * max(0, -dy)
        return (dx * k) ** 2 + dy ** 2 < 1
    n = 0
    for r in range(rows - 1):
        for q in range(cols - 1):
            A, B, C_, D = grid[(r, q)], grid[(r, q + 1)], grid[(r + 1, q)], grid[(r + 1, q + 1)]
            for T in ([A, B, C_], [B, D, C_]) if r % 2 == 0 else ([A, B, D], [A, D, C_]):
                cc = centroid(T)
                if not inside(cc):
                    continue
                n += 1
                v = sub(cc, (cx, cy))
                nn = (v[0] / rx + rnd.uniform(-0.7, 0.7), v[1] / ry + rnd.uniform(-0.7, 0.7))
                spoly(T, tone(nn, pal))
    # lacy edge: small leaf-flecks around the rim
    for i in range(46):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(0.86, 1.08)
        dy = math.sin(a)
        k = 1 + 0.35 * max(0, -dy)
        p = (cx + math.cos(a) * rx * rr / k, cy + dy * ry * rr)
        two_tone(DIAM_R, p, rnd.uniform(10, 18), rnd.uniform(0, 6.3), pal)
    return n


def fan_lobe(c, r, a0, a1, pleats, pal, rnd, ridge_col=None):
    """A pleated ginkgo-leaf fan (crown unit): pleats alternate facing, tone from the light model."""
    arc = []
    for k in range(pleats + 1):
        a = math.radians(a0 + (a1 - a0) * k / pleats)
        rr = r * (1.0 + (0.05 if k % 2 else -0.03)) * rnd.uniform(0.97, 1.03)
        arc.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    tris = []
    for k in range(pleats):
        th = math.radians(a0 + (a1 - a0) * (k + 0.5) / pleats)
        u = (math.cos(th), math.sin(th))
        s = 0.9 if k % 2 == 0 else -0.9
        n = plus(u, mul(perp(u), s))
        T = [c, arc[k], arc[k + 1]]
        spoly(T, tone(n, pal))
        tris.append(T)
    if ridge_col:
        for k in range(1, pleats, 2):
            line(c, arc[k], ridge_col, 1.4, 'opacity=".55"')
    return arc


def ginkgo_fans(lobes, trunk, rnd, pal=GOLD_FAR, branches=(), ridge_col='#FFF0C4'):
    tx, ty0, ty1, tw = trunk
    poly([(tx - tw, ty1), (tx - tw * 0.45, ty0), (tx, ty0), (tx, ty1)], '#6E7076')
    poly([(tx, ty1), (tx, ty0), (tx + tw * 0.45, ty0), (tx + tw, ty1)], '#5A5C63')
    for (a, b, w) in branches:
        strip(a, b, w, w * 0.4, ('#6E7076', '#64666C', '#5A5C63'), ridge=False, curl=False)
    n = 0
    for (cx, cy, r, spread) in lobes:
        # thin cut-paper shadow under each lobe (layered paper)
        fan_lobe((cx + 5, cy + 5), r, 270 - spread, 270 + spread, 5, ('#B48F45',) * 3, random.Random(1))
        fan_lobe((cx, cy), r, 270 - spread, 270 + spread, 5, pal, rnd, ridge_col)
        n += 5
    return n


n1 = ginkgo_fans([(130, 470, 118, 70), (40, 560, 120, 72), (226, 566, 110, 70), (-30, 680, 130, 74),
                  (140, 660, 140, 74), (270, 690, 112, 70), (60, 800, 136, 76), (220, 806, 118, 74)],
                 (120, 760, 1080, 30), rnd,
                 branches=[((120, 920), (40, 790), 18), ((122, 880), (222, 760), 16)])
n2 = ginkgo_fans([(960, 640, 100, 70), (880, 730, 104, 72), (1050, 730, 110, 72), (960, 820, 124, 74),
                  (860, 900, 104, 72), (1060, 910, 112, 74)],
                 (965, 860, 1084, 24), rnd,
                 branches=[((965, 980), (890, 900), 14), ((966, 950), (1040, 860), 14)])

# ---------------------------------------------------------------- 4b moss terrace bank + stone stair
STAIR_B, STAIR_T = (300, 760, 1405), (418, 642, 1078)


def stair_x(y):
    t = (STAIR_B[2] - y) / (STAIR_B[2] - STAIR_T[2])
    return STAIR_B[0] + (STAIR_T[0] - STAIR_B[0]) * t, STAIR_B[1] + (STAIR_T[1] - STAIR_B[1]) * t


poly([(0, 1064), (1080, 1070), (1080, 1102), (0, 1096)], MOSS[0])
bankL = [(0, 1094), (stair_x(1094)[0] - 26, 1094), (stair_x(1405)[0] - 40, 1430), (0, 1440)]
bankR = [(stair_x(1094)[1] + 26, 1100), (1080, 1100), (1080, 1444), (stair_x(1405)[1] + 40, 1432)]
poly(bankL, MOSS[1]); poly(bankR, MOSS[2])
# big folded planes on the bank
for P, t in [([(0, 1094), (150, 1094), (60, 1260), (0, 1250)], 0), ([(150, 1094), (stair_x(1094)[0] - 26, 1094), (stair_x(1300)[0] - 34, 1300), (60, 1260)], 1),
             ([(0, 1250), (60, 1260), (stair_x(1300)[0] - 34, 1300), (stair_x(1405)[0] - 40, 1430), (0, 1440)], 2),
             ([(stair_x(1094)[1] + 26, 1100), (900, 1100), (980, 1250), (stair_x(1300)[1] + 34, 1302)], 1),
             ([(900, 1100), (1080, 1100), (1080, 1270), (980, 1250)], 2),
             ([(stair_x(1300)[1] + 34, 1302), (980, 1250), (1080, 1270), (1080, 1444), (stair_x(1405)[1] + 40, 1432)], 2)]:
    spoly(P, ('#76854F', '#66744A', '#55623D')[t])
line((0, 1095), (stair_x(1094)[0] - 26, 1095), '#F4E3A6', 3, 'opacity=".75"')
line((stair_x(1094)[1] + 26, 1101), (1080, 1101), '#F4E3A6', 2, 'opacity=".45"')
# moss mounds (rounded karikomi as faceted domes)
for (mx, my, mr) in [(90, 1190, 120), (250, 1300, 80), (20, 1380, 110), (870, 1200, 110), (1030, 1300, 120), (800, 1360, 70)]:
    k = 8
    P = [(mx + math.cos(math.pi + math.pi * i / (k - 1)) * mr, my + math.sin(math.pi + math.pi * i / (k - 1)) * mr * 0.6) for i in range(k)]
    c0 = (mx - mr * 0.2, my - mr * 0.28)
    for i in range(k - 1):
        T = [P[i], P[i + 1], c0]
        nn = sub(centroid(T), (mx, my + mr * 0.3))
        spoly(T, tone(nn, MOSS))
    spoly([P[0], c0, P[-1]], MOSS[2])
yb, yt = STAIR_B[2], STAIR_T[2]
poly([(stair_x(yt)[0] - 22, yt + 6), (stair_x(yt)[0], yt), (STAIR_B[0], yb), (STAIR_B[0] - 40, yb + 18)], '#DCCBA2')
poly([(stair_x(yt)[1], yt), (stair_x(yt)[1] + 22, yt + 6), (STAIR_B[1] + 40, yb + 18), (STAIR_B[1], yb)], '#86847F')
steps, ratio = 7, 0.86
h0 = (yb - yt) * (1 - ratio) / (1 - ratio ** steps)
y = yb
RISER = '#8E8D8C'          # slate seen through haze
for k in range(steps):
    hk = h0 * ratio ** k
    riser = hk * (0.5 - 0.1 * k / steps)
    ya, yr, yt2 = y, y - riser, y - hk
    xa0, xa1 = stair_x(ya); xr0, xr1 = stair_x(yr); xt0, xt1 = stair_x(yt2)
    poly([(xa0, ya), (xa1, ya), (xr1, yr), (xr0, yr)], RISER)
    poly([(xr0, yr), (xr1, yr), (xt1, yt2), (xt0, yt2)], TREAD)
    line((xr0 + 2, yr + 1), (xr1 - 2, yr + 1), '#FFF4D6', 1.5, 'opacity=".9"')
    y = yt2
for i in range(40):
    leaf(rnd.choice('ggfm'), (rnd.uniform(0, 1080), rnd.uniform(1100, 1430)), rnd.uniform(10, 16), rnd.uniform(0, 6.3), 0.5)

# ---------------------------------------------------------------- kasumi (stylised mist bands)
def kasumi(x0, x1, y, h, op, col='#FBF2DE'):
    r = h / 2
    P = []
    for k in range(13):
        a = math.pi / 2 + math.pi * k / 12
        P.append((x0 + math.cos(a) * r, y + r + math.sin(a) * r))
    for k in range(13):
        a = -math.pi / 2 + math.pi * k / 12
        P.append((x1 + math.cos(a) * r, y + r + math.sin(a) * r))
    poly(P, col, f'opacity="{op}"')


kasumi(-40, 470, 956, 30, .5)
kasumi(150, 400, 938, 18, .35)
kasumi(700, 1120, 1020, 30, .55)

# ---------------------------------------------------------------- 2 light shafts + haze
sh = []
for a0, a1 in [(-16, -11), (-4, 2), (7, 10), (16, 24), (31, 35)]:
    r, A = 2400, (60, 900)
    sh.append([A, (A[0] + r * math.cos(math.radians(a0)), A[1] + r * math.sin(math.radians(a0))),
               (A[0] + r * math.cos(math.radians(a1)), A[1] + r * math.sin(math.radians(a1)))])
out.append('<g style="mix-blend-mode:screen" opacity=".16">')
for T in sh:
    poly(T, '#FFE9B8')
out.append('</g>')
out.append('<rect x="0" y="760" width="1080" height="720" fill="url(#haze)"/>')

# ---------------------------------------------------------------- 5 ground (raked gravel)
poly([(0, 1440), (stair_x(1405)[0] - 40, 1430), (STAIR_B[0], 1405), (STAIR_B[1], 1405), (stair_x(1405)[1] + 40, 1432),
      (1080, 1444), (1080, 1920), (0, 1920)], IVORY)
STONE = (190, 1716)
RINGS = 6
out.append('<defs><mask id="rakemask"><rect width="1080" height="1920" fill="#fff"/>'
           f'<ellipse cx="{STONE[0]}" cy="{STONE[1]}" rx="{92 + RINGS * 22 + 8}" ry="{30 + RINGS * 10 + 5}" fill="#000"/></mask></defs>')
out.append('<g mask="url(#rakemask)" opacity=".18">')
yy, sp = 1452.0, 12.0
while yy < 1930:
    P = [(x, yy + 3.5 * math.sin(x / 230 + yy / 80) + (x - 540) * 0.005) for x in range(-10, 1100, 30)]
    pline(P, SLATE, 2)
    sp *= 1.01
    yy += sp
out.append('</g><g opacity=".26">')
for i in range(1, RINGS + 1):
    out.append(f'<ellipse cx="{STONE[0]}" cy="{STONE[1]}" rx="{92 + i * 22}" ry="{30 + i * 10}" fill="none" stroke="{SLATE}" stroke-width="2"/>')
out.append('</g>')
# dappled foreground shadow (off-screen tree) - calm, darker bottom band for UI
fg = [(0, 1720)]
x = 0
while x < 1100:
    x += rnd.uniform(50, 110)
    fg.append((x, 1720 + x * 0.06 + rnd.uniform(-22, 22)))
fg += [(1080, 1920), (0, 1920)]
shadow_polys.append(fg)
# stone
sc = STONE
SP = [(sc[0] - 92, sc[1] + 18), (sc[0] - 70, sc[1] - 30), (sc[0] - 20, sc[1] - 54), (sc[0] + 42, sc[1] - 44), (sc[0] + 88, sc[1] - 6), (sc[0] + 80, sc[1] + 22)]
topc = (sc[0] - 10, sc[1] - 18)
shadow_polys.append([proj(q, sc[1] + 20) for q in SP])
for i in range(len(SP) - 1):
    T = [SP[i], SP[i + 1], topc]
    spoly(T, tone(sub(centroid(T), (sc[0], sc[1] + 10)), ('#BDB6A3', '#8E8B86', '#5E5F66')))
spoly([SP[0], topc, SP[-1]], '#5E5F66')
spoly([(sc[0] - 92, sc[1] + 18), (sc[0] + 80, sc[1] + 22), (sc[0] + 70, sc[1] + 30), (sc[0] - 80, sc[1] + 27)], MOSS[2])

# ---------------------------------------------------------------- buffers
def capture(fn):
    global out
    saved = out; out = []
    fn()
    res = out; out = saved
    return res


FY0, FY1 = 1300, 1478
POSTS = [818, 900, 1030]
RINGS_X = (900, 1030)
RING_Y = 1380


def draw_fence():
    for x0 in POSTS:
        shadow_polys.append([proj(q, FY1) for q in [(x0 - 12, FY1), (x0 + 12, FY1), (x0 + 12, FY0), (x0 - 12, FY0)]])
    for yr0, yr1 in [(1334, 1350), (1418, 1432)]:
        shadow_polys.append([proj(q, FY1) for q in [(800, yr0), (1100, yr0 - 4), (1100, yr1 - 4), (800, yr1)]])
        spoly([(800, yr0 + 4), (1080, yr0 - 2), (1080, yr1 - 2), (800, yr1 + 4)], FENCE[1])
        spoly([(800, yr0 + 4), (1080, yr0 - 2), (1080, yr0 + 2), (800, yr0 + 8)], FENCE[0])
    for x0 in POSTS:
        spoly([(x0 - 13, FY1), (x0 - 13, FY0 + 8), (x0, FY0), (x0, FY1)], FENCE[0])
        spoly([(x0, FY1), (x0, FY0), (x0 + 13, FY0 + 8), (x0 + 13, FY1)], FENCE[2])
        line((x0 - 13, FY0 + 8), (x0, FY0), RIDGE, 1.5, 'opacity=".8"')
    for rx_ in RINGS_X:
        out.append(f'<ellipse cx="{rx_ + 16}" cy="{RING_Y}" rx="14" ry="17" fill="none" stroke="#7A5A22" stroke-width="6"/>')
        out.append(f'<ellipse cx="{rx_ + 16}" cy="{RING_Y}" rx="14" ry="17" fill="none" stroke="{BRASS}" stroke-width="4"/>')
        out.append(f'<path d="M{rx_ + 4},{RING_Y - 8} A14,17 0 0 1 {rx_ + 20},{RING_Y - 16}" fill="none" stroke="#F6DC96" stroke-width="2"/>')
        spoly([(rx_ + 10, RING_Y - 22), (rx_ + 16, RING_Y - 26), (rx_ + 22, RING_Y - 22), (rx_ + 16, RING_Y - 16)], '#8E6A2A')


# --- mook A: un-crumpled and neatly re-folded into a flat paper "yakko" doll,
#     both sleeve tips clicked into the brass rings on the fence
def mook_A():
    base = (972, 1480)
    lean = math.radians(-3)
    T = lambda p: rot(p, base, lean)
    r0, r1 = (RINGS_X[0] + 16, RING_Y), (RINGS_X[1] + 16, RING_Y)
    cx = (r0[0] + r1[0]) / 2
    # hakama trapezoid (two panels, centre notch)
    hk = [T(p) for p in [(cx - 26, 1400), (cx + 26, 1400), (cx + 50, 1480), (cx + 6, 1480), (cx, 1462), (cx - 6, 1480), (cx - 50, 1480)]]
    spoly([hk[0], T((cx, 1400)), T((cx, 1462)), hk[5], hk[6]], KRAFT[0])
    spoly([T((cx, 1400)), hk[1], hk[2], hk[3], T((cx, 1462))], KRAFT[1])
    line(T((cx, 1400)), T((cx, 1462)), RIDGE, 1.5, 'opacity=".8"')
    # sleeves: wide horizontal band ring-to-ring
    sl = [T(p) for p in [(r0[0] + 10, 1360), (r1[0] - 10, 1360), (r1[0] - 10, 1402), (r0[0] + 10, 1402)]]
    spoly(sl, KRAFT[0])
    spoly([sl[1], sl[2], T((cx + 30, 1402))], KRAFT[1])
    spoly([sl[0], sl[3], T((cx - 30, 1402))], KRAFT[1])
    line(T((cx, 1360)), T((cx, 1402)), KRAFT[2], 1.2, 'opacity=".6"')
    line(sl[0], sl[1], RIDGE, 1.5, 'opacity=".8"')
    # sleeve tips through the rings
    spoly([T((r0[0] + 10, 1368)), r0, T((r0[0] + 10, 1394))], KRAFT[1])
    spoly([T((r1[0] - 10, 1368)), r1, T((r1[0] - 10, 1394))], KRAFT[2])
    # head: folded square on point
    hc = T((cx, 1334))
    HP = [(hc[0], hc[1] - 30), (hc[0] + 26, hc[1]), (hc[0], hc[1] + 26), (hc[0] - 26, hc[1])]
    spoly([HP[0], HP[3], HP[2]], KRAFT[0]); spoly([HP[0], HP[1], HP[2]], KRAFT[1])
    line(HP[3], HP[0], RIDGE, 1.5, 'opacity=".8"')
    for P in (hk, sl, HP):
        shadow_polys.append([proj(q, base[1]) for q in P])
    # residual creases (it used to be crumpled)
    for a, b in [((cx - 44, 1372), (cx + 30, 1392)), ((cx - 20, 1420), (cx + 26, 1446)), ((cx + 14, 1408), (cx - 12, 1474))]:
        line(T(a), T(b), KRAFT[2], 1, 'opacity=".4"')
    # click ticks at the first ring
    for a in (-160, -122, -84):
        d = (math.cos(math.radians(a)), math.sin(math.radians(a)))
        line(plus(r0, mul(d, 28)), plus(r0, mul(d, 48)), RIDGE, 4)


# --- mook B: balled up tight, mid-roll toward the broom (airborne)
def mook_B():
    r = random.Random(5)
    c = (846, 1186)
    rope([(878, 1146), (910, 1120), (936, 1130)], 15, r)
    rope([(812, 1232), (792, 1262), (812, 1284)], 15, r)
    crumple(c, 64, 60, r, counts=(14, 8, 1), jit=0.12, spike=0.12)
    for k in range(3):
        a0, a1 = -50 + k * 6, 26 + k * 6
        rr = 88 + k * 13
        P = [(c[0] + math.cos(math.radians(a)) * rr, c[1] + math.sin(math.radians(a)) * rr) for a in range(a0, a1, 6)]
        pline(P, '#FFF4D8', 3.4 - k * 0.8, f'opacity="{0.85 - k * 0.2:.2f}"')


# --- mook C: lunging in from the left edge behind the hero, arms raised toward him (cropped)
def mook_C():
    r = random.Random(33)
    gC = 1640
    rope([(30, 1500), (0, 1572), (-30, 1640)], 26, r, shadow=True, g=gC)
    rope([(100, 1500), (138, 1566), (176, 1636)], 26, r, shadow=True, g=gC)
    crumple((66, 1434), 86, 92, r, counts=(16, 9, 1), shadow=True, g=gC, jit=0.12, spike=0.14)
    crumple((130, 1316), 52, 48, r, counts=(13, 7, 1), shadow=True, g=gC, jit=0.12, spike=0.16)
    end = rope([(130, 1392), (196, 1360), (244, 1300), (262, 1246)], 22, r, shadow=True, g=gC)
    crumple(end, 24, 22, r, counts=(9, 4, 1), jit=0.15, spike=0.2)
    end2 = rope([(60, 1366), (98, 1290), (156, 1234)], 22, r, shadow=True, g=gC)
    crumple(end2, 22, 22, r, counts=(9, 4, 1), jit=0.15, spike=0.2)


# --- hero: origami monk-sweeper in kon-indigo paper
FR, FL = (338, 1552), (748, 1552)
KR, KL = (432, 1318), (690, 1298)
N_, SR, SL = (640, 756), (520, 800), (730, 792)
WL, WR = (540, 1030), (614, 1022)
WC = lerp(WL, WR, 0.36)
BROOM_A, BROOM_B = (450, 520), (860, 1470)
HR = lerp(BROOM_A, BROOM_B, 0.36)
HL = lerp(BROOM_A, BROOM_B, 0.54)
ER, EL = (474, 926), (786, 900)
HEAD = (672, 676)
HW, HH = 120, 156
TILT = math.radians(12)


def pleated_leg(C, widths, pleats=4, hem_drop=10):
    """hakama leg along centreline C (3 pts) with accordion pleats."""
    Cd = catmull(C, 8)
    wd = []
    L = [0]
    for i in range(1, len(Cd)):
        L.append(L[-1] + math.dist(Cd[i - 1], Cd[i]))
    for s in L:
        t = s / L[-1]
        wd.append(widths[0] + (widths[1] - widths[0]) * min(1, t * 2) + (widths[2] - widths[1]) * max(0, t * 2 - 1))
    left = offset_line(Cd, wd, +1)
    right = offset_line(Cd, wd, -1)
    fr, acc, shares = [], 0, []
    for j in range(pleats):
        shares += [0.28, 0.72]
    tot = sum(shares)
    for s in shares:
        fr.append(acc / tot); acc += s
    fr.append(1.0)
    lines_ = []
    for k, u in enumerate(fr):
        Lk = [lerp(left[i], right[i], u) for i in range(len(Cd))]
        if 0 < k < len(fr) - 1 and k % 2 == 1:
            Lk[-1] = plus(Lk[-1], (0, hem_drop))
        lines_.append(Lk)
    d = norm(sub(C[-1], C[0]))
    nl = perp(d)
    for k in range(len(fr) - 1):
        P = lines_[k] + lines_[k + 1][::-1]
        facing = nl if k % 2 == 0 else mul(nl, -1)
        col = tone(facing, KON)
        if k % 2 == 1 and col == KON[0]:
            col = KON[1]
        spoly(P, col)
    for k in range(1, len(fr) - 1):
        if k % 2 == 1:
            pline(lines_[k], RIDGE, 1.6, 'opacity=".9"')
        else:
            pline(lines_[k], KON[2], 1.2)
    pline(lines_[0], '#8FA2CF', 1.2, 'opacity=".8"')
    shadow_polys.append([proj(q) for q in left + right[::-1]])
    return left, right


def sleeve_flap(E_, H_, drop, sweep, front):
    """kimono sleeve: rectangular folded flap hanging from the forearm, swept back by the motion."""
    a = lerp(E_, H_, 0.02)
    b = lerp(E_, H_, 0.78)
    fa = plus(a, (sweep, drop))
    fb = plus(b, (sweep * 0.7, drop * 0.82))
    fold = lerp(fa, fb, 0.42)
    spoly([a, b, fb, fold], KON[1])
    spoly([a, fold, fa], KON[2])
    line(a, fold, RIDGE, 1.6, 'opacity=".85"')
    line(a, fa, '#8FA2CF', 1.3, 'opacity=".85"')
    line(fa, fb, KON[2], 1.2)
    shadow_polys.append([proj(q) for q in (a, b, fb, fa)])


def arm(S_, E_, H_):
    strip(S_, E_, 52, 46, KON, shadow=True, lit_frac=0.3)
    strip(E_, H_, 46, 36, KON, shadow=True, lit_frac=0.3)
    d1, d2 = norm(sub(E_, S_)), norm(sub(H_, E_))
    spoly([plus(E_, mul(perp(d1), 24)), plus(E_, mul(perp(d2), 22)), plus(E_, mul(d1, -12))], KON[1])


def hand(Hh, s=1.2):
    P = [(Hh[0] - 17 * s, Hh[1] - 6 * s), (Hh[0] + 4 * s, Hh[1] - 20 * s), (Hh[0] + 20 * s, Hh[1] + 6 * s), (Hh[0] - 1 * s, Hh[1] + 20 * s)]
    spoly(P, KON[1]); spoly([P[0], P[1], P[3]], KON[0])
    line(P[0], P[1], RIDGE, 2)


def hero_back():
    # tenugui tails: two short folded strips from the knot, trailing back-down
    knot = rot((HEAD[0] - 58, HEAD[1] - 20), HEAD, TILT)
    for path, w in [([(-96, -30), (-138, -18)], 17), ([(-90, 0), (-122, 26)], 15)]:
        Q = [knot] + [rot((HEAD[0] + x, HEAD[1] + y), HEAD, TILT) for x, y in path]
        for i in range(len(Q) - 1):
            d = norm(sub(Q[i + 1], Q[i])); pp = perp(d)
            w0, w1 = w * (1 - 0.3 * i), w * (0.7 - 0.3 * i) if i < len(Q) - 2 else 0.5
            P = [plus(Q[i], mul(pp, w0 / 2)), plus(Q[i + 1], mul(pp, w1 / 2)), plus(Q[i + 1], mul(pp, -w1 / 2)), plus(Q[i], mul(pp, -w0 / 2))]
            spoly(P, TENU[0] if i == 0 else TENU[2])
            if i == len(Q) - 2:
                spoly([P[1], P[2], plus(Q[i + 1], mul(d, 14))], TENU[2] if i == 0 else TENU[1])
    # rear sleeve flap + rear arm (behind torso)
    arm(SR, ER, HR)
    sleeve_flap(ER, HR, 118, -34, front=False)
    # feet (tabi)
    for F, L_ in ((FR, 52), (FL, 60)):
        spoly([(F[0] - 22, F[1] - 18), (F[0] + L_, F[1] - 2), (F[0] - 22, F[1] + 4)], KON[2])
        line((F[0] - 22, F[1] - 18), (F[0] + L_, F[1] - 2), '#8FA2CF', 1.2)
    pleated_leg([(546, 1056), KR, (FR[0] + 6, FR[1] - 12)], (86, 110, 172))
    pleated_leg([(600, 1050), KL, (FL[0] - 8, FL[1] - 12)], (88, 114, 178))
    ob = [(528, 1016), (628, 1004), (632, 1058), (524, 1070)]
    spoly(ob, KON[2])
    spoly([(528, 1016), (628, 1004), (629, 1018), (528, 1030)], KON[1])
    line((528, 1016), (628, 1004), RIDGE, 2)
    # hakama tie cord: a thin rust accent
    spoly([(530, 1044), (630, 1032), (630, 1040), (530, 1052)], RUST[0])
    spoly([(600, 1036), (618, 1034), (626, 1080), (612, 1082)], RUST[2])
    shadow_polys.append([proj(q) for q in ob])


def hero_torso():
    # V torso: lit sliver (sun side) | mid front panel | shade side
    spoly([N_, SR, WL, WC], KON[0]); spoly([N_, WC, WR, SL], KON[2])
    PL1, PL2 = lerp(SR, N_, 0.2), lerp(WL, WR, 0.2)
    spoly([N_, PL1, PL2, WC], KON[1])
    shadow_polys.append([proj(q) for q in (N_, SR, WL, WR, SL)])
    # neck (short) + head
    nb = rot((HEAD[0] - 2, HEAD[1] + 44), HEAD, TILT)
    strip(nb, plus(N_, (0, 8)), 44, 44, KON, ridge=False, lit_frac=0.3)
    # cross collar: ivory under-collar + indigo lapel
    spoly([(612, 764), (640, 754), (652, 768), (622, 850)], TENU[1])
    spoly([(600, 772), (632, 760), (684, 780), (614, 900)], KON[1])
    spoly([(600, 772), (614, 900), (608, 790)], KON[0])
    line((632, 760), (614, 900), RIDGE, 2)
    line(PL1, PL2, RIDGE, 2)
    line(N_, SR, RIDGE, 2)
    line(SR, WL, '#8FA2CF', 1.2, 'opacity=".8"')
    cx, cy = HEAD
    # faceted origami head: 7-point gem outline with a forward chin, facets around an inner apex
    OL = [(-6, -70), (38, -50), (58, 4), (26, 62), (-28, 56), (-56, -2), (-42, -50)]
    OL = [rot((cx + x, cy + y), HEAD, TILT) for x, y in OL]
    ap = rot((cx + 10, cy - 6), HEAD, TILT)
    tones_ = []
    for i in range(len(OL)):
        A_, B2 = OL[i], OL[(i + 1) % len(OL)]
        n = sub(lerp(A_, B2, 0.5), ap)
        ti = tone_idx(n)
        tones_.append(ti)
        spoly([ap, A_, B2], KON[ti])
    for i in range(len(OL)):
        # ridge on creases between a lit facet and its neighbour
        if tones_[i] == 0 or tones_[i - 1] == 0:
            line(ap, OL[i], RIDGE, 2)
    for i in range(len(OL)):
        if tones_[i] == 0:
            line(OL[i], OL[(i + 1) % len(OL)], '#8FA2CF', 1.4, 'opacity=".85"')
    shadow_polys.append([proj(q) for q in OL])
    # tenugui band around the brow + knot at the back
    band = [rot((cx + x, cy + y), HEAD, TILT) for x, y in [(-52, -34), (44, -40), (52, -20), (-56, -12)]]
    spoly(band, TENU[0])
    low = [rot((cx + x, cy + y), HEAD, TILT) for x, y in [(-56, -12), (52, -20), (48, -10), (-54, -2)]]
    spoly(low, TENU[2])
    kx, ky = cx - 56, cy - 22
    kn = [rot(p, HEAD, TILT) for p in [(kx - 14, ky - 2), (kx + 4, ky - 14), (kx + 14, ky + 4), (kx - 4, ky + 16)]]
    spoly(kn, TENU[1]); spoly([kn[0], kn[3], kn[2]], TENU[2])


def hero_front_arms():
    arm(SL, EL, HL)
    sleeve_flap(EL, HL, 112, -30, front=True)
    hand(HR); hand(HL)


def broom_shaft():
    A, B = BROOM_A, BROOM_B
    d = norm(sub(B, A)); p = perp(d)
    w = 15
    spoly([plus(A, mul(p, w / 2)), plus(B, mul(p, w / 2)), B, A], ROD[1])
    spoly([plus(A, mul(p, -w / 2)), plus(B, mul(p, -w / 2)), B, A], ROD[0])
    L = math.dist(A, B)
    for k in range(int(L / 36)):
        c = lerp(A, B, (k + 0.5) / (L / 36))
        line(plus(c, mul(p, -w / 2)), plus(plus(c, mul(p, w / 2)), mul(d, 12)), ROD[1], 1.2, 'opacity=".75"')
    line(plus(A, mul(p, -w / 2 + 2)), plus(B, mul(p, -w / 2 + 2)), RIDGE, 1.5, 'opacity=".85"')
    spoly([plus(A, mul(p, 9)), plus(A, mul(p, -9)), plus(A, mul(d, -18))], KRAFT[2])
    shadow_polys.append([proj(q) for q in (plus(A, mul(p, 8)), plus(B, mul(p, 8)), plus(B, mul(p, -8)), plus(A, mul(p, -8)))])


def broom_fan():
    apex = BROOM_B
    a0, a1 = math.radians(146), math.radians(24)
    n, r0 = 12, 16
    rays = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        d = (math.cos(a), math.sin(a))
        r1 = min(230, (1566 - apex[1]) / max(0.12, d[1]))
        rays.append((plus(apex, mul(d, r0)), plus(apex, mul(d, r1))))
    for i in range(n):
        Q = [rays[i][0], rays[i][1], rays[i + 1][1], rays[i + 1][0]]
        spoly(Q, FAN[i % 2])
        shadow_polys.append([proj(q, 1566) for q in Q])
    for i in range(0, n + 1, 2):
        line(rays[i][0], rays[i][1], '#B3A684', 1.2)
    for i in range(1, n, 2):
        line(rays[i][0], rays[i][1], '#FFFFFF', 1.2, 'opacity=".8"')
    spoly([plus(apex, (-16, -6)), plus(apex, (14, -12)), plus(apex, (20, 8)), plus(apex, (-10, 14))], RUST[0])
    spoly([plus(apex, (-10, 14)), plus(apex, (20, 8)), plus(apex, (12, 16))], RUST[2])


fence_buf = capture(draw_fence)
A_buf = capture(mook_A)
B_buf = capture(mook_B)
C_buf = capture(mook_C)
hb_buf = capture(hero_back)
ht_buf = capture(hero_torso)
shaft_buf = capture(broom_shaft)
arms_buf = capture(hero_front_arms)
fan_buf = capture(broom_fan)

# warm golden-hour grade on the world only (characters keep their pure paper colours)
out.append('<rect width="1080" height="1920" fill="url(#grade)" style="mix-blend-mode:soft-light"/>')
# ---------------------------------------------------------------- 12 cast shadows (one group: no double darkening)
out.append(f'<g opacity=".40" style="mix-blend-mode:multiply" fill="{SLATE}">')
for P in shadow_polys:
    out.append(f'<polygon points="{pts(P)}"/>')
out.append('</g>')

# ground leaves: 60 near the broom + scatter
for i in range(60):
    x = rnd.gauss(910, 100); yy = rnd.gauss(1572, 30)
    leaf(rnd.choice('ggfm'), (x, max(1490, yy)), rnd.uniform(24, 36), rnd.uniform(0, 6.3), 0.5)
for i in range(18):
    leaf(rnd.choice('gfm'), (rnd.uniform(0, 1080), rnd.uniform(1470, 1760)), rnd.uniform(20, 30), rnd.uniform(0, 6.3), 0.5)

out += fence_buf + A_buf + C_buf + hb_buf + ht_buf + shaft_buf + arms_buf + fan_buf

# ---------------------------------------------------------------- 10 leaf-trail spiral (sweep motion line)
ctrl = [(880, 1500), (962, 1452), (1004, 1340), (1008, 1180), (962, 1000), (872, 830), (750, 664), (600, 532), (420, 492),
        (262, 540), (176, 644), (190, 760), (282, 796), (336, 728)]
Cs = catmull(ctrl, 20)
rib = resample(Cs, 240)
# wind ribbon (filled, tapering) + two thin wind lines
wprof = [5 + 30 * math.sin(math.pi * min(1, i / 239 * 1.05)) ** 1.3 for i in range(240)]
cen = [q[0] for q in rib]
Lr, Rr = offset_line(cen, wprof, +1), offset_line(cen, wprof, -1)
out.append(f'<polygon points="{pts(Lr + Rr[::-1])}" fill="#E9B850" opacity=".20"/>')
for side, o, op in ((1, 46, .55), (-1, 40, .45)):
    seg = offset_line(cen, [o * math.sin(math.pi * i / 239) for i in range(240)], side)
    a0, a1 = (40, 170) if side > 0 else (70, 200)
    pline(seg[a0:a1], '#FFF6E0', 1.8, f'opacity="{op}"')
S = resample(Cs, 26)
for i, (p, tg) in enumerate(S):
    t = i / 25
    size = 20 + 26 * t
    off = mul(perp(tg), rnd.uniform(-14, 14) * (0.5 + t))
    ang = math.atan2(tg[1], tg[0]) + math.pi / 2 + rnd.uniform(-0.9, 0.9)
    kind = 'm' if (i % 3 == 1) else ('g' if i % 2 else 'f')
    leaf(kind, plus(p, off), size, ang)
# burst at the broom head (vortex start) + small flecks along the trail
for i in range(22):
    a = rnd.uniform(-2.9, -1.2)
    rr = rnd.uniform(40, 150)
    q = (930 + math.cos(a) * rr * 0.8, 1520 + math.sin(a) * rr * 0.7)
    leaf(rnd.choice('ggfm'), q, rnd.uniform(14, 26), rnd.uniform(0, 6.3))
for i, (p, tg) in enumerate(resample(Cs, 70)):
    if i % 2:
        continue
    q = plus(p, mul(perp(tg), rnd.uniform(-40, 40)))
    leaf('g', q, rnd.uniform(8, 13), rnd.uniform(0, 6.3))
out += B_buf
for k, (p, s) in enumerate([((924, 1096), 22), ((966, 1072), 18), ((1004, 1062), 14)]):
    leaf('g' if k != 1 else 'm', p, s, 0.6 + k * 0.7)

# ---------------------------------------------------------------- drifting leaves + motes
for i in range(16):
    leaf(rnd.choice('gfm'), (rnd.uniform(0, 1080), rnd.uniform(300, 1400)), rnd.uniform(9, 15), rnd.uniform(0, 6.3), rnd.uniform(0.5, 1), op=0.8)
out.append('<g fill="#FFF6DC">')
for i in range(110):
    a, b, c = rnd.choice(sh)
    u, v = rnd.random(), rnd.random()
    if u + v > 1: u, v = 1 - u, 1 - v
    p = (a[0] + u * (b[0] - a[0]) + v * (c[0] - a[0]), a[1] + u * (b[1] - a[1]) + v * (c[1] - a[1]))
    if 0 < p[0] < 1080 and 260 < p[1] < 1700:
        out.append(f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="{f(rnd.uniform(1, 2.6))}" opacity="{f(rnd.uniform(0.3, 0.8))}"/>')
out.append('</g>')

# ---------------------------------------------------------------- 11 near maple branch, top-right
brc = catmull([(1110, 236), (990, 276), (880, 322), (770, 362), (650, 376)], 6)
for i in range(len(brc) - 1):
    t = i / (len(brc) - 1)
    strip(brc[i], brc[i + 1], 26 - 18 * t, 26 - 18 * (t + 1 / len(brc)), BARK, ridge=False, curl=False)
twigs = [((880, 322), (836, 450)), ((990, 276), (1010, 410)), ((770, 362), (712, 460)), ((930, 300), (986, 236)), ((700, 372), (640, 436))]
for a, b in twigs:
    m = lerp(a, b, 0.5); m = plus(m, (8, 0))
    tw = catmull([a, m, b], 5)
    for i in range(len(tw) - 1):
        strip(tw[i], tw[i + 1], 7 - 4 * i / len(tw), 7 - 4 * (i + 1) / len(tw), BARK, ridge=False, curl=False)
spots = []
for a, b in twigs:
    for u in (0.55, 0.8, 1.0):
        spots.append(lerp(a, b, u))
for i in range(len(brc)):
    if i % 3 == 0:
        spots.append(plus(brc[i], (rnd.uniform(-20, 20), rnd.uniform(10, 40))))
for p in spots:
    for k in range(2):
        q = plus(p, (rnd.uniform(-26, 26), rnd.uniform(-8, 30)))
        two_tone(MAPLE_R, q, rnd.uniform(48, 70), rnd.uniform(-0.5, 0.5), RUST, stem=(0.13, 0.36))

# big near leaves (closer to camera, slightly darker: out of the sunlit air)
two_tone(MAPLE_R, (54, 1010), 78, 0.5, ('#9C3D25', '#86331F', '#6A2818'), stem=(0.13, 0.36))
two_tone(GINKGO_R, (1028, 1180), 70, -0.7, ('#D2A236', '#BE922E', '#A37B25'), stem=(0.3, 0.5))

# ---------------------------------------------------------------- 13 texture
out.append('<rect width="1080" height="1920" fill="url(#vig)" style="mix-blend-mode:multiply"/>')
out.append('<rect width="1080" height="1920" filter="url(#fibre)" opacity=".07" style="mix-blend-mode:multiply"/>')
out.append('<rect width="1080" height="1920" filter="url(#grain)" opacity=".05"/>')

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
       f'<defs>{defs}</defs>' + '\n'.join(out) + '</svg>')
open(OUT, 'w').write(svg)
print('wrote', OUT, len(svg) // 1024, 'KB', 'crown tris', n1, n2)
