import { chromium } from 'playwright';
import fs from 'fs';

const OUT = '/tmp/claude-1000/-home-unix/dc5bef73-42d8-4ee6-b7dd-5c33c5b4dc4a/scratchpad';
const TIMES = [3, 24, 42, 50, 65, 80, 88];

const browser = await chromium.connectOverCDP('http://172.29.16.1:9223');
const ctx = browser.contexts()[0] ?? await browser.newContext();
const page = await ctx.newPage();
await page.setViewportSize({ width: 1280, height: 720 });
await page.goto('http://localhost:8787/rm/live.html', { waitUntil: 'networkidle' });

const renderer = await page.evaluate(() => {
  const gl = document.querySelector('canvas').getContext('webgl2');
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unknown';
});
console.log('RENDERER', renderer);
if (/SwiftShader/i.test(renderer)) throw new Error('GPU_LANE_GOT_SWIFTSHADER');

// freeze the rAF loop so it can't race our captures
await page.evaluate(() => {
  window.__orig = window.renderFrame;
  window.renderFrame = () => {};
  window.setScale(1);   // stills at full internal resolution
});

for (const t of TIMES) {
  const dataUrl = await page.evaluate((tt) => {
    window.__orig(...window.stateAt(tt));
    const cv = document.querySelector('canvas');
    const gl = cv.getContext('webgl2');
    if (gl.isContextLost()) return 'LOST';
    return cv.toDataURL('image/png');
  }, t);
  if (dataUrl === 'LOST') { console.log('CONTEXT_LOST at', t); break; }
  const b64 = dataUrl.split(',')[1];
  fs.writeFileSync(`${OUT}/live_t${t}.png`, Buffer.from(b64, 'base64'));
  console.log('WROTE', `live_t${t}.png`, b64.length);
}
await page.close();
process.exit(0);
