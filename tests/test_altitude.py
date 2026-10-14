"""HACK-015: physics translation, counterfactual ΔStuff+, delta tables and observed triangulation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from stuffplus import altitude, schema

ROOT = Path(__file__).resolve().parent.parent


def _run_module():
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def result(_synthetic_cache):
    run = _run_module()
    shape_model, d = run.prepare(schema.clean(_synthetic_cache.copy()))
    return shape_model, d, run.run(shape_model, d, fast=True, write_reports=False)


def _shape_model():
    return SimpleNamespace(rho_ref=0.93, rho_effect={"Four-Seam": {"ivb": 1.2, "hb": 0.8},
                                                     "Curveball": {"ivb": 1.2, "hb": 0.8}})


def test_translation_moves_break_toward_zero_in_thin_air():
    df = pd.DataFrame({"pitch_family": ["Four-Seam", "Curveball"], "PitcherThrows": ["Right", "Left"],
                       "InducedVertBreak": [18.0, -10.0], "hb_arm": [9.0, 8.0], "HorzBreak": [9.0, -8.0],
                       "ivb_diff_fb": [0.0, -28.0], "hb_diff_fb": [0.0, -1.0], "rho": [1.0, 1.0]})
    t = altitude.physics_translator(_shape_model())(df, 0.82, df["rho"].to_numpy())
    assert t.InducedVertBreak[0] < 18.0  # fastball loses ride
    assert -10.0 < t.InducedVertBreak[1] < 0  # curveball drops less (toward 0)
    assert np.allclose(t.HorzBreak, t.hb_arm * np.array([1, -1]))
    assert (t.rho == 0.82).all()
    assert t.ivb_diff_fb[0] == pytest.approx(0.0)  # a primary fastball stays its own reference
    back = altitude.physics_translator(_shape_model())(t, 1.0, t["rho"].to_numpy())
    assert np.allclose(back.InducedVertBreak, df.InducedVertBreak)


def test_cluster_bootstrap_ci_contains_mean():
    v = pd.Series(np.r_[np.full(50, 1.0), np.full(50, 3.0)])
    c = pd.Series(np.repeat(np.arange(20), 5))
    m, lo, hi = altitude.cluster_bootstrap_mean(v, c, n_boot=300)
    assert lo <= m <= hi and m == pytest.approx(2.0)


def test_within_pitcher_observed():
    rows = []
    for k in range(40):
        for alt, shift in (("No Altitude", 0.0), ("Extreme Altitude", -2.0)):
            rows.append(pd.DataFrame({"pitch_key": f"k{k}", "pitcher_anon_id": f"p{k // 2}", "pitch_family": "Four-Seam",
                                      "altitude_category": alt, "x": 10 + k + shift + np.zeros(35)}))
    t = altitude.within_pitcher_observed(pd.concat(rows, ignore_index=True), ["x"], n_boot=100)
    assert t.loc[0, "extreme_minus_no"] == pytest.approx(-2.0) and t.loc[0, "pitches_compared"] == 40


def test_counterfactual_is_zero_when_air_is_the_same(result):
    _, d, res = result
    s = altitude.counterfactual_scores(d.head(300), res["model"], res["scaler"], rho_a=1.0, rho_b=1.0)
    assert np.allclose(s.delta_stuff, 0) and np.allclose(s.delta_p_whiff, 0)


def test_delta_tables_and_triangulation(result):
    _, d, res = result
    t = res["by_shape"]
    assert {"shape", "delta_stuff", "delta_lo", "delta_hi", "verdict", "physics", "relative_to_league"} <= set(t.columns)
    assert (t.delta_lo <= t.delta_stuff + 1e-9).all() and (t.delta_stuff <= t.delta_hi + 1e-9).all()
    assert set(t.verdict) <= {"gana relativo", "pierde relativo", "neutral"}
    assert t.physics.str.startswith("En aire de CDMX").all()
    assert {"pitch_family", "counterfactual_delta", "observed_model_delta"} <= set(res["triangulation"].columns)
    tri = res["triangulation"]
    assert {"counterfactual_delta_lo", "counterfactual_delta_hi", "observed_minus_counterfactual"} <= set(tri.columns)
    assert {"delta_hard_contact_pct", "delta_hr_per_fb_pct"} <= set(t.columns) and t.delta_hr_per_fb_pct.notna().all()
    assert set(res["curves"].rho.round(3)) >= {1.0, 0.819}


def test_model_uses_invariant_family():
    assert "AutoPitchType" not in altitude.STUFF_FEATURES_INVARIANT
    assert "pitch_family" in altitude.STUFF_FEATURES_INVARIANT
