"""HACK-024: raw-data leak check and the committed deploy bundle."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_no_raw_data", ROOT / "scripts" / "check_no_raw_data.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def _csv(path: Path, n: int, cols: list[str]) -> Path:
    pd.DataFrame({c: range(n) for c in cols}).to_csv(path, index=False)
    return path


def test_binary_data_files_are_rejected(tmp_path):
    for ext in (".parquet", ".pkl", ".rds", ".feather"):
        (tmp_path / f"x{ext}").write_bytes(b"0")
    bad = check.violations(sorted(tmp_path.iterdir()))
    assert len(bad) == 4 and all("binary data file" in b for b in bad)


def test_pitch_level_tables_over_1000_rows_are_rejected(tmp_path):
    ids = _csv(tmp_path / "ids.csv", 1001, ["PitchUID", "stuff_plus"])
    raw = _csv(tmp_path / "raw.csv", 1500, ["RelSpeed", "SpinRate", "PlateLocSide", "pitcher_anon_id"])
    bad = check.violations([ids, raw])
    assert len(bad) == 2 and "pitch id" in bad[0] and "raw per-pitch columns" in bad[1]


def test_small_or_aggregated_tables_pass(tmp_path):
    small = _csv(tmp_path / "small.csv", 1000, ["PitchUID", "RelSpeed", "SpinRate", "PlateLocSide"])  # at the limit
    agg = _csv(tmp_path / "agg.csv", 5000, ["pitcher_anon_id", "year", "pitches", "velo", "ivb", "stuff_plus"])
    two_raw = _csv(tmp_path / "two.csv", 5000, ["pitcher_anon_id", "RelSpeed", "SpinRate"])
    assert check.violations([small, agg, two_raw]) == []


def test_tsv_tables_are_parsed(tmp_path):
    p = tmp_path / "t.tsv"
    pd.DataFrame({"PitchUID": range(1200), "x": 1}).to_csv(p, sep="\t", index=False)
    assert len(check.violations([p])) == 1


def test_bundle_size_limit_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "bundle_mb", lambda bundles: 150.0)
    monkeypatch.setattr(check, "tracked", lambda root=check.ROOT: [])
    monkeypatch.setattr(check, "bundle_files", lambda bundles: [])
    assert check.main(["--bundle", "deploy/bundle", "--max-mb", "100"]) == 1


def test_repository_and_deploy_bundle_pass():
    assert check.main([]) == 0


def test_deploy_bundle_is_text_models_and_aggregates(monkeypatch):
    bundle = ROOT / "deploy" / "bundle"
    if not (bundle / "manifest.json").exists():
        pytest.skip("deploy bundle not built (python deploy/build_bundle.py)")
    files = [p for p in bundle.rglob("*") if p.is_file()]
    assert {p.suffix for p in files} <= {".txt", ".csv", ".json"}
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    for m in manifest["models"].values():
        assert (bundle / m["file"]).exists()
    assert check.bundle_mb(["deploy/bundle"]) <= 100
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(bundle))
    from stuffplus import bundle as bundle_mod

    assert bundle_mod.bundle_dir() == bundle
