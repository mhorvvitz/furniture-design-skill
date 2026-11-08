# Assembly Plan — Hidden-TV Coffee Table

Overall: 1260 × 420 × 720 mm
Construction style: traditional
Joint method: glued_dowel

## Mechanism & hardware notes

These joints are mounted per the hardware datasheet or a sizing procedure — no fixed drilling coordinates are emitted for them:

### pocket_screw — בורג כיס (Kreg)
Pocket-hole joinery: an angled Ø9.5mm stepped pilot bored with a Kreg-class jig, screw driven into the mating part. Fast and strong for boxes and face frames; semi-visible holes (plug or hide inside the box).
- **Mounting**: clamp the joint, drive screws through the pockets into the mating part; no through-drilling on the show face
- **Spacing**: one screw ~50mm from each end, then every ~150mm along the joint
- [confidence: high] — verify against the actual product datasheet.

### piano_hinge — ציר פסנתר (רצוף)
Continuous (piano) hinge running the full length of a lid/door. Distributes load along the whole edge — the right choice for a flip-top lid.
- **Mounting**: mount per the hinge datasheet: knuckle/barrel centred on the pivot line and sitting proud of the surface, leaf inset from the edge so the lid clears as it swings. Confirm leaf width against panel thickness before buying.
- **Spacing**: fasten EVERY pre-punched hole on a lid that bears weight
- [confidence: assumed] — verify against the actual product datasheet.

### gas_strut — בוכנת גז (לדלת מתרוממת)
Gas spring / lid stay that holds a lifting lid open and eases its fall. Sizing is a torque calculation, NOT a drilling coordinate.
- **Procedure**: required strut force ≈ (lid mass M × g × d_cg) ÷ mounting-arm length, split across the number of struts, where d_cg is the hinge-to-centre-of-gravity distance. Mark the force ASSUMED and confirm with the supplier's lid-stay / gas-strut calculator (Blum Aventos, Häfele Free, or the strut maker's tool). Bracket geometry sets the open angle.
- **Mounting**: one strut per side for lids over ~5kg or ~600mm; end fittings per the strut's ball-stud brackets
- [confidence: assumed] — verify against the actual product datasheet.

## Tools needed

- Brad-point Ø8mm with depth stop
- Carpenter's square / angle clamp
- Clamps
- Rubber mallet
- Pencil + tape measure

## Hardware list

- 1× continuous piano hinge (cut to lid length)
- 8× fluted hardwood dowel Ø8×30mm
- 2× ball-stud end brackets
- 2× gas struts (force per supplier calc)
- 1× hinge screws (every hole)
- 12× pocket-hole screws (length per panel thickness)
- 8× wood glue

## Pre-assembly drilling

**Do ALL drilling before you start assembling.** Once panels are joined, you can't reach the inside faces.

### BackApron_5

**glued_dowel** (face) — connecting to Leg_0:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at 140mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (face) — connecting to Leg_2:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at 140mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

### EndApron_6

**glued_dowel** (face) — connecting to Leg_0:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at 140mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (face) — connecting to Leg_1:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at 140mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

### EndApron_7

**glued_dowel** (face) — connecting to Leg_2:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at 140mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (face) — connecting to Leg_3:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at 140mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

### FrontBotRail_9

**glued_dowel** (face) — connecting to Leg_1:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at -20mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (face) — connecting to Leg_3:

  - **dowel_face**: Ø8mm × 15.0mm deep, at 40mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_face**: Ø8mm × 15.0mm deep, at -20mm along panel, panel_centermm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

### Leg_0

**glued_dowel** (edge) — connecting to BackApron_5:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at 140mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (edge) — connecting to EndApron_6:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at 140mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

### Leg_1

**glued_dowel** (edge) — connecting to EndApron_6:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at 140mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (edge) — connecting to FrontBotRail_9:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at -20mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

### Leg_2

**glued_dowel** (edge) — connecting to BackApron_5:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at 140mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (edge) — connecting to EndApron_7:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at 140mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

### Leg_3

**glued_dowel** (edge) — connecting to EndApron_7:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at 140mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

**glued_dowel** (edge) — connecting to FrontBotRail_9:

  - **dowel_edge**: Ø8mm × 19mm deep, at 40mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]
  - **dowel_edge**: Ø8mm × 19mm deep, at -20mm along panel, panel_thickness / 2mm from edge. Bit: Brad-point Ø8mm with depth stop. [confidence: high]

## Assembly steps

### Step 1: Install Leg

Parts: Leg_0, Leg_1, Leg_2, Leg_3

1. Position and fix per the drilling schedule above.

### Step 2: Install Lid

Parts: Lid_4

1. Position and fix per the drilling schedule above.

### Step 3: Install BackApron

Parts: BackApron_5

1. Position and fix per the drilling schedule above.

### Step 4: Install EndApron

Parts: EndApron_6, EndApron_7

1. Position and fix per the drilling schedule above.

### Step 5: Install FrontTopRail

Parts: FrontTopRail_8

1. Position and fix per the drilling schedule above.

### Step 6: Install FrontBotRail

Parts: FrontBotRail_9

1. Position and fix per the drilling schedule above.

### Step 7: Install CenterDivider

Parts: CenterDivider_10

1. Position and fix per the drilling schedule above.

### Step 8: Install CenterStile

Parts: CenterStile_11

1. Position and fix per the drilling schedule above.

### Step 9: Install TV

Parts: TV_12

1. Position and fix per the drilling schedule above.

### Step 10: Install VESAbracket

Parts: VESAbracket_13

1. Position and fix per the drilling schedule above.

### Step 11: Install DrawerSide

Parts: DrawerSide_16, DrawerSide_17

1. Position and fix per the drilling schedule above.

### Step 12: Install DrawerFB

Parts: DrawerFB_18, DrawerFB_19

1. Position and fix per the drilling schedule above.

### Step 13: Install DrawerSide

Parts: DrawerSide_21, DrawerSide_22

1. Position and fix per the drilling schedule above.

### Step 14: Install DrawerFB

Parts: DrawerFB_23, DrawerFB_24

1. Position and fix per the drilling schedule above.

### Step 15: Assemble drawer boxes

Parts: DrawerBottom_20, DrawerBottom_25

1. Position and fix per the drilling schedule above.

### Step 16: Hang doors

Parts: DrawerFront_14, DrawerFront_15

1. **v2 will add hinge-cup drilling coordinates here.**
2. Attach mounting plates to carcass sides at 37mm from front edge.
3. Click hinges into mounting plates; adjust overlay and alignment.

---
*All drilling coordinates from joinery.json (verified sources). Confirm hardware-specific dimensions against the actual product you purchased.*