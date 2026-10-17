#version 330
// 3 passes in one file: SCENE (raymarch -> HDR), BRIGHT (threshold), POST (bloom, tonemap)
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
uniform vec3 u_stA[11];
uniform vec3 u_stB[11];
uniform vec3 u_head;
uniform vec3 u_glove;           // glove centre
uniform vec3 u_gloveDir;        // forearm direction at the glove
uniform vec3 u_ballPos;
uniform float u_spin;
uniform vec4 u_trail[8];        // xyz, intensity
uniform float u_gongAge;        // seconds since the gong was hit (<0 before)
uniform vec4 u_plate[11];       // xyz, age since hit
uniform vec3 u_plateCol[11];
uniform vec4 u_bar[16];         // z, top y, half length, age since hit
uniform vec3 u_barCol[16];
uniform float u_seeA;           // seesaw angle
uniform vec3 u_weight;
uniform float u_hook;           // 1 while the weight still hangs
uniform vec3 u_fx;              // gong flash, slam flash, kick pulse

const float PI = 3.14159265;
const float BALL_R = 0.045;
const vec3 GONG_C = vec3(0.0, 1.25, 4.60);
const float GONG_R = 0.36, GONG_T = 0.03;
const float PLATE_R = 0.085, PLATE_T = 0.014;
const float TRACK_X = -0.75;
const vec3 SEE_P = vec3(-0.75, 0.14, 0.72);
const float SEE_HALF = 0.28;
const float WEIGHT_R = 0.085;
const vec3 KEY = normalize(vec3(-0.45, 0.85, -0.25));
const vec3 KEYCOL = vec3(1.15, 1.10, 1.02);

float sdRoundBox(vec3 p, vec3 b, float r) {
    vec3 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}
float sdEllipsoid(vec3 p, vec3 r) {
    float k0 = length(p / r);
    float k1 = length(p / (r * r));
    return k0 * (k0 - 1.0) / k1;
}
float smin(float a, float b, float k) {
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}
float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
    vec3 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h) - r;
}
// disc with axis along a unit vector
float sdDisc(vec3 p, vec3 c, vec3 axis, float r, float halfT) {
    vec3 q = p - c;
    float h = dot(q, axis);
    float rr = length(q - axis * h);
    vec2 d = vec2(rr - r, abs(h) - halfT);
    return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - 0.004;
}
mat3 rotX(float a) { float c = cos(a), s = sin(a); return mat3(1, 0, 0, 0, c, s, 0, -s, c); }

float trackTop(float z) {
    float u = (3.85 - z) / (3.85 - 1.15);
    return 0.28 + (0.10 - 0.28) * u;
}

vec3 map(vec3 p) {  // (dist, material, id)
    vec3 res = vec3(p.y, 1.0, 0.0);
    // pitcher + glove
    float sb = length(p - u_stA[0]) - 1.1;
    if (sb < res.x) {
        float d = length(p - u_head) - 0.085;
        for (int i = 0; i < 11; i++) {
            float r = i == 0 ? 0.034 : (i >= 9 ? 0.026 : 0.028);
            d = smin(d, sdCapsule(p, u_stA[i], u_stB[i], r), 0.018);
        }
        if (d < res.x) res = vec3(d, 6.0, 0.0);
        float dg = sdEllipsoid(p - u_glove, vec3(0.06, 0.065, 0.05));
        if (dg < res.x) res = vec3(dg, 7.0, 0.0);
    }
    // ball
    float db = length(p - u_ballPos) - BALL_R;
    if (db < res.x) res = vec3(db, 2.0, 0.0);
    // gong + frame
    float gb = length(p - GONG_C) - 0.9;
    if (gb < res.x + 0.6) {
        float wob = u_gongAge > 0.0 ? 0.04 * exp(-u_gongAge * 2.5) * sin(u_gongAge * 9.0) : 0.0;
        vec3 ax = normalize(vec3(0.0, wob, 1.0));
        float d = sdDisc(p, GONG_C, ax, GONG_R, GONG_T * 0.5);
        d = min(d, length(vec2(length((p - GONG_C).xy) - GONG_R * 0.55, dot(p - GONG_C, ax) + 0.012)) - 0.012);  // raised ring
        if (d < res.x) res = vec3(d, 3.0, 0.0);
        float f = sdCapsule(p, vec3(-0.52, 0.0, 4.62), vec3(-0.52, 1.80, 4.62), 0.03);
        f = min(f, sdCapsule(p, vec3(0.52, 0.0, 4.62), vec3(0.52, 1.80, 4.62), 0.03));
        f = min(f, sdCapsule(p, vec3(-0.60, 1.80, 4.62), vec3(0.60, 1.80, 4.62), 0.035));
        f = min(f, sdCapsule(p, vec3(-0.22, 1.80, 4.62), vec3(-0.18, 1.55, 4.61), 0.006));
        f = min(f, sdCapsule(p, vec3(0.22, 1.80, 4.62), vec3(0.18, 1.55, 4.61), 0.006));
        if (f < res.x) res = vec3(f, 8.0, 0.0);
    }
    // plates on thin posts
    if (abs(p.x) < 0.5 && p.z > 3.8 && p.z < 4.45 && p.y < 1.2) {
        for (int i = 0; i < 11; i++) {
            vec3 c = u_plate[i].xyz;
            float d = sdDisc(p, c, vec3(0.0, 1.0, 0.0), PLATE_R, PLATE_T * 0.5);
            if (d < res.x) res = vec3(d, 4.0, float(i));
            float ps = sdCapsule(p, vec3(c.x, 0.0, c.z), c - vec3(0.0, 0.01, 0.0), 0.006);
            if (ps < res.x) res = vec3(ps, 8.0, 0.0);
        }
    }
    // xylophone track
    if (abs(p.x - TRACK_X) < 0.25 && p.z > 0.9 && p.z < 4.05 && p.y < 0.5) {
        float zb = clamp(p.z, 1.0, 3.95);
        int ic = int(floor((3.85 - p.z) / 0.18 + 0.5));
        for (int j = -1; j <= 1; j++) {
            int i = ic + j;
            if (i < 0 || i >= 16) continue;
            vec4 b = u_bar[i];
            vec3 c = vec3(TRACK_X, b.y - 0.012, b.x);
            float d = sdRoundBox(p - c, vec3(b.z, 0.012, 0.07), 0.006);
            if (d < res.x) res = vec3(d, 5.0, float(i));
        }
        // rails and legs
        float rl = sdCapsule(p, vec3(TRACK_X - 0.075, 0.30 + BALL_R * 0.6, 3.95), vec3(TRACK_X - 0.075, 0.12 + BALL_R * 0.6, 1.05), 0.008);
        rl = min(rl, sdCapsule(p, vec3(TRACK_X + 0.075, 0.30 + BALL_R * 0.6, 3.95), vec3(TRACK_X + 0.075, 0.12 + BALL_R * 0.6, 1.05), 0.008));
        float lz = (floor(p.z / 0.9) + 0.5) * 0.9;
        rl = min(rl, sdCapsule(p, vec3(TRACK_X, 0.0, lz), vec3(TRACK_X, trackTop(lz) - 0.03, lz), 0.012));
        if (rl < res.x) res = vec3(rl, 8.0, 0.0);
    }
    // seesaw catapult, weight and its post
    if (abs(p.x - TRACK_X) < 0.4 && p.z > 0.1 && p.z < 1.4) {
        vec3 q = rotX(-u_seeA) * (p - SEE_P);
        float pl = sdRoundBox(q, vec3(0.06, 0.012, SEE_HALF + 0.02), 0.006);
        float cup = length(vec2(length(q.xz - vec2(0.0, SEE_HALF - 0.03)) - 0.045, q.y - 0.02)) - 0.008;
        pl = min(pl, cup);
        if (pl < res.x) res = vec3(pl, 9.0, 0.0);
        float pv = sdRoundBox(p - vec3(TRACK_X, 0.065, SEE_P.z), vec3(0.04, 0.065, 0.03), 0.01);
        float post = sdCapsule(p, vec3(TRACK_X - 0.16, 0.0, 0.43), vec3(TRACK_X - 0.16, 1.92, 0.43), 0.015);
        post = min(post, sdCapsule(p, vec3(TRACK_X - 0.16, 1.92, 0.43), vec3(TRACK_X, 1.92, 0.43), 0.012));
        if (u_hook > 0.5) post = min(post, sdCapsule(p, vec3(TRACK_X, 1.92, 0.43), u_weight + vec3(0.0, WEIGHT_R, 0.0), 0.003));
        pv = min(pv, post);
        if (pv < res.x) res = vec3(pv, 8.0, 0.0);
        float w = length(p - u_weight) - WEIGHT_R;
        w = min(w, length(vec2(length((p - u_weight - vec3(0.0, WEIGHT_R + 0.02, 0.0)).xy) - 0.035, p.z - u_weight.z)) - 0.01);
        if (w < res.x) res = vec3(w, 10.0, 0.0);
    }
    return res;
}

vec3 calcNormal(vec3 p) {
    const vec2 k = vec2(1, -1) * 0.0005;
    return normalize(k.xyy * map(p + k.xyy).x + k.yyx * map(p + k.yyx).x +
                     k.yxy * map(p + k.yxy).x + k.xxx * map(p + k.xxx).x);
}

float softShadow(vec3 ro, vec3 rd) {
    float res = 1.0, t = 0.01;
    for (int i = 0; i < 26; i++) {
        float h = map(ro + rd * t).x;
        res = min(res, 10.0 * h / t);
        t += clamp(h, 0.01, 0.25);
        if (res < 0.003 || t > 4.0) break;
    }
    return clamp(res, 0.0, 1.0);
}

float ao(vec3 p, vec3 n) {
    float occ = 0.0, sca = 1.0;
    for (int i = 1; i <= 4; i++) {
        float h = 0.01 + 0.04 * float(i);
        occ += (h - map(p + n * h).x) * sca;
        sca *= 0.7;
    }
    return clamp(1.0 - 3.0 * occ, 0.0, 1.0);
}

vec3 background(vec3 rd) {
    vec3 col = mix(vec3(0.030, 0.045, 0.085), vec3(0.006, 0.010, 0.030), smoothstep(-0.05, 0.6, rd.y));
    col += vec3(0.10, 0.16, 0.22) * exp(-abs(rd.y - 0.02) * 14.0) * 0.4;       // haze over the stands
    // stadium light banks: clusters of bright dots high up in four directions
    float az = atan(rd.x, rd.z);
    for (int k = 0; k < 4; k++) {
        float a0 = -2.4 + float(k) * 1.6;
        vec2 d = vec2((az - a0) * 1.0, rd.y - 0.36);
        vec2 g = abs(fract(d * vec2(55.0, 55.0)) - 0.5);
        float inBank = step(abs(d.x), 0.10) * step(abs(d.y), 0.035);
        col += vec3(1.0, 0.95, 0.85) * inBank * (1.0 - smoothstep(0.18, 0.32, length(g))) * 2.2;
        col += vec3(0.6, 0.65, 0.75) * exp(-dot(d, d) * 90.0) * 0.30;
    }
    // faint stands silhouette band
    col = mix(col, vec3(0.012, 0.016, 0.03), step(rd.y, 0.10) * step(0.0, rd.y) * 0.7);
    return col;
}

vec3 lightSpill(vec3 p) {
    vec3 acc = vec3(0.0);
    for (int i = 0; i < 11; i++) {
        float age = u_plate[i].w;
        if (age < 0.0) continue;
        float d = length(p - u_plate[i].xyz);
        acc += u_plateCol[i] * (0.15 + 2.5 * exp(-age / 0.2)) * exp(-d * 7.0) * 0.12;
    }
    if (p.z > 0.8 && p.z < 4.1) {
        for (int i = 0; i < 16; i++) {
            float age = u_bar[i].w;
            if (age < 0.0) continue;
            float d = length(p - vec3(TRACK_X, u_bar[i].y, u_bar[i].x));
            acc += u_barCol[i] * (0.15 + 2.5 * exp(-age / 0.18)) * exp(-d * 9.0) * 0.12;
        }
    }
    float ga = u_gongAge;
    if (ga >= 0.0) acc += vec3(1.0, 0.75, 0.35) * exp(-ga / 0.6) * exp(-length(p - GONG_C) * 2.5) * 0.6;
    if (isnan(acc.x + acc.y + acc.z) || isinf(acc.x + acc.y + acc.z)) acc = vec3(0.0);
    return acc;
}

vec3 shadeFloor(vec3 p, vec3 n, float sh, float occ, out float refl) {
    // grass with mowing stripes, dirt mound around the pitcher
    float stripe = step(0.5, fract(p.z * 0.45 + 0.25));
    vec3 grass = mix(vec3(0.045, 0.11, 0.05), vec3(0.06, 0.15, 0.065), stripe);
    float blade = hash12(floor(p.xz * 180.0));
    grass *= 0.85 + 0.3 * blade;
    float r = length(p.xz - vec2(0.2, 0.3));
    vec3 dirt = vec3(0.30, 0.19, 0.11) * (0.85 + 0.3 * hash12(floor(p.xz * 90.0)));
    vec3 col = mix(dirt, grass, smoothstep(1.05, 1.12, r));
    col = mix(col, vec3(0.85), (1.0 - smoothstep(0.0, 0.01, abs(p.z - 0.32) - 0.025)) * step(abs(p.x), 0.15) * 0.9);   // rubber
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 c = col * (KEYCOL * dif * 0.95 + vec3(0.18, 0.22, 0.32) * occ * 0.55);
    c += lightSpill(p) * occ;
    refl = 0.0;
    return c;
}

vec3 shadeBall(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 q = (p - u_ballPos) / BALL_R;
    float c = cos(u_spin), s = sin(u_spin);
    q = vec3(q.x, c * q.y - s * q.z, s * q.y + c * q.z);
    // baseball stitches: a wavy seam
    float seam = abs(q.y - 0.55 * sin(atan(q.z, q.x) * 2.0) * sqrt(max(1.0 - q.y * q.y, 0.0)));
    vec3 base = vec3(0.97, 0.96, 0.92);
    float st = (1.0 - smoothstep(0.02, 0.06, seam)) * step(0.5, fract(atan(q.z, q.x) * 9.0));
    base = mix(base, vec3(0.85, 0.08, 0.08), st);
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 40.0) * sh;
    return base * (KEYCOL * dif + vec3(0.30, 0.32, 0.42) * occ * 0.6) + spe * 0.4 + base * 0.25;
}

vec3 shadeMetal(vec3 p, vec3 n, vec3 rd, float sh, float occ, vec3 tint, float glow) {
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 90.0) * sh;
    float dif = max(dot(n, KEY), 0.0) * sh;
    float fre = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    vec3 env = mix(vec3(0.05, 0.07, 0.12), vec3(0.35, 0.40, 0.55), clamp(reflect(rd, n).y * 0.5 + 0.5, 0.0, 1.0));
    vec3 col = tint * (dif * KEYCOL * 0.6 + env * 0.9) + spe * 1.4 * mix(vec3(1.0), tint, 0.4) + fre * env * 0.4;
    col += tint * glow;
    return col * mix(0.6, 1.0, occ);
}

vec3 shadeStick(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 base = vec3(0.95, 0.93, 0.88);
    float dif = clamp(dot(n, KEY) * 0.8 + 0.2, 0.0, 1.0) * sh;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 50.0) * sh;
    float fre = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    vec3 col = base * (KEYCOL * dif * 0.9 + vec3(0.25, 0.28, 0.42) * occ * 0.6);
    col += spe * 0.35 + vec3(0.45, 0.6, 1.0) * fre * 0.45 * occ;
    return col;
}

vec3 shadeWood(vec3 p, vec3 n, vec3 rd, float sh, float occ, vec3 base) {
    float g = sin(p.x * 140.0 + sin(p.z * 23.0) * 3.0) * 0.5 + 0.5;
    base *= 0.85 + 0.2 * g;
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 40.0) * sh;
    return base * (KEYCOL * dif * 0.95 + vec3(0.22, 0.25, 0.36) * occ * 0.6) + spe * 0.25;
}

vec3 shade(vec3 p, vec3 n, vec3 rd, vec3 res, float t) {
    float sh = softShadow(p + n * 0.002, KEY);
    float occ = ao(p, n);
    float refl;
    vec3 col;
    int m = int(res.y + 0.5);
    if (m == 1) col = shadeFloor(p, n, sh, occ, refl);
    else if (m == 2) col = shadeBall(p, n, rd, sh, occ);
    else if (m == 3) {
        float ga = u_gongAge;
        float glow = ga >= 0.0 ? 0.2 + 1.4 * exp(-ga / 0.30) : 0.10;
        float rings = 0.5 + 0.5 * sin(length((p - GONG_C).xy) * 60.0);
        col = shadeMetal(p, n, rd, sh, occ, vec3(0.95, 0.62, 0.22) * (0.85 + 0.15 * rings), glow * 0.5);
    } else if (m == 4) {
        int i = int(res.z + 0.5);
        float age = u_plate[i].w;
        float glow = age >= 0.0 ? 0.35 + 4.0 * exp(-age / 0.18) : 0.06;
        col = shadeMetal(p, n, rd, sh, occ, mix(vec3(0.85, 0.75, 0.55), u_plateCol[i], 0.6), glow * 0.6);
    } else if (m == 5) {
        int i = int(res.z + 0.5);
        float age = u_bar[i].w;
        float glow = age >= 0.0 ? 0.3 + 4.0 * exp(-age / 0.16) : 0.0;
        col = shadeWood(p, n, rd, sh, occ, vec3(0.55, 0.30, 0.15)) + u_barCol[i] * glow * 0.6;
    } else if (m == 6) col = shadeStick(p, n, rd, sh, occ);
    else if (m == 7) col = shadeWood(p, n, rd, sh, occ, vec3(0.28, 0.12, 0.05));      // glove
    else if (m == 8) col = shadeMetal(p, n, rd, sh, occ, vec3(0.25, 0.27, 0.30), 0.0); // frames
    else if (m == 9) col = shadeWood(p, n, rd, sh, occ, vec3(0.62, 0.45, 0.25));
    else col = shadeMetal(p, n, rd, sh, occ, vec3(0.12, 0.12, 0.13), u_fx.y * 0.8);   // iron weight
    col = mix(col, vec3(0.03, 0.045, 0.085), 1.0 - exp(-0.0016 * t * t));
    return col;
}

void main() {
    vec2 uv = (2.0 * gl_FragCoord.xy - u_res) / u_res.y;
    vec3 rd = normalize(u_camRot * vec3(uv * u_tanH, 1.0));
    vec3 ro = u_camPos;
    float t = 0.0;
    vec3 res = vec3(-1.0, 0.0, 0.0);
    for (int i = 0; i < 160; i++) {
        vec3 h = map(ro + rd * t);
        if (h.x < 0.0004 * t + 0.0002) { res = vec3(t, h.y, h.z); break; }
        t += h.x * 0.9;
        if (t > 40.0) break;
    }
    vec3 col;
    float tHit = res.x < 0.0 ? 1e9 : res.x;
    if (res.x < 0.0) col = background(rd);
    else {
        vec3 p = ro + rd * res.x;
        col = shade(p, calcNormal(p), rd, res, res.x);
    }
    // ball trail glow (in front of the hit surface only)
    for (int i = 0; i < 8; i++) {
        vec4 tr = u_trail[i];
        if (tr.w <= 0.0) continue;
        vec3 w = tr.xyz - ro;
        float along = dot(w, rd);
        if (along < 0.0 || along > tHit + 0.05) continue;
        float d = length(w - rd * along);
        col += vec3(1.0, 0.95, 0.85) * tr.w * exp(-d * d / (0.0009 + 0.00002 * along * along)) * 0.9;
    }
    if (isnan(col.r + col.g + col.b) || isinf(col.r + col.g + col.b)) col = vec3(0.03, 0.045, 0.085);
    f_color = vec4(min(col, vec3(60.0)), 1.0);
}
#endif

#ifdef BRIGHT_PASS
uniform sampler2D u_hdr;
void main() {
    vec3 c = texture(u_hdr, v_uv).rgb;
    float l = max(c.r, max(c.g, c.b));
    f_color = vec4(c * smoothstep(0.8, 2.0, l), 1.0);
}
#endif

#ifdef POST_PASS
uniform sampler2D u_hdr;
uniform sampler2D u_bright;
uniform float u_impact;
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
    col += bloom / wsum * 0.8;
    vec2 vp = v_uv - 0.5;
    col *= 1.0 - 0.6 * dot(vp, vp);
    col = aces(col * 1.1);
    col = pow(col, vec3(1.0 / 2.2));
    col = mix(col, vec3(1.0), 0.35 * u_impact);
    col += (hash12(gl_FragCoord.xy + fract(u_time * 7.13) * 100.0) - 0.5) / 255.0;
    f_color = vec4(col, 1.0);
}
#endif
