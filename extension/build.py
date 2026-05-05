#!/usr/bin/env python3
"""Build PhishGuard extension for Chrome or Firefox.

Usage:
    python build.py chrome
    python build.py firefox
    python build.py both          # builds both, default

Output:
    dist/chrome/   — load via chrome://extensions/ → Load unpacked
    dist/firefox/  — load via about:debugging → Load Temporary Add-on
                     (select dist/firefox/manifest.json)

Each output folder also gets a .zip suitable for store submission.
"""
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

# Files/folders copied into every browser build (relative to extension root)
SHARED_PATHS = ["src", "vendor", "icons"]


def build(target: str) -> None:
    out_dir = DIST / target
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Copy shared content
    for path in SHARED_PATHS:
        src = ROOT / path
        dst = out_dir / path
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # Copy the right manifest
    manifest_src = ROOT / "manifests" / f"manifest.{target}.json"
    if not manifest_src.exists():
        sys.exit(f"Missing manifest: {manifest_src}")
    shutil.copy2(manifest_src, out_dir / "manifest.json")

    # Zip for store submission
    zip_path = DIST / f"phishguard-{target}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in out_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(out_dir))

    print(f"✓ {target:8s} → {out_dir}  ({zip_path.name})")


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    if target == "both":
        for t in ("chrome", "firefox"):
            build(t)
    elif target in ("chrome", "firefox"):
        build(target)
    else:
        sys.exit(f"Unknown target '{target}'. Use chrome | firefox | both.")


if __name__ == "__main__":
    main()
