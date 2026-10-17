#version 330
// Stickman obstacle course. Flat "paper diorama" look: SDF shapes, soft drop shadows,
// ink stickman with a light sticker outline, short ghost trail, comic impact bursts.
// World units = px at 1080 width, +y up. One full-screen pass per frame.

uniform vec2 u_res;
uniform float u_time;
uniform vec3 u_cam;          // cam x, y, zoom
uniform vec4 u_seg[9];       // stickman capsules a.xy, b.xy (order: torso, uarm_n, larm_n, uarm_f, larm_f, thigh_n, shin_n, thigh_f, shin_f)
uniform vec4 u_head;         // x, y, angle, radius
uniform vec4 u_gseg[27];     // 3 ghost poses x 9 capsules
uniform vec4 u_ghead[3];     // ghost heads x, y, -, alpha
uniform vec4 u_bbox;         // stickman+ghost world bbox (minx, miny, maxx, maxy) incl. margins
uniform vec4 u_face;         // expression id, look x, look y, blink(0..1)
uniform float u_dizzy;       // 0..1 dizzy stars
uniform vec4 u_ball;         // x, y, r, angle
uniform float u_padTop;
uniform vec4 u_stair;        // x0, tread, rise, steps
uniform float u_stepHit[6];  // brightness per step (0..1)
uniform vec3 u_pegs[12];     // x, y, hit glow
uniform vec4 u_plate;        // a.xy, b.xy
uniform vec2 u_plateVib;     // amplitude (px), phase
uniform vec4 u_hits[8];      // x, y, age, strength
uniform float u_fade;        // 0..1 fade from/to paper

in vec2 v_uv;
out vec4 f_color;

const float LEDGE_X1 = -260.0;
const float PEG_R = 13.0;
const float PAD_HW = 528.0;
const float PAD_H = 26.0;
const float PAD_BASE = -1560.0;
const float FLOOR_Y = -1600.0;
const float WALL_X = 540.0;

float px;   // one screen pixel in world units

// ---------------- helpers ----------------
float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}
float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x),
               mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}
float sdSeg(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
    return length(pa - ba * h);
}
float sdBox(vec2 p, vec2 c, vec2 hs, float r) {
    vec2 d = abs(p - c) - hs + r;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - r;
}
float sdStar5(vec2 p, float r, float rf) {
    const vec2 k1 = vec2(0.809016994375, -0.587785252292);
    const vec2 k2 = vec2(-k1.x, k1.y);
    p.x = abs(p.x);
    p -= 2.0 * max(dot(k1, p), 0.0) * k1;
    p -= 2.0 * max(dot(k2, p), 0.0) * k2;
    p.x = abs(p.x);
    p.y -= r;
    vec2 ba = rf * vec2(-k1.y, k1.x) - vec2(0, 1);
    float h = clamp(dot(p, ba) / dot(ba, ba), 0.0, r);
    return length(p - ba * h) * sign(p.y * ba.x - p.x * ba.y);
}
// anti-aliased fill of an SDF
float fill(float d) { return 1.0 - smoothstep(-px, px, d); }
vec3 over(vec3 col, vec3 c, float a) { return mix(col, c, clamp(a, 0.0, 1.0)); }

// ---------------- palette ----------------
const vec3 PAPER_TOP = vec3(0.955, 0.930, 0.885);
const vec3 PAPER_BOT = vec3(0.985, 0.860, 0.780);
const vec3 INK = vec3(0.105, 0.110, 0.140);
const vec3 INK_FAR = vec3(0.300, 0.310, 0.360);
const vec3 OUTLINE = vec3(0.990, 0.975, 0.950);
const vec3 WOOD = vec3(0.800, 0.565, 0.355);
const vec3 WOOD_DK = vec3(0.620, 0.405, 0.240);
const vec3 WOOD_LT = vec3(0.925, 0.735, 0.515);
const vec3 STEEL = vec3(0.600, 0.640, 0.715);
const vec3 STEEL_DK = vec3(0.330, 0.360, 0.430);
const vec3 SLATE = vec3(0.330, 0.360, 0.430);
const vec3 WALL = vec3(0.560, 0.590, 0.660);
const vec3 RUBBER = vec3(0.945, 0.330, 0.355);
const vec3 RUBBER_LT = vec3(1.000, 0.560, 0.540);
const vec3 BALL = vec3(0.110, 0.560, 0.560);
const vec3 ACCENT = vec3(1.000, 0.700, 0.120);
const vec3 GHOST = vec3(0.420, 0.520, 1.000);

// ---------------- set SDFs ----------------
float sdLedge(vec2 p) { return sdBox(p, vec2(-830.0, -62.4), vec2(570.0, 62.4), 4.0); }
float sdStep(vec2 p, float i) {
    float x0 = u_stair.x + u_stair.y * i;
    float yt = -u_stair.z * (i + 1.0);
    float h = u_stair.z * 1.4;
    return sdBox(p, vec2(x0 + 0.5 * u_stair.y, yt - 0.5 * h), vec2(0.5 * u_stair.y + 1.0, 0.5 * h + 1.0), 4.0);
}
float sdStairs(vec2 p, out float idx) {
    // profile: step columns (tread top down to far below), cut by the stringer underside
    float x0 = u_stair.x, T = u_stair.y, R = u_stair.z;
    idx = clamp(floor((p.x - x0) / T), 0.0, 5.0);
    float d = 1e9;
    for (int i = 0; i < 6; i++) {
        float xa = x0 + T * float(i);
        float yt = -R * (float(i) + 1.0);
        d = min(d, sdBox(p, vec2(xa + 0.5 * T, yt - 400.0), vec2(0.5 * T + 0.5, 400.0), 4.0));
    }
    vec2 A = vec2(x0 - 40.0, -R * 1.6 - 10.0), B = vec2(x0 + 6.0 * T, -R * 6.0 - R * 1.4);
    vec2 n = normalize(vec2(-(B - A).y, (B - A).x));      // points up/left
    float under = -dot(p - A, n);                           // >0 below the stringer
    d = max(d, under);
    d = max(d, p.x - (x0 + 6.0 * T));
    return d;
}
vec2 plateOffset(vec2 p) {
    vec2 a = u_plate.xy, b = u_plate.zw;
    vec2 ab = b - a;
    float s = clamp(dot(p - a, ab) / dot(ab, ab), 0.0, 1.0);
    vec2 n = normalize(vec2(-ab.y, ab.x));
    return n * u_plateVib.x * sin(3.14159 * s) * sin(u_plateVib.y);
}
float sdPlate(vec2 p) {
    vec2 o = plateOffset(p);
    return sdSeg(p - o, u_plate.xy, u_plate.zw) - 9.0;
}
float sdPad(vec2 p) { return sdBox(p, vec2(0.0, u_padTop - 0.5 * PAD_H), vec2(PAD_HW, 0.5 * PAD_H), 7.0); }
float sdBase(vec2 p) { return sdBox(p, vec2(0.0, PAD_BASE - 30.0), vec2(PAD_HW + 4.0, 30.0), 4.0); }
float sdWalls(vec2 p) {
    float l = sdBox(p, vec2(-WALL_X - 400.0, (-380.0 + FLOOR_Y) * 0.5), vec2(400.0, (-380.0 - FLOOR_Y) * 0.5), 3.0);
    float r = sdBox(p, vec2(WALL_X + 400.0, (-160.0 + FLOOR_Y) * 0.5), vec2(400.0, (-160.0 - FLOOR_Y) * 0.5), 3.0);
    return min(l, r);
}
float sdCoils(vec2 p) {
    float top = u_padTop - PAD_H, bot = PAD_BASE;
    float h = max(top - bot, 4.0);
    float d = 1e9;
    for (int i = 0; i < 7; i++) {
        float x = -450.0 + 150.0 * float(i);
        vec2 q = p - vec2(x, bot);
        if (abs(q.x) > 40.0 || q.y < -6.0 || q.y > h + 6.0) continue;
        float n = 4.0;
        float t = clamp(q.y / h, 0.0, 1.0) * n;
        float tri = abs(fract(t) - 0.5) * 2.0;           // 0..1 triangle wave
        float xp = (tri - 0.5) * 2.0 * 22.0;
        float slope = 4.0 * 22.0 * n / h;                // dx/dy of the zigzag
        d = min(d, abs(q.x - xp) / sqrt(1.0 + slope * slope));
    }
    return d - 3.2;
}

// ---------------- stickman ----------------
float R_SEG(int i) { return i == 0 ? 9.5 : 7.6; }

float sdMan(vec2 p, out float dFar) {
    float dm = length(p - u_head.xy) - u_head.w;
    dm = min(dm, sdSeg(p, u_seg[0].xy, u_seg[0].zw) - 9.5);
    dm = min(dm, sdSeg(p, u_seg[1].xy, u_seg[1].zw) - 7.6);
    dm = min(dm, sdSeg(p, u_seg[2].xy, u_seg[2].zw) - 7.6);
    dm = min(dm, sdSeg(p, u_seg[5].xy, u_seg[5].zw) - 7.6);
    dm = min(dm, sdSeg(p, u_seg[6].xy, u_seg[6].zw) - 7.6);
    float df = sdSeg(p, u_seg[3].xy, u_seg[3].zw) - 7.6;
    df = min(df, sdSeg(p, u_seg[4].xy, u_seg[4].zw) - 7.6);
    df = min(df, sdSeg(p, u_seg[7].xy, u_seg[7].zw) - 7.6);
    df = min(df, sdSeg(p, u_seg[8].xy, u_seg[8].zw) - 7.6);
    dFar = df;
    return dm;
}

float sdGhost(vec2 p, int g) {
    float d = length(p - u_ghead[g].xy) - u_head.w;
    for (int i = 0; i < 9; i++) {
        vec4 s = u_gseg[g * 9 + i];
        d = min(d, sdSeg(p, s.xy, s.zw) - (i == 0 ? 9.5 : 7.6));
    }
    return d;
}

// eyes / face in head-local coords: x = towards the front, y = up
vec3 drawFace(vec3 col, vec2 p) {
    float a = u_head.z;
    vec2 up = vec2(cos(a), sin(a));
    vec2 fw = vec2(-up.y, up.x);
    vec2 q = p - u_head.xy;
    vec2 l = vec2(dot(q, fw), dot(q, up));
    if (dot(l, l) > 30.0 * 30.0) return col;
    float e = u_face.x;
    vec2 look = vec2(dot(u_face.yz, fw), dot(u_face.yz, up));
    vec2 e1 = vec2(4.0, 4.0), e2 = vec2(15.0, 4.0);
    vec3 W = vec3(0.99, 0.98, 0.96);
    if (e < 0.5) {                       // calm dots, blink squashes them
        float sy = mix(1.0, 0.12, u_face.w);
        vec2 o = look * 1.6;
        float d1 = length((l - e1 - o) * vec2(1.0, 1.0 / sy)) - 3.3;
        float d2 = length((l - e2 - o) * vec2(1.0, 1.0 / sy)) - 3.3;
        col = over(col, W, fill(min(d1, d2) * sy));
    } else if (e < 1.5) {                // surprised: big eyes + pupils + O mouth
        float d1 = length(l - e1) - 5.6, d2 = length(l - e2 - vec2(0.5, 0.0)) - 5.6;
        col = over(col, W, fill(min(d1, d2)));
        vec2 o = look * 2.4;
        float p1 = length(l - e1 - o) - 2.4, p2 = length(l - e2 - vec2(0.5, 0.0) - o) - 2.4;
        col = over(col, INK, fill(min(p1, p2)));
        float m = abs(length((l - vec2(11.0, -9.0)) * vec2(1.0, 0.8)) - 3.6) - 1.3;
        col = over(col, W, fill(m));
    } else if (e < 2.5) {                // scrunched > <
        float d = 1e9;
        d = min(d, sdSeg(l, e1 + vec2(-3.0, 3.5), e1 + vec2(2.5, 0.0)));
        d = min(d, sdSeg(l, e1 + vec2(-3.0, -3.5), e1 + vec2(2.5, 0.0)));
        d = min(d, sdSeg(l, e2 + vec2(3.0, 3.5), e2 + vec2(-2.5, 0.0)));
        d = min(d, sdSeg(l, e2 + vec2(3.0, -3.5), e2 + vec2(-2.5, 0.0)));
        col = over(col, W, fill(d - 1.5));
    } else {                             // dizzy X X
        float d = 1e9;
        for (int k = 0; k < 2; k++) {
            vec2 c = k == 0 ? e1 : e2;
            d = min(d, sdSeg(l, c + vec2(-3.4, -3.4), c + vec2(3.4, 3.4)));
            d = min(d, sdSeg(l, c + vec2(-3.4, 3.4), c + vec2(3.4, -3.4)));
        }
        col = over(col, W, fill(d - 1.45));
        float m = sdSeg(l, vec2(7.0, -9.0), vec2(14.0, -8.0));   // little flat mouth
        col = over(col, W, fill(m - 1.2));
    }
    return col;
}

// ---------------- background ----------------
vec3 paper(vec2 p, vec2 sp) {
    float g = clamp((p.y + 1500.0) / -1900.0 + 1.0, 0.0, 1.0);   // 1 at top, 0 at bottom
    vec3 col = mix(PAPER_BOT, PAPER_TOP, smoothstep(0.0, 1.0, g));
    // parallax dot grid: scrolls at 55% of the camera
    vec2 pp = u_cam.xy * 0.45 + (p - u_cam.xy);
    vec2 cell = pp / 54.0;
    vec2 f = fract(cell) - 0.5;
    float dot_ = length(f) * 54.0 - 2.1;
    col = over(col, col * 0.90, fill(dot_ * 0.6) * 0.55);
    // big soft circles far behind (parallax 25%)
    vec2 qq = u_cam.xy * 0.75 + (p - u_cam.xy);
    float c1 = length(qq - vec2(-260.0, 120.0)) - 330.0;
    float c2 = length(qq - vec2(330.0, -700.0)) - 260.0;
    float c3 = length(qq - vec2(-300.0, -1250.0)) - 300.0;
    col = mix(col, col * vec3(1.0, 0.975, 0.95), (1.0 - smoothstep(-2.0, 2.0, min(c1, min(c2, c3)))) * 0.45);
    // paper grain
    col *= 0.985 + 0.03 * vnoise(sp * 0.9);
    return col;
}

float shadowOf(float d, float blur) { return 1.0 - smoothstep(-blur, blur, d); }

void main() {
    float scale = u_res.x / 1080.0 * u_cam.z;
    px = 1.0 / scale;
    vec2 sp = gl_FragCoord.xy;
    vec2 p = u_cam.xy + (sp - 0.5 * u_res) / scale;
    vec2 SO = vec2(9.0, -12.0);        // drop-shadow offset (light from upper left)

    vec3 col = paper(p, sp);

    // ---- set shadows onto paper ----
    float idx;
    vec2 ps = p - SO;
    float dSetSh = min(sdLedge(ps), sdStairs(ps, idx));
    dSetSh = min(dSetSh, sdPlate(ps));
    dSetSh = min(dSetSh, sdWalls(ps));
    dSetSh = min(dSetSh, sdPad(ps));
    for (int i = 0; i < 12; i++) dSetSh = min(dSetSh, length(ps - u_pegs[i].xy) - PEG_R - 5.0);
    float ballSh = length(ps - u_ball.xy) - u_ball.z;
    col *= 1.0 - 0.16 * shadowOf(min(dSetSh, ballSh), 9.0);

    // ---- walls ----
    float dw = sdWalls(p);
    vec3 wc = WALL * (0.97 + 0.05 * step(0.5, fract(p.y / 120.0)));
    col = over(col, WALL * 0.80, fill(dw));
    col = over(col, wc, fill(dw + 5.0));

    // ---- ledge + stairs (wood) ----
    float dl = sdLedge(p);
    float ds = sdStairs(p, idx);
    float dwood = min(dl, ds);
    if (dwood < 2.0 * px + 2.0) {
        float top = 0.0;
        float glow = 0.0;
        if (ds < dl) {
            top = -u_stair.z * (idx + 1.0);
            for (int i = 0; i < 6; i++) if (float(i) == idx) glow = u_stepHit[i];
        }
        float alt = (ds < dl) ? mod(idx, 2.0) : 0.0;   // alternate step shade so each step reads
        float depth = top - p.y;                                  // distance below the tread
        float grain = vnoise(vec2(p.x * 0.012, p.y * 0.22)) * 0.5 + vnoise(vec2(p.x * 0.03, p.y * 0.6)) * 0.5;
        vec3 w = mix(WOOD, WOOD_DK, smoothstep(10.0, 110.0, depth) * 0.55);
        w *= 0.93 + 0.12 * grain;
        w *= 1.0 - 0.045 * alt;
        // soft riser shadow just under each tread edge
        if (ds < dl) {
            float xr = u_stair.x + u_stair.y * idx;          // riser line of this step
            w *= 1.0 - 0.10 * (1.0 - smoothstep(0.0, 14.0, p.x - xr)) * step(idx, 5.5) * step(0.5, idx + 1.0);
        }
        w = mix(w, WOOD_LT, (1.0 - smoothstep(5.0, 8.0, depth)) * 0.9);   // bright nosing
        w = mix(w, w * 0.78, smoothstep(-6.0, -1.0, dwood) * 0.6);         // darker rim
        w += glow * vec3(0.20, 0.13, 0.05);
        col = over(col, w, fill(dwood));
    }

    // ---- plate (steel) ----
    float dp = sdPlate(p);
    if (dp < 4.0) {
        vec2 ab = normalize(u_plate.zw - u_plate.xy);
        vec2 n = vec2(-ab.y, ab.x);
        float side = dot(p - plateOffset(p) - u_plate.xy, n);
        vec3 c = mix(STEEL_DK, STEEL, smoothstep(-9.0, 6.0, side));
        c = mix(c, vec3(0.93, 0.95, 1.0), (1.0 - smoothstep(3.5, 6.0, abs(side - 4.0))) * 0.7);
        c += abs(u_plateVib.x) * 0.02 * vec3(1.0, 0.9, 0.6);
        col = over(col, c, fill(dp));
    }

    // ---- pegs (steel) ----
    for (int i = 0; i < 12; i++) {
        vec2 q = p - u_pegs[i].xy;
        if (abs(q.x) > 60.0 || abs(q.y) > 60.0) continue;
        float r = length(q);
        float g = u_pegs[i].z;
        // hit ring
        col = over(col, ACCENT, (1.0 - smoothstep(0.0, 2.0 * px, abs(r - PEG_R - 6.0 - 28.0 * (1.0 - g)) - 1.4)) * g * g);
        float d = r - PEG_R;
        vec3 c = mix(STEEL_DK, STEEL, smoothstep(-PEG_R, PEG_R * 0.6, dot(q, vec2(-0.6, 0.8))));
        c = mix(c, vec3(1.0), (1.0 - smoothstep(0.0, 4.0, length(q - vec2(-4.0, 5.0)))) * 0.85);
        c = mix(c, c * 0.55, smoothstep(-3.0, -0.5, d));
        c = mix(c, vec3(1.0, 0.92, 0.7), g * 0.45);
        col = over(col, c, fill(d));
    }

    // ---- trampoline: base, coils, rubber bed ----
    float db = sdBase(p);
    col = over(col, SLATE * 1.15, fill(db));
    float dc = sdCoils(p);
    col = over(col, STEEL_DK, fill(dc));
    col = over(col, STEEL, fill(dc + 1.4) * 0.6);
    float dpad = sdPad(p);
    if (dpad < 4.0) {
        float fromTop = u_padTop - p.y;
        vec3 c = mix(RUBBER_LT, RUBBER, smoothstep(3.0, 9.0, fromTop));
        c = mix(c, RUBBER * 0.75, smoothstep(16.0, 26.0, fromTop));
        col = over(col, c, fill(dpad));
    }
    // floor under everything
    col = over(col, WALL * 0.78, fill(p.y - FLOOR_Y));
    col = over(col, WALL * 0.92, fill(p.y - FLOOR_Y + 6.0) * (1.0 - fill(p.y - FLOOR_Y + 12.0)));

    // ---- ball ----
    vec2 qb = p - u_ball.xy;
    float dball = length(qb) - u_ball.z;
    if (dball < 4.0) {
        vec2 n2 = qb / u_ball.z;
        vec3 n = vec3(n2, sqrt(max(1.0 - dot(n2, n2), 0.0)));
        float lit = max(dot(n, normalize(vec3(-0.5, 0.6, 0.65))), 0.0);
        vec3 c = BALL * (0.45 + 0.7 * lit);
        c += vec3(1.0) * pow(max(dot(reflect(-normalize(vec3(-0.5, 0.6, 0.65)), n), vec3(0, 0, 1)), 0.0), 30.0) * 0.6;
        float ca = cos(u_ball.w), sa = sin(u_ball.w);
        vec2 lq = mat2(ca, -sa, sa, ca) * qb;
        float holes = min(length(lq - vec2(9.0, 10.0)) - 3.6, min(length(lq - vec2(-2.0, 13.0)) - 3.6, length(lq - vec2(3.0, -2.0)) - 4.3));
        c = over(c, BALL * 0.18, fill(holes));
        col = over(col, c, fill(dball));
    }

    // ---- stickman (only inside its bbox) ----
    if (p.x > u_bbox.x && p.y > u_bbox.y && p.x < u_bbox.z && p.y < u_bbox.w) {
        float dFar, dFarS;
        float dMan = sdMan(p, dFar);
        float dManS = sdMan(p - SO, dFarS);
        // man's shadow lands on set and paper
        col *= 1.0 - 0.20 * shadowOf(min(dManS, dFarS), 8.0);
        // ghost trail
        for (int g = 0; g < 3; g++) {
            float ga = u_ghead[g].w;
            if (ga < 0.01) continue;
            float dg = sdGhost(p, g);
            col = over(col, mix(col, GHOST, 0.85), fill(dg) * ga);
        }
        // far limbs, then main body with a sticker outline
        col = over(col, OUTLINE, fill(dFar - 2.6));
        col = over(col, INK_FAR, fill(dFar));
        col = over(col, OUTLINE, fill(dMan - 2.6));
        col = over(col, INK, fill(dMan));
        col = drawFace(col, p);
    }

    // ---- dizzy stars ----
    if (u_dizzy > 0.0) {
        vec2 hc = u_head.xy + vec2(0.0, 40.0);
        for (int k = 0; k < 3; k++) {
            float a = u_time * 4.2 + float(k) * 2.0944;
            vec2 c = hc + vec2(cos(a) * 44.0, sin(a) * 12.0);
            float s = 11.0 * u_dizzy * (0.8 + 0.25 * sin(a));
            vec2 q = p - c;
            float rot = u_time * 3.0 + float(k);
            q = mat2(cos(rot), -sin(rot), sin(rot), cos(rot)) * q;
            float d = sdStar5(q, s, 0.45);
            col = over(col, INK, fill(d - 2.0) * u_dizzy);
            col = over(col, ACCENT, fill(d) * u_dizzy);
        }
    }

    // ---- comic impact bursts ----
    for (int i = 0; i < 8; i++) {
        float age = u_hits[i].z;
        if (age < 0.0 || age > 0.3) continue;
        vec2 q = p - u_hits[i].xy;
        float r = length(q);
        float s = u_hits[i].w;
        if (r > 120.0) continue;
        float life = age / 0.3;
        float r0 = 20.0 + 70.0 * s * pow(life, 0.6);
        float r1 = r0 + (14.0 + 26.0 * s) * (1.0 - life);
        float ang = atan(q.y, q.x);
        float seed = u_hits[i].x * 0.37 + u_hits[i].y * 0.11;
        float k = 7.0;
        float sector = floor((ang / 6.28318 + 0.5) * k + fract(seed));
        float a0 = (sector + 0.5 - fract(seed)) / k * 6.28318 - 3.14159;
        vec2 dir = vec2(cos(a0), sin(a0));
        float d = sdSeg(q, dir * r0, dir * r1) - (2.6 * (1.0 - life) + 0.6);
        col = over(col, INK, fill(d - 1.5) * (1.0 - life));
        col = over(col, ACCENT, fill(d) * (1.0 - life));
        // quick white pop
        col = over(col, vec3(1.0), fill(r - (10.0 + 30.0 * s) * (0.3 + life)) * (1.0 - smoothstep(0.0, 0.25, life)) * 0.55);
    }

    // vignette, fade, dither
    vec2 v = (sp / u_res - 0.5) * vec2(1.0, u_res.y / u_res.x);
    col *= 1.0 - 0.22 * dot(v, v);
    col = mix(PAPER_TOP, col, u_fade);
    col += (hash12(sp + fract(u_time * 7.13) * 100.0) - 0.5) / 255.0;
    f_color = vec4(col, 1.0);
}
