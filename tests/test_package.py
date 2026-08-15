import package


def test_regenerate_calls_extra_outputs(demo_spec, tmp_path):
    called = {}

    def emitter(spec, outdir):
        called["hit"] = True
        (tmp_path / "extra.txt").write_text("ok", encoding="utf-8")
        return ["extra.txt"]

    class Mod:
        project = "Demo"
        rev = None
        style = "frameless_kd"
        banding = None
        notes = None
        joint_overrides = None
        extra_outputs = [emitter]

    written = package.regenerate(Mod(), demo_spec, str(tmp_path), ("views",))
    assert called.get("hit")
    assert "extra.txt" in written


def test_regenerate_emits_requested_wall_elevations(demo_spec, tmp_path):
    class Mod:
        project = "Demo"
        rev = None
        style = "frameless_kd"
        banding = None
        notes = None
        joint_overrides = None
        elevation_walls = ["left", "right"]

    written = package.regenerate(Mod(), demo_spec, str(tmp_path), ("views",))
    assert "elev_left.svg" in written
    assert "elev_right.svg" in written
    assert (tmp_path / "elev_left.svg").exists()
