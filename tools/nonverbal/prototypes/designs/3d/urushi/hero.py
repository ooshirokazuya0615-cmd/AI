import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from base import *
a = setup(); stage(); J = pose()   # hero at origin, 3/4 to camera
import bmesh
import random

YAW = -45.0
RW = Matrix.Rotation(math.radians(YAW), 4, 'Z')
RINV = Matrix.Rotation(math.radians(-YAW), 3, 'Z')
P = {k: RINV @ v for k, v in J.items()}          # joints back in the hero's local frame (facing -y, left = +x)
COL = bpy.context.collection

root = bpy.data.objects.new('URUSHI', None)
COL.objects.link(root)
root.matrix_basis = RW


# ---------------------------------------------------------------- helpers
def add_obj(name, me, m, parent=root, M=None):
    o = bpy.data.objects.new(name, me)
    COL.objects.link(o)
    if m is not None:
        o.data.materials.append(m)
    if parent is not None:
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
    if M is not None:
        o.matrix_basis = M
    return o


def smooth(me):
    for p in me.polygons:
        p.use_smooth = True


def frame(origin, z_dir, x_hint=None):
    z = Vector(z_dir).normalized()
    if x_hint is None:
        q = z.to_track_quat('Z', 'Y')
        R = q.to_matrix()
    else:
        x = Vector(x_hint)
        x = (x - x.dot(z) * z).normalized()
        y = z.cross(x)
        R = Matrix((x, y, z)).transposed()
    M = R.to_4x4()
    M.translation = Vector(origin)
    return M


def deformed_sphere(name, fn, segs=64, rings=32):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co = fn(v.co.copy())
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    smooth(me)
    return me


def subsurf(o, lv=1):
    md = o.modifiers.new('subd', 'SUBSURF')
    md.levels = md.render_levels = lv
    return md


# ---------------------------------------------------------------- materials
def kuro_urushi():
    m = bpy.data.materials.new('kuro_urushi')
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links.new
    b = N['Principled BSDF']
    b.inputs['Roughness'].default_value = 0.35
    b.inputs['Specular IOR Level'].default_value = 0.18
    b.inputs['Coat Weight'].default_value = 1.0
    b.inputs['Coat Roughness'].default_value = 0.04
    b.inputs['Coat IOR'].default_value = 1.5
    tc = N.new('ShaderNodeTexCoord')
    wave = N.new('ShaderNodeTexWave')
    wave.wave_type, wave.bands_direction = 'BANDS', 'X'
    wave.inputs['Scale'].default_value = 5.0
    wave.inputs['Distortion'].default_value = 8.0
    wave.inputs['Detail'].default_value = 4.0
    L(tc.outputs['Object'], wave.inputs['Vector'])
    bump = N.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.04
    L(wave.outputs['Fac'], bump.inputs['Height'])
    L(bump.outputs['Normal'], b.inputs['Normal'])          # grain on the base layer only; the coat stays glassy
    # faint wood tone showing through the lacquer
    grain = N.new('ShaderNodeMixRGB')
    grain.inputs['Color1'].default_value = (0.012, 0.010, 0.009, 1)
    grain.inputs['Color2'].default_value = (0.034, 0.017, 0.009, 1)
    gpow = N.new('ShaderNodeMath'); gpow.operation = 'POWER'; gpow.inputs[1].default_value = 3.0
    L(wave.outputs['Fac'], gpow.inputs[0])
    L(gpow.outputs['Value'], grain.inputs['Fac'])
    # hand-lacquer unevenness in the coat
    noise = N.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 25.0
    L(tc.outputs['Object'], noise.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = 0.3, 0.7
    mr.inputs['To Min'].default_value, mr.inputs['To Max'].default_value = 0.03, 0.09
    L(noise.outputs['Fac'], mr.inputs['Value'])
    L(mr.outputs['Result'], b.inputs['Coat Roughness'])
    # edge wear: vermilion-brown undercoat peeking at sharp convex edges
    geo = N.new('ShaderNodeNewGeometry')
    mw = N.new('ShaderNodeMapRange')
    mw.inputs['From Min'].default_value, mw.inputs['From Max'].default_value = 0.6, 0.68
    mw.inputs['To Min'].default_value, mw.inputs['To Max'].default_value = 0.0, 0.3
    L(geo.outputs['Pointiness'], mw.inputs['Value'])
    wear = N.new('ShaderNodeMixRGB')
    wear.inputs['Color2'].default_value = (0.10, 0.03, 0.015, 1)
    L(mw.outputs['Result'], wear.inputs['Fac'])
    L(grain.outputs['Color'], wear.inputs['Color1'])
    L(wear.outputs['Color'], b.inputs['Base Color'])
    return m


def shu_urushi():
    m = mat('shu_urushi', (0.578, 0.033, 0.024), 0.4, coat=1.0)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Coat Roughness'].default_value = 0.06
    b.inputs['Coat IOR'].default_value = 1.5
    b.inputs['Specular IOR Level'].default_value = 0.3
    return m


KURO = kuro_urushi()
SHU = shu_urushi()
GOLD = mat('gold', (1.0, 0.76, 0.33), 0.28, metal=1.0)


# ---------------------------------------------------------------- lathe spindles (Screw modifier on a 2D profile)
GAP = 0.002


def spindle(name, P0, R0, P1, R1, r0, r1, bulge=0.05, calf=0.0):
    P0, P1 = Vector(P0), Vector(P1)
    u = P1 - P0
    Lj = u.length

    def rim(R, r):
        rr = min(r * 0.86, (R + GAP) * 0.93)
        return rr, math.sqrt((R + GAP) ** 2 - rr ** 2)

    rr0, d0 = rim(R0, r0)
    rr1, d1 = rim(R1, r1)
    z0, z1 = d0, Lj - d1

    def body(z):
        t = (z - z0) / (z1 - z0)
        r = r0 + (r1 - r0) * t
        r *= 1 + bulge * math.sin(math.pi * t)
        if calf:
            r *= 1 + calf * math.exp(-((t - 0.3) / 0.17) ** 2)
        return r

    def fillet(s, rr, rb, f):
        if s >= f:
            return rb
        k = 1 - s / f
        return rr + (rb - rr) * math.sqrt(max(0.0, 1 - k * k))

    f0 = max(0.008, (body(z0) - rr0) * 2.2)
    f1 = max(0.008, (body(z1) - rr1) * 2.2)
    prof = []
    # concave socket dish at the start (sphere R0+gap around the ball)
    th0 = math.asin(rr0 / (R0 + GAP))
    for i in range(9):
        th = th0 * i / 8
        prof.append(((R0 + GAP) * math.sin(th), (R0 + GAP) * math.cos(th)))
    n = 56
    for i in range(1, n):
        s = (1 - math.cos(math.pi * i / n)) / 2      # denser near the ends
        z = z0 + (z1 - z0) * s
        rb = body(z)
        r = min(fillet(z - z0, rr0, rb, f0), fillet(z1 - z, rr1, rb, f1))
        prof.append((r, z))
    th1 = math.asin(rr1 / (R1 + GAP))
    for i in range(8, -1, -1):
        th = th1 * i / 8
        prof.append(((R1 + GAP) * math.sin(th), Lj - (R1 + GAP) * math.cos(th)))
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, 0, z) for x, z in prof], [(i, i + 1) for i in range(len(prof) - 1)], [])
    o = add_obj(name, me, KURO, M=frame(P0, u))
    sc = o.modifiers.new('lathe', 'SCREW')
    sc.axis = 'Z'; sc.steps = sc.render_steps = 48; sc.angle = 2 * math.pi
    sc.use_merge_vertices = True; sc.merge_threshold = 1e-5
    sc.use_smooth_shade = True; sc.use_normal_calculate = True
    subsurf(o, 2)
    o.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return o


def ball(name, c, r):
    me = deformed_sphere(name, lambda v: v * r, 48, 24)
    o = add_obj(name, me, SHU, M=Matrix.Translation(Vector(c)))
    subsurf(o, 1)
    return o


# ---------------------------------------------------------------- hero layout (local frame)
neck_pt = P['neck']
head_c = Vector((0.0, 0.0, P['head'].z + 0.015))
neck_ball_c = Vector((0.0, neck_pt.y, neck_pt.z + 0.065))
chest_c = neck_pt + Vector((0, -0.008, -0.195))
pelvis_c = P['hip'].copy()
waist_c = Vector((0.0, 0.006, 1.083))
sh = {s: Vector((0.18 * (1 if s == 'l' else -1), P['sh_' + s].y, P['sh_' + s].z - 0.02)) for s in 'lr'}
el = {s: P['el_' + s] for s in 'lr'}
ha = {s: P['ha_' + s] for s in 'lr'}
wr = {s: el[s] + (ha[s] - el[s]) * (1 - 0.075 / (ha[s] - el[s]).length) for s in 'lr'}
hipb = {s: Vector((0.09 * (1 if s == 'l' else -1), 0.0, 0.875)) for s in 'lr'}
kn = {s: P['kn_' + s] for s in 'lr'}
an = {s: P['ft_' + s] + Vector((0, 0, 0.04)) for s in 'lr'}

R_SH, R_EL, R_WR, R_HIP, R_KN, R_AN, R_WAIST, R_NECK = 0.045, 0.036, 0.026, 0.058, 0.046, 0.032, 0.06, 0.038

# --- head: egg, narrow end down, tilted forward 6 deg
HEAD_R = (0.085, 0.10, 0.117)


def egg(v):
    k = 1 - 0.17 * max(0.0, -v.z) ** 1.4
    return Vector((v.x * HEAD_R[0] * k, v.y * HEAD_R[1] * k, v.z * HEAD_R[2]))


HEAD_M = Matrix.Translation(head_c) @ Matrix.Rotation(math.radians(30), 4, 'Z') @ Matrix.Rotation(math.radians(6), 4, 'X')
head = add_obj('head', deformed_sphere('head', egg), KURO, M=HEAD_M)
subsurf(head, 1)

# --- neck + neck ball + gold ring
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=0.032, radius2=0.032, depth=0.12)
neck_me = bpy.data.meshes.new('neck'); bm.to_mesh(neck_me); bm.free(); smooth(neck_me)
neck = add_obj('neck', neck_me, KURO, M=Matrix.Translation(Vector((0, neck_pt.y, neck_pt.z + 0.0))))
neck.modifiers.new('bev', 'BEVEL').width = 0.004
ball('ball_neck', neck_ball_c, R_NECK)


# --- chest: rib-cage block
def chest_fn(v):
    x = math.copysign(abs(v.x) ** 0.62, v.x)
    z = math.copysign(abs(v.z) ** 0.75, v.z)
    y = math.copysign(abs(v.y) ** 0.85, v.y)
    wx = 1 + 0.13 * z
    wy = 1 + 0.07 * z
    X, Y, Z = x * 0.150 * wx, y * 0.105 * wy, z * 0.165
    if Y > 0.055:                       # flatter back
        Y = 0.055 + (Y - 0.055) * 0.7
    zb = -0.165 + 0.2 * 0.33
    if Z < zb:
        Z = zb + (Z - zb) * 0.6
    yf = -0.105 + 0.15 * 0.21
    if Y < yf:
        Y = yf + (Y - yf) * 0.5
    return Vector((X, Y, Z))


chest = add_obj('chest', deformed_sphere('chest', chest_fn), KURO, M=Matrix.Translation(chest_c))
subsurf(chest, 1)
# where the neck leaves the chest
def _chest_top(r_axis=0.034, dy=neck_pt.y - chest_c.y):
    zs = []
    for i in range(1, 400):
        ph = math.radians(40 * i / 400)
        for k in range(24):
            az = 2 * math.pi * k / 24
            q = chest_fn(Vector((math.sin(ph) * math.cos(az), math.sin(ph) * math.sin(az), math.cos(ph))))
            if abs(math.hypot(q.x, q.y - dy) - r_axis) < 0.002:
                zs.append(q.z)
    return sum(zs) / len(zs)


top_z = _chest_top()
ring_z = chest_c.z + top_z
bpy.ops.mesh.primitive_torus_add(major_radius=0.034, minor_radius=0.002, major_segments=64, minor_segments=12)
ring = bpy.context.object; ring.name = 'gold_ring'
ring.parent = root; ring.matrix_parent_inverse = Matrix.Identity(4)
ring.matrix_basis = Matrix.Translation(Vector((0, neck_pt.y, ring_z + 0.001)))
ring.data.materials.append(GOLD); bpy.ops.object.shade_smooth()

ball('ball_waist', waist_c, R_WAIST)


# --- pelvis
def pelvis_fn(v):
    x = math.copysign(abs(v.x) ** 0.72, v.x)
    y = math.copysign(abs(v.y) ** 0.9, v.y)
    z = v.z
    X, Y, Z = x * 0.145, y * 0.10, z * (0.11 if z > 0 else 0.095)
    if z < 0:
        X *= 1 - 0.24 * (-z) ** 1.2
        Y *= 1 - 0.10 * (-z)
    if Z > 0.075:
        Z = 0.075 + (Z - 0.075) * 0.5
    zb = -0.095 * 0.45
    if Z < zb:
        Z = zb + (Z - zb) * 0.55
    return Vector((X, Y, Z))


pelvis = add_obj('pelvis', deformed_sphere('pelvis', pelvis_fn), KURO, M=Matrix.Translation(pelvis_c))
subsurf(pelvis, 1)

# --- joint balls
for s in 'lr':
    ball('ball_sh_' + s, sh[s], R_SH)
    ball('ball_el_' + s, el[s], R_EL)
    ball('ball_wr_' + s, wr[s], R_WR)
    ball('ball_hip_' + s, hipb[s], R_HIP)
    ball('ball_kn_' + s, kn[s], R_KN)
    ball('ball_an_' + s, an[s], R_AN)

# --- spindles
for s in 'lr':
    spindle('upperarm_' + s, sh[s], R_SH, el[s], R_EL, 0.040, 0.030)
    spindle('forearm_' + s, el[s], R_EL, wr[s], R_WR, 0.033, 0.024)
    spindle('thigh_' + s, hipb[s], R_HIP, kn[s], R_KN, 0.064, 0.045)
    spindle('shin_' + s, kn[s], R_KN, an[s], R_AN, 0.047, 0.031, bulge=0.02, calf=0.10)


# --- hands: cupped mittens with a thumb nub
def hand(s):
    side = 1 if s == 'l' else -1
    fdir = (ha[s] - wr[s]).normalized()
    zdir = (fdir * 0.45 + Vector((0, 0, 0.85))).normalized()     # wrist cocked: open-hand guard, fingers up
    palm = Vector((-1.0 * side, -0.55, 0.0))                     # palms inward-forward: broad mitten faces read on camera
    M = frame(wr[s] + zdir * 0.010, zdir, palm)
    y_axis = M.to_3x3().col[1]
    flip = 1 if y_axis.dot(Vector((-side, 0, 0))) > 0 else -1     # thumb on the inner side
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.0)
    for v in bm.verts:
        c = v.co
        y = math.copysign(abs(c.y) ** 0.8, c.y)
        z = math.copysign(abs(c.z) ** (0.72 if c.z > 0 else 0.95), c.z)     # blunt, rounded fingertip end
        X = c.x * 0.025 * (1 - 0.15 * max(0, z))
        Y = y * 0.05 * (1 - 0.22 * max(0, -z))                            # narrower at the wrist
        v.co = Vector((X, Y, z * 0.085 + 0.07))
    th = bmesh.new()
    bmesh.ops.create_uvsphere(th, u_segments=24, v_segments=12, radius=1.0)
    Rt = Matrix.Rotation(math.radians(-30 * flip), 3, 'X')
    for v in th.verts:
        c = Vector((v.co.x * 0.018, v.co.y * 0.018, v.co.z * 0.035))
        v.co = Rt @ c + Vector((0.008, 0.034 * flip, 0.038))
    me = bpy.data.meshes.new('hand_' + s)
    bm.to_mesh(me); bm.free()
    tme = bpy.data.meshes.new('t'); th.to_mesh(tme); th.free()
    bm2 = bmesh.new(); bm2.from_mesh(me); bm2.from_mesh(tme); bm2.to_mesh(me); bm2.free()
    smooth(me)
    o = add_obj('hand_' + s, me, KURO, M=M)
    md = o.modifiers.new('cup', 'SIMPLE_DEFORM')
    md.deform_method = 'BEND'; md.deform_axis = 'Y'; md.angle = math.radians(25)
    subsurf(o, 1)
    return o


for s in 'lr':
    hand(s)


# --- feet: rounded wedges
def foot_fn(v):
    x = math.copysign(abs(v.x) ** 0.6, v.x)
    y = math.copysign(abs(v.y) ** (0.75 if v.y < 0 else 0.55), v.y)
    z = math.copysign(abs(v.z) ** (0.3 if v.z < 0 else 0.6), v.z)
    t = (y + 1) / 2                                   # 0 heel .. 1 toe
    k = min(1, max(0, (t - 0.22) / 0.78))
    h = 0.040 + 0.036 * (1 - k * k * (3 - 2 * k))     # tall instep at the ankle, thin rounded toe
    w = 0.062 + 0.024 * math.sin(math.pi * min(1, t / 0.9) ** 0.8)
    return Vector((x * w / 2, y * 0.12, (z + 1) / 2 * h))


def foot(s, toe_dir):
    fwd = Vector((toe_dir[0], toe_dir[1], 0)).normalized()
    A = an[s]
    origin = Vector((A.x, A.y, -0.001)) + fwd * 0.05
    R = Matrix((Vector((0, 0, 1)).cross(fwd), fwd, Vector((0, 0, 1)))).transposed().to_4x4()
    R.translation = origin
    o = add_obj('foot_' + s, deformed_sphere('foot_' + s, foot_fn, 64, 32), KURO, M=R)
    subsurf(o, 1)
    return o


foot('l', (-0.15, -1.0))
foot('r', (-0.55, -0.83))

# --- signature: gold maki-e meridian line (the only 'face')
pts = []
for i in range(61):
    t = math.radians(-25 + 205 * i / 60)
    v = Vector((0.0, -math.sin(t), math.cos(t)))
    p = egg(v)
    n = p.normalized()
    pts.append(HEAD_M @ (p + n * 0.0006))
cu = bpy.data.curves.new('maki_e', 'CURVE')
cu.dimensions = '3D'; cu.bevel_depth = 0.0035; cu.bevel_resolution = 3; cu.use_fill_caps = True
sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
for p, q in zip(sp.points, pts):
    p.co = (q.x, q.y, q.z, 1)
add_obj('maki_e_line', cu, GOLD)


# ---------------------------------------------------------------- extra lights for the lacquer (spec lighting notes)
def strip(loc, tgt, energy, col, sx, sy):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.data.shape = 'RECTANGLE'; l.data.size = sx; l.data.size_y = sy
    l.data.energy, l.data.color = energy, col
    l.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    l.light_linking.receiver_collection = LIT      # lights the lacquer only, never the floor or the straw men
    return l


LIT = bpy.data.collections.new('urushi_lit')
for o in list(bpy.data.objects):
    if o.parent == root:
        LIT.objects.link(o)
strip((2.7, -2.0, 2.3), (0, 0, 1.15), 70, (1.0, 0.84, 0.64), 0.5, 2.4)      # warm key, front-right
strip((-2.5, 2.3, 2.3), (0, 0, 1.2), 160, (0.58, 0.74, 1.0), 0.4, 2.2)      # cool rim, back-left


# ---------------------------------------------------------------- MOOKS: makiwara straw men
def straw_mat():
    m = bpy.data.materials.new('straw')
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links.new
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (70, 70, 1.2)
    L(tc.outputs['Object'], mp.inputs['Vector'])
    no = N.new('ShaderNodeTexNoise'); no.inputs['Scale'].default_value = 1.0; no.inputs['Detail'].default_value = 6.0
    L(mp.outputs['Vector'], no.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[1].position = 0.60
    ramp.color_ramp.elements[0].color = (0.254, 0.147, 0.036, 1)
    ramp.color_ramp.elements[1].color = (0.584, 0.381, 0.102, 1)
    L(no.outputs['Fac'], ramp.inputs['Fac'])
    mp2 = N.new('ShaderNodeMapping'); mp2.inputs['Scale'].default_value = (24, 24, 0.6)
    L(tc.outputs['Object'], mp2.inputs['Vector'])
    n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 1.0
    L(mp2.outputs['Vector'], n2.inputs['Vector'])
    dk = N.new('ShaderNodeMapRange')
    dk.inputs['From Min'].default_value, dk.inputs['From Max'].default_value = 0.35, 0.65
    dk.inputs['To Min'].default_value, dk.inputs['To Max'].default_value = 0.42, 1.0
    L(n2.outputs['Fac'], dk.inputs['Value'])
    mul = N.new('ShaderNodeMixRGB'); mul.blend_type = 'MULTIPLY'; mul.inputs['Fac'].default_value = 1.0
    L(ramp.outputs['Color'], mul.inputs['Color1'])
    L(dk.outputs['Result'], mul.inputs['Color2'])
    L(mul.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.75
    b.inputs['Sheen Weight'].default_value = 0.3
    bu = N.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = 0.4; bu.inputs['Distance'].default_value = 0.02
    L(no.outputs['Fac'], bu.inputs['Height'])
    L(bu.outputs['Normal'], b.inputs['Normal'])
    return m


def rope_mat():
    m = bpy.data.materials.new('rope')
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links.new
    b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.044, 0.023, 0.014, 1)
    b.inputs['Roughness'].default_value = 0.85
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (60, 6, 1)
    L(tc.outputs['UV'], mp.inputs['Vector'])
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'DIAGONAL'
    wv.inputs['Scale'].default_value = 1.0; wv.inputs['Distortion'].default_value = 0.5
    L(mp.outputs['Vector'], wv.inputs['Vector'])
    bu = N.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = 0.7; bu.inputs['Distance'].default_value = 0.004
    L(wv.outputs['Fac'], bu.inputs['Height'])
    L(bu.outputs['Normal'], b.inputs['Normal'])
    return m


STRAW = straw_mat()
ROPE = rope_mat()
FRAY = bpy.data.textures.new('fray', 'CLOUDS')
FRAY.noise_scale = 0.0035
FRAY.noise_depth = 1


def bundle(name, parent, p0, p1, rfun, fray_top=True, fray_bot=True, segs=48, rings=20, seed=0):
    """Straw bundle along p0->p1, radius rfun(t), frayed fringe on the end caps."""
    rnd = random.Random(seed)
    p0, p1 = Vector(p0), Vector(p1)
    Ln = (p1 - p0).length
    prof = [(0.0, 0.0, 1.0 if fray_bot else 0.0)]
    CR = 5
    for i in range(1, CR + 1):
        prof.append((rfun(0) * i / CR, 0.0, (1.0 - 0.35 * i / CR) if fray_bot else 0.0))
    for j in range(1, rings):
        t = j / rings
        prof.append((rfun(t), Ln * t, 0.0))
    for i in range(CR, 0, -1):
        prof.append((rfun(1) * i / CR, Ln, (1.0 - 0.35 * i / CR) if fray_top else 0.0))
    prof.append((0.0, Ln, 1.0 if fray_top else 0.0))
    verts, faces, wts, rows = [], [], [], []
    for r, z, w in prof:
        if r == 0.0:
            rows.append([len(verts)]); verts.append((0, 0, z)); wts.append(w)
        else:
            row = []
            for k in range(segs):
                ang = 2 * math.pi * k / segs
                rr = r * (1 + rnd.uniform(-0.05, 0.05) + 0.06 * math.sin(3 * ang + seed) * math.sin(7 * z + seed))
                row.append(len(verts)); verts.append((rr * math.cos(ang), rr * math.sin(ang), z)); wts.append(w)
            rows.append(row)
    for a_, b_ in zip(rows[:-1], rows[1:]):
        if len(a_) == 1:
            for k in range(segs):
                faces.append((a_[0], b_[(k + 1) % segs], b_[k]))
        elif len(b_) == 1:
            for k in range(segs):
                faces.append((a_[k], a_[(k + 1) % segs], b_[0]))
        else:
            for k in range(segs):
                faces.append((a_[k], a_[(k + 1) % segs], b_[(k + 1) % segs], b_[k]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update(calc_edges=True)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]); bm.to_mesh(me); bm.free()
    smooth(me)
    o = add_obj(name, me, STRAW, parent=parent, M=frame(p0, p1 - p0))
    vg = o.vertex_groups.new(name='fray')
    for i, w in enumerate(wts):
        if w > 0:
            vg.add([i], w, 'REPLACE')
    if fray_top or fray_bot:
        d = o.modifiers.new('fray', 'DISPLACE')
        d.texture = FRAY; d.direction = 'NORMAL'; d.mid_level = 0.0; d.strength = 0.045
        d.vertex_group = 'fray'; d.texture_coords = 'LOCAL'
    return o


def rope_band(name, parent, c, axis, R, r=0.020):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=64, minor_segments=12,
                                     generate_uvs=True)
    o = bpy.context.object; o.name = name
    o.parent = parent; o.matrix_parent_inverse = Matrix.Identity(4)
    o.matrix_basis = frame(c, axis)
    o.data.materials.append(ROPE); bpy.ops.object.shade_smooth()
    return o


def makiwara(name, pos, seed):
    rt = bpy.data.objects.new(name, None); COL.objects.link(rt)
    face = (Vector((0, 0, 0)) - Vector((pos[0], pos[1], 0))).normalized()
    yaw = math.atan2(face.y, face.x) + math.pi / 2       # local -y faces the hero
    rt.matrix_basis = Matrix.Translation(Vector((pos[0], pos[1], 0))) @ Matrix.Rotation(yaw, 4, 'Z')
    TB, TT = 0.70, 1.42
    bands = (0.17, 0.50, 0.84)

    def torso_r(t):
        r = 0.16
        if t > 0.66:
            k = (t - 0.66) / 0.34
            r = 0.16 - 0.04 * (3 * k * k - 2 * k * k * k)
        for tb in bands:
            r *= 1 - 0.07 * math.exp(-((t - tb) / 0.035) ** 2)
        return r

    bundle(name + '_torso', rt, (0, 0, TB), (0, 0, TT), torso_r, fray_top=False, fray_bot=True, segs=64, rings=40,
           seed=seed)
    for tb in bands:
        rope_band(name + '_band', rt, (0, 0, TB + (TT - TB) * tb), (0, 0, 1), torso_r(tb) + 0.010)
    # head bundle + tied tuft
    hc = Vector((0, 0, 1.55))
    h = add_obj(name + '_head', deformed_sphere(name + '_head', lambda v: Vector((v.x * 0.11, v.y * 0.11, v.z * 0.13)), 48, 24),
                STRAW, parent=rt, M=Matrix.Translation(hc))
    bundle(name + '_tuft', rt, hc + Vector((0, 0, 0.10)), hc + Vector((0, 0, 0.21)),
           lambda t: 0.035 + 0.025 * t, fray_top=True, fray_bot=False, segs=48, rings=6, seed=seed + 1)
    rope_band(name + '_tie', rt, hc + Vector((0, 0, 0.115)), (0, 0, 1), 0.036, 0.010)
    rope_band(name + '_neck', rt, Vector((0, 0, TT - 0.005)), (0, 0, 1), 0.115, 0.014)
    # stiff arms, 30 deg forward/down
    for sd in (1, -1):
        s0 = Vector((0.13 * sd, -0.02, 1.27))
        d = Vector((0.22 * sd, -math.cos(math.radians(30)), -math.sin(math.radians(30)))).normalized()
        bundle(name + '_arm', rt, s0, s0 + d * 0.56, lambda t: 0.05 * (1 - 0.1 * t), fray_top=True, fray_bot=False,
               seed=seed + 2 + sd)
        rope_band(name + '_wband', rt, s0 + d * 0.47, d, 0.048, 0.010)
        # legs
        l0 = Vector((0.085 * sd, 0, 0.78))
        l1 = Vector((0.10 * sd, 0, 0.0))
        bundle(name + '_leg', rt, l1, l0, lambda t: 0.07 * (1 - 0.08 * (1 - t)), fray_top=False, fray_bot=False,
               seed=seed + 5 + sd)
        rope_band(name + '_aband', rt, l1 + Vector((0, 0, 0.09)), l0 - l1, 0.067, 0.014)
    return rt


CP = Vector(CAM['loc']); f = (Vector(CAM['tgt']) - CP).normalized(); rgt = Vector((f.y, -f.x, 0)).normalized()
fh = Vector((f.x, f.y, 0)).normalized()
for i, (depth, lat) in enumerate(((7.3, -0.95), (6.6, 0.92), (9.8, -1.62))):
    p = CP + fh * depth + rgt * lat
    makiwara('makiwara%d' % i, (p.x, p.y), 10 * i)

finish(a)
