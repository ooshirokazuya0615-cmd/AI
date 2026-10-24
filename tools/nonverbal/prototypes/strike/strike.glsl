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
uniform vec3 u_ballPos;
uniform mat3 u_ballRot;
uniform vec3 u_pinPos[10];
uniform mat3 u_pinRot[10];
uniform float u_waveT;          // seconds since the ball tapped domino 0 (negative before)
uniform float u_bigA;           // slab angle
uniform int u_nNote;
uniform float u_noteK[32];
uniform vec3 u_noteCol[32];
uniform vec3 u_fx;              // strike flash, boom flash, kick pulse
uniform vec3 u_stA[11];
uniform vec3 u_stB[11];
uniform vec3 u_head;

const float PI = 3.14159265;
const float BALL_R = 0.109;
const float LANE_HALF = 0.533;
const float DECK_END = 4.0;
const float D_H = 0.30, D_W = 0.15, D_T = 0.04, D_D = 0.12, D_Z0 = 4.6;
const int N_DOM = 144;
const float DT = 0.0416666667;
const float TH_C = 0.26993, TH_R = 1.23096;
const float B_H = 0.90, B_W = 0.45, B_T = 0.12, B_Z = 21.92;
const vec3 KEY = normalize(vec3(-0.35, 0.90, -0.30));
const vec3 KEYCOL = vec3(1.25, 1.12, 0.98);

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

float domAngle(int k) {
    float tau = u_waveT - float(k) * DT;
    if (tau <= 0.0) return 0.0;
    if (tau < DT) { float u = tau / DT; return TH_C * (0.45 * u + 0.55 * u * u); }
    float u = clamp((tau - DT) / 0.40, 0.0, 1.0);
    return TH_C + (TH_R - TH_C) * (1.0 - pow(1.0 - u, 3.0));
}

// slab that rotates about its front-bottom edge (toward +z)
float sdTipped(vec3 p, float zc, float h, float w, float t, float a) {
    vec3 q = p - vec3(0.0, 0.0, zc + 0.5 * t);
    float c = cos(a), s = sin(a);
    q = vec3(q.x, c * q.y + s * q.z, -s * q.y + c * q.z);
    return sdRoundBox(q - vec3(0.0, 0.5 * h, -0.5 * t), vec3(0.5 * w, 0.5 * h, 0.5 * t), 0.008);
}

float sdPin(vec3 q) {
    float d = sdEllipsoid(q - vec3(0.0, -0.035, 0.0), vec3(0.0605, 0.118, 0.0605));
    d = smin(d, sdCapsule(q, vec3(0.0, 0.06, 0.0), vec3(0.0, 0.17, 0.0), 0.0235), 0.035);
    d = smin(d, length(q - vec3(0.0, 0.195, 0.0)) - 0.034, 0.03);
    d = max(d, -0.15 - q.y);
    return d;
}

float floorSDF(vec3 p) {
    float d = p.y;
    if (p.z < DECK_END) {
        float g = length(vec2(abs(p.x) - 0.5915, p.y)) - 0.058;
        d = max(d, -g);
    }
    return d;
}

float ballSDF(vec3 p) {
    vec3 q = transpose(u_ballRot) * (p - u_ballPos);
    float d = length(q) - BALL_R;
    // three finger holes
    vec3 h1 = normalize(vec3(0.0, 0.25, 1.0)), h2 = normalize(vec3(-0.22, 0.55, 0.8)), h3 = normalize(vec3(0.22, 0.55, 0.8));
    if (dot(q, h1) > 0.0) d = max(d, -(length(cross(q, h1)) - 0.012));
    if (dot(q, h2) > 0.0) d = max(d, -(length(cross(q, h2)) - 0.010));
    if (dot(q, h3) > 0.0) d = max(d, -(length(cross(q, h3)) - 0.010));
    return d;
}

vec3 map(vec3 p) {   // (dist, material, id)
    vec3 res = vec3(floorSDF(p), 1.0, 0.0);
    // ball
    float bb = length(p - u_ballPos) - BALL_R - 0.02;
    if (bb < res.x) {
        float d = ballSDF(p);
        if (d < res.x) res = vec3(d, 2.0, 0.0);
    }
    // pins (bounded)
    for (int i = 0; i < 10; i++) {
        float bd = length(p - u_pinPos[i]) - 0.25;
        if (bd > res.x) continue;
        float d = sdPin(transpose(u_pinRot[i]) * (p - u_pinPos[i]));
        if (d < res.x) res = vec3(d, 3.0, float(i));
    }
    // small dominoes (domain repetition along the line)
    vec3 lo = vec3(-0.12, -0.01, D_Z0 - 0.06), hi = vec3(0.12, 0.33, D_Z0 + float(N_DOM) * D_D + 0.3);
    vec3 bq = max(lo - p, p - hi);
    float bdist = length(max(bq, 0.0)) + min(max(bq.x, max(bq.y, bq.z)), 0.0);
    if (bdist < res.x) {
        int kc = int(floor((p.z - D_Z0) / D_D + 0.5));
        for (int j = -3; j <= 1; j++) {
            int k = kc + j;
            if (k < 0 || k >= N_DOM) continue;
            float d = sdTipped(p, D_Z0 + float(k) * D_D, D_H, D_W, D_T, domAngle(k));
            if (d < res.x) res = vec3(d, 4.0, float(k));
        }
    }
    // stickman bowler
    float sb = length(p - u_stA[0]) - 1.0;
    if (sb < res.x) {
        float d = length(p - u_head) - 0.085;
        for (int i = 0; i < 11; i++) {
            float r = i == 0 ? 0.034 : (i >= 9 ? 0.026 : 0.028);
            d = smin(d, sdCapsule(p, u_stA[i], u_stB[i], r), 0.018);
        }
        if (d < res.x) res = vec3(d, 6.0, 0.0);
    }
    // big slab
    float bs = length(p - vec3(0.0, 0.45, B_Z + 0.4)) - 1.1;
    if (bs < res.x) {
        float d = sdTipped(p, B_Z, B_H, B_W, B_T, u_bigA);
        if (d < res.x) res = vec3(d, 5.0, 0.0);
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

int noteSlot(int k) {
    for (int i = 0; i < 32; i++) {
        if (i >= u_nNote) break;
        if (abs(u_noteK[i] - float(k)) < 0.5) return i;
    }
    return -1;
}

vec3 background(vec3 rd) {
    vec3 col = mix(vec3(0.020, 0.022, 0.040), vec3(0.004, 0.005, 0.012), smoothstep(-0.1, 0.6, rd.y));
    // rows of ceiling lights over the alley
    if (rd.y > 0.02) {
        vec2 c = rd.xz / rd.y * 3.0;
        vec2 g = abs(fract(c * vec2(0.45, 0.22)) - 0.5);
        float l = (1.0 - smoothstep(0.05, 0.08, g.x)) * (1.0 - smoothstep(0.12, 0.18, g.y));
        col += vec3(1.0, 0.86, 0.62) * l * 0.32 * exp(-length(c) * 0.05);
    }
    col += vec3(0.25, 0.18, 0.55) * 0.05 * u_fx.z;
    return col;
}

// light spill from glowing note dominoes onto the floor
vec3 noteSpill(vec3 p) {
    vec3 acc = vec3(0.0);
    if (p.z < D_Z0 - 0.5) return acc;
    for (int i = 0; i < 32; i++) {
        if (i >= u_nNote) break;
        int k = int(u_noteK[i] + 0.5);
        float age = u_waveT - float(k) * DT;
        if (age < 0.0) continue;
        float zk = D_Z0 + float(k) * D_D + 0.12;
        float d = length(vec2(p.x, p.z - zk));
        float e = 0.35 + 3.0 * exp(-age / 0.25);
        acc += u_noteCol[i] * e * exp(-d * 9.0) * 0.20;
    }
    return acc;
}

vec3 shadeFloor(vec3 p, vec3 n, vec3 rd, float sh, float occ, out float refl) {
    vec3 col;
    float gloss = 0.0;
    if (p.z < DECK_END && abs(p.x) < LANE_HALF) {
        // maple boards along z
        float board = floor((p.x + LANE_HALF) / (2.0 * LANE_HALF / 39.0));
        float bn = hash12(vec2(board, 1.7));
        vec3 wood = mix(vec3(0.62, 0.40, 0.20), vec3(0.78, 0.55, 0.30), bn);
        float grain = sin(p.z * 60.0 + bn * 40.0 + sin(p.z * 7.0 + board) * 2.0) * 0.5 + 0.5;
        wood *= 0.88 + 0.12 * grain;
        float fb = fract((p.x + LANE_HALF) / (2.0 * LANE_HALF / 39.0));
        float seam = 1.0 - smoothstep(0.0, 0.05, min(fb, 1.0 - fb));
        wood *= 1.0 - 0.25 * seam;
        // aiming arrows
        for (int i = -3; i <= 3; i++) {
            float ax = float(i) * 5.0 * (2.0 * LANE_HALF / 39.0);
            float az = 1.2 + abs(float(i)) * 0.09;
            vec2 q = vec2(p.x - ax, p.z - az);
            float tri = max(abs(q.x) * 3.2 + q.y, -q.y - 0.12);
            wood = mix(wood, vec3(0.08, 0.05, 0.04), 1.0 - smoothstep(0.0, 0.004, tri));
        }
        // pin spots
        col = wood;
        gloss = 0.55;
    } else if (p.z < DECK_END && abs(p.x) < 0.66) {
        col = vec3(0.10, 0.10, 0.11);   // gutter
        gloss = 0.25;
    } else if (p.z < DECK_END) {
        col = vec3(0.05, 0.035, 0.03);  // neighbouring approach
        gloss = 0.2;
    } else {
        // stage: dark slate with a faint grid
        col = vec3(0.030, 0.032, 0.045);
        vec2 g = abs(fract(p.xz * 2.0) - 0.5);
        float line = 1.0 - smoothstep(0.485, 0.5, max(g.x, g.y));
        col += vec3(0.05, 0.06, 0.12) * line * 0.6;
        gloss = 0.22;
    }
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 c = col * (KEYCOL * dif * 0.9 + vec3(0.20, 0.22, 0.32) * occ * 0.55);
    c += noteSpill(p) * occ;
    c += vec3(1.0, 0.7, 0.4) * u_fx.x * exp(-length(p.xz - vec2(0.0, 3.1)) * 2.5) * 0.8;  // strike flash
    refl = gloss;
    return c;
}

vec3 shadeBall(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 q = transpose(u_ballRot) * (p - u_ballPos) / BALL_R;
    float sw = sin(q.x * 7.0 + sin(q.y * 9.0 + q.z * 5.0) * 1.8 + q.z * 3.0);
    vec3 base = mix(vec3(0.02, 0.05, 0.22), vec3(0.10, 0.28, 0.75), smoothstep(-0.4, 0.9, sw));
    base = mix(base, vec3(0.85, 0.65, 0.25), smoothstep(0.93, 0.99, sw) * 0.6);
    float hole = 1.0 - smoothstep(BALL_R - 0.006, BALL_R - 0.001, length(p - u_ballPos));
    base *= 1.0 - 0.9 * hole;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 120.0) * sh;
    float fre = pow(1.0 - max(dot(n, -rd), 0.0), 4.0);
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 col = base * (KEYCOL * dif * 0.9 + vec3(0.25, 0.27, 0.40) * occ * 0.5);
    col += vec3(1.0) * spe * 1.6 + vec3(0.6, 0.65, 0.9) * fre * 0.35 * occ;
    return col;
}

vec3 shadePin(vec3 p, vec3 n, int i, vec3 rd, float sh, float occ) {
    vec3 q = transpose(u_pinRot[i]) * (p - u_pinPos[i]);
    vec3 base = vec3(0.92, 0.91, 0.88);
    float stripe = (1.0 - smoothstep(0.004, 0.007, abs(q.y - 0.090))) + (1.0 - smoothstep(0.004, 0.007, abs(q.y - 0.118)));
    base = mix(base, vec3(0.80, 0.06, 0.06), clamp(stripe, 0.0, 1.0));
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 90.0) * sh;
    float dif = clamp(dot(n, KEY) * 0.85 + 0.15, 0.0, 1.0) * sh;
    vec3 col = base * (KEYCOL * dif * 0.85 + vec3(0.24, 0.26, 0.38) * occ * 0.55);
    col += spe * 1.1;
    return col;
}

vec3 shadeDomino(vec3 p, vec3 n, int k, vec3 rd, float sh, float occ) {
    int slot = noteSlot(k);
    float age = u_waveT - float(k) * DT;
    vec3 base = vec3(0.90, 0.87, 0.80);
    vec3 emit = vec3(0.0);
    // local coordinates to draw the centre line
    vec3 q = p - vec3(0.0, 0.0, D_Z0 + float(k) * D_D + 0.5 * D_T);
    float a = domAngle(k), c = cos(a), s = sin(a);
    q = vec3(q.x, c * q.y + s * q.z, -s * q.y + c * q.z);
    float midline = 1.0 - smoothstep(0.0025, 0.004, abs(q.y - 0.5 * D_H));
    base = mix(base, vec3(0.10), midline * 0.85);
    if (slot >= 0) {
        vec3 nc = u_noteCol[slot];
        base = mix(vec3(0.06, 0.06, 0.08), nc, 0.25);
        float lit = age > 0.0 ? 1.0 : 0.0;
        float flash = age > 0.0 ? exp(-age / 0.18) : 0.0;
        float pre = smoothstep(-0.6, 0.0, age) * (1.0 - lit);      // anticipation glow as the wave approaches
        vec3 lq = abs(q - vec3(0.0, 0.5 * D_H, -0.5 * D_T)) - vec3(0.5 * D_W, 0.5 * D_H, 0.5 * D_T);
        float edge = exp(-max(-max(lq.x, lq.y), 0.0) * 120.0);
        emit = nc * (edge * (0.6 + 1.2 * lit + 0.8 * pre) + (0.25 * lit + 4.0 * flash + 0.25 * pre));
    }
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 70.0) * sh;
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 col = base * (KEYCOL * dif * 0.9 + vec3(0.22, 0.24, 0.36) * occ * 0.6);
    col += spe * (slot >= 0 ? 0.9 : 0.5) + emit;
    return col;
}

vec3 shadeBig(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 q = p - vec3(0.0, 0.0, B_Z + 0.5 * B_T);
    float c = cos(u_bigA), s = sin(u_bigA);
    q = vec3(q.x, c * q.y + s * q.z, -s * q.y + c * q.z);
    vec3 lq = abs(q - vec3(0.0, 0.5 * B_H, -0.5 * B_T)) - vec3(0.5 * B_W, 0.5 * B_H, 0.5 * B_T);
    float edge = exp(-max(-max(lq.x, lq.y), 0.0) * 60.0);
    vec3 base = vec3(0.025, 0.025, 0.03);
    vec3 gold = vec3(1.0, 0.72, 0.30);
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 100.0) * sh;
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 col = base * (KEYCOL * dif + 0.3 * occ) + spe * 1.2;
    col += gold * edge * (0.6 + 2.5 * u_fx.y);
    return col;
}

vec3 shadeStick(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 base = vec3(0.95, 0.93, 0.88);
    float dif = clamp(dot(n, KEY) * 0.8 + 0.2, 0.0, 1.0) * sh;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 50.0) * sh;
    float fre = pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    vec3 col = base * (KEYCOL * dif * 0.9 + vec3(0.25, 0.27, 0.42) * occ * 0.6);
    col += spe * 0.35 + vec3(0.45, 0.55, 1.0) * fre * 0.45 * occ;
    return col;
}

vec3 shade(vec3 p, vec3 n, vec3 rd, vec3 res, float t, bool full, out float refl) {
    refl = 0.0;
    float sh = full ? softShadow(p + n * 0.002, KEY) : 1.0;
    float occ = full ? ao(p, n) : 1.0;
    vec3 col;
    if (res.y < 1.5) col = shadeFloor(p, n, rd, sh, occ, refl);
    else if (res.y < 2.5) col = shadeBall(p, n, rd, sh, occ);
    else if (res.y < 3.5) col = shadePin(p, n, int(res.z + 0.5), rd, sh, occ);
    else if (res.y < 4.5) col = shadeDomino(p, n, int(res.z + 0.5), rd, sh, occ);
    else if (res.y < 5.5) col = shadeBig(p, n, rd, sh, occ);
    else col = shadeStick(p, n, rd, sh, occ);
    col = mix(col, vec3(0.02, 0.022, 0.04), 1.0 - exp(-0.0025 * t * t));
    return col;
}

vec3 march(vec3 ro, vec3 rd, int steps, float tmax, out vec3 res) {
    float t = 0.0;
    res = vec3(-1.0, 0.0, 0.0);
    for (int i = 0; i < 160; i++) {
        if (i >= steps) break;
        vec3 h = map(ro + rd * t);
        if (h.x < 0.0004 * t + 0.0002) { res = vec3(t, h.y, h.z); break; }
        t += h.x * 0.9;
        if (t > tmax) break;
    }
    return ro + rd * t;
}

void main() {
    vec2 uv = (2.0 * gl_FragCoord.xy - u_res) / u_res.y;
    vec3 rd = normalize(u_camRot * vec3(uv * u_tanH, 1.0));
    vec3 ro = u_camPos;
    vec3 res;
    vec3 p = march(ro, rd, 150, 40.0, res);
    vec3 col;
    if (res.x < 0.0) {
        col = background(rd);
    } else {
        vec3 n = calcNormal(p);
        float refl;
        col = shade(p, n, rd, res, res.x, true, refl);
        if (refl > 0.0) {
            vec3 rr = reflect(rd, n);
            vec3 r2;
            vec3 p2 = march(p + n * 0.003, rr, 70, 12.0, r2);
            vec3 rc;
            if (r2.x < 0.0) rc = background(rr);
            else { float dummy; rc = shade(p2, calcNormal(p2), rr, r2, r2.x + res.x, false, dummy); }
            float fre = 0.04 + 0.96 * pow(1.0 - max(dot(n, -rd), 0.0), 5.0);
            col = mix(col, rc, clamp(refl * (0.25 + 0.75 * fre), 0.0, 0.9));
        }
    }
    f_color = vec4(col, 1.0);
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
