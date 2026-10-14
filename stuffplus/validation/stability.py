"""Aggregate stability of pitcher-held-out predictions, with sample-size gates.

Correlations of OOF scores are exploratory; each pitcher's seasons are scored by
the same pitcher-held-out fold model. Training may still include future seasons
of other pitchers, so this is not a prospective forecasting experiment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _correlation(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return np.nan, len(a)
    return float(np.corrcoef(a, b)[0, 1]), len(a)


def stability_table(frame, prediction, model, *, min_n=150, sample_sizes=(50, 100, 200, 400)):
    if min_n < 1 or any(n < 1 for n in sample_sizes):
        raise ValueError("stability sample sizes must be positive")
    d = frame.assign(_pred=np.asarray(prediction, float)).copy()
    d = d[np.isfinite(d._pred) & np.isfinite(d.rv)].copy()
    rows = []

    def add(check, source, a, b, pitches=0):
        r, pairs = _correlation(a, b)
        rows.append(dict(model=model, check=check, source=source, pitches=pitches,
                         pairs=pairs, correlation=r, status="evaluated" if np.isfinite(r) else "insufficient"))

    # Rank games within each pitcher-season, retaining the input chronology.
    games = d[["pitcher_anon_id", "year", "game_anon_id"]].drop_duplicates().copy()
    games["_half"] = games.groupby(["pitcher_anon_id", "year"]).cumcount() % 2
    d = d.merge(games, on=["pitcher_anon_id", "year", "game_anon_id"], how="left", validate="many_to_one")
    halves = d.groupby(["pitcher_anon_id", "year", "_half"]).agg(
        pred=("_pred", "mean"), obs=("rv", "mean"), n=("rv", "size")).reset_index()
    a, b = [halves[(halves._half == h) & (halves.n >= min_n)] for h in (0, 1)]
    paired = a.merge(b, on=["pitcher_anon_id", "year"], suffixes=("_a", "_b"))
    for source in ("pred", "obs"):
        add("split_half_games", source, paired[f"{source}_a"], paired[f"{source}_b"])
    season = d.groupby(["pitcher_anon_id", "year"]).agg(
        pred=("_pred", "mean"), obs=("rv", "mean"), n=("rv", "size")).reset_index()
    season = season[season.n >= min_n]
    for yr in (2024, 2025):
        pair = season[season.year == yr].merge(season[season.year == yr + 1], on="pitcher_anon_id", suffixes=("_a", "_b"))
        add(f"year_stability_{yr}_{yr+1}", "pred", pair.pred_a, pair.pred_b)
        for source in ("pred", "obs"):
            add(f"next_season_rv_{yr}_{yr+1}", source, pair[f"{source}_a"], pair.obs_b)
        if "t_whiff" in d:
            whiff = d.groupby(["pitcher_anon_id", "year"]).t_whiff.agg(["mean", "count"]).reset_index()
            whiff = whiff[whiff["count"] >= min_n]
            wp = whiff[whiff.year == yr].merge(whiff[whiff.year == yr + 1], on="pitcher_anon_id", suffixes=("_a", "_b"))
            rp = wp.merge(season[season.year == yr + 1][["pitcher_anon_id", "obs"]], on="pitcher_anon_id")
            add(f"next_season_rv_{yr}_{yr+1}", "raw_whiff", rp.mean_a, rp.obs)
    # First N vs a disjoint next N; no reusing first N in the reference mean.
    for n in sample_sizes:
        chunks = []
        for _, g in d.groupby(["pitcher_anon_id", "year"], sort=False):
            if len(g) >= 2 * n:
                chunks.append((g._pred.iloc[:n].mean(), g._pred.iloc[n:2*n].mean(),
                               g.rv.iloc[:n].mean(), g.rv.iloc[n:2*n].mean()))
        values = np.asarray(chunks, float).reshape(-1, 4)
        add("sample_stability", "pred", values[:, 0], values[:, 1], n)
        add("sample_stability", "obs", values[:, 2], values[:, 3], n)
    return pd.DataFrame(rows)
