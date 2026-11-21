"""
Same drop test in pybullet, where contacts are exposed directly:
p.getContactPoints() returns per-step contact points with normalForce.
"""
import math

import pybullet as p

HZ, R, Z0, G = 600, 0.3, 5.0, 9.81
E_BALL, E_FLOOR = 0.8, 0.9
p.connect(p.DIRECT)
p.setGravity(0, 0, -G)
p.setTimeStep(1 / HZ)
p.setPhysicsEngineParameter(numSubSteps=0, numSolverIterations=20)
floor = p.createMultiBody(0, p.createCollisionShape(p.GEOM_BOX, halfExtents=[2, 2, 0.5]),
                          basePosition=[0, 0, -0.5])
ball = p.createMultiBody(0.1, p.createCollisionShape(p.GEOM_SPHERE, radius=R), basePosition=[0, 0, Z0])
p.changeDynamics(floor, -1, restitution=E_FLOOR)
p.changeDynamics(ball, -1, restitution=E_BALL, linearDamping=0, angularDamping=0)

events, in_contact = [], False
for s in range(int(2.5 * HZ)):
    p.stepSimulation()
    cps = p.getContactPoints(ball, floor)
    force = sum(c[9] for c in cps)          # normalForce (N) summed over points
    if cps and not in_contact and force > 0:
        impulse = force / HZ
        events.append(((s + 1) / HZ, impulse, cps[0][5]))
    in_contact = bool(cps)

v1 = math.sqrt(2 * G * (Z0 - R)); t1 = v1 / G
e = E_BALL * E_FLOOR   # bullet combines restitution by multiplication
t2 = t1 + 2 * e * v1 / G
for k, (tr, (t, imp, pos)) in enumerate(zip((t1, t2), events)):
    print(f'pybullet impact {k + 1}: analytic {tr * 1000:.2f} ms, contact step {t * 1000:.2f} ms '
          f'(err {(t - tr) * 1000:+.2f} ms), impulse {imp:.4f} N s, contact at {tuple(round(c, 3) for c in pos)}')
print('pybullet version API', p.getAPIVersion())
