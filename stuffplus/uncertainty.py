"""Uncertainty under environment shift (HACK-055).

- ``density_ratio``: how different is the target environment (Extreme altitude) from the training one? A classifier
  P(target | x) on the model's own inputs (out of fold, pitcher-grouped) gives w(x) = p/(1-p) · n_src/n_tgt
  (Shimodaira 2000), plus overlap diagnostics: classifier AUC (0.5 = no shift) and the effective sample size.
- ``weighted_skill``: RMSE skill vs a baseline with importance weights, to estimate target-environment performance
  from source-environment cross-validation, then compare with the real holdout.
- ``split_conformal``: distribution-free intervals from absolute residuals of a calibration set; the weighted
  version (Tibshirani, Barber, Candès & Ramdas 2019) stays valid under covariate shift when the weights are the
  density ratio; ``coverage`` checks it on held-out pitchers (Angelopoulos & Bates 2021).
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from stuffplus import splits
from stuffplus.models.common import BASE_PARAMS, as_model_frame

CLF_PARAMS = {"objective": "binary", "learning_rate": 0.05, "num_leaves": 31, "min_data_in_leaf": 500}


def density_ratio(df: pd.DataFrame, features, is_target: np.ndarray, rounds: int = 200, k: int = 5,
                  clip: float = 20.0) -> tuple[np.ndarray, dict]:
    """Out-of-fold P(target | x) and importance weights w = p/(1-p)·n_src/n_tgt (clipped), with diagnostics."""
    y = np.asarray(is_target, bool).astype(float)
    X = as_model_frame(df, list(features))
    p = np.full(len(df), np.nan)
    for tr, te in splits.pitcher_group_kfold(df, k=k):
        m = lgb.train({**BASE_PARAMS, **CLF_PARAMS}, lgb.Dataset(X.iloc[tr], y[tr]), num_boost_round=rounds)
        p[te] = m.predict(X.iloc[te])
    p = np.clip(p, 1e-4, 1 - 1e-4)
    n_tgt, n_src = y.sum(), len(y) - y.sum()
    w = np.minimum(p / (1 - p) * n_src / n_tgt, clip)
    src = y == 0
    ws = w[src]
    diag = dict(auc=float(roc_auc_score(y, p)), ess=float(ws.sum() ** 2 / (ws ** 2).sum()), n_source=int(src.sum()),
                ess_share=float(ws.sum() ** 2 / (ws ** 2).sum() / src.sum()),
                w_p50=float(np.median(ws)), w_p99=float(np.quantile(ws, 0.99)), clipped_share=float((ws >= clip).mean()))
    return w, diag


def weighted_skill(y, pred, base, w=None) -> float:
    """1 − RMSE(pred)/RMSE(base), optionally importance-weighted."""
    y, pred, base = (np.asarray(a, float) for a in (y, pred, base))
    w = np.ones_like(y) if w is None else np.asarray(w, float)
    ok = np.isfinite(y) & np.isfinite(pred) & np.isfinite(base) & np.isfinite(w)
    mse = lambda p: np.sum(w[ok] * (y[ok] - p[ok]) ** 2) / np.sum(w[ok])
    return float(1 - np.sqrt(mse(pred)) / np.sqrt(mse(base)))


def weighted_quantile(values, weights, q: float) -> float:
    """Smallest v with cumulative weight share ≥ q (values may include +inf)."""
    order = np.argsort(values)
    v, w = np.asarray(values, float)[order], np.asarray(weights, float)[order]
    cum = np.cumsum(w) / w.sum()
    return float(v[np.searchsorted(cum, q, side="left").clip(max=len(v) - 1)])


def split_conformal(resid_cal, alpha: float = 0.1, w_cal=None, w_test=None) -> np.ndarray | float:
    """Half-width of (1-alpha) intervals from calibration absolute residuals.

    Unweighted: the ceil((n+1)(1-alpha))/n empirical quantile. Weighted (covariate shift): for each test point the
    weighted quantile of the calibration residuals plus a point mass at +inf carrying the test point's weight."""
    r = np.abs(np.asarray(resid_cal, float))
    r = r[np.isfinite(r)]
    n = len(r)
    if w_cal is None:
        level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
        return float(np.quantile(r, level, method="higher"))
    wc = np.asarray(w_cal, float)
    out = []
    for wt in np.atleast_1d(w_test):
        out.append(weighted_quantile(np.append(r, np.inf), np.append(wc, wt), 1 - alpha))
    return np.array(out)


def coverage(y, center, half_width) -> float:
    y = np.asarray(y, float)
    c = np.broadcast_to(np.asarray(center, float), y.shape)
    h = np.broadcast_to(np.asarray(half_width, float), y.shape)
    ok = np.isfinite(y) & np.isfinite(c) & np.isfinite(h)
    return float(np.mean(np.abs(y[ok] - c[ok]) <= h[ok]))
