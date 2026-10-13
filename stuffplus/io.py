"""Loading the raw pitch-by-pitch parquet.

Only this module touches the raw file. Everything downstream goes through ``load_raw`` and then
``stuffplus.schema.clean`` (HACK-002).
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pandas as pd

from stuffplus import config

MIN_PYARROW = (20, 0)


class DataNotFoundError(FileNotFoundError):
    """The raw parquet is not where we looked."""


def _check_pyarrow() -> None:
    import pyarrow

    version = tuple(int(x) for x in pyarrow.__version__.split(".")[:2])
    if version < MIN_PYARROW:
        raise ImportError(
            f"pyarrow {pyarrow.__version__} cannot read the ISAC parquet (written by pyarrow 20; "
            "fails with 'Repetition level histogram size mismatch'). Run: pip install -r requirements.txt"
        )


def load_raw(columns: Sequence[str] | None = None, path: str | Path | None = None) -> pd.DataFrame:
    """Read the raw parquet, optionally only some columns.

    Row order is preserved: rows are in game / plate-appearance order, which sequence features rely on.
    """
    _check_pyarrow()
    p = Path(path) if path is not None else config.data_path()
    if not p.exists():
        raise DataNotFoundError(
            f"Raw data not found at {p}. Copy stuff_model_df.parquet to data/raw/ "
            "or set STUFFPLUS_DATA. Never commit it."
        )
    return pd.read_parquet(p, columns=list(columns) if columns is not None else None, engine="pyarrow")
