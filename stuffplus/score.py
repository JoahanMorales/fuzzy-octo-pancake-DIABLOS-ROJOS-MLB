"""Scoring pipeline and leaderboards: Stuff+ (sea level / Harp Helú / own air), Location+, Pitching+ (HACK-016).

Every pitch is scored OUT OF FOLD (folds grouped by pitcher): the model that scores a pitcher never saw him, so the
leaderboards cannot reward memorization. Models: Stuff+ = component model with the altitude-invariant pitch family
and fitted physics (HACK-015); Location+ = HACK-011; Pitching+ = HACK-012 combined xRV with league-average batters.

    python -m stuffplus.score          # real data (~40 min)
    python -m stuffplus.score --fast

Outputs: ``artifacts/scores/pitch_scores.parquet`` (git-ignored, per-pitch deliverable sent by email, never
committed) and aggregated CSVs in ``reports/leaderboards/``.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus import config, splits
from stuffplus.scale import PlusScaler, aggregate, plus_to_percentile

LEADERBOARDS = config.REPORTS_DIR / "leaderboards"
SCORES = config.ARTIFACTS_DIR / "scores"
MIN_PITCHER = 300  # pitcher-season rows in the leaderboards
MIN_PITCH = 50  # pitcher × pitch rows
SCORE_COLS = ["stuff_plus", "stuff_plus_harp_helu", "stuff_plus_own_air", "location_plus", "pitching_plus"]


def _load(rel: str):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_"), config.repo_root() / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plus(df: pd.DataFrame, xrv: np.ndarray, ref: np.ndarray | None = None) -> np.ndarray:
    """Plus scale per season; ``ref`` (default ``xrv``) defines the 100/σ reference."""
    sc = PlusScaler().fit(df.assign(x=xrv if ref is None else ref), "x")
    return sc.transform(df.assign(x=xrv), "x").to_numpy()


def score_pitches(d: pd.DataFrame, shape_model, fast: bool = False) -> pd.DataFrame:
    """Per-pitch OOF scores. ``d`` = output of ``analysis/altitude_delta/run.py: prepare`` (has shape and pitch_family)."""
    from stuffplus.altitude import STUFF_FEATURES_INVARIANT, physics_translator
    from stuffplus.models.location import LocationModel
    from stuffplus.models.pitching import build_features, combine, run_oof
    from stuffplus.models.stuff import StuffModel
    from stuffplus.physics.constants import RHO_HARP_HELU

    folds = list(splits.pitcher_group_kfold(d))
    rounds = dict(class_rounds=40, contact_rounds=30) if fast else {}
    translate = physics_translator(shape_model)
    neutral, hh, own = (np.full(len(d), np.nan) for _ in range(3))
    for tr, te in folds:
        m = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=translate, **rounds).fit(d.iloc[tr])
        te_df = d.iloc[te]
        own[te] = m.predict_xrv(te_df)
        neutral[te] = m.predict_at_rho(te_df, 1.0)["xrv"].to_numpy()
        hh[te] = m.predict_at_rho(te_df, RHO_HARP_HELU)["xrv"].to_numpy()
    loc = LocationModel(**rounds).oof(d, folds)["loc_value"].to_numpy(float)
    pf = build_features(d)
    pit_rounds = dict(class_rounds=40, contact_rounds=30, target_rounds=40) if fast else {}
    oof = run_oof(pf, folds, **pit_rounds)
    pit = combine(oof, pf["rv_x"].to_numpy(), folds)["combined_neutral"]

    keep = ["PitchUID", "pitcher_anon_id", "year", "game_anon_id", "pitch_id", "pitch_key", "pitch_family", "shape",
            "PitcherThrows", "altitude_category", "rho", "RelSpeed", "InducedVertBreak", "HorzBreak", "SpinRate"]
    out = d[[c for c in keep if c in d]].copy()
    out["stuff_plus"] = _plus(d, neutral)  # park-neutral (sea level), the headline Stuff+
    out["stuff_plus_harp_helu"] = _plus(d, hh, ref=neutral)  # same ruler, Harp Helú air
    out["stuff_plus_own_air"] = _plus(d, own, ref=neutral)  # the air the pitch was actually thrown in
    out["location_plus"] = _plus(d, loc)
    out["pitching_plus"] = _plus(d, np.asarray(pit, float))
    out["delta_cdmx"] = out["stuff_plus_harp_helu"] - out["stuff_plus"]
    return out


def _signature(g: pd.DataFrame, top: int = 3) -> str:
    use = g["shape"].astype(str).value_counts(normalize=True).head(top)
    return " · ".join(f"{s} {u:.0%}" for s, u in use.items())


def leaderboards(scores: pd.DataFrame, parks: pd.DataFrame | None = None, min_pitcher: int = MIN_PITCHER,
                 min_pitch: int = MIN_PITCH) -> dict[str, pd.DataFrame]:
    """Aggregated tables (anonymized ids, shrunk toward 100). The pitcher-season mean is the usage-weighted arsenal."""
    key = ["pitcher_anon_id", "year"]
    tabs = {}
    base = scores.groupby(key).agg(pitches=("stuff_plus", "size"), throws=("PitcherThrows", "first"))
    for col in SCORE_COLS:
        a = aggregate(scores, col, by=key)
        base[col] = a.set_index(key)["shrunk"].reindex(base.index)
    base["delta_cdmx"] = base["stuff_plus_harp_helu"] - base["stuff_plus"]
    base["arsenal"] = scores.groupby(key).apply(_signature, include_groups=False)
    base["stuff_plus_percentile"] = base["stuff_plus"].map(plus_to_percentile)
    tabs["pitcher_season"] = (base[base.pitches >= min_pitcher].reset_index()
                              .sort_values("pitching_plus", ascending=False))

    pkey = key + ["pitch_id"]
    pp = scores.groupby(pkey).agg(pitch_family=("pitch_family", "first"), shape=("shape", "first"),
                                  pitches=("stuff_plus", "size"), velo=("RelSpeed", "mean"),
                                  ivb=("InducedVertBreak", "mean"), hb=("HorzBreak", "mean"), spin=("SpinRate", "mean"))
    pp["usage"] = pp["pitches"] / pp.groupby(level=key)["pitches"].transform("sum")
    for col in SCORE_COLS:
        a = aggregate(scores, col, by=pkey)
        pp[col] = a.set_index(pkey)["shrunk"].reindex(pp.index)
    pp["delta_cdmx"] = pp["stuff_plus_harp_helu"] - pp["stuff_plus"]
    tabs["pitcher_pitch"] = pp[pp.pitches >= min_pitch].reset_index().sort_values("stuff_plus", ascending=False)

    ps = tabs["pitcher_season"]
    tabs["best_arsenals_harp_helu"] = ps.sort_values("stuff_plus_harp_helu", ascending=False).head(25)[
        ["pitcher_anon_id", "year", "throws", "pitches", "arsenal", "stuff_plus", "stuff_plus_harp_helu", "delta_cdmx",
         "location_plus", "pitching_plus"]]
    # arsenal archetypes: the set of a pitcher's top-2 shapes, averaged across pitcher-seasons
    top2 = (scores.groupby(key + ["shape"]).size().rename("n").reset_index()
            .sort_values("n", ascending=False).groupby(key).head(2)
            .groupby(key)["shape"].apply(lambda s: " + ".join(sorted(s.astype(str)))).rename("archetype"))
    arch = ps.join(top2, on=key).groupby("archetype").agg(
        pitcher_seasons=("pitcher_anon_id", "size"), stuff_plus=("stuff_plus", "mean"),
        stuff_plus_harp_helu=("stuff_plus_harp_helu", "mean"), delta_cdmx=("delta_cdmx", "mean"),
        pitching_plus=("pitching_plus", "mean")).reset_index()
    tabs["arsenal_archetypes"] = arch[arch.pitcher_seasons >= 5].sort_values("stuff_plus_harp_helu", ascending=False)

    by_alt = scores.groupby(scores["altitude_category"].astype(str)).agg(
        pitches=("stuff_plus", "size"), rho=("rho", "median"), stuff_plus_neutral=("stuff_plus", "mean"),
        stuff_plus_own_air=("stuff_plus_own_air", "mean"), pitching_plus=("pitching_plus", "mean")).reset_index()
    tabs["by_altitude"] = by_alt
    if parks is not None and "park_id" in parks:
        s = scores.join(parks.set_index("game_anon_id")[["park_id"]], on="game_anon_id")
        tabs["by_park"] = (s.dropna(subset=["park_id"]).groupby("park_id").agg(
            games=("game_anon_id", "nunique"), pitches=("stuff_plus", "size"), rho=("rho", "median"),
            altitude=("altitude_category", lambda x: x.astype(str).mode().iat[0]),
            stuff_plus_neutral=("stuff_plus", "mean"), stuff_plus_own_air=("stuff_plus_own_air", "mean"))
            .reset_index().sort_values("rho"))
        tabs["by_park"]["air_effect"] = tabs["by_park"]["stuff_plus_own_air"] - tabs["by_park"]["stuff_plus_neutral"]
    return tabs


def _park_table(raw_clean: pd.DataFrame) -> pd.DataFrame | None:
    """game → home franchise from HACK-003 (``physics.parks.load_maps``); None if it cannot be built."""
    try:
        from stuffplus.physics.parks import load_maps

        maps = load_maps(raw_clean)
    except Exception:  # noqa: BLE001 - park ids are optional context for one table
        return None
    pm = maps.get("park_map")
    if pm is None:
        return None
    col = "franchise" if "franchise" in pm else ("home_team" if "home_team" in pm else None)
    return None if col is None else pm.rename(columns={col: "park_id"})[["game_anon_id", "park_id"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    from stuffplus import schema
    from stuffplus.io import load_raw

    clean = schema.clean(load_raw())
    shape_model, d = _load("analysis/altitude_delta/run.py").prepare(clean)
    scores = score_pitches(d, shape_model, fast=args.fast)
    SCORES.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(SCORES / "pitch_scores.parquet", index=False)
    tabs = leaderboards(scores, _park_table(clean))
    LEADERBOARDS.mkdir(parents=True, exist_ok=True)
    for name, t in tabs.items():
        t.round(3).to_csv(LEADERBOARDS / f"{name}.csv", index=False)
    print(tabs["pitcher_season"].head(10).round(1).to_string(index=False))
    print(tabs["arsenal_archetypes"].head(12).round(1).to_string(index=False))
    print(tabs.get("by_park", tabs["by_altitude"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
