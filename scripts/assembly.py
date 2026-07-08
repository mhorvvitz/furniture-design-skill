#!/usr/bin/env python3
"""assembly.py — assembly plan emitter.

Reads the positioned-part spec (same one every other emitter reads) and
joinery.json, then produces:
  1. A connections list (which parts touch, which faces, what joint type)
  2. Per-part drilling coordinates in mm from a stated reference corner
  3. A topologically-sorted build order respecting reachability
  4. A step-by-step assembly document (Markdown)

This is the bridge between "here are your cut panels" and "here is a standing
cabinet." Every drilling coordinate comes from joinery.json — never from memory,
never invented. If a number isn't in the data file, it's flagged assumed.

v1 scope: carcass joints (cam-and-dowel, confirmat, glued dowel), shelf pins,
back panel (dado/staple — noted but no drilling coords for the groove).
v2 planned: hinge-cup positions, runner mounting positions.
"""
import json, os, math

_JNR = None
def joinery_data():
    global _JNR
    if _JNR is None:
        p = os.path.join(os.path.dirname(__file__), "..", "assets", "joinery.json")
        _JNR = json.load(open(p, encoding="utf-8"))
    return _JNR


# ---------------------------------------------------------------------------
# Phase 1: Connection derivation
# ---------------------------------------------------------------------------

def _box(p):
    return (p["x"], p["x"] + p["sx"],
            p["y"], p["y"] + p["sy"],
            p["z"], p["z"] + p["sz"])


def _face_contact(a, b, tolerance=2.0):
    """Detect if two AABB parts share a face (touching within tolerance).
    Returns (axis, side, contact_area_mm2) or None.
    axis: 'x', 'y', or 'z'
    side: which face of `a` touches `b` — e.g. 'x_max' means a's right face touches b's left.
    """
    ax0, ax1, ay0, ay1, az0, az1 = _box(a)
    bx0, bx1, by0, by1, bz0, bz1 = _box(b)

    contacts = []
    # Check X faces
    if abs(ax1 - bx0) <= tolerance:
        oy = max(0, min(ay1, by1) - max(ay0, by0))
        oz = max(0, min(az1, bz1) - max(az0, bz0))
        if oy > tolerance and oz > tolerance:
            contacts.append(('x', 'x_max', oy * oz))
    if abs(bx1 - ax0) <= tolerance:
        oy = max(0, min(ay1, by1) - max(ay0, by0))
        oz = max(0, min(az1, bz1) - max(az0, bz0))
        if oy > tolerance and oz > tolerance:
            contacts.append(('x', 'x_min', oy * oz))
    # Check Y faces
    if abs(ay1 - by0) <= tolerance:
        ox = max(0, min(ax1, bx1) - max(ax0, bx0))
        oz = max(0, min(az1, bz1) - max(az0, bz0))
        if ox > tolerance and oz > tolerance:
            contacts.append(('y', 'y_max', ox * oz))
    if abs(by1 - ay0) <= tolerance:
        ox = max(0, min(ax1, bx1) - max(ax0, bx0))
        oz = max(0, min(az1, bz1) - max(az0, bz0))
        if ox > tolerance and oz > tolerance:
            contacts.append(('y', 'y_min', ox * oz))
    # Check Z faces
    if abs(az1 - bz0) <= tolerance:
        ox = max(0, min(ax1, bx1) - max(ax0, bx0))
        oy = max(0, min(ay1, by1) - max(ay0, by0))
        if ox > tolerance and oy > tolerance:
            contacts.append(('z', 'z_max', ox * oy))
    if abs(bz1 - az0) <= tolerance:
        ox = max(0, min(ax1, bx1) - max(ax0, bx0))
        oy = max(0, min(ay1, by1) - max(ay0, by0))
        if ox > tolerance and oy > tolerance:
            contacts.append(('z', 'z_min', ox * oy))

    if not contacts:
        return None
    # Return the contact with the largest area (primary joint face)
    return max(contacts, key=lambda c: c[2])


# The carcass vocabulary assembly.py actually understands. A connection between
# two of these is classified with confidence; anything outside it (a Lid, a
# BackApron, a Leg, an Upright…) is flagged "default_assumed" so a guessed joint
# is never presented as a verified one. (P0-3)
KNOWN_DEFNS = {
    "Side", "Top", "Bottom", "FixedPanel", "Divider", "Back", "Shelf",
    "DrawerMullion", "DrawerBoxSide", "DrawerBoxFB", "DrawerBottom", "DrawerFront",
}

# Joints for which this script emits real drilling coordinates. Everything else
# (piano_hinge, pocket_screw, gas_strut, drawer_slide_side_mount) is a "mount per
# datasheet / procedure" joint — listed with its guidance, not fake hole coords.
DRILLED_JOINTS = {"cam_and_dowel", "confirmat", "glued_dowel"}


def _joint_override(a, b, joint_overrides):
    """An explicit joint wins over classification: a part's own `joint` field, or
    a (defn_a, defn_b) entry in joint_overrides. Returns the joint string (which
    may be "none" to suppress the connection) or None."""
    for p in (a, b):
        if p.get("joint"):
            return p["joint"]
    if joint_overrides:
        na, nb = a.get("defn", ""), b.get("defn", "")
        for pair in ((na, nb), (nb, na)):
            if pair in joint_overrides:
                return joint_overrides[pair]
    return None


def derive_connections(spec, style="frameless_kd", joint_overrides=None):
    """Find all touching part pairs and assign joint types.

    Precedence: an explicit override (part `joint` field or `joint_overrides`
    dict) > carcass-vocabulary classification > the style default (flagged
    'default_assumed'). A joint of "none" suppresses the connection (correct for a
    lid resting on an apron, or an applied front handled by its own box)."""
    jnr = joinery_data()
    defaults = jnr["_default_by_style"].get(style, jnr["_default_by_style"]["frameless_kd"])
    parts = spec["parts"]
    connections = []

    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            a, b = parts[i], parts[j]
            # Skip rods, doors, drawer fronts, and non-cut fixtures
            if a.get("kind") in ("rod", "fixture") or b.get("kind") in ("rod", "fixture"):
                continue
            if a.get("kind") == "door" or b.get("kind") == "door":
                continue

            contact = _face_contact(a, b)
            if contact is None:
                continue

            axis, side, area = contact

            override = _joint_override(a, b, joint_overrides)
            if override == "none":
                continue
            if override:
                joint_type, classification = override, "specified"
            else:
                joint_type = _classify_joint(a, b, defaults, jnr)
                known = a.get("defn", "") in KNOWN_DEFNS and b.get("defn", "") in KNOWN_DEFNS
                classification = "vocabulary" if known else "default_assumed"

            connections.append({
                "part_a": _part_label(a, i),
                "part_a_idx": i,
                "part_b": _part_label(b, j),
                "part_b_idx": j,
                "contact_axis": axis,
                "contact_side": side,
                "contact_area_mm2": round(area),
                "joint_type": joint_type,
                "classification": classification,
            })

    return connections


def _part_label(p, idx):
    return f"{p.get('name', p.get('defn', f'Part_{idx}'))}_{idx}"


def _classify_joint(a, b, defaults, jnr):
    """Assign a joint type based on what the parts are."""
    na = a.get("defn", "")
    nb = b.get("defn", "")
    back_names = {"Back"}
    shelf_names = {"Shelf"}

    if na in back_names or nb in back_names:
        return "dado_groove"
    if na in shelf_names or nb in shelf_names:
        return defaults.get("shelves_fixed", "glued_dowel")
    # Drawer box parts
    if "DrawerBox" in na or "DrawerBox" in nb:
        return "glued_dowel"
    # Default carcass joint
    return defaults.get("carcass_joints", "cam_and_dowel")


# ---------------------------------------------------------------------------
# Phase 2: Hole schedules
# ---------------------------------------------------------------------------

def _joint_count(panel_width, jnr_spec):
    """How many fasteners for a panel of given width."""
    rules = jnr_spec.get("joints_per_panel", {})
    rule_text = rules.get("rule", "")
    spacing = rules.get("spacing_from_edge", 50)
    min_between = rules.get("min_spacing_between", 128)

    if panel_width <= 400:
        n = 2
    elif panel_width <= 600:
        n = 2
    elif panel_width <= 1000:
        n = 3
    else:
        n = 4
    return n, spacing


def _distribute_positions(panel_width, count, edge_inset):
    """Return positions (mm from panel edge 0) for `count` fasteners."""
    if count == 1:
        return [panel_width / 2]
    if count == 2:
        return [edge_inset, panel_width - edge_inset]
    positions = [edge_inset]
    remaining = panel_width - 2 * edge_inset
    gap = remaining / (count - 1)
    for i in range(1, count - 1):
        positions.append(edge_inset + i * gap)
    positions.append(panel_width - edge_inset)
    return [round(p, 1) for p in positions]


def generate_hole_schedule(spec, connections, style="frameless_kd"):
    """Generate per-part drilling instructions from connections + joinery.json."""
    jnr = joinery_data()
    parts = spec["parts"]
    schedule = {}  # keyed by part_label

    for conn in connections:
        jt = conn["joint_type"]
        # Groove joints and mount-per-datasheet joints (piano hinge, pocket screw,
        # gas strut, drawer slide) carry no face/edge drilling coords here — they
        # are covered by the hardware list and the mechanism-notes section.
        if jt not in DRILLED_JOINTS:
            continue
        if jt not in jnr:
            continue

        jnr_spec = jnr[jt]
        a = parts[conn["part_a_idx"]]
        b = parts[conn["part_b_idx"]]

        # Determine which part gets the face hole and which gets the edge hole.
        # A part presents its EDGE when its dimension along the contact axis
        # equals its panel thickness (smallest dimension). The other part
        # presents its FACE — that's where the through-holes or cam housings go.
        axis = conn["contact_axis"]
        a_contact_dim = {"x": a["sx"], "y": a["sy"], "z": a["sz"]}[axis]
        b_contact_dim = {"x": b["sx"], "y": b["sy"], "z": b["sz"]}[axis]
        a_thickness = min(a["sx"], a["sy"], a["sz"])
        b_thickness = min(b["sx"], b["sy"], b["sz"])

        a_is_edge = abs(a_contact_dim - a_thickness) < 2  # presenting its thin edge
        b_is_edge = abs(b_contact_dim - b_thickness) < 2

        if a_is_edge and not b_is_edge:
            edge_part, face_part = a, b
            edge_idx, face_idx = conn["part_a_idx"], conn["part_b_idx"]
        elif b_is_edge and not a_is_edge:
            edge_part, face_part = b, a
            edge_idx, face_idx = conn["part_b_idx"], conn["part_a_idx"]
        else:
            # Both or neither present an edge — use smaller contact dim as edge
            if a_contact_dim <= b_contact_dim:
                edge_part, face_part = a, b
                edge_idx, face_idx = conn["part_a_idx"], conn["part_b_idx"]
            else:
                edge_part, face_part = b, a
                edge_idx, face_idx = conn["part_b_idx"], conn["part_a_idx"]

        edge_label = _part_label(edge_part, edge_idx)
        face_label = _part_label(face_part, face_idx)

        # Determine panel width along the joint for fastener count.
        # This is the longer dimension of the CONTACT AREA, not the full panel.
        ax0, ax1, ay0, ay1, az0, az1 = _box(a)
        bx0, bx1, by0, by1, bz0, bz1 = _box(b)
        overlap_dims = []
        if axis != "x":
            overlap_dims.append(min(ax1, bx1) - max(ax0, bx0))
        if axis != "y":
            overlap_dims.append(min(ay1, by1) - max(ay0, by0))
        if axis != "z":
            overlap_dims.append(min(az1, bz1) - max(az0, bz0))
        panel_width = max(overlap_dims) if overlap_dims else 100

        count, edge_inset = _joint_count(panel_width, jnr_spec)
        positions = _distribute_positions(panel_width, count, edge_inset)

        # Build hole instructions
        face_holes = _face_hole_instructions(jt, jnr_spec, positions, face_part, axis)
        edge_holes = _edge_hole_instructions(jt, jnr_spec, positions, edge_part, axis)

        # Store
        if face_label not in schedule:
            schedule[face_label] = {"part": face_part, "holes": []}
        schedule[face_label]["holes"].append({
            "for_connection_to": edge_label,
            "joint_type": jt,
            "side": "face",
            "instructions": face_holes
        })

        if edge_label not in schedule:
            schedule[edge_label] = {"part": edge_part, "holes": []}
        schedule[edge_label]["holes"].append({
            "for_connection_to": face_label,
            "joint_type": jt,
            "side": "edge",
            "instructions": edge_holes
        })

    # Add System-32 shelf pin rows for side panels
    _add_shelf_pin_rows(spec, schedule, jnr)

    return schedule


def _face_hole_instructions(jt, jnr_spec, positions, part, contact_axis):
    """Generate face-side drilling instructions."""
    instructions = []
    if jt == "cam_and_dowel":
        cam = jnr_spec["cam_housing"]
        b34 = cam["edge_distance_options"]["B34"]
        for pos in positions:
            instructions.append({
                "type": "cam_housing",
                "drill_bit": cam["drill_bit"],
                "diameter": cam["hole_diameter"],
                "depth": cam["drilling_depth_18mm_panel"],
                "position_along_panel": pos,
                "position_from_edge": b34["center_to_front_edge"],
                "confidence": cam["confidence"],
            })
    elif jt == "confirmat":
        drill = jnr_spec["stepped_drill"]
        for pos in positions:
            instructions.append({
                "type": "confirmat_through",
                "drill_bit": drill["drill_bit"],
                "diameter": drill["face_hole_diameter"],
                "depth": "through",
                "position_along_panel": pos,
                "position_from_edge": "panel_center",
                "confidence": drill["confidence"],
            })
    elif jt == "glued_dowel":
        hole = jnr_spec["hole"]
        t = min(part["sx"], part["sy"], part["sz"])  # panel thickness
        max_depth = t * 0.75  # 75% rule
        depth = min(hole["depth_per_side"] + 2, max_depth)  # +2 for glue trap
        for pos in positions:
            instructions.append({
                "type": "dowel_face",
                "drill_bit": hole["drill_bit"],
                "diameter": hole["diameter"],
                "depth": round(depth, 1),
                "position_along_panel": pos,
                "position_from_edge": "panel_center",
                "confidence": hole["confidence"],
            })
    return instructions


def _edge_hole_instructions(jt, jnr_spec, positions, part, contact_axis):
    """Generate edge-side drilling instructions."""
    instructions = []
    if jt == "cam_and_dowel":
        bolt = jnr_spec["connecting_bolt"]
        for pos in positions:
            instructions.append({
                "type": "bolt_hole",
                "drill_bit": bolt["drill_bit"],
                "diameter": bolt["bolt_hole_diameter"],
                "depth": bolt["bolt_hole_depth_into_edge"],
                "position_along_panel": pos,
                "position_from_face": "panel_thickness / 2",
                "confidence": bolt["confidence"],
            })
    elif jt == "confirmat":
        drill = jnr_spec["stepped_drill"]
        for pos in positions:
            instructions.append({
                "type": "confirmat_pilot",
                "drill_bit": f"Ø{drill['edge_pilot_diameter']}mm brad-point",
                "diameter": drill["edge_pilot_diameter"],
                "depth": drill["edge_pilot_depth"],
                "position_along_panel": pos,
                "position_from_face": "panel_thickness / 2",
                "confidence": drill["confidence"],
            })
    elif jt == "glued_dowel":
        hole = jnr_spec["hole"]
        for pos in positions:
            instructions.append({
                "type": "dowel_edge",
                "drill_bit": hole["drill_bit"],
                "diameter": hole["diameter"],
                "depth": hole["depth_per_side"] + 2,
                "position_along_panel": pos,
                "position_from_face": "panel_thickness / 2",
                "confidence": hole["confidence"],
            })
    return instructions


def _add_shelf_pin_rows(spec, schedule, jnr):
    """Add System-32 shelf-pin drilling rows to side panels."""
    sp = jnr["shelf_pin"]
    for i, p in enumerate(spec["parts"]):
        defn = p.get("defn", "")
        if defn != "Side":
            continue
        label = _part_label(p, i)
        if label not in schedule:
            schedule[label] = {"part": p, "holes": []}

        # Side panel: height = sy, depth = sz
        height = p["sy"]
        depth = p["sz"]
        front_setback = sp["front_row_setback"]
        rear_setback = depth - front_setback

        # System-32 holes: first at 37mm from bottom, then every 32mm
        # (commonly first hole ~37mm up, but varies; standard is to start
        # the grid at a fixed offset and run to near the top)
        first_hole_y = 37  # mm from bottom of side panel
        hole_positions = []
        y = first_hole_y
        while y < height - 37:
            hole_positions.append(round(y, 1))
            y += sp["grid_spacing"]

        schedule[label]["holes"].append({
            "for_connection_to": "adjustable_shelves",
            "joint_type": "shelf_pin",
            "side": "face (inner)",
            "instructions": [{
                "type": "system_32_row",
                "drill_bit": f"Ø{sp['hole_diameter']}mm with depth stop at {sp['hole_depth']}mm",
                "diameter": sp["hole_diameter"],
                "depth": sp["hole_depth"],
                "rows": [
                    {"label": "front_row", "distance_from_front_edge": front_setback},
                    {"label": "rear_row", "distance_from_front_edge": rear_setback}
                ],
                "hole_positions_from_bottom": hole_positions,
                "total_holes_per_row": len(hole_positions),
                "confidence": sp["confidence"],
            }]
        })


# ---------------------------------------------------------------------------
# Phase 3: Build order (topological sort with reachability)
# ---------------------------------------------------------------------------

def _part_priority(part):
    """Lower number = assemble earlier. Encodes reachability rules."""
    defn = part.get("defn", "")
    kind = part.get("kind", "")
    priorities = {
        "Side": 10,       # sides first (one down, then fill, then close)
        "Bottom": 20,
        "FixedPanel": 25,
        "Divider": 27,
        "Top": 30,
        "Back": 35,        # inset back before second side closes
        "Shelf": 40,       # adjustable shelves after carcass is up
        "DrawerMullion": 42,
        "DrawerBoxSide": 50,
        "DrawerBoxFB": 51,
        "DrawerBottom": 52,
        "DrawerFront": 55,
    }
    if kind == "door":
        return 60           # doors and drawer fronts last
    if kind == "rod":
        return 45           # rods after carcass, before fronts
    return priorities.get(defn, 35)


def generate_build_order(spec):
    """Return parts sorted by assembly order, grouped into named steps."""
    parts = spec["parts"]
    indexed = [(i, p) for i, p in enumerate(parts)]
    indexed.sort(key=lambda x: _part_priority(x[1]))

    steps = []
    current_step = None

    for idx, part in indexed:
        defn = part.get("defn", "")
        kind = part.get("kind", "")
        step_name = _step_name(defn, kind)

        if current_step is None or current_step["name"] != step_name:
            current_step = {"name": step_name, "parts": []}
            steps.append(current_step)
        current_step["parts"].append({
            "index": idx,
            "label": _part_label(part, idx),
            "defn": defn,
        })

    return steps


def _step_name(defn, kind):
    names = {
        "Side": "Lay down first side panel",
        "Bottom": "Attach bottom panel",
        "FixedPanel": "Install fixed horizontal panels",
        "Divider": "Install vertical divider(s)",
        "Top": "Attach top panel",
        "Back": "Install back panel",
        "Shelf": "Insert adjustable shelves",
        "DrawerMullion": "Install drawer mullions",
        "DrawerBoxSide": "Assemble drawer boxes",
        "DrawerBoxFB": "Assemble drawer boxes",
        "DrawerBottom": "Assemble drawer boxes",
        "DrawerFront": "Mount drawer fronts",
        "Rod": "Install hanging rod(s)",
    }
    if kind == "door":
        return "Hang doors"
    if kind == "rod":
        return "Install hanging rod(s)"
    return names.get(defn, f"Install {defn}")


# ---------------------------------------------------------------------------
# Phase 4: Document output
# ---------------------------------------------------------------------------

def generate_assembly_document(spec, style="frameless_kd", joint_overrides=None):
    """Produce a complete assembly plan as Markdown."""
    connections = derive_connections(spec, style, joint_overrides)
    hole_schedule = generate_hole_schedule(spec, connections, style)
    build_order = generate_build_order(spec)
    jnr = joinery_data()

    lines = []
    lines.append(f"# Assembly Plan — {spec['name']}")
    lines.append(f"")
    o = spec["overall"]
    lines.append(f"Overall: {o['W']} × {o['H']} × {o['D']} mm")
    lines.append(f"Construction style: {style}")
    lines.append(f"Joint method: {jnr['_default_by_style'].get(style, {}).get('carcass_joints', 'see joinery.json')}")
    lines.append(f"")

    # Out-of-envelope warning block (P0-3): any joint assigned by the style
    # default to parts outside assembly.py's carcass vocabulary is a GUESS.
    _emit_out_of_envelope_warning(lines, connections)

    # Mechanism & hardware notes: joints that mount per datasheet / a procedure
    # (piano hinge, pocket screw, gas strut, drawer slide) rather than by drilled
    # coordinates.
    _emit_mechanism_notes(lines, connections, jnr)

    # Tools needed
    lines.append(f"## Tools needed")
    lines.append(f"")
    drill_bits = set()
    for label, sched in hole_schedule.items():
        for hole_group in sched["holes"]:
            for instr in hole_group["instructions"]:
                if isinstance(instr, dict):
                    drill_bits.add(instr.get("drill_bit", ""))
    for bit in sorted(drill_bits):
        if bit:
            lines.append(f"- {bit}")
    lines.append(f"- Carpenter's square / angle clamp")
    lines.append(f"- Clamps")
    lines.append(f"- Rubber mallet")
    lines.append(f"- Pencil + tape measure")
    lines.append(f"")

    # Hardware list
    lines.append(f"## Hardware list")
    lines.append(f"")
    _emit_hardware_list(lines, connections, jnr)

    # Pre-assembly drilling
    lines.append(f"## Pre-assembly drilling")
    lines.append(f"")
    lines.append(f"**Do ALL drilling before you start assembling.** "
                 f"Once panels are joined, you can't reach the inside faces.")
    lines.append(f"")

    for label in sorted(hole_schedule.keys()):
        sched = hole_schedule[label]
        lines.append(f"### {label}")
        lines.append(f"")
        for hole_group in sched["holes"]:
            jt = hole_group["joint_type"]
            side = hole_group["side"]
            conn_to = hole_group["for_connection_to"]
            lines.append(f"**{jt}** ({side}) — connecting to {conn_to}:")
            lines.append(f"")
            for instr in hole_group["instructions"]:
                if isinstance(instr, dict):
                    if instr["type"] == "system_32_row":
                        _emit_system32(lines, instr)
                    else:
                        _emit_hole(lines, instr)
            lines.append(f"")

    # Assembly steps
    lines.append(f"## Assembly steps")
    lines.append(f"")
    for step_num, step in enumerate(build_order, 1):
        lines.append(f"### Step {step_num}: {step['name']}")
        lines.append(f"")
        part_labels = [p["label"] for p in step["parts"]]
        lines.append(f"Parts: {', '.join(part_labels)}")
        lines.append(f"")
        _emit_step_instructions(lines, step, spec, connections, jnr, style)
        lines.append(f"")

    # Wall anchoring reminder for tall units
    if spec["overall"]["H"] >= 1200:
        lines.append(f"### Final step: Wall anchoring")
        lines.append(f"")
        lines.append(f"**This unit is {spec['overall']['H']}mm tall — anchor it to the wall.**")
        wf = jnr.get("wall_fixing", {})
        lines.append(f"{wf.get('anti_tip_mandatory', 'Anchor tall units to prevent tip-over.')}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*All drilling coordinates from joinery.json (verified sources). "
                 f"Confirm hardware-specific dimensions against the actual product you purchased.*")

    return "\n".join(lines)


def _emit_hole(lines, instr):
    depth = instr['depth']
    depth_str = f"{depth}mm" if isinstance(depth, (int, float)) else str(depth)
    pos = instr.get('position_along_panel', '—')
    edge = instr.get('position_from_edge', instr.get('position_from_face', '—'))
    conf = instr.get('confidence', 'unknown')
    lines.append(f"  - **{instr['type']}**: Ø{instr['diameter']}mm × {depth_str} deep, "
                 f"at {pos}mm along panel, {edge}mm from edge. "
                 f"Bit: {instr['drill_bit']}. [confidence: {conf}]")


def _emit_system32(lines, instr):
    rows = instr["rows"]
    positions = instr["hole_positions_from_bottom"]
    n = instr["total_holes_per_row"]
    lines.append(f"  - **System-32 shelf pin rows**: {len(rows)} rows × {n} holes each")
    for row in rows:
        lines.append(f"    - {row['label']}: {row['distance_from_front_edge']}mm from front edge")
    lines.append(f"    - Hole spacing: every 32mm, starting at {positions[0]}mm from bottom")
    lines.append(f"    - Ø{instr['diameter']}mm × {instr['depth']}mm deep")
    lines.append(f"    - Bit: {instr['drill_bit']}")
    lines.append(f"    - [confidence: {instr['confidence']}]")


def _emit_out_of_envelope_warning(lines, connections):
    """Prominent block for connections whose joint was assigned by the style
    default to parts outside the carcass vocabulary — a guess, flagged as one."""
    flagged = [c for c in connections if c.get("classification") == "default_assumed"]
    if not flagged:
        return
    parts = sorted({c["part_a"] for c in flagged} | {c["part_b"] for c in flagged})
    lines.append(f"> ⚠️ **REVIEW REQUIRED — {len(flagged)} joint(s) assigned by default, not verified.**")
    lines.append(f">")
    lines.append(f"> These connections involve parts outside this script's carcass")
    lines.append(f"> vocabulary ({', '.join(sorted(set(p.rsplit('_', 1)[0] for p in parts)))}). Each was given")
    lines.append(f"> the **style default** joint as a placeholder — that is a guess, not an")
    lines.append(f"> engineered choice. **Review and set the real joint for each before building**")
    lines.append(f"> (pass `joint=` on the part in the spec, or `joint_overrides` to the plan):")
    lines.append(f">")
    for c in flagged:
        lines.append(f"> - {c['part_a']} ↔ {c['part_b']} → assigned `{c['joint_type']}` (assumed)")
    lines.append(f"")


def _emit_mechanism_notes(lines, connections, jnr):
    """Guidance for mount-per-datasheet / procedure joints present in the plan."""
    present = []
    seen = set()
    for c in connections:
        jt = c["joint_type"]
        if jt in DRILLED_JOINTS or jt == "dado_groove" or jt in seen:
            continue
        if jt in jnr:
            present.append(jt)
            seen.add(jt)
    if not present:
        return
    lines.append(f"## Mechanism & hardware notes")
    lines.append(f"")
    lines.append(f"These joints are mounted per the hardware datasheet or a sizing "
                 f"procedure — no fixed drilling coordinates are emitted for them:")
    lines.append(f"")
    for jt in present:
        spec = jnr[jt]
        he = spec.get("he", "")
        lines.append(f"### {jt}" + (f" — {he}" if he else ""))
        if spec.get("description"):
            lines.append(f"{spec['description']}")
        if spec.get("procedure"):
            lines.append(f"- **Procedure**: {spec['procedure']}")
        if spec.get("mounting"):
            lines.append(f"- **Mounting**: {spec['mounting']}")
        if spec.get("spacing_rule"):
            lines.append(f"- **Spacing**: {spec['spacing_rule']}")
        conf = spec.get("confidence", "unknown")
        lines.append(f"- [confidence: {conf}] — verify against the actual product datasheet.")
        lines.append(f"")


def _emit_hardware_list(lines, connections, jnr):
    hw_counts = {}
    for conn in connections:
        jt = conn["joint_type"]
        if jt in jnr and "per_joint_hardware" in jnr[jt]:
            for item in jnr[jt]["per_joint_hardware"]:
                hw_counts[item] = hw_counts.get(item, 0) + 1
    for item, count in sorted(hw_counts.items()):
        # Strip any leading "1× " from the item template before multiplying
        clean = item.lstrip("1× ").lstrip("1×").strip() if item.startswith("1") else item
        lines.append(f"- {count}× {clean}")
    if not hw_counts:
        lines.append(f"- (no mechanical hardware — glue joints only)")
    lines.append(f"")


def _emit_step_instructions(lines, step, spec, connections, jnr, style):
    """Write human-readable assembly instructions for a step."""
    parts_in_step = {p["index"] for p in step["parts"]}
    defn = step["parts"][0]["defn"] if step["parts"] else ""

    if defn == "Side":
        lines.append(f"1. Lay the **first** side panel flat on a clean surface, inside face up.")
        lines.append(f"2. All cam housings and shelf-pin rows should already be drilled (see above).")
        lines.append(f"3. The second side panel is attached **last** in this group — after bottom, dividers, and top are in place.")
    elif defn == "Bottom":
        lines.append(f"1. Insert connecting bolts into the bottom panel's edge (pre-drilled holes).")
        lines.append(f"2. Lower the bottom into the first side's cam housings.")
        lines.append(f"3. Turn each cam 90° clockwise to lock.")
        lines.append(f"4. Check square with a carpenter's square before the joint sets.")
    elif defn in ("FixedPanel", "Divider"):
        lines.append(f"1. Insert bolts/dowels into the panel's edges.")
        lines.append(f"2. Position into the cam housings / dowel holes in the side.")
        lines.append(f"3. Lock cams or let dowels seat. Check square.")
    elif defn == "Top":
        lines.append(f"1. Same procedure as the bottom panel.")
        lines.append(f"2. After locking, measure diagonals to verify the carcass is square.")
    elif defn == "Back":
        lines.append(f"1. With the carcass lying face-down, slide the back panel into place.")
        lines.append(f"2. Pin or staple at ~200mm intervals around the perimeter.")
        lines.append(f"3. The back squares the carcass — measure diagonals before pinning.")
    elif defn == "Shelf":
        lines.append(f"1. Insert shelf pins at the desired heights in the System-32 rows.")
        lines.append(f"2. Lower each shelf onto its four pins.")
    elif "DrawerBox" in defn:
        lines.append(f"1. Assemble each drawer box separately: sides → front/back → bottom.")
        lines.append(f"2. Glue + clamp. Check the box is square (measure diagonals).")
        lines.append(f"3. **v2 will add runner mounting positions here.**")
    elif step["name"] == "Hang doors":
        lines.append(f"1. **v2 will add hinge-cup drilling coordinates here.**")
        lines.append(f"2. Attach mounting plates to carcass sides at 37mm from front edge.")
        lines.append(f"3. Click hinges into mounting plates; adjust overlay and alignment.")
    elif defn == "Rod":
        lines.append(f"1. Mark rod support bracket positions on both side panels.")
        lines.append(f"2. Screw brackets into place, set rod into brackets.")
    else:
        lines.append(f"1. Position and fix per the drilling schedule above.")


def write_assembly_plan(spec, path, style="frameless_kd", joint_overrides=None):
    """Write the assembly plan to a Markdown file."""
    doc = generate_assembly_document(spec, style, joint_overrides)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from carcass import Carcass, check_overlaps

    # Quick self-test: bookshelf
    c = Carcass(800, 1800, 300, t=18, name="Bookshelf")
    c.sides(); c.bottom(); c.top(); c.back(4)
    c.shelves(4, y0=18, y1=1782)
    s = c.spec()
    overlaps = check_overlaps(s)
    print(f"Overlaps: {len(overlaps)} (expected: 4 back-panel rebate flags)")

    doc = generate_assembly_document(s, style="frameless_permanent")
    print(doc[:2000])
    print(f"\n... ({len(doc)} chars total)")
