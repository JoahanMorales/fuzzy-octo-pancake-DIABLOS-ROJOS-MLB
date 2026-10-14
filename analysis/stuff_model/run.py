"""Stuff+ v1 (HACK-010): component model, honest validation, bundle for the dashboard.

    python analysis/stuff_model/run.py           # real data → artifacts/bundle (v1) + reports/stuff_model/
    python analysis/stuff_model/run.py --fast    # quick settings

Reports (aggregates only):
  metrics.csv              per-pitch OOF skill vs the null baselines (rubric's "mean xRV by count")
  component_metrics.csv    5-outcome log-loss vs prior and vs count, contact model RMSE
  predictiveness.csv       first N pitches → rest of season: Stuff+ vs the pitcher's own results
  reliability.csv          split-half (odd/even games) reliability of pitcher-season means
  class_values.csv         LMB run value of each pitch outcome
  stuff_by_pitch_type.csv  Stuff+ at sea level and in Harp Helú air, by pitch type
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stuffplus import api, config, evaluate, schema, splits  # noqa: E402
from stuffplus.baseline import CountBaseline  # noqa: E402
from stuffplus.bundle import save_bundle  # noqa: E402
from stuffplus.models.common import as_model_frame, fit_lgbm  # noqa: E402
from stuffplus.models.stuff import (  # noqa: E402
    OUTCOMES, STUFF_FEATURES, StuffModel, add_stuff_features, matched_sample_predictiveness, outcome_class,
    split_half_reliability,
)
from stuffplus.scale import PlusScaler  # noqa: E402
from stuffplus.serving import PROB_TARGETS  # noqa: E402

LOCATION_FEATURES = ["plate_x_arm", "PlateLocHeight", "Balls", "Strikes", "same_side", "is_rhp", "AutoPitchType"]
PITCHING_FEATURES = STUFF_FEATURES + ["plate_x_arm", "PlateLocHeight", "Balls", "Strikes", "same_side"]
REPORTS = config.REPORTS_DIR / "stuff_model"


def _v0():
    spec = importlib.util.spec_from_file_location("v0_run", ROOT / "analysis" / "v0" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Targets (rv, rv_x, t_*), arm-side physics, per-game air density, arsenal diffs."""
    return add_stuff_features(_v0().prepare(df_clean))


def _component_metrics(frame: pd.DataFrame, oof: pd.DataFrame, folds) -> pd.DataFrame:
    y = outcome_class(frame).to_numpy()
    ok = y >= 0
    P = oof[[f"p_{o}" for o in OUTCOMES]].to_numpy(float)
    eps = 1e-9
    ll_model = float(-np.log(np.clip(P[ok, :][np.arange(ok.sum()), y[ok]], eps, 1)).mean())
    prior = np.bincount(y[ok], minlength=len(OUTCOMES)) / ok.sum()
    ll_prior = float(-np.log(prior[y[ok]]).mean())
    # count-aware baseline: outcome shares by count, out of fold
    ll_count = []
    for tr, te in folds:
        tr_ok, te_ok = tr[ok[tr]], te[ok[te]]
        shares = pd.crosstab(frame["count"].iloc[tr_ok], y[tr_ok], normalize="index")
        p = shares.reindex(frame["count"].iloc[te_ok]).fillna(1 / len(OUTCOMES)).to_numpy()
        ll_count.append(-np.log(np.clip(p[np.arange(len(te_ok)), y[te_ok]], eps, 1)))
    ll_count = float(np.concatenate(ll_count).mean())
    ip = y == 4
    contact = evaluate.regression_metrics(frame["rv_x"].to_numpy()[ip], oof["contact_rv"].to_numpy(float)[ip])
    return pd.DataFrame([
        {"component": "outcome (5 classes)", "metric": "logloss", "model": ll_model, "prior": ll_prior, "count_baseline": ll_count},
        {"component": "contact value | in play", "metric": "rmse", "model": contact["rmse"],
         "prior": float(frame["rv_x"].to_numpy()[ip].std(ddof=0)), "count_baseline": np.nan},
    ])


def train(frame: pd.DataFrame, out_dir: Path, fast: bool = False, write_reports: bool = True) -> dict:
    t0 = time.time()
    rounds = dict(class_rounds=60, contact_rounds=40) if fast else {}
    folds = list(splits.pitcher_group_kfold(frame))
    model = StuffModel(**rounds)
    oof = model.oof(frame, folds)
    frame = frame.assign(xrv_stuff_oof=oof["xrv"].to_numpy(float))

    # --- validation (all out of fold, by pitcher) ---
    base_count = evaluate.oof_predict(frame, lambda tr, te: CountBaseline().fit(tr, ["rv_x"]).predict(te, "rv_x"), folds)
    base_type = evaluate.oof_predict(frame, lambda tr, te: CountBaseline(by=("AutoPitchType",)).fit(tr, ["rv_x"]).predict(te, "rv_x"), folds)
    n_boot = 100 if fast else 300
    m_count = evaluate.compare({"baseline": base_count, "stuff_v1": frame.xrv_stuff_oof}, frame.rv_x,
                               groups=frame.pitcher_anon_id, n_boot=n_boot).assign(baseline_name="mean xRV by count")
    m_type = evaluate.compare({"baseline": base_type, "stuff_v1": frame.xrv_stuff_oof}, frame.rv_x,
                              groups=frame.pitcher_anon_id, n_boot=n_boot).assign(baseline_name="mean xRV by pitch type")
    metrics = pd.concat([m_count, m_type], ignore_index=True)
    comp = _component_metrics(frame, oof, folds)
    pred = matched_sample_predictiveness(frame, "xrv_stuff_oof", sizes=(25, 50) if fast else (50, 100, 200, 400),
                                         rest_min=40 if fast else 300)
    rel = pd.DataFrame([split_half_reliability(frame, "xrv_stuff_oof", min_n=30 if fast else 150)])

    # --- final models ---
    model.fit(frame)
    xrv_full = model.predict_xrv(frame)
    distilled, r2 = model.distill(frame, xrv_full, rounds=80 if fast else 400)
    side = 40 if fast else 250
    models = {"stuff_xrv": (distilled, {"features": STUFF_FEATURES, "target": "xrv_stuff_components",
                                        "objective": "regression", "distill_r2": round(r2, 4)})}
    for t in PROB_TARGETS.values():
        models[f"stuff_{t}"] = (fit_lgbm(frame, STUFF_FEATURES, t, "binary", {"learning_rate": 0.1}, side, allow_location=False),
                                {"features": STUFF_FEATURES, "target": t, "objective": "binary"})
    models["location_xrv"] = (fit_lgbm(frame, LOCATION_FEATURES, "rv_x", params={"learning_rate": 0.1}, num_boost_round=side),
                              {"features": LOCATION_FEATURES, "target": "rv_x", "objective": "regression"})
    models["pitching_xrv"] = (fit_lgbm(frame, PITCHING_FEATURES, "rv_x", params={"learning_rate": 0.1}, num_boost_round=side),
                              {"features": PITCHING_FEATURES, "target": "rv_x", "objective": "regression"})

    def run(name, data, feats):
        return models[name][0].predict(as_model_frame(data, feats))

    neutral = model.translate(frame, 1.0, frame["rho"].to_numpy())
    scalers = {
        "stuff": PlusScaler().fit(frame.assign(x=run("stuff_xrv", neutral, STUFF_FEATURES)), "x"),
        "location": PlusScaler().fit(frame.assign(x=run("location_xrv", frame, LOCATION_FEATURES)), "x"),
        "pitching": PlusScaler().fit(frame.assign(x=run("pitching_xrv", neutral, PITCHING_FEATURES)), "x"),
    }
    rho_hh = api.resolve_rho("harp_helu")
    hh = model.translate(frame, rho_hh, frame["rho"].to_numpy())
    sp = scalers["stuff"]
    frame = frame.assign(
        stuff_plus_neutral=sp.transform(frame.assign(x=run("stuff_xrv", neutral, STUFF_FEATURES)), "x"),
        stuff_plus_hh=sp.transform(frame.assign(x=run("stuff_xrv", hh, STUFF_FEATURES)), "x"),
    )
    by_type = (frame.groupby(frame.AutoPitchType.astype(str), observed=True)
               .agg(pitches=("rv", "size"), stuff_plus_sea_level=("stuff_plus_neutral", "mean"),
                    stuff_plus_harp_helu=("stuff_plus_hh", "mean")).reset_index()
               .rename(columns={"AutoPitchType": "pitch_type"}))
    by_type["delta_cdmx"] = by_type.stuff_plus_harp_helu - by_type.stuff_plus_sea_level
    class_values = pd.DataFrame({"outcome": OUTCOMES,
                                 "rv_x_mean": [model.class_values.get(i, np.nan) for i in range(len(OUTCOMES))]})

    rho_by_alt = frame.groupby(frame.altitude_category.astype(str)).rho.median()
    rho = {"sea_level": 1.0, "harp_helu": float(rho_hh),
           "extreme_altitude": float(rho_by_alt.get("Extreme Altitude", 0.84)),
           "medium_altitude": float(rho_by_alt.get("Medium Altitude", 0.89))}
    summary = {
        "stuff_skill_vs_count": m_count.set_index("model").loc["stuff_v1", "skill_vs_baseline"],
        "stuff_skill_vs_pitch_type": m_type.set_index("model").loc["stuff_v1", "skill_vs_baseline"],
        "distill_r2": r2, "seconds": round(time.time() - t0, 1), "fast": fast,
        "predictiveness": pred.round(4).to_dict(orient="records"), "reliability": rel.round(4).to_dict(orient="records")[0],
    }
    save_bundle(out_dir, models, scalers, rho, summary,
                tables={"stuff_by_pitch_type": by_type.round(3), "class_values": class_values.round(5)},
                version="v1-fast" if fast else "v1")
    if write_reports:
        REPORTS.mkdir(parents=True, exist_ok=True)
        metrics.round(5).to_csv(REPORTS / "metrics.csv", index=False)
        comp.round(5).to_csv(REPORTS / "component_metrics.csv", index=False)
        pred.round(4).to_csv(REPORTS / "predictiveness.csv", index=False)
        rel.round(4).to_csv(REPORTS / "reliability.csv", index=False)
        class_values.round(5).to_csv(REPORTS / "class_values.csv", index=False)
        by_type.round(3).to_csv(REPORTS / "stuff_by_pitch_type.csv", index=False)
    return {"metrics": metrics, "components": comp, "predictiveness": pred, "reliability": rel,
            "by_type": by_type, "summary": summary, "model": model}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.BUNDLE_DIR))
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    from stuffplus.io import load_raw

    res = train(prepare(schema.clean(load_raw())), Path(args.out), fast=args.fast)
    print(res["metrics"][["baseline_name", "model", "rmse", "skill_vs_baseline", "skill_lo", "skill_hi"]].round(5).to_string(index=False))
    print(res["components"].round(4).to_string(index=False))
    print(res["predictiveness"].round(3).to_string(index=False))
    print(res["reliability"].round(3).to_string(index=False))
    print(res["by_type"].round(1).to_string(index=False))
    print(f"distill R2 {res['summary']['distill_r2']:.3f} · bundle -> {args.out} ({res['summary']['seconds']} s)")


if __name__ == "__main__":
    main()
