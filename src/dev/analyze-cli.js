// Decode the track with ffmpeg and extract a coarse energy profile plus kick
// onset candidates, writing both to public/score-seed.json for authoring the
// wake curve against real hits.
//   node src/dev/analyze-cli.js audio/seraph-clip.mp3
import { spawnSync } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { rmsEnvelope, normalize, detectBoundaries, detectOnsets } from './analyze.js';

const file = process.argv[2] || 'audio/seraph-clip.mp3';
const SR = 22050;             // decode sample rate (mono)
const HPS = 8;                // envelope hops per second

const ff = spawnSync('ffmpeg', [
  '-v', 'error', '-i', file, '-ac', '1', '-ar', String(SR), '-f', 'f32le', 'pipe:1',
], { maxBuffer: 1 << 30 });
if (ff.status !== 0) { console.error(ff.stderr.toString()); process.exit(1); }

const pcm = new Float32Array(ff.stdout.buffer, ff.stdout.byteOffset, Math.floor(ff.stdout.length / 4));
const duration = pcm.length / SR;
const hops = Math.round(duration * HPS);
const env = normalize(Array.from(rmsEnvelope(pcm, hops)));

const smooth = (a, r) => a.map((_, i) => {
  let s = 0, n = 0;
  for (let j = Math.max(0, i - r); j <= Math.min(a.length - 1, i + r); j++) { s += a[j]; n++; }
  return s / n;
});
const sm = smooth(env, HPS);

const STEP = 4 * HPS;
const profile = [];
for (let i = 0; i < sm.length; i += STEP) {
  const seg = sm.slice(i, i + STEP);
  const avg = seg.reduce((x, y) => x + y, 0) / seg.length;
  profile.push({ t: +(i / HPS).toFixed(0), e: +avg.toFixed(3) });
}
const boundaries = detectBoundaries(sm, 0.5).map(i => +(i / HPS).toFixed(1));
const onsets = detectOnsets(pcm, SR, { cutoffHz: 150, hopsPerSecond: 100, minGapSec: 0.08, floor: 0.35 });

console.log('duration', duration.toFixed(2), 's   hops', hops);
console.log('\n4s energy profile (t=sec, e=0..1):');
for (const p of profile) {
  const bar = '#'.repeat(Math.round(p.e * 30));
  console.log(`${String(p.t).padStart(4)}s |${bar.padEnd(30)}| ${p.e}`);
}
console.log('\nthreshold(0.5) crossings:', JSON.stringify(boundaries));
console.log(`\n${onsets.length} kick onset candidates (floor=0.35):`, JSON.stringify(onsets));

mkdirSync('public', { recursive: true });
const seed = { duration: +duration.toFixed(2), hopsPerSecond: HPS, boundaries, profile, onsets };
writeFileSync('public/score-seed.json', JSON.stringify(seed, null, 2));
console.log('\nwrote public/score-seed.json');
