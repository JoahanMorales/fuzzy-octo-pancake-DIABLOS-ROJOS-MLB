"""Model tuning (HACK-028): round counts and regularization chosen on pitcher-grouped CV, multi-seed averaging.

Why: the production models train a FIXED number of boosting rounds (300 multiclass rounds at learning rate 0.08)
with no early stopping. On held-out pitchers that overfits: the Stuff+ outcome model is best at ~35 rounds, and
at 300 it keeps only part of its log-loss gain over the prior (``reports/tuning/``).

Rules: the search uses 2024–25 only (the 2026 season holdout is never looked at); the round count is picked by an
INNER validation set of pitchers inside each training fold and scored on the outer fold; the final model uses a
fixed round count (the mean of the inner picks), never early stopping on its own data.

The tuned classes subclass the production ones and only change how the boosters are trained, so scoring,
translation and serving code work unchanged. ``SeedAverage`` averages boosters trained with different seeds.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Sequence

import lightgbm as lgb
import numpy as np
import pandas as pd

from stuffplus import splits
from stuffplus.models import multitarget as mt
from stuffplus.models.common import BASE_PARAMS, SEED, as_model_frame
from stuffplus.models.location import LocationModel
from stuffplus.models.pitching import PITCHING_FEATURES, PitchingComponents, batter_table, with_batter
from stuffplus.models.stuff import OUTCOMES, StuffModel, outcome_class
from stuffplus.schema import assert_no_target_leak

SEEDS = (SEED, SEED + 1, SEED + 2)
CONTACT_DEFAULT = {"learning_rate": 0.05, "num_leaves": 31, "min_data_in_leaf": 1000}


class SeedAverage:
    """Booster-like average of boosters trained with different seeds (``predict`` is all the models use)."""

    def __init__(self, boosters: Sequence[lgb.Booster]):
        self.boosters = list(boosters)

    def predict(self, X, **kw):
        return np.mean([b.predict(X, **kw) for b in self.boosters], axis=0)

    def feature_importance(self, *a, **kw):
        return np.mean([b.feature_importance(*a, **kw) for b in self.boosters], axis=0)


def train_seeds(X, y, params: dict, rounds: int, seeds: Sequence[int] = SEEDS) -> SeedAverage:
    return SeedAverage([lgb.train({**BASE_PARAMS, **params, "seed": s}, lgb.Dataset(X, y), num_boost_round=rounds)
                        for s in seeds])


# --------------------------------------------------------------------------------------------- search
def inner_split(d: pd.DataFrame, tr: np.ndarray, frac: float = 0.1, seed: int = SEED):
    """Split training rows into fit / inner-validation by pitcher (the outer test fold is never used)."""
    codes = pd.factorize(d.pitcher_anon_id.astype(str))[0]
    inner = np.random.default_rng(seed).random(codes.max() + 1) < frac
    return tr[~inner[codes[tr]]], tr[inner[codes[tr]]]


def _stop_on_inner(patience: int):
    """Stop when the INNER set has not improved for ``patience`` rounds (the outer test never decides)."""
    state = {"best": np.inf, "at": 0}

    def cb(env):
        loss = next(r[2] for r in env.evaluation_result_list if r[0] == "inner")
        if loss < state["best"]:
            state["best"], state["at"] = loss, env.iteration
        elif env.iteration - state["at"] >= patience:
            raise lgb.callback.EarlyStopException(state["at"], env.evaluation_result_list)
    cb.order = 30
    return cb


def curve(X: pd.DataFrame, y: np.ndarray, params: dict, fit: np.ndarray, val: np.ndarray, test: np.ndarray,
          max_rounds: int, metric: str, patience: int | None = 100) -> dict:
    """Train up to ``max_rounds`` (stopping ``patience`` rounds after the inner set stops improving; ``None`` =
    fixed rounds); return the inner-validation pick and the outer-test loss at that round."""
    ev: dict = {}
    t0 = time.time()
    cbs = [lgb.record_evaluation(ev)] + ([_stop_on_inner(patience)] if patience else [])
    lgb.train({**BASE_PARAMS, **params, "metric": metric}, lgb.Dataset(X.iloc[fit], y[fit]),
              num_boost_round=max_rounds, valid_sets=[lgb.Dataset(X.iloc[val], y[val]), lgb.Dataset(X.iloc[test], y[test])],
              valid_names=["inner", "test"], callbacks=cbs)
    vi, ti = np.asarray(ev["inner"][metric]), np.asarray(ev["test"][metric])
    best = int(vi.argmin())
    return {"inner_best_iter": best + 1, "test_at_inner_best": float(ti[best]), "test_best": float(ti.min()),
            "test_best_iter": int(ti.argmin()) + 1, "test_curve": ti, "secs": time.time() - t0}


def grid(space: dict[str, Sequence]) -> list[dict]:
    keys = list(space)
    return [dict(zip(keys, v)) for v in itertools.product(*(space[k] for k in keys))]


def search(d: pd.DataFrame, features: Sequence[str], configs: Sequence[dict], folds, *, kind: str,
           max_rounds: int = 1500, production: tuple[dict, int] | None = None, target: str = "rv_x",
           allow_location: bool = False, prepare=None) -> pd.DataFrame:
    """One row per config × fold. ``kind``: ``outcome`` (5-class), ``contact`` (rv_x | in play) or a binary
    target column name. ``production`` = (params, rounds) also reports the outer loss of the fixed-round model.
    ``prepare(train, test)`` may add fold-specific features (e.g. batter quality from the training fold only)."""
    assert_no_target_leak(list(features), allow_location=allow_location)
    rows = []
    for k, (tr, te) in enumerate(folds):
        frame = d
        if prepare is not None:
            frame = prepare(d.iloc[tr], d)
        X = as_model_frame(frame, list(features))
        if kind == "outcome":
            y = outcome_class(frame).to_numpy().astype(float)
            ok = y >= 0
            base, metric = {"objective": "multiclass", "num_class": len(OUTCOMES)}, "multi_logloss"
        elif kind == "contact":
            y = frame[target].to_numpy(float)
            ok = (outcome_class(frame).to_numpy() == 4) & np.isfinite(y)
            base, metric = {"objective": "regression"}, "l2"
        else:
            y = frame[kind].to_numpy(float)
            ok = np.isfinite(y)
            base, metric = {"objective": "binary"}, "binary_logloss"
        tr_ok, te_ok = tr[ok[tr]], te[ok[te]]
        fit, val = inner_split(frame, tr_ok)
        todo = [("production", production[0], production[1])] if production else []
        todo += [(f"c{i}", c, max_rounds) for i, c in enumerate(configs)]
        for name, params, rounds in todo:
            r = curve(X, y, {**base, **params}, fit, val, te_ok, rounds, metric,
                      patience=None if name == "production" else 100)
            row = dict(fold=k, config=name, **params, inner_best_iter=r["inner_best_iter"],
                       test_at_inner_best=r["test_at_inner_best"], test_best=r["test_best"],
                       test_best_iter=r["test_best_iter"], test_at_max=float(r["test_curve"][-1]), secs=r["secs"])
            if name == "production":
                row["test_at_inner_best"] = row["test_at_max"]  # production = fixed rounds, no early stopping
                row["inner_best_iter"] = rounds
            rows.append(row)
    return pd.DataFrame(rows)


def summarize(res: pd.DataFrame) -> pd.DataFrame:
    """Mean outer loss per config (at the inner pick), mean pick and its spread; best config first."""
    params = [c for c in res.columns if c not in {"fold", "config", "inner_best_iter", "test_at_inner_best",
                                                  "test_best", "test_best_iter", "test_at_max", "secs"}]
    g = res.groupby("config")
    out = g[params].first().join(g.agg(test_loss=("test_at_inner_best", "mean"), test_loss_sd=("test_at_inner_best", "std"),
                                       rounds=("inner_best_iter", "mean"), rounds_sd=("inner_best_iter", "std"),
                                       oracle_loss=("test_best", "mean")))
    return out.reset_index().sort_values("test_loss")


def pick(summary: pd.DataFrame) -> tuple[dict, int]:
    """Best non-production config and its fixed round count (mean inner pick, rounded)."""
    best = summary[summary.config != "production"].iloc[0]
    params = {k: (int(v) if float(v).is_integer() and k != "learning_rate" else float(v))
              for k, v in best.items() if k in {"learning_rate", "num_leaves", "min_data_in_leaf", "lambda_l2",
                                                "feature_fraction"} and pd.notna(v)}
    return params, int(round(best.rounds))


# --------------------------------------------------------------------------------------------- tuned models
@dataclass
class TunedSettings:
    class_params: dict
    class_rounds: int
    contact_params: dict = field(default_factory=lambda: dict(CONTACT_DEFAULT))
    contact_rounds: int = 200
    seeds: tuple = SEEDS


def _fit_tuned(self, df: pd.DataFrame, allow_location: bool):
    s: TunedSettings = self.settings
    assert_no_target_leak(self.features, allow_location=allow_location)
    y = outcome_class(df).to_numpy()
    ok = y >= 0
    X = as_model_frame(df, self.features)
    clf = train_seeds(X[ok], y[ok], {**s.class_params, "objective": "multiclass", "num_class": len(OUTCOMES)},
                      s.class_rounds, s.seeds)
    ip = y == 4
    reg = train_seeds(X[ip], df[self.target].to_numpy(float)[ip], {**s.contact_params, "objective": "regression"},
                      s.contact_rounds, s.seeds)
    values = pd.Series(df[self.target].to_numpy(float)[ok]).groupby(y[ok]).mean().to_dict()
    return clf, reg, {int(k): float(v) for k, v in values.items()}


@dataclass
class TunedStuffModel(StuffModel):
    settings: TunedSettings | None = None

    def _fit_parts(self, df):
        return _fit_tuned(self, df, allow_location=False)

    def oof(self, df, folds):
        res = pd.DataFrame(index=df.index, columns=[f"p_{o}" for o in OUTCOMES] + ["contact_rv", "xrv"], dtype=float)
        for tr, te in folds:
            m = TunedStuffModel(features=self.features, target=self.target, translate=self.translate,
                                settings=self.settings).fit(df.iloc[tr])
            res.iloc[te] = m.predict_components(df.iloc[te]).to_numpy()
        return res


@dataclass
class TunedLocationModel(LocationModel):
    settings: TunedSettings | None = None

    def _fit_parts(self, df):
        return _fit_tuned(self, df, allow_location=True)


@dataclass
class TunedPitchingComponents(PitchingComponents):
    settings: TunedSettings | None = None

    def _fit_parts(self, df):
        return _fit_tuned(self, df, allow_location=True)


def fit_targets(df: pd.DataFrame, rounds: dict[str, int], seeds: Sequence[int] = SEEDS) -> dict:
    """``multitarget.fit_targets`` with a round count per target and seed averaging."""
    X = as_model_frame(df, PITCHING_FEATURES)
    out = {}
    for t in mt.TARGETS:
        y = df[t].to_numpy(float)
        ok = np.isfinite(y)
        out[t] = train_seeds(X[ok], y[ok], mt.CLASS_PARAMS, rounds.get(t, 200), seeds)
    return out


def run_oof(d: pd.DataFrame, folds, comp: TunedSettings, target_rounds: dict[str, int]) -> dict:
    """``pitching.run_oof`` with tuned components and targets (actual and neutral batters)."""
    cols = [f"p_{o}" for o in OUTCOMES] + ["contact_rv", "xrv"]
    c, cn = (pd.DataFrame(index=d.index, columns=cols, dtype=float) for _ in range(2))
    probs, probs_n = [], []
    for tr, te in folds:
        TR = d.iloc[tr]
        tab, mu = batter_table(TR)
        TRb = with_batter(TR, tab, mu)
        TE, TEn = with_batter(d.iloc[te], tab, mu), with_batter(d.iloc[te], tab, mu, neutral=True)
        pc = TunedPitchingComponents(settings=comp).fit(TRb)
        c.iloc[te] = pc.predict_components(TE).to_numpy()
        cn.iloc[te] = pc.predict_components(TEn).to_numpy()
        tm = fit_targets(TRb, target_rounds, comp.seeds)
        probs.append(mt.predict_targets(tm, TE, PITCHING_FEATURES))
        probs_n.append(mt.predict_targets(tm, TEn, PITCHING_FEATURES))
    P, Pn = pd.concat(probs).reindex(d.index), pd.concat(probs_n).reindex(d.index)
    return {"rates": mt.event_rates(P, d, c["p_in_play"].to_numpy(float), c["xrv"].to_numpy(float)),
            "rates_neutral": mt.event_rates(Pn, d, cn["p_in_play"].to_numpy(float), cn["xrv"].to_numpy(float))}


class TunedPitchingEstimator:
    """Same fit/predict contract as ``validation.models.PitchingEstimator`` with tuned boosters."""

    def __init__(self, comp: TunedSettings, target_rounds: dict[str, int], inner_k: int = 3):
        self.comp, self.target_rounds, self.inner_k = comp, target_rounds, inner_k

    def fit(self, frame):
        train = frame.reset_index(drop=True).copy()
        folds = list(splits.pitcher_group_kfold(train, k=min(self.inner_k, train.pitcher_anon_id.nunique())))
        oof = run_oof(train, folds, self.comp, self.target_rounds)
        self.combiner = mt.Combiner().fit(oof["rates"], train.rv_x.to_numpy(float))
        self.batters, self.priors = batter_table(train)
        training = with_batter(train, self.batters, self.priors)
        self.component = TunedPitchingComponents(settings=self.comp).fit(training)
        self.targets = fit_targets(training, self.target_rounds, self.comp.seeds)
        return self

    def predict_xrv(self, frame):
        test = with_batter(frame, self.batters, self.priors, neutral=True)
        comp = self.component.predict_components(test)
        probs = mt.predict_targets(self.targets, test, PITCHING_FEATURES)
        rates = mt.event_rates(probs, test, comp.p_in_play.to_numpy(float), comp.xrv.to_numpy(float))
        return self.combiner.predict(rates)
