"""Evaluation harness shared by every model (HACK-005).

* ``report``: tidy metrics for one prediction vector (regression or probability).
* ``compare``: several models on the same rows, with skill vs a baseline and pitcher-cluster bootstrap CIs.
* ``reliability_curve``: calibration data for plots.
* ``oof_predict``: out-of-fold predictions over ``stuffplus.splits`` folds.
* ``pitcher_predictiveness``: does a pitcher-season's mean prediction anticipate NEXT season's run value
  better than this season's observed run value? This is how public Stuff+ models are judged.
"""
from __future__ import annotations

from typing import Callable, Iterable, Mapping

import numpy as np
import pandas as pd

EPS = 1e-6


def _clean(y, p) -> tuple[np.ndarray, np.ndarray]:
    y, p = np.asarray(y, float), np.asarray(p, float)
    ok = np.isfinite(y) & np.isfinite(p)
    return y[ok], p[ok]


def regression_metrics(y, p) -> dict[str, float]:
    y, p = _clean(y, p)
    err = y - p
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {"n": float(len(y)), "rmse": float(np.sqrt((err ** 2).mean())), "mae": float(np.abs(err).mean()),
            "r2": float(1 - (err ** 2).sum() / ss_tot) if ss_tot > 0 else np.nan, "bias": float(err.mean())}


def auc(y, p) -> float:
    """Rank AUC (Mann-Whitney), ties averaged."""
    y, p = _clean(y, p)
    pos = y == 1
    n1, n0 = int(pos.sum()), int((~pos).sum())
    if n1 == 0 or n0 == 0:
        return np.nan
    ranks = pd.Series(p).rank(method="average").to_numpy()
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def reliability_curve(y, p, bins: int = 10) -> pd.DataFrame:
    """Quantile bins of the prediction: mean predicted vs observed rate (for calibration plots)."""
    y, p = _clean(y, p)
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, len(edges) - 2)
    d = pd.DataFrame({"bin": idx, "p": p, "y": y})
    return d.groupby("bin").agg(p_mean=("p", "mean"), y_mean=("y", "mean"), n=("y", "size")).reset_index()


def classification_metrics(y, p, bins: int = 10) -> dict[str, float]:
    y, p = _clean(y, p)
    pc = np.clip(p, EPS, 1 - EPS)
    rel = reliability_curve(y, p, bins)
    ece = float((rel.n * (rel.p_mean - rel.y_mean).abs()).sum() / rel.n.sum()) if len(rel) else np.nan
    return {"n": float(len(y)), "base_rate": float(y.mean()),
            "logloss": float(-(y * np.log(pc) + (1 - y) * np.log(1 - pc)).mean()),
            "brier": float(((y - p) ** 2).mean()), "auc": auc(y, p), "ece": ece}


def report(y_true, y_pred, kind: str = "regression") -> pd.DataFrame:
    """One prediction vector → tidy (metric, value) frame. ``kind``: 'regression' or 'probability'."""
    m = regression_metrics(y_true, y_pred) if kind == "regression" else classification_metrics(y_true, y_pred)
    return pd.DataFrame({"metric": list(m), "value": list(m.values())})


def _loss_parts(y: np.ndarray, p: np.ndarray, kind: str) -> np.ndarray:
    if kind == "regression":
        return (y - p) ** 2
    pc = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(pc) + (1 - y) * np.log(1 - pc))


def compare(
    preds: Mapping[str, Iterable],
    y,
    kind: str = "regression",
    baseline: str = "baseline",
    groups=None,
    n_boot: int = 300,
    seed: int = 2240,
) -> pd.DataFrame:
    """Metrics per model on the same rows + skill vs ``baseline`` with a cluster-bootstrap 95 % CI.

    Skill = % reduction of RMSE (regression) or log-loss (probability) vs the baseline; > 0 beats it.
    ``groups`` (e.g. pitcher ids) makes the bootstrap resample whole pitchers, not single pitches.
    """
    y = np.asarray(y, float)
    P = {k: np.asarray(v, float) for k, v in preds.items()}
    if baseline not in P:
        raise KeyError(f"baseline {baseline!r} not in preds")
    ok = np.isfinite(y)
    for v in P.values():
        ok &= np.isfinite(v)
    y = y[ok]
    P = {k: v[ok] for k, v in P.items()}
    g = np.zeros(len(y), dtype=int) if groups is None else pd.factorize(np.asarray(groups)[ok])[0]
    n_groups = g.max() + 1
    counts = np.bincount(g, minlength=n_groups).astype(float)
    rng = np.random.default_rng(seed)
    w = rng.multinomial(n_groups, np.full(n_groups, 1 / n_groups), size=n_boot).astype(float) if n_groups > 1 else None

    def boot_loss(loss: np.ndarray) -> np.ndarray:
        sums = np.bincount(g, weights=loss, minlength=n_groups)
        return (w @ sums) / (w @ counts)

    base_loss = _loss_parts(y, P[baseline], kind)
    rows = []
    for name, p in P.items():
        m = regression_metrics(y, p) if kind == "regression" else classification_metrics(y, p)
        loss = _loss_parts(y, p, kind)
        if kind == "regression":
            skill = 1 - np.sqrt(loss.mean()) / np.sqrt(base_loss.mean())
            boot = 1 - np.sqrt(boot_loss(loss)) / np.sqrt(boot_loss(base_loss)) if w is not None else None
        else:
            skill = 1 - loss.mean() / base_loss.mean()
            boot = 1 - boot_loss(loss) / boot_loss(base_loss) if w is not None else None
        m.update(model=name, skill_vs_baseline=float(skill),
                 skill_lo=float(np.quantile(boot, 0.025)) if boot is not None else np.nan,
                 skill_hi=float(np.quantile(boot, 0.975)) if boot is not None else np.nan)
        rows.append(m)
    cols = ["model"] + [c for c in rows[0] if c != "model"]
    return pd.DataFrame(rows)[cols]


def oof_predict(
    df: pd.DataFrame,
    fit_predict: Callable[[pd.DataFrame, pd.DataFrame], np.ndarray],
    folds: Iterable[tuple[np.ndarray, np.ndarray]],
) -> np.ndarray:
    """Out-of-fold predictions: ``fit_predict(train_df, test_df) -> predictions for test_df``."""
    out = np.full(len(df), np.nan)
    for tr, te in folds:
        out[te] = np.asarray(fit_predict(df.iloc[tr], df.iloc[te]), float)
    return out


def pitcher_predictiveness(
    df: pd.DataFrame,
    pred_col: str,
    obs_col: str = "rv",
    min_n: int = 200,
    pitcher_col: str = "pitcher_anon_id",
) -> pd.DataFrame:
    """Correlate season-t pitcher means with season t+1 observed run value.

    Rows: ``predicted`` (mean of ``pred_col`` in t) and ``observed`` (mean of ``obs_col`` in t, the naive
    alternative). A good Stuff+ predicts next season better than last season's results do.
    """
    g = df.groupby([pitcher_col, "year"], observed=True).agg(n=(obs_col, "size"), pred=(pred_col, "mean"), obs=(obs_col, "mean"))
    g = g[g.n >= min_n].reset_index()
    nxt = g.assign(year=g.year - 1)[[pitcher_col, "year", "obs", "n"]].rename(columns={"obs": "obs_next", "n": "n_next"})
    pairs = g.merge(nxt, on=[pitcher_col, "year"])
    out = []
    for label, col in (("predicted", "pred"), ("observed", "obs")):
        r = pairs[col].corr(pairs["obs_next"]) if len(pairs) > 2 else np.nan
        out.append({"source": label, "pairs": len(pairs), "corr_next_season_rv": r})
    return pd.DataFrame(out)
