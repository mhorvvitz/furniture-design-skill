#!/usr/bin/env python3
"""packet.py — assemble the builder packet into one print-clean PDF.

Stage 5 of the skill delegates the PDF to a `pdf` skill that does not exist in
Claude Code (SKILL.md / deliverables.md). This is the emitter that replaces it,
so no project has to hand-roll a shop-drawing packet again.

It takes the artifacts the other emitters already produce — dimensioned SVG views
(draw.py / render), the cut-list markdown (cutlist.py --format md), and the
hardware / assembly markdown (assembly.py) — wraps them in an A4-landscape,
print-clean HTML document with a title block, and shells out to headless
Chrome/Edge to print it to PDF. No external Python deps: the markdown→HTML
converter is built in (headings, GFM tables, lists, bold/italic/code, blockquotes,
rules — the subset deliverable markdown actually uses).

If no browser is found the HTML is still written and IS a shippable deliverable —
open it and Ctrl-P → Save as PDF. The PDF step is a convenience, not a dependency.

Usage:
  python3 packet.py -o output/packet.pdf \
      --project "Hidden-TV coffee table" --overall 1260x420x720 --rev "Rev B" \
      --views output/plan.svg output/front.svg output/side.svg \
      --md output/cutlist.md output/assembly.md output/hardware.md \
      --legend "white_oak=White oak solid; white_oak_veneer=White-oak veneer ply"

  python3 packet.py ... --html-only         # write the HTML, skip the browser
  python3 packet.py ... --browser /path/to/chrome
"""
import argparse
import datetime
import html as _html
import os
import re
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------
# Markdown -> HTML  (deliverable subset: headings, GFM tables, lists, inline
# spans, blockquotes, hr, paragraphs). Small on purpose — not a full CommonMark
# implementation, just what cutlist.py / assembly.py actually emit.
# ---------------------------------------------------------------------------

def _inline(text):
    """Inline spans on already-escaped text: `code`, **bold**, *italic*."""
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def _row_cells(line):
    """Split a GFM table row into cells, dropping the outer pipes."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_divider(line):
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def md_to_html(md):
    """Convert a markdown string to an HTML fragment."""
    lines = md.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)
    list_stack = []  # ('ul'|'ol')

    def close_lists(to=0):
        while len(list_stack) > to:
            out.append(f"</{list_stack.pop()}>")

    while i < n:
        line = lines[i]
        raw = line.rstrip()

        # blank line: close any open lists, paragraph break
        if not raw.strip():
            close_lists()
            i += 1
            continue

        # horizontal rule
        if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", raw):
            close_lists()
            out.append("<hr/>")
            i += 1
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", raw)
        if m:
            close_lists()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(_html.escape(m.group(2).strip()))}</h{lvl}>")
            i += 1
            continue

        # GFM table: header row + divider row
        if raw.lstrip().startswith("|") and i + 1 < n and _is_divider(lines[i + 1]):
            close_lists()
            header = _row_cells(raw)
            out.append('<table><thead><tr>')
            for c in header:
                out.append(f"<th>{_inline(_html.escape(c))}</th>")
            out.append("</tr></thead><tbody>")
            i += 2
            while i < n and lines[i].lstrip().startswith("|"):
                cells = _row_cells(lines[i])
                out.append("<tr>")
                for c in cells:
                    out.append(f"<td>{_inline(_html.escape(c))}</td>")
                out.append("</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        # blockquote (collapse consecutive > lines into one block)
        if raw.lstrip().startswith(">"):
            close_lists()
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            inner = "<br/>".join(_inline(_html.escape(b)) for b in buf)
            out.append(f"<blockquote>{inner}</blockquote>")
            continue

        # unordered / ordered list item
        mu = re.match(r"^(\s*)([-*+])\s+(.*)$", raw)
        mo = re.match(r"^(\s*)(\d+)\.\s+(.*)$", raw)
        if mu or mo:
            kind = "ul" if mu else "ol"
            content = (mu or mo).group(3)
            if not list_stack or list_stack[-1] != kind:
                # switch/open a list of this kind at the top level (flat — nested
                # lists are rare in these docs and render acceptably flat)
                close_lists()
                out.append(f"<{kind}>")
                list_stack.append(kind)
            out.append(f"<li>{_inline(_html.escape(content))}</li>")
            i += 1
            continue

        # plain paragraph (accumulate until blank/structural line)
        close_lists()
        buf = [raw]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>|\||-{3,}\s*$)", lines[i]):
            buf.append(lines[i].rstrip())
            i += 1
        para = " ".join(buf)
        out.append(f"<p>{_inline(_html.escape(para))}</p>")

    close_lists()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _svg_block(path):
    """Inline an SVG file so the HTML is fully self-contained. Strips any XML
    prolog and clamps the rendered width to the page."""
    svg = _read(path)
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    # ensure it scales to the page rather than its intrinsic px width
    svg = re.sub(r"<svg ", '<svg style="max-width:100%;height:auto" ', svg, count=1)
    label = _html.escape(os.path.splitext(os.path.basename(path))[0])
    return f'<figure class="view"><div class="svgwrap">{svg}</div>' \
           f'<figcaption>{label}</figcaption></figure>'


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; }
@page { size: A4 landscape; margin: 12mm; }
body { font: 12px/1.5 -apple-system,Segoe UI,Arial,Helvetica,sans-serif;
       color: #1a1a1a; margin: 0; }
h1 { font-size: 22px; margin: 0 0 2px; }
h2 { font-size: 16px; margin: 18px 0 6px; border-bottom: 2px solid #4a5568;
     padding-bottom: 3px; page-break-after: avoid; }
h3 { font-size: 13px; margin: 12px 0 4px; page-break-after: avoid; }
h4 { font-size: 12px; margin: 8px 0 3px; }
p { margin: 4px 0; }
code { background: #f0ede6; padding: 1px 4px; border-radius: 3px;
       font: 11px/1.4 Consolas,Menlo,monospace; }
ul, ol { margin: 4px 0 4px 22px; padding: 0; }
li { margin: 1px 0; }
blockquote { margin: 8px 0; padding: 8px 12px; background: #fff7e6;
             border-left: 4px solid #dd8800; border-radius: 3px; }
hr { border: none; border-top: 1px solid #ddd; margin: 12px 0; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 14px;
        font-size: 11px; page-break-inside: avoid; }
th { background: #4a5568; color: #fff; text-align: left; }
th, td { border: 1px solid #cbd2d9; padding: 3px 7px; }
tbody tr:nth-child(even) { background: #f5f3ee; }

.titleblock { border: 2px solid #1a1a1a; padding: 12px 16px; margin-bottom: 16px;
              display: flex; justify-content: space-between; align-items: flex-start;
              page-break-after: avoid; }
.titleblock .meta { text-align: right; font-size: 11px; color: #444; }
.titleblock .meta b { color: #1a1a1a; }
.legend { margin-top: 6px; font-size: 11px; color: #444; }
.legend span { display: inline-block; margin-right: 14px; }
.legend i { display: inline-block; width: 11px; height: 11px; border: 1px solid #999;
            vertical-align: -1px; margin-right: 4px; }

.views { display: flex; flex-wrap: wrap; gap: 14px; }
.view { flex: 1 1 45%; min-width: 300px; margin: 0; page-break-inside: avoid; }
.svgwrap { border: 1px solid #ddd; padding: 6px; background: #fff; }
figcaption { font-size: 11px; color: #666; margin-top: 3px; text-align: center; }
.section { page-break-before: always; }
"""


def build_html(project, title, overall, units, rev, date, views, md_files, legend):
    parts = ["<!doctype html><html><head><meta charset='utf-8'>",
             f"<title>{_html.escape(title or project)}</title>",
             f"<style>{_CSS}</style></head><body>"]

    # title block
    meta = []
    if overall:
        meta.append(f"<div>Overall: <b>{_html.escape(overall)}</b> {units}</div>")
    meta.append(f"<div>Units: <b>{units}</b></div>")
    if rev:
        meta.append(f"<div>Revision: <b>{_html.escape(rev)}</b></div>")
    meta.append(f"<div>Date: <b>{date}</b></div>")
    parts.append("<div class='titleblock'>")
    parts.append(f"<div><h1>{_html.escape(title or project)}</h1>"
                 f"<div style='color:#555'>{_html.escape(project)}</div>")
    if legend:
        chips = "".join(
            f"<span><i style='background:{c}'></i>{_html.escape(name)}</span>"
            for name, c in legend)
        parts.append(f"<div class='legend'>{chips}</div>")
    parts.append("</div>")
    parts.append(f"<div class='meta'>{''.join(meta)}</div>")
    parts.append("</div>")

    # views
    if views:
        parts.append("<h2>Drawings</h2><div class='views'>")
        for v in views:
            parts.append(_svg_block(v))
        parts.append("</div>")

    # markdown documents, each starting a new page
    for md in md_files:
        frag = md_to_html(_read(md))
        parts.append(f"<div class='section'>{frag}</div>")

    parts.append("</body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Browser location + PDF print
# ---------------------------------------------------------------------------

def find_browser():
    """Locate a Chromium-family browser (Chrome, then Edge, then Chromium) across
    Windows / macOS / Linux. Returns a path or None."""
    # PATH first (Linux, and anyone with it exported)
    for name in ("google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "microsoft-edge", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    candidates = [
        # Windows
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        # Linux (non-PATH installs)
        "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def print_pdf(browser, html_path, pdf_path):
    """Drive headless Chrome/Edge to print html_path to pdf_path."""
    url = "file:///" + os.path.abspath(html_path).replace("\\", "/").lstrip("/")
    args = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={os.path.abspath(pdf_path)}", url]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)
    if r.returncode != 0 or not os.path.isfile(pdf_path):
        # older builds reject --headless=new; retry with legacy flag
        args[1] = "--headless"
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        except (subprocess.TimeoutExpired, OSError) as e:
            return False, str(e)
    ok = r.returncode == 0 and os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 1000
    return ok, (r.stderr or "").strip()


# ---------------------------------------------------------------------------

def parse_legend(spec):
    """`name=#rrggbb; name2=colour` -> [(name, colour), ...]. A bare `name` with
    no colour gets a neutral swatch."""
    out = []
    if not spec:
        return out
    for chunk in spec.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            name, colour = chunk.split("=", 1)
            out.append((name.strip(), colour.strip() or "#ccc"))
        else:
            out.append((chunk, "#ccc"))
    return out


def main():
    ap = argparse.ArgumentParser(description="Assemble the builder packet PDF.")
    ap.add_argument("-o", "--out", default="packet.pdf", help="output PDF path")
    ap.add_argument("--project", default="(untitled)")
    ap.add_argument("--title", default=None, help="headline (defaults to project)")
    ap.add_argument("--overall", default=None, help='e.g. "1260x420x720"')
    ap.add_argument("--units", default="mm")
    ap.add_argument("--rev", default=None)
    ap.add_argument("--date", default=None, help="defaults to today")
    ap.add_argument("--views", nargs="*", default=[], help="SVG view files, in order")
    ap.add_argument("--md", nargs="*", default=[], help="markdown docs (cutlist/assembly/hardware), in order")
    ap.add_argument("--legend", default=None, help='material legend "id=#hex; id2=#hex"')
    ap.add_argument("--html-only", action="store_true", help="write HTML, skip the browser")
    ap.add_argument("--browser", default=None, help="explicit path to Chrome/Edge")
    args = ap.parse_args()

    for f in args.views + args.md:
        if not os.path.isfile(f):
            print(f"ERROR: input not found: {f}", file=sys.stderr)
            sys.exit(1)

    date = args.date or datetime.date.today().isoformat()
    html = build_html(args.project, args.title, args.overall, args.units,
                      args.rev, date, args.views, args.md, parse_legend(args.legend))

    out = args.out
    html_path = os.path.splitext(out)[0] + ".html"
    os.makedirs(os.path.dirname(os.path.abspath(html_path)), exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {html_path}")

    if args.html_only:
        print("HTML-only mode — open it and Ctrl-P → Save as PDF, or drop --html-only.")
        return

    browser = args.browser or find_browser()
    if not browser:
        print("No Chrome/Edge/Chromium found — the HTML above is a complete, "
              "shippable deliverable. Open it and print to PDF (Ctrl-P), or pass "
              "--browser <path>.", file=sys.stderr)
        sys.exit(0)

    ok, err = print_pdf(browser, html_path, out)
    if ok:
        print(f"wrote {out}  (via {os.path.basename(browser)})")
    else:
        print(f"PDF print failed ({err or 'unknown error'}). The HTML at "
              f"{html_path} is still a shippable deliverable — print it manually.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
