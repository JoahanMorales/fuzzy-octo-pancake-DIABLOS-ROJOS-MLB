"""HACK-038: el mock del contrato web sale de agregados y rechaza filas de lanzamiento."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from stuffplus import export_web
from stuffplus.export_web import LeakError

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "web" / "public" / "data" / "mock"


def test_mock_reads_league_delta_from_stuff_v2():
    # HACK-087: el ΔStuff+ de liga sale del modelo de producción (delta_by_shape.csv), no de "Stuff+ v2 (familia)"
    shapes = pd.read_csv(ROOT / "reports" / "altitude_delta" / "delta_by_shape.csv")
    league = float((shapes["delta_stuff"] - shapes["relative_to_league"]).mean())
    doc = export_web.build_mock(ROOT)["validation.json"]
    assert doc["model_version"] == "stuff_v2"
    assert doc["model"] == "pitch_family Stuff+ composite"
    assert doc["translation"] == "physics_translator"
    assert doc["highlights"]["league_delta_cdmx"] == round(league, 4)
    assert doc["highlights"]["source_model"] == export_web.PRODUCTION_MODEL


def test_parks_shapes_physics_and_split_staff():
    docs = export_web.build_mock(ROOT)
    parks = docs["parks.json"]["parks"]
    assert len(parks) == 20
    assert {p["id"] for p in parks} >= {"5", "11"}
    assert docs["shapes.json"]["shapes"]
    assert all("cd_sea" in row and "cl_sea" in row and "elasticity" in row for row in docs["physics.json"]["families"])
    franchises = {f["id"]: f for f in docs["staff.json"]["franchises"]}
    assert set(franchises) == {"5", "11"}
    assert docs["staff.json"]["pooled"] is False
    ids_5 = {p["pitcher_anon_id"] for p in franchises["5"]["pitchers"]}
    ids_11 = {p["pitcher_anon_id"] for p in franchises["11"]["pitchers"]}
    assert ids_5.isdisjoint(ids_11)
    sample = next(doc for name, doc in docs.items() if name.startswith("pitcher/"))
    assert "AutoPitchType" not in json.dumps(sample)
    assert sample["seasons"][0]["arsenal_pitches"][0]["pitch_id"] >= 0


def test_refuses_pitch_level_rows():
    rows = [{"PitchUID": str(i), "RelSpeed": 90, "SpinRate": 2200, "PlateLocSide": 0.1} for i in range(1001)]
    with pytest.raises(LeakError):
        export_web.assert_aggregate({"rows": rows})
    raw = [{"pitcher_anon_id": "p", "RelSpeed": 90, "SpinRate": 2200, "InducedVertBreak": 15} for _ in range(1001)]
    with pytest.raises(LeakError):
        export_web.assert_aggregate({"rows": raw})


def test_aggregated_tables_over_1000_rows_pass():
    rows = [{"pitcher_anon_id": f"p{i}", "year": 2025, "pitches": 40, "stuff_plus": 100} for i in range(1001)]
    export_web.assert_aggregate({"rows": rows})


def test_write_mock_matches_committed_files_and_stays_under_25mb(tmp_path):
    export_web.write_mock(tmp_path, ROOT)
    written = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.json"))
    committed = sorted(p.relative_to(MOCK).as_posix() for p in MOCK.rglob("*.json"))
    assert written == committed
    for rel in written:
        assert json.loads((tmp_path / rel).read_text(encoding="utf-8")) == json.loads((MOCK / rel).read_text(encoding="utf-8"))
    assert export_web.dir_mb(tmp_path) <= export_web.MAX_MB


def test_cli_mock(tmp_path):
    assert export_web.main(["--mock", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "parks.json").is_file()
