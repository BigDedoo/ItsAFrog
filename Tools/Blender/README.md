# Frog character (Blender, scripted)

`build_frog.py` builds the frog mesh from named parameters, runs a geometry census, then
exports `Art/Frog/frog.glb` and `Art/Frog/frog.blend`. `render_contact_sheet.py` renders the
six-view sheet used for the visual check.

Pinned to **Blender 5.2 LTS / Python 3.13**; both scripts assert the version on start.

```text
blender --background --factory-startup --python-exit-code 1 \
        --python Tools/Blender/build_frog.py -- --out Art/Frog
blender --background --factory-startup --python-exit-code 1 \
        --python Tools/Blender/render_contact_sheet.py -- \
        --blend Art/Frog/frog.blend --out Art/Frog/frog_contact_sheet.png
```

Without a Blender install, `pip install bpy==5.2.2 pillow` (Python 3.13) and run the same
scripts with `python`, dropping the `--`.

## Conventions

- 1 Blender unit = 1 metre (`MM = 0.001`); glTF exports 1:1, so the frog is 1.0 m tall,
  sized to the `AFrogCharacter` capsule (42 cm radius, 96 cm half-height).
- +Z up, the frog faces -Y in Blender, which becomes +Y up / +Z forward in the glTF.
- Every dimension is a named constant at the top of `build_frog.py`. Visual fixes change
  those constants only.
- Geometry is built through `bpy.data` / `bmesh`. The only operators are the glTF export
  and the `.blend` save (plus `render.render` in the sheet script).
- An empty named `TongueSocket` sits just inside the mouth, matching
  `AFrogCharacter::TongueSocketName`.

## Census

Each mesh must have zero non-manifold edges, flipped neighbours, loose verts, degenerate
faces and self-overlaps, exactly one shell and positive volume. The body must be exactly
`FROG_HEIGHT` tall, sit on z = 0 and fit `MAX_WIDTH`. The build fails before exporting if
any of these is off.

## Parts

| Object | What |
| --- | --- |
| `FrogBody` | Metaball body, head, eye bumps, legs and toes merged into one mesh; skin + belly materials |
| `FrogEye_L/R`, `FrogPupil_L/R`, `FrogHighlight_L/R` | Eye spheres |
| `FrogMouth` | Smile tube, ray-cast onto the face |
| `FrogNostril_L/R`, `FrogCheek_L/R` | Face details, ray-cast onto the face |
