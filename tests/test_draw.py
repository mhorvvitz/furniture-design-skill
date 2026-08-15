import re

import pytest

import draw


def _rects(svg_text):
    """Every <rect> as (x, y, w, h) floats."""
    out = []
    for m in re.finditer(
            r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"',
            svg_text):
        out.append(tuple(float(g) for g in m.groups()))
    return out


def test_plan_draws_front_at_the_bottom(demo_spec, tmp_path):
    """A door (front, z=D) must land lower on the page than the back panel edge.
    Larger SVG y = lower on the page."""
    p = tmp_path / "plan.svg"
    draw.plan(demo_spec, str(p))
    svg = p.read_text(encoding="utf-8")

    assert "front at bottom" in svg

    D = demo_spec["overall"]["D"]
    front_parts = [q for q in demo_spec["parts"]
                   if q.get("kind") == "door"]
    assert front_parts
    # y of the deepest-z part must exceed the y of a z=0 part
    back_parts = [q for q in demo_spec["parts"] if q["z"] == 0]
    assert back_parts

    rects = _rects(svg)
    assert rects, "plan produced no rects"
    max_y = max(r[1] for r in rects)
    min_y = min(r[1] for r in rects)
    assert max_y > min_y

    # The discriminating assertion. In plan the SVG height of a rect is its part's
    # depth (sz) to scale, so the two shallowest rects are the 18mm-thick door
    # leaves — the frontmost parts in the piece. Being frontmost, they must be the
    # LOWEST rects on the page. Under the pre-fix projection they were the highest,
    # so this is what actually fails before the fix; `max_y > min_y` holds either
    # way and cannot catch the inversion.
    by_height = sorted(rects, key=lambda r: r[3])
    thinnest_ys = {r[1] for r in by_height[:len(front_parts)]}
    assert max_y in thinnest_ys, (
        "the lowest rect on the page is not a door leaf — the front of the piece "
        "is not being drawn at the bottom")


def test_plan_front_edge_is_below_back_edge(demo_spec, tmp_path):
    """Direct check of the projection: PZ must increase with z."""
    p = tmp_path / "plan2.svg"
    draw.plan(demo_spec, str(p))
    svg = p.read_text(encoding="utf-8")
    rects = _rects(svg)
    # The door spans z = D..D+18; the sides span z = 0..D. The door's top edge
    # (smallest y of the door rect) must be below the sides' top edge.
    ys = sorted(r[1] for r in rects)
    assert ys[-1] > ys[0] + 1


def test_elevation_rejects_unknown_wall(demo_spec, tmp_path):
    with pytest.raises(ValueError):
        draw.elevation(demo_spec, str(tmp_path / "x.svg"), "ceiling")


def test_elevation_left_puts_the_front_at_the_left_edge(demo_spec, tmp_path):
    """A door sits at z = D..D+18. Under the left-wall projection
    u = D - (z + sz), that maps to a small (near-zero, possibly negative) u,
    i.e. the left edge of the drawing."""
    D = demo_spec["overall"]["D"]
    door = next(p for p in demo_spec["parts"] if p.get("kind") == "door")
    u = D - (door["z"] + door["sz"])
    assert u <= 0 + 1e-9


def test_elevation_right_puts_the_front_at_the_right_edge(demo_spec):
    D = demo_spec["overall"]["D"]
    door = next(p for p in demo_spec["parts"] if p.get("kind") == "door")
    u = door["z"]
    assert u >= D - 1e-9


@pytest.mark.parametrize("wall", ["front", "back", "left", "right"])
def test_elevation_writes_a_file_for_every_wall(demo_spec, tmp_path, wall):
    out = tmp_path / f"{wall}.svg"
    draw.elevation(demo_spec, str(out), wall)
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("<svg")


def test_elevation_include_filter_reduces_part_count(demo_spec, tmp_path):
    all_svg = tmp_path / "all.svg"
    few_svg = tmp_path / "few.svg"
    draw.elevation(demo_spec, str(all_svg), "front")
    draw.elevation(demo_spec, str(few_svg), "front",
                   include=lambda p: p.get("kind") == "door")
    assert len(_rects(few_svg.read_text(encoding="utf-8"))) < \
           len(_rects(all_svg.read_text(encoding="utf-8")))
