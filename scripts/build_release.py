#!/usr/bin/env python3
"""build_release.py — (re)build the two downloadable release artifacts.

  - furniture-design.skill          the installable skill (unzips to furniture-design/)
  - furniture-design-skill-main.zip the full repo snapshot

Both are plain zips built **deterministically**: file order is sorted and every
entry uses a fixed timestamp, so the archive bytes are a pure function of the
included file contents. That means re-running this when nothing changed produces
byte-identical archives (no spurious git diffs) — which is what lets the
pre-commit hook rebuild on every commit without churn.

Run manually, or let `.githooks/pre-commit` run it automatically. From the repo
root:  python scripts/build_release.py
"""
import os
import glob
import zipfile

# Repo root = parent of this script's directory.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIXED_TIME = (1980, 1, 1, 0, 0, 0)   # zip epoch — deterministic, content-only diffs

SKILL_ARTIFACT = "furniture-design.skill"
MAIN_ARTIFACT = "furniture-design-skill-main.zip"


def _skill_files():
    """Files that make up the installable skill (clean — no build/dev scripts)."""
    fs = ["SKILL.md", "README.md", "LIMITATIONS.md"]
    fs += sorted(glob.glob("assets/*.json"))
    fs += sorted(glob.glob("references/*.md"))
    fs += sorted(f for f in glob.glob("scripts/*.py")
                 if os.path.basename(f) != "build_release.py")
    return [f.replace("\\", "/") for f in fs]


def _main_files(skill_files):
    """Repo snapshot: the skill payload plus the landing page, build script,
    .gitignore, and the freshly-built .skill itself."""
    extra = ["index.html", ".gitignore", "scripts/build_release.py", SKILL_ARTIFACT]
    return skill_files + [e for e in extra if os.path.exists(e)]


def _write_zip(out_path, files, prefix):
    """Deterministic zip: sorted arcnames, fixed timestamps, stable permissions."""
    entries = sorted(set(files), key=lambda f: f)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in entries:
            with open(f, "rb") as fh:
                data = fh.read()
            zi = zipfile.ZipInfo(f"{prefix}/{f}", date_time=FIXED_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    return len(entries)


def build():
    os.chdir(ROOT)
    skill_files = _skill_files()
    n1 = _write_zip(SKILL_ARTIFACT, skill_files, "furniture-design")
    # main.zip embeds the .skill, so build it after the .skill exists
    n2 = _write_zip(MAIN_ARTIFACT, _main_files(skill_files), "furniture-design-skill-main")
    return n1, n2


if __name__ == "__main__":
    n1, n2 = build()
    print(f"built {SKILL_ARTIFACT}: {n1} files")
    print(f"built {MAIN_ARTIFACT}: {n2} files")
