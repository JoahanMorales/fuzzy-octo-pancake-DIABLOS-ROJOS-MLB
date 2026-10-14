"""HACK-032 staff audit on a hand-built league (Louvain on the synthetic fixture does not give stable franchises)."""
import numpy as np
import pandas as pd
import pytest

from stuffplus import config, staff

RATES = {"stuff": 0.001, "pitching": 0.005, "rpw_league": 12.0, "rpw_extreme": 14.0}
# pitcher: (team, role, {pitch_id: (shape, neutral Stuff+, Stuff+ in Harp Helú air)})
PITCHERS = {
    "s1": (0, "SP", {0: ("riding 4S", 100, 84), 1: ("sweeper", 100, 96)}),  # gap 12: cut riding, lean sweeper
    "s2": (0, "SP", {0: ("sinker", 100, 90), 1: ("changeup", 100, 88)}),  # gap 2: no recommendation
    "r1": (0, "RP", {0: ("cutter", 100, 89), 1: ("slider", 100, 92)}),
    "s3": (1, "SP", {0: ("sinker", 100, 91), 1: ("slider", 100, 93)}),
    "r2": (1, "RP", {0: ("changeup", 100, 88), 1: ("curveball", 100, 93)}),
}


def _league(n_games=12, seed=2240):
    rng = np.random.default_rng(seed)
    rows, raw, games = [], [], []
    for g in range(n_games):
        home = g % 2
        games.append(dict(game_anon_id=f"g{g}", home_team=home, away_team=1 - home))
        for team in (0, 1):
            sp = ("s1" if (g // 2) % 2 == 0 else "s2") if team == 0 else "s3"
            rp = "r1" if team == 0 else "r2"
            for pitcher, n, first_inning in ((sp, 40, 1), (rp, 15, 7)):
                _, _, arsenal = PITCHERS[pitcher]
                for i in range(n):
                    pid = i % 2
                    shape, neutral, hh = arsenal[pid]
                    uid = f"{g}-{pitcher}-{i}"
                    e = rng.normal(0, 1)
                    rows.append(dict(PitchUID=uid, pitcher_anon_id=pitcher, year=2026, game_anon_id=f"g{g}",
                                     pitch_id=pid, pitch_family=shape, shape=shape, PitcherThrows="Right",
                                     altitude_category="Extreme Altitude", RelSpeed=90.0, InducedVertBreak=15.0,
                                     HorzBreak=5.0, stuff_plus=neutral + e, stuff_plus_harp_helu=hh + e,
                                     stuff_plus_own_air=(hh if team == home else neutral) + e,
                                     location_plus=100 + rng.normal(0, 1), pitching_plus=100 + rng.normal(0, 1)))
                    rows[-1]["delta_cdmx"] = rows[-1]["stuff_plus_harp_helu"] - rows[-1]["stuff_plus"]
                    raw.append({"PitchUID": uid, "Inning": first_inning + i // 8,
                                "Top/Bottom": "Top" if team == home else "Bottom",
                                "BatterSide": "Left" if i % 3 == 0 else "Right"})
    team_map = pd.DataFrame([dict(pitcher_anon_id=p, season=2026, team_id=t, franchise=5 if t == 0 else 7,
                                  role="pitcher", batter_anon_id=None) for p, (t, _, _) in PITCHERS.items()])
    return pd.DataFrame(rows), pd.DataFrame(raw), team_map, pd.DataFrame(games)


@pytest.fixture(scope="module")
def ctx():
    scores, raw, tm, pm = _league()
    return staff.pitch_context(scores, raw, tm, pm)


@pytest.fixture(scope="module")
def tables(ctx):
    return staff.audit(ctx, [5], RATES, min_pitches=50, min_starts=2, min_pitch_type=20)


def test_staff_franchises_are_the_lowest_density():
    rho = pd.DataFrame({"franchise": [3, 11, 5, 18], "rho_mean": [0.95, 0.813, 0.821, 0.826]})
    assert staff.staff_franchises(rho) == [11, 5]


def test_context_home_flag_and_starters(ctx):
    assert (ctx.is_home == (ctx["Top/Bottom"] == "Top")).all()
    starts = ctx[ctx.is_start].groupby("pitcher_anon_id").game_anon_id.nunique()
    assert starts.to_dict() == {"s1": 6, "s2": 6, "s3": 12}
    assert not ctx[ctx.pitcher_anon_id.isin(["r1", "r2"])].is_start.any()


def test_context_rejects_ambiguous_home_half():
    scores, raw, tm, pm = _league()
    raw["Top/Bottom"] = np.where(np.arange(len(raw)) % 2 == 0, "Top", "Bottom")
    with pytest.raises(ValueError, match="home team"):
        staff.pitch_context(scores, raw, tm, pm)


def test_pitch_plan_uses_level_in_harp_helu_air_and_min_gap(tables):
    plan = tables["pitch_plan"].set_index(["pitcher_anon_id", "shape"])
    assert plan.loc[("s1", "sweeper"), "recommendation"] == "apoyarse en casa"
    assert plan.loc[("s1", "riding 4S"), "recommendation"] == "reducir en casa"
    assert (plan.loc["s2", "recommendation"] == "").all()  # 2-point gap: no change
    assert set(tables["pitch_plan"].franchise) == {5}  # never another franchise's staff


def test_mix_runs_follow_the_stated_formula(tables):
    m = tables["mix_runs"].set_index("pitcher_anon_id").loc["s1"]
    expected = m.gap_points * min(0.10, m.cut_usage_home) * m.home_pitches_per_season * RATES["stuff"]
    assert m.runs_saved_per_season == pytest.approx(expected)
    assert m.gap_points == pytest.approx(12, abs=1.0)


def test_rotation_orders_by_altitude_resilience_at_home(tables):
    rot = tables["rotation"].set_index("pitcher_anon_id")
    assert set(rot.index) == {"s1", "s2"}
    assert rot.loc["s1", "altitude_resilience"] > rot.loc["s2", "altitude_resilience"]  # Δ −10 vs −11
    rr = tables["rotation_runs"].iloc[0]
    gap = rot.altitude_resilience.max() - rot.altitude_resilience.min()
    assert rr.runs_saved_per_season == pytest.approx(gap * rr.pitches_per_start * RATES["stuff"] * rr.swaps)
    # never more swaps than home series, the worst starter's home starts or the best starter's road starts
    best, worst = rot.loc[rr.best_resilience], rot.loc[rr.worst_resilience]
    assert rr.swaps <= min(rr.home_series, worst.season_home_starts, best.season_starts - best.season_home_starts)


def test_rotation_swaps_are_capped_by_the_schedule(ctx):
    pitchers = staff.pitcher_table(ctx, [5], min_pitches=50, min_starts=2)
    rot = staff.rotation(ctx, pitchers, RATES, min_starts=2)
    rot.loc[rot.pitcher_anon_id == "s2", "season_home_starts"] = 1  # the least resilient starter had 1 home start
    assert staff.rotation_runs(rot, ctx, RATES).iloc[0].swaps == 1


def test_bullpen_and_runs_summary(tables):
    bp = tables["bullpen"]
    assert list(bp.pitcher_anon_id) == ["r1"] and bp.matchup.isin(["vs zurdos", "vs derechos", "ambos lados"]).all()
    r = bp.iloc[0]  # the matchup is the platoon split above the league's for the same throwing hand
    assert r.platoon_vs_league == pytest.approx(r.pitching_plus_vs_Left - r.pitching_plus_vs_Right - r.league_platoon_gap)
    rs = tables["runs_saved"].set_index("component")
    assert rs.loc["total", "runs_per_season"] == pytest.approx(
        rs.drop("total").runs_per_season.sum())
    assert rs.loc["total", "wins_per_season"] == pytest.approx(rs.loc["total", "runs_per_season"] / RATES["rpw_extreme"])


def test_hack018_sensitivity_is_joined_by_franchise_seasons(ctx):
    sens = pd.DataFrame({"pitcher_anon_id": ["s1", "s1", "r1"], "year": [2026, 2025, 2026],
                         "delta_eb": [-9.0, -50.0, -11.0], "observed_eb": [-8.0, -50.0, np.nan]})
    t = staff.audit(ctx, [5], RATES, sens=sens, min_pitches=50, min_starts=2, min_pitch_type=20)["pitchers"]
    s1 = t.set_index("pitcher_anon_id").loc["s1"]
    assert s1.hack018_delta_eb == -9.0 and s1.hack018_observed_eb == -8.0  # 2025 is not a season on franchise 5


def test_outputs_are_aggregates_only(tables):
    for name, t in tables.items():
        assert not {"PitchUID", "game_anon_id", "batter_anon_id"} & set(t.columns), name


def test_rates_come_from_business_value_csvs():
    r = staff.load_rates(config.REPORTS_DIR)
    assert 0 < r["stuff"] < r["pitching"] and r["rpw_extreme"] > r["rpw_league"] > 0
