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
sc.render.use_persistent_data = True
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
def character(x, z, body_col, iris_col, accent, name, eye_r=0.088):
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
    mouth = torus((x, -0.04, z + 0.0), 0.035, 0.007, mat(name + 'mouth', (0.15, 0.02, 0.05), 0.4),
                  rot=(math.radians(90), 0, 0))
    parts.append(mouth)
    for o in parts:
        parent(o, root)
    for o in irises:
        parent(o, look)
    return dict(root=root, look=look, mouth=mouth, z0=z)


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


# ================================================================ characters
def character(x, z, body_col, iris_col, accent, name, eye_r=0.088):
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
    mouth = torus((x, -0.04, z + 0.0), 0.035, 0.007, mat(name + 'mouth', (0.15, 0.02, 0.05), 0.4),
                  rot=(math.radians(90), 0, 0))
    parts.append(mouth)
    for o in parts:
        parent(o, root)
    for o in irises:
        parent(o, look)
    return dict(root=root, look=look, mouth=mouth, z0=z)


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
    'romantic': dict(paper=(0.28, 0.05, 0.07), ink=(0.95, 0.72, 0.30), ink_metal=1.0, rough=0.45),
    # pieces with a page of their own, so two pieces of one era never look alike
    'ekn': dict(paper=(0.12, 0.17, 0.26), ink=(0.88, 0.86, 0.78), ink_metal=0.6, rough=0.7),    # night blue
    'otj': dict(paper=(0.88, 0.76, 0.50), ink=(0.10, 0.07, 0.04), ink_metal=0.0, rough=0.85),   # sunlit gold
}
LS = 0.075               # staff line spacing (one step = LS / 2)
K_SP, GAP_MIN = 0.40, 0.14     # engraved spacing: the gap after a note grows with the square root of its value
ACC_PAD = 0.075                # extra room in front of a note that carries an accidental


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
for s, song in enumerate(SONGS):
    hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
    clef = song['clef']
    if s > 0:
        drop_ = 0.0
        if song.get('machine'):                # room for the machine that carries the marble here
            x_l = HEAD[[h for h in C if h['s'] == s - 1 and h['mech'] != 'bigdrum'][-1]['i']][0].x
            drop_ = max(MACH_DROP, GD.height_need(song['machine'], x_l + 0.14 - (X_LEFT + 0.58)) - 0.10)
        row_z -= ROW_H * 1.25 + drop_          # a new page starts lower
    row = dict(s=s, z=row_z, t0=hs[0]['t'], x0=X_LEFT + CLEF_W + (0.35 if s == 0 or True else 0), notes=[], first=True)
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
        if nxt is not None and h['dur'] >= 0.34 and (
                x - row['x0'] >= ROW_W and (at_bar or not bu) or x - row['x0'] >= ROW_W + ROW_EXTRA):
            # carriage return: into a funnel at the end of the row, along a glass tube, out at the next row
            row_z -= ROW_H
            new = dict(s=s, z=row_z, t0=nxt['t'], x0=X_LEFT + CLEF_W + KS_DX * abs(song['keysig']), notes=[], first=False)
            RETURNS[h['i']] = dict(t0=h['t'] + 0.10, t1=nxt['t'] - 0.16, row_from=row, row_to=new,
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
    sys.exit(0)


def tube_path(ret, h):
    """Polyline for a carriage return: drop into the funnel, run left under the staff, rise to the next row."""
    a = CON[h['i']]
    rf, rt = ret['row_from'], ret['row_to']
    zt_ = rf['z'] - 0.42
    pts = [a, Vector((a.x + 0.16, HEAD_Y, a.z - 0.10)), Vector((a.x + 0.22, HEAD_Y, zt_ + 0.05)), Vector((a.x + 0.12, HEAD_Y, zt_)),
           Vector((X_LEFT + 0.15, HEAD_Y, zt_)), Vector((X_LEFT + 0.05, HEAD_Y, zt_ - 0.10)),
           Vector((X_LEFT + 0.12, HEAD_Y, rt['z'] + 0.55))]
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
          f"spring waits {mk_.wait:.2f} s", flush=True)
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
    rs_['t_c'] = rs_['h0']['t'] + 0.72                                       # caught
    rs_['t_t'] = rs_['t_c'] + 0.95                                           # tossed back
    rs_['t_in'] = rs_['t_t'] + 0.45                                          # into the funnel
    rs_['ret']['t0'], rs_['ret']['t1'] = rs_['t_in'], rs_['h1']['t'] - 0.16  # the tube ride, as usual
    NET_LOW = rs_['stand'] + Vector((-0.20, 0.12, 0.30))
    NET_UP = rs_['stand'] + Vector((-0.34, 0.14, 0.76))


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
    if t <= rs['t_c']:
        return ballistic(CON[rs['h0']['i']], rs['h0']['t'], bag(rs['t_c']), rs['t_c'], t)
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
    mid = Vector((nc.x + 0.12, nc.y, rs['stand'].z + 0.42))      # the net and the whole catcher in view
    if t <= rs['t_c']:
        k = smooth((t - rs['h0']['t']) / (rs['t_c'] - rs['h0']['t']))
        return p0.lerp(mid, k) + Vector((0, 0, 0.25 * math.sin(math.pi * k))), 1.55, (0.0, 0.0)
    if t <= rs['t_t']:
        return mid, 1.38, (0.0, 0.0)
    fun = rs['ret']['pts'][1]
    if t <= rs['t_in']:
        k = smooth((t - rs['t_t']) / (rs['t_in'] - rs['t_t']))
        return mid.lerp(fun, k), 1.38 - 0.08 * k, (0.0, 0.0)
    k = smooth((t - rs['t_in']) / (rs['h1']['t'] - rs['t_in']))
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
                    return ballistic(p0, h0['t'], pts[1], tube['t0'], t)
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
    return m


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
        x0s, x1s = X_LEFT + 0.05, row['x1']
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
                    xbar = xb - min(0.09, (xb - xa) * 0.45)
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
    neon = NEON[ERAS[era]['neon'][h['midi'] % len(ERAS[era]['neon'])]]
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
    frac = h['nunit'] * ts_[0] / ts_[1] / bu_ if ts_ and bu_ else 0.0
    if frac >= 0.5 - 1e-6:
        hole = sphere((0, 0, 0), 1.0, paper_mat(page_of(song)), scale=(0.58, 0.13, 0.46), segs=24)
        hole.parent = o                                   # in the head's own (unit-sphere) space
        hole.location, hole.rotation_euler = (0, -0.93, 0), (0, math.radians(-18), 0)
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
    emit_keys(hm, ((h['t'] - 1 / FPS, 0.0), (h['t'], 9.0), (h['t'] + 0.12, 3.5), (h['t'] + 0.45, 1.5)))
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
    for t_, e_ in ((h['t'] - 1 / FPS, 0.0), (h['t'], 0.4), (h['t'] + 0.25, 0.0)):
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
    p = Vector((X_LEFT - 0.34, 0.50, row['z'] + 0.52))
    cyl((p.x, WALL_Y, p.z - 0.10), (p.x, p.y, p.z - 0.10), 0.008, M_BRASS8, 10)          # wall arm
    cyl(p + Vector((0, 0, -0.12)), p + Vector((0, 0, -0.10)), 0.035, M_BRASS8, 24)         # drip tray
    ld = bpy.data.lights.new('practical', 'POINT')
    lo = bpy.data.objects.new('practical', ld)
    sc.collection.objects.link(lo)
    if era == 'baroque':
        cyl(p + Vector((0, 0, -0.10)), p + Vector((0, 0, 0.02)), 0.014, mat('wax', (0.92, 0.86, 0.72), 0.6), 16)
        flame = sphere(p + Vector((0, 0, 0.045)), 0.012, mat('flame', (1.0, 0.7, 0.3), 0.5, emit=(1.0, 0.62, 0.25), emit_s=24),
                       scale=(0.7, 0.7, 1.6), segs=12)
        ld.color, ld.shadow_soft_size, base_e = (1.0, 0.68, 0.35), 0.02, 11.0
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


# the marble's colour in each piece (each against its page: cobalt on candlelit parchment, crimson in the organ
# loft, deep violet in the rose salon, gold in the night, orange in the storm, lime in the violet evening, teal
# on gold, cyan in the red hall); it takes each new one from the chase lamps on the way into the piece
PIECE_COL = {'canon': (0.10, 0.35, 1.0), 'toc': (0.9, 0.08, 0.12), 'tm': (0.30, 0.05, 0.55), 'ekn': (1.0, 0.72, 0.12),
             'b5': (1.0, 0.35, 0.06), 'fe': (0.62, 1.0, 0.15), 'otj': (0.0, 0.45, 0.48), 'mk': (0.15, 0.85, 1.0)}
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
#   Symphony No. 5   a hammer over each long note: the three repeated notes ratchet it up, click by click,
#                    and the fourth brings it down (da-da-da-DUM), with lightning, thunder and a jolt
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


def hammer_for(hits, k_strike):
    """A hammer over note k_strike, cocked by the three notes before it."""
    hs = hits[k_strike]
    head, st, row = HEAD[hs['i']]
    yb = HEAD_Y - 0.13                                  # in front of the marble's plane, clear of it
    anvil = Vector((head.x + 0.085, yb, head.z - 0.035))
    face = anvil + Vector((0, 0, 0.055))                 # where the mallet's centre is at the strike
    piv = Vector((head.x + 0.40, yb, head.z + 0.40))
    hm_m = mat('hammer', (0.85, 0.62, 0.25), 0.25, metal=1.0)
    cube((anvil.x, anvil.y, anvil.z), (0.05, 0.06, 0.03), mat('anvil', (0.15, 0.15, 0.17), 0.3, metal=0.9))
    cyl(Vector((piv.x, WALL_Y, piv.z)), piv, 0.008, M_BRASS, 10)                   # the bracket
    hold = empty(piv, 'hammer_pivot')
    bpy.context.view_layer.update()
    arm = cyl(piv, face, 0.007, mat('arm', (0.3, 0.18, 0.08), 0.4), 10)
    d_ = (face - piv).normalized()
    across = Vector((-d_.z, 0, d_.x)) * 0.06              # the head lies across the handle: a T seen from the front
    mallet = cyl(face - across, face + across, 0.03, hm_m, 20)
    for o in (arm, mallet):
        parent(o, hold)
    t_s = hs['t']
    cocks = [hits[k_strike - 3 + j]['t'] for j in range(3)]
    keys = [(cocks[0] - 0.5, 25.0)]
    ang = 25.0
    for tc in cocks:
        keys += [(tc - 0.01, ang), (tc + 0.05, ang + 17.0), (tc + 0.09, ang + 15.0)]
        ang += 15.0
        SIG_HITS.append(dict(t=tc + 0.04, kind='ratchet', g=1.0))
    keys += [(t_s - 0.075, ang), (t_s - 0.03, ang * 0.55), (t_s, 0.0), (t_s + 0.05, 7.0), (t_s + 0.11, 0.0),
             (t_s + 0.9, 0.0), (t_s + 1.6, 25.0)]
    for tk, a_ in keys:
        hold.rotation_euler = (0, math.radians(a_), 0)
        hold.keyframe_insert('rotation_euler', frame=fr(max(0.0, tk)))
    pulse_ring(Vector((face.x, yb - 0.02, face.z - 0.03)), t_s, (0.7, 0.85, 1.0), r0=0.05, r1=0.5, life=0.4, rot=(0, 0, 0))
    burst(Vector((face.x, yb - 0.02, face.z - 0.03)), t_s, (0.8, 0.9, 1.0), n=14, speed=1.3, life=0.45)
    SIG_HITS.append(dict(t=t_s, kind='thunder', g=1.0))
    SHAKES.append(t_s)
    return t_s


b5_ = notes_of('b5')
if b5_:
    strikes = [hammer_for(b5_, k) for k in (3, 7, 17) if k < len(b5_)]
    page_z = HEAD[b5_[0]['i']][2]['z']
    ld = bpy.data.lights.new('lightning', 'AREA')
    ld.color, ld.size, ld.energy = (0.75, 0.85, 1.0), 5.0, 0.0
    lo_ = bpy.data.objects.new('lightning', ld)
    sc.collection.objects.link(lo_)
    lo_.location = (HEAD[b5_[len(b5_) // 2]['i']][0].x, -1.2, page_z + 1.6)
    lo_.rotation_euler = (math.radians(40), 0, 0)
    for t_s in strikes:
        for u, e in ((-0.02, 0.0), (0.0, 9000.0), (0.04, 1200.0), (0.08, 6500.0), (0.14, 600.0), (0.3, 0.0)):
            ld.energy = e
            ld.keyframe_insert('energy', frame=fr(t_s + u))

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
            xbar = xb - min(0.09, (xb - xa) * 0.45)
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
    pt = HEAD[top['i']][0] + Vector((0, -0.05, 0.12))
    for col_ in ('magenta', 'cyan', 'amber'):
        burst(pt, top['t'], NEON[col_], n=12, speed=1.6, life=0.7, size=0.009)
    pulse_ring(pt, top['t'], NEON['white'], r0=0.05, r1=0.45, life=0.5)
    SIG_HITS.append(dict(t=top['t'], kind='sparkle', g=1.0))

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
            ch = character(x_, r_['z'] - 0.52 + 0.49, bc, ic, acc, f'dancer{len(DANCERS)}')
            r_['below'] = 0.55
            DANCERS.append((ch, [h['t'] for h in otj_ if HEAD[h['i']][2] is r_]))

fe_ = notes_of('fe')                              # Fur Elise: a firefly rises from every note it plays
for j, h in enumerate(fe_):
    head = HEAD[h['i']][0]
    col_ = (1.0, 0.85, 0.35) if j % 3 else (0.7, 1.0, 0.45)
    fm_ = mat(f'firefly{j}', col_, 0.3, emit=col_, emit_s=0.0)
    o = sphere(head + Vector((0.0, -0.03, 0.02)), 0.006, fm_, segs=10)
    key_vis(o, h['t'], h['t'] + 2.4)
    sway = 0.03 * (1 if j % 2 else -1)
    for k in range(7):
        u = k / 6
        o.location = head + Vector((sway * math.sin(u * 5), -0.03 - 0.05 * u, 0.02 + 0.32 * u))
        o.keyframe_insert('location', frame=fr(h['t'] + 2.3 * u))
    emit_keys(fm_, ((h['t'], 0.0), (h['t'] + 0.15, 16.0), (h['t'] + 1.2, 8.0), (h['t'] + 2.3, 0.0)))

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
    sp_.color, sp_.energy, sp_.spot_size, sp_.spot_blend = (1.0, 0.25, 0.18), 260.0, math.radians(38), 0.6
    so_ = bpy.data.objects.new('redspot', sp_)
    sc.collection.objects.link(so_)
    xm = [HEAD[h['i']][0].x for h in mk_]
    zm = sum(HEAD[h['i']][0].z for h in mk_) / len(mk_)
    so_.location = ((min(xm) + max(xm)) / 2, -1.6, zm + 1.6)
    t0m, t1m = mk_[0]['t'] - 2.0, mk_[-1]['t'] + 3.0
    k = 0
    tt = t0m
    while tt <= t1m:                               # a slow sweep from side to side
        ang = math.radians(28) * math.sin(k * 0.9)
        so_.rotation_euler = (math.radians(52), ang, 0)
        so_.keyframe_insert('rotation_euler', frame=fr(tt))
        tt += 1.0
        k += 1

toc_ = notes_of('toc')
for j, h in enumerate(toc_):
    head, st, row = HEAD[h['i']]
    ph = 0.10 + 0.010 * (h['midi'] - 48)              # higher notes, longer pipes
    foot = Vector((head.x, WALL_Y - 0.01, row['z'] + 4 * LS + 0.10))     # flat against the wall, behind the marble
    if h['j'] in SONGS[KEY_S['toc']].get('fermata', ()):
        foot.z = max(foot.z, head.z + 0.30)                                  # clear of the fermata over the note
    # an organ flue pipe: a conical foot, the mouth (a dark slot with its upper lip), the body; burnished,
    # not mirror metal (a mirror pipe only reflects the dark loft and reads black), with a faint glow
    pm = mat(f'pipe{j}', (0.85, 0.66, 0.3), 0.32, metal=0.9, emit=(1.0, 0.75, 0.4), emit_s=0.35)
    cone(foot + Vector((0, 0, 0.018)), 0.004, 0.015, 0.036, pm, 16)
    cyl(foot + Vector((0, 0, 0.036)), foot + Vector((0, 0, 0.036 + ph)), 0.015, pm, 16)
    cube((foot.x, foot.y - 0.0145, foot.z + 0.050), (0.016, 0.004, 0.010), mat('pipemouth', (0.02, 0.015, 0.01), 0.6))
    cube((foot.x, foot.y - 0.0150, foot.z + 0.057), (0.018, 0.003, 0.003), pm)
    emit_keys(pm, ((h['t'] - 1 / FPS, 0.35), (h['t'], 3.0), (h['t'] + max(0.3, h['dur']), 0.6)))
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
emit_keys(big_rim, ((TF - 1 / FPS, 4.0), (TF, 60), (TF + 1.2, 10)))
emit_keys(big_head, ((TF - 1 / FPS, 0.0), (TF, 22), (TF + 1.2, 2)))
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
for n_, (s, m_) in enumerate(sorted(GAPMACH.items())):
    bc, ic, acc = designs[n_ % 3]
    ch = character(X_LEFT - 0.55, m_.E_.z + 0.15, bc, ic, acc, f'watch{n_}')
    chars.append((ch, m_.t_kick))
yel = character(DRUM.x + 0.55, DRUM.z + 0.02, (0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo', 'yel')
pink = character(DRUM.x - 0.55, DRUM.z + 0.02, (0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears', 'pink')
catcher = None
if RESCUE:
    st_ = RESCUE['stand']
    catcher = character(st_.x, st_.z + 0.49, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'catcher')
    cube((st_.x, 0.30, st_.z - 0.012), (0.34, 0.40, 0.024), M_BRASS, bevel=0.006)       # its stand
    for sx in (-1, 1):
        cyl(Vector((st_.x + sx * 0.12, WALL_Y, st_.z - 0.03)), Vector((st_.x + sx * 0.12, 0.12, st_.z - 0.03)), 0.008, M_BRASS, 10)
for ch in [c for c, _ in chars] + [yel, pink] + ([catcher] if catcher else []) + [d for d, _ in DANCERS]:
    r0 = ch['root']
    holder = empty((r0.location.x, r0.location.y, r0.location.z - 0.49), r0.name + '_holder')
    bpy.context.view_layer.update()
    parent(r0, holder)
    sc_ = 0.40 if r0.name.startswith('dancer') else 0.62
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
for ch, beats in DANCERS:                         # bouncing on every beat of Ode to Joy
    for tb in beats:
        hop(ch, tb, 0.07)
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
    hop(catcher, t1r + 0.04, 0.16)                                     # and cheers when it lands
    mouth_o(catcher, t1r, t1r + 0.9, 1.6)
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
    RESCUE_HITS = [dict(t=t0r + 0.03, kind='whoosh', g=1.0, L=0.7), dict(t=tcr, kind='land', g=0.5),
                   dict(t=tcr + 0.02, kind='net', g=1.0), dict(t=ttr - 0.28, kind='spring', g=0.5),
                   dict(t=ttr, kind='whoosh', g=0.8, L=0.45)]
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
# the marble collects the colour of every piece it plays: it starts pearl white, and as each piece begins
# it takes that piece's colour; one band of its swirl keeps each colour, so it strikes the final drum as a rainbow
ramp = nt_.nodes.new('ShaderNodeValToRGB')
PEARL = (0.86, 0.87, 0.92, 1)
els = ramp.color_ramp.elements
while len(els) < len(SONGS):
    els.new(0.5)
for k in range(len(SONGS)):
    els[k].position = (k + 0.5) / len(SONGS)
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
    # one marble all along: it soaks up the new piece's colour from the chase lamps it rolls past on the way in
    # (a gradual change you can see happen), and keeps a band of every colour it has had
    ch_ = sorted(x['t'] for x in (GAPMACH[k].hits if k in GAPMACH else []) if x['kind'] == 'chase')
    a_, b_ = (ch_[0] - 0.05, ch_[-1] + 0.1) if len(ch_) >= 2 else (t_k - 0.4, t_k + 0.12)
    for j in range(k, len(SONGS)):
        for tt, c_ in ((a_, piece_col(k - 1)), (b_, piece_col(k))):
            els[j].color = c_
            els[j].keyframe_insert('color', frame=fr(tt))
    for tt, g_ in ((max(0.0, t_k - 1 / FPS), 0.35 + 0.08 * k), (t_k + 0.05, 1.6), (t_k + 0.5, 0.35 + 0.08 * (k + 1))):
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


def local_frame(r_, tt):
    """Vertical centre and zoom for the stretch of the row on screen around time tt: the staff, the notes
    in view (and just ahead), and the highest hop above them."""
    lo_, hi_ = r_['z'] - r_.get('below', 0.05), r_['z'] + 4 * LS + 0.05
    for h in r_['notes']:
        if tt - 1.1 <= h['t'] <= tt + 1.7:
            z, st_ = HEAD[h['i']][0].z, HEAD[h['i']][1]
            T_ = C[h['i'] + 1]['t'] - h['t']
            apex = G / 8 * min(T_, T_HOP) ** 2                 # the hop that leaves this note
            lo_ = min(lo_, z - R_HEAD[2] - 0.07)
            hi_ = max(hi_, z + R_HEAD[2] + 2 * R + apex + 0.03, z + 3.5 * LS + 0.03 if st_ < 4 else z)
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
    return Vector((row_x(r_, tt), HEAD_Y, zc_)), max(zoom_, min(1.6, v_ / V_REF))


_POS = {h['i']: k for k, h in enumerate(C)}
RET_PAIRS = [(C[_POS[i]], C[_POS[i] + 1], r['row_from'], r['row_to']) for i, r in RETURNS.items()]


def frame_point(tt):
    """Where the camera wants to look at time tt: on a row, the music's position and the middle of the
    notes in view. While the ball is in a tube (a carriage return, or the way to the next page), the camera
    eases from the end of one row to the start of the next, pulling back a little on the way, so it is
    settled before the next note."""
    if tt <= C[0]['t']:
        return (*row_point(ROWS[0], C[0]['t']), (0.0, 0.0))
    for h0, h1, r0, r1 in RET_PAIRS:
        # a carriage return: from the row's last bars the view opens to hold the row end and the next row's
        # start together, so the ride through the tube crosses the frame, then closes in on the new row
        a_, b_ = h0['t'] - 0.5, h1['t'] + 0.35
        if a_ <= tt <= b_:
            pa, za = row_point(r0, h0['t'])
            pb, zb = row_point(r1, h1['t'])
            zfit = min(2.4, max(1.0, (abs(pa.x - pb.x) + 1.0) / (VIEW_H * 16 / 9), (abs(pa.z - pb.z) + 0.9) / VIEW_H))
            u = (tt - a_) / (b_ - a_)
            w = math.sin(math.pi * u)
            base, zbase = pa.lerp(pb, smooth(u)), za + (zb - za) * smooth(u)
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
                w = smooth((tt - (h0['t'] + 0.2)) / 0.9) * (1 - smooth((tt - (h0['t'] + 2.0)) / 0.8))
                zf_ = m_.zoom(tt, MACH_ZOOM)
                att, zz = m_.attention(tt).lerp(wide, w), zf_ + (zw - zf_) * w
                el_, yw_ = m_.elev(tt) * (1 - w), m_.yaw(tt)
                # and it arrives settled: the next piece's first-note framing (a little wider and higher, to
                # take the marble's drop in) is reached before the first note plays
                ka = smooth((tt - (h1['t'] - 1.5)) / 1.1)
                pb, zb = row_point(HEAD[h1['i']][2], h1['t'])
                return (att.lerp(pb + Vector((0, 0, 0.12)), ka), zz + (zb * 1.2 - zz) * ka,
                        (el_ * (1 - ka), yw_ * (1 - ka)))
            r0 = HEAD[h0['i']][2]
            r1 = HEAD[h1['i']][2] if h1['i'] in HEAD else r0
            if r1 is r0:
                return (*row_point(r0, tt), (0.0, 0.0))
            k = smooth((tt - h0['t']) / (h1['t'] - h0['t']))
            pa, za = row_point(r0, h0['t'])
            pb, zb = row_point(r1, h1['t'])
            return pa.lerp(pb, k), (za + (zb - za) * k) * (1 + 0.25 * math.sin(math.pi * k)), (0.0, 0.0)
    return (*row_point(ROWS[-1], C[-2]['t']), (0.0, 0.0))


def target(t):
    """Smoothed look-at point and zoom: the pan is averaged over a wider window (an even glide through
    fast runs), the height and zoom over a narrower one."""
    px, wx, pz, zf, el, yw, wz = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    for j in range(-12, 13):
        p_, z_, (e_, y_) = frame_point(t + j * 0.08)
        w1, w2 = math.exp(-(j / 7.0) ** 2), math.exp(-(j / 5.0) ** 2)
        px, wx = px + p_.x * w1, wx + w1
        pz, zf, el, yw, wz = pz + p_.z * w2, zf + z_ * w2, el + e_ * w2, yw + y_ * w1, wz + w2
    # the music sits a little above the middle, so the timeline band at the bottom stays clear of it
    return Vector((px / wx + 0.18, HEAD_Y, pz / wz - 0.05 * VIEW_H * zf / wz)), zf / wz, (el / wz, yw / wx)


Z_FIRST, Z_LAST = ROWS[0]['z'] + 2 * LS, ROWS[-1]['z'] + 2 * LS
X_MID = (X_LEFT + max(r['x1'] for r in ROWS)) / 2
REVEAL_T0 = TF + 1.6
REVEAL_T1 = T_END - 0.6


def reveal_time(z):
    """When the rising camera's centre passes height z during the closing reveal."""
    goal = (z - Z_LAST) / (Z_FIRST - Z_LAST)
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if smooth(mid) < goal else (lo, mid)
    return REVEAL_T0 + lo * (REVEAL_T1 - REVEAL_T0)


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
    kh = smooth((t - (FIN['launch'] - 0.3)) / 0.6)
    tg = tg.lerp((CON[C[-2]['i']] + DRUM) / 2 + Vector((0, 0, 0.2)), kh * (1 - smooth((t - (TF + 0.2)) / 0.6)))
    tg = tg.lerp(DRUM + Vector((0, 0, 0.1)), smooth((t - (TF + 0.1)) / 0.6))
    # after the drum: pull back to see a few rows, then rise up the whole score, back to 1680
    kb = smooth((t - (TF + 1.0)) / 0.8)
    off = off.lerp(Vector((0.25, -5.2, 0.15)), kb)
    if t > REVEAL_T0:
        k = smooth((t - REVEAL_T0) / (REVEAL_T1 - REVEAL_T0))
        tg = Vector((X_MID, YB, Z_LAST + (Z_FIRST - Z_LAST) * k))
    else:
        tg = tg.lerp(Vector((X_MID, YB, Z_LAST)), kb)
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

# ---------------------------------------------------------------- 8. light: each piece in its own light
# The camera only ever sees one page at a time, so the light is keyed in time: each piece has its own key
# (direction, colour, strength), fill and ambient, and the machine ride into a piece crossfades to it, so the
# marble arrives in a new room. Low-key where the era asks for it, so the glowing marble and notes carry
# the frame. After the final drum the light opens up to an even gallery light for the rise through 300 years.
LOOK = {   # key (strength, colour, direction to the light), fill (strength, colour), ambient (colour, strength)
    'canon': ((0.75, (1.0, 0.74, 0.46), (0.6, -1.0, 0.9)), (0.10, (1.0, 0.8, 0.6)), ((0.30, 0.20, 0.12), 0.10)),  # candlelight
    'toc': ((1.35, (1.0, 0.93, 0.82), (-0.5, -0.6, 1.6)), (0.06, (0.6, 0.7, 1.0)), ((0.10, 0.10, 0.16), 0.08)),   # organ loft
    'tm': ((1.3, (1.0, 0.86, 0.80), (0.5, -1.0, 1.0)), (0.30, (1.0, 0.80, 0.76)), ((0.55, 0.42, 0.42), 0.16)),    # salon
    'ekn': ((0.95, (0.62, 0.72, 1.0), (-0.4, -1.0, 1.2)), (0.18, (1.0, 0.72, 0.42)), ((0.05, 0.07, 0.16), 0.16)),  # night
    'b5': ((0.85, (0.72, 0.80, 1.0), (0.3, -1.0, 1.5)), (0.08, (0.5, 0.6, 1.0)), ((0.04, 0.05, 0.10), 0.10)),     # storm
    'fe': ((0.55, (0.95, 0.80, 0.95), (0.6, -1.0, 0.8)), (0.12, (0.7, 0.6, 1.0)), ((0.06, 0.05, 0.10), 0.12)),    # evening
    'otj': ((2.1, (1.0, 0.92, 0.74), (0.4, -1.0, 1.3)), (0.40, (0.85, 0.9, 1.0)), ((0.45, 0.45, 0.50), 0.30)),    # daylight
    'mk': ((0.60, (1.0, 0.55, 0.42), (-0.6, -1.0, 0.7)), (0.08, (1.0, 0.4, 0.3)), ((0.12, 0.03, 0.03), 0.10)),    # red hall
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
set_look(LOOK.get(SONGS[-1]['key'], GALLERY), TF + 0.8, SONGS[-1]['key'])
set_look(GALLERY, TF + 2.6)                       # no follow-spot for the wide rise at the end
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
