"""Neon music-machine look test: one still frame of an original-character music machine.

A glowing ball has just struck a drum pad; neon xylophone bars step down the wall;
two original characters on brass pedestals react. Wordless, original, no third-party IP.

Run with a Python that has bpy 4.5:
    python still.py -- --res 720x1280 --samples 48 --out still.png
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument('--res', default='720x1280')
ap.add_argument('--samples', type=int, default=48)
ap.add_argument('--out', default='still.png')
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
W, H = (int(v) for v in a.res.split('x'))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 6
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Punchy'

world = bpy.data.worlds.new('w')
sc.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.004, 0.004, 0.012, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0


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


def add(o, m):
    o.data.materials.append(m)
    return o


def cube(loc, scale, m, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = scale
    if bevel:
        bpy.ops.object.transform_apply(scale=True)
        md = o.modifiers.new('b', 'BEVEL')
        md.width, md.segments = bevel, 3
    bpy.ops.object.shade_smooth()
    return add(o, m)


def sphere(loc, r, m, scale=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r, location=loc)
    o = bpy.context.object
    if scale:
        o.scale = scale
    bpy.ops.object.shade_smooth()
    return add(o, m)


def cyl(p0, p1, r, m, verts=32):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    bpy.ops.object.shade_smooth()
    return add(o, m)


# --- materials ---------------------------------------------------------------
M_WALL = mat('wall', (0.025, 0.025, 0.035), 0.55)
M_BRASS = mat('brass', (0.85, 0.62, 0.25), 0.22, metal=1.0)
M_CHROME = mat('chrome', (0.9, 0.9, 0.95), 0.08, metal=1.0)
M_DARK = mat('dark', (0.02, 0.02, 0.025), 0.3, coat=0.6)
NEON = {
    'cyan': (0.05, 0.85, 1.0), 'magenta': (1.0, 0.08, 0.55), 'violet': (0.55, 0.2, 1.0),
    'lime': (0.45, 1.0, 0.25), 'amber': (1.0, 0.6, 0.08),
}
BAR_COLS = ['cyan', 'violet', 'magenta', 'amber', 'lime', 'cyan']

# --- back wall: dark vertical slats -------------------------------------------
for k in range(-14, 15):
    cube((k * 0.16, 0.6, 2.2), (0.14, 0.06, 6.0), M_WALL, bevel=0.01)
# floor
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.6))
add(bpy.context.object, mat('floor', (0.02, 0.02, 0.03), 0.15, coat=1.0))

# --- neon xylophone bars stepping down the wall --------------------------------
bars = []
for i, cname in enumerate(BAR_COLS):
    x = -0.95 + i * 0.32
    z = 3.0 - i * 0.36
    w = 0.30 - i * 0.012
    glow = 6.0 if i != 3 else 0.6
    m = mat(f'bar{i}', NEON[cname], 0.25, emit=NEON[cname], emit_s=glow)
    cube((x, 0.35, z), (w, 0.12, 0.05), m, bevel=0.012)
    # chrome pins holding each bar
    for s in (-1, 1):
        cyl((x + s * w * 0.35, 0.55, z), (x + s * w * 0.35, 0.28, z), 0.008, M_CHROME)
    bars.append((x, z))

# --- big drum pad on the right (just struck: brightest) -----------------------
pad_x, pad_z = 0.62, 0.95
cyl((pad_x, 0.55, pad_z), (pad_x, 0.30, pad_z), 0.26, M_DARK, verts=64)
bpy.ops.mesh.primitive_torus_add(major_radius=0.26, minor_radius=0.018, location=(pad_x, 0.30, pad_z),
                                 rotation=(math.radians(90), 0, 0))
add(bpy.context.object, mat('padring', NEON['magenta'], 0.2, emit=NEON['magenta'], emit_s=18))
cyl((pad_x, 0.31, pad_z), (pad_x, 0.295, pad_z), 0.22, mat('padface', (1, 0.5, 0.8), 0.3, emit=(1.0, 0.35, 0.7), emit_s=9))
# impact ring flash
bpy.ops.mesh.primitive_torus_add(major_radius=0.36, minor_radius=0.006, location=(pad_x, 0.27, pad_z),
                                 rotation=(math.radians(90), 0, 0))
add(bpy.context.object, mat('flash', (1, 1, 1), 0.2, emit=(1.0, 0.7, 0.9), emit_s=12))

# --- chrome rail: one smooth bevelled curve from the top bar toward the pad ---
cd = bpy.data.curves.new('rail', 'CURVE')
cd.dimensions = '3D'
cd.bevel_depth = 0.008
cd.bevel_resolution = 4
sp = cd.splines.new('POLY')
N = 60
sp.points.add(N - 1)
for t in range(N):
    u = t / (N - 1)
    x = -1.15 + u * 1.75
    z = 3.25 - u * 1.95 + 0.12 * math.sin(u * math.pi * 5)
    sp.points[t].co = (x, 0.24, z, 1)
ro = bpy.data.objects.new('rail', cd)
sc.collection.objects.link(ro)
ro.data.materials.append(M_CHROME)

# --- glowing ball with a short motion trail --------------------------------------
ball = Vector((0.55, 0.18, 1.22))
sphere(ball, 0.075, mat('ball', (1, 0.2, 0.6), 0.1, emit=(1.0, 0.25, 0.65), emit_s=25))
for j in range(1, 8):
    p = ball + Vector((-0.06 * j, 0.0, 0.05 * j + 0.004 * j * j))
    sphere(p, 0.075 * (1 - j * 0.11), mat(f'trail{j}', (1, 0.2, 0.6), 0.3,
                                           emit=(1.0, 0.25, 0.65), emit_s=6.0 * (1 - j / 8)))

# --- characters: original brass-pedestal busts with big anime eyes -------------
M_WHITE = mat('eyewhite', (0.95, 0.95, 0.97), 0.25)
M_HI = mat('hilite', (1, 1, 1), 0.2, emit=(1, 1, 1), emit_s=4)


def eye(c, r, iris_col, look=(0.0, 0.0), lid=0.0):
    c = Vector(c)
    sphere(c, r, M_WHITE, scale=(1.0, 0.45, 1.15))
    ic = c + Vector((look[0] * r * 0.3, -r * 0.42, look[1] * r * 0.3))
    sphere(ic, r * 0.62, mat('iris', iris_col, 0.2, emit=iris_col, emit_s=1.2), scale=(1.0, 0.35, 1.1))
    sphere(ic + Vector((0, -r * 0.18, 0)), r * 0.30, mat('pupil', (0.01, 0.01, 0.02), 0.2), scale=(1, 0.35, 1.1))
    sphere(ic + Vector((r * 0.22, -r * 0.30, r * 0.28)), r * 0.13, M_HI)
    sphere(ic + Vector((-r * 0.2, -r * 0.30, -r * 0.25)), r * 0.06, M_HI)


def character(x, z, body_col, iris_col, accent, mood):
    # pedestal
    cube((x, 0.15, z - 0.42), (0.36, 0.30, 0.16), M_BRASS, bevel=0.02)
    cube((x, -0.005, z - 0.42), (0.22, 0.01, 0.07), M_DARK)
    # pawn body + head
    bm = mat('body', body_col, 0.35, coat=0.8)
    cyl((x, 0.15, z - 0.34), (x, 0.15, z - 0.12), 0.13, bm)
    sphere((x, 0.15, z - 0.12), 0.13, bm, scale=(1, 1, 0.6))
    sphere((x, 0.15, z + 0.12), 0.24, bm)
    # neon rim / accent on top
    if accent == 'antenna':
        cyl((x, 0.15, z + 0.34), (x + 0.03, 0.15, z + 0.50), 0.008, M_CHROME)
        sphere((x + 0.03, 0.15, z + 0.51), 0.03, mat('ant', NEON['cyan'], 0.2, emit=NEON['cyan'], emit_s=15))
    else:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.014, location=(x, 0.15, z + 0.42))
        add(bpy.context.object, mat('halo', NEON['amber'], 0.2, emit=NEON['amber'], emit_s=12))
    # eyes
    if mood == 'wow':
        eye((x - 0.095, -0.02, z + 0.15), 0.088, iris_col, look=(1.0, 0.2))
        eye((x + 0.095, -0.02, z + 0.15), 0.088, iris_col, look=(1.0, 0.2))
        sphere((x + 0.01, -0.06, z - 0.02), 0.034, mat('mouth', (0.15, 0.02, 0.05), 0.4), scale=(1, 0.5, 1.3))
    else:
        eye((x - 0.095, -0.02, z + 0.15), 0.088, iris_col, look=(-1.0, 0.6))
        eye((x + 0.095, -0.02, z + 0.15), 0.088, iris_col, look=(-1.0, 0.6))
        # small smug smile: thin torus arc
        bpy.ops.mesh.primitive_torus_add(major_radius=0.04, minor_radius=0.007, location=(x - 0.01, -0.05, z + 0.0),
                                         rotation=(math.radians(90), 0, 0))
        add(bpy.context.object, mat('smile', (0.15, 0.02, 0.05), 0.4))


character(-0.62, 0.65, (0.20, 0.35, 0.95), (0.1, 0.9, 1.0), 'antenna', 'wow')     # surprised, watching the ball
character(0.05, 0.30, (0.95, 0.85, 0.25), (1.0, 0.3, 0.7), 'halo', 'smug')         # pleased drummer below the pad

# --- lights: cyan from left, magenta from right, soft top ----------------------
def area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.data.energy, l.data.color, l.data.size = energy, col, size
    l.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


area((-3.0, -1.5, 2.5), (0, 0.4, 1.6), 260, (0.2, 0.75, 1.0), 2.0)
area((3.0, -1.5, 1.5), (0, 0.4, 1.4), 300, (1.0, 0.15, 0.6), 2.0)
area((0, -2.5, 4.5), (0, 0.4, 1.5), 40, (0.8, 0.8, 1.0), 4.0)

# --- camera ----------------------------------------------------------------------
bpy.ops.object.camera_add(location=(0.0, -6.1, 1.65))
cam = bpy.context.object
cam.data.lens = 50
cam.rotation_euler = (Vector((-0.05, 0.4, 1.6)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = 6.2
cam.data.dof.aperture_fstop = 5.6
sc.camera = cam

# bloom-like glow via compositor glare
sc.use_nodes = True
nt = sc.node_tree
rl = nt.nodes['Render Layers']
comp = nt.nodes['Composite']
gl = nt.nodes.new('CompositorNodeGlare')
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.size = 8
if hasattr(gl, 'threshold'):
    gl.threshold = 0.9
nt.links.new(rl.outputs['Image'], gl.inputs['Image'])
nt.links.new(gl.outputs['Image'], comp.inputs['Image'])

sc.render.filepath = str(Path(a.out).resolve())
bpy.ops.render.render(write_still=True)
print('rendered', a.out)
