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

Part `kind` tags (optional, on `add()`):
  - "door"    — overlay front; hidden in the internal 2D view, skipped for joints.
  - "rod"     — hanging rod; round in 3D, excluded from cut list & joints.
  - "fixture" — a NON-CUT, render-only object that lives in the spec because it
                drives clearances and views (a TV, a VESA bracket, a mattress, a
                sink, an appliance) but must never reach the cut list or the joint
                derivation. Rendered by draw/render/sketchup_emit in a muted tone;
                skipped by cutlist_parts/cutlist_spec and assembly.py.
Parts may also carry `joint=` (e.g. "piano_hinge", "pocket_screw", "none") to
override assembly.py's joint classification for that part — see assembly.py.
"""
import json, os

_MAT = None
def materials():
    global _MAT
    if _MAT is None:
        p = os.path.join(os.path.dirname(__file__), "..", "assets", "materials.json")
        _MAT = json.load(open(p, encoding="utf-8"))
    return _MAT


# Sections searched (in order) when resolving a material id to sheet/colour info.
_MATERIAL_SECTIONS = ("sheet_goods", "veneered_panels", "solid_hardwoods")


def material_info(material_id):
    """Resolve a material id against materials.json across all catalog sections.
    Returns a dict {section, he, notes, rgb, sheet, is_board} or None if unknown.
    `sheet` is a [L, W] mm footprint for the cut-list fit check (nominal sheet for
    sheet goods / veneered panels, board_stock_max for solids)."""
    m = materials()
    for section in _MATERIAL_SECTIONS:
        d = m.get(section, {})
        e = d.get(material_id)
        if isinstance(e, dict):
            info = {"section": section, "he": e.get("he", ""),
                    "notes": e.get("notes", ""), "rgb": e.get("rgb"),
                    "sheet": None, "is_board": section == "solid_hardwoods"}
            ns = e.get("nominal_sheet")
            bs = e.get("board_stock_max")
            if ns:
                info["sheet"] = list(ns[0])
            elif bs:
                info["sheet"] = list(bs)
            return info
    # fixtures section is flat {id: {rgb,...}}
    fx = m.get("fixtures", {})
    if isinstance(fx.get(material_id), dict):
        e = fx[material_id]
        return {"section": "fixtures", "he": "", "notes": e.get("notes", ""),
                "rgb": e.get("rgb"), "sheet": None, "is_board": False}
    return None


def material_color(material_id, default=None):
    """RGB tuple for a material from materials.json, or `default` if unknown."""
    info = material_info(material_id)
    if info and info.get("rgb"):
        return tuple(info["rgb"])
    return default


def fixture_default_color():
    return tuple(materials().get("fixtures", {}).get("_fixture_default_rgb", [58, 58, 62]))


class Carcass:
    def __init__(self, W, H, D, t=18, material="plywood_birch", name="Piece", origin=(0, 0, 0)):
        self.W, self.H, self.D, self.t = W, H, D, t
        self.material = material
        self.name = name
        self.ox, self.oy, self.oz = origin
        self.parts = []
        self.warnings = []

    def _warn(self, msg):
        self.warnings.append(msg)
        import sys
        print(f"WARNING (carcass): {msg}", file=sys.stderr)

    # ---- low-level ----
    def add(self, defn, x, y, z, sx, sy, sz, material=None, grain="length", note="", kind=None, joint=None):
        d = dict(defn=defn, name=defn,
                x=x + self.ox, y=y + self.oy, z=z + self.oz,
                sx=sx, sy=sy, sz=sz,
                material=material or self.material, grain=grain, note=note)
        if kind:
            d["kind"] = kind
        if joint is not None:
            d["joint"] = joint
        self.parts.append(d)

    def fixture(self, defn, x, y, z, sx, sy, sz, material="steel", note="", grain="none"):
        """A non-cut, render-only object (TV, VESA bracket, mattress, appliance).
        Lives in the spec to drive clearances and views; excluded from the cut
        list and joint derivation via kind='fixture'."""
        self.add(defn, x, y, z, sx, sy, sz, material=material, grain=grain,
                 note=note, kind="fixture")

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
                box_material="plywood_birch", box_t=15, gap=3, mullion=True,
                front_h=None, box_h=None, box_depth=None, open_top=False,
                front_mode="overlay"):
        """Drawer fronts + boxes across the opening y0..y1.
        Box width derives from the chosen mount's clearance (materials.json).

        Extra parameters for out-of-the-ordinary drawers (defaults reproduce v1):
          front_h    — explicit front height (mm). Default: opening height
                       (y1-y0)-2*gap. Use a taller value for a farmhouse-style
                       APPLIED front that covers more facade than the box is tall.
          box_h      — explicit box height (mm). Default: the current heuristic
                       min((y1-y0)-t-40, 180). Cap it below the front when a
                       mechanism owns the top of the interior.
          box_depth  — explicit box depth (mm). Default: min(D-80, 500).
          open_top   — annotate the box as intentionally open-topped (it already
                       is in this model; the flag documents intent in the note).
          front_mode — "overlay" (default) or "applied" (false front screwed on
                       from inside the box; note marks it so the shop knows).
        """
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
        fh = front_h if front_h is not None else (y1 - y0) - 2 * gap
        fw = (self.W - 2 * gap - (cols - 1) * gap) / cols
        applied = front_mode == "applied"
        fnote = "APPLIED false front — screwed from inside the box" if applied else ""
        for i in range(cols):
            fx = gap + i * (fw + gap)
            self.add(front_defn, fx, y0 + gap, zf, fw, fh, self.t, grain="length",
                     kind="door", note=fnote)
        # mullions
        for i in range(1, cols):
            mx = inner_x0 + i * opening + (i - 1) * mull_t
            self.add("DrawerMullion", mx, y0 + self.t, 0, mull_t, (y1 - y0) - self.t, self.D) if mull_t else None
        # boxes (only if the mount uses ply sides) — positioned behind the front,
        # centered in each opening; axis order corrected so sides are thin-in-X,
        # tall-in-Y, long-in-Z (depth), not the flat mis-oriented slab from v1.
        if minus is not None:
            bw = opening - minus
            bd = box_depth if box_depth is not None else min(self.D - 80, 500)
            bh = box_h if box_h is not None else min((y1 - y0) - self.t - 40, 180)
            bz0 = 40  # setback from the front overlay
            by0 = y0 + self.t + 5  # clear the carcass's own panel thickness (t) + a small gap
            bnote = "open-topped drawer box" if open_top else ""
            # sanity: the box should not rise above the front it hides
            front_top = y0 + gap + fh
            if by0 + bh > front_top + 1:
                self._warn(
                    f"drawer box top ({by0 + bh:.0f}mm) rises above its front top "
                    f"({front_top:.0f}mm) — box would show above the facade; "
                    f"reduce box_h or raise front_h")
            for i in range(cols):
                ox = inner_x0 + i * (opening + mull_t)
                bxl = ox + (opening - bw) / 2
                bxr = bxl + bw - box_t
                self.add("DrawerBoxSide", bxl, by0, bz0, box_t, bh, bd, material=box_material, grain="none", note=bnote)
                self.add("DrawerBoxSide", bxr, by0, bz0, box_t, bh, bd, material=box_material, grain="none", note=bnote)
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


_CUTLIST_EXCLUDE = ("rod", "fixture")


def cutlist_parts(spec, exclude_kinds=_CUTLIST_EXCLUDE):
    """Collapse the positioned spec into cutlist.py's part schema (dims, qty).

    Internal helper — for a full, validatable cutlist.py input use cutlist_spec().
    Excludes non-cut parts (rods and fixtures) by `kind`.
    """
    groups = {}
    for p in spec["parts"]:
        if p.get("kind") in exclude_kinds:
            continue
        dims = sorted([p["sx"], p["sy"], p["sz"]])
        thick, W, L = dims[0], dims[1], dims[2]
        key = (p["defn"], round(L), round(W), round(thick), p["material"], p["grain"])
        groups[key] = groups.get(key, 0) + 1
    parts = []
    for (defn, L, W, thick, mat, grain), qty in groups.items():
        parts.append(dict(name=defn, qty=qty, length=L, width=W, material=mat, grain=grain))
    return parts


# Fallback board-stock sheet for solid lumber / unknown material ids (mm).
# Deliberately generous board length, narrow width — a "does it fit a board"
# check, not a nesting plan. Flagged in the emitted material note.
_BOARD_FALLBACK = {"sheet": [2000, 240], "kerf": 3, "trim": 5}


def _material_entry(material_id, thickness):
    """Build one cutlist.py materials-catalog entry for a (material, thickness),
    pulling the real sheet/board size from assets/materials.json across all catalog
    sections, and falling back to board stock for unknown ids."""
    thick_label = int(thickness) if float(thickness).is_integer() else thickness
    ent_id = f"{material_id}_{thick_label}"
    info = material_info(material_id)
    if info and info.get("sheet"):
        he = info.get("he", "")
        name = f"{material_id} {thick_label}mm" + (f" / {he}" if he else "")
        if info["is_board"]:
            name += " (solid — edge-glue wide parts)"
            kerf, trim = 3, 5
        else:
            kerf, trim = 4, 10
        return dict(id=ent_id, name=name, thickness=thickness,
                    sheet=list(info["sheet"]), kerf=kerf, trim=trim)
    # unknown id: board-stock fallback
    fb = _BOARD_FALLBACK
    return dict(id=ent_id, name=f"{material_id} {thick_label}mm (board stock — verify)",
                thickness=thickness, sheet=list(fb["sheet"]), kerf=fb["kerf"], trim=fb["trim"])


def cutlist_spec(spec, banding=None, notes=None, exclude_kinds=_CUTLIST_EXCLUDE,
                 project=None, units="mm"):
    """Bridge the positioned-part spec to the full JSON cutlist.py consumes.

    Unlike cutlist_parts(), this produces the WHOLE document: a materials catalog
    (auto-split by (material_id, thickness) so one nominal material can appear at
    several thicknesses — white-oak veneer at 30 and 20, ply at 20 and 15, etc.),
    per-part banding/notes, and checks.overall — so the LLM supplies only the
    judgement calls (which edges get banded, part notes) and never the arithmetic.

    banding / notes: optional dicts keyed by part `defn` name, e.g.
        banding={"Top": ["front"], "Side": ["front"]}, notes={"Side": "sys-32"}.
    Non-cut parts (rods, fixtures) are excluded by `kind`.
    """
    banding = banding or {}
    notes = notes or {}
    groups = {}   # (defn, L, W, thick, mat_id, grain) -> qty
    mat_thick = {}  # material_id -> set of thicknesses actually used
    defn_note = {}  # defn -> first non-empty part note (e.g. "APPLIED false front")
    for p in spec["parts"]:
        if p.get("kind") in exclude_kinds:
            continue
        dims = sorted([p["sx"], p["sy"], p["sz"]])
        thick, W, L = dims[0], dims[1], dims[2]
        thick_r = round(thick, 1)
        key = (p["defn"], round(L), round(W), thick_r, p["material"], p["grain"])
        groups[key] = groups.get(key, 0) + 1
        mat_thick.setdefault(p["material"], set()).add(thick_r)
        if p.get("note") and p["defn"] not in defn_note:
            defn_note[p["defn"]] = p["note"]

    # materials catalog: one entry per (material_id, thickness)
    materials_out, ent_id_for = [], {}
    for mat_id in sorted(mat_thick):
        for thick in sorted(mat_thick[mat_id]):
            ent = _material_entry(mat_id, thick)
            ent_id_for[(mat_id, thick)] = ent["id"]
            materials_out.append(ent)

    parts_out = []
    for (defn, L, W, thick, mat_id, grain), qty in groups.items():
        part = dict(name=defn, qty=qty, length=L, width=W,
                    material=ent_id_for[(mat_id, thick)], grain=grain)
        if defn in banding:
            part["banding"] = banding[defn]
        # explicit notes= override wins; otherwise carry the part's own note
        # (so drawers()' "APPLIED false front" annotation reaches the cut list)
        if defn in notes:
            part["notes"] = notes[defn]
        elif defn in defn_note:
            part["notes"] = defn_note[defn]
        parts_out.append(part)

    O = spec.get("overall", {})
    out = dict(project=project or spec.get("name", "(untitled)"), units=units,
               materials=materials_out, parts=parts_out)
    if O:
        out["checks"] = {"overall": {"width": O.get("W"), "height": O.get("H"),
                                     "depth": O.get("D")}}
    return out


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


def check_facade_coverage(spec, face="front", max_gap=5, plane_tol=30):
    """Catch visible holes in a facade — the class of bug where a short center
    divider (stopped to clear a mechanism) leaves a gap between two drawer fronts
    that nothing else covers.

    The visible facade plane (front = max Z) is tiled by every part whose outer
    face lies within `plane_tol` mm of it (fronts, rails, stiles, legs, applied
    panels). Any rectangular hole larger than `max_gap` on BOTH axes, inside the
    region bounded by the outermost members, is reported. Reveal lines (thin gaps)
    pass; real holes fail. Coarse row-scan on a `max_gap` grid — enough to catch
    the class, not a pixel-exact occlusion test.

    Returns a list of human-readable warning strings (does not raise). face may be
    "front" (XY plane at max Z), "back" (XY at min Z), "left"/"right" (ZY planes).
    """
    parts = [p for p in spec["parts"] if p.get("kind") != "rod"]
    if not parts:
        return []

    # Pick projection: (u,v) plane coords + the depth axis and its outer edge.
    def extents(p):
        return {"x": (p["x"], p["x"] + p["sx"]), "y": (p["y"], p["y"] + p["sy"]),
                "z": (p["z"], p["z"] + p["sz"])}

    if face in ("front", "back"):
        ua, va, da = "x", "y", "z"
    elif face in ("left", "right"):
        ua, va, da = "z", "y", "x"
    else:
        raise ValueError(f"unknown face {face!r}")

    all_d = [extents(p)[da] for p in parts]
    plane = max(hi for _, hi in all_d) if face in ("front", "right") else min(lo for lo, _ in all_d)

    rects = []
    for p in parts:
        e = extents(p)
        lo, hi = e[da]
        near = (abs(hi - plane) <= plane_tol) if face in ("front", "right") else (abs(lo - plane) <= plane_tol)
        if near:
            rects.append((e[ua][0], e[ua][1], e[va][0], e[va][1]))
    if not rects:
        return []

    umin = min(r[0] for r in rects); umax = max(r[1] for r in rects)
    vmin = min(r[2] for r in rects); vmax = max(r[3] for r in rects)

    step = float(max_gap)
    nu = max(1, int(round((umax - umin) / step)))
    nv = max(1, int(round((vmax - vmin) / step)))
    # covered[i][j]: cell centered at (umin+(i+.5)step, vmin+(j+.5)step)
    covered = [[False] * nv for _ in range(nu)]
    for i in range(nu):
        uc = umin + (i + 0.5) * step
        for j in range(nv):
            vc = vmin + (j + 0.5) * step
            for (u0, u1, v0, v1) in rects:
                if u0 <= uc <= u1 and v0 <= vc <= v1:
                    covered[i][j] = True
                    break

    # flood-fill connected uncovered cells, report bounding boxes bigger than max_gap on both axes
    seen = [[False] * nv for _ in range(nu)]
    warnings = []
    for i in range(nu):
        for j in range(nv):
            if covered[i][j] or seen[i][j]:
                continue
            stack = [(i, j)]; seen[i][j] = True
            imin = imax = i; jmin = jmax = j
            while stack:
                ci, cj = stack.pop()
                imin, imax = min(imin, ci), max(imax, ci)
                jmin, jmax = min(jmin, cj), max(jmax, cj)
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ni, nj = ci + di, cj + dj
                    if 0 <= ni < nu and 0 <= nj < nv and not covered[ni][nj] and not seen[ni][nj]:
                        seen[ni][nj] = True; stack.append((ni, nj))
            hole_u = (imax - imin + 1) * step
            hole_v = (jmax - jmin + 1) * step
            if hole_u > max_gap and hole_v > max_gap:
                cu = umin + (imin) * step
                cv = vmin + (jmin) * step
                warnings.append(
                    f"{face} facade: uncovered hole ~{hole_u:.0f}x{hole_v:.0f}mm near "
                    f"({ua}={cu:.0f}, {va}={cv:.0f}) — a front/rail/stile/leg may be "
                    f"missing or stopped short (reveals under {max_gap}mm are ignored)")
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
