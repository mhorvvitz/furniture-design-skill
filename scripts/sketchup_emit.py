#!/usr/bin/env python3
"""sketchup_emit.py — SketchUp build_model emitter.

Reads the positioned-part spec (carcass.py) and emits a Python string to run
verbatim via the SketchUp MCP's `build_model` tool. Deferred entirely to the
SDK's documented namespace and the sketchup-components skill's own patterns —
no invented API.

TWO SEAMS THIS FILE EXISTS TO GET RIGHT:

1. UNITS: spec is mm; build_model is inches-only. All positions/sizes go through
   mm()/25.4 at emission time, once, here — never inline elsewhere.
2. AXES: spec uses X=width, Y=height(up), Z=depth. SketchUp's SDK uses
   X=width, Y=depth, Z=height(up). So (x, y, z) in the spec maps to
   (X=x, Y=z, Z=y) in SketchUp, and box size (sx, sy, sz) maps to
   make_quad_box(sx, sz, sy). Getting this backwards builds correctly-SIZED
   geometry lying on its back. This mapping happens in exactly one place below.

Known v1 simplifications (flagged, not hidden):
- Rod cross-section is round (r=11mm / 22mm diameter) via a true lofted cylinder
  — matches the "oval steel rod" spec loosely (round, not oval), a deliberate
  simplification, not a placeholder.
- Style preset (Furniture / Product Studio) and hero-shot camera are the real
  values from the sketchup-styles / sketchup-camera skills, applied verbatim.
"""
from collections import OrderedDict

# Legacy fallback palette; live colours come from assets/materials.json via
# carcass.material_color, so a new material added to the data file shows up here
# without editing this map.
_MATCOLORS = {
    "plywood_birch": (220, 195, 154), "plywood_okoume": (216, 180, 140),
    "plywood_poplar": (217, 199, 162), "melamine": (238, 236, 230),
    "mdf": (217, 205, 184), "hardboard": (205, 180, 136), "steel": (184, 188, 194),
}


def _emit_mat(p):
    """The material key a part is COLOURED by in the model. Fixtures render in a
    single muted 'fixture' tone regardless of their real material."""
    return "fixture" if p.get("kind") == "fixture" else p["material"]


def _color_for(mat):
    """Resolve an emit-material key to an (r,g,b), preferring the data file."""
    try:
        from carcass import material_color, fixture_default_color
    except Exception:
        try:
            from .carcass import material_color, fixture_default_color
        except Exception:
            material_color = lambda *a, **k: None
            fixture_default_color = lambda: (58, 58, 62)
    if mat == "fixture":
        return tuple(int(c) for c in fixture_default_color())
    c = material_color(mat)
    if c:
        return tuple(int(x) for x in c)
    return _MATCOLORS.get(mat, (200, 195, 185))

_HELPERS = '''
IN = 25.4
def mm(v): return v / IN

def make_quad_box(w, d, h):
    geom = GeometryInput()
    geom.set_vertices([
        SUPoint3D(0,0,0), SUPoint3D(w,0,0), SUPoint3D(w,d,0), SUPoint3D(0,d,0),
        SUPoint3D(0,0,h), SUPoint3D(w,0,h), SUPoint3D(w,d,h), SUPoint3D(0,d,h)
    ])
    for fv in [[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7],[4,5,6,7],[0,3,2,1]]:
        loop = LoopInput()
        for i in fv: loop.add_vertex_index(i)
        _, geom = geom.add_face(loop)
    return geom

def get_or_create_material(name, r, g, b, a=255):
    existing = {m.get_name(): m for m in model.get_materials()}
    if name in existing:
        return existing[name]
    mat = Material()
    mat.set_name(name)
    mat.set_color(SUColor(r, g, b, a))
    model.add_materials([mat])
    return mat

def get_or_create_definition(name):
    for d in model.get_component_definitions():
        if d.get_name() == name:
            return d, False
    cd = ComponentDefinition()
    cd.set_name(name)
    model.add_component_definitions([cd])
    return cd, True

def apply_material_to_def(cd, mat):
    for face in cd.get_entities().get_faces():
        face.set_front_material(mat)
        face.set_back_material(mat)

# --- true-cylinder helpers (rods), from the sketchup-clean-geometry /
# sketchup-components skills verbatim, not reinvented ---
def circle_pts(cx, cy, cz, r, n=12):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(SUPoint3D(cx + r * math.cos(a), cy + r * math.sin(a), cz))
    return pts

def skin_rings(geom, ring_b, ring_t, n):
    for j in range(n):
        j2 = (j + 1) % n
        lp = LoopInput()
        lp.add_vertex_index(ring_b[j]); lp.add_vertex_index(ring_b[j2]); lp.add_vertex_index(ring_t[j2])
        _, geom = geom.add_face(lp)
        lp2 = LoopInput()
        lp2.add_vertex_index(ring_b[j]); lp2.add_vertex_index(ring_t[j2]); lp2.add_vertex_index(ring_t[j])
        _, geom = geom.add_face(lp2)
    return geom

def cap_ngon(geom, ring_indices, rev=False):
    loop = LoopInput()
    idxs = list(reversed(ring_indices)) if rev else ring_indices
    for i in idxs:
        loop.add_vertex_index(i)
    _, geom = geom.add_face(loop)
    return geom

def cap_circle_edges(geom, start_vertex_idx, center, normal, n):
    _, _, geom = geom.add_arc_curve(start_vertex_idx, start_vertex_idx, center, normal, n)
    return geom

def build_lofted_solid(profile, n=12):
    geom = GeometryInput()
    all_verts = []
    rings = []
    last_i = len(profile) - 1
    for i, (h, r) in enumerate(profile):
        if r == 0 and (i == 0 or i == last_i):
            all_verts.append(SUPoint3D(0, 0, h))
            rings.append(('pole', len(all_verts) - 1))
        else:
            ring_start = len(all_verts)
            all_verts.extend(circle_pts(0, 0, h, r, n))
            rings.append(('ring', list(range(ring_start, ring_start + n))))
    geom.set_vertices(all_verts)
    for i, (kind, payload) in enumerate(rings):
        if kind != 'ring':
            continue
        h = profile[i][0]
        normal = SUVector3D(0, 0, -1) if i == 0 else SUVector3D(0, 0, 1)
        geom = cap_circle_edges(geom, payload[0], SUPoint3D(0, 0, h), normal, n)
    for i in range(len(rings) - 1):
        a_kind, a_pay = rings[i]
        b_kind, b_pay = rings[i + 1]
        if a_kind == 'ring' and b_kind == 'ring':
            geom = skin_rings(geom, a_pay, b_pay, n)
    first_kind, first_pay = rings[0]
    if first_kind == 'ring':
        geom = cap_ngon(geom, first_pay, rev=True)
    last_kind, last_pay = rings[-1]
    if last_kind == 'ring':
        geom = cap_ngon(geom, last_pay, rev=False)
    return geom

def clean_geometry_on_entities(ents, profile, erase_threshold=0.9999):
    cap_heights = {round(profile[0][0], 4), round(profile[-1][0], 4)}
    preserve_heights = set(cap_heights)
    for _ in range(500):
        found = False
        for edge in ents.get_edges():
            faces = edge.get_faces()
            if len(faces) == 2:
                n0 = faces[0].get_normal()
                n1 = faces[1].get_normal()
                dot = n0.x*n1.x + n0.y*n1.y + n0.z*n1.z
                if dot > erase_threshold:
                    ents.erase_entities([edge])
                    found = True
                    break
        if not found:
            break
    for edge in ents.get_edges():
        faces = edge.get_faces()
        if len(faces) == 2:
            edge.set_soft(True)
            edge.set_smooth(True)
    for edge in ents.get_edges():
        sv = edge.get_start_vertex().get_position()
        ev = edge.get_end_vertex().get_position()
        sv_z = round(sv.z, 4)
        ev_z = round(ev.z, 4)
        if abs(sv_z - ev_z) < 0.0005 and sv_z in preserve_heights:
            edge.set_soft(False)
            edge.set_smooth(False)
'''

def _defn_names(parts):
    """Group parts by (defn, rounded geometry, material). Same defn name used for
    two different geometries gets auto-suffixed (_A/_B) so SketchUp definitions
    stay unambiguous, even if the caller reused a defn label sloppily."""
    geo_groups = OrderedDict()
    for p in parts:
        if p.get("kind") == "rod":
            continue
        key = (p["defn"], round(p["sx"], 1), round(p["sy"], 1), round(p["sz"], 1), _emit_mat(p))
        geo_groups.setdefault(key, []).append(p)
    base_to_keys = OrderedDict()
    for key in geo_groups:
        base_to_keys.setdefault(key[0], []).append(key)
    name_for_key = {}
    for base, keys in base_to_keys.items():
        if len(keys) == 1:
            name_for_key[keys[0]] = base
        else:
            for i, k in enumerate(keys):
                name_for_key[k] = f"{base}_{chr(65+i)}"
    return geo_groups, name_for_key


def emit(spec, piece_var="Piece"):
    O = spec["overall"]
    parts = spec["parts"]
    geo_groups, name_for_key = _defn_names(parts)
    # every emit-material used by a non-rod part (fixtures map to 'fixture'),
    # plus 'steel' when any rod is present (rods are always steel).
    materials_used = {_emit_mat(p) for p in parts if p.get("kind") != "rod"}
    if any(p.get("kind") == "rod" for p in parts):
        materials_used.add("steel")

    lines = [_HELPERS, ""]
    lines.append("# --- materials ---")
    lines.append("_mats = {}")
    for m in sorted(materials_used):
        r, g, b = _color_for(m)
        lines.append(f'_mats[{m!r}] = get_or_create_material({m!r}, {r}, {g}, {b})')
    lines.append("")
    lines.append(f'top = Group()')
    lines.append(f'model.get_entities().add_group(top)')
    lines.append(f'top.set_name({spec["name"]!r})')
    lines.append("")
    lines.append("# --- component definitions + instances ---")
    lines.append("_inst_counts = {}")
    for key, plist in geo_groups.items():
        defn_label, sx, sy, sz, mat = key
        su_name = name_for_key[key]
        lines.append(f'cd, is_new = get_or_create_definition({su_name!r})')
        lines.append("if is_new:")
        lines.append(f'    cd.get_entities().fill(make_quad_box(mm({sx}), mm({sz}), mm({sy})), weld_vertices=True)')
        lines.append(f'    apply_material_to_def(cd, _mats[{mat!r}])')
        for i, p in enumerate(plist):
            iname = f'{defn_label}_{i+1:02d}'
            # AXIS REMAP: spec (x,y,z) -> SketchUp (X=x, Y=z, Z=y)
            lines.append(
                f'inst = cd.create_instance(); inst.set_name({iname!r}); '
                f'inst.set_transform(SUTransformation([1,0,0,0, 0,1,0,0, 0,0,1,0, '
                f'mm({p["x"]}), mm({p["z"]}), mm({p["y"]}), 1])); '
                f'top.get_entities().add_instance(inst)'
            )
        lines.append(f'_inst_counts[{su_name!r}] = cd.get_num_instances()')
        lines.append("")

    rods = [p for p in parts if p.get("kind") == "rod"]
    if rods:
        lines.append("# --- rods: true round cylinder (build_lofted_solid), r=11mm ---")
        lines.append("cd, is_new = get_or_create_definition('Rod')")
        lines.append("if is_new:")
        lines.append("    _rod_profile = [(0, mm(11)), (1, mm(11))]")
        lines.append("    cd.get_entities().fill(build_lofted_solid(_rod_profile, n=12), weld_vertices=True)")
        lines.append("    clean_geometry_on_entities(cd.get_entities(), _rod_profile)")
        lines.append("    apply_material_to_def(cd, _mats['steel'])")
        for i, p in enumerate(rods):
            # Ry(90deg) maps local Z (length axis of the unit lofted solid) to world X;
            # local-Z column is scaled by L=mm(length) to set the rod's real length.
            # Verified numerically offline: L=mm(573)=>22.559in=573mm exactly (see LIMITATIONS.md).
            # Centerline = spec corner + half the 22mm cross-section (rod() stores a corner, not a center).
            lines.append(
                f'inst = cd.create_instance(); inst.set_name("Rod_{i+1:02d}"); '
                f'inst.set_transform(SUTransformation([0,0,-1,0, 0,1,0,0, mm({p["sx"]}),0,0,0, '
                f'mm({p["x"]}), mm({p["z"]+11}), mm({p["y"]+11}), 1])); '
                f'top.get_entities().add_instance(inst)'
            )
        lines.append("")

    # --- style: Furniture / Product Studio preset (from sketchup-styles presets.md, verbatim values) ---
    lines.append("# --- style: Furniture / Product Studio preset ---")
    lines.append("_DEFAULTS_RO = {")
    lines.append("    'EDGE_DISPLAY_MODE': TypedValue(int_value=1), 'EDGE_COLOR_MODE': TypedValue(int_value=0),")
    lines.append("    'RENDER_MODE': TypedValue(int_value=2), 'MODEL_TRANSPARENCY': TypedValue(bool_value=False),")
    lines.append("    'DRAW_DEPTH_QUE': TypedValue(bool_value=False), 'DEPTH_QUE_WIDTH': TypedValue(int_value=2),")
    lines.append("    'DRAW_SILHOUETTES': TypedValue(bool_value=True), 'SILHOUETTE_WIDTH': TypedValue(int_value=2),")
    lines.append("    'DRAW_HORIZON': TypedValue(bool_value=False), 'DRAW_GROUND': TypedValue(bool_value=False),")
    lines.append("    'DISPLAY_SKETCH_AXES': TypedValue(bool_value=False),")
    lines.append("    'HIGHLIGHT_COLOR': TypedValue(color_value=SUColor(0,1,255,255)),")
    lines.append("    'LOCKED_COLOR': TypedValue(color_value=SUColor(255,0,0,255)),")
    lines.append("}")
    lines.append("_FURNITURE_STUDIO_RO = {")
    lines.append("    'BACKGROUND_COLOR': TypedValue(color_value=SUColor(214,216,218,255)),")
    lines.append("    'FACE_FRONT_COLOR': TypedValue(color_value=SUColor(245,240,230,255)),")
    lines.append("    'FACE_BACK_COLOR': TypedValue(color_value=SUColor(180,178,170,255)),")
    lines.append("    'FOREGROUND_COLOR': TypedValue(color_value=SUColor(50,48,45,255)),")
    lines.append("    'DEPTH_QUE_WIDTH': TypedValue(int_value=1),")
    lines.append("    'AMBIENT_OCCLUSION': TypedValue(bool_value=True),")
    lines.append("    'AMBIENT_OCCLUSION_DISTANCE': TypedValue(float_value=12.0),")
    lines.append("    'AMBIENT_OCCLUSION_INTENSITY': TypedValue(float_value=0.5),")
    lines.append("    'AMBIENT_OCCLUSION_MULTIPLIER': TypedValue(float_value=1.2),")
    lines.append("}")
    lines.append("_FURNITURE_STUDIO_SI = {'DISPLAY_SHADOWS': TypedValue(bool_value=True),")
    lines.append("    'LIGHT': TypedValue(int_value=80), 'DARK': TypedValue(int_value=60)}")
    lines.append("ro = model.get_rendering_options()")
    lines.append("for _k, _v in {**_DEFAULTS_RO, **_FURNITURE_STUDIO_RO}.items():")
    lines.append("    ro[RenderingOptionKey[_k]] = _v")
    lines.append("si = model.get_shadow_info()")
    lines.append("for _k, _v in _FURNITURE_STUDIO_SI.items():")
    lines.append("    si[ShadowInfoKey[_k]] = _v")
    lines.append("")

    lines.append("# --- bounding box cross-check vs spec (catches unit/axis errors) ---")
    lines.append("bb = top.get_bounding_box()")
    lines.append("bb_w_mm = (bb.max_point[0]-bb.min_point[0]) * IN")
    lines.append("bb_d_mm = (bb.max_point[1]-bb.min_point[1]) * IN")
    lines.append("bb_h_mm = (bb.max_point[2]-bb.min_point[2]) * IN")
    lines.append("")

    # --- camera: real hero-shot recipe from sketchup-camera skill, FOV-aware, discrete object ---
    lines.append("# --- camera: hero shot, FOV-aware framing (sketchup-camera skill recipe) ---")
    lines.append("xmin, ymin, zmin = bb.min_point[0], bb.min_point[1], bb.min_point[2]")
    lines.append("xmax, ymax, zmax = bb.max_point[0], bb.max_point[1], bb.max_point[2]")
    lines.append("cx, cy, cz = (xmin+xmax)/2.0, (ymin+ymax)/2.0, (zmin+zmax)/2.0")
    lines.append("w, d, h = xmax-xmin, ymax-ymin, zmax-zmin")
    lines.append("fov = 32.0")
    lines.append("azimuth_rad, elevation_rad = math.radians(45), math.radians(30)")
    lines.append("dir_x = math.cos(azimuth_rad) * math.cos(elevation_rad)")
    lines.append("dir_y = -math.sin(azimuth_rad) * math.cos(elevation_rad)")
    lines.append("dir_z = math.sin(elevation_rad)")
    lines.append("right_len = math.sqrt(dir_x**2 + dir_y**2)")
    lines.append("right_x, right_y, right_z = -dir_y/right_len, dir_x/right_len, 0.0")
    lines.append("up_x = dir_y*right_z - dir_z*right_y")
    lines.append("up_y = dir_z*right_x - dir_x*right_z")
    lines.append("up_z = dir_x*right_y - dir_y*right_x")
    lines.append("horizontal_extent = abs(right_x)*w + abs(right_y)*d + abs(right_z)*h")
    lines.append("vertical_extent = abs(up_x)*w + abs(up_y)*d + abs(up_z)*h")
    lines.append("aspect_ratio = 1.6")
    lines.append("half_vfov = math.radians(fov/2.0)")
    lines.append("half_hfov = math.atan(aspect_ratio * math.tan(half_vfov))")
    lines.append("dist_v = (vertical_extent/2.0) / math.tan(half_vfov)")
    lines.append("dist_h = (horizontal_extent/2.0) / math.tan(half_hfov)")
    lines.append("dist = max(dist_v, dist_h) * 1.25")
    lines.append("eye = SUPoint3D(cx + dist*dir_x, cy + dist*dir_y, cz + dist*dir_z)")
    lines.append("target = SUPoint3D(cx, cy, zmin + h*0.4)")
    lines.append("cam = Camera()")
    lines.append("cam.set_orientation(eye, target, SUVector3D(0,0,1))")
    lines.append("cam.enable_perspective()")
    lines.append("cam.set_perspective_frustum_fov(fov)")
    lines.append("model.set_camera(cam)")
    lines.append("_check_cam = model.get_camera()")
    lines.append("_orient = _check_cam.get_orientation()")
    lines.append("_cam_ok = _check_cam.is_perspective() and _check_cam.get_perspective_frustum_fov() > 0")
    lines.append("")
    lines.append("result = {")
    lines.append('    "instances": _inst_counts,')
    lines.append('    "bbox_mm_expected": {"W": %r, "H": %r, "D": %r},' % (O["W"], O["H"], O["D"]))
    lines.append('    "bbox_mm_actual": {"W": round(bb_w_mm,1), "H": round(bb_h_mm,1), "D": round(bb_d_mm,1)},')
    lines.append('    "camera_ok": _cam_ok,')
    lines.append('    "camera_fov": _check_cam.get_perspective_frustum_fov(),')
    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys, ast
    sys.path.insert(0, ".")
    from carcass import Carcass
    c = Carcass(800, 1800, 300, t=18, name="Bookshelf")
    c.sides(); c.bottom(); c.top(); c.back(4); c.shelves(4, y0=18, y1=1782)
    code = emit(c.spec())
    ast.parse(code)  # syntax-only check; SDK namespace isn't available locally
    open("/tmp/bookshelf_build.py", "w").write(code)
    print("emitted /tmp/bookshelf_build.py — syntax OK (SDK calls unexecuted locally)")
    print(f"{len(code.splitlines())} lines")
