"""v4 timeline: a two-song medley with silent gaps ("ma"), in the style of House of Marble.

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
            + ['pad', 'pad2', 'pad', 'pad', 'pad2', 'pad', 'pad', 'pad'] + ['tile'] * 4 + ['pad', 'spring', 'bigdrum'])
# simple accompaniment (bass, chord) per bar of four quarters
OTJ_CHORDS = ['C', 'G', 'C', 'G', 'C', 'G', 'C', 'G7C']

START = 0.30          # first contact
GAP1 = 2.1            # silent rail + switch
SWITCH_AT = 1.55      # seconds into gap 1 when the switch clicks
FERMATA = 1.05        # extra air time before the final note
REVEAL_START, REVEAL_LEN, HOLD = 1.3, 2.6, 1.0


def notes():
    """All melody contacts: dict(i, t, midi, dur, mech, song)."""
    out, t = [], START
    for k, ((n, u), m) in enumerate(zip(FE, FE_MECH)):
        out.append(dict(i=len(out), k=k, t=t, midi=NAMES[n], dur=u * UA, mech=m, song='A'))
        t += u * UA
    t_last_a = out[-1]['t']
    t = t_last_a + GAP1
    for k, ((n, u), m) in enumerate(zip(OTJ, OTJ_MECH)):
        if m == 'bigdrum':
            t += FERMATA
        out.append(dict(i=len(out), k=k, t=t, midi=NAMES[n], dur=u * UB, mech=m, song='B'))
        t += u * UB
    return out


def gap1():
    n = notes()
    a_last = [h for h in n if h['song'] == 'A'][-1]
    return dict(t0=a_last['t'], switch=a_last['t'] + SWITCH_AT, t1=a_last['t'] + GAP1)


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
