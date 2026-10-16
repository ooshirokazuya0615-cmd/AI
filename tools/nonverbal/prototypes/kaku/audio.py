"""Audio for KAKU & RONDO #2. Every event time comes from timeline.py. The melody is a PLACEHOLDER
(it follows the cube's faces) and must be replaced by the owner's own melody before anything is published."""
import math
import sys
from pathlib import Path

import numpy as np

PROTO = Path('/home/user/AI/tools/nonverbal/prototypes')
sys.path.insert(0, '/home/user/AI/tools/nonverbal')
sys.path.insert(0, str(PROTO / 'otohame'))
sys.path.insert(0, str(PROTO / 'stickman'))
import engine as E   # noqa: E402
import sfx           # noqa: E402
import synth         # noqa: E402

import timeline as T  # noqa: E402

SR = E.SR
TAU = 2 * np.pi
B = T.BEAT
# one chord per bar (12 bars, loops)
CHORDS = [
    (50, [62, 66, 69, 76]),          # bar 0  D(add9)
    (55, [59, 62, 67, 71]),          # bar 1  G
    (52, [59, 62, 64, 67]),          # bar 2  Em7
    (57, [62, 64, 67, 69]),          # bar 3  A7sus4 (no C#: that is TI's note)
    (50, [62, 66, 69, 71]),          # bar 4  D6
    (55, [59, 62, 67, 71]),          # bar 5  G
    (52, [59, 62, 64, 67]),          # bar 6  Em7  (beat 3 = the hesitation)
    (55, [59, 62, 66, 67]),          # bar 7  Gmaj7 (the melody starts)
    (47, [59, 62, 66, 69]),          # bar 8  Bm7
    (52, [59, 62, 64, 67]),          # bar 9  Em7 -> A7 on beat 3
    (50, [62, 66, 69, 76]),          # bar 10 D (finish)
    (50, [62, 67, 69, 74]),          # bar 11 Dsus -> loops to D
]


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def env_ad(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-np.maximum(t - a, 0) / d)


# ---------------------------------------------------------------- voices
def marimba(midi, vel=1.0):
    """Kaku: soft low marimba bar + a tiny wooden knock + a faint body (3.7 t, gentle note)."""
    f = E.hz(midi)
    t = tt(1.6)
    x = np.sin(TAU * f * t) * np.exp(-t / (0.45 + 60 / f))
    x += 0.22 * vel * np.sin(TAU * f * 3.93 * t) * np.exp(-t / 0.05)
    x += 0.07 * np.sin(TAU * f * 9.2 * t) * np.exp(-t / 0.012)
    k = synth.noise(0.03, 1500, 7000, seed=int(midi)) * np.exp(-tt(0.03) / 0.004) * 0.45
    x[:len(k)] += k
    th = synth.thump(0.18, 95, 48) * 0.22
    x[:len(th)] += th
    return sfx.env_attack(x, 1.5) * vel


def vibe(midi, vel=1.0, sec=1.4):
    """Rondo: vibraphone-like bar with slow tremolo."""
    f = E.hz(midi)
    t = tt(sec)
    trem = 1 + 0.18 * np.sin(TAU * 5.5 * t)
    x = (np.sin(TAU * f * t) + 0.25 * np.sin(TAU * f * 4.0 * t) * np.exp(-t / 0.08)) * np.exp(-t / 0.9) * trem
    tick = synth.noise(0.01, 3000, 11000, seed=int(midi) + 7) * np.exp(-tt(0.01) / 0.0015) * 0.2
    x[:len(tick)] += tick
    return sfx.env_attack(x, 0.8) * vel


def fork_tone(midi, sec=2.2, vel=1.0, attack=0.04):
    """A tuning fork in the stands: nearly a pure sine, slow shimmer."""
    f = E.hz(midi)
    t = tt(sec)
    x = np.sin(TAU * f * t) * (1 + 0.04 * np.sin(TAU * 3.1 * t)) + 0.04 * np.sin(TAU * f * 6.27 * t) * np.exp(-t / 0.05)
    return x * env_ad(len(t), attack, sec * 0.35) * vel


def start_fork():
    f = E.hz(50)                                 # D3
    t = tt(4.5)
    x = np.sin(TAU * f * t) * np.exp(-t / 1.8)
    x += 0.35 * np.sin(TAU * f * 6.27 * t) * np.exp(-t / 0.25)
    x += 0.12 * np.sin(TAU * f * 2 * t) * np.exp(-t / 0.8)
    k = sfx.wood(420, 0.9, 5) * 0.6
    x[:len(k)] += k
    return sfx.env_attack(x, 1.0)


def bass_note(midi, sec, vel=1.0):
    """Upright bass pluck."""
    f = E.hz(midi)
    t = tt(sec + 0.25)
    x = np.sin(TAU * f * t) + 0.5 * np.sin(TAU * 2 * f * t) * np.exp(-t / 0.35) + 0.25 * np.sin(TAU * 3 * f * t) * np.exp(-t / 0.2)
    env = np.exp(-t / 0.55) * np.minimum(1, t / 0.004)
    env[int(sec * SR):] *= np.exp(-(t[int(sec * SR):] - sec) / 0.05)
    th = synth.noise(0.02, 200, 1500, seed=int(midi)) * np.exp(-tt(0.02) / 0.004) * 0.15
    x = np.tanh(1.6 * x * env) / np.tanh(1.6)
    x[:len(th)] += th
    return x * vel


def brush_tap(vel=1.0, seed=0):
    n = synth.noise(0.18, 1200, 9000, seed=seed)
    return n * env_ad(len(n), 0.002, 0.045) * vel


def brush_sweep(sec, seed=0):
    n = synth.noise(sec, 2000, 8000, seed=seed)
    t = np.linspace(0, 1, len(n))
    return n * (np.sin(np.pi * t) ** 1.5) * 0.35


def ride(vel=1.0, seed=0):
    return sfx.metal_ting(E.hz(88) * 1.01, 0.5, seed) * 0.5 * vel


def soft_kick(vel=1.0):
    return E.kick(0.5 * vel, 0.32, 52.0)


def click(vel=1.0):
    k = sfx.wood(1850, 0.6, 3)[:int(0.08 * SR)]
    return k * vel


def swish(seed=0):
    n = synth.noise(0.16, 2500, 10000, seed=seed)
    t = np.linspace(0, 1, len(n))
    return n * np.sin(np.pi * t) ** 2 * 0.5


def flap_burst(sec=0.3, seed=0):
    out = np.zeros(int(sec * SR) + 2000)
    rng = np.random.default_rng(seed)
    for k in range(int(sec / 0.022)):
        c = sfx.wood(2400 + rng.uniform(-200, 200), 0.4, seed + k)[:900] * rng.uniform(0.5, 1.0)
        i = int(k * 0.022 * SR)
        out[i:i + len(c)] += c
    return out


def unsettled(sec):
    """The stands turning: a soft cluster that does not resolve, held while they look."""
    t = tt(sec + 0.35)
    env = np.minimum(1.0, t / 0.25) * np.where(t < sec, 1.0, np.exp(-(t - sec) / 0.12)) * 0.6
    x = np.zeros_like(t)
    for m in (74, 75, 80):
        f = E.hz(m)
        x += np.sin(TAU * f * t) * (1 + 0.05 * np.sin(TAU * 3.3 * t))
    return x * env * 0.3


# ---------------------------------------------------------------- arrangement
def chord_at(beat):
    bar = int(beat // 4) % 12
    root, ch = CHORDS[bar]
    if bar == 9 and beat % 4 >= 2:
        root, ch = 57, [62, 64, 67, 69]     # A7sus4
    return root, ch


def render():
    pre = 2.0                                       # render a little before 0 and wrap it round
    n = int((T.DURATION + pre + 5.0) * SR)
    dry = E.Bus(n)
    send = E.Bus(n)

    def add(t, s, pan=0.0, g=1.0, wet=0.0):
        dry.add(t + pre, s, pan, g)
        if wet:
            send.add(t + pre, s, pan, g * wet)

    hes = 27                                        # the hesitation beat: only the referee's click
    tf = T.T_FINISH_K

    # the referee (metronome) on every beat; louder alone, and as a count-in at the end
    for b in range(T.NBEATS):
        v = 0.10
        if b == hes:
            v = 0.32
        elif b == 43:
            v = 0.25
        elif b >= 44:
            v = 0.18
        add(b * B, click(1.0), -0.15, v, 0.3)

    # the stands' hum: one sustained bed across the loop point (from 24.0 s round to 0.53 s)
    bed_len = (T.DURATION - 23.47) + T.T_START + 0.4
    t = tt(bed_len)
    env = np.minimum(1.0, t / 0.6) * np.where(t < bed_len - 0.4, 1.0, np.exp(-(t - (bed_len - 0.4)) / 0.15))
    hum = sum(np.sin(TAU * E.hz(m) * t + k) * (1 + 0.04 * np.sin(TAU * (2.7 + k) * t)) for k, m in enumerate((62, 69, 74))) * env * 0.25 / 3
    add(23.47, hum, 0.0, 1.1, 0.8)
    add(23.47 - T.DURATION, hum, 0.0, 1.1, 0.8)

    # start fork, with a riser from frame 0
    add(T.T_START, start_fork(), -0.35, 0.55, 0.6)
    add(0.0, synth.riser(T.T_START, seed=4) * 0.5, 0.0, 1.0)
    add(T.DURATION, synth.riser(T.T_START, seed=4) * 0.5, 0.0, 1.0)

    # Kaku's landings: the melody (placeholder) + the stands answering an octave up
    upper = {62: 66, 64: 66, 66: 69, 69: 71, 71: 74, 74: 78}
    for tl, note, c1, face in T.landings():
        pan = float(np.clip(c1[0] / 14.0, -0.6, 0.6))
        melody = tl >= T.tb(28) - 1e-6
        add(tl, marimba(note, 1.0), pan, 0.70 if melody else 0.55, 0.35)
        add(tl, fork_tone(note + 12, 1.8, 0.35 if melody else 0.22, attack=0.03), pan * 0.5, 1.0, 0.9)
        if melody:
            add(tl + B / 3, fork_tone(upper[note] + 12, 1.2, 0.15, attack=0.03), -pan * 0.5, 1.0, 0.9)
    # habit 1: the little rock-back onto the same face after the last note (lands on b42)
    add(T.tb(42), marimba(74, 1.0), 0.0, 0.55 * 0.5, 0.35)
    # the headband slides on the off-beat while Kaku is moving
    for tp in T.TIPS:
        add(tp['t'] - B / 2, swish(seed=int(tp['beat'])), 0.0, 0.10, 0.2)

    # Rondo: the brass line touching the ground, arpeggiating the chord
    ticks = T.rondo_ticks()
    for k, t0 in enumerate(ticks):
        beat = t0 / B
        root, ch = chord_at(beat)
        tones = sorted(set([m + 12 for m in ch] + [m + 24 for m in ch[:2]]))
        m = tones[k % len(tones)] if (k // len(tones)) % 2 == 0 else tones[-1 - k % len(tones)]
        p, _, _ = T.rondo(t0)
        pan = float(np.clip(p[0] / 14.0, -0.7, 0.7))
        v = 0.13
        if T.tb(26) + 0.1 <= t0 < T.tb(28):
            v = 0.03                                   # everything empties for the hesitation
        elif T.tb(28) <= t0 < T.tb(38.5):
            v = 0.07                                   # the mix ignores Rondo the way the stands do
        if t0 >= T.T_FIN_R_ACTUAL:
            v = 0.06
        add(t0, vibe(m, 1.0, 0.9), pan, v, 0.5)

    # rhythm section, building up: b2-9 bass+kick; b10-17 + brushes; b18-25 + ride and pad; melody section 28..39
    for b in range(2, 40):
        if b == hes:
            continue
        root, ch = chord_at(b)
        bar_beat = b % 4
        melody = b >= 28
        pcs = {m % 12 for m in ch}
        third = next(root + i for i in (4, 3, 5, 2) if (root + i) % 12 in pcs)
        if b == 26:
            add(b * B, bass_note(root - 12, B * 0.5, 1.0), 0.0, 0.42, 0.05)
            continue
        if not melody or bar_beat in (0, 2):
            walk = [root, third, root + 7, root + 5][bar_beat]
            if melody:
                walk = root if bar_beat == 0 else root + 7
            add(b * B, bass_note(walk - 12, B * (2 if melody else 1) * 0.92, 1.0), 0.0, 0.42, 0.05)
        brushes = b >= 10
        if bar_beat in (1, 3):
            if brushes:
                add(b * B, brush_tap(1.0, seed=b), 0.25, 0.20 if not melody else 0.15, 0.2)
        else:
            if brushes:
                add(b * B, brush_sweep(B * 0.95, seed=b + 50), -0.2, 0.10, 0.2)
            add(b * B, soft_kick(1.0 if bar_beat == 0 else 0.6), 0.0, 0.30, 0.0)
        if 18 <= b < 28:
            add(b * B, ride(0.8, seed=b), 0.35, 0.10, 0.3)
            if bar_beat in (1, 3):
                add(b * B + 2 * B / 3, ride(0.55, seed=b + 100), 0.35, 0.08, 0.3)
        if bar_beat == 0 and (b >= 16 or melody):
            pad = sum(fork_tone(m + 12, B * 4.2, 0.10, attack=0.3) for m in ch)
            add(b * B, pad, 0.0, 0.5 if not melody else 0.8, 0.7)

    # the stands turn to watch Rondo at corners 1 and 2: an unsettled chord held while they look, resolved when they turn back
    look = [(t, T.fork_look(t)[2]) for t in np.arange(0, T.tb(27), 0.01)]
    on = None
    for t, v in look:
        if v > 0.4 and on is None:
            on = t
        if v <= 0.4 and on is not None:
            add(on, unsettled(t - on), 0.0, 0.55, 0.8)
            add(on, swish(seed=int(on * 10)) * 0.6, 0.0, 0.25, 0.3)
            for mm in (74, 81):
                add(t, fork_tone(mm, 0.4, 0.25, attack=0.02), 0.0, 0.35, 0.8)
            on = None

    # Rondo crosses first: a little vibraphone run (no C#)
    for k, m in enumerate((81, 83, 86, 93)):
        add(T.T_FIN_R_ACTUAL + k * B / 6, vibe(m, 0.8, 1.0), -0.4, 0.10, 0.6)
    add(T.T_FIN_R_ACTUAL + 0.05, flap_burst(0.18, 3), 0.5, 0.05, 0.4)

    # Kaku finishes: the whole stand rings, held like the gold light; a TI-shaped hole later
    add(tf - 1.0, synth.riser(1.0 - B / 8, seed=9) * 0.05, 0.0, 1.0, 0.5)
    dur = 45.4 * B - tf
    t = tt(dur)
    tau = t
    env = np.minimum(1, tau / 0.06) * (0.55 + 0.45 * np.exp(-tau / 1.6))
    duck = np.ones_like(t)
    a, bb = 22.55 - tf, 23.40 - tf
    duck = np.where((t > a) & (t < bb), 10 ** (-10 / 20), 1.0)
    ramp = 0.08
    for edge, up in ((a, False), (bb, True)):
        m_ = (t > edge - ramp) & (t < edge + ramp)
        u = (t[m_] - (edge - ramp)) / (2 * ramp)
        duck[m_] = 10 ** ((-10 * (u if not up else 1 - u)) / 20)
    after = t >= (23.47 - tf)
    duck[after] = 10 ** (-4 / 20) * np.clip(1 - (t[after] - (23.47 - tf)) / (45.4 * B - 23.47), 0, 1)
    fin = sum(np.sin(TAU * E.hz(m) * t + k) * (1 + 0.04 * np.sin(TAU * (3.1 + 0.3 * k) * t)) for k, m in enumerate((62, 69, 74, 76, 78, 81, 86)))
    fin = fin * env * duck * 0.30 / 7 * 3.0
    add(tf, fin, 0.0, 1.5, 1.0)
    add(tf, bass_note(38, 2.6, 1.2), 0.0, 0.35, 0.1)
    add(tf, E.crash(0.5, 3.0, seed=6), 0.3, 0.07, 0.6)
    add(tf + 0.05, flap_burst(0.22, 5), 0.5, 0.05, 0.4)
    # the knot turns to TI: a soft slide, then TI's note (C#6) does NOT come
    add(T.T_LOOK_TI, swish(seed=77) * 0.8, -0.3, 0.12, 0.3)
    # the cube panel flips to the note on camera, with a soft chime; then both flip back to 0-0
    add(T.T_BOARD_NOTE, flap_burst(0.20, 7), 0.0, 0.14, 0.4)
    for mm in (74, 81):
        add(T.T_BOARD_NOTE + 0.05, fork_tone(mm, 1.2, 0.3, attack=0.02), 0.0, 0.5, 0.8)
    add(T.T_BOARD_BACK, flap_burst(0.35, 9), 0.0, 0.16, 0.4)
    # count-in into the loop
    add(44 * B, soft_kick(1.0), 0.0, 0.30, 0.0)
    for b in (45, 47):
        add(b * B, brush_tap(1.0, seed=b), 0.25, 0.16, 0.2)
    for b in (46, 47):
        add(b * B, bass_note(38, B * 0.9, 1.0), 0.0, 0.40, 0.05)

    mix = dry.buf.copy()
    wet = synth.reverb(send.buf, seconds=2.5, wet=1.0)
    mix += (wet - send.buf) * 0.5
    # wrap: what rang before 0 and after the end goes round the loop
    i0 = int(pre * SR)
    L = int(round(T.DURATION * SR))
    out = mix[i0:i0 + L].copy()
    tail = mix[i0 + L:]
    out[:min(len(tail), L)] += tail[:L]
    head = mix[:i0]
    out[L - len(head):] += head
    out *= 0.40
    out, gr = E.limiter(out, -1.0)
    return out


if __name__ == '__main__':
    x = render()
    E.write_wav16(Path(__file__).with_name('audio_test.wav'), x)
    print(x.shape, np.abs(x).max())
