#!/usr/bin/env python3
"""Tall Order, stick-body version.

The head rig (Rig class, characters, POSES, resolve, collar) is the original
Tall Order face rig copied unchanged.  Below it, a stick-body rig hangs a
body from each head's neck pivot: a frame = body(pose dict) + head(face dict).
"""
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- palette
EMERALD = '#1F5C4A'
EMERALD_D = '#12302B'
FLOOR_D = '#163F34'
GOLD = '#C9A24B'
IVORY = '#F3EDE0'
INK = '#161616'
SALMON = '#E59A7E'
SKIN_H = '#E8B996'   # Hasty
SKIN_L = '#B07A55'   # Mr. Level
SKIN_C = '#6E4632'   # clerk
COAT = '#24211F'     # tailcoat (a hair lighter than brow ink)
TRAY = '#C9C4B8'
TEA = '#8A4B2A'
MOUTH_IN = '#3A1E1A'

_uid = [0]


def uid(p='id'):
    _uid[0] += 1
    return f'{p}{_uid[0]}'


def shade(hx, f):
    """darken hex colour by fraction f (0.12 = 12 % darker)."""
    hx = hx.lstrip('#')
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    k = 1 - f
    return '#%02X%02X%02X' % (round(r * k), round(g * k), round(b * k))


def mix(a, b, t):
    a = a.lstrip('#'); b = b.lstrip('#')
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def f(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


# ---------------------------------------------------------------- face rig
class Rig:
    """Proportions of one character's head.  draw(cx, cy, pose) -> svg."""

    def __init__(self, W, H, skin, radius=20, hair='side', hair_color=INK,
                 eye_sep=54, eye_frac=0.46, eye_w=12, eye_h=40,
                 brow_w=80, brow_h=26, brow_gap=24, brow_out=19,
                 brow_color=INK, mouth_frac=0.76, mouth_w=54, mouth_th=9,
                 hair_frac=0.15, ears=True, mustache=False, shadow_w=None,
                 scale=1.0):
        self.__dict__.update(locals())
        del self.__dict__['self']
        if shadow_w is None:
            self.shadow_w = round(W * 0.2)
        self.eye_y = -H / 2 + eye_frac * H
        self.brow_y = self.eye_y - eye_h / 2 - brow_gap - brow_h / 2
        self.mouth_y = -H / 2 + mouth_frac * H

    # -- pieces -------------------------------------------------------
    def head(self, pose, clip):
        W, H, r = self.W, self.H, self.radius
        skin = shade(self.skin, pose.get('darken', 0))
        out = []
        if self.ears:
            ew, eh = 18 * self.scale, 36 * self.scale
            ey = -H / 2 + 0.47 * H - eh / 2
            out.append(f'<rect x="{f(-W/2-ew*0.6)}" y="{f(ey)}" width="{f(ew)}" height="{f(eh)}" rx="{f(ew/2)}" fill="{skin}"/>')
            out.append(f'<rect x="{f(W/2-ew*0.4)}" y="{f(ey)}" width="{f(ew)}" height="{f(eh)}" rx="{f(ew/2)}" fill="{shade(skin,0.12)}"/>')
        out.append(f'<clipPath id="{clip}"><rect x="{f(-W/2)}" y="{f(-H/2)}" width="{f(W)}" height="{f(H)}" rx="{f(r)}"/></clipPath>')
        out.append(f'<rect x="{f(-W/2)}" y="{f(-H/2)}" width="{f(W)}" height="{f(H)}" rx="{f(r)}" fill="{skin}"/>')
        sw = self.shadow_w
        out.append(f'<rect clip-path="url(#{clip})" x="{f(W/2-sw)}" y="{f(-H/2)}" width="{f(sw)}" height="{f(H)}" fill="{shade(skin,0.12)}"/>')
        if self.hair == 'tufts':
            out.append(self.hair_svg(clip))
        else:
            out.append(f'<g clip-path="url(#{clip})">' + self.hair_svg(clip) + '</g>')
        return '\n'.join(out)

    def hair_svg(self, clip):
        W, H = self.W, self.H
        top = -H / 2 - 4
        hb = -H / 2 + self.hair_frac * H
        c = self.hair_color
        if self.hair == 'side':
            nx = -W * 0.18               # side-part notch
            d = (f'M{f(-W/2-2)},{f(top)} L{f(W/2+2)},{f(top)} L{f(W/2+2)},{f(hb+8)} '
                 f'Q{f(W*0.1)},{f(hb-2)} {f(nx+6)},{f(hb-3)} '
                 f'L{f(nx-3)},{f(hb-self.hair_frac*H*0.72)} L{f(nx-3)},{f(hb+1)} '
                 f'Q{f(-W*0.36)},{f(hb+4)} {f(-W/2-2)},{f(hb+14)} Z')
            sheen = (f'<path clip-path="url(#{clip})" d="M{f(nx+22)},{f(top+self.hair_frac*H*0.45)} '
                     f'Q{f(W*0.12)},{f(top+self.hair_frac*H*0.25)} {f(W*0.36)},{f(top+self.hair_frac*H*0.5)}" '
                     f'stroke="{IVORY}" stroke-opacity="0.16" stroke-width="{f(6*self.scale)}" fill="none" stroke-linecap="round"/>')
            hs = (f'<clipPath id="{clip}h"><path d="{d}"/></clipPath>'
                  f'<rect clip-path="url(#{clip}h)" x="{f(W/2-self.shadow_w)}" y="{f(top)}" width="{f(self.shadow_w+4)}" height="{f(H*0.4)}" fill="{shade(c,0.12)}"/>')
            return f'<path clip-path="url(#{clip})" d="{d}" fill="{c}"/>' + hs
        if self.hair == 'slick':          # centre part, sideburns, shine
            d = (f'M{f(-W/2-2)},{f(top)} L{f(W/2+2)},{f(top)} L{f(W/2+2)},{f(hb+H*0.18)} '
                 f'L{f(W/2-W*0.05)},{f(hb+H*0.18)} L{f(W/2-W*0.06)},{f(hb+4)} '
                 f'Q{f(W*0.2)},{f(hb-6)} {f(4)},{f(hb-H*0.06)} L0,{f(hb+2)} L{f(-4)},{f(hb-H*0.06)} '
                 f'Q{f(-W*0.2)},{f(hb-6)} {f(-W/2+W*0.06)},{f(hb+4)} '
                 f'L{f(-W/2+W*0.05)},{f(hb+H*0.18)} L{f(-W/2-2)},{f(hb+H*0.18)} Z')
            shine = ''.join(
                f'<path clip-path="url(#{clip})" d="M{f(s*W*0.12)},{f(top+H*0.05)} Q{f(s*W*0.3)},{f(top+H*0.03)} {f(s*W*0.42)},{f(top+H*0.09)}" '
                f'stroke="{IVORY}" stroke-opacity="0.22" stroke-width="{f(5*self.scale)}" fill="none" stroke-linecap="round"/>'
                for s in (-1, 1))
            return f'<path clip-path="url(#{clip})" d="{d}" fill="{c}"/>' + shine
        if self.hair == 'tufts':          # bald, white side tufts
            t = []
            for s in (-1, 1):
                x0 = s * W / 2
                t.append(f'<path d="M{f(x0 - s*2)},{f(-H*0.18)} Q{f(x0 + s*W*0.16)},{f(-H*0.2)} {f(x0 + s*W*0.12)},{f(-H*0.02)} '
                         f'Q{f(x0 + s*W*0.08)},{f(H*0.04)} {f(x0 - s*2)},{f(H*0.0)} Z" fill="{c}"/>')
            return ''.join(t)
        return ''

    def brow_xy(self, side, b):
        s = -1 if side == 'L' else 1
        bx = s * (self.eye_sep / 2 + self.brow_out) + b.get('dx', 0)
        by = self.brow_y + b.get('dy', 0)
        return bx, by

    def brow(self, side, b, color):
        if b is None:
            return ''
        s = -1 if side == 'L' else 1
        w = b.get('w', self.brow_w)
        h = b.get('h', self.brow_h)
        bx, by = self.brow_xy(side, b)
        tilt = b.get('tilt', 0)            # + = inner end down
        rdeg = tilt if side == 'L' else -tilt
        out = []
        # motion trail from rest position up to the brow
        if b.get('trail'):
            rest_y = self.brow_y
            n = 3
            top = by + h / 2 + 10
            hair_bot = -self.H / 2 + (self.hair_frac * self.H if self.hair in ('side', 'slick') else 0) - 6
            bot = hair_bot if b.get('trail_to_rest') else top + b.get('trail_len', 70)
            seg = (bot - top) / n
            for i in range(n):
                y0 = top + i * seg + seg * 0.18
                y1 = y0 + seg * 0.5
                out.append(f'<line x1="{f(bx)}" y1="{f(y0)}" x2="{f(bx)}" y2="{f(y1)}" stroke="{color}" '
                           f'stroke-width="{f(5*self.scale)}" stroke-linecap="round" opacity="{f(0.75-0.2*i)}"/>')
        for g in b.get('ghosts', []):
            gx, gy, gt = (g + (0,))[:3] if len(g) < 3 else g
            gr = (tilt + gt) if side == 'L' else -(tilt + gt)
            out.append(f'<rect x="{f(-w/2)}" y="{f(-h/2)}" width="{f(w)}" height="{f(h)}" rx="{f(h/2)}" fill="{color}" opacity="0.3" '
                       f'transform="translate({f(bx+gx)},{f(by+gy)}) rotate({f(gr)})"/>')
        out.append(f'<rect x="{f(-w/2)}" y="{f(-h/2)}" width="{f(w)}" height="{f(h)}" rx="{f(h/2)}" fill="{color}" '
                   f'transform="translate({f(bx)},{f(by)}) rotate({f(rdeg)})"/>')
        nt = b.get('ticks', 0)
        if nt:
            tx, ty = rot(s * w / 2, 0, rdeg)
            tx += bx; ty += by
            base = 0 if s > 0 else 180
            base_angs = b.get('tick_angles', [-20, -55, 15])
            angs = base_angs[:nt] if s > 0 else [-a for a in base_angs][:nt]
            angs = [base + a if s > 0 else base - a for a in angs]
            angs = [a + rdeg for a in angs]
            op = b.get('tick_op', 1)
            for i, a in enumerate(angs):
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                d0, d1 = 12 * self.scale, 30 * self.scale
                out.append(f'<line x1="{f(tx+ca*d0)}" y1="{f(ty+sa*d0)}" x2="{f(tx+ca*d1)}" y2="{f(ty+sa*d1)}" stroke="{color}" '
                           f'stroke-width="{f(5*self.scale)}" stroke-linecap="round" opacity="{f(op*(1-0.35*i))}"/>')
        return '\n'.join(out)

    def eyes(self, e):
        st = e.get('state', 'dash')
        dx, dy = e.get('dx', 0), e.get('dy', 0)
        sep = e.get('sep', self.eye_sep)
        out = []
        for s in (-1, 1):
            x = s * sep / 2 + dx
            y = self.eye_y + dy
            for gx, gy in e.get('ghosts', []):
                out.append(self._eye(st, x + gx, y + gy, e, op=0.3))
            out.append(self._eye(st, x, y, e))
        return '\n'.join(out)

    def _eye(self, st, x, y, e, op=1.0):
        o = '' if op == 1 else f' opacity="{op}"'
        if st == 'dash':
            w = e.get('w', self.eye_w); h = e.get('h', self.eye_h)
            lid = e.get('lid', 0)              # fraction trimmed flat from top
            if lid:
                y0 = y - h / 2 + lid * h
                r = w / 2
                d = (f'M{f(x-w/2)},{f(y0)} L{f(x+w/2)},{f(y0)} L{f(x+w/2)},{f(y+h/2-r)} '
                     f'A{f(r)},{f(r)} 0 0 1 {f(x-w/2)},{f(y+h/2-r)} Z')
                return f'<path d="{d}" fill="{INK}"{o}/>'
            return f'<rect x="{f(x-w/2)}" y="{f(y-h/2)}" width="{f(w)}" height="{f(h)}" rx="{f(w/2)}" fill="{INK}"{o}/>'
        if st == 'dot':
            r = e.get('size', 18 * self.scale) / 2
            return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{INK}"{o}/>'
        if st == 'open':
            R = e.get('size', 44 * self.scale) / 2
            px, py = e.get('pupil', (0, 0))
            return (f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(R)}" fill="#FFFFFF"{o}/>'
                    f'<circle cx="{f(x+px)}" cy="{f(y+py)}" r="{f(7*self.scale)}" fill="{INK}"{o}/>')
        return ''

    def mouth(self, m):
        t = m.get('type', 'flat')
        x = m.get('dx', 0)
        y = self.mouth_y + m.get('dy', 0)
        w = m.get('w', self.mouth_w)
        th = m.get('th', self.mouth_th)
        st = f'stroke="{INK}" stroke-width="{f(th)}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
        if t == 'flat':
            return f'<line x1="{f(x-w/2)}" y1="{f(y)}" x2="{f(x+w/2)}" y2="{f(y)}" {st}/>'
        if t == 'curl':                     # one end turns up
            c = m.get('curl', 12 * self.scale)
            s = 1 if m.get('side', 'R') == 'R' else -1
            a, b = x - s * w / 2, x + s * w / 2
            k = x + s * w * 0.22
            return (f'<path d="M{f(a)},{f(y)} L{f(k)},{f(y)} Q{f(b)},{f(y)} {f(b + s*2)},{f(y-c)}" {st}/>')
        if t == 'o':
            rx = m.get('rx', 11 * self.scale); ry = m.get('ry', rx)
            return f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rx)}" ry="{f(ry)}" stroke="{INK}" stroke-width="{f(th*0.8)}" fill="{MOUTH_IN}"/>'
        if t == 'zig':
            a = m.get('amp', 8 * self.scale)
            pts = [(x - w / 2, y), (x - w / 4, y - a), (x, y + a), (x + w / 4, y - a), (x + w / 2, y)]
            return f'<polyline points="{" ".join(f(px)+","+f(py) for px,py in pts)}" {st}/>'
        if t == 'frown':
            a = m.get('amp', 14 * self.scale)
            return f'<path d="M{f(x-w/2)},{f(y+a*0.5)} Q{f(x)},{f(y-a*1.3)} {f(x+w/2)},{f(y+a*0.5)}" {st}/>'
        if t == 'take':
            W2, H2 = m.get('w', 100), m.get('h', 40)
            return (f'<rect x="{f(x-W2/2)}" y="{f(y-H2/2)}" width="{f(W2)}" height="{f(H2)}" rx="8" fill="{MOUTH_IN}"/>'
                    f'<rect x="{f(x-W2/2+6)}" y="{f(y-H2/2+4)}" width="{f(W2-12)}" height="{f(H2*0.28)}" rx="3" fill="{IVORY}"/>')
        return ''

    def extras(self, pose):
        out = []
        W, H = self.W, self.H
        if self.mustache:
            my = self.mouth_y - H * 0.13
            th = 4 * self.scale
            for s in (-1, 1):
                out.append(f'<path d="M{f(s*6)},{f(my)} Q{f(s*W*0.08)},{f(my+3)} {f(s*W*0.13)},{f(my-5)}" stroke="{INK}" '
                           f'stroke-width="{f(th)}" stroke-linecap="round" fill="none"/>')
        if pose.get('strand'):            # one slick hair sprung loose and wilting
            sx = W * 0.12
            y0 = -H / 2 + 4
            out.append(f'<path d="M{f(sx)},{f(y0)} C{f(sx+2)},{f(y0-50)} {f(sx+46)},{f(y0-58)} {f(sx+56)},{f(y0-8)}" '
                       f'stroke="{self.hair_color}" stroke-width="{f(6*self.scale)}" stroke-linecap="round" fill="none"/>')
        if pose.get('sweat'):
            sx, sy = pose['sweat']
            r = 9 * self.scale
            out.append(f'<path d="M{f(sx)},{f(sy-r*2.4)} Q{f(sx+r*1.1)},{f(sy-r*0.4)} {f(sx+r)},{f(sy+r*0.2)} '
                       f'A{f(r)},{f(r)} 0 1 1 {f(sx-r)},{f(sy+r*0.2)} Q{f(sx-r*1.1)},{f(sy-r*0.4)} {f(sx)},{f(sy-r*2.4)} Z" fill="{IVORY}"/>')
        if pose.get('gloom'):
            for i, gx in enumerate((-W * 0.22, 0, W * 0.22)):
                y0 = -H / 2 - 62 * self.scale
                out.append(f'<line x1="{f(gx)}" y1="{f(y0)}" x2="{f(gx)}" y2="{f(y0+38*self.scale)}" stroke="{INK}" '
                           f'stroke-width="{f(5*self.scale)}" stroke-linecap="round" opacity="0.55"/>')
        return '\n'.join(out)

    # -- whole head ---------------------------------------------------
    def draw(self, cx, cy, pose):
        clip = uid('hc')
        color = pose.get('brow_color', self.brow_color)
        parts = [self.head(pose, clip),
                 self.eyes(pose.get('eyes', {})),
                 self.mouth(pose.get('mouth', {})),
                 self.extras(pose),
                 self.brow('L', pose.get('browL', {}), color),
                 self.brow('R', pose.get('browR', {}), color)]
        r = pose.get('rot', 0)
        return f'<g transform="translate({f(cx)},{f(cy)}) rotate({f(r)})">\n' + '\n'.join(parts) + '\n</g>'


# ---------------------------------------------------------------- characters
SILVER = '#A8A299'
LEVEL_SHEET = Rig(170, 290, SKIN_L, radius=20, hair='side', hair_color=SILVER,
                  brow_w=70, brow_out=11, shadow_w=35)
LEVEL_SCENE = Rig(200, 340, SKIN_L, radius=24, hair='side', hair_color=SILVER, eye_sep=64,
                  eye_w=13, eye_h=44, brow_w=96, brow_h=32, brow_gap=26, brow_out=18,
                  mouth_w=58, mouth_th=10, scale=1.15, shadow_w=40)
HASTY = Rig(300, 215, SKIN_H, radius=30, hair='slick', eye_sep=96, eye_frac=0.56, eye_w=13, eye_h=36,
            brow_w=120, brow_h=30, brow_gap=14, brow_out=26, mouth_frac=0.85, mouth_w=44,
            mouth_th=8, hair_frac=0.13, mustache=True, scale=1.1, shadow_w=60)
CLERK = Rig(78, 110, SKIN_C, radius=12, hair='tufts', hair_color=IVORY, eye_sep=24, eye_frac=0.48,
            eye_w=6, eye_h=16, brow_w=30, brow_h=10, brow_gap=8, brow_out=6, brow_color=IVORY,
            mouth_w=20, mouth_th=5, scale=0.42, shadow_w=16)

# expression sheet poses (MR. LEVEL)
POSES = [
    # 1 neutral
    dict(),
    # 2 surprised: brows fly above head, dot eyes, tall o
    dict(eyes=dict(state='dot', size=18),
         browL=dict(dy=None, trail=True, trail_to_rest=True),
         browR=dict(dy=None, trail=True, trail_to_rest=True),
         mouth=dict(type='o', rx=13, ry=20, dy=4)),
    # 3 angry: steep V touching dashes, darker head
    dict(darken=0.10,
         browL=dict(dx=6, dy=None, tilt=30, ticks=2),
         browR=dict(dx=-6, dy=None, tilt=30, ticks=2),
         mouth=dict(type='frown')),
    # 4 smug
    dict(browL=dict(dy=-40, tilt=-10),
         browR=dict(dy=6),
         mouth=dict(type='curl', dx=34, side='R')),
    # 5 panic
    dict(eyes=dict(ghosts=[(-6, -3), (6, 3)]),
         browL=dict(dy=-26, tilt=-24, ghosts=[(-5, -6, -6), (5, 6, 6)]),
         browR=dict(dy=-6, tilt=-24, ghosts=[(5, -6, -6), (-5, 6, 6)]),
         mouth=dict(type='zig', w=60),
         sweat=(98, -40)),
    # 6 exasperated side-eye
    dict(eyes=dict(dx=44, lid=0.38, w=15),
         browL=dict(dy=14, dx=12),
         browR=dict(dy=14, dx=12),
         mouth=dict(type='flat', dx=-20),
         gloom=True),
]


def resolve(rig, pose):
    """fill in brow dy values that depend on rig geometry."""
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in pose.items()}
    head_top = -rig.H / 2
    for side in ('browL', 'browR'):
        b = p.get(side)
        if b is None or b.get('dy', 0) is not None:
            continue
        if p.get('darken'):        # angry: bottom edge touches top of dashes
            b['dy'] = (rig.eye_y - rig.eye_h / 2 - rig.brow_h / 2 + 4) - rig.brow_y
        else:                      # surprised: bottom edge 30 px above head top
            b['dy'] = (head_top - 30 - rig.brow_h / 2) - rig.brow_y
    return p


# ---------------------------------------------------------------- shared svg bits
def grain(w, h, op=0.04):
    fid = uid('gr')
    return (f'<filter id="{fid}" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="7"/>'
            f'<feColorMatrix type="saturate" values="0"/></filter>'
            f'<rect width="{w}" height="{h}" filter="url(#{fid})" opacity="{op}" style="mix-blend-mode:multiply"/>')


def lamp(cx, cy, rx, ry, op):
    gid = uid('lp')
    return (f'<radialGradient id="{gid}"><stop offset="0" stop-color="{IVORY}" stop-opacity="{op}"/>'
            f'<stop offset="0.55" stop-color="{IVORY}" stop-opacity="{op*0.6}"/>'
            f'<stop offset="1" stop-color="{IVORY}" stop-opacity="0"/></radialGradient>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{gid})"/>')


def svg_doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'{body}\n</svg>\n')


def collar(cx, y, s=1.0):
    """ivory wing collar + black bow tie centred at (cx, y)."""
    return (f'<path d="M{f(cx-34*s)},{f(y-6*s)} L{f(cx+34*s)},{f(y-6*s)} L{f(cx+30*s)},{f(y+14*s)} L{f(cx)},{f(y+26*s)} L{f(cx-30*s)},{f(y+14*s)} Z" fill="{IVORY}"/>'
            f'<path d="M{f(cx-8*s)},{f(y+2*s)} L{f(cx-22*s)},{f(y+16*s)} L{f(cx-6*s)},{f(y+16*s)} Z" fill="{shade(IVORY,0.12)}"/>'
            f'<path d="M{f(cx)},{f(y+12*s)} L{f(cx-30*s)},{f(y-2*s)} L{f(cx-30*s)},{f(y+26*s)} Z" fill="{INK}"/>'
            f'<path d="M{f(cx)},{f(y+12*s)} L{f(cx+30*s)},{f(y-2*s)} L{f(cx+30*s)},{f(y+26*s)} Z" fill="{INK}"/>'
            f'<rect x="{f(cx-7*s)}" y="{f(y+5*s)}" width="{f(14*s)}" height="{f(14*s)}" rx="{f(3*s)}" fill="{INK}"/>')


# =====================================================================
# STICK-BODY RIG (new).  Everything above this line is the original
# Tall Order head rig, copied unchanged.  A frame = body(pose) + head(face).
# Line language copies the heads: flat fills, no outlines, round pill ends,
# far side one value darker (shade 0.12), light from the left.
# =====================================================================
SALMON_D = shade(SALMON, 0.2)
GLOVE = IVORY
PATENT = '#121212'


def D(deg):
    """unit direction: 0 = down, 90 = right, 180 = up, -90 = left."""
    a = math.radians(deg)
    return math.sin(a), math.cos(a)


def add(p, v, k=1.0):
    return (p[0] + v[0] * k, p[1] + v[1] * k)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def ang_of(a, b):
    """direction angle (same convention as D) from a to b."""
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))


def pstr(pts):
    return ' '.join(f'{f(x)},{f(y)}' for x, y in pts)


def capsule_pts(p1, r1, p2, r2, n=10):
    """tapered capsule (two circles + outer tangents) as a point list."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = max(math.hypot(dx, dy), 1e-4)
    ux, uy = dx / L, dy / L
    s = max(-0.98, min(0.98, (r1 - r2) / L))
    c = math.sqrt(1 - s * s)
    phi = math.atan2(c, s)
    au = math.atan2(uy, ux)
    pts = []
    for i in range(n + 1):
        t = au + phi - 2 * phi * i / n
        pts.append((p2[0] + r2 * math.cos(t), p2[1] + r2 * math.sin(t)))
    m = n + 6
    for i in range(m + 1):
        t = au - phi - (2 * math.pi - 2 * phi) * i / m
        pts.append((p1[0] + r1 * math.cos(t), p1[1] + r1 * math.sin(t)))
    return pts


def capsule(p1, r1, p2, r2, fill, extra=''):
    return f'<polygon points="{pstr(capsule_pts(p1, r1, p2, r2))}" fill="{fill}"{extra}/>'


def ik(root, target, a, b, bend):
    """two-bone IK.  bend=+1 puts the joint on the screen-right of a downward limb."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d0 = max(math.hypot(dx, dy), 1e-4)
    ux, uy = dx / d0, dy / d0
    d = max(min(d0, (a + b) * 0.9995), abs(a - b) + 1e-3)
    x = (a * a - b * b + d * d) / (2 * d)
    h = math.sqrt(max(a * a - x * x, 0))
    px, py = uy * bend, -ux * bend
    j = (root[0] + ux * x + px * h, root[1] + uy * x + py * h)
    e = (root[0] + ux * d, root[1] + uy * d)
    return j, e


def bez2(p0, c, p1, t):
    return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])


def ribbon(p0, c, p1, w0, w1, fill, tip='point', n=14):
    """flat tapered ribbon along a quadratic curve (tails, tie)."""
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        p = bez2(p0, c, p1, t)
        q = bez2(p0, c, p1, min(t + 0.01, 1.0)) if t < 1 else p
        r = bez2(p0, c, p1, max(t - 0.01, 0.0))
        tx, ty = (q[0] - r[0]), (q[1] - r[1])
        L = max(math.hypot(tx, ty), 1e-6)
        nx, ny = -ty / L, tx / L
        w = (w0 + (w1 - w0) * t) / 2
        left.append((p[0] + nx * w, p[1] + ny * w))
        right.append((p[0] - nx * w, p[1] - ny * w))
    end = []
    if tip == 'point':
        q = bez2(p0, c, p1, 0.99)
        tx, ty = p1[0] - q[0], p1[1] - q[1]
        L = max(math.hypot(tx, ty), 1e-6)
        end = [(p1[0] + tx / L * w1 * 0.7, p1[1] + ty / L * w1 * 0.7)]
    elif tip == 'notch':
        q = bez2(p0, c, p1, 0.99)
        tx, ty = p1[0] - q[0], p1[1] - q[1]
        L = max(math.hypot(tx, ty), 1e-6)
        end = [(p1[0] - tx / L * w1 * 0.35, p1[1] - ty / L * w1 * 0.35)]
    pts = left + end + right[::-1]
    return f'<polygon points="{pstr(pts)}" fill="{fill}"/>'


def star4(x, y, r, fill=IVORY, op=1.0):
    k = r * 0.22
    pts = [(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)]
    return f'<polygon points="{pstr(pts)}" fill="{fill}" opacity="{op}"/>'


def ticks(x, y, r0, r1, angs, w=5, color=INK, op=0.6):
    o = []
    for a in angs:
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        o.append(f'<line x1="{f(x+ca*r0)}" y1="{f(y+sa*r0)}" x2="{f(x+ca*r1)}" y2="{f(y+sa*r1)}" '
                 f'stroke="{color}" stroke-width="{w}" stroke-linecap="round" opacity="{op}"/>')
    return ''.join(o)


# ---------------------------------------------------------------- hand props
def tray_cup(tx, ty, s=1.0, tilt_tea=0):
    """silver tray + saucer + brim-full cup.  (tx, ty) = centre of tray top."""
    o = []
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty+6*s)}" rx="{f(108*s)}" ry="{f(19*s)}" fill="{shade(TRAY,0.25)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty)}" rx="{f(108*s)}" ry="{f(18*s)}" fill="{TRAY}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty)}" rx="{f(92*s)}" ry="{f(12*s)}" fill="{mix(TRAY,IVORY,0.35)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty-4*s)}" rx="{f(52*s)}" ry="{f(10*s)}" fill="{shade(IVORY,0.12)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(ty-6*s)}" rx="{f(48*s)}" ry="{f(8*s)}" fill="{IVORY}"/>')
    cw, ch = 46 * s, 58 * s
    top = ty - 6 * s - ch
    o.append(f'<path d="M{f(tx+cw+2*s)},{f(top+12*s)} a{f(15*s)},{f(15*s)} 0 1 1 {f(-3*s)},{f(32*s)}" stroke="{IVORY}" stroke-width="{f(10*s)}" fill="none"/>')
    o.append(f'<path d="M{f(tx-cw)},{f(top)} L{f(tx+cw)},{f(top)} Q{f(tx+cw)},{f(top+ch-6*s)} {f(tx+14*s)},{f(top+ch)} '
             f'L{f(tx-14*s)},{f(top+ch)} Q{f(tx-cw)},{f(top+ch-6*s)} {f(tx-cw)},{f(top)} Z" fill="{IVORY}"/>')
    o.append(f'<path d="M{f(tx+20*s)},{f(top)} L{f(tx+cw)},{f(top)} Q{f(tx+cw)},{f(top+ch-6*s)} {f(tx+14*s)},{f(top+ch)} '
             f'L{f(tx+6*s)},{f(top+ch)} Q{f(tx+28*s)},{f(top+ch-12*s)} {f(tx+20*s)},{f(top)} Z" fill="{shade(IVORY,0.12)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(top)}" rx="{f(cw)}" ry="{f(10*s)}" fill="{shade(IVORY,0.06)}"/>')
    o.append(f'<ellipse cx="{f(tx)}" cy="{f(top)}" rx="{f(cw-3*s)}" ry="{f(8*s)}" fill="{TEA}"/>')
    o.append(f'<path d="M{f(tx-cw+3*s)},{f(top)} Q{f(tx)},{f(top-16*s)} {f(tx+cw-3*s)},{f(top)} Z" fill="{TEA}"/>')
    o.append(f'<ellipse cx="{f(tx-13*s)}" cy="{f(top-5*s)}" rx="{f(9*s)}" ry="{f(3*s)}" fill="{IVORY}" opacity="0.85"/>')
    return '\n'.join(o)


TRAY_BOTTOM = 25      # tray underside below its top-centre, at s=1


# ---------------------------------------------------------------- body rig
class Body:
    """Stick body hung from a head's neck pivot.

    Proportions in HU (head units).  joints(A, pose) -> dict of world points;
    layers(J, pose) -> svg per layer, so a frame is body(pose) + head(face)."""

    def __init__(self, HU, neck_vis, sh_drop=0.15, spine=0.88, leg=1.26, arm=1.1,
                 col=COAT, neck_col=None, hand_col=GLOVE, w_root=20, w_tip=14,
                 spine_w=17, neck_w=16, shoe='oxford', shoe_len=0.19, ankle=0.047,
                 kind='level', ring=False):
        self.HU = HU
        self.neck_vis = neck_vis
        self.sh_drop = sh_drop * HU
        self.spine = spine * HU
        self.ankle = ankle * HU
        lg = leg * HU - self.ankle
        self.thigh = self.shin = lg / 2
        self.uarm = self.farm = arm * HU / 2
        self.col = col
        self.col_far = shade(col, 0.12)
        self.neck_col = neck_col
        self.hand_col = hand_col
        self.r0, self.r2 = w_root / 2, w_tip / 2
        self.r1 = (self.r0 + self.r2) / 2
        self.spine_w, self.neck_w = spine_w, neck_w
        self.shoe = shoe
        self.shoe_len = shoe_len * HU
        self.kind = kind
        self.ring = ring
        self.mit_len = 0.12 * HU
        self.mit_r = max(w_tip * 0.9, 6)

    # -- skeleton ------------------------------------------------------
    def joints(self, A, pose):
        J = {'A': A}
        n = pose.get('neck', 0)
        s = pose.get('lean', 0)
        N = add(A, D(-n), 6 + self.neck_vis)
        hip = add(N, D(-s), self.spine)
        mid = lerp(N, hip, 0.5)
        dn = D(-s)
        perp = (dn[1], -dn[0])            # screen-right of a downward spine
        C = add(mid, perp, pose.get('curve', 0))
        S = bez2(N, C, hip, self.sh_drop / self.spine)
        J.update(N=N, H=hip, C=C, S=S, top=add(A, D(-n), -14))
        for side in ('N', 'F'):
            a = pose.get('arm' + side, {})
            if 'hand' in a:
                E, W = ik(S, a['hand'], self.uarm, self.farm, a.get('bend', 1))
            else:
                E = add(S, D(a.get('a1', 0)), self.uarm * a.get('upper', 1))
                W = add(E, D(a.get('a2', a.get('a1', 0))), self.farm * a.get('fore', 1))
            J['E' + side], J['W' + side] = E, W
            l = pose.get('leg' + side, {})
            if 'foot' in l:
                K, F = ik(hip, l['foot'], self.thigh, self.shin, l.get('bend', 1))
            else:
                K = add(hip, D(l.get('a1', 0)), self.thigh)
                F = add(K, D(l.get('a2', l.get('a1', 0))), self.shin)
            J['K' + side], J['F' + side] = K, F
        return J

    # -- pieces --------------------------------------------------------
    def limb(self, p0, p1, p2, color):
        return (capsule(p0, self.r0, p1, self.r1, color) +
                capsule(p1, self.r1, p2, self.r2, color))

    def mitten(self, W, h, side_col=None):
        """h = hand dict.  kind: mitten | flat | finger | none."""
        kind = h.get('kind', 'mitten')
        if kind == 'none':
            return ''
        col = side_col or self.hand_col
        a = h['ang']
        u = D(a)
        pr = (u[1], -u[0])
        th = h.get('thumb', 1)
        o = []
        cid = uid('mc')
        R = self.mit_r
        if kind == 'flat':
            b = add(W, u, -2)
            t = add(W, u, self.mit_len * 1.05 - R * 0.8)
            shape = capsule_pts(b, R * 0.62, t, R * 0.72)
        elif kind == 'finger' or kind == 'fist':
            b = add(W, u, -1)
            t = add(W, u, R * 0.5)
            shape = capsule_pts(b, R * 0.8, t, R * 0.95)
        else:
            b = add(W, u, -2)
            t = add(W, u, self.mit_len - R)
            shape = capsule_pts(b, R * 0.82, t, R)
        o.append(f'<clipPath id="{cid}"><polygon points="{pstr(shape)}"/></clipPath>')
        o.append(f'<polygon points="{pstr(shape)}" fill="{col}"/>')
        cx = sum(p[0] for p in shape) / len(shape)
        o.append(f'<rect clip-path="url(#{cid})" x="{f(cx + R*0.35)}" y="{f(W[1]-200)}" width="300" height="400" fill="{shade(col,0.12)}"/>')
        if kind == 'finger':
            fd = D(h.get('fdir', a))
            f0 = add(t, fd, R * 0.4)
            f1 = add(f0, fd, self.HU * 0.075)
            o.append(capsule(f0, R * 0.42, f1, R * 0.38, col))
        if self.ring and kind != 'finger':
            rp = add(add(b, pr, -th * R * 0.75), u, R * 0.9)
            o.append(f'<circle cx="{f(rp[0])}" cy="{f(rp[1])}" r="{f(max(R*0.32, 3.5))}" fill="{GOLD}"/>')
        return '\n'.join(o)

    def thumb(self, W, h, col=None):
        if h.get('kind', 'mitten') in ('none',) or h.get('thumb', 1) == 0:
            return ''
        col = col or self.hand_col
        a = h['ang']
        th = h.get('thumb', 1)
        ta = h.get('thumb_ang', a + th * 60)
        u = D(a)
        pr = (u[1], -u[0])
        R = self.mit_r
        b = add(add(W, pr, th * R * 0.55), u, R * 0.35)
        t = add(b, D(ta), R * 1.15)
        return capsule(b, R * 0.42, t, R * 0.36, col) + capsule(b, R * 0.42, t, R * 0.36, shade(col, 0.06), ' opacity="0.5"')

    def shoe_svg(self, F, ft, far=False):
        d = ft.get('dir', 1)
        tilt = ft.get('tilt', 0)
        L = self.shoe_len
        hgt = L * 0.32
        s = self.ankle            # sole below ankle
        o = []
        if self.shoe == 'oxford':
            path = (f'M{f(-0.26*L)},{f(s)} L{f(0.62*L)},{f(s)} Q{f(0.76*L)},{f(s)} {f(0.76*L)},{f(s-hgt*0.42)} '
                    f'Q{f(0.74*L)},{f(s-hgt*0.86)} {f(0.42*L)},{f(s-hgt*0.9)} L{f(0.12*L)},{f(s-hgt*1.06)} '
                    f'Q{f(-0.26*L)},{f(s-hgt*1.12)} {f(-0.26*L)},{f(s-hgt*0.5)} Z')
            col = PATENT if not far else shade(PATENT, 0.0)
            o.append(f'<path d="{path}" fill="{col}"/>')
            o.append(f'<rect x="{f(-0.26*L)}" y="{f(s-hgt*0.22)}" width="{f(0.24*L)}" height="{f(hgt*0.22)}" fill="{INK}"/>')
            o.append(f'<ellipse cx="{f(0.52*L)}" cy="{f(s-hgt*0.66)}" rx="{f(L*0.12)}" ry="{f(hgt*0.14)}" fill="{IVORY}" opacity="0.8"/>')
        else:   # spectator: pointed, ivory body, black toe cap + heel
            cid = uid('sp')
            path = (f'M{f(-0.24*L)},{f(s)} L{f(0.55*L)},{f(s)} Q{f(0.72*L)},{f(s-hgt*0.05)} {f(0.82*L)},{f(s-hgt*0.32)} '
                    f'Q{f(0.6*L)},{f(s-hgt*0.86)} {f(0.3*L)},{f(s-hgt*0.95)} L{f(0.08*L)},{f(s-hgt*1.08)} '
                    f'Q{f(-0.24*L)},{f(s-hgt*1.1)} {f(-0.24*L)},{f(s-hgt*0.5)} Z')
            base = IVORY if not far else shade(IVORY, 0.12)
            o.append(f'<clipPath id="{cid}"><path d="{path}"/></clipPath>')
            o.append(f'<path d="{path}" fill="{base}"/>')
            o.append(f'<path clip-path="url(#{cid})" d="M{f(0.4*L)},{f(s+5)} Q{f(0.36*L)},{f(s-hgt*0.6)} {f(0.5*L)},{f(s-hgt*1.3)} L{f(L)},{f(s-hgt*1.3)} L{f(L)},{f(s+5)} Z" fill="{INK}"/>')
            o.append(f'<path clip-path="url(#{cid})" d="M{f(-0.3*L)},{f(s+5)} L{f(-0.3*L)},{f(s-hgt*1.3)} L{f(-0.06*L)},{f(s-hgt*1.3)} Q{f(-0.12*L)},{f(s-hgt*0.5)} {f(-0.02*L)},{f(s+5)} Z" fill="{INK}"/>')
            o.append(f'<rect x="{f(-0.24*L)}" y="{f(s-2.5)}" width="{f(0.98*L)}" height="2.5" fill="{shade(INK,0)}" opacity="0.5"/>')
        tr = f'translate({f(F[0])},{f(F[1])}) rotate({f(tilt*d)}) scale({d},1)'
        return f'<g transform="{tr}">' + ''.join(o) + '</g>'

    # -- costume props ---------------------------------------------------
    def tails(self, J, pose):
        """swallowtail: one coat panel from the hip that splits into two tails.
        swing = hang angle (lags the body), lag = cloth bend, spread = split depth."""
        t = pose.get('tails', {})
        sw, lag = t.get('swing', 0), t.get('lag', 0)
        H = J['H']
        k = self.HU / 340
        Lt = self.thigh * t.get('len', 1.0)
        p0 = add(H, (0, -16 * k))
        p1 = add(p0, D(sw), Lt)
        c = add(lerp(p0, p1, 0.5), D(sw + 90), lag * Lt / 200)
        w0, w1 = 20 * k * t.get('w', 1), 50 * k * t.get('w', 1)
        split = t.get('split', 0.5)
        n = 16
        L_, R_, M_ = [], [], []
        for i in range(n + 1):
            u = i / n
            p = bez2(p0, c, p1, u)
            q = bez2(p0, c, p1, min(u + 0.01, 1))
            r = bez2(p0, c, p1, max(u - 0.01, 0))
            tx, ty = q[0] - r[0], q[1] - r[1]
            ln = max(math.hypot(tx, ty), 1e-6)
            nx, ny = -ty / ln, tx / ln
            w = (w0 + (w1 - w0) * u) / 2
            L_.append((p[0] + nx * w, p[1] + ny * w))
            R_.append((p[0] - nx * w, p[1] - ny * w))
            M_.append(p)
        apex = M_[int(n * split)]
        # tail tips slightly pointed outward
        tipL = add(L_[-1], D(sw), 6 * k)
        tipR = add(R_[-1], D(sw), 6 * k)
        pts = L_ + [tipL, apex, tipR] + R_[::-1]
        o = [f'<polygon points="{pstr(pts)}" fill="{self.col}"/>']
        # far tail one value darker (depth, like the head's shadow side)
        far = R_[int(n * split):] + [tipR, apex]
        o.append(f'<polygon points="{pstr(far)}" fill="{shade(self.col, 0.12)}"/>')
        return '\n'.join(o)

    def neck_props(self, J, pose):
        N = J['N']
        ang = ang_of(J['N'], J['H'])
        k = self.HU / 340
        if self.kind == 'level':
            s = pose.get('collar_s', 0.82 * k)
            return f'<g transform="rotate({f(-ang)},{f(N[0])},{f(N[1])})">' + collar(N[0], N[1] - 6 * s, s) + '</g>'
        if self.kind == 'hasty':
            s = self.HU / 300
            tie = pose.get('tie', 0)
            o = [f'<g transform="rotate({f(-ang)},{f(N[0])},{f(N[1])})">']
            x, y = N
            # salmon-dark lapel peaks + ivory shirt V
            o.append(f'<path d="M{f(x-30*s)},{f(y-4*s)} L{f(x-6*s)},{f(y-2*s)} L{f(x-4*s)},{f(y+26*s)} Z" fill="{SALMON_D}"/>')
            o.append(f'<path d="M{f(x+30*s)},{f(y-4*s)} L{f(x+6*s)},{f(y-2*s)} L{f(x+4*s)},{f(y+26*s)} Z" fill="{shade(SALMON_D,0.12)}"/>')
            o.append(f'<path d="M{f(x-12*s)},{f(y-6*s)} L{f(x+12*s)},{f(y-6*s)} L{f(x)},{f(y+14*s)} Z" fill="{IVORY}"/>')
            o.append('</g>')
            # thin black tie, swings on its own (follow-through)
            t0 = add(N, D(ang), 4 * s)
            a = ang + tie
            t1 = add(t0, D(a), self.HU * 0.3)
            c = add(lerp(t0, t1, 0.5), D(a + 90), -tie * 0.25)
            o.append(ribbon(t0, c, t1, 9 * s, 16 * s, INK, tip='point'))
            o.append(f'<rect x="{f(N[0]-5*s)}" y="{f(N[1]-2*s)}" width="{f(10*s)}" height="{f(9*s)}" rx="2" fill="{INK}" '
                     f'transform="rotate({f(-ang)},{f(N[0])},{f(N[1])})"/>')
            return '\n'.join(o)
        if self.kind == 'clerk':
            s = self.HU / 110 * 0.32
            return f'<g transform="rotate({f(-ang)},{f(N[0])},{f(N[1])})">' + collar(N[0], N[1] - 6 * s, s) + '</g>'
        return ''

    def chain(self, J, pose):
        c = pose.get('chain')
        if c is None:
            return ''
        H = J['H']
        up = D(ang_of(J['H'], J['N']))
        e1 = add(H, up, 4)
        e2 = add(H, up, 0.13 * self.HU)
        sw = c.get('swing', 0)
        L = c.get('len', 0.3) * self.HU
        d = D(sw)
        c1, c2 = add(e1, d, L), add(e2, d, L * 0.9)
        belly = (0.125 * e1[0] + 0.375 * c1[0] + 0.375 * c2[0] + 0.125 * e2[0],
                 0.125 * e1[1] + 0.375 * c1[1] + 0.375 * c2[1] + 0.125 * e2[1])
        o = [f'<path d="M{f(e1[0])},{f(e1[1])} C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(e2[0])},{f(e2[1])}" '
             f'stroke="{GOLD}" stroke-width="7" fill="none" stroke-linecap="round" stroke-dasharray="1 8"/>',
             f'<path d="M{f(e1[0])},{f(e1[1])} C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(e2[0])},{f(e2[1])}" '
             f'stroke="{GOLD}" stroke-width="4" fill="none" stroke-linecap="round"/>']
        fob = add(belly, d, 10)
        o.append(f'<circle cx="{f(fob[0])}" cy="{f(fob[1])}" r="11" fill="{GOLD}"/>')
        o.append(f'<circle cx="{f(fob[0]-2)}" cy="{f(fob[1]-1)}" r="6.5" fill="{IVORY}"/>')
        if c.get('glint'):
            o.append(star4(fob[0] + 14, fob[1] - 14, 13))
        return '\n'.join(o)

    # -- all layers ------------------------------------------------------
    def layers(self, J, pose):
        L = {}
        far = self.col_far
        hN = dict(pose.get('handN', {}))
        hF = dict(pose.get('handF', {}))
        hN.setdefault('ang', ang_of(J['EN'], J['WN']))
        hF.setdefault('ang', ang_of(J['EF'], J['WF']))
        fN = pose.get('footN', {})
        fF = pose.get('footF', {})
        # cast shadow
        sh = pose.get('shadow')
        L['shadow'] = ''
        if sh:
            x0, x1, y, op = sh
            L['shadow'] = (f'<polygon points="{f(x0)},{f(y)} {f(x1)},{f(y)} {f(x1+150)},{f(y-34)} {f(x0+110)},{f(y-34)}" '
                           f'fill="{EMERALD_D}" opacity="{op}"/>')
        L['legF'] = self.limb(J['H'], J['KF'], J['FF'], far) + self.shoe_svg(J['FF'], fF, far=True)
        L['armF'] = (self.limb(J['S'], J['EF'], J['WF'], far) + self.mitten(J['WF'], hF, shade(self.hand_col, 0.1))
                     + self.thumb(J['WF'], hF, shade(self.hand_col, 0.1)))
        # spine (coat) + neck (skin): one continuous stroke hip -> head pivot
        N, C, H, top = J['N'], J['C'], J['H'], J['top']
        sp = (f'<path d="M{f(H[0])},{f(H[1])} Q{f(C[0])},{f(C[1])} {f(N[0])},{f(N[1])}" stroke="{self.col}" '
              f'stroke-width="{self.spine_w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
        nk = (f'<line x1="{f(N[0])}" y1="{f(N[1])}" x2="{f(top[0])}" y2="{f(top[1])}" stroke="{self.neck_col}" '
              f'stroke-width="{self.neck_w}" stroke-linecap="round"/>')
        L['spine'] = nk + sp
        L['back'] = (self.tails(J, pose) if self.kind == 'level' and pose.get('tails') is not None else '')
        L['front'] = self.neck_props(J, pose) + (self.chain(J, pose) if self.kind == 'hasty' else '')
        L['legN'] = self.limb(J['H'], J['KN'], J['FN'], self.col) + self.shoe_svg(J['FN'], fN)
        L['armN'] = self.limb(J['S'], J['EN'], J['WN'], self.col) + self.mitten(J['WN'], hN)
        # hand prop + thumb nub in front of it
        prop = ''
        tr = pose.get('tray')
        if tr:
            s = tr.get('s', 1.0)
            W = J['W' + tr.get('hand', 'N')]
            hd = hN if tr.get('hand', 'N') == 'N' else hF
            u = D(hd['ang'])
            if hd.get('kind') == 'finger':
                fd = D(hd.get('fdir', hd['ang']))
                tip = add(add(add(W, u, self.mit_r * 0.5), fd, self.mit_r * 0.4), fd, self.HU * 0.075 + self.mit_r * 0.38)
                cx, top_y = tip[0], tip[1]
            else:
                mid = add(W, u, self.mit_len * 0.55)
                cx, top_y = mid[0] + tr.get('dx', 0), mid[1] - self.mit_r * 0.7
            prop = tray_cup(cx, top_y - TRAY_BOTTOM * s + 4 * s, s)
            J['tray'] = (cx, top_y - TRAY_BOTTOM * s)
        L['prop'] = prop + self.thumb(J['WN'], hN)
        L['marks'] = ''
        return L


class Char:
    def __init__(self, rig, body):
        self.rig, self.body = rig, body

    def pivot(self, cx, cy, rot_):
        dx, dy = rot(0, self.rig.H / 2 - 6, rot_)
        return (cx + dx, cy + dy)

    def solve_cy(self, cx, face, pose, floor, leg='F', bend=6):
        """head centre y so the standing leg (knee bent `bend` deg) meets the floor."""
        A0 = self.pivot(cx, 0, face.get('rot', 0))
        J = self.body.joints(A0, pose)
        b = self.body
        chord = math.sqrt(b.thigh ** 2 + b.shin ** 2 - 2 * b.thigh * b.shin * math.cos(math.radians(180 - bend)))
        fx = pose['leg' + leg]['foot'][0]
        dx = fx - J['H'][0]
        reach = math.sqrt(max(chord ** 2 - dx ** 2, 0))
        return floor - b.ankle - reach - J['H'][1]

    def draw(self, cx, cy, face, pose, marks=''):
        rot_ = face.get('rot', 0)
        A = self.pivot(cx, cy, rot_)
        J = self.body.joints(A, pose)
        L = self.body.layers(J, pose)
        head = self.rig.draw(cx, cy, resolve(self.rig, face))
        self.J = J
        return '\n'.join([L['shadow'], L['legF'], L['armF'], L['spine'], L['back'], head, L['front'],
                          L['legN'], L['armN'], L['prop'], L['marks'], marks])


# ---------------------------------------------------------------- cast
LEVEL_BODY = Body(340, 34, spine=0.88, leg=1.26, arm=1.1, col=COAT, neck_col=shade(SKIN_L, 0.12),
                  hand_col=GLOVE, shoe='oxford', kind='level')
LEVEL_SHEET_BODY = Body(290, 29, spine=0.86, leg=1.26, arm=1.1, col=COAT, neck_col=shade(SKIN_L, 0.12),
                        hand_col=GLOVE, w_root=18, w_tip=13, spine_w=16, neck_w=15, shoe='oxford', kind='level')
HASTY_BODY = Body(300, 16, spine=0.9, leg=1.2, arm=1.1, col=SALMON, neck_col=shade(SKIN_H, 0.12),
                  hand_col=SKIN_H, shoe='spectator', shoe_len=0.18, kind='hasty', ring=True)
CLERK_BODY = Body(110, 10, spine=0.9, leg=1.2, arm=1.1, col=INK, neck_col=shade(SKIN_C, 0.12),
                  hand_col=SKIN_C, w_root=10, w_tip=9, spine_w=10, neck_w=10, kind='clerk')

LEVEL = Char(LEVEL_SCENE, LEVEL_BODY)
LEVEL_S = Char(LEVEL_SHEET, LEVEL_SHEET_BODY)
HASTY_C = Char(HASTY, HASTY_BODY)
CLERK_C = Char(CLERK, CLERK_BODY)


# ---------------------------------------------------------------- set pieces
def floor_tiles(y0, y1, vp=(540, 700), tile=170, off=0, parity=0, light=None, fade=(0.08, 0.55)):
    out = [f'<rect x="0" y="{y0}" width="1080" height="{y1-y0}" fill="{FLOOR_D}"/>']
    vx, vy = vp
    rows = []
    y = y0
    h = 34
    while y < y1:
        rows.append((y, min(y + h, y1)))
        y += h
        h *= 1.35
    cols = [c + off for c in range(-2400 - tile * 4, 3600, tile)]
    tile_light = light or mix(EMERALD_D, '#EADFC4', 0.42)

    def X(x, yy):
        return vx + (x - vx) * (yy - vy) / (y1 - vy)
    for ri, (ya, yb) in enumerate(rows):
        for ci in range(len(cols) - 1):
            if (ri + ci + parity) % 2:
                continue
            xa0, xa1 = X(cols[ci], ya), X(cols[ci + 1], ya)
            xb0, xb1 = X(cols[ci], yb), X(cols[ci + 1], yb)
            out.append(f'<polygon points="{f(xa0)},{f(ya)} {f(xa1)},{f(ya)} {f(xb1)},{f(yb)} {f(xb0)},{f(yb)}" fill="{tile_light}"/>')
    gid = uid('fl')
    out.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{FLOOR_D}" stop-opacity="{fade[0]}"/>'
               f'<stop offset="1" stop-color="{FLOOR_D}" stop-opacity="{fade[1]}"/></linearGradient>')
    out.append(f'<rect x="0" y="{y0}" width="1080" height="{y1-y0}" fill="url(#{gid})"/>')

    def is_light(px, py):
        for ri, (ya, yb) in enumerate(rows):
            if ya <= py < yb:
                for ci in range(len(cols) - 1):
                    if X(cols[ci], py) <= px < X(cols[ci + 1], py):
                        return (ri + ci + parity) % 2 == 0
        return False
    return '\n'.join(out), is_light


def pick_floor(y0, y1, feet, vp=(540, 700), margin=34):
    """choose tile size / phase so every foot point stands on a light tile."""
    best = None
    for tile in (170, 180, 190, 200, 210, 220, 230):
        for off in range(0, tile, 5):
            for par in (0, 1):
                _, ok = floor_tiles(y0, y1, vp, tile, off, par)
                if all(ok(x, y) and ok(x - margin, y) and ok(x + margin, y) for x, y in feet):
                    return tile, off, par
    return 170, 0, 0


def arch(cx, top, w, bottom, stroke=6):
    r = w / 2
    return (f'<path d="M{cx-r},{bottom} L{cx-r},{top+r} A{r},{r} 0 0 1 {cx+r},{top+r} L{cx+r},{bottom}" '
            f'stroke="{GOLD}" stroke-width="{stroke}" fill="none"/>')


def floor_pool(cx, cy, rx, ry, op):
    gid = uid('pl')
    return (f'<radialGradient id="{gid}"><stop offset="0" stop-color="{IVORY}" stop-opacity="{op}"/>'
            f'<stop offset="0.6" stop-color="{IVORY}" stop-opacity="{op*0.5}"/>'
            f'<stop offset="1" stop-color="{IVORY}" stop-opacity="0"/></radialGradient>'
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{gid})"/>')


# ---------------------------------------------------------------- diagnostics
def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1e-9
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def head_clear(char, cx, cy, face, J, label):
    """min gap between each arm segment and the head rectangle (incl. ears)."""
    rig = char.rig
    r_ = face.get('rot', 0)
    ear = 18 * rig.scale * 0.6
    W2, H2 = rig.W / 2 + ear, rig.H / 2
    pts = []
    for i in range(41):
        t = i / 40
        for (x, y) in ((-W2 + 2 * W2 * t, -H2), (W2, -H2 + 2 * H2 * t), (W2 - 2 * W2 * t, H2), (-W2, H2 - 2 * H2 * t)):
            dx, dy = rot(x, y, r_)
            pts.append((cx + dx, cy + dy))
    res = []
    for side in ('N', 'F'):
        segs = [(J['S'], J['E' + side]), (J['E' + side], J['W' + side])]
        g = min(_seg_dist(p, a, b) for p in pts for a, b in segs)
        res.append(f'arm{side} gap {g:.0f}')
    print(label, ', '.join(res))


# ---------------------------------------------------------------- scene
def clerk_booth(cx_arch, top, w, ledge_y, horizon):
    """the right arch is the coat-check opening; clerk leans on the ledge."""
    o = []
    r = w / 2
    x0, x1 = cx_arch - r, cx_arch + r
    cid = uid('ar')
    o.append(f'<clipPath id="{cid}"><path d="M{x0},{ledge_y} L{x0},{top+r} A{r},{r} 0 0 1 {x1},{top+r} L{x1},{ledge_y} Z"/></clipPath>')
    o.append(f'<g clip-path="url(#{cid})">')
    o.append(f'<rect x="{x0}" y="{top}" width="{w}" height="{ledge_y-top}" fill="{EMERALD_D}"/>')
    o.append(lamp(cx_arch, ledge_y - 140, 170, 200, 0.30))
    # coats hanging in the dark, on a brass rail
    o.append(f'<line x1="{x0}" y1="{top+r+18}" x2="{x1}" y2="{top+r+18}" stroke="{shade(GOLD,0.35)}" stroke-width="5"/>')
    for i, cx in enumerate(range(int(x0) + 20, int(x1) - 10, 38)):
        if abs(cx - cx_arch) < 50:
            continue
        o.append(f'<path d="M{cx-15},{top+r+24} L{cx+15},{top+r+24} L{cx+20},{ledge_y-20} L{cx-20},{ledge_y-20} Z" '
                 f'fill="{mix(EMERALD_D, EMERALD, 0.45 if i % 2 else 0.22)}"/>')
    o.append('</g>')
    # clerk: stick upper body, forearms crossed on the ledge
    ch = CLERK_C
    b = ch.body
    face = dict(eyes=dict(state='dot', size=12, dx=-5, dy=2),
                browL=dict(dy=None, trail=True, trail_to_rest=True, w=34, h=13),
                browR=dict(dy=None, trail=True, trail_to_rest=True, w=34, h=13),
                mouth=dict(type='o', rx=8, ry=11, dy=3))
    pose = dict(armF=dict(a1=-58, a2=84, fore=0.62), armN=dict(a1=58, a2=-84, fore=0.62),
                handF=dict(ang=84, thumb=-1), handN=dict(ang=-84, thumb=1),
                legF=dict(a1=0), legN=dict(a1=0))
    ccx = cx_arch + 4
    # place head so the forearms land on the ledge
    A0 = ch.pivot(ccx, 0, 0)
    J0 = b.joints(A0, pose)
    ccy = ledge_y - 6 - J0['WN'][1]
    A = ch.pivot(ccx, ccy, 0)
    J = b.joints(A, pose)
    L = b.layers(J, pose)
    sc = uid('cs')
    o.append(f'<clipPath id="{sc}"><rect x="0" y="0" width="1080" height="{ledge_y+6}"/></clipPath>'
             f'<g clip-path="url(#{sc})">' + L['spine'] + '</g>')
    # counter ledge (in front of spine, under the forearms) + panel below
    o.append(f'<rect x="{x0-22}" y="{ledge_y}" width="{w+44}" height="22" rx="4" fill="{IVORY}"/>')
    o.append(f'<rect x="{x0-22}" y="{ledge_y+18}" width="{w+44}" height="6" fill="{shade(IVORY,0.25)}"/>')
    o.append(f'<rect x="{x0+16}" y="{ledge_y+48}" width="{w-32}" height="{horizon-ledge_y-90}" fill="none" stroke="{shade(GOLD,0.2)}" stroke-width="3" opacity="0.6"/>')
    rig = ch.rig
    rf = resolve(rig, face)
    o.append(L['armF'])
    o.append(rig.draw(ccx, ccy, rf))
    # bolder copies of the brow-trail dashes so they survive a phone downscale
    for side in ('browL', 'browR'):
        bx, by = rig.brow_xy(side[-1], rf[side])
        top_ = by + rf[side]['h'] / 2 + 6
        bot = -rig.H / 2 - 4
        for i in range(3):
            y0 = top_ + (bot - top_) * (0.06 + i * 0.34)
            y1 = y0 + (bot - top_) * 0.2
            o.append(f'<line x1="{f(ccx+bx)}" y1="{f(ccy+y0)}" x2="{f(ccx+bx)}" y2="{f(ccy+y1)}" stroke="{IVORY}" '
                     f'stroke-width="4.5" stroke-linecap="round" opacity="{f(0.9-0.22*i)}"/>')
    o.append(L['front'])
    o.append(L['armN'])
    o.append(b.thumb(J['WN'], dict(ang=-84, thumb=1)))
    return '\n'.join(o)


def build_scene():
    W, H = 1080, 1920
    horizon = 1290
    o = [f'<rect width="{W}" height="{H}" fill="{EMERALD}"/>']
    o.append(f'<clipPath id="wall"><rect x="0" y="232" width="{W}" height="{horizon-232}"/></clipPath><g clip-path="url(#wall)">'
             + lamp(470, 660, 520, 640, 0.58) + '</g>')
    o.append(arch(338, 262, 476, horizon, 7))
    o.append(arch(915, 300, 280, horizon, 7))
    o.append(f'<rect x="0" y="228" width="{W}" height="4" fill="{GOLD}"/>')
    o.append(clerk_booth(915, 300, 280, 604, horizon))

    # ---- characters: poses first (needed for the floor phase)
    lv_face = dict(POSES[3])
    lv_face = {k: (dict(v) if isinstance(v, dict) else v) for k, v in lv_face.items()}
    lv_face['rot'] = -18
    lv_face['eyes'] = dict(dx=26, dy=12, lid=0.38, w=14)
    lv_face['mouth'] = dict(type='curl', dx=34, side='R', curl=15)
    lcx, lcy = 244, 640
    lv_pose = dict(neck=-8, lean=-6, curve=4,
                   armN=dict(a1=133, a2=133), handN=dict(kind='flat', ang=90, thumb=1, thumb_ang=205),
                   armF=dict(a1=-14, a2=72, fore=0.42), handF=dict(ang=40, thumb=0),
                   legN=dict(a1=82, a2=-22), footN=dict(dir=1, tilt=40),
                   tails=dict(swing=-20, lag=16),
                   tray=dict(hand='N', s=1.0))
    A = LEVEL.pivot(lcx, lcy, lv_face['rot'])
    J0 = LEVEL.body.joints(A, dict(lv_pose, legF=dict(a1=0)))
    hip = J0['H']
    b = LEVEL.body
    fx = hip[0] - 8
    chord = math.sqrt(b.thigh ** 2 + b.shin ** 2 - 2 * b.thigh * b.shin * math.cos(math.radians(174)))
    floor_y = hip[1] + math.sqrt(chord ** 2 - (fx - hip[0]) ** 2) + b.ankle
    lv_pose['legF'] = dict(foot=(fx, floor_y - b.ankle), bend=1)
    lv_pose['footF'] = dict(dir=1)
    lv_pose['shadow'] = (fx - 70, fx + 120, floor_y, 0.55)

    hx, hy = 796, 828
    hs_face = dict(rot=-8, darken=0.10,
                   browL=dict(dx=4, dy=None, tilt=30, ticks=2),
                   browR=dict(dx=4, dy=None, tilt=30, ticks=2),
                   eyes=dict(dx=-12, dy=8),
                   mouth=dict(type='zig', w=60, dx=-6),
                   sweat=(176, -44))
    hs_pose = dict(neck=-6, lean=-9, curve=-8,
                   armN=dict(a1=-105, a2=-162), handN=dict(ang=-168, thumb=1),
                   armF=dict(a1=101, a2=170), handF=dict(ang=172, thumb=-1),
                   footN=dict(dir=-1, tilt=62), footF=dict(dir=-1, tilt=56),
                   chain=dict(swing=58, len=0.32, glint=True), tie=24)
    A = HASTY_C.pivot(hx, hy, hs_face['rot'])
    Jh = HASTY_C.body.joints(A, dict(hs_pose, legN=dict(a1=0), legF=dict(a1=0)))
    hh = Jh['H']
    hs_pose['legN'] = dict(foot=(hh[0] - 34, floor_y - 128), bend=-1)
    hs_pose['legF'] = dict(foot=(hh[0] + 4, floor_y - 118), bend=-1)
    hs_pose['shadow'] = (hh[0] - 80, hh[0] + 60, floor_y, 0.38)

    # ---- floor, with light tiles under both pairs of feet
    tile, off, par = pick_floor(horizon, 1660, [(fx + 10, floor_y - 4), (hh[0] - 10, floor_y - 4)])
    fsvg, _ = floor_tiles(horizon, 1660, tile=tile, off=off, parity=par)
    o.append(f'<rect x="0" y="{horizon-26}" width="{W}" height="26" fill="{EMERALD_D}"/>')
    o.append(f'<rect x="0" y="{horizon-28}" width="{W}" height="3" fill="{GOLD}"/>')
    o.append(fsvg)
    o.append(f'<rect x="0" y="1660" width="{W}" height="{H-1660}" fill="{FLOOR_D}"/>')
    # lamp reflection pooled on the polished floor behind Mr. Level's legs
    o.append(floor_pool(380, 1420, 330, 190, 0.42))
    o.append(floor_pool(380, 1300, 280, 60, 0.25))

    # ---- draw: Hasty behind, Mr. Level in front (tray on top)
    o.append(HASTY_C.draw(hx, hy, hs_face, hs_pose))
    Jh = HASTY_C.J
    head_clear(HASTY_C, hx, hy, hs_face, Jh, 'hasty')
    # whiff ticks around the stalled reaching mitten
    hn = add(Jh['WN'], D(-170), HASTY_C.body.mit_len * 0.7)
    o.append(ticks(hn[0], hn[1], 30, 46, (165, 200, 235), w=5, op=0.55))
    toe = max(Jh['FN'][1], Jh['FF'][1]) + 70
    for dx in (-30, 0, 30):
        x = (Jh['FN'][0] + Jh['FF'][0]) / 2 + dx
        o.append(f'<line x1="{f(x)}" y1="{f(toe)}" x2="{f(x)}" y2="{f(toe+22)}" stroke="{INK}" stroke-width="5" stroke-linecap="round" opacity="0.45"/>')
    o.append(LEVEL.draw(lcx, lcy, lv_face, lv_pose))
    Jl = LEVEL.J
    head_clear(LEVEL, lcx, lcy, lv_face, Jl, 'level')
    o.append(grain(W, H))
    print('scene: floor', round(floor_y), 'tile', tile, off, par, '| level head top', lcy - 170,
          'height', round(floor_y - (lcy - 170)), 'head%', round(340 / (floor_y - (lcy - 170)) * 100, 1),
          '| tray', tuple(round(v) for v in Jl['tray']), '| hasty fingertips',
          tuple(round(v) for v in hn), '| hasty soles ~', round(Jh['FN'][1]))
    return svg_doc(W, H, '\n'.join(o))


# ---------------------------------------------------------------- poses sheet
def build_poses():
    W, H = 1080, 1080
    floor_top, sole = 988, 1040
    o = [f'<rect width="{W}" height="{H}" fill="{EMERALD}"/>']
    cxs = (150, 470, 950)
    for cx in cxs:
        o.append(lamp(cx, 540, 230, 560, 0.24))
    fsvg, _ = floor_tiles(floor_top, H, vp=(540, 560), tile=150, off=40, parity=0, fade=(0.0, 0.25))
    o.append(f'<rect x="0" y="{floor_top-3}" width="{W}" height="3" fill="{GOLD}"/>')
    o.append(fsvg)
    for cx in cxs:
        o.append(floor_pool(cx, sole, 200, 46, 0.35))
    ch = LEVEL_S
    b = ch.body

    def stand(cx, face, pose, lift=0, feet=(-14, 14), bends=(-1, 1)):
        A0 = ch.pivot(cx, 0, face.get('rot', 0))
        pose = dict(pose)
        pose.setdefault('legF', dict(foot=(cx + feet[0], 0), bend=bends[0]))
        J0 = b.joints(A0, dict(pose, legF=dict(a1=0), legN=dict(a1=0)))
        hip = J0['H']
        chord = math.sqrt(b.thigh ** 2 + b.shin ** 2 - 2 * b.thigh * b.shin * math.cos(math.radians(174)))
        fx = pose['legF']['foot'][0]
        cy = sole - lift - b.ankle - math.sqrt(chord ** 2 - (fx - hip[0]) ** 2) - hip[1]
        A = ch.pivot(cx, cy, face.get('rot', 0))
        J = b.joints(A, dict(pose, legF=dict(a1=0), legN=dict(a1=0)))
        y = sole - lift - b.ankle
        pose['legF'] = dict(foot=(pose['legF']['foot'][0], y), bend=pose['legF'].get('bend', -1))
        if 'legN' not in pose:
            pose['legN'] = dict(foot=(cx + feet[1], y), bend=bends[1])
        return cy, pose

    # (1) READY: ramrod, heels together, tray at shoulder height, arm behind back
    f1 = dict(POSES[0])
    p1 = dict(armN=dict(a1=24, a2=153), handN=dict(kind='flat', ang=90, thumb=1, thumb_ang=205),
              armF=dict(a1=-10, a2=72, fore=0.3), handF=dict(kind='none'),
              footF=dict(dir=-1), footN=dict(dir=1),
              tails=dict(swing=-6, lag=0), tray=dict(hand='N', s=0.62))
    cy1, p1 = stand(cxs[0], f1, p1, feet=(-16, 16))
    p1['shadow'] = (cxs[0] - 60, cxs[0] + 70, sole, 0.5)
    o.append(ch.draw(cxs[0], cy1, f1, p1))
    head_clear(ch, cxs[0], cy1, f1, ch.J, 'pose1')
    tot = sole - (cy1 - ch.rig.H / 2)
    print('pose1 height', round(tot), 'HU', round(tot / 290, 2), 'head%', round(290 / tot * 100, 1))

    # (2) TALL LIFT: flamingo, tray arm straight up-and-out, free arm winged
    f2 = {k: (dict(v) if isinstance(v, dict) else v) for k, v in POSES[3].items()}
    f2['rot'] = -18
    f2['eyes'] = dict(dx=14, dy=4)
    p2 = dict(neck=-8, lean=-8, curve=4,
              armN=dict(a1=132, a2=132), handN=dict(kind='flat', ang=90, thumb=1, thumb_ang=205),
              armF=dict(a1=-34, a2=-16), handF=dict(ang=-14, thumb=-1),
              legN=dict(a1=86, a2=-6), footN=dict(dir=1, tilt=50), footF=dict(dir=1),
              tails=dict(swing=-34, lag=22), tray=dict(hand='N', s=0.6),
              legF=dict(foot=(cxs[1] + 8, 0), bend=1))
    cy2, p2 = stand(cxs[1], f2, p2)
    p2['shadow'] = (cxs[1] - 50, cxs[1] + 110, sole, 0.5)
    o.append(ch.draw(cxs[1], cy2, f2, p2))
    head_clear(ch, cxs[1], cy2, f2, ch.J, 'pose2')
    J2 = ch.J

    # (3) BROWS TAKE OFF: stiff board, sprung 40 px, tray on one fingertip
    f3 = dict(POSES[1])
    p3 = dict(armN=dict(a1=-3, a2=-90), handN=dict(kind='finger', ang=-90, fdir=180, thumb=0),
              armF=dict(a1=9, a2=6), handF=dict(ang=6, thumb=-1),
              footF=dict(dir=-1), footN=dict(dir=1),
              tails=dict(swing=0, lag=0, len=1.0, w=0.62, split=0.42), tray=dict(hand='N', s=0.6))
    cy3, p3 = stand(cxs[2], f3, p3, lift=40, feet=(-16, 16))
    p3['shadow'] = (cxs[2] - 40, cxs[2] + 50, sole, 0.32)
    marks = ''
    for dx in (-34, 0, 34):
        marks += (f'<line x1="{cxs[2]+dx}" y1="{sole-24}" x2="{cxs[2]+dx}" y2="{sole-6}" stroke="{INK}" stroke-width="5" '
                  f'stroke-linecap="round" opacity="0.5"/>')
    o.append(ch.draw(cxs[2], cy3, f3, p3, marks=marks))
    head_clear(ch, cxs[2], cy3, f3, ch.J, 'pose3')
    print('pose3 brow top', round(cy3 - 145 - 30 - 26))
    o.append(grain(W, H))
    return svg_doc(W, H, '\n'.join(o))


if __name__ == '__main__':
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(build_scene())
    with open(os.path.join(HERE, 'poses.svg'), 'w') as fh:
        fh.write(build_poses())
    print('ok')
