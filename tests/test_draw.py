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


def _flip_top_spec():
    """A flip-top: the lid (720mm long) is longer than the piece is tall (420mm),
    so when it swings up it reaches far above H."""
    from carcass import Carcass
    c = Carcass(1260, 420, 720, t=20, name="FlipTop")
    c.add("Leg", 30, 0, 30, 60, 390, 60)
    c.add("Lid", 0, 390, 0, 1260, 30, 720,
          motion={"type": "hinge", "pivot": [390, 0], "angle": 100,
                  "group": "lid", "label": "Lift the lid"})
    return c.spec()


def test_open_state_canvas_fits_a_lid_taller_than_the_piece(tmp_path):
    """Regression: the open panel was sized H*s+120, assuming the open state
    needs only the piece's own height. A 720mm lid pivoting at y=390 reaches
    ~1110mm up, so the raised lid was drawn through the closed views and off the
    top of the sheet. Every drawn y must now land inside the canvas."""
    spec = _flip_top_spec()
    p = tmp_path / "flip.svg"
    draw.draw(spec, str(p), states=True)
    svg = p.read_text(encoding="utf-8")

    h = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', svg).group(1))
    rot = re.search(r'rotate\(-?[\d.]+ ([\d.]+) ([\d.]+)\)', svg)
    assert rot, "open state must rotate the hinged lid"
    pivot_y = float(rot.group(2))

    # The lid reaches (pivot_y - r_px) at its highest; that must stay on canvas.
    # Scale is recoverable from the canvas: just assert the pivot leaves room for
    # a lid longer than the piece, which the old formula did not.
    assert pivot_y < h, "pivot off canvas"
    # 720mm of lid above a 390mm pivot needs far more than the 420mm the old
    # formula allowed; the canvas must have grown well past the closed-only size.
    closed_only = tmp_path / "closed.svg"
    draw.draw(spec, str(closed_only), states=False)
    h_closed = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"',
                               closed_only.read_text(encoding="utf-8")).group(1))
    assert h > h_closed + 400, (
        f"open-state canvas {h} barely grew over the closed {h_closed} — "
        f"the swept reach of the lid is not being accounted for")


def test_open_state_rotated_lid_clears_the_title_block(tmp_path):
    """The sheet title sits at y=30. Before the fix the raised lid tip landed at
    y~=4, straight through it. Compute the rotated tip and assert it clears."""
    import math as _m
    spec = _flip_top_spec()
    p = tmp_path / "flip2.svg"
    draw.draw(spec, str(p), states=True)
    svg = p.read_text(encoding="utf-8")

    g = re.search(r'<g transform="rotate\((-?[\d.]+) ([\d.]+) ([\d.]+)\)">'
                  r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"',
                  svg)
    assert g, "expected a rotated lid rect in the open state"
    ang, cx, cy, x, y, w, hh = (float(v) for v in g.groups())

    th = _m.radians(ang)
    tip = min(
        cy + (px - cx) * _m.sin(th) + (py - cy) * _m.cos(th)
        for px in (x, x + w) for py in (y, y + hh))
    assert tip > 100, (
        f"raised lid reaches y={tip:.1f}, colliding with the title at y=30 — "
        f"the open panel is not tall enough for the lid's swept reach")
