"""Valor de negocio (HACK-035): Stuff+ → carreras → victorias, con la conversión estimada con datos de la LMB.

Cadena:
1. ``game_scores``: marcador por juego sumando ``RunsScored`` por (juego, media entrada); gana el que anota más.
2. ``fit_pythagorean``: exponente pitagórico de la LMB (equipo-temporada, IC bootstrap sobre equipo-temporadas).
3. ``runs_per_win``: con W% = 1/(1+(RA/RS)^x) y r carreras por equipo-juego, una carrera menos permitida por juego
   vale x/(4r) de W%, o sea **carreras por victoria = 4r/x** (r mayor en altura ⇒ cada carrera vale menos).
4. ``runs_per_stuff_point``: por definición de la escala (HACK-013), 1 punto de Stuff+ = 0.1·σ de xRV *predicho* por
   lanzamiento; las carreras realizadas dependen de la pendiente de calibración fuera de muestra (``calibration_slope``).
   σ viene del bundle del modelo (``scalers.stuff.stats``); no se inventa.
5. ``conversion_table`` y ``altitude_proof_example``: puntos → carreras → victorias en casa (CDMX) y en la liga.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from stuffplus.config import SEED

GAME = "game_anon_id"
HALF = "Top/Bottom"
POINT_SD_FRACTION = 0.1  # 10 puntos = 1 σ (stuffplus.scale)


# ------------------------------------------------------------------ marcadores
def game_scores(df: pd.DataFrame, min_innings: int = 5) -> pd.DataFrame:
    """Un renglón por juego: carreras de local/visita, entradas, temporada, bucket de altitud y si ganó el local.

    Suma ``RunsScored`` por (juego, media entrada). Se descartan juegos sin ambas mitades, con menos de
    ``min_innings`` entradas o empatados (suspendidos)."""
    runs = df.groupby([GAME, HALF], observed=True)["RunsScored"].sum().unstack()
    for c in ("Top", "Bottom"):
        if c not in runs:
            runs[c] = np.nan
    info = df.groupby(GAME, observed=True).agg(innings=("Inning", "max"), season=("year", "first"),
                                               bucket=("altitude_category", lambda s: s.astype(str).mode().iat[0]))
    out = info.join(runs[["Top", "Bottom"]].rename(columns={"Bottom": "home_runs", "Top": "away_runs"}))
    out = out.dropna(subset=["home_runs", "away_runs"])
    out = out[(out["innings"] >= min_innings) & (out["home_runs"] != out["away_runs"])].copy()
    out["home_win"] = (out["home_runs"] > out["away_runs"]).astype(int)
    return out


def team_seasons(scores: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """Equipo-temporada: juegos, victorias, carreras a favor y en contra. ``teams`` indexada por juego con
    ``home_team`` y ``away_team`` (p.ej. ``park_map`` de HACK-003)."""
    g = scores.join(teams[["home_team", "away_team"]], how="inner")
    home = pd.DataFrame({"season": g["season"], "team": g["home_team"], "rs": g["home_runs"], "ra": g["away_runs"],
                         "w": g["home_win"]})
    away = pd.DataFrame({"season": g["season"], "team": g["away_team"], "rs": g["away_runs"], "ra": g["home_runs"],
                         "w": 1 - g["home_win"]})
    t = pd.concat([home, away]).groupby(["season", "team"]).agg(games=("w", "size"), wins=("w", "sum"),
                                                              rs=("rs", "sum"), ra=("ra", "sum")).reset_index()
    return t


# ------------------------------------------------------------------ pitagórico y carreras por victoria
def _sse(x: float, ts: pd.DataFrame) -> float:
    pred = ts["rs"] ** x / (ts["rs"] ** x + ts["ra"] ** x)
    return float((ts["games"] * (ts["wins"] / ts["games"] - pred) ** 2).sum())


def pythagorean_exponent(ts: pd.DataFrame, lo: float = 0.8, hi: float = 4.0) -> float:
    """Exponente x que minimiza el error cuadrático ponderado por juegos de W% (búsqueda de sección áurea)."""
    a, b, phi = lo, hi, (np.sqrt(5) - 1) / 2
    c, d = b - phi * (b - a), a + phi * (b - a)
    for _ in range(60):
        if _sse(c, ts) < _sse(d, ts):
            b = d
        else:
            a = c
        c, d = b - phi * (b - a), a + phi * (b - a)
    return float((a + b) / 2)


def fit_pythagorean(ts: pd.DataFrame, n_boot: int = 2000, seed: int = SEED) -> dict:
    """Exponente pitagórico con IC 95 % bootstrap sobre equipo-temporadas."""
    x = pythagorean_exponent(ts)
    rng = np.random.default_rng(seed)
    n = len(ts)
    boots = [pythagorean_exponent(ts.iloc[rng.integers(0, n, n)]) for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"exponent": x, "lo": float(lo), "hi": float(hi), "n_team_seasons": n}


def runs_per_win(runs_per_team_game: float, exponent: float) -> float:
    """Carreras por victoria = 4r/x (linealización pitagórica en torno a un equipo promedio)."""
    return 4.0 * runs_per_team_game / exponent


def wins_from_runs(runs_saved: float, runs_per_team_game: float, exponent: float) -> float:
    return runs_saved / runs_per_win(runs_per_team_game, exponent)


# ------------------------------------------------------------------ Stuff+ → carreras
def runs_per_stuff_point(sigma_xrv: float, calibration: float = 1.0) -> float:
    """Carreras por lanzamiento de +1 punto de Stuff+: 0.1·σ(xRV predicho)·pendiente de calibración.

    ``sigma_xrv``: desviación estándar por lanzamiento del xRV *predicho* (la que usa ``PlusScaler``)."""
    return POINT_SD_FRACTION * float(sigma_xrv) * float(calibration)


def calibration_slope(x, y, groups, n_boot: int = 1000, seed: int = SEED) -> dict:
    """Pendiente de calibración de ``y`` (rv_x observado) sobre ``x`` (xRV predicho fuera de muestra): carreras realizadas
    por carrera predicha. IC 95 % bootstrap por grupo (pitcher), con sumas por grupo (no recalcula nada por fila)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    codes, uniq = pd.factorize(pd.Series(np.asarray(groups)[ok]))
    k = len(uniq)
    sums = {n: np.bincount(codes, weights=v, minlength=k) for n, v in
            {"n": np.ones(ok.sum()), "x": x[ok], "y": y[ok], "xy": x[ok] * y[ok], "xx": x[ok] ** 2}.items()}

    def slope(c):
        n, sx, sy = c @ sums["n"], c @ sums["x"], c @ sums["y"]
        return ((c @ sums["xy"]) - sx * sy / n) / ((c @ sums["xx"]) - sx**2 / n)

    point = slope(np.ones(k))
    rng = np.random.default_rng(seed)
    boots = np.array([slope(rng.multinomial(k, np.full(k, 1 / k)).astype(float)) for _ in range(n_boot)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"slope": float(point), "lo": float(lo), "hi": float(hi), "sd_x": float(x[ok].std()), "n": int(ok.sum()),
            "n_groups": int(k)}


def sigma_from_variance_explained(sd_rv: float, r2: float) -> float:
    """σ del xRV predicho si el modelo explica la fracción ``r2`` de la varianza del xRV observado por lanzamiento."""
    return float(np.sqrt(r2) * sd_rv)


def conversion_table(sigmas: dict[str, float], pitches: Iterable[int], rpw: dict[str, float]) -> pd.DataFrame:
    """+1 punto de Stuff+ sostenido en N lanzamientos → carreras ahorradas → victorias, por escenario de σ y entorno.

    ``sigmas``: etiqueta → σ(xRV predicho); ``rpw``: entorno → carreras por victoria."""
    rows = []
    for label, s in sigmas.items():
        per_pitch = runs_per_stuff_point(s)
        for n in pitches:
            runs = per_pitch * n
            for env, r in rpw.items():
                rows.append(dict(escenario=label, sigma_xrv=s, lanzamientos=int(n), carreras=runs, entorno=env,
                                 carreras_por_victoria=r, victorias=runs / r))
    return pd.DataFrame(rows)


def altitude_proof_example(delta_runs_per_pitch: float, sensitivity_sd: float, pitches_per_start: float,
                           n_starts: int, rpw_home: float) -> pd.DataFrame:
    """Brecha entre un brazo de alta pérdida y uno a prueba de altura en una temporada de aperturas en casa.

    ``delta_runs_per_pitch``: costo medio de jugar en altura (Δ xRV por lanzamiento, Extreme − No).
    ``sensitivity_sd``: dispersión entre pitchers de ese costo compatible con los datos (``tau_hi``: el piso en 0 del
    estimador de momentos no prueba que no exista). Compara a +sd (alta pérdida) y −sd (a prueba de altura)."""
    rows = []
    for label, cost in (("alta pérdida (+τ95)", delta_runs_per_pitch + sensitivity_sd), ("promedio", delta_runs_per_pitch),
                        ("a prueba de altura (−τ95)", max(delta_runs_per_pitch - sensitivity_sd, 0.0))):
        runs = cost * pitches_per_start * n_starts
        rows.append(dict(brazo=label, carreras_extra_por_lanzamiento=cost, carreras_extra=runs, victorias_perdidas=runs / rpw_home))
    out = pd.DataFrame(rows)
    out.attrs["gap_runs"] = float(out.iloc[0]["carreras_extra"] - out.iloc[2]["carreras_extra"])
    out.attrs["gap_wins"] = float(out.iloc[0]["victorias_perdidas"] - out.iloc[2]["victorias_perdidas"])
    return out


# ------------------------------------------------------------------ sensibilidad por pitcher (momentos)
def _tau(delta: np.ndarray, se2: np.ndarray) -> float:
    return float(np.sqrt(max(np.var(delta, ddof=1) - se2.mean(), 0.0)))


def altitude_sensitivity(df: pd.DataFrame, metric: str, a: str, b: str, min_n: int = 100,
                         env_col: str = "altitude_category", n_boot: int = 1000, seed: int = SEED) -> dict:
    """Efecto medio Δ(b−a) de ``metric`` por lanzamiento y su dispersión verdadera entre pitchers.

    Δ por (pitcher-temporada) con varianza de muestreo var_a/n_a + var_b/n_b; τ² = Var(Δ) − media(var de muestreo)
    (método de momentos, piso en 0); ``tau_hi`` = percentil 95 de τ al remuestrear pitcher-temporadas: la mayor
    dispersión compatible con los datos cuando τ̂ = 0. Solo devuelve agregados."""
    d = df[df[env_col].isin([a, b]) & df[metric].notna()].copy()
    d["_ps"] = d["pitcher_anon_id"].astype(str) + "_" + d["year"].astype(str)
    g = d.groupby(["_ps", env_col], observed=True)[metric].agg(["mean", "var", "size"]).unstack(env_col)
    g = g[(g["size"][[a, b]] >= min_n).all(axis=1)]
    delta = (g["mean"][b] - g["mean"][a]).to_numpy()
    se2 = (g["var"][a] / g["size"][a] + g["var"][b] / g["size"][b]).to_numpy()
    tau = _tau(delta, se2)
    w = 1.0 / (se2 + tau**2)
    rng = np.random.default_rng(seed)
    n = len(delta)
    boots = [_tau(delta[i], se2[i]) for i in (rng.integers(0, n, n) for _ in range(n_boot))]
    return {"mean_delta": float((delta * w).sum() / w.sum()), "tau": tau, "tau_hi": float(np.percentile(boots, 95)),
            "raw_sd": float(np.std(delta, ddof=1)), "mean_sampling_sd": float(np.sqrt(se2.mean())),
            "n_pitcher_seasons": int(n)}
