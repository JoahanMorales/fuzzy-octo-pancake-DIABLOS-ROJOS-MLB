"""Design-lab data for the /laboratorio page (HACK-048) from reports/design_lab/*.csv (HACK-033 aggregates).

No contract file exists for the design lab yet (HACK-038/050), so the page ships this JSON next to its code;
every number is copied from the CSVs, nothing is computed here. Pitcher ids are anonymized pitcher-seasons.
Run from the repo root: python web/src/features/laboratorio/make_data.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "reports" / "design_lab"
OUT = Path(__file__).with_name("design_lab.json")


def _records(df: pd.DataFrame) -> list[dict]:
    return [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
            for r in df.to_dict(orient="records")]


def main() -> None:
    plan = pd.read_csv(SRC / "development_plan_top3.csv")
    payload = {
        "demo_data": False,
        "sources": [f"reports/design_lab/{f}" for f in ("tweak_summary.csv", "tweak_gains_by_family.csv",
                                                         "new_pitch_summary.csv", "development_plan_top3.csv",
                                                         "run_meta.csv")],
        "meta": _records(pd.read_csv(SRC / "run_meta.csv"))[0],
        "tweaks": _records(pd.read_csv(SRC / "tweak_summary.csv")),
        "by_family": _records(pd.read_csv(SRC / "tweak_gains_by_family.csv")),
        "new_pitch": _records(pd.read_csv(SRC / "new_pitch_summary.csv")),
        # compact: pitcher-season -> [[rank, ajuste, gain_hh, gain_sea, diff], ...]
        "plan": {pid: g.sort_values("rank")[["rank", "ajuste", "gain_hh", "gain_sea", "diff"]].values.tolist()
                 for pid, g in plan.groupby("pitcher_id")},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
