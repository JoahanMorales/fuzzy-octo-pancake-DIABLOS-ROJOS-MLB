"""Pitching+: everything about the pitch and its context → expected run value (HACK-012).

Features: release physics (altitude-invariant ``pitch_family``), arsenal and tunneling (HACK-006), location,
count/outs/times through the order, previous pitch (sequence), air density, and the batter's quality.
Batter quality (shrunk run value and whiff rate of that batter-season) is computed only from training folds and
set to the league average when scoring, so a pitcher is not rewarded for the hitters he happened to face.

Two estimates of xRV are produced and compared: the 5-outcome component composite (as Stuff+) and the HACK-012
combination of 8 outcome probabilities with fitted, sign-constrained weights (``models.multitarget``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd

from stuffplus.models import multitarget as mt
from stuffplus.models.common import BASE_PARAMS, as_model_frame
from stuffplus.models.stuff import OUTCOMES, StuffModel, outcome_class
from stuffplus.schema import assert_no_target_leak

STUFF_PART = ["RelSpeed", "SpinRate", "spin_axis_arm", "InducedVertBreak", "hb_arm", "RelHeight", "rel_side_arm",
              "Extension", "arm_angle", "is_rhp", "pitch_family", "rho"]
ARSENAL_PART = ["velo_diff_vs_fb", "ivb_diff_vs_fb", "hb_diff_vs_fb", "spin_diff_vs_fb", "axis_diff_vs_fb",
                "pitch_usage_pct", "arsenal_size", "tunnel_ratio", "decision_sep_vs_fb", "release_dist_vs_fb"]
CONTEXT_PART = ["plate_x_arm", "PlateLocHeight", "Balls", "Strikes", "Outs", "inning_capped", "same_side",
                "times_through_order", "pitch_number_in_pa", "prev_velo_diff", "prev_loc_diff"]
BATTER_PART = ["batter_rv", "batter_whiff"]
PITCHING_FEATURES = STUFF_PART + ARSENAL_PART + CONTEXT_PART + BATTER_PART
# what the dashboard can supply for a single typed pitch (used for the distilled serving model)
SERVING_FEATURES = STUFF_PART + ["velo_diff_fb", "ivb_diff_fb", "hb_diff_fb", "plate_x_arm", "PlateLocHeight",
                                 "Balls", "Strikes", "same_side"]
BATTER_PRIOR_N = 200


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add pitch_family/pitch_id, arsenal + tunneling and sequence features (physical traits only, no outcomes)."""
    from stuffplus.features.arsenal import fit_arsenal
    from stuffplus.features.sequence import add_sequence_features
    from stuffplus.models.location import add_pitch_family

    d = add_pitch_family(frame)
    d = fit_arsenal(d).transform(d)
    d = add_sequence_features(d)
    d["inning_capped"] = d["Inning"].clip(upper=10)
    return d


def batter_table(train: pd.DataFrame, k: int = BATTER_PRIOR_N) -> tuple[pd.DataFrame, dict]:
    """Shrunk batter-season run value and whiff rate, learned from ``train`` only."""
    mu = {"batter_rv": float(train["rv_x"].mean()), "batter_whiff": float(train["t_whiff"].mean())}
    g = train.groupby(["batter_anon_id", "year"]).agg(rv=("rv_x", "mean"), n=("rv_x", "size"),
                                                      wh=("t_whiff", "mean"), nw=("t_whiff", "count"))
    tab = pd.DataFrame({
        "batter_rv": (g.rv * g.n + mu["batter_rv"] * k) / (g.n + k),
        "batter_whiff": (g.wh.fillna(mu["batter_whiff"]) * g.nw + mu["batter_whiff"] * k) / (g.nw + k),
    })
    return tab, mu


def with_batter(df: pd.DataFrame, tab: pd.DataFrame, mu: dict, neutral: bool = False) -> pd.DataFrame:
    out = df.drop(columns=[c for c in BATTER_PART if c in df])
    if neutral:
        return out.assign(**mu)
    return out.join(tab, on=["batter_anon_id", "year"]).fillna(mu)


@dataclass
class PitchingComponents(StuffModel):
    """5-outcome composite with location and context allowed (Stuff+ forbids them)."""

    features: list[str] = field(default_factory=lambda: list(PITCHING_FEATURES))

    def _fit_parts(self, df: pd.DataFrame):
        assert_no_target_leak(self.features, allow_location=True)
        y = outcome_class(df).to_numpy()
        ok = y >= 0
        X = as_model_frame(df, self.features)
        clf = lgb.train({**BASE_PARAMS, "objective": "multiclass", "num_class": len(OUTCOMES), "learning_rate": 0.08,
                         "num_leaves": 127, "min_data_in_leaf": 300}, lgb.Dataset(X[ok], y[ok]), self.class_rounds)
        ip = y == 4
        reg = lgb.train({**BASE_PARAMS, "objective": "regression", "learning_rate": 0.05, "num_leaves": 31,
                         "min_data_in_leaf": 1000}, lgb.Dataset(X[ip], df[self.target].to_numpy(float)[ip]),
                        self.contact_rounds)
        values = pd.Series(df[self.target].to_numpy(float)[ok]).groupby(y[ok]).mean().to_dict()
        return clf, reg, {int(k): float(v) for k, v in values.items()}


def run_oof(d: pd.DataFrame, folds: Sequence[tuple[np.ndarray, np.ndarray]], class_rounds: int = 300,
            contact_rounds: int = 200, target_rounds: int = 200) -> dict:
    """Out-of-fold components, 8 target probabilities and event rates, with actual and neutral batters."""
    cols = [f"p_{o}" for o in OUTCOMES] + ["contact_rv", "xrv"]
    comp, comp_n = (pd.DataFrame(index=d.index, columns=cols, dtype=float) for _ in range(2))
    probs, probs_n = None, None
    for tr, te in folds:
        TR = d.iloc[tr]
        tab, mu = batter_table(TR)
        TRb = with_batter(TR, tab, mu)
        TE, TEn = with_batter(d.iloc[te], tab, mu), with_batter(d.iloc[te], tab, mu, neutral=True)
        pc = PitchingComponents(class_rounds=class_rounds, contact_rounds=contact_rounds).fit(TRb)
        comp.iloc[te] = pc.predict_components(TE).to_numpy()
        comp_n.iloc[te] = pc.predict_components(TEn).to_numpy()
        tm = mt.fit_targets(TRb, PITCHING_FEATURES, rounds=target_rounds)
        p, pn = mt.predict_targets(tm, TE, PITCHING_FEATURES), mt.predict_targets(tm, TEn, PITCHING_FEATURES)
        probs = p if probs is None else pd.concat([probs, p])
        probs_n = pn if probs_n is None else pd.concat([probs_n, pn])
    probs, probs_n = probs.reindex(d.index), probs_n.reindex(d.index)
    R = mt.event_rates(probs, d, comp["p_in_play"].to_numpy(float), comp["xrv"].to_numpy(float))
    Rn = mt.event_rates(probs_n, d, comp_n["p_in_play"].to_numpy(float), comp_n["xrv"].to_numpy(float))
    return {"components": comp, "components_neutral": comp_n, "probs": probs, "probs_neutral": probs_n,
            "rates": R, "rates_neutral": Rn}


def combine(oof: dict, y: np.ndarray, folds) -> dict:
    """Nested sign-constrained combination; neutral-batter xRV uses each fold's weights on neutral rates."""
    R, Rn = oof["rates"], oof["rates_neutral"]
    combined, weights = mt.nested_combination(R, y, folds)
    combined_n = np.full(len(R), np.nan)
    for tr, te in folds:
        c = mt.Combiner().fit(R.iloc[tr], np.asarray(y)[tr])
        combined_n[te] = c.predict(Rn.iloc[te])
    final = mt.Combiner().fit(R, np.asarray(y))
    return {"combined": combined, "combined_neutral": combined_n, "fold_weights": weights, "final": final}
