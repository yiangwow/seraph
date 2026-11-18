"""seraph v3 — Gate 1 blockout. Real assets, placeholder dressing:
composition check only. Run via Windows Blender 5.1 headless from WSL.
"""
import bpy
import glob
import math
import os
import random
from mathutils import Vector, Matrix

ASSETS = r"C:\Users\computer\seraph-assets"
BK = r"C:\Users\computer\blenderkit_data\models"
OUT = os.path.join(ASSETS, "v3_gate1_blockout.png")

EYE_CENTER = Vector((0.0, 0.0, 0.15))
CAM_LOC = Vector((0.0, -7.3, 0.65))

# ---------------------------------------------------------------- gpu/scene
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'HIP'
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == 'HIP'

bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080


def append_all_objects(blend_path, collection_name):
    coll = bpy.data.collections.new(collection_name)
    scene.collection.children.link(coll)
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        dst.objects = src.objects
    root = None
    for ob in dst.objects:
        if ob is not None:
            coll.objects.link(ob)
            if ob.parent is None:
                root = ob
    return coll, root


# ---------------------------------------------------------------- great eye
eye_blend = glob.glob(os.path.join(BK, "realistic-purple*", "*.blend"))[0]
eye_coll, eye_root = append_all_objects(eye_blend, "GreatEyeAsset")
# asset is anatomically scaled (~3.5cm); world radius 0.0173 -> x57 ~= 1.0
eye_root.name = "GreatEyeRoot"
eye_root.scale = (57.0, 57.0, 57.0)
eye_root.location = EYE_CENTER
gaze = (CAM_LOC - EYE_CENTER).normalized()
# asset iris faces -Y in local space (iris obj offset -0.0144 in y)
eye_root.rotation_euler = (-gaze).to_track_quat('Y', 'Z').to_euler()

# lids: plain shells for blockout (crumple + skin comes at Gate 2)
lid_mat = bpy.data.materials.new("LidBlock")
lid_mat.use_nodes = True
lid_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.85, 0.78, 0.70, 1)


def hemisphere(name, radius):
    import bmesh
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=48, ring_count=24,
                                         location=EYE_CENTER)
    obj = bpy.context.object
    obj.name = name
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = [v for v in bm.verts if v.co.z < -1e-3]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.materials.append(lid_mat)
    bpy.ops.object.shade_smooth()
    return obj


gm = gaze.to_track_quat('Z', 'Y').to_matrix().to_4x4()
OPEN = 0.85
a_top = -math.radians(90.0 + OPEN * 38.0)
a_bot = math.radians(90.0 + OPEN * 28.0)
top = hemisphere("LidTop", 1.10)
bot = hemisphere("LidBottom", 1.09)
top.rotation_euler = (gm @ Matrix.Rotation(a_top, 4, 'X')).to_euler()
bot.rotation_euler = (gm @ Matrix.Rotation(a_bot, 4, 'X')).to_euler()

# ---------------------------------------------------------------- rings (placeholder)
ring_mat = bpy.data.materials.new("RingBlock")
ring_mat.use_nodes = True
rb = ring_mat.node_tree.nodes["Principled BSDF"]
rb.inputs["Base Color"].default_value = (0.72, 0.40, 0.26, 1)
rb.inputs["Metallic"].default_value = 1.0
rb.inputs["Roughness"].default_value = 0.35

RING_SPECS = [
    {"major": 2.3, "tube": 0.16, "tilt": (0.62, 0.0, 0.10)},
    {"major": 1.5, "tube": 0.11, "tilt": (-0.50, 0.30, 0.0)},
]
for i, spec in enumerate(RING_SPECS):
    bpy.ops.mesh.primitive_torus_add(major_radius=spec["major"], minor_radius=spec["tube"],
                                     major_segments=96, minor_segments=24,
                                     location=EYE_CENTER)
    ring = bpy.context.object
    ring.name = f"Ring_{i}"
    ring.rotation_euler = spec["tilt"]
    ring.data.materials.append(ring_mat)
    bpy.ops.object.shade_smooth()

# ---------------------------------------------------------------- feathers
feather_blend = glob.glob(os.path.join(BK, "angel-wings_*", "*.blend"))[0]
f_coll, f_root = append_all_objects(feather_blend, "FeatherAsset")
f_meshes = [o for o in f_coll.objects if o.type == 'MESH']
proto = f_meshes[0]
proto.location = (0, 0, -50)  # park the prototype out of view

# feather asset world length (longest bbox axis)
dims = proto.dimensions
f_len = max(dims)
print(f"FEATHER dims={tuple(round(v,3) for v in dims)}")

_rng = random.Random(7)
ROW_LEN = [1.2, 1.9, 2.7]
N_F = 16


FEATHER_FIX = (Matrix.Rotation(math.radians(90), 4, 'X')
               @ Matrix.Rotation(math.radians(-90), 4, 'Z'))


def feather_clone(name, length, loc, rot):
    c = proto.copy()  # linked mesh data — cheap
    c.name = name
    s = length / f_len
    c.scale = (s, s, s)
    c.location = loc
    from mathutils import Euler
    c.rotation_euler = (Euler(rot, 'XYZ').to_matrix().to_4x4() @ FEATHER_FIX).to_euler()
    bpy.context.collection.objects.link(c)
    return c


# wings: v2 shoulder-arc cradle layout
for side, sx in (("L", -1.0), ("R", 1.0)):
    base = Vector((sx * 1.55, 0.95, -0.1))
    for row in range(3):
        for k in range(N_F):
            tk = k / (N_F - 1)
            fan = 0.35 - tk * 1.9
            f2 = fan * 0.55
            r_arm = 0.45 + 0.75 * tk - 0.14 * row
            loc = base + Vector((sx * r_arm * math.cos(f2), -0.06 * row,
                                 r_arm * math.sin(f2) + 0.05 * row))
            ln = ROW_LEN[row] * (1.0 + _rng.uniform(-0.1, 0.1))
            rot = (_rng.uniform(-0.06, 0.06),
                   -(fan + row * 0.04) * sx,
                   math.pi if sx < 0 else 0.0)
            feather_clone(f"Feather_{side}_{row}_{k}", ln, loc, rot)

# socket plumage: corona + hanging under-feathers
for ring_i, (rad0, ln0, y_off) in enumerate([(0.62, 0.55, 0.55), (0.78, 0.85, 0.75)]):
    for i in range(22):
        ang = (i / 22) * 2 * math.pi + ring_i * 0.12
        droop = max(0.0, -math.sin(ang))
        rise = max(0.0, math.sin(ang))
        if rise > 0.55:
            continue  # no top-quadrant tufts — plumage lives at sides/below
        ln = ln0 * (1 + _rng.uniform(-0.2, 0.2)) * (1 + 2.2 * droop) * (1 - 0.45 * rise)
        swirl = 0.65 * (1.0 - droop) + _rng.uniform(-0.12, 0.12)
        rj = rad0 * (1.0 + _rng.uniform(-0.12, 0.12))
        loc = EYE_CENTER + Vector((math.cos(ang) * rj, y_off + _rng.uniform(-0.08, 0.08),
                                   math.sin(ang) * rj))
        feather_clone(f"SocketF_{ring_i}_{i}", ln, loc,
                      (_rng.uniform(-0.06, 0.06), -(ang + swirl), 0.0))

# ---------------------------------------------------------------- clouds + sky
vdb = os.path.join(ASSETS, "clouds", "wdas_cloud", "wdas_cloud_eighth.vdb")
bpy.ops.object.volume_import(filepath=vdb, align='WORLD')
cloud = bpy.context.object
cloud.name = "Cloud_0"
cd = max(cloud.dimensions)
print(f"CLOUD dims={tuple(round(v,2) for v in cloud.dimensions)}")
cs = 30.0 / cd
cloud.scale = (cs, cs, cs)
cloud.location = (4.0, 14.0, -9.0)
cloud2 = cloud.copy()
cloud2.name = "Cloud_1"
cloud2.scale = (cs * 0.7, cs * 0.7, cs * 0.7)
cloud2.location = (-11.0, 9.0, -7.5)
cloud2.rotation_euler = (0, 0, 2.4)
bpy.context.collection.objects.link(cloud2)

world = bpy.data.worlds.new("Sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
env = wn.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(os.path.join(ASSETS, "hdri", "wasteland_clouds_puresky_4k.exr"))
bg = wn.nodes["Background"]
bg.inputs["Strength"].default_value = 1.0
wn.links.new(env.outputs["Color"], bg.inputs["Color"])
# rotate sun behind the being
mapping = wn.nodes.new('ShaderNodeMapping')
coord = wn.nodes.new('ShaderNodeTexCoord')
mapping.inputs['Rotation'].default_value = (0, 0, math.radians(90))
wn.links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
wn.links.new(mapping.outputs['Vector'], env.inputs['Vector'])

# ---------------------------------------------------------------- figure + camera
rock_mat = bpy.data.materials.new("RockDark")
rock_mat.use_nodes = True
rock_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.045, 0.05, 1)
bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.30, radius2=0.05, depth=1.1,
                                location=(-0.85, -4.6, -1.0))
rock = bpy.context.object
rock.rotation_euler = (0.06, 0.1, 0.5)
rock.data.materials.append(rock_mat)
fig_mat = bpy.data.materials.new("FigDark")
fig_mat.use_nodes = True
fig_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.018, 0.02, 1)
bpy.ops.mesh.primitive_cylinder_add(radius=0.0065, depth=0.034, location=(-0.78, -4.6, -0.443))
bpy.context.object.data.materials.append(fig_mat)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006, segments=12, ring_count=6,
                                     location=(-0.78, -4.6, -0.42))
bpy.context.object.data.materials.append(fig_mat)

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0.15))
target = bpy.context.object
target.name = "CameraTarget"
bpy.ops.object.camera_add(location=CAM_LOC)
cam = bpy.context.object
scene.camera = cam
con = cam.constraints.new(type='TRACK_TO')
con.target = target
con.track_axis = 'TRACK_NEGATIVE_Z'
con.up_axis = 'UP_Y'

scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("GATE1_DONE", OUT)
