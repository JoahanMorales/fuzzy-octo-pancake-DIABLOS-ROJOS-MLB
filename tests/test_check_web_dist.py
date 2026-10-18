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
    assert not set(run.VALIDATION_EXTRA) & set(docs["validation.json"])  # strict schema: keys unchanged
    extra = docs["validation_extra.json"]
    for key, rel in run.VALIDATION_EXTRA.items():
        if (run.repo_root() / rel).is_file():
            assert extra[key] and rel in extra["sources"]
    assert {r["split"] for r in extra["rows_fast"]} >= {"pitcher_kfold", "leave_one_park_out_1"}


@pytest.mark.skipif(not (ROOT / "reports/design_lab/tweak_summary.csv").exists(), reason="needs committed reports")
def test_real_export_carries_the_design_lab():
    run = _load("analysis/export_web/run.py", "export_web_run3")
    lab = run.design_lab(run.repo_root())
    assert lab["demo_data"] is True  # envelope; build_real flips it to False
    assert lab["tweaks"] and lab["plan"] and all(s.startswith("reports/design_lab/") for s in lab["sources"])
    docs = run.build_real()
    assert docs["design_lab.json"]["demo_data"] is False and "design_lab.json" in docs["manifest.json"]["files"]


def _scores(seed: int = 0):
    """Synthetic pitch scores: pitcher-season true Stuff+ plus per-pitch noise (sd 20), some altitude-heavy."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    rows = []
    for p in range(240):
        true, n = rng.normal(100, 6), int(rng.integers(500, 1800))
        alt = "Extreme Altitude" if p % 4 == 0 else "No Altitude"
        x = true + rng.normal(0, 20, n)
        rows.append(pd.DataFrame({"pitcher_anon_id": f"pitcher_{p:05d}", "year": 2025, "altitude_category": alt,
                                  "stuff_plus": x, "stuff_plus_harp_helu": x - 8 + rng.normal(0, 3, n)}))
    return pd.concat(rows, ignore_index=True)


def test_uncertainty_by_n_narrows_with_pitches_and_covers():
    unc = _load("analysis/export_web/uncertainty.py", "export_web_unc")
    t = unc.table(_scores())
    assert set(t.air) == {"neutral", "harp_helu"}
    for _, g in t.groupby("air"):
        g = g.sort_values("n_pitches")
        assert g.half_width.is_monotonic_decreasing  # more pitches, narrower band
        assert (g.coverage.between(0.85, 0.97)).all()
    big = t[(t.air == "neutral") & (t.n_pitches == 100)].iloc[0]
    assert 2.0 < big.half_width < 5.0  # ≈ 1.645 · 20/√100 widened by the noise of the rest


def test_real_export_adds_uncertainty_only_when_computed(tmp_path):
    run = _load("analysis/export_web/run.py", "export_web_run4")
    assert run.uncertainty(tmp_path) is None  # no table, no file, no band
    unc = _load("analysis/export_web/uncertainty.py", "export_web_unc2")
    (tmp_path / run.UNCERTAINTY).parent.mkdir(parents=True)
    unc.table(_scores(1)).to_csv(tmp_path / run.UNCERTAINTY, index=False)
    doc = run.uncertainty(tmp_path)
    assert doc["alpha"] == 0.1 and doc["rows"] and {"air", "n_pitches", "half_width", "coverage"} <= set(doc["rows"][0])
    run.ew.assert_aggregate(doc)
