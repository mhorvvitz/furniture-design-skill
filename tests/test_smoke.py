def test_demo_spec_shape(demo_spec):
    assert demo_spec["overall"] == {"W": 800, "H": 1800, "D": 400}
    assert len(demo_spec["parts"]) > 5


def test_doors_sit_at_the_front(demo_spec):
    """Guards the convention the whole plan depends on: front = Z = D."""
    doors = [p for p in demo_spec["parts"] if p.get("kind") == "door"]
    assert doors, "fixture must contain doors"
    for d in doors:
        assert d["z"] >= demo_spec["overall"]["D"] - 1
