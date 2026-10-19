"""Build Lantern Hill, a short platforming level for the frog, inside the Unreal Editor.

Run it like build_frog_demo.py (Tools > Execute Python Script, or headless with
UnrealEditor.exe ... -ExecutePythonScript=<this file>), after build_frog_demo.py and
build_asset_library.py have imported the stylized assets. Missing props are imported from
ExternalAssets/stylized-assets the same way those builders do.

What it does:
  1. Creates BP_LanternFrog (a child of BP_DemoFrog with hold-to-jump and this level's camera)
     and BP_LanternHillGameMode (AFrogLevelGameMode: fly count, checkpoints, respawn, HUD).
  2. Builds /Game/Stylized/Levels/Lvl_LanternHill from lantern_hill_layout.json: grass-topped
     islands in a night pond, props, golden flies, checkpoints, thorn hazards, a bounce mushroom,
     tutorial hints and the beacon goal, lit like the demo diorama.

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
LAYOUT = json.load(open(os.path.join(HERE, "lantern_hill_layout.json"), encoding="utf-8"))

ROOT = "/Game/Stylized"
DIR = ROOT + "/Levels"
LEVEL = DIR + "/Lvl_LanternHill"
M = 100.0  # layout metres -> Unreal centimetres
DRUM_BOTTOM = -150.0  # islands reach this far below the water line (cm)

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log(f"[LanternHill] {msg}")


def setp(obj, key, value):
    """set_editor_property that warns instead of stopping the build (property names drift between versions)."""
    try:
        obj.set_editor_property(key, value)
    except Exception as e:
        name = obj.get_name() if hasattr(obj, "get_name") else type(obj).__name__
        unreal.log_warning(f"[LanternHill] {name}.{key}: {e}")


# ---------------------------------------------------------------- assets

_meshes = {}


def mesh(name):
    """The stylized static mesh called name, from the asset library or the demo props (imported if missing)."""
    if name in _meshes:
        return _meshes[name]
    found = None
    for folder, src in ((f"{ROOT}/Library/{name}", os.path.join(ASSET_DIR, "library", f"{name}.glb")),
                        (f"{ROOT}/Props/{name}", os.path.join(ASSET_DIR, f"{name}.glb"))):
        if not (assets.does_directory_exist(folder) and assets.list_assets(folder)):
            if not os.path.exists(src):
                continue
            task = unreal.AssetImportTask()
            for k, v in (("filename", src), ("destination_path", folder), ("automated", True),
                         ("replace_existing", True), ("save", True)):
                task.set_editor_property(k, v)
            tools.import_asset_tasks([task])
            log(f"imported {name}")
        found = next((a for a in (assets.load_asset(p) for p in assets.list_assets(folder, recursive=True))
                      if isinstance(a, unreal.StaticMesh)), None)
        if found:
            break
    if not found:
        unreal.log_warning(f"[LanternHill] no static mesh for {name}")
    _meshes[name] = found
    return found


def complex_collision(m):
    body = m.get_editor_property("body_setup")
    if body and body.get_editor_property("collision_trace_flag") != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        assets.save_loaded_asset(m)


def blueprint(name, parent):
    path = f"{DIR}/{name}"
    if not assets.does_asset_exist(path):
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent)
        tools.create_asset(name, DIR, unreal.Blueprint, factory)
    return path, assets.load_blueprint_class(path)


def make_frog():
    """BP_LanternFrog: the demo frog (mesh, clips, diorama camera) with hold-to-jump and this level's view."""
    parent = assets.load_blueprint_class(f"{ROOT}/Demo/BP_DemoFrog")
    if not parent:
        raise RuntimeError("Run build_frog_demo.py first: BP_LanternFrog extends its BP_DemoFrog.")
    path, cls = blueprint("BP_LanternFrog", parent)
    cdo = unreal.get_default_object(cls)
    cam = LAYOUT["camera"]
    for k, v in (("jump_max_hold_time", float(LAYOUT["jump_max_hold_time"])),
                 ("stylized_capsule_height", LAYOUT["frog_capsule"]["height"] * M),
                 ("stylized_capsule_radius", LAYOUT["frog_capsule"]["radius"] * M),
                 ("diorama_pitch", float(cam["pitch"])), ("diorama_yaw", float(cam["yaw"])),
                 ("diorama_min_pitch", float(cam["min_pitch"])), ("diorama_max_pitch", float(cam["max_pitch"])),
                 ("diorama_arm_length", cam["arm_length_m"] * M),
                 ("diorama_min_arm_length", cam["min_arm_length_m"] * M),
                 ("diorama_max_arm_length", cam["max_arm_length_m"] * M),
                 ("diorama_field_of_view", float(cam["fov"]))):
        setp(cdo, k, v)
    setp(cdo.get_editor_property("character_movement"), "jump_z_velocity", float(LAYOUT["jump_z_velocity"]))
    assets.save_asset(path)
    return cls


def make_game_mode(pawn_cls):
    path, cls = blueprint("BP_LanternHillGameMode", unreal.FrogLevelGameMode)
    cdo = unreal.get_default_object(cls)
    third_person = assets.load_blueprint_class("/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode")
    if third_person:  # its controller adds the default input mapping
        setp(cdo, "player_controller_class", unreal.get_default_object(third_person).get_editor_property("player_controller_class"))
    setp(cdo, "default_pawn_class", pawn_cls)
    setp(cdo, "level_title", unreal.Text(LAYOUT["title"]))
    setp(cdo, "level_subtitle", unreal.Text(LAYOUT["subtitle"]))
    setp(cdo, "respawn_z", LAYOUT["respawn_z"] * M)
    assets.save_asset(path)
    return cls


def flat_material(name, color, roughness, specular=0.5):
    path = f"{ROOT}/Demo/{name}"
    if assets.does_asset_exist(path):
        return assets.load_asset(path)
    mat = tools.create_asset(name, f"{ROOT}/Demo", unreal.Material, unreal.MaterialFactoryNew())
    base = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    base.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for prop, value, y in ((unreal.MaterialProperty.MP_ROUGHNESS, roughness, 150),
                           (unreal.MaterialProperty.MP_SPECULAR, specular, 250)):
        c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, y)
        c.set_editor_property("r", value)
        mel.connect_material_property(c, "", prop)
    mel.recompile_material(mat)
    assets.save_asset(path)
    return mat


def cliff_material(tint):
    """M_LanternCliff: the painted dirt projected on the island sides (world XZ / YZ picked by the normal)."""
    path = f"{DIR}/M_LanternCliff"
    if assets.does_asset_exist(path):
        mat = assets.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset("M_LanternCliff", DIR, unreal.Material, unreal.MaterialFactoryNew())
    tex = ground_materials.texture("dirt", "color")

    def expr(cls, x, y, **props):
        e = mel.create_material_expression(mat, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    world = expr(unreal.MaterialExpressionWorldPosition, -1200, 0)
    samples = []
    for i, (r, g) in enumerate(((True, False), (False, True))):  # XZ, then YZ
        mask = expr(unreal.MaterialExpressionComponentMask, -1000, i * 200, r=r, g=g, b=True, a=False)
        mel.connect_material_expressions(world, "", mask, "")
        uv = expr(unreal.MaterialExpressionMultiply, -800, i * 200, const_b=-1.0 / 250.0)
        mel.connect_material_expressions(mask, "", uv, "A")
        s = expr(unreal.MaterialExpressionTextureSample, -600, i * 200, texture=tex)
        mel.connect_material_expressions(uv, "", s, "UVs")
        samples.append(s)
    normal = expr(unreal.MaterialExpressionVertexNormalWS, -1000, 450)
    nx = expr(unreal.MaterialExpressionComponentMask, -800, 450, r=True, g=False, b=False, a=False)
    mel.connect_material_expressions(normal, "", nx, "")
    ax = expr(unreal.MaterialExpressionAbs, -650, 450)
    mel.connect_material_expressions(nx, "", ax, "")
    blend = expr(unreal.MaterialExpressionLinearInterpolate, -400, 100)
    mel.connect_material_expressions(samples[0], "RGB", blend, "A")
    mel.connect_material_expressions(samples[1], "RGB", blend, "B")
    mel.connect_material_expressions(ax, "", blend, "Alpha")
    # Darker towards the water so the islands sit in the pond.
    height = expr(unreal.MaterialExpressionComponentMask, -1000, 650, r=False, g=False, b=True, a=False)
    mel.connect_material_expressions(world, "", height, "")
    shade = expr(unreal.MaterialExpressionMultiply, -800, 650, const_b=1.0 / 400.0)
    mel.connect_material_expressions(height, "", shade, "A")
    shade_c = expr(unreal.MaterialExpressionClamp, -650, 650, min_default=0.35, max_default=1.0)
    mel.connect_material_expressions(shade, "", shade_c, "")
    tinted = expr(unreal.MaterialExpressionMultiply, -250, 100)
    mel.connect_material_expressions(blend, "", tinted, "A")
    tint_c = expr(unreal.MaterialExpressionConstant3Vector, -450, 300, constant=unreal.LinearColor(*tint, 1.0))
    mul2 = expr(unreal.MaterialExpressionMultiply, -300, 400)
    mel.connect_material_expressions(tint_c, "", mul2, "A")
    mel.connect_material_expressions(shade_c, "", mul2, "B")
    mel.connect_material_expressions(mul2, "", tinted, "B")
    mel.connect_material_property(tinted, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = expr(unreal.MaterialExpressionConstant, -250, 300, r=0.9)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    assets.save_asset(path)
    return mat


# ---------------------------------------------------------------- level pieces

def no_collision(comp):
    # The profile as well as the flag: the flag alone left the pond walkable.
    comp.set_collision_profile_name("NoCollision")
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)


def spawn(cls, loc, rot=None, label=None):
    a = actors.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0, 0, 0))
    if label:
        a.set_actor_label(label)
    return a


def cylinder(label, x, y, z_bottom, z_top, radius, material, collide=True):
    """Engine cylinder (100 cm wide and tall, centred) stretched between two heights (cm)."""
    a = actors.spawn_actor_from_object(assets.load_asset("/Engine/BasicShapes/Cylinder.Cylinder"),
                                       unreal.Vector(x * M, y * M, (z_bottom + z_top) / 2))
    a.set_actor_label(label)
    a.set_actor_scale3d(unreal.Vector(radius * 2, radius * 2, (z_top - z_bottom) / 100.0))
    comp = a.get_editor_property("static_mesh_component")
    comp.set_material(0, material)
    if not collide:
        no_collision(comp)
    return a


def island(e, grass, cliff):
    top = e["top"] * M
    cylinder(f"Island_{e['name']}", e["x"], e["y"], DRUM_BOTTOM, top - 8, e["radius"], cliff)
    # A slightly wider grass cap gives the drum a soft lip.
    cylinder(f"Island_{e['name']}_Grass", e["x"], e["y"], top - 14, top, e["radius"] + 0.12, grass)


def point_light(label, loc, lumens, color, radius_cm, shadows=True):
    a = spawn(unreal.PointLight, loc, label=label)
    c = a.get_component_by_class(unreal.PointLightComponent)
    setp(c, "intensity_units", unreal.LightUnits.LUMENS)
    setp(c, "intensity", lumens)
    c.set_light_color(color)
    setp(c, "attenuation_radius", radius_cm)
    setp(c, "cast_shadows", shadows)
    return a


def fit(m, e):
    """(scale vector, bounds min, bounds max) fitting mesh m to the entry's width and/or height."""
    box = m.get_bounding_box()
    lo, hi = box.min, box.max
    kw = e["width"] * M / max(hi.x - lo.x, hi.y - lo.y, 1e-3) if "width" in e else None
    kh = e["height"] * M / max(hi.z - lo.z, 1e-3) if "height" in e else None
    kxy = kw or kh
    kz = kh or kw
    return unreal.Vector(kxy, kxy, kz), lo, hi


def local_offset(lo, hi, scale):
    """Relative location that centres the scaled bounds on the pivot with their bottom at 0."""
    return unreal.Vector(-(lo.x + hi.x) / 2 * scale.x, -(lo.y + hi.y) / 2 * scale.y, -lo.z * scale.z)


def place_prop(i, e):
    m = mesh(e["asset"])
    if not m:
        return None
    scale, lo, hi = fit(m, e)
    yaw = float(e.get("yaw", 0))
    off = local_offset(lo, hi, scale)
    r = math.radians(yaw)
    ox, oy = off.x * math.cos(r) - off.y * math.sin(r), off.x * math.sin(r) + off.y * math.cos(r)
    base = unreal.Vector(e["x"] * M, e["y"] * M, e.get("z", 0.0) * M)
    a = actors.spawn_actor_from_object(m, unreal.Vector(base.x + ox, base.y + oy, base.z + off.z), unreal.Rotator(0, 0, yaw))
    a.set_actor_label(f"{e['asset']}_{i:02d}")
    a.set_actor_scale3d(scale)
    comp = a.get_editor_property("static_mesh_component")
    if e.get("collision", True):
        complex_collision(m)
    else:
        no_collision(comp)
    if "light" in e:
        height = (hi.z - lo.z) * scale.z
        jar = e["asset"] == "firefly_jar"
        lumens = 150 if jar else 1500 if e["asset"] == "brazier" else 900 if e["asset"] == "torch_post" else 800
        color = unreal.LinearColor(1.0, 0.85, 0.45, 1) if jar else unreal.LinearColor(1.0, 0.55, 0.22, 1)
        point_light(f"light_{e['asset']}_{i:02d}", unreal.Vector(base.x, base.y, base.z + height * e["light"] + 20),
                    lumens, color, 500 if jar else 900, shadows=not jar)
    return a


def mesh_component(actor, m, e):
    """Fit the actor's Mesh component to the entry's size, standing on the actor's pivot."""
    scale, lo, hi = fit(m, e)
    comp = actor.get_editor_property("mesh")
    comp.set_static_mesh(m)
    comp.set_relative_scale3d(scale)
    comp.set_relative_location(local_offset(lo, hi, scale), False, False)
    return scale, lo, hi


def at(e, dz=0.0):
    return unreal.Vector(e["x"] * M, e["y"] * M, e.get("z", 0.0) * M + dz)


def place_fly(i, e, fly_mesh):
    a = spawn(unreal.FrogFlyPickup, at(e), unreal.Rotator(0, 0, 90), f"GoldenFly_{i:02d}")
    scale, lo, hi = fit(fly_mesh, {"height": LAYOUT["fly_height"]})
    comp = a.get_editor_property("mesh")
    comp.set_static_mesh(fly_mesh)
    comp.set_relative_scale3d(scale)
    # Centre the fly on the pivot so it bobs about the layout point.
    comp.set_relative_location(unreal.Vector(-(lo.x + hi.x) / 2 * scale.x, -(lo.y + hi.y) / 2 * scale.y,
                                             -(lo.z + hi.z) / 2 * scale.z), False, False)


def place_checkpoint(i, e):
    a = spawn(unreal.FrogCheckpoint, at(e), unreal.Rotator(0, 0, e.get("yaw", 0)), f"Checkpoint_{i + 1}")
    mesh_component(a, mesh("checkpoint_flag"), {"height": LAYOUT["checkpoint_height"]})


def place_bramble(i, e):
    m = mesh("thorn_bramble")
    place_prop(100 + i, dict(e, asset="thorn_bramble"))
    scale, lo, hi = fit(m, e)
    w, h = (hi.x - lo.x) * scale.x, (hi.z - lo.z) * scale.z
    a = spawn(unreal.FrogRespawnVolume, at(e), unreal.Rotator(0, 0, e.get("yaw", 0)), f"Thorns_{i:02d}")
    trig = a.get_editor_property("trigger")
    trig.set_box_extent(unreal.Vector(w * 0.4, w * 0.4, h * 0.45), True)
    trig.set_relative_location(unreal.Vector(0, 0, h * 0.45), False, False)
    setp(a, "message", unreal.Text("Ouch, thorns!"))


def place_bounce(i, e):
    m = mesh(e["asset"])
    complex_collision(m)
    a = spawn(unreal.FrogBouncePad, at(e), unreal.Rotator(0, 0, e.get("yaw", 0)), f"BounceMushroom_{i:02d}")
    scale, lo, hi = mesh_component(a, m, e)
    top = (hi.z - lo.z) * scale.z
    cap = (hi.x - lo.x) * scale.x * 0.5
    trig = a.get_editor_property("trigger")
    trig.set_box_extent(unreal.Vector(cap * 0.7, cap * 0.7, 30), True)
    trig.set_relative_location(unreal.Vector(0, 0, top + 5), False, False)
    setp(a, "launch_speed", float(e["launch"]))


def place_hint(i, e):
    a = spawn(unreal.FrogHintVolume, at(e), label=f"Hint_{i:02d}")
    trig = a.get_editor_property("trigger")
    r = e["radius"] * M
    trig.set_box_extent(unreal.Vector(r, r, 150), True)
    trig.set_relative_location(unreal.Vector(0, 0, 150), False, False)
    setp(a, "message", unreal.Text(e["text"]))


def place_goal(e):
    m = mesh(e["asset"])
    complex_collision(m)
    a = spawn(unreal.FrogGoal, at(e), unreal.Rotator(0, 0, e.get("yaw", 0)), "Goal_Beacon")
    mesh_component(a, m, e)


def night_lighting():
    moon = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -42, -150), "Moon")
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


# ---------------------------------------------------------------- build

def main():
    frog_cls = make_frog()
    gm_cls = make_game_mode(frog_cls)
    tint = LAYOUT["ground_tint"]
    grass = ground_materials.tinted_material("grass", tint, "Night")
    path_m = ground_materials.tinted_material("dirt", tint, "Night")
    cliff = cliff_material([c * 0.8 for c in tint])
    water = flat_material("M_DemoWater", (0.01, 0.04, 0.09), 0.05, 0.8)

    if assets.does_asset_exist(LEVEL):
        levels.load_level(LEVEL)
        actors.destroy_actors(actors.get_all_level_actors())
    else:
        levels.new_level(LEVEL)

    w = LAYOUT["water"]
    cylinder("Pond", w["x"], w["y"], -5, 0, w["radius"], water, collide=False)
    for e in LAYOUT["islands"]:
        island(e, grass, cliff)
    for i, p in enumerate(LAYOUT["paths"]):
        top = p["top"] * M + 0.4 + 0.2 * i
        cylinder(f"Path_{i:02d}", p["x"], p["y"], top - 1, top, p["radius"], path_m, collide=False)
    for i, e in enumerate(LAYOUT["props"]):
        place_prop(i, e)

    fly_mesh = mesh("golden_fly")
    for i, e in enumerate(LAYOUT["flies"]):
        place_fly(i, e, fly_mesh)
    for i, e in enumerate(LAYOUT["checkpoints"]):
        place_checkpoint(i, e)
    for i, e in enumerate(LAYOUT["brambles"]):
        place_bramble(i, e)
    for i, e in enumerate(LAYOUT["bounce_pads"]):
        place_bounce(i, e)
    for i, e in enumerate(LAYOUT["hints"]):
        place_hint(i, e)
    place_goal(LAYOUT["goal"])

    ps = LAYOUT["player_start"]
    spawn(unreal.PlayerStart, at(ps, 100), unreal.Rotator(0, 0, ps["yaw"]), "PlayerStart")
    night_lighting()

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", gm_cls)
    levels.save_current_level()
    log(f"built {LEVEL}: {len(LAYOUT['flies'])} golden flies, {len(LAYOUT['checkpoints'])} checkpoints; press Play to try it")


main()
