"""Test song for the long-form engine: an ORIGINAL anime-opening-style piece ("anison" feel), written here.

Not a transcription of any existing song. D minor, 152 bpm, eighth notes as the unit.
Three sections joined by the engine's one-bar gaps: intro (hook) -> verse + pre-chorus -> chorus.
The pre-chorus climbs and stops on a held E5; the launch gap is the "kime" break before the chorus.
"""
import songs6 as base
from songs6 import GAP_BEATS, START, midi  # noqa: F401

U8, BEAT = 0.197, 0.395

INTRO = [('D5', 2), ('D5', 1), ('C5', 1), ('A4', 2), ('G4', 1), ('A4', 1),
         ('D5', 3), ('E5', 1), ('F5', 2), ('E5', 1), ('C5', 1),
         ('D5', 2), ('A4', 2), ('C5', 1), ('A4', 1), ('G4', 2),
         ('A4', 8)]
VERSE = [('D4', 1), ('F4', 1), ('G4', 1), ('A4', 1), ('A4', 2), ('G4', 1), ('A4', 1),
         ('C5', 2), ('A4', 1), ('G4', 1), ('F4', 2), ('E4', 2),
         ('D4', 1), ('F4', 1), ('G4', 1), ('A4', 1), ('C5', 2), ('D5', 1), ('C5', 1),
         ('A4', 4), ('G4', 2), ('A4', 2)]
PRE = [('F4', 1), ('G4', 1), ('A4', 2), ('A#4', 1), ('A4', 1), ('G4', 2),
       ('A4', 1), ('A#4', 1), ('C5', 2), ('D5', 1), ('C5', 1), ('A#4', 2),
       ('C5', 1), ('D5', 1), ('E5', 2), ('F5', 1), ('E5', 1), ('D5', 1), ('E5', 1),
       ('E5', 8)]
CHORUS = [('A4', 1), ('C5', 1), ('D5', 2), ('D5', 1), ('E5', 1), ('F5', 2),
          ('E5', 1), ('D5', 1), ('C5', 2), ('D5', 2), ('A4', 2),
          ('A4', 1), ('C5', 1), ('D5', 2), ('F5', 1), ('G5', 1), ('A5', 2),
          ('G5', 2), ('F5', 1), ('E5', 1), ('D5', 4),
          ('A#4', 1), ('C5', 1), ('D5', 2), ('D5', 1), ('E5', 1), ('F5', 2),
          ('G5', 2), ('F5', 1), ('E5', 1), ('E5', 2), ('C5', 2),
          ('D5', 1), ('E5', 1), ('F5', 2), ('E5', 1), ('D5', 1), ('C5', 1), ('A4', 1),
          ('D5', 8)]

COMMON = dict(composer='original (this repository)', unit=U8, beat=BEAT, drone=('D2', 'A2'))
SONGS = [
    dict(COMMON, key='intro', title='Intro', centre=74, notes=INTRO,
         palette=dict(fast='bell', normal='bell', long='cymbal'), gap_in=None,
         chords=['Dm', 'C', 'Bb', 'A']),
    dict(COMMON, key='verse', title='Verse + pre-chorus', centre=67, notes=VERSE + PRE,
         palette=dict(fast='tile', normal='pad', long='block'), gap_in='chute',
         chords=['Dm', 'C', 'Dm', 'A', 'Bb', 'Bb', 'C', 'A']),
    dict(COMMON, key='chorus', title='Chorus', centre=76, notes=CHORUS,
         palette=dict(fast='tile', normal='pad', long='cymbal'), gap_in='launch',
         chords=['Bb', 'C', 'Am', 'Dm', 'Bb', 'C', 'A', 'Dm']),
]
FINAL_NOTE = 'D5'
DRUMS = True          # accompaniment: a rock beat and bass under the songs (not in the gaps)
FINAL_REST_BEATS, FINAL_FLIGHT_BEATS, OUTRO = base.FINAL_REST_BEATS, base.FINAL_FLIGHT_BEATS, base.OUTRO


def assign(song):
    return base.assign(song)


def timeline():
    return base.timeline(SONGS, FINAL_NOTE)


def total_seconds():
    return base.total_seconds(SONGS, FINAL_NOTE)
