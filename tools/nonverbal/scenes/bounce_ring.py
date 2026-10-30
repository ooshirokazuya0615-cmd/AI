"""
リングの中でボールが跳ねる。跳ねるたびに少し大きくなり、音がひとつ鳴る。
跳ねる間隔はだんだん短くなり、最後はリングいっぱいになって弾ける。

Shorts定番の「見ていて気持ちいい」系。言葉がないので世界中で見られる。
"""
import colorsys
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import synth

HERE = Path(__file__).resolve().parent

# 座標は「画面の横幅 = 1」、原点は画面中央、上が +y
RING = 0.40        # リングの内側の半径
R_START = 0.024    # ボールの最初の半径
R_END = RING - 0.012
GRAVITY = 1.25
PHYS_DT = 1 / 1200
INTRO = 0.6        # 物理が動き出すまで（リングが描かれる時間）
OUTRO = 3.4        # 弾けてから終わるまで
MAX_HITS = 8       # 同時に描く衝突エフェクトの数

# 和音進行 vi–IV–I–V（Am–F–C–G）。切なさから明るさへ抜けていく王道進行
CHORDS = [(9, 0, 4), (5, 9, 0), (0, 4, 7), (7, 11, 2)]
CHORD_SECONDS = 4.0
FINAL_CHORD = (0, 4, 7, 2)  # C add9。最後だけ開放的な響き


@dataclass
class Hit:
    t: float     # 動画の頭からの秒
    x: float     # リング上の接触点
    y: float
    speed: float  # リングに向かう速さ（音の強さに使う）
    count: int   # 何回目の衝突か


def simulate(growth, seed, until):
    """固定ステップで物理を回し、衝突のリストと各時刻の状態を返す。"""
    rng = np.random.default_rng(seed)
    x, y = rng.uniform(-0.12, 0.12), 0.18
    ang = rng.uniform(0, 2 * math.pi)
    vx, vy = 0.6 * math.cos(ang), 0.6 * math.sin(ang)
    r = R_START
    energy = 0.5 * (vx * vx + vy * vy) + GRAVITY * y
    energy = max(energy, GRAVITY * RING * 1.1)  # 一番上まで届くだけのエネルギーを保つ

    states, hits = [], []
    t = 0.0
    while t < until:
        vy -= GRAVITY * PHYS_DT
        x += vx * PHYS_DT
        y += vy * PHYS_DT
        t += PHYS_DT
        d = math.hypot(x, y)
        lim = RING - r
        if d > lim:
            nx, ny = x / d, y / d
            x, y = nx * lim, ny * lim
            vn = vx * nx + vy * ny
            if vn > 0:
                vx -= 2 * vn * nx
                vy -= 2 * vn * ny
                # ほんの少し角度を揺らして、同じ軌道の繰り返しを防ぐ
                a = rng.normal(0, 0.06)
                c, s = math.cos(a), math.sin(a)
                vx, vy = vx * c - vy * s, vx * s + vy * c
                if vx * nx + vy * ny > 0:  # 揺らした結果、外向きになったら戻す
                    vx, vy = vx * c + vy * s, -vx * s + vy * c
                hits.append(Hit(t + INTRO, nx * RING, ny * RING, vn, len(hits)))
                r = min(r + growth, R_END)
                lim = RING - r
                x, y = nx * lim, ny * lim
            # 大きくなって中心が動いた分、エネルギーが保存されるよう速さを合わせる
            sp = math.hypot(vx, vy)
            want = math.sqrt(max(2 * (energy - GRAVITY * y), 0.04))
            vx, vy = vx / sp * want, vy / sp * want
        states.append((x, y, r))
        if r >= R_END:
            return t + INTRO, hits, np.array(states)
    return None, hits, np.array(states)


def tune(target_end, seed):
    """フィナーレが狙った秒に来るよう、1回あたりの成長量を探す。"""
    best = None
    for growth in np.geomspace(0.0012, 0.02, 90):
        end, hits, states = simulate(growth, seed, until=target_end * 1.25)
        if end is None:
            continue
        if best is None or abs(end - target_end) < abs(best[0] - target_end):
            best = (end, hits, states)
    if best is None:
        raise SystemExit('この長さでは収まりませんでした。--seconds を変えてみてください')
    return best


def palette(k):
    """衝突回数 → 色。シアンから始まり、青 → 紫 → マゼンタ → 橙 → 金 と色相を一周する。"""
    return np.array(colorsys.hsv_to_rgb((0.52 + k * 0.0095) % 1.0, 0.78, 0.92))


class Scene:
    def __init__(self, gpu, cfg):
        self.gpu, self.cfg = gpu, cfg
        self.end, self.hits, self.states = tune(cfg.seconds - OUTRO, cfg.seed)
        self.duration = self.end + OUTRO
        self.frame_count = int(self.duration * cfg.fps)
        self.hit_times = np.array([h.t for h in self.hits])

        src = (HERE / 'bounce_ring.glsl').read_text()
        self.trail_pass = gpu.program(src.replace('//#define PASS', '#define TRAIL_PASS'))
        self.main_pass = gpu.program(src)
        self.trail = [gpu.target(), gpu.target()]
        self.color = palette(0)
        self.prev_pos = None

    # ---------- 状態 ----------

    def state(self, t):
        i = int((t - INTRO) / PHYS_DT)
        i = min(max(i, 0), len(self.states) - 1)
        return self.states[i]

    def hits_before(self, t):
        return int(np.searchsorted(self.hit_times, t, side='right'))

    # ---------- 映像 ----------

    def render(self, f):
        cfg = self.cfg
        t = f / cfg.fps
        x, y, r = self.state(t)
        n = self.hits_before(t)
        target = palette(n)
        self.color += (target - self.color) * (1 - math.exp(-1 / cfg.fps / 0.12))
        if f == 0:
            self.color = target.copy()
            self.prev_pos = (x, y)

        hits = np.full((MAX_HITS, 4), -1.0)
        hit_cols = np.zeros((MAX_HITS, 3))
        flash = 0.0
        for j, h in enumerate(self.hits[max(0, n - MAX_HITS):n][::-1]):
            age = t - h.t
            hits[j] = (h.x, h.y, age, h.count)
            hit_cols[j] = palette(h.count + 1)
            flash += math.exp(-age / 0.18) * min(h.speed, 1.5) / 1.5
        outro = t - self.end

        aspect = cfg.height / cfg.width
        common = {
            'u_res': (float(cfg.width), float(cfg.height)),
            'u_time': t,
        }
        ball_alpha = 1.0 if outro < 0 else max(0.0, 1 - outro / 0.12)
        src, dst = self.trail[f % 2], self.trail[(f + 1) % 2]
        self.gpu.draw(self.trail_pass, dst, {
            **common,
            'u_a': self.prev_pos, 'u_b': (x, y), 'u_r': r,
            'u_col': tuple(self.color * 0.34 * ball_alpha * min(1.0, max(0.0, (t - INTRO) / 0.3))),
            'u_decay': math.exp(-1 / cfg.fps / (0.38 if outro < 0 else 0.12)),
        }, {'u_prev': src.tex})
        self.prev_pos = (x, y)

        self.gpu.draw(self.main_pass, None, {
            **common,
            'u_aspect': aspect,
            'u_ball': (x, y, r),
            'u_ballCol': tuple(self.color),
            'u_ring': RING,
            'u_flash': min(flash, 2.0),
            'u_hits': hits,
            'u_hitCol': hit_cols,
            'u_intro': min(t / INTRO, 1.0),
            'u_outro': outro,
            'u_progress': (r - R_START) / (R_END - R_START),
        }, {'u_trail': dst.tex})

    # ---------- 音 ----------

    def chord_at(self, t):
        return CHORDS[int(max(t - INTRO, 0) / CHORD_SECONDS) % len(CHORDS)]

    def audio(self):
        mix = synth.Mix(self.duration)
        rng = np.random.default_rng(self.cfg.seed)

        # 背景のパッド：コードが変わるたびに次の和音へ重ねて移る
        for k in range(int(math.ceil((self.end - INTRO) / CHORD_SECONDS))):
            at = INTRO + k * CHORD_SECONDS
            chord = CHORDS[k % len(CHORDS)]
            length = min(CHORD_SECONDS + 1.6, self.end - at + 0.4)
            if length <= 0.5:
                break
            freqs = [synth.hz(36 + chord[0] + (12 if chord[0] < 4 else 0))] + \
                    [synth.hz(60 + pc - (12 if pc > 7 else 0)) for pc in chord]
            mix.add(at - 0.8, synth.pad(freqs, length + 0.8), gain=0.16)

        # 衝突のたびにベル。和音の構成音を上下に行き来するアルペジオになる
        last_note, last_thump, step = -1.0, -1.0, 0
        for h in self.hits:
            gap = h.t - last_note
            if gap < 0.07:  # 終盤の連打は間引く（映像は全部描く）
                continue
            pcs = set(self.chord_at(h.t))
            progress = h.count / max(len(self.hits) - 1, 1)
            lo = 62 + (5 if progress > 0.75 else 0)
            tones = [m for m in range(lo, lo + 25) if m % 12 in pcs]
            cycle = 2 * len(tones) - 2
            p = step % cycle
            note = tones[p if p < len(tones) else cycle - p]
            step += 1
            vel = min(max(h.speed / 1.4, 0.35), 1.0) * min(max(gap / 0.3, 0.45), 1.0)
            mix.add(h.t, synth.bell(synth.hz(note), bright=0.6 + 0.4 * vel),
                    pan=h.x / RING * 0.7, gain=0.30 * vel)
            if h.speed > 0.9 and h.t - last_thump > 0.35:
                mix.add(h.t, synth.thump(), gain=0.20 * vel)
                last_thump = h.t
            last_note = h.t

        # フィナーレ：上がっていく音 → 和音をかき鳴らす → 低音の一撃
        rise = min(2.6, self.end - INTRO)
        mix.add(self.end - rise, synth.riser(rise, seed=self.cfg.seed), gain=0.10)
        strum = [m for m in range(48, 92) if m % 12 in FINAL_CHORD]
        for i, m in enumerate(strum):
            mix.add(self.end + i * 0.016, synth.bell(synth.hz(m), seconds=3.4),
                    pan=rng.uniform(-0.6, 0.6), gain=0.16)
        mix.add(self.end, synth.thump(1.6, 90, 30), gain=0.65)
        mix.add(self.end, synth.noise(1.4, 300, 12000, self.cfg.seed) *
                np.exp(-np.arange(int(1.4 * synth.SR)) / synth.SR / 0.18), gain=0.18)
        mix.add(self.end, synth.pad([synth.hz(36), synth.hz(48)] +
                                    [synth.hz(60 + pc) for pc in FINAL_CHORD], OUTRO, fade=1.2),
                gain=0.24)

        return synth.reverb(mix.buf, seconds=3.2, wet=0.30, seed=self.cfg.seed)
