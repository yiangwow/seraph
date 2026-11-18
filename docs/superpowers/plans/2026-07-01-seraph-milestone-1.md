# seraph — Milestone 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the seraph project (toolchain + minimal render pipeline) and render
the first **dormant** angel — wheels within wheels, a few closed eyes — as a
screenshot-verified WebGL2 fullscreen shader.

**Architecture:** Vite + `vite-plugin-singlefile` project mirroring `~/gaia-breaks`.
A single fullscreen fragment shader (`angel.frag`) is driven each frame by
`uTime`/`uProgress`/`uAspect`, where `uProgress` comes from sampling an authored
wake curve against a wall-clock stand-in (`clock.js`) with the same interface
gaia-breaks' `audioClock.js` uses, so it swaps for a real audio clock later without
touching `main.js`'s shape.

**Tech Stack:** Vite 5, vitest 2, Playwright (`shoot.js` screenshots), raw WebGL2
(no Three.js/other GL library), vanilla JS (no framework).

## Global Constraints

- Flat 2D SDF shader language only — no raymarched 3D.
- Dark background throughout.
- `uProgress` climbs 0→1 over the clip's duration and clamps at 1 — it never resets
  or loops.
- Idle motion (rotation, blinking, breathing) is driven by `uTime`, independent of
  `uProgress` — nothing may be static, even before or after the wake build.
- Every visual change is screenshot-verified with `node src/dev/shoot.js` before
  being shown to the user.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- Single self-contained `dist/index.html` is the build output (via
  `vite-plugin-singlefile`); nothing external at runtime.
- Do not push to any remote or create the public repo — that only happens when the
  user explicitly says so.

## Scope

This plan implements **Milestone 1 only**, from the approved design spec
(`docs/superpowers/specs/2026-07-01-seraph-design.md`): scaffold + a first dormant
angel (wheels + a few closed eyes), screenshot-verified. Milestones 2–6 (blinking,
wings, halo, wake-wiring, music-lock) are deliberately not planned here — this is
visual/creative work that the design spec itself says to screenshot-verify and
iterate on with the user between each step, so pre-writing their shader code now
would just be guessing ahead of feedback. Once Milestone 1's screenshots are
reviewed, run brainstorming/writing-plans again for the next milestone.

---

### Task 1: Branch, project scaffold & tooling

**Files:**
- Create: `package.json`
- Create: `vite.config.js`
- Create: `.gitignore`
- Create: `index.html`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an installable Vite project with scripts `dev`, `build`, `preview`,
  `test`, `shoot`; `index.html` with a `#gl` canvas and
  `<script type="module" src="/src/main.js">` (later tasks create `main.js`).

- [ ] **Step 1: Create a feature branch**

Run: `git checkout -b milestone-1-scaffold`
Expected: `Switched to a new branch 'milestone-1-scaffold'`

- [ ] **Step 2: Create `package.json`**

```json
{
  "name": "seraph",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "shoot": "node src/dev/shoot.js"
  },
  "devDependencies": {
    "playwright": "^1.61.0",
    "vite": "^5.4.0",
    "vite-plugin-singlefile": "^2.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 3: Create `vite.config.js`**

```js
import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';

export default defineConfig(({ command }) => ({
  plugins: command === 'build' ? [viteSingleFile()] : [],
  build: { assetsInlineLimit: 100000000, cssCodeSplit: false },
}));
```

- [ ] **Step 4: Create `.gitignore`**

```
node_modules/
dist/
audio/
shots/
```

- [ ] **Step 5: Create `index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>seraph</title>
  <style>
    html,body{margin:0;height:100%;background:#000;overflow:hidden;}
    #stage{position:fixed;inset:0;}
    #gl{width:100%;height:100%;display:block;}
  </style>
</head>
<body>
  <div id="stage"><canvas id="gl"></canvas></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 6: Install dependencies**

Run: `npm install`
Expected: exits 0; `node_modules/.bin/vite` exists.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json vite.config.js .gitignore index.html
git commit -m "Scaffold seraph project"
```

---

### Task 2: Wake-curve score module

**Files:**
- Create: `tests/score.test.js`
- Create: `src/score.js`
- Create: `src/score-data.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `sampleCurve(points: {t:number,v:number}[], t: number): number` and
  `sampleScore(score: {wake: {t:number,v:number}[]}, t: number): number` from
  `src/score.js`; `score: { duration: number, wake: {t:number,v:number}[] }` from
  `src/score-data.js`. Task 4's `main.js` imports both.

- [ ] **Step 1: Write the failing tests**

Create `tests/score.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { sampleCurve, sampleScore } from '../src/score.js';

describe('sampleCurve', () => {
  const pts = [{ t: 0, v: 0 }, { t: 10, v: 1 }, { t: 20, v: 0 }];
  it('clamps before first and after last point', () => {
    expect(sampleCurve(pts, -1)).toBe(0);
    expect(sampleCurve(pts, 99)).toBe(0);
  });
  it('linearly interpolates between points', () => {
    expect(sampleCurve(pts, 5)).toBeCloseTo(0.5);
    expect(sampleCurve(pts, 15)).toBeCloseTo(0.5);
  });
  it('returns exact value at a knot', () => {
    expect(sampleCurve(pts, 10)).toBe(1);
  });
  it('handles a single-point curve as a constant', () => {
    expect(sampleCurve([{ t: 5, v: 0.7 }], 0)).toBe(0.7);
    expect(sampleCurve([{ t: 5, v: 0.7 }], 100)).toBe(0.7);
  });
});

describe('sampleScore', () => {
  it('samples the wake curve at time t and clamps at the end', () => {
    const score = { wake: [{ t: 0, v: 0 }, { t: 60, v: 1 }] };
    expect(sampleScore(score, 0)).toBe(0);
    expect(sampleScore(score, 30)).toBeCloseTo(0.5);
    expect(sampleScore(score, 60)).toBe(1);
    expect(sampleScore(score, 999)).toBe(1); // holds "fully awake", never resets
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run tests/score.test.js`
Expected: FAIL — `Cannot find module '../src/score.js'`

- [ ] **Step 3: Implement `src/score.js`**

```js
/** Piecewise-linear sample of [{t,v},...] sorted by t. Clamps outside the range. */
export function sampleCurve(points, t) {
  if (points.length === 0) return 0;
  if (t <= points[0].t) return points[0].v;
  const last = points[points.length - 1];
  if (t >= last.t) return last.v;
  for (let i = 1; i < points.length; i++) {
    if (t <= points[i].t) {
      const a = points[i - 1], b = points[i];
      const f = (t - a.t) / (b.t - a.t);
      return a.v + (b.v - a.v) * f;
    }
  }
  return last.v;
}

/** Sample the wake curve at time t, returning 0..1 progress. */
export function sampleScore(score, t) {
  return sampleCurve(score.wake, t);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run tests/score.test.js`
Expected: PASS (5 tests)

- [ ] **Step 5: Create `src/score-data.js`**

```js
// Authored score. The wake curve is a placeholder — 0..1 over the clip's real
// ~90.04s duration — until real kick onsets are extracted from audio/seraph-clip.mp3
// (Milestone 6: onset-extraction tooling + re-authoring).
export const score = {
  duration: 90,
  wake: [
    { t: 0, v: 0 },
    { t: 90, v: 1 },
  ],
};
```

- [ ] **Step 6: Commit**

```bash
git add tests/score.test.js src/score.js src/score-data.js
git commit -m "Add wake-curve score module"
```

---

### Task 3: Wall-clock module

**Files:**
- Create: `tests/clock.test.js`
- Create: `src/clock.js`

**Interfaces:**
- Consumes: nothing.
- Produces: `createClock(): { time: number, duration: number (settable),
  isPlaying: boolean, play(): Promise<void>, pause(): void, seek(t: number): void }`
  from `src/clock.js`. Same shape as gaia-breaks' `audioClock.js`, so `main.js`
  (Task 4) and a future real audio clock are interchangeable. Uses `Date.now()`,
  not `performance.now()`, so it fakes cleanly under `vi.useFakeTimers()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/clock.test.js`:

```js
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createClock } from '../src/clock.js';

describe('createClock', () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(0); });
  afterEach(() => { vi.useRealTimers(); });

  it('starts paused at time 0', () => {
    const clock = createClock();
    expect(clock.time).toBe(0);
    expect(clock.isPlaying).toBe(false);
  });

  it('advances time while playing', async () => {
    const clock = createClock();
    await clock.play();
    vi.advanceTimersByTime(2500);
    expect(clock.time).toBeCloseTo(2.5, 1);
  });

  it('freezes time on pause', async () => {
    const clock = createClock();
    await clock.play();
    vi.advanceTimersByTime(1000);
    clock.pause();
    const frozen = clock.time;
    vi.advanceTimersByTime(1000);
    expect(clock.time).toBe(frozen);
    expect(clock.isPlaying).toBe(false);
  });

  it('seek clamps to [0, duration] and preserves playing state', () => {
    const clock = createClock();
    clock.duration = 10;
    clock.seek(5);
    expect(clock.time).toBe(5);
    clock.seek(999);
    expect(clock.time).toBe(10);
    clock.seek(-5);
    expect(clock.time).toBe(0);
    expect(clock.isPlaying).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run tests/clock.test.js`
Expected: FAIL — `Cannot find module '../src/clock.js'`

- [ ] **Step 3: Implement `src/clock.js`**

```js
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

/** Wall-clock-backed stand-in for gaia-breaks' audioClock.js — same interface,
 * no <audio> element. Swap for a real audio-backed clock once a track exists in
 * audio/; callers never need to change shape. */
export function createClock() {
  let offset = 0;       // seconds accumulated while paused or seeked
  let startedAt = null; // Date.now() ms when playing began, or null if paused
  let duration = Infinity;

  function now() {
    return startedAt === null ? offset : offset + (Date.now() - startedAt) / 1000;
  }

  return {
    get time() { return clamp(now(), 0, duration); },
    get duration() { return duration; },
    set duration(d) { duration = d; },
    get isPlaying() { return startedAt !== null; },
    async play() { if (startedAt === null) { offset = clamp(offset, 0, duration); startedAt = Date.now(); } },
    pause() { if (startedAt !== null) { offset = now(); startedAt = null; } },
    seek(t) { offset = clamp(t, 0, duration); if (startedAt !== null) startedAt = Date.now(); },
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run tests/clock.test.js`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/clock.test.js src/clock.js
git commit -m "Add wall-clock stand-in module"
```

---

### Task 4: Dormant angel scene (wheels + closed eyes)

**Files:**
- Create: `src/gl/renderer.js`
- Create: `src/gl/shaders/fullscreen.vert`
- Create: `src/gl/shaders/common.glsl`
- Create: `src/gl/shaders/angel.frag`
- Create: `src/gl/scenes.js`
- Create: `src/main.js`
- Create: `src/dev/scrubber.js`
- Create: `src/dev/shoot.js`

**Interfaces:**
- Consumes: `sampleScore`, `score` (Task 2); `createClock` (Task 3).
- Produces: `window.__seraph = { clock, score }` — the hook `shoot.js` and any
  future dev tooling use to seek/read the piece from outside.

- [ ] **Step 1: Copy `src/gl/renderer.js` verbatim from gaia-breaks**

```js
import vertSrc from './shaders/fullscreen.vert?raw';

export function createRenderer(canvas) {
  const gl = canvas.getContext('webgl2', { antialias: false, alpha: false });
  if (!gl) throw new Error('WebGL2 not supported');

  function compile(fragSrc) {
    const prog = gl.createProgram();
    for (const [type, src] of [[gl.VERTEX_SHADER, vertSrc], [gl.FRAGMENT_SHADER, fragSrc]]) {
      const sh = gl.createShader(type);
      gl.shaderSource(sh, src); gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        throw new Error('shader: ' + gl.getShaderInfoLog(sh) + '\n' + src);
      }
      gl.attachShader(prog, sh);
    }
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('link: ' + gl.getProgramInfoLog(prog));
    return prog;
  }

  function createTarget(w, h) {
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { tex, fbo, w, h };
  }

  function draw(prog, setUniforms, target) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target ? target.fbo : null);
    gl.viewport(0, 0, target ? target.w : canvas.width, target ? target.h : canvas.height);
    gl.useProgram(prog);
    if (setUniforms) setUniforms(gl, prog);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  function uni(prog, name) { return gl.getUniformLocation(prog, name); }

  return { gl, canvas, compile, createTarget, draw, uni };
}
```

- [ ] **Step 2: Copy `src/gl/shaders/fullscreen.vert` verbatim from gaia-breaks**

Run: `cp ~/gaia-breaks/src/gl/shaders/fullscreen.vert ~/seraph/src/gl/shaders/fullscreen.vert`
Expected: file copied, exits 0.

- [ ] **Step 3: Copy `src/gl/shaders/common.glsl` verbatim from gaia-breaks**

```glsl
float hash(vec2 p){ return fract(sin(dot(p, vec2(41.3,289.1)))*43758.5453); }
float noise(vec2 p){
  vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  float a=hash(i), b=hash(i+vec2(1,0)), c=hash(i+vec2(0,1)), d=hash(i+vec2(1,1));
  return mix(mix(a,b,f.x), mix(c,d,f.x), f.y);
}
```

- [ ] **Step 4: Write `src/gl/shaders/angel.frag`**

```glsl
#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform float uTime;
uniform float uProgress;
uniform float uAspect;
// __COMMON__
void main(){
  vec2 p = (vUv - 0.5); p.x *= uAspect;
  float r = length(p);
  vec3 col = vec3(0.01, 0.01, 0.02); // dark background

  // WHEELS WITHIN WHEELS — concentric rings, each on its own slow rotation and
  // squash (a 2D stand-in for "a different axis"), interlocking around the core.
  // Counter-rotating and idling purely on uTime so the dormant angel is never
  // static, even before the wake build (uProgress) is wired in (Milestone 5).
  for (int w = 0; w < 3; w++){
    float fw = float(w);
    float rr = 0.18 + 0.10*fw;                            // ring radius, wheels within wheels
    float squash = mix(1.0, 0.55, fract(fw*0.37+0.15));   // each wheel tilted differently
    float spin = uTime*(0.05 + 0.025*fw) * ((mod(fw,2.0)<1.0)?1.0:-1.0); // counter-rotating
    vec2 q = vec2(p.x, p.y/squash);
    float rq = length(q);
    float aq = atan(q.y, q.x) - spin;

    // the rim itself: a thin luminous band
    float rim = smoothstep(0.006,0.0, abs(rq-rr));
    col += vec3(0.55,0.45,0.30) * rim * 0.5;

    // spokes: fine radial ticks around the rim so the rotation reads clearly
    float spokeN = 24.0 + 8.0*fw;
    float spoke = smoothstep(0.985,0.994, cos(aq*spokeN));
    col += vec3(0.35,0.28,0.18) * spoke * rim * 1.4;

    // a few closed eyes riding the rim, sparse and evenly spaced
    float eyeN = 6.0 + 2.0*fw;
    float cell = floor(aq/6.2831*eyeN + 0.5);
    float ca = cell/eyeN*6.2831 + spin;
    vec2 ec = vec2(cos(ca), sin(ca)*squash) * rr;
    vec2 tangent = normalize(vec2(-sin(ca)*squash, cos(ca)));
    vec2 radial  = normalize(vec2(cos(ca), sin(ca)*squash));
    vec2 lp = vec2(dot(p-ec, tangent), dot(p-ec, radial));
    float eyeD = length(lp/vec2(0.020, 0.0035)); // closed: nearly flat lid
    float eyeM = smoothstep(1.0,0.7,eyeD);
    col = mix(col, vec3(0.68,0.60,0.45), eyeM*0.8); // shut lid, faint gleam
    col += vec3(0.5,0.4,0.25) * smoothstep(0.05,0.0,abs(eyeD-1.0)) * 0.3; // lid seam glow
  }

  // core: a dark heart at the centre where the wheels converge, breathing gently
  float core = 0.10 + 0.006*sin(uTime*0.6);
  col *= smoothstep(core, core+0.03, r);
  col += vec3(0.10,0.05,0.03) * smoothstep(0.16,0.0,r) * 0.6;

  o = vec4(col, 1.0);
}
```

- [ ] **Step 5: Write `src/gl/scenes.js`**

```js
import common from './shaders/common.glsl?raw';
import angel from './shaders/angel.frag?raw';

const inject = (src) => src.replace('// __COMMON__', common);

export function createScenes(renderer) {
  const { compile, draw, uni } = renderer;
  const prog = compile(inject(angel));

  function frame({ uTime, uProgress, uAspect }) {
    draw(prog, (g, p) => {
      g.uniform1f(uni(p, 'uTime'), uTime);
      g.uniform1f(uni(p, 'uProgress'), uProgress);
      g.uniform1f(uni(p, 'uAspect'), uAspect);
    }, null);
  }

  return { frame };
}
```

- [ ] **Step 6: Write `src/main.js`**

```js
import { createRenderer } from './gl/renderer.js';
import { createScenes } from './gl/scenes.js';
import { createClock } from './clock.js';
import { sampleScore } from './score.js';
import { score } from './score-data.js';

const SHOOT = location.search.includes('shoot'); // headless screenshot mode

const canvas = document.getElementById('gl');
const dpr = Math.min(devicePixelRatio || 1, 2);
function resize(){ canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr; }
resize(); addEventListener('resize', resize);

const renderer = createRenderer(canvas);
const scenes = createScenes(renderer);
const clock = createClock();
clock.duration = score.duration;
clock.play();

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

- [ ] **Step 7: Write `src/dev/scrubber.js`**

```js
// Dev-only timeline scrubber + live wake-curve editor.
export function mountScrubber({ clock, score }) {
  const bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;bottom:0;left:0;right:0;padding:8px;background:rgba(0,0,0,.7);'
    + 'font:12px monospace;color:#cfe3ff;z-index:50;pointer-events:auto;display:flex;gap:10px;align-items:center;';
  const playBtn = document.createElement('button'); playBtn.textContent = '▶/⏸';
  const seek = document.createElement('input');
  seek.type = 'range'; seek.min = 0; seek.max = 1000; seek.value = 0; seek.style.flex = '1';
  const read = document.createElement('span'); read.style.minWidth = '220px';
  const edit = document.createElement('textarea');
  edit.style.cssText = 'position:fixed;top:8px;right:8px;width:280px;height:160px;background:#0b0b12;color:#9ec3ff;'
    + 'font:11px monospace;z-index:50;pointer-events:auto;';
  edit.value = JSON.stringify(score.wake, null, 1);

  playBtn.onclick = () => (clock.isPlaying ? clock.pause() : clock.play());
  seek.oninput = () => clock.seek((seek.value / 1000) * (clock.duration || 1));
  edit.onchange = () => {
    try { score.wake = JSON.parse(edit.value); } catch (e) { edit.style.borderColor = 'red'; return; }
    edit.style.borderColor = '';
  };

  bar.append(playBtn, seek, read);
  document.body.append(bar, edit);

  setInterval(() => {
    const d = clock.duration || 1;
    if (document.activeElement !== seek) seek.value = (clock.time / d) * 1000;
    read.textContent = `t=${clock.time.toFixed(1)}s / ${d.toFixed(0)}s`;
  }, 100);
}
```

- [ ] **Step 8: Write `src/dev/shoot.js`**

```js
// Headless screenshot tool: loads the dev page, seeks the wall-clock to given
// timestamps, and saves a PNG of each. Usage: node src/dev/shoot.js [t1 t2 ...]
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
await page.waitForFunction(() => window.__seraph && window.__seraph.clock, null, { timeout: 15000 })
  .catch(() => console.log('WARN: __seraph clock not ready'));

for (const t of times) {
  await page.evaluate((tt) => { window.__seraph.clock.seek(tt); }, t);
  await page.waitForTimeout(150);
  const name = `${OUT}/t_${String(Math.round(t)).padStart(3, '0')}.png`;
  await page.screenshot({ path: name });
  console.log('shot', name);
}
await browser.close();
console.log('done');
```

- [ ] **Step 9: Start the dev server in the background**

Run: `npm run dev` (background/separate terminal)
Expected: `Local: http://localhost:5173/` printed, no errors.

- [ ] **Step 10: Screenshot-verify**

Run: `npm run shoot -- 0 20 45 70 90`
Expected: `shots/t_000.png` .. `shots/t_090.png` written, no `PAGE ERROR`/`PAGE EXCEPTION`
lines printed.

- [ ] **Step 11: Visually confirm the screenshots**

Open the PNGs in `shots/`. Confirm: dark background; three concentric rings
visible, each rotated/squashed differently (wheels within wheels); a handful of
closed-eye slits riding the rims (not open pupils); nothing looks frozen/identical
between two different timestamps' screenshots (rotation should have visibly moved).
If something looks wrong (e.g. rings not visible, all black, or a compile error in
the console), fix `angel.frag` before proceeding — do not show these to the user
unverified.

- [ ] **Step 12: Stop the dev server**

Stop the background `npm run dev` process.

- [ ] **Step 13: Commit**

```bash
git add src/gl/renderer.js src/gl/shaders/fullscreen.vert src/gl/shaders/common.glsl \
        src/gl/shaders/angel.frag src/gl/scenes.js src/main.js src/dev/scrubber.js src/dev/shoot.js
git commit -m "Render dormant angel: wheels within wheels + closed eyes"
```

---

### Task 5: Build verification & delivery ritual

**Files:**
- None created — verification only.

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: a verified `dist/index.html` build artifact (gitignored, not committed).

- [ ] **Step 1: Run the full test suite**

Run: `npx vitest run`
Expected: PASS, 9 tests total (5 from `score.test.js`, 4 from `clock.test.js`).

- [ ] **Step 2: Build the single-file bundle**

Run: `npm run build`
Expected: exits 0; `dist/index.html` created.

- [ ] **Step 3: Confirm the build is self-contained**

Run: `grep -c 'src="/src' dist/index.html`
Expected: `0` — no references to `/src/...` paths remain (everything inlined by
`vite-plugin-singlefile`).

- [ ] **Step 4: Report back to the user**

Show the screenshots from Task 4 Step 11 and summarize what was built. Do not copy
`dist/index.html` to Downloads or push anything — only do that when the user asks.
