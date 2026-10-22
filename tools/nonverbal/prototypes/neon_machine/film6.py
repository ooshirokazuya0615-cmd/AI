"""Long-form marble-music film (v6), 16:9: eight public-domain melodies joined by silent one-bar gaps.

Look: House of Marble style (light studio wall, dark fixtures, neon light on each hit), original assets and
characters. Every melody note is one contact; pads, cymbals and xylophone bars are tilted to give a true
mirror bounce. Gaps ('rail', 'chute', 'launch') are counted in beats of the next song (see songs6.py).

    SONGS_MODULE=songs_kimetsu python film6.py -- ...   (default: songs6, the classical medley)
    python film6.py -- --res 1280x720 --samples 10 --out frames/f_#### [--frames 1-400] [--stills 30,600]
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


def add(o, m):
    o.data.materials.append(m)
    return o


def cube(loc, scale, m, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = scale
    if bevel:
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        md = o.modifiers.new('b', 'BEVEL')
        md.width, md.segments = bevel, 2
    return add(o, m)


def sphere(loc, r, m, scale=None, segs=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=max(8, segs // 2), radius=r, location=loc)
    o = bpy.context.object
    if scale:
        o.scale = scale
    bpy.ops.object.shade_smooth()
    return add(o, m)


def cyl(p0, p1, r, m, verts=20, smooth_=True):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    if smooth_:
        bpy.ops.object.shade_smooth()
    return add(o, m)


def cone(loc, r1, r2, depth, m, verts=32):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc)
    bpy.ops.object.shade_smooth()
    return add(bpy.context.object, m)


def torus(loc, R_, r_, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R_, minor_radius=r_, location=loc, rotation=rot,
                                     major_segments=40, minor_segments=10)
    return add(bpy.context.object, m)


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


# ================================================================ long-form look (as v4): light wall, dark fixtures, neon
M_WALL = mat('wall6', (0.78, 0.79, 0.80), 0.8)
M_FIX = mat('fixture', (0.035, 0.035, 0.04), 0.35, metal=0.3, coat=0.5)
M_FIX2 = mat('fixture2', (0.08, 0.08, 0.09), 0.3, metal=0.7)
M_RAIL = mat('rail', (0.05, 0.05, 0.055), 0.25, metal=0.9)
M_GLASS = mat('glass', (0.92, 0.95, 1.0), 0.03, trans=1.0)
NOTE_COL = {0: 'amber', 1: 'red', 2: 'lime', 3: 'violet', 4: 'cyan', 5: 'red', 6: 'magenta', 7: 'violet',
            8: 'violet', 9: 'magenta', 10: 'amber', 11: 'lime'}
C, GAPS = S.timeline()
SONGS = S.SONGS
FIN = C[-1]
TF = FIN['t']
DESC, DRIFT, XS = 0.24, 0.30, 0.045
rng = random.Random(23)


def ballistic(p0, t0, p1, t1, t):
    T = t1 - t0
    v = (p1 - p0 + Vector((0, 0, 0.5 * G * T * T))) / T
    u = t - t0
    return p0 + v * u + Vector((0, 0, -0.5 * G * u * u))


# ---------------------------------------------------------------- 1. the path: pieces (t0, t1, fn)
PIECES = []
CON = {}
sec_first = {s: next(h for h in C if h['s'] == s) for s in range(len(SONGS))}
sec_last = {s: [h for h in C if h['s'] == s and h['mech'] != 'bigdrum'][-1] for s in range(len(SONGS))}
gap_into = {g['s']: g for g in GAPS}
# the song before a 'launch' gap ends in a cup
for g in GAPS:
    if g['kind'] == 'launch':
        sec_last[g['s'] - 1]['mech'] = 'cup'
GAPGEO = {}      # s -> geometry of the gap leading into song s


SWOOPS = {}
ROW = 3.0          # seconds of travel before the machine turns around
TURN_DROP = 0.26   # extra drop at a turn
ZP = 0.012         # metres of height per semitone (the melody's contour is visible)


def place_section(s, origin, d):
    """Lay out one section starting at origin, travelling in x-direction d (+1 right, -1 left).
    The machine turns around on a long-enough note once it has travelled ROW seconds. Returns the end direction."""
    hs = [h for h in C if h['s'] == s and h['mech'] != 'bigdrum']
    song = SONGS[s]
    th = math.radians(8.0)
    bx, bz, tb, t_turn = origin.x, origin.z, hs[0]['t'], hs[0]['t']
    k, side = 0, 1
    while k < len(hs):
        h = hs[k]
        bx += DRIFT * d * (h['t'] - tb)
        bz -= DESC * (h['t'] - tb)
        tb = h['t']
        lift = max(-0.18, min(0.18, (h['midi'] - song['centre']) * ZP))
        if h['mech'] == 'tile':
            run = [h]
            while k + len(run) < len(hs) and hs[k + len(run)]['mech'] == 'tile':
                run.append(hs[k + len(run)])
            dirv = Vector((d * math.cos(th), 0, -math.sin(th)))
            p0 = Vector((bx, YB, bz + lift))
            for j, r in enumerate(run):
                CON[r['i']] = p0 + dirv * (0.5 * (r['t'] - h['t']))
                r['roll'] = j < len(run) - 1
            last = run[-1]
            bx, bz, tb = CON[last['i']].x, CON[last['i']].z - lift, last['t']
            k += len(run)
            h = last
        else:
            if h['mech'] == 'again':
                CON[h['i']] = CON[h['i'] - 1].copy()
            elif h['mech'] == 'bumper':
                CON[h['i']] = Vector((bx + 0.13 * side, YB, bz))
                h['side'] = side
                side = -side
            else:
                CON[h['i']] = Vector((bx, YB, bz + lift))
            k += 1
        # turn around on a long note once the row is long enough: the ball lands on a coaster rail that swoops
        # out, down and back underneath, so the next row runs the other way
        nxt = hs[k] if k < len(hs) else None
        if (nxt is not None and h['dur'] >= 0.36 and h['t'] - t_turn >= ROW and h['mech'] not in ('again', 'cup', 'tile')
                and nxt['mech'] != 'again'):
            c = CON[h['i']]
            pts = [c + Vector((dx * d, 0, dz)) for dx, dz in ((0.0, 0.0), (0.18, -0.07), (0.36, -0.22), (0.40, -0.40),
                                                             (0.24, -0.53), (0.02, -0.57))]
            t_end = h['t'] + h['dur'] - 0.14
            pts = [p - Vector((0, 0, R + 0.008)) for p in pts]
            SWOOPS[h['i']] = dict(pts=pts, t0=h['t'], t1=t_end, d=d)
            h['mech'] = 'swoop'
            d = -d
            bx, bz = pts[-1].x + 0.10 * d, pts[-1].z - 0.06 - (R + 0.008)
            tb = h['t'] + h['dur']
            t_turn = h['t']
    return d


D = 1
ORIGIN = Vector((-0.4, YB, 0.4))
for s in range(len(SONGS)):
    if s > 0:
        g = gap_into[s]
        L = sec_last[s - 1]
        PL = CON[L['i']]
        if g['kind'] == 'rail':
            pts = [PL + Vector((dx * D, 0, dz)) for dx, dz in ((0.30, -0.14), (0.58, -0.30), (0.90, -0.38), (1.20, -0.33),
                                                              (1.42, -0.24), (1.60, -0.22))]
            sw = pts[-1] + Vector((0.10 * D, 0, 0))
            GAPGEO[s] = dict(kind='rail', pts=pts, sw=sw, t_rail0=g['t_rail0'], t_sw=g['t_sw'], d=D)
            ORIGIN = sw + Vector((0.26 * D, 0, -0.42))
        elif g['kind'] == 'chute':
            top = PL + Vector((0.34 * D, 0, -0.18))
            bot = top + Vector((0.0, 0, -1.05))
            GAPGEO[s] = dict(kind='chute', top=top, bot=bot, t_in=g['t_in'], t_out=g['t_out'], d=D)
            D = -D                                  # come out of the tube going the other way
            ORIGIN = bot + Vector((0.30 * D, 0, -0.30))
        else:  # launch from the cup, across to the other side
            D = -D
            GAPGEO[s] = dict(kind='launch', cup=PL, t_launch=g['t_launch'], d=D)
            ORIGIN = PL + Vector((0.95 * D, 0, -0.26))
    D = place_section(s, ORIGIN, D)
# the final drum after the last cup
LASTCUP = sec_last[len(SONGS) - 1]
CON[FIN['i']] = CON[LASTCUP['i']] + Vector((-1.25 * D, 0, -0.30))   # the last launch crosses back


def catmull(pts, n=120):
    P = [pts[0] + (pts[0] - pts[1])] + pts + [pts[-1] + (pts[-1] - pts[-2])]
    out, per = [], n // (len(P) - 3)
    for sgi in range(len(P) - 3):
        p0, p1, p2, p3 = P[sgi:sgi + 4]
        for j in range(per):
            u = j / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(pts[-1])
    return out


for s, gg in GAPGEO.items():
    if gg['kind'] == 'rail':
        rail = catmull(gg['pts'])
        times = [0.0]
        for p, q in zip(rail[:-1], rail[1:]):
            v = math.sqrt(max(0.2, 1.2 + 2 * G * (rail[0].z - (p.z + q.z) / 2) * 0.35))
            times.append(times[-1] + (q - p).length / v)
        sc_ = (gg['t_sw'] - 0.05 - gg['t_rail0']) / times[-1]
        gg['rail'] = rail
        gg['rail_t'] = [gg['t_rail0'] + x * sc_ for x in times]
        gg['rail_c'] = [p + Vector((0, 0, R + 0.008)) for p in rail]


for i_, sw_ in SWOOPS.items():
    rail = catmull(sw_['pts'], 90)
    times = [0.0]
    for p, q in zip(rail[:-1], rail[1:]):
        v = math.sqrt(max(0.3, 1.0 + 2 * G * (rail[0].z - (p.z + q.z) / 2) * 0.5))
        times.append(times[-1] + (q - p).length / v)
    k_ = (sw_['t1'] - sw_['t0']) / times[-1]
    sw_['rail'] = rail
    sw_['rail_t'] = [sw_['t0'] + x * k_ for x in times]
    sw_['rail_c'] = [p + Vector((0, 0, R + 0.008)) for p in rail]


def swoop_pos(sw_, t):
    rt, rc = sw_['rail_t'], sw_['rail_c']
    for j in range(len(rt) - 1):
        if t <= rt[j + 1]:
            return rc[j].lerp(rc[j + 1], (t - rt[j]) / (rt[j + 1] - rt[j]))
    return rc[-1]


def gap_pos(s, t):
    gg = GAPGEO[s]
    L = sec_last[s - 1]
    F = sec_first[s]
    PL, PF = CON[L['i']], CON[F['i']]
    if gg['kind'] == 'rail':
        if t <= gg['t_rail0']:
            return ballistic(PL, L['t'], gg['rail_c'][0], gg['t_rail0'], t)
        rt, rc = gg['rail_t'], gg['rail_c']
        if t <= rt[-1]:
            for j in range(len(rt) - 1):
                if t <= rt[j + 1]:
                    return rc[j].lerp(rc[j + 1], (t - rt[j]) / (rt[j + 1] - rt[j]))
        hit = gg['sw'] + Vector((-(R + 0.012) * gg['d'], 0, 0.02))
        if t <= gg['t_sw']:
            return rc[-1].lerp(hit, (t - rt[-1]) / max(1e-3, gg['t_sw'] - rt[-1]))
        return ballistic(hit, gg['t_sw'], PF, F['t'], t)
    if gg['kind'] == 'chute':
        top_c = gg['top'] + Vector((0, 0, 0.02))
        if t <= gg['t_in']:
            return ballistic(PL, L['t'], top_c, gg['t_in'], t)
        if t <= gg['t_out']:
            k = (t - gg['t_in']) / (gg['t_out'] - gg['t_in'])
            return top_c.lerp(gg['bot'], k * k * 0.35 + k * 0.65)
        return ballistic(gg['bot'], gg['t_out'], PF, F['t'], t)
    # launch
    if t <= gg['t_launch']:
        return PL
    return ballistic(PL, gg['t_launch'], PF, F['t'], t)


ORDER = [h for h in C]


def ball_pos(t):
    if t <= C[0]['t']:
        return CON[0] + Vector((-(C[0]['t'] - t) * 0.5, 0, 0))
    for h0, h1 in zip(ORDER[:-1], ORDER[1:]):
        if h0['t'] <= t <= h1['t']:
            p0, p1 = CON[h0['i']], CON[h1['i']]
            if h1['mech'] == 'bigdrum':
                if t <= h1['launch']:
                    return p0
                return ballistic(p0, h1['launch'], p1, h1['t'], t)
            if h0['s'] != h1['s']:
                return gap_pos(h1['s'], t)
            if h0.get('roll'):
                return p0.lerp(p1, (t - h0['t']) / (h1['t'] - h0['t']))
            if h0['i'] in SWOOPS:
                sw_ = SWOOPS[h0['i']]
                if t <= sw_['t1']:
                    return swoop_pos(sw_, t)
                return ballistic(sw_['rail_c'][-1], sw_['t1'], p1, h1['t'], t)
            return ballistic(p0, h0['t'], p1, h1['t'], t)
    u = t - TF
    return CON[FIN['i']] + Vector((0, 0, max(0.0, 0.12 * math.exp(-u * 2.4) * abs(math.sin(u * 7.5)))))


def vel(t, dt=1 / 240):
    return (ball_pos(t + dt) - ball_pos(t - dt)) / (2 * dt)


def normal_at(h, min_up=0.35):
    vi, vo = vel(h['t'] - 0.004).normalized(), vel(h['t'] + 0.004).normalized()
    n = vo - vi
    if n.length < 1e-3:
        n = Vector((0, 0, 1))
    n.normalize()
    n.y = 0.0
    n.normalize()
    if n.z < min_up:
        n.z = min_up
        n.normalize()
    return n


def orient(o, n):
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = n.to_track_quat('Z', 'Y')


ERAS = getattr(S, 'ERA', None)
CUR_NEON = None


def ncol(m):
    if CUR_NEON:
        return NEON[CUR_NEON[m % len(CUR_NEON)]]
    return NEON[NOTE_COL[m % 12]]


def use_era(s):
    """Switch fixture finish and neon palette to the era of section s (no-op without ERA)."""
    global M_FIX, M_FIX2, M_RAIL, CUR_NEON
    if not ERAS:
        return
    e = ERAS[SONGS[s]['era']]
    key = SONGS[s]['era']
    M_FIX = bpy.data.materials.get('fix_' + key) or mat('fix_' + key, e['fix'], 0.35, metal=e['fix_metal'], coat=0.5)
    M_FIX2 = bpy.data.materials.get('fix2_' + key) or mat('fix2_' + key, tuple(min(1, c * 1.5 + 0.03) for c in e['fix']), 0.3,
                                                          metal=e['fix_metal'])
    M_RAIL = bpy.data.materials.get('rail_' + key) or mat('rail_' + key, tuple(c * 0.8 for c in e['fix']), 0.25, metal=0.9)
    CUR_NEON = e['neon']


# ---------------------------------------------------------------- 2. wall and floor
xs_ = [p.x for p in CON.values()]
zs_ = [p.z for p in CON.values()]
W_X0, W_X1 = min(xs_) - 5, max(xs_) + 5
if ERAS:
    tops = [max(CON[h['i']].z for h in C if h['s'] == s) for s in range(len(SONGS))]
    bots = [min(CON[h['i']].z for h in C if h['s'] == s) for s in range(len(SONGS))]
    bounds = [max(zs_) + 4] + [(bots[s - 1] + tops[s]) / 2 for s in range(1, len(SONGS))] + [min(zs_) - 4]
    for s in range(len(SONGS)):
        e = ERAS[SONGS[s]['era']]
        z0, z1 = bounds[s], bounds[s + 1]
        bpy.ops.mesh.primitive_plane_add(size=1, location=((W_X0 + W_X1) / 2, 0.62, (z0 + z1) / 2), rotation=(math.radians(90), 0, 0))
        wb = add(bpy.context.object, mat(f'wall_{s}', e['wall'], 0.8))
        wb.scale = (W_X1 - W_X0, z0 - z1 + 0.002, 1)
        if s > 0:   # a glowing trim marks the door into the next era, so the seam reads as intentional
            nc = NEON[e['neon'][0]]
            cyl((W_X0, 0.61, z0), (W_X1, 0.61, z0), 0.012, mat(f'eratrim_{s}', nc, 0.3, emit=nc, emit_s=6.0), 10)
else:
    bpy.ops.mesh.primitive_plane_add(size=1, location=((W_X0 + W_X1) / 2, 0.62, (min(zs_) + max(zs_)) / 2),
                                     rotation=(math.radians(90), 0, 0))
    w = add(bpy.context.object, M_WALL)
    w.scale = (W_X1 - W_X0, max(zs_) - min(zs_) + 8, 1)


# ---------------------------------------------------------------- 3. instruments
def stem(c, dz=-0.02):
    cyl((c.x, 0.62, c.z + dz), (c.x, c.y + 0.02, c.z + dz), 0.009, M_RAIL, 10)


def spark(h, col, n=4):
    burst(CON[h['i']] + Vector((0, -0.04, -R)), h['t'], col, n=n, speed=0.7, life=0.28, size=0.007)


def push(o, n, h, dz=0.012):
    base = o.location.copy()
    for u, k in ((-1 / FPS, 0), (0.04, 1), (0.14, -0.3), (0.26, 0)):
        o.location = base - n * dz * k
        o.keyframe_insert('location', frame=fr(h['t'] + u))
    o.location = base


def tile_shelf(run):
    p0, p1 = CON[run[0]['i']], CON[run[-1]['i']]
    d = (p1 - p0).normalized() if (p1 - p0).length > 1e-4 else Vector((1, 0, 0))
    th = math.atan2(-d.z, d.x)
    nrm = Vector((math.sin(th), 0, math.cos(th)))
    a0, a1 = p0 - d * 0.12 - nrm * R, p1 + d * 0.10 - nrm * R
    cube((a0 + a1) / 2 - nrm * 0.014, ((a1 - a0).length, 0.10, 0.028), M_FIX, bevel=0.005, rot=(0, th, 0))
    for sgn in (-1, 1):
        cyl(a0 + Vector((0, sgn * 0.042, 0.006)), a1 + Vector((0, sgn * 0.042, 0.006)), 0.005, M_RAIL, 8)
    seg = (a1 - a0).length / max(1, len(run))
    for h in run:
        col = ncol(h['midi'])
        tm = mat(f'tile{h["i"]}', col, 0.3, emit=col, emit_s=1.5)
        cube(CON[h['i']] - nrm * (R - 0.001), (min(0.1, seg * 0.86), 0.078, 0.007), tm, bevel=0.002, rot=(0, th, 0))
        flash(tm, h['t'], 1.5, 60.0, 9.0)
        spark(h, col, 3)
    for p in (a0 + d * 0.06, a1 - d * 0.06):
        cyl((p.x, 0.62, p.z - 0.12), (p.x, YB + 0.02, p.z - 0.02), 0.008, M_RAIL, 8)


PADRING = {}


def pad(h, r=0.065, spring=False):
    n = normal_at(h)
    c = CON[h['i']] - n * (R + 0.008)
    root = empty(c, f'pad{h["i"]}')
    disc = cyl(c - n * 0.008, c + n * 0.008, r, M_FIX, 40)
    col = ncol(h['midi'])
    rm = mat(f'padring{h["i"]}', col, 0.2, emit=col, emit_s=3.0)
    ring = torus(c + n * 0.007, r - 0.008, 0.009, rm)
    orient(ring, n)
    face = cyl(c + n * 0.006, c + n * 0.009, r * 0.55, M_FIX2, 32)
    for o in (disc, ring, face):
        parent(o, root)
    stem(c)
    flash(rm, h['t'], 3.0, 80.0, 9.0)
    PADRING[h['i']] = (rm, n)
    push(root, n, h, 0.025 if spring else 0.012)
    spark(h, col, 6)
    pulse_ring(c + n * 0.01, h['t'], col, r0=r, r1=r * 2.0, rot=(0, 0, 0))


def again(h):
    prev = h['i'] - 1
    while prev not in PADRING and prev > 0:
        prev -= 1
    if prev in PADRING:
        rm, n = PADRING[prev]
        flash(rm, h['t'], 9.0, 80.0, 9.0)
    spark(h, ncol(h['midi']), 4)


def block(h):
    n = normal_at(h)
    c = CON[h['i']] - n * (R + 0.022)
    o = cube(c, (0.15, 0.075, 0.044), M_FIX2, bevel=0.006)
    orient(o, n)
    col = ncol(h['midi'])
    lm = mat(f'blockled{h["i"]}', col, 0.2, emit=col, emit_s=2.0)
    strip = cube(c + n * 0.023 + Vector((0, -0.038, 0)), (0.13, 0.008, 0.012), lm)
    orient(strip, n)
    parent(strip, o)
    stem(c, 0)
    flash(lm, h['t'], 2.0, 70.0, 8.0)
    PADRING[h['i']] = (lm, n)
    push(o, n, h)
    spark(h, col, 6)


def xylo(h):
    n = normal_at(h)
    c = CON[h['i']] - n * (R + 0.01)
    col = ncol(h['midi'])
    root = empty(c, f'xy{h["i"]}')
    base = cube(c - n * 0.016, (0.17, 0.08, 0.016), M_FIX, bevel=0.004)
    barm = mat(f'xbar{h["i"]}', (0.85, 0.86, 0.9), 0.15, metal=1.0, emit=col, emit_s=0.3)
    bar = cube(c, (0.15, 0.058, 0.014), barm, bevel=0.003)
    for o in (base, bar):
        orient(o, n)
        parent(o, root)
    stem(c)
    flash(barm, h['t'], 0.3, 22.0, 3.0)
    push(root, n, h, 0.01)
    spark(h, col, 5)


def bell(h):
    c = CON[h['i']] - Vector((0, 0, R))
    col = ncol(h['midi'])
    hang = empty(c + Vector((0, 0, -0.10)), f'bellh{h["i"]}')
    bm = mat(f'bell{h["i"]}', (0.1, 0.1, 0.11), 0.25, metal=0.8)
    cap = sphere(c - Vector((0, 0, 0.012)), 0.022, M_FIX2, scale=(1, 1, 0.6))
    body = cone(c - Vector((0, 0, 0.06)), 0.065, 0.024, 0.09, bm)
    rm = mat(f'bellrim{h["i"]}', col, 0.2, emit=col, emit_s=3.0)
    rim = torus(c - Vector((0, 0, 0.105)), 0.065, 0.007, rm)
    for o in (cap, body, rim):
        parent(o, hang)
    cyl((c.x, 0.62, c.z - 0.10), (c.x, YB + 0.02, c.z - 0.10), 0.007, M_RAIL, 8)
    flash(rm, h['t'], 3.0, 70.0, 8.0)
    wobble(hang, h['t'], axis=1, amp=12)
    PADRING[h['i']] = (rm, Vector((0, 0, 1)))
    spark(h, col, 5)


def cymbal(h):
    n = normal_at(h, 0.5)
    c = CON[h['i']] - n * (R + 0.004)
    root = empty(c, f'cym{h["i"]}')
    disc = cyl(c - n * 0.003, c + n * 0.003, 0.10, M_BRASS, 48)
    rm = mat(f'cymrim{h["i"]}', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=1.5)
    rim = torus(c, 0.10, 0.005, rm)
    orient(rim, n)
    for o in (disc, rim):
        parent(o, root)
    cyl(c, (c.x, c.y, c.z - 0.12), 0.006, M_RAIL, 8)
    stem(Vector((c.x, c.y, c.z - 0.12)), 0)
    wobble(root, h['t'], axis=1, amp=12)
    flash(rm, h['t'], 1.5, 50.0, 5.0)
    PADRING[h['i']] = (rm, n)
    burst(CON[h['i']] + Vector((0, -0.04, -R)), h['t'], NEON['amber'], n=10, speed=1.0)


def flask(h):
    c = CON[h['i']] - Vector((0, 0, R))
    col = ncol(h['midi'])
    gm = mat(f'flask{h["i"]}', tuple(0.3 + 0.7 * x for x in col), 0.04, trans=1.0, emit=col, emit_s=0.5)
    root = empty(c + Vector((0, 0, -0.16)), f'flaskr{h["i"]}')
    body = sphere(c + Vector((0, 0, -0.115)), 0.055, gm, scale=(1, 1, 1.15), segs=32)
    neck = cyl(c + Vector((0, 0, -0.07)), c + Vector((0, 0, -0.012)), 0.018, gm, 20)
    cork = cyl(c + Vector((0, 0, -0.014)), c, 0.02, mat('cork', (0.55, 0.36, 0.2), 0.7), 16)
    for o in (body, neck, cork):
        parent(o, root)
    cyl(c + Vector((0, 0, -0.175)), c + Vector((0, 0, -0.24)), 0.006, M_RAIL, 8)
    stem(c + Vector((0, 0, -0.24)), 0)
    flash(gm, h['t'], 0.5, 18.0, 2.0)
    wobble(root, h['t'], axis=1, amp=8)
    spark(h, col, 5)


def pipe(h):
    c = CON[h['i']] - Vector((0, 0, R))
    col = ncol(h['midi'])
    length = 0.18 + max(0.0, (84 - h['midi'])) * 0.012
    cyl(c - Vector((0, 0, length)), c, 0.032, M_FIX2, 28)
    cyl(c - Vector((0, 0, length)), c - Vector((0, 0, length + 0.05)), 0.018, M_FIX, 16)
    lm = mat(f'pipe{h["i"]}', col, 0.2, emit=col, emit_s=2.0)
    torus(c - Vector((0, 0, 0.004)), 0.03, 0.007, lm)
    cube(c - Vector((0, 0.03, length * 0.75)), (0.03, 0.004, 0.012), lm)
    stem(c - Vector((0, 0, length * 0.5)), 0)
    flash(lm, h['t'], 2.0, 70.0, 8.0)
    spark(h, col, 5)


def bumper(h):
    z = CON[h['i']].z
    cx = CON[h['i']].x + h['side'] * (0.055 + R)
    col = ncol(h['midi'])
    cyl((cx, 0.62, z), (cx, YB - 0.035, z), 0.055, M_FIX, 40)
    rm = mat(f'bumprim{h["i"]}', col, 0.2, emit=col, emit_s=3.0)
    rim = torus((cx, YB - 0.036, z), 0.055, 0.009, rm, rot=(math.radians(90), 0, 0))
    flash(rm, h['t'], 3.0, 80.0, 9.0)
    for u, sk in ((-1 / FPS, 1.0), (0.04, 1.18), (0.2, 1.0)):
        rim.scale = (sk, sk, sk)
        rim.keyframe_insert('scale', frame=fr(h['t'] + u))
    spark(h, col, 6)


def swoop(h):
    sw_ = SWOOPS[h['i']]
    rail = sw_['rail']
    for sgn in (-1, 1):
        pts = [p + Vector((0, sgn * 0.03, 0)) for p in rail]
        for p, q in zip(pts[:-1:3], pts[3::3]):
            cyl(p, q, 0.005, M_RAIL, 8)
    for p in rail[::15]:
        cyl(p + Vector((0, -0.035, -0.006)), p + Vector((0, 0.035, -0.006)), 0.004, M_RAIL, 6)
        cyl((p.x, 0.62, p.z - 0.05), (p.x, YB + 0.03, p.z - 0.006), 0.006, M_RAIL, 8)
    col = ncol(h['midi'])
    gm = mat(f'gate{h["i"]}', col, 0.2, emit=col, emit_s=3.0)
    g0 = rail[0] + Vector((0, 0, 0.0))
    torus(g0 + Vector((0, 0, R + 0.01)), R + 0.03, 0.008, gm, rot=(0, math.radians(90), 0))
    flash(gm, h['t'], 3.0, 80.0, 9.0)
    # LED strip along the rail that lights up behind the ball
    for j, (p, tt_) in enumerate(zip(rail[6::10], sw_['rail_t'][6::10])):
        lm = mat(f'swled{h["i"]}_{j}', col, 0.2, emit=col, emit_s=0.3)
        sphere(p + Vector((0, -0.036, -0.004)), 0.006, lm, segs=8)
        emit_keys(lm, ((tt_ - 1 / FPS, 0.3), (tt_, 30), (tt_ + 0.4, 3)))
    spark(h, col, 6)


def spill(h):
    col = ncol(h['midi'])
    ld = bpy.data.lights.new(f'spill{h["i"]}', 'POINT')
    ld.color, ld.shadow_soft_size = col, 0.04
    lo = bpy.data.objects.new(f'spill{h["i"]}', ld)
    sc.collection.objects.link(lo)
    lo.location = CON[h['i']] + Vector((0, -0.06, -R))
    for t_, e_ in ((h['t'] - 1 / FPS, 0.0), (h['t'], 6.0), (h['t'] + 0.3, 0.0)):
        ld.energy = e_
        ld.keyframe_insert('energy', frame=fr(max(0.0, t_)))


BUILD = dict(swoop=swoop, pad=pad, again=again, block=block, xylo=xylo, bell=bell, cymbal=cymbal, flask=flask, pipe=pipe,
             bumper=bumper)
k = 0
cur_s = -1
while k < len(C) - 1:
    h = C[k]
    if h['s'] != cur_s:
        cur_s = h['s']
        use_era(cur_s)
    if h['mech'] == 'tile':
        run = [h]
        while k + len(run) < len(C) - 1 and C[k + len(run)]['mech'] == 'tile' and C[k + len(run)]['s'] == h['s']:
            run.append(C[k + len(run)])
        tile_shelf(run)
        k += len(run)
        continue
    if h['mech'] == 'cup':
        pad(h, r=0.075, spring=True)
    else:
        BUILD[h['mech']](h)
    if h['mech'] != 'again':
        spill(h)
    k += 1

# ---------------------------------------------------------------- 4. gap machinery
blue_at = None
for s, gg in GAPGEO.items():
    g = gap_into[s]
    use_era(s)
    if gg['kind'] == 'rail':
        rail = gg['rail']
        for sgn in (-1, 1):
            pts = [p + Vector((0, sgn * 0.03, 0)) for p in rail]
            for p, q in zip(pts[:-1:3], pts[3::3]):
                cyl(p, q, 0.005, M_RAIL, 8)
        for p in rail[::12]:
            cyl((p.x, 0.62, p.z - 0.05), (p.x, YB + 0.03, p.z - 0.006), 0.006, M_RAIL, 8)
        sw = gg['sw']
        sx = 0.035 * gg['d']
        cube(sw + Vector((sx, 0.24, 0.0)), (0.07, 0.02, 0.12), mat('switchplate', (0.85, 0.86, 0.88), 0.3, metal=0.9), bevel=0.006)
        tog = empty(sw + Vector((sx, 0.22, 0.0)), f'toggle{s}')
        lever = cube(sw + Vector((sx, 0.13, 0.02)), (0.018, 0.17, 0.018), M_FIX, bevel=0.004)
        parent(lever, tog)
        for t, ang in ((gg['t_sw'] - 1 / FPS, 0.0), (gg['t_sw'] + 0.05, -35.0)):
            tog.rotation_euler.x = math.radians(ang)
            tog.keyframe_insert('rotation_euler', index=0, frame=fr(t))
        led = mat(f'swled{s}', NEON['lime'], 0.2, emit=NEON['lime'], emit_s=0.0)
        sphere(sw + Vector((sx, 0.225, 0.045)), 0.008, led, segs=10)
        emit_keys(led, ((gg['t_sw'] - 1 / FPS, 0.0), (gg['t_sw'], 25.0)))
        if blue_at is None:
            blue_at = sw
    elif gg['kind'] == 'chute':
        top, bot = gg['top'], gg['bot']
        cone(top + Vector((0, 0, 0.05)), 0.03 + R, 0.10, 0.10, M_FIX2)
        tube = cyl(top, bot, R + 0.012, M_GLASS, 32)
        for j, k_ in enumerate((0.25, 0.5, 0.75)):
            # time when the ball passes this point of the tube (inverse of the easing used in gap_pos)
            a_, b_ = 0.35, 0.65
            kk = (-b_ + math.sqrt(b_ * b_ + 4 * a_ * k_)) / (2 * a_)
            tb = gg['t_in'] + kk * (gg['t_out'] - gg['t_in'])
            p = top.lerp(bot, k_)
            rm = mat(f'chutering{s}_{j}', NEON['cyan'], 0.2, emit=NEON['cyan'], emit_s=0.5)
            torus(p, R + 0.016, 0.006, rm)
            emit_keys(rm, ((tb - 1 / FPS, 0.5), (tb, 40), (tb + 0.35, 4)))
        stem(top.lerp(bot, 0.5), 0)
        cyl(bot, bot + Vector((0.12 * -gg['d'], 0, -0.04)), R + 0.01, M_FIX2, 24)
    # launch gaps reuse the cup (built above)

# ---------------------------------------------------------------- 5. final drum and characters
DC = CON[FIN['i']]
DX, DZ = DC.x, DC.z - R - 0.004
cyl((DX, YB, DZ - 0.12), (DX, YB, DZ), 0.2, mat('bigshell', (0.05, 0.05, 0.06), 0.25, coat=1.0), 48)
big_rim = mat('bigrim', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=4.0)
torus((DX, YB, DZ), 0.2, 0.012, big_rim)
big_head = mat('bighead', (0.95, 0.95, 0.97), 0.35, emit=(1.0, 0.35, 0.7), emit_s=0.0)
cyl((DX, YB, DZ), (DX, YB, DZ + 0.004), 0.186, big_head, 48)
emit_keys(big_rim, ((TF - 1 / FPS, 4.0), (TF, 60), (TF + 1.2, 10)))
emit_keys(big_head, ((TF - 1 / FPS, 0.0), (TF, 22), (TF + 1.2, 2)))
cyl((DX, YB, DZ - 0.12), (DX, YB, DZ - 1.0), 0.04, M_RAIL)
pulse_ring(Vector((DX, YB, DZ + 0.01)), TF, NEON['magenta'], r0=0.2, r1=0.85, life=0.5, rot=(0, 0, 0))
burst(Vector((DX, YB - 0.04, DZ + 0.02)), TF, NEON['magenta'], n=18, speed=1.7, life=0.5)
yel = character(DX + 0.55, DZ + 0.02, (0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo', 'yel')
pink = character(DX - 0.55, DZ + 0.02, (0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears', 'pink')
# blue watches the first gap: the first switch if there is a rail gap, otherwise the first chute or cup
if blue_at is None:
    g0 = GAPGEO[min(GAPGEO)]
    blue_at = (g0.get('top') or g0.get('cup')) + Vector((-0.55 * g0['d'], 0, -0.15))   # beside the machine, not over it
blue = character(blue_at.x + 0.05, blue_at.z + 0.62, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'blue')
WATCHERS = []
designs = [((0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears'), ((0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo'),
           ((0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna')]
for n_, (s_, gg_) in enumerate(sorted(GAPGEO.items())):
    if n_ == 0:
        continue                       # the first gap already has blue
    anchor = gg_.get('sw') or gg_.get('top') or gg_.get('cup')
    bc, ic, acc = designs[n_ % 3]
    wch = character(anchor.x - 0.5 * gg_['d'], anchor.z + 0.45, bc, ic, acc, f'watch{n_}')
    t_ev = gg_.get('t_sw') or gg_.get('t_in') or gg_.get('t_launch')
    WATCHERS.append((wch, t_ev))
for ch in (yel, pink, blue) + tuple(w for w, _ in WATCHERS):
    r0 = ch['root']
    holder = empty((r0.location.x, r0.location.y, r0.location.z - 0.49), r0.name + '_holder')
    bpy.context.view_layer.update()
    parent(r0, holder)
    holder.scale = (0.68, 0.68, 0.68)
t_c = TF + 0.9
for kk in range(80):
    cn = rng.choice(list(NEON))
    o = cube((0, 0, 0), (0.018, 0.004, 0.011), mat(f'conf{kk}', NEON[cn], 0.3, emit=NEON[cn], emit_s=rng.uniform(6, 14)))
    key_vis(o, t_c)
    v = Vector((rng.uniform(-1.4, 1.4), rng.uniform(-0.9, 0.1), rng.uniform(2.6, 4.6)))
    p0 = Vector((DX + rng.uniform(-0.1, 0.1), YB - 0.05, DZ + 0.05))
    sp = Vector((rng.uniform(-14, 14), rng.uniform(-14, 14), rng.uniform(-14, 14)))
    u = 0.0
    while t_c + u <= T_END + 0.2:
        drag = 1.0 - math.exp(-u * 1.6)
        o.location = p0 + v * (drag / 1.6) + Vector((0.08 * math.sin(u * 5 + kk), 0, -0.45 * u * u - 0.35 * u))
        o.rotation_euler = sp * u
        o.keyframe_insert('location', frame=fr(t_c + u))
        o.keyframe_insert('rotation_euler', frame=fr(t_c + u))
        u += 0.12

# ---------------------------------------------------------------- 6. marble
core_m = bpy.data.materials.new('marblecore')
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
e.color = (1.0, 0.35, 0.02, 1)
nt_.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 2.4
bsdf.inputs['Roughness'].default_value = 0.08
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

# ---------------------------------------------------------------- 7. acting
for ch in (yel, pink, blue) + tuple(w for w, _ in WATCHERS):
    track_eyes(ch, ball_pos)
for wch, t_ev in WATCHERS:
    mouth_o(wch, t_ev - 0.1, t_ev + 0.8, 1.7)
    hop(wch, t_ev + 0.1, 0.12)
g_blue = next((gg for gg in GAPGEO.values() if gg['kind'] == 'rail'), GAPGEO[min(GAPGEO)])
t_blue = g_blue.get('t_sw') or g_blue.get('t_in') or g_blue.get('t_launch')
mouth_o(blue, t_blue - 0.1, t_blue + 0.9, 1.7)
hop(blue, t_blue + 0.15, 0.14)
for ch in (yel, pink):
    mouth_o(ch, FIN['launch'] + 0.1, FIN['launch'] + 0.9, 1.5)
    hop(ch, TF + 0.02, 0.2)
    hop(ch, TF + 0.65, 0.12)
    mouth_o(ch, TF, TF + 1.8, 2.0)

# ---------------------------------------------------------------- 8. camera (16:9, side-scrolling three-quarter view)
bpy.ops.object.camera_add(location=(0, -4, 0))
cam = bpy.context.object
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 4.5
sc.camera = cam
OFF = Vector((0.42, -2.25, 0.32))
LAUNCHES = [(gg['t_launch'], sec_first[s]['t'], (gg['cup'] + CON[sec_first[s]['i']]) / 2) for s, gg in GAPGEO.items()
            if gg['kind'] == 'launch']
LAUNCHES.append((FIN['launch'], TF, (CON[LASTCUP['i']] + DC) / 2))


def target(t):
    acc, wsum = Vector((0, 0, 0)), 0.0
    for j in range(6):
        wgt = 1.0 / (1 + j)
        acc += ball_pos(max(0.0, t - j * 0.035)) * wgt
        wsum += wgt
    p = acc / wsum
    p.y = YB
    return p + Vector((0.08, 0, -0.06))


def cam_at(t):
    tg, off, lens = target(t), OFF.copy(), 42.0
    for tl, tland, mid in LAUNCHES:
        kl = smooth((t - (tl - 0.4)) / 0.5) * (1 - smooth((t - (tland + 0.2)) / 0.7))
        off = off * (1 + 0.5 * kl)
        tg = tg.lerp(mid + Vector((0, 0, 0.45)), 0.7 * kl)
    kh = smooth((t - (TF - 0.2)) / 0.8)
    tg = tg.lerp(DC + Vector((0, 0, 0.05)), kh)
    kr = smooth((t - (TF + 1.3)) / 2.6)
    off = off * (1 + 1.6 * kr)
    tg = tg + Vector((-0.8, 0, 0.5)) * kr
    return tg, off, lens


f = 1
while f <= N:
    t = (f - 1) / FPS
    tg, off, lens = cam_at(t)
    cam.location = tg + off
    cam.rotation_euler = (-off).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.dof.focus_distance = off.length
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_euler', frame=f)
    cam.data.keyframe_insert('lens', frame=f)
    cam.data.dof.keyframe_insert('focus_distance', frame=f)
    f += 2

world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.56, 0.58, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.4
bpy.ops.object.light_add(type='SUN', location=(0, -3, 5))
sun = bpy.context.object
sun.data.energy, sun.data.angle, sun.data.color = 2.0, math.radians(24), (1.0, 0.97, 0.94)
sun.rotation_euler = Vector((0.55, 1.0, -1.1)).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.light_add(type='SUN', location=(0, -3, 5))
fill = bpy.context.object
fill.data.energy, fill.data.angle, fill.data.color = 0.6, math.radians(40), (0.9, 0.93, 1.0)
fill.rotation_euler = Vector((-0.8, 1.0, 0.1)).to_track_quat('-Z', 'Y').to_euler()
sc.view_settings.look = 'AgX - Medium High Contrast'
sc.view_settings.exposure = -0.35
sc.use_nodes = True
nt = sc.node_tree
gl = nt.nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.size = 7
if hasattr(gl, 'threshold'):
    gl.threshold = 1.6
nt.links.new(nt.nodes['Render Layers'].outputs['Image'], gl.inputs['Image'])
nt.links.new(gl.outputs['Image'], nt.nodes['Composite'].inputs['Image'])

print('frames total', N, 'seconds', round(T_END, 2), 'objects', len(bpy.data.objects))
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
