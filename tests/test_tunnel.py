"""HACK-061: tunneling por tiempo (150 ms antes del plato) con geometría conocida y datos sintéticos."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import schema
from stuffplus.features.tunnel import (
    DECISION_S, DEC_SEP_FLOOR_IN, PLATE_FRONT_FT, TUNNEL_FEATURES, add_tunnel_features, flight_points, plate_time,
)

ROOT = Path(__file__).resolve().parent.parent


def _run_module():
    spec = importlib.util.spec_from_file_location("tunnel_run", ROOT / "analysis" / "tunnel" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pitch(**kw) -> dict:
    base = dict(x0=1.0, y0=50.0, z0=6.0, vx0=-4.0, vy0=-125.0, vz0=-3.0, ax0=8.0, ay0=24.0, az0=-18.0)
    base.update(kw)
    return base


def _frame(rows: list[dict]) -> pd.DataFrame:
    base = dict(pitcher_anon_id="p1", year=2025, game_anon_id="g1", PitcherThrows="Right")
    return pd.DataFrame([{**base, **r} for r in rows])


# --- geometría exacta ---------------------------------------------------------------------------------------------

def test_plate_time_solves_the_quadratic():
    t = plate_time(50.0, -120.0, 24.0)
    roots = np.roots([0.5 * 24.0, -120.0, 50.0 - PLATE_FRONT_FT])
    assert t == pytest.approx(min(r.real for r in roots if r.real > 0), rel=1e-12)
    assert 50.0 - 120.0 * t + 12.0 * t * t == pytest.approx(PLATE_FRONT_FT, abs=1e-9)


def test_plate_time_without_acceleration():
    assert plate_time(50.0, -100.0, 0.0) == pytest.approx((50.0 - PLATE_FRONT_FT) / 100.0, rel=1e-12)
    assert np.isnan(plate_time(50.0, 100.0, 0.0))  # se aleja del plato: sin solución


def test_decision_point_is_150ms_before_the_plate():
    p = pd.DataFrame([_pitch()])
    pts = flight_points(p).iloc[0]
    tp = pts.t_plate
    td = tp - DECISION_S
    assert 50.0 - 125.0 * tp + 12.0 * tp**2 == pytest.approx(PLATE_FRONT_FT, abs=1e-9)
    assert pts.y_dec == pytest.approx(50.0 - 125.0 * td + 12.0 * td**2, abs=1e-12)
    assert pts.x_dec == pytest.approx(1.0 - 4.0 * td + 4.0 * td**2, abs=1e-12)
    assert pts.z_dec == pytest.approx(6.0 - 3.0 * td - 9.0 * td**2, abs=1e-12)
    assert pts.x_plate == pytest.approx(1.0 - 4.0 * tp + 4.0 * tp**2, abs=1e-12)
    assert pts.z_plate == pytest.approx(6.0 - 3.0 * tp - 9.0 * tp**2, abs=1e-12)


def test_faster_ball_in_thin_air_moves_the_decision_point_back():
    sea = flight_points(pd.DataFrame([_pitch(vy0=-125.0, ay0=24.0)])).iloc[0]
    thin = flight_points(pd.DataFrame([_pitch(vy0=-130.0, ay0=19.0)])).iloc[0]
    assert thin.t_plate < sea.t_plate  # llega antes
    assert thin.y_dec > sea.y_dec  # 150 ms antes queda más lejos del plato


# --- separaciones contra la recta principal -----------------------------------------------------------------------

def _arsenal(d_ax=6.0, d_az=-4.0, hand="Right", sign=1.0):
    fb = [_pitch(x0=1.0 * sign, vx0=-4.0 * sign, ax0=8.0 * sign) for _ in range(4)]
    off = [_pitch(x0=1.0 * sign, vx0=-4.0 * sign, ax0=(8.0 + d_ax) * sign, az0=-18.0 + d_az) for _ in range(4)]
    df = _frame([{**r, "pitch_id": 0, "primary_fb_id": 0, "pitch_family": "Four-Seam"} for r in fb]
                + [{**r, "pitch_id": 1, "primary_fb_id": 0, "pitch_family": "Changeup"} for r in off])
    df["PitcherThrows"] = hand
    return df


def test_separation_in_inches_matches_hand_computation():
    out = add_tunnel_features(_arsenal())
    fb, off = out.iloc[:4], out.iloc[4:]
    assert (fb[TUNNEL_FEATURES] == 0.0).all().all()  # la recta principal contra sí misma
    tp = flight_points(pd.DataFrame([_pitch()])).iloc[0].t_plate
    td = tp - DECISION_S
    dec_dx, dec_dz = 0.5 * 6.0 * td**2 * 12, 0.5 * -4.0 * td**2 * 12
    plate_dx, plate_dz = 0.5 * 6.0 * tp**2 * 12, 0.5 * -4.0 * tp**2 * 12
    r = off.iloc[0]
    assert r.tunnel_dec_dx_in == pytest.approx(dec_dx, abs=1e-9)
    assert r.tunnel_dec_dz_in == pytest.approx(dec_dz, abs=1e-9)
    assert r.tunnel_dec_sep_in == pytest.approx(np.hypot(dec_dx, dec_dz), abs=1e-9)
    assert r.tunnel_plate_sep_in == pytest.approx(np.hypot(plate_dx, plate_dz), abs=1e-9)
    assert r.tunnel_ratio_t == pytest.approx(np.hypot(plate_dx, plate_dz) / np.hypot(dec_dx, dec_dz), abs=1e-9)
    assert r.tunnel_ratio_t > 1.0  # se separa tarde: más separación en el plato que en la decisión


def test_denominator_is_clipped_and_ratio_capped():
    out = add_tunnel_features(_arsenal(d_ax=1e-3, d_az=0.0))
    r = out.iloc[4]
    assert r.tunnel_dec_sep_in < DEC_SEP_FLOOR_IN
    assert r.tunnel_ratio_t == pytest.approx(r.tunnel_plate_sep_in / DEC_SEP_FLOOR_IN)


def test_left_hander_is_mirrored_to_the_same_features():
    right = add_tunnel_features(_arsenal())
    left = add_tunnel_features(_arsenal(hand="Left", sign=-1.0))
    pd.testing.assert_frame_equal(right[TUNNEL_FEATURES], left[TUNNEL_FEATURES], atol=1e-9)


def test_without_pitch_id_columns_falls_back_to_pitch_family():
    full = add_tunnel_features(_arsenal())
    bare = add_tunnel_features(_arsenal().drop(columns=["pitch_id", "primary_fb_id"]))
    pd.testing.assert_frame_equal(full[TUNNEL_FEATURES], bare[TUNNEL_FEATURES], atol=1e-9)


def test_unknown_pitch_and_missing_parameters_are_nan():
    df = _arsenal()
    df.loc[5, "pitch_id"] = -1
    df.loc[6, "vy0"] = np.nan
    out = add_tunnel_features(df)
    assert out.loc[5, TUNNEL_FEATURES].isna().all()
    assert out.loc[6, TUNNEL_FEATURES].isna().all()
    assert out.loc[4, TUNNEL_FEATURES].notna().all()


def test_small_game_uses_the_season_mean_of_the_pitch_type():
    df = _arsenal()
    g2 = _frame([{**_pitch(ax0=8.0 + 6.0), "pitch_id": 1, "primary_fb_id": 0, "pitch_family": "Changeup", "game_anon_id": "g2"}])
    out = add_tunnel_features(pd.concat([df, g2], ignore_index=True))
    # g2 solo tiene 1 lanzamiento: usa la media de temporada del pitch (g1 y g2) y la recta de la temporada
    assert out.loc[8, TUNNEL_FEATURES].notna().all()
    assert out.loc[8, "tunnel_dec_dx_in"] == pytest.approx(out.loc[4, "tunnel_dec_dx_in"], abs=1e-9)


def test_pitch_type_mean_removes_aim_noise():
    """Dos lanzamientos del mismo tipo con distinta ubicación comparten el mismo valor: no es ubicación."""
    df = _arsenal()
    df.loc[4, "z0"] += 0.5
    df.loc[5, "z0"] -= 0.5
    out = add_tunnel_features(df)
    assert out.loc[4, "tunnel_dec_dz_in"] == pytest.approx(out.loc[5, "tunnel_dec_dz_in"], abs=1e-9)


def test_feature_names_pass_the_stuff_leak_check():
    schema.assert_no_target_leak(TUNNEL_FEATURES, allow_location=False)


# --- datos sintéticos de punta a punta ----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def prepared(_synthetic_cache):
    return _run_module().prepare(schema.clean(_synthetic_cache.copy()))


def test_prepare_adds_features_and_references_are_zero(prepared):
    d = prepared
    assert set(TUNNEL_FEATURES) <= set(d.columns)
    ref = d["tunnel_is_ref"].to_numpy()
    assert ref.any()
    assert (d.loc[ref & d["tunnel_dec_sep_in"].notna(), TUNNEL_FEATURES] == 0.0).all().all()
    assert d.loc[~ref, "tunnel_plate_sep_in"].notna().mean() > 0.5
    assert d["tunnel_t_plate_s"].between(0.25, 0.6).all()


def test_synthetic_thin_air_is_faster_and_not_location(prepared):
    d = prepared
    nonref = d[~d["tunnel_is_ref"] & d["tunnel_dec_sep_in"].notna()]
    by_alt = nonref.groupby(nonref["altitude_category"].astype(str))["tunnel_t_plate_s"].mean()
    assert by_alt["Extreme Altitude"] < by_alt["No Altitude"]
    sgn = np.where(nonref["PitcherThrows"].astype(str).str.startswith("L"), -1.0, 1.0)
    assert abs(nonref["tunnel_plate_dz_in"].corr(nonref["PlateLocHeight"])) < 0.6
    assert abs(nonref["tunnel_plate_dx_in"].corr(nonref["PlateLocSide"] * sgn)) < 0.6


def test_adoption_verdict_applies_the_fixed_rule():
    run = _run_module()
    metrics = pd.DataFrame({"model": ["baseline", "base", "tunnel"], "skill_vs_baseline": [0.0, 0.010, 0.012],
                            "skill_lo": [0.0, 0.008, 0.011]})
    pred = pd.DataFrame({"first_n": [50, 100, 200], "r_base": [0.20, 0.25, 0.30], "r_tunnel": [0.21, 0.246, 0.30]})
    rel = pd.DataFrame({"r_base": [0.80], "r_tunnel": [0.80]})
    assert bool(run.adoption_verdict(metrics, pred, rel)["adoptar"].iloc[0])
    # IC inferior por debajo de la habilidad del base: no se adopta aunque la media sea mayor
    m2 = metrics.assign(skill_lo=[0.0, 0.008, 0.009])
    v2 = run.adoption_verdict(m2, pred, rel)
    assert not v2["adoptar"].iloc[0] and not v2["cumple"].iloc[0]
    # r de 200 baja más de 0.005
    p3 = pred.assign(r_tunnel=[0.21, 0.246, 0.294])
    assert not run.adoption_verdict(metrics, p3, rel)["adoptar"].iloc[0]
    # split-half baja más de 0.005
    assert not run.adoption_verdict(metrics, pred, rel.assign(r_tunnel=[0.79]))["adoptar"].iloc[0]


def test_run_end_to_end_writes_aggregate_reports(prepared, tmp_path):
    run = _run_module()
    res = run.run(prepared, fast=True, out_dir=tmp_path)
    assert {"baseline", "base", "tunnel"} == set(res["metrics"]["model"])
    for name in ("metrics", "predictiveness", "reliability", "altitude_check", "location_audit", "verdict"):
        assert (tmp_path / f"{name}.csv").exists()
    assert not res["altitude_check"].empty
    text = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Regla de adopción" in text and chr(0x2014) not in text
    assert all((tmp_path / f.name).stat().st_size < 2_000_000 for f in tmp_path.iterdir())
