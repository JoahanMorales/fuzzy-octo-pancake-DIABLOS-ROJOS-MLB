"""The "plus" scale: 100 = LMB average, 10 points = one standard deviation (HACK-013).

``Stuff+ = 100 + 10 · z``, ``z = sign · (xRV − μ_g) / σ_g`` where g is the reference group (by default the
season) and μ, σ come from LMB pitches scored at **sea-level air** (park-neutral). The same fitted scaler
turns predictions at any other air density into the *environment* flavour, so "96 in Harp Helú" and
"112 at sea level" are on one ruler. ``sign=-1`` because xRV is from the batter's view (lower is better).

Aggregations (pitch → pitcher, pitch type, arsenal) shrink small samples toward 100 with an empirical-Bayes
factor ``n / (n + k)``, k estimated from the data (within- vs between-group variance).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from math import erf, sqrt
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

GLOBAL = "__all__"


def _key(values: Iterable) -> str:
    return "|".join(str(v) for v in values)


@dataclass
class PlusScaler:
    by: tuple[str, ...] = ("year",)
    sign: int = -1
    center: float = 100.0
    spread: float = 10.0
    stats: dict[str, dict[str, float]] = field(default_factory=dict)

    def fit(self, df: pd.DataFrame, col: str) -> "PlusScaler":
        """Fit reference mean/sd per group on the park-neutral predictions in ``df[col]``."""
        x = df[col].astype(float)
        self.stats = {GLOBAL: {"mean": float(x.mean()), "sd": float(x.std(ddof=0)), "n": int(x.notna().sum())}}
        if self.by:
            for k, g in x.groupby([df[c] for c in self.by], observed=True):
                k = k if isinstance(k, tuple) else (k,)
                sd = float(g.std(ddof=0))
                if len(g) >= 2 and sd > 0:
                    self.stats[_key(k)] = {"mean": float(g.mean()), "sd": sd, "n": int(len(g))}
        if not self.stats[GLOBAL]["sd"] > 0:
            raise ValueError("cannot fit a scale on a constant prediction")
        return self

    def _group_stats(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        if not self.stats:
            raise RuntimeError("PlusScaler is not fitted")
        g = self.stats[GLOBAL]
        if not self.by:
            return np.full(len(df), g["mean"]), np.full(len(df), g["sd"])
        keys = df[self.by[0]].astype(str)
        for c in self.by[1:]:
            keys = keys + "|" + df[c].astype(str)
        means = {k: v["mean"] for k, v in self.stats.items()}
        sds = {k: v["sd"] for k, v in self.stats.items()}
        mean = keys.map(means).fillna(g["mean"]).to_numpy(float)
        sd = keys.map(sds).fillna(g["sd"]).to_numpy(float)
        return mean, sd

    def transform(self, df: pd.DataFrame, col: str) -> pd.Series:
        """Plus value for each row of ``df[col]`` (unseen groups use the global reference)."""
        mean, sd = self._group_stats(df)
        z = self.sign * (df[col].to_numpy(float) - mean) / sd
        return pd.Series(self.center + self.spread * z, index=df.index, name=f"{col}_plus")

    def fit_transform(self, df: pd.DataFrame, col: str) -> pd.Series:
        return self.fit(df, col).transform(df, col)

    def scale_value(self, xrv: float, group: Sequence | None = None) -> float:
        """One prediction (e.g. from the simulator) → plus, using ``group`` values in ``by`` order."""
        g = self.stats.get(_key(group), self.stats[GLOBAL]) if group is not None else self.stats[GLOBAL]
        return self.center + self.spread * self.sign * (xrv - g["mean"]) / g["sd"]

    # ---- persistence (bundle manifest "scaler" entry) ----
    def to_dict(self) -> dict:
        return {"by": list(self.by), "sign": self.sign, "center": self.center, "spread": self.spread, "stats": self.stats}

    @classmethod
    def from_dict(cls, d: dict) -> "PlusScaler":
        return cls(by=tuple(d["by"]), sign=int(d["sign"]), center=float(d["center"]),
                   spread=float(d["spread"]), stats={k: dict(v) for k, v in d["stats"].items()})

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "PlusScaler":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def plus_to_percentile(plus: float, center: float = 100.0, spread: float = 10.0) -> float:
    """Percentile (0–100) of a plus value under the normal reference: 120 → ~97.7."""
    return 50.0 * (1.0 + erf((plus - center) / spread / sqrt(2.0)))


def shrinkage_k(df: pd.DataFrame, col: str, group: Sequence[str]) -> float:
    """Empirical-Bayes prior strength k (in pitches): within-group variance / true between-group variance."""
    g = df.groupby(list(group), observed=True)[col]
    n = g.size()
    within = float((g.var(ddof=1) * (n - 1)).sum() / max((n - 1).sum(), 1))
    means = g.mean()
    tau2 = float(means.var(ddof=1) - (within / n).mean())
    if not np.isfinite(tau2) or tau2 <= 0:
        return float("inf")  # no detectable true spread: shrink everything to the center
    return within / tau2


def aggregate(
    df: pd.DataFrame,
    col: str,
    by: Sequence[str] = ("pitcher_anon_id", "year"),
    min_n: int = 1,
    k: float | None = None,
    center: float = 100.0,
) -> pd.DataFrame:
    """Group plus values with shrinkage: ``shrunk = center + (mean − center) · n / (n + k)``.

    The mean over all of a pitcher's pitches IS the usage-weighted arsenal value; pass
    ``by=("pitcher_anon_id", "year", "pitch_id")`` for per-pitch-type rows.
    """
    k = shrinkage_k(df, col, by) if k is None else k
    g = df.groupby(list(by), observed=True)[col]
    out = g.agg(n="size", raw="mean", sd="std").reset_index()
    weight = out["n"] / (out["n"] + k) if np.isfinite(k) else 0.0
    out["shrunk"] = center + (out["raw"] - center) * weight
    out["k"] = k
    out["percentile"] = out["shrunk"].map(plus_to_percentile)
    return out[out["n"] >= min_n].reset_index(drop=True)
