#!/usr/bin/env python3
"""import_mesh.py — read an EXISTING model back into a positioned-part spec.

The rest of this toolchain runs one way: parameters -> spec -> cut list, drawings,
render, SketchUp. This is the entry point for the other direction, which is the
normal case for built-in work: someone already has a model and you need its real
part sizes. The SketchUp MCP is build-only, the web share link has no export and
there is no .skp parser — but SketchUp Free does export STL, and an axis-aligned
box part shows up there as one connected component whose bounding box IS its cut
size. Nothing here is measured off an image.

Pipeline:
    read_stl(path)          -> triangles
    components(tris)        -> triangle-index groups (union-find on welded verts)
    boxes(tris, components) -> one bounding box per solid, flagged is_box
    to_spec(boxes, name)    -> a CANDIDATE positioned-part spec

`to_spec` output is a CANDIDATE, not a finished spec: every part is named
Part_001..., materials are unknown, and a component that is not a true box has
had its bounding box substituted for its real shape. Read the is_box column
before trusting a row, then rename and re-material by hand.

Scope: binary STL only — that is what SketchUp Free exports. ASCII STL, OBJ and
DAE are out of scope.
"""
import os
import struct
from collections import defaultdict

# SketchUp works Z-up; carcass.py works Y-up with front = Z = D. "xzy" reads as
# "spec takes the STL's x, then z, then y" -> spec y = stl z (height).
DEFAULT_AXIS_MAP = "xzy"


def read_stl(path):
    """Binary STL -> list of ((x,y,z), (x,y,z), (x,y,z)) float triangles."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 84:
        raise ValueError(f"{path}: too short to be a binary STL ({len(data)} bytes)")
    ntri = struct.unpack("<I", data[80:84])[0]
    expected = 84 + ntri * 50
    if len(data) != expected:
        # An ASCII STL also starts with "solid", so the size check is the reliable
        # discriminator rather than the header text.
        raise ValueError(
            f"{path}: not a binary STL — header claims {ntri} triangles "
            f"(= {expected} bytes) but the file is {len(data)} bytes. "
            f"ASCII STL is out of scope; re-export as binary.")
    raw = memoryview(data)
    tris = []
    for i in range(ntri):
        vals = struct.unpack_from("<12f", raw, 84 + i * 50)
        tris.append(tuple(tuple(vals[k * 3:k * 3 + 3]) for k in (1, 2, 3)))
    return tris


def components(tris, quant=1000):
    """Group triangle indices into connected solids.

    Vertices are quantised to 1/`quant` of a unit before comparison so that
    coordinates that differ only in float noise weld together; two triangles
    sharing any welded vertex are unioned. Returns a list of index lists.
    """
    parent = list(range(len(tris)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    vert_to_tris = defaultdict(list)
    for ti, t in enumerate(tris):
        for v in t:
            vert_to_tris[tuple(round(c * quant) for c in v)].append(ti)
    for tl in vert_to_tris.values():
        first = tl[0]
        for other in tl[1:]:
            union(first, other)

    groups = defaultdict(list)
    for ti in range(len(tris)):
        groups[find(ti)].append(ti)
    return list(groups.values())


def boxes(tris, comps, quant=1000):
    """One bounding box per component, largest volume first.

    `is_box` is True for a plain axis-aligned box: exactly 12 triangles over 8
    distinct corners. A False here means the bbox is an approximation of a more
    complex solid — check it before putting it on a cut list.
    """
    out = []
    for tl in comps:
        vs = [v for ti in tl for v in tris[ti]]
        b = {"x0": min(v[0] for v in vs), "x1": max(v[0] for v in vs),
             "y0": min(v[1] for v in vs), "y1": max(v[1] for v in vs),
             "z0": min(v[2] for v in vs), "z1": max(v[2] for v in vs),
             "ntri": len(tl),
             "nvert": len({tuple(round(c * quant) for c in v) for v in vs})}
        b["vol"] = ((b["x1"] - b["x0"]) * (b["y1"] - b["y0"]) * (b["z1"] - b["z0"]))
        b["is_box"] = (b["ntri"] == 12 and b["nvert"] == 8)
        out.append(b)
    out.sort(key=lambda c: -c["vol"])
    return out


def _axes(axis_map):
    if sorted(axis_map) != ["x", "y", "z"]:
        raise ValueError(
            f"axis_map must be a permutation of 'xyz', got {axis_map!r}")
    return tuple(axis_map)


def to_spec(boxes_, name, scale=1.0, axis_map=DEFAULT_AXIS_MAP, material="melamine"):
    """Bounding boxes -> a CANDIDATE positioned-part spec in Carcass.spec() shape.

    `scale` multiplies every coordinate (10.0 turns cm into mm). `axis_map` is a
    permutation of "xyz" naming which STL axis supplies spec x, y and z in turn;
    the default "xzy" converts SketchUp's Z-up export to this toolchain's Y-up
    frame. The model is translated so its minimum corner sits at the origin, and
    the discarded offset is recorded in `origin` so nothing is lost.

    Parts are named Part_001... in descending volume order. Rename them, set real
    materials, and check `is_box` before treating the result as buildable.
    """
    a0, a1, a2 = _axes(axis_map)
    parts = []
    for i, b in enumerate(boxes_, 1):
        lo = {ax: b[ax + "0"] * scale for ax in "xyz"}
        sz = {ax: (b[ax + "1"] - b[ax + "0"]) * scale for ax in "xyz"}
        parts.append({
            "defn": f"Part_{i:03d}", "name": f"Part_{i:03d}",
            "x": lo[a0], "y": lo[a1], "z": lo[a2],
            "sx": sz[a0], "sy": sz[a1], "sz": sz[a2],
            "material": material, "grain": "length",
            "note": "" if b["is_box"] else "NOT a plain box — bbox approximation",
            "is_box": b["is_box"], "ntri": b["ntri"], "nvert": b["nvert"],
        })

    if not parts:
        return dict(name=name, overall=dict(W=0, H=0, D=0),
                    origin=[0, 0, 0], parts=[])

    ox = min(p["x"] for p in parts)
    oy = min(p["y"] for p in parts)
    oz = min(p["z"] for p in parts)
    for p in parts:
        p["x"] -= ox
        p["y"] -= oy
        p["z"] -= oz

    return dict(
        name=name,
        overall=dict(W=max(p["x"] + p["sx"] for p in parts),
                     H=max(p["y"] + p["sy"] for p in parts),
                     D=max(p["z"] + p["sz"] for p in parts)),
        origin=[ox, oy, oz],
        parts=parts)


def main(path, scale=1.0, axis_map=DEFAULT_AXIS_MAP):
    tris = read_stl(path)
    comps = components(tris)
    bs = boxes(tris, comps)
    spec = to_spec(bs, os.path.splitext(os.path.basename(path))[0],
                   scale=scale, axis_map=axis_map)
    O = spec["overall"]
    print(f"{len(tris)} triangles -> {len(comps)} connected solid(s)")
    print(f"overall (spec frame, {axis_map}): "
          f"{O['W']:.1f} x {O['H']:.1f} x {O['D']:.1f}")
    print(f"origin offset discarded: "
          f"{spec['origin'][0]:.1f}, {spec['origin'][1]:.1f}, {spec['origin'][2]:.1f}")
    print(f"\n{'part':>10} {'box':>4} {'tri':>5} "
          f"{'sx':>9} {'sy':>9} {'sz':>9}   {'x':>9} {'y':>9} {'z':>9}")
    for p in spec["parts"]:
        print(f"{p['defn']:>10} {'Y' if p['is_box'] else '.':>4} {p['ntri']:>5} "
              f"{p['sx']:>9.1f} {p['sy']:>9.1f} {p['sz']:>9.1f}   "
              f"{p['x']:>9.1f} {p['y']:>9.1f} {p['z']:>9.1f}")
    n_odd = sum(1 for p in spec["parts"] if not p["is_box"])
    if n_odd:
        print(f"\n{n_odd} component(s) are NOT plain boxes — their rows are "
              f"bounding-box approximations, not cut sizes.")
    return spec


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if not a:
        raise SystemExit("usage: import_mesh.py <model.stl> [scale] [axis_map]")
    main(a[0], float(a[1]) if len(a) > 1 else 1.0,
         a[2] if len(a) > 2 else DEFAULT_AXIS_MAP)
