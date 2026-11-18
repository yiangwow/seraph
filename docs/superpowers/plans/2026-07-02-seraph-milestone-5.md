# seraph — Milestone 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire every visual part (halo, wings, wheels, eyes, core) to `uProgress`
so the angel visibly builds from dormant to fully awake over the wake curve's
duration, per the design spec's Milestone 5 — while every part's `uTime`-driven
idle motion keeps running throughout, never going static at either end.

**Architecture:** Single-file change to `src/gl/shaders/angel.frag`. A local
`wake` variable (`= uProgress`) is introduced once near the top of `main()`.
Every block's brightness/amplitude/speed terms that currently use a fixed
constant get changed to `mix(dormantValue, awakeValue, wake)`, where
`dormantValue` is always non-zero — this is what keeps idle motion alive at
`wake=0` (dim/slow, not absent) instead of just gating effects on/off. No new
uniforms, no changes to `main.js`/`score.js`/`clock.js` — `uProgress` is already
computed and passed in from Milestone 1; this task is purely about the shader
finally consuming it.

**Tech Stack:** Same as prior milestones (Vite, raw WebGL2 GLSL, Playwright
`shoot.js`, `npm run selfcheck`).

## Global Constraints

(Same as prior milestones' plans, still binding)
- Flat 2D SDF shader language only — no raymarched 3D.
- Dark background throughout.
- `uProgress` climbs 0→1 over the clip's duration (currently the 90s wake-curve
  placeholder in `score-data.js`) and clamps at 1 — it never resets or loops.
- Idle motion (rotation, blinking, breathing, flicker) is driven by `uTime`,
  independent of `uProgress` — nothing may be static, at `wake=0`, at `wake=1`,
  or anywhere in between. Every `mix(dormant, awake, wake)` term in this task
  must have a non-zero `dormant` value for exactly this reason — do not use
  `something * wake` alone anywhere, since that goes to exactly zero (static/
  invisible) at `wake=0`.
- Every visual change is screenshot-verified with `node src/dev/shoot.js`, AND
  `npm run selfcheck -- shots/<files>` must show no warnings, before being shown
  to the user.
- **Actually look at the screenshots and judge whether the dormant→awake build
  reads as a real transformation** (dimmer/slower/tighter at low progress vs.
  brighter/faster/fuller at high progress), not just "some numbers changed." This
  project's track record this session: a shader that compiles and technically
  varies is not the same as one that reads correctly — verify by eye.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- Do not push to any remote or create the public repo — that only happens when the
  user explicitly says so.

## Scope

This plan implements **Milestone 5 only** (wake-wiring) from
`docs/superpowers/specs/2026-07-01-seraph-design.md`. Music-lock (Milestone 6,
re-authoring the wake curve against the real track's kick onsets) is not in scope
here — this task only makes the *existing* placeholder wake curve (0→1 over 90s,
in `src/score-data.js`) visibly drive the shader.

---

### Task 1: Wire uProgress through every visual part

**Files:**
- Modify: `src/gl/shaders/angel.frag` (all five blocks: halo, wings, wheels, eyes,
  core)

**Interfaces:**
- Consumes: `uProgress` (existing uniform, already declared and passed by
  `src/gl/scenes.js`/`src/main.js` since Milestone 1 — no plumbing changes
  needed, only shader-side consumption).
- Produces: no new exported interface — leaf visual change.

- [ ] **Step 1: Add the `wake` shorthand**

In `src/gl/shaders/angel.frag`, immediately after `float r = length(p);` (currently
line 10), add:

```glsl
  float wake = uProgress; // 0 = dormant, 1 = fully awake; never resets (Milestone 1 clamps this)
```

- [ ] **Step 2: Wire the halo (lines currently ~13-44)**

Three targeted edits inside the halo block:

Change:
```glsl
    float lick = n1*0.075 + n2*0.030 + n3*0.012;
```
to:
```glsl
    float lick = (n1*0.075 + n2*0.030 + n3*0.012) * mix(0.4, 1.0, wake); // calmer edge dormant, wilder awake
```

Change:
```glsl
    col += flameCol * halo * (0.55 + 0.65*heat) * flicker;
```
to:
```glsl
    col += flameCol * halo * (0.55 + 0.65*heat) * flicker * mix(0.35, 1.0, wake); // dim ember -> full blaze
```

Change:
```glsl
    col += vec3(0.55,0.22,0.06) * outerGlow * 0.20;
```
to:
```glsl
    col += vec3(0.55,0.22,0.06) * outerGlow * 0.20 * mix(0.3, 1.0, wake);
```

- [ ] **Step 3: Wire the wings (the `for (int i = 0; i < 10; i++)` loop)**

Change:
```glsl
    float fold = 0.34*sin(uTime*foldSpeed + foldPhase);        // sweeps in/out, ~20 deg swing
```
to:
```glsl
    float fold = mix(0.15, 0.34, wake)*sin(uTime*foldSpeed + foldPhase); // gathered in dormant, full sweep awake
```

Change:
```glsl
    vec2 tip  = dir * (0.28 + 0.20*breathe);
```
to:
```glsl
    vec2 tip  = dir * (0.28 + mix(0.10, 0.20, wake)*breathe);  // folded close -> spread wide
```

Change:
```glsl
    vec3 wingCol = vec3(0.30,0.22,0.16) * (0.6+0.4*breathe);
    col = mix(col, wingCol, wingM*0.6);
    col += vec3(0.35,0.24,0.15) * smoothstep(0.006,0.0,abs(wing)) * 0.15; // faint edge glow, tight to the shape so it doesn't wash out the taper
```
to:
```glsl
    vec3 wingCol = vec3(0.30,0.22,0.16) * (0.6+0.4*breathe) * mix(0.55, 1.0, wake);
    col = mix(col, wingCol, wingM*0.6);
    col += vec3(0.35,0.24,0.15) * smoothstep(0.006,0.0,abs(wing)) * 0.15 * mix(0.55, 1.0, wake); // faint edge glow, tight to the shape so it doesn't wash out the taper
```

- [ ] **Step 4: Wire the wheels and eyes (the `for (int w = 0; w < 3; w++)` loop)**

Change:
```glsl
    float spin = uTime*(0.05 + 0.025*fw) * ((mod(fw,2.0)<1.0)?1.0:-1.0); // counter-rotating
```
to:
```glsl
    float spin = uTime*(0.05 + 0.025*fw) * mix(0.4, 1.0, wake) * ((mod(fw,2.0)<1.0)?1.0:-1.0); // lazy dormant spin -> full speed awake
```

Change:
```glsl
    col += vec3(0.55,0.45,0.30) * rim * 0.5;
```
to:
```glsl
    col += vec3(0.55,0.45,0.30) * rim * 0.5 * mix(0.5, 1.0, wake);
```

Change:
```glsl
    col += vec3(0.35,0.28,0.18) * spoke * rim * 1.4;
```
to:
```glsl
    col += vec3(0.35,0.28,0.18) * spoke * rim * 1.4 * mix(0.5, 1.0, wake);
```

Change:
```glsl
    float open = smoothstep(0.80,0.98,cyc); // brief, asynchronous glances; 0 most of the time
```
to:
```glsl
    float open = smoothstep(mix(0.90,0.80,wake), mix(0.995,0.90,wake), cyc); // rare brief glances dormant -> open often, longer, awake
```

Change:
```glsl
    col = mix(col, vec3(0.78,0.55,0.22), smoothstep(1.0,0.5,length(pup)) * eyeM * open);
```
to:
```glsl
    col = mix(col, vec3(0.78,0.55,0.22), smoothstep(1.0,0.5,length(pup)) * eyeM * open * mix(0.6, 1.0, wake));
```

- [ ] **Step 5: Wire the core**

Change:
```glsl
  float core = 0.10 + 0.006*sin(uTime*0.6);
  col *= smoothstep(core, core+0.03, r);
  col += vec3(0.10,0.05,0.03) * smoothstep(0.16,0.0,r) * 0.6;
```
to:
```glsl
  float core = 0.10 + (0.006+0.004*wake)*sin(uTime*0.6); // heartbeat deepens as it wakes
  col *= smoothstep(core, core+0.03, r);
  col += vec3(0.10,0.05,0.03) * smoothstep(0.16,0.0,r) * 0.6 * mix(0.6, 1.3, wake);
```

- [ ] **Step 6: Start the dev server in the background**

Run: `npm run dev`
Expected: `Local: http://localhost:5173/` printed, no errors.

- [ ] **Step 7: Screenshot-verify across the wake build**

Run: `npm run shoot -- 0 15 30 45 60 75 90 120`

Expected: `shots/t_000.png` .. `shots/t_120.png` written, no `PAGE ERROR`/
`PAGE EXCEPTION` lines. (`t_000` = fully dormant, `t_090` = the wake curve's
knot where it reaches fully awake per `score-data.js`, `t_120` = past the
curve's end, should look identical in *overall wake intensity* to `t_090` — same
brightness/speed level, just a different instant of the ongoing idle motion —
confirming the "holds awake, never resets" behavior from Milestone 1's clock fix
still applies here.)

- [ ] **Step 8: Run the automated self-check**

Run: `npm run selfcheck -- shots/t_000.png shots/t_015.png shots/t_030.png shots/t_045.png shots/t_060.png shots/t_075.png shots/t_090.png shots/t_120.png`
Expected: exit 0, "All 8 frame(s) look sane" — no blank-render or frozen-frame
warnings. (Frame-to-frame diffs here should generally trend larger through the
0→90s range than the steady-state milestones showed, since both idle motion AND
the wake intensity are changing together — that's expected, not a bug.)

- [ ] **Step 9: Visually confirm the dormant→awake build**

Open the PNGs in `shots/`. Confirm:
- `t_000.png` reads visibly dimmer/slower/more folded-in than `t_090.png`: dimmer
  halo (more ember-red, less blaze), wings held closer to the body, wheels
  spinning more lazily, eyes barely cracking open, a fainter core.
- `t_090.png` reads as the fully awake state: brighter/wilder halo, wings spread
  wide, wheels at full speed, eyes opening more readily, a stronger core pulse.
- Intermediate frames (`t_030`, `t_060`) show a legible progression between
  those two states, not a sudden jump.
- `t_120.png` looks like the same *intensity* level as `t_090.png` (both fully
  awake) — confirms the build doesn't regress or freeze after completing.
- Nothing has gone fully static or invisible in `t_000.png` — idle motion (spin,
  flicker, breathing) must still be visibly present at the dormant end, just
  dimmer/slower, not absent. If any part reads as literally frozen or blank at
  `t_000`, that means a `mix()` floor was set to zero somewhere — find and fix it
  before proceeding.

If the transformation doesn't read clearly, you have latitude to retune the
`mix()` floor/ceiling values (not the overall approach) — use your own visual
judgment, then re-verify (Steps 6-9) before committing.

- [ ] **Step 10: Stop the dev server**

- [ ] **Step 11: Commit**

```bash
git add src/gl/shaders/angel.frag
git commit -m "Wire uProgress through halo, wings, wheels, eyes, and core for the dormant-to-awake build"
```
