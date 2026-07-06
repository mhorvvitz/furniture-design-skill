#!/usr/bin/env python3
"""
cutlist.py — turn a furniture spec (JSON) into a validated cut list.

Does the arithmetic the LLM should not do by hand:
  - validates every part (positive dims, known material, fits a real sheet)
  - expands quantities into a flat part list
  - totals area and edge-banding length per material
  - estimates sheet yield with a guillotine shelf heuristic (FFD by height)

It is intentionally honest: the sheet count is an ESTIMATE, not an optimised cut
plan. For production nesting use OpenCutList (SketchUp) or CutList Optimizer.

Exit code is non-zero if any part fails validation. Treat that as a stop.

Usage:
  python3 cutlist.py spec.json --format md
  python3 cutlist.py spec.json --format csv -o cutlist.csv
  python3 cutlist.py spec.json --format json
"""

import argparse
import json
import sys

# Banding vocabulary -> which edges, and how their length is derived from a part.
# L1/L2 are the long edges (each = part length); W1/W2 the short edges (= width).
BANDING_EDGES = {
    "l1": ("length",), "l2": ("length",),
    "w1": ("width",), "w2": ("width",),
    "long": ("length", "length"),
    "short": ("width", "width"),
    "all": ("length", "length", "width", "width"),
    "front": ("length",),   # a shelf/side front edge runs along its length
    "back": ("length",),
}


def fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def banding_length(part):
    """Linear mm of edge banding for one instance of a part."""
    total = 0.0
    unknown = []
    for tag in part.get("banding", []) or []:
        key = str(tag).strip().lower()
        if key in BANDING_EDGES:
            for edge in BANDING_EDGES[key]:
                total += part[edge]
        else:
            unknown.append(tag)
    return total, unknown


def orientations(part):
    """Allowed (along_sheet_length, along_sheet_width) footprints given grain.

    grain 'length' locks the part's length to the sheet's decor/length direction.
    grain 'width' locks its width to the sheet length. 'none' allows rotation.
    """
    L, W = part["length"], part["width"]
    grain = str(part.get("grain", "none")).lower()
    if grain == "length":
        return [(L, W)]
    if grain == "width":
        return [(W, L)]
    return [(L, W), (W, L)]


def fits_sheet(part, mat):
    """True if some allowed orientation fits within the usable sheet area."""
    trim = mat.get("trim", 0)
    usable_l = mat["sheet"][0] - 2 * trim
    usable_w = mat["sheet"][1] - 2 * trim
    for a, b in orientations(part):
        if a <= usable_l and b <= usable_w:
            return True
    return False


def validate(spec):
    errors, warnings = [], []
    mats = {m["id"]: m for m in spec.get("materials", [])}
    if not mats:
        errors.append("no materials defined")
    for m in spec.get("materials", []):
        if "sheet" not in m or len(m["sheet"]) != 2:
            errors.append(f"material '{m.get('id')}' missing a 2-value sheet size")
    overall = (spec.get("checks", {}) or {}).get("overall", {})
    max_overall = max(overall.values()) if overall else None

    for i, p in enumerate(spec.get("parts", [])):
        tag = p.get("name", f"part#{i}")
        for d in ("length", "width"):
            if d not in p or not isinstance(p[d], (int, float)) or p[d] <= 0:
                errors.append(f"{tag}: non-positive or missing '{d}'")
        if p.get("qty", 1) <= 0:
            errors.append(f"{tag}: qty must be positive")
        mid = p.get("material")
        if mid not in mats:
            errors.append(f"{tag}: unknown material '{mid}'")
            continue
        if "length" in p and "width" in p and p["length"] > 0 and p["width"] > 0:
            if not fits_sheet(p, mats[mid]):
                s = mats[mid]["sheet"]
                errors.append(
                    f"{tag}: {p['length']}x{p['width']} does not fit sheet "
                    f"{s[0]}x{s[1]} (grain={p.get('grain','none')}) — split it or change material")
            if max_overall and max(p["length"], p["width"]) > max_overall + 1:
                warnings.append(
                    f"{tag}: longest side {max(p['length'], p['width'])} exceeds "
                    f"the largest overall dimension {max_overall} — likely a wrong number")
        _, unknown = banding_length(p)
        if unknown:
            warnings.append(f"{tag}: unrecognised banding tags {unknown} (not counted)")
    return errors, warnings, mats


def shelf_estimate(parts, mat):
    """Guillotine shelf packing (FFD by shelf-height). Returns sheet count.

    Honest heuristic only. Rows run along the sheet length; shelves stack along
    the sheet width.
    """
    trim = mat.get("trim", 0)
    kerf = mat.get("kerf", 0)
    usable_l = mat["sheet"][0] - 2 * trim
    usable_w = mat["sheet"][1] - 2 * trim

    # expand instances, choose for each a footprint (prefer taller shelf height
    # minimised: pick orientation with smaller width-along-sheet to stack more)
    items = []
    for p in parts:
        for _ in range(int(p.get("qty", 1))):
            opts = orientations(p)
            # add kerf to footprint
            opts = [(a + kerf, b + kerf) for a, b in opts]
            # keep only those that fit; pick the one with smallest 'b' (shelf height)
            opts = [o for o in opts if o[0] <= usable_l and o[1] <= usable_w]
            if not opts:
                return None  # shouldn't happen post-validation
            items.append(min(opts, key=lambda o: o[1]))

    # FFD by shelf height (b) descending
    items.sort(key=lambda o: o[1], reverse=True)

    sheets = []  # each: {"shelves": [{"used_l","height"}], "used_w"}
    for a, b in items:
        placed = False
        for sh in sheets:
            for shelf in sh["shelves"]:
                if shelf["height"] >= b and shelf["used_l"] + a <= usable_l:
                    shelf["used_l"] += a
                    placed = True
                    break
            if placed:
                break
            # try a new shelf on this sheet
            if sh["used_w"] + b <= usable_w:
                sh["shelves"].append({"used_l": a, "height": b})
                sh["used_w"] += b
                placed = True
                break
        if not placed:
            sheets.append({"shelves": [{"used_l": a, "height": b}], "used_w": b})
    return len(sheets)


def dedupe_names(parts):
    """If the same part 'name' is used for two genuinely different sizes, this
    is a real risk on a shop floor (two differently-sized parts labeled
    identically). Auto-suffix (_A/_B/...) on collision, mirroring
    sketchup_emit.py's identical safeguard, so the cut list can never present
    two distinct sizes under one ambiguous label. Returns a NEW list; does not
    mutate the input.
    """
    geo_key = lambda p: (round(p["length"]), round(p["width"]), round(p.get("thickness", 0)))
    base_to_geokeys = {}
    for p in parts:
        base_to_geokeys.setdefault(p.get("name", ""), set()).add(geo_key(p))
    needs_suffix = {name for name, keys in base_to_geokeys.items() if len(keys) > 1}
    if not needs_suffix:
        return parts
    seen_per_base = {}
    out = []
    for p in parts:
        name = p.get("name", "")
        if name in needs_suffix:
            key = geo_key(p)
            slot = seen_per_base.setdefault(name, {})
            if key not in slot:
                slot[key] = chr(65 + len(slot))
            p = dict(p)
            p["name"] = f"{name}_{slot[key]}"
        out.append(p)
    return out


def summarise(spec, mats):
    rows = []
    per_mat = {}
    for p in spec.get("parts", []):
        qty = int(p.get("qty", 1))
        area = p["length"] * p["width"] / 1e6  # m^2 per piece
        band, _ = banding_length(p)
        rows.append({
            "name": p.get("name", ""),
            "qty": qty,
            "length": p["length"],
            "width": p["width"],
            "thickness": mats[p["material"]]["thickness"],
            "material": mats[p["material"]]["name"],
            "material_id": p["material"],
            "grain": p.get("grain", "none"),
            "banding": ", ".join(p.get("banding", []) or []),
            "notes": p.get("notes", ""),
        })
        d = per_mat.setdefault(p["material"], {"parts": 0, "area": 0.0, "band": 0.0})
        d["parts"] += qty
        d["area"] += area * qty
        d["band"] += band * qty

    for mid, d in per_mat.items():
        est = shelf_estimate([p for p in spec["parts"] if p["material"] == mid], mats[mid])
        d["sheets_est"] = est
        d["area"] = round(d["area"], 3)
        d["band_m"] = round(d["band"] / 1000.0, 2)
    rows = dedupe_names(rows)
    return rows, per_mat


def render_md(spec, rows, per_mat, mats, warnings):
    out = [f"# Cut list — {spec.get('project','(untitled)')}", "",
           f"Units: {spec.get('units','mm')}", ""]
    out.append("| Part | Qty | Length | Width | Thk | Material | Grain | Banding | Notes |")
    out.append("|---|---:|---:|---:|---:|---|---|---|---|")
    for r in rows:
        out.append(f"| {r['name']} | {r['qty']} | {r['length']} | {r['width']} | "
                   f"{r['thickness']} | {r['material']} | {r['grain']} | "
                   f"{r['banding']} | {r['notes']} |")
    out += ["", "## Material summary", ""]
    out.append("| Material | Parts | Area (m²) | Banding (m) | Sheets (est.) |")
    out.append("|---|---:|---:|---:|---:|")
    for mid, d in per_mat.items():
        out.append(f"| {mats[mid]['name']} | {d['parts']} | {d['area']} | "
                   f"{d['band_m']} | {d['sheets_est']} |")
    out += ["", "> Sheet count is a heuristic estimate, not an optimised cut plan. "
            "For production nesting use OpenCutList or CutList Optimizer."]
    if warnings:
        out += ["", "## Warnings", ""] + [f"- {w}" for w in warnings]
    return "\n".join(out)


def render_csv(rows):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["part", "qty", "length_mm", "width_mm", "thickness_mm",
                "material", "grain", "banding", "notes"])
    for r in rows:
        w.writerow([r["name"], r["qty"], r["length"], r["width"], r["thickness"],
                    r["material"], r["grain"], r["banding"], r["notes"]])
    return buf.getvalue()


def render_json(spec, rows, per_mat, warnings):
    return json.dumps({
        "project": spec.get("project"),
        "units": spec.get("units", "mm"),
        "parts": rows,
        "material_summary": per_mat,
        "warnings": warnings,
        "nesting_note": "Sheet count is a heuristic estimate. Use OpenCutList / "
                        "CutList Optimizer for a production cut plan.",
    }, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Generate a validated cut list from a spec JSON.")
    ap.add_argument("spec")
    ap.add_argument("--format", choices=["md", "csv", "json"], default="md")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    errors, warnings, mats = validate(spec)
    if errors:
        fail(f"{len(errors)} validation error(s) — cut list NOT produced:")
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    rows, per_mat = summarise(spec, mats)
    if args.format == "md":
        text = render_md(spec, rows, per_mat, mats, warnings)
    elif args.format == "csv":
        text = render_csv(rows)
    else:
        text = render_json(spec, rows, per_mat, warnings)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out}")
    else:
        print(text)

    if warnings and args.format != "md":
        for w in warnings:
            print(f"WARNING: {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
