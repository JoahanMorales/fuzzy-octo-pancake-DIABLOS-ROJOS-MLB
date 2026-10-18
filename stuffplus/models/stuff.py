"""Stuff+ model: pitch physics → expected run value through pitch-outcome components (HACK-010).

Why components and not a direct regression: per-pitch run value is dominated by ball/strike noise (the v0
direct regression beat the count baseline by 0.02 %). Instead we predict what physics does control:

1. ``P(outcome | stuff)`` for 5 outcomes: ball (incl. HBP), called strike, whiff, foul, ball in play;
2. ``E[rv_x | in play, stuff]``: contact quality (``rv_x`` values batted balls by EV/LA/altitude);
3. ``xRV = Σ_c P(c) · V(c)`` with ``V(c)`` the LMB mean ``rv_x`` of each outcome (in play: model 2).

On the real data this stabilizes fast (split-half r 0.80 vs 0.20 for observed run value) and with 50
pitches predicts the rest of the season 4.5× better than the pitcher's own results (see reports/stuff_model).

Air: features carry the movement IN THE AIR of the pitch (``InducedVertBreak``, ``hb_arm``) plus ``rho``;
``predict_at_rho`` translates movement to another air first (Magnus ∝ ρ, the v0 rule; HACK-004's fitted
translation plugs in through ``translate``). For serving, the composite is distilled into one LightGBM
regressor (``distill``) so ``stuffplus.serving`` keeps a single ``stuff_xrv`` model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd

from stuffplus.models.common import BASE_PARAMS, add_arm_side_features, as_model_frame
from stuffplus.schema import assert_no_target_leak

OUTCOMES = ("ball", "called_strike", "whiff", "foul", "in_play")
FASTBALLS = ("Four-Seam", "Sinker")
STUFF_FEATURES = [
    "RelSpeed", "SpinRate", "spin_axis_arm", "InducedVertBreak", "hb_arm", "RelHeight", "rel_side_arm",
    "Extension", "arm_angle", "is_rhp", "AutoPitchType", "rho", "velo_diff_fb", "ivb_diff_fb", "hb_diff_fb",
]
CLASS_PARAMS = {"learning_rate": 0.08, "num_leaves": 63, "min_data_in_leaf": 500}
CONTACT_PARAMS = {"learning_rate": 0.05, "num_leaves": 31, "min_data_in_leaf": 1000}


def outcome_class(df: pd.DataFrame) -> pd.Series:
    """0 ball/HBP · 1 called strike · 2 whiff · 3 foul · 4 in play · -1 other."""
    call = df["PitchCall"].astype(str)
    cls = np.select(
        [call.isin(["BallCalled", "BallinDirt", "HitByPitch", "BallIntentional", "AutomaticBall"]),
         call.isin(["StrikeCalled", "AutomaticStrike"]), call.eq("StrikeSwinging"),
         call.str.startswith("FoulBall"), call.eq("InPlay")],
        [0, 1, 2, 3, 4], -1)
    return pd.Series(cls, index=df.index, name="outcome")


def add_stuff_features(df: pd.DataFrame) -> pd.DataFrame:
    """Arm-side physics, arm angle and differences vs the pitcher-season primary fastball.

    Arsenal features use only the pitcher's own physical measurements (no outcomes), so they never leak.
    HACK-006 provides the richer arsenal/tunneling set; these three diffs are the minimal version.
    """
    out = add_arm_side_features(df) if "hb_arm" not in df else df.copy()
    out["arm_angle"] = np.degrees(np.arctan2(out["RelHeight"].astype(float) - 5.0, out["rel_side_arm"].abs()))
    fb = out[out["AutoPitchType"].astype(str).isin(FASTBALLS)]
    prim = fb.groupby(["pitcher_anon_id", "year"]).agg(
        _fb_velo=("RelSpeed", "mean"), _fb_ivb=("InducedVertBreak", "mean"), _fb_hb=("hb_arm", "mean"))
    out = out.join(prim, on=["pitcher_anon_id", "year"])
    out["velo_diff_fb"] = out["RelSpeed"] - out["_fb_velo"]
    out["ivb_diff_fb"] = out["InducedVertBreak"] - out["_fb_ivb"]
    out["hb_diff_fb"] = out["hb_arm"] - out["_fb_hb"]
    return out.drop(columns=["_fb_velo", "_fb_ivb", "_fb_hb"])


def magnus_translate(df: pd.DataFrame, rho_to, rho_from) -> pd.DataFrame:
    """Default air translation: break ∝ ρ (also shifts the fastball-relative movement diffs)."""
    out = df.copy()
    scale = np.asarray(rho_to, float) / np.asarray(rho_from, float)
    for c in ("InducedVertBreak", "HorzBreak", "hb_arm"):
        if c in out:
            out[c] = out[c].astype(float) * scale
    if "ivb_diff_fb" in out:  # the primary fastball's movement moves with the same air
        out["ivb_diff_fb"] = out["ivb_diff_fb"] * scale
        out["hb_diff_fb"] = out["hb_diff_fb"] * scale
    out["rho"] = np.broadcast_to(np.asarray(rho_to, float), len(out)) if np.ndim(rho_to) == 0 else np.asarray(rho_to, float)
    return out


@dataclass
class StuffModel:
    features: list[str] = field(default_factory=lambda: list(STUFF_FEATURES))
    class_rounds: int = 300
    contact_rounds: int = 200
    target: str = "rv_x"
    classifier: lgb.Booster | None = None
    contact: lgb.Booster | None = None
    class_values: dict[int, float] = field(default_factory=dict)
    translate: Callable = magnus_translate

    def _fit_parts(self, df: pd.DataFrame):
        assert_no_target_leak(self.features, allow_location=False)
        y = outcome_class(df).to_numpy()
        ok = y >= 0
        X = as_model_frame(df, self.features)
        clf = lgb.train({**BASE_PARAMS, **CLASS_PARAMS, "objective": "multiclass", "num_class": len(OUTCOMES)},
                        lgb.Dataset(X[ok], y[ok]), num_boost_round=self.class_rounds)
        ip = y == 4
        reg = lgb.train({**BASE_PARAMS, **CONTACT_PARAMS, "objective": "regression"},
                        lgb.Dataset(X[ip], df[self.target].to_numpy(float)[ip]), num_boost_round=self.contact_rounds)
        values = pd.Series(df[self.target].to_numpy(float)[ok]).groupby(y[ok]).mean().to_dict()
        return clf, reg, {int(k): float(v) for k, v in values.items()}

    def fit(self, df: pd.DataFrame) -> "StuffModel":
        self.classifier, self.contact, self.class_values = self._fit_parts(df)
        return self

    @staticmethod
    def _combine(probs: np.ndarray, contact: np.ndarray, values: dict[int, float]) -> np.ndarray:
        v = np.array([values.get(c, 0.0) for c in range(len(OUTCOMES))])
        return probs[:, :4] @ v[:4] + probs[:, 4] * contact

    def predict_components(self, df: pd.DataFrame) -> pd.DataFrame:
        X = as_model_frame(df, self.features)
        probs = self.classifier.predict(X)
        out = pd.DataFrame(probs, columns=[f"p_{o}" for o in OUTCOMES], index=df.index)
        out["contact_rv"] = self.contact.predict(X)
        out["xrv"] = self._combine(probs, out["contact_rv"].to_numpy(), self.class_values)
        return out

    def predict_xrv(self, df: pd.DataFrame) -> np.ndarray:
        return self.predict_components(df)["xrv"].to_numpy()

    def predict_at_rho(self, df: pd.DataFrame, rho, rho_from: str | float = "rho") -> pd.DataFrame:
        """Components for the same pitches thrown in air ``rho`` (movement translated from ``rho_from``)."""
        src = df[rho_from].to_numpy(float) if isinstance(rho_from, str) else rho_from
        return self.predict_components(self.translate(df, rho, src))

    def oof(self, df: pd.DataFrame, folds: Sequence[tuple[np.ndarray, np.ndarray]]) -> pd.DataFrame:
        """Out-of-fold components and xRV (each fold's model never saw that fold's pitchers)."""
        res = pd.DataFrame(index=df.index, columns=[f"p_{o}" for o in OUTCOMES] + ["contact_rv", "xrv"], dtype=float)
        for tr, te in folds:
            m = StuffModel(self.features, self.class_rounds, self.contact_rounds, self.target, translate=self.translate)
            m.fit(df.iloc[tr])
            res.iloc[te] = m.predict_components(df.iloc[te]).to_numpy()
        return res

    def distill(self, df: pd.DataFrame, xrv: np.ndarray, rounds: int = 400) -> tuple[lgb.Booster, float]:
        """One regressor reproducing the composite xRV (for serving). Returns (booster, in-sample R²)."""
        X = as_model_frame(df, self.features)
        booster = lgb.train({**BASE_PARAMS, "objective": "regression", "learning_rate": 0.1, "num_leaves": 127,
                             "min_data_in_leaf": 100}, lgb.Dataset(X, xrv), num_boost_round=rounds)
        pred = booster.predict(X)
        r2 = 1 - float(((xrv - pred) ** 2).sum() / ((xrv - xrv.mean()) ** 2).sum())
        return booster, r2


def matched_sample_predictiveness(
    df: pd.DataFrame, pred_col: str, sizes: Sequence[int] = (50, 100, 200, 400), rest_min: int = 300,
    obs_cols: Sequence[str] = ("rv", "rv_x"), target_col: str = "rv",
) -> pd.DataFrame:
    """First N pitches of a pitcher-season → mean of ``target_col`` over the rest of that season.

    Compares the model's mean prediction with the pitcher's own observed results over the same N pitches.
    Rows are in game order, so "first N" is chronological.
    """
    key = ["pitcher_anon_id", "year"]
    i = df.groupby(key).cumcount()
    n = df.groupby(key)[target_col].transform("size")
    rows = []
    for size in sizes:
        d = df[n >= size + rest_min]
        first_mask = i[d.index] < size
        first = d[first_mask].groupby(key)[[pred_col, *obs_cols]].mean()
        rest = d[~first_mask].groupby(key)[target_col].mean().rename("rest")
        j = first.join(rest)
        row = {"first_n": size, "pitcher_seasons": len(j), "stuff_model": j[pred_col].corr(j["rest"])}
        row.update({f"observed_{c}": j[c].corr(j["rest"]) for c in obs_cols})
        rows.append(row)
    return pd.DataFrame(rows)


def split_half_reliability(df: pd.DataFrame, pred_col: str, obs_col: str = "rv", min_n: int = 150) -> dict:
    """Correlation of pitcher-season means between odd and even games (how stable is the metric?)."""
    half = pd.factorize(df["game_anon_id"])[0] % 2
    g = df.assign(_h=half).groupby(["pitcher_anon_id", "year", "_h"]).agg(
        p=(pred_col, "mean"), o=(obs_col, "mean"), n=(obs_col, "size")).unstack("_h")
    g = g[(g["n"][0] >= min_n) & (g["n"][1] >= min_n)]
    return {"pairs": int(len(g)), "stuff_model": float(g["p"][0].corr(g["p"][1])),
            f"observed_{obs_col}": float(g["o"][0].corr(g["o"][1]))}


# --- production Stuff+ (HACK-057) ------------------------------------------------------------------------------
# Adopted by joahan on 2026-10-16/17: Stuff+ v2 (HACK-052, R4 instead of R3, `uak decision`) with the temperature
# calibrator chosen by the pre-registered rule of HACK-053 (reports/calibration/decision.csv). StuffModel above stays
# as v1 for the ablations and v1 vs v2 comparisons.
PRODUCTION_VERSION = "stuff_v2"
PRODUCTION_CALIBRATION = "temperature"


class CountNeutral:
    """Production Stuff+: a fitted (calibrated) StuffV2Model whose ``xrv`` is the count-neutral stuff value
    (``StuffV2Model.stuff_value``: Σ_c w_family(c)·[xRV(c) − m_c]), so Stuff+ never credits or blames the count the
    pitch was thrown in. Components (probabilities, contact value) are the model's own at the pitch's count. Every
    other attribute (``translate``, ``features``, ``class_values``...) is the wrapped model's."""

    def __init__(self, model):
        self.model = model

    def __getattr__(self, name):
        return getattr(self.model, name)

    def predict_components(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self.model.predict_components(df).copy()
        out["xrv"] = self.model.stuff_value(df)
        return out

    def predict_xrv(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.stuff_value(df)

    def predict_at_rho(self, df: pd.DataFrame, rho, rho_from: str | float = "rho") -> pd.DataFrame:
        src = df[rho_from].to_numpy(float) if isinstance(rho_from, str) else rho_from
        return self.predict_components(self.model.translate(df, rho, src))


def fit_production_stuff(train: pd.DataFrame, translate: Callable | None = None, calibration: str = PRODUCTION_CALIBRATION,
                         k_inner: int = 3, **rounds) -> CountNeutral:
    """The production Stuff+ model fitted on ``train``: StuffV2Model + nested calibration, count-neutral value."""
    from stuffplus.calibration import fit_nested
    from stuffplus.models.stuff_v2 import StuffV2Model

    kw = dict(rounds, **({"translate": translate} if translate is not None else {}))
    return CountNeutral(fit_nested(lambda: StuffV2Model(**kw), train, calibration, k_inner=k_inner))
