"""seraph 3D scene — first pass. Real geometry: interlocking toruses (wheels),
lens-shaped eyes set into the rings, layered curved wing strips, an emissive
halo ring behind everything. All procedural (no imported assets/textures).
Run: blender --background --python blender/build_scene.py
"""
import bpy
import math
import mathutils

OUT = "/home/unix/seraph/blender/renders/still_001.png"


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in list(bpy.data.meshes):
        if block.users == 0:
            bpy.data.meshes.remove(block)


def make_emissive_material(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    emit.inputs['Color'].default_value = (*color, 1.0)
    emit.inputs['Strength'].default_value = strength
    links.new(emit.outputs['Emission'], out.inputs['Surface'])
    return mat


def make_flicker_emissive_material(name, color_low, color_high, strength):
    """Emission strength/color varies across the surface via noise, so the
    halo reads as uneven flame rather than a flat glowing ring."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    noise = nodes.new('ShaderNodeTexNoise')
    # 4D so animate.py can advance the 'W' input as a time axis, churning the
    # flame field each frame instead of leaving a frozen noise pattern.
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 8.0
    noise.inputs['Detail'].default_value = 4.0
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*color_low, 1.0)
    ramp.color_ramp.elements[1].color = (*color_high, 1.0)
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], emit.inputs['Color'])
    emit.inputs['Strength'].default_value = strength
    links.new(emit.outputs['Emission'], out.inputs['Surface'])
    return mat


def make_metal_material(name, color, rough=0.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def make_wing_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.92, 0.82, 0.60, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Alpha"].default_value = 0.95
    if "Emission" in bsdf.inputs:
        bsdf.inputs["Emission"].default_value = (0.35, 0.28, 0.15, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.6
    mat.blend_method = 'BLEND'
    return mat


clear_scene()

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_bloom = True
scene.eevee.bloom_intensity = 0.12
scene.eevee.bloom_threshold = 0.9
scene.eevee.use_gtao = True
scene.eevee.use_ssr = True
scene.render.resolution_x = 960
scene.render.resolution_y = 960
scene.render.film_transparent = False

world = bpy.data.worlds.new("SeraphWorld")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.005, 0.004, 0.008, 1.0)
bg.inputs[1].default_value = 1.0

# ---- WHEELS: interlocking toruses, each tilted on its own real 3D axis ----
wheel_mat = make_metal_material("WheelGold", (0.85, 0.65, 0.25), 0.25)
wheel_specs = [
    {"radius": 1.6, "tube": 0.045, "tilt": (0.3, 0.0, 0.0), "n_eyes": 10},
    {"radius": 1.3, "tube": 0.040, "tilt": (0.0, 0.6, 0.5), "n_eyes": 8},
    {"radius": 1.0, "tube": 0.035, "tilt": (0.55, -0.4, 0.25), "n_eyes": 7},
]

for i, spec in enumerate(wheel_specs):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=spec["radius"], minor_radius=spec["tube"],
        major_segments=72, minor_segments=16)
    torus = bpy.context.object
    torus.name = f"Wheel_{i}"
    torus.rotation_euler = spec["tilt"]
    torus.data.materials.append(wheel_mat)

# ---- EYES: lens shapes set into each ring's surface ----
iris_mat = make_emissive_material("IrisAmber", (1.0, 0.55, 0.15), 5.0)
pupil_mat = make_metal_material("PupilBlack", (0.01, 0.01, 0.01), 0.1)

for i, spec in enumerate(wheel_specs):
    rot_mat = mathutils.Euler(spec["tilt"], 'XYZ').to_matrix()
    # Parent every eye/pupil to its wheel so that when animate.py spins the
    # wheel about its own axis, the eyes ride the rim with it. This is what
    # makes wheel rotation *visible* at all — a smooth, rotationally-symmetric
    # torus spun about its normal shows nothing; the orbiting eyes are the only
    # features that reveal the spin. The parent inverse is the wheel's own tilt
    # matrix (wheel sits at the origin, so world = tilt rotation), which cancels
    # at bind time and leaves each eye at its authored world position.
    wheel_obj = bpy.data.objects[f"Wheel_{i}"]
    parent_inv = rot_mat.to_4x4().inverted()
    for j in range(spec["n_eyes"]):
        ang = (j / spec["n_eyes"]) * 2 * math.pi
        local = mathutils.Vector((math.cos(ang) * spec["radius"], math.sin(ang) * spec["radius"], 0))
        world_pos = rot_mat @ local
        normal_local = mathutils.Vector((math.cos(ang), math.sin(ang), 0))
        normal_world = rot_mat @ normal_local
        eye_rot = normal_world.to_track_quat('Z', 'Y').to_euler()

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=world_pos, segments=14, ring_count=7)
        eye = bpy.context.object
        eye.name = f"Eye_{i}_{j}"
        eye.scale = (1.0, 1.0, 0.3)
        eye.rotation_euler = eye_rot
        eye.data.materials.append(iris_mat)
        eye.parent = wheel_obj
        eye.matrix_parent_inverse = parent_inv

        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.022, location=world_pos, segments=10, ring_count=5)
        pupil = bpy.context.object
        pupil.name = f"Pupil_{i}_{j}"
        pupil.location = world_pos + normal_world * 0.01
        pupil.scale = (1.0, 1.0, 0.25)
        pupil.rotation_euler = eye_rot
        pupil.data.materials.append(pupil_mat)
        pupil.parent = wheel_obj
        pupil.matrix_parent_inverse = parent_inv

# ---- WINGS: layered curved strips fanned behind the wheels ----
wing_mat = make_wing_material("WingCream")
N_WINGS = 10
N_LAYERS = 3
for i in range(N_WINGS):
    base_ang = (i / N_WINGS) * 2 * math.pi
    for layer in range(N_LAYERS):
        curve = bpy.data.curves.new(f"WingCurve_{i}_{layer}", type='CURVE')
        curve.dimensions = '3D'
        curve.twist_mode = 'Z_UP'  # keep ribbon's flat face oriented toward world-Z
        # (and thus toward the elevated camera) along the whole curve, not just at bends
        curve.bevel_depth = 0.010  # small supplemental round thickness, reads at any angle
        curve.bevel_resolution = 2
        curve.extrude = 0.22 - 0.045 * layer  # flat ribbon width; outer layers narrower
        curve.fill_mode = 'FULL'
        curve.use_fill_caps = True
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(3)
        z_lift = 0.10 * layer
        # Wider angular spread between the 3 layers than before (0.16 vs 0.10 rad) so
        # the now-wider ribbons diverge instead of piling on top of each other and
        # self-intersecting (which produced jagged alpha-sorting artifacts at width 0.30).
        layer_ang = base_ang + (layer - 1) * 0.16
        # radius scales the WHOLE cross-section (bevel_depth + extrude) at each point.
        # Root stays moderate (0.35, wider than the original 0.22 but nowhere near the
        # overshot 0.90) and the floor stays a healthy fraction of root (0.20 vs root's
        # 0.35, ~57%) so the ribbon reads as a visibly tapered blade along its whole
        # length instead of collapsing to a hairline or ballooning into overlap.
        pts = [
            (0.85, 0.00, 0.05 + z_lift, 0.35),
            (1.55, 0.35, 0.25 + z_lift, 0.29),
            (2.15, 0.30, 0.15 + z_lift, 0.24),
            (2.55, 0.05, -0.05 + z_lift, 0.20),
        ]
        for k, (x, y, z, rad) in enumerate(pts):
            bp = spline.bezier_points[k]
            bp.co = (x, y, z)
            bp.radius = rad
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
        obj = bpy.data.objects.new(f"Wing_{i}_{layer}", curve)
        bpy.context.collection.objects.link(obj)
        obj.rotation_euler = (0, 0, layer_ang)
        obj.data.materials.append(wing_mat)

# ---- HALO: emissive ring behind everything ----
halo_mat = make_flicker_emissive_material("HaloFire", (0.5, 0.08, 0.02), (1.0, 0.75, 0.3), 1.4)
bpy.ops.mesh.primitive_torus_add(major_radius=2.9, minor_radius=0.10, major_segments=96, minor_segments=20)
halo = bpy.context.object
halo.name = "Halo"
halo.data.materials.append(halo_mat)

# ---- Lighting: the piece is mostly self-illuminating; one dim rim light for shape ----
bpy.ops.object.light_add(type='AREA', location=(-3, -4, 3))
rim = bpy.context.object
rim.data.energy = 80
rim.data.size = 3
rim.rotation_euler = (1.1, 0, -0.7)

# ---- Camera: elevated 3/4 view looking down at the composition (which is
# arranged roughly in the XY plane), via a Track-To constraint at the origin
# so we don't have to hand-derive Euler angles ----
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
target = bpy.context.object
target.name = "CameraTarget"

bpy.ops.object.camera_add(location=(0, -4.2, 5.2))
cam = bpy.context.object
scene.camera = cam
constraint = cam.constraints.new(type='TRACK_TO')
constraint.target = target
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

import os
os.makedirs(os.path.dirname(OUT), exist_ok=True)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("RENDER_DONE", OUT)
