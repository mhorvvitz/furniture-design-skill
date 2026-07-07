---
name: furniture-design
description: >-
  Design, visualize, and produce buildable plans for custom furniture — both
  freestanding pieces (tables, shelving, beds, desks) and built-ins (closets,
  wall units, kitchens, מזנונים, ארונות קיר) — from chat, sketches, or photos to
  a carpenter-ready package: dimensioned shop drawings, cut list/BOM, hardware
  schedule. Use for designing furniture, planning a built-in, turning a sketch
  or inspiration photo into something buildable, working out measurements/cut
  lists/joinery/hardware, modelling in SketchUp, or iterating with 2D drawings
  or a 3D view — even without saying "cut list" or "shop drawing." With the
  SketchUp MCP connector present, it drives it as the 3D backend (real `.skp`),
  deferring geometry mechanics to the bundled SketchUp skills. Defaults to
  metric / Israeli shop conventions (mm, סנדוויץ'/מלמין/MDF sheets, System 32).
---

# Furniture Design → Build

This skill takes a person from a vague idea ("I want a wall unit for the living
room") to a package a carpenter (נגר) can build from without a second
conversation. It is a **conversational funnel**, not a CAD program.

## What this is, and what it is not

- **It is**: the domain **orchestrator** — it pins down design intent, holds
  dimensions in a disciplined mm spec, drives the visualisation, resolves the
  construction, and emits precise carpenter deliverables.
- **It is not**: a geometry engine or a nesting engine. When the **SketchUp MCP**
  connector is available, *it* is the 3D backend — `build_model` builds a real
  SketchUp model and `save_model` produces a `.skp`. This skill drives it but
  defers all SDK mechanics to the bundled SketchUp skills (see
  `references/sketchup-integration.md`); it never re-documents how to build
  geometry. For production sheet nesting, the standard is OpenCutList (run on the
  `.skp`) or CutList Optimizer — do not pretend to out-compute them.

This skill owns the part those tools do badly: the messy human front end, the
measurement discipline, the construction math, and the handoff. Geometry,
rendering, and nesting belong to the tools built for them.

## The one rule that prevents ruined material

**Never derive a real-world dimension from an image.** A photo or a hand sketch
has no scale, no metrology, and lying walls. If you read millimetres off a
picture, you will produce confident numbers that a carpenter cuts to, and the
sheet goods are then scrap.

So, hard split:
- **Images and sketches** drive *style, proportion, function, and intent*.
- **Numbers** come from the user physically measuring the space or the object,
  or from agreed ergonomic standards. Claude's job with numbers is to *hold,
  compute, cross-check, and lay them out* — never to *invent* them.

State this to the user the first time it matters. They will try to send a photo
and ask for measurements; that is the moment to redirect to measuring.

## Workflow

Five stages. They are a loop, not a waterfall — expect to bounce between 3 and 4.
At the start of a project, ask which **construction style** applies (frameless /
System-32 sheet goods, or solid-wood traditional joinery) — it changes
everything downstream, and there is no safe default.

### 1 — Capture intent

Establish, in plain conversation: what the piece is, where it lives, what it must
hold or do, the style/material vibe, who is building it, and the budget posture
(flat-pack KD vs glued-and-doweled vs fine joinery). Accept inspiration photos
and sketches here freely — they are gold for *intent*. Restate the brief back so
the user can correct it before any drawing happens.

### 2 — Measurement intake

This is the discipline that makes the output trustworthy. Read
`references/measurement-intake.md` and walk the user through the right checklist
for their case (built-in vs freestanding differ a lot). Built-ins especially:
walls are not square, floors are not level, and a single "the wall is 3 m" number
is a trap. Record everything into the working spec with its source noted
(measured / standard / assumed). Mark every assumed number as `assumed` so it is
visible later.

### 3 — Visual iteration

Get the user to the design they actually want before resolving construction.
Three tiers, cheap to expensive — find the design in 1–2 before committing to 3:

- **Tier 1 — 2D dimensioned drawings**: build the positioned-part spec with
  `scripts/carcass.py` and emit the SVG with `scripts/draw.py` (tested — correct
  dimension chains, door-hiding, auto-dimensioned bays), shown via `visualize` /
  `show_widget`. Settle layout and proportions here; cheapest, iterate freely.
  Hand-draw the SVG per `references/visualization.md` only when the piece falls
  outside the box-carcass envelope (see "The script pipeline" below).
- **Tier 2 — realistic 3D preview**: emit the three.js HTML from the same spec
  with `scripts/render.py` — orbitable, real materials, soft shadows, studio
  lighting — so the user signs off on form, material, and feel. This runs
  **whether or not SketchUp is connected**, and is the approval gate. There is no
  AI photoreal generator here, so this render is the realistic preview
  (`references/visualization.md` has the hand-build fallback and polish notes).
- **Tier 3 — commit to SketchUp** (only after the user approves the look): if the
  SketchUp MCP is connected, build the real model and `.skp`, deferring all
  geometry mechanics to the bundled SketchUp skills and minding the mm→inch unit
  boundary — see `references/sketchup-integration.md`. If SketchUp is not
  connected, the tier-2 render stands as the 3D deliverable.

Drive every view from the spec's dimensions so nothing disagrees with the numbers.
Loop within a tier (show → react → adjust spec → re-render), and do not jump to
tier 3 on every tweak. Move to stage 4 once the user has approved the look.

See `references/visualization.md` for the 2D conventions and the tier-2 render;
`references/sketchup-integration.md` for the tier-3 SketchUp commit.

### 4 — Construction resolution

Now make it buildable. Read `references/construction-knowledge.md` and resolve:
material and panel thicknesses; carcass construction; joinery; hardware (hinges,
runners, shelf supports, legs, handles); edge banding; and — for built-ins —
scribe/filler allowances against the un-square reality measured in stage 2.

The error that hides here is **material-thickness math**. A nominal 1000 mm-wide
carcass in 18 mm panels has an internal width of 1000 − 2×18 = 964 mm, the shelf
is ~964 mm (less clearance), and the back rebate changes the depth. Every part
dimension must fall out of this math explicitly — never reuse a nominal envelope
number as a cut size. The reference file carries the formulas, the System-32
grid, and the Israeli sheet-size constraints.

### 5 — Carpenter package

Read `references/deliverables.md`. Produce, in the **language of the
conversation**:

1. **Cut list / BOM** — every part: name, qty, finished L×W×thickness, material,
   grain direction, which edges get banding. Built from the spec via
   `scripts/cutlist.py`, which computes the arithmetic, validates that no part
   exceeds a real sheet, totals edge-banding, and gives a **sheet-yield
   estimate** (honest heuristic, not a guarantee — defer real nesting to
   OpenCutList/CutList Optimizer). Deliver as a spreadsheet (use the `xlsx` skill)
   and/or inside the drawing PDF.
2. **Dimensioned shop drawings** — orthographic plan + elevations + sections,
   joinery detail callouts, an exploded/assembly view, a hardware schedule, and a
   title block stating units = **mm**. Render to PDF via the `pdf` skill. Do not
   hand-roll PDF mechanics. (These come from the spec, not from SketchUp — the
   SketchUp skills do not produce dimensioned drawings.)
3. **Hardware schedule** — itemised with quantities and standard part references.
4. **3D model (`.skp`)** — when SketchUp is connected, include the saved `.skp`
   from stage 3 so the carpenter can open the model and, if they wish, run
   OpenCutList on it for an authoritative nesting plan. See
   `references/sketchup-integration.md`.
5. **Assembly plan** — generated by `scripts/assembly.py`: a step-by-step build
   document with per-part drilling coordinates (mm from a stated reference
   corner), hardware list, tools needed, and a reachability-sorted build order.
   Before generating, **read `assets/joinery.json`** and confirm the construction
   style with the user (`frameless_kd` / `frameless_permanent` / `traditional`)
   — the style selects the default joint types and their drilling specs. All
   drilling numbers come from the data file, never from the model's training
   data. v1 covers carcass joints and shelf pins; hinge-cup and runner mounting
   positions are deferred to v2.

Before exporting anything, run the consistency checks in
`references/deliverables.md` (and the script's validator). If a number fails a
check, fix it or flag it — do not ship a cut list you have not reconciled.

## The script pipeline (use it first, not as a last resort)

The `scripts/` directory is a tested pipeline, not optional extras. It exists
because hand-deriving geometry re-creates bugs that were already found and fixed
(seven of them — see `LIMITATIONS.md`, which read **before stage 4** on any
non-trivial piece).

- `scripts/carcass.py` — the parametric core. A `Carcass(W, H, D, t, material,
  name)` object with `sides()`/`top()`/`bottom()`/`back()`/`shelves()`/
  `divider()`/`drawers()`/`doors()`/`rod()`, plus a generic `add()` for any
  axis-aligned box part (legs, aprons, stretchers). `.spec()` returns the
  **positioned-part spec** — the single source of truth every emitter reads.
  `check_overlaps(spec)` is the collision validator; `cutlist_parts(spec)`
  bridges to the cut-list schema.
- `scripts/draw.py` — tier-1 dimensioned SVG elevations from the spec.
- `scripts/render.py` — tier-2 three.js product render from the spec.
- `scripts/cutlist.py` — validated cut list / BOM from `cutlist_parts()` output.
- `scripts/assembly.py` — connection derivation, per-part drilling coordinates,
  build order, and step-by-step assembly plan. All drilling numbers from
  `assets/joinery.json` (verified Häfele/Blum sources) — never from memory.
  v1 covers carcass joints (cam-and-dowel, confirmat, glued dowel) and shelf
  pins; v2 planned for hinge-cup and runner mounting positions.
- `scripts/sketchup_emit.py` — tier-3 `build_model` code from the spec, encoding
  the live-verified patterns (mm→inch conversion, axis remap, component
  definitions, lofted rods, style preset, hero camera).

**Envelope**: the pipeline covers axis-aligned box-carcass work — panels, boxes,
rods — which is most cabinetry, shelving, wardrobes, and simple leg-and-panel
pieces. Outside it (curved/angled parts, turned legs, real chair joinery),
hand-build the views per the references, but keep the same spec discipline and
run the same consistency checks. Known sharp edges (e.g. `divider()` takes the
caller's bounds on trust) are in `LIMITATIONS.md`.

## Hard rules (the guardrails, collected)

1. No real-world dimensions from images. Ever. Numbers are measured or standard.
2. Do material-thickness math explicitly for every part. Nominal ≠ cut size.
3. Units are millimetres, stated on every deliverable.
4. Built-ins: never assume square/level. Require multi-point measurements and
   carry a scribe/filler allowance (see construction reference).
5. Validate every part against real sheet sizes (2440×1220, 2800×2070 melamine).
   A part longer than the sheet is a design error to surface immediately.
6. Flag grain/decor direction on visible parts of woodgrain material.
7. Mark assumed numbers as assumed. Material and hardware *availability* is the
   supplier's call — give sane defaults, label them, tell the user to confirm.
8. Run the consistency checks before emitting the cut list. LLM arithmetic across
   dozens of parts is where wrong numbers reach the saw — let the script do it.
9. Ask the construction style per project; do not default silently.
10. **Units across the SketchUp boundary**: the spec is mm; `build_model` is
    inches-only. Convert at geometry creation (`÷25.4`), keep mm as the source of
    truth, and cross-check the model's bounding box back against the spec. A raw
    mm value passed to a geometry call builds the part ~25× too big.
11. When SketchUp is connected, **defer all geometry mechanics to the bundled
    SketchUp skills** (read them via the MCP's `read_skill`); never write SDK code
    from memory or re-document it here. See `references/sketchup-integration.md`.
12. **Run `check_overlaps()` on the positioned spec before shipping anything.**
    It has caught real clashes (a rod through a divider, drawers inside the
    bottom panel) that reading the numbers did not. Expected exception: parts
    that sit in a rebate/groove (inset backs, drawer bottoms) flag as overlaps
    because the box-only model doesn't represent the cut — account for every
    flag explicitly as either "rebate, fine" or "real bug, fix." Unaccounted
    flags block export.
13. **Never emit a drilling coordinate from memory.** All drilling dimensions
    (hole diameters, depths, edge distances, spacings) come from
    `assets/joinery.json` or the actual hardware's datasheet. If a number
    isn't in the data file and the user hasn't provided a datasheet, mark it
    `assumed` and tell the user to verify before drilling. A wrong drilling
    coordinate ruins a panel — this rule exists because LLM numeric recall
    is not reliable enough for fabrication.

## Reference files

- `references/measurement-intake.md` — what to measure and how, built-in vs
  freestanding, ergonomic standards, recording into the spec.
- `references/construction-knowledge.md` — materials, Israeli sheet sizes,
  thickness math, System 32, joinery options, hardware, built-in allowances,
  edge banding. Cross-references `assets/joinery.json` for drilling specs.
- `references/visualization.md` — 2D drawing conventions and the tier-2 realistic
  3D preview (three.js product render, incl. the r128 orbit workaround).
- `references/sketchup-integration.md` — using the SketchUp MCP as the 3D backend:
  division of labour, the mm→inch unit boundary, part→geometry mapping, which
  bundled SketchUp skill owns which job, and the `.skp` deliverable path.
- `references/deliverables.md` — cut-list spec/schema, how to run the script,
  shop-drawing package contents and conventions, the pre-export consistency
  checklist.
- `assets/joinery.json` — machine-readable drilling specs for cam-and-dowel,
  confirmat, glued dowel, shelf pins, euro hinges, and wall fixings. Verified
  against Häfele/Blum first-party sources. Read by `scripts/assembly.py`.
- `LIMITATIONS.md` — verified behaviour, known bugs and fixes, accepted modelling
  gaps, and explicitly deferred items. **Read before stage 4** on any non-trivial
  piece — it documents the `divider()` bounds trap and the box-carcass-only
  generality boundary.

## The working spec

Keep one structured spec for the project as you go. **The canonical shape is the
positioned-part spec produced by `carcass.py`** — every part with its corner,
size, definition name, material, and grain — and every view (2D SVG, 3D render,
SketchUp model) and the cut list are *derived* from it, never edited directly.
The flat cut-list JSON documented in `references/deliverables.md` is a derived
format: generate it with `cutlist_parts()`, don't hand-transcribe (hand-write it
only for out-of-envelope pieces that never had a positioned spec). Alongside the
geometry, track measurement sources (`measured`/`standard`/`assumed`), joinery,
and hardware. When in doubt, update the spec, then regenerate all views and the
cut list from it, so they can never drift apart.
