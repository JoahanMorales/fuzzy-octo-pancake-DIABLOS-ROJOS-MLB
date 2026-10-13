"""Shared model plumbing: arm-side features and LightGBM out-of-fold training (HACK-031).

Every model task (Stuff+, Location+, Pitching+, tuning) trains through ``train_lgbm_oof`` so OOF
predictions, folds and parameters are comparable.

Handedness convention (checked on the raw data): Trackman ``HorzBreak`` and ``RelSide`` are positive toward
the arm side for right-handers and mirrored for left-handers (RHP four-seam HB +8.3", LHP −8.0").
``add_arm_side_features`` puts both hands on the right-hander's frame.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd

from stuffplus.config import SEED
from stuffplus.schema import PITCH_TYPES, assert_no_target_leak

BASE_PARAMS = {
    "learning_rate": 0.05, "num_leaves": 63, "min_data_in_leaf": 200, "feature_fraction": 0.8,
    "bagging_fraction": 0.8, "bagging_freq": 1, "lambda_l2": 1.0, "verbose": -1, "seed": SEED,
    "num_threads": 0,
}
OBJECTIVES = {"regression": "regression", "binary": "binary"}


def add_arm_side_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with ``hb_arm``, ``rel_side_arm``, ``spin_axis_arm`` and ``is_rhp`` (RHP frame)."""
    out = df.copy()
    rhp = out["PitcherThrows"].astype(str).eq("Right")
    sign = np.where(rhp, 1.0, -1.0)
    out["is_rhp"] = rhp.astype(int)
    out["hb_arm"] = out["HorzBreak"].astype(float) * sign
    out["rel_side_arm"] = out["RelSide"].astype(float) * sign
    axis = out["SpinAxis"].astype(float) % 360
    out["spin_axis_arm"] = np.where(rhp, axis, (360 - axis) % 360)
    if "PlateLocSide" in out:
        out["plate_x_arm"] = out["PlateLocSide"].astype(float) * sign
    return out


def as_model_frame(df: pd.DataFrame, features: Sequence[str]) -> pd.DataFrame:
    """Feature matrix with fixed categorical levels (so saved models and single-row inputs agree)."""
    X = df[list(features)].copy()
    for c in ("AutoPitchType", "pitch_family"):  # pitch_family = altitude-invariant label (features.identity)
        if c in X:
            X[c] = pd.Categorical(X[c].astype(str), categories=PITCH_TYPES)
    for c in X.columns:
        if X[c].dtype == bool:
            X[c] = X[c].astype(int)
    return X


@dataclass
class OOFResult:
    oof: np.ndarray
    models: list = field(default_factory=list)
    features: list = field(default_factory=list)
    best_iterations: list = field(default_factory=list)


def _train_one(X, y, objective, params, num_boost_round, valid=None):
    p = {**BASE_PARAMS, **(params or {}), "objective": OBJECTIVES[objective]}
    train = lgb.Dataset(X, y, free_raw_data=False)
    callbacks = []
    valid_sets = None
    if valid is not None:
        valid_sets = [lgb.Dataset(valid[0], valid[1], reference=train)]
        callbacks.append(lgb.early_stopping(50, verbose=False))
    return lgb.train(p, train, num_boost_round=num_boost_round, valid_sets=valid_sets, callbacks=callbacks)


def train_lgbm_oof(
    df: pd.DataFrame,
    features: Sequence[str],
    target: str,
    folds: Iterable[tuple[np.ndarray, np.ndarray]],
    objective: str = "regression",
    params: dict | None = None,
    num_boost_round: int = 400,
    allow_location: bool = True,
    group_col: str = "pitcher_anon_id",
    inner_valid_frac: float = 0.1,
) -> OOFResult:
    """Out-of-fold predictions for ``target`` (rows with NaN target are skipped in training, still predicted).

    Early stopping uses an INNER validation set: ~10 % of the training fold's pitchers (by ``group_col``).
    The held-out fold is never looked at while fitting, so OOF metrics are honest out-of-sample numbers
    (with ``pitcher_group_kfold`` folds, a pitcher's own pitches are never in his model's training data).
    """
    assert_no_target_leak(features, allow_location=allow_location)
    X = as_model_frame(df, features)
    y = df[target].astype(float).to_numpy()
    codes = pd.factorize(df[group_col].astype(str))[0] if group_col in df else np.arange(len(df))
    rng = np.random.default_rng(SEED)
    inner = rng.random(codes.max() + 1) < inner_valid_frac
    res = OOFResult(oof=np.full(len(df), np.nan), features=list(features))
    for tr, te in folds:
        tr_ok = tr[np.isfinite(y[tr])]
        is_val = inner[codes[tr_ok]]
        fit_idx, val_idx = tr_ok[~is_val], tr_ok[is_val]
        model = _train_one(X.iloc[fit_idx], y[fit_idx], objective, params, num_boost_round,
                           valid=(X.iloc[val_idx], y[val_idx]) if len(val_idx) else None)
        res.oof[te] = model.predict(X.iloc[te], num_iteration=model.best_iteration or None)
        res.models.append(model)
        res.best_iterations.append(int(model.best_iteration or num_boost_round))
    return res


def fit_lgbm(
    df: pd.DataFrame,
    features: Sequence[str],
    target: str,
    objective: str = "regression",
    params: dict | None = None,
    num_boost_round: int = 300,
    allow_location: bool = True,
) -> lgb.Booster:
    """Final model on every labelled row (use the OOF best iterations to pick ``num_boost_round``)."""
    assert_no_target_leak(features, allow_location=allow_location)
    y = df[target].astype(float)
    ok = y.notna().to_numpy()
    return _train_one(as_model_frame(df.loc[ok], features), y[ok].to_numpy(), objective, params, num_boost_round)
