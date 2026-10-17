"""Tunneling por tiempo (HACK-061): el punto de decisión del bateador son 150 ms antes de que la pelota llegue al plato.

Idea (Baseball Prospectus, "Pitch Tunnels"): el bateador se compromete en un *instante*, no a una distancia fija.
`features.arsenal` usa una distancia (23.8 ft); en aire delgado la pelota va más rápida y llega antes, así que 150 ms
antes del plato corresponden a otra distancia. Aquí se resuelve con el ajuste de 9 parámetros de Trackman (aceleración
constante, medido en y0 = 50 ft):

    x(t) = x0 + vx0 t + ax0 t²/2        (lateral)
    y(t) = y0 + vy0 t + ay0 t²/2        (hacia el plato, decrece)
    z(t) = z0 + vz0 t + az0 t²/2        (vertical)

1. `plate_time`: tiempo t_p en que y(t) = 17/12 ft (frente del plato), raíz positiva menor de la cuadrática.
2. Punto de decisión de cada lanzamiento: t_d = t_p − 0.150 s; se evalúa (x, z) en t_d.
3. Referencia: la recta principal del pitcher-temporada (`primary_fb_id`; si falta, la familia Four-Seam/Sinker más
   usada), con el promedio de sus 9 parámetros *del mismo juego* (≥ 3 rectas) o de la temporada, y su propio t_d.
   Cada tipo de pitch (`pitch_id`) usa su trayectoria promedio del juego (≥ 3) o de la temporada, con su propio t_d.
4. Separación (pulgadas) en x y z, magnitud en el punto de decisión y en el plato, y
   `tunnel_ratio_t` = separación en el plato / separación en la decisión (denominador acotado).

Rasgos físicos del tipo de pitch y de la recta del mismo pitcher; nunca resultados ni ubicación. Se comparan
trayectorias *promedio* por tipo de pitch y juego (ver `add_tunnel_features`), no lanzamientos sueltos, para que no
reflejen hacia dónde se apuntó. x se espeja por mano como en `arsenal.py` (positivo = lado del brazo).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from stuffplus.features.arsenal import KEYS

PLATE_FRONT_FT = 17.0 / 12.0  # frente del plato
DECISION_S = 0.150  # segundos antes de llegar al plato
PARAMS = ["x0", "y0", "z0", "vx0", "vy0", "vz0", "ax0", "ay0", "az0"]
MIRRORED = ("x0", "vx0", "ax0")
MIN_GAME_FB = 3
DEC_SEP_FLOOR_IN = 0.6  # = 0.05 ft, igual que arsenal.tunnel_ratio
RATIO_CAP = 20.0
REF_FAMILIES = ("Four-Seam", "Sinker")  # alternativa si no hay primary_fb_id
TUNNEL_FEATURES = [
    "tunnel_dec_dx_in", "tunnel_dec_dz_in", "tunnel_dec_sep_in",
    "tunnel_plate_dx_in", "tunnel_plate_dz_in", "tunnel_plate_sep_in", "tunnel_ratio_t",
]
DIAGNOSTICS = ["tunnel_t_plate_s", "tunnel_dec_y_ft"]


def _sign(df: pd.DataFrame) -> np.ndarray:
    return np.where(df["PitcherThrows"].astype(str).str.startswith("L"), -1.0, 1.0)


def plate_time(y0, vy0, ay0, y_plate: float = PLATE_FRONT_FT) -> np.ndarray:
    """Primer instante (s) en que y(t) = y_plate, raíz positiva menor; estable si ay0 → 0. NaN si no hay."""
    y0, vy0, ay0 = (np.asarray(v, float) for v in (y0, vy0, ay0))
    a, b, c = 0.5 * ay0, vy0, y0 - y_plate
    disc = np.sqrt(np.maximum(b * b - 4 * a * c, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = 2 * c / (-b + disc)
    return np.where(np.isfinite(t) & (t > 0), t, np.nan)


def _pos(p0, v0, a0, t):
    return p0 + v0 * t + 0.5 * a0 * t * t


def flight_points(P: pd.DataFrame, decision_s: float = DECISION_S) -> pd.DataFrame:
    """Para parámetros (x ya espejado): t_p, y y (x, z) en el punto de decisión y en el plato. Posiciones en ft."""
    g = {c: P[c].to_numpy(float) for c in PARAMS}
    t_p = plate_time(g["y0"], g["vy0"], g["ay0"])
    t_d = t_p - decision_s
    t_d = np.where(t_d > 0, t_d, np.nan)
    out = pd.DataFrame({
        "t_plate": t_p,
        "y_dec": _pos(g["y0"], g["vy0"], g["ay0"], t_d),
        "x_dec": _pos(g["x0"], g["vx0"], g["ax0"], t_d),
        "z_dec": _pos(g["z0"], g["vz0"], g["az0"], t_d),
        "x_plate": _pos(g["x0"], g["vx0"], g["ax0"], t_p),
        "z_plate": _pos(g["z0"], g["vz0"], g["az0"], t_p),
    }, index=P.index)
    return out


def _reference_mask(d: pd.DataFrame) -> pd.Series:
    """Filas que son la recta principal del pitcher-temporada (por pitch_id, o por familia si no hay id)."""
    if "primary_fb_id" in d and "pitch_id" in d:
        return pd.Series(d["pitch_id"].to_numpy() == d["primary_fb_id"].to_numpy(), index=d.index) & d["primary_fb_id"].notna()
    if "pitch_family" not in d:
        raise KeyError("se necesita primary_fb_id+pitch_id o pitch_family para elegir la recta principal")
    fb = d[d["pitch_family"].isin(REF_FAMILIES)]
    cnt = fb.groupby(KEYS + ["pitch_family"]).size().rename("n").reset_index()
    best = cnt.sort_values("n", ascending=False).drop_duplicates(KEYS).set_index(KEYS)["pitch_family"]
    key = pd.MultiIndex.from_frame(d[KEYS])
    return pd.Series(d["pitch_family"].to_numpy() == best.reindex(key).to_numpy(), index=d.index)


def _group_points(P: pd.DataFrame, keys: pd.DataFrame, by: list[str], min_n: int, decision_s: float) -> pd.DataFrame:
    """Puntos de vuelo de la trayectoria promedio de cada grupo `by` (n >= min_n). Índice = llaves del grupo."""
    g = pd.concat([P, keys[by]], axis=1).groupby(by)
    mean, n = g[PARAMS].mean(), g.size()
    return flight_points(mean[n >= min_n], decision_s).add_prefix("m_")


def _lookup(table: pd.DataFrame, d: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    return table.reindex(pd.MultiIndex.from_frame(d[by])).set_axis(d.index)


def add_tunnel_features(df: pd.DataFrame, decision_s: float = DECISION_S, min_game_n: int = MIN_GAME_FB) -> pd.DataFrame:
    """Copia de `df` con `TUNNEL_FEATURES`, `DIAGNOSTICS` y `tunnel_is_ref` (la fila es la recta principal). Sin pitch_id (< 0) o sin recta de referencia → NaN.

    Unidad de comparación = la trayectoria *promedio* de cada tipo de pitch (pitcher x temporada x pitch_id x juego,
    ≥ 3 lanzamientos, si no el promedio de la temporada) contra la trayectoria promedio de la recta principal
    construida igual. Así cada lanzamiento lleva la forma de su arsenal en el aire de ese juego, no hacia dónde se
    apuntó: comparar cada lanzamiento contra la recta daría casi `PlateLocHeight`/`PlateLocSide` menos una
    constante (r ≈ 0.9 en los datos reales), es decir ubicación disfrazada, prohibida en Stuff+.
    La recta principal vale 0 contra sí misma.
    """
    d = df.copy()
    P = pd.DataFrame({c: d[c].astype(float) for c in PARAMS}, index=d.index)
    sgn = _sign(d)
    for c in MIRRORED:
        P[c] = P[c] * sgn
    ok = P.notna().all(axis=1).to_numpy()
    tcol = "pitch_id" if "pitch_id" in d else "pitch_family"
    typed = ok & (d["pitch_id"].to_numpy() >= 0 if tcol == "pitch_id" else d["pitch_family"].notna().to_numpy())
    is_ref = _reference_mask(d).to_numpy() & ok
    gk = KEYS + ["game_anon_id"]

    def build(mask, extra: list[str]) -> pd.DataFrame:
        """Puntos por pitcher-temporada(-tipo)-juego con respaldo de temporada, para las filas de `d`."""
        keys = d.loc[mask, KEYS + extra + ["game_anon_id"]]
        Pm = P[mask]
        game = _group_points(Pm, keys, KEYS + extra + ["game_anon_id"], min_game_n, decision_s)
        season = _group_points(Pm, keys, KEYS + extra, 1, decision_s)
        r_game = _lookup(game, d, KEYS + extra + ["game_anon_id"])
        r_season = _lookup(season, d, KEYS + extra)
        return r_game.where(r_game["m_t_plate"].notna(), r_season)

    mine = build(typed, [tcol])
    ref = build(is_ref, [])
    in12 = 12.0
    dec_dx = (mine["m_x_dec"] - ref["m_x_dec"]) * in12
    dec_dz = (mine["m_z_dec"] - ref["m_z_dec"]) * in12
    plate_dx = (mine["m_x_plate"] - ref["m_x_plate"]) * in12
    plate_dz = (mine["m_z_plate"] - ref["m_z_plate"]) * in12
    dec_sep = np.hypot(dec_dx, dec_dz)
    plate_sep = np.hypot(plate_dx, plate_dz)
    out = pd.DataFrame({
        "tunnel_dec_dx_in": dec_dx, "tunnel_dec_dz_in": dec_dz, "tunnel_dec_sep_in": dec_sep,
        "tunnel_plate_dx_in": plate_dx, "tunnel_plate_dz_in": plate_dz, "tunnel_plate_sep_in": plate_sep,
        "tunnel_ratio_t": (plate_sep / dec_sep.clip(lower=DEC_SEP_FLOOR_IN)).clip(upper=RATIO_CAP),
        "tunnel_t_plate_s": mine["m_t_plate"], "tunnel_dec_y_ft": mine["m_y_dec"],
    }, index=d.index)
    out.loc[~typed, TUNNEL_FEATURES + DIAGNOSTICS] = np.nan
    out.loc[is_ref & out["tunnel_dec_sep_in"].notna().to_numpy(), TUNNEL_FEATURES] = 0.0
    out["tunnel_is_ref"] = is_ref
    return d.drop(columns=[c for c in TUNNEL_FEATURES + DIAGNOSTICS + ["tunnel_is_ref"] if c in d]).join(out)
