// seraph-light film renderer — GPU lane: same deterministic state logic as
// render_film.mjs, but drives Windows headless Chrome (AMD RX 6950 XT via
// ANGLE/D3D11) over CDP through the Windows-side relay on :9223.
// Output goes to rm/frames_gpu/ — never mix with SwiftShader frames.
// Usage: node rm/render_film_gpu.mjs
import { chromium } from 'playwright';
import { readFileSync, mkdirSync, existsSync, statSync } from 'fs';
import { score } from '../src/score-data.js';
import { sampleScore } from '../src/score.js';

const CDP = 'http://172.29.16.1:9223';
const PAGE_URL = 'file:///C:/Users/computer/seraph-assets/rm.html';

const seed = JSON.parse(readFileSync(new URL('../public/score-seed.json', import.meta.url)));
const ONSETS = seed.onsets;
const FPS = 30;
const N = 2700;
const GAZE_LOCK_T = 78.5;

function mulberry(a) { return function() { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function blinkEnvelope(t, wake) {
  if (wake < 0.6) return 0;
  const w = Math.floor(t / 11.5);
  const rng = mulberry(w * 7919 + 3);
  const blinkT = w * 11.5 + 1.5 + rng() * 8.5;
  const d = Math.abs(t - blinkT);
  if (d > 0.28) return 0;
  const c = 1 - d / 0.28;
  return c * c * (3 - 2 * c);
}

function stateAt(t) {
  const wake = sampleScore(score, t);
  let lid = 0.06 + 0.94 * wake + 0.03 * Math.sin(t * 2 * Math.PI / 11);
  lid *= 1 - 0.97 * blinkEnvelope(t, wake);
  lid = Math.max(0.02, Math.min(1, lid));
  const pupil = 0.85 + 0.40 * wake + 0.015 * Math.sin(t * 3.1);
  const lockf = t > GAZE_LOCK_T ? Math.max(0, 1 - (t - GAZE_LOCK_T) / 0.8) : 1;
  const amp = 0.10 * (0.3 + 0.7 * wake) * lockf;
  const gx = amp * (Math.sin(t * 2 * Math.PI / 13.7 + 1.3) + 0.5 * Math.sin(t * 2 * Math.PI / 7.3));
  const gy = amp * (Math.sin(t * 2 * Math.PI / 17.1 + 4.2) + 0.5 * Math.sin(t * 2 * Math.PI / 9.4 + 2.0));
  let pulse = 0;
  for (const o of ONSETS) {
    const dt = t - o.t;
    if (dt >= 0 && dt < 0.9) pulse = Math.max(pulse, (o.strength / 0.53) * Math.exp(-dt / 0.16));
  }
  return [t, wake, lid, pupil, gx, gy, Math.min(pulse, 1)];
}

const outDir = new URL('./frames_gpu/', import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const browser = await chromium.connectOverCDP(CDP);
const ctx = await browser.newContext({ viewport: { width: 1080, height: 1080 } });
const page = await ctx.newPage();
page.on('pageerror', e => console.error('PAGEERROR', e.message));
await page.goto(PAGE_URL);
await page.waitForFunction('window.__ready === true', { timeout: 20000 });
const renderer = await page.evaluate(() => {
  const gl = document.createElement('canvas').getContext('webgl2');
  const e = gl.getExtension('WEBGL_debug_renderer_info');
  return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
});
console.log('RENDERER', renderer);
if (/SwiftShader/i.test(renderer)) throw new Error('GPU_LANE_GOT_SWIFTSHADER');
const canvas = page.locator('#c');

const t0 = Date.now();
for (let f = 0; f < N; f++) {
  const t = f / FPS;
  const outPath = `${outDir}frame_${String(f).padStart(5, '0')}.png`;
  if (existsSync(outPath) && statSync(outPath).size > 100000) continue; // resume
  const st = stateAt(t);
  let res = await page.evaluate(s => window.renderFrame(...s), st);
  if (!res || !res.ok || res.sum >= 64 * 255) {
    console.log(`gl context lost at frame ${f} — reloading page`);
    await page.reload();
    await page.waitForFunction('window.__ready === true', { timeout: 20000 });
    res = await page.evaluate(s => window.renderFrame(...s), st);
    if (!res || !res.ok || res.sum >= 64 * 255) throw new Error(`DEAD_GL_AFTER_RELOAD at frame ${f} (ok=${res && res.ok} sum=${res && res.sum})`);
  }
  await canvas.screenshot({ path: outPath });
  if (f % 300 === 0) {
    const rate = (Date.now() - t0) / 1000 / (f + 1);
    console.log(`gpu progress ${f}/${N} rate=${rate.toFixed(2)}s/f eta=${(rate * (N - f) / 60).toFixed(0)}min`);
  }
}
await ctx.close();
console.log('FILM_FRAMES_DONE_GPU', outDir);
