"""RISO DUSK ROOFTOP - BRIMFUL still.
Builds still.html: two grayscale density plates (pink, blue) drawn with canvas 2D,
converted to AM halftone in JS and multiplied onto paper. Usage: python3 make.py [out.html]"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from pose2d import POSE, GROUND_Y  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'still.html')

# ---------------------------------------------------------------- parameters
P = dict(
    seed=7,
    cell=8, ang_pink=15, ang_blue=45, solid=0.92, kdot=0.71,
    misreg=[3, -2], starve=[0.82, 1.0], starve_freq=0.004, dropout=0.04,
    paper=[243, 238, 228], pink=[255, 79, 163], blue=[59, 91, 165],
    tooth=0.05, vignette=0.06,
    hero_dx=-70, hero_dy=0,
    stroke=24, cup_scale=1.2,
    # hero joints (spec coordinates, before hero_dx shift)
    hip=[540, 1040], neck=[548, 736], sh_l=[562, 752], sh_r=[534, 752],
    el_l=[636, 856], ha_l=[752, 806],
    el_r=[494, 872], ha_r=[512, 978],
    kn_l=[612, 1296], ft_l=[648, 1552], toe_l=[688, 1556],
    kn_r=[488, 1296], ft_r=[442, 1552], toe_r=[480, 1556],
    head=dict(cx=556, cy=622, w=124, h=60, rot=-14),
    hat=dict(dx=-4, dy=-44, rx=96, ry=15),
    sun=dict(x=184, y=968, r=140),
    tank=dict(x0=812, x1=1066, top=560, bot=905, legs_to=1262),
    mookA=dict(bx=1062, by=1560, h=1010, lean=-8, hand_gap=20),
    mookB=dict(bx=1092, by=1546, s=0.97),
    mookC=dict(bx=868, by=1300, s=0.45, flip=40),
    shadow=dict(kx=0.78, ky=0.11),
)

P['ground'] = GROUND_Y
P['pose_ref'] = POSE  # recorded for provenance; the hero uses the re-proportioned joints above

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><title>riso dusk</title>
<style>html,body{margin:0;padding:0;background:#F3EEE4}canvas{display:block}</style></head>
<body><canvas id="out" width="1080" height="1920"></canvas>
<script>
const PR = __PARAMS__;
const W = 1080, H = 1920, D2R = Math.PI / 180;
let _s = PR.seed * 9301 + 49297;
function rnd() { _s = (Math.imul(_s, 1664525) + 1013904223) >>> 0; return _s / 4294967296; }
function rr(a, b) { return a + (b - a) * rnd(); }
function hash(a, b, s) {
  let h = Math.imul(a, 374761393) ^ Math.imul(b, 668265263) ^ Math.imul(s, 1442695041);
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16; return (h >>> 0) / 4294967296;
}
// ------------------------------------------------------------- plates
function mk() { const c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, W, H); return x; }
const PK = mk(), BL = mk();
const g = d => { const v = Math.round(255 * (1 - Math.max(0, Math.min(1, d)))); return `rgb(${v},${v},${v})`; };
const both = f => { f(PK); f(BL); };
const save = () => both(c => c.save()), restore = () => both(c => c.restore());
function fill(path, pd, bd) {
  if (pd != null) { PK.fillStyle = g(pd); PK.fill(path); }
  if (bd != null) { BL.fillStyle = g(bd); BL.fill(path); }
}
function stk(path, w, pd, bd, cap = 'round', dash = null) {
  for (const [c, d] of [[PK, pd], [BL, bd]]) {
    if (d == null) continue;
    c.lineWidth = w; c.lineCap = cap; c.lineJoin = 'round'; c.strokeStyle = g(d);
    c.setLineDash(dash || []); c.stroke(path); c.setLineDash([]);
  }
}
function poly(pts, close = true) { const p = new Path2D(); p.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) p.lineTo(pts[i][0], pts[i][1]); if (close) p.closePath(); return p; }
const line = pts => poly(pts, false);
function rect(x, y, w, h) { const p = new Path2D(); p.rect(x, y, w, h); return p; }
function rrect(x, y, w, h, r) { const p = new Path2D(); p.roundRect(x, y, w, h, r); return p; }
function ell(cx, cy, rx, ry, rot = 0) { const p = new Path2D(); p.ellipse(cx, cy, rx, ry, rot, 0, Math.PI * 2); return p; }
function clipBoth(path) { both(c => c.clip(path)); }

// ------------------------------------------------------------- 1. sky
for (let y = 0; y < 1400; y++) {
  const b = y < 1150 ? 0.75 * (1 - y / 1150) : 0;
  const p = y < 450 ? 0 : y < 1150 ? 0.95 * (y - 450) / 700 : 0.95;
  PK.fillStyle = g(p); PK.fillRect(0, y, W, 1);
  BL.fillStyle = g(b); BL.fillRect(0, y, W, 1);
}
// sun glow: lighten both plates around the disc (screen with gray = multiply density)
const S = PR.sun;
both(c => {
  c.save(); c.globalCompositeOperation = 'screen';
  const gr = c.createRadialGradient(S.x, S.y, S.r * 0.9, S.x, S.y, S.r * 2.3);
  gr.addColorStop(0, 'rgb(185,185,185)'); gr.addColorStop(0.3, 'rgb(95,95,95)'); gr.addColorStop(1, 'rgb(0,0,0)');
  c.fillStyle = gr; c.fillRect(0, 500, W, 900); c.restore();
});
// faint rays from the low sun
both(c => {
  c.save(); c.globalCompositeOperation = 'screen';
  for (const [a, w, k] of [[-58, 5, 80], [-40, 3, 64], [-22, 6, 86], [-8, 2.6, 56], [-124, 4, 50]]) {
    const a0 = (a - w / 2) * D2R, a1 = (a + w / 2) * D2R, R = 1500;
    const gr = c.createRadialGradient(S.x, S.y, S.r, S.x, S.y, R * 0.7);
    gr.addColorStop(0, `rgb(${k},${k},${k})`); gr.addColorStop(1, 'rgb(0,0,0)');
    c.fillStyle = gr; c.beginPath(); c.moveTo(S.x, S.y);
    c.lineTo(S.x + R * Math.cos(a0), S.y + R * Math.sin(a0)); c.lineTo(S.x + R * Math.cos(a1), S.y + R * Math.sin(a1));
    c.closePath(); c.fill();
  }
  c.restore();
});
// long cloud streaks, lit pink from below (tapered lenses)
function lens(x0, y, w, t, sk = 0.35) {
  const p = new Path2D(); p.moveTo(x0, y);
  p.bezierCurveTo(x0 + w * sk, y - t * 1.3, x0 + w * 0.8, y - t * 0.9, x0 + w, y);
  p.bezierCurveTo(x0 + w * 0.75, y + t * 0.35, x0 + w * 0.25, y + t * 0.45, x0, y); p.closePath(); return p;
}
function cloud(x0, y, w, t, bumps) {
  const p = new Path2D(); p.moveTo(x0, y);
  let x = x0;
  for (let i = 0; i < bumps.length; i++) {
    const bw = w * bumps[i][0], bh = t * bumps[i][1];
    p.bezierCurveTo(x + bw * 0.05, y - bh * 1.25, x + bw * 0.95, y - bh * 1.25, x + bw, y - (i < bumps.length - 1 ? t * 0.25 : 0));
    x += bw;
  }
  p.lineTo(x0, y); p.closePath(); return p;
}
for (const [x0, y, w, t, b] of [
    [-40, 352, 520, 30, [[0.22, 0.5], [0.3, 1.0], [0.2, 0.7], [0.28, 0.35]]],
    [610, 404, 520, 26, [[0.25, 0.4], [0.35, 0.9], [0.4, 0.45]]],
    [150, 466, 380, 20, [[0.3, 0.6], [0.4, 1.0], [0.3, 0.4]]]]) {
  fill(cloud(x0, y, w, t, b), 0.58, 0.14);
  fill(lens(x0 + w * 0.1, y + 7, w * 0.8, 5, 0.5), 0.3, 0.45);   // cool shadowed underside wisp
}
// first stars
for (const [sx, sy, r] of [[118, 150, 9], [846, 96, 7], [600, 214, 6], [962, 262, 8], [330, 286, 5]]) {
  const p = poly([[sx, sy - r], [sx + r * 0.22, sy - r * 0.22], [sx + r, sy], [sx + r * 0.22, sy + r * 0.22], [sx, sy + r], [sx - r * 0.22, sy + r * 0.22], [sx - r, sy], [sx - r * 0.22, sy - r * 0.22]]);
  fill(p, 0, 0);
}
// a few far birds
for (const [bx, by, s] of [[150, 372, 1], [212, 410, 0.8], [118, 436, 0.65]]) {
  const p = new Path2D(); p.moveTo(bx - 16 * s, by - 4 * s); p.quadraticCurveTo(bx - 7 * s, by - 9 * s, bx, by);
  p.quadraticCurveTo(bx + 7 * s, by - 9 * s, bx + 16 * s, by - 4 * s);
  stk(p, 3.2, null, 1);
}
// ------------------------------------------------------------- 2. sun
fill(ell(S.x, S.y, S.r, S.r), 0, 0);
for (const [y, x0, x1, t] of [[948, -10, 290, 12], [994, 120, 360, 10]]) {
  fill(lens(x0, y + t * 0.3, x1 - x0, t, 0.5), null, 0.6);
}
// ------------------------------------------------------------- 3. far skyline
{
  let x = -10;
  const lit = [], far = [];
  while (x < W) {
    const w = rr(46, 112);
    const nearSun = Math.abs(x + w / 2 - S.x) < S.r + 30;
    const top = nearSun ? rr(1040, 1084) : rr(975, 1150);
    const b = rect(x, top, w + 1, 1320 - top); far.push(b);
    fill(b, null, 0.45);
    if (!nearSun && rnd() < 0.6) lit.push([x + rr(8, w - 20), top + rr(14, Math.min(120, 1220 - top - 20))]);
    if (!nearSun && rnd() < 0.3) { const h = rect(x + w * 0.3, top - 14, w * 0.35, 14); fill(h, null, 0.45); }
    x += w + rr(-6, 4);
  }
  // in front of the sun disc the far blocks read as a soft violet haze
  save(); clipBoth(ell(S.x, S.y, S.r + 1, S.r + 1));
  for (const b of far) fill(b, 0.38, null);
  restore();
  // distant spire with a pink warning light
  fill(poly([[658, 1100], [672, 1100], [667, 935], [663, 935]]), null, 0.45);
  fill(ell(665, 928, 5, 5), 1, 0);
  for (const [lx, ly] of lit) { if (ly < 1235) fill(rect(lx, ly, 12, 16), 1, 0); }
}
// ------------------------------------------------------------- 4. mid skyline
{
  const blds = [[-10, 1150, 120], [100, 1232, 150], [240, 1226, 120], [350, 1206, 110], [450, 1120, 130],
                [570, 1180, 95], [655, 1090, 120], [770, 1150, 120], [880, 1106, 120], [990, 1170, 110]];
  for (const [x0, top, w] of blds) {
    fill(rect(x0, top, w, 1330 - top), 0.85, 0.8);
  }
  // antennas
  for (const [ax, top, h] of [[40, 1150, 70], [505, 1120, 95], [700, 1090, 60], [935, 1106, 80]]) {
    stk(line([[ax, top], [ax, top - h]]), 3, null, 1, 'butt');
    stk(line([[ax - 14, top - h * 0.6], [ax + 14, top - h * 0.6]]), 2.5, null, 1, 'butt');
  }
  // small water tower on the 655 building
  fill(rect(682, 1036, 46, 40), null, 1);
  fill(poly([[678, 1038], [732, 1038], [705, 1016]]), null, 1);
  for (const lx of [686, 722]) stk(line([[lx, 1074], [lx, 1092]]), 3, null, 1, 'butt');
}
// ------------------------------------------------------------- 5. laundry
{
  const L0 = [0, 642], LC = [204, 652], L1 = [408, 618];
  const lineY = x => { const t = x / 408; return (1 - t) * (1 - t) * L0[1] + 2 * t * (1 - t) * LC[1] + t * t * L1[1]; };
  const lp = new Path2D(); lp.moveTo(...L0); lp.quadraticCurveTo(...LC, ...L1);
  stk(lp, 3, null, 1);
  stk(line([[408, 610], [408, 1300]]), 6, null, 1, 'butt');
  stk(line([[392, 618], [424, 618]]), 5, null, 1, 'butt');
  function sheet(x0, x1, h, sway, pd, bd, outline) {
    const y0 = lineY(x0), y1 = lineY(x1);
    const p = new Path2D();
    p.moveTo(x0, y0);
    p.lineTo(x1, y1);
    p.bezierCurveTo(x1 + sway * 0.5, y1 + h * 0.4, x1 + sway, y1 + h * 0.7, x1 + sway * 0.9, y1 + h);
    // wavy hem
    const n = 3, hx0 = x0 + sway * 0.6, hx1 = x1 + sway * 0.9;
    for (let i = n - 1; i >= 0; i--) {
      const xa = hx0 + (hx1 - hx0) * i / n, xm = hx0 + (hx1 - hx0) * (i + 0.5) / n;
      const ya = y0 + h * 0.97 + (i % 2 ? 10 : -6);
      p.quadraticCurveTo(xm, ya + 16, xa, ya);
    }
    p.bezierCurveTo(x0 + sway * 0.5, y0 + h * 0.7, x0 + sway * 0.3, y0 + h * 0.35, x0, y0);
    p.closePath();
    fill(p, pd, bd);
    if (outline) stk(p, 4, 0, 1);
    // pegs
    for (const px of [x0 + 6, x1 - 6]) fill(rect(px - 3, lineY(px) - 8, 7, 16), null, 1);
  }
  sheet(14, 140, 112, 14, 0, 0, true);      // paper sheet with blue outline
  sheet(160, 316, 150, 22, 0.4, 0, false);  // pink sheet
  sheet(334, 390, 84, 10, 1, 0, false);     // pink towel
}
// ------------------------------------------------------------- 6. water tank
{
  const T = PR.tank, x0 = T.x0, x1 = T.x1, cx = (x0 + x1) / 2, top = T.top, bot = T.bot, lg = T.legs_to;
  // stilts and braces
  const legs = [[x0 + 18, x0], [x1 - 18, x1], [x0 + 84, x0 + 78], [x1 - 84, x1 - 78]];
  for (const [a, b] of legs) stk(line([[a, bot + 10], [b, lg]]), 11, 0, 1, 'butt');
  const nb = 3, bh = (lg - bot - 20) / nb;
  for (let i = 0; i < nb; i++) {
    const ya = bot + 20 + i * bh, yb = ya + bh;
    for (const [xa, xb] of [[x0 + 10, x0 + 80], [x1 - 80, x1 - 10]]) {
      stk(line([[xa, ya], [xb, yb]]), 4, 0, 1, 'butt'); stk(line([[xb, ya], [xa, yb]]), 4, 0, 1, 'butt');
    }
    stk(line([[x0 + 4, yb], [x1 - 4, yb]]), 5, 0, 1, 'butt');
  }
  // body (slightly tapered barrel)
  const body = new Path2D(); body.moveTo(x0 + 4, top); body.lineTo(x1 - 4, top); body.lineTo(x1, bot - 20);
  body.quadraticCurveTo(cx, bot + 14, x0, bot - 20); body.closePath();
  fill(body, 0, 1);
  // conical lid + finial
  fill(poly([[x0 - 20, top + 8], [x1 + 20, top + 8], [cx + 4, top - 46]]), 0, 1);
  fill(rect(cx - 2, top - 64, 12, 20), 0, 1); fill(ell(cx + 4, top - 66, 9, 6), 0, 1);
  // hoops (lighter dotted bands)
  for (const f of [0.12, 0.34, 0.56, 0.78]) {
    const hy = top + (bot - top) * f;
    const hp = new Path2D(); hp.moveTo(x0 + 2, hy); hp.quadraticCurveTo(cx, hy + 16, x1 - 2, hy);
    stk(hp, 4, null, 0.55, 'butt');
  }
  // sun rim light on the sun-facing left edge
  fill(poly([[x0 + 4, top + 6], [x0 + 12, top + 6], [x0 + 8, bot - 18], [x0, bot - 20]]), 1, 0);
  fill(poly([[x0 - 20, top + 7], [cx + 4, top - 46], [cx + 6, top - 39], [x0 - 6, top + 7]]), 1, 0);
  stk(line([[x0 + 1, bot + 12], [x0 - 17, lg]]), 4, 1, 0, 'butt');
}
// ------------------------------------------------------------- 7. parapet
fill(rect(0, 1300, W, 90), 0.2, 0.3);
for (let x = 120; x < W; x += 190) stk(line([[x, 1310], [x, 1390]]), 2.5, null, 0.7, 'butt');
fill(rect(0, 1306, W, 4), null, 0.75);
fill(rect(0, 1298, W, 8), 1, 0);
// ------------------------------------------------------------- 8. roof floor
for (let y = 1390; y < 1920; y++) {   // pale mauve, a touch deeper toward the viewer
  const t = (y - 1390) / 530, e = t * t;
  PK.fillStyle = g(0.22 + 0.06 * e); PK.fillRect(0, y, W, 1);
  BL.fillStyle = g(0.12 + 0.13 * e); BL.fillRect(0, y, W, 1);
}
save(); clipBoth(rect(0, 1390, W, 530));
// shadow band under the parapet (sun behind it)
fill(poly([[0, 1390], [W, 1390], [W, 1408], [0, 1432]]), null, 0.45);
// tar seams converging to (540,1000)
for (const bx of [-1400, -650, -180, 230, 640, 1040, 1500, 2300]) {
  stk(line([[540, 1000], [bx, 1920]]), 3, null, 1, 'butt');
}
for (const sy of [1478, 1650]) stk(line([[0, sy], [W, sy]]), 2.5, null, 0.75, 'butt');
restore();

// ------------------------------------------------------------- shadows (projected on roof plane)
const SH = PR.shadow;
function proj(pt, gy) { const h = gy - pt[1]; return [pt[0] + h * SH.kx, gy + h * SH.ky]; }
save(); clipBoth(rect(0, 1393, W, 527));
{
  const gy = 1560;
  const HXs = PR.hero_dx;
  const J = k => { const p = PR[k]; return proj([p[0] + HXs, p[1]], gy); };
  // hero shadow: projected stick figure
  const sw = 20;
  stk(line([J('ft_r'), J('kn_r'), J('hip'), J('kn_l'), J('ft_l')]), sw, null, 0.45);
  stk(line([J('hip'), J('neck')]), sw, null, 0.45);
  stk(line([J('sh_l'), J('el_l'), J('ha_l')]), sw, null, 0.45);
  const hc = proj([PR.head.cx + HXs, PR.head.cy], gy);
  fill(ell(hc[0], hc[1], 62 * 1.15, 22, 0.05), null, 0.45);
  const ap = [[488, 990], [600, 990], [668, 1400], [430, 1400]].map(p => proj([p[0] + HXs, p[1]], gy));
  fill(poly(ap), null, 0.45);
  // tea stand shadow (box projected)
  const st = [[30, 1560], [300, 1560], [300, 1150], [30, 1150]].map(p => proj(p, gy));
  fill(poly([[30, 1560], [300, 1560], st[2], st[3]]), null, 0.45);
  // mook shadows: tall slabs projected
  for (const [bx, w, h] of [[PR.mookA.bx, 120, 900], [PR.mookB.bx, 120, 870]]) {
    const a = [bx - w / 2, gy], b = [bx + w / 2, gy];
    const ta = proj([bx - w / 2 - 0.14 * h, gy - h], gy), tb = proj([bx + w / 2 - 0.14 * h, gy - h], gy);
    fill(poly([a, b, tb, ta]), null, 0.45);
  }
}
restore();

// ------------------------------------------------------------- 9. tea stand
{
  // wheels
  for (const wx of [82, 248]) { fill(ell(wx, 1528, 30, 30), 0, 1); fill(ell(wx, 1528, 9, 9), 0, 0); }
  // cart body
  fill(rrect(26, 1352, 278, 168, 8), 0, 1);
  // pink sign with knocked-out cup icon
  fill(rrect(104, 1392, 120, 92, 10), 1, 0);
  {
    const cx = 160, cy = 1446;
    const cup = new Path2D(); cup.moveTo(cx - 26, cy - 20); cup.lineTo(cx + 26, cy - 20); cup.lineTo(cx + 18, cy + 16);
    cup.quadraticCurveTo(cx, cy + 22, cx - 18, cy + 16); cup.closePath();
    fill(cup, 0, 0);
    const hdl = new Path2D(); hdl.arc(cx + 28, cy - 4, 10, -Math.PI / 2, Math.PI / 2); stk(hdl, 6, 0, 0, 'butt');
    for (const sx of [-12, 2, 16]) {
      const s = new Path2D(); s.moveTo(cx + sx - 4, cy - 28); s.bezierCurveTo(cx + sx + 6, cy - 36, cx + sx - 8, cy - 42, cx + sx + 2, cy - 50);
      stk(s, 4.5, 0, 0);
    }
  }
  // counter slab
  fill(rrect(14, 1330, 304, 24, 4), 0, 1);
  // poles
  for (const px of [44, 284]) fill(rect(px - 5, 1210, 10, 122), 0, 1);
  // stacked paper cups (nested tower)
  for (let i = 0; i < 3; i++) {
    const y = 1330 - 30 - i * 16, cx = 82;
    const cp = poly([[cx - 22, y], [cx + 22, y], [cx + 16, y + 30], [cx - 16, y + 30]]);
    fill(cp, 0, 0); stk(cp, 2.5, 0, 1);
    fill(rect(cx - 23, y - 1, 46, 6), 0, 1);
  }
  // kettle
  {
    const kx = 210, ky = 1330;
    const kb = new Path2D(); kb.moveTo(kx - 40, ky); kb.bezierCurveTo(kx - 46, ky - 52, kx + 46, ky - 52, kx + 40, ky); kb.closePath();
    fill(kb, 0, 1);
    const sp = new Path2D(); sp.moveTo(kx + 30, ky - 22); sp.quadraticCurveTo(kx + 58, ky - 26, kx + 66, ky - 52); stk(sp, 9, 0, 1);
    const hd = new Path2D(); hd.moveTo(kx - 26, ky - 36); hd.bezierCurveTo(kx - 24, ky - 78, kx + 24, ky - 78, kx + 26, ky - 36); stk(hd, 6, 0, 1);
    fill(ell(kx, ky - 40, 9, 5), 0, 1);
    // pink glint
    const gl = new Path2D(); gl.moveTo(kx - 28, ky - 10); gl.quadraticCurveTo(kx - 30, ky - 28, kx - 16, ky - 36); stk(gl, 4, 1, 0);
  }
  // awning: 6 stripes pink / paper with scalloped hem
  {
    const ax0 = 22, ax1 = 310, top = 1150, bot = 1214, n = 6, sw = (ax1 - ax0) / n;
    for (let i = 0; i < n; i++) {
      const xa = ax0 + i * sw, xb = xa + sw;
      const p = new Path2D(); p.moveTo(xa + 8 - i * 0, top); p.lineTo(xb + 0, top);
      p.lineTo(xb + 6 * (i / n), bot); p.quadraticCurveTo((xa + xb) / 2, bot + 26, xa + 6 * ((i) / n) - 0, bot); p.closePath();
      fill(p, i % 2 ? 0 : 1, 0);
      stk(p, 3, 0, 1);
    }
    fill(rrect(ax0 - 4, top - 10, ax1 - ax0 + 12, 14, 6), 0, 1);
  }
}
// ------------------------------------------------------------- 10. mooks
function mookShape(front) {
  // local coords: origin at base centre, facing left; returns list of Path2D
  const s = [];
  s.push(rrect(-50, -862, 100, 124, 32));                 // head
  s.push(rect(-16, -744, 32, 44));                        // neck
  s.push(rrect(-60, -712, 118, 300, 24));                 // torso slab
  s.push(poly([[-54, -440], [-6, -440], [-10, -30], [-54, -30]]));  // front leg
  s.push(poly([[2, -440], [50, -440], [46, -30], [4, -30]]));       // rear leg
  s.push(rrect(-90, -36, 86, 36, 12));                    // front foot
  s.push(rrect(-34, -36, 80, 36, 12));                    // rear foot
  return s;
}
function frontShape() {
  const s = [];
  s.push(rrect(-52, -862, 104, 124, 32));
  s.push(rect(-16, -744, 32, 44));
  s.push(rrect(-90, -712, 180, 300, 30));
  s.push(rrect(-122, -700, 36, 270, 16)); s.push(rrect(86, -700, 36, 270, 16));
  s.push(poly([[-70, -440], [-8, -440], [-12, -10], [-74, -10]]));
  s.push(poly([[8, -440], [70, -440], [74, -10], [12, -10]]));
  return s;
}
function cardboard(shapes, interior = 0.6, border = 12, thick = 12) {
  if (thick) { both(c => { c.save(); c.translate(thick, thick * 0.4); });
    for (const p of shapes) { stk(p, border, 0, 1, 'round'); fill(p, 0, 1); }
    both(c => c.restore()); }
  for (const p of shapes) { stk(p, border, 0, 0, 'round'); }
  for (const p of shapes) { stk(p, border + 3, 0, 0, 'butt', [2.5, 3.5]); }
  for (const p of shapes) fill(p, 0, 0);
  for (const p of shapes) fill(p, 0, interior);
}
function mookStrut() { fill(poly([[30, -560], [44, -560], [150, 0], [118, 0]]), 0, 1); stk(line([[40, -300], [128, -60]]), 3, 0, 0.6); }
// B: behind, cropped, upright
{
  const M = PR.mookB; save(); both(c => { c.translate(M.bx, M.by); c.scale(M.s, M.s); });
  cardboard(mookShape()); restore();
}
// A: leaning toward the hero, arm hinged up to the cup
let A_handInfo = null;
{
  const M = PR.mookA, th = M.lean * D2R, sc = M.h / 862;
  const toW = (x, y) => [M.bx + sc * (x * Math.cos(th) - y * Math.sin(th)), M.by + sc * (x * Math.sin(th) + y * Math.cos(th))];
  save(); both(c => { c.translate(M.bx, M.by); c.rotate(th); c.scale(sc, sc); });
  mookStrut();
  cardboard(mookShape());
  // corrugated crease across the torso
  stk(line([[-58, -560], [56, -548]]), 2, 0, 0.25, 'butt');
  restore();
  // hinged arm: pivot at local shoulder, hand target 20 px short of the saucer rim
  const pv = toW(-6, -676);
  const rimX = 762 + (840 - 762) * PR.cup_scale + PR.hero_dx, target = [rimX + M.hand_gap + 26, 790 + PR.hero_dy];
  const ang = Math.atan2(target[1] - pv[1], target[0] - pv[0]);
  const len = Math.hypot(target[0] - pv[0], target[1] - pv[1]);
  save(); both(c => { c.translate(pv[0], pv[1]); c.rotate(ang); });
  const arm = [rrect(-24, -22, len - 20, 44, 20), rrect(len - 52, -27, 58, 52, 18), rrect(len - 50, -36, 22, 20, 8)];
  cardboard(arm);
  restore();
  fill(ell(pv[0], pv[1], 7, 7), 0, 1);
  fill(ell(pv[0] - 1, pv[1] - 1, 2.5, 2.5), 0, 0);
  A_handInfo = { pv, target, len };
}
// C: tiny, on the parapet, mid-flip on its hinge
{
  const M = PR.mookC;
  // swing arcs (path of the head)
  for (const [r, a0, a1, w] of [[1.03, -2.62, -2.36, 4], [0.9, -2.58, -2.38, 3]]) {
    const p = new Path2D(); p.arc(M.bx, M.by, r * 830 * M.s, a0, a1); stk(p, w, 0, 1);
  }
  save(); both(c => { c.translate(M.bx, M.by); c.rotate(-M.flip * D2R); c.scale(M.s, M.s); });
  cardboard(mookShape(), 0.6, 14);
  restore();
  // hinge plate on the coping
  fill(rrect(M.bx - 30, M.by - 6, 60, 10, 3), 0, 1);
  fill(ell(M.bx, M.by - 2, 6, 6), 0, 0);
}
// ------------------------------------------------------------- 11. hero
{
  const HX = PR.hero_dx, HY = PR.hero_dy, SW = PR.stroke;
  save(); both(c => c.translate(HX, HY));
  const j = k => PR[k];
  // rear arm behind the back
  stk(line([j('sh_r'), j('el_r'), j('ha_r')]), SW, 1, 1);
  // legs
  stk(line([j('hip'), j('kn_r'), j('ft_r'), j('toe_r')]), SW, 1, 1);
  stk(line([j('hip'), j('kn_l'), j('ft_l'), j('toe_l')]), SW, 1, 1);
  // torso + shoulders
  stk(line([j('hip'), j('neck')]), SW, 1, 1);
  stk(line([j('sh_r'), j('neck'), j('sh_l')]), SW, 1, 1);
  // apron: paper knock-out trapezoid, curved hem, violet outline, waist ties
  const ap = new Path2D(); ap.moveTo(488, 990); ap.lineTo(600, 990); ap.lineTo(668, 1400);
  ap.quadraticCurveTo(549, 1422, 430, 1400); ap.closePath();
  fill(ap, 0, 0);
  save(); clipBoth(ap);
  const fold = new Path2D(); fold.moveTo(584, 990); fold.lineTo(680, 990); fold.lineTo(680, 1430); fold.lineTo(612, 1430);
  fold.quadraticCurveTo(600, 1200, 584, 990); fold.closePath(); fill(fold, null, 0.16);
  restore();
  stk(ap, 5, 1, 1);
  const pk = new Path2D(); pk.moveTo(508, 1150); pk.lineTo(580, 1150); pk.lineTo(576, 1208); pk.quadraticCurveTo(544, 1214, 512, 1208); pk.closePath();
  stk(pk, 4, 1, 1);
  { const t1 = new Path2D(); t1.moveTo(490, 996); t1.bezierCurveTo(462, 1000, 446, 1022, 452, 1050); stk(t1, 6, 1, 1);
    const t2 = new Path2D(); t2.moveTo(490, 1000); t2.bezierCurveTo(470, 1012, 468, 1046, 482, 1072); stk(t2, 6, 1, 1);
    fill(ell(488, 999, 8, 6), 1, 1); }
  stk(line([[490, 1000], [598, 1000]]), 8, 1, 1, 'butt');
  // lead arm
  stk(line([j('sh_l'), j('el_l'), j('ha_l')]), SW, 1, 1);
  // neck
  const hd = PR.head;
  stk(line([[hd.cx - 6, hd.cy + 24], j('neck')]), SW, 1, 1);
  // head capsule + disc hat, tilted together
  save(); both(c => { c.translate(hd.cx, hd.cy); c.rotate(hd.rot * D2R); });
  fill(rrect(-hd.w / 2, -hd.h / 2, hd.w, hd.h, hd.h / 2), 1, 1);
  const ht = PR.hat;
  fill(ell(ht.dx + 2, ht.dy - 10, 36, 16), 1, 0);
  fill(ell(ht.dx, ht.dy, ht.rx, ht.ry), 1, 0);
  restore();
  // saucer + cup, scaled up a touch about the hand for phone legibility
  save(); both(c => { c.translate(762, 806); c.scale(PR.cup_scale, PR.cup_scale); c.translate(-762, -806); });
  fill(ell(770, 800, 70, 13), 0, 0); stk(ell(770, 800, 70, 13), 4, 0, 1);
  const cb = new Path2D(); cb.moveTo(730, 744); cb.lineTo(810, 744); cb.bezierCurveTo(806, 776, 796, 796, 770, 797);
  cb.bezierCurveTo(744, 796, 734, 776, 730, 744); cb.closePath();
  const hdl = new Path2D(); hdl.ellipse(812, 764, 12, 14, 0, -Math.PI * 0.55, Math.PI * 0.6); stk(hdl, 6, 0, 1, 'butt');
  fill(cb, 0, 0); stk(cb, 3, 0, 1);
  stk(ell(770, 744, 40, 9), 7, 0, 1);
  // tea: fills the rim and domes above it (brim-full meniscus)
  const tea = new Path2D(); tea.moveTo(733, 745); tea.bezierCurveTo(738, 726, 802, 726, 807, 745);
  tea.ellipse(770, 745, 37, 6.5, 0, 0, Math.PI, false); tea.closePath();
  fill(tea, 0.85, 0.3);
  const hl = new Path2D(); hl.moveTo(748, 737); hl.quadraticCurveTo(762, 731, 780, 733); stk(hl, 3, 0, 0);
  // one bead trembling on the rim edge
  const bead = new Path2D(); bead.moveTo(806, 742); bead.quadraticCurveTo(815, 752, 811, 757); bead.arc(808, 756, 4, 0.3, Math.PI * 1.2); bead.closePath();
  fill(bead, 0.85, 0.3);
  // steam
  for (const [sx, h, ph] of [[752, 120, 0], [772, 150, 1], [792, 110, 0]]) {
    const p = new Path2D(); const y0 = 720; p.moveTo(sx, y0);
    const w = ph ? 12 : -12;
    const lean = 0.16 * h;  // drifts toward the customer
    p.bezierCurveTo(sx + w, y0 - h * 0.25, sx - w + lean * 0.3, y0 - h * 0.45, sx + lean * 0.5, y0 - h * 0.6);
    p.bezierCurveTo(sx + w + lean * 0.7, y0 - h * 0.75, sx - w * 0.5 + lean * 0.9, y0 - h * 0.9, sx + w * 0.3 + lean, y0 - h);
    stk(p, 9, 0.5, 0);
  }
  restore();
  restore();
}

// ------------------------------------------------------------- halftone + print
const pd = PK.getImageData(0, 0, W, H).data, bd = BL.getImageData(0, 0, W, H).data;
function vnoiseGrid(freq, oct, seed, step) {
  const gw = Math.ceil(W / step) + 2, gh = Math.ceil(H / step) + 2, out = new Float32Array(gw * gh);
  const lat = (ix, iy, s) => hash(ix, iy, s);
  const sm = t => t * t * (3 - 2 * t);
  for (let gy = 0; gy < gh; gy++) for (let gx = 0; gx < gw; gx++) {
    let a = 0, amp = 1, tot = 0, f = freq;
    for (let o = 0; o < oct; o++) {
      const x = gx * step * f, y = gy * step * f, ix = Math.floor(x), iy = Math.floor(y), fx = sm(x - ix), fy = sm(y - iy);
      const v00 = lat(ix, iy, seed + o), v10 = lat(ix + 1, iy, seed + o), v01 = lat(ix, iy + 1, seed + o), v11 = lat(ix + 1, iy + 1, seed + o);
      a += amp * ((v00 * (1 - fx) + v10 * fx) * (1 - fy) + (v01 * (1 - fx) + v11 * fx) * fy); tot += amp; amp *= 0.5; f *= 2;
    }
    out[gy * gw + gx] = a / tot;
  }
  return { out, gw, step };
}
function sampleGrid(G, x, y) {
  const fx = x / G.step, fy = y / G.step, ix = Math.floor(fx), iy = Math.floor(fy), tx = fx - ix, ty = fy - iy, o = G.out, w = G.gw;
  const a = o[iy * w + ix], b = o[iy * w + ix + 1], c = o[(iy + 1) * w + ix], d = o[(iy + 1) * w + ix + 1];
  return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty;
}
const nP = vnoiseGrid(PR.starve_freq, 4, 101, 6), nB = vnoiseGrid(PR.starve_freq, 4, 202, 6);
const [s0, s1] = PR.starve;
function cover(data, x, y, ang, seed) {
  if (x < 0 || y < 0 || x >= W || y >= H) return 0;
  const d = 1 - data[(y * W + x) * 4] / 255;
  if (d < 0.004) return 0;
  if (d > PR.solid) return hash(x >> 1, y >> 1, seed + 7) < 0.004 ? 0.35 : 1;
  const c = Math.cos(ang), s = Math.sin(ang), cell = PR.cell;
  const u = (x * c + y * s) / cell, v = (-x * s + y * c) / cell;
  const r0 = PR.kdot * cell * Math.sqrt(d);
  let acc = 0;
  for (let k = 0; k < 4; k++) {
    const ox = (k & 1) ? 0.75 : 0.25, oy = (k & 2) ? 0.75 : 0.25;
    const uu = u + (ox * c + oy * s) / cell, vv = v + (-ox * s + oy * c) / cell;
    const iu = Math.floor(uu), iv = Math.floor(vv), fu = uu - iu - 0.5, fv = vv - iv - 0.5;
    const dist = Math.sqrt(fu * fu + fv * fv) * cell;
    const r = hash(iu, iv, seed) < PR.dropout ? r0 * (d > 0.22 ? 0.9 : 0.3) : r0;
    let cv = (r - dist) * 2 + 0.5; acc += cv < 0 ? 0 : cv > 1 ? 1 : cv;
  }
  return acc * 0.25;
}
const out = document.getElementById('out').getContext('2d');
const img = out.createImageData(W, H), o = img.data;
const pap = PR.paper, pi = PR.pink.map(v => v / 255), bl = PR.blue.map(v => v / 255);
const aP = PR.ang_pink * D2R, aB = PR.ang_blue * D2R, [mx, my] = PR.misreg;
for (let y = 0; y < H; y++) {
  for (let x = 0; x < W; x++) {
    let cp = cover(pd, x - mx, y - my, aP, 11), cb = cover(bd, x, y, aB, 23);
    if (cp > 0) cp *= s0 + (s1 - s0) * Math.min(1, Math.max(0, (sampleGrid(nP, x, y) - 0.25) * 2));
    if (cb > 0) cb *= s0 + (s1 - s0) * Math.min(1, Math.max(0, (sampleGrid(nB, x, y) - 0.25) * 2));
    // paper tooth (fine) + blue edge vignette
    const t = 1 - PR.tooth * (0.6 * hash(x, y, 5) + 0.4 * hash(x >> 1, y >> 1, 6));
    const ex = (x - W / 2) / (W / 2), ey = (y - H / 2) / (H / 2), e = Math.sqrt(ex * ex * 0.9 + ey * ey * 0.75);
    const vg = PR.vignette * Math.min(1, Math.max(0, (e - 0.55) / 0.5));
    const i = (y * W + x) * 4;
    for (let k = 0; k < 3; k++) {
      o[i + k] = pap[k] * t * (1 - cp * (1 - pi[k])) * (1 - cb * (1 - bl[k])) * (1 - vg * (1 - bl[k]));
    }
    o[i + 3] = 255;
  }
}
out.putImageData(img, 0, 0);
document.title = 'done';
</script></body></html>
"""

with open(OUT, 'w') as f:
    f.write(HTML.replace('__PARAMS__', json.dumps(P)))
print('wrote', OUT)
