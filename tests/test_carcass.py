import carcass


def test_validate_spec_clean_on_conforming_spec(demo_spec):
    assert carcass.validate_spec(demo_spec) == []


def test_validate_spec_flags_inverted_depth_axis(demo_spec):
    """Mirror every part in Z. Doors now sit at Z=0 instead of Z=D."""
    D = demo_spec["overall"]["D"]
    flipped = dict(demo_spec)
    flipped["parts"] = [
        dict(p, z=D - (p["z"] + p["sz"])) for p in demo_spec["parts"]
    ]
    warnings = carcass.validate_spec(flipped)
    assert warnings, "inverted depth axis must be flagged"
    assert any("depth axis" in w for w in warnings)


def test_validate_spec_silent_without_doors():
    """No front-facing parts means no evidence either way — stay quiet."""
    c = carcass.Carcass(600, 700, 300, t=18, name="Box")
    c.sides(); c.top(); c.bottom()
    assert carcass.validate_spec(c.spec()) == []
