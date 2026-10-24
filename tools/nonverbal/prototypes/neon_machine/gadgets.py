"""Interlude machines for the score film: a Pythagora-switch run between two pieces.

While the music rests, the marble leaves the last note of one piece and runs through a machine to the first
note of the next. A machine is a chain, flowing right to left and down: a short rail, then one to three
mechanisms joined by rails, a last rail, and a spring that flicks the marble onto the first note. The film
builds up: the first machine has one mechanism, the middle ones two, the last one three.

Mechanisms
  stairs    wooden steps, a knock on each
  xylo      eight tuned bars as steps: a descending C major scale
  dominoes  the marble topples a line of dominoes and rattles over them as they fall
  bells     it rolls past a row of little bells and rings a rising phrase
  loop      a drop into a quarter-pipe and a loop-the-loop
  jump      a steep run, a kicker, a flight over a gap into a catching cup
  tilt      a seesaw plank that flips when the marble passes its pivot
  spiral    a funnel: it circles faster and faster and drops through the hole (seen from above)
  helix     a corkscrew: two turns down around a pole
  plinko    a pegboard: it bounces down through the pins (each pin a note) into a slot

Nothing is keyframed by hand; the motion is computed:
  rolling          a = 5/7 g sin(angle) (a rolling solid sphere), less rolling resistance DRAG * v
  falls, flights   ballistic, g = 9.81
  the loop         energy: v^2 = v_in^2 - 10/7 g dh, so the marble slows over the top
  the funnel       angular momentum: it spins faster as it nears the hole
Each machine has to take exactly the time the music leaves for it: the rail angle is searched for that; if
even the gentlest angle is too quick, the spring holds the marble a moment before it fires.
"""
import math
import random

from mathutils import Vector

G = 9.81
ROLL_K = 5 / 7            # a rolling solid sphere accelerates at 5/7 of g sin(angle)
DRAG = 1.1                # rolling resistance on the rails (1/s): speed settles near a / DRAG
RAIL_HALF, RAIL_R = 0.030, 0.009      # rails thick enough to read at phone size
T_HOP_IN, T_HOP_OUT, T_KICK = 0.40, 0.42, 0.06
W_T1, W_LINK, W_LAST_MIN = 0.50, 0.35, 0.45
XYLO_MIDI = [84, 83, 81, 79, 77, 76, 74, 72]          # C6 B5 A5 G5 F5 E5 D5 C5
XYLO_HUE = [(0.95, 0.2, 0.25), (1.0, 0.5, 0.1), (1.0, 0.85, 0.15), (0.3, 0.85, 0.3),
            (0.15, 0.7, 0.95), (0.25, 0.4, 0.95), (0.6, 0.3, 0.9), (0.95, 0.3, 0.7)]
BELL_MIDI = [76, 79, 81, 84, 88, 91]                  # a rising pentatonic phrase
PLINKO_MIDI = [72, 74, 76, 79, 81, 84, 86, 88, 91]    # pins sound by column (pentatonic)
STYLE = {'baroque': 'wood', 'classical': 'gold', 'beethoven': 'steel', 'romantic': 'brass'}
DOM_GAP, DOM_DT = 0.075, 0.100                        # domino spacing and time between falls (a chain you can follow)
# how far left and down each mechanism takes the marble (for planning the room it needs)
WIDTH = {'stairs': 0.73, 'xylo': 0.87, 'dominoes': 1.30, 'bells': 1.05, 'loop': 0.95, 'jump': 1.15,
         'tilt': 0.70, 'spiral': 0.40, 'helix': 0.15, 'plinko': 0.75}
HEIGHT = {'stairs': 0.60, 'xylo': 0.63, 'dominoes': 0.36, 'bells': 0.12, 'loop': 0.62, 'jump': 0.55,
          'tilt': 0.20, 'spiral': 0.57, 'helix': 0.32, 'plinko': 0.78}


def ballistic(p0, t0, p1, t1, t):
    T = t1 - t0
    v = (p1 - p0 + Vector((0, 0, 0.5 * G * T * T))) / T
    u = t - t0
    return p0 + v * u + Vector((0, 0, -0.5 * G * u * u))


def smooth(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


def roll_s(u, v0, a0):
    """Distance rolled after u seconds from speed v0 with drive a0 and rolling resistance."""
    vt = a0 / DRAG
    return vt * u + (v0 - vt) * (1 - math.exp(-DRAG * u)) / DRAG


def roll_v(u, v0, a0):
    vt = a0 / DRAG
    return vt + (v0 - vt) * math.exp(-DRAG * u)


def roll_time(L, v0, a0):
    """(time, end speed) to roll L; None if the marble stops first (uphill)."""
    if L <= 0:
        return 0.0, v0
    vt = a0 / DRAG
    if vt <= 0:
        if v0 <= 0:
            return None
        t_stop = math.log((v0 - vt) / -vt) / DRAG if vt < 0 else 60.0
        if roll_s(t_stop, v0, a0) < L:
            return None
        hi = t_stop
    else:
        hi = 0.5
        while roll_s(hi, v0, a0) < L:
            hi *= 2
    lo = 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if roll_s(mid, v0, a0) < L:
            lo = mid
        else:
            hi = mid
    return hi, roll_v(hi, v0, a0)


def width_need(kinds):
    return W_T1 + sum(WIDTH[k] for k in kinds) + W_LINK * (len(kinds) - 1) + W_LAST_MIN + 0.1


def height_need(kinds, span_x):
    """Height (marble centre, top rail to spring) a chain needs, with its rails at about 8 degrees."""
    rails = W_T1 + W_LINK * (len(kinds) - 1) + max(W_LAST_MIN, span_x - width_need(kinds) + W_LAST_MIN)
    return sum(HEIGHT[k] for k in kinds) + rails * math.tan(math.radians(8)) + 0.22


class Track:
    """A straight run of the marble's centre from a to b (the rails lie `lift` below it, along the normal)."""

    def __init__(self, a, b):
        self.a, self.b = a.copy(), b.copy()
        d = b - a
        self.L = d.length
        self.d = d / self.L
        n = Vector((-self.d.z, 0, self.d.x))
        self.n = n.normalized() if n.z > 0 else -n.normalized()
        self.sin = -self.d.z                    # > 0 going downhill

    def at(self, s):
        return self.a + self.d * s


class Machine:
    def __init__(self, kinds, style, R, Y):
        self.kinds, self.style, self.R, self.Y = kinds, style, R, Y
        self.kind = '+'.join(kinds)
        self.lift = math.sqrt((R + RAIL_R) ** 2 - RAIL_HALF ** 2)   # marble centre above the rail axes
        self.segs, self.hits, self.rolls, self.parts, self.views = [], [], [], [], []
        self.closeups = []                      # (t0, t1, zoom, centre): moments the camera moves in on
        self.sharp = []                         # (t0, t1): fast orbits seen close, shot with a short shutter
        self.t_kick, self.wait, self.swing = None, 0.0, 1.0

    # -- motion ---------------------------------------------------------------------------------------
    def seg(self, t0, t1, fn):
        self.segs.append((t0, t1, fn))
        return t1

    def pos(self, t):
        for t0, t1, fn in self.segs:
            if t <= t1:
                return fn(max(t, t0))
        t0, t1, fn = self.segs[-1]
        return fn(t1)

    def roll(self, tr, t0, v0, s0=0.0, s1=None, bump=None, sound=True):
        """Roll along track tr from distance s0 to s1; bump(s) lifts the marble (over fallen dominoes)."""
        s1 = tr.L if s1 is None else s1
        a0 = ROLL_K * G * tr.sin
        res = roll_time(s1 - s0, v0, a0)
        if res is None:
            return None
        T, v1 = res

        def fn(t, tr=tr, t0=t0, v0=v0, a0=a0, s0=s0, T=T):
            s = s0 + roll_s(min(t - t0, T), v0, a0)
            return tr.at(s) + Vector((0, 0, bump(s) if bump else 0.0))
        self.seg(t0, t0 + T, fn)
        if sound:
            self.rolls.append(dict(t0=t0, t1=t0 + T, v0=v0, v1=v1, style=self.style))
        return t0 + T, v1

    def t_at(self, tr, t0, v0, s):
        """When a marble that set off at t0 with speed v0 along tr reaches distance s."""
        res = roll_time(s, v0, ROLL_K * G * tr.sin)
        return t0 + res[0] if res else None

    def hop(self, p0, t0, p1, t1):
        return self.seg(t0, t1, lambda t, p0=p0.copy(), p1=p1.copy(), t0=t0, t1=t1: ballistic(p0, t0, p1, t1, t))

    def hold(self, p, t0, t1):
        return self.seg(t0, t1, lambda t, p=p.copy(): p)

    def fall(self, p0, t0, h):
        T = math.sqrt(2 * h / G)
        return self.seg(t0, t0 + T, lambda t, p0=p0.copy(), t0=t0: p0 - Vector((0, 0, 0.5 * G * (t - t0) ** 2)))

    def hit(self, t, kind, g=1.0, midi=None):
        self.hits.append(dict(t=t, kind=kind, g=g, midi=midi))

    # -- the camera's view of it ------------------------------------------------------------------------
    def elev(self, t):
        """Camera elevation (radians): it rises to look down into the funnel or the corkscrew."""
        e = 0.0
        for a, b, deg, _ in self.views:
            e = max(e, math.radians(deg) * smooth((t - (a - 0.7)) / 0.7) * (1 - smooth((t - b) / 0.6)))
        return e

    def yaw(self, t):
        """A slow sideways swing through the machine, so its depth shows (alternate machines swing the
        other way)."""
        t0, t1 = self.segs[0][0], self.segs[-1][1]
        u = (t - t0) / (t1 - t0)
        return self.swing * math.radians(16) * math.sin(math.pi * min(1.0, max(0.0, u)))

    def zoom(self, t, base):
        """The camera's framing: base, or closer for a moment that deserves it (the rattle on the rim)."""
        z = base
        for a, b, zc, c in self.closeups:
            k = smooth((t - (a - 0.35)) / 0.35) * (1 - smooth((t - b) / 0.4))
            z = z + (zc - z) * k
        return z

    def closeness(self, t):
        """How far into a close-up the camera is at t (0..1); the wide view of the machine gives way to it."""
        k = 0.0
        for a, b, _, c in self.closeups:
            k = max(k, smooth((t - (a - 0.35)) / 0.35) * (1 - smooth((t - b) / 0.4)))
        return k

    def attention(self, t):
        """What the camera follows: the marble, or a mechanism's centre while the marble circles in it."""
        p = self.pos(t)
        for a, b, _, c in self.closeups:
            k = smooth((t - (a - 0.35)) / 0.35) * (1 - smooth((t - b) / 0.4))
            p = p.lerp(Vector((c.x, p.y, c.z)), k)
        for a, b, _, c in self.views:
            if c is not None:
                k = smooth((t - (a - 0.5)) / 0.5) * (1 - smooth((t - b) / 0.5))
                p = p.lerp(Vector((c.x, p.y, c.z - 0.08)), k)
        return p

    def frame_box(self):
        """The whole machine's extent (x and z of everything the marble passes), for the opening wide view."""
        t0, t1 = self.segs[0][0], self.segs[-1][1]
        ps = [self.pos(t0 + (t1 - t0) * k / 200) for k in range(201)]
        xs, zs = [p.x for p in ps], [p.z for p in ps]
        return (min(xs), max(xs), min(zs), max(zs))


# ======================================================================================== mechanisms
# Each takes the marble at p (moving left) with speed v at time t, and returns (p, v, t) where it leaves,
# or None if it cannot be laid out at this rail angle.
def rail(m, p, v, t, L, th):
    tr = Track(p, p + Vector((-L * math.cos(th), 0, -L * math.sin(th))))
    r = m.roll(tr, t, v)
    if r is None:
        return None
    m.parts.append(('rail', tr))
    return tr.b, r[1], r[0]


def mech_stairs(m, p, v, t, th, xylo=False):
    n, ws, hs, Ts = (8, 0.10, 0.07, 0.17) if xylo else (6, 0.11, 0.085, 0.19)
    steps, prev = [], p
    for k in range(n):
        q = Vector((p.x - (k + 0.5) * ws, m.Y, p.z - (k + 1) * hs))
        t = m.hop(prev, t, q, t + Ts)
        steps.append((q, t))
        if xylo:
            m.hit(t, 'glock', 0.63, XYLO_MIDI[k])      # under the music, not over it
        else:
            m.hit(t, 'wood', 0.85 - 0.05 * k)
        prev = q
    out = Vector((p.x - n * ws - 0.07, m.Y, p.z - (n + 1) * hs))
    t = m.hop(prev, t, out, t + Ts)
    m.hit(t, 'land', 0.7)
    m.parts.append(('xylo' if xylo else 'stairs', steps, hs, ws))
    return out, 0.35, t


def mech_xylo(m, p, v, t, th):
    return mech_stairs(m, p, v, t, th, xylo=True)


def mech_dominoes(m, p, v, t, th):
    m.hit(t, 'wall', 0.7)
    m.parts.append(('wall', p))
    t = m.fall(p, t, 0.15)
    c = p - Vector((0, 0, 0.15))
    m.hit(t, 'land', 0.8)
    Ld, ang = 1.3, math.radians(9)
    tr = Track(c, c + Vector((-Ld * math.cos(ang), 0, -Ld * math.sin(ang))))
    s_d0 = 0.28
    r = m.roll(tr, t, 0.0, 0.0, s_d0)
    if r is None:
        return None
    t, v = r
    n_dom = int((Ld - s_d0 - 0.25) / DOM_GAP)
    m.hit(t, 'domino', 1.0)
    # the chain runs ahead at its own pace, but each domino is always down before the marble gets to it
    # (t_at ignores drag, so it errs early: safe)
    v0_ = min(v, 0.12)
    doms, prev_ = [], t - 0.02
    for k in range(n_dom):
        s_k = s_d0 + 0.02 + k * DOM_GAP
        t_m = m.t_at(tr, t, v0_, max(0.0, s_k - 0.07 - s_d0))
        t_k = t + k * DOM_DT if t_m is None else min(t + k * DOM_DT, t_m - 0.12)
        t_k = max(t_k, prev_ + 0.02)
        doms.append((s_k, t_k))
        prev_ = t_k
    for s_k, t_k in doms[1:]:
        m.hit(t_k, 'domino', 0.55)
    s_end = doms[-1][0] + 0.06

    def bump(s, s_d0=s_d0, s_end=s_end):
        return 0.075 * smooth((s - s_d0) / 0.06) * (1 - smooth((s - s_end) / 0.06))   # over the fallen ones
    r = m.roll(tr, t, min(v, 0.12), s_d0, tr.L, bump)
    if r is None:
        return None
    m.parts.append(('rail', tr))
    m.parts.append(('dominoes', tr, doms))
    return tr.b, r[1], r[0]


def mech_bells(m, p, v, t, th):
    Lb, ang = 1.05, math.radians(6)
    tr = Track(p, p + Vector((-Lb * math.cos(ang), 0, -Lb * math.sin(ang))))
    v0, t0 = max(v, 0.25), t
    bells = []
    for k, mid in enumerate(BELL_MIDI):
        s_k = 0.15 + k * 0.165
        tk = m.t_at(tr, t0, v0, s_k)
        if tk is None:
            return None
        bells.append((s_k, tk, mid))
        m.hit(tk, 'bell', 1.0, mid)
    r = m.roll(tr, t0, v0)
    if r is None:
        return None
    m.parts.append(('rail', tr))
    m.parts.append(('bells', tr, bells))
    return tr.b, r[1], r[0]


def mech_loop(m, p, v, t, th):
    Y = m.Y
    h_ff, rq = 0.12, 0.42
    O = Vector((p.x - rq, Y, p.z - h_ff))
    B = Vector((p.x - rq, Y + 0.04, p.z - h_ff - rq))
    m.hit(t, 'wall', 0.6)
    m.parts.append(('wall', p))
    t = m.fall(p, t, h_ff)
    v_ff = math.sqrt(2 * G * h_ff)
    v_B = math.sqrt(0.8 * v_ff ** 2 + 10 / 7 * G * rq)
    Tq = (math.pi / 2 * rq) / ((v_ff + v_B) / 2)

    def quarter(tt, O=O, rq=rq, t0=t, Tq=Tq, v_ff=v_ff, v_B=v_B):
        u = (tt - t0) / Tq
        frac = min(1.0, (v_ff * u + 0.5 * (v_B - v_ff) * u * u) / ((v_ff + v_B) / 2))
        a = -math.pi / 2 * frac              # from the right (0) down to the bottom (-pi/2)
        return Vector((O.x + rq * math.cos(a), Y + 0.04 * frac, O.z + rq * math.sin(a)))
    m.rolls.append(dict(t0=t, t1=t + Tq, v0=v_ff, v1=v_B, style='loop'))
    t = m.seg(t, t + Tq, quarter)
    rl = min(0.16, 0.55 * v_B ** 2 / (27 / 7 * G))
    Cl = Vector((B.x, Y, B.z + rl))
    table, phi, tt, dt_ = [], 0.0, 0.0, 0.002
    while phi < 2 * math.pi:
        vv = math.sqrt(max(0.05, v_B ** 2 - 10 / 7 * G * rl * (1 - math.cos(phi))))
        table.append(phi)
        phi += vv / rl * dt_
        tt += dt_
    Tl = tt

    def loop(t_, Cl=Cl, rl=rl, t0=t, table=table):
        ph = table[min(len(table) - 1, int((t_ - t0) / 0.002))]
        y = Y + 0.04 - 0.08 * ph / (2 * math.pi)      # a gentle helix: in at the back, out in front
        return Vector((Cl.x - rl * math.sin(ph), y, Cl.z - rl * math.cos(ph)))
    m.rolls.append(dict(t0=t, t1=t + Tl, v0=v_B, v1=v_B, style='loop'))
    m.closeups.append((t - Tq - 0.5, t + Tl + 0.2, 0.7, Cl.copy()))   # in close for the loop itself
    t = m.seg(t, t + Tl, loop)
    m.parts.append(('loop', O, rq, Cl, rl))
    # run out, back to the machine's depth
    B2 = Vector((B.x, Y - 0.04, B.z))
    out = Vector((B.x - 0.32 * math.cos(th), Y, B.z - 0.32 * math.sin(th)))
    tr = Track(B2, out)
    r = m.roll(tr, t, v_B)
    if r is None:
        return None
    m.parts.append(('rail', tr))
    return out, r[1], r[0]


def mech_jump(m, p, v, t, th):
    """A steep run, a kicker, a flight over a gap and a cup that catches the marble."""
    Y = m.Y
    a_run, Lr, rk, a_up = math.radians(30), 0.45, 0.18, math.radians(20)
    run = Track(p, p + Vector((-Lr * math.cos(a_run), 0, -Lr * math.sin(a_run))))
    r = m.roll(run, t, v)
    if r is None:
        return None
    t, v_r = r
    m.parts.append(('rail', run))
    # the kicker: a short arc from 30 degrees down to 20 degrees up (centre above its lowest point)
    q = run.b
    O = q + Vector((-rk * math.sin(a_run), 0, rk * math.cos(a_run)))
    arc_len = rk * (a_run + a_up)
    v_k = math.sqrt(max(0.01, v_r ** 2 - 10 / 7 * G * (rk * (1 - math.cos(a_up)) - rk * (1 - math.cos(a_run)))))
    if v_k < 1.1:
        return None
    Tk = arc_len / ((v_r + v_k) / 2)

    def kick(tt, O=O, t0=t, Tk=Tk):
        a = a_run - (a_run + a_up) * min(1.0, (tt - t0) / Tk)   # angle from straight down (+ = right side)
        return O + Vector((rk * math.sin(a), 0, -rk * math.cos(a)))
    t = m.seg(t, t + Tk, kick)
    launch = kick(t)
    m.hit(t, 'clack', 0.6)
    vx, vz = -v_k * math.cos(a_up), v_k * math.sin(a_up)
    dz = 0.12
    T_f = (vz + math.sqrt(vz * vz + 2 * G * dz)) / G
    rim = launch + Vector((vx * T_f, 0, -dz))      # it lands on the cup's rim...
    m.closeups.append((t - 0.35, t + T_f, 0.85, launch.lerp(rim, 0.5)))   # the flight seen close
    cup = rim + Vector((-0.045, 0, -0.02))
    t = m.hop(launch, t, rim, t + T_f)
    m.hit(t, 'catch', 1.0)
    T_r = 0.9                                      # ...rattles twice round it (will it drop in?)...

    def rattle(tt, t0=t, cup=cup, T_r=T_r):
        u = min(1.0, (tt - t0) / T_r)
        ang = math.pi * 3.4 * u
        r = 0.065 * (1 - u ** 2.2)                 # it stays out on the rim, then spirals in
        return cup + Vector((r * math.cos(ang), r * math.sin(ang) * 0.8, 0.02 * (1 - u)))
    for k in range(12):
        m.hit(t + 0.072 * k, 'rattle', 1.0 - 0.07 * k)
    m.closeups.append((t, t + T_r, 0.95, cup.copy()))
    t = m.seg(t, t + T_r, rattle)
    out = cup - Vector((0.0, 0, 0.15))            # ...and in, and down through the hole
    m.hit(t, 'whoosh', 0.8)                        # down through the cup: no hole in the sound
    m.hits[-1]['L'] = 0.9
    t = m.hop(cup, t, out, t + 0.2)
    m.hit(t, 'land', 0.6)
    m.parts.append(('jump', O, rk, a_run, a_up, cup))
    return out, 0.3, t


def mech_tilt(m, p, v, t, th):
    Lp, thp = 0.56, math.radians(6.0)
    r = None
    while r is None and thp > math.radians(0.8):
        piv = p + Vector((-Lp / 2 * math.cos(thp), 0, Lp / 2 * math.sin(thp)))
        r = m.roll(Track(p, piv), t, max(v, 0.3))
        if r is None:
            thp *= 0.6
    if r is None:
        return None
    t_on = t
    t, v = r
    v = max(v, 0.08)
    T_tilt, t_p = 0.24, t

    def ride(tt, piv=piv, t_p=t_p, v=v, thp=thp, T_tilt=T_tilt):
        u = tt - t_p
        ang = thp - 2 * thp * smooth(u / T_tilt)    # the plank's rise to the left: +thp, then -thp
        return piv + Vector((-math.cos(ang), 0, math.sin(ang))) * (v * u)
    t = m.seg(t, t + T_tilt, ride)
    m.hit(t, 'clack', 0.9)
    dn = Vector((-math.cos(thp), 0, -math.sin(thp)))
    down = Track(piv + dn * (v * T_tilt), piv + dn * (Lp / 2))
    r = m.roll(down, t, v)
    if r is None:
        return None
    t, v = r
    out = down.b + Vector((-0.08, 0, -0.14))
    t = m.hop(down.b, t, out, t + 0.28)
    m.hit(t, 'land', 0.7)
    m.closeups.append((t_on, t, 0.8, piv - Vector((0, 0, 0.04))))
    m.parts.append(('tilt', piv, Lp, thp, t_p, T_tilt))
    return out, 0.3, t


def mech_spiral(m, p, v, t, th):
    Y = m.Y
    Rf, r_hole, depth = 0.26, 0.04, 0.2
    Oc = Vector((p.x, Y - Rf, p.z))
    D, v_in, steps = 2.0, max(v, 0.6), 240
    traj, phi = [], math.pi / 2

    def r_at(u):
        return r_hole + (Rf - r_hole) * (1 - u ** 1.7)
    for k in range(steps + 1):
        u = k / steps
        rr = r_at(u)
        zz = p.z - depth * ((Rf - rr) / (Rf - r_hole)) ** 1.5
        traj.append((t + u * D, Vector((Oc.x + rr * math.cos(phi), Oc.y + rr * math.sin(phi), zz))))
        if k < steps:
            phi += v_in * Rf / r_at((k + 0.5) / steps) ** 2 * 0.85 * D / steps   # angular momentum

    def spin(tt, traj=traj):
        for (ta, pa), (tb, pb) in zip(traj[:-1], traj[1:]):
            if tt <= tb:
                return pa.lerp(pb, (tt - ta) / max(1e-9, tb - ta))
        return traj[-1][1]
    m.views.append((t, t + D, 40, Oc.copy()))
    m.closeups.append((t, t + D, 0.75, Oc.copy()))   # in close for the whole orbit, not just its last laps
    m.sharp.append((t, t + D))                        # ...and sharp: at full blur the marble smeared into a worm
    m.rolls.append(dict(t0=t, t1=t + D, v0=v_in, v1=v_in * 3, style='funnel'))
    t = m.seg(t, t + D, spin)
    hole = traj[-1][1]
    below = Vector((Oc.x, Oc.y, hole.z - 0.12))
    t = m.hop(hole, t, below, t + 0.15)
    m.hit(t, 'clunk', 0.8)
    out = Vector((Oc.x - Rf - 0.12, Y, below.z - 0.2))
    chute = Track(below, out)
    t2 = t + max(0.25, chute.L / 1.3)
    t = m.seg(t, t2, lambda tt, ch=chute, t0=t, t2=t2: ch.at(ch.L * smooth((tt - t0) / (t2 - t0))))
    m.hit(t, 'land', 0.6)
    m.parts.append(('spiral', Oc, Rf, r_hole, p.z, depth, below, out))
    return out, 0.4, t


def mech_helix(m, p, v, t, th):
    """Two turns down a corkscrew around a pole; in and out at the back, still moving left."""
    Y = m.Y
    rh, turns, pitch = 0.11, 2, 0.15
    circ = 2 * math.pi * rh
    Lh = turns * math.hypot(circ, pitch)
    sin_a, cos_a = pitch / math.hypot(circ, pitch), circ / math.hypot(circ, pitch)
    a0 = ROLL_K * G * sin_a
    res = roll_time(Lh, max(v, 0.3), a0)
    if res is None:
        return None
    T, v1 = res
    ctr = Vector((p.x, Y - rh, p.z))
    v0 = max(v, 0.3)

    def screw(tt, t0=t, T=T, v0=v0):
        s = roll_s(min(tt - t0, T), v0, a0)
        ph = math.pi / 2 + s * cos_a / rh
        return Vector((ctr.x + rh * math.cos(ph), ctr.y + rh * math.sin(ph), ctr.z - s * sin_a))
    m.views.append((t, t + T, 24, None))
    m.rolls.append(dict(t0=t, t1=t + T, v0=v0, v1=v1, style=m.style))
    # a music-box tick each quarter turn, stepping down as the marble winds down (a plain pentatonic fall,
    # nothing from the next piece)
    fall = (91, 88, 86, 84, 81, 79, 76, 74)
    for k in range(4 * turns):                        # from the moment it enters
        rt = roll_time(max(0.01, k * (math.pi / 2) * rh / cos_a), v0, a0)
        if rt and rt[0] < T:
            m.hit(t + rt[0], 'glock', 0.32, fall[k % len(fall)])
    t = m.seg(t, t + T, screw)
    m.parts.append(('helix', ctr, rh, turns, pitch, p.z))
    return screw(t), v1, t


def mech_plinko(m, p, v, t, th):
    """A pegboard: the marble bounces down through the pins, a note on each, into a slot."""
    Y = m.Y
    rows, dx, dz = 7, 0.085, 0.07
    cx, top = p.x - 0.32, p.z - 0.10
    rng = random.Random(int(abs(p.x) * 1000) + 7)
    pin_r = 0.008
    j = 0
    contact = []                                   # marble centre at each pin it strikes
    for k in range(rows):
        x = cx + (j - k / 2) * dx
        contact.append((k, j, Vector((x, Y, top - k * dz + m.R + pin_r - 0.01))))
        j += rng.choice((0, 1))
    entry = contact[0][2] + Vector((0, 0, 0.0))
    m.closeups.append((t - 0.1, t + 0.26 + 0.135 * rows + 0.1, 0.72, Vector((cx, Y, top - rows * dz / 2))))
    t = m.hop(p, t, entry, t + 0.26)
    path = []
    for (k, jj, q), nxt in zip(contact, contact[1:] + [None]):
        col = int(round((q.x - cx) / dx * 2)) + rows
        m.hit(t, 'peg', 1.0, PLINKO_MIDI[min(len(PLINKO_MIDI) - 1, max(0, col // 2))])
        path.append((k, jj, t))
        if nxt is None:
            break
        t = m.hop(q, t, nxt[2], t + 0.135)
    x_slot = contact[-1][2].x + (dx / 2 if rng.random() < 0.5 else -dx / 2)
    slot = Vector((x_slot, Y, top - rows * dz - 0.02))
    t = m.hop(contact[-1][2], t, slot, t + 0.16)
    m.hit(t, 'land', 0.6)
    t = m.fall(slot, t, 0.09)                      # through the slot's trapdoor onto the chute beneath
    under = slot - Vector((0, 0, 0.09))
    out = Vector((cx - (rows / 2 + 1) * dx, Y, under.z - 0.06))
    chute = Track(under, out)
    r = m.roll(chute, t, 0.15)
    if r is None:
        return None
    m.parts.append(('plinko', cx, top, rows, dx, dz, path, pin_r, chute))
    return out, r[1], r[0]


MECH = {'stairs': mech_stairs, 'xylo': mech_xylo, 'dominoes': mech_dominoes, 'bells': mech_bells,
        'loop': mech_loop, 'jump': mech_jump, 'tilt': mech_tilt, 'spiral': mech_spiral, 'helix': mech_helix,
        'plinko': mech_plinko}


# ======================================================================================== planning
WHY = []


def plan(kinds, era, P_L, t_L, P_F, t_F, z_rowA, z_rowB, R, Y):
    """Lay out and time one machine from the last note (P_L at t_L) to the first note of the next piece
    (P_F at t_F). Every rail angle from 2 to 20 degrees is tried; the gentlest that arrives in time wins
    (refined between it and the last late one)."""
    target = t_F - T_HOP_OUT - T_KICK - 0.05          # arrival at the spring (a short squeeze before it fires)
    WHY.clear()

    def sim(th):
        return _simulate(kinds, era, P_L, t_L, P_F, z_rowA, z_rowB, R, Y, th)
    grid = [(math.radians(2.0 + 0.25 * k), None) for k in range(73)]
    ok = [(th, mm) for th, mm in ((th, sim(th)) for th, _ in grid) if mm is not None]
    if not ok:
        raise ValueError(f"no layout for the {'+'.join(kinds)} machine between t={t_L:.2f} and t={t_F:.2f}: "
                         'give it more time or room; tried: ' + ' | '.join(WHY[-4:]))
    early = [(th, mm) for th, mm in ok if mm.t_arrive <= target]
    if not early:                    # even the steepest rails arrive late: say so, never pass it off as on time
        th, best = min(ok, key=lambda x: x[1].t_arrive)
        best.late = best.t_arrive - target
    else:
        th, best = min(early, key=lambda x: x[0])
        late = [(t2, m2) for t2, m2 in ok if t2 < th and m2.t_arrive > target]
        if late:
            lo, hi = max(late, key=lambda x: x[0])[0], th
            for _ in range(30):
                mid = (lo + hi) / 2
                mm = sim(mid)
                if mm is None:
                    break
                if mm.t_arrive > target:
                    lo = mid
                else:
                    hi, best = mid, mm
    best.late = getattr(best, 'late', 0.0)
    _finish(best, P_F, t_F)
    best.box = best.frame_box()
    return best


def _simulate(kinds, era, P_L, t_L, P_F, z_rowA, z_rowB, R, Y, th):
    m = Machine(kinds, STYLE[era], R, Y)
    m.theta = th
    E = Vector((P_F.x - 0.32, Y, z_rowB + 0.80))
    C1 = Vector((max(P_L.x + 0.14, E.x + width_need(kinds)), Y, min(P_L.z - 0.30, z_rowA - 0.36)))
    t = m.hop(P_L, t_L, C1, t_L + T_HOP_IN)
    m.hit(t, 'land', 0.6)
    st = rail(m, C1, 0.3, t, W_T1, th)
    if st is None:
        WHY.append('first rail')
        return None
    p, v, t = st
    m.parts.append(('cap', C1))
    for k, kind in enumerate(kinds):
        st = MECH[kind](m, p, v, t, th)
        if st is None:
            WHY.append(f'{kind} at {math.degrees(th):.1f} deg')
            return None
        p, v, t = st
        if k < len(kinds) - 1:
            st = rail(m, p, v, t, W_LINK, th)
            if st is None:
                WHY.append('link rail')
                return None
            p, v, t = st
    # a drop onto the last rail, which runs to the spring
    c = Vector((p.x - 0.04, Y, 0.0))
    c.z = E.z + (c.x - E.x) * math.tan(th)
    dz = p.z - c.z
    if dz < 0.04 or dz > 0.75 or c.x - E.x < W_LAST_MIN:
        WHY.append(f'last drop dz={dz:.2f} room={c.x - E.x:.2f} at {math.degrees(th):.1f} deg')
        return None
    m.hit(t, 'wall', 0.5)
    m.parts.append(('wall', p))
    t = m.fall(p, t, dz)
    m.hit(t, 'land', 0.7)
    tr = Track(Vector((p.x, Y, c.z)), E)
    r = m.roll(tr, t, 0.0)
    if r is None:
        WHY.append('last rail')
        return None
    m.parts.append(('rail', tr))
    m.parts.append(('rings', tr, t))
    m.t_arrive, m.v_arrive, m.E_ = r[0], r[1], E
    m.t_last_rail = t
    return m


def _finish(m, P_F, t_F):
    """The spring: squeeze, (wait), fire onto the first note of the next piece."""
    t, E = m.t_arrive, m.E_
    squeeze = E + Vector((-0.025, 0, 0))
    t_launch, t_sq = t_F - T_HOP_OUT, t + T_KICK
    m.seg(t, t_sq, lambda tt, t0=t: E.lerp(squeeze, smooth((tt - t0) / T_KICK)))
    m.hit(t, 'spring', 0.8)
    if t_launch > t_sq:
        m.hold(squeeze, t_sq, t_launch)
    m.t_kick = max(t_launch, t_sq)
    m.wait = max(0.0, t_launch - t_sq)
    m.hit(m.t_kick, 'boing', 0.9)
    m.hop(squeeze, m.t_kick, P_F, t_F)


def time_at_x(m, x, t0, t1):
    """When the marble passes x (moving left) between t0 and t1."""
    lo, hi = t0, t1
    for _ in range(40):
        mid = (lo + hi) / 2
        if m.pos(mid).x > x:
            lo = mid
        else:
            hi = mid
    return hi


# ======================================================================================== building
def build(m, h):
    """Make the machine's parts. h holds the film's helpers: cube, cyl, sphere, torus, cone, mat, emit_keys,
    fr, revolve (a surface of revolution), glass, clear (materials), neon (colour), WALL_Y."""
    st = m.style
    if st == 'wood':
        rail_m = h.mat('m_wood', (0.33, 0.18, 0.08), 0.45, coat=0.4)
        arm_m = h.mat('m_brass', (0.88, 0.64, 0.26), 0.25, metal=1.0)
    elif st == 'gold':
        rail_m = h.mat('m_gold', (0.95, 0.75, 0.36), 0.18, metal=1.0)
        arm_m = h.mat('m_ebony', (0.05, 0.06, 0.12), 0.3, coat=0.8)     # ebony against the pale salon walls
    elif st == 'steel':
        rail_m = h.mat('m_steel', (0.9, 0.91, 0.95), 0.32, metal=1.0)     # satin: it catches the key light
        arm_m = h.mat('m_dark', (0.12, 0.12, 0.14), 0.35, metal=0.8)
    else:
        rail_m = h.mat('m_brass2', (0.9, 0.62, 0.28), 0.2, metal=1.0)
        arm_m = h.mat('m_walnut', (0.25, 0.12, 0.06), 0.4, coat=0.5)
    brass = h.mat('m_brass3', (0.88, 0.64, 0.26), 0.22, metal=1.0)
    lift, W, R, Y = m.lift, h.WALL_Y, m.R, m.Y

    def rails(a, b, n, arms=True):
        """Two rails under the marble's path from a to b (marble-centre points); n points from the rails
        towards the marble's centre."""
        a0, b0 = a - n * lift, b - n * lift
        side = (b0 - a0).cross(n)
        side = side.normalized() * RAIL_HALF if side.length > 1e-6 else Vector((0, RAIL_HALF, 0))
        for sy in (-1, 1):
            h.cyl(a0 + side * sy, b0 + side * sy, RAIL_R, rail_m, 10)
        if not arms:
            return
        L = (b0 - a0).length
        k = max(1, int(L / 0.45) + 1)
        for j in range(k):
            q = a0.lerp(b0, (j + 0.5) / k) - Vector((0, 0, 0.012))
            h.cyl(Vector((q.x, W, q.z)), Vector((q.x, q.y - RAIL_HALF, q.z)), 0.005, arm_m, 8)
            h.cube((q.x, q.y, q.z), (0.012, 2 * RAIL_HALF + 0.012, 0.006), arm_m)

    def endstop(p, side):
        """A stop beside a marble at p (side -1: on its left, +1: on its right)."""
        h.cube((p.x + side * (R + 0.012), p.y, p.z - lift + 0.02), (0.014, 2 * RAIL_HALF + 0.02, 0.07), arm_m)

    def curve(points, centre_of, arms_every=6):
        for k, (a_, b_) in enumerate(zip(points[:-1], points[1:])):
            mid = (a_ + b_) / 2
            c = centre_of(mid)
            n = (c - mid)
            n = Vector((n.x, 0, n.z)).normalized() if abs(n.x) + abs(n.z) > 1e-6 else Vector((0, 0, 1))
            rails(a_, b_, n, arms=(k % arms_every == 0))

    for part in m.parts:
        kind = part[0]
        if kind == 'rail':
            tr = part[1]
            rails(tr.a, tr.b, tr.n)
        elif kind == 'cap':
            endstop(part[1], +1)
        elif kind == 'wall':
            endstop(part[1], -1)
        elif kind == 'rings':
            # chase lamps on little posts above the long rail, each lighting as the marble passes under it
            # (rings round the rail were seen edge-on from the front and read as plates it passed through)
            tr, t0 = part[1], part[2]
            n_r = max(3, int(tr.L / 0.26))
            for k in range(n_r):
                s_k = tr.L * (k + 0.7) / (n_r + 0.4)
                c = tr.at(s_k)
                cc = getattr(h, 'chase', h.neon)          # the colour the marble takes as it passes them
                rm = h.mat(f'chase{k}', cc, 0.2, emit=cc, emit_s=0.3)
                top = Vector((c.x, Y + 0.035, c.z + 0.15))
                h.cyl(Vector((c.x, Y + 0.035, c.z - lift)), top, 0.004, arm_m, 8)
                h.sphere(top + Vector((0, 0, 0.014)), 0.016, rm, segs=16)
                tp = time_at_x(m, c.x, t0, m.t_arrive)
                h.emit_keys(rm, ((tp - 0.05, 0.3), (tp, 22.0), (tp + 0.4, 2.0)))
                m.hit(tp, 'chase', 0.55)                  # a note each; film8 tunes them up into the next piece
        elif kind in ('stairs', 'xylo'):
            steps, hs, ws = part[1], part[2], part[3]
            for k, (q, t_hit) in enumerate(steps):
                top = q.z - R
                if kind == 'xylo':
                    hue = XYLO_HUE[k]
                    bm = h.mat(f'xylo{k}', hue, 0.25, metal=0.6, emit=hue, emit_s=0.0)
                    h.cube((q.x, q.y, top - 0.008), (ws * 0.9, 0.08 - 0.004 * k, 0.016), bm)
                    h.emit_keys(bm, ((t_hit - 0.04, 0.0), (t_hit, 25.0), (t_hit + 0.5, 1.2)))
                    for sx in (-1, 1):
                        h.cyl(Vector((q.x + sx * ws * 0.3, W, top - 0.022)),
                              Vector((q.x + sx * ws * 0.3, q.y + 0.02, top - 0.022)), 0.004, arm_m, 8)
                else:
                    h.cube((q.x, q.y, top - 0.5 * hs), (ws, 0.09, hs), rail_m)
                    h.cyl(Vector((q.x, W, top - 0.5 * hs)), Vector((q.x, q.y + 0.045, top - 0.5 * hs)), 0.006, arm_m, 8)
        elif kind == 'dominoes':
            tr, doms = part[1], part[2]
            # black lacquered dominoes with ivory pips, big enough to read (they were white slivers on white)
            dm = h.mat('domino', (0.03, 0.03, 0.04), 0.18, coat=1.0)
            pip = h.mat('dominopip', (0.95, 0.93, 0.86), 0.3)
            board = -tr.n * lift
            DT, DD, DH = 0.018, 0.06, 0.12
            for k, (s_k, t_k) in enumerate(doms):
                foot = tr.at(s_k) + board                 # middle of the domino's foot, on the board
                o = h.cube((0, 0, 0), (DT, DD, DH), dm)
                for pz in (0.025, -0.025):                # two pips on the face toward the camera
                    pp = h.sphere((0, 0, 0), 0.006, pip, scale=(0.6 / DT, 0.25 / DD, 0.6 / DH), segs=10)
                    pp.parent = o                         # (in the domino's unit-cube space, so undo its scale)
                    pp.location = (0, -0.5, pz / DH)
                final = math.radians(60 if k < len(doms) - 1 else 86)
                for u in (-0.5, 0.0, 0.05, 0.10, 0.14, 0.17):
                    a = final * min(1.0, max(0.0, u / 0.17)) ** 2       # it tips, then speeds up
                    piv = foot + Vector((-DT / 2, 0, 0))                 # it turns about its left edge
                    vx, vz = DT / 2, DH / 2
                    o.location = piv + Vector((vx * math.cos(a) - vz * math.sin(a), 0, vx * math.sin(a) + vz * math.cos(a)))
                    o.rotation_euler = (0, -a, 0)
                    o.keyframe_insert('location', frame=h.fr(t_k + u))
                    o.keyframe_insert('rotation_euler', frame=h.fr(t_k + u))
            mid = tr.at((doms[0][0] + doms[-1][0]) / 2) + board - Vector((0, 0, 0.004))
            plank = h.cube(tuple(mid), (doms[-1][0] - doms[0][0] + 0.1, 0.05, 0.006), arm_m)
            plank.rotation_euler = (0, -math.atan2(tr.d.z, tr.d.x) + math.pi, 0)
        elif kind == 'bells':
            tr, bells = part[1], part[2]
            for k, (s_k, t_k, mid) in enumerate(bells):
                c = tr.at(s_k)
                bm = h.mat(f'bell{k}', (0.95, 0.74, 0.32), 0.15, metal=1.0, emit=(1.0, 0.8, 0.4), emit_s=0.0)
                top = Vector((c.x, Y - 0.085, c.z + 0.10))
                bell = h.cone(top - Vector((0, 0, 0.035)), 0.034, 0.008, 0.05, bm, 24)
                h.cyl(Vector((c.x, W, top.z + 0.01)), Vector((c.x, top.y, top.z + 0.01)), 0.004, arm_m, 8)
                h.cyl(top - Vector((0, 0, 0.03)), Vector((c.x, Y - 0.05, c.z)), 0.0025, arm_m, 6)   # its striker
                h.emit_keys(bm, ((t_k - 0.03, 0.0), (t_k, 9.0), (t_k + 0.6, 0.3)))
                for u, ang in ((-0.4, 0.0), (0.0, 0.0), (0.06, 0.25), (0.2, -0.15), (0.38, 0.08), (0.6, 0.0)):
                    bell.rotation_euler = (0, ang, 0)                     # it swings as it rings
                    bell.keyframe_insert('rotation_euler', frame=h.fr(t_k + u))
        elif kind == 'loop':
            O, rq, Cl, rl = part[1:]
            pts = [Vector((O.x + rq * math.cos(-math.pi / 2 * k / 30), Y + 0.04 * k / 30,
                           O.z + rq * math.sin(-math.pi / 2 * k / 30))) for k in range(31)]
            curve(pts, lambda mid: O)                          # the quarter-pipe
            lp = [Vector((Cl.x - rl * math.sin(2 * math.pi * k / 48), Y + 0.04 - 0.08 * k / 48,
                          Cl.z - rl * math.cos(2 * math.pi * k / 48))) for k in range(49)]
            curve(lp, lambda mid: Cl, arms_every=8)            # and the loop
        elif kind == 'jump':
            O, rk, a_run, a_up, cup = part[1:]
            pts = []
            for k in range(13):
                a = a_run - (a_run + a_up) * k / 12
                pts.append(O + Vector((rk * math.sin(a), 0, -rk * math.cos(a))))
            curve(pts, lambda mid: O)
            cm = h.mat('cup', (0.9, 0.66, 0.3), 0.18, metal=1.0)
            h.revolve(Vector((cup.x, Y, 0)), [(R + 0.012, cup.z - R - 0.02), (R + 0.03, cup.z - R + 0.02), (R + 0.05, cup.z - R + 0.06)], cm)
            h.cyl(Vector((cup.x, W, cup.z - R)), Vector((cup.x, Y + 0.06, cup.z - R)), 0.006, arm_m, 8)
        elif kind == 'tilt':
            piv, Lp, thp, t_p, T_tilt = part[1:]
            centre = piv - Vector((0, 0, lift + 0.008))
            plank_m = h.mat('plank', (0.86, 0.80, 0.68), 0.38, coat=0.5)          # pale maple: it reads on any wall
            plank = h.cube(tuple(centre), (Lp, 2 * RAIL_HALF + 0.024, 0.012), plank_m)
            for u, f in ((-1.0, 0.0), (0.0, 0.0), (T_tilt * 0.8, 0.9), (T_tilt, 1.0), (T_tilt + 0.06, 0.95),
                         (T_tilt + 0.14, 1.0)):
                plank.rotation_euler = (0, thp - 2 * thp * f, 0)     # left end up, then down
                plank.keyframe_insert('rotation_euler', frame=h.fr(t_p + u))
            h.cyl(Vector((centre.x, W, centre.z - 0.012)), Vector((centre.x, centre.y - 0.05, centre.z - 0.012)), 0.008, arm_m, 12)
            for sx in (-1, 1):                          # the two stops it rests on
                h.cube((centre.x + sx * (Lp / 2 - 0.03), centre.y, centre.z - Lp / 2 * math.sin(thp) - 0.025),
                       (0.02, 0.05, 0.03), arm_m)
        elif kind == 'spiral':
            Oc, Rf, r_hole, z_rim, depth, below, out = part[1:]
            fm = h.mat('funnel', (0.9, 0.66, 0.3) if st != 'steel' else (0.88, 0.9, 0.95), 0.38, metal=1.0)   # brushed
            prof = []
            for k in range(25):
                rr = r_hole + (Rf - r_hole) * k / 24
                zz = z_rim - depth * ((Rf - rr) / (Rf - r_hole)) ** 1.5 - R
                prof.append((rr + 0.004, zz))
            prof.append((Rf + 0.05, z_rim - R + 0.02))   # the lip
            h.revolve(Oc, prof, fm)
            h.cyl(Vector((Oc.x, Oc.y, prof[0][1])), below - Vector((0, 0, 0.03)), r_hole + 0.006, fm, 20)
            h.cyl(below, out, R + 0.004, h.clear, 24)          # the glass chute back to the rails
            for a_ in (0.7, 2.45):
                q = Vector((Oc.x + Rf * math.cos(a_), Oc.y + Rf * math.sin(a_), z_rim - R))
                h.cyl(Vector((q.x, W, q.z)), q, 0.006, arm_m, 8)
        elif kind == 'helix':
            ctr, rh, turns, pitch, z0 = part[1:]
            n_seg = 28 * turns
            for sgn in (-1, 1):                               # two rails, inside and outside of the track
                rr = rh + sgn * RAIL_HALF
                prev = None
                for k in range(n_seg + 1):
                    ph = math.pi / 2 + 2 * math.pi * turns * k / n_seg
                    q = Vector((ctr.x + rr * math.cos(ph), ctr.y + rr * math.sin(ph), z0 - lift - pitch * turns * k / n_seg))
                    if prev is not None:
                        h.cyl(prev, q, RAIL_R, rail_m, 8)
                    prev = q
            h.cyl(Vector((ctr.x, ctr.y, z0 + 0.08)), Vector((ctr.x, ctr.y, z0 - pitch * turns - 0.12)), 0.014, brass, 16)
            h.cyl(Vector((ctr.x, W, z0 + 0.06)), Vector((ctr.x, ctr.y, z0 + 0.06)), 0.007, arm_m, 8)
            for k in range(turns * 4):                         # spokes from the pole to the track
                ph = math.pi / 2 + math.pi / 2 * k + math.pi / 4
                zq = z0 - lift - 0.012 - pitch * (k + 0.5) / 4
                h.cyl(Vector((ctr.x, ctr.y, zq)), Vector((ctr.x + (rh + RAIL_HALF) * math.cos(ph), ctr.y + (rh + RAIL_HALF) * math.sin(ph), zq)),
                      0.004, arm_m, 6)
        elif kind == 'plinko':
            cx, top, rows, dx, dz, path, pin_r, chute = part[1:]
            board_m = h.mat('pegboard', (0.84, 0.80, 0.70), 0.5, coat=0.5)        # a pale board, dark pins
            wdt = (rows + 1) * dx + 0.06
            h.cube((cx, Y + 0.043, top - (rows * dz) / 2 + 0.02), (wdt, 0.01, rows * dz + 0.18), board_m)   # before the page trim
            struck = {(k, j): t for k, j, t in path}
            for k in range(rows):
                for j in range(k + 1):
                    x = cx + (j - k / 2) * dx
                    z = top - k * dz
                    pm = h.mat(f'pin{k}_{j}', (0.10, 0.09, 0.10), 0.3, metal=0.6, emit=h.neon, emit_s=0.0)
                    h.cyl(Vector((x, Y + 0.07, z)), Vector((x, Y - 0.035, z)), pin_r, pm, 8)
                    if (k, j) in struck:
                        tk = struck[(k, j)]
                        h.emit_keys(pm, ((tk - 0.02, 0.0), (tk, 18.0), (tk + 0.4, 0.6)))
            for j in range(rows + 2):                           # slot dividers at the bottom
                x = cx + (j - (rows + 1) / 2) * dx
                h.cube((x, Y, top - rows * dz - 0.05), (0.006, 0.09, 0.07), arm_m)
            rails(chute.a, chute.b, chute.n)
    # the spring at the end: a plate on a coil, against a block on the wall
    E = m.E_
    px = E.x - R - 0.008
    plate = h.cube((px, E.y, E.z), (0.01, 0.07, 0.1), arm_m)
    sm = h.mat('spring', (0.85, 0.85, 0.9), 0.15, metal=1.0)
    coils = [h.torus(Vector((px - 0.017 - k * 0.012, E.y, E.z)), 0.022, 0.003, sm, rot=(0, math.radians(90), 0))
             for k in range(5)]
    h.cube((px - 0.085, E.y, E.z), (0.012, 0.08, 0.12), arm_m)
    h.cyl(Vector((px - 0.085, W, E.z)), Vector((px - 0.085, E.y + 0.04, E.z)), 0.006, arm_m, 8)
    t_in, t_k = m.t_arrive, m.t_kick
    for tt, dxp in ((t_in - 0.02, 0.0), (t_in + T_KICK, -0.025), (t_k, -0.028), (t_k + 0.04, 0.006),
                    (t_k + 0.12, 0.0)):
        plate.location = (px + dxp, E.y, E.z)
        plate.keyframe_insert('location', frame=h.fr(tt))
        for k, c in enumerate(coils):
            c.location = (px - 0.017 - k * 0.012 * (1 + dxp / 0.07) + dxp * 0.2, E.y, E.z)
            c.keyframe_insert('location', frame=h.fr(tt))
