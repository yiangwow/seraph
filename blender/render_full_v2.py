"""Full-quality render of the whole 90s piece: 2700 frames @ 30fps, 64
samples, 1080x1080. Run AFTER build_scene_v2.py in the same invocation:
MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background \
  --python blender/build_scene_v2.py --python blender/render_full_v2.py
Then mux with the real track (see v2 plan Task 5):
ffmpeg -framerate 30 -i frame_%05d.png -i audio/seraph-clip.mp3 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest dist/seraph-v2.mp4
"""
import bpy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from animate_v2 import apply_frame_state

OUT_DIR = "/home/unix/seraph/blender/renders/full_v2"
os.makedirs(OUT_DIR, exist_ok=True)

FPS = 30
N_FRAMES = 2700  # 90.00s

scene = bpy.context.scene
scene.eevee.taa_render_samples = 64

for f in range(N_FRAMES):
    apply_frame_state(f / FPS)
    scene.render.filepath = f"{OUT_DIR}/frame_{f:05d}.png"
    bpy.ops.render.render(write_still=True)
    if f % 300 == 0:
        print(f"progress frame {f}/{N_FRAMES}")

print("FULL_RENDER_DONE")
