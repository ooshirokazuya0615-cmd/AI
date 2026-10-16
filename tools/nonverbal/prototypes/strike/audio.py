"""Audio for the strike prototype. Everything is synthesized; all events come from timeline.py."""
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


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def glass_mallet(midi, vel=1.0, sec=2.2):
    """Bright glass/ceramic bar: fundamental + inharmonic partials that die fast, plus a click."""
    f = E.hz(midi)
    t = tt(sec)
    x = np.sin(TAU * f * t) * np.exp(-t / (0.55 + 120 / f))
    x += 0.38 * np.sin(TAU * f * 2.756 * t) * np.exp(-t / 0.18)
    x += 0.16 * np.sin(TAU * f * 5.40 * t) * np.exp(-t / 0.06)
    x += 0.10 * np.sin(TAU * f * 8.93 * t) * np.exp(-t / 0.025)
    click = synth.noise(0.012, 2500, 9000, seed=midi) * np.exp(-tt(0.012) / 0.002) * 0.25
    x[:len(click)] += click
    return E.fade_edges(x * vel, 0.0005, 0.02)


def domino_click(seed, vel=1.0):
    n = synth.noise(0.03, 1800, 7500, seed=seed) * np.exp(-tt(0.03) / 0.0045)
    tok = np.sin(TAU * (1700 + 300 * (seed % 5)) * tt(0.03)) * np.exp(-tt(0.03) / 0.006) * 0.35
    return (n + tok) * vel


def rumble(sec, seed=4):
    t = tt(sec)
    low = synth.noise(sec, 35, 260, seed)
    am = 0.75 + 0.25 * np.sin(TAU * 4.1 * t)
    hiss = synth.noise(sec, 2500, 7000, seed + 1) * 0.05
    return low * am * 0.6 + hiss


def render():
    n = int((T.DURATION + 0.5) * SR)
    dry = E.Bus(n)
    send = E.Bus(n)
    rng = np.random.default_rng(7)

    # --- frame 0: the ball leaves the hand and races down the lane ---
    dry.add(0.0, E.whoosh(0.18, True, seed=3) * 0.5, 0.1, 0.20)
    dry.add(T.T_RELEASE + 0.03, synth.thump(0.25, 140, 55), 0.15, 0.55)                 # ball drops on the lane
    dry.add(T.T_RELEASE + 0.03, sfx.wood(420, 0.8, 21), 0.15, 0.22)
    roll = T.T_STRIKE - T.T_RELEASE
    r = rumble(roll + 0.05)
    env = np.minimum(1.0, tt(len(r) / SR) / 0.06)
    dry.add(T.T_RELEASE + 0.03, r * env, 0.0, 0.55)
    dry.add(0.0, synth.riser(T.T_STRIKE, seed=2) * 0.25, 0.0, 1.0)
    r2 = rumble(T.T_DOM0 - T.T_STRIKE, seed=9)
    dry.add(T.T_STRIKE, r2 * np.exp(-tt(len(r2) / SR) / 0.5), 0.0, 0.28)

    # --- strike ---
    dry.add(T.T_STRIKE, E.kick(1.25, 0.6, 46.0), 0.0, 0.9)
    dry.add(T.T_STRIKE, E.crash(0.9, 2.6), 0.15, 0.32)
    for i in range(14):   # dense pin-on-pin clatter in the first 70 ms
        dt = rng.uniform(0.0, 0.07)
        dry.add(T.T_STRIKE + dt, sfx.wood(rng.uniform(650, 1150), 1.0, int(rng.integers(1e6))), rng.uniform(-0.5, 0.5), 0.34)

    pins = T.Pins()
    for t0, kind, x in pins.events():
        pan = float(np.clip(x / 1.3, -0.8, 0.8))
        if kind == 'pin_land':
            dry.add(t0, sfx.wood(rng.uniform(520, 820), 0.9, int(rng.integers(1e6))), pan, 0.42)
            dry.add(t0, synth.thump(0.18, 160, 80) * 0.5, pan, 0.25)
        elif kind == 'pin_tick':
            dry.add(t0, sfx.wood(rng.uniform(700, 1000), 0.4, int(rng.integers(1e6))), pan, 0.16)

    # --- groove: from the strike to the slab; chords follow the melody ---
    nbeats = int(round((T.T_BIG - T.T_STRIKE) / T.BEAT))
    for b in range(nbeats):
        tb = T.T_STRIKE + b * T.BEAT
        if b % 2 == 0 and b > 0:
            dry.add(tb, E.kick(0.75, 0.38, 50.0), 0.0, 0.55)
        if b % 2 == 1:
            dry.add(tb, E.clap(0.6), 0.0, 0.22)
        if tb >= T.T_DOM0 - 1e-6:
            for e in range(2):
                dry.add(tb + e * T.BEAT / 2, E.hat(0.5 if e == 0 else 0.35, False, seed=b * 2 + e), 0.25, 0.10)
    segs = [(T.T_STRIKE, T.T_DOM0, 0)] + [(T.T_DOM0 + i * 4 * T.BEAT, T.T_DOM0 + (i + 1) * 4 * T.BEAT, i + 1) for i in range(3)]
    for t0, t1, ci in segs:
        dur = t1 - t0
        for st in np.arange(0.0, dur - 1e-6, 0.5):
            dry.add(t0 + st, E.bass(T.ROOTS[ci], 0.22, 0.8), 0.0, 0.36)
        pad = E.pad(T.CHORDS[ci], dur, attack=0.25, release=0.4, cutoff=1500)
        send.add(t0, pad, 0.0, 0.10)
        dry.add(t0, pad, 0.0, 0.07)

    # --- dominoes ---
    dry.add(T.T_DOM0, sfx.wood(900, 0.5, 3), -0.1, 0.25)        # ball taps domino 0
    for k in range(1, T.N_DOM):
        tk = T.T_DOM0 + k * T.DT
        dry.add(tk, domino_click(k, rng.uniform(0.7, 1.0)), -0.15 + 0.1 * math.sin(k * 0.3), 0.075)
    for nd in T.note_dominoes():
        m = nd['midi']
        g = glass_mallet(m, 1.0)
        pan = (m - 78) / 20
        dry.add(nd['t'], g, pan, 0.36)
        send.add(nd['t'], g, pan, 0.30)

    # --- hand-over to the slab, one beat of suspense, then the landing ---
    dry.add(T.T_BIG, sfx.wood(330, 1.0, 11), 0.0, 0.45)
    dry.add(T.T_BIG, E.pad((55, 59, 62, 67), T.T_BOOM - T.T_BIG + 0.2, attack=0.6, release=0.2, cutoff=1100), 0.0, 0.12)
    dry.add(T.T_BIG + 0.05, synth.riser(T.T_BOOM - T.T_BIG - 0.05, seed=5) * 0.45, 0.0, 1.0)
    dry.add(T.T_BOOM, E.kick(1.5, 1.2, 40.0), 0.0, 1.0)
    dry.add(T.T_BOOM, synth.noise(0.6, 40, 900, seed=13) * np.exp(-tt(0.6) / 0.12), 0.0, 0.35)
    dry.add(T.T_BOOM, E.crash(1.0, 3.2, seed=4), -0.15, 0.30)
    fin = E.pad(T.FINAL, T.DURATION - T.T_BOOM, attack=0.02, release=1.4, cutoff=2400)
    dry.add(T.T_BOOM, fin, 0.0, 0.20)
    send.add(T.T_BOOM, fin, 0.0, 0.22)
    for m, d, p in ((81, 0.0, 0.2), (88, 0.06, -0.25), (76, 0.12, 0.1)):
        b = synth.bell(E.hz(m), 3.0, 0.8)
        dry.add(T.T_BOOM + d, b, p, 0.20)
        send.add(T.T_BOOM + d, b, p, 0.25)
    dry.add(T.T_BOOM, E.bass(33, 2.0, 1.0), 0.0, 0.40)

    # --- the bowler celebrates: crouch, jump, land on the beat, fist pump ---
    dry.add(T.T_JUMP - 0.12, E.whoosh(0.25, True, seed=3) * 0.5, 0.0, 0.25)
    dry.add(T.T_JUMP + 0.5, synth.thump(0.16, 130, 75) * 0.7, 0.0, 0.35)
    dry.add(T.T_JUMP + 0.5, synth.noise(0.05, 1500, 6000, seed=51) * np.exp(-tt(0.05) / 0.01), 0.0, 0.10)
    for b in (1.0, 1.5):
        dry.add(T.T_JUMP + b, synth.thump(0.12, 130, 80) * 0.5, 0.0, 0.25)

    wet = synth.reverb(send.buf, seconds=2.6, wet=1.0)
    mix = dry.buf + (wet - send.buf) * 0.55
    mix, gr = E.limiter(mix, -1.0)
    return mix, gr
