import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from base import *
a = setup(); stage(); J = pose()   # J: joint positions, hero at origin, 3/4 to camera

# CHOCHIN - living paper lantern. Everything of the hero is built in hero-local coords
# (facing -y, hero's left = +x) under a root empty turned like pose() (-45 deg).
import random
import bmesh

sc = bpy.context.scene
COLL = sc.collection
YAW = -45.0
RINV = Matrix.Rotation(math.radians(-YAW), 3, 'Z')
P = {k: RINV @ v for k, v in J.items()}          # base pose joints back in hero-local coords

# ------------------------------------------------------------------ tunables
LANTERN_W = 3.4         # internal point light (W) - tuned so the paper peaks ~0.9 after AgX
PAPER_EMIT = 0.03       # washi self-emission strength (stabilises glow + lights the floor)
LIGHT_K = 2500          # colour temperature of the internal light
INNER_DARK = 0.85
SPILL_W = 26.0          # 'practical' spill: same spot as the core light, passes the paper, lights floor/limbs/mooks       # 0..1 darkening of the paper's inner face
LEAN = 4.0              # body leans into the stance (deg, toward the lead side)
CREST_AZ = 30.0         # crest centre azimuth from the front toward the lead side (deg) so it faces the 3/4 camera
CREST_Z = 1.00
GLARE = True

# ------------------------------------------------------------------ night version of the shared dojo
MOON = (0.6, 0.7, 1.0)
for o in list(sc.objects):
    if o.type != 'LIGHT':
        continue
    if o.location.x < -2.0:            # warm key -> faint high moon fill
        o.data.energy, o.data.color = 8.0, MOON
    elif o.location.y > 2.0:           # cool rim from behind (separates black limbs)
        o.data.energy, o.data.color = 200.0, MOON
    else:                              # front fill -> almost off
        o.data.energy, o.data.color = 3.0, MOON
_sh = bpy.data.materials['shoji'].node_tree.nodes['Principled BSDF']
_sh.inputs['Emission Color'].default_value = (*MOON, 1)
_sh.inputs['Emission Strength'].default_value = 0.38 * 0.15
_sh.inputs['Base Color'].default_value = (0.55, 0.62, 0.75, 1)
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.003, 0.004, 0.008, 1)
sc.cycles.max_bounces = 8
sc.cycles.transmission_bounces = 8
sc.cycles.diffuse_bounces = 4

# ------------------------------------------------------------------ helpers
def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    COLL.objects.link(o)
    o.parent = parent
    return o


def mesh_obj(name, verts, faces, m, parent=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    me.update()
    if smooth:
        me.shade_smooth()
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.parent = parent
    return o


def lathe(profile, segs=64, v0=None, f0=None):
    """Revolve [(r, z)] about z. r == 0 entries become poles. Returns verts, faces (outward normals for a bottom->top profile)."""
    verts = [] if v0 is None else v0
    faces = [] if f0 is None else f0
    rings = []
    for r, z in profile:
        if r < 1e-7:
            rings.append([len(verts)])
            verts.append(Vector((0, 0, z)))
        else:
            idx = []
            for i in range(segs):
                t = 2 * math.pi * i / segs
                idx.append(len(verts))
                verts.append(Vector((r * math.cos(t), r * math.sin(t), z)))
            rings.append(idx)
    for A, B in zip(rings[:-1], rings[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        for i in range(segs):
            j = (i + 1) % segs
            if len(A) == 1:
                faces.append((A[0], B[j], B[i]))
            elif len(B) == 1:
                faces.append((A[i], A[j], B[0]))
            else:
                faces.append((A[i], A[j], B[j], B[i]))
    return verts, faces


def arc(cx, cz, rad, a0, a1, n):
    return [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cz + rad * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def puck_profile(R, z0, z1, b_bot, b_top, dome=0.0, nb=5):
    """Closed cylinder profile with rounded bottom/top edges (radius b_*), optional slight domed top."""
    pr = [(0.0, z0)]
    pr += arc(R - b_bot, z0 + b_bot, b_bot, -90, 0, nb) if b_bot > 0 else [(R, z0)]
    pr += arc(R - b_top, z1 - b_top, b_top, 0, 90, nb) if b_top > 0 else [(R, z1)]
    if dome > 0:
        rr = R - b_top
        for k in range(1, 6):
            t = k / 6
            pr.append((rr * (1 - t), z1 + dome * (1 - (1 - t) ** 2)))
        pr.append((0.0, z1 + dome))
    else:
        pr.append((0.0, z1))
    return pr


def torus_geo(R, r, z, verts, faces, nU=96, nV=10):
    base = len(verts)
    for i in range(nU):
        u = 2 * math.pi * i / nU
        for j in range(nV):
            v = 2 * math.pi * j / nV
            rr = R + r * math.cos(v)
            verts.append(Vector((rr * math.cos(u), rr * math.sin(u), z + r * math.sin(v))))
    for i in range(nU):
        for j in range(nV):
            i1, j1 = (i + 1) % nU, (j + 1) % nV
            faces.append((base + i * nV + j, base + i1 * nV + j, base + i1 * nV + j1, base + i * nV + j1))


def rod(p0, p1, r, m, parent, name='rod', caps=True):
    o = cyl_between(p0, p1, r, m, name=name, caps=False)
    o.parent = parent
    if caps:
        for p in (p0, p1):
            sphere(p, r, m).parent = parent
    return o


def ball(p, r, m, parent, scale=None, name='ball'):
    o = sphere(p, r, m, name=name, scale=scale)
    o.parent = parent
    return o


def nd(nt, kind, **inp):
    n = nt.nodes.new(kind)
    for k, v in inp.items():
        if hasattr(v, 'is_linked') or hasattr(v, 'links'):
            nt.links.new(v, n.inputs[k])
        else:
            n.inputs[k].default_value = v
    return n


def M(nt, op, a, b=None, c=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b, c)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def V(nt, op, a, b=None):
    n = nt.nodes.new('ShaderNodeVectorMath')
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs['Vector'] if op not in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs['Value']


def lerp_col(nt, A, B, f):
    diff = V(nt, 'SUBTRACT', B, A)
    return V(nt, 'ADD', A, _scale(nt, diff, f))


def _scale(nt, col, s):
    n = nt.nodes.new('ShaderNodeVectorMath')
    n.operation = 'SCALE'
    if isinstance(col, (tuple, list)):
        n.inputs[0].default_value = col
    else:
        nt.links.new(col, n.inputs[0])
    if isinstance(s, (int, float)):
        n.inputs['Scale'].default_value = s
    else:
        nt.links.new(s, n.inputs['Scale'])
    return n.outputs['Vector']


def maprange(nt, x, a0, a1, b0, b1, smooth=False):
    n = nt.nodes.new('ShaderNodeMapRange')
    if smooth:
        n.interpolation_type = 'SMOOTHSTEP'
    n.clamp = True
    nt.links.new(x, n.inputs['Value'])
    n.inputs['From Min'].default_value = a0
    n.inputs['From Max'].default_value = a1
    n.inputs['To Min'].default_value = b0
    n.inputs['To Max'].default_value = b1
    return n.outputs['Result']


def principled(name, col, rough, metal=0.0, coat=0.0, coat_rough=0.03, sheen=0.0, rough_var=0.0, rough_scale=40.0):
    m = mat(name, col, rough, metal, coat=coat)
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    if coat:
        b.inputs['Coat Roughness'].default_value = coat_rough
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen
    if rough_var:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nd(nt, 'ShaderNodeTexNoise', Vector=tc.outputs['Object'], Scale=rough_scale, Detail=6.0)
        nt.links.new(maprange(nt, nz.outputs['Fac'], 0.3, 0.7, rough - rough_var, rough + rough_var), b.inputs['Roughness'])
    return m


# ------------------------------------------------------------------ materials
URUSHI = principled('urushi', (0.012, 0.010, 0.009), 0.35, coat=1.0, coat_rough=0.05, rough_var=0.08, rough_scale=25)
BRASS = principled('brass', (0.89, 0.70, 0.33), 0.25, metal=1.0, rough_var=0.07, rough_scale=60)
GOLD = principled('gold_line', (1.0, 0.76, 0.36), 0.18, metal=1.0)
BAMBOO = principled('bamboo', (0.30, 0.18, 0.07), 0.6, rough_var=0.1, rough_scale=200)

# profile of the lantern: two half-ellipses, r 0.16 at z 0.60 and 1.42, max 0.29 at z 1.00
Z0, Z1, ZM, RMAX, REND = 0.60, 1.42, 1.00, 0.29, 0.16
_K = math.sqrt(1 - (REND / RMAX) ** 2)
B_LO, B_HI = (ZM - Z0) / _K, (Z1 - ZM) / _K
NRIB = 22
RIB_DZ = (Z1 - Z0) / (NRIB + 1)
DIP = 0.0022            # paper sags very slightly between ribs


def prof_r(z):
    B = B_LO if z < ZM else B_HI
    t = min(1.0, abs(z - ZM) / B)
    return RMAX * math.sqrt(max(0.0, 1 - t * t))


def paper_r(z):
    return prof_r(z) - DIP * math.sin(math.pi * (z - Z0) / RIB_DZ) ** 2


def washi_mat():
    m = bpy.data.materials.new('washi')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    obj = tc.outputs['Object']
    sep = nd(nt, 'ShaderNodeSeparateXYZ', Vector=obj)
    x, y, z = sep.outputs['X'], sep.outputs['Y'], sep.outputs['Z']
    # fibres
    nz = nd(nt, 'ShaderNodeTexNoise', Vector=obj, Scale=120.0, Detail=10.0, Roughness=0.6)
    wv = nt.nodes.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    nt.links.new(obj, wv.inputs['Vector'])
    wv.inputs['Scale'].default_value = 30.0
    wv.inputs['Distortion'].default_value = 20.0
    wv.inputs['Detail'].default_value = 4.0
    f1 = maprange(nt, nz.outputs['Fac'], 0.32, 0.68, 0.0, 1.0)
    f2 = maprange(nt, wv.outputs['Fac'], 0.0, 1.0, 0.55, 1.0)
    fib = M(nt, 'MULTIPLY_ADD', M(nt, 'MULTIPLY', f1, f2), 0.22, 0.78)          # 0.78..1.0 so the fibre clouds show in backlight
    # patina near both rims (15 % darker)
    drim = M(nt, 'MINIMUM', M(nt, 'SUBTRACT', z, Z0), M(nt, 'SUBTRACT', Z1, z))
    pat = maprange(nt, drim, 0.0, 0.11, 0.85, 1.0, smooth=True)
    # 12 vertical paper seams (3 % darker)
    phi = M(nt, 'ARCTAN2', y, x)
    fr = M(nt, 'FRACT', M(nt, 'MULTIPLY_ADD', phi, 12.0 / (2 * math.pi), 0.25))
    seam = M(nt, 'GREATER_THAN', M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', fr, 0.5)), 0.488)
    sdark = M(nt, 'MULTIPLY_ADD', seam, -0.03, 1.0)
    tone = M(nt, 'MULTIPLY', pat, sdark)
    # crest frame: rotate so the crest direction maps to -y, then (u, v) = (x', z - zc)
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.vector_type = 'POINT'
    nt.links.new(obj, mp.inputs['Vector'])
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(-CREST_AZ))
    cs = nd(nt, 'ShaderNodeSeparateXYZ', Vector=mp.outputs['Vector'])
    u = cs.outputs['X']
    front = M(nt, 'LESS_THAN', cs.outputs['Y'], 0.0)
    v = M(nt, 'SUBTRACT', cs.outputs['Z'], CREST_Z)
    d = V(nt, 'LENGTH', nd(nt, 'ShaderNodeCombineXYZ', X=u, Y=v).outputs['Vector'])
    ring = M(nt, 'MULTIPLY', M(nt, 'LESS_THAN', d, 0.100), M(nt, 'GREATER_THAN', d, 0.080))
    dd = V(nt, 'LENGTH', nd(nt, 'ShaderNodeCombineXYZ', X=u, Y=M(nt, 'SUBTRACT', v, 0.030)).outputs['Vector'])
    disc = M(nt, 'LESS_THAN', dd, 0.035)
    sumi = ring
    au = M(nt, 'ABSOLUTE', u)
    for w, vc in ((0.09, -0.022), (0.07, -0.042), (0.05, -0.062)):
        bar = M(nt, 'MULTIPLY', M(nt, 'LESS_THAN', au, w / 2),
                M(nt, 'LESS_THAN', M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', v, vc)), 0.006))
        sumi = M(nt, 'MAXIMUM', sumi, bar)
    sumi = M(nt, 'MULTIPLY', sumi, front)
    verm = M(nt, 'MULTIPLY', disc, front)
    pig = M(nt, 'MAXIMUM', sumi, verm)
    # paper shading
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    inner = M(nt, 'MULTIPLY_ADD', geo.outputs['Backfacing'], -INNER_DARK, 1.0)   # inside of the skin reflects less -> hotter centre
    paper_col = _scale(nt, (0.896, 0.791, 0.578), M(nt, 'MULTIPLY', tone, inner))
    dif = nd(nt, 'ShaderNodeBsdfDiffuse', Color=paper_col, Roughness=1.0)
    tcol = _scale(nt, (1.0, 0.78, 0.50), M(nt, 'MULTIPLY', tone, fib))
    tra = nd(nt, 'ShaderNodeBsdfTranslucent', Color=tcol)
    mix = nd(nt, 'ShaderNodeMixShader', Fac=0.6)
    nt.links.new(dif.outputs[0], mix.inputs[1])
    nt.links.new(tra.outputs[0], mix.inputs[2])
    em = nd(nt, 'ShaderNodeEmission', Color=_scale(nt, (1.0, 0.62, 0.30), M(nt, 'MULTIPLY', tone, fib)),
            Strength=PAPER_EMIT)
    paper = nd(nt, 'ShaderNodeAddShader')
    nt.links.new(mix.outputs[0], paper.inputs[0])
    nt.links.new(em.outputs[0], paper.inputs[1])
    # pigment shading: opaque ink, translucency drops to ~10 %
    pcol = lerp_col(nt, (0.015, 0.015, 0.015), (0.578, 0.033, 0.024), verm)
    pb = nd(nt, 'ShaderNodeBsdfPrincipled', Roughness=0.8)
    nt.links.new(pcol, pb.inputs['Base Color'])
    nt.links.new(maprange(nt, verm, 0, 1, 0.8, 0.6), pb.inputs['Roughness'])
    tint = lerp_col(nt, (0.025, 0.021, 0.018), (0.30, 0.035, 0.018), verm)   # sumi ~2.5 %, vermilion glows red
    ptra = nd(nt, 'ShaderNodeBsdfTranslucent')
    nt.links.new(V(nt, 'MULTIPLY', tint, tcol), ptra.inputs['Color'])
    pem = nd(nt, 'ShaderNodeEmission', Strength=PAPER_EMIT)
    nt.links.new(V(nt, 'MULTIPLY', tint, (1.0, 0.62, 0.30)), pem.inputs['Color'])
    pmix = nd(nt, 'ShaderNodeMixShader', Fac=0.6)
    nt.links.new(pb.outputs[0], pmix.inputs[1])
    nt.links.new(ptra.outputs[0], pmix.inputs[2])
    padd = nd(nt, 'ShaderNodeAddShader')
    nt.links.new(pmix.outputs[0], padd.inputs[0])
    nt.links.new(pem.outputs[0], padd.inputs[1])
    final = nd(nt, 'ShaderNodeMixShader', Fac=pig)
    nt.links.new(paper.outputs[0], final.inputs[1])
    nt.links.new(padd.outputs[0], final.inputs[2])
    nt.links.new(final.outputs[0], out.inputs['Surface'])
    return m


WASHI = washi_mat()

# ------------------------------------------------------------------ hierarchy
root = empty('chochin')
root.rotation_euler = (0, 0, math.radians(YAW))
HIP = Vector((0, 0, 0.58))
body = empty('body', root)
body.matrix_basis = Matrix.Translation(HIP) @ Matrix.Rotation(math.radians(-LEAN), 4, 'X') @ Matrix.Translation(-HIP)

# ------------------------------------------------------------------ lantern body
zs = []
n_per = 8
for k in range(NRIB + 1):
    for s in range(n_per):
        zs.append(Z0 + RIB_DZ * (k + s / n_per))
zs.append(Z1)
vv, ff = lathe([(paper_r(z), z) for z in zs], segs=48)
paper = mesh_obj('washi', vv, ff, WASHI, body)
sub = paper.modifiers.new('sub', 'SUBSURF')
sub.levels = sub.render_levels = 1

vv, ff = [], []
for k in range(NRIB):
    z = Z0 + RIB_DZ * (k + 1)
    torus_geo(prof_r(z) + 0.002, 0.0045, z, vv, ff)
ribs = mesh_obj('ribs', vv, ff, BAMBOO, body)

# rims (bottom rim = pelvis)
for zc in (Z0, Z1):
    vv, ff = lathe(puck_profile(0.165, zc - 0.025, zc + 0.025, 0.006, 0.006), segs=96)
    mesh_obj('rim', vv, ff, URUSHI, body)

# head: lacquer lid with gold line
LID0, LID1 = Z1 + 0.025, Z1 + 0.025 + 0.11
vv, ff = lathe(puck_profile(0.15, LID0, LID1, 0.004, 0.02, dome=0.008), segs=96)
mesh_obj('lid', vv, ff, URUSHI, body)
LIDM = (LID0 + LID1) / 2 - 0.004
vv, ff = [], []
torus_geo(0.1503, 0.0025, LIDM, vv, ff, nU=128, nV=8)
mesh_obj('gold_line', vv, ff, GOLD, body)

# brass bail handle: studs on the lid sides, kettle-style bail tilted 15 deg back, top at 1.75
WIRE = 0.008
XB = 0.15 + 0.014 + WIRE
PIV_Z = LIDM + 0.012
TILT = 15.0
LEG = (1.75 - PIV_Z) / math.cos(math.radians(TILT)) - XB
for sx in (1, -1):
    vv, ff = lathe(puck_profile(0.013, 0.0, 0.014, 0.0, 0.003), segs=32)
    st = mesh_obj('stud', vv, ff, BRASS, body)
    st.matrix_basis = Matrix.Translation((sx * 0.149, 0, PIV_Z)) @ Matrix.Rotation(math.radians(90 * sx), 4, 'Y')
    ball((sx * XB, 0, PIV_Z), WIRE * 1.9, BRASS, body, name='bail_eye')
cu = bpy.data.curves.new('bail', 'CURVE')
cu.dimensions = '3D'
cu.bevel_depth = WIRE
cu.bevel_resolution = 6
cu.use_fill_caps = True
pts = [(XB, 0, 0), (XB, 0, LEG * 0.5), (XB, 0, LEG)]
for k in range(1, 40):
    t = math.pi * k / 40
    pts.append((XB * math.cos(t), 0, LEG + XB * math.sin(t)))
pts += [(-XB, 0, LEG), (-XB, 0, LEG * 0.5), (-XB, 0, 0)]
spl = cu.splines.new('POLY')
spl.points.add(len(pts) - 1)
for p, c in zip(spl.points, pts):
    p.co = (*c, 1)
bail = bpy.data.objects.new('bail', cu)
COLL.objects.link(bail)
bail.data.materials.append(BRASS)
bail.parent = body
bail.matrix_basis = Matrix.Translation((0, 0, PIV_Z)) @ Matrix.Rotation(math.radians(TILT), 4, 'X')
print('bail top z (body space)', PIV_Z + (LEG + XB) * math.cos(math.radians(TILT)))

# internal light (2200 K)
ld = bpy.data.lights.new('lantern_core', 'POINT')
ld.energy = LANTERN_W
ld.shadow_soft_size = 0.06
ld.use_nodes = True
lnt = ld.node_tree
bb = lnt.nodes.new('ShaderNodeBlackbody')
bb.inputs['Temperature'].default_value = LIGHT_K
lnt.links.new(bb.outputs['Color'], lnt.nodes['Emission'].inputs['Color'])
lo = bpy.data.objects.new('lantern_core', ld)
COLL.objects.link(lo)
lo.parent = body
lo.location = (0, 0, 1.0)

# spill light: the paper glow is calibrated for the camera, so a linked twin of the core light carries the lantern's
# light out onto the floor, the limbs and the mooks (light linking: it ignores and passes through the washi + ribs)
link = bpy.data.collections.new('lantern_skin')
for ob in (paper, ribs):
    link.objects.link(ob)
for cob in link.collection_objects:
    cob.light_linking.link_state = 'EXCLUDE'
sd = bpy.data.lights.new('lantern_spill', 'POINT')
sd.energy = SPILL_W
sd.shadow_soft_size = 0.18
sd.use_nodes = True
bb2 = sd.node_tree.nodes.new('ShaderNodeBlackbody')
bb2.inputs['Temperature'].default_value = LIGHT_K
sd.node_tree.links.new(bb2.outputs['Color'], sd.node_tree.nodes['Emission'].inputs['Color'])
so = bpy.data.objects.new('lantern_spill', sd)
COLL.objects.link(so)
so.parent = body
so.location = (0, 0, 1.0)
so.light_linking.receiver_collection = link
so.light_linking.blocker_collection = link

# ------------------------------------------------------------------ arms (pivot discs on the lantern sides)
ARM_Z = 1.25
ARM_LEN = {'l': (0.30, 0.32), 'r': (0.26, 0.26)}   # lead arm a bit longer so the fist clears the barrel silhouette
ARM_SWING = {'l': -40.0, 'r': -25.0}                 # lead upper arm swung forward (deg about hero x)
R_ROD_A = 0.018
slope = -(RMAX * ((ARM_Z - ZM) / B_HI ** 2) / math.sqrt(1 - ((ARM_Z - ZM) / B_HI) ** 2))
nrm_rz = Vector((1.0, -slope)).normalized()   # outward normal in (r, z)


def clear_of_lantern(p, need):
    rr = prof_r(min(max(p.z, Z0), Z1)) + 0.0065 if Z0 <= p.z <= Z1 else 0.0
    return math.hypot(p.x, p.y) - rr - need


def arm(side, sh, el, ha):
    sx = 1 if side == 'l' else -1
    surf = Vector((sx * prof_r(ARM_Z), 0, ARM_Z))
    n3 = Vector((sx * nrm_rz.x, 0, nrm_rz.y))
    dc = surf + n3 * (0.0065 + 0.006)
    vv, ff = lathe(puck_profile(0.035, -0.006, 0.006, 0.002, 0.003), segs=48)
    disc = mesh_obj('pivot_disc', vv, ff, URUSHI, body)
    disc.matrix_basis = Matrix.Translation(dc) @ n3.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    S = dc + n3 * 0.012
    UP, FORE = ARM_LEN[side]
    d1 = Matrix.Rotation(math.radians(ARM_SWING[side]), 3, 'X') @ (el - sh).normalized()
    E = S + UP * d1
    d2 = (ha - el).normalized()
    H = E + FORE * d2
    for _ in range(30):            # keep the fist and forearm clear of the paper
        worst = min(clear_of_lantern(H, 0.032 + 0.02),
                    min(clear_of_lantern(E.lerp(H, t / 8), R_ROD_A + 0.02) for t in range(9)))
        if worst >= 0:
            break
        radial = Vector((H.x, H.y, 0)).normalized()
        H = E + FORE * ((H + radial * 0.01) - E).normalized()
    ball(S, 0.022, URUSHI, body, name='shoulder')
    rod(S, E, R_ROD_A, URUSHI, body, name='upper_arm')
    rod(E, H, R_ROD_A, URUSHI, body, name='forearm')
    ball(E, 0.024, BRASS, body, name='elbow_cap')
    ball(H, 0.032, URUSHI, body, name='fist')
    return S, E, H


ARMS = {s: arm(s, P['sh_' + s], P['el_' + s], P['ha_' + s]) for s in ('l', 'r')}
print('arms', {k: [tuple(round(c, 3) for c in p) for p in v] for k, v in ARMS.items()})

# ------------------------------------------------------------------ legs (from the bottom rim)
ANKLE_Z = 0.055
HIP_Z = Z0 - 0.025
FOOT_DIR = {'l': Vector((0.20, -1.0, 0)).normalized(), 'r': Vector((-0.75, -0.66, 0)).normalized()}


HIPS = {'l': Vector((0.058, -0.069, HIP_Z)), 'r': Vector((-0.058, 0.069, HIP_Z))}     # pelvis turned with the stance
ANKLES = {'l': Vector((0.20, -0.30, ANKLE_Z)), 'r': Vector((-0.22, 0.30, ANKLE_Z))}
KNEE_HINT = {'l': Vector((0.5, -0.8, 0.0)), 'r': Vector((-0.55, -0.45, 0.0))}
LEG_L = 0.335


def leg(side):
    Hp, A = HIPS[side], ANKLES[side]
    d = A - Hp
    hint = KNEE_HINT[side] - d * (KNEE_HINT[side].dot(d) / d.length_squared)
    h = math.sqrt(max(0.0, LEG_L ** 2 - (d.length / 2) ** 2))
    K = Hp + d / 2 + hint.normalized() * h
    ball(Hp, 0.03, URUSHI, root, name='hip_socket')
    rod(Hp, K, 0.022, URUSHI, root, name='thigh')
    rod(K, A, 0.022, URUSHI, root, name='shin')
    ball(K, 0.028, BRASS, root, name='knee_cap')
    fd = FOOT_DIR[side]
    fc = Vector((A.x, A.y, 0.0)) + fd * 0.035
    fc.z = 0.033
    ft = ball(fc, 1.0, URUSHI, root, scale=(0.05, 0.11, 0.035), name='foot')
    ft.rotation_euler = (0, 0, math.atan2(fd.y, fd.x) + math.pi / 2)
    return Hp, K, A, LEG_L


LEGS = {s: leg(s) for s in ('l', 'r')}
print('legs', {k: [tuple(round(c, 3) for c in p) for p in v[:3]] + [round(v[3], 3)] for k, v in LEGS.items()})

# ------------------------------------------------------------------ mooks: KAMI-NINGYO (black folded kraft paper men)
KRAFT = principled('kraft', (0.023, 0.019, 0.016), 0.8, sheen=0.25)
_knt = KRAFT.node_tree
_tc = _knt.nodes.new('ShaderNodeTexCoord')
_nz = nd(_knt, 'ShaderNodeTexNoise', Vector=_tc.outputs['Object'], Scale=90.0, Detail=8.0)
_bp = nd(_knt, 'ShaderNodeBump', Strength=0.05, Height=_nz.outputs['Fac'])
_knt.links.new(_bp.outputs['Normal'], _knt.nodes['Principled BSDF'].inputs['Normal'])
rng = random.Random(7)


def bevel(o):
    b = o.modifiers.new('bev', 'BEVEL')
    b.width = 0.0015
    b.segments = 1
    b.limit_method = 'ANGLE'
    b.angle_limit = math.radians(20)


def flat_obj(name, bm, parent):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(KRAFT)
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    o.parent = parent
    bevel(o)
    return o


def prism(p0, p1, r, parent, twist=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=3, radius1=r, radius2=r * 0.85, depth=(p1 - p0).length)
    for vtx in bm.verts:
        vtx.co += Vector((rng.uniform(-0.006, 0.006), rng.uniform(-0.006, 0.006), 0))
    o = flat_obj('limb', bm, parent)
    q = (p1 - p0).to_track_quat('Z', 'Y')
    o.matrix_basis = Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4() @ Matrix.Rotation(twist, 4, 'Z')
    return o


def mook(pos, face_to, pose_kind, seed):
    rng.seed(seed)
    m_root = empty('mook', None)
    m_root.location = (pos[0], pos[1], 0)
    dvec = Vector((face_to[0] - pos[0], face_to[1] - pos[1]))
    m_root.rotation_euler = (0, 0, math.atan2(dvec.y, dvec.x) + math.pi / 2)   # local -y faces the hero
    # torso
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    for vtx in bm.verts:
        x0, y0, z0 = vtx.co
        taper = 0.78 + 0.22 * (z0 + 0.5)                    # narrower waist, broad folded shoulders
        fold = 0.035 if abs(x0) < 1e-4 else 0.0              # mountain fold down the centre, front and back
        vtx.co = Vector((x0 * 0.34 * taper, y0 * 0.18 + math.copysign(fold, y0), z0 * 0.50))
        vtx.co += Vector([rng.uniform(-0.02, 0.02) for _ in range(3)])
    t = flat_obj('torso', bm, m_root)
    t.location = (0, 0, 1.06)
    t.rotation_euler = (math.radians(rng.uniform(4, 9)), 0, math.radians(rng.uniform(-8, 8)))
    # head: octahedron
    bm = bmesh.new()
    rx, ry, rz = 0.10, 0.09, 0.14
    vs = [bm.verts.new(c) for c in ((rx, 0, 0), (-rx, 0, 0), (0, ry, 0), (0, -ry, 0), (0, 0, rz), (0, 0, -rz))]
    for i, j in ((0, 2), (2, 1), (1, 3), (3, 0)):
        bm.faces.new((vs[i], vs[j], vs[4]))
        bm.faces.new((vs[j], vs[i], vs[5]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    h = flat_obj('head', bm, m_root)
    h.location = (0, -0.03, 1.415)            # neck tip tucked into the folded shoulders
    h.rotation_euler = (math.radians(10), 0, math.radians(rng.uniform(-25, 25)))
    if pose_kind == 'claw':
        joints = dict(sh_l=(0.19, -0.02, 1.25), el_l=(0.36, -0.20, 1.12), ha_l=(0.30, -0.42, 1.28),
                      sh_r=(-0.19, -0.02, 1.25), el_r=(-0.36, -0.12, 1.05), ha_r=(-0.34, -0.36, 1.16),
                      hp_l=(0.10, 0, 0.82), kn_l=(0.22, -0.16, 0.44), ft_l=(0.26, -0.14, 0.03),
                      hp_r=(-0.10, 0, 0.82), kn_r=(-0.22, 0.06, 0.42), ft_r=(-0.30, 0.20, 0.03))
    else:  # 'lurk': one arm low and back, one arm forward, deep crouch
        joints = dict(sh_l=(0.19, -0.02, 1.24), el_l=(0.30, -0.26, 1.10), ha_l=(0.20, -0.50, 1.10),
                      sh_r=(-0.19, -0.02, 1.24), el_r=(-0.30, 0.06, 0.98), ha_r=(-0.34, 0.12, 0.74),
                      hp_l=(0.10, 0, 0.82), kn_l=(0.26, -0.22, 0.46), ft_l=(0.30, -0.26, 0.03),
                      hp_r=(-0.10, 0, 0.82), kn_r=(-0.20, 0.14, 0.40), ft_r=(-0.26, 0.34, 0.03))
    J2 = {k: Vector(v) for k, v in joints.items()}
    for s in ('l', 'r'):
        prism(J2['sh_' + s], J2['el_' + s], 0.05, m_root, twist=rng.uniform(0, 2))
        prism(J2['el_' + s], J2['ha_' + s], 0.045, m_root, twist=rng.uniform(0, 2))
        prism(J2['hp_' + s], J2['kn_' + s], 0.055, m_root, twist=rng.uniform(0, 2))
        prism(J2['kn_' + s], J2['ft_' + s], 0.05, m_root, twist=rng.uniform(0, 2))
        # folded foot wedge
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for vtx in bm.verts:
            vtx.co = Vector((vtx.co.x * 0.08, vtx.co.y * 0.20, (vtx.co.z + 0.5) * 0.05))
            if vtx.co.y < 0 and vtx.co.z > 0.01:
                vtx.co.z *= 0.3
        f = flat_obj('foot', bm, m_root)
        f.location = (J2['ft_' + s].x, J2['ft_' + s].y - 0.04, 0.0)
        f.rotation_euler = (0, 0, math.radians(rng.uniform(-20, 20)))
    return m_root


cam = sc.camera
cxy = Vector((cam.location.x, cam.location.y))
fwd = (Vector(CAM['tgt']).to_2d() - cxy).normalized()
right = Vector((fwd.y, -fwd.x))


def at_cam(depth, lateral):
    p = cxy + fwd * depth + right * lateral
    return (p.x, p.y)


FRAC = math.tan(math.atan(18.0 * 9 / 16 / CAM['lens']))     # half-width / depth of the 9:16 frame
mook(at_cam(7.2, -0.92 * 7.2 * FRAC), (0.0, 0.0), 'claw', 3)
mook(at_cam(7.6, 0.84 * 7.6 * FRAC), (0.0, 0.0), 'lurk', 11)

# ------------------------------------------------------------------ subtle bloom (compositor)
if GLARE:
    sc.use_nodes = True
    tree = sc.node_tree
    rl = tree.nodes['Render Layers']
    comp = tree.nodes['Composite']
    g = tree.nodes.new('CompositorNodeGlare')
    g.glare_type = 'FOG_GLOW'
    g.quality = 'HIGH'
    g.inputs['Threshold'].default_value = 0.55
    g.inputs['Strength'].default_value = 0.3
    g.inputs['Size'].default_value = 0.45
    tree.links.new(rl.outputs['Image'], g.inputs['Image'])
    tree.links.new(g.outputs['Image'], comp.inputs['Image'])

finish(a)
