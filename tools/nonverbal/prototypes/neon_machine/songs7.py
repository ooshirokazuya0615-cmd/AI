"""'300 Years of Music, One Marble' (v7): the medley in the order the pieces were written.

Each piece belongs to an era, and each era has its own room (wall colour, fixture finish, neon palette).
Mountain King is played three times, faster each time (Grieg's own accelerando), and closes the film.
year = year of composition (Pachelbel's Canon is undated; c. 1680-1706 is usual).
"""
import songs6 as base
from songs6 import midi  # noqa: F401

by = {s['key']: dict(s) for s in base.SONGS}
mk = dict(by['mk'])
phrase = mk['notes']
mk['notes'] = phrase + [(n, u * 0.82) for n, u in phrase] + [(n, u * 0.66) for n, u in phrase]
mk['nunits'] = [u for _, u in phrase] * 3          # notated values (the accelerando changes time, not notation)
mk['palette'] = dict(fast='bumper', normal='pad', long='cymbal')
# a breath before the last, fastest pass: the marble flies past the funnel and is rescued (film8, RESCUE);
# the notes are untouched, the music only waits
mk['gp'] = {2 * len(phrase) - 1: 2.2}

ORDER = [('canon', 1680, 'baroque'), ('toc', 1704, 'baroque'), ('tm', 1783, 'classical'), ('ekn', 1787, 'classical'),
         ('b5', 1808, 'beethoven'), ('fe', 1810, 'beethoven'), ('otj', 1824, 'beethoven'), ('mk', 1876, 'romantic')]
GAPS_IN = [None, 'chute', 'rail', 'launch', 'chute', 'rail', 'launch', 'chute']
COMPOSER = {'canon': 'Johann Pachelbel', 'toc': 'Johann Sebastian Bach', 'tm': 'Wolfgang Amadeus Mozart',
            'ekn': 'Wolfgang Amadeus Mozart', 'b5': 'Ludwig van Beethoven', 'fe': 'Ludwig van Beethoven',
            'otj': 'Ludwig van Beethoven', 'mk': 'Edvard Grieg'}
# the year as shown on the answer card, where the date is not certain (Canon is undated, c. 1680-1706;
# BWV 565's date and even its authorship are debated)
YEAR_LABEL = {'canon': 'c. 1680', 'toc': 'c. 1704'}
# the Pythagora-switch machine that carries the marble into each piece (gadgets.py), and how long the music
# rests for it (after the last note has rung)
MACHINE = {'toc': ['stairs'], 'tm': ['dominoes', 'bells'], 'ekn': ['loop', 'jump'], 'b5': ['plinko', 'tilt'],
           'fe': ['spiral', 'helix'], 'otj': ['jump', 'xylo'], 'mk': ['helix', 'loop', 'dominoes']}
# lengths set from each machine's own pace with its rails at about 8-9 degrees (measured with MACH_PACE=1)
INTERLUDE = {'toc': 4.0, 'tm': 6.4, 'ekn': 4.6, 'b5': 8.3, 'fe': 7.3, 'otj': 6.4, 'mk': 8.6}   # tm, ekn trimmed: dead rolling
SONGS = []
for (key, year, era), gap in zip(ORDER, GAPS_IN):
    s = dict(mk if key == 'mk' else by[key])
    s.update(year=year, era=era, gap_in=gap, composer_name=COMPOSER[key], year_label=YEAR_LABEL.get(key, str(year)))
    if key in MACHINE:
        s.update(machine=MACHINE[key], interlude=INTERLUDE[key])
    SONGS.append(s)
SONGS[0]['title'] = 'Canon in D'
SONGS[1]['title'] = 'Toccata and Fugue in D minor'      # "Toccata in D minor" alone is also BWV 913
# notation: clef, bar length and pickup (in the song's duration units); None = no bar lines (free rhythm)
NOTATION = {'canon': ('treble', 16, 0), 'toc': ('treble', None, 0), 'tm': ('treble', 8, 4), 'ekn': ('treble', 8, 0),
            'b5': ('treble', None, 0), 'fe': ('treble', 6, 2), 'otj': ('treble', 4, 0), 'mk': ('treble', 8, 0)}
KEYSIG = {'canon': 2, 'toc': -1, 'tm': 0, 'ekn': 1, 'b5': -3, 'fe': 0, 'otj': 0, 'mk': 0}   # sharps (+) / flats (-)
# fermatas, by note index, where the Mutopia editions have them (Toccata: on the held A and on the D that
# closes each phrase; Fifth: on the E-flat and the tied D)
FERMATA = {'toc': (2, 8, 11, 15), 'b5': (3, 7)}
TIMESIG = {'canon': (4, 4), 'tm': (2, 4), 'ekn': (4, 4), 'fe': (3, 8), 'otj': (4, 4), 'mk': (4, 4)}
# accompaniment, only where it is certain (checked against the same Mutopia editions):
#   canon: the ground bass; tm: the left hand of the theme; fe: the left-hand arpeggios under the long notes;
#   otj: the bass part (moved to C);
#   unison pieces (the orchestra/organ plays the line in octaves): the melody an octave lower
ACCOMP = {
    'canon': dict(bass=[('D3', 4), ('A2', 4), ('B2', 4), ('F#2', 4), ('G2', 4), ('D2', 4), ('G2', 4), ('A2', 4)] * 2 + [('D2', 16)]),
    'fe': dict(arpeggio=True),
    'otj': dict(bass=[('C3', 1), ('C3', 1), ('C3', 1), ('C3', 1), ('A2', 1.5), ('B2', 0.5), ('C3', 1), ('G2', 1),
                      ('E3', 1), ('E3', 1), ('D3', 1), ('C3', 1), ('G2', 1.5), ('G2', 0.5), ('G2', 2),
                      ('C3', 1), ('C3', 1), ('C3', 1), ('C3', 1), ('A2', 1.5), ('B2', 0.5), ('C3', 1), ('G2', 1),
                      ('E3', 1), ('E3', 1), ('D3', 1), ('C3', 1), ('G2', 1), ('G2', 1), ('C2', 2)]),
    # tm: Mozart's left hand under the theme (8ths: bass note, then the chord; None = the pickup rest)
    'tm': dict(staccato=True, bass=[(None, 4)]
               + [('A3', 2), ('C4+E4', 2), ('C4+E4', 2), ('C4+E4', 2)] * 2
               + [('A3', 2), ('C4+E4', 2), ('A3', 2), ('C4+E4', 2)]
               + [('A3', 2), ('C4+E4', 2), ('C4+E4', 2), ('C4+E4', 2)]
               + [('E3', 2), ('B3+E4', 2), ('B3+E4', 2), ('B3+E4', 2)] * 2
               + [('E3', 2), ('B3+E4', 2), ('B2', 2), ('B3', 2), ('E3', 4)]),
    'ekn': dict(octave=True), 'b5': dict(octave=True), 'toc': dict(octave=True), 'mk': dict(octave=True),
}
for s_ in SONGS:
    s_['accomp'] = ACCOMP.get(s_['key'], {})
    s_['clef'], s_['bar_units'], s_['pickup_units'] = NOTATION[s_['key']]
    s_['keysig'] = KEYSIG[s_['key']]
    s_['timesig'] = TIMESIG.get(s_['key'])
    s_['fermata'] = FERMATA.get(s_['key'], ())
    s_['note_value'] = NOTE_VALUE.get(s_['key'], {})
# the written value of a note (in the piece's units) where it differs from the time it takes: in Eine kleine
# Nachtmusik the D6 and D5 are quarters followed by a quarter rest (violin I: "g d g b d4 r"), so they take 4
# units of time but are engraved as quarters, with filled heads
NOTE_VALUE = {'ekn': {8: 2, 17: 2}}
FINAL_NOTE = 'A4'
ERA = {
    'baroque': dict(wall=(0.84, 0.76, 0.62), fix=(0.30, 0.17, 0.08), fix_metal=0.2, neon=['amber', 'red', 'amber', 'white']),
    'classical': dict(wall=(0.86, 0.87, 0.89), fix=(0.10, 0.13, 0.22), fix_metal=0.4, neon=['cyan', 'violet', 'lime', 'magenta']),
    'beethoven': dict(wall=(0.34, 0.36, 0.42), fix=(0.55, 0.56, 0.6), fix_metal=0.9, neon=['cyan', 'magenta', 'violet', 'lime']),
    'romantic': dict(wall=(0.30, 0.06, 0.08), fix=(0.62, 0.48, 0.22), fix_metal=1.0, neon=['red', 'amber', 'magenta', 'white']),
}
# the opening before the first note: room tone, a pendulum on the page counting in at the first piece's tempo,
# then a gate opens and the marble rolls down onto the first note (nothing starts out of silence)
base.START = 2.5                      # a one-bar count-in: four ticks
START, OUTRO = base.START, base.OUTRO + 4.0   # longer outro: the camera rises back through all the pages


_base_assign = base.assign


def assign(song):
    # every sounded note gets a head of its own, as engraved: no second bounce on the same head ('again')
    return ['pad' if m == 'again' else m for m in _base_assign(song)]


base.assign = assign                  # base.timeline looks it up in its own module


def timeline():
    return base.timeline(SONGS, FINAL_NOTE)


def total_seconds():
    return base.total_seconds(SONGS, FINAL_NOTE) + 4.0
