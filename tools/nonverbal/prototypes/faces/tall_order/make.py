#!/usr/bin/env python3
"""Tall Order -- brow-driven face rig + scene + expression sheet.

One Rig class draws every head.  A character = Rig(proportions);
a pose = dict of brow / eye / mouth parameters.  The scene and the
expression sheet both call Rig.draw(), so every frame of an animation
would just be a different pose dict.
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


# ---------------------------------------------------------------- expression sheet
def build_faces():
    W, H = 1080, 1080
    rig = LEVEL_SHEET
    body = [f'<rect width="{W}" height="{H}" fill="{EMERALD}"/>']
    for i, pose in enumerate(POSES):
        col, row = i % 3, i // 3
        ox, oy = col * 360, row * 540
        cx, cy = ox + 180, oy + 290
        body.append(lamp(cx, cy - 20, 200, 270, 0.2))
        # neck + shoulders + collar at cell bottom
        body.append(f'<rect x="{cx-30}" y="{cy+rig.H/2-10}" width="60" height="70" fill="{shade(SKIN_L,0.12)}"/>')
        body.append(f'<path d="M{cx-150},{oy+540} Q{cx-140},{cy+rig.H/2+52} {cx-40},{cy+rig.H/2+46} L{cx+40},{cy+rig.H/2+46} '
                    f'Q{cx+140},{cy+rig.H/2+52} {cx+150},{oy+540} Z" fill="{COAT}"/>')
        body.append(f'<path d="M{cx-36},{cy+rig.H/2+46} L{cx+36},{cy+rig.H/2+46} L{cx},{oy+540} Z" fill="{IVORY}"/>')
        body.append(collar(cx, cy + rig.H / 2 + 52, 1.0))
        body.append(rig.draw(cx, cy, resolve(rig, pose)))
    body.append(grain(W, H))
    return svg_doc(W, H, '\n'.join(body))


# ---------------------------------------------------------------- scene
def floor(y0, y1, vp=(540, 700)):
    """perspective checker between y0 and y1, fading toward y1."""
    out = [f'<rect x="0" y="{y0}" width="1080" height="{y1-y0}" fill="{EMERALD_D}"/>']
    vx, vy = vp
    # rows: geometric spacing
    rows = []
    y = y0
    h = 34
    while y < y1:
        rows.append((y, min(y + h, y1)))
        y += h
        h *= 1.35
    cols = list(range(-2400, 3600, 170))
    tile_light = mix(EMERALD_D, '#EADFC4', 0.33)
    for ri, (ya, yb) in enumerate(rows):
        for ci in range(len(cols) - 1):
            if (ri + ci) % 2:
                continue
            def X(x, yy):
                return vx + (x - vx) * (yy - vy) / (y1 - vy)
            xa0, xa1 = X(cols[ci], ya), X(cols[ci + 1], ya)
            xb0, xb1 = X(cols[ci], yb), X(cols[ci + 1], yb)
            out.append(f'<polygon points="{f(xa0)},{f(ya)} {f(xa1)},{f(ya)} {f(xb1)},{f(yb)} {f(xb0)},{f(yb)}" fill="{tile_light}"/>')
    gid = uid('fl')
    out.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{FLOOR_D}" stop-opacity="0.15"/>'
               f'<stop offset="1" stop-color="{FLOOR_D}" stop-opacity="0.92"/></linearGradient>')
    out.append(f'<rect x="0" y="{y0}" width="1080" height="{y1-y0}" fill="url(#{gid})"/>')
    return '\n'.join(out)


def arch(cx, top, w, bottom, stroke=6):
    r = w / 2
    return (f'<path d="M{cx-r},{bottom} L{cx-r},{top+r} A{r},{r} 0 0 1 {cx+r},{top+r} L{cx+r},{bottom}" '
            f'stroke="{GOLD}" stroke-width="{stroke}" fill="none"/>')


def level_body():
    """Mr. Level: tailcoat, one arm behind back, gloved hand under tray."""
    o = []
    cx = 330
    sh = shade(COAT, 0.12)
    # hard cast shadow (light from upper left)
    o.append(f'<polygon points="236,1552 444,1552 640,1500 470,1500" fill="{EMERALD_D}" opacity="0.75"/>')
    # coat tails behind the legs
    o.append(f'<path d="M262,1150 L398,1150 L404,1330 L338,1312 L330,1290 L322,1312 L256,1330 Z" fill="{sh}"/>')
    # legs
    o.append(f'<path d="M282,1170 L326,1170 L322,1528 L288,1528 Z" fill="{COAT}"/>')
    o.append(f'<path d="M334,1170 L378,1170 L372,1528 L338,1528 Z" fill="{sh}"/>')
    # big flat shoes
    o.append(f'<path d="M318,1522 L318,1552 L222,1552 Q214,1536 236,1526 Q262,1520 318,1522 Z" fill="{INK}"/>')
    o.append(f'<path d="M342,1522 L342,1552 L446,1552 Q454,1536 432,1526 Q404,1520 342,1522 Z" fill="{INK}"/>')
    o.append(f'<ellipse cx="248" cy="1532" rx="10" ry="3" fill="{IVORY}" opacity="0.35"/>')
    o.append(f'<ellipse cx="420" cy="1532" rx="10" ry="3" fill="{IVORY}" opacity="0.35"/>')
    # neck
    o.append(f'<rect x="304" y="858" width="52" height="56" fill="{shade(SKIN_L,0.12)}"/>')
    # torso (tailcoat, front cut away at waist)
    o.append(f'<path d="M236,948 Q240,918 290,912 L370,912 Q420,918 426,948 L408,1168 Q370,1196 330,1186 Q290,1196 252,1168 Z" fill="{COAT}"/>')
    o.append(f'<path d="M396,920 Q420,926 426,948 L408,1168 Q396,1178 384,1182 Z" fill="{sh}"/>')
    # shirt front (V)
    o.append(f'<path d="M298,914 L362,914 L340,1120 L330,1132 L320,1120 Z" fill="{IVORY}"/>')
    o.append(f'<path d="M346,914 L362,914 L340,1120 L336,1124 Z" fill="{shade(IVORY,0.12)}"/>')
    # shirt studs
    for y in (990, 1035, 1080):
        o.append(f'<circle cx="330" cy="{y}" r="3.5" fill="{INK}"/>')
    # lapels (satin, slightly lighter)
    o.append(f'<path d="M296,914 L270,958 L292,968 L276,1000 L322,1108 L314,1016 Z" fill="#33302D"/>')
    o.append(f'<path d="M364,914 L390,958 L368,968 L384,1000 L338,1108 L346,1016 Z" fill="#2B2826"/>')
    # pocket square
    o.append(f'<path d="M262,1000 L276,984 L284,996 L292,986 L300,1000 Z" fill="{IVORY}"/>')
    # collar + bow tie
    o.append(collar(330, 900, 1.05))
    return '\n'.join(o)


def level_arm_and_tray(tray_c):
    tx, ty = tray_c
    o = []
    sh = (418, 950); el = (474, 1106); wr = (tx - 40, ty + 48)
    # sleeve: shoulder -> elbow -> wrist (thick flat stroke)
    o.append(f'<path d="M{sh[0]},{sh[1]} L{el[0]},{el[1]} L{wr[0]},{wr[1]}" stroke="{COAT}" stroke-width="50" stroke-linejoin="round" stroke-linecap="round" fill="none"/>')
    o.append(f'<path d="M{sh[0]+18},{sh[1]+12} L{el[0]+12},{el[1]-4}" stroke="{shade(COAT,0.12)}" stroke-width="16" stroke-linecap="round" fill="none"/>')
    # ivory cuff: short band along the forearm at the wrist
    dx, dy = wr[0] - el[0], wr[1] - el[1]
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    c0 = (wr[0] - ux * 6, wr[1] - uy * 6); c1 = (wr[0] + ux * 10, wr[1] + uy * 10)
    o.append(f'<line x1="{f(c0[0])}" y1="{f(c0[1])}" x2="{f(c1[0])}" y2="{f(c1[1])}" stroke="{IVORY}" stroke-width="46" stroke-linecap="butt"/>')
    # white-gloved hand, palm up, fingertips under the tray
    o.append(f'<path d="M{tx-44},{ty+30} Q{tx-36},{ty+8} {tx-4},{ty+8} L{tx+30},{ty+10} Q{tx+34},{ty+19} {tx+18},{ty+22} '
             f'Q{tx-6},{ty+44} {tx-26},{ty+56} Z" fill="{IVORY}"/>')
    # tray (thickness + top)
    o.append(f'<ellipse cx="{tx}" cy="{ty+6}" rx="108" ry="19" fill="{shade(TRAY,0.25)}"/>')
    o.append(f'<ellipse cx="{tx}" cy="{ty}" rx="108" ry="18" fill="{TRAY}"/>')
    o.append(f'<ellipse cx="{tx}" cy="{ty}" rx="92" ry="12" fill="{mix(TRAY,IVORY,0.35)}"/>')
    # saucer
    o.append(f'<ellipse cx="{tx}" cy="{ty-4}" rx="52" ry="10" fill="{shade(IVORY,0.12)}"/>')
    o.append(f'<ellipse cx="{tx}" cy="{ty-6}" rx="48" ry="8" fill="{IVORY}"/>')
    # cup body
    cw, ch = 46, 58
    top = ty - 6 - ch
    o.append(f'<path d="M{tx+cw+2},{top+12} a15,15 0 1 1 -3,32" stroke="{IVORY}" stroke-width="10" fill="none"/>')
    o.append(f'<path d="M{tx-cw},{top} L{tx+cw},{top} Q{tx+cw},{top+ch-6} {tx+14},{top+ch} L{tx-14},{top+ch} Q{tx-cw},{top+ch-6} {tx-cw},{top} Z" fill="{IVORY}"/>')
    o.append(f'<path d="M{tx+20},{top} L{tx+cw},{top} Q{tx+cw},{top+ch-6} {tx+14},{top+ch} L{tx+6},{top+ch} Q{tx+28},{top+ch-12} {tx+20},{top} Z" fill="{shade(IVORY,0.12)}"/>')
    # rim + tea: filled to the rim, a hair-thin surface-tension dome
    o.append(f'<ellipse cx="{tx}" cy="{top}" rx="{cw}" ry="10" fill="{shade(IVORY,0.06)}"/>')
    o.append(f'<ellipse cx="{tx}" cy="{top}" rx="{cw-3}" ry="8" fill="{TEA}"/>')
    o.append(f'<path d="M{tx-cw+3},{top} Q{tx},{top-16} {tx+cw-3},{top} Z" fill="{TEA}"/>')
    o.append(f'<ellipse cx="{tx-13}" cy="{top-5}" rx="9" ry="3" fill="{IVORY}" opacity="0.85"/>')
    return '\n'.join(o)


def hasty_body(hand):
    """Hasty: short, wide, salmon double-breasted suit, on tiptoe, leaning in."""
    o = []
    fx, fy = 880, 1552
    sal_d = shade(SALMON, 0.12)
    lap = shade(SALMON, 0.2)
    o.append(f'<polygon points="796,1552 966,1552 1080,1510 940,1510" fill="{EMERALD_D}" opacity="0.75"/>')
    g = [f'<g transform="translate({fx},{fy}) skewX(10) translate({-fx},{-fy})">']
    # legs (short)
    g.append(f'<path d="M812,1300 L862,1300 L858,1478 L818,1478 Z" fill="{SALMON}"/>')
    g.append(f'<path d="M884,1300 L934,1300 L928,1478 L888,1478 Z" fill="{sal_d}"/>')
    # torso
    g.append(f'<path d="M752,1066 Q754,1034 796,1030 L946,1030 Q988,1034 990,1066 L984,1284 Q982,1318 946,1320 L796,1320 Q760,1318 758,1284 Z" fill="{SALMON}"/>')
    g.append(f'<path d="M940,1030 Q988,1034 990,1066 L984,1284 Q982,1318 946,1320 L936,1320 Z" fill="{sal_d}"/>')
    # shirt V + thin tie
    g.append(f'<path d="M834,1032 L908,1032 L871,1136 Z" fill="{IVORY}"/>')
    g.append(f'<path d="M865,1040 L877,1040 L875,1118 L871,1130 L867,1118 Z" fill="{INK}"/>')
    # lapels (double-breasted, peaked)
    g.append(f'<path d="M830,1032 L800,1060 L816,1070 L802,1090 L872,1170 L848,1082 Z" fill="{lap}"/>')
    g.append(f'<path d="M912,1032 L942,1060 L926,1070 L940,1090 L870,1170 L894,1082 Z" fill="{lap}"/>')
    # 2x3 buttons
    for y in (1188, 1230, 1272):
        for x in (844, 898):
            g.append(f'<circle cx="{x}" cy="{y}" r="6" fill="#7A3B2E"/>')
    g.append('</g>')
    o.extend(g)
    # tiptoe shoes in final coords: toes on the floor, heels lifted, pointing at Level
    for x0 in (826, 902):
        o.append(f'<path d="M{x0+10},{1470} L{x0+34},{1480} L{x0+22},{1532} Q{x0+4},{1556} {x0-34},{1552} '
                 f'Q{x0-40},{1540} {x0-22},{1530} Z" fill="{INK}"/>')
    # reaching arm: out from the near shoulder, hand cocked under the tray rim
    hx, hy = hand
    arm = f'M738,1092 Q700,1112 {hx+24},{hy+8}'
    o.append(f'<path d="{arm}" stroke="{shade(SALMON,0.2)}" stroke-width="44" stroke-linecap="round" fill="none" transform="translate(0,5)"/>')
    o.append(f'<path d="{arm}" stroke="{SALMON}" stroke-width="40" stroke-linecap="round" fill="none"/>')
    o.append(f'<line x1="{hx+30}" y1="{hy-10}" x2="{hx+24}" y2="{hy+26}" stroke="{IVORY}" stroke-width="12"/>')
    # fist + index finger pointing up at the rim
    o.append(f'<ellipse cx="{hx+8}" cy="{hy+8}" rx="18" ry="16" fill="{SKIN_H}"/>')
    o.append(f'<path d="M{hx-2},{hy} L{hx-10},{hy-26}" stroke="{SKIN_H}" stroke-width="11" stroke-linecap="round"/>')
    # freeze ticks around the stalled fingertip
    cx_, cy_ = hx - 10, hy - 28
    for a in (195, 240, 285, 330):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        o.append(f'<line x1="{f(cx_+ca*14)}" y1="{f(cy_+sa*14)}" x2="{f(cx_+ca*25)}" y2="{f(cy_+sa*25)}" stroke="{INK}" stroke-width="4" stroke-linecap="round" opacity="0.6"/>')
    return '\n'.join(o)


def coat_check(x, y, w, h):
    o = []
    o.append(f'<rect x="{x-10}" y="{y-10}" width="{w+20}" height="{h+20}" rx="6" fill="{GOLD}"/>')
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{EMERALD_D}"/>')
    # hanging coats in the dark
    for i, cx in enumerate(range(x + 22, x + w - 10, 34)):
        o.append(f'<path d="M{cx-14},{y+30} L{cx+14},{y+30} L{cx+18},{y+h-30} L{cx-18},{y+h-30} Z" fill="{mix(EMERALD_D, EMERALD, 0.45 if i%2 else 0.25)}"/>')
    o.append(f'<line x1="{x}" y1="{y+26}" x2="{x+w}" y2="{y+26}" stroke="{shade(GOLD,0.4)}" stroke-width="4"/>')
    # clerk
    ccx, ccy = x + w * 0.55, y + h - 74
    o.append(f'<path d="M{ccx-46},{y+h} Q{ccx-44},{ccy+52} {ccx},{ccy+50} Q{ccx+44},{ccy+52} {ccx+46},{y+h} Z" fill="{INK}"/>')
    o.append(f'<path d="M{ccx-10},{ccy+46} L{ccx+10},{ccy+46} L{ccx},{ccy+70} Z" fill="{IVORY}"/>')
    pose = dict(eyes=dict(dx=-6), browL=dict(dy=-22, tilt=-12), browR=dict(dy=3),
                mouth=dict(type='flat', w=18, dx=-2))
    o.append(CLERK.draw(ccx, ccy, pose))
    # counter ledge
    o.append(f'<rect x="{x-24}" y="{y+h-6}" width="{w+48}" height="22" rx="4" fill="{IVORY}"/>')
    o.append(f'<rect x="{x-24}" y="{y+h+12}" width="{w+48}" height="6" fill="{shade(IVORY,0.25)}"/>')
    return '\n'.join(o)


def build_scene():
    W, H = 1080, 1920
    o = [f'<rect width="{W}" height="{H}" fill="{EMERALD}"/>']
    horizon = 1290
    # back wall details
    o.append(f'<clipPath id="wall"><rect x="0" y="232" width="{W}" height="{horizon-232}"/></clipPath><g clip-path="url(#wall)">'
             + lamp(450, 640, 500, 620, 0.55) + '</g>')
    o.append(arch(330, 262, 440, horizon, 7))
    o.append(arch(905, 330, 290, horizon, 7))
    o.append(f'<rect x="0" y="228" width="{W}" height="4" fill="{GOLD}"/>')
    o.append(coat_check(800, 480, 200, 190))
    # baseboard + floor
    o.append(f'<rect x="0" y="{horizon-26}" width="{W}" height="26" fill="{EMERALD_D}"/>')
    o.append(f'<rect x="0" y="{horizon-28}" width="{W}" height="3" fill="{GOLD}"/>')
    o.append(floor(horizon, 1575))
    o.append(f'<rect x="0" y="1575" width="{W}" height="{H-1575}" fill="{FLOOR_D}"/>')
    # characters
    tray_c = (532, 1030)
    o.append(level_body())
    rig = LEVEL_SCENE
    level_pose = dict(
        eyes=dict(dx=22, dy=12),
        browL=dict(dy=None, trail=True, trail_to_rest=True),
        browR=dict(),
        mouth=dict(type='curl', dx=40, side='R', curl=15),
    )
    # floating brow: bottom edge 150 px above the head top, hanging still
    level_pose['browL']['dy'] = (-rig.H / 2 - 150 - rig.brow_h / 2) - rig.brow_y
    o.append(rig.draw(330, 700, level_pose))
    hand = (652, 1112)
    o.append(hasty_body(hand))
    hasty_pose = dict(
        rot=-6,
        eyes=dict(state='dot', size=22, dx=-8, dy=4),
        browL=dict(tilt=-14.5, dy=2, ticks=2, tick_op=0.9, tick_angles=[-50, -85]),
        browR=dict(tilt=-14.5, dy=2, ticks=2, tick_op=0.9, tick_angles=[-50, -85]),
        mouth=dict(type='o', rx=12, ry=12, dx=-6),
        strand=True,
    )
    o.append(HASTY.draw(800, 930, hasty_pose))
    o.append(level_arm_and_tray(tray_c))
    o.append(grain(W, H))
    return svg_doc(W, H, '\n'.join(o))


if __name__ == '__main__':
    with open(os.path.join(HERE, 'faces.svg'), 'w') as fh:
        fh.write(build_faces())
    with open(os.path.join(HERE, 'scene.svg'), 'w') as fh:
        fh.write(build_scene())
    print('ok')
