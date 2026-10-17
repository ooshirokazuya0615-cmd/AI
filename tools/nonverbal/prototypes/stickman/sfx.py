"""
Sample-free sound for the stickman scene. Every sound is synthesized from the
physics recording: contact events -> material-specific modal/noise impacts,
continuous state -> rolling rumble, air whoosh, trampoline boing.
A light musical layer (original motif in D major pentatonic) rides on big hits.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, '/home/user/AI/tools/nonverbal')
sys.dont_write_bytecode = True
import synth  # noqa: E402  (repo module, imported read-only)

import sim  # noqa: E402

SR = synth.SR
TAU = 2 * np.pi


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def env_attack(x, ms=1.5):
    n = max(1, int(ms * 1e-3 * SR))
    x[:n] *= np.linspace(0, 1, n)
    return x


def modal(freqs, decays, amps, sec, detune=0.0, seed=0):
    t = tt(sec)
    out = np.zeros_like(t)
    rng = np.random.default_rng(seed)
    for f, d, a in zip(freqs, decays, amps):
        if f >= SR / 2 - 500:
            continue
        f = f * (1 + detune * rng.normal())
        out += a * np.sin(TAU * f * t) * np.exp(-t / d)
    return env_attack(out, 0.6)


def burst(sec, lo, hi, tau, seed):
    t = tt(sec)
    return synth.noise(sec, lo, hi, seed) * np.exp(-t / tau)


# ---------------- materials ----------------

def wood(f0, s, seed):
    """Wooden step: inharmonic block modes + bright knock, darker when soft."""
    bright = 0.35 + 0.65 * min(s, 1)
    m = modal(f0 * np.array([1, 1.58, 2.41, 3.62, 5.1]), [0.085, 0.05, 0.034, 0.022, 0.014],
              np.array([1, 0.55, 0.42, 0.3, 0.2]) * np.array([1, 1, bright, bright ** 2, bright ** 3]), 0.35, 0.01, seed)
    k = burst(0.05, 900, 7000 * bright + 2000, 0.004, seed + 1) * 0.7 * bright
    out = m * 0.8
    out[:len(k)] += k
    if s > 0.5:
        th = synth.thump(0.16, 150, 70) * 0.28 * (s - 0.3)
        out[:len(th)] += th
    return out


def metal_ting(f, s, seed):
    """Struck steel pin: free-bar ratios, long ring, tiny click."""
    m = modal(f * np.array([1, 2.756, 5.404, 8.933]), [1.6, 0.7, 0.28, 0.12],
              [1, 0.45 * (0.5 + s), 0.25 * (0.4 + s), 0.12], 2.2, 0.0, seed)
    m += 0.25 * modal([f * 1.003], [1.2], [1], 2.2)          # slow beating = shimmer
    k = burst(0.02, 3000, 14000, 0.0015, seed) * 0.35
    m[:len(k)] += k
    return m * 0.55


def plate_clang(s, seed):
    """Steel sheet: dense inharmonic modes with beating pairs + noisy crash."""
    rng = np.random.default_rng(seed)
    f0 = 146.8  # D3
    ratios = np.array([1, 1.49, 2.12, 2.53, 3.07, 3.71, 4.38, 5.27, 6.4, 7.7])
    freqs = np.concatenate([f0 * ratios, f0 * ratios * 1.004])
    decays = np.concatenate([np.linspace(1.3, 0.25, 10)] * 2)
    amps = np.concatenate([rng.uniform(0.4, 1.0, 10) / np.sqrt(np.arange(1, 11))] * 2)
    m = modal(freqs, decays, amps, 2.0, 0.0, seed) * 0.55
    k = burst(0.25, 900, 9000, 0.035, seed + 3) * 0.45
    m[:len(k)] += k
    th = synth.thump(0.25, 110, 50) * 0.4
    m[:len(th)] += th
    return m * (0.5 + 0.5 * min(s, 1))


def stone(s, seed):
    k = burst(0.2, 70, 1400, 0.03, seed) * 0.8
    th = synth.thump(0.2, 95, 45) * 0.7
    k[:len(th)] += th
    return k


def body_thud(s, seed):
    """Soft body hit: low thud + a little cloth swish."""
    t = tt(0.16)
    th = np.sin(TAU * np.cumsum(95 + 70 * np.exp(-t / 0.015)) / SR) * np.exp(-t / 0.03)
    n = burst(0.16, 140, 1200, 0.022, seed) * 0.6
    sw = burst(0.16, 2500, 9000, 0.010, seed + 7) * 0.18
    return env_attack(th * 0.5 + n + sw, 1.0)


def head_bonk(s, seed):
    """Cartoon 'bonk': hollow knock with a quick pitch drop."""
    t = tt(0.3)
    f = 430 + 300 * np.exp(-t / 0.018)
    tone = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.07)
    tone += 0.35 * np.sin(TAU * np.cumsum(f * 2.71) / SR) * np.exp(-t / 0.035)
    k = burst(0.3, 1500, 7000, 0.003, seed) * 0.3
    return env_attack(tone + k, 0.8) * 0.6


def boing(s, seed):
    """Rubber trampoline: pitch-wobbling sine 'boing' + soft rubber thump."""
    t = tt(0.9)
    f0 = 92 + 55 * min(s, 1.2)
    wob = 1 + 0.16 * np.exp(-t / 0.28) * np.sin(TAU * 11.5 * t)
    f = f0 * (1 + 0.55 * np.exp(-t / 0.045)) * wob
    tone = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / 0.33)
    tone += 0.3 * np.sin(TAU * np.cumsum(2 * f) / SR) * np.exp(-t / 0.15)
    th = synth.thump(0.25, 120, 40)
    tone[:len(th)] += 0.6 * th
    return env_attack(tone, 2.0) * 0.7


def ball_hit(s, seed):
    """Bowling ball: heavy, dull, low wood thunk."""
    m = modal([118, 191, 287], [0.12, 0.07, 0.04], [1, 0.5, 0.3], 0.4, 0.0, seed)
    th = synth.thump(0.3, 100, 42)
    m[:len(th)] += 0.8 * th
    return m * 0.7


# ---------------- music ----------------

def mallet(f, sec=1.6, vel=1.0):
    """Soft marimba-like mallet: fundamental + 4th-ish overtone that dies fast."""
    t = tt(sec)
    x = np.sin(TAU * f * t) * np.exp(-t / (0.35 + 90 / f))
    x += 0.30 * vel * np.sin(TAU * f * 3.98 * t) * np.exp(-t / 0.06)
    x += 0.10 * np.sin(TAU * f * 2 * t) * np.exp(-t / 0.2)
    return env_attack(x, 3.0)


def chord_pad(midis, sec, fade=0.8):
    return synth.pad([synth.hz(m) for m in midis], sec, fade=fade)


# Original motif, D major pentatonic, falling then answering upward
MOTIF = [78, 76, 74, 69, 71, 74, 76, 74, 69, 71, 66, 69, 74]
STEP_NOTES = [69, 66, 64, 62, 59, 57]               # stairs ring a falling pentatonic
PEG_SCALE = [86, 88, 90, 93, 95, 98]                # pegs: left -> right ascending


def peg_note(x):
    k = int(np.clip((x + 400) / 900 * len(PEG_SCALE), 0, len(PEG_SCALE) - 1))
    return PEG_SCALE[k]


def eq(buf):
    """Master EQ: 2nd-order high-pass at 45 Hz and a -5 dB low shelf under ~140 Hz."""
    n = len(buf)
    size = 1 << int(np.ceil(np.log2(n)))
    f = np.fft.rfftfreq(size, 1 / SR)
    hp = 1 / np.sqrt(1 + (45 / np.maximum(f, 1)) ** 4)
    shelf = 10 ** (-7 / 20) + (1 - 10 ** (-7 / 20)) / (1 + (140 / np.maximum(f, 1)) ** 2)
    g = hp * shelf
    out = np.empty_like(buf)
    for ch in range(buf.shape[1]):
        out[:, ch] = np.fft.irfft(np.fft.rfft(buf[:, ch], size) * g, size)[:n]
    return out


def control_to_audio(series, n_audio):
    """Physics-rate (600 Hz) series -> audio-rate by linear interpolation."""
    tp = np.arange(len(series)) * sim.DT
    ta = np.arange(n_audio) / SR
    return np.interp(ta, tp, series)


def render_audio(tl, duration):
    rec = tl.rec
    mix = synth.Mix(duration)
    n = len(mix.buf)
    cam = tl.cam

    def pan_of(t, x):
        c = cam[tl.idx(t)]
        return float(np.clip((x - c[0]) / (540 / c[2]) * 0.65, -0.8, 0.8))

    # ---- impacts (deduplicated: same surface within 12 ms -> keep loudest) ----
    evs = sorted(rec.events, key=lambda e: e['t'])
    kept = []
    for e in evs:
        s = tl.strength(e)
        if s < 0.035:
            continue
        if kept and e['a'] == kept[-1]['a'] and e['t'] - kept[-1]['t'] < 0.012:
            if s > tl.strength(kept[-1]):
                kept[-1] = e
            continue
        kept.append(e)
    tally = {}
    for j, e in enumerate(kept):
        s = tl.strength(e)
        t, x = e['t'], e['x']
        surf, other = e['mat'], e['other']
        tally[surf] = tally.get(surf, 0) + 1
        g = 0.55 * min(s, 1.3) ** 1.1
        p = pan_of(t, x)
        seed = j + 11
        if surf == 'wood':
            step = int(e['a'][4:]) if e['a'].startswith('step') else None
            f0 = synth.hz(STEP_NOTES[step] - 12) if step is not None else 180.0
            if other == 'ball' or e['b'] == 'ball':
                mix.add(t, ball_hit(s, seed), p, g * 0.9)
            mix.add(t, wood(f0, s, seed), p, g)
        elif surf == 'metal':
            if e['a'] == 'plate':
                mix.add(t, plate_clang(s, seed), p, g * 1.1)
            else:
                mix.add(t, metal_ting(synth.hz(peg_note(x)), s, seed), p, g * 0.9)
        elif surf == 'rubber':
            if s > 0.25 and (e['b'] in ('torso', 'head', 'thigh_n', 'thigh_f')):
                mix.add(t, boing(s, seed), p * 0.5, g * 0.9)
            mix.add(t, body_thud(s, seed), p, g * 0.5)
        elif surf == 'stone':
            mix.add(t, stone(s, seed), p, g * 0.8)
        elif surf == 'ball':
            mix.add(t, ball_hit(s, seed), p, g * 0.8)
        if other == 'body':
            mix.add(t, body_thud(s, seed + 5), p, g * 0.38)
            if e['b'] == 'head' and s > 0.35:
                mix.add(t, head_bonk(s, seed), p, g * 0.7)

    # ---- ball rolling rumble (only while the ball is on a surface) ----
    roll = control_to_audio(rec.ball[:, 3], n)
    ang = control_to_audio(rec.ball[:, 2], n)
    rumble = synth.noise(n / SR, 90, 520, 5)
    bumps = 0.75 + 0.25 * np.abs(np.sin(ang * 1.5))       # finger holes / unevenness
    amp = np.clip(roll / 700, 0, 1.2) ** 1.3 * bumps
    amp = np.convolve(amp, np.ones(480) / 480, mode='same')
    rumble *= amp * 0.20
    xs = control_to_audio(rec.ball[:, 0], n)
    camx = control_to_audio(cam[:, 0], n)
    pan = np.clip((xs - camx) / 400, -0.8, 0.8)
    a = (pan + 1) * np.pi / 4
    mix.buf[:, 0] += rumble * np.cos(a)
    mix.buf[:, 1] += rumble * np.sin(a)

    # ---- air whoosh from ragdoll speed ----
    pos = rec.bodies[:, :, :2]
    spd = np.linalg.norm(np.gradient(pos, sim.DT, axis=0), axis=2).max(axis=1)
    spd = np.convolve(spd, np.ones(30) / 30, mode='same')
    v = control_to_audio(spd, n)
    w = np.clip((v - 500) / 1700, 0, 1) ** 2
    lo = synth.noise(n / SR, 250, 1400, 21)
    hi = synth.noise(n / SR, 1400, 6000, 22)
    whoosh = (lo * (1 - w) + hi * w) * w * 0.10
    mix.buf[:, 0] += whoosh
    mix.buf[:, 1] += whoosh

    # ---- music ----
    # "!" sting when he notices the ball
    if rec.t_notice > 0:
        for k, m in enumerate((74, 81)):
            mix.add(rec.t_notice + 0.07 * k, mallet(synth.hz(m), 0.8), 0.0, 0.16)
    # motif on big hits
    last, k = -1.0, 0
    for (t, x, y, s) in tl.big:
        if s < 0.6 or t - last < 0.2 or t > tl.t_settle:
            continue
        m = MOTIF[k % len(MOTIF)]
        k += 1
        mix.add(t, mallet(synth.hz(m), 1.6, min(s, 1)), pan_of(t, x) * 0.5, 0.15)
        last = t
    # chord bed: changes on story beats
    plate_t = next((e['t'] for e in rec.events if e['a'] == 'plate'), tl.t_pad - 1.5)
    beats = [(0.0, [62, 66, 69, 76]),                 # Dadd9
             (rec.t_hit, [59, 62, 66, 69]),           # Bm7
             (plate_t, [55, 59, 62, 66]),             # Gmaj7
             (tl.t_pad, [57, 62, 64, 69]),            # Asus4
             (tl.t_settle, [50, 57, 62, 66, 69, 76])]  # D add9 (home, the only low note)
    for j, (t0, notes) in enumerate(beats):
        t1 = beats[j + 1][0] if j + 1 < len(beats) else duration
        sec = max(t1 - t0 + 0.6, 0.8)
        mix.add(max(t0 - 0.15, 0), chord_pad(notes, sec, fade=0.5 if j else 0.9), 0.0, 0.07 if j < 4 else 0.10)
    # dizzy twinkle while the stars spin
    tw = [93, 90, 86, 90, 93, 98]
    t = tl.t_settle + 0.15
    k = 0
    while t < duration - 0.3:
        mix.add(t, mallet(synth.hz(tw[k % len(tw)]), 1.2, 0.6), 0.35 * math.sin(k * 2.1), 0.07)
        t += 0.25
        k += 1

    out = synth.reverb(eq(mix.buf), seconds=1.1, wet=0.14, seed=3)
    # tail fade to silence with the picture
    fade_n = int(0.35 * SR)
    out[-fade_n:] *= np.linspace(1, 0, fade_n)[:, None]
    return out, tally, kept
