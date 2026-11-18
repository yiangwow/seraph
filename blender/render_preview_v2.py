"""Sparse preview across the whole 90s for contact-sheet verification.
Run AFTER build_scene_v2.py in the same blender invocation:
MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background \
  --python blender/build_scene_v2.py --python blender/render_preview_v2.py
"""
import bpy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animate_v2 import apply_frame_state

OUT_DIR = "/home/unix/seraph/blender/renders/preview_v2"
os.makedirs(OUT_DIR, exist_ok=True)

scene = bpy.context.scene
scene.eevee.taa_render_samples = 24  # preview quality
times = list(range(0, 94, 3))        # 0,3,...,93 — 32 frames

for t in times:
    apply_frame_state(float(t))
    scene.render.filepath = f"{OUT_DIR}/t_{t:03d}.png"
    bpy.ops.render.render(write_still=True)
    print(f"rendered t={t}")

print("PREVIEW_DONE")
