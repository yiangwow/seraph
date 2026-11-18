# seraph — Milestone 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each closed eye on the wheels wake and blink independently — a brief,
asynchronous "glance" on its own seeded clock, never synchronized with the others —
per the design spec's Milestone 2.

**Architecture:** Single-file change to `src/gl/shaders/angel.frag`'s existing eye
block. No new files, no new uniforms — reuses `common.glsl`'s `hash()` (already
injected) to seed each eye's independent speed and phase, same technique gaia-breaks'
`maw.frag` uses for the ophanim's eye-wake (`hash(vec2(cell,fr))`-seeded phase).

**Tech Stack:** Same as Milestone 1 (Vite, raw WebGL2 GLSL, Playwright `shoot.js`
screenshots). No vitest changes — this is a pure shader edit, verified visually.

## Global Constraints

(Same as Milestone 1's plan, still binding)
- Flat 2D SDF shader language only — no raymarched 3D.
- Dark background throughout.
- Idle motion is driven by `uTime`, independent of `uProgress` — nothing may be
  static. This task is itself in service of that constraint (closed eyes were
  static in Milestone 1; this fixes that).
- Every visual change is screenshot-verified with `node src/dev/shoot.js` before
  being shown to the user.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- Do not push to any remote or create the public repo — that only happens when the
  user explicitly says so.

## Scope

This plan implements **Milestone 2 only** (independent eye blinking/waking) from
`docs/superpowers/specs/2026-07-01-seraph-design.md`. Wings (Milestone 3), halo
(Milestone 4), wake-wiring (Milestone 5), and music-lock (Milestone 6) are not in
scope here.

---

### Task 1: Independent eye wake/blink cycle

**Files:**
- Modify: `src/gl/shaders/angel.frag:35-46` (the eye-rendering block inside the
  wheel loop)

**Interfaces:**
- Consumes: `hash(vec2)` from `common.glsl` (already injected via `// __COMMON__`,
  no import needed — it's textually spliced into the shader source before compile).
- Produces: no new exported interface — this is a leaf visual change. `uTime`,
  `uProgress`, `uAspect` uniform names are unchanged.

- [ ] **Step 1: Replace the eye block in `src/gl/shaders/angel.frag`**

Find this existing block (currently lines 35-46, inside the `for (int w = 0; w < 3; w++)` loop, after the spokes code and before the loop's closing `}`):

```glsl
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
```

Replace it with:

```glsl
    // eyes riding the rim, sparse and evenly spaced — each wakes and blinks on its
    // own independent, seeded clock: mostly shut, with brief asynchronous glances.
    // Never synchronized, never fully static (Milestone 2).
    float eyeN = 6.0 + 2.0*fw;
    float cell = floor(aq/6.2831*eyeN + 0.5);
    float ca = cell/eyeN*6.2831 + spin;
    vec2 ec = vec2(cos(ca), sin(ca)*squash) * rr;
    vec2 tangent = normalize(vec2(-sin(ca)*squash, cos(ca)));
    vec2 radial  = normalize(vec2(cos(ca), sin(ca)*squash));
    vec2 lp = vec2(dot(p-ec, tangent), dot(p-ec, radial));

    float seed = hash(vec2(cell + fw*97.0, fw*13.0 + 5.0));
    float speed = 0.045 + 0.05*seed;
    float phase = seed*6.2831;
    float cyc = 0.5 + 0.5*sin(uTime*speed + phase);
    float open = smoothstep(0.80,0.98,cyc); // brief, asynchronous glances; 0 most of the time

    float eyeD = length(lp/vec2(0.020, 0.0035 + 0.0075*open)); // lid parts as it opens
    float eyeM = smoothstep(1.0,0.7,eyeD);
    col = mix(col, vec3(0.68,0.60,0.45), eyeM*(0.8-0.2*open)); // shut lid, faint gleam
    col += vec3(0.5,0.4,0.25) * smoothstep(0.05,0.0,abs(eyeD-1.0)) * 0.3; // lid seam glow
    // amber iris glints through as the lid parts
    vec2 pup = lp / vec2(0.020, 0.0075*open + 1e-4);
    col = mix(col, vec3(0.78,0.55,0.22), smoothstep(1.0,0.5,length(pup)) * eyeM * open);
```

- [ ] **Step 2: Start the dev server in the background**

Run: `npm run dev` (background/separate terminal)
Expected: `Local: http://localhost:5173/` printed, no errors.

- [ ] **Step 3: Screenshot-verify across enough time to catch async blinks**

Run: `npm run shoot -- 0 30 60 90 150 220 300`
Expected: `shots/t_000.png` .. `shots/t_300.png` written, no `PAGE ERROR`/
`PAGE EXCEPTION` lines printed.

(Note: with `speed` in `[0.045, 0.095]` rad/s, one eye's blink period is roughly
`2*PI/speed` ≈ 66–140s, so a 300s spread across 7 samples should catch at least a
few of the ~30 eyes mid-glance, at different rings and different moments — not all
of them will be caught open in any single frame, which is correct.)

- [ ] **Step 4: Visually confirm the screenshots**

Open the PNGs in `shots/`. Confirm: eyes are mostly shut across all frames (the
dormant read from Milestone 1 is preserved); at least one frame shows at least one
eye with a visibly parted lid and a faint amber iris glint, and it is NOT the same
eye/ring in every frame that's open (confirms independence, not a synchronized
pulse); nothing else regressed (still 3 concentric wheels, dark background, spokes
visible). If every eye blinks in unison, or none ever appear to open across all 7
samples, fix the shader (check the `hash()`/`speed`/`phase` math) before proceeding
— do not show unverified visuals to the user.

- [ ] **Step 5: Stop the dev server**

Stop the background `npm run dev` process.

- [ ] **Step 6: Commit**

```bash
git add src/gl/shaders/angel.frag
git commit -m "Give each eye an independent wake/blink cycle"
```
