"""seraph v2 — "Heaven" scene. The reference images govern: a colossal pale
ophanim in bright heaven — one giant lidded eye, fat carved copper rings
studded with eyes, great feathered wing fans, volumetric clouds, god-light.
All procedural (no imported assets/textures, nothing AI-generated).
Run: MESA_D3D12_DEFAULT_ADAPTER_NAME=AMD blender --background --python blender/build_scene_v2.py
"""
import bpy
import bmesh
import math
import mathutils
from mathutils import Vector, Matrix

OUT = "/home/unix/seraph/blender/renders/still_v2.png"

EYE_CENTER = Vector((0.0, 0.0, 0.15))
CAM_LOC = Vector((0.0, -7.3, 0.65))

RING_SPECS = [
    # major, tube, tilt, n_eyes, eye_r
    {"major": 2.3, "tube": 0.20, "tilt": (0.62, 0.0, 0.10), "n_eyes": 20, "eye_r": 0.11},
    {"major": 1.5, "tube": 0.13, "tilt": (-0.50, 0.30, 0.0), "n_eyes": 14, "eye_r": 0.09},
]

N_FEATHERS = 16
ROW_LEN = [1.2, 1.9, 2.7]     # coverts, secondaries, primaries
ROW_WID = [0.30, 0.34, 0.38]  # broad blades (refs), heavy overlap


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.textures):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


# ---------------------------------------------------------------- materials
def make_eyeball_material():
    """Shared by the great eye and every ring eye. Moon-pale iris with radial
    striations, veined sclera darkening toward the lids, pupil ramp.
    Contract with animate_v2: node "EyeRadialRamp" elements[0]/[1] positions
    are the pupil edge; Principled "Emission Strength" is the iris glow."""
    mat = bpy.data.materials.new("EyeballMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.18
    bsdf.inputs["Specular"].default_value = 0.55
    bsdf.inputs["Clearcoat"].default_value = 0.3

    coord = nodes.new('ShaderNodeTexCoord')
    remap = nodes.new('ShaderNodeVectorMath')
    remap.operation = 'MULTIPLY_ADD'
    remap.inputs[1].default_value = (2.0, 2.0, 2.0)
    remap.inputs[2].default_value = (-1.0, -1.0, -1.0)
    links.new(coord.outputs['Generated'], remap.inputs[0])
    sep = nodes.new('ShaderNodeSeparateXYZ')
    links.new(remap.outputs['Vector'], sep.inputs['Vector'])
    flat = nodes.new('ShaderNodeVectorMath')
    flat.operation = 'MULTIPLY'
    flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    links.new(remap.outputs['Vector'], flat.inputs[0])
    rad = nodes.new('ShaderNodeVectorMath')
    rad.operation = 'LENGTH'
    links.new(flat.outputs['Vector'], rad.inputs[0])

    # polar angle for radial iris striations
    theta = nodes.new('ShaderNodeMath')
    theta.operation = 'ARCTAN2'
    links.new(sep.outputs['Y'], theta.inputs[0])
    links.new(sep.outputs['X'], theta.inputs[1])
    pol = nodes.new('ShaderNodeCombineXYZ')
    thm = nodes.new('ShaderNodeMath')
    thm.operation = 'MULTIPLY'
    thm.inputs[1].default_value = 3.0
    links.new(theta.outputs['Value'], thm.inputs[0])
    rm = nodes.new('ShaderNodeMath')
    rm.operation = 'MULTIPLY'
    rm.inputs[1].default_value = 9.0
    links.new(rad.outputs['Value'], rm.inputs[0])
    links.new(thm.outputs['Value'], pol.inputs['X'])
    links.new(rm.outputs['Value'], pol.inputs['Y'])
    stria_tex = nodes.new('ShaderNodeTexNoise')
    stria_tex.inputs['Scale'].default_value = 7.0
    stria_tex.inputs['Detail'].default_value = 3.0
    links.new(pol.outputs['Vector'], stria_tex.inputs['Vector'])
    stria = nodes.new('ShaderNodeMath')          # 0.72..1.08 multiplier
    stria.operation = 'MULTIPLY_ADD'
    stria.inputs[1].default_value = 0.55
    stria.inputs[2].default_value = 0.60
    links.new(stria_tex.outputs['Fac'], stria.inputs[0])

    # base radial ramp: pupil -> moon-pale iris -> limbal ring -> sclera
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.name = "EyeRadialRamp"
    cr = ramp.color_ramp
    cr.elements[0].position = 0.17   # pupil edge — animated by animate_v2
    cr.elements[0].color = (0.004, 0.004, 0.006, 1.0)
    cr.elements[1].position = 0.21
    cr.elements[1].color = (0.55, 0.62, 0.66, 1.0)   # inner iris, moon-pale
    e = cr.elements.new(0.80); e.color = (0.28, 0.38, 0.48, 1.0)  # outer iris
    e = cr.elements.new(0.87); e.color = (0.07, 0.09, 0.12, 1.0)  # limbal ring
    e = cr.elements.new(0.91); e.color = (0.83, 0.76, 0.72, 1.0)  # sclera (warm, narrow rim)
    links.new(rad.outputs['Value'], ramp.inputs['Fac'])

    # striations modulate only inside the iris (fade out at limbal ring)
    iris_mask = nodes.new('ShaderNodeValToRGB')
    iris_mask.color_ramp.elements[0].position = 0.83
    iris_mask.color_ramp.elements[0].color = (1, 1, 1, 1)
    iris_mask.color_ramp.elements[1].position = 0.89
    iris_mask.color_ramp.elements[1].color = (0, 0, 0, 1)
    links.new(rad.outputs['Value'], iris_mask.inputs['Fac'])
    stria_fac = nodes.new('ShaderNodeMixRGB')
    stria_fac.blend_type = 'MULTIPLY'
    links.new(iris_mask.outputs['Color'], stria_fac.inputs['Fac'])
    stria_col = nodes.new('ShaderNodeCombineXYZ')
    for ch in ('X', 'Y', 'Z'):
        links.new(stria.outputs['Value'], stria_col.inputs[ch])
    stria_fac.inputs['Color2'].default_value = (1, 1, 1, 1)
    links.new(ramp.outputs['Color'], stria_fac.inputs['Color1'])
    links.new(stria_col.outputs['Vector'], stria_fac.inputs['Color2'])
    base = stria_fac  # already ramp*striation (striation white outside iris)

    # sclera veins: voronoi edge filaments, strongest toward the lids
    vor = nodes.new('ShaderNodeTexVoronoi')
    vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 7.5
    links.new(coord.outputs['Generated'], vor.inputs['Vector'])
    vein_line = nodes.new('ShaderNodeValToRGB')
    vein_line.color_ramp.elements[0].position = 0.0
    vein_line.color_ramp.elements[0].color = (1, 1, 1, 1)
    vein_line.color_ramp.elements[1].position = 0.10
    vein_line.color_ramp.elements[1].color = (0, 0, 0, 1)
    links.new(vor.outputs['Distance'], vein_line.inputs['Fac'])
    vein_mask = nodes.new('ShaderNodeValToRGB')  # only outside the iris
    vein_mask.color_ramp.elements[0].position = 0.80
    vein_mask.color_ramp.elements[0].color = (0, 0, 0, 1)
    vein_mask.color_ramp.elements[1].position = 0.97
    vein_mask.color_ramp.elements[1].color = (0.85, 0.85, 0.85, 1)
    links.new(rad.outputs['Value'], vein_mask.inputs['Fac'])
    vein_fac = nodes.new('ShaderNodeMixRGB')
    vein_fac.blend_type = 'MULTIPLY'
    vein_fac.inputs['Fac'].default_value = 1.0
    links.new(vein_line.outputs['Color'], vein_fac.inputs['Color1'])
    links.new(vein_mask.outputs['Color'], vein_fac.inputs['Color2'])
    veined = nodes.new('ShaderNodeMixRGB')
    veined.blend_type = 'MIX'
    veined.inputs['Color2'].default_value = (0.42, 0.10, 0.08, 1.0)
    links.new(vein_fac.outputs['Color'], veined.inputs['Fac'])
    links.new(base.outputs['Color'], veined.inputs['Color1'])

    # gentle darkening toward the lid line (fake occlusion)
    ao = nodes.new('ShaderNodeValToRGB')
    ao.color_ramp.elements[0].position = 0.62
    ao.color_ramp.elements[0].color = (1, 1, 1, 1)
    ao.color_ramp.elements[1].position = 1.0
    ao.color_ramp.elements[1].color = (0.62, 0.60, 0.62, 1)
    links.new(rad.outputs['Value'], ao.inputs['Fac'])
    shaded = nodes.new('ShaderNodeMixRGB')
    shaded.blend_type = 'MULTIPLY'
    shaded.inputs['Fac'].default_value = 1.0
    links.new(veined.outputs['Color'], shaded.inputs['Color1'])
    links.new(ao.outputs['Color'], shaded.inputs['Color2'])
    links.new(shaded.outputs['Color'], bsdf.inputs['Base Color'])

    # iris-only cold glow (dormant slit gleam; animate_v2 drives strength)
    emask = nodes.new('ShaderNodeValToRGB')
    emask.name = "EyeEmitMask"
    emask.color_ramp.elements[0].position = 0.80
    emask.color_ramp.elements[0].color = (0.75, 0.85, 1.0, 1.0)
    emask.color_ramp.elements[1].position = 0.88
    emask.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(rad.outputs['Value'], emask.inputs['Fac'])
    emix = nodes.new('ShaderNodeMixRGB')
    emix.blend_type = 'MULTIPLY'
    emix.inputs['Fac'].default_value = 1.0
    links.new(shaded.outputs['Color'], emix.inputs['Color1'])
    links.new(emask.outputs['Color'], emix.inputs['Color2'])
    links.new(emix.outputs['Color'], bsdf.inputs['Emission'])
    bsdf.inputs['Emission Strength'].default_value = 0.4
    return mat


def make_cornea_material(name):
    """Wet corneal layer: fresnel-weighted sharp gloss over transparency."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    fres = nodes.new('ShaderNodeFresnel')
    fres.inputs['IOR'].default_value = 1.38
    trans = nodes.new('ShaderNodeBsdfTransparent')
    gloss = nodes.new('ShaderNodeBsdfGlossy')
    gloss.inputs['Roughness'].default_value = 0.03
    mixsh = nodes.new('ShaderNodeMixShader')
    links.new(fres.outputs['Fac'], mixsh.inputs['Fac'])
    links.new(trans.outputs['BSDF'], mixsh.inputs[1])
    links.new(gloss.outputs['BSDF'], mixsh.inputs[2])
    links.new(mixsh.outputs['Shader'], out.inputs['Surface'])
    mat.blend_method = 'BLEND'
    mat.shadow_method = 'NONE'
    mat.show_transparent_back = False
    return mat


def make_skin_material(name):
    """Faceted parchment/bone lid: creased bump, rust staining in folds."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.55
    crease = nodes.new('ShaderNodeTexVoronoi')
    crease.feature = 'DISTANCE_TO_EDGE'
    crease.inputs['Scale'].default_value = 9.0
    cb = nodes.new('ShaderNodeBump')
    cb.inputs['Strength'].default_value = 0.7
    links.new(crease.outputs['Distance'], cb.inputs['Height'])
    links.new(cb.outputs['Normal'], bsdf.inputs['Normal'])
    stain = nodes.new('ShaderNodeTexNoise')
    stain.inputs['Scale'].default_value = 3.5
    st_ramp = nodes.new('ShaderNodeValToRGB')
    st_ramp.color_ramp.elements[0].position = 0.35
    st_ramp.color_ramp.elements[0].color = (0.88, 0.83, 0.78, 1.0)
    st_ramp.color_ramp.elements[1].position = 0.72
    st_ramp.color_ramp.elements[1].color = (0.62, 0.40, 0.30, 1.0)
    links.new(stain.outputs['Fac'], st_ramp.inputs['Fac'])
    links.new(st_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs["Emission"].default_value = (0.10, 0.08, 0.06, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.4
    return mat


def make_copper_material(name):
    """Worked rose-gold: carved lumps (displace modifiers, added per-object),
    engraved circumferential grooves (wave bump), patchy polish (roughness
    variation) and grime darkening in the hollows."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.78, 0.42, 0.28, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0

    # engraving: fine noise + wave grooves running around the band
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 26.0
    noise.inputs['Detail'].default_value = 8.0
    wave = nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'BANDS'
    wave.inputs['Scale'].default_value = 14.0
    wave.inputs['Distortion'].default_value = 6.0
    grooves = nodes.new('ShaderNodeMixRGB')
    grooves.blend_type = 'ADD'
    grooves.inputs['Fac'].default_value = 0.45
    links.new(noise.outputs['Fac'], grooves.inputs['Color1'])
    links.new(wave.outputs['Fac'], grooves.inputs['Color2'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.55
    links.new(grooves.outputs['Color'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    # patchy polish: rough where worked, mirror-bright where worn smooth
    rvar = nodes.new('ShaderNodeTexNoise')
    rvar.inputs['Scale'].default_value = 4.0
    rramp = nodes.new('ShaderNodeValToRGB')
    rramp.color_ramp.elements[0].position = 0.35
    rramp.color_ramp.elements[0].color = (0.14, 0.14, 0.14, 1)
    rramp.color_ramp.elements[1].position = 0.75
    rramp.color_ramp.elements[1].color = (0.55, 0.55, 0.55, 1)
    links.new(rvar.outputs['Fac'], rramp.inputs['Fac'])
    links.new(rramp.outputs['Color'], bsdf.inputs['Roughness'])

    # grime: darken hollows of the same groove field
    grime = nodes.new('ShaderNodeValToRGB')
    grime.color_ramp.elements[0].position = 0.25
    grime.color_ramp.elements[0].color = (0.35, 0.22, 0.16, 1)
    grime.color_ramp.elements[1].position = 0.6
    grime.color_ramp.elements[1].color = (1, 1, 1, 1)
    links.new(grooves.outputs['Color'], grime.inputs['Fac'])
    gmix = nodes.new('ShaderNodeMixRGB')
    gmix.blend_type = 'MULTIPLY'
    gmix.inputs['Fac'].default_value = 1.0
    gmix.inputs['Color1'].default_value = (0.78, 0.42, 0.28, 1.0)
    links.new(grime.outputs['Color'], gmix.inputs['Color2'])
    links.new(gmix.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def make_feather_material(name):
    """Ivory feather: barb striations streaking along the blade (stretched
    noise), root->tip brightness gradient, patchy sheen."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]

    coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (1.5, 30.0, 30.0)
    links.new(coord.outputs['Generated'], mapping.inputs['Vector'])
    streaks = nodes.new('ShaderNodeTexNoise')
    streaks.inputs['Scale'].default_value = 1.0
    streaks.inputs['Detail'].default_value = 3.0
    links.new(mapping.outputs['Vector'], streaks.inputs['Vector'])
    smul = nodes.new('ShaderNodeMath')      # 0.86..1.02 multiplier
    smul.operation = 'MULTIPLY_ADD'
    smul.inputs[1].default_value = 0.16
    smul.inputs[2].default_value = 0.86
    links.new(streaks.outputs['Fac'], smul.inputs[0])

    sep = nodes.new('ShaderNodeSeparateXYZ')
    links.new(coord.outputs['Generated'], sep.inputs['Vector'])
    grad = nodes.new('ShaderNodeValToRGB')  # root rust-stained -> tip pale
    grad.color_ramp.elements[0].position = 0.0
    grad.color_ramp.elements[0].color = (0.58, 0.36, 0.26, 1.0)
    e = grad.color_ramp.elements.new(0.35); e.color = (0.82, 0.72, 0.64, 1.0)
    grad.color_ramp.elements[-1].position = 1.0
    grad.color_ramp.elements[-1].color = (0.96, 0.93, 0.90, 1.0)
    links.new(sep.outputs['X'], grad.inputs['Fac'])
    # rust mottling bleeding along the blade (refs: oxidized streaks)
    rust_n = nodes.new('ShaderNodeTexNoise')
    rust_n.inputs['Scale'].default_value = 2.2
    rust_n.inputs['Detail'].default_value = 4.0
    rust_ramp = nodes.new('ShaderNodeValToRGB')
    rust_ramp.color_ramp.elements[0].position = 0.52
    rust_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    rust_ramp.color_ramp.elements[1].position = 0.78
    rust_ramp.color_ramp.elements[1].color = (0.60, 0.38, 0.28, 1.0)
    links.new(rust_n.outputs['Fac'], rust_ramp.inputs['Fac'])
    rust_mix = nodes.new('ShaderNodeMixRGB')
    rust_mix.blend_type = 'MULTIPLY'
    rust_mix.inputs['Fac'].default_value = 0.65
    links.new(grad.outputs['Color'], rust_mix.inputs['Color1'])
    links.new(rust_ramp.outputs['Color'], rust_mix.inputs['Color2'])

    scol = nodes.new('ShaderNodeCombineXYZ')
    for ch in ('X', 'Y', 'Z'):
        links.new(smul.outputs['Value'], scol.inputs[ch])
    base = nodes.new('ShaderNodeMixRGB')
    base.blend_type = 'MULTIPLY'
    base.inputs['Fac'].default_value = 1.0
    links.new(rust_mix.outputs['Color'], base.inputs['Color1'])
    links.new(scol.outputs['Vector'], base.inputs['Color2'])
    links.new(base.outputs['Color'], bsdf.inputs['Base Color'])

    rr = nodes.new('ShaderNodeValToRGB')
    rr.color_ramp.elements[0].position = 0.3
    rr.color_ramp.elements[0].color = (0.35, 0.35, 0.35, 1)
    rr.color_ramp.elements[1].position = 0.8
    rr.color_ramp.elements[1].color = (0.68, 0.68, 0.68, 1)
    links.new(streaks.outputs['Fac'], rr.inputs['Fac'])
    links.new(rr.outputs['Color'], bsdf.inputs['Roughness'])

    bsdf.inputs["Emission"].default_value = (0.28, 0.24, 0.18, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.10
    return mat


def make_flicker_emissive_material(name, color_low, color_high, strength):
    """4D-noise flame material (v1's halo approach); animate_v2 drives the
    noise 'W' input and the emission Strength."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    noise = nodes.new('ShaderNodeTexNoise')
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


def make_cloud_material(name, density, glow=0.0):
    """Volumetric cloud: 4D noise (W animatable) -> ramp cutting low values
    -> Principled Volume density. Faintly self-luminous (the refs' clouds
    glow from within — pure scattering self-shadows to black at these
    optical depths)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    vol = nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Color'].default_value = (0.92, 0.95, 1.0, 1.0)
    vol.inputs['Anisotropy'].default_value = -0.3
    vol.inputs['Emission Strength'].default_value = glow
    vol.inputs['Emission Color'].default_value = (1.0, 0.88, 0.80, 1.0)
    noise = nodes.new('ShaderNodeTexNoise')
    noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = 0.14
    noise.inputs['Detail'].default_value = 6.0
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.52
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    mul = nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = density
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], mul.inputs[0])
    # vertical fade: density dies toward the domain top so cloud tops are
    # wispy instead of ending at a hard slab boundary
    coord = nodes.new('ShaderNodeTexCoord')
    sep = nodes.new('ShaderNodeSeparateXYZ')
    links.new(coord.outputs['Generated'], sep.inputs['Vector'])
    zfade = nodes.new('ShaderNodeValToRGB')
    zfade.color_ramp.elements[0].position = 0.45
    zfade.color_ramp.elements[0].color = (1, 1, 1, 1)
    zfade.color_ramp.elements[1].position = 0.92
    zfade.color_ramp.elements[1].color = (0, 0, 0, 1)
    links.new(sep.outputs['Z'], zfade.inputs['Fac'])
    mul2 = nodes.new('ShaderNodeMath')
    mul2.operation = 'MULTIPLY'
    links.new(mul.outputs['Value'], mul2.inputs[0])
    links.new(zfade.outputs['Color'], mul2.inputs[1])
    links.new(mul2.outputs['Value'], vol.inputs['Density'])
    links.new(vol.outputs['Volume'], out.inputs['Volume'])
    return mat


# ---------------------------------------------------------------- helpers
def hemisphere_shell(name, radius, keep_top=True):
    """UV-sphere shell with the lower (or upper) half deleted — an eyelid."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=48, ring_count=24)
    obj = bpy.context.object
    obj.name = name
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    sign = -1.0 if keep_top else 1.0
    doomed = [v for v in bm.verts if sign * v.co.z > 1e-3]
    bmesh.ops.delete(bm, geom=doomed, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    return obj


# ================================================================= build
clear_scene()

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_bloom = True
scene.eevee.bloom_intensity = 0.28
scene.eevee.bloom_threshold = 0.95
scene.eevee.bloom_radius = 6.5
scene.eevee.use_gtao = True
scene.eevee.use_ssr = True
scene.eevee.use_volumetric_lights = True
scene.eevee.use_volumetric_shadows = True
scene.eevee.volumetric_start = 0.1
scene.eevee.volumetric_end = 60.0
scene.eevee.volumetric_tile_size = '4'
scene.eevee.volumetric_samples = 128
scene.eevee.shadow_cube_size = '1024'
scene.eevee.shadow_cascade_size = '2048'
scene.eevee.use_soft_shadows = True
scene.view_settings.exposure = -0.25
# this apt Blender build lacks OCIO/Filmic data — do tonal contrast in the
# compositor instead (S-curve-ish via Bright/Contrast)
scene.use_nodes = True
_ct = scene.node_tree
_ct.nodes.clear()
_rl = _ct.nodes.new('CompositorNodeRLayers')
_bc = _ct.nodes.new('CompositorNodeBrightContrast')
_bc.inputs['Contrast'].default_value = 12.0
_hs = _ct.nodes.new('CompositorNodeHueSat')
_hs.inputs['Saturation'].default_value = 1.06
_out = _ct.nodes.new('CompositorNodeComposite')
_ct.links.new(_rl.outputs['Image'], _bc.inputs['Image'])
_ct.links.new(_bc.outputs['Image'], _hs.inputs['Image'])
_ct.links.new(_hs.outputs['Image'], _out.inputs['Image'])
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.film_transparent = False

world = bpy.data.worlds.new("HeavenWorld")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.38, 0.35, 0.34, 1.0)
bg.inputs[1].default_value = 0.85

eyeball_mat = make_eyeball_material()
lid_mat = make_skin_material("LidIvory")
copper_mat = make_copper_material("RingCopper")
feather_mat = make_feather_material("FeatherIvory")

# ---- THE GREAT EYE ----
gaze_dir = (CAM_LOC - EYE_CENTER).normalized()
gaze_quat = gaze_dir.to_track_quat('Z', 'Y')

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=EYE_CENTER,
                                     segments=64, ring_count=32)
eye = bpy.context.object
eye.name = "GreatEye"
eye.rotation_euler = gaze_quat.to_euler()
eye.data.materials.append(eyeball_mat)
bpy.ops.object.shade_smooth()

cornea_mat = make_cornea_material("CorneaMat")
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.015, location=EYE_CENTER,
                                     segments=64, ring_count=32)
cornea = bpy.context.object
cornea.name = "Cornea"
cornea.rotation_euler = gaze_quat.to_euler()
cornea.data.materials.append(cornea_mat)
bpy.ops.object.shade_smooth()

# Lids: dome shells concentric with the eye. Rest = dome axis up/down (open);
# rotating about the eye-local X swings the dome over the front (+Z, camera).
# open=1 -> retracted; open=0 -> nearly meeting at the front. Radii differ
# slightly so the closed rims don't z-fight.
LID_OPEN_STILL = 0.85


def lid_angles(open_amt):
    # A hemisphere dome covers everything within 90 deg of its axis, so the
    # front only becomes visible once the dome swings PAST 90 deg. Visible
    # lens half-angle ~= (|theta|-90); open=0 -> rims meet at the front.
    a_top = -math.radians(90.0 + open_amt * 38.0)
    a_bot = math.radians(90.0 + open_amt * 28.0)
    return a_top, a_bot


lid_crumple = bpy.data.textures.new("LidCrumple", type='CLOUDS')
lid_crumple.noise_scale = 0.22
for name, radius, keep_top in (("LidTop", 1.04, True), ("LidBottom", 1.03, True)):
    lid = hemisphere_shell(name, radius)
    lid.location = EYE_CENTER
    lid.data.materials.append(lid_mat)
    bpy.ops.object.shade_smooth()
    lmod = lid.modifiers.new("Crumple", 'DISPLACE')
    lmod.texture = lid_crumple
    lmod.strength = 0.07

a_top, a_bot = lid_angles(LID_OPEN_STILL)
gm = gaze_quat.to_matrix().to_4x4()
bpy.data.objects["LidTop"].rotation_euler = (gm @ Matrix.Rotation(a_top, 4, 'X')).to_euler()
bpy.data.objects["LidBottom"].rotation_euler = (gm @ Matrix.Rotation(a_bot, 4, 'X')).to_euler()

# ---- THE RINGS: fat, carved, copper, studded with eyes ----
carve_tex = bpy.data.textures.new("RingCarve", type='CLOUDS')
carve_tex.noise_scale = 0.35
engrave_tex = bpy.data.textures.new("RingEngrave", type='CLOUDS')
engrave_tex.noise_scale = 0.07
engrave_tex.noise_depth = 3

for r, spec in enumerate(RING_SPECS):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=spec["major"], minor_radius=spec["tube"],
        major_segments=256, minor_segments=48, location=EYE_CENTER)
    ring = bpy.context.object
    ring.name = f"Ring_{r}"
    ring.rotation_euler = spec["tilt"]
    ring.data.materials.append(copper_mat)
    bpy.ops.object.shade_smooth()
    mod = ring.modifiers.new("Carve", 'DISPLACE')
    mod.texture = carve_tex
    mod.strength = 0.06
    mod2 = ring.modifiers.new("Engrave", 'DISPLACE')
    mod2.texture = engrave_tex
    mod2.strength = 0.022

    # eyes stud the band's front face (ring-local +Z side), parented so the
    # spin carries them (v1's parent-inverse pattern)
    tilt_mat = mathutils.Euler(spec["tilt"], 'XYZ').to_matrix().to_4x4()
    parent_inv = tilt_mat.inverted()
    for j in range(spec["n_eyes"]):
        ang = (j / spec["n_eyes"]) * 2 * math.pi
        local = Vector((math.cos(ang) * spec["major"],
                        math.sin(ang) * spec["major"],
                        spec["tube"] * 0.45))
        world_pos = EYE_CENTER + tilt_mat.to_3x3() @ local
        bpy.ops.mesh.primitive_uv_sphere_add(radius=spec["eye_r"],
                                             location=world_pos,
                                             segments=24, ring_count=12)
        reye = bpy.context.object
        reye.name = f"RingEye_{r}_{j}"
        # orientation: ring-normal blended 55% toward the camera, so irises
        # read from the viewer across the whole visible arc
        ring_quat = mathutils.Euler(spec["tilt"], 'XYZ').to_quaternion()
        cam_quat = (CAM_LOC - world_pos).normalized().to_track_quat('Z', 'Y')
        reye.rotation_euler = ring_quat.slerp(cam_quat, 0.55).to_euler()
        reye.data.materials.append(eyeball_mat)
        bpy.ops.object.shade_smooth()
        reye.parent = ring
        reye.matrix_parent_inverse = parent_inv

        # socket bezel: embeds the eye into the worked metal band
        bpy.ops.mesh.primitive_torus_add(
            major_radius=spec["eye_r"] * 1.02, minor_radius=spec["eye_r"] * 0.34,
            major_segments=32, minor_segments=12, location=world_pos)
        bezel = bpy.context.object
        bezel.name = f"Bezel_{r}_{j}"
        bezel.rotation_euler = spec["tilt"]
        bezel.data.materials.append(copper_mat)
        bpy.ops.object.shade_smooth()
        bezel.parent = ring
        bezel.matrix_parent_inverse = parent_inv

# ---- THE WINGS: two great feather fans cradling the ring ----
import random
_rng = random.Random(7)
FEATHER_JITTER = [[_rng.uniform(-0.08, 0.08) for _ in range(N_FEATHERS)] for _ in range(3)]

# Extrude widens curves along their LOCAL Z (verified by isolated debug
# render). A feather with length +X and width Z faces the -Y camera as a
# broad blade with NO rotation at all; the fan must therefore rotate about
# Y (the view axis' picture plane), and no Rx flip may ever be applied.
for side, sx in (("L", -1.0), ("R", 1.0)):
    bpy.ops.object.empty_add(type='PLAIN_AXES',
                             location=(sx * 1.55, 0.95, -0.1))
    root = bpy.context.object
    root.name = f"WingRoot_{side}"
    root.rotation_euler = (0.0, 0.0, math.pi if sx < 0 else 0.0)

    for row in range(3):
        L = ROW_LEN[row]
        W = ROW_WID[row]
        for k in range(N_FEATHERS):
            Lk = L * (1.0 + FEATHER_JITTER[row][k])
            curve = bpy.data.curves.new(f"FeatherCurve_{side}_{row}_{k}", type='CURVE')
            curve.dimensions = '3D'
            curve.twist_mode = 'Z_UP'
            curve.extrude = W * 0.5
            curve.bevel_depth = 0.006
            curve.bevel_resolution = 1
            curve.fill_mode = 'FULL'
            curve.use_fill_caps = True
            spline = curve.splines.new('BEZIER')
            spline.bezier_points.add(2)
            pts = [
                (0.08, 0.0, 0.0, 0.5),
                (0.52 * Lk, 0.0, 0.07 * Lk, 1.0),
                (Lk, 0.0, 0.02 * Lk, 0.12),
            ]
            for n, (x, y, z, radv) in enumerate(pts):
                bp = spline.bezier_points[n]
                bp.co = (x, y, z)
                bp.radius = radv
                bp.handle_left_type = 'AUTO'
                bp.handle_right_type = 'AUTO'
            fo = bpy.data.objects.new(f"Feather_{side}_{row}_{k}", curve)
            bpy.context.collection.objects.link(fo)
            fo.parent = root
            tk = k / (N_FEATHERS - 1)
            # fan cradles the ring: from above-horizontal wrapping down
            # around its outer-lower quadrant (ref 3's wrap)
            fan = 0.35 - tk * 1.9
            # roots sit on a curved "shoulder" arc so the blades radiate
            # like a real wing instead of stair-stepping past each other
            f2 = fan * 0.55
            r_arm = 0.45 + 0.75 * tk - 0.14 * row
            fo.location = (r_arm * math.cos(f2),
                           -0.06 * row,
                           r_arm * math.sin(f2) + 0.05 * row)
            # fan about Y keeps every blade broad-on to the camera; a tiny
            # seeded roll lets each blade catch light on its own
            roll = FEATHER_JITTER[row][k] * 0.9
            fo.rotation_euler = (roll, -(fan + row * 0.04), 0.0)
            fo.data.materials.append(feather_mat)

# ---- SOCKET PLUMAGE: feathers hugging the great eye (ref 3) ----
_prng = random.Random(23)
N_SOCKET = 22
for ring_i, (rad0, ln0, y_off) in enumerate([(0.62, 0.55, 0.55), (0.78, 0.85, 0.75)]):
    for i in range(N_SOCKET):
        ang = (i / N_SOCKET) * 2 * math.pi + ring_i * 0.12
        jit = 1.0 + _prng.uniform(-0.22, 0.22)
        # under-feathers hang long below (refs); upper corona stays short
        droop = max(0.0, -math.sin(ang))
        rise = max(0.0, math.sin(ang))
        ln = ln0 * jit * (1.0 + 2.2 * droop) * (1.0 - 0.45 * rise)
        wd = 0.18 + 0.08 * ring_i + 0.14 * droop
        curve = bpy.data.curves.new(f"SocketFCurve_{ring_i}_{i}", type='CURVE')
        curve.dimensions = '3D'
        curve.twist_mode = 'Z_UP'
        curve.extrude = wd * 0.5
        curve.bevel_depth = 0.005
        curve.bevel_resolution = 1
        curve.fill_mode = 'FULL'
        curve.use_fill_caps = True
        spline = curve.splines.new('BEZIER')
        spline.bezier_points.add(2)
        pts = [(0.05, 0.0, 0.0, 0.55), (0.5 * ln, 0.0, 0.05 * ln, 1.0), (ln, 0.0, -0.06 * ln * droop, 0.14)]
        for n, (x, y, z, radv) in enumerate(pts):
            bp = spline.bezier_points[n]
            bp.co = (x, y, z)
            bp.radius = radv
            bp.handle_left_type = 'AUTO'
            bp.handle_right_type = 'AUTO'
        fo = bpy.data.objects.new(f"SocketFeather_{ring_i}_{i}", curve)
        bpy.context.collection.objects.link(fo)
        rj = rad0 * (1.0 + _prng.uniform(-0.12, 0.12))
        fo.location = (EYE_CENTER.x + math.cos(ang) * rj,
                       EYE_CENTER.y + y_off + _prng.uniform(-0.08, 0.08),
                       EYE_CENTER.z + math.sin(ang) * rj)
        # tangential swirl: plumage sweeps around the eye instead of
        # radiating like a starburst; under-feathers swirl less (they hang)
        swirl = 0.65 * (1.0 - droop) + _prng.uniform(-0.12, 0.12)
        fo.rotation_euler = (_prng.uniform(-0.06, 0.06), -(ang + swirl), 0.0)
        fo.data.materials.append(feather_mat)

# ---- HALO + HEAVEN LIGHT (behind the being, facing the camera) ----
halo_mat = make_flicker_emissive_material("HaloFire", (0.55, 0.10, 0.03), (1.0, 0.75, 0.35), 1.4)
bpy.ops.mesh.primitive_torus_add(major_radius=3.1, minor_radius=0.14,
                                 major_segments=96, minor_segments=20,
                                 location=(0.0, 2.5, 0.6))
halo = bpy.context.object
halo.name = "Halo"
halo.rotation_euler = (math.pi / 2, 0.0, 0.0)
halo.data.materials.append(halo_mat)

def make_glow_disc_material(name, color, strength):
    """Emissive disc with soft radial falloff (no hard edge)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    emit = nodes.new('ShaderNodeEmission')
    coord = nodes.new('ShaderNodeTexCoord')
    remap = nodes.new('ShaderNodeVectorMath')
    remap.operation = 'MULTIPLY_ADD'
    remap.inputs[1].default_value = (2.0, 2.0, 2.0)
    remap.inputs[2].default_value = (-1.0, -1.0, -1.0)
    links.new(coord.outputs['Generated'], remap.inputs[0])
    rad = nodes.new('ShaderNodeVectorMath')
    rad.operation = 'LENGTH'
    links.new(remap.outputs['Vector'], rad.inputs[0])
    fade = nodes.new('ShaderNodeValToRGB')
    fade.color_ramp.elements[0].position = 0.15
    fade.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
    fade.color_ramp.elements[1].position = 0.92
    fade.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
    links.new(rad.outputs['Value'], fade.inputs['Fac'])
    emit.inputs['Color'].default_value = (*color, 1.0)
    emit.inputs['Strength'].default_value = strength
    trans = nodes.new('ShaderNodeBsdfTransparent')
    mixsh = nodes.new('ShaderNodeMixShader')
    links.new(fade.outputs['Color'], mixsh.inputs['Fac'])
    links.new(trans.outputs['BSDF'], mixsh.inputs[1])
    links.new(emit.outputs['Emission'], mixsh.inputs[2])
    links.new(mixsh.outputs['Shader'], out.inputs['Surface'])
    mat.blend_method = 'BLEND'
    mat.shadow_method = 'NONE'
    return mat


disc_mat = make_glow_disc_material("HeavenGlow", (1.0, 0.90, 0.74), 3.4)
bpy.ops.mesh.primitive_circle_add(radius=4.0, fill_type='NGON',
                                  location=(0.0, 8.0, 0.8))
disc = bpy.context.object
disc.name = "HeavenDisc"
disc.rotation_euler = (math.pi / 2, 0.0, 0.0)
disc.data.materials.append(disc_mat)

# ---- CLOUDS: volumetric deck below, haze behind for god-rays ----
deck_mat = make_cloud_material("CloudMat", density=1.0, glow=0.02)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 6.0, -5.0))
deck = bpy.context.object
deck.name = "CloudDeck"
deck.scale = (34.0, 26.0, 3.0)
deck.data.materials.append(deck_mat)

haze_mat = make_cloud_material("HazeMat", density=0.012)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 4.0, 1.0))
haze = bpy.context.object
haze.name = "CloudHaze"
haze.scale = (25.0, 13.0, 8.0)   # fills the camera->being corridor: god rays
haze.data.materials.append(haze_mat)

# foreground wisps drifting IN FRONT of the being's lower body — the
# occlusion is what sells the scale (refs: fog swallows the lower forms)
wisp_mat = make_cloud_material("WispMat", density=0.9, glow=0.008)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, -3.0, -1.9))
wisp = bpy.context.object
wisp.name = "CloudWisp"
wisp.scale = (8.0, 1.6, 1.1)
wisp.data.materials.append(wisp_mat)

# cloud bank behind the being (backlit by the heaven disc): the being
# emerges FROM cloud mass instead of floating before a flat backdrop
bank_mat = make_cloud_material("BankMat", density=0.8, glow=0.035)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0.0, 11.0, 2.0))
bank = bpy.context.object
bank.name = "CloudBank"
bank.scale = (16.0, 3.5, 7.0)
bank.data.materials.append(bank_mat)

# side towers framing the composition
tower_mat = make_cloud_material("TowerMat", density=0.7, glow=0.03)
for sx in (-1.0, 1.0):
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(sx * 9.0, 7.0, 1.5))
    tw = bpy.context.object
    tw.name = f"CloudTower_{'L' if sx < 0 else 'R'}"
    tw.scale = (3.5, 3.0, 6.5)
    tw.data.materials.append(tower_mat)

# low warm-pink light washing the cloud fronts facing the camera
bpy.ops.object.light_add(type='AREA', location=(0.0, -7.5, -2.2))
fog_l = bpy.context.object
fog_l.name = "FogLight"
fog_l.data.energy = 260.0
fog_l.data.size = 18.0
fog_l.data.color = (1.0, 0.82, 0.74)
fog_l.rotation_euler = Vector((0.0, 10.0, -3.0)).to_track_quat('-Z', 'Y').to_euler()

# ---- LIGHTS ----
bpy.ops.object.light_add(type='SUN', location=(0.0, 8.0, 6.0))
sun = bpy.context.object
sun.name = "Sun"
sun.data.energy = 2.2
sun.data.color = (1.0, 0.82, 0.62)
sun.data.angle = 0.05
sun.rotation_euler = Vector((0.0, -8.0, -6.0)).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.light_add(type='AREA', location=(0.0, -9.0, 4.0))
cloudlight = bpy.context.object
cloudlight.name = "CloudLight"
cloudlight.data.energy = 500.0
cloudlight.data.size = 24.0
cloudlight.data.color = (1.0, 0.88, 0.82)
cloudlight.rotation_euler = Vector((0.0, 9.0, -6.0)).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.light_add(type='AREA', location=(-3.0, -4.0, 2.0))
key = bpy.context.object
key.data.energy = 110.0
key.data.size = 2.2
key.data.color = (1.0, 0.86, 0.84)
key.rotation_euler = Vector((3.0, 4.0, -1.85)).to_track_quat('-Z', 'Y').to_euler()

# warm bounce behind the wings: fakes the halo firelight the emission
# surfaces can't cast in Eevee — fire-lit feather rims like ref 3
for sx in (-1.0, 1.0):
    bpy.ops.object.light_add(type='AREA', location=(sx * 3.4, 2.2, 0.4))
    wl = bpy.context.object
    wl.name = f"WingGlow_{'L' if sx < 0 else 'R'}"
    wl.data.energy = 90.0
    wl.data.size = 3.5
    wl.data.color = (1.0, 0.66, 0.36)
    wl.rotation_euler = Vector((-sx * 1.5, -3.0, -0.8)).to_track_quat('-Z', 'Y').to_euler()

# ---- SCALE FIGURE: a tiny human silhouette on a rock spur (all three
# refs use this) — the one cue that makes the being read as colossal ----
rock_mat = bpy.data.materials.new("RockDark")
rock_mat.use_nodes = True
_rb = rock_mat.node_tree.nodes["Principled BSDF"]
_rb.inputs["Base Color"].default_value = (0.05, 0.045, 0.05, 1.0)
_rb.inputs["Roughness"].default_value = 0.95

bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=0.30, radius2=0.05,
                                depth=1.1, location=(-0.85, -4.6, -1.0))
rock = bpy.context.object
rock.name = "ScaleRock"
rock.rotation_euler = (0.06, 0.1, 0.5)
rock.data.materials.append(rock_mat)
rock_top = -0.46

fig_mat = bpy.data.materials.new("FigureDark")
fig_mat.use_nodes = True
_fb = fig_mat.node_tree.nodes["Principled BSDF"]
_fb.inputs["Base Color"].default_value = (0.02, 0.018, 0.02, 1.0)
_fb.inputs["Roughness"].default_value = 0.9

# body: ~0.05 units tall at 2.7 from camera (~2.5% of frame height)
bpy.ops.mesh.primitive_cylinder_add(radius=0.0065, depth=0.034,
                                    location=(-0.78, -4.6, rock_top + 0.017))
body = bpy.context.object
body.name = "FigureBody"
body.data.materials.append(fig_mat)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006, segments=12, ring_count=6,
                                     location=(-0.78, -4.6, rock_top + 0.040))
head = bpy.context.object
head.name = "FigureHead"
head.data.materials.append(fig_mat)

# ---- CAMERA: low, monumental, looking slightly up at the being ----
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.15))
target = bpy.context.object
target.name = "CameraTarget"

bpy.ops.object.camera_add(location=CAM_LOC)
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
