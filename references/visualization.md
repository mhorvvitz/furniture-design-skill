# Visualization

How to render the design so the user can react to it. Two modes: fast 2D for
iteration, interactive 3D for sign-off. Both read from the spec so they cannot
disagree with the numbers.

## 2D — scaled drawings via the `visualize` tool

Use `show_widget` with SVG. These are for *iterating the design*, and double as
the basis for the final shop drawings.

Conventions:
- **Draw to scale.** Pick a scale that fits the viewport (e.g. 1:10, 1:20) and
  apply it uniformly. A view that is not to scale teaches the user the wrong
  proportions.
- **Views**: plan (top-down), front elevation, side elevation, and at least one
  **section** through the carcass showing shelves/backs/thickness. Built-ins also
  get an elevation showing the opening and any obstructions from stage 2.
- **Dimension lines**: real dimension chains with extension lines, arrowheads, and
  the value in **mm**. Chain the parts so they visibly sum to the overall — this
  is also how the user catches a wrong number early.
- **Label parts** with the same names used in the cut list, so the drawing and the
  BOM speak the same language.
- **Show material thickness** as real double lines at panel edges, not hairlines —
  the thickness is load-bearing information here.
- Keep colours/fills minimal and high-contrast; this is a technical drawing, not a
  render. Use the visualizer's theming variables rather than hard-coded colours.

Iterate: render → user reacts → update spec → re-render. Cheap and fast; do many.

## 3D — realistic preview (three.js product render)

This is **not** a fallback — it is the pre-commit "how it could look" render that
the user approves before paying any SketchUp modelling cost. It runs whether or
not SketchUp is connected. (SketchUp's own render only exists *after* you commit
to building the model there, which is exactly the cost this preview defers.) No
AI photoreal image generator is available in this environment, so this three.js
render is the realistic preview; aim for product-render quality, not a flat CAD
look.

Build an HTML artifact with three.js the user can orbit.

Environment constraints (important — these will bite if ignored):
- three **r128** is available.
- `OrbitControls` is **NOT** available. Implement a minimal orbit yourself:
  track pointer down/move, and on drag rotate a parent `THREE.Group` (or the
  camera around a target) by the pointer delta. A dozen lines of pointer handlers
  is enough. A slow auto-turntable also reads well for a hero look.
- `CapsuleGeometry` is **NOT** available (r142+). Build everything from
  `BoxGeometry`, `CylinderGeometry`, `SphereGeometry`, or custom geometry.
- No external asset loads needed — boxes and cylinders cover carcasses, shelves,
  legs, fronts, dowels.

Make it look real (this is the point of this tier):
- **PBR materials**: `MeshStandardMaterial` with sensible `color`, `roughness`,
  and `metalness`. Wood ≈ roughness 0.6–0.8, metalness 0; matt melamine ≈
  roughness 0.7; lacquered ≈ lower roughness. A cheap canvas-generated grain
  texture on the wood lifts realism a lot; a flat colour is acceptable if pushed
  for time.
- **Lighting + tone mapping**: a soft environment (an env map via
  `PMREMGenerator`, or a 3-point rig of one key directional + ambient + a fill)
  plus `ACESFilmicToneMapping` and `sRGB` output. This is most of what separates a
  "render" from a "CAD screenshot."
- **Soft contact shadow**: a ground plane receiving shadows (`shadowMap` enabled,
  `PCFSoftShadowMap`) grounds the piece. Keep the plane neutral.
- **Camera**: a 3/4 hero angle, slight perspective, framed to the bounding box.

Build rules:
- **Drive geometry from the spec dimensions** (convert mm → scene units
  consistently, e.g. 1 unit = 1 mm, then frame the camera). The render must never
  use numbers the 2D views don't.
- Represent real thickness (panels are boxes of thickness `t`, not planes) so the
  proportions read true.
- Optional: a toggle to explode the assembly (offset each part along its normal) —
  useful for showing joinery and seeding the assembly drawing.
- One self-contained file. No `localStorage`/`sessionStorage` (unsupported in
  artifacts) — hold state in JS variables.

The render is for **approval and communication**, not measurement. The carpenter
builds from the 2D dimensioned drawings and the cut list — and, once committed,
the SketchUp `.skp` — never from this render.

## Staging the three tiers

1. **2D dimensioned drawings** (above) — settle layout and proportions; cheapest,
   iterate freely.
2. **Realistic 3D preview** (this section) — once the layout is roughly right,
   show "how it could look" for sign-off on form, material, and feel.
3. **Commit to SketchUp** — only after the user approves the look. Build the real
   model and `.skp` per `references/sketchup-integration.md`. If SketchUp is not
   connected, the tier-2 render stands as the 3D deliverable.

Do not skip to tier 3 on every tweak; the point of tiers 1–2 is to find the design
cheaply before committing.

## Keeping views honest

After any change, regenerate *both* the relevant 2D views and (if shown) the 3D
model from the updated spec. The failure mode to avoid is a drawing that still
shows last revision's dimension while the cut list moved on. One spec, many views,
always regenerated — never hand-patch a single view.
