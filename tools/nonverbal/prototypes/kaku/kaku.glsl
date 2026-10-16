#version 330
// KAKU & RONDO #2 Square Track. 3 passes in one file: SCENE (raymarch -> HDR), BRIGHT, POST.
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
float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x), mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}

#ifdef SCENE_PASS
uniform vec3 u_camPos;
uniform mat3 u_camRot;
uniform float u_tanH;
uniform vec3 u_kC;            // Kaku centre
uniform mat3 u_kR;            // Kaku local -> world
uniform vec3 u_knot, u_tail1, u_tail2;
uniform vec3 u_rP;            // Rondo centre
uniform vec3 u_rN;            // normal of the brass great circle (world)
uniform vec3 u_look;          // stands look target x, z, blend
uniform float u_glow[6];
uniform float u_fin;          // finale: whole stand gold
uniform vec3 u_stA[11];
uniform vec3 u_stB[11];
uniform vec3 u_head;
uniform vec3 u_malA, u_malB;
uniform float u_metro;
uniform vec4 u_board;         // cube state, ball state, cube flip age, ball flip age
uniform float u_startAge;     // seconds since the start fork was struck
uniform float u_fpFade;
uniform sampler2D u_grid;     // 16x16: score flag (+order/100), footprint time, on-score flag, face id
uniform float u_finAge;       // seconds since Kaku finished (<0 before)
uniform vec2 u_score;         // x: pulse of unplayed score squares (0..1), y: hesitation progress (0..1, <0 off)
uniform vec3 u_rDots[16];     // Rondo's brass touches on the ground: x, z, age (<0 unused)

const float PI = 3.14159265;
const float H = 7.2;
const float CELL = 1.8;
const float TRK_IN = -3.0, TRK_OUT = 2.6;     // track band in L-inf radius around the centre square
const float STAND0 = 18.0, TIER_D = 1.1, TIER_H = 0.55;
const int NTIER = 10;
const float BACK = 29.0;
const vec3 START_FORK = vec3(-7.0, 0.0, -11.2);
const vec3 TI_POS = vec3(-10.6, 0.0, -4.6);
const vec3 METRO = vec3(-2.5, 0.0, 2.5);
const vec3 BOARD_C = vec3(-29.9, 12.1, -21.2);
const vec3 BOARD_EX = vec3(-0.895, 0.0, -0.446);   // board local x (its face looks along -x local = toward the first camera)
const vec3 BOARD_EZ = vec3(0.446, 0.0, -0.895);
const vec3 KEY = normalize(vec3(-0.42, 0.80, -0.30));
const vec3 KEYCOL = vec3(1.18, 1.12, 1.02);
const vec3 SKYCOL = vec3(0.62, 0.60, 0.54);
const vec3 CHIP_N = vec3(-0.57735, 0.57735, 0.57735);

// colours (linear)
const vec3 C_TRACK = vec3(0.46, 0.43, 0.37);
const vec3 C_LINE = vec3(0.065, 0.074, 0.088);
const vec3 C_APRON = vec3(0.36, 0.345, 0.315);
const vec3 C_GRASS = vec3(0.16, 0.20, 0.11);
const vec3 C_STONE = vec3(0.374, 0.357, 0.315);
const vec3 C_WALNUT = vec3(0.121, 0.053, 0.023);
const vec3 C_BAND = vec3(0.82, 0.75, 0.61);
const vec3 C_STEEL = vec3(0.036, 0.066, 0.15);
const vec3 C_BRASS = vec3(0.46, 0.29, 0.10);
const vec3 C_SCORE = vec3(0.56, 0.44, 0.26);
const vec3 C_CERAMIC = vec3(0.80, 0.78, 0.73);
const vec3 C_GOLD = vec3(1.00, 0.66, 0.24);

float sdRoundBox(vec3 p, vec3 b, float r) {
    vec3 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}
float sdBox2(vec2 p, vec2 b) {
    vec2 d = abs(p) - b;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}
float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
    vec3 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h) - r;
}
float smin(float a, float b, float k) {
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}
float sdEllipsoid(vec3 p, vec3 r) {
    float k0 = length(p / r);
    float k1 = length(p / (r * r));
    return k0 * (k0 - 1.0) / k1;
}
float g_tine = 0.037;
// tuning fork in local space (x: across the prongs, y: up, z: facing). size ~ 1.75 m
float sdFork(vec3 q, float s) {
    q /= s;
    float d = sdCapsule(q, vec3(0.0, 0.0, 0.0), vec3(0.0, 0.62, 0.0), 0.036);
    float bend;
    if (q.y < 0.78) bend = length(vec2(length(vec2(q.x, q.y - 0.78)) - 0.15, q.z)) - 0.036;   // lower half of the U
    else bend = length(vec3(abs(q.x) - 0.15, q.y - 0.78, q.z)) - 0.036;
    d = min(d, bend);
    d = min(d, sdCapsule(q, vec3(-0.15, 0.78, 0.0), vec3(-0.15, 1.72, 0.0), g_tine));
    d = min(d, sdCapsule(q, vec3(0.15, 0.78, 0.0), vec3(0.15, 1.72, 0.0), g_tine));
    d = min(d, max(length(q.xz) - 0.11, abs(q.y - 0.02) - 0.02));   // little foot
    return d * s;
}

float g_envDim = 1.0;

float kakuBox(vec3 p) {
    vec3 q = transpose(u_kR) * (p - u_kC);
    float d = sdRoundBox(q, vec3(0.9), 0.045);
    return max(d, dot(q, CHIP_N) - 1.4105);
}

// stands: (dist, section, glow-id) ; staircase in (m, y) where m = L-inf radius
vec3 mapStands(vec3 p) {
    float m = max(abs(p.x), abs(p.z));
    if (m < STAND0 - 1.0) return vec3(STAND0 - 0.35 - m, 6.0, 0.0);
    float res = 1e9;
    // front wall
    float fw = sdBox2(vec2(m - (STAND0 - 0.15), p.y - 0.25), vec2(0.15, 0.25));
    res = fw;
    float kf = clamp(floor((m - STAND0) / TIER_D), 0.0, float(NTIER - 1));
    for (int j = -1; j <= 1; j++) {
        float k = clamp(kf + float(j), 0.0, float(NTIER - 1));
        float top = 0.5 + TIER_H * k;
        float m0 = STAND0 + TIER_D * k;
        float d = sdBox2(vec2(m - (m0 + BACK) * 0.5, p.y - top * 0.5), vec2((BACK - m0) * 0.5, top * 0.5));
        res = min(res, d);
    }
    // rim / back wall
    res = min(res, sdBox2(vec2(m - (BACK + 0.4), p.y - 3.4), vec2(0.4, 3.4)));
    vec3 out_ = vec3(res, 6.0, 0.0);
    // forks on this tier and the next one
    bool sx = abs(p.x) >= abs(p.z);
    float u = sx ? p.z : p.x;
    float uc = (floor(u) + 0.5);
    g_tine = max(0.037, 0.7 * length(p - u_camPos) * 2.0 * u_tanH / u_res.y);
    for (int j = 0; j <= 1; j++) {
        float k = clamp(kf + float(j), 0.0, float(NTIER - 1));
        float mc = STAND0 + TIER_D * k + 0.55;
        float top = 0.5 + TIER_H * k;
        if (abs(uc) > mc - 0.7) continue;
        vec3 fw3 = sx ? vec3(sign(p.x) * mc, top, uc) : vec3(uc, top, sign(p.z) * mc);
        float df;
        if (p.y > top + 1.85) {
            df = max(p.y - (top + 1.8), 0.0) + 0.02;
        } else {
            vec2 toC = normalize(-fw3.xz);
            vec2 toT = normalize(u_look.xy - fw3.xz);
            float a0 = atan(toC.y, toC.x);
            float a1 = atan(toT.y, toT.x);
            float da = a1 - a0;
            da = da - 2.0 * PI * floor((da + PI) / (2.0 * PI));
            float w = clamp(u_look.z * 1.6 - length(fw3.xz - u_look.xy) / 40.0, 0.0, 1.0);
            w = smoothstep(0.0, 1.0, w);
            float a = a0 + clamp(da * 1.5, -1.3, 1.3) * w;
            vec2 f = vec2(cos(a), sin(a));
            vec3 rel = p - fw3;
            vec3 q = vec3(dot(rel.xz, vec2(-f.y, f.x)), rel.y, dot(rel.xz, f));
            float lean = 0.2 * w;                    // heads lean toward what they watch
            float cl = cos(lean), sl = sin(lean);
            q = vec3(q.x, q.y * cl + q.z * sl, -q.y * sl + q.z * cl);
            df = sdFork(q, 1.0);
            float edge = 0.5 - abs(u - uc);
            df = min(df, max(edge + 0.28, 0.02));
        }
        if (df < out_.x) {
            float ang = atan(fw3.z, fw3.x);
            float sec = mod(floor((ang + PI) / (2.0 * PI) * 6.0 + 0.5), 6.0);
            out_ = vec3(df, 5.0, sec + 0.09 * hash12(fw3.xz * 0.37));
        }
    }
    return out_;
}

vec3 map(vec3 p) {  // (dist, material, id)
    vec3 res = vec3(p.y, 1.0, 0.0);
    // Kaku + headband + knot + tails
    float bk = length(p - u_kC) - 1.75;
    if (bk < res.x) {
        float d = kakuBox(p);
        if (d < res.x) res = vec3(d, 2.0, 0.0);
        float shell = max(d - 0.017, -d - 0.004);
        float band = max(shell, abs(p.y - u_kC.y) - 0.115);
        float kn = sdEllipsoid(p - u_knot, vec3(0.075, 0.065, 0.075));
        float tl = min(sdCapsule(p, u_knot, u_tail1, 0.024), sdCapsule(p, u_knot, u_tail2, 0.024));
        band = min(band, min(kn, tl));
        if (band < res.x) res = vec3(band, 3.0, 0.0);
    }
    // Rondo
    float dr = length(p - u_rP) - 0.30;
    if (dr < res.x) res = vec3(dr, 4.0, 0.0);
    // starter + mallet
    float sb = length(p - (u_stA[0] + u_stB[0]) * 0.5) - 1.6;
    if (sb < res.x) {
        float d = length(p - u_head) - 0.145;
        for (int i = 0; i < 11; i++) {
            float r = i == 0 ? 0.058 : (i >= 9 ? 0.044 : 0.048);
            d = smin(d, sdCapsule(p, u_stA[i], u_stB[i], r), 0.03);
        }
        if (d < res.x) res = vec3(d, 7.0, 0.0);
        float ml = sdCapsule(p, u_malA, u_malB, 0.022);
        ml = min(ml, length(p - u_malB) - 0.075);
        if (ml < res.x) res = vec3(ml, 8.0, 0.0);
    }
    // the start fork (big) + its plinth
    vec3 qs = p - START_FORK;
    if (length(qs - vec3(0.0, 1.4, 0.0)) - 2.2 < res.x) {
        float wob = u_startAge > 0.0 ? 0.03 * exp(-u_startAge * 1.6) * sin(u_startAge * 70.0) : 0.0;
        vec3 q = vec3(qs.z, qs.y - 0.45, qs.x);              // prongs across z, facing x (toward the starter)
        q.x += wob * max(q.y - 1.0, 0.0);
        float d = sdFork(q, 1.38);
        if (d < res.x) res = vec3(d, 11.0, 0.0);
        float pl = sdRoundBox(qs - vec3(0.0, 0.22, 0.0), vec3(0.45, 0.22, 0.45), 0.03);
        if (pl < res.x) res = vec3(pl, 6.0, 0.0);
    }
    // TI: tiny fork on a little post, always facing Kaku
    vec3 qt = p - TI_POS;
    if (length(qt - vec3(0.0, 0.6, 0.0)) - 1.0 < res.x) {
        vec2 f = normalize(u_kC.xz - TI_POS.xz);
        vec3 q = vec3(dot(qt.xz, vec2(-f.y, f.x)), qt.y - 0.62, dot(qt.xz, f));
        float d = sdFork(q, 0.34);
        if (d < res.x) res = vec3(d, 12.0, 0.0);
        float post = sdRoundBox(qt - vec3(0.0, 0.31, 0.0), vec3(0.09, 0.31, 0.09), 0.02);
        if (post < res.x) res = vec3(post, 6.0, 0.0);
    }
    // the metronome referee
    vec3 qm = p - METRO;
    if (length(qm - vec3(0.0, 0.9, 0.0)) - 1.6 < res.x) {
        float h = clamp(qm.y / 1.5, 0.0, 1.0);
        float w = mix(0.42, 0.14, h);
        float body = max(sdRoundBox(qm - vec3(0.0, 0.75, 0.0), vec3(w, 0.75, w * 0.8), 0.02), -qm.y);
        if (body < res.x) res = vec3(body * 0.8, 9.0, 0.0);
        vec3 piv = METRO + vec3(0.0, 0.25, 0.36);
        vec3 tip = piv + vec3(sin(u_metro), cos(u_metro), 0.0) * 1.15;
        float rod = sdCapsule(p, piv, tip, 0.016);
        rod = min(rod, sdRoundBox(p - (piv + (tip - piv) * 0.7), vec3(0.07, 0.05, 0.03), 0.01));
        if (rod < res.x) res = vec3(rod, 13.0, 0.0);
    }
    // scoreboard on posts above the far stand
    vec3 rb = p - BOARD_C;
    vec3 qb = vec3(dot(rb, BOARD_EX), rb.y, dot(rb, BOARD_EZ));
    if (sdRoundBox(qb - vec3(0.0, -4.5, 0.0), vec3(1.0, 8.4, 3.0), 0.0) < res.x) {
        float d = sdRoundBox(qb, vec3(0.18, 3.3, 2.35), 0.05);
        if (d < res.x) res = vec3(d, 10.0, 0.0);
        float posts = min(sdCapsule(qb, vec3(0.3, -3.2, -1.5), vec3(0.3, -12.2, -1.5), 0.16),
                          sdCapsule(qb, vec3(0.3, -3.2, 1.5), vec3(0.3, -12.2, 1.5), 0.16));
        if (posts < res.x) res = vec3(posts, 14.0, 0.0);
    }
    vec3 st = mapStands(p);
    if (st.x < res.x) res = st;
    return res;
}

vec3 calcNormal(vec3 p, float t) {
    float e = 0.0006 + 0.0004 * t;
    vec2 k = vec2(1, -1) * e;
    return normalize(k.xyy * map(p + k.xyy).x + k.yyx * map(p + k.yyx).x +
                     k.yxy * map(p + k.yxy).x + k.xxx * map(p + k.xxx).x);
}

float softShadow(vec3 ro, vec3 rd, float tmax) {
    float res = 1.0, t = 0.02;
    for (int i = 0; i < 40; i++) {
        float h = map(ro + rd * t).x;
        res = min(res, 6.0 * h / t);
        t += clamp(h, 0.03, 0.6);
        if (res < 0.004 || t > tmax) break;
    }
    return clamp(res, 0.0, 1.0);
}

float ao(vec3 p, vec3 n) {
    float occ = 0.0, sca = 1.0;
    for (int i = 1; i <= 4; i++) {
        float h = 0.03 + 0.09 * float(i);
        occ += (h - map(p + n * h).x) * sca;
        sca *= 0.65;
    }
    return clamp(1.0 - 1.6 * occ, 0.0, 1.0);
}

vec3 sky(vec3 rd) {
    float y = clamp(rd.y, -0.2, 1.0);
    vec3 col = mix(vec3(0.70, 0.67, 0.60), vec3(0.52, 0.53, 0.53), smoothstep(0.0, 0.7, y));
    float cl = vnoise(rd.xz / max(rd.y, 0.08) * 1.4 + 3.0) * 0.6 + vnoise(rd.xz / max(rd.y, 0.08) * 3.7) * 0.4;
    col *= 0.94 + 0.10 * cl;
    return col * vec3(0.95, 0.93, 0.88) * (1.0 - 0.35 * u_fin);
}

// grain patterns: 0 straight, 1 cathedral, 2 rings; uv in [-1,1]
float grain(vec2 uv, float kind, float seed) {
    float g;
    if (kind < 0.5) g = sin((uv.x + 0.05 * vnoise(uv * 3.0 + seed)) * 70.0 + vnoise(uv * vec2(8.0, 1.5) + seed) * 3.0);
    else if (kind < 1.5) g = sin(length(vec2(uv.x * 1.6, uv.y + 1.6)) * 62.0 + vnoise(uv * 4.0 + seed) * 2.5);
    else g = sin(length(uv - vec2(0.35, -0.25)) * 70.0 + vnoise(uv * 5.0 + seed) * 3.0);
    return g * 0.5 + 0.5;
}

float faceKind(int face) {
    // FACE_IDX: 0 +X(B) 1 -X(F#) 2 +Y(D') 3 -Y(D) 4 +Z(A) 5 -Z(E)
    if (face <= 1) return 0.0;
    if (face <= 3) return 2.0;
    return 1.0;
}

vec3 shadeGround(vec3 p, vec3 n, float sh, float occ) {
    float m = max(abs(p.x), abs(p.z));
    float r = m - H;
    vec3 col;
    if (r < TRK_IN) {
        float stripe = step(0.5, fract((p.x + p.z) * 0.28));
        col = C_GRASS * (0.9 + 0.06 * stripe) * (0.9 + 0.2 * vnoise(p.xz * 6.0));
    } else if (r < TRK_OUT) {
        col = C_TRACK * (0.93 + 0.10 * vnoise(p.xz * 3.0) + 0.05 * vnoise(p.xz * 23.0));
        // grid cells
        ivec2 ci = ivec2(floor(p.x / CELL + 0.5) + 8.0, floor(p.z / CELL + 0.5) + 8.0);
        vec2 cc = (vec2(ci) - 8.0) * CELL;
        vec2 lp = (p.xz - cc) / (CELL * 0.5);          // [-1,1] in the cell
        if (ci.x >= 0 && ci.x < 16 && ci.y >= 0 && ci.y < 16) {
            vec4 g = texelFetch(u_grid, ci, 0);
            float inner = 1.0 - smoothstep(0.86, 0.90, max(abs(lp.x), abs(lp.y)));
            float cr = max(abs(cc.x), abs(cc.y)) - H;
            // the straight way: thin charcoal outlines on the centre line cells
            if (abs(cr) < 0.1) {
                float ol = smoothstep(0.035, 0.0, abs(max(abs(lp.x), abs(lp.y)) - 0.92));
                col = mix(col, C_LINE, ol * 0.85);
            }
            // the score: light amber squares with a hint of grain
            if (g.x > 0.5) {
                col = mix(col, C_SCORE * (0.95 + 0.08 * grain(lp, 1.0, 3.0)), inner * 0.72);
                bool unplayed = !(g.y >= 0.0 && u_time >= g.y);
                float order = floor((g.x - 1.0) * 100.0 + 0.5);
                if (unplayed) col += C_GOLD * 0.15 * u_score.x * inner;
                if (unplayed && order > 0.5 && u_score.y >= 0.0 && order <= u_score.y * 14.0 + 0.5) col += C_GOLD * 0.35 * inner;
            }
            // footprints
            if (g.y >= 0.0 && u_time >= g.y) {
                float age = u_time - g.y;
                float k = faceKind(int(g.w + 0.5));
                vec3 fpc = mix(vec3(0.20, 0.10, 0.045), vec3(0.11, 0.05, 0.02), grain(lp, k, g.w));
                if (g.z < 0.5) fpc = mix(col, fpc, 0.35);
                float a = inner * (1.0 - exp(-age / 0.05)) * u_fpFade;
                col = mix(col, fpc, a * 0.92);
                col += C_GOLD * inner * exp(-age / 0.22) * 0.9 * u_fpFade * (0.4 + 0.6 * g.z);
            }
        }
        // edge lines
        float e1 = abs(r - TRK_IN), e2 = abs(r - TRK_OUT);
        col = mix(col, C_LINE, smoothstep(0.07, 0.04, min(e1, e2)));
        // start line across the first straight, finish line (checks) across the last straight
        bool side1 = p.z < 0.0 && abs(p.z) >= abs(p.x);
        bool side4 = p.x < 0.0 && abs(p.x) >= abs(p.z);
        if (side1 && abs(p.x - (-H + 0.9)) < 0.07) col = C_LINE;
        if (side4 && abs(p.z - (-H + 0.9)) < 0.30) {
            float ch = mod(floor(p.x / 0.30) + floor((p.z + H) / 0.30), 2.0);
            col = mix(C_LINE, C_BAND * 0.9, ch);
        }
    } else {
        col = C_APRON * (0.92 + 0.10 * vnoise(p.xz * 1.5) + 0.04 * vnoise(p.xz * 17.0));
        // expansion joints
        vec2 jj = abs(fract(p.xz / 3.0) - 0.5);
        col *= 1.0 - 0.18 * smoothstep(0.012, 0.0, min(0.5 - jj.x, 0.5 - jj.y));
    }
    for (int i = 0; i < 16; i++) {
        vec3 dd = u_rDots[i];
        if (dd.z < 0.0) continue;
        float r = length(p.xz - dd.xy);
        col = mix(col, C_BRASS * 1.4, (1.0 - smoothstep(0.045, 0.065, r)) * exp(-dd.z / 1.5));
    }
    float dif = max(dot(n, KEY), 0.0) * sh;
    return col * (KEYCOL * dif * 0.85 + SKYCOL * occ * 0.75) * g_envDim;
}

vec3 shadeKaku(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 q = transpose(u_kR) * (p - u_kC);
    vec3 nl = transpose(u_kR) * n;
    vec3 an = abs(nl);
    int face;
    vec2 uv;
    if (an.x > an.y && an.x > an.z) { face = nl.x > 0.0 ? 0 : 1; uv = q.zy / 0.9; }
    else if (an.y > an.z) { face = nl.y > 0.0 ? 2 : 3; uv = q.xz / 0.9; }
    else { face = nl.z > 0.0 ? 4 : 5; uv = q.xy / 0.9; }
    float g = grain(uv, faceKind(face), float(face) * 1.7);
    vec3 base = mix(C_WALNUT * 1.18, C_WALNUT * 0.78, g);
    base *= 0.92 + 0.12 * vnoise(uv * 9.0 + float(face));
    // edges worn lighter
    vec3 eq = abs(q) / 0.9;
    float wear = smoothstep(1.86, 1.97, max(eq.x + eq.y, max(eq.y + eq.z, eq.x + eq.z)));
    base = mix(base, C_WALNUT * 1.7, wear * 0.5);
    // the chipped corner shows lighter end grain
    float chip = smoothstep(0.02, 0.0, abs(dot(q, CHIP_N) - 1.4105));
    base = mix(base, vec3(0.33, 0.20, 0.10), chip);
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 30.0) * sh * 0.10;
    float fill = max(dot(n, normalize(vec3(0.5, 0.3, 0.6))), 0.0) * 0.18;
    return base * (KEYCOL * dif * 0.95 + SKYCOL * occ * 0.75 + fill) * g_envDim + spe;
}

vec3 shadeCloth(vec3 p, vec3 n, float sh, float occ) {
    float weave = 0.94 + 0.06 * sin(p.y * 900.0) * sin((p.x + p.z) * 900.0);
    float dif = max(dot(n, KEY) * 0.8 + 0.2, 0.0) * sh;
    return C_BAND * weave * (KEYCOL * dif * 0.9 + SKYCOL * occ * 0.7);
}

vec3 shadeMetal(vec3 p, vec3 n, vec3 rd, float sh, float occ, vec3 tint, float rough) {
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), mix(160.0, 30.0, rough)) * sh;
    float dif = max(dot(n, KEY), 0.0) * sh;
    vec3 r = reflect(rd, n);
    vec3 env = mix(vec3(0.30, 0.28, 0.25), sky(r), smoothstep(-0.15, 0.2, r.y));
    float fre = 0.3 + 0.7 * pow(1.0 - max(dot(n, -rd), 0.0), 4.0);
    vec3 col = tint * (dif * KEYCOL * 0.55 + SKYCOL * occ * 0.35) + env * tint * 1.2 * fre * occ + spe * mix(vec3(1.0), tint * 2.0, 0.5) * 0.8;
    return col;
}

vec3 shadeRondo(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    vec3 q = (p - u_rP) / 0.30;
    float line = abs(dot(q, u_rN));
    float brass = 1.0 - smoothstep(0.045, 0.075, line);
    vec3 tint = mix(C_STEEL, C_BRASS, brass);
    vec3 c = shadeMetal(p, n, rd, sh, occ, tint, mix(0.35, 0.25, brass));
    c += vec3(0.30, 0.38, 0.55) * 0.15 * pow(1.0 - max(dot(n, -rd), 0.0), 3.0);
    return c + tint * mix(0.15, 0.22, brass);
}

vec3 shadeFork(vec3 p, vec3 n, vec3 rd, float sh, float occ, float sec, float rnd) {
    int s = int(sec + 0.5);
    float g = 0.0;
    for (int i = 0; i < 6; i++) if (i == s) g = u_glow[i];
    float shimmer = 0.75 + 0.25 * sin(u_time * 9.0 + rnd * 6.0);
    vec3 c = shadeMetal(p, n, rd, sh, occ, C_BRASS, 0.45) * g_envDim;
    c += vec3(1.0, 0.58, 0.16) * g * 1.0 * (0.7 + 0.3 * rnd);
    float finW = u_fin * smoothstep(0.0, 3.0, u_finAge * 35.0 - length(p.xz - u_kC.xz));
    c += vec3(1.0, 0.48, 0.10) * finW * 2.2 * (0.8 + 0.3 * shimmer) * (0.7 + 0.3 * rnd);
    return c;
}

vec3 shadeStone(vec3 p, vec3 n, float sh, float occ) {
    vec3 col = C_STONE * (0.9 + 0.12 * vnoise(p.xz * 2.0 + p.y));
    float dif = max(dot(n, KEY), 0.0) * sh;
    return col * (KEYCOL * dif * 0.85 + SKYCOL * occ * 0.75) * g_envDim;
}

vec3 shadeCeramic(vec3 p, vec3 n, vec3 rd, float sh, float occ) {
    float dif = clamp(dot(n, KEY) * 0.85 + 0.15, 0.0, 1.0) * sh;
    vec3 h = normalize(KEY - rd);
    float spe = pow(max(dot(n, h), 0.0), 60.0) * sh;
    return C_CERAMIC * (KEYCOL * dif * 0.9 + SKYCOL * occ * 0.7) + spe * 0.35;
}

vec3 shadeWood(vec3 p, vec3 n, float sh, float occ, vec3 base) {
    float g = sin(p.y * 40.0 + vnoise(p.xz * 6.0) * 4.0) * 0.5 + 0.5;
    base *= 0.85 + 0.25 * g;
    float dif = max(dot(n, KEY), 0.0) * sh;
    return base * (KEYCOL * dif * 0.9 + SKYCOL * occ * 0.7);
}

// --- scoreboard glyphs (2D, board-local: x across, y up; units ~ metres)
float sdSeg(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    return length(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0));
}
float glyph(vec2 p, float state) {
    // state 0 -> '0', 1 -> '1', 2 -> a note
    if (state < 0.5) {
        vec2 q = p / vec2(0.55, 0.85);
        return abs(length(q) - 1.0) * 0.6 - 0.11;
    } else if (state < 1.5) {
        return min(sdSeg(p, vec2(0.0, -0.85), vec2(0.0, 0.85)), sdSeg(p, vec2(0.0, 0.85), vec2(-0.32, 0.55))) - 0.13;
    }
    float head = length((p - vec2(-0.22, -0.55)) / vec2(1.25, 1.0)) - 0.27;
    float stem = sdSeg(p, vec2(0.10, -0.55), vec2(0.10, 0.85)) - 0.08;
    float flag = sdSeg(p, vec2(0.10, 0.85), vec2(0.45, 0.45)) - 0.08;
    return min(head, min(stem, flag));
}
vec3 shadeBoard(vec3 p, vec3 n, float sh, float occ) {
    vec3 rb = p - BOARD_C;
    vec3 q = vec3(dot(rb, BOARD_EX), rb.y, dot(rb, BOARD_EZ));
    vec3 col = vec3(0.045, 0.05, 0.06);
    if (q.x < -0.15) {                     // the face toward the stadium (-x)
        vec2 b = vec2(q.z, q.y);           // x across (viewer's right = +z), y up
        // two flap panels
        for (int s = 0; s < 2; s++) {
            float cy = s == 0 ? 1.6 : -1.6;
            vec2 lp = b - vec2(0.0, cy);
            float panel = sdBox2(lp, vec2(2.05, 1.45));
            vec3 pc = vec3(0.10, 0.11, 0.12);
            if (panel < 0.0) {
                float age = s == 0 ? u_board.z : u_board.w;
                float state = s == 0 ? u_board.x : u_board.y;
                // icon on the left of each panel: a square (Kaku) or a circle (Rondo)
                vec2 ip = lp - vec2(-1.05, 0.0);
                float icon = s == 0 ? sdBox2(ip, vec2(0.52, 0.52)) : length(ip) - 0.56;
                vec3 ic = s == 0 ? vec3(0.147, 0.058, 0.022) * 2.0 : vec3(0.027, 0.044, 0.076) * 2.6;
                float mark = s == 0 ? smoothstep(0.03, 0.0, abs(ip.y) - 0.07) : smoothstep(0.03, 0.0, abs(ip.x * 0.5 + ip.y * 0.86) - 0.045);
                ic = mix(ic, s == 0 ? C_BAND : C_BRASS * 1.6, mark * step(icon, 0.0));
                pc = mix(pc, ic, smoothstep(0.02, -0.02, icon));
                // the flap seam
                pc *= 1.0 - 0.5 * smoothstep(0.03, 0.0, abs(lp.y));
                float gl = glyph(lp - vec2(0.85, 0.0), state);
                vec3 gc = state > 1.5 ? vec3(1.0, 0.62, 0.15) * (1.15 + 0.25 * sin(u_time * 7.0)) : C_BAND * 0.9;
                float flip = (age >= 0.0 && age < 0.25) ? 1.0 - age / 0.25 : 0.0;
                float vis = smoothstep(0.02, -0.02, gl) * (1.0 - flip * step(abs(lp.y), flip * 1.7));
                pc = mix(pc, gc, vis);
            }
            col = mix(col, pc, step(panel, 0.0));
        }
    }
    float dif = max(dot(n, KEY), 0.0) * sh;
    return col * (0.6 + 0.5 * dif) + col * 0.4;
}

vec3 shade(vec3 p, vec3 n, vec3 rd, vec3 res, float t) {
    int m = int(res.y + 0.5);
    g_envDim = 1.0 - 0.35 * u_fin;
    float sh = softShadow(p + n * 0.01, KEY, m == 5 ? 3.0 : 14.0);
    float occ = ao(p, n);
    vec3 col;
    if (m == 1) col = shadeGround(p, n, sh, occ);
    else if (m == 2) col = shadeKaku(p, n, rd, sh, occ);
    else if (m == 3) col = shadeCloth(p, n, sh, occ);
    else if (m == 4) col = shadeRondo(p, n, rd, sh, occ);
    else if (m == 5) col = shadeFork(p, n, rd, sh, occ, floor(res.z + 0.001), fract(res.z) / 0.09);
    else if (m == 6) col = shadeStone(p, n, sh, occ);
    else if (m == 7) col = shadeCeramic(p, n, rd, sh, occ);
    else if (m == 8) col = shadeWood(p, n, sh, occ, vec3(0.30, 0.18, 0.09));
    else if (m == 9) col = shadeWood(p, n, sh, occ, vec3(0.22, 0.11, 0.05));
    else if (m == 10) col = shadeBoard(p, n, sh, occ);
    else if (m == 11) col = shadeMetal(p, n, rd, sh, occ, C_BRASS, 0.3) + C_GOLD * (u_startAge > 0.0 ? 1.2 * exp(-u_startAge / 0.5) : 0.0);
    else if (m == 12) col = shadeMetal(p, n, rd, sh, occ, C_BRASS * 0.95, 0.35);
    else if (m == 13) col = shadeMetal(p, n, rd, sh, occ, C_BRASS, 0.3);
    else col = shadeMetal(p, n, rd, sh, occ, vec3(0.08, 0.08, 0.09), 0.6);
    // aerial perspective toward the sky colour
    col = mix(col, sky(rd) * 0.85, (1.0 - exp(-0.00011 * t * t)) * (m == 10 || m == 14 ? 0.3 : 1.0));
    return col;
}

void main() {
    vec2 uv = (2.0 * gl_FragCoord.xy - u_res) / u_res.y;
    vec3 rd = normalize(u_camRot * vec3(uv * u_tanH, 1.0));
    vec3 ro = u_camPos;
    float t = 0.0;
    vec3 res = vec3(-1.0, 0.0, 0.0);
    for (int i = 0; i < 220; i++) {
        vec3 h = map(ro + rd * t);
        if (h.x < 0.0005 * t + 0.0005) { res = vec3(t, h.y, h.z); break; }
        t += h.x * 0.85;
        if (t > 90.0) break;
    }
    vec3 col;
    if (res.x < 0.0) col = sky(rd);
    else {
        vec3 p = ro + rd * res.x;
        col = shade(p, calcNormal(p, res.x), rd, res, res.x);
    }
    if (isnan(col.r + col.g + col.b) || isinf(col.r + col.g + col.b)) col = vec3(0.6);
    f_color = vec4(min(col, vec3(40.0)), 1.0);
}
#endif

#ifdef BRIGHT_PASS
uniform sampler2D u_hdr;
void main() {
    vec3 c = texture(u_hdr, v_uv).rgb;
    float l = max(c.r, max(c.g, c.b));
    f_color = vec4(c * smoothstep(1.0, 2.4, l), 1.0);
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
    col += bloom / wsum * 0.7;
    vec2 vp = v_uv - 0.5;
    col *= 1.0 - 0.45 * dot(vp, vp);
    col = aces(col * 0.82);
    col = mix(col, col * col * (3.0 - 2.0 * col), 0.25);
    col = pow(col, vec3(1.0 / 2.2));
    col = mix(col, vec3(1.0, 0.78, 0.38), 0.25 * u_impact);
    col += (hash12(gl_FragCoord.xy + fract(u_time * 7.13) * 100.0) - 0.5) / 255.0;
    f_color = vec4(col, 1.0);
}
#endif
