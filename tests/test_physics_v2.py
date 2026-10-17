"""HACK-041: aerodynamic coefficients, lift-gap split, Magnus elasticity and the RK4 flight engine (synthetic)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stuffplus.physics import coefficients as co
from stuffplus.physics.flight import Release, fly


def test_flight_reproduces_the_requested_sea_level_breaks_and_target():
    rel = Release(velo_mph=94, ivb_in=17, hb_in=8, target_z_ft=2.6, target_x_ft=0.2)
    f = fly(rel, 1.0)
    assert f.ivb_in == pytest.approx(17, abs=0.2) and f.hb_in == pytest.approx(8, abs=0.2)
    assert f.plate_z == pytest.approx(2.6, abs=0.05) and f.plate_x == pytest.approx(0.2, abs=0.05)
    assert 0.36 < f.flight_time < 0.45 and len(f.t) == len(f.pos)


def test_thin_air_loses_break_and_arrives_faster():
    rel = Release()
    sea, thin = fly(rel, 1.0), fly(rel, 0.82)
    assert thin.ivb_in == pytest.approx(rel.ivb_in * 0.82, rel=0.03)  # Magnus ∝ ρ (elasticity 1)
    assert thin.plate_mph > sea.plate_mph + 1.0  # less drag: the ball arrives faster
    assert thin.plate_z < sea.plate_z  # less ride: crosses lower with the same release
    steeper = fly(rel, 0.82, elasticity=1.5)
    assert steeper.ivb_in < thin.ivb_in


def test_breaking_ball_signs_are_kept():
    f = fly(Release(velo_mph=80, ivb_in=-12, hb_in=-6, target_z_ft=2.0), 1.0)
    assert f.ivb_in == pytest.approx(-12, abs=0.3) and f.hb_in == pytest.approx(-6, abs=0.3)


def _pitches(n=400, seed=0, rho_slope=1.0):
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(40):
        for g in range(n // 40):
            rho = rng.choice([1.0, 0.89, 0.84])
            rows.append(dict(pitch_key=f"k{k}", game_anon_id=f"g{k}_{g}", pitcher_anon_id=f"p{k % 10}",
                             pitch_family="Four-Seam" if k % 2 else "Slider", rho=rho,
                             magnus_acc=(18 + k * 0.1) * rho ** rho_slope * np.exp(rng.normal(0, 0.01))))
    return pd.DataFrame(rows)


def test_magnus_elasticity_recovers_the_planted_slope():
    for slope in (1.0, 1.5):
        el = co.magnus_elasticity(_pitches(rho_slope=slope), n_boot=50).set_index("pitch_family")
        assert el.loc["Four-Seam", "elasticity"] == pytest.approx(slope, abs=0.05)
        assert el.loc["Four-Seam", "lo"] <= el.loc["Four-Seam", "elasticity"] <= el.loc["Four-Seam", "hi"]


def test_gap_decomposition_multiplies_back_to_the_observed_ratio():
    t = pd.DataFrame([dict(pitch_family="Four-Seam", bucket="No Altitude", cl=0.20, S=0.22),
                      dict(pitch_family="Four-Seam", bucket="Extreme Altitude", cl=0.18, S=0.21)])
    g = co.gap_decomposition(t, cl_slope_s=0.5, rho_true_over_hat=0.96).iloc[0]
    total = (1 + g.explained_by_spin_param_pct / 100) * (1 + g.explained_by_density_bias_pct / 100) * (1 + g.residual_pct / 100)
    assert total == pytest.approx(g.cl_ratio)
    assert g.gap_pct == pytest.approx(-10.0)


def test_coefficients_mark_impossible_values_missing():
    d = pd.DataFrame({"vx0": [-5.0, -5.0], "vy0": [-135.0, -135.0], "vz0": [-4.0, -4.0], "ax0": [-12.0, 900.0],
                      "ay0": [28.0, 28.0], "az0": [-15.0, -15.0], "SpinRate": [2300.0, 2300.0], "rho": [1.0, 1.0]})
    c = co.coefficients(d)
    assert np.isfinite(c.loc[0, ["cd", "S", "Re"]]).all()
    assert c.loc[0, "Re"] > 1e5 and c.loc[1, "cl"] != c.loc[1, "cl"]  # absurd acceleration -> NaN


def _aero(n=6000, seed=3, a=0.10, b=0.55, cd_slope=-0.02):
    rng = np.random.default_rng(seed)
    S = rng.uniform(0.04, 0.35, n)
    Re = rng.uniform(1.4e5, 2.0e5, n)
    return pd.DataFrame(dict(pitch_family="Four-Seam", altitude_category="No Altitude",
                             pitcher_anon_id=[f"p{i % 120}" for i in range(n)], S=S, Re=Re,
                             cl=co.shs_cl(S, a, b) + rng.normal(0, 0.01, n),
                             cd=0.33 + cd_slope * Re / 1e5 + rng.normal(0, 0.005, n)))


def test_shs_fit_recovers_the_line_above_s_01_and_keeps_15s_below():
    fit = co.cl_vs_s(_aero(), n_boot=40)
    assert fit["a"] == pytest.approx(0.10, abs=0.01) and fit["b"] == pytest.approx(0.55, abs=0.03)
    assert fit["b_lo"] <= fit["b"] <= fit["b_hi"] and fit["n_below"] > 0
    assert co.shs_cl([0.05], 0.1, 0.55)[0] == pytest.approx(0.075)


def test_cd_vs_re_finds_the_planted_drag_crisis_slope_with_a_ci():
    t = co.cd_vs_re(_aero(), n_boot=40).iloc[0]
    assert t.slope_per_1e5 == pytest.approx(-0.02, abs=0.003)
    assert t.slope_lo <= t.slope_per_1e5 <= t.slope_hi < 0


def test_efficient_pitches_select_on_one_half_and_hold_out_the_other():
    rows = []
    for k in range(6):
        for g in range(8):
            for _ in range(10):
                rows.append(dict(pitch_key=f"k{k}", game_anon_id=f"k{k}g{g}", altitude_category="No Altitude",
                                 spin_eff=0.98 if k < 3 else 0.80))
    d = pd.DataFrame(rows)
    keep, held = co.efficient_pitches(d, min_pitches=20)
    assert keep == {"k0", "k1", "k2"}
    sel_rows = d[d.pitch_key.isin(keep)]
    assert 0 < held.sum() < len(sel_rows)  # only the non-selection games are held out
    assert not held[~d.pitch_key.isin(keep)].any()
