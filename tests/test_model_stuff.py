"""HACK-010: component Stuff+ model, validation helpers, bundle v1 and serving with arsenal features."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from stuffplus import api, schema, serving, splits
from stuffplus.models import stuff

ROOT = Path(__file__).resolve().parent.parent


def _run_module():
    spec = importlib.util.spec_from_file_location("stuff_run", ROOT / "analysis" / "stuff_model" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def trained(tmp_path_factory, _synthetic_cache):
    run = _run_module()
    frame = run.prepare(schema.clean(_synthetic_cache.copy()))
    out = tmp_path_factory.mktemp("bundle_v1")
    res = run.train(frame, out, fast=True, write_reports=False)
    return out, frame, res


def test_outcome_classes_cover_the_calls(synthetic_pitches):
    cls = stuff.outcome_class(schema.clean(synthetic_pitches))
    assert set(np.unique(cls)) <= {-1, 0, 1, 2, 3, 4}
    assert (cls >= 0).mean() > 0.99


def test_stuff_features_are_physical_only(trained):
    _, frame, _ = trained
    schema.assert_no_target_leak(stuff.STUFF_FEATURES, allow_location=False)
    assert set(stuff.STUFF_FEATURES) <= set(frame.columns)
    fb = frame[frame.AutoPitchType.astype(str).isin(stuff.FASTBALLS)]
    assert abs(fb.velo_diff_fb.mean()) < 1.5  # fastballs sit near their own primary-fastball reference


def test_components_are_probabilities_and_xrv_is_their_combination(trained):
    _, frame, res = trained
    comp = res["model"].predict_components(frame.head(200))
    P = comp[[f"p_{o}" for o in stuff.OUTCOMES]].to_numpy()
    assert np.allclose(P.sum(axis=1), 1.0, atol=1e-6) and (P >= 0).all()
    v = res["model"].class_values
    manual = P[:, :4] @ np.array([v[i] for i in range(4)]) + P[:, 4] * comp.contact_rv.to_numpy()
    assert np.allclose(manual, comp.xrv)
    assert v[2] < v[1] < v[0]  # whiff better than called strike better than ball (pitcher's view: lower rv)


def test_oof_never_trains_on_the_test_pitchers(trained):
    _, frame, _ = trained
    folds = list(splits.pitcher_group_kfold(frame))
    oof = stuff.StuffModel(class_rounds=20, contact_rounds=10).oof(frame, folds)
    assert oof.xrv.notna().all()
    for tr, te in folds:
        assert not set(frame.pitcher_anon_id.iloc[tr]) & set(frame.pitcher_anon_id.iloc[te])


def test_thinner_air_lowers_movement_and_changes_xrv(trained):
    _, frame, res = trained
    m = res["model"]
    fb = frame[frame.AutoPitchType.astype(str) == "Four-Seam"].head(300)
    sea = m.predict_at_rho(fb, 1.0)
    cdmx = m.predict_at_rho(fb, 0.81)
    assert not np.allclose(sea.xrv, cdmx.xrv)
    moved = m.translate(fb, 0.81, fb.rho.to_numpy())
    assert (moved.InducedVertBreak.abs() <= fb.InducedVertBreak.abs() / fb.rho * 0.81 + 1e-9).all()


def test_validation_tables(trained):
    _, _, res = trained
    met = res["metrics"]
    assert set(met.baseline_name) == {"mean xRV by count", "mean xRV by pitch type"}
    assert {"first_n", "stuff_model", "observed_rv"} <= set(res["predictiveness"].columns)
    rel = res["reliability"].iloc[0]
    assert rel.pairs > 0 and -1 <= rel.stuff_model <= 1
    assert res["components"].loc[0, "metric"] == "logloss"


def test_bundle_v1_serves_with_arsenal_context(trained, monkeypatch):
    out, _, res = trained
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(out))
    serving.reset_cache()
    assert res["summary"]["distill_r2"] > 0.5
    slider = api.PitchInput(pitch_type="Slider", throws="Right", velo=86, spin_rate=2550, spin_axis=95, ivb=1, hb=-11,
                            arsenal={"fb_velo": 95, "fb_ivb": 17, "fb_hb": 8})
    no_ctx = api.PitchInput(pitch_type="Slider", throws="Right", velo=86, spin_rate=2550, spin_axis=95, ivb=1, hb=-11)
    fb = api.PitchInput(pitch_type="Four-Seam", throws="Left", velo=94, spin_rate=2300, spin_axis=150, ivb=16, hb=-8)
    for p in (slider, no_ctx, fb):
        r = api.predict_pitch(p)
        assert r["demo_data"] is False and r["model_version"] == "v1-fast"
        assert np.isfinite(r["stuff_plus"]) and set(r["probs"]) == set(api.PROB_KEYS)
    cmp = api.compare_environments(slider, "harp_helu", "sea_level")
    assert cmp["delta_ivb"] <= 0 or abs(cmp["delta_ivb"]) < 1e-9
    serving.reset_cache()


def test_matched_sample_predictiveness_rewards_a_true_signal():
    import pandas as pd

    rng = np.random.default_rng(3)
    rows = []
    for p in range(150):
        talent = rng.normal(0, 0.03)
        n = 500
        rows.append(pd.DataFrame({"pitcher_anon_id": f"p{p}", "year": 2025, "game_anon_id": np.repeat(np.arange(25), 20),
                                  "rv": talent + rng.normal(0, 0.3, n), "pred": talent + rng.normal(0, 0.005, n)}))
    df = pd.concat(rows, ignore_index=True).assign(rv_x=lambda d: d.rv)
    t = stuff.matched_sample_predictiveness(df, "pred", sizes=(50,), rest_min=300)
    assert t.loc[0, "stuff_model"] > t.loc[0, "observed_rv"]
    rel = stuff.split_half_reliability(df, "pred", min_n=100)
    assert rel["stuff_model"] > rel["observed_rv"]
