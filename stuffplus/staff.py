"""Diablos staff audit (HACK-032): home vs road, which pitch to cut at home, rotation and bullpen.

Inputs are the OOF per-pitch scores (HACK-016), the inferred team/park maps (HACK-003) and four raw columns.
The Harp Helú staff is INFERRED: the two lowest-density franchises (HACK-003 cannot separate CDMX from Puebla,
P = 0.83), so every table is per franchise and never pooled. Recommendations use the model's Stuff+ in Harp Helú
air (all of a pitcher's pitches); observed home/road splits are thin and only shown as a check.
Outputs are aggregates (franchise × pitcher [× pitch]); no pitch-level row leaves this module.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus.scale import aggregate

KEY = ["franchise", "pitcher_anon_id"]
HALF = "Top/Bottom"
RAW_COLS = ["PitchUID", "Inning", HALF, "BatterSide"]


def staff_franchises(rho: pd.DataFrame, n: int = 2) -> list[int]:
    """The ``n`` franchises with the lowest home air density (``reports/park_id/franchise_rho.csv``)."""
    return [int(f) for f in rho.sort_values("rho_mean").franchise.head(n)]


def load_rates(reports: Path) -> dict[str, float]:
    """Runs per point per pitch (HACK-035, direct OOF, target rv_x) and runs per win (league and Extreme)."""
    pp = pd.read_csv(reports / "business_value" / "runs_per_point_direct.csv")
    pp = pp[pp.objetivo == "rv_x"].set_index("escala").carreras_por_punto_lanzamiento
    rpw = pd.read_csv(reports / "business_value" / "runs_per_win.csv").set_index("entorno").carreras_por_victoria
    return {"stuff": float(pp["Stuff+"]), "pitching": float(pp["Pitching+"]),
            "rpw_league": float(rpw["liga"]), "rpw_extreme": float(rpw["Extreme Altitude"])}


def pitch_context(scores: pd.DataFrame, raw: pd.DataFrame, team_map: pd.DataFrame,
                  park_map: pd.DataFrame) -> pd.DataFrame:
    """Per-pitch frame (in memory only) with the pitcher's franchise, home flag, start flag and batter side.

    Home = the pitcher's inferred team is the game's home team. Pitches whose inferred team is not in the game
    are dropped (team inference error). ``home_half`` is checked from the data, not assumed.
    """
    pit = (team_map[team_map.role == "pitcher"][["pitcher_anon_id", "season", "team_id", "franchise"]]
           .rename(columns={"season": "year"}))
    d = (scores.merge(raw[RAW_COLS], on="PitchUID", how="inner")
         .merge(pit, on=["pitcher_anon_id", "year"], how="inner")
         .merge(park_map[["game_anon_id", "home_team", "away_team"]], on="game_anon_id", how="inner"))
    d = d[(d.team_id == d.home_team) | (d.team_id == d.away_team)].copy()
    d["is_home"] = d.team_id == d.home_team
    share = d.groupby(HALF, observed=True).is_home.mean()
    if share.max() < 0.9:
        raise ValueError(f"no half-inning is clearly fielded by the home team: {share.to_dict()}")
    # starter = the pitcher with most first-inning pitches for his side of the game
    first = (d[d.Inning == 1].groupby(["game_anon_id", "team_id", "pitcher_anon_id"], observed=True).size()
             .rename("n").reset_index().sort_values("n").groupby(["game_anon_id", "team_id"]).tail(1))
    first["is_start"] = True
    d = d.merge(first[["game_anon_id", "pitcher_anon_id", "is_start"]], on=["game_anon_id", "pitcher_anon_id"],
                how="left")
    d["is_start"] = d.is_start.fillna(False).astype(bool)
    d["franchise"] = d.franchise.astype(int)
    return d


def _shrunk(d: pd.DataFrame, col: str, by: list[str]) -> pd.Series:
    """Empirical-Bayes mean toward the league mean of ``col`` (k fitted on every group in ``d``)."""
    return aggregate(d, col, by=by, center=float(d[col].mean())).set_index(by)["shrunk"]


def pitcher_table(d: pd.DataFrame, franchises, min_pitches: int = 200, min_starts: int = 5) -> pd.DataFrame:
    """Franchise × pitcher (seasons pooled while on that franchise). Shrinkage k is fitted on the whole league."""
    g = d.groupby(KEY, observed=True)
    games = d.drop_duplicates(KEY + ["game_anon_id"])
    t = pd.DataFrame({
        "seasons": g.year.agg(lambda s: "-".join(str(y) for y in sorted(s.unique()))),
        "throws": g.PitcherThrows.first(), "pitches": g.size(), "home_pitches": g.is_home.sum(),
        "games": games.groupby(KEY).size(), "starts": games.groupby(KEY).is_start.sum(),
        "home_starts": games[games.is_home].groupby(KEY).is_start.sum()}).fillna({"home_starts": 0})
    t["road_pitches"] = t.pitches - t.home_pitches
    t["role"] = np.where((t.starts >= min_starts) & (t.starts >= 0.5 * t.games), "abridor", "relevista")
    for col in ("stuff_plus", "stuff_plus_harp_helu", "pitching_plus", "location_plus"):
        t[col] = _shrunk(d, col, KEY)
    t["delta_cdmx"] = t.stuff_plus_harp_helu - t.stuff_plus
    league_delta = float(d.delta_cdmx.mean())
    t["altitude_resilience"] = t.delta_cdmx - league_delta  # + = loses less than the league in Harp Helú air
    for flag, name in ((True, "home"), (False, "road")):  # observed check: raw means, thin at home
        s = d[d.is_home == flag].groupby(KEY)
        t[f"own_air_{name}"] = s.stuff_plus_own_air.mean()
        t[f"neutral_{name}"] = s.stuff_plus.mean()
    t["own_air_home_minus_road"] = t.own_air_home - t.own_air_road
    t["neutral_home_minus_road"] = t.neutral_home - t.neutral_road  # ≈ 0 if the physics translation is right
    t = t.reset_index()
    return t[t.franchise.isin(list(franchises)) & (t.pitches >= min_pitches)].reset_index(drop=True)


def pitch_plan(d: pd.DataFrame, franchises, min_pitches: int = 50, min_usage: float = 0.05,
               min_gap: float = 5.0) -> pd.DataFrame:
    """Franchise × pitcher × pitch_id with the home recommendation.

    Lean on = highest Stuff+ in Harp Helú air among eligible pitches (≥ ``min_pitches`` and ≥ ``min_usage``);
    reduce at home = the lowest; flagged only with ≥ 2 eligible pitches and a gap ≥ ``min_gap`` Stuff+ points
    (≈ 1 sd between pitcher-seasons, HACK-035). Ties break on ΔCDMX. A pitch that loses
    the most to altitude can still be the best one in CDMX air: the level decides, not the delta.
    """
    key = KEY + ["pitch_id"]
    g = d.groupby(key, observed=True)
    p = pd.DataFrame({"pitch_family": g.pitch_family.first(), "shape": g["shape"].first(), "pitches": g.size(),
                      "home_pitches": g.is_home.sum(), "velo": g.RelSpeed.mean(), "ivb": g.InducedVertBreak.mean(),
                      "hb": g.HorzBreak.mean()})
    for col in ("stuff_plus", "stuff_plus_harp_helu"):
        p[col] = _shrunk(d, col, key)
    p = p.reset_index()
    p = p[p.franchise.isin(list(franchises))].copy()
    tot = p.groupby(KEY).pitches.transform("sum")
    home_tot = p.groupby(KEY).home_pitches.transform("sum")
    p["usage"] = p.pitches / tot
    p["usage_home"] = (p.home_pitches / home_tot.replace(0, np.nan)).fillna(0.0)
    p["delta_cdmx"] = p.stuff_plus_harp_helu - p.stuff_plus
    p["eligible"] = (p.pitches >= min_pitches) & (p.usage >= min_usage)
    p["recommendation"] = ""
    el = p[p.eligible].sort_values(["stuff_plus_harp_helu", "delta_cdmx"])
    n_el = el.groupby(KEY).pitch_id.transform("size")
    el = el[n_el >= 2]
    gap = el.groupby(KEY).stuff_plus_harp_helu.transform("max") - el.groupby(KEY).stuff_plus_harp_helu.transform("min")
    el = el[gap >= min_gap]
    p.loc[el.groupby(KEY).tail(1).index, "recommendation"] = "apoyarse en casa"
    p.loc[el.groupby(KEY).head(1).index, "recommendation"] = "reducir en casa"
    return p.sort_values(KEY + ["usage"], ascending=[True, True, False]).reset_index(drop=True)


def mix_runs(plan: pd.DataFrame, pitchers: pd.DataFrame, rates: dict, shift: float = 0.10) -> pd.DataFrame:
    """Runs saved per season by moving ``shift`` of home usage from the 'reduce' pitch to the 'lean on' pitch.

    Assumes each pitch keeps its quality when used a bit more or less (no adaptation by hitters): an
    optimistic, first-order estimate. Home pitches per season = home pitches on the franchise / seasons there.
    """
    lean = plan[plan.recommendation == "apoyarse en casa"].set_index(KEY)
    cut = plan[plan.recommendation == "reducir en casa"].set_index(KEY)
    both = lean.join(cut, lsuffix="_lean", rsuffix="_cut", how="inner")
    pt = pitchers.set_index(KEY)
    both = both.join(pt[["seasons", "home_pitches", "role"]], how="inner")
    n_seasons = both.seasons.str.count("-") + 1
    out = pd.DataFrame({
        "role": both.role, "lean_pitch": both.shape_lean, "cut_pitch": both.shape_cut,
        "lean_stuff_hh": both.stuff_plus_harp_helu_lean, "cut_stuff_hh": both.stuff_plus_harp_helu_cut,
        "gap_points": both.stuff_plus_harp_helu_lean - both.stuff_plus_harp_helu_cut,
        "cut_usage_home": both.usage_home_cut, "home_pitches_per_season": both.home_pitches / n_seasons})
    out["shift"] = np.minimum(shift, out.cut_usage_home)
    out["runs_saved_per_season"] = (out.gap_points * out["shift"] * out.home_pitches_per_season * rates["stuff"])
    return out.reset_index().sort_values(["franchise", "runs_saved_per_season"], ascending=[True, False])


def _value_runs(t: pd.DataFrame, rates: dict) -> tuple[pd.Series, pd.Series]:
    """Runs per 100 pitches vs an average pitcher: road = Pitching+; home adds the altitude resilience (Stuff+ rate)."""
    road = (t.pitching_plus - 100) * rates["pitching"] * 100
    return road + t.altitude_resilience * rates["stuff"] * 100, road


def rotation(d: pd.DataFrame, pitchers: pd.DataFrame, rates: dict, min_starts: int = 5) -> pd.DataFrame:
    """Starter order for home series (park-neutral value + altitude resilience) vs road series (park-neutral value),
    for each franchise's latest season. Pitcher values are the pooled franchise ones from ``pitcher_table``."""
    rows = []
    for f, df in d.groupby("franchise"):
        if f not in set(pitchers.franchise):
            continue
        season = int(df.year.max())
        s = df[(df.year == season) & df.is_start]
        starts = (s.drop_duplicates(["game_anon_id", "pitcher_anon_id"]).groupby("pitcher_anon_id")
                  .agg(starts=("is_start", "size"), home_starts=("is_home", "sum")))
        starts["pitches_per_start"] = s.groupby(["pitcher_anon_id", "game_anon_id"]).size().groupby(
            "pitcher_anon_id").mean()
        starts = starts[starts.starts >= min_starts].add_prefix("season_")
        t = pitchers[pitchers.franchise == f].set_index("pitcher_anon_id").join(starts, how="inner")
        if t.empty:
            continue
        home, road = _value_runs(t, rates)
        t = t.assign(season=season, home_value_runs_100=home, road_value_runs_100=road)
        t["home_order"] = t.home_value_runs_100.rank(ascending=False, method="first").astype(int)
        t["road_order"] = t.road_value_runs_100.rank(ascending=False, method="first").astype(int)
        rows.append(t.reset_index()[["franchise", "season", "pitcher_anon_id", "throws", "season_starts",
                                     "season_home_starts", "season_pitches_per_start", "pitching_plus", "stuff_plus",
                                     "stuff_plus_harp_helu", "delta_cdmx", "altitude_resilience", "home_value_runs_100",
                                     "road_value_runs_100", "home_order", "road_order"]])
    cols = ["franchise", "season", "pitcher_anon_id", "home_order", "road_order"]
    return (pd.concat(rows, ignore_index=True).sort_values(["franchise", "home_order"]) if rows
            else pd.DataFrame(columns=cols))


def rotation_runs(rot: pd.DataFrame, d: pd.DataFrame, rates: dict, games_per_series: int = 3) -> pd.DataFrame:
    """Runs per season from giving one home start per home series to the most altitude-resilient starter
    instead of the least resilient one (an explicit, simple scenario; series length is an assumption)."""
    out = []
    for f, r in rot.groupby("franchise"):
        if len(r) < 2:
            continue
        season = int(r.season.iloc[0])
        home_games = d[(d.franchise == f) & (d.year == season) & d.is_home].game_anon_id.nunique()
        best, worst = r.altitude_resilience.max(), r.altitude_resilience.min()
        pps = float(r.season_pitches_per_start.mean())
        series = home_games / games_per_series
        out.append(dict(franchise=f, season=season, starters=len(r), home_games=home_games,
                        home_series=series, resilience_gap_points=best - worst, pitches_per_start=pps,
                        runs_per_swapped_start=(best - worst) * pps * rates["stuff"],
                        runs_saved_per_season=(best - worst) * pps * rates["stuff"] * series,
                        orders_spearman=float(r.home_order.corr(r.road_order, method="spearman"))))
    return pd.DataFrame(out)


def bullpen(d: pd.DataFrame, pitchers: pd.DataFrame, rates: dict, min_side: int = 100,
            platoon_points: float = 1.5) -> pd.DataFrame:
    """Relievers: Pitching+ vs left/right-handed batters (shrunk), home value, and the matchup to use them in."""
    key = KEY + ["BatterSide"]
    side = _shrunk(d, "pitching_plus", key).unstack("BatterSide")
    n = d.groupby(key, observed=True).size().unstack("BatterSide")
    r = pitchers[pitchers.role == "relevista"].set_index(KEY)
    r = r.join(side.rename(columns=lambda c: f"pitching_plus_vs_{c}"))
    r = r.join(n.rename(columns=lambda c: f"pitches_vs_{c}"))
    home, _ = _value_runs(r, rates)
    r["home_value_runs_100"] = home
    gap = r.get("pitching_plus_vs_Left") - r.get("pitching_plus_vs_Right")
    enough = (r.get("pitches_vs_Left", 0) >= min_side) & (r.get("pitches_vs_Right", 0) >= min_side)
    r["matchup"] = np.select([enough & (gap >= platoon_points), enough & (gap <= -platoon_points)],
                             ["vs zurdos", "vs derechos"], "ambos lados")
    r["home_leverage_rank"] = r.groupby(level="franchise").home_value_runs_100.rank(ascending=False,
                                                                                    method="first").astype(int)
    keep = ["throws", "pitches", "pitching_plus", "pitching_plus_vs_Left", "pitching_plus_vs_Right",
            "pitches_vs_Left", "pitches_vs_Right", "stuff_plus_harp_helu", "delta_cdmx", "home_value_runs_100",
            "home_leverage_rank", "matchup"]
    return r[[c for c in keep if c in r]].reset_index().sort_values(["franchise", "home_leverage_rank"])


def runs_summary(mix: pd.DataFrame, rot_runs: pd.DataFrame, rates: dict) -> pd.DataFrame:
    """Projected runs (and wins at the Extreme bucket's runs per win) saved per season, per franchise."""
    rows = []
    for f in sorted(set(mix.franchise) | set(rot_runs.franchise)):
        m = float(mix.loc[mix.franchise == f, "runs_saved_per_season"].sum())
        r = float(rot_runs.loc[rot_runs.franchise == f, "runs_saved_per_season"].sum())
        for comp, runs in (("mezcla de lanzamientos en casa", m), ("orden de rotación casa/visita", r),
                           ("total", m + r)):
            rows.append(dict(franchise=f, component=comp, runs_per_season=runs,
                             wins_per_season=runs / rates["rpw_extreme"]))
    return pd.DataFrame(rows)


def audit(d: pd.DataFrame, franchises, rates: dict, shift: float = 0.10, min_pitches: int = 200,
          min_starts: int = 5, min_pitch_type: int = 50) -> dict[str, pd.DataFrame]:
    """Every table of the audit (aggregates only)."""
    pitchers = pitcher_table(d, franchises, min_pitches=min_pitches, min_starts=min_starts)
    plan = pitch_plan(d, franchises, min_pitches=min_pitch_type)
    plan = plan.merge(pitchers[KEY], on=KEY)  # only pitchers with enough pitches
    mix = mix_runs(plan, pitchers, rates, shift=shift)
    rot = rotation(d, pitchers, rates, min_starts=min_starts)
    rot_runs = rotation_runs(rot, d, rates)
    home_games = (d[d.franchise.isin(list(franchises)) & d.is_home].groupby(["franchise", "year"])
                  .game_anon_id.nunique().rename("home_games").reset_index())
    return {"pitchers": pitchers, "pitch_plan": plan, "home_games": home_games, "mix_runs": mix, "rotation": rot,
            "rotation_runs": rot_runs, "bullpen": bullpen(d, pitchers, rates),
            "runs_saved": runs_summary(mix, rot_runs, rates)}
