"""The score and hit timeline shared by the picture (short.py) and the sound (audio.py).

Melody: Beethoven, "Für Elise" (WoO 59, 1810), opening A section, right-hand line.
The composition is in the public domain; the performance and sound are generated here.

Every note is one hit: the ball lands on one neon bar at exactly that note's time.
Bars sit on a "piano roll" on the wall: x by pitch (higher = right), z by time (later = lower).
"""
UNIT = 0.23          # seconds per sixteenth note
INTRO = 0.55         # free fall before the first hit
DESCENT = 0.62       # metres the machine descends per second of music
X_PER_SEMI = 0.085  # metres of x per semitone
X_CENTER = 69        # MIDI pitch that sits at x = 0

NAMES = {'C4': 60, 'E4': 64, 'G#4': 68, 'A4': 69, 'B4': 71, 'C5': 72, 'D5': 74, 'D#5': 75, 'E5': 76}

_A = [('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
      ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('G#4', 1), ('B4', 1), ('C5', 3), ('E4', 1)]
_B = [('E5', 1), ('D#5', 1), ('E5', 1), ('D#5', 1), ('E5', 1), ('B4', 1), ('D5', 1), ('C5', 1),
      ('A4', 3), ('C4', 1), ('E4', 1), ('A4', 1), ('B4', 3), ('E4', 1), ('C5', 1), ('B4', 1), ('A4', 6)]
MELODY = _A + _B

# pitch class -> neon colour name (same pitch always the same colour)
PC_COLOUR = {0: 'amber', 2: 'lime', 3: 'violet', 4: 'cyan', 8: 'violet', 9: 'magenta', 11: 'lime'}


def hits():
    """List of dicts: time (s), midi pitch, duration (s), x, z of the bar top the ball touches."""
    out, t = [], INTRO
    for name, units in MELODY:
        p = NAMES[name]
        out.append(dict(t=t, midi=p, dur=units * UNIT, x=(p - X_CENTER) * X_PER_SEMI, z=-DESCENT * t))
        t += units * UNIT
    return out


def total_seconds(tail=2.2):
    h = hits()
    return h[-1]['t'] + tail
