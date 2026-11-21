"""
Turn events.json (collision events extracted from the Bullet bake) into a
sample-accurate soundtrack with the repo's synth parts (copied, read-only use).

  venv/bin/python events_audio.py --start-frame 1 --out audio.wav
Frame f (1-based, video fps) shows simulation time (f - 1) / fps, so an event at
sim time t goes to sample round((t - (start_frame - 1) / fps) * 48000).
"""
import argparse
import json
from pathlib import Path

import numpy as np

import synth_copy as synth

ap = argparse.ArgumentParser()
ap.add_argument('--start-frame', type=int, default=1)
ap.add_argument('--frames', type=int, default=0, help='0 = to the end')
ap.add_argument('--out', default='audio.wav')
a = ap.parse_args()

HERE = Path(__file__).resolve().parent
m = json.loads((HERE / 'events.json').read_text())
fps = m['fps']
t0 = (a.start_frame - 1) / fps
dur = (a.frames or (m['frames'] - a.start_frame + 1)) / fps
mix = synth.Mix(dur + 3)

PENTA = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81, 84]      # A minor / C major pentatonic
cache = {}


def tone(key, fn):
    if key not in cache:
        cache[key] = fn()
    return cache[key]


def knock(seed):
    n = synth.noise(0.06, 700, 3500, seed) * np.exp(-np.arange(int(0.06 * synth.SR)) / (0.008 * synth.SR))
    th = synth.thump(0.12, 200, 120)
    out = np.zeros(max(len(n), len(th)))
    out[:len(n)] += 0.6 * n
    out[:len(th)] += th
    return out


used = 0
for e in m['events']:
    t = e['t'] - t0
    if t < 0 or t > dur:
        continue
    x = e['pos'][0]
    pan = float(np.clip(x / 5.0, -0.9, 0.9))
    g = float(np.clip(e['dv'] / 5.0, 0.08, 1.0))
    if e['kind'] == 'peg':
        row = int(e['obj'].split('_')[1])
        idx = int(np.clip(round((x + 4.4) / 1.1), 0, 7)) + (4 - row) // 2
        midi = PENTA[min(idx, len(PENTA) - 1)]
        mix.add(t, tone(('bell', midi), lambda: synth.bell(synth.hz(midi), 2.2)), pan, 0.9 * g)
    elif e['kind'] == 'ball':
        midi = 88 + (e['ball'] % 5) * 2
        mix.add(t, tone(('click', midi), lambda: synth.bell(synth.hz(midi), 0.35, bright=1.6)), pan, 0.25 * g)
    elif e['kind'] == 'ramp':
        mix.add(t, tone('ramp', lambda: synth.thump(0.22, 240, 80)), pan, 0.8 * g)
    else:  # walls, frame, floor, dividers
        mix.add(t, tone(('knock', e['ball'] % 3), lambda: knock(e['ball'] % 3)), pan, 0.5 * g)
    used += 1

buf = synth.reverb(mix.buf, seconds=2.2, wet=0.18)
synth.write_wav(HERE / a.out, buf)
print(f'{used} events -> {a.out} ({dur:.2f} s from sim t = {t0:.3f} s)')
