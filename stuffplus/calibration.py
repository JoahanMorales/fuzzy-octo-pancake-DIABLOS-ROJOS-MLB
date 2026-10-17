"""Probability calibration for the 5-outcome models (HACK-053).

Boosted trees push probabilities away from the truth (Niculescu-Mizil & Caruana 2005); temperature scaling fixes
the spread with one parameter (Guo et al. 2017); one-vs-rest isotonic regression fixes any monotone distortion and
needs more data (we have it). Calibration is always NESTED: the calibrator is fitted on out-of-fold predictions
made inside the training set (``fit_nested``), never on the rows it will score.

``calibrated(model, cal)`` wraps any fitted outcome model that exposes ``predict_components`` with ``p_<outcome>``
columns (StuffModel, LocationModel, PitchingComponents, StuffV2Model): it recalibrates the probabilities and
recomputes xRV with the model's own combination (``_xrv`` when present, else ``_combine``). For models with
per-count recentring (``count_offset``), the offsets are refitted on the calibrated training predictions.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression

from stuffplus import splits
from stuffplus.models.stuff import OUTCOMES, outcome_class

EPS = 1e-9
P_COLS = [f"p_{o}" for o in OUTCOMES]


# ------------------------------------------------------------------ metrics
def log_loss(P: np.ndarray, y: np.ndarray) -> float:
    ok = y >= 0
    return float(-np.log(np.clip(P[ok][np.arange(ok.sum()), y[ok]], EPS, 1)).mean())


def classwise_ece(P: np.ndarray, y: np.ndarray, bins: int = 15) -> float:
    """Mean over classes of the expected calibration error of P(class) (equal-width bins)."""
    ok = y >= 0
    P, y = P[ok], y[ok]
    eces = []
    for k in range(P.shape[1]):
        p, t = P[:, k], (y == k).astype(float)
        idx = np.minimum((p * bins).astype(int), bins - 1)
        n = np.bincount(idx, minlength=bins)
        conf = np.bincount(idx, p, minlength=bins)
        acc = np.bincount(idx, t, minlength=bins)
        m = n > 0
        eces.append(float(np.sum(np.abs(acc[m] - conf[m])) / len(p)))
    return float(np.mean(eces))


def slope(y: np.ndarray, p: np.ndarray) -> float:
    """OLS slope of the outcome on the prediction (1 = calibrated spread)."""
    ok = np.isfinite(y) & np.isfinite(p)
    return float(np.polyfit(p[ok], y[ok], 1)[0])


# ------------------------------------------------------------------ calibrators
@dataclass
class Temperature:
    """softmax(log p / T): one parameter, keeps the ranking, shrinks (T > 1) or sharpens (T < 1) the spread."""
    T: float = 1.0

    def fit(self, P: np.ndarray, y: np.ndarray) -> "Temperature":
        ok = y >= 0
        logp = np.log(np.clip(P[ok], EPS, 1))
        yy = y[ok]

        def nll(t):
            z = logp / t
            z = z - z.max(axis=1, keepdims=True)
            lse = np.log(np.exp(z).sum(axis=1))
            return float(-(z[np.arange(len(yy)), yy] - lse).mean())

        self.T = float(minimize_scalar(nll, bounds=(0.25, 4.0), method="bounded").x)
        return self

    def transform(self, P: np.ndarray) -> np.ndarray:
        z = np.log(np.clip(P, EPS, 1)) / self.T
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)


@dataclass
class Isotonic:
    """One-vs-rest isotonic regression per outcome, then renormalized to sum to 1."""
    models: list = field(default_factory=list)

    def fit(self, P: np.ndarray, y: np.ndarray) -> "Isotonic":
        ok = y >= 0
        self.models = [IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(P[ok, k], (y[ok] == k).astype(float))
                       for k in range(P.shape[1])]
        return self

    def transform(self, P: np.ndarray) -> np.ndarray:
        Q = np.column_stack([m.predict(P[:, k]) for k, m in enumerate(self.models)])
        Q = np.clip(Q, EPS, None)
        return Q / Q.sum(axis=1, keepdims=True)


@dataclass
class Identity:
    def fit(self, P, y):
        return self

    def transform(self, P):
        return P


CALIBRATORS: dict[str, Callable[[], object]] = {"none": Identity, "temperature": Temperature, "isotonic": Isotonic}


# ------------------------------------------------------------------ wrapping a fitted model
def _calibrated_predict_components(self, df: pd.DataFrame) -> pd.DataFrame:
    out = type(self).__mro__[1].predict_components(self, df)
    P = self._calibrator.transform(out[P_COLS].to_numpy(float))
    out[P_COLS] = P
    contact = out["contact_rv"].to_numpy(float)
    if hasattr(self, "_xrv"):
        out["xrv"] = self._xrv(df, P, contact)
    else:
        out["xrv"] = self._combine(P, contact, self.class_values)
    return out


def calibrated(model, cal, train: pd.DataFrame | None = None):
    """A copy of the fitted ``model`` whose probabilities pass through ``cal``. With ``train`` and a
    ``count_offset`` attribute (Stuff+ v2), the per-count recentring is refitted on calibrated predictions."""
    base = type(model)
    cls = type(f"Calibrated{base.__name__}", (base,), {"predict_components": _calibrated_predict_components})
    new = copy.copy(model)
    new.__class__ = cls
    new._calibrator = cal
    if train is not None and getattr(new, "count_offset", None) is not None:
        from stuffplus.models.stuff_v2 import _count_key  # only models that have count_offset

        new.count_offset = new.count_offset * 0.0
        raw = pd.Series(new.predict_components(train)["xrv"].to_numpy()).groupby(_count_key(train).to_numpy()).mean()
        new.count_offset = (new.count_mean - raw.reindex(new.count_offset.index)).fillna(0.0)
    return new


def oof_probs(factory: Callable[[], object], df: pd.DataFrame, k: int = 3) -> np.ndarray:
    """Out-of-fold outcome probabilities inside ``df`` (pitcher-grouped folds)."""
    P = np.full((len(df), len(OUTCOMES)), np.nan)
    for tr, te in splits.pitcher_group_kfold(df, k=k):
        m = factory().fit(df.iloc[tr])
        P[te] = m.predict_components(df.iloc[te])[P_COLS].to_numpy(float)
    return P


def fit_nested(factory: Callable[[], object], train: pd.DataFrame, method: str, k_inner: int = 3):
    """Fit the model on ``train`` and a calibrator on inner out-of-fold predictions of ``train``."""
    model = factory().fit(train)
    if method == "none":
        return model
    y = outcome_class(train).to_numpy()
    P = oof_probs(factory, train, k=k_inner)
    ok = np.isfinite(P).all(axis=1)
    cal = CALIBRATORS[method]().fit(P[ok], np.where(ok, y, -1)[ok])
    return calibrated(model, cal, train=train)


def evaluate_methods(factory: Callable[[], object], df: pd.DataFrame, folds: Sequence, methods: Sequence[str],
                     k_inner: int = 3, value_fn: Callable | None = None) -> dict[str, dict[str, np.ndarray]]:
    """Outer-fold predictions (probabilities and xRV) for each calibration method; the inner OOF probabilities
    are shared by the methods of a fold so they are computed once. ``value_fn(model, test)`` adds a per-pitch
    pitcher-level value (e.g. Stuff+ v2's count-marginalized ``stuff_value``); default = xRV."""
    y = outcome_class(df).to_numpy()
    out = {m: {"P": np.full((len(df), len(OUTCOMES)), np.nan), "xrv": np.full(len(df), np.nan),
               "value": np.full(len(df), np.nan)} for m in methods}
    for tr, te in folds:
        train, test = df.iloc[tr], df.iloc[te]
        model = factory().fit(train)
        P_in = oof_probs(factory, train, k=k_inner) if any(m != "none" for m in methods) else None
        y_in = y[tr]
        for m in methods:
            if m == "none":
                fitted = model
            else:
                ok = np.isfinite(P_in).all(axis=1) & (y_in >= 0)
                fitted = calibrated(model, CALIBRATORS[m]().fit(P_in[ok], y_in[ok]), train=train)
            comp = fitted.predict_components(test)
            out[m]["P"][te] = comp[P_COLS].to_numpy(float)
            out[m]["xrv"][te] = comp["xrv"].to_numpy(float)
            out[m]["value"][te] = value_fn(fitted, test) if value_fn else out[m]["xrv"][te]
    return out
