"""HACK-005: null baselines and the evaluation harness."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stuffplus import baseline, evaluate, schema, splits, targets


@pytest.fixture
def frame(synthetic_pitches):
    return targets.build(schema.clean(synthetic_pitches))[0]


def test_count_baseline_learns_count_means(frame):
    b = baseline.CountBaseline(min_n=1).fit(frame, ["rv", "t_whiff"])
    pred = b.predict(frame, "rv")
    expected = frame.groupby("count").rv.transform("mean")
    assert np.allclose(pred, expected)
    w = b.predict(frame, "t_whiff")
    assert w.between(0, 1).all() and w.notna().all()


def test_unseen_cells_fall_back_to_global(frame):
    b = baseline.CountBaseline(by=("count", "pitch_family")).fit(frame, ["rv"])
    odd = frame.head(3).assign(count="9-9")
    assert np.allclose(b.predict(odd, "rv"), b.globals["rv"])
    with pytest.raises(KeyError):
        b.predict(frame, "t_chase")


def test_pitch_family_mapping(frame):
    fam = baseline.pitch_family(frame)
    assert set(fam) <= {"FB", "BB", "OS"}


def test_regression_and_classification_metrics():
    y = np.array([0.0, 1.0, 2.0, 3.0])
    m = evaluate.regression_metrics(y, y)
    assert m["rmse"] == 0 and m["r2"] == 1
    yb = np.array([0, 0, 1, 1])
    perfect = evaluate.classification_metrics(yb, np.array([0.1, 0.2, 0.8, 0.9]))
    assert perfect["auc"] == 1.0
    assert evaluate.auc(yb, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0
    assert evaluate.classification_metrics(yb, np.full(4, 0.5))["auc"] == 0.5


def test_ece_is_small_for_calibrated_predictions():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.05, 0.95, 50_000)
    y = (rng.uniform(size=p.size) < p).astype(float)
    assert evaluate.classification_metrics(y, p)["ece"] < 0.01
    assert evaluate.classification_metrics(y, np.clip(p + 0.2, 0, 1))["ece"] > 0.1
    rel = evaluate.reliability_curve(y, p)
    assert (rel.p_mean - rel.y_mean).abs().max() < 0.03


def test_compare_reports_skill_with_cluster_ci():
    rng = np.random.default_rng(1)
    n = 20_000
    groups = rng.integers(0, 200, n)
    x = rng.normal(size=n)
    y = 0.5 * x + rng.normal(size=n)
    out = evaluate.compare({"baseline": np.zeros(n), "model": 0.5 * x}, y, groups=groups, n_boot=200)
    m = out.set_index("model")
    assert m.loc["baseline", "skill_vs_baseline"] == pytest.approx(0)
    assert m.loc["model", "skill_vs_baseline"] > 0.05
    assert m.loc["model", "skill_lo"] > 0 and m.loc["model", "skill_lo"] < m.loc["model", "skill_hi"]
    yb = (rng.uniform(size=n) < 1 / (1 + np.exp(-x))).astype(float)
    pb = evaluate.compare({"baseline": np.full(n, yb.mean()), "model": 1 / (1 + np.exp(-x))}, yb, kind="probability")
    assert pb.set_index("model").loc["model", "skill_vs_baseline"] > 0


def test_oof_predict_covers_every_row_once(frame):
    folds = list(splits.pitcher_group_kfold(frame))
    pred = evaluate.oof_predict(frame, lambda tr, te: baseline.CountBaseline().fit(tr, ["rv"]).predict(te, "rv"), folds)
    assert np.isfinite(pred).all() and len(pred) == len(frame)


def test_pitcher_predictiveness_prefers_the_true_signal():
    rng = np.random.default_rng(2)
    rows = []
    for p in range(300):
        talent = rng.normal(0, 0.02)
        for year in (2024, 2025, 2026):
            rv = talent + rng.normal(0, 0.3, 400)
            rows.append(pd.DataFrame({"pitcher_anon_id": f"p{p}", "year": year, "rv": rv, "pred": talent}))
    df = pd.concat(rows, ignore_index=True)
    out = evaluate.pitcher_predictiveness(df, "pred").set_index("source")
    assert out.loc["predicted", "pairs"] == 600
    assert out.loc["predicted", "corr_next_season_rv"] > out.loc["observed", "corr_next_season_rv"]


def test_baseline_metrics_table(frame):
    t = baseline.baseline_metrics(frame, ["rv", "t_whiff"])
    assert set(t.split) == {"pitcher_kfold", "season_holdout", "park_holdout"}
    assert set(t.baseline) == {"count", "count_x_family"}
    assert t.loc[t.target == "rv", "rmse"].notna().all()
    assert t.loc[t.target == "t_whiff", "logloss"].notna().all()
