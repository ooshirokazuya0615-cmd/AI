"""Blender look test (frozen moments): shot 1 = a 3D stickman flying kick through a stack of wooden blocks,
shot 2 = the hero in the middle of a crowd of grey stickmen thrown outward.
Run: bvenv/bin/python look.py --res 1080x1920 --samples 40 --out a.png [--shot 1|2]"""
import argparse, math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector, Euler

ap = argparse.ArgumentParser()
ap.add_argument('--res', default='540x960'); ap.add_argument('--samples', type=int, default=32)
ap.add_argument('--out', default='look.png'); ap.add_argument('--shot', type=int, default=1)
ap.add_argument('--engine', default='CYCLES')
a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
W, H = (int(v) for v in a.res.split('x'))
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.film_transparent = False
if a.engine == 'CYCLES':
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.cycles.max_bounces = 6
else:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.eevee.taa_render_samples = a.samples
sc.view_settings.view_transform = 'AgX'
sc.view_settings.look = 'AgX - Medium High Contrast'

def mat(name, col, rough=0.5, metal=0.0, emit=None, emit_s=0.0, sss=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_s
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
    return m

def wood_mat(name, base=(0.32, 0.17, 0.08), scale=6.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexWave'); tex.wave_type = 'BANDS'; tex.bands_direction = 'X'
    tex.inputs['Scale'].default_value = scale; tex.inputs['Distortion'].default_value = 6.0; tex.inputs['Detail'].default_value = 4.0
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[c * 0.55 for c in base], 1); ramp.color_ramp.elements[1].color = (*base, 1)
    nt.links.new(tex.outputs['Fac'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.45
    return m

def cyl_between(p0, p1, r, m, name='seg'):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object; o.name = name
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    for p in (p0, p1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=r, location=p)
        s = bpy.context.object; s.data.materials.append(m); bpy.ops.object.shade_smooth()

def stickman(j, m, r=0.045, head=0.12, name='hero'):
    segs = [('hip', 'neck'), ('neck', 'sh_l'), ('neck', 'sh_r'), ('sh_l', 'el_l'), ('el_l', 'ha_l'), ('sh_r', 'el_r'), ('el_r', 'ha_r'),
            ('hip', 'kn_l'), ('kn_l', 'ft_l'), ('hip', 'kn_r'), ('kn_r', 'ft_r')]
    for s0, s1 in segs:
        cyl_between(j[s0], j[s1], r * (1.25 if (s0, s1) == ('hip', 'neck') else 1.0), m, name)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=head, location=j['head'])
    o = bpy.context.object; o.data.materials.append(m); bpy.ops.object.shade_smooth()

# ---------------- world & stage
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.012, 0.014, 0.022, 1); bg.inputs['Strength'].default_value = 1.0

floor = wood_mat('floor', (0.30, 0.17, 0.085), 3.0)
nt = floor.node_tree; bsdf = nt.nodes['Principled BSDF']; bsdf.inputs['Roughness'].default_value = 0.22
brick = nt.nodes.new('ShaderNodeTexBrick'); brick.inputs['Scale'].default_value = 1.2
brick.inputs['Mortar Size'].default_value = 0.006; brick.offset = 0.5; brick.squash = 1.0
brick.inputs['Brick Width'].default_value = 1.6; brick.inputs['Row Height'].default_value = 0.18
mix = nt.nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs['Fac'].default_value = 1.0
ramp = [n for n in nt.nodes if n.type == 'VALTORGB'][0]
nt.links.new(ramp.outputs['Color'], mix.inputs[1]); nt.links.new(brick.outputs['Color'], mix.inputs[2])
brick.inputs['Color1'].default_value = (1, 1, 1, 1); brick.inputs['Color2'].default_value = (0.85, 0.85, 0.85, 1); brick.inputs['Mortar'].default_value = (0.25, 0.25, 0.25, 1)
nt.links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); bpy.context.object.data.materials.append(floor)
# back wall with a soft vertical light strip pattern (dojo shoji feel)
wall = mat('wall', (0.05, 0.05, 0.06), 0.8)
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 9, 10), rotation=(math.radians(90), 0, 0)); bpy.context.object.data.materials.append(wall)
shoji = mat('shoji', (0.9, 0.85, 0.7), 0.9, emit=(1.0, 0.80, 0.52), emit_s=0.55)
lat = mat('lattice', (0.06, 0.035, 0.02), 0.6)
for k in range(-4, 5):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(k * 2.2, 8.9, 3.2), rotation=(math.radians(90), 0, 0))
    o = bpy.context.object; o.scale = (1.7, 3.6, 1); o.data.materials.append(shoji)
    for g in range(-1, 2):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(k * 2.2 + g * 0.56, 8.85, 3.2)); bpy.context.object.scale = (0.03, 0.03, 3.6); bpy.context.object.data.materials.append(lat)
    for g in range(-3, 4):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(k * 2.2, 8.85, 3.2 + g * 0.5)); bpy.context.object.scale = (1.7, 0.03, 0.03); bpy.context.object.data.materials.append(lat)

ceramic = mat('ceramic', (0.86, 0.84, 0.80), 0.32, sss=0.08)
red = mat('scarf', (0.62, 0.05, 0.04), 0.55)
woodblk = wood_mat('block', (0.62, 0.42, 0.22), 9.0)
grey = mat('grey', (0.18, 0.19, 0.21), 0.5)

if a.shot == 1:
    # hero mid flying side-kick, moving +x, kicking a stack of blocks that bursts
    hip = Vector((-0.2, 0, 1.25))
    j = dict(hip=hip, neck=hip + Vector((-0.26, 0.02, 0.44)), head=hip + Vector((-0.30, 0.03, 0.66)))
    j['sh_l'] = j['neck'] + Vector((0.0, -0.12, -0.03)); j['sh_r'] = j['neck'] + Vector((0.0, 0.12, -0.03))
    j['el_l'] = j['sh_l'] + Vector((0.12, -0.10, -0.14)); j['ha_l'] = j['el_l'] + Vector((0.16, 0.05, 0.12))      # guard in front
    j['el_r'] = j['sh_r'] + Vector((-0.16, 0.10, -0.12)); j['ha_r'] = j['el_r'] + Vector((-0.16, 0.04, 0.06))   # rear arm back for balance
    j['kn_r'] = hip + Vector((0.36, 0.06, 0.04)); j['ft_r'] = j['kn_r'] + Vector((0.40, 0.02, 0.06))   # kicking leg extended
    j['kn_l'] = hip + Vector((0.10, -0.08, -0.32)); j['ft_l'] = j['kn_l'] + Vector((-0.30, -0.02, -0.10))  # tucked leg
    stickman(j, ceramic)
    # scarf trailing behind the neck: a chain of thin flattened capsules
    pts = [j['neck'] + Vector((-0.03 - 0.16 * i, 0.02 * math.sin(i), 0.04 * math.sin(i * 0.9) + 0.02 * i)) for i in range(9)]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        cyl_between(p0, p1, 0.022, red, 'scarf')
    # block stack being hit at the foot: intact lower blocks + burst fragments
    foot = j['ft_r']
    for row in range(5):
        for col in range(2):
            c = Vector((foot.x + 0.24, (col - 0.5) * 0.42, 0.20 + row * 0.40))
            dist = abs(c.z - foot.z)
            if dist < 0.5:
                continue   # these are the ones flying
            bpy.ops.mesh.primitive_cube_add(size=0.40, location=c)
            o = bpy.context.object; o.data.materials.append(woodblk)
            bpy.ops.object.modifier_add(type='BEVEL'); o.modifiers['Bevel'].width = 0.012; o.modifiers['Bevel'].segments = 2
    for k in range(40):
        u = random.uniform(0, 1)
        d = Vector((random.uniform(0.4, 1.0), random.uniform(-0.8, 0.8), random.uniform(-0.3, 0.7))).normalized()
        c = foot + Vector((0.20, 0, 0)) + d * (0.06 + 0.95 * u ** 1.8)
        s = random.uniform(0.05, 0.22) * (1.2 - u * 0.5)
        bpy.ops.mesh.primitive_cube_add(size=1, location=c)
        o = bpy.context.object; o.scale = (s, s * random.uniform(0.3, 1.0), s * random.uniform(0.2, 0.8))
        o.rotation_euler = Euler((random.uniform(0, 6), random.uniform(0, 6), random.uniform(0, 6)))
        o.data.materials.append(woodblk)
    # dust specks
    dust = mat('dust', (0.9, 0.8, 0.6), 1.0, emit=(1.0, 0.85, 0.6), emit_s=0.6)
    for k in range(60):
        d = Vector((random.uniform(0.2, 1.0), random.uniform(-1, 1), random.uniform(-0.4, 0.8))).normalized()
        c = foot + Vector((0.24, 0, 0)) + d * random.uniform(0.2, 1.8)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.005, 0.014), location=c)
        bpy.context.object.data.materials.append(dust)
    cam_loc, cam_tgt, lens = (0.55, -3.0, 0.95), (0.35, 0.0, 1.20), 30
else:
    # one vs many: hero centre in a guard stance, grey opponents tumbling outward like dominoes
    hip = Vector((0, 0, 0.92))
    j = dict(hip=hip, neck=hip + Vector((0.04, 0, 0.50)), head=hip + Vector((0.06, 0, 0.70)))
    j['sh_l'] = j['neck'] + Vector((0, -0.13, -0.03)); j['sh_r'] = j['neck'] + Vector((0, 0.13, -0.03))
    j['el_l'] = j['sh_l'] + Vector((0.18, -0.08, -0.12)); j['ha_l'] = j['el_l'] + Vector((0.20, 0.05, 0.10))
    j['el_r'] = j['sh_r'] + Vector((-0.05, 0.20, -0.12)); j['ha_r'] = j['el_r'] + Vector((0.12, 0.10, 0.12))
    j['kn_l'] = hip + Vector((0.22, -0.18, -0.42)); j['ft_l'] = j['kn_l'] + Vector((0.05, -0.05, -0.47))
    j['kn_r'] = hip + Vector((-0.22, 0.18, -0.42)); j['ft_r'] = j['kn_r'] + Vector((-0.12, 0.05, -0.45))
    stickman(j, ceramic)
    pts = [j['neck'] + Vector((-0.05 - 0.15 * i, 0.03 * i, -0.05 * i + 0.02 * math.sin(i))) for i in range(7)]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        cyl_between(p0, p1, 0.022, red, 'scarf')
    for ring, (rad, n) in enumerate(((1.6, 7), (2.6, 11), (3.6, 15))):
        for k in range(n):
            ang = 2 * math.pi * k / n + ring * 0.3
            base = Vector((math.cos(ang) * rad, math.sin(ang) * rad, 0))
            out = Vector((math.cos(ang), math.sin(ang), 0))
            tilt = math.radians(30 + 22 * (2 - ring) + random.uniform(-10, 10))   # inner ring falls most
            up = (Vector((0, 0, 1)) * math.cos(tilt) + out * math.sin(tilt)).normalized()
            hp = base + up * 0.9
            side = out.cross(Vector((0, 0, 1))).normalized()
            jj = dict(hip=hp, neck=hp + up * 0.5, head=hp + up * 0.7)
            jj['sh_l'] = jj['neck'] - side * 0.13; jj['sh_r'] = jj['neck'] + side * 0.13
            jj['el_l'] = jj['sh_l'] - side * 0.12 + out * 0.14 + up * 0.02; jj['ha_l'] = jj['el_l'] - side * 0.06 + out * 0.18 - up * 0.04
            jj['el_r'] = jj['sh_r'] + side * 0.12 + out * 0.14 + up * 0.02; jj['ha_r'] = jj['el_r'] + side * 0.06 + out * 0.18 - up * 0.04
            jj['kn_l'] = hp - up * 0.42 - side * 0.08 - out * 0.08; jj['ft_l'] = jj['kn_l'] - up * 0.45 + out * 0.05
            jj['kn_r'] = hp - up * 0.42 + side * 0.08 + out * 0.10; jj['ft_r'] = jj['kn_r'] - up * 0.40 + out * 0.25
            stickman(jj, grey, r=0.04, head=0.11, name='mook')
    cam_loc, cam_tgt, lens = (0.8, -6.8, 3.2), (0.0, 0.6, 0.7), 28

# lights: warm key, cool rim, soft fill
def area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object; l.data.energy = energy; l.data.color = col; l.data.size = size
    d = Vector(tgt) - Vector(loc); l.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
area((-3.5, -3.0, 5.0), (0, 0, 1), 900, (1.0, 0.86, 0.68), 3.0)
area((3.0, 4.0, 3.0), (0, 0, 1.2), 1400, (0.55, 0.70, 1.0), 1.5)
area((0.0, -6.0, 1.5), (0, 0, 1.0), 120, (0.9, 0.9, 1.0), 6.0)

bpy.ops.object.camera_add(location=cam_loc)
cam = bpy.context.object; cam.data.lens = lens
d = Vector(cam_tgt) - Vector(cam_loc); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = d.length; cam.data.dof.aperture_fstop = 2.8
sc.camera = cam
sc.render.filepath = str(Path(a.out).resolve())
import time; t0 = time.time()
bpy.ops.render.render(write_still=True)
print('rendered', a.out, round(time.time() - t0, 1), 's')
