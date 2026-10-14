"""Build the ItsAFrog character mesh headlessly.

Target: Blender 5.2 LTS, Python 3.13. Uses bpy.data / bmesh only; the two
operators it calls are named below (glTF export and .blend save have no data
API equivalent).

Run (either form):
    blender --background --factory-startup --python-exit-code 1 \
            --python Tools/Blender/build_frog.py -- --out Art/Frog
    python Tools/Blender/build_frog.py --out Art/Frog   # with `pip install bpy==5.2.2`

APIs used that changed in 4.0 or later:
    - Mesh.shade_smooth()                 added 4.1 (replaces bpy.ops.object.shade_smooth)
    - Material node tree, Principled BSDF  socket names "Base Color"/"Roughness", stable since 4.0
    - bpy.ops.export_scene.gltf           export_yup / export_apply, stable through 5.2
    - Metaball elements                   unchanged API, evaluated through evaluated_get() (5.2)
"""

import argparse
import math
import os
import sys

import bpy  # must precede bmesh/mathutils when bpy runs as a module
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

# --------------------------------------------------------------------------
# Version pin: fail loudly on the wrong Blender instead of half-working.
# --------------------------------------------------------------------------
REQUIRED_BLENDER = (5, 2)
assert bpy.app.version[:2] == REQUIRED_BLENDER, (
    f"build_frog.py targets Blender {REQUIRED_BLENDER}, running {bpy.app.version_string}"
)

# --------------------------------------------------------------------------
# Units: 1 Blender unit = 1 metre (glTF mandates metres). A 20 mm part is 0.02.
# Axes: +Z up, the frog faces -Y (Blender "front" view). glTF export makes
# that +Y up / +Z forward.
# --------------------------------------------------------------------------
MM = 0.001

# ---- Overall size (fits the AFrogCharacter capsule: radius 420, half-height 960 mm)
FROG_HEIGHT = 1000 * MM          # ground to top of eye bumps, enforced exactly
CAPSULE_RADIUS = 420 * MM        # from FrogCharacter.cpp InitCapsuleSize(42, 96)
MAX_WIDTH = 2 * CAPSULE_RADIUS + 200 * MM   # feet may poke slightly past the capsule

# ---- Metaball body (positions/radii in the unscaled build space; the whole
#      frog is uniformly scaled to FROG_HEIGHT afterwards)
MB_RESOLUTION = 12 * MM
MB_THRESHOLD = 0.6
MB_STIFFNESS = 2.0
REPAIR_WELD_DIST = 0.5 * MM   # metaball polygonising leaves sliver faces; weld below this

BODY_CENTER = (0, 60 * MM, 330 * MM)
BODY_RADIUS = 420 * MM
BODY_SCALE = (1.00, 0.95, 0.85)

HEAD_CENTER = (0, -140 * MM, 560 * MM)
HEAD_RADIUS = 450 * MM
HEAD_SCALE = (1.38, 0.90, 0.68)

EYE_BUMP_CENTER = (260 * MM, -150 * MM, 760 * MM)   # mirrored in X
EYE_BUMP_RADIUS = 230 * MM

THIGH_CENTER = (300 * MM, 110 * MM, 210 * MM)       # mirrored in X
THIGH_RADIUS = 290 * MM
THIGH_SCALE = (0.80, 1.20, 0.80)

FOOT_CENTER = (300 * MM, -140 * MM, 60 * MM)        # back feet, mirrored in X
FOOT_RADIUS = 240 * MM
FOOT_SCALE = (0.80, 1.30, 0.45)

ARM_TOP = (230 * MM, -240 * MM, 330 * MM)           # front legs, mirrored in X
ARM_BOTTOM = (260 * MM, -310 * MM, 90 * MM)
ARM_RADIUS = 140 * MM

HAND_CENTER = (270 * MM, -350 * MM, 60 * MM)
HAND_RADIUS = 180 * MM
HAND_SCALE = (1.00, 0.90, 0.45)

TOE_COUNT = 3
TOE_RADIUS = 90 * MM
TOE_SPREAD_DEG = 30.0             # fan angle between neighbouring toes
FOOT_TOE_REACH = 210 * MM         # toe distance ahead of the foot centre
HAND_TOE_REACH = 140 * MM

# ---- Belly patch (material split on the body mesh, no extra geometry)
BELLY_CENTER_Z = 270 * MM
BELLY_RADIUS_X = 160 * MM
BELLY_RADIUS_Z = 210 * MM
BELLY_MIN_FRONT_NORMAL = 0.35     # -normal.y above this counts as front-facing

# ---- Eyes (separate closed meshes resting on the eye bumps)
EYE_RADIUS = 125 * MM
EYE_OUTSET = 50 * MM              # eye centre pushed from bump centre along EYE_DIRECTION
EYE_DIRECTION = (0.15, -0.90, 0.40)   # outward / forward / up (X mirrored)
PUPIL_RADIUS = 72 * MM
PUPIL_DEPTH_SCALE = 0.45          # flattens the pupil disc
PUPIL_DIRECTION = (0.10, -1.0, 0.05)
HIGHLIGHT_RADIUS = 22 * MM
HIGHLIGHT_OFFSET = (-28 * MM, 0, 30 * MM)   # on the pupil, toward the nose and up
SPHERE_SEGMENTS = 32
SPHERE_RINGS = 16

# ---- Face details placed by ray-casting onto the body surface
MOUTH_HALF_WIDTH = 210 * MM
MOUTH_Z = 505 * MM                # height of the mouth corners
MOUTH_SMILE_DEPTH = 60 * MM       # how far the centre dips below the corners
MOUTH_TUBE_RADIUS = 18 * MM
MOUTH_SAMPLES = 24
MOUTH_EMBED = 6 * MM              # tube centre sinks this far into the skin

NOSTRIL_X = 55 * MM
NOSTRIL_Z = 590 * MM
NOSTRIL_RADIUS = 14 * MM

CHEEK_X = 265 * MM
CHEEK_Z = 545 * MM
CHEEK_RADIUS = 60 * MM
CHEEK_DEPTH_SCALE = 0.25
CHEEK_EMBED = 6 * MM

TONGUE_SOCKET_NAME = "TongueSocket"   # matches AFrogCharacter::TongueSocketName
TONGUE_SOCKET_INSET = 40 * MM

# ---- Colours (linear RGB)
COLOR_SKIN = (0.18, 0.55, 0.12, 1.0)
COLOR_BELLY = (0.78, 0.86, 0.45, 1.0)
COLOR_EYE = (0.95, 0.95, 0.92, 1.0)
COLOR_PUPIL = (0.02, 0.02, 0.03, 1.0)
COLOR_MOUTH = (0.10, 0.02, 0.03, 1.0)
COLOR_CHEEK = (0.95, 0.40, 0.45, 1.0)
SKIN_ROUGHNESS = 0.45

# ---- Census tolerances
DEGENERATE_AREA = 1e-8            # m^2
BVH_EPSILON = 1e-6
SIZE_TOLERANCE = 1e-5


def mirror_x(p):
    return (-p[0], p[1], p[2])


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output directory for frog.glb / frog.blend")
    return ap.parse_args(argv)


def reset_scene():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                 bpy.data.metaballs, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for block in list(coll):
            coll.remove(block)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    return scene


def make_material(name, color, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color          # also what Workbench shows
    mat.roughness = roughness
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


# --------------------------------------------------------------------------
# Body: metaballs give one smooth blended skin, converted to a real mesh
# --------------------------------------------------------------------------
def add_ellipsoid(mb, co, radius, scale):
    el = mb.elements.new(type='ELLIPSOID')
    el.co = co
    el.radius = radius
    el.size_x, el.size_y, el.size_z = scale
    el.stiffness = MB_STIFFNESS
    return el


def add_ball(mb, co, radius):
    el = mb.elements.new(type='BALL')
    el.co = co
    el.radius = radius
    el.stiffness = MB_STIFFNESS
    return el


def add_capsule(mb, a, b, radius):
    a, b = Vector(a), Vector(b)
    axis = b - a
    el = mb.elements.new(type='CAPSULE')
    el.co = (a + b) / 2
    el.radius = radius
    el.size_x = axis.length / 2
    el.rotation = Vector((1, 0, 0)).rotation_difference(axis.normalized())
    el.stiffness = MB_STIFFNESS
    return el


def add_toes(mb, center, reach, sign):
    mid = (TOE_COUNT - 1) / 2
    for i in range(TOE_COUNT):
        ang = math.radians((i - mid) * TOE_SPREAD_DEG) * sign
        off = Vector((math.sin(ang) * reach, -math.cos(ang) * reach, 0))
        add_ball(mb, Vector(center) + off, TOE_RADIUS)


def build_body(scene):
    mb = bpy.data.metaballs.new("FrogBodyMeta")
    mb.resolution = MB_RESOLUTION
    mb.render_resolution = MB_RESOLUTION
    mb.threshold = MB_THRESHOLD

    add_ellipsoid(mb, BODY_CENTER, BODY_RADIUS, BODY_SCALE)
    add_ellipsoid(mb, HEAD_CENTER, HEAD_RADIUS, HEAD_SCALE)
    for side in (1, -1):
        m = (lambda p: p) if side == 1 else mirror_x
        add_ball(mb, m(EYE_BUMP_CENTER), EYE_BUMP_RADIUS)
        add_ellipsoid(mb, m(THIGH_CENTER), THIGH_RADIUS, THIGH_SCALE)
        add_ellipsoid(mb, m(FOOT_CENTER), FOOT_RADIUS, FOOT_SCALE)
        add_toes(mb, m(FOOT_CENTER), FOOT_TOE_REACH, side)
        add_capsule(mb, m(ARM_TOP), m(ARM_BOTTOM), ARM_RADIUS)
        add_ellipsoid(mb, m(HAND_CENTER), HAND_RADIUS, HAND_SCALE)
        add_toes(mb, m(HAND_CENTER), HAND_TOE_REACH, side)

    meta_obj = bpy.data.objects.new("FrogBodyMeta", mb)
    scene.collection.objects.link(meta_obj)
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(meta_obj.evaluated_get(dg))
    mesh.name = "FrogBody"
    bpy.data.objects.remove(meta_obj)
    bpy.data.metaballs.remove(mb)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=REPAIR_WELD_DIST)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=REPAIR_WELD_DIST)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("FrogBody", mesh)
    scene.collection.objects.link(obj)
    return obj


def normalize_height(body):
    """Uniformly scale the metaball result so it is exactly FROG_HEIGHT tall,
    sitting on z=0 and centred in X. Returns the factor so the face details,
    authored in build space, can be scaled identically."""
    zs = [v.co.z for v in body.data.vertices]
    xs = [v.co.x for v in body.data.vertices]
    zmin, zmax = min(zs), max(zs)
    xmid = (min(xs) + max(xs)) / 2
    factor = FROG_HEIGHT / (zmax - zmin)
    mat = Matrix.Scale(factor, 4) @ Matrix.Translation((-xmid, 0, -zmin))
    body.data.transform(mat)
    return mat


# --------------------------------------------------------------------------
# Separate closed parts
# --------------------------------------------------------------------------
def sphere_object(scene, name, center, radius, mat, scale=(1, 1, 1), align=None):
    """Closed UV sphere. `align` rotates local +Z to the given direction before
    the non-uniform scale is applied along it (used for flattened discs)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=SPHERE_SEGMENTS, v_segments=SPHERE_RINGS, radius=radius)
    xf = Matrix.Diagonal((*scale, 1))
    if align is not None:
        rot = Vector((0, 0, 1)).rotation_difference(Vector(align).normalized()).to_matrix().to_4x4()
        xf = rot @ xf
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ xf, verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def tube_object(scene, name, points, radius, mat, ring=12):
    """Closed tube along a polyline with flat caps, built in bmesh."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rings = []
    pts = [Vector(p) for p in points]
    for i, p in enumerate(pts):
        tangent = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = tangent.cross(Vector((0, 1, 0))).normalized()
        up = side.cross(tangent).normalized()
        verts = []
        for k in range(ring):
            a = 2 * math.pi * k / ring
            verts.append(bm.verts.new(p + (side * math.cos(a) + up * math.sin(a)) * radius))
        rings.append(verts)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(ring):
            bm.faces.new((r0[k], r0[(k + 1) % ring], r1[(k + 1) % ring], r1[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    mesh.shade_smooth()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def surface_hit(tree, xf, x, z):
    """First body hit for a ray shot from the front (-Y) toward +Y, at build-space x, z."""
    p = xf @ Vector((x, 0, z))
    loc, normal, _, _ = tree.ray_cast(Vector((p.x, -5.0, p.z)), Vector((0, 1, 0)))
    assert loc is not None, f"face ray missed the body at x={x:.3f} z={z:.3f}"
    return loc, normal


def build_face(scene, body, xf, mats):
    s = xf.to_scale().x
    place = lambda p: xf @ Vector(p)
    parts = []

    for side in (1, -1):
        m = (lambda p: p) if side == 1 else mirror_x
        eye_dir = Vector(m(EYE_DIRECTION)).normalized()
        eye_c = place(m(EYE_BUMP_CENTER)) + eye_dir * EYE_OUTSET * s
        tag = "L" if side == 1 else "R"   # frog's own left is +X (it faces -Y)
        parts.append(sphere_object(scene, f"FrogEye_{tag}", eye_c, EYE_RADIUS * s, mats["eye"]))

        pupil_dir = Vector(m(PUPIL_DIRECTION)).normalized()
        pupil_c = eye_c + pupil_dir * (EYE_RADIUS * s - PUPIL_RADIUS * s * PUPIL_DEPTH_SCALE * 0.5)
        parts.append(sphere_object(scene, f"FrogPupil_{tag}", pupil_c, PUPIL_RADIUS * s, mats["pupil"],
                                   scale=(1, 1, PUPIL_DEPTH_SCALE), align=pupil_dir))

        hl_off = Vector(m(HIGHLIGHT_OFFSET))
        hl_off.x = -hl_off.x if side == 1 else hl_off.x
        hl_c = pupil_c + pupil_dir * (PUPIL_RADIUS * s * PUPIL_DEPTH_SCALE * 0.8) + hl_off * s
        parts.append(sphere_object(scene, f"FrogHighlight_{tag}", hl_c, HIGHLIGHT_RADIUS * s, mats["eye"]))

    tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())

    pts = []
    for i in range(MOUTH_SAMPLES + 1):
        t = -1 + 2 * i / MOUTH_SAMPLES
        x = t * MOUTH_HALF_WIDTH
        z = MOUTH_Z - MOUTH_SMILE_DEPTH * (1 - t * t)
        loc, normal = surface_hit(tree, xf, x, z)
        pts.append(loc - normal * MOUTH_EMBED * s)
    parts.append(tube_object(scene, "FrogMouth", pts, MOUTH_TUBE_RADIUS * s, mats["mouth"]))

    for side in (1, -1):
        tag = "L" if side == 1 else "R"
        loc, normal = surface_hit(tree, xf, side * NOSTRIL_X, NOSTRIL_Z)
        parts.append(sphere_object(scene, f"FrogNostril_{tag}", loc, NOSTRIL_RADIUS * s, mats["mouth"]))
        loc, normal = surface_hit(tree, xf, side * CHEEK_X, CHEEK_Z)
        parts.append(sphere_object(scene, f"FrogCheek_{tag}", loc - normal * CHEEK_EMBED * s,
                                   CHEEK_RADIUS * s, mats["cheek"],
                                   scale=(1, 1, CHEEK_DEPTH_SCALE), align=normal))

    loc, normal = surface_hit(tree, xf, 0, MOUTH_Z - MOUTH_SMILE_DEPTH)
    socket = bpy.data.objects.new(TONGUE_SOCKET_NAME, None)
    socket.empty_display_size = 50 * MM
    socket.location = loc - normal * TONGUE_SOCKET_INSET * s
    scene.collection.objects.link(socket)
    return parts, socket


def paint_belly(body, xf, mats):
    """Material split only; the test runs in build space like the other parameters."""
    mesh = body.data
    mesh.materials.append(mats["skin"])
    mesh.materials.append(mats["belly"])
    to_build = xf.inverted()
    for poly in mesh.polygons:
        c, n = to_build @ poly.center, poly.normal
        inside = (c.x / BELLY_RADIUS_X) ** 2 + ((c.z - BELLY_CENTER_Z) / BELLY_RADIUS_Z) ** 2 < 1
        poly.material_index = 1 if (inside and -n.y > BELLY_MIN_FRONT_NORMAL) else 0
    mesh.shade_smooth()


# --------------------------------------------------------------------------
# Census: measure first, look second
# --------------------------------------------------------------------------
def census(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold)
    flipped = sum(1 for e in bm.edges if e.is_manifold and not e.is_contiguous)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    degenerate = sum(1 for f in bm.faces if f.calc_area() <= DEGENERATE_AREA)
    tree = BVHTree.FromBMesh(bm, epsilon=BVH_EPSILON)
    selfhit = len(tree.overlap(tree))
    volume = bm.calc_volume(signed=True)

    # shell count: flood fill over edges
    seen, shells = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        shells += 1
        stack = [v]
        while stack:
            cur = stack.pop()
            if cur.index in seen:
                continue
            seen.add(cur.index)
            stack.extend(e.other_vert(cur) for e in cur.link_edges)
    bm.free()
    return dict(nonmanifold=nonmanifold, flipped=flipped, loose=loose, degenerate=degenerate,
                selfhit=selfhit, shells=shells, volume=volume)


def run_census(body, parts):
    print(f"{'object':<20}{'nonman':>7}{'flip':>6}{'loose':>6}{'degen':>6}{'self':>6}{'shell':>6}{'vol(L)':>10}")
    for obj in [body, *parts]:
        r = census(obj)
        print(f"{obj.name:<20}{r['nonmanifold']:>7}{r['flipped']:>6}{r['loose']:>6}{r['degenerate']:>6}"
              f"{r['selfhit']:>6}{r['shells']:>6}{r['volume'] * 1000:>10.3f}")
        assert (r["nonmanifold"], r["flipped"], r["loose"], r["degenerate"], r["selfhit"]) == (0, 0, 0, 0, 0), \
            f"{obj.name} failed census: {r}"
        assert r["shells"] == 1, f"{obj.name} has {r['shells']} shells"
        assert r["volume"] > 0, f"{obj.name} has inward normals (volume {r['volume']})"

    dims = body.dimensions
    print(f"body dimensions (mm): {dims.x / MM:.1f} x {dims.y / MM:.1f} x {dims.z / MM:.1f}")
    assert abs(dims.z - FROG_HEIGHT) < SIZE_TOLERANCE, f"height {dims.z} != {FROG_HEIGHT}"
    assert dims.x <= MAX_WIDTH, f"width {dims.x} exceeds {MAX_WIDTH}"
    zmin = min(v.co.z for v in body.data.vertices)
    assert abs(zmin) < SIZE_TOLERANCE, f"frog does not sit on the ground (zmin={zmin})"


def main():
    args = parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    scene = reset_scene()
    mats = {
        "skin": make_material("FrogSkin", COLOR_SKIN, SKIN_ROUGHNESS),
        "belly": make_material("FrogBelly", COLOR_BELLY, SKIN_ROUGHNESS),
        "eye": make_material("FrogEyeWhite", COLOR_EYE, 0.2),
        "pupil": make_material("FrogPupil", COLOR_PUPIL, 0.1),
        "mouth": make_material("FrogMouth", COLOR_MOUTH, 0.6),
        "cheek": make_material("FrogCheek", COLOR_CHEEK, 0.6),
    }

    body = build_body(scene)
    xf = normalize_height(body)
    paint_belly(body, xf, mats)
    parts, socket = build_face(scene, body, xf, mats)

    root = bpy.data.objects.new("Frog", None)
    scene.collection.objects.link(root)
    for obj in [body, *parts, socket]:
        obj.parent = root

    run_census(body, parts)

    bpy.context.preferences.filepaths.save_version = 0   # no frog.blend1 backups
    # Named operator exceptions: no data-API equivalent exists for these two.
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "frog.blend"), check_existing=False)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "frog.glb"), export_format='GLB',
                              export_yup=True, export_apply=True)
    print(f"wrote {out}/frog.glb and frog.blend")


if __name__ == "__main__":
    main()
