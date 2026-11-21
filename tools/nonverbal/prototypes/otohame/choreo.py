"""
Score -> choreography. Nothing here is simulated forward: every jump is solved
backwards from the note it must land on.

World: x = song position (SPEED units per second), y up, z toward the side camera.
Each lead note is a pillar: x-extent = note length (piano roll), height = pitch degree.
"""
import colorsys
import math

import numpy as np

import score as S

R = 0.27            # blob radius
SPEED = 2.0         # world units per second of music
GAP = 0.07
DEPTH = 0.42        # pillar half-depth (z)
G_NOM = 17.0        # nominal gravity used to pick apex heights
PENTA = [64, 67, 69, 72, 74, 76, 79, 81]


def height(midi):
    return 0.42 + 0.27 * PENTA.index(midi)


def note_color(midi):
    k = PENTA.index(midi)
    h = [0.50, 0.54, 0.58, 0.64, 0.74, 0.84, 0.93, 0.11][k]   # low = cyan ... high = pink, top = gold
    return np.array(colorsys.hsv_to_rgb(h, 0.80, 1.0))


def X(t):
    return SPEED * (t - S.TM.offset)


def smoothstep(e0, e1, x):
    u = np.clip((x - e0) / (e1 - e0), 0, 1)
    return u * u * (3 - 2 * u)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Choreo:
    def __init__(self):
        notes = S.lead_notes()
        self.notes = notes
        self.final_t = S.TM.t(S.FINAL_BAR)
        # ---- pillars (block 0 = start platform)
        self.blocks = [dict(x0=-1.15, x1=-GAP, top=0.42, col=np.array([0.35, 0.40, 0.60]), t=-1.0, midi=None)]
        for n in notes:
            x0 = X(n.t) + GAP / 2
            x1 = X(n.t + n.dur) - GAP / 2
            if n.idx == len(notes) - 1:
                x1 = x0 + 2.6
            self.blocks.append(dict(x0=x0, x1=x1, top=height(n.midi), col=note_color(n.midi),
                                    t=n.t, midi=n.midi))
        # ---- landings and inverse-solved jumps
        self.lands = [dict(t=-10.0, x=-0.62, b=0)]
        for i, n in enumerate(notes):
            b = self.blocks[i + 1]
            inset = min(0.30, 0.5 * (b['x1'] - b['x0']))
            self.lands.append(dict(t=n.t, x=b['x0'] + inset, b=i + 1))
        self.jumps = []
        for i in range(1, len(self.lands)):
            a, c = self.lands[i - 1], self.lands[i]
            final = i == len(self.lands) - 1
            if i == 1:
                t_off = 0.13
            else:
                gap = c['t'] - a['t']
                stance = float(np.clip(0.30 * gap, 0.07, 0.16))
                if final:
                    stance = 0.085
                t_off = a['t'] + stance
            T = c['t'] - t_off
            y0 = self.blocks[a['b']]['top'] - self.dip(a['b'], t_off)
            y1 = self.blocks[c['b']]['top']
            clear = max(0.16, G_NOM * T * T / 8)
            if final:
                clear = 1.25
            apex = max(y0, y1) + clear
            h0, h1 = apex - y0, apex - y1
            g = ((math.sqrt(2 * h0) + math.sqrt(2 * h1)) / T) ** 2   # inverse solve: hit (x1,y1) at exactly T
            v0 = math.sqrt(2 * g * h0)
            vx = (c['x'] - a['x']) / T
            antic = min(0.11, 0.85 * (t_off - max(a['t'], 0.0))) if i > 1 else 0.11
            self.jumps.append(dict(t_off=t_off, t_land=c['t'], x0=a['x'], y0=y0, y1=y1,
                                   vx=vx, v0=v0, g=g, T=T, antic=antic, flip=final,
                                   impact=v0 - g * T, src=a['b'], dst=c['b']))
        self.land_t = np.array([l['t'] for l in self.lands[1:]])
        kick_t = [t for t, _ in S.drum_events()['kick']]
        self.kicks = np.array(kick_t)
        self.snares = np.array([t for t, _ in S.drum_events()['snare']])
        self.cuts = [0.0] + S.downbeats()
        self._smooth_path()

    # ------------------------------------------------------------ blocks
    def dip(self, b, t):
        tb = self.blocks[b]['t']
        if b == 0 or t < tb:
            return 0.0
        tau = t - tb
        amp = 0.075 if self.blocks[b]['midi'] != 81 or tb < self.final_t - 0.01 else 0.16
        return amp * math.exp(-tau / 0.11) * math.sin(2 * math.pi * tau / 0.30)

    def block_fx(self, t):
        rows = []
        for i, b in enumerate(self.blocks):
            if i == 0:
                rows.append((0.0, 0.3, 0.0, -1.0))
                continue
            tau = t - b['t']
            flash = math.exp(-tau / 0.20) if tau >= 0 else 0.0
            lit = (1.5 if b['midi'] == 81 and b['t'] >= self.final_t - 0.01 else 1.0) if tau >= 0 else 0.0
            if b['midi'] == 81 and b['t'] >= self.final_t - 0.01:
                flash *= 0.45
            pre = float(smoothstep(b['t'] - 0.30, b['t'], t)) if tau < 0 else 0.0
            rows.append((flash, lit, pre, tau if 0 <= tau < 1.2 else -1.0))
        return rows

    # ------------------------------------------------------------ body
    def phase(self, t):
        """('stand', land_index) or ('air', jump_index)."""
        for j, jp in enumerate(self.jumps):
            if t < jp['t_off']:
                return 'stand', j
            if t < jp['t_land']:
                return 'air', j
        return 'stand', len(self.jumps)

    def foot(self, t):
        kind, j = self.phase(t)
        if kind == 'air':
            jp = self.jumps[j]
            tau = t - jp['t_off']
            return np.array([jp['x0'] + jp['vx'] * tau, jp['y0'] + jp['v0'] * tau - 0.5 * jp['g'] * tau ** 2, 0.0]), \
                np.array([jp['vx'], jp['v0'] - jp['g'] * tau, 0.0]), kind, j
        land = self.lands[j]
        b = land['b']
        y = self.blocks[b]['top'] - self.dip(b, t)
        return np.array([land['x'], y, 0.0]), np.zeros(3), kind, j

    def squash(self, t):
        kind, j = self.phase(t)
        s = 0.0
        # landing squash with overshoot into stretch (damped)
        li = int(np.searchsorted(self.land_t, t, side='right')) - 1
        if li >= 0:
            tau = t - self.land_t[li]
            jp = self.jumps[li]
            final = jp['flip']
            amp = float(np.clip(0.16 + 0.042 * abs(jp['impact']), 0.24, 0.46)) if not final else 0.62
            per = 0.30 if not final else 0.42
            s += amp * (1 - math.exp(-tau / 0.012)) * math.exp(-tau / (0.085 if not final else 0.16)) \
                * math.cos(2 * math.pi * tau / per)
        # anticipation crouch before the next take-off
        if j < len(self.jumps):
            jp = self.jumps[j]
            a = jp['antic']
            amp = float(np.clip(0.06 + 0.028 * jp['v0'], 0.14, 0.38))
            if kind == 'stand':
                s += amp * float(smoothstep(jp['t_off'] - a, jp['t_off'], t)) ** 1.5
            else:
                tau = t - jp['t_off']
                s += amp * math.exp(-tau / 0.016)
        if kind == 'air':
            jp = self.jumps[j]
            tau = t - jp['t_off']
            vy = jp['v0'] - jp['g'] * tau
            k = 0.3 if jp['flip'] else 1.0
            s -= k * min(0.30, 0.020 * abs(vy) + 0.004 * abs(jp['vx'])) * min(1.0, tau / 0.03)
            if jp['flip']:
                s += 0.12 * math.sin(math.pi * tau / jp['T'])   # tuck during the flip
        # idle breathing / final pose
        if t < 0.0 + self.jumps[0]['t_off'] - 0.11:
            s += 0.03 * math.sin(2 * math.pi * t * 3)
        if t > self.final_t + 0.45:
            s += -0.10 * float(smoothstep(self.final_t + 0.45, self.final_t + 0.75, t)) \
                + 0.025 * math.sin(2 * math.pi * (t - self.final_t) * 2.0)
        return float(np.clip(s, -0.36, 0.55))

    def body(self, t, cam_pos):
        f, v, kind, j = self.foot(t)
        s = self.squash(t)
        sy = 1 - s
        sx = 1 / math.sqrt(sy)
        rad = np.array([R * sx, R * sy, R * sx])
        # facing: travel (+x) cheated 55% toward camera
        to_cam = cam_pos - f
        to_cam[1] = 0
        to_cam /= np.linalg.norm(to_cam) + 1e-9
        d = 0.45 * np.array([1.0, 0, 0]) + 0.55 * to_cam
        if t > self.final_t:
            d = to_cam
        yaw = math.atan2(d[0], d[2])
        lean = 0.0
        if kind == 'air':
            jp = self.jumps[j]
            tau = t - jp['t_off']
            lean = -0.22 * math.tanh(jp['vx'] / 4)
            if jp['flip']:
                u = tau / jp['T']
                lean = -2 * math.pi * float(smoothstep(0.08, 0.92, u))
        else:
            li = int(np.searchsorted(self.land_t, t, side='right')) - 1
            if li >= 0:
                tau = t - self.land_t[li]
                lean = 0.20 * math.exp(-tau / 0.09) * math.sin(2 * math.pi * tau / 0.30) * -1
        rot = rot_z(lean) @ rot_y(yaw)
        center = f + np.array([0, rad[1], 0])
        if abs(lean) > 0.5:  # flipping: spin around the body centre
            center = f + np.array([0, R, 0])
        # eyes
        nxt = self.lands[min(j + (1 if kind == 'stand' else 1), len(self.lands) - 1)]
        tb = self.blocks[nxt['b']]
        target = np.array([nxt['x'], tb['top'] + R, 0.0]) if t < self.final_t else cam_pos
        dl = rot.T @ (target - center)
        dl /= np.linalg.norm(dl) + 1e-9
        look = np.clip(dl[:2] * np.array([1.0, 1.0]), -0.8, 0.8)
        # face: squint on hard landings, blink twice, happy at the end
        squint = 0.0
        li = int(np.searchsorted(self.land_t, t, side='right')) - 1
        if li >= 0 and t - self.land_t[li] < 0.16:
            squint = 0.55 * math.exp(-(t - self.land_t[li]) / 0.07)
        blink = 0.0
        for tb_ in (1.92, 5.62):
            blink = max(blink, max(0.0, 1 - abs(t - tb_) / 0.06))
        mouth = 0.0
        if kind == 'air' and self.jumps[j]['flip']:
            mouth = 0.6
        happy = 0.0
        if t >= self.final_t:
            happy = float(smoothstep(self.final_t + 0.05, self.final_t + 0.25, t))
            mouth = 0.4 + 0.6 * happy
            squint = max(squint, 0.0)
        bounce = np.zeros(3)
        li = int(np.searchsorted(self.land_t, t, side='right')) - 1
        if li >= 0:
            bl = self.blocks[self.lands[li + 1]['b']]
            bounce = bl['col'] * min(1.0, 0.25 + 1.3 * math.exp(-(t - bl['t']) / 0.2))
            if kind == 'air':
                bounce *= max(0.0, 1 - (f[1] - bl['top']) / 1.2)
        return dict(center=center, rot=rot, rad=rad, look=look, squint=squint, blink=blink, bounce=bounce,
                    mouth=mouth, happy=happy, foot=f, kind=kind, s=s)

    # ------------------------------------------------------------ camera
    def _smooth_path(self):
        self.ts = np.arange(-1.0, S.DURATION + 1.0, 1 / 240)
        fp = np.array([self.foot(min(max(t, 0), S.DURATION))[0] for t in self.ts])
        sig = 0.22 * 240
        half = int(4 * sig)
        k = np.exp(-0.5 * (np.arange(-half, half + 1) / sig) ** 2)
        k /= k.sum()
        pad = len(k) // 2
        self.fs = np.stack([np.convolve(np.pad(fp[:, i], pad, mode='edge'), k, mode='valid') for i in range(3)], 1)

    def F(self, t):
        return np.array([np.interp(t, self.ts, self.fs[:, i]) for i in range(3)])

    def env(self, times, t, tau):
        times = times[times <= t]
        return math.exp(-(t - times[-1]) / tau) if len(times) else 0.0

    def camera(self, t):
        shot = int(np.searchsorted(self.cuts, t, side='right')) - 1
        t0 = self.cuts[shot]
        u = t - t0
        F = self.F(t)
        roll = 0.0
        if shot == 0:     # close-up on the face, crouching
            tgt = np.array([-0.62, 0.42 + 0.30, 0.0])
            pos = tgt + np.array([0.75 - 0.2 * u, 0.12, 1.55 - 0.3 * u])
            fov = 34
        elif shot == 1:   # 3/4 rear "runner" view: the upcoming notes recede into depth
            tgt = np.array([F[0] + 0.30, F[1] + 0.25, 0])
            pos = np.array([F[0] - 1.9 - 0.15 * u, F[1] + 1.45, 2.6])
            fov = 52
        elif shot == 2:   # low 3/4 from ahead: played (lit) notes trail behind the character
            tgt = np.array([F[0] - 0.15, F[1] + 0.40, 0])
            pos = np.array([F[0] + 2.4, F[1] + 0.25, 2.4])
            fov = 50
        elif shot == 3:   # high crane, shows the climb
            tgt = np.array([F[0] + 0.45, 0.65 * F[1] + 0.35, 0])
            pos = np.array([F[0] - 0.5 + 0.25 * u, F[1] + 3.0 - 0.3 * u, 4.0])
            fov = 50
        elif shot == 4:   # telephoto side, dutch tilt, fast run
            tgt = np.array([F[0] + 0.22, F[1] + 0.35, 0])
            pos = np.array([F[0] + 0.9, F[1] + 0.95, 7.2])
            fov = 25
            roll = 0.10
        else:             # hero: low front, push in
            c = np.array([self.lands[-1]['x'], height(81) + R, 0.0])
            tgt = c + np.array([0, 0.08, 0])
            # hold a medium hero frame, then pull back to reveal the whole lit melody skyline
            k = float(smoothstep(0.35, 1.45, u))
            k = k * k * (3 - 2 * k)
            near = c + np.array([0.95, 0.05, 2.3])
            far = c + np.array([2.6, 1.15, 1.0])      # ahead of the last pillar, looking back down the melody
            pos = near * (1 - k) + far * k
            tgt = tgt * (1 - k ** 2) + (c + np.array([-2.6, -0.75, -0.6])) * k ** 2
            fov = 40 + 8 * k
        if 1 <= shot <= 4:                       # ~15% closer than v1: bigger character in 9:16
            pos = tgt + (pos - tgt) * 0.85
        kick = self.env(self.kicks, t, 0.10)
        fov *= 1 - 0.035 * kick
        if shot + 1 < len(self.cuts):            # accelerating push-in that lands on the downbeat cut
            tc = self.cuts[shot + 1]
            fov *= 1 - 0.08 * float(smoothstep(tc - 0.5, tc, t)) ** 2
        if t >= self.final_t:
            e = math.exp(-(t - self.final_t) / 0.18)
            pos = pos + 0.035 * e * np.array([math.sin(97 * t), math.sin(131 * t + 1), 0])
        return pos, tgt, fov, roll, shot

    @staticmethod
    def cam_basis(pos, tgt, roll):
        f = tgt - pos
        f /= np.linalg.norm(f)
        r = np.cross(f, [0, 1, 0])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        c, s = math.cos(roll), math.sin(roll)
        r, u = r * c + u * s, -r * s + u * c
        return np.stack([r, u, f], 1)  # columns


class Confetti:
    def __init__(self, origin, t0, n=48, seed=4):
        rng = np.random.default_rng(seed)
        self.t0 = t0
        a = rng.uniform(0, 2 * np.pi, n)
        el = rng.uniform(0.35, 1.3, n)
        sp = rng.uniform(2.2, 4.8, n)
        self.v = np.stack([np.cos(a) * np.cos(el), np.sin(el), np.sin(a) * np.cos(el)], 1) * sp[:, None]
        self.spin = rng.uniform(4, 14, n)
        d = self.v / np.linalg.norm(self.v, axis=1, keepdims=True)
        self.o = origin + d * R * rng.uniform(1.0, 1.6, n)[:, None]   # spawn on a shell, not a point
        self.size = rng.uniform(0.035, 0.06, n)
        hues = rng.choice([0.56, 0.47, 0.33, 0.12, 0.95, 0.80], n)
        self.col = np.array([colorsys.hsv_to_rgb(h, 0.6, 1.0) for h in hues])

    def at(self, t):
        u = t - self.t0
        if u < 0:
            return None
        drag = (1 - np.exp(-u * 2.2)) / 2.2
        p = self.o + self.v * drag + np.array([0, -1.6, 0]) * u * u * 0.5
        return p, self.spin * u, self.size, self.col, max(0.0, 1 - u / 1.5)


def project(basis, pos, tanh_, p, aspect=9 / 16):
    d = p - pos
    x, y, z = d @ basis[:, 0], d @ basis[:, 1], d @ basis[:, 2]
    if z <= 0:
        return None
    return (x / z / tanh_) / aspect, (y / z / tanh_)   # NDC in [-1, 1]


def framing_report(ch, fps=60):
    bad = []
    for f in range(int(10 * fps)):
        t = f / fps
        pos, tgt, fov, roll, shot = ch.camera(t)
        B = ch.cam_basis(pos, tgt, roll)
        b = ch.body(t, pos)
        q = project(B, pos, math.tan(math.radians(fov) / 2), b['center'])
        if q is None or abs(q[0]) > 0.66 or abs(q[1]) > 0.8:
            bad.append((round(t, 3), shot, None if q is None else (round(q[0], 2), round(q[1], 2))))
    return bad
