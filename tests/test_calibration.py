"""HACK-053: nested probability calibration (temperature, isotonic) for the outcome models (synthetic data)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from stuffplus import calibration as cal
from stuffplus import schema, splits
from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.models.location import LocationModel, add_pitch_family
from stuffplus.models.stuff import StuffModel, outcome_class

ROOT = Path(__file__).resolve().parent.parent
FAST = dict(class_rounds=8, contact_rounds=6)


@pytest.fixture(scope="module")
def frame(_synthetic_cache):
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _, d = mod.prepare(schema.clean(_synthetic_cache.copy()))
    return d.reset_index(drop=True)


def _overconfident(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    logits = rng.normal(size=(n, 5))
    true = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
    y = np.array([rng.choice(5, p=p) for p in true])
    sharp = np.exp(logits * 2.5)
    return sharp / sharp.sum(axis=1, keepdims=True), y


def test_temperature_undoes_overconfidence():
    P, y = _overconfident()
    t = cal.Temperature().fit(P, y)
    assert 2.0 < t.T < 3.0
    Q = t.transform(P)
    assert np.allclose(Q.sum(axis=1), 1)
    assert cal.log_loss(Q, y) < cal.log_loss(P, y)
    assert cal.classwise_ece(Q, y) < cal.classwise_ece(P, y)


def test_isotonic_renormalizes_and_improves_ece():
    P, y = _overconfident(seed=1)
    Q = cal.Isotonic().fit(P, y).transform(P)
    assert np.allclose(Q.sum(axis=1), 1) and (Q > 0).all()
    assert cal.classwise_ece(Q, y) < cal.classwise_ece(P, y)


def test_metrics_ignore_unlabelled_rows():
    P = np.full((4, 5), 0.2)
    y = np.array([0, -1, 2, -1])
    assert cal.log_loss(P, y) == pytest.approx(-np.log(0.2))


def test_calibrated_wrapper_recomputes_xrv_with_the_model_combination(frame):
    m = StuffModel(features=list(STUFF_FEATURES_INVARIANT), **FAST).fit(frame)
    wrapped = cal.calibrated(m, cal.Temperature(T=2.0))
    raw, new = m.predict_components(frame), wrapped.predict_components(frame)
    assert np.allclose(new[cal.P_COLS].sum(axis=1), 1)
    assert not np.allclose(raw.xrv, new.xrv)
    expected = m._combine(new[cal.P_COLS].to_numpy(), new.contact_rv.to_numpy(), m.class_values)
    assert np.allclose(new.xrv, expected)
    assert isinstance(wrapped, StuffModel) and wrapped.classifier is m.classifier  # same trees, new head
    ident = cal.calibrated(m, cal.Identity())
    assert np.allclose(ident.predict_xrv(frame), m.predict_xrv(frame))


def test_location_model_keeps_location_value_when_calibrated(frame):
    d = add_pitch_family(frame) if "pitch_family" not in frame else frame
    m = LocationModel(**FAST).fit(d)
    w = cal.calibrated(m, cal.Temperature(T=1.5))
    assert np.isfinite(w.location_value(d)).all()


def test_nested_evaluation_never_uses_the_scored_fold(frame, monkeypatch):
    folds = list(splits.pitcher_group_kfold(frame, k=2))
    seen = []
    real = cal.oof_probs

    def spy(factory, df, k=3):
        seen.append(set(df.pitcher_anon_id))
        return real(factory, df, k=k)

    monkeypatch.setattr(cal, "oof_probs", spy)
    factory = lambda: StuffModel(features=list(STUFF_FEATURES_INVARIANT), **FAST)
    out = cal.evaluate_methods(factory, frame, folds, ["none", "temperature", "isotonic"], k_inner=2)
    for (tr, te), inner in zip(folds, seen):
        assert not inner & set(frame.pitcher_anon_id.iloc[te])  # calibrator data never contains test pitchers
    y = outcome_class(frame).to_numpy()
    for m in ("none", "temperature", "isotonic"):
        assert np.isfinite(out[m]["xrv"]).all() and np.isfinite(cal.log_loss(out[m]["P"], y))
