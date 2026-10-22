"""Long-form medley (v6): eight public-domain melodies, joined by one-bar silent gaps.

Each song: name, composer (death year), unit (seconds per duration unit), beat (seconds per beat, used to
count the gap before the song), centre (MIDI pitch at x = 0 of its section), notes [(name, units)],
palette (which instrument families it uses), tonic/fifth drone for the soft accompaniment,
and the gap that leads INTO the song ('rail', 'launch' or 'chute').

The transcriptions are from memory of the standard melodies; check each against an IMSLP score
and write the music ledger (POLICY ch. 7) before anything is published.
"""
_N = {}
for octave in range(2, 7):
    for k, nm in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']):
        _N[f'{nm}{octave}'] = 12 * (octave + 1) + k
for alias, real in (('Eb', 'D#'), ('Ab', 'G#'), ('Bb', 'A#'), ('Db', 'C#'), ('Gb', 'F#')):
    for octave in range(2, 7):
        _N[f'{alias}{octave}'] = _N[f'{real}{octave}']


def midi(name):
    return _N[name]


SONGS = [
    dict(key='ekn', title='Eine kleine Nachtmusik', composer='Mozart (d. 1791)', unit=0.21, beat=0.42, centre=67,
         notes=[('G4', 3), ('D4', 1), ('G4', 3), ('D4', 1), ('G4', 1), ('D4', 1), ('G4', 1), ('B4', 1), ('D5', 4),
                ('C5', 3), ('A4', 1), ('C5', 3), ('A4', 1), ('C5', 1), ('A4', 1), ('F#4', 1), ('A4', 1), ('D4', 4)] * 2,
         palette=dict(fast='tile', normal='bell', long='pad'), drone=('G2', 'D3'), gap_in=None),
    dict(key='fe', title='Für Elise', composer='Beethoven (d. 1827)', unit=0.23, beat=0.69, centre=70,
         notes=[('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
                ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('G#4', 1), ('B4', 1), ('C5', 3), ('E4', 1),
                ('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
                ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('C5', 1), ('B4', 1), ('A4', 4)],
         palette=dict(fast='tile', normal='pad', long='block'), drone=('A2', 'E3'), gap_in='rail'),
    dict(key='tm', title='Rondo alla Turca', composer='Mozart (d. 1791)', unit=0.15, beat=0.6, centre=76,
         notes=[('B4', 1), ('A4', 1), ('G#4', 1), ('A4', 1), ('C5', 4), ('D5', 1), ('C5', 1), ('B4', 1), ('C5', 1), ('E5', 4),
                ('F5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B5', 1), ('A5', 1), ('G#5', 1), ('A5', 1),
                ('B5', 1), ('A5', 1), ('G#5', 1), ('A5', 1), ('C6', 4)] * 2,
         palette=dict(fast='xylo', normal='pad', long='cymbal'), drone=('A2', 'E3'), gap_in='chute'),
    dict(key='b5', title='Symphony No. 5', composer='Beethoven (d. 1827)', unit=0.17, beat=0.68, centre=62,
         notes=[('G4', 1), ('G4', 1), ('G4', 1), ('Eb4', 9), ('F4', 1), ('F4', 1), ('F4', 1), ('D4', 11),
                ('G4', 1), ('G4', 1), ('G4', 1), ('Eb4', 1), ('Ab4', 1), ('Ab4', 1), ('Ab4', 1), ('G4', 1),
                ('Eb5', 1), ('Eb5', 1), ('Eb5', 1), ('C5', 9)],
         palette=dict(fast='pad', normal='pad', long='cymbal'), drone=('C3', 'G3'), gap_in='launch'),
    dict(key='canon', title='Canon in D', composer='Pachelbel (d. 1706)', unit=0.26, beat=0.52, centre=69,
         notes=[('F#5', 4), ('E5', 4), ('D5', 4), ('C#5', 4), ('B4', 4), ('A4', 4), ('B4', 4), ('C#5', 4),
                ('D5', 2), ('C#5', 2), ('B4', 2), ('A4', 2), ('G4', 2), ('F#4', 2), ('G4', 2), ('E4', 2), ('D4', 6)],
         palette=dict(fast='flask', normal='flask', long='flask'), drone=('D3', 'A3'), gap_in='rail'),
    dict(key='toc', title='Toccata in D minor', composer='Bach (d. 1750)', unit=0.13, beat=0.52, centre=69,
         notes=[('A5', 1), ('G5', 1), ('A5', 8), ('G5', 1), ('F5', 1), ('E5', 1), ('D5', 1), ('C#5', 3), ('D5', 10),
                ('A4', 1), ('G4', 1), ('A4', 8), ('E4', 1), ('F4', 1), ('C#4', 3), ('D4', 12)],
         palette=dict(fast='pipe', normal='pipe', long='pipe'), drone=('D2', 'A2'), gap_in='chute'),
    dict(key='mk', title='In the Hall of the Mountain King', composer='Grieg (d. 1907)', unit=0.2, beat=0.4, centre=62,
         notes=[('A3', 1), ('B3', 1), ('C4', 1), ('D4', 1), ('E4', 1), ('C4', 1), ('E4', 2),
                ('D#4', 1), ('B3', 1), ('D#4', 2), ('D4', 1), ('A#3', 1), ('D4', 2),
                ('A3', 1), ('B3', 1), ('C4', 1), ('D4', 1), ('E4', 1), ('C4', 1), ('E4', 1), ('A4', 1),
                ('G4', 1), ('E4', 1), ('C4', 1), ('E4', 1), ('G4', 4)],
         palette=dict(fast='bumper', normal='pad', long='block'), drone=('A2', 'E3'), gap_in='launch'),
    dict(key='otj', title='Ode to Joy', composer='Beethoven (d. 1827)', unit=0.30, beat=0.30, centre=64,
         notes=[('E4', 1), ('E4', 1), ('F4', 1), ('G4', 1), ('G4', 1), ('F4', 1), ('E4', 1), ('D4', 1),
                ('C4', 1), ('C4', 1), ('D4', 1), ('E4', 1), ('E4', 1.5), ('D4', 0.5), ('D4', 2),
                ('E4', 1), ('E4', 1), ('F4', 1), ('G4', 1), ('G4', 1), ('F4', 1), ('E4', 1), ('D4', 1),
                ('C4', 1), ('C4', 1), ('D4', 1), ('E4', 1), ('D4', 1.5), ('C4', 0.5), ('C4', 2)],
         palette=dict(fast='tile', normal='pad', long='block'), drone=('C3', 'G3'), gap_in='rail'),
]

START = 0.4
GAP_BEATS = 4          # (kept for older callers)
NEW_SONG_GAP = 1.4     # extra silence before a NEW song, after (at most 0.8 s of) the last note ringing out
FINAL_NOTE = 'C5'
FINAL_REST_BEATS, FINAL_FLIGHT_BEATS = 4, 4
OUTRO = 4.5


def assign(song):
    """Instrument for every note of a song, chosen so the picture keeps changing:
    runs of short notes alternate between the 'fast' family and the 'normal' one (a run is at most 6 notes);
    a repeated pitch on a pad or bell is a second bounce on the same one ('again'); long notes use 'long'."""
    notes, pal = song['notes'], song['palette']
    out, run_idx, k = [], 0, 0
    while k < len(notes):
        if notes[k][1] <= 1:
            j = k
            while j < len(notes) and notes[j][1] <= 1 and j - k < 6:
                j += 1
            fam = pal['fast'] if (run_idx % 2 == 0 and j - k >= 3) else pal['normal']
            run_idx += 1
            for q in range(k, j):
                out.append(fam)
            k = j
        else:
            out.append(pal['long'] if notes[k][1] >= 3 else pal['normal'])
            k += 1
    for q in range(1, len(notes)):
        if notes[q][0] == notes[q - 1][0] and out[q] == out[q - 1] and out[q] in ('pad', 'bell', 'cymbal', 'block'):
            out[q] = 'again'
    return out


def timeline(songs=None, final_note=None):
    """Contacts for the whole film and the gaps between sections.

    How long a gap is ("ma"):
      join='same' (the next section continues the same piece): no extra time at all. The gap machine
        (chute, launch...) runs while the last note is held, and the ball lands on the next downbeat.
      join='new' (a different piece): the last note rings for at most 0.8 s, then NEW_SONG_GAP of silence,
        so about 2 s from the last hit to the next song, as in the reference videos.
    The final drum lands about 1.9 s after the last note: the ball rests in the cup while the note rings
    (at most 1 s), then flies 0.9 s.
    """
    SONGS_ = songs if songs is not None else SONGS
    final_note = final_note or FINAL_NOTE
    contacts, gaps = [], []
    t = START
    for s, song in enumerate(SONGS_):
        if s > 0:
            last = contacts[-1]
            if song.get('join', 'new') == 'same':
                t1 = last['t'] + last['dur']
            else:
                t1 = last['t'] + min(last['dur'], 0.8) + NEW_SONG_GAP
            g = dict(kind=song['gap_in'], t0=last['t'], t1=t1, s=s, join=song.get('join', 'new'),
                     beats=[t1 - song['beat'] * (GAP_BEATS - b) for b in range(GAP_BEATS)])
            # when the machine in the gap does its one audible thing
            g['t_rail0'] = last['t'] + 0.30                  # rail: ball reaches the rail
            g['t_sw'] = t1 - 0.42                            # rail: the switch click, then a short drop
            g['t_in'] = last['t'] + 0.30                     # chute: enters the funnel
            g['t_out'] = t1 - 0.32                           # chute: leaves the tube
            g['t_launch'] = t1 - min(0.85, 0.5 * (t1 - last['t']))   # launch: the cup fires
            gaps.append(g)
            t = t1
        mechs = assign(song)
        for j, (n, u) in enumerate(song['notes']):
            contacts.append(dict(i=len(contacts), s=s, j=j, t=t, midi=midi(n), dur=u * song['unit'], mech=mechs[j]))
            t += u * song['unit']
    last = contacts[-1]
    launch = last['t'] + min(last['dur'], 1.0)
    final = dict(i=len(contacts), s=len(SONGS_) - 1, j=-1, t=launch + 0.9, midi=midi(final_note),
                 dur=2.0, mech='bigdrum', launch=launch)
    last['mech'] = 'cup'
    contacts.append(final)
    return contacts, gaps


def total_seconds(songs=None, final_note=None):
    c, _ = timeline(songs, final_note)
    return c[-1]['t'] + OUTRO
