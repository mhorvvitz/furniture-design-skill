import assembly


def test_suggest_joint_overrides_covers_every_derived_pair(demo_spec):
    suggested = assembly.suggest_joint_overrides(demo_spec)
    assert suggested, "demo spec must produce at least one connection"

    derived = assembly.derive_connections(demo_spec, "frameless_kd")
    for c in derived:
        a = c["part_a"].rsplit("_", 1)[0]
        b = c["part_b"].rsplit("_", 1)[0]
        assert tuple(sorted((a, b))) in suggested


def test_suggest_joint_overrides_keys_are_sorted_tuples(demo_spec):
    for k in assembly.suggest_joint_overrides(demo_spec):
        assert isinstance(k, tuple) and len(k) == 2
        assert k[0] <= k[1]


def test_suggest_joint_overrides_values_are_the_style_default(demo_spec):
    vals = set(assembly.suggest_joint_overrides(demo_spec, "frameless_kd").values())
    assert vals == {"cam_and_dowel"}
