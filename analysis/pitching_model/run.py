"""Pitching+ (HACK-012): multi-target model, fitted combination, calibration, validation and bundle update.

    python analysis/pitching_model/run.py          # real data, ~25 min; run after stuff_model and location_model
    python analysis/pitching_model/run.py --fast

Reports in reports/pitching_model/ (aggregates only):
  metrics.csv           OOF per-pitch skill vs mean xRV by count (rubric's null), on rv_x and on rv
  target_metrics.csv    each outcome probability: AUC / log-loss / ECE vs a count baseline, on its denominator
  weights.csv           combination weights (runs per 1 sd of each rate): final + per fold (stability)
  predictiveness.csv    neutral-batter Pitching+: first N pitches → rest of season, vs own results
  reliability.csv       split-half reliability; calibration.png  reliability curves of the 8 targets + xRV deciles
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

from stuffplus import config, evaluate, schema, splits  # noqa: E402
from stuffplus.baseline import CountBaseline  # noqa: E402
from stuffplus.bundle import MANIFEST, bundle_dir  # noqa: E402
from stuffplus.models import multitarget as mt  # noqa: E402
from stuffplus.models.common import BASE_PARAMS, as_model_frame  # noqa: E402
from stuffplus.models.pitching import SERVING_FEATURES, build_features, combine, run_oof  # noqa: E402
from stuffplus.models.stuff import matched_sample_predictiveness, split_half_reliability  # noqa: E402
from stuffplus.scale import PlusScaler  # noqa: E402

REPORTS = config.REPORTS_DIR / "pitching_model"


def _stuff_run():
    spec = importlib.util.spec_from_file_location("stuff_run", ROOT / "analysis" / "stuff_model" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare(df_clean: pd.DataFrame) -> pd.DataFrame:
    return build_features(_stuff_run().prepare(df_clean))


def _target_metrics(d: pd.DataFrame, probs: pd.DataFrame, folds) -> pd.DataFrame:
    rows = []
    for t in mt.TARGETS:
        y = d[t].to_numpy(float)
        ok = np.isfinite(y)
        base = evaluate.oof_predict(d, lambda tr, te, t=t: CountBaseline().fit(tr, [t]).predict(te, t), folds)
        m = evaluate.classification_metrics(y[ok], probs[f"p_{t[2:]}"].to_numpy()[ok])
        b = evaluate.classification_metrics(y[ok], base[ok])
        rows.append({"target": t, "n": int(ok.sum()), "base_rate": m["base_rate"], "auc": m["auc"], "auc_count": b["auc"],
                     "logloss": m["logloss"], "logloss_count": b["logloss"],
                     "logloss_skill": 1 - m["logloss"] / b["logloss"], "ece": m["ece"]})
    return pd.DataFrame(rows)


def _calibration_plot(d: pd.DataFrame, probs: pd.DataFrame, xrv: np.ndarray, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 3, figsize=(11, 10))
    for ax, t in zip(axes.ravel(), mt.TARGETS):
        y = d[t].to_numpy(float)
        ok = np.isfinite(y)
        rel = evaluate.reliability_curve(y[ok], probs[f"p_{t[2:]}"].to_numpy()[ok], bins=10)
        ax.plot([0, 1], [0, 1], color="#999", lw=1)
        ax.plot(rel.p_mean, rel.y_mean, marker="o", color="#D71920")
        lim = max(rel.p_mean.max(), rel.y_mean.max()) * 1.1
        ax.set_xlim(0, lim), ax.set_ylim(0, lim)
        ax.set_title(t[2:], fontsize=10)
        ax.set_xlabel("predicho"), ax.set_ylabel("observado")
    ax = axes.ravel()[-1]
    q = pd.qcut(xrv, 10, labels=False, duplicates="drop")
    g = pd.DataFrame({"p": xrv, "y": d["rv_x"].to_numpy(), "q": q}).groupby("q").mean()
    ax.plot(g.p, g.y, marker="o", color="#D71920")
    lo, hi = min(g.p.min(), g.y.min()), max(g.p.max(), g.y.max())
    ax.plot([lo, hi], [lo, hi], color="#999", lw=1)
    ax.set_title("xRV combinado (deciles)", fontsize=10), ax.set_xlabel("predicho"), ax.set_ylabel("observado rv_x")
    fig.suptitle("Calibración fuera de muestra (pliegues por pitcher)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _update_bundle(d: pd.DataFrame, target: np.ndarray, out_dir: Path, rounds: int) -> float:
    import lightgbm as lgb

    manifest_path = out_dir / MANIFEST
    if not manifest_path.exists():
        return float("nan")
    ok = np.isfinite(target)
    X = as_model_frame(d[ok], SERVING_FEATURES)
    booster = lgb.train({**BASE_PARAMS, "objective": "regression", "learning_rate": 0.1, "num_leaves": 127,
                         "min_data_in_leaf": 100}, lgb.Dataset(X, target[ok]), num_boost_round=rounds)
    pred = booster.predict(X)
    r2 = 1 - float(((target[ok] - pred) ** 2).sum() / ((target[ok] - target[ok].mean()) ** 2).sum())
    booster.save_model(str(out_dir / "models" / "pitching_xrv.txt"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["models"]["pitching_xrv"] = {"file": "models/pitching_xrv.txt", "features": SERVING_FEATURES,
                                          "target": "Pitching+ combined xRV, neutral batter (HACK-012)",
                                          "objective": "regression", "distill_r2": round(r2, 4), "task": "HACK-012"}
    manifest["scalers"]["pitching"] = PlusScaler().fit(d[ok].assign(x=pred), "x").to_dict()
    manifest_path.write_text(json.dumps(manifest, indent=2, default=float), encoding="utf-8")
    return r2


def run(d: pd.DataFrame, fast: bool = False, out_dir: Path | None = None, write_reports: bool = True) -> dict:
    rounds = dict(class_rounds=40, contact_rounds=30, target_rounds=40) if fast else {}
    folds = list(splits.pitcher_group_kfold(d))
    oof = run_oof(d, folds, **rounds)
    comb = combine(oof, d["rv_x"].to_numpy(), folds)
    d = d.assign(xrv_components=oof["components"]["xrv"].to_numpy(float), xrv_combined=comb["combined"],
                 xrv_neutral=comb["combined_neutral"])
    n_boot = 100 if fast else 300
    metrics = []
    for target in ("rv_x", "rv"):
        base = evaluate.oof_predict(d, lambda tr, te, t=target: CountBaseline().fit(tr, [t]).predict(te, t), folds)
        m = evaluate.compare({"baseline": base, "pitching_components": d.xrv_components, "pitching_combined": d.xrv_combined},
                             d[target], groups=d.pitcher_anon_id, n_boot=n_boot)
        metrics.append(m.assign(target=target, baseline_name="mean xRV by count"))
    metrics = pd.concat(metrics, ignore_index=True)
    targets = _target_metrics(d, oof["probs"], folds)
    w = comb["fold_weights"].T
    weights = pd.DataFrame({"regressor": w.index, "final_runs_per_sd": comb["final"].standardized().reindex(w.index).to_numpy(),
                            "fold_mean": w.mean(axis=1).to_numpy(), "fold_sd": w.std(axis=1).to_numpy(),
                            "expected_sign": [mt.REGRESSORS[r] for r in w.index]})
    pred = matched_sample_predictiveness(d, "xrv_neutral", sizes=(25, 50) if fast else (50, 100, 200, 400),
                                         rest_min=40 if fast else 300)
    rel = pd.DataFrame([split_half_reliability(d, "xrv_neutral", min_n=30 if fast else 150)]).rename(
        columns={"stuff_model": "pitching_model"})
    nxt = evaluate.pitcher_predictiveness(d, "xrv_neutral", min_n=50 if fast else 300)
    r2 = _update_bundle(d, d["xrv_neutral"].to_numpy(float), out_dir, 60 if fast else 300) if out_dir is not None else float("nan")
    if write_reports:
        REPORTS.mkdir(parents=True, exist_ok=True)
        metrics.round(5).to_csv(REPORTS / "metrics.csv", index=False)
        targets.round(4).to_csv(REPORTS / "target_metrics.csv", index=False)
        weights.round(5).to_csv(REPORTS / "weights.csv", index=False)
        pred.round(4).to_csv(REPORTS / "predictiveness.csv", index=False)
        pd.concat([rel, nxt.assign(test="next season")], axis=1).round(4).to_csv(REPORTS / "reliability.csv", index=False)
        _calibration_plot(d, oof["probs"], d["xrv_combined"].to_numpy(float), REPORTS / "calibration.png")
    return {"metrics": metrics, "targets": targets, "weights": weights, "predictiveness": pred, "reliability": rel,
            "next_season": nxt, "distill_r2": r2, "frame": d}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--bundle", default=None)
    args = ap.parse_args()
    from stuffplus.io import load_raw

    res = run(prepare(schema.clean(load_raw())), fast=args.fast, out_dir=Path(args.bundle) if args.bundle else bundle_dir())
    print(res["metrics"][["target", "model", "rmse", "skill_vs_baseline", "skill_lo", "skill_hi"]].round(5).to_string(index=False))
    print(res["targets"].round(3).to_string(index=False))
    print(res["weights"].round(4).to_string(index=False))
    print(res["predictiveness"].round(3).to_string(index=False))
    print(res["reliability"].round(3).to_string(index=False), res["next_season"].round(3).to_string(index=False))
    print(f"distill R2 {res['distill_r2']:.3f}")


if __name__ == "__main__":
    main()
