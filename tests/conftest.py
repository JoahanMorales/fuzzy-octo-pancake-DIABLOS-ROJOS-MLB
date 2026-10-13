"""Shared pytest fixtures. Tests never need the raw ISAC data."""
from __future__ import annotations

import pandas as pd
import pytest

from tests.fixtures.synthetic import make_synthetic_pitches, write_parquet


@pytest.fixture(autouse=True)
def _isolate_from_local_artifacts(monkeypatch, tmp_path_factory):
    """Tests never see a real bundle in artifacts/ (it would switch api.predict_pitch from mock to models).

    Tests that need models train a small bundle and point STUFFPLUS_BUNDLE at it themselves.
    """
    monkeypatch.setenv("STUFFPLUS_BUNDLE", str(tmp_path_factory.getbasetemp() / "no-bundle"))
    try:
        from stuffplus import serving
    except ImportError:
        yield
        return
    serving.reset_cache()
    yield
    serving.reset_cache()


@pytest.fixture(scope="session")
def _synthetic_cache() -> pd.DataFrame:
    return make_synthetic_pitches()


@pytest.fixture
def synthetic_pitches(_synthetic_cache: pd.DataFrame) -> pd.DataFrame:
    """~5,000 simulated pitches with the exact 84 columns and dtypes of the raw parquet (fresh copy per test)."""
    return _synthetic_cache.copy()


@pytest.fixture
def synthetic_parquet(tmp_path, _synthetic_cache):
    """Path to the synthetic data written as parquet, for code that reads files."""
    path = tmp_path / "stuff_model_df.parquet"
    write_parquet(_synthetic_cache, path)
    return path
