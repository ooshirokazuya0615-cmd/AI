"""
Build a representative 3D marble/peg scene with bpy, bake the Bullet rigid-body
simulation at the physics step rate (600 Hz), extract collision events, convert
the motion to keyframes at the video frame rate and save a .blend for rendering.

  venv/bin/python build_scene.py --seconds 8 --fps 60 --out scene.blend
"""
import argparse
import json
import math
import time
from pathlib import Path

import bpy
import mathutils
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ap = argparse.ArgumentParser()
ap.add_argument('--seconds', type=float, default=8.0)
ap.add_argument('--fps', type=int, default=60)
ap.add_argument('--substeps', type=int, default=10, help='physics steps per video frame')
ap.add_argument('--balls', type=int, default=14)
ap.add_argument('--out', default='scene.blend')
ap.add_argument('--res', default='1080x1920')
a = ap.parse_args()

HERE = Path(__file__).resolve().parent
W, H = (int(v) for v in a.res.split('x'))
SIM_HZ = a.fps * a.substeps            # Bullet fixed step = 1 / SIM_HZ
N_FRAMES = int(a.seconds * a.fps)
N_STEPS = N_FRAMES * a.substeps
R = 0.30                               # ball radius
G = 9.81

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100


# ---------------------------------------------------------------- materials
def principled(name, color, rough=0.3, metal=0.0, transmission=0.0, sss=0.0,
               coat=0.0, ior=1.45, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['Subsurface Weight'].default_value = sss
    b.inputs['Subsurface Radius'].default_value = (0.6, 0.3, 0.2)
    b.inputs['Subsurface Scale'].default_value = 0.25
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.03
    b.inputs['IOR'].default_value = ior
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = 1.0
    if transmission > 0:
        m.use_raytrace_refraction = True        # EEVEE Next screen-space refraction
        m.surface_render_method = 'DITHERED'
    # Workbench "MATERIAL" colour
    m.diffuse_color = (*color, 1)
    m.roughness = rough
    m.metallic = metal
    return m


mat_wall = principled('wall', (0.42, 0.40, 0.45), rough=0.6)
mat_ramp = principled('ramp', (0.13, 0.15, 0.20), rough=0.25, coat=0.6)
mat_peg = principled('peg', (0.92, 0.92, 0.95), rough=0.12, metal=1.0)
mat_frame = principled('frame', (0.95, 0.55, 0.20), rough=0.35, coat=0.5)
ball_mats = [
    principled('glass_cyan', (0.55, 0.95, 1.0), rough=0.02, transmission=1.0, ior=1.5),
    principled('gloss_red', (0.85, 0.05, 0.07), rough=0.15, coat=1.0),
    principled('jelly_orange', (1.0, 0.45, 0.10), rough=0.30, sss=1.0),
    principled('glass_amber', (1.0, 0.75, 0.35), rough=0.02, transmission=1.0, ior=1.5),
    principled('gloss_blue', (0.05, 0.20, 0.85), rough=0.15, coat=1.0),
    principled('jelly_pink', (1.0, 0.35, 0.60), rough=0.30, sss=1.0),
    principled('gold', (1.0, 0.75, 0.30), rough=0.18, metal=1.0),
]


# ---------------------------------------------------------------- geometry
def add_box(name, loc, size, rot_y_deg=0.0, mat=None, render=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    ob.rotation_euler = (0, math.radians(rot_y_deg), 0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.modifier_add(type='BEVEL')
    ob.modifiers['Bevel'].width = min(0.04, min(size) * 0.3)
    ob.modifiers['Bevel'].segments = 2
    if mat:
        ob.data.materials.append(mat)
    ob.hide_render = not render
    return ob


def passive(ob, shape='BOX', restitution=0.5, friction=0.4):
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.rigidbody.object_add(type='PASSIVE')
    ob.rigid_body.collision_shape = shape
    ob.rigid_body.restitution = restitution
    ob.rigid_body.friction = friction
    ob.select_set(False)


bpy.ops.rigidbody.world_add()
rbw = scene.rigidbody_world
rbw.substeps_per_frame = 1             # we bake at SIM_HZ "frames" with 1 substep
rbw.solver_iterations = 20
rbw.point_cache.frame_start = 1
rbw.point_cache.frame_end = N_STEPS + 1

statics = []          # (object, kind) for collision classification

DEPTH = 0.42          # channel half-depth (balls nearly 2D, like the real channels)
back = add_box('back_wall', (0, DEPTH + 0.1, 8.5), (12, 0.2, 22), mat=mat_wall)
passive(back, restitution=0.2, friction=0.0); statics.append((back, 'wall'))
front = add_box('front_glass', (0, -DEPTH - 0.1, 8.5), (12, 0.2, 22), render=False)
passive(front, restitution=0.2, friction=0.0); statics.append((front, 'wall'))
for side, x in (('L', -4.85), ('R', 4.85)):
    s = add_box(f'side_{side}', (x, 0, 8.5), (0.3, 1.2, 22), mat=mat_frame)
    passive(s, restitution=0.5); statics.append((s, 'side'))

rampA = add_box('rampA', (-1.4, 0, 14.0), (6.8, 1.1, 0.25), rot_y_deg=16, mat=mat_ramp)
rampB = add_box('rampB', (1.8, 0, 11.0), (6.2, 1.1, 0.25), rot_y_deg=-19, mat=mat_ramp)
for r in (rampA, rampB):
    passive(r, restitution=0.45, friction=0.5); statics.append((r, 'ramp'))

pegs = []
for row, z in enumerate((8.6, 7.6, 6.6, 5.6, 4.6)):
    off = 0.0 if row % 2 == 0 else 0.55
    x = -3.85 + off
    while x <= 3.86:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=1.0, vertices=24,
                                            location=(x, 0, z), rotation=(math.pi / 2, 0, 0))
        p = bpy.context.active_object
        p.name = f'peg_{row}_{len(pegs)}'
        p.data.materials.append(mat_peg)
        bpy.ops.object.shade_smooth()
        passive(p, shape='CYLINDER', restitution=0.75, friction=0.2)
        statics.append((p, 'peg'))
        pegs.append(p)
        x += 1.1

floor = add_box('floor', (0, 0, 0.4), (10, 1.2, 0.4), mat=mat_frame)
passive(floor, restitution=0.35); statics.append((floor, 'floor'))
for i, x in enumerate((-3.3, -2.0, -0.7, 0.7, 2.0, 3.3)):
    d = add_box(f'divider_{i}', (x, 0, 1.6), (0.12, 1.0, 2.0), mat=mat_frame)
    passive(d, restitution=0.4); statics.append((d, 'divider'))

# marbles
balls = []
for i in range(a.balls):
    x = -4.0 + (i * 0.83) % 2.6
    z = 15.6 + i * 0.5
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, segments=48, ring_count=24,
                                         location=(x, (i % 3 - 1) * 0.04, z))
    b = bpy.context.active_object
    b.name = f'ball_{i:02d}'
    bpy.ops.object.shade_smooth()
    b.data.materials.append(ball_mats[i % len(ball_mats)])
    b.rotation_mode = 'QUATERNION'
    bpy.ops.rigidbody.object_add(type='ACTIVE')
    rb = b.rigid_body
    rb.collision_shape = 'SPHERE'
    rb.mass = 0.1
    rb.friction = 0.3
    rb.restitution = 0.6
    rb.linear_damping = 0.02
    rb.angular_damping = 0.1
    rb.use_deactivation = False
    balls.append(b)

# ---------------------------------------------------------------- camera / light / world
cam_data = bpy.data.cameras.new('cam')
cam_data.lens = 35
cam_data.sensor_fit = 'VERTICAL'
cam_data.sensor_height = 24
cam = bpy.data.objects.new('cam', cam_data)
scene.collection.objects.link(cam)
cam.location = (0, -25, 8.6)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.camera = cam

key = bpy.data.lights.new('key', 'AREA')
key.shape = 'RECTANGLE'
key.size, key.size_y = 8, 4
key.energy = 2200
key_ob = bpy.data.objects.new('key', key)
scene.collection.objects.link(key_ob)
key_ob.location = (-5, -12, 20)
key_ob.rotation_euler = (Vector((0, 0, 8)) - Vector(key_ob.location)).to_track_quat('-Z', 'Y').to_euler()

rim = bpy.data.lights.new('rim', 'AREA')
rim.size = 3
rim.energy = 500
rim.color = (0.6, 0.75, 1.0)
rim_ob = bpy.data.objects.new('rim', rim)
scene.collection.objects.link(rim_ob)
rim_ob.location = (6, -6, 3)
rim_ob.rotation_euler = (Vector((0, 0, 6)) - Vector(rim_ob.location)).to_track_quat('-Z', 'Y').to_euler()

world = bpy.data.worlds.new('world')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.06, 0.09, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
scene.world = world

# ---------------------------------------------------------------- bake at SIM_HZ
# One scene frame == one Bullet step, so we see every physics step (no sub-frame blind spot).
scene.render.fps = SIM_HZ
scene.frame_start, scene.frame_end = 1, N_STEPS + 1
traj = [[None] * (N_STEPS + 1) for _ in balls]       # (pos, quat) per step
t0 = time.time()
for s in range(N_STEPS + 1):
    scene.frame_set(s + 1)
    for bi, b in enumerate(balls):
        mw = b.matrix_world
        traj[bi][s] = (tuple(mw.translation), tuple(mw.to_quaternion()))
bake_s = time.time() - t0
print(f'bake: {N_STEPS} steps @ {SIM_HZ} Hz in {bake_s:.1f} s')

# ---------------------------------------------------------------- collision events
# A contact impulse shows up as a velocity jump that gravity alone cannot explain.
# Times are refined below one physics step by intersecting the ballistic
# trajectories before and after the jump.
dg = bpy.context.evaluated_depsgraph_get()
scene.frame_set(1)
st_verts, st_polys, st_owner = [], [], []
for ob, kind in statics:
    me = ob.evaluated_get(dg).to_mesh()
    base = len(st_verts)
    st_verts += [ob.matrix_world @ v.co for v in me.vertices]
    for p in me.polygons:
        st_polys.append([base + i for i in p.vertices])
        st_owner.append((ob.name, kind))
    ob.evaluated_get(dg).to_mesh_clear()
bvh = BVHTree.FromPolygons(st_verts, st_polys)

dt = 1.0 / SIM_HZ
gvec = Vector((0, 0, -G))
THRESH = 0.35          # m/s of unexplained velocity change in one step


def vel(bi, s):
    return (Vector(traj[bi][s + 1][0]) - Vector(traj[bi][s][0])) / dt


raw = []
for bi in range(len(balls)):
    for s in range(1, N_STEPS - 1):
        v0, v1 = vel(bi, s - 1), vel(bi, s)
        dv = v1 - v0 - gvec * dt
        if dv.length < THRESH:
            continue
        p = Vector(traj[bi][s][0])
        # sub-step time: pre-impact parabola through p(s-1) with v0, post through p(s+1) with v1
        pa, pb = Vector(traj[bi][s - 1][0]), Vector(traj[bi][s + 1][0])
        ta, tb = (s - 1) * dt, (s + 1) * dt
        # difference of the two parabolas is linear in t: c0 + c1 * t = 0 (least squares)
        c1 = v0 - v1 + gvec * (tb - ta)
        c0 = pa - pb - v0 * ta + v1 * tb + 0.5 * gvec * (ta * ta - tb * tb)
        t_hit = -c0.dot(c1) / max(c1.dot(c1), 1e-12)
        t_hit = min(max(t_hit, ta), tb)
        n = dv.normalized()
        c = p - n * R                       # estimated contact point
        hit = bvh.find_nearest(c)
        what, ds = ('?', '?'), 1e9
        if hit[0] is not None:
            ds, what = (hit[0] - c).length, st_owner[hit[2]]
        db, other = 1e9, None
        for bj in range(len(balls)):
            if bj != bi:
                d = (Vector(traj[bj][s][0]) - p).length - 2 * R
                if d < db:
                    db, other = d, bj
        gap = ds
        if db < 0.06 and db < ds:
            what, gap = (balls[other].name, 'ball'), db
        raw.append(dict(ball=bi, step=s, t=t_hit, dv=dv.length,
                        impulse=dv.length * balls[bi].rigid_body.mass,
                        obj=what[0], kind=what[1], gap=round(gap, 4), pos=tuple(round(c, 4) for c in p),
                        normal=tuple(round(c, 4) for c in n)))

# merge: consecutive steps of the same contact, and both sides of a ball-ball hit
raw.sort(key=lambda e: (e['ball'], e['step']))
events = []
for e in raw:
    prev = events[-1] if events else None
    if prev and prev['ball'] == e['ball'] and e['step'] - prev['last_step'] <= 3 and prev['obj'] == e['obj']:
        prev['dv'] += e['dv']; prev['impulse'] += e['impulse']; prev['last_step'] = e['step']
        continue
    e['last_step'] = e['step']
    events.append(e)
final, seen = [], set()
for e in sorted(events, key=lambda e: e['t']):
    if e['kind'] == 'ball':
        other = int(e['obj'].split('_')[1])
        key2 = (min(e['ball'], other), max(e['ball'], other), round(e['t'] * 60))
        if key2 in seen:
            continue
        seen.add(key2)
    final.append(e)
# rolling contact produces many small kicks; keep audible hits only
audible = [e for e in final if e['dv'] > 0.6]
print(f'events: {len(raw)} raw step-kicks -> {len(final)} contacts -> {len(audible)} audible')
kinds = {}
for e in audible:
    kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
print('  by kind:', kinds)

# ---------------------------------------------------------------- keyframes at video fps
for b in balls:
    bpy.context.view_layer.objects.active = b
    b.select_set(True)
    bpy.ops.rigidbody.object_remove()
    b.select_set(False)
bpy.ops.rigidbody.world_remove()
scene.render.fps = a.fps
scene.frame_start, scene.frame_end = 1, N_FRAMES
for bi, b in enumerate(balls):
    b.animation_data_create()
    act = bpy.data.actions.new(f'act_{b.name}')
    b.animation_data.action = act
    frames = list(range(N_FRAMES))
    for path, idx_count, comp in (('location', 3, 0), ('rotation_quaternion', 4, 1)):
        for k in range(idx_count):
            fc = act.fcurves.new(path, index=k)
            fc.keyframe_points.add(len(frames))
            co = []
            for f in frames:
                co += [f + 1, traj[bi][f * a.substeps][comp][k]]
            fc.keyframe_points.foreach_set('co', co)
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()
    # Blender 4.4+ slotted actions: the legacy fcurves API makes a slot, but it must be assigned
    if getattr(b.animation_data, 'action_slot', 1) is None and act.slots:
        b.animation_data.action_slot = act.slots[0]

meta = dict(fps=a.fps, sim_hz=SIM_HZ, seconds=a.seconds, frames=N_FRAMES, radius=R,
            bake_seconds=bake_s, balls=[b.name for b in balls],
            events=[{k: v for k, v in e.items() if k != 'last_step'} for e in audible])
(HERE / 'events.json').write_text(json.dumps(meta, indent=1))
# trajectories at video fps for the GLSL comparison renderer
(HERE / 'traj.json').write_text(json.dumps(dict(
    fps=a.fps, radius=R,
    pos=[[traj[bi][f * a.substeps][0] for f in range(N_FRAMES)] for bi in range(len(balls))],
    pegs=[tuple(p.location) for p in pegs])))
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / a.out))
print('saved', a.out)
