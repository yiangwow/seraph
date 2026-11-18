# seraph — design

Date: 2026-07-01
Status: approved

## Context

Sister piece to `~/gaia-breaks` (the "Born to be a star" audiovisual piece). Where
gaia-breaks is a four-movement narrative arc locked to a track, seraph is a single,
fixed scene: a biblically accurate angel — ophanim/throne in spirit — centered,
alive, awe and dread rather than a character. Track: an ~85s clip (2:45–4:10) from
the YouTube video "Heavenly breakcore mix" — the user will supply the trimmed clip
as an mp3 in `audio/` (gitignored, never committed, same as gaia-breaks' track).
Audio is in scope from the start of the wake-arc work; the wake arc's duration and
eventual eye/wing timing are authored against this clip's real kick onsets, same
as gaia-breaks' music-lock, rather than free-running.

Reuses gaia-breaks' toolchain and patterns: Vite + `vite-plugin-singlefile`, raw
WebGL2 fullscreen fragment shaders, a shared `common.glsl`, the `shoot.js`
Playwright screenshot tool, a dev scrubber, and vitest for pure logic. Simplified
relative to gaia-breaks wherever gaia-breaks' complexity exists to serve multi-movement
crossfading that seraph doesn't have (one scene, no movements, no corruption pass).

## Visual target

One scene, flat 2D SDF language (no raymarched 3D — gaia-breaks tried that for its
Titan and reverted it; matching an established flat language matters more than
extra dimensionality). Dark background. Components, layered:

- **Wheels within wheels** — interlocking rings, each rotating at its own rate/axis
  (in 2D this reads as independent rotation speed + squash, not literal 3D axes)
- **Rings of eyes** — mounted on the wheels, sparse (not a swarm), each blinking and
  waking on its own independent clock
- **Many wings** — layered around/behind the wheels, breathing and folding
- **A burning halo**

Nothing is static: idle micro-motion everywhere, even after the piece reaches
"fully awake." Restrained glitch, if any — gaia-breaks' lesson was that heavy
datamosh/glitch reads as noise, not dread.

## Wake arc

`uProgress` is sampled from an authored curve (`score-data.js`, piecewise-linear
`[{t,v}]`) against the master clock: climbs 0→1 over the clip's ~85s duration, then
clamps at 1 (holds through any trailing seconds if the clip runs slightly longer).
At `uProgress` = 1 the angel is "fully awake" and simply breathes/idles
indefinitely — it does not reset or loop. Idle motion (blinking, breathing, wheel
rotation) is driven by `uTime`, independent of `uProgress`, so the piece is alive
before, during, and after the wake build.

Build order stays the same regardless of when the audio file actually lands:
milestones 1–4 (shapes, blinking, wings, halo) are screenshot-verified using the
wall-clock `clock.js` placeholder, since they don't need real audio to look right.
Once the user drops the trimmed clip into `audio/`, swap to a real `audioClock.js`
(identical interface to `clock.js`), run the onset-extraction tooling, and
re-author the wake/eye/wing curves against the clip's actual kick onsets — same
upgrade path gaia-breaks used for music-lock.

## Architecture

Reused near-verbatim from gaia-breaks:
- `vite.config.js`, `package.json` (`dev`/`build`/`test`/`shoot` scripts), vitest
- `src/gl/renderer.js` — generic WebGL2 compile/draw helper; no scene-specific
  logic, so no changes needed
- `src/gl/shaders/fullscreen.vert`, `src/gl/shaders/common.glsl` (hash/noise)
- `src/dev/shoot.js`, `src/dev/scrubber.js` — same shape, adapted per below
- `src/dev/analyze.html`, `src/dev/analyze-cli.js` — reused once the clip lands,
  to extract kick onsets from the mp3 into a seed JSON, same as gaia-breaks

Simplified for a single scene (no movement blending/corruption):
- `src/gl/scenes.js` — one fullscreen draw per frame of a single shader
  (`angel.frag`) with `uTime`/`uProgress`/`uAspect` uniforms. No multi-texture
  compositing, no crossfade blend.
- No `ui/uiLayer.js` — this piece has no diegetic game UI.
- `src/score.js` / `src/score-data.js` — kept as concept and name (mirrors
  gaia-breaks' "architect exactly like gaia-breaks" instruction), slimmed to just
  the wake curve. `score-data.js` authors the `[{t,v}]` wake curve; `score.js`
  samples it with the same `sampleCurve` used in gaia-breaks. Designed to grow
  additional authored curves (per-part timing for wings/halo) without restructuring.
- `src/clock.js` — new. Same interface as gaia-breaks' `audioClock.js`
  (`.time`, `.duration`, `.isPlaying`, `.play()`), backed by wall-clock
  (`performance.now()`-based) instead of an `<audio>` element. Swapping to a real
  audio clock later is a one-line change in `main.js`.

New/adapted:
- `src/gl/shaders/angel.frag` — the scene, single pass, built incrementally (see
  Milestones).
- `src/dev/shoot.js` — same screenshot-at-timestamps approach, but seeks via a
  `window.__seraph.setTime(t)` hook on `clock.js` instead of setting
  `<audio>.currentTime` (there is no audio element yet).

## Data flow

`main.js` loop: `clock.time` → `wake = sampleScore(score, clock.time)` (clamped
0..1) → `scenes.frame({ uTime: clock.time, uProgress: wake, uAspect })` → single
draw call to screen.

## Testing

vitest on `sampleCurve`/`score.js` only — pure logic, no shader testing (visuals
are verified by screenshot, not by test). Mirrors gaia-breaks' `score.test.js`.

## Milestones (build order, screenshot-verify each before moving on)

1. Scaffold (toolchain, `clock.js`, `score.js`/`score-data.js`, empty canvas) + a
   first **dormant** angel: wheels + a few closed eyes. Show screenshots.
2. Eyes blink/wake independently (per-eye phase seeded like gaia-breaks'
   `hash(vec2(cell, ring))` pattern in `maw.frag`).
3. Wings: multiple, breathing/folding.
4. Burning halo.
5. Wire all parts to `uProgress` for the dormant→awake build; confirm idle
   micro-motion (`uTime`-driven) is present at every stage, not just at rest states.
6. Once the trimmed clip exists in `audio/`: swap `clock.js` → `audioClock.js`,
   run onset extraction, re-author wake/eye/wing curves against the clip's real
   kicks, screenshot-verify against those exact timestamps.

## Delivery ritual

`npx vitest run` → `npm run build` → screenshot-verify with `shoot.js` at relevant
timestamps → copy `dist/index.html` to
`/mnt/c/Users/computer/Downloads/seraph.html` when asked → commit as
the owner's git identity, no Co-Authored-By → feature branch, push to a
new public repo `yiangwow/seraph` only when explicitly told to.

## Out of scope (for now)

- Multi-scene/movement system (this is one scene, permanently, unless later
  explicitly expanded)
- Diegetic UI overlay
