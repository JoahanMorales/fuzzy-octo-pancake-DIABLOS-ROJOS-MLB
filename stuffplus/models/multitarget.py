"""Multi-target outcome probabilities and their fitted combination into one xRV (HACK-012).

Each ``t_*`` target is a LightGBM classifier trained on its own denominator (whiff on swings, chase on pitches
outside the zone, …) and predicted for every pitch. The probabilities are turned into per-pitch expected event
rates (e.g. P(whiff) = P(swing) · P(whiff | swing)) and combined with a **sign-constrained ridge regression** on the
observed run value. Weights are fitted on other folds' out-of-fold predictions (nested), so the combined xRV of a
fold never used that fold's outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

from stuffplus.models.common import BASE_PARAMS, as_model_frame

TARGETS = ("t_swing", "t_whiff", "t_chase", "t_called_strike", "t_weak_contact", "t_groundball", "t_hard_contact", "t_out_in_pa")
CLASS_PARAMS = {"objective": "binary", "learning_rate": 0.08, "num_leaves": 63, "min_data_in_leaf": 300}

# per-pitch event rates (batter view: negative weight = good for the pitcher) and the sign each weight must have
REGRESSORS = {
    "whiff_rate": -1, "called_strike_rate": -1, "chase_rate": -1, "weak_contact_rate": -1, "groundball_rate": -1,
    "hard_contact_rate": +1, "out_in_pa": -1, "xrv_components": +1,
}


def fit_targets(df: pd.DataFrame, features: Sequence[str], rounds: int = 200) -> dict[str, lgb.Booster]:
    X = as_model_frame(df, features)
    models = {}
    for t in TARGETS:
        y = df[t].to_numpy(float)
        ok = np.isfinite(y)
        models[t] = lgb.train({**BASE_PARAMS, **CLASS_PARAMS}, lgb.Dataset(X[ok], y[ok]), num_boost_round=rounds)
    return models


def predict_targets(models: dict[str, lgb.Booster], df: pd.DataFrame, features: Sequence[str]) -> pd.DataFrame:
    X = as_model_frame(df, features)
    return pd.DataFrame({f"p_{t[2:]}": m.predict(X) for t, m in models.items()}, index=df.index)


def event_rates(probs: pd.DataFrame, df: pd.DataFrame, p_in_play: np.ndarray, xrv_components: np.ndarray) -> pd.DataFrame:
    """Conditional probabilities → per-pitch rates (the regressors of the combination)."""
    outside = df["outside_strike_zone"].astype(float).fillna(0).to_numpy()
    s = probs["p_swing"].to_numpy()
    return pd.DataFrame({
        "whiff_rate": s * probs["p_whiff"].to_numpy(),
        "called_strike_rate": (1 - s) * probs["p_called_strike"].to_numpy(),
        "chase_rate": outside * probs["p_chase"].to_numpy(),
        "weak_contact_rate": p_in_play * probs["p_weak_contact"].to_numpy(),
        "groundball_rate": p_in_play * probs["p_groundball"].to_numpy(),
        "hard_contact_rate": p_in_play * probs["p_hard_contact"].to_numpy(),
        "out_in_pa": probs["p_out_in_pa"].to_numpy(),
        "xrv_components": np.asarray(xrv_components, float),
    }, index=df.index)


@dataclass
class Combiner:
    """y ≈ b0 + Σ w_k · r_k with sign constraints and a small ridge penalty on standardized regressors."""

    alpha: float = 1.0
    weights: pd.Series = field(default_factory=pd.Series)
    intercept: float = 0.0
    mean_: pd.Series = field(default_factory=pd.Series)
    sd_: pd.Series = field(default_factory=pd.Series)

    def fit(self, R: pd.DataFrame, y: np.ndarray) -> "Combiner":
        ok = np.isfinite(y) & np.isfinite(R.to_numpy()).all(axis=1)
        R, y = R[ok], np.asarray(y, float)[ok]
        self.mean_, self.sd_ = R.mean(), R.std(ddof=0).replace(0, 1.0)
        Z = ((R - self.mean_) / self.sd_).to_numpy()
        n, k = Z.shape
        A = np.vstack([np.c_[np.ones(n), Z], np.c_[np.zeros(k), np.sqrt(self.alpha * n / 1e4) * np.eye(k)]])
        b = np.r_[y, np.zeros(k)]
        signs = np.array([REGRESSORS[c] for c in R.columns])
        lo = np.r_[-np.inf, np.where(signs > 0, 0.0, -np.inf)]
        hi = np.r_[np.inf, np.where(signs > 0, np.inf, 0.0)]
        sol = lsq_linear(A, b, bounds=(lo, hi), method="bvls")
        coef = sol.x[1:] / self.sd_.to_numpy()
        self.weights = pd.Series(coef, index=R.columns)
        self.intercept = float(sol.x[0] - (coef * self.mean_.to_numpy()).sum())
        return self

    def predict(self, R: pd.DataFrame) -> np.ndarray:
        return self.intercept + R[self.weights.index].to_numpy() @ self.weights.to_numpy()

    def standardized(self) -> pd.Series:
        """Weight × regressor sd: runs per one-sd change, comparable across regressors."""
        return self.weights * self.sd_


def nested_combination(R: pd.DataFrame, y: np.ndarray, folds) -> tuple[np.ndarray, pd.DataFrame]:
    """Combined xRV for each fold with weights fitted on the other folds; returns (oof, weights per fold)."""
    oof = np.full(len(R), np.nan)
    rows = []
    for i, (tr, te) in enumerate(folds):
        c = Combiner().fit(R.iloc[tr], np.asarray(y)[tr])
        oof[te] = c.predict(R.iloc[te])
        rows.append(c.standardized().rename(f"fold_{i}"))
    return oof, pd.DataFrame(rows)
