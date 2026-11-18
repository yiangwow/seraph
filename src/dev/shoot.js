// Headless screenshot tool: loads the dev page, seeks the audio-backed clock
// to given timestamps, and saves a PNG of each. Usage: node src/dev/shoot.js [t1 t2 ...]
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const URL = process.env.SHOOT_URL || 'http://localhost:5173/?shoot=1';
const OUT = 'shots';
const args = process.argv.slice(2);
const times = (args.length ? args : ['0', '20', '45', '70', '90']).map(Number);

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const [vw, vh] = (process.env.VIEWPORT || '1280x720').split('x').map(Number);
const page = await browser.newPage({ viewport: { width: vw, height: vh } });
page.on('console', (m) => { if (m.type() === 'error') console.log('PAGE ERROR:', m.text()); });
page.on('pageerror', (e) => console.log('PAGE EXCEPTION:', e.message));

await page.goto(URL, { waitUntil: 'load' });
await page.waitForFunction(() => {
  const c = window.__seraph && window.__seraph.clock;
  return c && c.duration > 0;
}, null, { timeout: 15000 }).catch(() => console.log('WARN: audio metadata not ready (duration unknown)'));

for (const t of times) {
  await page.evaluate((tt) => { window.__seraph.clock.seek(tt); }, t);
  await page.waitForTimeout(150);
  const name = `${OUT}/t_${String(Math.round(t)).padStart(3, '0')}.png`;
  await page.screenshot({ path: name });
  console.log('shot', name);
}
await browser.close();
console.log('done');
