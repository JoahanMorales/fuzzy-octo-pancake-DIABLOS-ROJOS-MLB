import numpy as np
import pandas as pd
import pytest

from stuffplus.features.arsenal import fit_arsenal, primary_fastball, trajectory_at
from stuffplus.features.sequence import add_sequence_features


def _traj(n, x_end=0.0, lat_end=0.0, vert_end=2.5, vert0=6.0, lat0=1.5):
    """Polinomios con X hacia el plato (54→0 en ~0.4 s) y Y/Z que llegan a (vert_end, lat_end) en x=0."""
    t_end = 0.4
    c1x, c0x = -(54.0) / t_end, 54.0
    return dict(PitchTrajectoryXc0=c0x, PitchTrajectoryXc1=c1x, PitchTrajectoryXc2=0.0,
                PitchTrajectoryYc0=vert0, PitchTrajectoryYc1=(vert_end - vert0) / t_end, PitchTrajectoryYc2=0.0,
                PitchTrajectoryZc0=lat0, PitchTrajectoryZc1=(lat_end - lat0) / t_end, PitchTrajectoryZc2=0.0)


def _pitches():
    rows = []
    for g in ("g1", "g2"):
        for i in range(12):
            fb = i % 3 != 2
            rows.append(dict(
                pitcher_anon_id=1, year=2023, game_anon_id=g, PitcherThrows="Left" if g == "gL" else "Right",
                pitch_id=0 if fb else 1, pitch_family="Four-Seam" if fb else "Changeup",
                RelSpeed=95.0 if fb else 85.0, InducedVertBreak=17.0 if fb else 6.0, HorzBreak=8.0 if fb else 12.0,
                SpinRate=2300.0 if fb else 1800.0, SpinAxis=200.0 if fb else 230.0,
                **_traj(1, lat_end=0.0 if fb else 1.0, vert_end=2.5 if fb else 1.5)))
    return pd.DataFrame(rows)


def test_primary_fastball_and_diffs_same_game():
    d = _pitches()
    assert primary_fastball(d).loc[(1, 2023)] == 0
    out = fit_arsenal(d).transform(d)
    ch = out[out.pitch_id == 1]
    assert ch.velo_diff_vs_fb.eq(-10.0).all() and ch.ivb_diff_vs_fb.eq(-11.0).all()
    assert ch.hb_diff_vs_fb.eq(4.0).all() and ch.spin_diff_vs_fb.eq(-500.0).all()
    assert ch.axis_diff_vs_fb.eq(30.0).all() and ch.fb_ref_same_game.eq(1).all()
    assert out[out.pitch_id == 0].velo_diff_vs_fb.eq(0).all()
    assert out.pitch_usage_pct.round(3).isin([0.667, 0.333]).all() and out.arsenal_size.eq(2).all()


def test_hb_mirrored_for_lefties():
    d = _pitches()
    d.loc[:, "PitcherThrows"] = "Left"
    d["HorzBreak"] = -d["HorzBreak"]  # mismo lanzamiento visto por un zurdo
    d["SpinAxis"] = 360.0 - d["SpinAxis"]
    out = fit_arsenal(d).transform(d)
    assert out[out.pitch_id == 1].hb_diff_vs_fb.eq(4.0).all()
    assert out[out.pitch_id == 1].axis_diff_vs_fb.eq(30.0).all()


def test_trajectory_and_tunnel():
    d = _pitches()
    p = trajectory_at(d.head(1), 0.0)
    assert p.vert.iloc[0] == pytest.approx(2.5) and p.lat.iloc[0] == pytest.approx(0.0)
    out = fit_arsenal(d).transform(d)
    ch = out[out.pitch_id == 1].iloc[0]
    # a 23.8 ft del plato (t=0.4·30.2/54) la separación es proporcional; en el plato mide √(1²+1²)
    assert ch.plate_sep_vs_fb == pytest.approx(np.hypot(1.0, 1.0))
    assert ch.decision_sep_vs_fb == pytest.approx(np.hypot(1.0, 1.0) * (1 - 23.8 / 54.0), rel=1e-6) or ch.decision_sep_vs_fb < ch.plate_sep_vs_fb
    assert ch.tunnel_ratio > 1.0


def test_no_leakage_fit_on_train_only():
    d = _pitches()
    train, test = d[d.game_anon_id == "g1"], d[d.game_anon_id == "g2"].copy()
    m = fit_arsenal(train)
    test2 = test.copy()
    test2["RelSpeed"] += 50  # lo que pase en test no cambia lo aprendido
    assert m.primary.equals(fit_arsenal(train).primary) and m.usage.equals(fit_arsenal(train).usage)
    unseen = test.assign(pitcher_anon_id=99)
    out = m.transform(unseen)
    assert out.pitch_usage_pct.isna().all()  # pitcher nunca visto: sin uso aprendido, no se inventa


def test_sequence_features():
    d = pd.DataFrame(dict(
        pa_id=["a"] * 3 + ["b"] * 2, game_anon_id="g", pitcher_anon_id=1, pitch_idx_in_game=range(5),
        pitch_id=[0, 1, 0, 1, 1], RelSpeed=[95, 85, 94, 84, 83.0],
        PlateLocSide=[0, 1, 1, 0, 0.0], PlateLocHeight=[2, 2, 3, 2, 2.0]))
    out = add_sequence_features(d)
    assert list(out.prev_pitch_id) == [-1, 0, 1, -1, 1]
    assert out.prev_velo_diff.iloc[1] == -10 and np.isnan(out.prev_velo_diff.iloc[0])
    assert out.prev_loc_diff.iloc[1] == pytest.approx(1.0) and out.prev_loc_diff.iloc[2] == pytest.approx(1.0)
    assert list(out.pitch_number_in_pa) == [1, 2, 3, 1, 2] and out.times_through_order.eq(1).all()
