"""v3: a rich marble-music machine (the look of Marble Music Stories / Vimelo3D / Marble Blend), original assets.

Every phrase of "Für Elise" gets its own instrument family, so the picture keeps changing:
  E-D#-E-D#-E  glowing tile rail (the ball rolls, each tile is a note)   | phrase B: ping-pong between pinball bumpers
  B-D-C        tube pegs sticking out of the wall
  long A / C   drum disc; a small clone marble pops out and plays the bass on hex speakers
  long B       brass cymbal; the clone plays the bass on brass horn bells
  C-E-A        xylophone bars on coloured base plates
  E-G#-B       ruby glass flasks
  E (pickup)   the blue character's paddle
  final A      the big drum, four bells, confetti, then the camera pulls back over the whole machine

Camera: three-quarter view from above-right, so every object casts a shadow on the wall.

    python short3.py -- --res 720x1280 --samples 16 --out frames/f_#### [--frames 1-40] [--stills 5,120]
"""
import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score2 as S  # noqa: E402

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
R = 0.045          # main marble
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

MEL = S.melody()
BASS = S.bass()
TAG = S.tag()
TL = S.t_last()
T_END = S.total_seconds()
N = int(round(T_END * FPS))
sc.frame_start, sc.frame_end = 1, N
U = S.UNIT


def fr(t):
    return 1 + t * FPS


def smooth(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


def zt(t):
    return -S.DESCENT * t


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
NOTE_COL = {0: 'amber', 2: 'lime', 3: 'violet', 4: 'cyan', 8: 'violet', 9: 'magenta', 11: 'lime'}


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


# ================================================================ wall
Z_TOP, Z_BOT = 3.5, MEL[-1]['z'] - 3.2
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.62, (Z_TOP + Z_BOT) / 2), rotation=(math.radians(90), 0, 0))
wall = add(bpy.context.object, M_WALL)
wall.scale = (9.0, Z_TOP - Z_BOT, 1)
# thin neon seams in the wall, for depth and colour
for x, cn in ((-1.45, 'cyan'), (-0.95, 'violet'), (1.05, 'magenta'), (1.6, 'cyan')):
    cyl((x, 0.61, Z_TOP), (x, 0.61, Z_BOT), 0.005, mat('seam' + cn, NEON[cn], 0.3, emit=NEON[cn], emit_s=1.4), 8)
for z in [Z_TOP - 1.5 - 1.9 * k for k in range(6)]:
    cyl((-3.5, 0.61, z), (3.5, 0.61, z), 0.003, mat('hseam', NEON['violet'], 0.3, emit=NEON['violet'], emit_s=0.5), 6)
# floating motes in front (bokeh)
for k in range(40):
    c = NEON[rng.choice(['cyan', 'magenta', 'violet', 'amber'])]
    sphere((rng.uniform(-1.0, 2.6), rng.uniform(-2.8, -1.4), rng.uniform(Z_BOT, 1.6)), rng.uniform(0.006, 0.013),
           mat(f'mote{k}', c, 0.5, emit=c, emit_s=rng.uniform(3, 8)), segs=8)

# ================================================================ layout: one contact per note
CON = {}         # melody index -> ball centre at the hit
ROLL = {}        # melody index -> True when the ball arrives rolling along a rail (no bounce)


def tile_rail(idxs, x0, slope_deg=11.0, d=0.118, colour_by_note=True, extra_after=0.05):
    th = math.radians(slope_deg)
    dirv = Vector((math.cos(th), 0, -math.sin(th)))
    nrm = Vector((math.sin(th), 0, math.cos(th)))
    t0 = MEL[idxs[0]]['t']
    p0 = Vector((x0, YB, zt(t0) - 0.02))
    tops = [p0 + dirv * (d * k) for k in range(len(idxs))]
    start, end = tops[0] - dirv * 0.09, tops[-1] + dirv * extra_after
    for s in (-1, 1):
        cyl(start + Vector((0, s * 0.036, 0.004)), end + Vector((0, s * 0.036, 0.004)), 0.006, M_CHROME, 10)
    # rail housing under the tiles
    mid = (start + end) / 2
    hous = cube(mid - nrm * 0.016, ((end - start).length, 0.085, 0.022), M_DARKM, bevel=0.004, rot=(0, th, 0))
    for k, (i, p) in enumerate(zip(idxs, tops)):
        col = ncol(MEL[i]['midi'])
        tm = mat(f'tile{i}', col, 0.25, emit=col, emit_s=0.4)
        cube(p - nrm * 0.004, (d * 0.86, 0.062, 0.01), tm, bevel=0.002, rot=(0, th, 0))
        flash(tm, MEL[i]['t'], 0.4, 26.0, 4.0)
        CON[i] = p + nrm * (R + 0.003)
        if k > 0:
            ROLL[i] = True
        burst(p + Vector((0, -0.05, 0.01)), MEL[i]['t'], col, n=5, speed=0.6, life=0.25, size=0.006)
    # ribs to the wall
    for p in (start, end):
        cyl((p.x, 0.62, p.z - 0.03), (p.x, YB + 0.04, p.z - 0.03), 0.007, M_CHROME, 8)


def peg(i, x):
    h = MEL[i]
    c = Vector((x, YB, zt(h['t']) - 0.03))
    col = ncol(h['midi'])
    body = cyl((x, 0.62, c.z), (x, YB - 0.01, c.z), 0.028, mat(f'peg{i}', (0.1, 0.1, 0.12), 0.35, metal=0.5), 24)
    capm = mat(f'pegcap{i}', col, 0.2, emit=col, emit_s=1.0)
    cap = sphere((x, YB - 0.012, c.z), 0.03, capm, scale=(1, 0.7, 1))
    flash(capm, h['t'], 1.0, 30.0, 4.5)
    CON[i] = Vector((x, YB, c.z + 0.03 + R))
    burst(Vector((x, YB - 0.05, c.z + 0.03)), h['t'], col)
    pulse_ring(Vector((x, YB - 0.04, c.z)), h['t'], col)
    return body, cap


def drum_disc(i, x, r=0.085):
    h = MEL[i]
    z = zt(h['t']) - 0.03
    bracket(Vector((x, YB, z - 0.04)))
    cyl((x, YB, z - 0.04), (x, YB, z - 0.012), 0.02, M_CHROME, 12)
    shell = cyl((x, YB, z - 0.026), (x, YB, z), r, mat(f'drumshell{i}', (0.08, 0.05, 0.12), 0.25, coat=0.9), 40)
    col = ncol(h['midi'])
    rm = mat(f'drumrim{i}', col, 0.2, emit=col, emit_s=3.0)
    rim = torus((x, YB, z), r, 0.007, rm)
    headm = mat(f'drumhead{i}', (0.9, 0.85, 0.9), 0.5, emit=col, emit_s=0.2)
    head = cyl((x, YB, z), (x, YB, z + 0.003), r - 0.006, headm, 40)
    flash(rm, h['t'], 3.0, 35.0, 6.0)
    flash(headm, h['t'], 0.2, 8.0, 0.8)
    for o in (shell, rim, head):
        dip(o, h['t'], -0.01)
    CON[i] = Vector((x, YB, z + 0.003 + R))
    burst(Vector((x, YB - 0.03, z + 0.01)), h['t'], col, n=9)
    pulse_ring(Vector((x, YB, z + 0.005)), h['t'], col, r0=r, r1=r * 2.2, rot=(0, 0, 0))


def xylo(i, x):
    h = MEL[i]
    z = zt(h['t']) - 0.02
    col = ncol(h['midi'])
    base = cube((x, YB, z - 0.025), (0.19, 0.085, 0.02), mat(f'xbase{i}', tuple(c * 0.35 for c in col), 0.45), bevel=0.004)
    barm = mat(f'xbar{i}', (0.85, 0.86, 0.9), 0.15, metal=1.0, emit=col, emit_s=0.0)
    bar = cube((x, YB, z - 0.008), (0.17, 0.06, 0.016), barm, bevel=0.003)
    for s in (-1, 1):
        cyl((x + s * 0.06, YB, z - 0.017), (x + s * 0.06, YB, z + 0.002), 0.005, M_CHROME, 8)
    bracket(Vector((x, YB, z - 0.035)))
    flash(barm, h['t'], 0.0, 16.0, 2.5)
    dip(bar, h['t'], -0.008)
    CON[i] = Vector((x, YB, z + R))
    burst(Vector((x, YB - 0.04, z + 0.005)), h['t'], col)


def flask(i, x):
    h = MEL[i]
    z = zt(h['t']) - 0.02     # top of the cork
    gm = mat(f'flask{i}', (1.0, 0.25, 0.3), 0.05, trans=1.0, emit=(1.0, 0.1, 0.15), emit_s=0.3)
    root = empty((x, YB, z - 0.16), f'flaskroot{i}')
    body = sphere((x, YB, z - 0.115), 0.055, gm, scale=(1, 1, 1.15), segs=32)
    neck = cyl((x, YB, z - 0.07), (x, YB, z - 0.012), 0.018, gm, 20)
    cork = cyl((x, YB, z - 0.014), (x, YB, z), 0.02, mat('cork', (0.55, 0.36, 0.2), 0.7), 16)
    stem = cyl((x, YB, z - 0.175), (x, YB, z - 0.24), 0.006, M_CHROME, 8)
    bracket(Vector((x, YB, z - 0.24)))
    for o in (body, neck, cork):
        parent(o, root)
    flash(gm, h['t'], 0.3, 14.0, 1.5)
    wobble(root, h['t'], axis=1, amp=8)
    CON[i] = Vector((x, YB, z + R))
    burst(Vector((x, YB - 0.04, z)), h['t'], (1.0, 0.2, 0.25))


def cymbal(i, x):
    h = MEL[i]
    z = zt(h['t']) - 0.03
    root = empty((x, YB, z), f'cymroot{i}')
    disc = cyl((x, YB, z - 0.003), (x, YB, z + 0.003), 0.095, M_BRASS, 48)
    bell = sphere((x, YB, z + 0.003), 0.022, M_BRASS, scale=(1, 1, 0.45))
    rm = mat(f'cymrim{i}', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=0.5)
    rim = torus((x, YB, z), 0.095, 0.004, rm)
    for o in (disc, bell, rim):
        parent(o, root)
    cyl((x, YB, z - 0.004), (x, YB, z - 0.11), 0.006, M_CHROME, 8)
    bracket(Vector((x, YB, z - 0.11)))
    wobble(root, h['t'], axis=1, amp=14)
    flash(rm, h['t'], 0.5, 30.0, 3.0)
    CON[i] = Vector((x - 0.03, YB, z + 0.006 + R))
    burst(Vector((x, YB - 0.04, z + 0.01)), h['t'], NEON['amber'], n=12, speed=1.1)


def bumper(i, x_contact, side):
    """Pinball bumper; the ball touches its side. side = +1 means the bumper sits to the right of the contact."""
    h = MEL[i]
    z = zt(h['t'])
    br = 0.055
    cx = x_contact + side * (br + R)
    col = ncol(h['midi'])
    cyl((cx, 0.62, z), (cx, YB - 0.035, z), br, mat(f'bump{i}', (0.06, 0.05, 0.09), 0.25, coat=1.0), 40)
    rm = mat(f'bumprim{i}', col, 0.2, emit=col, emit_s=3.0)
    rim = torus((cx, YB - 0.036, z), br, 0.009, rm, rot=(math.radians(90), 0, 0))
    capm = mat(f'bumpcap{i}', (1, 1, 1), 0.3, emit=col, emit_s=1.0)
    cap = cyl((cx, YB - 0.036, z), (cx, YB - 0.04, z), br * 0.6, capm, 32)
    flash(rm, h['t'], 3.0, 40.0, 6.0)
    flash(capm, h['t'], 1.0, 25.0, 3.0)
    for o in (rim, cap):
        for u, s in ((-1 / FPS, 1.0), (0.04, 1.18), (0.2, 1.0)):
            o.scale = (s, s, s)
            o.keyframe_insert('scale', frame=fr(h['t'] + u))
    CON[i] = Vector((x_contact, YB, z))
    burst(Vector((x_contact, YB - 0.04, z)), h['t'], col, n=8, speed=1.0)


# ---- clone marble playing the bass on speakers / horns
clones = []


def hex_speaker(p, t, col):
    body = cyl(p + Vector((0, 0, -0.05)), p, 0.07, mat('hexbody', (0.06, 0.06, 0.07), 0.35, metal=0.4), 6, smooth_=False)
    cm = mat('hexcone', (0.02, 0.02, 0.025), 0.6)
    cone(p + Vector((0, 0, -0.012)), 0.052, 0.018, 0.022, cm)
    rm = mat('hexring', col, 0.2, emit=col, emit_s=2.0)
    torus(p + Vector((0, 0, 0.002)), 0.056, 0.006, rm)
    bracket(p + Vector((0, 0, -0.03)))
    flash(rm, t, 2.0, 40.0, 5.0)
    pulse_ring(p + Vector((0, 0, 0.004)), t, col, r0=0.06, r1=0.16, rot=(0, 0, 0))
    return p + Vector((0, 0, 0.006 + R2))


def horn(p, t):
    hn = cone(p + Vector((0, 0, -0.05)), 0.018, 0.058, 0.1, M_BRASS)
    rm = mat('hornrim', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=1.0)
    torus(p, 0.058, 0.005, rm)
    cyl(p + Vector((0, 0, -0.1)), p + Vector((0, 0, -0.17)), 0.006, M_CHROME, 8)
    bracket(p + Vector((0, 0, -0.17)))
    flash(rm, t, 1.0, 30.0, 4.0)
    wobble(hn, t, axis=1, amp=6)
    burst(p + Vector((0, -0.03, 0.01)), t, NEON['amber'], n=6)
    return p + Vector((0.0, 0, R2 + 0.004))


def bass_clone(i, side, kind):
    """Under a long note: a small marble pops out of the struck instrument and plays bass notes 2 and 3."""
    group = [b for b in BASS if b['group'] == i]
    start = CON[i] + Vector((0, 0, -R + R2))
    col = NEON['cyan'] if kind == 'speaker' else NEON['amber']
    pts = [(group[0]['t'], start)]
    for k, b in enumerate(group[1:]):
        base = CON[i] + Vector((side * (0.27 + 0.22 * k), 0, -0.10 - 0.12 * k))
        p = base - Vector((0, 0, R2))
        top = hex_speaker(p, b['t'], col) if kind == 'speaker' else horn(p, b['t'])
        pts.append((b['t'], top))
    cm = mat(f'clone{i}', (0.7, 0.95, 1.0), 0.04, trans=1.0)
    core = mat(f'clonecore{i}', col, 0.3, emit=col, emit_s=12)
    o = sphere(start, R2, cm, segs=24)
    ci = sphere(start, R2 * 0.55, core, segs=12)
    t_off = pts[-1][0] + 0.45
    clones.append((o, ci, pts, t_off, side))
    key_vis(o, pts[0][0], t_off)
    key_vis(ci, pts[0][0], t_off)


# ---------------------------------------------------------------- place the stations (hand-tuned x, z from time)
tile_rail([0, 1, 2, 3, 4], -0.62)
peg(5, 0.20)
peg(6, -0.08)
peg(7, 0.22)
drum_disc(8, -0.04)
xylo(9, -0.70)
xylo(10, -0.46)
xylo(11, -0.22)
cymbal(12, 0.06)
flask(13, -0.44)
flask(14, -0.20)
flask(15, 0.04)
drum_disc(16, 0.30)
# 17: the paddle (below)
for k, i in enumerate(range(18, 23)):
    bumper(i, 0.12 if k % 2 == 0 else -0.12, 1 if k % 2 == 0 else -1)
peg(23, 0.30)
peg(24, 0.02)
peg(25, 0.30)
drum_disc(26, 0.04)
xylo(27, -0.70)
xylo(28, -0.46)
xylo(29, -0.22)
cymbal(30, 0.10)
tile_rail([31, 32, 33], -0.48, slope_deg=9.0)

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


# yellow launches the ball from her halo (the hook)
yel = character(-0.95, 0.42, (0.95, 0.85, 0.25), (1.0, 0.3, 0.7), 'halo', 'yel')
BALL0 = Vector((-0.95, YB - 0.12, 0.42 + 0.41 + 0.035))
# blue: the paddle save
pad_h = MEL[S.PADDLE_INDEX]
C_pad = Vector((-0.36, YB, zt(pad_h['t'])))
CON[S.PADDLE_INDEX] = C_pad
PL = 0.17
pivot = Vector((C_pad.x - (PL + R + 0.008), YB, C_pad.z))
blue = character(pivot.x - 0.14, C_pad.z + 0.15, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'blue')
piv = empty(pivot, 'paddle_pivot')
M_PAD = mat('paddle', NEON['cyan'], 0.3, emit=NEON['cyan'], emit_s=6)
parent(cyl(pivot, pivot + Vector((PL - 0.01, 0, 0)), 0.012, M_CHROME), piv)
parent(cyl(pivot + Vector((PL - 0.008, 0, 0)), pivot + Vector((PL + 0.008, 0, 0)), 0.09, M_PAD, 32), piv)
th = pad_h['t']
for t, ang in ((0.0, 0.0), (th - 0.5, 0.0), (th - 0.14, 38.0), (th, 0.0), (th + 0.1, -42.0), (th + 0.6, -42.0), (th + 1.0, 0.0)):
    piv.rotation_euler.y = math.radians(ang)
    piv.keyframe_insert('rotation_euler', index=1, frame=fr(t))
flash(M_PAD, th, 6.0, 30.0, 6.0)
burst(C_pad + Vector((-R, -0.05, 0)), th, NEON['cyan'], n=10, speed=1.2)

# ================================================================ finale: big drum, bells, pink
DR = MEL[-1]
DX, DZ = 0.10, zt(DR['t']) - 0.03
cyl((DX, YB, DZ - 0.12), (DX, YB, DZ), 0.21, mat('bigshell', (0.10, 0.04, 0.12), 0.25, coat=1.0), 48)
big_rim = mat('bigrim', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=5)
torus((DX, YB, DZ), 0.21, 0.013, big_rim)
big_head = mat('bighead', (1, 0.6, 0.85), 0.3, emit=(1.0, 0.35, 0.7), emit_s=1.0)
cyl((DX, YB, DZ), (DX, YB, DZ + 0.004), 0.195, big_head, 48)
emit_keys(big_rim, ((TL - 1 / FPS, 5), (TL, 50), (TL + 1.2, 12)))
emit_keys(big_head, ((TL - 1 / FPS, 1), (TL, 25), (TL + 1.2, 4)))
cyl((DX, YB, DZ - 0.12), (DX, YB, DZ - 1.2), 0.045, M_BRASS)
CON[DR['i']] = Vector((DX, YB, DZ + 0.004 + R))
pulse_ring(Vector((DX, YB, DZ + 0.01)), TL, (1, 0.75, 0.9), r0=0.21, r1=0.9, life=0.5, rot=(0, 0, 0))
burst(Vector((DX, YB - 0.04, DZ + 0.02)), TL, NEON['magenta'], n=18, speed=1.7, life=0.5)
pink = character(DX - 0.66, DZ + 0.1, (0.98, 0.45, 0.70), (0.55, 0.2, 1.0), 'ears', 'pink')

BELLS = [Vector((DX + 0.30, YB, DZ - 0.02)), Vector((DX + 0.50, YB, DZ + 0.12)),
         Vector((DX + 0.70, YB, DZ + 0.26)), Vector((DX + 0.90, YB, DZ + 0.40))]
tag_balls = []
for k, (bp, tg) in enumerate(zip(BELLS, TAG)):
    cn = ['cyan', 'violet', 'lime', 'amber'][k]
    hang = empty(bp + Vector((0, 0, 0.16)), f'bellhang{k}')
    bm = mat(f'bell{k}', NEON[cn], 0.15, metal=0.3, emit=NEON[cn], emit_s=1.2)
    bell_o = cone(bp + Vector((0, 0, 0.045)), 0.06, 0.025, 0.09, bm)
    rim = torus(bp, 0.06, 0.006, mat(f'bellrim{k}', NEON[cn], 0.2, emit=NEON[cn], emit_s=6))
    rod = cyl(bp + Vector((0, 0, 0.09)), bp + Vector((0, 0, 0.16)), 0.004, M_CHROME, 8)
    bracket(bp + Vector((0, 0, 0.16)))
    for o in (bell_o, rim, rod):
        parent(o, hang)
    emit_keys(bm, ((tg['t'] - 1 / FPS, 1.2), (tg['t'], 30), (tg['t'] + 0.5, 6)))
    wobble(hang, tg['t'], axis=1, amp=16)
    burst(bp + Vector((0, -0.06, 0)), tg['t'], NEON[cn], n=8, speed=0.9)
    tb = sphere((0, 0, 0), R * 0.6, mat(f'tagball{k}', (0.9, 0.95, 1.0), 0.05, trans=1.0), segs=20)
    tc = sphere((0, 0, 0), R * 0.33, mat(f'tagcore{k}', NEON[cn], 0.3, emit=NEON[cn], emit_s=14), segs=10)
    tag_balls.append((tb, tc, bp + Vector((0, 0, -0.02 - R * 0.6)), tg['t']))


# ================================================================ ball motion
def ballistic(p0, t0, p1, t1, t):
    T = t1 - t0
    v = (p1 - p0 + Vector((0, 0, 0.5 * G * T * T))) / T
    u = t - t0
    return p0 + v * u + Vector((0, 0, -0.5 * G * u * u))


PATH = [(0.0, BALL0)] + [(h['t'], CON[h['i']]) for h in MEL]


def ball_pos(t):
    if t <= 0.0:
        return BALL0
    for k in range(len(PATH) - 1):
        (t0, p0), (t1, p1) = PATH[k], PATH[k + 1]
        if t <= t1:
            if ROLL.get(MEL[k]['i'] if k < len(MEL) else -1):
                pass
            # rolling along a tile rail: straight line between the two tiles
            if k >= 1 and ROLL.get(k):
                return p0.lerp(p1, (t - t0) / (t1 - t0))
            return ballistic(p0, t0, p1, t1, t)
    u = t - TL
    return PATH[-1][1] + Vector((0, 0, max(0.0, 0.13 * math.exp(-u * 2.4) * abs(math.sin(u * 7.5)))))


# glass marble with a glowing swirl core
mg = mat('marbleglass', (0.95, 0.9, 1.0), 0.03, trans=1.0, coat=1.0)
core_m = bpy.data.materials.new('marblecore')
core_m.use_nodes = True
nt_ = core_m.node_tree
bsdf = nt_.nodes['Principled BSDF']
wave = nt_.nodes.new('ShaderNodeTexWave')
wave.wave_type = 'RINGS'
wave.inputs['Scale'].default_value = 3.0
wave.inputs['Distortion'].default_value = 9.0
ramp = nt_.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (1.0, 0.1, 0.5, 1)
ramp.color_ramp.elements[1].color = (0.2, 0.7, 1.0, 1)
nt_.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
nt_.links.new(ramp.outputs['Color'], bsdf.inputs['Emission Color'])
bsdf.inputs['Emission Strength'].default_value = 9.0
ball = sphere((0, 0, 0), R, mg, segs=40)
core = sphere((0, 0, 0), R * 0.62, core_m, segs=24)
glow_l = bpy.data.lights.new('ballglow', 'POINT')
glow_l.energy, glow_l.color, glow_l.shadow_soft_size = 2.0, (1.0, 0.4, 0.75), 0.02
glow_o = bpy.data.objects.new('ballglow', glow_l)
sc.collection.objects.link(glow_o)
spin = 0.0
prev = ball_pos(0.0)
for f in range(1, N + 1):
    t = (f - 1) / FPS
    p = ball_pos(t)
    spin += (p - prev).length / R
    prev = p
    for o in (ball, core, glow_o):
        o.location = p
        o.keyframe_insert('location', frame=f)
    core.rotation_euler = (spin * 0.7, spin, 0)
    core.keyframe_insert('rotation_euler', frame=f)

for o, ci, pts, t_off, side in clones:
    f = int(fr(pts[0][0]))
    while f <= fr(t_off) + 1:
        t = (f - 1) / FPS
        if t <= pts[-1][0]:
            for (t0, p0), (t1, p1) in zip(pts[:-1], pts[1:]):
                if t <= t1:
                    p = ballistic(p0, t0, p1, t1, t)
                    break
        else:
            u = t - pts[-1][0]
            p = pts[-1][1] + Vector((side * 0.5 * u, 0, 1.2 * u - 0.5 * G * u * u))
        o.location = ci.location = p
        o.keyframe_insert('location', frame=f)
        ci.keyframe_insert('location', frame=f)
        f += 1

for tb, tc, target, tt in tag_balls:
    start = Vector((DX, YB, DZ + 0.03))
    t_s = TL + 0.06
    key_vis(tb, t_s)
    key_vis(tc, t_s)
    f = int(fr(t_s))
    while f <= N:
        t = (f - 1) / FPS
        if t <= tt:
            p = ballistic(start, t_s, target, tt, t)
        else:
            u = min(t - tt, 0.7)
            p = target + Vector((0.25 * u, 0, 0.8 * u - 0.5 * G * u * u))
        tb.location = tc.location = p
        tb.keyframe_insert('location', frame=f)
        tc.keyframe_insert('location', frame=f)
        f += 1

# confetti
t_c = TL + S.CONFETTI_AT
for k in range(80):
    cn = rng.choice(list(NEON))
    o = cube((0, 0, 0), (0.018, 0.004, 0.011), mat(f'conf{k}', NEON[cn], 0.3, emit=NEON[cn], emit_s=rng.uniform(8, 20)))
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

# acting
track_eyes(yel, ball_pos)
track_eyes(blue, ball_pos)
track_eyes(pink, ball_pos)
for t, dz, sq in ((0.0, -0.02, 0.86), (0.08, 0.06, 1.1), (0.25, 0.0, 0.96), (0.4, 0.0, 1.0)):
    yel['root'].location.z = yel['z0'] + dz
    yel['root'].scale = (1 / sq ** 0.5, 1, sq)
    yel['root'].keyframe_insert('location', index=2, frame=fr(t))
    yel['root'].keyframe_insert('scale', frame=fr(t))
mouth_o(yel, 0.05, 0.6, 1.6)
mouth_o(blue, th - 0.35, th - 0.02, 1.5)
hop(blue, th + 0.25, 0.10)
hop(pink, TL + 0.02, 0.2)
mouth_o(pink, TL, TL + 1.6, 2.0)
hop(pink, TL + 0.7, 0.12)
for ch in (yel, blue):
    hop(ch, TL + 0.05, 0.16)
    hop(ch, TL + 0.6, 0.1)
    mouth_o(ch, TL, TL + 1.8, 1.8)

# ================================================================ camera: three-quarter view, tracking the ball
bpy.ops.object.camera_add(location=(0, -4, 0))
cam = bpy.context.object
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 3.5
sc.camera = cam
OFF = Vector((1.05, -3.75, 0.95))   # camera offset from its target
FULL = Vector((0.0, YB, (0.6 + DZ) / 2))


def target(t):
    # smooth follow: a lagged average of the ball, but never above the music's descent line
    acc, wsum = Vector((0, 0, 0)), 0.0
    for j in range(7):
        tt = max(0.0, t - j * 0.05)
        w = 1.0 / (1 + j)
        acc += ball_pos(tt) * w
        wsum += w
    p = acc / wsum
    p.x = 0.35 * p.x
    p.y = YB
    return p


def cam_at(t):
    tg = target(t)
    off = OFF.copy()
    lens = 38.0
    k0 = smooth(t / 1.0)                                  # hook: start tight on yellow
    tg = tg.lerp(Vector((-0.95, YB, 0.55)), 1 - k0)
    off = off * (0.55 + 0.45 * k0)
    lens = 46 * (1 - k0) + lens * k0
    ks = smooth((t - (th - 0.8)) / 0.5) * (1 - smooth((t - (th + 0.5)) / 0.6))   # push in on the save
    off = off * (1 - 0.22 * ks)
    tg = tg.lerp(Vector((C_pad.x - 0.1, YB, C_pad.z + 0.05)), 0.4 * ks)
    kh = smooth((t - (TL - 0.9)) / 1.1)                   # settle on the drum
    tg = tg.lerp(Vector((DX + 0.2, YB, DZ + 0.15)), kh)
    kr = smooth((t - (TL + S.REVEAL_START)) / S.REVEAL_LEN)  # the reveal
    tg = tg.lerp(FULL, kr)
    off = off.lerp(Vector((2.2, -8.6, 1.2)), kr)
    lens = lens * (1 - kr) + 33 * kr
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


# lights that travel with the camera: warm key from top-left (casts the wall shadows), cyan and magenta rims
def area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    lt = bpy.context.object
    lt.data.energy, lt.data.color, lt.data.size = energy, col, size
    lt.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return lt


sc.frame_set(1)
c0 = cam.matrix_world.translation.copy()
t0 = c0 - OFF * 0.55
for lt in (area(t0 + Vector((-1.6, -2.0, 2.4)), t0, 260, (1.0, 0.86, 0.75), 1.2),
           area(t0 + Vector((-2.6, -0.8, 0.2)), t0, 120, (0.2, 0.75, 1.0), 2.0),
           area(t0 + Vector((2.4, -1.2, -0.6)), t0, 150, (1.0, 0.15, 0.6), 2.0)):
    parent(lt, cam)

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

print('frames total', N, 'seconds', round(T_END, 2))
if a.stills:
    for fs in a.stills.split(','):
        sc.frame_set(int(fs))
        sc.render.filepath = str(Path(a.out).resolve()) + f'{int(fs):04d}.png'
        bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = str(Path(a.out).resolve())
    if a.frames:
        lo, hi = (int(v) for v in a.frames.split('-'))
        sc.frame_start, sc.frame_end = lo, hi
    bpy.ops.render.render(animation=True)
