#!/usr/bin/env python3
"""package.py — one command to regenerate the whole carpenter package from a spec.

Every small design change (drawer proportion, overhang, material swap, a new
stile) invalidates every deliverable at once. Re-running five emitters by hand —
and rebuilding throwaway per-project glue each time — is the largest avoidable
cost in a project. This is the regenerator: point it at the project's spec module
and it rebuilds the cut list (md/csv/xlsx/json), the 2D views, the 3D render, the
assembly plan, and the packet PDF — after running check_overlaps as a hard gate.

The project spec module (a normal .py file kept beside the piece) must expose the
positioned-part spec. It may do so as either:
  * `spec` — the dict returned by Carcass.spec(), or
  * `build()` — a function returning that dict.
Optional module attributes tune the emit; all have safe defaults:
  project, rev, style, banding, notes, joint_overrides, expected_overlaps, legend.

Usage:
  python3 package.py coffee_table_spec.py --out output/
  python3 package.py coffee_table_spec.py --out output/ --only cutlist,views
  python3 package.py coffee_table_spec.py --out output/ --force   # ignore overlap gate

Keep your per-project spec module in the repo next to the piece — it is a project
file, not scratch. Do not delete it between turns; it is what makes regeneration
one command instead of a rebuild.
"""
import argparse
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import carcass  # noqa: E402
import draw  # noqa: E402
import render  # noqa: E402
import cutlist  # noqa: E402
import assembly  # noqa: E402
import packet  # noqa: E402

ALL_STEPS = ("cutlist", "views", "render", "assembly", "packet")


def load_spec_module(path):
    spec_name = os.path.splitext(os.path.basename(path))[0]
    spec_import = importlib.util.spec_from_file_location(spec_name, path)
    mod = importlib.util.module_from_spec(spec_import)
    # let the project module import carcass etc. from scripts/
    sys.modules[spec_name] = mod
    spec_import.loader.exec_module(mod)
    if hasattr(mod, "spec"):
        spec = mod.spec() if callable(mod.spec) else mod.spec
    elif hasattr(mod, "build"):
        spec = mod.build()
    else:
        raise SystemExit(f"{path}: module must expose `spec` (dict or callable) or `build()`")
    return mod, spec


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(int(c) for c in rgb)


def build_legend(spec):
    """Material legend from the parts actually in the spec, coloured from
    materials.json (fixtures get the muted fixture tone)."""
    seen = []
    for p in spec["parts"]:
        mid = p.get("material")
        if mid and mid not in seen:
            seen.append(mid)
    legend = []
    for mid in seen:
        if any(p.get("material") == mid and p.get("kind") == "fixture" for p in spec["parts"]):
            rgb = carcass.fixture_default_color()
        else:
            rgb = carcass.material_color(mid, default=(210, 200, 175))
        legend.append((mid, _rgb_to_hex(rgb)))
    return legend


def overlap_gate(spec, expected, force):
    flags = carcass.check_overlaps(spec)
    facade = carcass.check_facade_coverage(spec)
    for w in flags:
        print(f"  overlap: {w}", file=sys.stderr)
    for w in facade:
        print(f"  facade:  {w}", file=sys.stderr)
    if len(flags) > expected and not force:
        raise SystemExit(
            f"ABORT: {len(flags)} overlap flag(s) but only {expected} expected "
            f"(rebate/groove joints). Review each above, then set "
            f"`expected_overlaps={len(flags)}` in the spec module if all are "
            f"accounted for, or pass --force. Unaccounted overlaps block regeneration.")
    if facade:
        print(f"  ({len(facade)} facade-coverage warning(s) — review, not blocking)",
              file=sys.stderr)


def has_motion(spec):
    return any(p.get("motion") for p in spec["parts"])


def regenerate(mod, spec, outdir, steps):
    os.makedirs(outdir, exist_ok=True)
    project = getattr(mod, "project", spec.get("name", "(untitled)"))
    rev = getattr(mod, "rev", None)
    style = getattr(mod, "style", "frameless_kd")
    banding = getattr(mod, "banding", None)
    notes = getattr(mod, "notes", None)
    joint_overrides = getattr(mod, "joint_overrides", None)
    legend = getattr(mod, "legend", None) or build_legend(spec)
    O = spec.get("overall", {})
    overall = f"{O.get('W')}x{O.get('H')}x{O.get('D')}" if O else None

    def outp(name):
        return os.path.join(outdir, name)

    written = []

    # --- cut list (all formats) ---
    cl_md = outp("cutlist.md")
    if "cutlist" in steps or "packet" in steps:
        cl = carcass.cutlist_spec(spec, banding=banding, notes=notes, project=project)
        errors, warnings, mats = cutlist.validate(cl)
        if errors:
            for e in errors:
                print(f"  cutlist ERROR: {e}", file=sys.stderr)
            raise SystemExit("ABORT: cut list failed validation — fix the spec.")
        rows, per_mat = cutlist.summarise(cl, mats)
        import json
        with open(outp("cutlist.json"), "w", encoding="utf-8") as f:
            f.write(cutlist.render_json(cl, rows, per_mat, warnings))
        with open(cl_md, "w", encoding="utf-8") as f:
            f.write(cutlist.render_md(cl, rows, per_mat, mats, warnings))
        with open(outp("cutlist.csv"), "w", encoding="utf-8") as f:
            f.write(cutlist.render_csv(rows))
        try:
            cutlist.write_xlsx(cl, rows, per_mat, mats, warnings, outp("cutlist.xlsx"))
        except SystemExit:
            print("  (xlsx skipped — openpyxl not installed)", file=sys.stderr)
        if "cutlist" in steps:
            written += ["cutlist.md", "cutlist.csv", "cutlist.json", "cutlist.xlsx"]

    # --- 2D views ---
    plan_svg, front_svg = outp("plan.svg"), outp("front.svg")
    if "views" in steps or "packet" in steps:
        draw.plan(spec, plan_svg)
        draw.draw(spec, front_svg, states=has_motion(spec))
        if "views" in steps:
            written += ["plan.svg", "front.svg"]

    # --- 3D render ---
    if "render" in steps:
        render.render(spec, outp("render.html"))
        written += ["render.html"]

    # --- assembly plan ---
    asm_md = outp("assembly.md")
    if "assembly" in steps or "packet" in steps:
        assembly.write_assembly_plan(spec, asm_md, style=style, joint_overrides=joint_overrides)
        if "assembly" in steps:
            written += ["assembly.md"]

    # --- packet PDF (depends on views + cutlist + assembly, regenerated above) ---
    if "packet" in steps:
        import datetime
        html = packet.build_html(
            project, project, overall, spec.get("units", "mm"), rev,
            datetime.date.today().isoformat(),
            [plan_svg, front_svg], [cl_md, asm_md], legend)
        pdf_path = outp("packet.pdf")
        html_path = outp("packet.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        browser = packet.find_browser()
        if browser and packet.print_pdf(browser, html_path, pdf_path)[0]:
            written += ["packet.pdf", "packet.html"]
        else:
            print("  (packet PDF skipped — no browser; packet.html is the deliverable)",
                  file=sys.stderr)
            written += ["packet.html"]

    return written


def main():
    ap = argparse.ArgumentParser(description="Regenerate the full carpenter package from a spec module.")
    ap.add_argument("spec_module", help="path to the project's <piece>_spec.py")
    ap.add_argument("--out", default="output", help="output directory")
    ap.add_argument("--only", default=None,
                    help=f"comma-separated subset of {','.join(ALL_STEPS)} (default: all)")
    ap.add_argument("--force", action="store_true", help="ignore the overlap gate")
    args = ap.parse_args()

    if args.only:
        steps = tuple(s.strip() for s in args.only.split(",") if s.strip())
        bad = [s for s in steps if s not in ALL_STEPS]
        if bad:
            raise SystemExit(f"unknown step(s) {bad}; valid: {', '.join(ALL_STEPS)}")
    else:
        steps = ALL_STEPS

    mod, spec = load_spec_module(args.spec_module)
    expected = getattr(mod, "expected_overlaps", 0)
    overlap_gate(spec, expected, args.force)

    written = regenerate(mod, spec, args.out, steps)
    print(f"regenerated {len(written)} file(s) in {args.out}/:")
    for w in written:
        print(f"  - {w}")


if __name__ == "__main__":
    main()
