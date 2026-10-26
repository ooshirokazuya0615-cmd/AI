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
# a breath before each faster pass: time for the marble's ride back to the start of the next line (film8:
# a line turns only where that ride can be followed), and before the last, fastest pass the marble flies
# past the funnel and is rescued (film8, RESCUE); the notes are untouched, the music only waits
mk['gp'] = {len(phrase) - 1: 0.75, 2 * len(phrase) - 1: 2.2}

# the twelve pieces added for the 20-piece film (2026-10-25), each melody transcribed note by note from a
# Mutopia edition (pieces20.json keeps the source file, bars and licence of each; see the music ledger)
import json as _json  # noqa: E402
import os as _os  # noqa: E402
_P20 = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'pieces20.json')
NEW_PIECES = []
if _os.path.exists(_P20):                # (until it exists, the film is the eight-piece version)
    with open(_P20) as _f:
        NEW_PIECES = _json.load(_f)
for p_ in NEW_PIECES:
    ms_ = sorted(midi(n) for n, _ in p_['notes'])
    by[p_['key']] = dict(key=p_['key'], title=p_['title'], composer=p_['composer_name'], unit=p_['unit'], beat=p_['beat'],
                         centre=ms_[len(ms_) // 2], notes=[tuple(x) for x in p_['notes']],
                         palette=dict(fast='tile', normal='pad', long='block'), drone=tuple(p_['drone']), gap_in='rail')

ORDER = [('canon', 1680, 'baroque'), ('toc', 1704, 'baroque'), ('minuet', 1725, 'baroque'), ('spring', 1725, 'baroque'),
         ('hall', 1741, 'baroque'),
         ('tm', 1783, 'classical'), ('ekn', 1787, 'classical'), ('k545', 1788, 'classical'),
         ('moon', 1801, 'beethoven'), ('b5', 1808, 'beethoven'), ('fe', 1810, 'beethoven'), ('march', 1818, 'beethoven'),
         ('otj', 1824, 'beethoven'),
         ('noct', 1832, 'romantic'), ('wed', 1842, 'romantic'), ('brin', 1853, 'romantic'), ('danube', 1866, 'romantic'),
         ('lull', 1868, 'romantic'), ('carmen', 1875, 'romantic'), ('mk', 1875, 'romantic')]
ORDER = [o_ for o_ in ORDER if o_[0] in by or o_[0] == 'mk']
# (years of composition, as for every piece: Peer Gynt's music was written in 1875 and first heard in 1876)
GAPS_IN = [None] + ['chute', 'rail', 'launch'] * 6 + ['chute']
COMPOSER = {'canon': 'Johann Pachelbel', 'toc': 'Johann Sebastian Bach', 'tm': 'Wolfgang Amadeus Mozart',
            'ekn': 'Wolfgang Amadeus Mozart', 'b5': 'Ludwig van Beethoven', 'fe': 'Ludwig van Beethoven',
            'otj': 'Ludwig van Beethoven', 'mk': 'Edvard Grieg'}
COMPOSER.update({p_['key']: p_['composer_name'] for p_ in NEW_PIECES})
# the year as shown on the answer card, where the date is not certain (Canon is undated, c. 1680-1706;
# BWV 565's date and even its authorship are debated)
YEAR_LABEL = {'canon': 'c. 1680', 'toc': 'c. 1704'}
YEAR_LABEL.update({p_['key']: p_['year_label'] for p_ in NEW_PIECES if p_.get('year_label')})
# between pieces the marble takes a glass tube to the next page, as at a line break, and the next piece
# comes in like the next number of a medley: the last note rings (at most 0.8 s, then it rings on under the
# new piece), and the new piece starts about a second later on its own beat (a whole number of its beats,
# and never less than a second's ride through the tube). No machines between pieces: they held the music up
# (gadgets.py and MACHINE still work, for a film that wants them)
MACHINE = {}


def medley_gap(song, prev):
    """The rest before a piece (after the previous one's last note has rung, at most 0.8 s)."""
    b = song['beat']
    while b > 1.3:                        # a slow beat (the Moonlight's bar-long one): count in halves
        b /= 2
    n = max(1, round(1.0 / b))
    while min(prev['notes'][-1][1] * prev['unit'], 0.8) + n * b - 0.34 < 1.0:    # the ride needs a second
        n += 1
    return n * b
SONGS = []
for (key, year, era), gap in zip(ORDER, GAPS_IN):
    s = dict(mk if key == 'mk' else by[key])
    s.update(year=year, era=era, gap_in=gap, composer_name=COMPOSER[key], year_label=YEAR_LABEL.get(key, str(year)))
    if key in MACHINE:
        s.update(machine=MACHINE[key])
    if SONGS:
        s.update(interlude=medley_gap(s, SONGS[-1]))
    SONGS.append(s)
SONGS[0]['title'] = 'Canon in D'
SONGS[1]['title'] = 'Toccata and Fugue in D minor'      # "Toccata in D minor" alone is also BWV 913
# notation: clef, bar length and pickup (in the song's duration units); None = no bar lines (free rhythm)
NOTATION = {'canon': ('treble', 16, 0), 'toc': ('treble', None, 0), 'tm': ('treble', 8, 4), 'ekn': ('treble', 8, 0),
            'b5': ('treble', None, 0), 'fe': ('treble', 6, 2), 'otj': ('treble', 4, 0), 'mk': ('treble', 8, 0)}
KEYSIG = {'canon': 2, 'toc': -1, 'tm': 0, 'ekn': 1, 'b5': -3, 'fe': 0, 'otj': 0, 'mk': 0}   # sharps (+) / flats (-)
for p_ in NEW_PIECES:
    n_ = p_['notation']
    NOTATION[p_['key']] = (n_['clef'], n_['bar_units'], n_['pickup_units'])
    KEYSIG[p_['key']] = p_['keysig']
# fermatas, by note index, where the Mutopia editions have them (Toccata: on the held A and on the D that
# closes each phrase; Fifth: on the E-flat and the tied D)
# the written value of a note (in the piece's units) where it differs from the time it takes: in Eine kleine
# Nachtmusik the D6 and D5 are quarters followed by a quarter rest (violin I: "g d g b d4 r"), so they take 4
# units of time but are engraved as quarters, with filled heads
# The Fifth has no bar lines on screen, so its written values are given against a whole note of 8 units (its
# unit is an eighth): the E-flat, the tied D and the C are half notes ("ef2", "d2 ~ | d", "c2 ~ | c4"), drawn
# as one open head each
NOTE_VALUE = {'ekn': {0: 2, 2: 2, 8: 2, 9: 2, 11: 2, 17: 2}, 'b5': {3: 4, 7: 4, 17: 4},
              'fe': {8: 2, 12: 2, 16: 2, 26: 2, 30: 2}}
# (Eine kleine's G and C are quarters followed by an eighth rest, "g4 r8 d8"; Für Elise's long A, B and C are
#  eighths followed by a sixteenth rest, "a8 r16": they take a dotted value's time but are written plain, so
#  they get no augmentation dot)
WHOLE_UNITS = {'b5': 8}
# where a piece's line breaks, when the general rule would break it on a short note (the Fifth: after the
# held D, so the marble sits on the fermata and then has a ride of about a second to the next line)
BREAK_AFTER = {'b5': (7,)}
# where the camera eases back for a moment (note indices): Für Elise, as the opening motif returns, to show
# the fireflies gathered over the page
BREATH = {'fe': (17, 30)}
# lit-note colours of a piece's own (else its era's): Für Elise in white and pink, so its lime marble stands alone
NEON_OF = {'fe': ['white', 'magenta', 'white', 'cyan'], 'otj': ['magenta', 'amber', 'violet', 'red']}   # Ode: no cyan
                                                                                                        # (its marble is teal)
# a piece framed a little wider than the rest (Für Elise: a gentler pan for a gentle piece, and the swarm in view)
FRAME_ZOOM = {'fe': 1.2}
# how far below its row a line's return tube runs (Ode to Joy: under the dancers' pedestals, not through them)
TUBE_DEPTH = {'otj': 0.57}
FERMATA = {'toc': (2, 8, 11, 15), 'b5': (3, 7)}
TIMESIG = {'canon': (4, 4), 'tm': (2, 4), 'ekn': (4, 4), 'fe': (3, 8), 'otj': (4, 4), 'mk': (4, 4)}
for p_ in NEW_PIECES:
    TIMESIG[p_['key']] = tuple(p_['timesig'])
    if p_.get('note_value'):
        NOTE_VALUE[p_['key']] = {int(k): v for k, v in p_['note_value'].items()}
# accompaniment, only where it is certain (checked against the same Mutopia editions):
#   canon: the ground bass; tm: the left hand of the theme; fe: the left-hand arpeggios under the long notes;
#   otj: the bass part (moved to C);
#   unison pieces (the orchestra/organ plays the line in octaves): the melody an octave lower
# the film is led in by the Canon's ground bass alone: its last six notes (B F# G D G A, INTRO_BEATS) cadence
# onto the D where the melody enters, so the music is there from the first frame, under the opening's story
GROUND = [('D3', 4), ('A2', 4), ('B2', 4), ('F#2', 4), ('G2', 4), ('D2', 4), ('G2', 4), ('A2', 4)]
INTRO_BEATS = 6
ACCOMP = {
    'canon': dict(bass=GROUND[-INTRO_BEATS:] + GROUND * 2 + [('D2', 16)],
                  lead=4 * INTRO_BEATS),         # (units before the first melody note: four to a beat)
    'fe': dict(arpeggio=True),
    'otj': dict(bass=[('C3', 1), ('C3', 1), ('C3', 1), ('C3', 1), ('A2', 1.5), ('B2', 0.5), ('C3', 1), ('G2', 1),
                      ('E3', 1), ('E3', 1), ('D3', 1), ('C3', 1), ('G2', 1.5), ('G2', 0.5), ('G2', 2),
                      ('C3', 1), ('C3', 1), ('C3', 1), ('C3', 1), ('A2', 1.5), ('B2', 0.5), ('C3', 1), ('G2', 1),
                      ('E3', 1), ('E3', 1), ('D3', 1), ('C3', 1), ('G2', 1), ('G2', 1), ('C2', 2)],
                ring=0.02),                      # a walking bass: each note gives way to the next
    # tm: Mozart's left hand under the theme (8ths: bass note, then the chord; None = the pickup rest)
    'tm': dict(staccato=True, bass=[(None, 4)]
               + [('A3', 2), ('C4+E4', 2), ('C4+E4', 2), ('C4+E4', 2)] * 2
               + [('A3', 2), ('C4+E4', 2), ('A3', 2), ('C4+E4', 2)]
               + [('A3', 2), ('C4+E4', 2), ('C4+E4', 2), ('C4+E4', 2)]
               + [('E3', 2), ('B3+E4', 2), ('B3+E4', 2), ('B3+E4', 2)] * 2
               + [('E3', 2), ('B3+E4', 2), ('B2', 2), ('B3', 2), ('E3', 4)]),
    'ekn': dict(octave=True), 'b5': dict(octave=True), 'toc': dict(octave=True), 'mk': dict(octave=True),
}
for p_ in NEW_PIECES:                    # the new pieces: the melody doubled an octave below (nothing invented)
    ACCOMP.setdefault(p_['key'], dict(octave=True))
# the flame's colour in each piece (each against its page; shared by film8 and the overlay's recap)
PIECE_COL = {'canon': (0.10, 0.35, 1.0), 'toc': (0.02, 0.62, 0.32), 'tm': (0.30, 0.05, 0.55), 'ekn': (1.0, 0.72, 0.12),
             'b5': (1.0, 0.35, 0.06), 'fe': (0.62, 1.0, 0.15), 'otj': (0.0, 0.24, 0.29), 'mk': (0.15, 0.85, 1.0),
             'minuet': (0.15, 0.75, 1.0), 'spring': (0.55, 1.0, 0.25), 'hall': (1.0, 0.55, 0.15), 'k545': (1.0, 0.40, 0.45),
             'moon': (0.70, 0.85, 1.0), 'march': (1.0, 0.20, 0.15), 'noct': (0.40, 1.0, 0.85), 'wed': (0.20, 0.30, 1.0),
             'brin': (1.0, 0.85, 0.35), 'danube': (1.0, 0.62, 0.20), 'lull': (1.0, 0.55, 0.70), 'carmen': (0.10, 0.85, 0.80)}
for s_ in SONGS:
    s_['accomp'] = ACCOMP.get(s_['key'], {})
    s_['clef'], s_['bar_units'], s_['pickup_units'] = NOTATION[s_['key']]
    s_['keysig'] = KEYSIG[s_['key']]
    s_['timesig'] = TIMESIG.get(s_['key'])
    s_['fermata'] = FERMATA.get(s_['key'], ())
    s_['note_value'] = NOTE_VALUE.get(s_['key'], {})
    s_['whole_units'] = WHOLE_UNITS.get(s_['key'])
    s_['break_after'] = BREAK_AFTER.get(s_['key'], ())
    s_['breath'] = BREATH.get(s_['key'])
    s_['neon'] = NEON_OF.get(s_['key'])
    s_['frame_zoom'] = FRAME_ZOOM.get(s_['key'], 1.0)
    s_['tube_depth'] = TUBE_DEPTH.get(s_['key'], 0.42)
FINAL_NOTE = 'A4'
ERA = {
    'baroque': dict(wall=(0.84, 0.76, 0.62), fix=(0.30, 0.17, 0.08), fix_metal=0.2, neon=['amber', 'red', 'amber', 'white']),
    'classical': dict(wall=(0.86, 0.87, 0.89), fix=(0.10, 0.13, 0.22), fix_metal=0.4, neon=['cyan', 'white', 'lime', 'magenta']),
    'beethoven': dict(wall=(0.34, 0.36, 0.42), fix=(0.55, 0.56, 0.6), fix_metal=0.9, neon=['cyan', 'magenta', 'violet', 'lime']),
    'romantic': dict(wall=(0.30, 0.06, 0.08), fix=(0.62, 0.48, 0.22), fix_metal=1.0, neon=['red', 'amber', 'magenta', 'white']),
}
# the opening before the first note (3.6 s): the ground bass alone, softly; a spark from the candle lights the
# marble, the gate opens and the marble rolls down onto the first note as the melody enters (film8)
base.START = 0.26 + INTRO_BEATS * SONGS[0]['beat']
START, OUTRO = base.START, base.OUTRO + 4.0   # longer outro: the camera rises back through all the pages


_base_assign = base.assign


def assign(song):
    # every sounded note gets a head of its own, as engraved: no second bounce on the same head ('again')
    return ['pad' if m == 'again' else m for m in _base_assign(song)]


base.assign = assign                  # base.timeline looks it up in its own module


def timeline():
    return base.timeline(SONGS, FINAL_NOTE)


# the finale after the drum (seconds from the drum): the 8-colour marble held, the rise back through the
# pages (a stop on each), the pull-back to the whole wall, and the closing card held to the end (shared by
# film8.py, overlay.py and audio6.py so picture, graphics and sound agree)
FINALE = dict(hold=1.8, rise0=3.2, rise1=16.2, wide1=18.4, card=18.9, end=24.5)   # (the rise passes 23 lines)


def total_seconds():
    c, _ = timeline()
    return c[-1]['t'] + FINALE['end']
