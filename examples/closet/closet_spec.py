"""Wardrobe closet — 1200 × 2400 × 600 mm, white melamine, System 32.

A frameless knock-down built-in: full-height centre divider splitting a hanging
bay (rod + hat shelf) from a five-shelf bay, behind two overlay doors. Exercises
the carcass helpers (sides/top/bottom/back/divider/shelves/rod/door) and the
System-32 shelf-pin drilling in assembly.py. Run:

    python scripts/package.py examples/closet/closet_spec.py --out examples/closet
"""
from carcass import Carcass

project = "Melamine wardrobe"
style = "frameless_kd"
banding = {"Door": ["all"], "FixedPanel": ["front"], "Shelf": ["front"]}
# Inset back rebates against the divider, the hat shelf, and the 5 shelves
# (1 + 1 + 5 = 7) — all expected rebate flags the box model can't represent.
expected_overlaps = 7

W, H, D, T = 1200, 2400, 600, 18
MID = W / 2                     # divider centre


def build():
    c = Carcass(W, H, D, t=T, material="melamine", name="Wardrobe")
    c.sides()
    c.bottom()
    c.top()
    c.back(4)

    # full-height centre divider
    c.divider(MID, y0=T, y1=H - T)

    # left bay: hanging — a hat shelf near the top, rod just below it
    c.shelves(1, y0=1900, y1=H - T, x0=T, x1=MID - T / 2, defn="FixedPanel")
    c.rod(y=1840, x0=T + 20, x1=MID - T / 2 - 20)

    # right bay: five adjustable shelves
    c.shelves(5, y0=T, y1=H - T, x0=MID + T / 2, x1=W - T)

    # two overlay doors across the full face
    c.door(y0=T, y1=H - T, leaves=2)

    return c.spec()
