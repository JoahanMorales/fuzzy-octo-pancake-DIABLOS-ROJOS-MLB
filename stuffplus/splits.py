"""Shared validation splits. Every model and report uses these, so all numbers are comparable.

All functions return POSITIONAL indices (use ``df.iloc[idx]``) and are deterministic for a given seed.

* ``pitcher_group_kfold``: the main CV. A pitcher is never in train and test at once (no memorizing arms).
* ``season_holdout``: train on 2024–2025, test on 2026.
* ``park_holdout``: train at No + Medium altitude, test at Extreme altitude (the altitude extrapolation test).
"""
from __future__ import annotations

from typing import Iterator, Sequence

import numpy as np
import pandas as pd

from stuffplus.config import SEED

Split = tuple[np.ndarray, np.ndarray]


def pitcher_folds(df: pd.DataFrame, k: int = 5, seed: int = SEED, group_col: str = "pitcher_anon_id") -> pd.Series:
    """Fold number (0..k-1) per row; pitchers are assigned greedily so folds have similar pitch counts."""
    if k < 2:
        raise ValueError("k must be >= 2")
    groups = df[group_col].astype(object).fillna("__missing__").astype(str)
    sizes = groups.value_counts(sort=False)
    rng = np.random.default_rng(seed)
    order = sizes.index.to_numpy()[rng.permutation(len(sizes))]
    order = sorted(order, key=lambda g: -sizes[g])  # stable: ties keep the random order
    totals = np.zeros(k, dtype=np.int64)
    fold_of: dict[str, int] = {}
    for g in order:
        f = int(np.argmin(totals))
        fold_of[g] = f
        totals[f] += sizes[g]
    return groups.map(fold_of).astype(int).rename("fold")


def pitcher_group_kfold(df: pd.DataFrame, k: int = 5, seed: int = SEED) -> Iterator[Split]:
    """Yield ``(train_idx, test_idx)`` for each of ``k`` pitcher-grouped folds."""
    folds = pitcher_folds(df, k=k, seed=seed).to_numpy()
    for f in range(k):
        yield np.flatnonzero(folds != f), np.flatnonzero(folds == f)


def season_holdout(df: pd.DataFrame, train: Sequence[int] = (2024, 2025), test: Sequence[int] = (2026,)) -> Split:
    year = df["year"].to_numpy()
    return np.flatnonzero(np.isin(year, train)), np.flatnonzero(np.isin(year, test))


def park_holdout(
    df: pd.DataFrame,
    train: Sequence[str] = ("No Altitude", "Medium Altitude"),
    test: Sequence[str] = ("Extreme Altitude",),
    col: str = "altitude_category",
) -> Split:
    """Altitude-bucket holdout. Pass ``col='park_id'`` and park ids for leave-one-park-out (HACK-003)."""
    values = df[col].astype(str).to_numpy()
    return np.flatnonzero(np.isin(values, list(train))), np.flatnonzero(np.isin(values, list(test)))


SPLITS = {
    "pitcher_kfold": "5-fold, grouped by pitcher_anon_id, seed 2240",
    "season_holdout": "train 2024-2025 → test 2026",
    "park_holdout": "train No + Medium altitude → test Extreme altitude",
}
