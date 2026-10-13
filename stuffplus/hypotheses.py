"""Hipótesis H1–H4 sobre el efecto de la altitud, con diseño intra-pitcher e IC bootstrap por pitcher (HACK-009).

Reglas del diseño (fijadas antes de mirar los datos reales):

* Se compara por ``pitch_key`` (pitcher × temporada × ``pitch_id``, HACK-029), nunca por ``AutoPitchType``.
* Estimador: Δ por lanzamiento = media(ambiente b) − media(ambiente a), solo con ``n >= min_n`` observaciones válidas
  de la métrica en ambos; promedio ponderado por la n armónica. El IC se obtiene remuestreando **pitchers**
  (clusters) sobre la tabla ya agregada, sin reajustar nada dentro del bucle.
* Dosis-respuesta: pendiente intra-lanzamiento de la métrica contra la ρ̂ del **parque** (no solo 3 buckets),
  por cada 0.1 de ρ̂ (ρ̂ menor = más altura, así que el signo esperado es el opuesto al de Δ Extreme−No).
* ``verdict``: Supported si el IC de Δ excluye 0 en la dirección predicha Y la pendiente concuerda; Partially si solo
  una de las dos; Rejected si ninguna.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from stuffplus.config import SEED

PITCHER = "pitcher_anon_id"
KEY = "pitch_key"
ENV = "altitude_category"
FAMILY = "pitch_family"
NO_ALT, MED_ALT, EXT_ALT = "No Altitude", "Medium Altitude", "Extreme Altitude"
FASTBALLS = ("Four-Seam", "Sinker", "Cutter")
OFFSPEED = ("Changeup", "Splitter")
BREAKING = ("Slider", "Curveball")
SLOPE_SCALE = 0.1  # pendiente por cada 0.1 de ρ̂


# ---------------------------------------------------------------- métricas derivadas
def add_movement_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega ``hb_arm`` (HB positivo = lado del brazo, igual para zurdos y derechos), ``abs_ivb``, ``abs_hb`` y
    ``total_break``. Una pérdida de movimiento se mide en magnitud: una curva que cae menos *pierde* quiebre."""
    out = df.copy()
    sign = np.where(out["PitcherThrows"].astype(str).str.startswith("L"), -1.0, 1.0)
    out["hb_arm"] = out["HorzBreak"].astype(float) * sign
    out["abs_ivb"] = out["InducedVertBreak"].astype(float).abs()
    out["abs_hb"] = out["hb_arm"].abs()
    out["total_break"] = np.hypot(out["InducedVertBreak"].astype(float), out["HorzBreak"].astype(float))
    return out


def add_batted_ball_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Métricas sobre bolas bateadas, NaN fuera de su denominador: ``hr_fb`` (HR / fly balls, igual que HACK-003),
    ``fb_distance``, ``gb_flag`` (1 si rodado, entre bolas en juego con tipo y sin bunt)."""
    out = df.copy()
    ht = out["hit_type"].astype(object)
    fly = ht.eq("FlyBall")
    out["hr_fb"] = out["home_run"].astype(float).where(fly)
    out["fb_distance"] = out["Distance"].astype(float).where(fly)
    valid = ht.notna() & ht.ne("Bunt") & out["PitchCall"].astype(str).eq("InPlay")
    out["gb_flag"] = ht.eq("GroundBall").astype(float).where(valid)
    return out


# ---------------------------------------------------------------- bootstrap por pitcher
def _ci(x: np.ndarray) -> tuple[float, float]:
    lo, hi = np.nanpercentile(x, [2.5, 97.5])
    return float(lo), float(hi)


def _cluster_boot(pitchers: np.ndarray, comps: Sequence[tuple[np.ndarray, np.ndarray]],
                  stat: Callable[..., np.ndarray], n_boot: int, seed: int) -> tuple[float, float, float]:
    """Remuestrea pitchers. ``comps`` = [(numerador_p, denominador_p), ...] alineados con ``pitchers``; cada razón
    Σ(c_p·num)/Σ(c_p·den) se recalcula con los conteos multinomiales y ``stat`` las combina. Devuelve (est, lo, hi)."""
    p = len(pitchers)
    point = stat(*[c[0].sum() / c[1].sum() for c in comps])
    if p < 2:
        return float(point), np.nan, np.nan
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(p, np.full(p, 1.0 / p), size=n_boot).astype(float)
    ratios = [(counts @ n) / (counts @ d) for n, d in comps]
    lo, hi = _ci(stat(*ratios))
    return float(point), lo, hi


def _cells(df: pd.DataFrame, metric: str, key_col: str, env_col: str, envs: Iterable) -> pd.DataFrame:
    """Media y n válidos de ``metric`` por (pitcher, key, ambiente)."""
    sub = df[df[env_col].isin(list(envs)) & df[metric].notna()]
    g = sub.groupby([PITCHER, key_col, env_col], observed=True)[metric].agg(["mean", "size"])
    return g


def _filter_family(df: pd.DataFrame, pitch_id_family, family_col: str) -> pd.DataFrame:
    if pitch_id_family is None:
        return df
    fams = [pitch_id_family] if isinstance(pitch_id_family, str) else list(pitch_id_family)
    return df[df[family_col].isin(fams)]


def _delta_parts(df: pd.DataFrame, metric: str, a, b, min_n: int, key_col: str, env_col: str):
    """Por pitcher: Σ w·Δ y Σ w de los lanzamientos con n >= min_n en a y en b (w = n armónica)."""
    g = _cells(df, metric, key_col, env_col, (a, b))
    mean, n = g["mean"].unstack(env_col), g["size"].unstack(env_col)
    ok = n[[a, b]].ge(min_n).all(axis=1) if {a, b} <= set(n.columns) else pd.Series(False, index=n.index)
    if not ok.any():
        return pd.DataFrame(columns=["sw", "w"])
    mean, n = mean[ok], n[ok]
    w = 1.0 / (1.0 / n[a] + 1.0 / n[b])
    d = (mean[b] - mean[a]) * w
    return pd.DataFrame({"sw": d, "w": w}).groupby(level=PITCHER).sum()


@dataclass
class Estimate:
    delta: float
    lo: float
    hi: float
    n_keys: int
    n_pitchers: int

    def as_dict(self) -> dict:
        return {"delta": self.delta, "lo": self.lo, "hi": self.hi, "n_keys": self.n_keys, "n_pitchers": self.n_pitchers}


def within_pitcher_delta(df: pd.DataFrame, metric: str, pitch_id_family, a: str, b: str, min_n: int = 20,
                         n_boot: int = 2000, *, key_col: str = KEY, env_col: str = ENV, family_col: str = FAMILY,
                         seed: int = SEED) -> Estimate:
    """Δ medio (ambiente ``b`` − ``a``) de ``metric`` dentro de cada lanzamiento, filtrado por familia(s) de
    ``pitch_id`` (``None`` = todas). IC 95 % bootstrap por pitcher. ``min_n`` cuenta observaciones válidas de la
    métrica (p.ej. swings para whiff), no lanzamientos."""
    sub = _filter_family(df, pitch_id_family, family_col)
    parts = _delta_parts(sub, metric, a, b, min_n, key_col, env_col)
    if parts.empty:
        return Estimate(np.nan, np.nan, np.nan, 0, 0)
    g = _cells(sub, metric, key_col, env_col, (a, b))
    n_keys = int(g["size"].unstack(env_col)[[a, b]].ge(min_n).all(axis=1).sum())
    est, lo, hi = _cluster_boot(parts.index.to_numpy(), [(parts["sw"].to_numpy(), parts["w"].to_numpy())],
                                lambda r: r, n_boot, seed)
    return Estimate(est, lo, hi, n_keys, len(parts))


def _dose_parts(df: pd.DataFrame, metric: str, rho_col: str, min_n: int, key_col: str) -> pd.DataFrame:
    """Por pitcher: Σ_k Σ_c n·(x−x̄_k)(y−ȳ_k) y Σ_k Σ_c n·(x−x̄_k)², con celdas (key × ρ̂ de parque) de n >= min_n."""
    sub = df[df[metric].notna() & df[rho_col].notna()]
    g = sub.groupby([PITCHER, key_col, rho_col])[metric].agg(["mean", "size"]).reset_index()
    g = g[g["size"] >= min_n]
    g = g[g.groupby(key_col)[rho_col].transform("nunique") >= 2]
    if g.empty:
        return pd.DataFrame(columns=["num", "den"])
    w = g["size"].to_numpy(float)
    kk = g[key_col]
    sw = pd.Series(w, index=g.index).groupby(kk).transform("sum")
    xbar = (g[rho_col] * w).groupby(kk).transform("sum") / sw
    ybar = (g["mean"] * w).groupby(kk).transform("sum") / sw
    g["num"] = w * (g[rho_col] - xbar) * (g["mean"] - ybar)
    g["den"] = w * (g[rho_col] - xbar) ** 2
    return g.groupby(PITCHER)[["num", "den"]].sum()


def dose_response(df: pd.DataFrame, metric: str, rho_col: str, pitch_id_family=None, min_n: int = 20,
                  n_boot: int = 2000, *, key_col: str = KEY, family_col: str = FAMILY, seed: int = SEED) -> Estimate:
    """Pendiente intra-lanzamiento de ``metric`` contra la ρ̂ del parque (``rho_col``), por cada 0.1 de ρ̂."""
    sub = _filter_family(df, pitch_id_family, family_col)
    parts = _dose_parts(sub, metric, rho_col, min_n, key_col)
    if parts.empty or parts["den"].sum() <= 0:
        return Estimate(np.nan, np.nan, np.nan, 0, 0)
    est, lo, hi = _cluster_boot(parts.index.to_numpy(), [(parts["num"].to_numpy(), parts["den"].to_numpy())],
                                lambda r: r * SLOPE_SCALE, n_boot, seed)
    n_keys = int(sub[sub[metric].notna()].groupby(key_col)[rho_col].nunique().ge(2).sum())
    return Estimate(est, lo, hi, n_keys, len(parts))


def paired_did(df: pd.DataFrame, metric: str, fam_a: Sequence[str], fam_b: Sequence[str], a: str, b: str,
               min_n: int = 20, n_boot: int = 2000, *, env_col: str = ENV, family_col: str = FAMILY,
               seed: int = SEED) -> Estimate:
    """Diferencia de diferencias dentro de pitcher-temporada: (Δ_b−a de las familias ``fam_a``) − (Δ de ``fam_b``).

    Cada grupo se agrupa por pitcher-temporada (no por lanzamiento) para que ambos tengan celdas suficientes."""
    d = df[df[family_col].isin(list(fam_a) + list(fam_b))].copy()
    d["_grp"] = np.where(d[family_col].isin(list(fam_a)), "A", "B")
    d["_ps"] = d[PITCHER].astype(str) + "_" + d["year"].astype(str)
    sub = d[d[env_col].isin((a, b)) & d[metric].notna()]
    g = sub.groupby([PITCHER, "_ps", "_grp", env_col], observed=True)[metric].agg(["mean", "size"])
    mean, n = g["mean"].unstack([ "_grp", env_col]), g["size"].unstack(["_grp", env_col])
    need = [("A", a), ("A", b), ("B", a), ("B", b)]
    if not set(need) <= set(n.columns):
        return Estimate(np.nan, np.nan, np.nan, 0, 0)
    ok = n[need].ge(min_n).all(axis=1)
    if not ok.any():
        return Estimate(np.nan, np.nan, np.nan, 0, 0)
    mean, n = mean[ok], n[ok]
    did = (mean[("A", b)] - mean[("A", a)]) - (mean[("B", b)] - mean[("B", a)])
    w = 1.0 / sum(1.0 / n[c] for c in need)
    parts = pd.DataFrame({"sw": did * w, "w": w}).groupby(level=PITCHER).sum()
    est, lo, hi = _cluster_boot(parts.index.to_numpy(), [(parts["sw"].to_numpy(), parts["w"].to_numpy())],
                                lambda r: r, n_boot, seed)
    return Estimate(est, lo, hi, int(ok.sum()), len(parts))


def moderated_delta(df: pd.DataFrame, metric: str, moderator: str, a: str, b: str, min_n: int = 30,
                    n_boot: int = 2000, *, key_col: str = "_ps", env_col: str = ENV, per: float = 0.1,
                    seed: int = SEED) -> Estimate:
    """Pendiente de Δ(b−a) de ``metric`` por pitcher-temporada contra ``moderator`` (columna constante por
    pitcher-temporada, p.ej. su GB% a nivel del mar), por cada ``per`` del moderador. MCO ponderado por la n
    armónica; IC bootstrap por pitcher. Con ``key_col='_ps'`` crea la clave pitcher-temporada."""
    d = df.copy()
    if key_col == "_ps":
        d["_ps"] = d[PITCHER].astype(str) + "_" + d["year"].astype(str)
    g = _cells(d, metric, key_col, env_col, (a, b))
    mean, n = g["mean"].unstack(env_col), g["size"].unstack(env_col)
    if not {a, b} <= set(n.columns):
        return Estimate(np.nan, np.nan, np.nan, 0, 0)
    ok = n[[a, b]].ge(min_n).all(axis=1)
    mod = d.groupby([PITCHER, key_col], observed=True)[moderator].first()
    t = pd.DataFrame({"y": mean[b] - mean[a], "w": 1.0 / (1.0 / n[a] + 1.0 / n[b]), "x": mod.reindex(mean.index)})[ok]
    t = t.dropna()
    if len(t) < 5:
        return Estimate(np.nan, np.nan, np.nan, len(t), 0)
    xbar = (t["x"] * t["w"]).sum() / t["w"].sum()
    ybar = (t["y"] * t["w"]).sum() / t["w"].sum()
    # la pendiente es razón de sumas centradas; el centrado depende de la muestra, pero es de segundo orden
    t["num"] = t["w"] * (t["x"] - xbar) * (t["y"] - ybar)
    t["den"] = t["w"] * (t["x"] - xbar) ** 2
    parts = t.groupby(level=PITCHER)[["num", "den"]].sum()
    est, lo, hi = _cluster_boot(parts.index.to_numpy(), [(parts["num"].to_numpy(), parts["den"].to_numpy())],
                                lambda r: r * per, n_boot, seed)
    return Estimate(est, lo, hi, len(t), len(parts))


# ---------------------------------------------------------------- veredicto
def _excludes_zero(lo: float, hi: float, direction: int) -> bool:
    if not np.isfinite(lo) or not np.isfinite(hi):
        return False
    return lo > 0 if direction > 0 else hi < 0


def verdict(delta: Estimate, direction: int, slope: Estimate | None = None) -> str:
    """``direction``: signo predicho de Δ (Extreme−No). La pendiente contra ρ̂ debe tener el signo opuesto.

    Supported = Δ y pendiente concuerdan (solo Δ si no hay pendiente); Partially = solo una; Rejected = ninguna."""
    d_ok = _excludes_zero(delta.lo, delta.hi, direction)
    if slope is None:
        return "Supported" if d_ok else "Rejected"
    s_ok = _excludes_zero(slope.lo, slope.hi, -direction)
    return "Supported" if d_ok and s_ok else ("Partially" if d_ok or s_ok else "Rejected")


def overall_verdict(verdicts: Iterable[str]) -> str:
    v = list(verdicts)
    if v and all(x == "Supported" for x in v):
        return "Supported"
    if any(x in ("Supported", "Partially") for x in v):
        return "Partially"
    return "Rejected"


# ---------------------------------------------------------------- ρ̂ por juego y por parque
def game_rho(df: pd.DataFrame, family_col: str = FAMILY) -> pd.Series:
    """ρ̂ por juego en la misma escala que HACK-004: Cd-proxy de rectas ÷ la mediana de juegos sin altitud (=1),
    con los juegos < 30 rectas encogidos hacia su bucket. Requiere ``pitch_family`` (``assign_pitch_id``)."""
    from stuffplus.physics import aero

    d = df.copy()
    d["is_fastball"] = d[family_col].isin(FASTBALLS)
    d["cd_proxy"] = aero.decompose(d)["cd_proxy"]
    ref = d.loc[d["is_fastball"] & d[ENV].eq(NO_ALT), "cd_proxy"].median()
    bucket = d.groupby("game_anon_id")[ENV].agg(lambda s: s.mode().iat[0])
    prior = d.groupby(ENV, observed=True)["cd_proxy"].median() / ref
    prior_game = bucket.astype(str).map(prior.rename(index=str)).astype(float)
    return aero.game_density_index(d, game_col="game_anon_id", ref_cd=ref, prior=prior_game)


def park_rho(rho_game: pd.Series, park_map: pd.DataFrame, game_col: str = "game_anon_id",
             park_col: str = "franchise") -> tuple[pd.Series, int]:
    """ρ̂ del parque (mediana de sus juegos de local) asignado a cada juego. Devuelve (serie por juego, juegos sin parque)."""
    pm = park_map.drop_duplicates(game_col).set_index(game_col)[park_col]
    park = pm.reindex(rho_game.index)
    med = rho_game.groupby(park).median()
    out = park.map(med)
    return out, int(out.isna().sum())
