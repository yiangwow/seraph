import bpy, sys, time, os
sys.path.insert(0, r"C:\Users\computer\seraph-assets")
from v3_animate import apply_frame_state

OUT_DIR = r"C:\Users\computer\seraph-assets\v3_preview"
os.makedirs(OUT_DIR, exist_ok=True)
scene = bpy.context.scene
scene.cycles.samples = 64
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.05
scene.render.use_persistent_data = True
scene.cycles.volume_step_rate = 2.0
t0 = time.time()
for t in range(0, 94, 3):
    apply_frame_state(float(t))
    scene.render.filepath = os.path.join(OUT_DIR, f"t_{t:03d}.png")
    bpy.ops.render.render(write_still=True)
n = len(range(0, 94, 3))
print(f"PREVIEW_DONE {n} frames, {(time.time()-t0)/n:.2f}s/frame steady-state")
