import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from base import *
a = setup(); stage(); J = pose()   # J: joint positions, hero at origin, 3/4 to camera

# HARIGANE - one-line copper wire figure.
# Everything for the hero is built in the hero's LOCAL frame (POSE_LOCAL: faces -y, left = +x, z up)
# and parented to an empty turned by the same yaw that pose() uses, so it matches J exactly.
import os
from mathutils import Quaternion

YAW = -45.0
RZ = Matrix.Rotation(math.radians(YAW), 3, 'Z')
RZi = RZ.transposed()
P = {k: Vector(v) for k, v in POSE_LOCAL.items()}
CAM_L = RZi @ Vector(CAM['loc'])          # camera position in hero-local coords
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
WR = 0.011          # wire radius (22 mm wire; 18 mm read under 4 px at 360 px wide)
STEP = 0.0025       # polyline sampling


# ------------------------------------------------------------------ polyline helpers
def cumlen(pts):
    s = [0.0]
    for i in range(1, len(pts)):
        s.append(s[-1] + (pts[i] - pts[i - 1]).length)
    return s


def resample(pts, step=STEP):
    s = cumlen(pts)
    L = s[-1]
    n = max(2, int(L / step) + 1)
    out, j = [], 0
    for i in range(n):
        t = L * i / (n - 1)
        while j < len(pts) - 2 and s[j + 1] < t:
            j += 1
        seg = s[j + 1] - s[j]
        f = 0.0 if seg < 1e-12 else (t - s[j]) / seg
        out.append(pts[j].lerp(pts[j + 1], min(max(f, 0.0), 1.0)))
    return out


def line(p0, p1, step=STEP):
    return resample([Vector(p0), Vector(p1)], step)


def vslerp(v0, v1, s):
    om = v0.angle(v1)
    if om < 1e-6:
        return v0.lerp(v1, s)
    return (v0 * math.sin((1 - s) * om) + v1 * math.sin(s * om)) / math.sin(om)


def fillet(pts, r, step=STEP):
    """Corner points -> dense polyline with circular fillets of radius r at interior corners."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        d0 = (p1 - p0).normalized()
        d1 = (p2 - p1).normalized()
        ang = d0.angle(d1)
        if ang < 1e-3:
            out.append(p1)
            continue
        t = r * math.tan(ang / 2)
        t = min(t, 0.45 * (p1 - p0).length, 0.45 * (p2 - p1).length)
        rr = t / math.tan(ang / 2)
        a0, a1 = p1 - d0 * t, p1 + d1 * t
        w = (d1 - d0 * d1.dot(d0)).normalized()
        c = a0 + w * rr
        v0, v1 = a0 - c, a1 - c
        k = max(3, int(rr * ang / step))
        for j in range(k + 1):
            out.append(c + vslerp(v0, v1, j / k))
    out.append(pts[-1])
    return resample(out, step)


def transport(pts, n0=None):
    n = len(pts)
    T = []
    for i in range(n):
        T.append((pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized())
    if n0 is None:
        n0 = Z if abs(T[0].dot(Z)) < 0.9 else X
    cur = (n0 - T[0] * n0.dot(T[0])).normalized()
    N = []
    for i in range(n):
        cur = (cur - T[i] * cur.dot(T[i])).normalized()
        N.append(cur.copy())
    B = [T[i].cross(N[i]) for i in range(n)]
    return T, N, B


def twisted(path, d0=None, d1=None, rate=7.5, rad=WR):
    """Two touching strands helixing round the path (parallel-transport frames).
    Returns (out_strand, back_strand): out runs along the path, back runs the reverse way.
    d0/d1 pick which side strand 1 sits on at the start/end (so junctions don't cross)."""
    T, N, B = transport(path)
    s = cumlen(path)
    L = s[-1]

    def ang(d, i):
        d = d - T[i] * d.dot(T[i])
        return math.atan2(d.dot(B[i]), d.dot(N[i]))
    phi0 = ang(Vector(d0), 0) if d0 is not None else 0.0
    want = 2 * math.pi * rate * L
    if d1 is not None:
        e = ang(Vector(d1), -1)
        k = round((phi0 + want - e) / (2 * math.pi))
        phi1 = e + 2 * math.pi * k
    else:
        phi1 = phi0 + want
    s1, s2 = [], []
    for i, p in enumerate(path):
        f = phi0 + (phi1 - phi0) * s[i] / L
        o = (N[i] * math.cos(f) + B[i] * math.sin(f)) * rad
        s1.append(p + o)
        s2.append(p - o)
    return s1, s2[::-1]


def herm(p0, t0, p1, t1, k=1.0, step=STEP):
    d = (p1 - p0).length
    m0, m1 = t0.normalized() * d * k, t1.normalized() * d * k
    n = max(2, int(d * 1.5 / step))
    out = []
    for i in range(1, n):
        s = i / n
        h00 = 2 * s ** 3 - 3 * s ** 2 + 1
        h10 = s ** 3 - 2 * s ** 2 + s
        h01 = -2 * s ** 3 + 3 * s ** 2
        h11 = s ** 3 - s ** 2
        out.append(p0 * h00 + m0 * h10 + p1 * h01 + m1 * h11)
    return out


def tan_end(pts):
    return (pts[-1] - pts[max(0, len(pts) - 4)]).normalized()


def tan_start(pts):
    return (pts[min(len(pts) - 1, 3)] - pts[0]).normalized()


def way(p, t, eps=0.002):
    """A waypoint with a direction, as a tiny 2-point piece."""
    p, t = Vector(p), Vector(t).normalized()
    return [p - t * eps, p + t * eps]


def chain(pieces, ks=None):
    out = list(pieces[0])
    for i in range(1, len(pieces)):
        nxt = pieces[i]
        k = ks[i - 1] if ks and i - 1 < len(ks) and ks[i - 1] else 0.9
        out += herm(out[-1], tan_end(out), nxt[0], tan_start(nxt), k)
        out += list(nxt)
    clean = [out[0]]
    for p in out[1:]:
        if (p - clean[-1]).length > 0.0006:
            clean.append(p)
    return clean


def spiral(C, eu, ev, r0, r1, turns, elong=1.0, sgn=1, step=STEP, dome=0.0, normal=Z):
    """Flat Archimedean spiral in the (eu, ev) plane, starting at C - r0*elong*eu, moving along sgn*ev, winding in."""
    tot = 2 * math.pi * turns
    approx = tot * (r0 + r1) / 2 * (1 + elong) / 2
    n = max(30, int(approx / step))
    out = []
    for i in range(n + 1):
        th = tot * i / n
        r = r0 + (r1 - r0) * th / tot
        out.append(C + eu * (-math.cos(th) * r * elong) + ev * (sgn * math.sin(th) * r) + normal * (dome * (th / tot) ** 1.3))
    return out


def spine(z):
    return Vector((0.0, 0.04 * (z - 0.95), z))


# ------------------------------------------------------------------ the figure's skeleton (local)
HIP = P['hip']
N0 = Vector((0.0, 0.02, 1.40))                 # neck base / shoulder-line junction
S_L = Vector((0.17, 0.02, 1.40))
S_R = Vector((-0.17, 0.02, 1.40))
BEAD_Z = 1.13
BEAD_C = spine(BEAD_Z)
BEAD_R = 0.05
HEAD_AX = Vector((0.0, 0.006, 0.0))            # head coil axis (x, y)
HZ0, HH, HR, HTURNS = 1.47, 0.28, 0.13, 7
TH_F = -math.pi / 2                            # front azimuth (-y)


def pel(adeg):                                  # pelvis loop, frontal plane, 0.20 x 0.12, centred at hip
    a_ = math.radians(adeg)
    return Vector((0.10 * math.cos(a_), 0.0, HIP.z + 0.06 * math.sin(a_)))


def pel_arc(a0, a1):
    n = max(8, int(abs(a1 - a0) / 2))
    return resample([pel(a0 + (a1 - a0) * i / n) for i in range(n + 1)])


def to_cam(p):
    v = CAM_L - p
    return v.normalized()


# ---- legs + feet
def leg(side):
    kn, ft = (P['kn_l'], P['ft_l']) if side == 'l' else (P['kn_r'], P['ft_r'])
    root = pel(-55 if side == 'l' else -125)
    d = (kn - root).normalized()
    start = root + d * 0.022
    t = (kn.z - 0.085) / (kn.z - ft.z)
    ank = kn.lerp(ft, t)                        # ankle: shin line at z = 0.085
    path = fillet([start, kn, ank], 0.05)
    fwd = Vector((0.06, -1, 0)).normalized() if side == 'l' else Vector((-0.62, -0.78, 0)).normalized()
    side_v = Z.cross(fwd).normalized()          # points to the figure's left of the foot
    s1, s2 = twisted(path, d0=X, d1=-fwd)        # strand 1 outer at the hip, at the heel side at the ankle
    elong, r0, r1 = 1.15, 0.075, 0.012
    gz = 0.0092
    C = Vector((ank.x, ank.y, gz)) + fwd * (r0 * elong - 0.013)
    sgn = -1 if side == 'l' else 1              # spiral wraps round the outside edge first
    sp = spiral(C, fwd, side_v, r0, r1, 2.0, elong, sgn, dome=0.014)   # outer turn on the floor, centre lifted a touch
    # rise from the spiral's inner end: tight bend up, then an instep arch back to the ankle
    E = sp[-1]
    te = tan_end(sp)
    rise = [E + te * (0.016 * math.sin(b)) + Z * (0.016 * (1 - math.cos(b)))
            for b in [math.pi / 2 * i / 10 for i in range(1, 11)]]
    rise += line(rise[-1] + Z * 0.001, rise[-1] + Z * 0.008)[1:]
    return s1, sp, rise, s2


# ---- arms + scroll hands
def arm(side):
    sh, el, ha = (S_L, P['el_l'], P['ha_l']) if side == 'l' else (S_R, P['el_r'], P['ha_r'])
    F = (ha - el).normalized()
    n = to_cam(ha)
    n = (n - F * n.dot(F)).normalized()
    S = F.cross(n).normalized()
    if S.z < 0:
        S = -S
    r0, r1, aa = 0.046, 0.012, 0.012
    W = ha - S * r0 - F * aa
    start = N0 + (X * 0.026 if side == 'l' else -X * 0.026)
    path = fillet([start, sh, el, W], 0.05)
    s1, s2 = twisted(path, d0=-Z, d1=n)          # strand 1 low at the neck; strand 2 behind the hand plane
    # scroll: continues straight from the wrist and curls toward S, 1.5 turns
    scr = []
    tot = 3 * math.pi
    m = 160
    for i in range(m + 1):
        th = tot * i / m
        r = r0 + (r1 - r0) * th / tot
        scr.append(ha + S * (-math.cos(th) * r) + F * (math.sin(th) * r))
    E = scr[-1]
    back = n * -0.025
    ret = [way(E + back * 0.6 - F * 0.006, -F), way(ha - S * 0.016 + back - F * 0.01, -S * 0.6 - F)]
    return s1, scr, ret, s2


# ------------------------------------------------------------------ build splines
splines = []

# A: lower body.  bead -> spine strand down -> pelvis loop -> left leg & foot -> pelvis -> right leg & foot -> pelvis -> spine strand up -> bead
lsp = line(spine(BEAD_Z + 0.004), spine(1.036))
a1, a2 = twisted(lsp, d1=X)
lL = leg('l')
lR = leg('r')
A = chain([
    a1,
    pel_arc(76, -36),
    lL[0], lL[1], lL[2], lL[3],
    pel_arc(-72, -108),
    lR[0], lR[1], lR[2], lR[3],
    pel_arc(-144, -256),
    a2,
], ks=[0.9, 0.9, 0.8, 0.6, 1.25, 0.9, 0.9, 0.8, 0.6, 1.25, 0.9, 0.9])
splines.append(A)

# B + C: upper body.
usp = line(spine(BEAD_Z - 0.004), spine(1.386))
b1, c1 = twisted(usp, d1=X)                       # B on +x at the top (peels off to the left shoulder)
c1 = c1[::-1]                                     # C runs upward too
aL = arm('l')
aR = arm('r')
nk_path = line(Vector((0.0, 0.02, 1.414)), Vector((HEAD_AX.x, HEAD_AX.y, HZ0 + 0.004)))
nb, nc = twisted(nk_path, d0=-X, d1=Vector((-math.cos(math.radians(105)), -math.sin(math.radians(105)), 0)))  # C ends up at TH_BK
nc = nc[::-1]


def hr(t):
    return HR * math.sin(math.pi * t) ** 0.7


def hpt(t, th, off=0.0):
    r = hr(t) + off
    return Vector((HEAD_AX.x + r * math.cos(th), HEAD_AX.y + r * math.sin(th), HZ0 + HH * t))


def hth(t):                                       # one continuous winding; front at t = 0.5
    return TH_F - 2 * math.pi * HTURNS * (t - 0.5)


def coil(t0, t1):
    n = max(60, int(2600 * (t1 - t0)))
    return [hpt(t0 + (t1 - t0) * i / n, hth(t0 + (t1 - t0) * i / n)) for i in range(n + 1)]


# head = a ball of coils wound by the two neck strands: B winds the lower half and ends as the nose,
# C climbs the back (hidden behind the ball) and winds the upper half.  No wire runs through the inside.
T_B0 = 0.5 - 3.0 / HTURNS                          # B starts at the front, just above the neck
TH_BK = math.radians(105.0)                        # back-left, where the coil rings bunch up in this camera's view
T_C0 = 0.5 + ((TH_F - TH_BK) % (2 * math.pi)) / (2 * math.pi * HTURNS)   # C starts there, one pitch above B's last pass
zc = HZ0 + HH * 0.5
hcB = coil(T_B0, 0.478)
nose = line(hpt(0.5, TH_F) + Vector((0.004, 0, 0)), hpt(0.5, TH_F, 0.068) - Z * 0.008)
B = chain([b1, aL[0], aL[1], aL[2][0], aL[2][1], aL[3], aR[0], aR[1], aR[2][0], aR[2][1], aR[3], nb, hcB, nose],
          ks=[0.9, 0.7, 0.7, 0.8, 0.8, 1.0, 0.7, 0.7, 0.8, 0.8, 0.9, 0.9, 0.9])
splines.append(B)

# C: spine strand 2 -> (bulges behind the shoulder crossing) -> neck strand 2 -> up the back of the ball -> upper coil -> tucked end
mer = []
for i in range(80):
    t = 0.035 + (T_C0 - 0.018 - 0.035) * i / 79
    t_in = T_C0 - 0.075
    off = 2 * WR + 0.002 if t < t_in else (2 * WR + 0.002) * max(0.0, (T_C0 - 0.012 - t) / (T_C0 - 0.012 - t_in))
    mer.append(hpt(t, TH_BK, off))
mer = resample(mer)
hcC = coil(T_C0, 0.986)
tuck = herm(hcC[-1], tan_end(hcC), Vector((HEAD_AX.x, HEAD_AX.y, 1.722)), -Z, 0.8)
Cc = chain([c1, way(Vector((0, 0.02 + 0.027, 1.400)), Z), nc, mer, hcC], ks=[0.8, 0.8, 0.8, 0.9])
Cc += tuck + [Vector((HEAD_AX.x, HEAD_AX.y, 1.722))]
splines.append(Cc)


# ------------------------------------------------------------------ chest ring (closed loop, no ends)
RING_Z, RING_H, RING_OFF = 1.21, 0.15, 0.029


def chest_ring():
    us = Vector((0, 0.04, 1)).normalized()
    f = X.cross(us).normalized()                  # front (-y)
    c = spine(RING_Z) + f * RING_OFF
    out = []
    n = 420
    for i in range(n):
        s = 2 * math.pi * i / n
        x = 0.15 * math.sin(s)
        zz = RING_H * math.cos(s)
        cup = math.radians(15)
        out.append(c + X * (x * math.cos(cup)) + us * zz - f * (abs(x) * math.sin(cup)) * (abs(x) / 0.15) ** 0.6)
    return out


ring = chest_ring()


# ------------------------------------------------------------------ small lashings (thin copper binding wire)
def lashing(zc_, below_off, turns=4, pitch=0.0075, rw=0.0034):
    us = Vector((0, 0.04, 1)).normalized()
    f = X.cross(us).normalized()
    c0 = spine(zc_)
    ax = 2 * WR + rw + 0.0012
    lo = -(below_off + WR + rw + 0.0012)
    hi = 2 * WR + rw + 0.0012
    cf, af = (lo + hi) / 2, (hi - lo) / 2
    n = int(turns * 60)
    out = []
    for i in range(n + 1):
        t = i / n
        th = 2 * math.pi * turns * t
        out.append(c0 + us * (pitch * turns * (t - 0.5)) + X * (ax * math.cos(th)) + f * (cf + af * math.sin(th)))
    # tuck the ends inward
    out = [out[0].lerp(c0 + f * cf, 0.35)] + out + [out[-1].lerp(c0 + f * cf, 0.35)]
    return out


lash = [lashing(RING_Z + RING_H, RING_OFF), lashing(RING_Z - RING_H, RING_OFF)]


def collar(z0, z1, turns=4, rw=0.0034):
    # neat binding round the neck pair, just above the shoulder junction
    c = Vector((0.0, 0.02, 0.0))
    rr = 2 * WR + rw + 0.0012
    n = int(turns * 60)
    out = []
    for i in range(n + 1):
        t = i / n
        th = 2 * math.pi * turns * t
        zz = z0 + (z1 - z0) * t
        cy = 0.02 + (HEAD_AX.y - 0.02) * (zz - 1.414) / (HZ0 + 0.004 - 1.414)
        out.append(Vector((c.x + rr * math.cos(th), cy + rr * math.sin(th), zz)))
    cz = lambda p: Vector((c.x, 0.02 + (HEAD_AX.y - 0.02) * (p.z - 1.414) / (HZ0 + 0.004 - 1.414), p.z))
    return [out[0].lerp(cz(out[0]), 0.4)] + out + [out[-1].lerp(cz(out[-1]), 0.4)]


lash.append(collar(1.428, 1.452))

DRY = os.environ.get('HARIGANE_DRY')

# ------------------------------------------------------------------ materials
def copper_mat():
    m = bpy.data.materials.new('copper')
    m.use_nodes = True
    nt = m.node_tree
    Nn, Lk = nt.nodes, nt.links
    out = Nn['Material Output']
    bs = Nn['Principled BSDF']
    tc = Nn.new('ShaderNodeTexCoord')
    bs.inputs['Metallic'].default_value = 1.0
    # roughness 0.16 - 0.30
    n1 = Nn.new('ShaderNodeTexNoise')
    n1.inputs['Scale'].default_value = 25
    n1.inputs['Detail'].default_value = 6
    Lk.new(tc.outputs['Object'], n1.inputs['Vector'])
    mr = Nn.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = 0.32
    mr.inputs['From Max'].default_value = 0.68
    mr.inputs['To Min'].default_value = 0.16
    mr.inputs['To Max'].default_value = 0.30
    Lk.new(n1.outputs['Fac'], mr.inputs['Value'])
    Lk.new(mr.outputs['Result'], bs.inputs['Roughness'])
    # oxidation smudge up to 25 %
    n2 = Nn.new('ShaderNodeTexNoise')
    n2.inputs['Scale'].default_value = 30
    n2.inputs['Detail'].default_value = 4
    Lk.new(tc.outputs['Object'], n2.inputs['Vector'])
    r2 = Nn.new('ShaderNodeMapRange')
    r2.inputs['From Min'].default_value = 0.36
    r2.inputs['From Max'].default_value = 0.66
    r2.inputs['To Min'].default_value = 0.0
    r2.inputs['To Max'].default_value = 0.25
    Lk.new(n2.outputs['Fac'], r2.inputs['Value'])
    mx = Nn.new('ShaderNodeMix')
    mx.data_type = 'RGBA'
    mx.inputs['A'].default_value = (0.93, 0.52, 0.34, 1)
    mx.inputs['B'].default_value = (0.45, 0.20, 0.10, 1)
    Lk.new(r2.outputs['Result'], mx.inputs['Factor'])
    Lk.new(mx.outputs['Result'], bs.inputs['Base Color'])
    # micro dents
    n4 = Nn.new('ShaderNodeTexNoise')
    n4.inputs['Scale'].default_value = 140
    Lk.new(tc.outputs['Object'], n4.inputs['Vector'])
    bump = Nn.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.06
    bump.inputs['Distance'].default_value = 0.002
    Lk.new(n4.outputs['Fac'], bump.inputs['Height'])
    Lk.new(bump.outputs['Normal'], bs.inputs['Normal'])
    # verdigris in crevices
    ao = Nn.new('ShaderNodeAmbientOcclusion')
    ao.only_local = True
    ao.samples = 6
    ao.inputs['Distance'].default_value = 0.03
    lt = Nn.new('ShaderNodeMath')
    lt.operation = 'LESS_THAN'
    lt.inputs[1].default_value = 0.5
    Lk.new(ao.outputs['AO'], lt.inputs[0])
    n3 = Nn.new('ShaderNodeTexNoise')
    n3.inputs['Scale'].default_value = 8
    n3.inputs['Detail'].default_value = 3
    Lk.new(tc.outputs['Object'], n3.inputs['Vector'])
    gt = Nn.new('ShaderNodeMath')
    gt.operation = 'GREATER_THAN'
    gt.inputs[1].default_value = 0.6
    Lk.new(n3.outputs['Fac'], gt.inputs[0])
    mul = Nn.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    Lk.new(lt.outputs[0], mul.inputs[0])
    Lk.new(gt.outputs[0], mul.inputs[1])
    vd = Nn.new('ShaderNodeBsdfPrincipled')
    vd.inputs['Base Color'].default_value = (0.078, 0.332, 0.254, 1)
    vd.inputs['Metallic'].default_value = 0.0
    vd.inputs['Roughness'].default_value = 0.85
    ms = Nn.new('ShaderNodeMixShader')
    Lk.new(mul.outputs[0], ms.inputs['Fac'])
    Lk.new(bs.outputs['BSDF'], ms.inputs[1])
    Lk.new(vd.outputs['BSDF'], ms.inputs[2])
    Lk.new(ms.outputs['Shader'], out.inputs['Surface'])
    return m


def walnut_mat():
    m = bpy.data.materials.new('walnut')
    m.use_nodes = True
    nt = m.node_tree
    Nn, Lk = nt.nodes, nt.links
    bs = Nn['Principled BSDF']
    tc = Nn.new('ShaderNodeTexCoord')
    wv = Nn.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS'
    wv.bands_direction = 'X'
    wv.inputs['Scale'].default_value = 6
    wv.inputs['Distortion'].default_value = 6
    wv.inputs['Detail'].default_value = 3
    wv.inputs['Detail Scale'].default_value = 1.5
    mp = Nn.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (14, 14, 3)
    Lk.new(tc.outputs['Object'], mp.inputs['Vector'])
    Lk.new(mp.outputs['Vector'], wv.inputs['Vector'])
    rp = Nn.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = (0.030, 0.012, 0.006, 1)
    rp.color_ramp.elements[1].color = (0.095, 0.045, 0.020, 1)
    rp.color_ramp.elements[0].position = 0.15
    Lk.new(wv.outputs['Fac'], rp.inputs['Fac'])
    # fine pores
    nz = Nn.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 600
    Lk.new(mp.outputs['Vector'], nz.inputs['Vector'])
    mm = Nn.new('ShaderNodeMix')
    mm.data_type = 'RGBA'
    mm.blend_type = 'MULTIPLY'
    mm.inputs['Factor'].default_value = 0.25
    Lk.new(rp.outputs['Color'], mm.inputs['A'])
    Lk.new(nz.outputs['Color'], mm.inputs['B'])
    Lk.new(mm.outputs['Result'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.4
    bs.inputs['Coat Weight'].default_value = 0.5
    bs.inputs['Coat Roughness'].default_value = 0.08
    return m


def iron_mat(threads=False):
    m = bpy.data.materials.new('iron_thread' if threads else 'iron')
    m.use_nodes = True
    nt = m.node_tree
    Nn, Lk = nt.nodes, nt.links
    out = Nn['Material Output']
    bs = Nn['Principled BSDF']
    tc = Nn.new('ShaderNodeTexCoord')
    bs.inputs['Base Color'].default_value = (0.023, 0.023, 0.025, 1)
    bs.inputs['Metallic'].default_value = 0.85
    bs.inputs['Roughness'].default_value = 0.55
    # worn bright steel on edges
    geo = Nn.new('ShaderNodeNewGeometry')
    pr = Nn.new('ShaderNodeMapRange')
    pr.inputs['From Min'].default_value = 0.62
    pr.inputs['From Max'].default_value = 0.70
    pr.inputs['To Max'].default_value = 0.0 if threads else 0.85
    Lk.new(geo.outputs['Pointiness'], pr.inputs['Value'])
    st = Nn.new('ShaderNodeBsdfPrincipled')
    st.inputs['Base Color'].default_value = (0.55, 0.55, 0.56, 1)
    st.inputs['Metallic'].default_value = 1.0
    st.inputs['Roughness'].default_value = 0.3
    m1 = Nn.new('ShaderNodeMixShader')
    Lk.new(pr.outputs['Result'], m1.inputs['Fac'])
    Lk.new(bs.outputs['BSDF'], m1.inputs[1])
    Lk.new(st.outputs['BSDF'], m1.inputs[2])
    # rust patches
    nz = Nn.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 4
    nz.inputs['Detail'].default_value = 8
    nz.inputs['Roughness'].default_value = 0.65
    Lk.new(tc.outputs['Object'], nz.inputs['Vector'])
    rr = Nn.new('ShaderNodeMapRange')
    rr.inputs['From Min'].default_value = 0.62
    rr.inputs['From Max'].default_value = 0.66
    Lk.new(nz.outputs['Fac'], rr.inputs['Value'])
    ru = Nn.new('ShaderNodeBsdfPrincipled')
    ru.inputs['Base Color'].default_value = (0.254, 0.044, 0.006, 1)
    ru.inputs['Metallic'].default_value = 0.0
    ru.inputs['Roughness'].default_value = 0.9
    m2 = Nn.new('ShaderNodeMixShader')
    Lk.new(rr.outputs['Result'], m2.inputs['Fac'])
    Lk.new(m1.outputs['Shader'], m2.inputs[1])
    Lk.new(ru.outputs['BSDF'], m2.inputs[2])
    Lk.new(m2.outputs['Shader'], out.inputs['Surface'])
    if threads:
        wv = Nn.new('ShaderNodeTexWave')
        wv.wave_type = 'BANDS'
        wv.bands_direction = 'Z'
        wv.inputs['Scale'].default_value = 120
        wv.inputs['Distortion'].default_value = 0
        Lk.new(tc.outputs['Object'], wv.inputs['Vector'])
        bp = Nn.new('ShaderNodeBump')
        bp.inputs['Strength'].default_value = 0.5
        bp.inputs['Distance'].default_value = 0.002
        Lk.new(wv.outputs['Fac'], bp.inputs['Height'])
        for sh in (bs, st, ru):
            Lk.new(bp.outputs['Normal'], sh.inputs['Normal'])
    return m


COP = copper_mat()
WAL = walnut_mat()
IRON = iron_mat()
IRON_T = iron_mat(True)

# ------------------------------------------------------------------ objects
root = bpy.data.objects.new('harigane_root', None)
bpy.context.scene.collection.objects.link(root)
root.rotation_euler = (0, 0, math.radians(YAW))


def curve_obj(name, spl_list, depth, res=3, cyclic=False):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_mode = 'ROUND'
    cu.bevel_depth = depth
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    cu.twist_mode = 'MINIMUM'
    for pts in spl_list:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            sp.points[i].co = (p.x, p.y, p.z, 1.0)
        sp.use_smooth = True
        sp.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(COP)
    o.parent = root
    return o


body = curve_obj('harigane_wire', splines, WR, 3)
ringo = curve_obj('chest_ring', [ring], WR, 3, cyclic=True)
lasho = curve_obj('lashing', lash, 0.0034, 2)

# walnut bead on the spine, with copper bushings top and bottom
us = Vector((0, 0.04, 1)).normalized()
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=BEAD_R, location=BEAD_C)
bead = bpy.context.object
bead.name = 'walnut_bead'
bead.scale = (1, 1, 0.85)
bead.rotation_mode = 'QUATERNION'
bead.rotation_quaternion = us.to_track_quat('Z', 'Y')
bpy.ops.object.shade_smooth()
bead.data.materials.append(WAL)
bead.parent = root
for sgn in (1, -1):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0275, minor_radius=0.0045, major_segments=48, minor_segments=12,
                                     location=BEAD_C + us * (sgn * BEAD_R * 0.85 * 0.83))
    t = bpy.context.object
    t.rotation_mode = 'QUATERNION'
    t.rotation_quaternion = us.to_track_quat('Z', 'Y')
    t.scale = (1, 1, 0.7)
    bpy.ops.object.shade_smooth()
    t.data.materials.append(COP)
    t.parent = root


# ------------------------------------------------------------------ mooks: BOLTS
def _orient(o, axis, roll=0.0):
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = Vector(axis).to_track_quat('Z', 'Y') @ Quaternion(Z, roll)


def hexnut(c, axis, r, depth, bore, m, bevel=0.008, roll=0.0, verts=6):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=c)
    o = bpy.context.object
    _orient(o, axis, roll)
    if bore:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=bore, depth=depth * 3, location=c)
        cut = bpy.context.object
        _orient(cut, axis, roll)
        cut.hide_render = True
        cut.display_type = 'WIRE'
        md = o.modifiers.new('bore', 'BOOLEAN')
        md.object = cut
        md.operation = 'DIFFERENCE'
        md.solver = 'EXACT'
    bv = o.modifiers.new('bevel', 'BEVEL')
    bv.width = bevel
    bv.segments = 2
    bv.limit_method = 'ANGLE'
    o.data.materials.append(m)
    return o


def bolt(p0, p1, r, m):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    _orient(o, d)
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m)
    return o


def mook(M, psi_deg, mirror=False, s=0.914, roll=0.0):
    Rm = Matrix.Rotation(math.radians(psi_deg), 3, 'Z')

    def W(v):
        v = Vector(v) * s
        if mirror:
            v.x = -v.x
        return Vector(M) + Rm @ v
    j = {k: W(v) for k, v in POSE_LOCAL.items()}
    up = (j['neck'] - j['hip']).normalized()
    fwd = Rm @ Vector((0, -1, 0))
    hip = j['hip']
    # pelvis bolt head + 3 stacked nuts on a carriage-bolt spine
    hexnut(hip + up * 0.02, up, 0.10, 0.06, 0, IRON, 0.006, roll + 0.3)
    z0 = 0.06
    for i in range(3):
        hexnut(hip + up * (z0 + 0.065 + 0.132 * i), up, 0.17, 0.13, 0.06, IRON, 0.008, roll + 0.25 * i)
    top = hip + up * (z0 + 0.396)
    bolt(hip + up * 0.04, top + up * 0.085, 0.055, IRON_T)
    # domed carriage head as the neck cap
    sphere(top + up * 0.085, 0.06, IRON, scale=(1, 1, 0.55))
    # head: thick washer standing upright, face toward the hero
    hc = top + up * 0.2
    hexnut(hc, fwd, 0.12, 0.045, 0.045, IRON, 0.006, 0, verts=48)
    # limbs: threaded bolts, joint nuts, hex-head hands and feet
    for sh, el, ha in (('sh_l', 'el_l', 'ha_l'), ('sh_r', 'el_r', 'ha_r')):
        shp = j[sh] + (j[sh] - top).normalized() * 0.0 - up * 0.04
        bolt(shp, j[el], 0.05, IRON_T)
        hexnut(j[el], (j[el] - shp).normalized() + (j[ha] - j[el]).normalized(), 0.072, 0.07, 0, IRON, 0.006)
        bolt(j[el], j[ha], 0.05, IRON_T)
        ax = (j[ha] - j[el]).normalized()
        hexnut(j[ha] + ax * 0.02, ax, 0.075, 0.05, 0, IRON, 0.006)
    for kn, ft, sx in (('kn_l', 'ft_l', 1), ('kn_r', 'ft_r', -1)):
        hp = hip + (Rm @ Vector((sx * (-1 if mirror else 1) * 0.07, 0, 0))) - up * 0.01
        foot = Vector((j[ft].x, j[ft].y, 0.026))
        bolt(hp, j[kn], 0.05, IRON_T)
        hexnut(j[kn], (j[kn] - hp).normalized() + (foot - j[kn]).normalized(), 0.072, 0.07, 0, IRON, 0.006)
        bolt(j[kn], foot + Z * 0.02, 0.05, IRON_T)
        hexnut(foot, Z, 0.075, 0.05, 0, IRON, 0.006, roll)


MOOKS = [((-2.0, 3.0, 0.0), False), ((-0.35, 3.35, 0.0), True)]
for Mp, mir in MOOKS:
    # yaw so the mook's forward (-y local) points at the hero
    d = Vector((-Mp[0], -Mp[1], 0)).normalized()
    psi = math.degrees(math.atan2(d.x, -d.y))
    mook(Mp, psi, mirror=mir)


# ------------------------------------------------------------------ dark wall section behind the figure (yakisugi boards)
def yakisugi():
    m = bpy.data.materials.new('yakisugi')
    m.use_nodes = True
    nt = m.node_tree
    Nn, Lk = nt.nodes, nt.links
    bs = Nn['Principled BSDF']
    tc = Nn.new('ShaderNodeTexCoord')
    br = Nn.new('ShaderNodeTexBrick')
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = 0.16
    br.inputs['Row Height'].default_value = 20.0
    br.inputs['Mortar Size'].default_value = 0.004
    br.inputs['Color1'].default_value = (0.030, 0.024, 0.020, 1)
    br.inputs['Color2'].default_value = (0.020, 0.017, 0.015, 1)
    br.inputs['Mortar'].default_value = (0.004, 0.004, 0.004, 1)
    Lk.new(tc.outputs['Object'], br.inputs['Vector'])
    Lk.new(br.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.7
    return m


YK = yakisugi()
bpy.ops.mesh.primitive_plane_add(size=1, location=(-2.25, 5.74, 2.5), rotation=(math.radians(90), 0, 0))
wl = bpy.context.object
wl.scale = (2.3, 5.0, 1)
wl.data.materials.append(YK)
for x in (-3.42, -1.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 5.70, 2.5))
    bpy.context.object.scale = (0.12, 0.10, 5.0)
    bpy.context.object.data.materials.append(mat('post', (0.045, 0.026, 0.014), 0.5))

# ------------------------------------------------------------------ extra lights: 2700 K hard key (crisp contact shadows, sparkle) + cool kicker
bpy.ops.object.light_add(type='SPOT', location=(-2.3, -2.9, 3.6))
sp = bpy.context.object
sp.data.energy = 520
sp.data.use_temperature = True
sp.data.temperature = 2700
sp.data.color = (1, 1, 1)
sp.data.shadow_soft_size = 0.04
sp.data.spot_size = math.radians(20)
sp.data.spot_blend = 0.35
sp.rotation_euler = (Vector((0, 0, 0.85)) - sp.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.light_add(type='AREA', location=(-1.6, 2.6, 2.4))
kk = bpy.context.object
kk.data.energy = 300
kk.data.color = (0.6, 0.72, 1.0)
kk.data.size = 0.8
kk.rotation_euler = (Vector((0, 0, 1.1)) - kk.location).to_track_quat('-Z', 'Y').to_euler()

# focus on the head coil, f/2.8
sc = bpy.context.scene
cam = sc.camera
head_w = RZ @ Vector((HEAD_AX.x, HEAD_AX.y, HZ0 + HH * 0.5))
cam.data.dof.focus_distance = (head_w - cam.location).length
cam.data.dof.aperture_fstop = 2.8
sc.cycles.max_bounces = 6
sc.cycles.glossy_bounces = 4

if DRY:
    from bpy_extras.object_utils import world_to_camera_view
    def pr(name, pl):
        v = world_to_camera_view(sc, cam, RZ @ Vector(pl)) if not isinstance(pl, tuple) else world_to_camera_view(sc, cam, Vector(pl))
        print(name, round(v.x, 3), round(v.y, 3), round(v.z, 2))
    for k in ('head', 'ha_l', 'ha_r', 'ft_l', 'ft_r'):
        pr(k, P[k])
    pr('top', Vector((0, 0, 1.75)))
    for Mp, mir in MOOKS:
        pr('mook_feet', tuple(Mp))
        pr('mook_head', (Mp[0], Mp[1], 1.5))
    print('points', sum(len(s) for s in splines), 'A', len(A), 'B', len(B), 'C', len(Cc))
    print('lengths', [round(cumlen(s)[-1], 2) for s in splines])
else:
    bd = os.environ.get('HARIGANE_BORDER')        # optional detail check: render only a region (fractions x0,y0,x1,y1)
    if bd:
        x0, y0, x1, y1 = (float(v) for v in bd.split(','))
        sc.render.use_border = True
        sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = x0, y0, x1, y1
    finish(a)
