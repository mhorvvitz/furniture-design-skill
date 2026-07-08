"""Dining table — 1600 × 750 × 900 mm, solid white oak, leg-and-apron.

An out-of-envelope piece: no carcass panels, every part placed with the generic
`add()` escape hatch — a 30 mm top on four 80 mm posts tied by aprons, 100 mm
overhang all round. Demonstrates solid-hardwood material and assembly.py's
out-of-envelope joint flagging (legs↔aprons are outside the carcass vocabulary,
so the plan marks those joints for review rather than guessing them). Run:

    python scripts/package.py examples/table/table_spec.py --out examples/table
"""
from carcass import Carcass

project = "Oak dining table"
style = "traditional"
# Solid legs/aprons are planed (no banding); the veneered-panel top gets an oak
# lipping on all four edges.
banding = {"Top": ["all"]}
expected_overlaps = 0     # all contacts are flush (butt joints), none penetrate

W, H, D = 1600, 750, 900
TOP_T = 30
LEG = 80                  # square post
INSET = 100               # leg inset from each edge (= overhang)
AP_T = 20                 # apron thickness
AP_H = 140                # apron height
LEG_H = H - TOP_T         # posts run floor to underside of top

# leg X/Z corners
lx0, lx1 = INSET, W - INSET - LEG        # 100, 1420
lz0, lz1 = INSET, D - INSET - LEG        # 100, 720
ay = LEG_H - 20 - AP_H                   # apron sits just under the top


def build():
    c = Carcass(W, H, D, t=AP_T, material="white_oak", name="DiningTable")

    # top (full footprint, overhanging the legs) — veneered oak panel with solid
    # oak lipping, so it comes off one sheet rather than edge-gluing wide boards
    c.add("Top", 0, LEG_H, 0, W, TOP_T, D, material="white_oak_veneer", grain="length",
          note="oak-veneered panel, solid-oak lipping all edges")

    # four legs
    for x in (lx0, lx1):
        for z in (lz0, lz1):
            c.add("Leg", x, 0, z, LEG, LEG_H, LEG, material="white_oak", grain="length")

    # long aprons (front/back), flush to the outer legs, spanning between them
    ap_x0, ap_len = lx0 + LEG, (lx1) - (lx0 + LEG)      # 180 .. 1420
    c.add("ApronFront", ap_x0, ay, lz0, ap_len, AP_H, AP_T, material="white_oak", grain="length")
    c.add("ApronBack",  ap_x0, ay, lz1, ap_len, AP_H, AP_T, material="white_oak", grain="length")

    # short aprons (sides), spanning between front/back legs
    ap_z0, ap_wid = lz0 + LEG, (lz1) - (lz0 + LEG)      # 180 .. 720
    c.add("ApronSide", lx0, ay, ap_z0, AP_T, AP_H, ap_wid, material="white_oak", grain="length")
    c.add("ApronSide", lx1 + LEG - AP_T, ay, ap_z0, AP_T, AP_H, ap_wid, material="white_oak", grain="length")

    return c.spec()
