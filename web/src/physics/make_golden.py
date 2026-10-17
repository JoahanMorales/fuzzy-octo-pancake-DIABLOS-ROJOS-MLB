"""Parity goldens for the TypeScript flight engine (HACK-042): 50 synthetic releases through stuffplus.physics.flight.

Releases are random vectors in observed ranges (never rows of the parquet). Also writes the HACK-041 flight check
(median four-seamer, No vs Extreme bucket ρ̂, measured elasticity) so the browser reproduces the reported ΔIVB.
Run from the repo root: PYTHONPATH=. python web/src/physics/make_golden.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus.physics.constants import RHO_HARP_HELU
from stuffplus.physics.flight import Release, fly

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("golden.json")


def _row(rel: Release, rho: float, el: float) -> dict:
    f = fly(rel, rho, el)
    return dict(velo=rel.velo_mph, ivb=rel.ivb_in, hb=rel.hb_in, height=rel.rel_height_ft, side=rel.rel_side_ft,
                extension=rel.extension_ft, target_x=rel.target_x_ft, target_z=rel.target_z_ft, cd=rel.cd, rho=rho,
                elasticity=el, out=dict(plate_x=f.plate_x, plate_z=f.plate_z, ivb=f.ivb_in, hb=f.hb_in,
                                        flight_time=f.flight_time, plate_mph=f.plate_mph, n=len(f.t)))


def main() -> None:
    rng = np.random.default_rng(42)
    u = lambda lo, hi: float(rng.uniform(lo, hi))  # noqa: E731
    cases = []
    for _ in range(50):
        rel = Release(velo_mph=u(72, 101), ivb_in=u(-16, 22), hb_in=u(-18, 18), rel_height_ft=u(4.8, 7.0),
                      rel_side_ft=u(-3.0, 3.0), extension_ft=u(5.3, 7.3), target_z_ft=u(1.2, 3.8),
                      target_x_ft=u(-1.2, 1.2), cd=u(0.26, 0.32))
        cases.append(_row(rel, u(0.78, 1.05), u(1.0, 1.9)))

    b = pd.read_csv(ROOT / "reports/physics_v2/coefficients_by_bucket.csv")
    fs = b[b.pitch_family == "Four-Seam"].set_index("bucket")
    check = pd.read_csv(ROOT / "reports/physics_v2/flight_check.csv")
    rep = check[(check.pitch_family == "Four-Seam") & (check.model == "elasticidad medida")].iloc[0]
    no = fs.loc["No Altitude"]
    median_fs = Release(velo_mph=float(no.velo), ivb_in=float(no.ivb), hb_in=float(no.hb), cd=float(no.cd))
    el = float(rep.elasticity)
    literal = fly(median_fs, RHO_HARP_HELU, el).ivb_in - fly(median_fs, 1.0, el).ivb_in  # ρ 1.0 → ρ_HH
    flight_check = dict(velo=float(no.velo), ivb=float(no.ivb), hb=float(no.hb), cd=float(no.cd),
                        rho_no=float(no.rho), rho_ext=float(fs.loc["Extreme Altitude", "rho"]),
                        elasticity=float(rep.elasticity), reported_delta_ivb=float(rep.pred_delta_ivb),
                        observed_delta_ivb=float(rep.obs_delta_ivb), rho_hh=float(RHO_HARP_HELU),
                        python_delta_ivb_sea_to_hh=float(literal))
    OUT.write_text(json.dumps(dict(cases=cases, flight_check=flight_check), indent=1) + "\n")
    print(f"wrote {OUT} ({len(cases)} cases)")


if __name__ == "__main__":
    main()
