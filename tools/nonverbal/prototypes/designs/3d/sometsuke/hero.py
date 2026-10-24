import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from base import *
a = setup(); stage(); J = pose()   # J: joint positions, hero at origin, 3/4 to camera

# SOMETSUKE - blue-and-white porcelain gourd. The hero is built in hero-local coords (facing -y, hero's left = +x)
# under a root empty turned like pose() (-45 deg). The gourd, cork, cord and arms hang under a 'body' empty that
# leans into the stance about the bottom of the gourd; legs and feet hang under the root.
import random
import bmesh
import numpy as np
import os

sc = bpy.context.scene
COLL = sc.collection
YAW = -45.0
RINV = Matrix.Rotation(math.radians(-YAW), 3, 'Z')
P = {k: RINV @ v for k, v in J.items()}          # base pose joints back in hero-local coords
TAU = 2 * math.pi

# ------------------------------------------------------------------ tunables
LEAN = (6.5, 1.5)        # body lean (deg): forward (toward -y), sideways (toward +x positive)
FACE_AZ = -50.0           # face centre azimuth (deg, atan2(y, x) in body coords; front = -90, camera ~ -25)
KNOT_AZ = -84.0           # bow knot azimuth
ARM_Z = 0.95
ARM_AZ = {'l': -12.0, 'r': 192.0}
CORK_TILT = 9.0
CORK_TILT_DIR = Vector((-0.50, -0.86, 0.0)).normalized()  # top leans toward hero's right-front = screen left
TEX_W, TEX_H = 4096, 2048
Z0, Z1 = 0.28, 1.68       # cylindrical texture v range
GLAZE_Z = 0.3225          # foot-ring top: below = unglazed biscuit
COBALT = (0.012, 0.047, 0.275)
POOL = (0.006, 0.020, 0.160)
WHITE = (0.905, 0.880, 0.823)
SILK_RED = (0.34, 0.017, 0.014)   # spec 0.462/0.03/0.023 read as coral under AgX; deepened to read crimson
SHOJI_REFL = 160.0         # glossy-only shoji panel (long highlight across the lower bulb)

root = bpy.data.objects.new('hero_root', None)
COLL.objects.link(root)
root.rotation_euler = (0, 0, math.radians(YAW))
PIVOT = Vector((0, 0, 0.30))
LEAN_M = (Matrix.Translation(PIVOT) @ Matrix.Rotation(math.radians(LEAN[0]), 4, 'X')
          @ Matrix.Rotation(math.radians(LEAN[1]), 4, 'Y') @ Matrix.Translation(-PIVOT))
body = bpy.data.objects.new('body', None)
COLL.objects.link(body)
body.parent = root
body.matrix_basis = LEAN_M

HERO = bpy.data.collections.new('hero_recv')    # receiver set for the glossy-only shoji panel


# ------------------------------------------------------------------ geometry helpers
def mesh_obj(name, verts, faces, m, parent=None, smooth=True, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        loop_uv = []
        for f in me.polygons:
            for li in f.loop_indices:
                loop_uv.extend(uvs[me.loops[li].vertex_index])
        uvl.data.foreach_set('uv', loop_uv)
    me.validate()
    me.update()
    if smooth:
        me.shade_smooth()
    if m is not None:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.parent = parent
    if parent is not None and (parent is body or parent is root or parent.name.startswith('hero')):
        HERO.objects.link(o)
    return o


def subsurf(o, lv=2):
    md = o.modifiers.new('sub', 'SUBSURF')
    md.levels = md.render_levels = lv
    return md


def lathe(profile, segs=64):
    verts, faces, rings = [], [], []
    for r, z in profile:
        if r < 1e-7:
            rings.append([len(verts)])
            verts.append(Vector((0, 0, z)))
        else:
            idx = []
            for i in range(segs):
                t = TAU * i / segs
                idx.append(len(verts))
                verts.append(Vector((r * math.cos(t), r * math.sin(t), z)))
            rings.append(idx)
    for A, B in zip(rings[:-1], rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                faces.append((A[0], B[i], B[j]))
            elif len(B) == 1:
                faces.append((A[i], A[j], B[0]))
            else:
                faces.append((A[i], A[j], B[j], B[i]))
    return verts, faces


def catmull(pts, spacing):
    """Centripetal Catmull-Rom through 2D points; returns dense list of (r, z)."""
    P_ = [Vector(p) for p in pts]
    ext = [P_[0] * 2 - P_[1]] + P_ + [P_[-1] * 2 - P_[-2]]
    out = []
    for k in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[k - 1], ext[k], ext[k + 1], ext[k + 2]
        t0 = 0.0
        t1 = t0 + max((p1 - p0).length, 1e-6) ** 0.5
        t2 = t1 + max((p2 - p1).length, 1e-6) ** 0.5
        t3 = t2 + max((p3 - p2).length, 1e-6) ** 0.5
        n = max(2, int(math.ceil((p2 - p1).length / spacing)))
        for s in range(n):
            t = t1 + (t2 - t1) * s / n
            A1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
            A2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
            A3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
            B1 = A1 * ((t2 - t) / (t2 - t0)) + A2 * ((t - t0) / (t2 - t0))
            B2 = A2 * ((t3 - t) / (t3 - t1)) + A3 * ((t - t1) / (t3 - t1))
            out.append(tuple(B1 * ((t2 - t) / (t2 - t1)) + B2 * ((t - t1) / (t2 - t1))))
    out.append(tuple(P_[-1]))
    return out


def frame_from(z_axis, y_hint=Vector((0, 0, 1))):
    z = z_axis.normalized()
    if abs(z.dot(y_hint.normalized())) > 0.98:
        y_hint = Vector((0, 1, 0))
    x = y_hint.cross(z).normalized()
    y = z.cross(x).normalized()
    M = Matrix((x, y, z)).transposed()
    return M


def place(o, loc, R3=None, scale=None):
    M = Matrix.Translation(Vector(loc))
    if R3 is not None:
        M = M @ R3.to_4x4()
    if scale is not None:
        M = M @ Matrix.Diagonal((*scale, 1.0))
    o.matrix_basis = M
    return o


def uvsphere(name, r, m, parent, loc, R3=None, scale=None, seg=48, rings=24):
    bm = bmesh.new()
    bm.loops.layers.uv.new('UVMap')
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r, calc_uvs=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.parent = parent
    HERO.objects.link(o)
    return place(o, loc, R3, scale)


def capsule_profile(r0, r1, L, n=8):
    pr = [(0.0, -r0)]
    for k in range(1, n):
        a_ = -math.pi / 2 + (math.pi / 2) * k / n
        pr.append((r0 * math.cos(a_), r0 * math.sin(a_)))
    pr.append((r0, 0.0))
    for k in range(1, 6):
        t = k / 6
        pr.append((r0 + (r1 - r0) * t, L * t))
    pr.append((r1, L))
    for k in range(1, n):
        a_ = (math.pi / 2) * k / n
        pr.append((r1 * math.cos(a_), L + r1 * math.sin(a_)))
    pr.append((0.0, L + r1))
    return pr


def capsule(name, p0, p1, r0, r1, m, parent):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    vv, ff = lathe(capsule_profile(r0, r1, d.length), segs=40)
    o = mesh_obj(name, vv, ff, m, parent)
    o.matrix_basis = Matrix.Translation(p0) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    subsurf(o, 1)
    return o


def tube(name, pts, radii, m, parent, nv=16, cap_end=True, cap_start=True, ragged=0.0, seed=1):
    """Sweep a circle along a 3D polyline. UV: u = metres along, v = 0..1 around."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    verts, faces, uvs = [], [], []
    acc = [0.0]
    for k in range(1, n):
        acc.append(acc[-1] + (pts[k] - pts[k - 1]).length)
    prev_x = None
    rng = random.Random(seed)
    for k, p in enumerate(pts):
        tg = (pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]).normalized()
        if prev_x is None:
            hint = Vector((0, 0, 1)) if abs(tg.z) < 0.9 else Vector((1, 0, 0))
            x = hint.cross(tg).normalized()
        else:
            x = (prev_x - tg * prev_x.dot(tg)).normalized()
        prev_x = x
        y = tg.cross(x)
        for j in range(nv):
            a_ = TAU * j / nv
            rr = radii[k]
            dz = 0.0
            if ragged and k == n - 1:
                dz = rng.uniform(-ragged, ragged)
            verts.append(p + (x * math.cos(a_) + y * math.sin(a_)) * rr + tg * dz)
            uvs.append((acc[k], j / nv))
    for k in range(n - 1):
        for j in range(nv):
            j1 = (j + 1) % nv
            faces.append((k * nv + j, k * nv + j1, (k + 1) * nv + j1, (k + 1) * nv + j))
    if cap_start:
        c = len(verts)
        verts.append(pts[0] - (pts[1] - pts[0]).normalized() * radii[0] * 0.6)
        uvs.append((0.0, 0.5))
        for j in range(nv):
            faces.append((c, (j + 1) % nv, j))
    if cap_end:
        c = len(verts)
        verts.append(pts[-1] + (pts[-1] - pts[-2]).normalized() * radii[-1] * 0.15)
        uvs.append((acc[-1], 0.5))
        b = (n - 1) * nv
        for j in range(nv):
            faces.append((b + j, b + (j + 1) % nv, c))
    return mesh_obj(name, verts, faces, m, parent, uvs=uvs)


def torus_mesh(name, R, r, m, parent, nU=128, nV=14, R2=None, flat=1.0):
    """Torus in its local XY plane. R2: second major radius (ellipse). UV u = metres along the cord."""
    R2 = R if R2 is None else R2
    verts, faces, uvs = [], [], []
    pts = [Vector((R * math.cos(TAU * i / nU), R2 * math.sin(TAU * i / nU), 0)) for i in range(nU)]
    acc = [0.0]
    for i in range(1, nU + 1):
        acc.append(acc[-1] + (pts[i % nU] - pts[i - 1]).length)
    for i in range(nU):
        tg = (pts[(i + 1) % nU] - pts[i - 1]).normalized()
        out = Vector((tg.y, -tg.x, 0))
        for j in range(nV):
            v = TAU * j / nV
            verts.append(pts[i] + out * (r * math.cos(v)) + Vector((0, 0, r * flat * math.sin(v))))
            uvs.append((acc[i], j / nV))
    for i in range(nU):
        for j in range(nV):
            i1, j1 = (i + 1) % nU, (j + 1) % nV
            faces.append((i * nV + j, i * nV + j1, i1 * nV + j1, i1 * nV + j))
    return mesh_obj(name, verts, faces, m, parent, uvs=uvs)


# ------------------------------------------------------------------ shader helpers
def nd(nt, kind, **inp):
    n = nt.nodes.new(kind)
    for k, v in inp.items():
        if k.startswith('_'):
            setattr(n, k[1:], v)
        else:
            n.inputs[k].default_value = v
    return n


def M(nt, op, a, b=None, c=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, x in enumerate((a, b, c)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def mixc(nt, fac, A, B):
    n = nt.nodes.new('ShaderNodeMixRGB')
    for sock, x in ((n.inputs['Fac'], fac), (n.inputs['Color1'], A), (n.inputs['Color2'], B)):
        if isinstance(x, (int, float)):
            sock.default_value = x
        elif isinstance(x, tuple):
            sock.default_value = (*x[:3], 1)
        else:
            nt.links.new(x, sock)
    return n.outputs['Color']


def smooth(nt, x, e0, e1):
    n = nt.nodes.new('ShaderNodeMapRange')
    n.interpolation_type = 'SMOOTHSTEP'
    nt.links.new(x, n.inputs['Value'])
    n.inputs['From Min'].default_value = e0
    n.inputs['From Max'].default_value = e1
    return n.outputs['Result']


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes['Principled BSDF'], nt.nodes['Material Output']


def link(nt, a_, b_):
    nt.links.new(a_, b_)


# ------------------------------------------------------------------ gourd profile
GOURD_KEYS = [
    (0.0, 0.3145), (0.08, 0.314), (0.14, 0.3115), (0.168, 0.307), (0.177, 0.3025), (0.184, 0.3003),
    (0.192, 0.3000), (0.1975, 0.3015), (0.2003, 0.3055), (0.2010, 0.3125), (0.2022, 0.3190), (0.2060, 0.3228),
    (0.2160, 0.3275), (0.2450, 0.3395), (0.2850, 0.3630), (0.3220, 0.3990), (0.3510, 0.4460), (0.3725, 0.5050),
    (0.3880, 0.5700), (0.3972, 0.6400), (0.4000, 0.7200), (0.3968, 0.8000), (0.3840, 0.8620), (0.3600, 0.9160),
    (0.3250, 0.9650), (0.2800, 1.0100), (0.2330, 1.0490), (0.1960, 1.0820), (0.1730, 1.1050), (0.1650, 1.1200),
    (0.1680, 1.1350), (0.1790, 1.1550), (0.1990, 1.1800), (0.2240, 1.2150), (0.2430, 1.2600), (0.2525, 1.3100),
    (0.2550, 1.3600), (0.2500, 1.4050), (0.2340, 1.4480), (0.2050, 1.4880), (0.1650, 1.5200), (0.1200, 1.5430),
    (0.0880, 1.5560), (0.0740, 1.5670), (0.0700, 1.5800), (0.0700, 1.6000), (0.0728, 1.6100), (0.0772, 1.6180),
    (0.0782, 1.6260), (0.0760, 1.6335), (0.0715, 1.6362), (0.0668, 1.6345), (0.0655, 1.6270), (0.0655, 1.6000),
    (0.0640, 1.5850), (0.0, 1.5830),
]
LIP_Z = 1.6362
OUTER0, OUTER1 = 6, 50            # indices of the outer, z-monotonic part of the profile
mesh_prof = catmull(GOURD_KEYS, 0.010)
fine = catmull(GOURD_KEYS[OUTER0:OUTER1 + 1], 0.0015)
PR = np.array([p[0] for p in fine])
PZ = np.maximum.accumulate(np.array([p[1] for p in fine]))
PZ = PZ + np.arange(len(PZ)) * 1e-9
PT = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(PR), np.diff(PZ)))])


def r_at(z):
    return float(np.interp(z, PZ, PR))


def t_at(z):
    return float(np.interp(z, PZ, PT))


def z_at_t(t):
    return float(np.interp(t, PT, PZ))


def surf(az_deg, z, off=0.0):
    """Point on the gourd surface (body coords) at azimuth / height, pushed out along the normal by off."""
    th = math.radians(az_deg)
    e = 0.002
    dr = (r_at(z + e) - r_at(z - e)) / (2 * e)
    nr, nz = 1.0, -dr
    ln = math.hypot(nr, nz)
    nr, nz = nr / ln, nz / ln
    rr = r_at(z) + nr * off
    return (Vector((rr * math.cos(th), rr * math.sin(th), z + nz * off)),
            Vector((nr * math.cos(th), nr * math.sin(th), nz)))


# ------------------------------------------------------------------ painted cobalt textures (numpy)
import time as _time
_t0 = _time.time()
rs = np.random.RandomState(7)


def vnoise(h, w, gh, gw, seed, wrap=True):
    r_ = np.random.RandomState(seed)
    g = r_.rand(gh + 1, gw + (0 if wrap else 1)).astype(np.float32)
    ys = (np.arange(h) + 0.5) / h * gh
    xs = (np.arange(w) + 0.5) / w * gw
    iy = np.minimum(ys.astype(int), gh - 1)
    ix = xs.astype(int)
    fy = ys - iy
    fx = xs - ix
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    gw_ = g.shape[1]
    ix1 = (ix + 1) % gw_ if wrap else np.minimum(ix + 1, gw_ - 1)
    ix = ix % gw_
    a0 = g[iy][:, ix] * (1 - fx) + g[iy][:, ix1] * fx
    a1 = g[iy + 1][:, ix] * (1 - fx) + g[iy + 1][:, ix1] * fx
    return (a0 * (1 - fy[:, None]) + a1 * fy[:, None]).astype(np.float32)


def fbm(h, w, gh, gw, seed, oct_=4, wrap=True):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(oct_):
        out += amp * vnoise(h, w, gh * 2 ** o, gw * 2 ** o, seed + o * 31, wrap)
        tot += amp
        amp *= 0.5
    return out / tot


def blur1(x, wrap=True):
    def sh(a_, dy, dx):
        b_ = np.roll(a_, dx, axis=1)
        if dy:
            b_ = np.roll(b_, dy, axis=0)
        return b_
    y = (4 * x + 2 * (sh(x, 1, 0) + sh(x, -1, 0) + sh(x, 0, 1) + sh(x, 0, -1))
         + sh(x, 1, 1) + sh(x, 1, -1) + sh(x, -1, 1) + sh(x, -1, -1)) / 16.0
    return y


def aa_line(dist, half_w, px):
    return np.clip((half_w - dist) / px + 0.5, 0.0, 1.0)


TH = (np.arange(TEX_W) + 0.5) / TEX_W * TAU - math.pi           # theta per column
ZZ = Z0 + (np.arange(TEX_H) + 0.5) / TEX_H * (Z1 - Z0)           # z per row
RZ = np.interp(ZZ, PZ, PR)
TZ = np.interp(ZZ, PZ, PT)
DTDZ = np.gradient(TZ, ZZ)
PX = np.maximum(TAU * RZ / TEX_W, DTDZ * (Z1 - Z0) / TEX_H)      # metres per texel (worst axis), per row

ink = np.zeros((TEX_H, TEX_W), np.float32)      # coverage
wash = np.zeros((TEX_H, TEX_W), np.float32)     # pale wash (dami)
nW = fbm(TEX_H, TEX_W, 8, 64, 11)               # brush width variation
nD = fbm(TEX_H, TEX_W, 16, 128, 23)             # ink density / pooling


def rows_between(z_lo, z_hi):
    j0 = max(0, int((z_lo - Z0) / (Z1 - Z0) * TEX_H) - 2)
    j1 = min(TEX_H, int((z_hi - Z0) / (Z1 - Z0) * TEX_H) + 3)
    return j0, j1


# (1) seigaiha band from the foot-ring to z 0.50 -- constant scale count per row so the rows interlock,
# scales shrink toward the foot like a potter would paint them.
N_SCALE = 20
SEI_W = 0.0066
SEI_WASH = 0.34
SEI_TOP = 0.50
j0, j1 = rows_between(GLAZE_Z - 0.01, SEI_TOP + 0.01)
tb = TZ[j0:j1, None]
rb = RZ[j0:j1, None]
pxb = PX[j0:j1, None]
TH2 = TH[None, :]
D = np.full((j1 - j0, TEX_W), np.inf, np.float32)
RV = np.ones((j1 - j0, TEX_W), np.float32)
row_t = []
t_cur = t_at(SEI_TOP) - (r_at(SEI_TOP) * math.pi / N_SCALE)
k = 0
while t_cur > t_at(GLAZE_Z) - 0.06:
    zr = z_at_t(t_cur)
    Rr = r_at(zr) * math.pi / N_SCALE
    row_t.append((t_cur, Rr, k % 2))
    t_cur -= Rr * 0.5
    k += 1
for (tr, Rr, odd) in row_t:                       # top row first; lower rows are painted over it
    step = TAU / N_SCALE
    off = 0.5 * odd
    a_ = (TH2 + math.pi) / step - off
    thc = (np.round(a_) + off) * step - math.pi
    dth = (TH2 - thc + math.pi) % TAU - math.pi
    dx = dth * rb
    dy = tb - tr
    d = np.sqrt(dx * dx + dy * dy).astype(np.float32)
    inside = d < Rr
    D[inside] = d[inside]
    RV[inside] = Rr
sei = np.zeros_like(D)
wv = SEI_W * (0.8 + 0.4 * nW[j0:j1])
for kk in range(1, 5):
    rk = RV * (kk / 4.0) - wv * 0.5
    sei = np.maximum(sei, aa_line(np.abs(D - rk), wv * 0.5 * (0.8 + 0.2 * kk / 4), pxb))
dn = D / RV
sw = np.clip((dn - 0.5) / 0.02, 0, 1) * np.clip((0.75 - dn) / 0.02, 0, 1) * SEI_WASH
sw = np.maximum(sw, np.clip((0.25 - dn) / 0.02, 0, 1) * SEI_WASH * 0.8)
fin = np.isfinite(D) & (TZ[j0:j1, None] <= t_at(SEI_TOP) + 0.001)
sei[~fin] = 0
sw[~fin] = 0
ink[j0:j1] = np.maximum(ink[j0:j1], sei)
wash[j0:j1] = np.maximum(wash[j0:j1], sw)


def ring(z_c, width, wobble=0.0006, seed=0):
    j0_, j1_ = rows_between(z_c - 0.02, z_c + 0.02)
    wob = (vnoise(1, TEX_W, 1, 12, 500 + seed)[0] - 0.5) * 2 * wobble
    tc = t_at(z_c) + wob[None, :]
    wvar = width * (0.85 + 0.3 * nW[j0_:j1_])
    dist = np.abs(TZ[j0_:j1_, None] - tc)
    ink[j0_:j1_] = np.maximum(ink[j0_:j1_], aa_line(dist, wvar * 0.5, PX[j0_:j1_, None]))


ring(GLAZE_Z + 0.009, 0.0045, seed=1)            # thin line where the seigaiha meets the foot
ring(0.528, 0.0085, seed=2)                        # (2) the two band rings
ring(0.552, 0.0085, seed=3)
_j0, _j1 = rows_between(0.52, 0.56)                 # pale wash between the two band rings
_tt = TZ[_j0:_j1, None]
wash[_j0:_j1] = np.maximum(wash[_j0:_j1], (np.clip((_tt - t_at(0.528)) / 0.001, 0, 1)
                                           * np.clip((t_at(0.552) - _tt) / 0.001, 0, 1) * 0.30) * np.ones((1, TEX_W)))
ring(1.093, 0.0050, seed=4)                       # (4) rings just below / above the waist cord
ring(1.150, 0.0050, seed=5)

# (3) nine sparse five-petal plum blossoms on the upper half of the lower bulb, away from the arms / tassel
PLUMS = [(-112, 0.80, 10), (-60, 0.775, 40), (-46, 0.905, 5), (-82, 0.905, 62), (25, 0.84, 18), (56, 0.765, 33),
         (92, 0.885, 50), (128, 0.79, 12), (158, 0.895, 27)]
for (azd, zc, rot) in PLUMS:
    R_PL = 0.042
    rp = 0.0175
    dc = R_PL - rp
    j0_, j1_ = rows_between(zc - 0.06, zc + 0.06)
    th0 = math.radians(azd)
    dth = (TH[None, :] - th0 + math.pi) % TAU - math.pi
    X = dth * RZ[j0_:j1_, None]
    Y = TZ[j0_:j1_, None] - t_at(zc)
    sel = np.abs(X) < 0.06
    sdf = np.full(X.shape, 9.0, np.float32)
    for p in range(5):
        aa = math.radians(rot + 90 + 72 * p)
        cx, cy = dc * math.cos(aa), dc * math.sin(aa)
        sdf = np.minimum(sdf, np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - rp)
    pxp = PX[j0_:j1_, None]
    wpl = 0.0046 * (0.8 + 0.4 * nW[j0_:j1_])
    outline = aa_line(np.abs(sdf), wpl * 0.5, pxp)
    rr_ = np.sqrt(X * X + Y * Y)
    centre = aa_line(rr_, 0.0058, pxp)
    stamen = np.zeros_like(rr_)
    for p in range(5):
        aa = math.radians(rot + 90 + 36 + 72 * p)
        sx_, sy_ = 0.0115 * math.cos(aa), 0.0115 * math.sin(aa)
        stamen = np.maximum(stamen, aa_line(np.sqrt((X - sx_) ** 2 + (Y - sy_) ** 2), 0.0026, pxp))
    petal_in = np.clip(-sdf / pxp + 0.5, 0, 1)
    blk = np.maximum(np.maximum(outline, centre), stamen) * sel
    ink[j0_:j1_] = np.maximum(ink[j0_:j1_], blk)
    wash[j0_:j1_] = np.maximum(wash[j0_:j1_], petal_in * sel * 0.30)

# hand-painted feel: 1 px blur, a faint bleed halo, noise-darkened pooling
ink = blur1(ink)
halo = blur1(blur1(blur1(ink)))
cov = 1.0 - (1.0 - ink) * (1.0 - 0.16 * halo) * (1.0 - blur1(wash))
pool = 0.35 + np.clip((nD - 0.48) * 3.0, 0, 1) * 0.5 + 0.15 * ink * ink
pool = np.clip(pool * ink, 0, 1)
img_arr = np.zeros((TEX_H, TEX_W, 4), np.float32)
img_arr[..., 0] = np.clip(cov, 0, 1) * (0.98 + 0.22 * nD) * (1.0 + 0.12 * ink)
img_arr[..., 1] = pool
img_arr[..., 3] = 1.0
PAT = bpy.data.images.new('sometsuke_pattern', TEX_W, TEX_H, alpha=True, float_buffer=True)
PAT.colorspace_settings.name = 'Non-Color'
PAT.pixels.foreach_set(img_arr.ravel())
PAT.update()
del img_arr, D, RV, sei, halo

# face: two half-closed sleepy eyes, painted in a separate hi-res window around the face
FW, FH = 1024, 512
F_TH0, F_DTH = math.radians(FACE_AZ - 32), math.radians(64)
F_Z0, F_DZ = 1.27, 0.16
FACE_Z = 1.345
fth = F_TH0 + (np.arange(FW) + 0.5) / FW * F_DTH
fz = F_Z0 + (np.arange(FH) + 0.5) / FH * F_DZ
frz = np.interp(fz, PZ, PR)
ftz = np.interp(fz, PZ, PT)
FX = (fth[None, :] - math.radians(FACE_AZ)) * frz[:, None]
FY = (ftz - t_at(FACE_Z))[:, None] * np.ones((1, FW))
fpx = max(F_DTH * 0.255 / FW, F_DZ / FH)
face = np.zeros((FH, FW), np.float32)
fpool = np.zeros((FH, FW), np.float32)
for side, ex in ((-1, -0.080), (1, 0.080)):
    lx = (FX - ex) / 0.0520                       # -1..1 across the lid
    sag = 0.0085
    ylid = sag * (1 - np.clip(lx, -1.2, 1.2) ** 2)
    # brush: pressed in at the outer end, lifted to a point at the inner end
    press = np.clip(1 - np.abs(lx) ** 3, 0, 1) ** 0.6 * (1.0 + 0.18 * side * lx)
    half = 0.0072 * press
    dist_lid = np.abs(FY - ylid)
    lid = aa_line(dist_lid, half, fpx) * (np.abs(lx) < 1.05)
    # pupil: disc r 0.022 hung under the lid, clipped by the lid curve
    pr = np.sqrt((FX - ex - side * 0.002) ** 2 + (FY - (sag - 0.0050)) ** 2)
    pup = aa_line(pr, 0.034, fpx) * np.clip((ylid - FY) / fpx + 0.5, 0, 1)
    face = np.maximum(face, np.maximum(lid, pup))
    fpool = np.maximum(fpool, 0.45 + pup * np.clip(1 - pr / 0.034, 0, 1) * 0.3 + lid * 0.3 * press)
nf = fbm(FH, FW, 8, 16, 77, wrap=False)
face = blur1(face, wrap=False)
fcov = 1 - (1 - face) * (1 - 0.14 * blur1(blur1(face)))
f_arr = np.zeros((FH, FW, 4), np.float32)
f_arr[..., 0] = np.clip(fcov, 0, 1) * 1.35
f_arr[..., 1] = np.clip(fpool * face + (nf - 0.5) * 0.3 * face, 0, 1)
f_arr[..., 3] = 1.0
FACE_IMG = bpy.data.images.new('sometsuke_face', FW, FH, alpha=True, float_buffer=True)
FACE_IMG.colorspace_settings.name = 'Non-Color'
FACE_IMG.pixels.foreach_set(f_arr.ravel())
FACE_IMG.update()
print('textures', round(_time.time() - _t0, 1), 's')


# ------------------------------------------------------------------ materials
def glaze_core(nt, bsdf, base_col_socket):
    link(nt, base_col_socket, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.30
    bsdf.inputs['Specular IOR Level'].default_value = 0.25    # keep the under-glaze sheen from milking the cobalt
    bsdf.inputs['Coat Weight'].default_value = 1.0
    bsdf.inputs['Coat Roughness'].default_value = 0.025
    bsdf.inputs['Coat IOR'].default_value = 1.52
    bsdf.inputs['Subsurface Weight'].default_value = 0.12
    bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.8, 0.6)
    bsdf.inputs['Subsurface Scale'].default_value = 0.006
    tc = nt.nodes.get('tc') or nd(nt, 'ShaderNodeTexCoord', _name='tc')
    nz = nd(nt, 'ShaderNodeTexNoise', Scale=6.0, Detail=3.0, Roughness=0.5)
    link(nt, tc.outputs['Object'], nz.inputs['Vector'])
    nz2 = nd(nt, 'ShaderNodeTexNoise', Scale=90.0, Detail=2.0)
    link(nt, tc.outputs['Object'], nz2.inputs['Vector'])
    h = M(nt, 'MULTIPLY_ADD', nz2.outputs['Fac'], 0.06, nz.outputs['Fac'])
    bump = nd(nt, 'ShaderNodeBump', Strength=0.35, Distance=0.01)
    link(nt, h, bump.inputs['Height'])
    link(nt, bump.outputs['Normal'], bsdf.inputs['Coat Normal'])


def white_var(nt, tc):
    n = nd(nt, 'ShaderNodeTexNoise', Scale=3.0, Detail=2.0)
    link(nt, tc.outputs['Object'], n.inputs['Vector'])
    w = mixc(nt, smooth(nt, n.outputs['Fac'], 0.35, 0.75), WHITE, (0.885, 0.875, 0.835))
    ao = nd(nt, 'ShaderNodeAmbientOcclusion', Distance=0.06, _samples=8)
    return mixc(nt, M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', 1.0, ao.outputs['AO']), 0.55), w, (0.74, 0.80, 0.80))


A_COB = [-math.log(c / w) for c, w in zip(COBALT, WHITE)]     # cobalt absorbance per channel (Beer-Lambert:
A_POOL = [-math.log(c / w) for c, w in zip(POOL, WHITE)]      # pigment under glaze filters the white body)


def ink_mix(nt, white, cov, pool):
    """white * exp(-cov * A), A = mix(cobalt, pooled cobalt): a thin wash reads as clear blue, not grey."""
    sc_ = nd(nt, 'ShaderNodeSeparateColor')
    link(nt, white, sc_.inputs['Color'])
    cc = nd(nt, 'ShaderNodeCombineColor')
    for i, ch in enumerate(('Red', 'Green', 'Blue')):
        A = M(nt, 'MULTIPLY_ADD', pool, A_POOL[i] - A_COB[i], A_COB[i]) if not isinstance(pool, (int, float)) \
            else A_COB[i] + (A_POOL[i] - A_COB[i]) * pool
        dens = M(nt, 'MULTIPLY', cov, A) if not isinstance(A, float) else M(nt, 'MULTIPLY', cov, A)
        t = M(nt, 'EXPONENT', M(nt, 'MULTIPLY', dens, -1.0))
        link(nt, M(nt, 'MULTIPLY', sc_.outputs[ch], t), cc.inputs[ch])
    return cc.outputs['Color']


def biscuit_bsdf(nt, tc, glaze_dist=None):
    b = nd(nt, 'ShaderNodeBsdfPrincipled')
    n = nd(nt, 'ShaderNodeTexNoise', Scale=260.0, Detail=4.0)
    link(nt, tc.outputs['Object'], n.inputs['Vector'])
    col = mixc(nt, smooth(nt, n.outputs['Fac'], 0.3, 0.7), (0.56, 0.49, 0.40), (0.66, 0.59, 0.49))
    if glaze_dist is not None:   # faint fire-blush on the biscuit next to the glaze line
        col = mixc(nt, glaze_dist, col, (0.70, 0.44, 0.26))
    link(nt, col, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85
    bump = nd(nt, 'ShaderNodeBump', Strength=0.25, Distance=0.002)
    link(nt, n.outputs['Fac'], bump.inputs['Height'])
    link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    return b


def gourd_mat():
    m, nt, bsdf, out = new_mat('porcelain_gourd')
    tc = nd(nt, 'ShaderNodeTexCoord', _name='tc')
    sep = nd(nt, 'ShaderNodeSeparateXYZ')
    link(nt, tc.outputs['Object'], sep.inputs['Vector'])
    th = M(nt, 'ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
    u = M(nt, 'MULTIPLY_ADD', th, 1.0 / TAU, 0.5)
    v = M(nt, 'MULTIPLY_ADD', sep.outputs['Z'], 1.0 / (Z1 - Z0), -Z0 / (Z1 - Z0))
    cmb = nd(nt, 'ShaderNodeCombineXYZ')
    link(nt, u, cmb.inputs['X'])
    link(nt, v, cmb.inputs['Y'])
    tex = nd(nt, 'ShaderNodeTexImage', _interpolation='Linear', _extension='REPEAT')
    tex.image = PAT
    link(nt, cmb.outputs['Vector'], tex.inputs['Vector'])
    uf = M(nt, 'MULTIPLY_ADD', th, 1.0 / F_DTH, -F_TH0 / F_DTH)
    vf = M(nt, 'MULTIPLY_ADD', sep.outputs['Z'], 1.0 / F_DZ, -F_Z0 / F_DZ)
    cmbf = nd(nt, 'ShaderNodeCombineXYZ')
    link(nt, uf, cmbf.inputs['X'])
    link(nt, vf, cmbf.inputs['Y'])
    texf = nd(nt, 'ShaderNodeTexImage', _interpolation='Linear', _extension='CLIP')
    texf.image = FACE_IMG
    link(nt, cmbf.outputs['Vector'], texf.inputs['Vector'])
    s1 = nd(nt, 'ShaderNodeSeparateColor')
    s2 = nd(nt, 'ShaderNodeSeparateColor')
    link(nt, tex.outputs['Color'], s1.inputs['Color'])
    link(nt, texf.outputs['Color'], s2.inputs['Color'])
    cov = M(nt, 'ADD', s1.outputs['Red'], s2.outputs['Red'], clamp=True)
    pool = M(nt, 'ADD', s1.outputs['Green'], s2.outputs['Green'], clamp=True)
    base = ink_mix(nt, white_var(nt, tc), cov, pool)
    glaze_core(nt, bsdf, base)
    # glaze line at the foot: below -> unglazed biscuit with a faint blush
    gl = smooth(nt, sep.outputs['Z'], GLAZE_Z - 0.0012, GLAZE_Z + 0.0008)
    blush = M(nt, 'SUBTRACT', 1.0, smooth(nt, sep.outputs['Z'], GLAZE_Z - 0.007, GLAZE_Z))
    blush = M(nt, 'SUBTRACT', 1.0, blush)
    bis = biscuit_bsdf(nt, tc, M(nt, 'MULTIPLY', blush, 0.55))
    mix = nd(nt, 'ShaderNodeMixShader')
    link(nt, gl, mix.inputs['Fac'])
    link(nt, bis.outputs['BSDF'], mix.inputs[1])
    link(nt, bsdf.outputs['BSDF'], mix.inputs[2])
    link(nt, mix.outputs['Shader'], out.inputs['Surface'])
    return m


def limb_mat(name, ring_at=None, ring_w=0.007, sole_below=None, ring_uv=False):
    m, nt, bsdf, out = new_mat(name)
    tc = nd(nt, 'ShaderNodeTexCoord', _name='tc')
    sep = nd(nt, 'ShaderNodeSeparateXYZ')
    link(nt, tc.outputs['Object'], sep.inputs['Vector'])
    white = white_var(nt, tc)
    if ring_at is not None:
        if ring_uv:
            uvn = nd(nt, 'ShaderNodeUVMap', _uv_map='UVMap')
            su = nd(nt, 'ShaderNodeSeparateXYZ')
            link(nt, uvn.outputs['UV'], su.inputs['Vector'])
            coord = su.outputs['X']
        else:
            coord = sep.outputs['Z']
        d = M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', coord, ring_at))
        cov = M(nt, 'SUBTRACT', 1.0, smooth(nt, d, ring_w * 0.5 - 0.0006, ring_w * 0.5 + 0.0006))
        base = ink_mix(nt, white, cov, 0.5)
    else:
        base = white
    glaze_core(nt, bsdf, base)
    if sole_below is not None:
        gl = smooth(nt, sep.outputs['Z'], sole_below - 0.001, sole_below + 0.001)
        bis = biscuit_bsdf(nt, tc)
        mix = nd(nt, 'ShaderNodeMixShader')
        link(nt, gl, mix.inputs['Fac'])
        link(nt, bis.outputs['BSDF'], mix.inputs[1])
        link(nt, bsdf.outputs['BSDF'], mix.inputs[2])
        link(nt, mix.outputs['Shader'], out.inputs['Surface'])
    return m


def cork_mat():
    m, nt, b, out = new_mat('cork')
    tc = nd(nt, 'ShaderNodeTexCoord')
    vo = nd(nt, 'ShaderNodeTexVoronoi', Scale=60.0, Randomness=1.0)
    link(nt, tc.outputs['Object'], vo.inputs['Vector'])
    pit = M(nt, 'SUBTRACT', 1.0, smooth(nt, vo.outputs['Distance'], 0.06, 0.20))
    gr = nd(nt, 'ShaderNodeTexNoise', Scale=420.0, Detail=6.0, Roughness=0.7)
    link(nt, tc.outputs['Object'], gr.inputs['Vector'])
    sp = nd(nt, 'ShaderNodeTexNoise', Scale=140.0, Detail=3.0)
    link(nt, tc.outputs['Object'], sp.inputs['Vector'])
    big = nd(nt, 'ShaderNodeTexNoise', Scale=18.0, Detail=3.0)
    link(nt, tc.outputs['Object'], big.inputs['Vector'])
    col = mixc(nt, smooth(nt, big.outputs['Fac'], 0.3, 0.7), (0.36, 0.205, 0.085), (0.48, 0.29, 0.125))
    col = mixc(nt, smooth(nt, gr.outputs['Fac'], 0.35, 0.7), col, (0.52, 0.33, 0.15))
    col = mixc(nt, M(nt, 'MULTIPLY', smooth(nt, sp.outputs['Fac'], 0.62, 0.70), 0.8), col, (0.16, 0.08, 0.03))
    col = mixc(nt, M(nt, 'MULTIPLY', pit, 0.85), col, (0.12, 0.06, 0.025))
    link(nt, col, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.85
    h = M(nt, 'MULTIPLY_ADD', pit, -1.0, M(nt, 'MULTIPLY', gr.outputs['Fac'], 0.35))
    bump = nd(nt, 'ShaderNodeBump', Strength=0.3, Distance=0.004)
    link(nt, h, bump.inputs['Height'])
    link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    return m


def silk_mat(name, strands=0):
    m, nt, b, out = new_mat(name)
    b.inputs['Base Color'].default_value = (*SILK_RED, 1)
    b.inputs['Roughness'].default_value = 0.40
    b.inputs['Sheen Weight'].default_value = 0.5
    b.inputs['Sheen Tint'].default_value = (0.62, 0.10, 0.08, 1)
    b.inputs['Specular IOR Level'].default_value = 0.22
    b.inputs['Anisotropic'].default_value = 0.5
    uv = nd(nt, 'ShaderNodeUVMap', _uv_map='UVMap')
    sp = nd(nt, 'ShaderNodeSeparateXYZ')
    link(nt, uv.outputs['UV'], sp.inputs['Vector'])
    if strands:     # tassel skirt: fine strands along the length
        ph = M(nt, 'MULTIPLY', sp.outputs['Y'], strands)
        jit = nd(nt, 'ShaderNodeTexNoise', Scale=4.0, Detail=2.0)
        link(nt, uv.outputs['UV'], jit.inputs['Vector'])
        ph = M(nt, 'MULTIPLY_ADD', jit.outputs['Fac'], 1.6, ph)
    else:           # 3-ply twist: helical grooves (pitch 3 cm)
        ph = M(nt, 'MULTIPLY', M(nt, 'MULTIPLY_ADD', sp.outputs['X'], 1 / 0.03, sp.outputs['Y']), 3.0)
    wave = M(nt, 'ABSOLUTE', M(nt, 'SINE', M(nt, 'MULTIPLY', ph, math.pi)))
    wave = M(nt, 'POWER', wave, 0.6)
    bump = nd(nt, 'ShaderNodeBump', Strength=0.55 if not strands else 0.4, Distance=0.002)
    link(nt, wave, bump.inputs['Height'])
    link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    tan = nd(nt, 'ShaderNodeTangent', _direction_type='UV_MAP')
    tan.uv_map = 'UVMap'
    link(nt, tan.outputs['Tangent'], b.inputs['Tangent'])
    dark = mixc(nt, M(nt, 'SUBTRACT', 1.0, wave), SILK_RED, tuple(c * 0.5 for c in SILK_RED))
    link(nt, dark, b.inputs['Base Color'])
    return m


def gold_mat():
    m, nt, b, out = new_mat('gold')
    b.inputs['Base Color'].default_value = (1.0, 0.76, 0.33, 1)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.3
    return m


GOURD = gourd_mat()
FOREARM = None   # built per arm (ring position depends on length)
UPPER = limb_mat('porcelain_limb')
FOOT = limb_mat('porcelain_foot', sole_below=-0.022)
CORK = cork_mat()
SILK = silk_mat('silk_cord')
SILK_T = silk_mat('silk_tassel', strands=70)
GOLD = gold_mat()

# ------------------------------------------------------------------ gourd body
gv, gf = lathe(mesh_prof, segs=64)
gourd = mesh_obj('gourd', gv, gf, GOURD, body)
subsurf(gourd, 2)
print('gourd rings', len(mesh_prof))

# cork stopper hat: tapered (wide end up), bevelled, sunk into the mouth, tilted
CORK_H, CORK_SINK, CR0, CR1, CB = 0.13, 0.03, 0.060, 0.085, 0.006


def cork_profile():
    z0, z1 = -CORK_SINK, CORK_H - CORK_SINK
    rr = lambda z: CR0 + (CR1 - CR0) * (z - z0) / (z1 - z0)
    pr = [(0.0, z0)]
    for k in range(0, 5):
        a_ = -math.pi / 2 + (math.pi / 2) * k / 4
        pr.append((rr(z0 + CB) - CB + CB * math.cos(a_), z0 + CB + CB * math.sin(a_)))
    for k in range(1, 6):
        z = z0 + CB + (z1 - z0 - 2 * CB) * k / 6
        pr.append((rr(z), z))
    for k in range(0, 5):
        a_ = (math.pi / 2) * k / 4
        pr.append((rr(z1 - CB) - CB + CB * math.cos(a_), z1 - CB + CB * math.sin(a_)))
    for k in range(1, 4):
        pr.append(((rr(z1) - CB) * (1 - k / 4), z1 + 0.0015 * math.sin(math.pi * k / 8)))
    pr.append((0.0, z1 + 0.0015))
    return pr


cv, cf = lathe(cork_profile(), segs=64)
cork = mesh_obj('cork', cv, cf, CORK, body)
tilt_axis = Vector((0, 0, 1)).cross(CORK_TILT_DIR).normalized()
cork.matrix_basis = Matrix.Translation((0, 0, LIP_Z)) @ Matrix.Rotation(math.radians(CORK_TILT), 4, tilt_axis)
subsurf(cork, 1)

# ------------------------------------------------------------------ red silk cord, bow knot and tassel
WAIST_Z = 1.120
cord = torus_mesh('waist_cord', 0.172, 0.011, SILK, body, nU=192, nV=14)
cord.location = (0, 0, WAIST_Z)
subsurf(cord, 1)
kp, kn = surf(KNOT_AZ, WAIST_Z, 0.0)
kp = Vector((kp.x, kp.y, WAIST_Z)) * 1.0
kdir = Vector((math.cos(math.radians(KNOT_AZ)), math.sin(math.radians(KNOT_AZ)), 0))
ktan = Vector((-kdir.y, kdir.x, 0))
kc = Vector((0, 0, WAIST_Z)) + kdir * (0.172 + 0.016)
knot = uvsphere('knot', 1.0, SILK, body, kc, frame_from(kdir, Vector((0, 0, 1))), (0.017, 0.015, 0.012))
for s in (-1, 1):
    az = KNOT_AZ + s * math.degrees(0.032 / 0.187)
    d_ = Vector((math.cos(math.radians(az)), math.sin(math.radians(az)), 0))
    t_ = Vector((-d_.y, d_.x, 0)) * s
    lc = Vector((0, 0, WAIST_Z + 0.006)) + d_ * (0.172 + 0.014)
    loop = torus_mesh('bow_loop', 0.040, 0.0085, SILK, body, nU=64, nV=10, R2=0.024)
    tilt = math.radians(14)
    xa = (t_ * math.cos(tilt) + Vector((0, 0, 1)) * math.sin(tilt)).normalized()
    za = d_
    ya = za.cross(xa).normalized()
    R3 = Matrix((xa, ya, za)).transposed()
    loop.matrix_basis = Matrix.Translation(lc) @ R3.to_4x4() @ Matrix.Diagonal((1, 1, 0.65, 1))
    subsurf(loop, 1)
# tail cord + tassel lying down the shoulder of the lower bulb
path = []
zt = WAIST_Z - 0.008
z_end_t = t_at(WAIST_Z) - 0.035
tz = t_at(zt)
while tz > z_end_t:
    p_, n_ = surf(KNOT_AZ - 3, z_at_t(tz), 0.0085)
    path.append(p_)
    tz -= 0.004
tail = tube('tassel_cord', [kc - kdir * 0.004] + path, [0.0065] * (len(path) + 1), SILK, body, nv=12)
t_head = t_at(WAIST_Z) - 0.045
hp, hn = surf(KNOT_AZ - 3, z_at_t(t_head), 0.019)
hp2, _ = surf(KNOT_AZ - 3, z_at_t(t_head - 0.004), 0.019)
head = uvsphere('tassel_head', 1.0, SILK, body, hp, frame_from(hp - hp2, hn), (0.018, 0.018, 0.020))
sk, rad = [], []
L_SK = 0.112
NS = 18
for k in range(NS + 1):
    tt = t_head - 0.012 - L_SK * k / NS
    rr = 0.020 + (0.032 - 0.020) * (k / NS) ** 0.8
    p_, n_ = surf(KNOT_AZ - 3, z_at_t(tt), rr + 0.0015)
    sk.append(p_)
    rad.append(rr)
skirt = tube('tassel_skirt', sk, rad, SILK_T, body, nv=40, ragged=0.004, seed=5)
gb0, gbn = surf(KNOT_AZ - 3, z_at_t(t_head - 0.012), 0.0205)
gb1, _ = surf(KNOT_AZ - 3, z_at_t(t_head - 0.016), 0.0205)
band = torus_mesh('gold_band', 0.0195, 0.0032, GOLD, body, nU=48, nV=10)
band.matrix_basis = Matrix.Translation(gb0) @ frame_from(gb0 - gb1, gbn).to_4x4()
print('tassel bottom z', round(sk[-1].z, 3))

# ------------------------------------------------------------------ arms (short porcelain capsules, mitten hands)
ELBOW_DEG = math.degrees((P['el_l'] - P['sh_l']).angle(P['ha_l'] - P['el_l']))
ARM_DIRS = {
    'l': (Vector((0.62, -0.76, -0.08)), Vector((-0.30, -0.30, 0.91))),
    'r': (Vector((-0.62, -0.74, -0.06)), Vector((0.30, -0.20, 0.94))),
}
ARM_L1, ARM_L2, ARM_R = 0.14, 0.16, 0.055


def arm(side):
    sp_, sn_ = surf(ARM_AZ[side], ARM_Z, -0.024)
    d1, d2 = (v.normalized() for v in ARM_DIRS[side])
    # keep the base-pose elbow bend: rotate d2 in the (d1, d2) plane to match it
    ax = d1.cross(d2).normalized()
    d2 = (Matrix.Rotation(math.radians(ELBOW_DEG), 3, ax) @ d1).normalized()
    E = sp_ + d1 * (ARM_L1 + 0.024)
    H = E + d2 * ARM_L2
    rb = 0.055
    a_, b_ = E - d1 * rb, E + d2 * rb
    pts = []
    n1 = 10
    for k in range(n1):
        pts.append(sp_.lerp(a_, k / n1))
    for k in range(12):
        t = k / 12
        pts.append(a_ * (1 - t) ** 2 + E * (2 * t * (1 - t)) + b_ * t * t)
    for k in range(9):
        pts.append(b_.lerp(H, k / 8))
    acc = [0.0]
    for k in range(1, len(pts)):
        acc.append(acc[-1] + (pts[k] - pts[k - 1]).length)
    tot = acc[-1]
    radii = [ARM_R * (1.06 - 0.14 * (x / tot)) for x in acc]
    fm = limb_mat('porcelain_arm_' + side, ring_at=tot - 0.016, ring_w=0.0085, ring_uv=True)
    o = tube('arm_' + side, pts, radii, fm, body, nv=28)
    subsurf(o, 1)
    # mitten: slightly flattened sphere with a thumb nub, palm facing in
    hc = H + d2 * 0.034
    inward = Vector((-hc.x, -hc.y - 0.15, 0)).normalized()
    R3 = frame_from(d2, inward)
    uvsphere('mitten_' + side, 0.064, UPPER, body, hc, R3, (1.0, 0.80, 1.06))
    th_ = hc + R3 @ Vector((0.0, 0.043, 0.010)) + d2 * 0.004
    uvsphere('thumb_' + side, 0.023, UPPER, body, th_, R3, (0.9, 0.85, 1.25))
    return sp_, E, H


ARMS = {s: arm(s) for s in ('l', 'r')}
print('elbow bend', round(ELBOW_DEG, 1), {k: [tuple(round(c, 3) for c in p) for p in v] for k, v in ARMS.items()})

# ------------------------------------------------------------------ legs + feet (root space)
HIP_BODY = {'l': Vector((0.095, -0.075, 0.335)), 'r': Vector((-0.095, 0.075, 0.335))}
ANKLE_XY = {'l': (0.195, -0.240), 'r': (-0.205, 0.215)}
FOOT_YAW = {'l': 10.0, 'r': -60.0}       # foot heading (deg from -y toward +x)
ANKLE_Z = 0.072
for s in ('l', 'r'):
    hp_ = LEAN_M @ HIP_BODY[s]
    A = Vector((ANKLE_XY[s][0], ANKLE_XY[s][1], ANKLE_Z))
    L = (A - hp_).length
    capsule('leg_' + s, hp_, A, 0.075, 0.060, UPPER, root)
    yaw = math.radians(FOOT_YAW[s])
    fwd = Vector((math.sin(yaw), -math.cos(yaw), 0))
    fc = Vector((A.x, A.y, 0)) + fwd * 0.045
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    for vt in bm.verts:
        x, y, z = vt.co
        z = z * 0.05
        if z < -0.026:
            z = -0.026 + (z + 0.026) * 0.25
        y = y * 0.13
        x = x * 0.075 * (1.0 - 0.12 * y / 0.13)
        vt.co = Vector((x, y, z))
    me = bpy.data.meshes.new('foot_' + s)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.materials.append(FOOT)
    fo = bpy.data.objects.new('foot_' + s, me)
    COLL.objects.link(fo)
    HERO.objects.link(fo)
    fo.parent = root
    zmin = min(v.co.z for v in me.vertices)
    fo.matrix_basis = (Matrix.Translation((fc.x, fc.y, -zmin - 0.0015))
                       @ Matrix.Rotation(math.atan2(fwd.y, fwd.x) + math.pi / 2, 4, 'Z'))
    subsurf(fo, 1)
    print('leg', s, 'L', round(L, 3), 'ankle', tuple(round(c, 3) for c in A))

# ------------------------------------------------------------------ mooks: JUGS (raw grey stoneware jug men)
def stoneware_mat():
    m, nt, b, out = new_mat('stoneware')
    tc = nd(nt, 'ShaderNodeTexCoord')
    sep = nd(nt, 'ShaderNodeSeparateXYZ')
    link(nt, tc.outputs['Object'], sep.inputs['Vector'])
    vo = nd(nt, 'ShaderNodeTexVoronoi', Scale=7.0)
    link(nt, tc.outputs['Object'], vo.inputs['Vector'])
    dimple = M(nt, 'POWER', M(nt, 'MINIMUM', vo.outputs['Distance'], 0.5), 2.0)
    wv = nd(nt, 'ShaderNodeTexWave', _wave_type='RINGS', Scale=0.0, Distortion=1.5, Detail=2.0)
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = 21.0
    link(nt, tc.outputs['Object'], wv.inputs['Vector'])
    grit = nd(nt, 'ShaderNodeTexNoise', Scale=180.0, Detail=5.0)
    link(nt, tc.outputs['Object'], grit.inputs['Vector'])
    h = M(nt, 'MULTIPLY_ADD', dimple, 0.3 / 0.25, M(nt, 'MULTIPLY', wv.outputs['Fac'], 0.1))
    h = M(nt, 'MULTIPLY_ADD', grit.outputs['Fac'], 0.08, h)
    bump = nd(nt, 'ShaderNodeBump', Strength=0.45, Distance=0.01)
    link(nt, h, bump.inputs['Height'])
    link(nt, bump.outputs['Normal'], b.inputs['Normal'])
    # kiln-ash glaze runs on the shoulders
    mp = nd(nt, 'ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (9.0, 9.0, 1.2)
    link(nt, tc.outputs['Object'], mp.inputs['Vector'])
    st = nd(nt, 'ShaderNodeTexNoise', Scale=1.0, Detail=4.0, Roughness=0.6)
    link(nt, mp.outputs['Vector'], st.inputs['Vector'])
    grad = smooth(nt, sep.outputs['Z'], 0.70, 1.02)
    ash = smooth(nt, M(nt, 'MULTIPLY_ADD', st.outputs['Fac'], 0.9, M(nt, 'MULTIPLY', grad, 0.75)), 0.78, 0.86)
    clay = mixc(nt, smooth(nt, grit.outputs['Fac'], 0.3, 0.7), (0.135, 0.125, 0.105), (0.176, 0.163, 0.138))
    col = mixc(nt, ash, clay, (0.159, 0.178, 0.080))
    link(nt, col, b.inputs['Base Color'])
    rough = M(nt, 'MULTIPLY_ADD', ash, -0.55, 0.85)
    link(nt, rough, b.inputs['Roughness'])
    return m


STONE = stoneware_mat()
JUG_PROF = [(0.0, 0.0), (0.15, 0.0), (0.18, 0.006), (0.205, 0.03), (0.245, 0.10), (0.272, 0.20), (0.280, 0.29),
            (0.272, 0.40), (0.245, 0.50), (0.200, 0.58), (0.150, 0.64), (0.108, 0.70), (0.082, 0.78), (0.066, 0.90),
            (0.060, 1.00), (0.062, 1.06), (0.072, 1.11), (0.082, 1.15), (0.080, 1.17), (0.066, 1.17), (0.054, 1.13),
            (0.050, 1.05), (0.0, 1.04)]


def mook(pos, face_to, tilt, seed):
    rng = random.Random(seed)
    m_root = bpy.data.objects.new('jug', None)
    COLL.objects.link(m_root)
    yaw = math.atan2(face_to[1] - pos[1], face_to[0] - pos[0]) + math.pi / 2
    m_root.matrix_basis = (Matrix.Translation((pos[0], pos[1], 0)) @ Matrix.Rotation(yaw, 4, 'Z')
                           @ Matrix.Rotation(math.radians(tilt), 4, 'Y'))
    prof = catmull([(r, z + 0.28) for r, z in JUG_PROF], 0.012)
    vv, ff = lathe(prof, segs=48)
    bod = mesh_obj('jug_body', vv, ff, STONE, m_root)
    subsurf(bod, 1)
    for s in (-1, 1):   # loop handles = arms
        h = torus_mesh('jug_handle', 0.12, 0.030, STONE, m_root, nU=48, nV=12)
        h.matrix_basis = (Matrix.Translation((s * 0.235, 0, 0.28 + 0.40)) @ Matrix.Rotation(math.pi / 2, 4, 'X'))
        bmh = None
        subsurf(h, 1)
        cyl = capsule('jug_leg', (s * 0.115, 0, 0.05), (s * 0.115, 0, 0.30), 0.07, 0.07, STONE, m_root)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.012, segments=3, affect='EDGES')
        me = bpy.data.meshes.new('slab')
        bm.to_mesh(me)
        bm.free()
        me.materials.append(STONE)
        sl = bpy.data.objects.new('jug_foot', me)
        COLL.objects.link(sl)
        sl.parent = m_root
        sl.matrix_basis = (Matrix.Translation((s * 0.125, -0.035, 0.024)) @ Matrix.Rotation(rng.uniform(-0.2, 0.2), 4, 'Z')
                           @ Matrix.Diagonal((0.17, 0.26, 0.048, 1)))
    return m_root


cam = sc.camera
cxy = Vector((cam.location.x, cam.location.y))
fwd_c = (Vector(CAM['tgt']).to_2d() - cxy).normalized()
right_c = Vector((fwd_c.y, -fwd_c.x))


def at_cam(depth, lateral):
    p = cxy + fwd_c * depth + right_c * lateral
    return (p.x, p.y)


FRAC = 18.0 * 9 / 16 / CAM['lens']
mook(at_cam(6.6, -0.86 * 6.6 * FRAC), (0.0, 0.0), -5.0, 3)
mook(at_cam(7.4, 0.80 * 7.4 * FRAC), (0.0, 0.0), 6.0, 11)
mook(at_cam(9.0, -0.25 * 9.0 * FRAC), (0.0, 0.0), 3.0, 21)

# ------------------------------------------------------------------ lighting additions
# glossy-only shoji panel at front-left: lays one long latticed highlight across the lower bulb
def shoji_reflector(loc, size, strength):
    m = bpy.data.materials.new('shoji_refl')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nd(nt, 'ShaderNodeOutputMaterial')
    em = nd(nt, 'ShaderNodeEmission', Color=(1.0, 0.86, 0.68, 1), Strength=strength)
    tc = nd(nt, 'ShaderNodeTexCoord')
    sep = nd(nt, 'ShaderNodeSeparateXYZ')
    link(nt, tc.outputs['Generated'], sep.inputs['Vector'])
    bx = M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', M(nt, 'FRACT', M(nt, 'MULTIPLY', sep.outputs['X'], 2.0)), 0.5))
    by = M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', M(nt, 'FRACT', M(nt, 'MULTIPLY', sep.outputs['Y'], 6.0)), 0.5))
    bars = M(nt, 'MAXIMUM', smooth(nt, bx, 0.47, 0.485), smooth(nt, by, 0.46, 0.48))
    edge = M(nt, 'MULTIPLY', smooth(nt, sep.outputs['X'], 0.0, 0.08), smooth(nt, M(nt, 'SUBTRACT', 1.0, sep.outputs['X']), 0.0, 0.08))
    k = M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', 1.0, M(nt, 'MULTIPLY', bars, 0.85)), edge)
    link(nt, M(nt, 'MULTIPLY', k, strength), em.inputs['Strength'])
    link(nt, em.outputs['Emission'], out.inputs['Surface'])
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    o = bpy.context.object
    o.name = 'shoji_reflector'
    o.data.materials.append(m)
    o.scale = (size[0], size[1], 1)
    tgt = Vector((0, 0, 0.75))
    o.rotation_euler = (tgt - Vector(loc)).to_track_quat('Z', 'Y').to_euler()
    o.visible_camera = False
    o.visible_diffuse = False
    o.visible_shadow = False
    o.visible_transmission = False
    o.visible_volume_scatter = False
    try:
        o.light_linking.receiver_collection = HERO
    except Exception as e:
        print('light linking unavailable', e)
    return o


refl_dir = Vector((-0.70, -0.71, 0.0)).normalized()
shoji_reflector(tuple(Vector((0, 0, 0.80)) + refl_dir * 1.9), (0.95, 3.0), SHOJI_REFL)

import os
_crop = os.environ.get('SOMETSUKE_CROP')     # inspection only: "x0,x1,y0,y1" render border (0..1)
if _crop:
    x0, x1, y0, y1 = (float(v) for v in _crop.split(','))
    sc.render.use_border = True
    sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x, sc.render.border_min_y, sc.render.border_max_y = x0, x1, y0, y1
finish(a)
