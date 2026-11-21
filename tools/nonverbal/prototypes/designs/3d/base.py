"""Shared stage for the hero-design lineup: the same dojo, lights and camera for every design, so only the character changes.

Use from a design script (run with the Blender venv python):
    import os, sys; sys.path.insert(0, '/path/to/designs/3d')
    from base import *
    a = setup()            # parses --res 540x960 --samples 16 --out x.png
    stage()                # floor, back wall, shoji, lights, camera
    J = pose()             # ready-stance joints (world coords, metres), hero at the origin, turned 3/4 to camera
    ... build the hero from J (and any props) ...
    finish(a)              # renders to --out

The hero stands at the origin on the floor (z = 0), about 1.75 m tall, in a fighting-ready stance.
Camera looks at it from the front-right (3/4 view), vertical 9:16 frame, background softly out of focus.
"""
import argparse
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

__all__ = ['bpy', 'math', 'Vector', 'Euler', 'Matrix', 'setup', 'stage', 'pose', 'finish', 'mat', 'wood_mat',
           'cyl_between', 'sphere', 'POSE_LOCAL', 'SEGS', 'CAM']

CAM = dict(loc=(1.45, -3.9, 1.05), tgt=(0.0, 0.0, 0.88), lens=55, fstop=2.8)

# ready stance, hero facing -y (toward the camera side); hero's left is +x
POSE_LOCAL = dict(
    hip=(0.0, 0.0, 0.95), neck=(0.0, 0.02, 1.45), head=(0.0, 0.0, 1.64),
    sh_l=(0.17, 0.02, 1.42), sh_r=(-0.17, 0.02, 1.42),
    el_l=(0.24, -0.12, 1.19), ha_l=(0.12, -0.36, 1.37),    # lead hand forward, fist up
    el_r=(-0.23, -0.04, 1.17), ha_r=(-0.10, -0.22, 1.40),  # rear hand guarding the chin
    kn_l=(0.17, -0.20, 0.52), ft_l=(0.21, -0.30, 0.05),    # lead foot forward
    kn_r=(-0.17, 0.15, 0.50), ft_r=(-0.25, 0.30, 0.05),
)
SEGS = [('hip', 'neck'), ('neck', 'sh_l'), ('neck', 'sh_r'), ('sh_l', 'el_l'), ('el_l', 'ha_l'), ('sh_r', 'el_r'),
        ('el_r', 'ha_r'), ('hip', 'kn_l'), ('kn_l', 'ft_l'), ('hip', 'kn_r'), ('kn_r', 'ft_r')]


def setup(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--res', default='540x960')
    ap.add_argument('--samples', type=int, default=16)
    ap.add_argument('--out', default='draft.png')
    if argv is None:
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    W, H = (int(v) for v in a.res.split('x'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    return a


def mat(name, col, rough=0.5, metal=0.0, emit=None, emit_s=0.0, sss=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_s
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
    if coat:
        b.inputs['Coat Weight'].default_value = coat
    return m


def wood_mat(name, base=(0.32, 0.17, 0.08), scale=6.0, rough=0.45):
    """Simple procedural wood (wave bands). Fine for floors; for close-up props, add noise for real grain."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexWave')
    tex.wave_type = 'BANDS'
    tex.bands_direction = 'X'
    tex.inputs['Scale'].default_value = scale
    tex.inputs['Distortion'].default_value = 6.0
    tex.inputs['Detail'].default_value = 4.0
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[c * 0.55 for c in base], 1)
    ramp.color_ramp.elements[1].color = (*base, 1)
    nt.links.new(tex.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    return m


def cyl_between(p0, p1, r, m, name='seg', caps=True, r1=None):
    """Cylinder (or cone if r1 is given) from p0 to p1, with sphere caps by default. Returns the cylinder object."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    if r1 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=d.length, location=(p0 + p1) / 2)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r, radius2=r1, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    o.name = name
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    if caps:
        for p, rr in ((p0, r), (p1, r if r1 is None else r1)):
            sphere(p, rr, m)
    return o


def sphere(loc, r, m, name='ball', scale=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=r, location=Vector(loc))
    o = bpy.context.object
    o.name = name
    if scale:
        o.scale = scale
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def pose(yaw_deg=-45.0, scale=1.0):
    """Ready-stance joints in world coords. yaw turns the hero about z (default: 3/4 toward the camera)."""
    R = Matrix.Rotation(math.radians(yaw_deg), 3, 'Z')
    return {k: R @ (Vector(v) * scale) for k, v in POSE_LOCAL.items()}


def _area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.data.energy, l.data.color, l.data.size = energy, col, size
    l.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return l


def stage(camera=True):
    sc = bpy.context.scene
    world = bpy.data.worlds.new('w')
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0.012, 0.014, 0.022, 1)
    # floor: varnished hinoki planks
    floor = wood_mat('floor', (0.30, 0.17, 0.085), 3.0, rough=0.22)
    nt = floor.node_tree
    bsdf = nt.nodes['Principled BSDF']
    brick = nt.nodes.new('ShaderNodeTexBrick')
    brick.inputs['Scale'].default_value = 1.2
    brick.inputs['Mortar Size'].default_value = 0.006
    brick.offset, brick.squash = 0.5, 1.0
    brick.inputs['Brick Width'].default_value = 1.6
    brick.inputs['Row Height'].default_value = 0.18
    brick.inputs['Color1'].default_value = (1, 1, 1, 1)
    brick.inputs['Color2'].default_value = (0.85, 0.85, 0.85, 1)
    brick.inputs['Mortar'].default_value = (0.25, 0.25, 0.25, 1)
    mix = nt.nodes.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Fac'].default_value = 1.0
    ramp = [n for n in nt.nodes if n.type == 'VALTORGB'][0]
    nt.links.new(ramp.outputs['Color'], mix.inputs[1])
    nt.links.new(brick.outputs['Color'], mix.inputs[2])
    nt.links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    bpy.context.object.data.materials.append(floor)
    # back wall with glowing shoji panels
    wall = mat('wall', (0.05, 0.05, 0.06), 0.8)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 6, 10), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(wall)
    shoji = mat('shoji', (0.9, 0.85, 0.7), 0.9, emit=(1.0, 0.80, 0.52), emit_s=0.38)
    lat = mat('lattice', (0.06, 0.035, 0.02), 0.6)
    for k in range(-4, 5):
        x = k * 2.2
        bpy.ops.mesh.primitive_plane_add(size=1, location=(x, 5.9, 2.4), rotation=(math.radians(90), 0, 0))
        o = bpy.context.object
        o.scale = (1.7, 3.6, 1)
        o.data.materials.append(shoji)
        for g in range(-1, 2):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x + g * 0.56, 5.85, 2.4))
            bpy.context.object.scale = (0.03, 0.03, 3.6)
            bpy.context.object.data.materials.append(lat)
        for g in range(-3, 4):
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 5.85, 2.4 + g * 0.5))
            bpy.context.object.scale = (1.7, 0.03, 0.03)
            bpy.context.object.data.materials.append(lat)
    # lights: warm key (front-left, high), cool rim (back-right), soft fill (front)
    _area((-2.8, -3.2, 4.2), (0, 0, 1.0), 800, (1.0, 0.86, 0.68), 3.0)
    _area((2.6, 3.0, 2.8), (0, 0, 1.2), 1100, (0.55, 0.70, 1.0), 1.5)
    _area((1.0, -5.5, 1.4), (0, 0, 1.0), 110, (0.9, 0.9, 1.0), 6.0)
    if camera:
        bpy.ops.object.camera_add(location=CAM['loc'])
        cam = bpy.context.object
        cam.data.lens = CAM['lens']
        d = Vector(CAM['tgt']) - Vector(CAM['loc'])
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = d.length
        cam.data.dof.aperture_fstop = CAM['fstop']
        sc.camera = cam


def finish(a):
    sc = bpy.context.scene
    sc.render.filepath = str(Path(a.out).resolve())
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('rendered', a.out, round(time.time() - t0, 1), 's')
