"""v2 timeline: melody, left-hand bass (played by dominoes), the paddle save, the tag arpeggio and the reveal.

Melody and bass: Beethoven, "Für Elise" (WoO 59, 1810; published 1867), opening A section.
The composition is public domain; performance and sound are generated here.

Kinds of melody hit:
  bar    - a neon bar on the wall
  lever  - a long note: the bar tips and starts a row of three dominoes (the left-hand arpeggio)
  paddle - the pickup into the second phrase: the blue character bats the ball back up
  drum   - the last note: the big drum
"""
UNIT = 0.23          # seconds per sixteenth note
INTRO = 0.55         # the ball pops off the yellow character's head and lands on the first bar
DESCENT = 0.62       # metres the machine descends per second of music
X_PER_SEMI = 0.085   # metres of x per semitone
X_CENTER = 69        # MIDI pitch at x = 0

NAMES = {'E2': 40, 'A2': 45, 'E3': 52, 'G#3': 56, 'A3': 57, 'C4': 60, 'E4': 64, 'G#4': 68, 'A4': 69,
         'B4': 71, 'C5': 72, 'D5': 74, 'D#5': 75, 'E5': 76, 'A5': 81}

_A = [('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
      ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('G#4', 1), ('B4', 1), ('C5', 3), ('E4', 1)]
_B = [('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
      ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('C5', 1), ('B4', 1), ('A4', 6)]
MELODY = _A + _B
PADDLE_INDEX = len(_A) - 1

# left-hand arpeggio under each long note
BASS_UNDER = {'A4': ['A2', 'E3', 'A3'], 'B4': ['E2', 'E3', 'G#3'], 'C5': ['A2', 'E3', 'A3']}

PC_COLOUR = {0: 'amber', 2: 'lime', 3: 'violet', 4: 'cyan', 8: 'violet', 9: 'magenta', 11: 'lime'}

TAG = ['A4', 'C5', 'E5', 'A5']   # four little balls ring four bells after the drum
TAG_DELAY, TAG_STEP = 0.34, 0.15
CONFETTI_AT = 1.05               # seconds after the drum
REVEAL_START, REVEAL_LEN, HOLD = 1.25, 2.6, 0.9


def melody():
    out, t = [], INTRO
    for i, (name, units) in enumerate(MELODY):
        p = NAMES[name]
        if i == len(MELODY) - 1:
            kind = 'drum'
        elif i == PADDLE_INDEX:
            kind = 'paddle'
        elif units == 3:
            kind = 'lever'
        else:
            kind = 'bar'
        out.append(dict(i=i, t=t, midi=p, name=name, units=units, dur=units * UNIT, kind=kind,
                        x=(p - X_CENTER) * X_PER_SEMI, z=-DESCENT * t))
        t += units * UNIT
    return out


def bass():
    out = []
    for h in melody():
        if h['kind'] == 'lever':
            for k, n in enumerate(BASS_UNDER[h['name']]):
                out.append(dict(t=h['t'] + k * UNIT, midi=NAMES[n], group=h['i'], k=k))
    return out


def tag():
    t0 = melody()[-1]['t']
    return [dict(t=t0 + TAG_DELAY + k * TAG_STEP, midi=NAMES[n], k=k) for k, n in enumerate(TAG)]


def t_last():
    return melody()[-1]['t']


def total_seconds():
    return t_last() + REVEAL_START + REVEAL_LEN + HOLD
