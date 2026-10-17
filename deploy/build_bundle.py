"""Copy the local model bundle into deploy/bundle (committed) and run the raw-data leak check (HACK-024).

    python deploy/build_bundle.py

The bundle is LightGBM text models + aggregated tables + manifest (no pitch rows). Source: the bundle that
``stuffplus.bundle.bundle_dir()`` resolves (``$STUFFPLUS_BUNDLE`` → ``artifacts/bundle`` → the main checkout's).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEST = ROOT / "deploy" / "bundle"
KEEP = {".txt", ".csv", ".json"}  # models are LightGBM text dumps; anything else is refused


def main() -> int:
    from stuffplus.bundle import bundle_dir

    src = bundle_dir()
    if not (src / "manifest.json").exists():
        print(f"no bundle at {src}: run analysis/stuff_model/run.py first", file=sys.stderr)
        return 2
    if src.resolve() == DEST.resolve():
        print("source and destination are the same bundle", file=sys.stderr)
        return 2
    files = [p for p in src.rglob("*") if p.is_file()]
    refused = [p for p in files if p.suffix.lower() not in KEEP]
    if refused:
        print("refusing to bundle non-text files: " + ", ".join(str(p.relative_to(src)) for p in refused), file=sys.stderr)
        return 1
    if DEST.exists():
        shutil.rmtree(DEST)
    for p in files:
        out = DEST / p.relative_to(src)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
    print(f"copied {len(files)} files from {src} to {DEST.relative_to(ROOT)}")
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "check_no_raw_data.py"), "--bundle", "deploy/bundle"],
                          cwd=ROOT).returncode


if __name__ == "__main__":
    sys.exit(main())
