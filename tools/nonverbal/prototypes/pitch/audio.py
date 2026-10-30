"""Audio for the pitch prototype. All synthesized; every event time comes from timeline.py."""
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
CHORDS = [(62, 66, 69), (59, 62, 66), (55, 59, 62), (57, 61, 64)]   # D Bm G A
ROOTS = [38, 35, 31, 33]
FINAL = (38, 50, 57, 62, 66, 69, 76)                                 # D add9


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def gong(sec=4.0):
    t = tt(sec)
    f0 = 98.0
    parts = [(1.0, 1.0, 3.0), (1.48, 0.7, 2.4), (2.09, 0.55, 2.0), (2.76, 0.45, 1.5), (3.42, 0.35, 1.1), (4.17, 0.25, 0.8)]
    x = np.zeros_like(t)
    for k, (r, a, d) in enumerate(parts):
        beat = 1 + 0.15 * np.sin(TAU * (0.7 + k * 0.4) * t)
        x += a * np.sin(TAU * f0 * r * t + 0.3 * np.sin(TAU * 2.1 * t)) * np.exp(-t / d) * beat
    hit = synth.noise(0.12, 200, 6000, seed=5) * np.exp(-tt(0.12) / 0.02)
    x[:len(hit)] += hit * 0.8
    sw = np.minimum(1.0, t / 0.05)                       # gongs swell a little after the hit
    return x * (0.6 + 0.4 * sw) * 0.5


def plate(midi):
    f = E.hz(midi)
    t = tt(1.8)
    x = np.sin(TAU * f * t) * np.exp(-t / 0.9)
    x += 0.45 * np.sin(TAU * f * 2.41 * t) * np.exp(-t / 0.35)
    x += 0.25 * np.sin(TAU * f * 3.87 * t) * np.exp(-t / 0.15)
    x += 0.12 * np.sin(TAU * f * 5.93 * t) * np.exp(-t / 0.06)
    tick = synth.noise(0.01, 3000, 10000, seed=midi) * np.exp(-tt(0.01) / 0.0015)
    x[:len(tick)] += tick * 0.4
    return E.fade_edges(x, 0.0004, 0.02)


def xylo(midi):
    return sfx.mallet(E.hz(midi), 1.2, 1.0)


def leather_pop():
    n = synth.noise(0.09, 300, 3500, seed=61) * np.exp(-tt(0.09) / 0.012)
    th = synth.thump(0.12, 160, 90) * 0.5
    out = np.zeros(int(0.12 * SR))
    out[:len(n)] += n
    out[:len(th)] += th
    return out


def render():
    n = int((T.DURATION + 0.5) * SR)
    dry = E.Bus(n)
    send = E.Bus(n)
    rng = np.random.default_rng(11)

    # --- the throw (frame 0 is already mid-windup) ---
    dry.add(0.0, E.whoosh(0.22, True, seed=2) * 0.5, 0.1, 0.22)
    dry.add(0.17, synth.thump(0.16, 120, 70) * 0.7, 0.1, 0.30)                    # stride lands
    zip_ = synth.noise(0.22, 1500, 9000, seed=9) * np.linspace(0.2, 1.0, int(0.22 * SR)) ** 2
    dry.add(T.T_REL - 0.02, zip_, 0.0, 0.22)
    dry.add(0.0, synth.riser(T.T_GONG, seed=4) * 0.20, 0.0, 1.0)

    # --- gong: the music starts ---
    g = gong()
    dry.add(T.T_GONG, g, 0.0, 0.55)
    send.add(T.T_GONG, g, 0.0, 0.25)
    dry.add(T.T_GONG, E.kick(1.2, 0.55, 46.0), 0.0, 0.8)
    dry.add(T.T_GONG, E.crash(0.8, 2.4), 0.2, 0.22)

    # --- groove (bars 0-2), break on bar 3 ---
    for bar in range(3):
        for beat in range(4):
            tb = T.tm(bar, beat * 4)
            if beat in (0, 2) and not (bar == 0 and beat == 0):
                dry.add(tb, E.kick(0.75, 0.38, 50.0), 0.0, 0.5)
            if beat in (1, 3):
                dry.add(tb, E.clap(0.55), 0.0, 0.20)
        for e in range(8):
            dry.add(T.tm(bar, e * 2), E.hat(0.32 if e % 2 else 0.45, False, seed=e + 10), 0.25, 0.09)
        for st in (0, 6, 10, 14):
            dry.add(T.tm(bar, st), E.bass(ROOTS[bar], 0.2, 0.8), 0.0, 0.34)
        pad = E.pad(CHORDS[bar], T.BEAT * 4, attack=0.25, release=0.4, cutoff=1500)
        send.add(T.tm(bar), pad, 0.0, 0.09)
        dry.add(T.tm(bar), pad, 0.0, 0.06)
    dry.add(T.tm(3), E.pad(CHORDS[3], T.BEAT * 4, attack=0.4, release=0.3, cutoff=1100), 0.0, 0.10)

    # --- melody contacts ---
    for t0, kind, m, x in T.contacts():
        pan = float(np.clip(x / 0.8, -0.8, 0.8))
        if kind == 'plate':
            s = plate(m)
            dry.add(t0, s, pan, 0.30)
            send.add(t0, s, pan, 0.28)
        elif kind == 'bar':
            s = xylo(m)
            dry.add(t0, s, -0.35, 0.40)
            send.add(t0, s, -0.35, 0.18)
            dry.add(t0, synth.noise(0.02, 1500, 6000, seed=int(m)) * np.exp(-tt(0.02) / 0.004), -0.35, 0.05)
    roll = synth.noise(T.T_CUP - T.T_TRACK, 80, 900, seed=21)
    dry.add(T.T_TRACK, roll * 0.5, -0.35, 0.10)

    # --- catapult ---
    dry.add(T.T_CUP, sfx.wood(260, 0.9, 31), -0.4, 0.40)                          # ball drops in the cup
    fall = T.T_SLAM - T.T_CUP
    t = tt(fall)
    whistle = np.sin(TAU * np.cumsum(1800 - 1100 * t / fall) / SR) * (t / fall) ** 1.5
    dry.add(T.T_CUP, whistle * 0.25, -0.4, 0.5)                                   # weight falls
    dry.add(T.T_SLAM, E.kick(1.4, 0.7, 42.0), 0.0, 0.9)
    dry.add(T.T_SLAM, sfx.plate_clang(1.0, 7), -0.4, 0.35)
    dry.add(T.T_SLAM, E.crash(0.9, 2.6, seed=6), -0.2, 0.25)
    dry.add(T.T_SLAM + 0.03, E.boing(0.5, 240) * 0.5, -0.4, 0.25)
    dry.add(T.T_SLAM + 0.1, synth.riser(T.T_CATCH - T.T_SLAM - 0.1, seed=7) * 0.38, 0.0, 1.0)

    # --- catch ---
    dry.add(T.T_CATCH, leather_pop(), -0.15, 0.7)
    dry.add(T.T_CATCH, E.kick(1.1, 0.8, 44.0), 0.0, 0.7)
    fin = E.pad(FINAL, T.DURATION - T.T_CATCH, attack=0.02, release=0.5, cutoff=2400)
    fin *= np.minimum(1.0, (T.DURATION - T.T_CATCH - tt(len(fin) / SR)) / 0.35).clip(0, 1)
    dry.add(T.T_CATCH, fin, 0.0, 0.20)
    send.add(T.T_CATCH, fin, 0.0, 0.22)
    for m, d, p in ((86, 0.0, 0.2), (81, 0.05, -0.2), (90, 0.10, 0.1)):
        b = synth.bell(E.hz(m), 2.8, 0.8)
        dry.add(T.T_CATCH + d, b, p, 0.16)
        send.add(T.T_CATCH + d, b, p, 0.22)
    dry.add(T.T_CATCH, E.bass(38, 1.0, 1.0), 0.0, 0.40)
    dry.add(T.T_CATCH + 0.9, E.whoosh(0.3, True, seed=12) * 0.4, 0.1, 0.18)        # winding up again (loop)

    wet = synth.reverb(send.buf, seconds=2.4, wet=1.0)
    mix = dry.buf + (wet - send.buf) * 0.55
    mix, gr = E.limiter(mix, -1.0)
    return mix, gr
