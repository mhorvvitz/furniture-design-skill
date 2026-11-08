#!/usr/bin/env python3
"""Render a still hero image from render.html — the PNG used on the landing page.

DERIVED, not drawn: this screenshots the project's own three.js render, so the
image on the landing page is the same geometry as every other output. Nothing
here edits the model; it only sets up one frame — lid fully open, drawers shut,
three-quarter view — and tunes the presentation for a still.

Why the presentation differs from the live viewer: render.py lights the scene for
an orbitable preview (key light 2.1, exposure 1.05). On a still of a pale oak
piece that blows the wood out to near-white, so exposure and key intensity are
dropped and the material colours deepened. The background is pushed ABOVE 1.0
because it passes through ACES tone mapping too — plain 0xffffff comes out grey
at this exposure.

Needs Chrome (SwiftShader is fine — no GPU required). Note the rAF stub: the
render loop calls requestAnimationFrame forever, which starves Chrome's
--virtual-time-budget and hangs the capture. Stubbing it makes the page draw
exactly one frame and then go idle.

    python examples/coffee_table/make_render_png.py
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

SRC = os.path.join(HERE, "render.html")
OUT = os.path.join(HERE, "render.png")

# One deterministic hero frame. Lighting and materials are NOT touched — the
# still must look like the live viewer. The only presentation change is a white
# backdrop so the image drops cleanly into the landing page's white card; the
# value is pushed far above 1.0 because it still passes through ACES tone
# mapping, where a plain 0xffffff lands around 0xdadada.
OVERRIDE = """
<style>#ui,#cap{display:none!important}</style>
<script>
for (var i = 0; i < 200; i++) {
  mgroups.lid.userData.tgt = 1; mgroups.drawers.userData.tgt = 0; animateMotion();
}
scene.background.setRGB(30.0, 30.0, 30.0);
ground.material.color.setRGB(26.0, 26.0, 26.0);
R.setSize(1400, 1000, false);
cam.aspect = 1.4; cam.updateProjectionMatrix();
tgt.set(630, 430, 330); az = -0.70; pol = 1.14; rad = 2320;
place(); R.render(scene, cam);
</script>
</body>"""


def main():
    import packet  # reuse the skill's browser discovery
    browser = packet.find_browser()
    if not browser:
        raise SystemExit("no Chrome/Edge found — cannot render the still")

    html = open(SRC, encoding="utf-8").read()
    # Stub rAF BEFORE the page's own script, so its loop runs one frame only.
    html = html.replace(
        '<script src="https://cdnjs',
        '<script>window.requestAnimationFrame=function(){return 0;};</script>\n'
        '<script src="https://cdnjs', 1)
    html = html.replace("</body>", OVERRIDE)

    tmpdir = tempfile.mkdtemp(prefix="ct_render_")
    page = os.path.join(tmpdir, "shot.html")
    raw = os.path.join(tmpdir, "raw.png")
    with open(page, "w", encoding="utf-8") as f:
        f.write(html)

    subprocess.run([browser, "--headless", "--disable-gpu",
                    "--enable-unsafe-swiftshader", f"--screenshot={raw}",
                    "--window-size=1400,1000", "--hide-scrollbars",
                    "--virtual-time-budget=20000", "file:///" + page.replace("\\", "/")],
                   capture_output=True, timeout=180)
    if not os.path.exists(raw):
        raise SystemExit("Chrome produced no screenshot")

    try:
        from PIL import Image, ImageChops
    except ImportError:
        import shutil
        shutil.copy(raw, OUT)
        print(f"wrote {OUT} (uncropped — install Pillow to trim)")
        return

    im = Image.open(raw).convert("RGB")
    flat = Image.new("RGB", im.size, im.getpixel((5, 5)))
    mask = ImageChops.difference(im, flat).convert("L").point(lambda v: 255 if v > 10 else 0)
    box = mask.getbbox()
    m = 26
    box = (max(0, box[0] - m), max(0, box[1] - m),
           min(im.size[0], box[2] + m), min(im.size[1], box[3] + m))
    im = im.crop(box)
    w = 1200
    im = im.resize((w, round(im.size[1] * w / im.size[0])), Image.LANCZOS)
    im.save(OUT, optimize=True)
    print(f"wrote {OUT} {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
