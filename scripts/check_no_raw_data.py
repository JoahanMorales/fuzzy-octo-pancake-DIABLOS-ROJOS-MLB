"""Fail if raw ISAC data could leave the laptop (HACK-024).

    python scripts/check_no_raw_data.py [--bundle DIR ...] [--max-mb 100]

Checks every git-tracked file plus every file in the deploy bundle(s):
- no parquet / pickle / rds / feather / hdf5 file at all (raw data and pitch-level outputs travel in these);
- no table (csv/tsv/json lines) with more than 1,000 rows that looks pitch-level: a pitch identifier column
  (``PitchUID``) or at least three raw per-pitch Trackman columns (velocity, spin, movement, plate location,
  exit speed...). Aggregates use renamed or summarized columns and are allowed;
- the bundle is at most ``--max-mb`` megabytes.
Exit code 1 lists every violation; 0 prints a one-line pass.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = {".parquet", ".pq", ".pkl", ".pickle", ".rds", ".feather", ".h5", ".hdf5"}
TABLES = {".csv", ".tsv", ".txt"}
MAX_ROWS = 1000
PITCH_ID = {"pitchuid", "pitch_uid"}
RAW_COLUMNS = {c.lower() for c in (
    "RelSpeed", "SpinRate", "SpinAxis", "InducedVertBreak", "HorzBreak", "VertBreak", "RelHeight", "RelSide",
    "Extension", "PlateLocHeight", "PlateLocSide", "ExitSpeed", "Angle", "Direction", "Distance",
    "VertApprAngle", "HorzApprAngle", "ZoneSpeed", "EffectiveVelo", "pfxx", "pfxz", "PitchCall", "TaggedPitchType",
    "AutoPitchType", "batter_anon_id")}
DEFAULT_BUNDLES = ("deploy/bundle",)


def tracked(root: Path = ROOT) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    return [root / p for p in out.decode("utf-8").split("\0") if p]


def _header_and_rows(path: Path) -> tuple[list[str], int] | None:
    """Header and data-row count of a delimited text table; None if the file is not a table."""
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            first = f.readline()
            if not first or ("," not in first and "\t" not in first):
                return None
            delim = "\t" if first.count("\t") > first.count(",") else ","
            header = next(csv.reader([first], delimiter=delim))
            rows = sum(1 for line in f if line.strip())
        return [h.strip().lower() for h in header], rows
    except OSError:
        return None


def violations(files: list[Path], max_rows: int = MAX_ROWS) -> list[str]:
    bad = []
    for path in files:
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        if suffix in BINARY:
            bad.append(f"{rel}: binary data file ({suffix}) must not be tracked or bundled")
            continue
        if suffix not in TABLES:
            continue
        parsed = _header_and_rows(path)
        if parsed is None:
            continue
        header, rows = parsed
        if rows <= max_rows:
            continue
        ids = PITCH_ID & set(header)
        raw = RAW_COLUMNS & set(header)
        if ids or len(raw) >= 3:
            why = f"pitch id {sorted(ids)}" if ids else f"raw per-pitch columns {sorted(raw)[:6]}"
            bad.append(f"{rel}: {rows:,} rows with {why} (> {max_rows:,} pitch-level rows)")
    return bad


def bundle_files(bundles) -> list[Path]:
    return [p for b in bundles for p in (ROOT / b).rglob("*") if p.is_file()]


def bundle_mb(bundles) -> float:
    return sum(p.stat().st_size for p in bundle_files(bundles)) / 1e6


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", action="append", default=None, help="bundle dir relative to the repo (repeatable)")
    ap.add_argument("--max-mb", type=float, default=100.0)
    args = ap.parse_args(argv)
    bundles = args.bundle or [b for b in DEFAULT_BUNDLES if (ROOT / b).exists()]
    files = sorted(set(tracked()) | set(bundle_files(bundles)))
    bad = violations(files)
    size = bundle_mb(bundles)
    if size > args.max_mb:
        bad.append(f"bundle {bundles} is {size:.1f} MB > {args.max_mb:.0f} MB")
    if bad:
        print("RAW_DATA_CHECK_FAIL")
        print("\n".join(f"- {b}" for b in bad))
        return 1
    print(f"RAW_DATA_CHECK_PASS files={len(files)} bundle={size:.1f}MB ({', '.join(bundles) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
