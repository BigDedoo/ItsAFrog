"""Stylized grass and dirt ground materials, shared by build_frog_demo.py and build_asset_library.py.

Imports Tools/FrogDemo/textures/<ground>_{color,normal,rough}.png to /Game/Stylized/Ground
(set FROG_DEMO_REIMPORT=1 to import again) and builds M_StylizedGrass / M_StylizedDirt.
The materials map the textures in world space (absolute world XY), so any mesh at any
scale gets the same texel density, and blend in a second, larger sample through a
world-space noise mask so the repeat doesn't show. The graph is rebuilt on every run,
so edit TILE_CM / the graph here and rerun a builder.

The painted textures are bright, so the levels use tinted_material(name, tint, tag), an
instance with the colour darkened to suit their lighting (night in the demo, sun in the
asset library); material(name) is the untinted parent.
"""
import os

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
TEX_DIR = os.path.join(HERE, "textures")
ROOT = "/Game/Stylized/Ground"
REIMPORT = os.environ.get("FROG_DEMO_REIMPORT") == "1"
TILE_CM = {"grass": 400.0, "dirt": 300.0}  # world size of one texture repeat
MACRO = 2.7  # the blended second sample repeats this many times larger
NOISE_SCALE = 0.004  # world-space noise for the blend mask (features of a few metres)

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary

# map kind -> (compression, sRGB, sampler type)
KINDS = {
    "color": (unreal.TextureCompressionSettings.TC_DEFAULT, True, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR),
    "normal": (unreal.TextureCompressionSettings.TC_NORMALMAP, False, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL),
    "rough": (unreal.TextureCompressionSettings.TC_MASKS, False, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS),
}


def log(msg):
    unreal.log(f"[Ground] {msg}")


def texture(ground, kind):
    name = f"T_{ground.capitalize()}_{kind.capitalize()}"
    path = f"{ROOT}/{name}"
    if REIMPORT or not assets.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", os.path.join(TEX_DIR, f"{ground}_{kind}.png"))
        task.set_editor_property("destination_path", ROOT)
        task.set_editor_property("destination_name", name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", False)
        tools.import_asset_tasks([task])
        tex = assets.load_asset(path)
        compression, srgb, _ = KINDS[kind]
        tex.set_editor_property("compression_settings", compression)
        tex.set_editor_property("srgb", srgb)
        assets.save_asset(path)
        log(f"imported {name}")
    return assets.load_asset(path)


def expr(mat, cls, x, y, **props):
    e = mel.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def link(src, dst, dst_input, src_output=""):
    if not mel.connect_material_expressions(src, src_output, dst, dst_input):
        unreal.log_warning(f"[Ground] could not connect {src.get_name()} -> {dst.get_name()}.{dst_input}")


def material(ground):
    """Create or rebuild M_Stylized<Ground>; returns the material."""
    name = f"M_Stylized{ground.capitalize()}"
    path = f"{ROOT}/{name}"
    if assets.does_asset_exist(path):
        mat = assets.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    textures = {k: texture(ground, k) for k in KINDS}
    tile = TILE_CM[ground]

    # World XY -> two UV sets: the base repeat and a larger one for the blend. U = -X, V = -Y,
    # so the image's "down" (where the painted pebbles cast their shadows) faces the diorama
    # camera (yaw 45) and the bumps read as raised rather than as pits.
    world = expr(mat, unreal.MaterialExpressionWorldPosition, -1400, 0)
    xy = expr(mat, unreal.MaterialExpressionComponentMask, -1200, 0, r=True, g=True, b=False, a=False)
    link(world, xy, "")
    uv_near = expr(mat, unreal.MaterialExpressionMultiply, -1000, -100, const_b=-1.0 / tile)
    uv_far = expr(mat, unreal.MaterialExpressionMultiply, -1000, 100, const_b=-1.0 / (tile * MACRO))
    link(xy, uv_near, "A")
    link(xy, uv_far, "A")

    noise = expr(mat, unreal.MaterialExpressionNoise, -700, 600, scale=NOISE_SCALE,
                 output_min=0.0, output_max=1.0, levels=3)

    tint = expr(mat, unreal.MaterialExpressionVectorParameter, -300, -400,
                parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    outputs = {"color": unreal.MaterialProperty.MP_BASE_COLOR,
               "normal": unreal.MaterialProperty.MP_NORMAL,
               "rough": unreal.MaterialProperty.MP_ROUGHNESS}
    for row, (kind, prop) in enumerate(outputs.items()):
        y = row * 300 - 300
        near = expr(mat, unreal.MaterialExpressionTextureSample, -700, y, texture=textures[kind], sampler_type=KINDS[kind][2])
        far = expr(mat, unreal.MaterialExpressionTextureSample, -500, y + 120, texture=textures[kind], sampler_type=KINDS[kind][2])
        link(uv_near, near, "UVs")
        link(uv_far, far, "UVs")
        blend = expr(mat, unreal.MaterialExpressionLinearInterpolate, -250, y)
        link(near, blend, "A", "R" if kind == "rough" else "RGB")
        link(far, blend, "B", "R" if kind == "rough" else "RGB")
        link(noise, blend, "Alpha")
        if kind == "color":
            tinted = expr(mat, unreal.MaterialExpressionMultiply, -100, y)
            link(blend, tinted, "A")
            link(tint, tinted, "B")
            blend = tinted
        elif kind == "normal":
            # +U/+V run along -X/-Y, so the DirectX normal's red/green flip to give a world normal.
            flip = expr(mat, unreal.MaterialExpressionConstant3Vector, -250, y + 150,
                        constant=unreal.LinearColor(-1.0, -1.0, 1.0, 1.0))
            world_normal = expr(mat, unreal.MaterialExpressionMultiply, -100, y)
            link(blend, world_normal, "A")
            link(flip, world_normal, "B")
            blend = world_normal
        mel.connect_material_property(blend, "", prop)

    # The normal is built in world space above; tangent space would follow the mesh's own UVs.
    mat.set_editor_property("tangent_space_normal", False)
    mel.layout_material_expressions(mat)
    mel.recompile_material(mat)
    assets.save_asset(path)
    log(f"built {name} ({tile / 100:.0f} m per repeat)")
    return mat


def tinted_material(ground, tint, tag):
    """MI_Stylized<Ground>_<tag>: an instance of M_Stylized<Ground> with its colour multiplied by tint."""
    parent = material(ground)
    name = f"MI_Stylized{ground.capitalize()}_{tag}"
    path = f"{ROOT}/{name}"
    if assets.does_asset_exist(path):
        mi = assets.load_asset(path)
    else:
        mi = tools.create_asset(name, ROOT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(*tint, 1.0))
    mel.update_material_instance(mi)
    assets.save_asset(path)
    return mi
