"""Typical sea-level pitch shapes for the /fisica page (HACK-072) from reports/physics_v2 (HACK-041 aggregates).

The contract physics.json carries the drag and Magnus coefficients but not what a typical pitch of each family looks
like, so the page ships this JSON next to its code (same rule as /laboratorio). Every number is copied from the CSV:
the median velocity, IVB and HB of the "No Altitude" bucket, nothing is computed here.
Run from the repo root: python web/src/features/fisica/make_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "reports" / "physics_v2" / "coefficients_by_bucket.csv"
OUT = Path(__file__).with_name("shapes.json")


def main() -> None:
    df = pd.read_csv(SRC)
    sea = df[df["bucket"] == "No Altitude"].sort_values("pitch_family")
    payload = {
        "demo_data": False,
        "sources": ["reports/physics_v2/coefficients_by_bucket.csv"],
        "bucket": "No Altitude",
        "shapes": [
            {"pitch_family": r.pitch_family, "pitches": int(r.pitches), "rho": round(r.rho, 4),
             "velo": round(r.velo, 2), "ivb": round(r.ivb, 2), "hb": round(r.hb, 2)}
            for r in sea.itertuples()
        ],
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(payload['shapes'])} families)")


if __name__ == "__main__":
    main()
