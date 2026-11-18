# seraph — Milestone 6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Swap the wall-clock stand-in for the real audio clip, extract kick onset
times from the track, and re-author the wake curve so the dormant→awake build is
locked to genuine moments in the music — per the design spec's Milestone 6.

**Architecture:** Three parts. (1) `src/audioClock.js`, copied verbatim from
gaia-breaks (same interface `clock.js` already implements, so `main.js`'s shape
barely changes), wired into `main.js` with a play gate (browser autoplay policy
requires a user gesture before audio can play — this is new; the wall-clock never
needed one). (2) `src/dev/analyze.js`/`analyze-cli.js`, adapted from gaia-breaks,
decode the mp3 via `ffmpeg` and extract both a coarse energy profile and
fine-grained kick onset candidates (a from-scratch low-band-energy-flux
peak-picker — gaia-breaks' own `analyze.js` only had coarse section-boundary
detection, not per-kick timestamps, so this is new code, not a copy). (3)
`src/score-data.js`'s wake curve is replaced with real numbers derived by running
that tool once against `audio/seraph-clip.mp3` — this plan already contains the
exact resulting curve (the analysis was run once during planning; see Task 3).

**Tech Stack:** Same as prior milestones, plus `ffmpeg` (already available on this
machine, confirmed via `which ffmpeg`) for audio decoding — no new npm
dependency.

## Global Constraints

(Same as prior milestones' plans, still binding)
- Flat 2D SDF shader language only — no raymarched 3D. (Not touched by this
  milestone — no shader changes.)
- Dark background throughout.
- `uProgress` climbs 0→1 and clamps at 1 — it never resets or loops. The
  re-authored wake curve in Task 3 must be **strictly non-decreasing** end to
  end (every point's value ≥ the previous point's value) — "kick accents" are
  expressed as steeper slope between two nearby points, never as a dip.
- Idle motion is driven by `uTime`, independent of `uProgress` — nothing may be
  static. (Not touched by this milestone's shader — already satisfied since
  Milestone 5; this milestone only changes what feeds `uProgress`'s input
  curve and where `uTime`'s underlying clock comes from.)
- Every visual change is screenshot-verified with `node src/dev/shoot.js`, AND
  `npm run selfcheck -- shots/<files>` must show no warnings, before being shown
  to the user.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- The mp3 (`audio/seraph-clip.mp3`) stays gitignored and is never committed —
  only code and the small derived JSON analysis artifact are committed.
- Do not push to any remote or create the public repo — that only happens when
  the user explicitly says so.

## Scope

This plan implements **Milestone 6**, the last item on the design spec's
roadmap (`docs/superpowers/specs/2026-07-01-seraph-design.md`). After this
milestone, all six milestones from the original spec are complete.

---

### Task 1: Real audio clock + play gate

**Files:**
- Create: `src/audioClock.js`
- Create: `tests/audioClock.test.js`
- Modify: `index.html` (add `<audio>` element and a play gate overlay)
- Modify: `src/main.js` (swap `createClock()` for `createAudioClock()`, wire the
  gate, create the volume control, import the track as an asset)
- Modify: `src/dev/shoot.js` (wait for real audio metadata before seeking)

**Interfaces:**
- Consumes: nothing new.
- Produces: `createAudioClock(media): { time, duration, isPlaying, play(),
  pause(), seek(t) }` — same shape as `src/clock.js`'s `createClock()`, so
  everything downstream (`main.js`'s loop, `sampleScore`, `scenes.frame`,
  `window.__seraph`) is unaffected by the swap.

- [ ] **Step 1: Write the failing test**

Create `tests/audioClock.test.js`:

```js
import { describe, it, expect, vi } from 'vitest';
import { createAudioClock } from '../src/audioClock.js';

function fakeMedia() {
  return { currentTime: 0, duration: 90, paused: true,
    play: vi.fn(function () { this.paused = false; return Promise.resolve(); }),
    pause: vi.fn(function () { this.paused = true; }) };
}

describe('createAudioClock', () => {
  it('reports clamped time within [0, duration]', () => {
    const m = fakeMedia(); const c = createAudioClock(m);
    m.currentTime = -5; expect(c.time).toBe(0);
    m.currentTime = 999; expect(c.time).toBe(90);
    m.currentTime = 50; expect(c.time).toBe(50);
  });
  it('play() starts the media and flips isPlaying', async () => {
    const m = fakeMedia(); const c = createAudioClock(m);
    await c.play();
    expect(m.play).toHaveBeenCalled(); expect(c.isPlaying).toBe(true);
  });
  it('seek() sets currentTime clamped', () => {
    const m = fakeMedia(); const c = createAudioClock(m);
    c.seek(200); expect(m.currentTime).toBe(90);
    c.seek(30); expect(m.currentTime).toBe(30);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/audioClock.test.js`
Expected: FAIL — `Cannot find module '../src/audioClock.js'`

- [ ] **Step 3: Implement `src/audioClock.js`**

```js
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

/** Thin wrapper over an HTMLAudioElement (or any {currentTime,duration,paused,play,pause}). */
export function createAudioClock(media) {
  return {
    get time() { return clamp(media.currentTime || 0, 0, media.duration || 0); },
    get duration() { return media.duration || 0; },
    get isPlaying() { return !media.paused; },
    async play() { await media.play(); },
    pause() { media.pause(); },
    seek(t) { media.currentTime = clamp(t, 0, media.duration || 0); },
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/audioClock.test.js`
Expected: PASS (3 tests)

- [ ] **Step 5: Update `index.html`**

Read the current file first (it currently has just a `#stage`/`#gl` canvas and a
script tag). Replace its full contents with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>seraph</title>
  <style>
    html,body{margin:0;height:100%;background:#000;overflow:hidden;font-family:'Courier New',monospace;}
    #stage{position:fixed;inset:0;}
    #gl{width:100%;height:100%;display:block;}
    #gate{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
          background:#000;color:#c9a869;letter-spacing:3px;cursor:pointer;z-index:10;}
  </style>
</head>
<body>
  <div id="stage"><canvas id="gl"></canvas></div>
  <div id="gate"><div style="text-align:center;line-height:2.4">
    <div style="font-size:22px;letter-spacing:8px;">SERAPH</div>
    <div style="font-size:14px;margin-top:26px;opacity:.85;">&#9654; BEGIN</div>
  </div></div>
  <audio id="track" preload="auto"></audio>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 6: Rewrite `src/main.js`**

Read the current file first. Replace its full contents with:

```js
import { createRenderer } from './gl/renderer.js';
import { createScenes } from './gl/scenes.js';
import { createAudioClock } from './audioClock.js';
import { sampleScore } from './score.js';
import { score } from './score-data.js';
// Import the track as an asset so the production build inlines it as a base64
// data URI (assetsInlineLimit is set huge in vite.config) — the single-file
// dist/index.html is then fully self-contained and plays standalone.
import trackUrl from '../audio/seraph-clip.mp3';

const SHOOT = location.search.includes('shoot'); // headless screenshot mode

const audioEl = document.getElementById('track');
audioEl.src = trackUrl;

const canvas = document.getElementById('gl');
const dpr = Math.min(devicePixelRatio || 1, 2);
function resize(){ canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr; }
resize(); addEventListener('resize', resize);

const renderer = createRenderer(canvas);
const scenes = createScenes(renderer);
const clock = createAudioClock(audioEl);

// volume: a small HUD-styled slider, bottom-right; remembers the level
const vol = document.createElement('div');
vol.id = 'vol';
vol.style.cssText = 'position:fixed;right:28px;bottom:28px;z-index:5;display:flex;align-items:center;gap:8px;'
  + 'color:#9a8666;font-size:10px;letter-spacing:2px;opacity:.4;transition:opacity .3s;';
vol.innerHTML = '<span>VOL</span><input type="range" min="0" max="1" step="0.01" style="width:110px;height:2px;accent-color:#c9a869;cursor:pointer;">';
document.body.appendChild(vol);
const volSlider = vol.querySelector('input');
volSlider.value = localStorage.getItem('seraph-vol') ?? '1';
audioEl.volume = +volSlider.value;
volSlider.addEventListener('input', () => {
  audioEl.volume = +volSlider.value;
  localStorage.setItem('seraph-vol', volSlider.value);
});

const gate = document.getElementById('gate');
if (SHOOT) { gate.style.display = 'none'; vol.style.display = 'none'; }
gate.addEventListener('click', async () => {
  gate.style.display = 'none';
  await clock.play();
});

(function loop(){
  const t = clock.time;
  const wake = sampleScore(score, t);
  scenes.frame({ uTime: t, uProgress: wake, uAspect: canvas.width / canvas.height });
  requestAnimationFrame(loop);
})();

// expose for the dev scrubber / screenshot tool
window.__seraph = { clock, score };

if (import.meta.env.DEV && !SHOOT) {
  const { mountScrubber } = await import('./dev/scrubber.js');
  mountScrubber({ clock, score });
}
```

Note what's deliberately *not* here: no `clock.duration = score.duration` —
`createAudioClock`'s `duration` is a read-only getter derived from
`media.duration`, so assigning to it would throw (this is exactly the bug
Milestone 1's whole-branch review caught and fixed for the wall-clock; the fix
there was removing that assignment from `main.js` entirely, which is why this
swap needs no compensating change here).

- [ ] **Step 7: Update `src/dev/shoot.js`'s readiness wait**

Read the current file first. Find this block:

```js
await page.goto(URL, { waitUntil: 'load' });
await page.waitForFunction(() => window.__seraph && window.__seraph.clock, null, { timeout: 15000 })
  .catch(() => console.log('WARN: __seraph clock not ready'));
```

Replace it with:

```js
await page.goto(URL, { waitUntil: 'load' });
await page.waitForFunction(() => {
  const c = window.__seraph && window.__seraph.clock;
  return c && c.duration > 0;
}, null, { timeout: 15000 }).catch(() => console.log('WARN: audio metadata not ready (duration unknown)'));
```

(`clock.duration` now comes from the real `<audio>` element's metadata, which
loads asynchronously — the old check only confirmed the clock object existed,
not that seeking would actually work yet. `clock.seek(t)` sets
`media.currentTime` directly, which does not require a user gesture — only
`.play()` does — so `shoot.js` can keep bypassing the gate entirely, same as
gaia-breaks' equivalent tool.)

- [ ] **Step 8: Start the dev server in the background**

Run: `npm run dev`
Expected: `Local: http://localhost:5173/` printed, no errors.

- [ ] **Step 9: Screenshot-verify the swap didn't break anything**

Run: `npm run shoot -- 0 30 60 90`
Expected: `shots/t_000.png` .. `shots/t_090.png` written, no `PAGE ERROR`/
`PAGE EXCEPTION`, no `WARN: audio metadata not ready`. Visually: should look the
same as the end of Milestone 5 (dormant at 0, awake by 90) — this task only
swaps the clock source, it doesn't change the wake curve yet (that's Task 3).

- [ ] **Step 10: Run the automated self-check**

Run: `npm run selfcheck -- shots/t_000.png shots/t_030.png shots/t_060.png shots/t_090.png`
Expected: exit 0, no warnings.

- [ ] **Step 11: Stop the dev server**

- [ ] **Step 12: Commit**

```bash
git add src/audioClock.js tests/audioClock.test.js index.html src/main.js src/dev/shoot.js
git commit -m "Swap wall-clock for real audio clock with a play gate"
```

---

### Task 2: Kick onset detection tool

**Files:**
- Create: `src/dev/analyze.js`
- Create: `tests/analyze.test.js`
- Create: `src/dev/analyze-cli.js`
- Modify: `package.json` (add an `analyze` script)

**Interfaces:**
- Consumes: nothing (pure functions + a CLI entry point).
- Produces: `rmsEnvelope(samples, hops)`, `normalize(arr)`,
  `detectBoundaries(env, threshold)`, `detectOnsets(samples, sampleRate,
  opts): {t: number, strength: number}[]` from `src/dev/analyze.js`. Task 3
  does not import these directly — it uses the CLI's printed/written output —
  but they're the tested foundation the CLI is built on.

- [ ] **Step 1: Write the failing tests**

Create `tests/analyze.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { rmsEnvelope, normalize, detectBoundaries, detectOnsets } from '../src/dev/analyze.js';

describe('rmsEnvelope', () => {
  it('downsamples to the requested number of hops', () => {
    const samples = new Float32Array(1000).fill(0.5);
    const env = rmsEnvelope(samples, 10);
    expect(env.length).toBe(10);
    expect(env[0]).toBeCloseTo(0.5, 5);
  });
  it('returns higher values for louder windows', () => {
    const s = new Float32Array(200);
    s.fill(0.1, 0, 100); s.fill(0.9, 100, 200);
    const env = rmsEnvelope(s, 2);
    expect(env[1]).toBeGreaterThan(env[0]);
  });
});

describe('normalize', () => {
  it('scales the peak to 1 and floor to 0', () => {
    const out = normalize([2, 4, 6]);
    expect(out[0]).toBeCloseTo(0); expect(out[2]).toBeCloseTo(1);
  });
  it('handles a flat array without NaN', () => {
    expect(normalize([3, 3, 3]).every(v => v === 0)).toBe(true);
  });
});

describe('detectBoundaries', () => {
  it('finds the index where energy jumps up past the threshold', () => {
    const env = [0.1, 0.1, 0.1, 0.9, 0.9, 0.2];
    const b = detectBoundaries(env, 0.4);
    expect(b).toContain(3); // jump up
    expect(b).toContain(5); // drop down
  });
});

describe('detectOnsets', () => {
  it('finds sharp low-frequency pulses and ignores flat sections', () => {
    const sr = 2000, dur = 3;
    const samples = new Float32Array(sr * dur);
    const at = (t) => Math.round(t * sr);
    for (let k = 0; k < 8; k++) { samples[at(1.0) + k] = 1.0; samples[at(2.0) + k] = 1.0; }
    const onsets = detectOnsets(samples, sr, { cutoffHz: 150, hopsPerSecond: 100, minGapSec: 0.08, floor: 0.2 });
    expect(onsets.length).toBeGreaterThanOrEqual(2);
    const times = onsets.map(o => o.t);
    expect(times.some(t => Math.abs(t - 1.0) < 0.1)).toBe(true);
    expect(times.some(t => Math.abs(t - 2.0) < 0.1)).toBe(true);
  });
  it('debounces closely-spaced peaks within minGapSec', () => {
    const sr = 2000, dur = 2;
    const samples = new Float32Array(sr * dur);
    const at = (t) => Math.round(t * sr);
    for (let k = 0; k < 8; k++) { samples[at(1.00) + k] = 1.0; samples[at(1.02) + k] = 1.0; }
    const onsets = detectOnsets(samples, sr, { cutoffHz: 150, hopsPerSecond: 100, minGapSec: 0.08, floor: 0.2 });
    expect(onsets.length).toBe(1);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run tests/analyze.test.js`
Expected: FAIL — `Cannot find module '../src/dev/analyze.js'`

- [ ] **Step 3: Implement `src/dev/analyze.js`**

```js
// Pure analysis helpers (tested). No DOM/WebAudio — works in Node via ffmpeg-decoded PCM.

/** RMS energy per hop. samples: Float32Array mono. hops: number of output buckets. */
export function rmsEnvelope(samples, hops) {
  const out = new Float32Array(hops);
  const win = Math.floor(samples.length / hops);
  for (let h = 0; h < hops; h++) {
    let sum = 0;
    const start = h * win;
    for (let i = 0; i < win; i++) { const v = samples[start + i] || 0; sum += v * v; }
    out[h] = Math.sqrt(sum / win);
  }
  return out;
}

/** Scale array so min->0, max->1. Flat input -> all zeros. */
export function normalize(arr) {
  let min = Infinity, max = -Infinity;
  for (const v of arr) { if (v < min) min = v; if (v > max) max = v; }
  const range = max - min;
  return arr.map(v => (range === 0 ? 0 : (v - min) / range));
}

/** Indices where the normalized envelope crosses `threshold` (up or down). */
export function detectBoundaries(env, threshold) {
  const b = [];
  for (let i = 1; i < env.length; i++) {
    const a = env[i - 1] >= threshold, c = env[i] >= threshold;
    if (a !== c) b.push(i);
  }
  return b;
}

/** Simple bass-band onset (kick) detector: one-pole low-pass to isolate the
 * kick/bass band, then peak-pick local maxima in the envelope's positive
 * derivative (flux) above `floor`, debounced by `minGapSec` so closely-spaced
 * hits don't over-trigger. Returns onset times in seconds with a strength. */
export function detectOnsets(samples, sampleRate, { cutoffHz = 150, hopsPerSecond = 100, minGapSec = 0.08, floor = 0.35 } = {}) {
  const rc = 1 / (2 * Math.PI * cutoffHz);
  const dt = 1 / sampleRate;
  const alpha = dt / (rc + dt);
  const lp = new Float32Array(samples.length);
  let prev = 0;
  for (let i = 0; i < samples.length; i++) { prev = prev + alpha * (samples[i] - prev); lp[i] = prev; }

  const hops = Math.max(1, Math.round((samples.length / sampleRate) * hopsPerSecond));
  const env = normalize(Array.from(rmsEnvelope(lp, hops)));
  const flux = env.map((v, i) => Math.max(0, v - (env[i - 1] ?? v)));

  const onsets = [];
  let lastT = -Infinity;
  for (let i = 1; i < flux.length - 1; i++) {
    const t = i / hopsPerSecond;
    if (flux[i] < floor) continue;
    if (flux[i] < flux[i - 1] || flux[i] < flux[i + 1]) continue; // local peak only
    if (t - lastT < minGapSec) continue;                          // debounce
    onsets.push({ t: +t.toFixed(3), strength: +flux[i].toFixed(3) });
    lastT = t;
  }
  return onsets;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run tests/analyze.test.js`
Expected: PASS (6 tests)

- [ ] **Step 5: Create `src/dev/analyze-cli.js`**

```js
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
```

- [ ] **Step 6: Add the `analyze` npm script**

In `package.json`, add to `"scripts"` (after `"selfcheck"`):

```json
    "analyze": "node src/dev/analyze-cli.js"
```

- [ ] **Step 7: Run it against the real clip and sanity-check the output**

Run: `npm run analyze -- audio/seraph-clip.mp3`
Expected: exits 0, prints a duration near 90s and a non-empty onset list,
writes `public/score-seed.json`. (This confirms the tool works end-to-end on
real audio — Task 3 uses this same tool's output, already run once during
planning, to derive its exact curve numbers below.)

- [ ] **Step 8: Commit**

```bash
git add src/dev/analyze.js tests/analyze.test.js src/dev/analyze-cli.js package.json public/score-seed.json
git commit -m "Add kick onset detection tool"
```

---

### Task 3: Re-author the wake curve against real onsets

**Files:**
- Modify: `src/score-data.js`

**Interfaces:**
- Consumes: nothing new.
- Produces: same shape as before (`score.duration: number`,
  `score.wake: {t,v}[]`) — only the data changes, not the shape, so
  `src/score.js`/`src/main.js` need no changes.

**Context:** Task 2's tool was already run once against
`audio/seraph-clip.mp3` during planning. Real results: duration 90.00s; a quiet
intro (0-16s, energy 0.08→0.52); energy rising and reaching a first plateau
around 20-24s (~0.55-0.59); a sustained, fluctuating high-energy midsection from
~32s to ~84s; a fade-out from 84s to 90s (energy drops from 0.31 to 0.19). The
strongest 8 kick onsets in chronological order: 42.82s, 48.35s, 53.8s, 60.7s,
61.66s, 72.37s, 74.39s, 78.52s. The curve below encodes: dormant through the
quiet intro, building through the energy rise, then a distinct upward "surge"
bracketing each of those 8 real hits (expressed as a steeper segment between a
point just before and a point just after each onset — never a dip, per the
Global Constraints), reaching fully awake (1.0) right after the last strong hit
at 78.52s, and holding at 1.0 through the fade-out and beyond (matching the
"never resets" rule — the outro's energy drop doesn't undo the wake).

- [ ] **Step 1: Replace the wake curve in `src/score-data.js`**

Read the current file first, then replace its contents with:

```js
// Authored score. The wake curve is derived from real analysis of
// audio/seraph-clip.mp3 (see src/dev/analyze-cli.js -> public/score-seed.json):
// a quiet 0-16s intro, energy rising to a plateau by ~24s, sustained chaotic
// midsection 32-84s, fade-out 84-90s. Points bracket the 8 strongest detected
// kick onsets (42.82, 48.35, 53.8, 60.7, 61.66, 72.37, 74.39, 78.52s) with a
// steeper "surge" segment right at each hit — strictly non-decreasing
// throughout (never a dip), reaching fully awake just after the last strong
// hit and holding through the fade-out.
export const score = {
  duration: 90,
  wake: [
    { t: 0,     v: 0.00 },
    { t: 8,     v: 0.04 },
    { t: 15.5,  v: 0.10 },
    { t: 16.4,  v: 0.22 }, // energy first crosses the sustained-high threshold
    { t: 20,    v: 0.38 },
    { t: 24,    v: 0.50 }, // first energy plateau
    { t: 32,    v: 0.58 }, // sustained high energy established
    { t: 42.4,  v: 0.62 },
    { t: 43.2,  v: 0.70 }, // surge: onset at 42.82 (strongest overall, 0.528)
    { t: 47.9,  v: 0.72 },
    { t: 48.8,  v: 0.78 }, // surge: onset at 48.35
    { t: 53.4,  v: 0.79 },
    { t: 54.2,  v: 0.85 }, // surge: onset at 53.8
    { t: 60.3,  v: 0.86 },
    { t: 62.1,  v: 0.91 }, // surge: covers the close 60.7/61.66 pair
    { t: 71.9,  v: 0.92 },
    { t: 74.9,  v: 0.96 }, // surge: covers the close 72.37/74.39 pair
    { t: 78.1,  v: 0.97 },
    { t: 79.0,  v: 1.00 }, // fully awake, right after the final strong hit at 78.52
    { t: 90,    v: 1.00 }, // holds through the fade-out — never resets
  ],
};
```

- [ ] **Step 2: Start the dev server in the background**

Run: `npm run dev`

- [ ] **Step 3: Screenshot-verify across the real build**

Run: `npm run shoot -- 0 8 16 24 32 43 49 54 62 75 79 90`
Expected: `shots/t_000.png` .. `shots/t_090.png` written, no `PAGE ERROR`/
`PAGE EXCEPTION`.

- [ ] **Step 4: Run the automated self-check**

Run: `npm run selfcheck -- shots/t_000.png shots/t_008.png shots/t_016.png shots/t_024.png shots/t_032.png shots/t_043.png shots/t_049.png shots/t_054.png shots/t_062.png shots/t_075.png shots/t_079.png shots/t_090.png`
Expected: exit 0, no warnings.

- [ ] **Step 5: Visually confirm the build tracks the real curve**

Open the PNGs. Confirm: `t_000`/`t_008` read as clearly more dormant/dim than
Milestone 5's old flat-ramp equivalents at those times (the new curve is much
lower this early — 0.00-0.04 vs the old linear ramp's ~0.0-0.09); `t_016`
onward shows the build actually underway; `t_079`/`t_090` read as fully awake
and hold at the same intensity (confirms no regression). This is verifying the
*data* changed correctly, not new shader behavior — Milestone 5's visual
mapping from `uProgress` to brightness/speed/etc. is unchanged and already
verified.

- [ ] **Step 6: Stop the dev server**

- [ ] **Step 7: Commit**

```bash
git add src/score-data.js
git commit -m "Re-author wake curve against the clip's real kick onsets"
```

---

### Task 4: Final delivery ritual

**Files:**
- None created — verification and packaging only.

- [ ] **Step 1: Run the full test suite**

Run: `npx vitest run`
Expected: PASS, 18 tests total (5 score + 4 clock + 3 audioClock + 6 analyze).

- [ ] **Step 2: Build the single-file bundle**

Run: `npm run build`
Expected: exits 0; `dist/index.html` created. Note: this build now embeds the
~1.3MB mp3 as base64, so the output will be several times larger than
Milestones 1-5's ~7KB builds (gaia-breaks' equivalent audio-embedded build was
several MB) — that size jump is expected, not a regression.

- [ ] **Step 3: Confirm the build is self-contained**

Run: `grep -c 'src="/src' dist/index.html`
Expected: `0`.

- [ ] **Step 4: Report back to the user**

Show the screenshots from Task 3 and summarize what changed. Do not copy
`dist/index.html` to Downloads or push anything — only do that when the user
asks. Remind them that with this task, all six milestones from the original
design spec are complete.
