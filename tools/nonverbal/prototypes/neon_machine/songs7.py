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

ORDER = [('canon', 1680, 'baroque'), ('toc', 1704, 'baroque'), ('tm', 1783, 'classical'), ('ekn', 1787, 'classical'),
         ('b5', 1808, 'beethoven'), ('fe', 1810, 'beethoven'), ('otj', 1824, 'beethoven'), ('mk', 1876, 'romantic')]
GAPS_IN = [None, 'chute', 'rail', 'launch', 'chute', 'rail', 'launch', 'chute']
COMPOSER = {'canon': 'Johann Pachelbel', 'toc': 'J. S. Bach', 'tm': 'W. A. Mozart', 'ekn': 'W. A. Mozart',
            'b5': 'L. van Beethoven', 'fe': 'L. van Beethoven', 'otj': 'L. van Beethoven', 'mk': 'Edvard Grieg'}
SONGS = []
for (key, year, era), gap in zip(ORDER, GAPS_IN):
    s = dict(mk if key == 'mk' else by[key])
    s.update(year=year, era=era, gap_in=gap, composer_name=COMPOSER[key])
    if key == 'canon':
        s['unit'] = 0.17          # a livelier opening: the famous line at a walking pace
    SONGS.append(s)
SONGS[0]['title'] = 'Canon in D'
# notation: clef, bar length and pickup (in the song's duration units); None = no bar lines (free rhythm)
NOTATION = {'canon': ('treble', 8, 0), 'toc': ('treble', None, 0), 'tm': ('treble', 8, 4), 'ekn': ('treble', 8, 0),
            'b5': ('treble', None, 0), 'fe': ('treble', 6, 2), 'otj': ('treble', 4, 0), 'mk': ('treble', 8, 0)}
KEYSIG = {'canon': 2, 'toc': -1, 'tm': 0, 'ekn': 1, 'b5': -3, 'fe': 0, 'otj': 0, 'mk': 0}   # sharps (+) / flats (-)
TIMESIG = {'canon': (4, 4), 'tm': (2, 4), 'ekn': (4, 4), 'fe': (3, 8), 'otj': (4, 4), 'mk': (4, 4)}
for s_ in SONGS:
    s_['clef'], s_['bar_units'], s_['pickup_units'] = NOTATION[s_['key']]
    s_['keysig'] = KEYSIG[s_['key']]
    s_['timesig'] = TIMESIG.get(s_['key'])
FINAL_NOTE = 'A4'
ERA = {
    'baroque': dict(wall=(0.84, 0.76, 0.62), fix=(0.30, 0.17, 0.08), fix_metal=0.2, neon=['amber', 'red', 'amber', 'white']),
    'classical': dict(wall=(0.86, 0.87, 0.89), fix=(0.10, 0.13, 0.22), fix_metal=0.4, neon=['cyan', 'violet', 'lime', 'magenta']),
    'beethoven': dict(wall=(0.34, 0.36, 0.42), fix=(0.55, 0.56, 0.6), fix_metal=0.9, neon=['cyan', 'magenta', 'violet', 'lime']),
    'romantic': dict(wall=(0.30, 0.06, 0.08), fix=(0.62, 0.48, 0.22), fix_metal=1.0, neon=['red', 'amber', 'magenta', 'white']),
}
START, OUTRO = base.START, base.OUTRO + 4.0   # longer outro: the camera rises back through all the pages


def assign(song):
    return base.assign(song)


def timeline():
    return base.timeline(SONGS, FINAL_NOTE)


def total_seconds():
    return base.total_seconds(SONGS, FINAL_NOTE) + 4.0
