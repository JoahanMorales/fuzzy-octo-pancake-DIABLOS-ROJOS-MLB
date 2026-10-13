"""Descomposición aerodinámica a partir del ajuste de 9 parámetros de Trackman (x0..az0, ft y ft/s)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import (
    BALL_AREA_M2,
    BALL_MASS_KG,
    BALL_RADIUS_M,
    FT_TO_M,
    G_FT_S2,
    RHO_SI_SEA_LEVEL,
    RPM_TO_RADS,
)

_NEEDED = ["vx0", "vy0", "vz0", "ax0", "ay0", "az0"]


def decompose(df: pd.DataFrame, rho=1.0, rho_si: float = RHO_SI_SEA_LEVEL) -> pd.DataFrame:
    """Devuelve drag/Magnus/Cd/Cl-proxy, eficiencia de giro y giro activo por lanzamiento.

    drag: aceleración a lo largo de −v (ft/s², >0 frena). magnus: aceleración ⊥ v con gravedad
    retirada. cd_proxy = drag/v², cl_proxy = magnus/v² (1/ft; escalan ∝ ρ). cd/cl/spin_eff pasan a
    coeficientes adimensionales con la densidad *de cada lanzamiento*: `rho` (relativa a nivel del mar, escalar o
    serie alineada con `df`, p.ej. ρ̂ del juego) × `rho_si` (kg/m³ a nivel del mar). Con `rho=1.0` se asume nivel
    del mar para todos: en altura eso sesga Cl y la eficiencia de giro a la baja (Nathan: Cl = 1/(2.32+0.4/S)).
    """
    v = df[["vx0", "vy0", "vz0"]].to_numpy(float)
    a = df[["ax0", "ay0", "az0"]].to_numpy(float).copy()
    a[:, 2] += G_FT_S2  # retira gravedad
    speed = np.linalg.norm(v, axis=1)
    vhat = v / speed[:, None]
    a_par = np.einsum("ij,ij->i", a, vhat)
    drag = -a_par
    a_perp = a - a_par[:, None] * vhat
    magnus = np.linalg.norm(a_perp, axis=1)

    out = pd.DataFrame(index=df.index)
    out["speed_fps"] = speed
    out["drag_acc"] = drag
    out["magnus_acc"] = magnus
    out["cd_proxy"] = drag / speed**2
    out["cl_proxy"] = magnus / speed**2

    # coeficientes adimensionales: a = 0.5 ρ A C v² / m  (SI)
    rho_pitch = rho_si * np.broadcast_to(np.asarray(rho, float), len(df))  # kg/m³ por lanzamiento
    k = 0.5 * rho_pitch * BALL_AREA_M2 / BALL_MASS_KG * FT_TO_M  # a[ft/s²]/v²[ft/s]² -> C
    cd = out["cd_proxy"] / k
    cl = out["cl_proxy"] / k
    out["cd"], out["cl"] = cd, cl

    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / cl - 2.32
        s = np.where(inv > 0, 0.4 / inv, np.nan)  # parámetro de giro S = rω/v
    omega_t = s * (speed * FT_TO_M) / BALL_RADIUS_M  # rad/s transversal implicado
    out["transverse_spin_rpm"] = omega_t / RPM_TO_RADS
    if "SpinRate" in df:
        spin = df["SpinRate"].to_numpy(float)
        eff = np.clip(out["transverse_spin_rpm"].to_numpy() / spin, 0.0, 1.0)
        out["spin_eff"] = eff
        out["active_spin_rpm"] = eff * spin
    return out


def game_density_index(
    df: pd.DataFrame,
    game_col: str = "GameID",
    fastball_col: str = "is_fastball",
    min_n: int = 30,
    prior: pd.Series | None = None,
    ref_cd: float | None = None,
) -> pd.Series:
    """ρ̂ por juego = mediana Cd-proxy de rectas ÷ `ref_cd` (Cd-proxy a nivel del mar; por defecto el juego de mayor Cd, o sea el menos alto).

    Juegos con < `min_n` rectas se encogen hacia `prior` (índice game, p.ej. parque) o la media global.
    """
    d = decompose(df)
    d[game_col] = df[game_col].to_numpy()
    mask = df[fastball_col].to_numpy(bool)
    g = d[mask].groupby(game_col)["cd_proxy"]
    med, n = g.median(), g.size()
    ref = med.max() if ref_cd is None else ref_cd
    raw = med / ref
    base = prior.reindex(raw.index) if prior is not None else pd.Series(raw.mean(), index=raw.index)
    base = base.fillna(raw.mean())
    w = (n / min_n).clip(upper=1.0)
    return w * raw + (1 - w) * base
