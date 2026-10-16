"""Build the stylized frog demo level inside the Unreal Editor.

Run from the editor (Tools > Execute Python Script...) after copying the
stylized asset folder (GLBs from the project's Meshy pipeline) to
<Project>/ExternalAssets/stylized-assets, or set FROG_ASSET_DIR to it.

What it does:
  1. Imports every prop GLB in frog_demo_layout.json to /Game/Stylized/Props/<name>
     and the packaged frog (demo/SK_Frog.glb: Idle, Walk, Run, TongueSocket bone)
     to /Game/Stylized/Frog. Already-imported assets are reused; set
     FROG_DEMO_REIMPORT=1 to import again.
  2. Creates BP_DemoFrog (AFrogCharacter with the stylized mesh, clips and the
     diorama camera) and BP_FrogDemoGameMode (the third-person game mode
     spawning BP_DemoFrog).
  3. Builds /Game/Stylized/Demo/Lvl_FrogDemo from the layout: grass island,
     pond, paths, props, warm point lights, moonlight, sky, fog and a night
     post-process, plus a PlayerStart.

Rerunning rebuilds the level from scratch; the layout file is the source of truth.
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
REIMPORT = os.environ.get("FROG_DEMO_REIMPORT") == "1"
LAYOUT = json.load(open(os.path.join(HERE, "frog_demo_layout.json")))

ROOT = "/Game/Stylized"
LEVEL = ROOT + "/Demo/Lvl_FrogDemo"
NO_COLLISION = {"reeds", "firefly_jar"}
M = 100.0  # layout metres -> Unreal centimetres

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(msg):
    unreal.log(f"[FrogDemo] {msg}")


def setp(obj, key, value):
    """set_editor_property that warns instead of stopping the build (property names drift between versions)."""
    try:
        obj.set_editor_property(key, value)
    except Exception as e:
        name = obj.get_name() if hasattr(obj, "get_name") else type(obj).__name__
        unreal.log_warning(f"[FrogDemo] {name}.{key}: {e}")


# ---------------------------------------------------------------- import

def import_glb(src, dest):
    if not os.path.exists(src):
        unreal.log_warning(f"[FrogDemo] missing {src}")
        return []
    if assets.does_directory_exist(dest) and assets.list_assets(dest) and not REIMPORT:
        return [assets.load_asset(p) for p in assets.list_assets(dest, recursive=True)]
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", src)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tools.import_asset_tasks([task])
    log(f"imported {os.path.basename(src)} -> {dest}")
    return [assets.load_asset(p) for p in assets.list_assets(dest, recursive=True)]


def first(objs, cls):
    return next((o for o in objs if isinstance(o, cls)), None)


def use_complex_collision(mesh):
    try:
        body = mesh.get_editor_property("body_setup")
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        assets.save_loaded_asset(mesh)
    except Exception as e:  # collision is nice to have; keep building
        unreal.log_warning(f"[FrogDemo] collision on {mesh.get_name()}: {e}")


def import_props():
    meshes = {}
    for name in sorted({p["asset"] for p in LAYOUT["props"]}):
        mesh = first(import_glb(os.path.join(ASSET_DIR, f"{name}.glb"), f"{ROOT}/Props/{name}"), unreal.StaticMesh)
        if mesh:
            if name not in NO_COLLISION:
                use_complex_collision(mesh)
            meshes[name] = mesh
        else:
            unreal.log_warning(f"[FrogDemo] no static mesh for {name}")
    return meshes


def import_frog():
    objs = import_glb(os.path.join(ASSET_DIR, "demo", "SK_Frog.glb"), f"{ROOT}/Frog")
    clips = {}
    for o in objs:
        if isinstance(o, unreal.AnimSequence):
            for clip in ("idle", "walk", "run"):
                if clip in o.get_name().lower():
                    clips[clip] = o
    return first(objs, unreal.SkeletalMesh), clips


# ---------------------------------------------------------------- blueprints

def blueprint(name, parent):
    path = f"{ROOT}/Demo/{name}"
    if not assets.does_asset_exist(path):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent)
        tools.create_asset(name, f"{ROOT}/Demo", unreal.Blueprint, factory)
    return path, unreal.EditorAssetLibrary.load_blueprint_class(path)


def make_frog_blueprint(mesh, clips):
    path, cls = blueprint("BP_DemoFrog", unreal.FrogCharacter)
    cdo = unreal.get_default_object(cls)
    cam = LAYOUT["camera"]
    props = {
        "use_diorama_camera": True,
        "diorama_pitch": float(cam["pitch"]),
        "diorama_yaw": float(cam["yaw"]),
        "diorama_arm_length": cam["arm_length_m"] * M,
        "diorama_min_arm_length": cam["min_arm_length_m"] * M,
        "diorama_max_arm_length": cam["max_arm_length_m"] * M,
        "diorama_field_of_view": float(cam["fov"]),
        "stylized_mesh": mesh,
        "stylized_mesh_yaw": float(LAYOUT["frog"]["mesh_yaw"]),
        "idle_animation": clips.get("idle"),
        "walk_animation": clips.get("walk"),
        "run_animation": clips.get("run"),
    }
    for k, v in props.items():
        if v is not None:
            cdo.set_editor_property(k, v)
    assets.save_asset(path)
    return cls


def make_game_mode(pawn_cls):
    parent = unreal.EditorAssetLibrary.load_blueprint_class("/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode")
    path, cls = blueprint("BP_FrogDemoGameMode", parent or unreal.GameModeBase)
    unreal.get_default_object(cls).set_editor_property("default_pawn_class", pawn_cls)
    assets.save_asset(path)
    return cls


# ---------------------------------------------------------------- materials

def flat_material(name, color, roughness, specular=0.5):
    path = f"{ROOT}/Demo/{name}"
    if assets.does_asset_exist(path):
        return assets.load_asset(path)
    mat = tools.create_asset(name, f"{ROOT}/Demo", unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    base = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    base.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    lib.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for prop, value, y in ((unreal.MaterialProperty.MP_ROUGHNESS, roughness, 150),
                           (unreal.MaterialProperty.MP_SPECULAR, specular, 250)):
        c = lib.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, y)
        c.set_editor_property("r", value)
        lib.connect_material_property(c, "", prop)
    lib.recompile_material(mat)
    assets.save_asset(path)
    return mat


# ---------------------------------------------------------------- level

def fresh_level():
    if assets.does_asset_exist(LEVEL):
        levels.load_level(LEVEL)
        actors.destroy_actors(actors.get_all_level_actors())
    else:
        levels.new_level(LEVEL)


def spawn(cls, loc, rot=unreal.Rotator(0, 0, 0), label=None):
    a = actors.spawn_actor_from_class(cls, loc, rot)
    if label:
        a.set_actor_label(label)
    return a


def disk(label, x, y, z, radius, thickness, material, collide=True):
    """Engine cylinder (100 cm wide/tall, centred) as a flat disk whose top is at z."""
    a = actors.spawn_actor_from_object(assets.load_asset("/Engine/BasicShapes/Cylinder.Cylinder"),
                                       unreal.Vector(x * M, y * M, z * M - thickness * M / 2))
    a.set_actor_label(label)
    a.set_actor_scale3d(unreal.Vector(radius * 2, radius * 2, thickness))
    comp = a.get_editor_property("static_mesh_component")
    comp.set_material(0, material)
    if not collide:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return a


def point_light(label, loc, lumens, color, radius_cm, shadows=True):
    a = spawn(unreal.PointLight, loc, label=label)
    c = a.get_component_by_class(unreal.PointLightComponent)
    setp(c, "intensity_units", unreal.LightUnits.LUMENS)
    setp(c, "intensity", lumens)
    c.set_light_color(color)
    setp(c, "attenuation_radius", radius_cm)
    setp(c, "cast_shadows", shadows)
    return a


def place_prop(i, e, mesh):
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
    loc = unreal.Vector(e["x"] * M - ox, e["y"] * M - oy, e.get("z", 0.0) * M - lo.z * k)
    a = actors.spawn_actor_from_object(mesh, loc, unreal.Rotator(0, 0, yaw))
    a.set_actor_label(f"{e['asset']}_{i:02d}")
    a.set_actor_scale3d(unreal.Vector(k, k, k))
    if e["asset"] in NO_COLLISION:
        a.get_editor_property("static_mesh_component").set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    if e.get("collectible"):
        a.set_editor_property("tags", [unreal.Name("Collectible")])
    if "light" in e:
        top = e.get("z", 0.0) * M + (hi.z - lo.z) * k * e["light"] + 20
        jar = e["asset"] == "firefly_jar"
        point_light(f"light_{e['asset']}_{i:02d}", unreal.Vector(e["x"] * M, e["y"] * M, top),
                    150 if jar else (1500 if e["asset"] == "brazier" else 800),
                    unreal.LinearColor(1.0, 0.85, 0.45, 1) if jar else unreal.LinearColor(1.0, 0.55, 0.22, 1),
                    500 if jar else 900, shadows=not jar)


def night_lighting():
    moon = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -40, -135), "Moon")
    mc = moon.get_component_by_class(unreal.DirectionalLightComponent)
    setp(mc, "intensity", 2.0)
    mc.set_light_color(unreal.LinearColor(0.55, 0.68, 1.0, 1))
    setp(mc, "atmosphere_sun_light", True)
    spawn(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), label="Sky")
    sky = spawn(unreal.SkyLight, unreal.Vector(0, 0, 500), label="SkyLight")
    sc = sky.get_component_by_class(unreal.SkyLightComponent)
    setp(sc, "real_time_capture", True)
    setp(sc, "intensity", 1.5)
    sc.set_light_color(unreal.LinearColor(0.6, 0.75, 1.0, 1))
    fog = spawn(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -100), label="Fog")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    setp(fc, "fog_density", 0.03)
    setp(fc, "fog_inscattering_luminance", unreal.LinearColor(0.05, 0.1, 0.22, 1))
    ppv = spawn(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), label="NightPostProcess")
    ppv.set_editor_property("unbound", True)
    s = ppv.get_editor_property("settings")
    for k, v in (("auto_exposure_min_brightness", -1.0), ("auto_exposure_max_brightness", 1.0),
                 ("auto_exposure_bias", -0.5), ("bloom_intensity", 1.2)):
        setp(s, "override_" + k, True)
        setp(s, k, v)
    ppv.set_editor_property("settings", s)


def main():
    if not os.path.isdir(ASSET_DIR):
        raise RuntimeError(f"Copy the stylized asset folder to {ASSET_DIR} (or set FROG_ASSET_DIR).")
    meshes = import_props()
    frog_mesh, clips = import_frog()
    if not frog_mesh:
        unreal.log_warning("[FrogDemo] frog skeletal mesh not found; BP_DemoFrog keeps the default mesh")
    frog_cls = make_frog_blueprint(frog_mesh, clips)
    gm_cls = make_game_mode(frog_cls)
    tint = LAYOUT["ground_tint"]  # darkens the painted grass/dirt for the night lighting
    grass = ground_materials.tinted_material("grass", tint, "Night")
    water = flat_material("M_DemoWater", (0.01, 0.04, 0.09), 0.05, 0.8)
    path_m = ground_materials.tinted_material("dirt", tint, "Night")

    fresh_level()
    g = LAYOUT["ground"]
    disk("Ground", g["x"], g["y"], 0.0, g["radius"], g["thickness"], grass)
    for i, w in enumerate(LAYOUT["water"]):
        disk(f"Pond_{i}", w["x"], w["y"], 0.03, w["radius"], 0.03, water, collide=False)
    for i, p in enumerate(LAYOUT["paths"]):
        disk(f"Path_{i}", p["x"], p["y"], 0.004 + 0.003 * i, p["radius"], 0.008, path_m, collide=False)
    for i, e in enumerate(LAYOUT["props"]):
        if e["asset"] in meshes:
            place_prop(i, e, meshes[e["asset"]])
    ps = LAYOUT["player_start"]
    spawn(unreal.PlayerStart, unreal.Vector(ps["x"] * M, ps["y"] * M, ps["z"] * M + 60),
          unreal.Rotator(0, 0, ps["yaw"]), "PlayerStart")
    night_lighting()

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", gm_cls)
    levels.save_current_level()
    log(f"built {LEVEL} with {len(meshes)} prop meshes; press Play to try it")


main()
