"""
Raymarched SDF version of the same marble/peg scene, rendered with moderngl
(same approach as tools/nonverbal/render.py). Ball positions come from the
Blender/Bullet bake (traj.json), so physics, events and audio are shared.

  xvfb-run -a venv/bin/python glsl_bench.py --frames 300,301,302 --ss 1
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import moderngl
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--frames', default='300,301,302')
ap.add_argument('--res', default='1080x1920')
ap.add_argument('--ss', type=int, default=1, help='supersampling grid (1 = 1 spp, 2 = 4 spp)')
ap.add_argument('--tag', default='')
ap.add_argument('--png', type=int, default=1)
ap.add_argument('--clip', default='', help='START,COUNT: encode an MP4 clip with --audio instead of benchmarking')
ap.add_argument('--audio', default='')
a = ap.parse_args()

HERE = Path(__file__).resolve().parent
W, H = (int(v) for v in a.res.split('x'))
traj = json.loads((HERE / 'traj.json').read_text())
NB = len(traj['pos'])

VERT = """#version 330
in vec2 in_pos; void main(){ gl_Position = vec4(in_pos,0,1); }"""

FRAG = """#version 330
out vec4 frag;
uniform vec2 uRes;
uniform int uSS;
uniform vec3 uBall[NB];
const float R = 0.30;
const vec3 CAM = vec3(0.0, -25.0, 8.6);
const float TANH = 12.0 / 35.0;          // 35 mm lens, 24 mm vertical sensor (same as Blender)
const vec3 LDIR = normalize(vec3(-5.0, -12.0, 20.0) - vec3(0.0, 0.0, 8.0));

float sdBox(vec3 p, vec3 b){ vec3 q = abs(p) - b; return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0) - 0.03; }
mat2 rot(float a){ float c = cos(a), s = sin(a); return mat2(c,-s,s,c); }
float sdRamp(vec3 p, vec3 c, float len, float ang){
    p -= c; p.xz = rot(-ang) * p.xz; return sdBox(p, vec3(len*0.5-0.03, 0.55-0.03, 0.125-0.03));
}
float sdPegs(vec3 p){
    // 5 staggered rows, pitch 1.1, cylinders along y (r = 0.12, half length 0.5)
    float d = 1e9;
    for (int row = 0; row < 5; row++){
        float z = 8.6 - float(row);
        float off = (row % 2 == 0) ? 0.0 : 0.55;
        float n = (row % 2 == 0) ? 7.0 : 6.0;
        float x0 = -3.85 + off;
        float i = clamp(floor((p.x - x0) / 1.1 + 0.5), 0.0, n);
        vec2 q = vec2(p.x - (x0 + 1.1*i), p.z - z);
        vec2 dd = abs(vec2(length(q), p.y)) - vec2(0.12, 0.5);
        d = min(d, min(max(dd.x,dd.y),0.0) + length(max(dd,0.0)));
    }
    return d;
}
float sdDividers(vec3 p){
    float d = 1e9;
    float xs[6] = float[](-3.3,-2.0,-0.7,0.7,2.0,3.3);
    for (int i = 0; i < 6; i++) d = min(d, sdBox(p - vec3(xs[i], 0.0, 1.6), vec3(0.06, 0.5, 1.0)));
    return d;
}
// material ids: 1 wall, 2 ramp, 3 peg, 4 frame, 10+i ball i
vec2 mapStatic(vec3 p){
    vec2 r = vec2(sdBox(p - vec3(0.0, 0.52, 8.5), vec3(6.0, 0.1, 11.0)), 1.0);
    float f = min(sdBox(vec3(abs(p.x), p.yz) - vec3(4.85, 0.0, 8.5), vec3(0.15, 0.6, 11.0)),
                  sdBox(p - vec3(0.0, 0.0, 0.4), vec3(5.0, 0.6, 0.2)));
    f = min(f, sdDividers(p));
    if (f < r.x) r = vec2(f, 4.0);
    float rp = min(sdRamp(p, vec3(-1.4, 0.0, 14.0), 6.8, radians(16.0)),
                   sdRamp(p, vec3(1.8, 0.0, 11.0), 6.2, radians(-19.0)));
    if (rp < r.x) r = vec2(rp, 2.0);
    float pg = sdPegs(p);
    if (pg < r.x) r = vec2(pg, 3.0);
    return r;
}
vec2 map(vec3 p){
    vec2 r = mapStatic(p);
    for (int i = 0; i < NB; i++){
        float d = length(p - uBall[i]) - R;
        if (d < r.x) r = vec2(d, 10.0 + float(i));
    }
    return r;
}
vec3 normalAt(vec3 p){
    vec2 e = vec2(0.0015, 0.0);
    return normalize(vec3(map(p+e.xyy).x - map(p-e.xyy).x, map(p+e.yxy).x - map(p-e.yxy).x,
                          map(p+e.yyx).x - map(p-e.yyx).x));
}
vec2 march(vec3 ro, vec3 rd, float tmax){
    float t = 0.0;
    for (int i = 0; i < 160; i++){
        vec2 h = map(ro + rd*t);
        if (h.x < 0.0008*t) return vec2(t, h.y);
        t += h.x;
        if (t > tmax) break;
    }
    return vec2(-1.0, 0.0);
}
float softShadow(vec3 ro, vec3 rd){
    float res = 1.0, t = 0.02;
    for (int i = 0; i < 32; i++){
        float h = map(ro + rd*t).x;
        res = min(res, 4.0*h/t);
        t += clamp(h, 0.03, 0.6);
        if (res < 0.002 || t > 20.0) break;
    }
    return clamp(res, 0.0, 1.0);
}
float ao(vec3 p, vec3 n){
    float o = 0.0, s = 1.0;
    for (int i = 1; i <= 5; i++){
        float h = 0.06 * float(i);
        o += (h - map(p + n*h).x) * s; s *= 0.7;
    }
    return clamp(1.0 - 2.5*o, 0.0, 1.0);
}
vec3 ballColor(int i){
    int k = i % 7;
    if (k == 0) return vec3(0.55, 0.95, 1.0);
    if (k == 1) return vec3(0.85, 0.05, 0.07);
    if (k == 2) return vec3(1.0, 0.45, 0.10);
    if (k == 3) return vec3(1.0, 0.75, 0.35);
    if (k == 4) return vec3(0.05, 0.20, 0.85);
    if (k == 5) return vec3(1.0, 0.35, 0.60);
    return vec3(1.0, 0.75, 0.30);
}
vec3 sky(vec3 rd){ return mix(vec3(0.05,0.06,0.09), vec3(0.5,0.55,0.65), clamp(rd.z*0.5+0.5,0.0,1.0)); }

// direct + ambient shading of a diffuse/glossy surface (no secondary rays)
vec3 shade(vec3 p, vec3 n, vec3 rd, float id, out float spec){
    vec3 alb; float rough = 0.5; spec = 0.04;
    if (id < 1.5) alb = vec3(0.42, 0.40, 0.45);
    else if (id < 2.5){ alb = vec3(0.13, 0.15, 0.20); rough = 0.25; spec = 0.08; }
    else if (id < 3.5){ alb = vec3(0.92, 0.92, 0.95); rough = 0.12; spec = 0.9; }
    else if (id < 4.5){ alb = vec3(0.95, 0.55, 0.20); rough = 0.35; }
    else { int bi = int(id - 10.0); alb = ballColor(bi); int k = bi % 7;
           rough = (k == 2 || k == 5) ? 0.3 : 0.15; spec = (k == 6) ? 0.9 : 0.06; }
    float sh = softShadow(p + n*0.01, LDIR);
    float occ = ao(p, n);
    float dif = max(dot(n, LDIR), 0.0);
    vec3 hv = normalize(LDIR - rd);
    float sp = pow(max(dot(n, hv), 0.0), 2.0 / (rough*rough*rough + 1e-3)) * (1.0/(rough+0.05));
    vec3 diffCol = (spec > 0.5) ? alb * 0.15 : alb;
    vec3 col = diffCol * (1.8*dif*(0.15+0.85*sh)*vec3(1.0,0.97,0.92) + 0.75*occ*sky(n));
    col += sp * sh * mix(vec3(spec), alb, spec > 0.5 ? 1.0 : 0.0) * 0.6;
    return col;
}

vec3 render(vec3 ro, vec3 rd){
    vec2 h = march(ro, rd, 60.0);
    if (h.x < 0.0) return sky(rd);
    vec3 p = ro + rd*h.x, n = normalAt(p);
    float spec; vec3 col = shade(p, n, rd, h.y, spec);
    float fres = spec + (1.0 - spec) * pow(1.0 - max(dot(n, -rd), 0.0), 5.0);
    bool isBall = h.y > 9.5;
    int k = isBall ? int(h.y - 10.0) % 7 : -1;
    if (isBall && (k == 0 || k == 3)){
        // glass marble: analytic refraction through the sphere, then one secondary march
        vec3 c = uBall[int(h.y - 10.0)];
        vec3 r1 = refract(rd, n, 1.0/1.5);
        float tb = dot(c - p, r1) * 2.0;                    // chord length inside the sphere
        vec3 p2 = p + r1*tb, n2 = normalize(p2 - c);
        vec3 r2 = refract(r1, -n2, 1.5); if (dot(r2,r2) < 0.5) r2 = reflect(r1, -n2);
        vec2 h2 = march(p2 + r2*0.02, r2, 30.0);
        vec3 behind = sky(r2);
        if (h2.x > 0.0){ vec3 q = p2 + r2*(0.02 + h2.x); float s2; behind = shade(q, normalAt(q), r2, h2.y, s2); }
        col = behind * ballColor(int(h.y - 10.0)) * 0.95;
        fres = 0.04 + 0.96*pow(1.0 - max(dot(n, -rd), 0.0), 5.0);
    }
    if (fres > 0.03){
        vec3 rr = reflect(rd, n);
        vec2 h3 = march(p + n*0.01, rr, 30.0);
        vec3 refl = sky(rr);
        if (h3.x > 0.0){ vec3 q = p + n*0.01 + rr*h3.x; float s3; refl = shade(q, normalAt(q), rr, h3.y, s3); }
        vec3 tint = (isBall && k == 6) ? ballColor(6) : vec3(1.0);
        col = mix(col, refl * tint, clamp(fres, 0.0, 1.0));
    }
    return col;
}

void main(){
    vec3 acc = vec3(0.0);
    for (int sy = 0; sy < uSS; sy++) for (int sx = 0; sx < uSS; sx++){
        vec2 off = (vec2(sx, sy) + 0.5) / float(uSS) - 0.5;
        vec2 uv = (gl_FragCoord.xy + off - 0.5*uRes) / (0.5*uRes.y);
        vec3 rd = normalize(vec3(uv.x*TANH, 1.0, uv.y*TANH));
        acc += render(CAM, rd);
    }
    vec3 col = acc / float(uSS*uSS);
    col = col / (1.0 + col);                     // simple tone map
    col = pow(col, vec3(1.0/2.2));
    frag = vec4(col, 1.0);
}
""".replace('NB', str(NB))


def ctx_create():
    for kw in ({}, {'backend': 'egl'}):
        try:
            return moderngl.create_standalone_context(require=330, **kw)
        except Exception as e:
            print('ctx fail', kw, e)
    raise SystemExit('no GL (run under xvfb-run)')


ctx = ctx_create()
print('GL_RENDERER', ctx.info['GL_RENDERER'])
prog = ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
vbo = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], 'f4').tobytes())
vao = ctx.vertex_array(prog, [(vbo, '2f', 'in_pos')])
fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
fbo.use()
prog['uRes'].value = (W, H)
prog['uSS'].value = a.ss
pos = np.array(traj['pos'], 'f4')          # (balls, frames, 3)

if a.clip:
    start, count = (int(v) for v in a.clip.split(','))
    out = HERE / f'clip_glsl_ss{a.ss}.mp4'
    ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
                           '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(traj['fps']), '-i', '-',
                           '-i', a.audio, '-vf', 'vflip,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
                           '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-c:a', 'aac', '-b:a', '192k',
                           '-shortest', str(out)], stdin=subprocess.PIPE)
    t0 = time.perf_counter()
    for f in range(start, start + count):
        prog['uBall'].write(pos[:, f - 1, :].tobytes())
        vao.render(moderngl.TRIANGLE_STRIP)
        ff.stdin.write(fbo.read(components=3, alignment=1))
    ff.stdin.close(); ff.wait()
    el = time.perf_counter() - t0
    print(f'CLIP {count} frames end-to-end (render + x264 slow + AAC) {el:.1f} s = {el / count:.3f} s/frame -> {out.name}')
    raise SystemExit
tag = a.tag or f'glsl_ss{a.ss}'
times = []
for f in (int(v) for v in a.frames.split(',')):
    prog['uBall'].write(pos[:, f - 1, :].tobytes())   # Blender frame f == index f-1
    t0 = time.perf_counter()
    vao.render(moderngl.TRIANGLE_STRIP)
    data = fbo.read(components=3, alignment=1)        # forces completion
    times.append(time.perf_counter() - t0)
    print(f'BENCH {tag} frame {f}: {times[-1]:.3f} s', flush=True)
    if a.png and f == int(a.frames.split(',')[0]):
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
                        '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-i', '-', '-vf', 'vflip',
                        '-frames:v', '1', str(HERE / 'renders' / f'{tag}-f{f:04d}.png')],
                       input=data, check=True)
res = dict(tag=tag, engine='GLSL', res=a.res, samples=a.ss * a.ss, times=times,
           first=times[0], steady=sum(times[1:]) / max(1, len(times) - 1))
print('RESULT', json.dumps(res))
with open(HERE / 'bench_results.jsonl', 'a') as fh:
    fh.write(json.dumps(res) + '\n')
