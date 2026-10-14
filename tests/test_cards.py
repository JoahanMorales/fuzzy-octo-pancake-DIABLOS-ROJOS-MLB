"""HACK-034: ficha de lanzador a 1600×900, flechas en marco del brazo, PNG y PDF."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from matplotlib.patches import FancyArrowPatch
from PIL import Image

from stuffplus import cards
from stuffplus.physics.constants import RHO_HARP_HELU

TOKENS = {
    "bg": "#0B0B0D", "panel": "#16161A", "line": "#2A2A31", "text": "#F4F4F5", "muted": "#A1A1AA",
    "red": "#D71920", "red_soft": "#FF4B52", "white": "#FFFFFF", "ok": "#3FB950",
}


def _frames():
    season = pd.DataFrame([
        {"pitcher_anon_id": "pitcher_00001", "year": 2026, "throws": "Right", "pitches": 400,
         "stuff_plus_harp_helu": 96.0, "altitude_proof_index": 90.0},
        {"pitcher_anon_id": "pitcher_00002", "year": 2026, "throws": "Left", "pitches": 380,
         "stuff_plus_harp_helu": 110.0, "altitude_proof_index": 108.0},
        {"pitcher_anon_id": "pitcher_00011", "year": 2026, "throws": "Right", "pitches": 360,
         "stuff_plus_harp_helu": 101.0, "altitude_proof_index": 100.0},
    ])
    # pitcher_00011 tiene pitch_id 1; la llave no debe confundirse con un sufijo suelto.
    pitches = pd.DataFrame([
        {"pitcher_anon_id": "pitcher_00001", "year": 2026, "pitch_id": 1, "pitch_family": "Four-Seam",
         "shape": "riding 4S", "usage": 0.6, "velo": 94.0, "ivb": 18.0, "hb": 8.0,
         "stuff_plus": 112.0, "stuff_plus_harp_helu": 100.0, "location_plus": 102.0, "pitching_plus": 104.0,
         "delta_cdmx": -12.0},
        {"pitcher_anon_id": "pitcher_00001", "year": 2026, "pitch_id": 11, "pitch_family": "Slider",
         "shape": "sweeper", "usage": 0.4, "velo": 84.0, "ivb": 2.0, "hb": -6.0,
         "stuff_plus": 98.0, "stuff_plus_harp_helu": 90.0, "location_plus": 99.0, "pitching_plus": 97.0,
         "delta_cdmx": -8.0},
        {"pitcher_anon_id": "pitcher_00002", "year": 2026, "pitch_id": 0, "pitch_family": "Changeup",
         "shape": "change", "usage": 1.0, "velo": 85.0, "ivb": 6.0, "hb": 10.0,
         "stuff_plus": 108.0, "stuff_plus_harp_helu": 110.0, "location_plus": 100.0, "pitching_plus": 106.0,
         "delta_cdmx": 2.0},
        {"pitcher_anon_id": "pitcher_00011", "year": 2026, "pitch_id": 1, "pitch_family": "Sinker",
         "shape": "sinker", "usage": 1.0, "velo": 92.0, "ivb": 8.0, "hb": 12.0,
         "stuff_plus": 101.0, "stuff_plus_harp_helu": 101.0, "location_plus": 100.0, "pitching_plus": 100.0,
         "delta_cdmx": 0.0},
    ])
    sens_p = pd.DataFrame([
        {"pitcher_anon_id": "pitcher_00001", "year": 2026, "altitude_proof_index": 90.0, "eligible": True,
         "driver_family": "Four-Seam", "physical_reason": "Cambio de movimiento estimado: IVB -2.00 pulgadas."},
        {"pitcher_anon_id": "pitcher_00002", "year": 2026, "altitude_proof_index": 108.0, "eligible": True,
         "driver_family": "Changeup", "physical_reason": "Cambio de movimiento estimado: IVB -1.00 pulgadas."},
        {"pitcher_anon_id": "pitcher_00011", "year": 2026, "altitude_proof_index": 100.0, "eligible": True,
         "driver_family": "Sinker", "physical_reason": "Cambio de movimiento estimado: IVB -1.50 pulgadas."},
    ])
    # Familia distinta en la recta de pitcher_00001 → respaldo por forma, no el Δ del pitch_key.
    sens_k = pd.DataFrame([
        {"pitcher_anon_id": "pitcher_00001", "year": 2026, "pitch_key": "pitcher_00001_2026_1",
         "pitch_family": "Sinker", "delta_ivb_in": 9.0, "delta_hb_arm_in": 9.0},
        {"pitcher_anon_id": "pitcher_00001", "year": 2026, "pitch_key": "pitcher_00001_2026_11",
         "pitch_family": "Slider", "delta_ivb_in": -1.0, "delta_hb_arm_in": 2.0},
        {"pitcher_anon_id": "pitcher_00002", "year": 2026, "pitch_key": "pitcher_00002_2026_0",
         "pitch_family": "Changeup", "delta_ivb_in": -0.5, "delta_hb_arm_in": 1.5},
        {"pitcher_anon_id": "pitcher_00011", "year": 2026, "pitch_key": "pitcher_00011_2026_1",
         "pitch_family": "Sinker", "delta_ivb_in": -0.2, "delta_hb_arm_in": 0.4},
    ])
    shapes = pd.DataFrame([
        {"shape": "riding 4S", "delta_ivb_in": -3.0, "delta_hb_arm_in": 0.5, "physics": "Menos ride en aire delgado."},
        {"shape": "sweeper", "delta_ivb_in": 0.6, "delta_hb_arm_in": 2.1, "physics": "El sweeper pierde whiff."},
        {"shape": "change", "delta_ivb_in": -1.0, "delta_hb_arm_in": 0.2, "physics": "El cambio pierde profundidad."},
        {"shape": "sinker", "delta_ivb_in": -1.2, "delta_hb_arm_in": 0.3, "physics": "El sinker pierde hundimiento."},
    ])
    # season table in the loader sense does not include the index; deck merge needs it on sensitivity only.
    season_lb = season.drop(columns=["altitude_proof_index"])
    return {
        "pitcher_season": season_lb,
        "pitcher_pitch": pitches,
        "sensitivity_pitchers": sens_p,
        "sensitivity_pitches": sens_k,
        "shapes": shapes,
    }


def test_hb_arm_flips_lefties():
    assert cards.hb_arm(10, "Right") == 10
    assert cards.hb_arm(10, "Left") == -10
    assert cards.hb_arm(-4, "Left") == 4


def test_full_pitch_key_and_family_fallback():
    tables = _frames()
    card = cards.build_card("pitcher_00001", 2026, tables)
    by_id = {row["pitch_id"]: row for row in card["arsenal"]}
    assert by_id[11]["pitch_key"] == "pitcher_00001_2026_11"
    assert by_id[11]["arrow"] and by_id[11]["delta_ivb"] == pytest.approx(-1.0)
    assert by_id[11]["delta_source"].startswith("reports/pitcher_sensitivity/pitches.csv")
    # Familia distinta: no usa el Δ 9.0 del pitch_key; usa la forma.
    assert by_id[1]["delta_ivb"] == pytest.approx(-3.0)
    assert "delta_by_shape" in by_id[1]["delta_source"]
    tables["sensitivity_pitchers"].loc[tables["sensitivity_pitchers"]["pitcher_anon_id"] == "pitcher_00001",
                                       "driver_family"] = "Slider"
    tables["sensitivity_pitchers"].loc[tables["sensitivity_pitchers"]["pitcher_anon_id"] == "pitcher_00001",
                                       "physical_reason"] = "NO-DEBE-SALIR"
    switched = cards.build_card("pitcher_00001", 2026, tables)
    assert "NO-DEBE-SALIR" not in switched["recommendations"][1]["text"]
    assert "-3.0" in switched["recommendations"][1]["text"]
    assert len(card["recommendations"]) == 3
    assert all(rec["source"] for rec in card["recommendations"])
    blob = " ".join(rec["text"] for rec in card["recommendations"])
    assert "Stuff+ Harp Helú" in blob and "neutral" in blob
    assert "2240" not in Path(cards.__file__).read_text(encoding="utf-8")
    assert card["rho"] == pytest.approx(RHO_HARP_HELU)
    assert "PitchUID" not in card and all("PitchUID" not in row for row in card["arsenal"])


def test_lefty_arrow_is_arm_side(tmp_path):
    card = cards.build_card("pitcher_00002", 2026, _frames())
    row = card["arsenal"][0]
    assert row["hb_arm"] == pytest.approx(-10.0)
    assert row["x1"] == pytest.approx(-10.0 + 1.5)
    fig = cards.render_card(card, TOKENS)
    ax = fig.axes[1]
    offsets = ax.collections[0].get_offsets()
    assert offsets[0, 0] == pytest.approx(-10.0)
    arrows = [p for p in ax.patches if isinstance(p, FancyArrowPatch)]
    assert len(arrows) == 1
    png = tmp_path / "left.png"
    fig.savefig(png, dpi=cards.DPI, facecolor=fig.get_facecolor())
    assert Image.open(png).size == (1600, 900)


def test_marker_without_arrow_when_shape_missing():
    tables = _frames()
    tables["shapes"] = tables["shapes"][tables["shapes"]["shape"] != "sinker"]
    tables["sensitivity_pitches"] = tables["sensitivity_pitches"][
        tables["sensitivity_pitches"]["pitcher_anon_id"] != "pitcher_00011"]
    card = cards.build_card("pitcher_00011", 2026, tables)
    assert len(card["arsenal"]) == 1 and card["arsenal"][0]["arrow"] is False
    fig = cards.render_card(card, TOKENS)
    ax = fig.axes[1]
    assert ax.collections[0].get_offsets().shape[0] == 1
    assert not any(isinstance(p, FancyArrowPatch) for p in ax.patches)
    labels = " ".join(t.get_text() for t in fig.findobj(match=plt_text))
    assert "sin Δ" in labels
    assert "Stuff+ neutral" in labels and "Stuff+ Harp Helú" in labels
    assert "HB lado del brazo" in labels


def plt_text(artist):
    from matplotlib.text import Text
    return isinstance(artist, Text)


def test_png_is_1600x900_and_pdf_is_nonempty(tmp_path):
    card = cards.build_card("pitcher_00011", 2026, _frames())
    paths = cards.export_card(card, tmp_path, TOKENS)
    assert Image.open(paths["png"]).size == (1600, 900)
    raw = paths["pdf"].read_bytes()
    assert raw.startswith(b"%PDF") and len(raw) > 500


def test_batch_deck_and_staff_without_roster_csv(tmp_path):
    tables = _frames()

    def loader():
        return pd.DataFrame({"season": [2026, 2026], "franchise": [5, 11],
                              "pitcher_anon_id": ["pitcher_00002", "pitcher_00999"]})

    manifest = cards.batch_export(tmp_path, tables, TOKENS, staff_loader=loader)
    assert list(manifest["role"]) == ["deck_mayor_indice", "deck_menor_indice", "deck_mayor_stuff_harp"]
    assert (tmp_path / "deck" / "pitcher_00002_2026.png").exists()
    assert (tmp_path / "staff" / "pitcher_00002_2026.pdf").exists()
    assert not (tmp_path / "staff" / "pitcher_00999_2026.png").exists()
    assert not list(tmp_path.glob("*.csv")) or (tmp_path / "manifest.csv").exists()
    saved = pd.read_csv(tmp_path / "manifest.csv")
    assert set(saved["role"]) == set(manifest["role"])
    assert not list(tmp_path.glob("*staff*.csv"))
    assert "PitchUID" not in saved.columns


def test_batch_writes_staff_missing_when_maps_fail(tmp_path):
    def boom():
        raise FileNotFoundError("sin mapa")

    cards.batch_export(tmp_path, _frames(), TOKENS, staff_loader=boom)
    text = (tmp_path / "staff_missing.txt").read_text(encoding="utf-8")
    assert "staff candidato" in text
    assert (tmp_path / "deck" / "pitcher_00002_2026.png").exists()
    assert not (tmp_path / "staff").exists()


def test_prepare_page_missing_reports(tmp_path):
    state = cards.prepare_page(tmp_path)
    assert state["ok"] is False and "ficha" in state["message"].lower()


def test_real_reports_export_one_deck_card(tmp_path):
    root = Path(__file__).resolve().parents[1] / "reports"
    if not (root / "leaderboards" / "pitcher_pitch.csv").exists():
        pytest.skip("sin agregados")
    tables = cards.load_tables(root)
    pid, year, role = cards.deck_example_keys(tables)[0]
    card = cards.build_card(pid, year, tables)
    assert role == "deck_mayor_indice"
    assert card["altitude_proof_index"] is not None
    assert 1 <= len(card["recommendations"]) and len(card["recommendations"]) == 3
    paths = cards.export_card(card, tmp_path, TOKENS)
    assert Image.open(paths["png"]).size == (1600, 900)
    joined = " ".join(t.get_text() for t in cards.render_card(card, TOKENS).findobj(match=plt_text))
    assert "Harp Helú" in joined and "nivel del mar" in joined
