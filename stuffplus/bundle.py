"""Artifact bundle: the only thing the dashboard and the deploy need (format in docs/CONTRACT.md §7).

``artifacts/bundle/`` = ``manifest.json`` + ``models/<name>.txt`` (LightGBM) + ``tables/<name>.csv`` (aggregates).
The bundle is git-ignored; it is rebuilt by ``analysis/v0/run.py`` (and later model tasks).

Location lookup (first hit wins): ``$STUFFPLUS_BUNDLE`` → ``<repo>/artifacts/bundle`` → the main checkout's
``artifacts/bundle`` (uak worktrees share it).
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import lightgbm as lgb
import pandas as pd

from stuffplus import config
from stuffplus.scale import PlusScaler

MANIFEST = "manifest.json"


def bundle_dir() -> Path:
    env = os.environ.get("STUFFPLUS_BUNDLE")
    if env:
        return Path(env)
    if (config.BUNDLE_DIR / MANIFEST).exists():
        return config.BUNDLE_DIR
    main = config.main_checkout_root()
    if main is not None and (main / "artifacts" / "bundle" / MANIFEST).exists():
        return main / "artifacts" / "bundle"
    return config.BUNDLE_DIR


@dataclass
class Bundle:
    path: Path
    manifest: dict[str, Any]
    models: dict[str, lgb.Booster] = field(default_factory=dict)
    scalers: dict[str, PlusScaler] = field(default_factory=dict)

    @property
    def version(self) -> str:
        return str(self.manifest.get("version", "unknown"))

    def features(self, model: str) -> list[str]:
        return list(self.manifest["models"][model]["features"])

    def table(self, name: str) -> pd.DataFrame:
        return pd.read_csv(self.path / "tables" / f"{name}.csv")


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=config.repo_root(),
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def save_bundle(
    out_dir: str | Path,
    models: Mapping[str, tuple[lgb.Booster, Mapping[str, Any]]],
    scalers: Mapping[str, PlusScaler],
    rho: Mapping[str, float],
    metrics: Mapping[str, Any] | None = None,
    tables: Mapping[str, pd.DataFrame] | None = None,
    version: str = "v0",
    extra: Mapping[str, Any] | None = None,
) -> Path:
    """Write a bundle. ``models``: name → (booster, {"features", "target", "objective", ...})."""
    out = Path(out_dir)
    (out / "models").mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    entries = {}
    for name, (booster, meta) in models.items():
        f = f"models/{name}.txt"
        booster.save_model(str(out / f))
        entries[name] = {"file": f, **dict(meta)}
    for name, t in (tables or {}).items():
        if "PitchUID" in t.columns or len(t) > 50_000:
            raise ValueError(f"table {name!r} looks pitch-level; bundles carry aggregates only")
        t.to_csv(out / "tables" / f"{name}.csv", index=False)
    manifest = {
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(),
        "models": entries,
        "rho": dict(rho),
        "scalers": {k: s.to_dict() for k, s in scalers.items()},
        "metrics": dict(metrics or {}),
        **dict(extra or {}),
    }
    if "stuff" in scalers:
        manifest["scaler"] = scalers["stuff"].to_dict()  # contract §7 name
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2, default=float), encoding="utf-8")
    return out


def load_bundle(path: str | Path | None = None) -> Bundle:
    p = Path(path) if path is not None else bundle_dir()
    manifest = json.loads((p / MANIFEST).read_text(encoding="utf-8"))
    models = {name: lgb.Booster(model_file=str(p / m["file"])) for name, m in manifest["models"].items()}
    scalers = {k: PlusScaler.from_dict(v) for k, v in manifest.get("scalers", {}).items()}
    return Bundle(path=p, manifest=manifest, models=models, scalers=scalers)
