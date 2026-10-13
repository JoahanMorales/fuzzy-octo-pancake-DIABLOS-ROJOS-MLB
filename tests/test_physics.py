import numpy as np
import pandas as pd
import pytest

from stuffplus.physics import aero, constants as C


def _traj(speed_mph, cd, cl, rho_si=C.RHO_SI_SEA_LEVEL, spin_rpm=2300.0):
    """Trayectoria con Cd/Cl conocidos: v hacia −y, Magnus hacia +z (backspin)."""
    v = speed_mph * C.MPH_TO_FPS
    k = 0.5 * rho_si * C.BALL_AREA_M2 / C.BALL_MASS_KG * C.FT_TO_M
    return dict(vx0=0.0, vy0=-v, vz0=0.0, ax0=0.0, ay0=cd * k * v**2, az0=-C.G_FT_S2 + cl * k * v**2, SpinRate=spin_rpm)


def test_decompose_recovers_known_cd_cl():
    df = pd.DataFrame([_traj(95, 0.35, 0.20), _traj(85, 0.30, 0.10)])
    out = aero.decompose(df)
    assert out["cd"].to_numpy() == pytest.approx([0.35, 0.30], rel=1e-9)
    assert out["cl"].to_numpy() == pytest.approx([0.20, 0.10], rel=1e-9)
    assert (out["drag_acc"] > 0).all()


def test_spin_efficiency_nathan_roundtrip():
    s = 0.17
    cl = 1 / (2.32 + 0.4 / s)
    row = _traj(95, 0.35, cl)
    v = 95 * C.MPH_TO_FPS * C.FT_TO_M
    w_t = s * v / C.BALL_RADIUS_M / C.RPM_TO_RADS
    row["SpinRate"] = w_t / 0.9
    out = aero.decompose(pd.DataFrame([row]))
    assert out["spin_eff"].iloc[0] == pytest.approx(0.9, rel=1e-6)
    assert out["active_spin_rpm"].iloc[0] == pytest.approx(w_t, rel=1e-6)


def test_cd_proxy_scales_with_density_and_cl_over_cd_does_not():
    lo, hi = 0.8, 1.0
    rows = [_traj(93, 0.35, 0.2, rho_si=C.RHO_SI_SEA_LEVEL * r) for r in (lo, hi)]
    out = aero.decompose(pd.DataFrame(rows))
    assert out["cd_proxy"].iloc[0] / out["cd_proxy"].iloc[1] == pytest.approx(lo)
    ratio = out["cl_proxy"] / out["cd_proxy"]
    assert ratio.iloc[0] == pytest.approx(ratio.iloc[1])


def test_game_density_index_and_shrinkage():
    rng = np.random.default_rng(0)
    rows, games = [], []
    for g, r, n in [("sea", 1.0, 60), ("alt", 0.84, 60), ("tiny", 0.5, 3)]:
        for _ in range(n):
            rows.append(_traj(94, 0.35 * r * (1 + rng.normal(0, 0.01)), 0.2 * r))
            games.append(g)
    df = pd.DataFrame(rows)
    df["GameID"], df["is_fastball"] = games, True
    idx = aero.game_density_index(df)
    assert idx["alt"] == pytest.approx(0.84, abs=0.01)
    assert idx["tiny"] > 0.6  # encogido hacia la media global, no 0.5


def test_constants():
    assert C.RHO_SEA_LEVEL == 1.0
    assert 0.70 < C.RHO_HARP_HELU < 0.85
    assert C.RHO_HARP_HELU < C.RHO_COORS < 1.0


def test_movement_model_recovers_rho_effect():
    from stuffplus.physics.translate import MovementModel

    rng = np.random.default_rng(1)
    n = 3000
    key = rng.integers(0, 60, n)
    rho = rng.choice([0.84, 1.0], n)
    base = rng.normal(0, 3, 60)[key]
    df = pd.DataFrame(dict(
        pitch_key=key, RelSpeed=rng.normal(93, 2, n), SpinRate=rng.normal(2300, 100, n), SpinAxis=rng.normal(200, 10, n),
        RelHeight=5.8 + rng.normal(0, .05, n), RelSide=-1.5 + rng.normal(0, .05, n), Extension=6.2 + rng.normal(0, .05, n)))
    df["InducedVertBreak"] = 15 + base + 0.01 * (df.SpinRate - 2300) + 23.0 * (rho - 1) + rng.normal(0, 1, n)
    df["HorzBreak"] = 9 + base + 10.0 * (rho - 1) + rng.normal(0, 1, n)
    df["SpeedDrop"] = 7.5 + 8.0 * (rho - 1) + rng.normal(0, .3, n)
    df["ZoneSpeed"] = 84 - 8.0 * (rho - 1) + rng.normal(0, .3, n)
    m = MovementModel().fit(df, pd.Series(rho))
    assert m.rho_effect["ivb"] == pytest.approx(23.0, abs=1.5)
    assert m.rho_effect["speed_drop"] == pytest.approx(8.0, abs=0.3)
    t = m.translate_pitch(df.head(5), 1.0, 0.84)
    assert (t["ivb"] < df["InducedVertBreak"].head(5)).all()
    assert m.expected_movement(df.head(5), 0.9).shape == (5, 4)
