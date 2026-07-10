#!/usr/bin/env python3
"""blender_render.py — photoreal product-shot emitter (Blender Cycles).

Reads the positioned-part spec (same one draw.py / render.py / cutlist read) and
renders a store-grade still: path-traced light, procedural wood grain, soft
studio shadow, hero 3/4 camera. This is the optional tier above the three.js
preview — for online-store listings, not for design iteration (Cycles is slow;
iterate in draw.py/render.py, shoot here once the design is signed off).

Requires the `bpy` wheel (Blender as a Python module, ~1 GB installed — which is
why it is an *optional* dependency and NOT vendored in this repo):

    pip install bpy        # needs Python 3.11; pulls Blender 4/5 headless

Usage:
    python3 scripts/blender_render.py examples/bookshelf/bookshelf_spec.py out.png
    python3 scripts/blender_render.py spec.json out.png --res 1600x2000 --samples 256
    python3 scripts/blender_render.py spec.py out.png --transparent   # alpha cutout
    python3 scripts/blender_render.py spec.py out.png --frames 12     # 360° spin set

Importable: `render_photo(spec, path, **opts)`.

Conventions shared with the other emitters:
  * spec axes: x = width, y = up, z = depth (front = high z). Internally mapped
    to Blender's Z-up (X=x, Y=z, Z=y) and mm -> metres so lighting physics read
    true.
  * colours come from assets/materials.json `rgb` — add a material there and it
    propagates here like it does to draw.py/render.py/sketchup_emit.py.
  * `motion` dicts are ignored — the still renders the closed state. Use
    render.py's articulated preview for open-state checks.
  * `kind="rod"` renders as a steel cylinder, `kind="fixture"` as a muted matte
    box; neither gets wood grain.

The render is for the listing photo, not measurement — the carpenter still
builds from the dimensioned 2D drawings and the cut list.
"""
import argparse
import importlib.util
import json
import math
import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
MATERIALS_JSON = os.path.join(SCRIPTS_DIR, "..", "assets", "materials.json")

MM = 0.001  # spec mm -> Blender metres

# Material ids that are flat sheet faces (no visible grain), vs everything
# woody, which gets the procedural grain treatment.
FLAT_SHEETS = {"melamine", "mdf", "hardboard", "osb"}
METALS = {"steel"}
FIXTURE_RGB = (58, 58, 62)


# ---------------------------------------------------------------- spec loading

def load_spec(path):
    """Accept a spec .json, or a .py module exposing `spec`/`build()` (same
    contract as package.py)."""
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    spec_import = importlib.util.spec_from_file_location("project_spec", path)
    mod = importlib.util.module_from_spec(spec_import)
    sys.path.insert(0, SCRIPTS_DIR)
    spec_import.loader.exec_module(mod)
    if hasattr(mod, "build"):
        return mod.build()
    spec = getattr(mod, "spec", None)
    if callable(spec):
        return spec()
    if isinstance(spec, dict):
        return spec
    raise SystemExit(f"{path}: module must expose `spec` (dict or callable) or `build()`")


def material_rgbs():
    """material id -> (r,g,b) 0-255, walked from every section of materials.json."""
    out = {}
    try:
        with open(MATERIALS_JSON, encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        return out

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, dict) and isinstance(v.get("rgb"), list):
                    out[k] = tuple(v["rgb"])
                walk(v)
    walk(data)
    return out


def srgb_to_linear(rgb255):
    def chan(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(chan(c) for c in rgb255)


# ---------------------------------------------------------------- scene build

def _wood_material(bpy, name, rgb, grained):
    """Principled material; woody ids get subtle procedural grain + bump."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    lin = srgb_to_linear(rgb)
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55 if grained else 0.62
    if not grained:
        return mat

    # grain: wave bands distorted by noise, darkening the base colour slightly,
    # plus a faint bump so raking light catches it
    tex = nt.nodes.new("ShaderNodeTexCoord")
    # squash coords across the grain so the wave bands stretch into long
    # streaks along x (the grain run used by the cut list)
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (0.6, 14.0, 14.0)
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Y"
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 4.0
    wave.inputs["Detail"].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (*[c * 0.6 for c in lin], 1.0)
    ramp.color_ramp.elements[1].color = (*lin, 1.0)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.02

    nt.links.new(tex.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(wave.outputs["Color"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _metal_material(bpy, name, rgb):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*srgb_to_linear(rgb), 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.32
    return mat


def _get_material(bpy, cache, mid, rgbs):
    if mid in cache:
        return cache[mid]
    rgb = rgbs.get(mid, (216, 198, 154))
    if mid == "fixture":
        m = _wood_material(bpy, mid, FIXTURE_RGB, grained=False)
    elif mid in METALS:
        m = _metal_material(bpy, mid, rgb)
    else:
        m = _wood_material(bpy, mid, rgb, grained=mid not in FLAT_SHEETS)
    cache[mid] = m
    return m


def _look_at(obj, target):
    import mathutils
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_scene(bpy, spec, transparent=False):
    """Parts, studio light, ground, camera. Returns (piece_root, camera)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    rgbs = material_rgbs()
    mats = {}

    O = spec["overall"]
    W, H, D = O["W"] * MM, O["H"] * MM, O["D"] * MM
    root = bpy.data.objects.new("Piece", None)
    scene.collection.objects.link(root)

    for p in spec["parts"]:
        # spec (x,y,z)+(sx,sy,sz), min corner -> Blender centre, Z-up
        cx = (p["x"] + p["sx"] / 2) * MM
        cy = (p["z"] + p["sz"] / 2) * MM
        cz = (p["y"] + p["sy"] / 2) * MM
        if p.get("kind") == "rod":
            bpy.ops.mesh.primitive_cylinder_add(
                radius=p["sy"] / 2 * MM, depth=p["sx"] * MM, vertices=48,
                location=(cx, cy, cz), rotation=(0, math.pi / 2, 0))
            obj = bpy.context.object
            obj.data.materials.append(_get_material(bpy, mats, "steel", rgbs))
        else:
            bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
            obj = bpy.context.object
            obj.scale = (p["sx"] * MM, p["sz"] * MM, p["sy"] * MM)
            bpy.ops.object.transform_apply(scale=True)
            mid = "fixture" if p.get("kind") == "fixture" else p["material"]
            obj.data.materials.append(_get_material(bpy, mats, mid, rgbs))
            # 0.6 mm bevel so panel edges catch highlights — most of what makes
            # a box read as a real object instead of CAD
            bev = obj.modifiers.new("bevel", "BEVEL")
            bev.width = 0.0006
            bev.segments = 2
        obj.name = p.get("name", "part")
        obj.parent = root

    # ground — shadow catcher when cutting out, seamless white cyc otherwise
    bpy.ops.mesh.primitive_plane_add(size=60, location=(W / 2, D / 2, 0))
    ground = bpy.context.object
    ground.name = "Ground"
    if transparent:
        ground.is_shadow_catcher = True
    else:
        gm = bpy.data.materials.new("ground")
        gm.use_nodes = True
        g = gm.node_tree.nodes["Principled BSDF"]
        g.inputs["Base Color"].default_value = (0.92, 0.915, 0.90, 1.0)
        g.inputs["Roughness"].default_value = 0.9
        ground.data.materials.append(gm)

    # world + 3-light studio rig, scaled to the piece
    world = bpy.data.worlds.new("studio")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.28

    S = max(W, H, D)

    def area(name, loc, target, power, size):
        light = bpy.data.lights.new(name, "AREA")
        light.energy = power
        light.size = size
        ob = bpy.data.objects.new(name, light)
        ob.location = loc
        scene.collection.objects.link(ob)
        _look_at(ob, target)
        return ob

    centre = (W / 2, D / 2, H / 2)
    area("key", (W / 2 - S * 1.6, D / 2 + S * 2.2, H + S * 1.2), centre, 300 * S * S, S * 2.2)
    area("fill", (W / 2 + S * 2.0, D / 2 + S * 1.4, H * 0.7), centre, 120 * S * S, S * 2.5)
    area("rim", (W / 2 + S * 0.8, D / 2 - S * 2.0, H + S * 1.5), centre, 200 * S * S, S * 1.5)

    # hero 3/4 camera, front-left, slightly above, framed to the bbox
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    diag = math.sqrt(W * W + H * H + D * D)
    dist = (diag / 2) / math.tan(cam_data.angle / 2) * 1.35
    direction = (-0.62, 1.0, 0.42)
    n = math.sqrt(sum(c * c for c in direction))
    cam.location = tuple(c + dist * d / n for c, d in zip(centre, direction))
    _look_at(cam, centre)
    return root, cam


def setup_render(bpy, path, res=(1200, 1500), samples=128, transparent=False):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
    scene.view_settings.exposure = 0.0
    scene.render.filepath = path


def render_photo(spec, path, res=(1200, 1500), samples=128, transparent=False, frames=1):
    """Render the spec to `path`. frames>1 renders a 360° turntable set as
    path_000.png ... path_NNN.png (for a store spin viewer)."""
    try:
        import bpy
    except ImportError:
        raise SystemExit(
            "blender_render.py needs the `bpy` module (Blender headless, ~1 GB, "
            "Python 3.11). Install with:  pip install bpy")

    root, _cam = build_scene(bpy, spec, transparent=transparent)
    setup_render(bpy, path, res=res, samples=samples, transparent=transparent)

    if frames <= 1:
        bpy.ops.render.render(write_still=True)
        return [path]

    base, ext = os.path.splitext(path)
    out = []
    for i in range(frames):
        # rotate the piece about its own vertical axis, not the world origin
        O = spec["overall"]
        pivot = (O["W"] * MM / 2, O["D"] * MM / 2)
        ang = 2 * math.pi * i / frames
        root.rotation_euler = (0, 0, ang)
        root.location = (
            pivot[0] - (pivot[0] * math.cos(ang) - pivot[1] * math.sin(ang)),
            pivot[1] - (pivot[0] * math.sin(ang) + pivot[1] * math.cos(ang)), 0)
        fp = f"{base}_{i:03d}{ext}"
        bpy.context.scene.render.filepath = fp
        bpy.ops.render.render(write_still=True)
        out.append(fp)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("spec", help="spec .json, or .py exposing spec/build()")
    ap.add_argument("out", help="output .png")
    ap.add_argument("--res", default="1200x1500", help="WxH px (default 1200x1500, 4:5 listing)")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--transparent", action="store_true",
                    help="alpha background + shadow catcher (store cutout)")
    ap.add_argument("--frames", type=int, default=1,
                    help=">1: render a 360-degree turntable set")
    a = ap.parse_args()
    w, h = a.res.lower().split("x")
    spec = load_spec(a.spec)
    files = render_photo(spec, a.out, res=(int(w), int(h)), samples=a.samples,
                         transparent=a.transparent, frames=a.frames)
    for f in files:
        print("wrote", f)


if __name__ == "__main__":
    main()
