"""Optional roster drop-in (HACK-056): map anonymous pitcher ids to names without refitting anything.

If the finals data (or the club) provides ``pitcher_anon_id,name,team,role``, drop it at ``data/roster.csv``
(git-ignored; override with the env var ``STUFFPLUS_ROSTER``). Absent file = ``load_roster()`` returns ``None`` and
``apply_names`` falls back to the anonymous id, so every consumer works the same with or without names.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from stuffplus import config

ENV_VAR = "STUFFPLUS_ROSTER"
DEFAULT_RELATIVE = Path("data") / "roster.csv"
COLUMNS = ["pitcher_anon_id", "name", "team", "role"]
_ID_ALIASES = ("pitcher_id",)  # the plan spells the key ``pitcher_id``


def roster_path() -> Path:
    """``$STUFFPLUS_ROSTER`` (absolute, or relative to the repo root) else ``<repo>/data/roster.csv``."""
    raw = os.environ.get(ENV_VAR)
    p = Path(raw) if raw else DEFAULT_RELATIVE
    return p if p.is_absolute() else config.repo_root() / p


def load_roster(path: str | Path | None = None) -> pd.DataFrame | None:
    """The roster as a DataFrame with ``COLUMNS`` (ids as strings, one row per id), or ``None`` if there is no file."""
    p = Path(path) if path is not None else roster_path()
    if not p.is_file():
        return None
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    if "pitcher_anon_id" not in df:
        df = df.rename(columns={a: "pitcher_anon_id" for a in _ID_ALIASES if a in df})
    missing = [c for c in ("pitcher_anon_id", "name") if c not in df]
    if missing:
        raise ValueError(f"{p}: roster needs columns {COLUMNS}; missing {missing}")
    for c in COLUMNS:
        if c not in df:
            df[c] = ""
    df["pitcher_anon_id"] = df["pitcher_anon_id"].str.strip()
    return df[COLUMNS].drop_duplicates("pitcher_anon_id", keep="last").reset_index(drop=True)


def apply_names(df: pd.DataFrame, col: str = "pitcher_anon_id", roster: pd.DataFrame | None = None) -> pd.DataFrame:
    """Copy of ``df`` with a ``pitcher_name`` column: the roster name, else the anonymous id (as text).

    ``roster`` defaults to ``load_roster()``. Row order and count never change; ids missing from the roster, or
    with a blank name, keep their anonymous id so a partial roster is safe.
    """
    out = df.copy()
    ids = out[col].astype("string")
    if roster is None:
        roster = load_roster()
    if roster is None or roster.empty:
        out["pitcher_name"] = ids
        return out
    clean = roster.assign(name=roster["name"].str.strip())
    names = clean[clean["name"] != ""].set_index("pitcher_anon_id")["name"]
    out["pitcher_name"] = ids.map(names).fillna(ids)
    return out
