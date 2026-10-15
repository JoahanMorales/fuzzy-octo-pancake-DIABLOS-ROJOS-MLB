"""HACK-020: dashboard pages read bundle aggregates and the simulator shows both airs."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.components.movement import extremes, shape_points
from stuffplus import serving

st_testing = pytest.importorskip("streamlit.testing.v1")
ROOT = Path(__file__).resolve().parents[1]


def test_shape_points_translate_to_cdmx_and_rank():
    shapes = pd.DataFrame([
        {"shape": "riding 4S", "n": 100, "hb_sl": 9.0, "ivb_sl": 19.0},
        {"shape": "sweeper", "n": 40, "hb_sl": -13.0, "ivb_sl": -2.0},
    ])
    deltas = pd.DataFrame([
        {"shape": "riding 4S", "delta_ivb_in": -5.0, "delta_hb_arm_in": -3.0,
         "stuff_sea_level": 108.0, "stuff_harp_helu": 92.0},
        {"shape": "sweeper", "delta_ivb_in": 0.6, "delta_hb_arm_in": 2.0,
         "stuff_sea_level": 101.0, "stuff_harp_helu": 97.0},
    ])
    sea = shape_points(shapes, deltas, "sea")
    city = shape_points(shapes, deltas, "cdmx")
    ride = city.loc[city["shape"] == "riding 4S"].iloc[0]
    assert ride.ivb == pytest.approx(14.0)
    assert ride.hb == pytest.approx(6.0)
    assert sea.loc[sea["shape"] == "riding 4S", "ivb"].iloc[0] == pytest.approx(19.0)
    assert extremes(city) == ("sweeper", "riding 4S")
    assert extremes(sea) == ("riding 4S", "sweeper")


def test_read_table_uses_bundle_not_raw(tmp_path, monkeypatch):
    tables = tmp_path / "tables"
    tables.mkdir()
    pd.DataFrame([{"pitcher_anon_id": "pitcher_test", "pitching_plus": 120.0}]).to_csv(
        tables / "pitcher_season.csv", index=False)
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(tmp_path))
    got = serving.read_table("pitcher_season")
    assert got is not None and got.iloc[0]["pitcher_anon_id"] == "pitcher_test"
    assert serving.read_table("missing") is None
    text = (ROOT / "app/pages/2_Leaderboard.py").read_text(encoding="utf-8")
    alt = (ROOT / "app/pages/4_Altitud.py").read_text(encoding="utf-8")
    assert "load_raw" not in text and "load_raw" not in alt
    assert "stuff_model_df" not in text and "stuff_model_df" not in alt


def test_leaderboard_renders_bundle_rows(tmp_path, monkeypatch):
    tables = tmp_path / "tables"
    tables.mkdir()
    pd.DataFrame([{
        "pitcher_anon_id": "pitcher_test", "year": 2026, "pitches": 40,
        "stuff_plus": 110.0, "stuff_plus_harp_helu": 99.0, "location_plus": 101.0,
        "pitching_plus": 105.0, "delta_cdmx": -11.0, "arsenal": "4S 80%",
    }]).to_csv(tables / "pitcher_season.csv", index=False)
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(tmp_path))
    at = st_testing.AppTest.from_file(str(ROOT / "app/pages/2_Leaderboard.py"), default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "pitcher_test" in at.dataframe[0].value.to_csv(index=False)


def test_altitude_page_shows_shapes(tmp_path, monkeypatch):
    tables = tmp_path / "tables"
    tables.mkdir()
    pd.DataFrame([{
        "shape": "sweeper", "pitches": 10, "delta_stuff": -4.6, "verdict": "gana relativo",
        "physics": "menos Magnus", "delta_ivb_in": 0.6, "delta_hb_arm_in": 2.1,
        "stuff_sea_level": 101.0, "stuff_harp_helu": 96.4,
    }]).to_csv(tables / "delta_by_shape.csv", index=False)
    pd.DataFrame([{"shape": "sweeper", "n": 10, "hb_sl": -13.0, "ivb_sl": -1.7}]).to_csv(
        tables / "shapes.csv", index=False)
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(tmp_path))
    at = st_testing.AppTest.from_file(str(ROOT / "app/pages/4_Altitud.py"), default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]
    assert "sweeper" in at.dataframe[0].value.to_csv(index=False)
    assert any("Mapa de movimiento" in m.value for m in at.markdown)


def test_simulator_shows_both_plus_and_why():
    at = st_testing.AppTest.from_file(str(ROOT / "app/pages/1_Simulador.py"), default_timeout=30).run()
    assert at.info
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    text = "\n".join(m.value for m in at.markdown)
    assert "Location+" in text and "Pitching+" in text
    assert "ΔStuff+ CDMX" in text and "¿Por qué?" in text
    cache = (ROOT / "app/components/model.py").read_text(encoding="utf-8")
    assert "st.cache_resource" in cache and "load_bundle" in cache
