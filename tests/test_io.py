"""HACK-001: loader, config and synthetic fixture fidelity."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from stuffplus import config, io
from tests.fixtures.synthetic import SCHEMA

DICTIONARY = Path(__file__).resolve().parent.parent / "data" / "stuff_plus_data_dictionary.csv"


def test_load_raw_reads_parquet_and_columns(synthetic_parquet):
    df = io.load_raw(path=synthetic_parquet)
    assert len(df) > 4000
    sub = io.load_raw(columns=["year", "RelSpeed"], path=synthetic_parquet)
    assert list(sub.columns) == ["year", "RelSpeed"]


def test_load_raw_missing_file_has_clear_message(tmp_path):
    with pytest.raises(io.DataNotFoundError, match="data/raw"):
        io.load_raw(path=tmp_path / "nope.parquet")


def test_env_var_overrides_data_path(monkeypatch, tmp_path):
    target = tmp_path / "x.parquet"
    monkeypatch.setenv("STUFFPLUS_DATA", str(target))
    assert config.data_path() == target


def test_fixture_has_dictionary_columns(synthetic_pitches):
    expected = pd.read_csv(DICTIONARY)["column_name"].tolist()
    assert sorted(synthetic_pitches.columns) == sorted(expected)
    assert len(synthetic_pitches.columns) == 84


def test_fixture_dtypes_match_pyarrow_schema(synthetic_parquet):
    assert pq.read_schema(synthetic_parquet).remove_metadata().equals(SCHEMA)


def test_fixture_shape_and_coverage(synthetic_pitches):
    df = synthetic_pitches
    assert 4000 <= len(df) <= 8000
    assert set(df.year.unique()) == {2024, 2025, 2026}
    assert {"No Altitude", "Medium Altitude", "Extreme Altitude"} <= set(df.altitude_category.dropna())
    assert df.pitcher_anon_id.nunique() >= 40
    assert df.batter_anon_id.nunique() >= 60
    assert df.game_anon_id.nunique() >= 30
    assert df.RelSpeed.between(70, 102).all()
    assert df.InducedVertBreak.between(-25, 30).all()
    assert df.SpinRate.between(1000, 3200).all()


def test_fixture_has_cleaning_edge_cases(synthetic_pitches):
    df = synthetic_pitches
    assert df.altitude_category.isna().any()
    assert (df.PitcherThrows == "Undefined").any()
    assert (df.BatterSide == "Switch").any()
    assert {"Sweeper", "Other"} <= set(df.AutoPitchType.astype(str))


def test_fixture_game_order_is_consistent(synthetic_pitches):
    df = synthetic_pitches
    same_pa = df.batter_anon_id.eq(df.batter_anon_id.shift()) & df.game_anon_id.eq(df.game_anon_id.shift())
    total = df.Balls + df.Strikes
    assert (total >= total.shift())[same_pa].mean() > 0.99
    assert df["count"].eq(df.Balls.astype(int).astype(str) + "-" + df.Strikes.astype(int).astype(str)).all()
    assert (df.Outs <= 2).all()


def test_fixture_drag_reflects_altitude(synthetic_pitches):
    """Extreme parks must show ~16 % less drag, like the real data (Extreme/No ~ 0.84)."""
    df = synthetic_pitches
    v = np.sqrt(df.vx0 ** 2 + df.vy0 ** 2 + df.vz0 ** 2)
    k = -(df.ax0 * df.vx0 + df.ay0 * df.vy0 + (df.az0 + 32.174) * df.vz0) / v ** 3
    med = k.groupby(df.altitude_category).median()
    ratio = med["Extreme Altitude"] / med["No Altitude"]
    assert 0.78 < ratio < 0.88


def test_fixture_outcome_flags_are_coherent(synthetic_pitches):
    df = synthetic_pitches
    call = df.PitchCall.astype(str)
    assert (df.is_whiff[call == "StrikeSwinging"] == 1).all()
    assert (df.is_whiff[call != "StrikeSwinging"] == 0).all()
    assert (df.is_ball_in_play[call == "InPlay"] == 1).all()
    assert df.hit_type.notna().eq(call == "InPlay").all()
    assert (df.strikeout.sum() > 0) and (df.base_on_balls.sum() > 0) and (df.home_run.sum() > 0)
    assert (df.RunsScored >= 0).all()


@pytest.mark.skipif(not config.data_path().exists(), reason="raw ISAC data not present (expected in CI)")
def test_real_file_schema_matches_fixture_schema():
    real = pq.read_schema(config.data_path()).remove_metadata()
    assert real.names == SCHEMA.names
    for name in SCHEMA.names:
        r, s = real.field(name).type, SCHEMA.field(name).type
        assert str(r).split("<")[0] == str(s).split("<")[0], name
