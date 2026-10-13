"""HACK-003: teams from lineups, home park, pitcher teams, franchise links (synthetic league of 6 teams)."""
import pandas as pd

from stuffplus.physics.parks import game_teams, infer_teams, link_franchises, park_table, pitcher_teams, tune_resolution

# The fixture has ~3 shared lineups per season between teammates (min 1) and none across teams, so the
# spec default of 3 would split teams; the test relaxes it. Real data keeps min_weight=3.
KW = dict(min_weight=1, min_batters=5)


def _true_team(batter: str) -> int:  # fixture ids: batter_{team*10+i}
    return int(batter.split("_")[1]) // 10


def test_infer_teams_recovers_every_team(synthetic_pitches):
    teams = infer_teams(synthetic_pitches, 2024, **KW).dropna()
    assert teams.nunique() == 6
    for _, members in teams.groupby(teams):
        assert len({_true_team(b) for b in members.index}) == 1  # purity 1.0, label-free
    assert len({t for t in teams.index.map(_true_team)}) == 6


def test_team_ids_are_stable(synthetic_pitches):
    a = infer_teams(synthetic_pitches, 2025, **KW)
    b = infer_teams(synthetic_pitches.sample(frac=1, random_state=1), 2025, **KW)
    pd.testing.assert_series_equal(a, b)


def test_home_team_and_altitude_purity(synthetic_pitches):
    df = synthetic_pitches[synthetic_pitches["year"] == 2024]
    teams = infer_teams(df, **KW)
    games = game_teams(df, teams)
    assert (games["home_purity"] == 1.0).all() and len(games) == df["game_anon_id"].nunique()
    table = park_table(df, games)
    assert (table["purity"] == 1.0).all() and len(table) == 6
    assert sorted(table["bucket"].astype(str).unique()) == sorted(df["altitude_category"].astype(str).unique())


def test_pitchers_pitch_for_the_fielding_team(synthetic_pitches):
    df = synthetic_pitches[synthetic_pitches["year"] == 2024]
    teams = infer_teams(df, **KW)
    pt = pitcher_teams(df, teams)
    assert pt.nunique() == 6
    # fixture: pitcher_{team*7+i}; every pitcher maps to one team consistent with his peers
    assert all(len(set(pt[[p for p in pt.index if int(p.split('_')[1]) // 7 == t]])) == 1 for t in range(6))


def test_franchises_link_across_seasons(synthetic_pitches):
    maps = {y: infer_teams(synthetic_pitches, y, **KW) for y in (2024, 2025, 2026)}
    links = link_franchises(maps)
    assert links["franchise"].nunique() == 6 and len(links) == 18
    assert links.groupby("franchise")["season"].nunique().eq(3).all()


def test_park_table_accepts_optional_rho(synthetic_pitches):
    df = synthetic_pitches[synthetic_pitches["year"] == 2024]
    games = game_teams(df, infer_teams(df, **KW))
    rho = pd.Series(1.0, index=games.index)
    assert {"rho_median", "rho_iqr"} <= set(park_table(df, games, rho).columns)


def test_missing_batter_ids_are_ignored(synthetic_pitches):
    df = synthetic_pitches.copy()
    df.loc[df.index[::50], "batter_anon_id"] = None
    assert infer_teams(df, 2024, **KW).dropna().nunique() == 6


def test_tune_resolution_keeps_a_clean_split(synthetic_pitches):
    res, teams = tune_resolution(synthetic_pitches, 2024, min_weight=1, min_batters=5)
    assert res == 1.0 and teams.dropna().nunique() == 6


def test_maps_are_rebuilt_deterministically_and_cached(synthetic_pitches, tmp_path):
    from stuffplus.physics.parks import load_maps
    a = load_maps(synthetic_pitches, cache_dir=tmp_path, min_weight=1, min_batters=5)
    assert (tmp_path / "park_map.parquet").exists() and a["park_map"]["franchise"].nunique() == 6
    b = load_maps(None, cache_dir=tmp_path)  # second call reads the cache, no raw data needed
    pd.testing.assert_frame_equal(a["park_map"], b["park_map"])
    c = load_maps(synthetic_pitches, cache_dir=tmp_path / "x", min_weight=1, min_batters=5)
    pd.testing.assert_frame_equal(a["park_map"], c["park_map"])
