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
