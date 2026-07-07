# SketchUp MCP Integration

When the **Trimble SketchUp MCP** connector is available, it is the 3D modelling
backend and the source of the `.skp` deliverable. This file is the bridge: when to
use it, the unit boundary, how furniture parts map to SketchUp geometry, and —
critically — which *bundled SketchUp skill* owns each job so this skill never
re-documents the SDK.

Detect availability by the presence of the SketchUp tools (`build_model`,
`save_model`, `list_skills`, `read_skill`, `create_model`/`load_model_from_path`).
If they are absent, fall back to `references/visualization.md` (visualizer SVG +
three.js). **This skill must not hard-depend on the connector.**

## Handling "connected but not approved"

A third state exists beyond "connector present" / "connector absent": the tools
are visible but the person has not (yet) granted per-call approval, or the
connector is toggled off for this chat. This surfaces as the **first** SketchUp
tool call failing with an approval/authorization error (e.g. "No approval
received") rather than any geometry error.

Procedure — do not treat this as a retry loop:

1. On the first SketchUp tool-call failure of this kind, **stop** — do not
   re-attempt the same call speculatively.
2. Tell the person plainly what happened (the connector didn't approve the
   call) and how to fix it (approve the prompt, or set the tool to
   **Always allow** under Settings → Connectors → Trimble SketchUp → Tool
   permissions, or check the connector is toggled on for this chat).
3. **Fall back to the tier-2 three.js render as the 3D deliverable** for this
   turn — do not block the rest of the pipeline (cut list, 2D drawings) on
   SketchUp access being resolved.
4. Offer to retry the SketchUp commit once the person confirms access is
   fixed; do not silently keep re-trying across turns.

This keeps the skill's tiered staging intact (2D → render → cut list → SketchUp
last) even when the SketchUp step specifically is blocked — the person still
gets a complete deliverable set, just without the `.skp`.

## Division of labour (do not duplicate)

This furniture skill owns the **domain**: the mm spec, measurement discipline,
carcass/thickness math, part naming, the cut list, and the carpenter handoff.

The **SketchUp MCP + its bundled skills** own the **geometry execution**. Before
generating any `build_model` code, read the relevant bundled skill (via the MCP's
`read_skill`, or as an installed skill if the user added it) — do not write SDK
code from memory. Map each job to its skill:

| Job | Bundled skill |
|---|---|
| Core SDK mechanics, namespace, partial-failure semantics, units | `sketchup-sdk` (read first) |
| Panels, shelves, tops, sides, doors, drawer fronts (flat boxes) | `sketchup-clean-geometry` → `make_quad_box` |
| Turned/tapered legs, posts, balusters, knobs | `sketchup-clean-geometry` → `build_lofted_solid` + `clean_geometry` |
| Repeated identical parts (shelves, legs, drawer fronts) | `sketchup-components` (component instances + arrays) |
| Organising the piece as a named part hierarchy | `sketchup-assembly-structure` |
| Keeping panels from overlapping at joints | `sketchup-part-boundaries` |
| Roundovers, chamfers, bullnose edges | `sketchup-rounded-corners`, `sketchup-solid-cleanup` |
| Presentation look (use the *Furniture / Product Studio* preset) | `sketchup-styles` |
| Hero camera before saving (required) | `sketchup-camera` |
| Multiple saved views (front / side / iso) | `sketchup-scenes` |

Ignore the SDK skill's *architectural* conventions that do not apply to furniture
— "walls are always 5 inches thick" and the door/window inner-loop opening rules
are for building models. Furniture parts are boxes (`make_quad_box`) and turned
solids (`build_lofted_solid`).

## The unit boundary (the highest-risk seam — get this right)

The working spec is in **mm**. `build_model` is **inches-only**. Convert at the
point of geometry creation, never before, and keep mm as the single source of
truth.

Put a conversion helper at the top of every `build_model` script:

```python
IN = 25.4
def mm(x):
    return x / IN        # mm -> inches
# e.g. an 18 mm panel, 600 mm deep, 2000 mm tall:
#   make_quad_box(mm(18), mm(600), mm(2000))
```

Never pass a raw mm number into a geometry call. A 600 mm shelf built as `600`
inches is a 15 m shelf — the `model_snapshot.bounding_box` will be wildly wrong.

**Cross-check after building**: `model_snapshot.bounding_box` w/d/h is in inches;
multiply by 25.4 and confirm it equals the spec's overall envelope in mm (within
rounding). If it does not, a conversion or transform error happened — stop and
fix before saving.

## Edit-friendly output structure (get this right, or the model is painful to edit)

A model where identical parts are independent copies is miserable to edit —
changing shelf depth means touching every shelf by hand. Build for editing, per
`sketchup-assembly-structure` and `sketchup-components`:

1. **Identical parts → one `ComponentDefinition`, N instances — never copies.**
   Editing the definition changes every instance at once, which is exactly what a
   user means by "edit the shelves as a group." Count-for-the-cut-list is
   unchanged (still N).
2. **Unique parts → named `Group`s.**
3. **The whole piece → one named top-level `Group`** containing all parts, so it
   selects and moves as a single unit. Furniture is the skill's canonical case.
4. **Name everything.** Definitions are singular nouns (`Shelf`, `Side`);
   instances are qualified (`Shelf_1`…`Shelf_N`); unique parts are descriptive
   (`Top`, `Bottom`, `Back`). A wall of `Group` / `Component#1` is a defined red
   flag. Append material + finished mm size so the model is self-documenting and an
   OpenCutList run on the `.skp` is meaningful:
   `defn.set_name("Shelf — mel18 — 762x290")`.
5. **Don't over-wrap.** Peer instances sit directly inside the piece's group; add a
   sub-group (e.g. `Drawers`) only for a real sub-assembly that moves/operates as a
   unit, not just because parts look alike.
6. **Handedness caveat.** Two mirror parts (left/right sides) share one definition
   *only if their features are symmetric*. With handed System-32 hole patterns they
   are mirror instances or separate definitions — do not blindly reuse one
   definition for both.

**Worked mapping — the 800×1800 bookshelf** (5 bays, 18 mm melamine):

```
Bookshelf  (Group at model root, placed by one transform)
├── Side          (ComponentDefinition)  → Side_L, Side_R      2 instances
├── TopBottom     (ComponentDefinition)  → Top, Bottom         2 instances (both 764×300)
├── Shelf         (ComponentDefinition)  → Shelf_1 … Shelf_4   4 instances (all 762×290)
└── Back          (Group, unique)                              1
```

Four physical part *types*, three shared definitions, one selectable object.
Change the shelf definition once and all four shelves update — and the cut list
still lists 4 × Shelf. Build each part at its own local origin and carry placement
on the instance/group transform (assembly-relative), so moving the piece is one
transform, not a vertex rewrite.

## Modelling workflow

**Default path**: generate the `build_model` code with `scripts/sketchup_emit.py`
from the positioned-part spec. It encodes, verbatim from the bundled skills and
verified live three times, the patterns that go wrong when re-derived: the
mm→inch conversion and spec-axis→SketchUp-axis remap, component definitions with
disambiguated names, lofted-cylinder rods with geometry cleanup, the
Furniture/Product Studio style preset, and the hero camera. Hand-write
`build_model` code — after reading the bundled skills via `read_skill` — only
for geometry the emitter doesn't cover. Either way, the workflow rules below
apply:

1. **Start clean.** First `build_model` of a modelling pass uses `clean: true` —
   guarantees an empty model and clears `session_state`, regardless of any
   residual state from a previous conversation (saved sessions stay alive).
2. **Build per the assembly-structure skill**: one group/component per part,
   positioned by the carcass math (all dimensions through `mm()`). Repeated parts
   via component arrays (`sketchup-components`), not copy-paste geometry.
3. **Materials**: solid-colour only (no `.skm` in the cloud env). Use
   `get_or_create_material` / `apply_material` from `sketchup-clean-geometry` to
   convey the finish (e.g. white melamine, walnut, oak).
4. **Style + camera**: apply the *Furniture / Product Studio* preset
   (`sketchup-styles`) and set a hero camera (`sketchup-camera`) — a camera is
   required before `save_model`.
5. **Save**: `save_model` → share the `.skp` download link and the thumbnail.
6. **Partial-failure aware**: `build_model` is not transactional. Build
   incrementally, inspect `model_snapshot` after each pass, and wrap risky
   operations in `try/except` so the model reaches a clean end-state.

## What SketchUp does NOT replace

- **The measurement discipline.** Still no real-world dimensions from photos. The
  model is only as right as the measured numbers feeding the spec.
- **The mm spec as source of truth.** The model is a *view* of the spec, like the
  2D drawings — regenerate it from the spec; never let the model become the
  authority and drift from the numbers.
- **Dimensioned 2D shop drawings.** The bundled skills cover modelling, style, and
  camera — not LayOut dimensioned drawings. Keep producing dimensioned
  plan/elevation/section via the visualizer + `pdf` skill
  (`references/deliverables.md`). The `.skp` gives the carpenter the 3D model and a
  render; the measured drawing still comes from the PDF path.
- **The cut list.** The MCP does not expose OpenCutList. Two coexisting paths:
  `scripts/cutlist.py` from the spec (works now, connector-independent), and — for
  an authoritative nesting plan — the user running **OpenCutList** on the saved
  `.skp` in SketchUp desktop. Offer both; do not claim the script out-computes
  OpenCutList.

## Staging (don't pay the modelling cost on every tweak)

Building and rebuilding the SketchUp model is not free, and it is the **commit**
step — the user reaches it only after approving the design. Find the design
cheaply first: iterate layout and proportions with the 2D visualizer (tier 1),
then show a realistic three.js product render for sign-off on look and material
(tier 2 — this is the pre-commit preview, not a fallback). **Then** commit to the
SketchUp model for the carpenter-grade 3D and the `.skp` (tier 3). Re-enter
SketchUp for substantive changes, not every minor nudge. See
`references/visualization.md` for tiers 1–2.
