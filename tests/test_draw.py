import re
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
