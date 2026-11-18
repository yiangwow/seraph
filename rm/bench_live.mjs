import { chromium } from 'playwright';

const W = +process.argv[2] || 2560, H = +process.argv[3] || 1440;
const browser = await chromium.connectOverCDP('http://172.29.16.1:9223');
const ctx = browser.contexts()[0] ?? await browser.newContext();
const page = await ctx.newPage();
await page.setViewportSize({ width: W, height: H });
await page.goto('http://localhost:8787/rm/live.html', { waitUntil: 'networkidle' });

const renderer = await page.evaluate(() => {
  const gl = document.querySelector('canvas').getContext('webgl2');
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unknown';
});
console.log('RENDERER', renderer);
if (/SwiftShader/i.test(renderer)) throw new Error('GPU_LANE_GOT_SWIFTSHADER');

// park the piece at its heaviest state: override the media clock so the live
// loop renders t=80 every frame without playing audio
await page.evaluate(() => {
  window.__benchT = 80;
  Object.defineProperty(HTMLMediaElement.prototype, 'currentTime', {
    get(){ return window.__benchT; }, set(v){ window.__benchT = v; }, configurable: true
  });
});

for (let i = 0; i < 6; i++) {
  const s = await page.evaluate(() => new Promise(res => {
    let n = 0, worst = 0, prev = 0; const t0 = performance.now();
    const cv = document.querySelector('canvas');
    function tick(ts){ if(prev) worst = Math.max(worst, ts-prev); prev = ts; n++;
      if (performance.now() - t0 < 2000) requestAnimationFrame(tick);
      else res({ fps: (n / (performance.now() - t0) * 1000).toFixed(1), worst: worst.toFixed(0), w: cv.width, h: cv.height }); }
    requestAnimationFrame(tick);
  }));
  console.log(`sample ${i}: ${s.fps} fps  worst ${s.worst}ms  internal ${s.w}x${s.h}`);
}
await page.close();
process.exit(0);
