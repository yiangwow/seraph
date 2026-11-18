// Self-check tool: decodes shoot.js's PNG screenshots and reports objective
// per-frame stats (brightness/variance, so a blank render is caught) plus a
// frame-to-frame pixel diff (so a frozen/static regression is caught) — a
// cheap, scriptable first pass before spending a vision-judgment look at the
// images. Usage: node src/dev/frame-stats.js shots/*.png (files in order)
import { PNG } from 'pngjs';
import { readFileSync } from 'node:fs';

function luminanceStats(png) {
  let sum = 0, sumSq = 0;
  const n = png.width * png.height;
  for (let i = 0; i < png.data.length; i += 4) {
    const lum = (png.data[i] + png.data[i + 1] + png.data[i + 2]) / 3;
    sum += lum;
    sumSq += lum * lum;
  }
  const mean = sum / n;
  const variance = sumSq / n - mean * mean;
  return { mean, stdev: Math.sqrt(Math.max(0, variance)) };
}

/** Mean absolute per-channel difference between two same-sized PNGs, normalized to 0..1. */
function pixelDiff(a, b) {
  let d = 0;
  const n = a.data.length;
  for (let i = 0; i < n; i += 4) {
    d += Math.abs(a.data[i] - b.data[i]) + Math.abs(a.data[i + 1] - b.data[i + 1]) + Math.abs(a.data[i + 2] - b.data[i + 2]);
  }
  return d / ((n / 4) * 3 * 255);
}

const files = process.argv.slice(2);
if (files.length === 0) {
  console.log('Usage: node src/dev/frame-stats.js shots/*.png');
  process.exit(1);
}

let prev = null, prevName = null;
let warnings = 0;
for (const f of files) {
  const png = PNG.sync.read(readFileSync(f));
  const s = luminanceStats(png);
  const flags = [];
  if (s.mean < 0.5 && s.stdev < 0.5) flags.push('WARN: near-black/near-uniform — might be a blank render');

  let diffStr = '';
  if (prev) {
    if (prev.width !== png.width || prev.height !== png.height) {
      diffStr = ` diff-vs-${prevName}=n/a (size mismatch)`;
    } else {
      const d = pixelDiff(prev, png);
      diffStr = ` diff-vs-${prevName}=${(d * 100).toFixed(3)}%`;
      // Calibrated against seraph's dark, sparse-highlight scenes: two truly
      // identical frames diff at exactly 0.000%, real motion between frames
      // (wheel rotation, an eye opening) measured 0.24-0.27% — this sits well
      // below real motion but well above the true-identical floor.
      if (d < 0.0005) flags.push(`WARN: nearly identical to ${prevName} — possible freeze/regression`);
    }
  }

  const flagStr = flags.length ? `  [${flags.join('; ')}]` : '';
  if (flags.length) warnings++;
  console.log(`${f}: mean=${s.mean.toFixed(1)} stdev=${s.stdev.toFixed(1)}${diffStr}${flagStr}`);

  prev = png; prevName = f;
}

if (warnings > 0) {
  console.log(`\n${warnings} warning(s) — investigate before treating the render as verified.`);
  process.exit(1);
}
console.log(`\nAll ${files.length} frame(s) look sane (non-blank, and each differs from its predecessor).`);
