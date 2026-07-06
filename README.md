# Furniture Design

A lightweight furniture design toolchain for generating carpentry-ready deliverables from a structured part spec.

It is not a full CAD package. It is a domain orchestrator that:

- holds a consistent millimetre-based furniture spec
- computes panel/thickness math and part positions
- emits a validated cut list / BOM
- renders 2D dimensioned shop drawings as SVG
- produces an interactive three.js 3D preview
- can emit SketchUp-compatible build scripts when a SketchUp MCP connector is available

## Key concepts

- **Spec-driven**: every output is generated from one structured spec. The spec is the single source of truth, and all downstream outputs should be regenerated from it.
- **Millimetre-first**: the internal working units are mm. This repo preserves mm as the authoritative data and converts only at the SketchUp boundary.
- **Human-aware**: images and sketches are for intent only; real dimensions must come from measurement or agreed standards.
- **Carpenter package**: the goal is a cut list/BOM, shop drawings, a hardware schedule, and optionally a real `.skp` model.

## Repository structure

- `SKILL.md` — project description and operation notes for the furniture-design skill.
- `LIMITATIONS.md` — verified behavior, known limitations, and what is intentionally deferred.
- `assets/materials.json` — material catalog used by the emitter and drawer logic.
- `scripts/carcass.py` — parametric spec builder for furniture carcasses, shelves, doors, drawers, rods, and other parts.
- `scripts/cutlist.py` — converts a JSON furniture spec into a validated cut list, sheet-fit checks, banding totals, and a sheet-yield estimate.
- `scripts/draw.py` — generates dimensioned SVG front and side elevations from the positioned part spec.
- `scripts/render.py` — generates a self-contained three.js HTML preview for the part spec.
- `scripts/sketchup_emit.py` — emits SketchUp build code for a Trimble SketchUp MCP backend, with unit conversion and part grouping.
- `references/` — design, measurement, visualization, SketchUp integration, and deliverables guidance.

## Usage

### 1. Build or import a spec

The repo does not include a single user-facing CLI for spec creation. Use `scripts/carcass.py` as a reference or build your own JSON spec matching the expected shape.

A spec typically includes:

- `project` / `name`
- `units` = `mm`
- `materials` with `id`, `name`, `thickness`, `sheet`, `kerf`, and `trim`
- `parts` with `name`, `qty`, `length`, `width`, `material`, `grain`, `banding`, and optional `notes`
- optional `checks.overall` for envelope sanity checks

### 2. Generate a cut list

```bash
python3 scripts/cutlist.py spec.json --format md
python3 scripts/cutlist.py spec.json --format csv -o cutlist.csv
python3 scripts/cutlist.py spec.json --format json
```

`cutlist.py` exits with a non-zero status if validation fails. Fix the spec before continuing.

### 3. Generate 2D drawings

Use `scripts/draw.py` with a Python import or your own wrapper. Example from the module:

```python
from scripts.draw import draw
from scripts.carcass import Carcass

c = Carcass(800, 1800, 300, t=18, name="Bookshelf")
c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4, y0=18, y1=1782)
draw(c.spec(), "bookshelf.svg")
```

### 4. Generate a 3D preview

Use `scripts/render.py` to create a standalone HTML preview:

```python
from scripts.render import render
from scripts.carcass import Carcass

c = Carcass(800, 1800, 300, t=18, name="Bookshelf")
c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4, y0=18, y1=1782)
render(c.spec(), "bookshelf.html")
```

Open the HTML file in a web browser.

### 5. Emit SketchUp build code

If you have a Trimble SketchUp MCP connector available, `scripts/sketchup_emit.py` can emit the Python string used by the connector to build the model.

The repo expects the SketchUp backend to handle the actual model assembly, style, camera, and `.skp` save.

## References

Use these docs for detailed workflow and discipline:

- `references/measurement-intake.md` — what to measure and how to record it.
- `references/construction-knowledge.md` — panel math, material rules, System-32, joinery, and edge banding.
- `references/visualization.md` — 2D drawing conventions and the three.js render tier.
- `references/sketchup-integration.md` — SketchUp MCP unit boundary, tool availability, and workspace model expectations.
- `references/deliverables.md` — cut list schema, shop drawing package requirements, and pre-export checks.

## Design principles

- Never derive a real dimension from a photo or sketch.
- Always keep mm as the source of truth.
- Validate every part against real sheet sizes.
- Mark assumed numbers explicitly.
- Treat the cut list estimate as a heuristic, not an optimized nesting plan.
- Use SketchUp only as the final commit step, not for early layout exploration.

## Notes

- This repo is focused on furniture and cabinet-style construction, not general building architecture.
- The scripts are intended as emitters and validators, not production-level CAD tools.
- For final nesting and shop-ready `.skp` output, combine this repo's structured spec with industry tools like OpenCutList or CutList Optimizer.
