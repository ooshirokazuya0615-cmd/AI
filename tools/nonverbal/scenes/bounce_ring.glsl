#version 330
// bounce_ring の描画。TRAIL_PASS を定義すると残像テクスチャの更新パスになる。
//#define PASS

uniform vec2 u_res;
uniform float u_time;
in vec2 v_uv;
out vec4 f_color;

// 画面座標 → 横幅1・中央原点・上が+y の座標
vec2 world() { return (gl_FragCoord.xy - 0.5 * u_res) / u_res.x; }

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float hash11(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
}

#ifdef TRAIL_PASS
// ---------- 残像：前のフレームを少し暗くして、今のボールを重ねる ----------
uniform sampler2D u_prev;
uniform vec2 u_a, u_b;   // 前フレームと今フレームのボール位置
uniform float u_r;
uniform vec3 u_col;
uniform float u_decay;

float sdSegment(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-9), 0.0, 1.0);
    return length(pa - ba * h);
}

void main() {
    vec2 p = world();
    vec3 prev = texture(u_prev, v_uv).rgb * u_decay;
    // 中心ほど濃い、ふちのぼけた帯（彗星の尾のように見える）
    float d = sdSegment(p, u_a, u_b) / u_r;
    float m = 1.0 - smoothstep(0.0, 0.75, d);
    m *= m;
    f_color = vec4(max(prev, u_col * m), 1.0);
}

#else
// ---------- 本描画 ----------
uniform float u_aspect;
uniform vec3 u_ball;      // x, y, 半径
uniform vec3 u_ballCol;
uniform float u_ring;
uniform float u_flash;    // 直近の衝突の強さの合計
uniform vec4 u_hits[8];   // 接触点x, y, 経過秒, 何回目か（経過秒<0は未使用）
uniform vec3 u_hitCol[8];
uniform float u_intro;    // 0→1 でリングが描かれる
uniform float u_outro;    // 弾けてからの秒（<0ならまだ）
uniform float u_progress; // ボールの大きさ 0→1
uniform sampler2D u_trail;

const float PI = 3.14159265;

float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x),
               mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}

float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 3; i++) { v += a * noise(p); p = p * 2.03 + 7.1; a *= 0.5; }
    return v;
}

// 光る点
float glow(float d, float size) { return size * size / (d * d + size * size); }

vec3 aces(vec3 x) {
    return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}

void main() {
    vec2 p = world();
    float px = 1.0 / u_res.x;
    float rr = length(p);
    float ang = atan(p.y, p.x);
    float alive = u_outro < 0.0 ? 1.0 : 1.0 - smoothstep(0.0, 0.12, u_outro);

    // 背景：中心ほど少し明るい夜空と、ゆっくり流れる霧
    vec3 col = mix(vec3(0.004, 0.006, 0.022), vec3(0.026, 0.020, 0.072), exp(-rr * 2.4));
    col += u_ballCol * 0.03 * fbm(p * 2.6 + vec2(u_time * 0.025, -u_time * 0.04)) * (0.5 + u_progress);
    vec2 cell = floor(p * 90.0);
    float star = hash12(cell);
    if (star > 0.988) {
        vec2 c = (cell + 0.5 + 0.35 * (vec2(hash12(cell + 3.1), hash12(cell + 9.7)) - 0.5)) / 90.0;
        float tw = 0.5 + 0.5 * sin(u_time * (1.0 + 3.0 * hash12(cell + 1.7)) + star * 50.0);
        col += vec3(0.75, 0.8, 1.0) * glow(length(p - c), 0.0012) * 0.45 * tw;
    }

    // 残像
    col += texture(u_trail, v_uv).rgb;

    // リング内側のガラスのような面
    float inside = 1.0 - smoothstep(u_ring - px, u_ring + px, rr);
    col += u_ballCol * 0.018 * inside * u_intro * alive;

    // リング本体。最初の0.6秒で12時の位置から時計回りに描かれていく
    float sweep = fract((PI * 0.5 - ang) / (2.0 * PI));
    float drawn = 1.0 - smoothstep(u_intro - 0.03, u_intro, sweep) + step(1.0, u_intro);
    float dRing = abs(rr - u_ring - 0.004);
    vec3 ringCol = mix(vec3(1.0), u_ballCol, 0.45);
    float core = 1.0 - smoothstep(0.0025, 0.0025 + 1.5 * px, dRing);
    float halo = exp(-dRing * 55.0) * 0.22 + exp(-dRing * 260.0) * 0.5;
    col += ringCol * (core * 1.1 + halo * (1.0 + 1.6 * u_flash)) * min(drawn, 1.0) * alive;

    // 衝突エフェクト：リングの光、波紋、火花
    for (int i = 0; i < 8; i++) {
        float age = u_hits[i].z;
        if (age < 0.0 || age > 1.0) continue;
        vec2 h = u_hits[i].xy;
        vec3 hc = u_hitCol[i];
        float hitAng = atan(h.y, h.x);
        float da = abs(mod(ang - hitAng + PI, 2.0 * PI) - PI);
        col += hc * exp(-da * da * 30.0) * exp(-dRing * 120.0) * exp(-age * 7.0) * 2.2 * alive;

        float wave = abs(length(p - h) - age * 0.32) - 0.0015;
        col += hc * (1.0 - smoothstep(0.0, 2.0 * px, wave)) * pow(max(1.0 - age / 0.7, 0.0), 2.0) * 0.7 * inside;

        vec2 n = normalize(h);
        for (int k = 0; k < 9; k++) {
            float s = u_hits[i].w * 13.0 + float(k);
            float a = atan(n.y, n.x) + (hash11(s) - 0.5) * 2.4;
            float v = 0.18 + 0.32 * hash11(s + 0.5);
            float life = 0.45 + 0.4 * hash11(s + 0.9);
            if (age > life) continue;
            vec2 sp = h + vec2(cos(a), sin(a)) * v * age * (1.0 - 0.45 * age) - vec2(0.0, 0.22) * age * age;
            float fade = pow(1.0 - age / life, 1.5);
            col += mix(hc, vec3(1.0), 0.35) * glow(length(p - sp), 0.0028) * fade * 1.2;
        }
    }

    // ボール：上から光が当たった球体として塗る
    vec2 q = p - u_ball.xy;
    float r = u_ball.z * smoothstep(0.0, 1.0, u_intro);
    float d = length(q) - r;
    if (r > 0.0) {
        vec2 qn = q / r;
        vec3 n = vec3(qn, sqrt(max(1.0 - dot(qn, qn), 0.0)));
        vec3 L = normalize(vec3(-0.45, 0.65, 0.62));
        float diff = max(dot(n, L), 0.0);
        float spec = pow(max(dot(reflect(-L, n), vec3(0, 0, 1)), 0.0), 36.0);
        float rim = pow(1.0 - n.z, 2.5);
        vec3 body = u_ballCol * (0.18 + 0.85 * diff) + vec3(1.0) * spec * 0.9 + u_ballCol * rim * 0.9;
        body *= 1.0 + 0.35 * u_flash;
        float fill = 1.0 - smoothstep(-px, px, d);
        col = mix(col, body, fill * alive);
        col += u_ballCol * exp(-max(d, 0.0) * 38.0) * 0.28 * alive;
    }

    // フィナーレ：閃光と、外へ広がる衝撃波と、飛び散る光の粒
    if (u_outro >= 0.0) {
        float o = u_outro;
        col += mix(vec3(1.0), u_ballCol, 0.3) * exp(-o * 10.0) * 2.0;
        float shock = abs(rr - (u_ring + o * 1.1)) - (0.004 + o * 0.01);
        col += mix(u_ballCol, vec3(1.0), 0.5) * exp(-max(shock, 0.0) * 90.0) * exp(-o * 1.8) * 1.4;
        for (int k = 0; k < 64; k++) {
            float s = float(k) + 101.0;
            float a = hash11(s) * 2.0 * PI;
            float v = 0.12 + 0.5 * hash11(s + 0.3);
            float start = u_ring * sqrt(hash11(s + 0.6));
            vec2 sp = vec2(cos(a), sin(a)) * (start + v * (1.0 - exp(-o * 2.2)) / 2.2 * 2.0)
                    - vec2(0.0, 0.05) * o * o;
            float life = 1.4 + 1.6 * hash11(s + 0.8);
            float fade = clamp(1.0 - o / life, 0.0, 1.0);
            vec3 c = 0.5 + 0.5 * cos(2.0 * PI * (hash11(s + 0.4) * 0.6 + vec3(0.5, 0.62, 0.78)));
            col += c * glow(length(p - sp), 0.0042) * fade * fade * 1.5;
        }
        col *= 1.0 - smoothstep(2.0, 3.2, o);
    }

    // 周辺減光 → トーンマップ → 8bitの縞を消す微小ノイズ
    vec2 vp = p / vec2(0.5, 0.5 * u_aspect);
    col *= 1.0 - 0.35 * dot(vp, vp) * 0.5;
    col = aces(col * 1.1);
    col = pow(col, vec3(1.0 / 2.2));
    col += (hash12(gl_FragCoord.xy + fract(u_time * 7.13) * 100.0) - 0.5) / 255.0;
    f_color = vec4(col, 1.0);
}
#endif
