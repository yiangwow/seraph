# seraph v3 — Asset-Driven Path-Traced Ophanim (Design Spec)

**Date:** 2026-07-02
**Status:** Approved direction (user: "go ahead"), supersedes the raymarch-shader
direction explored earlier the same day (that lane was chosen before the
Windows-GPU + asset pipeline was proven; it is parked, not deleted).

## Purpose

Produce a ~90-second rendered film of the seraph — the ophanim being this
project has been building all along (dormant→awake arc, locked to the real
track's kick onsets) — at a quality level competitive with professional
reference work (Jonas Pfeiffer's "Celestial Beings" series, which the user's
reference images come from). Two prior attempts fell short for diagnosed
reasons: the WebGL SDF version read as "static lines" (fixed, but medium
ceiling too low), and the scripted-primitives Eevee version read as "novice
work" (procedural primitives cannot fake sculpted asset detail; rasterized
lighting cannot fake path-traced light transport).

## What changed to make this attempt credible

1. **Real assets replace procedural primitives** (the expert workflow —
   assembly is scripted, creation is not):
   - Photoscanned baroque ornament pieces ×4 (BlenderKit) → ring encrusting
   - Production eye asset with fibrous iris texture (BlenderKit) → the great
     eye and all ring eyes. Known defect: demon slit pupil, to be overridden
     in-shader with a round, dilation-animatable pupil mask.
   - Photoscanned feather (BlenderKit) → cloned for wings + socket plumage
   - Disney "wdas_cloud" production VDB (half/quarter/eighth res) → clouds
   - 3× 4K sky EXRs (Polyhaven) → world lighting/backdrop
   - All under `C:\Users\computer\seraph-assets\` and
     `C:\Users\computer\blenderkit_data\models\`.
2. **Real path tracing**: Cycles on the Windows-side RX 6950 XT via HIP,
   driven headlessly from WSL (`blender.exe -b` works from WSL; verified:
   128 samples @ 960² in 2.56s). Blender 5.1.2.
3. **The user is the taste loop**: explicit approval gates where the user
   judges renders, optionally against extracted frames from the reference
   video (`seraph-assets\ref\`, if/when the user downloads it).

## Scene definition

Composition carries over from v2's validated framing (low monumental camera,
being centered, tiny human scale-figure on a rock spur bottom-left), rebuilt
with assets:

- **The Great Eye**: eye asset (Sclera_01 + Lens_01 + Iris_01 objects,
  anatomically-scaled ~3.5cm — scale up ~30×) at center. Shader work: round
  pupil override mask on the iris (radius = uniform driven per frame for
  wake dilation), sclera kept subtle. Lids: crumpled-shell approach from v2
  (they read well) upgraded with subsurface skin shading in Cycles.
- **Rings ×2**: torus guide paths (no visible bare torus). Ornament pieces
  arrayed/cloned along each path (Blender array+curve modifiers or
  geometry-nodes instancing; per-clone jitter in scale/rotation), copper/
  rose-gold material with roughness variation. Eye clones (same eye asset,
  small) set into bezels around each band. Counter-rotating spin via the
  proven closed-form wake integral (`blender/wake_curve.py`, reused as-is).
- **Wings + socket plumage**: the scanned feather cloned into 3-row fans
  (v2's shoulder-arc layout, which worked) and the eye-hugging corona +
  hanging under-feathers (v2's socket plumage layout). Per-clone length/
  roll/hue jitter. Wing-beat + traveling ripple animation as in v2.
- **Halo**: emissive flame torus behind (v2's 4D-noise flicker approach,
  ported to Cycles nodes) + HDRI sun glow.
- **Atmosphere**: Disney VDB cloud instanced 2-4× (scaled/rotated variants)
  below and behind; thin scatter haze in the camera corridor for god-rays;
  EXR sky world. Cycles volumetric scattering (real, not faked).
- **Scale figure**: dark silhouette figure + rock spur (v2 approach).

## Animation

`apply_frame_state(t)` architecture carried over verbatim in spirit from
`blender/animate_v2.py` (pure imperative per-frame state, no keyframes, all
deterministic, wake curve + integral from `blender/wake_curve.py`):
ring spin (integral form), lid open with breathing + seeded awake blinks,
gaze wander → lock at 78.5s, pupil dilation (now driving the shader mask
uniform), ring-eye apertures, wing beat + feather ripple, halo flicker,
cloud drift (VDB domain slow rotation/translation — NOT noise-W, since VDBs
are static grids), light energies with wake.

## Render & post

- 1080×1080 @ 30fps, 2700 frames, Cycles GPU, samples chosen after a timing
  test (target ≤ ~8s/frame → ≤ ~6h full render, launched in background,
  possibly overnight; OpenImageDenoise on).
- Post in Blender compositor, scripted: glare/bloom, film grain, gentle
  S-curve contrast, vignette, subtle chromatic aberration (lens distortion
  node). (This apt/WSL Blender lacked OCIO; Windows Blender 5.1 has full
  color management — use AgX/Filmic there, chosen at the lighting gate.)
- Mux with `audio/seraph-clip.mp3` via ffmpeg → `dist/seraph-v3.mp4`.

## Approval gates (user judges renders at each)

1. **Blockout**: composition with placeholder-dressed assets, one still.
2. **Dressed**: ornament rings, feather wings, eye integrated — geometry
   complete, one still.
3. **Look**: materials + lighting + clouds + grade, 2-3 stills (dormant /
   awake states).
4. **Motion**: 32-frame contact sheet spanning the 90s.
5. **Final**: full render + mux.

Gates 1-3 may loop; the user's read is the exit criterion, not mine.

## Verification discipline (unchanged from the whole project)

Contact sheets for anything temporal; I read every render myself before
claiming anything; independent verification over subagent/self reports; git
authorship the owner's git identity, no Co-Authored-By; no pushes
to any remote; renders/assets stay out of git (gitignored).

## Out of scope

- Real-time playback (offline film only).
- The raymarch-shader lane (parked).
- 4K output (1080² first; upres is a re-render decision after the film works).

## Risks

- **WSL→Windows Blender bridge quirks** (path translation, long arg strings):
  mitigated — all scripts live on `/mnt/c` and reference `C:\` paths.
- **VDB render cost**: Disney half-res cloud is 492MB; if per-frame times
  blow past budget, drop to quarter-res (68MB) which is still film-grade.
- **Eye slit pupil**: if the slit is mesh-hole rather than texture, add a
  backing disc behind the iris; shader mask handles the visible shape.
- **BlenderKit asset licenses**: free BlenderKit assets are royalty-free
  for use in rendered works; no redistribution of the assets themselves in
  the repo (they stay outside git).
