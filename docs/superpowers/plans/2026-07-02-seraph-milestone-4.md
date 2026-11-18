# seraph — Milestone 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a burning halo — a ring of fire at the outer edge of the composition,
flickering and never resting — per the design spec's Milestone 4.

**Architecture:** Single-file addition to `src/gl/shaders/angel.frag`, drawn
*first* (before the wing loop), so it reads as the backmost layer with wings and
wheels layered in front of it. Flame flicker uses `common.glsl`'s existing
`noise()`, sampled off a direction vector (`vec2(cos(ang),sin(ang))`) rather than
raw angle, to avoid the angle-wrap seam artifact already known (and accepted) in
the eye-wheel code — this is a proactive fix, not a regression.

**Tech Stack:** Same as prior milestones (Vite, raw WebGL2 GLSL, Playwright
`shoot.js`, `npm run selfcheck`).

## Global Constraints

(Same as prior milestones' plans, still binding)
- Flat 2D SDF shader language only — no raymarched 3D.
- Dark background throughout — the area between the halo ring and the frame edge,
  and between the halo and the wheels, must stay near-black; only the flame ring
  itself glows.
- Idle motion is driven by `uTime`, independent of `uProgress` — nothing may be
  static. The flame's flicker must be continuous, not a fixed/frozen pattern.
- Every visual change is screenshot-verified with `node src/dev/shoot.js`, AND
  `npm run selfcheck -- shots/<files>` must show no warnings, before being shown
  to the user.
- **Before declaring the task done, actually look at the screenshots yourself and
  judge them as a flame/halo, not just "did something render."** Milestone 3's
  first pass technically compiled and moved but didn't read as wings (looked like
  a sunburst) — the same failure mode applies here: verify the ring reads as
  fire (irregular, flickering, warm-to-hot gradient) and not as a smooth static
  ring or a uniform glow doughnut. If it doesn't read as fire, revise before
  committing — don't rely on "it compiles and passes selfcheck" as sufficient.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- Do not push to any remote or create the public repo — that only happens when the
  user explicitly says so.

## Scope

This plan implements **Milestone 4 only** (burning halo) from
`docs/superpowers/specs/2026-07-01-seraph-design.md`. Wake-wiring (Milestone 5)
and music-lock (Milestone 6) are not in scope here.

---

### Task 1: Burning halo ring

**Files:**
- Modify: `src/gl/shaders/angel.frag` (add the halo block, before the wing loop)

**Interfaces:**
- Consumes: `noise(vec2)` (existing, from `common.glsl`).
- Produces: no new exported interface — leaf visual addition. No uniform names
  change.

- [ ] **Step 1: Add the halo block to `src/gl/shaders/angel.frag`**

Insert this block immediately after the line `vec3 col = vec3(0.01, 0.01, 0.02); // dark background` and before the `// MANY WINGS` comment (so the halo is drawn first, backmost — wings and wheels draw on top of it):

```glsl
  // BURNING HALO — a ring of fire at the outer edge, flickering and never
  // resting; drawn first so wings and wheels layer in front of it. Flame
  // flicker samples noise off a direction vector, not raw angle, so there is
  // no seam at the angle wrap (unlike the eye-wheel noise, which accepts one).
  {
    float ang = atan(p.y, p.x);
    vec2 dirp = vec2(cos(ang), sin(ang));
    float rHalo = 0.56;
    float flick1 = noise(dirp*6.0  + vec2(0.0, uTime*0.35)) - 0.5;
    float flick2 = noise(dirp*17.0 + vec2(5.0, uTime*0.7))  - 0.5;
    float lick = flick1*0.05 + flick2*0.02;
    float band = 0.045 + 0.012*sin(uTime*0.4 + ang*3.0);
    float d = abs(r - (rHalo + lick));
    float halo = smoothstep(band, 0.0, d);

    float heat = noise(dirp*4.0 + vec2(-uTime*0.6, uTime*0.9));
    vec3 flameCol = mix(vec3(0.55,0.12,0.03), vec3(1.0,0.55,0.10), heat);
    flameCol = mix(flameCol, vec3(1.0,0.85,0.35), smoothstep(0.7,1.0,heat));
    col += flameCol * halo * (0.5 + 0.6*heat);

    float outerGlow = smoothstep(rHalo+band+0.10, rHalo, r) * smoothstep(rHalo-band-0.02, rHalo, r);
    col += vec3(0.6,0.25,0.08) * outerGlow * 0.25;
  }

```

- [ ] **Step 2: Start the dev server in the background**

Run: `npm run dev`
Expected: `Local: http://localhost:5173/` printed, no errors.

- [ ] **Step 3: Screenshot-verify**

Run: `npm run shoot -- 0 30 60 90 150 220 300`
Expected: `shots/t_000.png` .. `shots/t_300.png` written, no `PAGE ERROR`/
`PAGE EXCEPTION` lines.

- [ ] **Step 4: Run the automated self-check**

Run: `npm run selfcheck -- shots/t_000.png shots/t_030.png shots/t_060.png shots/t_090.png shots/t_150.png shots/t_220.png shots/t_300.png`
Expected: exit 0, "All 7 frame(s) look sane" — no blank-render or frozen-frame
warnings.

- [ ] **Step 5: Visually confirm the screenshots as a *flame*, not just motion**

Open the PNGs in `shots/`. This is the step most likely to need iteration — judge
it as art, not just as "did it render":
- Does the ring's edge look irregular/licking, like fire, or does it look like a
  smooth, static-edged ring with a color gradient? (The latter is a failure —
  revise the `lick`/noise frequencies or amplitude.)
- Is there visible warm-to-hot color variation around the ring (deep red through
  orange to pale yellow-white), or is it a flat single color? (Flat = failure —
  check the `heat`/`flameCol` mix.)
- Does the flame silhouette visibly change shape between frames (e.g. t_000 vs
  t_090), not just shift in brightness?
- Is the background between the halo and the wheels/wings still near-black (no
  wash-out from `outerGlow`)?
- Do wings and wheels from prior milestones still render correctly on top of the
  halo, unchanged?

If any of these read wrong, adjust the block (frequencies, amplitudes, color
stops) and re-verify (Steps 2-5 again) before committing — do not commit or
report success on a halo that merely "renders something."

- [ ] **Step 6: Stop the dev server**

- [ ] **Step 7: Commit**

```bash
git add src/gl/shaders/angel.frag
git commit -m "Add burning halo ring behind the wheels and wings"
```
