"""v4: medley with silent gaps, House of Marble style (light studio wall, dark fixtures, neon light), original assets.

  Für Elise   LED tile shelves, round pads and synth blocks; every pad is tilted so the bounce is a true mirror bounce
  gap 1       silence: the ball glides along a coaster rail and flips a light switch; the next section powers on
  Ode to Joy  repeated notes are double bounces on the same pad; the last pad is a spring
  gap 2       the spring launches the ball high (a held breath), and it lands on the big drum
  reveal      the camera pulls back over the whole machine

    python short4.py -- --res 720x1280 --samples 14 --out frames/f_#### [--frames 1-40] [--stills 5,120]
"""
import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score4 as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--res', default='720x1280')
ap.add_argument('--samples', type=int, default=16)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--out', default='frames/f_####')
ap.add_argument('--frames', default='')
ap.add_argument('--stills', default='')
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
W, H = (int(v) for v in a.res.split('x'))
FPS = a.fps
G = 9.81
R = 0.05           # main marble
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


# ================================================================ v4 look: light studio wall, dark fixtures, neon light
M_WALL = mat('wall4', (0.78, 0.79, 0.80), 0.8)
M_FIX = mat('fixture', (0.035, 0.035, 0.04), 0.35, metal=0.3, coat=0.5)
M_FIX2 = mat('fixture2', (0.08, 0.08, 0.09), 0.3, metal=0.7)
M_RAIL = mat('rail', (0.05, 0.05, 0.055), 0.25, metal=0.9)
NOTES = S.notes()
GAP = S.gap1()
TF = S.t_final()
DESC = 0.42
DRIFT = 0.07


def ballistic(p0, t0, p1, t1, t):
    T = t1 - t0
    v = (p1 - p0 + Vector((0, 0, 0.5 * G * T * T))) / T
    u = t - t0
    return p0 + v * u + Vector((0, 0, -0.5 * G * u * u))


def bvel(p0, t0, p1, t1, t):
    T = t1 - t0
    v = (p1 - p0 + Vector((0, 0, 0.5 * G * T * T))) / T
    return v + Vector((0, 0, -G * (t - t0)))


# ---------------------------------------------------------------- 1. contact positions
CON = {}
MODE = {}      # i -> how the ball travels from contact i to i+1: 'fly' | 'roll'
A = [h for h in NOTES if h['song'] == 'A']
B = [h for h in NOTES if h['song'] == 'B']


def base_a(t):
    return Vector((-0.30 + DRIFT * t, YB, 0.40 - DESC * t))


def place_song(hs, base, center, xs, speed, slope):
    th = math.radians(slope)
    dirv = Vector((math.cos(th), 0, -math.sin(th)))
    k = 0
    while k < len(hs):
        h = hs[k]
        if h['mech'] == 'tile':
            run = [h]
            while k + len(run) < len(hs) and hs[k + len(run)]['mech'] == 'tile':
                run.append(hs[k + len(run)])
            p0 = base(h['t']) + Vector(((h['midi'] - center) * xs, 0, 0))
            for j, r in enumerate(run):
                CON[r['i']] = p0 + dirv * (speed * (r['t'] - h['t']))
                MODE[r['i']] = 'roll' if j < len(run) - 1 else 'fly'
            k += len(run)
            continue
        if h['mech'] == 'pad2':
            CON[h['i']] = CON[h['i'] - 1].copy()
        else:
            CON[h['i']] = base(h['t']) + Vector(((h['midi'] - center) * xs, 0, 0))
        MODE[h['i']] = 'fly'
        k += 1


place_song(A, base_a, 70, 0.045, 0.5, 8.0)

# gap 1: launch pad -> coaster rail -> switch -> drop into section B
LP = CON[A[-1]['i']]
RAIL_PTS = [LP + Vector(d) for d in ((0.30, 0, -0.16), (0.55, 0, -0.34), (0.85, 0, -0.44), (1.15, 0, -0.40),
                                     (1.38, 0, -0.30), (1.55, 0, -0.27))]
T_RAIL0 = A[-1]['t'] + 0.38
SW = RAIL_PTS[-1] + Vector((0.10, 0, 0.0))        # the switch toggle the ball knocks
T_SW = GAP['switch']


def catmull(pts, n=120):
    P = [pts[0] + (pts[0] - pts[1])] + pts + [pts[-1] + (pts[-1] - pts[-2])]
    out = []
    for s in range(len(P) - 3):
        p0, p1, p2, p3 = P[s:s + 4]
        for j in range(n // (len(P) - 3)):
            u = j / (n // (len(P) - 3))
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    out.append(pts[-1])
    return out


RAIL = catmull(RAIL_PTS)
# time along the rail from energy (faster when lower), scaled to arrive at the switch on time
v0 = 1.1
times = [0.0]
for p, q in zip(RAIL[:-1], RAIL[1:]):
    v = math.sqrt(max(0.2, v0 * v0 + 2 * G * (RAIL[0].z - (p.z + q.z) / 2) * 0.35))
    times.append(times[-1] + (q - p).length / v)
scale = (T_SW - 0.05 - T_RAIL0) / times[-1]
RAIL_T = [T_RAIL0 + x * scale for x in times]
RAIL_C = [p + Vector((0, 0, R + 0.008)) for p in RAIL]   # ball centre rides above the rail


def base_b(t):
    return Vector((SW.x + 0.22 + DRIFT * (t - GAP['t1']), YB, SW.z - 0.42 - DESC * (t - GAP['t1'])))


place_song(B[:-2], base_b, 64, 0.06, 0.5, 6.0)
SPRING = B[-2]
CON[SPRING['i']] = base_b(SPRING['t']) + Vector(((SPRING['midi'] - 64) * 0.06, 0, 0))
MODE[SPRING['i']] = 'fly'
FIN = B[-1]
CON[FIN['i']] = CON[SPRING['i']] + Vector((0.95, 0, -0.32))
DRUM_C = CON[FIN['i']]


# ---------------------------------------------------------------- 2. the ball path
def ball_pos(t):
    if t <= NOTES[0]['t']:
        # rolling in from the left on the first shelf
        return CON[0] + Vector((-(NOTES[0]['t'] - t) * 0.5, 0, 0.0))
    for h0, h1 in zip(NOTES[:-1], NOTES[1:]):
        if h0['t'] <= t <= h1['t']:
            p0, p1 = CON[h0['i']], CON[h1['i']]
            if h0['song'] == 'A' and h1['song'] == 'B':
                return gap_pos(t)
            if MODE[h0['i']] == 'roll':
                return p0.lerp(p1, (t - h0['t']) / (h1['t'] - h0['t']))
            return ballistic(p0, h0['t'], p1, h1['t'], t)
    u = t - TF
    return DRUM_C + Vector((0, 0, max(0.0, 0.12 * math.exp(-u * 2.4) * abs(math.sin(u * 7.5)))))


def gap_pos(t):
    if t <= T_RAIL0:
        return ballistic(LP, A[-1]['t'], RAIL_C[0], T_RAIL0, t)
    if t <= RAIL_T[-1]:
        for j in range(len(RAIL_T) - 1):
            if t <= RAIL_T[j + 1]:
                k = (t - RAIL_T[j]) / (RAIL_T[j + 1] - RAIL_T[j])
                return RAIL_C[j].lerp(RAIL_C[j + 1], k)
    if t <= T_SW:
        return RAIL_C[-1].lerp(SW + Vector((-R - 0.012, 0, 0.02)), (t - RAIL_T[-1]) / max(1e-3, T_SW - RAIL_T[-1]))
    return ballistic(SW + Vector((-R - 0.012, 0, 0.02)), T_SW, CON[B[0]['i']], B[0]['t'], t)


def vel(t, dt=1 / 240):
    return (ball_pos(t + dt) - ball_pos(t - dt)) / (2 * dt)


def normal_at(h):
    """Surface normal that turns the incoming velocity into the outgoing one (mirror bounce)."""
    vi = vel(h['t'] - 0.004).normalized()
    vo = vel(h['t'] + 0.004).normalized()
    n = vo - vi
    if n.length < 1e-3:
        n = Vector((0, 0, 1))
    n.normalize()
    if n.z < 0.35:                      # keep pads facing mostly up so they read as pads
        n.z = 0.35
        n.normalize()
    n.y = 0.0
    return n.normalized()


def orient(o, n):
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = n.to_track_quat('Z', 'Y')


# ---------------------------------------------------------------- 3. wall
z_hi = max(p.z for p in CON.values()) + 2.5
z_lo = min(p.z for p in CON.values()) - 3.5
x_lo = min(p.x for p in CON.values()) - 3.5
x_hi = max(p.x for p in CON.values()) + 3.5
bpy.ops.mesh.primitive_plane_add(size=1, location=((x_lo + x_hi) / 2, 0.62, (z_hi + z_lo) / 2), rotation=(math.radians(90), 0, 0))
w = add(bpy.context.object, M_WALL)
w.scale = (x_hi - x_lo, z_hi - z_lo, 1)
# a floor far below, so the reveal has a ground line
bpy.ops.mesh.primitive_plane_add(size=1, location=((x_lo + x_hi) / 2, -2.0, z_lo + 0.4))
fl = add(bpy.context.object, mat('floor4', (0.70, 0.71, 0.72), 0.6))
fl.scale = (x_hi - x_lo, 6.0, 1)

ALL_LIGHTS = []   # (material, t_power_on, base) for section B power-on


def lit(m, h, base, peak, after, powered=True):
    if powered:
        flash(m, h['t'], base, peak, after)
    else:
        ALL_LIGHTS.append((m, h, base, peak, after))


# ---------------------------------------------------------------- 4. instruments
def wall_pin(p, n=None):
    cyl((p.x, 0.62, p.z), (p.x, p.y + 0.015, p.z), 0.007, M_RAIL, 10)


def tile_shelf(run, powered):
    p0, p1 = CON[run[0]['i']], CON[run[-1]['i']]
    d = (p1 - p0).normalized() if (p1 - p0).length > 1e-4 else Vector((1, 0, 0))
    th = math.atan2(-d.z, d.x)
    nrm = Vector((math.sin(th), 0, math.cos(th)))
    a0 = p0 - d * 0.12 - nrm * R
    a1 = p1 + d * 0.10 - nrm * R
    mid = (a0 + a1) / 2
    cube(mid - nrm * 0.014, ((a1 - a0).length, 0.10, 0.028), M_FIX, bevel=0.005, rot=(0, th, 0))
    for s in (-1, 1):
        cyl(a0 + Vector((0, s * 0.042, 0.006)), a1 + Vector((0, s * 0.042, 0.006)), 0.005, M_RAIL, 8)
    seg = (a1 - a0).length / max(1, len(run))
    for j, h in enumerate(run):
        col = ncol(h['midi'])
        tm = mat(f'tile{h["i"]}', col, 0.3, emit=col, emit_s=0.0)
        cube(CON[h['i']] - nrm * (R - 0.001), (min(0.1, seg * 0.86), 0.078, 0.007), tm, bevel=0.002, rot=(0, th, 0))
        lit(tm, h, 1.5, 60.0, 9.0, powered)
        burst(CON[h['i']] + Vector((0, -0.05, -R + 0.01)), h['t'], col, n=4, speed=0.5, life=0.22, size=0.006)
    # diagonal brackets to the wall
    for p in (a0 + d * 0.06, a1 - d * 0.06):
        cyl((p.x, 0.62, p.z - 0.12), (p.x, YB + 0.02, p.z - 0.02), 0.008, M_RAIL, 8)


def pad(h, powered, r=0.065, spring=False):
    n = normal_at(h)
    c = CON[h['i']] - n * (R + 0.008)
    root = empty(c, f'pad{h["i"]}')
    disc = cyl(c - n * 0.008, c + n * 0.008, r, M_FIX, 40)
    col = ncol(h['midi'])
    rm = mat(f'padring{h["i"]}', col, 0.2, emit=col, emit_s=0.0)
    ring = torus(c + n * 0.007, r - 0.008, 0.009, rm)
    orient(ring, n)
    face = cyl(c + n * 0.006, c + n * 0.009, r * 0.55, mat(f'padface{h["i"]}', (0.12, 0.12, 0.14), 0.4, metal=0.5), 32)
    for o in (disc, ring, face):
        parent(o, root)
    # stem to the wall
    cyl((c.x, 0.62, c.z - 0.02), (c.x, c.y + 0.02, c.z - 0.02), 0.009, M_RAIL, 10)
    lit(rm, h, 3.0, 80.0, 9.0, powered)
    if not powered:
        pass
    base = root.location.copy()
    dz = 0.025 if spring else 0.012
    for u, k in ((-0.12 if spring else -1 / FPS, 0), (0.0, 1), (0.05, -0.4), (0.16, 0)):
        root.location = base - n * dz * k
        root.keyframe_insert('location', frame=fr(h['t'] + u))
    burst(CON[h['i']] - n * R + Vector((0, -0.04, 0)), h['t'], col, n=7)
    pulse_ring(c + n * 0.01, h['t'], col, r0=r, r1=r * 2.0, rot=(0, 0, 0))
    return root


def block(h, powered):
    n = normal_at(h)
    c = CON[h['i']] - n * (R + 0.022)
    o = cube(c, (0.15, 0.075, 0.044), M_FIX2, bevel=0.006)
    orient(o, n)
    col = ncol(h['midi'])
    lm = mat(f'blockled{h["i"]}', col, 0.2, emit=col, emit_s=0.0)
    strip = cube(c + n * 0.023 + Vector((0, -0.038, 0)), (0.13, 0.008, 0.012), lm)
    orient(strip, n)
    for j in (-1, 0, 1):
        hole = cyl(c + Vector((j * 0.04, -0.039, 0)), c + Vector((j * 0.04, -0.034, 0)), 0.008, M_FIX, 12)
    cyl((c.x, 0.62, c.z), (c.x, c.y + 0.03, c.z), 0.009, M_RAIL, 10)
    lit(lm, h, 2.0, 70.0, 8.0, powered)
    base = o.location.copy()
    for u, k in ((-1 / FPS, 0), (0.04, 1), (0.14, -0.3), (0.26, 0)):
        o.location = base - n * 0.012 * k
        o.keyframe_insert('location', frame=fr(h['t'] + u))
    burst(CON[h['i']] - n * R + Vector((0, -0.04, 0)), h['t'], col, n=6)


def build_song(hs, powered):
    k = 0
    while k < len(hs):
        h = hs[k]
        m = h['mech']
        if m == 'tile':
            run = [h]
            while k + len(run) < len(hs) and hs[k + len(run)]['mech'] == 'tile':
                run.append(hs[k + len(run)])
            tile_shelf(run, powered)
            k += len(run)
            continue
        if m == 'pad':
            # a pad that will be hit twice (pad2 follows) is built once
            pad(h, powered)
        elif m == 'pad2':
            col = ncol(h['midi'])
            ring_m = bpy.data.materials.get(f'padring{h["i"] - 1}')
            if ring_m:
                lit(ring_m, h, 9.0, 80.0, 9.0, powered)
            burst(CON[h['i']] + Vector((0, -0.04, -R)), h['t'], col, n=6)
        elif m == 'block':
            block(h, powered)
        elif m in ('launchpad', 'spring'):
            pad(h, powered, r=0.075, spring=True)
        k += 1


build_song(A, True)
build_song(B[:-1], False)

# gap rail (black double rail on ribs) and the light switch
for s in (-1, 1):
    pts = [p + Vector((0, s * 0.03, 0)) for p in RAIL]
    for p, q in zip(pts[:-1:3], pts[3::3]):
        cyl(p, q, 0.005, M_RAIL, 8)
for p in RAIL[::12]:
    cyl(p + Vector((0, -0.035, -0.006)), p + Vector((0, 0.035, -0.006)), 0.004, M_RAIL, 6)
    cyl((p.x, 0.62, p.z - 0.05), (p.x, YB + 0.03, p.z - 0.006), 0.006, M_RAIL, 8)
plate = cube(SW + Vector((0.035, 0.24, 0.0)), (0.07, 0.02, 0.12), mat('switchplate', (0.85, 0.86, 0.88), 0.3, metal=0.9), bevel=0.006)
tog = empty(SW + Vector((0.035, 0.22, 0.0)), 'toggle')
lever = cube(SW + Vector((0.035, 0.13, 0.02)), (0.018, 0.17, 0.018), M_FIX, bevel=0.004)
parent(lever, tog)
for t, ang in ((T_SW - 1 / FPS, 0.0), (T_SW + 0.05, -35.0)):
    tog.rotation_euler.x = math.radians(ang)
    tog.keyframe_insert('rotation_euler', index=0, frame=fr(t))
sw_led = mat('switchled', NEON['lime'], 0.2, emit=NEON['lime'], emit_s=0.0)
sphere(SW + Vector((0.035, 0.225, 0.045)), 0.008, sw_led, segs=10)
emit_keys(sw_led, ((T_SW - 1 / FPS, 0.0), (T_SW, 25.0)))

# section B powers on in a wave from the switch, then plays as normal
for m, h, base_s, peak, after in ALL_LIGHTS:
    d = (CON[h['i']] - SW).length
    t_on = T_SW + 0.08 + d * 0.22
    sock = m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    for t, s in ((0.0, 0.0), (T_SW, 0.0), (t_on, 12.0), (t_on + 0.12, base_s if base_s else 1.0), (h['t'] - 1 / FPS, base_s if base_s else 1.0),
                 (h['t'], peak), (h['t'] + 0.35, after)):
        if t <= h['t'] + 0.35:
            sock.default_value = s
            sock.keyframe_insert('default_value', frame=fr(t))

# ---------------------------------------------------------------- 5. big drum, bells, characters
DX, DZ = DRUM_C.x, DRUM_C.z - R - 0.004
cyl((DX, YB, DZ - 0.12), (DX, YB, DZ), 0.2, mat('bigshell', (0.05, 0.05, 0.06), 0.25, coat=1.0), 48)
big_rim = mat('bigrim', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=0.0)
torus((DX, YB, DZ), 0.2, 0.012, big_rim)
big_head = mat('bighead', (0.95, 0.95, 0.97), 0.35, emit=(1.0, 0.35, 0.7), emit_s=0.0)
cyl((DX, YB, DZ), (DX, YB, DZ + 0.004), 0.186, big_head, 48)
emit_keys(big_rim, ((T_SW, 0), (T_SW + 1.0, 4.0), (TF - 1 / FPS, 4.0), (TF, 60), (TF + 1.2, 10)))
emit_keys(big_head, ((TF - 1 / FPS, 0.0), (TF, 22), (TF + 1.2, 2)))
cyl((DX, YB, DZ - 0.12), (DX, YB, DZ - 1.0), 0.04, M_RAIL)
pulse_ring(Vector((DX, YB, DZ + 0.01)), TF, NEON['magenta'], r0=0.2, r1=0.85, life=0.5, rot=(0, 0, 0))
burst(Vector((DX, YB - 0.04, DZ + 0.02)), TF, NEON['magenta'], n=18, speed=1.7, life=0.5)
yel = character(DX + 0.55, DZ + 0.02, (0.95, 0.82, 0.2), (1.0, 0.3, 0.7), 'halo', 'yel')
pink = character(DX - 0.55, DZ + 0.02, (0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears', 'pink')
blue = character(SW.x + 0.42, SW.z + 0.04, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'blue')

for ch in (yel, pink, blue):
    r0 = ch['root']
    holder = empty((r0.location.x, r0.location.y, r0.location.z - 0.49), r0.name + '_holder')
    bpy.context.view_layer.update()    # the new empty's world matrix must be current before parenting
    parent(r0, holder)
    holder.scale = (0.68, 0.68, 0.68)

# confetti
t_c = TF + 0.9
for k in range(80):
    cn = rng.choice(list(NEON))
    o = cube((0, 0, 0), (0.018, 0.004, 0.011), mat(f'conf{k}', NEON[cn], 0.3, emit=NEON[cn], emit_s=rng.uniform(6, 14)))
    key_vis(o, t_c)
    v = Vector((rng.uniform(-1.4, 1.4), rng.uniform(-0.9, 0.1), rng.uniform(2.6, 4.6)))
    p0 = Vector((DX + rng.uniform(-0.1, 0.1), YB - 0.05, DZ + 0.05))
    sp = Vector((rng.uniform(-14, 14), rng.uniform(-14, 14), rng.uniform(-14, 14)))
    u = 0.0
    while t_c + u <= T_END + 0.2:
        drag = 1.0 - math.exp(-u * 1.6)
        o.location = p0 + v * (drag / 1.6) + Vector((0.08 * math.sin(u * 5 + k), 0, -0.45 * u * u - 0.35 * u))
        o.rotation_euler = sp * u
        o.keyframe_insert('location', frame=fr(t_c + u))
        o.keyframe_insert('rotation_euler', frame=fr(t_c + u))
        u += 0.12

# ---------------------------------------------------------------- 6. the marble (galaxy swirl, glossy)
mg = mat('marbleglass', (0.95, 0.95, 1.0), 0.02, trans=1.0, coat=1.0)
core_m = bpy.data.materials.new('marblecore')
core_m.use_nodes = True
nt_ = core_m.node_tree
bsdf = nt_.nodes['Principled BSDF']
wave = nt_.nodes.new('ShaderNodeTexWave')
wave.wave_type = 'RINGS'
wave.inputs['Scale'].default_value = 2.6
wave.inputs['Distortion'].default_value = 11.0
ramp = nt_.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.12, 0.0, 0.45, 1)
ramp.color_ramp.elements[1].color = (0.0, 0.45, 0.4, 1)
e = ramp.color_ramp.elements.new(0.5)
e.color = (1.0, 0.35, 0.02, 1)
nt_.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.08
bsdf.inputs['Coat Weight'].default_value = 1.0
ball = sphere((0, 0, 0), R * 0.2, mg, segs=8)
ball.hide_render = True
core = sphere((0, 0, 0), R, core_m, segs=40)
spin, prev = 0.0, ball_pos(0.0)
for f in range(1, N + 1):
    t = (f - 1) / FPS
    p = ball_pos(t)
    spin += (p - prev).length / R
    prev = p
    for o in (ball, core):
        o.location = p
        o.keyframe_insert('location', frame=f)
    core.rotation_euler = (0, spin, spin * 0.3)
    core.keyframe_insert('rotation_euler', frame=f)

# ---------------------------------------------------------------- 7. acting
for ch in (yel, pink, blue):
    track_eyes(ch, ball_pos)
mouth_o(blue, T_SW - 0.1, T_SW + 0.9, 1.7)
hop(blue, T_SW + 0.15, 0.14)
hop(blue, T_SW + 0.6, 0.08)
for ch in (yel, pink):
    mouth_o(ch, SPRING['t'] + 0.2, SPRING['t'] + 0.9, 1.5)    # watching the high launch
    hop(ch, TF + 0.02, 0.2)
    hop(ch, TF + 0.65, 0.12)
    mouth_o(ch, TF, TF + 1.8, 2.0)
hop(blue, TF + 0.1, 0.12)

# ---------------------------------------------------------------- 8. camera
bpy.ops.object.camera_add(location=(0, -4, 0))
cam = bpy.context.object
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 4.0
sc.camera = cam
OFF = Vector((0.62, -2.85, 0.46))


def target(t):
    acc, wsum = Vector((0, 0, 0)), 0.0
    for j in range(9):
        tt = max(0.0, t - j * 0.06)
        wgt = 1.0 / (1 + j)
        acc += ball_pos(tt) * wgt
        wsum += wgt
    p = acc / wsum
    p.y = YB
    return p + Vector((0.05, 0, -0.08))


mids = [p for p in CON.values()]
FULL = Vector(((min(p.x for p in mids) + max(p.x for p in mids)) / 2, YB, (min(p.z for p in mids) + max(p.z for p in mids)) / 2))
span = max(max(p.z for p in mids) - min(p.z for p in mids), 1.6 * (max(p.x for p in mids) - min(p.x for p in mids)))


def cam_at(t):
    tg = target(t)
    off = OFF.copy()
    lens = 55.0
    # the high launch before the last note: pull back a little to keep the arc in frame
    kl = smooth((t - (SPRING['t'] - 0.1)) / 0.5) * (1 - smooth((t - (TF + 0.2)) / 0.8))
    off = off * (1 + 0.45 * kl)
    tg = tg.lerp((CON[SPRING['i']] + DRUM_C) / 2 + Vector((0, 0, 0.35)), 0.6 * kl)
    kh = smooth((t - (TF - 0.2)) / 0.8)
    tg = tg.lerp(DRUM_C + Vector((0, 0, 0.05)), kh * (1 - kl))
    kr = smooth((t - (TF + S.REVEAL_START)) / S.REVEAL_LEN)
    tg = tg.lerp(FULL, kr)
    off = off.lerp(Vector((1.4, -span * 1.55, 0.9)), kr)
    lens = lens * (1 - kr) + 40 * kr
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

# soft studio light: a big key from top-left (soft wall shadows) and a gentle fill; travels with the camera
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.56, 0.58, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.4


def area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    lt = bpy.context.object
    lt.data.energy, lt.data.color, lt.data.size = energy, col, size
    lt.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return lt


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

print('frames total', N, 'seconds', round(T_END, 2))
if a.stills:
    for fs in a.stills.split(','):
        sc.frame_set(int(fs))
        sc.render.filepath = str(Path(a.out).resolve()) + f'{int(fs):04d}.png'
        bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = str(Path(a.out).resolve())
    # resumable: skip frames that already exist (a restart only loses the frame in progress)
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    if a.frames:
        lo, hi = (int(v) for v in a.frames.split('-'))
        sc.frame_start, sc.frame_end = lo, hi
    bpy.ops.render.render(animation=True)
