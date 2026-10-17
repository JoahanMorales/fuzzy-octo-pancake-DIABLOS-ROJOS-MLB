"""Fail if the static web build could leak raw ISAC data (HACK-050).

    npm --prefix web run build && python scripts/check_web_dist.py [web/dist] [--max-mb 25]

Applies the raw-data rules of ``scripts/check_no_raw_data.py`` (HACK-024) to every file of the built site:
- no parquet / pickle / rds / feather / hdf5 file;
- no delimited table with more than 1,000 rows that looks pitch-level (a ``PitchUID`` column or three or more raw
  Trackman columns);
- the same rule inside JSON: any list of objects longer than 1,000 whose keys include a pitch id or three raw
  Trackman columns (the web contract only ships aggregates);
- the whole build is at most ``--max-mb`` megabytes (25 by default).
Exit 1 lists every violation; 0 prints one ``WEB_DIST_OK`` line.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "web" / "dist"
MAX_MB = 25.0


def _rules():
    spec = importlib.util.spec_from_file_location("check_no_raw_data", ROOT / "scripts" / "check_no_raw_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _object_lists(obj):
    if isinstance(obj, list):
        if obj and all(isinstance(r, dict) for r in obj):
            yield obj
        for v in obj:
            if isinstance(v, (dict, list)):
                yield from _object_lists(v)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _object_lists(v)


def json_violations(path: Path, rules, max_rows: int) -> list[str]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    bad = []
    for rows in _object_lists(doc):
        if len(rows) <= max_rows:
            continue
        keys = set()
        for r in rows[:50]:
            keys |= {str(k).lower() for k in r}
        ids, raw = rules.PITCH_ID & keys, rules.RAW_COLUMNS & keys
        if ids or len(raw) >= 3:
            why = f"pitch id {sorted(ids)}" if ids else f"raw per-pitch columns {sorted(raw)[:6]}"
            bad.append(f"{path}: JSON list of {len(rows)} rows with {why} (> {max_rows})")
    return bad


def check(dist: Path, max_mb: float = MAX_MB) -> list[str]:
    rules = _rules()
    if not dist.is_dir():
        return [f"{dist}: no existe; corre npm --prefix web run build"]
    files = [p for p in dist.rglob("*") if p.is_file()]
    bad = list(rules.violations(files, max_rows=rules.MAX_ROWS))
    for p in files:
        if p.suffix.lower() == ".json":
            bad += json_violations(p, rules, rules.MAX_ROWS)
    size = sum(p.stat().st_size for p in files) / 1e6
    if size > max_mb:
        bad.append(f"{dist}: {size:.1f} MB > {max_mb:.0f} MB")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dist", nargs="?", type=Path, default=DEFAULT_DIST)
    ap.add_argument("--max-mb", type=float, default=MAX_MB)
    args = ap.parse_args(argv)
    bad = check(args.dist, args.max_mb)
    if bad:
        print("\n".join(bad))
        return 1
    files = [p for p in args.dist.rglob("*") if p.is_file()]
    print(f"WEB_DIST_OK files={len(files)} size={sum(p.stat().st_size for p in files) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
