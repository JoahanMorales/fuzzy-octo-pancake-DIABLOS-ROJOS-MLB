"""python -m analysis.export_web.run [--out web/public/data/real]  (HACK-050, under a minute).

Writes the deploy version of the HACK-038 web contract to ``web/public/data/real/``: the same aggregates as the
mock (``stuffplus.export_web.build_mock`` reads only ``reports/`` and ``deploy/bundle/tables/``, never the parquet)
with ``demo_data: false``, and a pitcher page for every pitcher in the leaderboard, not only the Diablos staff.

The browser models are not copied: HACK-040 already writes the real trees to ``web/public/data/models/``
(13 MB) and a second copy would break the 25 MB budget. ``real/manifest.json`` says where they are, lists every
file, and is what the app checks first: if it exists the app reads ``real/``, else ``mock/`` (the badge shows
``demo_data``). Every document passes ``assert_aggregate`` (the raw-data rules of ``scripts/check_no_raw_data.py``)
and the whole ``web/public/data`` folder must stay within 25 MB.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from stuffplus import export_web as ew
from stuffplus.config import repo_root

MODELS_REL = "../models/"  # relative to real/: web/public/data/models/ (HACK-040)
# extra validation tables for the methodology page (HACK-049): all aggregates, read from committed reports
VALIDATION_EXTRA = {
    "rows_fast": "reports/validation/official_fast/validation_table.csv",  # pitcher_kfold, leave_one_park_out_1..20
    "calibration_bins": "reports/validation/official_fast/calibration.csv",  # predicted vs observed xRV by bin
    "calibration_bins_holdouts": "reports/validation/official_full/calibration.csv",  # season / park holdouts
    "calibration_methods": "reports/calibration/methods.csv",  # HACK-053: log-loss, ECE, slope per method
    "leak_audit": "reports/leak_audit/audit.csv",  # HACK-054: whiff AUC by feature set
}


def _real(obj):
    """Copy of a contract document with every ``demo_data`` flag set to False."""
    if isinstance(obj, dict):
        return {k: (False if k == "demo_data" else _real(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_real(v) for v in obj]
    return obj


def build_real(root: Path | None = None) -> dict[str, dict]:
    root = root or repo_root()
    docs = {rel: doc for rel, doc in ew.build_mock(root).items()
            if not rel.startswith("models/") and not rel.startswith("pitcher/")}
    every = set(pd.read_csv(root / "reports/leaderboards/pitcher_season.csv", usecols=["pitcher_anon_id"])
                .pitcher_anon_id.astype(str))
    docs.update(ew._pitcher_docs(root, every))
    val = docs["validation.json"]
    for key, rel in VALIDATION_EXTRA.items():
        if (root / rel).is_file():
            val[key] = ew._records(pd.read_csv(root / rel))
            val["sources"] = [*val["sources"], rel]
    docs = {rel: _real(doc) for rel, doc in docs.items()}
    for doc in docs.values():
        ew.assert_aggregate(doc)
    models = sorted(p.name for p in (root / "web/public/data/models").glob("*.json"))
    docs["manifest.json"] = {
        **_real(ew.envelope(["analysis/export_web/run.py"])),
        "files": sorted(docs),
        "pitchers": len(every),
        "models_dir": MODELS_REL,
        "models": models,
    }
    return docs


def write_real(out: Path, root: Path | None = None) -> dict[str, dict]:
    docs = build_real(root)
    if out.exists():
        shutil.rmtree(out)
    for rel, doc in docs.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    public = out.parent
    total = ew.dir_mb(public)
    if total > ew.MAX_MB:
        raise ew.LeakError(f"{public} pesa {total:.1f} MB > {ew.MAX_MB:.0f} MB")
    return docs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    out = args.out or repo_root() / "web" / "public" / "data" / "real"
    docs = write_real(out)
    print(f"WEB_REAL_OK files={len(docs)} real={ew.dir_mb(out):.1f} MB data={ew.dir_mb(out.parent):.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
