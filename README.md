# ItsAFrog

Unreal Engine 5.8 third-person project featuring a controllable frog character.

## Character controls

`AFrogCharacter` provides:

- Third-person spring-arm and follow camera
- Enhanced Input movement relative to camera yaw
- Mouse/gamepad look
- Press-and-hold jump behavior

The class uses the existing input assets in `Content/Input/Actions` and is built as part of the `ItsAFrogEditor` target.

## Build

Build the editor target for Development Win64 with Unreal Engine 5.8:

```text
ItsAFrogEditor Win64 Development
```

## Stylized frog demo

`Tools/FrogDemo` builds `Lvl_FrogDemo`, a small night-time diorama that shows off the stylized Meshy asset set with a high three-quarter camera.

1. Run `python Tools/FrogDemo/fetch_assets.py` to download the prop GLBs from Meshy and copy the packaged frog into `ExternalAssets/stylized-assets` (git-ignored because the GLBs are large).
2. Build and open the editor, then run `Tools/FrogDemo/build_frog_demo.py` with **Tools > Execute Python Script**.
   Or run it without opening the editor UI yourself (the editor starts, runs the script and quits):

   ```text
   UnrealEditor.exe "<path>\ItsAFrog.uproject" -ExecutePythonScript="<path>\Tools\FrogDemo\build_frog_demo.py" -unattended -nosplash
   ```

   Don't use the `-run=pythonscript` commandlet: it imports the assets but crashes in UE 5.8 once the script starts spawning actors into the new level.
3. Open `/Game/Stylized/Demo/Lvl_FrogDemo` and press Play.

The script imports the assets to `/Game/Stylized`, creates `BP_DemoFrog` and `BP_FrogDemoGameMode`, and lays the level out from `Tools/FrogDemo/frog_demo_layout.json` (metres, Unreal axes). Edit the layout and rerun the script to rebuild the level.

`Tools/FrogDemo/build_asset_library.py` (run the same way, after `fetch_assets.py`) imports the basic asset library, 20 props listed in `library_layout.json`, to `/Game/Stylized/Library` and lays them out at real-world size in `/Game/Stylized/Library/Lvl_AssetLibrary`. Run `build_frog_demo.py` first to walk the gallery as the frog.

Both builders call `Tools/FrogDemo/ground_materials.py`, which imports the painted grass and dirt textures in `Tools/FrogDemo/textures` to `/Game/Stylized/Ground` and builds `M_StylizedGrass` (4 m per repeat) and `M_StylizedDirt` (3 m). They are mapped in world space, so they keep the same scale on any mesh, and blend in a larger second sample so the repeat doesn't show. Each level uses a tinted instance (`ground_tint` in its layout file) to suit its lighting.

`AFrogCharacter` options used by the demo:

- **Camera > Diorama**: `bUseDioramaCamera` sets a high three-quarter camera at `DioramaPitch`/`DioramaYaw` and `DioramaArmLength`. Horizontal look input turns it around the frog (`DioramaTurnScale`, 0 locks it) and vertical look input tilts it between `DioramaMinPitch` and `DioramaMaxPitch` (`DioramaTiltScale`, 0 locks it). Movement follows the camera's yaw, and the tongue aims where the frog faces. The mouse wheel (or gamepad shoulders) zooms between `DioramaMinArmLength` and `DioramaMaxArmLength`, `DioramaZoomStep` per wheel notch; assign `ZoomAction` to use your own input action, otherwise one is created at runtime.
- **Character > Stylized**: `StylizedMesh` swaps in a skeletal mesh and fits the capsule to it. Use `StylizedMeshYaw` if the model faces the wrong way (the packaged demo frog needs -90, set from `frog.mesh_yaw` in the layout). `StylizedCapsuleHeight` and `StylizedCapsuleRadius` set the capsule directly: the packaged frog's skeleton carries its scale, so fitting to its bounds gives a 20 cm capsule.
- **Character > Locomotion**: `IdleAnimation`, `WalkAnimation`, `RunAnimation` and `RunSpeedThreshold` play clips by speed when the mesh has no Animation Blueprint.

## Lantern Hill

`Tools/FrogDemo/build_lantern_hill.py` builds `/Game/Stylized/Levels/Lvl_LanternHill`, a short platforming level (a couple of minutes) for the frog. Run it the same way as the other builders, after `build_frog_demo.py`; the layout lives in `Tools/FrogDemo/lantern_hill_layout.json`.

The route: hop the stepping stones across the pond, climb a stump and a stone pillar (the pillar needs a held jump), cross a run of pillars over the water, slip between the thorn bushes, bounce off the red mushroom up to the hill and light the beacon. Ten golden flies are spread along it, some on detours, one only reachable from the top of a mushroom bounce. Two checkpoints catch you when you fall in the water or touch the thorns.

`BP_LanternFrog` is the demo frog with a lower hold-to-jump (`JumpZVelocity` 330, `JumpMaxHoldTime` 0.25 s: a tap clears about 0.8 m, a full hold about 1.4 m) and a 95 cm capsule. The gameplay pieces are C++ in `Source/ItsAFrog/FrogLevel`:

- `AFrogLevelGameMode` keeps the fly count, the respawn point, the run timer and the finish, and sends the player back to the last checkpoint below `RespawnZ`. `AFrogLevelHUD` draws the counter, timer, title, controls, toasts and finish card on the canvas.
- `AFrogFlyPickup`, `AFrogCheckpoint`, `AFrogGoal`, `AFrogBouncePad`, `AFrogRespawnVolume` and `AFrogHintVolume` are trigger boxes the builder places and gives meshes from the asset library.
