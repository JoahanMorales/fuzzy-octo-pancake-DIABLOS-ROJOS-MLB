"""python -m analysis.tuning.monotone — is the production Stuff+ already monotone in fastball velocity? (HACK-028)

Partial dependence of xRV on ``RelSpeed`` for four-seamers (and sinkers): every fastball of the league is moved to each
velocity on a grid with all its other traits kept, and the mean xRV is recorded. Physics says faster ⇒ lower xRV
(better for the pitcher). If the curve already falls, a monotone constraint adds nothing; the multiclass outcome model
cannot take one sign for all classes anyway (balls and whiffs move in opposite directions).
Writes reports/tuning/monotone_velocity.csv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.tuning.run import OUT, load_frame
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.models.stuff import StuffModel

GRID = np.arange(86.0, 99.5, 1.0)


def partial_dependence(model: StuffModel, d: pd.DataFrame, family: str, n: int = 20000, seed: int = 2240) -> pd.DataFrame:
    fb = d[d.pitch_family.astype(str) == family]
    fb = fb.sample(min(n, len(fb)), random_state=seed)
    rows = []
    for v in GRID:
        x = fb.assign(RelSpeed=v, velo_diff_fb=fb.velo_diff_fb + (v - fb.RelSpeed))
        rows.append(dict(pitch_family=family, velo=v, xrv=float(model.predict_xrv(x).mean()), pitches=len(fb)))
    out = pd.DataFrame(rows)
    out["step"] = out.xrv.diff()
    return out


def contact_constraint_test(d: pd.DataFrame) -> pd.DataFrame:
    """Held-out (2024–25, 3 pitcher folds) contact MSE with and without ``RelSpeed`` monotone decreasing."""
    from stuffplus import splits
    from stuffplus.models import tuning
    from stuffplus.models.stuff import CONTACT_PARAMS

    feats = list(STUFF_FEATURES_INVARIANT)
    mono = [-1 if f == "RelSpeed" else 0 for f in feats]
    dd = d[d.year < 2026].reset_index(drop=True)
    folds = list(splits.pitcher_group_kfold(dd, k=3))
    res = tuning.search(dd, feats, [{**CONTACT_PARAMS, "monotone_constraints": mono}], folds, kind="contact",
                        production=(CONTACT_PARAMS, 200), max_rounds=200)
    res["config"] = res.config.map({"production": "sin restricción (200 rondas)", "c0": "RelSpeed monótona ↓"})
    return res.groupby("config").agg(test_mse=("test_at_inner_best", "mean"), rounds=("inner_best_iter", "mean")).reset_index()


def main() -> None:
    d = load_frame()
    m = StuffModel(features=list(STUFF_FEATURES_INVARIANT)).fit(d)
    pdp = pd.concat([partial_dependence(m, d, f) for f in ("Four-Seam", "Sinker")], ignore_index=True)
    pdp.round(6).to_csv(OUT / "monotone_velocity.csv", index=False)
    contact_constraint_test(d).round(6).to_csv(OUT / "monotone_contact_test.csv", index=False)
    for f, g in pdp.groupby("pitch_family"):
        print(f, "falls at", int((g.step < 0).sum()), "of", int(g.step.notna().sum()), "steps;",
              f"xRV {g.xrv.iloc[0]:+.4f} at {GRID[0]:.0f} mph -> {g.xrv.iloc[-1]:+.4f} at {GRID[-1]:.0f} mph")


if __name__ == "__main__":
    main()
