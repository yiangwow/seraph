import bpy, sys, time, os
sys.path.insert(0, r"C:\Users\computer\seraph-assets")
from v3_animate import apply_frame_state

OUT_DIR = r"C:\Users\computer\seraph-assets\v3_full"
os.makedirs(OUT_DIR, exist_ok=True)
scene = bpy.context.scene
scene.cycles.samples = 64
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.05
scene.render.use_persistent_data = True
scene.cycles.volume_step_rate = 2.0

FPS = 30
N = 2700
t0 = time.time()
done0 = 0
for f in range(N):
    out = os.path.join(OUT_DIR, f"frame_{f:05d}.png")
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        done0 += 1
        continue  # resume support: skip frames a previous run completed
    apply_frame_state(f / FPS)
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    if f % 100 == 0:
        el = time.time() - t0
        done = f + 1 - done0
        rate = el / max(done, 1)
        print(f"progress {f}/{N} rate={rate:.1f}s/frame eta={rate*(N-f)/3600:.1f}h", flush=True)
print("V3_FULL_DONE", flush=True)
