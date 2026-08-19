"""Regressions for the two emit-pipeline bugs reported in issue #2.

Both were found on a real project only after ten revisions, because the
workarounds looked like normal steps.
"""
import carcass
import package
import pytest


def _mod(**kw):
    class Mod:
        project = "Demo"
        rev = None
        style = "frameless_kd"
        banding = None
        notes = None
        joint_overrides = None
    m = Mod()
    for k, v in kw.items():
        setattr(m, k, v)
    return m


# --------------------------------------------------------------- P0 #1
def test_replaces_overrides_a_builtin_step(demo_spec, tmp_path):
    """A project's own render must run INSTEAD of the stock one, not be
    overwritten by it."""
    marker = "<!--project-render-->"

    def my_render(spec, outdir):
        import os
        with open(os.path.join(outdir, "render.html"), "w", encoding="utf-8") as f:
            f.write(marker)
        return ["render.html (project)"]

    written = package.regenerate(_mod(replaces={"render": my_render}),
                                 demo_spec, str(tmp_path), ("render",))
    assert (tmp_path / "render.html").read_text(encoding="utf-8") == marker
    assert "render.html (project)" in written


def test_without_replaces_the_builtin_render_still_runs(demo_spec, tmp_path):
    package.regenerate(_mod(), demo_spec, str(tmp_path), ("render",))
    html = (tmp_path / "render.html").read_text(encoding="utf-8")
    assert "THREE" in html or "three" in html


def test_skip_drops_a_step(demo_spec, tmp_path):
    written = package.regenerate(_mod(), demo_spec, str(tmp_path),
                                 ("views", "render"), skip=("render",))
    assert (tmp_path / "plan.svg").exists()
    assert not (tmp_path / "render.html").exists()
    assert not any("render" in w for w in written)


# --------------------------------------------------------------- P0 #2
def test_packet_includes_docs_a_project_generated(demo_spec, tmp_path):
    """extra_outputs must be able to contribute to the packet — it is the
    document the carpenter actually holds."""
    def emitter(spec, outdir):
        import os
        with open(os.path.join(outdir, "drawers.md"), "w", encoding="utf-8") as f:
            f.write("# Drawer boxes\n\nUNIQUE-DRAWER-MARKER\n")
        return ["drawers.md"]

    package.regenerate(_mod(extra_outputs=[emitter],
                            packet_docs=["cutlist.md", "assembly.md", "drawers.md"]),
                       demo_spec, str(tmp_path), ("cutlist", "views", "assembly", "packet"))
    html = (tmp_path / "packet.html").read_text(encoding="utf-8")
    assert "UNIQUE-DRAWER-MARKER" in html


def test_packet_picks_up_wall_elevations_automatically(demo_spec, tmp_path):
    package.regenerate(_mod(elevation_walls=["left"]), demo_spec, str(tmp_path),
                       ("cutlist", "views", "assembly", "packet"))
    html = (tmp_path / "packet.html").read_text(encoding="utf-8")
    assert "elev_left" in html


# --------------------------------------------------------------- P1 #5
def test_stale_banding_or_notes_key_is_reported(demo_spec):
    warns = package.check_mod_keys(
        _mod(banding={"Side": ["front"], "Valance": ["front"]},
             notes={"NoSuchPart": "hi"}),
        demo_spec)
    joined = " ".join(warns)
    assert "Valance" in joined
    assert "NoSuchPart" in joined
    assert "Side" not in joined


# --------------------------------------------------------------- P1 #6
def test_thickness_not_in_the_material_catalogue_warns():
    c = carcass.Carcass(600, 700, 300, t=19, material="melamine", name="Odd")
    c.sides()
    warns = carcass.check_material_thickness(c.spec())
    assert warns and "19" in " ".join(warns)


def test_catalogued_thickness_is_silent():
    c = carcass.Carcass(600, 700, 300, t=18, material="melamine", name="Fine")
    c.sides()
    assert carcass.check_material_thickness(c.spec()) == []


def test_unknown_material_does_not_crash_the_check():
    c = carcass.Carcass(600, 700, 300, t=18, material="unobtainium", name="X")
    c.sides()
    assert carcass.check_material_thickness(c.spec()) == []
