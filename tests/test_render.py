import render


def test_render_emits_group_toggles(demo_spec, tmp_path):
    out = tmp_path / "r.html"
    render.render(demo_spec, str(out))
    html = out.read_text(encoding="utf-8")
    assert 'id="vw"' in html, "view preset bar missing"
    for v in ("iso", "front", "left", "right", "top"):
        assert f'data-v="{v}"' in html


def test_render_declares_views_after_orbit_state(demo_spec, tmp_path):
    """Regression: VIEWS referenced AZ0 before its `const` was initialised,
    which threw at load and silently killed lighting, orbit and the render loop."""
    out = tmp_path / "r2.html"
    render.render(demo_spec, str(out))
    html = out.read_text(encoding="utf-8")
    assert html.index("let az=") < html.index("const VIEWS")


def test_render_tags_every_part_with_a_group(demo_spec, tmp_path):
    """Each part carries a `g` field so the JS can hide a whole run at once."""
    out = tmp_path / "r3.html"
    render.render(demo_spec, str(out))
    html = out.read_text(encoding="utf-8")
    for label in ("Carcass", "Shelves", "Fronts", "Rods"):
        assert f'"g": "{label}"' in html or f'"g":"{label}"' in html
        assert f">{label}<" in html, f"no visibility checkbox for {label}"


def test_render_group_checkboxes_are_wired_to_applyvis(demo_spec, tmp_path):
    out = tmp_path / "r4.html"
    render.render(demo_spec, str(out))
    html = out.read_text(encoding="utf-8")
    assert "function applyVis()" in html
    assert "applyVis);" in html, "checkboxes not bound to applyVis"
