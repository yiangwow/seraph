"""Per-frame procedural animation for the seraph scene.

Architecture: no keyframes, no drivers. `apply_frame_state(t)` sets every
animated object's transform / material state directly for the given time in
seconds, exactly like the WebGL shader's main() recomputed everything from
uTime every frame. Task 4/5 call this once per frame before rendering.

The constants here are a deliberate port of the *post-amplitude-pass* values in
src/gl/shaders/angel.frag — the ones verified to read as ALIVE, not the original
too-subtle first attempt. The two lessons baked in throughout:
  (1) WIDE dynamic range: dormant floors sit near 0.05-0.22, not 0.4+, so the
      dormant->awake swing is dramatic (typically 5-45x), not a timid 2.5x.
  (2) FAST cycles: every oscillation completes in ~20-50s, so a full cycle is
      actually seen within the ~90s piece — no 100-300s crawls.
Both were the exact failures that made the earlier version read as static.
"""
import bpy
import math
import random
import mathutils
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wake_curve import sample_wake

# Fixed, reproducible per-wing phase seeds (0..1). Re-running a render must
# produce identical frames, so these are a literal table, not hashed at runtime.
WING_PHASES = [0.13, 0.87, 0.41, 0.62, 0.05, 0.94, 0.28, 0.71, 0.50, 0.36]

# Mirrors build_scene.py's wheel_specs n_eyes (manual mirror, same convention as
# wake_curve.py — if wheel_specs changes, update this in the same commit).
WHEEL_EYE_COUNTS = [10, 8, 7]

# Per-wheel base spin rates (rad/s), mirroring angel.frag's uTime*(0.16+0.09*fw)
# so the three wheels never turn in lockstep.
WHEEL_SPEEDS = [0.16, 0.25, 0.34]


def _eye_seed(wheel, idx):
    """Deterministic per-eye seed in [0,1). Fixed formula => identical every
    run (no reliance on Python's nondeterministic hash())."""
    return random.Random(wheel * 7919 + idx * 104729 + 17).random()


# Precomputed seed table (documented shape from the brief); every eye's blink
# clock is derived from its own value here so blinks stay asynchronous.
EYE_SEEDS = {
    (w, j): _eye_seed(w, j)
    for w, n in enumerate(WHEEL_EYE_COUNTS)
    for j in range(n)
}

# Pristine base transforms, captured on the first apply_frame_state call (when
# build_scene.py's authored values are still untouched) so every frame is
# computed relative to the same baseline rather than accumulating drift.
_base_rot = {}
_base_scale = {}


def _base_rotation(obj):
    if obj.name not in _base_rot:
        _base_rot[obj.name] = tuple(obj.rotation_euler)
    return _base_rot[obj.name]


def _base_scl(obj):
    if obj.name not in _base_scale:
        _base_scale[obj.name] = tuple(obj.scale)
    return _base_scale[obj.name]


def _mix(a, b, t):
    return a + (b - a) * t


def _smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def apply_frame_state(t):
    """Set the whole scene's animated state to time `t` (seconds)."""
    wake = sample_wake(t)

    # ---- WHEELS: each spins about its own local normal axis ---------------
    # angle = t * base_speed * mix(dormant_floor, 1.0, wake) * direction.
    # Floor 0.22 (a lazy idle even when dormant) -> full speed awake; wheels
    # counter-rotate so the interlock reads. The spin is applied in the ring's
    # OWN untilted plane (Rotation about Z) then composed under the wheel's
    # tilt, so the ring stays in its tilted plane and the parented eyes orbit
    # the rim — which is the only thing that makes a symmetric torus's rotation
    # visible at all.
    for w in range(3):
        obj = bpy.data.objects.get(f"Wheel_{w}")
        if obj is None:
            continue
        tilt = mathutils.Euler(_base_rotation(obj), 'XYZ').to_matrix().to_4x4()
        direction = 1.0 if (w % 2 == 0) else -1.0
        angle = t * WHEEL_SPEEDS[w] * _mix(0.22, 1.0, wake) * direction
        spin = mathutils.Matrix.Rotation(angle, 4, 'Z')
        obj.rotation_euler = (tilt @ spin).to_euler()

    # ---- EYES: independent, asynchronous blinking ------------------------
    # Mirrors angel.frag's eye block. Each eye runs its own sine clock; the
    # OPEN window is wake-dependent — dormant it must climb past ~0.94 to crack
    # open (rare, brief glances), awake past only ~0.55 (open often, longer).
    # Openness drives the lid aperture: local-Y scale from a thin 0.08 slit
    # (near-shut, amber iris just gleaming through) to a full 1.0 round eye —
    # a >12x range, deliberately wider than the shader's ~3x since a real
    # emissive lens under Eevee bloom can afford the drama.
    for w, n in enumerate(WHEEL_EYE_COUNTS):
        lo = _mix(0.94, 0.55, wake)
        hi = _mix(0.995, 0.78, wake)
        for j in range(n):
            seed = EYE_SEEDS[(w, j)]
            speed = 0.16 + 0.16 * seed          # period ~20-39s: seen within the piece
            phase = seed * math.tau
            cyc = 0.5 + 0.5 * math.sin(t * speed + phase)
            open_amt = _smoothstep(lo, hi, cyc)
            aperture = _mix(0.08, 1.0, open_amt)
            for prefix in ("Eye", "Pupil"):
                o = bpy.data.objects.get(f"{prefix}_{w}_{j}")
                if o is None:
                    continue
                bx, by, bz = _base_scl(o)
                o.scale = (bx, by * aperture, bz)

    # ---- WINGS: fold (sweep drift) + breathe (length pulse) ---------------
    # Fold: an oscillating offset on the wing's Z sweep angle, amplitude
    # mix(0.05, 0.55, wake) rad — barely gathered dormant (~3deg), full 31deg
    # sweep awake (an 11x swing). Breathe: length pulse via local-X scale,
    # amplitude mix(0.05, 0.35, wake) — a subtle dormant flutter opening to a
    # dramatic +-35% stretch awake. Both phase- and speed-seeded per wing (and
    # on different phases from each other) so no two wings, and neither of a
    # wing's two motions, move in unison.
    for i in range(10):
        ph = WING_PHASES[i]
        fold_speed = 0.12 + 0.10 * ph           # period ~28-52s
        fold = _mix(0.05, 0.55, wake) * math.sin(t * fold_speed + ph * math.tau)

        br_speed = 0.18 + 0.12 * ph             # period ~21-35s
        breathe = math.sin(t * br_speed + ph * 4.0)
        stretch = 1.0 + _mix(0.05, 0.35, wake) * breathe

        for layer in range(3):
            o = bpy.data.objects.get(f"Wing_{i}_{layer}")
            if o is None:
                continue
            rx, ry, rz = _base_rotation(o)
            o.rotation_euler = (rx, ry, rz + fold)
            sx, sy, sz = _base_scl(o)
            o.scale = (sx * stretch, sy, sz)

    # ---- HALO: churning flame + wake-scaled blaze ------------------------
    # Advance the 4D noise 'W' axis so the flame field boils each frame, and
    # scale emission Strength by mix(0.12, 1.0, wake) times a fast intensity
    # flicker (0.65 + 0.45*sin(t*6.5), period ~1s). Net strength runs from a
    # dim ~0.03 ember when dormant to a ~1.5 full blaze awake (~45x range) — a
    # direct port of angel.frag's "dim ember -> full blaze" flicker.
    mat = bpy.data.materials.get("HaloFire")
    if mat is not None and mat.use_nodes:
        nodes = mat.node_tree.nodes
        noise = next((n for n in nodes if n.type == 'TEX_NOISE'), None)
        emit = next((n for n in nodes if n.type == 'EMISSION'), None)
        if noise is not None and 'W' in noise.inputs:
            noise.inputs['W'].default_value = t * 1.8
        if emit is not None:
            flicker = 0.65 + 0.45 * math.sin(t * 6.5)
            emit.inputs['Strength'].default_value = 1.4 * _mix(0.12, 1.0, wake) * flicker
