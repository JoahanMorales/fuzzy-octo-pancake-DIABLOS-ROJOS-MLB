"""Smooth physics effects plus ridge-pooled shape intercepts, fitted jointly."""
from __future__ import annotations

import numpy as np
import pandas as pd
from pygam import LinearGAM, l, s, te

FEATURES = ("RelSpeed", "InducedVertBreak", "hb_arm", "rho")


class GAMShapeModel:
    """Fixed penalties; unseen/missing shapes receive the population smooth.

    Shape coefficients have a common Gaussian/ridge penalty (partial pooling).
    This pools intercepts, not entire shape-specific smooths. AutoPitchType is
    an explicitly tracker-derived proxy; pass a prepared pitch_family instead
    when an appropriate training-only identity mapping is available.
    """

    def __init__(self, shape_col="AutoPitchType", n_splines=6, lam=10.0, pool_lam=20.0):
        if n_splines < 4 or lam <= 0 or pool_lam <= 0:
            raise ValueError("Require n_splines >= 4 and positive penalties")
        self.shape_col, self.n_splines = shape_col, n_splines
        self.lam, self.pool_lam = lam, pool_lam
        self.model = None

    def _numeric(self, frame):
        return frame.loc[:, FEATURES].astype(float).replace([np.inf, -np.inf], np.nan)

    def _matrix(self, frame):
        numeric = self._numeric(frame).fillna(self.medians).to_numpy()
        labels = frame[self.shape_col].astype("string")
        columns = [labels.eq(label).fillna(False).to_numpy(dtype=float) for label in self.shapes]
        return np.column_stack([numeric, *columns]) if columns else numeric

    def fit(self, frame: pd.DataFrame):
        y = frame["rv_x"].to_numpy(float)
        if len(y) < 2 or not np.isfinite(y).all():
            raise ValueError("Training requires at least two finite rv_x values")
        self.medians = self._numeric(frame).median()
        if self.medians.isna().any():
            raise ValueError("All-missing training features: " + ", ".join(self.medians.index[self.medians.isna()]))
        self.shapes = sorted(frame[self.shape_col].dropna().astype(str).unique())
        terms = s(0, n_splines=self.n_splines, lam=self.lam)
        terms += s(1, n_splines=self.n_splines, lam=self.lam)
        terms += s(2, n_splines=self.n_splines, lam=self.lam)
        terms += te(1, 3, n_splines=self.n_splines, lam=self.lam)
        for i in range(len(self.shapes)):
            terms += l(4 + i, lam=self.pool_lam)
        self.model = LinearGAM(terms).fit(self._matrix(frame), y)
        return self

    def predict_xrv(self, frame: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("Fit the GAM before predicting")
        if frame.empty:
            return np.empty(0)
        return self.model.predict(self._matrix(frame))
