# seraph v2 — "Heaven" Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the seraph 3D scene to match the user's reference art — a
colossal pale ophanim in bright heaven: one giant central eye with real lids
and a wandering gaze, fat ornate copper rings studded with rows of eyes,
great feathered wing fans, volumetric clouds and god-light — replacing the
v1 scene the user judged as "just 3d lines."

**Supersedes:** `2026-07-02-seraph-3d-pipeline.md` Tasks 4–5 (never run) and
its Task 3 animation (whose review found one Important defect — the
non-integral wheel-spin formula producing angular-velocity spikes at wake
kinks and 84–178s dormant periods; that fix is folded into this plan's
Task 1/3 rather than patched in place). v1 files (`build_scene.py`,
`animate.py`) stay in the repo untouched as history; v2 is new files.

**Architecture:** Same proven pipeline shape as v1: headless
`MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background --python <script>`,
Eevee, per-frame imperative animation (`apply_frame_state(t)`, no
keyframes/drivers), sparse preview + tiled contact sheet before any full
render, ffmpeg mux at the end. What changes is the *scene content* and the
spin math.

**Tech Stack:** Blender 3.0.1 / Eevee (with volumetrics enabled this time),
Python `bmesh` for lid hemispheres, procedural node materials only (no image
textures, no AI-generated anything), ffmpeg.

## Global Constraints

- **No AI-generated imagery anywhere.** Everything procedural via Blender's
  Python API. Explicit user requirement.
- **Always** prefix Blender runs with `MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD`.
- **Verify with dense contact sheets spanning the whole 90s**, not pairwise
  diffs. Mandatory before any full render.
- **Wide dynamic range, fast cycles** (amplitude-pass lesson): dormant floors
  ~0.05–0.35, full cycles visible within the piece. The v1 3D review proved
  this must hold *by the numbers*, not just in comments.
- **Spin must use the closed-form wake integral** (Task 1), never
  `t * mix(floor, 1, wake(t))` — that form has a computable velocity-spike
  defect at every wake-curve kink (found in v1 Task 3 review).
- **Reuse `blender/wake_curve.py`'s WAKE_CURVE** — already verified against
  the shipped WebGL curve and the real track. Do not re-author timing.
- **The reference images govern the look**: bright ivory/white heaven, copper
  /rose-gold ornate rings, blue-gray iris, monumental scale. When in doubt,
  re-look at the refs, not the v1 scene.
- Git authorship: the owner's git identity, no Co-Authored-By.
- No pushing to any remote. mp3 and all render output stay gitignored.
- Renders are cheap (~2s/frame): **judge every visual step by actually
  reading the rendered image**, and iterate in place — a step is done when
  the image reads right, not when the script exits 0.

---

### Task 1: Wake integral (the spin-math fix)

**Files:**
- Modify: `blender/wake_curve.py`

**Interfaces:**
- Produces: `wake_integral(t: float) -> float` — ∫₀ᵗ wake(s) ds, exact
  closed form (wake is piecewise-linear ⇒ integral is piecewise-quadratic).
- Spin usage (Task 3): `angle(t) = base_speed * (floor*t + (1-floor)*wake_integral(t)) * direction`.
  This gives instantaneous angular speed `base_speed * mix(floor, 1, wake(t))`
  — always positive, no spikes, no dormant freeze.

- [ ] **Step 1: Append to `blender/wake_curve.py`:**

```python
# Cumulative integral of the wake curve at each knot, so wake_integral is a
# cheap closed-form lookup. Spin angles must use this (see v2 plan Task 1):
# angle = speed * (floor*t + (1-floor)*wake_integral(t)). Differentiating
# gives speed*mix(floor,1,wake(t)) exactly — smooth, monotonic, no spikes —
# unlike angle = t*speed*mix(...), whose derivative has a t*wake'(t) term
# that spikes at every curve kink.
_CUM = [0.0]
for _i in range(1, len(WAKE_CURVE)):
    _t0, _v0 = WAKE_CURVE[_i - 1]
    _t1, _v1 = WAKE_CURVE[_i]
    _CUM.append(_CUM[-1] + (_v0 + _v1) * 0.5 * (_t1 - _t0))


def wake_integral(t):
    """Integral of sample_wake from 0 to t (closed form)."""
    pts = WAKE_CURVE
    if t <= pts[0][0]:
        return pts[0][1] * t  # before first knot the curve clamps to v0
    if t >= pts[-1][0]:
        return _CUM[-1] + pts[-1][1] * (t - pts[-1][0])
    for i in range(1, len(pts)):
        t1, v1 = pts[i]
        if t <= t1:
            t0, v0 = pts[i - 1]
            f = (t - t0) / (t1 - t0)
            v_t = v0 + (v1 - v0) * f
            return _CUM[i - 1] + (v0 + v_t) * 0.5 * (t - t0)
    return _CUM[-1]
```

- [ ] **Step 2: Verify numerically**

```bash
cd ~/seraph && MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background --python-expr "
import sys; sys.path.insert(0, 'blender')
from wake_curve import sample_wake, wake_integral
# Riemann-sum cross-check: integral must match a fine numeric sum everywhere.
n, T = 90000, 90.0
dt = T / n
s, worst = 0.0, 0.0
for k in range(n):
    s += sample_wake((k + 0.5) * dt) * dt
    if (k+1) % 10000 == 0:
        worst = max(worst, abs(s - wake_integral((k+1)*dt)))
print('worst abs error vs numeric integral:', worst)
assert worst < 1e-3, 'MISMATCH'
# Monotonic and clamp behavior
assert wake_integral(0) == 0.0
assert abs((wake_integral(95) - wake_integral(90)) - 5.0) < 1e-9  # holds at 1.0 after end
print('OK')
"
```
Expected: `worst abs error` below 1e-3 and `OK`.

- [ ] **Step 3: Commit**

```bash
git add blender/wake_curve.py
git commit -m "Add closed-form wake integral for smooth spin (fixes velocity-spike defect)"
```

---

### Task 2: Scene v2 — the being in heaven (hero still)

**Files:**
- Create: `blender/build_scene_v2.py`

**Interfaces:**
- Produces (object names Task 3 depends on): `GreatEye`, `LidTop`, `LidBottom`,
  `Ring_0` (outer, fat), `Ring_1` (inner), `RingEye_{r}_{j}` (r∈{0,1},
  j<counts [20, 14]) parented to their ring, `Feather_{side}_{row}_{k}`
  (side∈{L,R}, row∈{0,1,2}, k<14) parented to `WingRoot_L`/`WingRoot_R`
  empties, `Halo`, `HeavenDisc`, `CloudDeck`/`CloudHaze` volume domains,
  `Sun`, camera + `CameraTarget`. Materials: `EyeballMat` (shared by great
  eye and ring eyes; its node tree contains one `ShaderNodeValToRGB` whose
  elements[0].position is the pupil-edge radius — Task 3 animates it),
  `HaloFire` (4D noise, W animatable), `CloudMat` (Principled Volume fed by
  4D noise, W animatable).

**Design targets (from the reference images — these govern):**
- Bright ivory world, volumetric cloud deck below/behind, sun backlight,
  bloom. Being reads pale-and-copper against light, monumental, low camera
  looking slightly up.
- `GreatEye`: UV sphere r≈0.85 at origin, local +Z tracked at the camera.
  Procedural eyeball material in Generated coords: radial ramp
  pupil(dark) → iris(blue-gray, ring-striations via RINGS wave + noise
  distortion) → sclera(warm white, faint vein noise). Slight iris emission
  so the slit glows between lids when dormant.
- `LidTop`/`LidBottom`: bmesh half-sphere shells r≈0.88 concentric with the
  eye, ivory skin material; they rotate about the eye's local X to part.
  Build via: `bpy.ops.mesh.primitive_uv_sphere_add`, then
  `bmesh.from_mesh` → `bmesh.ops.delete` verts with `co.z < -1e-3`
  (top lid; mirror for bottom), then orient with the same track quat as the
  eye. Closed = rims meeting at the equator; open = each rotated ~±75°.
- Rings: `Ring_0` torus major 2.3 / tube 0.20, tilt ≈ (0.62, 0, 0) —
  encircles the eye like ref 3. `Ring_1` major 1.5 / tube 0.13, tilt
  ≈ (-0.5, 0.3, 0). Both: 128/32 segments, DISPLACE modifier (CLOUDS
  texture, noise_scale≈0.35, strength≈0.06) for the carved organic
  silhouette, copper Principled (base ≈ (0.72, 0.36, 0.22), metallic 1.0,
  roughness 0.35) with high-freq noise → Bump (strength ≈ 0.4) for
  engraving. Rows of eyes (r 0.11 / 0.09, sharing `EyeballMat`) studding
  each band, oriented radially outward, parented to the ring (v1's
  parent-inverse pattern) so spin carries them.
- Wings: per side, an empty `WingRoot_{L,R}` at ≈ (±1.6, 0.3, -0.9); 3 rows
  × 14 feathers. A feather = bezier curve ribbon (extrude for width, radius
  taper root→tip, slight tilt), row lengths ≈ 0.9/1.4/2.0 (coverts →
  primaries), fanned so the primaries spread widest; ivory material
  (≈ (0.93, 0.90, 0.86), roughness 0.6, emission strength ≈ 0.08). The fans
  cradle the ring like ref 3 — tips sweeping up and outward.
- `HeavenDisc`: emissive warm-white disc (r≈4, strength≈4) behind the being
  at y≈+6, facing camera — the blown-out heaven core the volumetrics catch.
  Keep the `HaloFire` flame torus (r≈3.1) just in front of it, plane facing
  the camera (rotated 90° about X vs v1), reads as the burning halo.
- Volumetrics: `scene.eevee.use_volumetric_lights = True`,
  `volumetric_end ≈ 60`, `volumetric_tile_size = '8'`, samples ≈ 64.
  `CloudDeck`: big flattened cube (x/y ±30, z −8…−2) with Principled Volume,
  density = 4D noise (scale≈0.25) through a ColorRamp cutting low values —
  puffy deck below. `CloudHaze`: thin large box behind/around for god-rays.
  If Eevee volumetrics prove unusable after real iteration (blobby, noisy,
  slow), documented fallback: emissive gradient backdrop + world mist — but
  try volumetrics first, the refs' depth comes from them.
- Camera ≈ (0, −4.8, 0.9), Track-To `CameraTarget` at (0, 0, 0.15) — low,
  monumental. Sun from behind-above (0, 8, 6 aimed at origin, energy ≈ 4).
  Bloom intensity ≈ 0.18, threshold ≈ 0.85. 1080×1080.

- [ ] **Step 1:** Write `blender/build_scene_v2.py` implementing all of the
  above (reuse v1's helper patterns: `clear_scene`, flicker material,
  parent-inverse eye mounting, Track-To camera; end with a still render to
  `blender/renders/still_v2.png` and `print("RENDER_DONE", OUT)`).
- [ ] **Step 2:** Render, read the image, iterate. The bar (judge against the
  refs, not against v1): Does the giant eye dominate and read as a wet,
  living eye? Do the rings read as thick carved copper, not wire? Do the
  wings read as feathered mass? Is the frame bright heaven with cloud depth,
  not black void? Iterate on values in place until yes — renders are ~2s.
- [ ] **Step 3:** `cp blender/renders/still_v2.png /mnt/c/Users/computer/Downloads/seraph_v2_hero.png`
- [ ] **Step 4:** Commit: `git add blender/build_scene_v2.py && git commit -m "Rebuild scene as pale ophanim in bright heaven (v2): giant lidded eye, carved copper rings, feathered wing fans, volumetric clouds"`

---

### Task 3: Animation v2

**Files:**
- Create: `blender/animate_v2.py`

**Interfaces:**
- Consumes: `sample_wake`, `wake_integral` (Task 1); Task 2's object/material
  names (listed in Task 2's Produces block).
- Produces: `apply_frame_state(t: float)` — same contract as v1: pure
  imperative per-frame state, no keyframes/drivers, deterministic (fixed
  seed tables only), base transforms cached on first call (v1's
  `_base_rot`/`_base_scale` pattern).

**Element formulas (starting values; iterate against Task 4's sheet):**
- **Ring spin** (both rings, opposite directions):
  `angle = speed * (0.35*t + 0.65*wake_integral(t)) * dir`, speeds
  ≈ 0.30 / 0.50 rad/s. Dormant periods ≈ 60/36s (carved texture + eye rows
  make partial turns visible), awake ≈ 21/13s. No spikes by construction.
- **Great eye lids**: `open = mix(0.06, 1.0, wake)` plus a slow breathing
  oscillation (±0.03, period ≈ 11s), plus full blinks when awake: seeded
  events every ~9–14s once wake > 0.6, each a ~0.5s close-open envelope.
  Dormant look: a thin glowing slit — one of the piece's key images.
- **Gaze**: base = track-to-camera rotation (cached); wander = two summed
  sines per axis, amplitude ±0.12 rad × `mix(0.3, 1.0, wake)`, periods
  ≈ 7–17s; **gaze lock**: multiply wander by `clamp(1 - (t-78.5)/0.8, 0, 1)`
  so the eye snaps to the camera at the final onset and holds.
- **Pupil**: dilate `EyeballMat` ramp elements[0].position from 0.18 → 0.30
  with wake (plus small flicker), and iris emission strength `mix(0.3, 2.0, wake)`.
- **Ring eyes**: v1's seeded async blink (aperture = local-Y scale, 0.08→1.0,
  wake-dependent open window, periods ~20–39s).
- **Wing beat**: `WingRoot_{L,R}` rotation offset, amplitude
  `mix(0.04, 0.30, wake)` rad, period ≈ 7–11s (seeded per side, not
  synchronized); **feather ripple**: each feather adds
  `0.5 * beat_amplitude * sin(phase - k*0.45)` on local Z, so the beat
  travels along the fan. This ripple is a primary "alive" signal.
- **Halo/heaven**: `HaloFire` W = t*1.8, strength
  `1.4 * mix(0.12, 1, wake) * (0.65 + 0.45*sin(t*6.5))`; `HeavenDisc`
  emission `mix(1.2, 5.0, wake)`; Sun energy `mix(2.5, 5.0, wake)`.
- **Clouds**: `CloudMat` noise W = t*0.35 — always-on churn that carries
  motion through the dormant intro (the v1 review's compounding-stillness
  gap: slow rings + shut eyes made the intro read frozen; the clouds and
  lid-slit breathing now own that window).

- [ ] **Step 1:** Implement `blender/animate_v2.py` per above.
- [ ] **Step 2:** Smoke test t ∈ {0, 20, 45, 79, 90} (no exceptions), then a
  5-frame strip render + tile, and read it: lids must visibly part, rings
  visibly advance between panels, wings visibly change pose.
- [ ] **Step 3:** Commit: `git add blender/animate_v2.py && git commit -m "Animate v2: lids, wandering gaze with final lock, integral-driven ring spin, wing-beat ripple"`

---

### Task 4: Preview contact sheet (user checkpoint)

**Files:**
- Create: `blender/render_preview_v2.py` (same shape as the v1 plan's
  preview: 32 times 0–93 step 3, `taa_render_samples = 24`, out to
  `blender/renders/preview_v2/t_XXX.png`, print `PREVIEW_DONE`).

- [ ] **Step 1:** Write and run it:
  `cd ~/seraph && MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD timeout 900 blender --background --python blender/build_scene_v2.py --python blender/render_preview_v2.py`
  (Volumetrics make frames costlier than v1's ~2s — time it; if a frame
  exceeds ~20s, reduce volumetric samples/tile quality before proceeding.)
- [ ] **Step 2:** `cd blender/renders/preview_v2 && ffmpeg -y -v error -pattern_type glob -i 't_0*.png' -frames:v 1 -vf "scale=160:160,tile=8x4" contact_sheet.png`
  Read it. The bar: dormant slit-eye opening to full gaze across the sheet;
  rings visibly advancing panel-to-panel; wing pose differing between panels
  2–3 apart; brightness building through the 42–79s surge; reads as a being
  waking, judged against the refs.
- [ ] **Step 3:** `cp contact_sheet.png /mnt/c/Users/computer/Downloads/seraph_v2_preview_sheet.png`
  and commit the script. **Stop here for the user's go/no-go on full render.**

---

### Task 5: Full render + mux (after user approves Task 4)

**Files:**
- Create: `blender/render_full_v2.py`

Same mechanics as the v1 plan's Task 5, retargeted: 1080×1080 @ 30fps,
2700 frames, `taa_render_samples = 64` (drop to 48 if Step 1 timing of
Task 4 says a full render would exceed ~4h — report timing before starting
either way), frames to `blender/renders/full_v2/frame_%05d.png`, run in
background, then:

```bash
cd ~/seraph/blender/renders/full_v2 && ffmpeg -y -framerate 30 -i frame_%05d.png -i /home/unix/seraph/audio/seraph-clip.mp3 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest /home/unix/seraph/dist/seraph-v2.mp4
```

Verify with ffprobe (duration ≈ 90s) + extract and read stills at 10/45/80s,
deliver to `/mnt/c/Users/computer/Downloads/seraph-v2.mp4`, commit the script.
