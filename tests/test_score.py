"""HACK-016: out-of-fold per-pitch scores and aggregated leaderboards."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from stuffplus import schema, score

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def scored(_synthetic_cache):
    spec = importlib.util.spec_from_file_location("alt_run", ROOT / "analysis" / "altitude_delta" / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)
    shape_model, d = run.prepare(schema.clean(_synthetic_cache.copy()))
    return d, score.score_pitches(d, shape_model, fast=True)


def test_per_pitch_scores(scored):
    d, s = scored
    assert len(s) == len(d) and s.PitchUID.is_unique
    for c in score.SCORE_COLS:
        assert s[c].notna().all(), c
    by_year = s.groupby("year")["stuff_plus"].mean()
    assert np.allclose(by_year, 100, atol=1e-6)  # park-neutral Stuff+ is the 100 reference
    assert s["stuff_plus_harp_helu"].mean() != pytest.approx(100, abs=1e-3)  # same ruler, different air


def test_leaderboards(scored):
    _, s = scored
    games = s["game_anon_id"].drop_duplicates()
    parks = pd.DataFrame({"game_anon_id": games, "park_id": np.arange(len(games)) % 3})
    tabs = score.leaderboards(s, parks, min_pitcher=20, min_pitch=5)
    assert {"pitcher_season", "pitcher_pitch", "best_arsenals_harp_helu", "arsenal_archetypes", "by_altitude",
            "by_park"} <= set(tabs)
    ps = tabs["pitcher_season"]
    assert (ps.pitches >= 20).all() and ps.arsenal.str.contains("%").all()
    pp = tabs["pitcher_pitch"]
    assert np.allclose(pp.groupby(["pitcher_anon_id", "year"]).usage.sum().clip(upper=1), pp.groupby(
        ["pitcher_anon_id", "year"]).usage.sum(), atol=1e-9)
    best = tabs["best_arsenals_harp_helu"]
    assert best.stuff_plus_harp_helu.is_monotonic_decreasing
    for name, t in tabs.items():
        assert "PitchUID" not in t.columns, name


def test_shrinkage_pulls_small_samples(scored):
    _, s = scored
    ps = score.leaderboards(s, min_pitcher=1, min_pitch=1)["pitcher_season"]
    raw = s.groupby(["pitcher_anon_id", "year"])["stuff_plus"].mean()
    shrunk = ps.set_index(["pitcher_anon_id", "year"])["stuff_plus"]
    assert ((shrunk - 100).abs() <= (raw.reindex(shrunk.index) - 100).abs() + 1e-9).all()
