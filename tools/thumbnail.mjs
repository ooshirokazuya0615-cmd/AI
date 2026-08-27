#!/usr/bin/env node
/**
 * YouTubeサムネ生成ツール
 *
 *   node tools/thumbnail.mjs <spec.json> [出力先.png]
 *
 * 1280x720 のPNGを書き出します。
 * 仕様は tools/README.md を参照。
 */
import { chromium } from 'playwright';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';

const run = promisify(execFile);

// Nodeのfetchはプロキシ環境変数を見ないため、取得はcurlに任せる
async function get(url, binary = false) {
  const args = ['-sSL', '--compressed', '-A', UA, url];
  const { stdout } = await run('curl', binary ? [...args, '--output', '-'] : args,
    { maxBuffer: 64 * 1024 * 1024, encoding: binary ? 'buffer' : 'utf8' });
  return stdout;
}

const W = 1280, H = 720;
const CACHE = path.join(path.dirname(new URL(import.meta.url).pathname), '.fontcache');

/* ---------- フォント取得（Google Fontsから必要な文字だけ切り出す） ---------- */

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

async function fetchFont(family, weight, text) {
  const chars = [...new Set([...text])].sort().join('');
  const key = `${family}-${weight}-${Buffer.from(chars).toString('base64url').slice(0, 40)}`;
  const cached = path.join(CACHE, `${key}.b64`);
  if (existsSync(cached)) return readFile(cached, 'utf8');

  const url = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family)}:wght@${weight}` +
              `&text=${encodeURIComponent(chars)}`;
  const css = await get(url);
  const woff2 = css.match(/url\((https:\/\/fonts\.gstatic\.com\/[^)]+)\)/)?.[1];
  if (!woff2) throw new Error(`フォントを取得できませんでした: ${family} ${weight}`);
  const buf = Buffer.from(await get(woff2, true));
  const b64 = buf.toString('base64');
  await mkdir(CACHE, { recursive: true });
  await writeFile(cached, b64);
  return b64;
}

/* ---------- テキスト装飾 ---------- */

// [強調] を <em> に変換。HTMLは全てエスケープする。
function markup(line) {
  return line
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\[([^\]]*)\]/g, '<em>$1</em>');
}

const stripMarks = (s) => s.replace(/[[\]]/g, '');

/* ---------- プリセット ---------- */

const PRESETS = {
  // スカッと系：赤黒の斜め分割・極太ゴシック・黄色アクセント
  sukatto: {
    font: { family: 'Noto Sans JP', weight: 900 },
    background: `
      background:
        linear-gradient(115deg, #12060a 0%, #12060a 46%, #8b0f1d 46%, #c4142a 100%);`,
    overlay: `
      background-image:
        repeating-linear-gradient(115deg, rgba(255,255,255,.045) 0 3px, transparent 3px 9px);`,
    ink: '#ffffff',
    accent: '#ffd21e',
    stroke: '#0a0306',
    strokeWidth: 11,
    glow: 'rgba(255, 60, 80, .55)',
    labelBg: '#ffd21e',
    labelInk: '#1a0409',
    align: 'left',
    subInk: 'rgba(255,255,255,.72)',
  },
  // 感動系：藍のグラデ・明朝・金アクセント・静かな余白
  kandou: {
    font: { family: 'Noto Serif JP', weight: 900 },
    background: `
      background:
        radial-gradient(ellipse 90% 70% at 50% 0%, #2a4a7a 0%, transparent 62%),
        linear-gradient(180deg, #0e1a30 0%, #060b16 100%);`,
    overlay: `
      background-image:
        radial-gradient(circle at 50% 42%, rgba(255,225,170,.13) 0%, transparent 55%);`,
    ink: '#f4f1ea',
    accent: '#f0c96b',
    stroke: '#04070e',
    strokeWidth: 8,
    glow: 'rgba(240, 201, 107, .30)',
    labelBg: 'rgba(240,201,107,.16)',
    labelInk: '#f0c96b',
    align: 'center',
    subInk: 'rgba(244,241,234,.62)',
  },
};

/* ---------- HTML組み立て ---------- */

function buildHtml(spec, fontB64) {
  const p = { ...PRESETS[spec.preset ?? 'sukatto'], ...(spec.overrides ?? {}) };
  const lines = spec.lines ?? [];

  // 行数に応じて自動で文字サイズを決める（1行が長いほど小さく）
  const longest = Math.max(...lines.map((l) => stripMarks(l).length), 1);
  const byCount = [0, 168, 150, 122, 96, 78][Math.min(lines.length, 5)] ?? 78;
  const byLength = (W - 150) / longest * 1.06;
  const size = Math.round(Math.min(byCount, byLength) * (spec.scale ?? 1));

  const bgImage = spec.bgImage
    ? `<div class="photo" style="background-image:url('${spec.bgImage}')"></div>`
    : '';

  return `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {
  font-family: 'TH';
  src: url(data:font/woff2;base64,${fontB64}) format('woff2');
  font-weight: ${p.font.weight};
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: ${W}px; height: ${H}px; overflow: hidden; }
.stage {
  position: relative; width: ${W}px; height: ${H}px;
  ${p.background}
  font-family: 'TH', 'IPAGothic', sans-serif;
  font-weight: ${p.font.weight};
  display: flex; flex-direction: column;
  justify-content: center;
  align-items: ${p.align === 'center' ? 'center' : 'flex-start'};
  padding: 56px 64px;
}
.photo {
  position: absolute; inset: 0;
  background-size: cover; background-position: center;
  opacity: ${spec.bgOpacity ?? 0.42};
  mix-blend-mode: luminosity;
}
.overlay { position: absolute; inset: 0; ${p.overlay} }
.vignette {
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 78% 78% at 50% 46%, transparent 42%, rgba(0,0,0,.62) 100%);
}
.content { position: relative; width: 100%; text-align: ${p.align}; }

.label {
  display: inline-block;
  background: ${p.labelBg}; color: ${p.labelInk};
  font-size: 30px; letter-spacing: .16em; padding: 9px 26px 10px;
  margin-bottom: 26px; border-radius: 4px;
}

.line {
  font-size: ${size}px;
  line-height: 1.14;
  letter-spacing: ${spec.tracking ?? '-.02em'};
  color: ${p.ink};
  -webkit-text-stroke: ${p.strokeWidth}px ${p.stroke};
  paint-order: stroke fill;
  text-shadow:
    0 6px 0 ${p.stroke},
    0 0 42px ${p.glow},
    0 14px 34px rgba(0,0,0,.62);
  white-space: nowrap;
}
.line em { font-style: normal; color: ${p.accent}; }

.sub {
  margin-top: 26px; font-size: 34px; letter-spacing: .06em;
  color: ${p.subInk};
  -webkit-text-stroke: 5px ${p.stroke};
  paint-order: stroke fill;
}
</style></head><body>
<div class="stage">
  ${bgImage}
  <div class="overlay"></div>
  <div class="vignette"></div>
  <div class="content">
    ${spec.label ? `<div class="label">${markup(spec.label).replace(/<\/?em>/g, '')}</div>` : ''}
    ${lines.map((l) => `<div class="line">${markup(l)}</div>`).join('\n    ')}
    ${spec.sub ? `<div class="sub">${markup(spec.sub).replace(/<\/?em>/g, '')}</div>` : ''}
  </div>
</div>
</body></html>`;
}

/* ---------- 実行 ---------- */

const [specPath, outArg] = process.argv.slice(2);
if (!specPath) {
  console.error('使い方: node tools/thumbnail.mjs <spec.json> [出力先.png]');
  process.exit(1);
}

const spec = JSON.parse(await readFile(specPath, 'utf8'));
const preset = PRESETS[spec.preset ?? 'sukatto'];
if (!preset) throw new Error(`未知のpreset: ${spec.preset}（sukatto / kandou）`);

const allText = [spec.label, ...(spec.lines ?? []), spec.sub].filter(Boolean).join('');
const fontB64 = await fetchFont(preset.font.family, preset.font.weight, stripMarks(allText));

const out = outArg ?? specPath.replace(/\.json$/, '.png');
await mkdir(path.dirname(path.resolve(out)), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.setContent(buildHtml(spec, fontB64), { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: out });
await browser.close();

console.log(`書き出しました: ${out}`);
