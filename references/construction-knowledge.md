# Construction Knowledge

Everything needed to turn an approved design into a buildable spec. Numbers here
are Israeli-shop defaults; confirm material/hardware availability with the
supplier, and mark anything you assume.

## Material library (Israel — real stock)

Seeded from current Israeli supplier listings (עץ איתן, EGGER IL, camisa,
dpi-zahav, guetaavigdor). Confirm availability with the supplier — thicknesses and
sheet sizes vary by yard and change over time. Machine-readable copy lives in
`assets/materials.json`, which the generators and `cutlist.py` read.

**Sheet goods** — standard sheet 122×244 cm; melamine/MDF also 280×207 cm. Plan
nesting against the **usable** sheet (~2400×1200), not the nominal 2440×1220, to
leave saw kerf + edge cleanup.

| Material | Hebrew | Real thicknesses (mm) | Actual vs label | Typical use |
|---|---|---|---|---|
| Melamine particleboard (MFC) | סיבית מלמין | 8, 16, 18, 25 | ≈ nominal | carcasses, shelves, fronts |
| MDF | MDF / לוח סיבים | 3, 5.5, 7.5, 10, 12, 16, 19, 22, 28, 30 (EGGER: 12/16/19/22/28) | ≈ nominal (tightly calibrated) | painted/routed fronts, doors |
| Plywood — birch | דיקט בירץ׳ | 4, 6, 9, 12, 15, 18, 21, 30 | **−~1 mm** | fine/exposed work, structure |
| Plywood — okoume | אוקומה | 4, 6, 8, 10, 12, 17, 20, 30 | **−~1 mm** | cheaper carcasses, marine |
| Plywood — poplar | צפצפה | 4, 6, 8, 10, 12, 17 | **−~1 mm** | light, cheap |
| OSB | OSB | 11, 15, 18 | −~1 mm | hidden structure |
| Hardboard | מזונית | 3, 4, 5 | ≈ nominal | drawer bottoms, inset backs |

**Solid pine (nominal → finished/planed).** Sold un-planed (נסור) at nominal cm
sections; planing (הקצעה) removes material, so **the finished size is smaller and
the cut list must use the finished value, never the nominal.** Common sections:
2.5×5, 2.5×10, 5×5, 5×10, 5×20 cm. Finished ≈ **nominal − ~5 mm per dimension**
(assumed placeholder — **confidence low**; varies by mill, confirm before cutting).

Notes:
- MFC: pre-finished, cheap, fast; weak screw-holding in the cut edge — use KD
  connectors or confirmat, not plain screws into the edge.
- Plywood: stronger, holds edge fasteners well, more stable for tall doors; birch
  gives the clean striped edge people expose deliberately. Costs more.
- Solid wood moves seasonally — never trap a wide solid panel captive on all edges.

## Sheet sizes (the nesting constraint)

Stock sheets in Israel (confirm with supplier):
- **2440 × 1220 mm** — the universal sheet (8×4 ft) for plywood/סנדוויץ', MDF,
  OSB, and much MFC.
- **2800 × 2070 mm** — common large melamine/MFC sheet.
- MFC also available **2440 × 1220**; some suppliers **2750 × 1830**.

Two consequences:
1. **Any finished part must fit within a stock sheet** (allowing for saw kerf and
   a trim margin). A part longer than 2800 mm, or wider than 1220 mm on a 2440×1220
   sheet, is a design error — surface it, then split the part or change material.
2. **Woodgrain/decor MFC has a direction.** A "horizontal grain" look forces part
   orientation on the sheet and changes yield. Track grain on every visible part.

## Thickness math (do this for every part — never skip it)

Let `t` = panel thickness (e.g. 18). For a simple box carcass of external
width `W`, height `H`, depth `D`, with top/bottom captured between the two sides
(sides run full height):

- Sides (×2): `H` long × `D` deep
- Top & bottom (×2): `(W − 2t)` long × `D` deep
- Fixed shelf: `(W − 2t)` × `(D − back_rebate − front_setback)`
- Back, rebated into a 4 mm groove set in `g` from the rear:
  - panel ≈ `(W − 2t + 2·groove_depth)` × `(H − 2t + 2·groove_depth)`
  - or, full-overlay back screwed on: `W` × `H` (simpler, less clean)
- Adjustable shelf: `(W − 2t − clearance)` × shelf depth; clearance ~ 2–3 mm total
  so it does not bind.

If top/bottom instead **cap** the sides (sides between top and bottom):
- Sides (×2): `(H − 2t)` × `D`
- Top & bottom (×2): `W` × `D`

Decide which carcass scheme you are using and apply it consistently. Write the
scheme into the spec; the cut list depends on it.

### Fronts: doors and drawer faces

For overlay fronts, size each face to its opening plus the overlay, minus the
reveal/gap between adjacent fronts. A typical reveal/gap is **~3 mm**. In System
32 work, face heights/widths are an increment of 32 mm minus the gap (e.g.
32×8 − 3 = 253 mm) so they index to the hole grid.

Drawer box internal width = opening − 2×runner clearance (runner-specific, often
~13 mm per side for ball-bearing, ~ per spec for undermount — read the runner's
datasheet; do not guess the clearance).

## System 32 (frameless cabinetry)

The European frameless standard, and what most Israeli kitchen hardware assumes.

- Two rows of **5 mm holes**, spaced **32 mm** centre-to-centre, run top-to-bottom
  on the inside of each side panel.
- Front row is **37 mm** from the front edge (industry standard setback for hinge
  plates, shelf pins, and drawer-slide brackets).
- Hinge **cup** is **35 mm** diameter, bored in the door.
- Cabinet heights that land on the grid: **720 mm** (22×32 + 16 mm panel) and
  **768 mm** (24×32). Widths typically 300–1200 mm in steps; base depth ~560–576.
- Faces sized in 32 mm increments minus the gap so hardware indexes cleanly and
  shelves/doors are interchangeable.

Use System 32 when: frameless sheet-goods cabinets, euro hinges, adjustable
shelves on pins, drawer banks. Skip it for solid-wood face-frame or traditional
joinery, where the grid does not apply.

## Joinery / connection methods

Pick per construction style and per budget. Built-ins are usually KD (knock-down)
or doweled-and-glued; fine freestanding work earns real joinery.

Sheet-goods / KD:
- **Cam-and-dowel** (minifix/Rafix + dowel): the standard flat-pack/site-assembly
  connector. Hidden, demountable, fast. Default for kitchens and closets.
- **Confirmat screws**: strong, simple, visible head (or capped); great for
  carcass assembly where the side is hidden.
- **Dowels (glued)**: clean, strong, permanent; needs accurate boring.
- **Dado/groove + glue**: captures shelves/backs; combine with mechanical fixing.
- **Pocket screws**: fast, strong, visible holes on the hidden face.

Solid-wood / traditional:
- **Mortise & tenon**: frames, tables, chairs. The strong default.
- **Dovetails**: drawer boxes, casework corners; strong and fine.
- **Domino / biscuit**: alignment + moderate strength for panels and frames.
- **Breadboard ends / floating panels**: to allow solid-wood movement.

Always allow for seasonal movement in solid wood; never glue a wide solid panel
captive on all four edges.

## Hardware

- **Hinges**: euro/concealed, 35 mm cup. Overlay type — full / half / inset —
  must match the front layout. Soft-close is the common expectation. Specify cup
  drilling distance from the door edge per the hinge datasheet.
- **Drawer runners / mounts** — the choice sets the **drawer-box width** (box =
  cabinet clear opening − the clearance below). Always confirm the exact clearance
  from the chosen runner's datasheet; the figures below are typical, not gospel.

  | Mount | Box width = opening − | Feel / cost | Notes |
  |---|---|---|---|
  | Side-mount ball-bearing, full-extension | **~26 mm** (13/side) | cheap, visible runner, IL-common | 25–45 kg/pair; box height free |
  | Side-mount, soft-close | ~26 mm | mid | as above + damper |
  | Undermount soft-close (Blum Tandem, Hettich) | **~42 mm** | hidden, premium | box back/bottom notched per system; needs 4 mm+ bottom in groove |
  | Metal-sided system (Blum Antaro/Legrabox, Hettich AvanTech) | **no ply sides** | cleanest, priciest | buy the drawer as a unit; only the **front + bottom (+ back)** are shop-made |
  | Roller/epoxy (light duty) | ~26 mm | cheapest | 3/4 extension, light loads only |

  Rule: never emit a drawer-box dimension until the mount is chosen — the
  clearance is the mount's, not a guess.
- **Shelf supports**: pins into the 5 mm / 32 mm holes; studs/brackets for heavy
  loads.
- **Legs / feet**: adjustable cabinet legs (typ. 100–150 mm) + clip-on toe-kick
  (פנל סוקל); levels on uneven floors.
- **Handles / pulls**: knobs, bar pulls, or handleless (J-profile / push-to-open)
  — affects front sizing and machining.
- **Wall fixing** (built-ins **and any tall unit**): suspension brackets / French
  cleat + packers for the un-plumb wall. **Anti-tip anchoring is mandatory for any
  tall unit in a child's room** — a floor-standing wardrobe that isn't screwed to
  the wall is a tip-over hazard; children climb open drawers.

## Built-in allowances (against the un-square reality)

- **Scribe**: leave a scribe strip on the side(s) that meet a wall — extra
  material (commonly 10–20 mm) planed to follow the wall's true line. Without it,
  a gap shows.
- **Filler panels**: where a run does not divide evenly, or to stand cabinets off
  a wall/corner for door clearance.
- **Toe-kick taper**: if the floor slopes, the kick is scribed/tapered so the
  carcass sits level (use the smallest measured height as the level reference).
- **Top scribe / shadow gap**: where the unit meets a non-level ceiling, either
  scribe the top or design a deliberate shadow gap so the error is not read as a
  mistake.
- Always design from the **smallest** measured width/height; the surplus goes into
  scribe and filler, never the other way around.

## Edge banding (קנט)

- Visible edges of MFC/MDF get banding (PVC, commonly 0.4–2 mm; 1–2 mm for
  impact-prone edges like fronts and worktops).
- On the cut list, record **which edges** are banded per part (e.g. "front +
  both long edges"). Banding adds ~ its thickness to the visible dimension —
  usually ignored at 0.4–1 mm, but note it for tight tolerances.
- Hidden edges (against a wall, inside a carcass) are usually left raw to save
  cost — confirm the user's preference.
