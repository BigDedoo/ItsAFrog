"""Cut the baked-in ground bases off the plant GLBs so they can be stacked and overlapped naturally.

Meshy modelled some plants standing on a base (a soil mound, disc or plate). For each GLB in
BASE_CUTS this drops every triangle whose centre lies below the base's top (a fraction of the
model's height, measured from the upward-facing surface the base's top makes), and flattens what
is left onto that plane so the plant meets the ground cleanly. The cut is recorded in the GLB
(asset.extras.frogdemo_base_cut), so running it again changes nothing.

fetch_assets.py runs this after downloading; it also runs on its own with any Python 3:

    python Tools/FrogDemo/strip_bases.py
"""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "ExternalAssets", "stylized-assets")

# GLB path under stylized-assets -> height fraction of the top of its base
BASE_CUTS = {
    "bush.glb": 0.125,
    "mushroom.glb": 0.112,
    "library/grass_tuft.glb": 0.115,
    "library/fern.glb": 0.19,
}

COMPONENT = {5126: ("f", 4), 5125: ("I", 4), 5123: ("H", 2), 5121: ("B", 1)}


def read_glb(path):
    data = open(path, "rb").read()
    json_len = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + json_len])
    off = 20 + json_len
    bin_len = struct.unpack_from("<I", data, off)[0]
    return gltf, bytearray(data[off + 8:off + 8 + bin_len])


def write_glb(path, gltf, binary):
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    binary = bytes(binary) + b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path + ".part", "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(binary), 0x004E4942) + binary)
    os.replace(path + ".part", path)


def view(gltf, index):
    """(offset, stride, format, item size) of an accessor's elements in the BIN chunk."""
    a = gltf["accessors"][index]
    bv = gltf["bufferViews"][a["bufferView"]]
    fmt, size = COMPONENT[a["componentType"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
    return bv.get("byteOffset", 0) + a.get("byteOffset", 0), bv.get("byteStride", size * n), fmt * n, size * n


def strip(path, cut):
    gltf, binary = read_glb(path)
    extras = gltf.setdefault("asset", {}).setdefault("extras", {})
    if "frogdemo_base_cut" in extras:
        return False
    identity = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
    for node in gltf.get("nodes", []):
        if node.get("matrix", identity) != identity or "rotation" in node or "scale" in node:
            raise RuntimeError(f"{path}: node rotation/scale isn't handled; the cut assumes glTF +Y is up")

    prims = [p for m in gltf["meshes"] for p in m["primitives"]]
    heights = []
    for p in prims:
        off, stride, fmt, _ = view(gltf, p["attributes"]["POSITION"])
        count = gltf["accessors"][p["attributes"]["POSITION"]]["count"]
        heights += [struct.unpack_from(fmt, binary, off + i * stride)[1] for i in range(count)]
    y0, y1 = min(heights), max(heights)
    cut_y = y0 + cut * (y1 - y0)

    for p in prims:
        pa = p["attributes"]["POSITION"]
        poff, pstride, pfmt, _ = view(gltf, pa)
        pos = [list(struct.unpack_from(pfmt, binary, poff + i * pstride)) for i in range(gltf["accessors"][pa]["count"])]
        ioff, istride, ifmt, _ = view(gltf, p["indices"])
        idx = [struct.unpack_from(ifmt, binary, ioff + i * istride)[0] for i in range(gltf["accessors"][p["indices"]]["count"])]

        kept = []
        for t in range(0, len(idx), 3):
            tri = idx[t:t + 3]
            if sum(pos[v][1] for v in tri) / 3 >= cut_y:
                kept += tri
        used = set(kept)
        for v in used:
            if pos[v][1] < cut_y:
                pos[v][1] = cut_y
        for v in used:
            struct.pack_into(pfmt, binary, poff + v * pstride, *pos[v])
        acc = gltf["accessors"][pa]
        acc["min"] = [min(pos[v][k] for v in used) for k in range(3)]
        acc["max"] = [max(pos[v][k] for v in used) for k in range(3)]

        # New index data at the end of the BIN chunk, same component type as before.
        binary += b"\0" * (-len(binary) % 4)
        iacc = gltf["accessors"][p["indices"]]
        fmt, size = COMPONENT[iacc["componentType"]]
        data = struct.pack(f"<{len(kept)}{fmt}", *kept)
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(data), "target": 34963})
        binary += data
        iacc.update(bufferView=len(gltf["bufferViews"]) - 1, byteOffset=0, count=len(kept))
        iacc.pop("min", None)
        iacc.pop("max", None)
        print(f"  {os.path.basename(path)}: kept {len(kept) // 3} of {len(idx) // 3} triangles above {cut:.1%} of the height")

    gltf["buffers"][0]["byteLength"] = len(binary) + (-len(binary) % 4)
    extras["frogdemo_base_cut"] = cut
    write_glb(path, gltf, binary)
    return True


def main(out=OUT):
    for rel, cut in BASE_CUTS.items():
        path = os.path.join(out, rel)
        if not os.path.exists(path):
            print("  missing", rel)
        elif not strip(path, cut):
            print(f"  {rel}: base already cut")


if __name__ == "__main__":
    main()
