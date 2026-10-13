"""Walking skeleton: Stuff+ v0 end to end (HACK-031).

    python analysis/v0/run.py            # real data → artifacts/bundle/ + analysis/v0/metrics.csv
    python analysis/v0/run.py --fast     # quick run (fewer trees) for smoke checks

v0 is deliberately simple; later tasks replace pieces behind the same bundle format:
* air density per game: median drag of fastballs / sea-level median (HACK-004 replaces it);
* movement translation between airs: Magnus ∝ ρ (HACK-004's within-pitcher model replaces it);
* features: release physics + ρ (Stuff+), location + count (Location+), both (Pitching+); arsenal
  features come with HACK-006/HACK-010.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stuffplus import config, evaluate, schema, splits, targets  # noqa: E402
from stuffplus.baseline import CountBaseline  # noqa: E402
from stuffplus.bundle import save_bundle  # noqa: E402
from stuffplus.models.common import add_arm_side_features, fit_lgbm, train_lgbm_oof  # noqa: E402
from stuffplus.scale import PlusScaler  # noqa: E402
from stuffplus.serving import PROB_TARGETS, translate_movement  # noqa: E402

STUFF_FEATURES = ["RelSpeed", "SpinRate", "spin_axis_arm", "InducedVertBreak", "hb_arm", "RelHeight",
                  "rel_side_arm", "Extension", "is_rhp", "AutoPitchType", "rho"]
LOCATION_FEATURES = ["plate_x_arm", "PlateLocHeight", "Balls", "Strikes", "same_side", "is_rhp", "AutoPitchType"]
PITCHING_FEATURES = STUFF_FEATURES + ["plate_x_arm", "PlateLocHeight", "Balls", "Strikes", "same_side"]
G = 32.174


def game_rho(df: pd.DataFrame, min_fastballs: int = 30) -> pd.Series:
    """Per-pitch air density proxy: game median fastball drag ÷ sea-level (No Altitude) median."""
    v = np.sqrt(df.vx0 ** 2 + df.vy0 ** 2 + df.vz0 ** 2)
    k = -(df.ax0 * df.vx0 + df.ay0 * df.vy0 + (df.az0 + G) * df.vz0) / v ** 3
    fb = df.AutoPitchType.astype(str).isin(["Four-Seam", "Sinker"])
    per_game = k[fb].groupby(df.game_anon_id[fb]).agg(["median", "size"])
    alt = df.groupby("game_anon_id").altitude_category.first().astype(str)
    sea = per_game["median"][alt.reindex(per_game.index).eq("No Altitude")].median()
    rho = per_game["median"] / sea
    bucket = rho.groupby(alt.reindex(rho.index)).median()
    thin = per_game["size"] < min_fastballs
    rho[thin] = alt.reindex(rho.index)[thin].map(bucket)
    out = df.game_anon_id.map(rho)
    return out.fillna(df.altitude_category.astype(str).map(bucket)).fillna(1.0).clip(0.6, 1.2).rename("rho")


def prepare(df_clean: pd.DataFrame) -> pd.DataFrame:
    frame, _, _ = targets.build(df_clean)
    frame = add_arm_side_features(frame)
    frame["rho"] = game_rho(frame)
    return frame


def train_v0(frame: pd.DataFrame, out_dir: Path, fast: bool = False) -> dict:
    rounds = 60 if fast else 600
    side_rounds = 40 if fast else 250
    params = {"learning_rate": 0.1} if fast else {}
    t0 = time.time()
    folds = list(splits.pitcher_group_kfold(frame))
    oof = train_lgbm_oof(frame, STUFF_FEATURES, "rv", folds, params=params, num_boost_round=rounds, allow_location=False)
    base = evaluate.oof_predict(frame, lambda tr, te: CountBaseline().fit(tr, ["rv"]).predict(te, "rv"), folds)
    cmp = evaluate.compare({"baseline": base, "stuff_v0": oof.oof}, frame.rv, groups=frame.pitcher_anon_id,
                           n_boot=100 if fast else 300)
    frame = frame.assign(xrv_oof=oof.oof)
    pred = evaluate.pitcher_predictiveness(frame, "xrv_oof", min_n=50 if fast else 300)
    n_final = int(np.median(oof.best_iterations))

    models = {"stuff_xrv": (fit_lgbm(frame, STUFF_FEATURES, "rv", params=params, num_boost_round=n_final,
                                     allow_location=False),
                            {"features": STUFF_FEATURES, "target": "rv", "objective": "regression"})}
    for t in PROB_TARGETS.values():
        models[f"stuff_{t}"] = (fit_lgbm(frame, STUFF_FEATURES, t, "binary", {"learning_rate": 0.1},
                                         side_rounds, allow_location=False),
                                {"features": STUFF_FEATURES, "target": t, "objective": "binary"})
    models["location_xrv"] = (fit_lgbm(frame, LOCATION_FEATURES, "rv", params={"learning_rate": 0.1},
                                       num_boost_round=side_rounds),
                              {"features": LOCATION_FEATURES, "target": "rv", "objective": "regression"})
    models["pitching_xrv"] = (fit_lgbm(frame, PITCHING_FEATURES, "rv", params={"learning_rate": 0.1},
                                       num_boost_round=side_rounds),
                              {"features": PITCHING_FEATURES, "target": "rv", "objective": "regression"})

    from stuffplus.models.common import as_model_frame

    def predict(name, data, feats):
        return models[name][0].predict(as_model_frame(data, feats))

    neutral = translate_movement(frame, 1.0, frame["rho"].to_numpy())
    scalers = {
        "stuff": PlusScaler().fit(frame.assign(x=predict("stuff_xrv", neutral, STUFF_FEATURES)), "x"),
        "location": PlusScaler().fit(frame.assign(x=predict("location_xrv", frame, LOCATION_FEATURES)), "x"),
        "pitching": PlusScaler().fit(frame.assign(x=predict("pitching_xrv", neutral, PITCHING_FEATURES)), "x"),
    }
    frame = frame.assign(stuff_plus_neutral=scalers["stuff"].transform(
        frame.assign(x=predict("stuff_xrv", neutral, STUFF_FEATURES)), "x"))
    by_type = (frame.groupby([frame.AutoPitchType.astype(str), frame.altitude_category.astype(str)], observed=True)
               .agg(pitches=("rv", "size"), rho=("rho", "median"), stuff_plus_neutral=("stuff_plus_neutral", "mean"))
               .reset_index().rename(columns={"AutoPitchType": "pitch_type"}))
    rho_by_alt = frame.groupby(frame.altitude_category.astype(str)).rho.median()
    rho = {"sea_level": 1.0, "extreme_altitude": float(rho_by_alt.get("Extreme Altitude", 0.84)),
           "medium_altitude": float(rho_by_alt.get("Medium Altitude", 0.89))}
    metrics = {
        "pitcher_kfold": cmp.set_index("model").round(5).to_dict(orient="index"),
        "predictiveness": pred.set_index("source").round(4).to_dict(orient="index"),
        "train_rows": int(len(frame)), "best_iterations": oof.best_iterations,
        "seconds": round(time.time() - t0, 1), "fast": fast,
    }
    save_bundle(out_dir, models, scalers, rho, metrics, tables={"stuff_by_pitch_type_v0": by_type.round(3)},
                version="v0-fast" if fast else "v0")
    return {"compare": cmp, "predictiveness": pred, "by_type": by_type, "metrics": metrics}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(config.BUNDLE_DIR))
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    from stuffplus.io import load_raw

    frame = prepare(schema.clean(load_raw()))
    res = train_v0(frame, Path(args.out), fast=args.fast)
    out = Path(__file__).resolve().parent
    res["compare"].round(5).to_csv(out / "metrics.csv", index=False)
    res["predictiveness"].round(4).to_csv(out / "predictiveness.csv", index=False)
    res["by_type"].round(3).to_csv(out / "stuff_by_pitch_type.csv", index=False)
    print(res["compare"][["model", "rmse", "skill_vs_baseline", "skill_lo", "skill_hi"]].round(5).to_string(index=False))
    print(res["predictiveness"].round(3).to_string(index=False))
    print(f"bundle → {args.out} ({res['metrics']['seconds']} s)")


if __name__ == "__main__":
    main()
