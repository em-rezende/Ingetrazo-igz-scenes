#!/usr/bin/env python3
# =========================================================================
# Copyright (C) 2026 Ezequiel M. Rezende
# License: GPL-3.0-or-later (same as IngeTrazo)
# =========================================================================
# Build the distributable ``igz_tb_scenes.zip`` for the IngeTrazo extension
# catalog (https://github.com/ingelibre/ingetrazo-extensions).
#
# The catalog installs ONE file per entry: a .py file, or a .zip holding a
# single folder with an __init__.py (see TEMPLATE.toml in that repository).
# This extension uses the zip form because it ships a package with several
# modules (core/), translation files (i18n/) and SVG icons (icons/).
#
# The archive is built deterministically on purpose: fixed timestamps,
# sorted entries and a fixed create-system, so its SHA-256 changes ONLY
# when the content changes. That is what lets the catalog fingerprint
# (``sha256`` in ``extensions/<id>.toml``) be verified and reproduced.
#
# Usage:
#     python packaging/build_extension.py
#
# Output:
#     dist/igz_tb_scenes.zip
#     dist/igz_tb_scenes.zip.sha256   (the value to paste in the catalog entry)
#
# The printed SHA-256 is what goes into ``extensions/igz_tb_scenes.toml``;
# upload the very same dist/igz_tb_scenes.zip as a GitHub Release asset of
# the tag named in the entry's ``download`` URL.
#
# This is the canonical builder: packaging/build_extension.ps1 delegates to
# it when Python is available, so the published fingerprint is reproducible.
# =========================================================================
from __future__ import annotations

import hashlib
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "dist")

#: Single top-level folder inside the zip (required by the catalog).
PACKAGE = "igz_tb_scenes"
ZIP_NAME = f"{PACKAGE}.zip"

#: Source tree copied verbatim (``__init__.py`` + core/ + i18n/ + icons/).
PACKAGE_DIR = os.path.join(ROOT, PACKAGE)

#: Documentation bundled inside the package (optional but tidy).
EXTRA_FILES = ["LICENSE", "README.md", "README_ptBR.md", "THIRD-PARTY.md"]

#: Never bundled: caches, bytecode and OS metadata.
EXCLUDED_DIRS = {"__pycache__", ".git", ".mypy_cache", ".pytest_cache"}
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".pyd")
EXCLUDED_NAMES = {"Thumbs.db", "Desktop.ini", ".DS_Store"}

#: Text files are normalised to LF before zipping, so the fingerprint does not
#: depend on the Git line-ending settings of the machine that builds it.
TEXT_SUFFIXES = (".py", ".md", ".json", ".svg", ".txt")

#: Fixed timestamp so the archive is byte-for-byte reproducible.
FIXED_DATE = (2026, 1, 1, 0, 0, 0)


def read_version() -> str:
    """Read ``__version__`` from the package entry point, so it never drifts."""
    with open(os.path.join(PACKAGE_DIR, "__init__.py"), encoding="utf-8") as fh:
        for line in fh:
            match = re.match(r"\s*__version__\s*=\s*['\"]([^'\"]+)['\"]", line)
            if match:
                return match.group(1)
    return "0.0.0"


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _read_entry(path: str) -> bytes:
    """Read a file, normalising text files to LF line endings."""
    data = _read(path)
    if path.lower().endswith(TEXT_SUFFIXES):
        data = data.replace(b"\r\n", b"\n")
    return data


def collect_entries() -> list[tuple[str, bytes]]:
    """Return ``(arcname, data)`` for every file, sorted by name."""
    files: dict[str, bytes] = {}

    # The whole package tree: __init__.py, core/*.py, i18n/*.json, icons/*.svg.
    for base, dirs, names in os.walk(PACKAGE_DIR):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for name in sorted(names):
            if name in EXCLUDED_NAMES or name.lower().endswith(EXCLUDED_SUFFIXES):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, PACKAGE_DIR).replace(os.sep, "/")
            files[f"{PACKAGE}/{rel}"] = _read_entry(path)

    # Docs stay at the repository root but ship inside the package folder.
    for name in EXTRA_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            files.setdefault(f"{PACKAGE}/{name}", _read_entry(path))

    return sorted(files.items(), key=lambda item: item[0])


def build() -> str:
    os.makedirs(DIST, exist_ok=True)
    out_zip = os.path.join(DIST, ZIP_NAME)

    with zipfile.ZipFile(out_zip, "w") as zf:
        for arcname, data in collect_entries():
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3          # 3 = Unix: stable across OSes
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)

    digest = hashlib.sha256(_read(out_zip)).hexdigest()

    with open(out_zip + ".sha256", "w", encoding="ascii") as fh:
        fh.write(f"{digest}  {ZIP_NAME}\n")

    return digest


def main() -> None:
    version = read_version()
    digest = build()
    print(f"igz_tb_scenes {version}")
    print(f"  dist/{ZIP_NAME}")
    print(f"  sha256 = \"{digest}\"")
    print("")
    print("  Paste that sha256 into extensions/igz_tb_scenes.toml and upload")
    print(f"  dist/{ZIP_NAME} to the GitHub Release of the tag in `download`.")


if __name__ == "__main__":
    main()
