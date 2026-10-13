import numpy as np
import pandas as pd
import pytest

from stuffplus import hypotheses as H


def _planted(delta=-3.0, slope_per_rho=30.0, n_pitchers=40, seed=0, per_cell=40):
    """Lanzamientos de 2 familias en 3 parques (ρ̂ 1.0 / 0.89 / 0.84) con efecto plantado: y = base_k + slope·(ρ̂−1)."""
    rng = np.random.default_rng(seed)
    rows = []
    parks = {"No Altitude": 1.0, "Medium Altitude": 0.89, "Extreme Altitude": 0.84}
    for p in range(n_pitchers):
        for fam, sh in (("Four-Seam", "R"), ("Curveball", "L")):
            base = rng.normal(16 if fam == "Four-Seam" else -10, 2.0)
            for env, rho in parks.items():
                y = base + slope_per_rho * (rho - 1.0) + rng.normal(0, 0.6, per_cell)
                for v in y:
                    rows.append((p, f"{p}_2024_{fam}", fam, env, rho, v, 2024, "Left" if sh == "L" else "Right"))
    return pd.DataFrame(rows, columns=["pitcher_anon_id", "pitch_key", "pitch_family", "altitude_category",
                                       "park_rho", "m", "year", "PitcherThrows"])


def test_within_pitcher_delta_recovers_planted_effect():
    df = _planted()  # Extreme − No = 30·(0.84−1) = −4.8
    est = H.within_pitcher_delta(df, "m", "Four-Seam", H.NO_ALT, H.EXT_ALT, min_n=20, n_boot=200)
    assert est.lo < -4.8 < est.hi and est.hi < 0
    assert est.n_pitchers == 40 and est.n_keys == 40


def test_min_n_drops_thin_keys():
    df = _planted(per_cell=10)
    est = H.within_pitcher_delta(df, "m", "Four-Seam", H.NO_ALT, H.EXT_ALT, min_n=20, n_boot=50)
    assert est.n_keys == 0 and np.isnan(est.delta)


def test_dose_response_recovers_slope_and_agrees_with_delta_sign():
    df = _planted()
    s = H.dose_response(df, "m", "park_rho", "Four-Seam", min_n=20, n_boot=200)
    assert s.lo < 30.0 * H.SLOPE_SCALE < s.hi  # +3.0 por cada +0.1 de ρ̂
    d = H.within_pitcher_delta(df, "m", "Four-Seam", H.NO_ALT, H.EXT_ALT, n_boot=200)
    assert H.verdict(d, -1, s) == "Supported"


def test_verdict_rules():
    e = lambda lo, hi: H.Estimate((lo + hi) / 2, lo, hi, 10, 10)
    assert H.verdict(e(-2, -1), -1, e(1, 2)) == "Supported"
    assert H.verdict(e(-2, -1), -1, e(-1, 1)) == "Partially"
    assert H.verdict(e(-1, 1), -1, e(-1, 1)) == "Rejected"
    assert H.verdict(e(-2, -1), +1) == "Rejected (opposite)"  # significativo pero en dirección contraria
    assert H.verdict(e(-1, 1), +1, e(-1, 1)) == "Rejected"
    assert H.overall_verdict(["Supported", "Rejected"]) == "Partially"
    assert H.overall_verdict(["Rejected"]) == "Rejected"


def test_movement_metrics_arm_side_and_magnitude_loss():
    df = pd.DataFrame({"PitcherThrows": ["Right", "Left"], "InducedVertBreak": [16.0, -10.0],
                       "HorzBreak": [8.0, -8.0]})
    out = H.add_movement_metrics(df)
    assert out["hb_arm"].tolist() == [8.0, 8.0]  # zurdo y derecho del mismo lado del brazo
    assert out["total_break"].iloc[0] == pytest.approx(np.hypot(16, 8))
    # una curva que cae menos (IVB −10 → −8) pierde magnitud aunque su ΔIVB sea positivo
    assert abs(-8.0) < out["abs_ivb"].iloc[1]


def test_paired_did_detects_offspeed_specific_effect():
    rng = np.random.default_rng(1)
    rows = []
    for p in range(40):
        for fam in ("Changeup", "Slider"):
            for env in (H.NO_ALT, H.EXT_ALT):
                eff = -0.10 if (fam == "Changeup" and env == H.EXT_ALT) else 0.0
                for v in rng.binomial(1, 0.3 + eff, 60):
                    rows.append((p, 2024, fam, env, float(v)))
    df = pd.DataFrame(rows, columns=["pitcher_anon_id", "year", "pitch_family", "altitude_category", "whiff"])
    est = H.paired_did(df, "whiff", ("Changeup",), ("Slider",), H.NO_ALT, H.EXT_ALT, min_n=30, n_boot=200)
    assert est.lo < -0.10 < est.hi and est.hi < 0


def test_moderated_delta_recovers_slope():
    rng = np.random.default_rng(2)
    rows = []
    for p in range(120):
        gb = rng.uniform(0.3, 0.6)
        for env in (H.NO_ALT, H.EXT_ALT):
            shift = (0.10 - 0.5 * gb) if env == H.EXT_ALT else 0.0  # más rodados → menos daño
            for v in rng.normal(shift, 0.3, 80):
                rows.append((p, 2024, env, gb, v))
    df = pd.DataFrame(rows, columns=["pitcher_anon_id", "year", "altitude_category", "gb_sea", "rv"])
    est = H.moderated_delta(df, "rv", "gb_sea", H.NO_ALT, H.EXT_ALT, min_n=30, n_boot=200, per=0.1)
    assert est.lo < -0.05 < est.hi


def test_batted_ball_metrics_denominators():
    df = pd.DataFrame({"hit_type": ["FlyBall", "FlyBall", "GroundBall", "Bunt", None],
                       "home_run": [1.0, 0.0, 0.0, 0.0, 0.0], "Distance": [400.0, 250.0, 60.0, 10.0, np.nan],
                       "PitchCall": ["InPlay"] * 4 + ["BallCalled"]})
    out = H.add_batted_ball_metrics(df)
    assert out["hr_fb"].iloc[:2].tolist() == [1.0, 0.0] and out["hr_fb"].iloc[2:].isna().all()
    assert out["hr_fb"].notna().sum() == 2 and out["fb_distance"].notna().sum() == 2
    assert out["gb_flag"].notna().sum() == 3 and out["gb_flag"].sum() == 1  # el bunt y el no-InPlay quedan fuera


def test_smoke_on_synthetic_fixture(synthetic_pitches):
    from stuffplus.features.identity import assign_pitch_id
    from stuffplus.schema import clean

    d = H.add_movement_metrics(assign_pitch_id(clean(synthetic_pitches)))
    est = H.within_pitcher_delta(d[d.pitch_id >= 0], "total_break", None, H.NO_ALT, H.EXT_ALT, min_n=5, n_boot=50)
    assert est.n_pitchers >= 0  # corre de punta a punta sin lanzar
