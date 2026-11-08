"""Hidden-TV flip-top coffee table — 1260 × 420 × 720 mm, white oak.

The skill's hardest piece, and the one that drove most of its features. It is
simultaneously:

  * **out of envelope** — no carcass panels at all; a leg-and-apron frame placed
    part-by-part through the generic `add()` escape hatch;
  * **a mechanism piece** — a piano-hinged lid that flips up 100° carrying a 43″
    TV on a VESA bracket, counter-balanced by gas struts;
  * **a fixture piece** — the TV and its bracket live in the spec because they
    drive the clearances and the views, but they are not cut parts, so they
    carry `kind="fixture"` and never reach the cut list;
  * **a drawer piece** — two farmhouse drawers with tall applied fronts over
    short, mechanism-clearing boxes.

The clearance-stack rule (`references/mechanisms.md`) is what set the depth: a
43″ panel plus bracket standoff would not clear the aprons at the original
600 mm, so the table grew to 660 mm of carcass depth *before* any structure was
drawn. It was not "made to fit."

Geometry frame (mm): X = length, Y = height (up), Z = depth, front face (the
sofa side) at Z = D — the skill's standard convention, which `validate_spec()`
checks. `overall` is the LID's footprint (1260 × 720); the leg-and-apron frame
beneath it is 1200 × 660, inset by the 30 mm overhang via `origin`, so the body
below can be written in comfortable carcass-local coordinates.

Measured inputs (2026-07-07, from the owner's actual 43″ TV): panel 970 × 560,
30 thick, VESA 200 × 200, bracket 20 thick, TV 10 kg + bracket 2 kg = 12 kg
hanging off the lid. Size the struts from that mass with the torque formula in
`references/mechanisms.md`, then confirm against the supplier's calculator —
the strut force is NOT asserted here.

Run:

    python scripts/package.py examples/coffee_table/coffee_table_spec.py \
        --out examples/coffee_table
"""
from carcass import Carcass

project = "Hidden-TV coffee table"
rev = "Rev B"
style = "traditional"          # solid oak, hidden joints

# Every veneered panel gets solid white-oak lipping on its exposed edges; the
# solid oak parts are planed, not banded.
# Banding tags are edge-relative, not world-relative: an apron's top edge runs
# along its length, so it is "l1" (one length edge), not "top".
banding = {
    "Lid": ["all"],
    "BackApron": ["l1"],       # top edge — visible once the lid is up
    "EndApron": ["l1"],
    "FrontBotRail": ["front"],
    "DrawerFront": ["all"],
}

notes = {
    "Lid": "30mm ply core, white-oak veneer BOTH faces, solid-oak lipping all round",
    "CenterStile": "solid oak; stub-tenoned to the bottom rail, cleated to the inner top rail — NOT to the lid",
    "FrontTopRail": "hidden tie rail + lid bearing, set back to clear the TV",
}

# Every contact pair, authored deliberately. Enumerate them with
#     python scripts/assembly.py --list-pairs examples/coffee_table/coffee_table_spec.py
# and regenerate after any geometry change — moving a part creates new
# adjacencies. Nothing here is guessed: this piece is entirely outside
# assembly.py's carcass vocabulary, so without these every joint would be
# flagged "default_assumed" for review.
#
# The three "none" entries are the point of the mechanism: the lid LIFTS, so it
# is fastened to the back apron (hinge) and the end aprons (struts) and to
# nothing else. Fastening it to the legs or the front rail would weld the
# mechanism shut.
joint_overrides = {
    ("BackApron", "Lid"): "piano_hinge",        # the hinge axis
    ("EndApron", "Lid"): "gas_strut",           # struts counter the 12kg lid
    ("FrontTopRail", "Lid"): "none",            # bearing surface only
    ("Leg", "Lid"): "none",                     # lid lifts clear

    ("BackApron", "Leg"): "glued_dowel",        # leg-and-apron frame
    ("EndApron", "Leg"): "glued_dowel",
    ("FrontBotRail", "Leg"): "glued_dowel",
    ("FrontTopRail", "Leg"): "pocket_screw",    # hidden ply tie rail
    ("BackApron", "CenterDivider"): "pocket_screw",
    ("CenterDivider", "CenterStile"): "pocket_screw",

    ("DrawerFB", "DrawerSide"): "pocket_screw",  # drawer box corners
    ("DrawerBottom", "DrawerFB"): "none",        # bottom captured, no fastener
    ("DrawerBottom", "DrawerSide"): "none",
}

# All contacts are flush butt joints — nothing penetrates.
expected_overlaps = 0

# ---- overall / frame -------------------------------------------------------
W, H, D = 1260, 420, 720       # the lid's footprint = the piece's overall
OVH = 30                       # lid overhang past the frame, all four sides
FW, FD = W - 2 * OVH, D - 2 * OVH   # frame footprint: 1200 × 660

LEG = 60                       # square leg
LEG_H = 390                    # floor to underside of lid
LID_T = 30
AP_T = 20                      # apron thickness
AP_H = 180                     # apron height
AP_Y = 210                     # apron bottom

HINGE_Y, HINGE_Z = LEG_H, 0    # piano-hinge axis: rear top of the frame
OPEN_DEG = 100                 # lid open angle (TV stands past vertical)
TRAVEL = 380                   # drawer open travel

# The lid, the TV and the bracket are ONE moving assembly: they share a motion
# group so the 2D open-state elevation and the 3D toggle move them together.
LID_MOTION = {"type": "hinge", "pivot": [HINGE_Y, HINGE_Z], "angle": OPEN_DEG,
              "group": "lid", "label": "Lift the lid"}
DRAWER_MOTION = {"type": "slide", "vector": [0, 0, TRAVEL],
                 "group": "drawers", "label": "Open drawers"}

WO_VEN = "white_oak_veneer"    # veneer over a stable ply core (exposed panels)
WO = "white_oak"               # solid oak (legs, stile, lipping)
PLY = "plywood_birch"          # drawer boxes + hidden rails
PLY_T = 18                     # a STOCKED birch-ply thickness (20mm is not)
HB = "hardboard"               # drawer bottoms


def build():
    # origin insets the whole frame by the overhang in X and Z, so the body
    # below is written in frame coordinates while the spec stays absolute.
    c = Carcass(W, H, D, t=AP_T, material=WO_VEN,
                name="Hidden-TV Coffee Table", origin=(OVH, 0, OVH))

    # ---- legs ----
    for x in (0, FW - LEG):
        for z in (0, FD - LEG):
            c.add("Leg", x, 0, z, LEG, LEG_H, LEG, material=WO, grain="length",
                  note="solid white oak — veneering a 60x60 leg is impractical")

    # ---- flip-up lid (hinged along the back apron) ----
    c.add("Lid", -OVH, LEG_H, -OVH, W, LID_T, D, material=WO_VEN, grain="length",
          motion=LID_MOTION,
          note=f"piano hinge inset {OVH}mm from the rear edge; TV VESA underneath; "
               f"gas struts sized from the 12kg lid assembly — verify with the supplier")

    # ---- aprons / frame ----
    c.add("BackApron", LEG, AP_Y, 0, FW - 2 * LEG, AP_H, AP_T,
          material=WO_VEN, grain="length",
          note="piano hinge mounts along its top edge")
    c.add("EndApron", 0, AP_Y, LEG, AP_T, AP_H, FD - 2 * LEG,
          material=WO_VEN, grain="length")
    c.add("EndApron", FW - AP_T, AP_Y, LEG, AP_T, AP_H, FD - 2 * LEG,
          material=WO_VEN, grain="length")

    # front frame — the drawer openings live here. The hidden ply members use
    # PLY_T, not the 20mm apron thickness: birch ply is not stocked at 20mm and
    # cutlist.py rejects it. Positioned so the rail still beds the lid at Y=390.
    c.add("FrontTopRail", LEG, LEG_H - PLY_T, 615, FW - 2 * LEG, PLY_T, PLY_T,
          material=PLY, grain="length")
    c.add("FrontBotRail", LEG, 190, FD - AP_T, FW - 2 * LEG, AP_T, AP_T,
          material=WO_VEN, grain="length",
          note="exposed between the legs")
    c.add("CenterDivider", 590, AP_Y, AP_T, PLY_T, 105, 620,
          material=PLY, grain="length",
          note="internal drawer divider, stopped short to clear the TV")

    # fixed oak face stile capping the gap above the stopped divider. Stopping
    # the divider left a facade hole that check_facade_coverage() caught — this
    # is the part that closes it.
    c.add("CenterStile", 578, 215, FD - AP_T, 44, 168, AP_T,
          material=WO, grain="length")

    # ---- the served object: NOT cut parts ----
    # kind="fixture" keeps these out of the cut list and the joint derivation
    # while still driving the clearance stack and every view.
    c.fixture("TV", 115, 340, 50, 970, LID_T, 560, material="tv",
              motion=LID_MOTION,
              note="43in panel 970x560x30 — lies flat when closed, flips up with the lid")
    c.fixture("VESAbracket", 500, 370, 230, 200, AP_T, 200, material="steel",
              motion=LID_MOTION,
              note="200x200 VESA, screwed to a solid backing block let into the lid")

    # ---- drawer fronts (tall applied facade over a short box) ----
    for x in (70, 625):
        c.add("DrawerFront", x, 215, FD - AP_T, 505, 168, AP_T,
              material=WO_VEN, grain="length", kind="door", motion=DRAWER_MOTION,
              note="APPLIED false front, screwed from inside the box; 3mm reveal "
                   "either side of the centre stile")

    # ---- drawer boxes (height limited by the TV well above) ----
    for x0 in (90, 640):
        c.add("DrawerSide", x0, 212, 40, 15, 100, 595, material=PLY,
              grain="none", motion=DRAWER_MOTION)
        c.add("DrawerSide", x0 + 455, 212, 40, 15, 100, 595, material=PLY,
              grain="none", motion=DRAWER_MOTION)
        c.add("DrawerFB", x0 + 15, 212, 620, 440, 100, 15, material=PLY,
              grain="none", motion=DRAWER_MOTION)
        c.add("DrawerFB", x0 + 15, 212, 40, 440, 100, 15, material=PLY,
              grain="none", motion=DRAWER_MOTION)
        c.add("DrawerBottom", x0 + 15, 212, 55, 440, 4, 565, material=HB,
              grain="none", motion=DRAWER_MOTION,
              note="captured between the front and back panels")

    return c.spec()


if __name__ == "__main__":
    import carcass as _c
    s = build()
    print(f"parts: {len(s['parts'])}  overall: "
          f"{s['overall']['W']}x{s['overall']['H']}x{s['overall']['D']}")
    for w in _c.validate_spec(s):
        print("  spec:   ", w)
    for w in _c.check_overlaps(s):
        print("  overlap:", w)
    for w in _c.check_facade_coverage(s):
        print("  facade: ", w)
