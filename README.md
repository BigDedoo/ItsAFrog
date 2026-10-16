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

`AFrogCharacter` options used by the demo:

- **Camera > Diorama**: `bUseDioramaCamera` locks the camera at `DioramaPitch`/`DioramaYaw` and `DioramaArmLength`. Horizontal look input turns it around the frog (`DioramaTurnScale`, 0 locks it). Movement follows the camera's yaw, and the tongue aims where the frog faces. The mouse wheel (or gamepad shoulders) zooms between `DioramaMinArmLength` and `DioramaMaxArmLength`, `DioramaZoomStep` per wheel notch; assign `ZoomAction` to use your own input action, otherwise one is created at runtime.
- **Character > Stylized**: `StylizedMesh` swaps in a skeletal mesh and fits the capsule to it. Use `StylizedMeshYaw` if the model faces the wrong way (the packaged demo frog needs -90, set from `frog.mesh_yaw` in the layout).
- **Character > Locomotion**: `IdleAnimation`, `WalkAnimation`, `RunAnimation` and `RunSpeedThreshold` play clips by speed when the mesh has no Animation Blueprint.
