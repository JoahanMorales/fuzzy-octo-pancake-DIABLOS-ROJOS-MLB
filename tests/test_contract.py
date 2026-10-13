"""HACK-002: clean schema, splits and the predict API contract."""
from __future__ import annotations

import numpy as np
import pytest

from stuffplus import api, schema, splits


@pytest.fixture
def clean_df(synthetic_pitches):
    return schema.clean(synthetic_pitches)


# ---------- schema.clean ----------

def test_clean_drops_edge_cases_and_reports(synthetic_pitches, clean_df):
    rep = clean_df.attrs["clean_report"]
    assert rep["rows_in"] == len(synthetic_pitches)
    assert rep["rows_out"] == len(clean_df)
    assert rep["altitude_missing"] > 0 and rep["pitcher_hand_unknown"] > 0 and rep["pitch_type_dropped"] > 0
    assert set(clean_df.altitude_category.astype(str)) <= set(schema.ALTITUDE_LEVELS)
    assert set(clean_df.PitcherThrows) <= set(schema.HANDS)
    assert set(clean_df.BatterSide) <= set(schema.HANDS)
    assert set(clean_df.AutoPitchType.astype(str)) <= set(schema.PITCH_TYPES)
    assert "Sweeper" not in set(clean_df.AutoPitchType.astype(str))


def test_clean_maps_switch_batter_to_side_faced(synthetic_pitches, clean_df):
    switch_rows = synthetic_pitches.index[synthetic_pitches.BatterSide == "Switch"]
    assert rep_switch(clean_df) == len(switch_rows) > 0
    # the switch batter always stands opposite the pitcher's hand after cleaning
    b = synthetic_pitches.loc[switch_rows[0], "batter_anon_id"]
    rows = clean_df[clean_df.batter_anon_id == b]
    assert (rows.BatterSide != rows.PitcherThrows).all()


def rep_switch(df):
    return df.attrs["clean_report"]["switch_batters_mapped"]


def test_clean_types_and_helpers(clean_df):
    assert clean_df.EffectiveVelo.dtype.kind == "f"
    assert str(clean_df.AutoPitchType.dtype) == "category"
    assert clean_df.same_side.isin([0, 1]).all()
    assert (clean_df.home_batting == (clean_df["Top/Bottom"].astype(str) == "Bottom")).all()
    assert clean_df.attrs["clean_report"]["rows_out"] == len(clean_df)


def test_pa_ids_follow_the_count(clean_df):
    first = clean_df.groupby("pa_id").head(1)
    assert (first["count"] == "0-0").mean() > 0.97
    assert (clean_df.groupby("pa_id").pa_ends.sum() <= 1).all()
    assert (clean_df.pitch_number_in_pa >= 1).all()
    # pa ids never span two games
    assert (clean_df.groupby("pa_id").game_anon_id.nunique() == 1).all()


def test_feature_lists_are_disjoint_from_targets_and_ids():
    targets, ids = set(schema.TARGET_COLUMNS), set(schema.ID_COLUMNS)
    for feats in (schema.PHYSICAL_FEATURES, schema.FLIGHT_FEATURES, schema.LOCATION_FEATURES, schema.CONTEXT_FEATURES):
        assert not set(feats) & (targets | ids)


def test_leak_guard(clean_df):
    schema.assert_no_target_leak(schema.PHYSICAL_FEATURES, allow_location=False)
    with pytest.raises(schema.LeakError):
        schema.assert_no_target_leak(["RelSpeed", "is_whiff"])
    with pytest.raises(schema.LeakError):
        schema.assert_no_target_leak(["RelSpeed", "PlateLocSide"], allow_location=False)
    X = schema.feature_frame(clean_df, schema.PHYSICAL_FEATURES, allow_location=False)
    assert list(X.columns) == schema.PHYSICAL_FEATURES


# ---------- splits ----------

def test_pitcher_kfold_is_grouped_complete_and_deterministic(clean_df):
    folds = list(splits.pitcher_group_kfold(clean_df, k=5))
    assert len(folds) == 5
    seen = np.concatenate([te for _, te in folds])
    assert sorted(seen) == list(range(len(clean_df)))
    for tr, te in folds:
        assert not set(clean_df.pitcher_anon_id.iloc[tr]) & set(clean_df.pitcher_anon_id.iloc[te])
    again = list(splits.pitcher_group_kfold(clean_df, k=5))
    assert all((a[1] == b[1]).all() for a, b in zip(folds, again))
    sizes = [len(te) for _, te in folds]
    assert max(sizes) / min(sizes) < 1.6


def test_missing_pitcher_ids_are_dropped_and_tolerated(synthetic_pitches):
    raw = synthetic_pitches.copy()
    raw.loc[raw.index[:7], "pitcher_anon_id"] = None
    out = schema.clean(raw)
    assert out.pitcher_anon_id.notna().all()
    assert out.attrs["clean_report"]["pitcher_id_missing"] >= 1
    folds = splits.pitcher_folds(raw, k=5)  # raw frame with NaN ids must not crash
    assert folds.notna().all() and set(folds) == set(range(5))


def test_season_and_park_holdouts(clean_df):
    tr, te = splits.season_holdout(clean_df)
    assert set(clean_df.year.iloc[tr]) == {2024, 2025} and set(clean_df.year.iloc[te]) == {2026}
    tr, te = splits.park_holdout(clean_df)
    assert set(clean_df.altitude_category.astype(str).iloc[te]) == {"Extreme Altitude"}
    assert "Extreme Altitude" not in set(clean_df.altitude_category.astype(str).iloc[tr])


# ---------- api ----------

def _fastball(**kw):
    base = dict(pitch_type="Four-Seam", throws="Right", velo=95.0, spin_rate=2400, spin_axis=210, ivb=18.0, hb=9.0)
    base.update(kw)
    return api.PitchInput(**base)


def test_predict_pitch_contract_keys():
    out = api.predict_pitch(_fastball(plate_x=0.7, plate_z=3.3, balls=0, strikes=2))
    assert set(out) == set(api.PREDICTION_KEYS)
    assert set(out["probs"]) == set(api.PROB_KEYS)
    assert all(0.0 <= v <= 1.0 for v in out["probs"].values())
    assert out["location_plus"] is not None
    assert out["demo_data"] is True


def test_predict_pitch_is_deterministic_and_location_optional():
    p = _fastball()
    assert api.predict_pitch(p) == api.predict_pitch(p)
    assert api.predict_pitch(p)["location_plus"] is None


def test_altitude_reduces_movement_and_neutral_ignores_rho():
    p = _fastball()
    cdmx, sea = api.predict_pitch(p, "harp_helu"), api.predict_pitch(p, "sea_level")
    assert cdmx["movement_expected"]["ivb"] < sea["movement_expected"]["ivb"]
    assert cdmx["stuff_plus_neutral"] == sea["stuff_plus_neutral"] == sea["stuff_plus"]
    neutral = api.predict_pitch(p, "harp_helu", flavour="neutral")
    assert neutral["stuff_plus"] == sea["stuff_plus"]
    cmp = api.compare_environments(p)
    assert cmp["delta_ivb"] < 0 and cmp["delta_stuff_plus"] == round(cdmx["stuff_plus"] - sea["stuff_plus"], 1)


def test_movement_measured_in_cdmx_translates_back_up():
    seen_in_cdmx = _fastball(ivb=14.6, rho_measured=0.81)
    sea = api.predict_pitch(seen_in_cdmx, "sea_level")
    assert sea["movement_expected"]["ivb"] == pytest.approx(14.6 / 0.81, abs=0.01)


def test_input_validation():
    with pytest.raises(ValueError):
        _fastball(pitch_type="Knuckleball")
    with pytest.raises(ValueError):
        _fastball(velo=130)
    with pytest.raises(ValueError):
        api.predict_pitch(_fastball(), rho=0.2)
    with pytest.raises(ValueError):
        api.predict_pitch(_fastball(), rho="mars")


def test_from_row_round_trip(clean_df):
    row = clean_df.iloc[0]
    p = api.PitchInput.from_row(row)
    assert p.velo == pytest.approx(row.RelSpeed)
    assert set(api.predict_pitch(p)) == set(api.PREDICTION_KEYS)
