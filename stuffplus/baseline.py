"""Null models every Stuff+ / Location+ / Pitching+ model must beat (HACK-005).

The rubric names the null model: mean xRunValue by count. ``CountBaseline`` predicts the mean of any
target by count; ``CountBaseline(by=("count", "pitch_family"))`` is the stronger version that also knows
the broad pitch family (fastball / breaking / offspeed). Targets are fitted on their own denominator
(non-NaN rows), so ``t_whiff`` is P(whiff | swing) by count.

``python -m stuffplus.baseline`` writes ``reports/baseline/baseline_metrics.csv`` for all three splits.
"""
from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from stuffplus.config import REPORTS_DIR

FAMILY = {"Four-Seam": "FB", "Sinker": "FB", "Cutter": "FB", "Slider": "BB", "Curveball": "BB",
          "Changeup": "OS", "Splitter": "OS"}


def pitch_family(df: pd.DataFrame) -> pd.Series:
    """Broad family from AutoPitchType (fine for baselines; within-pitcher work uses pitch_id, HACK-029)."""
    return df["AutoPitchType"].astype(str).map(FAMILY).fillna("OTHER").rename("pitch_family")


class CountBaseline:
    """Mean of each target by ``by`` (default: count), global mean for unseen cells."""

    def __init__(self, by: Sequence[str] = ("count",), min_n: int = 20):
        self.by = tuple(by)
        self.min_n = min_n
        self.tables: dict[str, pd.Series] = {}
        self.globals: dict[str, float] = {}

    def _keys(self, df: pd.DataFrame) -> pd.Series:
        cols = [pitch_family(df) if c == "pitch_family" and c not in df else df[c] for c in self.by]
        key = cols[0].astype(str)
        for c in cols[1:]:
            key = key + "|" + c.astype(str)
        return key

    def fit(self, df: pd.DataFrame, targets: Iterable[str] = ("rv",)) -> "CountBaseline":
        keys = self._keys(df)
        for t in targets:
            y = df[t].astype(float)
            ok = y.notna()
            stats = y[ok].groupby(keys[ok]).agg(["mean", "size"])
            self.tables[t] = stats.loc[stats["size"] >= self.min_n, "mean"]
            self.globals[t] = float(y[ok].mean())
        return self

    def predict(self, df: pd.DataFrame, target: str = "rv") -> pd.Series:
        if target not in self.tables:
            raise KeyError(f"target {target!r} was not fitted")
        return self._keys(df).map(self.tables[target]).fillna(self.globals[target]).astype(float).rename(f"{target}_baseline")


def _split_iter(df: pd.DataFrame):
    from stuffplus import splits

    yield "pitcher_kfold", list(splits.pitcher_group_kfold(df))
    yield "season_holdout", [splits.season_holdout(df)]
    yield "park_holdout", [splits.park_holdout(df)]


def baseline_metrics(df: pd.DataFrame, targets: Sequence[str]) -> pd.DataFrame:
    """Out-of-sample metrics of both baselines (count, count × family) for every split and target."""
    from stuffplus import evaluate

    rows = []
    for split_name, folds in _split_iter(df):
        for by in (("count",), ("count", "pitch_family")):
            name = "count" if by == ("count",) else "count_x_family"
            for t in targets:
                kind = "regression" if t.startswith("rv") else "probability"

                def fit_predict(tr, te, t=t, by=by):
                    return CountBaseline(by=by).fit(tr, [t]).predict(te, t).to_numpy()

                idx = np.concatenate([te for _, te in folds])
                pred = evaluate.oof_predict(df, fit_predict, folds)[idx]
                y = df[t].to_numpy(float)[idx]
                m = evaluate.report(y, pred, kind).set_index("metric")["value"].to_dict()
                rows.append({"split": split_name, "baseline": name, "target": t, **m})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from stuffplus import targets as tg
    from stuffplus.io import load_raw
    from stuffplus.schema import clean

    frame, _, _ = tg.build(clean(load_raw()))
    out = REPORTS_DIR / "baseline"
    out.mkdir(parents=True, exist_ok=True)
    table = baseline_metrics(frame, ["rv"] + list(tg.TARGETS))
    table.round(5).to_csv(out / "baseline_metrics.csv", index=False)
    print(table[table.target.isin(["rv", "t_whiff"])].round(4).to_string(index=False))
