import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from base import *
a = setup(); stage(); J = pose()   # J: joint positions, hero at origin, 3/4 to camera
# TOKEI - brass clockwork automaton. Built in the hero's local frame (facing -y, left = +x), then turned by YAW.
import bmesh
import random

sc = bpy.context.scene
sc.cycles.max_bounces = 8                 # glass dome + ruby eyes need a few more transmission bounces
sc.cycles.transmission_bounces = 8
sc.cycles.transparent_max_bounces = 12
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False

YAW = -45.0
RW = Matrix.Rotation(math.radians(YAW), 4, 'Z')
T_CHEST, T_HEAD, T_PELVIS = 22.0, 32.0, -22.0  # chest opened toward the camera; hips bladed so the legs read as a stance, not an X

HERO = bpy.data.collections.new('tokei_parts')
sc.collection.children.link(HERO)
DOMEC = bpy.data.collections.new('tokei_dome')
MOOKC = bpy.data.collections.new('tokei_mooks')
sc.collection.children.link(MOOKC)


# ---------------------------------------------------------------- helpers
def empty(name, parent=None, M=None, coll=HERO):
    o = bpy.data.objects.new(name, None)
    coll.objects.link(o)
    if parent is not None:
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
    if M is not None:
        o.matrix_basis = M
    return o


def add_obj(name, me, m, parent, M=None, coll=HERO):
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    for mm in (m if isinstance(m, (list, tuple)) else [m]):
        if mm is not None:
            o.data.materials.append(mm)
    if parent is not None:
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
    if M is not None:
        o.matrix_basis = M
    return o


def frame(origin, z_dir, x_hint=None):
    z = Vector(z_dir).normalized()
    if x_hint is None:
        R = z.to_track_quat('Z', 'Y').to_matrix()
    else:
        x = Vector(x_hint)
        x = (x - x.dot(z) * z).normalized()
        y = z.cross(x)
        R = Matrix((x, y, z)).transposed()
    M = R.to_4x4()
    M.translation = Vector(origin)
    return M


def rotz(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def bm_mesh(bm, name, smooth=True, sharp=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    if sharp is not None:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    return me


def bev(o, w, seg=2, ang=30, harden=True):
    md = o.modifiers.new('bev', 'BEVEL')
    md.width = w
    md.segments = seg
    md.limit_method = 'ANGLE'
    md.angle_limit = math.radians(ang)
    md.harden_normals = harden
    return md


def cyl_me(name, r, depth, segs=32, r2=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r,
                          radius2=r if r2 is None else r2, depth=depth)
    return bm_mesh(bm, name, sharp=30)


def cylinder(name, c, axis, r, depth, m, parent, segs=32, bevel=0.0015, r2=None, x_hint=None):
    o = add_obj(name, cyl_me(name, r, depth, segs, r2), m, parent, frame(c, axis, x_hint))
    if bevel:
        bev(o, bevel)
    return o


def tube(name, p0, p1, r, m, parent, r1=None, segs=28):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    return cylinder(name, (p0 + p1) / 2, d, r, d.length, m, parent, segs, bevel=0.0012,
                    r2=None if r1 is None else r1)


def ellipsoid_me(name, rx, ry, rz, segs=48, rings=24, fn=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    for v in bm.verts:
        co = Vector((v.co.x * rx, v.co.y * ry, v.co.z * rz))
        v.co = fn(co) if fn else co
    return bm_mesh(bm, name)


def ellipsoid(name, c, radii, m, parent, M=None, segs=48, rings=24):
    o = add_obj(name, ellipsoid_me(name, *radii, segs=segs, rings=rings), m, parent)
    o.matrix_basis = M if M is not None else Matrix.Translation(Vector(c))
    return o


def sweep_me(name, pts, nrm, bin_, r, rsegs=14, closed=True):
    bm = bmesh.new()
    rings = []
    for P, N, B in zip(pts, nrm, bin_):
        rings.append([bm.verts.new(P + r * (math.cos(v) * N + math.sin(v) * B))
                      for v in [2 * math.pi * k / rsegs for k in range(rsegs)]])
    n = len(rings)
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        for k in range(rsegs):
            l = (k + 1) % rsegs
            bm.faces.new((rings[i][k], rings[j][k], rings[j][l], rings[i][l]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm_mesh(bm, name)


def torus_me(name, R, r, segs=64, rsegs=14, ax=1.0, az=1.0):
    us = [2 * math.pi * k / segs for k in range(segs)]
    pts = [Vector((R * ax * math.cos(u), R * az * math.sin(u), 0)) for u in us]
    nrm = [Vector((math.cos(u) / ax, math.sin(u) / az, 0)).normalized() for u in us]
    return sweep_me(name, pts, nrm, [Vector((0, 0, 1))] * segs, r, rsegs)


def torus(name, c, axis, R, r, m, parent, segs=64, rsegs=14):
    return add_obj(name, torus_me(name, R, r, segs, rsegs), m, parent, frame(c, axis))


def lathe_me(name, prof, segs=64):
    bm = bmesh.new()
    rings = []
    for r, z in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z))
                          for k in range(segs)])
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(segs):
            l = (k + 1) % segs
            if len(B) == 1:
                bm.faces.new((A[k], A[l], B[0]))
            elif len(A) == 1:
                bm.faces.new((A[0], B[l], B[k]))
            else:
                bm.faces.new((A[k], A[l], B[l], B[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm_mesh(bm, name)


# ---------------------------------------------------------------- materials
def node(nt, t, loc=None, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    return m, nt, nt.nodes['Principled BSDF']


def brass_mat(name, base=(0.89, 0.70, 0.33), rough=0.18, var=0.08, smudge=True, aniso=0.0):
    m, nt, b = principled(name)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Base Color'].default_value = (*base, 1)
    tc = node(nt, 'ShaderNodeTexCoord')
    nz = node(nt, 'ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 40
    nz.inputs['Detail'].default_value = 3
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = node(nt, 'ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.3
    mr.inputs['From Max'].default_value = 0.7
    mr.inputs['To Min'].default_value = rough - var
    mr.inputs['To Max'].default_value = rough + var
    nt.links.new(nz.outputs['Fac'], mr.inputs['Value'])
    out = mr.outputs['Result']
    if smudge:   # three-ish faint fingerprint smudges: sparse voronoi blobs x ridge rings
        vo = node(nt, 'ShaderNodeTexVoronoi')
        vo.inputs['Scale'].default_value = 2.2
        vo.inputs['Randomness'].default_value = 1.0
        nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
        blob = node(nt, 'ShaderNodeMapRange')
        blob.inputs['From Min'].default_value = 0.06
        blob.inputs['From Max'].default_value = 0.0
        nt.links.new(vo.outputs['Distance'], blob.inputs['Value'])
        wv = node(nt, 'ShaderNodeTexWave', wave_type='RINGS')
        wv.rings_direction = 'SPHERICAL'
        wv.inputs['Scale'].default_value = 260
        wv.inputs['Distortion'].default_value = 3
        nt.links.new(tc.outputs['Object'], wv.inputs['Vector'])
        m1 = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
        nt.links.new(blob.outputs['Result'], m1.inputs[0])
        nt.links.new(wv.outputs['Fac'], m1.inputs[1])
        m2 = node(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD')
        nt.links.new(m1.outputs[0], m2.inputs[0])
        m2.inputs[1].default_value = 0.1
        nt.links.new(out, m2.inputs[2])
        out = m2.outputs[0]
    nt.links.new(out, b.inputs['Roughness'])
    if aniso:
        b.inputs['Anisotropic'].default_value = aniso
    return m


def blued_mat(name='blued', rough=0.2):
    m, nt, b = principled(name)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Base Color'].default_value = (0.05, 0.10, 0.36, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Anisotropic'].default_value = 0.3
    return m


def perlage_mat(name):
    m = brass_mat(name, base=(0.66, 0.45, 0.18), rough=0.27, var=0.02, smudge=False)
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = [n for n in nt.nodes if n.type == 'TEX_COORD'][0]
    vo = node(nt, 'ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 60
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    mr = node(nt, 'ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.0
    mr.inputs['From Max'].default_value = 0.6
    mr.inputs['To Min'].default_value = 0.2
    mr.inputs['To Max'].default_value = 0.35
    nt.links.new(vo.outputs['Distance'], mr.inputs['Value'])
    nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
    bp = node(nt, 'ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.25
    bp.inputs['Distance'].default_value = 0.0004
    nt.links.new(vo.outputs['Distance'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def engine_turned_mat(name):
    m = brass_mat(name, rough=0.2, var=0.05)
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = [n for n in nt.nodes if n.type == 'TEX_COORD'][0]
    sp = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sp.inputs[0])
    at = node(nt, 'ShaderNodeMath', operation='ARCTAN2')
    nt.links.new(sp.outputs['Y'], at.inputs[0])
    nt.links.new(sp.outputs['X'], at.inputs[1])
    mu = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(at.outputs[0], mu.inputs[0])
    mu.inputs[1].default_value = 24
    sn = node(nt, 'ShaderNodeMath', operation='SINE')
    nt.links.new(mu.outputs[0], sn.inputs[0])
    ad = node(nt, 'ShaderNodeMath', operation='MULTIPLY_ADD')
    nt.links.new(sn.outputs[0], ad.inputs[0])
    ad.inputs[1].default_value = 0.0025
    nt.links.new(sp.outputs['Z'], ad.inputs[2])
    cb = node(nt, 'ShaderNodeCombineXYZ')
    nt.links.new(ad.outputs[0], cb.inputs['Z'])
    wb = node(nt, 'ShaderNodeTexWave', wave_type='BANDS')
    wb.bands_direction = 'Z'
    wb.wave_profile = 'SAW'
    wb.inputs['Scale'].default_value = 75
    nt.links.new(cb.outputs[0], wb.inputs['Vector'])
    wr = node(nt, 'ShaderNodeTexWave', wave_type='RINGS')
    wr.rings_direction = 'Z'
    wr.wave_profile = 'SAW'
    wr.inputs['Scale'].default_value = 75
    nt.links.new(tc.outputs['Object'], wr.inputs['Vector'])
    gm = node(nt, 'ShaderNodeNewGeometry')
    sn2 = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(gm.outputs['Normal'], sn2.inputs[0])
    ab = node(nt, 'ShaderNodeMath', operation='ABSOLUTE')
    nt.links.new(sn2.outputs['Z'], ab.inputs[0])
    mx = node(nt, 'ShaderNodeMix', data_type='FLOAT')
    nt.links.new(ab.outputs[0], mx.inputs['Factor'])
    nt.links.new(wb.outputs['Fac'], mx.inputs['A'])
    nt.links.new(wr.outputs['Fac'], mx.inputs['B'])
    bp = node(nt, 'ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.35
    bp.inputs['Distance'].default_value = 0.0006
    nt.links.new(mx.outputs['Result'], bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def glass_mat(name, col=(0.97, 0.985, 1.0), ior=1.45, emit=0.0, shadow_clear=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    out = nt.nodes['Material Output']
    g = node(nt, 'ShaderNodeBsdfGlass')
    g.distribution = 'GGX'
    g.inputs['Color'].default_value = (*col, 1)
    g.inputs['IOR'].default_value = ior
    g.inputs['Roughness'].default_value = 0.0
    sh = g.outputs[0]
    if emit:
        em = node(nt, 'ShaderNodeEmission')
        em.inputs['Color'].default_value = (*col, 1)
        em.inputs['Strength'].default_value = emit
        ad = node(nt, 'ShaderNodeAddShader')
        nt.links.new(sh, ad.inputs[0])
        nt.links.new(em.outputs[0], ad.inputs[1])
        sh = ad.outputs[0]
    if shadow_clear:
        lp = node(nt, 'ShaderNodeLightPath')
        tr = node(nt, 'ShaderNodeBsdfTransparent')
        mx = node(nt, 'ShaderNodeMixShader')
        nt.links.new(lp.outputs['Is Shadow Ray'], mx.inputs['Fac'])
        nt.links.new(sh, mx.inputs[1])
        nt.links.new(tr.outputs[0], mx.inputs[2])
        sh = mx.outputs[0]
    nt.links.new(sh, out.inputs['Surface'])
    return m


BRASS = brass_mat('brass')
BRASS_POL = brass_mat('brass_polished', base=(0.93, 0.74, 0.36), rough=0.08, var=0.03)
BRASS_SAT = brass_mat('brass_satin', base=(0.86, 0.66, 0.30), rough=0.26, var=0.06)
BRASS_IN = brass_mat('brass_inside', base=(0.60, 0.40, 0.16), rough=0.3, var=0.05, smudge=False)
GEARM = brass_mat('gear_brass', base=(0.95, 0.76, 0.38), rough=0.12, var=0.04, smudge=False)
PLATE = perlage_mat('movement_plate')
TURNED = engine_turned_mat('engine_turned')
BLUED = blued_mat('blued')
SCREWM = blued_mat('blued_screw', rough=0.12)
RUBY = glass_mat('ruby', (0.80, 0.03, 0.06), 1.76, emit=0.2)
RUBY_EYE = glass_mat('ruby_eye', (0.80, 0.03, 0.06), 1.76, emit=0.35)
RUBY_EYE.node_tree.nodes['Emission'].inputs['Color'].default_value = (0.62, 0.008, 0.025, 1)   # deeper red under AgX
GLASS = glass_mat('glass_dome')

# ---------------------------------------------------------------- frames
root = empty('TOKEI', M=RW)
CH = empty('chest_frame', root, rotz(T_CHEST))
HD = empty('head_frame', root, rotz(T_HEAD))
PV = empty('pelvis_frame', root, rotz(T_PELVIS))
M_CH, M_PV = rotz(T_CHEST), rotz(T_PELVIS)


def screw(name, c, axis, parent, r=0.010, h=0.004, slot_deg=None):
    """Blued screw head: two domed halves with a slot between them, plus a base disc."""
    axis = Vector(axis).normalized()
    bm = bmesh.new()
    g = r * 0.16
    n = 14
    base_h = h * 0.35
    for s in (-1, 1):
        ring_b, ring_t = [], []
        for k in range(n + 1):
            t = -math.pi / 2 + math.pi * k / n
            x, y = r * math.cos(t) * s, r * math.sin(t)
            x = s * max(abs(x), g / 2)
            ring_b.append(bm.verts.new((x, y, base_h)))
            ring_t.append(bm.verts.new((x * 0.88, y * 0.88, h)))
        bm.faces.new(ring_t if s > 0 else list(reversed(ring_t)))
        bm.faces.new(list(reversed(ring_b)) if s > 0 else ring_b)
        for k in range(n):
            bm.faces.new((ring_b[k], ring_b[k + 1], ring_t[k + 1], ring_t[k]))
        bm.faces.new((ring_b[-1], ring_b[0], ring_t[0], ring_t[-1]))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r, radius2=r, depth=base_h,
                          matrix=Matrix.Translation((0, 0, base_h / 2)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bm_mesh(bm, name, sharp=30)
    rnd = random.Random(hash(name) & 0xffff)
    xh = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
    if abs(xh.normalized().dot(axis)) > 0.9:
        xh = Vector((1, 0.3, 0.2))
    return add_obj(name, me, SCREWM, parent, frame(c, axis, xh))


def pivot(name, c, axis, parent, tube_r, hub_r=None, cheek_r=0.034, cheek_w=0.007, sides=(-1, 1)):
    """Brass hinge: hub across the tube, a pivot disc on each side, blued screw in the centre."""
    c, axis = Vector(c), Vector(axis).normalized()
    hub_r = hub_r or tube_r + 0.004
    hub_w = 2 * tube_r + 0.004
    cylinder(name + '_hub', c, axis, hub_r, hub_w, BRASS_SAT, parent, 32, 0.0012)
    for s in sides:
        cc = c + axis * s * (hub_w / 2 + cheek_w / 2)
        cylinder(name + '_disc%d' % s, cc, axis, cheek_r, cheek_w, BRASS, parent, 40, 0.0016)
        screw(name + '_screw%d' % s, c + axis * s * (hub_w / 2 + cheek_w - 0.0005), axis * s, parent)


def ferrule(name, p, d, r, parent):
    d = Vector(d).normalized()
    cylinder(name, p, d, r + 0.003, 0.012, BRASS_POL, parent, 32, 0.001)


def ik(S, W, L1, L2, pole):
    S, W = Vector(S), Vector(W)
    d = W - S
    D = min(d.length, (L1 + L2) * 0.995)
    dn = d.normalized()
    a_ = (L1 * L1 - L2 * L2 + D * D) / (2 * D)
    h = math.sqrt(max(L1 * L1 - a_ * a_, 0.0))
    pv = Vector(pole)
    pv = (pv - pv.dot(dn) * dn).normalized()
    return S + dn * a_ + pv * h, S + dn * D


# ---------------------------------------------------------------- gears
def gear_me(name, r, N, spokes=5, phase=0.0, tooth_h=0.007, tip=0.36, base=0.62, rim_w=None, hub_r=None,
            axle_r=0.0, hub=True):
    bm = bmesh.new()
    P = 2 * math.pi / N
    ro, rr = r + tooth_h / 2, r - tooth_h / 2
    rim_w = rim_w or max(0.0045, 0.12 * r)
    ri = rr - rim_w
    hub_r = hub_r or max(0.006, 0.2 * r)
    keys = [(-0.5, rr), (-base / 2, rr), (-tip / 2, ro), (tip / 2, ro), (base / 2, rr)]
    outer, inner = [], []
    for k in range(N):
        for f, rad in keys:
            ang = phase + (k + f) * P
            outer.append(bm.verts.new((rad * math.cos(ang), rad * math.sin(ang), 0)))
            inner.append(bm.verts.new((ri * math.cos(ang), ri * math.sin(ang), 0)))
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((inner[i], inner[j], outer[j], outer[i]))
    # hub (annulus or disc)
    hs = 24
    hv = [] if not hub else [bm.verts.new((hub_r * math.cos(2 * math.pi * k / hs), hub_r * math.sin(2 * math.pi * k / hs), 0)) for k in range(hs)]
    if not hub:
        pass
    elif axle_r > 0:
        av = [bm.verts.new((axle_r * math.cos(2 * math.pi * k / hs), axle_r * math.sin(2 * math.pi * k / hs), 0)) for k in range(hs)]
        for k in range(hs):
            l = (k + 1) % hs
            bm.faces.new((av[k], av[l], hv[l], hv[k]))
    else:
        bm.faces.new(hv)
    # spokes
    sw = max(0.0032, 0.11 * r)
    for s in range(spokes):
        ang = phase + 2 * math.pi * s / spokes + P * 0.25
        u = Vector((math.cos(ang), math.sin(ang), 0))
        w = Vector((-u.y, u.x, 0)) * (sw / 2)
        r0, r1 = hub_r * 0.85, ri + 0.0012
        q = [u * r0 - w, u * r1 - w * 0.8, u * r1 + w * 0.8, u * r0 + w]
        bm.faces.new([bm.verts.new(v) for v in q])
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    return bm_mesh(bm, name, smooth=False)


def gear(name, c, axis, r, N, th, m, parent, spokes=5, phase=0.0, x_hint=(1, 0, 0), **kw):
    o = add_obj(name, gear_me(name, r, N, spokes, phase, **kw), m, parent, frame(c, axis, x_hint))
    sd = o.modifiers.new('solid', 'SOLIDIFY')
    sd.thickness = th
    sd.offset = 0.0
    sd.use_even_offset = True
    bev(o, 0.0005, 1, 35, harden=False)
    return o


# ================================================================= BODY LAYOUT (hero-local metres)
Z_HIP, Z_DRUM = 0.86, 0.87
C_CH = Vector((0.0, 0.0, 1.215))       # chest case centre
CA, CB, CC = 0.14, 0.065, 0.17         # case semi axes (x, y, z)
Z_DOME0 = 1.43                         # dome base ring

# ---------------------------------------------------------------- HEAD (head frame)
H_DISC = Z_DOME0 + 0.0075
cylinder('head_floor', (0, 0, H_DISC), (0, 0, 1), 0.12, 0.015, TURNED, HD, 64, 0.002)
torus('head_ring', (0, 0, Z_DOME0 + 0.007), (0, 0, 1), 0.122, 0.012, BRASS_POL, HD, 72, 16)
DH, DR = 0.25, 0.118
prof = []
for i in range(25):
    t = i / 24
    z = DH * (1 - (1 - t) ** 1.6)
    r = DR * max(0.0, 1 - (z / DH) ** 2.6) ** (1 / 2.6)
    prof.append((r, z))
prof[-1] = (0.0, DH)
dome = add_obj('dome', lathe_me('dome', prof, 72), GLASS, HD, Matrix.Translation((0, 0, Z_DOME0 + 0.012)))
sd = dome.modifiers.new('solid', 'SOLIDIFY')
sd.thickness = 0.004
sd.offset = 1.0
sd.use_even_offset = True
DOMEC.objects.link(dome)
Z_DTOP = Z_DOME0 + 0.012 + DH
cylinder('crown_stem', (0, 0, Z_DTOP + 0.008), (0, 0, 1), 0.008, 0.024, BRASS_POL, HD, 24, 0.0008)
cylinder('crown_collar', (0, 0, Z_DTOP + 0.001), (0, 0, 1), 0.014, 0.006, BRASS_POL, HD, 32, 0.001)
# knurled crown: 32 sides, every other vertex pushed out 1.5 mm
bm = bmesh.new()
ncr, crr, crh = 32, 0.024, 0.026
bot = [bm.verts.new(((crr + (0.0015 if k % 2 else 0)) * math.cos(2 * math.pi * k / ncr),
                     (crr + (0.0015 if k % 2 else 0)) * math.sin(2 * math.pi * k / ncr), 0)) for k in range(ncr)]
top = [bm.verts.new((v.co.x, v.co.y, crh)) for v in bot]
for k in range(ncr):
    l = (k + 1) % ncr
    bm.faces.new((bot[k], bot[l], top[l], top[k]))
bm.faces.new(list(reversed(bot)))
ft = bm.faces.new(top)
r_ = bmesh.ops.inset_region(bm, faces=[ft], thickness=0.004, depth=0.003)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bm_mesh(bm, 'crown', sharp=30)
crown = add_obj('crown', me, BRASS_POL, HD, Matrix.Translation((0, 0, Z_DTOP + 0.018)))
bev(crown, 0.002, 2, 30)
Z_TOP = Z_DTOP + 0.018 + crh + 0.003

# balance wheel (vertical, facing forward = -y)
WC = Vector((0, 0.006, Z_DOME0 + 0.012 + 0.108))
torus('balance_rim', WC, (0, -1, 0), 0.065, 0.005, GEARM, HD, 96, 12)
for k in range(2):
    ang = math.radians(20 + 90 * k)
    d = Vector((math.cos(ang), 0, math.sin(ang)))
    o = add_obj('balance_spoke%d' % k, cyl_me('sp', 0.0028, 0.13, 12), GEARM, HD, frame(WC, d))
for k in range(16):   # timing screws on the rim
    ang = 2 * math.pi * k / 16 + 0.1
    d = Vector((math.cos(ang), 0, math.sin(ang)))
    cylinder('timing_screw%d' % k, WC + d * 0.071, d, 0.0032, 0.004, BRASS_POL, HD, 12, 0.0006)
cylinder('balance_staff', WC + Vector((0, 0.012, 0)), (0, 1, 0), 0.0022, 0.04, SCREWM, HD, 12, 0)
cylinder('balance_hub', WC, (0, 1, 0), 0.007, 0.006, GEARM, HD, 24, 0.0008)
# balance cock behind the wheel
cz0 = Z_DOME0 + 0.015
cock_h = WC.z - cz0
o = add_obj('balance_cock', cyl_me('ck', 0.012, cock_h, 4), BRASS, HD,
            frame((0, WC.y + 0.03, cz0 + cock_h / 2), (0, 0, 1), (1, 1, 0)))
o.scale = (1.0, 0.45, 1.0)
cylinder('cock_head', WC + Vector((0, 0.03, 0)), (0, 1, 0), 0.016, 0.008, BRASS, HD, 32, 0.001)
cylinder('cock_jewel', WC + Vector((0, 0.025, 0)), (0, 1, 0), 0.004, 0.003, RUBY, HD, 16, 0)
# hairspring: flat Archimedean spiral, 8 turns, in front of the wheel
cu = bpy.data.curves.new('hairspring', 'CURVE')
cu.dimensions = '3D'
cu.bevel_depth = 0.0009
cu.bevel_resolution = 2
pts = []
turns, nper = 8, 40
for i in range(turns * nper + 1):
    th = 2 * math.pi * i / nper
    rr = 0.006 + (0.035 - 0.006) * i / (turns * nper)
    pts.append(WC + Vector((rr * math.cos(th), -0.0075, rr * math.sin(th))))
spl = cu.splines.new('POLY')
spl.points.add(len(pts) - 1)
for p_, q in zip(spl.points, pts):
    p_.co = (q.x, q.y, q.z, 1)
add_obj('hairspring', cu, BLUED, HD)
# eye bridge + ruby eyes
EZ = WC.z + 0.02
add_obj('eye_bridge', ellipsoid_me('eb', 0.052, 0.005, 0.0075, 32, 12), BRASS_POL, HD,
            Matrix.Translation((0, -0.0125, EZ)))
for s in (-1, 1):
    e = Vector((0.025 * s, -0.020, EZ))
    ellipsoid('ruby_eye%d' % s, e, (0.014, 0.014, 0.014), RUBY_EYE, HD)
    torus('eye_setting%d' % s, e + Vector((0, 0.005, 0)), (0, -1, 0), 0.0145, 0.0026, BRASS_POL, HD, 40, 10)

# ---------------------------------------------------------------- NECK + CHEST (chest frame)
tube('neck_rod', (0, 0, C_CH.z + CC - 0.02), (0, 0, Z_DOME0 + 0.004), 0.016, BLUED, CH)
torus('neck_collar', (0, 0, C_CH.z + CC + 0.002), (0, 0, 1), 0.022, 0.0075, BRASS_POL, CH, 48, 12)
cylinder('neck_boss', (0, 0, C_CH.z + CC - 0.004), (0, 0, 1), 0.03, 0.012, BRASS, CH, 40, 0.0015)


bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=1.0)
for v in bm.verts:
    v.co = Vector((v.co.x * CA, v.co.y * CB, v.co.z * CC))
for f in bm.faces:
    f.material_index = 0 if f.calc_center_median().y < 0 else 1
me = bm_mesh(bm, 'chest_case')
case = add_obj('chest_case', me, [BRASS_SAT, BLUED, BRASS_IN, BRASS_IN], CH, Matrix.Translation(C_CH))
sd = case.modifiers.new('solid', 'SOLIDIFY')
sd.thickness = 0.006
sd.offset = -1.0
sd.use_even_offset = True
sd.material_offset = 2
WA, WB = 0.11, 0.14
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=96, radius1=1.0, radius2=1.0, depth=0.11)
for v in bm.verts:
    v.co = Vector((v.co.x * WA, v.co.y * WB, v.co.z))
cut_me = bm_mesh(bm, 'window_cut', smooth=False)
cutter = add_obj('window_cutter', cut_me, BRASS_IN, CH, frame(C_CH + Vector((0, -0.067, 0)), (0, -1, 0), (1, 0, 0)))
cutter.hide_render = True
cutter.display_type = 'WIRE'
bo = case.modifiers.new('window', 'BOOLEAN')
bo.operation = 'DIFFERENCE'
bo.solver = 'EXACT'
bo.object = cutter
bo.material_mode = 'TRANSFER'


def case_y(x, z):
    return -CB * math.sqrt(max(0.0, 1 - (x / CA) ** 2 - (z / CC) ** 2))


# polished bezel hugging the case around the window
us = [2 * math.pi * k / 128 for k in range(128)]
pts, nrm = [], []
for u in us:
    x, z = (WA + 0.003) * math.cos(u), (WB + 0.003) * math.sin(u)
    pts.append(C_CH + Vector((x, case_y(x, z) - 0.002, z)))
    nrm.append(Vector((math.cos(u) / WA, 0, math.sin(u) / WB)).normalized())
add_obj('bezel', sweep_me('bezel', pts, nrm, [Vector((0, -1, 0))] * len(us), 0.0095, 16), BRASS_POL, CH)
# caseband line between the brass front and the blued back
pts = [C_CH + Vector(((CA + 0.001) * math.cos(u), 0, (CC + 0.001) * math.sin(u))) for u in us]
nrm = [Vector((math.cos(u) / CA, 0, math.sin(u) / CC)).normalized() for u in us]
add_obj('caseband', sweep_me('caseband', pts, nrm, [Vector((0, 1, 0))] * len(us), 0.0035, 10), BRASS_POL, CH)
# movement plate
PY = 0.006
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=96, radius1=1.0, radius2=1.0, depth=0.005)
for v in bm.verts:
    v.co = Vector((v.co.x * 0.128, v.co.y * 0.158, v.co.z))
pl = add_obj('movement_plate', bm_mesh(bm, 'plate', sharp=30), PLATE, CH,
             frame(C_CH + Vector((0, PY, 0)), (0, -1, 0), (1, 0, 0)))
# five meshing gears (layout from a small offline search; teeth = round(r * 420))
GR = [0.03, 0.045, 0.06, 0.035, 0.08]
GC = {0: (-0.0871, 0.0587), 1: (0.085, 0.0205), 2: (-0.0002, 0.0819), 3: (0.0762, -0.0757), 4: (-0.0366, -0.0532)}
PAR = {2: 4, 0: 2, 1: 2, 3: 4}
GN = [int(round(r * 420)) for r in GR]
phase = {4: 0.13}
for g in (2, 0, 1, 3):
    p = PAR[g]
    th = math.atan2(GC[g][1] - GC[p][1], GC[g][0] - GC[p][0])
    Pp, Pg = 2 * math.pi / GN[p], 2 * math.pi / GN[g]
    up = ((th - phase[p]) / Pp) % 1.0
    ug = (-up - 0.5) % 1.0
    phase[g] = th + math.pi - ug * Pg
GY = -0.003
for g in range(5):
    c = C_CH + Vector((GC[g][0], GY - 0.0004 * g, GC[g][1]))
    gear('gear%d' % g, c, (0, -1, 0), GR[g], GN[g], 0.006, GEARM, CH, spokes=4 if g % 2 else 5, phase=phase[g])
    cylinder('arbor%d' % g, c + Vector((0, 0.004, 0)), (0, -1, 0), 0.0025, 0.014, BRASS_POL, CH, 12, 0.0004)
    if g in (0, 1, 3):
        ellipsoid('gear_ruby%d' % g, c + Vector((0, -0.0055, 0)), (0.006, 0.0035, 0.006), RUBY, CH)
        torus('ruby_chaton%d' % g, c + Vector((0, -0.004, 0)), (0, -1, 0), 0.0062, 0.0016, BRASS_POL, CH, 24, 8)
    else:
        cylinder('gear_cap%d' % g, c + Vector((0, -0.005, 0)), (0, -1, 0), 0.0065, 0.004, BRASS_POL, CH, 24, 0.0008)
# four blued screws on free spots of the plate
cands = []
rng = random.Random(7)
for i in range(4000):
    x, z = rng.uniform(-0.1, 0.1), rng.uniform(-0.13, 0.13)
    if (x / 0.098) ** 2 + (z / 0.125) ** 2 > 1:
        continue
    if all(math.hypot(x - GC[g][0], z - GC[g][1]) > GR[g] + 0.0035 + 0.01 for g in range(5)):
        cands.append((x, z))
chosen = [cands[0]]
while len(chosen) < 4 and cands:
    best = max(cands, key=lambda q: min(math.hypot(q[0] - c_[0], q[1] - c_[1]) for c_ in chosen))
    chosen.append(best)
for i, (x, z) in enumerate(chosen):
    screw('plate_screw%d' % i, C_CH + Vector((x, PY - 0.0025, z)), (0, -1, 0), CH, r=0.007, h=0.0035)
# winding key in his back
KY0 = CB - 0.004
cylinder('key_collar', C_CH + Vector((0, KY0 + 0.008, 0)), (0, 1, 0), 0.016, 0.01, BRASS_POL, CH, 32, 0.0012)
tube('key_shaft', C_CH + Vector((0, KY0, 0)), C_CH + Vector((0, KY0 + 0.07, 0)), 0.006, BRASS_POL, CH)
for s in (-1, 1):   # butterfly bow, in the y-z plane
    torus('key_bow%d' % s, C_CH + Vector((0, KY0 + 0.085, s * 0.022)), (1, 0, 0), 0.02, 0.0055, BRASS_POL, CH, 40, 10)
ellipsoid('key_knot', C_CH + Vector((0, KY0 + 0.082, 0)), (0.008, 0.012, 0.012), BRASS_POL, CH)

# ---------------------------------------------------------------- SHOULDERS + ARMS (chest frame)
def limb_r(r0, r1, bulge, t):
    return (r0 + (r1 - r0) * t) * (1 + bulge * math.sin(math.pi * t) ** 0.9)


def spindle(name, p0, p1, r0, r1, m, parent, bulge=0.14, n=28, segs=36):
    """Lathe-turned blued-steel limb: slight belly in the middle, tapering to the far joint."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    prof = [(0.0, 0.0)] + [(limb_r(r0, r1, bulge, i / n), L * i / n) for i in range(n + 1)] + [(0.0, L)]
    me = lathe_me(name, prof, segs)
    me.set_sharp_from_angle(angle=math.radians(40))
    o = add_obj(name, me, m, parent, frame(p0, d))
    for t in (0.0, 1.0):   # brass ferrules near both ends
        tt = 0.11 if t == 0 else 0.89
        ferrule(name + '_fer%d' % int(t), p0 + d * tt, d, limb_r(r0, r1, bulge, tt), parent)
    return o


def mitten_fn(v):
    # unit sphere -> squared-off mitten plate: x = palm normal, y = width, z = along the hand
    sx = 0.024 * v.x * (0.72 + 0.28 * (1 - abs(v.y)))
    sy = 0.042 * math.copysign(abs(v.y) ** 0.78, v.y)
    sz = 0.068 * math.copysign(abs(v.z) ** 0.82, v.z)
    sx += 0.012 * ((v.z + 1) / 2) ** 2          # fingers curl toward the palm
    return Vector((sx, sy, sz))


L_UP, L_FORE = 0.27, 0.37          # forearm +15 %
CAM_CH = (RW @ M_CH).inverted() @ Vector(CAM['loc'])
Z_SH = C_CH.z + 0.115
ARM = {
    'l': dict(s=1, S=Vector((0.183, 0.0, Z_SH)), W=Vector((0.10, -0.50, 1.04)), pole=(0.6, 0.2, -1.0), lift=0.45, fwd=0.0),
    'r': dict(s=-1, S=Vector((-0.183, 0.0, Z_SH)), W=Vector((-0.03, -0.36, 1.44)), pole=(-1.0, 0.2, -0.5), lift=0.3, fwd=0.8),
}
for k, A in ARM.items():
    s = A['s']
    S = A['S']
    # shoulder: blued axle out of the case, brass gear (20 teeth, 5 spokes), brass boss
    tube('sh_axle_' + k, (s * 0.085, 0, Z_SH), (s * 0.17, 0, Z_SH), 0.011, BLUED, CH)
    gear('sh_gear_' + k, (s * 0.152, 0, Z_SH), (s, 0, 0), 0.05, 20, 0.011, BRASS, CH, spokes=5,
         phase=0.1 * s, x_hint=(0, 0, 1), hub_r=0.016)
    cylinder('sh_boss_' + k, (s * 0.175, 0, Z_SH), (s, 0, 0), 0.03, 0.03, BRASS_SAT, CH, 40, 0.0018)
    screw('sh_screw_' + k, (s * 0.19, 0, Z_SH), (s, 0, 0), CH, r=0.012)
    E, W = ik(S, A['W'], L_UP, L_FORE, A['pole'])
    A['E'], A['W2'] = E, W
    spindle('upper_arm_' + k, S, E, 0.027, 0.024, BLUED, CH, 0.12)
    spindle('forearm_' + k, E, W, 0.025, 0.021, BLUED, CH, 0.15)
    du, dfw = (E - S).normalized(), (W - E).normalized()
    ax = du.cross(dfw)
    if ax.length < 1e-3:
        ax = Vector((1, 0, 0))
    pivot('elbow_' + k, E, ax.normalized(), CH, 0.025, hub_r=0.029, cheek_r=0.036)
    # hand: brass mitten plate + thumb plate on a pin, wrist pivot
    hd = (dfw + Vector((0, -A['fwd'], A['lift']))).normalized()
    cdir = (CAM_CH - (W + hd * 0.07)).normalized()          # mitten plate cheated to face the camera
    n = (cdir - cdir.dot(hd) * hd).normalized()
    w = n.cross(hd).normalized()
    if w.dot(Vector((0, -0.6, 1.0))) < 0:                    # thumb on the upper / forward edge
        w = -w
    pivot('wrist_' + k, W, n, CH, 0.021, hub_r=0.023, cheek_r=0.028, cheek_w=0.006)
    hc = W + hd * 0.074
    Mh = Matrix((n, hd.cross(n), hd)).transposed().to_4x4()      # right-handed (mitten is symmetric across its width)
    Mh.translation = hc
    add_obj('hand_' + k, ellipsoid_me('hand', 1, 1, 1, 40, 24, fn=mitten_fn), BRASS, CH, Mh)
    tb = W + hd * 0.04 + w * 0.034
    tdir = (hd * 0.55 + w * 0.83).normalized()
    ty = tdir.cross(n).normalized()
    Mt = Matrix((n, ty, tdir)).transposed().to_4x4()
    Mt.translation = tb + tdir * 0.024
    add_obj('thumb_' + k, ellipsoid_me('thumb', 0.011, 0.013, 0.03, 24, 12), BRASS, CH, Mt)
    cylinder('thumb_pin_' + k, tb, n, 0.0045, 0.036, BRASS_POL, CH, 16, 0.0006)
    for sg in (-1, 1):
        screw('thumb_screw_%s%d' % (k, sg), tb + n * sg * 0.018, n * sg, CH, r=0.006, h=0.0025)

# ---------------------------------------------------------------- WAIST + PELVIS (pelvis frame)
tube('waist_rod', (0, 0, Z_DRUM + 0.04), (0, 0, C_CH.z - CC + 0.02), 0.02, BLUED, PV)
ellipsoid('waist_ball', (0, 0, 0.985), (0.045, 0.045, 0.045), BRASS_POL, PV)
cylinder('pelvis_drum', (0, 0, Z_DRUM), (0, 0, 1), 0.11, 0.10, TURNED, PV, 72, 0.006)
torus('drum_band', (0, 0, Z_DRUM - 0.012), (0, 0, 1), 0.111, 0.004, BLUED, PV, 72, 8)
# mainspring-barrel teeth around the top of the drum
gear('drum_teeth', (0, 0, Z_DRUM + 0.032), (0, 0, 1), 0.112, int(round(0.112 * 420)), 0.012, GEARM, PV,
     spokes=0, hub=False, rim_w=0.008)

# ---------------------------------------------------------------- LEGS (hero frame, hips from the pelvis frame)
L_TH, L_SH = 0.45, 0.44
LEG = {
    'l': dict(s=1, A=Vector((0.21, -0.30, 0.056)), pole=(0.8, -0.6, 0.0), fdir=15.0),
    'r': dict(s=-1, A=Vector((-0.25, 0.30, 0.056)), pole=(-1.0, -0.15, 0.0), fdir=-40.0),
}
for k, Lg in LEG.items():
    s = Lg['s']
    Hp = M_PV @ Vector((s * 0.13, 0.0, Z_HIP))
    hip_ax = M_PV.to_3x3() @ Vector((s, 0, 0))
    K, A_ = ik(Hp, Lg['A'], L_TH, L_SH, Lg['pole'])
    spindle('thigh_' + k, Hp, K, 0.038, 0.031, BLUED, root, 0.12)
    spindle('shin_' + k, K, A_, 0.031, 0.024, BLUED, root, 0.18)
    dt, ds = (K - Hp).normalized(), (A_ - K).normalized()
    pivot('hip_' + k, Hp, hip_ax, root, 0.038, hub_r=0.04, cheek_r=0.046, sides=(1,) if s > 0 else (-1,))
    kax = dt.cross(ds)
    kax = kax.normalized() if kax.length > 1e-3 else Vector((1, 0, 0))
    if kax.dot(Vector((s, 0, 0))) < 0:
        kax = -kax
    pivot('knee_' + k, K, kax, root, 0.031, hub_r=0.034, cheek_r=0.041)
    # foot: brass boat, flat bottom, toe slightly raised
    fa = math.radians(Lg['fdir'])
    fd = Vector((math.sin(fa), -math.cos(fa), 0))
    fl = Vector((-fd.y, fd.x, 0))
    fc = Vector((A_.x, A_.y, 0.0)) + fd * 0.035

    def boat(v):
        z = max(v.z, 0.0)
        toe = max(0.0, -v.y / 0.12)
        return Vector((v.x * (1 - 0.25 * toe ** 2), v.y, z + (0.012 * toe ** 3 if z > 0.001 else 0.0) + 0.0005))
    Mf = Matrix((fl, -fd, Vector((0, 0, 1)))).transposed().to_4x4()
    Mf.translation = fc
    ft_ = add_obj('foot_' + k, ellipsoid_me('foot', 0.05, 0.12, 0.035, 48, 24, fn=boat), BRASS, root, Mf)
    pivot('ankle_' + k, A_, fl, root, 0.024, hub_r=0.027, cheek_r=0.034)

# ---------------------------------------------------------------- extra lights (hero only, per lighting notes)
def light(kind, loc, tgt, energy, col, **kw):
    bpy.ops.object.light_add(type=kind, location=loc)
    l = bpy.context.object
    l.data.energy, l.data.color = energy, col
    for k_, v_ in kw.items():
        setattr(l.data, k_, v_)
    l.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    l.light_linking.receiver_collection = HERO
    return l


light('SPOT', (0.9, -2.2, 3.1), (0, 0, 1.25), 260, (1.0, 0.83, 0.62), spot_size=math.radians(32), spot_blend=0.6,
      shadow_soft_size=0.12)                                                     # watchmaker's lamp
light('AREA', (-1.7, 1.7, 2.3), (0, 0, 1.3), 220, (0.55, 0.72, 1.0), shape='RECTANGLE', size=0.4, size_y=2.0)  # cool rim
# one clean shoji reflection on the dome: an emissive lattice card seen only in reflections, lighting only the dome
C_D = Vector((0, 0, Z_DOME0 + 0.13))
camp = Vector(CAM['loc'])
v = (C_D - camp).normalized()
rgt = v.cross(Vector((0, 0, 1))).normalized()
nrm_ = (-v + Vector((0, 0, 0.6)) - rgt * 0.45).normalized()
R_ = v - 2 * v.dot(nrm_) * nrm_
cc = C_D + R_ * 1.3
bpy.ops.mesh.primitive_plane_add(size=1, location=cc)
card = bpy.context.object
card.name = 'shoji_card'
card.rotation_euler = (-R_).to_track_quat('Z', 'Y').to_euler()
card.scale = (0.45, 0.62, 1)
cm = bpy.data.materials.new('shoji_card')
cm.use_nodes = True
nt = cm.node_tree
nt.nodes.remove(nt.nodes['Principled BSDF'])
tcn = node(nt, 'ShaderNodeTexCoord')
spn = node(nt, 'ShaderNodeSeparateXYZ')
nt.links.new(tcn.outputs['Generated'], spn.inputs[0])
masks = []
for axis_, cnt in (('X', 3), ('Y', 4)):
    mu = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(spn.outputs[axis_], mu.inputs[0])
    mu.inputs[1].default_value = cnt
    fr = node(nt, 'ShaderNodeMath', operation='FRACT')
    nt.links.new(mu.outputs[0], fr.inputs[0])
    pp = node(nt, 'ShaderNodeMath', operation='PINGPONG')
    nt.links.new(fr.outputs[0], pp.inputs[0])
    pp.inputs[1].default_value = 0.5
    gt = node(nt, 'ShaderNodeMath', operation='GREATER_THAN')
    nt.links.new(pp.outputs[0], gt.inputs[0])
    gt.inputs[1].default_value = 0.035
    masks.append(gt)
mm = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
nt.links.new(masks[0].outputs[0], mm.inputs[0])
nt.links.new(masks[1].outputs[0], mm.inputs[1])
st = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
nt.links.new(mm.outputs[0], st.inputs[0])
st.inputs[1].default_value = 40.0
em = node(nt, 'ShaderNodeEmission')
em.inputs['Color'].default_value = (1.0, 0.86, 0.64, 1)
nt.links.new(st.outputs[0], em.inputs['Strength'])
nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
card.data.materials.append(cm)
card.visible_camera = False
card.visible_diffuse = False
card.visible_shadow = False
card.visible_transmission = False
card.light_linking.receiver_collection = DOMEC


# ---------------------------------------------------------------- MOOKS: TINS, tin-can weeble men
def tin_mat(name='tin', band_z=None):
    m, nt, b = principled(name)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.42
    tc = node(nt, 'ShaderNodeTexCoord')
    vo = node(nt, 'ShaderNodeTexVoronoi')
    vo.inputs['Scale'].default_value = 3
    nt.links.new(tc.outputs['Object'], vo.inputs['Vector'])
    bp = node(nt, 'ShaderNodeBump')
    bp.inputs['Strength'].default_value = 0.15
    bp.inputs['Distance'].default_value = 0.02
    nt.links.new(vo.outputs['Distance'], bp.inputs['Height'])
    if band_z is not None:   # rolled beads around the can body
        wv = node(nt, 'ShaderNodeTexWave', wave_type='BANDS')
        wv.bands_direction = 'Z'
        wv.inputs['Scale'].default_value = 4.6
        nt.links.new(tc.outputs['Object'], wv.inputs['Vector'])
        pw = node(nt, 'ShaderNodeMath', operation='POWER')
        nt.links.new(wv.outputs['Fac'], pw.inputs[0])
        pw.inputs[1].default_value = 5.0
        bp2 = node(nt, 'ShaderNodeBump')
        bp2.inputs['Strength'].default_value = 0.6
        bp2.inputs['Distance'].default_value = 0.004
        nt.links.new(pw.outputs[0], bp2.inputs['Height'])
        nt.links.new(bp.outputs['Normal'], bp2.inputs['Normal'])
        nt.links.new(bp2.outputs['Normal'], b.inputs['Normal'])
    else:
        nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    sp = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sp.inputs[0])
    g1 = node(nt, 'ShaderNodeMath', operation='GREATER_THAN')
    nt.links.new(sp.outputs['Z'], g1.inputs[0])
    g1.inputs[1].default_value = band_z if band_z is not None else 9.0
    l1 = node(nt, 'ShaderNodeMath', operation='LESS_THAN')
    nt.links.new(sp.outputs['Z'], l1.inputs[0])
    l1.inputs[1].default_value = (band_z if band_z is not None else 9.0) + 0.08
    band = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(g1.outputs[0], band.inputs[0])
    nt.links.new(l1.outputs[0], band.inputs[1])
    nz = node(nt, 'ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 60
    nz.inputs['Detail'].default_value = 6
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    sc_ = node(nt, 'ShaderNodeMath', operation='GREATER_THAN')
    nt.links.new(nz.outputs['Fac'], sc_.inputs[0])
    sc_.inputs[1].default_value = 0.42
    bm_ = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(band.outputs[0], bm_.inputs[0])
    nt.links.new(sc_.outputs[0], bm_.inputs[1])
    fa = node(nt, 'ShaderNodeMath', operation='MULTIPLY')
    nt.links.new(bm_.outputs[0], fa.inputs[0])
    fa.inputs[1].default_value = 0.4
    mx = node(nt, 'ShaderNodeMix', data_type='RGBA')
    nt.links.new(fa.outputs[0], mx.inputs['Factor'])
    gn = node(nt, 'ShaderNodeTexNoise')       # light grime so the tins sit back behind the hero
    gn.inputs['Scale'].default_value = 3.5
    gn.inputs['Detail'].default_value = 4
    nt.links.new(tc.outputs['Object'], gn.inputs['Vector'])
    gr = node(nt, 'ShaderNodeMix', data_type='RGBA')
    gmr = node(nt, 'ShaderNodeMapRange')
    gmr.inputs['From Min'].default_value = 0.45
    gmr.inputs['From Max'].default_value = 0.65
    gmr.inputs['To Max'].default_value = 0.55
    nt.links.new(gn.outputs['Fac'], gmr.inputs['Value'])
    nt.links.new(gmr.outputs['Result'], gr.inputs['Factor'])
    gr.inputs['A'].default_value = (0.60, 0.61, 0.63, 1)
    gr.inputs['B'].default_value = (0.33, 0.32, 0.30, 1)
    nt.links.new(gr.outputs['Result'], mx.inputs['A'])
    mx.inputs['B'].default_value = (0.25, 0.08, 0.05, 1)
    nt.links.new(mx.outputs['Result'], b.inputs['Base Color'])
    return m


TIN = tin_mat()
TIN_B = tin_mat('tin_band', band_z=0.03)
LEAD = mat('lead', (0.18, 0.18, 0.19), 0.6, metal=0.5)


def strip_me(name, secs, w, t):
    """Flat strip through a list of (point, along, across) sections."""
    bm = bmesh.new()
    rings = []
    for P, D, X in secs:
        Y = D.cross(X).normalized()
        rings.append([bm.verts.new(P + X * sx * w / 2 + Y * sy * t / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for i in range(len(rings) - 1):
        for k in range(4):
            l = (k + 1) % 4
            bm.faces.new((rings[i][k], rings[i][l], rings[i + 1][l], rings[i + 1][k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm_mesh(bm, name, smooth=False)


def tin_man(name, pos, yaw, tilt, seed):
    S = 1.2
    rt = empty(name, None, Matrix.Translation((pos[0], pos[1], 0)) @ rotz(yaw) @ Matrix.Translation((0, 0, 0.21 * S))
               @ Matrix.Rotation(math.radians(tilt), 4, 'X') @ Matrix.Translation((0, 0, -0.21 * S))
               @ Matrix.Diagonal((S, S, S, 1)), coll=MOOKC)
    rnd = random.Random(seed)
    add_obj(name + '_weight', ellipsoid_me('w', 0.21, 0.21, 0.21, 48, 24, fn=lambda v: Vector((v.x, v.y, min(v.z, 0.0)))),
                LEAD, rt, Matrix.Translation((0, 0, 0.21)), coll=MOOKC)
    add_obj(name + '_body', cyl_me('b', 0.17, 0.70, 64), TIN_B, rt, Matrix.Translation((0, 0, 0.56)), coll=MOOKC)
    for z in (0.214, 0.906):
        add_obj(name + '_rim', torus_me('rim', 0.171, 0.008, 64, 10), TIN, rt, Matrix.Translation((0, 0, z)), coll=MOOKC)
    add_obj(name + '_lidring', torus_me('lr', 0.15, 0.004, 64, 8), TIN, rt, Matrix.Translation((0, 0, 0.91)), coll=MOOKC)
    # seam with 4 tab-and-slot rectangles (on the side facing the camera)
    sa = math.radians(-35)
    sd_ = Vector((math.cos(sa), math.sin(sa), 0))
    sx = Vector((-sd_.y, sd_.x, 0))
    Ms = Matrix((sx, sd_, Vector((0, 0, 1)))).transposed().to_4x4()
    Ms.translation = sd_ * 0.171 + Vector((0, 0, 0.56))
    add_obj(name + '_seam', cyl_me('sm', 0.5, 1.0, 4), TIN, rt, Ms @ Matrix.Diagonal((0.014, 0.004, 0.68, 1)) @
            Matrix.Rotation(math.pi / 4, 4, 'Z'), coll=MOOKC)
    for i in range(4):
        Mt = Ms.copy()
        Mt.translation = sd_ * 0.173 + Vector((0, 0, 0.32 + i * 0.16))
        add_obj(name + '_tab%d' % i, cyl_me('tb', 0.5, 1.0, 4), TIN, rt,
                Mt @ Matrix.Diagonal((0.034, 0.004, 0.05, 1)) @ Matrix.Rotation(math.pi / 4, 4, 'Z'), coll=MOOKC)
    # neck + head can with a dented lid
    add_obj(name + '_neck', cyl_me('nk', 0.045, 0.04, 32), TIN, rt, Matrix.Translation((0, 0, 0.925)), coll=MOOKC)
    add_obj(name + '_head', cyl_me('hd', 0.10, 0.15, 48), TIN, rt, Matrix.Translation((0, 0, 1.02)), coll=MOOKC)
    bm = bmesh.new()
    nr, ns = 7, 48
    dc = Vector((rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04)))
    cen = bm.verts.new((0, 0, 0))
    rings = []
    for i in range(1, nr + 1):
        rr = 0.098 * i / nr
        rings.append([bm.verts.new((rr * math.cos(2 * math.pi * k / ns), rr * math.sin(2 * math.pi * k / ns), 0)) for k in range(ns)])
    for k in range(ns):
        bm.faces.new((cen, rings[0][k], rings[0][(k + 1) % ns]))
    for i in range(nr - 1):
        for k in range(ns):
            l = (k + 1) % ns
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][l], rings[i][l]))
    for v_ in bm.verts:
        d2 = (v_.co.x - dc.x) ** 2 + (v_.co.y - dc.y) ** 2
        v_.co.z -= 0.014 * math.exp(-d2 / 0.0012) * (1 - (math.hypot(v_.co.x, v_.co.y) / 0.098) ** 4)
    add_obj(name + '_lid', bm_mesh(bm, 'lid'), TIN, rt, Matrix.Translation((0, 0, 1.0965)), coll=MOOKC)
    add_obj(name + '_hrim', torus_me('hr', 0.101, 0.006, 48, 8), TIN, rt, Matrix.Translation((0, 0, 1.094)), coll=MOOKC)
    # arms: stamped strips, bent 30 deg, fixed by bent tabs
    for s in (-1, 1):
        P0 = Vector((s * 0.178, 0, 0.80))
        d0 = Vector((s * math.sin(math.radians(9)), 0, -math.cos(math.radians(9))))
        X0 = Vector((0, 1, 0))
        P1 = P0 + d0 * 0.175
        d1 = (Matrix.Rotation(math.radians(-30), 3, Vector((1, 0, 0))) @ d0).normalized()   # bent 30 deg forward
        P2 = P1 + d1 * 0.175
        add_obj(name + '_arm%d' % s, strip_me('arm', [(P0, d0, X0), (P1, (d0 + d1).normalized(), X0),
                                                      (P2, d1, X0)], 0.05, 0.012), TIN, rt, coll=MOOKC)
        add_obj(name + '_atab%d' % s, cyl_me('at', 0.5, 1.0, 4), TIN, rt,
                Matrix.Translation(P0 + Vector((-s * 0.004, 0, 0.012))) @ Matrix.Diagonal((0.012, 0.06, 0.035, 1))
                @ Matrix.Rotation(math.pi / 4, 4, 'Z'), coll=MOOKC)
    return rt


CP = Vector(CAM['loc'])
f = (Vector(CAM['tgt']) - CP).normalized()
rgt = Vector((f.y, -f.x, 0)).normalized()
fh = Vector((f.x, f.y, 0)).normalized()
for i, (depth, lat, tilt) in enumerate(((7.3, -0.95, 5.0), (6.6, 0.95, -7.0), (9.8, -1.65, 9.0))):
    p = CP + fh * depth + rgt * lat
    yaw = math.degrees(math.atan2(-(CP.x - p.x), (CP.y - p.y))) + 180
    tin_man('tin%d' % i, (p.x, p.y), yaw + (i - 1) * 25, tilt, 11 * i + 3)

finish(a)
