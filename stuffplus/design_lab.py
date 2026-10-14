"""Laboratorio de diseño de lanzamientos (HACK-033): ¿qué ajuste gana más Stuff+ en el Harp Helú?

Cada ajuste se aplica al lanzamiento *con su movimiento a nivel del mar* (``rho = 1``) y se puntúa en dos aires con el
mismo modelo de HACK-015 (``StuffModel`` con identidad ``pitch_family`` y traslado físico): el del Harp Helú
(``RHO_HARP_HELU``) y el del nivel del mar. La diferencia entre ambas ganancias dice si el ajuste vale más o menos en CDMX.

Reglas de coherencia (un árbol de decisión lee un lanzamiento incoherente como uno raro):
* velocidad y movimiento de la recta cambian las diferencias contra la recta (``*_diff_fb``) de los secundarios;
* girar el eje rota el vector (IVB, HB lado del brazo) conservando su magnitud;
* +% de eficiencia de giro = magnitud de movimiento × (1 + %) con ``SpinRate`` fijo (supuesto físico, no un rasgo del modelo);
* bajar el slot mueve ``RelHeight`` según la geometría de ``arm_angle`` y el movimiento según lo observado en pitchers con ese slot;
* un ajuste solo es admisible si el perfil resultante cae dentro del casco denso de perfiles observados de esa familia
  (``profile.knn_in_hull``); fuera del casco los árboles son planos y mostrarían ceros falsos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
import pandas as pd

from stuffplus.config import SEED
from stuffplus.profile import DIFF_FEATURES, FASTBALL_FAMILIES, LINKED_DIFF, PROFILE_FEATURES, knn_in_hull

PITCHER_SEASON = ["pitcher_anon_id", "year"]
NOISE_FLOOR = 0.10  # puntos de Stuff+ por debajo de los cuales una ganancia se considera ruido (≈ 1 % de σ del Stuff+ por lanzamiento)
NEW_PITCH_USAGE = 0.10  # uso supuesto de un lanzamiento nuevo (declarado en el reporte)


@dataclass(frozen=True)
class Tweak:
    key: str
    label: str
    kind: str  # velocity | axis | spin_eff | slot
    amount: float


TWEAKS: tuple[Tweak, ...] = (
    Tweak("velo_+1", "+1 mph de velocidad", "velocity", 1.0),
    Tweak("axis_+5", "eje de giro +5°", "axis", 5.0),
    Tweak("axis_-5", "eje de giro −5°", "axis", -5.0),
    Tweak("spineff_+5", "+5 % de eficiencia de giro (más movimiento)", "spin_eff", 0.05),
    Tweak("slot_-5", "slot de brazo 5° más bajo", "slot", -5.0),
)


# ---------------------------------------------------------------- operaciones coherentes sobre un marco
def _is_fb(frame: pd.DataFrame) -> pd.Series:
    return frame["pitch_family"].astype(str).isin(FASTBALL_FAMILIES)


def _propagate_to_secondaries(out: pd.DataFrame, before: pd.DataFrame, rows: pd.Series, features: Sequence[str]) -> None:
    """Si las filas ajustadas son la recta, las diferencias de los secundarios del mismo pitcher-temporada se mueven
    en sentido contrario al cambio medio de la recta; si son secundarios, su propia diferencia se mueve con su cambio."""
    fb_rows = rows & _is_fb(out)
    sec_rows = rows & ~_is_fb(out)
    for feat in features:
        diff = LINKED_DIFF.get(feat)
        if diff is None or diff not in out:
            continue
        change = out[feat].to_numpy(float) - before[feat].to_numpy(float)
        if sec_rows.any():
            out.loc[sec_rows, diff] = out.loc[sec_rows, diff].to_numpy(float) + change[sec_rows.to_numpy()]
        if fb_rows.any():
            d = pd.Series(change, index=out.index)[fb_rows].groupby([out.loc[fb_rows, c] for c in PITCHER_SEASON]).mean()
            key = pd.MultiIndex.from_frame(out[PITCHER_SEASON])
            shift = pd.Series(d.reindex(key).to_numpy(), index=out.index).fillna(0.0).to_numpy()
            others = ~_is_fb(out).to_numpy()
            out.loc[others, diff] = out.loc[others, diff].to_numpy(float) - shift[others]


def rotate_movement(frame: pd.DataFrame, mask: pd.Series, degrees: float, axis_sign: float = 1.0) -> pd.DataFrame:
    """Gira el eje de giro ``degrees`` y rota (IVB, HB lado del brazo) el mismo ángulo conservando la magnitud.

    ``axis_sign`` convierte el sentido del eje al del vector de movimiento (se estima de los datos, ``estimate_axis_sign``)."""
    out = frame.copy()
    th = np.radians(degrees) * axis_sign
    ivb, hb = out["InducedVertBreak"].to_numpy(float), out["hb_arm"].to_numpy(float)
    new_ivb, new_hb = ivb * np.cos(th) - hb * np.sin(th), ivb * np.sin(th) + hb * np.cos(th)
    m = mask.to_numpy()
    out.loc[m, "InducedVertBreak"], out.loc[m, "hb_arm"] = new_ivb[m], new_hb[m]
    out.loc[m, "spin_axis_arm"] = out.loc[m, "spin_axis_arm"].to_numpy(float) + degrees
    _propagate_to_secondaries(out, frame, mask, ["InducedVertBreak", "hb_arm"])
    return out


def scale_movement(frame: pd.DataFrame, mask: pd.Series, factor: float) -> pd.DataFrame:
    """Eficiencia de giro +x %: la magnitud del movimiento sube ×(1+x) con el mismo eje y ``SpinRate`` fijo."""
    out = frame.copy()
    m = mask.to_numpy()
    for c in ("InducedVertBreak", "hb_arm"):
        out.loc[m, c] = out.loc[m, c].to_numpy(float) * factor
    _propagate_to_secondaries(out, frame, mask, ["InducedVertBreak", "hb_arm"])
    return out


def add_velocity(frame: pd.DataFrame, mask: pd.Series, mph: float) -> pd.DataFrame:
    out = frame.copy()
    m = mask.to_numpy()
    out.loc[m, "RelSpeed"] = out.loc[m, "RelSpeed"].to_numpy(float) + mph
    _propagate_to_secondaries(out, frame, mask, ["RelSpeed"])
    return out


def arm_angle_of(rel_height, rel_side_abs) -> np.ndarray:
    """Misma definición que ``add_stuff_features``: grados de atan2(altura − 5 ft, |salida lateral|)."""
    return np.degrees(np.arctan2(np.asarray(rel_height, float) - 5.0, np.abs(np.asarray(rel_side_abs, float))))


def slot_movement_slopes(frame: pd.DataFrame, features: Sequence[str] = ("InducedVertBreak", "hb_arm"),
                         controls: Sequence[str] = ("RelSpeed", "SpinRate")) -> dict[str, dict[str, float]]:
    """Pendiente de cada rasgo de movimiento por grado de ``arm_angle`` dentro de cada familia, controlando velocidad y giro.

    Es lo observado entre pitchers con distinto slot (no una causa): acota «bajar el slot» al movimiento que esos pitchers muestran."""
    res: dict[str, dict[str, float]] = {}
    for fam, g in frame.groupby(frame["pitch_family"].astype(str)):
        cols = ["arm_angle", *controls]
        X = g[cols].astype(float).dropna()
        if len(X) < 200:
            continue
        A = np.column_stack([np.ones(len(X)), X.to_numpy()])
        res[fam] = {}
        for f in features:
            y = g.loc[X.index, f].astype(float).to_numpy()
            beta, *_ = np.linalg.lstsq(A, y, rcond=None)
            res[fam][f] = float(beta[1])
    return res


def lower_slot(frame: pd.DataFrame, mask: pd.Series, degrees: float, slopes: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Cambia el ángulo de brazo ``degrees`` (negativo = más bajo): ``RelHeight`` sigue la geometría de ``arm_angle`` con la
    salida lateral fija, y el movimiento cambia según la pendiente observada por familia (``slot_movement_slopes``)."""
    out = frame.copy()
    m = mask.to_numpy()
    new_angle = out["arm_angle"].to_numpy(float) + degrees
    out.loc[m, "arm_angle"] = new_angle[m]
    out.loc[m, "RelHeight"] = 5.0 + np.abs(out.loc[m, "rel_side_arm"].to_numpy(float)) * np.tan(np.radians(new_angle[m]))
    fam = out["pitch_family"].astype(str)
    for f in ("InducedVertBreak", "hb_arm"):
        slope = fam.map(lambda x: slopes.get(x, {}).get(f, 0.0)).to_numpy(float)
        out.loc[m, f] = out.loc[m, f].to_numpy(float) + slope[m] * degrees
    _propagate_to_secondaries(out, frame, mask, ["InducedVertBreak", "hb_arm"])
    return out


def estimate_axis_sign(frame: pd.DataFrame) -> float:
    """+1 si el ángulo del vector de movimiento atan2(HB, IVB) crece con ``spin_axis_arm`` (rotación en el mismo sentido), −1 si no.

    Se mira dentro de cada familia, con el eje desenvuelto alrededor de su mediana (un eje cerca de 0/360° no cuenta como salto)."""
    num = den = 0.0
    for _, g in frame.groupby(frame["pitch_family"].astype(str)):
        ax = g["spin_axis_arm"].astype(float).to_numpy()
        ax = (ax - np.nanmedian(ax) + 180.0) % 360.0 - 180.0
        ang = np.degrees(np.arctan2(g["hb_arm"].astype(float).to_numpy(), g["InducedVertBreak"].astype(float).to_numpy()))
        ang = (ang - np.nanmedian(ang) + 180.0) % 360.0 - 180.0
        ok = np.isfinite(ax) & np.isfinite(ang)
        if ok.sum() < 200:
            continue
        num += float(np.cov(ax[ok], ang[ok])[0, 1])
        den += float(np.var(ax[ok]))
    return 1.0 if den > 0 and num >= 0 else -1.0


def apply_tweak(frame: pd.DataFrame, mask: pd.Series, tweak: Tweak, slopes: dict | None = None, axis_sign: float = 1.0) -> pd.DataFrame:
    if tweak.kind == "velocity":
        return add_velocity(frame, mask, tweak.amount)
    if tweak.kind == "axis":
        return rotate_movement(frame, mask, tweak.amount, axis_sign)
    if tweak.kind == "spin_eff":
        return scale_movement(frame, mask, 1.0 + tweak.amount)
    if tweak.kind == "slot":
        return lower_slot(frame, mask, tweak.amount, slopes or {})
    raise ValueError(f"ajuste desconocido: {tweak.kind}")


# ---------------------------------------------------------------- casco de datos (admisibilidad)
def admissible(profile_rows: pd.DataFrame, reference: pd.DataFrame, cols: Sequence[str] = PROFILE_FEATURES, k: int = 10,
               keep: float = 0.95) -> np.ndarray:
    """True donde el perfil (ya ajustado) cae en la parte densa de los perfiles observados de la familia (``reference``)."""
    use = [c for c in cols if c in profile_rows and c in reference]
    return knn_in_hull(profile_rows[use].to_numpy(float), reference[use].to_numpy(float), k=k, keep=keep)


# ---------------------------------------------------------------- ganancias
def tweak_gain(frame: pd.DataFrame, mask: pd.Series, tweak: Tweak, score: Callable[[pd.DataFrame], dict[str, np.ndarray]],
               slopes: dict | None = None, axis_sign: float = 1.0, base: pd.DataFrame | None = None) -> pd.DataFrame:
    """Ganancia por lanzamiento (después − antes) en cada aire. ``score(frame)`` devuelve {'hh': Stuff+ Harp Helú, 'sea': Stuff+ nivel del mar}
    para un marco con movimiento a nivel del mar. Solo se puntúan las filas afectadas por el ajuste (la familia y, si es la recta, los secundarios).
    ``base``: Stuff+ ya calculado de ``frame`` (columnas ``hh`` y ``sea``, mismo índice) para no puntuar dos veces las mismas filas."""
    after = apply_tweak(frame, mask, tweak, slopes, axis_sign)
    cols = ["RelSpeed", "InducedVertBreak", "hb_arm", "RelHeight", *DIFF_FEATURES]
    changed = ~np.isclose(after[cols].to_numpy(float), frame[cols].to_numpy(float), rtol=0, atol=1e-9, equal_nan=True).all(axis=1)
    idx = np.flatnonzero(changed)
    out = pd.DataFrame({"hh": 0.0, "sea": 0.0}, index=frame.index)
    if len(idx):
        a = score(after.iloc[idx])
        b = {"hh": base["hh"].to_numpy()[idx], "sea": base["sea"].to_numpy()[idx]} if base is not None else score(frame.iloc[idx])
        out.iloc[idx, 0] = a["hh"] - b["hh"]
        out.iloc[idx, 1] = a["sea"] - b["sea"]
    out["diff"] = out["hh"] - out["sea"]
    return out


def usage_weighted_gain(gain: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    """Ganancia de arsenal por pitcher-temporada: media sobre sus lanzamientos muestreados (el uso queda representado por la muestra)."""
    g = gain[["hh", "sea", "diff"]].join(frame[PITCHER_SEASON])
    return g.groupby(PITCHER_SEASON, observed=True).mean()


def rank_top3(plan: pd.DataFrame, group: str = "pitcher_id", value: str = "gain_hh", noise: float = NOISE_FLOOR) -> pd.DataFrame:
    """Los 3 mejores ajustes por pitcher-temporada, solo los admisibles y por encima del piso de ruido; ordenados de mayor a menor."""
    ok = plan[(plan["admissible"]) & (plan[value] >= noise)]
    top = ok.sort_values([group, value], ascending=[True, False]).groupby(group, sort=False).head(3).copy()
    top["rank"] = top.groupby(group).cumcount() + 1
    return top


# ---------------------------------------------------------------- lanzamiento nuevo (splitter / sinker / sweeper)
def comparable_profile(centroids: pd.DataFrame, pitcher: pd.Series, shape_mask: pd.Series, velo_tol: float = 2.5,
                       angle_tol: float = 12.0, min_comp: int = 8) -> pd.Series | None:
    """Mediana del perfil de la forma entre pitchers comparables (misma mano, velocidad de recta y ángulo de brazo parecidos).
    ``centroids``: perfiles pitcher-temporada-familia con ``fb_velo``; devuelve None si hay menos de ``min_comp`` comparables."""
    c = centroids[shape_mask]
    c = c[(c["is_rhp"] == pitcher["is_rhp"]) & ((c["fb_velo"] - pitcher["fb_velo"]).abs() <= velo_tol)
          & ((c["arm_angle"] - pitcher["arm_angle"]).abs() <= angle_tol)]
    if len(c) < min_comp:
        return None
    return c[PROFILE_FEATURES + DIFF_FEATURES].median()


def new_pitch_row(pitcher: pd.Series, comp: pd.Series) -> pd.Series:
    """Fila del lanzamiento nuevo: salida del propio pitcher (velocidad vía diferencia, extensión, altura, lado, ángulo) y
    movimiento / giro / eje de los comparables, todo a nivel del mar."""
    row = comp.copy()
    row["RelSpeed"] = pitcher["fb_velo"] + comp["velo_diff_fb"]
    for c in ("Extension", "RelHeight", "rel_side_arm", "arm_angle"):
        row[c] = pitcher[c]
    row["is_rhp"] = pitcher["is_rhp"]
    row["rho"] = 1.0
    return row


def arsenal_delta_with_new_pitch(s_new: float, s_arsenal_mean: float, usage: float = NEW_PITCH_USAGE) -> float:
    """El lanzamiento nuevo toma ``usage`` del uso repartido proporcionalmente: Δ = uso × (Stuff+ nuevo − Stuff+ medio del arsenal). Puede ser negativo."""
    return float(usage * (s_new - s_arsenal_mean))


def cluster_mean_ci(values: pd.Series, clusters: pd.Series, n_boot: int = 500, seed: int = SEED) -> tuple[float, float, float]:
    """Media e IC 95 % remuestreando pitchers (clusters)."""
    from stuffplus.altitude import cluster_bootstrap_mean

    return cluster_bootstrap_mean(values, clusters, n_boot=n_boot, seed=seed)
