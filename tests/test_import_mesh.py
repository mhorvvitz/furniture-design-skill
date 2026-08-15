import struct
import import_mesh


def _write_two_boxes(path):
    """Two disjoint axis-aligned boxes, 12 triangles each, as binary STL."""
    def box(ox, oy, oz, sx, sy, sz):
        v = [(ox, oy, oz), (ox+sx, oy, oz), (ox+sx, oy+sy, oz), (ox, oy+sy, oz),
             (ox, oy, oz+sz), (ox+sx, oy, oz+sz), (ox+sx, oy+sy, oz+sz),
             (ox, oy+sy, oz+sz)]
        f = [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),
             (1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
        return [(v[a], v[b], v[c]) for a, b, c in f]

    tris = box(0, 0, 0, 10, 20, 30) + box(100, 0, 0, 5, 5, 5)
    with open(path, "wb") as fh:
        fh.write(b"\0" * 80)
        fh.write(struct.pack("<I", len(tris)))
        for t in tris:
            fh.write(struct.pack("<3f", 0, 0, 1))
            for p in t:
                fh.write(struct.pack("<3f", *p))
            fh.write(struct.pack("<H", 0))


def test_read_stl_returns_all_triangles(tmp_path):
    p = tmp_path / "two.stl"
    _write_two_boxes(str(p))
    tris = import_mesh.read_stl(str(p))
    assert len(tris) == 24


def test_components_separates_disjoint_solids(tmp_path):
    p = tmp_path / "two.stl"
    _write_two_boxes(str(p))
    tris = import_mesh.read_stl(str(p))
    comps = import_mesh.components(tris)
    assert len(comps) == 2
    assert sorted(len(c) for c in comps) == [12, 12]


def test_boxes_recover_exact_dimensions(tmp_path):
    p = tmp_path / "two.stl"
    _write_two_boxes(str(p))
    tris = import_mesh.read_stl(str(p))
    bs = import_mesh.boxes(tris, import_mesh.components(tris))
    dims = sorted(tuple(round(b[k+"1"] - b[k+"0"]) for k in "xyz") for b in bs)
    assert dims == [(5, 5, 5), (10, 20, 30)]


def test_boxes_flag_true_boxes(tmp_path):
    p = tmp_path / "two.stl"
    _write_two_boxes(str(p))
    tris = import_mesh.read_stl(str(p))
    bs = import_mesh.boxes(tris, import_mesh.components(tris))
    assert all(b["is_box"] for b in bs)


def test_to_spec_produces_carcass_shaped_output(tmp_path):
    p = tmp_path / "two.stl"
    _write_two_boxes(str(p))
    tris = import_mesh.read_stl(str(p))
    bs = import_mesh.boxes(tris, import_mesh.components(tris))
    spec = import_mesh.to_spec(bs, "Imported", scale=10.0)
    assert set(spec) >= {"name", "overall", "parts"}
    assert len(spec["parts"]) == 2
    for q in spec["parts"]:
        assert {"defn", "x", "y", "z", "sx", "sy", "sz"} <= set(q)
    # scale=10 turns cm into mm, and the default axis_map="xzy" maps the Z-up STL
    # frame onto Carcass's Y-up frame: spec x = stl x, spec y = stl z (height),
    # spec z = stl y (depth). So the 10x20x30 STL box becomes 100 wide, 300 tall,
    # 200 deep. Both axes are asserted so the mapping cannot silently transpose.
    assert max(q["sx"] for q in spec["parts"]) == 100
    assert max(q["sy"] for q in spec["parts"]) == 300
    assert max(q["sz"] for q in spec["parts"]) == 200


def test_to_spec_axis_map_is_overridable(tmp_path):
    """A mesh already in the Y-up frame is imported with axis_map='xyz'."""
    p = tmp_path / "two.stl"
    _write_two_boxes(str(p))
    tris = import_mesh.read_stl(str(p))
    bs = import_mesh.boxes(tris, import_mesh.components(tris))
    spec = import_mesh.to_spec(bs, "Imported", scale=10.0, axis_map="xyz")
    assert max(q["sy"] for q in spec["parts"]) == 200
    assert max(q["sz"] for q in spec["parts"]) == 300
