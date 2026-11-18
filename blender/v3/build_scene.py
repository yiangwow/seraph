"""seraph v3 — dressed scene (Gates 2-3 build). Asset-driven:
ornament-encrusted rings with bezel-set eyes, parchment lids, feather wings
and socket plumage, halo, Disney VDB clouds, puresky world, scale figure.
Run headless via Windows Blender 5.1 from WSL.
"""
import bpy
import bmesh
import glob
import math
import os
import random
from mathutils import Vector, Matrix, Euler

ASSETS = r"C:\Users\computer\seraph-assets"
BK = r"C:\Users\computer\blenderkit_data\models"
OUT = os.path.join(ASSETS, "v3_gate2_dressed.png")

EYE_CENTER = Vector((0.0, 0.0, 0.15))
CAM_LOC = Vector((0.0, -7.3, 0.65))

RING_SPECS = [
    {"major": 2.3, "tube": 0.15, "tilt": (0.62, 0.0, 0.10), "n_eyes": 16, "eye_s": 0.115, "n_orn": 30},
    {"major": 1.5, "tube": 0.10, "tilt": (-0.50, 0.30, 0.0), "n_eyes": 12, "eye_s": 0.088, "n_orn": 20},
]

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


def set_in(bsdf, name, val):
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = val


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


_rng = random.Random(7)

# ---------------------------------------------------------------- materials
copper_mat = bpy.data.materials.new("Copper")
copper_mat.use_nodes = True
cb = copper_mat.node_tree.nodes["Principled BSDF"]
set_in(cb, "Base Color", (0.74, 0.42, 0.28, 1.0))
set_in(cb, "Metallic", 1.0)
set_in(cb, "Roughness", 0.32)
# roughness variation
cn = copper_mat.node_tree.nodes
cl = copper_mat.node_tree.links
rvar = cn.new('ShaderNodeTexNoise')
rvar.inputs['Scale'].default_value = 5.0
rramp = cn.new('ShaderNodeValToRGB')
rramp.color_ramp.elements[0].position = 0.35
rramp.color_ramp.elements[0].color = (0.16, 0.16, 0.16, 1)
rramp.color_ramp.elements[1].position = 0.75
rramp.color_ramp.elements[1].color = (0.55, 0.55, 0.55, 1)
cl.new(rvar.outputs['Fac'], rramp.inputs['Fac'])
cl.new(rramp.outputs['Color'], cb.inputs['Roughness'])

skin_mat = bpy.data.materials.new("ParchmentSkin")
skin_mat.use_nodes = True
sb = skin_mat.node_tree.nodes["Principled BSDF"]
sn = skin_mat.node_tree.nodes
sl = skin_mat.node_tree.links
set_in(sb, "Roughness", 0.55)
set_in(sb, "Subsurface Weight", 0.15)
set_in(sb, "Subsurface Radius", (0.06, 0.03, 0.02))
crease = sn.new('ShaderNodeTexVoronoi')
crease.feature = 'DISTANCE_TO_EDGE'
crease.inputs['Scale'].default_value = 9.0
cbump = sn.new('ShaderNodeBump')
cbump.inputs['Strength'].default_value = 0.6
sl.new(crease.outputs['Distance'], cbump.inputs['Height'])
sl.new(cbump.outputs['Normal'], sb.inputs['Normal'])
stain = sn.new('ShaderNodeTexNoise')
stain.inputs['Scale'].default_value = 3.5
st_ramp = sn.new('ShaderNodeValToRGB')
st_ramp.color_ramp.elements[0].position = 0.35
st_ramp.color_ramp.elements[0].color = (0.90, 0.85, 0.80, 1.0)
st_ramp.color_ramp.elements[1].position = 0.75
st_ramp.color_ramp.elements[1].color = (0.66, 0.45, 0.34, 1.0)
sl.new(stain.outputs['Fac'], st_ramp.inputs['Fac'])
sl.new(st_ramp.outputs['Color'], sb.inputs['Base Color'])

halo_mat = bpy.data.materials.new("HaloFire")
halo_mat.use_nodes = True
hn = halo_mat.node_tree.nodes
hl = halo_mat.node_tree.links
hn.clear()
hout = hn.new('ShaderNodeOutputMaterial')
hemit = hn.new('ShaderNodeEmission')
hnoise = hn.new('ShaderNodeTexNoise')
hnoise.noise_dimensions = '4D'
hnoise.inputs['Scale'].default_value = 8.0
hnoise.inputs['Detail'].default_value = 4.0
hramp = hn.new('ShaderNodeValToRGB')
hramp.color_ramp.elements[0].color = (0.55, 0.10, 0.03, 1.0)
hramp.color_ramp.elements[1].color = (1.0, 0.72, 0.32, 1.0)
hl.new(hnoise.outputs['Fac'], hramp.inputs['Fac'])
hl.new(hramp.outputs['Color'], hemit.inputs['Color'])
hemit.inputs['Strength'].default_value = 6.0
hl.new(hemit.outputs['Emission'], hout.inputs['Surface'])

# ---------------------------------------------------------------- great eye
eye_blend = glob.glob(os.path.join(BK, "realistic-purple*", "*.blend"))[0]
eye_coll, eye_root = append_all_objects(eye_blend, "GreatEyeAsset")
eye_root.name = "GreatEyeRoot"
eye_root.scale = (57.0, 57.0, 57.0)
eye_root.location = EYE_CENTER
gaze = (CAM_LOC - EYE_CENTER).normalized()
eye_root.rotation_euler = (-gaze).to_track_quat('Y', 'Z').to_euler()

lid_crumple = bpy.data.textures.new("LidCrumple", type='CLOUDS')
lid_crumple.noise_scale = 0.22


def hemisphere(name, radius):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=64, ring_count=32,
                                         location=EYE_CENTER)
    obj = bpy.context.object
    obj.name = name
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = [v for v in bm.verts if v.co.z < -1e-3]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.materials.append(skin_mat)
    bpy.ops.object.shade_smooth()
    mod = obj.modifiers.new("Crumple", 'DISPLACE')
    mod.texture = lid_crumple
    mod.strength = 0.07
    return obj


# Round-pupil override: paint a soft-edged black disc over the slit in the
# iris texture's UV space. "PupilR" value node = radius, animatable.
iris_mats = [m for m in bpy.data.materials if 'iris' in m.name.lower()]
for im in iris_mats:
    if not im.use_nodes:
        continue
    nt = im.node_tree
    bsdf_n = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf_n is None:
        continue
    old_link = next((l for l in nt.links if l.to_node == bsdf_n
                     and l.to_socket.name == 'Base Color'), None)
    uv = nt.nodes.new('ShaderNodeTexCoord')
    cen = nt.nodes.new('ShaderNodeVectorMath')
    cen.operation = 'SUBTRACT'
    cen.inputs[1].default_value = (0.5, 0.5, 0.0)
    nt.links.new(uv.outputs['UV'], cen.inputs[0])
    rad_n = nt.nodes.new('ShaderNodeVectorMath')
    rad_n.operation = 'LENGTH'
    nt.links.new(cen.outputs['Vector'], rad_n.inputs[0])
    pupil_r = nt.nodes.new('ShaderNodeValue')
    pupil_r.name = 'PupilR'
    pupil_r.outputs[0].default_value = 0.16
    edge = nt.nodes.new('ShaderNodeMath')
    edge.operation = 'ADD'
    edge.inputs[1].default_value = 0.025
    nt.links.new(pupil_r.outputs[0], edge.inputs[0])
    mask = nt.nodes.new('ShaderNodeMapRange')
    nt.links.new(rad_n.outputs['Value'], mask.inputs['Value'])
    nt.links.new(pupil_r.outputs[0], mask.inputs['From Min'])
    nt.links.new(edge.outputs['Value'], mask.inputs['From Max'])
    mixp = nt.nodes.new('ShaderNodeMixRGB')
    mixp.blend_type = 'MIX'
    mixp.inputs['Color1'].default_value = (0.004, 0.004, 0.006, 1.0)
    nt.links.new(mask.outputs['Result'], mixp.inputs['Fac'])
    if old_link is not None:
        nt.links.new(old_link.from_socket, mixp.inputs['Color2'])
        nt.links.remove(old_link)
    else:
        mixp.inputs['Color2'].default_value = tuple(bsdf_n.inputs['Base Color'].default_value)
    nt.links.new(mixp.outputs['Color'], bsdf_n.inputs['Base Color'])
    if 'Emission Color' in bsdf_n.inputs:
        nt.links.new(mixp.outputs['Color'], bsdf_n.inputs['Emission Color'])
        bsdf_n.inputs['Emission Strength'].default_value = 0.55
    print(f"PUPIL_OVERRIDE on {im.name}")

# The slit is a HOLE in the iris mesh. Backing patch strategy: a full-iris
# disc just behind the iris, colored to continue the iris, with a round
# procedural pupil at its center ("PupilR" value node = dilation hook).
# Through the slit hole you now see iris-tone fill + a round pupil.
patch_mat = bpy.data.materials.new("PupilPatch")
patch_mat.use_nodes = True
pn = patch_mat.node_tree.nodes
pl = patch_mat.node_tree.links
pbsdf = pn["Principled BSDF"]
set_in(pbsdf, "Roughness", 0.35)
pco = pn.new('ShaderNodeTexCoord')
prm = pn.new('ShaderNodeVectorMath')
prm.operation = 'MULTIPLY_ADD'
prm.inputs[1].default_value = (2.0, 2.0, 2.0)
prm.inputs[2].default_value = (-1.0, -1.0, -1.0)
pl.new(pco.outputs['Generated'], prm.inputs[0])
pfl = pn.new('ShaderNodeVectorMath')
pfl.operation = 'MULTIPLY'
pfl.inputs[1].default_value = (1.0, 1.0, 0.0)
pl.new(prm.outputs['Vector'], pfl.inputs[0])
prd = pn.new('ShaderNodeVectorMath')
prd.operation = 'LENGTH'
pl.new(pfl.outputs['Vector'], prd.inputs[0])
pupil_r = pn.new('ShaderNodeValue')
pupil_r.name = 'PupilR'
pupil_r.outputs[0].default_value = 0.37
pedge = pn.new('ShaderNodeMath')
pedge.operation = 'ADD'
pedge.inputs[1].default_value = 0.05
pl.new(pupil_r.outputs[0], pedge.inputs[0])
pmask = pn.new('ShaderNodeMapRange')
pl.new(prd.outputs['Value'], pmask.inputs['Value'])
pl.new(pupil_r.outputs[0], pmask.inputs['From Min'])
pl.new(pedge.outputs['Value'], pmask.inputs['From Max'])
pnoise = pn.new('ShaderNodeTexNoise')
pnoise.inputs['Scale'].default_value = 14.0
pnoise.inputs['Detail'].default_value = 4.0
pmix0 = pn.new('ShaderNodeMixRGB')
pmix0.blend_type = 'MULTIPLY'
pmix0.inputs['Fac'].default_value = 0.35
pmix0.inputs['Color1'].default_value = (0.38, 0.46, 0.53, 1.0)
pl.new(pnoise.outputs['Color'], pmix0.inputs['Color2'])
pmix = pn.new('ShaderNodeMixRGB')
pmix.blend_type = 'MIX'
pmix.inputs['Color1'].default_value = (0.004, 0.004, 0.006, 1.0)
pl.new(pmask.outputs['Result'], pmix.inputs['Fac'])
pl.new(pmix0.outputs['Color'], pmix.inputs['Color2'])
pl.new(pmix.outputs['Color'], pbsdf.inputs['Base Color'])
if 'Emission Color' in pbsdf.inputs:
    pl.new(pmix.outputs['Color'], pbsdf.inputs['Emission Color'])
    pbsdf.inputs['Emission Strength'].default_value = 0.55

bpy.ops.mesh.primitive_circle_add(vertices=64, radius=0.56, fill_type='NGON',
                                  location=EYE_CENTER + gaze * 0.79)
patch = bpy.context.object
patch.name = "PupilPatch"
patch.rotation_euler = gaze.to_track_quat('Z', 'Y').to_euler()
patch.data.materials.append(patch_mat)
patch.parent = eye_root
patch.matrix_parent_inverse = eye_root.matrix_world.inverted()

gm = gaze.to_track_quat('Z', 'Y').to_matrix().to_4x4()
OPEN = 0.85
a_top = -math.radians(90.0 + OPEN * 38.0)
a_bot = math.radians(90.0 + OPEN * 28.0)
top = hemisphere("LidTop", 1.10)
bot = hemisphere("LidBottom", 1.09)
top.rotation_euler = (gm @ Matrix.Rotation(a_top, 4, 'X')).to_euler()
bot.rotation_euler = (gm @ Matrix.Rotation(a_bot, 4, 'X')).to_euler()

# ---------------------------------------------------------------- ornaments
orn_blends = sorted(glob.glob(os.path.join(BK, "baroque-*", "*.blend")))
orn_protos = []
for i, ob_path in enumerate(orn_blends):
    coll, root = append_all_objects(ob_path, f"OrnAsset_{i}")
    meshes = [o for o in coll.objects if o.type == 'MESH']
    for m in meshes:
        m.location = (0, 0, -60 - i * 5)  # park prototypes
        # give every ornament the shared copper material
        m.data.materials.clear()
        m.data.materials.append(copper_mat)
    orn_protos.append(meshes[0])
print(f"ORNAMENTS: {len(orn_protos)}")


def axis_fix_matrix(dims):
    """Map an ornament's local axes: longest axis -> X (tangent),
    shortest -> Z (radial/outward relief normal)."""
    order = sorted(range(3), key=lambda a: -dims[a])
    long_a, mid_a, short_a = order
    basis = [Vector((0, 0, 0)) for _ in range(3)]
    src = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    m = Matrix.Identity(4)
    cols = {0: src[long_a], 1: src[mid_a], 2: src[short_a]}
    m = Matrix((
        (cols[0].x, cols[1].x, cols[2].x, 0),
        (cols[0].y, cols[1].y, cols[2].y, 0),
        (cols[0].z, cols[1].z, cols[2].z, 0),
        (0, 0, 0, 1),
    ))
    return m.inverted()


# ---------------------------------------------------------------- rings
# Trim workflow (how jewelry props are actually built): one carved trim
# piece reoriented long-axis->X, then Array(FIT_CURVE)+Curve modifiers bend
# copies into a continuous carved band around a bezier circle. Spinning the
# circle slides the pattern around the band (conveyor) = ring rotation.
eye_protos = [o for o in eye_coll.objects if o.type == 'MESH']


def reoriented_trim_mesh(proto, target_len):
    me = proto.data.copy()
    dims = proto.dimensions
    order = sorted(range(3), key=lambda a: -dims[a])
    src = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    R = Matrix((src[order[0]], src[order[1]], src[order[2]])).to_4x4()
    sc = target_len / dims[order[0]]
    me.transform(Matrix.Diagonal((sc, sc, sc, 1.0)) @ R)
    return me


# orn_protos sorted by blend path: [acanthus, centerpiece, corner, scrollwork]
TRIM_FOR_RING = {0: 3, 1: 3}

for r, spec in enumerate(RING_SPECS):
    bpy.ops.curve.primitive_bezier_circle_add(radius=spec["major"],
                                              location=EYE_CENTER)
    ring = bpy.context.object
    ring.name = f"Ring_{r}"
    ring.rotation_euler = spec["tilt"]

    tilt_mat = Euler(spec["tilt"], 'XYZ').to_matrix().to_4x4()

    # slim base band under the trim (fills gaps, carries silhouette)
    bpy.ops.mesh.primitive_torus_add(major_radius=spec["major"],
                                     minor_radius=spec["tube"] * 0.7,
                                     major_segments=128, minor_segments=24,
                                     location=EYE_CENTER)
    band = bpy.context.object
    band.name = f"Band_{r}"
    band.rotation_euler = spec["tilt"]
    band.data.materials.append(copper_mat)
    bpy.ops.object.shade_smooth()
    band.parent = ring
    band.matrix_parent_inverse = ring.matrix_world.inverted()

    # continuous carved trim around the band — outer wheel only. The inner
    # wheel stays a sleek polished band + bezel eyes (trim shreds on its
    # tight curvature, and the ornate/sleek contrast reads intentional).
    if r == 0:
        tproto = orn_protos[TRIM_FOR_RING[r]]
        tme = reoriented_trim_mesh(tproto, 0.95)
        trim = bpy.data.objects.new(f"Trim_{r}", tme)
        bpy.context.collection.objects.link(trim)
        if not trim.data.materials:
            trim.data.materials.append(copper_mat)
        trim.location = EYE_CENTER
        trim.rotation_euler = spec["tilt"]
        arr = trim.modifiers.new("Arr", 'ARRAY')
        arr.fit_type = 'FIT_CURVE'
        arr.curve = ring
        arr.use_relative_offset = True
        arr.relative_offset_displace = (0.96, 0.0, 0.0)   # slight overlap
        crv = trim.modifiers.new("Crv", 'CURVE')
        crv.object = ring
        crv.deform_axis = 'POS_X'
    else:
        band.scale = (1.0, 1.0, 1.35)

    # bezel-set eyes at strict rhythm on the band front
    for j in range(spec["n_eyes"]):
        ang = (j / spec["n_eyes"]) * 2 * math.pi + 0.11
        local = Vector((math.cos(ang) * spec["major"], math.sin(ang) * spec["major"],
                        spec["tube"] * 0.62))
        world_pos = EYE_CENTER + (tilt_mat.to_3x3() @ local)
        bpy.ops.mesh.primitive_torus_add(major_radius=spec["eye_s"] * 1.05,
                                         minor_radius=spec["eye_s"] * 0.35,
                                         major_segments=32, minor_segments=12,
                                         location=world_pos)
        bez = bpy.context.object
        bez.name = f"Bezel_{r}_{j}"
        bez.rotation_euler = spec["tilt"]
        bez.data.materials.append(copper_mat)
        bpy.ops.object.shade_smooth()
        bez.parent = ring
        bez.matrix_parent_inverse = ring.matrix_world.inverted()
        front = (tilt_mat.to_3x3() @ Vector((0, 0, 1))).normalized()
        fq = (-front).to_track_quat('Y', 'Z')
        cq = (-(CAM_LOC - world_pos).normalized()).to_track_quat('Y', 'Z')
        eq = fq.slerp(cq, 0.55)
        for pm in eye_protos:
            ec = pm.copy()
            ec.parent = None
            ec.name = f"RingEye_{r}_{j}_{pm.name.split('_')[0]}"
            ec.scale = (spec["eye_s"],) * 3
            ec.location = world_pos
            ec.rotation_euler = eq.to_euler()
            bpy.context.collection.objects.link(ec)
            ec.parent = ring
            ec.matrix_parent_inverse = ring.matrix_world.inverted()

# third ring: slim steep outer wheel — wheels within wheels density
bpy.ops.mesh.primitive_torus_add(major_radius=3.05, minor_radius=0.045,
                                 major_segments=128, minor_segments=16,
                                 location=EYE_CENTER)
ring2 = bpy.context.object
ring2.name = "Ring_2"
ring2.rotation_euler = (1.30, 0.18, 0.0)
ring2.data.materials.append(copper_mat)
bpy.ops.object.shade_smooth()
t2 = Euler((1.30, 0.18, 0.0), 'XYZ').to_matrix()
for j in range(8):
    ang = (j / 8) * 2 * math.pi
    wp = EYE_CENTER + (t2 @ Vector((math.cos(ang) * 3.05, math.sin(ang) * 3.05, 0.05)))
    for pm in eye_protos:
        ec = pm.copy()
        ec.parent = None
        ec.name = f"Ring2Eye_{j}_{pm.name.split('_')[0]}"
        ec.scale = (0.07,) * 3
        ec.location = wp
        cq = (-(CAM_LOC - wp).normalized()).to_track_quat('Y', 'Z')
        ec.rotation_euler = cq.to_euler()
        bpy.context.collection.objects.link(ec)
        ec.parent = ring2
        ec.matrix_parent_inverse = ring2.matrix_world.inverted()

# ---------------------------------------------------------------- feathers
feather_blend = glob.glob(os.path.join(BK, "angel-wings_*", "*.blend"))[0]
f_coll, f_root = append_all_objects(feather_blend, "FeatherAsset")
f_meshes = [o for o in f_coll.objects if o.type == 'MESH']
proto = f_meshes[0]
proto.location = (0, 0, -50)
f_len = max(proto.dimensions)

FEATHER_FIX = (Matrix.Rotation(math.radians(90), 4, 'X')
               @ Matrix.Rotation(math.radians(-90), 4, 'Z'))
ROW_LEN = [1.2, 1.9, 2.7]
N_F = 16


def feather_clone(name, length, loc, rot):
    c = proto.copy()
    c.name = name
    s = length / f_len
    c.scale = (s, s, s)
    c.location = loc
    c.rotation_euler = (Euler(rot, 'XYZ').to_matrix().to_4x4() @ FEATHER_FIX).to_euler()
    bpy.context.collection.objects.link(c)
    return c


# wings: fan starts lower (no ear-tufts), roots slightly wider
for side, sx in (("L", -1.0), ("R", 1.0)):
    base = Vector((sx * 1.7, 0.95, -0.15))
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=base)
    wroot = bpy.context.object
    wroot.name = f"WingRoot_{side}"
    for row in range(3):
        for k in range(N_F):
            tk = k / (N_F - 1)
            fan = 0.10 - tk * 1.85
            f2 = fan * 0.55
            r_arm = 0.45 + 0.75 * tk - 0.14 * row
            loc = base + Vector((sx * r_arm * math.cos(f2), -0.06 * row,
                                 r_arm * math.sin(f2) + 0.05 * row))
            ln = ROW_LEN[row] * (1.0 + _rng.uniform(-0.1, 0.1))
            rot = (_rng.uniform(-0.06, 0.06),
                   -(fan + row * 0.04) * sx,
                   math.pi if sx < 0 else 0.0)
            fc = feather_clone(f"Feather_{side}_{row}_{k}", ln, loc, rot)
            fc["base_rot"] = list(rot)
            fc["fk"] = k
            fc.parent = wroot
            fc.matrix_parent_inverse = wroot.matrix_world.inverted()

# socket plumage: sides + hanging below only
for ring_i, (rad0, ln0, y_off) in enumerate([(0.62, 0.55, 0.55), (0.78, 0.85, 0.75)]):
    for i in range(22):
        ang = (i / 22) * 2 * math.pi + ring_i * 0.12
        droop = max(0.0, -math.sin(ang))
        rise = max(0.0, math.sin(ang))
        if rise > 0.55:
            continue
        ln = ln0 * (1 + _rng.uniform(-0.2, 0.2)) * (1 + 2.2 * droop) * (1 - 0.45 * rise)
        swirl = 0.65 * (1.0 - droop) + _rng.uniform(-0.12, 0.12)
        rj = rad0 * (1.0 + _rng.uniform(-0.12, 0.12))
        loc = EYE_CENTER + Vector((math.cos(ang) * rj, y_off + _rng.uniform(-0.08, 0.08),
                                   math.sin(ang) * rj))
        feather_clone(f"SocketF_{ring_i}_{i}", ln, loc,
                      (_rng.uniform(-0.06, 0.06), -(ang + swirl), 0.0))

# ---------------------------------------------------------------- halo
bpy.ops.mesh.primitive_torus_add(major_radius=3.1, minor_radius=0.13,
                                 major_segments=96, minor_segments=20,
                                 location=(0.0, 2.8, 0.7))
halo = bpy.context.object
halo.name = "Halo"
halo.rotation_euler = (math.pi / 2, 0.0, 0.0)
halo.data.materials.append(halo_mat)

# ---------------------------------------------------------------- clouds + sky
vdb = os.path.join(ASSETS, "clouds", "wdas_cloud", "wdas_cloud_quarter.vdb")
bpy.ops.object.volume_import(filepath=vdb, align='WORLD')
cloud = bpy.context.object
cloud.name = "Cloud_0"
cd = max(cloud.dimensions)
cs = 30.0 / cd
cloud.scale = (cs, cs, cs)
cloud.location = (4.0, 14.0, -9.0)
cloud2 = cloud.copy()
cloud2.name = "Cloud_1"
cloud2.scale = (cs * 0.7, cs * 0.7, cs * 0.7)
cloud2.location = (-11.0, 9.0, -7.5)
cloud2.rotation_euler = (0, 0, 2.4)
bpy.context.collection.objects.link(cloud2)

haze_mat = bpy.data.materials.new("GodHaze")
haze_mat.use_nodes = True
hzn = haze_mat.node_tree.nodes
hzn.clear()
hout = hzn.new('ShaderNodeOutputMaterial')
hvol = hzn.new('ShaderNodeVolumeScatter')
hvol.inputs['Density'].default_value = 0.008
hvol.inputs['Anisotropy'].default_value = 0.55
haze_mat.node_tree.links.new(hvol.outputs['Volume'], hout.inputs['Volume'])
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 4.0, 1.0))
hazebox = bpy.context.object
hazebox.name = "GodHaze"
hazebox.scale = (12.0, 10.0, 6.0)
hazebox.data.materials.append(haze_mat)

world = bpy.data.worlds.new("Sky")
scene.world = world
world.use_nodes = True
wn = world.node_tree
env = wn.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load(os.path.join(ASSETS, "hdri", "wasteland_clouds_puresky_4k.exr"))
bg = wn.nodes["Background"]
bg.inputs["Strength"].default_value = 1.0
wn.links.new(env.outputs["Color"], bg.inputs["Color"])
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

bpy.ops.object.light_add(type='SUN', location=(0.0, 10.0, 5.0))
sun = bpy.context.object
sun.name = "Sun"
sun.data.energy = 3.2
sun.data.angle = 0.06
sun.data.color = (1.0, 0.86, 0.70)
sun.rotation_euler = Vector((0.0, -10.0, -4.5)).to_track_quat('-Z', 'Y').to_euler()

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

# grade: AgX + compositor glare/grain/vignette
try:
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Punchy'
except Exception as e:
    print("VIEWXFORM", e)
# Blender 5.x compositor: standalone node group; assign only when the
# whole tree built and linked successfully
try:
    ng = bpy.data.node_groups.new('SeraphComp', 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new('CompositorNodeRLayers')
    glare = ng.nodes.new('CompositorNodeGlare')
    for attr, val in (('glare_type', 'FOG_GLOW'), ('mode', 'FOG_GLOW')):
        if hasattr(glare, attr):
            try:
                setattr(glare, attr, val)
                break
            except Exception:
                pass
    for attr, val in (('quality', 'HIGH'), ('mix', -0.55)):
        if hasattr(glare, attr):
            try:
                setattr(glare, attr, val)
            except Exception:
                pass
    for sock, val in (('Strength', 0.35), ('Mix', -0.55), ('Threshold', 1.0)):
        if sock in glare.inputs:
            try:
                glare.inputs[sock].default_value = val
            except Exception:
                pass
    lens = ng.nodes.new('CompositorNodeLensdist')
    if hasattr(lens, 'use_fit'):
        lens.use_fit = True
    if 'Dispersion' in lens.inputs:
        lens.inputs['Dispersion'].default_value = 0.012
    gout = ng.nodes.new('NodeGroupOutput')
    ng.links.new(rl.outputs['Image'], glare.inputs['Image'])
    ng.links.new(glare.outputs['Image'], lens.inputs['Image'])
    ng.links.new(lens.outputs['Image'], gout.inputs[0])
    scene.compositing_node_group = ng
    print("COMPOSITOR_OK")
except Exception as e:
    scene.compositing_node_group = None
    print("COMPOSITOR_SKIP", e)

if not os.environ.get('SERAPH_NO_STILL'):
    scene.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
print("GATE2_DONE", OUT)
