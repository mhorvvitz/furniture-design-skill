#!/usr/bin/env python3
"""carcass.py — the parametric core of the furniture skill.

Turns conversation parameters into a POSITIONED-PART SPEC: a flat list of
axis-aligned parts, each with a corner (x,y,z), a size (sx,sy,sz), a component
definition name, material and grain. This one spec is the single source of truth
that every emitter reads — cut list, 2D drawing, 3D render, SketchUp build — so
they can never disagree.

Coordinate frame (mm): X = width (0..W), Y = height (0..H, up),
Z = depth (0..D, front face at Z=D). Corner = the minimum (x,y,z).

Identical parts share a `defn` (component-definition) name so the SketchUp emitter
can build them as instances and the cut list groups them. Cut-list L/W/thickness
are derived from the size: thickness = smallest axis, L/W = the other two.

Not a universal cabinet kernel (that's Polyboard/Cabinet Vision). It covers the
common box-carcass pattern — sides, fixed panels, dividers, shelves, drawers,
doors — which is what tables/shelving/wardrobes/kitchens actually are.
"""
import json, os

_MAT = None
def materials():
    global _MAT
    if _MAT is None:
        p = os.path.join(os.path.dirname(__file__), "..", "assets", "materials.json")
        _MAT = json.load(open(p, encoding="utf-8"))
    return _MAT


class Carcass:
    def __init__(self, W, H, D, t=18, material="plywood_birch", name="Piece", origin=(0, 0, 0)):
        self.W, self.H, self.D, self.t = W, H, D, t
        self.material = material
        self.name = name
        self.ox, self.oy, self.oz = origin
        self.parts = []

    # ---- low-level ----
    def add(self, defn, x, y, z, sx, sy, sz, material=None, grain="length", note="", kind=None):
        d = dict(defn=defn, name=defn,
                x=x + self.ox, y=y + self.oy, z=z + self.oz,
                sx=sx, sy=sy, sz=sz,
                material=material or self.material, grain=grain, note=note)
        if kind:
            d["kind"] = kind
        self.parts.append(d)

    # ---- carcass shell ----
    def sides(self, depth=None):
        d = depth or self.D
        self.add("Side", 0, 0, 0, self.t, self.H, d)
        self.add("Side", self.W - self.t, 0, 0, self.t, self.H, d)

    def bottom(self, depth=None):
        d = depth or self.D
        self.add("Bottom", self.t, 0, 0, self.W - 2 * self.t, self.t, d)

    def top(self, depth=None):
        d = depth or self.D
        self.add("Top", self.t, self.H - self.t, 0, self.W - 2 * self.t, self.t, d)

    def fixed_panel(self, z_height, defn="FixedPanel", depth=None):
        """Horizontal fixed panel with its underside at z_height (mm up)."""
        d = depth or self.D
        self.add(defn, self.t, z_height, 0, self.W - 2 * self.t, self.t, d)

    def back(self, tb=4, inset=True, material="hardboard"):
        if inset:
            self.add("Back", self.t, self.t, 0, self.W - 2 * self.t, self.H - 2 * self.t, tb,
                     material=material, grain="none")
        else:
            self.add("Back", 0, 0, -tb, self.W, self.H, tb, material=material, grain="none")

    def divider(self, x, y0, y1, defn="Divider", depth=None):
        d = depth or self.D
        self.add(defn, x - self.t / 2, y0, 0, self.t, y1 - y0, d)

    # ---- interior ----
    def shelves(self, count, y0, y1, x0=None, x1=None, defn="Shelf", depth=None, setback=20, side_gap=1):
        """`count` shelves evenly spaced between y0..y1, spanning x0..x1."""
        x0 = self.t if x0 is None else x0
        x1 = self.W - self.t if x1 is None else x1
        d = (depth or self.D) - setback
        w = (x1 - x0) - 2 * side_gap
        bays = count + 1
        gap = (y1 - y0 - count * self.t) / bays
        for i in range(1, count + 1):
            yb = y0 + i * gap + (i - 1) * self.t
            self.add(defn, x0 + side_gap, yb, 0, w, self.t, d)

    def door(self, y0, y1, leaves=2, defn="Door", front_t=None, gap=3, thick=None):
        """Overlay door leaves covering the opening y0..y1 across full width."""
        ft = thick or self.t
        zf = self.D  # overlay in front
        h = (y1 - y0) - 2 * gap
        total_w = self.W - 2 * gap
        w = (total_w - (leaves - 1) * gap) / leaves
        for i in range(leaves):
            x = gap + i * (w + gap)
            self.add(defn, x, y0 + gap, zf, w, h, ft, grain="length", kind="door")

    def drawers(self, y0, y1, count=1, mount="side_ball_bearing", front_defn="DrawerFront",
                box_material="plywood_birch", box_t=15, gap=3, mullion=True):
        """Drawer fronts + boxes across the opening y0..y1.
        Box width derives from the chosen mount's clearance (materials.json)."""
        dm = materials()["drawer_mounts"][mount]
        minus = dm.get("opening_minus")
        inner_x0, inner_x1 = self.t, self.W - self.t
        # optional center mullions between drawers
        cols = count
        mull_t = self.t if mullion and cols > 1 else 0
        clear_total = (inner_x1 - inner_x0) - (cols - 1) * mull_t
        opening = clear_total / cols
        # fronts (overlay, full face)
        zf = self.D
        fh = (y1 - y0) - 2 * gap
        fw = (self.W - 2 * gap - (cols - 1) * gap) / cols
        for i in range(cols):
            fx = gap + i * (fw + gap)
            self.add(front_defn, fx, y0 + gap, zf, fw, fh, self.t, grain="length", kind="door")
        # mullions
        for i in range(1, cols):
            mx = inner_x0 + i * opening + (i - 1) * mull_t
            self.add("DrawerMullion", mx, y0 + self.t, 0, mull_t, (y1 - y0) - self.t, self.D) if mull_t else None
        # boxes (only if the mount uses ply sides) — positioned behind the front,
        # centered in each opening; axis order corrected so sides are thin-in-X,
        # tall-in-Y, long-in-Z (depth), not the flat mis-oriented slab from v1.
        if minus is not None:
            bw = opening - minus
            bd = min(self.D - 80, 500)
            bh = min((y1 - y0) - self.t - 40, 180)
            bz0 = 40  # setback from the front overlay
            by0 = y0 + self.t + 5  # clear the carcass's own panel thickness (t) + a small gap
            for i in range(cols):
                ox = inner_x0 + i * (opening + mull_t)
                bxl = ox + (opening - bw) / 2
                bxr = bxl + bw - box_t
                self.add("DrawerBoxSide", bxl, by0, bz0, box_t, bh, bd, material=box_material, grain="none")
                self.add("DrawerBoxSide", bxr, by0, bz0, box_t, bh, bd, material=box_material, grain="none")
                self.add("DrawerBoxFB", bxl + box_t, by0, bz0,
                        bw - 2 * box_t, bh, box_t, material=box_material, grain="none")
                self.add("DrawerBoxFB", bxl + box_t, by0, bz0 + bd - box_t,
                        bw - 2 * box_t, bh, box_t, material=box_material, grain="none")
                self.add("DrawerBottom", bxl + box_t, by0, bz0,
                        bw - 2 * box_t, 4, bd, material="hardboard", grain="none")

    def rod(self, y, x0=None, x1=None, z=None):
        x0 = self.t if x0 is None else x0
        x1 = self.W - self.t if x1 is None else x1
        z = (self.D * 0.55) if z is None else z
        self.parts.append(dict(defn="Rod", name="Rod", kind="rod",
                               x=x0 + self.ox, y=y + self.oy, z=z + self.oz,
                               sx=x1 - x0, sy=22, sz=22, material="steel", grain="none", note=""))

    # ---- output ----
    def spec(self):
        return dict(name=self.name, overall=dict(W=self.W, H=self.H, D=self.D),
                    origin=[self.ox, self.oy, self.oz], parts=self.parts)


def cutlist_parts(spec):
    """Collapse the positioned spec into cutlist.py's part schema (dims, qty)."""
    groups = {}
    for p in spec["parts"]:
        if p.get("kind") == "rod":
            continue
        dims = sorted([p["sx"], p["sy"], p["sz"]])
        thick, W, L = dims[0], dims[1], dims[2]
        key = (p["defn"], round(L), round(W), round(thick), p["material"], p["grain"])
        groups[key] = groups.get(key, 0) + 1
    parts = []
    for (defn, L, W, thick, mat, grain), qty in groups.items():
        parts.append(dict(name=defn, qty=qty, length=L, width=W, material=mat, grain=grain))
    return parts


def check_overlaps(spec_or_parts, tolerance=1.0):
    """Generic AABB (axis-aligned bounding box) overlap detector across all parts,
    including rods. Flags any pair whose 3D boxes penetrate by more than
    `tolerance` mm on ALL THREE axes simultaneously — parts that are flush
    against each other (sharing a face, zero overlap) are NOT flagged; only
    true 3D penetration is. This is the standard AABB intersection test used
    throughout collision detection and CAD (e.g. SketchUp's own Solid
    Inspector) — nothing novel, just applied to the part list.

    This is exactly the class of check that would have caught the divider
    bug found during the closet test: a divider called with raw module
    bounds instead of true clear-space bounds physically overlapped the
    panels above and below it by 18mm on every axis.

    Returns a list of human-readable warning strings. Does not raise — the
    caller decides whether a warning is fatal.
    """
    parts = spec_or_parts["parts"] if isinstance(spec_or_parts, dict) else spec_or_parts

    def box(p):
        return (p["x"], p["x"] + p["sx"], p["y"], p["y"] + p["sy"], p["z"], p["z"] + p["sz"])

    warnings = []
    n = len(parts)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = parts[i], parts[j]
            ax0, ax1, ay0, ay1, az0, az1 = box(a)
            bx0, bx1, by0, by1, bz0, bz1 = box(b)
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            oz = min(az1, bz1) - max(az0, bz0)
            if ox > tolerance and oy > tolerance and oz > tolerance:
                warnings.append(
                    f"{a.get('name', a.get('defn', '?'))} overlaps "
                    f"{b.get('name', b.get('defn', '?'))} by "
                    f"{ox:.1f}x{oy:.1f}x{oz:.1f}mm — check divider/panel clear-space bounds"
                )
    return warnings


if __name__ == "__main__":
    # quick self-test: the 80cm bookshelf
    c = Carcass(800, 1800, 300, t=18, name="Bookshelf")
    c.sides(); c.bottom(); c.top(); c.back(4)
    c.shelves(4, y0=18, y1=1782)
    s = c.spec()
    print("positioned parts:", len(s["parts"]))
    for p in cutlist_parts(s):
        print(f"  {p['qty']}x {p['name']:10} {p['length']}x{p['width']}  {p['material']}")
