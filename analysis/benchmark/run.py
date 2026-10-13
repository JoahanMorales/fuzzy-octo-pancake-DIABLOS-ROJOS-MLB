"""Shared-split exploratory benchmark on precomputed rv_x; aggregate reports only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus import evaluate, splits
from stuffplus.baseline import CountBaseline
from stuffplus.models.bench import GAMShapeModel
from stuffplus.models.stuff import StuffModel, outcome_class

LIMITATION = ("Exploratory/transductive: shared preparation estimates target tables, "
              "arsenal means and density normalization before splitting. These results "
              "do not certify fully nested out-of-sample robustness or causal altitude effects.")


def benchmark(frame, *, demo_data, fast=False, shape_col="AutoPitchType", factories=None):
    """Fit each model on identical train rows, score identical finite-target test rows.

    No penalty/ensemble selection uses these evaluation rows. Empty folds and
    missing contact training data abort explicitly rather than alter denominators.
    Factories can supply compatible fit/predict_xrv models for diagnostic tests.
    """
    frame = frame.reset_index(drop=True)
    finite = np.isfinite(frame.rv_x.to_numpy(float))
    factories = factories or {
        "gam": lambda: GAMShapeModel(shape_col=shape_col),
        "lightgbm": lambda: StuffModel(**({"class_rounds": 30, "contact_rounds": 20} if fast else {})),
    }
    schemes = {
        "pitcher_kfold": list(splits.pitcher_group_kfold(frame)),
        "season_holdout": [splits.season_holdout(frame)],
        "park_holdout": [splits.park_holdout(frame)],
    }
    metrics, calibration, audits = [], [], []
    for name, folds in schemes.items():
        predictions = {key: np.full(len(frame), np.nan) for key in ("baseline", "gam", "lightgbm")}
        tested = np.zeros(len(frame), dtype=bool)
        for fold, (train, test) in enumerate(folds):
            train, test = train[finite[train]], test[finite[test]]
            if len(train) < 2 or not len(test):
                raise ValueError(f"{name} fold {fold}: empty/insufficient eligible train or test")
            if tested[test].any() or np.intersect1d(train, test).size:
                raise ValueError(f"{name}: overlapping evaluation rows")
            tr, te = frame.iloc[train], frame.iloc[test]
            if not outcome_class(tr).eq(4).any():
                raise ValueError(f"{name} fold {fold}: no in-play training rows for LightGBM contact model")
            predictions["baseline"][test] = CountBaseline().fit(tr, ["rv_x"]).predict(te, "rv_x")
            for key, factory in factories.items():
                predictions[key][test] = factory().fit(tr).predict_xrv(te)
            tested[test] = True
            audits.append(dict(split=name, fold=fold, n_train=len(train), n_test=len(test),
                               train_pitchers=tr.pitcher_anon_id.nunique(), test_pitchers=te.pitcher_anon_id.nunique()))
        selected = {key: values[tested] for key, values in predictions.items()}
        if not all(np.isfinite(values).all() for values in selected.values()):
            raise ValueError(f"{name}: nonfinite model predictions; comparison aborted")
        selected["blend_50_50"] = (selected["gam"] + selected["lightgbm"]) / 2
        y = frame.rv_x.to_numpy(float)[tested]
        metrics.append(evaluate.compare(selected, y, groups=frame.pitcher_anon_id.to_numpy()[tested],
                                        n_boot=50 if fast else 300).assign(split=name))
        for key, values in selected.items():
            calibration.append(evaluate.reliability_curve(y, values).assign(split=name, model=key))
    return {
        "metrics": pd.concat(metrics, ignore_index=True).assign(demo_data=demo_data),
        "calibration": pd.concat(calibration, ignore_index=True).assign(demo_data=demo_data),
        "folds": pd.DataFrame(audits).assign(demo_data=demo_data),
        "metadata": {"demo_data": demo_data, "fast": fast, "target": "rv_x", "shape_col": shape_col,
                     "limitation": LIMITATION, "excluded_nonfinite_targets": int((~finite).sum()),
                     "ensemble": "Fixed 50/50 diagnostic only; not selected or deployed",
                     "gam": {"n_splines": 6, "lam": 10.0, "pool_lam": 20.0},
                     "park_holdout": "Altitude bucket holdout, not a named-stadium holdout"},
    }


def write_reports(result, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    for key in ("metrics", "calibration", "folds"):
        result[key].to_csv(output / f"{key}.csv", index=False)
    (output / "metadata.json").write_text(json.dumps(result["metadata"], indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use synthetic data; never official evidence")
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()
    from analysis.stuff_model.run import prepare
    from stuffplus import config, io, schema
    if args.demo:
        from tests.fixtures.synthetic import make_synthetic_pitches
        raw = make_synthetic_pitches(n_innings=2)
    else:
        raw = io.load_raw()
    result = benchmark(prepare(schema.clean(raw)), demo_data=args.demo, fast=args.fast)
    output = config.REPORTS_DIR / "benchmark" / ("demo" if args.demo else "real")
    write_reports(result, output)
    print(f"Wrote aggregate reports to {output}; demo_data={args.demo}")
    print(LIMITATION)


if __name__ == "__main__":
    main()
