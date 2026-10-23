"""Interlude machines for the score film: a short Pythagora-switch run between two pieces.

While the music rests, the marble leaves the last note of one piece and travels through a small machine to
the first note of the next: a short rail to the right, one mechanism, a long rail back across the page, and
a spring that flicks it onto the first note. The mechanisms:
  stairs    wooden steps, a knock on each one
  xylo      eight tuned bars as steps: a descending C major scale on the way down
  dominoes  the marble topples a line of dominoes and rattles over them as they fall
  loop      a drop into a quarter-pipe and a loop-the-loop
  tilt      a seesaw plank that flips when the marble rolls past its pivot
  spiral    a funnel: the marble circles faster and faster and drops through the hole (seen from above)
  loopdom   a loop, then dominoes
Nothing is keyframed by hand; the motion is computed:
  rolling on rails   a = 5/7 g sin(angle) (a rolling solid sphere), less rolling resistance DRAG * v
  falls and hops     ballistic, g = 9.81
  the loop           energy: v^2 = v_in^2 - 10/7 g dh, so the marble slows over the top
  the funnel         angular momentum: it spins faster as it nears the hole
The machine has to take exactly the time the music leaves for it, so the rail angle is solved for that; if
even the gentlest angle is too quick, the spring holds the marble a moment before it fires.
"""
import math

from mathutils import Vector

G = 9.81
ROLL_K = 5 / 7            # a rolling solid sphere accelerates at 5/7 of g sin(angle)
DRAG = 1.1                # rolling resistance on the rails (1/s): speed settles near a / DRAG
RAIL_HALF, RAIL_R = 0.030, 0.0045
T_HOP_IN, T_HOP_OUT, T_KICK = 0.40, 0.42, 0.06
XYLO_MIDI = [84, 83, 81, 79, 77, 76, 74, 72]          # C6 B5 A5 G5 F5 E5 D5 C5
XYLO_HUE = [(0.95, 0.2, 0.25), (1.0, 0.5, 0.1), (1.0, 0.85, 0.15), (0.3, 0.85, 0.3),
            (0.15, 0.7, 0.95), (0.25, 0.4, 0.95), (0.6, 0.3, 0.9), (0.95, 0.3, 0.7)]
STYLE = {'baroque': 'wood', 'classical': 'gold', 'beethoven': 'steel', 'romantic': 'brass'}
DOM_GAP, DOM_DT = 0.042, 0.034                        # domino spacing and the time between falls


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


class Track:
    """A straight run of the marble's centre from a to b (the rails lie `lift` below it, along the normal)."""

    def __init__(self, a, b):
        self.a, self.b = a.copy(), b.copy()
        d = b - a
        self.L = d.length
        self.d = d / self.L
        n = Vector((-self.d.z, 0, self.d.x))
        self.n = n if n.z > 0 else -n
        self.sin = -self.d.z                    # > 0 going downhill

    def at(self, s):
        return self.a + self.d * s


class Machine:
    def __init__(self, kind, style, R, Y):
        self.kind, self.style, self.R, self.Y = kind, style, R, Y
        self.lift = math.sqrt((R + RAIL_R) ** 2 - RAIL_HALF ** 2)   # marble centre above the rail axes
        self.segs, self.hits, self.rolls, self.parts = [], [], [], []
        self.spiral = None                      # (t0, t1, funnel centre): the camera looks down into it
        self.t_kick, self.wait = None, 0.0

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

    def roll(self, tr, t0, v0, s0=0.0, s1=None, bump=None):
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
        self.rolls.append(dict(t0=t0, t1=t0 + T, v0=v0, v1=v1, style=self.style))
        return t0 + T, v1

    def hop(self, p0, t0, p1, t1):
        return self.seg(t0, t1, lambda t, p0=p0.copy(), p1=p1.copy(), t0=t0, t1=t1: ballistic(p0, t0, p1, t1, t))

    def hold(self, p, t0, t1):
        return self.seg(t0, t1, lambda t, p=p.copy(): p)

    def fall(self, p0, t0, h):
        T = math.sqrt(2 * h / G)
        return self.seg(t0, t0 + T, lambda t, p0=p0.copy(), t0=t0: p0 - Vector((0, 0, 0.5 * G * (t - t0) ** 2)))

    def hit(self, t, kind, g=1.0, midi=None):
        self.hits.append(dict(t=t, kind=kind, g=g, midi=midi))

    def elev(self, t):
        """Camera elevation (radians): it rises to look down into the funnel, then comes back down."""
        if not self.spiral:
            return 0.0
        a, b, _ = self.spiral
        return math.radians(40) * smooth((t - (a - 0.7)) / 0.7) * (1 - smooth((t - b) / 0.6))

    def attention(self, t):
        """What the camera follows: the marble, or the funnel's centre while the marble circles in it."""
        p = self.pos(t)
        if self.spiral:
            a, b, c = self.spiral
            k = smooth((t - (a - 0.5)) / 0.5) * (1 - smooth((t - b) / 0.5))
            p = p.lerp(Vector((c.x, p.y, c.z - 0.08)), k)
        return p


# ======================================================================================== planning
def plan(kind, era, P_L, t_L, P_F, t_F, z_rowA, z_rowB, R, Y):
    """Lay out and time one interlude machine from the last note (P_L at t_L) to the first note of the
    next piece (P_F at t_F). The rail angle is chosen so the marble reaches the spring on time: every
    angle from 2 to 20 degrees is tried, then the best one is refined."""
    target = t_F - T_HOP_OUT - T_KICK - 0.05          # arrival at the spring (a short squeeze before it fires)
    WHY.clear()

    def sim(th):
        return _simulate(kind, era, P_L, t_L, P_F, z_rowA, z_rowB, R, Y, th)
    grid = [(math.radians(2.0 + 0.25 * k), None) for k in range(73)]
    grid = [(th, sim(th)) for th, _ in grid]
    ok = [(th, m) for th, m in grid if m is not None]
    if not ok:
        raise ValueError(f'no layout for the {kind} machine between t={t_L:.2f} and t={t_F:.2f}: '
                         'give this interlude more time or room; tried: ' + ' | '.join(WHY[-4:]))
    early = [(th, m) for th, m in ok if m.t_arrive <= target]
    if not early:
        th, best = min(ok, key=lambda x: x[1].t_arrive)        # as quick as it gets (the hop will be late)
    else:
        th, best = min(early, key=lambda x: x[0])               # the gentlest rails that make it in time
        late = [(t2, m2) for t2, m2 in ok if t2 < th and m2.t_arrive > target]
        if late:                                                # refine between the last late and first early
            lo, hi = max(late, key=lambda x: x[0])[0], th
            for _ in range(30):
                mid = (lo + hi) / 2
                m = sim(mid)
                if m is None:
                    break
                if m.t_arrive > target:
                    lo = mid
                else:
                    hi, best = mid, m
    _finish(best, P_F, t_F)
    return best


WHY = []


def _why(where, env):
    """Note why a layout failed (for the error message), and fail."""
    keys = ('dz', 'hs', 'rq', 'depth', 'thp', 'W2')
    WHY.append(f"{where} " + ' '.join(f"{k}={env[k]:.3f}" for k in keys if isinstance(env.get(k), float)))
    return None


def _simulate(kind, era, P_L, t_L, P_F, z_rowA, z_rowB, R, Y, th):
    """Everything flows right to left: under the last note, a short rail, the mechanism, a longer rail,
    and the spring above the start of the next page."""
    m = Machine(kind, STYLE[era], R, Y)
    m.theta = th
    tn = math.tan(th)
    mech = 'loop' if kind == 'loopdom' else kind
    y2 = Y - 0.04 if mech == 'loop' else Y           # after the loop's helix the rail runs 4 cm further out
    E = Vector((P_F.x - 0.32, Y, z_rowB + 0.80))
    n_st, ws = (8, 0.10) if mech == 'xylo' else (6, 0.11)
    Lp, Rf = 0.56, 0.26
    W_m = {'stairs': n_st * ws + 0.07, 'xylo': n_st * ws + 0.07, 'dominoes': 0.0, 'tilt': Lp + 0.07,
           'spiral': Rf + 0.12, 'loop': 0.55}[mech]
    C1 = Vector((max(P_L.x + 0.14, E.x + W_m + 1.0), Y, min(P_L.z - 0.30, z_rowA - 0.36)))
    W_roll = C1.x - E.x - W_m
    W1 = min(1.1, max(0.45, 0.35 * W_roll))
    x1e = C1.x - W1
    t = m.hop(P_L, t_L, C1, t_L + T_HOP_IN)
    m.hit(t, 'land', 0.6)
    tr1 = Track(C1, Vector((x1e, Y, C1.z - W1 * tn)))
    r = m.roll(tr1, t, 0.3)
    if r is None:
        return None
    t, v = r
    m.parts.append(('rail', tr1, 'T1'))
    p = tr1.b

    def rail2_start(x):
        return Vector((x, y2, E.z + (x - E.x) * tn))
    # ---------------------------------------------------------------- the mechanism
    if mech in ('stairs', 'xylo'):
        c2 = rail2_start(x1e - n_st * ws - 0.07)
        dz = p.z - c2.z
        hs = dz / (n_st + 1)
        if not 0.035 <= hs <= 0.2:
            return None
        Ts = 0.17 if mech == 'xylo' else 0.19
        prev, steps = p, []
        for k in range(n_st):
            q = Vector((x1e - (k + 0.5) * ws, Y, p.z - (k + 1) * hs))
            t = m.hop(prev, t, q, t + Ts)
            steps.append((q, t))
            if mech == 'xylo':
                m.hit(t, 'glock', 1.0, XYLO_MIDI[k])
            else:
                m.hit(t, 'wood', 0.85 - 0.05 * k)
            prev = q
        t = m.hop(prev, t, c2, t + Ts)
        m.hit(t, 'land', 0.7)
        m.parts.append((mech, steps, hs, ws))
        v = 0.35
    elif mech == 'dominoes':
        c2 = rail2_start(x1e + 0.03)
        dz = p.z - c2.z
        if dz < 0.12:
            return None
        m.hit(t, 'wall', 0.7)
        t = m.fall(p, t, dz)
        m.hit(t, 'land', 0.8)
        m.parts.append(('wall', p))
        v = 0.0
    elif mech == 'tilt':
        thp = math.radians(6.0)
        c2 = rail2_start(x1e - Lp - 0.07)
        r = None
        while r is None and thp > math.radians(0.8):
            piv = p + Vector((-Lp / 2 * math.cos(thp), 0, Lp / 2 * math.sin(thp)))
            r = m.roll(Track(p, piv), t, v)
            if r is None:
                thp *= 0.6
        if r is None:
            return None
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
        end = down.b
        if end.z - c2.z < 0.06:
            return _why('tilt drop', dict(dz=end.z - c2.z))
        t = m.hop(end, t, c2, t + 0.30)
        m.hit(t, 'land', 0.7)
        m.parts.append(('tilt', piv, Lp, thp, t_p, T_tilt))
        v = 0.3
    elif mech == 'spiral':
        r_hole = 0.04
        c2 = rail2_start(x1e - Rf - 0.12)
        dz = p.z - c2.z
        depth = min(0.22, dz - 0.32)
        if depth < 0.08:
            return None
        Oc = Vector((x1e, Y - Rf, p.z))
        D, v_in, steps = 2.1, max(v, 0.6), 240
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
        m.spiral = (t, t + D, Oc.copy())
        m.rolls.append(dict(t0=t, t1=t + D, v0=v_in, v1=v_in * 3, style='funnel'))
        t = m.seg(t, t + D, spin)
        hole = traj[-1][1]
        below = Vector((Oc.x, Oc.y, hole.z - 0.12))
        t = m.hop(hole, t, below, t + 0.15)
        m.hit(t, 'clunk', 0.8)
        chute = Track(below, c2)
        t2 = t + max(0.25, chute.L / 1.3)
        t = m.seg(t, t2, lambda tt, ch=chute, t0=t, t2=t2: ch.at(ch.L * smooth((tt - t0) / (t2 - t0))))
        m.hit(t, 'land', 0.6)
        m.parts.append(('spiral', Oc, Rf, r_hole, p.z, depth, below, c2))
        v = 0.4
    elif mech == 'loop':
        h_ff = 0.12
        # the quarter-pipe's bottom starts the second rail; its radius takes up the remaining height
        rq = (p.z - h_ff - E.z - (x1e - E.x) * tn) / (1 - tn)
        if not 0.2 <= rq <= 1.3:
            return None
        O = Vector((x1e - rq, Y, p.z - h_ff))
        c2 = Vector((x1e - rq, y2, p.z - h_ff - rq))
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
        t = m.seg(t, t + Tq, quarter)
        rl = min(0.17, 0.55 * v_B ** 2 / (27 / 7 * G))
        Cl = Vector((c2.x, Y, c2.z + rl))
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
        t = m.seg(t, t + Tl, loop)
        m.parts.append(('loop', O, rq, Cl, rl))
        v = v_B
    # ---------------------------------------------------------------- the rail on to the spring
    E_ = Vector((E.x, y2, E.z))
    W2 = c2.x - E.x
    if W2 < 0.4:
        return None
    tr2 = Track(c2, E_)
    if tr2.sin <= 0:
        return None
    m.parts.append(('rail', tr2, 'T2'))
    if kind in ('dominoes', 'loopdom'):
        s_d0 = 0.28 if kind == 'dominoes' else 0.55
        n_dom = int(min(26, (tr2.L - s_d0 - 0.3) / DOM_GAP))
        if n_dom < 8:
            return None
        r = m.roll(tr2, t, v, 0.0, s_d0)
        if r is None:
            return None
        t, v = r
        m.hit(t, 'domino', 1.0)
        doms = [(s_d0 + 0.02 + k * DOM_GAP, t + k * DOM_DT) for k in range(n_dom)]
        for s_k, t_k in doms[1:]:
            m.hit(t_k, 'domino', 0.55)
        s_end = doms[-1][0] + 0.06

        def bump(s, s_d0=s_d0, s_end=s_end):
            return 0.034 * smooth((s - s_d0) / 0.05) * (1 - smooth((s - s_end) / 0.05))
        r = m.roll(tr2, t, min(v, 0.12), s_d0, tr2.L, bump)
        if r is None:
            return None
        t, v = r
        m.parts.append(('dominoes', tr2, doms))
    else:
        r = m.roll(tr2, t, v)
        if r is None:
            return None
        t, v = r
    m.t_arrive, m.v_arrive, m.E_ = t, v, E_
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


# ======================================================================================== building
def build(m, h):
    """Make the machine's parts. h holds the film's helpers: cube, cyl, sphere, torus, mat, emit_keys,
    fr, revolve (a surface of revolution), glass (material), WALL_Y."""
    st = m.style
    if st == 'wood':
        rail_m = h.mat('m_wood', (0.33, 0.18, 0.08), 0.45, coat=0.4)
        arm_m = h.mat('m_brass', (0.88, 0.64, 0.26), 0.25, metal=1.0)
    elif st == 'gold':
        rail_m = h.mat('m_gold', (0.95, 0.75, 0.36), 0.18, metal=1.0)
        arm_m = h.mat('m_ivory', (0.93, 0.92, 0.88), 0.3, coat=0.8)
    elif st == 'steel':
        rail_m = h.mat('m_steel', (0.9, 0.91, 0.95), 0.12, metal=1.0)
        arm_m = h.mat('m_dark', (0.12, 0.12, 0.14), 0.35, metal=0.8)
    else:
        rail_m = h.mat('m_brass2', (0.9, 0.62, 0.28), 0.2, metal=1.0)
        arm_m = h.mat('m_walnut', (0.25, 0.12, 0.06), 0.4, coat=0.5)
    lift, W, R, Y = m.lift, h.WALL_Y, m.R, m.Y

    def rails(a, b, n, arms=True):
        """Two rails under the marble's path from a to b (marble-centre points); n points from the rails
        towards the marble's centre."""
        a0, b0 = a - n * lift, b - n * lift
        for sy in (-1, 1):
            off = Vector((0, sy * RAIL_HALF, 0))
            h.cyl(a0 + off, b0 + off, RAIL_R, rail_m, 10)
        if not arms:
            return
        L = (b0 - a0).length
        k = max(2, int(L / 0.45) + 1)
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
            n = Vector((c.x - mid.x, 0, c.z - mid.z)).normalized()
            rails(a_, b_, n, arms=(k % arms_every == 0))

    for part in m.parts:
        kind = part[0]
        if kind == 'rail':
            tr, side = part[1], part[2]
            rails(tr.a, tr.b, tr.n)
            if side == 'T1':
                endstop(tr.a, +1)               # a cap behind the marble where it lands
            elif m.kind not in ('loop', 'loopdom'):
                endstop(tr.a, +1)
        elif kind == 'wall':
            endstop(part[1], -1)                # the marble runs into it and drops
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
            dm = h.mat('domino', (0.95, 0.94, 0.9), 0.3, coat=0.6)
            board = -tr.n * lift
            for k, (s_k, t_k) in enumerate(doms):
                foot = tr.at(s_k) + board                 # middle of the domino's foot, on the board
                o = h.cube((0, 0, 0), (0.012, 0.042, 0.072), dm)
                final = math.radians(76 if k < len(doms) - 1 else 88)
                for u in (-0.5, 0.0, 0.04, 0.08, 0.11, 0.13):
                    a = final * min(1.0, max(0.0, u / 0.13)) ** 2       # it tips, then speeds up
                    # turn about the left edge of the foot (it falls to the left, the way the marble goes)
                    piv = foot + Vector((-0.006, 0, 0))
                    vx, vz = 0.006, 0.036
                    o.location = piv + Vector((vx * math.cos(a) - vz * math.sin(a), 0, vx * math.sin(a) + vz * math.cos(a)))
                    o.rotation_euler = (0, -a, 0)
                    o.keyframe_insert('location', frame=h.fr(t_k + u))
                    o.keyframe_insert('rotation_euler', frame=h.fr(t_k + u))
            mid = tr.at((doms[0][0] + doms[-1][0]) / 2) + board - Vector((0, 0, 0.004))
            plank = h.cube(tuple(mid), (doms[-1][0] - doms[0][0] + 0.1, 0.05, 0.006), arm_m)
            plank.rotation_euler = (0, -math.atan2(tr.d.z, tr.d.x) + math.pi, 0)
        elif kind == 'tilt':
            piv, Lp, thp, t_p, T_tilt = part[1:]
            centre = piv - Vector((0, 0, lift + 0.008))
            plank = h.cube(tuple(centre), (Lp, 2 * RAIL_HALF + 0.024, 0.012), rail_m)
            for u, f in ((-1.0, 0.0), (0.0, 0.0), (T_tilt * 0.8, 0.9), (T_tilt, 1.0), (T_tilt + 0.06, 0.95),
                         (T_tilt + 0.14, 1.0)):
                plank.rotation_euler = (0, thp - 2 * thp * f, 0)     # left end up, then down
                plank.keyframe_insert('rotation_euler', frame=h.fr(t_p + u))
            h.cyl(Vector((centre.x, W, centre.z - 0.012)), Vector((centre.x, centre.y - 0.05, centre.z - 0.012)), 0.008, arm_m, 12)
            for sx in (-1, 1):                          # the two stops it rests on
                h.cube((centre.x + sx * (Lp / 2 - 0.03), centre.y, centre.z - Lp / 2 * math.sin(thp) - 0.025),
                       (0.02, 0.05, 0.03), arm_m)
        elif kind == 'spiral':
            Oc, Rf, r_hole, z_rim, depth, below, c2 = part[1:]
            fm = h.mat('funnel', (0.9, 0.66, 0.3) if st != 'steel' else (0.88, 0.9, 0.95), 0.12, metal=1.0)
            prof = []
            for k in range(25):
                rr = r_hole + (Rf - r_hole) * k / 24
                zz = z_rim - depth * ((Rf - rr) / (Rf - r_hole)) ** 1.5 - R
                prof.append((rr + 0.004, zz))
            prof.append((Rf + 0.05, z_rim - R + 0.02))   # the lip
            h.revolve(Oc, prof, fm)
            h.cyl(Vector((Oc.x, Oc.y, prof[0][1])), below - Vector((0, 0, 0.03)), r_hole + 0.006, fm, 20)
            h.cyl(below, c2, R + 0.01, h.glass, 24)          # the glass chute back to the rail
            for a_ in (0.7, 2.45):
                q = Vector((Oc.x + Rf * math.cos(a_), Oc.y + Rf * math.sin(a_), z_rim - R))
                h.cyl(Vector((q.x, W, q.z)), q, 0.006, arm_m, 8)
        elif kind == 'loop':
            O, rq, Cl, rl = part[1:]
            pts = [Vector((O.x + rq * math.cos(-math.pi / 2 * k / 30), Y + 0.04 * k / 30,
                           O.z + rq * math.sin(-math.pi / 2 * k / 30))) for k in range(31)]
            curve(pts, lambda mid: O)
            lp = [Vector((Cl.x - rl * math.sin(2 * math.pi * k / 48), Y + 0.04 - 0.08 * k / 48,
                          Cl.z - rl * math.cos(2 * math.pi * k / 48))) for k in range(49)]
            curve(lp, lambda mid: Cl, arms_every=8)
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
