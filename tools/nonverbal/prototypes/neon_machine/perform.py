"""How the score film's pieces are played: a velocity for every note and how long it rings.

A machine playing every note at one strength sounds like a machine. Here each piece has its own dynamic
arc (Mountain King grows from pp to ff, the Fifth starts at its loudest, Für Elise stays soft), downbeats
lean a little, higher notes in a phrase sing a little more, long notes get weight, and a touch of
unevenness keeps it human. Articulation follows each style: Canon and Für Elise ring into each other as
with the pedal down, Turca and Mountain King are short and detached.
"""
import numpy as np

# velocity (0..1) at the first and at the last note of each piece
# (kept within about 5 dB of each other on average, so nobody reaches for the volume between pieces)
DYNAMICS = {'canon': (0.60, 0.78), 'toc': (0.88, 0.94), 'tm': (0.67, 0.78), 'ekn': (0.80, 0.88),
            'b5': (0.95, 0.78), 'fe': (0.54, 0.66), 'otj': (0.48, 0.68), 'mk': (0.36, 1.0)}
# how long a note rings, as a multiple of its sounding length (touch and pedal), plus 0.10 s
RING = {'canon': 1.8, 'toc': 1.15, 'tm': 0.8, 'ekn': 0.95, 'b5': 1.4, 'fe': 2.4, 'otj': 1.05, 'mk': 0.75}


def plan(S, C):
    """Velocity and ring length for every contact index, and each piece's (t0, t1, v0, v1) for its
    accompaniment."""
    vel, ring, arcs = {}, {}, {}
    rng = np.random.default_rng(3)
    for s, song in enumerate(S.SONGS):
        hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
        if not hs:
            continue
        v0, v1 = DYNAMICS.get(song['key'], (0.6, 0.6))
        arcs[s] = (hs[0]['t'], hs[-1]['t'], v0, v1)
        nun = song.get('nunits') or [u for _, u in song['notes']]
        bu, pu = song.get('bar_units'), song.get('pickup_units') or 0
        centre = float(np.mean([h['midi'] for h in hs]))
        pos = 0.0
        for k, h in enumerate(hs):
            v = v0 + (v1 - v0) * k / max(1, len(hs) - 1)
            if bu:
                in_bar = (pos - pu) % bu
                if abs(in_bar) < 1e-6:
                    v += 0.07                                   # downbeat
                elif bu % 2 == 0 and abs(in_bar - bu / 2) < 1e-6:
                    v += 0.035                                  # the bar's other strong beat
            v += 0.08 * max(-1.0, min(1.0, (h['midi'] - centre) / 12))   # the line sings as it rises
            if h['dur'] >= 2 * song['beat'] - 1e-6:
                v += 0.04                                       # long notes carry weight
            v += rng.normal(0, 0.018)
            vel[h['i']] = float(min(1.0, max(0.08, v)))
            r = h['dur'] * RING.get(song['key'], 1.0) + 0.10
            if k == len(hs) - 1:
                r = max(r, 2.6)                                 # the last note of a piece rings out
            ring[h['i']] = min(4.0, r)
            pos += nun[k] if k < len(nun) else 1
    return vel, ring, arcs


def level_at(arcs, s, t):
    """The piece's dynamic at time t (for its accompaniment)."""
    t0, t1, v0, v1 = arcs[s]
    return v0 + (v1 - v0) * min(1.0, max(0.0, (t - t0) / max(1e-6, t1 - t0)))
