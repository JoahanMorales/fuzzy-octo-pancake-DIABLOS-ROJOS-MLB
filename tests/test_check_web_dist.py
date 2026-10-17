"""HACK-050: the web build leak check and the real-data export (synthetic dist folders only)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cwd = _load("scripts/check_web_dist.py", "check_web_dist")


def _dist(tmp_path: Path) -> Path:
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (d / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (d / "data" / "real").mkdir(parents=True)
    agg = {"demo_data": False, "rows": [{"pitch_family": "Four-Seam", "stuff_plus": 101.2, "pitches": 900}] * 3000}
    (d / "data" / "real" / "shapes.json").write_text(json.dumps(agg), encoding="utf-8")
    return d


def test_clean_build_passes(tmp_path):
    assert cwd.check(_dist(tmp_path)) == []
    assert cwd.main([str(_dist(tmp_path / "b"))]) == 0


def test_json_with_pitch_level_rows_fails(tmp_path):
    d = _dist(tmp_path)
    rows = [{"PitchUID": f"u{i}", "RelSpeed": 94.0} for i in range(1001)]
    (d / "data" / "leak.json").write_text(json.dumps({"nested": {"rows": rows}}), encoding="utf-8")
    bad = cwd.check(d)
    assert any("leak.json" in b and "pitch id" in b for b in bad)


def test_json_with_three_raw_trackman_columns_fails_but_short_lists_pass(tmp_path):
    d = _dist(tmp_path)
    raw = [{"RelSpeed": 94, "SpinRate": 2300, "InducedVertBreak": 17}]
    (d / "data" / "raw.json").write_text(json.dumps(raw * 1001), encoding="utf-8")
    (d / "data" / "small.json").write_text(json.dumps(raw * 50), encoding="utf-8")
    bad = cwd.check(d)
    assert any("raw.json" in b for b in bad) and not any("small.json" in b for b in bad)


def test_binary_and_pitch_level_csv_fail(tmp_path):
    d = _dist(tmp_path)
    (d / "data" / "x.parquet").write_bytes(b"PAR1")
    lines = ["PitchUID,RelSpeed"] + [f"u{i},94" for i in range(1001)]
    (d / "data" / "p.csv").write_text("\n".join(lines), encoding="utf-8")
    bad = cwd.check(d)
    assert any("parquet" in b for b in bad) and any("p.csv" in b for b in bad)


def test_size_budget_and_missing_dist(tmp_path):
    d = _dist(tmp_path)
    (d / "assets" / "big.bin").write_bytes(b"0" * 2_000_000)
    assert any("MB >" in b for b in cwd.check(d, max_mb=1.0))
    assert cwd.check(tmp_path / "nope") and cwd.main([str(tmp_path / "nope")]) == 1


def test_real_export_flips_demo_flag_and_keeps_aggregates():
    run = _load("analysis/export_web/run.py", "export_web_run")
    doc = {"demo_data": True, "a": [{"demo_data": True, "x": 1}], "b": {"demo_data": True}}
    out = run._real(doc)
    assert out == {"demo_data": False, "a": [{"demo_data": False, "x": 1}], "b": {"demo_data": False}}
    assert doc["demo_data"] is True  # the input is not mutated
    assert run.MODELS_REL == "../models/"


@pytest.mark.skipif(not (ROOT / "reports/leaderboards/pitcher_season.csv").exists(), reason="needs committed reports")
def test_build_real_from_committed_reports_is_aggregate_only(tmp_path):
    run = _load("analysis/export_web/run.py", "export_web_run2")
    docs = run.build_real()
    assert "manifest.json" in docs and all(d.get("demo_data") is False for d in docs.values())
    assert sum(r.startswith("pitcher/") for r in docs) == docs["manifest.json"]["pitchers"]
    assert not any(r.startswith("models/") for r in docs)  # real trees stay in web/public/data/models/
    val = docs["validation.json"]
    for key, rel in run.VALIDATION_EXTRA.items():
        if (run.repo_root() / rel).is_file():
            assert val[key] and rel in val["sources"]
    assert {r["split"] for r in val["rows_fast"]} >= {"pitcher_kfold", "leave_one_park_out_1"}
