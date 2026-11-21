"""Read a Standard MIDI File (no extra libraries) and turn its melody into a song for songs6.py / film6.py.

    python midi_in.py song.mid               # list the tracks and their note ranges
    python midi_in.py song.mid --track 2 --bars 1-8 --title "..."   # print a song dict to paste into SONGS

The melody is taken from one track (or all tracks) as a "skyline": at each moment the highest sounding note.
Notes shorter than --min-ms are merged into the previous one so every contact is playable for the ball.
"""
import argparse
import struct


def _varlen(b, i):
    v = 0
    while True:
        c = b[i]
        i += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80:
            return v, i


def read(path):
    """Returns (ticks_per_beat, tempo_changes [(tick, us_per_beat)], tracks [[(tick_on, tick_off, pitch, vel, ch)]])."""
    data = open(path, 'rb').read()
    assert data[:4] == b'MThd', 'not a MIDI file'
    _, fmt, ntr, div = struct.unpack('>IHHH', data[4:14])
    i, tempos, tracks = 14, [], []
    for _ in range(ntr):
        assert data[i:i + 4] == b'MTrk'
        ln = struct.unpack('>I', data[i + 4:i + 8])[0]
        b, j, t, run, on, notes = data[i + 8:i + 8 + ln], 0, 0, None, {}, []
        while j < len(b):
            dt, j = _varlen(b, j)
            t += dt
            st = b[j]
            if st < 0x80:
                st = run
            else:
                j += 1
            if st == 0xFF:
                typ = b[j]
                l2, j = _varlen(b, j + 1)
                if typ == 0x51:
                    tempos.append((t, int.from_bytes(b[j:j + 3], 'big')))
                j += l2
            elif st in (0xF0, 0xF7):
                l2, j = _varlen(b, j)
                j += l2
            else:
                run = st
                kind, ch = st & 0xF0, st & 0x0F
                if kind in (0xC0, 0xD0):
                    j += 1
                    continue
                d1, d2 = b[j], b[j + 1]
                j += 2
                if kind == 0x90 and d2 > 0:
                    on[(ch, d1)] = (t, d2)
                elif kind in (0x80, 0x90):
                    if (ch, d1) in on:
                        t0, vel = on.pop((ch, d1))
                        notes.append((t0, t, d1, vel, ch))
        tracks.append(sorted(notes))
        i += 8 + ln
    return div, sorted(tempos) or [(0, 500000)], tracks


def tick_to_sec(div, tempos):
    def f(tick):
        sec, last_t, us = 0.0, 0, tempos[0][1]
        for tt, u in tempos:
            if tt >= tick:
                break
            sec += (tt - last_t) * us / 1e6 / div
            last_t, us = tt, u
        return sec + (tick - last_t) * us / 1e6 / div
    return f


def skyline(notes):
    """Highest note at each onset; returns [(tick_on, tick_off, pitch)] without overlaps."""
    by_on = {}
    for t0, t1, p, v, ch in notes:
        if ch == 9:       # drums
            continue
        if t0 not in by_on or p > by_on[t0][1]:
            by_on[t0] = (t1, p)
    ons = sorted(by_on)
    out = []
    for k, t0 in enumerate(ons):
        t1, p = by_on[t0]
        if k + 1 < len(ons):
            t1 = min(t1, ons[k + 1]) if t1 > t0 else ons[k + 1]
        out.append((t0, t1, p))
    return out


NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def name(p):
    return f'{NAMES[p % 12]}{p // 12 - 1}'


def to_song(path, track=None, bars=None, min_ms=110, title='untitled', composer='', gap_in='rail'):
    div, tempos, tracks = read(path)
    sec = tick_to_sec(div, tempos)
    notes = [n for k, tr in enumerate(tracks) if track is None or k == track for n in tr]
    line = skyline(notes)
    if bars:
        lo, hi = bars
        line = [n for n in line if (lo - 1) * 4 * div <= n[0] < hi * 4 * div]
    beat = tempos[0][1] / 1e6
    unit = beat / 4                      # durations in sixteenths
    merged = []
    for t0, t1, p in line:
        s0 = sec(t0)
        if merged and (s0 - merged[-1][0]) * 1000 < min_ms:
            continue
        merged.append((s0, p))
    out = []
    for k, (s0, p) in enumerate(merged):
        s1 = merged[k + 1][0] if k + 1 < len(merged) else s0 + beat
        out.append((name(p), round((s1 - s0) / unit * 4) / 4))
    centre = sorted(p for _, p in merged)[len(merged) // 2] if merged else 64
    return dict(key=title.lower()[:8], title=title, composer=composer, unit=round(unit, 4), beat=round(beat, 4),
                centre=centre, notes=out, palette=dict(fast='tile', normal='pad', long='block'),
                drone=(name(centre - 24), name(centre - 17)), gap_in=gap_in)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mid')
    ap.add_argument('--track', type=int)
    ap.add_argument('--bars')
    ap.add_argument('--title', default='untitled')
    a = ap.parse_args()
    div, tempos, tracks = read(a.mid)
    if a.track is None and not a.bars:
        print('ticks/beat', div, 'tempo bpm', round(60e6 / tempos[0][1], 1))
        for k, tr in enumerate(tracks):
            if tr:
                ps = [n[2] for n in tr]
                print(f'track {k}: {len(tr)} notes, range {name(min(ps))}-{name(max(ps))}, channels {sorted(set(n[4] for n in tr))}')
    else:
        bars = tuple(int(x) for x in a.bars.split('-')) if a.bars else None
        print(repr(to_song(a.mid, a.track, bars, title=a.title)))
