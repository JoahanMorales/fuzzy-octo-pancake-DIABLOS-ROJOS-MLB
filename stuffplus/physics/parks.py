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

    lineups = df.groupby([GAME, HALF], observed=True)[BATTER].agg(lambda s: sorted(set(s)))
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
    g = games[["home_team"]].join(bucket.rename("bucket"))
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
