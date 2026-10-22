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
sc.render.motion_blur_shutter = 0.45
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
SONGS = S.SONGS
FIN = C[-1]
TF = FIN['t']
ERAS = S.ERA
rng = random.Random(31)

# paper and ink for each era (the wall is the page)
PAGE = {
    'baroque': dict(paper=(0.80, 0.70, 0.52), ink=(0.16, 0.10, 0.06), ink_metal=0.0, rough=0.9),
    'classical': dict(paper=(0.90, 0.89, 0.86), ink=(0.03, 0.03, 0.035), ink_metal=0.0, rough=0.85),
    'beethoven': dict(paper=(0.07, 0.09, 0.17), ink=(0.86, 0.88, 0.93), ink_metal=0.9, rough=0.6),
    'romantic': dict(paper=(0.28, 0.05, 0.07), ink=(0.95, 0.72, 0.30), ink_metal=1.0, rough=0.45),
}
LS = 0.075               # staff line spacing (one step = LS / 2)
XS = 0.62                # metres per second along a staff row
ROW_W = 2.9              # a row turns (carriage return) on a long note once it is this wide
ROW_H = 1.05             # distance between rows
X_LEFT = -1.6
CLEF_W = 0.55
KS_DX = 0.072            # spacing of the key-signature accidentals
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
        row_z -= ROW_H * 1.25           # a new page (era) starts a little lower
    row = dict(s=s, z=row_z, t0=hs[0]['t'], x0=X_LEFT + CLEF_W + (0.35 if s == 0 or True else 0), notes=[], first=True)
    ROWS.append(row)
    sec_rows[s] = [row]
    nunits = song.get('nunits') or [u for _, u in song['notes']]
    kalt, bu, pu = key_alt(song['keysig']), song['bar_units'], song['pickup_units']
    state, bar_now, pos = {}, None, 0.0
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
        x = row['x0'] + XS * (h['t'] - row['t0'])
        st = step_of(name, clef)
        head = Vector((x, HEAD_Y, row['z'] + st * LS / 2))
        HEAD[h['i']] = (head, st, row)
        CON[h['i']] = head + Vector((0, HEAD_Y - HEAD_Y, R_HEAD[2] + R))
        if h['mech'] == 'again':
            CON[h['i']] = CON[h['i'] - 1].copy()
            HEAD[h['i']] = HEAD[h['i'] - 1]
        row['notes'].append(h)
        nxt = hs[j + 1] if j + 1 < len(hs) else None
        if nxt is not None and x - row['x0'] >= ROW_W and h['dur'] >= 0.34 and nxt['mech'] != 'again':
            # carriage return: into a funnel at the end of the row, along a glass tube, out at the next row
            row_z -= ROW_H
            new = dict(s=s, z=row_z, t0=nxt['t'], x0=X_LEFT + CLEF_W + KS_DX * abs(song['keysig']), notes=[], first=False)
            RETURNS[h['i']] = dict(t0=h['t'] + 0.10, t1=nxt['t'] - 0.16, row_from=row, row_to=new)
            row['x1'] = x + 0.25
            row = new
            ROWS.append(row)
            sec_rows[s].append(row)
    row['x1'] = row['x0'] + XS * (hs[-1]['t'] - row['t0']) + 0.25
    row_z = row['z']
# final drum after the double bar of the last row
LASTROW = ROWS[-1]
DRUM = Vector((LASTROW['x1'] + 0.55, HEAD_Y, LASTROW['z'] - 0.35))
CON[FIN['i']] = DRUM + Vector((0, 0, 0.004 + R))


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

# gaps between songs: the same tube, longer, into the next page
GAPTUBE = {}
for g in GAPS:
    s = g['s']
    L_ = [h for h in C if h['s'] == s - 1 and h['mech'] != 'bigdrum'][-1]
    F_ = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum'][0]
    pa = CON[L_['i']]
    rf, rt = HEAD[L_['i']][2], HEAD[F_['i']][2]
    zt_ = rf['z'] - 0.42
    pts = [pa, Vector((pa.x + 0.18, HEAD_Y, pa.z - 0.10)), Vector((pa.x + 0.26, HEAD_Y, zt_ + 0.05)), Vector((pa.x + 0.12, HEAD_Y, zt_)),
           Vector((X_LEFT + 0.15, HEAD_Y, zt_)), Vector((X_LEFT - 0.05, HEAD_Y, (zt_ + rt['z']) / 2)),
           Vector((X_LEFT + 0.12, HEAD_Y, rt['z'] + 0.62))]
    GAPTUBE[s] = dict(pts=pts, t0=L_['t'] + 0.12, t1=F_['t'] - 0.18, L=L_, F=F_)


LEDGE_END = CON[0] + Vector((-0.10, 0, 0.06))
LEDGE_START = LEDGE_END + Vector((-0.32, 0, 0.025))


def ease(k):
    return k * k * (3 - 2 * k)


def kick_time(h0):
    """When a long note flicks the held ball on to the next note (None for an ordinary flight)."""
    if h0['i'] + 1 >= len(C):
        return None
    h1 = C[h0['i'] + 1]
    if h1['mech'] == 'bigdrum' or RETURNS.get(h0['i']) or (h0['s'] != h1['s'] and GAPTUBE.get(h1['s'])):
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


def ball_pos(t):
    if t <= C[0]['t']:
        # first frame: already rolling in along the opening ledge, it drops onto the first note
        start = LEDGE_END
        if t <= C[0]['t'] - 0.18:
            return LEDGE_START.lerp(start, max(0.0, t) / (C[0]['t'] - 0.18))
        return ballistic(start, C[0]['t'] - 0.18, CON[0], C[0]['t'], t)
    for h0, h1 in zip(C[:-1], C[1:]):
        if h0['t'] <= t <= h1['t']:
            p0, p1 = CON[h0['i']], CON[h1['i']]
            if h1['mech'] == 'bigdrum':
                if t <= h1['launch']:
                    return p0
                return ballistic(p0, h1['launch'], p1, h1['t'], t)
            tube = RETURNS.get(h0['i']) or (GAPTUBE.get(h1['s']) if h0['s'] != h1['s'] else None)
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


def text_obj(txt, loc, size, m, rot=(math.radians(90), 0, 0), align='CENTER'):
    cu = bpy.data.curves.new('txt', 'FONT')
    cu.body = txt
    cu.font = bpy.data.fonts.load(FREESERIF, check_existing=True)
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
    lift = {'♯': 0.021, '♮': 0.022, '♭': 0.035}[sym]      # engraved size: a sharp is about 2.6 spaces tall
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
    wp = add(bpy.context.object, paper_mat(era))
    wp.scale = (W_X1 - W_X0, z_top - z_bot + 0.002, 1)
    if s > 0:
        nc = NEON[ERAS[era]['neon'][0]]
        cyl((W_X0, WALL_Y - 0.01, z_top), (W_X1, WALL_Y - 0.01, z_top), 0.01, mat(f'trim{s}', nc, 0.3, emit=nc, emit_s=1.2), 10)
    ink = ink_mat(era)
    for row in sec_rows[s]:
        x0s, x1s = X_LEFT + 0.05, row['x1']
        for ln in range(5):
            z = row['z'] + ln * LS
            cube(((x0s + x1s) / 2, WALL_Y - 0.004, z), (x1s - x0s, 0.004, 0.0045), ink)
        # system bracket and clef
        cube((x0s, WALL_Y - 0.004, row['z'] + 2 * LS), (0.006, 0.004, 4 * LS), ink)
        glyph = '\U0001D11E' if song['clef'] == 'treble' else '\U0001D122'
        clef_z = row['z'] + (1.25 * LS if song['clef'] == 'treble' else 2.6 * LS)
        text_obj(glyph, Vector((x0s + 0.12, WALL_Y - 0.008, clef_z)), 0.42 if song['clef'] == 'treble' else 0.24, ink)
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
    ink = ink_mat(era)
    head, st, row = HEAD[h['i']]
    neon = NEON[ERAS[era]['neon'][h['midi'] % len(ERAS[era]['neon'])]]
    if h['mech'] == 'again':
        m = bpy.data.materials.get(f'head{h["i"] - 1}')
        while m is None and h['i'] > 0:
            break
        if m:
            emit_keys(m, ((h['t'] - 1 / FPS, 6.0), (h['t'], 40.0), (h['t'] + 0.4, 6.0)))
        burst(CON[h['i']] + Vector((0, -0.04, -R)), h['t'], neon, n=4, speed=0.6, life=0.25, size=0.006)
        continue
    pg = PAGE[era]
    hm = mat(f'head{h["i"]}', pg['ink'], 0.12, metal=pg['ink_metal'] * 0.6, emit=neon, emit_s=0.0, coat=1.0)
    o = sphere(head, 1.0, hm, scale=R_HEAD, segs=32)
    o.rotation_euler = (0, math.radians(-20), 0)        # the slant of an engraved note head
    # stem (flat on the page): up on the right below the middle line, down on the left above it
    up = st < 4
    sx = head.x + (0.045 if up else -0.045)
    z0s = row['z'] + st * LS / 2
    stem_o = cube((sx, WALL_Y - 0.006, z0s + (1 if up else -1) * 3.5 * LS / 2), (0.006, 0.004, 3.5 * LS), ink)
    wobble(stem_o, h['t'], axis=1, amp=2.2)
    cyl((head.x, WALL_Y, head.z), (head.x, head.y + 0.02, head.z), 0.006, ink, 8)          # the pin holding the head
    # ledger lines
    if st < -1 or st > 9:
        rng_ = range(-2, st - 1, -2) if st < -1 else range(10, st + 1, 2)
        for ls_ in rng_:
            cube((head.x, WALL_Y - 0.004, row['z'] + ls_ * LS / 2), (0.16, 0.004, 0.0045), ink)
    if h['acc']:
        accidental(h['acc'], head.x - 0.11, z0s, ink)
    # glow on the hit, and it stays softly lit: the played music remains on the page
    emit_keys(hm, ((h['t'] - 1 / FPS, 0.0), (h['t'], 45.0), (h['t'] + 0.45, 3.0)))
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
    for t_, e_ in ((h['t'] - 1 / FPS, 0.0), (h['t'], 5.0), (h['t'] + 0.35, 0.0)):
        ld.energy = e_
        ld.keyframe_insert('energy', frame=fr(max(0.0, t_)))
    # only exists while it glows (keeps ~250 lights out of the light tree), and only reaches nearby
    ld.use_custom_distance = True
    ld.cutoff_distance = 0.9
    key_vis(lo, h['t'] - 2 / FPS, h['t'] + 0.4)

# the opening ledge
cyl(LEDGE_START - Vector((0.05, 0, R + 0.006)), LEDGE_END - Vector((-0.01, 0, R + 0.006)), 0.009, mat('ledge', (0.85, 0.62, 0.28), 0.25, metal=1.0), 12)
for p_ in (LEDGE_START, LEDGE_END):
    cyl((p_.x, WALL_Y, p_.z - R - 0.006), (p_.x, YB, p_.z - R - 0.006), 0.006, mat('ledgepin', (0.85, 0.62, 0.28), 0.25, metal=1.0), 8)

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
        flame = sphere(p + Vector((0, 0, 0.045)), 0.012, mat('flame', (1.0, 0.7, 0.3), 0.5, emit=(1.0, 0.62, 0.25), emit_s=40),
                       scale=(0.7, 0.7, 1.6), segs=12)
        ld.color, ld.shadow_soft_size, base_e = (1.0, 0.68, 0.35), 0.02, 9.0
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
for key, tube in list(RETURNS.items()) + [(('gap', s), g) for s, g in GAPTUBE.items()]:
    pts = tube['pts'][1:]
    era = SONGS[C[key]['s'] if not isinstance(key, tuple) else key[1]]['era']
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
for n_, (s, g) in enumerate(sorted(GAPTUBE.items())):
    bc, ic, acc = designs[n_ % 3]
    pts = g['pts']
    ch = character(X_LEFT - 0.55, pts[-1].z + 0.15, bc, ic, acc, f'watch{n_}')
    chars.append((ch, g['t1']))
yel = character(DRUM.x + 0.55, DRUM.z + 0.02, (0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo', 'yel')
pink = character(DRUM.x - 0.55, DRUM.z + 0.02, (0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears', 'pink')
for ch in [c for c, _ in chars] + [yel, pink]:
    r0 = ch['root']
    holder = empty((r0.location.x, r0.location.y, r0.location.z - 0.49), r0.name + '_holder')
    bpy.context.view_layer.update()
    parent(r0, holder)
    holder.scale = (0.62, 0.62, 0.62)
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
ramp = nt_.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.9, 0.02, 0.25, 1)
ramp.color_ramp.elements[1].color = (0.05, 0.25, 0.9, 1)
e = ramp.color_ramp.elements.new(0.5)
e.color = (1.0, 0.75, 0.2, 1)
nt_.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 2.0
bsdf.inputs['Roughness'].default_value = 0.06
bsdf.inputs['Coat Weight'].default_value = 1.0
ball = sphere((0, 0, 0), R, core_m, segs=40)
spin, prev = 0.0, ball_pos(0.0)
for f in range(1, N + 1):
    t = (f - 1) / FPS
    p = ball_pos(t)
    spin += (p - prev).length / R
    prev = p
    ball.location = p
    ball.keyframe_insert('location', frame=f)
    ball.rotation_euler = (0, spin, spin * 0.3)
    ball.keyframe_insert('rotation_euler', frame=f)

# ---------------------------------------------------------------- 7. camera: reads the score like a page
bpy.ops.object.camera_add(location=(0, -4, 0))
cam = bpy.context.object
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 4.0
sc.camera = cam
focus_empty = empty((0, HEAD_Y - 0.02, 0), 'focus')
cam.data.dof.focus_object = focus_empty   # focus rides with the marble on the note-head plane
OFF = Vector((0.20, -1.95, 0.16))


def row_at(t):
    for h0, h1 in zip(C[:-1], C[1:]):
        if h0['t'] <= t <= h1['t']:
            if h0['i'] in HEAD and h1['i'] in HEAD and HEAD[h0['i']][2] is HEAD[h1['i']][2]:
                return HEAD[h0['i']][2]
            return None
    return None


VIEW_H = 2 * OFF.length * 10.125 / 50.0        # visible height on the head plane at the base distance (50 mm)
for row in ROWS:
    zs_ = [HEAD[h['i']][0].z for h in row['notes']]
    lo_ = min(row['z'] - 0.05, min(zs_) - R_HEAD[2] - 0.07)
    hi_ = max(row['z'] + 4 * LS + 0.05, max(zs_) + 2 * R + 0.22)      # the highest hop above the highest note
    row['zc'], row['zoom'] = (lo_ + hi_) / 2, max(1.0, (hi_ - lo_) / (0.86 * VIEW_H))


def frame_point(tt):
    """Where the camera wants to look at time tt: on a row, the music's own position (x moves at XS per
    second, the speed the notes are laid out at) and the middle of the row's notes; in a tube, the ball."""
    r_ = row_at(tt)
    if r_ is not None:
        return Vector((r_['x0'] + XS * (tt - r_['t0']), HEAD_Y, r_['zc'])), r_['zoom']
    b_ = ball_pos(max(0.0, tt))
    return Vector((b_.x, HEAD_Y, b_.z)), 1.0


def target(t):
    acc_, zf, ws = Vector((0, 0, 0)), 0.0, 0.0
    for j in range(-8, 9):
        p_, z_ = frame_point(t + j * 0.08)
        w_ = math.exp(-(j / 5.0) ** 2)
        acc_ += p_ * w_
        zf += z_ * w_
        ws += w_
    return acc_ / ws + Vector((0.18, 0, 0)), zf / ws


Z_FIRST, Z_LAST = ROWS[0]['z'] + 2 * LS, ROWS[-1]['z'] + 2 * LS
X_MID = (X_LEFT + max(r['x1'] for r in ROWS)) / 2
REVEAL_T0 = TF + 1.6
REVEAL_T1 = T_END - 0.6


def cam_at(t):
    tg, zf = target(t)
    off = OFF * zf
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
    cam.data.dof.aperture_fstop = 4.0 + 6.0 * smooth((t - (TF + 1.0)) / 1.0)   # deeper focus for the wide reveal
    bp_ = ball_pos(t)
    focus_empty.location = (bp_.x, HEAD_Y - 0.02, bp_.z)
    focus_empty.keyframe_insert('location', frame=f)
    cam.data.dof.keyframe_insert('aperture_fstop', frame=f)
    f += 2

world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.55, 0.56, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
bpy.ops.object.light_add(type='SUN', location=(0, -3, 5))
sun = bpy.context.object
sun.data.energy, sun.data.angle, sun.data.color = 2.2, math.radians(20), (1.0, 0.96, 0.9)
sun.rotation_euler = Vector((0.5, 1.0, -1.0)).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.light_add(type='SUN', location=(0, -3, 5))
fill = bpy.context.object
fill.data.energy, fill.data.angle, fill.data.color = 0.5, math.radians(40), (0.9, 0.93, 1.0)
fill.rotation_euler = Vector((-0.8, 1.0, 0.1)).to_track_quat('-Z', 'Y').to_euler()
sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = -0.3
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.03
sc.use_nodes = True
nt = sc.node_tree
gl = nt.nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.size = 7
if hasattr(gl, 'threshold'):
    gl.threshold = 1.5
nt.links.new(nt.nodes['Render Layers'].outputs['Image'], gl.inputs['Image'])
nt.links.new(gl.outputs['Image'], nt.nodes['Composite'].inputs['Image'])

import json  # noqa: E402
ev_path = os.environ.get('EVENTS_OUT')
if ev_path:
    json.dump(dict(returns=[dict(t0=r['t0'], t1=r['t1']) for r in RETURNS.values()],
                   gaps=[dict(t0=g['t0'], t1=g['t1']) for g in GAPTUBE.values()], taps=TAPS), open(ev_path, 'w'))
print('frames total', N, 'seconds', round(T_END, 2), 'rows', len(ROWS), 'objects', len(bpy.data.objects), flush=True)
print('row zoom', ' '.join(f"{SONGS[r['s']]['key']}:{r['zoom']:.2f}" for r in ROWS), 'taps', len(TAPS), flush=True)
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
