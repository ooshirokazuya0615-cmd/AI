"""3 A.M. NOIR PRINT - BRIMFUL still.

Builds two grayscale density plates as SVG (K = black ink, T = teal spot ink),
embeds them in still.html, and screens them in-browser (canvas) into an AM halftone
two-ink silkscreen print on bone paper.
Usage: python3 make.py [out.html]  ->  render with render_wait.js
"""
import base64, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from pose2d import POSE, GROUND_Y  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'still.html')
W, H = 1080, 1920

# ------------------------------------------------------------------ parameters
P = dict(
    seed=11,
    cell=7, ang=45, ang_t=75,
    paper=[232, 225, 208], black=[17, 17, 17], teal=[30, 140, 140],
    tooth=0.06, grain=0.04, mesh=0.04, spread_thr=0.5, spread_jit=0.16,
    shade_o=0.7,
    # light bands (vertical surfaces): 8 bands, 44 wide, 36 gap, descending 24 deg
    band_ang=24, band_w=44, band_gap=36, n_bands=8,
    hero_c=287,      # n-offset of hero band 0 (cup sits in band 1)
    sconce=(992, 420), ceil=0.78, haze=0.18,
    hero_nb=11, wall_lit=0.5, apron_sh=0.42, face_lit=0.6,
    shaft_ang=52, shafts=[(430, 50, 0.22), (560, 64, 0.26), (700, 44, 0.2), (830, 60, 0.24), (960, 40, 0.18)], motes=60, motes2=26,
    wall_c=167,      # wall bands (half-period offset from hero -> stripe break at silhouette)
    figA_c=267, figB_c=307, figC_c=267,
    vp=(540, 980), floor_top=1320, ground=GROUND_Y,
    misreg=(3, 2),
)
P['ground'] = GROUND_Y

D2R = math.pi / 180


def g(D):
    v = round(255 * (1 - max(0.0, min(1.0, D))))
    return '#%02x%02x%02x' % (v, v, v)


def sh(D, o=None):
    o = P['shade_o'] if o is None else o
    return 1 - (1 - D) * (1 - o)


def V(m, lit, shade=None, o=None):
    """value for mode m ('lit'|'shade'|'sil')"""
    if m == 'sil':
        return '#000'
    if m == 'lit':
        return g(lit)
    return g(shade if shade is not None else sh(lit, o))


def pts(ps):
    return ' '.join(f'{x:.1f},{y:.1f}' for x, y in ps)


def poly(ps, fill, extra=''):
    return f'<polygon points="{pts(ps)}" fill="{fill}" {extra}/>'


def pth(d, fill, extra=''):
    return f'<path d="{d}" fill="{fill}" {extra}/>'


def ln(a, b, stroke, w, extra=''):
    return (f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
            f'stroke="{stroke}" stroke-width="{w}" {extra}/>')


def pl(ps, stroke, w, extra=''):
    return f'<polyline points="{pts(ps)}" fill="none" stroke="{stroke}" stroke-width="{w}" {extra}/>'


def ell(cx, cy, rx, ry, fill, extra=''):
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" {extra}/>'


def rect(x, y, w, h, fill, extra=''):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" {extra}/>'


def circ(cx, cy, r, fill, extra=''):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" {extra}/>'


# ------------------------------------------------------------------ light bands
def band_dirs(ang):
    a = ang * D2R
    d = (math.cos(a), math.sin(a))
    n = (-math.sin(a), math.cos(a))
    return d, n


def band_polys(c, ang=None, w=None, gap=None, nb=None, t0=-2200, t1=2600):
    ang = P['band_ang'] if ang is None else ang
    w = P['band_w'] if w is None else w
    gap = P['band_gap'] if gap is None else gap
    nb = P['n_bands'] if nb is None else nb
    d, n = band_dirs(ang)
    out = []
    for k in range(nb):
        a = c + (w + gap) * k
        b = a + w
        q = [(a * n[0] + t0 * d[0], a * n[1] + t0 * d[1]), (a * n[0] + t1 * d[0], a * n[1] + t1 * d[1]),
             (b * n[0] + t1 * d[0], b * n[1] + t1 * d[1]), (b * n[0] + t0 * d[0], b * n[1] + t0 * d[1])]
        out.append(q)
    return out


def floor_band_polys():
    """8 floor bands, perspective: uniform spacing in floor depth, lines through a far-left VP."""
    vx, vy = -1700, P['vp'][1]
    out = []
    z0, w, per = 0.965, 0.075, 0.137
    for k in range(8):
        za = z0 + per * k
        zb = za + w
        ya = vy + 580 / zb  # far edge (higher on screen)
        yb = vy + 580 / za
        def at(yc, x):
            return vy + (yc - vy) * (x - vx) / (540 - vx)
        q = [(-50, at(ya, -50)), (1130, at(ya, 1130)), (1130, at(yb, 1130)), (-50, at(yb, -50))]
        out.append(q)
    return out


# ------------------------------------------------------------------ scene pieces
def wall(m):
    s = []
    s.append(rect(0, 0, W, P['floor_top'], V(m, P['wall_lit'], 0.86)))
    # deco reeded panel lines (bone hairline + black shadow line)
    for x in range(340, W, 120):
        s.append(rect(x, 178, 2, 1002, V(m, 0.0, 0.66)))
        s.append(rect(x + 5, 178, 3, 1002, V(m, 0.75, 1.0)))
    # stepped deco cornice + ceiling
    s.append(rect(0, 0, W, 150, 'url(#ceilG)'))
    for y, hgt, val in [(150, 4, 0.0), (156, 8, 1.0), (166, 3, 0.0), (171, 7, 1.0)]:
        s.append(rect(0, y, W, hgt, V(m, val, 0.75 if val == 0 else 1.0)))
    # dado / wainscot
    s.append(rect(0, 1180, W, 140, V(m, 0.62, 0.97)))
    s.append(rect(0, 1180, W, 4, V(m, 0.0, 0.6)))
    s.append(rect(0, 1186, W, 6, V(m, 1.0, 1.0)))
    for x in range(296, W, 28):
        s.append(rect(x, 1196, 3, 118, V(m, 1.0, 1.0)))
    s.append(rect(0, 1312, W, 8, V(m, 1.0, 1.0)))
    return ''.join(s)


def fan_shape(cx, cy, sc, rot, squash, fill):
    """4 blades + hub, in the fan plane, squashed vertically."""
    blades = []
    for i in range(4):
        a = rot + i * 90
        blades.append(f'<g transform="rotate({a:.1f})"><path d="M 18,-11 C 70,-26 190,-30 228,-14 '
                      f'C 240,-6 240,8 228,14 C 190,26 70,22 18,11 Z" fill="{fill}"/></g>')
    return (f'<g transform="translate({cx},{cy}) scale({sc},{sc * squash})">' + ''.join(blades) +
            f'<circle r="30" fill="{fill}"/></g>')


def fan_shadow(m):
    return fan_shape(540, 470, 1.75, 15 + 30, 0.5, V(m, 0.9, 0.9))


def fan():
    s = [rect(555, 0, 10, 80, '#000')]
    s.append(fan_shape(560, 92, 1.0, 22, 0.16, '#000'))
    s.append(ell(560, 96, 34, 15, '#000'))
    s.append(ell(560, 108, 16, 9, '#000'))
    s.append(f'<path d="M 527,92 Q 560,80 593,92" fill="none" stroke="#fff" stroke-width="2" opacity="0.6"/>')
    return ''.join(s)


def window_svg():
    s = [rect(0, 160, 280, 960, '#000')]
    x0, x1, y0, y1 = 0, 262, 178, 1102
    n = 26
    pitch = (y1 - y0) / n
    for i in range(n):
        y = y0 + i * pitch
        hgt = pitch - 8
        s.append(rect(x0, y, x1 - x0, hgt, 'url(#slatGlow)'))
        s.append(rect(x0, y + hgt - 6, x1 - x0, 6, 'url(#slatGlowLo)'))
    # ladder cords
    for x in (70, 190):
        s.append(rect(x, y0, 3, y1 - y0, '#000', 'opacity="0.85"'))
    # frame
    s.append(rect(262, 160, 22, 960, '#000'))
    s.append(rect(0, 160, 284, 18, '#000'))
    s.append(rect(0, 1102, 300, 24, '#000'))
    s.append(rect(0, 1100, 300, 3, '#fff'))
    return ''.join(s)


def sconce(m):
    cx, cy = P['sconce']
    blk = V(m, 1, 1)
    s = []
    # stepped skyscraper backplate
    s.append(rect(cx - 9, cy - 6, 18, 150, blk))
    s.append(rect(cx - 16, cy + 30, 32, 92, blk))
    s.append(rect(cx - 24, cy + 60, 48, 44, blk))
    s.append(rect(cx - 9, cy + 30, 2, 92, V(m, 0.0, 0.5)))
    # frosted glass fan shade opening upward
    s.append(pth(f'M {cx-70},{cy-58} A 70,58 0 0 0 {cx+70},{cy-58} Z', V(m, 0.2, 0.52)))
    for a in (-56, -28, 0, 28, 56):
        x2 = cx + 70 * math.sin(a * D2R)
        y2 = cy - 58 + 58 * math.cos(a * D2R)
        s.append(ln((cx, cy - 2), (x2, y2), blk, 3))
    s.append(rect(cx - 74, cy - 62, 148, 7, blk))
    s.append(rect(cx - 74, cy - 62, 148, 2, V(m, 0.0, 0.4)))
    s.append(ell(cx, cy - 2, 12, 6, blk))
    return ''.join(s)


def bottle(x, base, kind, m, glint=True):
    s = []
    if kind == 0:   # wine
        hgt, bw, nw, sh_ = 132, 30, 10, 62
    elif kind == 1:  # whisky square
        hgt, bw, nw, sh_ = 104, 40, 13, 30
    elif kind == 2:  # liqueur round
        hgt, bw, nw, sh_ = 96, 44, 11, 48
    else:            # tall slim
        hgt, bw, nw, sh_ = 150, 24, 9, 80
    top = base - hgt
    shy = top + (hgt - sh_) * 0.42
    d = (f'M {x-bw/2},{base} L {x-bw/2},{shy+sh_*0.35} C {x-bw/2},{shy} {x-nw/2},{shy+4} {x-nw/2},{shy-10} '
         f'L {x-nw/2},{top+6} L {x-nw/2-2},{top} L {x+nw/2+2},{top} L {x+nw/2},{top+6} L {x+nw/2},{shy-10} '
         f'C {x+nw/2},{shy+4} {x+bw/2},{shy} {x+bw/2},{shy+sh_*0.35} L {x+bw/2},{base} Z')
    if kind == 2:
        d = (f'M {x-bw/2+4},{base} C {x-bw/2-4},{base-40} {x-bw/2},{top+44} {x-nw/2},{top+30} L {x-nw/2},{top} '
             f'L {x+nw/2},{top} L {x+nw/2},{top+30} C {x+bw/2},{top+44} {x+bw/2+4},{base-40} {x+bw/2-4},{base} Z')
    s.append(pth(d, V(m, 1, 1)))
    if glint:
        gx = x - bw / 2 + 6
        s.append(rect(gx, shy + 12, 3, max(10, (base - shy) * 0.45), V(m, 0.0, 0.55)))
        s.append(rect(x - nw / 2 + 2, top + 10, 2, 12, V(m, 0.0, 0.6)))
    return ''.join(s)


def bar(m):
    s = []
    # back-bar shelf with bottles (quiet: silhouettes + a few glints)
    s.append(rect(560, 1060, 520, 20, V(m, 1, 1)))
    kinds = [0, 1, 3, 2, 0, 3, 1, 0, 2, 3]
    x = 612
    for i, k in enumerate(kinds):
        s.append(bottle(x, 1062, k, m, glint=(i % 2 == 0)))
        x += [44, 52, 40, 56][k] + 6
    # counter top
    s.append(rect(560, 1080, 520, 26, V(m, 1, 1)))
    s.append(rect(560, 1080, 520, 3, V(m, 0.0, 0.4)))
    # counter front: fluted panel
    s.append(rect(572, 1106, 508, 214, V(m, 0.55, 0.95)))
    for xx in (700, 860, 1020):
        s.append(rect(xx, 1112, 5, 166, V(m, 1, 1)))
    s.append(rect(572, 1196, 508, 4, V(m, 1, 1)))
    s.append(rect(572, 1106, 508, 8, V(m, 1, 1)))
    s.append(rect(572, 1278, 508, 10, V(m, 1, 1)))
    s.append(rect(572, 1278, 508, 2, V(m, 0.0, 0.6)))
    return ''.join(s)


def floor_tiles():
    vx, vy = P['vp']
    F = 1000.0
    s_t = 120.0 / 580.0
    rows = []
    j = 4
    while True:
        y = vy + F / (s_t * j)
        rows.append((j, y))
        if y < P['floor_top']:
            break
        j += 1
    out = []
    for (ja, ya), (jb, yb) in zip(rows[:-1], rows[1:]):
        # ya lower on screen (nearer), yb higher
        for i in range(-30, 31):
            if (i + ja) % 2:
                continue
            def X(ii, yy):
                return vx + s_t * (ii + 0.5) * (yy - vy)
            ybc = max(yb, P['floor_top'])
            q = [(X(i, ya), ya), (X(i + 1, ya), ya), (X(i + 1, ybc), ybc), (X(i, ybc), ybc)]
            if max(p[0] for p in q) < -20 or min(p[0] for p in q) > W + 20:
                continue
            out.append(q)
    return out


TILES = floor_tiles()


def floor(m):
    s = [rect(0, P['floor_top'], W, H - P['floor_top'], 'url(#floorShade)' if m == 'shade' else g(0.0))]
    for q in TILES:
        s.append(poly(q, g(1.0)))
    return ''.join(s)


# ------------------------------------------------------------------ hero BRIM
HX = dict(head=(556, 630), hat=(556, 582))


def hero(m, rim=True):
    s = []
    blk = V(m, 1, 1)
    # rear arm behind the back (drawn before torso)
    s.append(pl([(514, 764), (478, 872), (528, 968)], blk, 14,
                'stroke-linejoin="miter" stroke-linecap="round"'))
    # legs (16px rods) + shoes
    s.append(ln((678, 1420), (700, 1548), blk, 16))
    s.append(ln((426, 1420), (404, 1540), blk, 16))
    s.append(poly([(690, 1538), (712, 1536), (746, 1552), (748, 1561), (688, 1561)], blk))  # lead heel-strike
    s.append(poly([(392, 1534), (414, 1530), (440, 1550), (444, 1560), (404, 1560), (388, 1548)], blk))
    # neck
    s.append(ln((556, 670), (556, 752), blk, 13))
    # vest trapezoid
    s.append(pth('M 506,748 L 606,748 Q 612,749 612,756 L 592,990 L 500,990 L 500,756 Q 500,749 506,748 Z', blk))
    # shirt V + bow tie
    s.append(poly([(540, 748), (574, 748), (557, 806)], V(m, 0.0, 0.5)))
    s.append(poly([(544, 752), (557, 758), (544, 765)], blk))
    s.append(poly([(570, 752), (557, 758), (570, 765)], blk))
    s.append(circ(557, 758, 3.5, blk))
    # lead arm (in front of torso)
    s.append(pl([(602, 760), (636, 856), (752, 806)], blk, 14, 'stroke-linejoin="miter" stroke-miterlimit="6"'))
    # apron
    ap = 'M 490,990 L 600,990 C 624,1140 652,1320 688,1446 Q 550,1458 412,1446 C 446,1320 474,1140 490,990 Z'
    s.append(pth(ap, V(m, 0.0, P['apron_sh'])))
    # apron folds
    s.append(pth('M 560,1000 C 575,1150 600,1300 628,1450 L 612,1451 C 588,1300 566,1150 552,1000 Z', V(m, 0.3, 0.7)))
    s.append(pth('M 512,1060 C 504,1200 486,1330 470,1450 L 462,1449 C 478,1330 496,1200 506,1060 Z', V(m, 0.42, 0.75)))
    s.append(pth('M 600,996 C 628,1160 656,1330 688,1446 L 676,1447 C 646,1330 618,1160 592,996 Z', V(m, 0.45, 0.8)))
    # waist band + apron string bow behind
    s.append(rect(488, 986, 114, 8, blk))
    # head + hat
    hx, hy = HX['head']
    s.append(ell(hx, hy, 38, 48, blk))
    if m == 'lit':
        # band light on the face (lower half only - hat brim shades the top)
        s.append(f'<g clip-path="url(#cpHeadLow)">{ell(hx, hy, 38, 48, g(P["face_lit"]))}</g>')
    tx, ty = HX['hat']
    s.append(f'<g transform="rotate(-4 {tx} {ty})">{ell(tx, ty, 112, 18, blk)}'
             f'{ell(tx + 6, ty - 10, 44, 12, blk)}</g>')
    return ''.join(s)


def hero_rim():
    """continuous rim light on the window-side edges (drawn after shading)."""
    s = []
    s.append('<path d="M 501.5,760 L 501.5,986" fill="none" stroke="#fff" stroke-width="3"/>')
    s.append('<path d="M 521,640 Q 520,660 532,672" fill="none" stroke="#fff" stroke-width="2.5"/>')
    s.append('<path d="M 474,868 L 510,768" fill="none" stroke="#fff" stroke-width="2.2"/>')
    s.append('<path d="M 476,878 L 520,958" fill="none" stroke="#fff" stroke-width="2"/>')
    s.append('<path d="M 418.5,1432 L 397.5,1538" fill="none" stroke="#fff" stroke-width="2"/>')
    s.append('<path d="M 671.5,1440 L 692,1540" fill="none" stroke="#fff" stroke-width="2"/>')
    s.append('<path d="M 600,762 L 631,850" fill="none" stroke="#fff" stroke-width="2"/>')
    return ''.join(s)


def hero_sil():
    """flat silhouette for masks / shadows"""
    return hero('sil', rim=False)


# ------------------------------------------------------------------ cup (K-plate part) and teal plate
CUP_BODY = 'M 734,738 C 736,770 748,793 760,797 L 788,797 C 800,793 812,770 814,738 Z'


def cup_k(m):
    """K-plate view of cup + saucer: knockout + shading. Drawn after hero, inside hero layer."""
    s = []
    s.append(f'<path d="M 813,744 C 838,738 840,770 806,778" fill="none" stroke="{V(m, 0.0)}" stroke-width="7"/>')
    s.append(ell(774, 800, 78, 14, V(m, 0.0)))
    s.append(pth('M 696,800 Q 774,830 852,800 Q 774,818 696,800 Z', V(m, 0.55, 0.85)))  # saucer underside
    # thumb over rim + hand hidden under saucer
    s.append(pth(CUP_BODY, V(m, 0.0)))
    s.append(ell(774, 738, 40, 10, V(m, 0.0)))
    s.append(pth('M 798,742 C 806,760 800,786 786,797 L 790,797 C 802,792 812,770 814,738 Z', V(m, 0.5, 0.85)))
    s.append(ell(774, 738.5, 37.5, 8.6, g(1.0)))  # tea surface
    s.append(poly([(726, 793), (740, 790), (746, 797), (730, 801)], g(1.0)))  # thumb on saucer rim
    return ''.join(s)


def cup_hi():
    """bone highlights painted after shading (meniscus, steam)."""
    s = []
    s.append(f'<path d="M 739,740 Q 774,750 809,740" fill="none" stroke="#fff" stroke-width="2.2"/>')
    s.append(f'<path d="M 748,735 Q 762,731 772,731" fill="none" stroke="#fff" stroke-width="1.6" opacity="0.8"/>')
    steam = [('M 758,722 C 746,700 772,686 760,662 C 750,642 766,630 758,610 C 752,596 760,586 756,576', 3.0),
             ('M 776,718 C 788,694 764,678 778,650 C 788,630 772,614 780,590 C 786,572 778,560 782,548', 3.4),
             ('M 794,722 C 806,704 788,692 798,672 C 806,658 796,648 800,634', 2.6)]
    for d, w in steam:
        s.append(f'<path d="{d}" fill="none" stroke="#fff" stroke-width="{w}" stroke-linecap="round"/>')
    return ''.join(s)


def cup_t():
    s = ['<g transform="translate(%d,%d)">' % P['misreg']]
    s.append('<path d="M 813,744 C 838,738 840,770 806,778" fill="none" stroke="#000" stroke-width="7"/>')
    s.append(ell(774, 800, 78, 14, '#000'))
    s.append(pth(CUP_BODY, '#000'))
    s.append(ell(774, 738, 40, 10, '#000'))
    # knock the meniscus out of the teal too
    s.append('<path d="M 739,740 Q 774,750 809,740" fill="none" stroke="#fff" stroke-width="2.2"/>')
    s.append('</g>')
    return ''.join(s)


# ------------------------------------------------------------------ dress forms
def form_xf(bx, by, s, tilt):
    a = tilt * D2R
    ca, sa = math.cos(a), math.sin(a)
    def f(x, y):
        x, y = x * s, y * s
        return (bx + x * ca - y * sa, by + x * sa + y * ca)
    return f


def torso_path(T):
    return (f'M -26,{T} C -40,{T+2} -70,{T+14} -75,{T+40} C -79,{T+60} -78,{T+80} -72,{T+100} '
            f'C -64,{T+125} -45,{T+145} -45,{T+170} C -45,{T+200} -72,{T+225} -70,{T+255} '
            f'C -69,{T+280} -66,{T+292} -62,{T+300} Q 0,{T+318} 62,{T+300} '
            f'C 66,{T+292} 69,{T+280} 70,{T+255} C 72,{T+225} 45,{T+200} 45,{T+170} '
            f'C 45,{T+145} 64,{T+125} 72,{T+100} C 78,{T+80} 79,{T+60} 75,{T+40} '
            f'C 70,{T+14} 40,{T+2} 26,{T} Z')


def dress_form(m, uid, bx, by, s, tilt, pole, arms, vals, stand=(1, 1), core=1.0, dowel=1.0):
    """arms: list of (shoulder_side, elbow_world, tip_world); vals: (torso_lit, torso_shade)"""
    T = -(pole + 300)
    xf = form_xf(bx, by, s, tilt)
    blk = V(m, 1, 1)
    stv = V(m, stand[0], stand[1])
    tl, ts = vals
    o = []
    o.append(f'<g transform="translate({bx},{by}) rotate({tilt}) scale({s})">')
    blk_t = blk
    blk = stv
    # tripod
    hub = -78
    for fx, fy in [(-92, -10), (84, -14), (22, 12)]:
        o.append(ln((0, hub), (fx, fy), blk, 9, 'stroke-linecap="round"'))
        o.append(circ(fx, fy, 6, blk))
    o.append(ell(0, hub, 14, 7, blk))
    o.append(rect(-6, -pole - 4, 12, pole + hub * -1 - 70, blk))
    o.append(rect(-11, -pole * 0.55, 22, 18, blk))
    blk = blk_t
    # torso
    o.append(f'<clipPath id="cpT{uid}{m}"><path d="{torso_path(T)}"/></clipPath>')
    o.append(pth(torso_path(T), V(m, tl, ts)))
    o.append(f'<g clip-path="url(#cpT{uid}{m})">'
             f'{ell(84 + 30 * (1 - core), T+170, 62 * core, 210, V(m, min(1, tl + 0.3), min(1, ts + 0.12)))}'
             f'{ell(-96, T+150, 40, 200, V(m, max(0, tl - 0.25), max(0, ts - 0.12)))}</g>')
    # waist tape + centre seam
    o.append(f'<path d="M -45,{T+170} Q 2,{T+182} 45,{T+170}" fill="none" stroke="{V(m, 0.0, 0.55)}" stroke-width="2.5"/>')
    o.append(f'<path d="M 6,{T+6} Q 16,{T+150} 8,{T+306}" fill="none" stroke="{V(m, 0.0, 0.55)}" stroke-width="2.5"/>')
    o.append(f'<path d="M -26,{T} Q 0,{T+8} 26,{T}" fill="none" stroke="{blk}" stroke-width="4"/>')
    # neck cap + knob
    o.append(rect(-17, T - 26, 34, 28, stv))
    o.append(ell(0, T - 26, 24, 7, stv))
    o.append(circ(0, T - 40, 9, stv))
    o.append('</g>')
    # dowel arms (world coords)
    for side, el, tip in arms:
        shp = xf(68 * side, T + 42)
        w = 10 * s * dowel
        o.append(pl([shp, el, tip], blk, w, 'stroke-linejoin="round" stroke-linecap="round"'))
        for p_ in (shp, el, tip):
            o.append(circ(p_[0], p_[1], 9 * s * dowel, blk))
    return ''.join(o)


def form_rim(uid, rim=True, pole_rim=True):
    """rim light on the window side of torso + dowel highlights, drawn after shading."""
    f = FORMS[uid]
    bx, by, s, tilt, pole = f['bx'], f['by'], f['s'], f['tilt'], f['pole']
    T = -(pole + 300)
    xf = form_xf(bx, by, s, tilt)
    o = []
    if rim:
        o.append(f'<g transform="translate({bx},{by}) rotate({tilt}) scale({s})">'
                 f'<clipPath id="cpR{uid}"><path d="{torso_path(T)}"/></clipPath>'
                 f'<clipPath id="cpRL{uid}"><rect x="-200" y="{T-10}" width="197" height="285"/></clipPath>'
                 f'<g clip-path="url(#cpR{uid})"><g clip-path="url(#cpRL{uid})"><path d="{torso_path(T)}" fill="none" '
                 f'stroke="#fff" stroke-width="{7/s:.1f}"/></g></g>'
                 f'<circle cx="-3" cy="{T-43}" r="3" fill="#fff"/>'
                 f'<line x1="-14" y1="{T-22}" x2="-14" y2="{T-4}" stroke="#fff" stroke-width="{2.2/s:.1f}"/>'
                 + (f'<line x1="-5" y1="{-pole+4}" x2="-5" y2="-86" stroke="#fff" stroke-width="{2.0/s:.1f}"/>'
                    f'<line x1="-6" y1="-80" x2="-88" y2="-14" stroke="#fff" stroke-width="{1.8/s:.1f}" opacity="0.8"/>'
                    if pole_rim else '') + '</g>')
    for side, el, tip in f['arms']:
        shp = xf(68 * side, T + 42)
        for a, b in ((shp, el), (el, tip)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy)
            nx, ny = dy / L, -dx / L
            if nx > 0:
                nx, ny = -nx, -ny
            dw = f.get('dowel', 1.0)
            off = 3.2 * s * dw
            o.append(ln((a[0] + nx * off + dx / L * 9 * s * dw, a[1] + ny * off + dy / L * 9 * s * dw),
                        (b[0] + nx * off - dx / L * 9 * s * dw, b[1] + ny * off - dy / L * 9 * s * dw), '#fff', 1.8 * dw))
        for p_ in (el, tip):
            o.append(circ(p_[0] - 3 * s * f.get('dowel', 1.0), p_[1] - 3 * s * f.get('dowel', 1.0), 2.4 * s, '#fff'))
    return ''.join(o)


FORMS = dict(
    B=dict(bx=172, by=1432, s=0.78, tilt=3, pole=430, vals=(0.85, 0.96),
           arms=[(-1, (70, 1000), (40, 1090)), (1, (300, 980), (380, 940))]),
    C=dict(bx=846, by=1446, s=0.62, tilt=-11, pole=220, vals=(0.04, 0.36), stand=(0.45, 0.72), core=0.45,
           arms=[(-1, (676, 1196), (650, 1250)), (1, (842, 1150), (884, 1128))]),
    A=dict(bx=1090, by=1668, s=1.1, tilt=-6, pole=600, vals=(0.8, 0.95),
           arms=[(-1, (928, 634), (872, 794)), (1, (1104, 840), (1118, 980))], dowel=1.55),
)


def form(m, k):
    f = FORMS[k]
    return dress_form(m, k, f['bx'], f['by'], f['s'], f['tilt'], f['pole'], f['arms'], f['vals'], f.get('stand', (1, 1)), f.get('core', 1.0), f.get('dowel', 1.0))


def motion_arcs_C():
    f = FORMS['C']
    bx, by, s, tilt = f['bx'], f['by'], f['s'], f['tilt']
    out = []
    base_a = -90 + tilt
    for i, r in enumerate([0.70, 0.86, 1.04]):
        rr = r * (f['pole'] + 300) * s
        a0, a1 = base_a + 16, base_a + 34 - i * 3
        p0 = (bx + rr * math.cos(a0 * D2R), by + rr * math.sin(a0 * D2R))
        p1 = (bx + rr * math.cos(a1 * D2R), by + rr * math.sin(a1 * D2R))
        out.append(f'<path d="M {p0[0]:.1f},{p0[1]:.1f} A {rr:.1f},{rr:.1f} 0 0 1 {p1[0]:.1f},{p1[1]:.1f}" '
                   f'fill="none" stroke="#fff" stroke-width="{3.6 - i*0.5:.1f}" stroke-linecap="round"/>')
    return ''.join(out)


# ------------------------------------------------------------------ assemble K plate
def layer(fn, mask):
    return fn('shade') + f'<g mask="url(#{mask})">' + fn('lit') + '</g>'


def band_mask(mid, c, clip=None, fall='fallW', nb=None, soft='soft'):
    polys = band_polys(c, nb=nb)
    inner = ''.join(poly(q, f'url(#{fall})') for q in polys)
    cl = f' clip-path="url(#{clip})"' if clip else ''
    return (f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
            f'<g filter="url(#{soft})"{cl}>{inner}</g></mask>')


def build_k():
    defs = []
    defs.append('<filter id="soft" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">'
                '<feGaussianBlur stdDeviation="1.3"/></filter>')
    defs.append('<filter id="softW" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">'
                '<feGaussianBlur stdDeviation="3.2"/></filter>')
    defs.append('<radialGradient id="ceilG" gradientUnits="userSpaceOnUse" cx="560" cy="80" r="560" '
                'gradientTransform="translate(560 80) scale(1 0.5) translate(-560 -80)">'
                f'<stop offset="0" stop-color="{g(0.66)}"/><stop offset="0.6" stop-color="{g(0.8)}"/>'
                f'<stop offset="1" stop-color="{g(0.93)}"/></radialGradient>')
    defs.append('<filter id="blur3" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="sRGB">'
                '<feGaussianBlur stdDeviation="3"/></filter>')
    defs.append('<filter id="blur8" x="-20%" y="-20%" width="140%" height="140%" color-interpolation-filters="sRGB">'
                '<feGaussianBlur stdDeviation="8"/></filter>')
    defs.append('<filter id="hazeBig" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">'
                '<feGaussianBlur stdDeviation="90"/></filter>')
    defs.append('<filter id="haze" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">'
                '<feGaussianBlur stdDeviation="22"/></filter>')
    # falloff of street light (mask luminance)
    defs.append('<radialGradient id="fallW" gradientUnits="userSpaceOnUse" cx="470" cy="720" r="820">'
                '<stop offset="0" stop-color="#fff"/><stop offset="0.4" stop-color="#f0f0f0"/>'
                '<stop offset="0.8" stop-color="#909090"/><stop offset="1" stop-color="#505050"/></radialGradient>')
    defs.append('<radialGradient id="fallH" gradientUnits="userSpaceOnUse" cx="420" cy="760" r="1100">'
                '<stop offset="0" stop-color="#fff"/><stop offset="0.6" stop-color="#fff"/>'
                '<stop offset="1" stop-color="#c8c8c8"/></radialGradient>')
    defs.append('<radialGradient id="fallF" gradientUnits="userSpaceOnUse" cx="420" cy="1500" r="560" gradientTransform="translate(420 1500) scale(1.25 0.8) translate(-420 -1500)">'
                '<stop offset="0" stop-color="#fff"/><stop offset="0.5" stop-color="#e0e0e0"/>'
                '<stop offset="1" stop-color="#000"/></radialGradient>')
    # slat glow in the window (paint, not mask): density low near the street lamp
    defs.append('<radialGradient id="slatGlow" gradientUnits="userSpaceOnUse" cx="120" cy="840" r="760">'
                f'<stop offset="0" stop-color="{g(0.0)}"/><stop offset="0.28" stop-color="{g(0.08)}"/>'
                f'<stop offset="0.62" stop-color="{g(0.46)}"/><stop offset="1" stop-color="{g(0.74)}"/></radialGradient>')
    defs.append('<radialGradient id="slatGlowLo" gradientUnits="userSpaceOnUse" cx="120" cy="840" r="760">'
                f'<stop offset="0" stop-color="{g(0.35)}"/><stop offset="1" stop-color="{g(0.85)}"/></radialGradient>')
    defs.append('<linearGradient id="floorShade" gradientUnits="userSpaceOnUse" x1="0" y1="1320" x2="0" y2="1920">'
                f'<stop offset="0" stop-color="{g(0.84)}"/><stop offset="0.4" stop-color="{g(0.86)}"/>'
                f'<stop offset="1" stop-color="{g(0.97)}"/></linearGradient>')
    defs.append('<linearGradient id="reflFade" gradientUnits="userSpaceOnUse" x1="0" y1="1560" x2="0" y2="1800">'
                '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>')
    defs.append('<clipPath id="cpWallLit"><rect x="284" y="178" width="796" height="1142"/></clipPath>')
    defs.append(f'<clipPath id="cpHeadLow"><rect x="500" y="{HX["head"][1] + 8}" width="120" height="60"/></clipPath>')
    defs.append(f'<clipPath id="cpFloor"><rect x="0" y="{P["floor_top"]}" width="{W}" height="{H - P["floor_top"]}"/></clipPath>')
    # masks
    defs.append(band_mask('mWall', P['wall_c'], clip='cpWallLit', fall='fallW', soft='softW'))
    defs.append(band_mask('mHero', P['hero_c'], fall='fallH', nb=P['hero_nb']))
    defs.append(band_mask('mA', P['figA_c'], fall='fallW'))
    defs.append(band_mask('mB', P['figB_c'], fall='fallH'))
    defs.append(band_mask('mC', P['figC_c'], fall='fallW'))
    fb = ''.join(poly(q, 'url(#fallF)') for q in floor_band_polys())
    # hero cast shadow on floor (blocks the floor bands)
    shadow = (f'<g transform="matrix(1,0,-0.62,-0.16,{0.62*1560:.1f},{1560+0.16*1560:.1f})" filter="url(#blur3)">'
              f'{hero_sil()}</g>')
    defs.append(f'<mask id="mFloor" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                f'<g clip-path="url(#cpFloor)"><g filter="url(#soft)">{fb}</g>{shadow}</g></mask>')
    defs.append(f'<mask id="mRefl" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                f'<rect x="0" y="1560" width="{W}" height="360" fill="url(#reflFade)"/></mask>')

    defs.append('<clipPath id="cpLeft"><rect x="-400" y="-3000" width="398" height="4000"/></clipPath>')
    defs.append('<linearGradient id="shaftFade" gradientUnits="userSpaceOnUse" x1="284" y1="500" x2="900" y2="1500">'
                '<stop offset="0" stop-color="#fff"/><stop offset="0.55" stop-color="#fff" stop-opacity="0.55"/>'
                '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    body = []
    body.append(rect(0, 0, W, H, '#fff'))
    body.append(layer(wall, 'mWall'))
    body.append(layer(fan_shadow, 'mWall'))
    body.append(layer(sconce, 'mWall'))
    body.append(window_svg())
    body.append(layer(bar, 'mWall'))
    body.append(layer(floor, 'mFloor'))
    # glossy reflection of the hero
    body.append(f'<g mask="url(#mRefl)"><g opacity="0.22" filter="url(#blur3)" '
                f'transform="translate(0,{2*P["ground"]}) scale(1,-1)">{hero("shade", rim=False)}</g></g>')
    # contact shadows
    body.append(ell(716, 1561, 50, 6, g(1.0), 'filter="url(#blur3)" opacity="0.9"'))
    body.append(ell(416, 1561, 40, 6, g(1.0), 'filter="url(#blur3)" opacity="0.9"'))
    body.append(fan())
    # air: light shafts falling from the blinds toward the floor (white haze, behind figures)
    shafts = []
    d, n = band_dirs(P['shaft_ang'])
    for (y0, wdt, op) in P['shafts']:
        x0, L = 284, 1150
        q = [(x0, y0), (x0 + L * d[0], y0 + L * d[1]), (x0 + L * d[0] - wdt * 1.4, y0 + L * d[1] + wdt * 1.6),
             (x0, y0 + wdt)]
        shafts.append(poly(q, 'url(#shaftFade)', f'opacity="{op}"'))
    body.append(f'<g filter="url(#haze)">{"".join(shafts)}</g>')
    body.append(f'<g filter="url(#haze)">{ell(300, 820, 90, 330, "#fff", "opacity=\"0.2\"")}</g>')
    body.append(f'<g filter="url(#haze)" opacity="0.2">'
                f'{poly([(284, 880), (330, 880), (640, 1330), (284, 1330)], "#fff")}</g>')
    body.append(f'<g filter="url(#hazeBig)" opacity="{P["haze"]}">'
                f'{poly([(284, 300), (1080, 660), (1080, 1300), (284, 1200)], "#fff")}</g>')
    # dress forms B (window, backlit), C (mid, spinning)
    body.append(layer(lambda m: form(m, 'B'), 'mB'))
    body.append(form_rim('B', rim=False))
    body.append(layer(lambda m: form(m, 'C'), 'mC'))
    body.append(form_rim('C'))
    body.append(motion_arcs_C())
    # hero + cup
    body.append(layer(lambda m: hero(m) + cup_k(m), 'mHero'))
    body.append(hero_rim())
    body.append(cup_hi())
    tx, ty = HX['hat']
    body.append(f'<g transform="rotate(-4 {tx} {ty})"><path d="M {tx-108},{ty-3} Q {tx-60},{ty-17} {tx},{ty-18} '
                f'Q {tx+60},{ty-17} {tx+108},{ty-3}" fill="none" stroke="#fff" stroke-width="3"/></g>')
    # foreground dress form A
    body.append(layer(lambda m: form(m, 'A'), 'mA'))
    body.append(form_rim('A', pole_rim=False))
    # dust motes in the shafts
    import random
    rnd = random.Random(P['seed'])
    motes = []
    d, n = band_dirs(P['shaft_ang'])
    for _ in range(P['motes']):
        t = rnd.random() ** 1.3
        y0 = rnd.uniform(420, 1000)
        x = 290 + t * 620 * d[0] + rnd.gauss(0, 18)
        y = y0 + t * 620 * d[1] + rnd.gauss(0, 18)
        if 470 < x < 700 and 560 < y < 1460:
            continue  # keep the hero silhouette clean
        r = rnd.choice([2.4, 2.8, 3.2, 4.0])
        motes.append(circ(x, y, r, '#fff', f'opacity="{rnd.uniform(0.45, 0.95):.2f}"'))
    for _ in range(P['motes2']):
        x = rnd.uniform(290, 470) if rnd.random() < 0.6 else rnd.uniform(620, 900)
        y = rnd.uniform(1000, 1300) if x < 480 else rnd.uniform(860, 1050)
        motes.append(circ(x, y, rnd.choice([2.6, 3.0, 3.6]), '#fff', f'opacity="{rnd.uniform(0.6, 1):.2f}"'))
    body.append(''.join(motes))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*2}" height="{H*2}" viewBox="0 0 {W} {H}">'
            f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>')


def build_t():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*2}" height="{H*2}" viewBox="0 0 {W} {H}">'
            f'<rect width="{W}" height="{H}" fill="#fff"/>{cup_t()}</svg>')


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>3 A.M. Noir Print</title>
<style>html,body{margin:0;padding:0;background:#E8E1D0}canvas{display:block}</style></head>
<body><canvas id="out" width="1080" height="1920"></canvas>
<script>
const P = __P__;
const KSRC = 'data:image/svg+xml;base64,__K__';
const TSRC = 'data:image/svg+xml;base64,__T__';
const W = 1080, H = 1920, S = 2, W2 = W * S, H2 = H * S;
function hash(x, y, s) {
  let h = Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263) ^ Math.imul(s | 0, 1442695041);
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16; return (h >>> 0) / 4294967296;
}
function vnoise(x, y, s) {
  const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
  const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
  const a = hash(xi, yi, s), b = hash(xi + 1, yi, s), c = hash(xi, yi + 1, s), d = hash(xi + 1, yi + 1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function fbm(x, y, s, oct) { let t = 0, a = 0.5, f = 1, n = 0; for (let i = 0; i < oct; i++) { t += a * vnoise(x * f, y * f, s + i * 17); n += a; a *= 0.5; f *= 2; } return t / n; }
function load(src) { return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = src; }); }
function plate(im) {
  const c = document.createElement('canvas'); c.width = W2; c.height = H2;
  const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, W2, H2); x.drawImage(im, 0, 0, W2, H2);
  return x.getImageData(0, 0, W2, H2).data;
}
// round-dot radius for coverage D in a square cell of side c
function makeLUT(c) {
  const N = 1024, lut = new Float32Array(N + 1);
  const cov = r => { const h = c / 2; if (r <= h) return Math.PI * r * r / (c * c);
    if (r >= h * Math.SQRT2) return 1;
    const seg = r * r * Math.acos(h / r) - h * Math.sqrt(r * r - h * h);
    return (Math.PI * r * r - 4 * seg) / (c * c); };
  for (let i = 0; i <= N; i++) { const D = i / N; let lo = 0, hi = c * 0.7072;
    for (let k = 0; k < 40; k++) { const m = (lo + hi) / 2; if (cov(m) < D) lo = m; else hi = m; } lut[i] = (lo + hi) / 2; }
  return lut;
}
function screen(data, cell, angDeg, solidHi) {
  const out = new Float32Array(W2 * H2), lut = makeLUT(cell);
  const a = angDeg * Math.PI / 180, ca = Math.cos(a) / cell, sa = Math.sin(a) / cell;
  for (let y = 0; y < H2; y++) for (let x = 0; x < W2; x++) {
    const i = y * W2 + x, D = 1 - data[i * 4] / 255;
    if (D <= 0.01) continue;
    if (D >= solidHi) { out[i] = 1; continue; }
    let u = (x + 0.5) * ca + (y + 0.5) * sa, v = -(x + 0.5) * sa + (y + 0.5) * ca;
    u -= Math.round(u); v -= Math.round(v);
    const d = Math.sqrt(u * u + v * v) * cell;
    out[i] = d < lut[(D * 1024) | 0] ? 1 : 0;
  }
  return out;
}
function spread(ink, thr, jit, seed) {
  // 5-tap separable box blur (~0.7px at 1x) + noisy threshold = ink spread / organic edges
  const tmp = new Float32Array(W2 * H2), out = new Float32Array(W2 * H2);
  for (let y = 0; y < H2; y++) { let acc = 0; const r = y * W2;
    for (let x = -2; x < W2 + 2; x++) {
      if (x + 2 < W2) acc += ink[r + x + 2]; if (x - 3 >= 0) acc -= ink[r + x - 3];
      if (x >= 0 && x < W2) tmp[r + x] = acc / 5; } }
  for (let x = 0; x < W2; x++) { let acc = 0;
    for (let y = -2; y < H2 + 2; y++) {
      if (y + 2 < H2) acc += tmp[(y + 2) * W2 + x]; if (y - 3 >= 0) acc -= tmp[(y - 3) * W2 + x];
      if (y >= 0 && y < H2) { const b = acc / 5; const n = vnoise(x * 0.35, y * 0.35, seed) - 0.5;
        const t = thr + jit * n; out[y * W2 + x] = Math.min(1, Math.max(0, (b - t) * 6 + 0.5)); } } }
  return out;
}
function down(a) {
  const o = new Float32Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = 2 * y * W2 + 2 * x; o[y * W + x] = (a[i] + a[i + 1] + a[i + W2] + a[i + W2 + 1]) * 0.25; }
  return o;
}
(async () => {
  const t0 = performance.now();
  const [ik, it] = await Promise.all([load(KSRC), load(TSRC)]);
  const dk = plate(ik), dt = plate(it);
  let K = screen(dk, P.cell * S, P.ang, 0.985), T = screen(dt, P.cell * S, P.ang_t, 0.9);
  K = down(spread(K, P.spread_thr, P.spread_jit, 5)); T = down(spread(T, P.spread_thr, P.spread_jit, 9));
  const cv = document.getElementById('out'), ctx = cv.getContext('2d');
  const img = ctx.createImageData(W, H), px = img.data;
  const pap = P.paper, bk = P.black, tl = P.teal;
  let s = P.seed * 7919 + 1;
  const rnd = () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x;
    const tooth = 1 - P.tooth * fbm(x * 0.6, y * 0.6, 3, 2);
    const mott = fbm(x * 0.004, y * 0.004, 21, 3);
    const pm = 1 - 0.02 * fbm(x * 0.01, y * 0.012, 31, 3);
    let r = pap[0] * tooth * pm, g = pap[1] * tooth * pm, b = pap[2] * tooth * pm;
    const at = T[i], ak = K[i];
    const mesh = ((x + y) & 1) ? 1 : 0;
    if (at > 0) { const tm = 0.94 + 0.12 * mott - P.mesh * mesh;
      r += (tl[0] * tm - r) * at; g += (tl[1] * tm - g) * at; b += (tl[2] * tm - b) * at; }
    if (ak > 0) { const km = 0.85 + 0.45 * fbm(x * 0.01, y * 0.01, 41, 3) - P.mesh * mesh * 2;
      const kr = bk[0] * km * 0.96 + r * 0.04, kg = bk[1] * km * 0.96 + g * 0.04, kb = bk[2] * km * 0.96 + b * 0.04;
      r += (kr - r) * ak; g += (kg - g) * ak; b += (kb - b) * ak; }
    const gr = (rnd() + rnd() - 1) * P.grain * 255;
    px[i * 4] = r + gr; px[i * 4 + 1] = g + gr; px[i * 4 + 2] = b + gr; px[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  console.log('pipeline ms', Math.round(performance.now() - t0));
  window.__done = true;
})();
</script></body></html>
"""


def main():
    import json
    k = build_k()
    t = build_t()
    with open(os.path.join(HERE, 'plate_k.svg'), 'w') as f:
        f.write(k)
    with open(os.path.join(HERE, 'plate_t.svg'), 'w') as f:
        f.write(t)
    html = (HTML.replace('__P__', json.dumps(P))
            .replace('__K__', base64.b64encode(k.encode()).decode())
            .replace('__T__', base64.b64encode(t.encode()).decode()))
    with open(OUT, 'w') as f:
        f.write(html)
    print('wrote', OUT, len(html) // 1024, 'KB')


if __name__ == '__main__':
    main()
