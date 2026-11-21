"""v5 timeline: the v4 medley with musically timed gaps ("ma"), for the long-form (16:9) format.

Rules for the gaps:
  1. a song rings out its last note in full before the silence starts
  2. a gap is counted in beats of the next song: one bar (4 beats); the sounds inside it fall on beats
     (rail joints on beats 1-3, the switch on beat 4), and the next song starts on the following downbeat
  3. the last melody note is played on time; the ball rests in a cup for 2 silent beats, launches on the
     next downbeat, flies one bar and lands on the big drum on the downbeat after that

  section A  Beethoven, "Für Elise" (WoO 59; published 1867), opening A section, right hand
  gap 1      silence: the ball glides along a coaster rail and flips a light switch; section B powers on
  section B  Beethoven, Symphony No. 9, "Ode to Joy" theme (1824), two phrases
  gap 2      a fermata: the ball is launched high into the air
  finale     the last note lands on the big drum; reveal

Both compositions are public domain; the performance and sound are generated here.
Every melody note is one contact of the ball. The accompaniment has no contacts.
"""
NAMES = {'E2': 40, 'A2': 45, 'C3': 48, 'E3': 52, 'G3': 55, 'G#3': 56, 'A3': 57, 'B3': 59, 'C4': 60, 'D4': 62,
         'E4': 64, 'F4': 65, 'G4': 67, 'G#4': 68, 'A4': 69, 'B4': 71, 'C5': 72, 'D5': 74, 'D#5': 75, 'E5': 76}

# ---- section A: Für Elise, in sixteenths
UA = 0.23
FE = [('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
      ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('G#4', 1), ('B4', 1), ('C5', 3), ('E4', 1),
      ('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
      ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('C5', 1), ('B4', 1), ('A4', 4)]
FE_BASS = {8: ['A2', 'E3', 'A3'], 12: ['E2', 'E3', 'G#3'], 16: ['A2', 'E3', 'A3'],
           26: ['A2', 'E3', 'A3'], 30: ['E2', 'E3', 'G#3'], 34: ['A2', 'E3', 'A3']}
# mechanism for each note: tile = rolling LED shelf, pad = round pad, block = synth block
FE_MECH = (['tile'] * 5 + ['pad'] * 3 + ['block'] + ['pad'] * 3 + ['block'] + ['pad'] * 3 + ['block'] + ['pad']
           + ['tile'] * 5 + ['pad'] * 3 + ['block'] + ['pad'] * 3 + ['block'] + ['pad'] * 3 + ['launchpad'])

# ---- section B: Ode to Joy, in quarter notes (C major)
UB = 0.30
OTJ = [('E4', 1), ('E4', 1), ('F4', 1), ('G4', 1), ('G4', 1), ('F4', 1), ('E4', 1), ('D4', 1),
       ('C4', 1), ('C4', 1), ('D4', 1), ('E4', 1), ('E4', 1.5), ('D4', 0.5), ('D4', 2),
       ('E4', 1), ('E4', 1), ('F4', 1), ('G4', 1), ('G4', 1), ('F4', 1), ('E4', 1), ('D4', 1),
       ('C4', 1), ('C4', 1), ('D4', 1), ('E4', 1), ('D4', 1.5), ('C4', 0.5), ('C4', 2)]
OTJ_MECH = (['tile'] * 8 + ['pad', 'pad2', 'pad', 'pad', 'block', 'pad', 'block']
            + ['pad', 'pad2', 'pad', 'pad', 'pad2', 'pad', 'pad', 'pad'] + ['tile'] * 4 + ['pad', 'pad', 'spring'])
# simple accompaniment (bass, chord) per bar of four quarters
OTJ_CHORDS = ['C', 'G', 'C', 'G', 'C', 'G', 'C', 'G7C']

START = 0.30          # first contact
GAP_BEATS = 4         # gap 1: one bar of Ode to Joy's tempo
CUP_REST_BEATS = 4    # the ball sits in the cup: 2 beats while the last note rings + 2 silent beats
FLIGHT_BEATS = 4      # one bar in the air
REVEAL_START, REVEAL_LEN, HOLD = 1.3, 2.6, 1.0


def notes():
    """All contacts: dict(i, k, t, midi, dur, mech, song). The last one (bigdrum) is the tag, not a melody note."""
    out, t = [], START
    for k, ((n, u), m) in enumerate(zip(FE, FE_MECH)):
        out.append(dict(i=len(out), k=k, t=t, midi=NAMES[n], dur=u * UA, mech=m, song='A'))
        t += u * UA
    t_end_a = t                                   # the last note of section A has rung out
    t = t_end_a + GAP_BEATS * UB
    for k, ((n, u), m) in enumerate(zip(OTJ, OTJ_MECH)):
        out.append(dict(i=len(out), k=k, t=t, midi=NAMES[n], dur=u * UB, mech=m, song='B'))
        t += u * UB
    last = out[-1]
    launch = last['t'] + CUP_REST_BEATS * UB
    out.append(dict(i=len(out), k=len(OTJ), t=launch + FLIGHT_BEATS * UB, midi=NAMES['C5'], dur=2.0,
                    mech='bigdrum', song='B', launch=launch))
    return out


def gap1():
    n = notes()
    a = [h for h in n if h['song'] == 'A']
    t_end_a = a[-1]['t'] + a[-1]['dur']
    return dict(t0=a[-1]['t'], end_a=t_end_a, beats=[t_end_a + j * UB for j in range(GAP_BEATS)],
                switch=t_end_a + (GAP_BEATS - 1) * UB, t1=t_end_a + GAP_BEATS * UB)


def accompaniment():
    """(t, midi, dur, voice) events with no ball contact."""
    out = []
    n = notes()
    for h in n:
        if h['song'] == 'A' and h['k'] in FE_BASS:
            for j, nm in enumerate(FE_BASS[h['k']]):
                out.append((h['t'] + j * UA, NAMES[nm], 0.9, 'piano'))
    b = [h for h in n if h['song'] == 'B']
    bar_t = b[0]['t']
    roots = {'C': ('C3', ['C4', 'E4', 'G4']), 'G': ('G3', ['B3', 'D4', 'G4'])}
    for ci, ch in enumerate(OTJ_CHORDS):
        if ch == 'G7C':
            for (rt, tri), dt in ((roots['G'], 0.0), (roots['C'], 2 * UB)):
                out.append((bar_t + dt, NAMES[rt], 0.9, 'bass'))
                for m in tri:
                    out.append((bar_t + dt, NAMES[m], 0.9, 'pad'))
        else:
            rt, tri = roots[ch]
            out.append((bar_t, NAMES[rt], 4 * UB * 0.9, 'bass'))
            out.append((bar_t + 2 * UB, NAMES[rt] + 7, 2 * UB * 0.9, 'bass'))
            for m in tri:
                out.append((bar_t, NAMES[m], 4 * UB, 'pad'))
        bar_t += 4 * UB
        if ci == 6:
            pass
    # the accompaniment pauses during the fermata; the final chord comes with the big drum
    return out


def t_final():
    return notes()[-1]['t']


def total_seconds():
    return t_final() + REVEAL_START + REVEAL_LEN + HOLD
