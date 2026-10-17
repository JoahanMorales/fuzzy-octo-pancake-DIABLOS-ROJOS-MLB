"""python -m analysis.stuff_v2.altitude_units — is the v1 vs v2 altitude gap a scale artifact? (HACK-052 diagnostic)

Stuff+ = 100 + 10·z, so ΔStuff+ in points = Δ(runs per pitch) / σ(neutral values) · 10. If v2's count-marginalized
values have a smaller spread across pitches than v1's per-pitch xRV, the same change in runs reads as more points.
Writes reports/stuff_v2/altitude_units.csv: per model, σ of the sea-level values, Δ in runs per pitch (league and by
shape) and Δ in points. Diagnostic only: the adoption rule (R3, in points) is not changed by it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.stuff_v2.run import OUT, load_frame
from stuffplus.altitude import STUFF_FEATURES_INVARIANT, physics_translator
from stuffplus.features.shapes import fit_shapes
from stuffplus.models.stuff import StuffModel
from stuffplus.models.stuff_v2 import StuffV2Model
from stuffplus.physics.constants import RHO_HARP_HELU


def main() -> None:
    d = load_frame().reset_index(drop=True)
    shape_model, _ = fit_shapes(d)
    translate = physics_translator(shape_model)
    v1 = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=translate).fit(d)
    v2 = StuffV2Model(translate=translate).fit(d)
    flavours = {
        "Stuff+ v1": (v1.predict_at_rho(d, 1.0)["xrv"].to_numpy(), v1.predict_at_rho(d, RHO_HARP_HELU)["xrv"].to_numpy()),
        "Stuff+ v2 (familia)": (v2.stuff_value_at_rho(d, 1.0), v2.stuff_value_at_rho(d, RHO_HARP_HELU)),
    }
    shape = d["shape"].astype(str).to_numpy()
    rows = []
    for model, (sea, hh) in flavours.items():
        sd = float(np.std(sea))
        runs = hh - sea  # + = more runs allowed in Harp Helú air (worse for the pitcher)
        by = pd.Series(runs).groupby(shape).agg(["mean", "size"])
        by = by[by["size"] >= 200]["mean"]
        rows.append(dict(model=model, sd_sea_level=sd, league_delta_runs=float(runs.mean()),
                         league_delta_points=float(-10 * runs.mean() / sd),
                         least_hurt_shape=by.idxmin(), most_hurt_shape=by.idxmax(),
                         **{f"runs_{k}": v for k, v in by.items()}))
    t = pd.DataFrame(rows)
    t.round(6).to_csv(OUT / "altitude_units.csv", index=False)
    print(t[["model", "sd_sea_level", "league_delta_runs", "league_delta_points", "least_hurt_shape",
             "most_hurt_shape"]].to_string(index=False))


if __name__ == "__main__":
    main()
