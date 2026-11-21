"""v2: neon marble machine plays "Für Elise", built to hold attention for the whole Short.

Beats (times from score2.py):
  hook     the ball sits in the yellow character's halo; she hops and it pops onto the first bar
  phrase A each note is a bar; long notes tip a lever that starts three dominoes (the left-hand bass)
  save     the blue character bats the ball back up with a paddle (that swing is a note)
  phrase B same melody, the lit bars now form a trail of light above
  finale   the drum; four little balls ring four bells; light confetti
  reveal   the camera pulls far back to show the whole lit machine and all three characters

    python short2.py -- --res 720x1280 --samples 20 --out frames/f_#### [--frames 1-40] [--stills 8,120]
"""
import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score2 as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--res', default='720x1280')
ap.add_argument('--samples', type=int, default=20)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--out', default='frames/f_####')
ap.add_argument('--frames', default='')
ap.add_argument('--stills', default='', help='comma-separated frame numbers to render as stills')
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
W, H = (int(v) for v in a.res.split('x'))
FPS = a.fps
G = 9.81
R = 0.045            # ball radius
BAR_T, BAR_W = 0.045, 0.13
rng = random.Random(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.fps = FPS
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
sc.render.use_persistent_data = True
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.45
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'
world = bpy.data.worlds.new('w')
sc.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.004, 0.012, 1)

MEL = S.melody()
BASS = S.bass()
TAG = S.tag()
TL = S.t_last()
T_END = S.total_seconds()
N = int(round(T_END * FPS))
sc.frame_start, sc.frame_end = 1, N


def fr(t):
    return 1 + t * FPS


def smooth(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


# ---------------------------------------------------------------- helpers
def mat(name, col, rough=0.4, metal=0.0, emit=None, emit_s=0.0, coat=0.0, alpha=1.0, trans=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
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
        sock.keyframe_insert('default_value', frame=fr(t))


def add(o, m):
    o.data.materials.append(m)
    return o


def cube(loc, scale, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
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


def cyl(p0, p1, r, m, verts=20):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    bpy.ops.object.shade_smooth()
    return add(o, m)


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
    """Hide an object (render) outside [t_on, t_off]."""
    for t, hide in ((t_on - 1 / FPS, True), (t_on, False)) + (((t_off, False), (t_off + 1 / FPS, True)) if t_off else ()):
        o.hide_render = hide
        o.keyframe_insert('hide_render', frame=fr(max(0.0, t)))


NEON = {'cyan': (0.05, 0.85, 1.0), 'magenta': (1.0, 0.08, 0.55), 'violet': (0.55, 0.2, 1.0),
        'lime': (0.45, 1.0, 0.25), 'amber': (1.0, 0.6, 0.08), 'white': (1.0, 0.9, 0.95)}
M_WALL = mat('wall', (0.025, 0.025, 0.035), 0.55)
M_BRASS = mat('brass', (0.85, 0.62, 0.25), 0.22, metal=1.0)
M_CHROME = mat('chrome', (0.9, 0.9, 0.95), 0.08, metal=1.0)
M_DARK = mat('dark', (0.02, 0.02, 0.025), 0.25, coat=0.8)
M_WHITE = mat('eyewhite', (0.95, 0.95, 0.97), 0.25)
M_HI = mat('hilite', (1, 1, 1), 0.2, emit=(1, 1, 1), emit_s=4)
M_PUPIL = mat('pupil', (0.01, 0.01, 0.02), 0.2)


# ---------------------------------------------------------------- the ball path
def contact_of(h):
    return Vector((h['x'], 0.30, h['z'] + R))


PATH = []   # (time, centre) contacts; the ball flies an exact parabola between consecutive ones


def ballistic(p0, t0, p1, t1, t):
    T = t1 - t0
    v = (p1 - p0 + Vector((0, 0, 0.5 * G * T * T))) / T
    u = t - t0
    return p0 + v * u + Vector((0, 0, -0.5 * G * u * u))


# ---------------------------------------------------------------- wall, depth layers
Z_TOP, Z_BOT = 3.5, MEL[-1]['z'] - 3.0
for k in range(-22, 23):
    cube((k * 0.16, 0.6, (Z_TOP + Z_BOT) / 2), (0.14, 0.06, Z_TOP - Z_BOT), M_WALL, bevel=0.01)
# a few dim vertical neon tubes set into the wall for depth
for k, cn in ((-19, 'magenta'), (-11, 'cyan'), (-6, 'violet'), (4, 'magenta'), (9, 'cyan'), (13, 'violet'), (20, 'cyan')):
    cyl((k * 0.16 + 0.08, 0.55, Z_TOP), (k * 0.16 + 0.08, 0.55, Z_BOT), 0.006,
        mat('tube' + cn, NEON[cn], 0.3, emit=NEON[cn], emit_s=0.9), 8)
# foreground floating light motes (out of focus bokeh)
for k in range(46):
    c = NEON[rng.choice(['cyan', 'magenta', 'violet', 'amber'])]
    sphere((rng.uniform(-1.6, 1.6), rng.uniform(-3.0, -1.6), rng.uniform(Z_BOT, 1.2)), rng.uniform(0.006, 0.014),
           mat(f'mote{k}', c, 0.5, emit=c, emit_s=rng.uniform(3, 9)), segs=8)


# ---------------------------------------------------------------- hit effects
def burst(p, t, col, n=7, speed=0.9, life=0.35, size=0.009):
    m = mat('spark', col, 0.3, emit=col, emit_s=30)
    for j in range(n):
        ang = rng.uniform(0, 2 * math.pi)
        v = Vector((math.cos(ang) * speed * rng.uniform(0.5, 1.0), -rng.uniform(0.0, 0.25),
                    abs(math.sin(ang)) * speed * rng.uniform(0.6, 1.2) + 0.3))
        o = sphere(p, size, m, segs=8)
        key_vis(o, t, t + life)
        for u in (0.0, life * 0.33, life * 0.66, life):
            o.location = p + v * u + Vector((0, 0, -0.5 * G * u * u))
            s = 1.0 - (u / life) * 0.9
            o.scale = (s, s, s)
            o.keyframe_insert('location', frame=fr(t + u))
            o.keyframe_insert('scale', frame=fr(t + u))


def ripple(p, t, col, r0=0.04, r1=0.15, life=0.28):
    rm = mat('ripple', col, 0.2, emit=col, emit_s=14)
    emit_keys(rm, ((t, 14), (t + life, 0.5)))
    o = torus(p, 1.0, 0.03, rm, rot=(math.radians(90), 0, 0))
    key_vis(o, t, t + life)
    for u, r in ((0.0, r0), (life, r1)):
        o.scale = (r, r, r * 0.4)
        o.keyframe_insert('scale', frame=fr(t + u))


# ---------------------------------------------------------------- characters
def character(x, z, body_col, iris_col, accent, name, eye_r=0.088):
    root = empty((x, 0.15, z), name)
    look = empty((x, 0.0, z + 0.15), name + '_look')
    parent(look, root)
    parts = [cube((x, 0.15, z - 0.42), (0.34, 0.30, 0.14), M_BRASS, bevel=0.02)]
    bm = mat(name + 'body', body_col, 0.35, coat=0.8)
    parts.append(cyl((x, 0.15, z - 0.35), (x, 0.15, z - 0.12), 0.12, bm))
    parts.append(sphere((x, 0.15, z + 0.12), 0.23, bm, segs=40))
    if accent == 'antenna':
        parts.append(cyl((x, 0.15, z + 0.33), (x + 0.03, 0.15, z + 0.48), 0.008, M_CHROME))
        parts.append(sphere((x + 0.03, 0.15, z + 0.49), 0.03, mat('ant', NEON['cyan'], 0.2, emit=NEON['cyan'], emit_s=15)))
    elif accent == 'halo':
        parts.append(torus((x, 0.15, z + 0.41), 0.11, 0.013, mat('halo', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=12)))
    elif accent == 'ears':
        for s in (-1, 1):
            parts.append(sphere((x + s * 0.15, 0.15, z + 0.33), 0.06, bm, scale=(0.7, 0.7, 1.4)))
            parts.append(sphere((x + s * 0.15, 0.10, z + 0.34), 0.025,
                                mat('earglow', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=8), scale=(0.7, 0.4, 1.4)))
    irises = []
    for s in (-1, 1):
        c = Vector((x + s * 0.09, -0.03, z + 0.15))
        parts.append(sphere(c, eye_r, M_WHITE, scale=(1.0, 0.45, 1.15)))
        ic = c + Vector((0, -eye_r * 0.42, 0))
        im = mat(name + 'iris', iris_col, 0.2, emit=iris_col, emit_s=1.2)
        irises.append(sphere(ic, eye_r * 0.62, im, scale=(1.0, 0.35, 1.1)))
        irises.append(sphere(ic + Vector((0, -eye_r * 0.18, 0)), eye_r * 0.30, M_PUPIL, scale=(1, 0.35, 1.1)))
        irises.append(sphere(ic + Vector((eye_r * 0.22, -eye_r * 0.30, eye_r * 0.28)), eye_r * 0.13, M_HI))
    mouth = torus((x, -0.07, z + 0.0), 0.035, 0.007, mat(name + 'mouth', (0.15, 0.02, 0.05), 0.4),
                  rot=(math.radians(90), 0, 0))
    parts.append(mouth)
    for o in parts:
        parent(o, root)
    for o in irises:
        parent(o, look)
    return dict(root=root, look=look, mouth=mouth, z0=z, x0=x)


def track_eyes(ch, pos_fn, t0=0.0, t1=None):
    t1 = T_END if t1 is None else t1
    f = int(fr(t0))
    while f <= fr(t1):
        t = (f - 1) / FPS
        b = pos_fn(t)
        d = b - (ch['root'].location + Vector((0, 0, 0.15)))
        ch['look'].delta_location = (max(-1, min(1, d.x / 0.6)) * 0.024, 0, max(-1, min(1, d.z / 0.8)) * 0.028)
        ch['look'].keyframe_insert('delta_location', frame=f)
        f += 2


def hop(ch, t, h=0.15, squash=True):
    r = ch['root']
    for u, dz, sq in ((-0.06, 0, 1.0), (0.0, -0.03, 0.88), (0.14, h, 1.08), (0.30, 0.0, 0.92), (0.40, 0, 1.0)):
        r.location.z = ch['z0'] + dz
        r.keyframe_insert('location', index=2, frame=fr(t + u))
        if squash:
            r.scale = (1 / sq ** 0.5, 1, sq)
            r.keyframe_insert('scale', frame=fr(t + u))


def mouth_o(ch, t0, t1, s=1.9):
    m = ch['mouth']
    for t, k in ((t0 - 0.05, 1.0), (t0 + 0.08, s), (t1, s), (t1 + 0.2, 1.0)):
        m.scale = (k, k * (1.3 if k > 1 else 1), k)
        m.keyframe_insert('scale', frame=fr(t))


# ---------------------------------------------------------------- bars, levers, dominoes
def bar_colour(midi):
    return NEON[S.PC_COLOUR[midi % 12]]


bar_objs = {}
for h in MEL:
    if h['kind'] not in ('bar', 'lever'):
        continue
    col = bar_colour(h['midi'])
    m = mat(f'bar{h["i"]}', col, 0.25, emit=col, emit_s=1.0)
    zc = h['z'] - BAR_T / 2
    bar = cube((h['x'], 0.30, zc), (BAR_W, 0.10, BAR_T), m, bevel=0.01)
    for s in (-1, 1):
        cyl((h['x'] + s * BAR_W * 0.33, 0.56, zc), (h['x'] + s * BAR_W * 0.33, 0.30, zc), 0.006, M_CHROME, 8)
    emit_keys(m, ((h['t'] - 1 / FPS, 1.0), (h['t'], 32.0), (h['t'] + 0.35, 5.5)))
    for t, dz in ((h['t'] - 1 / FPS, 0.0), (h['t'] + 0.04, -0.02), (h['t'] + 0.16, 0.005), (h['t'] + 0.3, 0.0)):
        bar.location.z = zc + dz
        bar.keyframe_insert('location', index=2, frame=fr(t))
    burst(Vector((h['x'], 0.24, h['z'])), h['t'], col)
    ripple(Vector((h['x'], 0.24, h['z'] - 0.01)), h['t'], col)
    bar_objs[h['i']] = (bar, zc, m)

DOM_H, DOM_T, DOM_GAP = 0.19, 0.034, 0.105
dominoes = []
for h in MEL:
    if h['kind'] != 'lever':
        continue
    prev = MEL[h['i'] - 1]
    side = 1.0 if h['x'] - prev['x'] <= 0 else -1.0
    side = -side if False else side
    # put the row on the side away from the bar the ball came from
    side = -1.0 if prev['x'] > h['x'] else 1.0
    bar, zc, bm = bar_objs[h['i']]
    # the lever: the bar tips toward the row and knocks the first domino
    for t, ang in ((h['t'] - 1 / FPS, 0.0), (h['t'] + 0.06, 14.0), (h['t'] + 0.35, 10.0), (h['t'] + 0.8, 0.0)):
        bar.rotation_euler.y = math.radians(ang) * side
        bar.keyframe_insert('rotation_euler', index=1, frame=fr(t))
    shelf_z = h['z'] - 0.075
    x0 = h['x'] + side * (BAR_W / 2 + 0.03)
    xs = [x0 + side * k * DOM_GAP for k in range(3)]
    cube(((xs[0] + xs[-1]) / 2 + side * 0.03, 0.30, shelf_z - 0.012), (abs(xs[-1] - xs[0]) + 0.16, 0.12, 0.024), M_BRASS,
         bevel=0.004)
    group = [b for b in BASS if b['group'] == h['i']]
    colname = 'amber' if h['name'] == 'B4' else 'violet'
    for k, (xk, b) in enumerate(zip(xs, group)):
        dm = mat(f'dom{h["i"]}_{k}', (0.03, 0.03, 0.04), 0.2, emit=NEON[colname], emit_s=0.6, coat=0.9)
        bpy.ops.mesh.primitive_cube_add(size=1)
        d = bpy.context.object
        d.scale = (DOM_T, 0.09, DOM_H)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        # pivot on the bottom edge it tips over
        d.data.transform(Matrix.Translation((side * DOM_T / 2, 0, DOM_H / 2)))
        d.location = (xk - side * DOM_T / 2, 0.30, shelf_z)
        add(d, dm)
        # neon edge strip on the top
        e = cube((xk, 0.26, shelf_z + DOM_H - 0.008), (DOM_T * 0.9, 0.012, 0.01),
                 mat(f'domedge{h["i"]}_{k}', NEON[colname], 0.2, emit=NEON[colname], emit_s=4))
        parent(e, d)
        t0 = b['t']
        lean = math.degrees(math.asin((DOM_GAP - DOM_T) / DOM_H))
        last = k == 2
        keys = [(t0 - 1 / FPS, 0.0), (t0 + S.UNIT * 0.55, lean * 0.35), (t0 + S.UNIT, lean if not last else 55.0)]
        keys += [(t0 + S.UNIT + 0.25, lean + 18 if not last else 84.0)]
        if not last:
            keys += [(group[-1]['t'] + S.UNIT + 0.3, 62.0 - 12 * k)]
        for t, ang in keys:
            d.rotation_euler.y = math.radians(ang) * side
            d.keyframe_insert('rotation_euler', index=1, frame=fr(t))
        emit_keys(dm, ((t0 - 1 / FPS, 0.6), (t0 + 0.05, 9.0), (t0 + 0.5, 2.5)))
        burst(Vector((xk + side * 0.05, 0.24, shelf_z + 0.02)), t0 + S.UNIT * 0.9, NEON[colname], n=4, speed=0.5,
              life=0.25, size=0.006)
        dominoes.append(d)

# ---------------------------------------------------------------- characters in the machine
first = MEL[0]
yel = character(0.22, 0.30, (0.95, 0.85, 0.25), (1.0, 0.3, 0.7), 'halo', 'yel')
BALL0 = Vector((0.22, 0.15, 0.30 + 0.41 + 0.035))   # resting in her halo
pad_h = MEL[S.PADDLE_INDEX]
C_pad = contact_of(pad_h)
PADDLE_L = 0.17
pivot = Vector((C_pad.x - (PADDLE_L + R + 0.008), 0.30, C_pad.z))
blue = character(pivot.x - 0.14, C_pad.z + 0.15, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'blue')
piv = empty(pivot, 'paddle_pivot')
M_PAD = mat('paddle', NEON['cyan'], 0.3, emit=NEON['cyan'], emit_s=6)
handle = cyl(pivot, pivot + Vector((PADDLE_L - 0.01, 0, 0)), 0.012, M_CHROME)
disc = cyl(pivot + Vector((PADDLE_L - 0.008, 0, 0)), pivot + Vector((PADDLE_L + 0.008, 0, 0)), 0.09, M_PAD, 32)
parent(handle, piv)
parent(disc, piv)
th = pad_h['t']
for t, ang in ((0.0, 0.0), (th - 0.5, 0.0), (th - 0.14, 38.0), (th, 0.0), (th + 0.1, -42.0), (th + 0.6, -42.0), (th + 1.0, 0.0)):
    piv.rotation_euler.y = math.radians(ang)
    piv.keyframe_insert('rotation_euler', index=1, frame=fr(t))
emit_keys(M_PAD, ((th - 1 / FPS, 3.0), (th, 30.0), (th + 0.4, 5.0)))
burst(C_pad + Vector((-R, -0.05, 0)), th, NEON['cyan'], n=10, speed=1.2)

DRUM = MEL[-1]
pad_z = DRUM['z'] - 0.02
pink = character(DRUM['x'] - 0.66, pad_z + 0.07, (0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears', 'pink')

# ---------------------------------------------------------------- the drum and the bells
cyl((DRUM['x'], 0.30, pad_z - 0.10), (DRUM['x'], 0.30, pad_z), 0.24, M_DARK, 48)
ring_m = mat('padring', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=6)
torus((DRUM['x'], 0.30, pad_z), 0.24, 0.014, ring_m)
face_m = mat('padface', (1, 0.5, 0.8), 0.3, emit=(1.0, 0.35, 0.7), emit_s=1.5)
cyl((DRUM['x'], 0.30, pad_z), (DRUM['x'], 0.30, pad_z + 0.004), 0.21, face_m, 48)
emit_keys(ring_m, ((TL - 1 / FPS, 6), (TL, 45), (TL + 1.2, 12)))
emit_keys(face_m, ((TL - 1 / FPS, 1.5), (TL, 25), (TL + 1.2, 4)))
cyl((DRUM['x'], 0.30, pad_z - 0.10), (DRUM['x'], 0.30, pad_z - 1.1), 0.05, M_BRASS)
shock = torus((DRUM['x'], 0.30, pad_z + 0.01), 1.0, 0.01, mat('shock', (1, 1, 1), 0.2, emit=(1, 0.75, 0.9), emit_s=16))
key_vis(shock, TL, TL + 0.5)
for u, s in ((0, 0.24), (0.5, 0.95)):
    shock.scale = (s, s, s)
    shock.keyframe_insert('scale', frame=fr(TL + u))
burst(Vector((DRUM['x'], 0.24, pad_z + 0.02)), TL, NEON['magenta'], n=16, speed=1.6, life=0.5)

BELL_POS = [Vector((0.34, 0.30, pad_z - 0.02)), Vector((0.54, 0.30, pad_z + 0.12)),
            Vector((0.74, 0.30, pad_z + 0.26)), Vector((0.94, 0.30, pad_z + 0.40))]
tag_balls = []
for k, (bp, tg) in enumerate(zip(BELL_POS, TAG)):
    cn = ['cyan', 'violet', 'lime', 'amber'][k]
    hang = empty(bp + Vector((0, 0, 0.16)), f'bellhang{k}')
    bm = mat(f'bell{k}', NEON[cn], 0.15, emit=NEON[cn], emit_s=1.2)
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.06, radius2=0.025, depth=0.09, location=bp + Vector((0, 0, 0.045)))
    bell = add(bpy.context.object, bm)
    bpy.ops.object.shade_smooth()
    rim = torus(bp, 0.06, 0.006, mat(f'bellrim{k}', NEON[cn], 0.2, emit=NEON[cn], emit_s=6))
    rod = cyl(bp + Vector((0, 0, 0.09)), bp + Vector((0, 0, 0.16)), 0.004, M_CHROME, 8)
    cyl(bp + Vector((-0.05, 0.25, 0.16)), bp + Vector((0.05, 0.25, 0.16)), 0.006, M_BRASS, 8)
    cyl(bp + Vector((0, 0.25, 0.16)), bp + Vector((0, 0.56, 0.16)), 0.005, M_CHROME, 8)
    for o in (bell, rim, rod):
        parent(o, hang)
    emit_keys(bm, ((tg['t'] - 1 / FPS, 1.2), (tg['t'], 30), (tg['t'] + 0.5, 6)))
    for u, ang in ((-1 / FPS, 0), (0.08, 16), (0.35, -10), (0.65, 6), (1.0, -3), (1.4, 0)):
        hang.rotation_euler.y = math.radians(ang)
        hang.keyframe_insert('rotation_euler', index=1, frame=fr(tg['t'] + u))
    burst(bp + Vector((0, -0.06, 0)), tg['t'], NEON[cn], n=8, speed=0.9)
    tb = sphere((0, 0, 0), R * 0.6, mat(f'tagball{k}', (1, 0.8, 0.9), 0.1, emit=NEON[cn], emit_s=20))
    tag_balls.append((tb, bp + Vector((0, 0, -0.02 - R * 0.6)), tg['t']))

# ---------------------------------------------------------------- ball keyframes
PATH = [(0.0, BALL0)] + [(h['t'], contact_of(h) if h['kind'] != 'paddle' else C_pad) for h in MEL]


def ball_pos(t):
    if t <= 0.0:
        return BALL0
    for (t0, p0), (t1, p1) in zip(PATH[:-1], PATH[1:]):
        if t <= t1:
            return ballistic(p0, t0, p1, t1, t)
    u = t - TL
    hop_h = max(0.0, 0.14 * math.exp(-u * 2.4) * abs(math.sin(u * 7.5)))
    return PATH[-1][1] + Vector((0, 0, hop_h))


ball_m = mat('ball', (1, 0.2, 0.6), 0.05, emit=(1.0, 0.25, 0.65), emit_s=24, coat=1.0)
ball = sphere((0, 0, 0), R, ball_m, segs=32)
halo_b = sphere((0, 0, 0), R * 1.6, mat('ballhalo', (1, 0.3, 0.7), 0.5, emit=(1.0, 0.3, 0.7), emit_s=1.2, alpha=0.25))
trail = []
for j in range(1, 5):
    tm = mat(f'trail{j}', (1, 0.2, 0.6), 0.3, emit=(1.0, 0.25, 0.65), emit_s=6.0 * (1 - j / 5))
    trail.append((j, sphere((0, 0, 0), R * (1 - j * 0.15), tm, segs=12)))
for f in range(1, N + 1):
    t = (f - 1) / FPS
    p = ball_pos(t)
    ball.location = p
    ball.keyframe_insert('location', frame=f)
    halo_b.location = p
    halo_b.keyframe_insert('location', frame=f)
    for j, o in trail:
        o.location = ball_pos(max(0.0, t - j * 0.016))
        o.keyframe_insert('location', frame=f)
# little tag balls: pop out of the drum and land on the bells
for tb, target, tt in tag_balls:
    start = Vector((DRUM['x'], 0.30, pad_z + 0.03))
    t_s = TL + 0.06
    key_vis(tb, t_s, T_END)
    f = int(fr(t_s))
    while f <= N:
        t = (f - 1) / FPS
        if t <= tt:
            tb.location = ballistic(start, t_s, target, tt, t)
        else:
            u = t - tt
            tb.location = target + Vector((0.25 * u, 0, -0.5 * G * u * u)) if u < 0.6 else target + Vector((0.15, 0, -1.8))
        tb.keyframe_insert('location', frame=f)
        f += 1

# ---------------------------------------------------------------- confetti
t_c = TL + S.CONFETTI_AT
for k in range(70):
    cn = rng.choice(list(NEON))
    o = cube((0, 0, 0), (0.018, 0.004, 0.011), mat(f'conf{k}', NEON[cn], 0.3, emit=NEON[cn], emit_s=rng.uniform(8, 20)))
    key_vis(o, t_c, T_END)
    v = Vector((rng.uniform(-1.4, 1.4), rng.uniform(-0.9, 0.1), rng.uniform(2.6, 4.6)))
    p0 = Vector((DRUM['x'] + rng.uniform(-0.1, 0.1), 0.25, pad_z + 0.05))
    spin = Vector((rng.uniform(-14, 14), rng.uniform(-14, 14), rng.uniform(-14, 14)))
    for u in [i * 0.12 for i in range(int((T_END - t_c) / 0.12) + 2)]:
        drag = 1.0 - math.exp(-u * 1.6)
        o.location = p0 + v * (drag / 1.6) + Vector((0.08 * math.sin(u * 5 + k), 0, -0.9 * u * u * 0.5 - 0.35 * u))
        o.rotation_euler = spin * u
        o.keyframe_insert('location', frame=fr(t_c + u))
        o.keyframe_insert('rotation_euler', frame=fr(t_c + u))

# ---------------------------------------------------------------- character acting
track_eyes(yel, ball_pos)
track_eyes(blue, ball_pos)
track_eyes(pink, ball_pos)
# hook: yellow squashes and pops the ball out of her halo
for t, dz, sq in ((0.0, -0.02, 0.86), (0.08, 0.06, 1.1), (0.25, 0.0, 0.96), (0.4, 0.0, 1.0)):
    yel['root'].location.z = yel['z0'] + dz
    yel['root'].scale = (1 / sq ** 0.5, 1, sq)
    yel['root'].keyframe_insert('location', index=2, frame=fr(t))
    yel['root'].keyframe_insert('scale', frame=fr(t))
mouth_o(yel, 0.05, 0.6, 1.6)
# the save: blue braces, swings, then a proud hop
mouth_o(blue, th - 0.35, th - 0.02, 1.5)
hop(blue, th + 0.25, 0.10)
# finale: everyone reacts to the drum
hop(pink, TL + 0.02, 0.2)
mouth_o(pink, TL, TL + 1.6, 2.0)
hop(pink, TL + 0.7, 0.12)
for ch in (yel, blue):
    hop(ch, TL + 0.05, 0.16)
    hop(ch, TL + 0.6, 0.1)
    mouth_o(ch, TL, TL + 1.8, 1.8)

# ---------------------------------------------------------------- camera
bpy.ops.object.camera_add(location=(0, -4.4, 0))
cam = bpy.context.object
cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 3.2
sc.camera = cam
cam.data.lens = 40


def cam_state(t):
    """(x, y, z, lens, roll_deg) for time t."""
    follow_z = -S.DESCENT * t - 0.15
    # hook: tight on yellow, then pull out as the ball drops
    k0 = smooth(t / 0.9)
    y = -2.3 * (1 - k0) + -4.0 * k0
    z = (0.55 * (1 - k0) + follow_z * k0)
    x = 0.22 * (1 - k0) + 0.04 * math.sin(t * 0.9) * k0
    lens = 50 * (1 - k0) + 40 * k0
    roll = 0.0
    # the save: push in a little toward blue
    ks = smooth((t - (th - 0.8)) / 0.5) * (1 - smooth((t - (th + 0.5)) / 0.6))
    y += 0.9 * ks
    x += -0.35 * ks
    roll += -3.0 * ks
    # phrase B: a slow dutch tilt for energy
    kb = smooth((t - (th + 0.5)) / 1.5) * (1 - smooth((t - (TL - 1.0)) / 1.0))
    roll += 4.0 * kb * math.sin((t - th) * 1.3)
    # finale: ease to hold on the drum, then the big reveal
    kh = smooth((t - (TL - 0.9)) / 1.1)
    z = (1 - kh) * z + kh * (DRUM['z'] + 0.25)
    x = (1 - kh) * x + kh * 0.12
    kr = smooth((t - (TL + S.REVEAL_START)) / S.REVEAL_LEN)
    y = (1 - kr) * y + kr * -8.6
    z = (1 - kr) * z + kr * (DRUM['z'] * 0.5 + 0.35)
    x = (1 - kr) * x
    lens = (1 - kr) * lens + kr * 34
    return x, y, z, lens, roll


f = 1
while f <= N:
    t = (f - 1) / FPS
    x, y, z, lens, roll = cam_state(t)
    cam.location = (x, y, z)
    cam.rotation_euler = (math.radians(90), math.radians(roll), 0)
    cam.data.lens = lens
    cam.data.dof.focus_distance = 0.30 - y
    cam.keyframe_insert('location', frame=f)
    cam.keyframe_insert('rotation_euler', frame=f)
    cam.data.keyframe_insert('lens', frame=f)
    cam.data.dof.keyframe_insert('focus_distance', frame=f)
    f += 2


def area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    lt = bpy.context.object
    lt.data.energy, lt.data.color, lt.data.size = energy, col, size
    lt.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return lt


sc.frame_set(1)
c0 = cam.matrix_world.translation.copy()
for lt in (area(c0 + Vector((-2.6, 3.0, 0.6)), c0 + Vector((0, 4.8, 0)), 230, (0.2, 0.75, 1.0), 2.0),
           area(c0 + Vector((2.6, 3.0, -0.4)), c0 + Vector((0, 4.8, 0)), 260, (1.0, 0.15, 0.6), 2.0),
           area(c0 + Vector((0, 2.2, 2.2)), c0 + Vector((0, 4.8, 0)), 30, (0.8, 0.8, 1.0), 4.0)):
    parent(lt, cam)

# glow
sc.use_nodes = True
nt = sc.node_tree
gl = nt.nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.size = 8
if hasattr(gl, 'threshold'):
    gl.threshold = 0.85
nt.links.new(nt.nodes['Render Layers'].outputs['Image'], gl.inputs['Image'])
nt.links.new(gl.outputs['Image'], nt.nodes['Composite'].inputs['Image'])

sc.render.filepath = str(Path(a.out).resolve())
print('frames total', N, 'seconds', round(T_END, 2))
if a.stills:
    for fs in a.stills.split(','):
        sc.frame_set(int(fs))
        sc.render.filepath = str(Path(a.out).resolve()) + f'{int(fs):04d}.png'
        bpy.ops.render.render(write_still=True)
else:
    if a.frames:
        lo, hi = (int(v) for v in a.frames.split('-'))
        sc.frame_start, sc.frame_end = lo, hi
    bpy.ops.render.render(animation=True)
