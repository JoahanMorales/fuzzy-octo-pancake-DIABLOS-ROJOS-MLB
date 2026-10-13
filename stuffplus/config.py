"""Paths and settings shared by every module.

The raw ISAC parquet is never committed. It is looked up, in order:
1. ``$STUFFPLUS_DATA`` (absolute or relative to the repo root);
2. ``<repo>/data/raw/stuff_model_df.parquet`` (the worktree or checkout you are in);
3. the same path in the main checkout (uak worktrees share it, so each agent does not need a copy).
"""
from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

RAW_FILENAME = "stuff_model_df.parquet"
RAW_RELATIVE = Path("data") / "raw" / RAW_FILENAME
SEED = 2240


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Root of the current checkout or worktree (falls back to this package's parent)."""
    here = Path(__file__).resolve().parent.parent
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True, check=True
        ).stdout.strip()
        return Path(out) if out else here
    except (OSError, subprocess.CalledProcessError):
        return here


@lru_cache(maxsize=1)
def main_checkout_root() -> Path | None:
    """Root of the main checkout when running inside a uak worktree, else None."""
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=repo_root(), capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    root = Path(common).parent
    return None if root == repo_root() else root


def data_path() -> Path:
    """Best existing location of the raw parquet (or the default path, for the error message)."""
    env = os.environ.get("STUFFPLUS_DATA")
    if env:
        p = Path(env)
        return p if p.is_absolute() else repo_root() / p
    local = repo_root() / RAW_RELATIVE
    if local.exists():
        return local
    main = main_checkout_root()
    if main is not None and (main / RAW_RELATIVE).exists():
        return main / RAW_RELATIVE
    return local


ARTIFACTS_DIR = repo_root() / "artifacts"
BUNDLE_DIR = ARTIFACTS_DIR / "bundle"
REPORTS_DIR = repo_root() / "reports"
