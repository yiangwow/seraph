# seraph — Milestone 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add many wings, layered behind the wheels, each breathing and folding on
its own independent clock — per the design spec's Milestone 3.

**Architecture:** A `capsule(p,a,b,r)` SDF primitive (same technique gaia-breaks'
`maw.frag` uses for its falling-figure limbs) is added to the shared `common.glsl`.
`angel.frag` gains a wing-fan loop, drawn *before* the existing wheel loop so the
wheels visually sit in front of the wing roots (2D draw-order layering). Each wing
is a tapered capsule stroke fanned around the core; per-wing `fold` (sweep angle)
and `breathe` (length pulse) are driven by `uTime` with a `hash()`-seeded phase per
wing, same independent-motion technique Milestone 2 used for the eyes.

**Tech Stack:** Same as Milestones 1-2 (Vite, raw WebGL2 GLSL, Playwright
`shoot.js`). Verification also runs the new `npm run selfcheck` tool
(`src/dev/frame-stats.js`, added this session) as a first-pass automated sanity
check before the qualitative visual look.

## Global Constraints

(Same as prior milestones' plans, still binding)
- Flat 2D SDF shader language only — no raymarched 3D.
- Dark background throughout.
- Idle motion is driven by `uTime`, independent of `uProgress` — nothing may be
  static. Every wing's fold/breathe cycle must be phase-varied (via `hash()`) so
  wings never move in unison.
- Every visual change is screenshot-verified with `node src/dev/shoot.js` before
  being shown to the user. Also run `npm run selfcheck -- shots/<files>` and
  resolve any WARN before treating the render as verified — it catches blank
  renders and frozen/near-identical frame pairs mechanically.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- Do not push to any remote or create the public repo — that only happens when the
  user explicitly says so.

## Scope

This plan implements **Milestone 3 only** (wings) from
`docs/superpowers/specs/2026-07-01-seraph-design.md`. The burning halo (Milestone
4), wake-wiring (Milestone 5), and music-lock (Milestone 6) are not in scope here.

---

### Task 1: Wing fan behind the wheels

**Files:**
- Modify: `src/gl/shaders/common.glsl` (add `capsule()`)
- Modify: `src/gl/shaders/angel.frag` (add the wing loop, before the existing
  wheel loop)

**Interfaces:**
- Consumes: `hash(vec2)` (existing, from `common.glsl`).
- Produces: `capsule(vec2 p, vec2 a, vec2 b, float r): float` in `common.glsl` —
  a new shared primitive later shaders/milestones may also use. No uniform names
  change.

- [ ] **Step 1: Add `capsule()` to `src/gl/shaders/common.glsl`**

Append this function to the end of the file (after `noise()`):

```glsl
float capsule(vec2 p, vec2 a, vec2 b, float r){
  vec2 pa=p-a, ba=b-a; float h=clamp(dot(pa,ba)/dot(ba,ba),0.0,1.0);
  return length(pa-ba*h)-r;
}
```

- [ ] **Step 2: Add the wing loop to `src/gl/shaders/angel.frag`**

Insert this block immediately after the line `vec3 col = vec3(0.01, 0.01, 0.02); // dark background` and before the `// WHEELS WITHIN WHEELS` comment (so wings are drawn first — the wheel loop that follows draws on top of them, giving the "wings layered behind the wheels" look):

```glsl
  // MANY WINGS — layered behind the wheels, breathing and folding, never resting.
  // Flat, curved capsule strokes fanned around the core; each wing breathes
  // (length pulses) and folds (sweep angle drifts) on its own seeded clock, so
  // none of them move in unison (same independent-motion technique as the eyes).
  for (int i = 0; i < 10; i++){
    float fi = float(i);
    float baseA = fi/10.0*6.2831;
    float seed = hash(vec2(fi+41.0, 7.0));
    float foldSpeed = 0.02 + 0.02*seed;
    float foldPhase = seed*6.2831;
    float fold = 0.35*sin(uTime*foldSpeed + foldPhase);        // sweeps in/out
    float breathe = 0.9 + 0.12*sin(uTime*(0.06+0.03*seed) + seed*4.0);

    float a = baseA + fold*0.4;
    vec2 dir = vec2(cos(a), sin(a));
    vec2 root = dir * 0.30;
    vec2 tip  = dir * (0.30 + 0.34*breathe);
    vec2 tangent = vec2(-dir.y, dir.x);
    tip += tangent * 0.10*sin(fold*1.6);                       // gentle swept curve

    float wing = capsule(p, root, tip, 0.018);
    float wingM = smoothstep(0.020,0.0, wing);
    vec3 wingCol = vec3(0.30,0.22,0.16) * (0.6+0.4*breathe);
    col = mix(col, wingCol, wingM*0.55);
    col += vec3(0.35,0.24,0.15) * smoothstep(0.05,0.0,abs(wing)) * 0.25; // faint edge glow
  }

```

The result should read as ten dim, warm-toned feather strokes fanning outward from
just inside the wheels' inner edge to well beyond their outer rim, each slowly
sweeping and pulsing on its own clock, with the wheels and their eyes drawn on top
of the wing roots (unchanged code, now executing after this block).

- [ ] **Step 3: Start the dev server in the background**

Run: `npm run dev`
Expected: `Local: http://localhost:5173/` printed, no errors (a GLSL compile error
here would mean a typo in the capsule call or a missing `__COMMON__` splice —
check `src/gl/scenes.js` still does `src.replace('// __COMMON__', common)` if so).

- [ ] **Step 4: Screenshot-verify**

Run: `npm run shoot -- 0 30 60 90 150 220 300`
Expected: `shots/t_000.png` .. `shots/t_300.png` written, no `PAGE ERROR`/
`PAGE EXCEPTION` lines.

- [ ] **Step 5: Run the automated self-check**

Run: `npm run selfcheck -- shots/t_000.png shots/t_030.png shots/t_060.png shots/t_090.png shots/t_150.png shots/t_220.png shots/t_300.png`
Expected: exit 0, "All 7 frame(s) look sane" — no blank-render or frozen-frame
warnings. If it warns, that's a real signal (e.g. a wing loop with a `uTime`
coefficient of exactly 0, or a botched `hash()` call producing NaN) — fix
`angel.frag` and re-shoot/re-check before proceeding, same as a failing test.

- [ ] **Step 6: Visually confirm the screenshots**

Open the PNGs in `shots/`. Confirm: ten dim feather-like strokes fan out from
behind the wheels (visible extending past the outer ring, roots tucked under it);
wing angles/lengths visibly differ between timestamps (breathing/folding, not
static); wheels and eyes from Milestones 1-2 are unchanged and still drawn on top
where they overlap the wing roots; dark background preserved. If wings look
synchronized (all identical angle/length in every frame) or don't move at all
across the 7 samples, that's a bug even if `selfcheck` passed (mechanical checks
catch blank/frozen frames, not "all ten wings happen to look the same") — fix
before proceeding.

- [ ] **Step 7: Stop the dev server**

- [ ] **Step 8: Commit**

```bash
git add src/gl/shaders/common.glsl src/gl/shaders/angel.frag
git commit -m "Add wing fan behind the wheels, breathing and folding independently"
```
