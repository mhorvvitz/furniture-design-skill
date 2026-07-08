# Known limitations

Stated plainly so nobody mistakes "packaged" for "finished." Verified vs
unverified is marked explicitly — see the confidence note on each.

## Verified with evidence

- **`cutlist.py`** — validated against real specs (bookshelf, closet ×2, plus a
  deliberate name-collision test). Correctly rejects oversized parts, unknown
  materials, non-positive dims, and now auto-suffixes (`_A`/`_B`) any part name
  reused across two genuinely different sizes so a cut list can never present
  two distinct sizes under one ambiguous label. **Confidence: high.**
- **`carcass.py`** — all methods now exercised: shell (`sides`/`bottom`/`top`/
  `back`/`shelves`) on the bookshelf; `drawers()`/`doors()`/`divider()`/`rod()`
  on the closet (36 parts, two stacked modules). **Confidence: high**, with the
  caveat on `divider()` noted below.
- **`check_overlaps()`** (new) — generic AABB (axis-aligned bounding box)
  overlap detector across all parts, including rods. Standard collision-
  detection technique (same approach as SketchUp's own Solid Inspector), not a
  novel invention. **Proven to catch real bugs, not just run cleanly**: it
  independently re-discovered the divider-clash bug from the original closet
  test when fed a reconstruction of the buggy call, and — on this round's
  fresh pass — caught two *new*, previously-undetected bugs (see below).
  **Confidence: high** that it catches true 3D penetration; it also flags
  rebate/groove joints (backs, drawer bottoms) that this box-only model doesn't
  represent — those are expected, documented, and distinguishable from real
  bugs by inspection (see "Known, accepted modeling gap" below).
- **`draw.py`** — verified on the bookshelf and closet: correct panel counts,
  correct overall dims, correct auto-dimensioned bay/clear-height chains
  (338/339mm bookshelf; 1464mm hang-zone, 249/250mm cubbies, 282mm drawer clear
  on the closet — the 249.3mm figure matches independent hand calculation from
  earlier in the session). Door-hiding for the "internal" view now keyed off a
  `kind="door"` tag rather than fragile exact-name matching (a real bug this
  round's testing caught — see below). **Confidence: high on geometry.** Visual
  polish is plainer than a hand-tuned drawing — auto-placing dimension lines
  without collisions is an open CAD problem, not something this script solves.
- **`render.py`** — verified: valid HTML/JS (`node --check` passed), correct
  part counts embedded on both test pieces. **Confidence: high on code
  correctness, moderate on visual appearance** (three.js can't be executed
  headless here — never actually seen rendered, only reasoned about).
- **`sketchup_emit.py` + the SketchUp MCP pipeline** — **verified live, three
  times**: bookshelf (simple box carcass), full closet (36 parts, two stacked
  modules, doors, drawers, dividers, rods — box-approximated rods on that
  pass), and a standalone rod/style/camera test (confirms the *current*, fully
  upgraded emitter). All three confirmed correct via the tool's own returned
  data, not self-assessment:
  - mm→inch conversion and the spec-axis→SketchUp-axis remap: bounding box
    matched expected exactly, all three runs.
  - True lofted-cylinder rods (`build_lofted_solid` + `clean_geometry_on_entities`,
    verbatim from the bundled skills): confirmed via returned bbox — 364mm test
    rod measured exactly 364mm in the snapshot, correct 22mm diameter, and
    14-face clean-quad topology (12 merged side quads + 2 caps) matching the
    skill's documented cleanup behavior.
  - Furniture/Product Studio style preset (verbatim RGB/RenderingOptions values
    from `sketchup-styles/references/presets.md`): applied without error.
  - Tuned hero-shot camera (verbatim FOV-aware recipe from `sketchup-camera`
    SKILL.md): `camera_ok: true`, correct FOV returned, verified via the skill's
    own recommended read-back check.
  **Confidence: high** across doors/drawers/dividers/rods/style/camera.

## Bugs found and fixed this round (kept here for the record, not swept away)

Two testing passes — the original closet build, and this round's "close the
deferred items" pass — surfaced seven real bugs total. All are fixed in the
shipped scripts, not just noted here. Listed because catching them is the
point of testing:

1. **Carcass depth double-counted the door** (18mm too deep). Fixed: shell
   depth 582mm + 18mm overlay door = 600mm external.
2. **Dividers 36mm too long — real physical clash** with the panels above/below.
   Fixed by computing bounds from panel faces, not nominal module boundaries.
   `divider()` does not enforce this itself — see the open sharp edge below.
3. **`draw.py`'s door-hiding filter used exact string match**, silently failing
   for any defn name other than the literal "Door". Fixed via a `kind="door"`
   tag set in `carcass.py`, filtered on in `draw.py`.
4. **Drawer box parts had no real position or correct axis orientation** — all
   10 pieces stacked at `(0,0,0)`, wrong axis order. Fixed with real per-drawer
   positioning and corrected axis order.
5. **SketchUp rod length was ~25.4× too short** — a double unit-conversion in
   the original box-approximation scaling trick. Caught from the tool's own
   `model_snapshot` bounding boxes, not local reasoning — the top-level bbox
   check didn't catch it because rods don't move the overall envelope. **This
   remains a documented limitation of the bbox cross-check itself**: it
   verifies gross unit/axis errors on load-bearing geometry, not every
   individual part. (Superseded by item 7 below — rods are no longer boxes.)
6. **Full-width top rod crashed straight through the vertical divider.** The
   original closet build declared one continuous rod spanning the full 1200mm
   width, not accounting for the divider occupying the middle of that same
   height range. Caught by `check_overlaps()`, not by manual review — this is
   exactly the class of bug the checker was built for. Fixed by splitting into
   two rod segments, one per side of the divider (which is also how this would
   actually be built — a rod doesn't pass through solid wood).
7. **Drawer boxes started 8mm inside the carcass's own bottom panel.** The
   quick "reasonable approximation" placement (`by0 = y0 + 10`) didn't account
   for the carcass bottom panel's 18mm thickness. Caught by `check_overlaps()`.
   Fixed: `by0 = y0 + t + 5` (clears the panel plus a margin).

## Known, accepted modeling gap (not a bug — distinguish from the above)

`check_overlaps()` also flags every case where a thin panel is meant to sit in
a **rebate or groove** cut into another part — the inset back panel against
full-depth interior parts (dividers, shelves, mullions), and each drawer
bottom against its box's front/back panels. This carcass builder does not
model grooves/rebates; every part is a plain box. In real construction these
are relieved by a dado cut and do not conflict; in this idealized model they
show as bounding-box overlap because the geometry doesn't represent the cut.
**This is expected and was manually verified**: on the closet, all 12 remaining
overlap warnings (after fixing the 2 real bugs above) decompose exactly into
8 back-panel cases + 4 drawer-bottom cases — nothing unaccounted for.
Confidence this is fully understood, not a hidden bug pile: high.

## Unverified / explicitly deferred

1. **`divider()`'s clear-space-bounds sharp edge.** The method takes whatever
   `y0`/`y1` the caller passes; it does not itself verify those are true
   clear-space bounds rather than nominal module bounds. Bug #2 above happened
   exactly this way. `check_overlaps()` will now catch the *consequence* of
   getting this wrong (if the caller remembers to run it), but nothing
   currently *prevents* the mistake at the point of calling `divider()`. A
   future version could compute clear-space bounds automatically from
   neighboring panels; not implemented.
2. **The material catalog (`assets/materials.json`) is seeded, not exhaustive
   or per-supplier**, and never will be — it's inherently bounded by what
   suppliers stock at a given time. Confirm before ordering.
3. **Solid-lumber finished size (`plane_loss_mm: 5`) is an assumed placeholder**,
   flagged low-confidence in `construction-knowledge.md`. Mill-specific; no
   amount of further research converts this to a fact absent a real
   measurement. Update it if you get real numbers from a supplier.
4. **The "connected but not approved" fallback is now documented** (a
   stop-inform-fallback procedure in `sketchup-integration.md`) but **not
   tested** — there was no live scenario in which to trigger the failure path
   deliberately once approval was granted. Confidence the documented procedure
   is sound: moderate (it's straightforward, but untested is untested).
5. **Three shapes tested end-to-end** (bookshelf, closet, and — new — a
   leg-and-apron flip-top coffee table with a hidden TV, piano-hinged lid, gas
   struts, and two farmhouse drawers). The coffee table was the first genuinely
   out-of-envelope piece and the first mechanism piece, and it exercised the
   generality boundary hard:
   - **Generalized cleanly**: the `Carcass.add()` escape hatch (every part placed
     via `add()`), `check_overlaps()`, `cutlist.py` validation, and the
     `sketchup_emit.py` mm→inch/axis seam (bbox cross-check exact).
   - **Did not, and were fixed in this pass**: `draw.py` sized by height alone
     (blew the canvas on a low/wide piece — now fits both axes); `assembly.py`
     silently classified the piano hinge and pocket-screwed boxes as glued dowels
     (now flags out-of-envelope joints loudly + honours `joint=` overrides);
     `drawers()` couldn't do a tall applied front over a short mechanism-clearing
     box (now parameterized). The mechanism vocabulary (`kind="fixture"`, `joint=`,
     `motion=`, `front_h`/`box_h`) was added so the emitters extend to
     out-of-envelope pieces instead of being rebuilt by hand.
   Still unproven beyond this: curved/turned/angled work and real chair joinery —
   nothing here shows the skill generalizes past axis-aligned panels + simple
   leg-and-apron structure.

## What "finished" would additionally require

- A true generality test: a project that isn't a panel-and-carcass box.
- Resolving item 1 above (either by discipline or by automating clear-space
  bound computation in `divider()`).
- A live trigger of the "connected but not approved" path to confirm the
  documented fallback actually behaves as written under Claude's own judgment
  mid-conversation, not just as a procedure on paper.
