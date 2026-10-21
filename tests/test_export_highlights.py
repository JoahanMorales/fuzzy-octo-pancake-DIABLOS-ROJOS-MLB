"""HACK-087: los highlights de validation.json salen del modelo de producción (delta_by_shape.csv)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from stuffplus import export_web

ROOT = Path(__file__).resolve().parents[1]
SHAPES = ROOT / "reports" / "altitude_delta" / "delta_by_shape.csv"
REAL = ROOT / "web" / "public" / "data" / "real" / "validation.json"


@pytest.fixture(scope="module")
def highlights() -> dict:
    return export_web.build_mock(ROOT)["validation.json"]["highlights"]


def test_league_delta_is_the_production_league_mean(highlights):
    shapes = pd.read_csv(SHAPES)
    league = (shapes["delta_stuff"] - shapes["relative_to_league"]).mean()
    assert highlights["league_delta_cdmx"] == pytest.approx(league, abs=1e-4)
    assert round(highlights["league_delta_cdmx"], 1) == -13.0
    assert highlights["source_model"] == export_web.PRODUCTION_MODEL
    assert "familia" not in highlights["source_model"]


def test_best_and_worst_shapes_come_from_delta_by_shape(highlights):
    shapes = pd.read_csv(SHAPES)
    best = shapes.loc[shapes["delta_stuff"].idxmax()]
    worst = shapes.loc[shapes["delta_stuff"].idxmin()]
    assert (highlights["best_shape"], highlights["best_delta"]) == (best["shape"], pytest.approx(best["delta_stuff"]))
    assert (highlights["worst_shape"], highlights["worst_delta"]) == (worst["shape"], pytest.approx(worst["delta_stuff"]))
    assert highlights["best_delta"] > highlights["league_delta_cdmx"] > highlights["worst_delta"]


def test_validation_lists_delta_by_shape_as_source():
    doc = export_web.build_mock(ROOT)["validation.json"]
    assert "reports/altitude_delta/delta_by_shape.csv" in doc["sources"]


def test_committed_real_validation_matches_the_export(highlights):
    real = json.loads(REAL.read_text(encoding="utf-8"))
    for key, value in highlights.items():
        if isinstance(value, float):
            assert real["highlights"][key] == pytest.approx(value, abs=1e-4), key
        else:
            assert real["highlights"][key] == value, key
