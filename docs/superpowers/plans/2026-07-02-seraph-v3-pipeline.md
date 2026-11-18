# seraph v3 — Asset-Driven Cycles Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> NOTE: executed inline by the controller this session per user direction
> ("take over and do this shit for real") with user approval gates replacing
> per-task subagent reviews — the user judges renders at each gate.

**Goal:** Build and render the seraph v3 film per
`docs/superpowers/specs/2026-07-02-seraph-v3-design.md` (read it first — it
defines scene, assets, animation, gates).

**Architecture:** Python scripts in `blender/v3/` executed by **Windows**
Blender 5.1.2 from WSL:
`"/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b -P <script>`.
Scripts reference `C:\` paths internally. Cycles GPU via HIP (RX 6950 XT) —
enable per-script (`prefs.compute_device_type='HIP'`, verified working).
Scene is rebuilt from scripts every run (same philosophy as v1/v2); assets
append from `C:\Users\computer\blenderkit_data\models\` and
`C:\Users\computer\seraph-assets\`.

## Global Constraints

- Assets are appended, never committed to git (`blender/renders/`,
  `seraph-assets` stay untracked).
- Animation stays pure `apply_frame_state(t)` (no keyframes/drivers), reuses
  `blender/wake_curve.py` (sample_wake + wake_integral) unchanged.
- Contact sheets for anything temporal; controller reads every render.
- Git: the owner's git identity, no Co-Authored-By, no pushes.
- Each gate ends with renders copied to `/mnt/c/Users/computer/Downloads/`
  and a STOP for the user's verdict.

## Tasks

### Task 1: Blockout (Gate 1)
- [ ] `blender/v3/build_scene.py`: append eye asset (scale ~30×, at center,
  gaze-tracked to camera), two torus guide rings (placeholder gray tubes),
  feather-clone placeholder fans, VDB cloud (eighth-res for speed) below,
  EXR sky world, camera + scale figure from v2 layout. Render 1080² still.
- [ ] Iterate composition until it reads; copy to Downloads; STOP for user.

### Task 2: Dressing (Gate 2)
- [ ] Ornament arrays along ring paths (geometry-nodes/array+curve, jitter),
  bezel-set eye clones, real feather fans + socket plumage, lids
  (crumpled shells + SSS skin), halo torus. Still; Downloads; STOP.

### Task 3: Look (Gate 3)
- [ ] Materials (round-pupil shader override + dilation uniform, copper
  variation, feather translucency), lighting rig (HDRI + sun + warm/cool
  areas), half-res VDB, AgX/Filmic pick, compositor grade (glare, grain,
  S-curve, vignette). Dormant + awake stills; Downloads; STOP.

### Task 4: Motion (Gate 4)
- [ ] `blender/v3/animate.py` (`apply_frame_state(t)` per spec) +
  `blender/v3/render_preview.py` (32 frames, low samples) → contact sheet;
  Downloads; STOP.

### Task 5: Final (Gate 5)
- [ ] Timing test → choose samples (≤ ~8s/frame target). Full 2700-frame
  render (background, possibly overnight), ffmpeg mux with
  `audio/seraph-clip.mp3` → `dist/seraph-v3.mp4`, verify stills from the
  mp4, deliver to Downloads.
