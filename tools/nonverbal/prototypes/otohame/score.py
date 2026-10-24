"""
The score is the master clock. Audio AND animation read the same event list.

120 BPM, 4/4, A minor pentatonic over Am-F-C-G. Original motif: a tresillo (3+3+2)
staircase that climbs, a quick 8th-note run in bar 4, and a final A5 hit on bar 5.
Bar 1 downbeat at t = 0.5 s (one beat of count-in for the first anticipation).
"""
from dataclasses import dataclass

import numpy as np

import engine as E

BPM = 120
TM = E.TempoMap(BPM, offset=0.5)
S16 = TM.step_sec()
DURATION = 10.0
FINAL_BAR = 4

# (bar, 16th step, midi, length in 16ths)
LEAD = [
    (0, 0, 69, 6), (0, 6, 72, 6), (0, 12, 76, 4),                       # Am  A C E
    (1, 0, 74, 6), (1, 6, 72, 6), (1, 12, 69, 2), (1, 14, 72, 2),       # F   D C A C
    (2, 0, 76, 6), (2, 6, 79, 6), (2, 12, 81, 4),                       # C   E G A
    (3, 0, 79, 4), (3, 4, 76, 4), (3, 8, 74, 2), (3, 10, 76, 2), (3, 12, 79, 4),  # G run
    (4, 0, 81, 16),                                                      # final A5
]
ROOTS = [33, 29, 36, 31, 33]          # A1 F1 C2 G1 | A1
CHORDS = [(57, 60, 64), (53, 57, 60), (55, 60, 64), (55, 59, 62)]
FINAL_CHORD = (57, 60, 64, 71)        # Am add9

DRUMS = {  # per bar 0..3
    'kick':  ['x.....x...x.....', 'x.....x...x.....', 'x.....x...x.....', 'x.......x.......'],
    'snare': ['....x.......x...', '....x.......x...', '....x.......x...', '....x...5.67789x'],
    'hat':   ['x.6.x.6.x.6.x.6.', 'x.6.x.6.x.6.x.o.', 'x.6.x.6.x.6.x.6.', 'x.6.x.6.x.......'],
}
BASS = ['x.....x.....x.x.'] * 4           # tresillo + pickup, sidechained to kick


@dataclass
class Note:
    t: float
    dur: float
    midi: int
    vel: float
    idx: int


def lead_notes():
    out = []
    for i, (bar, st, m, ln) in enumerate(LEAD):
        t = TM.t(bar, st)
        out.append(Note(t, ln * S16, m, 1.0, i))
    return out


def drum_events():
    ev = {k: [] for k in ('kick', 'snare', 'hat', 'ohat', 'crash')}
    for name, bars in DRUMS.items():
        for b, pat in enumerate(bars):
            for t, v, ch in E.step(pat, TM, b):
                ev['ohat' if ch == 'o' else name].append((t, v))
    ev['kick'].append((TM.t(FINAL_BAR), 1.0))
    ev['crash'].append((TM.t(FINAL_BAR), 1.0))
    ev['hat'] += [(TM.t(-1, 12 + i), 0.45 + 0.1 * i) for i in range(4)]  # count-in ticks
    return {k: sorted(v) for k, v in ev.items()}


def downbeats():
    return [TM.t(b) for b in range(FINAL_BAR + 1)]


# ---------------------------------------------------------------- audio render
def render_audio(stems=False):
    n = int(DURATION * E.SR)
    buses = {k: E.Bus(n) for k in ('drums', 'bass', 'pad', 'lead', 'fx', 'foley')}
    send_rev, send_dly = E.Bus(n), np.zeros(n)
    dr = drum_events()
    kicks = [t for t, _ in dr['kick']]

    for t, v in dr['kick']:
        buses['drums'].add(t, E.kick(v), gain=0.60)
    for t, v in dr['snare']:
        s = E.snare(v) + 0.6 * E.clap(v)
        buses['drums'].add(t, s, pan=0.05, gain=0.5 * v)
        send_rev.add(t, s, gain=0.18 * v)
    for i, (t, v) in enumerate(dr['hat']):
        buses['drums'].add(t, E.hat(v, seed=i), pan=0.28, gain=0.16 * v)
    for t, v in dr['ohat']:
        buses['drums'].add(t, E.hat(v, open_=True), pan=0.28, gain=0.14)
    for t, v in dr['crash']:
        c = E.crash(v)
        buses['drums'].add(t, c, pan=-0.2, gain=0.28)
        send_rev.add(t, c, gain=0.12)

    for b in range(4):
        for t, v, _ in E.step(BASS[b], TM, b):
            st = round((t - TM.t(b)) / S16)
            m = ROOTS[b] + (12 if st == 12 else 7 if st == 14 else 0)
            buses['bass'].add(t, E.bass(m, (5 if st < 12 else 1.7) * S16, 0.9 if st else 1.0), gain=0.50)
    buses['bass'].add(TM.t(FINAL_BAR), E.bass(ROOTS[4], 1.3, 1.0), gain=0.45)

    for b in range(4):
        p = E.pad(CHORDS[b], 2.0, attack=0.12, release=0.25)
        buses['pad'].add(TM.t(b) - 0.02, p, gain=0.40)
    p = E.pad(FINAL_CHORD + (45,), 1.2, attack=0.02, release=0.3, cutoff=2200)
    buses['pad'].add(TM.t(FINAL_BAR), p, gain=0.45)

    dly_src = E.Bus(n)
    for nt in lead_notes():
        gate = min(nt.dur * 0.85, 1.25)
        x = E.lead(nt.midi, gate, nt.vel, seed=nt.idx)
        x = np.tanh(1.5 * x) / np.tanh(1.5)            # a little drive = presence on phone speakers
        buses['lead'].add(nt.t, x, pan=0.0, gain=0.40)
        dly_src.add(nt.t, x, gain=0.32)
        send_rev.add(nt.t, x, gain=0.10)
        # ASMR foley: the blob's landing "pop" (pitch follows the note a little)
        buses['foley'].add(nt.t, E.pop(0.8, f0=700 + 3 * (nt.midi - 60) * 10, seed=nt.idx), gain=0.30)
    # final sparkle run (pentatonic up) on the pose
    for i, m in enumerate((81, 84, 86, 88, 91, 93)):
        t = TM.t(FINAL_BAR) + 0.10 + i * S16 * 0.5
        x = E.lead(m + 12, 0.05, 0.5, seed=40 + i)
        buses['fx'].add(t, x, pan=-0.5 + 0.2 * i, gain=0.07)
        send_rev.add(t, x, gain=0.06)
    buses['fx'].add(0.0, E.whoosh(0.5), gain=0.10)                       # count-in rise
    buses['fx'].add(TM.t(FINAL_BAR) - 0.115 - 0.40, E.whoosh(0.40), gain=0.12)  # flip whoosh ends INTO the break
    buses['foley'].add(TM.t(FINAL_BAR) + 0.12, E.boing(0.55, 300), gain=0.16)

    # sidechain: bass + pad duck under every kick
    g = E.duck(n, kicks, depth=0.65)
    buses['bass'].buf *= g[:, None]
    buses['pad'].buf *= E.duck(n, kicks, depth=0.8, release=0.22)[:, None]

    for k in ('pad', 'lead', 'fx'):                    # keep the low end for kick + bass only
        for ch in (0, 1):
            buses[k].buf[:, ch] = E.fft_filter(buses[k].buf[:, ch], lo=170, order=1)
    dly = E.pingpong(dly_src.buf.mean(axis=1), delay=3 * S16, fb=0.32, taps=5)
    import sys
    sys.path.insert(0, '/home/user/AI/tools/nonverbal')
    import synth
    rev = synth.reverb(send_rev.buf, seconds=1.8, wet=1.0, seed=2) - send_rev.buf

    mix = sum(b.buf for b in buses.values()) + 0.22 * dly + 0.55 * rev
    # glue: gentle saturation on the bus, then look-ahead limiter
    # pre-hit break: everything ducks out for the last ~16th before the final downbeat,
    # so the hit lands on contrast instead of on a wall of noise
    th = TM.t(FINAL_BAR)
    brk = np.ones(n)
    i0, i1 = int((th - 0.115) * E.SR), int(th * E.SR)
    r = int(0.018 * E.SR)
    brk[i0:i0 + r] = np.linspace(1, 0.06, r)
    brk[i0 + r:i1] = 0.06
    mix = mix * brk[:, None]
    mix = mix / (np.abs(mix).max() + 1e-9) * 1.3          # drive ~+2.3 dB into the limiter
    mix = np.tanh(mix * 0.9) / 0.9
    mix, gr = E.limiter(mix, ceiling_db=-1.0)
    nf = int(0.25 * E.SR)
    mix[-nf:] *= np.linspace(1, 0, nf)[:, None]
    return (mix, gr, {k: b.buf for k, b in buses.items()}) if stems else (mix, gr)
