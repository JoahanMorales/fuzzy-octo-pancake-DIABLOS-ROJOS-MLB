"""Location+ (HACK-011): validation, zone tables, heatmaps (sea level vs Harp Helú air) and bundle update.

    python analysis/location_model/run.py          # run AFTER analysis/stuff_model/run.py (it updates that bundle)
    python analysis/location_model/run.py --fast

Reports (aggregates only) in reports/location_model/:
  metrics.csv            OOF per-pitch skill of xRV_loc vs mean xRV by count (the rubric's null model)
  component_metrics.csv  5-outcome log-loss vs prior and count baseline
  zones.csv              location value and observed rv_x by zone × count bucket × pitch family
  reliability.csv        split-half reliability of pitcher-season Location+
  altitude_by_zone.csv   location value by zone at sea level vs Harp Helú air (Four-Seam, Slider, Changeup)
  heatmap_*.png          location value maps (RHP vs RHB, catcher's view mirrored to arm side)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stuffplus import api, config, evaluate, schema, splits  # noqa: E402
from stuffplus.baseline import FAMILY, CountBaseline  # noqa: E402
from stuffplus.bundle import MANIFEST, bundle_dir  # noqa: E402
from stuffplus.models.common import BASE_PARAMS, as_model_frame  # noqa: E402
from stuffplus.models.location import LOCATION_FEATURES, LocationModel, count_bucket, heatmap_grid, zone_label  # noqa: E402
from stuffplus.models.stuff import split_half_reliability  # noqa: E402
from stuffplus.scale import PlusScaler  # noqa: E402

REPORTS = config.REPORTS_DIR / "location_model"


def _stuff_run():
    spec = importlib.util.spec_from_file_location("stuff_run", ROOT / "analysis" / "stuff_model" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plot_heatmaps(grid: pd.DataFrame, path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    types, counts = list(dict.fromkeys(grid.AutoPitchType)), list(dict.fromkeys(grid["count"]))
    vmax = float(np.nanquantile(np.abs(grid.loc_value), 0.98)) or 0.01
    fig, axes = plt.subplots(len(types), len(counts), figsize=(3.2 * len(counts), 3.6 * len(types)), squeeze=False)
    for i, pt in enumerate(types):
        for j, cnt in enumerate(counts):
            g = grid[(grid.AutoPitchType == pt) & (grid["count"] == cnt)]
            piv = g.pivot_table(index="PlateLocHeight", columns="plate_x_arm", values="loc_value")
            ax = axes[i][j]
            im = ax.imshow(piv.to_numpy(), origin="lower", cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                           extent=[piv.columns.min(), piv.columns.max(), piv.index.min(), piv.index.max()], aspect="auto")
            ax.add_patch(plt.Rectangle((-0.83, 1.5), 1.66, 2.0, fill=False, lw=1.5, color="black"))
            ax.set_title(f"{pt} · {cnt}", fontsize=10)
            ax.set_xlabel("x (ft): brazo ← → guante" if i == len(types) - 1 and j == len(counts) // 2 else "")
            ax.set_ylabel("altura (ft)" if j == 0 else "")
    fig.suptitle(title + "\n(azul = mejor para el pitcher; valor en carreras vs promedio del conteo)", fontsize=11)
    fig.colorbar(im, ax=axes, shrink=0.6, label="valor de ubicación (carreras, vista del bateador)")
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def _update_bundle(model: LocationModel, frame: pd.DataFrame, loc_value: np.ndarray, out_dir: Path, rounds: int) -> float:
    """Replace the bundle's location model with a distilled Location+ (location value) model + its scaler."""
    import lightgbm as lgb

    manifest_path = out_dir / MANIFEST
    if not manifest_path.exists():
        return float("nan")
    X = as_model_frame(frame, LOCATION_FEATURES)
    booster = lgb.train({**BASE_PARAMS, "objective": "regression", "learning_rate": 0.1, "num_leaves": 127,
                         "min_data_in_leaf": 100}, lgb.Dataset(X, loc_value), num_boost_round=rounds)
    pred = booster.predict(X)
    r2 = 1 - float(((loc_value - pred) ** 2).sum() / ((loc_value - loc_value.mean()) ** 2).sum())
    booster.save_model(str(out_dir / "models" / "location_xrv.txt"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["models"]["location_xrv"] = {"file": "models/location_xrv.txt", "features": LOCATION_FEATURES,
                                          "target": "location_value (xRV_loc - mean by count x pitch type)",
                                          "objective": "regression", "distill_r2": round(r2, 4), "task": "HACK-011"}
    manifest["scalers"]["location"] = PlusScaler().fit(frame.assign(x=pred), "x").to_dict()
    manifest_path.write_text(json.dumps(manifest, indent=2, default=float), encoding="utf-8")
    return r2


def train(frame: pd.DataFrame, fast: bool = False, out_dir: Path | None = None, write_reports: bool = True) -> dict:
    rounds = dict(class_rounds=60, contact_rounds=40) if fast else {}
    folds = list(splits.pitcher_group_kfold(frame))
    oof = LocationModel(**rounds).oof(frame, folds)
    frame = frame.assign(xrv_loc_oof=oof["xrv"].to_numpy(float), loc_value_oof=oof["loc_value"].to_numpy(float))
    base = evaluate.oof_predict(frame, lambda tr, te: CountBaseline().fit(tr, ["rv_x"]).predict(te, "rv_x"), folds)
    metrics = evaluate.compare({"baseline": base, "location_v1": frame.xrv_loc_oof}, frame.rv_x,
                               groups=frame.pitcher_anon_id, n_boot=100 if fast else 300).assign(baseline_name="mean xRV by count")
    comp = _stuff_run()._component_metrics(frame, oof, folds)
    rel = pd.DataFrame([split_half_reliability(frame, "loc_value_oof", obs_col="rv_x", min_n=30 if fast else 150)])

    frame = frame.assign(zone=zone_label(frame), count_bucket=count_bucket(frame),
                         pitch_family=frame.AutoPitchType.astype(str).map(FAMILY))
    zones = (frame.groupby(["pitch_family", "count_bucket", "zone"], observed=True)
             .agg(pitches=("rv_x", "size"), location_value=("loc_value_oof", "mean"), observed_rv_x=("rv_x", "mean"))
             .reset_index())
    zones = zones[zones.pitches >= (5 if fast else 200)]

    model = LocationModel(**rounds).fit(frame)
    rho_hh = api.resolve_rho("harp_helu")
    step = 0.25 if fast else 0.125
    grid = heatmap_grid(model, rhos=(1.0, rho_hh), xs=np.round(np.arange(-1.5, 1.51, step), 3),
                        zs=np.round(np.arange(0.5, 4.51, step), 3))
    g = grid.assign(zone=zone_label(grid))
    alt = (g.assign(air=np.where(g.rho == 1.0, "sea_level", "harp_helu"))
           .pivot_table(index=["AutoPitchType", "zone"], columns="air", values="loc_value", aggfunc="mean")
           .reset_index().rename(columns={"AutoPitchType": "pitch_type"}))
    alt["delta_cdmx"] = alt["harp_helu"] - alt["sea_level"]

    r2 = float("nan")
    if out_dir is not None:
        r2 = _update_bundle(model, frame, model.location_value(frame), out_dir, rounds=60 if fast else 300)
    if write_reports:
        REPORTS.mkdir(parents=True, exist_ok=True)
        metrics.round(5).to_csv(REPORTS / "metrics.csv", index=False)
        comp.round(5).to_csv(REPORTS / "component_metrics.csv", index=False)
        zones.round(5).to_csv(REPORTS / "zones.csv", index=False)
        rel.round(4).to_csv(REPORTS / "reliability.csv", index=False)
        alt.round(5).to_csv(REPORTS / "altitude_by_zone.csv", index=False)
        _plot_heatmaps(grid[grid.rho == 1.0], REPORTS / "heatmap_sea_level.png", "Location+ · nivel del mar")
        _plot_heatmaps(grid[grid.rho == rho_hh], REPORTS / "heatmap_harp_helu.png", "Location+ · aire del Harp Helú")
    return {"metrics": metrics, "components": comp, "reliability": rel, "zones": zones, "altitude": alt,
            "grid": grid, "model": model, "distill_r2": r2}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--bundle", default=None, help="bundle dir to update (default: the active bundle)")
    args = ap.parse_args()
    from stuffplus.io import load_raw

    frame = _stuff_run().prepare(schema.clean(load_raw()))
    res = train(frame, fast=args.fast, out_dir=Path(args.bundle) if args.bundle else bundle_dir())
    print(res["metrics"][["model", "rmse", "skill_vs_baseline", "skill_lo", "skill_hi"]].round(5).to_string(index=False))
    print(res["components"].round(4).to_string(index=False))
    print(res["reliability"].round(3).to_string(index=False))
    a = res["altitude"]
    print(a[a.zone.isin(["1", "2", "3", "5", "7", "8", "9"])].round(4).to_string(index=False))
    print(f"distill R2 {res['distill_r2']:.3f}")


if __name__ == "__main__":
    main()
