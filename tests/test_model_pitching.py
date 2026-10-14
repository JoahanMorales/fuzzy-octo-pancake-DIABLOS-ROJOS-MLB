"""HACK-012: Pitching+ multi-target model, sign-constrained combination, neutral batters, bundle update."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import api, schema, serving
from stuffplus.models import multitarget as mt
from stuffplus.models import pitching

ROOT = Path(__file__).resolve().parent.parent


def _load(rel):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_"), ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def result(tmp_path_factory, _synthetic_cache):
    stuff_run, pit_run = _load("analysis/stuff_model/run.py"), _load("analysis/pitching_model/run.py")
    clean = schema.clean(_synthetic_cache.copy())
    bundle = tmp_path_factory.mktemp("bundle_pitch")
    stuff_run.train(stuff_run.prepare(clean), bundle, fast=True, write_reports=False)
    d = pit_run.prepare(clean)
    return d, pit_run.run(d, fast=True, out_dir=bundle, write_reports=False), bundle


def test_features_exist_and_do_not_leak(result):
    d, _, _ = result
    schema.assert_no_target_leak(pitching.PITCHING_FEATURES, allow_location=True)
    missing = set(pitching.PITCHING_FEATURES) - set(d.columns) - set(pitching.BATTER_PART)
    assert not missing
    assert "AutoPitchType" not in pitching.PITCHING_FEATURES


def test_batter_quality_is_shrunk_and_neutralizable():
    tr = pd.DataFrame({"batter_anon_id": ["a"] * 10 + ["b"] * 1000, "year": 2025,
                       "rv_x": [1.0] * 10 + [0.0] * 1000, "t_whiff": 0.2})
    tab, mu = pitching.batter_table(tr, k=200)
    assert 0 < tab.loc[("a", 2025), "batter_rv"] < 0.1  # 10 pitches barely move the prior
    te = pd.DataFrame({"batter_anon_id": ["a", "zzz"], "year": 2025})
    assert pitching.with_batter(te, tab, mu).batter_rv.notna().all()
    neutral = pitching.with_batter(te, tab, mu, neutral=True)
    assert (neutral.batter_rv == mu["batter_rv"]).all()


def test_combiner_respects_signs():
    rng = np.random.default_rng(0)
    R = pd.DataFrame({k: rng.uniform(0, 1, 5000) for k in mt.REGRESSORS})
    y = 0.3 * R["hard_contact_rate"] - 0.2 * R["whiff_rate"] + 0.5 * R["groundball_rate"] + rng.normal(0, 0.05, 5000)
    c = mt.Combiner().fit(R, y.to_numpy())
    for k, s in mt.REGRESSORS.items():
        assert c.weights[k] * s >= -1e-9, k  # groundball's true +0.5 is clipped to 0 by the sign rule
    assert c.weights["hard_contact_rate"] == pytest.approx(0.3, abs=0.05)
    assert c.weights["groundball_rate"] == pytest.approx(0.0, abs=1e-9)


def test_reports(result):
    _, res, _ = result
    m = res["metrics"]
    assert set(m.target) == {"rv_x", "rv"} and {"pitching_components", "pitching_combined"} <= set(m.model)
    assert set(res["targets"].target) == set(mt.TARGETS)
    w = res["weights"]
    assert (w.final_runs_per_sd * w.expected_sign >= -1e-9).all()
    assert {"first_n", "stuff_model"} <= set(res["predictiveness"].columns)


def test_neutral_batter_changes_predictions(result):
    _, res, _ = result
    d = res["frame"]
    assert not np.allclose(d.xrv_combined, d.xrv_neutral)


def test_bundle_pitching_model_is_served(result, monkeypatch):
    _, _, bundle = result
    man = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert man["models"]["pitching_xrv"]["task"] == "HACK-012"
    assert set(man["models"]["pitching_xrv"]["features"]) == set(pitching.SERVING_FEATURES)
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(bundle))
    serving.reset_cache()
    p = api.PitchInput("Four-Seam", "Right", 95, 2400, 210, 17, 8, plate_x=0.3, plate_z=3.3, balls=1, strikes=2,
                       batter_side="Left")
    r = api.predict_pitch(p)
    assert np.isfinite(r["pitching_plus"]) and r["pitching_plus"] != r["stuff_plus"]
    serving.reset_cache()
