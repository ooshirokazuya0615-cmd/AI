"""
Accuracy check of collision-time extraction from Blender's Bullet rigid body world.
One sphere (r = 0.3) dropped from z = 5 onto a passive box whose top is z = 0.
Analytic: first impact when centre z = r -> t1 = sqrt(2 (z0 - r) / g);
bounce speed = e v1 with e = e_ball * e_floor (Blender multiplies restitutions)
-> t2 = t1 + 2 e v1 / g.
"""
import math
import sys

import bpy
from mathutils import Vector

FPS, SUB = 60, int(sys.argv[-1]) if sys.argv[-1].isdigit() else 10
HZ = FPS * SUB
R, Z0, G = 0.3, 5.0, 9.81
E_BALL, E_FLOOR = 0.8, 0.9

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
bpy.ops.rigidbody.world_add()
rbw = sc.rigidbody_world
rbw.substeps_per_frame = 1
rbw.solver_iterations = 20
N = int(2.5 * HZ)
rbw.point_cache.frame_end = N + 1
sc.render.fps = HZ
sc.frame_end = N + 1

bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.5))
floor = bpy.context.active_object
bpy.ops.rigidbody.object_add(type='PASSIVE')
floor.rigid_body.restitution = E_FLOOR
bpy.ops.mesh.primitive_uv_sphere_add(radius=R, location=(0, 0, Z0))
ball = bpy.context.active_object
bpy.ops.rigidbody.object_add(type='ACTIVE')
ball.rigid_body.collision_shape = 'SPHERE'
ball.rigid_body.restitution = E_BALL
ball.rigid_body.linear_damping = 0.0
ball.rigid_body.angular_damping = 0.0
ball.rigid_body.use_deactivation = False

zs = []
for s in range(N + 1):
    sc.frame_set(s + 1)
    zs.append(Vector(ball.matrix_world.translation))

dt = 1 / HZ
g = Vector((0, 0, -G))
hits = []
for s in range(1, N - 1):
    v0 = (zs[s] - zs[s - 1]) / dt
    v1 = (zs[s + 1] - zs[s]) / dt
    dv = v1 - v0 - g * dt
    if dv.length > 0.35:
        ta, tb = (s - 1) * dt, (s + 1) * dt
        c1 = v0 - v1 + g * (tb - ta)
        c0 = zs[s - 1] - zs[s + 1] - v0 * ta + v1 * tb + 0.5 * g * (ta * ta - tb * tb)
        t = -c0.dot(c1) / c1.dot(c1)
        if hits and s - hits[-1][2] <= 3:
            continue
        hits.append((t, s * dt, s))

v1 = math.sqrt(2 * G * (Z0 - R))
t1 = v1 / G
e = E_BALL * E_FLOOR
t2 = t1 + 2 * e * v1 / G
print(f'SIM {HZ} Hz (fps {FPS} x {SUB} substeps)')
for k, (t_ref, (t, t_step, s)) in enumerate(zip((t1, t2), hits)):
    print(f'  impact {k + 1}: analytic {t_ref * 1000:8.2f} ms | step-quantised {t_step * 1000:8.2f} ms '
          f'(err {(t_step - t_ref) * 1000:+6.2f} ms) | refined {t * 1000:8.2f} ms '
          f'(err {(t - t_ref) * 1000:+6.2f} ms = {(t - t_ref) * 48000:+5.0f} samples @48k) | centre z at event {zs[s].z:.4f}')
e_eff = (hits[1][0] - hits[0][0]) * G / 2 / v1 if len(hits) > 1 else float('nan')
print(f'  effective restitution from the sim: {e_eff:.3f} (nominal product {e:.3f}) -> 2nd-impact offset is physics, not detection')
print('  min centre z after first impact', min(z.z for z in zs), '(r = 0.3: penetration check)')
