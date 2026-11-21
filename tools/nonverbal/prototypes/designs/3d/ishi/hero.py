import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from base import *
a = setup(); stage(); J = pose()   # J: joint positions, hero at origin, 3/4 to camera
# ISHI - balanced river-stone master. Every part is a procedurally shaped, displaced stone.
import os
import random
import bmesh
from mathutils import Quaternion, noise

sc = bpy.context.scene
YAW = -45.0
R = Matrix.Rotation(math.radians(YAW), 3, 'Z')    # same turn as pose()
FWD = R @ Vector((0, -1, 0))                       # hero facing (world)
Z = Vector((0, 0, 1))


def W(p):
    """hero-local (facing -y, left = +x) -> world"""
    return R @ Vector(p)


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ============================================================ materials
def node(nt, kind, loc=None, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def L(nt, a_out, b_in):
    nt.links.new(a_out, b_in)


def rgba(c):
    return (*c, 1.0)


def obj_coords(nt, jitter=True):
    """object-space coords, offset per object so identical stones never share a pattern"""
    tc = nt.nodes.new('ShaderNodeTexCoord')
    if not jitter:
        return tc.outputs['Object']
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    sc_ = nt.nodes.new('ShaderNodeVectorMath')
    sc_.operation = 'SCALE'
    sc_.inputs[0].default_value = (37.1, 51.7, 23.3)
    L(nt, oi.outputs['Random'], sc_.inputs['Scale'])
    ad = nt.nodes.new('ShaderNodeVectorMath')
    ad.operation = 'ADD'
    L(nt, tc.outputs['Object'], ad.inputs[0])
    L(nt, sc_.outputs['Vector'], ad.inputs[1])
    return ad.outputs['Vector']


def noise_tex(nt, vec, scale, detail=2.0, rough=0.5, dist=0.0):
    n = nt.nodes.new('ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    n.inputs['Distortion'].default_value = dist
    L(nt, vec, n.inputs['Vector'])
    return n


def voronoi(nt, vec, scale, feature='F1', rand=1.0):
    v = nt.nodes.new('ShaderNodeTexVoronoi')
    v.feature = feature
    v.inputs['Scale'].default_value = scale
    v.inputs['Randomness'].default_value = rand
    L(nt, vec, v.inputs['Vector'])
    return v


def maprange(nt, val, a0, a1, b0, b1, interp='LINEAR', clamp=True):
    m = nt.nodes.new('ShaderNodeMapRange')
    m.interpolation_type = interp
    m.clamp = clamp
    m.inputs['From Min'].default_value = a0
    m.inputs['From Max'].default_value = a1
    m.inputs['To Min'].default_value = b0
    m.inputs['To Max'].default_value = b1
    L(nt, val, m.inputs['Value'])
    return m.outputs['Result']


def mixc(nt, fac, c1, c2, blend='MIX'):
    m = nt.nodes.new('ShaderNodeMixRGB')
    m.blend_type = blend
    if isinstance(fac, float):
        m.inputs['Fac'].default_value = fac
    else:
        L(nt, fac, m.inputs['Fac'])
    for i, c in ((1, c1), (2, c2)):
        if isinstance(c, tuple):
            m.inputs[i].default_value = rgba(c)
        else:
            L(nt, c, m.inputs[i])
    return m.outputs['Color']


def math_n(nt, op, x, y=None):
    m = nt.nodes.new('ShaderNodeMath')
    m.operation = op
    for i, v in enumerate((x, y)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            m.inputs[i].default_value = v
        else:
            L(nt, v, m.inputs[i])
    return m.outputs['Value']


def bump(nt, height, strength, dist=1.0, normal=None):
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = strength
    b.inputs['Distance'].default_value = dist
    L(nt, height, b.inputs['Height'])
    if normal is not None:
        L(nt, normal, b.inputs['Normal'])
    return b.outputs['Normal']


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes['Principled BSDF'], nt.nodes['Material Output']


def basalt_into(nt, bs, vec):
    """dark river basalt: per-stone hue, wet glossy vs dry matte patches, light speckles, pits, dirty crevices"""
    oi = nt.nodes.new('ShaderNodeObjectInfo')
    tint = nt.nodes.new('ShaderNodeValToRGB')
    cr = tint.color_ramp
    cr.interpolation = 'CONSTANT'
    cr.elements[0].position, cr.elements[0].color = 0.0, rgba((0.031, 0.037, 0.034))
    cr.elements[1].position, cr.elements[1].color = 0.3, rgba((0.027, 0.030, 0.034))
    e = cr.elements.new(0.55)
    e.color = rgba((0.038, 0.035, 0.031))
    e = cr.elements.new(0.8)
    e.color = rgba((0.034, 0.041, 0.035))
    L(nt, oi.outputs['Random'], tint.inputs['Fac'])
    lo = noise_tex(nt, vec, 5.0, 4.0, 0.55)
    lof = maprange(nt, lo.outputs['Fac'], 0.32, 0.68, 0.0, 1.0)
    base = mixc(nt, lof, mixc(nt, 1.0, tint.outputs['Color'], (0.72, 0.72, 0.72), 'MULTIPLY'),
                mixc(nt, 1.0, tint.outputs['Color'], (1.3, 1.3, 1.3), 'MULTIPLY'))
    # faint mineral banding so big stones are not uniform
    band = noise_tex(nt, vec, 1.6, 3.0, 0.6, dist=2.0)
    base = mixc(nt, maprange(nt, band.outputs['Fac'], 0.48, 0.75, 0.0, 0.45), base, (0.072, 0.076, 0.071))
    sp = voronoi(nt, vec, 170.0)
    spm = maprange(nt, sp.outputs['Distance'], 0.11, 0.06, 0.0, 0.9)
    base = mixc(nt, spm, base, (0.25, 0.26, 0.24))
    # vesicle pits (darker, recessed)
    pit = voronoi(nt, vec, 32.0)
    pitm = maprange(nt, pit.outputs['Distance'], 0.10, 0.06, 0.0, 1.0)
    base = mixc(nt, math_n(nt, 'MULTIPLY', pitm, 0.7), base, (0.018, 0.02, 0.019))
    # dry (lighter, matte) vs wet (darker, glossy) patches
    wet = noise_tex(nt, vec, 3.0, 3.0, 0.5)
    dryf = maprange(nt, wet.outputs['Fac'], 0.50, 0.66, 0.0, 1.0, 'SMOOTHSTEP')
    base = mixc(nt, math_n(nt, 'MULTIPLY', dryf, 0.55), base, (0.078, 0.081, 0.077))
    # soil / moss traces in the crevices where stones press together
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.035
    ao.samples = 8
    crev = maprange(nt, ao.outputs['AO'], 0.75, 0.30, 0.0, 1.0)
    mos = noise_tex(nt, vec, 18.0, 3.0, 0.6)
    crc = mixc(nt, maprange(nt, mos.outputs['Fac'], 0.45, 0.6, 0.0, 1.0), (0.022, 0.020, 0.016), (0.035, 0.06, 0.012))
    base = mixc(nt, crev, base, crc)
    L(nt, base, bs.inputs['Base Color'])
    rough = maprange(nt, wet.outputs['Fac'], 0.40, 0.66, 0.30, 0.62)
    L(nt, math_n(nt, 'MAXIMUM', rough, math_n(nt, 'MULTIPLY', crev, 0.85)), bs.inputs['Roughness'])
    mic = noise_tex(nt, vec, 250.0, 2.0, 0.5)
    nrm = bump(nt, mic.outputs['Fac'], 0.04)
    grain = noise_tex(nt, vec, 70.0, 4.0, 0.65)
    nrm = bump(nt, grain.outputs['Fac'], 0.10, 0.004, nrm)
    nrm = bump(nt, math_n(nt, 'MULTIPLY', pitm, -1.0), 0.25, 0.002, nrm)
    return nrm


def m_basalt(name='basalt'):
    m, nt, bs, out = new_mat(name)
    vec = obj_coords(nt)
    nrm = basalt_into(nt, bs, vec)
    L(nt, nrm, bs.inputs['Normal'])
    bs.inputs['Specular IOR Level'].default_value = 0.5
    return m


def m_basalt_vein(centre=0.0):
    """basalt with a slightly wavy, slightly raised white quartz band around local z = centre"""
    m, nt, bs, out = new_mat('basalt_vein')
    vec = obj_coords(nt, jitter=False)
    nrm = basalt_into(nt, bs, vec)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    L(nt, vec, sep.inputs['Vector'])
    wav = noise_tex(nt, vec, 8.0, 2.0, 0.5)
    fine = noise_tex(nt, vec, 70.0, 3.0, 0.6)
    z = math_n(nt, 'ADD', sep.outputs['Z'], math_n(nt, 'MULTIPLY', sep.outputs['X'], 0.07))      # slight tilt
    z = math_n(nt, 'ADD', z, maprange(nt, wav.outputs['Fac'], 0.3, 0.7, -0.012, 0.012, clamp=False))
    z = math_n(nt, 'ADD', z, maprange(nt, fine.outputs['Fac'], 0.3, 0.7, -0.0025, 0.0025, clamp=False))
    d = math_n(nt, 'ABSOLUTE', math_n(nt, 'SUBTRACT', z, centre))
    mask = maprange(nt, d, 0.021, 0.0175, 0.0, 1.0, 'SMOOTHSTEP')
    q = nt.nodes.new('ShaderNodeBsdfPrincipled')
    qn = noise_tex(nt, vec, 30.0, 3.0, 0.6)
    L(nt, mixc(nt, maprange(nt, qn.outputs['Fac'], 0.35, 0.65, 0.0, 1.0), (0.80, 0.78, 0.72), (0.88, 0.865, 0.81)), q.inputs['Base Color'])
    q.inputs['Roughness'].default_value = 0.3
    q.inputs['Subsurface Weight'].default_value = 0.3
    q.inputs['Subsurface Radius'].default_value = (0.6, 0.6, 0.6)
    q.inputs['Subsurface Scale'].default_value = 0.01
    vn = bump(nt, mask, 0.6, 0.0012, nrm)
    L(nt, vn, bs.inputs['Normal'])
    L(nt, vn, q.inputs['Normal'])
    mx = nt.nodes.new('ShaderNodeMixShader')
    L(nt, mask, mx.inputs['Fac'])
    L(nt, bs.outputs['BSDF'], mx.inputs[1])
    L(nt, q.outputs['BSDF'], mx.inputs[2])
    L(nt, mx.outputs['Shader'], out.inputs['Surface'])
    return m


def m_granite():
    """pale salt-and-pepper granite: fine irregular biotite, white feldspar, a few warm crystals"""
    m, nt, bs, out = new_mat('granite')
    vec = obj_coords(nt, jitter=False)
    dn = noise_tex(nt, vec, 40.0, 2.0, 0.5)
    dv = nt.nodes.new('ShaderNodeVectorMath')
    dv.operation = 'ADD'
    L(nt, vec, dv.inputs[0])
    L(nt, mixc(nt, 1.0, dn.outputs['Color'], (0.006, 0.006, 0.006), 'MULTIPLY'), dv.inputs[1])
    dvec = dv.outputs['Vector']
    lo = noise_tex(nt, vec, 6.0, 3.0, 0.55)
    base = mixc(nt, maprange(nt, lo.outputs['Fac'], 0.35, 0.65, 0.0, 1.0), (0.33, 0.315, 0.285), (0.44, 0.42, 0.375))
    fel = noise_tex(nt, dvec, 150.0, 2.0, 0.5)
    fel_m = maprange(nt, fel.outputs['Fac'], 0.565, 0.595, 0.0, 0.9)
    base = mixc(nt, fel_m, base, (0.70, 0.68, 0.64))
    bio = voronoi(nt, dvec, 140.0)
    bio_m = maprange(nt, bio.outputs['Distance'], 0.215, 0.165, 0.0, 1.0)
    base = mixc(nt, bio_m, base, (0.035, 0.034, 0.032))
    pk = voronoi(nt, dvec, 55.0)
    pk_m = maprange(nt, pk.outputs['Distance'], 0.12, 0.08, 0.0, 0.5)
    base = mixc(nt, pk_m, base, (0.52, 0.42, 0.33))
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.03
    ao.samples = 8
    base = mixc(nt, maprange(nt, ao.outputs['AO'], 0.8, 0.35, 0.0, 0.8), base, (0.05, 0.05, 0.04))
    L(nt, base, bs.inputs['Base Color'])
    L(nt, maprange(nt, fel_m, 0.0, 0.9, 0.5, 0.34), bs.inputs['Roughness'])
    mic = noise_tex(nt, vec, 250.0, 2.0, 0.5)
    nrm = bump(nt, mic.outputs['Fac'], 0.05)
    nrm = bump(nt, bio_m, 0.12, 0.0008, nrm)
    L(nt, nrm, bs.inputs['Normal'])
    return m


def m_moss():
    m, nt, bs, out = new_mat('moss')
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_name = 'moss_h'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = rgba((0.05, 0.10, 0.015))
    ramp.color_ramp.elements[1].position = 0.9
    ramp.color_ramp.elements[1].color = rgba((0.15, 0.25, 0.035))
    L(nt, at.outputs['Fac'], ramp.inputs['Fac'])
    tc = nt.nodes.new('ShaderNodeTexCoord')
    hue = noise_tex(nt, tc.outputs['Object'], 60.0, 2.0, 0.5)
    col = mixc(nt, maprange(nt, hue.outputs['Fac'], 0.4, 0.7, 0.0, 0.5), ramp.outputs['Color'], (0.17, 0.22, 0.03))
    L(nt, col, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.9
    bs.inputs['Sheen Weight'].default_value = 0.8
    bs.inputs['Sheen Roughness'].default_value = 0.4
    bs.inputs['Sheen Tint'].default_value = rgba((0.7, 0.9, 0.4))
    bs.inputs['Specular IOR Level'].default_value = 0.3
    fz = noise_tex(nt, tc.outputs['Object'], 400.0, 2.0, 0.6)
    L(nt, bump(nt, fz.outputs['Fac'], 0.3), bs.inputs['Normal'])
    return m


def m_sprig():
    m, nt, bs, out = new_mat('sprig')
    bs.inputs['Base Color'].default_value = rgba((0.17, 0.27, 0.045))
    bs.inputs['Roughness'].default_value = 0.7
    bs.inputs['Sheen Weight'].default_value = 0.6
    bs.inputs['Sheen Tint'].default_value = rgba((0.7, 0.9, 0.4))
    bs.inputs['Subsurface Weight'].default_value = 0.2
    bs.inputs['Subsurface Radius'].default_value = (0.4, 0.8, 0.2)
    bs.inputs['Subsurface Scale'].default_value = 0.004
    return m


def m_gravel():
    m, nt, bs, out = new_mat('gravel')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    vec = tc.outputs['Object']
    g = voronoi(nt, vec, 170.0)
    g2 = voronoi(nt, vec, 170.0)
    g2.feature = 'F2'
    edge = math_n(nt, 'SUBTRACT', g2.outputs['Distance'], g.outputs['Distance'])
    tone = maprange(nt, g.outputs['Color'], 0.0, 1.0, 0.0, 1.0)
    base = mixc(nt, tone, (0.44, 0.43, 0.40), (0.60, 0.585, 0.55))
    dark = maprange(nt, edge, 0.0, 0.12, 1.0, 0.0)
    base = mixc(nt, math_n(nt, 'MULTIPLY', dark, 0.55), base, (0.25, 0.24, 0.22))
    sp = voronoi(nt, vec, 90.0)
    base = mixc(nt, maprange(nt, sp.outputs['Distance'], 0.08, 0.05, 0.0, 0.7), base, (0.22, 0.21, 0.2))
    L(nt, base, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.9
    hgt = maprange(nt, edge, 0.0, 0.25, 0.0, 1.0, 'SMOOTHSTEP')
    L(nt, bump(nt, hgt, 0.8, 0.003), bs.inputs['Normal'])
    return m


def m_rubble():
    m, nt, bs, out = new_mat('rubble_granite')
    vec = obj_coords(nt)
    lo = noise_tex(nt, vec, 4.0, 3.0, 0.55)
    base = mixc(nt, maprange(nt, lo.outputs['Fac'], 0.35, 0.65, 0.0, 1.0), (0.040, 0.032, 0.026), (0.066, 0.053, 0.042))
    f1 = voronoi(nt, vec, 160.0)
    base = mixc(nt, maprange(nt, f1.outputs['Distance'], 0.22, 0.17, 0.0, 1.0), base, (0.025, 0.022, 0.02))
    f2 = noise_tex(nt, vec, 140.0, 2.0, 0.5)
    base = mixc(nt, maprange(nt, f2.outputs['Fac'], 0.6, 0.63, 0.0, 0.6), base, (0.17, 0.155, 0.135))
    L(nt, base, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.8
    cr = voronoi(nt, vec, 7.0, 'DISTANCE_TO_EDGE')
    crm = maprange(nt, cr.outputs['Distance'], 0.0, 0.025, 0.0, 1.0)
    mic = noise_tex(nt, vec, 120.0, 3.0, 0.6)
    nrm = bump(nt, mic.outputs['Fac'], 0.12)
    L(nt, bump(nt, crm, 0.2, 0.003, nrm), bs.inputs['Normal'])
    return m


BASALT = m_basalt()
VEIN = m_basalt_vein()
GRANITE = m_granite()
MOSS = m_moss()
SPRIG = m_sprig()


# ============================================================ stone builder
def stone_bm(radii, seed, ex=(1.0, 1.0, 1.0), s1=0.015, f1=1.15, s2=0.007, f2=2.3, cuts=10, taper=0.14, flat=0.3):
    rng = random.Random(seed)
    tp = rng.uniform(-taper, taper)                 # egg-like taper along the long axis
    fa = rng.uniform(0, 2 * math.pi)                # one side worn flatter
    fdir = Vector((math.cos(fa), math.sin(fa), rng.uniform(-0.3, 0.3))).normalized()
    fk = rng.uniform(0.3, 1.0) * flat
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    o1 = Vector([rng.uniform(-40, 40) for _ in range(3)])
    o2 = Vector([rng.uniform(-40, 40) for _ in range(3)])
    rx, ry, rz = radii
    for v in bm.verts:
        x, y, z = v.co
        x2, y2, z2 = x * x, y * y, z * z
        u = Vector((x * math.sqrt(max(0.0, 1 - y2 / 2 - z2 / 2 + y2 * z2 / 3)),
                    y * math.sqrt(max(0.0, 1 - z2 / 2 - x2 / 2 + z2 * x2 / 3)),
                    z * math.sqrt(max(0.0, 1 - x2 / 2 - y2 / 2 + x2 * y2 / 3)))).normalized()
        q = Vector([math.copysign(abs(c) ** e, c) for c, e in zip(u, ex)])
        k = 1.0 + tp * q.z
        fd = u.dot(fdir)
        k *= 1.0 - fk * max(0.0, fd - 0.35) ** 2 / 0.42      # flatten the side facing fdir
        p = Vector((q.x * rx * k, q.y * ry * k, q.z * rz * (1.0 - 0.5 * fk * max(0.0, fd - 0.35) ** 2 / 0.42)))
        n = Vector((u.x / rx, u.y / ry, u.z / rz)).normalized()
        d = s1 * noise.noise(u * f1 + o1) + s2 * noise.noise(u * f2 + o2)
        v.co = p + n * d
    return bm


def stone(name, centre, radii, rot, m, seed, sub=2, **kw):
    bm = stone_bm(radii, seed, **kw)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    rm = rot.to_matrix() if isinstance(rot, Quaternion) else rot
    o.matrix_world = Matrix.Translation(Vector(centre)) @ rm.to_4x4()
    me.materials.append(m)
    sm = o.modifiers.new('sub', 'SUBSURF')
    sm.levels, sm.render_levels = 1, sub
    return o


RNG = random.Random(7)


def jit_rot(base, deg=6.0):
    e = Euler([math.radians(RNG.uniform(-deg, deg)) for _ in range(3)])
    return base @ e.to_matrix()


def jit_off(k=0.015):
    return R @ Vector((RNG.uniform(-k, k), RNG.uniform(-k, k) * 0.6, 0))


def axis_rot(d, roll=None, tilt=4.0):
    d = Vector(d).normalized()
    q = d.to_track_quat('Z', 'Y')
    roll = RNG.uniform(0, 2 * math.pi) if roll is None else roll
    t = Euler((math.radians(RNG.uniform(-tilt, tilt)), math.radians(RNG.uniform(-tilt, tilt)), roll))
    return q.to_matrix() @ t.to_matrix()


# ============================================================ body plan (hero-local, then rotated into the 3/4 turn)
HIP_Z = 0.87
SH_Z = 1.37
S_L, S_R = Vector((0.26, 0.0, SH_Z)), Vector((-0.26, 0.0, SH_Z))
H_L, H_R = Vector((0.11, 0.0, HIP_Z)), Vector((-0.11, 0.0, HIP_Z))
P = POSE_LOCAL


def dirv(a_, b_):
    return (Vector(P[b_]) - Vector(P[a_])).normalized()


# arms: lead fist pushed a little further forward than the base pose so it separates from the torso in the 3/4 view;
# rear elbow tucks in so the short arm still guards the chin
E_L = S_L + Vector((0.05, -0.20, -0.20)).normalized() * 0.26
HA_L = E_L + (Vector((0.20, -0.46, 1.31)) - E_L).normalized() * 0.235
E_R = S_R + Vector((0.02, -0.35, -0.94)).normalized() * 0.26
HA_R = E_R + (Vector((-0.11, -0.27, 1.34)) - E_R).normalized() * 0.25


def ik(hip, ank, l1, l2, hint):
    d = ank - hip
    dl = d.length
    u = d / dl
    if dl >= l1 + l2 - 1e-4:
        return hip + u * l1
    a_ = (l1 * l1 - l2 * l2 + dl * dl) / (2 * dl)
    h = math.sqrt(max(0.0, l1 * l1 - a_ * a_))
    w = (hint - u * hint.dot(u)).normalized()
    return hip + u * a_ + w * h


FOOT = {
    'l': dict(c=Vector((0.22, -0.31, 0.034)), yaw=10.0, hint=Vector((0.25, -1.0, 0.0))),
    'r': dict(c=Vector((-0.26, 0.30, 0.034)), yaw=-38.0, hint=Vector((-0.55, -0.85, 0.0))),
}
for k, f in FOOT.items():
    yaw = math.radians(f['yaw'])
    f['dir'] = Vector((math.sin(yaw), -math.cos(yaw), 0.0))        # toe direction, hero-local
    f['ank'] = f['c'] - f['dir'] * 0.025 + Vector((0, 0, 0.045))   # shin end sinks into the foot slab
LT, LS = 0.42, 0.47
K_L = ik(H_L, FOOT['l']['ank'], LT, LS, FOOT['l']['hint'])
K_R = ik(H_R, FOOT['r']['ank'], LT, LS, FOOT['r']['hint'])


def seg_stone(name, p0, p1, rxy, m, seed, pre=0.0, post=0.0, **kw):
    """pebble whose long axis spans p0-pre .. p1+post (hero-local points)"""
    d = (p1 - p0).normalized()
    a0, a1 = p0 - d * pre, p1 + d * post
    c = (a0 + a1) / 2
    rz = (a1 - a0).length / 2
    r0 = rxy if isinstance(rxy, tuple) else (rxy, rxy)
    rot = R @ axis_rot(d)
    return stone(name, W(c) + jit_off(0.006), (r0[0], r0[1], rz), rot, m, seed, **kw), rz


SEED = iter(range(100, 999))
LOG = {}
# --- torso: three flat basalt slabs, centred on the base spine line
spine0, spine1 = Vector(P['hip']), Vector(P['neck'])


def spine_at(z):
    t = (z - spine0.z) / (spine1.z - spine0.z)
    return spine0.lerp(spine1, t)


TORSO = [('pelvis', 0.93, (0.22, 0.17, 0.092), BASALT, 0.030), ('belly', 1.11, (0.24, 0.175, 0.10), VEIN, 0.022),
         ('chest', 1.305, (0.27, 0.195, 0.12), BASALT, 0.034)]
for nm, zc, rr, mm, s1 in TORSO:
    c = spine_at(zc)
    off = jit_off(0.015) if nm != 'belly' else jit_off(0.008)
    stone(nm, W(c) + off, rr, jit_rot(R, 5.0), mm, next(SEED), ex=(0.88, 0.88, 0.70), s1=s1, f1=1.3, s2=0.006,
          cuts=14, taper=0.0, flat=0.12)

# --- neck pebble + granite head
NECK_Z, HEAD_Z = 1.455, 1.585
stone('neck', W(spine_at(NECK_Z)), (0.075, 0.068, 0.045), jit_rot(R, 6.0), BASALT, next(SEED), s1=0.010, taper=0.0)
HEAD_ROT = R @ Euler((math.radians(4.0), math.radians(-3.0), math.radians(5.0))).to_matrix()
HEAD_C = W(Vector((0.0, -0.005, HEAD_Z)))
head = stone('head', HEAD_C, (0.13, 0.12, 0.15), HEAD_ROT, GRANITE, next(SEED), s1=0.022, f1=1.2, s2=0.005, cuts=16,
             taper=0.08, flat=0.10)

# --- arms: shoulder pebble, upper arm, forearm, fist
for side, S, E, HA in (('l', S_L, E_L, HA_L), ('r', S_R, E_R, HA_R)):
    stone('shoulder_' + side, W(S) + jit_off(0.005), (0.088, 0.08, 0.078), jit_rot(R, 8.0), BASALT, next(SEED), s1=0.016)
    _, rz = seg_stone('uparm_' + side, S, E, (0.08, 0.064), BASALT, next(SEED), pre=-0.04, post=-0.005, s1=0.02, ex=(0.85, 0.85, 0.95))
    LOG['uparm_rz_' + side] = rz
    _, rz = seg_stone('forearm_' + side, E, HA, (0.072, 0.06), BASALT, next(SEED), pre=-0.012, post=-0.01, s1=0.018, ex=(0.85, 0.85, 0.95))
    LOG['forearm_rz_' + side] = rz
    d2 = (HA - E).normalized()
    hc = HA + d2 * 0.058
    stone('fist_' + side, W(hc), (0.068, 0.054, 0.084), R @ axis_rot(d2, roll=math.radians(90 if side == 'l' else -60)),
          BASALT, next(SEED), s1=0.014)

# --- legs: thigh, knee pebble, shin, flat foot slab
for side, H, K in (('l', H_L, K_L), ('r', H_R, K_R)):
    f = FOOT[side]
    _, rz = seg_stone('thigh_' + side, H, K, (0.115, 0.088), BASALT, next(SEED), pre=0.04, post=-0.05, s1=0.03, ex=(0.85, 0.85, 0.95))
    LOG['thigh_rz_' + side] = rz
    stone('knee_' + side, W(K), (0.092, 0.086, 0.08), jit_rot(R, 8.0), BASALT, next(SEED), s1=0.016)
    _, rz = seg_stone('shin_' + side, K, f['ank'], (0.098, 0.076), BASALT, next(SEED), pre=-0.05, post=0.0, s1=0.026, ex=(0.85, 0.85, 0.95))
    LOG['shin_rz_' + side] = rz
    fy = math.atan2(f['dir'].x, -f['dir'].y)
    frot = R @ Matrix.Rotation(-fy, 3, 'Z') @ Euler((math.radians(RNG.uniform(-2, 2)), math.radians(RNG.uniform(-2, 2)), 0)).to_matrix()
    stone('foot_' + side, W(f['c']), (0.085, 0.145, 0.042), frot, BASALT, next(SEED), ex=(0.82, 0.82, 0.55), s1=0.016,
          taper=0.12, flat=0.0)

# ============================================================ moss cushion on the head (SIGNATURE 1)
def build_moss():
    bm = bmesh.new()
    bm.from_mesh(head.data)
    # head-local axis leaning 10 deg toward his facing (local -y)
    ax = Vector((0.0, -math.sin(math.radians(10)), math.cos(math.radians(10))))
    top = max(ax.dot(v.co) for v in bm.verts)
    thr = top - 0.036
    o3 = Vector((11.3, -7.1, 3.7))
    edge_n = lambda co: 0.005 * noise.noise(co * 35 + o3)
    dead = [f for f in bm.faces if all(ax.dot(v.co) < thr - 0.008 for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    bm.normal_update()
    lay = bm.verts.layers.float.new('moss_h')
    o1, o2 = Vector((3.1, 8.2, -5.5)), Vector((-12.4, 4.4, 9.9))
    pts = []
    for v in bm.verts:
        co = v.co.copy()
        h = ax.dot(co) - (thr + edge_n(co))
        w = smooth(-0.004, 0.012, h)
        n1 = noise.noise(co * 25 + o1) * 0.5 + 0.5
        f1 = noise.voronoi(co * 40 + o2, distance_metric='DISTANCE', exponent=2.5)[0][0]
        v1 = max(0.0, 1.0 - f1 * 1.25)
        n3 = noise.noise(co * 90 + o2)
        cush = 0.008 + 0.014 * n1 + 0.009 * v1 + 0.0018 * n3
        dome = math.sqrt(w)
        v.co = co + v.normal * (-0.0035 + dome * cush)
        v[lay] = min(1.0, max(0.0, (0.35 * n1 + 0.65 * v1) * (0.3 + 0.7 * w)))
        if w > 0.85:
            pts.append((v.co.copy(), v.normal.copy()))
    me = bpy.data.meshes.new('moss')
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    o = bpy.data.objects.new('moss', me)
    sc.collection.objects.link(o)
    o.matrix_world = head.matrix_world.copy()
    me.materials.append(MOSS)
    sm = o.modifiers.new('sub', 'SUBSURF')
    sm.levels, sm.render_levels = 1, 1
    # 7 tiny bent sprigs
    rng = random.Random(5)
    sb = bmesh.new()
    picks = rng.sample(pts, min(7, len(pts)))
    for co, n in picks:
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=True, cap_tris=False, segments=6, radius1=0.006, radius2=0.0012, depth=0.025)
        bend = rng.uniform(0.004, 0.009)
        for v in tmp.verts:
            t = (v.co.z + 0.0125) / 0.025
            v.co.z += 0.0125
            v.co.x += bend * t * t
        d = (n + ax * 0.6 + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0))).normalized()
        mtx = Matrix.Translation(co - n * 0.003) @ (d.to_track_quat('Z', 'Y') @ Quaternion(Z, rng.uniform(0, 6.28))).to_matrix().to_4x4()
        bmesh.ops.transform(tmp, matrix=mtx, verts=tmp.verts[:])
        tm = bpy.data.meshes.new('tmp')
        tmp.to_mesh(tm)
        tmp.free()
        sb.from_mesh(tm)
        bpy.data.meshes.remove(tm)
    sme = bpy.data.meshes.new('sprigs')
    sb.to_mesh(sme)
    sb.free()
    sme.shade_smooth()
    so = bpy.data.objects.new('sprigs', sme)
    sc.collection.objects.link(so)
    so.matrix_world = head.matrix_world.copy()
    sme.materials.append(SPRIG)
    top_w = max((head.matrix_world @ v.co).z for v in me.vertices)
    LOG['moss_top'] = round(top_w, 3)


build_moss()


# ============================================================ raked white gravel patch (thumbnail hook)
def build_gravel():
    X0, X1, Y0, Y1 = -1.35, 1.35, -1.5, 1.85
    NX, NY = 300, 370
    spacing, amp = 0.072, 0.012
    U = Vector((-0.348, 0.937, 0.0)).normalized()      # rake direction: away from the camera
    Pp = Vector((U.y, -U.x, 0.0))
    feet = []
    for k in ('l', 'r'):
        f = FOOT[k]
        feet.append((W(f['c']), W(f['dir'])))
    r_in, n_ring = 0.15, 3
    r_out = r_in + spacing * n_ring
    on = Vector((5.5, 2.2, 0.0))

    def ridge(t):
        return (0.5 + 0.5 * math.cos(2 * math.pi * t)) ** 1.4

    def height(x, y):
        p = Vector((x, y, 0.0))
        best = 9.0
        for c, d in feet:
            q = p - c
            t = max(-0.07, min(0.07, q.dot(d)))
            r = (q - d * t).length
            best = min(best, r)
        jitter = 0.006 * noise.noise(p * 2.5 + on) + 0.0015 * noise.noise(p * 14 + on)
        if best < r_in:
            return 0.0
        if best < r_out:
            return ridge((best - r_in) / spacing + 0.5 + jitter / spacing) * smooth(r_in, r_in + 0.02, best)
        psi = (p.dot(Pp))
        for c, d in feet:
            q = p - c
            r2 = max(q.length_squared, 1e-6)
            psi -= (r_out ** 2) * q.dot(Pp) / r2
        return ridge(psi / spacing + jitter / spacing)

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=NX, y_segments=NY, size=1.0)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys)
    for v in bm.verts:
        x = X0 + (v.co.x - mnx) / (mxx - mnx) * (X1 - X0)
        y = Y0 + (v.co.y - mny) / (mxy - mny) * (Y1 - Y0)
        p = Vector((x, y, 0))
        z = 0.004 + amp * height(x, y) + 0.0012 * noise.noise(p * 60 + on)
        v.co = Vector((x, y, z))
    me = bpy.data.meshes.new('gravel')
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    o = bpy.data.objects.new('gravel', me)
    sc.collection.objects.link(o)
    me.materials.append(m_gravel())
    # dark timber edging
    ed = wood_mat('edging', (0.055, 0.032, 0.018), 9.0, rough=0.5)
    wdt, hgt = 0.07, 0.045
    for cx, cy, sx, sy in (((X0 + X1) / 2, Y1 + wdt / 2, X1 - X0 + 2 * wdt, wdt), ((X0 + X1) / 2, Y0 - wdt / 2, X1 - X0 + 2 * wdt, wdt),
                           (X0 - wdt / 2, (Y0 + Y1) / 2, wdt, Y1 - Y0), (X1 + wdt / 2, (Y0 + Y1) / 2, wdt, Y1 - Y0)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, hgt / 2))
        b = bpy.context.object
        b.scale = (sx, sy, hgt)
        b.data.materials.append(ed)
        bv = b.modifiers.new('bv', 'BEVEL')
        bv.width, bv.segments = 0.006, 2


build_gravel()


# ============================================================ mooks: RUBBLE (angular quarry-granite men), out of focus behind
RUB = m_rubble()
RUB_OBJS = []


def block(name, size, centre, rot, m, seed, j=0.04, cuts=2, bevel=0.008, grooves=None, parent=None):
    rng = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    j = min(j, min(size) / (cuts + 1) * 0.35)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector([rng.uniform(-j, j) for _ in range(3)])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.matrix_world = Matrix.Translation(Vector(centre)) @ rot.to_4x4()
    me.materials.append(m)
    RUB_OBJS.append(o)
    if grooves:
        for gi, (gp, gr, gl) in enumerate(grooves):
            bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=gr, depth=gl, location=(0, 0, 0))
            cyl = bpy.context.object
            cyl.matrix_world = o.matrix_world @ Matrix.Translation(Vector(gp))
            cyl.hide_render = True
            cyl.hide_viewport = True
            RUB_OBJS.append(cyl)
            bo = o.modifiers.new('groove%d' % gi, 'BOOLEAN')
            bo.object, bo.operation, bo.solver = cyl, 'DIFFERENCE', 'EXACT'
    bv = o.modifiers.new('bevel', 'BEVEL')
    bv.width, bv.segments, bv.limit_method = bevel, 1, 'ANGLE'
    bv.angle_limit = math.radians(25)
    return o


def rubble_man(base, yaw_deg, seed, lean=6.0, arms='up', topple=0.0, roll=0.0):
    first = len(RUB_OBJS)
    Rm = (Matrix.Rotation(math.radians(yaw_deg), 3, 'Z') @ Matrix.Rotation(math.radians(topple), 3, 'Y')
          @ Matrix.Rotation(math.radians(lean + roll), 3, 'X'))
    rr = random.Random(seed)

    def P_(p):
        return Vector(base) + Rm @ Vector(p)

    def rot(extra=(0, 0, 0)):
        return Rm @ Euler([math.radians(e + rr.uniform(-4, 4)) for e in extra]).to_matrix()

    s = next(SEED)
    grooves = [((-0.17 + 0.075 * i, -0.17, 0.12), 0.012, 0.36) for i in range(4)]
    block('rub_torso', (0.48, 0.34, 0.58), P_((0, 0, 1.09)), rot(), RUB, s, j=0.04, grooves=grooves)
    block('rub_head', (0.22, 0.22, 0.22), P_((0.01, -0.02, 1.49)), rot((0, 0, 8)), RUB, next(SEED), j=0.03)
    for sx in (1, -1):
        block('rub_thigh', (0.16, 0.16, 0.36), P_((sx * 0.13, 0.0, 0.64)), rot((0, sx * -4, 0)), RUB, next(SEED), j=0.025)
        block('rub_shin', (0.14, 0.14, 0.36), P_((sx * 0.15, -0.02, 0.27)), rot(), RUB, next(SEED), j=0.022)
        block('rub_foot', (0.15, 0.24, 0.09), P_((sx * 0.15, -0.06, 0.05)), rot(), RUB, next(SEED), j=0.015)
        block('rub_upper', (0.14, 0.14, 0.30), P_((sx * 0.32, -0.02, 1.18)), rot((0, sx * -12, 0)), RUB, next(SEED), j=0.025)
        if arms == 'up':
            block('rub_fore', (0.13, 0.13, 0.28), P_((sx * 0.34, -0.17, 1.05)), rot((65, 0, 0)), RUB, next(SEED), j=0.022)
            block('rub_fist', (0.14, 0.14, 0.14), P_((sx * 0.33, -0.31, 1.03)), rot(), RUB, next(SEED), j=0.02)
        else:
            block('rub_fore', (0.13, 0.13, 0.28), P_((sx * 0.37, -0.03, 0.88)), rot((0, sx * -6, 0)), RUB, next(SEED), j=0.022)
            block('rub_fist', (0.15, 0.15, 0.15), P_((sx * 0.38, -0.04, 0.70)), rot(), RUB, next(SEED), j=0.02)
    # whole rigid figure rests on the floor (toppled ones lie on their side)
    objs = RUB_OBJS[first:]
    minz = min((o.matrix_world @ v.co).z for o in objs if not o.hide_render for v in o.data.vertices)
    for o in objs:
        o.matrix_world = Matrix.Translation((0, 0, -minz - 0.004)) @ o.matrix_world
    return objs


# one standing (facing the hero), one already toppled flat on its back, lying away from the camera
MOOKS = [((-0.30, 3.80, 0.0), 31, 'up', 0.0, 0.0, None), ((-1.81, 2.0, 0.0), 47, 'down', 10.0, -91.0, CAM['loc'])]
for mp, sd, arms, tp, rl, look in MOOKS:
    tgt = Vector(look) if look else Vector((0, 0, 0))
    d = Vector((tgt.x - mp[0], tgt.y - mp[1], 0)).normalized()
    psi = math.degrees(math.atan2(d.x, -d.y))
    rubble_man(mp, psi, sd, lean=5.0 if arms == 'up' else 3.0, arms=arms, topple=tp, roll=rl)


# ============================================================ extra lights: warm low raking key + cool rim from behind-left
def spot(loc, tgt, energy, col, size_deg, soft):
    bpy.ops.object.light_add(type='SPOT', location=loc)
    l = bpy.context.object
    l.data.energy, l.data.color = energy, col
    l.data.spot_size = math.radians(size_deg)
    l.data.spot_blend = 0.6
    l.data.shadow_soft_size = soft
    l.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return l


def area(loc, tgt, energy, col, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    l = bpy.context.object
    l.data.energy, l.data.color, l.data.size = energy, col, size
    l.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return l


spot((-2.7, -1.0, 1.25), (0.0, 0.0, 0.95), 650, (1.0, 0.74, 0.50), 30, 0.06)
spot((-1.3, 2.4, 2.3), (0.0, 0.0, 1.15), 900, (0.55, 0.70, 1.0), 22, 0.25)

cam = sc.camera
cam.data.dof.focus_distance = (HEAD_C - Vector((0, 0, 0.35)) - cam.location).length
sc.cycles.glossy_bounces = 4
sc.cycles.transmission_bounces = 2

print('ISHI', {k: round(v, 3) if isinstance(v, float) else v for k, v in LOG.items()})
if os.environ.get('ISHI_DRY'):
    from bpy_extras.object_utils import world_to_camera_view
    dg = bpy.context.evaluated_depsgraph_get()
    def frame_box(objs):
        xs, ys = [], []
        for o in objs:
            if o.hide_render or o.type != 'MESH':
                continue
            for v in o.data.vertices:
                c = world_to_camera_view(sc, cam, o.matrix_world @ v.co)
                xs.append(c.x); ys.append(c.y)
        return round(min(xs), 3), round(max(xs), 3), round(1 - max(ys), 3), round(1 - min(ys), 3)
    hero = [o for o in sc.objects if o.type == 'MESH' and o.name.split('.')[0].split('_')[0] in
            ('pelvis', 'belly', 'chest', 'neck', 'head', 'moss', 'sprigs', 'shoulder', 'uparm', 'forearm', 'fist', 'thigh', 'knee', 'shin', 'foot')]
    print('hero frame x0 x1 top bottom', frame_box(hero))
    print('fist_l', frame_box([o for o in hero if o.name.startswith('fist_l')]))
    print('knee_l', frame_box([o for o in hero if o.name.startswith('knee_l') or o.name.startswith('shin_l')]))
    rub = [o for o in RUB_OBJS]
    n = len(rub) // 2
    print('mook A', frame_box(rub[:n]), 'mook B', frame_box(rub[n:]))
    sys.exit(0)
bd = os.environ.get('ISHI_BORDER')      # optional detail check: render a region only (fractions x0,y0,x1,y1)
if bd:
    x0, y0, x1, y1 = (float(v) for v in bd.split(','))
    sc.render.use_border = True
    sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = x0, y0, x1, y1
finish(a)
