import numpy as np
import pandas as pd
import pytest

from stuffplus import value as V


def _half_rows(game, half, inn, runs, bucket="No Altitude", year=2024):
    rows = [dict(game_anon_id=game, **{"Top/Bottom": half}, Inning=i, RunsScored=0.0, year=year, altitude_category=bucket)
            for i in range(1, inn + 1)]
    rows[0]["RunsScored"] = float(runs)  # todas las carreras en una sola fila
    return rows


def _df(games):
    rows = []
    for g, (away, home, inn) in games.items():
        rows += _half_rows(g, "Top", inn, away) + _half_rows(g, "Bottom", inn, home)
    return pd.DataFrame(rows)


def test_game_scores_sums_runs_per_half_and_drops_ties_and_short_games():
    df = _df({"a": (3, 5, 9), "b": (4, 4, 9), "c": (1, 0, 3), "d": (7, 2, 9)})
    s = V.game_scores(df)
    assert list(s.index) == ["a", "d"]  # b empatado, c con 3 entradas
    assert s.loc["a", ["away_runs", "home_runs", "home_win"]].tolist() == [3, 5, 1]
    assert s.loc["d", "home_win"] == 0


def test_pythagorean_exponent_recovers_planted_value():
    rng = np.random.default_rng(0)
    n, x_true = 120, 1.85
    rs = rng.uniform(4, 7, n) * 90
    ra = rng.uniform(4, 7, n) * 90
    p = rs**x_true / (rs**x_true + ra**x_true)
    wins = rng.binomial(90, p)
    ts = pd.DataFrame(dict(games=90, wins=wins, rs=rs, ra=ra))
    fit = V.fit_pythagorean(ts, n_boot=200)
    assert fit["lo"] < x_true < fit["hi"]


def test_runs_per_win_and_wins_from_runs():
    assert V.runs_per_win(5.0, 2.0) == pytest.approx(10.0)  # la regla de los 10 carreras por victoria
    assert V.runs_per_win(7.0, 2.0) > V.runs_per_win(5.0, 2.0)  # más anotación (altura) ⇒ cada carrera vale menos
    assert V.wins_from_runs(20, 5.0, 2.0) == pytest.approx(2.0)
    # la linealización coincide con el pitagórico exacto para una diferencia pequeña
    r, x, d = 5.0, 1.9, 0.2
    exact = (r**x) / (r**x + (r - d) ** x) - 0.5  # RS=r, RA=r-d: ventaja de d carreras por juego
    assert exact == pytest.approx(d / V.runs_per_win(r, x), rel=0.08)


def test_stuff_point_is_a_tenth_of_sigma_and_scales_linearly():
    assert V.runs_per_stuff_point(0.05) == pytest.approx(0.005)
    sig = V.sigma_from_variance_explained(0.27, 0.01)
    assert sig == pytest.approx(0.027)
    t = V.conversion_table({"r2=1%": sig}, [1000, 2000], {"liga": 10.0, "CDMX": 15.0})
    a = t[(t.lanzamientos == 1000) & (t.entorno == "liga")].iloc[0]
    b = t[(t.lanzamientos == 2000) & (t.entorno == "liga")].iloc[0]
    c = t[(t.lanzamientos == 1000) & (t.entorno == "CDMX")].iloc[0]
    assert b.carreras == pytest.approx(2 * a.carreras)
    assert c.victorias == pytest.approx(a.victorias * 10 / 15)  # en altura la misma carrera vale menos victorias


def test_altitude_sensitivity_no_heterogeneity_gives_tau_zero_but_positive_bound():
    rng = np.random.default_rng(4)
    rows = []
    for p in range(500):
        for env, shift in (("No Altitude", 0.0), ("Extreme Altitude", 0.01)):
            rows += [(f"p{p}", 2024, env, v) for v in rng.normal(shift, 0.25, 120)]
    df = pd.DataFrame(rows, columns=["pitcher_anon_id", "year", "altitude_category", "rv"])
    s = V.altitude_sensitivity(df, "rv", "No Altitude", "Extreme Altitude", min_n=100)
    assert s["tau"] < 0.012 and s["tau_hi"] > s["tau"] and s["mean_delta"] == pytest.approx(0.01, abs=0.004)


def test_altitude_proof_example_orders_arms():
    ex = V.altitude_proof_example(0.010, 0.006, 90, 15, 15.0)
    assert ex.iloc[0].carreras_extra > ex.iloc[1].carreras_extra > ex.iloc[2].carreras_extra
    assert ex.attrs["gap_wins"] == pytest.approx(ex.attrs["gap_runs"] / 15.0)


def test_altitude_sensitivity_recovers_mean_and_true_spread():
    rng = np.random.default_rng(3)
    rows = []
    for p in range(200):
        eff = rng.normal(0.02, 0.01)  # τ verdadero = 0.01
        for env, shift in (("No Altitude", 0.0), ("Extreme Altitude", eff)):
            y = rng.normal(shift, 0.25, 400)
            rows += [(f"p{p}", 2024, env, v) for v in y]
    df = pd.DataFrame(rows, columns=["pitcher_anon_id", "year", "altitude_category", "rv"])
    s = V.altitude_sensitivity(df, "rv", "No Altitude", "Extreme Altitude", min_n=100)
    assert s["mean_delta"] == pytest.approx(0.02, abs=0.003)
    assert s["tau"] == pytest.approx(0.01, abs=0.004)
    assert s["raw_sd"] > s["tau"]  # el ruido de muestreo infla la dispersión observada
    assert s["tau_hi"] >= s["tau"] and s["tau_hi"] < 0.02


def test_smoke_on_synthetic_fixture(synthetic_pitches):
    from stuffplus.schema import clean

    s = V.game_scores(clean(synthetic_pitches), min_innings=1)
    assert len(s) > 0 and set(s["home_win"]) <= {0, 1}
    assert (s[["home_runs", "away_runs"]] >= 0).all().all()
