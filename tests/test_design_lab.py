import numpy as np
import pandas as pd
import pytest

from stuffplus import design_lab as D


def _frame():
    """Un pitcher-temporada con 2 rectas y 2 sliders (movimiento a nivel del mar)."""
    rows = []
    for fam, n, speed, ivb, hb, axis in (("Four-Seam", 2, 94.0, 17.0, 8.0, 210.0), ("Slider", 2, 85.0, 1.0, -4.0, 120.0)):
        for i in range(n):
            rows.append(dict(pitcher_anon_id="p1", year=2025, pitch_family=fam, RelSpeed=speed + i, InducedVertBreak=ivb + i * 0.5,
                             hb_arm=hb, SpinRate=2300.0, spin_axis_arm=axis, Extension=6.2, RelHeight=5.9, rel_side_arm=-1.7,
                             arm_angle=float(D.arm_angle_of(5.9, 1.7)), is_rhp=1, rho=1.0,
                             velo_diff_fb=0.0 if fam == "Four-Seam" else speed - 94.0, ivb_diff_fb=0.0 if fam == "Four-Seam" else ivb - 17.0,
                             hb_diff_fb=0.0 if fam == "Four-Seam" else hb - 8.0))
    return pd.DataFrame(rows)


def _fb(f):
    return f["pitch_family"].eq("Four-Seam")


def test_fastball_velocity_tweak_moves_secondary_diffs():
    f = _frame()
    out = D.add_velocity(f, _fb(f), 1.0)
    assert out.loc[_fb(f), "RelSpeed"].tolist() == (f.loc[_fb(f), "RelSpeed"] + 1).tolist()
    assert out.loc[~_fb(f), "RelSpeed"].tolist() == f.loc[~_fb(f), "RelSpeed"].tolist()  # el slider no cambia
    assert out.loc[~_fb(f), "velo_diff_fb"].tolist() == pytest.approx((f.loc[~_fb(f), "velo_diff_fb"] - 1).tolist())


def test_secondary_tweak_moves_only_its_own_diff():
    f = _frame()
    out = D.add_velocity(f, ~_fb(f), 1.0)
    assert out.loc[~_fb(f), "velo_diff_fb"].tolist() == pytest.approx((f.loc[~_fb(f), "velo_diff_fb"] + 1).tolist())
    assert out.loc[_fb(f), "velo_diff_fb"].tolist() == f.loc[_fb(f), "velo_diff_fb"].tolist()


def test_axis_rotation_keeps_magnitude_and_shifts_axis():
    f = _frame()
    out = D.rotate_movement(f, _fb(f), 5.0)
    m = _fb(f)
    before = np.hypot(f.loc[m, "InducedVertBreak"], f.loc[m, "hb_arm"])
    after = np.hypot(out.loc[m, "InducedVertBreak"], out.loc[m, "hb_arm"])
    assert after.to_numpy() == pytest.approx(before.to_numpy())
    assert out.loc[m, "spin_axis_arm"].tolist() == (f.loc[m, "spin_axis_arm"] + 5).tolist()
    assert not np.allclose(out.loc[m, "hb_arm"], f.loc[m, "hb_arm"])  # el vector sí giró
    back = D.rotate_movement(out, m, -5.0)
    assert back.loc[m, "InducedVertBreak"].to_numpy() == pytest.approx(f.loc[m, "InducedVertBreak"].to_numpy())


def test_spin_efficiency_scales_movement_not_spin_rate():
    f = _frame()
    out = D.scale_movement(f, _fb(f), 1.05)
    m = _fb(f)
    assert out.loc[m, "InducedVertBreak"].to_numpy() == pytest.approx(f.loc[m, "InducedVertBreak"].to_numpy() * 1.05)
    assert out.loc[m, "hb_arm"].to_numpy() == pytest.approx(f.loc[m, "hb_arm"].to_numpy() * 1.05)
    assert out.loc[m, "SpinRate"].tolist() == f.loc[m, "SpinRate"].tolist()


def test_lower_slot_geometry_is_consistent_with_arm_angle():
    f = _frame()
    slopes = {"Four-Seam": {"InducedVertBreak": 0.2, "hb_arm": -0.1}}
    out = D.lower_slot(f, _fb(f), -5.0, slopes)
    m = _fb(f)
    assert out.loc[m, "arm_angle"].to_numpy() == pytest.approx(f.loc[m, "arm_angle"].to_numpy() - 5.0)
    # la altura de salida recalculada reproduce el ángulo nuevo
    assert D.arm_angle_of(out.loc[m, "RelHeight"], out.loc[m, "rel_side_arm"]) == pytest.approx(out.loc[m, "arm_angle"].to_numpy())
    assert (out.loc[m, "RelHeight"] < f.loc[m, "RelHeight"]).all()
    assert out.loc[m, "InducedVertBreak"].to_numpy() == pytest.approx(f.loc[m, "InducedVertBreak"].to_numpy() - 1.0)  # 0.2 in/° × −5°
    assert out.loc[m, "hb_arm"].to_numpy() == pytest.approx(f.loc[m, "hb_arm"].to_numpy() + 0.5)


def test_tweak_gain_scores_only_affected_rows_with_fake_linear_scorer():
    f = _frame()

    def score(fr):  # Stuff+ lineal: velocidad pesa más en el aire de altura (la «diferencia» de CDMX)
        return {"hh": 100 + 1.5 * fr["RelSpeed"].to_numpy() - 0.2 * fr["velo_diff_fb"].to_numpy(),
                "sea": 100 + 1.0 * fr["RelSpeed"].to_numpy() - 0.2 * fr["velo_diff_fb"].to_numpy()}

    g = D.tweak_gain(f, _fb(f), D.TWEAKS[0], score)
    assert g.loc[_fb(f), "hh"].to_numpy() == pytest.approx(1.5)
    assert g.loc[_fb(f), "diff"].to_numpy() == pytest.approx(0.5)
    # los sliders solo cambian por su diferencia contra la recta (−1 mph de diferencia × −0.2 → +0.2)
    assert g.loc[~_fb(f), "hh"].to_numpy() == pytest.approx(0.2)
    arsenal = D.usage_weighted_gain(g, f)
    assert arsenal.loc[("p1", 2025), "hh"] == pytest.approx((1.5 * 2 + 0.2 * 2) / 4)


def test_hull_rejects_out_of_range_profiles():
    rng = np.random.default_rng(0)
    ref = pd.DataFrame({"RelSpeed": rng.normal(93, 1.5, 400), "InducedVertBreak": rng.normal(16, 2, 400)})
    inside = pd.DataFrame({"RelSpeed": [93.0], "InducedVertBreak": [16.0]})
    outside = pd.DataFrame({"RelSpeed": [105.0], "InducedVertBreak": [40.0]})
    assert D.admissible(inside, ref, cols=["RelSpeed", "InducedVertBreak"])[0]
    assert not D.admissible(outside, ref, cols=["RelSpeed", "InducedVertBreak"])[0]


def test_top3_sorted_admissible_and_above_noise():
    plan = pd.DataFrame({"pitcher_id": ["a"] * 5 + ["b"] * 2,
                         "tweak": list("vwxyz") + ["v", "w"],
                         "gain_hh": [0.5, 2.0, 1.0, 3.0, 0.05, 1.0, -1.0],
                         "admissible": [True, True, True, False, True, True, True]})
    top = D.rank_top3(plan)
    a = top[top.pitcher_id == "a"]
    assert a["tweak"].tolist() == ["w", "x", "v"] and a["rank"].tolist() == [1, 2, 3]  # y inadmisible, z ruido
    assert top[top.pitcher_id == "b"]["tweak"].tolist() == ["v"]  # w es negativo


def test_axis_sign_estimation_and_new_pitch_helpers():
    rng = np.random.default_rng(1)
    n = 600
    axis = rng.uniform(190, 230, n)
    ang = 0.8 * (axis - 210) + rng.normal(0, 3, n)  # el vector gira con el eje
    th = np.radians(ang)
    f = pd.DataFrame({"pitch_family": "Four-Seam", "spin_axis_arm": axis,
                      "InducedVertBreak": 17 * np.cos(th), "hb_arm": 17 * np.sin(th)})
    assert D.estimate_axis_sign(f) == 1.0
    f["spin_axis_arm"] = 420 - f["spin_axis_arm"]  # eje invertido
    assert D.estimate_axis_sign(f) == -1.0
    assert D.arsenal_delta_with_new_pitch(95.0, 100.0, 0.1) == pytest.approx(-0.5)  # un lanzamiento peor que el arsenal resta


def test_comparable_profile_needs_enough_comparables():
    rng = np.random.default_rng(2)
    n = 30
    cols = D.PROFILE_FEATURES + D.DIFF_FEATURES
    cen = pd.DataFrame(rng.normal(0, 1, (n, len(cols))), columns=cols)
    cen["is_rhp"], cen["fb_velo"], cen["arm_angle"] = 1, rng.normal(93, 1, n), rng.normal(30, 4, n)
    pitcher = pd.Series({"is_rhp": 1, "fb_velo": 93.0, "arm_angle": 30.0})
    mask = pd.Series(True, index=cen.index)
    assert D.comparable_profile(cen, pitcher, mask) is not None
    assert D.comparable_profile(cen, pd.Series({"is_rhp": 0, "fb_velo": 93.0, "arm_angle": 30.0}), mask) is None


def test_smoke_on_synthetic_fixture(synthetic_pitches):
    from stuffplus.features.identity import assign_pitch_id
    from stuffplus.models.stuff import add_stuff_features
    from stuffplus.schema import clean

    d = add_stuff_features(assign_pitch_id(clean(synthetic_pitches)))
    d = d[d.pitch_id >= 0]
    assert D.estimate_axis_sign(d) in (-1.0, 1.0)
    assert isinstance(D.slot_movement_slopes(d, controls=("RelSpeed",)), dict)
    fb = d["pitch_family"].astype(str).isin(D.FASTBALL_FAMILIES)
    out = D.add_velocity(d.reset_index(drop=True), fb.reset_index(drop=True), 1.0)
    assert len(out) == len(d)
