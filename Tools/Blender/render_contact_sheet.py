"""Six-view contact sheet of the frog for the visual check (after the census).

Target: Blender 5.2 LTS, Python 3.13. Workbench renders under --background
with a software GL context; Cycles is not used (the sheet is for proportion,
not the verdict). The only operator called is render.render, which has no
data-API equivalent.

    blender --background --factory-startup --python-exit-code 1 \
            --python Tools/Blender/render_contact_sheet.py -- \
            --blend Art/Frog/frog.blend --out Art/Frog/frog_contact_sheet.png
"""

import argparse
import math
import os
import sys
import tempfile

import bpy
from mathutils import Vector

REQUIRED_BLENDER = (5, 2)
assert bpy.app.version[:2] == REQUIRED_BLENDER, (
    f"render_contact_sheet.py targets Blender {REQUIRED_BLENDER}, running {bpy.app.version_string}"
)

MM = 0.001

TILE_PX = 640
COLUMNS = 3
LABEL_PX = 34
ORTHO_MARGIN = 0.80          # ortho frame = bounding-sphere diameter * this
CAMERA_DISTANCE = 5000 * MM
THREE_QUARTER_YAW_DEG = 35.0
THREE_QUARTER_PITCH_DEG = 25.0
BACKGROUND = (0.92, 0.92, 0.90)

# name -> camera direction (from the model toward the camera). The frog faces -Y.
VIEWS = {
    "front": Vector((0, -1, 0)),
    "back": Vector((0, 1, 0)),
    "left": Vector((1, 0, 0)),     # the frog's own left side (+X)
    "right": Vector((-1, 0, 0)),
    "top": Vector((0, 0, 1)),
    "three-quarter": None,         # computed from the yaw/pitch constants
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    return ap.parse_args(argv)


def scene_bounds(scene):
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for obj in scene.objects:
        if obj.type != 'MESH':
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def setup_render(scene):
    scene.render.engine = 'BLENDER_WORKBENCH'
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'MATERIAL'
    shading.show_cavity = True
    shading.cavity_type = 'WORLD'
    shading.show_object_outline = True
    shading.background_type = 'VIEWPORT'
    shading.background_color = BACKGROUND
    scene.display.render_aa = '8'
    scene.render.resolution_x = TILE_PX
    scene.render.resolution_y = TILE_PX
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'


def main():
    args = parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args.blend))
    scene = bpy.context.scene
    setup_render(scene)

    lo, hi = scene_bounds(scene)
    center = (lo + hi) / 2
    extent = (hi - lo).length    # bounding-sphere diameter: every view fits

    cam_data = bpy.data.cameras.new("SheetCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = extent * ORTHO_MARGIN
    cam_data.clip_end = CAMERA_DISTANCE * 2
    cam = bpy.data.objects.new("SheetCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    yaw, pitch = math.radians(THREE_QUARTER_YAW_DEG), math.radians(THREE_QUARTER_PITCH_DEG)
    VIEWS["three-quarter"] = Vector((math.sin(yaw) * math.cos(pitch),
                                     -math.cos(yaw) * math.cos(pitch),
                                     math.sin(pitch)))

    tmp = tempfile.mkdtemp()
    tiles = []
    for name, direction in VIEWS.items():
        d = direction.normalized()
        cam.location = center + d * CAMERA_DISTANCE
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler() if name != "top" else (0, 0, 0)
        path = os.path.join(tmp, f"{name}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        tiles.append((name, path))

    from PIL import Image, ImageDraw   # tiling only; Blender does the drawing

    rows = math.ceil(len(tiles) / COLUMNS)
    sheet = Image.new("RGB", (COLUMNS * TILE_PX, rows * (TILE_PX + LABEL_PX)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (name, path) in enumerate(tiles):
        x, y = (i % COLUMNS) * TILE_PX, (i // COLUMNS) * (TILE_PX + LABEL_PX)
        sheet.paste(Image.open(path).convert("RGB"), (x, y + LABEL_PX))
        draw.text((x + 12, y + 8), name, fill="black", font_size=22)
    sheet.save(os.path.abspath(args.out))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
