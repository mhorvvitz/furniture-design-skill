"""Bookshelf — 800 × 1800 × 300 mm, birch plywood, 4 adjustable shelves.

The skill's canonical box-carcass case: a freestanding open bookshelf, glued and
doweled (frameless_permanent), inset hardboard back. Run:

    python scripts/package.py examples/bookshelf/bookshelf_spec.py --out examples/bookshelf
"""
from carcass import Carcass

project = "Birch bookshelf"
style = "frameless_permanent"
banding = {"Side": ["front"], "Shelf": ["front"], "Top": ["front"], "Bottom": ["front"]}
# The inset back rebates against the 4 shelves; the box model reads those as
# overlaps (expected — a rebate the flush-box model can't represent).
expected_overlaps = 4


def build():
    c = Carcass(800, 1800, 300, t=18, material="plywood_birch", name="Bookshelf")
    c.sides()
    c.bottom()
    c.top()
    c.back(4)
    c.shelves(4, y0=18, y1=1782)
    return c.spec()
