"""Add the cherry blossom trees to the open Lantern Hill level without rebuilding it.

build_lantern_hill.py rebuilds the whole level from lantern_hill_layout.json, which would drop
anything placed by hand in the editor. This script only places the layout's sakura_* props on top
of the level that is already open, the same way build_lantern_hill.py places props, and saves it.
Rerunning replaces the trees it placed before (actors labelled sakura_*) and nothing else.

Run `python Tools/FrogDemo/fetch_assets.py` first (it downloads the trees and cuts the root plate off
sakura_b), open Lvl_LanternHill, then Tools > Execute Python Script with this file.
"""
import json
import math
import os

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
ASSET_DIR = os.environ.get("FROG_ASSET_DIR", os.path.join(PROJECT_DIR, "ExternalAssets", "stylized-assets"))
LAYOUT = json.load(open(os.path.join(HERE, "lantern_hill_layout.json"), encoding="utf-8"))

LIBRARY = "/Game/Stylized/Library"
LEVEL = "/Game/Stylized/Levels/Lvl_LanternHill"
PREFIX = "sakura_"
M = 100.0  # layout metres -> Unreal centimetres

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def log(msg):
    unreal.log(f"[CherryTrees] {msg}")


def mesh(name):
    """The library static mesh called name, imported from ExternalAssets if it isn't there yet."""
    folder = f"{LIBRARY}/{name}"
    if not (assets.does_directory_exist(folder) and assets.list_assets(folder)):
        src = os.path.join(ASSET_DIR, "library", f"{name}.glb")
        if not os.path.exists(src):
            raise RuntimeError(f"{src} is missing; run Tools/FrogDemo/fetch_assets.py first")
        task = unreal.AssetImportTask()
        for k, v in (("filename", src), ("destination_path", folder), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            task.set_editor_property(k, v)
        tools.import_asset_tasks([task])
        log(f"imported {name}")
    m = next((a for a in (assets.load_asset(p) for p in assets.list_assets(folder, recursive=True))
              if isinstance(a, unreal.StaticMesh)), None)
    if not m:
        raise RuntimeError(f"no static mesh in {folder}")
    body = m.get_editor_property("body_setup")
    if body and body.get_editor_property("collision_trace_flag") != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        assets.save_loaded_asset(m)
    return m


def place(i, e):
    """Spawn entry e like build_lantern_hill.place_prop: scaled to its height, bottom centred on x/y/z."""
    m = mesh(e["asset"])
    box = m.get_bounding_box()
    lo, hi = box.min, box.max
    k = e["height"] * M / max(hi.z - lo.z, 1e-3)
    yaw = float(e.get("yaw", 0))
    r = math.radians(yaw)
    ox, oy = -(lo.x + hi.x) / 2 * k, -(lo.y + hi.y) / 2 * k
    ox, oy = ox * math.cos(r) - oy * math.sin(r), ox * math.sin(r) + oy * math.cos(r)
    loc = unreal.Vector(e["x"] * M + ox, e["y"] * M + oy, e.get("z", 0.0) * M - lo.z * k)
    a = actors.spawn_actor_from_object(m, loc, unreal.Rotator(0, 0, yaw))
    a.set_actor_label(f"{e['asset']}_{i:02d}")
    a.set_actor_scale3d(unreal.Vector(k, k, k))
    return a


def main():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != LEVEL:
        raise RuntimeError(f"open {LEVEL} first (the open level is {world.get_path_name()})")
    old = [a for a in actors.get_all_level_actors() if a.get_actor_label().startswith(PREFIX)]
    if old:
        actors.destroy_actors(old)
    placed = [place(i, e) for i, e in enumerate(LAYOUT["props"]) if e["asset"].startswith(PREFIX)]
    levels.save_current_level()
    log(f"placed {', '.join(a.get_actor_label() for a in placed)} in {LEVEL} and saved it")


main()
