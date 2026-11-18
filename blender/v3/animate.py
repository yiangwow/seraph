"""seraph v3 — per-frame procedural animation (same architecture as v2:
pure imperative apply_frame_state(t), no keyframes, deterministic, wake
integral for all spins). Runs inside Windows Blender after v3_build.py.
Reads the wake curve from the repo via the WSL-mounted path.
"""
import bpy
import math
import random
import sys
import os
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, r"\\wsl.localhost\Ubuntu\home\unix\seraph\blender")
try:
    from wake_curve import sample_wake, wake_integral
except Exception:
    sys.path.insert(0, r"C:\Users\computer\seraph-assets")
    from wake_curve import sample_wake, wake_integral

RING_SPEEDS = [0.30, 0.50]
RING_EYE_COUNTS = [16, 12]
N_F = 16
GAZE_LOCK_T = 78.5
EYE_CENTER = Vector((0.0, 0.0, 0.15))
CAM_LOC = Vector((0.0, -7.3, 0.65))

FEATHER_FIX = (Matrix.Rotation(math.radians(90), 4, 'X')
               @ Matrix.Rotation(math.radians(-90), 4, 'Z'))

_rng_seeds = random.Random(11)
RING_EYE_SEEDS = {
    (r, j): _rng_seeds.random()
    for r, n in enumerate(RING_EYE_COUNTS)
    for j in range(n)
}

_base_rot = {}
_base_scale = {}


def _base(store, obj):
    if obj.name not in store:
        store[obj.name] = tuple(obj.rotation_euler) if store is _base_rot else tuple(obj.scale)
    return store[obj.name]


def _mix(a, b, t):
    return a + (b - a) * t


def _smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    v = max(0.0, min(1.0, (x - a) / (b - a)))
    return v * v * (3.0 - 2.0 * v)


def _spin_angle(t, speed, floor=0.35):
    return speed * (floor * t + (1.0 - floor) * wake_integral(t))


def _blink_envelope(t, wake):
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


def apply_frame_state(t):
    wake = sample_wake(t)
    gaze = (CAM_LOC - EYE_CENTER).normalized()

    # ---- rings: counter-rotating, children ride along -------------------
    for r, speed, direction in ((0, 0.30, 1.0), (1, 0.50, -1.0), (2, 0.14, 1.0)):
        ring = bpy.data.objects.get(f"Ring_{r}")
        if ring is None:
            continue
        tilt = Euler(_base(_base_rot, ring), 'XYZ').to_matrix().to_4x4()
        ang = _spin_angle(t, speed) * direction
        ring.rotation_euler = (tilt @ Matrix.Rotation(ang, 4, 'Z')).to_euler()

    # ---- great eye: gaze wander -> lock; lids; blinks --------------------
    eye = bpy.data.objects.get("GreatEyeRoot")
    if eye is not None:
        gm0 = Euler(_base(_base_rot, eye), 'XYZ').to_matrix().to_4x4()
        amp = 0.10 * _mix(0.3, 1.0, wake)
        lockf = max(0.0, min(1.0, 1.0 - (t - GAZE_LOCK_T) / 0.8)) if t > GAZE_LOCK_T else 1.0
        yaw = amp * lockf * (math.sin(t * 2 * math.pi / 13.7 + 1.3)
                             + 0.5 * math.sin(t * 2 * math.pi / 7.3))
        pitch = amp * lockf * (math.sin(t * 2 * math.pi / 17.1 + 4.2)
                               + 0.5 * math.sin(t * 2 * math.pi / 9.4 + 2.0))
        eye.rotation_euler = (gm0 @ Matrix.Rotation(pitch, 4, 'X')
                                  @ Matrix.Rotation(yaw, 4, 'Z')).to_euler()

    open_amt = _mix(0.06, 1.0, wake) + 0.03 * math.sin(t * 2 * math.pi / 11.0)
    open_amt *= (1.0 - 0.97 * _blink_envelope(t, wake))
    open_amt = max(0.02, min(1.0, open_amt))
    gm = gaze.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    a_top = -math.radians(90.0 + open_amt * 38.0)
    a_bot = math.radians(90.0 + open_amt * 28.0)
    top = bpy.data.objects.get("LidTop")
    bot = bpy.data.objects.get("LidBottom")
    if top is not None:
        top.rotation_euler = (gm @ Matrix.Rotation(a_top, 4, 'X')).to_euler()
    if bot is not None:
        bot.rotation_euler = (gm @ Matrix.Rotation(a_bot, 4, 'X')).to_euler()

    # ---- pupil dilation ---------------------------------------------------
    pm = bpy.data.materials.get("PupilPatch")
    if pm is not None and pm.use_nodes:
        node = pm.node_tree.nodes.get("PupilR")
        if node is not None:
            node.outputs[0].default_value = _mix(0.30, 0.44, wake) + 0.006 * math.sin(t * 3.1)

    # ---- ring eyes: asynchronous blink (squash local Z = height) ----------
    lo = _mix(0.94, 0.55, wake)
    hi = _mix(0.995, 0.78, wake)
    for r, n in enumerate(RING_EYE_COUNTS):
        for j in range(n):
            seed = RING_EYE_SEEDS[(r, j)]
            speed = 0.16 + 0.16 * seed
            cyc = 0.5 + 0.5 * math.sin(t * speed + seed * math.tau)
            ap = _mix(0.10, 1.0, _smoothstep(lo, hi, cyc))
            for part in ("Sclera", "Lens", "Iris"):
                o = bpy.data.objects.get(f"RingEye_{r}_{j}_{part}")
                if o is None:
                    continue
                bs = _base(_base_scale, o)
                o.scale = (bs[0], bs[1], bs[2] * ap)

    # ---- wings: root beat + traveling feather ripple ----------------------
    beat_amp = _mix(0.04, 0.26, wake)
    for side, period, phase in (("L", 8.5, 0.0), ("R", 10.5, 2.1)):
        beat_phase = t * 2 * math.pi / period + phase
        beat = beat_amp * math.sin(beat_phase)
        root = bpy.data.objects.get(f"WingRoot_{side}")
        if root is not None:
            rx, ry, rz = _base(_base_rot, root)
            root.rotation_euler = (rx, ry + beat, rz)
        for row in range(3):
            for k in range(N_F):
                fo = bpy.data.objects.get(f"Feather_{side}_{row}_{k}")
                if fo is None or "base_rot" not in fo:
                    continue
                br = fo["base_rot"]
                ripple = 0.5 * beat_amp * math.sin(beat_phase - k * 0.45)
                fo.rotation_euler = (Euler((br[0], br[1] + ripple, br[2]), 'XYZ')
                                     .to_matrix().to_4x4() @ FEATHER_FIX).to_euler()

    # ---- halo flame --------------------------------------------------------
    hm = bpy.data.materials.get("HaloFire")
    if hm is not None and hm.use_nodes:
        noise = next((n for n in hm.node_tree.nodes if n.type == 'TEX_NOISE'), None)
        emit = next((n for n in hm.node_tree.nodes if n.type == 'EMISSION'), None)
        if noise is not None and 'W' in noise.inputs:
            noise.inputs['W'].default_value = t * 1.8
        if emit is not None:
            flicker = 0.65 + 0.45 * math.sin(t * 6.5)
            emit.inputs['Strength'].default_value = 6.0 * _mix(0.18, 1.0, wake) * flicker

    # ---- sun + cloud drift -------------------------------------------------
    sun = bpy.data.objects.get("Sun")
    if sun is not None:
        sun.data.energy = _mix(1.6, 4.2, wake)
    for i, (rz, dx) in enumerate(((0.006, 0.05), (-0.008, -0.04))):
        c = bpy.data.objects.get(f"Cloud_{i}")
        if c is None:
            continue
        br = _base(_base_rot, c)
        c.rotation_euler = (br[0], br[1], br[2] + rz * t)
        c.delta_location = Vector((dx * t * 0.1, 0.0, 0.0))
