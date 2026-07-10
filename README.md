# Furniture Design

A lightweight furniture design toolchain for generating carpentry-ready deliverables from a structured part spec.

> **New here?** The [landing page](https://mhorvvitz.github.io/furniture-design-skill/) has one-click downloads and install steps. Or jump straight to [Using this skill with Claude](#using-this-skill-with-claude).

It is not a full CAD package. It is a domain orchestrator that:

- holds a consistent millimetre-based furniture spec
- computes panel/thickness math and part positions
- emits a validated cut list / BOM (md, csv, json, **xlsx**)
- renders 2D dimensioned shop drawings as SVG (plan, elevations, open-state)
- produces an interactive three.js 3D preview with open/close + explode toggles
- assembles a **print-clean packet PDF** from the drawings and cut list
- generates an assembly plan with per-part drilling coordinates
- regenerates the entire package from one spec with a single command
- can emit SketchUp-compatible build scripts when a SketchUp MCP connector is available

## Key concepts

- **Two authored sources of truth**: the design *inputs* — measurements (with their source), materials, hardware, and decisions — are authored in a per-project `docs/spec.md`; the verified drilling/hardware specs live in `assets/joinery.json`. Everything else is *derived* from these and should never be authored twice.
- **Spec-driven**: from the authored inputs, one **positioned-part spec** is computed (part positions with thickness math). Every output — cut list, 2D drawings, 3D preview, assembly plan, SketchUp build — is generated from that positioned spec and should be regenerated from it, never hand-edited.
- **Millimetre-first**: the internal working units are mm. This repo preserves mm as the authoritative data and converts only at the SketchUp boundary.
- **Human-aware**: images and sketches are for intent only; real dimensions must come from measurement or agreed standards.
- **Carpenter package**: the goal is a cut list/BOM, shop drawings, a hardware schedule, and optionally a real `.skp` model.

## Data flow

Inputs are authored once, at the top, and flow one way to every output:

```
docs/spec.md                 authored inputs — SOURCE OF TRUTH for measurements,
   │                         materials, hardware, decisions (each with its source)
   │  (agreed numbers transcribed in)
   ▼
<piece>_spec.py              the per-project instance script — drives carcass.py
   │  .spec()                (the shared parametric engine; not edited per project)
   ▼
positioned-part spec         every part: corner + size + material + grain,
(the dict / spec.json)       computed with thickness math — source of truth for geometry
   │
   ├─► draw.py           →  2D dimensioned SVG (plan + elevations + open-state)
   ├─► render.py         →  3D three.js preview
   ├─► cutlist.py        →  cut list / BOM  (md/csv/xlsx/json; reads spec.json)
   ├─► assembly.py       →  drilling coords + build order   ◄── assets/joinery.json
   ├─► sketchup_emit.py  →  build_model code → .skp
   └─► packet.py         →  print-clean packet PDF (views + cut list + assembly)

   package.py runs draw/render/cutlist/assembly/packet in one command,
   gated on check_overlaps — use it to regenerate the whole package after a change.
```

Change an input in `docs/spec.md` first, then rebuild the positioned spec, then regenerate the outputs — so nothing drifts. Where a script and `docs/spec.md` disagree, the record wins and the script is corrected.

## Repository structure

- `SKILL.md` — project description and operation notes for the furniture-design skill.
- `LIMITATIONS.md` — verified behavior, known limitations, and what is intentionally deferred.
- `assets/materials.json` — material catalog used by the emitter and drawer logic.
- `scripts/carcass.py` — parametric spec builder for furniture carcasses, shelves, doors, drawers, rods, fixtures, and other parts; plus `cutlist_spec()`, `check_overlaps()`, and `check_facade_coverage()`.
- `scripts/cutlist.py` — converts a JSON furniture spec into a validated cut list (md/csv/json/xlsx), sheet-fit checks, banding totals, and a sheet-yield estimate.
- `scripts/draw.py` — dimensioned SVG plan, front/side elevations, and an open-state elevation for moving parts.
- `scripts/render.py` — self-contained three.js HTML preview with motion (open/close) and explode toggles.
- `scripts/blender_render.py` — optional photoreal product still (Blender Cycles via `pip install bpy`, ~1 GB — not vendored) for online-store listings; alpha cutouts and 360° turntable sets.
- `scripts/assembly.py` — connection derivation, per-part drilling coordinates, build order, and a step-by-step assembly plan.
- `scripts/sketchup_emit.py` — emits SketchUp build code for a Trimble SketchUp MCP backend, with unit conversion and part grouping.
- `scripts/packet.py` — assembles the SVG views + cut-list/assembly markdown into one print-clean A4 PDF (headless Chrome/Edge); no external skill dependency.
- `scripts/package.py` — one command to regenerate the whole package from a project spec module, gated on `check_overlaps`.
- `references/` — design, measurement, visualization, mechanisms, SketchUp integration, deliverables, and the Stage-6 skill-review reviewer.

## Examples

Three real pieces, each run end-to-end through the pipeline. Every folder holds
its `*_spec.py` and the full generated package — cut list (md/csv/json/xlsx),
plan + elevations (SVG), 3D preview (HTML), assembly plan, and the packet PDF.

| Example | Piece | Size (mm) | Material | Shows off |
|---|---|---|---|---|
| [`examples/bookshelf`](examples/bookshelf) | Birch bookshelf | 800 × 1800 × 300 | Birch plywood | The core box-carcass case: sides/top/bottom/back + adjustable shelves |
| [`examples/table`](examples/table) | Oak dining table | 1600 × 750 × 900 | Solid oak + oak-veneer top | Out-of-envelope leg-and-apron built with `add()`; solid-wood + veneer materials |
| [`examples/closet`](examples/closet) | Melamine wardrobe | 1200 × 2400 × 600 | White melamine | System-32 built-in: centre divider, hanging rod, 5 shelves, two overlay doors |

Regenerate any of them with:

```bash
python scripts/package.py examples/table/table_spec.py --out examples/table
```

## Using this skill with Claude

### Download

Two packaged downloads, both of which unzip to a `furniture-design/` folder:

- **[`furniture-design.skill`](https://github.com/mhorvvitz/furniture-design-skill/raw/main/furniture-design.skill)** — the installable skill (SKILL.md, references, assets, scripts). This is the one to install.
- **[`furniture-design-skill-main.zip`](https://github.com/mhorvvitz/furniture-design-skill/raw/main/furniture-design-skill-main.zip)** — the full repo snapshot, if you also want the README and this landing page.

(A `.skill` file is just a zip — rename to `.zip` if your unzip tool won't open it directly.)

### Install (Claude Desktop and Claude Code / CLI)

1. Unzip the download and place the `furniture-design/` folder in Claude's skills directory:
   - Windows: `%USERPROFILE%\.claude\skills\furniture-design`
   - macOS/Linux: `~/.claude/skills/furniture-design`
2. Confirm the folder holds `SKILL.md` at its top level.
3. Restart Claude (or your CLI session) and start a new chat so the skill is discovered.
4. Ask for a furniture task — e.g. *"design me a 900 mm oak sideboard"* — and the skill activates.

You can also symlink the repo into the skills directory instead of copying, so updates are picked up automatically.

### SketchUp MCP setup

This skill is most useful when the SketchUp MCP connector is also available:

1. Install and launch the Trimble SketchUp MCP connector/server.
2. Enable it in Claude Desktop or your CLI session.
3. Confirm the connector can open SketchUp and save a `.skp` model.
4. Once that is working, the skill can use `scripts/sketchup_emit.py` to generate model-ready build instructions.

For implementation details, see `references/sketchup-integration.md`.

## Usage

### 1. Build the positioned-part spec

The canonical spec is the **positioned-part spec** built with `scripts/carcass.py`
— every part with its corner position, size, definition name, material, and
grain. Every downstream output (cut list, 2D drawings, 3D preview, SketchUp
build) is derived from it. The input numbers you pass in (dimensions, material,
thickness) should come from the project's `docs/spec.md`, where they are authored
and their sources recorded — not re-declared here as their canonical copy (see
[Data flow](#data-flow)).

```python
from scripts.carcass import Carcass, check_overlaps

c = Carcass(800, 1800, 300, t=18, name="Bookshelf")
c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4, y0=18, y1=1782)
spec = c.spec()
check_overlaps(spec)   # account for every flag before continuing
```

There are two JSON shapes in this repo — don't confuse them:

- the **positioned spec** above (corner + size per part): the source of truth;
- the **flat cut-list JSON** consumed by `cutlist.py` (`materials` +
  `parts` with `length`/`width`/`qty`/`banding`): a derived format. Generate its
  `parts` array with `carcass.cutlist_parts(spec)` rather than transcribing
  dimensions by hand. Only hand-write it for pieces `carcass.py` can't model.

### 2. Generate a cut list

```bash
python3 scripts/cutlist.py spec.json --format md
python3 scripts/cutlist.py spec.json --format csv  -o cutlist.csv
python3 scripts/cutlist.py spec.json --format json
python3 scripts/cutlist.py spec.json --format xlsx -o cutlist.xlsx   # needs openpyxl
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

### 5. Generate an assembly plan

```python
from scripts.assembly import write_assembly_plan
from scripts.carcass import Carcass

c = Carcass(800, 1800, 300, t=18, name="Bookshelf")
c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4, y0=18, y1=1782)
write_assembly_plan(c.spec(), "bookshelf_assembly.md", style="frameless_permanent")
```

The assembly plan includes per-part drilling coordinates (from `assets/joinery.json`), a hardware list, tools needed, and a reachability-sorted build order. All drilling dimensions are sourced from verified Häfele/Blum specifications with confidence levels.

### 6. Emit SketchUp build code

If you have a Trimble SketchUp MCP connector available, `scripts/sketchup_emit.py` can emit the Python string used by the connector to build the model.

The repo expects the SketchUp backend to handle the actual model assembly, style, camera, and `.skp` save.

### 7. Regenerate the whole package with one command

Author the piece as a small `<piece>_spec.py` that exposes `spec` (or a `build()` returning it), then let `package.py` rebuild every deliverable — cut list (all formats), 2D views, 3D render, assembly plan, and the packet PDF — after a `check_overlaps` gate:

```bash
python3 scripts/package.py my_piece_spec.py --out output/
python3 scripts/package.py my_piece_spec.py --out output/ --only cutlist,views   # cheap incremental
```

Keep that spec module in the project — it's a source file, not scratch. To build only the packet PDF from existing views + markdown, call `scripts/packet.py` directly.

## References

Use these docs for detailed workflow and discipline:

- `references/measurement-intake.md` — what to measure and how to record it.
- `references/construction-knowledge.md` — panel math, material rules, System-32, joinery, and edge banding.
- `references/visualization.md` — 2D drawing conventions and the three.js render tier.
- `references/mechanisms.md` — lift-lids, flip-tops, and other moving-mass pieces: clearance-stack rule, strut/hinge sizing, racking reinforcement.
- `references/sketchup-integration.md` — SketchUp MCP unit boundary, tool availability, the `.skp` download/validation pattern, and workspace model expectations.
- `references/deliverables.md` — cut list schema, shop drawing package requirements, and pre-export checks.
- `references/skill-review-agent.md` — the Stage-6 end-of-project reviewer that feeds improvements back to the skill.
- `assets/joinery.json` — machine-readable drilling specs for Israeli-standard joinery (cam-and-dowel, confirmat, glued dowel, shelf pins, euro hinges). Verified against Häfele and Blum first-party sources.

## Development — release artifacts

`furniture-design.skill` and `furniture-design-skill-main.zip` are rebuilt
automatically on every commit by a tracked pre-commit hook
(`.githooks/pre-commit`), so the downloads never lag the source. The build is
deterministic, so a commit that doesn't touch the packaged content leaves the
archives byte-identical (no spurious diffs).

On a fresh clone, enable the hook once:

```bash
git config core.hooksPath .githooks
```

To rebuild by hand: `python scripts/build_release.py`.

## v2 roadmap

Planned additions for the assembly plan (tracked in `assets/joinery.json` and `scripts/assembly.py`):

- **Hinge-cup drilling positions**: Ø35mm cup boring on doors, mounting plate positions on carcass sides. Data already seeded in joinery.json (`euro_hinge_35cup`); emitter integration deferred because positions are brand/overlay-dependent and need the user's specific hinge datasheet.
- **Drawer runner mounting positions**: screw hole coordinates for side-mount and undermount runners. Deferred because clearances are mount-specific (current `drawer_mounts` in materials.json carries the box-width deduction but not screw positions).

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
