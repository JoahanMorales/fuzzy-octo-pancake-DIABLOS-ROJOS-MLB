"""Shared pytest fixtures. Tests never need the raw ISAC data."""
from __future__ import annotations

import pandas as pd
import pytest

from tests.fixtures.synthetic import make_synthetic_pitches, write_parquet


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
