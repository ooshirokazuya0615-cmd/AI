"""Neon marble machine plays "Für Elise": vertical Short, one bar per note, camera tracks the ball down.

Timing comes from score.py, so picture and sound share one clock.

    python short.py -- --res 540x960 --samples 12 --fps 30 --out frames/f_####.png [--frames 1-40]
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import DESCENT, hits, total_seconds  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--res', default='540x960')
ap.add_argument('--samples', type=int, default=12)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--out', default='frames/f_####.png')
ap.add_argument('--frames', default='')
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
W, H = (int(v) for v in a.res.split('x'))
FPS = a.fps
G = 9.81
R_BALL = 0.045
BAR_T = 0.045       # bar thickness
BAR_W = 0.13

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.fps = FPS
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.render.use_persistent_data = True
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'

world = bpy.data.worlds.new('w')
sc.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.004, 0.012, 1)

HITS = hits()
T_END = total_seconds()
T_LAST = HITS[-1]['t']
N_FRAMES = int(round(T_END * FPS))
sc.frame_start, sc.frame_end = 1, N_FRAMES


def fr(t):
    return 1 + t * FPS


def mat(name, col, rough=0.4, metal=0.0, emit=None, emit_s=0.0, coat=0.0):
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
    return m


def emit_key(m, t, s):
    sock = m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
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
        md.width, md.segments = bevel, 3
    bpy.ops.object.shade_smooth()
    return add(o, m)


def sphere(loc, r, m, scale=None, segs=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=segs // 2, radius=r, location=loc)
    o = bpy.context.object
    if scale:
        o.scale = scale
    bpy.ops.object.shade_smooth()
    return add(o, m)


def cyl(p0, p1, r, m, verts=24):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    bpy.ops.object.shade_smooth()
    return add(o, m)


def parent(o, p):
    o.parent = p
    o.matrix_parent_inverse = p.matrix_world.inverted()


NEON = {
    'cyan': (0.05, 0.85, 1.0), 'magenta': (1.0, 0.08, 0.55), 'violet': (0.55, 0.2, 1.0),
    'lime': (0.45, 1.0, 0.25), 'amber': (1.0, 0.6, 0.08),
}
from score import PC_COLOUR  # noqa: E402

M_WALL = mat('wall', (0.025, 0.025, 0.035), 0.55)
M_BRASS = mat('brass', (0.85, 0.62, 0.25), 0.22, metal=1.0)
M_CHROME = mat('chrome', (0.9, 0.9, 0.95), 0.08, metal=1.0)
M_DARK = mat('dark', (0.02, 0.02, 0.025), 0.3, coat=0.6)

z_top, z_bot = 3.5, HITS[-1]['z'] - 2.5
# --- wall of vertical slats covering the whole descent -------------------------
for k in range(-12, 13):
    cube((k * 0.16, 0.6, (z_top + z_bot) / 2), (0.14, 0.06, z_top - z_bot), M_WALL, bevel=0.01)

# --- one neon bar per note (the last note is the big drum pad) ------------------
for i, h in enumerate(HITS[:-1]):
    col = NEON[PC_COLOUR[h['midi'] % 12]]
    m = mat(f'bar{i}', col, 0.25, emit=col, emit_s=1.0)
    zc = h['z'] - BAR_T / 2
    bar = cube((h['x'], 0.30, zc), (BAR_W, 0.10, BAR_T), m, bevel=0.01)
    for s in (-1, 1):
        cyl((h['x'] + s * BAR_W * 0.33, 0.56, zc), (h['x'] + s * BAR_W * 0.33, 0.30, zc), 0.006, M_CHROME, 10)
    # light up on the hit, then glow back down
    # unplayed bars glow faintly; played bars stay lit, so the melody leaves a trail of light
    emit_key(m, h['t'] - 1 / FPS, 1.0)
    emit_key(m, h['t'], 30.0)
    emit_key(m, h['t'] + 0.35, 5.5)
    # small dip when struck
    for t, dz in ((h['t'] - 1 / FPS, 0.0), (h['t'] + 0.04, -0.018), (h['t'] + 0.16, 0.004), (h['t'] + 0.3, 0.0)):
        bar.location.z = zc + dz
        bar.keyframe_insert('location', index=2, frame=fr(t))

# --- final drum pad ----------------------------------------------------------------
L = HITS[-1]
pad_z = L['z'] - 0.02
pad = cyl((L['x'], 0.56, pad_z - 0.0), (L['x'], 0.30, pad_z), 0.0, M_DARK)  # placeholder removed below
bpy.data.objects.remove(pad)
# pad lies flat (face up) so the ball lands on it
cyl((L['x'], 0.30, pad_z - 0.10), (L['x'], 0.30, pad_z), 0.24, M_DARK, 64)
bpy.ops.mesh.primitive_torus_add(major_radius=0.24, minor_radius=0.014, location=(L['x'], 0.30, pad_z))
ring_m = mat('padring', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=6)
add(bpy.context.object, ring_m)
face_m = mat('padface', (1, 0.5, 0.8), 0.3, emit=(1.0, 0.35, 0.7), emit_s=1.5)
cyl((L['x'], 0.30, pad_z), (L['x'], 0.30, pad_z + 0.004), 0.21, face_m, 64)
for m, lo, hi in ((ring_m, 6, 40), (face_m, 1.5, 22)):
    emit_key(m, L['t'] - 1 / FPS, lo)
    emit_key(m, L['t'], hi)
    emit_key(m, L['t'] + 1.2, lo * 1.6)
# expanding shock ring
bpy.ops.mesh.primitive_torus_add(major_radius=0.24, minor_radius=0.008, location=(L['x'], 0.30, pad_z + 0.01))
shock = add(bpy.context.object, mat('shock', (1, 1, 1), 0.2, emit=(1.0, 0.75, 0.9), emit_s=16))
for t, s in ((L['t'] - 1 / FPS, 0.001), (L['t'], 1.0), (L['t'] + 0.5, 3.2), (L['t'] + 0.51, 0.001)):
    shock.scale = (s, s, s)
    shock.keyframe_insert('scale', frame=fr(t))
# pedestal column under the pad
cyl((L['x'], 0.30, pad_z - 0.10), (L['x'], 0.30, pad_z - 0.9), 0.05, M_BRASS)


# --- ball path: free fall, then an exact parabola from each hit to the next --------
def contact(h):
    return Vector((h['x'], 0.30, h['z'] + R_BALL))


def ball_pos(t):
    if t <= HITS[0]['t']:
        dt = HITS[0]['t'] - t
        return contact(HITS[0]) + Vector((0, 0, 0.5 * G * dt * dt))
    for h0, h1 in zip(HITS[:-1], HITS[1:]):
        if t <= h1['t']:
            T = h1['t'] - h0['t']
            p0, p1 = contact(h0), contact(h1)
            v = (p1 - p0 - Vector((0, 0, -0.5 * G * T * T))) / T
            u = t - h0['t']
            return p0 + v * u + Vector((0, 0, -0.5 * G * u * u))
    # after the last hit: small bounces on the pad, settling
    u = t - L['t']
    hop = max(0.0, 0.16 * math.exp(-u * 2.2) * abs(math.sin(u * 7.0)))
    return contact(L) + Vector((0, 0, hop))


ball_m = mat('ball', (1, 0.2, 0.6), 0.1, emit=(1.0, 0.25, 0.65), emit_s=22)
ball = sphere((0, 0, 0), R_BALL, ball_m, segs=32)
trail = []
for j in range(1, 5):
    tm = mat(f'trail{j}', (1, 0.2, 0.6), 0.3, emit=(1.0, 0.25, 0.65), emit_s=7.0 * (1 - j / 5))
    trail.append((j, sphere((0, 0, 0), R_BALL * (1 - j * 0.15), tm, segs=16)))
for f in range(1, N_FRAMES + 1):
    t = (f - 1) / FPS
    ball.location = ball_pos(t)
    ball.keyframe_insert('location', frame=f)
    for j, o in trail:
        o.location = ball_pos(max(0.0, t - j * 0.018))
        o.keyframe_insert('location', frame=f)

# --- characters on brass ledges beside the pad ----------------------------------
M_WHITE = mat('eyewhite', (0.95, 0.95, 0.97), 0.25)
M_HI = mat('hilite', (1, 1, 1), 0.2, emit=(1, 1, 1), emit_s=4)


def empty(loc, name):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    sc.collection.objects.link(o)
    return o


def character(x, z, body_col, iris_col, accent, name):
    root = empty((x, 0.15, z), name)
    look = empty((x, 0.0, z + 0.15), name + '_look')
    parent(look, root)
    parts = []
    parts.append(cube((x, 0.15, z - 0.42), (0.34, 0.30, 0.14), M_BRASS, bevel=0.02))
    bm = mat(name + 'body', body_col, 0.35, coat=0.8)
    parts.append(cyl((x, 0.15, z - 0.35), (x, 0.15, z - 0.12), 0.12, bm))
    parts.append(sphere((x, 0.15, z + 0.12), 0.23, bm))
    if accent == 'antenna':
        parts.append(cyl((x, 0.15, z + 0.33), (x + 0.03, 0.15, z + 0.48), 0.008, M_CHROME))
        parts.append(sphere((x + 0.03, 0.15, z + 0.49), 0.03, mat('ant', NEON['cyan'], 0.2, emit=NEON['cyan'], emit_s=15)))
    else:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.11, minor_radius=0.013, location=(x, 0.15, z + 0.41))
        parts.append(add(bpy.context.object, mat('halo', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=12)))
    irises = []
    for s in (-1, 1):
        c = Vector((x + s * 0.09, -0.03, z + 0.15))
        parts.append(sphere(c, 0.085, M_WHITE, scale=(1.0, 0.45, 1.15)))
        ic = c + Vector((0, -0.036, 0))
        im = mat(name + 'iris', iris_col, 0.2, emit=iris_col, emit_s=1.2)
        irises.append(sphere(ic, 0.053, im, scale=(1.0, 0.35, 1.1)))
        irises.append(sphere(ic + Vector((0, -0.016, 0)), 0.026, mat('pupil', (0.01, 0.01, 0.02), 0.2), scale=(1, 0.35, 1.1)))
        irises.append(sphere(ic + Vector((0.019, -0.026, 0.024)), 0.011, M_HI))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.035, minor_radius=0.007, location=(x, -0.07, z + 0.0),
                                     rotation=(math.radians(90), 0, 0))
    mouth = add(bpy.context.object, mat(name + 'mouth', (0.15, 0.02, 0.05), 0.4))
    parts.append(mouth)
    for o in parts:
        parent(o, root)
    for o in irises:
        parent(o, look)
    return root, look, mouth


cz = pad_z + 0.05
blue, blue_look, blue_mouth = character(L['x'] - 0.72, cz, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'blue')
yel, yel_look, yel_mouth = character(L['x'] + 0.72, cz - 0.08, (0.95, 0.85, 0.25), (1.0, 0.3, 0.7), 'halo', 'yel')

# eyes follow the ball (pupils shift a little toward it)
for f in range(1, N_FRAMES + 1, 2):
    t = (f - 1) / FPS
    b = ball_pos(t)
    for root, look in ((blue, blue_look), (yel, yel_look)):
        d = b - (root.location + Vector((0, 0, 0.15)))
        dx = max(-1, min(1, d.x / 0.6)) * 0.022
        dz = max(-1, min(1, d.z / 0.8)) * 0.026
        look.location = (root.location.x + dx, -0.15 + 0.0, root.location.z + 0.15 + dz) if False else look.location
        look.delta_location = (dx, 0, dz)
        look.keyframe_insert('delta_location', frame=f)

# reactions on the final hit: blue jumps with a wide "O" mouth, yellow bounces twice
tl = L['t']
for t, dz, sq in ((tl - 0.05, 0, 1.0), (tl + 0.05, -0.03, 0.9), (tl + 0.25, 0.22, 1.08), (tl + 0.45, 0.0, 0.92),
                  (tl + 0.55, 0.0, 1.0)):
    blue.location.z = cz + dz
    blue.scale = (1 / sq ** 0.5, 1, sq)
    blue.keyframe_insert('location', index=2, frame=fr(t))
    blue.keyframe_insert('scale', frame=fr(t))
for t, s in ((tl - 0.05, 1.0), (tl + 0.1, 1.9), (tl + 1.4, 1.9), (tl + 1.6, 1.0)):
    blue_mouth.scale = (s, s * 1.3 if s > 1 else 1, s)
    blue_mouth.keyframe_insert('scale', frame=fr(t))
for t, dz in ((tl + 0.1, 0), (tl + 0.3, 0.12), (tl + 0.5, 0), (tl + 0.7, 0.08), (tl + 0.9, 0)):
    yel.location.z = cz - 0.08 + dz
    yel.keyframe_insert('location', index=2, frame=fr(t))

# --- camera: glides down with the music, eases to a stop on the finale -------------
bpy.ops.object.camera_add(location=(0, -4.4, 0))
cam = bpy.context.object
cam.data.lens = 40
cam.rotation_euler = (math.radians(90), 0, 0)
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 4.7
cam.data.dof.aperture_fstop = 6.3
sc.camera = cam
z_hold = L['z'] + 0.25
for f in range(1, N_FRAMES + 1, 3):
    t = (f - 1) / FPS
    z_follow = -DESCENT * t - 0.15
    k = min(1.0, max(0.0, (t - (tl - 0.9)) / 1.2))
    k = k * k * (3 - 2 * k)
    cam.location.z = (1 - k) * z_follow + k * max(z_hold, z_follow)
    cam.location.x = 0.06 * math.sin(t * 0.9)
    cam.keyframe_insert('location', frame=f)


# lights ride with the camera: cyan from the left, magenta from the right
def area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.data.energy, l.data.color, l.data.size = energy, col, size
    l.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return l


for l in (area((-2.6, -1.4, 0.6), (0, 0.4, 0), 230, (0.2, 0.75, 1.0), 2.0),
          area((2.6, -1.4, -0.4), (0, 0.4, 0), 260, (1.0, 0.15, 0.6), 2.0),
          area((0, -2.2, 2.2), (0, 0.4, 0), 30, (0.8, 0.8, 1.0), 4.0)):
    l.location.z += cam.location.z
    parent(l, cam)

# glow
sc.use_nodes = True
nt = sc.node_tree
gl = nt.nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'MEDIUM'
gl.size = 8
if hasattr(gl, 'threshold'):
    gl.threshold = 0.9
nt.links.new(nt.nodes['Render Layers'].outputs['Image'], gl.inputs['Image'])
nt.links.new(gl.outputs['Image'], nt.nodes['Composite'].inputs['Image'])

sc.render.filepath = str(Path(a.out).resolve())
if a.frames:
    lo, hi = (int(v) for v in a.frames.split('-'))
    sc.frame_start, sc.frame_end = lo, hi
print('frames', sc.frame_start, sc.frame_end, 'of', N_FRAMES)
bpy.ops.render.render(animation=True)
