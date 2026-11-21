"""
Stickman ragdoll obstacle course (pymunk / Chipmunk2D), deterministic and seeded.

World units are "pixels at 1080 px screen width", origin at the top-of-stairs
ledge, +y up. Every physics step is recorded so the renderer and the audio
synth read the exact same timeline (sound cannot drift from picture).

Story beats (all physics, with keyframed muscle targets layered on top):
  0.0s  stickman stands on the ledge, breathing; a bowling ball rolls in
  ~0.7s he notices it (arms fly up -> keyframed spring targets)
  ~1.0s ball sweeps his shins, hold released -> ragdoll with muscle tone
        tumbles down wooden stairs, through metal pegs, onto a rubber pad
  end   he lies on the pad, dizzy
"""
import math
from dataclasses import dataclass, field

import numpy as np
import pymunk

DT = 1 / 600          # physics step; 10 substeps per 60 fps frame
GRAVITY = -2300.0

# ---------------- course geometry ----------------
LEDGE_X1 = -260.0               # ledge ends here, stairs start
TREAD, RISE, STEPS = 105.0, 78.0, 6
STAIR_END_X = LEDGE_X1 + TREAD * STEPS          # 400
STAIR_BOTTOM_Y = -RISE * STEPS                  # -420
PEG_R = 13.0
PAD_W, PAD_H = 1056.0, 26.0
PAD_TOP_REST = -1440.0
PAD_BASE_Y = -1560.0
FLOOR_Y = -1600.0
WALL_X = 540.0
RAMP_Y0, RAMP_Y1, RAMP_X1 = -1200.0, -1352.0, 238.0
PLATE = ((548.0, -650.0), (290.0, -740.0))   # metal deflector under the stair exit

MATERIALS = ('wood', 'metal', 'rubber', 'stone', 'body', 'ball')


def peg_layout():
    pegs = []
    rows = [(-860, (-370, -130, 110, 350)),
            (-1005, (-250, -10, 230, 470)),
            (-1145, (-370, -130, 110, 350))]
    for y, xs in rows:
        for x in xs:
            pegs.append((float(x), float(y)))
    return pegs


PEGS = peg_layout()

# ---------------- ragdoll ----------------
# name: (length, radius, mass)
SEGS = {
    'torso': (90.0, 8.0, 4.0),
    'uarm_n': (50.0, 6.5, 0.8), 'larm_n': (48.0, 6.5, 0.6),
    'uarm_f': (50.0, 6.5, 0.8), 'larm_f': (48.0, 6.5, 0.6),
    'thigh_n': (60.0, 7.5, 1.6), 'shin_n': (58.0, 7.5, 1.1),
    'thigh_f': (60.0, 7.5, 1.6), 'shin_f': (58.0, 7.5, 1.1),
}
HEAD_R, HEAD_M, NECK = 23.0, 1.5, 31.0
BODY_ORDER = ['torso', 'head', 'uarm_n', 'larm_n', 'uarm_f', 'larm_f',
              'thigh_n', 'shin_n', 'thigh_f', 'shin_f']
D = math.radians

# Standing pose, facing LEFT (front = -x). Absolute segment angles.
STAND = {
    'torso': D(92), 'head': D(92),
    'thigh_n': D(-97), 'shin_n': D(-86), 'thigh_f': D(-82), 'shin_f': D(-76),
    'uarm_n': D(-100), 'larm_n': D(-118), 'uarm_f': D(-78), 'larm_f': D(-96),
}
# "Whoa!" pose when he sees the ball: arms thrown up, a little lean back
WHOA = dict(STAND, uarm_n=D(-215), larm_n=D(-250), uarm_f=D(-190), larm_f=D(-215),
            torso=D(84), head=D(80))

# joints: (parent, child, relative-angle range = child.angle - parent.angle)
PI = math.pi
JOINTS = [
    ('torso', 'head', (-0.55, 0.75)),
    ('torso', 'uarm_n', (-PI - 3.0, -PI + 1.3)), ('uarm_n', 'larm_n', (-2.6, 0.0)),
    ('torso', 'uarm_f', (-PI - 3.0, -PI + 1.3)), ('uarm_f', 'larm_f', (-2.6, 0.0)),
    ('torso', 'thigh_n', (-PI - 2.1, -PI + 0.45)), ('thigh_n', 'shin_n', (0.0, 2.5)),
    ('torso', 'thigh_f', (-PI - 2.1, -PI + 0.45)), ('thigh_f', 'shin_f', (0.0, 2.5)),
]


def unit(a):
    return np.array([math.cos(a), math.sin(a)])


def pose_points(angles, hip):
    """Joint positions for a pose given absolute angles and the hip point."""
    P = {'hip': np.array(hip, float)}
    P['neck'] = P['hip'] + unit(angles['torso']) * SEGS['torso'][0]
    P['head'] = P['neck'] + unit(angles['head']) * NECK
    sh = P['neck'] - unit(angles['torso']) * 7.0
    for side in 'nf':
        P['sh_' + side] = sh
        P['el_' + side] = sh + unit(angles['uarm_' + side]) * SEGS['uarm_' + side][0]
        P['hand_' + side] = P['el_' + side] + unit(angles['larm_' + side]) * SEGS['larm_' + side][0]
        P['kn_' + side] = P['hip'] + unit(angles['thigh_' + side]) * SEGS['thigh_' + side][0]
        P['an_' + side] = P['kn_' + side] + unit(angles['shin_' + side]) * SEGS['shin_' + side][0]
    return P


SEG_ENDS = {
    'torso': ('hip', 'neck'),
    'uarm_n': ('sh_n', 'el_n'), 'larm_n': ('el_n', 'hand_n'),
    'uarm_f': ('sh_f', 'el_f'), 'larm_f': ('el_f', 'hand_f'),
    'thigh_n': ('hip', 'kn_n'), 'shin_n': ('kn_n', 'an_n'),
    'thigh_f': ('hip', 'kn_f'), 'shin_f': ('kn_f', 'an_f'),
}


@dataclass
class Params:
    seed: int = 0
    ball_v: float = 520.0
    stick_x: float = -372.0
    tone: float = 1.0           # muscle tone multiplier after the hit
    duration: float = 9.0
    jitter: float = 1.0
    stair_fric: float = 0.45
    pad_k: float = 5000.0
    body_e: float = 0.45
    pad_c: float = 4.0
    pad_e: float = 0.85


@dataclass
class Recording:
    params: Params
    t_hit: float = -1.0
    t_notice: float = -1.0
    steps: int = 0
    bodies: np.ndarray = None    # (steps, n_bodies, 3)  x, y, angle  (ragdoll in BODY_ORDER)
    ball: np.ndarray = None      # (steps, 4) x, y, angle, rolling speed when on ground else 0
    pad: np.ndarray = None       # (steps, 2) top y, vy
    events: list = field(default_factory=list)
    touched: set = field(default_factory=set)


class Course:
    def __init__(self, p: Params):
        self.p = p
        rng = np.random.default_rng(p.seed)
        self.rng = rng
        sp = self.space = pymunk.Space()
        sp.gravity = (0, GRAVITY)
        sp.iterations = 30
        sp.damping = 0.995
        sp.collision_slop = 0.3
        self.static = sp.static_body
        self.info = {}

        def tag(shape, mat, name, fric, elast):
            shape.friction, shape.elasticity = fric, elast
            self.info[shape] = (mat, name)
            sp.add(shape)
            return shape

        # ledge (extends off-screen left so the ball can roll in)
        tag(pymunk.Poly(self.static, [(-1400, 0), (LEDGE_X1, 0), (LEDGE_X1, -RISE * 1.6), (-1400, -RISE * 1.6)]),
            'wood', 'ledge', 0.8, 0.25)
        for i in range(STEPS):
            x0 = LEDGE_X1 + TREAD * i
            yt = -RISE * (i + 1)
            tag(pymunk.Poly(self.static, [(x0, yt), (x0 + TREAD, yt), (x0 + TREAD, yt - RISE * 1.4), (x0, yt - RISE * 1.4)],
                            radius=1.0), 'wood', f'step{i}', p.stair_fric, 0.3)
        for i, (x, y) in enumerate(PEGS):
            tag(pymunk.Circle(self.static, PEG_R, (x, y)), 'metal', f'peg{i}', 0.15, 0.55)
        tag(pymunk.Segment(self.static, PLATE[0], PLATE[1], 9), 'metal', 'plate', 0.25, 0.45)
        tag(pymunk.Segment(self.static, (-WALL_X - 12, -380), (-WALL_X - 12, FLOOR_Y), 12), 'stone', 'wallL', 0.4, 0.3)
        tag(pymunk.Segment(self.static, (WALL_X + 12, -160), (WALL_X + 12, FLOOR_Y), 12), 'stone', 'wallR', 0.4, 0.3)
        tag(pymunk.Segment(self.static, (-900, FLOOR_Y), (900, FLOOR_Y), 4), 'stone', 'floor', 0.8, 0.1)

        # springy pad: a vertical-only body on a damped spring
        pm = 8.0
        pad = self.pad = pymunk.Body(pm, float('inf'))
        pad.position = (0, PAD_TOP_REST - PAD_H / 2)
        sp.add(pad)
        self.pad_shape = tag(pymunk.Poly.create_box(pad, (PAD_W, PAD_H), radius=4), 'rubber', 'pad', 0.9, p.pad_e)
        k = p.pad_k
        rest = (PAD_TOP_REST - PAD_H / 2 - PAD_BASE_Y) + pm * -GRAVITY / k
        sp.add(pymunk.GrooveJoint(self.static, pad, (0, PAD_BASE_Y + 10), (0, PAD_TOP_REST + 200), (0, 0)))
        sp.add(pymunk.DampedSpring(self.static, pad, (0, PAD_BASE_Y), (0, 0), rest, k, p.pad_c))

        # bowling ball
        r = 31.0
        ball = self.ball = pymunk.Body(9.0, pymunk.moment_for_circle(9.0, 0, r))
        ball.position = (-800, r)
        v = p.ball_v * (1 + 0.04 * p.jitter * rng.normal())
        ball.velocity = (v, 0)
        ball.angular_velocity = -v / r
        sp.add(ball)
        tag(pymunk.Circle(ball, r), 'ball', 'ball', 0.7, 0.3)

        self._build_ragdoll(rng)
        self.rec = Recording(p)
        self._last_evt = {}
        self._pre_data = {}
        self.ball_ground = False
        self.t = 0.0
        sp.on_collision(None, None, pre_solve=self._pre, post_solve=self._post)

    # ---------- ragdoll ----------
    def _build_ragdoll(self, rng):
        sp, j = self.space, self.p.jitter
        ang = {k: v + D(1.5) * j * rng.normal() for k, v in STAND.items()}
        hip = (self.p.stick_x, 0.0)
        P = pose_points(ang, hip)
        low = min(P['an_n'][1], P['an_f'][1])
        P = pose_points(ang, (hip[0], -low + SEGS['shin_n'][1] + 0.5))
        self.stand_pose = ang
        flt = pymunk.ShapeFilter(group=1)
        p_el = self.p.body_e
        self.parts = {}
        for name, (L, r, m) in SEGS.items():
            a, b = P[SEG_ENDS[name][0]], P[SEG_ENDS[name][1]]
            body = pymunk.Body(m, pymunk.moment_for_segment(m, (-L / 2, 0), (L / 2, 0), r))
            body.position = tuple((a + b) / 2)
            body.angle = ang[name]
            sh = pymunk.Segment(body, (-L / 2, 0), (L / 2, 0), r)
            sh.friction, sh.elasticity, sh.filter = 0.7, p_el, flt
            self.info[sh] = ('body', name)
            sp.add(body, sh)
            self.parts[name] = body
        hb = pymunk.Body(HEAD_M, pymunk.moment_for_circle(HEAD_M, 0, HEAD_R))
        hb.position, hb.angle = tuple(P['head']), ang['head']
        sh = pymunk.Circle(hb, HEAD_R)
        sh.friction, sh.elasticity, sh.filter = 0.6, p_el + 0.1, flt
        self.info[sh] = ('body', 'head')
        sp.add(hb, sh)
        self.parts['head'] = hb

        pivots = {('torso', 'head'): P['neck'],
                  ('torso', 'uarm_n'): P['sh_n'], ('uarm_n', 'larm_n'): P['el_n'],
                  ('torso', 'uarm_f'): P['sh_f'], ('uarm_f', 'larm_f'): P['el_f'],
                  ('torso', 'thigh_n'): P['hip'], ('thigh_n', 'shin_n'): P['kn_n'],
                  ('torso', 'thigh_f'): P['hip'], ('thigh_f', 'shin_f'): P['kn_f']}
        self.springs = {}
        for pa, ch, (lo, hi) in JOINTS:
            A, B = self.parts[pa], self.parts[ch]
            pj = pymunk.PivotJoint(A, B, tuple(pivots[(pa, ch)]))
            pj.collide_bodies = False
            sp.add(pj, pymunk.RotaryLimitJoint(A, B, lo, hi))
            s = pymunk.DampedRotarySpring(A, B, ang[pa] - ang[ch], 0, 0)  # NB: spring uses a.angle - b.angle
            sp.add(s)
            self.springs[ch] = (s, pa)
        # puppet hold until the ball hits: hip pinned to a kinematic anchor + upright torso
        self.anchor = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.anchor.position = tuple(P['hip'])
        sp.add(self.anchor)
        self.hold = [pymunk.PivotJoint(self.anchor, self.parts['torso'], tuple(P['hip'])),
                     pymunk.DampedRotarySpring(self.anchor, self.parts['torso'], -ang['torso'], 6e6, 2e5)]
        for c in self.hold:
            c.max_force = 4e6
        sp.add(*self.hold)
        self.holding = True
        self.set_tone(stiff=True)

    def set_tone(self, stiff, target=None):
        target = target or self.stand_pose
        for ch, (s, pa) in self.springs.items():
            I = self.parts[ch].moment
            if stiff:
                w, z = 95.0, 0.9   # chain inertia at the shoulder is ~4x the segment's own
            else:
                w, z = (5.0 if ch != 'head' else 7.0) * self.p.tone, 0.35
            s.stiffness = I * w * w
            s.damping = 2 * z * I * w
            s.rest_angle = target[pa] - target[ch]

    def release(self):
        if self.holding:
            self.space.remove(*self.hold)
            self.holding = False
            # a little "tense" target pose while falling: arms out, knees bent
            fall = dict(self.stand_pose, uarm_n=D(-200), larm_n=D(-230), uarm_f=D(-150), larm_f=D(-170),
                        thigh_n=D(-130), shin_n=D(-80), thigh_f=D(-110), shin_f=D(-60), head=self.stand_pose['torso'])
            self.set_tone(stiff=False, target=fall)

    # ---------- contacts ----------
    def _pre(self, arb, space, data):
        a, b = arb.shapes
        if a is self.pad_shape or b is self.pad_shape:
            arb.restitution = self.p.pad_e   # trampoline: override the multiplied elasticity
        ps = arb.contact_point_set
        if not ps.points:
            return
        pt = ps.points[0].point_a
        n = ps.normal
        va = a.body.velocity_at_world_point(pt) if a.body.body_type != pymunk.Body.STATIC else pymunk.Vec2d(0, 0)
        vb = b.body.velocity_at_world_point(pt) if b.body.body_type != pymunk.Body.STATIC else pymunk.Vec2d(0, 0)
        # >0: approaching along the normal (a -> b)
        self._pre_data[(id(a), id(b))] = ((va - vb).dot(n), (pt.x, pt.y))

    def _post(self, arb, space, data):
        a, b = arb.shapes
        ia, ib = self.info.get(a), self.info.get(b)
        if ia is None or ib is None:
            return
        J = arb.total_impulse.length
        names = {ia[1], ib[1]}
        if 'ball' in names and (ia[0] in ('wood', 'stone') or ib[0] in ('wood', 'stone')):
            self.ball_ground = True
        if 'ball' in names and (ia[0] == 'body' or ib[0] == 'body') and self.holding and self.t > 0.3:
            self.rec.t_hit = self.t
            self.release()
        vn, pt = self._pre_data.pop((id(a), id(b)), (0.0, None))
        if pt is None:
            return
        key = (ia[1], ib[1]) if ia[1] < ib[1] else (ib[1], ia[1])
        last = self._last_evt.get(key, -1.0)
        if (arb.is_first_contact and vn > 25) or (vn > 140 and self.t - last > 0.06):
            if self.t - last < 0.025:
                return
            self._last_evt[key] = self.t
            if ia[0] == 'body':
                ia, ib = ib, ia
            self.rec.events.append(dict(t=self.t, x=pt[0], y=pt[1], J=J, vn=vn,
                                        mat=ia[0], other=ib[0], a=ia[1], b=ib[1]))
            if ib[0] == 'body' or ia[0] == 'body':
                self.rec.touched.add(ia[1])

    # ---------- run ----------
    def run(self):
        p = self.p
        n = int(round(p.duration / DT))
        rec = self.rec
        bodies = np.zeros((n, len(BODY_ORDER), 3))
        ballr = np.zeros((n, 4))
        padr = np.zeros((n, 2))
        whoa_set = False
        for i in range(n):
            self.t = i * DT
            # idle breathing on the puppet anchor
            if self.holding:
                self.anchor.velocity = (0, 2.5 * 2 * PI * 0.7 * math.cos(2 * PI * 0.7 * self.t))
                # notice the ball when it is ~170 px away -> "whoa" keyframe
                if not whoa_set and self.ball.position.x > self.p.stick_x - 230:
                    whoa_set = True
                    rec.t_notice = self.t
                    self.set_tone(stiff=True, target=WHOA)
                    self.hold[1].rest_angle = -WHOA['torso']
            if self.t > 2.0 and self.ball_ground:   # rolling resistance once the gag is over
                self.ball.angular_velocity *= 0.985
                self.ball.velocity *= 0.985
            self.ball_ground = False
            self.space.step(DT)
            for k, name in enumerate(BODY_ORDER):
                b = self.parts[name]
                bodies[i, k] = (b.position.x, b.position.y, b.angle)
            bb = self.ball
            ballr[i] = (bb.position.x, bb.position.y, bb.angle,
                        abs(bb.angular_velocity) * 31.0 if self.ball_ground else 0.0)
            padr[i] = (self.pad.position.y + PAD_H / 2, self.pad.velocity.y)
        rec.steps, rec.bodies, rec.ball, rec.pad = n, bodies, ballr, padr
        return rec


def simulate(p: Params):
    return Course(p).run()


def evaluate(rec: Recording):
    """Story check: did the run hit the beats we want? Returns (ok, score, notes)."""
    ev = rec.events
    body_ev = [e for e in ev if e['other'] == 'body']
    steps = {e['a'] for e in body_ev if e['a'].startswith('step')}
    pegs = {e['a'] for e in body_ev if e['a'].startswith('peg')}
    pad_hits = [e for e in body_ev if e['a'] == 'pad']
    t_pad = pad_hits[0]['t'] if pad_hits else 99
    torso = rec.bodies[:, 0]
    end = torso[-1]
    rest_speed = np.linalg.norm(torso[-1, :2] - torso[-61, :2]) / (60 * DT)
    on_pad = abs(end[0]) < PAD_W / 2 and end[1] < PAD_TOP_REST + 80
    big_pad = [e for e in pad_hits if e['vn'] > 400]
    ok = bool(rec.t_hit > 0 and len(steps) >= 3 and len(pegs) >= 2 and t_pad < rec.params.duration - 2.2
          and on_pad and rest_speed < 40)
    score = len(steps) + 1.5 * len(pegs) + min(len(big_pad), 3) - abs(t_pad - 5.2) - rest_speed / 40
    notes = dict(t_hit=round(rec.t_hit, 3), steps=len(steps), pegs=len(pegs), t_pad=round(t_pad, 2),
                 pad_bounces=len(big_pad), on_pad=on_pad, rest_speed=round(rest_speed, 1),
                 end=(round(end[0]), round(end[1])), events=len(ev))
    return ok, score, notes


if __name__ == '__main__':
    import sys
    import time
    seeds = range(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
    for s in seeds:
        t0 = time.time()
        rec = simulate(Params(seed=s))
        ok, score, notes = evaluate(rec)
        print(s, ok, round(score, 2), notes, f'{time.time() - t0:.2f}s')
