# seraph — 3D Rendered Video Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a real, pre-rendered video of the seraph piece — proper 3D
geometry, lighting, and materials, GPU-rendered via Blender — after the
real-time flat-2D WebGL version was judged (by the user, after watching it live)
to feel static and to lack real presence ("just some lines, no angel"). No AI
image/video generation anywhere in this pipeline — everything is procedural
geometry, materials, and animation, authored via Blender's Python API and
rendered by Blender's own renderer (Eevee, GPU-accelerated).

**Architecture:** A sequence of Python scripts run headless via
`blender --background --python <script>`, forcing the discrete AMD GPU (not the
Intel iGPU that WSL2's D3D12 passthrough picks by default):
`MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background --python ...`.
The pipeline builds geometry, drives it per-frame with plain Python (not
Blender's driver/expression system — see rationale in Task 3), renders sparse
low-cost preview frames for verification (mirroring the WebGL project's
contact-sheet technique, which is what actually caught the "feels static"
problem there), then does a full render once the preview passes, and finally
muxes the frame sequence with the real audio track via `ffmpeg` into an mp4.

**Tech Stack:** Blender 3.0.1 (installed this session via apt), Eevee render
engine, GPU-accelerated via WSL2 D3D12 passthrough to an AMD Radeon RX 6950 XT
(confirmed working — see Task 0 checkpoint below), `ffmpeg` (already used
throughout this project for onset analysis and contact sheets), Node.js (only
for a small one-time data-export step in Task 2).

## Global Constraints

- **No AI-generated imagery or video anywhere in this pipeline.** All geometry,
  materials, lighting, and animation are procedural/hand-authored via Blender's
  Python API. This was an explicit, direct user requirement after rejecting an
  AI-stills-based alternative.
- **Always force the AMD GPU.** Every Blender invocation in this plan must be
  prefixed `MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD` — omitting it silently falls
  back to the much weaker Intel UHD Graphics 770 iGPU. Verify this per-task
  (see Task 0) rather than assuming it's inherited.
- **Verify with dense multi-frame previews, not isolated pairwise comparisons.**
  The WebGL project's `npm run selfcheck` (pairwise frame diffs) passed on a
  build the user directly experienced as static and lifeless — pairwise diffs
  being non-zero is necessary but nowhere near sufficient to prove something
  "reads as alive" over a real viewing. Every animation-verification step in
  this plan requires building a tiled contact sheet (the same `ffmpeg -vf tile`
  technique already used successfully in the WebGL project) spanning the WHOLE
  duration and actually looking at it, not just checking that frames differ.
- **Wide dynamic range, fast-enough cycles.** The WebGL project's first
  wake-wiring pass used dormant→awake ranges of roughly 2x (e.g.
  `mix(0.4, 1.0, wake)`) and motion periods of 60-300+ seconds — both proved
  far too subtle to read within a ~90s viewing and had to be redone with much
  wider ranges (floors down to ~0.1-0.15) and much faster base speeds (full
  cycles completing in 20-50s, not 100-300s). Apply that lesson from the start
  here — don't repeat the mistake in a new medium.
- **Reuse the already-validated wake curve and real onset data**, don't
  re-derive them. Real analysis of `audio/seraph-clip.mp3` (90.00s duration) is
  already committed at `public/score-seed.json` (37 detected onsets; the 8
  strongest, chronologically: 42.82s/48.35s/53.8s/60.7s/61.66s/72.37s/74.39s/
  78.52s). The hand-authored 20-point wake curve already shipped in
  `src/score-data.js` (strictly non-decreasing, 0→1, surging at those 8 onsets,
  holding at 1.0 from 79.0s through 90s) is the source of truth for wake
  timing — port its exact 20 points, don't re-author new ones, so the 3D
  pipeline's sense of "when the piece wakes up" matches the shipped WebGL
  version and the real track.
- Git authorship for every commit: the owner's git identity, no
  Co-Authored-By line. This is a personal art project; the same rules from
  `docs/superpowers/specs/2026-07-01-seraph-design.md` and this repo's prior
  commits apply.
- Do not push to any remote or create the public repo — that only happens when
  the user explicitly says so.
- The mp3 stays gitignored; render output (`blender/renders/`, frame sequences,
  final video files) should also be gitignored — these are large derived
  binary artifacts, not source.

## Already Done (context for whoever picks this up)

- Blender 3.0.1 installed via `apt install blender mesa-vulkan-drivers
  vulkan-tools mesa-utils`. GPU passthrough confirmed working:
  `MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD glxinfo` reports
  `OpenGL renderer string: D3D12 (AMD Radeon RX 6950 XT)`. Without that env
  var, it silently uses `D3D12 (Intel(R) UHD Graphics 770)` instead — much
  weaker, and the default.
- `blender/build_scene.py` exists and builds: 3 interlocking toruses at
  different Euler-angle tilts ("wheels within wheels" — genuine 3D depth,
  unlike the WebGL version's flat squash-hack), lens-shaped eye geometry set
  into each ring's surface (position/orientation computed via the ring's own
  rotation matrix, so eyes sit flush on the tilted rings), an emissive torus
  halo behind everything, one dim area light for rim shading, and a camera
  using a Track-To constraint aimed at an origin Empty (elevated 3/4 view,
  NOT a straight-on view — the whole composition sits roughly in the XY plane,
  so a camera looking along Y collapses everything edge-on into a blown-out
  line, which is exactly what happened on the first attempt).
- Two renders so far: attempt 1 was badly broken (camera looking edge-on
  through the halo's plane, halo emission strength 6.0 wildly overexposed —
  the render was almost entirely blown-out white). Attempt 2, after
  repositioning the camera via Track-To and dropping halo emission strength to
  1.4, looks genuinely good: the three tilted interlocking rings read with
  real depth and lighting, the halo reads as a proper ring, small amber eye
  points are visible. The user reacted positively ("looking better for sure").
- **Known problem, not yet fixed**: the wings (built as bezier curves with a
  round `bevel_depth` cross-section, cool-gray non-emissive material) read as
  thin gray tentacles/wires, not wings — no flat wing-like silhouette, no warm
  tone. The fix was identified but not yet applied or re-rendered (Task 1
  below has the exact fix).
- No animation exists yet — everything so far is a single static test frame.

---

### Task 0: Environment checkpoint (run first, every session)

Not a code task — a verification gate. Before doing anything else in this
plan, in a fresh session/subagent:

- [ ] Run `MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD glxinfo 2>&1 | grep "OpenGL renderer"`
  and confirm it prints `D3D12 (AMD Radeon RX 6950 XT)`. If it doesn't (e.g. a
  fresh container/session where this wasn't installed), stop and re-run:
  `sudo apt update && sudo apt install -y blender mesa-vulkan-drivers vulkan-tools mesa-utils`
  (this needs a sudo password the agent does not have — surface this to the
  user rather than guessing/attempting to bypass it, exactly as happened
  earlier this session).
- [ ] Run `which blender && blender --version` and confirm `Blender 3.0.1`
  (or whatever version is actually installed) responds.
- [ ] Confirm `ls ~/seraph/blender/build_scene.py` exists — if this whole
  `blender/` directory is missing, something upstream of this plan was lost;
  stop and reconcile with the user rather than reconstructing from memory.

---

### Task 1: Fix the wings, lock a good static "awake" composition

**Files:**
- Modify: `blender/build_scene.py`

**Why:** the wings are the one piece of the current render that's actively
bad, not just unfinished. Fix this before building any animation on top of a
broken element.

**Interfaces:**
- Consumes: nothing new — same script, same `make_wing_material` /
  wing-building loop already present.
- Produces: no new interface — this is a geometry/material fix within the
  existing script.

- [ ] **Step 1: Replace `make_wing_material`**

Find the current function (creates a flat, non-emissive, cool-toned
`Principled BSDF` material) and replace it with one that adds warmth via a
touch of emission, so wings don't depend entirely on external lighting to read
as anything other than gray:

```python
def make_wing_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.92, 0.82, 0.60, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Alpha"].default_value = 0.95
    if "Emission" in bsdf.inputs:
        bsdf.inputs["Emission"].default_value = (0.35, 0.28, 0.15, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.6
    mat.blend_method = 'BLEND'
    return mat
```

(Blender 3.0's Principled BSDF has built-in `Emission`/`Emission Strength`
inputs — no separate emission shader/mix node needed, unlike the halo
material's approach.)

- [ ] **Step 2: Replace the wing-building loop**

Find the current loop (creates 2 layers per wing, each a bezier curve with
`curve.bevel_depth` — a *round* tube cross-section, which is why it reads as
tentacles, not wings). Replace with a version that uses `curve.extrude` for an
actual flat ribbon cross-section, and per-point `radius` for a proper
wide-root/narrow-tip wing taper, with 3 layers per wing for a feathered look:

```python
wing_mat = make_wing_material("WingCream")
N_WINGS = 10
N_LAYERS = 3
for i in range(N_WINGS):
    base_ang = (i / N_WINGS) * 2 * math.pi
    for layer in range(N_LAYERS):
        curve = bpy.data.curves.new(f"WingCurve_{i}_{layer}", type='CURVE')
        curve.dimensions = '3D'
        curve.bevel_depth = 0.008
        curve.bevel_resolution = 2
        curve.extrude = 0.16 - 0.045 * layer  # flat ribbon width; outer layers narrower
        curve.fill_mode = 'FULL'
        curve.use_fill_caps = True
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(3)
        z_lift = 0.10 * layer
        layer_ang = base_ang + (layer - 1) * 0.10  # slight fan spread per layer
        pts = [
            (0.85, 0.00, 0.05 + z_lift, 0.22),
            (1.55, 0.35, 0.25 + z_lift, 0.13),
            (2.15, 0.30, 0.15 + z_lift, 0.06),
            (2.55, 0.05, -0.05 + z_lift, 0.01),
        ]
        for k, (x, y, z, rad) in enumerate(pts):
            bp = spline.bezier_points[k]
            bp.co = (x, y, z)
            bp.radius = rad
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
        obj = bpy.data.objects.new(f"Wing_{i}_{layer}", curve)
        bpy.context.collection.objects.link(obj)
        obj.rotation_euler = (0, 0, layer_ang)
        obj.data.materials.append(wing_mat)
```

- [ ] **Step 3: Render and verify**

Run: `cd ~/seraph && MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD timeout 120 blender --background --python blender/build_scene.py`
Expected: `RENDER_DONE` printed, no Python tracebacks.

Read `blender/renders/still_001.png` with your Read tool. Judge specifically:
do the wings now read as flat, tapered, wing-like blades (wide near the wheels,
narrowing outward, with visible layering between the 3 curves per wing), warm
in tone rather than cold gray? If they still read as tentacles/wires, you have
latitude to adjust `curve.extrude`, the `radius` taper values, or the control
point path shape — this is a creative judgment call, keep iterating (re-run
Step 3) until it genuinely looks like a wing, not just "technically different
from before." Do not proceed to Task 2 on an unconvincing result.

- [ ] **Step 4: Copy the result out for the user to see**

Run: `cp ~/seraph/blender/renders/still_001.png /mnt/c/Users/computer/Downloads/seraph_3d_wings_fixed.png`

- [ ] **Step 5: Commit**

```bash
cd ~/seraph && git add blender/build_scene.py
git commit -m "Fix wing geometry: flat tapered ribbons instead of round tentacle-like tubes"
```

---

### Task 2: Port the wake curve as shared data

**Files:**
- Create: `blender/wake_curve.py`

**Why:** the animation (Task 3) needs to sample the same dormant→awake curve
the WebGL version already ships, so both stay consistent with each other and
with the real track's structure — not two independently-authored, potentially
drifting timings.

**Interfaces:**
- Consumes: nothing (the 20 points are transcribed directly — see rationale
  below for why this plan doesn't build a JS→JSON export step).
- Produces: `sample_wake(t: float) -> float` — piecewise-linear sample,
  clamped outside the curve's range, mirroring `src/score.js`'s
  `sampleCurve`/`sampleScore` exactly. Task 3 imports and calls this.

**Note on approach:** a fancier version of this task would export
`src/score-data.js`'s `wake` array to JSON via a small Node script and have
Blender read that JSON at build time, so there's only one authored copy of the
20 points. That's more properly DRY, but for 20 static numbers that are
unlikely to change independently of a full re-authoring pass (which would touch
both the JS and this file anyway), directly transcribing them into a pure
Python module is simpler and has zero cross-runtime tooling to break. If the
points are ever re-authored, update both files in the same commit — call this
out explicitly in both files' comments.

- [ ] **Step 1: Create `blender/wake_curve.py`**

```python
"""The dormant->awake wake curve, ported from src/score-data.js's `wake` array.
If that curve is ever re-authored (e.g. against a different/trimmed track),
update both files in the same commit — this is a manual mirror, not a shared
data file, by deliberate simplication (see plan Task 2 for rationale)."""

WAKE_CURVE = [
    (0.0, 0.00),
    (8.0, 0.04),
    (15.5, 0.10),
    (16.4, 0.22),
    (20.0, 0.38),
    (24.0, 0.50),
    (32.0, 0.58),
    (42.4, 0.62),
    (43.2, 0.70),
    (47.9, 0.72),
    (48.8, 0.78),
    (53.4, 0.79),
    (54.2, 0.85),
    (60.3, 0.86),
    (62.1, 0.91),
    (71.9, 0.92),
    (74.9, 0.96),
    (78.1, 0.97),
    (79.0, 1.00),
    (90.0, 1.00),
]


def sample_wake(t):
    """Piecewise-linear sample of WAKE_CURVE at time t (seconds). Clamps
    outside the curve's range — mirrors src/score.js's sampleCurve exactly."""
    pts = WAKE_CURVE
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        t1, v1 = pts[i]
        if t <= t1:
            t0, v0 = pts[i - 1]
            f = (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * f
    return pts[-1][1]
```

- [ ] **Step 2: Verify it matches the JS version's behavior at spot-check points**

Run this to confirm no transcription errors (compares against known values
from the JS curve at its exact knot points and a few interpolated midpoints):

```bash
cd ~/seraph && MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background --python -c "
import sys; sys.path.insert(0, 'blender')
from wake_curve import sample_wake
checks = [(0,0.00),(24,0.50),(43.2,0.70),(79.0,1.00),(90,1.00),(999,1.00),(-5,0.00),(30,0.56)]
for t, expected in checks:
    got = sample_wake(t)
    status = 'OK' if abs(got-expected) < 1e-6 else 'MISMATCH'
    print(f'{status}: t={t} got={got} expected={expected}')
"
```

Expected: all `OK`. (The `t=30` check is a genuine interpolated midpoint
between the `(24, 0.50)` and `(32, 0.58)` knots — compute it independently
before trusting the expected value, don't just copy a number that happens to
make the check pass.)

- [ ] **Step 3: Commit**

```bash
git add blender/wake_curve.py
git commit -m "Port the wake curve to Python for the Blender animation pipeline"
```

---

### Task 3: Procedural animation (no keyframes — per-frame imperative state, mirroring the proven GLSL approach)

**Files:**
- Create: `blender/animate.py`

**Architecture decision — read before implementing:** Blender supports two
ways to drive animation: (a) keyframes + F-curves, or (b) drivers (Python
expressions evaluated live), or (c) an imperative approach where a script sets
every object's transform/material properties directly for a given frame number
before that frame is rendered, with no keyframes or drivers involved at all —
effectively treating `frame_number / fps` as `uTime` and computing everything
from scratch each frame, exactly like the WebGL shader's `main()` function did
every frame from `uTime`/`uProgress`. **Use approach (c).** It's what this
project already has a proven, debugged mental model for (every formula in
`src/gl/shaders/angel.frag` is directly portable — same math, different
language), it's trivial to unit-test in isolation (call the per-frame function
with a few `t` values and inspect the numbers, no Blender UI/keyframe
inspection needed), and it sidesteps an entire class of Blender-specific bugs
(driver dependency cycles, F-curve interpolation surprises) that would cost
real time to debug for no benefit here, since we're rendering offline anyway
and don't need Blender's own timeline scrubbing UI to work.

**Interfaces:**
- Consumes: `sample_wake(t)` from `blender/wake_curve.py` (Task 2); the named
  objects `build_scene.py` creates (`Wheel_0/1/2`, `Wing_{i}_{layer}` for
  i in 0-9 and layer in 0-2, `Halo`, and the eye objects — Task 1's script
  needs to give eye objects predictable names, e.g. `Eye_{wheel}_{index}` and
  `Pupil_{wheel}_{index}`, if it doesn't already; check and fix naming as part
  of this task if needed).
- Produces: `apply_frame_state(t: float)` — given a time in seconds, sets
  every animated object's rotation/scale/material-emission-strength to the
  correct state for that instant. Task 4/5 call this once per frame before
  rendering.

- [ ] **Step 1: Design the per-element formulas, translating the WebGL lessons directly**

Before writing code, translate each `angel.frag` block's *already-tuned*
constants (post amplitude-pass — the ones that were verified to read as alive,
not the original too-subtle ones) into the 3D equivalent. This is not a blind
copy — 3D geometry responds differently than a 2D SDF shader (e.g. "brightness"
in 3D is emission strength on a real light-casting surface, which will read
differently under Eevee's bloom than a flat additive shader color) — but the
*shape* of each formula (base speed, wake-dependent range, per-element phase
seeding so nothing moves in unison) should carry over as a starting point:

- Wheel rotation: `angle(t) = t * (base_speed) * mix(dormant_floor, 1.0, wake(t))`,
  per-wheel `base_speed` varying so they don't move in lockstep (mirrors
  `angel.frag`'s `uTime*(0.16 + 0.09*fw)` — same idea, different base radius
  count since there are only 3 wheels here too).
- Wing fold: an oscillating rotation offset per wing, phase-seeded per wing
  index (use Python's `hash()` or a fixed seed table — do NOT rely on
  nondeterministic hashing between runs, since re-running the render must
  reproduce identical frames; seed a `random.Random(wing_index)` instance per
  wing, or use a fixed lookup table of 10 phase values).
- Wing breathe: scale factor on the wing curve's local Y axis or overall
  object scale, oscillating independently per wing.
- Eye blink: independent per-eye open/closed state (scale the pupil/iris
  objects' Z-thinness, mirroring the GLSL `eyeD` lid-parting math), each eye
  on its own seeded cycle, wake-dependent open-window width (dormant: rarely
  open; awake: open often) — same shape as `angel.frag`'s eye block.
- Halo flicker: drive the `HaloFire` material's noise texture's `Scale`/`W`
  input (a 4th noise dimension used as a time axis) each frame, plus scale the
  emission `Strength` input by `mix(dormant_floor, ceiling, wake(t))`.

- [ ] **Step 2: Implement `apply_frame_state(t)` in `blender/animate.py`**

Write the actual Python implementing the design from Step 1. Include this
verbatim at the top of the file:

```python
import bpy, math
from wake_curve import sample_wake

WING_PHASES = [0.13, 0.87, 0.41, 0.62, 0.05, 0.94, 0.28, 0.71, 0.50, 0.36]  # fixed, reproducible
EYE_SEEDS = { ... }  # fill in per-eye based on however build_scene.py names/counts eyes
```

(The exact body is left to the implementer — this is the one part of this plan
without exact prescribed code, because it depends on Task 1's final object
naming and the Step 1 design above, both of which don't exist as fixed
artifacts yet. Follow the Global Constraints — especially wide dynamic range
and fast-enough cycles — and the per-block formula shapes from Step 1.)

- [ ] **Step 3: Smoke-test in isolation, without rendering**

```bash
cd ~/seraph && MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background --python blender/build_scene.py --python-expr "
import sys; sys.path.insert(0, 'blender')
from animate import apply_frame_state
for t in [0, 20, 45, 79, 90]:
    apply_frame_state(t)
    print(f't={t}: no exception')
"
```

Expected: no tracebacks for any of the 5 sample times. This just proves the
function runs cleanly across the dormant/rising/surging/awake/holding range
before spending render time on it.

- [ ] **Step 4: Commit**

```bash
git add blender/animate.py
git commit -m "Add per-frame procedural animation driven by the wake curve"
```

---

### Task 4: Preview render + contact-sheet verification

**Files:**
- Create: `blender/render_preview.py`

**Why:** rendering all ~2700 frames (90s * 30fps) at final quality before ever
looking at the animation would be expensive and is exactly the kind of
premature commitment this project's WebGL side learned to avoid. Render a
sparse, low-cost preview spanning the whole duration first.

**Interfaces:**
- Consumes: `apply_frame_state` (Task 3), the built scene (Task 1).
- Produces: PNG files in `blender/renders/preview/`, and (via a follow-up
  `ffmpeg` step, same technique as the WebGL project) a tiled contact sheet.

- [ ] **Step 1: Write `blender/render_preview.py`**

```python
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from animate import apply_frame_state

OUT_DIR = "/home/unix/seraph/blender/renders/preview"
os.makedirs(OUT_DIR, exist_ok=True)

scene = bpy.context.scene
scene.eevee.taa_render_samples = 24  # lower than final quality — this is a preview
times = [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48, 51, 54,
         57, 60, 63, 66, 69, 72, 75, 78, 81, 84, 87, 90, 93]

for t in times:
    apply_frame_state(t)
    scene.render.filepath = f"{OUT_DIR}/t_{int(t):03d}.png"
    bpy.ops.render.render(write_still=True)
    print(f"rendered t={t}")

print("PREVIEW_DONE")
```

- [ ] **Step 2: Run it (build the scene fresh, then render the preview sequence)**

```bash
cd ~/seraph && MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD timeout 600 blender --background --python blender/build_scene.py --python blender/render_preview.py
```

Expected: `PREVIEW_DONE`, 32 PNGs in `blender/renders/preview/`. (32 frames at
24 samples and 960x960 should take low single-digit minutes on this GPU, based
on the ~1.8-2.7s per 64-sample still observed earlier — budget up to 10
minutes and treat longer as a real problem to investigate, not just wait out.)

- [ ] **Step 3: Build a contact sheet and judge it against the ORIGINAL complaint**

```bash
cd ~/seraph/blender/renders/preview && ffmpeg -y -v error -pattern_type glob -i 't_0*.png' -frames:v 1 -vf "scale=160:160,tile=8x4" contact_sheet.png
```

Read `contact_sheet.png`. This is the real test, same standard the WebGL
amplitude-pass used: does brightness/activity clearly trend from
dim/still/dormant (early panels) to bright/full/awake (panels in the 42-79s
surge range)? Do wheel rotation, wing angles, and eye states visibly differ
between panels only 2-3 apart (6-9s), not just between the first and last
panel? Does it read as a being that's alive and building toward something, or
does it still look like a static diagram with some numbers changing behind the
scenes? If it doesn't clear that bar, go back to Task 3's formulas (wider
ranges, faster cycles) and redo Task 4 — don't proceed to a full render on an
unconvincing preview.

- [ ] **Step 4: Copy the contact sheet out for the user**

```bash
cp ~/seraph/blender/renders/preview/contact_sheet.png /mnt/c/Users/computer/Downloads/seraph_3d_preview_sheet.png
```

- [ ] **Step 5: Commit the scripts (not the renders — those are gitignored)**

```bash
git add blender/render_preview.py
git commit -m "Add preview-render + contact-sheet verification step"
```

(If `blender/renders/` isn't already gitignored, add it to `.gitignore` in
this same commit — check first with `git status`.)

---

### Task 5: Full render + audio mux (only after Task 4's preview genuinely passes)

**Files:**
- Create: `blender/render_full.py`

**This task should not start until a human (the user) has reviewed the
Task 4 contact sheet and confirmed it's worth committing full render time to.**
That's a real checkpoint, not a formality — full rendering is the expensive,
slow step in this pipeline.

**Interfaces:**
- Consumes: `apply_frame_state` (Task 3), the built scene (Task 1).
- Produces: `blender/renders/full/frame_%05d.png` (one file per frame), then
  a final muxed video via `ffmpeg`.

- [ ] **Step 1: Decide and record the final render settings**

Defaults to start from (adjust only with reasoning, not guessing): 1280x720,
30fps (→ 2700 frames for 90.00s), `taa_render_samples = 64` (matches what was
already proven to look clean in the two test stills). Estimate total render
time from Task 4's per-frame timing before committing — if 64-sample stills
at 960x960 took ~1.8-2.7s each, a 1280x720 frame at the same sample count
should be in a similar ballpark (resolution scales cost sub-linearly relative
to sample count in Eevee); 2700 frames at ~2s each is ~90 minutes. If actual
timing is far off from this estimate, stop and report back rather than let a
multi-hour render run unnoticed.

- [ ] **Step 2: Write and run `blender/render_full.py`**

Same structure as `render_preview.py` (Task 4) but: `times` becomes
`[f/30 for f in range(2700)]` (every frame, not sparse samples), samples set
per Step 1's decision, output path `blender/renders/full/frame_%05d.png`. Use
`run_in_background` for the actual render invocation given the expected
runtime — don't block a session on a 90-minute foreground command.

- [ ] **Step 3: Mux with the real audio track**

```bash
cd ~/seraph/blender/renders/full && ffmpeg -y -framerate 30 -i frame_%05d.png -i /home/unix/seraph/audio/seraph-clip.mp3 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest /home/unix/seraph/dist/seraph-3d.mp4
```

- [ ] **Step 4: Verify the output file**

```bash
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 /home/unix/seraph/dist/seraph-3d.mp4
```
Expected: duration close to 90.00s, non-trivial file size. Extract a couple of
still frames from the final mp4 (`ffmpeg -ss 45 -i seraph-3d.mp4 -frames:v 1 check.png`)
and Read them to confirm the muxed video actually contains the expected
imagery (not a corrupt/black output) before calling this done.

- [ ] **Step 5: Deliver**

```bash
cp /home/unix/seraph/dist/seraph-3d.mp4 /mnt/c/Users/computer/Downloads/seraph-3d.mp4
```

- [ ] **Step 6: Commit the scripts**

```bash
git add blender/render_full.py
git commit -m "Add full render + audio mux pipeline"
```
