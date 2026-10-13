"""Park identification (HACK-003): teams from batter lineups, home park per game, franchise links.

Method: per season, build a graph of batters weighted by the number of (game, half) lineups they share
and cluster it with Louvain. Each cluster is a team. The home team of a game is the majority team of the
Bottom-half batters (the home side bats in the Bottom). Pitchers pitch the half where their team is NOT
batting, so they inherit a team from the same map. Pitcher clustering does not work (trades merge teams).

Team ids are stable: clusters are numbered by their smallest batter id, so reruns give identical ids.
Nothing here needs air density; park tables take an optional per-game ``rho`` Series (HACK-004).
"""
from __future__ import annotations

import itertools
from collections import Counter

import numpy as np
import pandas as pd

SEED = 2240
HALF = "Top/Bottom"
BATTER = "batter_anon_id"
PITCHER = "pitcher_anon_id"
GAME = "game_anon_id"


def _season(df: pd.DataFrame, season: int | None) -> pd.DataFrame:
    return df if season is None else df[df["year"] == season]


def lineup_graph(df: pd.DataFrame, min_weight: int = 3):
    """Batter graph; edge weight = number of (game, half) lineups the two batters share (kept if >= min_weight)."""
    import networkx as nx

    lineups = df.groupby([GAME, HALF], observed=True)[BATTER].agg(lambda s: sorted(set(s.dropna())))
    weights: Counter = Counter()
    for batters in lineups:
        weights.update(itertools.combinations(batters, 2))
    graph = nx.Graph()
    graph.add_nodes_from(df[BATTER].dropna().unique())
    graph.add_weighted_edges_from((a, b, w) for (a, b), w in weights.items() if w >= min_weight)
    return graph


def infer_teams(df: pd.DataFrame, season: int | None = None, min_weight: int = 3,
                resolution: float = 1.0, min_batters: int = 5, seed: int = SEED) -> pd.Series:
    """Batter -> team id (0..k-1, numbered by smallest batter id) for one season.

    ``min_weight=3`` is the spec default for real data. Batters whose cluster has fewer than ``min_batters``
    members (call-ups seen in a couple of lineups) get NaN so they cannot create fake teams.
    """
    from networkx.algorithms.community import louvain_communities

    sub = _season(df, season)
    graph = lineup_graph(sub, min_weight)
    communities = louvain_communities(graph, weight="weight", resolution=resolution, seed=seed)
    big = sorted((sorted(c) for c in communities if len(c) >= min_batters), key=lambda c: c[0])
    team = {b: i for i, members in enumerate(big) for b in members}
    return pd.Series(team, name="team_id", dtype="Int64").reindex(sorted(graph.nodes)).rename_axis(BATTER)


def _majority(s: pd.Series):
    s = s.dropna()
    return s.mode().iloc[0] if len(s) else pd.NA


def game_teams(df: pd.DataFrame, batter_team: pd.Series) -> pd.DataFrame:
    """Per game: home_team (majority team of Bottom batters), away_team (Top), and the purity of both calls."""
    sub = df[[GAME, HALF, BATTER]].copy()
    sub["team"] = sub[BATTER].map(batter_team)
    sub = sub.dropna(subset=["team"])
    rows = {}
    for half, name in (("Bottom", "home"), ("Top", "away")):
        h = sub[sub[HALF].astype(str) == half].groupby(GAME)["team"]
        rows[f"{name}_team"] = h.agg(_majority)
        rows[f"{name}_purity"] = h.agg(lambda s: (s == _majority(s)).mean())
    out = pd.DataFrame(rows)
    return out.dropna(subset=["home_team"]).astype({"home_team": "int64"})


def pitcher_teams(df: pd.DataFrame, batter_team: pd.Series) -> pd.Series:
    """Pitcher -> team for one season: the side that is NOT batting while he pitches (anonymised ids only)."""
    games = game_teams(df, batter_team)
    sub = df[[GAME, HALF, PITCHER]].drop_duplicates().join(games[["home_team", "away_team"]], on=GAME)
    top = sub[HALF].astype(str).eq("Top")  # Top: away bats, home pitches
    sub["team"] = np.where(top, sub["home_team"], sub["away_team"])
    team = sub.dropna(subset=["team"]).groupby(PITCHER)["team"].agg(_majority).astype("int64")
    return team.rename("team_id")


def link_franchises(season_maps: dict[int, pd.Series]) -> pd.DataFrame:
    """Link per-season team ids into franchises by batter overlap (greedy best match to the previous season).

    Returns one row per (season, team_id) with a stable ``franchise`` id taken from the first season.
    """
    seasons = sorted(season_maps)
    first = season_maps[seasons[0]].dropna()
    link = {(seasons[0], int(t)): int(t) for t in first.unique()}
    next_id = max(link.values(), default=-1) + 1
    for prev, cur in zip(seasons, seasons[1:]):
        a, b = season_maps[prev].dropna(), season_maps[cur].dropna()
        shared = a.index.intersection(b.index)
        pairs = Counter(zip(a.loc[shared].astype(int), b.loc[shared].astype(int)))
        used: set[int] = set()
        for (ta, tb), _ in sorted(pairs.items(), key=lambda kv: -kv[1]):
            if (cur, tb) in link or link.get((prev, ta)) in used:
                continue
            link[(cur, tb)] = link[(prev, ta)]
            used.add(link[(prev, ta)])
        for t in sorted(int(x) for x in b.unique()):
            if (cur, t) not in link:
                link[(cur, t)] = next_id
                next_id += 1
    return pd.DataFrame([{"season": s, "team_id": t, "franchise": f} for (s, t), f in sorted(link.items())])


def park_table(df: pd.DataFrame, games: pd.DataFrame, rho: pd.Series | None = None) -> pd.DataFrame:
    """One row per home team: home games, altitude bucket, purity (share of games in the modal bucket).

    ``rho`` is an optional per-game air-density Series indexed by game id (HACK-004); adds median / IQR.
    """
    bucket = df.groupby(GAME, observed=True)["altitude_category"].agg(_majority)
    g = games[["home_team"]].join(bucket.rename("bucket")).dropna(subset=["bucket"])  # unknown altitude: skipped
    if rho is not None:
        g = g.join(rho.rename("rho"))
    out = []
    for team, grp in g.groupby("home_team"):
        row = {"team_id": team, "home_games": len(grp), "bucket": _majority(grp["bucket"]),
               "purity": float((grp["bucket"] == _majority(grp["bucket"])).mean())}
        if "rho" in grp:
            q1, med, q3 = grp["rho"].quantile([0.25, 0.5, 0.75])
            row.update(rho_median=med, rho_iqr=q3 - q1)
        out.append(row)
    return pd.DataFrame(out)


def tune_resolution(df: pd.DataFrame, season: int | None = None, grid=(1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 6.0),
                    min_purity: float = 0.9, max_games_ratio: float = 1.5, max_teams: int = 21,
                    **kwargs) -> tuple[float, pd.Series]:
    """Smallest Louvain resolution whose split is consistent; returns (resolution, batter -> team).

    Consistent = every team has altitude purity >= ``min_purity``, no team has more than ``max_games_ratio``
    times the median home games (two same-altitude teams merged are 'pure' but have ~2x games), and at most
    ``max_teams`` teams (LMB has 20). If no resolution qualifies the last one on the grid is returned.
    """
    sub = _season(df, season)
    for res in grid:
        teams = infer_teams(sub, None, resolution=res, **kwargs)
        table = park_table(sub, game_teams(sub, teams))
        games = table["home_games"]
        if (table["purity"].min() >= min_purity and games.max() <= max_games_ratio * games.median()
                and len(table) <= max_teams):
            return res, teams
    return res, teams


def build_maps(df: pd.DataFrame, **kwargs) -> dict[str, pd.DataFrame]:
    """Row-level maps rebuilt deterministically from the raw data (never committed; see ``load_maps``).

    ``park_map``: game -> season, home/away team, purity, franchise, is_home_bucket.
    ``team_map``: batter/pitcher -> season, team_id, franchise, role.
    ``kwargs`` go to ``tune_resolution`` (e.g. ``min_weight`` for tiny synthetic data).
    """
    seasons = sorted(df["year"].dropna().unique())
    bmaps, games, teams = {}, [], []
    for yr in seasons:
        sub = df[df["year"] == yr]
        _, bt = tune_resolution(sub, **kwargs)
        bmaps[yr] = bt
        games.append(game_teams(sub, bt).reset_index().assign(season=yr))
        teams.append(pd.concat([bt.dropna().rename("team_id").reset_index().assign(role="batter"),
                                pitcher_teams(sub, bt).reset_index().assign(role="pitcher")]).assign(season=yr))
    links = link_franchises(bmaps)
    park_map = pd.concat(games, ignore_index=True).merge(
        links.rename(columns={"team_id": "home_team"}), on=["season", "home_team"])
    team_map = pd.concat(teams, ignore_index=True).merge(links, on=["season", "team_id"])
    bucket = df.groupby(GAME, observed=True)["altitude_category"].agg(_majority)
    park_map["bucket"] = park_map[GAME].map(bucket)
    return {"park_map": park_map, "team_map": team_map}


def load_maps(df: pd.DataFrame | None = None, cache_dir=None, **kwargs) -> dict[str, pd.DataFrame]:
    """Maps for downstream tasks: read the local cache in ``artifacts/`` if present, else rebuild from raw data."""
    from stuffplus.config import ARTIFACTS_DIR

    cache = (cache_dir or ARTIFACTS_DIR)
    paths = {k: cache / f"{k}.parquet" for k in ("park_map", "team_map")}
    if all(p.exists() for p in paths.values()):
        return {k: pd.read_parquet(p) for k, p in paths.items()}
    if df is None:
        from stuffplus.io import load_raw
        from stuffplus.schema import clean
        df = clean(load_raw())
    maps = build_maps(df, **kwargs)
    cache.mkdir(parents=True, exist_ok=True)
    for k, p in paths.items():
        maps[k].to_parquet(p, index=False)
    return maps


def candidate_staff(maps: dict[str, pd.DataFrame], franchises) -> pd.DataFrame:
    """Pitchers (anonymised ids) who pitched for the given franchise(s), per season. Not committed: row-level."""
    tm = maps["team_map"]
    out = tm[(tm["role"] == "pitcher") & tm["franchise"].isin(list(franchises))]
    return out[["season", "franchise", "pitcher_anon_id"]].sort_values(["season", "franchise", "pitcher_anon_id"])
