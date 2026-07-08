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
default), build the **whole** document with `carcass.cutlist_spec(spec, banding,
notes)` — it produces the materials catalog *and* the parts array in one call.
Critically, it **auto-splits the materials catalog by `(material_id, thickness)`**,
so one nominal material used at several thicknesses (white-oak veneer at 30 and 20,
ply at 20 and 15, solid oak at 60 and 20) becomes distinct catalog entries with the
right sheet/kerf/trim pulled from `assets/materials.json` — the case that has no
compliant hand-free path otherwise. Non-cut parts (`kind="rod"`/`"fixture"`) are
excluded automatically. You supply only the judgement calls:

```python
from carcass import cutlist_spec
cl = cutlist_spec(spec,
                  banding={"Top": ["front"], "Side": ["front"]},   # by defn name
                  notes={"Side": "system-32 holes both rows"})
json.dump(cl, open("cutlist_spec.json", "w"), ensure_ascii=False, indent=2)
```

`banding`/`notes` are dicts keyed by part `defn` name — the LLM never does the
arithmetic. `cutlist_parts()` is the lower-level helper (bare part rows, no
materials catalog); prefer `cutlist_spec()` for anything you will actually validate
and ship. Never hand-transcribe dimensions from the positioned spec into this file;
that re-introduces exactly the arithmetic errors the pipeline exists to prevent.
Hand-write this JSON only for out-of-envelope pieces that have no positioned spec.

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
python3 scripts/cutlist.py spec.json --format md              # human table to stdout
python3 scripts/cutlist.py spec.json --format csv -o cutlist.csv
python3 scripts/cutlist.py spec.json --format json            # machine-readable
python3 scripts/cutlist.py spec.json --format xlsx -o cutlist.xlsx   # spreadsheet
```

The script **exits non-zero and prints errors** if any part fails validation
(non-positive dimension, part larger than its sheet, unknown material). Treat a
non-zero exit as a stop: fix the spec, do not ship.

The **spreadsheet is built by the script itself** — `--format xlsx` (openpyxl:
one part table with a material column, a material-summary block, and the sheet
estimate; it prints an install hint and falls back to `--format csv` if openpyxl
is missing). Do not hand-roll spreadsheet mechanics, and do not reach for a
separate `xlsx` skill — it does not exist in this environment; this is the path.

### Honesty about nesting

The sheet-yield number is a **heuristic estimate** (area + a guillotine-shelf
packing), not an optimised cut plan. State this. For a production nesting diagram,
point the user to **OpenCutList** (SketchUp) or **CutList Optimizer** — that is
the industry-standard tool for the job and this skill does not try to beat it.

## 2 — Dimensioned shop drawings (PDF)

Assemble the packet with **`scripts/packet.py`**, not a separate `pdf` skill
(which does not exist in this environment). It inlines the SVG views (from
`draw.py`: `plan()` + `draw()` elevations) and the cut-list / assembly markdown
into one print-clean A4-landscape HTML with a title block, then shells out to
headless Chrome/Edge to print it to PDF:

```bash
python3 scripts/packet.py -o output/packet.pdf \
    --project "Living-room wall unit" --overall 1000x2000x600 --rev "Rev A" \
    --views output/plan.svg output/front.svg \
    --md output/cutlist.md output/assembly.md \
    --legend "mel18=#ececec; back4=#8a7a5c"
```

If no browser is found it still writes `packet.html` — that HTML is itself a
shippable deliverable (open it, Ctrl-P → Save as PDF). In practice you rarely call
this directly: `scripts/package.py` regenerates the packet alongside every other
deliverable in one command. The package contains:

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
5b. **Facade fully covered** (script-assisted): run
    `carcass.check_facade_coverage(spec)`. It projects every part on the visible
    face and reports any hole larger than the reveal gap that no front/rail/stile/
    leg covers — the class of bug where a divider stopped short (to clear a
    mechanism) leaves a visible gap between two fronts. Reveals pass; real holes
    fail. Open-front pieces (bookshelves) legitimately flag their open bays —
    treat those as expected, like a `check_overlaps` rebate flag.
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

## Publishing the package (optional)

Not every project publishes, but when the user wants a shareable link, the pattern
that worked: a small GitHub Pages site under `docs/` — `docs/index.html` landing
page, deliverables under `docs/downloads/*` (the PDF, xlsx, `.skp`, an embedded
model-viewer iframe), and a `.nojekyll` file so Pages serves the assets verbatim.
Two gotchas that each cost a round-trip:

- **`.gitignore` inline comments don't work.** `output/  # generated` does *not*
  ignore `output/` — the comment becomes part of the pattern. Put comments on their
  own line.
- **Enabling Pages via the API needs piped JSON.** `gh api -f` nested params fail;
  pipe the body instead:
  `echo '{"source":{"branch":"main","path":"/docs"}}' | gh api -X PUT repos/OWNER/REPO/pages --input -`.

Keep the per-project spec scripts either committed or consciously local — decide,
don't leave it ambiguous. The `.skp` and PDFs are build outputs; the `<piece>_spec.py`
is source.
