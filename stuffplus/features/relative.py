"""Relative features without location leakage (HACK-054).

Approach angles (VAA/HAA) are physics, but most of their variance is WHERE the pitch crossed the plate and from
how high it was released: a model that sees raw VAA sees location. Public pitch models that rank VAA first can
report high whiff AUCs that are partly location (the leak this module removes).

``ApproachResidual``: per ``pitch_family``, regress VAA on plate height + release height + extension (and HAA on
arm-side plate x + arm-side release side + extension) on TRAINING rows only; the residual (``vaa_net``,
``haa_net``) is the part of the approach angle that location and release do not explain (Shape+ v2 idea,
FanGraphs Community). ``add_hand_diffs``: velocity/movement vs the pitcher-season primary fastball thrown to the
SAME batter side (Driveline "Revisiting Stuff+", 2024), physical traits only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

VAA_X = ["PlateLocHeight", "RelHeight", "Extension"]
HAA_X = ["plate_x_arm", "rel_side_arm", "Extension"]
NET_FEATURES = ["vaa_net", "haa_net"]
HAND_FEATURES = ["velo_diff_fb_hand", "ivb_diff_fb_hand", "hb_diff_fb_hand"]


def _arm(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    sign = np.where(out["PitcherThrows"].astype(str).eq("Right"), 1.0, -1.0)
    if "plate_x_arm" not in out:
        out["plate_x_arm"] = out["PlateLocSide"].astype(float) * sign
    if "rel_side_arm" not in out:
        out["rel_side_arm"] = out["RelSide"].astype(float) * sign
    if "haa_arm" not in out:
        out["haa_arm"] = out["HorzApprAngle"].astype(float) * sign
    return out


def _ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    ok = np.isfinite(A).all(axis=1) & np.isfinite(y)
    return np.linalg.lstsq(A[ok], y[ok], rcond=None)[0] if ok.sum() > A.shape[1] else np.zeros(A.shape[1])


@dataclass
class ApproachResidual:
    """Fit on training rows; ``transform`` adds ``vaa_net``/``haa_net`` (degrees) to any frame."""
    coef: dict = field(default_factory=dict)
    r2: dict = field(default_factory=dict)  # share of VAA/HAA variance explained by location + release, by family

    def fit(self, df: pd.DataFrame) -> "ApproachResidual":
        d = _arm(df)
        for fam, g in d.groupby(d["pitch_family"].astype(str), observed=True):
            for name, target, xs in (("vaa", "VertApprAngle", VAA_X), ("haa", "haa_arm", HAA_X)):
                X, y = g[xs].to_numpy(float), g[target].to_numpy(float)
                b = _ols(X, y)
                self.coef[(fam, name)] = b
                pred = np.column_stack([np.ones(len(X)), X]) @ b
                ok = np.isfinite(pred) & np.isfinite(y)
                self.r2[(fam, name)] = float(1 - np.var(y[ok] - pred[ok]) / np.var(y[ok])) if ok.sum() > 2 else np.nan
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        d = _arm(df)
        out = df.copy()
        for name, target, xs in (("vaa", "VertApprAngle", VAA_X), ("haa", "haa_arm", HAA_X)):
            res = np.full(len(d), np.nan)
            fam = d["pitch_family"].astype(str).to_numpy()
            X = d[xs].to_numpy(float)
            for f in np.unique(fam):
                b = self.coef.get((f, name))
                if b is None:
                    continue
                m = fam == f
                res[m] = d[target].to_numpy(float)[m] - np.column_stack([np.ones(m.sum()), X[m]]) @ b
            out[f"{name}_net"] = res
        return out

    def r2_table(self) -> pd.DataFrame:
        rows = [dict(pitch_family=f, angle=n, r2_location_release=v) for (f, n), v in self.r2.items()]
        return pd.DataFrame(rows).sort_values(["angle", "pitch_family"])


def add_hand_diffs(df: pd.DataFrame, primary_col: str = "primary_fb_id", key=("pitcher_anon_id", "year")) -> pd.DataFrame:
    """Velocity / IVB / arm-side HB minus the pitcher-season primary fastball thrown to the same batter side."""
    d = _arm(df)
    if "hb_arm" not in d:
        d["hb_arm"] = d["HorzBreak"].astype(float) * np.where(d["PitcherThrows"].astype(str).eq("Right"), 1.0, -1.0)
    keys = list(key) + ["BatterSide"]
    if primary_col in d and "pitch_id" in d:
        fb = d[d["pitch_id"] == d[primary_col]]
    else:  # fallback: the most used fastball family of the pitcher-season
        fb = d[d["pitch_family"].astype(str).isin(["Four-Seam", "Sinker"])]
    ref = fb.groupby(keys, observed=True).agg(_v=("RelSpeed", "mean"), _i=("InducedVertBreak", "mean"), _h=("hb_arm", "mean"))
    out = d.join(ref, on=keys)
    out["velo_diff_fb_hand"] = out["RelSpeed"] - out["_v"]
    out["ivb_diff_fb_hand"] = out["InducedVertBreak"] - out["_i"]
    out["hb_diff_fb_hand"] = out["hb_arm"] - out["_h"]
    return out.drop(columns=["_v", "_i", "_h"])
