// Render an SVG or HTML file to PNG with headless Chromium.
// Usage: NODE_PATH=$(npm root -g) node render.js in.svg out.png [width height]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [inp, out, w = '1080', h = '1920'] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
  const p = await b.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  const t0 = Date.now();
  await p.goto('file://' + path.resolve(inp));
  await p.waitForTimeout(300);
  await p.screenshot({ path: out, clip: { x: 0, y: 0, width: +w, height: +h } });
  await b.close();
  console.log('rendered', out, ((Date.now() - t0) / 1000).toFixed(1), 's');
})();
