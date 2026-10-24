"""v8 "300 Years of Music, One Marble": the wall is the score and the marble plays it.

Every note is an engraved note head standing out from the page exactly where it is written: height by staff
position (clef, ledger lines, sharps), left to right by time; bar lines, key and time signatures, double bars.
At the end of a row a long note sends the ball into a funnel and through a glass tube back to the start of
the next row (a carriage return); between pieces the tube carries it down to the next era's page.

    SONGS_MODULE=songs7 python film8.py -- --res 1920x1080 --samples 12 --out frames/f_#### [--stills 60,900]
"""
import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib  # noqa: E402
import os  # noqa: E402
S = importlib.import_module(os.environ.get('SONGS_MODULE', 'songs6'))   # which medley to build
import gadgets as GD  # noqa: E402   the Pythagora-switch machines between pieces

ap = argparse.ArgumentParser()
ap.add_argument('--res', default='1280x720')
ap.add_argument('--samples', type=int, default=16)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--out', default='frames/f_####')
ap.add_argument('--frames', default='')
ap.add_argument('--stills', default='')
ap.add_argument('--gpu', action='store_true', help='render on the graphics card (OptiX, CUDA, HIP or Metal)')
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
W, H = (int(v) for v in a.res.split('x'))
FPS = a.fps
G = 9.81
R = 0.056          # main marble
R2 = 0.03          # clone marble
YB = 0.30          # depth of the ball's plane (wall is at y = 0.62)
rng = random.Random(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.fps = FPS
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
if a.gpu:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        devs = [d for d in prefs.devices if d.type == kind]
        if devs:
            for d in prefs.devices:
                d.use = d.type == kind
            sc.cycles.device = 'GPU'
            print('rendering on', kind, [d.name for d in devs], flush=True)
            break
    else:
        print('no GPU found, rendering on the CPU', flush=True)
sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.cycles.transmission_bounces = 4
sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
sc.render.use_persistent_data = False      # on, it rendered some instanced pipes black in sequences (not in stills)
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.35
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'
world = bpy.data.worlds.new('w')
sc.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.006, 0.005, 0.012, 1)

T_END = S.total_seconds()
N = int(round(T_END * FPS))
sc.frame_start, sc.frame_end = 1, N


def fr(t):
    return 1 + t * FPS


def smooth(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


# ================================================================ helpers
def mat(name, col, rough=0.4, metal=0.0, emit=None, emit_s=0.0, coat=0.0, trans=0.0, alpha=1.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['IOR'].default_value = ior
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_s
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    if trans:
        b.inputs['Transmission Weight'].default_value = trans
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    return m


def emit_keys(m, pts):
    sock = m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    for t, s in pts:
        sock.default_value = s
        sock.keyframe_insert('default_value', frame=fr(max(0.0, t)))


def flash(m, t, base, peak, after):
    emit_keys(m, ((t - 1 / FPS, base), (t, peak), (t + 0.35, after)))


_SHARED = {}


def _prim(key, make, smooth_=False):
    """An object on a mesh shared by every call with the same shape (exactly what the operator would build).
    Building through the operators slows down as the scene grows; this keeps the build fast and lets
    Cycles instance the repeated shapes."""
    me = _SHARED.get(key)
    if me is None:
        make()
        tmp = bpy.context.object
        me = tmp.data
        if smooth_:
            me.shade_smooth()
        me.materials.append(None)
        bpy.data.objects.remove(tmp)
        _SHARED[key] = me
    o = bpy.data.objects.new(key[0], me)
    o['shared'] = 1
    bpy.context.collection.objects.link(o)
    return o


def add(o, m):
    if o.get('shared'):
        o.material_slots[0].link = 'OBJECT'
        o.material_slots[0].material = m
    else:
        o.data.materials.append(m)
    return o


def cube(loc, scale, m, bevel=0.0, rot=(0, 0, 0)):
    if bevel:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
        o = bpy.context.object
        o.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        md = o.modifiers.new('b', 'BEVEL')
        md.width, md.segments = bevel, 2
        return add(o, m)
    o = _prim(('cube',), lambda: bpy.ops.mesh.primitive_cube_add(size=1))
    o.location, o.rotation_euler, o.scale = loc, rot, scale
    return add(o, m)


def sphere(loc, r, m, scale=None, segs=24):
    o = _prim(('sphere', round(r, 6), segs), lambda: bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segs, ring_count=max(8, segs // 2), radius=r), smooth_=True)
    o.location = loc
    if scale:
        o.scale = scale
    return add(o, m)


def cyl(p0, p1, r, m, verts=20, smooth_=True):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    o = _prim(('cyl', verts, round(r, 6), round(d.length, 6), smooth_), lambda: bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=r, depth=d.length), smooth_=smooth_)
    o.location = (p0 + p1) / 2
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return add(o, m)


def cone(loc, r1, r2, depth, m, verts=32):
    o = _prim(('cone', verts, round(r1, 6), round(r2, 6), round(depth, 6)), lambda: bpy.ops.mesh.primitive_cone_add(
        vertices=verts, radius1=r1, radius2=r2, depth=depth), smooth_=True)
    o.location = loc
    return add(o, m)


def torus(loc, R_, r_, m, rot=(0, 0, 0)):
    o = _prim(('torus', round(R_, 6), round(r_, 6)), lambda: bpy.ops.mesh.primitive_torus_add(
        major_radius=R_, minor_radius=r_, major_segments=40, minor_segments=10))
    o.location, o.rotation_euler = loc, rot
    return add(o, m)


def empty(loc, name='e'):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    sc.collection.objects.link(o)
    return o


def parent(o, p):
    o.parent = p
    o.matrix_parent_inverse = p.matrix_world.inverted()


def key_vis(o, t_on, t_off=None):
    pts = [(t_on - 1 / FPS, True), (t_on, False)]
    if t_off is not None:
        pts += [(t_off, False), (t_off + 1 / FPS, True)]
    for t, hide in pts:
        o.hide_render = hide
        o.keyframe_insert('hide_render', frame=fr(max(0.0, t)))


def bracket(p, length=None):
    """A chrome arm from the wall to point p (the instrument hangs on it)."""
    return cyl((p.x, 0.62, p.z), (p.x, p.y + 0.02, p.z), 0.008, M_CHROME, 10)


NEON = {'cyan': (0.05, 0.85, 1.0), 'magenta': (1.0, 0.08, 0.55), 'violet': (0.55, 0.2, 1.0),
        'lime': (0.45, 1.0, 0.25), 'amber': (1.0, 0.6, 0.08), 'red': (1.0, 0.12, 0.12), 'white': (1.0, 0.92, 0.96)}
NOTE_COL = {0: 'amber', 2: 'lime', 3: 'violet', 4: 'cyan', 5: 'red', 7: 'violet', 8: 'violet', 9: 'magenta', 11: 'lime'}


def ncol(midi):
    return NEON[NOTE_COL[midi % 12]]


M_WALL = mat('wall', (0.07, 0.05, 0.09), 0.85)
M_CHROME = mat('chrome', (0.92, 0.92, 0.96), 0.07, metal=1.0)
M_BRASS = mat('brass', (0.88, 0.64, 0.26), 0.2, metal=1.0)
M_DARKM = mat('darkmetal', (0.12, 0.12, 0.14), 0.3, metal=0.8)
M_RUBBER = mat('rubber', (0.03, 0.03, 0.035), 0.5)
M_WHITE = mat('eyewhite', (0.95, 0.95, 0.97), 0.25)
M_HI = mat('hilite', (1, 1, 1), 0.2, emit=(1, 1, 1), emit_s=4)
M_PUPIL = mat('pupil', (0.01, 0.01, 0.02), 0.2)


# ================================================================ effects
def burst(p, t, col, n=7, speed=0.9, life=0.35, size=0.008):
    m = mat('spark', col, 0.3, emit=col, emit_s=30)
    for j in range(n):
        ang = rng.uniform(0, 2 * math.pi)
        v = Vector((math.cos(ang) * speed * rng.uniform(0.5, 1.0), -rng.uniform(0.05, 0.35),
                    abs(math.sin(ang)) * speed * rng.uniform(0.6, 1.2) + 0.3))
        o = sphere(p, size, m, segs=8)
        key_vis(o, t, t + life)
        for u in (0.0, life * 0.33, life * 0.66, life):
            o.location = p + v * u + Vector((0, 0, -0.5 * G * u * u))
            s = 1.0 - (u / life) * 0.9
            o.scale = (s, s, s)
            o.keyframe_insert('location', frame=fr(t + u))
            o.keyframe_insert('scale', frame=fr(t + u))


def shell(p, t, col, n=26, r=0.20, life=0.95, size=0.0075):
    """A firework shell: sparks fly out evenly in a ring (seen face-on), slow as the air takes them, sag a
    little and fade; a bright flash at the centre as it opens."""
    m = mat('shell', col, 0.3, emit=col, emit_s=26)
    for j in range(n):
        ang = 2 * math.pi * (j + rng.uniform(-0.25, 0.25)) / n
        rr = r * rng.uniform(0.75, 1.05)
        d = Vector((math.cos(ang), rng.uniform(-0.15, 0.15), math.sin(ang)))
        o = sphere(p, size, m, segs=8)
        key_vis(o, t, t + life)
        for u in (0.0, 0.08, 0.2, 0.4, 0.65, life):
            o.location = p + d * rr * (1 - math.exp(-u / 0.12)) + Vector((0, 0, -0.18 * u * u))
            s = max(0.05, 1.0 - (u / life) ** 1.6)
            o.scale = (s, s, s)
            o.keyframe_insert('location', frame=fr(t + u))
            o.keyframe_insert('scale', frame=fr(t + u))
    fm = mat('shellflash', (1, 1, 1), 0.3, emit=(1.0, 0.95, 0.85), emit_s=0.0)
    fl = sphere(p, 0.03, fm, segs=12)
    emit_keys(fm, ((t - 0.02, 0.0), (t, 30.0), (t + 0.12, 0.0)))
    key_vis(fl, t - 0.02, t + 0.15)


def pulse_ring(p, t, col, r0=0.04, r1=0.14, life=0.28, rot=(math.radians(90), 0, 0)):
    rm = mat('ring', col, 0.2, emit=col, emit_s=14)
    emit_keys(rm, ((t, 14), (t + life, 0.3)))
    o = torus(p, 1.0, 0.035, rm, rot=rot)
    key_vis(o, t, t + life)
    for u, r in ((0.0, r0), (life, r1)):
        o.scale = (r, r, r * 0.5)
        o.keyframe_insert('scale', frame=fr(t + u))


def wobble(o, t, axis=1, amp=10.0, base=0.0):
    for u, k in ((-1 / FPS, 0), (0.05, 1), (0.18, -0.6), (0.32, 0.35), (0.5, -0.15), (0.7, 0)):
        o.rotation_euler[axis] = base + math.radians(amp * k)
        o.keyframe_insert('rotation_euler', index=axis, frame=fr(t + u))


def dip(o, t, dz=-0.012):
    z0 = o.location.z
    for u, d in ((-1 / FPS, 0), (0.04, dz), (0.15, -dz * 0.3), (0.28, 0)):
        o.location.z = z0 + d
        o.keyframe_insert('location', index=2, frame=fr(t + u))
    o.location.z = z0


# ================================================================ characters
def character(x, z, body_col, iris_col, accent, name, eye_r=0.088, smile=False, both=False):
    root = empty((x, 0.18, z), name)
    look = empty((x, 0.0, z + 0.15), name + '_look')
    parent(look, root)
    parts = [cube((x, 0.18, z - 0.42), (0.34, 0.30, 0.14), M_BRASS, bevel=0.02)]
    bm = mat(name + 'body', body_col, 0.35, coat=0.8)
    parts.append(cyl((x, 0.18, z - 0.35), (x, 0.18, z - 0.12), 0.12, bm))
    parts.append(sphere((x, 0.18, z + 0.12), 0.23, bm, segs=40))
    if accent == 'antenna':
        parts.append(cyl((x, 0.18, z + 0.33), (x + 0.03, 0.18, z + 0.48), 0.008, M_CHROME))
        parts.append(sphere((x + 0.03, 0.18, z + 0.49), 0.03, mat('ant', NEON['cyan'], 0.2, emit=NEON['cyan'], emit_s=15)))
    elif accent == 'halo':
        parts.append(torus((x, 0.18, z + 0.41), 0.11, 0.013, mat('halo', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=12)))
    elif accent == 'ears':
        for s in (-1, 1):
            parts.append(sphere((x + s * 0.15, 0.18, z + 0.33), 0.06, bm, scale=(0.7, 0.7, 1.4)))
            parts.append(sphere((x + s * 0.15, 0.13, z + 0.34), 0.025,
                                mat('earglow', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=8), scale=(0.7, 0.4, 1.4)))
    irises = []
    for s in (-1, 1):
        c = Vector((x + s * 0.09, 0.0, z + 0.15))
        parts.append(sphere(c, eye_r, M_WHITE, scale=(1.0, 0.45, 1.15)))
        ic = c + Vector((0, -eye_r * 0.42, 0))
        im = mat(name + 'iris', iris_col, 0.2, emit=iris_col, emit_s=1.2)
        irises.append(sphere(ic, eye_r * 0.62, im, scale=(1.0, 0.35, 1.1)))
        irises.append(sphere(ic + Vector((0, -eye_r * 0.18, 0)), eye_r * 0.30, M_PUPIL, scale=(1, 0.35, 1.1)))
        irises.append(sphere(ic + Vector((eye_r * 0.22, -eye_r * 0.30, eye_r * 0.28)), eye_r * 0.13, M_HI))
    mm_ = mat(name + 'mouth', (0.15, 0.02, 0.05), 0.4)
    beads = []
    if smile or both:                               # a wide grin: beads along the bottom of a circle
        beads = [sphere((x + 0.055 * math.cos(a_), -0.045, z + 0.035 + 0.055 * math.sin(a_)), 0.011, mm_, segs=10)
                 for a_ in [math.radians(200 + 20 * k) for k in range(8)]]
        parts += beads
        mouth = beads[0]
    if not smile or both:
        mouth = torus((x, -0.04, z + 0.0), 0.035, 0.007, mm_, rot=(math.radians(90), 0, 0))
        parts.append(mouth)
    for o in parts:
        parent(o, root)
    for o in irises:
        parent(o, look)
    return dict(root=root, look=look, mouth=mouth, z0=z, beads=beads)


def track_eyes(ch, pos_fn):
    f = 1
    while f <= N:
        t = (f - 1) / FPS
        d = pos_fn(t) - (ch['root'].location + Vector((0, 0, 0.15)))
        ch['look'].delta_location = (max(-1, min(1, d.x / 0.6)) * 0.024, 0, max(-1, min(1, d.z / 0.8)) * 0.028)
        ch['look'].keyframe_insert('delta_location', frame=f)
        f += 2


def hop(ch, t, h=0.15):
    r = ch['root']
    for u, dz, sq in ((-0.06, 0, 1.0), (0.0, -0.03, 0.88), (0.14, h, 1.08), (0.30, 0.0, 0.92), (0.40, 0, 1.0)):
        r.location.z = ch['z0'] + dz
        r.keyframe_insert('location', index=2, frame=fr(t + u))
        r.scale = (1 / sq ** 0.5, 1, sq)
        r.keyframe_insert('scale', frame=fr(t + u))


def mouth_o(ch, t0, t1, s=1.9):
    m = ch['mouth']
    for t, k in ((t0 - 0.05, 1.0), (t0 + 0.08, s), (t1, s), (t1 + 0.2, 1.0)):
        m.scale = (k, k * (1.3 if k > 1 else 1), k)
        m.keyframe_insert('scale', frame=fr(max(0.0, t)))


# ================================================================ v8: the marble plays the score written on the wall
FREESERIF = '/usr/share/fonts/truetype/freefont/FreeSerif.ttf'
C, GAPS = S.timeline()
for h_ in C:          # on the score every written note has its own head (no second bounce on one head)
    if h_['mech'] == 'again':
        h_['mech'] = 'pad'
SONGS = S.SONGS
FIN = C[-1]
TF = FIN['t']
ERAS = S.ERA
rng = random.Random(31)

# paper and ink for each era (the wall is the page)
PAGE = {
    'baroque': dict(paper=(0.80, 0.70, 0.52), ink=(0.16, 0.10, 0.06), ink_metal=0.0, rough=0.9),
    'classical': dict(paper=(0.66, 0.52, 0.50), ink=(0.05, 0.03, 0.03), ink_metal=0.0, rough=0.85),   # dusty-rose salon
    'beethoven': dict(paper=(0.07, 0.09, 0.17), ink=(0.86, 0.88, 0.93), ink_metal=0.9, rough=0.6),
    'romantic': dict(paper=(0.46, 0.10, 0.12), ink=(1.0, 0.84, 0.46), ink_metal=0.2, rough=0.5),     # lit crimson
    # pieces with a page of their own, so two pieces of one era never look alike
    'ekn': dict(paper=(0.20, 0.19, 0.42), ink=(0.95, 0.93, 0.86), ink_metal=0.2, rough=0.7, stars=True),  # indigo night
    'b5': dict(paper=(0.30, 0.33, 0.38), ink=(0.95, 0.96, 0.98), ink_metal=0.25, rough=0.6),       # slate storm
    'fe': dict(paper=(0.30, 0.20, 0.36), ink=(0.96, 0.91, 0.96), ink_metal=0.2, rough=0.6),        # violet dusk
    'otj': dict(paper=(0.88, 0.76, 0.50), ink=(0.10, 0.07, 0.04), ink_metal=0.0, rough=0.85),   # sunlit gold
}
LS = 0.075               # staff line spacing (one step = LS / 2)
K_SP, GAP_MIN = 0.40, 0.14     # engraved spacing: the gap after a note grows with the square root of its value
ACC_PAD = 0.075                # extra room in front of a note that carries an accidental


def bar_x(h, nxt):
    """x of the bar line between note h and the next one: about one space before the next note's leftmost
    ink (its accidental, its down-stem, or its head), and clear of this note's up-stem."""
    xa, xb = HEAD[h['i']][0].x, HEAD[nxt['i']][0].x
    left = xb - (0.14 if nxt.get('acc') else 0.051 if HEAD[nxt['i']][1] >= 4 else 0.052)
    return max(left - 0.075, xa + 0.11)


def engr_gap(song, h):
    return max(GAP_MIN, K_SP * math.sqrt(song['unit'] * h['nunit']))
ROW_W = 2.9              # a row turns (carriage return) on a long note once it is this wide
BAR_PAD = 0.08           # extra room at a bar line, about a space before the next head
ROW_H = 1.05             # distance between rows
X_LEFT = -1.6
# how far a row may run past ROW_W looking for a bar line it can turn on. Rondo alla Turca and Für Elise
# never end a bar on a note long enough for the tube ride (their bars end on sixteenths), so they keep to one
# long line each instead of breaking mid-bar, as no engraver would
ROW_EXTRA = float(os.environ.get('ROW_EXTRA', 5.5))
CLEF_W = 0.55
KS_DX = 0.072            # spacing of the key-signature accidentals
MACH_DROP = 1.0          # extra room between pages for the machine that carries the marble across
WALL_Y = 0.62
HEAD_Y = 0.54            # note heads stand just off the page (stems on the page read as attached)
R_HEAD = (0.052, 0.045, 0.037)
LETTERS = 'CDEFGAB'
KS_SHARPS, KS_FLATS = 'FCGDAEB', 'BEADGCF'
ACC_SYM = {1: '♯', -1: '♭', 0: '♮'}


def spell(name):
    """'Eb4' -> ('E', -1, 4): the letter, the alteration and the octave, as the score spells it."""
    alt = {'#': 1, 'b': -1}.get(name[1], 0) if len(name) > 2 else 0
    return name[0], alt, int(name[-1])


def step_of(name, clef):
    """Staff step (0 = bottom line) for a spelled pitch: treble bottom line E4, bass bottom line G2."""
    L, _, o = spell(name)
    ref = 4 * 7 + 2 if clef == 'treble' else 2 * 7 + 4
    return o * 7 + LETTERS.index(L) - ref


def key_alt(ks):
    return {L: 1 if ks > 0 and L in KS_SHARPS[:ks] else -1 if ks < 0 and L in KS_FLATS[:-ks] else 0 for L in LETTERS}


T_HOP = 0.40     # the longest free flight; a longer note holds the ball on its head first
E_REST = 0.5     # restitution of the small settling bounces


def bounces(t0, hold):
    """Settling bounces after a hit: list of (start, duration, height), dying out within 70% of the hold."""
    h1 = min(0.035, G / 8 * (0.7 * hold * (1 - E_REST)) ** 2)
    out, u, hk = [], t0, h1
    while hk > 4e-4:
        Tk = 2 * math.sqrt(2 * hk / G)
        out.append((u, Tk, hk))
        u += Tk
        hk *= E_REST ** 2
    return out


def is_held(h0, h1):
    return h1['t'] - h0['t'] > T_HOP + 0.06


def ballistic(p0, t0, p1, t1, t):
    T = t1 - t0
    v = (p1 - p0 + Vector((0, 0, 0.5 * G * T * T))) / T
    u = t - t0
    return p0 + v * u + Vector((0, 0, -0.5 * G * u * u))


# ---------------------------------------------------------------- 1. layout: rows of staves, page after page
CON, HEAD, ROWS, RETURNS = {}, {}, [], {}
sec_rows = {}
row_z = 0.0
PAGE_X = {}           # how far right each page starts: after a long line the next page starts further right,
SPAN_MAX = 1.2        # so a machine never rolls back more than this beyond its own mechanisms
for s, song in enumerate(SONGS):
    hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
    clef = song['clef']
    px = 0.0
    if s > 0:
        drop_ = 0.0
        if song.get('machine'):                # room for the machine that carries the marble here
            x_l = HEAD[[h for h in C if h['s'] == s - 1 and h['mech'] != 'bigdrum'][-1]['i']][0].x
            px = max(0.0, x_l + 0.14 - (X_LEFT + 0.58) - GD.width_need(song['machine']) - SPAN_MAX)
            drop_ = max(MACH_DROP, GD.height_need(song['machine'], x_l + 0.14 - (X_LEFT + px + 0.58)) - 0.10)
        row_z -= ROW_H * 1.25 + drop_          # a new page starts lower
    PAGE_X[s] = px
    row = dict(s=s, z=row_z, t0=hs[0]['t'], x0=X_LEFT + px + CLEF_W + 0.35, notes=[], first=True, px=px)
    ROWS.append(row)
    sec_rows[s] = [row]
    nunits = song.get('nunits') or [u for _, u in song['notes']]
    kalt, bu, pu = key_alt(song['keysig']), song['bar_units'], song['pickup_units']
    state, bar_now, pos = {}, None, 0.0
    xc = row['x0']
    for j, h in enumerate(hs):
        h['nunit'] = nunits[j]
        # accidentals as engraved: only against the key signature, and they last until the bar line
        name = song['notes'][h['j']][0]
        bar = int((pos - pu) // bu) if bu else 0
        if bar != bar_now:
            state, bar_now = {}, bar
        L, alt, o = spell(name)
        h['acc'] = None if alt == state.get((L, o), kalt[L]) else ACC_SYM[alt]
        state[(L, o)] = alt
        pos += h['nunit']
        x = xc + (ACC_PAD if h['acc'] else 0.0)
        xc = x + engr_gap(song, h)
        st = step_of(name, clef)
        head = Vector((x, HEAD_Y, row['z'] + st * LS / 2))
        HEAD[h['i']] = (head, st, row)
        CON[h['i']] = head + Vector((0, HEAD_Y - HEAD_Y, R_HEAD[2] + R))
        if h['mech'] == 'again':
            CON[h['i']] = CON[h['i'] - 1].copy()
            HEAD[h['i']] = HEAD[h['i'] - 1]
        row['notes'].append(h)
        nxt = hs[j + 1] if j + 1 < len(hs) else None
        # a new line starts at a bar line, as on a printed page; only when no bar ends on a note long
        # enough for the tube ride does the row run on a little and break mid-bar
        at_bar = bool(bu) and int((pos - pu) // bu) != bar
        if at_bar:
            xc += BAR_PAD
        brk = song.get('break_after')                 # a piece may name its line break (the Fifth: after the D)
        if nxt is not None and (h['j'] in brk if brk else h['dur'] >= 0.34 and (
                x - row['x0'] >= ROW_W and (at_bar or not bu) or x - row['x0'] >= ROW_W + ROW_EXTRA)):
            # carriage return: into a funnel at the end of the row, along a glass tube, out at the next row
            row_z -= ROW_H
            new = dict(s=s, z=row_z, t0=nxt['t'], x0=X_LEFT + px + CLEF_W + KS_DX * abs(song['keysig']), notes=[], after_return=True,
                       first=False, px=px)
            # on a long note the marble sits on it a while (the fermata) and leaves for a ride of about a second
            RETURNS[h['i']] = dict(t0=h['t'] + max(0.14, h['dur'] - 1.3), t1=nxt['t'] - 0.16, row_from=row, row_to=new,
                                   at_bar=at_bar or not bu, width=x - row['x0'])
            row['x1'] = x + 0.25
            row = new
            xc = row['x0']
            ROWS.append(row)
            sec_rows[s].append(row)
    row['x1'] = HEAD[hs[-1]['i']][0].x + max(0.25, engr_gap(song, hs[-1]) + 0.06)
    row_z = row['z']
# final drum after the double bar of the last row
LASTROW = ROWS[-1]
DRUM = Vector((LASTROW['x1'] + 0.55, HEAD_Y, LASTROW['z'] - 0.35))
CON[FIN['i']] = DRUM + Vector((0, 0, 0.004 + R))
if os.environ.get('LAYOUT_ONLY'):              # quick check of the line breaks, without building the scene
    print('line breaks', ' '.join(f"{SONGS[C[i]['s']]['key']}:{'bar' if r['at_bar'] else 'MID'}({r['width']:.1f})"
                                  for i, r in RETURNS.items()), flush=True)
    print('rows', ' '.join(f"{SONGS[r['s']]['key']}:{r['x1'] - r['x0']:.1f}" for r in ROWS), flush=True)
    print('page x', {SONGS[k]['key']: round(v, 2) for k, v in PAGE_X.items()}, flush=True)
    print('wall: rows z', round(ROWS[0]['z'], 2), 'to', round(ROWS[-1]['z'], 2), ' x', X_LEFT, 'to',
          round(max(r['x1'] for r in ROWS), 2), ' drum', tuple(round(v, 2) for v in DRUM), flush=True)
    sys.exit(0)


def tube_path(ret, h):
    """Polyline for a carriage return: drop into the funnel, run left under the staff, rise to the next row."""
    a = CON[h['i']]
    rf, rt = ret['row_from'], ret['row_to']
    zt_ = rf['z'] - SONGS[rf['s']].get('tube_depth', 0.42)
    # the funnel stands past the line-end bar line (on the staff it sat among the notes)
    pts = [a, Vector((a.x + 0.36, HEAD_Y, a.z - 0.16)), Vector((a.x + 0.42, HEAD_Y, zt_ + 0.05)), Vector((a.x + 0.32, HEAD_Y, zt_)),
           Vector((X_LEFT + rt['px'] + 0.15, HEAD_Y, zt_)), Vector((X_LEFT + rt['px'] + 0.05, HEAD_Y, zt_ - 0.10)),
           Vector((X_LEFT + rt['px'] + 0.12, HEAD_Y, rt['z'] + 0.55))]
    return pts


def poly_at(pts, k):
    L = [0.0]
    for p, q in zip(pts[:-1], pts[1:]):
        L.append(L[-1] + (q - p).length)
    s_ = k * L[-1]
    for j in range(len(pts) - 1):
        if s_ <= L[j + 1]:
            return pts[j].lerp(pts[j + 1], (s_ - L[j]) / max(1e-6, L[j + 1] - L[j]))
    return pts[-1]


for i, ret in RETURNS.items():
    ret['pts'] = tube_path(ret, C[i])

# gaps between songs: a small Pythagora-switch machine carries the marble to the next page (gadgets.py)
GAPMACH = {}
for g in GAPS:
    s = g['s']
    L_ = [h for h in C if h['s'] == s - 1 and h['mech'] != 'bigdrum'][-1]
    F_ = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum'][0]
    mk_ = GD.plan(SONGS[s].get('machine', ['stairs']), SONGS[s]['era'], CON[L_['i']], L_['t'], CON[F_['i']], F_['t'],
                  HEAD[L_['i']][2]['z'], HEAD[F_['i']][2]['z'], R, HEAD_Y)
    mk_.L, mk_.F = L_, F_
    mk_.swing = 1.0 if len(GAPMACH) % 2 == 0 else -1.0
    GAPMACH[s] = mk_
    print(f"machine {SONGS[s]['key']}: {mk_.kind}, rail angle {math.degrees(mk_.theta):.1f} deg, "
          f"spring waits {mk_.wait:.2f} s" + (f", LATE by {mk_.late:.2f} s" if mk_.late > 0 else ''), flush=True)
    if mk_.late > 0.02 and not os.environ.get('ALLOW_LATE'):
        raise SystemExit(f"the machine into {SONGS[s]['key']} arrives {mk_.late:.2f} s after the music needs it: "
                         'give it a longer interlude or a shorter path')
    if os.environ.get('MACH_PACE'):              # the interlude each machine needs at a lively 7-9 degrees
        need = []
        for deg in (7, 8, 9):
            m8 = GD._simulate(mk_.kinds, SONGS[s]['era'], CON[L_['i']], L_['t'], CON[F_['i']], HEAD[L_['i']][2]['z'],
                              HEAD[F_['i']][2]['z'], R, HEAD_Y, math.radians(deg))
            need.append(round(m8.t_arrive - L_['t'] + GD.T_KICK + 0.05 + GD.T_HOP_OUT - min(L_['dur'], 0.8), 2)
                        if m8 else None)
        print(f"  pace {SONGS[s]['key']}: interlude at 7/8/9 deg = {need}", flush=True)


# the opening: the marble waits behind a small brass gate at the top of a long ledge while a pendulum on the
# page counts in at the first piece's tempo (soft ticks over room tone, so nothing starts out of silence). On
# the third tick before the first note the gate swings open and the marble rolls down from rest, gathering
# speed, and drops onto the first note.
BEAT0 = SONGS[0]['beat']
T_HOP0 = 0.18
TICKS = [C[0]['t'] - k * BEAT0 for k in range(8, 0, -1) if C[0]['t'] - k * BEAT0 > 0.1]
T_GATE = C[0]['t'] - 3 * BEAT0
LEDGE_LEN = 0.48
LEDGE_ACC = 2 * LEDGE_LEN / (C[0]['t'] - T_HOP0 - T_GATE) ** 2      # rolling from rest: reaches the end on time
LEDGE_TH = math.asin(LEDGE_ACC / (5 / 7 * 9.81))
LEDGE_V = LEDGE_ACC * (C[0]['t'] - T_HOP0 - T_GATE)
LEDGE_END = CON[0] + Vector((-0.10, 0, 0.06))
LEDGE_START = LEDGE_END + Vector((-LEDGE_LEN * math.cos(LEDGE_TH), 0, LEDGE_LEN * math.sin(LEDGE_TH)))
print(f'opening: ticks {[round(t_, 2) for t_ in TICKS]}, gate {T_GATE:.2f} s, ledge {math.degrees(LEDGE_TH):.1f} deg, '
      f'leaves at {LEDGE_V:.2f} m/s', flush=True)


def ease(k):
    return k * k * (3 - 2 * k)


def kick_time(h0):
    """When a long note flicks the held ball on to the next note (None for an ordinary flight)."""
    if h0['i'] + 1 >= len(C):
        return None
    h1 = C[h0['i'] + 1]
    if h1['mech'] == 'bigdrum' or RETURNS.get(h0['i']) or h0['s'] != h1['s']:
        return None
    return h1['t'] - T_HOP if is_held(h0, h1) else None


# the small taps of the settling bounces (for the sound)
TAPS = []
for h_ in C[:-1]:
    tk_ = kick_time(h_)
    if tk_ is not None:
        for b0, Tk, hk in bounces(h_['t'], tk_ - h_['t']):
            if hk > 0.003:
                TAPS.append(dict(t=b0 + Tk, g=math.sqrt(hk / 0.035)))


# ---------------------------------------------------------------- the rescue
# Before Mountain King's last, fastest pass the marble hits its note too hard, sails past the funnel and off
# the end of the line. The music stops (a general pause in the medley). The blue character on a stand beside
# the line catches it in a net; it wobbles there, nearly tipping out; then the net tosses it back into the
# funnel, the tube carries it to the next line, and it lands on the first note exactly on the beat: the
# fastest pass begins.
RESCUE = None
for i_, ret_ in RETURNS.items():
    if SONGS[C[i_]['s']].get('gp', {}).get(C[i_]['j']):
        RESCUE = dict(h0=C[i_], h1=C[i_ + 1], ret=ret_)
if RESCUE:
    rs_ = RESCUE
    row_ = rs_['ret']['row_from']
    rs_['stand'] = Vector((row_['x1'] + 0.95, 0.18, row_['z'] - 0.62))      # the catcher's feet
    rs_['t_clip'] = rs_['h0']['t'] + 0.22                                    # it clips the funnel's lip...
    rs_['rim'] = rs_['ret']['pts'][1] + Vector((0.07, 0, 0.065 + R))
    rs_['t_c'] = rs_['h0']['t'] + 0.95                                       # ...flies up, hangs, falls: caught low
    rs_['t_t'] = rs_['t_c'] + 0.85                                           # tossed back
    rs_['t_in'] = rs_['t_t'] + 0.45                                          # into the funnel
    rs_['ret']['t0'], rs_['ret']['t1'] = rs_['t_in'], rs_['h1']['t'] - 0.16  # the tube ride, as usual
    NET_LOW = rs_['stand'] + Vector((-0.20, 0.12, 0.30))
    NET_UP = rs_['stand'] + Vector((-0.34, 0.14, 0.50))


def net_ring(t):
    """Centre of the catcher's net: lowered, raised to catch, sagging and rocking, wound back, swung."""
    tc, tt_ = RESCUE['t_c'], RESCUE['t_t']
    p = NET_LOW.lerp(NET_UP, smooth((t - (tc - 0.45)) / 0.4))
    if tc <= t:                                          # it sags with the catch and rocks: will it tip out?
        u = t - tc
        p = p + Vector((0.05 * math.sin(u * 9) * math.exp(-u * 1.2), 0,
                        -0.07 * math.exp(-u * 4) * min(1.0, u * 25) - 0.02 * math.sin(u * 7) * math.exp(-u * 0.8)))
    wind = smooth((t - (tt_ - 0.3)) / 0.3) * (1 - smooth((t - tt_) / 0.08))
    swing = smooth((t - tt_) / 0.12) * (1 - smooth((t - (tt_ + 0.5)) / 0.5))
    return p + Vector((0.12, 0, -0.10)) * wind + Vector((-0.18, 0, 0.14)) * swing


def rescue_pos(t):
    rs = RESCUE
    bag = lambda tt: net_ring(tt) - Vector((0, 0, 0.05))   # noqa: E731
    if t <= rs['t_clip']:
        return ballistic(CON[rs['h0']['i']], rs['h0']['t'], rs['rim'], rs['t_clip'], t)
    if t <= rs['t_c']:
        return ballistic(rs['rim'], rs['t_clip'], bag(rs['t_c']), rs['t_c'], t)
    if t <= rs['t_t']:
        return bag(t)
    pts, tub = rs['ret']['pts'], rs['ret']
    if t <= rs['t_in']:
        return ballistic(bag(rs['t_t']), rs['t_t'], pts[1], rs['t_in'], t)
    if t <= tub['t1']:
        return poly_at(pts[1:], ease((t - tub['t0']) / (tub['t1'] - tub['t0'])))
    return ballistic(pts[-1], tub['t1'], CON[rs['h1']['i']], rs['h1']['t'], t)


def rescue_view(t):
    """The camera through the rescue: follow the lob, come close on the wobbling net, then pull right back
    to see the long throw land on the next line."""
    rs = RESCUE
    p0, p1, nc = CON[rs['h0']['i']], CON[rs['h1']['i']], net_ring(rs['t_c'])
    mid = Vector((nc.x + 0.12, nc.y, rs['stand'].z + 0.32))      # the net and the whole catcher, above the HUD
    if t <= rs['t_c']:
        k = smooth((t - rs['h0']['t']) / (rs['t_c'] - rs['h0']['t']))
        return p0.lerp(mid, k) + Vector((0, 0, 0.25 * math.sin(math.pi * k))), 1.55, (0.0, 0.0)
    fun = rs['ret']['pts'][1]
    both = (nc + fun) / 2 + Vector((0, 0, 0.05))                  # the net and the funnel in one frame
    if t <= rs['t_t']:
        k = smooth((t - (rs['t_t'] - 0.45)) / 0.45)
        return mid.lerp(both, k), 1.38 + 0.2 * k, (0.0, 0.0)
    if t <= rs['t_in']:
        k = smooth((t - rs['t_t']) / (rs['t_in'] - rs['t_t']))
        return both.lerp(fun, 0.4 * k), 1.58 - 0.18 * k, (0.0, 0.0)
    k = smooth(min(1.0, (t - rs['t_in']) / max(1e-6, rs['h1']['t'] - 0.3 - rs['t_in'])))
    pb, zb = row_point(HEAD[rs['h1']['i']][2], rs['h1']['t'])
    return fun.lerp(pb, k), (1.3 + (zb - 1.3) * k) * (1 + 0.25 * math.sin(math.pi * k)), (0.0, 0.0)


def ball_pos(t):
    if t <= C[0]['t']:
        # the opening: it waits behind the gate, rolls down the ledge from rest, and drops onto the first note
        if t <= T_GATE:
            return LEDGE_START.copy()
        if t <= C[0]['t'] - T_HOP0:
            return LEDGE_START.lerp(LEDGE_END, 0.5 * LEDGE_ACC * (t - T_GATE) ** 2 / LEDGE_LEN)
        return ballistic(LEDGE_END, C[0]['t'] - T_HOP0, CON[0], C[0]['t'], t)
    for h0, h1 in zip(C[:-1], C[1:]):
        if h0['t'] <= t <= h1['t']:
            p0, p1 = CON[h0['i']], CON[h1['i']]
            if h1['mech'] == 'bigdrum':
                if t <= h1['launch']:
                    return p0
                return ballistic(p0, h1['launch'], p1, h1['t'], t)
            if h0['s'] != h1['s'] and h1['s'] in GAPMACH:
                return GAPMACH[h1['s']].pos(t)
            if RESCUE and h0 is RESCUE['h0']:
                return rescue_pos(t)
            tube = RETURNS.get(h0['i'])
            if tube:
                pts = tube['pts']
                if t <= tube['t0']:
                    tk = max(h0['t'], tube['t0'] - 0.14)     # a long last note: it rests there, then hops in
                    if t <= tk:
                        u_ = t - h0['t']
                        return p0 + Vector((0, 0, max(0.0, 0.025 * math.sin(u_ * 9.0) * math.exp(-u_ * 7.0))))
                    return ballistic(p0, tk, pts[1], tube['t0'], t)
                if t <= tube['t1']:
                    return poly_at(pts[1:], ease((t - tube['t0']) / (tube['t1'] - tube['t0'])))
                return ballistic(pts[-1], tube['t1'], p1, h1['t'], t)
            if is_held(h0, h1):
                tk = h1['t'] - T_HOP
                if t >= tk:
                    return ballistic(p0, tk, p1, h1['t'], t)
                for b0, Tk, hk in bounces(h0['t'], tk - h0['t']):
                    if t < b0 + Tk:
                        u_ = t - b0
                        return p0 + Vector((0, 0, math.sqrt(2 * G * hk) * u_ - 0.5 * G * u_ * u_))
                return p0
            return ballistic(p0, h0['t'], p1, h1['t'], t)
    u = t - TF
    return CON[FIN['i']] + Vector((0, 0, max(0.0, 0.12 * math.exp(-u * 2.4) * abs(math.sin(u * 7.5)))))


# ---------------------------------------------------------------- 2. the page: paper, staves, clefs, bars
def page_of(song):
    """The page style of a piece: its own if it has one, else its era's."""
    return song['key'] if song['key'] in PAGE else song['era']


def ink_mat(era):
    pg = PAGE[era]
    return bpy.data.materials.get('ink_' + era) or mat('ink_' + era, pg['ink'], 0.35, metal=pg['ink_metal'])


def paper_mat(era):
    """Paper with a little fibre and ink-wash variation (procedural), so the page never looks flat."""
    name = 'paper_' + era
    if bpy.data.materials.get(name):
        return bpy.data.materials[name]
    pg = PAGE[era]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt_ = m.node_tree
    b = nt_.nodes['Principled BSDF']
    noise = nt_.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 12.0
    ramp = nt_.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[c * 0.88 for c in pg['paper']], 1)
    ramp.color_ramp.elements[1].color = (*[min(1, c * 1.04) for c in pg['paper']], 1)
    nt_.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    nt_.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = pg['rough']
    bump = nt_.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.08
    n2 = nt_.nodes.new('ShaderNodeTexNoise')
    n2.inputs['Scale'].default_value = 140.0
    nt_.links.new(n2.outputs['Fac'], bump.inputs['Height'])
    nt_.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    if pg.get('stars'):
        night_sky(nt_, b, [r_ for r_ in ROWS if page_of(SONGS[r_['s']]) == era])
    return m


def night_sky(nt_, b, rows):
    """A sparse field of small, faint stars in the paper (world-space Voronoi cells, about a third of them
    lit, each at its own brightness), kept off the staves so the music reads as clearly as ever."""
    N = nt_.nodes.new
    geo = N('ShaderNodeNewGeometry')
    xyz = N('ShaderNodeSeparateXYZ')
    nt_.links.new(geo.outputs['Position'], xyz.inputs['Vector'])
    on_wall = N('ShaderNodeCombineXYZ')                                   # the wall's own 2-D coordinates
    nt_.links.new(xyz.outputs['X'], on_wall.inputs['X'])
    nt_.links.new(xyz.outputs['Z'], on_wall.inputs['Y'])
    vor = N('ShaderNodeTexVoronoi')
    vor.voronoi_dimensions = '2D'
    vor.inputs['Scale'].default_value = 9.0
    nt_.links.new(on_wall.outputs['Vector'], vor.inputs['Vector'])

    def ramp(src, a, b_, lo=0.0, hi=1.0):
        mr = N('ShaderNodeMapRange')
        mr.clamp = True
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = a, b_
        mr.inputs['To Min'].default_value, mr.inputs['To Max'].default_value = lo, hi
        nt_.links.new(src, mr.inputs['Value'])
        return mr.outputs['Result']

    def mul(x, y):
        m_ = N('ShaderNodeMath')
        m_.operation = 'MULTIPLY'
        nt_.links.new(x, m_.inputs[0])
        if isinstance(y, float):
            m_.inputs[1].default_value = y
        else:
            nt_.links.new(y, m_.inputs[1])
        return m_.outputs['Value']
    core = ramp(vor.outputs['Distance'], 0.0, 0.05, 1.0, 0.0)             # a dot about 1 cm across
    rgb = N('ShaderNodeSeparateColor')
    nt_.links.new(vor.outputs['Color'], rgb.inputs['Color'])
    lit = ramp(rgb.outputs['Red'], 0.66, 0.70)                            # a third of the cells hold a star
    bright = ramp(rgb.outputs['Green'], 0.0, 1.0, 0.35, 1.0)
    out = mul(mul(core, lit), bright)
    for r_ in rows:                                                       # none on or near a staff
        d_ = N('ShaderNodeMath')
        d_.operation = 'SUBTRACT'
        nt_.links.new(xyz.outputs['Z'], d_.inputs[0])
        d_.inputs[1].default_value = r_['z'] + 2 * LS
        ab = N('ShaderNodeMath')
        ab.operation = 'ABSOLUTE'
        nt_.links.new(d_.outputs['Value'], ab.inputs[0])
        out = mul(out, ramp(ab.outputs['Value'], 0.34, 0.44))
    b.inputs['Emission Color'].default_value = (1.0, 0.94, 0.82, 1)
    nt_.links.new(mul(out, 9.0), b.inputs['Emission Strength'])         # faint: never a sparkle


def text_obj(txt, loc, size, m, rot=(math.radians(90), 0, 0), align='CENTER', font=None):
    cu = bpy.data.curves.new('txt', 'FONT')
    cu.body = txt
    cu.font = bpy.data.fonts.load(font or FREESERIF, check_existing=True)
    cu.size = size
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.extrude = 0.004
    o = bpy.data.objects.new('txt', cu)
    o.location = loc
    o.rotation_euler = rot
    sc.collection.objects.link(o)
    o.data.materials.append(m)
    return o


def accidental(sym, x, z, ink):
    """An accidental whose optical centre sits on the note's line (the flat's bowl, the sharp's box)."""
    lift = {'♯': 0.021, '♮': 0.022, '♭': 0.008}[sym]      # engraved size: a sharp is about 2.6 spaces tall
    return text_obj(sym, Vector((x, WALL_Y - 0.008, z + lift)), 0.25, ink)


xs_all = [p.x for p in CON.values()]
W_X0, W_X1 = X_LEFT - 4, max(xs_all) + 4
page_bounds = []
for s, song in enumerate(SONGS):
    rows = sec_rows[s]
    z_top = rows[0]['z'] + ROW_H * 0.75
    z_bot = rows[-1]['z'] - ROW_H * 0.55
    page_bounds.append((z_top, z_bot))
for s, song in enumerate(SONGS):
    era = song['era']
    z_top = page_bounds[s - 1][1] if s > 0 else page_bounds[0][0] + 4
    z_bot = page_bounds[s][1] if s < len(SONGS) - 1 else page_bounds[s][1] - 4
    bpy.ops.mesh.primitive_plane_add(size=1, location=((W_X0 + W_X1) / 2, WALL_Y, (z_top + z_bot) / 2),
                                     rotation=(math.radians(90), 0, 0))
    wp = add(bpy.context.object, paper_mat(page_of(song)))
    wp.scale = (W_X1 - W_X0, z_top - z_bot + 0.002, 1)
    if s > 0:
        nc = NEON[ERAS[era]['neon'][0]]
        trim_m = mat(f'trim{s}', (0.80, 0.60, 0.30), 0.3, metal=1.0, emit=nc, emit_s=0.0)
        cyl((W_X0, WALL_Y - 0.016, z_top), (W_X1, WALL_Y - 0.016, z_top), 0.016, trim_m, 12)
        if s in GAPMACH:                        # the new page's border flares as the marble arrives
            tF = GAPMACH[s].F['t']
            emit_keys(trim_m, ((tF - 0.02, 0.0), (tF + 0.06, 9.0), (tF + 0.9, 0.0)))
    ink = ink_mat(page_of(song))
    for row in sec_rows[s]:
        x0s, x1s = X_LEFT + row['px'] + 0.05, row['x1']
        for ln in range(5):
            z = row['z'] + ln * LS
            cube(((x0s + x1s) / 2, WALL_Y - 0.004, z), (x1s - x0s, 0.004, 0.0045), ink)
        # system bracket and clef
        cube((x0s, WALL_Y - 0.004, row['z'] + 2 * LS), (0.006, 0.004, 4 * LS), ink)
        glyph = '\U0001D11E' if song['clef'] == 'treble' else '\U0001D122'
        clef_z = row['z'] + (1.81 * LS if song['clef'] == 'treble' else 2.6 * LS)
        text_obj(glyph, Vector((x0s + 0.12, WALL_Y - 0.008, clef_z)), 0.52 if song['clef'] == 'treble' else 0.24, ink)
        # key signature
        ks = song['keysig']
        sharp_steps, flat_steps = [8, 5, 9, 6, 3, 7, 4], [4, 7, 3, 6, 2, 5, 1]
        for q in range(abs(ks)):
            stp = (sharp_steps if ks > 0 else flat_steps)[q]
            accidental('♯' if ks > 0 else '♭', x0s + 0.27 + q * KS_DX, row['z'] + stp * LS / 2, ink)
        if row is sec_rows[s][0] and song.get('timesig'):
            n_, d_ = song['timesig']
            xt = x0s + 0.27 + abs(ks) * KS_DX + 0.06
            for dg, zz in ((n_, 3 * LS), (d_, 1 * LS)):          # each digit fills two spaces
                text_obj(str(dg), Vector((xt, WALL_Y - 0.008, row['z'] + zz - 0.008)), 0.265, ink)
    # bar lines: where the notated count crosses a whole bar
    bu, pu = song['bar_units'], song['pickup_units']
    if bu:
        hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
        acc = 0.0
        for j, h in enumerate(hs):
            nxt = hs[j + 1] if j + 1 < len(hs) else None
            acc2 = acc + h['nunit']
            if nxt is not None and int((acc2 - pu) // bu) > int((acc - pu) // bu):
                xa, xb = HEAD[h['i']][0].x, HEAD[nxt['i']][0].x
                if HEAD[h['i']][2] is HEAD[nxt['i']][2]:
                    xbar = bar_x(h, nxt)
                    rz = HEAD[h['i']][2]['z']
                    cube((xbar, WALL_Y - 0.004, rz + 2 * LS), (0.006, 0.004, 4 * LS), ink)
                else:                                   # the bar ends with the line: its bar line closes the line
                    rw = HEAD[h['i']][2]
                    cube((rw['x1'] - 0.003, WALL_Y - 0.004, rw['z'] + 2 * LS), (0.006, 0.004, 4 * LS), ink)
            acc = acc2
    # double bar at the end of the piece
    lr = sec_rows[s][-1]
    for dx, wd in ((0.0, 0.006), (0.03, 0.018)):
        cube((lr['x1'] - 0.03 + dx, WALL_Y - 0.004, lr['z'] + 2 * LS), (wd, 0.004, 4 * LS), ink)

# ---------------------------------------------------------------- 3. note heads, stems, ledger lines, accidentals
LIGHTS = []
for h in C:
    if h['mech'] == 'bigdrum':
        continue
    song = SONGS[h['s']]
    era = song['era']
    ink = ink_mat(page_of(song))
    head, st, row = HEAD[h['i']]
    pal_ = song.get('neon') or ERAS[era]['neon']
    neon = NEON[pal_[h['midi'] % len(pal_)]]
    if h['mech'] == 'again':
        m = bpy.data.materials.get(f'head{h["i"] - 1}')
        while m is None and h['i'] > 0:
            break
        if m:
            emit_keys(m, ((h['t'] - 1 / FPS, 1.5), (h['t'], 22.0), (h['t'] + 0.12, 6.0), (h['t'] + 0.4, 1.5)))
        burst(CON[h['i']] + Vector((0, -0.04, -R)), h['t'], neon, n=4, speed=0.6, life=0.25, size=0.006)
        continue
    pg = PAGE[page_of(song)]
    hm = mat(f'head{h["i"]}', pg['ink'], 0.12, metal=pg['ink_metal'] * 0.6, emit=neon, emit_s=0.0, coat=1.0)
    o = sphere(head, 1.0, hm, scale=R_HEAD, segs=32)
    o.rotation_euler = (0, math.radians(-20), 0)        # the slant of an engraved note head
    # stem (flat on the page): up on the right below the middle line, down on the left above it
    up = st < 4
    sx = head.x + (0.045 if up else -0.045)
    z0s = row['z'] + st * LS / 2
    stem_l = max(3.5 * LS, abs(st - 4) * LS / 2)          # two or more ledger lines: the stem reaches the middle line
    # halves and wholes are open heads (an ink ring round the paper); a whole note has no stem
    ts_, bu_ = song.get('timesig'), song.get('bar_units')
    nval = song.get('note_value', {}).get(h['j'], h['nunit'])          # written value, if not the time taken
    wu_ = bu_ * ts_[1] / ts_[0] if ts_ and bu_ else song.get('whole_units')     # units in a whole note
    frac = nval / wu_ if wu_ else 0.0
    if frac >= 0.5 - 1e-6:
        hole = sphere((0, 0, 0), 1.0, paper_mat(page_of(song)), scale=(0.58, 0.13, 0.46), segs=24)
        hole.parent = o                                   # in the head's own (unit-sphere) space
        hole.location, hole.rotation_euler = (0, -0.93, 0), (0, math.radians(-18), 0)
    base_ = frac / 1.5 if frac else 0.0                   # a dotted value: 1.5 times a plain note value
    if base_ and abs(math.log2(base_) - round(math.log2(base_))) < 1e-6:
        dz_ = LS / 2 if st % 2 == 0 else 0.0                # a note on a line takes its dot in the space above
        sphere((head.x + 0.085, WALL_Y - 0.008, z0s + dz_), 0.011, ink, segs=10)
    if frac < 1.0 - 1e-6:
        stem_o = cube((sx, WALL_Y - 0.006, z0s + (1 if up else -1) * stem_l / 2), (0.006, 0.004, stem_l), ink)
        wobble(stem_o, h['t'], axis=1, amp=2.2)
    cyl((head.x, WALL_Y, head.z), (head.x, head.y + 0.02, head.z), 0.006, ink, 8)          # the pin holding the head
    # ledger lines
    if st < -1 or st > 9:
        rng_ = range(-2, st - 1, -2) if st < -1 else range(10, st + 1, 2)
        for ls_ in rng_:
            cube((head.x, WALL_Y - 0.004, row['z'] + ls_ * LS / 2), (0.16, 0.004, 0.0045), ink)
    if h['acc']:
        accidental(h['acc'], head.x - 0.11, z0s, ink)
    if h['j'] in song.get('fermata', ()):
        fz = max(row['z'] + 4 * LS + 0.08, head.z + 0.15, z0s + stem_l + 0.08 if up else -1e9)   # clear of an up-stem
        text_obj('\U0001D110', Vector((head.x, WALL_Y - 0.008, fz)), 0.42, ink)
    # glow on the hit, and it stays softly lit: the played music remains on the page
    pk_ = 9.0 if page_of(song) in ('tm', 'classical', 'otj') else 6.0        # lighter pages take a brighter flash
    emit_keys(hm, ((h['t'] - 1 / FPS, 0.0), (h['t'], pk_), (h['t'] + 0.12, pk_ * 0.4), (h['t'] + 0.45, 1.5)))
    for u, k in ((-1 / FPS, 0), (0.04, 1), (0.16, -0.3), (0.3, 0)):
        o.location = head - Vector((0, 0, 0.012 * k))
        o.keyframe_insert('location', frame=fr(h['t'] + u))
    o.location = head
    tk = kick_time(h)
    if tk is not None and tk - 0.07 > h['t'] + 0.32:          # the held note presses down and flicks the ball on
        for u, k in ((-0.07, 0), (-0.02, 0.8), (0.05, -0.3), (0.16, 0)):
            o.location = head - Vector((0, 0, 0.010 * k))
            o.keyframe_insert('location', frame=fr(tk + u))
        o.location = head
    burst(CON[h['i']] + Vector((0, -0.04, -R)), h['t'], neon, n=6, speed=0.75, life=0.3, size=0.007)
    ld = bpy.data.lights.new(f'spill{h["i"]}', 'POINT')
    ld.color, ld.shadow_soft_size = neon, 0.04
    lo = bpy.data.objects.new(f'spill{h["i"]}', ld)
    sc.collection.objects.link(lo)
    lo.location = head + Vector((0, -0.10, 0.02))
    for t_, e_ in ((h['t'] - 1 / FPS, 0.0), (h['t'], 0.0), (h['t'] + 0.25, 0.0)):
        ld.energy = e_
        ld.keyframe_insert('energy', frame=fr(max(0.0, t_)))
    # only exists while it glows (keeps ~250 lights out of the light tree), and only reaches nearby
    ld.use_custom_distance = True
    ld.cutoff_distance = 0.9
    key_vis(lo, h['t'] - 2 / FPS, h['t'] + 0.4)

# the opening: the ledge, the gate that holds the marble, the pendulum that counts in, the title on the page
M_LEDGE = mat('ledge', (0.85, 0.62, 0.28), 0.25, metal=1.0)
cyl(LEDGE_START - Vector((0.07, 0, R + 0.006)), LEDGE_END - Vector((-0.01, 0, R + 0.006)), 0.009, M_LEDGE, 12)
BALL_Y = LEDGE_START.y
for p_ in (LEDGE_START - Vector((0.05, 0, 0)), LEDGE_END):
    cyl((p_.x, WALL_Y, p_.z - R - 0.006), (p_.x, BALL_Y - 0.012, p_.z - R - 0.006), 0.006, M_LEDGE, 8)
cyl(LEDGE_START - Vector((R + 0.012, 0, R + 0.006)), LEDGE_START - Vector((R + 0.012, 0, -0.02)), 0.006, M_LEDGE, 10)  # back stop
GATE_H = 2 * R + 0.012          # clears the rail under it
gate = empty(LEDGE_START + Vector((R + 0.008, 0, R + 0.018)), 'gate_hinge')
cyl((gate.location.x, WALL_Y, gate.location.z), (gate.location.x, BALL_Y - 0.036, gate.location.z), 0.008, M_LEDGE, 12)
cyl((gate.location.x, BALL_Y - 0.036, gate.location.z), (gate.location.x, BALL_Y + 0.036, gate.location.z), 0.008, M_LEDGE, 16)
cyl((gate.location.x, BALL_Y + 0.066, LEDGE_START.z - R - 0.006), (gate.location.x, BALL_Y + 0.066, gate.location.z + 0.01),
    0.006, M_LEDGE, 10)                                              # the post, behind the marble's path
gate_plate = cube((0, 0, 0), (0.014, 0.06, GATE_H), M_LEDGE, bevel=0.002)
gate_plate.parent = gate
gate_plate.location = (0, 0, -GATE_H / 2)
for t_, a_ in ((0.0, 0.0), (T_GATE - 0.03, 0.0), (T_GATE + 0.09, -1.48), (T_GATE + 0.17, -1.30), (T_GATE + 0.25, -1.38)):
    gate.rotation_euler = (0, a_, 0)                 # swings up and away downhill, with a little bounce
    gate.keyframe_insert('rotation_euler', frame=fr(t_))
PEND_L = 9.81 * (2 * BEAT0 / (2 * math.pi)) ** 2    # half a swing per beat
PEND_A = 0.33
pend = empty(Vector((LEDGE_START.x - 0.19, WALL_Y - 0.035, LEDGE_START.z + PEND_L + 0.02)), 'pendulum')
cyl((pend.location.x, WALL_Y, pend.location.z), (pend.location.x, pend.location.y - 0.012, pend.location.z), 0.008, M_LEDGE, 16)
cyl((pend.location.x, WALL_Y, pend.location.z), (pend.location.x, WALL_Y - 0.008, pend.location.z), 0.045, M_LEDGE, 32)  # rosette
for o_ in (cyl((0, 0, 0), (0, 0, -PEND_L), 0.0035, M_LEDGE, 8),
           sphere((0, 0, -PEND_L), 0.052, M_LEDGE, scale=(1, 0.30, 1), segs=32)):
    o_.parent = pend
k_ = -int(C[0]['t'] / BEAT0) - 1                    # from before the first frame, so it is already swinging
while C[0]['t'] + k_ * BEAT0 <= T_END + BEAT0:      # at the far end of each swing, the tick
    pend.rotation_euler = (0, PEND_A * (1 if k_ % 2 else -1), 0)
    pend.keyframe_insert('rotation_euler', frame=fr(C[0]['t'] + k_ * BEAT0))
    k_ += 1
for fc_ in pend.animation_data.action.fcurves:
    for kp_ in fc_.keyframe_points:
        kp_.interpolation = 'BEZIER'
        kp_.handle_left_type = kp_.handle_right_type = 'AUTO_CLAMPED'
TITLE_X, TITLE_Z = X_LEFT + 1.30, ROWS[0]['z'] + 4 * LS + 0.80   # in the opening view, above the first row's framing
text_obj('300 Years of Music', Vector((TITLE_X, WALL_Y - 0.006, TITLE_Z)), 0.19, ink_mat(SONGS[0]['era']),
         font='/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf')
text_obj('one marble', Vector((TITLE_X, WALL_Y - 0.006, TITLE_Z - 0.16)), 0.10, ink_mat(SONGS[0]['era']),
         font='/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf')

# ---------------------------------------------------------------- 3b. practical lights of the era
M_BRASS8 = mat('brass8', (0.85, 0.62, 0.28), 0.25, metal=1.0)
for row in ROWS:
    era = SONGS[row['s']]['era']
    if era not in ('baroque', 'romantic'):
        continue
    p = Vector((X_LEFT + row['px'] - 0.34, 0.50, row['z'] + 0.52))
    cyl((p.x, WALL_Y, p.z - 0.10), (p.x, p.y, p.z - 0.10), 0.008, M_BRASS8, 10)          # wall arm
    cyl(p + Vector((0, 0, -0.12)), p + Vector((0, 0, -0.10)), 0.035, M_BRASS8, 24)         # drip tray
    ld = bpy.data.lights.new('practical', 'POINT')
    lo = bpy.data.objects.new('practical', ld)
    sc.collection.objects.link(lo)
    if era == 'baroque':
        cyl(p + Vector((0, 0, -0.10)), p + Vector((0, 0, 0.02)), 0.014, mat('wax', (0.92, 0.86, 0.72), 0.6), 16)
        flame = sphere(p + Vector((0, 0, 0.045)), 0.012, mat('flame', (1.0, 0.7, 0.3), 0.5, emit=(1.0, 0.62, 0.25), emit_s=14),
                       scale=(0.7, 0.7, 1.6), segs=12)
        ld.color, ld.shadow_soft_size, base_e = (1.0, 0.68, 0.35), 0.02, 6.0
        lo.location = p + Vector((0, -0.02, 0.05))
    else:
        sphere(p + Vector((0, 0, -0.02)), 0.05, mat('gasglobe', (1.0, 0.85, 0.6), 0.2, emit=(1.0, 0.7, 0.4), emit_s=8), segs=24)
        flame = None
        ld.color, ld.shadow_soft_size, base_e = (1.0, 0.74, 0.45), 0.05, 14.0
        lo.location = p + Vector((0, -0.04, -0.02))
    t_ = 0.0
    while t_ <= T_END:
        e_ = base_e * rng.uniform(0.82, 1.08) if era == 'baroque' else base_e * rng.uniform(0.95, 1.02)
        ld.energy = e_
        ld.keyframe_insert('energy', frame=fr(t_))
        if flame is not None:
            flame.scale = (0.7, 0.7, 1.6 * e_ / base_e)
            flame.keyframe_insert('scale', frame=fr(t_))
        t_ += 0.16

# ---------------------------------------------------------------- 4. carriage-return tubes
M_GLASS = mat('acrylic8', (0.92, 0.95, 1.0), 0.08, alpha=0.16)
for key, tube in RETURNS.items():
    pts = tube['pts'][1:]
    era = SONGS[C[key]['s']]['era']
    neon = NEON[ERAS[era]['neon'][0]]
    cone(pts[0] + Vector((0, 0, 0.035)), R + 0.010, R + 0.032, 0.06, M_BRASS8)     # small brass funnel
    for p, q in zip(pts[1:-1], pts[2:]):
        cyl(p, q, R + 0.008, M_GLASS, 28)
        sphere(p, R + 0.008, M_GLASS, segs=20)
    for k in range(1, 9):
        kk = k / 9
        p = poly_at(pts, kk)
        rm = mat('tubering', neon, 0.2, emit=neon, emit_s=0.6)
        torus(p, R + 0.011, 0.003, rm, rot=(0, math.radians(90), 0))
        # time when the ball passes (inverse of the ease)
        lo_, hi_ = 0.0, 1.0
        for _ in range(30):
            mid = (lo_ + hi_) / 2
            if ease(mid) < kk:
                lo_ = mid
            else:
                hi_ = mid
        tp = tube['t0'] + lo_ * (tube['t1'] - tube['t0'])
        emit_keys(rm, ((tp - 1 / FPS, 0.6), (tp, 30.0), (tp + 0.3, 1.5)))

# ---------------------------------------------------------------- 4b. the machines between pieces
def revolve(centre, profile, m, segs=48):
    """An open surface of revolution about a vertical axis through centre; profile = [(radius, z), ...]."""
    verts, faces = [], []
    for r_, z_ in profile:
        for k in range(segs):
            a = 2 * math.pi * k / segs
            verts.append((centre.x + r_ * math.cos(a), centre.y + r_ * math.sin(a), z_))
    for i in range(len(profile) - 1):
        for k in range(segs):
            a0, a1 = i * segs + k, i * segs + (k + 1) % segs
            faces.append((a0, a1, a1 + segs, a0 + segs))
    me = bpy.data.meshes.new('revolve')
    me.from_pydata(verts, [], faces)
    me.shade_smooth()
    me.materials.append(m)
    o = bpy.data.objects.new('revolve', me)
    bpy.context.collection.objects.link(o)
    return o


# the marble's colour in each piece (each against its page: cobalt on candlelit parchment, emerald in the organ
# loft, deep violet in the rose salon, gold in the night, orange in the storm, lime in the violet evening, teal
# on gold, cyan in the red hall); it takes each new one from the chase lamps on the way into the piece
PIECE_COL = {'canon': (0.10, 0.35, 1.0), 'toc': (0.02, 0.62, 0.32), 'tm': (0.30, 0.05, 0.55), 'ekn': (1.0, 0.72, 0.12),
             'b5': (1.0, 0.35, 0.06), 'fe': (0.62, 1.0, 0.15), 'otj': (0.0, 0.24, 0.29), 'mk': (0.15, 0.85, 1.0)}
from types import SimpleNamespace  # noqa: E402
M_CLEAR = mat('clearglass', (0.95, 0.97, 1.0), 0.04, alpha=0.07)
for s_, m_ in GAPMACH.items():
    HELP = SimpleNamespace(cube=cube, cyl=cyl, sphere=sphere, torus=torus, cone=cone, mat=mat, emit_keys=emit_keys, fr=fr,
                           revolve=revolve, glass=M_GLASS, clear=M_CLEAR, WALL_Y=WALL_Y,
                           neon=NEON[ERAS[SONGS[s_]['era']]['neon'][0]], chase=PIECE_COL[SONGS[s_]['key']])
    GD.build(m_, HELP)
    # the chase lamps along the last rail play a rising line that lands a step below the next piece's first
    # note, so the machine leads the ear into the music (a glockenspiel, in the bell's range)
    chase = sorted((x for x in m_.hits if x['kind'] == 'chase'), key=lambda x: x['t'])
    if chase:
        target = [h for h in C if h['s'] == s_ and h['mech'] != 'bigdrum'][0]['midi']
        while target < 84:
            target += 12
        steps = [2, 2, 1, 2, 2, 2, 1]                       # a major scale, walked down from the target
        m_note = target - 2
        line = []
        for k_ in range(len(chase)):
            line.append(m_note)
            m_note -= steps[k_ % len(steps)]
        for x, mi in zip(chase, reversed(line)):
            x['midi'] = mi

# ---------------------------------------------------------------- 4c. signature moments inside the pieces
# Each piece gets one thing of its own, always driven by the notes the marble plays:
#   Symphony No. 5   a drop hammer beside each long note: the three repeated notes ratchet it up, click by
#                    click, and the fourth brings it down (da-da-da-DUM), with lightning, thunder and a jolt
#   Rondo alla Turca a little Turkish drum at every bar line, struck on the downbeat (Mozart was imitating
#                    the Janissary band)
#   Eine kleine      fireworks on the top note of the rising arpeggio
#   Ode to Joy       little figures below the staff bounce on every beat
#   Toccata          organ pipes behind the line glow with each note
#   Fur Elise        a firefly rises from every note into the night-blue page
SIG_HITS, SHAKES = [], []
KEY_S = {song['key']: k for k, song in enumerate(SONGS)}


def notes_of(key):
    return [h for h in C if h['s'] == KEY_S.get(key) and h['mech'] != 'bigdrum']


def hammer_for(hits, k_strike, g=1.0):
    """A drop hammer beside note k_strike, cocked by the three notes before it. g: how hard (they build up).
    The weight hangs above the staff, right of the fermata, so nothing of the music is covered while it
    waits; each repeated note ratchets it up a notch, and on the long note it slams onto an anvil beside the
    head (the marble and the stem stay in view) and is winched straight back up."""
    hs = hits[k_strike]
    head, st, row = HEAD[hs['i']]
    yb = HEAD_Y - 0.13                                  # in front of the marble's plane, clear of it
    xh = head.x + 0.30                                  # beyond the return funnel at a line's end
    anvil = Vector((xh, yb, head.z - 0.035))
    z_land = anvil.z + 0.03 + 0.034                     # the weight's centre resting on the plate
    z_rest = row['z'] + 4 * LS + 0.19                   # above the staff and the fermata's arc
    hm_m = mat('hammer', (0.85, 0.62, 0.25), 0.25, metal=1.0)
    cyl(Vector((xh, yb + 0.03, anvil.z)), Vector((xh, yb - 0.03, anvil.z)), 0.03, M_BRASS, 24)   # a round brass plate
    hold = empty(Vector((xh, yb, z_rest)), 'hammer_weight')
    bpy.context.view_layer.update()
    wt = cyl(Vector((xh - 0.055, yb, z_rest)), Vector((xh + 0.055, yb, z_rest)), 0.034, hm_m, 24)
    rod = cyl(Vector((xh, yb, z_rest + 0.03)), Vector((xh, yb, z_rest + 0.13)), 0.005, M_BRASS, 8)   # a short stem
    eye = torus(Vector((xh, yb, z_rest + 0.15)), 0.018, 0.004, M_BRASS, rot=(math.radians(90), 0, 0))   # its ring
    for o in (wt, rod, eye):
        parent(o, hold)
    t_s = hs['t']
    cocks = [hits[k_strike - 3 + j]['t'] for j in range(3)]
    keys, dz = [(cocks[0] - 0.5, 0.0)], 0.0
    for tc in cocks:
        keys += [(tc - 0.01, dz), (tc + 0.05, dz + 0.045), (tc + 0.09, dz + 0.035)]
        dz += 0.035
        SIG_HITS.append(dict(t=tc + 0.04, kind='ratchet', g=1.0))
    drop = z_land - z_rest
    keys += [(t_s - 0.075, dz), (t_s, drop), (t_s + 0.05, drop + 0.025), (t_s + 0.10, drop), (t_s + 0.18, drop + 0.06),
             (t_s + 0.6, 0.0)]                          # it lifts off at once: the held note stays in view
    for tk, d_ in keys:
        hold.location = (xh, yb, z_rest + d_)
        hold.keyframe_insert('location', frame=fr(max(0.0, tk)))
    hit_p = Vector((xh, yb - 0.04, anvil.z + 0.03))
    pulse_ring(hit_p, t_s, NEON['amber'], r0=0.04, r1=0.13, life=0.3, rot=(0, 0, 0))
    burst(hit_p, t_s, (1.0, 0.8, 0.5), n=10, speed=1.0, life=0.4)
    SIG_HITS.append(dict(t=t_s, kind='thunder', g=g))
    SHAKES.append(t_s)
    return t_s


b5_ = notes_of('b5')
if b5_:
    # the three strikes build: thunder and flash at about 70 %, 84 % and 100 %
    STRIKE_G = {3: 0.71, 7: 0.84, 17: 1.0}
    strikes = [(hammer_for(b5_, k, STRIKE_G[k]), STRIKE_G[k]) for k in (3, 7, 17) if k < len(b5_)]
    ld = bpy.data.lights.new('lightning', 'AREA')
    ld.shape, ld.size, ld.size_y = 'RECTANGLE', 0.5, 3.0          # a tall window of light, low and to the side
    ld.color, ld.energy = (0.75, 0.85, 1.0), 0.0
    lo_ = bpy.data.objects.new('lightning', ld)
    sc.collection.objects.link(lo_)
    LIGHTNING_PEAK = float(os.environ.get('LIGHTNING_PEAK', 28.0))     # +45..60 levels at the peak, no white-out
    for t_s, g_ in strikes:
        hd_ = HEAD[[h for h in b5_ if h['t'] == t_s][0]['i']][0]
        e_ = LIGHTNING_PEAK * g_
        # it rakes across the wall from the left: the light slides right as it flares and dies
        for u, e, dx_ in ((-0.02, 0.0, -1.6), (0.0, e_, -1.4), (0.045, 0.75 * e_, -1.0), (0.12, 0.35 * e_, -0.4),
                          (0.22, 0.12 * e_, 0.2), (0.33, 0.0, 0.6)):
            ld.energy = e
            ld.keyframe_insert('energy', frame=fr(t_s + u))
            lo_.location = (hd_.x + dx_, -0.6, hd_.z + 0.5)
            lo_.rotation_euler = (math.radians(70), math.radians(-35), 0)   # grazing the wall
            lo_.keyframe_insert('location', frame=fr(t_s + u))
            lo_.keyframe_insert('rotation_euler', frame=fr(t_s + u))

tm_ = notes_of('tm')
if tm_:
    song_ = SONGS[KEY_S['tm']]
    bu, pu, pos_ = song_['bar_units'], song_['pickup_units'], 0.0
    drum_m = mat('davul', (0.55, 0.08, 0.06), 0.35, coat=0.6)
    DRUM_SKINS = []
    for j, h in enumerate(tm_[:-1]):
        nxt = tm_[j + 1]
        p2 = pos_ + h['nunit']
        if int((p2 - pu) // bu) > int((pos_ - pu) // bu) and HEAD[h['i']][2] is HEAD[nxt['i']][2]:
            xa, xb = HEAD[h['i']][0].x, HEAD[nxt['i']][0].x
            xbar = bar_x(h, nxt)
            rz = HEAD[h['i']][2]['z']
            dc = Vector((xbar, HEAD_Y - 0.03, rz - 0.21))
            HEAD[h['i']][2]['below'] = 0.36
            cyl(dc - Vector((0, 0, 0.045)), dc + Vector((0, 0, 0.045)), 0.075, drum_m, 28)
            sk_m = mat(f'davulskin{j}', (0.95, 0.9, 0.8), 0.5, emit=(1.0, 0.8, 0.5), emit_s=0.0)
            skin_o = cyl(dc + Vector((0, 0, 0.045)), dc + Vector((0, 0, 0.050)), 0.072, sk_m, 28)
            emit_keys(sk_m, ((nxt['t'] - 0.02, 0.0), (nxt['t'], 5.0), (nxt['t'] + 0.3, 0.0)))
            torus(dc + Vector((0, 0, 0.048)), 0.075, 0.006, M_BRASS)
            cyl(Vector((xbar, WALL_Y, rz - 0.25)), Vector((xbar, HEAD_Y - 0.03, rz - 0.25)), 0.007, M_BRASS, 8)
            piv = dc + Vector((0.15, 0, 0.15))
            hold = empty(piv, 'mallet')
            bpy.context.view_layer.update()
            o1 = cyl(piv, dc + Vector((0.015, 0, 0.07)), 0.005, mat('stick', (0.4, 0.25, 0.1), 0.4), 8)
            o2 = sphere(dc + Vector((0.015, 0, 0.07)), 0.022, mat('malletball', (0.95, 0.9, 0.8), 0.5))
            for o in (o1, o2):
                parent(o, hold)
            tb = nxt['t']
            for u, a_ in ((-0.35, 0.0), (-0.12, 28.0), (0.0, -2.0), (0.06, 6.0), (0.2, 0.0)):
                hold.rotation_euler = (0, math.radians(-a_), 0)
                hold.keyframe_insert('rotation_euler', frame=fr(tb + u))
            SIG_HITS.append(dict(t=tb, kind='davul', g=1.0))
            DRUM_SKINS.append((skin_o, tb))
        pos_ = p2

ekn_ = notes_of('ekn')
if len(ekn_) > 8:
    top = ekn_[8]                                       # D6, the top of the rising arpeggio
    hd_, rz_ = HEAD[top['i']][0], HEAD[top['i']][2]['z']
    # the note sends up four rockets that fan out and burst across the night sky above the staff, one after
    # another (no flat ring over the music: these are in the world, above it)
    for k_, (dx_, dz_, dt_, col_) in enumerate(((-0.60, 0.70, 0.32, 'magenta'), (0.40, 0.74, 0.42, 'cyan'),
                                                (-0.10, 0.78, 0.55, 'amber'), (0.85, 0.68, 0.68, 'lime'))):
        t0_ = top['t'] + 0.04 * k_
        p0_ = hd_ + Vector((0, -0.06, 0.06))
        p1_ = Vector((hd_.x + dx_, HEAD_Y - 0.10, rz_ + dz_))
        rk_ = sphere(p0_, 0.010, mat(f'rocket{k_}', NEON[col_], 0.3, emit=NEON[col_], emit_s=20), segs=8)
        key_vis(rk_, t0_, top['t'] + dt_)
        for u_ in (0.0, 0.33, 0.66, 1.0):                # an arc that slows as it climbs
            tt_ = t0_ + (top['t'] + dt_ - t0_) * u_
            rk_.location = p0_.lerp(p1_, 1 - (1 - u_) ** 2) + Vector((0, 0, 0.05 * math.sin(math.pi * u_)))
            rk_.keyframe_insert('location', frame=fr(tt_))
        shell(p1_, top['t'] + dt_, NEON[col_], r=0.17 + 0.03 * (k_ % 2))
        shell(p1_, top['t'] + dt_ + 0.06, NEON['white'], n=10, r=0.08, life=0.6, size=0.005)
        SIG_HITS.append(dict(t=top['t'] + dt_, kind='sparkle', g=0.30 + 0.08 * (k_ % 2)))   # under the music
    SIG_HITS.append(dict(t=top['t'], kind='whoosh', g=0.3, L=0.5))

otj_ = notes_of('otj')
DANCERS = []
if otj_:
    rows_ = []
    for h in otj_:
        r_ = HEAD[h['i']][2]
        if r_ not in rows_:
            rows_.append(r_)
    looks = [((0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears'), ((0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo'),
             ((0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna')]
    for r_ in rows_:
        xs_ = [HEAD[h['i']][0].x for h in otj_ if HEAD[h['i']][2] is r_]
        for k, fx in enumerate((0.2, 0.55, 0.88)):
            x_ = xs_[0] + (xs_[-1] - xs_[0]) * fx
            bc, ic, acc = looks[k % 3]
            ch = character(x_, r_['z'] + 0.03, bc, ic, acc, f'dancer{len(DANCERS)}', smile=True)
            r_['below'] = 0.70                     # their feet (0.46 below the staff) clear of the timeline band
            DANCERS.append((ch, [h for h in otj_ if HEAD[h['i']][2] is r_], k))

fe_ = notes_of('fe')                              # Fur Elise: a firefly rises from every note it plays
FF_LIFE = 6.0                                     # they linger, so the sky fills as the piece goes on
for j, h in enumerate(fe_):
    head = HEAD[h['i']][0]
    for n_ in range(3 if h['dur'] > 0.5 else 2):  # two from every note, three from the long ones
        col_ = (1.0, 0.78, 0.30) if (j + n_) % 2 else (1.0, 0.66, 0.24)     # warm amber only (the marble is lime)
        fm_ = mat(f'firefly{j}_{n_}', col_, 0.3, emit=col_, emit_s=0.0)
        t0_ = h['t'] + 0.10 * n_
        o = sphere(head + Vector((0.0, -0.03, 0.10)), 0.016, fm_, segs=12)
        key_vis(o, t0_, t0_ + FF_LIFE)
        sway, ph_ = 0.08 * (1 if (j + n_) % 2 else -1), rng.uniform(0, 3)
        z0_, rise_ = rng.uniform(0.05, 0.20), rng.uniform(0.28, 0.56)      # scattered: never a neat row of dots
        for k in range(13):
            u = k / 12
            o.location = head + Vector((sway * math.sin(u * 7 + ph_) + 0.07 * (n_ - 0.5), -0.03 - 0.08 * u,
                                        z0_ + rise_ * u ** 0.8))
            o.keyframe_insert('location', frame=fr(t0_ + FF_LIFE * u))
        # it blinks as it drifts up (on for a moment, dim, on again), then fades
        bl_, tb_, on_ = [(t0_, 0.0), (t0_ + 0.12, 14.0)], t0_ + 0.12, True
        while tb_ < t0_ + FF_LIFE - 0.6:
            tb_ += rng.uniform(0.3, 0.6)
            on_ = not on_
            bl_.append((tb_, (13.0 if on_ else 2.0) * (1 - 0.5 * (tb_ - t0_) / FF_LIFE)))
        bl_.append((t0_ + FF_LIFE, 0.0))
        emit_keys(fm_, bl_)

# era atmosphere: dust drifting in the candlelight of the baroque pages; a red spotlight sweeping the last page
bq_ = [h for h in C if h['mech'] != 'bigdrum' and SONGS[h['s']]['era'] == 'baroque']
if bq_:
    xs_ = [HEAD[h['i']][0].x for h in bq_]
    zs_ = [HEAD[h['i']][0].z for h in bq_]
    t_a, t_b = 0.0, bq_[-1]['t'] + 6.0
    dust_m = mat('dust', (1.0, 0.85, 0.6), 0.5, emit=(1.0, 0.8, 0.5), emit_s=1.5)
    rd = random.Random(5)
    for k in range(140):
        p0 = Vector((rd.uniform(min(xs_) - 1.0, max(xs_) + 1.0), rd.uniform(0.05, 0.48), rd.uniform(min(zs_) - 0.8, max(zs_) + 0.9)))
        drift = Vector((rd.uniform(-0.12, 0.12), rd.uniform(-0.03, 0.03), rd.uniform(-0.05, 0.10)))
        o = sphere(p0, rd.uniform(0.0012, 0.0026), dust_m, segs=6)
        for tt, f_ in ((t_a, 0.0), (t_b, 1.0)):
            o.location = p0 + drift * (f_ * (t_b - t_a) / 10.0)
            o.keyframe_insert('location', frame=fr(tt))
        try:                                       # an even drift (the layered-action API may differ)
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
        except AttributeError:
            pass
mk_ = notes_of('mk')
if mk_:
    sp_ = bpy.data.lights.new('redspot', 'SPOT')
    sp_.color, sp_.energy, sp_.spot_size, sp_.spot_blend = (1.0, 0.48, 0.38), 200.0, math.radians(34), 1.0
    so_ = bpy.data.objects.new('redspot', sp_)
    sc.collection.objects.link(so_)
    xm = [HEAD[h['i']][0].x for h in mk_]
    zm = sum(HEAD[h['i']][0].z for h in mk_) / len(mk_)
    so_.location = ((min(xm) + max(xm)) / 2, -1.6, zm + 1.6)
    t0m, t1m = mk_[0]['t'] - 2.0, mk_[-1]['t'] + 3.0
    mk_rets = sorted(RETURNS[i]['t1'] for i in RETURNS if C[i]['s'] == KEY_S['mk'])
    MK_PASSES = [mk_[0]['t']] + [min(h['t'] for h in mk_ if h['t'] > t_) for t_ in mk_rets]
    ph, tt = 0.0, t0m
    while tt <= t1m:                               # it rides with the marble, swaying faster each pass
        n_pass = sum(1 for tp_ in MK_PASSES if tt >= tp_)
        ph += 0.5 * (0.9, 0.9, 1.5, 2.3)[min(3, n_pass)]
        bx_ = sum(ball_pos(tt + d_).x for d_ in (-0.4, -0.2, 0.0, 0.2, 0.4)) / 5
        so_.location = (bx_, -1.6, zm + 1.6)
        so_.rotation_euler = (math.radians(52), math.radians(10) * math.sin(ph), 0)
        so_.keyframe_insert('rotation_euler', frame=fr(tt))
        so_.keyframe_insert('location', frame=fr(tt))
        tt += 0.5

toc_ = notes_of('toc')
for j, h in enumerate(toc_):
    head, st, row = HEAD[h['i']]
    ph = 0.10 + 0.010 * (h['midi'] - 48)              # higher notes, longer pipes
    foot = Vector((head.x, WALL_Y - 0.01, row['z'] + 4 * LS + 0.10))     # flat against the wall, behind the marble
    if h['j'] in SONGS[KEY_S['toc']].get('fermata', ()):                  # clear of the fermata over the note
        st_ = HEAD[h['i']][1]
        z0_ = row['z'] + st_ * LS / 2
        fz_ = max(row['z'] + 4 * LS + 0.08, head.z + 0.15,
                  z0_ + max(3.5 * LS, abs(st_ - 4) * LS / 2) + 0.08 if st_ < 4 else -1e9)
        foot.z = max(foot.z, fz_ + 0.12)
    # an organ flue pipe: a conical foot, the mouth (a dark slot with its upper lip), the body; half-metal with
    # a broad sheen and a soft glow (a mirror pipe that happens to face nothing bright reads as a black bar)
    pm = mat(f'pipe{j}', (0.85, 0.66, 0.3), 0.45, metal=0.5, emit=(1.0, 0.75, 0.4), emit_s=0.8)   # never a black bar
    cone(foot + Vector((0, 0, 0.018)), 0.004, 0.015, 0.036, pm, 16)
    cyl(foot + Vector((0, 0, 0.036)), foot + Vector((0, 0, 0.036 + ph)), 0.015, pm, 16)
    cube((foot.x, foot.y - 0.0145, foot.z + 0.050), (0.016, 0.004, 0.010), mat('pipemouth', (0.02, 0.015, 0.01), 0.6))
    cube((foot.x, foot.y - 0.0150, foot.z + 0.057), (0.018, 0.003, 0.003), pm)
    emit_keys(pm, ((h['t'] - 1 / FPS, 0.8), (h['t'], 3.0), (h['t'] + max(0.3, h['dur']), 1.0)))
    if os.environ.get('DEBUG_PIPES'):
        print('pipe', j, h['i'], h['midi'], round(h['t'], 2), round(h['dur'], 2), round(foot.x, 3), pm.name, flush=True)
        if os.environ['DEBUG_PIPES'] == 'paint':           # paint each pipe a different flat colour
            pm.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (j % 3 == 0, j % 3 == 1, j % 3 == 2, 1)
            for fc_ in (pm.node_tree.animation_data.action.fcurves if pm.node_tree.animation_data else []):
                for kp_ in fc_.keyframe_points:
                    kp_.co[1] = 4.0


# ---------------------------------------------------------------- 5. finale, characters
cyl((DRUM.x, HEAD_Y, DRUM.z - 0.12), (DRUM.x, HEAD_Y, DRUM.z), 0.2, mat('bigshell', (0.05, 0.05, 0.06), 0.25, coat=1.0), 48)
big_rim = mat('bigrim', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=4.0)
torus((DRUM.x, HEAD_Y, DRUM.z), 0.2, 0.012, big_rim)
big_head = mat('bighead', (0.95, 0.92, 0.85), 0.35, emit=(1.0, 0.5, 0.2), emit_s=0.0)
cyl((DRUM.x, HEAD_Y, DRUM.z), (DRUM.x, HEAD_Y, DRUM.z + 0.004), 0.186, big_head, 48)
emit_keys(big_rim, ((TF - 1 / FPS, 4.0), (TF, 36), (TF + 0.5, 8)))      # a flash, not a white-out of the marble
emit_keys(big_head, ((TF - 1 / FPS, 0.0), (TF, 12), (TF + 0.5, 1.5)))
cyl((DRUM.x, HEAD_Y, DRUM.z - 0.12), (DRUM.x, HEAD_Y, DRUM.z - 1.0), 0.04, mat('drumpole', (0.6, 0.45, 0.2), 0.3, metal=1.0))
pulse_ring(Vector((DRUM.x, HEAD_Y, DRUM.z + 0.01)), TF, NEON['amber'], r0=0.2, r1=0.85, life=0.5, rot=(0, 0, 0))
burst(Vector((DRUM.x, HEAD_Y - 0.04, DRUM.z + 0.02)), TF, NEON['amber'], n=18, speed=1.7, life=0.5)
# the launch cup at the end of the last row
cup_i = C[-2]['i']
cupc = CON[cup_i] - Vector((0, 0, R + 0.01))
cone(cupc, 0.03, 0.07, 0.05, mat('cup', (0.6, 0.45, 0.2), 0.3, metal=1.0))

chars = []
designs = [((0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears'), ((0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo'),
           ((0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna')]
for n_, (s, m_) in enumerate(sorted(GAPMACH.items()) if os.environ.get('WATCHERS') else []):
    bc, ic, acc = designs[n_ % 3]                 # (off: at the frame edge they read as stray assets)
    ch = character(X_LEFT - 0.55, m_.E_.z + 0.15, bc, ic, acc, f'watch{n_}')
    chars.append((ch, m_.t_kick))
yel = character(DRUM.x + 0.75, DRUM.z + 0.02, (0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo', 'yel')
pink = character(DRUM.x - 0.75, DRUM.z + 0.02, (0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears', 'pink')
catcher = None
if RESCUE:
    st_ = RESCUE['stand']
    catcher = character(st_.x, st_.z + 0.49, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'catcher', both=True)
    cube((st_.x, 0.30, st_.z - 0.012), (0.34, 0.40, 0.024), M_BRASS, bevel=0.006)       # its stand
    for sx in (-1, 1):
        cyl(Vector((st_.x + sx * 0.12, WALL_Y, st_.z - 0.03)), Vector((st_.x + sx * 0.12, 0.12, st_.z - 0.03)), 0.008, M_BRASS, 10)
for ch in [c for c, _ in chars] + [yel, pink] + ([catcher] if catcher else []) + [d for d, _, _ in DANCERS]:
    r0 = ch['root']
    holder = empty((r0.location.x, r0.location.y, r0.location.z - 0.49), r0.name + '_holder')
    bpy.context.view_layer.update()
    parent(r0, holder)
    sc_ = 0.32 if r0.name.startswith('dancer') else 0.50 if r0.name in ('yel', 'pink') else 0.62
    holder.scale = (sc_, sc_, sc_)
for ch, t_ev in chars:
    track_eyes(ch, ball_pos)
    mouth_o(ch, t_ev - 0.3, t_ev + 0.6, 1.7)
    hop(ch, t_ev + 0.05, 0.12)
for ch in (yel, pink):
    track_eyes(ch, ball_pos)
    mouth_o(ch, FIN['launch'] + 0.1, FIN['launch'] + 0.9, 1.5)
    hop(ch, TF + 0.02, 0.2)
    hop(ch, TF + 0.65, 0.12)
    mouth_o(ch, TF, TF + 1.8, 2.0)
# Ode to Joy: they dance to it. A small bob on every note; on beats 1, 2 and 3 of each bar pink, yellow and
# blue take a big hop in turn (a wave), on beat 4 all three; and all jump together when the answer pops
# (they cheer for the viewer) and on the last note of each line
beat_of, t_cheer = {}, None
if 'otj' in KEY_S:
    otj_all, pos_ = notes_of('otj'), 0.0
    bu_ = int(SONGS[KEY_S['otj']]['bar_units'] or 4)
    for h in otj_all:
        beat_of[h['i']] = int(round(pos_)) % bu_
        pos_ += h['nunit']
    t_cheer = otj_all[0]['t'] + 3.0                  # the quiz answer (overlay GUESS)
for ch, notes_, k_ in DANCERS:
    evs = {}
    for h in notes_:
        b_ = beat_of.get(h['i'], 0)
        evs[round(h['t'], 3)] = 0.25 if b_ == k_ else 0.18 if b_ == 3 else 0.08
    evs[round(notes_[-1]['t'], 3)] = 0.32
    if t_cheer is not None and notes_[0]['t'] - 0.2 <= t_cheer <= notes_[-1]['t'] + 0.5:
        evs[round(t_cheer, 3)] = 0.36
    for tb in sorted(evs):
        hop(ch, tb, evs[tb])
    track_eyes(ch, ball_pos)
if catcher:
    rs_ = RESCUE
    t0r, t1r, tcr, ttr = rs_['h0']['t'], rs_['h1']['t'], rs_['t_c'], rs_['t_t']
    track_eyes(catcher, ball_pos)
    mouth_o(catcher, t0r + 0.12, tcr + 0.25, 2.0)                     # it sees the marble fly off
    hop(catcher, tcr - 0.32, 0.10)                                     # jumps to catch it
    rr_ = catcher['root']
    for u, ang_ in ((-0.01, 0.0), (0.12, 0.16), (0.34, -0.13), (0.58, 0.09), (0.86, -0.04), (1.1, 0.0)):
        rr_.rotation_euler = (0, ang_, 0)                              # teeters with the weight in the net
        rr_.keyframe_insert('rotation_euler', frame=fr(tcr + u))
    hop(catcher, tcr + 0.45, 0.12)                                     # got it!
    hop(catcher, t1r + 0.04, 0.16)                                     # and cheers when it lands
    key_vis(catcher['mouth'], 0.0, tcr + 0.35)                         # the "o" gives way to a grin
    for b_ in catcher['beads']:
        key_vis(b_, tcr + 0.35)
    # a warm spot finds the catcher for its moment
    cs_ = bpy.data.lights.new('catcherspot', 'SPOT')
    cs_.color, cs_.spot_size, cs_.spot_blend, cs_.energy = (1.0, 0.86, 0.66), math.radians(30), 0.5, 0.0
    co_ = bpy.data.objects.new('catcherspot', cs_)
    sc.collection.objects.link(co_)
    co_.location = st_ + Vector((0.3, -1.6, 1.4))
    co_.rotation_euler = (st_ + Vector((-0.1, 0.0, 0.5)) - co_.location).to_track_quat('-Z', 'Y').to_euler()
    for tt_, e_ in ((t0r - 0.1, 0.0), (t0r + 0.3, 140.0), (t1r + 0.6, 140.0), (t1r + 1.4, 0.0)):
        cs_.energy = e_
        cs_.keyframe_insert('energy', frame=fr(tt_))
    net_m = mat('netring', (0.85, 0.85, 0.9), 0.2, metal=1.0)
    ring_o = torus(Vector((0, 0, 0)), 0.085, 0.006, net_m)
    bag_o = revolve(Vector((0, 0, 0)), [(0.085, 0.0), (0.075, -0.035), (0.05, -0.07), (0.02, -0.09), (0.004, -0.095)],
                    mat('netbag', (0.95, 0.95, 0.92), 0.6, alpha=0.45), segs=32)
    handle_o = cyl(Vector((0, 0, -0.5)), Vector((0, 0, 0.5)), 0.006, mat('handle', (0.5, 0.3, 0.12), 0.4), 10)
    handle_o.rotation_mode = 'QUATERNION'

    def hand_at(t):
        return st_ + Vector((-0.08, 0.06, 0.30))
    f = max(1, int(fr(t0r - 0.8)))
    while f <= min(N, int(fr(t1r + 1.2))):
        t = (f - 1) / FPS
        rc = net_ring(t)
        tilt = -0.5 * smooth((t - ttr) / 0.12) * (1 - smooth((t - (ttr + 0.5)) / 0.5)) + 0.25 * smooth((t - (ttr - 0.3)) / 0.3) * (1 - smooth((t - ttr) / 0.08))
        for o in (ring_o, bag_o):
            o.location = rc
            o.rotation_euler = (0, tilt, 0)
            o.keyframe_insert('location', frame=f)
            o.keyframe_insert('rotation_euler', frame=f)
        hd = hand_at(t)
        d = rc - hd
        handle_o.location = (hd + rc) / 2
        handle_o.rotation_quaternion = d.to_track_quat('Z', 'Y')
        handle_o.scale = (1, 1, d.length)
        for path_ in ('location', 'rotation_quaternion', 'scale'):
            handle_o.keyframe_insert(path_, frame=f)
        f += 1
    t_clip = rs_['t_clip']
    burst(rs_['rim'] - Vector((0, 0.03, R)), t_clip, NEON['amber'], n=9, speed=0.8, life=0.35)
    RESCUE_HITS = [dict(t=t0r + 0.03, kind='whoosh', g=1.0, L=0.7), dict(t=t_clip, kind='clang', g=1.0),
                   dict(t=tcr, kind='land', g=0.5),
                   dict(t=tcr + 0.02, kind='net', g=1.0), dict(t=ttr - 0.28, kind='spring', g=0.5),
                   dict(t=ttr, kind='whoosh', g=0.8, L=0.45),
                   dict(t=tcr + 0.15, kind='timp_roll', g=1.0, L=t1r - 0.05 - (tcr + 0.15))]
else:
    RESCUE_HITS = []

t_c = TF + 0.9
for kk in range(90):
    cn = rng.choice(list(NEON))
    o = cube((0, 0, 0), (0.018, 0.004, 0.011), mat(f'conf{kk}', NEON[cn], 0.3, emit=NEON[cn], emit_s=rng.uniform(6, 14)))
    key_vis(o, t_c)
    v = Vector((rng.uniform(-1.4, 1.4), rng.uniform(-0.9, 0.1), rng.uniform(2.6, 4.6)))
    p0 = Vector((DRUM.x + rng.uniform(-0.1, 0.1), HEAD_Y - 0.05, DRUM.z + 0.05))
    sp = Vector((rng.uniform(-14, 14), rng.uniform(-14, 14), rng.uniform(-14, 14)))
    u = 0.0
    while t_c + u <= T_END + 0.2:
        drag = 1.0 - math.exp(-u * 1.6)
        o.location = p0 + v * (drag / 1.6) + Vector((0.08 * math.sin(u * 5 + kk), 0, -0.45 * u * u - 0.35 * u))
        o.rotation_euler = sp * u
        o.keyframe_insert('location', frame=fr(t_c + u))
        o.keyframe_insert('rotation_euler', frame=fr(t_c + u))
        u += 0.12

# ---------------------------------------------------------------- 6. the marble
core_m = bpy.data.materials.new('marble')
core_m.use_nodes = True
nt_ = core_m.node_tree
bsdf = nt_.nodes['Principled BSDF']
wave = nt_.nodes.new('ShaderNodeTexWave')
wave.wave_type = 'RINGS'
wave.inputs['Scale'].default_value = 2.6
wave.inputs['Distortion'].default_value = 11.0
# the marble takes the colour of each piece it plays, and on the final drum shows them all at once
ramp = nt_.nodes.new('ShaderNodeValToRGB')
PEARL = (0.86, 0.87, 0.92, 1)
els = ramp.color_ramp.elements
while len(els) < len(SONGS):
    els.new(0.5)
for k in range(len(SONGS)):
    els[k].position = k / len(SONGS)
ramp.color_ramp.interpolation = 'CONSTANT'          # on the drum: eight clean bands, not a pastel blend
nt_.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
glow = bsdf.inputs['Emission Strength']
starts = [[h for h in C if h['s'] == k][0]['t'] for k in range(len(SONGS))]
def piece_col(k):
    return (*PIECE_COL.get(SONGS[k]['key'], (1, 1, 1)), 1)


for j in range(len(SONGS)):
    els[j].color = piece_col(0)
    els[j].keyframe_insert('color', frame=fr(0.0))
for k, t_k in enumerate(starts[1:], start=1):
    # one marble all along, one colour at a time: it soaks up each new piece's colour from the chase lamps it
    # rolls past on the way in (a gradual change you can see happen); its swirl never changes
    ch_ = sorted(x['t'] for x in (GAPMACH[k].hits if k in GAPMACH else []) if x['kind'] == 'chase')
    a_, b_ = (ch_[0] - 0.05, ch_[-1] + 0.1) if len(ch_) >= 2 else (t_k - 0.4, t_k + 0.12)
    for j in range(len(SONGS)):
        for tt, c_ in ((a_, piece_col(k - 1)), (b_, piece_col(k))):
            els[j].color = c_
            els[j].keyframe_insert('color', frame=fr(tt))
# ...and on the final drum every colour it has carried comes back at once, one band each: 300 years in one marble
for j in range(len(SONGS)):
    for tt, c_ in ((TF - 1 / FPS, piece_col(len(SONGS) - 1)), (TF + 0.25, piece_col(j))):
        els[j].color = c_
        els[j].keyframe_insert('color', frame=fr(tt))
    for tt, g_ in ((max(0.0, t_k - 1 / FPS), 0.35 + 0.08 * k), (t_k + 0.05, 1.6), (t_k + 0.5, 0.35 + 0.08 * (k + 1))):
        glow.default_value = g_
        glow.keyframe_insert('default_value', frame=fr(tt))
for tt, g_ in ((TF - 1 / FPS, 0.99), (TF + 0.1, 1.3), (TF + S.FINALE['hold'] + 0.6, 0.9)):   # the drum: it glows
    glow.default_value = g_
    glow.keyframe_insert('default_value', frame=fr(tt))
bsdf.inputs['Roughness'].default_value = 0.06
bsdf.inputs['Coat Weight'].default_value = 1.0
ball = sphere((0, 0, 0), R, core_m, segs=40)
spin, prev = 0.0, ball_pos(0.0)
for f in range(1, N + 1):
    t = (f - 1) / FPS
    p = ball_pos(t)
    spin -= (p.x - prev.x) / R                  # it turns the way it travels (rolling on the rails)
    prev = p
    ball.location = p
    ball.keyframe_insert('location', frame=f)
    ball.rotation_euler = (0, spin, 0)
    ball.keyframe_insert('rotation_euler', frame=f)

# a follow-spot from above the camera's left shoulder: a soft pool of light that travels with the marble and
# throws its shadow on the page, so the hero is always the brightest, clearest thing in the frame
fsd = bpy.data.lights.new('followspot', 'SPOT')
fsd.spot_size, fsd.spot_blend, fsd.shadow_soft_size, fsd.color = math.radians(17), 1.0, 0.05, (1.0, 0.97, 0.92)
follow = bpy.data.objects.new('followspot', fsd)
sc.collection.objects.link(follow)
FOLLOW_OFF = Vector((-0.7, -2.4, 1.5))
for f in range(1, N + 1, 2):
    t = (f - 1) / FPS
    p = ball_pos(t)
    follow.location = p + FOLLOW_OFF
    follow.rotation_euler = (-FOLLOW_OFF).to_track_quat('-Z', 'Y').to_euler()
    follow.keyframe_insert('location', frame=f)
    follow.keyframe_insert('rotation_euler', frame=f)

# ---------------------------------------------------------------- 7. camera: reads the score like a page
bpy.ops.object.camera_add(location=(0, -4, 0))
cam = bpy.context.object
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 5.0
cam.data.clip_end = 400.0                 # the closing shot of the whole wall is far back
sc.camera = cam
focus_empty = empty((0, HEAD_Y - 0.02, 0), 'focus')
cam.data.dof.focus_object = focus_empty   # focus rides with the marble on the note-head plane
OFF = Vector((0.20, -1.95, 0.16)) * 1.3     # wide enough that a pan crosses the frame in about 3 s


def row_at(t):
    for h0, h1 in zip(C[:-1], C[1:]):
        if h0['t'] <= t <= h1['t']:
            if h0['i'] in HEAD and h1['i'] in HEAD and HEAD[h0['i']][2] is HEAD[h1['i']][2]:
                return HEAD[h0['i']][2]
            return None
    return None


VIEW_H = 2 * OFF.length * 10.125 / 50.0        # visible height on the head plane at the base distance (50 mm)


# while a quiz card is up (top right: from LEAD before the first note until the answer leaves, as in
# overlay.py) the framing keeps room above the music, so the card never lies over the staff
CARD_PAD = 0.26
CARDS = []
for k_, song_ in enumerate(SONGS):
    hs_ = [h for h in C if h['s'] == k_ and h['mech'] != 'bigdrum']
    t0_ = hs_[0]['t']
    CARDS.append((t0_ - (0.15 if k_ == 0 else 1.2), t0_ + min(6.0, hs_[-1]['t'] - t0_ - 0.2)))


def card_up(tt):
    return max([smooth((tt - (a_ - 0.5)) / 0.5) * (1 - smooth((tt - b_) / 0.5)) for a_, b_ in CARDS] + [0.0])


def local_frame(r_, tt):
    """Vertical centre and zoom for the stretch of the row on screen around time tt: the staff, the notes
    in view (and just ahead), and the highest hop above them (and room for the quiz card while it is up)."""
    lo_, hi_ = r_['z'] - r_.get('below', 0.05), r_['z'] + 4 * LS + 0.05
    for h in r_['notes']:
        if tt - 1.1 <= h['t'] <= tt + 1.7:
            z, st_ = HEAD[h['i']][0].z, HEAD[h['i']][1]
            T_ = C[h['i'] + 1]['t'] - h['t']
            apex = G / 8 * min(T_, T_HOP) ** 2                 # the hop that leaves this note
            lo_ = min(lo_, z - R_HEAD[2] - 0.07)
            hi_ = max(hi_, z + R_HEAD[2] + 2 * R + apex + 0.03, z + 3.5 * LS + 0.03 if st_ < 4 else z)
    hi_ += CARD_PAD * card_up(tt)
    return (lo_ + hi_) / 2, max(1.0, (hi_ - lo_) / (0.86 * VIEW_H))


def row_x(r_, tt):
    """The music's position along a row at time tt: from head to head at an even pace."""
    ns = r_['notes']
    for a_, b_ in zip(ns[:-1], ns[1:]):
        if a_['t'] <= tt <= b_['t']:
            xa, xb = HEAD[a_['i']][0].x, HEAD[b_['i']][0].x
            return xa + (xb - xa) * (tt - a_['t']) / max(1e-6, b_['t'] - a_['t'])
    return HEAD[ns[-1]['i']][0].x if tt > ns[-1]['t'] else HEAD[ns[0]['i']][0].x


V_REF = 0.70     # the fastest the score may slide past (metres per second at the base framing)
MACH_ZOOM = 1.15 # a little wider while the marble runs through a machine (closer than before: it was lost)


def row_point(r_, tt):
    """Look-at point and zoom on a row. When the music runs fast the camera pulls back a little, so the
    page never slides past faster than V_REF (Mountain King's accelerando opens the view as it speeds up)."""
    zc_, zoom_ = local_frame(r_, tt)
    v_ = (row_x(r_, tt + 0.6) - row_x(r_, tt - 0.6)) / 1.2
    return Vector((row_x(r_, tt), HEAD_Y, zc_)), max(zoom_, min(1.6, v_ / V_REF)) * SONGS[r_['s']].get('frame_zoom', 1.0)


_POS = {h['i']: k for k, h in enumerate(C)}
RET_PAIRS = [(C[_POS[i]], C[_POS[i] + 1], r['row_from'], r['row_to'], r['t0']) for i, r in RETURNS.items()]


def frame_point(tt):
    """Where the camera wants to look at time tt: on a row, the music's position and the middle of the
    notes in view. While the ball is in a tube (a carriage return, or the way to the next page), the camera
    eases from the end of one row to the start of the next, pulling back a little on the way, so it is
    settled before the next note."""
    if tt <= C[0]['t']:
        return (*row_point(ROWS[0], C[0]['t']), (0.0, 0.0))
    for h0, h1, r0, r1, t_ret in RET_PAIRS:
        # a carriage return: from the row's last bars the view opens to hold the row end and the next row's
        # start together, so the ride through the tube crosses the frame, then closes in on the new row
        # (after a long last note, not before the ride: the held note is seen close)
        a_, b_ = max(h0['t'] - 0.5, t_ret - 0.6), h1['t'] + 0.35
        if a_ <= tt <= b_:
            pa, za = row_point(r0, h0['t'])
            pb, zb = row_point(r1, h1['t'])
            zfit = min(2.4, max(1.0, (abs(pa.x - pb.x) + 1.0) / (VIEW_H * 16 / 9), (abs(pa.z - pb.z) + 0.9) / VIEW_H))
            u = min(1.0, (tt - a_) / max(1e-6, h1['t'] - 0.2 - a_))
            w = math.sin(math.pi * u)                    # the bump is over 0.2 s before the first note
            ub = smooth(min(1.0, (tt - a_) / max(1e-6, h1['t'] - 0.3 - a_)))   # at the line start 0.3 s early
            base, zbase = pa.lerp(pb, ub), za + (zb - za) * ub
            return base.lerp(pa.lerp(pb, 0.55), w), zbase + (zfit - zbase) * w, (0.0, 0.0)
    for h0, h1 in zip(C[:-1], C[1:]):
        if h0['t'] <= tt <= h1['t']:
            if RESCUE and h0 is RESCUE['h0']:
                return rescue_view(tt)
            if h0['s'] != h1['s'] and h1['s'] in GAPMACH:       # a machine: follow the marble through it
                m_ = GAPMACH[h1['s']]
                x0_, x1_, z0_, z1_ = m_.box               # first, the whole machine: what is it going to do?
                wide = Vector(((x0_ + x1_) / 2, HEAD_Y, (z0_ + z1_) / 2))
                zw = min(3.2, max(1.4, (x1_ - x0_ + 0.5) / (VIEW_H * 16 / 9), (z1_ - z0_ + 0.45) / VIEW_H))
                # the pull-back starts on the piece's last hit (not before), holds, then follows the marble
                w = smooth((tt - (h0['t'] + 0.2)) / 1.6) * (1 - smooth((tt - (h0['t'] + 2.0)) / 0.8))
                w *= 1 - m_.closeness(tt)                 # a close-up (the loop, the rim) wins over the wide view
                zf_ = m_.zoom(tt, MACH_ZOOM)
                att, zz = m_.attention(tt).lerp(wide, w), zf_ + (zw - zf_) * w
                el_, yw_ = m_.elev(tt) * (1 - w), m_.yaw(tt)
                # and it arrives settled: the next piece's first-note framing (a little wider and higher, to
                # take the marble's drop in) is reached before the first note plays
                ka = smooth((tt - (h1['t'] - 1.5)) / 1.1)
                pb, zb = row_point(HEAD[h1['i']][2], h1['t'])
                p_, z_ = att.lerp(pb + Vector((0, 0, 0.12)), ka), zz + (zb * 1.2 - zz) * ka
                # ...but never so far ahead that the marble leaves the frame: keep it in the middle 70%
                bp_ = m_.pos(tt)
                hw_, hh_ = 0.35 * VIEW_H * 16 / 9 * z_, 0.35 * VIEW_H * z_
                p_ = Vector((min(max(p_.x, bp_.x - hw_), bp_.x + hw_), p_.y, min(max(p_.z, bp_.z - hh_), bp_.z + hh_)))
                return (p_, z_, (el_ * (1 - ka), yw_ * (1 - ka)))
            r0 = HEAD[h0['i']][2]
            r1 = HEAD[h1['i']][2] if h1['i'] in HEAD else r0
            if r1 is r0:
                p_, z_ = row_point(r0, tt)
                arrived = r0.get('first') and r0['s'] in GAPMACH
                if arrived or r0.get('after_return'):     # just arrived: still at the first hit, then away
                    t1st = r0['notes'][0]['t']
                    lift_, zm_ = (0.12, 1.2) if arrived else (0.0, 1.0)
                    k_ = smooth((tt - t1st) / (1.2 if arrived else 0.9))
                    if k_ < 1:
                        pa, za = row_point(r0, t1st)
                        p_, z_ = (pa + Vector((0, 0, lift_))).lerp(p_, k_), za * zm_ + (z_ - za * zm_) * k_
                return (p_, z_, (0.0, 0.0))
            k = smooth((tt - h0['t']) / (h1['t'] - h0['t']))
            pa, za = row_point(r0, h0['t'])
            pb, zb = row_point(r1, h1['t'])
            return pa.lerp(pb, k), (za + (zb - za) * k) * (1 + 0.25 * math.sin(math.pi * k)), (0.0, 0.0)
    return (*row_point(ROWS[-1], C[-2]['t']), (0.0, 0.0))


BREATHS = []                                        # (from, to, zoom factor, lift): the camera eases out
for k_, song_ in enumerate(SONGS):
    if song_.get('breath'):
        hs_ = [h for h in C if h['s'] == k_ and h['mech'] != 'bigdrum']
        BREATHS.append((hs_[song_['breath'][0]]['t'], hs_[song_['breath'][1]]['t'], 1.15, 0.12))
if RESCUE:                                          # Mountain King's last, fastest pass: wide and nearly still,
    BREATHS.append((RESCUE['h1']['t'] + 0.3, C[-2]['t'], 1.35, 0.0))   # so the speed reads against the frame


def target(t):
    """Smoothed look-at point and zoom: the pan is averaged over a wider window (an even glide through
    fast runs), the height and zoom over a narrower one."""
    px, wx, pz, zf, el, yw, wz = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    tight = 0.0                                   # through the rescue's catch and toss, follow the action closely
    if RESCUE:
        tight = smooth((t - (RESCUE['t_c'] - 0.6)) / 0.4) * (1 - smooth((t - (RESCUE['t_in'] + 0.1)) / 0.4))
    s1, s2 = 7.0 - 4.5 * tight, 5.0 - 3.0 * tight
    for j in range(-12, 13):
        p_, z_, (e_, y_) = frame_point(t + j * 0.08)
        w1, w2 = math.exp(-(j / s1) ** 2), math.exp(-(j / s2) ** 2)
        px, wx = px + p_.x * w1, wx + w1
        pz, zf, el, yw, wz = pz + p_.z * w2, zf + z_ * w2, el + e_ * w2, yw + y_ * w1, wz + w2
    # the music sits a little above the middle, so the timeline band at the bottom stays clear of it
    zf, pz = zf / wz, pz / wz - 0.05 * VIEW_H * zf / wz
    for a_, b_, zm_, dz_ in BREATHS:                # ease back (and look up a little), then settle again
        w_ = smooth((t - (a_ - 0.3)) / 1.0) * (1 - smooth((t - b_) / 1.2))
        zf, pz = zf * (1 + (zm_ - 1) * w_), pz + dz_ * w_
    return Vector((px / wx + 0.18, HEAD_Y, pz)), zf, (el / wz, yw / wx)


Z_FIRST, Z_LAST = ROWS[0]['z'] + 2 * LS, ROWS[-1]['z'] + 2 * LS
X_MID = (X_LEFT + max(r['x1'] for r in ROWS)) / 2
_RX = sorted(((r['z'] + 2 * LS, (X_LEFT + r['px'] + r['x1']) / 2) for r in ROWS))


def reveal_x(z):
    """Middle of the rows at height z, for the closing rise (pages may step to the right)."""
    if z <= _RX[0][0]:
        return _RX[0][1]
    for (za, xa), (zb, xb) in zip(_RX[:-1], _RX[1:]):
        if za <= z <= zb:
            return xa + (xb - xa) * smooth((z - za) / max(1e-6, zb - za))
    return _RX[-1][1]
FIN_ = S.FINALE
REVEAL_T0, REVEAL_T1, WIDE_T1 = TF + FIN_['rise0'], TF + FIN_['rise1'], TF + FIN_['wide1']
# the rise back through 300 years stops a beat on each piece's page (a blur of pages read as nothing): from
# the last row up to the first, easing between the page centres, moving 80 % of each step and resting 20 %
STOPS_Z = []
for k_ in range(len(SONGS) - 1, -1, -1):
    zs_ = [r_['z'] + 2 * LS for r_ in sec_rows[k_]]
    STOPS_Z.append(sum(zs_) / len(zs_))
STOPS_Z[0], STOPS_Z[-1] = Z_LAST, Z_FIRST


def rise_z(t):
    n = len(STOPS_Z) - 1
    u = (t - REVEAL_T0) / (REVEAL_T1 - REVEAL_T0) * n
    if u <= 0:
        return STOPS_Z[0]
    if u >= n:
        return STOPS_Z[-1]
    k = int(u)
    return STOPS_Z[k] + (STOPS_Z[k + 1] - STOPS_Z[k]) * smooth(min(1.0, (u - k) / 0.8))


def reveal_time(z):
    """When the rising camera's centre passes height z during the closing reveal."""
    t = REVEAL_T0
    while t < REVEAL_T1 and rise_z(t) < z:
        t += 0.01
    return t


# the last image: the whole wall, every page lit, the marble's path drawn on it; the wall left of centre and
# the closing card in the open gallery to its right
_wx0, _wx1 = X_LEFT - 0.4, max(max(r_['x1'] for r_ in ROWS), DRUM.x) + 0.6
_wz0, _wz1 = DRUM.z - 0.7, ROWS[0]['z'] + 4 * LS + 1.15
WIDE_H = (_wz1 - _wz0) * 1.06
WIDE_D = WIDE_H / (2 * 10.125 / 50.0)
WIDE_C = Vector(((_wx0 + _wx1) / 2 + 0.21 * WIDE_H * 16 / 9, HEAD_Y, (_wz0 + _wz1) / 2))
WIDE_OFF = Vector((0.0, -WIDE_D, 0.0))


# the payoff: as the camera rises back through the 300 years, every row it passes lights up again, a ripple
# from its first note to its last with a soft bell on the row's opening pitch, and stays lit, so the whole
# score glows in the colours of its eras by the time the camera is back at 1680
for row in ROWS:
    hs_ = [h for h in row['notes'] if h['mech'] != 'again']
    if not hs_:
        continue
    t_row = reveal_time(row['z'] + 2 * LS)
    xs_ = [HEAD[h['i']][0].x for h in hs_]
    for h in hs_:
        m_ = bpy.data.materials.get(f"head{h['i']}")
        if m_ is None:
            continue
        tr_ = t_row - 0.30 + 0.55 * (HEAD[h['i']][0].x - min(xs_)) / max(1e-6, max(xs_) - min(xs_))
        emit_keys(m_, ((tr_ - 1 / FPS, 1.5), (tr_, 28.0), (tr_ + 0.6, 9.0)))
    SIG_HITS.append(dict(t=t_row - 0.30, kind='bell', midi=max(72, min(96, hs_[0]['midi'] + 12)), g=0.45))


# ...and for the last, whole-wall image the marble's entire path is drawn on the wall, gate to drum, each
# piece's stretch (with the machine that carried the marble into it) in that piece's colour
def path_trail(k, t0, t1):
    pts = [ball_pos(t0 + j / FPS) for j in range(int((t1 - t0) * FPS) + 1)]
    cu = bpy.data.curves.new(f'trail{k}', 'CURVE')
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = '3D', 0.035, 2
    sp_ = cu.splines.new('POLY')
    sp_.points.add(len(pts) - 1)
    for p_, q_ in zip(sp_.points, pts):
        p_.co = (q_.x, q_.y - 0.02, q_.z, 1.0)
    col_ = PIECE_COL.get(SONGS[k]['key'], (1, 1, 1))
    tm_ = mat(f'trail{k}', col_, 0.4, emit=col_, emit_s=0.0)
    cu.materials.append(tm_)
    o = bpy.data.objects.new(f'trail{k}', cu)
    sc.collection.objects.link(o)
    key_vis(o, REVEAL_T1 - 0.1)
    emit_keys(tm_, ((REVEAL_T1, 0.0), (REVEAL_T1 + 1.6, 6.0), (T_END, 6.0)))


for k_ in range(len(SONGS)):
    hs_ = [h for h in C if h['s'] == k_ and h['mech'] != 'bigdrum']
    t_a = 0.0 if k_ == 0 else [h for h in C if h['s'] == k_ - 1 and h['mech'] != 'bigdrum'][-1]['t']
    path_trail(k_, t_a, TF if k_ == len(SONGS) - 1 else hs_[-1]['t'])


# the opening view: the whole top of the first page (candle, pendulum, gate, title, the first bars), then a
# slow push in that arrives on the first note's framing just after it plays
_ox0, _ox1 = X_LEFT - 0.42, max(CON[0].x + 0.85, TITLE_X + 0.80)
_oz0, _oz1 = ROWS[0]['z'] - 0.10, TITLE_Z + 0.14
OPEN_C = Vector(((_ox0 + _ox1) / 2, HEAD_Y, (_oz0 + _oz1) / 2))
OPEN_Z = max((_ox1 - _ox0) / (VIEW_H * 16 / 9), (_oz1 - _oz0) / VIEW_H)
OPEN_T1 = C[0]['t'] + 0.35
OPEN_YAW = 0.12


def cam_at(t):
    tg, zf, (el, yw) = target(t)
    if t < OPEN_T1:
        k = smooth((t - 0.6) / (OPEN_T1 - 0.6))        # hold the whole view a moment, then push in
        tg, zf, yw = OPEN_C.lerp(tg, k), OPEN_Z + (zf - OPEN_Z) * k, OPEN_YAW * (1 - k) + yw * k
    off = OFF * zf
    if el:                                       # rise and look down (into the funnel)
        rho, a0 = math.hypot(off.y, off.z), math.atan2(off.z, -off.y)
        off = Vector((off.x, -rho * math.cos(a0 + el), rho * math.sin(a0 + el)))
    if yw:                                       # swing round a little (the machine's depth shows)
        off = Vector((off.x * math.cos(yw) - off.y * math.sin(yw), off.x * math.sin(yw) + off.y * math.cos(yw), off.z))
    # the last leap: the drum framed (near the middle, clear of the HUD) before the marble lands on it
    kh = smooth((t - (C[-2]['t'] + 0.15)) / 0.7)
    tg = tg.lerp(CON[C[-2]['i']] * 0.35 + DRUM * 0.65 + Vector((0, 0, 0.22)), kh * (1 - smooth((t - (TF + 0.2)) / 0.8)))
    tg = tg.lerp(DRUM + Vector((0, 0, 0.12)), smooth((t - (TF + 0.1)) / 0.8))
    # after the drum: hold on the 8-colour marble, pull back to a page's height, then rise through the pages
    kb = smooth((t - (TF + FIN_['hold'])) / 1.4)
    off = off * (1 - 0.5 * smooth((t - (TF + 0.15)) / 0.6))     # in close on the 8-colour marble
    off = off.lerp(Vector((0.25, -9.0, 0.15)), kb)
    if t > REVEAL_T0:
        zr_ = rise_z(t)
        tg = Vector((reveal_x(zr_), YB, zr_))
    else:
        tg = tg.lerp(Vector((reveal_x(Z_LAST), YB, Z_LAST)), kb)
    kw = smooth((t - REVEAL_T1) / (WIDE_T1 - REVEAL_T1))     # ...and out to the whole wall, held to the end
    if kw > 0:
        tg, off = tg.lerp(WIDE_C, kw), off.lerp(WIDE_OFF, kw)
    for t_s in SHAKES:                           # the hammer's jolt
        u = t - t_s
        if 0.0 <= u < 0.45:
            amp = 0.022 * math.exp(-u * 9)
            tg = tg + Vector((amp * math.sin(u * 95), 0, amp * math.cos(u * 73)))
    return tg, off, 50.0


f = 1
while f <= N:
    t = (f - 1) / FPS
    tg, off, lens = cam_at(t)
    cam.location = tg + off
    cam.rotation_euler = (-off).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_euler', frame=f)
    cam.data.keyframe_insert('lens', frame=f)
    cam.data.dof.aperture_fstop = 5.0 + 5.0 * smooth((t - (TF + 1.0)) / 1.0)   # deeper focus for the wide reveal
    bp_ = ball_pos(t)
    focus_empty.location = (bp_.x, HEAD_Y - 0.02, bp_.z)
    focus_empty.keyframe_insert('location', frame=f)
    cam.data.dof.keyframe_insert('aperture_fstop', frame=f)
    f += 1 if any(-0.1 <= t - t_s < 0.5 for t_s in SHAKES) else 2      # every frame through a jolt

# a short shutter through the fast orbits the camera watches close (the funnel), the usual one elsewhere
SHARP = [w_ for m_ in GAPMACH.values() for w_ in m_.sharp]
if RESCUE:
    SHARP.append((RESCUE['h1']['t'], C[-2]['t']))     # the last pass: the marble's frantic hops, sharp
SHARP.append((REVEAL_T0 - 0.2, WIDE_T1))              # the rise: each page readable as it passes
for m_ in [SimpleNamespace(sharp=SHARP)]:
    for a_, b_ in m_.sharp:
        for tt_, sh_ in ((a_ - 0.4, 0.35), (a_ - 0.1, 0.12), (b_ + 0.1, 0.12), (b_ + 0.4, 0.35)):
            sc.render.motion_blur_shutter = sh_
            sc.keyframe_insert('render.motion_blur_shutter', frame=fr(tt_))
sc.render.motion_blur_shutter = 0.35

# ---------------------------------------------------------------- 8. light: each piece in its own light
# The camera only ever sees one page at a time, so the light is keyed in time: each piece has its own key
# (direction, colour, strength), fill and ambient, and the machine ride into a piece crossfades to it, so the
# marble arrives in a new room. Low-key where the era asks for it, so the glowing marble and notes carry
# the frame. After the final drum the light opens up to an even gallery light for the rise through 300 years.
LOOK = {   # key (strength, colour, direction to the light), fill (strength, colour), ambient (colour, strength)
    'canon': ((0.75, (1.0, 0.74, 0.46), (0.6, -1.0, 0.9)), (0.10, (1.0, 0.8, 0.6)), ((0.30, 0.20, 0.12), 0.10)),  # candlelight
    'toc': ((1.35, (1.0, 0.93, 0.82), (-0.5, -0.6, 1.6)), (0.06, (0.6, 0.7, 1.0)), ((0.10, 0.10, 0.16), 0.08)),   # organ loft
    'tm': ((1.3, (1.0, 0.86, 0.80), (0.5, -1.0, 1.0)), (0.30, (1.0, 0.80, 0.76)), ((0.55, 0.42, 0.42), 0.16)),    # salon
    'ekn': ((1.30, (0.70, 0.74, 1.0), (-0.4, -1.0, 1.2)), (0.26, (1.0, 0.74, 0.46)), ((0.10, 0.09, 0.22), 0.24)),  # moonlit night
    'b5': ((0.80, (0.80, 0.86, 1.0), (0.3, -1.0, 1.5)), (0.13, (0.62, 0.70, 0.90)), ((0.14, 0.16, 0.20), 0.13)),   # storm
    'fe': ((1.0, (1.0, 0.80, 0.84), (-0.9, -1.0, 0.45)), (0.25, (0.76, 0.68, 1.0)), ((0.12, 0.09, 0.16), 0.16)),   # dusk
    'otj': ((2.1, (1.0, 0.92, 0.74), (0.4, -1.0, 1.3)), (0.40, (0.85, 0.9, 1.0)), ((0.45, 0.45, 0.50), 0.30)),    # daylight
    'mk': ((1.15, (1.0, 0.64, 0.52), (-0.6, -1.0, 0.7)), (0.20, (1.0, 0.55, 0.45)), ((0.20, 0.07, 0.07), 0.18)),   # red hall
}
GALLERY = ((1.6, (1.0, 0.96, 0.9), (0.5, -1.0, 1.0)), (0.35, (0.9, 0.93, 1.0)), ((0.40, 0.40, 0.42), 0.22))
bpy.ops.object.light_add(type='SUN', location=(0, -3, 5))
sun = bpy.context.object
sun.data.angle = math.radians(20)
bpy.ops.object.light_add(type='SUN', location=(0, -3, 5))
fill = bpy.context.object
fill.data.angle = math.radians(40)
fill.rotation_euler = Vector((-0.8, 1.0, 0.1)).to_track_quat('-Z', 'Y').to_euler()
bg_ = world.node_tree.nodes['Background']


# the follow-spot's strength in each room (strong in the dark ones, a touch in the bright ones)
FOLLOW_E = {'canon': 40.0, 'toc': 52.0, 'tm': 36.0, 'ekn': 66.0, 'b5': 66.0, 'fe': 66.0, 'otj': 25.0, 'mk': 50.0}


def set_look(lk, t, key=None):
    fsd.energy = FOLLOW_E.get(key, 0.0)
    fsd.keyframe_insert('energy', frame=fr(t))
    (ke, kc, kd), (fe_, fc), (wc, ws) = lk
    sun.data.energy, sun.data.color = ke, kc
    sun.rotation_euler = (-Vector(kd)).to_track_quat('-Z', 'Y').to_euler()
    fill.data.energy, fill.data.color = fe_, fc
    bg_.inputs['Color'].default_value, bg_.inputs['Strength'].default_value = (*wc, 1), ws
    for o_, path_ in ((sun.data, 'energy'), (sun.data, 'color'), (sun, 'rotation_euler'), (fill.data, 'energy'),
                      (fill.data, 'color')):
        o_.keyframe_insert(path_, frame=fr(t))
    bg_.inputs['Color'].keyframe_insert('default_value', frame=fr(t))
    bg_.inputs['Strength'].keyframe_insert('default_value', frame=fr(t))


for k, song in enumerate(SONGS):
    hs_ = [h for h in C if h['s'] == k and h['mech'] != 'bigdrum']
    lk = LOOK.get(song['key'], GALLERY)
    if k == 0:
        set_look(lk, 0.0, song['key'])
    else:                                         # the ride into the piece is the change of room
        prev = [h for h in C if h['s'] == k - 1 and h['mech'] != 'bigdrum'][-1]
        set_look(LOOK.get(SONGS[k - 1]['key'], GALLERY), prev['t'] + 0.3, SONGS[k - 1]['key'])
        set_look(lk, hs_[0]['t'] - 0.2, song['key'])
MK_GAIN = (1.0, 1.3, 1.65)                        # Mountain King's light rises with each faster pass


def scaled_look(lk, g):
    (ke, kc, kd), (fe_, fc), (wc, ws) = lk
    return (ke * g, kc, kd), (fe_ * g, fc), (wc, ws * g)


if 'mk' in KEY_S and mk_:
    for n_, tp_ in enumerate(MK_PASSES[1:3], start=1):
        set_look(scaled_look(LOOK['mk'], MK_GAIN[n_ - 1]), tp_ - 0.4, 'mk')   # hold, then step up as it begins
        set_look(scaled_look(LOOK['mk'], MK_GAIN[n_]), tp_, 'mk')
set_look(scaled_look(LOOK.get(SONGS[-1]['key'], GALLERY), MK_GAIN[-1]), TF + 0.8, SONGS[-1]['key'])
set_look(GALLERY, TF + 2.6)                       # no follow-spot for the wide rise at the end
set_look(GALLERY, REVEAL_T1)
set_look((GALLERY[0], GALLERY[1], ((0.30, 0.30, 0.33), 0.07)), WIDE_T1)   # the wall glows in a darker gallery
sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = -0.3
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.03
sc.use_nodes = True
nt = sc.node_tree
gl = nt.nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.size = 6
if hasattr(gl, 'threshold'):
    gl.threshold = 2.0
nt.links.new(nt.nodes['Render Layers'].outputs['Image'], gl.inputs['Image'])
nt.links.new(gl.outputs['Image'], nt.nodes['Composite'].inputs['Image'])

if os.environ.get('DEBUG_PIPES') == 'keys':       # which action drives each pipe's glow, and its values
    for m_ in bpy.data.materials:
        if m_.name.startswith('pipe') and m_.node_tree and m_.node_tree.animation_data:
            act = m_.node_tree.animation_data.action
            vals = [round(kp.co[1], 2) for fc in act.fcurves for kp in fc.keyframe_points][:6] if act else None
            users = [mm.name for mm in bpy.data.materials if mm.node_tree and mm.node_tree.animation_data
                     and mm.node_tree.animation_data.action == act and mm is not m_][:4]
            print('pipe-mat', m_.name, act.name if act else None, vals, 'shared with', users, flush=True)
import json  # noqa: E402
ev_path = os.environ.get('EVENTS_OUT')
if ev_path:
    json.dump(dict(intro=dict(first=C[0]['t'], ticks=TICKS, gate=T_GATE, roll=[T_GATE, C[0]['t'] - T_HOP0, LEDGE_V]),
                   returns=[dict(t0=r['t0'], t1=r['t1']) for r in RETURNS.values()],
                   gaps=[], taps=TAPS, mhits=[x for m_ in GAPMACH.values() for x in m_.hits] + RESCUE_HITS + SIG_HITS,
                   mrolls=[x for m_ in GAPMACH.values() for x in m_.rolls]), open(ev_path, 'w'))
print('opening view zoom', round(OPEN_Z, 2), 'centre', tuple(round(v, 2) for v in OPEN_C), flush=True)
print('frames total', N, 'seconds', round(T_END, 2), 'rows', len(ROWS), 'objects', len(bpy.data.objects), flush=True)
print('line breaks', ' '.join(f"{SONGS[C[i]['s']]['key']}:{'bar' if r['at_bar'] else 'MID'}({r['width']:.1f})"
                              for i, r in RETURNS.items()), flush=True)
print('rescue', (RESCUE['h0']['t'], RESCUE['h1']['t'], tuple(round(v, 2) for v in RESCUE['stand'])) if RESCUE else None, flush=True)
print('zoom max', round(max(local_frame(r, h['t'])[1] for r in ROWS for h in r['notes']), 2), 'taps', len(TAPS), flush=True)
if os.environ.get('EVENTS_ONLY'):
    sys.exit(0)
if a.stills:
    for fs in a.stills.split(','):
        sc.frame_set(int(fs))
        sc.render.filepath = str(Path(a.out).resolve()) + f'{int(fs):04d}.png'
        bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = str(Path(a.out).resolve())
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    if a.frames:
        lo, hi = (int(v) for v in a.frames.split('-'))
        sc.frame_start, sc.frame_end = lo, hi
    bpy.ops.render.render(animation=True)
