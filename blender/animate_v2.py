"""Per-frame procedural animation for the seraph v2 "Heaven" scene.

Same architecture as v1's animate.py (no keyframes, no drivers — pure
imperative state as a function of t, mirroring how the WebGL shader
recomputed everything from uTime), with v1's review defect fixed: all spin
angles use the closed-form wake integral, so angular velocity is exactly
speed*mix(floor,1,wake(t)) — smooth, positive, no spikes at curve kinks.

Amplitude-pass lessons baked in: wide dormant->awake ranges (6-45x), every
cycle completing within ~7-40s, per-element phase seeding, and always-on
motion (cloud churn, lid breathing, gaze wander) covering the dormant intro.
"""
import bpy
import math
import random
from mathutils import Euler, Matrix

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wake_curve import sample_wake, wake_integral

# Manual mirrors of build_scene_v2.py's layout (same convention as
# wake_curve.py: if the scene script changes these, update here in the same
# commit).
RING_EYE_COUNTS = [20, 14]
RING_SPEEDS = [0.30, 0.50]          # rad/s awake; dormant floor 0.35 below
N_FEATHERS = 16
N_ROWS = 3
GAZE_LOCK_T = 78.5                  # final strong onset: the eye fixes on you

_rng = random.Random(11)
RING_EYE_SEEDS = {
    (r, j): _rng.random()
    for r, n in enumerate(RING_EYE_COUNTS)
    for j in range(n)
}

_base_rot = {}


def _base_rotation(obj):
    if obj.name not in _base_rot:
        _base_rot[obj.name] = tuple(obj.rotation_euler)
    return _base_rot[obj.name]


def _mix(a, b, t):
    return a + (b - a) * t


def _smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    v = max(0.0, min(1.0, (x - a) / (b - a)))
    return v * v * (3.0 - 2.0 * v)


def _spin_angle(t, speed, floor=0.35):
    """Integral form: d(angle)/dt = speed*mix(floor,1,wake(t)). Never use
    t*speed*mix(...) — its derivative spikes at wake-curve kinks (v1 review
    finding)."""
    return speed * (floor * t + (1.0 - floor) * wake_integral(t))


def _blink_envelope(t, wake):
    """Occasional full blinks once the being is awake: one seeded blink at a
    random moment inside each ~11.5s window. Deterministic (seeded by window
    index). Returns 0..1 closedness."""
    if wake < 0.6:
        return 0.0
    w = int(t // 11.5)
    rng = random.Random(w * 7919 + 3)
    blink_t = w * 11.5 + rng.uniform(1.5, 10.0)
    d = abs(t - blink_t)
    if d > 0.28:
        return 0.0
    c = 1.0 - d / 0.28
    return c * c * (3.0 - 2.0 * c)


def _find_node(mat, node_type):
    return next((n for n in mat.node_tree.nodes if n.type == node_type), None)


def apply_frame_state(t):
    wake = sample_wake(t)

    # ---- RINGS: counter-rotating spin about their own tilted axes --------
    for r in range(2):
        ring = bpy.data.objects.get(f"Ring_{r}")
        if ring is None:
            continue
        tilt = Euler(_base_rotation(ring), 'XYZ').to_matrix().to_4x4()
        direction = 1.0 if r == 0 else -1.0
        angle = _spin_angle(t, RING_SPEEDS[r]) * direction
        ring.rotation_euler = (tilt @ Matrix.Rotation(angle, 4, 'Z')).to_euler()

    # ---- GREAT EYE: gaze wander -> final lock onto the viewer ------------
    eye = bpy.data.objects.get("GreatEye")
    if eye is not None:
        gm = Euler(_base_rotation(eye), 'XYZ').to_matrix().to_4x4()
        amp = 0.12 * _mix(0.3, 1.0, wake)
        lockf = max(0.0, min(1.0, 1.0 - (t - GAZE_LOCK_T) / 0.8)) if t > GAZE_LOCK_T else 1.0
        yaw = amp * lockf * (math.sin(t * 2 * math.pi / 13.7 + 1.3)
                             + 0.5 * math.sin(t * 2 * math.pi / 7.3))
        pitch = amp * lockf * (math.sin(t * 2 * math.pi / 17.1 + 4.2)
                               + 0.5 * math.sin(t * 2 * math.pi / 9.4 + 2.0))
        eye.rotation_euler = (gm @ Matrix.Rotation(pitch, 4, 'X')
                                 @ Matrix.Rotation(yaw, 4, 'Y')).to_euler()

        # lids: parting with wake + slow breathing + awake blinks
        open_amt = _mix(0.06, 1.0, wake) + 0.03 * math.sin(t * 2 * math.pi / 11.0)
        open_amt *= (1.0 - 0.97 * _blink_envelope(t, wake))
        open_amt = max(0.02, min(1.0, open_amt))
        a_top = -math.radians(90.0 + open_amt * 38.0)
        a_bot = math.radians(90.0 + open_amt * 28.0)
        top = bpy.data.objects.get("LidTop")
        bot = bpy.data.objects.get("LidBottom")
        if top is not None:
            top.rotation_euler = (gm @ Matrix.Rotation(a_top, 4, 'X')).to_euler()
        if bot is not None:
            bot.rotation_euler = (gm @ Matrix.Rotation(a_bot, 4, 'X')).to_euler()

    # pupil dilation + iris glow (shared eyeball material)
    mat = bpy.data.materials.get("EyeballMat")
    if mat is not None and mat.use_nodes:
        ramp = mat.node_tree.nodes.get("EyeRadialRamp")
        if ramp is not None:
            pupil = _mix(0.16, 0.30, wake) + 0.008 * math.sin(t * 3.1)
            ramp.color_ramp.elements[0].position = pupil
            ramp.color_ramp.elements[1].position = pupil + 0.04
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Emission Strength"].default_value = _mix(0.65, 2.0, wake)

    # ---- RING EYES: asynchronous seeded blinking --------------------------
    lo = _mix(0.94, 0.55, wake)
    hi = _mix(0.995, 0.78, wake)
    for r, n in enumerate(RING_EYE_COUNTS):
        for j in range(n):
            o = bpy.data.objects.get(f"RingEye_{r}_{j}")
            if o is None:
                continue
            seed = RING_EYE_SEEDS[(r, j)]
            speed = 0.16 + 0.16 * seed          # period ~20-39s
            cyc = 0.5 + 0.5 * math.sin(t * speed + seed * math.tau)
            aperture = _mix(0.08, 1.0, _smoothstep(lo, hi, cyc))
            o.scale = (1.0, aperture, 1.0)

    # ---- WINGS: whole-fan beat + ripple travelling along the feathers ----
    beat_amp = _mix(0.04, 0.30, wake)
    for side, period, phase in (("L", 8.5, 0.0), ("R", 10.5, 2.1)):
        beat_phase = t * 2 * math.pi / period + phase
        beat = beat_amp * math.sin(beat_phase)
        root = bpy.data.objects.get(f"WingRoot_{side}")
        if root is not None:
            rx, ry, rz = _base_rotation(root)
            root.rotation_euler = (rx, ry + beat, rz)
        for row in range(N_ROWS):
            for k in range(N_FEATHERS):
                fo = bpy.data.objects.get(f"Feather_{side}_{row}_{k}")
                if fo is None:
                    continue
                frx, fry, frz = _base_rotation(fo)
                ripple = 0.5 * beat_amp * math.sin(beat_phase - k * 0.45)
                fo.rotation_euler = (frx, fry + ripple, frz)

    # ---- HALO: churning flame, wake-scaled blaze --------------------------
    mat = bpy.data.materials.get("HaloFire")
    if mat is not None and mat.use_nodes:
        noise = _find_node(mat, 'TEX_NOISE')
        emit = _find_node(mat, 'EMISSION')
        if noise is not None and 'W' in noise.inputs:
            noise.inputs['W'].default_value = t * 1.8
        if emit is not None:
            flicker = 0.65 + 0.45 * math.sin(t * 6.5)
            emit.inputs['Strength'].default_value = 1.4 * _mix(0.12, 1.0, wake) * flicker

    # ---- HEAVEN LIGHT + SUN: the sky itself wakes up ----------------------
    mat = bpy.data.materials.get("HeavenGlow")
    if mat is not None and mat.use_nodes:
        emit = _find_node(mat, 'EMISSION')
        if emit is not None:
            emit.inputs['Strength'].default_value = _mix(0.95, 4.0, wake)
    sun = bpy.data.objects.get("Sun")
    if sun is not None:
        sun.data.energy = _mix(2.2, 6.0, wake)
    for side in ("L", "R"):
        wl = bpy.data.objects.get(f"WingGlow_{side}")
        if wl is not None:
            wl.data.energy = _mix(12.0, 100.0, wake)

    # ---- CLOUDS: always-on churn (owns the dormant intro's motion) --------
    for mname in ("CloudMat", "HazeMat"):
        mat = bpy.data.materials.get(mname)
        if mat is not None and mat.use_nodes:
            noise = _find_node(mat, 'TEX_NOISE')
            if noise is not None and 'W' in noise.inputs:
                noise.inputs['W'].default_value = t * 0.35
