"""Give Lantern Hill's frog the four-legged chubby body and a working tongue, inside the Unreal Editor.

Run it like the other builders (Tools > Execute Python Script, or headless with
UnrealEditor.exe ... -ExecutePythonScript=<this file>), after build_lantern_hill.py. It reads
demo/SK_FrogQuad.glb and demo/SK_FrogTongue.glb from ExternalAssets/stylized-assets
(fetch_assets.py copies them there from this folder).

What it does:
  1. Imports SK_FrogQuad.glb (the chubby frog: Idle, Walk, Run, TongueSocket bone at the mouth) to
     /Game/Stylized/FrogQuad/Body and SK_FrogTongue.glb (a 30 cm chain Bone_000 > Bone_002 ... Bone_009
     > Bone_001) to /Game/Stylized/FrogQuad/Tongue, and gives their glTF materials skinned-mesh parents.
  2. Makes ABP_FrogQuadTongue, the tongue's Anim Blueprint (parent UTongueAnimInstance): Spline IK from
     Bone_000 to Bone_001 with one Control Point per bone fed from SplineTransforms, an auto-calculated
     spline, full stretch and the bone axis read off the imported chain. Python can't add Anim Graph
     nodes, so the first build copies an Anim Blueprint that already has that graph
     (FROG_TONGUE_ABP_TEMPLATE, default /Game/Characters/Frog_v9/Tongue/ABP_FrogTongue_v9 from the
     frog-v9 branch) and retargets it; later builds reuse the committed asset and reapply the settings.
  3. Adds IA_Tongue to IMC_Default: left mouse button, E and the gamepad right trigger.
  4. Points BP_LanternFrog at the new frog (mesh, clips, the low wide capsule from
     lantern_hill_layout.json), its TongueAction at IA_Tongue and its TongueMesh at the tongue.
Set FROG_DEMO_REIMPORT=SK_FrogQuad (or SK_FrogTongue, or 1) to import the GLBs again.
"""
import json
import os

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
ASSET_DIR = os.environ.get("FROG_ASSET_DIR", os.path.join(PROJECT_DIR, "ExternalAssets", "stylized-assets"))
REIMPORT = os.environ.get("FROG_DEMO_REIMPORT", "")
LAYOUT = json.load(open(os.path.join(HERE, "lantern_hill_layout.json"), encoding="utf-8"))
TEMPLATE = os.environ.get("FROG_TONGUE_ABP_TEMPLATE", "/Game/Characters/Frog_v9/Tongue/ABP_FrogTongue_v9")

ROOT = "/Game/Stylized"
DIR = ROOT + "/FrogQuad"
ABP = DIR + "/ABP_FrogQuadTongue"
FROG_BP = ROOT + "/Levels/BP_LanternFrog"
IA_TONGUE = "/Game/Input/Actions/IA_Tongue"
IMC = "/Game/Input/IMC_Default"
TONGUE_KEYS = ("LeftMouseButton", "E", "Gamepad_RightTrigger")
M = 100.0  # layout metres -> Unreal centimetres

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
bel = unreal.BlueprintEditorLibrary
pins = unreal.BlueprintGraphPinLibrary


def log(msg):
    unreal.log(f"[FrogQuad] {msg}")


# ---------------------------------------------------------------- import

def import_glb(name, dest):
    src = os.path.join(ASSET_DIR, "demo", f"{name}.glb")
    if not (assets.does_directory_exist(dest) and assets.list_assets(dest)) or REIMPORT == "1" or name in REIMPORT.split(","):
        if not os.path.exists(src):
            raise RuntimeError(f"Missing {src}: run Tools/FrogDemo/fetch_assets.py first.")
        task = unreal.AssetImportTask()
        for k, v in (("filename", src), ("destination_path", dest), ("automated", True),
                     ("replace_existing", True), ("save", True)):
            task.set_editor_property(k, v)
        tools.import_asset_tasks([task])
        log(f"imported {name}.glb -> {dest}")
    objs = [assets.load_asset(p) for p in assets.list_assets(dest, recursive=True)]
    mesh = next((o for o in objs if isinstance(o, unreal.SkeletalMesh)), None)
    if not mesh:
        raise RuntimeError(f"No skeletal mesh imported from {name}.glb")
    use_skinned_parents(mesh)
    return mesh, objs


def use_skinned_parents(mesh):
    """Reparent the mesh's glTF material instances to project copies flagged for skeletal meshes.

    Same fix as build_frog_demo.py: Interchange parents them to the engine's M_GLTF, which lacks the
    SkeletalMesh usage flag, so skinned meshes render with the grey default material in game.
    """
    for slot in mesh.get_editor_property("materials"):
        mi = slot.get_editor_property("material_interface")
        parent = mi.get_editor_property("parent") if isinstance(mi, unreal.MaterialInstanceConstant) else None
        if not isinstance(parent, unreal.Material) or parent.get_editor_property("used_with_skeletal_mesh"):
            continue
        path = f"{ROOT}/Frog/{parent.get_name()}_Skinned"
        if not assets.does_asset_exist(path):
            assets.duplicate_asset(parent.get_path_name().split(".")[0], path)
        skinned = assets.load_asset(path)
        if not skinned.get_editor_property("used_with_skeletal_mesh"):
            skinned.set_editor_property("used_with_skeletal_mesh", True)
            unreal.MaterialEditingLibrary.recompile_material(skinned)
            assets.save_asset(path)
        unreal.MaterialEditingLibrary.set_material_instance_parent(mi, skinned)
        assets.save_loaded_asset(mi, only_if_is_dirty=False)  # reparenting doesn't mark the package dirty
        log(f"{mi.get_name()} now uses {path} (skeletal-mesh usage)")


# ---------------------------------------------------------------- tongue Anim Blueprint

def chain_axis(skeleton):
    """Spline IK bone axis: the local axis along which Bone_002 sits from Bone_000."""
    pose = unreal.AnimPoseExtensions.get_reference_pose(skeleton)
    t = unreal.AnimPoseExtensions.get_bone_pose(pose, "Bone_002", unreal.AnimPoseSpaces.LOCAL).translation
    comps = {"X": t.x, "Y": t.y, "Z": t.z}
    axis = max(comps, key=lambda k: abs(comps[k]))
    if comps[axis] < 0:
        unreal.log_warning(f"[FrogQuad] tongue bones run along -{axis}; Spline IK only takes +X/+Y/+Z")
    log(f"tongue chain runs along local {axis} ({t})")
    return getattr(unreal.SplineBoneAxis, axis)


def make_tongue_abp(skeleton, bone_count):
    if not assets.does_asset_exist(ABP):
        if not assets.does_asset_exist(TEMPLATE):
            raise RuntimeError(
                f"{ABP} doesn't exist and its template {TEMPLATE} isn't in the project. Copy an Anim Blueprint "
                "with a Spline IK node fed from SplineTransforms there (or set FROG_TONGUE_ABP_TEMPLATE).")
        assets.duplicate_asset(TEMPLATE, ABP)
        log(f"copied {TEMPLATE} -> {ABP}")
    abp = assets.load_asset(ABP)
    abp.set_editor_property("target_skeleton", skeleton)
    axis = chain_axis(skeleton)

    graph = next(g for g in abp.get_animation_graphs() if g.get_name() == "AnimGraph")
    spline = graph.get_graph_nodes_of_class(unreal.AnimGraphNode_SplineIK, False)
    if len(spline) != 1:
        raise RuntimeError(f"{ABP} needs exactly one Spline IK node, found {len(spline)}")
    spline = spline[0]

    # Unhook the template's SplineTransforms lookups for control points past this chain's bone count.
    for p in control_point_pins(spline)[bone_count:]:
        for q in pins.list_connected_pins(p):
            for r in bel.list_all_pins(pins.get_owning_node(q)):
                pins.break_pin_links(r)

    node = spline.get_editor_property("node")
    start, end = unreal.BoneReference(), unreal.BoneReference()
    start.set_editor_property("bone_name", "Bone_000")
    end.set_editor_property("bone_name", "Bone_001")
    for k, v in (("start_bone", start), ("end_bone", end), ("bone_axis", axis), ("auto_calculate_spline", True),
                 ("stretch", 1.0), ("control_points", [unreal.Transform()] * bone_count)):
        node.set_editor_property(k, v)
    spline.set_editor_property("node", node)

    # The template's tip twist was for its own mesh; this tongue's tip needs none.
    for mod in graph.get_graph_nodes_of_class(unreal.AnimGraphNode_ModifyBone, False):
        pins.set_pin_value(bel.find_input_pin(mod, "Alpha"), "0.0")
        log(f"disabled {bel.get_node_title(mod)}")

    # Compiling reconstructs the node with one Control Points pin per bone; then drop the unhooked lookups.
    bel.compile_blueprint(abp)
    bel.remove_unused_nodes(abp)
    bel.compile_blueprint(abp)
    for i, p in enumerate(control_point_pins(spline)):
        src = [pins.get_owning_node(q) for q in pins.list_connected_pins(p)]
        index = [pins.get_pin_value(r) for n in src for r in bel.list_input_pins(n) if "Dimension" in str(pins.get_pin_name(r))]
        if not src:
            unreal.log_warning(f"[FrogQuad] Control Point {i} isn't fed from SplineTransforms")
        elif index and index[0] != str(i):
            unreal.log_warning(f"[FrogQuad] Control Point {i} reads SplineTransforms[{index[0]}]")
    assets.save_asset(ABP, only_if_is_dirty=False)
    log(f"{ABP}: Spline IK Bone_000-Bone_001, {len(control_point_pins(spline))} control points, "
        f"axis {axis}, status {abp.get_editor_property('status')}")
    return abp


def control_point_pins(spline):
    found = [p for p in bel.list_input_pins(spline) if str(pins.get_pin_name(p)).startswith("ControlPoints_")]
    return sorted(found, key=lambda p: int(str(pins.get_pin_name(p)).split("_")[1]))


# ---------------------------------------------------------------- input

def make_tongue_input():
    if assets.does_asset_exist(IA_TONGUE):
        action = assets.load_asset(IA_TONGUE)
    else:
        folder, name = IA_TONGUE.rsplit("/", 1)
        action = tools.create_asset(name, folder, unreal.InputAction, unreal.InputAction_Factory())
    action.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    assets.save_asset(IA_TONGUE, only_if_is_dirty=False)

    imc = assets.load_asset(IMC)
    mapped = {str(m.get_editor_property("key").export_text())
              for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")
              if m.get_editor_property("action") == action}
    for name in TONGUE_KEYS:
        if name not in mapped:
            key = unreal.Key()
            key.import_text(name)
            imc.map_key(action, key)
            log(f"IMC_Default: {name} -> IA_Tongue")
    assets.save_asset(IMC, only_if_is_dirty=False)
    return action


# ---------------------------------------------------------------- frog

def configure_frog(mesh, clips, tongue, abp, action):
    cls = assets.load_blueprint_class(FROG_BP)
    if not cls:
        raise RuntimeError("Run build_lantern_hill.py first: it creates BP_LanternFrog.")
    cdo = unreal.get_default_object(cls)
    cap = LAYOUT["frog_capsule"]
    for k, v in (("stylized_mesh", mesh), ("idle_animation", clips.get("idle")), ("walk_animation", clips.get("walk")),
                 ("run_animation", clips.get("run")), ("stylized_capsule_height", cap["height"] * M),
                 ("stylized_capsule_radius", cap["radius"] * M), ("tongue_action", action)):
        if v is None:
            unreal.log_warning(f"[FrogQuad] nothing for {k}")
            continue
        cdo.set_editor_property(k, v)
    tm = cdo.get_editor_property("tongue_mesh")
    tm.set_editor_property("skeletal_mesh_asset", tongue)
    tm.set_editor_property("anim_class", abp.generated_class())
    assets.save_asset(FROG_BP, only_if_is_dirty=False)
    log(f"BP_LanternFrog: {mesh.get_name()}, clips {sorted(clips)}, capsule {cap}, tongue {tongue.get_name()} + {abp.get_name()}")


def main():
    frog, objs = import_glb("SK_FrogQuad", DIR + "/Body")
    clips = {}
    for o in objs:
        if isinstance(o, unreal.AnimSequence):
            for clip in ("idle", "walk", "run"):
                if clip in o.get_name().lower():
                    clips[clip] = o
    tongue, _ = import_glb("SK_FrogTongue", DIR + "/Tongue")
    skeleton = tongue.get_editor_property("skeleton")
    bones = unreal.AnimPoseExtensions.get_bone_names(unreal.AnimPoseExtensions.get_reference_pose(skeleton))
    chain = [b for b in bones if str(b).startswith("Bone_")]
    abp = make_tongue_abp(skeleton, len(chain))
    action = make_tongue_input()
    configure_frog(frog, clips, tongue, abp, action)
    log("done; open Lvl_LanternHill and press Play (left mouse, E or right trigger flicks the tongue)")


main()
