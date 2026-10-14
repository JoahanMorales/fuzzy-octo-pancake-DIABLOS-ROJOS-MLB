"""HACK-021: perfil de prospecto a partir de un arsenal corto o un CSV Trackman."""
from __future__ import annotations

import pandas as pd
import pytest

from stuffplus.api import PitchInput
from stuffplus.prospect import VERDICTS, evaluate_arsenal

ROOT_SEASONS = pd.DataFrame({
    "pitcher_anon_id": ["pitcher_00001", "pitcher_00002", "pitcher_00003", "pitcher_00004"],
    "year": [2026, 2026, 2026, 2026],
    "pitches": [100, 100, 100, 100],
    "throws": ["Right", "Right", "Right", "Right"],
    "delta_cdmx": [-10.0, -10.0, -10.0, -10.0],
    "stuff_plus_harp_helu": [80.0, 90.0, 100.0, 110.0],
})
ROOT_PITCHES = pd.DataFrame({
    "pitcher_anon_id": [f"pitcher_{i:05d}" for i in range(1, 7)],
    "year": [2026] * 6,
    "pitch_family": ["Four-Seam"] * 6,
    "shape": ["riding 4S"] * 6,
    "velo": [90, 92, 94, 95, 96, 98],
    "ivb": [16, 17, 18, 18, 19, 20],
    "hb": [6, 7, 8, 8, 9, 10],
    "stuff_plus_harp_helu": [80, 88, 96, 100, 104, 110],
    "pitches": [40] * 6,
})
ROOT_SHAPES = pd.DataFrame({
    "shape": ["riding 4S", "sweeper", "4S"],
    "pitches": [100, 100, 100],
    "delta_hr_per_fb_pct": [1.0, 9.0, 5.0],
})


def _pitch(pitch_type="Four-Seam", velo=95.0, ivb=18.0, hb=8.0, usage=None, throws="Right", rho_measured=1.0):
    arsenal = {} if usage is None else {"usage": usage}
    return PitchInput(
        pitch_type, throws, velo, 2300, 210, ivb, hb, extension=6.2, rho_measured=rho_measured, arsenal=arsenal,
    )


def _fake_predict(table):
    def predict(pitch, rho="harp_helu", flavour="environment"):
        hh, neutral = table[pitch.velo]
        return {
            "stuff_plus": hh, "stuff_plus_neutral": neutral, "location_plus": None,
            "pitching_plus": hh, "demo_data": True,
        }
    return predict


def _eval(pitches, monkeypatch, table, **kwargs):
    monkeypatch.setattr("stuffplus.prospect.predict_pitch", _fake_predict(table))
    return evaluate_arsenal(
        pitches, seasons=ROOT_SEASONS, pitch_table=ROOT_PITCHES, shapes=ROOT_SHAPES,
        per_point=0.0007237, runs_per_win_home=14.329, **kwargs,
    )


def test_rejects_arsenal_outside_two_to_five(monkeypatch):
    monkeypatch.setattr("stuffplus.prospect.predict_pitch", _fake_predict({95: (100, 100)}))
    with pytest.raises(ValueError):
        evaluate_arsenal([_pitch()], seasons=ROOT_SEASONS, pitch_table=ROOT_PITCHES, shapes=ROOT_SHAPES, per_point=1, runs_per_win_home=10)
    with pytest.raises(ValueError):
        evaluate_arsenal([_pitch(velo=90 + i) for i in range(6)], seasons=ROOT_SEASONS, pitch_table=ROOT_PITCHES, shapes=ROOT_SHAPES, per_point=1, runs_per_win_home=10)


def test_usage_weighted_arsenal_and_single_scoring_call(monkeypatch):
    calls = []

    def predict(pitch, rho="harp_helu", flavour="environment"):
        calls.append((rho, flavour, pitch.velo))
        hh, neutral = {95: (110, 100), 86: (90, 80)}[pitch.velo]
        return {"stuff_plus": hh, "stuff_plus_neutral": neutral, "location_plus": 100, "pitching_plus": hh, "demo_data": True}

    monkeypatch.setattr("stuffplus.prospect.predict_pitch", predict)
    slider = PitchInput("Slider", "Right", 86, 2500, 120, 2, -12, extension=6.2, arsenal={"usage": 0.25})
    out = evaluate_arsenal(
        [_pitch(velo=95, usage=0.75), slider],
        seasons=ROOT_SEASONS, pitch_table=ROOT_PITCHES, shapes=ROOT_SHAPES, per_point=0.001, runs_per_win_home=10,
    )
    assert calls == [("harp_helu", "environment", 95.0), ("harp_helu", "environment", 86.0)]
    assert out["arsenal"]["stuff_plus_harp_helu"] == pytest.approx(105.0)
    assert out["arsenal"]["stuff_plus_neutral"] == pytest.approx(95.0)
    assert out["arsenal"]["delta_cdmx"] == pytest.approx(10.0)
    assert out["pitches"][0]["shape"] == "riding 4S"
    assert out["pitches"][1]["shape"] == "sweeper"
    assert {row["pitch_type"] for row in out["pitches"]} == {"Four-Seam", "Slider"}


def test_shape_uses_sea_level_movement_not_the_thin_air_label(monkeypatch):
    slider = PitchInput("Slider", "Right", 86, 2500, 120, 2, -12, extension=6.2)
    out = _eval([_pitch(ivb=14.0, rho_measured=0.8), slider], monkeypatch, {95: (100, 90), 86: (90, 80)})
    by_type = {row["pitch_type"]: row["shape"] for row in out["pitches"]}
    assert by_type["Four-Seam"] == "riding 4S"


def test_index_hr_runs_and_verdicts(monkeypatch):
    signed = _eval(
        [_pitch(velo=95, usage=0.6), PitchInput("Slider", "Right", 86, 2500, 120, 2, -4, arsenal={"usage": 0.4})],
        monkeypatch, {95: (110, 100), 86: (110, 100)},
    )
    assert signed["altitude_proof_index"] == pytest.approx(120.0)
    assert signed["index_kind"] == "model_delta_vs_league"
    assert signed["hr_risk"] is False
    assert signed["verdict"] == "Firmar"
    assert signed["runs_saved_home"] == pytest.approx((110 - 100) * 0.0007237 * 1250, abs=0.02)
    assert signed["wins_saved_home"] == pytest.approx(signed["runs_saved_home"] / 14.329, abs=0.002)

    avoid = _eval([_pitch(velo=90), _pitch(velo=88, ivb=10, hb=4)], monkeypatch, {90: (80, 70), 88: (80, 70)})
    assert avoid["verdict"] == "Evitar para casa"

    develop = _eval([_pitch(velo=94), _pitch(velo=92, ivb=10, hb=4)], monkeypatch, {94: (100, 90), 92: (100, 90)})
    assert develop["verdict"] == "Desarrollar"
    assert set(VERDICTS) == {"Firmar", "Desarrollar", "Evitar para casa"}


def test_hr_flag_when_arsenal_beats_league_hr_rate(monkeypatch):
    risky = _eval(
        [_pitch("Slider", velo=86, ivb=2, hb=-12), PitchInput("Changeup", "Right", 84, 1700, 220, 6, 12)],
        monkeypatch, {86: (100, 120), 84: (100, 120)},
    )
    assert risky["pitches"][0]["shape"] == "sweeper"
    assert risky["hr_risk"] is True
    assert risky["hr_risk_shape"] == "sweeper"
    assert risky["verdict"] == "Evitar para casa"


def test_five_anonymized_comparables(monkeypatch):
    out = _eval([_pitch(), PitchInput("Changeup", "Right", 84, 1700, 220, 8, 14)], monkeypatch, {95: (100, 90), 84: (90, 80)})
    assert len(out["comparables"]) == 5
    assert out["comparable_pitch"]["pitch_type"] == "Four-Seam"
    for row in out["comparables"]:
        assert row["pitcher_anon_id"].startswith("pitcher_")
        assert set(row) == {"pitcher_anon_id", "year", "shape", "pitch_family", "distance", "stuff_plus_harp_helu", "velo"}
    distances = [row["distance"] for row in out["comparables"]]
    assert distances == sorted(distances)


def test_trackman_csv_aggregates_to_arsenal(tmp_path, monkeypatch):
    frame = pd.DataFrame({
        "AutoPitchType": ["Four-Seam"] * 3 + ["Slider"] * 1 + ["Sweeper"] * 1,
        "PitcherThrows": ["Right"] * 5,
        "RelSpeed": [95, 96, 94, 85, 84],
        "SpinRate": [2300, 2300, 2300, 2500, 2500],
        "SpinAxis": [210, 200, 220, 100, 110],
        "InducedVertBreak": [18, 18, 18, 3, 2],
        "HorzBreak": [8, 8, 8, -6, -12],
    })
    path = tmp_path / "prospecto.csv"
    frame.to_csv(path, index=False)
    out = _eval(path, monkeypatch, {95: (108, 98), 84.5: (96, 88)})
    assert len(out["pitches"]) == 2
    by_type = {row["pitch_type"]: row for row in out["pitches"]}
    assert by_type["Four-Seam"]["usage"] == pytest.approx(0.6)
    assert by_type["Slider"]["usage"] == pytest.approx(0.4)
    assert by_type["Four-Seam"]["velo"] == pytest.approx(95.0)
    assert out["demo_data"] is True


def test_real_leaderboards_return_anonymized_lmb_arms(monkeypatch):
    monkeypatch.setattr("stuffplus.prospect.predict_pitch", _fake_predict({95: (100, 90), 84: (90, 80)}))
    out = evaluate_arsenal([_pitch(), PitchInput("Changeup", "Right", 84, 1700, 220, 8, 14)])
    assert len(out["comparables"]) == 5
    assert all(row["pitcher_anon_id"].startswith("pitcher_") for row in out["comparables"])
    assert out["verdict"] in VERDICTS
    assert out["sources"]["runs"].endswith("(Stuff+, rv_x)")
    assert out["home_pitches"] == 1250
