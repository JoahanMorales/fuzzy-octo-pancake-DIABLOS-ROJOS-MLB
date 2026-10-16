"""Stuff+ v2 (HACK-052): count-neutral stuff value that composes with the count baseline.

Why: pure Stuff+ (HACK-010) never sees the count, so per pitch it cannot beat the rubric's null (mean xRV by
count) — a strike is worth more at 3-0 than at 0-2. v2 lets the count *value* the outcomes and nothing else:

1. ``P(outcome | stuff, count)`` (LightGBM multiclass) and ``E[rv_x | in play, stuff, count]``: the count enters
   only as ``Balls``/``Strikes`` (``check_features``: never location, never anything else);
2. ``V_k(c)``: mean ``rv_x`` of outcome k in count c, shrunk toward the class mean in sparse cells (train only);
3. per-pitch prediction ``xRV(stuff, c) = Σ_k P_k V_k(c) + o_c`` (in play: the contact model) uses the pitch's
   real count; ``o_c`` re-centres each count on its train mean m_c, so the count null is nested exactly: the
   difference is the **incremental value of stuff over the count null**;
4. **Stuff+ v2** marginalizes the count away: ``value = Σ_c w_f(c) · [xRV(stuff, c) − m_c]`` with ``m_c`` the
   train mean of ``rv_x`` in count c and ``w_f`` the train share of each count *for the pitch's family*
   (a slider is valued in the counts where sliders are thrown). A pitcher's own count mix never moves his Stuff+.
   ``weights="league"`` (one vector for every family) is the pre-registered sensitivity row.
The model includes stuff × count interactions; that is part of the method and is reported as such.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd

from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.models.common import BASE_PARAMS, as_model_frame
from stuffplus.models.stuff import CLASS_PARAMS, CONTACT_PARAMS, OUTCOMES, StuffModel, outcome_class
from stuffplus.schema import LeakError, assert_no_target_leak

COUNT_FEATURES = ["Balls", "Strikes"]
COUNTS = [(b, s) for b in range(4) for s in range(3)]
V2_FEATURES = list(STUFF_FEATURES_INVARIANT) + COUNT_FEATURES
SHRINK_K = 200  # pitches: weight of the class mean when a (count, outcome) cell is sparse


def check_features(features) -> None:
    """Stuff v2 may add exactly ``Balls``/``Strikes`` to features that pass the pure-Stuff+ rule."""
    feats = list(features)
    base = [f for f in feats if f not in COUNT_FEATURES]
    assert_no_target_leak(base, allow_location=False)
    extra = set(feats) - set(base)
    if not extra <= set(COUNT_FEATURES):
        raise LeakError(f"Stuff v2 may only add the count, got {sorted(extra)}")


def _count_key(df: pd.DataFrame) -> pd.Series:
    return df["Balls"].astype(int).clip(0, 3).astype(str) + "-" + df["Strikes"].astype(int).clip(0, 2).astype(str)


@dataclass
class StuffV2Model(StuffModel):
    features: list[str] = field(default_factory=lambda: list(V2_FEATURES))
    count_values: pd.DataFrame | None = None  # index count "b-s", columns outcome 0..4, rv_x per outcome
    count_mean: pd.Series | None = None  # m_c: train mean rv_x by count
    family_weights: pd.DataFrame | None = None  # index pitch_family, columns count, rows sum to 1
    league_weights: pd.Series | None = None
    count_offset: pd.Series | None = None  # m_c − mean model xRV in count c (train): nests the count null exactly

    def _fit_parts(self, df: pd.DataFrame):
        check_features(self.features)
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

    def fit(self, df: pd.DataFrame) -> "StuffV2Model":
        super().fit(df)
        y = outcome_class(df).to_numpy()
        ok = y >= 0
        key = _count_key(df).to_numpy()
        target = df[self.target].to_numpy(float)
        cells = pd.DataFrame({"c": key[ok], "k": y[ok], "v": target[ok]}).groupby(["c", "k"]).v.agg(["sum", "size"])
        prior = pd.Series(self.class_values)
        shrunk = (cells["sum"] + SHRINK_K * cells.index.get_level_values("k").map(prior).to_numpy()) / (
            cells["size"] + SHRINK_K)
        table = shrunk.unstack("k").reindex(index=[f"{b}-{s}" for b, s in COUNTS], columns=range(len(OUTCOMES)))
        self.count_values = table.fillna(pd.Series(self.class_values))  # unseen cells fall back to the class mean
        self.count_mean = pd.Series(target).groupby(key).mean().reindex(table.index).fillna(float(np.nanmean(target)))
        share = pd.crosstab(df["pitch_family"].astype(str), key, normalize="index") if "pitch_family" in df else None
        self.league_weights = pd.Series(key).value_counts(normalize=True).reindex(table.index).fillna(0.0)
        self.family_weights = (share.reindex(columns=table.index).fillna(0.0) if share is not None else None)
        self.count_offset = pd.Series(0.0, index=table.index)
        raw = pd.Series(self.predict_components(df)["xrv"].to_numpy()).groupby(key).mean()
        self.count_offset = (self.count_mean - raw.reindex(table.index)).fillna(0.0)
        return self

    def _xrv(self, df: pd.DataFrame, probs: np.ndarray, contact: np.ndarray) -> np.ndarray:
        key = _count_key(df)
        v = self.count_values.loc[key].to_numpy(float)
        offset = self.count_offset.loc[key].to_numpy(float) if self.count_offset is not None else 0.0
        return (probs[:, :4] * v[:, :4]).sum(axis=1) + probs[:, 4] * contact + offset

    def predict_components(self, df: pd.DataFrame) -> pd.DataFrame:
        X = as_model_frame(df, self.features)
        probs = self.classifier.predict(X)
        out = pd.DataFrame(probs, columns=[f"p_{o}" for o in OUTCOMES], index=df.index)
        out["contact_rv"] = self.contact.predict(X) if self.contact is not None else 0.0
        out["xrv"] = self._xrv(df, probs, out["contact_rv"].to_numpy())
        return out

    def _weights(self, df: pd.DataFrame, weights: str) -> np.ndarray:
        """Per-pitch count weights (n × 12): the family's train distribution, or the league one."""
        league = np.tile(self.league_weights.to_numpy(float), (len(df), 1))
        if weights == "league" or self.family_weights is None or "pitch_family" not in df:
            return league
        fam = self.family_weights.reindex(df["pitch_family"].astype(str)).to_numpy(float, copy=True)
        missing = np.isnan(fam).any(axis=1)
        fam[missing] = league[missing]
        return fam

    def stuff_value(self, df: pd.DataFrame, weights: str = "family") -> np.ndarray:
        """Count-neutral stuff value (runs per pitch, lower = better for the pitcher): Σ_c w(c)·[xRV(c) − m_c]."""
        w = self._weights(df, weights)
        out = np.zeros(len(df))
        for j, (b, s) in enumerate(COUNTS):
            if not w[:, j].any():
                continue
            at = df.assign(Balls=b, Strikes=s)
            out += w[:, j] * (self.predict_components(at)["xrv"].to_numpy() - self.count_mean.iloc[j])
        return out

    def stuff_value_at_rho(self, df: pd.DataFrame, rho, weights: str = "family", rho_from: str = "rho") -> np.ndarray:
        src = df[rho_from].to_numpy(float) if isinstance(rho_from, str) else rho_from
        return self.stuff_value(self.translate(df, rho, src), weights=weights)


def count_only(rounds: dict | None = None) -> StuffV2Model:
    """Ablation: the same architecture with the count and no stuff (attributes the gain to stuff, not count)."""
    m = StuffV2Model(features=list(COUNT_FEATURES), **(rounds or {}))
    return m
