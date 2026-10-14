"""HACK-028: round-count search on inner pitchers, seed averaging and tuned model classes (synthetic data)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest

from stuffplus import schema, splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.models import tuning
from stuffplus.models.stuff import CLASS_PARAMS

ROOT = Path(__file__).resolve().parent.parent
FAST = tuning.TunedSettings(class_params={"learning_rate": 0.1, "num_leaves": 7, "min_data_in_leaf": 20},
                            class_rounds=5, contact_params={"learning_rate": 0.1, "num_leaves": 7,
                                                            "min_data_in_leaf": 20}, contact_rounds=5, seeds=(1, 2))


@pytest.fixture(scope="module")
def frame(_synthetic_cache):
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _, d = mod.prepare(schema.clean(_synthetic_cache.copy()))
    return d.reset_index(drop=True)


def test_search_reports_production_fixed_rounds_and_inner_pick(frame):
    folds = list(splits.pitcher_group_kfold(frame, k=2))
    configs = [{"learning_rate": 0.1, "num_leaves": 7, "min_data_in_leaf": 20}]
    res = tuning.search(frame, STUFF_FEATURES_INVARIANT, configs, folds, kind="outcome", max_rounds=60,
                        production=(CLASS_PARAMS, 12))
    assert set(res.config) == {"production", "c0"} and len(res) == 2 * len(folds)
    prod = res[res.config == "production"]
    assert (prod.inner_best_iter == 12).all() and np.allclose(prod.test_at_inner_best, prod.test_at_max)
    assert (res[res.config == "c0"].inner_best_iter <= 60).all()
    s = tuning.summarize(res)
    params, rounds = tuning.pick(s)
    assert params == configs[0] and 1 <= rounds <= 60


def test_search_rejects_target_leakage(frame):
    folds = list(splits.pitcher_group_kfold(frame, k=2))
    with pytest.raises(schema.LeakError):
        tuning.search(frame, ["RelSpeed", "rv_x"], [{}], folds, kind="outcome", max_rounds=5)


def test_inner_split_holds_out_whole_pitchers(frame):
    tr = np.arange(len(frame))
    fit, val = tuning.inner_split(frame, tr, frac=0.3)
    assert len(fit) + len(val) == len(tr) and len(val) > 0
    assert not set(frame.pitcher_anon_id.iloc[fit]) & set(frame.pitcher_anon_id.iloc[val])


def test_stop_on_inner_ignores_the_outer_test_set():
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"x": rng.normal(size=600)})
    y = (X.x + rng.normal(scale=3, size=600)).to_numpy()
    idx = np.arange(600)
    r = tuning.curve(X, y, {"objective": "regression", "learning_rate": 0.3, "num_leaves": 31, "min_data_in_leaf": 5},
                     idx[:400], idx[400:500], idx[500:], max_rounds=500, metric="l2", patience=20)
    assert len(r["test_curve"]) < 500  # stopped early, on the inner set
    assert len(r["test_curve"]) - r["inner_best_iter"] == 20


def test_seed_average_is_the_mean_of_its_boosters():
    rng = np.random.default_rng(1)
    X = pd.DataFrame({"a": rng.normal(size=300), "b": rng.normal(size=300)})
    y = X.a.to_numpy() + rng.normal(size=300)
    avg = tuning.train_seeds(X, y, {"objective": "regression", "num_leaves": 7, "min_data_in_leaf": 10,
                                    "bagging_fraction": 0.5}, 10, seeds=(1, 2, 3))
    assert len(avg.boosters) == 3 and isinstance(avg.boosters[0], lgb.Booster)
    assert np.allclose(avg.predict(X), np.mean([b.predict(X) for b in avg.boosters], axis=0))


def test_tuned_stuff_model_fits_and_translates(frame):
    m = tuning.TunedStuffModel(features=list(STUFF_FEATURES_INVARIANT), settings=FAST).fit(frame)
    comp = m.predict_components(frame)
    probs = comp[[c for c in comp if c.startswith("p_")]].to_numpy()
    assert np.allclose(probs.sum(axis=1), 1) and np.isfinite(comp.xrv).all()
    assert isinstance(m.classifier, tuning.SeedAverage) and len(m.classifier.boosters) == 2
    assert np.isfinite(m.predict_at_rho(frame, 0.82)["xrv"]).all()
    folds = list(splits.pitcher_group_kfold(frame, k=2))
    assert m.oof(frame, folds).xrv.notna().all()


def test_tuned_location_model_keeps_location_value(frame):
    from stuffplus.models.location import add_pitch_family

    d = add_pitch_family(frame) if "pitch_family" not in frame else frame
    m = tuning.TunedLocationModel(settings=FAST).fit(d)
    v = m.location_value(d)
    assert np.isfinite(v).all() and abs(float(np.mean(v))) < 0.05


def test_adoption_rule_needs_loss_gain_and_no_pitcher_level_drop():
    from analysis.tuning.summary import decide

    kf = pd.DataFrame({"model": ["Stuff+", "Stuff+ ajustado", "Location+", "Location+ ajustado"],
                       "outcome_logloss": [1.50, 1.49, 1.04, 1.03], "first50_r": [0.26, 0.23, 0.12, 0.13],
                       "first200_r": [0.30, 0.29, 0.18, 0.19], "split_half_r": [0.80, 0.75, 0.56, 0.58],
                       "skill_vs_baseline": [0.0, 0.0, 0.027, 0.028]})
    pk = pd.DataFrame({"model": ["Pitching+", "Pitching+ ajustado"], "skill_vs_baseline": [0.039, 0.0394],
                       "first50_r": [0.25, 0.254], "first200_r": [0.36, 0.358], "split_half_r": [0.66, 0.663]})
    alt = pd.DataFrame({"model": ["Stuff+", "Stuff+ ajustado"], "league_delta": [-10.3, -10.0],
                        "best_shape": ["sweeper", "sweeper"], "worst_shape": ["riding 4S", "riding 4S"]})
    dec = decide(kf, pk, alt).set_index("model")
    assert not dec.loc["Stuff+", "adopt"] and "split-half" in dec.loc["Stuff+", "failed"]
    assert dec.loc["Location+", "adopt"] and dec.loc["Pitching+", "adopt"]  # −0.002 is within the tolerance
