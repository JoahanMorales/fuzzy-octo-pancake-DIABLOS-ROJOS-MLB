"""python -m analysis.stuff_v2.altitude_bias — which model's altitude effect matches reality? (HACK-052, follow-up)

R3 (ΔStuff+ in Harp Helú air within ±1.5 of v1) failed: v2 estimates a 21 % larger altitude cost in runs per pitch
(`altitude_units.csv`: σ of the values is the same, so it is not a scale artifact). R3 compared v2 with v1, not with
the data. This test compares both with the data.

R4 (written 2026-10-16 BEFORE running this file; the human decides whether it replaces R3):
  Park holdout: train only on No + Medium altitude games, predict the 181k Extreme-altitude pitches. Bias = mean
  observed rv_x − predicted, per pitch. v2 "matches reality better" if |bias v2| ≤ |bias v1| and its pitcher-cluster
  95 % CI is not worse than v1's upper bound. Same per-pitch predictions as the HACK-014 suite (v1 = Stuff+ with ρ).
Writes reports/stuff_v2/altitude_bias.csv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.stuff_v2.run import OUT, load_frame
from stuffplus import splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.baseline import CountBaseline
from stuffplus.models.stuff import StuffModel
from stuffplus.models.stuff_v2 import StuffV2Model


def _cluster_ci(resid: np.ndarray, groups: np.ndarray, n_boot: int = 500, seed: int = 2240) -> tuple[float, float]:
    codes = pd.factorize(groups)[0]
    sums, counts = np.bincount(codes, resid), np.bincount(codes).astype(float)
    rng = np.random.default_rng(seed)
    w = rng.multinomial(len(sums), np.full(len(sums), 1 / len(sums)), size=n_boot)
    boot = (w @ sums) / (w @ counts)
    return float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


def main() -> None:
    d = load_frame().reset_index(drop=True)
    tr, te = splits.park_holdout(d)
    train, test = d.iloc[tr], d.iloc[te]
    y = test.rv_x.to_numpy(float)
    preds = {
        "baseline (conteo)": CountBaseline().fit(train, ["rv_x"]).predict(test, "rv_x"),
        "Stuff+ v1": StuffModel(features=list(STUFF_FEATURES_INVARIANT)).fit(train).predict_xrv(test),
        "Stuff+ v2": StuffV2Model().fit(train).predict_xrv(test),
    }
    groups = test.pitcher_anon_id.to_numpy()
    rows = []
    for model, p in preds.items():
        r = y - np.asarray(p, float)
        lo, hi = _cluster_ci(r, groups)
        rows.append(dict(model=model, n=len(r), bias_obs_minus_pred=float(r.mean()), lo=lo, hi=hi))
    t = pd.DataFrame(rows)
    v1, v2 = t.set_index("model").loc["Stuff+ v1"], t.set_index("model").loc["Stuff+ v2"]
    t["r4_v2_matches_better"] = bool(abs(v2.bias_obs_minus_pred) <= abs(v1.bias_obs_minus_pred) and v2.hi <= v1.hi)
    t.round(6).to_csv(OUT / "altitude_bias.csv", index=False)
    print(t.round(5).to_string(index=False))


if __name__ == "__main__":
    main()
