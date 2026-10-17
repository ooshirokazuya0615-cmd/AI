"""
Benchmark: procedural SDF blob mascot scene (hero jelly blob + heavy cube antagonist +
small friend + tuned xylophone stairs + 4 marbles) on a pastel cyclorama, raymarched in
GLSL via moderngl (same approach as tools/nonverbal/render.py).

Character animation is driven by uniforms only (position, squash, lid tilt/height,
pupil look), i.e. no meshes, no rigs.

  xvfb-run -a venv/bin/python blob_bench.py --ss 1 --frames 6
  xvfb-run -a venv/bin/python blob_bench.py --ss 1 --clip 120     # end-to-end with x264 slow
"""
import argparse
import json
import math
import subprocess
import time
from pathlib import Path

import moderngl
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--res', default='1080x1920')
ap.add_argument('--ss', type=int, default=1)
ap.add_argument('--frames', type=int, default=6)
ap.add_argument('--clip', type=int, default=0)
ap.add_argument('--refl', type=int, default=1, help='1 = one reflection bounce on glossy/metal')
ap.add_argument('--sss', type=int, default=1, help='1 = fake subsurface (thickness probe) on jelly')
ap.add_argument('--tag', default='')
a = ap.parse_args()
HERE = Path(__file__).resolve().parent
W, H = (int(v) for v in a.res.split('x'))

VERT = """#version 330
in vec2 in_pos; void main(){ gl_Position = vec4(in_pos,0,1); }"""

FRAG = r"""#version 330
out vec4 frag;
uniform vec2 uRes;
uniform int uSS;
uniform int uRefl;
uniform int uSSS;
uniform vec4 uHero;     // xyz position (feet centre), w squash (1 = rest, <1 squashed)
uniform vec4 uFace;     // x lid height (0 open .. 1 closed), y lid tilt (+ angry, - sad), zw pupil look
uniform vec4 uVillain;  // xyz position, w yaw
uniform vec4 uFriend;   // xyz position, w squash
uniform vec3 uMarble[4];

const vec3 CAM = vec3(0.0, -9.5, 3.0);
const vec3 TGT = vec3(0.0, 0.0, 1.35);
const float TANH = 12.0 / 30.0;
const vec3 LDIR = normalize(vec3(-0.45, -0.6, 0.9));

float smin(float a, float b, float k){ float h = clamp(0.5 + 0.5*(b-a)/k, 0.0, 1.0); return mix(b, a, h) - k*h*(1.0-h); }
float sdBox(vec3 p, vec3 b, float r){ vec3 q = abs(p) - b + r; return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0) - r; }
float sdEll(vec3 p, vec3 r){ float k0 = length(p/r); float k1 = length(p/(r*r)); return k0*(k0-1.0)/k1; }
mat2 rot(float a){ float c = cos(a), s = sin(a); return mat2(c,-s,s,c); }

// material ids: 1 floor/cyc, 2 jelly hero, 3 eye white, 4 pupil, 5 cheek, 6 metal villain,
// 7 friend, 8 bar (tuned), 9 marble, 10 mouth
vec2 opU(vec2 a, vec2 b){ return a.x < b.x ? a : b; }

vec2 eyes(vec3 q, float s, float er, float lidH, float tilt, vec2 look, float bodyId){
    // q is hero-local; eyes mirrored on x
    vec3 e = vec3(abs(q.x), q.y, q.z);
    vec3 c = vec3(0.21, -0.47*inversesqrt(s), 0.78*s);
    float white = length(e - c) - er;
    vec3 pc = c + vec3(look.x*sign(q.x)*0.0 + look.x, -0.11, look.y) * vec3(1.0, 1.0, 1.0);
    pc.x = c.x + look.x * sign(q.x) * 1.0 * (q.x > 0.0 ? 1.0 : -1.0) * 0.0 + look.x;
    float pupil = length(e - vec3(c.x + (q.x > 0.0 ? look.x : -look.x), c.y - 0.115, c.z + look.y)) - er*0.52;
    // lid: shell slightly larger than the eye, kept above a tilted plane
    vec3 l = e - c;
    vec3 pn = normalize(vec3(-tilt*0.9, 0.0, 1.0));
    float plane = -(dot(l, pn) - (1.0 - 2.0*lidH)*er*1.05);
    float lid = max(length(l) - er*1.08, plane);
    vec2 r = vec2(white, 3.0);
    r = opU(r, vec2(pupil, 4.0));
    r = opU(r, vec2(lid, bodyId));
    return r;
}

vec2 hero(vec3 p){
    vec3 q = p - uHero.xyz;
    float bound = length(q - vec3(0.0, 0.0, 0.7)) - 1.15;
    if (bound > 0.3) return vec2(bound, 2.0);
    float s = uHero.w;
    vec3 sc = vec3(inversesqrt(s), inversesqrt(s), s);
    float body = sdEll(q - vec3(0.0, 0.0, 0.62*s), vec3(0.62, 0.58, 0.60) * sc);
    vec3 f = vec3(abs(q.x), q.y, q.z);
    body = smin(body, length(f - vec3(0.30*sc.x, -0.05, 0.14)) - 0.17, 0.18);
    body = smin(body, length(q - vec3(0.0, 0.05, 1.22*s)) - 0.10, 0.16);       // sprout nub
    float mouth = sdEll(q - vec3(0.0, -0.56*sc.y, 0.50*s), vec3(0.09, 0.05, 0.035));
    body = max(body, -mouth);
    vec2 r = vec2(body, 2.0);
    float cheek = length(f - vec3(0.36*sc.x, -0.47*sc.y, 0.56*s)) - 0.075;
    r = opU(r, vec2(max(cheek, body - 0.004), 5.0));
    r = opU(r, vec2(max(mouth - 0.01, body + 0.01) , 10.0));
    r = opU(r, eyes(q, s, 0.15, uFace.x, uFace.y, uFace.zw, 2.0));
    return r;
}

vec2 villain(vec3 p){
    vec3 q = p - uVillain.xyz;
    float bound = length(q - vec3(0.0, 0.0, 0.7)) - 1.25;
    if (bound > 0.3) return vec2(bound, 6.0);
    q.xy = rot(uVillain.w) * q.xy;
    q.z -= 0.7;
    vec2 r = vec2(sdBox(q, vec3(0.7), 0.12), 6.0);
    vec3 e = vec3(abs(q.x), q.y, q.z);
    float white = sdEll(e - vec3(0.27, -0.70, 0.18), vec3(0.15, 0.05, 0.11));
    float pupil = length(e - vec3(0.24, -0.74, 0.15)) - 0.055;
    vec3 b = e - vec3(0.27, -0.72, 0.36); b.xz = rot(0.45) * b.xz;
    float brow = sdBox(b, vec3(0.2, 0.05, 0.04), 0.02);
    r = opU(r, vec2(white, 3.0));
    r = opU(r, vec2(pupil, 4.0));
    r = opU(r, vec2(brow, 4.0));
    return r;
}

vec2 friend(vec3 p){
    vec3 q = p - uFriend.xyz;
    float bound = length(q - vec3(0.0, 0.0, 0.3)) - 0.55;
    if (bound > 0.3) return vec2(bound, 7.0);
    float s = uFriend.w;
    vec3 sc = vec3(inversesqrt(s), inversesqrt(s), s);
    float body = sdEll(q - vec3(0.0, 0.0, 0.27*s), vec3(0.28, 0.26, 0.27) * sc);
    vec2 r = vec2(body, 7.0);
    vec3 e = vec3(abs(q.x), q.y, q.z);
    r = opU(r, vec2(length(e - vec3(0.10, -0.215, 0.33*s)) - 0.06, 3.0));
    r = opU(r, vec2(length(e - vec3(0.10, -0.265, 0.33*s)) - 0.032, 4.0));
    return r;
}

vec2 bars(vec3 p){
    // 7 tuned blocks as a descending staircase on the left
    vec3 q = p - vec3(-1.05, 1.6, -1.0);
    float bound = sdBox(q - vec3(0.0, 0.0, 1.6), vec3(1.3, 0.8, 1.8), 0.0);
    if (bound > 0.3) return vec2(bound, 8.0);
    float d = 1e9; float id = 0.0;
    for (int i = 0; i < 7; i++){
        float fi = float(i);
        float bx = sdBox(q - vec3(-0.9 + fi*0.3, 0.0, 3.1 - fi*0.42), vec3(0.14, 0.55, 0.06), 0.03);
        if (bx < d){ d = bx; id = fi; }
    }
    return vec2(d, 8.0 + id*0.01);
}

vec2 map(vec3 p){
    // floor + curved cyclorama behind (y = 3.5), radius 2.5
    float fl = p.z;
    vec2 yz = vec2(p.y - 1.0, p.z - 2.5);
    float cyc = (p.y > 1.0 && p.z < 2.5) ? 2.5 - length(yz) : (p.z >= 2.5 ? 3.5 - p.y : fl);
    vec2 r = vec2(cyc, 1.0);
    r = opU(r, hero(p));
    r = opU(r, villain(p));
    r = opU(r, friend(p));
    r = opU(r, bars(p));
    for (int i = 0; i < 4; i++) r = opU(r, vec2(length(p - uMarble[i]) - 0.16, 9.0 + float(i)*0.01));
    return r;
}

vec3 normalAt(vec3 p){
    vec2 e = vec2(0.0012, -0.0012);
    return normalize(e.xyy*map(p+e.xyy).x + e.yyx*map(p+e.yyx).x + e.yxy*map(p+e.yxy).x + e.xxx*map(p+e.xxx).x);
}
vec2 march(vec3 ro, vec3 rd, float tmax){
    float t = 0.0;
    for (int i = 0; i < 140; i++){
        vec2 h = map(ro + rd*t);
        if (abs(h.x) < 0.0007*t) return vec2(t, h.y);
        t += h.x;
        if (t > tmax) break;
    }
    return vec2(-1.0, 0.0);
}
float softShadow(vec3 ro, vec3 rd){
    float res = 1.0, t = 0.02;
    for (int i = 0; i < 32; i++){
        float h = 0.85*map(ro + rd*t).x;
        res = min(res, 6.0*h/t);
        t += clamp(h, 0.03, 0.5);
        if (res < 0.002 || t > 12.0) break;
    }
    return clamp(res, 0.0, 1.0);
}
float ao(vec3 p, vec3 n){
    float o = 0.0, s = 1.0;
    for (int i = 1; i <= 5; i++){ float h = 0.05*float(i); o += (h - map(p + n*h).x)*s; s *= 0.75; }
    return clamp(1.0 - 2.2*o, 0.0, 1.0);
}
vec3 barColor(float k){ return 0.55 + 0.45*cos(6.2831*(k/7.0 + vec3(0.0, 0.33, 0.67))); }

vec3 albedo(float id, vec3 p, out float rough, out float metal, out float jelly){
    rough = 0.5; metal = 0.0; jelly = 0.0;
    if (id < 1.5) return mix(vec3(0.98, 0.86, 0.80), vec3(0.80, 0.88, 1.0), clamp(p.z/5.0, 0.0, 1.0));
    if (id < 2.5){ rough = 0.18; jelly = 1.0; return vec3(0.18, 0.72, 0.52); }
    if (id < 3.5){ rough = 0.12; return vec3(0.97); }
    if (id < 4.5){ rough = 0.08; return vec3(0.02); }
    if (id < 5.5){ jelly = 1.0; rough = 0.3; return vec3(1.0, 0.55, 0.6); }
    if (id < 6.5){ rough = 0.28; metal = 1.0; return vec3(0.62, 0.64, 0.70); }
    if (id < 7.5){ rough = 0.2; jelly = 1.0; return vec3(1.0, 0.82, 0.25); }
    if (id < 8.9){ rough = 0.35; return barColor(floor((id - 8.0)*100.0 + 0.5)); }
    if (id < 9.9){ rough = 0.05; return vec3(0.75, 0.85, 1.0); }
    return vec3(0.25, 0.05, 0.08);
}
vec3 sky(vec3 rd){ return mix(vec3(0.95, 0.9, 0.88), vec3(0.75, 0.85, 1.0), clamp(rd.z*0.5+0.5, 0.0, 1.0)); }

vec3 shade(vec3 p, vec3 n, vec3 rd, float id, out float rough, out float metal){
    float jelly;
    vec3 alb = albedo(id, p, rough, metal, jelly);
    float sh = softShadow(p + n*0.01, LDIR);
    float occ = ao(p, n);
    float ndl = dot(n, LDIR);
    float dif = jelly > 0.5 ? clamp((ndl + 0.35)/1.35, 0.0, 1.0) : max(ndl, 0.0);   // wrap light for jelly
    vec3 hv = normalize(LDIR - rd);
    float sp = pow(max(dot(n, hv), 0.0), 2.0/(rough*rough*rough + 1e-3)) * (1.0/(rough + 0.05));
    vec3 base = metal > 0.5 ? alb*0.12 : alb;
    vec3 col = base * (1.6*dif*(0.2 + 0.8*sh)*vec3(1.0, 0.96, 0.9) + 0.7*occ*sky(n));
    if (jelly > 0.5 && uSSS == 1){
        // fake subsurface: how much material lies behind the surface along -n
        float th = 0.0;
        for (int i = 1; i <= 3; i++){ float d = 0.08*float(i); th += clamp(-map(p - n*d).x / d, 0.0, 1.0); }
        th /= 3.0;
        float back = pow(clamp(dot(rd, LDIR)*0.5 + 0.5, 0.0, 1.0), 2.0);
        col += alb * alb * (0.35 + 0.9*back) * (1.0 - th) * 0.9;
    }
    float rim = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    col += rim * 0.25 * sky(n) * occ;
    col += sp * sh * (metal > 0.5 ? alb : vec3(0.06)) * 0.8;
    return col;
}

vec3 render(vec3 ro, vec3 rd){
    vec2 h = march(ro, rd, 40.0);
    if (h.x < 0.0) return sky(rd);
    vec3 p = ro + rd*h.x, n = normalAt(p);
    float rough, metal;
    vec3 col = shade(p, n, rd, h.y, rough, metal);
    if (uRefl == 1 && (metal > 0.5 || rough < 0.2)){
        float f0 = metal > 0.5 ? 0.9 : 0.04;
        float fres = f0 + (1.0 - f0)*pow(1.0 - max(dot(n, -rd), 0.0), 5.0);
        vec3 rr = reflect(rd, n);
        vec2 h3 = march(p + n*0.01, rr, 20.0);
        vec3 refl = sky(rr);
        if (h3.x > 0.0){ vec3 q = p + n*0.01 + rr*h3.x; float r2, m2; refl = shade(q, normalAt(q), rr, h3.y, r2, m2); }
        float rk, mk, jk; vec3 tint = metal > 0.5 ? albedo(h.y, p, rk, mk, jk) : vec3(1.0);
        col = mix(col, refl*tint, clamp(fres*(1.0 - 0.6*rough), 0.0, 1.0));
    }
    return col;
}

void main(){
    vec3 fw = normalize(TGT - CAM);
    vec3 rt = normalize(cross(fw, vec3(0.0, 0.0, 1.0)));
    vec3 up = cross(rt, fw);
    vec3 acc = vec3(0.0);
    for (int sy = 0; sy < uSS; sy++) for (int sx = 0; sx < uSS; sx++){
        vec2 off = (vec2(sx, sy) + 0.5)/float(uSS) - 0.5;
        vec2 uv = (gl_FragCoord.xy + off - 0.5*uRes) / (0.5*uRes.y);
        vec3 rd = normalize(fw + (uv.x*rt + uv.y*up)*TANH);
        acc += render(CAM, rd);
    }
    vec3 col = acc / float(uSS*uSS);
    col = col / (1.0 + 0.6*col);
    col = pow(col, vec3(1.0/2.2));
    frag = vec4(col, 1.0);
}
"""


def ctx_create():
    for kw in ({}, {'backend': 'egl'}):
        try:
            return moderngl.create_standalone_context(require=330, **kw)
        except Exception as e:
            print('ctx fail', kw, e)
    raise SystemExit('no GL (run under xvfb-run)')


ctx = ctx_create()
print('GL_RENDERER', ctx.info['GL_RENDERER'])
t0 = time.perf_counter()
prog = ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
print(f'compile {time.perf_counter() - t0:.2f} s')
vbo = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())
vao = ctx.vertex_array(prog, [(vbo, '2f', 'in_pos')])
fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
fbo.use()
prog['uRes'].value = (W, H)
prog['uSS'].value = a.ss
prog['uRefl'].value = a.refl
prog['uSSS'].value = a.sss


def set_state(f, fps=60):
    """A tiny procedural animation: hero hops with squash, villain slides in, friend bounces."""
    t = f / fps
    hop = abs(math.sin(t * math.pi * 1.6))
    squash = 1.0 - 0.28 * max(0.0, 1.0 - hop * 4.0) + 0.12 * hop
    prog['uHero'].value = (-0.4 + 0.15 * math.sin(t), 0.0, 0.9 * hop, squash)
    prog['uFace'].value = (0.25 + 0.2 * math.sin(t * 2), 0.4 * math.sin(t * 0.7), 0.03 * math.sin(t * 3), 0.02)
    prog['uVillain'].value = (1.9 - 0.2 * math.sin(t), 0.3, 0.0, 0.15 * math.sin(t * 0.5))
    fh = abs(math.sin(t * math.pi * 2.3))
    prog['uFriend'].value = (0.85, -1.1, 0.35 * fh, 1.0 - 0.2 * max(0.0, 1.0 - fh * 5))
    m = np.array([[-1.75 + 0.3 * k, 1.6, 2.4 - 0.42 * k + 0.3 * abs(math.sin(t * 5 + k))] for k in range(4)], 'f4')
    prog['uMarble'].write(m.tobytes())


tag = a.tag or f'blob_ss{a.ss}_refl{a.refl}_sss{a.sss}'
if a.clip:
    out = HERE / f'{tag}_clip.mp4'
    ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
                           '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '60', '-i', '-',
                           '-vf', 'vflip,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
                           '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', str(out)], stdin=subprocess.PIPE)
    t0 = time.perf_counter()
    for f in range(a.clip):
        set_state(f)
        vao.render(moderngl.TRIANGLE_STRIP)
        ff.stdin.write(fbo.read(components=3, alignment=1))
    ff.stdin.close(); ff.wait()
    el = time.perf_counter() - t0
    print(f'CLIP {tag} {a.clip} frames end-to-end {el:.1f} s = {el / a.clip:.3f} s/frame -> {out.name}')
    with open(HERE / 'bench_results.jsonl', 'a') as fh:
        fh.write(json.dumps(dict(tag=tag + '_clip', engine='GLSL-blob', res=a.res, frames=a.clip,
                                 s_per_frame_e2e=el / a.clip)) + '\n')
    raise SystemExit

times = []
for f in range(a.frames):
    set_state(f * 17)
    t0 = time.perf_counter()
    vao.render(moderngl.TRIANGLE_STRIP)
    data = fbo.read(components=3, alignment=1)
    times.append(time.perf_counter() - t0)
    print(f'BENCH {tag} frame {f}: {times[-1]:.3f} s', flush=True)
    if f == 1:
        (HERE / 'renders').mkdir(exist_ok=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-i', '-', '-vf', 'vflip',
                        '-frames:v', '1', str(HERE / f'test_{tag}.png')], input=data, check=True)
steady = sorted(times[1:])[len(times[1:]) // 2]
res = dict(tag=tag, engine='GLSL-blob', res=a.res, samples=a.ss * a.ss, times=times, first=times[0], median_steady=steady)
print('RESULT', json.dumps(res))
with open(HERE / 'bench_results.jsonl', 'a') as fh:
    fh.write(json.dumps(res) + '\n')
