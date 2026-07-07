# Deliverables

The carpenter package. Produce it in the **language of the conversation**. Three
artifacts: a cut list / BOM, dimensioned shop drawings, and a hardware schedule.
Reconcile every number through the consistency checks before exporting.

## 1 — Cut list / BOM

The cut list is generated from a structured spec by `scripts/cutlist.py`, so the
arithmetic, sheet-fit validation, edge-banding totals, and sheet-yield estimate
are computed deterministically rather than reasoned out. Reason about the design;
let the script do the counting.

**Where this JSON comes from**: if the piece was built with `carcass.py` (the
default), derive the `parts` array with `carcass.cutlist_parts(spec)` — it
collapses the positioned spec into this schema and auto-disambiguates any part
name reused across different sizes. Never hand-transcribe dimensions from the
positioned spec into this file; that re-introduces exactly the arithmetic errors
the pipeline exists to prevent. Hand-write this JSON only for out-of-envelope
pieces that have no positioned spec.

### Spec JSON the script consumes

```json
{
  "project": "Living-room wall unit",
  "units": "mm",
  "materials": [
    {
      "id": "mel18",
      "name": "Melamine 18mm white / מלמין לבן",
      "thickness": 18,
      "sheet": [2800, 2070],
      "kerf": 4,
      "trim": 10
    },
    {
      "id": "back4",
      "name": "Hardboard back 4mm",
      "thickness": 4,
      "sheet": [2440, 1220],
      "kerf": 3,
      "trim": 10
    }
  ],
  "parts": [
    {
      "name": "Side / צד",
      "qty": 2,
      "length": 2000,
      "width": 580,
      "material": "mel18",
      "grain": "length",
      "banding": ["front"],
      "notes": "system-32 holes both rows"
    },
    {
      "name": "Top+Bottom / מדף עליון+תחתון",
      "qty": 2,
      "length": 964,
      "width": 580,
      "material": "mel18",
      "grain": "length",
      "banding": ["front"]
    }
  ],
  "checks": {
    "overall": { "width": 1000, "height": 2000, "depth": 600 }
  }
}
```

Field notes:
- `grain`: `"length"`, `"width"`, or `"none"`. Controls whether the part may be
  rotated for nesting. Woodgrain decor parts must lock orientation.
- `banding`: edge tags from a controlled vocabulary so the script can total the
  linear metres. Valid tags: `L1`/`L2` (a long edge, length = part length),
  `W1`/`W2` (a short edge, = part width), `long` (both long edges), `short` (both
  short), `all` (full perimeter), and aliases `front`/`back` (one long edge each).
  Unknown tags are warned about and counted as zero — keep to the vocabulary.
- `kerf`: saw-blade width to allow between parts. `trim`: edge margin discarded
  from each sheet.
- `checks.overall`: optional; lets the script and you sanity-check that parts are
  consistent with the stated envelope.

### Running it

```bash
python3 scripts/cutlist.py spec.json --format md      # human table to stdout
python3 scripts/cutlist.py spec.json --format csv -o cutlist.csv
python3 scripts/cutlist.py spec.json --format json    # machine-readable, for the xlsx step
```

The script **exits non-zero and prints errors** if any part fails validation
(non-positive dimension, part larger than its sheet, unknown material). Treat a
non-zero exit as a stop: fix the spec, do not ship.

Then build the spreadsheet with the **`xlsx` skill** from the script's output
(one row per part, grouped by material, with a totals/summary block and the
sheet-yield estimate). Do not hand-roll spreadsheet mechanics.

### Honesty about nesting

The sheet-yield number is a **heuristic estimate** (area + a guillotine-shelf
packing), not an optimised cut plan. State this. For a production nesting diagram,
point the user to **OpenCutList** (SketchUp) or **CutList Optimizer** — that is
the industry-standard tool for the job and this skill does not try to beat it.

## 2 — Dimensioned shop drawings (PDF)

Render with the **`pdf` skill**. The package contains:

- **Title block**: project name, date, "Units: mm", overall dimensions, material
  legend, revision/version.
- **Plan view** (to scale, dimensioned).
- **Front elevation** (to scale, dimensioned; fronts, gaps/reveals, handles).
- **Side elevation / section** showing depth, shelves, back capture, panel
  thickness.
- **Joinery detail callouts**: enlarged views of the key connections (e.g.
  cam-and-dowel positions, dado depth, hinge cup location) with dimensions.
- **Exploded / assembly view**: parts pulled apart along their normals so the
  carpenter sees order of assembly and connector placement.
- **Hardware schedule** (can live on the drawing or as the separate artifact).
- **Part labels** matching the cut list exactly.

Conventions: consistent scale per view (state it), dimension chains that sum to
the overall, mm throughout, grain arrows on visible woodgrain parts, and a note of
which edges are banded.

## 3 — Hardware schedule

Itemised list: hinge type + count, runner type + count + size, shelf pins,
legs/feet, handles, KD connectors, wall fixings, screws. Quantities derived from
the design (e.g. 2 hinges per door up to ~900 mm height, 3 above). Reference
standard parts; mark anything whose availability the supplier must confirm.

## Pre-export consistency checklist

Run before producing any final file. The script covers the geometric ones; the
rest are judgement.

1. **Parts vs overall.** Across each axis, the relevant parts + gaps should equal
   the stated envelope (this summation is human judgement). The script does a
   coarse sanity check — it flags any part whose longest side exceeds the largest
   overall dimension, a common sign of a transposed or wrong number.
2. **No part exceeds its sheet** (script-enforced).
3. **No non-positive or implausible dimension** (script-enforced).
4. **Thickness math applied**: internal dims = external − 2t where they should be;
   no nominal envelope number reused as a cut size.
5. **Openings fit fronts**: door/drawer faces + reveals match their openings; no
   negative reveal, no collision between adjacent fronts.
6. **Grain direction** set on every visible woodgrain part.
7. **Edge banding** specified on every visible edge.
8. **Hardware fits**: drawer-box clearances match the chosen runner; hinge overlay
   matches the front layout; shelf pins land on the 32 mm grid if System 32.
9. **Built-in allowances present**: scribe on wall-meeting sides, filler where the
   run does not divide evenly, toe-kick referenced to the smallest measured
   height.
10. **Assumed numbers resolved**: every `assumed` value in the spec has been
    confirmed or flagged to the user.
11. **`check_overlaps()` clean**: run it on the positioned spec; every flag must
    be explicitly accounted for — either a rebate/groove joint the box model
    can't represent (inset backs, drawer bottoms — expected), or a real clash
    that must be fixed. An unaccounted flag blocks export. Hard rule 12.

If any check fails, fix the spec and regenerate the cut list and drawings from it.
Never reconcile by editing a single output by hand — the spec is the source of
truth.
