"""Find a start orientation + zigzag pattern whose landings play a decent phrase ending B-A-D'."""
import itertools
import numpy as np

# local face -> note (D major): +X B, -X F#, +Y D', -Y D, +Z A, -Z E
FACE_NOTE = {(1, 0, 0): 71, (-1, 0, 0): 66, (0, 1, 0): 74, (0, -1, 0): 62, (0, 0, 1): 69, (0, 0, -1): 64}
NAME = {62: 'D', 64: 'E', 66: 'F#', 69: 'A', 71: 'B', 74: "D'"}
UP = np.array([0, 1, 0])


def rot90(axis):
    a = np.array(axis, float)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + K + K @ K   # sin=1, 1-cos=1


def tip(R, d):
    return np.rint(rot90(np.cross(UP, d)) @ R).astype(int)


def bottom_note(R):
    loc = R.T @ np.array([0, -1, 0])
    return FACE_NOTE[tuple(int(v) for v in np.rint(loc))]


def all_rotations():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            M = np.zeros((3, 3), int)
            for i, (p, s) in enumerate(zip(perm, signs)):
                M[i, p] = s
            if round(np.linalg.det(M)) == 1:
                out.append(M)
    return out


X, Z = np.array([1, 0, 0]), np.array([0, 0, 1])
LAP = [X] * 8 + [Z] * 8 + [-X] * 8 + [-Z]          # tips 1..25


def chord_of(beat):
    if beat < 32: return {67, 71, 74, 66}        # Gmaj7 (bar 7)
    if beat < 36: return {66, 69, 73, 64}        # F#m7 (bar 8)
    if beat < 38: return {64, 67, 71, 74}        # Em7
    if beat < 40: return {69, 73, 76, 67}        # A7
    return {62, 66, 69}


def score(notes):
    s = 0.0
    for a, b in zip(notes, notes[1:]):
        iv = abs(a - b)
        s += {0: -3, 1: 1, 2: 2, 3: 2, 4: 0.5, 5: 0}.get(iv, -1.5 - 0.3 * iv)
    s += 1.5 * len(set(notes))
    for i, n in enumerate(notes):
        beat = 28 + i
        if beat % 2 == 0 and (n % 12) in {c % 12 for c in chord_of(beat)}:
            s += 1.2
    # arch: peak somewhere in the middle
    pk = int(np.argmax(notes))
    s += 2.0 if 3 <= pk <= 9 else 0
    return s


results = []
for R0 in all_rotations():
    R = R0.copy()
    lap_notes = []
    for d in LAP:
        R = tip(R, d)
        lap_notes.append(bottom_note(R))
    Rh = R.copy()
    for pat in itertools.product('FS', repeat=11):
        seq = list(pat) + ['S', 'F']
        if seq[0] != 'S' or seq.count('F') != 7:
            continue
        R = Rh.copy()
        lat = 0
        notes = []
        for m in seq:
            if m == 'F':
                d = -Z
            else:
                d = X if lat == 0 else -X
                lat = 1 - lat
            R = tip(R, d)
            notes.append(bottom_note(R))
        if notes[-3:] != [66, 69, 74]:
            continue
        results.append((score(notes), ''.join(seq), notes, lap_notes, R0))
results.sort(key=lambda r: -r[0])
print(len(results))
for sc, seq, notes, lap, R0 in results[:12]:
    print(round(sc, 1), seq, ' '.join(NAME[n] for n in notes), '| sides:', ' '.join(NAME[n] for n in lap[:4]), '/', ' '.join(NAME[n] for n in lap[8:12]), '/', ' '.join(NAME[n] for n in lap[16:20]), '| R0', R0.tolist())
