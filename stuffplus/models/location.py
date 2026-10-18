"""Location+ model: the marginal value of where a pitch was thrown (HACK-011).

Inputs are ONLY location and situation: plate location (arm-side mirrored), count, batter side, the
altitude-invariant pitch family (``features.identity``; Trackman's AutoPitchType relabels pitches with air
density, so it is never used here) and air density; no pitch physics. Same component design as Stuff+ (``models.stuff``):
``xRV_loc = Σ P(outcome | location, count, …) · V(outcome)`` with contact value from a regression on balls in play.

Location value = ``xRV_loc − mean xRV_loc for that count and pitch type``, so a 3-0 count is not blamed on the
location and a 0-2 count is not credited to it. Location+ = 100 + 10·z(−location value).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd

from stuffplus.models.common import BASE_PARAMS, as_model_frame
from stuffplus.models.stuff import OUTCOMES, StuffModel, outcome_class
from stuffplus.schema import assert_no_target_leak

LOCATION_FEATURES = ["plate_x_arm", "PlateLocHeight", "Balls", "Strikes", "same_side", "is_rhp", "pitch_family", "rho"]
ZONE_X = 0.83  # half plate (8.5 in) + ball radius, ft
ZONE_Z = (1.5, 3.5)  # league-average vertical zone, ft
CLASS_PARAMS = {"learning_rate": 0.08, "num_leaves": 127, "min_data_in_leaf": 300}
COUNT_BUCKETS = {"ahead": ("0-1", "0-2", "1-2"), "even": ("0-0", "1-1", "2-2"), "behind": ("1-0", "2-0", "2-1", "3-0", "3-1", "3-2")}


def add_pitch_family(df: pd.DataFrame) -> pd.DataFrame:
    """Add the altitude-invariant ``pitch_family`` (per pitcher-season mixture fitted on sea-level games).

    Pitches the mixture leaves unassigned keep their AutoPitchType (a small share; reported by the caller).
    """
    from stuffplus.features.identity import assign_pitch_id

    out = df if "pitch_family" in df and "pitch_id" in df else assign_pitch_id(df)
    fam = out["pitch_family"].astype(object)
    out = out.copy()
    out["pitch_family_assigned"] = fam.notna()
    out["pitch_family"] = fam.where(fam.notna(), out["AutoPitchType"].astype(str)).astype(str)
    return out


def zone_label(df: pd.DataFrame) -> pd.Series:
    """Zones 1–9 (rows top→bottom, columns arm side→glove side) and shadow/chase/waste regions outside."""
    x = df["plate_x_arm"].astype(float).to_numpy()
    z = df["PlateLocHeight"].astype(float).to_numpy()
    lo, hi = ZONE_Z
    inside = (np.abs(x) <= ZONE_X) & (z >= lo) & (z <= hi)
    col = np.clip(((ZONE_X - x) / (2 * ZONE_X / 3)).astype(int), 0, 2)  # arm side (x>0) first
    row = np.clip(((hi - z) / ((hi - lo) / 3)).astype(int), 0, 2)
    dist = np.maximum.reduce([np.abs(x) - ZONE_X, lo - z, z - hi])
    label = np.where(inside, (row * 3 + col + 1).astype(str),
                     np.where(dist <= 0.25, "shadow", np.where(dist <= 1.0, "chase", "waste")))
    return pd.Series(label, index=df.index, name="zone")


def count_bucket(df: pd.DataFrame) -> pd.Series:
    lookup = {c: b for b, cs in COUNT_BUCKETS.items() for c in cs}
    return df["count"].astype(str).map(lookup).fillna("even").rename("count_bucket")


@dataclass
class LocationModel(StuffModel):
    features: list[str] = field(default_factory=lambda: list(LOCATION_FEATURES))
    class_rounds: int = 300
    contact_rounds: int = 200
    reference: pd.Series | None = None  # mean xRV_loc by (count, AutoPitchType)

    def _fit_parts(self, df: pd.DataFrame):
        assert_no_target_leak(self.features, allow_location=True)
        y = outcome_class(df).to_numpy()
        ok = y >= 0
        X = as_model_frame(df, self.features)
        clf = lgb.train({**BASE_PARAMS, **CLASS_PARAMS, "objective": "multiclass", "num_class": len(OUTCOMES)},
                        lgb.Dataset(X[ok], y[ok]), num_boost_round=self.class_rounds)
        ip = y == 4
        reg = lgb.train({**BASE_PARAMS, "objective": "regression", "learning_rate": 0.05, "num_leaves": 31,
                         "min_data_in_leaf": 1000}, lgb.Dataset(X[ip], df[self.target].to_numpy(float)[ip]),
                        num_boost_round=self.contact_rounds)
        values = pd.Series(df[self.target].to_numpy(float)[ok]).groupby(y[ok]).mean().to_dict()
        return clf, reg, {int(k): float(v) for k, v in values.items()}

    def fit(self, df: pd.DataFrame) -> "LocationModel":
        super().fit(df)
        self.reference = self._reference(df, self.predict_xrv(df))
        return self

    @staticmethod
    def _key(df: pd.DataFrame) -> pd.Series:
        return df["count"].astype(str) + "|" + df["pitch_family"].astype(str)

    def _reference(self, df: pd.DataFrame, xrv: np.ndarray) -> pd.Series:
        return pd.Series(xrv, index=df.index).groupby(self._key(df)).mean()

    def location_value(self, df: pd.DataFrame, xrv: np.ndarray | None = None) -> np.ndarray:
        """xRV_loc minus the league mean for the same count and pitch type (negative = good location)."""
        if self.reference is None or self.classifier is None:
            raise RuntimeError("LocationModel is not fitted: call fit() first")
        missing = [c for c in self.features + ["count"] if c not in df]
        if missing:
            raise KeyError(f"missing columns for Location+: {missing}")
        xrv = self.predict_xrv(df) if xrv is None else xrv
        ref = self._key(df).map(self.reference).fillna(float(np.mean(self.reference))).to_numpy()
        return np.asarray(xrv, float) - ref

    def oof(self, df: pd.DataFrame, folds: Sequence[tuple[np.ndarray, np.ndarray]]) -> pd.DataFrame:
        res = pd.DataFrame(index=df.index, columns=[f"p_{o}" for o in OUTCOMES] + ["contact_rv", "xrv", "loc_value"], dtype=float)
        for tr, te in folds:
            m = LocationModel(class_rounds=self.class_rounds, contact_rounds=self.contact_rounds, target=self.target)
            m.fit(df.iloc[tr])
            comp = m.predict_components(df.iloc[te])
            comp["loc_value"] = m.location_value(df.iloc[te], comp["xrv"].to_numpy())
            res.iloc[te] = comp.to_numpy()
        return res


def heatmap_grid(
    model: LocationModel, pitch_types: Sequence[str] = ("Four-Seam", "Slider", "Changeup"),
    counts: Sequence[str] = ("1-2", "1-1", "2-1"), rhos: Sequence[float] = (1.0,),
    xs: np.ndarray | None = None, zs: np.ndarray | None = None,
) -> pd.DataFrame:
    """Location value on a plate grid (RHP vs RHB, arm-side x) for each pitch family × count × air density."""
    xs = np.round(np.arange(-1.5, 1.51, 0.125), 3) if xs is None else xs
    zs = np.round(np.arange(0.5, 4.51, 0.125), 3) if zs is None else zs
    gx, gz = np.meshgrid(xs, zs)
    frames = []
    for pt in pitch_types:
        for cnt in counts:
            b, s = (float(v) for v in cnt.split("-"))
            for rho in rhos:
                frames.append(pd.DataFrame({
                    "plate_x_arm": gx.ravel(), "PlateLocHeight": gz.ravel(), "Balls": b, "Strikes": s, "count": cnt,
                    "same_side": 1, "is_rhp": 1, "pitch_family": pt, "rho": rho}))
    grid = pd.concat(frames, ignore_index=True)
    grid["loc_value"] = model.location_value(grid)
    return grid[["pitch_family", "count", "rho", "plate_x_arm", "PlateLocHeight", "loc_value"]]


# --- production Location+ (HACK-057): temperature, chosen by the pre-registered rule of HACK-053 ------------------
PRODUCTION_CALIBRATION = "temperature"


def fit_production_location(train: pd.DataFrame, calibration: str = PRODUCTION_CALIBRATION, k_inner: int = 3,
                            **rounds) -> LocationModel:
    """LocationModel + nested calibration; the count × family reference is recomputed on calibrated predictions."""
    from stuffplus.calibration import fit_nested

    m = fit_nested(lambda: LocationModel(**rounds), train, calibration, k_inner=k_inner)
    if calibration != "none":
        m.reference = m._reference(train, m.predict_xrv(train))
    return m


def production_location_oof(df: pd.DataFrame, folds: Sequence[tuple[np.ndarray, np.ndarray]], **kw) -> np.ndarray:
    """Out-of-fold Location+ value (negative = good location) with the production model."""
    out = np.full(len(df), np.nan)
    for tr, te in folds:
        m = fit_production_location(df.iloc[tr], **kw)
        out[te] = m.location_value(df.iloc[te])
    return out
