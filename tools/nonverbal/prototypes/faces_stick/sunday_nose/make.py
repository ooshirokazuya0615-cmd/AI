#!/usr/bin/env python3
"""Sunday Nose on stick bodies.

HEAD  = the original Face rig from make_face_original.py, imported unchanged
        (Face2 only adds per-eye gaze for crossed eyes and the neck anchor).
BODY  = one shared stick rig: neck anchor + pose dict -> joints -> ink strokes
        with a cyan / mustard colour plate printed 3 px off register.
Every frame is body(pose) + head(expression); scene.svg and poses.svg are both
built from these same two rigs.
"""
import math, os, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_face_original as F                     # noqa: E402
from make_face_original import (INK, CREAM, CYAN, ROSE, MUSTARD, PINKNOSE, WHITE, CLOTH, MOUTH, FLUSH, OFF,  # noqa
                                uid, f1, P, rot, xf, ellipse_pts, hull, resample, spline, qbez, clipped, crescent,
                                inked, stroke, ring_d, ht_fade, ht_ellipse, common_defs, grain, drop_pts, Face,
                                teacup, steam, doughnut, glaze_drip, newspaper, awning, shrub, small_table)

SKIN_B = F.SKIN_B; SKIN_G = F.SKIN_G
LOAFER = '#6E4526'; TEA = '#A9682F'; TEA_HI = '#C98A4A'; FLOOR = '#E5DBC5'


# ================================================================ head rig (unchanged, plus two hooks)
class Face2(Face):
    def eye_geom(s, side, e):
        if e.get('gaze_lr'):
            e = dict(e); e['gaze'] = e['gaze_lr'][0 if side < 0 else 1]
        return Face.eye_geom(s, side, e)

    def anchor(s, tilt=0.0):
        """neck/tilt pivot: (cx + turn*0.06*hw, cy + 0.44*hh), turned with the head."""
        return rot((s.cx + s.turn * 0.06 * s.hw, s.cy + 0.44 * s.hh), tilt, (s.cx, s.cy))


def bix_head(cx, cy, hh=320, turn=0.7):
    k = hh / 390.0
    return Face2(cx, cy, hh * 250 / 320, hh, SKIN_B, dict(kind='button', w=80 * k, h=60 * k, y=0.55, fill='#9E6A49'),
                 72 * k, 108 * k, 14 * k, 72 * k, 14, 28 * k, pupil_r=max(6.5, 9 * k), turn=turn, hair='flicks', seed=11)


def gus_head(cx, cy, hh=340, turn=-0.85):
    k = hh / 430.0
    return Face2(cx, cy, hh * 290 / 340, hh, SKIN_G,
                 dict(kind='potato', w=150 * k, h=120 * k, y=0.57, fill=PINKNOSE, shade='htR'),
                 78 * k, 112 * k, 28 * k, 72 * k, 13, 22 * k, pupil_r=max(7, 9 * k), turn=turn, hair='fringe', seed=21,
                 shade_op=0.5, egg_k=0.15, eye_ox=1.0, far_shift=4 * k, jowls=True)


def wit_head(cx, cy, hh=240, turn=-0.55):
    k = hh / 180.0
    return Face2(cx, cy, hh * 150 / 180, hh, '#C99A72', dict(kind='button', w=46 * k, h=34 * k, y=0.56, fill='#AD7F5A'),
                 34 * k, 50 * k, 7 * k, 30 * k, 12, 12 * k, pupil_r=6.5, turn=turn, hair='fringe', seed=31,
                 line=(6, 9), shade_op=0.45)


# ================================================================ stick body rig
def D(a):
    """direction for an angle measured from straight down: 0 down, 90 right, -90 left, 180 up."""
    r = math.radians(a)
    return (math.sin(r), math.cos(r))


def padd(p, v, k=1.0):
    return (p[0] + v[0] * k, p[1] + v[1] * k)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def ink_poly(pts, w0, w1, swell=0.10, seed=0, step=2.5, wmin=9.0, capn=10):
    """variable-width ink stroke with ROUND caps at both ends (never a pointed brush end)."""
    pts = resample(pts, step, False)
    n = len(pts)
    ph = random.Random(seed).random() * 6.28
    Lp, Rp, W = [], [], []
    for i in range(n):
        p0 = pts[max(i - 1, 0)]; p2 = pts[min(i + 1, n - 1)]
        tx, ty = p2[0] - p0[0], p2[1] - p0[1]; l = math.hypot(tx, ty) or 1
        nx, ny = -ty / l, tx / l
        s = i / (n - 1)
        w = (w0 + (w1 - w0) * s) * (1 + swell * (0.6 * math.sin(math.pi * s) + 0.4 * math.sin(s * 7.0 + ph)))
        w = max(wmin, w); W.append(w)
        Lp.append((pts[i][0] + nx * w / 2, pts[i][1] + ny * w / 2))
        Rp.append((pts[i][0] - nx * w / 2, pts[i][1] - ny * w / 2))

    def tangent(i, j):
        tx, ty = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]; l = math.hypot(tx, ty) or 1
        return tx / l, ty / l
    te = tangent(n - 2, n - 1); ts = tangent(0, 1)
    an_e = math.atan2(te[0], -te[1]); an_s = math.atan2(ts[0], -ts[1])
    end = [(pts[-1][0] + W[-1] / 2 * math.cos(an_e - math.pi * k / capn), pts[-1][1] + W[-1] / 2 * math.sin(an_e - math.pi * k / capn)) for k in range(1, capn)]
    beg = [(pts[0][0] + W[0] / 2 * math.cos(an_s + math.pi - math.pi * k / capn), pts[0][1] + W[0] / 2 * math.sin(an_s + math.pi - math.pi * k / capn)) for k in range(1, capn)]
    return Lp + end + Rp[::-1] + beg


def ik(S, T, a, b, bend=1):
    """two-bone IK. bend=+1 / -1 picks the elbow (knee) side; never fully straight unless asked."""
    dx, dy = T[0] - S[0], T[1] - S[1]
    d = math.hypot(dx, dy) or 1
    d = max(abs(a - b) + 1, min(a + b - 0.5, d))
    ang = math.atan2(dy, dx)
    al = math.acos(max(-1, min(1, (a * a + d * d - b * b) / (2 * a * d))))
    ea = ang + bend * al
    E = (S[0] + a * math.cos(ea), S[1] + a * math.sin(ea))
    W = (S[0] + d * math.cos(ang), S[1] + d * math.sin(ang))
    return E, W


HU_DEF = dict(hide=0.06, sh=0.15, spine=0.73, up=0.53, fore=0.50, thigh=0.64, shin=0.62,
              foot=0.19, foot_h=0.085, hand=0.13, hand_w=0.085)

SHOE_LOC = [(-0.30, -0.05), (-0.25, -0.52), (0.02, -0.60), (0.30, -0.40), (0.58, -0.25), (0.74, -0.02),
            (0.75, 0.32), (0.64, 0.46), (-0.30, 0.46), (-0.37, 0.22)]


class Stick:
    """joint positions -> strokes.  pose keys (angles from straight down, world space):
       neck, spine, bow (HU, toward the facing side), n/f + up, lo (arm), th, sh (leg),
       toe (toe direction), sole (+1/-1 which side the sole faces), hand (paddle direction),
       grip ('mitt' | 'flat' | 'pinch' | 'none'), thumb (+1/-1 side), lo_k (forearm foreshortening)."""

    def __init__(s, hu, facing=-1, plate=CYAN, glove=WHITE, shoe='brogue', seed=300, L=None,
                 legw=(18, 14, 11), armw=(16, 13, 10.5), spinew=(17, 16), knuckle=False):
        s.hu, s.facing, s.plate, s.glove, s.shoe_kind, s.seed = hu, facing, plate, glove, shoe, seed
        s.L = dict(HU_DEF); s.L.update(L or {})
        s.legw, s.armw, s.spinew, s.knuckle = legw, armw, spinew, knuckle

    # ---------------------------------------------------------- joints
    def joints(s, A, p):
        L, hu = s.L, s.hu
        J = dict(A=A, pose=p)
        S = padd(A, D(p.get('neck', 0)), (L['hide'] + L['sh']) * hu)
        H = padd(S, D(p.get('spine', 0)), L['spine'] * hu)
        t = D(p.get('spine', 0)); perp = (-t[1], t[0])
        M = padd(lerp(S, H, 0.5), perp, -s.facing * p.get('bow', 0) * hu)
        J.update(S=S, H=H, M=M)
        J['spine_pts'] = spline([A, S, M, H], False, 14)
        J['neck_base'] = padd(A, D(p.get('neck', 0)), L['hide'] * hu)
        for k in 'nf':
            if k + 'Wr' in p:                      # IK: wrist target relative to the shoulder (HU) + elbow side
                T = (S[0] + p[k + 'Wr'][0] * hu, S[1] + p[k + 'Wr'][1] * hu)
                E, W = ik(S, T, L['up'] * hu, L['fore'] * hu * p.get(k + 'lo_k', 1.0), p.get(k + 'bend', 1))
            elif k + 'Wt' in p:
                E, W = ik(S, p[k + 'Wt'], L['up'] * hu, L['fore'] * hu * p.get(k + 'lo_k', 1.0), p.get(k + 'bend', 1))
            else:
                E = padd(S, D(p[k + 'up']), L['up'] * hu)
                W = padd(E, D(p[k + 'lo']), L['fore'] * hu * p.get(k + 'lo_k', 1.0))
            lk = p.get(k + 'leg_k', 1.0)           # projection of a leg pointing partly toward the camera
            if k + 'Fr' in p:
                T = (H[0] + p[k + 'Fr'][0] * hu, H[1] + p[k + 'Fr'][1] * hu)
                K, Fa = ik(H, T, L['thigh'] * hu * lk * p.get(k + 'th_k', 1.0), L['shin'] * hu * lk, p.get(k + 'kbend', 1))
            else:
                K = padd(H, D(p[k + 'th']), L['thigh'] * hu * lk * p.get(k + 'th_k', 1.0))
                Fa = padd(K, D(p[k + 'sh']), L['shin'] * hu * lk)
            J[k + 'E'], J[k + 'W'], J[k + 'K'], J[k + 'F'] = E, W, K, Fa
            J[k + 'shoe'] = s.shoe_poly(Fa, p.get(k + 'toe', 90 * s.facing), p.get(k + 'sole', s.facing))
            J[k + 'hand_ang'] = p.get(k + 'hand', math.degrees(math.atan2(W[0] - E[0], W[1] - E[1])))
        return J

    def shoe_poly(s, Fa, toe_ang, sole):
        L = s.L['foot'] * s.hu; Hh = s.L['foot_h'] * s.hu
        td = D(toe_ang)
        sn = (-td[1], td[0]) if sole > 0 else (td[1], -td[0])
        loc = spline([(x * L, y * Hh) for x, y in SHOE_LOC], True, 8)
        return [(Fa[0] + td[0] * u + sn[0] * v, Fa[1] + td[1] * u + sn[1] * v) for u, v in loc]

    # ---------------------------------------------------------- parts
    def limb(s, p0, p1, p2, w, seed):
        a = ink_poly([p0, p1], w[0], w[1], seed=seed)
        b = ink_poly([p1, p2], w[1], w[2], seed=seed + 1)
        ap = ink_poly([p0, p1], w[0] + 4, w[1] + 4, seed=seed)
        bp = ink_poly([p1, p2], w[1] + 4, w[2] + 4, seed=seed + 1)
        return (f'<path d="{P(xf(ap, *OFF))}" fill="{s.plate}"/><path d="{P(xf(bp, *OFF))}" fill="{s.plate}"/>'
                f'<path d="{P(a)}" fill="{INK}"/><path d="{P(b)}" fill="{INK}"/>')

    def spine(s, J):
        pts = J['spine_pts']
        a = ink_poly(pts, s.spinew[0], s.spinew[1], swell=0.08, seed=s.seed + 5)
        ap = ink_poly(pts, s.spinew[0] + 4, s.spinew[1] + 4, swell=0.08, seed=s.seed + 5)
        return f'<path d="{P(xf(ap, *OFF))}" fill="{s.plate}"/><path d="{P(a)}" fill="{INK}"/>'

    def shoe(s, J, k):
        pts = J[k + 'shoe']
        out = []
        if s.shoe_kind == 'brogue':
            out.append(f'<path d="{P(xf(pts, *OFF))}" fill="{s.plate}"/>')
            out.append(f'<path d="{P(pts)}" fill="{INK}"/>')
            p = J['pose']; td = D(p.get(k + 'toe', 90 * s.facing)); sole = p.get(k + 'sole', s.facing)
            sn = (-td[1], td[0]) if sole > 0 else (td[1], -td[0])
            L = s.L['foot'] * s.hu; Hh = s.L['foot_h'] * s.hu; Fa = J[k + 'F']
            W = lambda u, v: (Fa[0] + td[0] * u * L + sn[0] * v * Hh, Fa[1] + td[1] * u * L + sn[1] * v * Hh)
            out.append(stroke(qbez(W(0.36, -0.30), W(0.56, -0.26), W(0.66, -0.06), 10), 4.5, color=WHITE, taper=(0.3, 0.3)))
            for j in range(4):           # brogue perforations along the toe cap seam (dots, no glyphs)
                q = W(0.30 - 0.03 * j, -0.30 + 0.17 * j)
                out.append(f'<circle cx="{f1(q[0])}" cy="{f1(q[1])}" r="1.9" fill="{CLOTH}"/>')
            out.append(stroke([W(-0.28, 0.30), W(0.62, 0.30)], 2.6, color='#4A4A4A', taper=(0.1, 0.1)))
        else:                            # loafer + cyan sock plate
            p = J['pose']; Fa = J[k + 'F']; Kn = J[k + 'K']
            dv = (Fa[0] - Kn[0], Fa[1] - Kn[1]); dl = math.hypot(*dv) or 1; dv = (dv[0] / dl, dv[1] / dl)
            sock = ink_poly([padd(Fa, dv, -0.10 * s.hu), padd(Fa, dv, -0.01 * s.hu)], 24, 24, swell=0, wmin=1)
            out.append(inked(sock, CYAN, (3, 4.5), s.seed + 60))
            out.append(stroke([padd(padd(Fa, dv, -0.06 * s.hu), (-dv[1], dv[0]), 11), padd(padd(Fa, dv, -0.06 * s.hu), (-dv[1], dv[0]), -11)], 3, color=CLOTH, taper=(0.2, 0.2)))
            out.append(inked(pts, LOAFER, (4, 6), s.seed + 61))
            td = D(p.get(k + 'toe', 90 * s.facing)); sole = p.get(k + 'sole', s.facing)
            sn = (-td[1], td[0]) if sole > 0 else (td[1], -td[0])
            L = s.L['foot'] * s.hu; Hh = s.L['foot_h'] * s.hu
            W = lambda u, v: (Fa[0] + td[0] * u * L + sn[0] * v * Hh, Fa[1] + td[1] * u * L + sn[1] * v * Hh)
            out.append(stroke(qbez(W(0.12, -0.40), W(0.30, -0.24), W(0.46, -0.32), 10), 4, taper=(0.2, 0.2)))
            out.append(stroke(qbez(W(0.46, -0.20), W(0.60, -0.14), W(0.68, 0.02), 8), 4, color='#C79A6B', taper=(0.3, 0.3)))
        return ''.join(out)

    def mitten_pts(s, Wp, ang, flat=1.0):
        L = s.L['hand'] * s.hu; Wd = s.L['hand_w'] * s.hu
        d = D(ang); n = (-d[1], d[0])
        pts = []
        for i in range(44):
            t = 2 * math.pi * i / 44
            u = L * 0.44 + L * 0.56 * math.cos(t)
            v = Wd / 2 * flat * math.sin(t) * (1 + 0.16 * math.cos(t))
            pts.append((Wp[0] + d[0] * u + n[0] * v, Wp[1] + d[1] * u + n[1] * v))
        return pts

    def thumb_pts(s, Wp, ang, side, flat=1.0, along=0.34, spread=48):
        L = s.L['hand'] * s.hu; Wd = s.L['hand_w'] * s.hu
        d = D(ang); n = (-d[1], d[0])
        c = (Wp[0] + d[0] * L * along + n[0] * side * Wd * 0.46 * flat, Wp[1] + d[1] * L * along + n[1] * side * Wd * 0.46 * flat)
        td = D(ang - side * spread)
        tn = (-td[1], td[0])
        pts = []
        for i in range(30):
            t = 2 * math.pi * i / 30
            u = L * 0.20 * math.cos(t) + L * 0.10; v = Wd * 0.25 * math.sin(t)
            pts.append((c[0] + td[0] * u + tn[0] * v, c[1] + td[1] * u + tn[1] * v))
        return pts

    def hand(s, J, k):
        p = J['pose']; grip = p.get(k + 'grip', 'mitt')
        if grip == 'none':
            return ''
        flat = 0.78 if grip == 'flat' else 1.0
        pts = s.mitten_pts(J[k + 'W'], J[k + 'hand_ang'], flat)
        inner = ''
        if s.knuckle:
            L = s.L['hand'] * s.hu; d = D(J[k + 'hand_ang']); W0 = J[k + 'W']
            kc = (W0[0] + d[0] * L * 0.72, W0[1] + d[1] * L * 0.72)
            inner = clipped(pts, f'<circle cx="{f1(kc[0] + OFF[0])}" cy="{f1(kc[1] + OFF[1])}" r="{f1(L * 0.42)}" fill="url(#htRs)"/>', OFF)
        return inked(pts, s.glove, (3, 4.5), s.seed + (11 if k == 'n' else 17), inner=inner)

    def thumb(s, J, k):
        p = J['pose']; grip = p.get(k + 'grip', 'mitt')
        if grip == 'none':
            return ''
        flat = 0.78 if grip == 'flat' else 1.0
        side = p.get(k + 'thumb', 1)
        pts = s.thumb_pts(J[k + 'W'], J[k + 'hand_ang'], side, flat, p.get(k + 'thumb_at', 0.34), p.get(k + 'thumb_sp', 48))
        return inked(pts, s.glove, (2.5, 4), s.seed + (21 if k == 'n' else 27))

    def layers(s, J):
        lw, aw = s.legw, s.armw
        out = {}
        for k, sd in (('f', 40), ('n', 50)):
            out[k + '_leg'] = s.limb(J['H'], J[k + 'K'], J[k + 'F'], lw, s.seed + sd) + s.shoe(J, k)
            out[k + '_arm'] = s.limb(J['S'], J[k + 'E'], J[k + 'W'], aw, s.seed + sd + 5) + s.hand(J, k)
            out[k + '_thumb'] = s.thumb(J, k)
        out['spine'] = s.spine(J)
        return out


# ================================================================ costume props
def bow_tie(c, neck_ang, size, seed, squash=1.0):
    bl = [(0, -0.05), (-0.48, -0.27), (-0.53, 0.25), (0, 0.07)]
    out = []
    for sd in (-1, 1):
        loc = spline([(x * size * sd * squash, y * size) for x, y in bl], True, 6)
        out.append(inked(xf(loc, c[0], c[1], -neck_ang), ROSE, (4, 5.5), seed + sd,
                         inner=clipped(xf(loc, c[0], c[1], -neck_ang), f'<rect x="{f1(c[0] - size)}" y="{f1(c[1])}" width="{f1(2 * size)}" height="{f1(size)}" fill="url(#htRs)" opacity="0.7"/>', OFF)))
        crease = xf([(sd * size * 0.16 * squash, -0.02 * size), (sd * size * 0.36 * squash, -0.10 * size)], c[0], c[1], -neck_ang)
        out.append(stroke(crease, 3.5, taper=(0.2, 0.3), wmin=0.5))
    out.append(inked(xf(ellipse_pts(0, 0.01 * size, size * 0.12 * max(squash, 0.8), size * 0.14, 30), c[0], c[1], -neck_ang), ROSE, (3.5, 5), seed + 5))
    return ''.join(out)


def apron(H, spine_ang, hu, hang, spread, seed, facing, length=0.95, wb=0.28, flutter=0.0, tails=None):
    t = D(spine_ang); n = (-t[1], t[0])
    R = length * hu
    tl = padd(H, n, wb * hu / 2); tr = padd(H, n, -wb * hu / 2)
    a0 = hang - spread / 2; a1 = hang + spread / 2
    N = 30
    rr = lambda i: R * (1 + flutter * math.sin(i * math.pi * 6 / N) * (0.3 + 0.7 * i / N))
    arc = [padd(H, D(a0 + (a1 - a0) * i / N), rr(i)) for i in range(N + 1)]
    if math.dist(tl, arc[0]) + math.dist(tr, arc[-1]) > math.dist(tl, arc[-1]) + math.dist(tr, arc[0]):
        arc = arc[::-1]
    poly = [tl] + arc + [tr]
    npl = 5
    inner = []
    for j in range(npl):                         # alternate pleats shaded with cyan halftone
        if j % 2 == 1:
            w = [lerp(tl, tr, j / npl), lerp(tl, tr, (j + 1) / npl)] + arc[int(N * (j + 1) / npl)::-1][:int(N / npl) + 1]
            inner.append(f'<path d="{P(xf(w, *OFF))}" fill="url(#htCs)" opacity="0.9"/>')
    inner.append(crescent(poly, 'htC', -14 * facing, -8, 0.35))
    band_o = [padd(H, D(a0 + (a1 - a0) * i / N), rr(i) * 0.93) for i in range(N + 1)]
    band_i = [padd(H, D(a0 + (a1 - a0) * i / N), rr(i) * 0.875) for i in range(N + 1)]
    inner.append(f'<path d="{P(xf(band_o + band_i[::-1], *OFF))}" fill="{CYAN}"/>')
    body = clipped(poly, ''.join(inner), (0, 0))
    out = [inked(poly, CLOTH, (5, 7.5), seed, inner=body)]
    for j in range(1, npl):
        a = lerp(tl, tr, j / npl); b = arc[int(N * j / npl)]
        out.append(stroke([lerp(a, b, 0.08), lerp(a, b, 0.86)], 3.5, taper=(0.3, 0.3), wmin=0.4))
    out.append(stroke([padd(tl, t, 3), padd(tr, t, 3)], 9, taper=(0.05, 0.05)))
    if tails is not None:                       # apron strings at the back: lag the body, settle late
        back = tl if (tl[0] - H[0]) * facing < 0 else tr
        for k, (da, ln) in enumerate(((-9, 0.20), (11, 0.16))):
            d = D(tails + da); nn = (-d[1], d[0])
            q = [padd(back, nn, -6), padd(back, nn, 6), padd(padd(back, d, ln * hu), nn, 5), padd(padd(back, d, ln * hu), nn, -5)]
            out.append(inked(q, CLOTH, (3, 4), seed + 9 + k))
    return ''.join(out)


def necktie(c, ang, L, w, seed, bend=0.0):
    def B(p):
        x, y = p
        return (x + bend * L * (max(y, 0) / L) ** 2, y)
    blade = [B(p) for p in spline([(-0.17 * w, 0.10 * w), (0.17 * w, 0.10 * w), (0.36 * w, 0.45 * L), (0.50 * w, 0.84 * L),
                                   (0.0, L), (-0.50 * w, 0.84 * L), (-0.36 * w, 0.45 * L)], True, 6)]
    knot = spline([(-0.30 * w, -0.17 * w), (0.30 * w, -0.17 * w), (0.19 * w, 0.20 * w), (-0.19 * w, 0.20 * w)], True, 5)
    bw = xf(blade, c[0], c[1], -ang); kn = xf(knot, c[0], c[1], -ang)
    out = []
    for poly, sd in ((bw, 0), (kn, 3)):
        x, y, ww, hh = min(p[0] for p in poly) - 40, min(p[1] for p in poly) - 40, 400, 400
        inner = clipped(poly, f'<rect x="{f1(x)}" y="{f1(y)}" width="{ww}" height="{hh}" fill="url(#chk)"/>', OFF) + crescent(poly, 'htM', -10, -6, 0.6)
        out.append(inked(poly, MUSTARD, (4, 6), seed + sd, inner=inner))
    return ''.join(out)


CUP_BODY = [(-86, -46), (-82, -6), (-58, 34), (0, 46), (58, 34), (82, -6), (86, -46)]


def cup(bx, by, s=0.75, tip=0.0, bulge=False, drop_up=0.0, flip=False):
    """teacup() from the face file, carried by its saucer bottom (bx, by)."""
    svg, rim_y, rh = teacup(0, 0)
    extra = []
    if bulge:                                   # brim tension: the tea surface domes above the rim, still attached
        dome = [(22 + 15 * math.cos(t), -59 - 13 * math.sin(t)) for t in (math.pi * j / 24 for j in range(25))]
        extra.append(f'<path d="{P(dome)}" fill="{TEA}"/>')
        extra.append(f'<path d="{P(ellipse_pts(18, -63, 5, 3.5, 20))}" fill="{TEA_HI}"/>')
        extra.append(stroke(dome, 5, taper=(0.12, 0.12), wmin=0.4))
        extra.append(f'<circle cx="17" cy="-65" r="2.6" fill="{WHITE}"/>')
    if drop_up:                                 # a single droplet lifted clear of the rim, frozen
        dp = drop_pts(24, -66 - drop_up, 26, 0)
        extra.append(inked(dp, TEA, (3.5, 5), 77, bias=0.5, off=(2, 2)))
        extra.append(f'<circle cx="19" cy="{f1(-69 - drop_up)}" r="3.4" fill="{WHITE}"/>')
        for dx in (-26, 70):
            extra.append(stroke([(dx, -70 - drop_up * 0.6), (dx + (8 if dx > 0 else -8), -86 - drop_up * 0.6)], 5, taper=(0.1, 0.6)))
    sx = -s if flip else s
    return (f'<g transform="translate({f1(bx)} {f1(by)}) rotate({f1(tip)}) scale({f1(sx)} {f1(s)}) translate(0 -73)">'
            f'{svg}{"".join(extra)}</g>')


def cup_ghost(bx, by, s, op, flip=False):
    """afterimage of the cup in world space: cyan halftone fill + a dotted ink silhouette (print-style ghost)."""
    sx = -s if flip else s
    T = lambda pts: [(bx + x * sx, by + (y - 73) * s) for x, y in pts]
    body = T(spline(CUP_BODY, True, 10))
    sau = T(ellipse_pts(0, 50, 124, 23, 70))
    rim = T(ellipse_pts(0, -46, 86, 19, 60))
    hd = T(spline([(-70, -26), (-122, -28), (-124, 14), (-58, 26)], False, 10))
    dash = f'fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round" stroke-dasharray="0.1 8.5"'
    shapes = (f'<path d="{P(sau)}" fill="{CLOTH}" fill-opacity="0.55"/><path d="{P(sau)}" fill="url(#htCs)"/>'
              f'<path d="{P(body)}" fill="{CLOTH}" fill-opacity="0.55"/><path d="{P(body)}" fill="url(#htC)"/>'
              f'<path d="{P(rim)}" fill="{CLOTH}"/><path d="{P(rim)}" fill="url(#htCs)" opacity="0.5"/>'
              f'<path d="{P(sau)}" {dash}/><path d="{P(body)}" {dash}/><path d="{P(rim)}" {dash}/><path d="{P(hd, False)}" {dash}/>')
    return f'<g opacity="{op}">{shapes}</g>'


def held_doughnut(cx, cy, s, tip, drip=True):
    ow, oh = 78, 34
    inner = doughnut(0, 0, ow, oh)
    if drip:
        inner += glaze_drip(6, oh + 6, 30)
    return f'<g transform="translate({f1(cx)} {f1(cy)}) rotate({f1(tip)}) scale({f1(s)})">{inner}</g>'


def motion_arc(pts, w=5, color=INK):
    return stroke(pts, w, color=color, taper=(0.05, 0.85), wmin=0.15)


def arc_pts(c, rx, ry, a0, a1, n=40):
    return [(c[0] + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


# ================================================================ character assembly
def place(face_fn, E, body, pose, head_x, floor_y, stand='n'):
    """build the head at head_x, then slide everything so the standing shoe sole sits on the floor."""
    tilt = E.get('head_tilt', 0)
    f0 = face_fn(head_x, 0.0)
    J0 = body.joints(f0.anchor(tilt), pose)
    low = max(p[1] for p in J0[stand + 'shoe'])
    cy = floor_y - low
    f = face_fn(head_x, cy)
    return f, body.joints(f.anchor(tilt), pose)


def figure(face, E, body, J, back='', front='', prop='', marks='', shadow='', under_far=''):
    L = body.layers(J)
    return ''.join([shadow, L['f_leg'], under_far, L['f_arm'], L['spine'], back, face.draw(E), front,
                    L['n_leg'], L['n_arm'], prop, L['f_thumb'], L['n_thumb'], marks])


def bbox_of(J, extra=()):
    pts = [J[k] for k in ('A', 'S', 'H', 'nE', 'nW', 'nK', 'nF', 'fE', 'fW', 'fK', 'fF')] + J['nshoe'] + J['fshoe'] + list(extra)
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


# ================================================================ BIX / GUS bodies
def bix_body(hu, facing):
    return Stick(hu, facing, plate=CYAN, glove=WHITE, shoe='brogue', seed=400)


def gus_body(hu, facing):
    return Stick(hu, facing, plate=MUSTARD, glove=SKIN_G, shoe='loafer', seed=500, knuckle=True,
                 L=dict(spine=0.75))


# ================================================================ SCENE
def window2():
    out = []
    x0, y0, x1, y1 = 600, 400, 1100, 950
    glass = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    out.append(f'<path d="{P(glass)}" fill="#DCE7E6"/>')
    out.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="url(#htCs)" opacity="0.75"/>')
    for a, b in ((640, 70), (742, 26)):
        st = [(a, y1), (a + b, y1), (a + b + 220, y0), (a + 220, y0)]
        out.append(clipped(glass, f'<path d="{P(st)}" fill="#EEF2EC"/>'))
    # back counter + cups on a shelf inside the café (abstract shapes only)
    out.append(clipped(glass, f'<rect x="{x0}" y="{y1 - 70}" width="{x1 - x0}" height="70" fill="#C9D6D4"/>'
                              f'<rect x="{x0}" y="{y1 - 70}" width="{x1 - x0}" height="70" fill="url(#htKs)" opacity="0.25"/>'))
    out.append(inked(glass, None, (8, 12), 61))
    sill = [(x0 - 16, y1 - 2), (x1, y1 - 2), (x1, y1 + 18), (x0 - 16, y1 + 18)]
    out.append(inked(sill, CREAM, (6, 8), 62))
    return ''.join(out)


def floor2(y0=950):
    out = [f'<rect x="0" y="{y0}" width="1080" height="{1920 - y0 + 2}" fill="{FLOOR}"/>',
           stroke([(-10, y0), (1090, y0 + 1)], 8, taper=(0, 0))]
    # terrace tiles in perspective: faint joints vanishing toward the shop
    vx, vy = 540, 360
    for k in range(-9, 10):
        xb = 540 + k * 170
        t0 = (y0 - vy) / (1920 - vy)
        xa = vx + (xb - vx) * t0
        out.append(stroke([(xa, y0), (xb, 1920)], 2.5, color='#D3C7AE', taper=(0, 0)))
    for y in (978, 1022, 1086, 1176, 1300, 1470, 1710):
        out.append(stroke([(-10, y), (1090, y)], 2.5, color='#D3C7AE', taper=(0, 0)))
    out.append(ht_fade(0, 1420, 1080, 1920, CYAN, pitch=10, rmax=4.2, rmin=0.2, power=1.25))
    return ''.join(out)


def bistro_chair(x, y, s=1.0, flip=1):
    """background café chair (rose metal) - lighter value than the cast."""
    c = '#B9607F'
    out = []
    pts = lambda L: [(x + flip * a * s, y + b * s) for a, b in L]
    out.append(stroke(pts([(-40, 0), (-44, 120)]), 6, color=c, taper=(0, 0)))
    out.append(stroke(pts([(40, 0), (46, 120)]), 6, color=c, taper=(0, 0)))
    out.append(stroke(pts([(36, 0), (40, -120), (30, -150)]), 6, color=c, taper=(0, 0)))
    out.append(stroke(pts([(-36, 0), (-30, -120), (-22, -150)]), 6, color=c, taper=(0, 0)))
    out.append(stroke(qbez(*pts([(-26, -146), (4, -170), (34, -146)])), 6, color=c, taper=(0, 0)))
    out.append(stroke(qbez(*pts([(-30, -96), (4, -110), (38, -96)])), 5, color=c, taper=(0, 0)))
    seat = pts([(-54, -6), (54, -6), (50, 8), (-50, 8)])
    out.append(inked(seat, ROSE, (3.5, 5), 171))
    return ''.join(out)


BIX_SCENE_E = dict(head_tilt=5, turn=0.66, lid=(0.30, 0.30), lid_tilt=(-4, -4), gaze=(1.0, 0.05), pupil_vis=0.55,
                   brow_raise=(-2, 26), brow_arch=(0.04, 0.24), brow_tilt=(4, -8), nose_tilt=8, mouth='curl')
GUS_SCENE_E = dict(head_tilt=-6, eye_scale=(1.10, 1.10), gaze_lr=((1.0, 0.75), (-1.0, 0.75)), pupil_r=7,
                   brow_raise=(20, 26), brow_arch=(0.16, 0.16), brow_tilt=(-6, -10), flush=True, tip_flush=True, bead=True,
                   mouth='o')
WIT_SCENE_E = dict(gaze=(-1, 0.3), lid=(0.55, 0.55), pupil_vis=0.85, brow_gap=6, brow_raise=(10, 0), brow_arch=(0.14, 0.02),
                   brow_tilt=(-6, 4))


def head_box(f):
    return (f.cx - f.hw / 2 - f.hh * 0.06, f.cy - f.hh / 2 - f.hh * 0.16, f.cx + f.hw / 2 + f.hh * 0.06, f.cy + f.hh / 2)


def union(*bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def jbox(J, pad=12):
    b = bbox_of(J)
    return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)


def shrub_floor(dx, dy):
    return f'<g transform="translate({dx} {dy})">{shrub()}</g>'


def build_scene(bix_x=300, gus_x=815, show=False):
    W, H = 1080, 1920
    FL = 1600
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{common_defs()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    out.append(floor2())
    out.append(window2())
    out.append(awning())
    out.append(small_table(178, 1302, 58, CLOTH, 81))
    out.append(shrub_floor(-14, 760))
    # ---- witness behind the window, newspaper lowered to the nose
    wit = wit_head(992, 556, 240, -0.74)
    out.append(wit.draw(WIT_SCENE_E))
    nx0, ny0, nx1, ny1 = 874, 612, 1086, 800
    out.append(newspaper(nx0, ny0, nx1, ny1))
    wb = Stick(240, -1, plate=CYAN, glove='#C99A72', seed=600)
    for k, (x, y, a, sd) in enumerate(((892, 652, 180, 1), (1062, 656, 180, -1))):
        mp = wb.mitten_pts((x, y), a, 1.0)
        out.append(inked(mp, '#C99A72', (3, 4.5), 610 + k))
        tp = wb.thumb_pts((x, y), a, sd, 1.0, 0.62, 78)
        out.append(inked(tp, '#C99A72', (2.5, 4), 620 + k))

    # ---- BIX: arabesque on his left toe, cup carried far left on a flat glove
    bE = dict(BIX_SCENE_E)
    bix_fn = lambda x, y: bix_head(x, y, 320, bE['turn'])
    bb = bix_body(320, -1)
    bpose = dict(neck=4, spine=8, bow=-0.02,
                 nWr=(-0.565, -0.17), nbend=-1, nhand=-90, ngrip='flat', nthumb=-1, nthumb_at=0.55,
                 fup=26, flo=-90, flo_k=0.30, fgrip='none',
                 nth=-4, nsh=5, ntoe=-12, nsole=-1,
                 fth=101, fsh=101, ftoe=103, fsole=-1, fleg_k=0.82)
    bix, bJ = place(bix_fn, bE, bb, bpose, bix_x, FL, 'n')
    # ---- GUS: lunge on tiptoe into where the cup was
    gE = dict(GUS_SCENE_E)
    gus_fn = lambda x, y: gus_head(x, y, 340, -0.85)
    gb = gus_body(340, -1)
    gpose = dict(neck=22, spine=26, bow=0.07,
                 nWr=(-0.78, -0.35), nbend=-1, ngrip='pinch', nthumb=1, nhand=-125,
                 fWr=(0.48, -0.12), fbend=1, fhand=150,
                 nth=-22, nsh=4, ntoe=-24, nsole=-1,
                 fth=8, fsh=176, ftoe=96, fsole=-1)
    gus, gJ = place(gus_fn, gE, gb, gpose, gus_x, FL, 'n')
    gE['marks'] = [('sweat', gus.cx - gus.hw * 0.12, gus.cy - gus.hh * 0.60, 30, -20),
                   ('sweat', gus.cx - gus.hw * 0.44, gus.cy - gus.hh * 0.48, 24, -48)]

    # cast shadows
    out.append(ht_ellipse(bJ['nF'][0] - 10, FL + 8, 130, 16, INK, 10, 3.4))
    out.append(ht_ellipse(gJ['nF'][0] + 10, FL + 8, 140, 16, INK, 10, 3.4))

    cup_b = (bJ['nW'][0] - 22, bJ['nW'][1] - 4)        # saucer bottom on the flat glove
    dn_c = (gJ['nW'][0] - 30, gJ['nW'][1] + 20)
    # ---- the cup's trail: a level strobe of halftone ghosts zipping left behind Bix's head
    gs = 0.55
    gy = dn_c[1] + 0.64 * 40 - 4 + 119 * gs          # newest ghost's rim sits just under the dunking doughnut
    ghosts = [(dn_c[0] + 6, gy, 0.70), (dn_c[0] - 108, gy - 4, 0.88), (dn_c[0] - 214, gy - 8, 1.0)]
    trail = ''
    for k, (x, y) in enumerate(((dn_c[0] + 80, gy - 52), (dn_c[0] + 66, gy - 30), (dn_c[0] + 84, gy - 8))):
        trail += stroke([(x, y), (x + 70 + 10 * k, y)], 5, taper=(0.85, 0.1), wmin=0.2)
    trail += ''.join(cup_ghost(x, y, gs, op) for x, y, op in ghosts)
    for k, y in enumerate((cup_b[1] - 52, cup_b[1] - 22)):        # speed lines on the far side, into the real cup
        trail += stroke([(cup_b[0] + 92, y), (cup_b[0] + 150 - 20 * k, y)], 5, taper=(0.1, 0.85), wmin=0.2)
    out.append(trail)

    # GUS
    tie = necktie(gJ['S'], -42, 0.40 * 340, 0.155 * 340, 520, bend=-0.12)
    dn = held_doughnut(dn_c[0], dn_c[1], 0.64, -18)
    gspeed = ''.join(stroke([(gJ['H'][0] + 40 + 14 * k, gJ['H'][1] - 200 + 42 * k), (gJ['H'][0] + 118 + 14 * k, gJ['H'][1] - 200 + 42 * k)], 5, taper=(0.1, 0.8)) for k in range(3))
    out.append(figure(gus, gE, gb, gJ, front=tie, prop=dn, marks=gspeed))

    # BIX
    ap = apron(bJ['H'], bpose['spine'], 320, 40, 74, 430, -1, length=0.92, wb=0.26, flutter=0.035, tails=72)
    bt = bow_tie(padd(bJ['S'], D(bpose['neck']), -0.02 * 320), bpose['neck'], 0.26 * 320, 440, squash=0.82)
    cp = cup(cup_b[0], cup_b[1], 0.66, 0, bulge=True)
    out.append(figure(bix, bE, bb, bJ, back=ap, front=bt, prop=cp))
    out.append(grain(W, H))
    out.append('</svg>')
    info = dict(bix=(bix.cx, bix.cy), gus=(gus.cx, gus.cy), cup=cup_b, dn=dn_c,
                bJ={k: bJ[k] for k in ('A', 'S', 'H', 'nE', 'nW', 'fW', 'nF', 'fF')},
                gJ={k: gJ[k] for k in ('A', 'S', 'H', 'nE', 'nW', 'fW', 'nF', 'fF')})
    return ''.join(out), info


# ================================================================ POSES SHEET
E_READY = dict(turn=0.35, gaze=(0.0, 0.1))
E_SMUG = dict(turn=-0.38, head_tilt=-5, lid=(0.30, 0.30), lid_tilt=(-4, -4), gaze=(0.45, 0.05), pupil_vis=0.55,
              brow_raise=(26, -2), brow_arch=(0.24, 0.04), brow_tilt=(-8, 4), nose_tilt=10, mouth='curl')
E_PANIC = dict(turn=0.18, head_tilt=3, eye_scale=(1.32, 1.32), eye_push=6, pupil_r=6.5,
               brow_raise=(18, 18), brow_arch=(0.14, 0.14), brow_tilt=(-24, -24), hair_up=1.0, mouth='wavy')
CUP_S = 0.46


def pose_ready(hh, x, FL, build=True):
    E = dict(E_READY)
    fn = lambda cx, cy: bix_head(cx, cy, hh, E['turn'])
    b = bix_body(hh, 1)
    p = dict(neck=0, spine=-1, bow=0.0,
             nWr=(0.40, -0.10), nbend=1, nhand=90, ngrip='flat', nthumb=1, nthumb_at=0.55,
             fup=-14, flo=90, flo_k=0.30, fgrip='none',
             nth=4, nsh=-3, ntoe=104, nsole=1,
             fth=1, fsh=-4, ftoe=-70, fsole=-1)
    f, J = place(fn, E, b, p, x, FL, 'n')
    s = CUP_S
    cb = (J['nW'][0] + 14, J['nW'][1] - 3)
    box = union(head_box(f), jbox(J), (cb[0] - 124 * s, cb[1] - 200 * s, cb[0] + 124 * s, cb[1]))
    if not build:
        return box
    ap = apron(J['H'], p['spine'], hh, 3, 20, 431, 1, length=0.95, wb=0.26, tails=10)
    bt = bow_tie(padd(J['S'], D(0), -0.02 * hh), 0, 0.26 * hh, 441, squash=0.92)
    c = cup(cb[0], cb[1], s, 0, bulge=True) + steam_small(cb[0], cb[1] - s * 119, 0.34)
    sh = ht_ellipse(J['nF'][0], FL + 6, 84, 10, INK, 9, 3.0)
    return figure(f, E, b, J, back=ap, front=bt, prop=c, shadow=sh), box


def pose_pirouette(hh, x, FL, build=True):
    E = dict(E_SMUG)
    fn = lambda cx, cy: bix_head(cx, cy, hh, E['turn'])
    b = bix_body(hh, -1)
    p = dict(neck=-6, spine=8, bow=-0.03,
             nWr=(-0.50, 0.30), nbend=-1, nhand=-90, ngrip='flat', nthumb=-1, nthumb_at=0.55,
             fWr=(0.56, -0.74), fbend=1, fhand=170, fgrip='mitt', fthumb=1,
             nth=-4, nsh=5, ntoe=-12, nsole=-1,
             fth=101, fsh=101, ftoe=103, fsole=-1, fleg_k=0.86)
    f, J = place(fn, E, b, p, x, FL, 'n')
    s = CUP_S
    cb = (J['nW'][0] - 14, J['nW'][1] - 3)
    box = union(head_box(f), jbox(J), (cb[0] - 124 * s - 10, cb[1] - 200 * s, cb[0] + 124 * s, cb[1]))
    if not build:
        return box
    S = J['S']
    gh = [(S[0] + 0.92 * hh, cb[1] - 0.06 * hh, 0.50), (S[0] + 0.58 * hh, cb[1] - 0.03 * hh, 0.70), (S[0] + 0.24 * hh, cb[1], 0.88)]
    trail = ''.join(cup_ghost(gx, gy, s * 0.92, op) for gx, gy, op in gh)
    for k in range(3):
        y = cb[1] - 0.06 * hh - 0.09 * hh * k
        trail += stroke([(S[0] + 1.06 * hh - 0.04 * hh * k, y - 0.08 * hh), (S[0] + 1.20 * hh, y - 0.10 * hh)], 4.5, taper=(0.85, 0.1), wmin=0.2)
    ap = apron(J['H'], p['spine'], hh, 40, 76, 432, -1, length=0.92, wb=0.26, flutter=0.04, tails=74)
    bt = bow_tie(padd(S, D(p['neck']), -0.02 * hh), p['neck'], 0.26 * hh, 442, squash=0.84)
    c = cup(cb[0], cb[1], s, 0, bulge=True)
    sh = ht_ellipse(J['nF'][0], FL + 6, 74, 10, INK, 9, 3.0)
    return figure(f, E, b, J, back=ap, front=bt, prop=c, shadow=sh + trail), box


def pose_panic(hh, x, FL, build=True):
    E = dict(E_PANIC)
    fn = lambda cx, cy: bix_head(cx, cy, hh, E['turn'])
    b = bix_body(hh, 1)
    p = dict(neck=4, spine=-8, bow=0.08,
             nWr=(0.40, 0.40), nbend=1, nhand=96, ngrip='flat', nthumb=1, nthumb_at=0.5,
             fWr=(0.24, 0.44), fbend=1, fhand=92, fgrip='flat', fthumb=1, fthumb_at=0.5,
             nth=58, nsh=10, ntoe=-78, nsole=-1,
             fth=50, fsh=-32, ftoe=80, fsole=1)
    f, J = place(fn, E, b, p, x, FL, 'n')
    s = CUP_S
    cb = lerp(J['nW'], J['fW'], 0.5); cb = (cb[0] + 0.03 * hh, cb[1] - 4)
    box = union(head_box(f), jbox(J), (cb[0] - 124 * s, cb[1] - 220 * s, cb[0] + 124 * s + 10, cb[1]),
                (f.cx - f.hw * 0.66 - 20, f.cy - f.hh * 0.5, f.cx + f.hw * 0.64 + 20, f.cy))
    if not build:
        return box
    E['gaze_lr'] = ((0.9, 1.0), (0.2, 1.0))
    E['marks'] = [('sweat', f.cx - f.hw * 0.66, f.cy - f.hh * 0.30, 24, -35), ('sweat', f.cx + f.hw * 0.64, f.cy - f.hh * 0.42, 27, 40)]
    ap = apron(J['H'], p['spine'], hh, 34, 24, 433, 1, length=0.56, wb=0.26, tails=-30)
    bt = bow_tie(padd(J['S'], D(p['neck']), -0.02 * hh), p['neck'], 0.26 * hh, 443, squash=0.94)
    c = cup(cb[0], cb[1], s, 12, drop_up=22)
    sh = ht_ellipse((J['nF'][0] + J['fF'][0]) / 2, FL + 6, 100, 10, INK, 9, 3.0)
    return figure(f, E, b, J, back=ap, front=bt, prop=c, shadow=sh), box


TUCK = 0.20


def build_poses(hh=None):
    W = H = 1080
    FL = 958
    M = 20
    fns = (pose_ready, pose_pirouette, pose_panic)
    if hh is None:                               # largest head that lets the three poses sit side by side
        hh = 280
        while hh > 150:
            tot = sum(b[2] - b[0] for b in (fn(hh, 0, FL, False) for fn in fns)) - TUCK * hh
            if tot <= W - 2 * M - 2 * 16:
                break
            hh -= 2
    boxes = [fn(hh, 0, FL, False) for fn in fns]
    gap = (W - 2 * M - sum(b[2] - b[0] for b in boxes) + TUCK * hh) / 2
    xs = []; cur = M
    for i, b in enumerate(boxes):
        xs.append(cur - b[0]); cur += (b[2] - b[0]) + gap - (TUCK * hh if i == 1 else 0)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<defs>{common_defs()}</defs>', f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    out.append(ht_fade(0, 960, 1080, 1080, CYAN, pitch=10, rmax=3.0, rmin=0.3, power=1.0))
    out.append(stroke([(20, 960), (1060, 960)], 4, color=CYAN, taper=(0.02, 0.02)))
    real = []
    for fn, x in zip(fns, xs):
        svg, box = fn(hh, x, FL, True)
        out.append(svg); real.append(box)
    out.append(grain(W, H))
    out.append('</svg>')
    return ''.join(out), real, hh


def steam_small(cx, rim_y, s):
    return f'<g transform="translate({f1(cx)} {f1(rim_y)}) scale({s})">{steam(0, 0)}</g>'


# ================================================================ expression sheet ('!' removed)
SHEET2 = [(n, dict(E)) for n, E in F.SHEET]
SHEET2[1][1]['marks'] = [('emanata', 150), ('sweat', 300, 70, 26, 30), ('sweat', 62, 76, 22, -30)]


def build_faces():
    F.SHEET[:] = SHEET2
    return F.build_faces()


if __name__ == '__main__':
    svg, info = build_scene()
    with open(os.path.join(HERE, 'scene.svg'), 'w') as f:
        f.write(svg)
    svg2, boxes, hh = build_poses()
    with open(os.path.join(HERE, 'poses.svg'), 'w') as f:
        f.write(svg2)
    with open(os.path.join(HERE, 'faces.svg'), 'w') as f:
        f.write(build_faces())
    r = lambda v: [round(c) for c in v]
    print('scene', {k: (r(v) if not isinstance(v, dict) else {a: r(b) for a, b in v.items()}) for k, v in info.items()})
    print('poses hh', round(hh, 1), [r(b) for b in boxes])
