"""Import the basic asset library and lay it out in a gallery level.

Run from the editor (Tools > Execute Python Script...) after
`python Tools/FrogDemo/fetch_assets.py`, which downloads the library GLBs to
<Project>/ExternalAssets/stylized-assets/library (or set FROG_ASSET_DIR to the
stylized-assets folder). Run build_frog_demo.py first if you want to walk the
gallery as the frog: the level reuses BP_FrogDemoGameMode when it exists.

What it does:
  1. Imports every GLB in library_layout.json to /Game/Stylized/Library/<name>.
     Already-imported assets are reused; set FROG_DEMO_REIMPORT=1 to import again (or a comma-separated list of asset names, e.g. bush,fern).
  2. Builds /Game/Stylized/Library/Lvl_AssetLibrary: each prop at its real-world
     size (frog = 1 m) on a grid with a name label, under plain daylight so the
     colours read true.
"""
import json
import math
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ground_materials  # noqa: E402
PROJECT_DIR = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
ASSET_DIR = os.environ.get("FROG_ASSET_DIR", os.path.join(PROJECT_DIR, "ExternalAssets", "stylized-assets"))
# "1" reimports everything; a comma-separated list of asset names reimports just those.
REIMPORT = os.environ.get("FROG_DEMO_REIMPORT", "")
LAYOUT = json.load(open(os.path.join(HERE, "library_layout.json")))

ROOT = "/Game/Stylized/Library"
LEVEL = ROOT + "/Lvl_AssetLibrary"
GAME_MODE = "/Game/Stylized/Demo/BP_FrogDemoGameMode"
M = 100.0  # layout metres -> Unreal centimetres

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(msg):
    unreal.log(f"[AssetLibrary] {msg}")


def setp(obj, key, value):
    try:
        obj.set_editor_property(key, value)
    except Exception as e:
        unreal.log_warning(f"[AssetLibrary] {type(obj).__name__}.{key}: {e}")


def import_mesh(name):
    src = os.path.join(ASSET_DIR, "library", f"{name}.glb")
    dest = f"{ROOT}/{name}"
    if not (assets.does_directory_exist(dest) and assets.list_assets(dest)) or REIMPORT == "1" or name in REIMPORT.split(","):
        if not os.path.exists(src):
            unreal.log_warning(f"[AssetLibrary] missing {src}")
            return None
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", src)
        task.set_editor_property("destination_path", dest)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", True)
        tools.import_asset_tasks([task])
        log(f"imported {name}")
    objs = [assets.load_asset(p) for p in assets.list_assets(dest, recursive=True)]
    return next((o for o in objs if isinstance(o, unreal.StaticMesh)), None)


def complex_collision(mesh):
    try:
        mesh.get_editor_property("body_setup").set_editor_property(
            "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        assets.save_loaded_asset(mesh)
    except Exception as e:
        unreal.log_warning(f"[AssetLibrary] collision on {mesh.get_name()}: {e}")


def spawn(cls, loc, rot=unreal.Rotator(0, 0, 0), label=None):
    a = actors.spawn_actor_from_class(cls, loc, rot)
    if label:
        a.set_actor_label(label)
    return a


def place(e, mesh, x, y):
    box = mesh.get_bounding_box()
    lo, hi = box.min, box.max
    if "width" in e:
        k = e["width"] * M / max(hi.x - lo.x, hi.y - lo.y, 1e-3)
    else:
        k = e["height"] * M / max(hi.z - lo.z, 1e-3)
    yaw = float(e.get("yaw", 0))
    # Put the scaled, rotated bounds centre on (x, y) and the bottom on z.
    cx, cy = (lo.x + hi.x) / 2 * k, (lo.y + hi.y) / 2 * k
    r = math.radians(yaw)
    ox, oy = cx * math.cos(r) - cy * math.sin(r), cx * math.sin(r) + cy * math.cos(r)
    loc = unreal.Vector(x - ox, y - oy, e.get("z", 0.0) * M - lo.z * k)
    a = actors.spawn_actor_from_object(mesh, loc, unreal.Rotator(0, 0, yaw))
    a.set_actor_label(e["asset"])
    a.set_actor_scale3d(unreal.Vector(k, k, k))
    comp = a.get_editor_property("static_mesh_component")
    if e.get("collision", True):
        complex_collision(mesh)
    else:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    tags = [t for t, on in (("Collectible", e.get("collectible")), ("Hazard", e.get("hazard"))) if on]
    if tags:
        a.set_editor_property("tags", [unreal.Name(t) for t in tags])
    if "light" in e:
        lamp = spawn(unreal.PointLight, unreal.Vector(x, y, (hi.z - lo.z) * k * e["light"] + 20), label=f"light_{e['asset']}")
        c = lamp.get_component_by_class(unreal.PointLightComponent)
        setp(c, "intensity_units", unreal.LightUnits.LUMENS)
        setp(c, "intensity", 800)
        c.set_light_color(unreal.LinearColor(1.0, 0.55, 0.22, 1))
        setp(c, "attenuation_radius", 900)
    return (hi.y - lo.y) * k


def label(text, x, y):
    # Upright on the ground, reading towards -X where the PlayerStart is.
    a = spawn(unreal.TextRenderActor, unreal.Vector(x, y, 2), unreal.Rotator(0, 0, 180), f"label_{text}")
    c = a.get_editor_property("text_render")
    c.set_text(text.replace("_", " "))
    setp(c, "world_size", 45.0)
    setp(c, "horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    setp(c, "vertical_alignment", unreal.VerticalTextAligment.EVRTA_TEXT_BOTTOM)
    c.set_text_render_color(unreal.Color(70, 45, 25, 255))  # dark brown reads on the sunlit grass


def daylight():
    sun = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -50, -40), "Sun")
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    setp(c, "intensity", 6.0)
    setp(c, "atmosphere_sun_light", True)
    spawn(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), label="SkyAtmosphere")
    sky = spawn(unreal.SkyLight, unreal.Vector(0, 0, 500), label="SkyLight")
    setp(sky.get_component_by_class(unreal.SkyLightComponent), "real_time_capture", True)
    spawn(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), label="Fog")
    # Auto exposure would otherwise brighten the tinted grass back to a washed-out pastel.
    ppv = spawn(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), label="DaylightPostProcess")
    ppv.set_editor_property("unbound", True)
    s = ppv.get_editor_property("settings")
    setp(s, "override_auto_exposure_bias", True)
    setp(s, "auto_exposure_bias", -0.7)
    ppv.set_editor_property("settings", s)


def main():
    props = LAYOUT["props"]
    cols, step = LAYOUT["columns"], LAYOUT["spacing"] * M
    rows = math.ceil(len(props) / cols)
    meshes = {e["asset"]: import_mesh(e["asset"]) for e in props}

    if assets.does_asset_exist(LEVEL):
        levels.load_level(LEVEL)
        actors.destroy_actors(actors.get_all_level_actors())
    else:
        levels.new_level(LEVEL)

    # Ground: one flat engine cylinder under the whole grid, top at z = 0.
    floor = actors.spawn_actor_from_object(assets.load_asset("/Engine/BasicShapes/Cylinder.Cylinder"),
                                           unreal.Vector(0, 0, -10))
    floor.set_actor_label("Ground")
    floor.set_actor_scale3d(unreal.Vector(step * (cols + 1) / 100, step * (rows + 1) / 100, 0.2))
    grass = ground_materials.tinted_material("grass", LAYOUT["ground_tint"], "Day")  # full-bright paint washes out in sun
    floor.get_editor_property("static_mesh_component").set_material(0, grass)

    for i, e in enumerate(props):
        # Rows run along X (away from the start), columns along Y, centred on the origin.
        x = (i // cols - (rows - 1) / 2) * step
        y = (i % cols - (cols - 1) / 2) * step
        mesh = meshes[e["asset"]]
        if not mesh:
            unreal.log_warning(f"[AssetLibrary] no static mesh for {e['asset']}")
            continue
        place(e, mesh, x, y)
        label(e["asset"], x - step * 0.35, y)

    spawn(unreal.PlayerStart, unreal.Vector(-(rows / 2 + 0.3) * step, 0, 100), label="PlayerStart")
    daylight()
    gm = unreal.EditorAssetLibrary.load_blueprint_class(GAME_MODE) if assets.does_asset_exist(GAME_MODE) else None
    if gm:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        world.get_world_settings().set_editor_property("default_game_mode", gm)
    levels.save_current_level()
    log(f"built {LEVEL} with {sum(1 for m in meshes.values() if m)} of {len(props)} props")


main()
