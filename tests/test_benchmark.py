"""Synthetic benchmark evidence: pooling, isolation, shared denominators, reports."""
import json

import numpy as np
import pandas as pd
import pytest

from analysis.benchmark.run import LIMITATION, benchmark, write_reports
from stuffplus.models.bench import GAMShapeModel


@pytest.fixture
def frame():
    rng = np.random.default_rng(2240)
    n = 360
    x = pd.DataFrame({
        "RelSpeed": rng.normal(92, 3, n), "InducedVertBreak": rng.normal(12, 4, n),
        "hb_arm": rng.normal(6, 3, n), "rho": rng.uniform(.8, 1, n),
        "AutoPitchType": np.tile(["Four-Seam", "Slider"], n // 2),
        "pitcher_anon_id": np.repeat(np.arange(12), n // 12),
        "year": np.tile([2024, 2025, 2026], n // 3),
        "altitude_category": np.tile(["No Altitude", "Medium Altitude", "Extreme Altitude"], n // 3),
        "count": "0-0", "PitchCall": "InPlay",
    })
    x["rv_x"] = -.03 * (x.RelSpeed - 92) + .02 * (x.InducedVertBreak - 12) * x.rho
    x["rv_x"] += .15 * x.AutoPitchType.eq("Slider") + rng.normal(0, .01, n)
    return x


def test_real_gam_learns_physics_and_pooled_shape(frame):
    train, test = frame.iloc[:270], frame.iloc[270:]
    model = GAMShapeModel(pool_lam=2).fit(train)
    error = np.mean((model.predict_xrv(test) - test.rv_x) ** 2)
    assert error < .25 * np.mean((train.rv_x.mean() - test.rv_x) ** 2)
    assert any(term.istensor for term in model.model.terms)
    strong = GAMShapeModel(pool_lam=1e7).fit(train)
    probe = test.iloc[[0, 0]].copy()
    probe["AutoPitchType"] = ["Four-Seam", "Slider"]
    assert abs(np.diff(strong.predict_xrv(probe))[0]) < abs(np.diff(model.predict_xrv(probe))[0]) / 10


def test_preprocessing_uses_training_only_and_unknown_shapes_pool(frame):
    train = frame.iloc[:270].copy()
    train.loc[0, "RelSpeed"] = np.nan
    model = GAMShapeModel().fit(train)
    medians = model.medians.copy()
    before = model.model.coef_.copy()
    probe = frame.iloc[270:275].copy()
    probe["RelSpeed"] = np.nan
    probe["AutoPitchType"] = "new-shape"
    a = model.predict_xrv(probe)
    probe["AutoPitchType"] = pd.NA
    np.testing.assert_allclose(a, model.predict_xrv(probe))
    probe["rho"] = 9  # held-out feature mutation must not change fitted state
    model.predict_xrv(probe)
    pd.testing.assert_series_equal(medians, model.medians)
    np.testing.assert_array_equal(before, model.model.coef_)
    assert medians.RelSpeed == train.RelSpeed.median()


def test_invalid_training_and_unfitted_model(frame):
    with pytest.raises(ValueError, match="Fit the GAM"):
        GAMShapeModel().predict_xrv(frame)
    with pytest.raises(ValueError, match="All-missing"):
        GAMShapeModel().fit(frame.assign(rho=np.nan))
    with pytest.raises(ValueError, match="finite rv_x"):
        GAMShapeModel().fit(frame.assign(rv_x=np.nan))


def test_shared_splits_no_model_fit_leak_and_aggregate_reports(frame, tmp_path):
    fits = []

    class Spy:
        def fit(self, train):
            self.train = train.index.to_numpy()
            self.mean = train.rv_x.mean()
            fits.append(self.train)
            return self

        def predict_xrv(self, test):
            assert not np.intersect1d(self.train, test.index).size
            return np.full(len(test), self.mean)

    frame.loc[0, "rv_x"] = np.nan
    result = benchmark(frame, demo_data=True, fast=True, factories={"gam": Spy, "lightgbm": Spy})
    assert len(fits) == 14
    for i in range(0, len(fits), 2):
        np.testing.assert_array_equal(fits[i], fits[i + 1])
        assert 0 not in fits[i]
    metrics = result["metrics"]
    assert len(metrics) == 12 and metrics.groupby("split").n.nunique().eq(1).all()
    assert metrics.demo_data.all() and np.isfinite(metrics.rmse).all()
    write_reports(result, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {"metrics.csv", "calibration.csv", "folds.csv", "metadata.json"}
    metadata = json.loads((tmp_path / "metadata.json").read_text())
    assert metadata["demo_data"] and metadata["excluded_nonfinite_targets"] == 1
    assert metadata["limitation"] == LIMITATION and "transductive" in LIMITATION
    for key in ("metrics", "calibration", "folds"):
        assert "pitcher_anon_id" not in result[key].columns


@pytest.mark.parametrize("mutation, error", [
    ({"year": 2024}, "empty/insufficient"),
    ({"PitchCall": "StrikeCalled"}, "no in-play"),
])
def test_unavailable_folds_abort_explicitly(frame, mutation, error):
    class Mean:
        def fit(self, train):
            return self

        def predict_xrv(self, test):
            return np.zeros(len(test))

    with pytest.raises(ValueError, match=error):
        benchmark(frame.assign(**mutation), demo_data=True, fast=True, factories={"gam": Mean, "lightgbm": Mean})
