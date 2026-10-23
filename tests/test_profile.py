"""HACK-017: ideal physical profile (PDP feature × ρ through the physics translation, hull-bounded search)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import profile, schema
from stuffplus.models.location import add_pitch_family
from stuffplus.models.stuff import STUFF_FEATURES, StuffModel
from stuffplus.scale import PlusScaler

ROOT = Path(__file__).resolve().parent.parent
FEATURES = [("pitch_family" if f == "AutoPitchType" else f) for f in STUFF_FEATURES]


def _prepare(df_clean: pd.DataFrame) -> pd.DataFrame:
    spec = importlib.util.spec_from_file_location("stuff_run", ROOT / "analysis" / "stuff_model" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return add_pitch_family(mod.prepare(df_clean))


@pytest.fixture(scope="module")
def fitted(_synthetic_cache):
    d = _prepare(schema.clean(_synthetic_cache.copy()))
    model = StuffModel(features=FEATURES, class_rounds=30, contact_rounds=20).fit(d)
    scaler = PlusScaler().fit(d.assign(x=model.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    sea = profile.to_sea_level(model, d)
    return model, scaler, d, sea


def test_sea_level_frame_has_rho_one_and_less_ride_in_thin_air(fitted):
    model, _, d, sea = fitted
    assert np.allclose(sea["rho"], 1.0)
    fb = sea[profile.is_fastball(sea) & (sea["InducedVertBreak"] > 5)].head(50)
    thin = model.translate(fb, 0.82, fb["rho"].to_numpy(float))
    assert (thin["InducedVertBreak"] < fb["InducedVertBreak"]).all()  # Magnus ∝ ρ: ride shrinks


def test_set_feature_moves_secondary_diff_but_not_fastball_diff():
    df = pd.DataFrame({"pitch_family": ["Four-Seam", "Slider"], "RelSpeed": [94.0, 85.0], "velo_diff_fb": [0.0, -9.0]})
    out = profile.set_feature(df, "RelSpeed", 90.0)
    assert out.velo_diff_fb.tolist() == [0.0, -4.0]


def test_pdp_grid_inside_quantiles_and_sensitivity_columns(fitted):
    model, scaler, _, sea = fitted
    base = sea.sample(300, random_state=0)
    pdp = profile.pdp_2d(model, scaler, base, ["RelSpeed", "InducedVertBreak"], rhos=[1.0, 0.82], n_grid=4)
    assert len(pdp) == 2 * 4 * 2
    lo, hi = base["RelSpeed"].quantile([0.05, 0.95])
    v = pdp.loc[pdp.feature == "RelSpeed", "value"]
    assert v.min() == pytest.approx(lo) and v.max() == pytest.approx(hi)
    sens = profile.rho_sensitivity(pdp, rho_alt=0.82)
    assert set(sens.verdict) <= {"importa más en altitud", "importa menos en altitud", "igual"}
    h = profile.h_statistic(pdp)
    assert ((h.h2_rho >= 0) & (h.h2_rho <= 1)).all()


def test_h_statistic_zero_for_additive_and_positive_for_interaction():
    vals, rhos = np.linspace(0, 1, 5), [1.0, 0.9, 0.8]
    add = pd.DataFrame([{"feature": "a", "value": v, "rho": r, "stuff_plus": 3 * v + 10 * r} for v in vals for r in rhos])
    inter = pd.DataFrame([{"feature": "b", "value": v, "rho": r, "stuff_plus": 5 * v * r} for v in vals for r in rhos])
    h = profile.h_statistic(pd.concat([add, inter])).set_index("feature").h2_rho
    assert h["a"] == pytest.approx(0.0, abs=1e-12) and h["b"] > 0


def test_knn_hull_rejects_far_outlier():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))
    keep = profile.knn_in_hull(np.vstack([X[:5], [[20.0, 20.0, 20.0]]]), ref=X)
    assert not keep[-1]


def test_delta_by_bins_ci_contains_mean():
    rng = np.random.default_rng(1)
    n = 600
    trait = pd.Series(rng.normal(size=n), name="spin_eff")
    delta = pd.Series(-5 + 2 * trait + rng.normal(size=n))
    pitchers = pd.Series(rng.integers(0, 40, n))
    t = profile.delta_by_bins(delta, trait, pitchers, n_bins=4, n_boot=200)
    assert len(t) == 4 and (t.delta_lo <= t.delta_stuff).all() and (t.delta_stuff <= t.delta_hi).all()
    assert t.delta_stuff.is_monotonic_increasing


def test_candidates_and_arsenals_stay_observed(fitted):
    model, scaler, _, sea = fitted
    cents = profile.centroids(sea, min_n=20)
    assert (cents["n"] >= 20).all() and np.allclose(cents.groupby(["pitcher_anon_id", "year"]).usage.sum(), 1.0)
    fb, stats = profile.best_fastballs(model, scaler, cents, rho_alt=0.82, top=3)
    assert len(fb) > 0 and -1 <= stats["spearman_alt_vs_sea"] <= 1
    assert fb.stuff_alt.is_monotonic_decreasing
    sec = profile.secondaries_given_fastball(model, scaler, cents, fb.iloc[0], rho_alt=0.82)
    assert (~sec.pitch_family.isin(profile.FASTBALL_FAMILIES)).all()
    if len(sec):
        assert np.allclose(sec.velo_diff_fb, sec.RelSpeed - fb.iloc[0].RelSpeed)
    ars = profile.best_arsenals(profile.score_profiles(model, scaler, cents, 0.82))
    if len(ars):
        assert ars.arsenal.str.count(r"\+").eq(2).all()


def test_ideal_profile_run_uses_production_stuff(_synthetic_cache):
    """HACK-077: analysis/ideal_profile fits the production Stuff+ (nested calibration, count-neutral value)."""
    from stuffplus.models.stuff import CountNeutral

    spec = importlib.util.spec_from_file_location("ideal_run", ROOT / "analysis" / "ideal_profile" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    shape_model, d = mod._altitude_run().prepare(schema.clean(_synthetic_cache.copy()))
    model, scaler = mod.fit(d, shape_model, fast=True)
    assert isinstance(model, CountNeutral)
    res = mod.run(d, model, scaler, fast=True)
    assert {"pdp", "sens", "hstat", "shap"} <= set(res) and len(res["sens"]) > 0
