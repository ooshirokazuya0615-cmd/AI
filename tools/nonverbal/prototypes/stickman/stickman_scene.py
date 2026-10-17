"""
Stickman ragdoll scene, written against the tools/nonverbal Scene interface:
    Scene(gpu, cfg) -> .frame_count, .render(f), .audio()
Picture and sound are both derived from the same recorded physics timeline.
"""
import math
from pathlib import Path

import numpy as np

import sim
import sfx

HERE = Path(__file__).resolve().parent

# The tuned take (found with search.py; see evaluate() for the story checks)
TAKE = dict(seed=3, ball_v=560, pad_k=3000, pad_e=0.85, body_e=0.35, duration=9.0)
SEG_NAMES = ['torso', 'uarm_n', 'larm_n', 'uarm_f', 'larm_f', 'thigh_n', 'shin_n', 'thigh_f', 'shin_f']
SEG_IDX = [sim.BODY_ORDER.index(n) for n in SEG_NAMES]
HEAD_IDX = sim.BODY_ORDER.index('head')
GHOST_DT = 1 / 45
END_HOLD = 0.0


def seg_endpoints(row):
    """(9,4) capsule endpoints + head (x, y, angle) from one recorded body row."""
    segs = np.zeros((9, 4))
    for k, (name, bi) in enumerate(zip(SEG_NAMES, SEG_IDX)):
        x, y, a = row[bi]
        L = sim.SEGS[name][0]
        d = np.array([math.cos(a), math.sin(a)]) * L / 2
        segs[k] = (x - d[0], y - d[1], x + d[0], y + d[1])
    return segs, row[HEAD_IDX]


class Timeline:
    """Everything derived from the recording that both picture and sound need."""

    def __init__(self, rec):
        self.rec = rec
        self.T = rec.steps * sim.DT
        ev = rec.events
        self.body_events = [e for e in ev if e['other'] == 'body']
        # impacts worth a comic burst / camera kick
        self.big = []
        last = -1
        for e in sorted(self.body_events, key=lambda e: e['t']):
            s = self.strength(e)
            if s > 0.45 and e['t'] - last > 0.09:
                self.big.append((e['t'], e['x'], e['y'], s))
                last = e['t']
        # settle time: torso slow for good after landing on the pad
        tor = rec.bodies[:, 0, :2]
        sp = np.linalg.norm(np.diff(tor, axis=0), axis=1) / sim.DT
        sp = np.convolve(sp, np.ones(60) / 60, mode='same')
        pad_t = [e['t'] for e in self.body_events if e['a'] == 'pad']
        self.t_pad = pad_t[0] if pad_t else self.T
        i0 = int(self.t_pad / sim.DT)
        moving = np.where(sp[i0:] > 110)[0]
        self.t_settle = (i0 + moving[-1]) * sim.DT + 0.15 if len(moving) else self.t_pad
        self.t_settle = min(self.t_settle, self.T - 1.2)
        self.head_hits = [e['t'] for e in self.body_events if e['b'] == 'head' and self.strength(e) > 0.5]
        self._camera()

    @staticmethod
    def strength(e):
        # impulse normalised so a hard stair landing is ~1
        return float(np.clip((e['J'] / 3500.0) ** 0.7, 0, 1.5))

    def idx(self, t):
        return min(max(int(round(t / sim.DT)), 0), self.rec.steps - 1)

    def _camera(self):
        """Critically damped follow cam at physics rate (independent of render fps)."""
        rec = self.rec
        n = rec.steps
        cam = np.zeros((n, 3))
        tor = rec.bodies[:, 0, :2]
        vel = np.gradient(tor, sim.DT, axis=0)
        pos = np.array([-120.0, tor[0, 1] - 190.0])
        v = np.zeros(2)
        wx, wy = 3.2, 4.0
        for i in range(n):
            t = i * sim.DT
            zoom = 1.62 + 0.10 * math.exp(-((t - rec.t_hit) / 0.35) ** 2) \
                + 0.70 * smooth((t - self.t_settle) / 1.5)
            hw, hh = 540.0 / zoom, 960.0 / zoom
            tgt = np.array([tor[i, 0] * 0.65, tor[i, 1] - 190.0 + 0.10 * vel[i, 1]])
            if t > self.t_settle - 0.3:   # end: frame the face
                k = smooth((t - self.t_settle + 0.3) / 1.2)
                tgt = tgt * (1 - k) + k * np.array([rec.bodies[i, HEAD_IDX, 0], rec.bodies[i, HEAD_IDX, 1] - 60])
            tgt[0] = np.clip(tgt[0], -(600 - hw), 600 - hw)
            tgt[1] = np.clip(tgt[1], -1760 + hh, 330 - hh)
            for axis, w in ((0, wx), (1, wy)):
                a = w * w * (tgt[axis] - pos[axis]) - 2 * w * v[axis]
                v[axis] += a * sim.DT
                pos[axis] += v[axis] * sim.DT
            cam[i] = (pos[0], pos[1], zoom)
        self.cam = cam

    def shake(self, t):
        off = np.zeros(2)
        for (te, x, y, s) in self.big:
            age = t - te
            if 0 <= age < 0.35:
                a = 5.0 * min(s, 1.2) * math.exp(-age / 0.07)
                off += a * np.array([math.sin(age * 71 + x), math.cos(age * 57 + y)])
        return off

    def face(self, t):
        rec = self.rec
        i = self.idx(t)
        head = rec.bodies[i, HEAD_IDX, :2]
        look = rec.ball[i, :2] - head
        look = look / (np.linalg.norm(look) + 1e-6)
        blink = 0.0
        for tb in (0.32,):
            blink = max(blink, max(0.0, 1 - abs(t - tb) / 0.06))
        if t < rec.t_notice:
            return 0.0, look, blink
        if t < rec.t_hit + 0.55:
            return 1.0, look, 0.0
        if t >= self.t_settle:
            return 3.0, look, 0.0
        if any(0 <= t - th < 0.4 for th in self.head_hits):
            return 3.0, look, 0.0
        return 2.0, look, 0.0


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Scene:
    def __init__(self, gpu, cfg, rec=None):
        self.gpu, self.cfg = gpu, cfg
        self.rec = rec if rec is not None else sim.simulate(sim.Params(**TAKE))
        self.tl = Timeline(self.rec)
        self.duration = self.tl.T
        self.frame_count = int(round(self.duration * cfg.fps))
        if gpu is not None:
            self.prog = gpu.program((HERE / 'stickman.glsl').read_text())
        ev = self.tl.body_events
        self.peg_hits = {i: [e for e in self.rec.events if e['a'] == f'peg{i}'] for i in range(len(sim.PEGS))}
        self.step_hits = {i: [e for e in self.rec.events if e['a'] == f'step{i}'] for i in range(sim.STEPS)}
        self.plate_hits = [e for e in self.rec.events if e['a'] == 'plate']

    def _decay(self, hits, t, tau, scale=1.0):
        g = 0.0
        for e in hits:
            age = t - e['t']
            if 0 <= age < 6 * tau:
                g = max(g, min(self.tl.strength(e) * scale, 1.0) * math.exp(-age / tau))
        return g

    def uniforms(self, t):
        tl, rec = self.tl, self.rec
        i = tl.idx(t)
        segs, head = seg_endpoints(rec.bodies[i])
        cam = tl.cam[i].copy()
        cam[:2] += tl.shake(t)
        # ghosts
        gsegs, gheads = [], []
        lo = np.minimum(segs[:, :2], segs[:, 2:]).min(axis=0)
        hi = np.maximum(segs[:, :2], segs[:, 2:]).max(axis=0)
        lo = np.minimum(lo, head[:2] - 30)
        hi = np.maximum(hi, head[:2] + 30)
        for g in range(3):
            j = tl.idx(t - (g + 1) * GHOST_DT)
            s2, h2 = seg_endpoints(rec.bodies[j])
            moved = np.linalg.norm(rec.bodies[j, 0, :2] - rec.bodies[i, 0, :2])
            alpha = float(np.clip((moved - 10) / 60, 0, 1)) * (0.34 - 0.09 * g)
            gsegs.append(s2)
            gheads.append((h2[0], h2[1], 0.0, alpha))
            if alpha > 0.01:
                lo = np.minimum(lo, np.minimum(s2[:, :2], s2[:, 2:]).min(axis=0))
                hi = np.maximum(hi, np.maximum(s2[:, :2], s2[:, 2:]).max(axis=0))
                lo = np.minimum(lo, h2[:2] - 30)
                hi = np.maximum(hi, h2[:2] + 30)
        lo -= np.array([20, 40])   # outline + drop shadow margins
        hi += np.array([30, 20])
        expr, look, blink = tl.face(t)
        dizzy = smooth((t - tl.t_settle - 0.1) / 0.5)
        hits = np.full((8, 4), -1.0)
        recent = [h for h in tl.big if 0 <= t - h[0] < 0.3][-8:]
        for k, (te, x, y, s) in enumerate(recent):
            hits[k] = (x, y, t - te, min(s, 1.2))
        pegs = np.zeros((12, 3))
        for k, (x, y) in enumerate(sim.PEGS):
            pegs[k] = (x, y, self._decay(self.peg_hits[k], t, 0.12, 1.6))
        steps = [self._decay(self.step_hits[k], t, 0.10, 1.2) for k in range(6)]
        vib, phase = 0.0, 0.0
        for e in self.plate_hits:
            age = t - e['t']
            if 0 <= age < 0.8:
                a = 5.0 * min(self.tl.strength(e) * 1.4, 1.2) * math.exp(-age / 0.12)
                if a > abs(vib):
                    vib, phase = a, age * 2 * math.pi * 21
        fade = smooth(t / 0.25) * (1 - smooth((t - (self.duration - 0.35)) / 0.35))
        return {
            'u_res': (float(self.cfg.width), float(self.cfg.height)),
            'u_time': t,
            'u_cam': tuple(cam),
            'u_seg': segs, 'u_head': (head[0], head[1], head[2], 24.0),
            'u_gseg': np.concatenate(gsegs), 'u_ghead': np.array(gheads),
            'u_bbox': (lo[0], lo[1], hi[0], hi[1]),
            'u_face': (expr, look[0], look[1], blink),
            'u_dizzy': dizzy,
            'u_ball': (rec.ball[i, 0], rec.ball[i, 1], 31.0, rec.ball[i, 2]),
            'u_padTop': float(rec.pad[i, 0]),
            'u_stair': (sim.LEDGE_X1, sim.TREAD, sim.RISE, float(sim.STEPS)),
            'u_stepHit': np.array(steps),
            'u_pegs': pegs,
            'u_plate': (*sim.PLATE[0], *sim.PLATE[1]),
            'u_plateVib': (vib, phase),
            'u_hits': hits,
            'u_fade': fade,
        }

    def render(self, f):
        self.gpu.draw(self.prog, None, self.uniforms(f / self.cfg.fps))

    def audio(self):
        buf, self.sound_tally, self.sound_events = sfx.render_audio(self.tl, self.duration)
        return buf
