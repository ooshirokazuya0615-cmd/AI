#version 330
// 3 passes in one file: SCENE (raymarch -> HDR), BRIGHT (threshold), POST (bloom, confetti, tonemap)
//#define PASS
in vec2 v_uv;
out vec4 f_color;
uniform vec2 u_res;
uniform float u_time;

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

#ifdef SCENE_PASS
uniform vec3 u_camPos;
uniform mat3 u_camRot;
uniform float u_tanH;

uniform vec3 u_cPos;
uniform mat3 u_cRot;     // local -> world
uniform vec3 u_cRad;
uniform float u_cR;
uniform vec4 u_face;     // squint, blink, mouth, happy
uniform vec2 u_look;
uniform vec3 u_bodyCol;
uniform vec3 u_bounce;   // colour of the pillar below (note flash)

uniform int u_nBlk;
uniform vec4 u_blk[20];     // x0, x1, top, halfDepth
uniform vec4 u_blkFx[20];   // flash, lit, prelight, age since hit (<0 none)
uniform vec3 u_blkCol[20];
uniform float u_landX[20];

uniform vec3 u_drum;        // kick, snare, hat envelopes
uniform float u_final;      // seconds since final hit (<0 before)

const float PI = 3.14159265;
const vec3 KEY = normalize(vec3(-0.45, 0.85, 0.55));

float sdRoundBox(vec3 p, vec3 b, float r) {
    vec3 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}
float sdEllipsoid(vec3 p, vec3 r) {
    float k0 = length(p / r);
    float k1 = length(p / (r * r));
    return k0 * (k0 - 1.0) / k1;
}

int findBlock(float x) {
    int idx = -1;
    for (int i = 0; i < 20; i++) {
        if (i >= u_nBlk) break;
        if (u_blk[i].x - 0.05 <= x) idx = i;
    }
    return idx;
}

// eye ellipsoid in body-local space; returns distance
vec3 eyeCenter(float side) { return vec3(side * 0.37, 0.24, 0.86) * u_cRad; }
float eyeSDF(vec3 q, float side, out vec3 eq) {
    vec3 c = eyeCenter(side);
    eq = q - c;
    float open = (1.0 - 0.9 * u_face.y) * (1.0 - 0.55 * u_face.x) * (1.0 - 0.72 * u_face.w);
    vec3 r = u_cR * vec3(0.19, 0.25 * max(open, 0.08), 0.13);
    vec3 p = eq;
    p.y += u_face.w * 2.2 * p.x * p.x / u_cR;     // happy ^ ^ arc
    return sdEllipsoid(p, r);
}

vec3 mapChar(vec3 p) { // (dist, mat, side)
    vec3 q = transpose(u_cRot) * (p - u_cPos);
    float d = sdEllipsoid(q, u_cRad);
    vec3 res = vec3(d, 3.0, 0.0);
    vec3 eq;
    for (int s = 0; s < 2; s++) {
        float side = s == 0 ? -1.0 : 1.0;
        float de = eyeSDF(q, side, eq);
        if (de < res.x) res = vec3(de, 4.0, side);
    }
    return res;
}

vec3 map(vec3 p) { // (dist, material, block index / eye side)
    vec3 res = vec3(p.y, 1.0, -1.0);
    int bi = findBlock(p.x);
    for (int j = -1; j <= 1; j++) {
        int k = bi + j;
        if (k < 0 || k >= u_nBlk) continue;
        vec4 b = u_blk[k];
        vec3 c = vec3(0.5 * (b.x + b.y), 0.5 * (b.z - 0.5), 0.0);
        vec3 h = vec3(0.5 * (b.y - b.x), 0.5 * (b.z + 0.5), b.w);
        float d = sdRoundBox(p - c, h, 0.04);
        if (d < res.x) res = vec3(d, 2.0, float(k));
    }
    float bound = length(p - u_cPos) - 1.25 * max(u_cRad.x, u_cRad.y);
    if (bound < res.x) {
        vec3 c = mapChar(p);
        if (c.x < res.x) res = c;
    }
    return res;
}

vec3 calcNormal(vec3 p) {
    const vec2 k = vec2(1, -1) * 0.0007;
    return normalize(k.xyy * map(p + k.xyy).x + k.yyx * map(p + k.yyx).x +
                     k.yxy * map(p + k.yxy).x + k.xxx * map(p + k.xxx).x);
}

float softShadow(vec3 ro, vec3 rd) {
    float res = 1.0, t = 0.02;
    for (int i = 0; i < 28; i++) {
        float h = map(ro + rd * t).x;
        res = min(res, 9.0 * h / t);
        t += clamp(h, 0.02, 0.35);
        if (res < 0.003 || t > 9.0) break;
    }
    return clamp(res, 0.0, 1.0);
}

float ao(vec3 p, vec3 n) {
    float occ = 0.0, sca = 1.0;
    for (int i = 1; i <= 4; i++) {
        float h = 0.03 + 0.09 * float(i);
        occ += (h - map(p + n * h).x) * sca;
        sca *= 0.7;
    }
    return clamp(1.0 - 2.2 * occ, 0.0, 1.0);
}

vec3 sky(vec3 rd) {
    float y = rd.y;
    vec3 col = mix(vec3(0.035, 0.016, 0.07), vec3(0.004, 0.006, 0.022), smoothstep(-0.05, 0.55, y));
    col += vec3(0.22, 0.06, 0.30) * exp(-abs(y - 0.01) * 12.0) * 0.35;               // horizon haze
    vec3 sd = normalize(vec3(0.55, 0.30, -1.0));
    float sdd = max(dot(rd, sd), 0.0);
    col += vec3(1.0, 0.40, 0.55) * (pow(sdd, 1400.0) * 2.2 + pow(sdd, 60.0) * 0.06) * (1.0 + 1.0 * u_drum.x);
    col += vec3(0.30, 0.12, 0.55) * 0.12 * u_drum.y * (1.0 - smoothstep(0.0, 0.6, y));  // snare flash
    // distant equalizer skyline: thin bars, atmospheric, heights jump with kick / snare
    float az = atan(rd.z, rd.x) * 70.0 / PI;
    float bi = floor(az);
    float hb = hash12(vec2(bi, 3.0));
    float bh = 0.006 + 0.05 * hb * hb * (0.5 + 1.0 * u_drum.x + 0.6 * u_drum.y * step(0.5, hash12(vec2(bi, 9.0))));
    float inBar = step(abs(fract(az) - 0.5), 0.30);
    if (rd.y > -0.02 && rd.y < bh && inBar > 0.5) {
        col = mix(col, vec3(0.05, 0.02, 0.09), 0.75) + vec3(1.0, 0.3, 0.8) * exp(-(bh - rd.y) * 700.0) * (0.3 + 1.2 * u_drum.x);
    }
    vec2 sp = vec2(atan(rd.z, rd.x), asin(clamp(rd.y, -1.0, 1.0))) * 70.0;
    vec2 cell = floor(sp);
    float st = hash12(cell);
    vec2 off = vec2(hash12(cell + 7.3), hash12(cell + 1.9)) * 0.6 + 0.2;
    float dd = length(fract(sp) - off);
    if (st > 0.93 && y > 0.04) col += vec3(0.7, 0.8, 1.0) * (0.35 + 0.8 * u_drum.z) * exp(-dd * dd * 90.0) * (st - 0.93) * 12.0;
    return col;
}

vec3 bodyShade(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 q = transpose(u_cRot) * (p - u_cPos);
    vec3 nl = q / u_cRad;                    // ~unit sphere coords
    vec3 base = u_bodyCol;
    // belly lighter, cheeks blush
    base = mix(base, vec3(1.0, 0.93, 0.72), smoothstep(0.1, -0.7, nl.y) * smoothstep(0.0, 0.8, nl.z) * 0.6);
    for (int s = 0; s < 2; s++) {
        float side = s == 0 ? -1.0 : 1.0;
        float dc = length(nl.xy - vec2(side * 0.55, -0.05));
        base = mix(base, vec3(1.0, 0.42, 0.45), (1.0 - smoothstep(0.08, 0.2, dc)) * step(0.0, nl.z) * 0.55);
    }
    // mouth: thin smile line when closed, D-shaped grin when open
    vec2 m = nl.xy - vec2(0.0, -0.13);
    float mw = 0.17;
    float isOpen = step(0.05, u_face.z);
    float lineM = (1.0 - smoothstep(0.012, 0.024, abs(m.y - 1.8 * m.x * m.x))) * (1.0 - smoothstep(mw - 0.03, mw, abs(m.x)));
    float oh = 0.20 * u_face.z;
    float dOpen = length(vec2(m.x / mw, m.y / max(oh, 1e-3)));
    float openM = (1.0 - smoothstep(0.90, 1.0, dOpen)) * (1.0 - smoothstep(0.0, 0.012, m.y));
    float mouth = mix(lineM, openM, isOpen) * step(0.3, nl.z);
    vec3 mcol = mix(vec3(0.30, 0.04, 0.08), vec3(1.0, 0.42, 0.50), smoothstep(-0.45 * oh, -0.95 * oh, m.y) * isOpen);
    base = mix(base, mcol, mouth);

    float dif = clamp(dot(n, KEY) * 0.8 + 0.2, 0.0, 1.0) * sh;   // wrapped diffuse (soft body)
    float sss = pow(clamp(dot(rd, KEY) * 0.5 + 0.5, 0.0, 1.0), 3.0) * 0.4;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 60.0) * sh;
    float fre = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    vec3 col = base * (vec3(1.15, 1.0, 0.88) * dif * 0.95 + vec3(0.22, 0.22, 0.45) * occ * 0.45);
    col += base * vec3(1.0, 0.4, 0.2) * sss;
    col += mix(base, vec3(1.0), 0.3) * u_bounce * clamp(-n.y * 0.8 + 0.3, 0.0, 1.0) * 0.55;
    col += vec3(1.0) * spe * 0.8 * (1.0 - mouth);
    col += vec3(0.55, 0.40, 1.0) * fre * 0.55 * occ;              // purple rim from the sky
    return col;
}

vec3 eyeShade(vec3 p, vec3 n, float side, vec3 rd, float sh) {
    vec3 q = transpose(u_cRot) * (p - u_cPos);
    vec3 eq = q - eyeCenter(side);
    vec2 e = eq.xy / (u_cR * vec2(0.19, 0.25));
    float closedish = max(u_face.w, step(0.6, u_face.y));
    vec2 pc = e - u_look * vec2(0.42, 0.38);
    float pupil = 1.0 - smoothstep(0.50, 0.56, length(pc * vec2(1.0, 0.85)));
    vec3 col = mix(vec3(0.97), vec3(0.03, 0.03, 0.06), pupil);
    float hl = 1.0 - smoothstep(0.10, 0.16, length(pc - vec2(0.22, 0.25)));
    col = mix(col, vec3(1.6), hl * pupil);
    col = mix(col, vec3(0.08, 0.04, 0.06), closedish);
    float dif = clamp(dot(n, KEY) * 0.6 + 0.4, 0.0, 1.0) * (0.5 + 0.5 * sh);
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 120.0);
    return col * (0.35 + 0.9 * dif) + spe * 1.2;
}

vec3 blockShade(vec3 p, vec3 n, int k, vec3 rd, float sh, float occ) {
    vec4 b = u_blk[k];
    vec4 fx = u_blkFx[k];
    vec3 c = u_blkCol[k];
    vec3 lp = p - vec3(0.5 * (b.x + b.y), b.z, 0.0);
    float dx = 0.5 * (b.y - b.x) - abs(lp.x), dz = b.w - abs(lp.z), dy = -lp.y;
    vec3 an = abs(n);
    float top = step(0.7, an.y) * step(0.0, n.y);
    float edge = top > 0.5 ? min(dx, dz) : (an.x > an.z ? min(dz, dy) : min(dx, dy));
    float rim = exp(-max(edge, 0.0) * 34.0);
    float e = 0.22 + 0.55 * fx.y + 0.7 * fx.z + 2.6 * fx.x;   // emissive energy
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 60.0) * sh;
    vec3 body = vec3(0.016, 0.018, 0.034) + c * 0.012;
    vec3 col = body * (0.5 + 1.6 * dif) * occ + vec3(0.7, 0.75, 1.0) * spe * 0.12;
    col += vec3(0.30, 0.25, 0.6) * pow(1.0 - max(dot(n, -rd), 0.0), 4.0) * 0.08;   // glassy fresnel
    col += c * rim * 0.42 * e;
    col += c * top * (0.05 + 0.10 * e);
    col += mix(c, vec3(1.0), 0.15) * top * fx.x * fx.x * 0.8;   // hit: top face flares
    col += c * (1.0 - top) * 0.05 * e * smoothstep(-0.5, b.z, p.y) * smoothstep(0.0, 0.04, edge);
    if (fx.w >= 0.0 && top > 0.5) {
        float d = length(p.xz - vec2(u_landX[k], 0.0));
        float w = abs(d - fx.w * 2.2);
        col += mix(c, vec3(1.0), 0.4) * exp(-w * 45.0) * exp(-fx.w * 5.5) * 2.2;
    }
    return col;
}

vec3 groundShade(vec3 p, vec3 rd, float sh, float occ, float t) {
    vec3 col = vec3(0.010, 0.011, 0.022);
    float dif = max(KEY.y, 0.0) * sh;
    col *= 0.35 + 1.2 * dif * occ;
    // grid, pulsing with the kick
    vec2 g = abs(fract(p.xz * 2.0) - 0.5);
    float w = 0.012 + 0.002 * t;
    float line = 1.0 - smoothstep(0.5 - w, 0.5, max(g.x, g.y));
    float fade = exp(-t * 0.08);
    col += vec3(0.20, 0.30, 0.9) * line * (0.05 + 0.40 * u_drum.x) * fade * occ;
    // glow spill from nearby pillars
    int bi = findBlock(p.x);
    for (int j = -1; j <= 1; j++) {
        int k = bi + j;
        if (k < 0 || k >= u_nBlk) continue;
        vec4 b = u_blk[k];
        float dx = max(max(b.x - p.x, p.x - b.y), 0.0);
        float dz = max(abs(p.z) - b.w, 0.0);
        float d = length(vec2(dx, dz));
        float e = 0.15 + 0.5 * u_blkFx[k].y + 2.0 * u_blkFx[k].x;
        col += u_blkCol[k] * exp(-d * 5.0) * 0.07 * e;
    }
    return col;
}

void main() {
    vec2 uv = (2.0 * gl_FragCoord.xy - u_res) / u_res.y;
    vec3 rd = normalize(u_camRot * vec3(uv * u_tanH, 1.0));
    vec3 ro = u_camPos;
    float t = 0.0;
    vec3 res = vec3(1e9, 0.0, -1.0);
    for (int i = 0; i < 120; i++) {
        vec3 h = map(ro + rd * t);
        if (h.x < 0.0006 * t + 0.0004) { res = vec3(t, h.y, h.z); break; }
        t += h.x * 0.95;
        if (t > 45.0) break;
    }
    vec3 col;
    vec3 skyc = sky(rd);
    if (res.y < 0.5) {
        col = skyc;
    } else {
        vec3 p = ro + rd * res.x;
        vec3 n = calcNormal(p);
        float sh = softShadow(p + n * 0.003, KEY);
        float occ = ao(p, n);
        if (res.y < 1.5) col = groundShade(p, rd, sh, occ, res.x);
        else if (res.y < 2.5) col = blockShade(p, n, int(res.z + 0.5), rd, sh, occ);
        else if (res.y < 3.5) col = bodyShade(p, n, rd, sh, occ);
        else col = eyeShade(p, n, res.z, rd, sh);
        // fog toward the horizon haze
        col = mix(col, vec3(0.03, 0.014, 0.06), 1.0 - exp(-0.0020 * res.x * res.x));
    }
    // final-hit flash
    
    f_color = vec4(col, 1.0);
}
#endif

#ifdef BRIGHT_PASS
uniform sampler2D u_hdr;
void main() {
    vec3 c = texture(u_hdr, v_uv).rgb;
    float l = max(c.r, max(c.g, c.b));
    f_color = vec4(c * smoothstep(0.9, 2.2, l), 1.0);
}
#endif

#ifdef POST_PASS
uniform sampler2D u_hdr;
uniform sampler2D u_bright;
uniform int u_nConf;
uniform vec4 u_conf[48];     // screen x,y (pixels), angle, size (pixels)
uniform vec4 u_confCol[48];  // rgb, alpha
uniform float u_aspect;
uniform float u_impact;   // 1 on the impact frame

vec3 aces(vec3 x) {
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}
void main() {
    vec3 col = texture(u_hdr, v_uv).rgb;
    vec3 bloom = vec3(0.0);
    float wsum = 0.0;
    for (int l = 1; l <= 6; l++) {
        float w = 1.0 / float(l);
        vec2 px = exp2(float(l)) / u_res;
        vec3 s = textureLod(u_bright, v_uv, float(l)).rgb * 0.4
               + textureLod(u_bright, v_uv + vec2(px.x, 0), float(l)).rgb * 0.15
               + textureLod(u_bright, v_uv - vec2(px.x, 0), float(l)).rgb * 0.15
               + textureLod(u_bright, v_uv + vec2(0, px.y), float(l)).rgb * 0.15
               + textureLod(u_bright, v_uv - vec2(0, px.y), float(l)).rgb * 0.15;
        bloom += s * w;
        wsum += w;
    }
    col += bloom / wsum * 0.75;
    // confetti (2D, projected in python)
    vec2 fc = gl_FragCoord.xy;
    for (int i = 0; i < 48; i++) {
        if (i >= u_nConf) break;
        vec4 c = u_conf[i];
        vec2 d = fc - c.xy;
        float ca = cos(c.z), sa = sin(c.z);
        d = mat2(ca, -sa, sa, ca) * d;
        float flip = abs(cos(c.z * 1.7));
        vec2 hs = c.w * vec2(1.0, 0.45 * flip + 0.08);
        vec2 q = abs(d) - hs;
        float a = 1.0 - smoothstep(-0.5, 0.8, max(q.x, q.y));
        col = mix(col, u_confCol[i].rgb * (0.7 + 0.6 * flip), a * u_confCol[i].a);
    }
    vec2 vp = v_uv - 0.5;
    col *= 1.0 - 0.55 * dot(vp, vp);
    col = aces(col * 1.05);
    col = pow(col, vec3(1.0 / 2.2));
    float lum = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(col, vec3(1.0 - smoothstep(0.08, 0.55, lum)) * vec3(1.0, 0.92, 0.98), u_impact);
    col += (hash12(gl_FragCoord.xy + fract(u_time * 7.13) * 100.0) - 0.5) / 255.0;
    f_color = vec4(col, 1.0);
}
#endif
