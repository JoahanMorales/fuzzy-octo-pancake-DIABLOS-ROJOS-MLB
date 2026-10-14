"""Fit models on shared splits and write aggregate diagnostics only.

Input targets/features are prepared globally by the current training pipeline.
These diagnostics are EXPLORATORY/TRANSDUCTIVE, never inductive OOS evidence.
Model fitting and the count baseline are train-only; preprocessing is not.
Factories accept no arguments, return fit(frame)/predict_xrv(frame) estimators.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable, Mapping

import numpy as np
import pandas as pd

from stuffplus import evaluate, splits
from stuffplus.baseline import CountBaseline
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.models.stuff import StuffModel
from stuffplus.models.location import LocationModel
from stuffplus.validation.models import PhysicsNeutralEstimator, PitchingEstimator
from stuffplus.validation.stability import stability_table

LIMITATION = (
    "Exploratory/transductive: shared preparation fits target values, density reference, "
    "pitch identity and arsenal statistics globally. Model fits are train-only but these "
    "reports do not establish inductive out-of-sample performance. Physics ablations "
    "are predictive diagnostics, not causal effects or production promotion evidence."
)


@dataclass
class ModelSpec:
    factory: Callable
    transform: Callable = lambda x: x


def default_models(fast: bool = False) -> dict[str, ModelSpec]:
    rounds = dict(class_rounds=15, contact_rounds=10) if fast else {}
    no_air = [c for c in STUFF_FEATURES_INVARIANT if c != "rho"]
    return {
        "Stuff+": ModelSpec(lambda: StuffModel(features=STUFF_FEATURES_INVARIANT, **rounds)),
        "Location+": ModelSpec(lambda: LocationModel(**rounds)),
        "Pitching+": ModelSpec(lambda: PitchingEstimator(fast=fast)),
        "Stuff+ no density": ModelSpec(lambda: StuffModel(features=no_air, **rounds)),
        "Stuff+ physics neutral": ModelSpec(lambda: PhysicsNeutralEstimator(no_air, rounds)),
    }


def split_plan(frame: pd.DataFrame, k: int = 5):
    yield "pitcher_kfold", list(splits.pitcher_group_kfold(frame, k=k))
    yield "season_holdout", [splits.season_holdout(frame)]
    yield "park_holdout", [splits.park_holdout(frame)]
    if "park_id" in frame:
        parks = sorted(frame.park_id.dropna().astype(str).unique())
        for i, park in enumerate(parks):
            # Never include unknown/unmapped parks in training implicitly.
            yield f"leave_one_park_out_{i + 1}", [splits.park_holdout(
                frame, train=[p for p in parks if p != park], test=[park], col="park_id")]


def validate_indices(folds, n: int):
    seen = set()
    for tr, te in folds:
        tr, te = np.asarray(tr), np.asarray(te)
        if not len(tr) or not len(te):
            return "empty train or test split"
        if (tr.dtype.kind not in "iu" or te.dtype.kind not in "iu"
                or len(np.unique(tr)) != len(tr) or len(np.unique(te)) != len(te)
                or np.any(tr < 0) or np.any(te < 0) or np.any(tr >= n) or np.any(te >= n)):
            raise ValueError("split contains duplicate or out-of-range positions")
        if set(tr) & set(te) or seen & set(te):
            raise ValueError("split leaks rows or predicts test rows twice")
        seen.update(te)
    return None


def run_all(frame: pd.DataFrame, out_dir: str | Path, *, demo_data: bool,
            models: Mapping[str, ModelSpec] | None = None, fast: bool = False,
            k: int = 5, n_boot: int = 300, min_n: int = 150,
            sample_sizes=(50, 100, 200, 400)) -> dict[str, pd.DataFrame]:
    """No fitted estimators or pitch/pitcher/game rows are exported.

    Missing model implementations/splits are recorded explicitly. Estimator errors
    propagate rather than hiding a failed model or shrinking its evaluation sample.
    """
    required = {"rv_x", "rv", "count", "pitcher_anon_id", "game_anon_id", "year", "altitude_category"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"missing validation columns: {sorted(missing)}")
    if frame.empty or frame[list(required - {"rv", "rv_x"})].isna().any().any():
        raise ValueError("empty frame or missing split/group keys")
    if k < 2 or frame.pitcher_anon_id.nunique() < k or n_boot < 1:
        raise ValueError("need >= k pitchers, k >= 2 and n_boot >= 1")
    frame = frame.reset_index(drop=True).copy()
    specs = dict(default_models(fast) if models is None else models)
    if "baseline" in specs:
        raise ValueError("baseline is a reserved model name")
    metric_rows, calibration, statuses, stability = [], [], [], []
    if "Pitching+" not in specs:
        statuses.append(dict(split="all", model="Pitching+", status="unavailable",
                             reason="HACK-012 model not provided; no proxy substituted"))
    if "park_id" not in frame or frame.park_id.isna().all():
        statuses.append(dict(split="leave_one_park_out", model="all", status="unavailable",
                             reason="HACK-003 recovered park IDs not provided"))
    for split_name, folds in split_plan(frame, k):
        reason = validate_indices(folds, len(frame))
        if reason:
            statuses.append(dict(split=split_name, model="all", status="skipped", reason=reason))
            continue
        indices = np.concatenate([te for _, te in folds])
        predictions = {"baseline": np.full(len(frame), np.nan)}
        predictions.update({name: np.full(len(frame), np.nan) for name in specs})
        for tr, te in folds:
            train, test = frame.iloc[tr].copy(), frame.iloc[te].copy()
            if not np.isfinite(train.rv_x.to_numpy(float)).any():
                raise ValueError(f"{split_name}: no finite training targets")
            base = np.asarray(CountBaseline().fit(train, ["rv_x"]).predict(test, "rv_x"), float)
            if base.shape != (len(te),) or not np.isfinite(base).all():
                raise ValueError("baseline: expected finite prediction for every held-out row")
            predictions["baseline"][te] = base
            for name, spec in specs.items():
                model = spec.factory()
                model.fit(spec.transform(train.copy()))
                p = np.asarray(model.predict_xrv(spec.transform(test.copy())), float)
                if p.shape != (len(te),) or not np.isfinite(p).all():
                    raise ValueError(f"{name}: expected finite prediction for every held-out row")
                predictions[name][te] = p
        y = frame.rv_x.to_numpy(float)[indices]
        ok = np.isfinite(y)
        for p in predictions.values():
            ok &= np.isfinite(p[indices])
        scored = indices[ok]
        if not len(scored):
            statuses.append(dict(split=split_name, model="all", status="skipped", reason="no finite test targets"))
            continue
        base_rmse = np.sqrt(np.mean((frame.rv_x.to_numpy(float)[scored] - predictions["baseline"][scored]) ** 2))
        if base_rmse == 0:
            raise ValueError(f"{split_name}: zero baseline loss; skill undefined")
        wide = evaluate.compare({n: p[scored] for n, p in predictions.items()},
                                frame.rv_x.to_numpy(float)[scored],
                                groups=frame.pitcher_anon_id.to_numpy()[scored], n_boot=n_boot)
        for record in wide.to_dict("records"):
            name = record.pop("model")
            for metric, value in record.items():
                metric_rows.append(dict(split=split_name, model=name, metric=metric, value=value))
            curve = evaluate.reliability_curve(frame.rv_x.to_numpy(float)[scored], predictions[name][scored])
            calibration.append(curve.assign(split=split_name, model=name))
            statuses.append(dict(split=split_name, model=name, status="evaluated", reason=""))
        if split_name == "pitcher_kfold":
            for name, p in predictions.items():
                stability.append(stability_table(frame, p, name, min_n=min_n, sample_sizes=sample_sizes))
    tables = {
        "validation_table": pd.DataFrame(metric_rows, columns=["split", "model", "metric", "value"]),
        "calibration": pd.concat(calibration, ignore_index=True) if calibration else pd.DataFrame(
            columns=["bin", "p_mean", "y_mean", "n", "split", "model"]),
        "status": pd.DataFrame(statuses, columns=["split", "model", "status", "reason"]),
        "stability": pd.concat(stability, ignore_index=True) if stability else pd.DataFrame(),
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table["demo_data"] = demo_data
        table["evidence"] = "exploratory_transductive"
        table.to_csv(out / f"{name}.csv", index=False)
    meta = dict(demo_data=demo_data, evidence="exploratory_transductive", limitation=LIMITATION,
                acceptance_complete=False, reason="inductive fold preparation and official-data validation pending",
                pitching_combination="weights fitted on inner pitcher folds of outer training data; neutral batters",
                pitch_family_fallback_fraction=(float((~frame.pitch_family_assigned).mean())
                    if "pitch_family_assigned" in frame else None),
                target="rv_x", baseline="train-only mean rv_x by count",
                ci="95% pitcher-cluster bootstrap; conditional on globally prepared targets/features",
                n_boot=n_boot, fast=fast, pitcher_folds=k, row_count=len(frame))
    (out / "provenance.json").write_text(json.dumps(meta, indent=2) + "\n")
    pivot = tables["validation_table"].pivot(index=["split", "model"], columns="metric", values="value")
    # Markdown does not require tabulate (not a project dependency).
    summary = pivot.reset_index().to_csv(index=False)
    unavailable = tables["status"].query("status != 'evaluated'").to_csv(index=False)
    (out / "validation.md").write_text(
        f"# Validation diagnostics\n\ndemo_data: {str(demo_data).lower()}\n\n{LIMITATION}\n\n"
        "RMSE skill is a fraction (0.01 = 1%). CIs resample held-out pitchers. "
        "Calibration uses mean predicted/observed rv_x, not probabilities. "
        "Park identities are inferred franchises, not verified stadium labels.\n\n"
        "HACK-014 acceptance is incomplete: inductive fold preparation and official-data "
        "evidence are pending. Sample stability uses global full-season "
        "features; it does not establish a deployment minimum pitch count.\n\n"
        f"## Metrics\n\n```csv\n{summary}```\n\n## Unavailable checks\n\n```csv\n{unavailable}```\n")
    return tables
