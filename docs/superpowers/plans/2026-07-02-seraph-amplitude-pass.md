# seraph — Amplitude Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the user's direct feedback after watching the piece live: "it's very
static, like the circles move but that's it — nothing is happening, there's no
angel here, just some lines." Diagnosed via a contact-sheet of 32 frames spanning
the full ~93s at 3s intervals: the composition is nearly indistinguishable frame
to frame at a glance, even though per-frame pixel diffs are non-zero. Root cause:
nearly every periodic motion in `angel.frag` has a period of 60-300+ seconds, so
within one ~90s viewing most things complete well under one cycle, and the
dormant→awake intensity ranges (e.g. `mix(0.4, 1.0, wake)`) are only ~2x —
nowhere near dramatic enough to read as "waking up." This plan does not change
any shapes or add new elements — it retunes speeds, amplitudes, and wake-ranges
across every existing block so the same composition reads as alive and
transformative over a real ~90s viewing.

**Architecture:** Single-file change to `src/gl/shaders/angel.frag` — numeric
constants only (speeds, amplitudes, `mix()` floor/ceiling pairs). No new
uniforms, no shape/geometry changes, no changes to any other file.

**Tech Stack:** Same as prior milestones (Vite, raw WebGL2 GLSL, Playwright
`shoot.js`, `npm run selfcheck`), plus a new verification technique: a
**contact sheet** — many frames tiled into one grid image via `ffmpeg` — because
that is the method that actually revealed this problem; isolated pairwise
screenshot comparisons did not.

## Global Constraints

(Same as prior milestones' plans, still binding)
- Flat 2D SDF shader language only — no raymarched 3D.
- Dark background throughout.
- `uProgress` climbs 0→1 and clamps at 1 — never resets or loops (unchanged;
  this task only changes how dramatically the shader *responds* to it, not the
  curve itself).
- Idle motion is driven by `uTime`, independent of `uProgress` — nothing may be
  static. Every `mix(dormant, awake, wake)` term must keep a non-zero `dormant`
  floor, same rule as Milestone 5 — this task widens those floors/ceilings for
  more dramatic range, it does not remove the floor.
- **New for this task**: verify with a contact sheet, not just discrete
  before/after screenshots. Isolated pairwise comparisons already passed on the
  current build and still missed a real "feels static" problem — a grid of many
  frames viewed at once is what actually exposes whether the whole arc reads as
  alive.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line.
- Do not push to any remote or create the public repo — that only happens when
  the user explicitly says so.

## Scope

This is a tuning pass, not one of the original six milestones — it's a direct
response to user feedback after watching the finished piece. It touches every
block in `angel.frag` (halo, wings, wheels, eyes, core) but only their numeric
constants, not their structure. Wing shape/character and overall composition
(the other two options the user was offered) are explicitly out of scope for
this pass — only speed/amplitude/range tuning.

---

### Task 1: Widen every motion range and speed up every cycle

**Files:**
- Modify: `src/gl/shaders/angel.frag` (all five blocks)

**Interfaces:**
- Consumes: nothing new.
- Produces: no new exported interface — leaf visual tuning.

- [ ] **Step 1: Widen the halo (currently lines ~14-45)**

Change:
```glsl
    float n1 = noise(dirp*3.5  + vec2(0.0, -uTime*0.5))  - 0.5;
    float n2 = noise(dirp*10.0 + vec2(4.0,  uTime*1.3))  - 0.5;
    float n3 = noise(dirp*26.0 + vec2(9.0,  uTime*2.6))  - 0.5;
    float lick = (n1*0.075 + n2*0.030 + n3*0.012) * mix(0.4, 1.0, wake); // calmer edge dormant, wilder awake
```
to:
```glsl
    float n1 = noise(dirp*3.5  + vec2(0.0, -uTime*0.5))  - 0.5;
    float n2 = noise(dirp*10.0 + vec2(4.0,  uTime*1.3))  - 0.5;
    float n3 = noise(dirp*26.0 + vec2(9.0,  uTime*2.6))  - 0.5;
    float lick = (n1*0.14 + n2*0.055 + n3*0.022) * mix(0.15, 1.0, wake); // barely licking dormant, wildly jagged awake
```

Change:
```glsl
    float flicker = 0.75 + 0.25*sin(uTime*5.3 + n3*8.0); // fast intensity flicker, never static
    col += flameCol * halo * (0.55 + 0.65*heat) * flicker * mix(0.35, 1.0, wake); // dim ember -> full blaze
```
to:
```glsl
    float flicker = 0.65 + 0.45*sin(uTime*6.5 + n3*9.0); // fast intensity flicker, never static
    col += flameCol * halo * (0.55 + 0.65*heat) * flicker * mix(0.12, 1.0, wake); // dim ember -> full blaze
```

Change:
```glsl
    col += vec3(0.55,0.22,0.06) * outerGlow * 0.20 * mix(0.3, 1.0, wake);
```
to:
```glsl
    col += vec3(0.55,0.22,0.06) * outerGlow * 0.20 * mix(0.10, 1.0, wake);
```

- [ ] **Step 2: Widen the wings (the `for (int i = 0; i < 10; i++)` loop)**

Change:
```glsl
    float foldSpeed = 0.035 + 0.035*seed;
    float foldPhase = seed*6.2831;
    float fold = mix(0.15, 0.34, wake)*sin(uTime*foldSpeed + foldPhase); // gathered in dormant, full sweep awake
    float breathe = 0.85 + 0.18*sin(uTime*(0.06+0.03*seed) + seed*4.0);
```
to:
```glsl
    float foldSpeed = 0.12 + 0.10*seed;
    float foldPhase = seed*6.2831;
    float fold = mix(0.05, 0.55, wake)*sin(uTime*foldSpeed + foldPhase); // gathered in dormant, full sweep awake
    float breathe = 0.80 + 0.32*sin(uTime*(0.18+0.12*seed) + seed*4.0);
```

Change:
```glsl
    vec2 tip  = dir * (0.28 + mix(0.10, 0.20, wake)*breathe);  // folded close -> spread wide
    vec2 tangent = vec2(-dir.y, dir.x);
    float curveAmt = 0.05 + 0.09*seed;                         // each wing's own sweep character
    tip += tangent * (curveAmt + 0.02*sin(uTime*foldSpeed*1.7 + foldPhase));
```
to:
```glsl
    vec2 tip  = dir * (0.28 + mix(0.04, 0.32, wake)*breathe);  // folded close -> spread wide
    vec2 tangent = vec2(-dir.y, dir.x);
    float curveAmt = 0.05 + 0.09*seed;                         // each wing's own sweep character
    tip += tangent * (curveAmt + 0.04*sin(uTime*foldSpeed*1.7 + foldPhase));
```

Change:
```glsl
    vec3 wingCol = vec3(0.30,0.22,0.16) * (0.6+0.4*breathe) * mix(0.55, 1.0, wake);
    col = mix(col, wingCol, wingM*0.6);
    col += vec3(0.35,0.24,0.15) * smoothstep(0.006,0.0,abs(wing)) * 0.15 * mix(0.55, 1.0, wake); // faint edge glow, tight to the shape so it doesn't wash out the taper
```
to:
```glsl
    vec3 wingCol = vec3(0.30,0.22,0.16) * (0.6+0.4*breathe) * mix(0.22, 1.0, wake);
    col = mix(col, wingCol, wingM*0.6);
    col += vec3(0.35,0.24,0.15) * smoothstep(0.006,0.0,abs(wing)) * 0.15 * mix(0.22, 1.0, wake); // faint edge glow, tight to the shape so it doesn't wash out the taper
```

- [ ] **Step 3: Widen the wheels (the `for (int w = 0; w < 3; w++)` loop, wheel-rim part)**

Change:
```glsl
    float spin = uTime*(0.05 + 0.025*fw) * mix(0.4, 1.0, wake) * ((mod(fw,2.0)<1.0)?1.0:-1.0); // lazy dormant spin -> full speed awake
```
to:
```glsl
    float spin = uTime*(0.16 + 0.09*fw) * mix(0.22, 1.0, wake) * ((mod(fw,2.0)<1.0)?1.0:-1.0); // lazy dormant spin -> full speed awake
```

Change:
```glsl
    col += vec3(0.55,0.45,0.30) * rim * 0.5 * mix(0.5, 1.0, wake);
```
to:
```glsl
    col += vec3(0.55,0.45,0.30) * rim * 0.5 * mix(0.22, 1.0, wake);
```

Change:
```glsl
    col += vec3(0.35,0.28,0.18) * spoke * rim * 1.4 * mix(0.5, 1.0, wake);
```
to:
```glsl
    col += vec3(0.35,0.28,0.18) * spoke * rim * 1.4 * mix(0.22, 1.0, wake);
```

- [ ] **Step 4: Widen the eyes (same loop, eyes part)**

Change:
```glsl
    float seed = hash(vec2(cell + fw*97.0, fw*13.0 + 5.0));
    float speed = 0.045 + 0.05*seed;
    float phase = seed*6.2831;
    float cyc = 0.5 + 0.5*sin(uTime*speed + phase);
    float open = smoothstep(mix(0.90,0.80,wake), mix(0.995,0.90,wake), cyc); // rare brief glances dormant -> open often, longer, awake
```
to:
```glsl
    float seed = hash(vec2(cell + fw*97.0, fw*13.0 + 5.0));
    float speed = 0.16 + 0.16*seed;
    float phase = seed*6.2831;
    float cyc = 0.5 + 0.5*sin(uTime*speed + phase);
    float open = smoothstep(mix(0.94,0.55,wake), mix(0.995,0.78,wake), cyc); // rare brief glances dormant -> open often, longer, awake
```

Change:
```glsl
    col = mix(col, vec3(0.78,0.55,0.22), smoothstep(1.0,0.5,length(pup)) * eyeM * open * mix(0.6, 1.0, wake));
```
to:
```glsl
    col = mix(col, vec3(0.78,0.55,0.22), smoothstep(1.0,0.5,length(pup)) * eyeM * open * mix(0.28, 1.0, wake));
```

- [ ] **Step 5: Widen the core**

Change:
```glsl
  float core = 0.10 + (0.006+0.004*wake)*sin(uTime*0.6); // heartbeat deepens as it wakes
  col *= smoothstep(core, core+0.03, r);
  col += vec3(0.10,0.05,0.03) * smoothstep(0.16,0.0,r) * 0.6 * mix(0.6, 1.3, wake);
```
to:
```glsl
  float core = 0.10 + (0.012+0.016*wake)*sin(uTime*1.3); // heartbeat deepens and quickens as it wakes
  col *= smoothstep(core, core+0.03, r);
  col += vec3(0.10,0.05,0.03) * smoothstep(0.16,0.0,r) * 0.6 * mix(0.28, 1.7, wake);
```

- [ ] **Step 6: Start the dev server in the background**

Run: `npm run dev`
Expected: `Local: http://localhost:5173/` printed, no errors.

- [ ] **Step 7: Take dense screenshots across the whole clip**

Run: `node src/dev/shoot.js 0 3 6 9 12 15 18 21 24 27 30 33 36 39 42 45 48 51 54 57 60 63 66 69 72 75 78 81 84 87 90 93`
Expected: 32 PNGs written to `shots/`, no `PAGE ERROR`/`PAGE EXCEPTION`.

- [ ] **Step 8: Run the automated self-check**

Run: `npm run selfcheck -- shots/t_000.png shots/t_003.png shots/t_006.png shots/t_009.png shots/t_012.png shots/t_015.png shots/t_018.png shots/t_021.png shots/t_024.png shots/t_027.png shots/t_030.png shots/t_033.png shots/t_036.png shots/t_039.png shots/t_042.png shots/t_045.png shots/t_048.png shots/t_051.png shots/t_054.png shots/t_057.png shots/t_060.png shots/t_063.png shots/t_066.png shots/t_069.png shots/t_072.png shots/t_075.png shots/t_078.png shots/t_081.png shots/t_084.png shots/t_087.png shots/t_090.png shots/t_093.png`
Expected: exit 0, no blank/frozen warnings. (This checks pairwise diffs only — it
already passed on the pre-fix build, so a clean pass here is necessary but NOT
sufficient. Step 9 is the real test.)

- [ ] **Step 9: Build a contact sheet and judge the whole arc at once**

Run:
```bash
cd shots && ffmpeg -y -v error -pattern_type glob -i 't_0*.png' -frames:v 1 -vf "scale=213:120,tile=8x4" contact_sheet.png && cd ..
```

Open `shots/contact_sheet.png` with your Read tool. This is the actual test —
judge it against the ORIGINAL complaint, not against the plan's intent:

- Does brightness/activity clearly trend from dim/sparse (early panels) to
  bright/full (panels around the 42-79s surge range, i.e. roughly panels 15-27
  of the 32-panel grid) — a visible transformation, not a flat wash?
- Do the wheel rim tick-marks/spoke patterns visibly rotate to different
  angular positions between panels that are only 2-3 panels apart (6-9s), not
  just between the first and last panel?
- Do the wing angles/lengths visibly differ panel to panel, not read as the
  same static sunburst shape repeated 32 times?
- Does the halo's jagged silhouette visibly reshape between nearby panels?
- Are lit (amber) eyes visible in noticeably different positions across
  panels, and are there visibly MORE lit eyes in the later/awake panels than
  the earliest/dormant panels?

If the contact sheet still reads as static/repetitive to your own eye — the
same failure mode as before, just possibly less severe — you have latitude to
push the changed constants further in the same direction (faster, wider range)
and re-verify (Steps 6-9) before committing. Do not commit or report success
based on Step 8 (selfcheck) alone — that check already passed on the broken
build and is known to be insufficient on its own for this specific problem.

- [ ] **Step 10: Stop the dev server**

- [ ] **Step 11: Commit**

```bash
git add src/gl/shaders/angel.frag
git commit -m "Widen motion ranges and speed up cycles so the piece reads as alive over a real viewing"
```
